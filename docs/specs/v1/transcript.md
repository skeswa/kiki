# Transcript spec

The thread transcript is a local recall surface for human-authored, agent-authored, and kiki-authored conversational text.

## Storage

Transcript rows live in `<repo>/.kiki/state.db`, which is gitignored.

The transcript is local-only in v1. It must not feed:

- `kk publish` PR drafting
- auto-describe
- auto-rename
- any externally visible artifact

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

## Reopen catch-up

`kk reopen` composes catch-up from recent rows where `synthesized=false`. This prevents recursive catch-up quoting.

The catch-up itself is captured as `synthesized=true`.

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

Agent MCP transcript reads are same-thread only when MCP ships.
