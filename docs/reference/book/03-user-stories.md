# User Stories

User stories are part of the book's contract with the implementer. They preserve the use cases that gave the normative chapters their shape: what the engineer is trying to do, what friction kiki is meant to remove, and where the v1 boundary was deliberately drawn.

Read these before the invariants. If a story and a normative chapter appear to pull in different directions, the invariant and behavioral chapter govern the implementation. The story still matters: it names the user need that the implementation must satisfy without violating the stricter rule.

## Setup and lifecycle

1. As a developer, I want to install `kk` from a single binary distribution, so that getting started is one command.
2. As a developer, I want to run `kk init` in a git+jj repository to opt that repo into kiki management, so that I am explicit about which repos kkd watches.
3. As a developer, I want kk to verify prerequisites (jj initialized, gh authenticated, Claude Code installed) at `kk init`, so that I get clear errors instead of cryptic failures later.
4. As a developer, I want kkd to start automatically the first time I invoke `kk`, so that I never have to think about daemon lifecycle.
5. As a developer, I want kkd to recover from crashes by reading its sqlite state on restart, so that my threads survive daemon issues.
6. As a developer, I want kkd to be resurrectable across system restarts via launchd/systemd-user, so that my threads survive reboots.
7. As a developer, I want `kk init` to NOT auto-spawn a starter thread, so that I am explicit about when threads are created.

## Thread creation

8. As a developer, I want `kk new <name>` to spawn a thread with its own jj workspace, tmux session, and Claude Code agent, so that I start a new line of work instantly.
9. As a developer, I want `kk new` (no name) to derive a placeholder name from my initial prompt, so that I do not have to commit to a name upfront.
10. As a developer, I want `kk new <name> --follows <parent>` to create a child thread coupled to a parent, so that I can stack work on top of a work-in-progress feature.
11. As a developer, I want `kk new <name> --no-follow` to create a snapshot fork (no live coupling), so that I can branch off the current state without inheriting future changes when the contextual default would otherwise follow the current thread.
12. As a developer, I want `kk new --harness <name>` to override the default agent harness for a single thread, so that once additional harnesses ship I can pick the right one per task. (v1: only `claude-code` is accepted; any other harness name errors with a clear "unsupported harness, see [agent.default_harness] config" message until further adapters are added.)
13. As a developer, I want each thread to live in its own jj workspace so agents in different threads do not accidentally interfere with each other's files in the course of normal cooperative work, so that parallel agentic work stays in its own lane. (This is a cooperative isolation property, not filesystem access control; see Trust model: same-UID processes can still reach sibling workspaces.)
14. As a developer, I want to spawn N sibling threads off the same starting point in parallel (e.g., one per caller of a function I'm refactoring), so that I can fan out migration work across agents simultaneously.

## Switching and orientation

15. As a developer, I want `kk switch <thread>` to point my tmux client at that thread's session, so that switching is instant.
16. As a developer, I want a tmux keybinding (e.g., `prefix+k`) that overlays the kk TUI for fast switching and spawning, so that I never have to leave my current session.
17. As a developer, I want `kk` with no arguments to open the interactive TUI, so that I can browse and act on threads visually.
18. As a developer, I want `kk ls` to list active threads with status icons, so that I can scan state at a glance from any terminal.
19. As a developer, I want `kk ls --all` to include closed threads, so that I can find archived work.
20. As a developer, I want a tmux status-line strip showing thread count and an "attention needed" indicator, so that I have ambient peripheral awareness while heads-down.
21. As a developer, I want `kk` invocations inside a thread's tmux session to know which thread I am in via env, tmux session name, or cwd, so that thread-acting commands work without specifying a target.
22. As a developer, I want `kk` invocations outside any registered repo to show threads across all registered repos, so that I get the full picture from anywhere.

## Cascade coordination

23. As a developer working in thread A, I want my edits to ancestor revisions to automatically rebase descendant thread B without breaking B's agent, so that refactoring naturally flows downstream.
24. As a developer in thread B (a child of A), I want my agent to receive a clear "your base changed, here is the diff" signal at the next tool boundary when A's revisions are amended, so that I never act on stale context.
25. As a developer, I want my thread's working copy to be rebased ONLY at agent tool boundaries or quiescence, never with the agent mid-edit, so that the agent's mental model never diverges from what is on disk.
26. As a developer, I want the cascade to handle textual conflicts by marking the thread "conflicted" and surfacing a notification, so that I resolve them deliberately instead of corrupting agent state.
27. As a developer in a child thread B that follows parent A, I want B to pick up A's new commits automatically (auto-rebased onto A's new tip), so that stacked work stays coordinated without manual rebasing.
28. As a developer, I want `kk thread detach` to break the live-follow link, so that I can pin a child thread at its current base while the parent advances independently. (v1 escape hatch if specified in `cli.md`; otherwise deferred.)
29. As a developer, I want `kk thread attach <child> --to <parent>` to re-establish a follows link, so that I can resume live coupling after a turbulent moment. (Deferred beyond v1.)
30. As a developer, I want `kk thread reparent <child> --onto <new-parent>` to move a thread under a different parent, so that I can correct stack relationships when I realize the topology was wrong. (Deferred beyond v1.)
31. As a developer, I want kk to refuse cyclic follows links, so that the coupling graph stays a DAG.
32. As a developer, I want a child thread to move onto the repo default branch and auto-detach (with notification) when its parent thread merges, so that stacked work survives the parent landing without silently following a moving target.
33. As a developer, I want kk to escalate from soft-pause to SIGINT+resume only when (i) a textual conflict cannot auto-resolve, (ii) the agent is in long pure-thinking with no upcoming tool call to intercept, or (iii) I explicitly request `kk thread interrupt`, so that the disruptive escalation is rare and predictable.
34. As a developer, I want `kk thread interrupt <thread>` as the explicit human escape hatch to hard-stop and re-frame an agent, so that I can rescue a stuck or off-track thread.

