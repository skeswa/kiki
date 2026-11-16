# Interface

The interface surfaces in this chapter are v1.x polish unless [Orientation](../01-orientation.md) says otherwise; that chapter is the only scope ledger. This is the v1 contract for each surface when it ships.

Kiki's threads live in a dedicated Herdr server (see [Terminal runtime](../13-architecture/terminal-runtime.md)). A human looks at them through a Herdr client. Herdr draws the panes, the tabs, and its own sidebar. Kiki draws only what is specific to kiki: the overlay, approval cards, and an optional Stack pane. The custom UI is a ratatui-rendered `kk` process. Kiki always shows the real agent PTY; it never re-renders or proxies the harness's screen.

## Vocabulary

- **Herdr client** — one terminal attached to kiki's dedicated Herdr server, opened with `kk attach` (see [Commands](../09-commands.md#kk-attach)). Several clients may be attached at once. Each has its own view.
- **Terminal group** — the thread's terminal home: one Herdr workspace on the dedicated server. In this book an unqualified "workspace" always means a jj workspace.
- **Role pane** — a pane kiki provisions in the terminal group's first tab: the **agent pane** (`agent`, required), the **shell pane** (`shell`), and the **UI pane** (`ui`). A role is bound to the process identity that claimed it through the kiki pane launcher, and it ends when that process ends; it never comes from a pane's position, title, or label.
- **User pane** — any pane or tab the user adds natively in Herdr. `user` is not a role; it is the absence of one. Kiki never recreates one. Close accounts for every process in it.
- **Herdr sidebar** — Herdr's native sidebar at the left of every client. It lists the server's Herdr workspaces, so it lists every thread's terminal group across all registered repos. Kiki feeds it a label and tokens; see [Herdr sidebar projection](#herdr-sidebar-projection).
- **Overlay** — kiki's custom TUI, opened by bare `kk` (inside a registered repo) or by the overlay keybinding. Transient. Dismissed on switch, on `q` or `esc`, or on completing a verb. Outside a registered repo, bare `kk` falls back to the command summary plus `kk ls` (see [Commands](../09-commands.md)).
- **Shell pane** — the `shell` role pane: the user's `$SHELL` at the jj workspace path, beside the agent pane in the same tab (default position: below; configurable to the right). On by default. Detailed semantics in [Shell pane](#shell-pane).
- **UI pane** — the optional `ui` role pane: a narrow, navigation-only pane that keeps the Stack tree permanently visible. Off by default. Detailed semantics in [UI pane](#ui-pane).
- **Stack section** — the threads in the current repo, rendered as a follows-aware tree in `kk log` order. Cursor moves here for navigation.
- **Activity section** — the same threads, flat-listed by most-recent agent event (descending). Cursor moves here for triage. It appears in the overlay only; outside the overlay, the Herdr sidebar carries the ambient attention role.
- **Preview pane** — the right two-thirds of the overlay. Renders one of: transcript tail, working-copy diff, PR comments. Toggled by `t` / `d` / `c`. It is a region of the overlay, not a Herdr pane.
- **Chord ribbon** — a one-line keybinding hint at the bottom edge of the overlay. Toggled by `?`. Adapts to current selection (e.g. hides `c` for a thread without a PR).
- **Inlined status** — the per-thread status block the Stack section renders under the _current_ thread's bookmark line. Reuses `StatusRenderer --no-jj` byte-identically with `kk status` (see [Commands](../09-commands.md)). Single source of truth.
- **Checkpoint lag** — a normal active-thread condition in which the tracked checkpoint target trails the workspace's persisted live head. Detailed status labels it `checkpoint behind head`; compact TUI surfaces append `↑` to the bookmark. This is not dirty state or cascade conflict.
- **Context strip** — the bottom-most line of the overlay or the UI pane. One compressed sentence with TUI-specific content. Two forms by context: the overlay form carries repo + bookmark + cascade glyph + agent model + ctx % + last op age; the UI-pane form is shorter (bookmark + cascade glyph + agent glyph) because the agent pane next to it already surfaces model and ctx. This is a TUI footer, separate from the `StatusRenderer`-backed inlined status.
- **Toast** — a non-modal floating pill in the overlay's top-right corner. Used for cascade events, agent finish/error notifications, auto-archive-on-PR-merge undo prompts, and config-set warnings. Auto-dismisses after `[ui] toast_ttl_ms` (default 4000) or its trigger-specific TTL (e.g., the auto-archive undo grace is 5000ms, overriding the default — see [Publishing](../07-publishing.md)). Carries at most one optional named action (e.g., `undo`); never opens an approval card. A **Herdr toast** is a different thing: Herdr's own notification, used as one attention transport (see [Toasts](#toasts)).
- **Card** — a centered modal panel with title, body, and one or two action buttons. Used for spawn input and foreground approval.

The overlay authenticates ordinary current-thread reads with the contextual thread credential and consumes the repo-summary stream for every other row. It never treats cursor position as authority. Opening transcript, diff, PR-comment, or detailed-audit content for a non-current thread enters the foreground approval flow before fetching content. The approved response is one immutable snapshot bound to the method, target, query, and repository observation; refreshing it, changing tabs, expanding its range, or opening the full reader requires a new challenge. No sensitive bytes are fetched speculatively behind an approval card.

## Native and custom surfaces

Kiki reuses Herdr's UI where it already answers the need and builds UI only where the need is kiki-specific. The decision is recorded in [Terminal runtime · Native and custom UI](../13-architecture/terminal-runtime.md#native-and-custom-ui); this chapter specifies the result.

| Need                                                                       | Surface                                                          | Owner                                 |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------- |
| Panes, splits, tabs, scrollback, copy mode, mouse, resize                  | Herdr, unmodified                                                | Herdr                                 |
| A cross-repo list of threads with attention state                          | the Herdr sidebar, fed by kiki's label and tokens                | Herdr draws; kiki publishes           |
| Ambient "something needs you" while heads-down                             | Herdr sidebar tokens and Herdr toasts, plus OS notifications     | Herdr and the OS draw; kiki publishes |
| Moving between threads                                                     | Herdr's own navigation, and `kk switch`                          | each Herdr client                     |
| The follows tree, stack-aware log, transcript and diff preview, spawn form | the `kk` overlay                                                 | kiki                                  |
| Approval cards                                                             | the enrolled `ApprovalPresenter`, in its own foreground terminal | kiki, always                          |
| A permanently visible Stack tree                                           | the optional UI pane                                             | kiki                                  |

Several Herdr behaviors this chapter relies on are known from reading Herdr's source at the candidate revision and have not yet been exercised against a running candidate build: popups, keybinding commands and the ids they receive, plugin panes, and toast delivery and rate limiting. Each is an acceptance gate recorded in [Terminal runtime](../13-architecture/terminal-runtime.md#what-exists-what-kiki-builds-what-herdr-must-add), not an established fact. Where a gate fails, the surface that depends on it changes; the rules below do not.

Three rules follow:

- Kiki does not rebuild what Herdr provides. There is no kiki pane manager, tab bar, scrollback viewer, or status line.
- Nothing Herdr draws is an input to kiki. Labels, tokens, Herdr's agent states, and pane placement are presentation; kiki never reads a decision out of them.
- A Herdr keybinding, plugin action, or sidebar click may open a kiki surface or move a view. It is never an approval, and it never carries more authority than the `kk` process it starts.

## Glyph language

Two glyphs per row, max. PR appears inline as `#NNNN` only if set.

| state                   | glyph | color  |
| ----------------------- | ----- | ------ |
| cascade in sync         | `──`  | dim    |
| cascade pending         | `↻`   | amber  |
| cascade conflicted      | `◐`   | red    |
| agent idle              | `○`   | dim    |
| agent working           | `●`   | amber  |
| agent finished          | `✓`   | green  |
| agent blocked           | `◐`   | red    |
| lifecycle in progress   | `…`   | amber  |
| lifecycle repair needed | `!`   | red    |
| lifecycle closed        | `□`   | dim    |
| follows arrow           | `←●`  | dim    |
| current thread mark     | `▸`   | accent |

The cascade indicator uses the same three-valued state model as `kk status` (`in sync`, `pending`, `conflicted`). For `Creating | ClosePreflight | CloseCommit | DestroyCommit`, lifecycle `…` replaces the agent glyph; for `CreateFailed | CloseFailed | ProjectionDiverged | DestroyFailed`, `!` replaces it and the literal lifecycle label appears in detail; `□` identifies a closed row when closed rows are requested. `Destroyed` rows are hidden unless an explicit future destroyed-thread view requests them. Active rows use the normal agent display states. This replacement rule preserves the two-state-glyph limit.

The same glyphs appear in the overlay, the UI pane, `kk log`, and the tokens kiki publishes to the Herdr sidebar. Herdr's own agent detection (`idle | working | blocked | done | unknown`) is a screen-and-process heuristic and is not this table's agent state. Kiki's agent glyph comes from kiki's `AgentStatus`. If a Herdr sidebar row also shows Herdr's detected state, it is a hint, and kiki's token is the kiki state.

Every state in this table must be distinguishable by glyph alone, not by color. Color is an accelerator: it makes scanning faster, but `NO_COLOR=1` and color-blind palettes must still convey the state. The `LogRenderer` and `StatusRenderer` projections strip color when `NO_COLOR=1` is set in the environment and rely on glyph + label to carry the signal. See [Invariants](../02-invariants.md).

## Overlay

The overlay opens in `NAVIGATE` mode in one of two ways:

- **Bare `kk`** typed in a pane, or in any other terminal inside a registered repo, runs the overlay inline, filling that pane or terminal.
- **The overlay keybinding** opens the same `kk` process as a Herdr popup over the current view. Kiki writes this binding into the `keys.command[]` table of its generated Herdr configuration; the user does not hand-edit Herdr's keymap to get it. Herdr passes the binding the active workspace, tab, and pane ids, and `kk` resolves the current thread from them.

Either way the overlay is an ordinary `kk` process with its own terminal. It holds no authority the same command typed in a shell would not hold.

The overlay is focused on the current thread (resolved via the standard CLI [context-resolution](../09-commands.md#context-resolution) chain). If no current thread resolves but the repo is registered, the cursor lands on the most-recently-active thread in the repo. If the repo has no threads, the overlay shows an empty-state placeholder ("no threads — press `n` to create one") with `n` and `?` as the only active verbs.

`enter` on a thread row is `kk switch` for the caller's client, under the same contract (see [Commands](../09-commands.md#kk-switch)). The caller is the client that pressed the overlay keybinding, or the foreground client showing the pane where `kk` was typed. An overlay running in a terminal that is not a Herdr client has no caller client: `enter` moves no one and names `kk attach <thread>`. If Herdr does not advertise `client_targeted_focus`, `enter` fails with the same message as `kk switch` and the overlay stays open. The overlay never moves every attached client.

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
 ●─pi/refactor      ↻   wrk       │  agent       ● working   2m 18s
 │                                  │  pr          #482 draft  ●●●●● ci green
 ●─pi/codex-conv ▸  ↻   ←●        │  follows     pi/refactor → main
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
 │                                  │   could you check whether a materialized intent
 ●─pi/refactor      ↻   wrk       │   is dropped on a hook crash before MarkDelivered?
 │                                  │
 ●─pi/codex-conv ▸  ↻   ←●        │  agent  2m 04s ago
 │                                  │   reading kiki-core/cascade/intent_store.rs ...
 ●─pi/agent-tui     ○     idle      │   its saved payload stays deliverable until ack,
                                    │   so a crash before MarkDelivered re-enters the
 ACTIVITY                           │   same intent. Want me
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

The `d` preview below has two sources. For the contextual thread, pressing `d` is the same explicit, human-invoked passthrough as `kk status --diff`: the overlay's `kk` process runs it in the caller's own jj workspace, and it may snapshot the working copy (see [Commands](../09-commands.md#kk-status)). It runs only on that keypress, never on a timer or on cursor movement. For any other thread, `d` keeps its approval rule and renders from a pinned read that ignores the working copy. Everything else the overlay and the UI pane poll uses pinned reads only.

### Wireframe — `d` shows working-copy diff

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui                              ?  esc

 STACK                              │  diff · pi-extensions/codex-conv-tui · jj st --diff
                                    │
 ● main             ──    in        │  M  kiki-core/src/cascade/intent_store.rs +14 -2
 │                                  │  M  kkd/src/services/cascade.rs       +6  -0
 ●─pi/refactor      ↻   wrk       │  ?  tests/cascade/crash_before_md.rs  +88
 │                                  │  ─────────────────────────────────────────────
 ●─pi/codex-conv ▸  ↻   ←●        │  diff --git a/kiki-core/src/cascade/intent_store.rs
 │                                  │  +pub fn lookup_pending(&self) -> Option<Row> {
 ●─pi/agent-tui     ○     idle      │  +    self.rows
                                    │  +        .iter()
 ACTIVITY                           │  +        .find(|i| i.is_deliverable())
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
 ●─pi/refactor      ↻   wrk       │
 │                                  │  ─ comments ─────────────────────────────────
 ●─pi/codex-conv ▸  ↻   ←●        │
 │                                  │  @ogul  18m ago  on cascade/intent_store.rs:42
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
 ●─pi/refactor      ↻   wrk       │
 │                                  │
 ●─pi/codex-conv ▸  ↻   ←●        │
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

### Wireframe — foreground approval card (`x` close on cursored thread)

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui                              ?  esc

 STACK                              │  pi-extensions/codex-conv-tui
                                    │
 ● main             ──    in        │  …
 │                                  │
 ●─pi/refactor      ↻   wrk       │   ╭─ Close pi-extensions/codex-conv-tui? ───╮
 │                                  │   │                                          │
 ●─pi/codex-conv ▸  ↻   ←●        │   │  Stops the agent and every process in    │
 │                                  │   │  the terminal group: agent, shell, and   │
 ●─pi/agent-tui     ○     idle      │   │  1 user pane (5 processes).              │
                                    │   │  Forgets the jj workspace and removes    │
 ACTIVITY                           │   │  ~/code/pi-extensions-kiki-codex-conv.   │
                                    │   │  Tracked jj revisions are kept.          │
                                    │   │  PR #482 is left open (use --discard-pr).│
 ● codex-conv     working   2m18s   │   │  plan 7f3a91c2 · one use · expires 30s   │
 ● refactor       working    34s    │   │                                          │
 ◐ session-recall conflicted        │   │   ⏎  Close      esc  Cancel              │
 ○ agent-tui      idle     1h12m    │   ╰──────────────────────────────────────────╯
 ✓ minimal-foot   finished   8m     │
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  master ✻  ── in sync  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

`i` (interrupt) shows the same shape; the body changes. `enter` confirms the daemon-issued challenge through the enrolled presenter, then the exact operation retries with its one-use approval. There is no chord that fires destructive verbs in one keystroke.

Approval cards are always custom and always foreground-bound. The card is drawn by the `kk` process that is the enrolled `ApprovalPresenter`, in the terminal that process owns: the pane where `kk` was typed, or the popup the overlay keybinding opened. A Herdr toast, sidebar row, plugin popup that is not that `kk` process, or keybinding can never display or confirm an approval. A close card names the whole terminal group, because close stops every process in every pane of it, including panes the user added.

### Wireframe — spawn card (`n` for new thread, `N` for new-as-child-of-cursored)

```
 kiki · SPAWN · child of pi-extensions/codex-conv-tui                          esc

   ╭─ New thread ────────────────────────────────────────────────────────────────╮
   │                                                                              │
   │  name        pi/cascade-recovery_                                            │
   │  follows     pi-extensions/codex-conv-tui  (─ no follow)                     │
   │  agent       claude-code   (default — change in user config)                 │
   │  ui pane     ○  on   ●  off   (default: off, from [ui] ui_pane)             │
   │                                                                              │
   │   ⏎  Spawn      esc  Cancel                                                  │
   ╰──────────────────────────────────────────────────────────────────────────────╯
```

`n` opens this with `follows` set to "── no follow" by default. `N` opens it with `follows` set to the cursored thread.

Submitting the spawn form begins, but does not itself satisfy, the one-shot approval flow required by `kk new`. The daemon returns a canonical plan naming the base/head, follows choice, workspace, harness, and initial-input digest; the overlay displays that plan in an approval card and confirms it through its enrolled foreground presenter. The same two-phase shape applies to publish, close, interrupt, reopen, and any cross-thread or consequential repair action.

## Herdr sidebar projection

Herdr's native sidebar is the always-visible thread list. It replaces a kiki-drawn status strip and takes the ambient Activity and attention role. Kiki does not draw it. Kiki publishes into it:

- **Label.** `kkd` sets each terminal group's Herdr workspace label to the repo's directory name, the thread's display name, and a short provisioning tag. It is for people and for discovery hints only.
- **Tokens (v1.x).** `kkd` publishes metadata tokens on each terminal group's Herdr workspace, and kiki's generated Herdr configuration composes them into the sidebar row after the label with style rules:

| token             | content                                                                                                                     | example                                          |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `$kiki_follows`   | the follows arrow and parent thread name; empty when the thread follows nothing                                             | `←● refactor`                                    |
| `$kiki_cascade`   | the cascade glyph and its word                                                                                              | `── in sync`, `↻ pending`, `◐ conflicted`        |
| `$kiki_agent`     | the agent display state glyph and its word, for an `Active` thread                                                          | `○ idle`, `● working`, `✓ finished`, `◐ blocked` |
| `$kiki_lifecycle` | the lifecycle glyph and the literal lifecycle label, for a thread that is not `Active`; it takes the place of `$kiki_agent` | `… Creating`, `! CloseFailed`                    |

Every token carries its glyph and a word, so a row reads correctly with `NO_COLOR=1` and with any Herdr theme. Style rules may add color; they never carry a state on their own.

The projection is one-way, and it is never authority:

- `kkd` republishes the label and every token after each state change and after every resync with the server. A token that was overwritten, expired, or lost in a server restart heals on the next publish.
- Kiki never reads a label or token back. Any process on the server's socket can change them. A row is not evidence that a thread is `Active`, that an agent is ready, or that a cascade was delivered. `kk ls` and `kk status` report kiki's state.
- Kiki publishes the label and tokens only to a terminal group with a current binding. A Herdr workspace that Herdr restored after a server restart is a remnant container, and one the user created by hand is the user's; neither has kiki tokens. Its row shows whatever label Herdr kept and nothing from kiki. A kept label does not tie a remnant to a thread.
- The row is not a kiki control. Selecting a row is Herdr's own navigation for that client. No kiki verb is bound in the sidebar, so it cannot spawn, publish, close, interrupt, or approve.

The sidebar lists terminal groups from every registered repo in one list. The label names the repo, so rows from different repos stay distinct.

### Wireframe — a Herdr client on the kiki server (Herdr sidebar · agent pane · shell pane)

```
 ╭─ kiki ──────────────────────────────────────────────────────────────╮ ╭─ agent · codex-conv ───────────────────╮
 │                                                                     │ │                                        │
 │   pi-extensions refactor 2c81               ↻ pending    ● working  │ │ > human                                │
 │ ▸ pi-extensions codex-conv 7f3a ←● refactor ↻ pending    ● working  │ │   could you check whether a            │
 │   pi-extensions agent-tui b0d4              ── in sync   ○ idle     │ │   materialized intent is dropped on a  │
 │   pi-extensions session-recall 9d1e         ◐ conflicted ◐ blocked  │ │   hook crash before MarkDelivered?     │
 │   pi-extensions minimal-foot 51aa           ── in sync   ✓ finished │ │                                        │
 │   kiki-docs api-guide 3b7e                  ── in sync   ● working  │ │ ● working  2m 18s  esc to interrupt    │
 │   kiki-www footer-year c02d                 ── in sync   … Creating │ │                                        │
 │                                                                     │ │   reading kiki-core/cascade/           │
 │                                                                     │ │   intent_store.rs ...                  │
 │                                                                     │ │                                        │
 │                                                                     │ ╰────────────────────────────────────────╯
 │                                                                     │ ╭─ shell ────────────────────────────────╮
 │                                                                     │ │ codex-conv $ jj st                     │
 │                                                                     │ │ M kiki-core/src/cascade/intent_store.rs│
 │                                                                     │ │ Working copy : qxnopkyl 8a3c2d1e       │
 │                                                                     │ │ codex-conv $ _                         │
 │                                                                     │ │                                        │
 │                                                                     │ │                                        │
 │                                                                     │ │                                        │
 │                                                                     │ │                                        │
 ╰─────────────────────────────────────────────────────────────────────╯ ╰────────────────────────────────────────╯
```

The left region is Herdr's sidebar, one row per terminal group, with the label (repo, thread, provisioning tag) followed by kiki's tokens. The last two rows belong to other repos. `▸` here stands for however Herdr marks the row a client is viewing. The right region is the thread's first tab: the agent pane on top, hosting the harness's PTY, and the shell pane below. The last row shows a thread that is still `Creating`: its lifecycle token stands where the agent token would be.

## UI pane

The UI pane is the optional `ui` role pane. It keeps the Stack tree permanently visible beside the agent. It is opt-in via `[ui] ui_pane = true` in user config, or per thread via `kk new --sidebar` / `--no-sidebar` (see [Commands](../09-commands.md#kk-new)). Herdr's sidebar is always present and is not controlled by these settings.

Its direct PTY child is the kiki pane launcher, which claims the `ui` role and then replaces itself with the kiki UI process. The pane is provisioned with an explicit working directory and environment, as every role pane is.

It renders the overlay's Stack section, with the inlined status under the current thread, in a narrow fixed-width pane (`[ui] ui_pane_width`, default 32 columns). It has no Activity section and no preview; the Herdr sidebar and the overlay cover those. It is **navigation-only**: `j` / `k` / `↑` / `↓` move the cursor, `enter` switches the caller's client to the cursored thread under the `kk switch` contract, and `?` toggles the chord ribbon (showing only the navigation verbs). Mouse click on a row moves the cursor; scroll-wheel scrolls the tree. Spawn, publish, close, destroy, interrupt, reopen, and preview-toggle are not bound — accidental focus on the UI pane cannot mutate state. Moving focus between panes is Herdr's own pane navigation.

The UI pane is ensured when the terminal group is provisioned: at `kk new`, at `kk reopen`, and by a `kk repair` terminal restart. `kk switch` never creates it. If the user closes the pane, or the UI process exits and Herdr removes the pane, kiki does not put it back until one of those events.

### Wireframe — a thread's tab with the UI pane (UI pane · agent pane; Herdr's sidebar sits to the left of the tab as above)

```
 ╭─ ui ────────────────────────╮ ╭─ agent · codex-conv ─────────────────────────────╮
 │                             │ │                                                  │
 │ STACK                       │ │ > human                                          │
 │                             │ │   could you check whether a materialized intent │
 │ ● main          ──    in    │ │   is dropped on a hook crash before              │
 │ │                           │ │   MarkDelivered?                                 │
 │ ●─pi/refactor   ↻  wrk    │ │                                                  │
 │ │                           │ │ ● working   2m 18s   esc to interrupt            │
 │ ●─pi/codex ▸    ↻  ←●     │ │                                                  │
 │ │                           │ │   reading kiki-core/cascade/intent_store.rs ...  │
 │ ●─pi/agent     ○     idle   │ │                                                  │
 │                             │ │                                                  │
 │ ─────────────────────────── │ │                                                  │
 │ ↑↓ ⏎ switch · ?             │ │                                                  │
 │ master ✻  ── in sync  ●     │ │                                                  │
 ╰─────────────────────────────╯ ╰──────────────────────────────────────────────────╯
```

The UI pane's context strip is shorter than the overlay's: just bookmark + dirty + cascade glyph + agent dot. Model and ctx-% are omitted because they are agent-pane state and the agent pane already shows them. The per-row inlined status under the current thread's bookmark line is unchanged from the overlay — same `StatusRenderer --no-jj` projection.

## Shell pane

The shell pane is the `shell` role pane: the user's shell at the thread's jj workspace path, in the same tab as the agent pane. It exists so the user can interact directly with the same jj workspace the agent is operating in — running `jj`, `gh`, tests, or any other command — without leaving the thread's terminal group. The agent pane and the shell pane share a working copy; what one writes the other sees.

The shell pane is on by default (`[ui] shell_pane = true`). It is opt-out, not opt-in, because direct shell access alongside the agent is an expected component of the kiki experience, not an extra. When opted out, the terminal group's first tab contains only the agent pane (and the UI pane, if that is enabled).

In kiki's vocabulary, **the** shell pane is the singular `shell` role pane kiki provisions. If the user splits a pane or opens a tab natively in Herdr, that is a user pane — kiki does not recreate it and does not call it a shell pane.

### Launch

The shell pane is created by Herdr layout application with a direct argv command, never by typing into another shell. Its direct PTY child is the kiki pane launcher. The launcher reports to `kkd`, claims the `shell` role for the thread's terminal binding, and then replaces itself with the user's shell, taken from `$SHELL` (fallback `/bin/sh`).

Kiki passes the pane's working directory and environment explicitly in the provisioning call:

- the working directory is the jj workspace path;
- the environment includes `KIKI_THREAD_ID` and the thread's other context variables, so `kk` typed in the pane resolves the thread at the environment step of [context resolution](../09-commands.md#context-resolution);
- the environment never includes the `ApprovalPresenter` credential, a reusable Admin credential, or the bytes of any credential.

The shell does not inherit the environment of whichever terminal ran `kk new`. Herdr starts the pane; kiki's explicit variables are the only thread-specific ones in it.

### Layout

The shell pane lives in the same tab as the agent pane. By default it sits in a horizontal split below the agent (the agent on top, the shell on the bottom). Configurable via `[ui] shell_pane_position` (`below` | `right`, default `below`) and `[ui] shell_pane_size_pct` (int, default `25`).

`shell_pane_size_pct` is read as "the percentage of the dimension the split divides" — height when `position = below`, width when `position = right` — so the same key produces the analogous proportion under either orientation. Under the default `below` + `25`, the agent occupies the top 75% of height and the shell the bottom 25%; under `right` + `25`, the agent occupies 75% of width on the left and the shell 25% on the right. Kiki provisions the shell pane in the agent's tab by design, so the user can see one while interacting with the other. After provisioning, the layout is the user's: Herdr's native resize, zoom, and move apply, and kiki does not put panes back.

The four layout combinations of `[ui] ui_pane` × `[ui] shell_pane`, shown with the default `shell_pane_position = below`. Herdr's sidebar is outside the tab in every case:

| `ui_pane` | `shell_pane` | tab layout                                                                  |
| --------- | ------------ | --------------------------------------------------------------------------- |
| `true`    | `true`       | UI pane left (32 cols) · agent top-right (~75%) · shell bottom-right (~25%) |
| `false`   | `true`       | agent top (~75%) · shell bottom (~25%) — full width                         |
| `true`    | `false`      | UI pane left (32 cols) · agent right (full height)                          |
| `false`   | `false`      | agent only — full tab                                                       |

Under `shell_pane_position = right`, the agent / shell rows flip orientation: the shell sits to the right of the agent (taking `shell_pane_size_pct` of width), and the UI pane — when present — still occupies the leftmost 32 cols. The UI pane's position is fixed; only the shell pane's position is configurable.

The default layout (`ui_pane = false`, `shell_pane = true`) is the wireframe under [Herdr sidebar projection](#herdr-sidebar-projection).

`kk new`, `kk reopen`, and `kk switch` target the agent pane, so a client that arrives at a thread lands where the harness is. Kiki does not otherwise move pane focus.

### Lifecycle

- **`kk new`**: provisions the shell pane with the terminal group if `[ui] shell_pane = true`, before the harness starts.
- **`kk reopen <thread>`**: as `kk new` — the pane is provisioned fresh in a new terminal group. Shell history, scrollback, and any processes that were running before close are not preserved; the user's shell starts cold.
- **`kk repair` terminal restart**: the restart plan for a `TerminalMissing` thread ensures the shell pane as at creation, with its explicit working directory and environment.
- **`kk switch <thread>`**: does nothing to the shell pane. Switch performs no terminal mutation and never re-creates a pane.
- **The shell exits or the user closes the pane**: Herdr removes a pane when its direct command exits, so typing `exit` removes the shell pane. Its role binding ends. Kiki raises no issue and does not put the pane back until the next reopen or terminal restart. A user who wants another shell splits one natively in Herdr.
- **A natively split pane** is a user pane. It does not inherit the shell pane's explicit environment, so it has no `KIKI_THREAD_ID`; `kk` typed there resolves the thread through its Herdr pane identity instead.
- **After a Herdr server restart**: a restored pane is a remnant pane — a plain shell with no role and none of kiki's variables. It is not the shell pane. `kk` typed there resolves the thread, if at all, from the working directory. The restart plan either reuses the remnant container, replacing its first tab with the role layout, or closes it; either way it provisions real role panes.
- **`kk close`**: closes the whole terminal group, and the shell pane goes with it. Any process running in the shell pane is stopped alongside the agent. See [Threads · close](../03-threads.md#close).

`kkd` does not manage what runs in the shell pane. It does not track which commands run there, does not surface the pane's state in the overlay or the Herdr sidebar, and does not log audit rows for activity in it. Anything kiki cares about that the user does there — direct jj operations, gh interactions — routes through the existing op-log watcher and GitHub polling paths as if the user had run it anywhere else. This is the ambient-coordinator stance applied to the shell pane: kiki sets it up, then gets out of the way.

`kkd` does observe the shell pane's processes when it must prove something about the workspace. At `kk close` and `kk thread destroy`, `ProcessSupervisor` takes the direct child of every pane in the terminal group — the shell pane and user panes included — as a root, freezes it with its descendants, and verifies exit by OS process identity before the jj workspace is forgotten or deleted. A background job started from the shell pane is therefore part of the close plan. A job that cannot be accounted for stops the deletion; it is never silently abandoned or silently killed outside the approved set.

### Authority

The shell pane runs the user's shell process at the user's UID. Kiki puts context identifiers in its environment and no credential. When the user invokes `kk`, context resolution names the thread and the CLI loads only that thread's credential. Consequential operations enter the foreground one-shot approval flow, where the `kk` process the user ran acts as the presenter in that pane; the CLI never auto-loads reusable Admin authority, and the pane's environment never supplies the presenter credential. See [Authority](../04-authority.md).

## Toasts

Toasts are non-modal pills in the overlay's top-right corner, stacking downward. Each carries one line of summary text: glyph, thread name, event, elapsed.

Two subtypes share the surface:

- **Notification toast** — no interactive action. The body may include hint text naming an overlay verb (e.g., "tap T to read transcript"); the verb is fielded by the overlay's normal keymap, the toast does not intercept it.
- **Actionable toast** — carries exactly one named action (e.g., `undo`). The action is invoked by clicking the action label, or by pressing the named key while the toast is the most-recent unactioned toast (this is the _only_ keystroke a toast intercepts; everything else passes through to the overlay). The action is never destructive — it is restorative (`undo` of a kiki-initiated mutation, e.g., auto-archive on PR-merge — see [Publishing](../07-publishing.md)). Toasts never open an approval card.

Dismissal rules (apply to both subtypes):

- auto-dismiss after the toast's TTL elapses (default `[ui] toast_ttl_ms` = 4000ms; specific triggers may override, e.g., auto-archive undo grace = 5000ms — see [Publishing](../07-publishing.md))
- click anywhere on the toast pill (excluding the action label, which runs the action) dismisses it
- moving the keyboard cursor onto the row that issued the toast, or clicking that row, dismisses the toast (treated as "user acknowledged")
- invoking the toast's action (actionable toasts only) dismisses the toast on completion

Toast triggers (v1):

- agent finish (`✓`) — notification
- agent error / blocked (`◐`) — notification
- cascade conflict on a non-current thread (`◐`) — notification
- cascade materialized for a child thread (`──`, only when ≥ 2 child reconciliations coalesce) — notification
- config-set warning that won't take effect until next `kk new` / `kk reopen` — notification
- auto-archive on PR-merge (`✓`) with `undo` action (v1.x polish; 5s grace — see [Publishing](../07-publishing.md)) — actionable

Overlay toasts are drawn only by the overlay. The UI pane hosts none, and kiki draws nothing over the live agent pane.

### Notifications outside the overlay

When no overlay is open, attention events travel on two channels:

- **The Herdr sidebar.** The thread's tokens change, so the row shows the new glyph and word. This is passive: it needs a client to be attached and looking.
- **The configured notification transport**, `[notifications] os_provider` (`auto | notify-rust | osascript | herdr | off` — see [Configuration](../11-configuration.md) and [Observability](../12-observability.md)).

`os_provider = herdr` sends the event as a Herdr toast. A Herdr toast is shown to every client attached to the kiki server. It is global, best-effort, and rate-limited, and it reaches nobody when no client is attached. That is acceptable because kiki's attention events are not caller-scoped: a cascade conflict or a blocked agent concerns the thread, not whoever ran a command. Nothing that must reach one specific person travels by Herdr toast.

A Herdr toast or an OS notification carries the same one-line summary as an overlay toast, with its glyph and words. It carries no action, intercepts no key, and never displays or confirms an approval. The actionable `undo` toast exists only in the overlay; outside it, the notification names the event and the user acts through `kk`.

### Wireframe — conflicted-thread toast in overlay

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui     ┌─────────────────────────────┐
                                                    │ ◐ session-recall conflicted │
 STACK                                              │   tap T to read transcript  │
                                                    └─────────────────────────────┘
 ● main             ──    in
 │
 ●─pi/refactor      ↻   wrk
 │
 ●─pi/codex-conv ▸  ↻   ←●
 │
 ●─pi/agent-tui     ○     idle
 │
 ●─pi/session-recall ◐    conflict

 …
```

## Forms

Spawn and approval cards are the only initial UI forms. Both:

- center on screen
- have a single labeled title row, a body, and one or two action buttons
- accept `enter` for the primary action and `esc` for cancel
- accept `tab` and `shift+tab` to move between fields, when there is more than one field

Forms are pure ratatui widgets drawn by the overlay's `kk` process; they are never Herdr popups of their own, plugin panes, or toasts. Submitting a form calls `BeginApproval`; it does not perform the operation. The approval card must display the daemon-returned canonical plan and digest byte-for-byte. Only an enrolled foreground presenter may call `ConfirmApproval`, after which the overlay retries the exact operation with the resulting approval id. A changed plan dismisses the stale card and starts again. The card surface stays inside the overlay process, but authority remains in the daemon challenge and one-use capability.

## Overlay state machine

The overlay is a small state machine:

- `NAVIGATE`: default state. Sidebar cursor moves through Stack and Activity rows.
- `PREVIEW`: right pane is pinned to transcript tail, diff, or PR comments for the cursored thread.
- `APPROVE`: a sensitive read, spawn, or consequential verb waits on a daemon-issued foreground approval challenge.
- `SPAWN`: spawn form collects thread name, follows target, and harness fields.
- `VIEWER`: full-screen transcript reader opened by `T`.

`q` and `esc` leave the overlay from `NAVIGATE` and return to the prior overlay state from sub-states. `enter` only switches threads from `NAVIGATE` on a bookmark row. Destructive actions are unavailable from the UI pane and from the Herdr sidebar.

For the current thread, `space`, `t`, `d`, and `T` may enter `PREVIEW` or `VIEWER` directly under `ThreadScoped<T>`. For another thread, those keys enter `APPROVE`; success installs only the approved immutable snapshot and then enters the requested view. `c` follows the same rule because PR comments exceed the repo-summary scope. Cancellation returns to `NAVIGATE` without issuing the read.

## Keymap

Overlay (`NAVIGATE` mode):

| key       | verb                                                                            |
| --------- | ------------------------------------------------------------------------------- |
| `↑` / `k` | move cursor up                                                                  |
| `↓` / `j` | move cursor down                                                                |
| `tab`     | jump cursor between Stack and Activity                                          |
| `enter`   | switch the caller's client to the cursored thread (dismisses overlay)           |
| `space`   | toggle preview pane on the cursored thread                                      |
| `t`       | preview-mode = transcript tail                                                  |
| `d`       | preview-mode = working-copy diff                                                |
| `c`       | preview-mode = PR comments (preview only — not close)                           |
| `T`       | open full-screen transcript reader                                              |
| `n`       | spawn modal (new thread, no follow)                                             |
| `N`       | spawn modal (new thread, follows cursored)                                      |
| `p`       | publish cursored thread (`kk publish`)                                          |
| `x`       | close cursored thread (opens approval card)                                     |
| `i`       | interrupt cursored thread's agent (opens approval card)                         |
| `r`       | reopen cursored thread (only meaningful when thread is closed; otherwise no-op) |
| `?`       | toggle chord ribbon                                                             |
| `q`       | dismiss overlay                                                                 |
| `esc`     | dismiss overlay                                                                 |
| click     | (mouse) move cursor to clicked row, or switch preview tab                       |
| scroll    | (mouse) scroll the focused pane (sidebar list or preview)                       |

Note: `c` previews PR comments. Close is `x`. The binding favors the frequent read action and keeps closing behind a distinct key.

UI pane:

| key             | verb                                              |
| --------------- | ------------------------------------------------- |
| `↑` `↓` `j` `k` | move cursor                                       |
| `enter`         | switch the caller's client to the cursored thread |
| `?`             | toggle chord ribbon (read-only set)               |
| click           | move cursor to clicked row                        |
| scroll          | scroll the tree                                   |

The UI pane binds **no** verb that mutates state. Spawn, publish, close, destroy, interrupt, and preview-toggle are unbound. It binds no key for moving between panes; that is Herdr's own navigation.

The overlay keybinding is the only key kiki binds in Herdr's own keymap. The Herdr sidebar carries no kiki bindings. Every other Herdr key keeps Herdr's meaning.

## Context strip

One line at the bottom of the overlay. Order, left to right:

`<repo>  <bookmark>[*][↑]  <cascade-glyph cascade-state>  <agent-model>  ctx ●●●●○ <pct>%  last op <duration>`

`*` is the dirty marker for the current working copy; `↑` means its tracked checkpoint target trails the persisted live head. `<cascade-glyph cascade-state>` is the kiki-CLI-shared three-valued indicator. `<agent-model>` is the harness-reported model name. `ctx` is the harness-reported context-window utilization. `last op` is the duration since the last jj op on the current thread.

The UI pane's context strip is a shortened form: `<bookmark>[*][↑]  <cascade-glyph cascade-state>  <agent-glyph>`. Model and ctx are omitted because the agent pane next to it already surfaces them.

The context strip is a TUI-specific footer and is **not** a `StatusRenderer` projection. The `StatusRenderer`-fed artifact is the _inlined status_ under the current thread's bookmark line in the Stack section; that artifact is byte-identical with `kk status --no-jj` per `testing.md` (`StatusRenderer` shared-renderer test).

## Degradation

If the terminal the overlay runs in — the pane where `kk` was typed, or the popup the keybinding opened — is narrower than `[ui] overlay_min_cols` (default 80) when it starts, the overlay refuses to open and prints `kk ls` output instead, with a warning. There is no half-overlay state.

Role panes are not skipped for size. `kkd` provisions a terminal group whether or not any client is attached, so there is no terminal size to test at thread creation. A narrow client is handled by Herdr's own resize and zoom. The overlay is still available via bare `kk`.

Each surface degrades on its own, and none of them changes thread state:

- **No client attached.** Nothing is drawn. Threads keep running, tokens are still published, and the configured OS notification transport still fires. `kk ls`, `kk status`, and `kk log` work from any terminal.
- **No `client_targeted_focus`.** This is a required Herdr extension. `kk switch`, the overlay's `enter`, and the UI pane's `enter` fail with a message that names the capability. Kiki never substitutes a focus change that moves every client. Herdr's own navigation still works, and so does the explicit `kk switch --all-clients`.
- **Tokens not shipped, lost, or overwritten.** The sidebar row shows the label alone, or a stale token, until the next publish. `kk ls` is the truthful list.
- **Herdr server restarted.** Restored panes are remnant panes in containers without kiki tokens. Affected threads show `!` with their lifecycle label in the overlay and `kk ls`, with the reason `TerminalMissing`, until `kk repair` restarts them. No surface shows an agent state for a thread that has no ready incarnation.
- **A row too narrow** to render the full glyph + name + status in the overlay or UI pane truncates the name with a single-character ellipsis (no multi-character `…` wrap). Collapsed-summary lines from `kk log` follow the existing CLI rules. Truncation inside the Herdr sidebar is Herdr's.

## Mouse

Mouse capture is on by default (`[ui] mouse_enabled = true`). The following events are honored in v1:

- click on an overlay sidebar row → moves the cursor and dismisses any overlay toast issued by that row; the UI pane has no toast surface
- click on a UI pane row → moves the cursor
- click on a preview-tab letter (`t` / `d` / `c`) in the preview pane header → switches preview mode, equivalent to pressing the corresponding key
- click on a toast pill, anywhere except the action label → dismisses that toast (notification toasts have no action label and dismiss on any click; actionable toasts dismiss everywhere except the labeled action)
- click on a toast's named action label (actionable toasts only) → invokes the action and dismisses the toast on completion
- scroll wheel on a focused pane → scrolls that pane

Drag, drag-resize, right-click context menus, click-and-drag selection, and hover/motion-driven UI are explicitly **out of v1 scope** for kiki's own surfaces. Herdr owns the multiplexer: pane selection, resize, text selection, scrollback, and clicks on the Herdr sidebar are Herdr's, and kiki does not contend with them. A click on a Herdr sidebar row is Herdr's navigation for that client; it invokes nothing in kiki.

If `[ui] mouse_enabled = false`, kiki's own processes do not request mouse capture and fall back to keyboard-only behavior. The key does not change Herdr's mouse handling.

## Configuration

[Configuration](../11-configuration.md) owns the key tables, types, defaults, and reload behavior. This section only names what the surfaces above read.

`[ui]` keys referenced by this spec:

- `ui_pane` (bool, default `false`) — whether the UI pane is provisioned
- `ui_pane_width` (int, default `32`) — the UI pane's width in columns
- `shell_pane` (bool, default `true`)
- `shell_pane_position` (string, default `"below"`)
- `shell_pane_size_pct` (int, default `25`)
- `mouse_enabled` (bool, default `true`)
- `overlay_min_cols` (int, default `80`)
- `toast_ttl_ms` (int, default `4000`)
- `theme` (string, default `"soft-dark"`)

All `[ui]` keys are personal preference: valid in user and per-thread config, invalid in repo-shared config (warned-and-ignored). Reload behavior:

- `mouse_enabled`, `toast_ttl_ms`, and `theme` are cosmetic and hot-reload. `theme` styles kiki's own surfaces; the Herdr client's theme is Herdr's.
- `overlay_min_cols` takes effect at the next overlay open.
- `ui_pane`, `ui_pane_width`, `shell_pane`, `shell_pane_position`, and `shell_pane_size_pct` take effect the next time a terminal group is provisioned — `kk new`, `kk reopen`, or a `kk repair` terminal restart. They do not reshape a live terminal group, and `kk switch` never applies them.

Outside `[ui]`:

- `[notifications] os_provider` selects the attention transport, including `herdr`; see [Toasts](#toasts).
- `[terminal]` and `[paths] herdr_dir` locate the Herdr executable, the dedicated server's session name, and its state. Kiki generates the dedicated server's Herdr configuration from them, including the sidebar row composition and the overlay keybinding. That generated file is kiki's; the user's own Herdr configuration is never read or changed.
