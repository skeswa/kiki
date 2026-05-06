# Config spec

Configuration is TOML and layered.

## Precedence

From lowest to highest:

1. hardcoded defaults
2. user config: `~/.config/kiki/config.toml`
3. repo-local gitignored config: `<repo>/.kiki/config.toml`
4. repo-shared committed config: `<repo>/.kiki.toml`
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

`[ui] persistent_sidebar` is personal preference. It is valid in user and per-thread config, but invalid in repo-shared config. If set in repo-shared config, kiki warns and ignores it.
