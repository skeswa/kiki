# Appendix B: User Stories

User stories are part of the book's contract with the implementer. They preserve the use cases that gave the normative chapters their shape: what the engineer is trying to do, what friction kiki is meant to remove, and where the v1 boundary was deliberately drawn.

Read these before the invariants. If a story and a normative chapter appear to pull in different directions, the invariant and behavioral chapter govern the implementation. The story still matters: it names the user need that the implementation must satisfy without violating the stricter rule.

## Setup and lifecycle

1. As a developer, I want to install `kk` from a single binary distribution, so that getting started is one command.
2. As a developer, I want to run `kk init` in a git+jj repository to opt that repo into kiki management, so that I am explicit about which repos kkd watches.
3. As a developer, I want kk to verify only local coordination prerequisites at `kk init` — notably that jj is initialized — so that a missing GitHub login does not block local work. Harness binaries are checked at `kk new`; `gh` and GitHub authentication are checked lazily at `kk publish` or explicitly via `kk doctor --github`.
4. As a developer, I want kkd to start automatically the first time I invoke `kk`, so that I never have to think about daemon lifecycle.
5. As a developer, I want kkd to recover from crashes by reading its sqlite state on restart, so that my threads survive daemon issues.
6. As a developer, I want kkd to be resurrectable across system restarts via launchd/systemd-user, so that my threads survive reboots.
7. As a developer, I want `kk init` to NOT auto-spawn a starter thread, so that I am explicit about when threads are created.

## Thread creation

