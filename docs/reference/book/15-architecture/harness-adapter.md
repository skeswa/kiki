# Harness adapter

The harness adapter is the seam between `kkd` and an agent runtime. v1 ships two adapters: `claude-code` and `codex`. Other harnesses are deferred. The seam keeps the cascade orchestrator harness-neutral: both v1 adapters satisfy the same trait pair, prove the same capabilities, and speak the same delivery protocol. They differ only in how each proves its boundaries, and those proofs are per adapter/version, never assumed from the other harness's behavior.

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
| `finished`    | `Quiescent`, most recent turn completed (the harness's turn-completion signal; Claude Code's stop event, Codex's `Stop` lifecycle event)     |
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

These fields describe behavioral proof, not a particular settings mechanism. `exclusive_pre_tool_use` may be satisfied by isolated launch settings (Claude Code), a launch-scoped harness home (Codex), or the ownership-tracked fallback, but a managed v1 process cannot start when it is false. `structured_tool_hooks` is true only when every tool that can observe or mutate workspace files is hook-gated in the pinned harness version, or the launch-scoped configuration disables the tools that are not; a harness whose file-touching tools can bypass the pre-tool boundary has no safe soft barrier. Without `parallel_batch_boundary`, soft delivery is disabled. Kiki may then fall back only when `restart_startup_delivery` proves that a tagged payload is the mandatory first input and that the resulting model turn echoes its one-use id; otherwise cascade-capable managed execution is unsupported. For a harness without `soft_pause`, `enqueue_context` leaves the prepared payload on its intent for this restart path. The daemon checks `capabilities` for every new incarnation rather than assuming a prior process's result remains valid.

`parallel_batch_boundary` does not require that the harness dispatches tools in parallel — it requires that the batch boundary is unambiguous. Claude Code satisfies it with an explicit batch-completion signal over concurrently dispatched calls. A serial dispatcher satisfies it degenerately: when the integration gate proves the pinned version never runs two tool calls of one model turn concurrently, each batch contains exactly one call and closes when that call resolves. How resolution is proved is the adapter's obligation — an executed call resolves with its post-tool event, but a denied call never executes and never produces one, so completion must come from a harness-driven signal that survives the emitting hook's crash: under the serial proof, the next turn-scoped hook event can only arrive after the blocked call resolved. The proof is version-scoped; a version that begins dispatching concurrently without a provable completion boundary loses the capability and drops to `RestartStartup`.

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

`kk-hook` is the pre-tool sidecar that fronts cascade delivery for both v1 harnesses. Claude Code invokes it through its `PreToolUse` hook; Codex invokes it through its lifecycle-hook system, whose `PreToolUse` event covers shell, `apply_patch`, and MCP tool calls. `PreToolUse` and `PostToolBatch` name kiki's protocol entry points, not any harness's event vocabulary; each adapter maps its own events onto them. A `PostToolBatch` report says only that the triggering tool batch has finished; it never acknowledges delivery. The sidecar stays small for latency reasons:

- Fast-path round-trip target: <5ms typical, imperceptible to agents.
- Slow path (rebase + payload compose) is bounded by `jj rebase` plus a small constant.

The hook's exact behavior — unresolved-intent lookup, boundary probe, batch barrier, decision step, and post-stdout `MarkDelivered` — lives in [Cascade](../07-cascade.md). The adapter must attach stable runtime-incarnation, model-turn, and tool-batch identities to soft-delivery calls. It durably fixes `Block` before reconciliation may mutate files. Concurrent `PreToolUse` calls in one batch all receive a blocking response when any member triggers reconciliation. Only a matching `PostToolBatch` can complete `SoftBatch`, and only a later model turn can acknowledge it. `RestartStartup` instead requires the first replacement-process model turn to echo its exact `startup_delivery_id`; it never fabricates a tool batch for startup input.

## Hook degradation

When `kkd` is unreachable (socket missing, connection refused, daemon mid-restart) and no cascade barrier has been activated for the current batch, the hook degrades to pass-through. The connect timeout is 200ms and the overall hook budget is 1s; on expiry the hook returns the harness's non-blocking decision (Claude Code's `continue`, Codex's `allow`) so the agent's tool call is not blocked, then appends one structured record to `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log`.

The per-thread hook launcher caches the first admission decision for the lifetime of each batch so every sibling hook observes the same result. A cached `PassThrough` defers intents discovered later in that batch; a cached `Block(intent_id)` fails closed. If a `PassThrough` cache entry is lost, the launcher can no longer prove that reconciliation is safe in that batch. It blocks the unknown call, hard-pauses the old incarnation without mutating the workspace, and starts a replacement before reconsidering pending work. The blocked decision's durable `SoftBatch` proof remains embedded in `sync_intents` and is authoritative after reconnect. If neither the daemon nor the launcher token can prove a blocked batch completed, the adapter blocks the call and requests `RestartStartup` recovery rather than passing through a tool against newly materialized files.

`~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log` is the catch-all for client-side errors that cannot reach `kkd`. It is created lazily at first failure. The hook learns its absolute path at thread-spawn time, where `kkd` writes it into the per-thread harness config alongside the credential path; the source repo's filesystem is never touched.

Pass-through is not a violation of the cascade safety invariant; it is the explicit precondition's failure mode. The cascade invariant in [Invariants](../04-invariants.md) requires `kkd` to be reachable for kiki to materialize a desired state at a safe boundary. When the daemon is unreachable, jj repository state may already contain native descendant evolution, but kiki leaves the workspace files untouched and preserves or reconstructs the pending intent. Two cases:

- The watcher saw the trigger op before the outage. The `sync_intent` and its normalized trigger rows are already in sqlite; they survive the daemon stop.
- The trigger op happened during the outage. The trigger lives in jj's op log (the upstream source of truth). On `kkd` restart, op-log catch-up replays missed ops, populates `op_history`, and runs before/after classification to create the same exact-base-transition intent as the live watcher.

Either way, the next successful PreToolUse round-trip after `kkd` returns selects the oldest unresolved intent and probes the workspace immediately. `NativeRewrite` needs no file update for `FreshClean | FreshDirty` and may update `StaleClean`; `ParentAdvance` may mutate only from `FreshClean`. Any dirty or indeterminate state that requires mutation enters `RecoveryRequired` and hard-pauses for edit-preserving recovery. The successful path persists the result, synthetic payload, anchor, and `Materialized` state on the intent in one transaction. Cascade delivery is deferred, not dropped, and outage edits are not silently hidden.

In the deferred window, jj repository state may already contain evolved descendants while the workspace files remain stale. Before a barrier is activated, the agent's tool call may therefore run against the last materialized files until `kkd` returns. Once reconciliation begins and files may change, all calls in that batch are blocked instead. When `kkd` returns and observes a non-empty `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log` for a thread, it surfaces a single notification per thread summarizing the gap.

## Exclusive hook boundary and settings ownership

A harness may run all matching hooks concurrently, so v1 never claims that `kk-hook` runs first and does not chain user pre-tool hooks. Every managed process incarnation—initial creation, reopen, explicit restart, crash recovery, or `RestartStartup` fallback—starts only after the adapter proves that kiki is the sole matching pre-tool hook for that exact launch. A settings fingerprint from an older incarnation is cache input, not proof for a new one. This restriction is session-scoped: it does not modify user-global configuration and does not disable hooks in unmanaged sessions of either harness. If an adapter cannot prove exclusive pre-tool control, the attempted incarnation fails before the agent receives a prompt. A version that provides exclusive hook control but no unambiguous batch boundary may run only when it also proves `restart_startup_delivery`.

### Claude Code

The preferred mechanism is a launch-scoped generated settings file under `~/.config/kiki/repos/<repo_id>/harness/<thread_id>/`, passed with harness arguments that isolate the managed process from project, local-project, and user `PreToolUse` definitions. The generated file declares kiki's `PreToolUse`, its batch-completion entry point where supported, and absolute credential/error-log paths. An adapter/version combination is accepted only after an integration test proves that no independently discovered user or project `PreToolUse` hook runs in that managed process. Unrelated hook events may remain enabled only when the same test proves they cannot race workspace reconciliation or reintroduce a matching `PreToolUse` hook.

If Claude Code cannot accept a fully isolated launch-scoped settings source, the fallback is a structural merge into `<workspace>/.claude/settings.local.json`. Kiki records the prior bytes and content hash outside the workspace, installs a uniquely identified fragment, and restores only when the current file still matches the kiki-owned post-merge hash. Concurrent human edits cause an ownership conflict and require explicit repair; kiki never overwrites them. The fallback must also prove that inherited/global `PreToolUse` hooks are excluded, not merely that kiki's hook appears in the local file.

Kiki never writes, replaces, or deletes `<workspace>/.claude/settings.json`; it may be tracked project configuration.

### Codex

Codex resolves its configuration, hooks, trust store, sessions, and authentication from one root directory selected by `CODEX_HOME`. The adapter launches every managed incarnation with `CODEX_HOME` pointed at the same launch-scoped directory, `~/.config/kiki/repos/<repo_id>/harness/<thread_id>/`. Kiki generates that home per incarnation: a `config.toml` that enables the lifecycle-hook feature, declares kiki's `PreToolUse` and turn-lifecycle hooks with absolute credential/error-log paths, and pre-trusts exactly those hooks in the generated trust store. Because the launch-scoped home *is* the user layer for that process, the user's real `~/.codex/` configuration and hooks are structurally excluded rather than merely overridden.

Two obligations follow from the relocation. First, `CODEX_HOME` also moves authentication, so the adapter must provision credentials into the generated home explicitly (a copied auth file or a configured API-key source) before the launch gate opens; a launch that would fall back to the user's real home for auth is a failed isolation proof. Second, workspace-local `.codex/` configuration can still be discovered from the working directory. Codex's trust model leaves non-managed project hooks untrusted by default, and the generated trust store grants nothing beyond kiki's own hooks — but that exclusion is an integration-gate proof per pinned version, not an assumption. A version in which a workspace `.codex/` hook, plugin hook, or managed-policy hook can run in the managed process without kiki's grant fails the gate.

There is no workspace-merge fallback for Codex. Kiki never writes, replaces, or deletes anything under `<workspace>/.codex/`; if launch-scoped `CODEX_HOME` isolation is unavailable or its proof fails, the attempted incarnation fails before the agent receives a prompt.

## Codex boundary mapping

Codex's hook events carry `session_id`, turn-scoped `turn_id`, and per-call `tool_use_id`. A Codex turn spans the whole agentic loop for one user input — many sequential model steps share one `turn_id` — so `turn_id` is not the protocol's `model_turn_id`. What stands in for it is the model step, and proven-serial dispatch is what makes steps identifiable: once the integration gate proves the pinned version never runs two tool calls of one turn concurrently and requests a new tool only after the model has consumed the previous call's result, each `tool_use_id` names a distinct model step and durable hook-arrival order is step order. The adapter uses `tool_use_id` as `tool_batch_id` (a batch of one) and the recorded serial order — with `turn_id` monotonicity as a cross-check — as its model-turn identity. The proof is version-scoped and must cover subagent-originated tool calls; a version that dispatches concurrently, or whose subagents do, without an unambiguous boundary loses `parallel_batch_boundary` and runs with `RestartStartup` delivery only.

A blocked call is expressed through the hook's deny decision, whose reason is returned to the model as the tool result. The integration gate must prove the saved payload reaches the model byte-identically through that channel; lossy truncation or reformatting fails soft delivery. Denial also means the tool never executes, so a blocked batch never produces a post-tool event — and the completion proof cannot be the emitting hook's own post-stdout RPC either, because that best-effort call dies with the hook. The harness itself supplies the crash-surviving report: under the serial-dispatch proof, the next turn-scoped hook event of the same incarnation — a `PreToolUse` with a serially later `tool_use_id`, or the turn's `Stop` — can only arrive after the blocked call resolved, so its admission transaction durably records the blocked batch's `batch_completed_at`. That arrival is the Codex adapter's `PostToolBatch` report, and like every `PostToolBatch` it never acknowledges by itself. `structured_tool_hooks` requires the same coverage proof as everywhere else: every workspace-observing tool in the pinned version fires `PreToolUse`, or the generated config disables the ones that do not.

`MarkDelivered` remains the ordinary best-effort post-stdout RPC, but for Codex it is never acknowledgement evidence: it proves the hook wrote the deny, not that the harness applied it. A hook that exceeds the harness-side timeout, or whose output the harness rejects, writes stdout into a void while the model receives a substituted result. The authoritative consumption evidence is the **delivery receipt**: Codex durably persists every tool call's result — a deny reason included — in its session record under the launch-scoped `CODEX_HOME`, because resume must reconstruct exactly what the model saw. The completing arrival's transaction therefore acknowledges only when the session record's result for the blocked `tool_use_id` is the byte-identical saved payload; the receipt is also the runtime enforcement of the deny-fidelity gate proof. A contrary receipt — the record shows a generic or substituted result — means the model consumed something else and the tool did not run, so the prepared payload is rebound to the arriving batch and emitted byte-identically there, per the protocol's ordinary redelivery step. That retry is bounded, and the bound is durable: the rebinding transaction counts the attempt on the intent itself, so a daemon restart cannot forget a contrary receipt and re-enter the retry. A second contrary receipt for the same intent proves the deny channel itself is rejecting this payload on this version, so the intent fails over to `RestartStartup`, whose delivery is the mandatory first input of a replacement process and does not ride the hook output at all. A receipt not yet readable defers acknowledgement to a later boundary when no further delivery is pending, and otherwise fails closed into `RestartStartup` within the hook budget, preferring a rare duplicate delivery over a wrong acknowledgement. Delivery failure never loops silently past that ladder: bounded `RestartStartup` attempts that keep failing their handshake or echo record exhaustion on the intent in the transaction that abandons the last attempt, leave it unacknowledged, keep the agent hard-paused, and raise a loud attention event for the human. Restart recovery resumes that exhausted state and re-surfaces the blocked thread; it never mints a fresh attempt against it. The only exits are the two `kk repair` plans defined in [Cascade](../07-cascade.md#delivery-protocol): a journaled retry that re-arms one fresh bounded cycle, or a one-shot-approved discard that acknowledges without delivery proof.

Three supporting properties are version proofs at the gate: the per-thread launcher answers for a dead sidecar under an active barrier with a generic blocking deny, so a barrier-covered call never fails open into tool execution; the generated config pins the harness-side hook timeout above the slow path's bound so a healthy hook cannot be timed out mid-reconciliation; and the pinned version's session record durably contains each tool result as returned to the model, deny results included, so receipts exist to be read. A payload delivered on a turn's final tool call stays `Delivered` until the next turn's first `PreToolUse`; `Stop` completes the batch but never acknowledges.

The `Stop` lifecycle event is the turn-completion signal behind the `finished` display state and quiescence detection. `SessionStart` distinguishes fresh starts from resumes, and the adapter uses it — together with the mandatory tagged first input — for the `RestartStartup` acceptance handshake: kiki starts or resumes the harness session (`codex resume <harness_session_id>`) with the saved payload as the first input carrying the one-use `startup_delivery_id`, and the first model turn generated from that input must echo the id through its turn-scoped hook metadata before acknowledgement, exactly as the protocol requires of every adapter.

## Per-thread harness selection

- Default per-repo via `agent.default_harness`.
- Override per-thread via `kk new <name> --harness <name>` and `--harness-arg "..."`.
- A thread cannot change harness mid-life; `kk thread restart <thread> --harness <new>` is the explicit path (terminates the current agent and respawns).
- v1: the `Harness` trait is the architectural seam, and the `claude-code` and `codex` adapters ship. `kk new --harness <other>` errors with `"unsupported harness in v1"`. `kk new` (no `--harness`) defaults to `agent.default_harness` (initially `claude-code`) and errors at spawn time with `"<harness> not on PATH — install it or pass --harness <other>"` if that harness's binary is missing. `kk init` does not pre-validate any harness binary; the architecture is BYO-harness.

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

Cascade-injection row writes are NOT part of this trait or the acceptance-slice `MarkDelivered` transaction. When transcript capture ships in v1.x, `kkd` projects the durable delivery event separately and idempotently, independent of the harness; projection failure cannot roll back delivery. Its first `TranscriptAdapter` implementations are `ClaudeCodeAdapter`, over Claude Code's session JSONL, and `CodexAdapter`, over Codex's rollout JSONL under the launch-scoped `CODEX_HOME` — which makes discovery deterministic rather than a search of the user's real session directory. Each writes a different projector and reuses the rest.

## Spawn lifecycle

`kk new` performs the durable creation saga defined in [Threads](../05-threads.md). For the harness portion, credentials and exclusive settings must exist before the external process receives an initial prompt. Reopen, explicit restart, and recovery reuse the same per-incarnation gate and ready proof even though they have different lifecycle journals. The creation order is:

1. Resolve name/prompt/follows/harness/sidebar options. Initial prompt comes from `-m "<prompt>"` (winning if both are supplied) or stdin; absent both, the spawn proceeds without a first-turn prompt and the placeholder name is `unnamed-<short-hex>`.
2. Insert the `Creating` sqlite thread row and lifecycle journal; the stable `thread_id` attaches every later step.
3. `jj workspace add` at the exact selected base under `<workspaces_root>/<repo>-kiki-<slug>/`.
4. In that workspace, create the initial working-copy change, read its exact `@`, and persist it as `thread_head_commit_id`.
5. Create the thread bookmark at that exact commit and persist the same commit as `checkpoint_commit_id`. Kiki never assumes the bookmark followed a later `jj new`.
6. Write the `ThreadScoped<thread_id>` credential to `~/.config/kiki/repos/<repo_id>/credentials/<thread_id>` (mode `0600`).
7. Generate and validate the launch-scoped isolated settings — Claude Code's generated settings file or Codex's generated `CODEX_HOME`. If Claude Code cannot accept isolated launch settings, perform the ownership-tracked `settings.local.json` merge and persist enough recovery data to restore it safely before continuing; the Codex adapter has no workspace-merge fallback and fails the incarnation instead.
8. Create the detached tmux session and optional shell/sidebar panes without starting the harness process.
9. Start the harness launcher blocked on the saga's database-backed one-use readiness gate.
10. Record the process incarnation and activate the gate while the thread remains `Creating`. The launcher may then exec `Harness::spawn(SpawnOpts { thread_id, resume_harness_session_id: Option<HarnessSessionId>, initial_prompt: Option<String>, harness_args })`. A matching ready handshake records the live process and settings fingerprint; only that second transaction completes the saga and enters `Active`. Exec or handshake failure becomes `CreateFailed`.

Every step is journaled and idempotent; failure before step 9 cannot expose a partially configured agent, and failure afterward leaves a recoverable creation state rather than claiming cross-system atomicity.
