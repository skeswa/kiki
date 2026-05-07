# Orientation

This chapter defines what kiki is. Later chapters define how it behaves.

## The tool

kiki (`kk`) is an agentic coding workflow coordinator. It gives a developer a first-class unit for a themed line of work: a jj-backed revision stack, an isolated workspace, a tmux session, and an agent session that can be paused, resumed, published, archived, and composed with related work.

kiki exists to make parallel, recursive work patterns cheap enough that a developer can maximally utilize and collaborate with agents. Today, switching between agent-led lines of inquiry means stashes, branches, rebases, lost terminals, and reconstructed context. kiki makes that machinery ambient: threads branch from other threads, follow live ancestor changes, and carry enough local transcript and status context that the human can get oriented without needing to resort to archaeology.

## Principles

- kiki coordinates ambiently. Developers may still use `jj`, `tmux`, and `gh` directly.
- Threads provide cooperative isolation. v1 separates workspaces to prevent accidental interference; it does not sandbox same-UID processes.
- Human-authored prose is preserved. kiki may draft names, descriptions, and PR text, but it must not silently overwrite deliberate human edits.
- Local transcript data stays local. v1 transcript rows may feed local recall and reopen catch-up; they must not feed externally published artifacts.
- Cascade safety matters more than eagerness. Descendant workspaces move at agent boundaries or quiescence, not mid-edit.

## v1 contract

v1 is successful when kiki can create, switch, coordinate, publish, archive, reopen, and inspect agentic work threads without relying on the original PRD as the implementation contract.

The v1 acceptance surface includes:

- `kk init`, `kk new`, `kk switch`, `kk ls`, `kk close`, `kk reopen`
- `kk publish`, `kk log`, `kk status`, `kk thread transcript`
- per-user daemon with per-repo opt-in
- jj workspace + bookmark backed thread identity
- tmux session lifecycle
- pluggable harness architecture; the `claude-code` adapter is the only one that ships in v1
- PreToolUse hook IPC for cascade delivery
- cascade pause, rebase, inject, acknowledge, and conflict handling
- transcript capture and local read API
- stack-aware publish flow
- enough config layering for defaults, user, repo-local, per-thread, environment, and CLI flags

## Deferred or stretch

These can deepen v1 but must not block the core acceptance slice unless explicitly promoted:

- overlay TUI
- persistent sidebar pane
- AI auto-rename polish
- AI auto-describe polish
- full notification vocabulary
- PR-merge auto-archive
- read-only MCP transcript tools

## Out of scope for v1

- filesystem sandboxing or security isolation between threads
- resource caps for agents
- Codex and non-Claude-Code harness adapters
- broad MCP substrate for cross-thread agent messaging or spawning
- webhooks; GitHub polling is sufficient for v1
- full-screen multiplexer behavior beyond tmux integration

## Non-goals

v1 leaves these problems alone:

- kiki does not sandbox agents from each other. Per-thread workspaces provide cooperative separation only.
- kiki does not manage CPU, memory, token, or model spend.
- kiki does not block direct use of `jj`, `gh`, or `tmux`.
- kiki does not mirror the full `jj` CLI surface. When users need arbitrary jj behavior, they should run `jj`.
- kiki does not publish local transcript prose, summarize it into PRs, or feed it into auto-describe or auto-rename.
- kiki does not defend against an actively malicious same-UID process that can read files and invoke `kk`.
