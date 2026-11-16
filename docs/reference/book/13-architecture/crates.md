# Crate layout

kiki is a Cargo workspace with four crates. The split exists so the gRPC service surface is a real seam: `kkd` is the only privileged process, and every UI is a client of the same protocol.

| Crate       | Kind    | Responsibility                                                                                                                                          |
| ----------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kiki-core` | library | shared types, traits, generated proto types, sqlite migrations. No I/O.                                                                                 |
| `kkd`       | binary  | the daemon. Owns all state and behavior. gRPC server.                                                                                                   |
| `kk`        | binary  | the CLI. Hosts the TUI and the pane launcher as subcommands. Pure client of the gRPC service; also a Herdr client for caller-local focus and attach.    |
| `kk-hook`   | binary  | the pre-tool sidecar invoked by the managed harness's hooks (Claude Code and Codex), and its per-thread hook launcher. Pure client of the gRPC service. |

## Why four crates

`kiki-core` is a pure library with no I/O so types and traits can be shared between `kkd` and clients without dragging in tokio/tonic runtime concerns. `kkd` is the only crate that opens sqlite, shells out to `jj` or `gh`, starts the dedicated Herdr server with the `herdr` executable, or drives that server's JSON socket to provision, observe, and close terminal groups. `kk` and `kk-hook` are both clients of the same gRPC contract — there is no privileged internal API. `kk` additionally talks to the dedicated Herdr server as a viewer: `TerminalClient` requests caller-local focus and, for `kk attach`, runs `herdr` in its connect-only client mode after `kkd` has ensured the server. That path carries no kiki authority and mutates no kiki state.

The pane launcher is a hidden subcommand of the `kk` binary, not a fifth crate. Herdr starts it by direct argv as the PTY child of every role pane. It is a pure gRPC client and makes no launch decision of its own. `kkd` computes each launch specification — argv, environment, settings paths — through the harness adapter; the launcher only executes that specification and supervises the child. It reports its Herdr ids and blocks on its gate. The `agent` launcher holds one supervision stream to `kkd` for its whole life; on each gate it creates the harness child held before exec, reports the child's pid, releases it once `kkd` has recorded its identity, later reports its exit, and awaits the next incarnation's gate. The `shell` and `ui` launchers are released by their role-claim transaction and then replace themselves with the user's shell or the kiki UI process. It never signals a harness: termination goes through `ProcessSupervisor` by recorded identity. See [Terminal runtime](terminal-runtime.md#provisioning).

The hook launcher is a different process and ships in the `kk-hook` crate. It is the per-thread, hook-side process described in [Harness adapter](harness-adapter.md#hook): it caches each tool batch's first admission decision and answers with a blocking deny for a dead sidecar under an active barrier. In this book "the launcher" without a qualifier in a terminal context means the pane launcher; the hook-side process is always written "hook launcher".

A future native or web UI joins as a fifth client of the same surface.

## Internal layout inside `kkd`

`kkd` is one daemon binary but is split-by-concern internally. A `ThreadController` owns each thread's lifecycle and dies with the thread; a small set of cross-cutting components own daemon-wide concerns:

- `OpLogWatcher` — watches the resolved main-repo `op_heads/heads/` store through `OpFrontierSampler`, plus periodic sampling; populates normalized operation nodes, parent edges, workspace projections, and the observed frontier. See [`op-log-watcher.md`](op-log-watcher.md).
- `CascadeOrchestrator` — per-thread reconciliation lock; classify native rewrite versus parent advance; materialize; hold the parallel-batch delivery barrier; acknowledge only from a later model turn.
- `ProjectionReconciler` — compare stable identity with workspace, bookmark, path, and terminal-binding projections; auto-normalize only unique identity-preserving drift; produce named `kk repair` plans otherwise.
- `TerminalRuntime` — v1 `HerdrRuntime` implementation generates and validates the Herdr configuration; starts, finds, and verifies the dedicated Herdr server; subscribes to events; provisions, snapshots, and closes terminal groups; fences a group where the capability exists; publishes labels and tokens; and sends global toasts. It reports observations and never claims readiness, process absence, or delivery.
- `ProcessSupervisor` — faces the local OS, not Herdr: process identity, descendant and holder inventory, write-ahead freeze, re-proof, verified resume, termination of recorded identities with verified exit, and the orphan scan. Every result has an `Unknown` outcome that preserves files.
- `MetadataLedger` + `AICompose` (v1.x) — auto-describe / auto-rename ownership tracking and prompt assembly.
- `GitHubBackend` (v1.x; default `GhCli` impl) — PR creation, status polling, comment surfacing.
- `ConfigLoader` — the acceptance slice's minimal daemon/harness/terminal/path/notification keys; v1.x adds the full layered TOML and per-thread SQLite surface enumerated in [Configuration](../11-configuration.md).
- `AuthEnforcer` + approval broker — `ThreadScoped` checks for ordinary work, persisted begin/display/confirm challenges and one-shot plan-bound `HumanApproval` for consequential operations, and Admin only for bootstrap or foreground-presenter enrollment.
- `ThreadTranscriptStore` (v1.x) — JSONL tail, projection, FTS5 read API, and provider-egress consent state.
- `JjBackend` — v1 `JjCli` implementation shells out to `jj` and parses structured template output. A later `JjLib` implementation can swap behind the same trait.

This split keeps "closing thread foo's terminal group" from becoming entangled with global daemon state and leaves room to extract per-thread supervisors into separate processes later without rewriting business logic.

`TerminalClient` is the third terminal-facing module and lives in `kk`, because focus belongs to a viewer and not to the daemon. The three traits are defined in `kiki-core`; each has an in-process fake as its second adapter. Together they replace the former single tmux backend. Harness safety and delivery are in none of them.

## Stack

- Rust, edition decided by the implementer at first build.
- `tonic` for the gRPC server and client codegen.
- `rusqlite` (or `sqlx` with the sqlite feature) for state.
- `ratatui` for the custom UI only: approval cards, the v1.x overlay TUI (opened as a Herdr popup or pane), and the optional v1.x `ui` role pane. Panes, splits, tabs, scrollback, and the thread sidebar are Herdr's and are not reimplemented.
- `clap` for CLI parsing.

## The Bun/TypeScript bootstrap

The repo is currently bootstrapped as a Bun + TypeScript project (`package.json`, `tsconfig.json`, `index.ts` placeholder). Implementation will be Rust per the original architectural decision; the Bun bootstrap is a placeholder pending the first real `kkd` commit.
