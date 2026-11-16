# Storyboard

The earlier chapters describe what kiki does one verb at a time. This chapter describes what kiki feels like across one work-week. It follows a single developer through a porting project. The project crosses three repos. It tests every branching, merging, and abandoning pattern the rest of the book commits to.

The protagonist is unnamed. The work is to port the iOS Kestrel app to Android. Product is still iterating on the spec while the port happens. Two other repos — the user-facing docs and the marketing site — also need attention along the way. The three repos are:

- `kestrel-mobile` — the iOS/Android codebase, where the port lives.
- `kestrel-docs` — the user-facing product documentation.
- `kestrel-www` — the marketing site, where one copyright year is wrong.

The storyboard introduces no new commands, flags, glyphs, or screen elements. Every beat in it grounds out in the normative (binding) chapters:

- Where a beat is load-bearing, it cites the chapter that authorizes it.
- Where a beat would require behavior the rest of the book does not authorize, that gap is a finding. It is not a license to extend the surface here.

Transcripts and wireframes in this chapter render the fields the spec commits to in a plausible terminal shape. Exact spacing, column ordering, and any output text the spec does not pin are illustrative. They show what kiki _might_ look like in motion, not what an implementation must emit byte-for-byte. Three things do follow the spec: the glyphs, the committed cascade-state words (`in sync`, `pending`, `conflicted`), and the empty-state placeholder. What kiki says to an agent is defined by [Cascade](../05-cascade.md) and is not quoted here.

Acts are time-stamped (`Day · HH:MM — <repo>`) so the order of events is easy to follow. Over the week:

- product changes its mind twice;
- work stacks up;
- a thread is abandoned in flight;
- a cascade conflicts and recovers;
- a laptop reboots overnight;
- the week closes with a stack of merged PRs and a quiet TUI.

## Act 1 — Bootstrapping

### Mon 09:14 — kestrel-mobile, kestrel-docs, kestrel-www

