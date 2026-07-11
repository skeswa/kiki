# Crate layout

kiki is a Cargo workspace with four crates. The split exists so the gRPC service surface is a real seam: `kkd` is the only privileged process, and every UI is a client of the same protocol.

| Crate       | Kind    | Responsibility                                                                  |
| ----------- | ------- | ------------------------------------------------------------------------------- |
| `kiki-core` | library | shared types, traits, generated proto types, sqlite migrations. No I/O.         |
| `kkd`       | binary  | the daemon. Owns all state and behavior. gRPC server.                           |
| `kk`        | binary  | the CLI. Hosts the TUI as a subcommand. Pure client of the gRPC service.        |
| `kk-hook`   | binary  | the PreToolUse sidecar invoked by Claude Code. Pure client of the gRPC service. |

## Why four crates

`kiki-core` is a pure library with no I/O so types and traits can be shared between `kkd` and clients without dragging in tokio/tonic runtime concerns. `kkd` is the only crate that opens sqlite or shells out to `jj`, `gh`, or `tmux`. `kk` and `kk-hook` are both clients of the same gRPC contract — there is no privileged internal API. A future native or web UI joins as a fifth client of the same surface.

## Internal layout inside `kkd`

`kkd` is one daemon binary but is split-by-concern internally. A `ThreadController` owns each thread's lifecycle and dies with the thread; a small set of cross-cutting components own daemon-wide concerns:

- `OpLogWatcher` — fsnotify on `.jj/repo/op_heads/`, populates normalized operation nodes, parent edges, workspace projections, and the observed frontier. See [`op-log-watcher.md`](op-log-watcher.md).
- `CascadeOrchestrator` — per-thread reconciliation lock; classify native rewrite versus parent advance; materialize; hold the parallel-batch delivery barrier; acknowledge only from a later model turn.
- `ProjectionReconciler` — compare stable identity with workspace, bookmark, path, and tmux projections; auto-normalize only unique identity-preserving drift; produce named `kk repair` plans otherwise.
- `MetadataLedger` + `AICompose` (v1.x) — auto-describe / auto-rename ownership tracking and prompt assembly.
- `GitHubBackend` (v1.x; default `GhCli` impl) — PR creation, status polling, comment surfacing.
- `ConfigLoader` — the acceptance slice's minimal daemon/harness/path/notification keys; v1.x adds the full layered TOML and per-thread SQLite surface enumerated in [Configuration](../13-configuration.md).
- `AuthEnforcer` + approval broker — `ThreadScoped` checks for ordinary work, persisted begin/display/confirm challenges and one-shot plan-bound `HumanApproval` for consequential operations, and Admin only for bootstrap or foreground-presenter enrollment.
- `ThreadTranscriptStore` (v1.x) — JSONL tail, projection, FTS5 read API, and provider-egress consent state.
- `JjBackend` — v1 `JjCli` implementation shells out to `jj` and parses structured template output. A later `JjLib` implementation can swap behind the same trait.

This split keeps "killing thread foo's tmux session" from becoming entangled with global daemon state and leaves room to extract per-thread supervisors into separate processes later without rewriting business logic.

## Stack

- Rust, edition decided by the implementer at first build.
- `tonic` for the gRPC server and client codegen.
- `rusqlite` (or `sqlx` with the sqlite feature) for state.
- `ratatui` for the overlay TUI and the persistent sidebar.
- `clap` for CLI parsing.

## The Bun/TypeScript bootstrap

The repo is currently bootstrapped as a Bun + TypeScript project (`package.json`, `tsconfig.json`, `index.ts` placeholder). Implementation will be Rust per the original architectural decision; the Bun bootstrap is a placeholder pending the first real `kkd` commit.
