# D-0003: Use colocated jj and one shared contributor guide

- Recorded: 2026-11-16
- Decided by: owner, 2026-11-16; source: “I want this repo to use jj just like swingset” and “all of these things and practices we have stolen from swingset should be part of AGENTS.md and CLAUDE.md”
- Topic: Version control and contributor workflow
- Supersedes: Earlier CLAUDE.md guidance permitting Git writes alongside jj
- Superseded by: —

## Decision

Use jj in a colocated checkout, retaining the existing Git history and origin.
Use separately described draft revisions for logical changes. Finalizing with
`jj commit`, moving `main`, and pushing require a user request; routine work
may snapshot, describe, and separate local draft changes. Use jj for VCS writes.

Pin jj through mise. Provide `mise run vcs:init` for new Git clones and local
defaults: a 16 MiB new-file snapshot limit, tracked `main@origin`, and
`trunk()` resolving to `main@origin`. Published trunk history only advances.

Make `AGENTS.md` the shared owner of repository guidance, including the journal,
decisions, mise tasks, formatting, and jj. `CLAUDE.md` imports it and highlights
those workflows for Claude Code.

## Why

The old guide claimed a colocated checkout even though `.jj/` was absent.
Initializing jj makes the documented workflow real. A shared guide follows
Swingset's pattern and prevents two copies of contributor rules from drifting.

## Alternatives and consequences

Keeping Git as a second write interface would make the working-copy workflow
ambiguous. Colocation preserves GitHub compatibility. The `.jj/` directory and
repository-local settings are not portable through Git; new clones must run
the initialization task. The journal, tooling, and VCS changes remain local
draft revisions until the user asks to finalize or publish them.

## Links

- [Shared contributor guidance](../../AGENTS.md) and [Claude entry point](../../CLAUDE.md)
- [Swingset VCS and contributor rules](https://github.com/skeswa/swingset/blob/ec2e7f13198e2939d4f73104b80771c8fdaff304/AGENTS.md)
