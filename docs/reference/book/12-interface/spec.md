# Interface

The TUI is v1.x polish, not acceptance slice (see [Orientation](../01-orientation.md)). This is the v1 contract if it ships. The TUI is a ratatui-rendered process: `kk` opens it inline, and the persistent sidebar runs as a separate ratatui process inside its own tmux pane. kiki always shows the real agent PTY.

## Vocabulary

- **Overlay** — the full-screen TUI invoked by bare `kk` (inside a registered repo) or tmux `prefix+k`. Transient. Dismissed on switch, on `q` or `esc`, or on completing a verb. Outside a registered repo, bare `kk` falls back to the command summary plus `kk ls` (see [Commands](../11-commands.md)).
- **Persistent sidebar** — an opt-in tmux pane spawned at thread birth. Always-on, navigation-only. Lives next to the agent pane until the user kills it.
- **Shell pane** — an opt-out tmux pane spawned at thread birth, running the user's `$SHELL` at the workspace cwd, laid out alongside the agent pane in the same tmux window (default position: below; configurable to the right). The pane kiki manages — singular — so direct `jj` / `gh` / test invocations live alongside the agent without leaving the thread. Detailed semantics in [Shell pane](#shell-pane).
- **Stack section** — the threads in the current repo, rendered as a follows-aware tree in `kk log` order. Cursor moves here for navigation.
- **Activity section** — the same threads, flat-listed by most-recent agent event (descending). Cursor moves here for triage.
- **Preview pane** — the right two-thirds of the overlay. Renders one of: transcript tail, working-copy diff, PR comments. Toggled by `t` / `d` / `c`.
- **Chord ribbon** — a one-line keybinding hint at the bottom edge of the overlay. Toggled by `?`. Adapts to current selection (e.g. hides `c` for a thread without a PR).
- **Inlined status** — the per-thread status block the Stack section renders under the _current_ thread's bookmark line. Reuses `StatusRenderer --no-jj` byte-identically with `kk status` (see [Commands](../11-commands.md)). Single source of truth.
- **Context strip** — the bottom-most line of the overlay or the persistent sidebar pane. One compressed sentence with TUI-specific content. Two forms by context: the overlay form carries repo + bookmark + cascade glyph + agent model + ctx % + last op age; the persistent-sidebar form is shorter (bookmark + cascade glyph + agent glyph) because the agent pane next to it already surfaces model and ctx. This is a TUI footer, separate from the `StatusRenderer`-backed inlined status.
- **Toast** — a non-modal floating pill in the overlay's top-right corner. Used for cascade events, agent finish/error notifications, auto-archive-on-PR-merge undo prompts, and config-set warnings. Auto-dismisses after `[ui] toast_ttl_ms` (default 4000) or its trigger-specific TTL (e.g., the auto-archive undo grace is 5000ms, overriding the default — see [Publishing](../09-publishing.md)). Carries at most one optional named action (e.g., `undo`); never opens a confirmation card.
- **Card** — a centered modal panel with title, body, and one or two action buttons. Used for spawn and destructive confirmation.

## Glyph language

Two glyphs per row, max. PR appears inline as `#NNNN` only if set.

| state               | glyph | color  |
| ------------------- | ----- | ------ |
| cascade in sync     | `──`  | dim    |
| cascade pending     | `●●○` | amber  |
| cascade conflicted  | `◐`   | red    |
| agent idle          | `○`   | dim    |
| agent working       | `●`   | amber  |
| agent finished      | `✓`   | green  |
| agent blocked       | `◐`   | red    |
| follows arrow       | `←●`  | dim    |
| current thread mark | `▸`   | accent |

The cascade indicator uses the same three-valued state model as `kk status` (`in sync`, `pending`, `conflicted`). The agent-state indicator uses the harness state model (`idle`, `working`, `finished`, `blocked`). The CLI prints the textual cascade state described in [Commands](../11-commands.md); the TUI projects cascade and agent states to glyphs from the table above.

Every state in this table must be distinguishable by glyph alone, not by color. Color is an accelerator: it makes scanning faster, but `NO_COLOR=1` and color-blind palettes must still convey the state. The `LogRenderer` and `StatusRenderer` projections strip color when `NO_COLOR=1` is set in the environment and rely on glyph + label to carry the signal. See [Invariants](../04-invariants.md).

