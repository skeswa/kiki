# Testing spec

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
- `TranscriptStore`
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
