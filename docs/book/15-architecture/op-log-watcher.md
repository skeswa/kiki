# Op-log watcher

The op-log watcher is `kkd`'s window into jj. It detects external operations (human, agent via Bash, sibling tools) and feeds the cascade orchestrator and the transcript backfill path.

## Mechanism

- `fsnotify` on `.jj/repo/op_heads/` for change detection.
- `jj op log --no-graph -T '...'` cursor-polling as a parsing fallback if fsnotify misses an event.
- 250ms debounce per repo before triggering cascade evaluation.
- Per-op evaluation walks each managed thread's ancestry (cached) to determine impact. O(threads × ancestry-depth) per op — acceptable in practice.

## `op_history` cache

Each observed op is persisted as `(repo_id, op_id, workspace_id, committed_at, change_id, commit_id, parent_op_id)` with `UNIQUE (repo_id, op_id, workspace_id)`.

The **per-workspace** dimension is load-bearing. jj's op log is repo-shared, but `@` is per-workspace, so an op that advances thread A's workspace `@` leaves thread B's workspace `@` unchanged. A repo-keyed cache (one row per op) would have no answer to "what was workspace B's `@` at this op?" The denormalized per-workspace key answers the backfill question directly: to anchor a JSONL entry for thread T (workspace W), look up the latest `op_history` row WHERE `workspace_id = W AND committed_at <= entry.timestamp`.

Rows are inserted only when an op produces a _new_ `@` for the workspace in question. The lookup's "latest row at or before timestamp" semantics handle gaps correctly.

## Op attribution

`kkd` dedupes its own jj operations by recording every kk-initiated `op_id` in the `op_attribution` table and prefixing the op message with `kk:`. The watcher checks attribution before reacting; self-attributed ops do not re-trigger cascade.

External ops (no `kk:` prefix, op_id not in `op_attribution`) pass through to ancestry impact evaluation. If the op affected any descendant thread's ancestry, cascade fires for those descendants.

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
