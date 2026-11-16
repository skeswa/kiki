# Transcript anchoring design note

The [thread transcript](../appendix-a-glossary.md#thread-transcript) is kiki's locally stored record of the conversation in a thread. Each row is "anchored": tied to the piece of work it was about.

Transcript rows are anchored to [jj](https://docs.jj-vcs.dev/latest/) [change ids](https://docs.jj-vcs.dev/latest/glossary/), so local recall follows the user's mental model of work, not individual rewritten commit hashes. (In jj, a change keeps the same change id when it is rewritten, while each rewrite gets a new commit id.)

`change_id` is the primary alignment key. `commit_id` is captured as a historical snapshot. It is not maintained-current as the change is amended or rebased.

## Live capture

While kiki is running, [JSONL](https://jsonlines.org/) entries are anchored to the [workspace](../appendix-a-glossary.md#workspace)'s current `@` as known by the [op-log](https://docs.jj-vcs.dev/latest/operation-log/) watcher. (`@` is the workspace's current working-copy commit. The op log is jj's record of every operation.)

## Backfill

Backfill means filling in rows for a time when kiki was not running.

If kiki was down while an agent ran, restart-time `@` is the wrong anchor for old entries. Backfill reconstructs the anchor from per-workspace jj op history (see the [operation-history cache](../appendix-a-glossary.md#operation-history-cache)).

The per-workspace dimension is required because jj's op log is repo-shared while `@` is workspace-local.

If no reliable anchor exists for an entry, kiki records [`anchor_unknown=true`](../appendix-a-glossary.md#anchor-unknown-true). Anchor-aware queries skip those rows by default. Recent and search queries include them.