## Overlay

Bare `kk` or tmux `prefix+k` opens the overlay in `NAVIGATE` mode, focused on the current thread (resolved via the standard CLI context-resolution chain). If no current thread resolves but the repo is registered, the cursor lands on the most-recently-active thread in the repo. If the repo has no threads, the overlay shows an empty-state placeholder ("no threads — press `n` to create one") with `n` and `?` as the only active verbs.

The overlay is one screen, three regions stacked vertically:

1. Top: a single-line breadcrumb — `kiki · NAVIGATE · <repo>/<thread>`.
2. Middle: a fixed-width left sidebar (Stack on top, Activity on bottom) and a flexible-width right preview pane.
3. Bottom: a one-line context strip; an optional chord ribbon hovers above it when `?` is held.

### Wireframe — bare overlay open

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui                               ?  esc

 STACK                              │  pi-extensions/codex-conv-tui
                                    │
 ● main             ──    in        │  bookmark    pi-extensions/codex-conv-tui
 │                                  │  cascade     ── in sync
 ●─pi/refactor      ●●○   wrk       │  agent       ● working   2m 18s
 │                                  │  pr          #482 draft  ●●●●● ci green
 ●─pi/codex-conv ▸  ●●●   ←●        │  follows     pi/refactor → main
 │                                  │  workspace   ~/code/pi-extensions-kiki-codex-conv
 ●─pi/agent-tui     ○     idle      │
                                    │  ─ preview ────────────────────────────────────
 ACTIVITY                           │
                                    │   t  transcript tail
 ● codex-conv     working   2m18s   │   d  working-copy diff
 ● refactor       working    34s    │   c  PR #482 comments
 ◐ session-recall conflicted        │
 ○ agent-tui      idle     1h12m    │
 ✓ minimal-foot   finished   8m     │
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  master ✻  ── in sync  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

### Wireframe — `t` opens transcript tail in the preview pane

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui                              ?  esc

 STACK                              │  transcript · pi-extensions/codex-conv-tui · tail
                                    │
 ● main             ──    in        │  human  2m 18s ago
 │                                  │   could you check whether the cascade outbox row
 ●─pi/refactor      ●●○   wrk       │   is dropped on a hook crash before MarkDelivered?
 │                                  │
 ●─pi/codex-conv ▸  ●●●   ←●        │  agent  2m 04s ago
 │                                  │   reading kiki-core/cascade/outbox.rs ... I see
 ●─pi/agent-tui     ○     idle      │   the row is keyed on applied_cascade_seq >
                                    │   acknowledged_cascade_seq, so a crash before
 ACTIVITY                           │   MarkDelivered re-enters the same row. Want me
                                    │   to add a regression test for that path?
 ● codex-conv     working   2m18s   │
 ● refactor       working    34s    │  human  18s ago
 ◐ session-recall conflicted        │   yes — match the testing.md cascade list
 ○ agent-tui      idle     1h12m    │
 ✓ minimal-foot   finished   8m     │  ── more above (T to open full reader) ─────────
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  master ✻  ── in sync  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

`T` (shift-t) escalates from preview-tail to a full-screen `kk thread transcript` reader. `esc` returns to overlay.

### Wireframe — `d` shows working-copy diff

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui                              ?  esc

 STACK                              │  diff · pi-extensions/codex-conv-tui · jj st --diff
                                    │
 ● main             ──    in        │  M  kiki-core/src/cascade/outbox.rs   +14 -2
 │                                  │  M  kkd/src/services/cascade.rs       +6  -0
 ●─pi/refactor      ●●○   wrk       │  ?  tests/cascade/crash_before_md.rs  +88
 │                                  │  ─────────────────────────────────────────────
 ●─pi/codex-conv ▸  ●●●   ←●        │  diff --git a/kiki-core/src/cascade/outbox.rs
 │                                  │  +pub fn lookup_pending(&self) -> Option<Row> {
 ●─pi/agent-tui     ○     idle      │  +    self.rows
                                    │  +        .iter()
 ACTIVITY                           │  +        .find(|r| r.applied_cascade_seq
                                    │  +              > r.acknowledged_cascade_seq)
 ● codex-conv     working   2m18s   │  +}
 ● refactor       working    34s    │  …
 ◐ session-recall conflicted        │
 ○ agent-tui      idle     1h12m    │
 ✓ minimal-foot   finished   8m     │  ── jj st --diff (use `kk status --diff` to script)
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  master ✻  ── in sync  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

