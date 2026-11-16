# Metadata Evolution

kiki may eventually help keep thread names, checkpoint bookmark names, and revision descriptions — jj's commit messages — current as work changes. Both the ownership foundation and the execution loop are v1.x work. The acceptance slice writes no AI-authored metadata, so it does not need to carry a ledger before that behavior exists. When the feature ships, kiki must know which prose it owns and which belongs to the human.

## Ownership ledger

kiki tracks ownership in sqlite. It does not infer ownership by guessing from content, and it does not depend on jj trailers.

The ledger works like a sign-out sheet: kiki may only edit prose it can prove it wrote last. For every kiki-authored revision description or bookmark name, kiki records a content hash — a fingerprint of the text — in `metadata_writes`. On the next read:

- if the current content still matches the stored hash, kiki may update it;
- if the current content differs, the artifact becomes human-owned;
- once human-owned, kiki does not rewrite it unless the user explicitly opts back in.

This conservative rule applies to human edits and to agent-authored edits alike. From kiki's point of view, anything outside the ledger is user territory.

## Revision descriptions

Auto-describe, when enabled, may run after:

- thread creation;
- an agent quiescence window — a quiet stretch with no agent tool calls — defaulting to 30 seconds;
- `jj split`;
- `jj squash`;
- explicit `kk thread describe --refresh`.

kiki stamps each job with an input hash. If the diff, ancestry, bookmark name, or relevant metadata changes while the model is running, kiki discards the result and queues a fresh job from the current state.

The auto-describe prompt may use:

- the revision diff;
- ancestor descriptions;
- the current bookmark name;
- kiki-owned metadata state.

It must not read the thread transcript.

## Bookmark names

Auto-rename, when enabled, may propose slugs — short, dash-separated names — for kiki-owned thread bookmarks. (A jj bookmark is roughly a git branch name.) The prompt includes sibling bookmark names so the model can choose a distinct slug.

An external `jj bookmark rename` marks the bookmark human-owned for the rest of the thread's life. Kiki follows the rename to the new name only when one exact operation proves it, under the rename rule in [Op-log watcher](13-architecture/op-log-watcher.md#the-classifier); a rename it cannot prove is `BookmarkMissing` and goes to `kk repair`. kiki does not rename it again unless an explicit future command opts it back in.

## Squash and merge ownership

`jj squash` folds one revision's changes into another. When a squash combines a kiki-owned description with non-kiki content, the resulting description becomes human-owned. Ownership defaults toward preservation.

This rule is intentionally simple. If kiki cannot prove the resulting prose is still its own, it steps aside.

## Trailers

Setting `[autorename] trailer = true` may add an opt-in `Kk-Auto: true` trailer — an extra labeled line at the end of a commit message — for transparency. The trailer is audit decoration only. The sqlite content-hash ledger still decides ownership.

## Race control

Metadata writes require a per-thread advisory lock, a lock that cooperating writers agree to check before writing. Auto-describe and auto-rename wait for snapshot quiescence: no in-flight agent tool call touching files, and no in-progress jj operation.

If kiki cannot acquire the lock within 5 seconds, it abandons the attempt and re-queues it. kiki may spend a model call and still discard the result. That waste is better than writing stale prose.

## Configuration

`[autorename]` controls the feature:

- `enabled`: `true | false`
- `cadence`: `idle-only | events | always | off`
- `idle_ms`: how long things must stay quiet before a job fires
- `trailer`: whether to write the transparency trailer (default `false`; opt-in)
- event toggles for creation, split, squash, and manual refresh

Cost management remains outside v1. kiki does not cap model spend, concurrent agents, CPU, RAM, or token usage.

## Provider

Auto-describe and auto-rename call the model through `AICompose`, a provider-agnostic seam — an interface that hides which AI vendor is in use. `[ai]` selects the backend:

- `provider`: `anthropic | openai | local-ollama | ...`
- `model`: provider-specific model identifier (defaults to a Haiku-class model for Anthropic).
- `api_key_env`: env var holding the API key (default `ANTHROPIC_API_KEY` for Anthropic).
- `api_key_path`: file path holding the API key (alternative to `api_key_env`).

The first provider implementation is Anthropic. The trait surface is generic, so additional providers can be added without touching the metadata ledger or the prompt-assembly logic.

The auto-AI loop is opt-in. `[autorename] enabled = false` is the default, so a fresh install never calls a provider until the user configures one.
