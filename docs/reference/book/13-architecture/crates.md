# Crate layout

kiki is a [Cargo workspace](https://doc.rust-lang.org/cargo/reference/workspaces.html) with four crates. A crate is one [Rust](https://www.rust-lang.org/) package: either a library or a program. A Cargo workspace is a set of crates built together.

The split exists so the [gRPC](https://grpc.io/) service surface is a real seam. A seam is a clean boundary between parts. [`kkd`](../appendix-a-glossary.md#kkd) is the only privileged process, and every UI is a client of the same protocol.

| Crate       | Kind    | Responsibility                                                                                                                                                                                                                                                         |
| ----------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kiki-core` | library | Shared types, traits, generated proto types, and sqlite migrations. No I/O (it reads and writes nothing itself).                                                                                                                                                       |
| `kkd`       | binary  | The [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>), kiki's background program. Owns all state and behavior. gRPC server.                                                                                                                                 |
| `kk`        | binary  | The CLI (command-line program). Hosts the TUI and the [pane launcher](../appendix-a-glossary.md#pane-launcher) as subcommands. Pure client of the gRPC service. Also a Herdr client for [caller-local focus](../appendix-a-glossary.md#caller-local-focus) and attach. |
| `kk-hook`   | binary  | The pre-tool sidecar that the managed [harness](../appendix-a-glossary.md#harness)'s hooks invoke (Claude Code and Codex), and its per-thread [hook launcher](../appendix-a-glossary.md#hook-launcher). Pure client of the gRPC service.                               |

Some terms from the table:

- A **binary** is a program you can run.
- **Proto types** are data types generated from a [Protocol Buffers](https://protobuf.dev/) file, which describes the gRPC messages.
- **Migrations** are the scripts that set up and update the [SQLite](https://www.sqlite.org/) database layout. See [schema migration](https://en.wikipedia.org/wiki/Schema_migration).
- A **TUI** is a [text-based user interface](https://en.wikipedia.org/wiki/Text-based_user_interface): an interactive screen drawn in a terminal.
- A **sidecar** is a small helper program that runs beside a main program.
- A **hook** is a command the harness runs at set moments, such as before a tool call. See [Claude Code hooks](https://docs.claude.com/en/docs/claude-code/hooks).

## Why four crates

**`kiki-core`** is a pure library with no I/O. This lets `kkd` and the clients share types and [traits](https://doc.rust-lang.org/book/ch10-02-traits.html) without dragging in tokio/tonic runtime concerns. (tokio and [tonic](https://github.com/hyperium/tonic) are the Rust libraries that run the networking.)

**`kkd`** is the only crate that does any of these:

- opens sqlite;
- shells out to `jj` or `gh` (runs them as separate programs);
- starts the [dedicated Herdr server](../appendix-a-glossary.md#dedicated-herdr-server) with the `herdr` executable;
- drives that server's JSON socket to provision (set up), observe, and close [terminal groups](../appendix-a-glossary.md#terminal-group).

**`kk` and `kk-hook`** are both clients of the same gRPC contract. There is no privileged internal API.

`kk` also talks to the dedicated [Herdr](https://github.com/herdrdev/herdr) server as a viewer:

- `TerminalClient` requests caller-local focus.
- For `kk attach`, `TerminalClient` runs `herdr` in its connect-only client mode, after `kkd` has ensured the server.

That path carries no kiki authority and mutates (changes) no kiki state.

### The pane launcher

The pane launcher is a hidden subcommand of the `kk` binary, not a fifth crate. Herdr starts it by direct argv (directly, with a list of arguments) as the PTY child of every [role pane](../appendix-a-glossary.md#role-pane). A PTY is a [pseudoterminal](https://en.wikipedia.org/wiki/Pseudoterminal), and the PTY child is the first program the terminal starts.

The launcher is a pure gRPC client and makes no launch decision of its own:

- `kkd` computes each [launch specification](../appendix-a-glossary.md#launch-specification) through the harness adapter. The specification holds argv, environment, and settings paths.
- The launcher only executes that specification and supervises the child.
- The launcher reports its Herdr ids and blocks on its gate.

The `agent` launcher holds one supervision stream to `kkd` for its whole life. On each gate it does these steps:

1. It creates the harness child, held before exec (before the harness program starts running).
2. It reports the child's pid ([process id](https://en.wikipedia.org/wiki/Process_identifier)).
3. It releases the child once `kkd` has recorded its identity.
4. Later, it reports the child's exit.
5. It awaits the next [incarnation](../appendix-a-glossary.md#incarnation)'s gate.

The `shell` and `ui` launchers are released by their role-claim transaction. They then replace themselves with the user's shell or the kiki UI process.

The pane launcher never signals a harness. Termination goes through `ProcessSupervisor` by recorded identity. See [Terminal runtime](terminal-runtime.md#provisioning).

### The hook launcher

The hook launcher is a different process and ships in the `kk-hook` crate. It is the per-thread, hook-side process described in [Harness adapter](harness-adapter.md#hook). It does two things:

- It caches each [tool batch](../appendix-a-glossary.md#tool-batch)'s first admission decision.
- It answers with a blocking deny for a dead sidecar under an active barrier.

A note on names in this book:

- "The launcher" without a qualifier, in a terminal context, means the pane launcher.
- The hook-side process is always written "hook launcher".

### Future clients

A future native or web UI joins as a fifth client of the same surface.

## Internal layout inside `kkd`

`kkd` is one daemon binary, but inside it is split by concern.

- A `ThreadController` owns each [thread](../appendix-a-glossary.md#thread)'s lifecycle and dies with the thread.
- A small set of cross-cutting components own daemon-wide concerns. They are listed here.

The components:

- **`OpLogWatcher`** watches jj's [operation log](https://docs.jj-vcs.dev/latest/operation-log/), its record of every change to the repository.
  - It watches the resolved main-repo `op_heads/heads/` store through [`OpFrontierSampler`](../appendix-a-glossary.md#frontier-sampler), plus periodic sampling.
  - It populates normalized operation nodes, parent edges, workspace projections, and the observed frontier.
  - See [`op-log-watcher.md`](op-log-watcher.md).
- **`CascadeOrchestrator`** runs the [cascade](../appendix-a-glossary.md#cascade-reconciliation).
  - It holds a per-thread [reconciliation lock](../appendix-a-glossary.md#reconciliation-lock).
  - It classifies native rewrite versus parent advance.
  - It materializes.
  - It holds the parallel-batch [delivery barrier](../appendix-a-glossary.md#delivery-barrier).
  - It acknowledges only from a later [model turn](../appendix-a-glossary.md#model-turn).
- **`ProjectionReconciler`** compares stable identity with the workspace, bookmark, path, and terminal-binding [projections](../appendix-a-glossary.md#projection).
  - It auto-normalizes only unique identity-preserving drift.
  - Otherwise it produces named `kk repair` plans.
- **`TerminalRuntime`** has one v1 implementation, `HerdrRuntime`. It reports observations and never claims readiness, process absence, or delivery. `HerdrRuntime` does these things:
  - It generates and validates the Herdr configuration.
  - It starts, finds, and verifies the dedicated Herdr server.
  - It subscribes to events.
  - It provisions, snapshots, and closes terminal groups.
  - It fences a group where the capability exists.
  - It publishes labels and tokens.
  - It sends global [toasts](../appendix-a-glossary.md#toast) (pop-up notices).
- **`ProcessSupervisor`** faces the local OS (operating system), not Herdr.
  - It covers process identity, descendant and [holder](../appendix-a-glossary.md#holder) inventory, write-ahead freeze, re-proof, [verified resume](../appendix-a-glossary.md#verified-resume), termination of recorded identities with [verified exit](../appendix-a-glossary.md#verified-exit), and the [orphan](../appendix-a-glossary.md#orphan) scan.
  - Every result has an `Unknown` outcome that preserves files.
- **`MetadataLedger` + `AICompose`** (v1.x) handle [auto-describe](../appendix-a-glossary.md#auto-describe) / [auto-rename](../appendix-a-glossary.md#auto-rename) ownership tracking and prompt assembly.
- **`GitHubBackend`** (v1.x; default `GhCli` impl) handles [pull request](https://docs.github.com/en/pull-requests) (PR) creation, status polling, and comment surfacing.
- **`ConfigLoader`** loads configuration.
  - In the [acceptance slice](../appendix-a-glossary.md#acceptance-slice), it loads the minimal daemon/harness/terminal/path/notification keys.
  - v1.x adds the full layered [TOML](https://toml.io/) and per-thread SQLite surface enumerated in [Configuration](../11-configuration.md).
- **`AuthEnforcer` + approval broker** check who may do what.
  - `ThreadScoped` checks cover ordinary work.
  - Consequential operations use persisted begin/display/confirm challenges and a one-shot plan-bound `HumanApproval`. (See [human approval](../appendix-a-glossary.md#human-approval).)
  - Admin is used only for bootstrap or foreground-presenter enrollment.
- **`ThreadTranscriptStore`** (v1.x) covers the JSONL tail, projection, FTS5 read API, and [provider-egress consent](../appendix-a-glossary.md#provider-egress-consent) state. ([JSONL](https://jsonlines.org/) is one JSON record per line. [FTS5](https://www.sqlite.org/fts5.html) is SQLite's full-text search.)
- **`JjBackend`** is how `kkd` talks to jj.
  - The v1 `JjCli` implementation shells out to `jj` and parses structured template output.
  - A later `JjLib` implementation can swap in behind the same trait.

This split has two benefits:

- It keeps "closing thread foo's terminal group" from becoming entangled with global daemon state.
- It leaves room to extract per-thread supervisors into separate processes later, without rewriting business logic.

**The third terminal-facing module.** `TerminalClient` lives in `kk`, because focus belongs to a viewer and not to the daemon.

- The three traits are defined in `kiki-core`.
- Each has an in-process fake as its second adapter (second implementation).
- Together they replace the former single tmux backend.
- Harness safety and delivery are in none of them.

## Stack

- [Rust](https://www.rust-lang.org/), edition decided by the implementer at first build.
- `tonic` for the gRPC server and client codegen (generated code).
- `rusqlite` (or `sqlx` with the sqlite feature) for state.
- `ratatui` for the custom UI only. ([ratatui](https://ratatui.rs/) is a Rust library for drawing terminal screens.)
  - The custom UI is approval cards, the v1.x [overlay TUI](../appendix-a-glossary.md#overlay-tui) (opened as a Herdr popup or pane), and the optional v1.x [`ui` role pane](../appendix-a-glossary.md#ui-role-pane).
  - Panes, splits, tabs, scrollback, and the thread sidebar are Herdr's and are not reimplemented.
- `clap` for CLI parsing (reading command-line arguments).

## The Bun/TypeScript bootstrap

The repo is currently bootstrapped as a Bun + TypeScript project (`package.json`, `tsconfig.json`, `index.ts` placeholder). Implementation will be Rust, per the original architectural decision. The Bun bootstrap is a placeholder pending the first real `kkd` commit.
