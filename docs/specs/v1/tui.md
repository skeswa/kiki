# TUI spec

The TUI is not required for the first core implementation slice, but this is the v1 contract if it ships.

## Overlay

Bare `kk` or tmux `prefix+k` opens an overlay with:

- left sidebar using the same stack-aware renderer as `kk log`
- current thread status inlined under its bookmark line
- right preview pane for transcript tail, diff, or PR comments

Overlay keybindings include navigation, preview, spawn, publish, close, interrupt, transcript reader, help, and dismiss.

Destructive actions require confirmation.

## Persistent sidebar

The persistent sidebar is opt-in through user config or per-thread creation flags.

It is navigation-only:

- move cursor
- switch to selected thread
- help
- return focus / quit pane UI

It does not bind spawn, publish, close, destroy, or interrupt.

If the terminal is narrower than `sidebar_min_terminal_cols`, kiki skips sidebar creation and logs a warning.

If the user kills the sidebar pane within a live session, kiki does not auto-respawn it until the next switch or reopen.
