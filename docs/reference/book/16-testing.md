# Testing

Tests should target observable behavior and persisted state, not private implementation details.

## Required high-value modules

- `AncestryQuery`
- `OpAttribution`
- `MetadataLedger`
- `CascadeOrchestrator`
- `ConfigLoader`
- `ContextDiscovery`
- `AICompose`
- `AuthEnforcer`
- `ThreadTranscriptStore`
- `LogRenderer`
- `StatusRenderer`
- `SidebarController` if TUI/sidebar ships
- `PaneLifecycle` if persistent sidebar ships
- `OverlayController` if overlay TUI ships — open/close, NAVIGATE-mode transitions, preview-mode toggling (`t`/`d`/`c`), chord-ribbon adaptation by selection, narrow-terminal degradation, mouse click-to-focus
- `ToastQueue` if overlay TUI ships — TTL expiry, click dismiss, action-invocation dismiss, row-focus acknowledgement dismiss, coalescing of cascade-applied events
- `FormController` if overlay TUI ships — spawn-card field navigation, destructive-confirmation modal flow

## Regression tests for resolved spec conflicts

- `kk ls --all` includes closed threads but does not widen repo scope.
- `kk ls --all-repos` widens repo scope independently of lifecycle scope.
- Cooperative workspace isolation is documented and no test claims security isolation.
- Kiki-owned workspace files under `.kiki/` do not block `kk close`.
- User-created untracked or ignored files still block or prompt during `kk close`.
- Stop hook is not installed in v1 unless behavior is specified and tested.

## Cascade crash tests

The cascade tests must cover:

- pre-stdout hook crash
- pre-stdout hook crash followed by a newly enqueued cascade
- crash between stdout and `MarkDelivered`
- crash after `MarkDelivered`
- agent crash after delivery but before acknowledgement
- resume with delivered-but-unacknowledged outbox row
- multiple cascades before first hook coalescing into one delivery
- `cascade_outbox` lookup ignores `delivered_at` and keys on `applied_cascade_seq > acknowledged_cascade_seq`

They must also cover the worked scenarios in [Cascade](07-cascade.md): ancestor amend, parent bookmark advance, textual conflict, external jj op, and agent crash after delivery. These are scenario tests over observable state, not assertions about private function boundaries.

## Module-specific obligations

`MetadataLedger` tests cover content-hash ownership, trailer independence, sticky human bookmark renames, squash inheritance toward human ownership, and opt-back-in refresh.

`AuthEnforcer` tests cover Admin-only rejection for thread-scoped credentials, thread-scoped rejection across sibling threads, revoked and malformed credentials, audit-log rows for accepted and rejected parseable attempts, and the MCP status-code ordering in [Roadmap](18-roadmap.md) when that surface ships.

`ThreadTranscriptStore` tests cover FTS search, author/direction preservation, change-aligned reads, tombstoned and redirected changes, JSONL rotation/truncation recovery, offset and row insertion in one transaction, reopen catch-up recursion prevention, `pending_kkd_prepends` FIFO matching, cascade-injection row idempotency, and outbox-pinned anchors.

`LogRenderer` tests cover stack-aware expansion, collapsed siblings and unrelated threads, `--no-stack`, `--all`, `--wide`, `-r <revset>` disabling collapse, and parser errors when `-r` is combined with collapse flags.

`StatusRenderer` tests cover the kiki header, omission of empty PR/CI/agent fields, follows and children rows, the three-valued cascade state, `--diff`, `--diff --stat`, and `--no-jj`.

`SidebarController`, `OverlayController`, `ToastQueue`, `FormController`, and `PaneLifecycle` are required only if their UI surfaces ship. Their tests cover navigation versus destructive action gating, preview toggles, confirmation cards, disconnected/reconnecting rendering, cursor preservation across event streams, toast TTL/click/action behavior, spawn form navigation, pane ensure-on-attach, user-killed-pane non-respawn during a live session, terminal-too-narrow warnings, and repo-shared `[ui]` rejection.

## Fakes

Deep-module tests should use fakes for:

- `JjBackend`
- `TmuxBackend`
- `GitHubBackend`
- `Harness`
- `TranscriptAdapter`
- notification sink
- clock
- filesystem event source

The fakes should expose edge cases directly: op storms, hook crashes, JSONL rotation, out-of-order timestamps, remote divergence, and agent session restart.

## Integration-only surfaces

The real `jj`, `gh`, Claude Code, ratatui terminal loop, tmux pane wiring, and fsnotify watcher are smoke-tested or integration-tested. Their detailed behavior is dominated by upstream tools. Core interpretation logic belongs in deep-module tests against fakes.
