# Native evolution and workspace materialization

[jj](https://docs.jj-vcs.dev/latest/) is the version-control tool kiki drives. When you rewrite a commit in jj, jj rewrites the commits built on top of it by itself. This note calls that "native evolution". A jj [workspace](../appendix-a-glossary.md#workspace) is a working directory with its own files. Updating those files to match is called [materialization](../appendix-a-glossary.md#materialization). This note records why kiki treats the two as separate events.

## Decision

Kiki distinguishes jj repository evolution from on-disk workspace materialization.

### When an ancestor is rewritten

When an ancestor revision is rewritten, jj may immediately evolve descendant commits and the [working-copy commit](https://docs.jj-vcs.dev/latest/glossary/) recorded for another workspace. The other workspace's files can remain stale (out of date).

Kiki then does the following:

1. It compares before/after operation views and the [follows](../appendix-a-glossary.md#follows) edge's [last synchronized base](../appendix-a-glossary.md#synchronized-base).
2. It records a [`NativeRewrite`](../appendix-a-glossary.md#nativerewrite) containing the exact `from_base_commit → to_base_commit` transition.
3. It waits for the managed agent's [safe boundary](../appendix-a-glossary.md#safe-boundary).
4. It verifies that the current child still descends from `to_base_commit`.
5. It materializes the child's current jj state.

It does not rebase history jj already evolved. It does not pin a child working-copy commit that may evolve again before the boundary.

### When a parent gains a new commit

A parent's persisted workspace head may gain a new commit that is not already an ancestor of the following child. jj has no knowledge of kiki's [follows edge](../appendix-a-glossary.md#follows-edge). So kiki records a [`ParentAdvance`](../appendix-a-glossary.md#parentadvance) intent. It explicitly rebases the child's provably single-parent [owned stack](../appendix-a-glossary.md#owned-stack) onto that exact commit at the child's safe boundary.

The [thread](../appendix-a-glossary.md#thread) [bookmark](../appendix-a-glossary.md#bookmark) is checkpointed separately. It is not treated as the [live head](../appendix-a-glossary.md#live-head), because jj does not move it merely when `jj new` creates a child. jj does move it when the commit it names is rewritten; [D-0005](https://github.com/skeswa/kiki/blob/main/journal/decisions/0005-track-checkpoint-through-native-successors.md) records how kiki tracks that.

## Why

The earlier design treated both cases as delayed explicit rebases. That model conflicts with jj's native descendant evolution. By the time the [op-log](https://docs.jj-vcs.dev/latest/operation-log/) watcher sees an ancestor rewrite, the repository may already contain successor commits for every descendant workspace. Running another generic rebase is redundant at best and targets the wrong state at worst.

The revised model gives each layer one job:

- jj owns revisions, successor commits, operation history, and stale-workspace detection;
- kiki owns follows intent, exact-base-transition classification, safe materialization, edit recovery, agent explanation, and acknowledgement.

## Multi-hop consequence

Repository evolution does not pretend to move one [follows edge](../appendix-a-glossary.md#follows-edge) at a time. A single jj operation may logically evolve B and C in A→B→C. Kiki records separate materialization intents for every affected workspace. Each workspace moves on disk only at its own managed-agent boundary.

An explicit `ParentAdvance` on B may likewise cause jj to evolve C. C receives `NativeRewrite`, not a second explicit rebase.

## Direct jj limitation

Kiki remains an [ambient coordinator](../appendix-a-glossary.md#ambient-coordinator): it watches and reacts, and does not stand between the human and jj. A human may run `jj` directly in a stale child workspace. That command may materialize the new state before kiki's boundary.

Some materialization changes files without producing a new op-log head, so the watcher alone cannot observe it. (On jj 0.46.0 this holds for a clean stale workspace in a non-colocated repository; a [colocated](https://docs.jj-vcs.dev/latest/git-compatibility/) repository records an operation for the same update. Either way an operation is not freshness evidence.)

The hard guarantee is therefore about kiki-controlled mutations for the managed agent. It is not about gatekeeping every same-UID process. Kiki probes current workspace state at every boundary and informs the agent even when there was no new operation.

## Unsnapshotted edits

Unsnapshotted edits are file changes that jj has not yet recorded in a commit.

`jj workspace update-stale` can preserve unsnapshotted edits in a [divergent](https://docs.jj-vcs.dev/latest/glossary/) or conflicted successor while placing a different clean successor on disk. Treating command success as successful recovery would therefore hide work from the managed agent. A bookmark on the affected commit becomes conflicted in the same step.

Immediately before materialization, kiki runs a non-mutating [`WorkspaceProbe`](../appendix-a-glossary.md#workspaceprobe).

- `FreshClean` and `FreshDirty` need no update for a `NativeRewrite`.
- `StaleClean` may take the normal materialization path.
- Any dirty or indeterminate state that must be mutated [hard-pauses](../appendix-a-glossary.md#hard-pause) the agent and runs [`WorkspaceRecovery`](../appendix-a-glossary.md#workspacerecovery) outside the source workspace. The intent enters `RecoveryRequired` in the transaction that records the bundle.

Recovery runs these steps:

1. It first saves a byte-and-hash bundle of changed and untracked non-ignored paths.
2. It then invokes jj's stale-workspace recovery.
3. It enumerates all divergent successors.
4. It verifies where the edits landed.
5. It selects a conflict-bearing result only when edit preservation can be proved.

Ambiguity requires human selection. Kiki never resumes the agent in a clean working tree that merely makes the edits harder to find.

## Later records

Added 2026-11-16. The reasoning above stands. Two later records refine what surrounds it:

- [D-0005](https://github.com/skeswa/kiki/blob/main/journal/decisions/0005-track-checkpoint-through-native-successors.md) tracks the checkpoint bookmark through jj's native rewrite successors. The same native evolution this note describes for commits also carries bookmarks.
- [D-0004](https://github.com/skeswa/kiki/blob/main/journal/decisions/0004-use-herdr-as-terminal-runtime.md) moves terminal hosting to Herdr. The safe boundary stays a harness proof; no terminal observation substitutes for it.

The jj 0.46.0 rerun also established that kiki must read every view at an exact operation id with the working copy ignored, and that no supported command lists all operation heads. The [Op-log watcher](../13-architecture/op-log-watcher.md) chapter carries those contracts.

## Implementation gate

The CLI proof of concept must validate these pieces before the production `JjBackend` contract is frozen:

- `WorkspaceProbe`,
- `jj workspace update-stale`,
- divergent-successor enumeration,
- the [`OpFrontierSampler`](../appendix-a-glossary.md#frontier-sampler), and
- the `--no-integrate-operation` / `jj op integrate` flow.

It must validate them with:

- unsnapshotted edits,
- conflicts,
- concurrent operations,
- [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) crashes,
- direct materialization with no new op-log head, and
- multi-workspace descendant evolution.
