# Configuration

Configuration is TOML and layered: several sources stack on top of each other, and higher layers win. Think of a stack of transparency sheets — the topmost sheet with a value written on it is the one you see.

Configuration must answer two questions clearly: what value is effective, and where did it come from. Anything else is a tax the user pays every time they debug a machine they forgot they configured.

The acceptance slice implements only the layers and keys needed to run the daemon, select a harness, locate the terminal runtime, place state and workspaces, and deliver critical notifications. The full layering and the feature-specific sections below are staged according to the sole scope ledger in [Orientation](01-orientation.md).

## Precedence

From lowest to highest:

1. hardcoded defaults
2. user config: `~/.config/kiki/config.toml`
3. repo-local gitignored config: `~/.config/kiki/repos/<repo_id>/config.toml`
4. `KIKI_*` environment
5. CLI flags

Those five layers are the acceptance-slice precedence. v1.x inserts two more layers: repo-shared committed config (`<repo>/.kiki.toml`) below user config, and per-thread SQLite config above repo-local config. Adding those layers must not change the relative order of the acceptance layers.

## Commands

The acceptance slice supports:

- `get`
- `show`

`kk config get <key>` reports both the effective value and the layer it came from.

`set`, `unset`, and `edit` ship with the v1.x full-layering surface. Until then, users edit the user or repo-local TOML file directly and use `show` to verify the result.

Unknown keys warn, not error.

## Structural keys

Structural keys, such as the daemon socket, the state-database paths, and the `[terminal]` keys, require a daemon restart. The default harness takes effect at the next `kk new`; it does not restart live threads.

Cosmetic keys may hot-reload — the change applies immediately.

Some keys take effect at the next thread-lifecycle event (`kk new` or `kk reopen`) rather than hot-reloading or requiring a daemon restart. Deferred UI keys may instead take effect at the next overlay open. None of these are reapplied retroactively to live terminal groups or incarnations.

Configuration is deserialized into strongly typed Rust structs. Each field declares its reload behavior as `hot`, `lifecycle`, or `restart`. The daemon uses that metadata to decide what happens when a value changes: apply it immediately, wait for the next lifecycle event, or warn and name the required restart.

Map-like config values merge by key across layers. List-like values replace as a unit, unless a later chapter explicitly gives that key append semantics.

## Sections

Acceptance-slice sections:

