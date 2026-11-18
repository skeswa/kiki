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
- **First-run bootstrap.** `kkd` is installed and started as a per-user service. A service is a background program that the operating system (OS) starts and restarts. There are two ways in:
  - In a terminal, the first `kk` invocation asks whether to install `kkd`, and installs and starts it on a yes.
  - [`kk daemon install`](../09-commands.md#kk-daemon-install) does the same without asking. This is the path for a script and for a machine with no human. Without a terminal, `kk` never prompts. If `kkd` is not installed, `kk` fails with exit code 5 and names `kk daemon install`. See [exit codes](../09-commands.md#exit-codes).
  - Install creates the [Admin bootstrap credential](../appendix-a-glossary.md#bootstrap-admin-credential) and prints its path. `kk` never loads that credential by itself afterward.
  - On macOS the service is a [launchd](https://en.wikipedia.org/wiki/Launchd) user agent. On Linux it is a [systemd](https://en.wikipedia.org/wiki/Systemd) user unit.
  - `kk` never forks `kkd` from the invoking terminal. That is, `kk` never starts `kkd` as a child of that terminal.
  - So `kkd`, and the dedicated Herdr server it starts, run outside the terminal application's own job and process tree. Quitting the terminal application ends neither them nor any agent.
  - The server is not a child inside `kkd`'s own service unit either. `kkd` asks the service manager to start it as a separate unit: a separate launchd job on macOS, and a separate transient systemd user unit on Linux. ("Transient" means created at run time, with no unit file on disk.)
  - So a `kkd` crash, restart, or upgrade does not stop the server or any agent. This is a proof gate: the test kills `kkd` under each real service manager and checks that the server and the agents keep running. See [Terminal runtime](terminal-runtime.md#starting-and-addressing-the-server).
  - No step here needs a desktop session or an attached Herdr client. kiki is [headless](../appendix-a-glossary.md#headless): `kkd` and the server run the same way on a machine that nobody is logged in to at a screen.
  - On macOS reached over Secure Shell (SSH) with no graphical login, the per-user graphical launchd domain does not exist. `kk daemon install` then installs `kkd`, and `kkd` starts the server job, in launchd's per-user domain that is not tied to a graphical login. This is an unproven gate: the survival test above must pass in that domain before the mode is supported.
  - State files in `~/.config/kiki/` are created with mode `0700`. The [gRPC](https://grpc.io/) socket and credential files are mode `0600`. (These are [Unix file permissions](https://en.wikipedia.org/wiki/File-system_permissions). Both modes give access to the owning user only.)
- **No service manager.** Many containers and continuous-integration (CI) runners have no per-user service manager. There the operator runs `kkd --foreground` under whatever supervisor they already use.
  - `kkd --foreground` stays attached to the process that started it and logs to standard error. It installs nothing.
  - On first start it creates the state directory and the Admin bootstrap credential if they are absent, and logs the credential's path.
  - `kk` never starts `kkd` in this mode. If `kkd` is not running, `kk` fails with exit code 5.
  - With no service manager to ask, `kkd` starts the Herdr server as a detached process in its own OS session. The server is then not a member of `kkd`'s session or [process group](https://en.wikipedia.org/wiki/Process_group).
  - The same survival proof is a gate for this mode: the test kills `kkd` under the supervisor and checks that the server and the agents keep running. If a supervisor also stops the server or agents when restarting the daemon, that configuration fails the gate. A separate OS session alone does not prove survival. A platform mode that fails the gate is unsupported. This gate is unproven.
  - The operator's supervisor is what restarts `kkd`. If nothing restarts it, the server and the agents keep running, and commands that need the daemon fail with exit code 5 until `kkd` is back.
- **Reboot survival.** The service manager restarts `kkd` after a crash, logout, or reboot. In the `kkd --foreground` mode, the operator's supervisor does this instead.
  - Recovery on restart reads sqlite ([SQLite](https://www.sqlite.org/), kiki's database). Threads survive crashes and reboots.
  - Agent processes do not survive a reboot. Their threads read [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing) afterwards.
  - After a reboot or a login, the service manager does not start the Herdr server unit by itself. `kkd` starts it on demand, the next time a command needs the server. See [Terminal runtime](terminal-runtime.md#starting-and-addressing-the-server).
- **Components.** Each thread has its own `ThreadController` actor. (An actor is a small independent worker inside the daemon.)
  - A `ThreadController` supervises the thread's durable lifecycle [sagas](../appendix-a-glossary.md#saga). A saga is a multi-step operation that records each step so it can recover after a crash.
  - A `ThreadController` dies only after its thread is closed or destroyed coherently.
  - Cross-cutting components (those that serve the whole daemon) include the [op-log watcher](../appendix-a-glossary.md#op-log-watcher), cascade orchestrator, projection reconciler, terminal runtime adapter, process supervisor, and approval broker. The approval broker holds the automation policy evaluator; see [The automation policy](#the-automation-policy).
  - AI and GitHub workers join later with their v1.x features.

## What the daemon owns

- **All gRPC behavior.** [gRPC](https://grpc.io/) is the [remote procedure call](https://en.wikipedia.org/wiki/Remote_procedure_call) system that clients use to ask `kkd` to do things.
  - Every call goes through `AuthEnforcer`, the component that checks credentials.
  - A consequential operation claims its `HumanApproval` atomically (in one indivisible step) while it creates the durable operation journal. That [approval](../appendix-a-glossary.md#human-approval) is bound to the method, the target, the argument, and the rendered plan.
  - A [`PolicyApproval`](../appendix-a-glossary.md#policy-approval) for the same plan satisfies the same requirement and is claimed the same way. It is the one-shot approval `kkd` issues when the active automation policy allows the plan. [Authority](../04-authority.md#policyapproval) owns that rule and its exceptions.
  - The operation then consumes the approval when that exact plan completes.
  - Every parseable transport attempt produces exactly one SQLite audit row. The row goes in the target repo database when the repo resolves. Otherwise it goes in the user database.
- **Durable sagas** for creation, checkpoint, close, reopen, and repair. A terminal restart ([`restart-terminal`](../appendix-a-glossary.md#restart-terminal)) is one of these: a journaled lifecycle operation with its own step list.
  - The managed [workspace](../appendix-a-glossary.md#workspace)'s exact `@` is persisted (saved) as the live [thread head](../appendix-a-glossary.md#thread-head). (`@` is [jj](https://docs.jj-vcs.dev/latest/)'s name for a workspace's [working-copy commit](https://docs.jj-vcs.dev/latest/glossary/).)
  - [Bookmarks](../appendix-a-glossary.md#bookmark) are explicit checkpoints.
- **The cascade [state machine](https://en.wikipedia.org/wiki/Finite-state_machine).** The [cascade](../appendix-a-glossary.md#cascade-reconciliation) carries a parent thread's changes to the threads that follow it. The state machine does these things:
  - It classifies observed jj transitions into [`NativeRewrite`](../appendix-a-glossary.md#nativerewrite), [`ParentAdvance`](../appendix-a-glossary.md#parentadvance), `AlreadyAligned`, or [`TopologyDiverged`](../appendix-a-glossary.md#topologydiverged).
  - It validates a strict linear [owned stack](../appendix-a-glossary.md#owned-stack).
  - It persists `sync_intents`, each pinned to an exact [base transition](../appendix-a-glossary.md#base-transition). (See [`sync_intent`](../appendix-a-glossary.md#sync-intent).)
  - It binds a parallel-tool-batch barrier before mutation, and writes the thread's [barrier marker](../appendix-a-glossary.md#barrier-marker) before that.
  - It owns the soft-batch or restart-startup delivery proof through acknowledgement.
- **The `PassThrough` cache.** When `kkd` admits the first call of a [tool batch](../appendix-a-glossary.md#tool-batch) with no pending work, it remembers that [`PassThrough`](../appendix-a-glossary.md#batch-admission) decision so every other call in the batch gets the same answer.
  - `kkd` keeps this cache in memory only, keyed by incarnation and batch.
  - [`kk-hook`](../appendix-a-glossary.md#kk-hook) keeps nothing. It is a stateless client that makes one call and exits. There is no separate hook-side process.
  - After a `kkd` restart the cache is gone. See [Failure model](#failure-model) for the rule that covers this.
  - `kkd`, not the hook, performs any [hard pause](../appendix-a-glossary.md#hard-pause) and any replacement of an incarnation.
- **Locks.** `kkd` holds two kinds of lock. [Invariants](../02-invariants.md#locks-and-their-order) defines them.
  - The per-thread [reconciliation lock](../appendix-a-glossary.md#reconciliation-lock) guards one thread's reconciliation. The [lifecycle lock](../appendix-a-glossary.md#lifecycle-lock) is that same thread lock, held for the whole length of a lifecycle operation such as a close. It is not a second lock.
  - The per-repo [repo jj lock](../appendix-a-glossary.md#repo-jj-lock) is held around every unpinned working-copy command and every operation-head integration, from the frontier sample that the step depends on until the re-sample. It is short and innermost. It is never held across a wait.
  - The order is always the same: the parent thread's lock, then the child thread's lock, then the repo jj lock.
  - The human-invoked passthroughs (the body of `kk status` and the overlay's diff for the caller's own thread) are run by `kk`, not by `kkd`. They take none of `kkd`'s locks. See [Invariants](../02-invariants.md#operation-history-is-a-dag).
- **[Projection](../appendix-a-glossary.md#projection) reconciliation** for workspace records, paths, bookmarks, and terminal bindings. Reconciliation means comparing kiki's records with the observed resources.
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
  - Nothing in `kkd` waits for a viewer. The server may have zero attached clients, and every lifecycle step and safety proof runs the same way.
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

1. **An explicit CLI target** selects the thread the command acts on. Skip this step when resolving the caller and choosing its credential.
2. **`KIKI_THREAD_ID` in the environment.** This is an [environment variable](https://en.wikipedia.org/wiki/Environment_variable). Kiki sets it explicitly on every [role pane](../appendix-a-glossary.md#role-pane). Herdr does not copy one pane's explicit environment into a split.
3. **Herdr pane identity.** This step applies when the caller's `HERDR_SOCKET_PATH` is kiki's dedicated server.
   - `kk` sends the caller's `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, and `HERDR_PANE_ID` to `kkd`.
   - `kkd` resolves them against the bindings of the current `server_instance_id`.
   - `kkd` accepts the result only after a check. Using the CLI connection's [peer credentials](https://man7.org/linux/man-pages/man7/unix.7.html) (what the OS reports about the calling program), it verifies that the calling process is a descendant or session member of that pane's root process on the current server instance.
   - This is how a pane the user split natively resolves to its thread.
   - Pane identity from any other Herdr server is ignored.
   - Pane ids in an environment can go stale after a native pane move. The verification is what catches that.
4. **The current [working directory](https://en.wikipedia.org/wiki/Working_directory).**

**Callers outside Herdr.** A script, a CI job, or a human in a plain SSH session has no Herdr variables at all. An argument can locate the target. The working directory can locate the caller. Naming a target never loads its credential. Discovery never needs an attached Herdr client.

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
  - `kkd` starts the server as its own service-manager unit, not as a child inside `kkd`'s unit. That is a separate launchd job on macOS and a separate transient systemd user unit on Linux. The server must outlive `kkd`.
  - Under `kkd --foreground`, with no service manager, `kkd` starts the server as a detached process in its own OS session. See [Lifecycle](#lifecycle).
  - The server starts with no client attached and needs none. A client attaches only when a person runs `kk attach`.
  - Before it spawns the server, `kkd` writes a `terminal_servers` row in state `Starting`. It moves the row to `Open` once it has read the server's peer identity. So a crash between the two is recoverable: on restart `kkd` finds the `Starting` row and either completes it from the peer it finds on the socket or marks the start as failed.
  - Kiki does not redirect `XDG_CONFIG_HOME` or `XDG_STATE_HOME`. (These [XDG base-directory](https://specifications.freedesktop.org/basedir-spec/latest/) variables tell programs where to keep configuration and state.) Panes inherit the server's whole environment. So a redirected value would make jj, git, gh, and every shell in every thread read configuration from the wrong place.
  - For the same reason, `kkd` starts the server with an environment it builds on purpose. That environment is the user's login baseline of `HOME`, `USER`, `SHELL`, `PATH`, and locale. It is never the environment of whichever terminal happened to invoke `kk`.
  - Role panes add their explicit variables on top.
  - `HERDR_CONFIG_PATH` is visible inside panes.
  - Starting the server creates no terminal group and starts no agent.
- **Find.** `kkd` connects to the session's socket.
  - A `terminal_servers` row is in one of four states: `Starting | Open | Unverified | Ended`. `kkd` recognises a server it started by the peer identity on its `Open` row.
  - If the socket's peer is one `kkd` did not start, the server is unverified. That includes the new server process after Herdr's own handoff or upgrade.
  - `kkd` then ends the old row, which ends its bindings and raises [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing) for each affected thread. It records the new peer as `Unverified`.
  - `kkd` provisions nothing on an unverified server. The fix is the approved [`replace-terminal-server`](../appendix-a-glossary.md#replace-terminal-server) plan, and after it [`restart-terminal`](../appendix-a-glossary.md#restart-terminal) for each thread.
  - An instance change where `kkd` itself started the new server, for example after a server crash, gets an `Open` row. Each thread then needs only `restart-terminal`.
  - `kk attach` asks `kkd` to ensure the server through `EnsureTerminalServer`. Then it uses Herdr's connect-only client mode for the named session. It never uses a client entry point that would start a server itself.
- **Replace.** [`replace-terminal-server`](../appendix-a-glossary.md#replace-terminal-server) is the one plan that stops a running dedicated server. It is user-scoped, not thread-scoped. It is applied with `kk repair --server`.
  - The plan lists every thread and every process that the replacement stops.
  - It needs a one-shot approval. Its plan always carries the [risk label](../appendix-a-glossary.md#risk-label) `server-wide`, so a policy rule allows it only if the rule accepts that label.
  - It stops the old server with [verified exit](../appendix-a-glossary.md#verified-exit) and ends its row, whether that row was `Open` or `Unverified`. Then it starts a new one through the start path above.
  - Afterwards the old instance's bindings have ended, and each affected thread reads `TerminalMissing`. The server replacement starts no agent. Each thread is brought back with `restart-terminal`.
- **Changed settings.** `[terminal] session`, `[terminal] herdr_bin`, and `[paths] herdr_dir` decide which server `kkd` runs. If one of them changes while an instance is open, `kkd` does not start a second server.
  - It keeps the old server.
  - It reports that a change is pending.
  - It requires `replace-terminal-server` before the new value takes effect.
- **Verify.** On every connection `kkd` reads the ping reply. The reply returns Herdr's version, its protocol number, and an object of named boolean (true/false) capability flags. `kkd` checks them against the supported range it pins.
  - An unsupported server is not used. Terminal lifecycle operations fail with an error that says what to do, and existing threads keep their recorded state.
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
  - The user can hide or collapse the sidebar that shows the label. Nothing depends on it being visible, or on any client being attached to see it.

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

A process can outlive its pane, its terminal group, and the terminal server. `kkd` asks `ProcessSupervisor` which recorded process identities are still alive, and whether a harness remnant is left under a live `agent` launcher. It asks at these times:

- at daemon start, before any thread is reported `Active`;
- whenever the `server_instance_id` changes;
- before provisioning a replacement terminal group or activating a replacement [incarnation](../appendix-a-glossary.md#incarnation)'s gate;
- before any step that forgets or deletes a jj workspace, together with the holder scan.

[`OrphanedProcess`](../appendix-a-glossary.md#orphanedprocess) is a standing projection issue with exactly two causes:

- a **survivor**: a recorded process identity that is alive with no current binding, and that is not a member of a container on the current server instance;
- a **[harness remnant](../appendix-a-glossary.md#harness-remnant)**: any descendant of a live `agent` launcher, other than the launcher itself, while no incarnation is live. A remnant need not have been recorded before. Before a replacement incarnation's gate is activated, kiki takes an inventory rooted at the `agent` launcher. That inventory **must** show no process other than the launcher itself in its descendant, session, and [process-group](https://en.wikipedia.org/wiki/Process_group) sets. A surviving tool child of the retired harness is a remnant.

While the issue is unresolved, it blocks replacement, materialization, and deletion in that workspace. `kkd` activates no gate, provisions no replacement terminal group, materializes nothing, and deletes nothing.

The plan that resolves the issue is [`terminate-orphans`](../appendix-a-glossary.md#terminate-orphans). It needs a one-shot approval.

- For a remnant, it runs freeze discovery rooted at the launcher. For a survivor, it uses the recorded identities.
- It records `FreezeDiscovery` rows under the approval.
- It terminates those processes with verified exit.

A process that is a pane member of a container on the current instance is a terminal member, not an orphan, except a harness remnant under a live `agent` launcher. That includes a member of an [unbound container](../appendix-a-glossary.md#unbound-container): a terminal container on the current instance with no current binding, such as a group whose `agent` launcher died while the group itself survived. The `restart-terminal` and `close-without-terminal` plans dispose of those containers and their processes.

**Unrecorded holders.** An **unrecorded** same-UID process that holds the workspace is not a standing issue. ("Same-UID" means running as the same user.) It never blocks an `Active` thread's boundaries.

- It matters only to an operation that deletes the workspace: close, destroy, [`close-without-terminal`](../appendix-a-glossary.md#close-without-terminal), and the cleanup of a failed create or reopen.
- There it makes the result `Unknown`, unless the approved plan names that exact holder identity as accepted. The caller names it with `--accept-holder <pid>`. One example is an editor left open. (See [accepted holder](../appendix-a-glossary.md#accepted-holder).)
- A plan that accepts such a holder carries the risk label `outside-holders`. With no human, only a policy rule that accepts that label can approve it.
- A holder the plan does not name is drift.
- The holder scan excludes `kkd`, its own child processes, and the invoking `kk` process.
- Every `Unknown` result reports each offending pid, its command line, and the step that clears it.
- Processes running as another user are invisible to the scan. Kiki says so and claims nothing about them.
- A member that is stopped by a debugger makes the result `Unknown`.

**Termination.** `kkd` terminates only identities it recorded. It does so only after it has stopped them and re-read their identity. On a mismatch, it continues that process and treats it as unknown.

Where the OS offers a process handle, such as a [pidfd](https://man7.org/linux/man-pages/man2/pidfd_open.2.html), `kkd` [signals](<https://en.wikipedia.org/wiki/Signal_(IPC)>) through the handle rather than a bare pid. A handle keeps pointing at the same process even if its pid is reused.

## The automation policy

The [automation policy](../appendix-a-glossary.md#automation-policy) is the set of rules that lets a plan run with no human confirming it. [Authority](../04-authority.md#automation-policy) owns its meaning. This section says where it lives in the daemon.

- **The evaluator.** The policy evaluator is pure logic in `kiki-core`. It takes a canonical policy and one request, and it returns a `PolicyDecision`: `Allowed{rule}`, `RequireHuman{rule}`, or `NoMatch`. It opens no file and reads no database. See [Crate layout](crates.md#where-each-named-module-lives).
- **Who calls it.** Only the approval broker calls it, and only inside `BeginApproval`. The broker supplies these inputs:
  - the principal, which it works out from the caller's credential and, for a thread caller, from the [follows](../appendix-a-glossary.md#follows) graph;
  - the repo;
  - the operation name; and
  - the plan’s risk labels, which the preflight computed. For a consent plan the broker also supplies the normalized provider identity and current disclosure version.
- **What it replaces.** The policy replaces only the human's confirm step. It runs after the preflight and before nothing else changes. Freeze, holder scans, the final proof, and verified exit run the same way under either kind of approval. A plan that a safety proof refuses is refused, whatever the policy says.
- **When the policy is loaded.** `kkd` loads the active policy at three moments:
  - at daemon start, from the active row of `automation_policies` in the user database, before it serves any call;
  - when `ApplyAutomationPolicy` commits, in the same step that makes the new row active; and
  - when `RevokeAutomationPolicy` commits, which leaves no policy loaded.
- **What is never loaded.** `kkd` never evaluates the `[automation]` tables in the configuration file. Editing the file does nothing until `kk automation apply` activates it. `ConfigLoader` does not feed the evaluator.
- **A stored policy that cannot be read.** If the active row's text does not match its digest, or does not parse, `kkd` loads no policy. Every decision is then `NoMatch`, and `kk automation status` reports the fault. This is [failing closed](../appendix-a-glossary.md#fail-closed).
- **No policy.** With no active row, every decision is `NoMatch`. kiki then behaves as it did before automation existed: a human confirms at a foreground terminal, and a caller with no terminal fails with exit code 3.
- **Automation credentials.** `kkd` stores each credential's hash in `automation_credentials` and writes the secret to `~/.config/kiki/automation/<name>.cred`, mode `0600`. That directory is outside every managed workspace. `kkd` never puts the secret in a harness, a hook, or a pane environment.
- **Activation is hygiene, not a boundary.** Activation needs the enrolled presenter or the Admin credential. That keeps an agent from granting itself authority by editing a file. Like presenter enrollment, it works only under the cooperative same-UID model. It does not stop a malicious process that runs as the same user.

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
- **The service manager restarts `kkd`.** `kkd` runs under launchd or systemd-user and is restarted by it. Under `kkd --foreground`, the operator's supervisor restarts it. Restart recovery reads sqlite state. Thread identity and persisted lifecycle state survive reboots.
  - The active automation policy is reloaded from its stored row. An approval that was issued but not yet claimed is a durable row. It stays valid until its expiry.
- **`kkd` crashes during a freeze.**
  - Each discovered process identity was committed to `process_records` before it was signalled. The row includes its prior stop state and the freeze's lifecycle operation id.
  - On restart, `kkd` rebuilds the [frozen set](../appendix-a-glossary.md#frozen-set) from those rows.
  - The close order is one list: freeze, post-freeze recheck, holder scan, checkpoint, each child step, final proof, kiki-side termination with verified exit, terminal-container close request, post-exit filesystem recheck, workspace forget, directory delete. [`close-without-terminal`](../appendix-a-glossary.md#close-without-terminal) uses the same list after its preflight inventory and approval.
  - Before the [final proof](../appendix-a-glossary.md#final-proof), it performs verified resume. The same holds when a single frozen step runs past `[timeouts] frozen_step` before termination begins.
  - After the final proof, it continues the journal forward. Once termination has begun, a failure is `CloseFailed` or the plan's own failed state. It is never resume.
  - The filesystem watch died with the old process. So the [post-exit filesystem recheck](../appendix-a-glossary.md#post-exit-filesystem-recheck) re-reads the generation and fingerprint, and compares them with the final proof's journaled values.
  - A mismatch is `CloseFailed` or `DestroyFailed`, with files preserved.
- **`kkd` crashes during a hard pause.** A [hard pause](../appendix-a-glossary.md#hard-pause) is journaled. `agent_sessions.pause_state` is one of `None | Stopping | Stopped | Killed`, and `kkd` writes each value before it takes the matching step.
  - On restart, recovery rolls a hard pause forward to the kill.
  - Recovery never resumes a harness that was being retired.
- **`kkd` crashes while starting the server.** The `terminal_servers` row is still `Starting`.
  - On restart, `kkd` connects to the session's socket. If a server answers, `kkd` reads its peer identity and moves the row to `Open`.
  - If no server answers, `kkd` marks that start as failed and ends the row. It does not start again at once. It starts a server on demand, the next time a command needs one, with a new row.
- **`kkd` restarts while the Herdr server survives.** Agents keep running. This is the normal case, because the server runs in its own service-manager unit, or as a detached process under `kkd --foreground`.
  - `kkd` reconnects and verifies the peer's `(pid, start_time)` against its open `terminal_servers` row. Then it snapshots, runs the [orphan scan](../appendix-a-glossary.md#orphan-scan), and reconciles.
  - `agent` launchers reopen their supervision streams. `kkd` authenticates each one by its accepted peer process identity.
  - The in-memory `PassThrough` cache is gone. So the first pre-tool call from an incarnation that was already running before this `kkd` start is an unknown in-flight batch. The one exception is a hook payload that proves the call is the first call of a new [model turn](../appendix-a-glossary.md#model-turn). For an unknown batch, `kkd` leaves files untouched, hard-pauses the incarnation, and replaces it to establish a clean boundary.
  - A binding continues if its recorded launcher and harness process identities are still live under the same instance. The incarnation continues too, subject to the next rule.
  - A live launcher whose harness is gone keeps its binding and its `agent` role. The incarnation is retired without acknowledgement, [`AgentStatus`](../appendix-a-glossary.md#agentstatus) is `Crashed`, and the thread's lifecycle is unchanged.
  - A binding whose `agent` launcher is gone ends, and its thread raises [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing).
- **The harness exits while its launcher lives.**
  - The launcher reports the exit, re-reads the thread credential, and awaits the next gate. `kkd` rotates that credential when the incarnation ends. The rotation does not close the launcher's supervision stream or reject its exit report, because `kkd` authenticates an accepted launcher by its peer process identity.
  - The incarnation is retired without acknowledgement. The thread shows `blocked`, never working.
  - A replacement incarnation is a new `agent_sessions` row and a new one-use gate, awaited by the same accepted launcher. It needs no terminal provisioning.
  - Its gate is activated only after the harness-remnant check above passes.
  - Two paths start a replacement incarnation:
    - Kiki's own protocol restarts: a cascade hard restart or a `RestartStartup` replacement. These are daemon-initiated steps of the delivery protocol and need no one-shot approval of either kind.
    - The `kk repair` plan [`restart-agent`](../appendix-a-glossary.md#restart-agent), the explicit restart path. It is same-thread and needs no approval in thread context. `restart-agent` uses `RestartStartup` when an intent is pending.
  - Only the launcher's own exit, or the loss of its binding or server instance, ends the `agent` role and raises `TerminalMissing`. The restart plan for `TerminalMissing` needs approval.
  - In a group whose only pane is the `agent` pane, the launcher's exit also removes the whole Herdr workspace. This is because Herdr drops a workspace when its last pane's command exits, and reports only a pane-exit event.
- **The Herdr server crashes or is killed.** Its PTYs close.
  - Processes that ignored hangup or left their session can survive. They are absent from every terminal view. (Hangup is the signal a process gets when its terminal closes.)
  - `kkd` observes the connection error. It treats every binding of that instance as ended and retires every incarnation without acknowledgement. It runs the orphan scan before anything else.
  - `kkd` starts a fresh server only on demand, the next time a command such as `kk new`, `kk attach`, or a repair plan needs it. `kkd` itself started that server, so it gets an `Open` row, and each affected thread needs only `restart-terminal`. `kkd` starts no agent on its own: each affected thread raises `TerminalMissing`.
  - A terminal restart is the approved `kk repair` plan [`restart-terminal`](../appendix-a-glossary.md#restart-terminal), with a fresh credential, launch settings, gate, and handshake. It never reuses a remnant or [unbound container](../appendix-a-glossary.md#unbound-container).
  - `restart-terminal` is a journaled lifecycle operation with its own step list:
    1. It lists every remnant or unbound container tied to the thread, with the processes in each, for approval.
    2. It freezes those processes. If the freeze returns `Unknown`, it takes verified resume and the plan stops.
    3. It proves that each listed container holds exactly the processes recorded at freeze. Then it terminates them with verified exit and requests each container's close.
    4. It re-runs the holder scan and the orphan scan.
    5. Only then does it provision a fresh terminal group.
  - Its precondition is that no recorded process survives outside the listed containers. An unresolved [`OrphanedProcess`](../appendix-a-glossary.md#orphanedprocess) blocks the plan for its workspace until [`terminate-orphans`](../appendix-a-glossary.md#terminate-orphans) has run.
  - If the restart fails after provisioning, `TerminalMissing` stays open and the thread stays `ProjectionDiverged`. The half-made group is removed by [`cleanup-failed-restart`](../appendix-a-glossary.md#cleanup-failed-restart), under the same limits as [`cleanup-failed-create`](../appendix-a-glossary.md#cleanup-failed-create).
- **[Cold restore](../appendix-a-glossary.md#cold-restore).** A restarted server restores layout, labels, working directories, and the same public ids, with new processes.
  - Launch argv (the command and its arguments) is saved but not rerun. Launch environment and tokens are not kept.
  - A restored pane whose saved directory is gone has no process at all.
  - Herdr allocates workspace ids from a counter that resumes above the highest surviving id. So an id may recur for an unrelated new group.
  - A restored pane is a plain shell with no role, running in the jj workspace.
  - `kkd` handles a cold restore exactly as a server crash: new instance, ended bindings, orphan scan, `TerminalMissing`, and the same restart plan that closes remnant containers before provisioning.
  - A restored pane is never `Active` evidence. The generated configuration keeps Herdr from resuming agents itself.
- **Live handoff** is unsupported in v1, and `kkd` never initiates it. v1 does not re-prove survivors.
  - After an observed handoff, including Herdr's own handoff or upgrade, the socket's peer is a server `kkd` did not start.
  - `kkd` ends the old `terminal_servers` row, which ends its bindings and raises `TerminalMissing`. It records the new peer as `Unverified` and provisions nothing on it.
  - The fix is `replace-terminal-server`, which stops that server and every process in it. After it, each thread is brought back with `restart-terminal`.
- **A runtime call's reply is lost.** `kkd` never repeats a create or close blindly.
  - Provisioning recovers from a fresh snapshot and launcher reports. It rotates the [provision nonce](../appendix-a-glossary.md#provision-nonce) before any re-issued create call.
  - Close does not wait on the reply at all. Kiki has already terminated the frozen set with verified exit, and the close request is cleanup.
  - See [Provisioning](terminal-runtime.md#provisioning) and [Process supervision](terminal-runtime.md#process-supervision).
- **Creation or reopen fails after provisioning.** Automatic compensation (undoing the steps already completed) **may** close the provisioned group and remove the new jj workspace, but only while all three of these hold:
  - the [launch gate](../appendix-a-glossary.md#launch-gate) was never activated;
  - `ProcessSupervisor` shows the group contains nothing but kiki's own blocked launchers; and
  - the workspace still equals its initial [materialization](../appendix-a-glossary.md#materialization).

  Otherwise the saga stops with its projections intact. Cleanup is then an approved [repair plan](../appendix-a-glossary.md#repair-plan) that uses the close machinery: [`cleanup-failed-create`](../appendix-a-glossary.md#cleanup-failed-create) or [`cleanup-failed-reopen`](../appendix-a-glossary.md#cleanup-failed-reopen).

- **The ready handshake never arrives.** `kkd` waits up to `[timeouts] ready_handshake` (default `60s`) from launch. On expiry a creation becomes `CreateFailed`, and a reopen or restart takes its own failure state.
- **`kkd` is unreachable from the hook, or slow.** [`kk-hook`](../appendix-a-glossary.md#kk-hook) is a stateless client that makes one call. What happens depends on how far that call got.
  - **Not admitted in time.** After `hook_connect` expires the hook blocks the call and logs the gap, whether or not the marker exists.
  - **Admitted into a reconciliation.** Once `kkd` has admitted the call into a reconciliation, the hook waits up to `[timeouts] slow_path` (default `30s`). This is the [slow-path bound](../appendix-a-glossary.md#slow-path-bound). If it expires, or `kkd` crashes while it owns the reconciliation, the hook answers with a generic blocking deny ("kiki is reconciling; try again"). It never answers "continue". This is [failing closed](../appendix-a-glossary.md#fail-closed).
  - **After `kkd` comes back.** The `PassThrough` cache was in `kkd`'s memory and is gone. The first pre-tool call from an incarnation that was already running is an unknown in-flight batch, unless the hook payload proves it is the first call of a new model turn. `kkd` leaves files untouched and replaces the incarnation to establish a clean boundary.
  - The [cascade barrier](../appendix-a-glossary.md#delivery-barrier) for a blocked batch is durable in `sync_intents`. It survives the restart. An unprovable batch-completion boundary forces a hard restart with the saved payload.
  - **The barrier marker.** When `kkd` binds a `Block` for a thread, it first writes a durable [barrier marker](../appendix-a-glossary.md#barrier-marker) file in that thread's runtime directory, before it changes any file. It removes the file when the barrier lifts. After a crash, recovery removes it only after the reconciliation is resolved. This is how the stateless hook knows to block while `kkd` is down.
  - **A hook process that dies before answering.** A proof for each pinned harness version shows that the harness does not run the tool as if the hook had allowed it. If the proof fails, that harness version is unsupported for cascade delivery.
  - Missed transitions remain reconstructable from jj's operation DAG (its graph of operations). The next successful boundary probes actual files before mutation.
  - See [Harness adapter](harness-adapter.md).
- **A same-UID adversary** can read credentials and invoke `kk` directly. The daemon's authorization model reduces accidental and buggy agent blast radius. It does not defend against active malice. See [Authority](../04-authority.md).
