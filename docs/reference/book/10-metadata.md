# Metadata Evolution

kiki may eventually help keep thread names, bookmark names, and revision descriptions current as work changes. The foundation ships in v1 even if the background AI loop does not: kiki must know which prose it owns and which prose belongs to the human.

## Ownership ledger

Ownership is tracked in sqlite, not inferred from vibes and not dependent on jj trailers.

For every kiki-authored revision description or bookmark name, kiki records a content hash in `metadata_writes`. On the next read:

- if the current content still matches the stored hash, kiki may update it;
- if the current content differs, the artifact becomes human-owned;
- once human-owned, kiki does not rewrite it unless the user explicitly opts back in.

This conservative rule applies to human edits and agent-authored edits. From kiki's point of view, anything outside the ledger is user territory.

## Revision descriptions

Auto-describe, when enabled, may run after:

- thread creation;
- an agent quiescence window, defaulting to 30 seconds with no agent tool calls;
- `jj split`;
- `jj squash`;
- explicit `kk thread describe --refresh`.

Each job is stamped with an input hash. If the diff, ancestry, bookmark name, or relevant metadata changes while the model is running, the result is discarded and a fresh job is queued from current state.

The auto-describe prompt may use:

- the revision diff;
- ancestor descriptions;
- the current bookmark name;
- kiki-owned metadata state.

It must not read the thread transcript.

## Bookmark names

Auto-rename, when enabled, may propose bookmark slugs for kiki-owned thread bookmarks. The prompt includes sibling bookmark names so the model can choose a distinct slug.

An external `jj bookmark rename` marks the bookmark human-owned for the rest of the thread's life. kiki does not rename it again unless an explicit future command opts it back in.

## Squash and merge ownership

When `jj squash` combines a kiki-owned description with non-kiki content, the resulting description becomes human-owned. Ownership defaults toward preservation.

This rule is intentionally simple. If kiki cannot prove the resulting prose is still its own, it steps aside.

## Trailers

`[autorename] trailer = true` may add an opt-in `Kk-Auto: true` trailer for transparency. The trailer is audit decoration only. Ownership is still determined by the sqlite content-hash ledger.

## Race control

Metadata writes require a per-thread advisory lock. Auto-describe and auto-rename wait for snapshot quiescence: no in-flight agent tool call touching files and no in-progress jj operation.

If the lock cannot be acquired within 5 seconds, the attempt is abandoned and re-queued. kiki may spend a model call and still discard the result; that is preferable to writing stale prose.

## Configuration

`[autorename]` controls the feature:

- `enabled`: `true | false`
- `cadence`: `idle-only | events | always | off`
- `idle_ms`: quiescence delay before firing
- `trailer`: whether to write the transparency trailer (default `false`; opt-in)
- event toggles for creation, split, squash, and manual refresh

Cost management remains outside v1. kiki does not cap model spend, concurrent agents, CPU, RAM, or token usage.

## Provider

Auto-describe and auto-rename go through a provider-agnostic `AICompose` seam. `[ai]` selects the backend:

- `provider`: `anthropic | openai | local-ollama | ...`
- `model`: provider-specific model identifier (defaults to a Haiku-class model for Anthropic).
- `api_key_env`: env var holding the API key (default `ANTHROPIC_API_KEY` for Anthropic).
- `api_key_path`: file path holding the API key (alternative to `api_key_env`).

v1 ships only the Anthropic implementation. The trait surface is generic so additional providers can be added without touching the metadata ledger or the prompt-assembly logic.

The auto-AI loop is opt-in. `[autorename] enabled = false` is the default, so a fresh install never calls a provider until the user configures one.
