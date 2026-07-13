# Op-log watcher

The op-log watcher is `kkd`'s window into jj. It detects external operations (human, agent via Bash, sibling tools) and feeds the cascade orchestrator and the transcript backfill path.

## Mechanism

- `fsnotify` on `.jj/repo/op_heads/` for change detection.
- `jj op log --no-graph -T '...'` frontier-polling as a parsing fallback if fsnotify misses an event.
- 250ms debounce per repo before triggering cascade evaluation.
- Per-op evaluation compares before/after managed workspace commits and validates actual ancestry for affected follows edges. A live parent's exact workspace `@`/`thread_head_commit_id`, not its bookmark, drives follows classification. Bookmark changes are projection-audit inputs only. O(threads × ancestry-depth) per op is acceptable in practice for v1.

## Operation-DAG cache

Each observed operation node is persisted in `op_history(repo_id, op_id, committed_at, observed_at, processed_at?)`. Operation ancestry is normalized in `op_history_parents(repo_id, op_id, parent_op_id)`, with one row for every parent edge. Per-view workspace state lives in `op_workspace_heads(repo_id, op_id, workspace_id, change_id, commit_id)`. `op_watch_frontier(repo_id, op_id, observed_at)` stores the current known antichain of operation heads. A singular `parent_op_id` or last-op cursor is not an acceptable implementation of this contract.

The **per-workspace** dimension of `op_workspace_heads` is load-bearing. jj's op log is repo-shared, but `@` is per-workspace. One operation may change only A's working-copy commit, or an ancestor rewrite may evolve A, B, and C together while each workspace retains a distinct `@`. A repo-keyed cache cannot answer either “what was workspace B's `@` at this op?” or “which managed workspaces evolved in this op?” Transcript backfill joins `op_workspace_heads` to `op_history` and may use `committed_at <= entry.timestamp` only after restricting candidates to one operation-ancestry path that was observed for that workspace. If incomparable candidates have no unique ancestry maximum, the transcript row is `anchor_unknown`; wall-clock order must not choose an operation branch.

An `op_workspace_heads` row is inserted only when an op produces a _new_ `@` for the workspace in question relative to at least one parent view. The transcript lookup's "latest row at or before timestamp" semantics handle gaps only within the unique ancestry restriction above; timestamps are never used to order or choose between incomparable jj operations.

Whenever a stable workspace id and canonical path identify exactly one managed workspace, insertion of a new workspace `@` and update of `threads.thread_head_commit_id` occur in the same per-repo transaction. This remains true when the thread is `ProjectionDiverged` solely because its bookmark or tmux session is missing or moved: those issues do not make `@` ambiguous and must not freeze follows classification. A missing workspace record/directory or ambiguous path disables head updates until repair. The persisted value is not copied to the bookmark: the expected bookmark target remains `checkpoint_commit_id` until creation completion, publish, close, detach, or an explicit adopt-head repair performs a journaled checkpoint.

## Operation-DAG frontier

Jj operations form a DAG and may have multiple concurrent heads or an integration operation with multiple parents. The watcher therefore maintains the current observed head frontier plus per-node `processed_at`, not a scalar cursor:

1. Read the complete current `op_heads` set and compare it with the durable `op_watch_frontier`; persist newly observed heads before interpretation.
2. Discover every operation reachable from a current head whose `op_history.processed_at` is null or absent, including every parent edge.
3. Process the discovered subgraph in parent-before-child topological layers. Incomparable operations remain incomparable; `committed_at` never fabricates an order between them.
4. For an operation with multiple parents, query each parent's workspace views. If the result differs from more than one parent, classify against the durable follows anchors and normalized trigger set; if there is no single coherent base transition, record `TopologyDiverged` rather than choosing a preferred parent.
5. In the same per-repo transaction as the resulting `op_history`, `op_history_parents`, `op_workspace_heads`, head-cache, attribution, and intent changes, mark every completely interpreted node processed and replace `op_watch_frontier` with the final sampled head antichain.

Crash before the interpretation transaction leaves reachable nodes unprocessed and safely replays them from the persisted or freshly sampled `op_watch_frontier`. Unique keys make replay idempotent. An op integration may coalesce normalized trigger ids into one pre-materialization intent, but never rewrites the operation DAG into a false linear “through” range.

`RefreshToFrontier(repo_id)` is the synchronous form of this algorithm. It repeatedly samples `op_heads`, processes the discovered DAG, and returns a pinned frontier/view only when the sampled head set is unchanged across the final persistence transaction. Detach, parent-close preflight, the post-freeze close proof, and topology-sensitive repair must call it; absence of an existing intent is not freshness evidence.

## Op attribution

`kkd` dedupes its own jj operations by recording every kk-initiated `op_id` in the `op_attribution` table and prefixing the op message with `kk:`. The watcher checks attribution before reacting; self-attributed ops do not re-trigger cascade.

External ops (no `kk:` prefix, op_id not in `op_attribution`) pass through reconciliation classification. Classification is based on state, not command name:

- if the exact evolved parent base is already an ancestor of the managed child's current repository commit, record `NativeRewrite` with the exact old-base → evolved-base ids; the child's before/after commits are evidence, not the pinned target;
- if the parent's exact live head advances to a new tip not already in the child's ancestry, record `ParentAdvance` with that exact destination commit;
- if the new topology is ambiguous, backward-moving, conflicted, or inconsistent with the follows edge, record `TopologyDiverged`.

Moving, deleting, or recreating the parent bookmark never creates `ParentAdvance`. It creates or resolves a bookmark projection issue; follows edges continue to use pinned commits and observed live heads.

### Linear owned-stack validation

