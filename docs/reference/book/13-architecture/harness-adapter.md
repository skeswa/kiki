# Harness adapter

A [harness](../appendix-a-glossary.md#harness) is an agent runtime: the program that runs a coding agent, such as [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) or [Codex](https://github.com/openai/codex). The harness adapter is the seam between [`kkd`](../appendix-a-glossary.md#kkd) (kiki's background program) and an agent runtime.

- v1 ships two adapters: `claude-code` and `codex`. Other harnesses are deferred.
- The seam keeps the cascade orchestrator harness-neutral. Both v1 adapters satisfy the same trait pair, prove the same capabilities, and speak the same delivery protocol.
- The adapters differ only in how each proves its boundaries.
- Those proofs are per adapter/version. They are never assumed from the other harness's behavior.

## Trait pair

A [trait](https://doc.rust-lang.org/book/ch10-02-traits.html) is Rust's way to describe a set of functions that a type must provide.

```
trait Harness {
    fn name(&self) -> &str;
    fn capabilities(&self) -> Capabilities;
    fn launch_spec(&self, opts: SpawnOpts) -> Result<LaunchSpec>;
    fn audit_exclusivity(&self, spec: &LaunchSpec) -> Result<ExclusivityProof>;
    fn map_event(&self, event: &HookEvent) -> Result<BoundaryIdentity>;
    fn delivery_receipt(&self, session: &HarnessSessionId, batch: &ToolBatchId) -> Result<ReceiptOutcome>;
    fn status_inputs(&self, event: &HookEvent) -> Vec<StatusInput>;
}

// A `kkd` type. It is not part of `kiki-core`.
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

### What each part is for

The `Harness` trait lives in `kiki-core`. It does no I/O of its own beyond reading the harness's files. Its methods are:

- **`launch_spec`** turns spawn options into the exact command to run (see the next section).
- **`audit_exclusivity`** reads the effective settings of one planned launch. It proves that kiki's hook is the only matching pre-tool hook, or it fails. See [Exclusive hook boundary](#exclusive-hook-boundary-and-settings-ownership).
- **`map_event`** maps one harness hook event onto kiki's protocol terms. It returns the incarnation, the [model turn](../appendix-a-glossary.md#model-turn) identity, and the [tool batch](../appendix-a-glossary.md#tool-batch) identity. It also says which protocol entry point the event is: session start, `PreToolUse`, `PostToolBatch`, or turn completion. An event the adapter cannot map with proof returns an error, and the caller treats the batch as unknown.
- **`delivery_receipt`** looks up what the model actually received for one blocked batch. It returns matching, contrary, or not yet readable. An adapter whose harness needs no receipt returns "not required". See [The delivery receipt](#the-delivery-receipt).
- **`status_inputs`** turns a harness event into the facts that feed [`AgentStatus`](../appendix-a-glossary.md#agentstatus) and the display states: a turn started, a turn completed, or an attention event such as a permission prompt.

`HookEvent`, `BoundaryIdentity`, `ExclusivityProof`, `ReceiptOutcome`, and `StatusInput` are this chapter's names for those inputs and results.

`RunningAgent` is a `kkd` type, not a `kiki-core` type. It needs the database, the pane launcher's stream, and `ProcessSupervisor`, and `kiki-core` does no I/O.

### The adapter never starts a process

The adapter never starts a process.

- `launch_spec` resolves the options into a [`LaunchSpec`](../appendix-a-glossary.md#launch-specification): argv (the command line), environment, working directory, and settings paths.
- `kkd` calls it.
- The `agent` [pane launcher](../appendix-a-glossary.md#pane-launcher) receives the result through its gate and executes exactly that.
- `RunningAgent` is `kkd`'s handle for one [incarnation](../appendix-a-glossary.md#runtime-agent-incarnation) (one run of a harness process), built from recorded identities. It is not a child-process object owned by the adapter.

### Two session ids

- `agent_session_id` identifies one kiki-managed process incarnation. It changes on every restart.
  - It is the same value the protocol calls `incarnation_id`. The two names never denote different things, and the column names stay as they are.
- `harness_session_id` identifies the harness conversation. It may be reused by `--resume`.

This split is required for delivery safety:

- Starting a replacement process retires the previous incarnation and clears its `delivered_intent_id` without acknowledging it.
- A pending payload is rebound through [`RestartStartup`](../appendix-a-glossary.md#restartstartup-delivery-proof) to the new incarnation and a one-use `startup_delivery_id`.
- The first [model turn](../appendix-a-glossary.md#model-turn) of the new incarnation must prove it came from that startup input before it can acknowledge delivery.

`restart_with_message` implements that proof-carrying path rather than an untracked prepend. Kiki persists the replacement incarnation and startup id before launch. The mechanism is the same for both harnesses:

1. The [launch specification](../appendix-a-glossary.md#launch-specification) makes the saved payload the mandatory first harness input. It also carries the `startup_delivery_id` in the launcher environment that the harness and its hooks inherit.
2. The session-start hook reports that exact id with `ReportHarnessReady`. This is the acceptance handshake.
3. The first pre-tool hook call of a model turn in that incarnation is the acknowledgement. `kkd` ties it to the startup id through the incarnation, so no tool batch is made up for the startup input.

Each harness must prove all three facts for its pinned version, in its own proof-of-concept step (see [Build Sequencing](../15-build-sequencing.md#proof-of-concept)). The proof is required for both adapters. It is not an optional extra.

If the proof fails for a harness, `restart_startup_delivery` is false for it. That harness then ships managed sessions without cascade delivery, so its threads cannot follow other threads. That scope cut is recorded as a new decision record.

### Process identities

`process` is the harness process. It is the child of the thread's `agent` pane launcher.

1. The launcher creates that child held before exec (the child exists but has not started running the harness program).
2. The launcher reports the child's pid ([process id](https://en.wikipedia.org/wiki/Process_identifier)) through `ReportHarnessStarted`.
3. `kkd` verifies through the OS that it is the launcher's child, and records its identity on `agent_sessions`.
4. Only then does the launcher release it.

`ReportHarnessStarted` is [idempotent](https://en.wikipedia.org/wiki/Idempotence) (safe to repeat).

- A repeat from the same launcher, for the same incarnation and the same child identity, is accepted as a no-op and gets the same answer. So a launcher whose reply was lost can send the report again.
- A launcher that already holds a recorded child ignores a re-delivered gate specification. It does not create a second child. It reports the existing child again.
- A report that names a different child for an incarnation that already has one is refused.

The harness identity is therefore recorded before the harness runs. The [ready handshake](../appendix-a-glossary.md#ready-handshake) records readiness, not the pid.

The launcher's own identity is recorded on `terminal_panes`. Neither identity stands in for the other. Both are `(pid, start_time)` identities read from the OS rather than bare pids.

### Terminate and restart

`terminate` and `restart_with_message` are orchestration requests, not a second process-control path.

- `terminate` retires the incarnation by terminating the harness's whole process tree through [`ProcessSupervisor`](../appendix-a-glossary.md#processsupervisor). The tree is recorded, stopped, re-verified, and killed by exact identity. The launcher is left alive.
- [Hard-pause](../appendix-a-glossary.md#hard-pause) is the same operation.
- `restart_with_message` does that, then records a replacement `agent_sessions` row, and activates a new one-use gate that the same accepted launcher awaits.
- A replacement incarnation needs no terminal provisioning.

A hard pause is journaled, so a crash in the middle of one cannot be misread.

- `agent_sessions` carries `pause_state: None | Stopping | Stopped | Killed`.
- `kkd` writes `Stopping` before it signals anything, `Stopped` once the whole recorded tree is stopped and re-verified, and `Killed` once every recorded identity is verified gone.
- Recovery after a `kkd` crash rolls a hard pause forward to the kill. It never resumes a harness that was being retired.

Before a replacement incarnation's gate is activated, kiki takes an inventory rooted at the `agent` launcher. The inventory must show no process other than the launcher itself in its descendant, session, and [process-group](https://en.wikipedia.org/wiki/Process_group) sets. A surviving tool child of the retired harness raises [`OrphanedProcess`](../appendix-a-glossary.md#orphanedprocess) with harness-remnant evidence. It blocks replacement, [materialization](../appendix-a-glossary.md#materialization), and deletion: the gate is not activated, nothing is written into the workspace, and nothing is deleted.

### The launcher outlives incarnations

The launcher outlives incarnations.

- A harness exit retires the incarnation without acknowledgement and makes `status` report `Crashed`. It does not end the `agent` role or change the thread's lifecycle.
- Only the launcher's own exit, or the loss of its binding or [server instance](../appendix-a-glossary.md#server-instance), ends the role.

A crashed harness under a live launcher is restarted by the `kk repair` plan [`restart-agent`](../appendix-a-glossary.md#restart-agent). This is the explicit restart path.

- It starts a replacement incarnation on the live launcher after the remnant check, with a fresh gate, and with `RestartStartup` if an intent is pending.
- It is same-thread and needs no approval in thread context.

Kiki's own protocol restarts are a cascade hard restart or a `RestartStartup` replacement. They are daemon-initiated steps of the delivery protocol, and they need no `HumanApproval` either. A requested interruption or close does need a one-shot approval. That is a `HumanApproval` or, when the activated [automation policy](../appendix-a-glossary.md#automation-policy) allows the plan, a [`PolicyApproval`](../appendix-a-glossary.md#policy-approval). See [Authority](../04-authority.md#policyapproval).

### Credential rotation

The thread credential (see [`ThreadScoped<T>` credential](../appendix-a-glossary.md#threadscoped-credential)) is rotated when an incarnation ends, and at reopen or terminal restart.

- Its file path is stable, and its contents are replaced atomically.
- The launcher re-reads it after `ReportHarnessExit`.
- `kk` and [`kk-hook`](../appendix-a-glossary.md#kk-hook) read it on every invocation.

The launcher's own calls do not depend on that credential staying the same. After `kkd` accepts a launcher's claim, it authenticates that launcher's calls by the accepted peer process identity `(pid, start_time)`. So rotating the thread credential when an incarnation ends does not close `SuperviseLauncher`, and it does not reject `ReportHarnessExit`.

### Agent status

[`AgentStatus`](../appendix-a-glossary.md#agentstatus) is `Running | Quiescent | Stuck(duration) | Crashed`. The cascade orchestrator uses `status` and `capabilities` to decide two things: whether soft-pause is viable, and whether pending reconciliation may materialize the managed workspace.

`AgentStatus` is derived only from these sources:

- the harness's own hooks and lifecycle events, mapped by the adapter's `status_inputs`;
- the pane launcher's exit report;
- `ProcessSupervisor`.

The terminal runtime never feeds it.

- [Herdr](../appendix-a-glossary.md#herdr)'s agent detection (`idle | working | blocked | done | unknown`) is a screen-and-process heuristic (an educated guess). It may be shown as a hint.
- None of these is evidence of `Quiescent`, of quiescence for soft-pause, of delivery, or of acknowledgement: Herdr's agent detection, `agent.wait`, or text accepted into a pane's input queue.
- The adapter never delivers a payload by sending terminal input.

## Agent display states

[`AgentStatus`](../appendix-a-glossary.md#agentstatus) is the orchestrator's vocabulary. The human-facing surfaces render a four-value projection of it. Those surfaces are `kk ls`, `kk log --wide`, and the TUI glyph table in [Interface](../10-interface/spec.md). The projection folds in two session signals the harness already emits:

| display state | source                                                                                                                                                                 |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `working`     | `Running`                                                                                                                                                              |
| `idle`        | `Quiescent`, most recent turn not completed (or no turn yet)                                                                                                           |
| `finished`    | `Quiescent`, most recent turn completed (the harness's turn-completion signal: Codex's `Stop` lifecycle event; for Claude Code, the proof named as an open gate below) |
| `blocked`     | `Crashed`, or an unacknowledged attention event such as a permission prompt, where `attention_events` is proved (see [Observability](../12-observability.md))          |

`Stuck(duration)` alone is not `blocked`. A silent agent keeps its `working` or `idle` state and is rendered dim. The silence threshold is a deferred `[notifications]` key.

### Without a quiescence proof

A harness version with `quiescence_detection: false` never reports `Quiescent`. For such a version:

- `kk ls` shows `working` whenever the harness is alive and not `blocked`.
- It never shows `idle` or `finished`.
- When a parent thread closes, an idle child's [boundary snapshot](../appendix-a-glossary.md#boundary-snapshot) uses the warned rule, the same as close preflight: the snapshot is taken with a warning, and a working agent shows up later as [approval drift](../appendix-a-glossary.md#approval-drift).

### The permission-prompt signal

A permission prompt can show `blocked` only when the adapter proves the `attention_events` capability.

- The capability names the exact harness event that says "the agent is waiting on a person", and a proof step shows that event fires for the pinned version.
- For a harness version without that proof, permission-prompt detection is v1.x. Crash detection still gives `blocked` for that version.

**Kiki never answers the prompt.** A permission prompt is the harness's own question to a person. It is not a kiki approval.

- No adapter method, hook answer, or terminal input from kiki answers one. The adapter never sends terminal input at all.
- [`kk-hook`](../appendix-a-glossary.md#kk-hook)'s non-blocking answer at the pre-tool boundary leaves the harness's own permission decision in place. Its blocking answer is about cascade delivery, not about permission.
- An automation policy approves kiki's own operations only. No rule and no `PolicyApproval` answers a harness prompt.

On a [headless](../appendix-a-glossary.md#headless) host, where no human is present, this looks as follows:

- The operator sets the harness's own permission settings ahead of time, so that the agent does not stop to ask. Those settings stay the harness's, and kiki writes none of them.
  - The settings must reach the managed process through a source that kiki's launch isolation leaves in place. See [Exclusive hook boundary and settings ownership](#exclusive-hook-boundary-and-settings-ownership).
  - For Claude Code, the isolation excludes other `PreToolUse` hooks. It does not exclude the harness's permission settings.
  - For Codex, the generated `CODEX_HOME` replaces the user layer. So permission settings in the user's real `~/.codex/` do not apply. The operator can set [Codex launch arguments](../11-configuration.md#sections) in the kiki user config. This works with an empty workspace. Prove on each supported version that the saved arguments take effect on create, reopen, and replacement, with exactly kiki’s hooks active. A conflicting or unsupported setting fails launch before the first prompt.
- If a prompt appears anyway, the agent waits. Where `attention_events` is proved, the `agent_blocked` event still fires, the thread shows `blocked`, and the event appears in [`kk events`](../09-commands.md#kk-events).
- A human can answer later. They connect over Secure Shell (SSH), run `kk attach`, and answer in the agent's pane.
- See [Observability](../12-observability.md).

### The open gate for Claude Code

Kiki installs no Claude Code stop hook unless that hook is promoted with specified, tested behavior. Until then, Claude Code's `finished` state and its `quiescence_detection` capability rest on an adapter/version proof that this chapter does not yet name. That proof is an open gate.

A Claude Code version without the proof:

- reports `quiescence_detection: false`;
- shows `working` whenever the harness is alive and not blocked, and never `idle` or `finished`;
- cannot use [agent quiescence](../appendix-a-glossary.md#agent-quiescence) as a cascade boundary.

Lifecycle preflights do not depend on it. `kk close` preflight proceeds for such a version and warns that a working agent will make the [approval drift](../appendix-a-glossary.md#approval-drift).

### Display only

The projection is display-only.

- The cascade orchestrator branches on `AgentStatus` and `Capabilities`, never on display states.
- Renderers project. They do not keep a state model of their own.

## Capabilities

[Capabilities](../appendix-a-glossary.md#capabilities) say what a harness can prove. They are a typed struct:

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
    attention_events: bool,
}
```

These fields describe behavioral proof, not a particular settings mechanism. Each one is true only when the adapter has proved the behavior for the pinned harness version.

- **`soft_pause`** is true when the harness can be held at a tool boundary without ending its process. The pre-tool hook can block a tool call, return kiki's payload to the model as that call's result, and let the model carry on in the same process.
- **`session_resume`** is true when a new process can continue an earlier harness conversation from its `harness_session_id`. A replacement incarnation then keeps the conversation. When it is false, every replacement starts a new conversation.
- **`mcp_client`** is true when the harness can connect to an [MCP](https://modelcontextprotocol.io/) server named in its launch-scoped configuration. Only the v1.x same-thread transcript tools need it. Nothing in the acceptance slice depends on it.
- **`quiescence_detection`** is true when the adapter can prove the agent is idle between turns (see [agent quiescence](../appendix-a-glossary.md#agent-quiescence)).
- **`attention_events`** is true when the adapter names a harness event that reports a permission prompt, and a proof step shows it fires. See [The permission-prompt signal](#the-permission-prompt-signal).

- **`exclusive_pre_tool_use`** may be satisfied by isolated launch settings (Claude Code), a launch-scoped harness home (Codex), or the ownership-tracked fallback. A managed v1 process cannot start when it is false.
- **`structured_tool_hooks`** is true only when one of these holds:
  - every tool that can observe or mutate workspace files is hook-gated in the pinned harness version; or
  - the launch-scoped configuration disables the tools that are not.

  A harness whose file-touching tools can bypass the pre-tool boundary has no safe soft barrier.

- **`parallel_batch_boundary`.** Without it, soft delivery is disabled.
  - Kiki may then fall back only when `restart_startup_delivery` is proved. That proof shows the tagged payload is the mandatory first input, the session-start hook reports its one-use id, and the first pre-tool hook call of a [model turn](../appendix-a-glossary.md#model-turn) in that incarnation acknowledges it.
  - Otherwise the harness ships managed sessions without cascade delivery, and its threads cannot follow.
- **`restart_startup_delivery`** is true when the harness passes the [`RestartStartup`](../appendix-a-glossary.md#restartstartup-delivery-proof) proof described under [Two session ids](#two-session-ids).
- **`enqueue_context`** is the `RunningAgent` method that hands a prepared payload to the delivery protocol. With `soft_pause` true, the payload waits on its intent and the pre-tool hook delivers it at the next tool boundary. For a harness without `soft_pause`, `enqueue_context` leaves the prepared payload on its intent. The `RestartStartup` fallback described above then delivers it.
- The daemon checks `capabilities` for every new incarnation. It does not assume a prior process's result remains valid.

### What `parallel_batch_boundary` requires

A [tool batch](../appendix-a-glossary.md#tool-batch) is the group of tool calls a model sends out together in one model turn (one model response). `parallel_batch_boundary` does not require that the harness dispatches tools in parallel. It requires that the batch boundary is unambiguous.

- **Claude Code** satisfies it with an explicit batch-completion signal over concurrently dispatched calls.
- **A serial dispatcher** satisfies it degenerately (as the simplest special case). This holds when the integration gate proves the pinned version never runs two tool calls of one model turn concurrently. Each batch then contains exactly one call and closes when that call resolves.

How resolution is proved is the adapter's obligation:

- An executed call resolves with its post-tool event.
- A denied call never executes and never produces a post-tool event.
- So completion must come from a harness-driven signal that survives the emitting hook's crash.
- Under the serial proof, that signal is the next turn-scoped hook event. It can only arrive after the blocked call resolved.

The proof is version-scoped. A version that begins dispatching concurrently without a provable completion boundary loses the capability and drops to `RestartStartup`.

## ContextMessage

A [`ContextMessage`](../appendix-a-glossary.md#contextmessage) is the message kiki delivers to a thread's agent during a cascade.

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

A hook is a command the harness runs at a set moment, such as just before a tool call ([Claude Code hooks](https://docs.claude.com/en/docs/claude-code/hooks)). [`kk-hook`](../appendix-a-glossary.md#kk-hook) is the pre-tool sidecar that fronts cascade delivery for both v1 harnesses. A sidecar is a small helper program that runs beside the main one.

- Claude Code invokes it through its `PreToolUse` hook.
- Codex invokes it through its lifecycle-hook system. Codex's `PreToolUse` event covers shell, `apply_patch`, and [MCP](https://modelcontextprotocol.io/) tool calls.
- `PreToolUse` and `PostToolBatch` name kiki's protocol entry points, not any harness's event vocabulary (see [PreToolUse / PostToolBatch hooks](../appendix-a-glossary.md#pretooluse-posttoolbatch-hooks)). Each adapter maps its own events onto them.
- A `PostToolBatch` report says only that the triggering tool batch has finished. It never acknowledges delivery.

The sidecar stays small for latency reasons:

- `kk-hook` is a stateless one-call client. Each run connects to `kkd`, makes one call, prints the answer, and exits. It keeps nothing between runs. There is no separate hook-side helper process.
- Fast-path round-trip target: <5ms typical, imperceptible to agents.
- The slow path (rebase plus payload compose) holds the tool batch for at most the [slow-path bound](../appendix-a-glossary.md#slow-path-bound), `[timeouts] slow_path` (default `30s`).

The hook has two separate time limits:

- **`[timeouts] hook_connect` (default `1s`)** covers only connecting to `kkd` and being admitted. If it expires, the hook checks the thread's [barrier marker](../appendix-a-glossary.md#barrier-marker). With the marker present it answers with the generic blocking deny. With the marker absent it returns the harness's non-blocking decision. See [Hook degradation](#hook-degradation).
- **`[timeouts] slow_path` (default `30s`)** applies once `kkd` has admitted the call into a reconciliation. The hook waits up to that long. If it expires, or the reconciliation's owner crashes, the answer is a generic blocking deny ("kiki is reconciling; try again"). It is never "continue".

Each adapter pins the harness-side hook timeout in its generated configuration above `slow_path` plus a margin. So the harness cannot time out a healthy hook in the middle of a reconciliation. Because the pin is written at launch, a changed `slow_path` reaches a running harness only with its next incarnation.

The hook's exact behavior lives in [Cascade](../05-cascade.md). That covers unresolved-intent lookup, boundary probe, batch barrier, decision step, and post-stdout `MarkDelivered`.

The adapter's obligations for soft delivery ([`SoftBatch`](../appendix-a-glossary.md#softbatch-delivery-proof)):

- The adapter must attach stable runtime-incarnation, model-turn, and tool-batch identities to soft-delivery calls.
- It durably fixes `Block` before reconciliation may mutate files.
- Concurrent `PreToolUse` calls in one batch all receive a blocking response when any member triggers reconciliation.
- Only a matching `PostToolBatch` can complete `SoftBatch`. Only a later [model turn](../appendix-a-glossary.md#model-turn) can acknowledge it.

`RestartStartup` works differently. The session-start hook reports the exact `startup_delivery_id`, and the first pre-tool hook call of a model turn in the replacement incarnation acknowledges it. It never fabricates a tool batch for startup input.

## Hook degradation

This section says what the hook does when it cannot reach `kkd`.

The hook degrades to pass-through when both of these hold:

- `kkd` is unreachable (socket missing, connection refused, daemon mid-restart); and
- no [cascade barrier](../appendix-a-glossary.md#delivery-barrier) is bound for the thread.

The hook is stateless and cannot read the database, so it learns the second fact from a file: the [barrier marker](../appendix-a-glossary.md#barrier-marker).

- When `kkd` binds a `Block` for a thread, it first writes the marker durably at `~/.config/kiki/repos/<repo_id>/barriers/<thread_id>`. It does this before it changes any workspace file.
- `kkd` removes the marker when the barrier lifts. After a crash, recovery removes it only after the reconciliation it guards is resolved.
- The hook learns the marker's absolute path the same way it learns the error-log path: `kkd` writes it into the per-thread harness config at thread-spawn time.
- The hook only checks whether the file exists. It never writes or removes it.

The limits are:

- `[timeouts] hook_connect` (default `1s`) covers connecting to `kkd` and being admitted. It covers nothing else.
- On expiry, the hook checks the marker.
  - **Marker present.** The hook answers with the generic blocking deny ("kiki is reconciling; try again"). The tool call does not run.
  - **Marker absent.** The hook returns the harness's non-blocking decision (Claude Code's `continue`, Codex's `allow`), so the agent's tool call is not blocked.
- Either way, the hook then appends one structured record to `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log`.

**A hook process that dies before answering.** The marker cannot cover a `kk-hook` process that is killed or crashes before it prints an answer. That case is covered by a proof for each pinned harness version: the harness must not run the tool as if the hook had allowed it. If the proof fails, that harness version is unsupported for cascade delivery.

Pass-through ends at admission. Once `kkd` has admitted a call into a reconciliation, the hook waits up to `[timeouts] slow_path`. If that expires, or the reconciliation's owner crashes, the hook answers with a generic blocking deny ("kiki is reconciling; try again"). It never answers "continue" for an admitted call.

### The admission cache

`kkd` caches the first admission decision for the lifetime of each batch, so every sibling hook call observes the same result. `kkd` owns that cache. It lives in `kkd`'s memory and is keyed by incarnation and batch. `kk-hook` holds no cache, and no other hook-side process exists.

- A cached [`PassThrough`](../appendix-a-glossary.md#batch-admission) defers intents discovered later in that batch.
- A `Block(intent_id)` decision is also durable on the intent, so it [fails closed](../appendix-a-glossary.md#fail-closed) (the call stays blocked) even after a restart. While `kkd` is down, the [barrier marker](../appendix-a-glossary.md#barrier-marker) keeps the call blocked.
- After a `kkd` restart the in-memory cache is gone. The rule is then: the first pre-tool call from an incarnation that was already running before this `kkd` start is an unknown in-flight batch. The one exception is a hook payload that proves the call is the first call of a new model turn.
- For an unknown in-flight batch, `kkd` can no longer prove that reconciliation is safe in that batch. `kkd`, not the hook, then does three things in order:
  1. It answers the unknown call with a block.
  2. It hard-pauses the old incarnation without mutating the workspace.
  3. It starts a replacement before reconsidering pending work.
- The blocked decision's durable `SoftBatch` proof remains embedded in `sync_intents`. It is authoritative after reconnect.
- If `kkd` cannot prove that a blocked batch completed, it blocks the call and takes `RestartStartup` recovery. It does not pass through a tool against newly materialized files.

### The error log

`~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log` is the catch-all for client-side errors that cannot reach `kkd`.

- It is created lazily, at first failure.
- The hook learns its absolute path at thread-spawn time. At that time `kkd` writes it into the per-thread harness config alongside the credential path.
- The source repo's filesystem is never touched.

### Why pass-through is safe

Pass-through is not a violation of the cascade safety invariant. It is the explicit precondition's failure mode.

- The cascade invariant in [Invariants](../02-invariants.md) requires `kkd` to be reachable for kiki to materialize a desired state at a [safe boundary](../appendix-a-glossary.md#safe-boundary).
- When the daemon is unreachable, jj repository state may already contain native descendant evolution. Even so, kiki leaves the workspace files untouched and preserves or reconstructs the pending intent.
- Pass-through happens only with the [barrier marker](../appendix-a-glossary.md#barrier-marker) absent. An absent marker means `kkd` has not started changing this thread's files for a reconciliation that is still unresolved.

Two cases:

- The watcher saw the trigger op before the outage. The [`sync_intent`](../appendix-a-glossary.md#sync-intent) and its normalized trigger rows are already in sqlite; they survive the daemon stop.
- The trigger op happened during the outage. The trigger lives in jj's [op log](https://docs.jj-vcs.dev/latest/operation-log/) (the upstream source of truth). On `kkd` restart, op-log catch-up replays missed ops, populates `op_history`, and runs before/after classification to create the same exact-base-transition intent as the live watcher.

Either way, the next successful PreToolUse round-trip after `kkd` returns selects the oldest unresolved intent and probes the workspace immediately (see [`WorkspaceProbe`](../appendix-a-glossary.md#workspaceprobe)).

- [`NativeRewrite`](../appendix-a-glossary.md#nativerewrite) needs no file update for `FreshClean | FreshDirty` and may update `StaleClean`.
- [`ParentAdvance`](../appendix-a-glossary.md#parentadvance) may mutate only from `FreshClean`.
- Any dirty or indeterminate state that requires mutation enters `RecoveryRequired` and hard-pauses for edit-preserving recovery.
- The successful path persists the result, synthetic payload, anchor, and `Materialized` state on the intent in one transaction.

Cascade delivery is deferred, not dropped, and outage edits are not silently hidden.

### The deferred window

In the deferred window, jj repository state may already contain evolved descendants while the workspace files remain stale.

- Before a barrier is activated, the agent's tool call may therefore run against the last materialized files until `kkd` returns.
- Once reconciliation begins and files may change, all calls in that batch are blocked instead.
- When `kkd` returns, it may observe a non-empty `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log` for a thread. If so, it surfaces a single notification per thread summarizing the gap.

## Exclusive hook boundary and settings ownership

A harness may run all matching hooks concurrently. So v1 never claims that `kk-hook` runs first, and it does not chain user pre-tool hooks. Instead, kiki requires that its hook is the only pre-tool hook.

- Every managed process incarnation starts only after the adapter proves that kiki is the sole matching pre-tool hook for that exact launch. This covers initial creation, reopen, explicit restart, crash recovery, and `RestartStartup` fallback.
- A settings [fingerprint](https://en.wikipedia.org/wiki/Cryptographic_hash_function) from an older incarnation is cache input, not proof for a new one.
- This restriction is session-scoped. It does not modify user-global configuration. It does not disable hooks in unmanaged sessions of either harness.
- If an adapter cannot prove exclusive pre-tool control, the attempted incarnation fails before the agent receives a prompt.

### Herdr's own integrations

Herdr ships its own agent integrations. They write hook entries into a harness's configuration directory.

- Kiki never runs Herdr's integration installer against launch-scoped settings, a generated `CODEX_HOME`, or a workspace settings file. The generated Herdr configuration never asks Herdr to.
- Current Herdr integrations for Claude Code and Codex install only a session-start reporter. Earlier versions installed pre-tool entries.
- The exclusive-hook proof therefore audits the effective settings of each launch for any Herdr hook entry, legacy or current. It treats a matching pre-tool entry as a failed proof, like any other foreign hook.
- Herdr's detection of managed agents works from process and screen observation without those hooks. Kiki does not depend on it.

The harness [launch specification](../appendix-a-glossary.md#launch-specification) removes every `HERDR_*` variable from the harness's [environment](https://en.wikipedia.org/wiki/Environment_variable).

- So the agent and its tools hold no Herdr socket address or pane identity.
- The pane keeps `KIKI_THREAD_ID`.
- Herdr's own hook scripts do nothing without those variables.
- Like the rest of the model, this is cooperative hygiene, not a security boundary. The harness still runs as the same user.

A harness version that provides exclusive hook control but no unambiguous batch boundary delivers cascades only when it also proves `restart_startup_delivery`.

### The session-start hook

Both generated harness configurations declare a session-start hook that runs `kk-hook`. It carries the [ready handshake](../appendix-a-glossary.md#ready-handshake) (`ReportHarnessReady`), so no thread can reach `Active` without it.

A proof step for each pinned harness version shows that the hook fires:

- exactly once per incarnation;
- before any tool runs;
- on a fresh start and on a resume.

If the proof fails for a harness version, that version is unsupported. There is no fallback for it.

### Claude Code

The preferred mechanism is a launch-scoped generated settings file under `~/.config/kiki/repos/<repo_id>/harness/<thread_id>/`. Kiki passes it with harness arguments that isolate the managed process from project, local-project, and user `PreToolUse` definitions.

- The generated file declares kiki's `PreToolUse`, its session-start hook, its batch-completion entry point where supported, and absolute credential/error-log paths.
- It pins the harness-side hook timeout above `[timeouts] slow_path` plus a margin.
- An adapter/version combination is accepted only after an integration test proves that no independently discovered user or project `PreToolUse` hook runs in that managed process.
- Unrelated hook events may remain enabled only when the same test proves two things: they cannot race workspace reconciliation, and they cannot reintroduce a matching `PreToolUse` hook.

If Claude Code cannot accept a fully isolated launch-scoped settings source, the fallback is a structural merge into `<workspace>/.claude/settings.local.json`.

1. Kiki records the prior bytes and content hash outside the workspace.
2. Kiki installs a uniquely identified fragment.
3. Kiki restores only when the current file still matches the kiki-owned post-merge hash.

Rules for the fallback:

- Concurrent human edits cause an ownership conflict and require explicit repair. Kiki never overwrites them.
- The fallback must also prove that inherited/global `PreToolUse` hooks are excluded. It is not enough that kiki's hook appears in the local file.

Kiki never writes, replaces, or deletes `<workspace>/.claude/settings.json`; it may be tracked project configuration.

### Codex

Codex resolves its configuration, hooks, trust store, sessions, and authentication from one root directory selected by `CODEX_HOME`.

- The adapter launches every managed incarnation with `CODEX_HOME` pointed at the same launch-scoped directory, `~/.config/kiki/repos/<repo_id>/harness/<thread_id>/`.
- Kiki generates that home per incarnation. It contains a `config.toml` ([TOML](https://toml.io/) is a configuration file format) that:
  - enables the lifecycle-hook feature;
  - declares kiki's `PreToolUse`, session-start (`SessionStart`), and turn-lifecycle hooks with absolute credential/error-log paths;
  - pins the harness-side hook timeout above `[timeouts] slow_path` plus a margin;
  - pre-trusts exactly those hooks in the generated trust store.
- The launch-scoped home _is_ the user layer for that process. So the user's real `~/.codex/` configuration and hooks are structurally excluded rather than merely overridden.

Two obligations follow from the relocation.

1. **Authentication.** `CODEX_HOME` also moves authentication. So the adapter must provision credentials into the generated home explicitly (a copied auth file or a configured API-key source) before the [launch gate](../appendix-a-glossary.md#launch-gate) opens. A launch that would fall back to the user's real home for auth is a failed isolation proof.
2. **Workspace-local configuration.** Workspace-local `.codex/` configuration can still be discovered from the working directory.
   - Codex's trust model leaves non-managed project hooks untrusted by default. The generated trust store grants nothing beyond kiki's own hooks.
   - But that exclusion is an integration-gate proof per pinned version, not an assumption.
   - A version fails the gate if a workspace `.codex/` hook, plugin hook, or managed-policy hook can run in the managed process without kiki's grant.

There is no workspace-merge fallback for Codex.

- Kiki never writes, replaces, or deletes anything under `<workspace>/.codex/`.
- If launch-scoped `CODEX_HOME` isolation is unavailable or its proof fails, the attempted incarnation fails before the agent receives a prompt.

## Codex boundary mapping

The Codex adapter maps Codex's events onto the model turns and tool batches used by kiki's delivery protocol. Each mapping below has its own proof requirements.

### Identifying model steps

Codex's hook events carry `session_id`, turn-scoped `turn_id`, and per-call `tool_use_id`.

- A Codex turn spans the whole agentic loop for one user input. Many sequential model steps share one `turn_id`.
- So `turn_id` is not the protocol's `model_turn_id`.
- What stands in for it is the model step. Proven-serial dispatch is what makes steps identifiable.

The serial-dispatch proof has two parts. The integration gate must prove that the pinned version:

1. never runs two tool calls of one turn concurrently; and
2. requests a new tool only after the model has consumed the previous call's result.

Once both are proved:

- each `tool_use_id` names a distinct model step;
- durable hook-arrival order is step order;
- the adapter uses `tool_use_id` as `tool_batch_id` (a batch of one);
- the adapter uses the recorded serial order as its model-turn identity, with `turn_id` monotonicity as a cross-check.

The proof is version-scoped and must cover subagent-originated tool calls. A version that dispatches concurrently, or whose subagents do, without an unambiguous boundary loses `parallel_batch_boundary` and runs with `RestartStartup` delivery only.

### Blocking a call and proving the batch completed

A blocked call is expressed through the hook's deny decision. The deny reason is returned to the model as the tool result.

- **Deny fidelity.** The integration gate must prove the saved payload reaches the model byte-identically through that channel. Lossy truncation or reformatting fails soft delivery.
- **No post-tool event.** Denial also means the tool never executes. So a blocked batch never produces a post-tool event.
- **Not the hook's own RPC.** The completion proof cannot be the emitting hook's own post-stdout [RPC](https://en.wikipedia.org/wiki/Remote_procedure_call) either. That best-effort call dies with the hook.

The harness itself supplies the crash-surviving report:

1. Under the serial-dispatch proof, the next turn-scoped hook event of the same incarnation can only arrive after the blocked call resolved. That event is a `PreToolUse` with a serially later `tool_use_id`, or the turn's `Stop`.
2. So that event's admission transaction durably records the blocked batch's `batch_completed_at`.
3. That arrival is the Codex adapter's `PostToolBatch` report. Like every `PostToolBatch`, it never acknowledges by itself.

`structured_tool_hooks` requires the same coverage proof as everywhere else. Either every workspace-observing tool in the pinned version fires `PreToolUse`, or the generated config disables the ones that do not.

### The delivery receipt

`MarkDelivered` remains the ordinary best-effort post-stdout RPC. For Codex it is never acknowledgement evidence.

- It proves the hook wrote the deny. It does not prove that the harness applied it.
- A hook may exceed the harness-side timeout, or the harness may reject its output. Such a hook writes stdout into a void, while the model receives a substituted result.

The authoritative consumption evidence is the **delivery receipt** (see [delivery receipt](../appendix-a-glossary.md#delivery-receipt)).

- Codex durably persists every tool call's result, a deny reason included, in its session record under the launch-scoped `CODEX_HOME`. It does so because resume must reconstruct exactly what the model saw.
- The completing arrival's transaction therefore acknowledges only when the session record's result for the blocked `tool_use_id` is the byte-identical saved payload.
- The receipt is also the runtime enforcement of the deny-fidelity gate proof.

What happens for each receipt outcome:

1. **A matching receipt.** The transaction acknowledges, as above.
2. **A contrary receipt.** The record shows a generic or substituted result. This means the model consumed something else and the tool did not run.
   - The prepared payload is rebound to the arriving batch and emitted byte-identically there, per the protocol's ordinary redelivery step.
   - That retry is bounded, and the bound is durable. The rebinding transaction counts the attempt on the intent itself. So a daemon restart cannot forget a contrary receipt and re-enter the retry.
3. **A second contrary receipt for the same intent.** This proves the deny channel itself is rejecting this payload on this version.
   - The intent fails over to `RestartStartup`.
   - `RestartStartup` delivery is the mandatory first input of a replacement process. It does not ride the hook output at all.
4. **A receipt not yet readable.**
   - When no further delivery is pending, acknowledgement is deferred to a later boundary.
   - Otherwise the intent [fails closed](../appendix-a-glossary.md#fail-closed) into `RestartStartup` within `[timeouts] slow_path`. This prefers a rare duplicate delivery over a wrong acknowledgement.

Delivery failure never loops silently past that ladder.

- Delivery retries are bounded by `[cascade] delivery_attempts` (default `3`). If `RestartStartup` attempts keep failing their handshake or their first-turn acknowledgement, kiki records exhaustion on the intent, in the same transaction that abandons the last attempt. It then:
  - leaves the intent unacknowledged;
  - keeps the agent hard-paused;
  - raises a loud [attention event](../appendix-a-glossary.md#attention-event) for the human.
- Restart recovery resumes that exhausted state and re-surfaces the blocked thread. It never mints a fresh attempt against it.
- The only exits are the two `kk repair` plans defined in [Cascade](../05-cascade.md#delivery-protocol):
  - a journaled retry that re-arms one fresh bounded cycle; or
  - a one-shot-approved discard that acknowledges without delivery proof.

### Supporting version proofs

Three supporting properties are version proofs at the gate:

1. A barrier-covered call never fails open into tool execution. `kk-hook` answers an admitted call with a generic blocking deny when `slow_path` expires or the reconciliation's owner crashes. The proof also covers a `kk-hook` process that dies before it writes an answer: the pinned version must not run the tool as if the hook had allowed it.
2. The generated config pins the harness-side hook timeout above `[timeouts] slow_path` plus a margin. So a healthy hook cannot be timed out mid-reconciliation.
3. The pinned version's session record durably contains each tool result as returned to the model, deny results included. So receipts exist to be read.

A payload delivered on a turn's final tool call stays `Delivered` until the next turn's first `PreToolUse`. `Stop` completes the batch but never acknowledges.

### Lifecycle events and the startup handshake

The `Stop` lifecycle event is the turn-completion signal behind the `finished` display state and quiescence detection.

`SessionStart` is Codex's session-start hook. It fires on fresh starts and on resumes, and it tells them apart. The adapter uses it for the ready handshake and, together with the mandatory tagged first input, for the `RestartStartup` acceptance handshake:

1. Kiki starts or resumes the harness session (`codex resume <harness_session_id>`) with the saved payload as the first input. The launch specification carries the one-use `startup_delivery_id` in the launcher environment.
2. The `SessionStart` hook reports that id with `ReportHarnessReady`.
3. The first pre-tool hook call of a [model turn](../appendix-a-glossary.md#model-turn) in that incarnation is the acknowledgement.

This is exactly what the protocol requires of every adapter.

## Per-thread harness selection

- Default per-repo via `agent.default_harness`.
- Override per-thread via `kk new <name> --harness <name>` and `--harness-arg "..."`.
- A thread cannot change harness mid-life; `kk thread restart <thread> --harness <new>` is the explicit path (terminates the current agent and respawns).
- v1:
  - The `Harness` trait is the architectural seam, and the `claude-code` and `codex` adapters ship.
  - `kk new --harness <other>` errors with `"unsupported harness in v1"`.
  - `kk new` (no `--harness`) defaults to `agent.default_harness` (initially `claude-code`).
  - If that harness's binary is missing, `kk new` errors at spawn time with `"<harness> not on PATH — install it or pass --harness <other>"`.
  - `kk init` does not pre-validate any harness binary; the architecture is BYO-harness (bring your own harness).

`kk thread restart --harness <new>` is not part of the acceptance slice unless promoted in [Orientation](../01-orientation.md). This chapter reserves the semantics so a future implementation does not mutate a thread's harness identity in place.

## Capture

Capture means reading what was said in a harness session into the [thread transcript](../appendix-a-glossary.md#thread-transcript). The capture-side abstraction is a separate trait, `TranscriptAdapter`:

```
trait TranscriptAdapter {
    fn discover(&self, session_id: SessionId) -> PathBuf;
    fn tail(&self, from_offset: u64) -> impl Iterator<Item = JsonlEntry>;
    fn project(&self, entry: &JsonlEntry) -> Option<(Author, Direction, String, DedupKey)>;
    fn position(&self) -> u64;
}
```

- Cascade-injection row writes are NOT part of this trait or the acceptance-slice `MarkDelivered` transaction.
- When transcript capture ships in v1.x, `kkd` projects the durable delivery event separately and [idempotently](https://en.wikipedia.org/wiki/Idempotence), independent of the harness. Projection failure cannot roll back delivery.
- Its first `TranscriptAdapter` implementations are:
  - `ClaudeCodeAdapter`, over Claude Code's session [JSONL](https://jsonlines.org/);
  - `CodexAdapter`, over Codex's rollout JSONL under the launch-scoped `CODEX_HOME`. This makes discovery deterministic rather than a search of the user's real session directory.
- Each writes a different projector and reuses the rest.

## Spawn lifecycle

`kk new` performs the durable creation [saga](../appendix-a-glossary.md#saga) defined in [Threads](../03-threads.md). A saga is a multi-step operation that kiki records step by step, so it can retry or undo.

- For the harness portion, credentials and exclusive settings must exist before the external process receives an initial prompt.
- No step below needs an attached Herdr client or a human. The harness runs in its pane whether or not anyone is viewing it.
- Reopen, explicit restart, and recovery reuse the same per-incarnation gate and ready proof, even though they have different lifecycle journals.

The creation order is:

1. Resolve name/prompt/follows/harness/pane options.
   - Initial prompt comes from `-m "<prompt>"` (winning if both are supplied) or stdin.
   - Absent both, the spawn proceeds without a first-turn prompt and the placeholder name is `unnamed-<short-hex>`.
2. Insert the `Creating` sqlite thread row and lifecycle journal; the stable `thread_id` attaches every later step.
3. `jj workspace add` at the exact selected base under `<workspaces_root>/<repo>-kiki-<slug>/`.
   - The command is pinned to the sampled operation head. It does not ignore the working copy, because it must write the new one.
   - It creates the [workspace](../appendix-a-glossary.md#workspace) and its initial working-copy commit in one command.
4. Read that workspace's exact `@` with a [pinned read](../appendix-a-glossary.md#pinned-read) and persist it as `thread_head_commit_id`.
5. Create the thread [bookmark](../appendix-a-glossary.md#bookmark) at that exact commit.
   - Persist the same commit as `checkpoint_commit_id` and as `bookmark_expected_commit_id`, and append the placement row to `thread_checkpoints`.
   - Kiki never assumes the bookmark followed a later `jj new`.
6. Write the `ThreadScoped<thread_id>` credential to `~/.config/kiki/repos/<repo_id>/credentials/<thread_id>` (mode `0600`).
7. Generate and validate the launch-scoped isolated settings: Claude Code's generated settings file or Codex's generated `CODEX_HOME`.
   - If Claude Code cannot accept isolated launch settings, perform the ownership-tracked `settings.local.json` merge and persist enough recovery data to restore it safely before continuing.
   - The Codex adapter has no workspace-merge fallback and fails the incarnation instead.
8. Run the [orphan](../appendix-a-glossary.md#orphan) scan for the thread, then provision its [terminal group](../appendix-a-glossary.md#terminal-group) through `TerminalRuntime`, following the journaled protocol in [Terminal runtime](terminal-runtime.md#provisioning).
   - First persist the `provision_id`, intended roles, exact workspace path, current `server_instance_id`, and the hash of the [provision nonce](../appendix-a-glossary.md#provision-nonce).
   - Then create the Herdr workspace and apply the role layout.
   - Every role pane's direct command is the pane launcher, started by argv with an explicit working directory and environment.
   - The argv carries only the `provision_id` and role. The nonce travels in the launch environment.
   - Nothing is typed into a shell, and no harness process starts in this step.
   - Herdr's create call first starts the user's login shell in the jj workspace, where it runs its rc files, before the layout replaces that tab. That shell is an ordinary pane member until it is gone.
   - The layout appends a new tab with new ids rather than reusing the old ones.
9. Each launcher reports its Herdr ids, then blocks on its gate.
   - `kkd` accepts a report only from a process whose parent is the current server instance and which a fresh per-pane process query shows to be the reported pane's root.
   - Each report is handled when it arrives, in one transaction per report. There is no table of pending reports. The transaction accepts that launcher for `(provision_id, role)` and records its OS-read process identity.
   - The [terminal binding](../appendix-a-glossary.md#terminal-binding) becomes `Bound` in the transaction that accepts the `agent` claim. `agent` is the only [required role](../appendix-a-glossary.md#required-role).
   - `kkd` waits up to `[timeouts] launcher_report` (default `10s`) for the reports. A `shell` or `ui` launcher that has not reported by then is recorded as absent and raises a warning. It does not fail provisioning. A missing `agent` report does.
   - Reports are idempotent. A repeat of an accepted report from the same peer process identity `(pid, start_time)` gets the same answer again.
   - A different process presenting for a consumed role is refused and must exit. That covers a duplicate launcher from a repeated create call, which exits without starting anything.
   - A group whose launchers are all refused removes itself, because Herdr drops a workspace when its last pane's command exits.
10. In a second transaction, which requires the `Bound` binding, record the process incarnation and activate its one-use launch gate while the thread remains `Creating`.
    - `kkd` resolves `SpawnOpts { thread_id, resume_harness_session_id: Option<HarnessSessionId>, initial_prompt: Option<String>, harness_args }` through `Harness::launch_spec` and delivers the result on the launcher's supervision stream.
    - The launcher creates the harness child held before exec, and reports its pid through `ReportHarnessStarted`. It releases the child only after `kkd` has verified and recorded the child's identity on `agent_sessions`.
    - A repeated `ReportHarnessStarted` for the same incarnation and child is a no-op. A launcher that already holds a recorded child ignores a re-delivered gate specification and reports the existing child.
    - The harness then runs in the pane's foreground.
    - The launcher does not replace itself. It stays alive across incarnations, because Herdr removes a pane when its direct command exits. It reports the harness's exit.
    - `kk-hook` sends the ready handshake from the harness's session-start hook event, with the incarnation id and the settings and hook fingerprints.
    - The transaction that commits the handshake re-reads the launcher's OS identity and the open `terminal_servers` row. Only that transaction completes the saga and enters `Active`.
    - The handshake must arrive within `[timeouts] ready_handshake` (default `60s`), counted from the launch. Expiry is `CreateFailed`. In a restart it is that restart's failure instead.
    - Any other launch or handshake failure also becomes `CreateFailed`.

### Journaling and idempotence

Every step is journaled.

- Steps 1–7 are [idempotent](https://en.wikipedia.org/wiki/Idempotence) (safe to repeat).
- Step 8 is not idempotent at the runtime, because a lost reply may have created a terminal group. So recovery reads a fresh snapshot and launcher reports before it issues any new call.
- The single accepted `agent` launcher per `(provision_id, role)` in step 9, and its one gate claim, guarantee that a duplicate group can never yield a duplicate harness.
- Failure before step 10 cannot expose a partially configured agent.
- Failure afterward leaves a recoverable creation state rather than claiming cross-system atomicity.

### Automatic compensation

Automatic compensation (kiki undoing its own steps) is limited. It may close the provisioned group and remove the new jj workspace only while all of these hold:

- the launch gate was never activated;
- `ProcessSupervisor` shows the group contains nothing but kiki's own blocked launchers;
- the workspace still equals its initial materialization.

Otherwise the saga stops in `CreateFailed` with its projections intact. Cleanup is then an approved repair plan that uses the close machinery: freeze, [loss inventory](../appendix-a-glossary.md#loss-inventory), final proof, termination, verified exit.

### What does not count as a step

A successful create or layout reply, a visible prompt, and Herdr reporting an agent in the pane are not steps in this sequence and complete none of them.
