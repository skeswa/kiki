# Transcript anchoring design note

Transcript rows are anchored to jj change ids so local recall follows the user's mental model of work, not individual rewritten commit hashes.

`change_id` is the primary alignment key. `commit_id` is captured as a historical snapshot but is not maintained-current as the change is amended or rebased.

## Live capture

While kiki is running, JSONL entries are anchored to the workspace's current `@` as known by the op-log watcher.

## Backfill

If kiki was down while an agent ran, entries must not be stamped with whatever `@` happens to be current when kiki restarts. Backfill reconstructs the anchor from per-workspace jj op history.

The per-workspace dimension is required because jj's op log is repo-shared while `@` is workspace-local.

If no reliable anchor exists for an entry, kiki records `anchor_unknown=true`. Anchor-aware queries skip those rows by default; recent and search queries include them.
