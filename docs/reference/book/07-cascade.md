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
- the parent bookmark target before and after;
- whether the new exact parent target is an ancestor of the child's repository commit after the operation;
- whether relevant bookmarks, changes, or operation heads are conflicted or divergent.

The result is:

- `NativeRewrite { from_base, to_base, trigger_op }` when the parent target changed and `to_base` is already an ancestor of the child;
- `ParentAdvance { from_base, to_base, trigger_op }` when the parent target changed and `to_base` is not yet an ancestor of the child;
- `AlreadyAligned` when no reconciliation remains;
- `TopologyDiverged { reason }` when the parent moved backward, the follows anchors no longer describe the real topology, or the relevant jj state is conflicted or ambiguous.

Change ids correlate rewritten parent revisions; commit ids pin the exact base transition. Kiki must not resolve “whatever the parent bookmark points to later” as the destination of an older intent.

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
- embedded outbox fields: byte-stable payload, pinned transcript anchor, preparation/delivery/acknowledgement timestamps, and transcript row id;
- optional recovery metadata naming preserved files or divergent commits.

The intent row is the only authority for cascade progress and delivery. There are no mirrored pending/materialized/acknowledged counters, separate context queue, or separate cascade-outbox table. The thread's three-valued UI status is derived from all unresolved intents, with blocking state taking precedence:

- any `RecoveryRequired | TopologyDiverged` → `conflicted`;
- otherwise, any `Detected | Reconciling | Materialized | Delivered` → `pending`;
- no unresolved intent → `in sync`.

Each **runtime agent incarnation** carries only `delivered_intent_id`, identifying the intent most recently emitted to that process and not yet acknowledged. This row has its own kiki UUID; the harness conversation/session id is a separate field and may be reused by `--resume`. Starting a new process retires the prior incarnation and clears its marker without acknowledging the intent, so the first boundary in the resumed process redelivers it.

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
7. Compose the byte-stable payload from the base transition and actual result. In one SQLite transaction, store the result commit, payload, anchor, and `state=Materialized`, and advance the follows edge's last synchronized base.

`jj workspace update-stale` has no exact-target argument and may reconcile to a newer compatible repository view if an external operation lands concurrently. The actual result is authoritative. If it covers a coherent later base transition, kiki records or supersedes the covered intents accordingly; if it does not, kiki stops rather than claiming the older target was materialized exactly.

## Unsnapshotted-edit recovery

A stale workspace with unsnapshotted edits is a normal active-agent race, not an exceptional corruption case. `jj workspace update-stale` may preserve the edits in a divergent/conflicted successor while placing a clean evolved successor on disk. Kiki must never resume the agent on that clean successor while its edits are hidden elsewhere.

Recovery is deliberately loud:

1. Hard-pause the agent before materialization.
2. Create a loss-safe recovery bundle through `WorkspaceRecovery` at `~/.kiki/repos/<repo_id>/recovery/<intent_id>/`, outside the source workspace. At minimum it contains byte copies and hashes of every probe-identified changed or untracked non-ignored path, a path inventory, the working-copy change/commit ids, and the starting operation id. For `Unknown`, it copies every non-ignored workspace path because no narrower dirty set has been proved. It must remain useful even if the next jj command changes repository state. Persist its path and fingerprint on the intent before invoking a mutating jj command. The CLI PoC must prove the concrete mechanism; if it cannot, automatic `NativeRewrite` is not accepted for v1.
3. Run jj's stale-workspace recovery and enumerate every successor/divergent commit for the affected working-copy change id.
4. Verify that the pre-materialization edits are represented either in the materialized commit or in explicitly named recovery/divergent commits.
5. If exactly one recovery successor can be selected safely, make the conflict-bearing result visible in the workspace and resume with conflict framing. Otherwise leave the thread `RecoveryRequired`, preserve the recovery record, and require human selection.
6. Transition `RecoveryRequired → Reconciling → Materialized` only after the selected workspace state visibly contains the edits or after the human explicitly chooses a recovery outcome. Record that choice and the recovery-bundle location in the intent.

