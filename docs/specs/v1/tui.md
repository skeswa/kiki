# TUI spec

The TUI is not required for the first core implementation slice. This is the v1 contract if it ships. The TUI is a ratatui-rendered process — `kk` opens it inline; the persistent sidebar runs as a separate ratatui process inside its own tmux pane. The agent pane is never reinterpreted: kiki always shows the real PTY.

## Vocabulary

- **Overlay** — the full-screen TUI invoked by bare `kk` (inside a registered repo) or tmux `prefix+k`. Transient. Dismissed on switch, on `q` or `esc`, or on completing a verb. Outside a registered repo, bare `kk` does not open the overlay; it falls back to the command summary plus `kk ls` (see `cli.md`).
- **Persistent sidebar** — an opt-in tmux pane spawned at thread birth. Always-on, navigation-only. Lives next to the agent pane until the user kills it.
- **Stack section** — the threads in the current repo, rendered as a follows-aware tree in `kk log` order. Cursor moves here for navigation.
- **Activity section** — the same threads, flat-listed by most-recent agent event (descending). Cursor moves here for triage.
- **Preview pane** — the right two-thirds of the overlay. Renders one of: transcript tail, working-copy diff, PR comments. Toggled by `t` / `d` / `c`.
- **Chord ribbon** — a one-line keybinding hint at the bottom edge of the overlay. Toggled by `?`. Adapts to current selection (e.g. hides `c` for a thread without a PR).
- **Inlined status** — the per-thread status block the Stack section renders under the _current_ thread's bookmark line. Reuses `StatusRenderer --no-jj` byte-identically with `kk status` (see `cli.md`). Single source of truth.
- **Context strip** — the bottom-most line of the overlay or the persistent sidebar pane. One compressed sentence with TUI-specific content. Two forms by context: the overlay form carries repo + bookmark + cascade glyph + agent model + ctx % + last op age; the persistent-sidebar form is shorter (bookmark + cascade glyph + agent glyph) because the agent pane next to it already surfaces model and ctx. Distinct from the inlined status — the context strip is a TUI footer, not a `StatusRenderer` projection.
- **Toast** — a non-modal floating pill in the overlay's top-right corner. Used for cascade events, agent finish/error notifications, auto-archive-on-PR-merge undo prompts, and config-set warnings. Auto-dismisses after `[ui] toast_ttl_ms` (default 4000) or its trigger-specific TTL (e.g., the auto-archive undo grace is 5000ms per PRD line 352, overriding the default). Carries at most one optional named action (e.g., `undo`); never opens a confirmation card.
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

The cascade indicator and the agent-state indicator share the same three-valued state model as `kk status` (`in sync`, `pending`, `conflicted`). The CLI prints the textual state per `cli.md`; the TUI projects each state to a glyph from the table above. The state model is the source of truth — the textual and glyph forms are two presentations.

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
 │                                  │  workspace   ~/code/pi-extensions.kiki/codex-conv
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
 ●─pi/agent-tui     ○     idle      │   │  ~/code/pi-extensions.kiki/codex-conv.   │
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

## Toasts

Toasts are non-modal pills in the overlay's top-right corner, stacking downward. Each carries one line of summary text: glyph, thread name, event, elapsed.

Two subtypes share the surface:

- **Notification toast** — no interactive action. The body may include hint text naming an overlay verb (e.g., "tap T to read transcript"); the verb is fielded by the overlay's normal keymap, the toast does not intercept it.
- **Actionable toast** — carries exactly one named action (e.g., `undo`). The action is invoked by clicking the action label, or by pressing the named key while the toast is the most-recent unactioned toast (this is the _only_ keystroke a toast intercepts; everything else passes through to the overlay). The action is never destructive — it is restorative (`undo` of a kiki-initiated mutation, e.g., auto-archive on PR-merge per PRD line 352). Toasts never open a confirmation card.

Dismissal rules (apply to both subtypes):

- auto-dismiss after the toast's TTL elapses (default `[ui] toast_ttl_ms` = 4000ms; specific triggers may override, e.g., auto-archive undo grace = 5000ms per PRD line 352)
- click anywhere on the toast pill (excluding the action label, which runs the action) dismisses it
- moving the keyboard cursor onto the row that issued the toast, or clicking that row, dismisses the toast (treated as "user acknowledged")
- invoking the toast's action (actionable toasts only) dismisses the toast on completion

Toast triggers (v1):

- agent finish (`✓`) — notification
- agent error / blocked (`◐`) — notification
- cascade conflict on a non-current thread (`◐`) — notification
- cascade applied to a child thread (`──`, only when ≥ 2 children rebased to coalesce noise) — notification
- config-set warning that won't take effect until next `kk new` / `kk reopen` — notification
- auto-archive on PR-merge (`✓`) with `undo` action (5s grace per PRD line 352) — actionable

Toasts do not appear in the persistent sidebar pane (which is navigation-only and would ambiguously stack with the agent pane below it). When the overlay is closed, OS-native notifications (configured via `[notifications]` per PRD lines 612-) carry the same events; the toast is the in-overlay analogue, not a replacement.

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

Forms are pure ratatui widgets; they do not call `kkd` until `enter` is pressed. The card surface stays inside the overlay process — there is no separate window.

## Keymap

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

Note: `c` is **preview-PR-comments**, not close. Close is `x`. The two are deliberately disjoint because `c` would otherwise collide with the more-frequent comments-preview action.

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

The sidebar binds **no** verb that mutates state. Spawn, publish, close, destroy, interrupt, and preview-toggle are deliberately unbound.

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

- `persistent_sidebar` (bool, default `false`) — covered in `config.md`
- `sidebar_width` (int, default `32`)
- `sidebar_min_terminal_cols` (int, default `100`)
- `mouse_enabled` (bool, default `true`)
- `overlay_min_cols` (int, default `80`)
- `toast_ttl_ms` (int, default `4000`)
- `theme` (string, default `"soft-dark"`)

All `[ui]` keys are personal preference: valid in user and per-thread config, invalid in repo-shared config (warned-and-ignored). Hot-reload semantics (matching `config.md`):

- `mouse_enabled`, `toast_ttl_ms`, and `theme` are cosmetic and hot-reload.
- `persistent_sidebar`, `sidebar_width`, `sidebar_min_terminal_cols`, and `overlay_min_cols` take effect on the next lifecycle event (`kk new`, `kk reopen`, or next overlay open) — they do not retroactively reshape live sessions.
