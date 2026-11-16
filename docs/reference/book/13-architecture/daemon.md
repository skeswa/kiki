# Daemon

`kkd` is a single user-scoped daemon, opt-in per repository via `kk init`. It is a coordinator, not a terminal host: one user-scoped daemon, many threads, thin clients over stable IPC, and no ownership of what is drawn inside a pane. Terminals live in a separate, dedicated Herdr server that `kkd` starts, verifies, observes, and never trusts as an authority. [Terminal runtime](terminal-runtime.md) defines that boundary; this chapter covers the daemon's side of it.

## Lifecycle

- One `kkd` per user.
- First-run bootstrap: started on first `kk` invocation. State files in `~/.config/kiki/` are created with mode `0700`; the gRPC socket and credential files are mode `0600`.
- Reboot survival: `kkd` is intended to be resurrectable across restarts via launchd / systemd-user. Recovery on restart reads sqlite; threads survive crashes and reboots.
- Per-thread `ThreadController` actors supervise durable lifecycle sagas and die only after a thread is closed or destroyed coherently; cross-cutting components include the op-log watcher, cascade orchestrator, projection reconciler, terminal runtime adapter, process supervisor, and approval broker. AI and GitHub workers join later with their v1.x features.

## What the daemon owns

- All gRPC behavior. Every call goes through `AuthEnforcer`; a consequential operation atomically claims its method, target, argument, and rendered-plan-bound `HumanApproval` while creating the durable operation journal, then consumes it when that exact plan completes. Every parseable transport attempt produces exactly one SQLite audit row: in the target repo database when the repo resolves, otherwise in the user database.
- Durable creation, checkpoint, close, reopen, and repair sagas. The managed workspace's exact `@` is persisted as the live thread head; bookmarks are explicit checkpoints.
- The cascade state machine. It classifies observed jj transitions into `NativeRewrite`, `ParentAdvance`, `AlreadyAligned`, or `TopologyDiverged`; validates a strict linear owned stack; persists exact-base-transition `sync_intents`; binds a parallel-tool-batch barrier before mutation; and owns soft-batch or restart-startup delivery proof through acknowledgement.
- Projection reconciliation for workspace records, paths, bookmarks, and terminal bindings. Only unique identity-preserving normalization is automatic; ambiguous changes become named `kk repair` plans.
- The dedicated Herdr server's lifecycle and generated configuration, terminal-group provisioning and close through `TerminalRuntime`, and one-way presentation publishing. See [The dedicated Herdr server](#the-dedicated-herdr-server).
- OS process proofs through `ProcessSupervisor`: process identity, freeze, verified resume, verified exit, workspace-holder inventory, and the orphan scan. A runtime reply is never an input to these proofs except as a source of root process ids that the supervisor re-reads from the OS.
- The v1.x transcript JSONL tail. The per-(thread, session_id) offset advances atomically with `thread_messages` inserts so persisted state never diverges from inserted rows.
- Op-log watching. See [`op-log-watcher.md`](op-log-watcher.md).
- Auto-rename / auto-describe ownership and execution, when that v1.x feature ships.

## What the daemon does NOT own

- Active-thread focus. Which terminal a human is looking at belongs to each Herdr client. `kk switch` is a summary lookup in `kkd` plus a caller-local focus request made by `kk` through `TerminalClient`; it mutates no terminal, needs no `HumanApproval`, and there is no mutating `Switch` RPC. `kkd` never calls a focus method on a viewer's behalf, and there is no ambient operational Admin authority. Caller-local focus requires the runtime capability `client_targeted_focus`; without it `kk switch` fails naming the capability, and only the explicit `kk switch --all-clients` moves every attached client.
- The terminal. Herdr owns PTYs, panes, tabs, layout, scrollback, copy mode, input, rendering, its native sidebar, and toasts. `kkd` provisions and closes terminal groups and publishes labels and tokens through Herdr's JSON socket API; it does not multiplex, render, or read a decision back out of anything Herdr displays. `kkd` never calls Herdr's `worktree.*` methods.
- jj revisions. `jj` owns revisions; `kkd` reacts to op-log events and issues thread-aware porcelain. Users can run `jj` directly any time and `kkd` reacts to whatever it sees.

## Context discovery

"Which thread am I in?" is resolved by `ContextDiscovery`, in this order:

