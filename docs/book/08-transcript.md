# Transcript

The thread transcript is a local recall surface for human-authored, agent-authored, and kiki-authored conversational text.

It is a memory aid for the human and, at local boundaries, for the same thread's resumed agent. Code truth remains in jj and the filesystem.

## Storage

Transcript rows live in `<repo>/.kiki/state.db`, which is gitignored.

The transcript is local-only in v1. It must not feed:

- `kk publish` PR drafting
- auto-describe
- auto-rename
- any externally visible artifact

This prohibition applies even when using the transcript would make the generated artifact better. The transcript contains dead ends, local reasoning, tool failures, and quoted material the user did not choose to publish.

## Row model

Each captured row records:

- `thread_id`
- optional `change_id`, `commit_id`, and `op_id`
- `session_id`
- monotonic per-thread `seq`
- `captured_at`
- `author`: `human`, `agent`, or `kk`
- `direction`: `inbound_to_agent`, `outbound_from_agent`, or `local_record`
- `text`
- `dedup_key`
- `synthesized`
- `anchor_unknown`

Kiki-authored cascade, reopen catch-up, and hard-escalation messages are `author=kk`, `direction=inbound_to_agent`, and `synthesized=true`.

## Full-text search and deduplication

`thread_messages` has an FTS5 virtual table over `text`; `kk thread transcript --search <query>` uses that index.

`dedup_key` is the idempotency key. Harness-projected rows use a harness-derived row id, such as Claude Code's JSONL `uuid`. Cascade-injection rows use `cascade:<applied_cascade_seq>` with no session component, because the same cascade payload may be re-delivered across sessions.

## Capture

The v1 capture adapter is Claude Code JSONL projection.

Captured:

- user text rows
- assistant text rows

Not captured in v1:

- token-streaming deltas
- structured tool calls
- structured tool outputs
- extended-thinking blocks

Backfill must anchor rows using per-workspace jj op history. If no reliable anchor exists, the row is inserted with `anchor_unknown=true`.

Backfill must not stamp old messages with whatever `@` happens to be current when kiki restarts. That would make later change-aligned queries misleading.

## Recovery and idempotency

Transcript capture may lag while `kkd` is down, but it must not silently miss or duplicate messages.

For each `(thread_id, session_id)`, kiki stores a `transcript_offsets` row containing `(byte_offset, last_row_uuid)`. On daemon restart, kiki resumes from that offset. If the JSONL file has rotated or is shorter than the stored offset, kiki reads from the top and relies on `INSERT OR IGNORE` over `dedup_key`.

`kk reopen` may reuse a harness session id or create a new one, depending on harness behavior. A reused session resumes from its stored offset. A fresh session starts with a new offset row; the thread transcript is the union of all session ids ordered by thread-local `seq`.

Cascade-injection rows are not projected from harness JSONL. They are written by the `MarkDelivered` handler after stdout delivery, using `dedup_key=cascade:<applied_cascade_seq>` and the anchor pinned in `cascade_outbox`. A retry must re-emit the outbox payload byte-identically. If `@` advances between outbox write and `MarkDelivered`, the transcript row still binds to the outbox anchor.

## Reopen catch-up

`kk reopen` composes catch-up from recent rows where `synthesized=false`. This prevents recursive catch-up quoting.

The catch-up itself is captured as `synthesized=true`.

Before invoking the harness with a kiki-prepended catch-up or hard-escalation message, `kkd` inserts a `pending_kkd_prepends` sidecar row keyed by `(thread_id, sha256(text))` with a short TTL. The JSONL projector uses that sidecar to mark the eventual harness-emitted user row as `author=kk`, `direction=inbound_to_agent`, and `synthesized=true`.

The sidecar match intentionally omits `session_id`, because a fresh-session reopen may not have a session id until after the harness starts. Duplicate `(thread_id, text_sha256)` rows are allowed and consumed FIFO so two byte-identical prepends in the TTL window produce two synthesized rows.

Catch-up source queries must exclude `synthesized=true` rows. This prevents reopen catch-ups from quoting older catch-ups, cascade messages, or hard-escalation framing back into themselves.

## Read API

Human CLI can read repo transcripts through `kk thread transcript`.

Expected query modes:

- by change
- `--search <query>`
- `--range <from>..<to>`
- `--recent <n>`
- `--include-unanchored`
- `--include-tombstoned`
- `--no-synthesized`

Agent MCP transcript reads are stretch/post-v1. When they ship, they are same-thread only.

## Privacy and retention

v1 performs no secret scrubbing. Local-only storage is the privacy posture. Redaction that is "usually right" is not enough for text that may contain prompts, quoted source, command output, or tool failures.

v1 has no transcript retention cap. SQLite is expected to handle the volume because token deltas and tool payloads are not captured.

`kk close` preserves transcript rows. `kk thread destroy` deletes them by default; `--keep-log` is the explicit retention opt-out.
