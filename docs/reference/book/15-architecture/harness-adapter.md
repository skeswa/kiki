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
    fn session_id(&self) -> SessionId;
    fn pid(&self) -> Pid;
    fn enqueue_context(&self, msg: ContextMessage) -> Result<()>;
    fn restart_with_message(&self, msg: String) -> Result<()>;
    fn terminate(&self) -> Result<()>;
    fn status(&self) -> AgentStatus;
}
```

`AgentStatus` is `Running | Quiescent | Stuck(duration) | Crashed`. The cascade orchestrator uses `status` and `capabilities` to decide whether soft-pause is viable or hard-escalation is needed.

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

Cascade behavior degrades cleanly when a capability is absent. A harness without `soft_pause` has `enqueue_context` lower into "queue and deliver on next `--resume`". The daemon checks `capabilities` before deciding the cascade path.

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

The hook's exact behavior — outbox lookup, decision step, post-stdout `MarkDelivered` — lives in [Cascade](../07-cascade.md).

## Hook degradation

When `kkd` is unreachable (socket missing, connection refused, daemon mid-restart), the hook degrades to pass-through. The connect timeout is 200ms and the overall hook budget is 1s; on expiry the hook returns Claude Code's `continue` decision so the agent's tool call is not blocked, then appends one structured record to `<workspace>/kiki-errors.log`.

`<workspace>/kiki-errors.log` is the catch-all for client-side errors that cannot reach `kkd`. It is created lazily at first failure. Kiki does not auto-mutate `.gitignore` to exclude the log; whether to ignore it is the user's call.

Pass-through is not a violation of the cascade safety invariant; it is the explicit precondition's failure mode. The cascade invariant in [Invariants](../04-invariants.md) requires `kkd` to be reachable in order to apply a rebase at a safe boundary. When the daemon is unreachable, no rebase is applied — the working copy is left untouched — and the pending cascade state is durable elsewhere. Two cases:

- The watcher saw the trigger op before the outage. `pending_cascade_seq` and any associated `context_queue` rows are already in sqlite; they survive the daemon stop.
- The trigger op happened during the outage. The trigger lives in jj's op log (the upstream source of truth). On `kkd` restart, the op-log catch-up replays missed ops, populates `op_history`, and runs ancestry-impact evaluation — bumping `pending_cascade_seq` and enqueueing `context_queue` rows for affected followers exactly as the live watcher would have.

Either way, the next successful PreToolUse round-trip after `kkd` returns sees `pending_cascade_seq > applied_cascade_seq`, applies the rebase, composes the synthetic payload, persists it to `cascade_outbox`, and emits it. `cascade_outbox` only ever holds applied-but-not-yet-acknowledged cascades; pending-but-not-yet-applied cascades are not stored there. Cascade delivery is deferred, not dropped.

In the deferred window, the agent's tool call may run against a working copy that has not yet picked up an ancestor change. That is the trade-off: the hook prefers an agent that keeps moving over an agent that wedges on a daemon hiccup, and it relies on the queue to make sure the cascade is still delivered the moment `kkd` returns. When `kkd` returns and observes a non-empty `kiki-errors.log` for a thread, it surfaces a single notification per thread summarizing the gap.

## Hook chaining

`kk-hook` is installed at thread spawn into a per-thread Claude Code config (scoped to the thread's workspace dir, not polluting user-global). It always runs first. After running the acknowledgement step, if `pending_cascade_seq <= acknowledged_cascade_seq`, the hook returns "continue" and Claude Code's hook chain proceeds to user-defined hooks. Reverted on thread close.

## Per-thread harness selection

- Default per-repo via `agent.default_harness`.
- Override per-thread via `kk new <name> --harness <name>` and `--harness-arg "..."`.
- A thread cannot change harness mid-life; `kk thread restart <thread> --harness <new>` is the explicit path (terminates the current agent and respawns).
- v1: the `Harness` trait is the architectural seam, but only the `claude-code` adapter ships. `kk new --harness <other>` errors with `"unsupported harness in v1"`. `kk new` (no `--harness`) defaults to `claude-code` and errors at spawn time with `"claude-code not on PATH — install it or pass --harness <other> once another adapter ships"` if the binary is missing. `kk init` does not pre-validate the harness binary; the architecture is genuinely BYO-harness, even though v1 ships only one.

`kk thread restart --harness <new>` is not part of the first acceptance slice unless promoted elsewhere; this chapter reserves the semantics so a future implementation does not mutate a thread's harness identity in place.

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
7. Harness spawn through `Harness::spawn(SpawnOpts { thread_id, session_id, initial_prompt: Option<String>, harness_args })`. The harness adapter routes the optional initial prompt to the harness's first user-turn input; for Claude Code, this is the harness's startup-message contract.
8. `ThreadScoped<thread_id>` credential written to `<workspace>/.kiki/hook-cred` (mode `0600`) and per-thread harness hook config installed (e.g., `<workspace>/.claude/settings.json` for Claude Code).
