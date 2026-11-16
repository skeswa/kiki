# D-0002: Use pinned mise tooling for tasks and formatting

- Recorded: 2026-11-16
- Decided by: owner, 2026-11-16; source: “I would also like to steal how swingset does formatting and uses mise for scripts and tasks”; tool selection adapted by the agent
- Topic: Development workflow
- Supersedes: —
- Superseded by: —

## Decision

Make `mise.toml` the task and tool-version authority for local work and CI.
Keep Bun package scripts as compatibility aliases. Use exactly pinned Oxfmt
for the current code and documentation formats and Taplo for TOML, with
`mise run fmt` and a non-writing `fmt:check` included in `mise run check`.

Keep generated files, lockfiles, fixtures, retained evidence, published probes,
and dated research reports out of automatic formatting. Formatting works
without the documentation dependencies installed.

## Why

Swingset gives contributors one command interface and reproducible formatting
independent of the application environment. Kiki's previous Bun-only formatter
was tied to site dependencies, and CI did not check its output.

## Alternatives and consequences

Keeping task implementations in both Bun and mise would create competing
definitions. Thin aliases preserve existing commands. Copying every Swingset
formatter would install tools for languages Kiki does not yet maintain; add
those when needed. The formatter version change requires a baseline format of
handwritten files, with evidence preserved.

## Links

- [Tooling and formatting rules](../../AGENTS.md#tooling-and-tasks) and [task definitions](../../mise.toml)
- [Swingset mise configuration at the inspected revision](https://github.com/skeswa/swingset/blob/ec2e7f13198e2939d4f73104b80771c8fdaff304/mise.toml)
