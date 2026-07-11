# Transcript

The thread transcript is a local recall surface for human-authored, agent-authored, and kiki-authored conversational text.

It is a memory aid for the human and, after explicit provider-egress consent, for the same thread's resumed agent. Code truth remains in jj and the filesystem.

Transcript capture, transcript reads, and transcript-backed reopen catch-up are v1.x work, not part of the acceptance slice. The acceptance-slice cascade protocol does not depend on a transcript row being written. This chapter fixes the privacy and data-model boundary for when the feature ships.

## Storage

Transcript rows live in `~/.kiki/repos/<repo_id>/state.db`. The source repo's filesystem holds no transcript state — kiki centralizes all per-repo runtime under `~/.kiki/`.

Transcript rows are stored locally. They must not feed:

- `kk publish` PR drafting
- auto-describe
- auto-rename
- any externally visible artifact

This prohibition applies even when using the transcript would make the generated artifact better. The transcript contains dead ends, local reasoning, tool failures, and quoted material the user did not choose to publish.

“Stored locally” does not mean “never leaves the machine.” If the user explicitly requests reopen catch-up, kiki sends the selected catch-up text to the configured harness/model provider as agent input. [Reopen catch-up](#reopen-catch-up) defines the required consent boundary.

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

`dedup_key` is the idempotency key. Harness-projected rows use a harness-derived row id, such as Claude Code's JSONL `uuid`. Cascade-injection rows use `cascade:<intent_id>` with no session component, because the same intent payload may be re-delivered across sessions.

## Capture

The first capture adapter is Claude Code JSONL projection.

Captured:

- user text rows
- assistant text rows

Not captured initially:

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

Cascade-injection rows are not projected from harness JSONL. When transcript capture is enabled, the transcript projector records the durable `MarkDelivered` event using `dedup_key=cascade:<intent_id>` and the payload and anchor embedded in that `sync_intent`. A retry must re-emit the saved payload byte-identically. If `@` advances between materialization and delivery, the row still binds to the saved anchor. Failure to project this optional row cannot fail or roll back cascade acknowledgement.

## Reopen catch-up

Plain `kk reopen` does not send transcript text to the agent. `kk reopen --catch-up` explicitly requests a catch-up composed from recent rows where `synthesized=false`; this prevents recursive catch-up quoting.

A closed thread has no live thread credential. `BeginApproval` therefore discloses that catch-up was requested but returns no transcript text. After the exact reopen approval is claimed into its durable journal, and before the harness starts, the daemon releases the preview only to the same enrolled foreground presenter as an authorized reversible step. Declining provider egress drops the catch-up and continues as a plain reopen unless the human cancels the whole operation; no transcript text reaches the harness first.

Before the first provider-bound catch-up, kiki shows that selected local transcript text will be sent to the configured model provider and asks for foreground consent. The user may approve once, remember approval for that provider and repo, or cancel. A remembered preference is revocable and changing provider identity invalidates it. Remembering privacy consent suppresses that prompt; it does not bypass the separate authority required to reopen a thread. Under the v1 authority contract, non-interactive reopen remains unavailable.

Kiki should offer a preview before consent. It does not claim to scrub secrets or reliably redact the catch-up. Consent covers model-provider egress for reopen context only; it does not permit transcript use in publication, metadata generation, telemetry, or unrelated agent prompts.

The catch-up itself is captured as `synthesized=true`.

Before invoking the harness with a kiki-prepended catch-up or hard-escalation message, `kkd` inserts a `pending_kkd_prepends` sidecar row keyed by `(thread_id, sha256(text))` with a short TTL. The JSONL projector, when installed, uses that sidecar to mark the eventual harness-emitted user row as `author=kk`, `direction=inbound_to_agent`, and `synthesized=true`.

The sidecar match intentionally omits `session_id`, because a fresh-session reopen may not have a session id until after the harness starts. Duplicate `(thread_id, text_sha256)` rows are allowed and consumed FIFO so two byte-identical prepends in the TTL window produce two synthesized rows.

Catch-up source queries must exclude `synthesized=true` rows. This prevents reopen catch-ups from quoting older catch-ups, cascade messages, or hard-escalation framing back into themselves.

## Read API

The v1.x human CLI reads transcripts through `kk thread transcript`. Query modes cover by-change reads, full-text search, change ranges, tail reads, and anchored/tombstoned/synthesized row filtering; the flag surface lives in [Commands](11-commands.md#kk-thread-transcript).

Agent MCP transcript reads are v1.x polish. When they ship, they are same-thread only.

An MCP transcript result is local IPC on its first hop but normally becomes model-provider input when the harness returns tool output to a hosted model. Same-thread authority therefore is necessary but not sufficient. Before enabling transcript MCP for a managed harness, kiki requires remembered provider-egress consent for purpose `transcript_mcp` and that harness's current provider identity. MCP itself cannot open the foreground prompt or grant consent: without a matching record it returns `ConsentRequired` and no transcript content. The human grants or revokes that purpose through the foreground privacy-consent CLI/TUI surface.

## Provider-egress consent

Provider-egress consent is a privacy policy record, not a `HumanApproval` and not configuration. Each durable record binds:

- `repo_id`;
- `thread_id`;
- normalized provider identity: harness, provider/service, endpoint origin, and a non-secret account or tenant fingerprint when available;
- purpose: `catch_up` or `transcript_mcp`;
- disclosure-policy version, grant time, and optional revocation time.

The foreground presenter shows the provider identity, purpose, thread scope, and absence of secret scrubbing before granting. A remembered grant applies only to that tuple. Thread, provider, endpoint, account/tenant, purpose, or disclosure-version change fails closed and asks again. A one-time catch-up approval is attached only to that invocation and is not inserted as a remembered grant.

Consent records live in the registered repo's SQLite database and are inspectable and revocable. Revocation takes effect before the next provider-bound read; it does not recall content already sent. Committed config, environment variables, CLI flags, MCP calls, and an operational `HumanApproval` cannot create a remembered grant.

## Privacy and retention

Kiki performs no secret scrubbing. Locally stored, never used for publication, and explicit provider-egress consent are separate promises. Redaction that is "usually right" is not enough for text that may contain prompts, quoted source, command output, or tool failures.

The initial transcript release has no retention cap. SQLite is expected to handle the volume because token deltas and tool payloads are not captured.

`kk close` preserves transcript rows. `kk thread destroy` deletes them by default; `--keep-log` is the explicit retention opt-out.
