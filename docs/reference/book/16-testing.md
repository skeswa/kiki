# Testing

Tests should target observable behavior and persisted state, not private implementation details.

## Required high-value modules

Acceptance slice:

- `AncestryQuery`
- `OpAttribution`
- `MetadataLedger`
- `CascadeOrchestrator`
- `ConfigLoader`
- `ContextDiscovery`
- `AuthEnforcer`
- `ThreadTranscriptStore`
- `LogRenderer`
- `StatusRenderer`

Required alongside the v1.x polish surface that ships them:

- `AICompose`
- `SidebarController`
- `PaneLifecycle`
- `OverlayController` — open/close, NAVIGATE-mode transitions, preview-mode toggling (`t`/`d`/`c`), chord-ribbon adaptation by selection, narrow-terminal degradation, mouse click-to-focus
- `ToastQueue` — TTL expiry, click dismiss, action-invocation dismiss, row-focus acknowledgement dismiss, coalescing of cascade-applied events
- `FormController` — spawn-card field navigation, destructive-confirmation modal flow

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
- `kk-hook` returns `continue` and writes to `~/.kiki/repos/<repo_id>/errors/<thread_id>.log` when it cannot reach `kkd` within its connect/overall budget; it does not block the agent's tool call. A reconciliation pending during the outage must still be delivered on the next successful PreToolUse round-trip. If the watcher saw the trigger, durable state lives in `sync_intents`; otherwise restart catch-up reconstructs it from jj's op log. If the agent edited the stale tree during the outage, the next probe enters `RecoveryRequired` rather than treating it as clean.
- Native ancestor evolution: amending A causes jj to evolve B's repository working-copy commit. The classifier records `NativeRewrite` with the exact old-base → evolved-base ids, performs no redundant rebase, and at B's safe boundary verifies that B's current commit still contains that base before materializing it.
- Parent-tip advance: adding A2 without rewriting A1 leaves B on A1. The classifier records `ParentAdvance` with exact destination A2; B's boundary performs the explicit owned-stack rebase and materializes its result.
- Multi-workspace cascade in A→B→C: one jj operation may logically evolve both B and C. Both receive independent `NativeRewrite` intents immediately from before/result operation comparison; B and C materialize at their respective boundaries. If an explicit advance of B evolves C, the initiating reconciliation handler records C's intent even though the watcher skips the attributed op.
- Direct human materialization: running `jj workspace update-stale` directly in stale B may change B's files without creating a new op-log head. The boundary probe detects `FreshClean` or `FreshDirty`, performs no duplicate update, and still delivers context for the unresolved intent.
- Coalescing updates one pre-materialization intent's base transition and normalized trigger rows. Once payload preparation begins, later work receives a new ordered intent and cannot mutate the saved delivery.
- A stale workspace with unsnapshotted edits or an `Unknown` probe result enters `RecoveryRequired`, hard-pauses the agent, enumerates divergent successors outside the workspace, and never resumes on a clean successor that hides those edits.
- `LogRenderer` and `StatusRenderer` produce monochrome-distinguishable output when `NO_COLOR=1` is set; every state in the cascade, agent, and lifecycle vocabularies has a distinct glyph or label without color.

## Cascade crash tests

The cascade tests must cover:

- pre-stdout hook crash
- pre-stdout hook crash followed by a newly enqueued cascade
- crash between stdout and `MarkDelivered`
- crash after `MarkDelivered`
- agent crash after delivery but before acknowledgement
- resume with a delivered-but-unacknowledged intent
- multiple cascades before first hook coalescing into one delivery
- deliverable-intent lookup and byte-identical retry for both `Materialized` and `Delivered`
- daemon crash and recovery at every `sync_intent` state, including `RecoveryRequired`
- `WorkspaceProbe` returning `FreshClean`, `FreshDirty`, `StaleClean`, `StaleDirty`, and `Unknown`, plus fingerprint drift immediately before mutation
- `jj workspace update-stale` with clean files, unsnapshotted edits, conflicts, direct materialization that creates no new operation, and a concurrently advanced base transition
- recovery verifies edit-bearing divergent successors before choosing the visible result; ambiguous recovery requires human selection
- process restart with a reused harness session id retires the old runtime incarnation without acknowledgement and redelivers the saved payload
- `--no-integrate-operation` plus `jj op integrate` feasibility for planned `ParentAdvance`, including concurrent external operations

They must also cover the worked scenarios in [Cascade](07-cascade.md): native ancestor rewrite, parent bookmark advance, conflict exposure, direct human materialization, and agent crash after delivery. These are scenario tests over observable state, not assertions about private function boundaries.

## Module-specific obligations

`MetadataLedger` tests cover content-hash ownership, trailer independence, sticky human bookmark renames, squash inheritance toward human ownership, and opt-back-in refresh.

`AuthEnforcer` tests cover Admin-only rejection for thread-scoped credentials, thread-scoped rejection across sibling threads, revoked and malformed credentials, audit-log rows for accepted and rejected parseable attempts, and the MCP status-code ordering in [Roadmap](18-roadmap.md) when that surface ships.

`ThreadTranscriptStore` tests cover FTS search, author/direction preservation, change-aligned reads, tombstoned and redirected changes, JSONL rotation/truncation recovery, offset and row insertion in one transaction, reopen catch-up recursion prevention, `pending_kkd_prepends` FIFO matching, cascade-injection row idempotency, and intent-pinned anchors.

`LogRenderer` tests cover stack-aware expansion, collapsed siblings and unrelated threads, `--no-stack`, `--all`, `--wide`, `-r <revset>` disabling collapse, and parser errors when `-r` is combined with collapse flags.

`StatusRenderer` tests cover the kiki header, omission of empty PR/CI/agent fields, follows and children rows, the three-valued cascade state, `--diff`, `--diff --stat`, and `--no-jj`.

`SidebarController`, `OverlayController`, `ToastQueue`, `FormController`, and `PaneLifecycle` tests cover navigation versus destructive action gating, preview toggles, confirmation cards, disconnected/reconnecting rendering, cursor preservation across event streams, toast TTL/click/action behavior, spawn form navigation, pane ensure-on-attach, user-killed-pane non-respawn during a live session, terminal-too-narrow warnings, and repo-shared `[ui]` rejection.

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
