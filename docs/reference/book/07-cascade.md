# Cascade

Cascade is the v1 safety-critical feature. A following child must converge on its parent's desired base without letting the managed agent observe new files without an explanation. The design follows jj's actual division of responsibility: jj owns revision evolution in repository state; kiki owns follows intent, safe workspace reconciliation, recovery, and agent context.

Every cascade is a base transition from the last synchronized parent commit to a new exact parent commit:

- **`NativeRewrite`** — jj has already evolved the child's repository history so the new parent base is an ancestor of the child's current repository commit. Kiki must not rebase it again; it reconciles the on-disk workspace to jj's current view at a safe boundary.
- **`ParentAdvance`** — the new parent base is not already an ancestor of the child. jj cannot infer kiki's follows relationship from revision topology alone, so kiki explicitly rebases the child's owned stack onto that exact parent commit at a safe boundary.

The intent pins the base transition, not the child's working-copy commit. A child commit is a volatile outcome: agent edits and ordinary jj snapshots can change it without changing whether the follows base is synchronized.

## Invariant

Kiki does not reconcile evolved state or perform an explicit follows rebase in a managed workspace while that workspace's managed agent is mid-edit.

Repository state may evolve earlier. Rewriting an ancestor in workspace A can cause jj to evolve workspace B's working-copy commit in the shared repository immediately, leaving B's files stale. The invariant governs when kiki changes B's files and agent context, not when jj records successor commits.

A direct human `jj` command is an explicit escape hatch. It may reconcile a stale workspace before kiki's boundary and may do so without creating a new repository operation. Kiki therefore discovers actual workspace freshness at the next managed boundary; it does not pretend every materialization is observable in the op log.

## Classification

The op-log watcher classifies repository transitions from before/after operation views, not command names. For each follows edge it compares:

- the edge's last synchronized parent commit;
- the parent workspace's exact `@` before and after, with the result persisted as `thread_head_commit_id`;
- whether the new exact parent head is an ancestor of the child's repository commit after the operation;
- whether relevant bookmarks, changes, or operation heads are conflicted or divergent.

The result is:

- `NativeRewrite { from_base, to_base, trigger_op }` when the parent head changed and `to_base` is already an ancestor of the child;
- `ParentAdvance { from_base, to_base, trigger_op }` when the parent head changed and `to_base` is not yet an ancestor of the child;
- `AlreadyAligned` when no reconciliation remains;
- `TopologyDiverged { reason }` when the parent moved backward, the follows anchors no longer describe the real topology, or the relevant jj state is conflicted or ambiguous.

Change ids correlate rewritten parent revisions; commit ids pin the exact base transition. The bookmark is not consulted for follows classification. Kiki must not resolve “whatever the parent workspace or checkpoint points to later” as the destination of an older intent.

The same rule applies when a follows edge is first created. Because `thread_head_commit_id` is a cache, creation pins a fresh jj operation view, reads the parent workspace's actual `@` from that view, updates the parent's cached head, and uses that exact commit as both the child's base and the edge's initial synchronized-parent anchor in one journaled step. It never bases a child on a possibly lagging watcher observation.

## Coalescing and multi-hop evolution

An intent in `Detected` may absorb later compatible parent transitions by replacing `to_base` with the newest exact base, reclassifying its kind against current ancestry, and recording every contributing operation. Once reconciliation starts, later transitions create a new intent instead of changing the in-flight target.

Repository evolution is not forced to proceed one follows edge at a time. A single jj rewrite may logically evolve B and C in A→B→C. Kiki records one base-transition intent for each affected follows edge, and each workspace reconciles independently at its own safe boundary.

An explicit `ParentAdvance` on B may cause jj to evolve C. The initiating handler compares its starting and result operation views and records C's resulting `NativeRewrite`; the attributed operation is not classified a second time by the watcher.

## Synchronization intent: the sole protocol authority

Each reconciliation is one durable `sync_intents` row:

