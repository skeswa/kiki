# Invariants

These are the promises v1 relies on. They cut across the book; local chapter details should be read in light of them.

## Identity is stable

A thread has a stable `thread_id`. Its live head is the managed workspace's current `@`, persisted as `thread_head_commit_id`; bookmark names, workspace paths, tmux sessions, and harness sessions are projections. They may change. The `thread_id` must not.

This is load-bearing state. Credentials, audit rows, transcript rows, PR links, lifecycle state, and follows links all join through this identity. Code should treat bookmarks as checkpoint and publication handles, not identity or the live source of truth for a running thread.

## External projections fail loud

Kiki observes mutable projections rather than assuming it still owns them. A missing or moved bookmark, missing jj workspace record, mismatched workspace path, or missing tmux session must be classified explicitly. Kiki may repair a projection automatically only when the intended result is provable; otherwise the thread enters `ProjectionDiverged` and waits for `kk repair` or another explicit human choice.

Projection health does not erase capabilities that remain provable. A bookmark-only issue blocks checkpoint, publish, and close but does not stop unambiguous workspace-head tracking or follows classification. A missing managed session still permits head observation but blocks boundary mutation. Only workspace identity or path ambiguity suspends both. Temporary projection changes owned by an in-flight lifecycle journal fail or resume that journal rather than creating a competing state machine.

## Lifecycle work is recoverable

Thread creation, close, reopen, repair, and destroy span SQLite, jj, the filesystem, tmux, and a harness process. They are durable sagas, not cross-system atomic transactions. A crash or failed compensation must leave a persisted journal and honest lifecycle state from which restart recovery or an explicit command can continue. Reopen remains `Closed` until the replacement incarnation's ready handshake commits. No recovery path may leave an apparently `Active` thread whose managed agent and tmux session were already destroyed.

## Workspaces are cooperative isolation

Thread workspaces prevent accidental file interference during normal use. They should not be documented, tested, or presented as filesystem security.

A same-UID process can read sibling workspaces, `~/.config/kiki`, and shared jj repository state. v1 accepts that fact and scopes credentials to reduce accidental blast radius, not to defeat an adversary with the user's privileges.

## Cascade materializes only at safe boundaries

A parent rewrite may cause jj to evolve descendant commits immediately in repository state. Kiki must not redundantly rebase that already-evolved history. It records the exact transition from the last synchronized base to the evolved base, then materializes the child's current jj state only at an agent boundary or quiescence. It does not pin the child's working-copy commit as the target because that commit may legitimately evolve again before the boundary.

When a parent's persisted live head advances by adding a new revision, and the new exact head is not already an ancestor of the child, kiki performs an explicit rebase of the child's owned stack at the same safe boundary. A v1 owned stack must be a provable single-parent chain from the synchronized base to the child's live head; ambiguous, merged, or foreign topology stops as `TopologyDiverged`. It is acceptable for either reconciliation kind to wait for a safe boundary or for `kkd` to become reachable. It is not acceptable for kiki to materialize or explicitly rebase the managed workspace while its agent is mid-edit, and it is not acceptable to silently drop pending reconciliation.

The guarantee is scoped to kiki-controlled mutations for the managed agent. A human who runs `jj` directly in a stale child workspace may explicitly update it before kiki's boundary. That command can alter files without advancing the op-log head, so kiki probes the workspace again at the next boundary rather than relying on watcher events alone. The ambient-coordinator posture does not pretend direct human commands are gated.

Kiki must not make unsnapshotted edits disappear from the visible working tree. Immediately before reconciliation it proves the stale workspace clean, or hard-pauses and enters explicit recovery. Recovery runs outside the source workspace, preserves and enumerates divergent successors, verifies where the edits landed, and resumes only after selecting a result that retains them or obtaining human direction.

For every v1 adapter — Claude Code and Codex alike — kiki exclusively owns the managed session's pre-tool boundary and re-proves that isolation for every process incarnation. It must not race user-defined pre-tool handlers. If one tool in a dispatched batch triggers reconciliation, kiki durably binds `Block` and the complete batch identity before changing the workspace; every tool call in that batch is blocked. Batch completion establishes soft-delivery proof, and only a later model turn may acknowledge the payload. Another concurrent `PreToolUse` from the same batch is never acknowledgement evidence. What a batch is, and how its completion is proved, is an adapter/version proof: Claude Code's parallel batch closes with an explicit completion signal, while Codex's proven-serial dispatch makes each batch a single tool call whose blocked completion is reported by the harness's next turn-scoped hook event — a denied call never runs and fires no post-tool event, so the crash-surviving completion report is the next arrival, which the serial proof shows cannot precede the blocked call's resolution — and whose acknowledgement additionally requires the harness session record's byte-identical delivery receipt, since hook-side write evidence cannot prove the model received the payload rather than a substituted result. If a safe batch boundary cannot be proved, a replacement process receives the saved payload as its first startup message and must prove it processed that message before acknowledgement.

## Cascade delivery is crash-safe

Cascade delivery must be idempotent and crash-safe. The system should prefer a rare duplicate delivery over silently dropping a cascade; when optional transcript projection ships, it must remain idempotent too.

The implementation therefore stores reconciliation, byte-stable delivery payload, acknowledgement, and recovery state on one durable `sync_intent`. It may derive UI state from those rows, but must not maintain a second progress protocol that can disagree with them.

## Operation history is a DAG

jj operations may have multiple parents or temporarily divergent heads. Restart catch-up stores normalized parent edges and traverses every unprocessed ancestor reachable from the observed frontier in topological order. A singular parent column or “last cursor to head” scan is not an acceptable approximation because it can silently skip a workspace transition.

## Human prose is owned by humans

Human-owned revision descriptions, bookmark names, and PR descriptions must not be silently overwritten.

kiki may draft. kiki may refresh when explicitly asked. It must preserve deliberate user prose unless the user opts back into regeneration.

## Transcript storage and egress are explicit

Thread transcripts are stored locally and must not feed externally visible artifacts such as PR descriptions, auto-describe output, or auto-renames. A catch-up sent to a hosted harness or transcript-derived MCP result returned to a hosted model may leave the machine for the configured provider; kiki must disclose that boundary and obtain a remembered, revocable grant bound to the thread, provider, and purpose before egress.

This is a confidentiality rule. Treat it accordingly.

## Authority is explicit

Destructive, cross-thread, sensitive-read, and externally visible daemon actions require a method, target, argument, and rendered-plan-bound one-shot human approval issued through a persisted begin/display/confirm exchange with an enrolled interactive `ApprovalPresenter`. A reusable Admin credential must not be loaded automatically by every `kk` subprocess and cannot replace confirmation for an operational call.

Thread-scoped credentials may operate on their own thread and may read the narrow same-repo summary surface. They must not read sibling transcripts, inspect sibling diffs, or mutate sibling threads.

## State is distinguishable without color

Every state kiki surfaces in any UI must be distinguishable without color. Glyphs and labels carry the signal; color is an accelerator, never the only signal.

Kiki honors `NO_COLOR=1` by emitting no ANSI color sequences. The shared `LogRenderer` and `StatusRenderer` projections must produce monochrome-distinguishable output for every state in the cascade, agent, and lifecycle vocabularies.
