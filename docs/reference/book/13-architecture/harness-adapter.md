# Harness adapter

The harness adapter is the seam between `kkd` and an agent runtime. v1 ships two adapters: `claude-code` and `codex`. Other harnesses are deferred. The seam keeps the cascade orchestrator harness-neutral: both v1 adapters satisfy the same trait pair, prove the same capabilities, and speak the same delivery protocol. They differ only in how each proves its boundaries, and those proofs are per adapter/version, never assumed from the other harness's behavior.

## Trait pair

```
trait Harness {
    fn name(&self) -> &str;
    fn capabilities(&self) -> Capabilities;
    fn launch_spec(&self, opts: SpawnOpts) -> Result<LaunchSpec>;
}

struct RunningAgent {
    thread_id: ThreadId,
    agent_session_id: AgentSessionId,
    harness_session_id: HarnessSessionId,
    process: ProcessIdentity,
    launcher: ProcessIdentity,
}

impl RunningAgent {
    fn enqueue_context(&self, msg: ContextMessage) -> Result<()>;
    fn restart_with_message(&self, msg: String) -> Result<()>;
    fn terminate(&self) -> Result<()>;
    fn status(&self) -> AgentStatus;
}
```

The adapter never starts a process. `launch_spec` resolves the options into a `LaunchSpec` — argv, environment, working directory, and settings paths. `kkd` calls it; the `agent` pane launcher receives the result through its gate and executes exactly that. `RunningAgent` is `kkd`'s handle for one incarnation, built from recorded identities; it is not a child-process object owned by the adapter.

`agent_session_id` identifies one kiki-managed process incarnation and changes on every restart. It is the same value the protocol calls `incarnation_id`; the two names never denote different things, and the column names stay as they are. `harness_session_id` identifies the harness conversation and may be reused by `--resume`. This split is required for delivery safety: starting a replacement process retires the previous incarnation and clears its `delivered_intent_id` without acknowledging it. A pending payload is rebound through `RestartStartup` to the new incarnation and a one-use `startup_delivery_id`; the first model turn must causally echo that id before it can acknowledge delivery.

`restart_with_message` implements that proof-carrying path rather than an untracked prepend. Kiki persists the replacement incarnation and startup id before launch; the adapter makes the tagged message the mandatory first harness input, reports an acceptance handshake for that exact id, and includes it in the hook metadata of the resulting first model turn. If the harness cannot supply all three proofs, `restart_startup_delivery` is false.

`process` is the harness process, the child of the thread's `agent` pane launcher. The launcher creates that child held before exec and reports its pid through `ReportHarnessStarted`; `kkd` verifies through the OS that it is the launcher's child and records its identity on `agent_sessions` before the launcher releases it. The harness identity is therefore recorded before the harness runs, and the ready handshake records readiness, not the pid. The launcher's own identity is recorded on `terminal_panes`. Neither stands in for the other, and both are `(pid, start_time)` identities read from the OS rather than bare pids.

`terminate` and `restart_with_message` are orchestration requests, not a second process-control path. `terminate` retires the incarnation by terminating the harness's whole process tree through `ProcessSupervisor`: the tree is recorded, stopped, re-verified, and killed by exact identity, and the launcher is left alive. Hard-pause is the same operation. `restart_with_message` does that and then records a replacement `agent_sessions` row and activates a new one-use gate that the same accepted launcher awaits. A replacement incarnation needs no terminal provisioning.

Before a replacement incarnation's gate is activated, an inventory rooted at the `agent` launcher must show no process other than the launcher itself in its descendant, session, and process-group sets. A surviving tool child of the retired harness raises `OrphanedProcess` with harness-remnant evidence and blocks both the gate and workspace materialization.

The launcher outlives incarnations. A harness exit retires the incarnation without acknowledgement and makes `status` report `Crashed`; it does not end the `agent` role or change the thread's lifecycle. Only the launcher's own exit, or the loss of its binding or server instance, ends the role. A crashed harness under a live launcher is restarted by the `kk repair` plan `restart-agent`, the explicit restart path: it starts a replacement incarnation on the live launcher after the remnant check, with a fresh gate and `RestartStartup` if an intent is pending. It is same-thread and needs no approval in thread context. Kiki's own protocol restarts — a cascade hard restart or a `RestartStartup` replacement — are daemon-initiated steps of the delivery protocol and need no `HumanApproval` either; a human-requested interruption or close does.

