# State schema

kiki state lives in two SQLite databases. All tables are versioned via migrations. Recovery on daemon restart reads from sqlite; threads survive crashes and reboots.

## Database split

| Path                               | Scope    | Contents                                              |
| ---------------------------------- | -------- | ----------------------------------------------------- |
| `~/.kiki/state.db`                 | per-user | repo registry, daemon meta                            |
| `~/.kiki/repos/<repo_id>/state.db` | per-repo | threads, agent sessions, transcripts, cascades, audit |

Both databases live under `~/.kiki/` — kiki's centralized state directory. The source repo's own filesystem holds no kiki state; the per-repo `state.db` lives at `~/.kiki/repos/<repo_id>/state.db`, where `<repo_id>` is a UUID assigned at `kk init` and recorded in the per-user `repos` table. The user-level database knows which repos kkd watches; the per-repo database holds everything that lives or dies with the repo.

The `<repo_id>` UUID gives the centralized directory a stable, opaque name during one registration; it is **not** an identity that survives the source repo being moved out of band. With no breadcrumb inside the source repo, kiki's only handle on a registered repo is its `canonical_path`. If the user `mv`s the tree, `kk` invoked from the new location reports the repo as unregistered (because no `canonical_path` matches). The prior `<repo_id>` and its centralized state remain in `~/.kiki/repos/<old_repo_id>/` until `kk repo unregister` is run against the original path. The v1 recoveries are: move the source tree back so the registered `canonical_path` matches; or `kk repo unregister` followed by `kk init` at the new location, which starts a fresh registration with a new `repo_id`. By default, `kk repo unregister` removes both the registry row and the centralized state directory; `--keep-state` retains the directory on disk for manual inspection but offers no kiki-managed recovery — a subsequent `kk init` at the same canonical path mints a fresh `<repo_id>` with no link to the preserved bytes. See [Commands · Repo registry](../11-commands.md#repo-registry). A move-aware `kk repo relocate` command is not in v1.

## Tables

The list below is table-level. Column-level definitions are derived from the behavioral chapters.

### Per-user (`~/.kiki/state.db`)

