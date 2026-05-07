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
    kind: MessageKind,    // RebaseAlert | ParentMerged | ConflictNoticed | UserNote | ...
    text: String,
    structured: Option<JsonValue>,
}
```

The `structured` field carries diff payloads, file lists, etc. for richer agent re-orientation.

## Hook

`kk-hook` is the PreToolUse sidecar that fronts cascade delivery for Claude Code. It is small (~100 lines of glue) and stays small for latency reasons:

- Fast-path round-trip target: <5ms typical, imperceptible to agents.
- Slow path (rebase + payload compose) is bounded by `jj rebase` plus a small constant.

The hook's exact behavior — outbox lookup, decision step, post-stdout `MarkDelivered` — lives in [Cascade](../06-cascade.md).

## Hook chaining

`kk-hook` is installed at thread spawn into a per-thread Claude Code config (scoped to the thread's workspace dir, not polluting user-global). It always runs first. After running the acknowledgement step, if `pending_cascade_seq <= acknowledged_cascade_seq`, the hook returns "continue" and Claude Code's hook chain proceeds to user-defined hooks. Reverted on thread close.

## Per-thread harness selection

- Default per-repo via `agent.default_harness`.
- Override per-thread via `kk new <name> --harness <name>` and `--harness-arg "..."`.
- A thread cannot change harness mid-life; `kk thread restart <thread> --harness <new>` is the explicit path (terminates the current agent and respawns).
- v1: only `claude-code` is accepted; any other harness name errors with a clear "unsupported harness" message.

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

`kk new` performs an atomic spawn. If any step fails, `kkd` unwinds prior steps to avoid orphaned state. The full sequence — kept here for the harness-adapter context; the canonical lifecycle description lives in [Threads](../04-threads.md):

1. Resolve name/prompt/follows/harness/sidebar options.
2. Insert the sqlite thread row (the stable `thread_id` other steps attach to).
3. `jj workspace add`.
4. Bookmark create.
5. `jj new` on the bookmark.
6. `tmux new-session -d` cd'd into the workspace path.
7. Harness spawn with thread-id env injected and optional initial prompt delivered.
8. `ThreadScoped<thread_id>` credential written to `<workspace>/.kiki/hook-cred` (mode `0600`) and per-thread harness hook config installed (e.g., `<workspace>/.claude/settings.json` for Claude Code).
