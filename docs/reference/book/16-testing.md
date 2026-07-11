# Testing

Tests should target observable behavior and persisted state, not private implementation details.

## Required high-value modules

Acceptance slice:

- `AncestryQuery`
- `OpAttribution`
- `CascadeOrchestrator`
- `ThreadLifecycleSaga`
- `ProjectionReconciler`
- `ConfigLoader`
- `ContextDiscovery`
- `AuthEnforcer`
- `ApprovalBroker`
- `LogRenderer`
- `StatusRenderer`

Required alongside the v1.x polish surface that ships them:

- `AICompose`
- `MetadataLedger`
- `ThreadTranscriptStore`
- `SidebarController`
- `PaneLifecycle`
- `OverlayController` — open/close, NAVIGATE-mode transitions, preview-mode toggling (`t`/`d`/`c`), chord-ribbon adaptation by selection, narrow-terminal degradation, mouse click-to-focus
- `ToastQueue` — TTL expiry, click dismiss, action-invocation dismiss, row-focus acknowledgement dismiss, coalescing of cascade-applied events
- `FormController` — spawn-card field navigation and daemon-issued approval-card flow

## Regression tests for resolved spec conflicts

- `kk ls --all` includes closed threads but does not widen repo scope.
- `kk ls --all-repos` widens repo scope independently of lifecycle scope.
- Cooperative workspace isolation is documented and no test claims security isolation.
- Kiki-owned launch settings and centralized state outside the workspace do not block `kk close`; a hash-owned `.claude/settings.local.json` fallback is ignored only while it still matches kiki's recorded bytes.
- User-created untracked or ignored files still block or prompt during `kk close`.
- Stop hook is not installed in v1 unless behavior is specified and tested.
- Managed Claude sessions prove that kiki is the sole matching `PreToolUse` hook. A project or user `PreToolUse` fixture must not execute in the managed process, and no test may claim kiki merely runs before concurrently dispatched user hooks.
- Launch-scoped settings isolation leaves tracked `.claude/settings.json` and user-global settings byte-identical. Where the fallback is exercised, it merges only `.claude/settings.local.json`, restores it only from the expected kiki-owned hash, and reports concurrent user edits instead of overwriting them.
- Unrelated Claude hook events remain enabled only for an adapter/version fixture that proves they cannot race workspace reconciliation or add another matching `PreToolUse` hook.
- `kk init` is idempotent in an already-registered repo (status print + exit 0, no mutation).
- `kk init` does not pre-validate harness binaries; missing-harness errors surface at `kk new` time only.
- `kk init` succeeds when `gh` is missing or unauthenticated. The first GitHub-backed command performs the check and reports the actionable error without corrupting local state.
- A thread whose workspace directory is deleted out of band records `ProjectionDiverged { reason: WorkspaceDirectoryMissing }` at daemon boot or `kk ls`, fires exactly one notification, and is neither recreated nor reclassified automatically.
- Creation crash injection at every journal step leaves `Creating` or `CreateFailed`; gate activation and process exec remain `Creating`, and only the matching ready handshake may enter `Active`. The launcher cannot pass its database-backed gate before credentials, exclusive hooks, live head, checkpoint, and tmux projections are durable. Restart adoption must distinguish an activated gate, an exec'd process, and a ready incarnation without duplicating any external resource.
- Reopen stays `Closed` while its durable journal recreates projections. Crash injection at every step either adopts the exact resource, compensates to `Closed`, or records a stable repair plan; it never exposes `Active` before a matching ready handshake, and every new incarnation independently re-proves exclusive hook control.
- Close freezes the tmux pane root processes and every descendant to a fixed point, records prior stopped state, proves no descendant escaped, and refuses quiescence when a same-UID process outside that set has a cwd, root, mapping, or open descriptor in the workspace. It checkpoints the exact pinned commit with a non-snapshotting jj command, verifies the armed filesystem generation and frozen workspace fingerprint, synchronously reconciles/detaches children, repeats the holder/fingerprint proof, and only then kills the session. A failed proof or child detach resumes and verifies the original process tree before returning `Active`; failed resume becomes `CloseFailed`. Crashes after proof or session kill resume the idempotent journal rather than guessing from filesystem presence.
- A close approval is bound to the rendered plan and preflight fingerprint. Drift discovered after freeze causes a verified resume and a fresh plan/approval; the daemon never prompts while leaving a session frozen.
- Workspace-record, path, bookmark, and session mismatches produce durable projection issues. Only unique identity-preserving normalization auto-repairs; every ambiguous plan uses a stable repair id that becomes stale when observed state changes. Bookmark-only divergence continues safe workspace-head tracking and follows classification, session divergence continues observation but suspends boundary mutation, and workspace identity/path ambiguity suspends both.
- A `SessionMissing` repair can restart to `Active` or execute a stable complete-close plan directly to `Closed`. Adopting a moved bookmark for a closed thread succeeds only when the exact observed commit satisfies archived topology checks and updates checkpoint and head together. Projection mismatches created by an in-flight creation or close saga fail that saga rather than switching to `ProjectionDiverged`.
- `kk-hook` returns `continue` and writes to `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log` when it cannot reach `kkd` within its connect/overall budget; it does not block the agent's tool call. A reconciliation pending during the outage must still be delivered on the next successful PreToolUse round-trip. If the watcher saw the trigger, durable state lives in `sync_intents`; otherwise restart catch-up reconstructs it from jj's op log. If the agent edited the stale tree during the outage, the next probe enters `RecoveryRequired` rather than treating it as clean.
- Once a cascade delivery barrier is active, daemon outage no longer passes tools through: every call in that tool batch is blocked until a matching `PostToolBatch` completes the barrier or the adapter takes the hard-restart path.
- The `Block` admission and complete soft-barrier identity commit before the first reconciliation mutation. Crash injection between every probe, jj, filesystem, and SQLite step must never leave changed files with an unbound batch.
- Native ancestor evolution: amending A causes jj to evolve B's repository working-copy commit. The classifier records `NativeRewrite` with the exact old-base → evolved-base ids, performs no redundant rebase, and at B's safe boundary verifies that B's current commit still contains that base before materializing it.
- Parent-head advance: adding A2 in A's managed workspace updates A's persisted live head while its checkpoint bookmark may remain on A1. The classifier records `ParentAdvance` from the exact live head; B's boundary rebases only the validated single-parent owned chain. Merge, multiple-root, or foreign topology stops as `TopologyDiverged`.
- Successful `ParentAdvance` persists B's actual result as `threads.thread_head_commit_id` in the same transaction as the materialized intent; the watcher may skip the attributed jj operation without losing that head advance.
- Multi-workspace cascade in A→B→C: one jj operation may logically evolve both B and C. Both receive independent `NativeRewrite` intents immediately from before/result operation comparison; B and C materialize at their respective boundaries. If an explicit advance of B evolves C, the initiating reconciliation handler records C's intent even though the watcher skips the attributed op.
- Direct human materialization: running `jj workspace update-stale` directly in stale B may change B's files without creating a new op-log head. The boundary probe detects `FreshClean` or `FreshDirty`, performs no duplicate update, and still delivers context for the unresolved intent.
- Coalescing updates one pre-materialization intent's base transition and normalized trigger rows. Once payload preparation begins, later work receives a new ordered intent and cannot mutate the saved delivery.
- A stale workspace with unsnapshotted edits or an `Unknown` probe result enters `RecoveryRequired`, hard-pauses the agent, enumerates divergent successors outside the workspace, and never resumes on a clean successor that hides those edits.
- Watcher restart from a multi-parent or divergent jj operation graph traverses all reachable, unprocessed ancestors from the persisted frontier in topological order. Tests must fail any implementation that stores one parent or advances one linear cursor through the operation DAG.
- Creating a follows edge and detaching one both pin an exact operation view and synchronously refresh affected live heads before choosing or discarding an anchor. A lagging asynchronous watcher cannot make either command lose a parent or child advance.
- `kk thread destroy` deletes kiki projections and records only after a confirmed exact plan. It preserves jj revisions by default; `--abandon-revisions` may abandon only the validated, unreferenced, single-parent owned chain named in a separate approved plan, and refuses shared, foreign, followed, or ambiguous topology.
- Destroy crash injection before and after bookmark deletion, optional exact revision abandonment, session/workspace cleanup, and tombstoning yields only the recorded `DestroyCommit`, `DestroyFailed`, or `Destroyed` outcome. After the first irreversible step, no recovery path relabels the thread `Active`, `Closed`, or `ProjectionDiverged`; `kk repair` can only finish the exact approved plan or invoke explicit jj operation recovery where applicable.
- `LogRenderer` and `StatusRenderer` produce monochrome-distinguishable output when `NO_COLOR=1` is set; every state in the cascade, agent, and lifecycle vocabularies has a distinct glyph or label without color.

