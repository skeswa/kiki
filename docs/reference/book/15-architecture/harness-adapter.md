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

`agent_session_id` identifies one kiki-managed process incarnation and changes on every restart. `harness_session_id` identifies the harness conversation and may be reused by `--resume`. This split is required for delivery safety: starting a replacement process retires the previous incarnation and clears its `delivered_intent_id` without acknowledging it. A pending payload is rebound through `RestartStartup` to the new incarnation and a one-use `startup_delivery_id`; the first model turn must causally echo that id before it can acknowledge delivery.

`restart_with_message` implements that proof-carrying path rather than an untracked prepend. Kiki persists the replacement incarnation and startup id before launch; the adapter makes the tagged message the mandatory first harness input, reports an acceptance handshake for that exact id, and includes it in the hook metadata of the resulting first model turn. If the harness cannot supply all three proofs, `restart_startup_delivery` is false.

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
    parallel_batch_boundary: bool,
    exclusive_pre_tool_use: bool,
    restart_startup_delivery: bool,
    mcp_client: bool,
    quiescence_detection: bool,
}
```

These fields describe behavioral proof, not a particular settings mechanism. `exclusive_pre_tool_use` may be satisfied by isolated launch settings or by the ownership-tracked fallback, but a managed v1 process cannot start when it is false. Without `parallel_batch_boundary`, soft delivery is disabled. Kiki may then fall back only when `restart_startup_delivery` proves that a tagged payload is the mandatory first input and that the resulting model turn echoes its one-use id; otherwise cascade-capable managed execution is unsupported. For a harness without `soft_pause`, `enqueue_context` leaves the prepared payload on its intent for this restart path. The daemon checks `capabilities` for every new incarnation rather than assuming a prior process's result remains valid.

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

`kk-hook` is the `PreToolUse` sidecar that fronts cascade delivery for Claude Code. A companion `PostToolBatch` entry point reports only that the triggering parallel batch has finished; it never acknowledges delivery. The sidecar stays small for latency reasons:

- Fast-path round-trip target: <5ms typical, imperceptible to agents.
- Slow path (rebase + payload compose) is bounded by `jj rebase` plus a small constant.

The hook's exact behavior — unresolved-intent lookup, boundary probe, batch barrier, decision step, and post-stdout `MarkDelivered` — lives in [Cascade](../07-cascade.md). The adapter must attach stable runtime-incarnation, model-turn, and tool-batch identities to soft-delivery calls. It durably fixes `Block` before reconciliation may mutate files. Concurrent `PreToolUse` calls in one batch all receive a blocking response when any member triggers reconciliation. Only a matching `PostToolBatch` can complete `SoftBatch`, and only a later model turn can acknowledge it. `RestartStartup` instead requires the first replacement-process model turn to echo its exact `startup_delivery_id`; it never fabricates a tool batch for startup input.

## Hook degradation

When `kkd` is unreachable (socket missing, connection refused, daemon mid-restart) and no cascade barrier has been activated for the current batch, the hook degrades to pass-through. The connect timeout is 200ms and the overall hook budget is 1s; on expiry the hook returns Claude Code's `continue` decision so the agent's tool call is not blocked, then appends one structured record to `~/.kiki/repos/<repo_id>/errors/<thread_id>.log`.

The per-thread hook launcher caches the first admission decision for the lifetime of each batch so every sibling hook observes the same result. A cached `PassThrough` defers intents discovered later in that batch; a cached `Block(intent_id)` fails closed. If a `PassThrough` cache entry is lost, the launcher can no longer prove that reconciliation is safe in that batch. It blocks the unknown call, hard-pauses the old incarnation without mutating the workspace, and starts a replacement before reconsidering pending work. The blocked decision's durable `SoftBatch` proof remains embedded in `sync_intents` and is authoritative after reconnect. If neither the daemon nor the launcher token can prove a blocked batch completed, the adapter blocks the call and requests `RestartStartup` recovery rather than passing through a tool against newly materialized files.

`~/.kiki/repos/<repo_id>/errors/<thread_id>.log` is the catch-all for client-side errors that cannot reach `kkd`. It is created lazily at first failure. The hook learns its absolute path at thread-spawn time, where `kkd` writes it into the per-thread harness config alongside the credential path; the source repo's filesystem is never touched.

Pass-through is not a violation of the cascade safety invariant; it is the explicit precondition's failure mode. The cascade invariant in [Invariants](../04-invariants.md) requires `kkd` to be reachable for kiki to materialize a desired state at a safe boundary. When the daemon is unreachable, jj repository state may already contain native descendant evolution, but kiki leaves the workspace files untouched and preserves or reconstructs the pending intent. Two cases:

- The watcher saw the trigger op before the outage. The `sync_intent` and its normalized trigger rows are already in sqlite; they survive the daemon stop.
- The trigger op happened during the outage. The trigger lives in jj's op log (the upstream source of truth). On `kkd` restart, op-log catch-up replays missed ops, populates `op_history`, and runs before/after classification to create the same exact-base-transition intent as the live watcher.

Either way, the next successful PreToolUse round-trip after `kkd` returns selects the oldest unresolved intent and probes the workspace immediately. `NativeRewrite` needs no file update for `FreshClean | FreshDirty` and may update `StaleClean`; `ParentAdvance` may mutate only from `FreshClean`. Any dirty or indeterminate state that requires mutation enters `RecoveryRequired` and hard-pauses for edit-preserving recovery. The successful path persists the result, synthetic payload, anchor, and `Materialized` state on the intent in one transaction. Cascade delivery is deferred, not dropped, and outage edits are not silently hidden.

In the deferred window, jj repository state may already contain evolved descendants while the workspace files remain stale. Before a barrier is activated, the agent's tool call may therefore run against the last materialized files until `kkd` returns. Once reconciliation begins and files may change, all calls in that batch are blocked instead. When `kkd` returns and observes a non-empty `~/.kiki/repos/<repo_id>/errors/<thread_id>.log` for a thread, it surfaces a single notification per thread summarizing the gap.

## Exclusive hook boundary and settings ownership

Claude Code may run all matching hooks concurrently, so v1 never claims that `kk-hook` runs first and does not chain user `PreToolUse` hooks. Every managed Claude process incarnation—initial creation, reopen, explicit restart, crash recovery, or `RestartStartup` fallback—starts only after the adapter proves that kiki is the sole matching `PreToolUse` hook for that exact launch. A settings fingerprint from an older incarnation is cache input, not proof for a new one. This restriction is session-scoped: it does not modify user-global configuration and does not disable hooks in unmanaged Claude sessions.

The preferred mechanism is a launch-scoped generated settings file under `~/.kiki/repos/<repo_id>/harness/<thread_id>/`, passed with harness arguments that isolate the managed process from project, local-project, and user `PreToolUse` definitions. The generated file declares kiki's `PreToolUse`, its batch-completion entry point where supported, and absolute credential/error-log paths. An adapter/version combination is accepted only after an integration test proves that no independently discovered user or project `PreToolUse` hook runs in that managed process. Unrelated hook events may remain enabled only when the same test proves they cannot race workspace reconciliation or reintroduce a matching `PreToolUse` hook.

If Claude Code cannot accept a truly isolated launch-scoped settings source, the fallback is a structural merge into `<workspace>/.claude/settings.local.json`. Kiki records the prior bytes and content hash outside the workspace, installs a uniquely identified fragment, and restores only when the current file still matches the kiki-owned post-merge hash. Concurrent human edits cause an ownership conflict and require explicit repair; kiki never overwrites them. The fallback must also prove that inherited/global `PreToolUse` hooks are excluded, not merely that kiki's hook appears in the local file.

Kiki never writes, replaces, or deletes `<workspace>/.claude/settings.json`; it may be tracked project configuration. If neither settings strategy can prove exclusive `PreToolUse` control, the attempted incarnation fails before the agent receives a prompt. A version that provides exclusive hook control but no unambiguous parallel-batch boundary may run only when it also proves `restart_startup_delivery`.

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

Cascade-injection row writes are NOT part of this trait or the acceptance-slice `MarkDelivered` transaction. When transcript capture ships in v1.x, `kkd` projects the durable delivery event separately and idempotently, independent of the harness; projection failure cannot roll back delivery. Its first `TranscriptAdapter` implementation is `ClaudeCodeAdapter`; a later Codex adapter writes a different projector and reuses the rest.

## Spawn lifecycle

`kk new` performs the durable creation saga defined in [Threads](../05-threads.md). For the harness portion, credentials and exclusive settings must exist before the external process receives an initial prompt. Reopen, explicit restart, and recovery reuse the same per-incarnation gate and ready proof even though they have different lifecycle journals. The creation order is:

1. Resolve name/prompt/follows/harness/sidebar options. Initial prompt comes from `-m "<prompt>"` (winning if both are supplied) or stdin; absent both, the spawn proceeds without a first-turn prompt and the placeholder name is `unnamed-<short-hex>`.
2. Insert the `Creating` sqlite thread row and lifecycle journal; the stable `thread_id` attaches every later step.
3. `jj workspace add` at the exact selected base under `<workspaces_root>/<repo>-kiki-<slug>/`.
4. In that workspace, create the initial working-copy change, read its exact `@`, and persist it as `thread_head_commit_id`.
5. Create the thread bookmark at that exact commit and persist the same commit as `checkpoint_commit_id`. Kiki never assumes the bookmark followed a later `jj new`.
6. Write the `ThreadScoped<thread_id>` credential to `~/.kiki/repos/<repo_id>/credentials/<thread_id>` (mode `0600`).
7. Generate and validate the launch-scoped isolated settings. If unavailable, perform the ownership-tracked `settings.local.json` merge. Persist enough recovery data to restore the fallback safely before continuing.
8. Create the detached tmux session and optional shell/sidebar panes without starting the harness process.
9. Start the harness launcher blocked on the saga's database-backed one-use readiness gate.
10. Record the process incarnation and activate the gate while the thread remains `Creating`. The launcher may then exec `Harness::spawn(SpawnOpts { thread_id, resume_harness_session_id: Option<HarnessSessionId>, initial_prompt: Option<String>, harness_args })`. A matching ready handshake records the live process and settings fingerprint; only that second transaction completes the saga and enters `Active`. Exec or handshake failure becomes `CreateFailed`.

Every step is journaled and idempotent; failure before step 9 cannot expose a partially configured agent, and failure afterward leaves a recoverable creation state rather than claiming cross-system atomicity.
