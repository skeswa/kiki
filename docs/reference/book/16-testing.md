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
- `kk init` is idempotent in an already-registered repo (status print + exit 0, no mutation).
- `kk init` does not pre-validate harness binaries; missing-harness errors surface at `kk new` time only.
- A thread whose workspace directory has been deleted out-of-band transitions to `Orphaned` at next daemon boot or `kk ls`, fires exactly one notification, and is not auto-recreated or auto-Closed.
- `kk-hook` returns `continue` and writes to `<workspace>/kiki-errors.log` when it cannot reach `kkd` within its connect/overall budget; it does not block the agent's tool call. A cascade that was pending during the outage must still be delivered on the next successful PreToolUse round-trip after `kkd` returns — pass-through defers delivery, never drops it. The deferred state lives in `pending_cascade_seq` and `context_queue` when the watcher saw the trigger before the outage; otherwise the trigger is reconstructed from jj's op log by the daemon-restart op-log catch-up. `cascade_outbox` is asserted to remain empty for unapplied cascades — it only holds applied-but-not-yet-acknowledged rows.
- Multi-hop cascade in A→B→C: amending A enqueues cascade only on B (via the watcher's external-op route). C's cascade is enqueued only after B's `PreToolUseDecision` applies the rebase, and the enqueue happens via the orchestrator's internal-propagation route — not by the watcher reacting to B's kkd-initiated rebase op (which must remain `op_attribution`-skipped). The internal-propagation enqueue must be in the same transaction as the `cascade_outbox` persist for B.
- `LogRenderer` and `StatusRenderer` produce monochrome-distinguishable output when `NO_COLOR=1` is set; every state in the cascade, agent, and lifecycle vocabularies has a distinct glyph or label without color.

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