Before recording a rebasable `ParentAdvance`, and again immediately before executing it, the classifier validates the v1 owned-stack contract against one pinned operation view. Let `B` be the exact last-synchronized base, `H` the child's exact live head, and `S` the revisions reachable from `H` after excluding ancestors of `B`. Kiki requires:

1. `B` is an ancestor of `H`.
2. `S` has exactly one root and that root's sole parent is `B`.
3. Every revision in `S` has one parent and forms one uninterrupted chain to `H`; merges, multiple roots, and conflicted topology fail validation.
4. Descendants of `S` outside that chain are completely accounted for by recursively valid registered follows children. Any unregistered or ambiguous descendant is foreign topology.

The explicit rebase names the exact validated members of `S`; it never uses a dynamic all-descendants selector. Failure of any condition records `TopologyDiverged` on the intent with the pinned evidence. Kiki does not choose a likely root, silently absorb a revision, or perform a partial rebase. If the discrepancy concerns a missing/moved external projection rather than revision ancestry, it records `ProjectionDiverged` as described below.

A single external op may logically evolve multiple workspaces in A→B→C. The watcher records a separate base-transition intent for every affected workspace; it does not pretend repository evolution occurred one hop at a time.

The watcher detects repository transitions, not every file materialization. In particular, a direct `jj workspace update-stale` can change a workspace's files without producing a new op-log head. `WorkspaceProbe` at the next managed boundary is therefore the authority on current freshness.

Kiki-initiated explicit advances are `op_attribution`-skipped by the watcher, but their reconciliation handler compares the starting and resulting operation views before completing the intent. Any other workspace jj evolved receives a `NativeRewrite` intent in the same durable result-recording step. See [Cascade](../07-cascade.md) and [Native evolution](../20-decisions/native-evolution.md).

## Projection audit: detect broadly, repair narrowly

The op-log watcher feeds a companion projection audit because not every projection failure is represented by a jj operation. The audit runs at daemon boot, after op-log catch-up, for every `kk ls`, before switch/lifecycle commands, and after relevant filesystem or tmux notifications. It compares stable database identity with observed jj workspace records, canonical paths, bookmark targets, and tmux sessions.

At minimum it records these durable `thread_projection_issues`:

- `WorkspaceDirectoryMissing`
- `WorkspaceRecordMissing`
- `WorkspacePathMismatch`
- `BookmarkMissing`
- `BookmarkMoved`
- `SessionMissing`

Detection records expected and observed values before notification and moves an otherwise coherent `Active` or `Closed` thread to `ProjectionDiverged`, preserving the prior lifecycle as the repair target. Audits are lifecycle-sensitive: a closed thread is expected to lack a workspace and session, but still requires its checkpoint bookmark. The audit may automatically resolve only a unique identity-preserving normalization—for example, a lexical-path mismatch where the stable jj workspace id resolves to the same filesystem object. Recreating a workspace record, adopting or restoring a bookmark target, adopting a moved directory, or restarting a session requires an explicit `kk repair` choice recorded in the issue and lifecycle journals. Missing state is never interpreted as a successful close, and a missing session is never reported as a live `Active` agent.

Projection divergence is not a blanket observation embargo. The audit derives capabilities per issue:

| Issue                                                                   | Safe observation while unresolved                                                                      | Mutations blocked                                                                                              |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| `BookmarkMissing` / `BookmarkMoved`                                     | continue exact workspace-`@` history and follows-parent classification                                 | checkpoint, publish, close, detach until the bookmark plan is resolved                                         |
| `SessionMissing`                                                        | continue exact workspace-`@` history and follows-parent classification                                 | agent-boundary delivery and workspace materialization; lifecycle mutation except an approved no-session repair |
| uniquely identified `WorkspacePathMismatch`                             | continue observation through the stable workspace id while the automatic canonicalization plan commits | path-dependent workspace mutation                                                                              |
| `WorkspaceDirectoryMissing` / `WorkspaceRecordMissing` / ambiguous path | no workspace-head observation is claimed                                                               | all workspace and follows-source mutation                                                                      |

An unresolved issue may still block a thread from acting as a cascade child even while its exact head safely acts as a follows source. Consumers must request the specific capability they need; they must not branch only on `lifecycle == Active`.

Lifecycle sagas own their expected temporary mismatches. The audit consults the exact lifecycle operation and completed-step journal before raising an issue so that a bookmark move during checkpoint or a missing tmux session after the journaled close kill is not misclassified. An unexpected mismatch first fails that operation. Compensation either restores the operation's coherent `Active` or `Closed` target, or records a normal projection issue with that stable resume lifecycle and enters `ProjectionDiverged`. Transitional states never become an invented projection resume target. Conversely, an unjournaled mismatch cannot be waved away as lifecycle activity.

## Daemon-restart catch-up

On daemon restart, the watcher runs an op-log catch-up _before_ the transcript JSONL backfill. Catch-up applies the operation-DAG frontier algorithm from every durable frontier member to the complete current head set, then queries each registered workspace's view at each discovered op:

```
jj -R <workspace_root> --at-op <op_id> log -r '@' --no-graph -T 'change_id ++ " " ++ commit_id ++ "\n"'
```

The `-R <workspace_root>` is load-bearing because jj resolves `@` from the selected workspace; there is no `jj log --workspace` flag to rely on. `kkd` inserts a row for each `(op_id, workspace_id)` pair where `@` differs from the workspace's previous row (idempotent on the unique key).

## Retention

Workspace-view rows are bounded by `op-log-size × workspace-count`; normalized edges and the small frontier add `O(op-log-size)` state. Retention is the lifetime of the repo's registration.

## Tests

The watcher itself is tested via integration; the _logic_ of op-event interpretation is covered by `AncestryQuery` + `OpAttribution` deep-module tests (see [Testing](../16-testing.md)).
