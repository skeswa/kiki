# Configuration

Configuration is how you change kiki's settings. It is written in [TOML](https://toml.io/), a plain-text settings format. Settings can come from several sources. For each key, the highest-priority source that sets it determines the value.

Configuration inspection must show each effective value and the source that set it. This lets users trace an unexpected setting.

The [acceptance slice](appendix-a-glossary.md#acceptance-slice) is the part of kiki that v1 needs to be accepted. It implements only the layers and keys needed to:

- run the [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) (kiki's background program, [`kkd`](appendix-a-glossary.md#kkd));
- select a [harness](appendix-a-glossary.md#harness) (the coding-agent program kiki runs in a thread);
- locate the terminal runtime;
- place state and workspaces;
- deliver critical notifications.

The full layering and the feature-specific sections below are staged according to the sole scope ledger in [Orientation](01-orientation.md).

## Precedence

Precedence is the order in which layers win. From lowest to highest:

1. hardcoded defaults
2. user config: `~/.config/kiki/config.toml`
3. repo-local config: `~/.config/kiki/repos/<repo_id>/config.toml` (it lives outside the repository, so it is never committed)
4. `KIKI_*` environment
5. CLI flags

"`KIKI_*` environment" means [environment variables](https://en.wikipedia.org/wiki/Environment_variable) whose names start with `KIKI_`. The exact forms are:

- **Environment variable:** `KIKI_<SECTION>_<KEY>`, in upper case. For example, `KIKI_AGENT_DEFAULT_HARNESS=codex` sets `[agent] default_harness`.
- **CLI flag:** `--config section.key=value`. For example, `--config agent.default_harness=codex`.

### Keys that only the user config file can set

Some keys are structural to the daemon: every key in `[terminal]`, and `[paths] herdr_dir`. They shape the one terminal server that [`kkd`](appendix-a-glossary.md#kkd) runs for the user, and `kkd` does not run inside anyone's terminal.

For these keys, only the user config file counts. The environment and the flags of the terminal that invoked `kk` are ignored for them, with a warning. Repo-local config is ignored for them too.

Those five layers are the acceptance-slice precedence. v1.x ([later polish](appendix-a-glossary.md#v1-x-polish)) inserts two more layers:

- repo-shared committed config (`<repo>/.kiki.toml`), below user config;
- per-thread [SQLite](https://www.sqlite.org/) config, above repo-local config.

Adding those layers must not change the relative order of the acceptance layers.

## Commands

The acceptance slice supports:

- `get`
- `show`

`kk config get <key>` reports both the effective value and the layer it came from.

`kk config show` prints the whole merged configuration. Beside each value it names the layer the value came from.

`set`, `unset`, and `edit` ship with the v1.x full-layering surface. Until then, users edit the user or repo-local TOML file directly and use `show` to verify the result.

Unknown keys warn, not error.

## Structural keys

A changed setting does not always apply right away. This section says when each kind of key takes effect.

- **Structural keys** require a daemon restart. Examples are the daemon socket and the state-database paths.
- **Terminal-server keys** are structural too, but a daemon restart is not enough to apply them. They are `[terminal] session`, `[terminal] herdr_bin`, and `[paths] herdr_dir`. If one changes while a [server instance](appendix-a-glossary.md#server-instance) is open, `kkd` does not start a second server. It keeps the old one, reports that a change is pending, and requires the approved [`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server) plan (`kk repair --server`). See [Terminal keys](#terminal-keys).
- **The default harness** takes effect at the next `kk new`. It does not restart live threads.
- **`workspaces_root`** applies to the next `kk new`. Existing workspaces stay where they are.
- **`[timeouts]` keys and `[cascade] delivery_attempts`** reload live. A new value applies to the next wait that starts.
- **Cosmetic keys** may hot-reload: the change applies immediately.
- **Some keys** take effect at the next thread-lifecycle event (`kk new` or `kk reopen`) rather than hot-reloading or requiring a daemon restart.
- **Deferred UI keys** may instead take effect at the next overlay open.

Keys that wait for a lifecycle event or an overlay open are not reapplied retroactively to live [terminal groups](appendix-a-glossary.md#terminal-group) or [incarnations](appendix-a-glossary.md#incarnation). A terminal group is the set of terminals that belongs to one thread. An incarnation is one running lifetime of a thread's agent.

Configuration is deserialized (read from text) into strongly typed [Rust](https://www.rust-lang.org/) structs. Each field declares its reload behavior as `hot`, `lifecycle`, or `restart`. The daemon uses that metadata to decide what happens when a value changes:

- apply it immediately;
- wait for the next lifecycle event; or
- warn and name the required restart.

Values merge across layers in one of two ways:

- Map-like config values merge by key across layers.
- List-like values replace as a unit, unless a later chapter explicitly gives that key append semantics.

## Sections

A TOML file groups keys into named sections, written in square brackets.

Acceptance-slice sections:

- `[agent]`: the default harness and harness-specific args.
  - The key is `default_harness = "claude-code" | "codex"`, initially `claude-code`. These name [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) and [Codex](https://github.com/openai/codex).
  - Args are keyed per harness, so one repo can default to Claude Code while a thread spawns with `--harness codex`.
- `[notifications]`: per-event `loud | soft | silent` behavior for acceptance-slice [attention events](appendix-a-glossary.md#attention-event), plus `os_provider` (`auto | notify-rust | osascript | herdr | off`).
  - Per-event keys hot-reload.
  - `os_provider` resolves at the next dispatch.
  - See [Notification keys](#notification-keys) and [Observability](12-observability.md).
- `[paths]`: overrides for state, socket, generated-Herdr-configuration, and workspace-root paths.
- `[terminal]`: where the [Herdr](appendix-a-glossary.md#herdr) executable is and which named Herdr server kiki owns. Herdr is the [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer) that hosts kiki's terminals. See [Terminal keys](#terminal-keys).
- `[timeouts]`: how long kiki waits at each step that has a time limit. See [Timeout keys](#timeout-keys).
- `[cascade]`: `delivery_attempts`, the limit on delivery retries. See [Timeout keys](#timeout-keys).

Deferred v1.x sections:

- `[github]`: backend selection (initially `gh`, the [GitHub CLI](https://cli.github.com/)) and, once polling ships, poll cadence.
- `[autorename]`: [auto-describe](appendix-a-glossary.md#auto-describe) and [auto-rename](appendix-a-glossary.md#auto-rename) triggers and cadence. The metadata ledger and execution loop ship together with that feature; they are not acceptance foundations.
- `[ui]`: personal-preference keys for the [overlay TUI](appendix-a-glossary.md#overlay-tui), the optional [`ui` role pane](appendix-a-glossary.md#ui-role-pane), and the `shell` [role pane](appendix-a-glossary.md#role-pane).
- `[reopen]`: `catchup_pairs` (default `10`) controls explicitly requested `kk reopen --catch-up` text.
- `[ai]`: provider, model, and credential-source settings for provider-backed v1.x features.

### Consent is not configuration

Transcript-egress consent is your permission to send [transcript](appendix-a-glossary.md#thread-transcript) content to an AI provider. Remembered transcript-egress consent is durable privacy state, not a configuration layer.

- It is keyed in the registered repo's SQLite database by thread, normalized provider identity, purpose (`catch_up | transcript_mcp`), and disclosure version.
- You can inspect it, grant it for MCP (the [Model Context Protocol](https://modelcontextprotocol.io/)), and revoke it through `kk privacy consent`.
- It cannot be pre-approved by committed TOML, environment, CLI flags, MCP, or a generic operational approval.
- A grant must come from the enrolled foreground presenter after the provider-specific disclosure. (The presenter is the [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter): the enrolled local program that shows a plan to a person at the keyboard and collects the answer.)

## Notification keys

`[notifications]` holds one key per [attention event](appendix-a-glossary.md#attention-event). Each key takes a level: `loud`, `soft`, or `silent`. This chapter owns the key names and what each level does. [Observability](12-observability.md#attention-events) describes the events themselves.

### What each level does

kiki has four places to show an event. A level decides which of them it uses.

| Level    | OS notification                               | Herdr toast                        | Overlay toast (v1.x) | Status mark |
| -------- | --------------------------------------------- | ---------------------------------- | -------------------- | ----------- |
| `loud`   | yes, unless `os_provider` is `herdr` or `off` | only when `os_provider` is `herdr` | yes                  | yes         |
| `soft`   | no                                            | no                                 | yes                  | yes         |
| `silent` | no                                            | no                                 | no                   | yes         |

- **OS notification and Herdr toast** are the two forms of the configured transport, `os_provider`. Exactly one of them is used for a `loud` event: the OS notification by default, or the Herdr [toast](appendix-a-glossary.md#toast) when `os_provider = "herdr"`. With `os_provider = "off"`, neither is sent.
- **Overlay toast** is kiki's own toast inside the [overlay](appendix-a-glossary.md#overlay-tui). It appears only while an overlay is open, and only after the overlay ships.
- **Status mark** is the event's durable state, shown by `kk ls`, `kk status`, and the sidebar projection. No level turns it off. A level changes how hard kiki tries to get your attention; it never hides state.

### Event keys

| Key                   | Event                                                                                    | Default  | Tier             |
| --------------------- | ---------------------------------------------------------------------------------------- | -------- | ---------------- |
| `agent_blocked`       | the agent is waiting on a permission prompt                                              | `loud`   | acceptance slice |
| `agent_crashed`       | the harness exited or crashed under a live launcher                                      | `loud`   | acceptance slice |
| `cascade_conflicted`  | a cascade reconciliation exposed textual conflicts                                       | `loud`   | acceptance slice |
| `lifecycle_failed`    | a lifecycle operation failed (`CreateFailed`, `CloseFailed`, a failed reopen or restart) | `loud`   | acceptance slice |
| `projection_issue`    | a [projection issue](appendix-a-glossary.md#projection-issue) opened on an active thread | `loud`   | acceptance slice |
| `delivery_exhausted`  | an intent's delivery attempts are [exhausted](appendix-a-glossary.md#exhausted-intent)   | `loud`   | acceptance slice |
| `parent_abandoned`    | a follows parent's head or owned revisions were abandoned locally                        | `loud`   | acceptance slice |
| `goal_complete`       | the agent reports its goal complete                                                      | `soft`   | acceptance slice |
| `agent_silent`        | the agent has been silent past the silence threshold                                     | `silent` | v1.x             |
| `parent_merged`       | a follows parent's pull request merged                                                   | `loud`   | v1.x             |
| `pr_check_failed`     | a pull-request check failed                                                              | `loud`   | v1.x             |
| `external_force_push` | an external force-push of the thread's branch was seen                                   | `loud`   | v1.x             |
| `metadata_written`    | an auto-rename or auto-describe write completed                                          | `silent` | v1.x             |

Notes:

- `agent_blocked` depends on the harness adapter proving its permission-prompt signal. For a harness without that proof, permission-prompt detection is v1.x. A crashed agent still shows `blocked` through `agent_crashed`. See [Observability](12-observability.md#attention-events).
- A closed thread's `CheckpointAbandoned` issue does not fire `projection_issue`. It is reported on `kk ls --all` and `kk repair` only.
- `goal_complete` at `soft` is a status mark plus an overlay toast. Before the overlay ships, only the status mark shows.
- The acceptance-slice events are the ones in the scope ledger in [Orientation](01-orientation.md): a blocked or crashed agent, a conflicted cascade, an exhausted delivery, a followed parent abandoned, a failed lifecycle operation, and a projection issue. `goal_complete` is also in the slice, as a `soft` status mark with an overlay toast.
- v1.x keys are ignored with a warning until their feature ships. The state behind a v1.x event still shows in `kk ls` and `kk status` where the slice already tracks it.
- The silence threshold for `agent_silent` is a separate deferred key.

## Timeout keys

Many steps in kiki wait for something, and each wait has a limit. `[timeouts]` names every one of those limits. When another chapter says a step is "bounded" or has a "deadline", it names one of these keys.

| Key                | Default | Used for                                                                                                                        |
| ------------------ | ------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `launcher_report`  | `10s`   | waiting for role launchers to report                                                                                            |
| `ready_handshake`  | `60s`   | launch until the [ready handshake](appendix-a-glossary.md#ready-handshake); expiry is `CreateFailed` (or the restart's failure) |
| `freeze_stabilize` | `5s`    | the [freeze](appendix-a-glossary.md#freeze) reaching a fixed point (two passes that find the same set of processes)             |
| `frozen_step`      | `30s`   | any single step while processes are frozen                                                                                      |
| `verified_exit`    | `10s`   | waiting for a terminated process to be gone                                                                                     |
| `hook_connect`     | `1s`    | [`kk-hook`](appendix-a-glossary.md#kk-hook) connecting to `kkd` and being admitted                                              |
| `slow_path`        | `30s`   | one reconciliation holding a tool batch (the [slow-path bound](appendix-a-glossary.md#slow-path-bound))                         |
| `frontier_retry`   | `2s`    | [frontier sampler](appendix-a-glossary.md#frontier-sampler) retries                                                             |

One more limit lives in its own section:

| Key                           | Default | Used for                                                                                                         |
| ----------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------- |
| `[cascade] delivery_attempts` | `3`     | how many times kiki retries a delivery before the intent is [exhausted](appendix-a-glossary.md#exhausted-intent) |

Rules for these keys:

- All of them are user-config keys. They are ignored with a warning in repo-local config.
- They reload live. A new value applies to the next wait that starts; a wait already running keeps the limit it started with.
- Values are durations written as a number and a unit, such as `500ms`, `10s`, or `2m`.
- A `frozen_step` expiry before termination begins takes [verified resume](appendix-a-glossary.md#verified-resume). Once termination has begun, a failure is `CloseFailed` (or the plan's failed state), never a resume.
- On a `hook_connect` expiry, `kkd` never admitted the call, so the hook checks the thread's [barrier marker](appendix-a-glossary.md#barrier-marker). With the marker absent, the tool call goes through with the harness's non-blocking decision. With the marker present, the answer is a blocking deny. A `slow_path` expiry is different: `kkd` already admitted the call, so the answer is a blocking deny, never continue.
- Each harness adapter pins the harness's own hook timeout above `slow_path` plus a margin. Raising `slow_path` therefore takes effect for a thread's harness at its next [incarnation](appendix-a-glossary.md#incarnation).

## Path keys

`[paths]` is the central place to relocate kiki's filesystem footprint: the files and directories kiki uses. All keys are optional; defaults are listed below.

| key               | type   | default                             | scope                                                   |
| ----------------- | ------ | ----------------------------------- | ------------------------------------------------------- |
| `user_state_dir`  | string | `~/.config/kiki/`                   | structural: daemon restart                              |
| `user_state_db`   | string | `<user_state_dir>/state.db`         | structural: daemon restart                              |
| `kkd_socket`      | string | `<user_state_dir>/kkd.sock`         | structural: daemon restart                              |
| `repo_state_dir`  | string | `<user_state_dir>/repos/<repo_id>/` | structural: daemon restart                              |
| `herdr_dir`       | string | `<user_state_dir>/herdr/`           | structural: user config only; `replace-terminal-server` |
| `workspaces_root` | string | `<parent-of-repo>/`                 | applies to the next `kk new`                            |

### The MCP socket and audit tables

`kkd_mcp_socket` (default `<user_state_dir>/kkd-mcp.sock`) is the path of the separate socket for the deferred MCP transcript surface. The key ships with that surface and is ignored with a warning until then.

There is no `audit_log` path key. The audit record lives in database tables, not in a file:

- Attempts resolved to a repo write to that repo database's SQLite `audit_log`.
- Bootstrap, registry-wide, unknown-repo, and pre-resolution attempts write to the per-user database's SQLite `user_audit_log`.
- Each attempt has exactly one authoritative row; neither table is mirrored to a file.

### `workspaces_root`

`workspaces_root` does not embed `<repo>` or `<slug>`. kiki always materializes the [workspace](appendix-a-glossary.md#workspace) (a thread's own directory of files) as `<workspaces_root>/<repo>-kiki-<slug>/`.

For example, setting `workspaces_root = ~/work/kk-workspaces/` puts every thread's workspace under that directory instead of next to its source repo.

### `repo_state_dir`

`repo_state_dir` defaults to a centralized location under `<user_state_dir>`, keyed by the repo's `<repo_id>`. The `<repo_id>` is a [UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier) assigned at `kk init` and recorded in the per-user `repos` table.

Per-repo state lives under that directory:

- the per-repo `state.db` containing audit rows;
- the repo-local `config.toml`;
- `errors/<thread_id>.log`;
- `credentials/` (one file per thread plus the repo's `registration` credential);
- `harness/<thread_id>/` (launch-scoped harness settings);
- `recovery/` (data kiki needs to restore files it changed).

The source repo's own filesystem carries no kiki state. The one exception is the deferred optional `<repo>/.kiki.toml` committed config layer, which may live there when a team deliberately adds one.

### `herdr_dir`

`herdr_dir` holds exactly one thing: the Herdr configuration file kiki generates, `<herdr_dir>/config.toml`. `kkd` passes that file to the [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) through `HERDR_CONFIG_PATH`. The dedicated server is the one Herdr server kiki runs for itself.

`herdr_dir` is not a root for Herdr's other files. Herdr has no configuration-directory option:

- it keeps the named session's socket, saved state, and logs under its own directories, keyed by the session name;
- it shares its plugin registry and state directory with the user's other Herdr use.

Kiki does not redirect `XDG_CONFIG_HOME` or `XDG_STATE_HOME` to change that. (These are the [XDG base directory](https://specifications.freedesktop.org/basedir-spec/latest/) variables that tell programs where to keep settings and state.) The reason is that every pane inherits the server's environment. jj, git, gh, and shells in every thread would then read their configuration from the wrong place.

What separates kiki's server from the user's default Herdr server is therefore a separate server process, socket, saved session, and configuration file, not a separate directory tree.

## Terminal keys

`[terminal]` selects the terminal runtime kiki drives. Both keys are structural to the daemon, so only the user config file counts for them. `KIKI_*` environment variables and `--config` flags from the terminal that invoked `kk` are ignored for them, with a warning. So is repo-local config. The same holds for `[paths] herdr_dir`. (See [Keys that only the user config file can set](#keys-that-only-the-user-config-file-can-set).)

| key         | type   | default           | scope                                                   |
| ----------- | ------ | ----------------- | ------------------------------------------------------- |
| `herdr_bin` | string | `herdr` on `PATH` | structural: user config only; `replace-terminal-server` |
| `session`   | string | `kiki`            | structural: user config only; `replace-terminal-server` |

"`herdr` on `PATH`" means the `PATH` of the constructed environment described under [Who starts the server](#who-starts-the-server), not the `PATH` of the terminal that invoked `kk`.

### Changing a terminal key while a server is running

A change to `session`, `herdr_bin`, or `[paths] herdr_dir` cannot just be applied, because the server that is running was started with the old values.

- If a [server instance](appendix-a-glossary.md#server-instance) is open, `kkd` does not start a second server. It keeps the old one and keeps using the old values for it.
- `kkd` reports that a change is pending. `kk repair --server` shows it.
- The change takes effect only through the approved [`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server) plan, applied with `kk repair --server`. That plan lists every thread and process the replacement stops, stops the old server with verified exit, and starts a new one with the new values.
- If no server instance is open, the new values are used the next time `kkd` starts the server.

### What the two keys mean

`herdr_bin` is the executable [`kkd`](appendix-a-glossary.md#kkd) uses to start the [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) and `kk attach` uses to attach a client.

`session` is the [Herdr](appendix-a-glossary.md#herdr) session name of that server, and it is the server's address. `kkd` starts the server with `--session <name>` and `HERDR_CONFIG_PATH=<herdr_dir>/config.toml`, and nothing else selects it.

- A Herdr session is a server namespace, not a per-thread object; kiki runs exactly one.
- The name must not be `default` or any session name the user already uses.
- `kkd` checks that the longest socket name Herdr derives for it fits the platform's socket-path limit.

### Who starts the server

Only `kkd` starts the server. But the server must outlive `kkd`, so `kkd` does not run it as a child inside its own service unit. It asks the service manager to run the server as a unit of its own:

- on macOS, a separate [launchd](https://en.wikipedia.org/wiki/Launchd) job;
- on Linux, a separate transient [systemd](https://en.wikipedia.org/wiki/Systemd) user unit.

launchd and systemd are the system services that keep background programs running. A "transient" unit is one created at run time by a command, with no unit file on disk.

A `kkd` crash, restart, or upgrade must not stop the server, because stopping the server ends every thread's processes. This is a proof gate, not an assumption: the test kills `kkd` under each real service manager and checks that the server and the agents keep running (see [Testing](14-testing.md)).

`kkd` starts the server with a constructed environment: the user's login baseline of `HOME`, `USER`, `SHELL`, `PATH`, and locale. It never uses the environment of the terminal that invoked `kk`.

- Panes inherit that environment plus Herdr's own variables and each role pane's explicit ones.
- `HERDR_CONFIG_PATH` is visible inside panes.
- `kk attach` uses Herdr's connect-only client mode and never starts a server.
- `kkd` recognises a server it started by the peer identity on its `Open` `terminal_servers` row. A running server `kkd` did not start is unverified. That includes one left by Herdr's own handoff or upgrade. `kkd` ends the old row, which ends its bindings and raises [`TerminalMissing`](appendix-a-glossary.md#terminalmissing), and records the new peer as `Unverified`. It provisions nothing on an unverified server. The fix is the `replace-terminal-server` plan, and after it `restart-terminal` for each thread.
- An instance change where `kkd` itself started the new server, for example after a server crash, needs only `restart-terminal`.

### Supported Herdr versions

Kiki pins a supported Herdr version range. When `kkd` starts or connects to the dedicated server, it checks three things against that range:

- the version;
- the protocol number;
- the object of named capability flags returned by the ping reply.

An unsupported or missing Herdr fails terminal lifecycle commands with an error that names the found and required versions. It does not corrupt recorded thread state.

[`client_targeted_focus`](appendix-a-glossary.md#client-targeted-focus) is the one required Herdr extension, and it must arrive as a new flag in that object. It lets kiki move one viewer's screen without moving anyone else's (see [caller-local focus](appendix-a-glossary.md#caller-local-focus)). Until the server advertises it, caller-local `kk switch` fails by naming the capability. It does not degrade to a focus change that moves every client.

`kkd` never stops a running dedicated server on its own to apply a changed key: stopping it ends every thread's processes. Only the approved `replace-terminal-server` plan stops it (see [Changing a terminal key while a server is running](#changing-a-terminal-key-while-a-server-is-running)).

### The generated Herdr configuration file

Kiki generates the dedicated server's Herdr configuration file and owns it. These Herdr settings are fixed by kiki and are not exposed as kiki keys:

- automatic agent resume on restore is off (`[session] resume_agents_on_restore = false`);
- onboarding is off;
- Herdr's update, version, and manifest checks are off;
- toast delivery is set to Herdr's own [toasts](appendix-a-glossary.md#toast) (`[ui.toast] delivery = "herdr"`), which Herdr leaves off by default;
- sidebar rows and width are sized for kiki's label;
- the sidebar row layout that displays the tokens kiki publishes. This is a v1.x surface; the generated file declares no [sidebar tokens](appendix-a-glossary.md#sidebar-token) until it ships;
- the keybinding that opens the overlay and the plugin or command entries it invokes (v1.x);
- Herdr's agent-integration installer is never invoked against a managed harness's settings.

A toast is a small message that pops up briefly and then goes away.

`kkd` regenerates the file and validates it with its own parser immediately before every server start. It refuses to start the server on any diagnostic. This is not optional tidiness:

- Herdr's client can rewrite the file from its settings screen.
- When Herdr cannot parse the file, it silently loads its defaults, which turn agent resume on.

Edits to the generated file are therefore overwritten at the next start.

Some Herdr preferences are ones kiki does not need to control: theme, Herdr's own keybindings, mouse and scrollback behavior. They are not kiki configuration keys in v1, and kiki's generated file leaves them at Herdr's defaults.

The user's default Herdr server and its configuration file are never read or changed.

## UI keys

This entire section is deferred until the v1.x UI surfaces ship.

"Next terminal-group provisioning" below means the next `kk new`, `kk reopen`, or terminal-restart repair. `mouse_enabled` and `theme` apply to kiki's own surfaces, the [overlay](appendix-a-glossary.md#overlay-tui) and the [`ui` pane](appendix-a-glossary.md#ui-role-pane), not to Herdr.

All `[ui]` keys are personal preference. They are valid in user and per-thread config, but invalid in repo-shared config. If set in repo-shared config, kiki warns and ignores them.

| key                   | type   | default       | hot-reload                           |
| --------------------- | ------ | ------------- | ------------------------------------ |
| `ui_pane`             | bool   | `false`       | no: next terminal-group provisioning |
| `ui_pane_width`       | int    | `32`          | no: next terminal-group provisioning |
| `shell_pane`          | bool   | `true`        | no: next terminal-group provisioning |
| `shell_pane_position` | string | `"below"`     | no: next terminal-group provisioning |
| `shell_pane_size_pct` | int    | `25`          | no: next terminal-group provisioning |
| `mouse_enabled`       | bool   | `true`        | yes                                  |
| `overlay_min_cols`    | int    | `80`          | no: next overlay open                |
| `toast_ttl_ms`        | int    | `4000`        | yes                                  |
| `theme`               | string | `"soft-dark"` | yes                                  |

### `theme`

`theme` selects the palette (the set of colors). The canonical alternates are `soft-dark` (default), `soft-light`, and `high-contrast`. Unknown theme values warn and fall back to `soft-dark`.

### `shell_pane_position`

`shell_pane_position` accepts one of two values:

- `below` (horizontal split below the agent pane, default); or
- `right` (vertical split to the right of the agent pane).

Unknown values warn and fall back to `below`. The `shell` role pane (see [shell pane](appendix-a-glossary.md#shell-pane)) always lives in the same tab as the `agent` pane; routing it to a separate tab is intentionally omitted.

### The `ui_pane*` keys

The `ui_pane*` keys replace the former persistent-sidebar keys. Herdr's native sidebar now carries the cross-thread list and attention state. So the `ui` role pane exists only for users who want a permanently visible Stack ([follows](appendix-a-glossary.md#follows)) tree.

Kiki's generated Herdr configuration sizes Herdr's sidebar for kiki's label. That width is not a kiki key, and the user can still hide or collapse the sidebar in Herdr.

### When role-pane keys apply

Role-pane keys are `lifecycle` keys. They apply when kiki provisions a [terminal group](appendix-a-glossary.md#terminal-group):

- at `kk new`;
- at `kk reopen`;
- when a `kk repair` plan restarts a thread's terminal after a terminal-runtime restart.

`kk switch` performs no terminal mutation. So it never applies these keys and never re-creates a pane the user closed. A user who wants another shell splits natively in Herdr.

The full lifecycle, degradation, and authority semantics for the shell pane live in [Interface · Shell pane](10-interface/spec.md#shell-pane).

The semantics, wireframes, and degradation rules for these keys live in [Interface](10-interface/spec.md).