### Wireframe — `c` shows PR comments

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui                              ?  esc

 STACK                              │  pr #482 · draft · pi-extensions/codex-conv-tui
                                    │
 ● main             ──    in        │  base  main
 │                                  │  ci    ●●●●● green   ci.yaml passed 1m ago
 ●─pi/refactor      ●●○   wrk       │
 │                                  │  ─ comments ─────────────────────────────────
 ●─pi/codex-conv ▸  ●●●   ←●        │
 │                                  │  @ogul  18m ago  on cascade/outbox.rs:42
 ●─pi/agent-tui     ○     idle      │   nit: drop the lookup_pending wrapper, use
                                    │   the closure inline?
 ACTIVITY                           │
                                    │  @sandile  12m ago
 ● codex-conv     working   2m18s   │   prefer keeping the named fn so the test name
 ● refactor       working    34s    │   reads. ok to keep?
 ◐ session-recall conflicted        │
 ○ agent-tui      idle     1h12m    │  (no transcript leakage — comments are gh,
 ✓ minimal-foot   finished   8m     │   not the local transcript store)
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  master ✻  ── in sync  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

### Wireframe — chord ribbon visible (`?` toggled)

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui                              ?  esc

 STACK                              │  pi-extensions/codex-conv-tui
                                    │  …
 ● main             ──    in        │
 │                                  │
 ●─pi/refactor      ●●○   wrk       │
 │                                  │
 ●─pi/codex-conv ▸  ●●●   ←●        │
 │                                  │
 ●─pi/agent-tui     ○     idle      │
                                    │
 ACTIVITY                           │
                                    │
 ● codex-conv     working   2m18s   │
 ● refactor       working    34s    │
 ◐ session-recall conflicted        │
 ○ agent-tui      idle     1h12m    │
 ✓ minimal-foot   finished   8m     │
 ── nav ↑↓ · ⏎ switch · space preview · t/d/c view · n new · N child · p publish · x
    close · i interrupt · T transcript reader · ? help · esc dismiss
 pi-extensions  master ✻  ── in sync  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

The ribbon adapts to selection. For a closed thread, `i`, `p`, and `x` drop out and `r` (reopen — see keymap below) appears. For a thread without a PR, `c` (preview comments) drops out independently.

### Wireframe — destructive confirmation card (`x` close on cursored thread)

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui                              ?  esc

 STACK                              │  pi-extensions/codex-conv-tui
                                    │
 ● main             ──    in        │  …
 │                                  │
 ●─pi/refactor      ●●○   wrk       │   ╭─ Close pi-extensions/codex-conv-tui? ───╮
 │                                  │   │                                          │
 ●─pi/codex-conv ▸  ●●●   ←●        │   │  Stops the agent and tmux session.       │
 │                                  │   │  Forgets the jj workspace and removes    │
 ●─pi/agent-tui     ○     idle      │   │  ~/code/pi-extensions-kiki-codex-conv.   │
                                    │   │  Tracked jj revisions are kept.          │
 ACTIVITY                           │   │  PR #482 is left open (use --discard-pr).│
                                    │   │                                          │
 ● codex-conv     working   2m18s   │   │   ⏎  Close      esc  Cancel              │
 ● refactor       working    34s    │   ╰──────────────────────────────────────────╯
 ◐ session-recall conflicted        │
 ○ agent-tui      idle     1h12m    │
 ✓ minimal-foot   finished   8m     │
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  master ✻  ── in sync  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

`i` (interrupt) shows the same shape; the body changes. Both require an explicit `enter` — there is no chord that fires destructive verbs in one keystroke.

### Wireframe — spawn card (`n` for new thread, `N` for new-as-child-of-cursored)

