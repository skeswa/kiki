# Embedded cascade outbox design note

## Decision

The durable `sync_intent` row embeds the cascade outbox. Once reconciliation succeeds, the same transaction stores the result operation and workspace commit, byte-stable synthetic payload, transcript anchor, preparation timestamp, and `Materialized` state.

There is no separate `cascade_outbox` table, context queue, or family of progress counters. The ordered intent sequence and intent state are the protocol authority; status displays are queries over those rows.

## Delivery

The hook selects the oldest deliverable intent and emits its saved payload. Only after stdout succeeds does it call `MarkDelivered(agent_session_id, intent_id)`. That transaction:

1. changes `Materialized` to `Delivered`, or leaves an idempotently retried `Delivered` intent in that state,
2. sets `delivered_at` only if it was null,
3. records `delivered_intent_id` on the current runtime process incarnation, and
4. inserts the visible transcript row with `dedup_key=cascade:<intent_id>`.

The incarnation's next `PreToolUse` changes that intent to `Acknowledged` and clears `delivered_intent_id` atomically. PostToolUse is not involved. A restarted process always receives a new kiki incarnation id, even if the harness reuses its conversation id; restart retires the prior marker without acknowledging the intent.

If the hook crashes before `MarkDelivered`, the intent remains `Materialized`; if it crashes after the RPC but before the agent's next tool call, the intent remains `Delivered`. A replacement incarnation can re-emit either state's saved payload byte-identically. Duplicate delivery is acceptable; silent loss and payload drift are not.

## Why one row owns the protocol

A separate intent, counter set, queue, and outbox each described a different projection of the same cascade. Every crash and coalescing path then had to update those projections in lockstep. Embedding delivery in the intent removes invalid combinations by construction: an intent cannot claim materialization without the result and payload constraints, and acknowledgement names the exact delivered intent.

Coalescing may add trigger operation rows and advance the base transition only while an intent is pre-materialization. Once a payload is prepared, later work receives a new intent so a retry never changes the meaning of an already deliverable message.
