# Op-log watcher

The op-log watcher is `kkd`'s window into jj. It detects external operations (human, agent via Bash, sibling tools) and feeds the cascade orchestrator and the transcript backfill path.

## Mechanism

- `fsnotify` on `.jj/repo/op_heads/` for change detection.
- `jj op log --no-graph -T '...'` cursor-polling as a parsing fallback if fsnotify misses an event.
- 250ms debounce per repo before triggering cascade evaluation.
- Per-op evaluation compares before/after repository views for parent bookmarks and managed workspace commits, then validates actual ancestry for affected follows edges. O(threads × ancestry-depth) per op is acceptable in practice for v1.

## `op_history` cache

Each observed op is persisted as `(repo_id, op_id, workspace_id, committed_at, change_id, commit_id, parent_op_id)` with `UNIQUE (repo_id, op_id, workspace_id)`.

The **per-workspace** dimension is load-bearing. jj's op log is repo-shared, but `@` is per-workspace. One operation may change only A's working-copy commit, or an ancestor rewrite may evolve A, B, and C together while each workspace retains a distinct `@`. A repo-keyed cache cannot answer either “what was workspace B's `@` at this op?” or “which managed workspaces evolved in this op?” The denormalized per-workspace key answers both; transcript backfill looks up the latest `op_history` row WHERE `workspace_id = W AND committed_at <= entry.timestamp`.

Rows are inserted only when an op produces a _new_ `@` for the workspace in question. The lookup's "latest row at or before timestamp" semantics handle gaps correctly.

## Op attribution

`kkd` dedupes its own jj operations by recording every kk-initiated `op_id` in the `op_attribution` table and prefixing the op message with `kk:`. The watcher checks attribution before reacting; self-attributed ops do not re-trigger cascade.

External ops (no `kk:` prefix, op_id not in `op_attribution`) pass through reconciliation classification. Classification is based on state, not command name:

- if the exact evolved parent base is already an ancestor of the managed child's current repository commit, record `NativeRewrite` with the exact old-base → evolved-base ids; the child's before/after commits are evidence, not the pinned target;
- if only the parent bookmark gained a new tip not already in the child's ancestry, record `ParentAdvance` with the exact destination commit;
- if the new topology is ambiguous, backward-moving, conflicted, or inconsistent with the follows edge, record `TopologyDiverged`.

A single external op may logically evolve multiple workspaces in A→B→C. The watcher records a separate base-transition intent for every affected workspace; it does not pretend repository evolution occurred one hop at a time.

The watcher detects repository transitions, not every file materialization. In particular, a direct `jj workspace update-stale` can change a workspace's files without producing a new op-log head. `WorkspaceProbe` at the next managed boundary is therefore the authority on current freshness.

Kiki-initiated explicit advances are `op_attribution`-skipped by the watcher, but their reconciliation handler compares the starting and resulting operation views before completing the intent. Any other workspace jj evolved receives a `NativeRewrite` intent in the same durable result-recording step. See [Cascade](../07-cascade.md) and [Native evolution](../20-decisions/native-evolution.md).

## Daemon-restart catch-up

On daemon restart, the watcher runs an op-log catch-up _before_ the transcript JSONL backfill. The catch-up reads `jj op log` from the last persisted op cursor to the current head, then queries each registered workspace's view at each op:

```
jj -R <workspace_root> --at-op <op_id> log -r '@' --no-graph -T 'change_id ++ " " ++ commit_id ++ "\n"'
```

The `-R <workspace_root>` is load-bearing because jj resolves `@` from the selected workspace; there is no `jj log --workspace` flag to rely on. `kkd` inserts a row for each `(op_id, workspace_id)` pair where `@` differs from the workspace's previous row (idempotent on the unique key).

## Retention

The cache is bounded by `op-log-size × workspace-count`, which jj keeps modest. Retention is the lifetime of the repo's registration.

## Tests

The watcher itself is tested via integration; the _logic_ of op-event interpretation is covered by `AncestryQuery` + `OpAttribution` deep-module tests (see [Testing](../16-testing.md)).
