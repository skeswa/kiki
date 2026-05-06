# Cascade outbox design note

The cascade outbox exists to pin synthetic cascade payloads across crash and retry boundaries.

Without an outbox, a crash after composing a cascade message but before confirmed delivery can cause the retry to re-compose from newer state. If another cascade was enqueued in the meantime, the retry payload can differ from the payload that would have been delivered originally. That creates either silent loss or a phantom transcript row.

The v1 design avoids this by:

1. applying the protected rebase,
2. composing the synthetic payload,
3. storing the payload and anchor in `cascade_outbox`,
4. emitting the payload to the agent,
5. calling `MarkDelivered`,
6. writing the visible transcript row inside `MarkDelivered`.

Retries look up any row where `applied_cascade_seq > acknowledged_cascade_seq`, regardless of `delivered_at`, and re-emit it byte-identically.

The system prefers duplicate delivery over silent loss. Duplicate delivery can happen after crashes; the transcript remains idempotent through `dedup_key=cascade:<applied_cascade_seq>`.
