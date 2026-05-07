# State schema

kiki state lives in two SQLite databases. All tables are versioned via migrations. Recovery on daemon restart reads from sqlite; threads survive crashes and reboots.

## Database split

| Path                    | Scope                 | Contents                                              |
| ----------------------- | --------------------- | ----------------------------------------------------- |
| `~/.kiki/state.db`      | per-user              | repo registry, daemon meta                            |
| `<repo>/.kiki/state.db` | per-repo (gitignored) | threads, agent sessions, transcripts, cascades, audit |

`<repo>/.kiki/` is gitignored. The user-level database knows which repos kkd watches; the per-repo database holds everything that lives or dies with the repo.

## Tables

The list below is table-level. Column-level definitions are derived from the behavioral chapters.

### Per-user (`~/.kiki/state.db`)

- `repos` — registered repo paths, registration time, opt-in metadata.
- `daemon_meta` — daemon startup info, last-known socket path, schema version.

### Per-repo (`<repo>/.kiki/state.db`)

- `threads` — per-thread row carrying `pending_cascade_seq`, `applied_cascade_seq`, `acknowledged_cascade_seq`.
- `thread_links` — directed follows edges. DAG-validated at insert time.
- `agent_sessions` — per-session row carrying `delivered_in_flight_seq` and harness `session_id`.
- `context_queue` — cascade messages with monotonic seq numbers per thread; drained at the next PreToolUse after delivery.
- `cascade_outbox` — per-(thread, applied_cascade_seq) row carrying `(payload, anchor_change_id, anchor_commit_id, anchor_op_id, prepared_at, delivered_at NULL, transcript_row_id NULL)` with `UNIQUE (thread_id, applied_cascade_seq)`. Pins synthetic payload + anchor at compose time. See [cascade outbox](../../appendix/decisions/cascade-outbox.md).
- `metadata_writes` — kk-ownership content-hash ledger for descriptions and bookmark names.
- `cascades` — in-flight rebase coordination including the per-thread cascade lock.
- `op_attribution` — kk-initiated op-id dedupe so the watcher does not react to its own ops.
- `op_history` — per-(repo, op_id, workspace_id) cache of `(committed_at, change_id, commit_id, parent_op_id)` with `UNIQUE (repo_id, op_id, workspace_id)`. Per-workspace key is load-bearing because `@` is workspace-local.
- `pr_links` — thread → PR.
- `thread_config` — per-thread config layer key/value/updated_at.
- `credentials` — `(cred_id, kind: 'Admin' | 'ThreadScoped', thread_id?, issued_at, revoked_at?)`.
- `audit_log` — append-only `(timestamp, cred_id, declared_scope, method, args_summary, outcome)`.
- `thread_messages` — per-thread transcript rows. `(thread_id, change_id?, commit_id?, op_id?, session_id, seq, captured_at, author, direction, text, dedup_key, synthesized, anchor_unknown)` with `UNIQUE (thread_id, dedup_key)` and an FTS5 virtual table over `text`. CHECK constraint binding `anchor_unknown` to nullability of the `(change_id, commit_id, op_id)` triple. See [Transcript](../07-transcript.md).
- `thread_changes` — per-(thread, change_id) row carrying `tombstoned_at?` (abandon) and `redirected_to?` (squash).
- `transcript_offsets` — per-(thread, session_id) `(byte_offset, last_row_uuid)` for crash-safe tail resumption. Both fields advance in the same transaction as the corresponding `thread_messages` insert.
- `pending_kkd_prepends` — TTL-bounded `(prepend_id PRIMARY KEY, thread_id, text_sha256, inserted_at)`. Duplicate `(thread_id, text_sha256)` rows are allowed and consumed FIFO. Match key omits `session_id` so fresh-session reopens match correctly.

### v2-only

- `causal_chains`, `causal_chain_visits` — deferred until the broader MCP substrate ships. See [Roadmap](../17-roadmap.md).

## CHECK constraints worth calling out

- `thread_messages`: `(anchor_unknown=FALSE AND change_id IS NOT NULL AND commit_id IS NOT NULL AND op_id IS NOT NULL) OR (anchor_unknown=TRUE AND change_id IS NULL AND commit_id IS NULL AND op_id IS NULL)`. The two states cannot drift apart.
- `cascade_outbox`: `delivered_at IS NULL` distinguishes outstanding deliveries from completed ones; lookup uses `applied_cascade_seq > acknowledged_cascade_seq` and ignores `delivered_at`.

## Migrations

Every schema change ships as a migration. Migrations are forward-only. Once a release is cut, schema changes must preserve upgrade compatibility. The migration runner is part of `kiki-core`.