The recovery payload names all preserved commit ids and recovery paths. “Work was preserved somewhere in the op log” is insufficient if the agent resumes on files that omit it. Thread lifecycle operations never delete recovery bundles automatically, including close or thread destroy; they surface the paths for manual disposition. The deliberately repo-wide `kk repo unregister` remains the exception: use `--keep-state` to retain the centralized directory and its recovery bundles.

## `ParentAdvance` reconciliation

At the child's safe boundary:

1. Claim the lock and transition the oldest intent `Detected → Reconciling`.
2. Validate that the recorded owned stack and `from_base_commit` still match actual ancestry. Otherwise transition to `TopologyDiverged`.
3. Probe workspace freshness and edits. `FreshClean` may proceed. A preceding native stale state reconciles through the rules above; `FreshDirty | StaleDirty | Unknown` must create an edit-preserving recovery bundle and enter `RecoveryRequired` before the explicit rebase starts.
4. Persist the planned source revset, starting operation, and exact `to_base_commit` on the intent.
5. Explicitly rebase the child's owned stack through `JjBackend`.
6. Compare starting and result operation views and record `NativeRewrite` intents for other descendant workspaces jj evolved.
7. Reconcile the current child's workspace, inspect conflicts, and determine the actual result commit.
8. Compose the payload and atomically persist the result, anchor, embedded outbox, and `state=Materialized`; then advance the follows edge's last synchronized base.

The CLI PoC must evaluate jj's `--no-integrate-operation` plus `jj op integrate` as the preferred way to inspect a planned result before integration. Recovery must use exact operation ids, not rerun an ambiguous “rebase onto current parent” command.

## Delivery protocol

On each PreToolUse call:

1. If this runtime incarnation has `delivered_intent_id`, atomically mark that intent `Acknowledged`, write/drain any corresponding transcript state, and clear the marker.
2. Find the oldest unacknowledged intent whose payload is prepared. Re-emit its embedded payload byte-identically, regardless of whether another session previously delivered it.
3. Otherwise reconcile the oldest `Detected` intent.
4. If reconciliation produces `Materialized`, emit its embedded payload.
5. If no work exists, pass through to the tool.

After stdout emission, `kk-hook` calls `MarkDelivered(intent_id)`. One SQLite transaction writes the visible transcript row idempotently, marks the intent `Delivered`, and sets the current runtime incarnation's `delivered_intent_id`. A partial unique index permits only one live incarnation to claim an intent. Process restart retires and clears the old claim without acknowledging it before retry.

If the daemon crashes after changing files but before persisting `Materialized`, restart finds the intent in `Reconciling`, probes actual workspace state, and resumes recovery. If it crashes after the atomic `Materialized` transaction, the embedded payload is already available for retry. No state can claim materialization without carrying the payload that explains it.

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

If an agent receives intent N and crashes before acknowledgement, N remains `Delivered`. Restart retires the old runtime incarnation and its marker without acknowledgement; the replacement incarnation's next PreToolUse re-emits N's embedded payload byte-for-byte, even when the harness conversation id is reused. The agent may see it twice across processes; the transcript records it once through `dedup_key=cascade:<intent_id>`.

## Conflicts and escalation

Conflicts and divergent changes are first-class jj states, not necessarily failed commands. Kiki inspects result revisions and every successor of the affected working-copy change id rather than relying only on process exit status or whichever divergent commit jj happens to place on disk.

Hard escalation is required when:

- a required workspace mutation sees `FreshDirty | StaleDirty | Unknown`;
- reconciliation exposes textual conflicts or divergent successors;
- topology or exact base state cannot be reconciled automatically; or
- the human invokes `kk thread interrupt`.

## Parent merged

When a parent merges, kiki records a `ParentAdvance`-shaped transition whose exact `to_base_commit` is the resolved default-branch commit. The child rebases and reconciles at its safe boundary. Kiki then force-pushes with `--force-with-lease`, updates the child PR base, and drops the follows link only after local and remote updates succeed.

## Parent abandoned

If an external jj operation abandons a parent bookmark or makes the follows topology ambiguous, kiki records `TopologyDiverged` and requires human attention. It does not silently choose a new parent.

## Detach and graph surgery

`kk thread detach` removes the follows edge and leaves the child pinned at its last synchronized base. If an unresolved intent exists, detach must show the exact base transition and require the user to reconcile it first or explicitly discard the follows intent. Broader graph surgery remains deferred beyond v1.