1. An explicit CLI target.
2. `KIKI_THREAD_ID` in the environment. Kiki sets it explicitly on every role pane; Herdr does not copy one pane's explicit environment into a split.
3. Herdr pane identity. When the caller's `HERDR_SOCKET_PATH` is kiki's dedicated server, `kk` sends the caller's `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, and `HERDR_PANE_ID` to `kkd`, which resolves them against the bindings of the current `server_instance_id`. This is how a pane the user split natively resolves to its thread. Pane identity from any other Herdr server is ignored.
4. The current working directory.

Environment text is a locator, not authority. Herdr ids never authorize anything and never substitute for a credential. A ref observed under the current server instance and matching a current binding may locate the caller's contextual thread; after that, the thread's own credential is what authorizes. A Herdr id that matches no current binding on the current instance resolves nothing and falls through to the next step.

## The dedicated Herdr server

`kkd` owns one named Herdr server per user. It is separate from the user's default Herdr server, and `kkd` never reads or changes that server's configuration, state, or terminals.

- **Generate.** Before starting the server, `kkd` writes the server's configuration file under kiki's Herdr configuration root (`[paths] herdr_dir`, default `<user_state_dir>/herdr/`). The file disables automatic agent resume. When the v1.x sidebar tokens and keybindings ship, it also declares those tokens and binds those keys. Kiki owns that file; user edits to it are overwritten.
- **Find or start.** The server is addressed by that configuration root plus the session name (`terminal.session`); Herdr derives the socket and saved state beneath that root, and `kkd` names no socket path of its own. `kkd` connects to the derived socket. If nothing answers, it starts the server with `terminal.herdr_bin`, the configuration root, and the session name. Starting the server creates no terminal group and starts no agent. `kk attach` asks `kkd` to perform this same step before it attaches a client.
- **Verify.** On every connection `kkd` reads the ping reply, which returns Herdr's version, protocol number, and capabilities, and checks them against the supported range it pins. An unsupported server is not used: terminal lifecycle operations fail with an actionable error, and existing threads keep their recorded state. `RuntimeCapabilities` is derived only from that reply. Herdr ignores unknown request parameters, so `kkd` never probes for an extension by sending it.
- **Identify.** `kkd` reads the socket peer's process identity `(pid, start_time)` from the OS on every connection. The `server_instance_id` is kiki's row id for one such observed peer. Herdr's public API reports no instance identity. Every recorded Herdr workspace, tab, and pane id is stored with the instance it was read under and is meaningless under any other.
- **Observe.** `kkd` subscribes to events and then takes a full snapshot. Events are wake-up hints; the snapshot is the observation.
- **Publish.** `kkd` publishes a label, and in v1.x tokens, only to a terminal group with a current binding. A remnant container left by a restore keeps whatever label Herdr restored and receives no kiki tokens.

### Runtime reconciliation

`kkd` resubscribes, takes a fresh snapshot, reconciles every terminal binding, and republishes presentation after each of these: daemon start, a reconnect, any connection error, a reported loss of events, and a changed `server_instance_id`. Reconciliation compares each binding's recorded handles and launcher process identities with the snapshot and with the OS. A terminal change that an in-flight lifecycle journal expected belongs to that journal. Every other difference becomes a projection issue under the rules in [Threads](../03-threads.md#projection-divergence-and-repair). Nothing is reconstructed from Herdr's event history, labels, or tokens.

### Orphan scan

A process can outlive its pane, its terminal group, and the terminal server. `kkd` asks `ProcessSupervisor` which recorded process identities are still alive and which same-UID processes hold each managed workspace:

- at daemon start, before any thread is reported `Active`;
- whenever the `server_instance_id` changes;
- before provisioning a replacement terminal group or starting a replacement incarnation;
- before any step that forgets or deletes a jj workspace.

`OrphanedProcess` is raised for a thread in two cases: a recorded process identity is alive without a current binding, or a same-UID process holds the workspace and belongs to no pane in the current runtime snapshot. Processes that are members of a pane in the snapshot — `user` panes and remnant panes included — are accounted for by the pane and are not orphans. While the issue is unresolved, `kkd` starts no replacement agent in that workspace and deletes nothing. `kkd` never signals a process whose identity it did not record itself.

## Op attribution

