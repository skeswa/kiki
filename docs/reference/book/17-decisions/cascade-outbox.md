# Embedded cascade outbox design note

A cascade is how kiki carries a parent [thread](../appendix-a-glossary.md#thread)'s changes into the threads that [follow](../appendix-a-glossary.md#follows) it. An outbox is a stored message that is waiting to be delivered. This note records where kiki keeps the message it delivers to an agent after a cascade, and how it proves the agent received it.

## Decision

The durable [`sync_intent`](../appendix-a-glossary.md#sync-intent) row embeds the cascade outbox. (A `sync_intent` is kiki's database record of one cascade reconciliation.) Once reconciliation succeeds, the same [transaction](https://en.wikipedia.org/wiki/Database_transaction) stores all of these:

- the result operation and [workspace](../appendix-a-glossary.md#workspace) commit,
- the byte-stable synthetic payload (the message, saved so its bytes stay the same),
- the transcript anchor,
- the preparation timestamp, and
- the `Materialized` state.

There is no separate `cascade_outbox` table, context queue, or family of progress counters. The ordered intent sequence and intent state are the protocol authority. Status displays are queries over those rows.

## Delivery proofs

Every delivered intent uses one of two explicit modes. The proof for each mode lives on the intent.

- [`SoftBatch`](../appendix-a-glossary.md#softbatch-delivery-proof) binds the current runtime [incarnation](../appendix-a-glossary.md#incarnation) (one launch of the agent process), [model turn](../appendix-a-glossary.md#model-turn), and [tool batch](../appendix-a-glossary.md#tool-batch).
  - [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) may invoke several [`PreToolUse`](../appendix-a-glossary.md#pretooluse) handlers concurrently for one assistant response. So the first admitted call durably fixes `Block(intent_id)` before reconciliation can mutate files or release the lock.
  - Every sibling call is blocked.
  - Once the payload is prepared, every sibling receives the saved bytes.
  - While reconciliation is incomplete, siblings wait or fail closed rather than pass through.
- [`RestartStartup`](../appendix-a-glossary.md#restartstartup-delivery-proof) binds a replacement incarnation and a kiki-minted, one-use `startup_delivery_id`.
  - The tagged payload is the replacement process's mandatory first [harness](../appendix-a-glossary.md#harness) input.
  - Its acceptance handshake marks delivery.
  - Only the first model turn that causally echoes that exact id may acknowledge it.
  - _Note, 2026-11-16:_ the echo requirement was later replaced. The session-start hook now reports the id with `ReportHarnessReady`, and `kkd` matches the first pre-tool hook call of a model turn in that incarnation by its incarnation id. See [Acknowledging a restart delivery](../05-cascade.md#acknowledging-a-restart-delivery).
  - Startup input does not invent a tool batch.

A sibling hook, new batch id, process start, or settings fingerprint is never acknowledgement evidence by itself.

Only after stdout succeeds does the hook call `MarkDelivered(intent_id, incarnation_id, model_turn_id, tool_batch_id)`. That transaction:

1. changes `Materialized` to `Delivered`, or leaves an idempotently retried `Delivered` intent in that state,
2. sets `delivered_at` only if it was null,
3. records `delivered_intent_id` on the current runtime process incarnation, and
4. preserves the intent-embedded [delivery barrier](../appendix-a-glossary.md#delivery-barrier).

When [transcript](../appendix-a-glossary.md#thread-transcript) capture is installed in v1.x, it projects this durable event [idempotently](https://en.wikipedia.org/wiki/Idempotence) with `dedup_key=cascade:<intent_id>`. Transcript insertion is not part of the acceptance-slice delivery transaction and cannot make acknowledgement fail.

### Completion and acknowledgement

`PostToolBatch` applies only to `SoftBatch`. It records only that the exact blocked batch completed. It does not acknowledge delivery.

A `PreToolUse` carrying a provably later `model_turn_id` may then change a `Delivered` intent to `Acknowledged` and clear the marker and proof atomically.

Historical rule superseded by [the current receipt requirement](../05-cascade.md#recovering-a-lost-delivery-mark) and [D-0013](https://github.com/skeswa/kiki/blob/main/journal/decisions/0013-prove-admission-and-delivery.md).

Suppose stdout reached the harness but `MarkDelivered` was lost. Then the exact completed batch plus that later turn may recover `Materialized → Acknowledged` in one transaction. That transaction records recovered delivery at the completion time before acknowledging. Without both pieces of evidence, `Materialized` is redelivered.

### Restart fallback

If the adapter cannot prove soft batch completion and later-turn identity, it retires the old incarnation without acknowledgement. It binds `RestartStartup` before launching the replacement.

A restarted process always receives a new kiki incarnation id and startup delivery id, even if the harness reuses its conversation id. A crash before the tagged-input acceptance handshake retires that attempt and retries. It never claims delivery.

### Crashes

- If a hook crashes before `MarkDelivered`, the intent remains `Materialized` with its `SoftBatch` proof.
- If it crashes after the [RPC](https://en.wikipedia.org/wiki/Remote_procedure_call) but before a later model turn, the intent remains `Delivered`.
- Unknown or incomplete blocked batches fail closed into `RestartStartup`.
- A replacement incarnation can re-emit either state's saved payload byte-identically.

Duplicate delivery is acceptable. Silent loss, same-batch acknowledgement, payload drift, and unproved startup delivery are not.

## Why one row owns the protocol

A separate intent, counter set, queue, and outbox each described a different projection (view) of the same cascade. Every crash and coalescing path then had to update those projections in lockstep.

Embedding delivery in the intent removes invalid combinations by construction. An intent cannot claim materialization without the result and payload constraints. Acknowledgement names the exact delivered intent.

Coalescing (merging several triggers into one intent) may add trigger operation rows and advance the [base transition](../appendix-a-glossary.md#base-transition) only while an intent is pre-materialization. Once a payload is prepared, later work receives a new intent. So a retry never changes the meaning of an already deliverable message.
