# Naming

The tool is named **kiki**. The command is `kk`.

## Names

- Tool name: `kiki`
- CLI binary: `kk`
- Daemon binary: `kkd`
- Hook sidecar: `kk-hook` (exclusive `PreToolUse` admission plus `PostToolBatch` completion reporting for the Claude adapter)
- User state directory: `~/.config/kiki/`
- User config: `~/.config/kiki/config.toml`
- Per-repo state and gitignored config: `~/.config/kiki/repos/<repo_id>/` (centralized; the source repo's filesystem holds no kiki state)
- Repo-shared committed config: `<repo>/.kiki.toml` (the only kiki file that lives inside the source repo, and only when the team commits one)

## Command style

Daily-driver verbs should be short and single-word:

- `new`
- `switch`
- `ls`
- `close`
- `reopen`
- `publish`
- `status`
- `interrupt`

Namespaced subcommands such as `thread`, `config`, and `audit` are for management surfaces.

## Why `kk`

`kk` sits beside `jj` on the home row. That is useful ergonomically and symbolically: kiki works with jj rather than hiding it.

The name also points at kiki as a gathering: multiple lines of work, multiple agents, and a human engineer sharing a space without stepping on one another. The product should retain that spirit. It can be precise without becoming sterile.