## Ambient coordinator

35. As a developer, I want to run `jj` directly inside or outside any thread's workspace and have kk react to my ops, so that kk feels additive to my normal jj workflow rather than invasive.
36. As a developer, I want kk to detect when an agent invokes `jj` via Bash and react identically to a human invocation, so that the abstraction does not leak.
37. As a developer, I want kk to surface a "your parent thread was abandoned" prompt when external `jj abandon` removes a parent's bookmark, so that I am asked how to respond instead of silently breaking.
38. As a developer, I want kk to never re-react to its own jj ops (op-attribution dedupe), so that the system cannot fall into self-triggered loops.
39. As a developer, I want kk to coalesce rapid-fire jj op storms into a single cascade per thread, so that ten quick ops do not cause ten cascades.
40. As a developer, I want kk to detect when something other than kk force-pushes a thread's branch (manual `git push --force`, etc.) and surface a "remote diverged" warning requiring explicit reconciliation, so that I never have a silent mismatch between local and remote state.

## AI auto-evolution

41. As a developer, I want kk to track ownership of revision descriptions and bookmark names, so that the v1 invariant "never overwrite human-authored prose" is enforceable even before background AI evolution ships.
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

51. As a developer, I want `kk publish` to open `$EDITOR` with an AI-pre-filled PR title and description, so that I review and edit instead of writing from scratch.
52. As a developer, I want `kk publish --no-edit` to skip the editor and use the AI draft as-is, so that low-stakes PRs are one command.
53. As a developer, I want `kk publish --no-ai` to open the editor empty, so that I can write sensitive PRs without any model involvement.
54. As a developer, I want `kk publish -m "<title>"` to set the title inline, so that I can fast-path simple cases.
55. As a developer, I want `kk publish --ready` to open the PR as ready-for-review (default is draft), so that I do not unnecessarily block reviewers on WIP.
56. As a developer, I want `kk publish` from a child thread whose parent is unpublished to automatically publish ancestors first (top-down), so that the PR stack is wired up correctly.
57. As a developer, I want each thread in a stack publish to get its own editor session top-down, so that I can review and edit each PR title/description as it is published.
58. As a developer, I want `kk publish --downstack` to publish the current thread plus all unpublished descendants, so that I can land a feature tree in one command.
59. As a developer, I want a thread's PR base to default to the parent thread's branch when stacked, otherwise to the repo's default branch (resolved from `gh repo view`), so that stack relationships translate correctly to GitHub.
60. As a developer, I want PR descriptions to be human-territory after creation (kk does not silently overwrite), with `kk publish --refresh` as an opt-in regenerator, so that my reviewer-facing prose is stable.
61. As a developer, I want a child thread's branch to be automatically rebased onto the repo default branch and force-pushed with `--force-with-lease` when its parent merges, with the PR base updated to that default branch, so that stacked PRs survive the parent landing without manual cleanup.
62. As a developer, I want `kk thread comments` to list a thread's PR review comments inside the thread context (read-only display in v1), so that I can respond with full context.