- `intent_id`, `thread_id`, and monotonic per-thread `seq`;
- `kind: NativeRewrite | ParentAdvance`;
- `from_base_commit` and exact `to_base_commit`;
- `classification_op_id` naming the exact repository view used for the latest classification, plus normalized trigger-operation rows;
- `state: Detected | Reconciling | Materialized | Delivered | Acknowledged | RecoveryRequired | TopologyDiverged | Superseded`;
- optional planned/result operation ids and actual result workspace commit;
- embedded outbox fields: byte-stable payload, pinned transcript anchor, preparation/delivery/acknowledgement timestamps, transcript row id, `delivery_mode: SoftBatch | RestartStartup`, and that mode's exact proof fields;
- optional recovery metadata naming preserved files or divergent commits.

The intent row is the only authority for cascade progress and delivery. There are no mirrored pending/materialized/acknowledged counters, separate context queue, or separate cascade-outbox table. The thread's three-valued UI status is derived from all unresolved intents, with blocking state taking precedence:

- any `RecoveryRequired | TopologyDiverged` → `conflicted`;
- otherwise, any `Detected | Reconciling | Materialized | Delivered` → `pending`;
- no unresolved intent → `in sync`.

Each **runtime agent incarnation** carries only `delivered_intent_id`, identifying the intent most recently emitted to that process and not yet acknowledged. This row has its own kiki UUID; the harness conversation/session id is a separate field and may be reused by `--resume`. The active intent embeds the durable delivery proof. `SoftBatch` names the runtime incarnation, model turn, tool batch, binding time, and optional exact batch-completion time. `RestartStartup` names the replacement incarnation and a kiki-minted one-use `startup_delivery_id` that the harness must causally echo on the first model turn generated from that startup input.

In-memory batch admission is only an optimization. A durable `Block` is reconstructed from the intent. A lost `PassThrough` admission is not guessed or reconstructed: the adapter restarts the incarnation before permitting a reconciliation decision that could mutate the workspace. Starting any replacement process retires the prior marker without acknowledging the intent; when a payload is pending, the replacement receives it through `RestartStartup` before any tool is allowed to run.

## Reconciliation lock and ordering

Each thread has an in-memory reconciliation lock owned by `CascadeOrchestrator`, concretely a `tokio::sync::Mutex` keyed by `thread_id`. The durable intent state, not the mutex, provides crash recovery.

Intents reconcile in sequence order. The lock serializes concurrent hook decisions and recovery for one thread. The op-log watcher may update only a `Detected` intent; after an intent enters `Reconciling`, newer work gets a later sequence.

## Workspace probe

Before changing files, kiki performs a non-materializing workspace probe against the edge's last synchronized base, jj's recorded working-copy state, and the current filesystem. The probe returns a fingerprint plus one of:

- `FreshClean` — the workspace is already reconciled and has no unsnapshotted edits, including when a human updated it directly;
- `FreshDirty` — the base is already reconciled, but the current filesystem has unsnapshotted edits;
- `StaleClean` — jj's repository view evolved but the on-disk workspace has no unsnapshotted tracked changes relative to its last checked-out state;
- `StaleDirty` — the workspace is stale and also contains unsnapshotted changes;
- `Unknown` — the CLI backend cannot prove one of the preceding states without mutating the workspace.

The fingerprint covers the path inventory and byte hashes used to classify edits; kiki rechecks it immediately before mutation and aborts to recovery if it drifted. The `JjCli` proof of concept must demonstrate a lossless implementation. If it cannot distinguish a clean state from a dirty one without mutation, v1 must return `Unknown`. Optimistic materialization is not permitted.

## `NativeRewrite` reconciliation

At the child's safe boundary:

