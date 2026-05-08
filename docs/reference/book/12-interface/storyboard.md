# Storyboard

The earlier chapters describe what kiki does one verb at a time. This chapter describes what kiki feels like across one work-week, by following a single developer through a porting project that crosses three repos and tests every branching, merging, and abandoning pattern the rest of the book commits to.

The protagonist is unnamed. The work is to port the iOS Kestrel app to Android, while product is still iterating on the spec, and while two other repos — the user-facing docs and the marketing site — also need attention along the way. The three repos are:

- `kestrel-mobile` — the iOS/Android codebase, where the port lives.
- `kestrel-docs` — the user-facing product documentation.
- `kestrel-www` — the marketing site, where one copyright year is wrong.

The storyboard introduces no new commands, flags, output strings, glyphs, or screen elements. Every beat in it grounds out in the normative chapters. Where a beat is load-bearing, it cites the chapter that authorizes it. Where it would require behavior the rest of the book does not authorize, that gap is a finding, not a license to extend the surface here.

Acts are time-stamped (`Day · HH:MM — <repo>`) so the temporal arc is legible: product changes its mind twice, work stacks up, a thread is abandoned in flight, a cascade conflicts and recovers, and the week closes with a stack of merged PRs and a quiet TUI.

## Act 1 — Bootstrapping

### Mon 09:14 — kestrel-mobile, kestrel-docs, kestrel-www

None of the three repos are kiki-registered. The developer runs `kk init` in each, in the order they will be touched. `kk init` is idempotent and never creates a starter thread (see [Commands · `kk init`](../11-commands.md#kk-init)).

```console
$ cd ~/code/kestrel-mobile
$ kk init
registered  ~/code/kestrel-mobile  (mon 2026-05-04 09:14:32)
threads     0 active, 0 closed
state       ~/code/kestrel-mobile/.kiki/state.db
ok.

$ cd ~/code/kestrel-docs && kk init
registered  ~/code/kestrel-docs  (mon 2026-05-04 09:15:10)
threads     0 active, 0 closed
state       ~/code/kestrel-docs/.kiki/state.db
ok.

$ cd ~/code/kestrel-www && kk init
registered  ~/code/kestrel-www  (mon 2026-05-04 09:15:32)
threads     0 active, 0 closed
state       ~/code/kestrel-www/.kiki/state.db
ok.
```

The developer hops back into `kestrel-mobile` and types bare `kk`. The repo is registered and the TUI ships, so the overlay opens in `NAVIGATE` mode — but with no threads to navigate, it shows the empty-state placeholder, with `n` and `?` as the only active verbs (see [Interface · spec](spec.md#overlay)).

```text
 kiki · NAVIGATE · kestrel-mobile                                              ?  esc

 STACK                              │  no threads
                                    │
                                    │   press  n  to create one
                                    │
                                    │
 ACTIVITY                           │
                                    │
                                    │
 ─────────────────────────────────────────────────────────────────────────────────────
 kestrel-mobile  main                                                       last op  —
```

> kkd: `kk init` writes a row to `~/.kiki/state.db` (the cross-repo registry) and creates `<repo>/.kiki/state.db` for per-repo runtime state. The daemon is a single user-scoped process; it now knows about three repos, even though only one of them has the developer's attention.

## Act 2 — The skeleton thread

### Mon 10:42 — kestrel-mobile

The first thread will scaffold Android navigation: the gradle module, a top-level `NavHost`, and a Material 3 theme that mirrors the iOS app's tab structure. The developer wants the persistent sidebar pane on for this work, so they pass `--sidebar` and decide to write `[ui] persistent_sidebar = true` into their user config later (see [Configuration](../13-configuration.md)).

```console
$ kk new --sidebar android-skel -m "Scaffold Android navigation: gradle module,
  NavHost, Material 3 theme. Match the iOS app's tab structure but use a
  NavigationBar rather than UITabBarController."
ok. thread android-skel · workspace ~/code/kestrel-mobile-kiki-android-skel · sidebar pane spawned.
```

The tmux client lands inside the new thread's session, with the sidebar pane on the left and the agent pane on the right. The agent has just received the first turn and started reading. The cascade glyph is `──` (in sync, dim) — there's nothing to follow yet.

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
ok. thread auth follows android-skel · sidebar pane spawned.
```

A bare `kk` in either thread now opens the overlay with both threads in the Stack tree. The follows arrow `←●` marks the auth thread as a child of `android-skel`; `▸` marks whichever thread the cursor is on.

```text
 kiki · NAVIGATE · kestrel-mobile/auth                                         ?  esc

 STACK                              │  kestrel-mobile/auth
                                    │
 ● main             ──    in        │  bookmark    auth
 │                                  │  cascade     ── in sync
 ●─android-skel     ──    wrk       │  agent       ● working    34s
 │                                  │  pr          —
 ●─auth          ▸  ──    ←●        │  follows     auth → android-skel → main
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
