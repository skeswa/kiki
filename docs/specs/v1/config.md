# Config spec

Configuration is TOML and layered.

## Precedence

From lowest to highest:

1. hardcoded defaults
2. repo-shared committed config: `<repo>/.kiki.toml`
3. user config: `~/.config/kiki/config.toml`
4. repo-local gitignored config: `<repo>/.kiki/config.toml`
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

## UI keys

All `[ui]` keys are personal preference. They are valid in user and per-thread config, but invalid in repo-shared config. If set in repo-shared config, kiki warns and ignores them.

| key                         | type   | default       | hot-reload                       |
| --------------------------- | ------ | ------------- | -------------------------------- |
| `persistent_sidebar`        | bool   | `false`       | no — next `kk new` / `kk reopen` |
| `sidebar_width`             | int    | `32`          | no — next `kk new` / `kk reopen` |
| `sidebar_min_terminal_cols` | int    | `100`         | no — next `kk new` / `kk reopen` |
| `mouse_enabled`             | bool   | `true`        | yes                              |
| `overlay_min_cols`          | int    | `80`          | no — next overlay open           |
| `toast_ttl_ms`              | int    | `4000`        | yes                              |
| `theme`                     | string | `"soft-dark"` | yes                              |

`theme` selects the palette; the canonical alternates documented for v1 are `soft-dark` (default), `soft-light`, and `high-contrast`. Unknown theme values warn and fall back to `soft-dark`.

The semantics, wireframes, and degradation rules for these keys live in `tui.md`.
