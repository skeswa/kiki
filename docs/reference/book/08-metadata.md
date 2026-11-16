# Metadata Evolution

kiki may eventually help keep three kinds of text current as work changes:

- [thread](appendix-a-glossary.md#thread) names (a thread is kiki's unit of work);
- checkpoint [bookmark](appendix-a-glossary.md#bookmark) names; and
- revision descriptions, which are the commit messages of [jj](https://docs.jj-vcs.dev/latest/), the version-control tool kiki drives.

Both the ownership foundation and the execution loop are [v1.x](appendix-a-glossary.md#v1-x-polish) work. The [acceptance slice](appendix-a-glossary.md#acceptance-slice) (the first accepted release) writes no AI-authored metadata, so it does not need to carry a ledger before that behavior exists. When the feature ships, kiki must know which prose it owns and which belongs to the human.

## Ownership ledger

The ownership ledger exists so that kiki does not overwrite words a human wrote. It is the record that tells kiki which text it wrote itself and may therefore update.

kiki tracks ownership in sqlite ([SQLite](https://www.sqlite.org/), its local database). It does not infer ownership by guessing from content, and it does not depend on jj trailers.

The ledger works like a sign-out sheet: kiki may only edit prose it can prove it wrote last. For every kiki-authored revision description or bookmark name, kiki records a content [hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function) — a fingerprint of the text — in `metadata_writes`. On the next read:

- if the current content still matches the stored hash, kiki may update it;
- if the current content differs, the artifact becomes human-owned;
- once human-owned, kiki does not rewrite it unless the user explicitly opts back in.

This conservative rule applies to human edits and to agent-authored edits alike. From kiki's point of view, anything outside the ledger is user territory.

## Revision descriptions

[Auto-describe](appendix-a-glossary.md#auto-describe) is the feature that writes a revision's description for you. This section says when it may run and what it may read.

Auto-describe, when enabled, may run after:

- thread creation;
- a quiet window — a stretch with no agent tool calls — defaulting to 30 seconds;
- `jj split`;
- `jj squash`;
- explicit `kk thread describe --refresh`.

kiki stamps each job with an input hash. If the diff, ancestry, bookmark name, or relevant metadata changes while the model is running, kiki discards the result and queues a fresh job from the current state.

The auto-describe prompt may use:

- the revision diff;
- ancestor descriptions;
- the current bookmark name;
- kiki-owned metadata state.

It must not read the [thread transcript](appendix-a-glossary.md#thread-transcript), kiki's local record of the conversation.

## Bookmark names

[Auto-rename](appendix-a-glossary.md#auto-rename) is the feature that suggests a name for a thread's bookmark. This section says what it may rename and what happens when a human renames the bookmark instead.

Auto-rename, when enabled, may propose slugs — short, dash-separated names — for kiki-owned thread bookmarks. (A jj [bookmark](https://docs.jj-vcs.dev/latest/bookmarks/) is roughly a git branch name.) The prompt includes sibling bookmark names so the model can choose a distinct slug.

An external `jj bookmark rename` marks the bookmark human-owned for the rest of the thread's life.

- Kiki follows the rename to the new name only when one exact [operation](https://docs.jj-vcs.dev/latest/operation-log/) proves it, under the rename rule in [Op-log watcher](13-architecture/op-log-watcher.md#the-classifier).
- A rename it cannot prove is [`BookmarkMissing`](appendix-a-glossary.md#bookmarkmissing) and goes to `kk repair`.
- A rename of a published thread always goes to repair, because jj leaves the tracked remote bookmark under the old name.
- kiki does not rename it again unless an explicit future command opts it back in.

## Squash and merge ownership

Sometimes kiki's text and a human's text end up combined in one description. This section says who owns the result.

`jj squash` folds one revision's changes into another. When a squash combines a kiki-owned description with non-kiki content, the resulting description becomes human-owned. Ownership defaults toward preservation.

This rule is intentionally simple. If kiki cannot prove the resulting prose is still its own, it steps aside.

## Trailers

A trailer is an extra labeled line at the end of a commit message. kiki can add one for transparency, but the trailer decides nothing about ownership.

Setting `[autorename] trailer = true` may add an opt-in `Kk-Auto: true` trailer. The trailer is audit decoration only. The sqlite content-hash ledger still decides ownership.

## Race control

Race control keeps kiki from writing a description based on files that are still changing. This section says how kiki waits its turn and when it gives up. (Two writers acting at once is called a [race condition](https://en.wikipedia.org/wiki/Race_condition).)

Metadata writes require a per-thread advisory lock, a lock that cooperating writers agree to check before writing. [Auto-describe](appendix-a-glossary.md#auto-describe) and [auto-rename](appendix-a-glossary.md#auto-rename) wait until nothing is changing the files or the repository:

- no in-flight agent tool call touching files; and
- no in-progress jj operation.

If kiki cannot acquire the lock within 5 seconds, it abandons the attempt and re-queues it. kiki may spend a model call and still discard the result. That waste is better than writing stale prose.

## Configuration

These settings turn the feature on and control how often it runs. They live in kiki's [TOML](https://toml.io/) configuration file.

`[autorename]` controls the feature:

- `enabled`: `true | false`
- `cadence`: `idle-only | events | always | off`
- `idle_ms`: how long things must stay quiet before a job fires
- `trailer`: whether to write the transparency trailer (default `false`; opt-in)
- event toggles for creation, split, squash, and manual refresh

Cost management remains outside v1. kiki does not cap model spend, concurrent agents, CPU, RAM, or token usage.

## Provider

The provider is the AI service that writes the text. This section says how kiki picks one and where it finds the key.

[Auto-describe](appendix-a-glossary.md#auto-describe) and [auto-rename](appendix-a-glossary.md#auto-rename) call the model through `AICompose`, a provider-agnostic seam — an interface that hides which AI vendor is in use. `[ai]` selects the backend:

- `provider`: `anthropic | openai | local-ollama | ...`
- `model`: provider-specific model identifier (defaults to a Haiku-class model for Anthropic).
- `api_key_env`: env var ([environment variable](https://en.wikipedia.org/wiki/Environment_variable)) holding the API key (default `ANTHROPIC_API_KEY` for Anthropic).
- `api_key_path`: file path holding the API key (alternative to `api_key_env`).

The first provider implementation is Anthropic. The [trait](https://doc.rust-lang.org/book/ch10-02-traits.html) surface (the interface definition) is generic, so additional providers can be added without touching the metadata ledger or the prompt-assembly logic.

The auto-AI loop is opt-in. `[autorename] enabled = false` is the default, so a fresh install never calls a provider until the user configures one.
