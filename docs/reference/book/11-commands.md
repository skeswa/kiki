# Commands

The CLI is porcelain over the thread model. It should make common kiki operations obvious without pretending to be a complete replacement for `jj`, `tmux`, or `gh`.

Every `kk` invocation presents the `Admin` credential — the binary reads `~/.kiki/admin-cred` on each call — so the sections below do not restate the requirement per command. [Authority](06-authority.md) owns the model, its read-gating rules, and the one exception (`kk switch` needs no `Admin` gate).

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

- jj is initialized — hard error if not, with a message naming `jj init --colocate` as the typical fix.
- `gh` is authenticated enough for publish operations — hard error if not.
- `kkd` can write the per-repo state directory at `~/.kiki/repos/<repo_id>/` — hard error if not writable. The source repo's filesystem itself receives no writes; the only kiki file that may live there is the optional committed `<repo>/.kiki.toml` (the repo-shared config layer), which `kk init` does not create.

`kk init` does **not** verify that any specific harness binary is installed. The harness contract is pluggable (see [Harness adapter](15-architecture/harness-adapter.md)); v1 ships only the `claude-code` adapter, but kiki does not refuse registration on a host that has not installed a harness yet. The check happens at `kk new` time instead: spawning a thread with the configured default harness errors if that harness's binary is missing.

`kk init` is idempotent in an already-registered repo. It prints a status summary (registration path and time, active and closed thread counts, state.db location) and exits with status 0; no mutation. Re-registering after `kk repo unregister` is the explicit re-registration path.

`kk init` does not create a starter thread. Thread creation is explicit.

## `kk`

Bare `kk` opens the overlay TUI in `NAVIGATE` mode (see [Interface](12-interface/spec.md)) when the TUI ships. Before the TUI ships, it prints a concise command summary and points to `kk ls`. Outside a registered repo, even after the TUI ships, `kk` falls back to the command summary plus `kk ls`.

## `kk new`

`kk new` creates a thread as specified in [Threads](05-threads.md).

Important flags:

- `--follows <parent>` creates a live follows edge;
- `--no-follow` suppresses contextual following;
- `-m "<prompt>"` supplies an initial prompt delivered to the harness as the first user turn;
- `--harness <name>` selects a harness for the thread;
- `--harness-arg <arg>` passes harness-specific arguments;
- `--sidebar` / `--no-sidebar` override persistent sidebar config for the thread.

Initial prompt sources are `-m` and stdin. If both are supplied, `-m` wins. If neither is supplied, `kk new` proceeds without an initial prompt: the placeholder name becomes `unnamed-<short-hex>` (kk-owned) and the agent starts with no first-turn input. It is acceptable for the user to spawn a thread without yet knowing what it is about.

The first-turn prompt is captured in the transcript as `author=human`, `direction=inbound_to_agent`.

## `kk switch`

`kk switch <thread>` switches the tmux client to the target thread's tmux session. It does not mutate daemon focus state; see [Authority](06-authority.md).

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

Collapsed line format:

- Default: `<status-glyph> <bookmark> [#<pr>] <agent-glyph> "<last-revision-description>"`.
- `--wide`: adds literal PR state (`draft`, `ready`, `merged`, `closed`), CI roll-up, agent state with age, and relative last activity.

No other jj-log flags: `-r <revset>` is the only jj-shaped flag adopted by `kk log` in v1. Other jj log affordances, such as patches, templates, reverse order, and custom color, remain direct `jj log` usage. This avoids a near-mirror CLI that drifts as jj evolves.

Outside a registered repo, `kk log` errors and points to `kk ls`.

The escape hatch for arbitrary revision selection is `jj`. kiki decorates the model it owns; it does not clone every flag of the tools beneath it.

## `kk status`

`kk status` renders a kiki header followed by literal `jj st` output.

- `--diff` appends the working-copy patch.
- `--diff --stat` emits a diffstat instead of a patch.
- `--no-jj` suppresses the jj body and emits only the header.

The cascade state indicator is exactly one of `in sync`, `pending`, or `conflicted`; it does not include counts.

## `kk publish`

`kk publish` publishes the resolved thread to GitHub through `gh`; see [Publishing](09-publishing.md).

Important flags:

