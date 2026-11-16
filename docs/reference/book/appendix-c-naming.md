# Appendix C: Naming

The tool is named **kiki**. The command is `kk`.

## Names

This list gives the exact name of each program, directory, and file that belongs to kiki.

- Tool name: `kiki`
- CLI binary: `kk`. A CLI is a command-line interface: a program you run by typing in a terminal. See [`kk`](appendix-a-glossary.md#kk).
- Daemon binary: `kkd`. A [daemon](appendix-a-glossary.md#ext-daemon) is a program that runs in the background. See [`kkd`](appendix-a-glossary.md#kkd).
- Hook sidecar: `kk-hook`. It is the small program that a managed [harness](appendix-a-glossary.md#harness) (the program that runs a coding agent) calls at its [hook](appendix-a-glossary.md#ext-hook) points. For the managed harness adapters, it handles exclusive `PreToolUse` admission plus `PostToolBatch` completion reporting. See [`kk-hook`](appendix-a-glossary.md#kk-hook) and [PreToolUse / PostToolBatch hooks](appendix-a-glossary.md#pretooluse-posttoolbatch-hooks).
- User state directory: `~/.config/kiki/`
- User config: `~/.config/kiki/config.toml`. The file is written in [TOML](https://toml.io/), a simple format for settings.
- Per-repo state and repo-local config, both kept outside the repository: `~/.config/kiki/repos/<repo_id>/`. This location is centralized: the source repo's filesystem holds no kiki state.
- Generated [Herdr](appendix-a-glossary.md#herdr) configuration: `~/.config/kiki/herdr/config.toml`. Herdr is the [terminal multiplexer](appendix-a-glossary.md#ext-terminal-multiplexer) that hosts kiki's terminals.
  - `[paths] herdr_dir` holds only this file.
  - The [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) is the Herdr session named `kiki` by default.
  - Herdr keeps that session's socket and saved state under its own directories.
- Repo-shared committed config: `<repo>/.kiki.toml`. This is the only kiki file that lives inside the source repo, and it is there only when the team commits one.

## Command style

Daily-driver verbs are the commands you use every day. They should be short and single-word:

- `init`
- `new`
- `attach`
- `switch`
- `ls`
- `log`
- `status`
- `close`
- `reopen`
- `repair`
- `publish`

Namespaced subcommands such as `thread`, `config`, and `audit` are for management surfaces. A namespaced subcommand is a command grouped under another word, and `kk thread interrupt` is one.

One subcommand is hidden and internal: `kk ui-pane`. Only the `ui` [pane launcher](appendix-a-glossary.md#pane-launcher) runs it, to draw the optional UI pane. People do not type it.

Two commands contain the word "attach", and the two are unrelated:

- `kk attach` opens a terminal view on kiki's Herdr server.
- `kk thread attach` is the namespaced command for the [follows](appendix-a-glossary.md#follows) graph (the links between a [thread](appendix-a-glossary.md#thread) and its parent thread). It is deferred.

See [Commands](09-commands.md) for what each command does.

## Why `kk`

`kk` sits beside `jj` on the home row of the keyboard. [jj](appendix-a-glossary.md#ext-jj) is the version-control tool that kiki works with. The closeness is useful for typing. It is also a symbol: kiki works with jj and does not hide it.

The name also points at kiki as a gathering: multiple lines of work, multiple agents, and a human engineer sharing a space without stepping on one another. The product should retain that spirit. It can be precise without becoming sterile.
