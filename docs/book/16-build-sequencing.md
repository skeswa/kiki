# Build Sequencing

The riskiest v1 assumption is the cascade path through Claude Code's PreToolUse hook and resume behavior. Validate that before investing in the full daemon.

## Proof of concept

Before committing to the full architecture, build a one-shot proof of concept:

1. Create two jj workspaces sharing a parent revision.
2. Run a Claude Code agent in the descendant workspace.
3. Amend the ancestor revision from the parent workspace.
4. Prove that the descendant can be rebased at a PreToolUse boundary.
5. Prove that the agent receives a synthetic result, re-reads affected files, and continues coherently.

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
2. `CascadeOrchestrator` integrated with `kk-hook`.
3. `MetadataLedger` ownership foundation.
4. `kk publish` stack flow with editor integration.
5. `LogRenderer`, `StatusRenderer`, `kk log`, and `kk status`.
6. Transcript capture, read API, and reopen catch-up.
7. Overlay TUI using gRPC plus shared renderers.
8. Persistent sidebar pane.
9. PR merge polling and auto-archive.

## Acceptance slice

v1 is real when these work together against a real jj+git repo, tmux, Claude Code, and `gh`:

1. Thread lifecycle: `kk init`, contextual `kk new`, `kk switch`, `kk close`, and `kk reopen`.
2. Safe cascade: parent changes rebase following children at a Claude Code PreToolUse boundary, deliver kiki-authored context, and handle retry and conflict paths.
3. Publish: `kk publish` publishes stacks top-down and keeps PR text human-owned after creation.
4. Recall and orientation: transcript capture, `kk thread transcript`, `kk log`, and `kk status`.
5. Local-only transcript rule: transcripts feed local recall and reopen catch-up, and do not feed publishing or metadata generation.

The overlay TUI, persistent sidebar, AI auto-rename polish, and full notification vocabulary deepen the demo. They do not replace the acceptance slice.

## Budget

The expected v1 build budget is:

- acceptance slice: 5-7 weeks;
- stretch/demo polish: 2-4 additional weeks;
- edge-case buffer: 1-2 weeks.

The buffer belongs to op-log edge cases, hook chaining, jj op-id dedupe, transcript offset behavior, cascade retry paths, and sidebar lifecycle details.
