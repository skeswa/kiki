# Testing

Tests should target observable behavior and persisted state — what the system does and what it stores. They should not target private implementation details.

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

These modules are also required. Each one is tested alongside the v1.x polish surface that ships it:

- `AICompose`
- `MetadataLedger`
- `ThreadTranscriptStore`
- `SidebarController`
- `PaneLifecycle`
- `OverlayController` — opening and closing, NAVIGATE-mode transitions, preview-mode toggling (`t`/`d`/`c`), the chord ribbon adapting to the current selection, graceful degradation in narrow terminals, and mouse click-to-focus
- `ToastQueue` — expiry when a toast's TTL (time-to-live) runs out, dismissal on click, dismissal when the toast's action is invoked, dismissal when its row gains focus and is thereby acknowledged, and coalescing of cascade-applied events
- `FormController` — field navigation in the spawn card, and the approval-card flow that the daemon issues

## Regression tests for resolved spec conflicts

- `kk ls --all` includes closed threads. (A thread is kiki's unit of work: a named sequence of revisions in jj, the version-control system kiki drives.) It does not widen repo scope.
- `kk ls --all-repos` widens repo scope. It does so independently of lifecycle scope.
- Workspace isolation is cooperative, not a security boundary. (A jj workspace is an extra working directory attached to the same repository.) The docs say so, and no test claims security isolation.
- Kiki keeps its launch settings and centralized state outside the workspace, so they do not block `kk close`. The `.claude/settings.local.json` fallback is the one file kiki may own inside the workspace; kiki records a hash of the bytes it wrote there. `kk close` ignores that file only while it still matches kiki's recorded bytes.
- Untracked or ignored files that the user created still block or prompt during `kk close`.
- A turn-completion (stop) hook is installed only where its behavior is specified and tested. The Codex adapter's `Stop` lifecycle event is part of its specified contract. A Claude Code stop hook is not installed in v1 unless it is promoted with specified, tested behavior.
- Managed sessions of every v1 harness prove that kiki is the sole matching pre-tool hook. (A harness is the coding-agent program, such as Claude Code; a pre-tool hook runs before each of the agent's tool calls.) A project or user pre-tool fixture must not execute in the managed process. No test may claim that kiki merely runs before concurrently dispatched user hooks.
- Launch-scoped settings isolation leaves the tracked `.claude/settings.json` and the user's global settings byte-identical. Where the fallback is exercised instead, it merges only `.claude/settings.local.json`. It restores that file only from the expected kiki-owned hash. If the user edited the file concurrently, it reports that instead of overwriting.
- A managed Codex session launches under the generated `CODEX_HOME`, with authentication provisioned into it. The user's real `~/.codex/` configuration is untouched and unread. Hook fixtures from the workspace `.codex/`, from plugins, and from managed policy must not execute in the managed process. Nothing under `<workspace>/.codex/` is created, modified, or deleted. There is no workspace-merge fallback: a failed isolation proof fails the incarnation (one launch of the harness process) before the agent receives a prompt.
- The Codex adapter/version fixture proves its boundary before `parallel_batch_boundary` is claimed. The proof covers the following. No two tool calls of one turn run concurrently, and that includes calls originated by subagents. A new tool is requested only after the model has consumed the previous call's result. A deny decision returns the saved payload to the model byte-identically, and the denied tool never executes. When the hook sidecar is dead under an active barrier (a block that holds the agent's tool batch during reconciliation), the launcher answers with a generic blocking deny, so a barrier-covered call never fails open. A denied call fires no post-tool event. So the blocked single-call batch's `batch_completed_at` is recorded by the next turn-scoped hook event's admission transaction — a crash-surviving report driven by the harness — and never by the emitting hook's own RPC. Acknowledgement requires a `PreToolUse` with a distinct, serially later `tool_use_id`. A same-or-later Codex `turn_id` alone never suffices, because one `turn_id` spans many model steps. Acknowledgement always requires the delivery receipt: the session record's byte-identical deny result for the blocked `tool_use_id`. `MarkDelivered` alone never suffices. Crash and fault injection covers these cases. Hook death before stdout: the launcher answers with a generic deny, and the contrary receipt redelivers on the arriving batch. Stdout written but timed out or rejected by the harness: `MarkDelivered` is recorded, the receipt is contrary, and the intent is redelivered — never acknowledged. (An intent is the durable record of one unit of pending cascade work.) Persistent output rejection: a second contrary receipt for the same intent fails over to `RestartStartup` instead of redelivering again, and exhausted bounded restart attempts hard-pause with a loud attention event rather than looping. Daemon restart between and after those attempts: the attempt history and exhaustion state are read from the intent, so a restart after the first contrary receipt still treats the next one as the second, and a restart after exhaustion re-surfaces the blocked thread without minting a new attempt. The two repair exits: a `retry-delivery` plan re-arms exactly one fresh bounded cycle by incrementing the delivery epoch, so bounds count only attempt rows stamped with the current epoch — a prior-epoch row can never consume the fresh cycle, and no bound ever compares timestamps, even under clock skew or rollback — while a `discard-delivery` plan acknowledges without delivery proof only under a one-shot approval bound to that plan, and records the human resolution; no other write is accepted against an exhausted intent. Receipt unreadable at the completing arrival: acknowledgement defers when no delivery is pending, and takes `RestartStartup` when one is. Matching receipt: acknowledge. Beyond the fault cases, the generated config pins the harness-side hook timeout above the slow-path bound, and the fixture proves the session record durably contains deny results exactly as returned to the model. Every workspace-observing tool in the pinned version fires `PreToolUse` or is disabled by the generated config.
- Unrelated harness hook events stay enabled only for an adapter/version fixture that proves two things: they cannot race workspace reconciliation, and they cannot add another matching pre-tool hook.
- `kk init` is idempotent in an already-registered repo. It prints status and exits 0 without mutating anything.
- `kk init` does not pre-validate harness binaries. A missing-harness error surfaces only at `kk new` time.
- `kk init` succeeds when `gh` is missing or unauthenticated. The first GitHub-backed command performs the check. It reports an actionable error without corrupting local state.
- If a thread's workspace directory is deleted out of band, the thread records `ProjectionDiverged { reason: WorkspaceDirectoryMissing }` at daemon boot or `kk ls`. It fires exactly one notification. It is neither recreated nor reclassified automatically.
- Crash injection at every creation journal step leaves the thread in `Creating` or `CreateFailed`. Gate activation and process exec remain `Creating`. Only the matching ready handshake may enter `Active`. The launcher cannot pass its database-backed gate before the credentials, exclusive hooks, live head, checkpoint, and tmux projections are durable. Restart adoption must distinguish an activated gate, an exec'd process, and a ready incarnation, without duplicating any external resource.
- Reopen keeps the thread `Closed` while its durable journal recreates projections. Crash injection at every step either adopts the exact resource, compensates back to `Closed`, or records a stable repair plan. It never exposes `Active` before a matching ready handshake. Every new incarnation independently re-proves exclusive hook control.
- Close freezes the tmux pane's root processes and every descendant to a fixed point. It records each process's prior stopped state. It proves that no descendant escaped. It refuses to declare quiescence when a same-UID process outside that set has a cwd, root, mapping, or open descriptor in the workspace. It checkpoints the exact pinned commit with a non-snapshotting jj command. It verifies the armed filesystem generation and the frozen workspace fingerprint. It synchronously reconciles or detaches children. It repeats the holder and fingerprint proof. Only then does it kill the session. A failed proof or a failed child detach resumes the processes and verifies the original process tree before returning `Active`. A failed resume becomes `CloseFailed`. Crashes after the proof or after the session kill resume the idempotent journal; close never guesses from filesystem presence.
- A close approval is bound to the rendered plan and the preflight fingerprint. Drift discovered after the freeze causes a verified resume and a fresh plan and approval. The daemon never prompts while leaving a session frozen.
- Workspace-record, path, bookmark, and session mismatches all produce durable projection issues. Only a unique, identity-preserving normalization may auto-repair. Every ambiguous plan uses a stable repair id, and that id goes stale when the observed state changes. Bookmark-only divergence continues safe workspace-head tracking and follows classification. Session divergence continues observation but suspends boundary mutation. Workspace identity or path ambiguity suspends both.
- A `SessionMissing` repair can restart the thread to `Active`, or execute a stable complete-close plan directly to `Closed`. Adopting a moved bookmark for a closed thread succeeds only when the exact observed commit satisfies the archived topology checks, and the adoption updates checkpoint and head together. Projection mismatches created by an in-flight creation or close saga fail that saga; they do not switch the thread to `ProjectionDiverged`.
- `kk-hook` returns `continue` and writes to `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log` when it cannot reach `kkd` within its connect and overall budget. It does not block the agent's tool call. A reconciliation pending during the outage must still be delivered on the next successful PreToolUse round-trip. If the watcher saw the trigger, durable state lives in `sync_intents`. Otherwise, restart catch-up reconstructs it from jj's op log (jj's record of every operation run against the repo). If the agent edited the stale tree during the outage, the next probe enters `RecoveryRequired` rather than treating the tree as clean.
- Once a cascade delivery barrier is active, a daemon outage no longer lets tools pass through. Every call in that tool batch stays blocked until a matching `PostToolBatch` completes the barrier or the adapter takes the hard-restart path.
- The `Block` admission and the complete soft-barrier identity commit before the first reconciliation mutation. Crash injection between every probe, jj, filesystem, and SQLite step must never leave changed files with an unbound batch.
- Native ancestor evolution: amending thread A causes jj to evolve thread B's repository working-copy commit. The classifier records `NativeRewrite` with the exact old-base → evolved-base ids. It performs no redundant rebase. At B's safe boundary, it verifies that B's current commit still contains that base before materializing it (updating B's files to match).
- Parent-head advance: adding revision A2 in A's managed workspace updates A's persisted live head, while A's checkpoint bookmark may remain on A1. The classifier records `ParentAdvance` from the exact live head. B's boundary rebases only the validated single-parent owned chain. Merge, multiple-root, or foreign topology stops as `TopologyDiverged`.
- A successful `ParentAdvance` persists B's actual result as `threads.thread_head_commit_id`, in the same transaction as the materialized intent. The watcher may then skip the attributed jj operation without losing that head advance.
- Multi-workspace cascade in A→B→C: one jj operation may logically evolve both B and C. Both receive independent `NativeRewrite` intents immediately, from comparing the before and result operations. B and C materialize at their own boundaries. If an explicit advance of B evolves C, the initiating reconciliation handler records C's intent, even though the watcher skips the attributed op.
- Direct human materialization: a person may run `jj workspace update-stale` directly in stale B. That can change B's files without creating a new op-log head. The boundary probe detects `FreshClean` or `FreshDirty`, performs no duplicate update, and still delivers context for the unresolved intent.
- Coalescing updates one pre-materialization intent's base transition and its normalized trigger rows. Once payload preparation begins, later work receives a new ordered intent and cannot mutate the saved delivery.
- A stale workspace with unsnapshotted edits, or an `Unknown` probe result, enters `RecoveryRequired`. Recovery hard-pauses the agent and enumerates divergent successors outside the workspace. It never resumes on a clean successor that hides those edits.
- Watcher restart from a multi-parent or divergent jj operation graph traverses all reachable, unprocessed ancestors from the persisted frontier, in topological order. Tests must fail any implementation that stores one parent or advances one linear cursor through the operation DAG.
- Creating a follows edge and detaching one both pin an exact operation view. Both synchronously refresh the affected live heads before choosing or discarding an anchor. A lagging asynchronous watcher cannot make either command lose a parent or child advance.
- `kk thread destroy` deletes kiki projections and records only after an exact plan is confirmed. It preserves jj revisions by default. `--abandon-revisions` may abandon only the validated, unreferenced, single-parent owned chain named in a separate approved plan. It refuses shared, foreign, followed, or ambiguous topology.
- Destroy crash injection — before and after bookmark deletion, optional exact revision abandonment, session and workspace cleanup, and tombstoning — yields only the recorded `DestroyCommit`, `DestroyFailed`, or `Destroyed` outcome. After the first irreversible step, no recovery path relabels the thread `Active`, `Closed`, or `ProjectionDiverged`. `kk repair` can only finish the exact approved plan, or invoke explicit jj operation recovery where that applies.
- `LogRenderer` and `StatusRenderer` produce output that stays readable in monochrome when `NO_COLOR=1` is set. Every state in the cascade, agent, and lifecycle vocabularies has a distinct glyph or label that does not depend on color.

## Cascade crash tests

A cascade is how kiki carries a parent thread's changes into the threads that follow it. The cascade tests must cover:

- a hook crash before it writes stdout
- a pre-stdout hook crash followed by a newly enqueued cascade
- a crash between stdout and `MarkDelivered`
- a crash after `MarkDelivered`
- two or more concurrent `PreToolUse` calls racing to reconcile the same intent; exactly one materialization occurs, and every call in the triggering batch is blocked
- permutations in which each logical tool is the first hook to arrive for a batch with pending work; whichever arrives first fixes `Block`, and no arrival order lets a sibling tool execute
- a batch whose first admission is `PassThrough`; an intent detected before a later sibling hook is deferred to the next batch, rather than partially blocking a batch that was already admitted
- a launcher or daemon restart after a `PassThrough` admission loses the cache; an unknown in-flight batch leaves files untouched and hard-restarts the incarnation to establish a clean boundary, while an active durable `Block` stays fail-closed
- a concurrent sibling `PreToolUse` arriving after payload emission but before `MarkDelivered`; it receives the byte-identical payload and cannot acknowledge the intent
- matching, duplicate, stale, missing, and reordered `PostToolBatch` events; only the matching event marks batch completion, and none of them acknowledges delivery
- a new batch in the same model turn after `PostToolBatch`; it cannot acknowledge merely because its batch id differs
- the first `PreToolUse` from a provably later model turn acknowledges the delivered intent, then evaluates the next ordered intent before deciding whether its tool may run; if `MarkDelivered` was lost, the same exact proof atomically repairs delivery and advances `Materialized -> Acknowledged`
- hook, daemon, and agent crashes before and after durable barrier creation, and before and after `batch_completed_at`; ambiguous completion always hard-restarts with the saved payload
- the hard-restart fallback when an adapter cannot expose an unambiguous batch-completion boundary: the replacement row and the byte-stable startup payload are durable before exec, the payload is the replacement's first startup message, its first managed boundary proves startup processing before acknowledgement, and no interrupted tool is replayed automatically
- an agent crash after delivery but before acknowledgement
- a resume with a delivered-but-unacknowledged intent
- multiple cascades before the first hook, coalescing into one delivery
- deliverable-intent lookup and byte-identical retry for both `Materialized` and `Delivered`
- daemon crash and recovery at every `sync_intent` state, including `RecoveryRequired`
- `WorkspaceProbe` returning `FreshClean`, `FreshDirty`, `StaleClean`, `StaleDirty`, and `Unknown`, plus fingerprint drift immediately before mutation
- `jj workspace update-stale` with clean files, with unsnapshotted edits, with conflicts, with direct materialization that creates no new operation, and with a concurrently advanced base transition
- recovery verifies edit-bearing divergent successors before choosing the visible result; ambiguous recovery requires a human to choose
- a process restart with a reused harness session id retires the old runtime incarnation without acknowledgement, re-proves exclusive hook control, and injects the saved payload before any replacement-process tool may run; a crash before its first boundary redelivers to another replacement
- `--no-integrate-operation` plus `jj op integrate` feasibility for a planned `ParentAdvance`, including concurrent external operations

They must also cover the worked scenarios in [Cascade](05-cascade.md): native ancestor rewrite, parent live-head advance, conflict exposure, direct human materialization, a parallel tool batch, and an agent crash after delivery. These are scenario tests over observable state, not assertions about private function boundaries.

## Module-specific obligations

`MetadataLedger` tests cover content-hash ownership, trailer independence, sticky renames of human bookmarks, squash inheritance toward human ownership, and opt-back-in refresh.

`AuthEnforcer` and `ApprovalBroker` tests cover thread-scoped rejection across siblings and operational rejection of Admin. They cover broker enrollment; persisted begin/display/confirm/cancel challenges; binding of the nonce, channel, method, target, arguments, and rendered plan; atomic capability issuance after confirmation; atomic claim with one durable operation id; crash resume of only that plan; final consumption; expiry and replay; plan-digest drift; and non-interactive failure. Audit tests cover accepted, rejected, unidentified, bootstrap, registration, invalid-repo, and `ListRepos` attempts. Each attempt writes exactly one row, routed to the per-repo or per-user SQLite sink, with nullable credential and approval identities represented explicitly.

`ThreadTranscriptStore` tests cover FTS (full-text search); author and direction preservation; change-aligned reads; tombstoned and redirected changes; recovery from JSONL rotation and truncation; offset and row insertion in one transaction; prevention of reopen catch-up recursion; `pending_kkd_prepends` FIFO matching; idempotent cascade-injection rows; and intent-pinned anchors. Provider-egress cases cover first consent, remembered consent, revocation, a configured-provider change, local preview without egress, and denial of same-thread transcript MCP until an active purpose-bound grant exists.

`LogRenderer` tests cover stack-aware expansion, collapsed siblings and unrelated threads, `--no-stack`, `--all`, `--wide`, `-r <revset>` disabling collapse, and parser errors when `-r` is combined with collapse flags.

`StatusRenderer` tests cover the exact live head; the checkpoint bookmark and commit; the `current | behind | diverged` checkpoint relationship; omission of unavailable v1.x PR fields; follows and children rows; the three-valued cascade state; `--diff`; `--diff --stat`; and `--no-jj`.

`SidebarController`, `OverlayController`, `ToastQueue`, `FormController`, and `PaneLifecycle` tests cover navigation versus consequential-action gating, contextual-thread previews versus exact sibling-read approval, daemon-issued approval cards, disconnected and reconnecting rendering, cursor preservation across event streams, toast TTL/click/action behavior, spawn form navigation, pane ensure-on-attach, not respawning a user-killed pane during a live session, terminal-too-narrow warnings, and rejection of repo-shared `[ui]` config. The persistent sidebar never receives a toast. If the sidebar is the only visible kiki surface, eligible events use the OS-notification fallback, while durable row state remains visible.

Publishing tests prove that the first publishing tranche uses a human-authored or static template, not transcript or AI drafting. Parent-merge local reconciliation may complete without approval. Force-push and PR-base mutation remain a pending named remote plan until a foreground one-shot approval claims it. A failure retains the follows edge and is safe to retry.

## Fakes

Deep-module tests should use fakes — stand-in implementations that act like the real dependency but run in-process — for:

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

The real `jj`, `gh`, Claude Code, Codex, the ratatui terminal loop, tmux pane wiring, and the fsnotify watcher are smoke-tested or integration-tested. Each shipped harness's integration is still a release gate. For Claude Code, the gate covers exclusive `PreToolUse` settings isolation, stable model-turn and tool-batch identity, concurrent hook behavior, and `PostToolBatch` completion. For Codex, it covers `CODEX_HOME` isolation with kiki's hooks pre-trusted, the serial-dispatch proof, byte-identical visibility of deny payloads, and `Stop`/`SessionStart` lifecycle behavior. An upstream version that fails its probes uses hard restart or is unsupported; it is never modeled optimistically. Core interpretation logic belongs in deep-module tests against fakes.