1. Claim the reconciliation lock, load the oldest intent, and transition `Detected → Reconciling`.
2. Revalidate the exact base transition against current repository ancestry. A compatible newer transition may supersede this intent; ambiguity becomes `TopologyDiverged`.
3. Run the non-materializing workspace probe.
4. For `FreshClean | FreshDirty`, verify actual ancestry and continue to result persistence without rewriting files. A `NativeRewrite` does not need to disturb later edits after the base was already materialized.
5. For `StaleClean`, run `jj workspace update-stale`, then verify the actual resulting workspace commit and ancestry.
6. For `StaleDirty | Unknown`, transition to `RecoveryRequired`, hard-pause the agent, and enter the recovery path below. Do not soft-materialize and resume.
7. Compose the byte-stable payload from the base transition and actual result. In one SQLite transaction, store the result commit, payload, anchor, and `state=Materialized`; update the thread's cached live head from the exact result operation view; and advance the follows edge's last synchronized base.

`jj workspace update-stale` has no exact-target argument and may reconcile to a newer compatible repository view if an external operation lands concurrently. The actual result is authoritative. If it covers a coherent later base transition, kiki records or supersedes the covered intents accordingly; if it does not, kiki stops rather than claiming the older target was materialized exactly.

## Unsnapshotted-edit recovery

A stale workspace with unsnapshotted edits is a normal active-agent race, not an exceptional corruption case. `jj workspace update-stale` may preserve the edits in a divergent/conflicted successor while placing a clean evolved successor on disk. Kiki must never resume the agent on that clean successor while its edits are hidden elsewhere.

Recovery is deliberately loud:

1. Hard-pause the agent before materialization.
2. Create a loss-safe recovery bundle through `WorkspaceRecovery` at `~/.config/kiki/repos/<repo_id>/recovery/<intent_id>/`, outside the source workspace. At minimum it contains byte copies and hashes of every probe-identified changed or untracked non-ignored path, a path inventory, the working-copy change/commit ids, and the starting operation id. For `Unknown`, it copies every non-ignored workspace path because no narrower dirty set has been proved. It must remain useful even if the next jj command changes repository state. Persist its path and fingerprint on the intent before invoking a mutating jj command. The CLI PoC must prove the concrete mechanism; if it cannot, automatic `NativeRewrite` is not accepted for v1.
3. Run jj's stale-workspace recovery and enumerate every successor/divergent commit for the affected working-copy change id.
4. Verify that the pre-materialization edits are represented either in the materialized commit or in explicitly named recovery/divergent commits.
5. If exactly one recovery successor can be selected safely, make the conflict-bearing result visible in the workspace and resume with conflict framing. Otherwise leave the thread `RecoveryRequired`, preserve the recovery record, and require human selection.
6. Transition `RecoveryRequired → Reconciling → Materialized` only after the selected workspace state visibly contains the edits or after the human explicitly chooses a recovery outcome. Record that choice and the recovery-bundle location in the intent.

The recovery payload names all preserved commit ids and recovery paths. “Work was preserved somewhere in the op log” is insufficient if the agent resumes on files that omit it. Thread lifecycle operations never delete recovery bundles automatically, including close or thread destroy; they surface the paths for manual disposition. The deliberately repo-wide `kk repo unregister` remains the exception: use `--keep-state` to retain the centralized directory and its recovery bundles.

## `ParentAdvance` reconciliation

At the child's safe boundary:

1. Claim the lock and transition the oldest intent `Detected → Reconciling`.
2. Validate that the exact revisions after `from_base_commit` through the current thread head form the v1 single-parent owned chain, with no merge, multiple root, or foreign descendant. Otherwise transition to `TopologyDiverged`; never synthesize a dynamic descendants revset.
3. Probe workspace freshness and edits. `FreshClean` may proceed. A preceding native stale state reconciles through the rules above; `FreshDirty | StaleDirty | Unknown` must create an edit-preserving recovery bundle and enter `RecoveryRequired` before the explicit rebase starts.
4. Persist the planned source revset, starting operation, and exact `to_base_commit` on the intent.
5. Explicitly rebase the exact validated chain through `JjBackend`.
6. Compare starting and result operation views and record `NativeRewrite` intents for other descendant workspaces jj evolved.
7. Reconcile the current child's workspace, inspect conflicts, and determine the actual result commit.
8. Compose the payload and atomically persist the result, anchor, embedded outbox, and `state=Materialized`; update `thread_head_commit_id` to the actual rebased workspace `@` from the exact result operation view; then advance the follows edge's last synchronized base.

