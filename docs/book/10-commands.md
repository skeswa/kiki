# Commands

The CLI is porcelain over the thread model. It should make common kiki operations obvious without pretending to be a complete replacement for `jj`, `tmux`, or `gh`.

## Context resolution

Commands that act on a thread resolve context in this order:

1. explicit CLI target
2. environment
3. tmux session name
4. current working directory

If no thread resolves but the command is repo-scoped, the command may fall back to the registered repo. If no registered repo resolves, commands that need repo state must error with an actionable message.

## `kk init`

`kk init` opts a git+jj repository into kiki management.

It verifies prerequisites:

- jj is initialized;
- `gh` is authenticated enough for publish operations;
- Claude Code is available for the v1 harness;
- the repo can store gitignored local state under `<repo>/.kiki/`.

`kk init` does not create a starter thread. Thread creation is explicit.

## `kk`

Bare `kk` opens the overlay TUI in `NAVIGATE` mode (see [Interface](11-interface.md)) when the TUI ships. Before the TUI ships, it prints a concise command summary and points to `kk ls`. Outside a registered repo, even after the TUI ships, `kk` falls back to the command summary plus `kk ls`.

## `kk new`

`kk new` creates a thread as specified in [Threads](04-threads.md).

Important flags:

- `--follows <parent>` creates a live follows edge;
- `--no-follow` suppresses contextual following;
- `--harness <name>` selects a harness for the thread;
- `--harness-arg <arg>` passes harness-specific arguments;
- `--sidebar` / `--no-sidebar` override persistent sidebar config for the thread.

## `kk switch`

`kk switch <thread>` switches the tmux client to the target thread's tmux session. It does not mutate daemon focus state; see [Authority](05-authority.md).

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

`kk log` is stack-aware revision porcelain. It keeps the surface smaller than `jj log` and decorates the thread model kiki owns.

- Default expansion is current thread plus follows ancestors.
- Siblings, descendants not on the current line, and unrelated threads collapse to summaries.
- `--no-stack` expands only the current thread.
- `--all` includes closed threads as collapsed lines.
- `--wide` enriches collapsed summaries.
- `-r <revset>` passes through to jj revset selection, disables collapse logic, and errors if combined with `--no-stack`, `--all`, or `--wide`.

Outside a registered repo, `kk log` errors and points to `kk ls`.

The escape hatch for arbitrary revision selection is `jj`. kiki decorates the model it owns; it does not clone every flag of the tools beneath it.

## `kk status`

`kk status` renders a kiki header followed by literal `jj st` output.

- `--diff` appends the working-copy patch.
- `--diff --stat` emits a diffstat instead of a patch.
- `--no-jj` suppresses the jj body and emits only the header.

The cascade state indicator is exactly one of `in sync`, `pending`, or `conflicted`; it does not include counts.

## Thread management commands

Expected thread-management commands include:

- `kk close`
- `kk reopen <thread>`
- `kk thread transcript`
- `kk thread comments`
- `kk thread interrupt`
- `kk thread destroy`
- `kk thread detach` if the v1 detach escape hatch ships

`attach` and `reparent` are deferred graph-surgery commands.