## Closing and reopening

63. As a developer, I want `kk close` to archive the current thread (kill tmux session, forget jj's workspace record, and remove the materialized workspace directory after a loss-prevention preflight plus post-stop recheck) while preserving the bookmark and revisions, so that I never lose tracked work to closure.
64. As a developer, I want `kk close` to take me back to the parent thread's session if it exists, so that I keep working without manual session-switching.
65. As a developer, I want `kk reopen <thread>` to restore an archived thread (re-create workspace, re-spawn tmux session, re-resume agent), so that I can pick up old work seamlessly.
66. As a developer, I want children of a closed thread to auto-detach with a notification, so that I am aware of the lifecycle change.
67. As a developer, I want a merged PR to auto-archive its thread with a 5-second undo grace period, so that completion cleans itself up.
68. As a developer, I want a PR closed-without-merge to surface a notification but NOT auto-archive its thread, so that I can decide whether to keep iterating.
69. As a developer, I want `kk thread destroy` as a separate, irreversible command (one-way `jj abandon`), so that I have a clear ladder from soft-close to permanent removal.
70. As a developer, I want plain `kk close` to leave any open PR untouched, with `kk close --discard-pr` as the explicit "also close the PR" option, so that GitHub-visible state is preserved unless I deliberately change it.

## Observability and notifications

71. As a developer, I want OS-native notifications when an agent hits a permission prompt, when a cascade produces a conflict, when a parent thread merges or is abandoned, and when a PR check fails, so that I do not miss important moments.
72. As a developer, I want notifications to be configurable per-event-type, so that I can tune signal vs. noise.
73. As a developer, I want CI status changes on a PR to surface as notifications but NOT auto-trigger any fix action, so that kk does not make assumptions about what to do.
74. As a developer, I want the TUI to show a tree of threads (parent-child via follows), so that I can visualize my work structure.
75. As a developer, I want `kk status` on a thread to show its branch, recent activity, agent status, and PR (if any), so that I can quickly orient.

## Configuration

76. As a developer, I want layered TOML configuration (defaults -> repo-shared-committed -> user-global -> repo-local-gitignored -> per-thread -> env -> CLI flags), so that team defaults can be committed while personal overrides stay personal.
77. As a developer, I want `kk config get|set|unset|edit|show` commands, so that I can manage config without hand-editing files.
78. As a developer, I want `kk config get <key>` to show which layer the effective value came from, so that "why is my config not taking effect" is fast to debug.
79. As a developer, I want unknown config keys to produce warnings (not errors), so that old configs survive kk upgrades.
80. As a developer, I want an opt-in `Kk-Auto: true` description trailer for transparency, so that I can audit which descriptions were AI-written.

## Pluggable UI architecture

81. As a future UI author, I want a stable gRPC contract over a unix socket exposing all daemon state and behavior, so that I can build alternative UIs (native macOS GUI, web, mobile) without modifying kkd.
82. As a future UI author, I want server-streaming events for thread state changes, so that my UI reacts in real-time without polling.
83. As a developer, I want `kk` CLI, `kk` TUI, and `kk-hook` to be pure clients of the same gRPC API (no privileged internals), so that UIs and the daemon evolve independently.

## Cross-repo

84. As a developer, I want one kkd per user, not per repo, so that I have a single mental model: one daemon, one credential surface, one set of CLI verbs, even though each `kk` TUI invocation is repo-scoped (the cross-repo view ships as `kk ls` with the `repo` column).
85. As a developer, I want `kk init` in each repo to be the per-repo opt-in, so that kkd is explicit about what it manages.
86. As a developer, I want `kk ls` outside a registered repo to list threads across ALL registered repos with a `repo` column, so that I get the full picture.
87. As a developer, I want `kk ls` inside a registered repo to default to that repo, with `--all-repos` to widen the repo scope to every registered repo and `--all` to widen the lifecycle scope to include closed threads (the two flags compose independently), so that the contextual default matches my likely intent and the two scope axes never conflate.

## Hooks and harness integration

88. As a developer, I want kk to install its Claude Code PreToolUse hook per-thread without polluting my global Claude Code config, so that my non-kk Claude Code work is unaffected. v1 does not install a Stop hook unless that hook has a separately specified job.
89. As a developer, I want kk's hooks to chain non-destructively with my user-defined hooks (kk runs first, passes through if it has nothing to inject), so that I keep my custom hooks.
90. As a developer, I want kk to revert hook config when a thread is closed, so that nothing lingers on disk.
91. As a developer with a less-capable harness (Codex without rich hook support), I want kk to gracefully degrade to SIGINT+resume for context delivery, so that the tool still works just less smoothly.
92. As a developer, I want the `kk-hook` sidecar to add imperceptible latency (target <5ms typical) to each agent tool call, so that the hook never feels in the way.

## Trust model and auditability

93. As a developer, I want destructive and global operations (close other threads, destroy, reparent across threads, register/unregister a repo) to require an `Admin` credential, so that a buggy hook or a misbehaving agent acting on its own thread cannot accidentally take destructive action elsewhere.
94. As a developer, I want each thread's `kk-hook` to be issued a `ThreadScoped` credential bound to that thread's id, so that even if a hook's behavior is wrong it cannot mutate any other thread's state.
95. As a developer, I want every parseable daemon transport attempt (accepted or rejected, gRPC or MCP) logged in an append-only audit log with caller credential when identifiable, declared scope, method, args summary, outcome, and timestamp, so that when something destructive or suspicious happens I can answer "who did it" definitively.
96. As a developer, I want `kk audit log` (Admin) and per-thread audit slices via `kk thread audit` to surface the audit trail, so that auditing is discoverable rather than buried in the daemon. (Distinct from `kk thread transcript`, which is the conversational transcript per the Thread transcript section.)
97. As a developer, I want the trust model documented honestly: kkd does not defend against an actively malicious same-UID agent that has the user's `Admin` credential, so that I do not over-rely on the capability scoping for properties it cannot deliver.

## Thread transcript

98. As a developer, I want kkd to capture each human-authored, agent-authored, and kk-authored conversational text event in a thread to a durable on-disk log bound to the jj change-id that was `@` at capture time, so that I have a recall surface separate from what was committed.
99. As a developer, I want the thread transcript to live in `<repo>/.kiki/state.db` (gitignored, never pushed), so that prose containing dead ends, tool errors, or quoted file contents stays local.
100.  As a developer, I want `kk thread transcript [<change>]` to print messages for a change, with `--search <query>` for full-text, `--range <from>..<to>` for spans, and `--recent <n>` for tail-of-thread, so that I can recall context as a human reader.
101.  As a developer, I want my agent to be able to retrieve from its own thread's log mid-task via a kiki-hosted MCP server, so that the agent can recall what the user asked or what happened earlier without me bridging it manually. (Stretch / post-v1; human `kk thread transcript` is the v1 acceptance surface.)
102.  As a developer, I do NOT want my agent to read another thread's log via MCP in v1, so that cross-thread context-sharing waits for the v2 substrate design and its safety mechanisms (causal-chain detection, depth caps, audit trail).
103.  As a developer, I want `kk reopen` to seed the resumed agent with a brief catch-up message synthesized from the log, so that a reopened thread is not a cold start.
104.  As a developer, I want auto-describe and the `kk publish` PR-drafter to NOT read from the thread transcript, so that local-only prose cannot silently leak into externally-published artifacts.
105.  As a developer, I want `kk thread destroy` to delete the thread transcript alongside the bookmark by default, with `--keep-log` as the explicit retention opt-out, so that destroy means destroy unless I say otherwise.
106.  As a developer, I want the capture path abstracted behind a `TranscriptAdapter` trait, so that future harnesses (Codex, others) can be added without touching the log schema or the read API.
107.  As a developer, I do NOT want token-streaming deltas, structured tool-call inputs and outputs, or extended-thinking blocks captured in v1, so that the log is a readable narrative rather than a verbose event stream.

## Revision and status view (`kk log`, `kk status`)

108. As a developer, I want `kk log` to be the daily-driver revision view, analogous to `jj log`, but stack-aware: my current thread's revisions render in detail and unrelated threads collapse to one-line summaries, so that I see what I am working on without drowning in everyone else's history.
109. As a developer, I want `kk log`'s default expansion to follow the entire follows-stack the current thread sits in (current + every ancestor thread up to trunk), so that stacked work reads as one coherent chain instead of forcing me to switch threads to see what I am building on.
110. As a developer, I want sibling and unrelated threads to render as collapsed one-liners showing the bookmark, an optional PR number, a status glyph, and the thread's last revision description, so that scanning is cheap and the screen stays useful.
111. As a developer, I want `kk log --no-stack` to drop to strict-current-thread expansion (ancestors collapse), so that I have a focused view when the stack is irrelevant to what I'm reading.
112. As a developer, I want `kk log --all` to include closed/archived threads as collapsed lines, so that I can find archived work without leaving the log.
113. As a developer, I want `kk log --wide` (`-w`) to switch collapsed lines to a richer format including PR draft/ready state, CI roll-up, and agent state, so that I get a one-screen status view when I want one.
114. As a developer, I want `kk log -r <revset>` to pass through to a jj revset and render results with kk decoration (PR badges, thread coloring) but disable collapse logic, so that I have one explicit escape hatch for "I know exactly what I want."
115. As a developer, I want `kk log -r` combined with `--no-stack`/`--all`/`--wide` to error rather than silently ignore the conflicting flag, so that the override semantics stay unambiguous.
116. As a developer, I want `kk log` invoked when no thread can be resolved from env/tmux/cwd to render the trunk in detail with all repo threads as collapsed lines, plus a header announcing the degraded state, so that the command is always useful from anywhere in a registered repo.
117. As a developer, I want `kk log` invoked outside any registered repo to error with a pointer to `kk ls` (the cross-repo view), so that `kk log` and `kk ls` stay distinct concepts.
118. As a developer, I want `kk status` to render a small kk-shaped header (thread, PR, CI, agent state, follows summary) followed by literal `jj st` output for the working copy, so that I get the thread context plus the file listing I already know how to read.
119. As a developer, I want `kk status --diff` (`-p`) to append the working-copy patch (and `--diff --stat` for diffstat), so that I can review changes without dropping to `jj diff`.
120. As a developer, I want `kk status --no-jj` to suppress the working-copy section and emit only the kk header, so that I can script against the thread context and so the sidebar can reuse the same renderer cheaply.
121. As a developer, I want the cascade-state indicator in `kk status` to be three-valued (`in sync` / `pending` / `conflicted`) with no count, so that the most common signal is glanceable and the noisy edge ("how many cascades behind") doesn't become a recurring distraction.
122. As a developer, I want `kk` to remain pure porcelain: `kk log` and `kk status` adopt no jj flags beyond `-r <revset>`, so that anything jj can do, I do via `jj` directly without learning a near-mirror surface that risks subtle drift.

## Interactive overlay TUI (`prefix+k` / `kk`)

123. As a developer, I want the overlay TUI to be a left sidebar plus a right-hand content pane, where the sidebar shows two sections: a Stack section (the same stack-aware log as `kk log` with the current thread's status inlined under its bookmark line) on top and an Activity section (the same threads, flat-listed by most-recent agent event) below it, so that one panel answers both "where am I in the work?" and "who needs me?" without me leaving navigation.
124. As a developer, I want the navigation cursor to move on log lines (j/k or arrows) and `enter` to switch to the cursored thread (dismissing the overlay), so that the most common action is the cheapest keystroke.
125. As a developer, I want `space` to preview the cursored thread in the right pane (transcript tail / diff / comments toggleable via `t`/`d`/`c`) without changing my active thread, so that I can peek before committing to a switch.
126. As a developer, I want destructive and creative verbs (`n` spawn, `N` spawn-as-child-of-cursored, `p` publish, `x` close, `i` interrupt) to be available only in the overlay TUI, not in the persistent sidebar pane, so that a stray keypress in a passive sidebar can't take action. (`c` is reserved for the PR-comments preview in story 125; close binds to `x` to avoid the collision.)
127. As a developer, I want destructive overlay verbs (`x`, `i`) to open a confirmation modal rather than firing immediately, so that fat-fingering doesn't cost me work.
128. As a developer, I want lowercase `t` in the overlay to surface a transcript-tail preview in the right pane (alongside `d` diff and `c` PR comments) and shift-`T` to escalate to a full-screen `kk thread transcript` reader for the cursored thread, so that the cheap glance and the deep drill-down sit on the same letter at two different intensities.
129. As a developer, I want `?` to surface a help overlay listing the active keymap, so that the action set is discoverable rather than memorized.

## Persistent sidebar pane (opt-in)

130. As a developer, I want to opt into a persistent sidebar tmux pane (left, fixed-width) on every thread session via `[ui] persistent_sidebar = true` in my user-global config, so that I have continuous peripheral awareness of log + thread status without invoking the overlay.
131. As a developer, I want `kk new <name> --sidebar` / `--no-sidebar` to override my default per thread, so that one-off threads can opt in or out without changing global config.
132. As a developer, I want the sidebar pane to render the same Stack + Activity content the overlay's sidebar does, so that there is one mental model for the sidebar regardless of where it lives.
133. As a developer, I want the sidebar pane restricted to navigation-only keys (j/k/arrows/tab/enter/q/?, plus mouse click-to-focus and scroll). Destructive/creative verbs are not bound, so that accidental focus on the sidebar pane (a real tmux focus accident) cannot mutate state.
134. As a developer, I want the sidebar pane to spawn at thread birth (during `kk new`'s atomic spawn), and to be re-ensured idempotently at every `kk switch`/`kk reopen` to that thread, so that the pane is reliably present without kk policing tmux mid-session.
135. As a developer, I want kk to NOT auto-respawn the sidebar pane within a live session if I deliberately killed it (`prefix+x`), so that maximizing the agent pane is honored until I detach and reattach.
136. As a developer, I want kk to skip spawning the sidebar pane when my terminal is narrower than `[ui] sidebar_min_terminal_cols` (default 100) and log a warning at `kk new` time, so that the sidebar never renders broken on a narrow terminal.
137. As a developer, I want toggling `[ui] persistent_sidebar` after threads exist to take effect at next `kk new`/`kk reopen` (not retroactively reshape live sessions), with a config-set warning making the lag visible, so that I'm not surprised when an existing thread stays unchanged.

## Stated non-goals

138. As a developer, I do NOT want kk to manage or cap my agent's resource consumption (CPU, RAM, tokens), so that those decisions stay in my hands.
139. As a developer, I do NOT want kk to refuse `jj`, `gh`, or tmux operations I run directly, so that kk remains additive infrastructure.
140. As a developer, I do NOT want kk to surface CPU/RSS for agent processes; that is what Activity Monitor and htop are for, and duplicating them poorly clutters kk.
141. As a developer, I do NOT expect per-thread workspace isolation to act as a security boundary (filesystem ACLs, sandboxing) in v1; that is a future-version concern. v1 promises only cooperative separation.
