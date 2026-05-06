# Daemon

`kkd` is a single user-scoped daemon, opt-in per repository via `kk init`. The tmux analogy is the architectural anchor: tmux is a single user-scoped daemon serving sessions across any directory; it does not gatekeep what you do inside a pane; clients (the `tmux` CLI) are thin views over a stable IPC. `kkd` is the same shape.

## Lifecycle

- One `kkd` per user.
- First-run bootstrap: started on first `kk` invocation. State files in `~/.kiki/` are created with mode `0700`; the gRPC socket and credential files are mode `0600`.
- Reboot survival: `kkd` is intended to be resurrectable across restarts via launchd / systemd-user. Recovery on restart reads sqlite; threads survive crashes and reboots.
- Per-thread `ThreadController` actors die with their thread; cross-cutting components (op-log watcher, cascade orchestrator, AI background queue, GitHub poller) are daemon-wide.

## What the daemon owns

- All gRPC behavior. Every call goes through `AuthEnforcer`. Audit rows are written for every parseable transport attempt.
- The cascade state machine. Per-thread `cascade_lock` is held only while applying the rebase + composing the synthetic payload + persisting to `cascade_outbox`.
- The transcript JSONL tail. The per-(thread, session_id) offset advances atomically with `thread_messages` inserts so persisted state never diverges from inserted rows.
- Op-log watching. See [`op-log-watcher.md`](op-log-watcher.md).
- Auto-rename / auto-describe execution loop, when those ship. The `MetadataLedger` content-hash ownership rule is the v1-required foundation; the execution loop is stretch.

## What the daemon does NOT own

- Active-thread focus. "Which thread am I in?" is discovered by the CLI's `ContextDiscovery` (env → tmux session name → cwd). `kk switch` is a tmux client operation, not a daemon mutation. `AuthEnforcer` therefore does not gate switch on `Admin` — see [`../specs/auth.md`](../specs/auth.md).
- The terminal. tmux owns sessions, panes, copy mode, scrollback. `kkd` creates panes and switches focus through the tmux CLI; it does not multiplex.
- jj revisions. `jj` owns revisions; `kkd` reacts to op-log events and issues thread-aware porcelain. Users can run `jj` directly any time and `kkd` reacts to whatever it sees.

## Op attribution

`kkd`'s own jj operations carry a `kk:` prefix in their op message and are recorded in `op_attribution` keyed on `op_id`. The watcher dedupes self-initiated ops so cascade does not re-fire on `kkd`'s own writes.

## Failure model

- On daemon crash, in-flight gRPC calls fail; clients reconnect. The cascade state machine's crash-safety guarantees come from the `cascade_outbox` + `MarkDelivered` ordering, not from the daemon staying up.
- On daemon restart, the op-log catch-up (read `jj op log` since the last persisted cursor) runs _before_ JSONL backfill, so anchor lookups see a current `op_history`.
- A same-UID adversary can read credentials and invoke `kk` directly. The daemon's authorization model reduces accidental and buggy agent blast radius; it does not defend against active malice — see [`../specs/auth.md`](../specs/auth.md).
