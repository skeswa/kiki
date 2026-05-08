# Storyboard

The earlier chapters describe what kiki does one verb at a time. This chapter describes what kiki feels like across one work-week, by following a single developer through a porting project that crosses three repos and tests every branching, merging, and abandoning pattern the rest of the book commits to.

The protagonist is unnamed. The work is to port the iOS Kestrel app to Android, while product is still iterating on the spec, and while two other repos — the user-facing docs and the marketing site — also need attention along the way. The three repos are:

- `kestrel-mobile` — the iOS/Android codebase, where the port lives.
- `kestrel-docs` — the user-facing product documentation.
- `kestrel-www` — the marketing site, where one copyright year is wrong.

The storyboard introduces no new commands, flags, glyphs, or screen elements. Every beat in it grounds out in the normative chapters. Where a beat is load-bearing, it cites the chapter that authorizes it. Where it would require behavior the rest of the book does not authorize, that gap is a finding, not a license to extend the surface here.

Transcripts and wireframes in this chapter render the fields the spec commits to in a plausible terminal shape. Exact spacing, column ordering, and any output text the spec does not pin are illustrative — they show what kiki *might* look like in motion, not what an implementation must emit byte-for-byte. Glyphs and committed output strings (the `in sync` / `pending` / `conflicted` cascade-state words; the empty-state placeholder; the conflict-framing message) are reproduced verbatim from the spec.

Acts are time-stamped (`Day · HH:MM — <repo>`) so the temporal arc is legible: product changes its mind twice, work stacks up, a thread is abandoned in flight, a cascade conflicts and recovers, and the week closes with a stack of merged PRs and a quiet TUI.

## Act 1 — Bootstrapping

### Mon 09:14 — kestrel-mobile, kestrel-docs, kestrel-www