The CLI PoC must evaluate jj's `--no-integrate-operation` plus `jj op integrate` as the preferred way to inspect a planned result before integration. Recovery must use exact operation ids, not rerun an ambiguous “rebase onto current parent” command.

## Delivery protocol

Claude Code may dispatch several tool calls from one assistant response and invoke their `PreToolUse` hooks concurrently. A second hook invocation from that batch is not evidence that the model consumed the first hook's synthetic result. Kiki therefore treats the complete tool batch as the delivery boundary, not an individual hook process.

The adapter supplies stable `model_turn_id` and `tool_batch_id` values to `kk-hook`, and a matching `PostToolBatch` event marks that batch complete. Their derivation is adapter-specific and must pass the integration gate in [Build Sequencing](17-build-sequencing.md). If the installed Claude Code version cannot provide or support an unambiguous batch-completion boundary, soft delivery is disabled and kiki uses the hard-restart fallback below.

The first `PreToolUse` admitted for a batch fixes that batch's decision under the reconciliation lock. If no intent is ready, the adapter caches `PassThrough` for the batch and intents detected afterward wait for the next batch; a later sibling hook may not begin reconciliation. If work is ready, kiki writes the complete `SoftBatch` proof and durably fixes `Block(intent_id)` before reconciliation may perform any workspace mutation. It retains the reconciliation lock through that decision and mutation. All sibling calls reuse the fixed decision. This avoids the impossible promise of retracting a tool call that was already admitted before a later hook arrived.

`PassThrough` needs no cascade row, but losing that cache means kiki cannot prove whether another call in the batch was already admitted. The launcher therefore blocks the unknown call, hard-pauses the incarnation without changing the workspace, and starts a replacement incarnation. Pending work is reconciled only after the old batch can no longer be running; if it produces a payload, delivery uses `RestartStartup`. Cache loss may cause a disruptive restart, but never a mid-batch mutation or an indefinite wait for a completion event that may never arrive. An already durable `Block` remains fail-closed and follows its intent instead of this cache-loss path.

On every `PreToolUse` call:

1. Claim the per-thread reconciliation lock and load the active intent proof, incarnation marker, batch admission, and oldest unresolved intent. Handle `RestartStartup` through step 2 before consulting batch admission. Otherwise a cached `PassThrough` returns immediately and newly detected work waits for a later batch; a missing admission cache for an unknown in-flight batch takes the cache-loss restart path above.
2. If the active intent uses `RestartStartup`, acknowledge only when this call names its replacement incarnation and exact `startup_delivery_id`. A match proves this model turn consumed the startup payload; clear that delivery proof and marker atomically, then select the next intent. A missing or mismatched id blocks and fails closed.
3. If an active `SoftBatch` `Block` names this `tool_batch_id`, block the requested tool and never acknowledge it. If the payload is prepared, emit it byte-identically. If the intent is still `Reconciling`, the sibling waits behind the owning reconciliation within the hook budget; an owner crash or timeout keeps the call blocked and enters recovery or hard restart rather than emitting a nonexistent payload or passing through.
4. If an active `SoftBatch` names another batch but has not been durably marked complete, fail closed: block the tool and initiate hard-restart recovery. An absent, crashed, or reordered `PostToolBatch` must never turn into acknowledgement by inference.
5. If the `SoftBatch` is complete, the intent is `Delivered`, and this call's `model_turn_id` is later than the delivered turn, atomically mark it `Acknowledged`, clear the incarnation marker and delivery-proof fields, and then select the next intent. The exact recovered `Materialized` case is defined below. `Reconciling` and `RecoveryRequired` can never be acknowledged. A different batch id alone is insufficient; the adapter must prove a later model turn.
6. Find the oldest unacknowledged prepared intent or oldest `Detected` intent. Before reconciliation or any possible workspace mutation, atomically fix `Block(intent_id)`, set `delivery_mode=SoftBatch`, and bind the current incarnation, model turn, and tool batch. Only then may a `Detected` intent enter `Reconciling`. A crash can therefore leave an incomplete payload, but never changed files without a durable fail-closed batch decision.
7. Once reconciliation has prepared the payload, block this tool call and emit it. Every other call in the same batch follows step 3 and is also blocked. If recovery finds a bound barrier whose payload is not yet prepared, it blocks with generic recovery framing until the exact saved payload exists or hard restart takes over. If no intent or active delivery proof exists, pass through.

