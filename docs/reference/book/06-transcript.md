# Transcript

The [thread transcript](appendix-a-glossary.md#thread-transcript) is a local, searchable record of conversational text written by the human, the agent, and kiki. (A [thread](appendix-a-glossary.md#thread) is kiki's unit of work.)

It is a memory aid for the human. After explicit [provider-egress consent](appendix-a-glossary.md#provider-egress-consent), permission to send text to the model provider, it also serves the same thread's resumed agent. Code truth stays in [jj](https://docs.jj-vcs.dev/latest/) (the Jujutsu version-control system) and the filesystem.

Transcript capture, transcript reads, and transcript-backed [reopen catch-up](appendix-a-glossary.md#catch-up) are [v1.x](appendix-a-glossary.md#v1-x-polish) work. They are not part of the [acceptance slice](appendix-a-glossary.md#acceptance-slice) (the minimal first release). The acceptance-slice cascade protocol does not depend on a transcript row being written. This chapter fixes the privacy and data-model boundary for when the feature ships.

## Storage

This section says where transcript rows are kept and what they must never be used for. In short: they stay in kiki's own local database, and they never feed anything that gets published.

Transcript rows live in `~/.config/kiki/repos/<repo_id>/state.db`, a [SQLite](https://www.sqlite.org/) database file. The source repo's filesystem holds no transcript state. kiki centralizes all per-repo runtime under `~/.config/kiki/`.

Transcript rows are stored locally and are never published (the [local-storage / no-publication rule](appendix-a-glossary.md#local-storage-no-publication-rule)). They must not feed:

- `kk publish` PR drafting
- [auto-describe](appendix-a-glossary.md#auto-describe)
- [auto-rename](appendix-a-glossary.md#auto-rename)
- any externally visible artifact

This prohibition holds even when the transcript would make the generated artifact better. The transcript contains dead ends, local reasoning, tool failures, and quoted material the user did not choose to publish.

Local storage is a storage promise, not an egress promise. (Egress means data leaving the machine.) Sending anything to a model provider is a separate, consented step. If the user explicitly requests [reopen catch-up](appendix-a-glossary.md#catch-up), kiki sends the selected catch-up text to the configured harness/model provider as agent input. [Reopen catch-up](#reopen-catch-up) defines the required consent boundary.

## Row model

Each piece of captured text is one database row. This section lists the fields every row records.

Each captured row records:

- `thread_id`
- optional `change_id`, `commit_id`, and `op_id`: jj anchors that tie the row to a point in repo history
- `session_id`
- monotonic per-thread `seq`: a counter that only increases
- `captured_at`
- `author`: `human`, `agent`, or `kk`
- `direction`: `inbound_to_agent`, `outbound_from_agent`, or `local_record`
- `text`
- `dedup_key`
- `synthesized`
- `anchor_unknown`

Some messages are written by kiki and sent to the agent: cascade messages, [reopen catch-up](appendix-a-glossary.md#catch-up) messages, and [hard-escalation](appendix-a-glossary.md#hard-escalation) messages. These kiki-authored messages carry `author=kk`, `direction=inbound_to_agent`, and `synthesized=true` (see [`synthesized=TRUE`](appendix-a-glossary.md#synthesized-true)).

## Full-text search and deduplication

This section covers two things: how transcript text is searched, and how kiki avoids storing the same row twice.

**Search.** `thread_messages` has an [FTS5](https://www.sqlite.org/fts5.html) virtual table (SQLite's full-text index) over `text`. `kk thread transcript --search <query>` uses that index.

**Deduplication.** `dedup_key` is the idempotency key: inserting the same row twice has no effect. ([Idempotent](https://en.wikipedia.org/wiki/Idempotence) means doing something twice has the same effect as doing it once.) The key is built in one of two ways:

- Harness-projected rows use a harness-derived row id, such as the `uuid` in a Claude Code [JSONL](https://jsonlines.org/) record. (A [harness](appendix-a-glossary.md#harness) is the agent program kiki runs.)
- Cascade-injection rows use `cascade:<intent_id>` with no session component, because the same intent payload may be re-delivered across sessions.

## Capture

Capture is how text gets from the agent program into the transcript. This section says which sources kiki reads, what it keeps, and how it ties old rows to repo history.

The first capture adapters (see [TranscriptAdapter](appendix-a-glossary.md#transcriptadapter)) project rows from harness log files:

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) session JSONL; and
- [Codex](https://github.com/openai/codex) rollout JSONL.

JSONL is a file format with one JSON record per line. A managed Codex thread's rollouts live under its launch-scoped `CODEX_HOME`, so discovery is deterministic: kiki always knows where to look.

Captured:

- user text rows
- assistant text rows

Not captured initially:

- token-streaming deltas
- structured tool calls
- structured tool outputs
- extended-thinking blocks

### Backfill

Backfill means importing rows written while kiki was not watching. Backfill must anchor rows using per-workspace jj op history (see the [operation-history cache](appendix-a-glossary.md#operation-history-cache)). If no reliable anchor exists, kiki inserts the row with `anchor_unknown=true` (see [`anchor_unknown=TRUE`](appendix-a-glossary.md#anchor-unknown-true)).

Backfill must not stamp old messages with whatever `@` (the current [working-copy](https://docs.jj-vcs.dev/latest/working-copy/) revision) happens to be when kiki restarts. That would make later change-aligned queries misleading.

## Recovery and idempotency

kiki's background process can stop and restart while the agent keeps writing. This section says how capture picks up where it stopped without losing or repeating a message.

Transcript capture may lag while [`kkd`](appendix-a-glossary.md#kkd) (the kiki daemon) is down, but it must not silently miss or duplicate messages.

**Offsets.** For each `(thread_id, session_id)`, kiki stores a `transcript_offsets` row containing `(byte_offset, last_row_uuid)`. This records how far into the log file kiki has read.

- On daemon restart, kiki resumes from that offset.
- If the JSONL file has rotated or is shorter than the stored offset, kiki reads from the top. It relies on `INSERT OR IGNORE` over `dedup_key` to skip rows it already has.

**Sessions.** `kk reopen` may reuse a harness session id or create a new one, depending on harness behavior.

- A reused session resumes from its stored offset.
- A fresh session starts a new offset row.
- The thread transcript is the union of all session ids, ordered by thread-local `seq`.

**Cascade rows.** Cascade-injection rows are not projected from harness JSONL.

- When transcript capture is enabled, the transcript projector records the durable `MarkDelivered` event. It uses `dedup_key=cascade:<intent_id>` plus the payload and anchor embedded in that [`sync_intent`](appendix-a-glossary.md#sync-intent).
- A retry must re-emit the saved payload byte-identically.
- If `@` advances between materialization and delivery, the row still binds to the saved anchor.
- Failure to project this optional row cannot fail or roll back cascade acknowledgement.

See [Cascade](05-cascade.md#delivery-protocol) for the delivery protocol these rows record.

## Reopen catch-up

Catch-up gives a reopened thread's agent some context from the earlier conversation. It is a message composed from recent transcript rows, and kiki sends it only when the human asks for it and agrees to send that text to the model provider.

### What catch-up is

- Plain `kk reopen` does not send transcript text to the agent.
- `kk reopen --catch-up` explicitly requests a catch-up composed from recent rows where `synthesized=false`. That filter prevents recursive catch-up quoting.

### When the preview is released

A closed thread has no live thread credential. `BeginApproval` therefore discloses that catch-up was requested but returns no transcript text. (`BeginApproval` is the call that starts a one-shot approval: a [human approval](appendix-a-glossary.md#human-approval), or a [`PolicyApproval`](appendix-a-glossary.md#policy-approval) when a rule in the activated [automation policy](appendix-a-glossary.md#automation-policy) allows the plan.)

The daemon releases the preview at one point only: after the exact reopen approval is claimed into its durable journal, and before the harness starts. It releases the preview:

- only to the same enrolled foreground presenter (see [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter)); and
- only as an authorized, reversible step.

If the human declines [provider egress](appendix-a-glossary.md#provider-egress), kiki drops the catch-up and continues as a plain reopen, unless the human cancels the whole operation. No transcript text reaches the harness first.

When consent comes from a remembered grant or from a policy rule (see [Consent with no person present](#consent-with-no-person-present)), there is no one to show a preview to. The daemon releases no preview, and the catch-up goes to the harness at the same point in the reopen.

### Asking for consent

Before the first provider-bound catch-up, kiki shows that selected local transcript text will be sent to the configured model provider, and asks for foreground consent. The user may:

- approve once;
- remember approval for that thread, provider, and purpose; or
- cancel.

A remembered preference is revocable, and a change in provider identity invalidates it. Remembering privacy consent suppresses that prompt only. It does not bypass the separate authority required to reopen a thread. The reopen still needs its own one-shot approval, from a person or from a policy rule that allows `reopen` (see [Commands](09-commands.md#kk-reopen)).

Kiki should offer a preview before consent. Kiki does not claim to scrub secrets or reliably redact the catch-up. Consent covers model-provider egress for reopen context only. It does not permit transcript use in publication, metadata generation, telemetry, or unrelated agent prompts.

### Consent with no person present

Kiki is [headless](appendix-a-glossary.md#headless): a reopen can run with no terminal and no person. The consent question has no flag that answers it. With no person, consent for a catch-up comes from two places only:

- a grant the person remembered earlier, for that thread, provider, and purpose; or
- a rule in the activated automation policy that names the operation `consent:catch_up` and lists the provider in `providers`.

The two approvals stay separate. A rule that allows `reopen` does not give consent, and a consent rule does not allow the reopen. A `*` in a rule's `operations` never matches a consent operation.

`kkd` checks for consent during the reopen preflight. Without a foreground terminal, and with neither a remembered grant nor a matching rule, `kk reopen --catch-up` fails closed with [exit code](09-commands.md#exit-codes) 3 before anything changes. `kk reopen` without `--catch-up` then reopens the thread cold.

### How the catch-up is recorded

The catch-up itself is captured as `synthesized=true`.

Before invoking the harness with a kiki-prepended catch-up or hard-escalation message, `kkd` inserts a [`pending_kkd_prepends`](appendix-a-glossary.md#pending-kkd-prepends) sidecar row. A sidecar row is a helper row kept beside the main data. The row is keyed by `(thread_id, sha256(text))` and has a short TTL ([time to live](https://en.wikipedia.org/wiki/Time_to_live): how long it stays valid). Here `sha256(text)` is a [hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function), a fingerprint of the text.

The JSONL projector, when installed, uses that sidecar to mark the eventual harness-emitted user row as `author=kk`, `direction=inbound_to_agent`, and `synthesized=true`.

The sidecar match intentionally omits `session_id`, because a fresh-session reopen may not have a session id until after the harness starts. Duplicate `(thread_id, text_sha256)` rows are allowed and consumed first-in, first-out. So two byte-identical prepends in the TTL window produce two synthesized rows.

Catch-up source queries must exclude `synthesized=true` rows. This prevents reopen catch-ups from quoting older catch-ups, cascade messages, or hard-escalation framing back into themselves.

## Read API

This section says who can read a transcript and through which door. The human reads through a command; an agent may later read its own thread's transcript, but only after the human has agreed to send that text to the provider.

**Human reads.** The v1.x human CLI reads transcripts through `kk thread transcript`. Query modes cover by-change reads, full-text search, change ranges, tail reads, and filtering by anchored, tombstoned, or synthesized rows. The flag surface lives in [Commands](09-commands.md#kk-thread-transcript).

**Agent reads.** Agent transcript reads over [MCP](https://modelcontextprotocol.io/) (the Model Context Protocol, the tool-call interface agents use) are v1.x polish. When they ship, they are same-thread only.

An MCP transcript result travels over local IPC ([inter-process communication](https://en.wikipedia.org/wiki/Inter-process_communication), programs on one machine talking to each other) on its first hop. But it normally becomes model-provider input when the harness returns tool output to a hosted model. Same-thread authority is therefore necessary but not sufficient.

- Before enabling transcript MCP for a managed harness, kiki requires remembered [provider-egress consent](appendix-a-glossary.md#provider-egress-consent) for purpose `transcript_mcp` and for that harness's current provider identity.
- MCP itself cannot open the foreground prompt or grant consent. Without a matching record it returns `ConsentRequired` and no transcript content.
- A person grants that purpose through the foreground privacy-consent CLI/TUI surface. Revoking it needs no approval: `kk privacy consent revoke` works with or without a terminal.
- With no person present, `kk privacy consent grant transcript-mcp` records the grant only when an activated policy rule names `consent:transcript_mcp` and lists that provider (see [Provider-egress consent](#provider-egress-consent)).

## Provider-egress consent

[Provider-egress consent](appendix-a-glossary.md#provider-egress-consent) is the recorded permission to send one thread's transcript text to one model provider for one purpose. A person gives it, or a policy rule the user activated for exactly that purpose and provider gives it. This section says what each record contains and how narrowly it applies.

Provider-egress consent is a privacy policy record. It is not a `HumanApproval` (see [human approval](appendix-a-glossary.md#human-approval)), not an ordinary `PolicyApproval`, and not configuration. Each durable record binds:

- `repo_id`;
- `thread_id`;
- normalized provider identity: harness, provider/service, endpoint origin, and a non-secret account or tenant fingerprint when available;
- purpose: `catch_up` or `transcript_mcp`;
- disclosure-policy version, grant time, and optional revocation time.

**Granting.** Before granting, the foreground presenter shows the provider identity, purpose, thread scope, and the absence of secret scrubbing.

- A remembered grant applies only to that exact tuple (that exact combination of values).
- A change in thread, provider, endpoint, account/tenant, purpose, or disclosure version [fails closed](appendix-a-glossary.md#fail-closed) and asks again. "Fails closed" means kiki refuses until it has a new answer.
- A one-time catch-up approval attaches only to that invocation. kiki does not insert it as a remembered grant.

**Granting by policy.** A machine with no person can still use a provider-backed feature, through one narrow path: a rule in the activated automation policy (see [Authority](04-authority.md#automation-policy) and [Configuration](11-configuration.md#automation-keys)).

- The rule must name the operation `consent:<purpose>`: `consent:catch_up` or `consent:transcript_mcp`.
- The rule must list the normalized provider identity in `providers`. A consent rule without `providers` is invalid, and there is no `*` for providers.
- A `*` in the rule's `operations` never matches a consent operation. A rule that approves everything else still gives no consent.
- The rule counts only after `kk automation apply` activates it. Writing it in the config file grants nothing.
- The rule stands in for the person's confirmation only. `kkd` still records the consent with the same tuple, and it writes an audit row with the rule name and the policy digest.
- A change in provider, endpoint, account/tenant, or disclosure version still fails closed, unless the rule also lists the new provider identity.
- Consent rules ship with the transcript features they gate, which are v1.x.

**Storage and revocation.** Consent records live in the registered repo's SQLite database. They are inspectable and revocable. Revocation takes effect before the next provider-bound read. It does not recall content already sent. Revoking a record does not change the policy: while a consent rule stays active, it can give the consent again. To stop that, remove the rule and run `kk automation apply`, or run `kk automation revoke`.

**What cannot create a grant.** A plain config key in any layer, [environment variables](https://en.wikipedia.org/wiki/Environment_variable), CLI flags, MCP calls, and an operational one-shot approval (a `HumanApproval` or a `PolicyApproval` for some other operation) cannot create a grant. Only two things can: a person at the foreground presenter, and an activated policy rule that names the purpose and the provider.

## Privacy and retention

This section states what kiki promises about transcript privacy and how long rows are kept.

Kiki performs no secret scrubbing. Three promises stay separate:

- rows are stored locally;
- rows are never used for publication; and
- [provider egress](appendix-a-glossary.md#provider-egress) requires explicit consent.

Redaction that is "usually right" is not enough for text that may contain prompts, quoted source, command output, or tool failures.

The initial transcript release has no retention cap. SQLite is expected to handle the volume because token deltas and tool payloads are not captured.

`kk close` preserves transcript rows. `kk thread destroy` deletes them by default; `--keep-log` is the explicit opt-out that keeps them.
