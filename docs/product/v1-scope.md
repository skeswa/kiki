# v1 scope

v1 is successful when kiki can create, switch, coordinate, publish, archive, reopen, and inspect agentic work threads without relying on the original PRD as the implementation contract.

## Acceptance surface

The v1 acceptance slice includes:

- `kk init`
- `kk new`
- `kk switch`
- `kk ls`
- `kk close`
- `kk reopen`
- `kk publish`
- `kk log`
- `kk status`
- `kk thread transcript`
- per-user daemon with per-repo opt-in
- jj workspace + bookmark backed thread identity
- tmux session lifecycle
- Claude Code v1 harness integration
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
