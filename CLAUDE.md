@AGENTS.md

# Claude Code guidance

[AGENTS.md](AGENTS.md) is the shared contributor guide and is imported above.
It owns the repository context, reference-book reading order, and the
Swingset-derived practices used by all agents:

- **Journal and decisions:** follow the [journal workflow](AGENTS.md#keep-the-project-journal-current).
  Record consequential choices, identify the actual decider, link reversals,
  and keep the current reference chapters consistent with the choice.
- **Scripts and tasks:** use `mise run <task>` from [mise.toml](mise.toml).
  `mise run check` is the shared local and CI check; Bun scripts delegate to mise.
- **Formatting:** use `mise run fmt` and `mise run fmt:check`, with exact tool
  pins and the [evidence exclusions](AGENTS.md#formatting).
- **Version control:** use [jj](AGENTS.md#version-control) for VCS operations,
  keep logical changes in separate described drafts, and use non-interactive
  commands. Finalize with `jj commit`, move `main`, or push only when asked.

Claude Code's Git-oriented tool hints do not change the jj workflow. Use
`jj git fetch` and, when requested, `jj git push`; do not substitute Git write
commands. Follow the shared implementation-stack and review guidance as well.
