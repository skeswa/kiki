# Daemon

`kkd` is a single user-scoped daemon, opt-in per repository via `kk init`. The architectural anchor is tmux: one user-scoped daemon, many sessions, thin clients over stable IPC, no ownership of what happens inside a pane. `kkd` follows that shape.

## Lifecycle

- One `kkd` per user.
- First-run bootstrap: started on first `kk` invocation. State files in `~/.kiki/` are created with mode `0700`; the gRPC socket and credential files are mode `0600`.
- Reboot survival: `kkd` is intended to be resurrectable across restarts via launchd / systemd-user. Recovery on restart reads sqlite; threads survive crashes and reboots.
- Per-thread `ThreadController` actors supervise durable lifecycle sagas and die only after a thread is closed or destroyed coherently; cross-cutting components include the op-log watcher, cascade orchestrator, projection reconciler, and approval broker. AI and GitHub workers join later with their v1.x features.

## What the daemon owns

- All gRPC behavior. Every call goes through `AuthEnforcer`; a consequential operation atomically claims its method, target, argument, and rendered-plan-bound `HumanApproval` while creating the durable operation journal, then consumes it when that exact plan completes. Every parseable transport attempt produces exactly one SQLite audit row: in the target repo database when the repo resolves, otherwise in the user database.
- Durable creation, checkpoint, close, reopen, and repair sagas. The managed workspace's exact `@` is persisted as the live thread head; bookmarks are explicit checkpoints.
- The cascade state machine. It classifies observed jj transitions into `NativeRewrite`, `ParentAdvance`, `AlreadyAligned`, or `TopologyDiverged`; validates a strict linear owned stack; persists exact-base-transition `sync_intents`; binds a parallel-tool-batch barrier before mutation; and owns soft-batch or restart-startup delivery proof through acknowledgement.
- Projection reconciliation for workspace records, paths, bookmarks, and tmux sessions. Only unique identity-preserving normalization is automatic; ambiguous changes become named `kk repair` plans.
- The v1.x transcript JSONL tail. The per-(thread, session_id) offset advances atomically with `thread_messages` inserts so persisted state never diverges from inserted rows.
- Op-log watching. See [`op-log-watcher.md`](op-log-watcher.md).
- Auto-rename / auto-describe ownership and execution, when that v1.x feature ships.

## What the daemon does NOT own

- Active-thread focus. "Which thread am I in?" is discovered by the CLI's `ContextDiscovery` (env -> tmux session name -> cwd). `kk switch` is a summary lookup plus tmux client operation and needs no `HumanApproval`; there is no ambient operational Admin authority.
- The terminal. tmux owns sessions, panes, copy mode, scrollback. `kkd` creates panes and switches focus through the tmux CLI; it does not multiplex.
- jj revisions. `jj` owns revisions; `kkd` reacts to op-log events and issues thread-aware porcelain. Users can run `jj` directly any time and `kkd` reacts to whatever it sees.

## Op attribution

`kkd`'s own jj operations carry a `kk:` prefix in their op message and are recorded in `op_attribution` keyed on `op_id`. The watcher dedupes self-initiated ops so it does not classify them twice. The initiating reconciliation handler still compares the before/result operation views and records `NativeRewrite` intents for any other workspaces jj evolved.

## Failure model

- On daemon crash, in-flight gRPC calls fail; clients reconnect. Cascade crash safety comes from durable intent and barrier state plus post-stdout `MarkDelivered(intent_id, incarnation_id, model_turn_id, tool_batch_id)` ordering, not from the daemon staying up.
- On daemon restart, op-log catch-up walks every unprocessed operation reachable from the observed frontier through normalized parent edges, in topological order. It runs _before_ JSONL backfill so anchor lookups see current operation and workspace history.
- `kkd` is intended to be resurrectable by launchd or systemd-user. Restart recovery reads sqlite state; thread identity and persisted lifecycle state survive reboots.
- Before a batch has activated a cascade barrier, `kk-hook` may degrade to a cached batch-wide pass-through when `kkd` is unreachable and log the gap under `errors/<thread_id>.log`. If restart loses that cache and the in-flight batch is unknown, kiki leaves files untouched and replaces the incarnation to establish a clean boundary. Once reconciliation may have changed files, the durable barrier fails closed: every sibling call remains blocked, and an unprovable batch-completion boundary forces hard restart with the saved payload. Missed transitions remain reconstructable from jj's operation DAG, and the next successful boundary probes actual files before mutation. See [Harness adapter](harness-adapter.md).
- A same-UID adversary can read credentials and invoke `kk` directly. The daemon's authorization model reduces accidental and buggy agent blast radius; it does not defend against active malice — see [Authority](../06-authority.md).