## Cascade crash tests

The cascade tests must cover:

- pre-stdout hook crash
- pre-stdout hook crash followed by a newly enqueued cascade
- crash between stdout and `MarkDelivered`
- crash after `MarkDelivered`
- two or more concurrent `PreToolUse` calls racing to reconcile the same intent; exactly one materialization occurs and all calls in the triggering batch are blocked
- permutations in which each logical tool is the first hook to arrive for a batch with pending work; whichever arrives first fixes `Block`, and arrival order never permits a sibling tool to execute
- a batch whose first admission is `PassThrough`; an intent detected before a later sibling hook is deferred to the next batch rather than partially blocking an already-admitted batch
- launcher or daemon restart after a `PassThrough` admission loses the cache; an unknown in-flight batch leaves files untouched and hard-restarts the incarnation to establish a clean boundary, while an active durable `Block` remains fail-closed
- a concurrent sibling `PreToolUse` arriving after payload emission but before `MarkDelivered`; it receives the byte-identical payload and cannot acknowledge the intent
- matching, duplicate, stale, missing, and reordered `PostToolBatch` events; only the matching event marks batch completion and none acknowledges delivery
- a new batch in the same model turn after `PostToolBatch`; it cannot acknowledge merely because its batch id differs
- the first `PreToolUse` from a provably later model turn acknowledges the delivered intent, then evaluates the next ordered intent before deciding whether its tool may run; if `MarkDelivered` was lost, the same exact proof atomically repairs delivery and advances `Materialized -> Acknowledged`
- hook, daemon, and agent crashes before and after durable barrier creation and before and after `batch_completed_at`; ambiguous completion always hard-restarts with the saved payload
- hard-restart fallback when the Claude adapter cannot expose an unambiguous batch-completion boundary: the replacement row and byte-stable startup payload are durable before exec, the payload is its first startup message, its first managed boundary proves startup processing before acknowledgement, and no interrupted tool is replayed automatically
- agent crash after delivery but before acknowledgement
- resume with a delivered-but-unacknowledged intent
- multiple cascades before first hook coalescing into one delivery
- deliverable-intent lookup and byte-identical retry for both `Materialized` and `Delivered`
- daemon crash and recovery at every `sync_intent` state, including `RecoveryRequired`
- `WorkspaceProbe` returning `FreshClean`, `FreshDirty`, `StaleClean`, `StaleDirty`, and `Unknown`, plus fingerprint drift immediately before mutation
- `jj workspace update-stale` with clean files, unsnapshotted edits, conflicts, direct materialization that creates no new operation, and a concurrently advanced base transition
- recovery verifies edit-bearing divergent successors before choosing the visible result; ambiguous recovery requires human selection
- process restart with a reused harness session id retires the old runtime incarnation without acknowledgement, re-proves exclusive hook control, and injects the saved payload before any replacement-process tool is allowed to run; a crash before its first boundary redelivers to another replacement
- `--no-integrate-operation` plus `jj op integrate` feasibility for planned `ParentAdvance`, including concurrent external operations