- `[agent]` — the default harness (`default_harness = "claude-code" | "codex"`, initially `claude-code`) and harness-specific args. Args are keyed per harness, so one repo can default to Claude Code while a thread spawns with `--harness codex`.
- `[notifications]` — per-event `loud | soft | silent` behavior for acceptance-slice attention events, plus `os_provider` (`auto | notify-rust | osascript | herdr | off`). Per-event keys hot-reload; `os_provider` resolves at the next dispatch. See [Observability](12-observability.md).
- `[paths]` — overrides for state, socket, Herdr-state, and workspace-root paths.
- `[terminal]` — where the Herdr executable is and which named Herdr server kiki owns. See [Terminal keys](#terminal-keys).

Deferred v1.x sections:

- `[github]` — backend selection (initially `gh`) and, once polling ships, poll cadence.
- `[autorename]` — auto-describe and auto-rename triggers and cadence. The metadata ledger and execution loop ship together with that feature; they are not acceptance foundations.
- `[ui]` — personal-preference keys for the overlay TUI, the optional `ui` role pane, and the `shell` role pane.
- `[reopen]` — `catchup_pairs` (default `10`) controls explicitly requested `kk reopen --catch-up` text.
- `[ai]` — provider, model, and credential-source settings for provider-backed v1.x features.

Remembered transcript-egress consent is durable privacy state, not a configuration layer. It is keyed in the registered repo's SQLite database by thread, normalized provider identity, purpose (`catch_up | transcript_mcp`), and disclosure version. You can inspect it, grant it for MCP, and revoke it through `kk privacy consent`. It cannot be pre-approved by committed TOML, environment, CLI flags, MCP, or a generic operational approval. A grant must come from the enrolled foreground presenter after the provider-specific disclosure.

## Path keys

`[paths]` is the central place to relocate kiki's filesystem footprint. All keys are optional; defaults are listed below.

| key               | type   | default                             | scope                       |
| ----------------- | ------ | ----------------------------------- | --------------------------- |
| `user_state_dir`  | string | `~/.config/kiki/`                   | structural — daemon restart |
| `user_state_db`   | string | `<user_state_dir>/state.db`         | structural — daemon restart |
| `kkd_socket`      | string | `<user_state_dir>/kkd.sock`         | structural — daemon restart |
| `repo_state_dir`  | string | `<user_state_dir>/repos/<repo_id>/` | structural — daemon restart |
| `herdr_dir`       | string | `<user_state_dir>/herdr/`           | structural — daemon restart |
| `workspaces_root` | string | `<parent-of-repo>/`                 | structural — next `kk new`  |

`kkd_mcp_socket` is a deferred MCP-substrate path key. There is no `audit_log` path key. Attempts resolved to a repo write to that repo database's SQLite `audit_log`. Bootstrap, registry-wide, unknown-repo, and pre-resolution attempts write to the per-user database's SQLite `user_audit_log`. Each attempt has exactly one authoritative row; neither table is mirrored to a file.

`workspaces_root` does not embed `<repo>` or `<slug>`; kiki always materializes the workspace as `<workspaces_root>/<repo>-kiki-<slug>/`. Setting `workspaces_root = ~/work/kk-workspaces/` puts every thread's workspace under that directory instead of next to its source repo.

`repo_state_dir` defaults to a centralized location under `<user_state_dir>`, keyed by the repo's `<repo_id>` (a UUID assigned at `kk init` and recorded in the per-user `repos` table). Per-repo state lives under that directory: the per-repo `state.db` containing audit rows, the gitignored `config.toml`, `errors/<thread_id>.log`, and `credentials/<thread_id>`. The source repo's own filesystem carries no kiki state. The one exception is the deferred optional `<repo>/.kiki.toml` committed config layer, which may live there when a team deliberately adds one.

`herdr_dir` is kiki's Herdr configuration root. The dedicated server is addressed by this root plus the session name (`terminal.session`); Herdr derives the socket and saved state beneath the root, and kiki names no socket path of its own. The configuration file kiki generates lives here too. Kiki starts the server so that it reads and writes only under this root and never under the user's own Herdr configuration. Changing `herdr_dir` while a dedicated server is running does not move that server; the old server and its terminal groups must be closed first.

## Terminal keys

`[terminal]` selects the terminal runtime kiki drives. Both keys are valid in user config, `KIKI_*` environment, and CLI flags. They are per-user, so they are ignored with a warning in repo-local config.

| key         | type   | default           | scope                       |
| ----------- | ------ | ----------------- | --------------------------- |
| `herdr_bin` | string | `herdr` on `PATH` | structural — daemon restart |
| `session`   | string | `kiki`            | structural — daemon restart |

`herdr_bin` is the executable `kkd` uses to start the dedicated server and `kk attach` uses to attach a client. `session` is the Herdr session name of that server. A Herdr session is a server namespace, not a per-thread object; kiki runs exactly one.

Kiki pins a supported Herdr version range. When `kkd` starts or connects to the dedicated server, it checks the version, protocol number, and capabilities returned by the ping reply against that range. An unsupported or missing Herdr fails terminal lifecycle commands with an error that names the found and required versions; it does not corrupt recorded thread state. `client_targeted_focus` is a required Herdr extension, not an optional one: until the server advertises it, caller-local `kk switch` fails by naming the capability rather than degrading to a focus change that moves every client. `kkd` never stops a running dedicated server to apply a changed key: stopping it ends every thread's processes.

Kiki generates the dedicated server's Herdr configuration file and owns it. These Herdr settings are fixed by kiki and are not exposed as kiki keys:

- automatic agent resume on restore is off (`[session] resume_agents_on_restore = false`);
- the sidebar row layout that displays the tokens kiki publishes — a v1.x surface; the generated file declares no sidebar tokens until it ships;
- the keybinding that opens the overlay and the plugin or command entries it invokes (v1.x);
- Herdr's agent-integration installer is never invoked against a managed harness's settings.

Edits to the generated file are overwritten. Herdr preferences that kiki does not need to control — theme, Herdr's own keybindings, mouse and scrollback behavior — are not kiki configuration keys in v1; kiki's generated file leaves them at Herdr's defaults. The user's default Herdr server and its configuration are never read or changed.

## UI keys

This entire section is deferred until the v1.x UI surfaces ship.

"Next terminal-group provisioning" below means the next `kk new`, `kk reopen`, or terminal-restart repair. `mouse_enabled` and `theme` apply to kiki's own surfaces — the overlay and the `ui` pane — not to Herdr.

All `[ui]` keys are personal preference. They are valid in user and per-thread config, but invalid in repo-shared config. If set in repo-shared config, kiki warns and ignores them.

| key                   | type   | default       | hot-reload                            |
| --------------------- | ------ | ------------- | ------------------------------------- |
| `ui_pane`             | bool   | `false`       | no — next terminal-group provisioning |
| `ui_pane_width`       | int    | `32`          | no — next terminal-group provisioning |
| `shell_pane`          | bool   | `true`        | no — next terminal-group provisioning |
| `shell_pane_position` | string | `"below"`     | no — next terminal-group provisioning |
| `shell_pane_size_pct` | int    | `25`          | no — next terminal-group provisioning |
| `mouse_enabled`       | bool   | `true`        | yes                                   |
| `overlay_min_cols`    | int    | `80`          | no — next overlay open                |
| `toast_ttl_ms`        | int    | `4000`        | yes                                   |
| `theme`               | string | `"soft-dark"` | yes                                   |

`theme` selects the palette. The canonical alternates are `soft-dark` (default), `soft-light`, and `high-contrast`. Unknown theme values warn and fall back to `soft-dark`.

`shell_pane_position` accepts `below` (horizontal split below the agent pane, default) or `right` (vertical split to the right of the agent pane). Unknown values warn and fall back to `below`. The `shell` role pane always lives in the same tab as the `agent` pane; routing it to a separate tab is intentionally omitted.

The `ui_pane*` keys replace the former persistent-sidebar keys. Herdr's native sidebar now carries the cross-thread list and attention state, so the `ui` role pane exists only for users who want a permanently visible Stack (follows) tree. Herdr's own sidebar width and visibility are Herdr preferences, not kiki keys.

Role-pane keys are `lifecycle` keys. They apply when kiki provisions a terminal group: at `kk new`, at `kk reopen`, and when a `kk repair` plan restarts a thread's terminal after a terminal-runtime restart. `kk switch` performs no terminal mutation, so it never applies them and never re-creates a pane the user closed; a user who wants another shell splits natively in Herdr. The full lifecycle, degradation, and authority semantics for the shell pane live in [Interface · Shell pane](10-interface/spec.md#shell-pane).

The semantics, wireframes, and degradation rules for these keys live in [Interface](10-interface/spec.md).