`kestrel-mobile` is already kiki-registered. The developer brought it under management on a prior project, and no [threads](../appendix-a-glossary.md#thread) are in flight from that work. (A thread is kiki's unit of work: one line of changes with its own files, terminals, and agent.)

The two new-to-kiki repos for this week are `kestrel-docs` and `kestrel-www`. The developer runs `kk init` in each. `kk init` is [idempotent](https://en.wikipedia.org/wiki/Idempotence): running it again changes nothing. It never creates a starter thread (see [Commands · `kk init`](../09-commands.md#kk-init)).

```console
$ cd ~/code/kestrel-docs && kk init
registered  ~/code/kestrel-docs  (mon 2026-05-04 09:15:10)
threads     0 active, 0 closed
state       ~/.config/kiki/repos/9b0c1d4f/state.db

$ cd ~/code/kestrel-www && kk init
registered  ~/code/kestrel-www  (mon 2026-05-04 09:15:32)
threads     0 active, 0 closed
state       ~/.config/kiki/repos/2e7a8c5b/state.db
```

The developer returns to `kestrel-mobile` and types bare `kk`. The repo is registered and the TUI ships, so the [overlay](../appendix-a-glossary.md#overlay-tui) opens in `NAVIGATE` mode. The overlay is kiki's interactive screen. There are no threads to navigate, so it shows the empty-state placeholder, with `n` and `?` as the only active verbs (see [Interface · spec](spec.md#overlay)).

```text
 kiki · NAVIGATE · kestrel-mobile                                              ?  esc

 STACK                              │  no threads — press `n` to create one
                                    │
                                    │
                                    │
 ACTIVITY                           │
                                    │
                                    │
                                    │
 ─────────────────────────────────────────────────────────────────────────────────────
```

> kkd: [`kkd`](../appendix-a-glossary.md#kkd) is kiki's background [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>). `kk init` does two things:
>
> - It adds a row to `~/.config/kiki/state.db` (the cross-repo registry) under a freshly minted `<repo_id>` UUID.
> - It then creates `~/.config/kiki/repos/<repo_id>/` for per-repo runtime state. That directory holds `state.db` (including the daemon-enforced append-only audit table), gitignored config, per-thread credentials, and per-thread error logs.
>
> Nothing is written inside the source repo's filesystem.

## Act 2 — The skeleton thread

### Mon 10:42 — kestrel-mobile

The first [thread](../appendix-a-glossary.md#thread) will scaffold Android navigation: the gradle module, a top-level `NavHost`, and a Material 3 theme that mirrors the iOS app's tab structure.

Kiki runs its terminals in [Herdr](../appendix-a-glossary.md#herdr), a terminal multiplexer. Herdr's sidebar already gives a list of threads. With one thread there is no tree worth pinning. So the developer leaves the optional UI pane off for now (see [Interface · spec](spec.md#ui-pane)).

```console
$ kk new android-skel -m "Scaffold Android navigation: gradle module,
  NavHost, Material 3 theme. Match the iOS app's tab structure but use a
  NavigationBar rather than UITabBarController."
```

`kk new` runs a durable creation [saga](../appendix-a-glossary.md#saga): a multi-step operation that records each step so it can recover after a crash. The saga covers (see [Threads · creation](../03-threads.md#creation)):

- the thread row;
- the [jj workspace](../appendix-a-glossary.md#workspace) at `~/code/kestrel-mobile-kiki-android-skel/` (the thread's own copy of the files);
- the initial change and persisted [live head](../appendix-a-glossary.md#live-head);
- the checkpoint [bookmark](../appendix-a-glossary.md#bookmark);
- the per-thread credential;
- isolated [harness](../appendix-a-glossary.md#harness) settings (the harness is the agent program);
- the [terminal group](../appendix-a-glossary.md#terminal-group).

The terminal group is one Herdr workspace on the [dedicated server](../appendix-a-glossary.md#dedicated-herdr-server). It has an agent pane and a shell pane in its first tab. Each pane's direct child is the kiki [pane launcher](../appendix-a-glossary.md#pane-launcher). The harness launches last, after its [safe boundary](../appendix-a-glossary.md#safe-boundary) exists. The terminal group exists on the server whether or not anyone is looking at it.

The developer ran `kk new` in an ordinary terminal that is not a [Herdr client](../appendix-a-glossary.md#herdr-client). So there is no caller client to move. `kk new` succeeds, moves nobody's view, and prints how to reach the thread.

Moving no attached client's view while provisioning is kiki's contract. Whether Herdr's create and layout calls honor it with clients attached is still an unproven [acceptance gate](../appendix-a-glossary.md#acceptance-gate) (see [Commands · `kk new`](../09-commands.md#kk-new)).

The developer opens a view:

```console
$ kk attach android-skel
```

`kk attach` works in two steps (see [Commands · `kk attach`](../09-commands.md#kk-attach)):

1. It asks `kkd` to ensure the dedicated server is running.
2. It then runs Herdr's connect-only client for kiki's named session, with kiki's generated configuration file.

So this client can only land on kiki's server, never on a Herdr server the developer uses for other work.

This is the developer's terminal for the rest of the week. Herdr's sidebar is on the left with one entry: the label on its first row, kiki's tokens on its second. The agent pane is on top and the shell pane below it.

```text
 ╭─ kiki ───────────────────────────────╮ ╭─ agent · android-skel ───────────────────────────╮
 │                                      │ │                                                  │
 │ ▸ kestrel-mobile android-skel a41c   │ │ > human                                          │
 │     ── in sync  ● working            │ │   Scaffold Android navigation: gradle module,    │
 │                                      │ │   NavHost, Material 3 theme. Match the iOS app's │
 │                                      │ │   tab structure but use a NavigationBar rather   │
 │                                      │ │   than UITabBarController.                       │
 │                                      │ │                                                  │
 │                                      │ │ ● working   4s   esc to interrupt                │
 │                                      │ │                                                  │
 │                                      │ │   reading app/src/main/AndroidManifest.xml ...   │
 │                                      │ │                                                  │
 │                                      │ ╰──────────────────────────────────────────────────╯
 │                                      │ ╭─ shell ──────────────────────────────────────────╮
 │                                      │ │ android-skel $ _                                 │
 │                                      │ │                                                  │
 │                                      │ │                                                  │
 │                                      │ │                                                  │
 ╰──────────────────────────────────────╯ ╰──────────────────────────────────────────────────╯
```

The sidebar is Herdr's. Kiki publishes the thread's label and tokens into it and never reads them back. No kiki verb is bound there, so nothing done in the sidebar can spawn, publish, close, or interrupt. Consequential verbs use daemon-issued foreground approval cards in the overlay (see [Interface · spec](spec.md#herdr-sidebar-projection)).

> kkd: each creation step and compensation is journaled. A crash leaves `Creating` or `CreateFailed` for restart recovery. Kiki does not rely on a cross-system transaction.
>
> Kiki opens the agent launcher's [gate](../appendix-a-glossary.md#launch-gate) only after all of these are ready: the workspace, live head, checkpoint bookmark, credential, isolated hook settings, and terminal group. Only that [incarnation](../appendix-a-glossary.md#incarnation)'s settings-bound [ready handshake](../appendix-a-glossary.md#ready-handshake) activates the thread.
>
> Herdr's reply to the create call, the pane appearing, and Herdr's own agent detection are not evidence of any of it (see [Terminal runtime · provisioning](../13-architecture/terminal-runtime.md#provisioning)).

## Act 3 — Branching off for auth

### Mon 14:20 — kestrel-mobile

The skeleton thread is partway through wiring the `NavHost` and theme. The auth flow needs a parallel [thread](../appendix-a-glossary.md#thread) to start on. Auth depends on the navigation skeleton — the `login` destination, the back-stack rules. But it doesn't need to wait for the skeleton to finish.

The developer spawns a child thread that [follows](../appendix-a-glossary.md#follows) the skeleton. Following is a live link from a child thread to a parent thread. Two things come from it (see [Cascade · classification](../05-cascade.md#classification)):

- Future native rewrites will [materialize](../appendix-a-glossary.md#materialization) in `auth` at its boundary. To materialize is to update the files on disk to match what jj recorded.
- Future parent tips will explicitly advance `auth` there.

```console
$ kk new auth --follows android-skel -m "Implement password login against the
  existing iOS endpoints. The NavHost in android-skel has a `login` destination
  scaffolded; wire onSuccess to pop to the home tab."
```

`--follows` records a live edge from `auth` to `android-skel`.

With a second thread the stack has a shape. So between threads the developer added `[ui] ui_pane = true` to user config. `auth`'s tab comes up with a narrow UI pane showing the Stack tree beside the agent (see [Configuration](../11-configuration.md)). `android-skel`'s live [terminal group](../appendix-a-glossary.md#terminal-group) is not reshaped. Herdr's sidebar now has two entries, and `auth`'s entry carries the follows token `←● android-skel`.

A bare `kk` in either thread now opens the [overlay](../appendix-a-glossary.md#overlay-tui) with both threads in the Stack tree. The follows arrow `←●` marks the auth thread as a child of `android-skel`. `▸` marks whichever thread the cursor is on.

```text
 kiki · NAVIGATE · kestrel-mobile/auth                                         ?  esc

 STACK                              │  kestrel-mobile/auth
                                    │
 ● main             ──    in        │  bookmark    auth
 │                                  │  cascade     ── in sync
 ●─android-skel     ──    wrk       │  agent       ● working    34s
 │                                  │  pr          —
 ●─auth          ▸  ──    ←●        │  follows     android-skel → main
                                    │  workspace   ~/code/kestrel-mobile-kiki-auth
                                    │
 ACTIVITY                           │  ─ preview ────────────────────────────────────
                                    │
 ● auth           working     34s   │
 ● android-skel   working   3h41m   │
                                    │
 ─────────────────────────────────────────────────────────────────────────────────────
 kestrel-mobile  auth  ── in sync  claude-opus-4-7  ctx ●●●○○ 41%  last op 12s
```

Both threads are working concurrently. The Stack section orders them by `kk log` (parent above child). The Activity section orders the same threads flat by most-recent agent event. `tab` jumps the cursor between the two sections. `enter` switches the developer's own [Herdr client](../appendix-a-glossary.md#herdr-client) to whichever thread the cursor is on (see [Interface · keymap](spec.md#keymap)).

The follows [DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph) (a graph with no loops) is, for now, two hops deep: `main → android-skel → auth`. Each active thread follows its parent's persisted workspace head. It does not assume that jj automatically advances bookmarks. jj may evolve several descendant commits in one operation. Kiki still materializes and explains each affected workspace independently.

## Act 4 — Product changes their mind (small)

### Tue 11:00 — kestrel-mobile

Overnight, the navigation skeleton settled into a clean shape. Product responded with a small correction: the bottom-bar tab order should put `Library` left of `Discover`, not right.

The change is small enough that the developer makes it directly, without spawning a [thread](../appendix-a-glossary.md#thread) for it. They switch to `android-skel` and move focus to the [shell pane](../appendix-a-glossary.md#shell-pane) below the agent. The shell pane is already cd'd into the jj workspace and already running their `$SHELL`. They amend the relevant revision by hand:

```console
$ cd ~/code/kestrel-mobile-kiki-android-skel
$ jj describe -r @- -m "Scaffold Android navigation: NavHost + Material 3 + bottom NavigationBar (Library, Discover, Profile)"
```

They run `jj` directly. Kiki does not refuse direct `jj` or `gh` operations, or native Herdr use. It watches the op log ([jj's operation log](https://docs.jj-vcs.dev/latest/operation-log/)) and reacts to whatever it sees (see [Invariants](../02-invariants.md)).

jj evolves `auth`'s descendant commit in shared repository state as part of the ancestor rewrite. But `auth`'s on-disk files remain at their previously materialized state.

> kkd: the [op-log watcher](../appendix-a-glossary.md#op-log-watcher) compares the before/after operation views. `auth` already descends from the evolved `android-skel` base. So the watcher classifies [`NativeRewrite`](../appendix-a-glossary.md#nativerewrite) and stores that exact [base transition](../appendix-a-glossary.md#base-transition) in a [`sync_intent`](../appendix-a-glossary.md#sync-intent), kiki's durable record of one reconciliation. It does not schedule another rebase for work jj already evolved (see [Cascade · classification](../05-cascade.md#classification)).

A few seconds later, the auth agent finishes the function it was writing and prepares its next [tool batch](../appendix-a-glossary.md#tool-batch) (the tool calls an agent sends together). The steps that follow are (see [Cascade · delivery protocol](../05-cascade.md#delivery-protocol)):

1. Kiki's exclusive [`PreToolUse`](../appendix-a-glossary.md#pretooluse) hook first binds a durable `Block` barrier for the entire batch.
2. It then probes the workspace.
3. Because the workspace is provably stale and clean, the orchestrator [materializes](../appendix-a-glossary.md#materialization) its evolved state. It stores the result, payload, anchor, and `Materialized` state.
4. Every call in that tool batch remains blocked.
5. `PostToolBatch` closes the soft-delivery barrier.
6. Only a later [model turn](../appendix-a-glossary.md#model-turn) may acknowledge the intent.

The glyph shows in two places: the overlay's Stack row, and the cascade token on `auth`'s row in Herdr's sidebar. In both, it briefly flips through `↻` (pending) and back to `──` (in sync) once the agent acknowledges.

No toast fires for this cascade. The toast trigger for coalesced child materialization only fires when at least two child reconciliations [coalesce](../appendix-a-glossary.md#coalescing) (see [Interface · toasts](spec.md#toasts)), and `auth` is the only affected thread.

The agent's view of the change is a single synthetic turn explaining what evolved and which files were materialized. The developer's view is a momentary glyph flip on one row. Neither has to coordinate further. The act is intentionally undramatic. That is what an [ambient coordinator](../appendix-a-glossary.md#ambient-coordinator) looks like when it's working.

## Act 5 — Cross-repo interlude: the copyright bump

### Tue 16:45 — kestrel-www

In the middle of the auth work, the developer remembers that the marketing site's footer still says "© 2025". They do not interrupt either of the kestrel-mobile [threads](../appendix-a-glossary.md#thread). They open a separate terminal window, change directory, and spawn a third thread in a different repo:

```console
$ cd ~/code/kestrel-www
$ kk new copyright-2026 -m "Bump copyright year in the footer to 2026.
  The string lives in components/Footer.tsx — replace the literal year
  only, do not touch any other footer copy."
```

The new thread has no [follows](../appendix-a-glossary.md#follows) link. `kestrel-www` has no other kiki threads, and no parent makes sense. That window is not a [Herdr client](../appendix-a-glossary.md#herdr-client), so again nobody's view moves.

The new thread gets its own [terminal group](../appendix-a-glossary.md#terminal-group) on the same server. Herdr's sidebar in the developer's client now lists three entries from two repos in one list. The developer selects the new entry there — Herdr's own navigation — and works from that thread's shell pane.

The agent edits one line. A minute later, the developer reviews the diff in the overlay's [preview pane](../appendix-a-glossary.md#preview-pane) (`d`), is satisfied, and publishes:

```console
$ kk publish --ready -m "Bump copyright year to 2026"
```

`--ready` opens the PR ([pull request](https://docs.github.com/en/pull-requests)) ready for review rather than as a draft (see [Publishing · defaults](../07-publishing.md#defaults)). The base branch resolves to `main` because the thread has no follows ancestor (see [Publishing · PR base](../07-publishing.md#defaults)). CI is green within a minute. Marketing's reviewer approves. The developer merges via `gh pr merge` directly — kiki does not gate that — and closes the thread:

```console
$ kk close
```

`kk close` needs a quiet agent; this one finished minutes ago. The close runs in this order (see [Threads · close](../03-threads.md#close)):

1. Preflight takes its [boundary snapshot](../appendix-a-glossary.md#boundary-snapshot) and builds the plan.
2. Kiki shows the plan in an approval card. The card lists the terminal group's processes. It says the approval covers every process in that group at freeze time.
3. On the developer's `enter`, kiki [freezes](../appendix-a-glossary.md#freeze) every process in the terminal group: the agent, the shell, anything else running in its panes.
4. It repeats its loss check, checkpoints the [bookmark](../appendix-a-glossary.md#bookmark), and runs its [final proof](../appendix-a-glossary.md#final-proof).
5. Kiki then terminates the frozen processes itself and verifies each exit by OS process identity.
6. Only after that does it ask Herdr to close the terminal group, recheck the filesystem, forget the jj workspace, delete the materialized directory, and mark the thread `Closed`.

Herdr's reply to the close request is cleanup, not proof. The [verified exit](../appendix-a-glossary.md#verified-exit) is the proof. If a check had failed before the termination, the same processes would resume. The thread would not become a dead `Active` row.

The developer typed `kk close` in the thread's own shell pane, so that `kk` process ends with the group. `kk ls` carries the result. The thread's entry leaves Herdr's sidebar, and Herdr places the developer's client on one of the remaining terminal groups.

Total wall time on the copyright bump: about twelve minutes. Nothing in `kestrel-mobile` was perturbed. The two `kestrel-mobile` threads remain active. `kestrel-www` now has one closed thread.

## Act 6 — The docs thread, started in parallel

### Wed 09:14 — kestrel-docs

Wednesday morning, product asks for first-pass documentation of the Android setup story. Beta testers should have something to read alongside the build they are about to receive. The docs live in their own repo. The developer spawns a [thread](../appendix-a-glossary.md#thread) there:

```console
$ cd ~/code/kestrel-docs
$ kk new android-docs -m "Document the Android app's first-run flow:
  install from Firebase App Distribution, log in (password for now,
  biometric coming soon), grant notification permission, land on the
  Library tab. Match the structure of the iOS first-run page."
```

`kestrel-docs` has no other kiki threads either, so `android-docs` is parentless and follows nothing.

From any registered repo, `kk ls --all-repos` now lists every active thread across both repos (see [Commands · `kk ls`](../09-commands.md#kk-ls)):

- The exact column shape is up to the renderer. The spec commits to a `repo` column when the listing crosses repo scope, and to active-thread coverage.
- The listing the developer sees contains `kestrel-mobile/android-skel`, `kestrel-mobile/auth` (with its follows arrow back to `android-skel`), and `kestrel-docs/android-docs`.
- `--all` would include closed threads, like `copyright-2026`. It is independent of `--all-repos` and is not passed here.

The developer keeps moving between threads with `kk switch`, and sometimes by selecting a row in Herdr's sidebar. `kk switch` moves the client that ran it and no other. It does not mutate daemon focus state (see [Commands · `kk switch`](../09-commands.md#kk-switch)). This is [caller-local focus](../appendix-a-glossary.md#caller-local-focus).

Later that morning the developer runs `kk attach android-docs` in a second terminal window on another monitor, to keep the docs agent in view. Both clients are now attached to the same server. A `kk switch auth` typed in the first window moves the first window only. The docs view stays where it is.

That depends on the Herdr capability [`client_targeted_focus`](../appendix-a-glossary.md#client-targeted-focus). On a server without it, `kk switch` would refuse and name the capability rather than move both windows. The daemon is not "in" any thread; it is watching all of them.

## Act 7 — Product changes their mind (big)

### Wed 15:30 — kestrel-mobile

Mid-afternoon, product Slacks: scrap the password-first auth flow. Sales has been hearing repeated requests for biometric-first login from enterprise pilots. The team wants to ship the Android beta with that posture from day one. Password is now a fallback, not the front door.

The auth [thread](../appendix-a-glossary.md#thread)'s direction is wrong. Not in detail — fully. Closing it and starting a new one is cleaner than re-prompting the agent and watching it patch its way to a different posture.

The `auth` agent is mid-task, and close needs a quiet agent. So the developer first stops it in its own pane with the harness's `esc`. Then they open the [overlay](../appendix-a-glossary.md#overlay-tui), cursor to `auth` in the Stack, and press `x`. The overlay requests a daemon-canonical close challenge and displays its approval card (see [Interface · forms](spec.md#forms)):

```text
 kiki · NAVIGATE · kestrel-mobile/auth                                         ?  esc

 STACK                              │  kestrel-mobile/auth
                                    │
 ● main             ──    in        │   ╭─ Close kestrel-mobile/auth? ───────────────╮
 │                                  │   │                                            │
 ●─android-skel     ──    wrk       │   │  Stops every process in the listed         │
 │                                  │   │  terminal group at freeze time: agent,     │
 ●─auth          ▸  ──    ←●        │   │  shell, ui (3 found now).                  │
                                    │   │  Forgets the jj workspace and removes      │
                                    │   │  ~/code/kestrel-mobile-kiki-auth.          │
                                    │   │  Tracked jj revisions are kept.            │
                                    │   │  No PR is open.                            │
                                    │   │                                            │
                                    │   │   ⏎  Close      esc  Cancel                │
                                    │   ╰────────────────────────────────────────────╯
 ACTIVITY                           │
 ─────────────────────────────────────────────────────────────────────────────────────
 kestrel-mobile  auth  ── in sync  claude-opus-4-7  ctx ●●●○○ 41%  last op 12s
```

The developer presses `enter`. `kk close` then does the following, in order:

1. It [freezes](../appendix-a-glossary.md#freeze) and rechecks every process in the [terminal group](../appendix-a-glossary.md#terminal-group).
2. It checkpoints the bookmark without snapshotting or changing the frozen workspace.
3. It terminates the frozen processes with [verified exit](../appendix-a-glossary.md#verified-exit).
4. Then it closes the terminal group, forgets the workspace, and marks the thread `Closed`.

The developer specifically did not run `kk thread destroy`. That command is an irreversible deletion of kiki's thread record. It requires a one-use [human approval](../appendix-a-glossary.md#human-approval). It still preserves jj revisions unless a separate `--abandon-revisions` plan is approved (see [Threads · destroy](../03-threads.md#destroy)).

Then the developer spawns the replacement:

```console
$ kk new auth-biometric --follows android-skel -m "Biometric-first login,
  with password as a fallback for devices without enrolled biometrics.
  Use AndroidX Biometric. The login NavHost destination is in
  android-skel; pop to the home tab on success, fall through to the
  password form on biometric failure."
```

The Stack tree's shape is unchanged: there is still one thread following `android-skel`. But the slot now holds `auth-biometric`. The `auth` thread is gone from the active list. `kk ls --all` would still show it, marked closed (see [Commands · `kk ls`](../09-commands.md#kk-ls)).

## Act 8 — A cascade conflict

### Thu 10:08 — kestrel-mobile

Thursday morning, the `android-skel` [thread](../appendix-a-glossary.md#thread)'s agent adds a new navigation-refactor revision. It moves the auth-related destinations out of the root `NavHost` into a nested `loginGraph`.

The new parent tip is not yet in `auth-biometric`'s ancestry, so the watcher classifies [`ParentAdvance`](../appendix-a-glossary.md#parentadvance). That means the parent gained a new commit that the child does not yet contain. At `auth-biometric`'s next [safe boundary](../appendix-a-glossary.md#safe-boundary), the explicit advance onto that exact parent commit exposes textual conflicts in the same files the child changed.

The reconciliation's result contains [jj conflicts](https://docs.jj-vcs.dev/latest/conflicts/). So `auth-biometric`'s cascade status reads `conflicted`, and it stays `conflicted` for as long as the result does. Kiki tells the agent about the reconciliation through the delivery protocol, as [Cascade · conflicts and escalation](../05-cascade.md#conflicts-and-escalation) defines.

A loud notification fires. The cascade token on `auth-biometric`'s row in Herdr's sidebar changes to `◐ conflicted` in both of the developer's attached clients.

The developer happens to have the overlay focused on `android-skel`. From that vantage, `auth-biometric` is a non-current thread, so the conflict surfaces as a toast. [Toasts](../appendix-a-glossary.md#toast) for cascade conflicts only fire on non-current threads (see [Interface · toasts](spec.md#toasts)). The conflicted thread's row also turns red:

```text
 kiki · NAVIGATE · kestrel-mobile/android-skel      ┌────────────────────────────────┐
                                                    │ ◐ auth-biometric conflicted    │
 STACK                              │               │   tap T to read transcript     │
                                                    └────────────────────────────────┘
 ● main             ──    in        │
 │                                  │
 ●─android-skel  ▸  ──    wrk       │
 │                                  │
 ●─auth-biometric   ◐    ←●         │
                                    │
```

The overlay credential is contextual to `android-skel`. So activating `T` here would first display an exact sibling-read plan and require a one-use foreground approval. The developer does not request it. Switching into `auth-biometric` makes subsequent same-thread inspection contextual instead.

The developer cursors to `auth-biometric` and presses `enter`, which moves that client to the thread's agent pane. They move focus to the shell pane below the agent. They resolve the conflict by hand, rather than leave it to the agent. jj's conflict markup makes the merge tractable; the resolution touches three lines.

```console
$ cd ~/code/kestrel-mobile-kiki-auth-biometric
$ jj resolve
```

> kkd: the [op-log watcher](../appendix-a-glossary.md#op-log-watcher) sees the resolve op like any other external op. Once a later operation shows the thread's chain free of conflicts, its status leaves `conflicted` (see [Cascade · conflicts and escalation](../05-cascade.md#conflicts-and-escalation)). What the agent is told next is the delivery protocol's business, not the storyboard's.

The cascade glyph on `auth-biometric` returns to `──`. The conflict cost the developer about eight minutes of focused attention and zero corrupted state.

## Act 9 — Publishing the stack

### Thu 16:00 — kestrel-mobile

By late Thursday, the navigation skeleton is complete and the biometric-first auth flow works end-to-end against staging. The developer wants both [threads](../appendix-a-glossary.md#thread) in front of reviewers as a stack: skeleton at the bottom, auth-biometric on top. From the skeleton thread, they invoke a downstack publish:

```console
$ kk publish --downstack --ready
```

What the flags and the flow do:

- `--downstack` publishes the current thread plus unpublished descendants, top-down (see [Commands · `kk publish`](../09-commands.md#kk-publish)).
- `--ready` opens both PRs ready for review rather than as drafts (see [Publishing · defaults](../07-publishing.md#defaults)).
- Kiki publishes ancestors first, then descendants. Skeleton's PR is created with base `main`. Then auth-biometric's PR is created with base `android-skel`.
- Each PR opens a separate editor session with a non-transcript static template, so the developer writes its title and body.
- AI drafting belongs to the later metadata tranche and is not part of this publishing flow (see [Publishing · PR text](../07-publishing.md#pr-text)).

Once both editors close and `gh` returns success, `kk log --wide` shows the stack annotated with PR state, CI roll-up, agent state, and last-activity age (see [Commands · `kk log`](../09-commands.md#kk-log)):

```console
$ kk log --wide
●─auth-biometric  [#143] ●  "Biometric-first auth flow"  ready  ●●●●● ci green  working    34s
●─android-skel    [#142] ●  "Scaffold Android navigation"  ready  ●●●●● ci green  working   12m
●─main
```

Reviewers approve through the day; the skeleton PR merges first. Kiki polls GitHub through `gh` and notices the merge. What follows for `auth-biometric` (see [Cascade · parent merged](../05-cascade.md#parent-merged)):

1. Kiki records a [`ParentAdvance`](../appendix-a-glossary.md#parentadvance)-shaped transition to the exact merged default-branch commit.
2. At the child's [safe boundary](../appendix-a-glossary.md#safe-boundary) it rebases and materializes the child locally.
3. It then stops with a named remote-update plan. The plan covers the exact `--force-with-lease` push and the PR-base change.
4. The developer reviews that plan in the foreground and confirms a one-use approval.
5. Only after the claimed journal completes both remote effects does kiki drop the [follows](../appendix-a-glossary.md#follows) link.

Without approval, the child remains locally reconciled with `remote update pending` visible.

> kkd: the parent-merge work remains represented by four things: the exact-base [`sync_intent`](../appendix-a-glossary.md#sync-intent), the [follows edge](../appendix-a-glossary.md#follows-edge), the PR link, and the claimed remote-operation journal. The storyboard does not invent a second cascade lifecycle. The follows link is dropped only after local and approved remote updates succeed.

The `auth-biometric` row in the Stack updates after the parent-merge transition. The follows arrow `←●` disappears, since auth-biometric no longer follows anything. Shortly after, reviewers approve `auth-biometric` and that PR merges too. The week's port has landed on `main` as two clean commits.

## Act 10 — Closing out

### Fri 09:00 — across repos

The laptop installed an update and rebooted overnight. No process survives a reboot: the Herdr server, every agent, and every shell are gone.

[`kkd`](../appendix-a-glossary.md#kkd) comes back through its user service. It runs as a [launchd](https://en.wikipedia.org/wiki/Launchd) user agent, not as a child of any terminal, and it starts the Herdr server from there. The developer opens a terminal and runs `kk attach`, which asks `kkd` to ensure the dedicated server is running; `kkd` starts it again.

Herdr restores the layout it saved: three Herdr workspaces with their labels and working directories. It starts a plain shell in each pane. Each label still reads repo, thread, provisioning tag.

```text
 ╭─ kiki ───────────────────────────────╮
 │                                      │
 │   kestrel-mobile android-skel a41c   │
 │   kestrel-mobile auth-biometric e90b │
 │   kestrel-docs android-docs 5c12     │
 │                                      │
 ╰──────────────────────────────────────╯
```

The rows look like Thursday's, minus kiki's tokens. They are not [threads](../appendix-a-glossary.md#thread) coming back:

- Kiki disabled Herdr's agent auto-resume in the configuration it generated, so no harness was restarted.
- A restored pane has no launcher, no credential, no launch settings, and no [ready handshake](../appendix-a-glossary.md#ready-handshake).

`kk ls --all-repos` says what is true. `android-skel`, `auth-biometric`, and `android-docs` are each listed as `ProjectionDiverged` with the reason [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing). None is `Active`. (`ProjectionDiverged` is the [lifecycle state](../appendix-a-glossary.md#thread-lifecycle-states) for a thread whose outside pieces no longer match kiki's records.)

> kkd: the server it now talks to has a different `server_instance_id`. Every [binding](../appendix-a-glossary.md#terminal-binding) from the old instance is ended, and every incarnation is retired without acknowledgement.
>
> The [orphan](../appendix-a-glossary.md#orphan) scan finds none of the recorded process identities alive — a reboot leaves nothing — and no stray holder of any workspace. It does find the restored shells, whose working directories are inside the jj workspaces. Those are [remnant panes](../appendix-a-glossary.md#remnant-pane). The current snapshot names each one's pane and root process, so they are accounted terminal members, not orphans.
>
> No [`OrphanedProcess`](../appendix-a-glossary.md#orphanedprocess) issue is raised. Each thread gets `TerminalMissing` (see [Terminal runtime · runtime changes are reconciliation](../13-architecture/terminal-runtime.md#runtime-changes-are-reconciliation)).

The mobile work has merged, and the docs draft is committed and waiting on product. So the developer does not restart agents just to stop them. `kk repair` diagnoses a thread and names its plans: restart the terminal and agent, or [`close-without-terminal`](../appendix-a-glossary.md#close-without-terminal) (see [Commands · `kk repair`](../09-commands.md#kk-repair)). The developer takes the second.

```console
$ kk repair auth-biometric                  # read-only: prints the diagnosis and plan ids
$ kk repair auth-biometric --apply <repair-id>
$ kk repair android-skel --apply <repair-id>
$ cd ~/code/kestrel-docs && kk repair android-docs --apply <repair-id>
```

Each apply shows its approval card first:

- The card lists the [remnant containers](../appendix-a-glossary.md#remnant-container) whose shells hold that thread's jj workspace, with those processes.
- The card says the approval covers every process in the listed containers at freeze time.
- Kiki matched the containers to the thread by that OS evidence, not by the labels in the sidebar.
- The developer does not have to close the restored shells by hand.
- The [loss inventory](../appendix-a-glossary.md#loss-inventory) already ran in preflight, before the card.

On approval the plan runs in this order (see [Threads · projection divergence and repair](../03-threads.md#projection-divergence-and-repair)):

1. It [freezes](../appendix-a-glossary.md#freeze) each listed container, terminates its processes with [verified exit](../appendix-a-glossary.md#verified-exit), and closes it.
2. Once nothing holds the workspace, it checkpoints exactly as an ordinary close does.
3. It forgets the jj workspace and removes the materialized directory.
4. It transitions the thread to `Closed`.

Merged revisions live on `main`. The docs thread's revisions stay under its checkpoint bookmark. PRs remain untouched.

Had a thread still been in flight, the developer would have applied the restart plan instead. Under its own approval, that plan does the following:

- It closes the listed remnant containers the same way. Kiki never reuses one.
- It provisions a fresh terminal group with role panes.
- It starts a new incarnation with a fresh credential, [launch gate](../appendix-a-glossary.md#launch-gate), and ready handshake.
- Only that handshake makes the thread `Active` again.

A final `kk ls --all-repos --all` shows the week as a flat list across the three repos. The `--all` flag includes closed threads, and the `--all-repos` flag widens repo scope. They are independent (see [Commands · `kk ls`](../09-commands.md#kk-ls)).

- `kestrel-mobile/android-skel` — closed
- `kestrel-mobile/auth` — closed (the password-first version, abandoned mid-week)
- `kestrel-mobile/auth-biometric` — closed (the biometric-first replacement, merged)
- `kestrel-docs/android-docs` — closed (not yet published; its revisions are kept under its bookmark)
- `kestrel-www/copyright-2026` — closed

Bare `kk` from `kestrel-mobile` opens the overlay with no active work remaining. The closed threads are reachable through `kk ls --all` and `kk reopen <thread>` if anything from the week needs revisiting.

Five threads were spawned, one was abandoned, three merged, and one was archived with its work kept for later. The follows DAG is empty; no sync intents are unresolved; the daemon is idle.

## Epilogue

The patterns this storyboard demonstrates and the chapters that authorize them:

- **Branching** — acts 3 and 7. `kk new --follows <parent>` records a live cascade edge plus exact synchronization anchors (see [Threads · creation](../03-threads.md#creation), [Cascade · classification](../05-cascade.md#classification)).
- **Merging back** — acts 5 and 9 (see [Publishing](../07-publishing.md), [Cascade · parent merged](../05-cascade.md#parent-merged)).
  - Act 5 is a single thread merging direct to `main`.
  - Act 9 is a stacked publish. There the parent merge reconciles the child onto the exact merged `main` commit at its safe boundary.
- **Abandoning** — act 7's `kk close` of the wrong-direction `auth` thread (see [Threads · close](../03-threads.md#close), [Threads · destroy](../03-threads.md#destroy)).
  - Close retains the thread's transcript and kiki record for possible reuse.
  - That is in contrast to approved `kk thread destroy`. Destroy removes that record but preserves jj revisions unless a separately approved abandonment plan is requested.
- **Cross-repo** — acts 1 (registration), 5 (`kestrel-www` copyright bump), 6 (`kestrel-docs` parallel work). One daemon, per-repo registration, `kk ls --all-repos` for the global view (see [Commands · `kk ls`](../09-commands.md#kk-ls)).
- **Cascade in motion** — acts 4 and 8 (see [Cascade](../05-cascade.md), [Invariants](../02-invariants.md)).
  - Act 4 shows jj-native ancestor evolution followed by safe materialization.
  - Act 8 shows an explicit parent advance with conflict and human resolution.
  - Both demonstrate that direct `jj` operations are first-class inputs to the coordinator, not gated by it.
- **Terminal runtime as projection** — acts 2, 6, and 10 (see [Commands · `kk attach`](../09-commands.md#kk-attach), [Terminal runtime](../13-architecture/terminal-runtime.md), [Invariants](../02-invariants.md#the-terminal-runtime-is-a-projection-not-an-authority)).
  - Acts 2 and 6: `kk attach` opens a view; `kk switch` moves only the caller's client.
  - Act 10: a reboot restores remnant Herdr containers. No thread is `Active` until `kk repair` restarts it. No workspace is deleted until every process holding it is closed with verified exit.
- **Stacked publish** — act 9 (see [Commands · `kk publish`](../09-commands.md#kk-publish), [Cascade · parent merged](../05-cascade.md#parent-merged)).
  - `kk publish --downstack` publishes ancestors first.
  - A parent merge then reconciles descendants locally onto the repo default branch.
  - It leaves force-push/PR-base changes behind an exact foreground-approved remote plan.

If the storyboard appears to require any behavior the rest of the book does not authorize, that is a finding. The storyboard is illustrative; the specification is normative.
