# Daemon

[`kkd`](../appendix-a-glossary.md#kkd) is kiki's [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>): a program that runs in the background. There is a single `kkd` per user. A repository joins only when the user opts in with `kk init`.

`kkd` is a coordinator, not a terminal host. That means:

- one user-scoped daemon, serving many [threads](../appendix-a-glossary.md#thread);
- thin clients that talk to it over stable IPC (inter-process communication, the way programs on one machine talk to each other);
- no ownership of what is drawn inside a pane.

Terminals live in a separate, [dedicated Herdr server](../appendix-a-glossary.md#dedicated-herdr-server). ([Herdr](https://github.com/herdrdev/herdr) is the [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer) kiki uses.) `kkd` starts that server, verifies it, and observes it. `kkd` never trusts it as an authority.

[Terminal runtime](terminal-runtime.md) defines that boundary. This chapter covers the daemon's side of it.

## Lifecycle

- **One `kkd` per user.**
- **First-run bootstrap.** The first `kk` invocation installs and starts `kkd` as a per-user service. A service is a background program that the operating system (OS) starts and restarts.
  - On macOS the service is a [launchd](https://en.wikipedia.org/wiki/Launchd) user agent. On Linux it is a [systemd](https://en.wikipedia.org/wiki/Systemd) user unit.
  - `kk` never forks `kkd` from the invoking terminal. That is, `kk` never starts `kkd` as a child of that terminal.
  - So `kkd`, and the dedicated Herdr server it starts, run outside the terminal application's own job and process tree. Quitting the terminal application ends neither them nor any agent.
  - State files in `~/.config/kiki/` are created with mode `0700`. The [gRPC](https://grpc.io/) socket and credential files are mode `0600`. (These are [Unix file permissions](https://en.wikipedia.org/wiki/File-system_permissions). Both modes give access to the owning user only.)
- **Reboot survival.** The service manager restarts `kkd` after a crash, logout, or reboot.
  - Recovery on restart reads sqlite ([SQLite](https://www.sqlite.org/), kiki's database). Threads survive crashes and reboots.
  - Agent processes do not survive a reboot. Their threads read [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing) afterwards.
- **Components.** Each thread has its own `ThreadController` actor. (An actor is a small independent worker inside the daemon.)
  - A `ThreadController` supervises the thread's durable lifecycle [sagas](../appendix-a-glossary.md#saga). A saga is a multi-step operation that records each step so it can recover after a crash.
  - A `ThreadController` dies only after its thread is closed or destroyed coherently.
  - Cross-cutting components (those that serve the whole daemon) include the [op-log watcher](../appendix-a-glossary.md#op-log-watcher), cascade orchestrator, projection reconciler, terminal runtime adapter, process supervisor, and approval broker.
  - AI and GitHub workers join later with their v1.x features.

## What the daemon owns

- **All gRPC behavior.** [gRPC](https://grpc.io/) is the [remote procedure call](https://en.wikipedia.org/wiki/Remote_procedure_call) system that clients use to ask `kkd` to do things.
  - Every call goes through `AuthEnforcer`, the component that checks credentials.
  - A consequential operation claims its `HumanApproval` atomically (in one indivisible step) while it creates the durable operation journal. That [approval](../appendix-a-glossary.md#human-approval) is bound to the method, the target, the argument, and the rendered plan.
  - The operation then consumes the approval when that exact plan completes.
  - Every parseable transport attempt produces exactly one SQLite audit row. The row goes in the target repo database when the repo resolves. Otherwise it goes in the user database.
- **Durable sagas** for creation, checkpoint, close, reopen, and repair.
  - The managed [workspace](../appendix-a-glossary.md#workspace)'s exact `@` is persisted (saved) as the live [thread head](../appendix-a-glossary.md#thread-head). (`@` is [jj](https://docs.jj-vcs.dev/latest/)'s name for a workspace's [working-copy commit](https://docs.jj-vcs.dev/latest/glossary/).)
  - [Bookmarks](../appendix-a-glossary.md#bookmark) are explicit checkpoints.
- **The cascade [state machine](https://en.wikipedia.org/wiki/Finite-state_machine).** The [cascade](../appendix-a-glossary.md#cascade-reconciliation) carries a parent thread's changes to the threads that follow it. The state machine does these things:
  - It classifies observed jj transitions into [`NativeRewrite`](../appendix-a-glossary.md#nativerewrite), [`ParentAdvance`](../appendix-a-glossary.md#parentadvance), `AlreadyAligned`, or [`TopologyDiverged`](../appendix-a-glossary.md#topologydiverged).
  - It validates a strict linear [owned stack](../appendix-a-glossary.md#owned-stack).
  - It persists `sync_intents`, each pinned to an exact [base transition](../appendix-a-glossary.md#base-transition). (See [`sync_intent`](../appendix-a-glossary.md#sync-intent).)
  - It binds a parallel-tool-batch barrier before mutation.
  - It owns the soft-batch or restart-startup delivery proof through acknowledgement.
- **[Projection](../appendix-a-glossary.md#projection) reconciliation** for workspace records, paths, bookmarks, and terminal bindings. Reconciliation means comparing kiki's records with what really exists.
  - Only unique identity-preserving normalization is automatic.
  - Ambiguous changes become named `kk repair` plans.
- **The dedicated Herdr server.** `kkd` owns three things here:
  - the server's lifecycle and generated configuration;
  - provisioning (setting up) and closing [terminal groups](../appendix-a-glossary.md#terminal-group) through `TerminalRuntime`;
  - one-way presentation publishing.

  See [The dedicated Herdr server](#the-dedicated-herdr-server).

- **OS process proofs through `ProcessSupervisor`.** These cover process identity, write-ahead freeze, [verified resume](../appendix-a-glossary.md#verified-resume), termination with [verified exit](../appendix-a-glossary.md#verified-exit), the inventory of [workspace holders](../appendix-a-glossary.md#holder), and the [orphan](../appendix-a-glossary.md#orphan) scan.
  - A runtime reply is never an input to these proofs, with one exception. It may be a source of root process ids. The supervisor re-reads those ids from the OS.
- **The v1.x transcript JSONL tail.** ([JSONL](https://jsonlines.org/) is a file format with one JSON record per line. "Tail" means reading new lines as they are added.)
  - The per-(thread, session_id) offset advances atomically with `thread_messages` inserts. So persisted state never diverges from inserted rows.
- **Op-log watching.** See [`op-log-watcher.md`](op-log-watcher.md).
- **[Auto-rename](../appendix-a-glossary.md#auto-rename) / [auto-describe](../appendix-a-glossary.md#auto-describe)** ownership and execution, when that v1.x feature ships.

## What the daemon does NOT own

- **Active-thread focus.** Which terminal a human is looking at belongs to each [Herdr client](../appendix-a-glossary.md#herdr-client).
  - `kk switch` has two parts: a summary lookup in `kkd`, and a [caller-local focus](../appendix-a-glossary.md#caller-local-focus) request that `kk` makes through `TerminalClient`.
  - `kk switch` mutates (changes) no terminal and needs no `HumanApproval`. There is no mutating `Switch` RPC.
  - `kkd` never calls a focus method on a viewer's behalf.
  - There is no ambient operational Admin authority.
  - Caller-local focus requires the Herdr extension [`client_targeted_focus`](../appendix-a-glossary.md#client-targeted-focus). This is the only upstream extension (a change made in Herdr itself) that kiki requires.
  - Without it, `kk switch` fails and names the capability. Only the explicit `kk switch --all-clients` moves every attached client.
- **The terminal.** Herdr owns PTYs ([pseudoterminals](https://en.wikipedia.org/wiki/Pseudoterminal)), panes, tabs, layout, scrollback, copy mode, input, rendering, its native sidebar, and [toasts](../appendix-a-glossary.md#toast).
  - `kkd` provisions and closes terminal groups. It publishes labels and tokens through Herdr's JSON socket API.
  - `kkd` does not multiplex or render. It does not read a decision back out of anything Herdr displays.
  - `kkd` never calls Herdr's `worktree.*` methods.
- **jj revisions.** `jj` owns revisions.
  - `kkd` reacts to op-log events and issues thread-aware porcelain (user-friendly commands built on jj). The op log is jj's [operation log](https://docs.jj-vcs.dev/latest/operation-log/), its record of every change to the repository.
  - Users can run `jj` directly at any time. `kkd` reacts to whatever it sees.

## Context discovery

When a command runs, kiki has to answer "Which thread am I in?". `ContextDiscovery` resolves this, in this order:

1. **An explicit CLI target.**
2. **`KIKI_THREAD_ID` in the environment.** This is an [environment variable](https://en.wikipedia.org/wiki/Environment_variable). Kiki sets it explicitly on every [role pane](../appendix-a-glossary.md#role-pane). Herdr does not copy one pane's explicit environment into a split.
3. **Herdr pane identity.** This step applies when the caller's `HERDR_SOCKET_PATH` is kiki's dedicated server.
   - `kk` sends the caller's `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, and `HERDR_PANE_ID` to `kkd`.
   - `kkd` resolves them against the bindings of the current `server_instance_id`.
   - `kkd` accepts the result only after a check. Using the CLI connection's [peer credentials](https://man7.org/linux/man-pages/man7/unix.7.html) (what the OS reports about the calling program), it verifies that the calling process is a descendant or session member of that pane's root process on the current server instance.
   - This is how a pane the user split natively resolves to its thread.
   - Pane identity from any other Herdr server is ignored.
   - Pane ids in an environment can go stale after a native pane move. The verification is what catches that.
4. **The current [working directory](https://en.wikipedia.org/wiki/Working_directory).**

**Popups and keybindings.** A command started from a Herdr popup or keybinding has no `HERDR_PANE_ID`. Herdr supplies `HERDR_ACTIVE_WORKSPACE_ID`, `HERDR_ACTIVE_TAB_ID`, and `HERDR_ACTIVE_PANE_ID` instead.

- `kkd` applies the same resolution to the active pane's terminal group. But it uses the result only as a locator for read-only and navigation commands.
- A mutation invoked from a popup still needs the thread credential and, where required, an approval.

**Environment text is a locator, not authority.**

- Herdr ids never authorize anything and never substitute for a credential.
- A ref **may** locate the caller's contextual thread when two things are true: it was observed under the current [server instance](../appendix-a-glossary.md#server-instance), and it matches a current binding. After that, the thread's own credential is what authorizes.
- A Herdr id that matches no current binding on the current instance resolves nothing. Discovery falls through to the next step.

## The dedicated Herdr server

`kkd` owns one named Herdr server per user. Four things separate it from the user's default Herdr server: a separate server process, socket, saved session, and configuration file. It does not have a separate directory tree. `kkd` never reads or changes the default server's configuration file, saved session, or terminals.

- **Address.** The server is named by its Herdr session name (`terminal.session`, default `kiki`).
  - Herdr has no configuration-directory flag.
  - Herdr keeps a named session's socket, saved state, and logs under its own directories, keyed by the session name.
  - Herdr shares its plugin registry and state directory with the user's other Herdr use.
  - `kkd` reads the socket location from that layout. Before starting anything, it checks that the longest derived socket name fits the platform's socket-path limit.
- **Generate and validate.** Kiki's generated configuration file is `<herdr_dir>/config.toml`. The directory comes from `[paths] herdr_dir`, and its default is `<user_state_dir>/herdr/`. That directory holds only this file. (The file is written in [TOML](https://toml.io/), a simple configuration format.)
  - The file sets automatic agent resume off.
  - It sets onboarding off.
  - It sets Herdr's update, version, and manifest checks off.
  - It sets toast delivery to Herdr's own [toasts](../appendix-a-glossary.md#toast).
  - It sets sidebar rows and width sized for kiki's label.
  - When the v1.x [sidebar tokens](../appendix-a-glossary.md#sidebar-token) and keybindings ship, it also declares them.

  Two facts make the file fragile. Herdr's own client can rewrite it from its settings screen. And when the file fails to parse, Herdr silently loads defaults, which have agent resume on. So, immediately before every server start, `kkd` regenerates the file and validates it with its own parser. `kkd` refuses to start the server on any diagnostic.

- **Start.** Only `kkd` starts the server. It runs `terminal.herdr_bin` with `--session <name>` and `HERDR_CONFIG_PATH=<herdr_dir>/config.toml`.
  - Kiki does not redirect `XDG_CONFIG_HOME` or `XDG_STATE_HOME`. (These [XDG base-directory](https://specifications.freedesktop.org/basedir-spec/latest/) variables tell programs where to keep configuration and state.) Panes inherit the server's whole environment. So a redirected value would make jj, git, gh, and every shell in every thread read configuration from the wrong place.
  - For the same reason, `kkd` starts the server with an environment it builds on purpose. That environment is the user's login baseline of `HOME`, `USER`, `SHELL`, `PATH`, and locale. It is never the environment of whichever terminal happened to invoke `kk`.
  - Role panes add their explicit variables on top.
  - `HERDR_CONFIG_PATH` is visible inside panes.
  - Starting the server creates no terminal group and starts no agent.
- **Find.** `kkd` connects to the session's socket.
  - A running server is unverified in two cases: this `kkd` installation did not start it, or its peer identity matches no open `terminal_servers` row.
  - For an unverified server, `kkd` provisions nothing on it, threads bound to it read [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing), and replacing it is an approved plan.
  - `kk attach` asks `kkd` to ensure the server through `EnsureTerminalServer`. Then it uses Herdr's connect-only client mode for the named session. It never uses a client entry point that would start a server itself.
- **Verify.** On every connection `kkd` reads the ping reply. The reply returns Herdr's version, its protocol number, and an object of named boolean (true/false) capability flags. `kkd` checks them against the supported range it pins.
  - An unsupported server is not used. Terminal lifecycle operations fail with an actionable error, and existing threads keep their recorded state.
  - The adapter derives `RuntimeCapabilities` from the version and protocol plus those flags.
  - [`client_targeted_focus`](../appendix-a-glossary.md#client-targeted-focus) **must** arrive as a new upstream flag.
  - Herdr already reports `live_handoff` as true. That flag is not a gate signal, and kiki does not treat handoff as supported because of it.
  - Herdr ignores unknown request parameters. So `kkd` never probes for an extension by sending it.
- **Identify.** On every connection, `kkd` reads the socket peer's process identity `(pid, start_time)` from the OS. (A pid is a [process id](https://en.wikipedia.org/wiki/Process_identifier), the number the OS gives a running program.)
  - The `server_instance_id` is kiki's row id for one such observed peer.
  - Herdr's public API reports no instance identity.
  - Every recorded Herdr workspace, tab, and pane id is stored with the instance it was read under. It is meaningless under any other instance.
  - A pane's root process is trusted only if its parent is the current server process.
- **Observe.** `kkd` subscribes to events and then takes a snapshot.
  - Events are wake-up hints. The snapshot is the observation.
  - Herdr's session snapshot carries no process ids. So a snapshot is the session snapshot plus a per-pane process query.
  - A snapshot is not atomic (not taken at one single instant). Every pid in it is re-read from the OS before it is trusted.
- **Publish.** `kkd` publishes a label, and in v1.x tokens, only to a terminal group with a current binding.
  - A [remnant container](../appendix-a-glossary.md#remnant-container) left by a restore keeps whatever label Herdr restored. It receives no kiki tokens.
  - The user can hide or collapse the sidebar that shows the label. Nothing depends on it being visible.

### Runtime reconciliation

`kkd` resyncs after each of these:

- daemon start;
- a reconnect;
- any connection error;
- a reported loss of events;
- a changed `server_instance_id`.

To resync, `kkd` resubscribes, takes a fresh snapshot, reconciles every [terminal binding](../appendix-a-glossary.md#terminal-binding), and republishes presentation.

Reconciliation compares each binding's recorded handles and launcher process identities with the snapshot and with the OS.

- A terminal change that an in-flight [lifecycle journal](../appendix-a-glossary.md#lifecycle-journal) expected belongs to that journal.
- Every other difference becomes a [projection issue](../appendix-a-glossary.md#projection-issue) under the rules in [Threads](../03-threads.md#projection-divergence-and-repair).

Nothing is reconstructed from Herdr's event history, labels, or tokens.

### Orphan scan

A process can outlive its pane, its terminal group, and the terminal server. `kkd` asks `ProcessSupervisor` which recorded process identities are still alive. It asks at these times:

- at daemon start, before any thread is reported `Active`;
- whenever the `server_instance_id` changes;
- before provisioning a replacement terminal group or activating a replacement [incarnation](../appendix-a-glossary.md#incarnation)'s gate;
- before any step that forgets or deletes a jj workspace, together with the holder scan.

[`OrphanedProcess`](../appendix-a-glossary.md#orphanedprocess) is a standing projection issue with exactly two causes:

- a **recorded** process identity that is alive without a current binding;
- a **[harness remnant](../appendix-a-glossary.md#harness-remnant)**. Before a replacement incarnation's gate is activated, kiki takes an inventory rooted at the `agent` launcher. That inventory **must** show no process other than the launcher itself in its descendant, session, and [process-group](https://en.wikipedia.org/wiki/Process_group) sets. A surviving tool child of the retired harness is a remnant.

While the issue is unresolved, `kkd` activates no gate and materializes nothing in that workspace. Recorded role processes that are pane members on the current instance are terminal members, not orphans.

**Unrecorded holders.** An **unrecorded** same-UID process that holds the workspace is not a standing issue. ("Same-UID" means running as the same user.) It never blocks an `Active` thread's boundaries.

- It matters only to an operation that deletes the workspace: close, destroy, [`close-without-terminal`](../appendix-a-glossary.md#close-without-terminal), and failed-create cleanup.
- There it makes the result `Unknown`, unless the approved plan names that exact holder identity as accepted. Naming it is the human's informed choice. One example is an editor left open. (See [accepted holder](../appendix-a-glossary.md#accepted-holder).)
- A holder the plan does not name is drift.
- The holder scan excludes `kkd`, its own child processes, and the invoking `kk` process.
- Every `Unknown` result reports each offending pid, its command line, and the step that clears it.
- Processes running as another user are invisible to the scan. Kiki says so and claims nothing about them.
- A member that is stopped by a debugger makes the result `Unknown`.

**Termination.** `kkd` terminates only identities it recorded. It does so only after it has stopped them and re-read their identity. On a mismatch, it continues that process and treats it as unknown.

Where the OS offers a process handle, such as a [pidfd](https://man7.org/linux/man-pages/man2/pidfd_open.2.html), `kkd` [signals](<https://en.wikipedia.org/wiki/Signal_(IPC)>) through the handle rather than a bare pid. A handle keeps pointing at the same process even if its pid is reused.

## Op attribution

"Op attribution" means marking which jj [operations](https://docs.jj-vcs.dev/latest/operation-log/) kiki itself made.

jj offers no way to set an operation's description from the command line. So `kkd` attributes its own operations in two ways:

- Every jj invocation runs with a per-invocation operation user and host configuration that marks it as kiki's.
- `kkd` records every operation id the command wrote in `op_attribution`. One command may write several.

Classification still runs on every operation, kiki's own included. Attribution suppresses only cascade re-triggering.

The initiating reconciliation handler compares the before and result operation views. It records `NativeRewrite` intents for any other workspaces jj evolved.

## Failure model

This section lists what can go wrong and what kiki does about each case.

- **The daemon crashes.** In-flight gRPC calls fail, and clients reconnect.
  - Cascade crash safety does not come from the daemon staying up.
  - It comes from durable intent and barrier state, plus the ordering of `MarkDelivered(intent_id, incarnation_id, model_turn_id, tool_batch_id)` after stdout is written.
- **The daemon restarts.** Op-log catch-up walks every unprocessed operation reachable from the observed frontier through normalized parent edges, in [topological order](https://en.wikipedia.org/wiki/Topological_sorting) (parents before children).
  - It runs _before_ JSONL backfill, so anchor lookups see current operation and workspace history.
- **The service manager restarts `kkd`.** `kkd` runs under launchd or systemd-user and is restarted by it. Restart recovery reads sqlite state. Thread identity and persisted lifecycle state survive reboots.
- **`kkd` crashes during a freeze.**
  - Each discovered process identity was committed to `process_records` before it was signalled. The row includes its prior stop state and the freeze's lifecycle operation id.
  - On restart, `kkd` rebuilds the [frozen set](../appendix-a-glossary.md#frozen-set) from those rows.
  - Before the [final proof](../appendix-a-glossary.md#final-proof), it performs verified resume.
  - After the final proof, it continues the journal forward.
  - The filesystem watch died with the old process. So the [post-exit filesystem recheck](../appendix-a-glossary.md#post-exit-filesystem-recheck) re-reads the generation and fingerprint, and compares them with the final proof's journaled values.
  - A mismatch is `CloseFailed` or `DestroyFailed`, with files preserved.
- **`kkd` restarts while the Herdr server survives.** Agents keep running.
  - `kkd` reconnects and verifies the peer's `(pid, start_time)` against its open `terminal_servers` row. Then it snapshots, runs the [orphan scan](../appendix-a-glossary.md#orphan-scan), and reconciles.
  - `agent` launchers reopen their supervision streams.
  - A binding continues if its recorded launcher and harness process identities are still live under the same instance. The harness's next hook round-trip re-proves the incarnation as usual.
  - A live launcher whose harness is gone keeps its binding and its `agent` role. The incarnation is retired without acknowledgement, [`AgentStatus`](../appendix-a-glossary.md#agentstatus) is `Crashed`, and the thread's lifecycle is unchanged.
  - A binding whose `agent` launcher is gone ends, and its thread raises [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing).
- **The harness exits while its launcher lives.**
  - The launcher reports the exit, re-reads the thread credential, and awaits the next gate.
  - The incarnation is retired without acknowledgement. The thread shows `blocked`, never working.
  - A replacement incarnation is a new `agent_sessions` row and a new one-use gate, awaited by the same accepted launcher. It needs no terminal provisioning.
  - Its gate is activated only after the harness-remnant check above passes.
  - Two paths start a replacement incarnation:
    - Kiki's own protocol restarts: a cascade hard restart or a `RestartStartup` replacement. These are daemon-initiated steps of the delivery protocol and need no `HumanApproval`.
    - The `kk repair` plan [`restart-agent`](../appendix-a-glossary.md#restart-agent), the explicit restart path. It is same-thread and needs no approval in thread context. `restart-agent` uses `RestartStartup` when an intent is pending.
  - Only the launcher's own exit, or the loss of its binding or server instance, ends the `agent` role and raises `TerminalMissing`. The restart plan for `TerminalMissing` needs approval.
  - In a group whose only pane is the `agent` pane, the launcher's exit also removes the whole Herdr workspace. This is because Herdr drops a workspace when its last pane's command exits, and reports only a pane-exit event.
- **The Herdr server crashes or is killed.** Its PTYs close.
  - Processes that ignored hangup or left their session can survive. They are absent from every terminal view. (Hangup is the signal a process gets when its terminal closes.)
  - `kkd` observes the connection error. It treats every binding of that instance as ended and retires every incarnation without acknowledgement. It runs the orphan scan before anything else.
  - `kkd` **may** start a fresh server so that `kk attach` and repair work. But it starts no agent on its own: each affected thread raises `TerminalMissing`.
  - A terminal restart is an approved `kk repair` plan with a fresh credential, launch settings, gate, and handshake. It never reuses a remnant or [unbound container](../appendix-a-glossary.md#unbound-container).
  - The plan does these steps in order:
    1. It lists every remnant or unbound container whose processes hold the workspace, with those processes.
    2. It closes each one through freeze, termination with verified exit, and a close request.
    3. It re-runs the holder scan.
    4. Only then does it provision a fresh terminal group.
  - An unresolved [`OrphanedProcess`](../appendix-a-glossary.md#orphanedprocess) blocks that plan for its workspace.
- **[Cold restore](../appendix-a-glossary.md#cold-restore).** A restarted server restores layout, labels, working directories, and the same public ids, with new processes.
  - Launch argv (the command and its arguments) is saved but not rerun. Launch environment and tokens are not kept.
  - A restored pane whose saved directory is gone has no process at all.
  - Herdr allocates workspace ids from a counter that resumes above the highest surviving id. So an id may recur for an unrelated new group.
  - A restored pane is a plain shell with no role, running in the jj workspace.
  - `kkd` handles a cold restore exactly as a server crash: new instance, ended bindings, orphan scan, `TerminalMissing`, and the same restart plan that closes remnant containers before provisioning.
  - A restored pane is never `Active` evidence. The generated configuration keeps Herdr from resuming agents itself.
- **Live handoff** is unsupported in v1, and `kkd` never initiates it. An observed instance change with surviving recorded processes blocks boundary mutation and raises `TerminalMissing` with that evidence.
- **A runtime call's reply is lost.** `kkd` never repeats a create or close blindly.
  - Provisioning recovers from a fresh snapshot and launcher reports. It rotates the [provision nonce](../appendix-a-glossary.md#provision-nonce) before any re-issued create call.
  - Close does not wait on the reply at all. Kiki has already terminated the frozen set with verified exit, and the close request is cleanup.
  - See [Provisioning](terminal-runtime.md#provisioning) and [Process supervision](terminal-runtime.md#process-supervision).
- **Creation or reopen fails after provisioning.** Automatic compensation (undoing the steps already completed) **may** close the provisioned group and remove the new jj workspace, but only while all three of these hold:
  - the [launch gate](../appendix-a-glossary.md#launch-gate) was never activated;
  - `ProcessSupervisor` shows the group contains nothing but kiki's own blocked launchers; and
  - the workspace still equals its initial [materialization](../appendix-a-glossary.md#materialization).

  Otherwise the saga stops with its projections intact. Cleanup is then an approved [repair plan](../appendix-a-glossary.md#repair-plan) that uses the close machinery.

- **`kkd` is unreachable from the hook.** What [`kk-hook`](../appendix-a-glossary.md#kk-hook) does depends on how far the batch has got.
  - Before a batch has activated a [cascade barrier](../appendix-a-glossary.md#delivery-barrier), `kk-hook` **may** degrade to a cached batch-wide pass-through when `kkd` is unreachable. It logs the gap under `errors/<thread_id>.log`.
  - If a restart loses that cache and the in-flight batch is unknown, kiki leaves files untouched. It replaces the incarnation to establish a clean boundary.
  - Once reconciliation may have changed files, the durable barrier [fails closed](../appendix-a-glossary.md#fail-closed). Every sibling call remains blocked. An unprovable batch-completion boundary forces a hard restart with the saved payload.
  - Missed transitions remain reconstructable from jj's operation DAG (its graph of operations). The next successful boundary probes actual files before mutation.
  - See [Harness adapter](harness-adapter.md).
- **A same-UID adversary** can read credentials and invoke `kk` directly. The daemon's authorization model reduces accidental and buggy agent blast radius. It does not defend against active malice. See [Authority](../04-authority.md).
