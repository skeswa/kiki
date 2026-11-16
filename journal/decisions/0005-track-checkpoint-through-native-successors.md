# D-0005: Track the checkpoint bookmark through jj's native successors

- Recorded: 2026-11-16
- Decided by: agent, 2026-11-16, under the owner's instruction to resolve the checkpoint inconsistency explicitly without redefining the checkpoint bookmark as the live head; source: the 2026-10-30 jj experiments and the 2026-11-16 rerun on jj 0.46.0
- Topic: Checkpoint bookmark and projection audit
- Supersedes: the "kiki moves the bookmark only at explicit checkpoints" and fixed expected-target wording in [Thread head and lifecycle sagas](../../docs/reference/book/17-decisions/thread-head-and-sagas.md)
- Superseded by: —

## Decision

A [bookmark](../../docs/reference/book/appendix-a-glossary.md#bookmark) is [jj](https://docs.jj-vcs.dev/latest/)'s named pointer to a commit. Each kiki
[thread](../../docs/reference/book/appendix-a-glossary.md#thread) has one, used as a checkpoint: a saved point to reopen or
publish from.

The checkpoint bookmark stays a checkpoint. Kiki still _places_ it only at
explicit checkpoints, and it is still never the [live head](../../docs/reference/book/appendix-a-glossary.md#live-head) or a
[follows](../../docs/reference/book/appendix-a-glossary.md#follows) target. What changes is the
[expected target](../../docs/reference/book/appendix-a-glossary.md#expected-bookmark-target) between placements. Kiki keeps
four facts apart:

1. **Placement history.** Each explicit checkpoint appends an immutable row:
   the exact commit, change, and operation where kiki put the bookmark.
2. **[Native successor](../../docs/reference/book/appendix-a-glossary.md#native-successor) tracking.** Sometimes jj itself
   carries the bookmark to a rewrite successor of the expected commit. When
   the operation's predecessor record proves that, kiki advances the expected
   target and appends a succession row. No issue is raised.
3. **External movement.** Any other change of target is a
   [projection](../../docs/reference/book/appendix-a-glossary.md#projection-divergence) issue for `kk repair`. That covers a
   different unrelated commit, a conflicted bookmark, divergent successors,
   deletion, or a move without predecessor evidence.
4. **Head advance.** `jj new` or `jj commit` moves `@` and leaves the bookmark
   behind. That is an ordinary relationship, not an issue.

Three refinements followed from probes on jj 0.46.0 the same day:

- `jj undo` of a tracked succession pops the expected target back instead of
  raising an issue.
- A `jj bookmark rename` proven in one local operation is normalized, not
  reported as a deletion.
- A checkpoint targets the live head or, when that head is the empty commit jj
  leaves after `jj commit`, its parent. It refuses to move the bookmark
  backward or sideways. The relationship vocabulary is
  `current | behind | ahead | diverged`.

For an active thread, a successor in a different change is accepted only when
it is the live head or lies on the validated [owned chain](../../docs/reference/book/appendix-a-glossary.md#owned-stack).
Such a successor is the result of `jj split` or of squashing the bookmarked
commit into its parent. For a closed thread only a same-change successor is
accepted, and the archived head advances with it.

## Why

jj bookmarks follow rewrites. The first ordinary edit after `kk new` snapshots
the working copy, rewrites the checkpointed commit, and moves the bookmark to
its successor with no bookmark command. Under the earlier fixed
`checkpoint_commit_id` rule that was `BookmarkMoved`. So every thread would
have entered repair on its first edit, and every closed thread on any ancestor
rewrite. Reproduced on jj 0.44.0 and 0.46.0.

## Alternatives and consequences

- **Require repair for every move.** Keeps the old wording and makes normal use
  unusable.
- **Let the bookmark follow `@`.** Redefines the checkpoint as the live head and
  loses the reopen and publication meaning.
- **Same-change successors only, even when active.** Sends every `jj split` of a
  freshly created thread's first commit to repair, against the promise that
  direct jj use stays ordinary.

Successor tracking depends on jj's operation predecessor record being readable
at an exact operation. Where it is missing, the move is external and goes to
repair.

## Links

- Contract: [Threads](../../docs/reference/book/03-threads.md#thread-identity), [Op-log watcher](../../docs/reference/book/13-architecture/op-log-watcher.md), [State schema](../../docs/reference/book/13-architecture/schema.md)
- Evidence: [Herdr foundations and jj integration](../../docs/research/herdr-jj.md), [2026-11-16 revalidation](../investigations/2026/2026-11-16-herdr-jj-revalidation.md)
- Related: [D-0004](0004-use-herdr-as-terminal-runtime.md)