`kkd`'s own jj operations carry a `kk:` prefix in their op message and are recorded in `op_attribution` keyed on `op_id`. The watcher dedupes self-initiated ops so it does not classify them twice. The initiating reconciliation handler still compares the before/result operation views and records `NativeRewrite` intents for any other workspaces jj evolved.

## Failure model

- On daemon crash, in-flight gRPC calls fail; clients reconnect. Cascade crash safety comes from durable intent and barrier state plus post-stdout `MarkDelivered(intent_id, incarnation_id, model_turn_id, tool_batch_id)` ordering, not from the daemon staying up.
- On daemon restart, op-log catch-up walks every unprocessed operation reachable from the observed frontier through normalized parent edges, in topological order. It runs _before_ JSONL backfill so anchor lookups see current operation and workspace history.
- `kkd` is intended to be resurrectable by launchd or systemd-user. Restart recovery reads sqlite state; thread identity and persisted lifecycle state survive reboots.
- **`kkd` restarts while the Herdr server survives.** Agents keep running. `kkd` reconnects, verifies the `server_instance_id` against its record, snapshots, runs the orphan scan, and reconciles. A binding whose recorded launcher and harness process identities are still live under the same instance continues, and the harness's next hook round-trip re-proves the incarnation as usual. A live launcher whose harness is gone keeps its binding and its `agent` role: the incarnation is retired without acknowledgement, `AgentStatus` is `Crashed`, and the thread's lifecycle is unchanged. A binding whose `agent` launcher is gone ends, and its thread raises `TerminalMissing`.
- **The harness exits while its launcher lives.** The launcher reports the exit and awaits the next gate. The incarnation is retired without acknowledgement and the thread shows `blocked`, never working. A replacement incarnation — cascade `RestartStartup` or an explicit restart — is a new `agent_sessions` row and a new one-use gate awaited by the same accepted launcher, after the orphan scan. It needs no terminal provisioning and no approval beyond what that cascade or restart path already requires. Only the launcher's own exit, or the loss of its binding or server instance, ends the `agent` role and raises `TerminalMissing`, whose restart plan needs approval.
- **The Herdr server crashes or is killed.** Its PTYs close. Processes that ignored hangup or left their session can survive and are absent from every terminal view. `kkd` observes the connection error, treats every binding of that instance as ended, retires every incarnation without acknowledgement, and runs the orphan scan before anything else. `kkd` may start a fresh server so that `kk attach` and repair work, but it starts no agent on its own: each affected thread raises `TerminalMissing`, and restart is a `kk repair` plan with a fresh credential, launch settings, gate, and handshake. An unresolved `OrphanedProcess` blocks that plan for its workspace.
- **Cold restore.** A restarted server restores layout, labels, working directories, and the same public ids, with new processes. Launch argv is saved but not rerun; launch environment and tokens are not kept. Herdr workspace ids also recur for unrelated new groups. A restored pane is a plain shell with no role. `kkd` handles it exactly as a server crash: new instance, ended bindings, orphan scan, `TerminalMissing`. A restored pane is never `Active` evidence, and the generated configuration keeps Herdr from resuming agents itself.
- **Live handoff** is unsupported in v1 and `kkd` never initiates it. An observed instance change with surviving recorded processes blocks boundary mutation and raises `TerminalMissing` with that evidence.
- **A runtime call's reply is lost.** `kkd` never repeats a create or close blindly. Provisioning recovers from a fresh snapshot and launcher reports; close proceeds on `ProcessSupervisor` evidence. See [Provisioning](terminal-runtime.md#provisioning) and [Process supervision](terminal-runtime.md#process-supervision).
- Before a batch has activated a cascade barrier, `kk-hook` may degrade to a cached batch-wide pass-through when `kkd` is unreachable and log the gap under `errors/<thread_id>.log`. If restart loses that cache and the in-flight batch is unknown, kiki leaves files untouched and replaces the incarnation to establish a clean boundary. Once reconciliation may have changed files, the durable barrier fails closed: every sibling call remains blocked, and an unprovable batch-completion boundary forces hard restart with the saved payload. Missed transitions remain reconstructable from jj's operation DAG, and the next successful boundary probes actual files before mutation. See [Harness adapter](harness-adapter.md).
- A same-UID adversary can read credentials and invoke `kk` directly. The daemon's authorization model reduces accidental and buggy agent blast radius; it does not defend against active malice — see [Authority](../04-authority.md).
