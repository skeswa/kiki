# Harness adapter

The harness adapter is the seam between `kkd` and an agent runtime. v1 ships only the Claude Code adapter; Codex and other harnesses are deferred. Designing the seam now keeps the cascade orchestrator harness-neutral.

## Trait pair

```
trait Harness {
    fn name(&self) -> &str;
    fn capabilities(&self) -> Capabilities;
    fn spawn(&self, opts: SpawnOpts) -> Result<Box<dyn RunningAgent>>;
}

trait RunningAgent {
    fn thread_id(&self) -> ThreadId;
    fn agent_session_id(&self) -> AgentSessionId;
    fn harness_session_id(&self) -> HarnessSessionId;
    fn pid(&self) -> Pid;
    fn enqueue_context(&self, msg: ContextMessage) -> Result<()>;
    fn restart_with_message(&self, msg: String) -> Result<()>;
    fn terminate(&self) -> Result<()>;
    fn status(&self) -> AgentStatus;
}
```

`agent_session_id` identifies one kiki-managed process incarnation and changes on every restart. `harness_session_id` identifies the harness conversation and may be reused by `--resume`. This split is required for delivery safety: starting a replacement process retires the previous incarnation and clears its `delivered_intent_id` without acknowledging it, forcing byte-identical redelivery in the new process.

`AgentStatus` is `Running | Quiescent | Stuck(duration) | Crashed`. The cascade orchestrator uses `status` and `capabilities` to decide whether soft-pause is viable and whether pending reconciliation may materialize the managed workspace.

## Agent display states

`AgentStatus` is the orchestrator's vocabulary. The human-facing surfaces (`kk ls`, `kk log --wide`, the TUI glyph table in [Interface](../12-interface/spec.md)) render a four-value projection of it, folding in two session signals the harness already emits:

| display state | source                                                                                                                                       |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `working`     | `Running`                                                                                                                                    |
| `idle`        | `Quiescent`, most recent turn not completed (or no turn yet)                                                                                 |
| `finished`    | `Quiescent`, most recent turn completed (the harness's turn-completion signal; Claude Code's stop event)                                     |
| `blocked`     | `Stuck(duration)`, `Crashed`, or an unacknowledged attention event such as a permission prompt (see [Observability](../14-observability.md)) |

The projection is display-only: the cascade orchestrator branches on `AgentStatus` and `Capabilities`, never on display states, and renderers project rather than keep a state model of their own.

## Capabilities

Capabilities are a typed struct:

```
struct Capabilities {
    soft_pause: bool,
    session_resume: bool,
    structured_tool_hooks: bool,
    mcp_client: bool,
    quiescence_detection: bool,
}
```

Cascade behavior degrades cleanly when a capability is absent. For a harness without `soft_pause`, `enqueue_context` leaves the prepared payload on its durable intent for delivery on the next `--resume`. The daemon checks `capabilities` before deciding the cascade path.

## ContextMessage

```
struct ContextMessage {
    kind: ContextMessageKind,
    text: String,
    structured: Option<JsonValue>,
}
```

`ContextMessageKind` includes at least `RebaseAlert`, `ParentMerged`, `ConflictNoticed`, and `UserNote`.

The `structured` field carries diff payloads, file lists, etc. for richer agent re-orientation.

## Hook

`kk-hook` is the PreToolUse sidecar that fronts cascade delivery for Claude Code. It is small (~100 lines of glue) and stays small for latency reasons:

- Fast-path round-trip target: <5ms typical, imperceptible to agents.
- Slow path (rebase + payload compose) is bounded by `jj rebase` plus a small constant.

The hook's exact behavior — unresolved-intent lookup, boundary probe, decision step, and post-stdout `MarkDelivered(intent_id)` — lives in [Cascade](../07-cascade.md).

## Hook degradation

When `kkd` is unreachable (socket missing, connection refused, daemon mid-restart), the hook degrades to pass-through. The connect timeout is 200ms and the overall hook budget is 1s; on expiry the hook returns Claude Code's `continue` decision so the agent's tool call is not blocked, then appends one structured record to `~/.kiki/repos/<repo_id>/errors/<thread_id>.log`.

`~/.kiki/repos/<repo_id>/errors/<thread_id>.log` is the catch-all for client-side errors that cannot reach `kkd`. It is created lazily at first failure. The hook learns its absolute path at thread-spawn time, where `kkd` writes it into the per-thread harness config alongside the credential path; the source repo's filesystem is never touched.

Pass-through is not a violation of the cascade safety invariant; it is the explicit precondition's failure mode. The cascade invariant in [Invariants](../04-invariants.md) requires `kkd` to be reachable for kiki to materialize a desired state at a safe boundary. When the daemon is unreachable, jj repository state may already contain native descendant evolution, but kiki leaves the workspace files untouched and preserves or reconstructs the pending intent. Two cases:

