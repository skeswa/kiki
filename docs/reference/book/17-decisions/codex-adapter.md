# Codex as a second v1 harness

A [harness](../appendix-a-glossary.md#harness) is a coding-agent program that kiki starts and coordinates. This note records why [Codex](https://github.com/openai/codex) joined [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) as a v1 harness, and how kiki's delivery protocol maps onto it.

## Decision

v1 ships two harness adapters, `claude-code` and `codex`. Both sit behind the same `Harness`/`RunningAgent` [traits](https://doc.rust-lang.org/book/ch10-02-traits.html), the same [`Capabilities`](../appendix-a-glossary.md#capabilities) proofs, and the same cascade delivery protocol.

Earlier drafts deferred Codex entirely. The user-story tier for it was a degraded SIGINT+resume path. That rested on the assumption that Codex had no hook API that could enforce the required boundary. (A hook is a program the harness runs at a set moment, such as before each tool call.)

## Why the deferral was reversed

Codex's lifecycle-hook system changed after that deferral. It now has these parts:

- Its `PreToolUse` event covers shell, `apply_patch`, and [MCP](https://modelcontextprotocol.io/) tool calls.
- That event can deny a call with a reason returned to the model.
- It carries `session_id`, turn-scoped `turn_id`, and per-call `tool_use_id` identities.
- A `Stop` event reports turn completion.
- `SessionStart` distinguishes fresh starts from resumes.

The cascade boundary needs four ingredients:

- an exclusive pre-tool admission point over file-touching tools,
- a payload channel back to the model,
- turn identity for acknowledgement, and
- a resume path for [`RestartStartup`](../appendix-a-glossary.md#restartstartup-delivery-proof).

The new hooks provide a candidate for each requirement. The integration gate still has to prove that each one works.

Kiki's protocol already supports multiple harnesses. [`PreToolUse` and `PostToolBatch`](../appendix-a-glossary.md#pretooluse-posttoolbatch-hooks) are its entry points. [`SoftBatch`](../appendix-a-glossary.md#softbatch-delivery-proof) binds an [incarnation](../appendix-a-glossary.md#incarnation), [model turn](../appendix-a-glossary.md#model-turn), and [tool batch](../appendix-a-glossary.md#tool-batch); each adapter maps its harness's events to those terms. Deferring Codex removed one integration gate but did not simplify the protocol.

## The boundary mapping

Claude Code's hard case is the parallel tool batch. One assistant response causes several concurrent `PreToolUse` invocations, and none of them proves the model consumed another's synthetic result.

Codex dispatches the tool calls of a [model turn](../appendix-a-glossary.md#model-turn) serially (one at a time) and has no batch-completion event. Its adapter therefore needs a different way to identify a batch and its completion.

### One call is one batch

The `parallel_batch_boundary` capability requires an unambiguous batch boundary. Tool calls need not run in parallel.

The integration gate first proves two things about a pinned Codex version:

- it never runs two tool calls of one turn concurrently, subagent-originated calls included, and
- it requests a new tool only after the model consumed the previous call's result.

Once that is proved, each batch contains exactly one call. The concurrent-sibling steps of the delivery protocol are then vacuously satisfied: with no siblings, there is nothing for them to check.

The proof applies to one Codex version. If a version starts dispatching concurrently without a provable completion boundary, the next incarnation check removes the capability. That version runs with `RestartStartup` delivery only.

### Completion

The completion design went through three approaches. The first two failed because they could not provide evidence after a denied call or a hook crash.

1. The first approach used the single call's `PostToolUse` event. A denied call never executes and fires no post-tool event, so soft delivery would wait forever for completion evidence.
2. The second attempt was the emitting hook's own post-stdout confirmation. It fails the crash test. That [RPC](https://en.wikipedia.org/wiki/Remote_procedure_call) is the protocol's explicitly weaker best-effort evidence, and it dies with the hook.
3. The third approach uses the harness's next event, which can arrive even after a hook crash. Under the serial-dispatch proof, the next turn-scoped hook arrival cannot happen before the blocked call resolved. That arrival is a `PreToolUse` with a serially later `tool_use_id`, or the turn's `Stop`. So its admission [transaction](https://en.wikipedia.org/wiki/Database_transaction) records `batch_completed_at`. This is a crash-surviving, harness-driven `PostToolBatch` report, structurally parallel to Claude Code's.

### Consumption and the delivery receipt

Recording that a hook wrote a result does not prove the model received it.

Hook-side write evidence is `MarkDelivered`, or any durable mark the hook records around its own stdout. It proves the hook _emitted_ the deny, not that the harness _applied_ it. A hook may exceed the harness-side timeout, or the harness may reject its output. The harness then gives the model a substituted result. Acknowledging on write evidence would acknowledge a payload the model never saw.

The harness's session record provides the missing evidence. Codex durably persists every tool result in its session record, deny reasons included, because resume must reconstruct exactly what the model saw. That record is the **[delivery receipt](../appendix-a-glossary.md#delivery-receipt)**. Acknowledgement requires the blocked `tool_use_id`'s recorded result to be the byte-identical saved payload. That also makes the deny-fidelity gate proof runtime-enforced.

A contrary receipt (one that does not match) redelivers byte-identically on the arriving batch, but only once. A second contrary receipt is evidence that this version's deny channel rejects the payload. Repeated retries would keep using the same failed delivery path.

The second contrary receipt fails the intent over to `RestartStartup`. Its delivery is the replacement process's mandatory first input and does not touch the hook output. When the bounded restart attempts exhaust their handshake retries, the agent is [hard-paused](../appendix-a-glossary.md#hard-pause), an [attention event](../appendix-a-glossary.md#attention-event) is raised, and a human is required.

Attempts and exhaustion are durable intent state, written in the transactions that make them. An in-memory retry counter would reset on a [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) restart and allow retries beyond the bound.

A human can use `kk repair` to resolve an [exhausted intent](../appendix-a-glossary.md#exhausted-intent) in exactly two ways:

- a journaled re-arm that grants one fresh bounded cycle, or
- a one-shot-approved discard that acknowledges without delivery proof and says so before it is approved.

The re-arm boundary is a monotonic [delivery epoch](../appendix-a-glossary.md#delivery-epoch) stamped onto each attempt row, not a timestamp. (An epoch here is a counter that only goes up.) A wall-clock timestamp cannot reliably identify the fresh cycle under clock skew, rollback, or restart. The epoch id can.

An unreadable receipt defers acknowledgement when nothing is pending. It [fails closed](../appendix-a-glossary.md#fail-closed) into `RestartStartup` when a delivery is. The crash-safety invariant prefers a rare duplicate delivery over an acknowledgement by inference.

Three supporting properties are version proofs:

- the launcher answers for a dead sidecar under an active barrier with a generic blocking deny, so a barrier-covered call never fails open;
- the generated config pins the hook timeout above the slow path's bound; and
- the session record durably contains deny results, so receipts exist to be read.

Note added 2026-11-16: the first property is now worded differently. There is no separate "hook launcher" process. [`kk-hook`](../appendix-a-glossary.md#kk-hook) is a stateless one-call client, and `kkd` owns the cache of batch decisions. Once `kkd` has admitted a call into a reconciliation, a timeout or an owner crash is answered with a generic blocking deny, never with continue. The generated config pins the harness-side hook timeout above `[timeouts] slow_path` plus a margin. See [Harness adapter](../13-architecture/harness-adapter.md).

### Identity

Identity needed the same care. Codex's `turn_id` scopes the whole agentic loop for one user input, and many sequential model steps share it. So it cannot be the protocol's `model_turn_id`. Two consecutive tool calls with one `turn_id` are separated by a model step that consumed the first call's result. Keying acknowledgement on `turn_id` would postpone it until the next user prompt.

Under the serial-dispatch proof, each `tool_use_id` names a distinct model step, and durable hook-arrival order is step order. So a later `PreToolUse` with a distinct, serially later `tool_use_id` is the later-model-turn acknowledgement proof. The `Stop` event, like `PostToolBatch`, never acknowledges.

### Two proofs with no Claude analogue

Two further proofs have no Claude analogue and are therefore stated explicitly.

- **Deny-payload fidelity.** Codex returns a denied call's reason to the model as the tool result. That channel must carry the saved payload byte-identically.
- **Coverage.** `structured_tool_hooks` is true only when every [workspace](../appendix-a-glossary.md#workspace)-observing tool in the pinned version fires `PreToolUse` or is disabled by the generated configuration. A harness whose file-touching tools can bypass the boundary has no safe soft barrier.

## Isolation via `CODEX_HOME`, with no fallback

Claude Code needs two mechanisms to enforce hook exclusivity because its settings sources always layer:

- preferred launch-scoped settings, and
- an ownership-tracked merge into `<workspace>/.claude/settings.local.json` when isolation is unavailable.

Codex resolves configuration, hooks, trust, sessions, and authentication from one `CODEX_HOME` root. So the adapter gets a stronger primitive. It points `CODEX_HOME` at the generated per-thread directory, and the user's real `~/.codex/` is structurally excluded rather than overridden.

Kiki pre-trusts exactly its own hooks in the generated trust store. Codex's own trust model leaves non-managed workspace and plugin hooks untrusted by default. The gate proves that exclusion per version rather than assuming it.

Because the primitive is stronger, there is deliberately no workspace-merge fallback. Kiki never writes anything under `<workspace>/.codex/`. A failed isolation proof fails the incarnation before the agent receives a prompt.

Changing `CODEX_HOME` also changes where Codex looks for authentication. So provisioning credentials into the generated home is part of the [launch gate](../appendix-a-glossary.md#launch-gate). A launch that would fall back to the user's real home for authentication fails the isolation proof.

## What this does not change

The cascade invariants, the [`sync_intent`](../appendix-a-glossary.md#sync-intent) protocol authority, `RestartStartup` semantics, and the capability-driven degradation ladder are untouched. Codex slots into them.

Harnesses beyond these two remain deferred behind the same traits. The transcript projector for Codex rollout [JSONL](https://jsonlines.org/) ships with v1.x [transcript](../appendix-a-glossary.md#thread-transcript) capture, like its Claude counterpart.
