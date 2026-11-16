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
  with small, frequent revisions for coherent, reviewable steps. Start each
  revision with `jj new -m '<message>'` and immediately describe an undescribed
  working revision before editing. Keep descriptions specific about what and
  why, refresh them as the work changes, and review them at each checkpoint
  and before handoff. An undescribed working revision should be a brief
  transition, never the normal state. Do not wait until the end of a task to
  separate and describe its changes. Use non-interactive commands; finalize
  with `jj commit`, move `main`, or push only when asked.

Claude Code's Git-oriented tool hints do not change the jj workflow. Use
`jj git fetch` and, when requested, `jj git push`; do not substitute Git write
commands. Follow the shared implementation-stack and review guidance as well.