- The watcher saw the trigger op before the outage. The `sync_intent` and its normalized trigger rows are already in sqlite; they survive the daemon stop.
- The trigger op happened during the outage. The trigger lives in jj's op log (the upstream source of truth). On `kkd` restart, op-log catch-up replays missed ops, populates `op_history`, and runs before/after classification to create the same exact-base-transition intent as the live watcher.

Either way, the next successful PreToolUse round-trip after `kkd` returns selects the oldest unresolved intent and probes the workspace immediately. `NativeRewrite` needs no file update for `FreshClean | FreshDirty` and may update `StaleClean`; `ParentAdvance` may mutate only from `FreshClean`. Any dirty or indeterminate state that requires mutation enters `RecoveryRequired` and hard-pauses for edit-preserving recovery. The successful path persists the result, synthetic payload, anchor, and `Materialized` state on the intent in one transaction. Cascade delivery is deferred, not dropped, and outage edits are not silently hidden.

In the deferred window, jj repository state may already contain evolved descendants while the workspace files remain stale. The agent's tool call may therefore run against the last materialized files until `kkd` returns. That is the trade-off: the hook prefers an agent that keeps moving over an agent that wedges on a daemon hiccup, and durable intent/op history ensures reconciliation is still delivered. When `kkd` returns and observes a non-empty `~/.kiki/repos/<repo_id>/errors/<thread_id>.log` for a thread, it surfaces a single notification per thread summarizing the gap.

## Hook chaining

`kk-hook` is installed at thread spawn into a per-thread Claude Code config (scoped to the thread's workspace dir, not polluting user-global). It always runs first. After acknowledging `agent_sessions.delivered_intent_id`, if no unresolved intent remains, the hook returns "continue" and Claude Code's hook chain proceeds to user-defined hooks. Reverted on thread close.

## Per-thread harness selection

- Default per-repo via `agent.default_harness`.
- Override per-thread via `kk new <name> --harness <name>` and `--harness-arg "..."`.
- A thread cannot change harness mid-life; `kk thread restart <thread> --harness <new>` is the explicit path (terminates the current agent and respawns).
- v1: the `Harness` trait is the architectural seam, but only the `claude-code` adapter ships. `kk new --harness <other>` errors with `"unsupported harness in v1"`. `kk new` (no `--harness`) defaults to `claude-code` and errors at spawn time with `"claude-code not on PATH — install it or pass --harness <other> once another adapter ships"` if the binary is missing. `kk init` does not pre-validate the harness binary; the architecture is genuinely BYO-harness, even though v1 ships only one.

`kk thread restart --harness <new>` is not part of the acceptance slice unless promoted in [Orientation](../01-orientation.md); this chapter reserves the semantics so a future implementation does not mutate a thread's harness identity in place.

## Capture

The capture-side abstraction is a separate trait, `TranscriptAdapter`:

```
trait TranscriptAdapter {
    fn discover(&self, session_id: SessionId) -> PathBuf;
    fn tail(&self, from_offset: u64) -> impl Iterator<Item = JsonlEntry>;
    fn project(&self, entry: &JsonlEntry) -> Option<(Author, Direction, String, DedupKey)>;
    fn position(&self) -> u64;
}
```

Cascade-injection row writes are NOT part of this trait — they are performed by `kkd`'s cascade orchestrator inside the `MarkDelivered` handler, independent of harness. v1's `TranscriptAdapter` impl is `ClaudeCodeAdapter`; v2's Codex adapter writes a different projector and reuses the rest.

## Spawn lifecycle

`kk new` performs an atomic spawn. If any step fails, `kkd` unwinds prior steps to avoid orphaned state. The full sequence — kept here for the harness-adapter context; the canonical lifecycle description lives in [Threads](../05-threads.md):

1. Resolve name/prompt/follows/harness/sidebar options. Initial prompt comes from `-m "<prompt>"` (winning if both are supplied) or stdin; absent both, the spawn proceeds without a first-turn prompt and the placeholder name is `unnamed-<short-hex>`.
2. Insert the sqlite thread row (the stable `thread_id` other steps attach to).
3. `jj workspace add` at `<workspaces_root>/<repo>-kiki-<slug>/` (configurable; see [Configuration](../13-configuration.md)).
4. Bookmark create.
5. `jj new` on the bookmark.
6. `tmux new-session -d` cd'd into the workspace path.
7. Harness spawn through `Harness::spawn(SpawnOpts { thread_id, resume_harness_session_id: Option<HarnessSessionId>, initial_prompt: Option<String>, harness_args })`. Every call creates a new kiki `agent_session_id`; the optional harness id is only the conversation to resume. The adapter routes the optional initial prompt to the harness's first user-turn input; for Claude Code, this is the harness's startup-message contract.
8. `ThreadScoped<thread_id>` credential written to `~/.kiki/repos/<repo_id>/credentials/<thread_id>` (mode `0600`) and per-thread harness hook config installed inside the workspace at the path the harness expects (e.g., `<workspace>/.claude/settings.json` for Claude Code). The harness config references the credential and the per-thread error-log path by absolute path under `~/.kiki/`. The workspace tree itself receives only the harness config file; nothing kiki-internal goes inside the source repo's filesystem.