They must also cover the worked scenarios in [Cascade](07-cascade.md): native ancestor rewrite, parent live-head advance, conflict exposure, direct human materialization, parallel tool batch, and agent crash after delivery. These are scenario tests over observable state, not assertions about private function boundaries.

## Module-specific obligations

`MetadataLedger` tests cover content-hash ownership, trailer independence, sticky human bookmark renames, squash inheritance toward human ownership, and opt-back-in refresh.

`AuthEnforcer` and `ApprovalBroker` tests cover thread-scoped rejection across siblings; operational rejection of Admin; broker enrollment; persisted begin/display/confirm/cancel challenges; nonce, channel, method, target, argument, and rendered-plan binding; atomic capability issuance after confirmation; atomic claim with one durable operation id; crash resume of only that plan; final consumption; expiry and replay; plan-digest drift; and non-interactive failure. Audit tests cover accepted, rejected, unidentified, bootstrap, registration, invalid-repo, and `ListRepos` attempts, with exactly one row routed to the per-repo or per-user SQLite sink and nullable credential/approval identities represented explicitly.

`ThreadTranscriptStore` tests cover FTS search, author/direction preservation, change-aligned reads, tombstoned and redirected changes, JSONL rotation/truncation recovery, offset and row insertion in one transaction, reopen catch-up recursion prevention, `pending_kkd_prepends` FIFO matching, cascade-injection row idempotency, and intent-pinned anchors. Provider-egress cases cover first consent, remembered consent, revocation, configured-provider change, local preview without egress, and same-thread transcript MCP denial until an active purpose-bound grant exists.