`kestrel-mobile` is already kiki-registered — the developer brought it under management on a prior project, and there are no threads in flight from that work. The two new-to-kiki repos for this week are `kestrel-docs` and `kestrel-www`. The developer runs `kk init` in each. `kk init` is idempotent and never creates a starter thread (see [Commands · `kk init`](../11-commands.md#kk-init)).

```console
$ cd ~/code/kestrel-docs && kk init
registered  ~/code/kestrel-docs  (mon 2026-05-04 09:15:10)
threads     0 active, 0 closed
state       ~/.kiki/repos/9b0c1d4f/state.db

$ cd ~/code/kestrel-www && kk init
registered  ~/code/kestrel-www  (mon 2026-05-04 09:15:32)
threads     0 active, 0 closed
state       ~/.kiki/repos/2e7a8c5b/state.db
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

> kkd: `kk init` adds a row to `~/.kiki/state.db` (the cross-repo registry) under a freshly minted `<repo_id>` UUID, then creates `~/.kiki/repos/<repo_id>/` for per-repo runtime state — `state.db`, gitignored config, audit log, per-thread credentials, and per-thread error logs all live under that directory. Nothing is written inside the source repo's filesystem. The daemon is a single user-scoped process; it now knows about three repos, even though only one of them has the developer's attention.

## Act 2 — The skeleton thread

### Mon 10:42 — kestrel-mobile

The first thread will scaffold Android navigation: the gradle module, a top-level `NavHost`, and a Material 3 theme that mirrors the iOS app's tab structure. The developer wants the persistent sidebar pane on for this work, so they pass `--sidebar` and decide to write `[ui] persistent_sidebar = true` into their user config later (see [Configuration](../13-configuration.md)).

```console
$ kk new --sidebar android-skel -m "Scaffold Android navigation: gradle module,
  NavHost, Material 3 theme. Match the iOS app's tab structure but use a
  NavigationBar rather than UITabBarController."
```

`kk new` atomically creates the thread row, the jj workspace at `~/code/kestrel-mobile-kiki-android-skel/`, the bookmark, the initial change, the tmux session, the harness process, and the per-thread hook credential (see [Threads · creation](../05-threads.md#creation)). The tmux client opens the new thread's session, with the sidebar pane on the left and the agent pane on the right. The agent has received the first turn and started reading. The cascade glyph is `──` because no descendant follows the thread yet.

```text
 ╭─ kiki ──────────────────────╮ ╭─ android-skel ───────────────────────────────────╮
 │                             │ │                                                  │
 │ STACK                       │ │ > human                                          │
 │                             │ │   Scaffold Android navigation: gradle module,   │
 │ ● main          ──    in    │ │   NavHost, Material 3 theme. Match the iOS app's │
 │ │                           │ │   tab structure but use a NavigationBar rather   │
 │ ●─android-skel ▸ ──   wrk   │ │   than UITabBarController.                       │
 │                             │ │                                                  │
 │ ACTIVITY                    │ │ ● working   4s   esc to interrupt                │
 │                             │ │                                                  │
 │ ● android-skel  wrk    4s   │ │   reading app/src/main/AndroidManifest.xml ...   │
 │                             │ │                                                  │
 │ ─────────────────────────── │ │                                                  │
 │ ↑↓ ⇄ ⏎ switch · q · ?       │ │                                                  │
 │ android-skel  ── in sync  ● │ │                                                  │
 ╰─────────────────────────────╯ ╰──────────────────────────────────────────────────╯
```

The sidebar pane is navigation-only: spawn, publish, close, destroy, and interrupt are unbound there, so an accidental focus on the sidebar cannot mutate state. The destructive verbs live behind the overlay's confirmation cards (see [Interface · spec](spec.md#persistent-sidebar-pane)).

> kkd: thread creation is atomic. The sqlite row, jj workspace, bookmark, initial change, tmux session, harness process, hook credential, and per-thread harness config all came up together; if any of those steps had failed, the daemon would have unwound the rest before returning (see [Threads · creation](../05-threads.md#creation)).

## Act 3 — Branching off for auth

### Mon 14:20 — kestrel-mobile

The skeleton thread is partway through wiring the `NavHost` and theme; the auth flow needs a parallel thread to start on. Auth depends on the navigation skeleton — the `login` destination, the back-stack rules — but it doesn't need to wait for the skeleton to finish. The developer spawns a child thread that follows the skeleton, so any future change to the skeleton's revisions will rebase the auth thread at its next agent boundary (see [Cascade · trigger](../07-cascade.md#trigger)).

```console
$ kk new auth --follows android-skel -m "Implement password login against the
  existing iOS endpoints. The NavHost in android-skel has a `login` destination
  scaffolded; wire onSuccess to pop to the home tab."
```

`--follows` records a live edge from `auth` to `android-skel`; `--sidebar` is now defaulted on, courtesy of an entry the developer added to user config between threads.

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

Both threads are working concurrently. The Stack section orders them by `kk log` (parent above child); the Activity section orders the same threads flat by most-recent agent event. `tab` jumps the cursor between the two sections; `enter` switches the tmux client to whichever thread the cursor is on (see [Interface · keymap](spec.md#keymap)).

The follows DAG is, for now, two hops deep: `main → android-skel → auth`. Cascades will travel one hop at a time when ancestors evolve — that is the next act.

## Act 4 — Product changes their mind (small)

### Tue 11:00 — kestrel-mobile

Overnight, the navigation skeleton settled into a clean shape, and product responded with a small correction: the bottom-bar tab order should put `Library` left of `Discover`, not right. The change is small enough that the developer makes it directly, without spawning a thread for it. They drop into the `android-skel` workspace's tmux session, open a shell pane next to the agent pane, and amend the relevant revision by hand:

```console
$ cd ~/code/kestrel-mobile-kiki-android-skel
$ jj describe -r @- -m "Scaffold Android navigation: NavHost + Material 3 + bottom NavigationBar (Library, Discover, Profile)"
```

They run `jj` directly. kiki does not refuse direct `jj`/`gh`/`tmux` operations; it watches the op log and reacts to whatever it sees (see [Invariants](../04-invariants.md)). What kkd sees is an external op — no `kk:` prefix, `op_id` not in `op_attribution` — and an ancestry change that affects the auth thread, which directly follows `android-skel`.

> kkd: the op-log watcher dedupes against `op_attribution`, decides the op is external, walks the follows DAG to find direct descendants of the changed revision, and bumps `pending_cascade_seq` on `auth`. No rebase happens yet. The cascade waits for the auth agent's next PreToolUse boundary, so the agent never operates on stale disk state mid-edit (see [Cascade · invariant](../07-cascade.md#invariant)).

A few seconds later, the auth agent finishes the function it was writing and prepares its next tool call. `kk-hook` intercepts the PreToolUse, calls `PreToolUseDecision`, and the cascade orchestrator applies the rebase, advances `applied_cascade_seq`, composes a synthetic `ContextMessage`, persists it to `cascade_outbox`, and emits it to the agent. The agent receives it as its next turn and acknowledges on its following tool call (see [Cascade · delivery protocol](../07-cascade.md#delivery-protocol)).

In the auth thread's overlay, the Stack row's cascade glyph briefly flips through `●●○` (pending) and back to `──` (in sync) once the agent acknowledges. No toast fires for this cascade — the toast trigger for "cascade applied to a child thread" only fires when ≥ 2 children rebased in coalescence (see [Interface · toasts](spec.md#toasts)), and `auth` is the only descendant.

The agent's view of the change is a single synthetic turn explaining what was rebased; the developer's view is a momentary glyph flip on the Stack row. Neither has to coordinate further. The act is intentionally undramatic — that is what an ambient coordinator looks like when it's working.

## Act 5 — Cross-repo interlude: the copyright bump

### Tue 16:45 — kestrel-www

In the middle of the auth work, the developer remembers that the marketing site's footer still says "© 2025". They do not interrupt either of the kestrel-mobile threads. They open a shell, change directory, and spawn a third thread in a different repo:

```console
$ cd ~/code/kestrel-www
$ kk new copyright-2026 -m "Bump copyright year in the footer to 2026.
  The string lives in components/Footer.tsx — replace the literal year
  only, do not touch any other footer copy."
```

The new thread has no follows link; `kestrel-www` has no other kiki threads, and no parent makes sense. The agent edits one line. A minute later, the developer reviews the diff in the overlay's preview pane (`d`), is satisfied, and publishes:

```console
$ kk publish --ready -m "Bump copyright year to 2026"
```

`--ready` opens the PR ready for review rather than as a draft (see [Publishing · defaults](../09-publishing.md#defaults)). The base branch resolves to `main` because the thread has no follows ancestor (see [Publishing · PR base](../09-publishing.md#defaults)). CI is green within a minute. Marketing's reviewer approves. The developer merges via `gh pr merge` directly — kiki does not gate that — and closes the thread:

```console
$ kk close
```

`kk close` stops the agent and tmux session, forgets the jj workspace, deletes the materialized workspace directory, and marks the thread `Closed` (see [Threads · close](../05-threads.md#close)). Tracked jj revisions survive on the merged commit; the bookmark is left in place. The PR is left untouched, which is the correct default — `--discard-pr` is the explicit close-the-PR path, and there is nothing to discard here because the PR has already merged.

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

`kestrel-docs` has no other kiki threads either, so `android-docs` is parentless and follows nothing. From any registered repo, `kk ls --all-repos` now lists every active thread across both repos. The exact column shape is up to the renderer; the spec commits to a `repo` column when the listing crosses repo scope and to active-thread coverage. The listing the developer sees contains `kestrel-mobile/android-skel`, `kestrel-mobile/auth` (with its follows arrow back to `android-skel`), and `kestrel-docs/android-docs` (see [Commands · `kk ls`](../11-commands.md#kk-ls)). `--all` (which would include closed threads, like `copyright-2026`) is independent of `--all-repos` and is not passed here.

The developer keeps moving between threads with `kk switch`, which is a pure tmux client operation that does not mutate daemon focus state (see [Commands · `kk switch`](../11-commands.md#kk-switch)). The daemon is not "in" any thread; it is watching all of them.

## Act 7 — Product changes their mind (big)

### Wed 15:30 — kestrel-mobile

Mid-afternoon, product Slacks: scrap the password-first auth flow. Sales has been hearing repeated requests for biometric-first login from enterprise pilots, and the team wants to ship the Android beta with that posture from day one. Password is now a fallback, not the front door.

The auth thread's direction is wrong. Not in detail — fully. Closing it and starting a new one is cleaner than re-prompting the agent and watching it patch its way to a different posture. The developer opens the overlay, cursors to `auth` in the Stack, and presses `x`. The confirmation card appears (see [Interface · forms](spec.md#forms)):

```text
 kiki · NAVIGATE · kestrel-mobile/auth                                         ?  esc

 STACK                              │  kestrel-mobile/auth
                                    │
 ● main             ──    in        │   ╭─ Close kestrel-mobile/auth? ───────────────╮
 │                                  │   │                                            │
 ●─android-skel     ──    wrk       │   │  Stops the agent and tmux session.         │
 │                                  │   │  Forgets the jj workspace and removes      │
 ●─auth          ▸  ──    ←●        │   │  ~/code/kestrel-mobile-kiki-auth.          │
                                    │   │  Tracked jj revisions are kept.            │
                                    │   │  No PR is open.                            │
                                    │   │                                            │
                                    │   │   ⏎  Close      esc  Cancel                │
                                    │   ╰────────────────────────────────────────────╯
                                    │
 ACTIVITY                           │
 ─────────────────────────────────────────────────────────────────────────────────────
 kestrel-mobile  auth  ── in sync  claude-opus-4-7  ctx ●●●○○ 41%  last op 12s
```

The developer presses `enter`. `kk close` stops the agent, kills the tmux session, forgets the workspace, and marks the thread `Closed` — but it retains the transcript. The developer specifically did not run `kk thread destroy`: that is the irreversible path, which abandons the bookmark, revokes credentials, and deletes the transcript by default (see [Threads · destroy](../05-threads.md#destroy)). `Closed` is recoverable (`kk reopen <thread>`) and the transcript is searchable later if anything from the password-first attempt turns out to be worth keeping.

Then the developer spawns the replacement:

```console
$ kk new auth-biometric --follows android-skel -m "Biometric-first login,
  with password as a fallback for devices without enrolled biometrics.
  Use AndroidX Biometric. The login NavHost destination is in
  android-skel; pop to the home tab on success, fall through to the
  password form on biometric failure."
```

The Stack tree's shape is unchanged — there is still one thread following `android-skel` — but the slot now holds `auth-biometric`. The `auth` thread is gone from the active list; `kk ls --all` would still show it, marked closed (see [Commands · `kk ls`](../11-commands.md#kk-ls)).

## Act 8 — A cascade conflict

### Thu 10:08 — kestrel-mobile

Thursday morning, the `android-skel` thread's agent commits a navigation refactor: it moves the auth-related destinations out of the root `NavHost` into a nested `loginGraph`. This changes the same files the `auth-biometric` thread is mid-edit on. The cascade fires; the protected rebase on `auth-biometric` produces a textual conflict.

`auth-biometric` transitions to `Conflicted`. The cascade orchestrator interrupts the agent and resumes it with conflict framing (see [Cascade · scenario 3](../07-cascade.md#scenario-3-textual-conflict)):

> Cascade rebase produced a conflict on auth-biometric. Resolve before continuing.

A loud notification fires. The developer happens to have the overlay focused on `android-skel`; from that vantage, `auth-biometric` is a non-current thread, so the conflict surfaces as a toast — toasts for cascade conflicts only fire on non-current threads (see [Interface · toasts](spec.md#toasts)). The conflicted thread's row also turns red:

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

The developer cursors to `auth-biometric` and presses `enter` to switch to its tmux session, opens a shell pane next to the agent (which is paused), and resolves the conflict by hand. jj's conflict markup makes the merge tractable; the resolution touches three lines.

```console
$ cd ~/code/kestrel-mobile-kiki-auth-biometric
$ jj resolve
```

> kkd: the op-log watcher sees the resolve op like any other external op. Once the rebase no longer conflicts, the thread leaves the `Conflicted` state and cascade work resumes (see [Cascade · conflicts and escalation](../07-cascade.md#conflicts-and-escalation)). The agent is resumed with a synthetic context message describing what was rebased and what the human resolved, and continues.

The cascade glyph on `auth-biometric` returns to `──`. The conflict cost the developer about eight minutes of focused attention and zero corrupted state.

## Act 9 — Publishing the stack

### Thu 16:00 — kestrel-mobile

By late Thursday, the navigation skeleton is complete and the biometric-first auth flow works end-to-end against staging. The developer wants both threads in front of reviewers as a stack: skeleton at the bottom, auth-biometric on top. From the skeleton thread, they invoke a downstack publish:

```console
$ kk publish --downstack --ready
```

`--downstack` publishes the current thread plus unpublished descendants, top-down (see [Publishing · flags](../09-publishing.md#flags)). `--ready` opens both PRs ready for review rather than as drafts (see [Publishing · defaults](../09-publishing.md#defaults)). kiki publishes ancestors first, then descendants: skeleton's PR is created with base `main`; auth-biometric's PR is then created with base `android-skel`. Each PR opens a separate editor session so the developer can shape its title and body — the AI-drafted text is a starting point, not the finished version. The transcript is not input to PR drafting (see [Publishing · PR text](../09-publishing.md#pr-text)).

Once both editors close and `gh` returns success, `kk log --wide` shows the stack annotated with PR state, CI roll-up, agent state, and last-activity age (see [Commands · `kk log`](../11-commands.md#kk-log)):

```console
$ kk log --wide
●─auth-biometric  [#143] ●  "Biometric-first auth flow"  ready  ●●●●● ci green  working    34s
●─android-skel    [#142] ●  "Scaffold Android navigation"  ready  ●●●●● ci green  working   12m
●─main
```

Reviewers approve through the day; the skeleton PR merges first. kiki polls GitHub through `gh` and notices the merge. For `auth-biometric`, the parent-merged auto-cascade kicks in (see [Cascade · parent merged](../07-cascade.md#parent-merged)): kiki rebases the child onto the repo default branch, force-pushes with `--force-with-lease`, updates the child PR's base from `android-skel` to `main`, and only then drops the follows link. The link is dropped only after local and remote updates succeed.

> kkd: the parent-merge transition lives in 07-cascade.md's state machine as `FollowingParent → ParentMergePending → DetachedMovedToDefault`. The follows link is dropped only after local and remote updates succeed. The auth-biometric thread is now an independent thread targeting `main`, not a child of `android-skel`.

The `auth-biometric` row in the Stack updates after the parent-merge transition: the follows arrow `←●` disappears, since auth-biometric no longer follows anything. Shortly after, reviewers approve `auth-biometric` and that PR merges too. The week's port has landed on `main` as two clean commits.

## Act 10 — Closing out

### Fri 09:00 — across repos

Friday morning, the developer cleans up. `auth-biometric` and `android-skel` each have a merged PR; their threads have done their job. `kk close` archives them. The agent stops, the tmux session is killed, the jj workspace is forgotten, the materialized workspace directory is removed, and the threads transition to `Closed` (see [Threads · close](../05-threads.md#close)). Tracked jj revisions live on `main`; bookmarks are kept; PRs are left untouched (already merged). The developer does the same in `kestrel-docs` after a smaller PR cycle on the `android-docs` thread.

```console
$ kk close                                  # in auth-biometric
$ kk switch android-skel && kk close
$ cd ~/code/kestrel-docs && kk close        # android-docs
```

A final `kk ls --all-repos --all` (the `--all` flag includes closed threads, the `--all-repos` flag widens repo scope — they are independent, see [Commands · `kk ls`](../11-commands.md#kk-ls)) shows the week as a flat list across the three repos:

- `kestrel-mobile/android-skel` — closed
- `kestrel-mobile/auth` — closed (the password-first version, abandoned mid-week)
- `kestrel-mobile/auth-biometric` — closed (the biometric-first replacement, merged)
- `kestrel-docs/android-docs` — closed
- `kestrel-www/copyright-2026` — closed

Bare `kk` from `kestrel-mobile` opens the overlay with no active work remaining; the closed threads are reachable through `kk ls --all` and `kk reopen <thread>` if anything from the week needs revisiting. Five threads were spawned, one was abandoned, four merged. The follows DAG is empty; the cascade outbox is empty; the daemon is idle.

## Epilogue

The patterns this storyboard demonstrates and the chapters that authorize them:

- **Branching** — acts 3 and 7. `kk new --follows <parent>` records a live cascade edge in the follows DAG (see [Threads · creation](../05-threads.md#creation), [Cascade · trigger](../07-cascade.md#trigger)).
- **Merging back** — acts 5 (a single thread merging direct to `main`) and 9 (a stacked publish where the parent merge auto-rebases the child onto `main`) (see [Publishing](../09-publishing.md), [Cascade · parent merged](../07-cascade.md#parent-merged)).
- **Abandoning** — act 7's `kk close` of the wrong-direction `auth` thread, retaining the transcript and revisions for possible reuse, in contrast to the irreversible `kk thread destroy` (see [Threads · close](../05-threads.md#close), [Threads · destroy](../05-threads.md#destroy)).
- **Cross-repo** — acts 1 (registration), 5 (`kestrel-www` copyright bump), 6 (`kestrel-docs` parallel work). One daemon, per-repo registration, `kk ls --all-repos` for the global view (see [Commands · `kk ls`](../11-commands.md#kk-ls)).
- **Cascade in motion** — act 4 (small ancestor change, hop-by-hop propagation), act 8 (textual conflict and human resolution). Both demonstrate that direct `jj` operations are first-class inputs to the coordinator, not gated by it (see [Cascade](../07-cascade.md), [Invariants](../04-invariants.md)).
- **Stacked publish** — act 9. `kk publish --downstack` publishes ancestors first; the parent merge then auto-migrates descendants onto the repo default branch (see [Publishing · flags](../09-publishing.md#flags), [Cascade · parent merged](../07-cascade.md#parent-merged)).

If the storyboard appears to require any behavior the rest of the book does not authorize, that is a finding. The storyboard is illustrative; the specification is normative.
