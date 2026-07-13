# Embedded cascade outbox design note

## Decision

The durable `sync_intent` row embeds the cascade outbox. Once reconciliation succeeds, the same transaction stores the result operation and workspace commit, byte-stable synthetic payload, transcript anchor, preparation timestamp, and `Materialized` state.

There is no separate `cascade_outbox` table, context queue, or family of progress counters. The ordered intent sequence and intent state are the protocol authority; status displays are queries over those rows.

## Delivery proofs

Every delivered intent uses one of two explicit modes whose proof lives on the intent:

- `SoftBatch` binds the current runtime incarnation, model turn, and tool batch. Claude Code may invoke several `PreToolUse` handlers concurrently for one assistant response, so the first admitted call durably fixes `Block(intent_id)` before reconciliation can mutate files or release the lock. Every sibling call is blocked. Once the payload is prepared, every sibling receives the saved bytes; while reconciliation is incomplete, siblings wait or fail closed rather than pass through.
- `RestartStartup` binds a replacement incarnation and a kiki-minted, one-use `startup_delivery_id`. The tagged payload is the replacement process's mandatory first harness input. Its acceptance handshake marks delivery, and only the first model turn that causally echoes that exact id may acknowledge it. Startup input does not invent a tool batch.

A sibling hook, new batch id, process start, or settings fingerprint is never acknowledgement evidence by itself.

Only after stdout succeeds does the hook call `MarkDelivered(intent_id, incarnation_id, model_turn_id, tool_batch_id)`. That transaction:

1. changes `Materialized` to `Delivered`, or leaves an idempotently retried `Delivered` intent in that state,
2. sets `delivered_at` only if it was null,
3. records `delivered_intent_id` on the current runtime process incarnation, and
4. preserves the intent-embedded delivery barrier.

When transcript capture is installed in v1.x, it projects this durable event idempotently with `dedup_key=cascade:<intent_id>`. Transcript insertion is not part of the acceptance-slice delivery transaction and cannot make acknowledgement fail.

`PostToolBatch` applies only to `SoftBatch` and records only that the exact blocked batch completed; it does not acknowledge delivery. A `PreToolUse` carrying a provably later `model_turn_id` may then change a `Delivered` intent to `Acknowledged` and clear the marker and proof atomically. If stdout reached the harness but `MarkDelivered` was lost, the exact completed batch plus that later turn may recover `Materialized → Acknowledged` in one transaction: it records recovered delivery at the completion time before acknowledging. Without both pieces of evidence, `Materialized` is redelivered.

If the adapter cannot prove soft batch completion and later-turn identity, it retires the old incarnation without acknowledgement and binds `RestartStartup` before launching the replacement. A restarted process always receives a new kiki incarnation id and startup delivery id, even if the harness reuses its conversation id. A crash before the tagged-input acceptance handshake retires that attempt and retries; it never claims delivery.

If a hook crashes before `MarkDelivered`, the intent remains `Materialized` with its `SoftBatch` proof; if it crashes after the RPC but before a later model turn, the intent remains `Delivered`. Unknown or incomplete blocked batches fail closed into `RestartStartup`. A replacement incarnation can re-emit either state's saved payload byte-identically. Duplicate delivery is acceptable; silent loss, same-batch acknowledgement, payload drift, and unproved startup delivery are not.

## Why one row owns the protocol

A separate intent, counter set, queue, and outbox each described a different projection of the same cascade. Every crash and coalescing path then had to update those projections in lockstep. Embedding delivery in the intent removes invalid combinations by construction: an intent cannot claim materialization without the result and payload constraints, and acknowledgement names the exact delivered intent.

Coalescing may add trigger operation rows and advance the base transition only while an intent is pre-materialization. Once a payload is prepared, later work receives a new intent so a retry never changes the meaning of an already deliverable message.