```
 kiki · SPAWN · child of pi-extensions/codex-conv-tui                          esc

   ╭─ New thread ────────────────────────────────────────────────────────────────╮
   │                                                                              │
   │  name        pi/cascade-recovery_                                            │
   │  follows     pi-extensions/codex-conv-tui  (─ no follow)                     │
   │  agent       claude-code   (default — change in user config)                 │
   │  sidebar     ●  on   ○  off   (default: on, from [ui] persistent_sidebar)   │
   │                                                                              │
   │   ⏎  Spawn      esc  Cancel                                                  │
   ╰──────────────────────────────────────────────────────────────────────────────╯
```

`n` opens this with `follows` set to "── no follow" by default. `N` opens it with `follows` set to the cursored thread.

## Persistent sidebar pane

The persistent sidebar is opt-in via `[ui] persistent_sidebar = true` in user config, or per-thread via `kk new --sidebar` / `--no-sidebar`. It is spawned at thread birth and re-ensured idempotently at `kk switch` / `kk reopen`. If the user kills the pane within a live session, kiki does not auto-respawn.

It renders the same Stack + Activity content as the overlay's sidebar, in a narrower fixed-width pane. It is **navigation-only**: `j` / `k` / `↑` / `↓` move the cursor, `tab` jumps the cursor between Stack and Activity, `enter` switches to the cursored thread, `?` toggles the chord ribbon (showing only the navigation verbs), `q` returns focus to the agent pane. Mouse click on a row moves the cursor; scroll-wheel scrolls the section. Spawn, publish, close, destroy, interrupt, reopen, and preview-toggle are not bound — accidental focus on the sidebar pane (a real tmux focus accident) cannot mutate state.

If the terminal is narrower than `[ui] sidebar_min_terminal_cols` (default 100), kiki skips sidebar creation and logs a warning at thread birth.

### Wireframe — persistent sidebar pane in tmux (32-col pane default, configurable via `[ui] sidebar_width`; agent pane to the right)

```
 ╭─ kiki ──────────────────────╮ ╭─ codex-conv-tui ─────────────────────────────────╮
 │                             │ │                                                  │
 │ STACK                       │ │ > human                                          │
 │                             │ │   could you check whether the cascade outbox    │
 │ ● main          ──    in    │ │   row is dropped on a hook crash before          │
 │ │                           │ │   MarkDelivered?                                 │
 │ ●─pi/refactor   ●●○  wrk    │ │                                                  │
 │ │                           │ │ ● working   2m 18s   esc to interrupt            │
 │ ●─pi/codex ▸    ●●●  ←●     │ │                                                  │
 │ │                           │ │   reading kiki-core/cascade/outbox.rs ...        │
 │ ●─pi/agent     ○     idle   │ │                                                  │
 │                             │ │                                                  │
 │ ACTIVITY                    │ │                                                  │
 │                             │ │                                                  │
 │ ● codex     wrk    2m18s    │ │                                                  │
 │ ● refactor  wrk     34s     │ │                                                  │
 │ ◐ session   conflict        │ │                                                  │
 │ ○ agent     idle  1h12m     │ │                                                  │
 │ ✓ minimal   ✓        8m     │ │                                                  │
 │ ─────────────────────────── │ │                                                  │
 │ ↑↓ ⇄ ⏎ switch · q · ?       │ │                                                  │
 │ master ✻  ── in sync  ●     │ │                                                  │
 ╰─────────────────────────────╯ ╰──────────────────────────────────────────────────╯
```

The sidebar's context strip is shorter than the overlay's: just bookmark + dirty + cascade glyph + agent dot. Model and ctx-% are omitted because they are agent-pane state and the agent pane already shows them. The per-row inlined status under the current thread's bookmark line is unchanged from the overlay — same `StatusRenderer --no-jj` projection.

## Shell pane

The shell pane is a kiki-spawned tmux pane running the user's shell at the thread's workspace cwd. It exists so the user can interact directly with the same jj workspace the agent is operating in — running `jj`, `gh`, tests, or any other command — without leaving the thread's tmux session. The agent pane and the shell pane share a working copy; what one writes the other sees.

The shell pane is on by default (`[ui] shell_pane = true`). It is opt-out, not opt-in, because direct shell access alongside the agent is an expected component of the kiki experience, not an extra. When opted out, the thread's session contains only the agent pane (and the persistent sidebar pane, if that is also enabled).