The thread credential is rotated when an incarnation ends and at reopen or terminal restart. Its file path is stable and its contents are replaced atomically. The launcher re-reads it after `ReportHarnessExit`; `kk` and `kk-hook` read it on every invocation.

`AgentStatus` is `Running | Quiescent | Stuck(duration) | Crashed`. The cascade orchestrator uses `status` and `capabilities` to decide whether soft-pause is viable and whether pending reconciliation may materialize the managed workspace.

`AgentStatus` is derived only from the harness's own hooks and lifecycle events, the pane launcher's exit report, and `ProcessSupervisor`. The terminal runtime never feeds it. Herdr's agent detection (`idle | working | blocked | done | unknown`) is a screen-and-process heuristic that may be shown as a hint. Neither it, nor `agent.wait`, nor text accepted into a pane's input queue is evidence of `Quiescent`, of quiescence for soft-pause, of delivery, or of acknowledgement. The adapter never delivers a payload by sending terminal input.

## Agent display states

`AgentStatus` is the orchestrator's vocabulary. The human-facing surfaces (`kk ls`, `kk log --wide`, the TUI glyph table in [Interface](../10-interface/spec.md)) render a four-value projection of it, folding in two session signals the harness already emits:

| display state | source                                                                                                                                                                 |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `working`     | `Running`                                                                                                                                                              |
| `idle`        | `Quiescent`, most recent turn not completed (or no turn yet)                                                                                                           |
| `finished`    | `Quiescent`, most recent turn completed (the harness's turn-completion signal: Codex's `Stop` lifecycle event; for Claude Code, the proof named as an open gate below) |
| `blocked`     | `Crashed`, or an unacknowledged attention event such as a permission prompt (see [Observability](../12-observability.md))                                              |

`Stuck(duration)` alone is not `blocked`. A silent agent keeps its `working` or `idle` state and is rendered dim; the silence threshold is a deferred `[notifications]` key.

Kiki installs no Claude Code stop hook unless that hook is promoted with specified, tested behavior. Until then, Claude Code's `finished` state and its `quiescence_detection` capability rest on an adapter/version proof that this chapter does not yet name. That proof is an open gate: a Claude Code version without it reports `quiescence_detection: false`, never shows `finished`, and cannot use agent quiescence as a cascade boundary. Lifecycle preflights do not depend on it: `kk close` preflight proceeds for such a version and warns that a working agent will make the approval drift.

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

`ContextMessageKind` and `JsonValue` are this chapter's names for the message kind and the structured payload type. `ContextMessageKind` includes at least `RebaseAlert`, `ParentMerged`, `ConflictNoticed`, and `UserNote`.

The `structured` field carries diff payloads, file lists, etc. for richer agent re-orientation.

## Hook

`kk-hook` is the pre-tool sidecar that fronts cascade delivery for both v1 harnesses. Claude Code invokes it through its `PreToolUse` hook; Codex invokes it through its lifecycle-hook system, whose `PreToolUse` event covers shell, `apply_patch`, and MCP tool calls. `PreToolUse` and `PostToolBatch` name kiki's protocol entry points, not any harness's event vocabulary; each adapter maps its own events onto them. A `PostToolBatch` report says only that the triggering tool batch has finished; it never acknowledges delivery. The sidecar stays small for latency reasons:

- Fast-path round-trip target: <5ms typical, imperceptible to agents.
- Slow path (rebase + payload compose) is bounded by `jj rebase` plus a small constant.

The hook's exact behavior — unresolved-intent lookup, boundary probe, batch barrier, decision step, and post-stdout `MarkDelivered` — lives in [Cascade](../05-cascade.md). The adapter must attach stable runtime-incarnation, model-turn, and tool-batch identities to soft-delivery calls. It durably fixes `Block` before reconciliation may mutate files. Concurrent `PreToolUse` calls in one batch all receive a blocking response when any member triggers reconciliation. Only a matching `PostToolBatch` can complete `SoftBatch`, and only a later model turn can acknowledge it. `RestartStartup` instead requires the first replacement-process model turn to echo its exact `startup_delivery_id`; it never fabricates a tool batch for startup input.

## Hook degradation