`PostToolBatch` never acknowledges an intent. For `PassThrough`, it expires the launcher cache entry. For a `SoftBatch` `Block`, it verifies the active incarnation, turn, and batch tuple and durably sets that proof's `batch_completed_at`. `RestartStartup` does not accept a batch-completion report. A subsequent `PreToolUse` carrying the proof required by its delivery mode performs acknowledgement. Duplicate `PostToolBatch` events are idempotent; stale or mismatched events are logged and ignored.

After stdout emission, `kk-hook` calls `MarkDelivered(intent_id, incarnation_id, model_turn_id, tool_batch_id)`. One SQLite transaction marks the intent `Delivered`, preserves the already-bound barrier, and sets the current runtime incarnation's `delivered_intent_id`. A partial unique index permits only one live incarnation to claim an intent. When v1.x transcript capture is enabled, a separate idempotent projection records at most one visible row through `dedup_key=cascade:<intent_id>`; its failure cannot roll back or block cascade delivery.

An exact completed `SoftBatch` plus a `PreToolUse` carrying a provably later `model_turn_id` is stronger delivery evidence than the best-effort post-stdout RPC. If `MarkDelivered` was lost and the intent is still `Materialized`, the acknowledgement transaction first records recovered delivery using `batch_completed_at`, then performs `Materialized → Acknowledged`, clears the barrier, and schedules the same idempotent transcript projection. Without both the exact completion tuple and later-turn proof, `Materialized` cannot skip delivery and is redelivered or hard-restarted.

The barrier is fail-closed because workspace files may already have changed. If `PostToolBatch` is unavailable, never arrives, or its identity cannot be proved after a hook or daemon crash, kiki hard-pauses and switches the intent to `delivery_mode=RestartStartup`. It creates a replacement incarnation and a one-use `startup_delivery_id` in one transaction, then starts or resumes the harness with the saved payload as its mandatory first input carrying that id. The launcher cannot release the process without that input. A ready handshake proving that the harness accepted the tagged startup input marks the intent `Delivered` and sets the replacement incarnation's `delivered_intent_id`; a crash before the handshake retires that attempt without acknowledgement and retries with a new incarnation and id.

The first `PreToolUse` generated by the replacement process may acknowledge only when it names the replacement incarnation and causally echoes the exact `startup_delivery_id`. That evidence proves the model turn was generated after consuming the startup payload, so the acknowledgement transaction clears the `RestartStartup` proof and incarnation marker before selecting the next intent. It does not require or fabricate a tool-batch id for the startup input. No tool from the interrupted batch is replayed automatically, and a mismatched or absent startup id fails closed.

If the daemon crashes after binding the barrier and changing files but before persisting `Materialized`, every sibling hook still fails closed; restart finds `Reconciling`, probes actual workspace state, and resumes recovery. If it crashes after the atomic `Materialized` transaction, the embedded payload is available for retry. Restart reconstructs the intent's `SoftBatch` or `RestartStartup` proof and validates only that mode's exact evidence. No mutation begins without a durable block decision, no state claims materialization without its explanatory payload, and no unrelated hook arrival claims consumption.

## Worked scenarios

### Scenario 1: clean ancestor rewrite

Thread A evolves from base X1 to X2. jj already rebases B's repository history so X2 is an ancestor of B, while B's disk remains clean and stale. Kiki records `NativeRewrite { from_base: X1, to_base: X2 }`. At B's boundary the probe returns `StaleClean`; kiki runs `jj workspace update-stale`, stores the actual result and embedded payload, and informs the agent.

