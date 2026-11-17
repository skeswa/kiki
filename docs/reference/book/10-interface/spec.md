# Interface

The interface surfaces in this chapter are [v1.x polish](../appendix-a-glossary.md#v1-x-polish) unless [Orientation](../01-orientation.md) says otherwise. That chapter is the only scope ledger. This chapter is the v1 contract for each surface when it ships.

Kiki's [threads](../appendix-a-glossary.md#thread) live in a [dedicated Herdr server](../appendix-a-glossary.md#dedicated-herdr-server) (see [Terminal runtime](../13-architecture/terminal-runtime.md)). [Herdr](https://github.com/herdrdev/herdr) is a [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer): a program that runs many terminals inside one window. A human looks at the threads through a [Herdr client](../appendix-a-glossary.md#herdr-client).

The drawing work is split:

- Herdr draws the panes, the tabs, and its own native sidebar.
- Kiki draws only what is specific to kiki: the overlay, approval cards, and an optional Stack pane.

The custom UI is a `kk` process rendered with [ratatui](https://ratatui.rs/), a library for text interfaces. Kiki always shows the real agent [PTY](https://en.wikipedia.org/wiki/Pseudoterminal) (the pseudoterminal the agent runs in). It never re-renders or proxies the screen of the [harness](../appendix-a-glossary.md#harness), which is the agent program.

## Vocabulary

- **[Herdr client](../appendix-a-glossary.md#herdr-client)**: one terminal attached to kiki's dedicated Herdr server. It is opened with `kk attach` (see [Commands](../09-commands.md#kk-attach)). Several clients may be attached at once. Each has its own view.
- **Terminal group**: the thread's terminal home: one Herdr workspace on the dedicated server. In this book an unqualified "workspace" always means a [jj workspace](../appendix-a-glossary.md#workspace). See [terminal group](../appendix-a-glossary.md#terminal-group).
- **Role pane**: a pane kiki provisions in the terminal group's first tab. See [role pane](../appendix-a-glossary.md#role-pane).
  - There are three: the **agent pane** (`agent`, required), the **shell pane** (`shell`), and the **UI pane** (`ui`).
  - A role is bound to the process identity that claimed it through the kiki [pane launcher](../appendix-a-glossary.md#pane-launcher).
  - The role ends when that process ends.
  - A role never comes from a pane's position, title, or label.
- **User pane**: any pane or tab the user adds natively in Herdr. `user` is not a role; it is the absence of one. Kiki never recreates one. Close accounts for every process in it.
- **Herdr sidebar**: Herdr's native sidebar at the left of a client.
  - It lists the server's Herdr workspaces. So it lists every thread's terminal group across all registered repos.
  - The user can hide or collapse it. It is Herdr's, not kiki's.
  - Kiki feeds it a label and tokens; see [Herdr sidebar projection](#herdr-sidebar-projection).
- **[Thread list](../appendix-a-glossary.md#thread-list)**: the left column of the overlay, holding the Stack and Activity sections. It is part of the overlay's own drawing. It is not the Herdr sidebar and not the UI pane.
- **Overlay**: kiki's custom [TUI](https://en.wikipedia.org/wiki/Text-based_user_interface) (text-based user interface).
  - It is opened by bare `kk` (inside a registered repo) or by the overlay keybinding.
  - It is transient. It is dismissed on switch, on `q` or `esc`, or on completing a verb.
  - Whenever no overlay is available, bare `kk` prints the `kk ls` listing instead. That covers three cases: before the overlay ships, outside a registered repo, and when `kk` is not running on an interactive terminal (see [Commands](../09-commands.md)).
- **Shell pane**: the `shell` role pane: the user's `$SHELL` at the jj workspace path. It sits beside the agent pane in the same tab (default position: below; configurable to the right). On by default. Detailed semantics in [Shell pane](#shell-pane).
- **UI pane**: the optional `ui` role pane: a narrow, navigation-only pane that keeps the Stack tree permanently visible. Off by default. Detailed semantics in [UI pane](#ui-pane).
- **Stack section**: the threads in the current repo, rendered as a [follows](../appendix-a-glossary.md#follows)-aware tree in `kk log` order. Cursor moves here for navigation.
- **Activity section**: the same threads, flat-listed by most-recent agent event (descending). Cursor moves here for triage. It appears in the overlay only. Outside the overlay, the Herdr sidebar carries the ambient attention role.
- **[Preview pane](../appendix-a-glossary.md#preview-pane)**: the right two-thirds of the overlay. It renders one of: transcript tail, working-copy diff, PR comments. Toggled by `t` / `d` / `c`. It is a region of the overlay, not a Herdr pane.
- **[Chord ribbon](../appendix-a-glossary.md#chord-ribbon)**: a one-line keybinding hint at the bottom edge of the overlay. Toggled by `?`. It adapts to the current selection (e.g. it hides `c` for a thread without a PR).
- **Inlined status**: the per-thread status block the Stack section renders under the _current_ thread's [bookmark](../appendix-a-glossary.md#bookmark) line. It reuses `StatusRenderer --no-jj` byte-identically with `kk status` (see [Commands](../09-commands.md)). Single source of truth.
- **Checkpoint lag**: a normal active-thread condition in which the tracked [checkpoint target](../appendix-a-glossary.md#checkpoint-target) trails the jj workspace's persisted [live head](../appendix-a-glossary.md#live-head). This is the `behind` relationship of `kk status`.
  - Detailed status labels it `checkpoint behind head`.
  - Compact TUI surfaces append `↑` to the bookmark.
  - The other relationships (`current`, `ahead`, `diverged`) are spelled out in the inlined status.
  - A freshly reopened thread reads `current` and shows no `↑`. So does a thread whose head is an empty commit on top of the checkpoint.
  - This is not dirty state or cascade conflict.
- **[Context strip](../appendix-a-glossary.md#context-strip)**: the bottom-most line of the overlay or the UI pane. One compressed sentence with TUI-specific content. It has two forms by context:
  - The overlay form carries repo + bookmark + cascade glyph + agent model + ctx % + last op age.
  - The UI-pane form is shorter: bookmark, cascade glyph, and agent dot. It has no dirty marker. The agent pane next to it already surfaces model and ctx.
  - [Context strip](#context-strip) below is the one full definition of both forms.
  - This is a TUI footer, separate from the `StatusRenderer`-backed inlined status.
- **Toast**: a non-modal floating pill in the overlay's top-right corner.
  - It is used for cascade events, agent finish/error notifications, the close proposal after a PR merge, and config-set warnings.
  - It auto-dismisses after `[ui] toast_ttl_ms` (default 4000).
  - It carries at most one optional named action. The action never performs or confirms anything consequential.
  - A **Herdr toast** is a different thing: Herdr's own notification, used as one attention transport (see [Toasts](#toasts)).
- **Card**: a centered modal panel with title, body, and one or two action buttons. Used for spawn input and foreground approval.

### What the overlay may read

The overlay follows these rules about what it reads and with what authority:

- It authenticates ordinary current-thread reads with the contextual thread credential (the [`ThreadScoped<T>` credential](../appendix-a-glossary.md#threadscoped-credential) of the thread it runs in).
- It consumes the repo-summary stream for every other row. See [repo-summary read scope](../appendix-a-glossary.md#repo-summary-read-scope).
- It never treats cursor position as authority.
- Opening transcript, diff, PR-comment, or detailed-audit content for a non-current thread enters the foreground approval flow before fetching content.
- The approved response is one immutable snapshot. It is bound to the method, target, query, and repository observation.
- Refreshing that snapshot, changing tabs, expanding its range, or opening the full reader requires a new challenge.
- No sensitive bytes are fetched speculatively behind an approval card.

## Native and custom surfaces

Kiki reuses [Herdr](../appendix-a-glossary.md#herdr)'s UI where it already answers the need. Kiki builds UI only where the need is kiki-specific. The decision is recorded in [Terminal runtime · Native and custom UI](../13-architecture/terminal-runtime.md#native-and-custom-ui). This chapter specifies the result.

| Need                                                                       | Surface                                                          | Owner                                 |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------- |
| Panes, splits, tabs, scrollback, copy mode, mouse, resize                  | Herdr, unmodified                                                | Herdr                                 |
| A cross-repo list of threads with attention state                          | the Herdr sidebar, fed by kiki's label and tokens                | Herdr draws; kiki publishes           |
| Ambient "something needs you" while heads-down                             | Herdr sidebar tokens and Herdr toasts, plus OS notifications     | Herdr and the OS draw; kiki publishes |
| Moving between threads                                                     | Herdr's own navigation, and `kk switch`                          | each Herdr client                     |
| The follows tree, stack-aware log, transcript and diff preview, spawn form | the `kk` overlay                                                 | kiki                                  |
| Approval cards                                                             | the enrolled `ApprovalPresenter`, in its own foreground terminal | kiki, always                          |
| A permanently visible Stack tree                                           | the optional UI pane                                             | kiki                                  |

The [`ApprovalPresenter`](../appendix-a-glossary.md#approvalpresenter) is the `kk` process that is allowed to show and confirm an approval.

This chapter relies on several Herdr behaviors that are known only from reading Herdr's source at the candidate revision. They have not yet been exercised against a running candidate build:

- popups (one per server, shown to every client viewing the owning tab);
- keybinding commands and the `HERDR_ACTIVE_*` ids they receive;
- plugin panes;
- toast delivery and its one-per-second limit.

Each is an [acceptance gate](../appendix-a-glossary.md#acceptance-gate) recorded in [Terminal runtime](../13-architecture/terminal-runtime.md#what-exists-what-kiki-builds-what-herdr-must-add), not an established fact. Where a gate fails, the surface that depends on it changes. The rules below do not.

Three rules follow:

- Kiki does not rebuild what Herdr provides. There is no kiki pane manager, tab bar, scrollback viewer, or status line.
- Nothing Herdr draws is an input to kiki. Labels, tokens, Herdr's agent states, and pane placement are presentation. Kiki never reads a decision out of them.
- A Herdr keybinding, plugin action, or sidebar click may open a kiki surface or move a view. It is never an approval. It never carries more authority than the `kk` process it starts.

## Glyph language

A glyph is a small symbol that stands for a state. Each row shows at most two glyphs. PR appears inline as `#NNNN` only if set.

| state                   | glyph | color  |
| ----------------------- | ----- | ------ |
| cascade in sync         | `──`  | dim    |
| cascade pending         | `↻`   | amber  |
| cascade conflicted      | `✗`   | red    |
| agent idle              | `○`   | dim    |
| agent working           | `●`   | amber  |
| agent finished          | `✓`   | green  |
| agent blocked           | `◐`   | red    |
| lifecycle in progress   | `…`   | amber  |
| lifecycle repair needed | `!`   | red    |
| lifecycle closed        | `□`   | dim    |
| follows arrow           | `←●`  | dim    |
| current thread mark     | `▸`   | accent |

Cascade conflicted (`✗`) and agent blocked (`◐`) are different glyphs on purpose. A conflicted cascade and a blocked agent need different actions, and one row can show both.

The cascade indicator uses the same three-valued state model as `kk status` (`in sync`, `pending`, `conflicted`). A cascade is how a parent thread's change reaches the threads that follow it; see [cascade reconciliation](../appendix-a-glossary.md#cascade-reconciliation).

The lifecycle glyph can replace the agent glyph. The states named below are [thread lifecycle states](../appendix-a-glossary.md#thread-lifecycle-states):

- For `Creating | ClosePreflight | CloseCommit | DestroyCommit`, lifecycle `…` replaces the agent glyph.
- A `Closed` thread with a `Reopen` operation in progress also shows `…`, with words that say a reopen is running. This row appears in the default `kk ls` and in the overlay without asking for closed rows, because the thread is on its way back to `Active`.
- For `CreateFailed | CloseFailed | ProjectionDiverged | DestroyFailed`, `!` replaces it, and the literal lifecycle label appears in detail.
- `□` identifies a closed row when closed rows are requested. `kk ls --all` and `kk log --all` request them on the command line. In the overlay, `a` turns them on and off (see [Keymap](#keymap)).
- `Destroyed` rows are hidden unless an explicit future destroyed-thread view requests them.
- Active rows use the normal [agent display states](../appendix-a-glossary.md#agent-display-states).

This replacement rule preserves the two-state-glyph limit.

The same glyphs appear in the overlay, the UI pane, `kk log`, and the tokens kiki publishes to the Herdr sidebar. Herdr has its own agent detection (`idle | working | blocked | done | unknown`). That detection is a screen-and-process heuristic (an educated guess), and it is not this table's agent state. Kiki's agent glyph comes from kiki's [`AgentStatus`](../appendix-a-glossary.md#agentstatus). If a Herdr sidebar row also shows Herdr's detected state, it is a hint, and kiki's token is the kiki state.

Every state in this table must be distinguishable by glyph alone, not by color. Color is an accelerator: it makes scanning faster. But [`NO_COLOR=1`](https://no-color.org/) and color-blind palettes must still convey the state. The [`LogRenderer` and `StatusRenderer`](../appendix-a-glossary.md#logrenderer-statusrenderer) projections strip color when `NO_COLOR=1` is set in the environment. They rely on glyph + label to carry the signal. See [Invariants](../02-invariants.md).

## Overlay

The [overlay](../appendix-a-glossary.md#overlay-tui) is kiki's interactive screen for browsing and acting on [threads](../appendix-a-glossary.md#thread). It opens in `NAVIGATE` mode in one of two ways:

- **Bare `kk`** typed in a pane, or in any other terminal inside a registered repo, runs the overlay inline. It fills that pane or terminal.
- **The overlay keybinding** opens the same `kk` process as a [Herdr](../appendix-a-glossary.md#herdr) popup over the current view.
  - Kiki writes this binding into the `keys.command[]` table of its generated Herdr configuration. The user does not hand-edit Herdr's keymap to get it.
  - Herdr gives the popup process `HERDR_ACTIVE_WORKSPACE_ID`, `HERDR_ACTIVE_TAB_ID`, and `HERDR_ACTIVE_PANE_ID` (and no `HERDR_PANE_ID`).
  - [`kkd`](../appendix-a-glossary.md#kkd) (kiki's daemon) verifies them before `kk` uses them to locate the current thread.
  - That locator serves reading and navigation only. Every mutation the overlay starts still needs the thread credential and, where required, approval.

Either way the overlay is an ordinary `kk` process with its own terminal. It holds no authority the same command typed in a shell would not hold.

A popup has consequences the inline form does not. All of them come from source reading and are inside the gate named above:

- Herdr shows one popup per server. While one client has the overlay open as a popup, another client's overlay keybinding cannot open a second one. Bare `kk` in a pane still works.
- A popup is visible to every client viewing the tab it was opened over. It closes when that tab goes away.
- A popup's process appears in no Herdr pane listing. The overlay therefore changes its [working directory](https://en.wikipedia.org/wiki/Working_directory) out of the jj workspace as soon as it starts. This way it is never an unlisted [holder](../appendix-a-glossary.md#holder) of the workspace. Holder scans do not count the invoking `kk` process.

The overlay is focused on the current thread. It resolves that thread via the standard CLI [context-resolution](../09-commands.md#context-resolution) chain. Two fallbacks apply:

- If no current thread resolves but the repo is registered, the cursor lands on the most-recently-active thread in the repo.
- If the repo has no threads, the overlay shows an empty-state placeholder ("no threads — press `n` to create one"), with `n` and `?` as the only active verbs.

`enter` on a thread row is `kk switch` for the caller's client, under the same contract (see [Commands](../09-commands.md#kk-switch)). These rules decide who the caller is and what happens:

- The caller is the client that pressed the overlay keybinding, or the foreground client showing the pane where `kk` was typed.
- An overlay running in a terminal that is not a [Herdr client](../appendix-a-glossary.md#herdr-client) has no caller client. There, `enter` moves no one and names `kk attach <thread>`.
- If Herdr does not advertise [`client_targeted_focus`](../appendix-a-glossary.md#client-targeted-focus), `enter` fails with the same message as `kk switch`, and the overlay stays open.
- The overlay never moves every attached client.

The overlay is one screen, three regions stacked vertically:

1. Top: a single-line breadcrumb, `kiki · NAVIGATE · <repo>/<thread>`.
2. Middle: a fixed-width [thread list](../appendix-a-glossary.md#thread-list) on the left (Stack on top, Activity on bottom) and a flexible-width [preview pane](../appendix-a-glossary.md#preview-pane) on the right.
3. Bottom: a one-line [context strip](../appendix-a-glossary.md#context-strip). An optional [chord ribbon](../appendix-a-glossary.md#chord-ribbon) hovers above it when `?` is held.

### Wireframe: bare overlay open

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
 ✗ session-recall conflicted        │
 ○ agent-tui      idle     1h12m    │
 ✓ minimal-foot   finished   8m     │
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  pi/codex-conv*  ↻ pending  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

### Wireframe: `t` opens transcript tail in the preview pane

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
 ✗ session-recall conflicted        │   yes — match the testing.md cascade list
 ○ agent-tui      idle     1h12m    │
 ✓ minimal-foot   finished   8m     │  ── more above (T to open full reader) ─────────
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  pi/codex-conv*  ↻ pending  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

`T` (shift-t) escalates from preview-tail to a full-screen `kk thread transcript` reader. `esc` returns to overlay.

The `d` preview below has two sources.

For the contextual thread, pressing `d` is an explicit, human-invoked passthrough:

- The overlay's `kk` process runs the diff in the caller's own jj workspace, exactly as `kk status --diff` does.
- It may snapshot the working copy (see [Commands](../09-commands.md#kk-status)). A [snapshot](https://docs.jj-vcs.dev/latest/working-copy/) is jj recording the current files as a commit.
- Those two, the `kk status` body and this `d` diff, are the only human-invoked CLI passthroughs.
- It runs only on that keypress, never on a timer or on cursor movement.

For any other thread, `d` keeps its approval rule. It renders from a [pinned read](../appendix-a-glossary.md#pinned-read) that ignores the working copy.

Everything else the overlay and the UI pane poll uses pinned reads only.

### Wireframe: `d` shows working-copy diff

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
 ✗ session-recall conflicted        │
 ○ agent-tui      idle     1h12m    │
 ✓ minimal-foot   finished   8m     │  ── jj st --diff (use `kk status --diff` to script)
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  pi/codex-conv*  ↻ pending  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

### Wireframe: `c` shows PR comments

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
 ✗ session-recall conflicted        │
 ○ agent-tui      idle     1h12m    │  (no transcript leakage — comments are gh,
 ✓ minimal-foot   finished   8m     │   not the local transcript store)
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  pi/codex-conv*  ↻ pending  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

### Wireframe: chord ribbon visible (`?` toggled)

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
 ✗ session-recall conflicted        │
 ○ agent-tui      idle     1h12m    │
 ✓ minimal-foot   finished   8m     │
 ── nav ↑↓ · ⏎ switch · space preview · t/d/c view · n new · N child · p publish · x
    close · i interrupt · a closed rows · T transcript reader · ? help · esc dismiss
 pi-extensions  pi/codex-conv*  ↻ pending  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

The ribbon adapts to selection:

- Closed rows are hidden until `a` shows them. `a` is always in the ribbon.
- For a closed thread, `i`, `p`, and `x` drop out, and `r` (reopen: see keymap below) appears.
- For a `Closed` thread with a reopen in progress, `i`, `p`, `x`, and `r` all drop out until the reopen finishes or fails.
- For a thread without a PR, `c` (preview comments) drops out independently.

### Wireframe: foreground approval card (`x` close on cursored thread)

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui                              ?  esc

 STACK                              │  pi-extensions/codex-conv-tui
                                    │
 ● main             ──    in        │  …
 │                                  │
 ●─pi/refactor      ↻   wrk       │   ╭─ Close pi-extensions/codex-conv-tui? ───╮
 │                                  │   │                                          │
 ●─pi/codex-conv ▸  ↻   ←●        │   │  Stops every process in the listed       │
 │                                  │   │  terminal group at freeze time: agent,   │
 ●─pi/agent-tui     ○     idle      │   │  shell, 1 user pane (5 found now).       │
                                    │   │  Forgets the jj workspace and removes    │
 ACTIVITY                           │   │  ~/code/pi-extensions-kiki-codex-conv.   │
                                    │   │  Tracked jj revisions are kept.          │
                                    │   │  PR #482 is left open (use --discard-pr).│
 ● codex-conv     working   2m18s   │   │  plan 7f3a91c2 · one use · expires 30s   │
 ● refactor       working    34s    │   │                                          │
 ✗ session-recall conflicted        │   │   ⏎  Close      esc  Cancel              │
 ○ agent-tui      idle     1h12m    │   ╰──────────────────────────────────────────╯
 ✓ minimal-foot   finished   8m     │
 ─────────────────────────────────────────────────────────────────────────────────────
 pi-extensions  pi/codex-conv*  ↻ pending  claude-opus-4-7  ctx ●●●●○ 78%  last op 12s
```

`i` (interrupt) shows the same shape; the body changes. `enter` confirms the daemon-issued challenge through the enrolled presenter. Then the exact operation retries with its one-use approval. There is no chord that fires destructive verbs in one keystroke.

Approval cards are always custom and always foreground-bound:

- The card is drawn by the `kk` process that is the enrolled [`ApprovalPresenter`](../appendix-a-glossary.md#approvalpresenter).
- That process draws it in the terminal it owns: the pane where `kk` was typed, or the popup the overlay keybinding opened.
- A Herdr toast, sidebar row, plugin popup that is not that `kk` process, or keybinding can never display or confirm an approval.

A close, destroy, or terminal-restart card says exactly what it covers:

- It lists the terminal containers it covers and the process inventory found at preflight.
- It states its scope: the approval covers every process in the listed terminal containers at freeze time.
- A process that joins a listed container after the card was drawn and before the freeze is covered by that statement.
- The card also names any outside holder of the workspace that the human is asked to accept.

An approval card needs a terminal its `kk` process owns in the foreground. A pane's PTY is the [controlling terminal](<https://en.wikipedia.org/wiki/Job_control_(Unix)>) of its child, so a `kk` typed in a pane qualifies. Whether a popup's terminal qualifies is part of the popup gate. Where it does not, the approval flow [fails closed](../appendix-a-glossary.md#fail-closed), and the same verb is available from `kk` in a pane. ("Fails closed" means the action is refused, not allowed by default.)

### Wireframe: spawn card (`n` for new thread, `N` for new-as-child-of-cursored)

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

`n` works like `kk new` typed on the command line. It opens this card with `follows` set to the contextual thread: the thread the overlay runs in. If the overlay has no contextual thread, `follows` starts at "── no follow". `N` opens the card with `follows` set to the cursored thread. In both cases the human can change the field, including to "── no follow", before submitting.

The `name` field is optional, as the name argument of `kk new [<name>]` is. Left empty, the thread gets the placeholder name `unnamed-<short-hex>` (see [Commands](../09-commands.md#kk-new)).

Submitting the spawn form begins the one-shot approval flow required by `kk new`. It does not itself satisfy that flow. The flow has two phases:

1. The daemon returns a canonical plan. The plan names the base/head, follows choice, workspace, harness, and initial-input digest.
2. The overlay displays that plan in an approval card and confirms it through its enrolled foreground presenter.

The same two-phase shape applies to publish, close, interrupt, reopen, and any cross-thread or consequential repair action. `kk thread destroy` has no overlay verb; it is CLI-only.

## Herdr sidebar projection

[Herdr](../appendix-a-glossary.md#herdr)'s native sidebar is the ambient [thread list](../appendix-a-glossary.md#thread-list). It replaces a kiki-drawn status strip, and it takes the ambient Activity and attention role. Kiki does not draw it. The user can hide or collapse it like any other Herdr UI.

Kiki publishes two things into it. Both are set by [`kkd`](../appendix-a-glossary.md#kkd), kiki's daemon:

- **Label.** `kkd` sets each [terminal group](../appendix-a-glossary.md#terminal-group)'s [Herdr workspace label](../appendix-a-glossary.md#sidebar-label). The label holds the repo's directory name, the thread's display name, and a short provisioning tag. It is for people and for discovery hints only.
- **Tokens (v1.x).** `kkd` publishes [metadata tokens](../appendix-a-glossary.md#sidebar-token) on each terminal group's Herdr workspace.
  - Kiki's generated Herdr configuration lays the sidebar entry out in two rows: the label on the first, the tokens on the second. It adds style rules.
  - The configuration sets a sidebar width that fits kiki's label within Herdr's allowed range.
  - Token keys and values stay within Herdr's limits: a key of at most 32 characters from `[A-Za-z0-9_-]`, and a value of at most 80 characters.
  - The generated configuration declares these tokens only when this surface ships.

| token             | content                                                                                                                     | example                                          |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `$kiki_follows`   | the follows arrow and parent thread name; empty when the thread follows nothing                                             | `←● refactor`                                    |
| `$kiki_cascade`   | the cascade glyph and its word                                                                                              | `── in sync`, `↻ pending`, `✗ conflicted`        |
| `$kiki_agent`     | the agent display state glyph and its word, for an `Active` thread                                                          | `○ idle`, `● working`, `✓ finished`, `◐ blocked` |
| `$kiki_lifecycle` | the lifecycle glyph and the literal lifecycle label, for a thread that is not `Active`; it takes the place of `$kiki_agent` | `… Creating`, `! CloseFailed`                    |

Every token carries its glyph and a word. So a row reads correctly with `NO_COLOR=1` and with any Herdr theme. Style rules may add color; they never carry a state on their own.

The [projection](../appendix-a-glossary.md#herdr-sidebar-projection) is one-way, and it is never authority:

- **Kiki republishes.** `kkd` republishes the label and every token after each state change and after every resync with the server. A token that was overwritten or lost in a server restart heals on the next publish.
- **Kiki never reads back.** Kiki never reads a label or token back. Any process on the server's socket can change them. A row is not evidence that a thread is `Active`, that an agent is ready, or that a cascade was delivered. `kk ls` and `kk status` report kiki's state.
- **Only bound groups get tokens.** Kiki publishes the label and tokens only to a terminal group with a current [binding](../appendix-a-glossary.md#terminal-binding).
  - A Herdr workspace that Herdr restored after a server restart is a [remnant container](../appendix-a-glossary.md#remnant-container).
  - A Herdr workspace the user created by hand is the user's.
  - Neither has kiki tokens. Its row shows whatever label Herdr kept and nothing from kiki.
  - A kept label does not tie a remnant to a thread.
- **The row is not a kiki control.** Selecting a row is Herdr's own navigation for that client. No kiki verb is bound in the sidebar. So it cannot spawn, publish, close, interrupt, or approve.

The sidebar lists terminal groups from every registered repo in one list. The label names the repo, so rows from different repos stay distinct.

### Wireframe: a Herdr client on the kiki server (Herdr sidebar · agent pane · shell pane)

```
 ╭─ kiki ───────────────────────────────╮ ╭─ agent · codex-conv ─────────────────────────────╮
 │                                      │ │                                                  │
 │   pi-extensions refactor 2c81        │ │ > human                                          │
 │     ↻ pending  ● working             │ │   could you check whether a materialized intent  │
 │ ▸ pi-extensions codex-conv 7f3a      │ │   is dropped on a hook crash before              │
 │     ↻ pending  ● working  ←● refactor│ │   MarkDelivered?                                 │
 │   pi-extensions agent-tui b0d4       │ │                                                  │
 │     ── in sync  ○ idle               │ │ ● working   2m 18s   esc to interrupt            │
 │   pi-extensions session-recall 9d1e  │ │                                                  │
 │     ✗ conflicted  ◐ blocked          │ │   reading kiki-core/cascade/intent_store.rs ...  │
 │   pi-extensions minimal-foot 51aa    │ │                                                  │
 │     ── in sync  ✓ finished           │ │                                                  │
 │   kiki-docs api-guide 3b7e           │ ╰──────────────────────────────────────────────────╯
 │     ── in sync  ● working            │ ╭─ shell ──────────────────────────────────────────╮
 │   kiki-www footer-year c02d          │ │ codex-conv $ jj st                               │
 │     ── in sync  … Creating           │ │ M  kiki-core/src/cascade/intent_store.rs         │
 │                                      │ │ Working copy : qxnopkyl 8a3c2d1e                 │
 │                                      │ │ codex-conv $ _                                   │
 │                                      │ │                                                  │
 │                                      │ │                                                  │
 │                                      │ │                                                  │
 │                                      │ │                                                  │
 ╰──────────────────────────────────────╯ ╰──────────────────────────────────────────────────╯
```

How to read the wireframe:

- The left region is Herdr's sidebar when it is shown. It has one entry per terminal group. The label (repo, thread, provisioning tag) is on the first row, and kiki's tokens are on the second.
- `▸` here stands for however Herdr marks the entry a client is viewing.
- The right region is the thread's first tab. The agent pane is on top, hosting the harness's PTY. The shell pane is below.
- The last entry shows a thread that is still `Creating`. Its lifecycle token stands where the agent token would be.
- The last two entries belong to other repos.

## UI pane

The UI pane is the optional [`ui` role pane](../appendix-a-glossary.md#ui-role-pane). It keeps the Stack tree permanently visible beside the agent. It is opt-in in two ways:

- via `[ui] ui_pane = true` in user config; or
- per thread via `kk new --ui-pane` / `--no-ui-pane` (see [Commands](../09-commands.md#kk-new)).

Herdr's sidebar is separate and is not controlled by these settings.

The pane's direct [PTY](https://en.wikipedia.org/wiki/Pseudoterminal) child is the kiki [pane launcher](../appendix-a-glossary.md#pane-launcher). The launcher claims the `ui` role and then replaces itself with the kiki UI process, `kk ui-pane`. `kk ui-pane` is a hidden, internal subcommand: only the `ui` pane launcher runs it, and [Commands](../09-commands.md) lists it as internal. That process reads through [pinned reads](../appendix-a-glossary.md#pinned-read) only and never snapshots a working copy. The pane is provisioned with an explicit working directory and environment, as every role pane is.

What it shows:

- It renders the overlay's Stack section, with the inlined status under the current thread.
- It renders in a narrow fixed-width pane (`[ui] ui_pane_width`, default 32 columns).
- It has no Activity section and no preview. The Herdr sidebar and the overlay cover those.

It is **navigation-only**:

- `j` / `k` / `↑` / `↓` move the cursor.
- `enter` switches the caller's client to the cursored thread under the `kk switch` contract.
- `?` toggles the [chord ribbon](../appendix-a-glossary.md#chord-ribbon) (showing only the navigation verbs).
- Mouse click on a row moves the cursor; scroll-wheel scrolls the tree.
- Spawn, publish, close, interrupt, reopen, and preview-toggle are not bound. Accidental focus on the UI pane cannot mutate state.
- Moving focus between panes is Herdr's own pane navigation.

The UI pane is ensured when the [terminal group](../appendix-a-glossary.md#terminal-group) is provisioned: at `kk new`, at `kk reopen`, and by the [`restart-terminal`](../appendix-a-glossary.md#restart-terminal) plan of `kk repair`. `kk switch` never creates it. The user may close the pane, or the UI process may exit so that Herdr removes the pane. In either case kiki does not put it back until one of those events.

### Wireframe: a thread's tab with the UI pane (UI pane · agent pane; Herdr's sidebar sits to the left of the tab as above)

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
 │ pi/codex  ↻ pending  ●      │ │                                                  │
 ╰─────────────────────────────╯ ╰──────────────────────────────────────────────────╯
```

The UI pane's [context strip](../appendix-a-glossary.md#context-strip) is shorter than the overlay's: just bookmark, cascade glyph, and agent dot, with no dirty marker (see [Context strip](#context-strip)). Model and ctx-% are omitted because they are agent-pane state, and the agent pane already shows them. The per-row inlined status under the current thread's bookmark line is unchanged from the overlay. It is the same `StatusRenderer --no-jj` projection.

## Shell pane

The shell pane is the `shell` [role pane](../appendix-a-glossary.md#role-pane): the user's shell at the thread's [jj workspace](../appendix-a-glossary.md#workspace) path, in the same tab as the agent pane. It exists so the user can interact directly with the same jj workspace the agent is operating in. The user can run `jj`, `gh`, tests, or any other command there without leaving the thread's [terminal group](../appendix-a-glossary.md#terminal-group). The agent pane and the shell pane share a working copy. What one writes, the other sees.

The shell pane is on by default (`[ui] shell_pane = true`). It is opt-out, not opt-in, because direct shell access alongside the agent is an expected component of the kiki experience, not an extra. When opted out, the terminal group's first tab contains only the agent pane (and the UI pane, if that is enabled).

In kiki's vocabulary, **the** shell pane is the singular `shell` role pane kiki provisions. If the user splits a pane or opens a tab natively in Herdr, that is a [user pane](../appendix-a-glossary.md#user-pane). Kiki does not recreate it and does not call it a shell pane.

### Launch

The shell pane is created by Herdr layout application with a direct argv command. ("Direct argv" means Herdr starts the program itself from an exact list of arguments.) It is never created by typing into another shell.

The pane's direct PTY child is the kiki [pane launcher](../appendix-a-glossary.md#pane-launcher). The launcher does three things in order:

1. It reports to [`kkd`](../appendix-a-glossary.md#kkd).
2. It claims the `shell` role for the thread's [terminal binding](../appendix-a-glossary.md#terminal-binding).
3. It replaces itself with the user's shell, taken from `$SHELL` (fallback `/bin/sh`).

Kiki passes the pane's working directory and its thread-specific variables explicitly in the provisioning call:

- the working directory is the jj workspace path;
- the explicit variables include `KIKI_THREAD_ID` and the thread's other context variables, so `kk` typed in the pane resolves the thread at the environment step of [context resolution](../09-commands.md#context-resolution);
- no `ApprovalPresenter` credential, reusable Admin credential, or credential bytes of any kind are placed in it.

Everything else in the shell's environment comes from the Herdr server. (The environment is the set of [environment variables](https://en.wikipedia.org/wiki/Environment_variable) a process starts with.)

- Every pane inherits the server's whole environment, plus Herdr's own `HERDR_*` variables and terminal settings.
- `kkd` starts the server with a deliberately constructed environment: the user's login baseline (`HOME`, `USER`, `SHELL`, `PATH`, locale). It does not use the environment of whichever terminal first ran `kk`.
- So the shell does not inherit the environment of the terminal that ran `kk new`. A variable exported there is not in the pane.
- `HERDR_CONFIG_PATH`, which points at kiki's generated configuration file, is visible inside every pane. It is a path, not a secret.

The agent pane differs in one respect. The harness's [launch specification](../appendix-a-glossary.md#launch-specification) removes every `HERDR_*` variable from the harness's environment and keeps `KIKI_THREAD_ID`.

### Layout

The shell pane lives in the same tab as the agent pane. By default it sits in a horizontal split below the agent (the agent on top, the shell on the bottom). Two keys configure this:

- `[ui] shell_pane_position` (`below` | `right`, default `below`);
- `[ui] shell_pane_size_pct` (int, default `25`).

`shell_pane_size_pct` is read as "the percentage of the dimension the split divides". That dimension is height when `position = below` and width when `position = right`. So the same key produces the analogous proportion under either orientation:

- Under the default `below` + `25`, the agent occupies the top 75% of height and the shell the bottom 25%.
- Under `right` + `25`, the agent occupies 75% of width on the left and the shell 25% on the right.

Kiki provisions the shell pane in the agent's tab by design, so the user can see one while interacting with the other. After provisioning, the layout is the user's. Herdr's native resize, zoom, and move apply, and kiki does not put panes back.

The table shows the four layout combinations of `[ui] ui_pane` × `[ui] shell_pane`, with the default `shell_pane_position = below`. Herdr's sidebar is outside the tab in every case:

| `ui_pane` | `shell_pane` | tab layout                                                                  |
| --------- | ------------ | --------------------------------------------------------------------------- |
| `true`    | `true`       | UI pane left (32 cols) · agent top-right (~75%) · shell bottom-right (~25%) |
| `false`   | `true`       | agent top (~75%) · shell bottom (~25%): full width                          |
| `true`    | `false`      | UI pane left (32 cols) · agent right (full height)                          |
| `false`   | `false`      | agent only: full tab                                                        |

Under `shell_pane_position = right`, the agent / shell rows flip orientation:

- The shell sits to the right of the agent, taking `shell_pane_size_pct` of width.
- The UI pane, when present, still occupies the leftmost 32 cols.

The UI pane's position is fixed. Only the shell pane's position is configurable.

The default layout (`ui_pane = false`, `shell_pane = true`) is the wireframe under [Herdr sidebar projection](#herdr-sidebar-projection).

`kk new`, `kk reopen`, and `kk switch` target the agent pane, so a client that arrives at a thread lands where the harness is. Kiki does not otherwise move pane focus.

### Lifecycle

- **`kk new`**: provisions the shell pane with the terminal group if `[ui] shell_pane = true`, before the harness starts.
- **`kk reopen <thread>`**: as `kk new`. The pane is provisioned fresh in a new terminal group. Shell history, scrollback, and any processes that were running before close are not preserved. The user's shell starts cold.
- **`kk repair` terminal restart**: the [`restart-terminal`](../appendix-a-glossary.md#restart-terminal) plan for a [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing) thread ensures the shell pane as at creation, with its explicit working directory and environment.
- **`kk switch <thread>`**: does nothing to the shell pane. Switch performs no terminal mutation and never re-creates a pane.
- **The shell exits or the user closes the pane**:
  - Herdr removes a pane when its direct command exits, so typing `exit` removes the shell pane.
  - The role is bound to that shell process, so it ends with it.
  - Kiki raises no issue and does not put the pane back until the next reopen or terminal restart.
  - A user who wants another shell splits one natively in Herdr.
- **A natively split pane** is a user pane. It inherits the server's environment like every pane, but not the shell pane's explicit variables. So it has no `KIKI_THREAD_ID`. `kk` typed there resolves the thread through its Herdr pane identity instead.
- **After a Herdr server restart**:
  - A restored pane is a [remnant pane](../appendix-a-glossary.md#remnant-pane): a plain shell with no role and none of kiki's explicit variables. It is not the shell pane.
  - `kk` typed there resolves the thread, if at all, from the working directory.
  - Kiki never reuses a remnant container. The `restart-terminal` plan closes each listed one with [verified exit](../appendix-a-glossary.md#verified-exit) and provisions a fresh terminal group with real role panes.
- **`kk close`**: ends the whole terminal group, and the shell pane goes with it. Kiki terminates every process running in the shell pane alongside the agent, under the approved plan, before the group is closed. See [Threads · close](../03-threads.md#close).

`kkd` does not manage what runs in the shell pane:

- It does not track which commands run there.
- It does not surface the pane's state in the overlay or the Herdr sidebar.
- It does not log audit rows for activity in it.

The user may do things there that kiki cares about, such as direct jj operations or gh interactions. Those route through the existing [op-log watcher](../appendix-a-glossary.md#op-log-watcher) and GitHub polling paths, as if the user had run them anywhere else. This is the [ambient-coordinator](../appendix-a-glossary.md#ambient-coordinator) stance applied to the shell pane: kiki sets it up, then gets out of the way.

`kkd` does observe the shell pane's processes when it must prove something about the workspace. This happens at `kk close` and `kk thread destroy`:

1. [`ProcessSupervisor`](../appendix-a-glossary.md#processsupervisor) takes the direct child of every pane in the terminal group as a root. The shell pane and user panes are included.
2. It [freezes](../appendix-a-glossary.md#freeze) each root with its descendants.
3. It verifies exit by OS process identity before the jj workspace is forgotten or deleted.

A background job started from the shell pane is therefore part of the close plan. A job that cannot be accounted for stops the deletion. It is never silently abandoned, and it is never silently killed outside the approved scope. When that happens kiki reports the pid ([process id](https://en.wikipedia.org/wiki/Process_identifier)), the command line, and the step that clears it.

### Authority

The shell pane runs the user's shell process at the user's UID (the user's own account). Kiki puts context identifiers in its environment and no credential.

- When the user invokes `kk`, context resolution names the thread, and the CLI loads only that thread's credential.
- Consequential operations enter the foreground one-shot approval flow. There, the `kk` process the user ran acts as the presenter in that pane.
- The CLI never auto-loads reusable Admin authority.
- The pane's environment never supplies the presenter credential.

See [Authority](../04-authority.md).

## Toasts

[Toasts](../appendix-a-glossary.md#toast) are non-modal pills in the overlay's top-right corner, stacking downward. ("Non-modal" means they do not block the rest of the screen.) Each carries one line of summary text: glyph, thread name, event, elapsed.

Two subtypes share the surface:

- **Notification toast**: no interactive action. The body may include hint text naming an overlay verb (e.g., "tap T to read transcript"). The verb is fielded by the overlay's normal keymap; the toast does not intercept it.
- **Actionable toast**: carries exactly one named action.
  - The action is invoked by clicking the action label, or by pressing the named key while the toast is the most-recent unactioned toast.
  - That key is the _only_ keystroke a toast intercepts. Everything else passes through to the overlay.
  - The action never performs or confirms a consequential operation.
  - At most it opens the overlay's approval card for a plan the daemon proposed, where the ordinary two-phase approval applies.
  - Dismissing or ignoring the toast changes nothing.

Dismissal rules (apply to both subtypes):

- auto-dismiss after the toast's TTL elapses (default `[ui] toast_ttl_ms` = 4000ms)
- click anywhere on the toast pill (excluding the action label, which runs the action) dismisses it
- moving the keyboard cursor onto the row that issued the toast, or clicking that row, dismisses the toast (treated as "user acknowledged")
- invoking the toast's action (actionable toasts only) dismisses the toast

Toast triggers (v1):

- agent finish (`✓`), the goal-complete event: notification. Its default level is `soft`: a status mark plus this overlay toast, and no OS notification or Herdr toast. [Configuration](../11-configuration.md) owns the per-event level table.
- agent error / blocked (`◐`): notification
- cascade conflict on a non-current thread (`✗`): notification
- cascade materialized for a child thread (`──`, only when ≥ 2 child reconciliations [coalesce](../appendix-a-glossary.md#coalescing)): notification
- config-set warning that won't take effect until next `kk new` / `kk reopen`: notification
- close proposed after a PR merge (`✓`), with a `review` action that opens the close plan's approval card (v1.x, with the GitHub integration, see [Publishing](../07-publishing.md)): actionable. Kiki never closes a thread by itself, and there is no undo grace: nothing happens until the human approves the card.

Overlay toasts are drawn only by the overlay. The UI pane hosts none, and kiki draws nothing over the live agent pane.

### Notifications outside the overlay

When no overlay is open, [attention events](../appendix-a-glossary.md#attention-event) travel on two channels:

- **The Herdr sidebar.** The thread's tokens change, so the entry shows the new glyph and word. This is passive: it needs a client to be attached, with the sidebar shown, and someone looking.
- **The configured notification transport**, `[notifications] os_provider` (`auto | notify-rust | osascript | herdr | off` (see [Configuration](../11-configuration.md) and [Observability](../12-observability.md)).

Whether an event uses each channel depends on its level (`loud | soft | silent`). Configuration owns the table of event keys, default levels, and what each level does on each surface. [Orientation](../01-orientation.md) lists which attention events the acceptance slice raises.

`os_provider = herdr` sends the event as a Herdr toast. Herdr's toasts are off by default; kiki's generated configuration turns them on for the dedicated server. A Herdr toast is offered to every client attached to the kiki server, and each client applies its own display policy.

A Herdr toast is global and best-effort:

- Herdr's reply to the request is not a display receipt.
- It reaches nobody when no client is attached.
- At the candidate revision Herdr accepts one such toast per second.
- Kiki does not queue or retry a dropped one.

That is acceptable because kiki's attention events are not caller-scoped. A cascade conflict or a blocked agent concerns the thread, not whoever ran a command. Nothing that must reach one specific person travels by Herdr toast.

A Herdr toast or an OS notification carries the same one-line summary as an overlay toast, with its glyph and words. It carries no action, intercepts no key, and never displays or confirms an approval. Actionable toasts exist only in the overlay. Outside it, the notification names the event and the user acts through `kk`.

### Wireframe: conflicted-thread toast in overlay

```
 kiki · NAVIGATE · pi-extensions/codex-conv-tui     ┌─────────────────────────────┐
                                                    │ ✗ session-recall conflicted │
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
 ●─pi/session-recall ✗    conflict

 …
```

## Forms

Spawn and approval cards are the only initial UI forms. Both:

- center on screen
- have a single labeled title row, a body, and one or two action buttons
- accept `enter` for the primary action and `esc` for cancel
- accept `tab` and `shift+tab` to move between fields, when there is more than one field

Forms are pure ratatui widgets drawn by the overlay's `kk` process. They are never Herdr popups of their own, plugin panes, or [toasts](../appendix-a-glossary.md#toast).

A form does not perform the operation. It starts an approval, in these steps:

1. Submitting a form calls `BeginApproval`. It does not perform the operation.
2. The approval card must display the daemon-returned canonical plan and digest byte-for-byte.
3. Only an enrolled foreground presenter may call `ConfirmApproval`.
4. After that, the overlay retries the exact operation with the resulting approval id.

A changed plan dismisses the stale card and starts again. The card surface stays inside the overlay process, but authority remains in the daemon challenge and one-use capability. See [human approval](../appendix-a-glossary.md#human-approval).

## Overlay state machine

The overlay is a small [state machine](https://en.wikipedia.org/wiki/Finite-state_machine): at any moment it is in exactly one of these states.

- `NAVIGATE`: default state. The thread-list cursor moves through Stack and Activity rows.
- `PREVIEW`: right pane is pinned to transcript tail, diff, or PR comments for the cursored thread.
- `APPROVE`: a sensitive read, spawn, or consequential verb waits on a daemon-issued foreground approval challenge.
- `SPAWN`: spawn form collects the thread name, follows target, harness, and UI-pane choice.
- `VIEWER`: full-screen transcript reader opened by `T`.

Leaving and switching:

- `q` and `esc` leave the overlay from `NAVIGATE`. From sub-states they return to the prior overlay state.
- `enter` only switches threads from `NAVIGATE` on a bookmark row.
- Destructive actions are unavailable from the UI pane and from the Herdr sidebar.

Reading content:

- For the current thread, `space`, `t`, `d`, and `T` may enter `PREVIEW` or `VIEWER` directly under [`ThreadScoped<T>`](../appendix-a-glossary.md#threadscoped-credential).
- For another thread, those keys enter `APPROVE`. Success installs only the approved immutable snapshot and then enters the requested view.
- `c` follows the same rule, because PR comments exceed the [repo-summary scope](../appendix-a-glossary.md#repo-summary-read-scope).
- Cancellation returns to `NAVIGATE` without issuing the read.

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
| `c`       | preview-mode = PR comments (preview only, not close)                            |
| `T`       | open full-screen transcript reader                                              |
| `n`       | spawn modal (new thread; follows the contextual thread by default, as `kk new`) |
| `N`       | spawn modal (new thread, follows cursored)                                      |
| `p`       | publish cursored thread (`kk publish`)                                          |
| `x`       | close cursored thread (opens approval card)                                     |
| `i`       | interrupt cursored thread's agent (opens approval card)                         |
| `r`       | reopen cursored thread (only meaningful when thread is closed; otherwise no-op) |
| `a`       | show or hide closed rows (off when the overlay opens)                           |
| `?`       | toggle chord ribbon                                                             |
| `q`       | dismiss overlay                                                                 |
| `esc`     | dismiss overlay                                                                 |
| click     | (mouse) move cursor to clicked row, or switch preview tab                       |
| scroll    | (mouse) scroll the focused region (thread list or preview)                      |

Note: `c` previews PR comments. Close is `x`. The binding favors the frequent read action and keeps closing behind a distinct key.

Closed rows start hidden, as in `kk ls`. Pressing `a` adds them to the Stack and Activity sections with the `□` glyph, the same rows `kk ls --all` lists. Pressing `a` again hides them. This is how the cursor reaches a closed thread so that `r` can reopen it. A `Closed` thread with a reopen in progress is shown either way, with `…`.

UI pane:

| key             | verb                                              |
| --------------- | ------------------------------------------------- |
| `↑` `↓` `j` `k` | move cursor                                       |
| `enter`         | switch the caller's client to the cursored thread |
| `?`             | toggle chord ribbon (read-only set)               |
| click           | move cursor to clicked row                        |
| scroll          | scroll the tree                                   |

The UI pane binds **no** verb that mutates state. Spawn, publish, close, interrupt, reopen, and preview-toggle are unbound. It binds no key for moving between panes; that is Herdr's own navigation.

The overlay keybinding is the only key kiki binds in Herdr's own keymap. The Herdr sidebar carries no kiki bindings. Every other Herdr key keeps Herdr's meaning.

## Context strip

One line at the bottom of the overlay. The UI pane has a shorter form, defined at the end of this section. The overlay's order, left to right:

`<repo>  <bookmark>[*][↑]  <cascade-glyph cascade-state>  <agent-model>  ctx ●●●●○ <pct>%  last op <duration>`

What each part means:

- `*` is the dirty marker for the current working copy, as of the last pinned observation. The strip never snapshots to compute it.
- `↑` means its tracked checkpoint target trails the persisted live head.
- `<cascade-glyph cascade-state>` is the kiki-CLI-shared three-valued indicator.
- `<agent-model>` is the harness-reported model name.
- `ctx` is the harness-reported context-window utilization.
- `last op` is the duration since the last jj op on the current thread. An op is one recorded jj [operation](https://docs.jj-vcs.dev/latest/operation-log/).

The UI pane's [context strip](../appendix-a-glossary.md#context-strip) is a shortened form: `<bookmark>[↑]  <cascade-glyph cascade-state>  <agent-glyph>`. Its three parts are the bookmark, the cascade glyph with its word, and the agent dot (the agent glyph alone, with no word). It has no dirty marker, because the UI pane uses pinned reads only and the shell pane beside it answers that question. Model and ctx are omitted because the agent pane next to it already surfaces them. This paragraph is the one definition of the UI-pane form; other sections point here.

The context strip is a TUI-specific footer and is **not** a `StatusRenderer` projection. The `StatusRenderer`-fed artifact is the _inlined status_ under the current thread's bookmark line in the Stack section. That artifact must be byte-identical with `kk status --no-jj` for the same thread and operation. [Testing](../14-testing.md) must hold a test that asserts it.

## Degradation

Degradation means what each surface does when it cannot work in full.

The overlay runs in a terminal: the pane where `kk` was typed, or the popup the keybinding opened. If that terminal is narrower than `[ui] overlay_min_cols` (default 80) when the overlay starts, the overlay refuses to open. It prints `kk ls` output instead, with a warning. There is no half-overlay state.

Role panes are not skipped for size. `kkd` provisions a terminal group whether or not any client is attached, so there is no terminal size to test at thread creation. A narrow client is handled by Herdr's own resize and zoom. The overlay is still available via bare `kk`.

Each surface degrades on its own, and none of them changes thread state:

- **Herdr sidebar hidden or collapsed.** That is the user's choice in Herdr. Kiki still publishes. The overlay, `kk ls`, and notifications are unaffected.
- **Agent-only terminal group.** With the shell and UI panes off, the agent pane is the group's only pane. If its launcher exits, Herdr removes the whole Herdr workspace and moves the viewing clients elsewhere. The thread reads [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing), as for any ended `agent` role.
- **Popup unavailable.** If another client already has a popup open, the overlay keybinding cannot open one. Bare `kk` in a pane still opens the overlay.
- **No client attached.** Nothing is drawn. Threads keep running, tokens are still published, and the configured OS notification transport still fires. `kk ls`, `kk status`, and `kk log` work from any terminal.
- **No [`client_targeted_focus`](../appendix-a-glossary.md#client-targeted-focus).** This is a required Herdr extension.
  - `kk switch`, the overlay's `enter`, and the UI pane's `enter` fail with a message that names the capability.
  - Kiki never substitutes a focus change that moves every client.
  - Herdr's own navigation still works, and so does the explicit `kk switch --all-clients`.
- **Tokens not shipped, lost, or overwritten.** The sidebar row shows the label alone, or a stale token, until the next publish. `kk ls` is the truthful list.
- **Herdr server restarted.**
  - Restored panes are remnant panes in containers without kiki's label updates or tokens.
  - Affected threads show `!` with their lifecycle label in the overlay and `kk ls`, with the reason `TerminalMissing`, until `kk repair` restarts them.
  - No surface shows an agent state for a thread that has no ready [incarnation](../appendix-a-glossary.md#incarnation) (running agent process).
- **A row too narrow** to render the full glyph + name + status in the overlay or UI pane truncates the name with a single-character ellipsis (no multi-character `…` wrap). Collapsed-summary lines from `kk log` follow the existing CLI rules. Truncation inside the Herdr sidebar is Herdr's.

## Mouse

Mouse capture is on by default (`[ui] mouse_enabled = true`). The following events are honored in v1:

- click on an overlay thread-list row → moves the cursor and dismisses any overlay toast issued by that row; the UI pane has no toast surface
- click on a UI pane row → moves the cursor
- click on a preview-tab letter (`t` / `d` / `c`) in the [preview pane](../appendix-a-glossary.md#preview-pane) header → switches preview mode, equivalent to pressing the corresponding key
- click on a toast pill, anywhere except the action label → dismisses that toast (notification [toasts](../appendix-a-glossary.md#toast) have no action label and dismiss on any click; actionable toasts dismiss everywhere except the labeled action)
- click on a toast's named action label (actionable toasts only) → invokes the action and dismisses the toast on completion
- scroll wheel on a focused pane → scrolls that pane

Drag, drag-resize, right-click context menus, click-and-drag selection, and hover/motion-driven UI are explicitly **out of v1 scope** for kiki's own surfaces.

Herdr owns the multiplexer. Pane selection, resize, text selection, scrollback, and clicks on the Herdr sidebar are Herdr's, and kiki does not contend with them. A click on a Herdr sidebar row is Herdr's navigation for that client; it invokes nothing in kiki.

If `[ui] mouse_enabled = false`, kiki's own processes do not request mouse capture and fall back to keyboard-only behavior. The key does not change Herdr's mouse handling.

## Configuration

[Configuration](../11-configuration.md) owns the key tables, types, defaults, and reload behavior. This section only names what the surfaces above read.

`[ui]` keys referenced by this spec:

- `ui_pane` (bool, default `false`): whether the UI pane is provisioned
- `ui_pane_width` (int, default `32`): the UI pane's width in columns
- `shell_pane` (bool, default `true`)
- `shell_pane_position` (string, default `"below"`)
- `shell_pane_size_pct` (int, default `25`)
- `mouse_enabled` (bool, default `true`)
- `overlay_min_cols` (int, default `80`)
- `toast_ttl_ms` (int, default `4000`)
- `theme` (string, default `"soft-dark"`)

All `[ui]` keys are personal preference. They are valid in user and per-thread config. They are invalid in repo-shared config, where they are warned-and-ignored. Reload behavior:

- `mouse_enabled`, `toast_ttl_ms`, and `theme` are cosmetic and hot-reload (they take effect without a restart). `theme` styles kiki's own surfaces; the [Herdr client](../appendix-a-glossary.md#herdr-client)'s theme is Herdr's.
- `overlay_min_cols` takes effect at the next overlay open.
- `ui_pane`, `ui_pane_width`, `shell_pane`, `shell_pane_position`, and `shell_pane_size_pct` take effect the next time a terminal group is provisioned: `kk new`, `kk reopen`, or a `kk repair` terminal restart. They do not reshape a live terminal group, and `kk switch` never applies them.

Outside `[ui]`:

- `[notifications] os_provider` selects the attention transport, including `herdr`; see [Notifications outside the overlay](#notifications-outside-the-overlay).
- `[terminal]` names the Herdr executable and the dedicated server's session name.
- `[paths] herdr_dir` holds kiki's generated Herdr configuration file and nothing else. Herdr keeps the session's socket and saved state under its own directories.
  - `kkd` regenerates and validates that file before every server start.
  - The file sets, among other things, the sidebar rows and width, the overlay keybinding, Herdr toast delivery, and `resume_agents_on_restore = false`.
  - That generated file is kiki's. The user's own Herdr configuration is never read or changed.