In kiki's vocabulary, **the** shell pane is the singular pane kiki creates at thread birth. If the user runs `tmux split-window` to add additional panes, those are just tmux panes — kiki neither manages them nor refers to them as shell panes. Re-ensure logic on `kk switch` / `kk reopen` only ever looks for and creates the one kiki-managed shell pane.

### Layout

The shell pane lives in the same tmux window as the agent pane. By default it sits in a horizontal split below the agent (the agent on top, the shell on the bottom). Configurable via `[ui] shell_pane_position` (`below` | `right`, default `below`) and `[ui] shell_pane_size_pct` (int, default `25`).

`shell_pane_size_pct` is read as "the percentage of the dimension the split divides" — height when `position = below`, width when `position = right` — so the same key produces the analogous proportion under either orientation. Under the default `below` + `25`, the agent occupies the top 75% of height and the shell the bottom 25%; under `right` + `25`, the agent occupies 75% of width on the left and the shell 25% on the right. The shell pane never escapes the agent's tmux window — the agent and shell are co-resident in one window by design, so the user can see one while interacting with the other.

The four layout combinations of `[ui] persistent_sidebar` × `[ui] shell_pane`, shown with the default `shell_pane_position = below`:

| `persistent_sidebar` | `shell_pane` | layout                                                                      |
| -------------------- | ------------ | --------------------------------------------------------------------------- |
| `true`               | `true`       | sidebar left (32 cols) · agent top-right (~75%) · shell bottom-right (~25%) |
| `false`              | `true`       | agent top (~75%) · shell bottom (~25%) — full width                         |
| `true`               | `false`      | sidebar left (32 cols) · agent right (full height)                          |
| `false`              | `false`      | agent only — full window                                                    |

Under `shell_pane_position = right`, the agent / shell rows flip orientation: the shell sits to the right of the agent (taking `shell_pane_size_pct` of width), and the sidebar — when present — still occupies the leftmost 32 cols. The sidebar's position is fixed; only the shell pane's position is configurable.

Initial focus at thread birth lands on the agent pane so the developer can interact with the harness's first turn. Pane focus across `kk switch` follows tmux's default behavior (last-focused pane on the session before detach), so kiki does not override user muscle memory.

### Wireframe — default thread tmux layout (sidebar + agent + shell)

```
 ╭─ kiki ──────────────────────╮ ╭─ codex-conv-tui ─────────────────────────────────╮
 │                             │ │                                                  │
 │ STACK                       │ │ > human                                          │
 │                             │ │   could you check whether the cascade outbox    │
 │ ● main          ──    in    │ │   row is dropped on a hook crash before          │
 │ │                           │ │   MarkDelivered?                                 │
 │ ●─pi/refactor   ●●○  wrk    │ │                                                  │
 │ │                           │ │ ● working   2m 18s   esc to interrupt            │
 │ ●─pi/codex ▸    ●●●  ←●     │ │                                                  │
 │ │                           │ │   reading kiki-core/cascade/outbox.rs ...        │
 │ ●─pi/agent     ○     idle   │ ╰──────────────────────────────────────────────────╯
 │                             │ ╭─ shell ──────────────────────────────────────────╮
 │ ACTIVITY                    │ │ ~/code/pi-extensions-kiki-codex-conv $ jj st     │
 │                             │ │ M  kiki-core/src/cascade/outbox.rs               │
 │ ● codex     wrk    2m18s    │ │ Working copy : qxnopkyl 8a3c2d1e                 │
 │ ● refactor  wrk     34s     │ │ ~/code/pi-extensions-kiki-codex-conv $ _         │
 │ ◐ session   conflict        │ │                                                  │
 │ ○ agent     idle  1h12m     │ │                                                  │
 │ ✓ minimal   ✓        8m     │ │                                                  │
 │ ─────────────────────────── │ │                                                  │
 │ ↑↓ ⇄ ⏎ switch · q · ?       │ │                                                  │
 │ master ✻  ── in sync  ●     │ │                                                  │
 ╰─────────────────────────────╯ ╰──────────────────────────────────────────────────╯
```

