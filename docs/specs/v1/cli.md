# CLI spec

## Context resolution

Commands that act on a thread resolve context in this order:

1. explicit CLI target
2. environment
3. tmux session name
4. current working directory

If no thread resolves but the command is repo-scoped, the command may fall back to the registered repo. If no registered repo resolves, commands that need repo state must error with an actionable message.

## `kk`

Bare `kk` opens the overlay TUI in `NAVIGATE` mode (see `tui.md`) when the TUI ships. Before the TUI ships, it prints a concise command summary and points to `kk ls`. Outside a registered repo, even after the TUI ships, `kk` falls back to the command summary plus `kk ls` rather than opening an empty overlay.

## `kk ls`

`kk ls` lists active threads.

Repo scope and lifecycle scope are independent:

- Inside a registered repo, default scope is the current repo.
- Outside a registered repo, default scope is all registered repos and includes a `repo` column.
- `--all-repos` widens repo scope from current repo to all registered repos.
- `--all` includes closed threads.
- Destroyed threads remain hidden unless an explicit destroyed-thread flag is added.

`--all` must not change repo scope.

## `kk log`

`kk log` is stack-aware revision porcelain, not a mirror of `jj log`.

- Default expansion is current thread plus follows ancestors.
- Siblings, descendants not on the current line, and unrelated threads collapse to summaries.
- `--no-stack` expands only the current thread.
- `--all` includes closed threads as collapsed lines.
- `--wide` enriches collapsed summaries.
- `-r <revset>` passes through to jj revset selection, disables collapse logic, and errors if combined with `--no-stack`, `--all`, or `--wide`.

Outside a registered repo, `kk log` errors and points to `kk ls`.

## `kk status`

`kk status` renders a kiki header followed by literal `jj st` output.

- `--diff` appends the working-copy patch.
- `--diff --stat` emits a diffstat instead of a patch.
- `--no-jj` suppresses the jj body and emits only the header.

The cascade state indicator is exactly one of `in sync`, `pending`, or `conflicted`; it does not include counts.