8. As a developer, I want `kk new <name>` to spawn a thread with its own jj workspace, terminal group, and managed agent (Claude Code by default), so that I start a new line of work instantly.
9. As a developer, I want `kk new` (no name) to derive a placeholder name from my initial prompt, so that I do not have to commit to a name upfront.
10. As a developer, I want `kk new <name> --follows <parent>` to create a child thread coupled to a parent, so that I can stack work on top of a work-in-progress feature.
11. As a developer, I want `kk new <name> --no-follow` to create a snapshot fork (no live coupling), so that I can branch off the current state without inheriting future changes when the contextual default would otherwise follow the current thread.
12. As a developer, I want `kk new --harness <name>` to override the default agent harness for a single thread, so that I can pick the right one per task — Claude Code for one thread, Codex for its sibling. (v1: `claude-code` and `codex` are accepted; any other harness name errors with a clear "unsupported harness, see [agent.default_harness] config" message until further adapters are added.)
13. As a developer, I want each thread to live in its own jj workspace so agents in different threads do not accidentally interfere with each other's files in the course of normal cooperative work, so that parallel agentic work stays in its own lane. (This is a cooperative isolation property, not filesystem access control; see Trust model: same-UID processes can still reach sibling workspaces.)
14. As a developer, I want to spawn N sibling threads off the same starting point in parallel (e.g., one per caller of a function I'm refactoring), so that I can fan out migration work across agents simultaneously.
    14a. As a developer, I want the active workspace's `@` to be the thread's live head while its bookmark remains an explicit checkpoint/publication projection, so that ordinary `jj new` behavior cannot silently leave kiki following or publishing the wrong commit.
    14b. As a developer, I want thread creation to recover durably from a daemon crash at any external step and to start the harness only after credentials and isolated hook configuration are ready, so that “atomic spawn” does not depend on impossible cross-system rollback.

## Switching and orientation

15. As a developer, I want `kk switch <thread>` to move my own Herdr client to that thread's agent pane without mutating any terminal or daemon state, so that switching is instant and never restarts, recreates, or repairs anything as a side effect.
    15a. As a developer, I want `kk attach [<thread>]` to open a Herdr client on kiki's dedicated terminal server, addressing it by kiki's configuration root and session name for me and asking kkd to make sure it is running, so that any terminal can become a view onto my threads without touching the Herdr server I use for other work.
    15b. As a developer with several clients attached — two monitors, or a second person looking on — I want `kk switch` to move only the client that invoked it, to refuse and name the missing required `client_targeted_focus` extension when the terminal server cannot target one client, and to offer `kk switch --all-clients` as a separately named operation, so that nobody's view moves unless they or I asked for exactly that.
    15c. As a developer, I want a `kk switch` that has no identifiable viewer — run by an agent, a script, or a pane nobody is looking at — to move no one and say so, so that automation cannot yank my view.
16. As a developer, I want a Herdr keybinding, generated by kiki in its own Herdr configuration, that opens the kk overlay as a popup for fast switching and spawning, so that I never have to leave my current view.
17. As a developer, I want `kk` with no arguments to open the interactive TUI, so that I can browse and act on threads visually.
18. As a developer, I want `kk ls` to list active and repair-relevant operational threads with lifecycle labels that remain distinct without color, so that creating, failed, closing, or projection-diverged work cannot disappear from the default view.
19. As a developer, I want `kk ls --all` to include closed threads, so that I can find archived work.
20. As a developer, I want Herdr's native sidebar to list every thread's terminal group across my registered repos, labelled by kiki and, in v1.x, carrying lifecycle, cascade, agent, and follows tokens that are distinguishable without color, so that I have ambient peripheral awareness while heads-down. I understand those rows are a one-way projection that kiki republishes and never reads back; `kk ls` is the truthful list.
21. As a developer, I want `kk` invocations inside a thread's terminal group to know which thread I am in — from an explicit target, then `KIKI_THREAD_ID` on the panes kiki provisions, then the Herdr pane identity of a pane I split myself, then cwd — so that thread-acting commands work without specifying a target and a pane on some other Herdr server is never mistaken for a thread.
22. As a developer, I want `kk` invocations outside any registered repo to show threads across all registered repos, so that I get the full picture from anywhere.

## Cascade coordination

23. As a developer working in thread A, I want jj's native evolution of descendant thread B to be materialized safely for B's agent, without redundantly rebasing work jj already evolved, so that refactoring naturally flows downstream.
24. As a developer in thread B (a child of A), I want my agent to receive a clear "your base changed, here is the diff" signal at the next tool boundary when A's revisions are amended, so that the repository may evolve immediately while B's files and agent context move together.
25. As a developer, I want kiki to materialize evolved state or perform an explicit follows rebase ONLY at agent tool boundaries or quiescence, never with the managed agent mid-edit, so that the agent's mental model never diverges from what is on disk. I understand that a direct human `jj` command in a stale child workspace is an explicit escape hatch that may materialize it earlier; at the next boundary kiki must probe actual files and recover unsnapshotted edits rather than assume the op log tells the whole story.
26. As a developer, I want the cascade to handle textual conflicts by marking the thread "conflicted" and surfacing a notification, so that I resolve them deliberately instead of corrupting agent state.
27. As a developer in a child thread B that follows parent A, I want B to pick up A's newly added live-head commits automatically through an explicit boundary-safe `ParentAdvance` reconciliation, so that stacked work stays coordinated without pretending A's bookmark automatically followed `jj new`.
28. As a developer, I want `kk thread detach` to synchronously catch up the operation DAG, surface any parent transition that watcher lag had not recorded yet, checkpoint my exact child head, and only then break the live-follow link, so that detach cannot silently discard a parent advance. This is the v1 graph-surgery escape hatch; attach and reparent remain deferred.
29. As a developer, I want `kk thread attach <child> --to <parent>` to re-establish a follows link, so that I can resume live coupling after a turbulent moment. (Deferred beyond v1.)
30. As a developer, I want `kk thread reparent <child> --onto <new-parent>` to move a thread under a different parent, so that I can correct stack relationships when I realize the topology was wrong. (Deferred beyond v1.)
31. As a developer, I want kk to refuse cyclic follows links, so that the coupling graph stays a DAG.
32. As a developer, I want the v1.x GitHub integration to move a child locally onto the exact merged default-branch commit, then present a one-shot-approved remote force-push/PR-base plan and detach only after local and remote state agree, so that stacked work survives the parent landing without silently reusing an older publish approval.
33. As a developer, I want kk to escalate from soft-pause to SIGINT+resume only when the safety contract requires it—dirty or indeterminate files before mutation, textual conflicts or divergent successors, ambiguous topology, an unprovable delivery barrier, prolonged pure thinking with no boundary, or my explicit `kk thread interrupt`—so that disruption is rare but never preferred over edit or delivery safety.
34. As a developer, I want `kk thread interrupt <thread>` as the explicit human escape hatch to hard-stop and re-frame an agent, so that I can rescue a stuck or off-track thread.
    34a. As a developer, I want kiki to block every tool call in a dispatched tool batch when one call triggers reconciliation, and to acknowledge delivery only after that batch closes and a later model turn begins, so that a sibling call from the same batch cannot observe new files before the agent receives the explanation. (Claude Code's parallel batch is the hard case; Codex's proven-serial dispatch makes each batch a single call.)
    34b. As a developer, I want v1 managed sessions — Claude Code and Codex alike — to reserve the pre-tool boundary exclusively for kiki, with a clear startup diagnostic when effective user hooks would race it, so that the safe boundary is real rather than configuration-order folklore.

## Ambient coordinator

35. As a developer, I want to run `jj` directly inside or outside any thread's workspace and have kk react to my ops, so that kk feels additive to my normal jj workflow rather than invasive.
36. As a developer, I want kk to detect when an agent invokes `jj` via Bash and react identically to a human invocation, so that the abstraction does not leak.
37. As a developer, I want kk to distinguish deletion/movement of a parent's checkpoint bookmark from external `jj abandon` of its live head or owned revisions, so that bookmark drift enters projection repair while ancestry destruction stops as topology divergence instead of either event silently changing my follows base.
38. As a developer, I want kk to never re-react to its own jj ops (op-attribution dedupe), so that the system cannot fall into self-triggered loops.
39. As a developer, I want kk to traverse jj's complete operation-head frontier, preserve incomparable concurrent operations instead of ordering them by timestamp, and coalesce compatible rapid-fire triggers into one cascade per thread, so that op storms stay quiet without losing a branch of the operation DAG.
40. As a developer, I want kk to detect when something other than kk force-pushes a thread's branch (manual `git push --force`, etc.) and surface a "remote diverged" warning requiring explicit reconciliation, so that I never have a silent mismatch between local and remote state.
    40a. As a developer, I want kiki to track my checkpoint bookmark through jj's own rewrite successors without complaint, and to detect missing, externally moved, or conflicted bookmarks, missing jj workspace records, path mismatches, missing terminal groups or agents, and orphaned processes, repair only provably unambiguous cases automatically, and otherwise guide me through `kk repair`, while continuing safe live-head observation when the workspace itself is still uniquely identified, so that an ordinary edit never sends a thread to repair and an unrelated bookmark or terminal problem does not silently freeze follows coordination.
    40b. As a developer, I want kiki to look for processes it recorded that outlived their pane, terminal group, or terminal server — and for any workspace holder that belongs to no pane in the current terminal — before it starts a replacement agent and before it deletes a jj workspace, to block both while one survives, and to offer an approved terminate-and-verify of exactly the recorded processes or leave the thread blocked, so that two writers never share a workspace and a process kiki did not start is never signalled on a guess.

## AI auto-evolution

41. As a developer, I want kk to track ownership of revision descriptions and bookmark names before background AI evolution writes either surface, so that the invariant "never overwrite human-authored prose" is proven with the v1.x metadata feature rather than burdening the initial coordination slice.
42. As a developer, I want kk to eventually auto-evolve bookmark names and revision descriptions as work takes shape, so that my history narrates itself. (Stretch / post-v1 execution.)
43. As a developer, I want auto-rename and auto-describe to fire when the thread's agent has been quiescent for a configurable window OR after specific events (`jj split`, `jj squash`), so that the AI loop never races my agent. (Stretch / post-v1 execution.)
44. As a developer, I want kk to NEVER silently overwrite a description I or my agent typed, so that my prose and intent stay intact and kk remains trustworthy.
45. As a developer, I want kk to NEVER re-rename a bookmark I renamed manually, so that my deliberate naming sticks for the rest of the thread's life.
46. As a developer, I want `kk thread describe --refresh` to opt a revision back into auto-describe, so that I have an explicit escape hatch when I want kiki to take over again. (Stretch / post-v1 with auto-describe.)
47. As a developer, I want auto-describe to use a fast, cheap model (e.g., Haiku-class), so that auto-AI cost stays modest.
48. As a developer, I want auto-describe to discard its model output if the input state changed during model latency (input-hash recheck), so that descriptions never describe stale content.
49. As a developer, I want auto-rename's prompt to include sibling bookmark names so the model picks a distinct slug, so that I never end up with two threads colliding on the same name.
50. As a developer, I want a squash that combines a kk-owned revision with a human-owned one to mark the squashed result as human-owned, so that ownership defaults to the more conservative side.

## Publishing

51. As a developer, I want the first v1.x `kk publish` flow to open `$EDITOR` with text derived only from explicit command input and non-transcript metadata, with opt-in AI prefill added later alongside the metadata execution loop, so that manual publishing does not wait for or silently invoke a model.
52. As a developer, I want `kk publish --no-edit` to skip the editor and use the exact generated non-transcript draft shown in the approved plan, whether deterministic in the first release or AI-assisted after that feature ships, so that low-stakes PRs are one command without changing the egress boundary.
53. As a developer, once AI publishing assistance ships, I want `kk publish --no-ai` to force the manual non-model drafting path, so that I can write sensitive PRs without model involvement. The flag is not part of the first manual publishing release.
54. As a developer, I want `kk publish -m "<title>"` to set the title inline, so that I can fast-path simple cases.
55. As a developer, I want `kk publish --ready` to open the PR as ready-for-review (default is draft), so that I do not unnecessarily block reviewers on WIP.
56. As a developer, I want `kk publish` from a child thread whose parent is unpublished to automatically publish ancestors first (top-down), so that the PR stack is wired up correctly.
57. As a developer, I want each thread in a stack publish to get its own editor session top-down, so that I can review and edit each PR title/description as it is published.
58. As a developer, I want `kk publish --downstack` to publish the current thread plus all unpublished descendants, so that I can land a feature tree in one command.
59. As a developer, I want a thread's PR base to default to the parent thread's branch when stacked, otherwise to the repo's default branch (resolved from `gh repo view`), so that stack relationships translate correctly to GitHub.
60. As a developer, I want PR descriptions to be human-territory after creation (kk does not silently overwrite), with `kk publish --refresh` as an opt-in regenerator, so that my reviewer-facing prose is stable.
61. As a developer, I want a child thread to be reconciled locally onto the exact merged default-branch commit when its parent merges, then receive an exact one-shot approval plan for `--force-with-lease` and PR-base update before those remote mutations occur, so that stacked PRs survive landing without granting unattended remote authority.
62. As a developer, I want the v1.x `kk thread comments` surface to list a thread's PR review comments read-only inside the thread context, so that I can respond with full context.

## Closing and reopening

63. As a developer, I want `kk close` to freeze and prove quiescent every process in the thread's terminal group — the agent, the shell, and any panes or tabs I added — rerun loss-prevention and operation-frontier checks against the exact approved plan, resume the original process states if safety or the approval fingerprint changed, and otherwise checkpoint the exact head and reconcile/detach children before closing the terminal group, forgetting the workspace, and removing the directory, so that a failed or drifted close never leaves a dead thread labeled Active or reuses stale approval.
    63a. As a developer, I want `kk close` to treat the terminal server's "closed" reply as a request acknowledgement only, and to forget and delete the jj workspace only after every frozen process is verified gone by OS process identity and no other process holds the workspace, so that a background job that ignored the hangup can never be writing into a directory kiki is deleting. If exit cannot be verified, I want the files kept and the failure reported.
64. As a developer, I want `kk close` run from outside the closed thread to move my own client to the parent thread when it is active, a `kk close` typed inside the thread to simply end with it and leave the result in `kk ls`, and otherwise Herdr to place any client that was showing the closed terminal group, so that I keep working without manual switching and nobody else's view is moved on my behalf.
65. As a developer, I want `kk reopen <thread>` to restore an archived thread through a restart-recoverable journal whose launcher must report ready before the thread becomes Active, so that a crash during workspace, credential, terminal-group, or harness recreation leaves an honest repairable state.
    65a. As a developer whose machine rebooted or whose terminal server restarted, I want the layouts Herdr restores to be treated as empty containers — no agent resumed by the terminal runtime, no thread reported Active — and each affected thread to show `TerminalMissing` until I run `kk repair`, which either restarts the agent with a fresh credential, launch settings, gate, and ready handshake, or closes the thread without one, and in both cases names and handles the restored shells itself instead of asking me to clean them up first, so that a pane that merely reappeared is never mistaken for a managed agent.
66. As a developer, I want parent close to synchronously refresh every child edge, require a choice for any newly discovered transition, and while the parent is frozen checkpoint and detach each child before closing the parent's terminal group, so that watcher lag or a failed detach cannot erase a parent advance or leave an unresumable parent.
67. As a developer, I want a merged PR to auto-archive its thread with a 5-second undo grace period, so that completion cleans itself up. Merge polling, notification, state updates, and auto-archive all ship with the v1.x GitHub integration rather than the coordination acceptance slice.
68. As a developer, I want a PR closed-without-merge to surface a notification but NOT auto-archive its thread, so that I can decide whether to keep iterating.
69. As a developer, I want `kk thread destroy` to preserve jj revisions by default while deleting the local thread projections through a method-bound journal, and require a separate `--abandon-revisions` approval naming an exact validated chain with no registered or foreign descendants, so that ordinary cleanup never implies history loss or expands an inferred `jj abandon` revset.
70. As a developer, I want plain `kk close` to leave any open PR untouched, with `kk close --discard-pr` as the explicit "also close the PR" option, so that GitHub-visible state is preserved unless I deliberately change it.

## Observability and notifications

71. As a developer, I want acceptance-slice OS notifications for agent permission prompts, cascade conflicts, and local parent abandonment, with merge and PR-check notifications added by the v1.x GitHub integration, so that unavailable remote polling is not implied by the core coordinator.
72. As a developer, I want notifications to be configurable per-event-type, so that I can tune signal vs. noise.
73. As a developer, I want CI status changes on a PR to surface as notifications but NOT auto-trigger any fix action, so that kk does not make assumptions about what to do.
74. As a developer, I want the TUI to show a tree of threads (parent-child via follows), so that I can visualize my work structure.
75. As a developer, I want `kk status` to distinguish the live workspace head from its bookmark checkpoint, showing where kiki last placed the checkpoint, the target it now expects after jj's own rewrites, and whether that target is `current`, `behind`, or `diverged` relative to the head; v1.x may add PR state, so that ordinary bookmark lag is never mistaken for lost work.

## Configuration

76. As a developer, I want layered TOML configuration (defaults -> repo-shared-committed -> user-global -> repo-local-gitignored -> per-thread -> env -> CLI flags), so that team defaults can be committed while personal overrides stay personal.
77. As a developer, I want `kk config get|set|unset|edit|show` commands, so that I can manage config without hand-editing files.
78. As a developer, I want `kk config get <key>` to show which layer the effective value came from, so that "why is my config not taking effect" is fast to debug.
79. As a developer, I want unknown config keys to produce warnings (not errors), so that old configs survive kk upgrades.
80. As a developer, I want an opt-in `Kk-Auto: true` description trailer for transparency, so that I can audit which descriptions were AI-written.

## Pluggable UI architecture

81. As a future local UI author, I want a stable gRPC contract over a unix socket exposing daemon state and behavior, so that I can build another same-host UI without modifying kkd. Remote and mobile clients may reuse service semantics, but require a future transport and authentication contract.
82. As a future UI author, I want server-streaming events for thread state changes, so that my UI reacts in real-time without polling.
83. As a developer, I want `kk` CLI, `kk` TUI, and `kk-hook` to be pure clients of the same gRPC API (no privileged internals), so that UIs and the daemon evolve independently.

## Cross-repo

84. As a developer, I want one kkd per user, not per repo, so that I have a single mental model: one daemon, one credential surface, one set of CLI verbs, even though each `kk` TUI invocation is repo-scoped (the cross-repo view ships as `kk ls` with the `repo` column).
85. As a developer, I want `kk init` in each repo to be the per-repo opt-in, so that kkd is explicit about what it manages.
86. As a developer, I want `kk ls` outside a registered repo to list threads across ALL registered repos with a `repo` column, so that I get the full picture.
87. As a developer, I want `kk ls` inside a registered repo to default to that repo, with `--all-repos` to widen the repo scope to every registered repo and `--all` to widen the lifecycle scope to include closed threads (the two flags compose independently), so that the contextual default matches my likely intent and the two scope axes never conflate.

## Hooks and harness integration

88. As a developer, I want kk to launch its managed Claude session with isolated, launch-scoped hook settings, so that my non-kk Claude Code work is unaffected and tracked `.claude/settings.json` is never overwritten.
89. As a developer, I want kiki to refuse an unsafe managed session when it cannot prove exclusive control of the pre-tool boundary, while preserving unrelated hook types only when the harness can isolate them, so that concurrent user hooks cannot race workspace reconciliation.
90. As a developer, I want any fallback merge into `.claude/settings.local.json` to preserve prior bytes through a content-hash ownership record and restore only kiki's own fragment on close, so that nothing user-owned is overwritten or deleted.
91. As a developer, I want kk to launch its managed Codex session under a generated launch-scoped `CODEX_HOME` with kiki's hooks pre-trusted and my own `~/.codex/` configuration structurally excluded, so that my non-kk Codex work is unaffected and nothing under `<workspace>/.codex/` is ever written.
    91a. As a developer on a harness version that cannot prove its batch boundary (a Codex version whose dispatch discipline changed, or a Claude Code version without an unambiguous batch-completion signal), I want kk to gracefully degrade to proof-carrying restart+resume for context delivery, so that the tool still works, just less smoothly. A version that cannot supply the restart proofs either is unsupported for managed execution, not silently approximated.
92. As a developer, I want the `kk-hook` sidecar to add imperceptible latency (target <5ms typical) to each agent tool call, so that the hook never feels in the way.

## Trust model and auditability

93. As a developer, I want destructive, cross-thread, sensitive-read, and externally visible operations to require a one-use approval bound to the exact method and target and issued through an interactive foreground flow, so that a buggy hook or agent invoking `kk` cannot inherit reusable human authority.
94. As a developer, I want each thread's `kk-hook` to be issued a `ThreadScoped` credential bound to that thread's id, so that even if a hook's behavior is wrong it cannot mutate any other thread's state.
95. As a developer, I want every parseable daemon transport attempt (accepted or rejected, gRPC or MCP) recorded exactly once in SQLite—with resolved-repo attempts in that repo's audit table and unscoped or unresolved attempts in the user-level table—so that operational history is queryable without inventing a repo for bootstrap or failed routing.
96. As a developer, I want `kk audit log` and per-thread audit slices via `kk thread audit` to surface the audit trail, while understanding that append-only is enforced by daemon APIs and is not tamper-proof against my UID.
97. As a developer, I want the trust model documented honestly: one-shot approvals reduce accidental agent authority but do not defend against an actively malicious same-UID process that can impersonate user interaction or modify local state.

## Thread transcript

98. As a developer, I want kkd to capture each human-authored, agent-authored, and kk-authored conversational text event in a thread to a durable on-disk log bound to the jj change-id that was `@` at capture time, so that I have a recall surface separate from what was committed.
99. As a developer, I want the thread transcript to live in `~/.config/kiki/repos/<repo_id>/state.db` (centralized under `~/.config/kiki/`, never pushed, and never inside the source repo's filesystem), so that prose containing dead ends, tool errors, or quoted file contents does not enter the repo or publication paths; separately consented provider egress remains explicit.
100.  As a developer, I want `kk thread transcript [<change>]` to print messages for a change, with `--search <query>` for full-text, `--range <from>..<to>` for spans, and `--recent <n>` for tail-of-thread, so that I can recall context as a human reader.
101.  As a developer, I want my agent to be able to retrieve from its own thread's log mid-task via a kiki-hosted MCP server, so that the agent can recall what happened earlier without me bridging it manually. This follows the v1.x human transcript surface and is not acceptance work.
102.  As a developer, I do NOT want my agent to read another thread's log via MCP in v1, so that cross-thread context-sharing waits for the v2 substrate design and its safety mechanisms (causal-chain detection, depth caps, audit trail).
103.  As a developer, I want the v1.x `kk reopen --catch-up` flow to preview and, after first-use consent, send a brief transcript-derived catch-up to the resumed agent, so that a reopened thread need not be a cold start and provider egress is never mislabeled as local-only.
104.  As a developer, I want auto-describe and PR drafting to NOT read from the locally stored transcript, so that recall prose cannot silently leak into published artifacts.
105.  As a developer, I want `kk thread destroy` to delete the thread transcript alongside the bookmark by default, with `--keep-log` as the explicit retention opt-out, so that destroy means destroy unless I say otherwise.
106.  As a developer, I want the capture path abstracted behind a `TranscriptAdapter` trait, so that future harnesses (Codex, others) can be added without touching the log schema or the read API.
107.  As a developer, I do NOT want token-streaming deltas, structured tool-call inputs and outputs, or extended-thinking blocks captured in the initial transcript release, so that the log is a readable narrative rather than a verbose event stream.

## Revision and status view (`kk log`, `kk status`)

108. As a developer, I want `kk log` to be the daily-driver revision view, analogous to `jj log`, but stack-aware: my current thread's revisions render in detail and unrelated threads collapse to one-line summaries, so that I see what I am working on without drowning in everyone else's history.
109. As a developer, I want `kk log`'s default expansion to follow the entire follows-stack the current thread sits in (current + every ancestor thread up to trunk), so that stacked work reads as one coherent chain instead of forcing me to switch threads to see what I am building on.
110. As a developer, I want sibling and unrelated threads to render as collapsed one-liners showing the bookmark, an optional PR number, a status glyph, and the thread's last revision description, so that scanning is cheap and the screen stays useful.
111. As a developer, I want `kk log --no-stack` to drop to strict-current-thread expansion (ancestors collapse), so that I have a focused view when the stack is irrelevant to what I'm reading.
112. As a developer, I want `kk log --all` to include closed/archived threads as collapsed lines, so that I can find archived work without leaving the log.
113. As a developer, I want `kk log --wide` (`-w`) to switch collapsed lines to a richer format including PR draft/ready state, CI roll-up, and agent state, so that I get a one-screen status view when I want one.
114. As a developer, I want `kk log -r <revset>` to pass through to a jj revset and render results with kk decoration (PR badges, thread coloring) but disable collapse logic, so that I have one explicit escape hatch for "I know exactly what I want."
115. As a developer, I want `kk log -r` combined with `--no-stack`/`--all`/`--wide` to error rather than silently ignore the conflicting flag, so that the override semantics stay unambiguous.
116. As a developer, I want `kk log` invoked when no thread can be resolved from an explicit target, the environment, Herdr pane identity, or cwd to render the trunk in detail with all repo threads as collapsed lines, plus a header announcing the degraded state, so that the command is always useful from anywhere in a registered repo.
117. As a developer, I want `kk log` invoked outside any registered repo to error with a pointer to `kk ls` (the cross-repo view), so that `kk log` and `kk ls` stay distinct concepts.
118. As a developer, I want `kk status` to render a small kk-shaped header (thread, PR, CI, agent state, follows summary) followed by literal `jj st` output for the working copy — run by the `kk` CLI in my own contextual workspace exactly as if I had typed it, never by the daemon, while the header comes from pinned reads that do not touch the working copy — so that I get the thread context plus the file listing I already know how to read and no background process ever snapshots my files.
119. As a developer, I want `kk status --diff` (`-p`) to append the working-copy patch (and `--diff --stat` for diffstat) through the same explicit, human-invoked passthrough in my own contextual workspace, so that I can review changes without dropping to `jj diff`.
120. As a developer, I want `kk status --no-jj` to suppress the working-copy section and emit only the kk header, so that I can script against the thread context and so the overlay and UI pane can reuse the same renderer cheaply.
121. As a developer, I want the cascade-state indicator in `kk status` to be three-valued (`in sync` / `pending` / `conflicted`) with no count, so that the most common signal is glanceable and the noisy edge ("how many cascades behind") doesn't become a recurring distraction.
122. As a developer, I want `kk` to remain pure porcelain: `kk log` and `kk status` adopt no jj flags beyond `-r <revset>`, so that anything jj can do, I do via `jj` directly without learning a near-mirror surface that risks subtle drift.

## Interactive overlay TUI (`kk` / overlay keybinding)

123. As a developer, I want the overlay TUI to be a left sidebar plus a right-hand content pane, where the sidebar shows two sections: a Stack section (the same stack-aware log as `kk log` with the current thread's status inlined under its bookmark line) on top and an Activity section (the same threads, flat-listed by most-recent agent event) below it, so that one panel answers both "where am I in the work?" and "who needs me?" without me leaving navigation.
124. As a developer, I want the navigation cursor to move on log lines (j/k or arrows) and `enter` to switch to the cursored thread (dismissing the overlay), so that the most common action is the cheapest keystroke.
125. As a developer, I want `space` to preview the cursored thread in the right pane (transcript tail / diff / comments toggleable via `t`/`d`/`c`) without changing my active thread, so that I can peek before committing to a switch.
126. As a developer, I want destructive and creative verbs (`n` spawn, `N` spawn-as-child-of-cursored, `p` publish, `x` close, `i` interrupt) to be available only in the overlay TUI, not in the UI pane or Herdr's sidebar, so that a stray keypress or click in a passive surface can't take action. (`c` is reserved for the PR-comments preview in story 125; close binds to `x` to avoid the collision.)
127. As a developer, I want consequential overlay verbs (`x`, `i`) to open a daemon-issued approval card rather than firing immediately, and that card to be drawn only by kiki's own foreground presenter — never by a Herdr toast, plugin, keybinding, or sidebar row — so that fat-fingering does not cost me work and the confirmation is bound to the exact plan.
128. As a developer, I want lowercase `t` in the overlay to surface a transcript-tail preview in the right pane (alongside `d` diff and `c` PR comments) and shift-`T` to escalate to a full-screen `kk thread transcript` reader for the cursored thread, so that the cheap glance and the deep drill-down sit on the same letter at two different intensities.
129. As a developer, I want `?` to surface a help overlay listing the active keymap, so that the action set is discoverable rather than memorized.

## Herdr sidebar and UI pane (opt-in)

130. As a developer, I want to opt into a UI pane (left of the agent, `[ui] ui_pane_width` columns) in every thread's terminal group via `[ui] ui_pane = true` in my user-global config, so that I have the Stack tree permanently visible without invoking the overlay, alongside the thread list Herdr's sidebar already gives me.
131. As a developer, I want `kk new <name> --sidebar` / `--no-sidebar` to override my UI-pane default per thread, so that one-off threads can opt in or out without changing global config.
132. As a developer, I want the UI pane to render the same Stack tree and inlined status the overlay does, and Herdr's sidebar to carry the cross-repo list and attention state, so that there is one mental model for each view regardless of where it lives and kiki does not rebuild what Herdr already draws.
133. As a developer, I want the UI pane restricted to navigation-only keys (j/k/arrows/enter/?, plus mouse click-to-focus and scroll). Destructive/creative verbs are not bound, so that accidental focus on the UI pane cannot mutate state.
134. As a developer, I want the role panes — agent, shell, and UI — to be provisioned with the terminal group during `kk new`'s recoverable creation saga, each launched by direct argv with an explicit working directory and environment, and ensured again only at `kk reopen` and at a `kk repair` terminal restart, never at `kk switch`, so that the panes are reliably present without pretending the terminal runtime participates in a database transaction and without navigation mutating my layout.
135. As a developer, I want kk to NOT put back a shell or UI pane I deliberately closed until the thread is reopened or its terminal is restarted, so that my layout choices are honored; if I want another shell I split one natively in Herdr.
136. As a developer, I want role panes provisioned whether or not any client is attached and whatever its size, with Herdr's own resize and zoom handling a narrow terminal, so that thread creation never depends on which window I happened to run it from.
137. As a developer, I want toggling `[ui] ui_pane` after threads exist to take effect the next time a terminal group is provisioned (`kk new`, `kk reopen`, or a terminal restart), not retroactively reshape live terminal groups, with a config-set warning making the lag visible, so that I'm not surprised when an existing thread stays unchanged.

## Shell pane (opt-out)

137a. As a developer, I want every thread's terminal group to come up with a shell pane alongside the agent pane in the same tab by default (positioned below the agent in the default layout, or to the right via `[ui] shell_pane_position`), with cwd set to the jj workspace, `KIKI_THREAD_ID` set explicitly, no approval or Admin credential in its environment, and the shell process taken from my `$SHELL`, so that direct `jj` / `gh` / test invocations live alongside the agent without me having to spawn a separate terminal and `cd` into the workspace each time.

137b. As a developer, I want the shell pane to end with the terminal group at `kk close` along with the agent (and any other panes or tabs I added), with every process in them named in the close plan, frozen, and verified gone, so that the close blast radius is unambiguous and I learn not to leave long-running jobs in the thread's panes expecting them to survive.

## Stated non-goals

138. As a developer, I do NOT want kk to manage or cap my agent's resource consumption (CPU, RAM, tokens), so that those decisions stay in my hands.
139. As a developer, I do NOT want kk to refuse `jj`, `gh`, or native Herdr operations I run directly, so that kk remains additive infrastructure.
140. As a developer, I do NOT want kk to surface CPU/RSS for agent processes; that is what Activity Monitor and htop are for, and duplicating them poorly clutters kk.
141. As a developer, I do NOT expect per-thread workspace isolation to act as a security boundary (filesystem ACLs, sandboxing) in v1; that is a future-version concern. v1 promises only cooperative separation.