The sidebar pane (left) is the persistent navigation surface; the agent pane (top-right) hosts the harness's PTY; the shell pane (bottom-right) hosts the user's shell at the workspace cwd. The wireframe shows the default `shell_pane_position = below`; under `right`, the shell pane swaps to a vertical band to the right of the agent. When `[ui] persistent_sidebar = false`, the sidebar region drops and the agent + shell expand to fill the window. When `[ui] shell_pane = false`, the shell region drops and the agent fills its column.

### Lifecycle

- **`kk new`**: spawns the shell pane if `[ui] shell_pane = true` and the terminal is at least `[ui] shell_pane_min_rows` tall, with cwd set to the workspace path and the shell process taken from `$SHELL` (fallback `/bin/sh`). No environment variables are injected; the shell inherits the parent env unchanged.
- **`kk switch <thread>`**: re-ensures the shell pane idempotently. If the pane is present, no-op. If absent (the session was just attached, or the pane was killed before the previous detach), kiki recreates it fresh at the workspace cwd.
- **`kk reopen <thread>`**: as `kk new` — the pane is spawned fresh. Shell history, scrollback, and any processes that were running before close are not preserved; the user's shell starts cold.
- **`kk close`**: the tmux session is killed, and the shell pane goes with it. Any process running in the shell pane is killed alongside the agent. See [Threads · close](../05-threads.md#close).
- **User kills the pane mid-session**: kiki does not auto-respawn it within the same continuous attach. The next `kk switch` or `kk reopen` re-ensures it.

The pane is transparent to kkd after spawn in v1. The daemon does not track which process is running in it, does not surface its state in the TUI or sidebar, and does not log audit rows for activity in it. Anything kiki cares about that the user does in the shell pane — direct jj operations, gh interactions — routes through the existing op-log watcher and GitHub polling paths as if the user had run it anywhere else. This is the ambient-coordinator stance applied to the shell pane: kiki sets it up, then gets out of the way. Future versions may promote the shell pane to a tracked surface; v1 commits only to spawn, re-ensure, and degrade.

### Degradation

If the terminal has fewer rows than `[ui] shell_pane_min_rows` (default `24`) at thread birth, kiki skips spawning the shell pane and logs a warning, mirroring the persistent sidebar's `sidebar_min_terminal_cols` skip-and-warn rule. The same threshold check runs idempotently at `kk switch` / `kk reopen`, so resizing the terminal larger and switching back picks up the shell pane on the next event. Resizing smaller after birth does not retroactively kill the pane.

### Authority

The shell pane runs the user's shell process at the user's UID; kiki passes no thread-scoped credential into it. When the user invokes `kk` from inside the shell pane, the `kk` binary reads `~/.kiki/admin-cred` exactly as it does from any other terminal — the same context-resolution chain (env → tmux session name → cwd) auto-discovers the thread. See [Authority](../06-authority.md).

## Toasts

Toasts are non-modal pills in the overlay's top-right corner, stacking downward. Each carries one line of summary text: glyph, thread name, event, elapsed.

Two subtypes share the surface:

- **Notification toast** — no interactive action. The body may include hint text naming an overlay verb (e.g., "tap T to read transcript"); the verb is fielded by the overlay's normal keymap, the toast does not intercept it.
- **Actionable toast** — carries exactly one named action (e.g., `undo`). The action is invoked by clicking the action label, or by pressing the named key while the toast is the most-recent unactioned toast (this is the _only_ keystroke a toast intercepts; everything else passes through to the overlay). The action is never destructive — it is restorative (`undo` of a kiki-initiated mutation, e.g., auto-archive on PR-merge — see [Publishing](../09-publishing.md)). Toasts never open a confirmation card.

Dismissal rules (apply to both subtypes):

- auto-dismiss after the toast's TTL elapses (default `[ui] toast_ttl_ms` = 4000ms; specific triggers may override, e.g., auto-archive undo grace = 5000ms — see [Publishing](../09-publishing.md))
- click anywhere on the toast pill (excluding the action label, which runs the action) dismisses it
- moving the keyboard cursor onto the row that issued the toast, or clicking that row, dismisses the toast (treated as "user acknowledged")
- invoking the toast's action (actionable toasts only) dismisses the toast on completion

Toast triggers (v1):

- agent finish (`✓`) — notification
- agent error / blocked (`◐`) — notification
- cascade conflict on a non-current thread (`◐`) — notification
- cascade applied to a child thread (`──`, only when ≥ 2 children rebased to coalesce noise) — notification
- config-set warning that won't take effect until next `kk new` / `kk reopen` — notification
- auto-archive on PR-merge (`✓`) with `undo` action (v1.x polish; 5s grace — see [Publishing](../09-publishing.md)) — actionable

Toasts are overlay-only. The persistent sidebar is navigation-only, and stacking toast UI beside the live agent pane would be ambiguous. When the overlay is closed, OS-native notifications (configured via `[notifications]` — see [Configuration](../13-configuration.md)) carry the same events.

### Wireframe — conflicted-thread toast in overlay

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui     ┌─────────────────────────────┐
                                                    │ ◐ session-recall conflicted │
 STACK                                              │   tap T to read transcript  │
                                                    └─────────────────────────────┘
 ● main             ──    in
 │
 ●─pi/refactor      ●●○   wrk
 │
 ●─pi/codex-conv ▸  ●●●   ←●
 │
 ●─pi/agent-tui     ○     idle
 │
 ●─pi/session-recall ◐    conflict

 …
```

## Forms

Spawn and confirmation cards are the only v1 forms. Both:

- center on screen
- have a single labeled title row, a body, and one or two action buttons
- accept `enter` for the primary action and `esc` for cancel
- accept `tab` and `shift+tab` to move between fields, when there is more than one field

Forms are pure ratatui widgets; they call `kkd` only after `enter`. The card surface stays inside the overlay process.

## Keymap

## Overlay state machine

The overlay is a small state machine:

- `NAVIGATE`: default state. Sidebar cursor moves through Stack and Activity rows.
- `PREVIEW`: right pane is pinned to transcript tail, diff, or PR comments for the cursored thread.
- `CONFIRM`: destructive verbs such as close or interrupt wait for explicit confirmation.
- `SPAWN`: spawn form collects thread name, follows target, and harness fields.
- `VIEWER`: full-screen transcript reader opened by `T`.

`q` and `esc` leave the overlay from `NAVIGATE` and return to the prior overlay state from sub-states. `enter` only switches threads from `NAVIGATE` on a bookmark row. Destructive actions are unavailable from the persistent sidebar pane.

Overlay (`NAVIGATE` mode):

| key       | verb                                                                            |
| --------- | ------------------------------------------------------------------------------- |
| `↑` / `k` | move cursor up                                                                  |
| `↓` / `j` | move cursor down                                                                |
| `tab`     | jump cursor between Stack and Activity                                          |
| `enter`   | switch to cursored thread (dismisses overlay)                                   |
| `space`   | toggle preview pane on the cursored thread                                      |
| `t`       | preview-mode = transcript tail                                                  |
| `d`       | preview-mode = working-copy diff                                                |
| `c`       | preview-mode = PR comments (preview only — not close)                           |
| `T`       | open full-screen transcript reader                                              |
| `n`       | spawn modal (new thread, no follow)                                             |
| `N`       | spawn modal (new thread, follows cursored)                                      |
| `p`       | publish cursored thread (`kk publish`)                                          |
| `x`       | close cursored thread (opens confirmation card)                                 |
| `i`       | interrupt cursored thread's agent (opens confirmation card)                     |
| `r`       | reopen cursored thread (only meaningful when thread is closed; otherwise no-op) |
| `?`       | toggle chord ribbon                                                             |
| `q`       | dismiss overlay                                                                 |
| `esc`     | dismiss overlay                                                                 |
| click     | (mouse) move cursor to clicked row, or switch preview tab                       |
| scroll    | (mouse) scroll the focused pane (sidebar list or preview)                       |

Note: `c` previews PR comments. Close is `x`. The binding favors the frequent read action and keeps closing behind a distinct key.

Persistent sidebar pane:

| key             | verb                                |
| --------------- | ----------------------------------- |
| `↑` `↓` `j` `k` | move cursor                         |
| `tab`           | jump between Stack and Activity     |
| `enter`         | switch to cursored thread           |
| `?`             | toggle chord ribbon (read-only set) |
| `q`             | return focus to agent pane          |
| click           | move cursor to clicked row          |
| scroll          | scroll the section                  |

The sidebar binds **no** verb that mutates state. Spawn, publish, close, destroy, interrupt, and preview-toggle are unbound.

## Context strip

One line at the bottom of the overlay. Order, left to right:

`<repo>  <bookmark>[*]  <cascade-glyph cascade-state>  <agent-model>  ctx ●●●●○ <pct>%  last op <duration>`

`*` is the dirty marker for the current thread's working copy. `<cascade-glyph cascade-state>` is the kiki-CLI-shared three-valued indicator. `<agent-model>` is the harness-reported model name. `ctx` is the harness-reported context-window utilization. `last op` is the duration since the last jj op on the current thread.

The persistent sidebar's context strip is a shortened form: `<bookmark>[*]  <cascade-glyph cascade-state>  <agent-glyph>`. Model and ctx are omitted because the agent pane next to it already surfaces them.

The context strip is a TUI-specific footer and is **not** a `StatusRenderer` projection. The `StatusRenderer`-fed artifact is the _inlined status_ under the current thread's bookmark line in the Stack section; that artifact is byte-identical with `kk status --no-jj` per `testing.md` (`StatusRenderer` shared-renderer test).

## Degradation

If the terminal is narrower than `[ui] overlay_min_cols` (default 80) at the moment `kk` is invoked, the overlay refuses to open and prints `kk ls` output instead, with a warning. There is no half-overlay state.

If the terminal is narrower than `[ui] sidebar_min_terminal_cols` (default 100) at thread creation, the persistent sidebar pane is skipped and a warning is logged at `kk new` time. The same skip applies idempotently at later `kk switch` / `kk reopen` (the ensure-pane check is a silent no-op in that case — no re-warning). The overlay is still available via bare `kk`.

If a row is too narrow to render the full glyph + name + status, the name is truncated with a single-character ellipsis (no multi-character `…` wrap). Collapsed-summary lines from `kk log` follow the existing CLI rules.

## Mouse

Mouse capture is on by default (`[ui] mouse_enabled = true`). The following events are honored in v1:

- click on a sidebar row → moves cursor to that row, equivalent to navigating with arrows; if the row issued a still-active toast, that toast also dismisses
- click on a preview-tab letter (`t` / `d` / `c`) in the preview pane header → switches preview mode, equivalent to pressing the corresponding key
- click on a toast pill, anywhere except the action label → dismisses that toast (notification toasts have no action label and dismiss on any click; actionable toasts dismiss everywhere except the labeled action)
- click on a toast's named action label (actionable toasts only) → invokes the action and dismisses the toast on completion
- scroll wheel on a focused pane → scrolls that pane

Drag, drag-resize, right-click context menus, click-and-drag selection, and hover/motion-driven UI are explicitly **out of v1 scope**. tmux owns the outer multiplexer; kiki does not contend with tmux's mouse mode for pane manipulation.

If `[ui] mouse_enabled = false`, kiki does not request mouse capture from the terminal and falls back to keyboard-only behavior.

## Configuration

`[ui]` keys introduced or referenced by this spec:

- `persistent_sidebar` (bool, default `false`) — covered in [Configuration](../13-configuration.md)
- `sidebar_width` (int, default `32`)
- `sidebar_min_terminal_cols` (int, default `100`)
- `shell_pane` (bool, default `true`)
- `shell_pane_position` (string, default `"below"`)
- `shell_pane_size_pct` (int, default `25`)
- `shell_pane_min_rows` (int, default `24`)
- `mouse_enabled` (bool, default `true`)
- `overlay_min_cols` (int, default `80`)
- `toast_ttl_ms` (int, default `4000`)
- `theme` (string, default `"soft-dark"`)

All `[ui]` keys are personal preference: valid in user and per-thread config, invalid in repo-shared config (warned-and-ignored). Hot-reload semantics (matching [Configuration](../13-configuration.md)):

- `mouse_enabled`, `toast_ttl_ms`, and `theme` are cosmetic and hot-reload.
- `persistent_sidebar`, `sidebar_width`, `sidebar_min_terminal_cols`, `shell_pane`, `shell_pane_position`, `shell_pane_size_pct`, `shell_pane_min_rows`, and `overlay_min_cols` take effect on the next lifecycle event (`kk new`, `kk reopen`, `kk switch`, or next overlay open, depending on the key) — they do not retroactively reshape live sessions.
