# Build Sequencing

The riskiest v1 assumption is the cascade path across jj native descendant evolution, stale-workspace materialization, explicit parent-tip advance, and Claude Code's PreToolUse boundary. Validate that before investing in the full daemon.

## Proof of concept

Before committing to the full architecture, build a one-shot proof of concept:

1. Create two jj workspaces sharing a parent revision.
2. Run a Claude Code agent in the descendant workspace.
3. Amend the ancestor revision from the parent workspace and prove that jj evolves the descendant in repository state while leaving its files stale.
4. Prove that kiki can classify that exact base transition as `NativeRewrite` without pinning the volatile child tip, then use `WorkspaceProbe` to distinguish `FreshClean`, `FreshDirty`, `StaleClean`, `StaleDirty`, and `Unknown` at a PreToolUse boundary.
5. Advance the parent with a new tip and prove that kiki classifies `ParentAdvance`, explicitly rebases the child's owned stack onto the exact commit, and materializes the result at the boundary.
6. Prove that A→B→C repository evolution can affect multiple descendant commits at once while B and C materialize independently at their own boundaries.
7. Prove clean native materialization and direct human materialization with no new op-log head. For unsnapshotted edits, create an external recovery bundle, enumerate divergent successors, and prove kiki never resumes on a clean tree that hides the edits.
8. Evaluate `--no-integrate-operation` plus `jj op integrate` as the planned-rebase mechanism, including conflicts, concurrent operations, and crash recovery.
9. Prove that one `sync_intent` owns reconciliation, embedded payload, delivery, and acknowledgement through crash injection at every transition.
10. Prove that the agent receives a synthetic result, re-reads affected files, and continues coherently.

The PoC needs no daemon, no TUI, and no polished CLI. Shell scripts are enough. It should answer whether the hardest coordination primitive is real.

## First commit

Scaffold the Rust workspace:

- `kiki-core` library;
- `kkd` daemon binary;
- `kk` CLI binary;
- `kk-hook` sidecar binary.

Get gRPC over a unix socket working end-to-end with a ping/pong call and one test.

## First feature slice

After the PoC:

1. `kk init`
2. `kk new <name>`
3. `kk switch <name>`
4. jj workspace creation
5. bookmark creation
6. tmux session creation
7. Claude Code spawn

This slice should spawn a thread, attach to it, and start the agent. No cascade, AI metadata, publish flow, or TUI is required.

## Foundation order

Build upward in this order:

1. `OpLogWatcher`, `OpAttribution`, and `AncestryQuery`.
2. `CascadeOrchestrator` base-transition classification, `WorkspaceProbe`/`WorkspaceRecovery`, intent-owned delivery, native materialization, and explicit advance integrated with `kk-hook`.
3. `MetadataLedger` ownership foundation.
4. `ConfigLoader` layering and `kk config`.
5. `kk publish` stack flow with editor integration.
6. `LogRenderer`, `StatusRenderer`, `kk log`, and `kk status`.
7. Transcript capture, read API, and reopen catch-up.
8. `kk thread detach` as the graph-surgery escape hatch.

v1.x polish (enumerated in [Orientation](01-orientation.md)) builds on top of that, in this order:

1. Overlay TUI using gRPC plus shared renderers.
2. Persistent sidebar pane.
3. PR merge polling and auto-archive.

## Acceptance slice

v1 is real when these work together against a real jj+git repo, tmux, Claude Code, and `gh`:

1. Thread lifecycle: `kk init`, contextual `kk new`, `kk switch`, `kk close`, and `kk reopen`.
2. Safe cascade: native jj evolution is materialized without redundant rebasing, new parent tips explicitly advance following children at a Claude Code PreToolUse boundary, and both paths deliver kiki-authored context with retry and conflict handling.
3. Publish: `kk publish` publishes stacks top-down and keeps PR text human-owned after creation.
4. Recall and orientation: transcript capture, `kk thread transcript`, `kk log`, and `kk status`.
5. Configuration: `kk config get|set|unset|edit|show` reads and writes the layered config with source attribution.
6. Escape hatch: `kk thread detach` breaks a follows edge without broader graph surgery.
7. Local-only transcript rule: transcripts feed local recall and reopen catch-up, and do not feed publishing or metadata generation.

The v1.x polish tier deepens the demo. It does not replace the acceptance slice.

## Budget

The expected v1 build budget is:

- acceptance slice: 5-7 weeks;
- v1.x polish: 2-4 additional weeks;
- edge-case buffer: 1-2 weeks.

The buffer belongs to op-log edge cases, hook chaining, jj op-id dedupe, transcript offset behavior, cascade retry paths, and sidebar lifecycle details.