- `--no-edit` uses the AI draft as-is.
- `--no-ai` opens an empty editor draft.
- `-m "<title>"` sets the PR title inline.
- `--ready` opens the PR ready for review instead of draft.
- `--downstack` publishes the current thread plus unpublished descendants, top-down.
- `--refresh` regenerates title/body for an existing PR only when explicitly requested.
- `--review-stack` names the default top-down, editor-session-per-PR stack publish; an uncommitted alias that may not ship.

## `kk close`

`kk close [<thread>]` archives a thread without deleting tracked jj work; see [Threads](05-threads.md#close).

Important flags:

- `--discard-pr` also closes the open PR. Plain `kk close` leaves PR state untouched.

## `kk reopen`

`kk reopen <thread>` restores a closed thread; see [Threads](05-threads.md#reopen) for the restore-and-catch-up semantics.

## `kk thread transcript`

`kk thread transcript [<thread>] [<change>]` reads the local transcript for a thread.

Important flags:

- `--search <query>` runs full-text search.
- `--range <from>..<to>` reads a change span.
- `--recent <n>` reads the tail of the thread.
- `--include-unanchored` includes rows with unknown change anchors.
- `--include-tombstoned` includes rows for tombstoned or redirected changes.
- `--no-synthesized` hides kiki-authored synthesized rows.

## `kk thread comments`

`kk thread comments [<thread>]` lists GitHub PR review comments for the thread's PR.

The v1 surface is read-only. Feeding review comments into agent context is future work.

## `kk thread interrupt`

`kk thread interrupt <thread>` hard-stops and reframes the thread's agent through the harness resume path. It is the explicit human escape hatch for a stuck or off-track agent and uses the same hard-escalation shape as cascade conflict handling.

## `kk thread detach`

`kk thread detach <thread>` removes the thread's live follows edge; see [Cascade](07-cascade.md#detach-and-graph-surgery) for what detach does and does not touch. `attach` and `reparent` are deferred beyond v1.

## `kk thread destroy`

`kk thread destroy <thread>` permanently destroys a thread except for jj operation recovery; see [Threads](05-threads.md#destroy).

Important flags:

- `--keep-log` retains transcript rows for explicit destroyed-thread views.

Destroy requires explicit confirmation.

## `kk config`

`kk config get|set|unset|edit|show` manages layered TOML configuration; see [Configuration](13-configuration.md).

`kk config get <key>` reports the effective value and the source layer. Unknown keys warn rather than error. Structural key changes must tell the user whether they hot-reload, take effect at the next lifecycle event, or require daemon restart.

## Deferred thread management commands

`attach`, `reparent`, and `restore --to <path>` (used to re-point an `Orphaned` thread at a moved workspace) are deferred graph-surgery and lifecycle commands.

## Repo registry

`kk repo unregister <path>` removes a repo from the per-user registry. It is the explicit counterpart to `kk init`.

By default, `kk repo unregister` removes both the row from `~/.kiki/state.db`'s `repos` table and the centralized state directory at `~/.kiki/repos/<repo_id>/` (threads, transcript, audit log, credentials, and per-thread error logs). The action is irreversible — there is no kiki-managed undo, mirroring `kk thread destroy`'s shape (see [Threads · destroy](05-threads.md#destroy)). The `Admin` authority requirement is the safeguard; v1 does not add a confirmation prompt on top.

`--keep-state` preserves the centralized state directory on disk while still removing the registry row. The preserved directory becomes orphaned bytes, useful only for an operator who wants to inspect or copy the contents before deleting them by hand. It does **not** enable any kiki-managed recovery: a future `kk init` at the same canonical path mints a fresh `repo_id` and a fresh state directory; the preserved directory has no link to the new registration. The flag exists because losing transcripts and audit logs by mistyping a path is a high cost, and `--keep-state` is the careful-operator escape hatch — not a recovery contract.

Source-repo moves are not auto-detected. With no breadcrumb inside the source tree, a moved repo appears unregistered to `kk` from the new path. The v1 recoveries are: move the source tree back so its path matches the registered `canonical_path`; or `kk repo unregister` (with `--keep-state` first if the operator wants to copy state out before re-init) followed by `kk init` at the new location, which starts a fresh registration with a new `repo_id`. A move-aware `kk repo relocate` command is not in v1.
