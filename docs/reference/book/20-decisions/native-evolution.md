# Native evolution and workspace materialization

## Decision

Kiki distinguishes jj repository evolution from on-disk workspace materialization.

When an ancestor revision is rewritten, jj may immediately evolve descendant commits and the working-copy commit recorded for another workspace. The other workspace's files can remain stale. Kiki compares before/after operation views and the follows edge's last synchronized base, then records a `NativeRewrite` containing the exact `from_base_commit → to_base_commit` transition. It waits for the managed agent's safe boundary, verifies that the current child still descends from `to_base_commit`, and materializes the child's current jj state. It does not rebase history jj already evolved or pin a child working-copy commit that may evolve again before the boundary.

When a parent bookmark gains a new tip that is not already an ancestor of the following child, jj has no knowledge of kiki's follows edge. Kiki records a `ParentAdvance` intent and explicitly rebases the child's owned stack onto the exact parent commit at the child's safe boundary.

## Why

The earlier design treated both cases as delayed explicit rebases. That model conflicts with jj's native descendant evolution: by the time the op-log watcher sees an ancestor rewrite, the repository may already contain successor commits for every descendant workspace. Running another generic rebase is redundant at best and targets the wrong state at worst.

The revised model gives each layer one job:

- jj owns revisions, successor commits, operation history, and stale-workspace detection;
- kiki owns follows intent, exact-base-transition classification, safe materialization, edit recovery, agent explanation, and acknowledgement.

## Multi-hop consequence

Repository evolution does not pretend to move one follows edge at a time. A single jj operation may logically evolve B and C in A→B→C. Kiki records separate materialization intents for every affected workspace, and each workspace moves on disk only at its own managed-agent boundary.

An explicit `ParentAdvance` on B may likewise cause jj to evolve C. C receives `NativeRewrite`, not a second explicit rebase.

## Direct jj limitation

Kiki remains an ambient coordinator. A human may run `jj` directly in a stale child workspace, and that command may materialize the new state before kiki's boundary. Some materialization changes files without producing a new op-log head, so the watcher alone cannot observe it. The hard guarantee is therefore about kiki-controlled mutations for the managed agent, not about gatekeeping every same-UID process. Kiki probes current workspace state at every boundary and informs the agent even when there was no new operation.

## Unsnapshotted edits

`jj workspace update-stale` can preserve unsnapshotted edits in a divergent or conflicted successor while placing a different clean successor on disk. Treating command success as successful recovery would therefore hide work from the managed agent.

Immediately before materialization, kiki runs a non-mutating `WorkspaceProbe`. `FreshClean` and `FreshDirty` need no update for a `NativeRewrite`; `StaleClean` may take the normal materialization path. Any dirty or indeterminate state that must be mutated enters `RecoveryRequired`, hard-pauses the agent, and runs `WorkspaceRecovery` outside the source workspace. Recovery first saves a byte-and-hash bundle of changed and untracked non-ignored paths, then invokes jj's stale-workspace recovery, enumerates all divergent successors, verifies where the edits landed, and selects a conflict-bearing result only when edit preservation can be proved. Ambiguity requires human selection. Kiki never resumes the agent in a clean working tree that merely makes the edits harder to find.

## Implementation gate

The CLI proof of concept must validate `WorkspaceProbe`, `jj workspace update-stale`, divergent-successor enumeration, and the `--no-integrate-operation` / `jj op integrate` flow with unsnapshotted edits, conflicts, concurrent operations, daemon crashes, direct materialization with no new op-log head, and multi-workspace descendant evolution before the production `JjBackend` contract is frozen.
