# Storyboard

The earlier chapters describe what kiki does one verb at a time. This chapter describes what kiki feels like across one work-week, by following a single developer through a porting project that crosses three repos and tests every branching, merging, and abandoning pattern the rest of the book commits to.

The protagonist is unnamed. The work is to port the iOS Kestrel app to Android, while product is still iterating on the spec, and while two other repos — the user-facing docs and the marketing site — also need attention along the way. The three repos are:

- `kestrel-mobile` — the iOS/Android codebase, where the port lives.
- `kestrel-docs` — the user-facing product documentation.
- `kestrel-www` — the marketing site, where one copyright year is wrong.

The storyboard introduces no new commands, flags, glyphs, or screen elements. Every beat in it grounds out in the normative chapters. Where a beat is load-bearing, it cites the chapter that authorizes it. Where it would require behavior the rest of the book does not authorize, that gap is a finding, not a license to extend the surface here.

Transcripts and wireframes in this chapter render the fields the spec commits to in a plausible terminal shape. Exact spacing, column ordering, and any output text the spec does not pin are illustrative — they show what kiki _might_ look like in motion, not what an implementation must emit byte-for-byte. Glyphs and committed output strings (the `in sync` / `pending` / `conflicted` cascade-state words; the empty-state placeholder; the conflict-framing message) are reproduced verbatim from the spec.

Acts are time-stamped (`Day · HH:MM — <repo>`) so the temporal arc is legible: product changes its mind twice, work stacks up, a thread is abandoned in flight, a cascade conflicts and recovers, a laptop reboots overnight, and the week closes with a stack of merged PRs and a quiet TUI.

## Act 1 — Bootstrapping

### Mon 09:14 — kestrel-mobile, kestrel-docs, kestrel-www

