# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read this first

The canonical spec for what this repo is building lives at `docs/prds/0001-kiki.md`. It is long but exhaustive — read it before making any non-trivial change. Subsequent PRDs will be added as `docs/prds/000N-*.md`. Treat the PRD as the source of truth for behavior, scope, and v1 vs. v2 boundaries; if something in the code disagrees with the PRD, that is a finding to surface, not silently align with.

## What kiki is, in one paragraph

kiki (binary `kk`) is a daemon-backed coordinator that ties jujutsu (jj), tmux, Claude Code/Codex, and the GitHub CLI (`gh`) into a single workflow for multi-threaded agentic coding. The atom is a **thread** — a themed sequence of jj revisions on a bookmark, materialized in its own jj workspace, attached to its own tmux session running an agent. Threads can branch off other threads with live-follow semantics; when an ancestor evolves, descendants are auto-rebased and their agents are paused-informed-resumed via a `PreToolUse`-hook-driven synthetic-tool-result mechanism. kiki is an **ambient coordinator**, not a gatekeeper: it watches the jj op log and reacts to whatever it sees (human, agent, or kkd itself), and never refuses direct `jj`/`gh`/`tmux` ops.

The planned cargo workspace per the PRD has four crates: `kiki-core` (library — shared types/traits/proto/migrations, no I/O), `kkd` (daemon binary), `kk` (CLI binary that also hosts the TUI as a subcommand), and `kk-hook` (PreToolUse sidecar binary). `kkd` is the gRPC **server**, hosting a stable service over `~/.kiki/kkd.sock`; `kk` and `kk-hook` are the first two **clients** of that service, with no privileged internal API — any future UI (e.g., a native macOS GUI) consumes the same gRPC surface they do. State lives in `~/.kiki/state.db` (cross-repo registry) plus `<repo>/.kiki/state.db` (per-repo runtime).

## Implementation-stack tension to be aware of

The PRD specifies **Rust** (Q8 in the grilling, locked) for `kkd` and friends. The repo is currently bootstrapped as a **Bun + TypeScript** project (`package.json`, `tsconfig.json`, `index.ts` placeholder). This is a real divergence and not yet reconciled in the PRD. If you are about to write or modify implementation code, surface this to the user before picking a language — do not silently default to either side.

## Common commands

```bash
mise install         # provision Bun (only tool pinned today)
bun install          # install deps
bun run index.ts     # run the placeholder entrypoint
bun run fmt          # format with oxfmt (per package.json's "fmt" script)
```

There is no test runner, linter, or build step configured yet; the project is pre-skeleton. Do not invent commands that aren't in `package.json`.

## VCS

This repo uses **jujutsu (jj) colocated with git**. Both `.jj/` and `.git/` exist; `git` operations work but `jj` is the primary interface. Conventions:

- Use `jj describe -m "<subject>\n\n<body>"` for revision descriptions. Recent commits use a one-line subject in imperative mood plus a multi-paragraph body — match that style.
- The `main` bookmark is the trunk.
- The repo uses GitHub (`origin git@github.com:skeswa/kiki.git`); pushes go via `jj git push` or `git push`.

## Codex stop-time review gate

A stop-time Codex review gate is enabled for this repo (set up via `/codex-jj:setup --enable-review-gate`). Before stop, a fresh Codex review may be required. The plugin lives outside this repo at `/Users/skeswa/repos/skeswa/codex-plugin-cc`.

## PRD review precedent

PRDs in this repo are expected to survive a Codex review pass. The first PRD's review found three v1-scope contradictions (config layering, Codex harness, `kk reopen`), all resolved in the same revision. When updating PRDs, reread Out of Scope against User Stories and Implementation Decisions for consistency before publishing.