- `repos` — `(repo_id, canonical_path, registered_at, opt_in_metadata)`. `repo_id` is a UUID assigned at `kk init` and keys the per-repo state directory at `~/.kiki/repos/<repo_id>/`. `canonical_path` is the realpath of the registered source repo at registration time and is the only handle kiki has for matching a future invocation back to this row. `repo_id` is stable for the life of the registration (so the centralized directory's name does not churn while kkd is running); it is **not** preserved across `kk repo unregister` + `kk init`, which is a fresh registration with a new UUID. An out-of-band `mv` of the source tree cannot be auto-detected — see the move semantics in the section above.
- `daemon_meta` — daemon startup info, last-known socket path, schema version.

### Per-repo (`~/.kiki/repos/<repo_id>/state.db`)

- `threads` — per-thread row carrying identity, bookmark/workspace references, and a `lifecycle` column with values `Active | ClosePreflight | CloseCommit | Closed | Orphaned | Destroyed` (see [Threads](../05-threads.md)). Cascade progress is not projected onto this row; it is derived from `sync_intents`.
- `thread_links` — directed follows edges, DAG-validated at insert time, including the exact last-synchronized parent commit and the child's owned-stack base needed to distinguish alignment from out-of-band topology divergence.
- `agent_sessions` — one row per runtime process incarnation carrying `(agent_session_id, harness_session_id, started_at, retired_at?, delivered_intent_id?)`. `agent_session_id` is a kiki UUID and changes on every process start even when `--resume` reuses `harness_session_id`. The nullable delivery pointer names the synthetic result emitted by this incarnation but not yet acknowledged by its subsequent boundary.
- `metadata_writes` — kk-ownership content-hash ledger for descriptions and bookmark names.
- `sync_intents` — the sole durable reconciliation and delivery authority. Each row carries `(intent_id, thread_id, seq, kind, from_base_commit_id, to_base_commit_id, classification_op_id, state, planned_op_id?, result_op_id?, result_workspace_commit_id?, payload?, anchor_change_id?, anchor_commit_id?, anchor_op_id?, prepared_at?, delivered_at?, acknowledged_at?, transcript_row_id?, recovery_reason?, recovery_bundle_path?, recovery_fingerprint?, recovery_details?)`, where kind is `NativeRewrite | ParentAdvance` and state is `Detected | Reconciling | Materialized | Delivered | Acknowledged | RecoveryRequired | TopologyDiverged | Superseded`. `UNIQUE (thread_id, seq)` orders intents; sequence allocation and insertion occur in one transaction. Recovery bundles live under `~/.kiki/repos/<repo_id>/recovery/<intent_id>/`, outside the source workspace. The saved payload and anchor are the embedded outbox. The runtime lock remains an in-memory `tokio::sync::Mutex` keyed by `thread_id`; restart recovery resumes from intent state and exact operation ids. See [Cascade](../07-cascade.md) and the [embedded-outbox design note](../20-decisions/cascade-outbox.md).
- `sync_intent_triggers` — normalized `(intent_id, op_id)` rows with `UNIQUE (intent_id, op_id)`. Coalescing adds observed operation ids here and updates `classification_op_id` to the exact view used for reclassification only while the intent remains pre-materialization; it does not impose a false linear “through” order on jj's operation DAG.
- `op_attribution` — kk-initiated op-id dedupe so the watcher does not react to its own ops.
- `op_history` — per-(repo, op_id, workspace_id) cache of `(committed_at, change_id, commit_id, parent_op_id)` with `UNIQUE (repo_id, op_id, workspace_id)`. Per-workspace key is load-bearing because `@` is workspace-local.
- `pr_links` — thread → PR.
- `thread_config` — per-thread config layer key/value/updated_at.
- `credentials` — `(cred_id, kind: 'Admin' | 'ThreadScoped', thread_id?, issued_at, revoked_at?)`.
- `audit_log` — append-only `(timestamp, cred_id, declared_scope, method, args_summary, outcome)`.
- `thread_messages` — per-thread transcript rows. `(thread_id, change_id?, commit_id?, op_id?, session_id, seq, captured_at, author, direction, text, dedup_key, synthesized, anchor_unknown)` with `UNIQUE (thread_id, dedup_key)` and an FTS5 virtual table over `text`. CHECK constraint binding `anchor_unknown` to nullability of the `(change_id, commit_id, op_id)` triple. See [Transcript](../08-transcript.md).
- `thread_changes` — per-(thread, change_id) row carrying `tombstoned_at?` (abandon) and `redirected_to?` (squash).
- `transcript_offsets` — per-(thread, session_id) `(byte_offset, last_row_uuid)` for crash-safe tail resumption. Both fields advance in the same transaction as the corresponding `thread_messages` insert.
- `pending_kkd_prepends` — TTL-bounded `(prepend_id PRIMARY KEY, thread_id, text_sha256, inserted_at)`. Duplicate `(thread_id, text_sha256)` rows are allowed and consumed FIFO. Match key omits `session_id` so fresh-session reopens match correctly.

### v2-only

- `causal_chains`, `causal_chain_visits` — deferred until the broader MCP substrate ships. See [Roadmap](../18-roadmap.md).

## CHECK constraints worth calling out

- `thread_messages`: `(anchor_unknown=FALSE AND change_id IS NOT NULL AND commit_id IS NOT NULL AND op_id IS NOT NULL) OR (anchor_unknown=TRUE AND change_id IS NULL AND commit_id IS NULL AND op_id IS NULL)`. The two states cannot drift apart.
- `sync_intents`: both exact base commits are required. `Materialized`, `Delivered`, and `Acknowledged` require a result workspace commit, byte-stable payload, complete anchor triple, and `prepared_at`. `Delivered` additionally requires `delivered_at`; `Acknowledged` requires both delivery and acknowledgement timestamps. `RecoveryRequired` requires `recovery_reason`, `recovery_bundle_path`, and `recovery_fingerprint`. Normal transitions move forward through `Detected → Reconciling → Materialized → Delivered → Acknowledged`. `RecoveryRequired` may return to `Reconciling` only with recorded recovery details or a human choice; `TopologyDiverged` may return only after a recorded human resolution. Only a pre-materialization intent may become `Superseded`.
- `agent_sessions`: `delivered_intent_id`, when non-null, must reference a `Delivered` intent for the same thread. A partial unique index allows at most one non-retired incarnation to claim an intent. Starting a replacement process retires the old incarnation and clears its pointer without acknowledgement; the new incarnation must receive the saved payload before it can claim or acknowledge the intent. The acknowledgement transaction advances the intent and clears the current pointer together.

## Migrations

Every schema change ships as a migration. Migrations are forward-only. Once a release is cut, schema changes must preserve upgrade compatibility. The migration runner is part of `kiki-core`.