`kestrel-mobile` is already kiki-registered — the developer brought it under management on a prior project, and there are no threads in flight from that work. The two new-to-kiki repos for this week are `kestrel-docs` and `kestrel-www`. The developer runs `kk init` in each. `kk init` is idempotent and never creates a starter thread (see [Commands · `kk init`](../09-commands.md#kk-init)).

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

The developer returns to `kestrel-mobile` and types bare `kk`. The repo is registered and the TUI ships, so the overlay opens in `NAVIGATE` mode — but with no threads to navigate, it shows the empty-state placeholder, with `n` and `?` as the only active verbs (see [Interface · spec](spec.md#overlay)).

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

> kkd: `kk init` adds a row to `~/.config/kiki/state.db` (the cross-repo registry) under a freshly minted `<repo_id>` UUID, then creates `~/.config/kiki/repos/<repo_id>/` for per-repo runtime state — `state.db` (including the daemon-enforced append-only audit table), gitignored config, per-thread credentials, and per-thread error logs live under that directory. Nothing is written inside the source repo's filesystem.

## Act 2 — The skeleton thread

### Mon 10:42 — kestrel-mobile

The first thread will scaffold Android navigation: the gradle module, a top-level `NavHost`, and a Material 3 theme that mirrors the iOS app's tab structure. Herdr's sidebar already gives a list of threads, and with one thread there is no tree worth pinning, so the developer leaves the optional UI pane off for now (see [Interface · spec](spec.md#ui-pane)).

```console
$ kk new android-skel -m "Scaffold Android navigation: gradle module,
  NavHost, Material 3 theme. Match the iOS app's tab structure but use a
  NavigationBar rather than UITabBarController."
```

`kk new` runs a durable creation saga for the thread row, jj workspace at `~/code/kestrel-mobile-kiki-android-skel/`, initial change and persisted live head, checkpoint bookmark, per-thread credential, isolated harness settings, and terminal group (see [Threads · creation](../03-threads.md#creation)). The terminal group is one Herdr workspace on the dedicated server, with an agent pane and a shell pane in its first tab. Each pane's direct child is the kiki pane launcher. The harness launches last, after its safe boundary exists. The terminal group exists on the server whether or not anyone is looking at it. The developer ran `kk new` in an ordinary terminal that is not a Herdr client, so there is no caller client to move: `kk new` succeeds, moves nobody's view, and prints how to reach the thread. Moving no attached client's view while provisioning is kiki's contract; that Herdr's create and layout calls honor it with clients attached is still an unproven acceptance gate (see [Commands · `kk new`](../09-commands.md#kk-new)). The developer opens a view:

```console
$ kk attach android-skel
```

`kk attach` asks `kkd` to ensure the dedicated server is running and addresses it by kiki's configuration root plus the session name, so this client can only land on kiki's server, never on a Herdr server the developer uses for other work (see [Commands · `kk attach`](../09-commands.md#kk-attach)). This is the developer's terminal for the rest of the week. Herdr's sidebar is on the left with one row; the agent pane is on top and the shell pane below it.

```text
 ╭─ kiki ─────────────────────────────────────────────────────╮ ╭─ agent · android-skel ─────────────────╮
 │                                                            │ │                                        │
 │ ▸ kestrel-mobile android-skel a41c  ── in sync   ● working │ │ > human                                │
 │                                                            │ │   Scaffold Android navigation: gradle  │
 │                                                            │ │   module, NavHost, Material 3 theme.   │
 │                                                            │ │   Match the iOS app's tab structure    │
 │                                                            │ │   but use a NavigationBar rather than  │
 │                                                            │ │   UITabBarController.                  │
 │                                                            │ │                                        │
 │                                                            │ │ ● working  4s  esc to interrupt        │
 │                                                            │ │                                        │
 │                                                            │ │   reading AndroidManifest.xml ...      │
 │                                                            │ │                                        │
 │                                                            │ ╰────────────────────────────────────────╯
 │                                                            │ ╭─ shell ────────────────────────────────╮
 │                                                            │ │ android-skel $ _                       │
 │                                                            │ │                                        │
 │                                                            │ │                                        │
 │                                                            │ │                                        │
 ╰────────────────────────────────────────────────────────────╯ ╰────────────────────────────────────────╯
```

The sidebar is Herdr's. Kiki publishes the thread's label and tokens into it and never reads them back. No kiki verb is bound there, so nothing done in the sidebar can spawn, publish, close, or interrupt. Consequential verbs use daemon-issued foreground approval cards in the overlay (see [Interface · spec](spec.md#herdr-sidebar-projection)).

> kkd: each creation step and compensation is journaled. A crash leaves `Creating` or `CreateFailed` for restart recovery rather than relying on a cross-system transaction. Only after the workspace, live head, checkpoint bookmark, credential, isolated hook settings, and terminal group are ready does kiki open the agent launcher's gate; only that incarnation's settings-bound ready handshake activates the thread. Herdr's reply to the create call, the pane appearing, and Herdr's own agent detection are not evidence of any of it (see [Terminal runtime · provisioning](../13-architecture/terminal-runtime.md#provisioning)).

## Act 3 — Branching off for auth

### Mon 14:20 — kestrel-mobile

The skeleton thread is partway through wiring the `NavHost` and theme; the auth flow needs a parallel thread to start on. Auth depends on the navigation skeleton — the `login` destination, the back-stack rules — but it doesn't need to wait for the skeleton to finish. The developer spawns a child thread that follows the skeleton, so future native rewrites will materialize in `auth` at its boundary and future parent tips will explicitly advance it there (see [Cascade · classification](../05-cascade.md#classification)).

```console
$ kk new auth --follows android-skel -m "Implement password login against the
  existing iOS endpoints. The NavHost in android-skel has a `login` destination
  scaffolded; wire onSuccess to pop to the home tab."
```

`--follows` records a live edge from `auth` to `android-skel`. With a second thread the stack has a shape, so between threads the developer added `[ui] ui_pane = true` to user config: `auth`'s tab comes up with a narrow UI pane showing the Stack tree beside the agent (see [Configuration](../11-configuration.md)). `android-skel`'s live terminal group is not reshaped. Herdr's sidebar now has two rows, and `auth`'s row carries the follows token `←● android-skel`.

A bare `kk` in either thread now opens the overlay with both threads in the Stack tree. The follows arrow `←●` marks the auth thread as a child of `android-skel`; `▸` marks whichever thread the cursor is on.

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

Both threads are working concurrently. The Stack section orders them by `kk log` (parent above child); the Activity section orders the same threads flat by most-recent agent event. `tab` jumps the cursor between the two sections; `enter` switches the developer's own Herdr client to whichever thread the cursor is on (see [Interface · keymap](spec.md#keymap)).

The follows DAG is, for now, two hops deep: `main → android-skel → auth`. Each active thread follows its parent's persisted workspace head, not an assumption that jj automatically advances bookmarks. jj may evolve several descendant commits in one operation; kiki still materializes and explains each affected workspace independently.

## Act 4 — Product changes their mind (small)

### Tue 11:00 — kestrel-mobile

Overnight, the navigation skeleton settled into a clean shape, and product responded with a small correction: the bottom-bar tab order should put `Library` left of `Discover`, not right. The change is small enough that the developer makes it directly, without spawning a thread for it. They switch to `android-skel` and move focus to the shell pane below the agent — already cd'd into the jj workspace, already running their `$SHELL` — and amend the relevant revision by hand:

```console
$ cd ~/code/kestrel-mobile-kiki-android-skel
$ jj describe -r @- -m "Scaffold Android navigation: NavHost + Material 3 + bottom NavigationBar (Library, Discover, Profile)"
```

They run `jj` directly. kiki does not refuse direct `jj` or `gh` operations, or native Herdr use; it watches the op log and reacts to whatever it sees (see [Invariants](../02-invariants.md)). jj evolves `auth`'s descendant commit in shared repository state as part of the ancestor rewrite, but `auth`'s on-disk files remain at their previously materialized state.

> kkd: the op-log watcher compares the before/after operation views. Because `auth` already descends from the evolved `android-skel` base, it classifies `NativeRewrite` and stores that exact base transition in a `sync_intent`. It does not schedule another rebase for work jj already evolved (see [Cascade · classification](../05-cascade.md#classification)).

A few seconds later, the auth agent finishes the function it was writing and prepares its next tool batch. Kiki's exclusive `PreToolUse` hook first binds a durable `Block` barrier for the entire batch, then probes the workspace. Because it is provably stale and clean, the orchestrator materializes its evolved state and stores the result, payload, anchor, and `Materialized` state. Every call in that tool batch remains blocked; `PostToolBatch` closes the soft-delivery barrier, and only a later model turn may acknowledge the intent (see [Cascade · delivery protocol](../05-cascade.md#delivery-protocol)).

In the overlay's Stack row, and in the cascade token on `auth`'s row in Herdr's sidebar, the glyph briefly flips through `↻` (pending) and back to `──` (in sync) once the agent acknowledges. No toast fires for this cascade — the toast trigger for coalesced child materialization only fires when at least two child reconciliations coalesce (see [Interface · toasts](spec.md#toasts)), and `auth` is the only affected thread.

The agent's view of the change is a single synthetic turn explaining what evolved and which files were materialized; the developer's view is a momentary glyph flip on one row. Neither has to coordinate further. The act is intentionally undramatic — that is what an ambient coordinator looks like when it's working.

## Act 5 — Cross-repo interlude: the copyright bump

### Tue 16:45 — kestrel-www

In the middle of the auth work, the developer remembers that the marketing site's footer still says "© 2025". They do not interrupt either of the kestrel-mobile threads. They open a separate terminal window, change directory, and spawn a third thread in a different repo:

```console
$ cd ~/code/kestrel-www
$ kk new copyright-2026 -m "Bump copyright year in the footer to 2026.
  The string lives in components/Footer.tsx — replace the literal year
  only, do not touch any other footer copy."
```

The new thread has no follows link; `kestrel-www` has no other kiki threads, and no parent makes sense. That window is not a Herdr client, so again nobody's view moves. The new thread gets its own terminal group on the same server, and Herdr's sidebar in the developer's client now lists three rows from two repos in one list. The developer selects the new row there — Herdr's own navigation — and works from that thread's shell pane. The agent edits one line. A minute later, the developer reviews the diff in the overlay's preview pane (`d`), is satisfied, and publishes:

```console
$ kk publish --ready -m "Bump copyright year to 2026"
```

`--ready` opens the PR ready for review rather than as a draft (see [Publishing · defaults](../07-publishing.md#defaults)). The base branch resolves to `main` because the thread has no follows ancestor (see [Publishing · PR base](../07-publishing.md#defaults)). CI is green within a minute. Marketing's reviewer approves. The developer merges via `gh pr merge` directly — kiki does not gate that — and closes the thread:

```console
$ kk close
```

`kk close` shows its plan in an approval card and waits for the developer's `enter`. It then freezes every process in the terminal group — the agent, the shell, anything else running in its panes — repeats its loss check, and checkpoints the bookmark to the live head. Only then does it close the terminal group, verify by OS process identity that every frozen process has exited and nothing else holds the workspace, forget the jj workspace, delete the materialized directory, and mark the thread `Closed` (see [Threads · close](../03-threads.md#close)). Herdr's reply to the close request is not the proof; the verified exit is. If the final check failed, the same processes would resume instead of the thread becoming a dead `Active` row. The thread's row leaves Herdr's sidebar, and Herdr places the developer's client on one of the remaining terminal groups.

Total wall time on the copyright bump: about twelve minutes. Nothing in `kestrel-mobile` was perturbed. The two `kestrel-mobile` threads remain active; `kestrel-www` now has one closed thread.

## Act 6 — The docs thread, started in parallel

### Wed 09:14 — kestrel-docs

Wednesday morning, product asks for first-pass documentation of the Android setup story so that beta testers have something to read alongside the build they are about to receive. The docs live in their own repo. The developer spawns a thread there:

```console
$ cd ~/code/kestrel-docs
$ kk new android-docs -m "Document the Android app's first-run flow:
  install from Firebase App Distribution, log in (password for now,
  biometric coming soon), grant notification permission, land on the
  Library tab. Match the structure of the iOS first-run page."
```

`kestrel-docs` has no other kiki threads either, so `android-docs` is parentless and follows nothing. From any registered repo, `kk ls --all-repos` now lists every active thread across both repos. The exact column shape is up to the renderer; the spec commits to a `repo` column when the listing crosses repo scope and to active-thread coverage. The listing the developer sees contains `kestrel-mobile/android-skel`, `kestrel-mobile/auth` (with its follows arrow back to `android-skel`), and `kestrel-docs/android-docs` (see [Commands · `kk ls`](../09-commands.md#kk-ls)). `--all` (which would include closed threads, like `copyright-2026`) is independent of `--all-repos` and is not passed here.

The developer keeps moving between threads with `kk switch`, and sometimes by selecting a row in Herdr's sidebar. `kk switch` moves the client that ran it and no other, and it does not mutate daemon focus state (see [Commands · `kk switch`](../09-commands.md#kk-switch)). Later that morning the developer runs `kk attach android-docs` in a second terminal window on another monitor, to keep the docs agent in view. Both clients are now attached to the same server. A `kk switch auth` typed in the first window moves the first window only; the docs view stays where it is. That depends on the Herdr capability `client_targeted_focus`. On a server without it, `kk switch` would refuse and name the capability rather than move both windows. The daemon is not "in" any thread; it is watching all of them.

## Act 7 — Product changes their mind (big)

### Wed 15:30 — kestrel-mobile

Mid-afternoon, product Slacks: scrap the password-first auth flow. Sales has been hearing repeated requests for biometric-first login from enterprise pilots, and the team wants to ship the Android beta with that posture from day one. Password is now a fallback, not the front door.

The auth thread's direction is wrong. Not in detail — fully. Closing it and starting a new one is cleaner than re-prompting the agent and watching it patch its way to a different posture. The developer opens the overlay, cursors to `auth` in the Stack, and presses `x`. The overlay requests a daemon-canonical close challenge and displays its approval card (see [Interface · forms](spec.md#forms)):

```text
 kiki · NAVIGATE · kestrel-mobile/auth                                         ?  esc

 STACK                              │  kestrel-mobile/auth
                                    │
 ● main             ──    in        │   ╭─ Close kestrel-mobile/auth? ───────────────╮
 │                                  │   │                                            │
 ●─android-skel     ──    wrk       │   │  Stops the agent and every process in      │
 │                                  │   │  the terminal group: agent, shell, ui      │
 ●─auth          ▸  ──    ←●        │   │  (3 processes).                            │
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

The developer presses `enter`. `kk close` freezes and rechecks every process in the terminal group, checkpoints the bookmark without snapshotting or changing the frozen workspace, then closes the terminal group, verifies that the frozen processes have exited, forgets the workspace, and marks the thread `Closed`. The developer specifically did not run `kk thread destroy`: that irreversible deletion of kiki's thread record requires a one-use human approval and still preserves jj revisions unless a separate `--abandon-revisions` plan is approved (see [Threads · destroy](../03-threads.md#destroy)).

Then the developer spawns the replacement:

```console
$ kk new auth-biometric --follows android-skel -m "Biometric-first login,
  with password as a fallback for devices without enrolled biometrics.
  Use AndroidX Biometric. The login NavHost destination is in
  android-skel; pop to the home tab on success, fall through to the
  password form on biometric failure."
```

The Stack tree's shape is unchanged — there is still one thread following `android-skel` — but the slot now holds `auth-biometric`. The `auth` thread is gone from the active list; `kk ls --all` would still show it, marked closed (see [Commands · `kk ls`](../09-commands.md#kk-ls)).

## Act 8 — A cascade conflict

### Thu 10:08 — kestrel-mobile

Thursday morning, the `android-skel` thread's agent adds a new navigation-refactor revision: it moves the auth-related destinations out of the root `NavHost` into a nested `loginGraph`. The new parent tip is not yet in `auth-biometric`'s ancestry, so the watcher classifies `ParentAdvance`. At `auth-biometric`'s next safe boundary, the explicit advance onto that exact parent commit exposes textual conflicts in the same files the child changed.

`auth-biometric` transitions to the cascade `conflicted` projection. The orchestrator interrupts the agent and resumes it with conflict framing (see [Cascade · conflicts and escalation](../05-cascade.md#conflicts-and-escalation)):

> Cascade reconciliation produced conflicts in auth-biometric. Resolve before continuing.

A loud notification fires, and the cascade token on `auth-biometric`'s row in Herdr's sidebar changes to `◐ conflicted` in both of the developer's attached clients. The developer happens to have the overlay focused on `android-skel`; from that vantage, `auth-biometric` is a non-current thread, so the conflict surfaces as a toast — toasts for cascade conflicts only fire on non-current threads (see [Interface · toasts](spec.md#toasts)). The conflicted thread's row also turns red:

```text
 kiki · NAVIGATE · kestrel-mobile/android-skel      ┌────────────────────────────────┐
                                                    │ ◐ auth-biometric conflicted    │
 STACK                              │               │   tap T to request transcript  │
                                                    └────────────────────────────────┘
 ● main             ──    in        │
 │                                  │
 ●─android-skel  ▸  ──    wrk       │
 │                                  │
 ●─auth-biometric   ◐    ←●         │
                                    │
```

Because the overlay credential is contextual to `android-skel`, activating `T` here would first display an exact sibling-read plan and require a one-use foreground approval. The developer does not request it; switching into `auth-biometric` makes subsequent same-thread inspection contextual instead.

The developer cursors to `auth-biometric` and presses `enter`, which moves that client to the thread's agent pane. They move focus to the shell pane below the agent (which is paused) and resolve the conflict by hand. jj's conflict markup makes the merge tractable; the resolution touches three lines.

```console
$ cd ~/code/kestrel-mobile-kiki-auth-biometric
$ jj resolve
```

> kkd: the op-log watcher sees the resolve op like any other external op. Once the working-copy commit is no longer conflicted, the thread leaves cascade `conflicted` and reconciliation resumes (see [Cascade · conflicts and escalation](../05-cascade.md#conflicts-and-escalation)). The agent is resumed with a synthetic context message describing the parent advance and what the human resolved, and continues.

The cascade glyph on `auth-biometric` returns to `──`. The conflict cost the developer about eight minutes of focused attention and zero corrupted state.

## Act 9 — Publishing the stack

### Thu 16:00 — kestrel-mobile

By late Thursday, the navigation skeleton is complete and the biometric-first auth flow works end-to-end against staging. The developer wants both threads in front of reviewers as a stack: skeleton at the bottom, auth-biometric on top. From the skeleton thread, they invoke a downstack publish:

```console
$ kk publish --downstack --ready
```

`--downstack` publishes the current thread plus unpublished descendants, top-down (see [Commands · `kk publish`](../09-commands.md#kk-publish)). `--ready` opens both PRs ready for review rather than as drafts (see [Publishing · defaults](../07-publishing.md#defaults)). kiki publishes ancestors first, then descendants: skeleton's PR is created with base `main`; auth-biometric's PR is then created with base `android-skel`. Each PR opens a separate editor session with a non-transcript static template so the developer writes its title and body. AI drafting belongs to the later metadata tranche and is not part of this publishing flow (see [Publishing · PR text](../07-publishing.md#pr-text)).

Once both editors close and `gh` returns success, `kk log --wide` shows the stack annotated with PR state, CI roll-up, agent state, and last-activity age (see [Commands · `kk log`](../09-commands.md#kk-log)):

```console
$ kk log --wide
●─auth-biometric  [#143] ●  "Biometric-first auth flow"  ready  ●●●●● ci green  working    34s
●─android-skel    [#142] ●  "Scaffold Android navigation"  ready  ●●●●● ci green  working   12m
●─main
```

Reviewers approve through the day; the skeleton PR merges first. kiki polls GitHub through `gh` and notices the merge. For `auth-biometric`, kiki records a `ParentAdvance`-shaped transition to the exact merged default-branch commit (see [Cascade · parent merged](../05-cascade.md#parent-merged)). At the child's safe boundary it rebases and materializes the child locally, then stops with a named remote-update plan covering the exact `--force-with-lease` push and PR-base change. The developer reviews that plan in the foreground and confirms a one-use approval. Only after the claimed journal completes both remote effects does kiki drop the follows link; without approval, the child remains locally reconciled with `remote update pending` visible.

> kkd: the parent-merge work remains represented by the exact-base `sync_intent`, the follows edge, the PR link, and the claimed remote-operation journal; the storyboard does not invent a second cascade lifecycle. The follows link is dropped only after local and approved remote updates succeed.

The `auth-biometric` row in the Stack updates after the parent-merge transition: the follows arrow `←●` disappears, since auth-biometric no longer follows anything. Shortly after, reviewers approve `auth-biometric` and that PR merges too. The week's port has landed on `main` as two clean commits.

## Act 10 — Closing out

### Fri 09:00 — across repos

The laptop installed an update and rebooted overnight. No process survives a reboot: the Herdr server, every agent, and every shell are gone. `kkd` comes back through its user service. The developer opens a terminal and runs `kk attach`, which asks `kkd` to ensure the dedicated server is running; `kkd` starts it again. Herdr restores the layout it saved — three Herdr workspaces with their labels and working directories — and starts a plain shell in each pane. Each label still reads repo, thread, provisioning tag.

```text
 ╭─ kiki ───────────────────────────────────────────╮
 │                                                  │
 │   kestrel-mobile android-skel a41c               │
 │   kestrel-mobile auth-biometric e90b             │
 │   kestrel-docs android-docs 5c12                 │
 │                                                  │
 ╰──────────────────────────────────────────────────╯
```

The rows look like Thursday's, minus kiki's tokens. They are not threads coming back. Kiki disabled Herdr's agent auto-resume in the configuration it generated, so no harness was restarted, and a restored pane has no launcher, no credential, no launch settings, and no ready handshake. `kk ls --all-repos` says what is true: `android-skel`, `auth-biometric`, and `android-docs` are each listed as `ProjectionDiverged` with the reason `TerminalMissing`. None is `Active`.

> kkd: the server it now talks to has a different `server_instance_id`. Every binding from the old instance is ended and every incarnation retired without acknowledgement. The orphan scan finds none of the recorded process identities alive — a reboot leaves nothing — and no stray holder of any workspace. It does find the restored shells, whose working directories are inside the jj workspaces. Those are remnant panes: the current snapshot names each one's pane and root process, so they are accounted terminal members, not orphans. No `OrphanedProcess` issue is raised. Each thread gets `TerminalMissing` (see [Terminal runtime · runtime changes are reconciliation](../13-architecture/terminal-runtime.md#runtime-changes-are-reconciliation)).

All three threads' work has merged, so the developer does not restart agents just to stop them. `kk repair` diagnoses a thread and names its plans: restart the terminal and agent, or `close-without-terminal` (see [Commands · `kk repair`](../09-commands.md#kk-repair)). The developer takes the second.

```console
$ kk repair auth-biometric                  # read-only: prints the diagnosis and plan ids
$ kk repair auth-biometric --apply <repair-id>
$ kk repair android-skel --apply <repair-id>
$ cd ~/code/kestrel-docs && kk repair android-docs --apply <repair-id>
```

Each apply shows its approval card first. The card lists the remnant containers whose shells hold that thread's jj workspace. Kiki matched them to the thread by that OS evidence, not by the labels in the sidebar. The developer does not have to close the restored shells by hand: the approved plan closes each listed container and verifies that its processes exited. The loss inventory already ran in preflight, before the card. After the containers are closed and nothing holds the workspace, it checkpoints exactly as an ordinary close does, forgets the jj workspace, removes the materialized directory, and transitions the thread to `Closed` (see [Threads · projection divergence and repair](../03-threads.md#projection-divergence-and-repair)). Tracked revisions live on `main`; PRs remain untouched.

Had a thread still been in flight, the developer would have applied the restart plan instead. Under its own approval, it reuses or closes the remnant container, provisions fresh role panes, and starts a new incarnation with a fresh credential, launch gate, and ready handshake, and only that handshake makes the thread `Active` again.

A final `kk ls --all-repos --all` (the `--all` flag includes closed threads, the `--all-repos` flag widens repo scope — they are independent, see [Commands · `kk ls`](../09-commands.md#kk-ls)) shows the week as a flat list across the three repos:

- `kestrel-mobile/android-skel` — closed
- `kestrel-mobile/auth` — closed (the password-first version, abandoned mid-week)
- `kestrel-mobile/auth-biometric` — closed (the biometric-first replacement, merged)
- `kestrel-docs/android-docs` — closed
- `kestrel-www/copyright-2026` — closed

Bare `kk` from `kestrel-mobile` opens the overlay with no active work remaining; the closed threads are reachable through `kk ls --all` and `kk reopen <thread>` if anything from the week needs revisiting. Five threads were spawned, one was abandoned, four merged. The follows DAG is empty; no sync intents are unresolved; the daemon is idle.

## Epilogue

The patterns this storyboard demonstrates and the chapters that authorize them:

- **Branching** — acts 3 and 7. `kk new --follows <parent>` records a live cascade edge plus exact synchronization anchors (see [Threads · creation](../03-threads.md#creation), [Cascade · classification](../05-cascade.md#classification)).
- **Merging back** — acts 5 (a single thread merging direct to `main`) and 9 (a stacked publish where the parent merge reconciles the child onto the exact merged `main` commit at its safe boundary) (see [Publishing](../07-publishing.md), [Cascade · parent merged](../05-cascade.md#parent-merged)).
- **Abandoning** — act 7's `kk close` of the wrong-direction `auth` thread, retaining its transcript and kiki record for possible reuse, in contrast to approved `kk thread destroy`, which removes that record but preserves jj revisions unless a separately approved abandonment plan is requested (see [Threads · close](../03-threads.md#close), [Threads · destroy](../03-threads.md#destroy)).
- **Cross-repo** — acts 1 (registration), 5 (`kestrel-www` copyright bump), 6 (`kestrel-docs` parallel work). One daemon, per-repo registration, `kk ls --all-repos` for the global view (see [Commands · `kk ls`](../09-commands.md#kk-ls)).
- **Cascade in motion** — act 4 (jj-native ancestor evolution followed by safe materialization), act 8 (explicit parent advance with conflict and human resolution). Both demonstrate that direct `jj` operations are first-class inputs to the coordinator, not gated by it (see [Cascade](../05-cascade.md), [Invariants](../02-invariants.md)).
- **Terminal runtime as projection** — acts 2 and 6 (`kk attach` opens a view; `kk switch` moves only the caller's client) and act 10 (a reboot restores remnant Herdr containers; no thread is `Active` until `kk repair` restarts it, and no workspace is deleted until every process holding it is closed with verified exit) (see [Commands · `kk attach`](../09-commands.md#kk-attach), [Terminal runtime](../13-architecture/terminal-runtime.md), [Invariants](../02-invariants.md#the-terminal-runtime-is-a-projection-not-an-authority)).
- **Stacked publish** — act 9. `kk publish --downstack` publishes ancestors first; a parent merge then reconciles descendants locally onto the repo default branch and leaves force-push/PR-base changes behind an exact foreground-approved remote plan (see [Commands · `kk publish`](../09-commands.md#kk-publish), [Cascade · parent merged](../05-cascade.md#parent-merged)).

If the storyboard appears to require any behavior the rest of the book does not authorize, that is a finding. The storyboard is illustrative; the specification is normative.