`LogRenderer` tests cover stack-aware expansion, collapsed siblings and unrelated threads, `--no-stack`, `--all`, `--wide`, `-r <revset>` disabling collapse, and parser errors when `-r` is combined with collapse flags.

`StatusRenderer` tests cover the exact live head, checkpoint bookmark and commit, `current | behind | diverged` checkpoint relationship, omission of unavailable v1.x PR fields, follows and children rows, the three-valued cascade state, `--diff`, `--diff --stat`, and `--no-jj`.

`SidebarController`, `OverlayController`, `ToastQueue`, `FormController`, and `PaneLifecycle` tests cover navigation versus consequential-action gating, contextual-thread previews versus exact sibling-read approval, daemon-issued approval cards, disconnected/reconnecting rendering, cursor preservation across event streams, toast TTL/click/action behavior, spawn form navigation, pane ensure-on-attach, user-killed-pane non-respawn during a live session, terminal-too-narrow warnings, and repo-shared `[ui]` rejection. The persistent sidebar never receives a toast; if it is the only visible kiki surface, eligible events use the OS-notification fallback while durable row state remains visible.

Publishing tests prove the first publishing tranche uses a human-authored or static template rather than transcript or AI drafting. Parent-merge local reconciliation may complete without approval, but force-push and PR-base mutation remain a pending named remote plan until a foreground one-shot approval claims it; failure retains the follows edge and is safely retryable.

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

The fakes should expose edge cases directly: op storms, hook crashes, parallel tool batches, concurrent hook arrival, missing and reordered batch completion, model-turn identity, settings-source discovery, JSONL rotation, out-of-order timestamps, remote divergence, and agent session restart.

## Integration-only surfaces

The real `jj`, `gh`, Claude Code, ratatui terminal loop, tmux pane wiring, and fsnotify watcher are smoke-tested or integration-tested. Claude Code integration is nevertheless a release gate for exclusive `PreToolUse` settings isolation, stable model-turn/tool-batch identity, concurrent hook behavior, and `PostToolBatch` completion; an upstream version that fails those probes uses hard restart or is unsupported rather than being modeled optimistically. Core interpretation logic belongs in deep-module tests against fakes.
