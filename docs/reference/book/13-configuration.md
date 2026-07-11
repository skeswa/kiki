# Configuration

Configuration is TOML and layered.

Configuration must answer two questions clearly: what value is effective, and where did it come from. Anything else is a tax paid every time the user debugs a machine they forgot they configured.

## Precedence

From lowest to highest:

1. hardcoded defaults
2. repo-shared committed config: `<repo>/.kiki.toml`
3. user config: `~/.config/kiki/config.toml`
4. repo-local gitignored config: `~/.kiki/repos/<repo_id>/config.toml`
5. per-thread sqlite config
6. `KIKI_*` environment
7. CLI flags

## Commands

`kk config` supports:

- `get`
- `set`
- `unset`
- `edit`
- `show`

`kk config get <key>` reports both effective value and source layer.

Unknown keys warn, not error.

## Structural keys

Structural keys such as default harness and daemon socket path require daemon restart.

Cosmetic keys may hot-reload.

Some keys take effect at the next thread-lifecycle event (`kk new`, `kk reopen`, or next overlay open) rather than hot-reloading or requiring a daemon restart. They are not reapplied retroactively to live sessions.

Configuration is deserialized into strongly typed Rust structs. Each field declares reload behavior as `hot`, `lifecycle`, or `restart`; the daemon uses that metadata to decide whether a changed value applies immediately, waits for the next lifecycle event, or produces a warning naming the required restart.

Map-like config values merge by key across layers. List-like values replace as a unit unless a later chapter explicitly gives that key append semantics.

## Sections

The top-level config sections expected in v1:

- `[agent]` — default harness, harness-specific args.
- `[github]` — backend selection (default `gh` shell-out), poll cadence.
- `[autorename]` — auto-describe / auto-rename triggers and cadence (the execution loop is v1.x polish; the v1-required foundation is the `MetadataLedger` ownership ledger).
- `[notifications]` — per-event behavior (loud / soft / silent) for the attention-event vocabulary (agent permission prompts, cascade conflict, parent merged, parent abandoned, PR check failed, etc.) and `os_provider` (`auto | notify-rust | osascript | tmux | off`) for the OS-native transport. Per-event keys hot-reload; `os_provider` hot-reloads at the next notification dispatch. See [Observability](14-observability.md).
- `[ui]` — personal-preference keys for the overlay TUI, persistent sidebar, and shell pane (table below).
- `[reopen]` — `catchup_pairs` (default `10`) controls the size of the `kk reopen` catch-up message.
- `[ai]` — `provider`, `model`, `api_key_env`, `api_key_path` for the auto-describe / auto-rename backend (see [Metadata Evolution](10-metadata.md)).
- `[paths]` — overrides for state, socket, and workspace-root paths.

## Path keys

`[paths]` is the central place to relocate kiki's filesystem footprint. All keys are optional; defaults are listed below.

| key               | type   | default                         | scope                       |
| ----------------- | ------ | ------------------------------- | --------------------------- |
| `user_state_dir`  | string | `~/.kiki/`                      | structural — daemon restart |
| `user_state_db`   | string | `<user_state_dir>/state.db`     | structural — daemon restart |
| `kkd_socket`      | string | `<user_state_dir>/kkd.sock`     | structural — daemon restart |
| `kkd_mcp_socket`  | string | `<user_state_dir>/kkd-mcp.sock` | structural — daemon restart |
| `repo_state_dir`  | string | `<user_state_dir>/repos/<repo_id>/` | structural — daemon restart |
| `workspaces_root` | string | `<parent-of-repo>/`             | structural — next `kk new`  |
| `audit_log`       | string | `<repo_state_dir>/audit.log`    | structural — daemon restart |

`workspaces_root` does not embed `<repo>` or `<slug>`; kiki always materializes the workspace as `<workspaces_root>/<repo>-kiki-<slug>/`. Setting `workspaces_root = ~/work/kk-workspaces/` puts every thread's workspace under that directory rather than next to its source repo.

`repo_state_dir` defaults to a centralized location under `<user_state_dir>` keyed by the repo's `<repo_id>` (a UUID assigned at `kk init` and recorded in the per-user `repos` table). Per-repo state — the per-repo `state.db`, gitignored `config.toml`, `audit.log`, `errors/<thread_id>.log`, and `credentials/<thread_id>` — lives under that directory. The source repo's own filesystem carries no kiki state; only an optional `<repo>/.kiki.toml` (the committed repo-shared config layer) lives there, and only when the team commits one.

## UI keys

All `[ui]` keys are personal preference. They are valid in user and per-thread config, but invalid in repo-shared config. If set in repo-shared config, kiki warns and ignores them.

| key                         | type   | default       | hot-reload                       |
| --------------------------- | ------ | ------------- | -------------------------------- |
| `persistent_sidebar`        | bool   | `false`       | no — next `kk new` / `kk reopen` |
| `sidebar_width`             | int    | `32`          | no — next `kk new` / `kk reopen` |
| `sidebar_min_terminal_cols` | int    | `100`         | no — next `kk new` / `kk reopen` |
| `shell_pane`                | bool   | `true`        | no — next `kk new` / `kk reopen` / `kk switch` |
| `shell_pane_position`       | string | `"below"`     | no — next `kk new` / `kk reopen` / `kk switch` |
| `shell_pane_size_pct`       | int    | `25`          | no — next `kk new` / `kk reopen` / `kk switch` |
| `shell_pane_min_rows`       | int    | `24`          | no — next `kk new` / `kk reopen` / `kk switch` |
| `mouse_enabled`             | bool   | `true`        | yes                              |
| `overlay_min_cols`          | int    | `80`          | no — next overlay open           |
| `toast_ttl_ms`              | int    | `4000`        | yes                              |
| `theme`                     | string | `"soft-dark"` | yes                              |

`theme` selects the palette; the canonical alternates documented for v1 are `soft-dark` (default), `soft-light`, and `high-contrast`. Unknown theme values warn and fall back to `soft-dark`.

`shell_pane_position` accepts `below` (horizontal split below the agent pane, default) or `right` (vertical split to the right of the agent pane). Unknown values warn and fall back to `below`. The shell pane is always co-resident with the agent pane in the same tmux window; routing it to a separate window is intentionally not a v1 option. The full lifecycle, degradation, and authority semantics for the shell pane live in [Interface · Shell pane](12-interface/spec.md#shell-pane).

The semantics, wireframes, and degradation rules for these keys live in [Interface](12-interface/spec.md).