When `kkd` is unreachable (socket missing, connection refused, daemon mid-restart) and no cascade barrier has been activated for the current batch, the hook degrades to pass-through. The connect timeout is 200ms and the overall hook budget is 1s; on expiry the hook returns the harness's non-blocking decision (Claude Code's `continue`, Codex's `allow`) so the agent's tool call is not blocked, then appends one structured record to `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log`.

The per-thread hook launcher (the hook-side process, distinct from the [pane launcher](terminal-runtime.md#provisioning)) caches the first admission decision for the lifetime of each batch so every sibling hook observes the same result. A cached `PassThrough` defers intents discovered later in that batch; a cached `Block(intent_id)` fails closed. If a `PassThrough` cache entry is lost, the hook launcher can no longer prove that reconciliation is safe in that batch. It blocks the unknown call, hard-pauses the old incarnation without mutating the workspace, and starts a replacement before reconsidering pending work. The blocked decision's durable `SoftBatch` proof remains embedded in `sync_intents` and is authoritative after reconnect. If neither the daemon nor the hook launcher's token can prove a blocked batch completed, the adapter blocks the call and requests `RestartStartup` recovery rather than passing through a tool against newly materialized files.

`~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log` is the catch-all for client-side errors that cannot reach `kkd`. It is created lazily at first failure. The hook learns its absolute path at thread-spawn time, where `kkd` writes it into the per-thread harness config alongside the credential path; the source repo's filesystem is never touched.

Pass-through is not a violation of the cascade safety invariant; it is the explicit precondition's failure mode. The cascade invariant in [Invariants](../02-invariants.md) requires `kkd` to be reachable for kiki to materialize a desired state at a safe boundary. When the daemon is unreachable, jj repository state may already contain native descendant evolution, but kiki leaves the workspace files untouched and preserves or reconstructs the pending intent. Two cases:

- The watcher saw the trigger op before the outage. The `sync_intent` and its normalized trigger rows are already in sqlite; they survive the daemon stop.
- The trigger op happened during the outage. The trigger lives in jj's op log (the upstream source of truth). On `kkd` restart, op-log catch-up replays missed ops, populates `op_history`, and runs before/after classification to create the same exact-base-transition intent as the live watcher.

Either way, the next successful PreToolUse round-trip after `kkd` returns selects the oldest unresolved intent and probes the workspace immediately. `NativeRewrite` needs no file update for `FreshClean | FreshDirty` and may update `StaleClean`; `ParentAdvance` may mutate only from `FreshClean`. Any dirty or indeterminate state that requires mutation enters `RecoveryRequired` and hard-pauses for edit-preserving recovery. The successful path persists the result, synthetic payload, anchor, and `Materialized` state on the intent in one transaction. Cascade delivery is deferred, not dropped, and outage edits are not silently hidden.

In the deferred window, jj repository state may already contain evolved descendants while the workspace files remain stale. Before a barrier is activated, the agent's tool call may therefore run against the last materialized files until `kkd` returns. Once reconciliation begins and files may change, all calls in that batch are blocked instead. When `kkd` returns and observes a non-empty `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log` for a thread, it surfaces a single notification per thread summarizing the gap.

## Exclusive hook boundary and settings ownership

A harness may run all matching hooks concurrently, so v1 never claims that `kk-hook` runs first and does not chain user pre-tool hooks. Every managed process incarnation—initial creation, reopen, explicit restart, crash recovery, or `RestartStartup` fallback—starts only after the adapter proves that kiki is the sole matching pre-tool hook for that exact launch. A settings fingerprint from an older incarnation is cache input, not proof for a new one. This restriction is session-scoped: it does not modify user-global configuration and does not disable hooks in unmanaged sessions of either harness. If an adapter cannot prove exclusive pre-tool control, the attempted incarnation fails before the agent receives a prompt.

Herdr ships its own agent integrations, which write hook entries into a harness's configuration directory. Kiki never runs Herdr's integration installer against launch-scoped settings, a generated `CODEX_HOME`, or a workspace settings file, and the generated Herdr configuration never asks Herdr to. Current Herdr integrations for Claude Code and Codex install only a session-start reporter, but earlier versions installed pre-tool entries. The exclusive-hook proof therefore audits the effective settings of each launch for any Herdr hook entry, legacy or current, and treats a matching pre-tool entry as a failed proof like any other foreign hook. Herdr's detection of managed agents works from process and screen observation without those hooks, and kiki does not depend on it.

The harness launch specification removes every `HERDR_*` variable from the harness's environment, so the agent and its tools hold no Herdr socket address or pane identity; the pane keeps `KIKI_THREAD_ID`. Herdr's own hook scripts do nothing without those variables. Like the rest of the model this is cooperative hygiene, not a security boundary: the harness still runs as the same user. A version that provides exclusive hook control but no unambiguous batch boundary may run only when it also proves `restart_startup_delivery`.

### Claude Code

The preferred mechanism is a launch-scoped generated settings file under `~/.config/kiki/repos/<repo_id>/harness/<thread_id>/`, passed with harness arguments that isolate the managed process from project, local-project, and user `PreToolUse` definitions. The generated file declares kiki's `PreToolUse`, its batch-completion entry point where supported, and absolute credential/error-log paths. An adapter/version combination is accepted only after an integration test proves that no independently discovered user or project `PreToolUse` hook runs in that managed process. Unrelated hook events may remain enabled only when the same test proves they cannot race workspace reconciliation or reintroduce a matching `PreToolUse` hook.

If Claude Code cannot accept a fully isolated launch-scoped settings source, the fallback is a structural merge into `<workspace>/.claude/settings.local.json`. Kiki records the prior bytes and content hash outside the workspace, installs a uniquely identified fragment, and restores only when the current file still matches the kiki-owned post-merge hash. Concurrent human edits cause an ownership conflict and require explicit repair; kiki never overwrites them. The fallback must also prove that inherited/global `PreToolUse` hooks are excluded, not merely that kiki's hook appears in the local file.

Kiki never writes, replaces, or deletes `<workspace>/.claude/settings.json`; it may be tracked project configuration.

### Codex

Codex resolves its configuration, hooks, trust store, sessions, and authentication from one root directory selected by `CODEX_HOME`. The adapter launches every managed incarnation with `CODEX_HOME` pointed at the same launch-scoped directory, `~/.config/kiki/repos/<repo_id>/harness/<thread_id>/`. Kiki generates that home per incarnation: a `config.toml` that enables the lifecycle-hook feature, declares kiki's `PreToolUse` and turn-lifecycle hooks with absolute credential/error-log paths, and pre-trusts exactly those hooks in the generated trust store. Because the launch-scoped home _is_ the user layer for that process, the user's real `~/.codex/` configuration and hooks are structurally excluded rather than merely overridden.

Two obligations follow from the relocation. First, `CODEX_HOME` also moves authentication, so the adapter must provision credentials into the generated home explicitly (a copied auth file or a configured API-key source) before the launch gate opens; a launch that would fall back to the user's real home for auth is a failed isolation proof. Second, workspace-local `.codex/` configuration can still be discovered from the working directory. Codex's trust model leaves non-managed project hooks untrusted by default, and the generated trust store grants nothing beyond kiki's own hooks — but that exclusion is an integration-gate proof per pinned version, not an assumption. A version in which a workspace `.codex/` hook, plugin hook, or managed-policy hook can run in the managed process without kiki's grant fails the gate.

There is no workspace-merge fallback for Codex. Kiki never writes, replaces, or deletes anything under `<workspace>/.codex/`; if launch-scoped `CODEX_HOME` isolation is unavailable or its proof fails, the attempted incarnation fails before the agent receives a prompt.

## Codex boundary mapping

Codex's hook events carry `session_id`, turn-scoped `turn_id`, and per-call `tool_use_id`. A Codex turn spans the whole agentic loop for one user input — many sequential model steps share one `turn_id` — so `turn_id` is not the protocol's `model_turn_id`. What stands in for it is the model step, and proven-serial dispatch is what makes steps identifiable: once the integration gate proves the pinned version never runs two tool calls of one turn concurrently and requests a new tool only after the model has consumed the previous call's result, each `tool_use_id` names a distinct model step and durable hook-arrival order is step order. The adapter uses `tool_use_id` as `tool_batch_id` (a batch of one) and the recorded serial order — with `turn_id` monotonicity as a cross-check — as its model-turn identity. The proof is version-scoped and must cover subagent-originated tool calls; a version that dispatches concurrently, or whose subagents do, without an unambiguous boundary loses `parallel_batch_boundary` and runs with `RestartStartup` delivery only.

A blocked call is expressed through the hook's deny decision, whose reason is returned to the model as the tool result. The integration gate must prove the saved payload reaches the model byte-identically through that channel; lossy truncation or reformatting fails soft delivery. Denial also means the tool never executes, so a blocked batch never produces a post-tool event — and the completion proof cannot be the emitting hook's own post-stdout RPC either, because that best-effort call dies with the hook. The harness itself supplies the crash-surviving report: under the serial-dispatch proof, the next turn-scoped hook event of the same incarnation — a `PreToolUse` with a serially later `tool_use_id`, or the turn's `Stop` — can only arrive after the blocked call resolved, so its admission transaction durably records the blocked batch's `batch_completed_at`. That arrival is the Codex adapter's `PostToolBatch` report, and like every `PostToolBatch` it never acknowledges by itself. `structured_tool_hooks` requires the same coverage proof as everywhere else: every workspace-observing tool in the pinned version fires `PreToolUse`, or the generated config disables the ones that do not.

`MarkDelivered` remains the ordinary best-effort post-stdout RPC, but for Codex it is never acknowledgement evidence: it proves the hook wrote the deny, not that the harness applied it. A hook that exceeds the harness-side timeout, or whose output the harness rejects, writes stdout into a void while the model receives a substituted result. The authoritative consumption evidence is the **delivery receipt**: Codex durably persists every tool call's result — a deny reason included — in its session record under the launch-scoped `CODEX_HOME`, because resume must reconstruct exactly what the model saw. The completing arrival's transaction therefore acknowledges only when the session record's result for the blocked `tool_use_id` is the byte-identical saved payload; the receipt is also the runtime enforcement of the deny-fidelity gate proof. A contrary receipt — the record shows a generic or substituted result — means the model consumed something else and the tool did not run, so the prepared payload is rebound to the arriving batch and emitted byte-identically there, per the protocol's ordinary redelivery step. That retry is bounded, and the bound is durable: the rebinding transaction counts the attempt on the intent itself, so a daemon restart cannot forget a contrary receipt and re-enter the retry. A second contrary receipt for the same intent proves the deny channel itself is rejecting this payload on this version, so the intent fails over to `RestartStartup`, whose delivery is the mandatory first input of a replacement process and does not ride the hook output at all. A receipt not yet readable defers acknowledgement to a later boundary when no further delivery is pending, and otherwise fails closed into `RestartStartup` within the hook budget, preferring a rare duplicate delivery over a wrong acknowledgement. Delivery failure never loops silently past that ladder: bounded `RestartStartup` attempts that keep failing their handshake or echo record exhaustion on the intent in the transaction that abandons the last attempt, leave it unacknowledged, keep the agent hard-paused, and raise a loud attention event for the human. Restart recovery resumes that exhausted state and re-surfaces the blocked thread; it never mints a fresh attempt against it. The only exits are the two `kk repair` plans defined in [Cascade](../05-cascade.md#delivery-protocol): a journaled retry that re-arms one fresh bounded cycle, or a one-shot-approved discard that acknowledges without delivery proof.

Three supporting properties are version proofs at the gate: the per-thread hook launcher answers for a dead sidecar under an active barrier with a generic blocking deny, so a barrier-covered call never fails open into tool execution; the generated config pins the harness-side hook timeout above the slow path's bound so a healthy hook cannot be timed out mid-reconciliation; and the pinned version's session record durably contains each tool result as returned to the model, deny results included, so receipts exist to be read. A payload delivered on a turn's final tool call stays `Delivered` until the next turn's first `PreToolUse`; `Stop` completes the batch but never acknowledges.

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

`kk new` performs the durable creation saga defined in [Threads](../03-threads.md). For the harness portion, credentials and exclusive settings must exist before the external process receives an initial prompt. Reopen, explicit restart, and recovery reuse the same per-incarnation gate and ready proof even though they have different lifecycle journals. The creation order is:

1. Resolve name/prompt/follows/harness/pane options. Initial prompt comes from `-m "<prompt>"` (winning if both are supplied) or stdin; absent both, the spawn proceeds without a first-turn prompt and the placeholder name is `unnamed-<short-hex>`.
2. Insert the `Creating` sqlite thread row and lifecycle journal; the stable `thread_id` attaches every later step.
3. `jj workspace add` at the exact selected base under `<workspaces_root>/<repo>-kiki-<slug>/`. The command is pinned to the sampled operation head and does not ignore the working copy, because it must write the new one. It creates the workspace and its initial working-copy commit in one command.
4. Read that workspace's exact `@` with a pinned read and persist it as `thread_head_commit_id`.
5. Create the thread bookmark at that exact commit. Persist the same commit as `checkpoint_commit_id` and as `bookmark_expected_commit_id`, and append the placement row to `thread_checkpoints`. Kiki never assumes the bookmark followed a later `jj new`.
6. Write the `ThreadScoped<thread_id>` credential to `~/.config/kiki/repos/<repo_id>/credentials/<thread_id>` (mode `0600`).
7. Generate and validate the launch-scoped isolated settings — Claude Code's generated settings file or Codex's generated `CODEX_HOME`. If Claude Code cannot accept isolated launch settings, perform the ownership-tracked `settings.local.json` merge and persist enough recovery data to restore it safely before continuing; the Codex adapter has no workspace-merge fallback and fails the incarnation instead.
8. Run the orphan scan for the thread, then provision its terminal group through `TerminalRuntime`, following the journaled protocol in [Terminal runtime](terminal-runtime.md#provisioning): persist the `provision_id`, intended roles, exact workspace path, current `server_instance_id`, and the hash of the provision nonce; then create the Herdr workspace and apply the role layout. Every role pane's direct command is the pane launcher, started by argv with an explicit working directory and environment. The argv carries only the `provision_id` and role; the nonce travels in the launch environment. Nothing is typed into a shell, and no harness process starts in this step. Herdr's create call first starts the user's login shell in the jj workspace, where it runs its rc files, before the layout replaces that tab; that shell is an ordinary pane member until it is gone, and the layout appends a new tab with new ids rather than reusing the old ones.
9. Each launcher reports its Herdr ids, then blocks on its gate. `kkd` accepts a report only from a process whose parent is the current server instance and which a fresh per-pane process query shows to be the reported pane's root. In one transaction `kkd` accepts exactly one launcher per `(provision_id, role)`, records its OS-read process identity, and marks the terminal binding `Bound`. A duplicate launcher from a repeated create call is refused and exits without starting anything; a group whose launchers are all refused removes itself, because Herdr drops a workspace when its last pane's command exits.
10. In a second transaction, which requires the `Bound` binding, record the process incarnation and activate its one-use launch gate while the thread remains `Creating`. `kkd` resolves `SpawnOpts { thread_id, resume_harness_session_id: Option<HarnessSessionId>, initial_prompt: Option<String>, harness_args }` through `Harness::launch_spec` and delivers the result on the launcher's supervision stream. The launcher creates the harness child held before exec, reports its pid through `ReportHarnessStarted`, and releases it only after `kkd` has verified and recorded the child's identity on `agent_sessions`. The harness then runs in the pane's foreground. The launcher does not replace itself: it stays alive across incarnations, because Herdr removes a pane when its direct command exits, and it reports the harness's exit. `kk-hook` sends the ready handshake from the harness's session-start hook event with the incarnation id and the settings and hook fingerprints. The transaction that commits it re-reads the launcher's OS identity and the open `terminal_servers` row; only that transaction completes the saga and enters `Active`. Launch or handshake failure becomes `CreateFailed`.

Every step is journaled. Steps 1–7 are idempotent. Step 8 is not idempotent at the runtime — a lost reply may have created a terminal group — so recovery reads a fresh snapshot and launcher reports before it issues any new call, and the single gate claim in step 9 guarantees that a duplicate group can never yield a duplicate harness. Failure before step 10 cannot expose a partially configured agent, and failure afterward leaves a recoverable creation state rather than claiming cross-system atomicity.

Automatic compensation is limited. It may close the provisioned group and remove the new jj workspace only while the launch gate was never activated, `ProcessSupervisor` shows the group contains nothing but kiki's own blocked launchers, and the workspace still equals its initial materialization. Otherwise the saga stops in `CreateFailed` with its projections intact, and cleanup is an approved repair plan that uses the close machinery: freeze, loss inventory, final proof, termination, verified exit.

A successful create or layout reply, a visible prompt, and Herdr reporting an agent in the pane are not steps in this sequence and complete none of them.
