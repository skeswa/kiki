# Configuration

Configuration is TOML and layered.

Configuration must answer two questions clearly: what value is effective, and where did it come from. Anything else is a tax paid every time the user debugs a machine they forgot they configured.

The acceptance slice implements only the layers and keys needed to run the daemon, select a harness, place state/workspaces, and deliver critical notifications. The full layering and feature-specific sections below are staged according to the sole scope ledger in [Orientation](01-orientation.md).

## Precedence

From lowest to highest:

1. hardcoded defaults
2. user config: `~/.config/kiki/config.toml`
3. repo-local gitignored config: `~/.kiki/repos/<repo_id>/config.toml`
4. `KIKI_*` environment
5. CLI flags

Those five layers are the acceptance-slice precedence. v1.x inserts repo-shared committed config (`<repo>/.kiki.toml`) below user config and per-thread SQLite config above repo-local config. Adding those layers must not change the relative order of the acceptance layers.

## Commands

The acceptance slice supports:

- `get`
- `show`

`kk config get <key>` reports both effective value and source layer.

`set`, `unset`, and `edit` ship with the v1.x full-layering surface. Until then, users edit the user or repo-local TOML file directly and use `show` to verify the result.

Unknown keys warn, not error.

## Structural keys

Structural keys such as daemon socket and state-database paths require daemon restart. The default harness takes effect at the next `kk new` rather than restarting live threads.

Cosmetic keys may hot-reload.

Some keys take effect at the next thread-lifecycle event (`kk new` or `kk reopen`) rather than hot-reloading or requiring a daemon restart. Deferred UI keys may instead take effect at the next overlay open. They are not reapplied retroactively to live sessions.

Configuration is deserialized into strongly typed Rust structs. Each field declares reload behavior as `hot`, `lifecycle`, or `restart`; the daemon uses that metadata to decide whether a changed value applies immediately, waits for the next lifecycle event, or produces a warning naming the required restart.

Map-like config values merge by key across layers. List-like values replace as a unit unless a later chapter explicitly gives that key append semantics.

## Sections

Acceptance-slice sections:

- `[agent]` — default harness, harness-specific args.
- `[notifications]` — per-event `loud | soft | silent` behavior for acceptance-slice attention events and `os_provider` (`auto | notify-rust | osascript | tmux | off`). Per-event keys hot-reload; `os_provider` resolves at the next dispatch. See [Observability](14-observability.md).
- `[paths]` — overrides for state, socket, and workspace-root paths.

Deferred v1.x sections:

- `[github]` — backend selection (initially `gh`) and, once polling ships, poll cadence.
- `[autorename]` — auto-describe and auto-rename triggers and cadence. The metadata ledger and execution loop ship together with that feature; they are not acceptance foundations.
- `[ui]` — personal-preference keys for the overlay TUI, persistent sidebar, and shell pane.
- `[reopen]` — `catchup_pairs` (default `10`) controls explicitly requested `kk reopen --catch-up` text.
- `[ai]` — provider, model, and credential-source settings for provider-backed v1.x features.

Remembered transcript-egress consent is durable privacy state, not a configuration layer. It is keyed in the registered repo's SQLite database by thread, normalized provider identity, purpose (`catch_up | transcript_mcp`), and disclosure version. It can be inspected, granted for MCP, and revoked through `kk privacy consent`, but cannot be pre-approved by committed TOML, environment, CLI flags, MCP, or a generic operational approval; a grant must come from the enrolled foreground presenter after the provider-specific disclosure.

## Path keys

`[paths]` is the central place to relocate kiki's filesystem footprint. All keys are optional; defaults are listed below.

| key               | type   | default                             | scope                       |
| ----------------- | ------ | ----------------------------------- | --------------------------- |
| `user_state_dir`  | string | `~/.kiki/`                          | structural — daemon restart |
| `user_state_db`   | string | `<user_state_dir>/state.db`         | structural — daemon restart |
| `kkd_socket`      | string | `<user_state_dir>/kkd.sock`         | structural — daemon restart |
| `repo_state_dir`  | string | `<user_state_dir>/repos/<repo_id>/` | structural — daemon restart |
| `workspaces_root` | string | `<parent-of-repo>/`                 | structural — next `kk new`  |

`kkd_mcp_socket` is a deferred MCP-substrate path key. There is no `audit_log` path: resolved repo attempts use that repo database's SQLite `audit_log`, while bootstrap, registry-wide, unknown-repo, and pre-resolution attempts use the per-user database's SQLite `user_audit_log`. Each attempt has exactly one authoritative row; neither table is mirrored to a file.

`workspaces_root` does not embed `<repo>` or `<slug>`; kiki always materializes the workspace as `<workspaces_root>/<repo>-kiki-<slug>/`. Setting `workspaces_root = ~/work/kk-workspaces/` puts every thread's workspace under that directory rather than next to its source repo.

`repo_state_dir` defaults to a centralized location under `<user_state_dir>` keyed by the repo's `<repo_id>` (a UUID assigned at `kk init` and recorded in the per-user `repos` table). Per-repo state — the per-repo `state.db` containing audit rows, gitignored `config.toml`, `errors/<thread_id>.log`, and `credentials/<thread_id>` — lives under that directory. The source repo's own filesystem carries no kiki state; only the deferred optional `<repo>/.kiki.toml` committed config layer may live there when a team deliberately adds one.

## UI keys

This entire section is deferred until the v1.x UI surfaces ship.

All `[ui]` keys are personal preference. They are valid in user and per-thread config, but invalid in repo-shared config. If set in repo-shared config, kiki warns and ignores them.

| key                         | type   | default       | hot-reload                                     |
| --------------------------- | ------ | ------------- | ---------------------------------------------- |
| `persistent_sidebar`        | bool   | `false`       | no — next `kk new` / `kk reopen`               |
| `sidebar_width`             | int    | `32`          | no — next `kk new` / `kk reopen`               |
| `sidebar_min_terminal_cols` | int    | `100`         | no — next `kk new` / `kk reopen`               |
| `shell_pane`                | bool   | `true`        | no — next `kk new` / `kk reopen` / `kk switch` |
| `shell_pane_position`       | string | `"below"`     | no — next `kk new` / `kk reopen` / `kk switch` |
| `shell_pane_size_pct`       | int    | `25`          | no — next `kk new` / `kk reopen` / `kk switch` |
| `shell_pane_min_rows`       | int    | `24`          | no — next `kk new` / `kk reopen` / `kk switch` |
| `mouse_enabled`             | bool   | `true`        | yes                                            |
| `overlay_min_cols`          | int    | `80`          | no — next overlay open                         |
| `toast_ttl_ms`              | int    | `4000`        | yes                                            |
| `theme`                     | string | `"soft-dark"` | yes                                            |

`theme` selects the palette; the canonical alternates are `soft-dark` (default), `soft-light`, and `high-contrast`. Unknown theme values warn and fall back to `soft-dark`.

`shell_pane_position` accepts `below` (horizontal split below the agent pane, default) or `right` (vertical split to the right of the agent pane). Unknown values warn and fall back to `below`. The shell pane is always co-resident with the agent pane in the same tmux window; routing it to a separate window is intentionally omitted. The full lifecycle, degradation, and authority semantics for the shell pane live in [Interface · Shell pane](12-interface/spec.md#shell-pane).

The semantics, wireframes, and degradation rules for these keys live in [Interface](12-interface/spec.md).
