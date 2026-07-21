# Invariants

These are the promises v1 relies on. They cut across the whole book. Each chapter's local details should be read in light of them.

## Identity is stable

Every thread has one stable ID: `thread_id`. A thread is kiki's unit of work — a themed sequence of jj revisions. Its live head is the current `@` of its managed workspace. In jj (the version-control tool kiki drives), `@` names the working-copy commit: the change being edited right now. kiki persists that head as `thread_head_commit_id`. Everything else — bookmark names, workspace paths, tmux sessions, harness sessions — is a projection: an outward reflection of the thread, not the thread itself. Projections may change. The `thread_id` must not.

This identity is load-bearing state. Credentials, audit rows, transcript rows, PR links, lifecycle state, and follows links all join through it. Code should treat a bookmark like a bookmark left in a book: it marks a checkpoint or a publication point, not the page you are actually on. A bookmark is not identity, and it is not the live source of truth for a running thread.

## External projections fail loud

Projections are mutable, so kiki observes them instead of assuming it still owns them. A missing or moved bookmark, a missing jj workspace record, a mismatched workspace path, or a missing tmux session must each be classified explicitly. kiki may repair a projection automatically only when it can prove what the correct result is. Otherwise the thread enters `ProjectionDiverged` and waits for `kk repair` or another explicit human choice.

A broken projection does not erase the capabilities kiki can still prove. If only the bookmark is bad, checkpoint, publish, and close are blocked, but unambiguous workspace-head tracking and follows classification keep working. If the managed session is missing, kiki can still observe the head, but boundary mutation is blocked. Only ambiguity about the workspace's identity or path suspends both. If an in-flight lifecycle journal owns a temporary projection change, that change fails or resumes the journal; it does not create a competing state machine.

## Lifecycle work is recoverable

Creating, closing, reopening, repairing, and destroying a thread each touch SQLite, jj, the filesystem, tmux, and a harness process. These operations are durable sagas — multi-step jobs that record their progress as they go — not atomic transactions across systems. If a step crashes, or a compensating cleanup step fails, kiki must leave behind a persisted journal and an honest lifecycle state. Restart recovery or an explicit command can then continue from that record. A reopened thread stays `Closed` until the replacement incarnation's ready handshake commits. No recovery path may leave a thread that looks `Active` after its managed agent and tmux session were already destroyed.

## Workspaces are cooperative isolation

Each thread gets its own workspace so threads do not trample each other's files during normal use. That isolation is cooperative, not security. It should not be documented, tested, or presented as filesystem security.

Any process running as the same user can read sibling workspaces, `~/.config/kiki`, and shared jj repository state. v1 accepts that fact. Credential scoping exists to shrink the blast radius of accidents, not to defeat an adversary who already has the user's privileges.

## Cascade materializes only at safe boundaries

A cascade is how a change in a parent thread reaches the child threads that follow it. When a parent commit is rewritten, jj may immediately evolve the descendant commits in repository state on its own. kiki must not redundantly rebase history that jj already evolved. Instead, it records the exact transition — from the last synchronized base to the evolved base — and materializes the child's current jj state only at an agent boundary or at quiescence (a moment when the agent is idle). It does not pin the child's working-copy commit as the target, because that commit may legitimately evolve again before the boundary.

The other case is a head advance. When a parent's persisted live head advances by adding a new revision, and that exact new head is not already an ancestor of the child, kiki performs an explicit rebase of the child's owned stack at the same kind of safe boundary. In v1, an owned stack must be a provable single-parent chain from the synchronized base to the child's live head. If the topology is ambiguous, merged, or foreign, kiki stops and marks the thread `TopologyDiverged`. Waiting is acceptable: either reconciliation kind may wait for a safe boundary or for `kkd` (the kiki daemon) to become reachable. Two things are not acceptable: kiki must not materialize or explicitly rebase the managed workspace while its agent is mid-edit, and it must not silently drop pending reconciliation.

This guarantee covers kiki-controlled mutations for the managed agent, and only those. A human may run `jj` directly in a stale child workspace and explicitly update it before kiki's boundary. That command can change files without advancing the head of the op-log (jj's operation log), so kiki probes the workspace again at the next boundary instead of relying on watcher events alone. kiki is an ambient coordinator; it does not pretend direct human commands are gated.