### Scenario 2: ancestor rewrite after an agent edit

The agent edits B's files, then A evolves X1→X2 before B's next jj snapshot. At B's boundary the probe returns `StaleDirty` or `Unknown`. Kiki hard-pauses, records recovery state, runs stale recovery, and surfaces every divergent successor. It does not resume on a clean X2-based tree that omits the edit.

### Scenario 3: parent adds a revision

Parent `bar` advances from X to X+b1 while child `foo` remains at X+f1. Kiki records `ParentAdvance { from_base: X, to_base: X+b1 }`. At `foo`'s safe boundary it snapshots/reconciles the workspace as required, explicitly rebases the owned stack, stores the result and payload, and informs the agent. Any evolved grandchild receives its own `NativeRewrite` intent.

### Scenario 4: direct human reconciliation

The human runs `jj workspace update-stale` before the managed agent's boundary. This may change files without creating an op-log entry. The original base-transition intent remains pending; at the next boundary the workspace probe returns `FreshClean` or `FreshDirty`, kiki verifies ancestry, stores the observed result, and delivers context without rewriting files again.

### Scenario 5: agent crash after delivery

If an agent receives intent N and crashes before acknowledgement, N remains `Delivered`. Restart retires the old runtime incarnation and incomplete `SoftBatch` proof without acknowledgement, then binds a new `RestartStartup` attempt. The replacement process receives N's embedded payload byte-for-byte with a one-use `startup_delivery_id`, even when the harness conversation id is reused; no replacement-process tool runs first. Its first causally tagged model turn acknowledges N. The agent may see the payload twice across processes, while the transcript projection records it once through `dedup_key=cascade:<intent_id>`.

### Scenario 6: parallel tool batch

One assistant response requests tools T1, T2, and T3 concurrently. T1's hook finds an intent, binds `SoftBatch` to that model turn and batch, and only then materializes the workspace. T1 is blocked and receives the payload. T2 and T3 may already be waiting or may arrive afterward; both observe the same proof, are blocked, and receive the same payload. `PostToolBatch` marks only batch completion. The first `PreToolUse` from a later assistant response acknowledges the intent; neither T2 nor T3 can do so.

## Conflicts and escalation

Conflicts and divergent changes are first-class jj states, not necessarily failed commands. Kiki inspects result revisions and every successor of the affected working-copy change id rather than relying only on process exit status or whichever divergent commit jj happens to place on disk.

Hard escalation is required when:

- a required workspace mutation sees `FreshDirty | StaleDirty | Unknown`;
- reconciliation exposes textual conflicts or divergent successors;
- topology or exact base state cannot be reconciled automatically; or
- an active delivery barrier has no provable batch-completion or later-model-turn boundary; or
- the human invokes `kk thread interrupt`.

## Parent merged

Once the v1.x GitHub polling integration ships, a parent merge records a `ParentAdvance`-shaped transition whose exact `to_base_commit` is the resolved default-branch commit. The child rebases and reconciles at its safe boundary. The approved remote-operation journal then updates the child branch and PR base, and drops the follows link only after local and remote state are observed coherent.

## Parent abandoned

Deleting or moving only the parent's checkpoint bookmark creates `ProjectionDiverged`; it does not change the pinned follows relationship. If an external jj operation abandons the parent live head or owned revisions, or otherwise makes ancestry ambiguous, kiki records `TopologyDiverged` and requires human attention. It does not silently choose a new parent or reinterpret a bookmark as the head.

## Detach and graph surgery

`kk thread detach` removes the follows edge and leaves the child's current ancestry unchanged. It first runs `RefreshToFrontier`, refreshes the parent and child workspace heads from the pinned operation view, and creates any transition a lagging watcher had not yet recorded. The user must reconcile that exact transition or explicitly discard it with one-shot approval. Only then does kiki checkpoint the child's exact live head and delete the edge, preserving the thread-owned base anchor so the independent thread remains publishable, reopenable, and safe to validate later. Broader graph surgery remains deferred beyond v1.