kiki must not make unsnapshotted edits — file changes jj has not yet recorded — disappear from the visible working tree. Immediately before reconciliation, kiki proves the stale workspace is clean, or it hard-pauses and enters explicit recovery. Recovery runs outside the source workspace. It preserves and enumerates divergent successors, verifies where the edits landed, and resumes only after selecting a result that retains them or obtaining human direction.

Delivery rides on the harness's pre-tool boundary: the hook that fires before an agent's tool call runs. For every v1 adapter — Claude Code and Codex alike — kiki exclusively owns that boundary in the managed session, and it re-proves that exclusive ownership for every process incarnation. It must not race user-defined pre-tool handlers. A batch is the set of tool calls the harness dispatches together. If one tool in a dispatched batch triggers reconciliation, kiki durably binds `Block` and the complete batch identity before it changes the workspace. Every tool call in that batch is blocked. Batch completion establishes soft-delivery proof — evidence the payload reached the harness. Only a later model turn may acknowledge the payload. Another concurrent `PreToolUse` event from the same batch is never acknowledgement evidence.

What counts as a batch, and how its completion is proved, is an adapter/version proof. Claude Code dispatches tools in parallel, and its batch closes with an explicit completion signal. Codex dispatches tools serially, and that serial behavior is itself proven, so each Codex batch is a single tool call. A denied Codex call never runs and fires no post-tool event. The crash-surviving completion report is therefore the next turn-scoped hook event to arrive, and the serial proof shows that event cannot precede the blocked call's resolution. Codex acknowledgement requires one thing more: the harness session record must contain a byte-identical delivery receipt, because hook-side write evidence cannot prove the model received the payload rather than a substituted result. If a safe batch boundary cannot be proved, a replacement process receives the saved payload as its first startup message, and it must prove it processed that message before acknowledgement.

## Cascade delivery is crash-safe

Cascade delivery must be idempotent and crash-safe. Idempotent means running it twice has the same effect as running it once. The system should prefer a rare duplicate delivery over silently dropping a cascade. When optional transcript projection ships, it must remain idempotent too.

The implementation therefore stores reconciliation state, the byte-stable delivery payload, acknowledgement, and recovery state on one durable `sync_intent`. It may derive UI state from those rows, but it must not maintain a second progress protocol that can disagree with them.

## Operation history is a DAG

jj records every repository operation in a log. That history is a DAG — a directed acyclic graph, not a straight line. An operation may have multiple parents, and heads may temporarily diverge. Restart catch-up therefore stores normalized parent edges and traverses every unprocessed ancestor reachable from the observed frontier, in topological order. A singular parent column, or a "last cursor to head" scan, is not an acceptable approximation, because either one can silently skip a workspace transition.

## Human prose is owned by humans

Revision descriptions, bookmark names, and PR descriptions that a human wrote must not be silently overwritten.

kiki may draft. kiki may refresh when explicitly asked. It must preserve deliberate user prose unless the user opts back into regeneration.

## Transcript storage and egress are explicit

kiki stores thread transcripts locally. Transcripts must not feed externally visible artifacts such as PR descriptions, auto-describe output, or auto-renames. Some flows do send data out: a catch-up sent to a hosted harness, or a transcript-derived MCP result returned to a hosted model, may leave the machine for the configured provider. Before that happens, kiki must disclose the boundary and obtain a grant that is remembered, revocable, and bound to the thread, the provider, and the purpose.

This is a confidentiality rule. Treat it accordingly.

## Authority is explicit

Some daemon actions are high-stakes: destructive actions, cross-thread actions, sensitive reads, and externally visible actions. Each one requires a one-shot human approval bound to the method, target, arguments, and rendered plan, issued through a persisted begin/display/confirm exchange with an enrolled interactive `ApprovalPresenter`. A reusable Admin credential must not be loaded automatically by every `kk` subprocess, and it cannot replace confirmation for an operational call.

Thread-scoped credentials may operate on their own thread and may read the narrow same-repo summary surface. They must not read sibling transcripts, inspect sibling diffs, or mutate sibling threads.

## State is distinguishable without color

Every state kiki surfaces in any UI must be distinguishable without color. Glyphs and labels carry the signal. Color is an accelerator, never the only signal.

kiki honors `NO_COLOR=1` by emitting no ANSI color sequences. The shared `LogRenderer` and `StatusRenderer` projections must produce monochrome-distinguishable output for every state in the cascade, agent, and lifecycle vocabularies.
