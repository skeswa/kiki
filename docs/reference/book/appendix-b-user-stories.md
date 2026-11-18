# Appendix B: User Stories

A [user story](https://en.wikipedia.org/wiki/User_story) is a short statement of what a user wants and why. The stories here are part of the book's contract with the implementer. They preserve the use cases that gave the normative (binding) chapters their shape:

- what the engineer is trying to do;
- what friction kiki is meant to remove;
- where the v1 boundary was deliberately drawn.

Read these before the [invariants](02-invariants.md). A story and a normative chapter may appear to pull in different directions. When they do, the invariant and the behavioral chapter govern the implementation. The story still matters. It names the user need that the implementation must satisfy without violating the stricter rule.

Each story is one short sentence. The bullets under a story are part of that story: they carry its conditions and details. A note such as "(v1.x)" or "(Out of v1.)" says when the story ships; [Orientation](01-orientation.md) holds the full scope list.

## Setup and lifecycle

1. As a developer, I want to install kiki as a single distribution, so that getting started is one command.
   - The distribution carries `kk` (the command-line tool), [`kkd`](appendix-a-glossary.md#kkd) (the background [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>)), and [`kk-hook`](appendix-a-glossary.md#kk-hook) (the helper that agent hooks call).
2. As a developer, I want to run `kk init` in a git+[jj](https://docs.jj-vcs.dev/latest/) repository to opt that repo into kiki management, so that I am explicit about which repos kkd watches.
3. As a developer, I want kk to verify only local coordination prerequisites at `kk init`, so that a missing GitHub login does not block local work.
   - The notable local check is that jj is initialized.
   - [Harness](appendix-a-glossary.md#harness) binaries (the agent programs, such as Claude Code) are checked at `kk new`.
   - [`gh`](https://cli.github.com/) and GitHub authentication are checked lazily at `kk publish`, or explicitly via `kk doctor --github`.
4. As a developer, I want kkd to start automatically the first time I invoke `kk`, so that I never have to think about daemon lifecycle.
5. As a developer, I want kkd to recover from crashes by reading its [sqlite](https://www.sqlite.org/) state on restart, so that my [threads](appendix-a-glossary.md#thread) survive daemon issues.
6. As a developer, I want `kk` to bootstrap `kkd` as a [launchd](https://en.wikipedia.org/wiki/Launchd) user agent rather than as a child of my terminal, so that `kkd` comes back after a reboot and quitting my terminal application does not take my agents with it.
   - On Linux, the equivalent is a [systemd](https://en.wikipedia.org/wiki/Systemd) user unit.
   - `kkd` starts the terminal server from there.
7. As a developer, I want `kk init` to NOT auto-spawn a starter thread, so that I am explicit about when threads are created.

## Thread creation

8. As a developer, I want `kk new <name>` to spawn a [thread](appendix-a-glossary.md#thread), so that I start a new line of work instantly.
   - The thread has its own [jj workspace](appendix-a-glossary.md#workspace) (its own copy of the files).
   - It has its own [terminal group](appendix-a-glossary.md#terminal-group) (its own set of terminal panes).
   - It has its own managed agent, which is [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) by default.
9. As a developer, I want `kk new` (no name) to derive a placeholder name from my initial prompt, so that I do not have to commit to a name upfront. (v1.x.)
   - The name argument of `kk new [<name>]` is optional. In the acceptance slice, a thread created with a prompt and no name is called `unnamed-<short-hex>`.
   - Deriving the name from the prompt is the v1.x part.
10. As a developer, I want `kk new <name> --follows <parent>` to create a child thread coupled to a parent, so that I can stack work on top of a work-in-progress feature.
    - This coupling is the [follows](appendix-a-glossary.md#follows) link.
11. As a developer, I want `kk new <name> --no-follow` to create a snapshot fork, so that I can branch off the current state without inheriting future changes.
    - A snapshot fork has no live coupling.
    - This matters when the contextual default would otherwise follow the current thread.
12. As a developer, I want `kk new --harness <name>` to override the default agent [harness](appendix-a-glossary.md#harness) for a single thread, so that I can pick the right one per task.
    - For example, Claude Code for one thread and [Codex](https://github.com/openai/codex) for its sibling.
    - (v1: `claude-code` and `codex` are accepted. Any other harness name errors with `"unsupported harness in v1"` until further adapters are added.)
13. As a developer, I want each thread to live in its own jj workspace, so that parallel agentic work stays in its own lane.
    - Agents in different threads do not accidentally interfere with each other's files in the course of normal cooperative work.
    - (This is a cooperative isolation property, not filesystem access control. See [Trust model](#trust-model-and-auditability): same-UID processes, meaning processes that run as the same user account, can still reach sibling workspaces.)
14. As a developer, I want to spawn N sibling threads off the same starting point in parallel, so that I can fan out migration work across agents simultaneously.
    - For example, one thread per caller of a function I'm refactoring.

    14a. As a developer, I want the active workspace's `@` to be the thread's [live head](appendix-a-glossary.md#live-head), so that ordinary `jj new` behavior cannot silently leave kiki following or publishing the wrong commit.
    - `@` is jj's name for the [working-copy commit](https://docs.jj-vcs.dev/latest/glossary/).
    - The thread's [bookmark](appendix-a-glossary.md#bookmark) remains an explicit checkpoint/publication [projection](appendix-a-glossary.md#projection).

    14b. As a developer, I want thread creation to recover durably from a daemon crash at any external step, so that “atomic spawn” does not depend on impossible cross-system rollback.
    - Kiki starts the harness only after credentials and isolated hook configuration are ready.

## Switching and orientation

15. As a developer, I want `kk switch <thread>` to move my own [Herdr](appendix-a-glossary.md#herdr) client to that thread's agent pane, so that switching is instant.
    - The switch does not mutate any terminal or daemon state.
    - It never restarts, recreates, or repairs anything as a side effect.

    15a. As a developer, I want `kk attach [<thread>]` to open a [Herdr client](appendix-a-glossary.md#herdr-client) on kiki's [dedicated terminal server](appendix-a-glossary.md#dedicated-herdr-server), so that any terminal can become a view onto my threads without touching the Herdr server I use for other work.
    - It asks kkd to make sure the server is running.
    - It then connects to kiki's named session with kiki's generated configuration.
    - It never starts a server itself.

    15b. As a developer with several clients attached, I want `kk switch` to move only the client that invoked it, so that nobody's view moves unless they or I asked for exactly that.
    - Examples of several clients: two monitors, or a second person looking on.
    - When the terminal server cannot target one client, `kk switch` refuses and names the missing required [`client_targeted_focus`](appendix-a-glossary.md#client-targeted-focus) extension.
    - `kk switch --all-clients` is offered as a separately named operation.

    15c. As a developer, I want a `kk switch` that has no identifiable viewer to move no one and say so, so that automation cannot yank my view.
    - Examples: a `kk switch` run by an agent, a script, or a pane nobody is looking at.

16. As a developer, I want a Herdr keybinding that opens the kk [overlay](appendix-a-glossary.md#overlay-tui) as a popup, so that I never have to leave my current view. (v1.x, with the overlay.)
    - Kiki generates the keybinding in its own Herdr configuration.
    - The overlay is for fast switching and spawning.
17. As a developer, I want `kk` with no arguments to open the interactive [TUI](https://en.wikipedia.org/wiki/Text-based_user_interface) (text-based user interface), so that I can browse and act on threads visually. (v1.x.)
    - Until the overlay ships, and whenever no overlay is available, bare `kk` prints the `kk ls` listing.
18. As a developer, I want `kk ls` to list active and repair-relevant operational threads, so that creating, failed, closing, or projection-diverged work cannot disappear from the default view.
    - Each row carries a [lifecycle](appendix-a-glossary.md#thread-lifecycle-states) label.
    - The labels remain distinct without color.
19. As a developer, I want `kk ls --all` to include closed threads, so that I can find archived work.
20. As a developer, I want Herdr's native sidebar to list every thread's [terminal group](appendix-a-glossary.md#terminal-group) across my registered repos, so that I have ambient peripheral awareness while heads-down.
    - Kiki labels each entry with the repo, the thread, and a short tag.
    - In v1.x, each entry also carries lifecycle, cascade, agent, and follows tokens that are distinguishable without color.
    - I understand that the sidebar is Herdr's and I can hide it.
    - I understand that its entries are a one-way [projection](appendix-a-glossary.md#herdr-sidebar-projection) that kiki republishes and never reads back.
    - `kk ls` is the truthful list.
21. As a developer, I want `kk` invocations inside a thread's terminal group to know which thread I am in, so that thread-acting commands work without specifying a target and a pane on some other Herdr server is never mistaken for a thread.
    - Kiki looks in this order:
      1. an explicit target;
      2. then `KIKI_THREAD_ID` on the panes kiki provisions;
      3. then the Herdr pane identity of a pane I split myself;
      4. then cwd (the [working directory](https://en.wikipedia.org/wiki/Working_directory)).
22. As a developer, I want `kk` invocations outside any registered repo to show threads across all registered repos, so that I get the full picture from anywhere.

## Cascade coordination

A cascade is how a change in a parent [thread](appendix-a-glossary.md#thread) reaches the threads that [follow](appendix-a-glossary.md#follows) it. See [cascade reconciliation](appendix-a-glossary.md#cascade-reconciliation).

23. As a developer working in thread A, I want jj's native evolution of descendant thread B to be [materialized](appendix-a-glossary.md#materialization) safely for B's agent, so that refactoring naturally flows downstream.
    - Materializing means updating B's files on disk to match what jj already recorded.
    - Kiki does not redundantly rebase work jj already evolved.
24. As a developer in thread B (a child of A), I want my agent to receive a clear "your base changed, here is the diff" signal when A's revisions are amended, so that B's files and agent context move together.
    - The signal arrives at the next tool boundary.
    - The repository may evolve immediately; only B's files and agent context wait for that boundary.
25. As a developer, I want kiki to materialize evolved state or perform an explicit follows rebase ONLY at agent tool boundaries or [quiescence](appendix-a-glossary.md#agent-quiescence), so that the agent's mental model never diverges from what is on disk.
    - Kiki never does either while the managed agent is mid-edit.
    - I understand that a direct human `jj` command in a stale child workspace is an explicit escape hatch. It may materialize the workspace earlier.
    - At the next boundary kiki must probe the actual files and recover unsnapshotted edits, rather than assume the op log tells the whole story.
26. As a developer, I want the cascade to handle textual conflicts by marking the thread "conflicted" and surfacing a notification, so that I resolve them deliberately instead of corrupting agent state.
27. As a developer in a child thread B that follows parent A, I want B to pick up A's newly added [live-head](appendix-a-glossary.md#live-head) commits automatically, so that stacked work stays coordinated.
    - B picks them up through an explicit boundary-safe [`ParentAdvance`](appendix-a-glossary.md#parentadvance) reconciliation.
    - Kiki does not assume that A's [bookmark](appendix-a-glossary.md#bookmark) automatically followed `jj new`.
28. As a developer, I want `kk thread detach` to run its safety steps first and only then break the live-follow link, so that detach cannot silently discard a parent advance.
    - The steps, in order:
      1. synchronously catch up the operation [DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph) (the graph of jj operations);
      2. surface any parent transition that watcher lag had not recorded yet;
      3. checkpoint my exact child head;
      4. only then break the live-follow link.
    - `kk thread detach [<thread>]` acts on the contextual thread when no target is given.
    - Pending parent work is discarded only with `--discard-pending`, which needs approval.
    - This is the v1 graph-surgery escape hatch. `kk thread attach` and `kk thread reparent` are out of v1.
29. As a developer, I want `kk thread attach <child> --to <parent>` to re-establish a follows link, so that I can resume live coupling after a turbulent moment. (Out of v1.)
30. As a developer, I want `kk thread reparent <child> --onto <new-parent>` to move a thread under a different parent, so that I can correct stack relationships when I realize the topology was wrong. (Out of v1.)
31. As a developer, I want kk to refuse cyclic follows links, so that the coupling graph stays a DAG (a graph with no loops).
32. As a developer, I want the v1.x GitHub integration to handle a merged parent in three ordered steps, so that stacked work survives the parent landing without silently reusing an older publish approval.
    1. Move the child locally onto the exact merged default-branch commit.
    2. Then present a one-shot-approved remote force-push/PR-base plan.
    3. Detach only after local and remote state agree.
33. As a developer, I want kk to escalate from [soft-pause](appendix-a-glossary.md#soft-pause) to SIGINT+resume only when the safety contract requires it, so that disruption is rare but never preferred over edit or delivery safety.
    - SIGINT is the interrupt [signal](<https://en.wikipedia.org/wiki/Signal_(IPC)>); this is the [hard escalation](appendix-a-glossary.md#hard-escalation).
    - The cases that require it are:
      - dirty or indeterminate files before mutation;
      - divergent successors;
      - ambiguous topology;
      - an unprovable [delivery barrier](appendix-a-glossary.md#delivery-barrier);
      - my explicit v1.x `kk thread interrupt`.
34. As a developer, I want `kk thread interrupt [<thread>]` as the explicit human escape hatch to hard-stop and re-frame an agent, so that I can rescue a stuck or off-track thread. (v1.x.)
    - Without a target, it acts on the contextual thread.

    34a. As a developer, I want kiki to block every tool call in a dispatched [tool batch](appendix-a-glossary.md#tool-batch) when one call triggers reconciliation, so that a sibling call from the same batch cannot observe new files before the agent receives the explanation.
    - Kiki acknowledges delivery only after that batch closes and a later [model turn](appendix-a-glossary.md#model-turn) begins.
    - (Claude Code's parallel batch is the hard case. Codex's proven-serial dispatch makes each batch a single call.)

    34b. As a developer, I want v1 managed sessions to reserve the pre-tool boundary exclusively for kiki, so that the [safe boundary](appendix-a-glossary.md#safe-boundary) does not depend on hook configuration order.
    - This applies to Claude Code and Codex alike.
    - Kiki gives a clear startup diagnostic when effective user hooks would race the boundary.

## Ambient coordinator

Kiki is an [ambient coordinator](appendix-a-glossary.md#ambient-coordinator): it watches and reacts to the tools you already use, and does not stand in front of them.

35. As a developer, I want to run `jj` directly inside or outside any thread's workspace and have kk react to my ops, so that kk feels additive to my normal jj workflow rather than invasive.
    - An "op" is a jj [operation](https://docs.jj-vcs.dev/latest/operation-log/): one recorded change to the repository.
36. As a developer, I want kk to detect when an agent invokes `jj` via Bash and react identically to a human invocation, so that the abstraction does not leak.
37. As a developer, I want kk to tell two external events on a parent apart, so that neither event silently changes my follows base.
    - Deletion or movement of a parent's checkpoint [bookmark](appendix-a-glossary.md#bookmark) is bookmark drift. It enters [projection](appendix-a-glossary.md#projection-divergence) repair, where `kk repair` offers the bookmark plans named in story 40a.
    - External `jj abandon` of the parent's [live head](appendix-a-glossary.md#live-head) or owned revisions is ancestry destruction. It stops as [topology divergence](appendix-a-glossary.md#topologydiverged).
38. As a developer, I want kk to never re-react to its own jj ops (op-attribution dedupe), so that the system cannot fall into self-triggered loops.
39. As a developer, I want kk to follow jj's operation history in three specific ways, so that op storms stay quiet without losing a branch of the operation DAG.
    - It traverses jj's complete operation-head [frontier](appendix-a-glossary.md#operation-frontier).
    - It preserves incomparable concurrent operations instead of ordering them by timestamp.
    - It coalesces compatible rapid-fire triggers into one cascade per thread.
40. As a developer, I want kk to detect when something other than kk force-pushes a thread's branch, so that I never have a silent mismatch between local and remote state.
    - Examples: a manual `git push --force`, etc.
    - Kk surfaces a "remote diverged" warning that requires explicit reconciliation.

    40a. As a developer, I want kiki to follow my checkpoint bookmark through jj's own rewrite successors and detect projection failures, so that an ordinary edit never sends a thread to repair and an unrelated bookmark or terminal problem does not silently freeze follows coordination.
    - Kiki detects each of these:
      - missing, externally moved, or conflicted bookmarks;
      - missing jj workspace records;
      - path mismatches;
      - missing [terminal groups](appendix-a-glossary.md#terminal-group) or agents;
      - orphaned processes.
    - It repairs only provably unambiguous cases automatically.
    - Otherwise it guides me through `kk repair`, which names one plan per problem.
    - For a bookmark problem there are four plans:
      - [`restore-bookmark`](appendix-a-glossary.md#restore-bookmark) puts the bookmark back on the target kiki expects. It needs no approval in the thread's own context, and it is offered only while that target is visible.
      - [`adopt-bookmark`](appendix-a-glossary.md#adopt-bookmark) accepts where the bookmark was moved to, when that commit is my live head or on my thread's own chain.
      - [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target) lets me pick the live head or a commit on my thread's own chain. It is the way out whenever the expected target is hidden.
      - [`unhide-checkpoint`](appendix-a-glossary.md#unhide-checkpoint) makes an abandoned checkpoint commit visible again.
    - The last three need a one-shot approval. Kiki never places the bookmark on a commit outside my thread's own chain.
    - If jj's operation history itself was rewritten, the repo-level [`reanchor-history`](appendix-a-glossary.md#reanchor-history) plan (`kk repair --repo`) re-anchors every affected thread under one approval.
    - For a workspace problem the plans are [`recreate-workspace`](appendix-a-glossary.md#recreate-workspace) (the directory is missing), [`reattach-workspace`](appendix-a-glossary.md#reattach-workspace) (jj's workspace record is missing), and [`repoint-workspace`](appendix-a-glossary.md#repoint-workspace) (the path does not match).
    - It continues safe live-head observation when the workspace itself is still uniquely identified.

    40b. As a developer, I want kiki to look for leftover processes before it starts a replacement agent, so that two writers never share a workspace.
    - It looks for processes it recorded that outlived their pane, terminal group, or terminal server.
    - It looks for tool processes that a dead harness left under its launcher.
    - Such a process is an [orphan](appendix-a-glossary.md#orphan), and the issue it raises is [`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess).
    - While one survives, kiki blocks replacement, materialization, and deletion for that thread.
    - It offers the [`terminate-orphans`](appendix-a-glossary.md#terminate-orphans) plan, which terminates exactly those processes with verified exit under a one-shot approval. Otherwise it leaves the thread blocked.

    40c. As a developer, I want a process kiki did not start that merely holds my workspace never to block my active thread, so that kiki never signals a stranger's process on a guess and never deletes under one unknowingly.
    - An editor is an example of such a [holder](appendix-a-glossary.md#holder).
    - The process matters only when kiki is about to delete that workspace.
    - There, I want the files kept unless I approved a plan that names that exact process as [accepted](appendix-a-glossary.md#accepted-holder).
    - I want to be told its pid ([process id](https://en.wikipedia.org/wiki/Process_identifier)), its command line, and what clears it.

## AI auto-evolution

41. As a developer, I want kk to track ownership of revision descriptions and [bookmark](appendix-a-glossary.md#bookmark) names before background AI evolution writes either surface, so that the invariant "never overwrite human-authored prose" is proven with the v1.x metadata feature.
    - The proof ships with that feature. It does not burden the initial coordination slice.
42. As a developer, I want kk to eventually auto-evolve bookmark names and revision descriptions as work takes shape, so that my history narrates itself. (v1.x execution.)
43. As a developer, I want [auto-rename](appendix-a-glossary.md#auto-rename) and [auto-describe](appendix-a-glossary.md#auto-describe) to fire at two kinds of moment, so that the AI loop never races my agent. (v1.x execution.)
    - They fire when the thread's agent has been [quiescent](appendix-a-glossary.md#agent-quiescence) (idle) for a configurable window,
    - OR after specific events (`jj split`, `jj squash`).
44. As a developer, I want kk to NEVER silently overwrite a description I or my agent typed, so that my prose and intent stay intact and kk remains trustworthy.
45. As a developer, I want kk to NEVER re-rename a bookmark I renamed manually, so that my deliberate naming sticks for the rest of the thread's life.
46. As a developer, I want `kk thread describe --refresh` to opt a revision back into auto-describe, so that I have an explicit escape hatch when I want kiki to take over again. (v1.x, with auto-describe.)
47. As a developer, I want auto-describe to use a fast, cheap model (e.g., Haiku-class), so that auto-AI cost stays modest.
48. As a developer, I want auto-describe to discard its model output if the input state changed during model latency, so that descriptions never describe stale content.
    - Kiki checks this with an input-hash recheck: it [hashes](https://en.wikipedia.org/wiki/Cryptographic_hash_function) the input again and compares.
49. As a developer, I want auto-rename's prompt to include sibling bookmark names, so that I never end up with two threads colliding on the same name.
    - With those names in the prompt, the model picks a distinct slug.
50. As a developer, I want a squash that combines a kk-owned revision with a human-owned one to mark the squashed result as human-owned, so that ownership defaults to the more conservative side.

## Publishing

Publishing means opening a [pull request](https://docs.github.com/en/pull-requests) (PR) on GitHub for a [thread](appendix-a-glossary.md#thread).

51. As a developer, I want the first v1.x `kk publish` flow to open `$EDITOR` with prepared text, so that manual publishing does not wait for or silently invoke a model.
    - The text is derived only from explicit command input and non-transcript metadata.
    - Opt-in AI prefill is added later, alongside the metadata execution loop.
52. As a developer, I want `kk publish --no-edit` to skip the editor, so that low-stakes PRs are one command without changing the egress boundary.
    - It uses the exact generated non-transcript draft shown in the approved plan.
    - That draft is deterministic in the first release, or AI-assisted after that feature ships.
53. As a developer, once AI publishing assistance ships, I want `kk publish --no-ai` to force the manual non-model drafting path, so that I can write sensitive PRs without model involvement.
    - The flag is not part of the first manual publishing release.
54. As a developer, I want `kk publish -m "<title>"` to set the title inline, so that I can fast-path simple cases.
55. As a developer, I want `kk publish --ready` to open the PR as ready-for-review, so that I do not unnecessarily block reviewers on WIP.
    - The default is draft.
56. As a developer, I want `kk publish` from a child thread whose parent is unpublished to automatically publish ancestors first (top-down), so that the PR stack is wired up correctly.
57. As a developer, I want each thread in a stack publish to get its own editor session top-down, so that I can review and edit each PR title/description as it is published.
58. As a developer, I want `kk publish --downstack` to publish the current thread plus all unpublished descendants, so that I can land a feature tree in one command.
59. As a developer, I want a thread's PR base to have a sensible default, so that stack relationships translate correctly to GitHub.
    - When the thread is stacked, the default is the parent thread's branch.
    - Otherwise, the default is the repo's default branch, resolved from `gh repo view`.
60. As a developer, I want PR descriptions to be human-territory after creation, so that my reviewer-facing prose is stable.
    - Kk does not silently overwrite them.
    - `kk publish --refresh` is an opt-in regenerator.
61. As a developer, I want a child thread to be reconciled locally onto the exact merged default-branch commit when its parent merges, so that stacked PRs survive landing and kiki never changes the remote before that exact change is approved.
    - The child then receives an exact one-shot approval plan for `--force-with-lease` and the PR-base update.
    - The plan comes before those remote mutations occur.
62. As a developer, I want the v1.x `kk thread comments` surface to list a thread's PR review comments read-only inside the thread context, so that I can respond with full context.

## Closing and reopening

63. As a developer, I want `kk close` to refuse while my agent is working and otherwise to close in checked steps, so that a failed or drifted close never leaves a dead thread labeled Active or reuses stale approval.
    - The steps, in order:
      1. Freeze and prove quiescent every process in the thread's [terminal group](appendix-a-glossary.md#terminal-group): the agent, the shell, and any panes or tabs I added.
      2. Rerun loss-prevention and [operation-frontier](appendix-a-glossary.md#operation-frontier) checks against the exact approved plan.
      3. If safety or the approval fingerprint changed, resume the original process states.
      4. Otherwise, checkpoint the exact head and reconcile/detach children.
      5. After that, terminate the frozen processes, close the terminal group, forget the workspace, and remove the directory.
    - I want the approval card to list the processes it found.
    - I want the card to say plainly that it covers every process in the listed terminal containers at freeze time.
    - When an automation policy rule approves the close and no card is drawn, I want the plan that `kk` prints to carry the same list and the same statement (story 149).

    63a. As a developer, I want `kk close` to terminate the frozen processes itself and verify each exit by OS process identity, so that a background job that ignored the hangup can never be writing into a directory kiki is deleting.
    - It treats the terminal server's "closed" reply as cleanup and never as proof.
    - It forgets and deletes the [jj workspace](appendix-a-glossary.md#workspace) only after that [verified exit](appendix-a-glossary.md#verified-exit) and a final filesystem recheck.
    - If exit cannot be verified, I want the files kept and the failure reported.

64. As a developer, I want a close to leave each client's view in the right place, so that I keep working without manual switching and nobody else's view is moved on my behalf.
    - A `kk close` run from outside the closed thread moves my own client to the parent thread, when that thread is active with a bound terminal group.
    - A `kk close` typed inside the thread ends with it and leaves the result in `kk ls`.
    - Otherwise, Herdr places any client that was showing the closed terminal group.
65. As a developer, I want `kk reopen <thread>` to restore an archived thread through a restart-recoverable [journal](appendix-a-glossary.md#lifecycle-journal), so that a crash during workspace, credential, terminal-group, or harness recreation leaves a recorded state that supports repair.
    - The launcher must report ready before the thread becomes Active.

    65a. As a developer whose machine rebooted or whose terminal server restarted, I want the layouts Herdr restores to be treated as [remnant containers](appendix-a-glossary.md#remnant-container), so that a pane that merely reappeared is never mistaken for a managed agent.
    - No agent is resumed by the terminal runtime.
    - No thread is reported Active.
    - No restored container is ever reused.
    - Each affected thread shows [`TerminalMissing`](appendix-a-glossary.md#terminalmissing) until I run `kk repair`.
    - `kk repair` offers two plans:
      - [`restart-terminal`](appendix-a-glossary.md#restart-terminal) restarts the agent in a fresh terminal group with a fresh credential, launch settings, gate, and ready handshake; or
      - [`close-without-terminal`](appendix-a-glossary.md#close-without-terminal) closes the thread without one.
    - In both cases it lists and closes the restored shells itself under my approval. It does not ask me to clean them up first.

    65b. As a developer whose agent crashed while its pane is still there, I want the thread to stay Active with the agent shown as blocked, so that a harness crash is a small recovery and not a terminal repair.
    - `kk repair`'s [`restart-agent`](appendix-a-glossary.md#restart-agent) plan starts a fresh [incarnation](appendix-a-glossary.md#incarnation) (a new agent process) in the same pane without an approval prompt.
    - It does so once nothing the dead agent started is still running.

    65c. As a developer whose `kk new` or `kk reopen` failed after the agent could have run or the workspace changed, I want kiki to stop with everything in place, so that automatic rollback never deletes work.
    - Kiki offers cleanup as an approved [repair plan](appendix-a-glossary.md#repair-plan) with the same safeguards as close: [`cleanup-failed-create`](appendix-a-glossary.md#cleanup-failed-create) after a failed `kk new`, and [`cleanup-failed-reopen`](appendix-a-glossary.md#cleanup-failed-reopen) after a failed `kk reopen`.
    - A close or destroy that failed partway is finished with [`retry-close`](appendix-a-glossary.md#retry-close) or [`retry-destroy`](appendix-a-glossary.md#retry-destroy).

66. As a developer, I want parent close to settle every child before the parent's terminal group closes, so that watcher lag or a failed detach cannot erase a parent advance or leave an unresumable parent.
    - The steps, in order:
      1. synchronously refresh every child edge;
      2. require a choice for any newly discovered transition;
      3. while the parent is frozen, checkpoint and detach each child;
      4. only then close the parent's terminal group.
67. As a developer, I want a merged PR to propose closing its thread and never to close anything by itself, so that completion is one keypress away without kiki ever stopping processes or deleting a workspace unasked.
    - The proposal is a notification with an action that opens the ordinary close approval card.
    - Merge polling, notification, state updates, and the close proposal all ship with the v1.x GitHub integration rather than the coordination [acceptance slice](appendix-a-glossary.md#acceptance-slice).
68. As a developer, I want a PR closed-without-merge to surface a notification but NOT auto-archive its thread, so that I can decide whether to keep iterating.
69. As a developer, I want `kk thread destroy` to preserve jj revisions by default, so that ordinary cleanup never implies history loss or expands an inferred `jj abandon` revset.
    - It deletes the local thread [projections](appendix-a-glossary.md#projection) through a method-bound journal.
    - Abandoning revisions requires a separate `--abandon-revisions` approval.
    - That approval names an exact validated chain with no registered or foreign descendants.
70. As a developer, I want plain `kk close` to leave any open PR untouched, so that GitHub-visible state is preserved unless I deliberately change it.
    - `kk close --discard-pr` is the explicit "also close the PR" option.

## Observability and notifications

71. As a developer, I want [acceptance-slice](appendix-a-glossary.md#acceptance-slice) attention notifications for the events the coordination core can raise by itself, so that unavailable remote polling is not implied by the core coordinator.
    - The events are: a blocked or crashed agent, a conflicted cascade, an exhausted delivery, a followed parent abandoned, a failed lifecycle operation, and a [projection issue](appendix-a-glossary.md#projection-issue). This is the list in [Orientation](01-orientation.md).
    - A permission prompt is one way an agent becomes blocked. Detecting it depends on the harness adapter's `attention_events` proof. For a harness without that proof, permission-prompt detection is v1.x; a crash still shows as blocked.
    - An agent reporting its goal complete is also in the acceptance slice, and it is quieter: by default (`soft`) it is a status mark plus an overlay toast, with no OS notification.
    - Merge and PR-check notifications are added by the v1.x GitHub integration.
72. As a developer, I want notifications to be configurable per-event-type, so that I can tune signal vs. noise.
    - Each event has a level: `loud`, `soft`, or `silent`. [Configuration](11-configuration.md) lists the event keys and their defaults.
73. As a developer, I want [CI](https://en.wikipedia.org/wiki/Continuous_integration) status changes on a PR to surface as notifications but NOT auto-trigger any fix action, so that kk does not make assumptions about what to do.
74. As a developer, I want the TUI to show a tree of threads (parent-child via [follows](appendix-a-glossary.md#follows)), so that I can visualize my work structure. (v1.x, with the overlay.)
    - In the acceptance slice, `kk log` shows the same tree as text.
75. As a developer, I want `kk status` to distinguish the live workspace head from its [bookmark](appendix-a-glossary.md#bookmark) checkpoint, so that ordinary bookmark lag is never mistaken for lost work.
    - It shows where kiki last [placed the checkpoint](appendix-a-glossary.md#checkpoint-placement).
    - It shows the [target it now expects](appendix-a-glossary.md#expected-bookmark-target) after jj's own rewrites.
    - It shows whether the head is `current`, `behind`, `ahead`, or `diverged` relative to that target. This is the [checkpoint relationship](appendix-a-glossary.md#checkpoint-relationship).
    - A head that is only an empty commit on top of the checkpoint reads `current`. That is the case right after `jj commit` or `kk reopen`.
    - v1.x may add PR state.

## Configuration

76. As a developer, I want layered [TOML](https://toml.io/) configuration, so that team defaults can be committed while personal overrides stay personal.
    - The layers are: defaults -> repo-shared-committed -> user-global -> repo-local (kept outside the repository) -> per-thread -> env -> CLI flags.
    - (The full set of layers is v1.x. The acceptance slice ships only the minimal configuration that [Orientation](01-orientation.md) lists.)
77. As a developer, I want `kk config get|set|unset|edit|show` commands, so that I can manage config without hand-editing files.
    - (`get` and `show` are in the acceptance slice. `set`, `unset`, and `edit` are v1.x.)
    - `kk config show` prints the merged configuration with the layer each value came from.
78. As a developer, I want `kk config get <key>` to show which layer the effective value came from, so that "why is my config not taking effect" is fast to debug.
79. As a developer, I want unknown config keys to produce warnings (not errors), so that old configs survive kk upgrades.
80. As a developer, I want an opt-in `Kk-Auto: true` description trailer for transparency, so that I can audit which descriptions were AI-written. (v1.x, with auto-describe.)

## Pluggable UI architecture

81. As a future local UI author, I want a stable [gRPC](https://grpc.io/) contract over a [unix socket](https://en.wikipedia.org/wiki/Unix_domain_socket) exposing daemon state and behavior, so that I can build another same-host UI without modifying kkd.
    - After v1, a user can open their own profile from another authorized device. The execution host checks each request and keeps the thread’s workspace, harness login, and history. See [Remote access through profiles](13-architecture/remote-access.md).
82. As a future UI author, I want server-streaming events for thread state changes, so that my UI reacts in real-time without polling.
83. As a developer, I want `kk` CLI, `kk` TUI, and `kk-hook` to be pure clients of the same gRPC API (no privileged internals), so that UIs and the daemon evolve independently.

## Cross-repo

84. As a developer, I want one kkd per user, not per repo, so that I have a single mental model: one daemon, one credential surface, one set of CLI verbs.
    - Each `kk` TUI invocation is still repo-scoped.
    - The cross-repo view ships as `kk ls` with the `repo` column.
85. As a developer, I want `kk init` in each repo to be the per-repo opt-in, so that kkd is explicit about what it manages.
86. As a developer, I want `kk ls` outside a registered repo to list threads across ALL registered repos with a `repo` column, so that I get the full picture.
87. As a developer, I want `kk ls` inside a registered repo to default to that repo, so that the contextual default matches my likely intent and the two scope axes never conflate.
    - `--all-repos` widens the repo scope to every registered repo.
    - `--all` widens the lifecycle scope to include closed threads.
    - The two flags compose independently.

## Hooks and harness integration

A [harness](appendix-a-glossary.md#harness) is the agent program kiki runs, such as Claude Code or Codex. A hook is a command the harness runs at a set moment, such as before each tool call; see [Claude Code hooks](https://docs.claude.com/en/docs/claude-code/hooks).

88. As a developer, I want kk to launch its managed Claude session with isolated, launch-scoped hook settings, so that my non-kk Claude Code work is unaffected and tracked `.claude/settings.json` is never overwritten.
89. As a developer, I want kiki to refuse an unsafe managed session when it cannot prove exclusive control of the pre-tool boundary, so that concurrent user hooks cannot race workspace reconciliation.
    - Kiki preserves unrelated hook types only when the harness can isolate them.
90. As a developer, I want any fallback merge into `.claude/settings.local.json` to leave my own content intact, so that nothing user-owned is overwritten or deleted.
    - The merge preserves prior bytes through a content-hash ownership record.
    - On close, kiki restores only its own fragment.
91. As a developer, I want kk to launch its managed Codex session under a generated launch-scoped `CODEX_HOME`, so that my non-kk Codex work is unaffected and nothing under `<workspace>/.codex/` is ever written.
    - Kiki's hooks are pre-trusted there.
    - My own `~/.codex/` configuration is structurally excluded.

    91a. As a developer on a harness version that cannot prove its batch boundary, I want kk to fall back to proof-carrying restart+resume for context delivery, so that delivery can continue at the cost of restarting the agent.
    - Examples of such a version: a Codex version whose dispatch discipline changed, or a Claude Code version without an unambiguous batch-completion signal.
    - A version that cannot supply the restart proofs either is unsupported for managed execution, not silently approximated.

92. As a developer, I want the [`kk-hook`](appendix-a-glossary.md#kk-hook) sidecar to add imperceptible latency to each agent tool call, so that the hook never feels in the way.
    - The target is under 5ms in the typical case.

## Trust model and auditability

93. As a developer, I want destructive, cross-thread, sensitive-read, and externally visible operations to require a one-use [approval](appendix-a-glossary.md#human-approval), so that a buggy hook or agent invoking `kk` cannot inherit reusable human authority.
    - The approval is bound to the exact method and target.
    - By default it is issued through an interactive foreground flow, where I confirm the plan myself.
    - The only other source is an [automation policy](appendix-a-glossary.md#automation-policy) rule that I wrote and activated (stories 144 to 149). Such a rule issues a one-use [`PolicyApproval`](appendix-a-glossary.md#policy-approval) for the exact plan.
    - There is no `--yes` flag, no piped confirmation, no approval from an environment variable, and no reusable approval token.
94. As a developer, I want each thread's `kk-hook` to be issued a [`ThreadScoped`](appendix-a-glossary.md#threadscoped-credential) credential bound to that thread's id, so that even if a hook's behavior is wrong it cannot mutate any other thread's state.
95. As a developer, I want every parseable daemon transport attempt recorded exactly once in [SQLite](https://www.sqlite.org/), so that operational history is queryable without inventing a repo for bootstrap or failed routing.
    - This covers every attempt: accepted or rejected, gRPC or [MCP](https://modelcontextprotocol.io/).
    - Resolved-repo attempts go in that repo's audit table.
    - Unscoped or unresolved attempts go in the user-level table.
96. As a developer, I want `kk audit log` and per-thread audit slices via `kk thread audit` to surface the audit trail.
    - I understand that append-only is enforced by daemon APIs and is not tamper-proof against my UID (my own user account).
97. As a developer, I want the trust model to state its protections and limits.
    - One-shot approvals reduce accidental agent authority.
    - Policy activation is hygiene of the same kind. It keeps an agent from granting itself authority by editing a config file. It is not a security boundary.
    - They do not defend against an actively malicious same-UID process that can impersonate user interaction or modify local state.

## Thread transcript

The [thread transcript](appendix-a-glossary.md#thread-transcript) is kiki's stored record of the conversation in a thread.

98. As a developer, I want kkd to capture each human-authored, agent-authored, and kk-authored conversational text event in a thread to a durable on-disk log, so that I have a recall surface separate from what was committed.
    - Each event is bound to the jj change-id that was `@` at capture time.
99. As a developer, I want the thread transcript to live in `~/.config/kiki/repos/<repo_id>/state.db`, so that prose containing dead ends, tool errors, or quoted file contents does not enter the repo or publication paths.
    - The file is centralized under `~/.config/kiki/`, never pushed, and never inside the source repo's filesystem.
    - Separately consented [provider egress](appendix-a-glossary.md#provider-egress) remains explicit. (Provider egress means sending text to the company that hosts the model.)
100.  As a developer, I want `kk thread transcript [<change>]` to print messages for a change, so that I can recall context as a human reader.
      - `--search <query>` gives full-text search.
      - `--range <from>..<to>` gives spans.
      - `--recent <n>` gives the tail of the thread.
101.  As a developer, I want my agent to be able to retrieve from its own thread's log mid-task via a kiki-hosted [MCP](https://modelcontextprotocol.io/) server, so that the agent can recall what happened earlier without me bridging it manually.
      - This follows the v1.x human transcript surface and is not acceptance work.
102.  As a developer, I do NOT want my agent to read another thread's log via MCP in v1, so that cross-thread context-sharing waits for the v2 substrate design and its safety mechanisms.
      - Those mechanisms are [causal-chain](appendix-a-glossary.md#causal-chain) detection, depth caps, and an audit trail.
103.  As a developer, I want the v1.x `kk reopen --catch-up` flow to send a brief transcript-derived catch-up to the resumed agent, so that a reopened thread need not be a cold start.
      - The flow previews the catch-up first.
      - It sends the catch-up after first-use consent.
      - Provider egress is never mislabeled as local-only.
104.  As a developer, I want [auto-describe](appendix-a-glossary.md#auto-describe) and PR drafting to NOT read from the locally stored transcript, so that recall prose cannot silently leak into published artifacts.
      - This is the [no-publication rule](appendix-a-glossary.md#no-publication-rule).
105.  As a developer, I want `kk thread destroy` to delete the thread transcript by default, along with the local bookmark and the thread's other local projections, so that destroy means destroy unless I say otherwise.
      - The thread's jj revisions are still kept by default (story 69).
      - `--keep-log` is the explicit retention opt-out.
106.  As a developer, I want the capture path abstracted behind a [`TranscriptAdapter`](appendix-a-glossary.md#transcriptadapter) trait, so that both v1 harnesses (Claude Code and Codex) share one path and later harnesses can be added without touching the log schema or the read API.
107.  As a developer, I do NOT want token-streaming deltas, structured tool-call inputs and outputs, or extended-thinking blocks captured in the initial transcript release, so that the log is a readable narrative rather than a verbose event stream.

## Revision and status view (`kk log`, `kk status`)

108. As a developer, I want `kk log` to be the daily-driver revision view, so that I see what I am working on without drowning in everyone else's history.
     - It is analogous to `jj log`, but stack-aware. See [stack-aware collapse](appendix-a-glossary.md#stack-aware-collapse).
     - My current thread's revisions render in detail.
     - Unrelated threads collapse to one-line summaries.
109. As a developer, I want `kk log`'s default expansion to follow the entire follows-stack the current thread sits in, so that stacked work reads as one coherent chain instead of forcing me to switch threads to see what I am building on.
     - The stack is the current thread plus every ancestor thread up to trunk.
110. As a developer, I want sibling and unrelated threads to render as collapsed one-liners, so that scanning is cheap and the screen stays useful.
     - Each one-liner shows the bookmark, an optional PR number, a status glyph, and the thread's last revision description.
111. As a developer, I want `kk log --no-stack` to drop to strict-current-thread expansion (ancestors collapse), so that I have a focused view when the stack is irrelevant to what I'm reading.
112. As a developer, I want `kk log --all` to include closed/archived threads as collapsed lines, so that I can find archived work without leaving the log.
113. As a developer, I want `kk log --wide` (`-w`) to switch collapsed lines to a richer format, so that I get a one-screen status view when I want one.
     - The richer format includes PR draft/ready state, CI roll-up, and agent state.
114. As a developer, I want `kk log -r <revset>` to pass through to a jj [revset](https://docs.jj-vcs.dev/latest/revsets/) (jj's query language for picking revisions), so that I have one explicit escape hatch for "I know exactly what I want."
     - Results render with kk decoration (PR badges, thread coloring).
     - Collapse logic is disabled.
115. As a developer, I want `kk log -r` combined with `--no-stack`/`--all`/`--wide` to error rather than silently ignore the conflicting flag, so that the override semantics stay unambiguous.
116. As a developer, I want `kk log` to still render something useful when no thread can be resolved, so that the command is always useful from anywhere in a registered repo.
     - "No thread can be resolved" means none is found from an explicit target, the environment, Herdr pane identity, or cwd.
     - In that case `kk log` renders the trunk in detail with all repo threads as collapsed lines.
     - It adds a header announcing the degraded state.
117. As a developer, I want `kk log` invoked outside any registered repo to error with a pointer to `kk ls` (the cross-repo view), so that `kk log` and `kk ls` stay distinct concepts.
118. As a developer, I want `kk status` to render a small kk-shaped header followed by literal `jj st` output for the working copy, so that I get the thread context plus the file listing I already know how to read.
     - No background process ever snapshots my files.
     - The header shows thread, PR, CI, agent state, and follows summary.
     - (`kk status` is in the acceptance slice. Its PR and CI fields are v1.x; until those integrations ship, the header leaves them out.)
     - The `jj st` part is run by the `kk` CLI in my own contextual workspace, exactly as if I had typed it. It is never run by the daemon.
     - The header comes from [pinned reads](appendix-a-glossary.md#pinned-read) that do not touch the working copy.
119. As a developer, I want `kk status --diff` (`-p`) to append the working-copy patch, so that I can review changes without dropping to `jj diff`.
     - `--diff --stat` appends a diffstat instead.
     - Both go through the same explicit, human-invoked passthrough in my own contextual workspace.
120. As a developer, I want `kk status --no-jj` to suppress the working-copy section and emit only the kk header, so that I can script against the thread context and so the overlay and UI pane can reuse the same renderer cheaply.
121. As a developer, I want the cascade-state indicator in `kk status` to be three-valued (`in sync` / `pending` / `conflicted`) with no count, so that the most common signal is glanceable.
     - The noisy edge ("how many cascades behind") then doesn't become a recurring distraction.
122. As a developer, I want `kk` to remain pure porcelain, so that anything jj can do, I do via `jj` directly without learning a near-mirror surface that risks subtle drift.
     - Porcelain here means a thin, human-friendly layer on top of another tool.
     - `kk log` and `kk status` adopt no jj flags beyond `-r <revset>`.

## Interactive overlay TUI (`kk` / overlay keybinding)

The [overlay](appendix-a-glossary.md#overlay-tui) is kiki's interactive screen. [Interface](10-interface/spec.md#overlay) specifies it. Stories 123 to 129 are all v1.x: the overlay is [v1.x polish](appendix-a-glossary.md#v1-x-polish).

123. As a developer, I want the overlay TUI to be a thread list on the left plus a preview pane on the right, so that one panel answers both "where am I in the work?" and "who needs me?" without me leaving navigation. (v1.x.)
     - The thread list shows two sections.
     - On top is a Stack section: the same stack-aware log as `kk log`, with the current thread's status inlined under its bookmark line.
     - Below it is an Activity section: the same threads, flat-listed by most-recent agent event.
124. As a developer, I want the navigation cursor to move on log lines (j/k or arrows) and `enter` to switch to the cursored thread (dismissing the overlay), so that the most common action is the cheapest keystroke. (v1.x.)
125. As a developer, I want `space` to preview the cursored thread in the right pane without changing my active thread, so that I can peek before committing to a switch. (v1.x.)
     - The preview is the transcript tail, the diff, or the comments, toggleable via `t`/`d`/`c`.
126. As a developer, I want destructive and creative verbs to be available only in the overlay TUI, so that a stray keypress or click in a passive surface can't take action. (v1.x.)
     - The verbs are `n` spawn, `N` spawn-as-child-of-cursored, `p` publish, `x` close, `i` interrupt, and `r` reopen.
     - `n` follows the thread the overlay runs in by default, the same as `kk new` typed there.
     - `a` shows or hides closed rows, so that `r` can reach a closed thread.
     - They are not available in the UI pane or Herdr's sidebar.
     - (`c` is reserved for the PR-comments preview in story 125; close binds to `x` to avoid the collision.)
127. As a developer, I want consequential overlay verbs (`x`, `i`) to open a daemon-issued approval card rather than firing immediately, so that fat-fingering does not cost me work and the confirmation is bound to the exact plan. (v1.x.)
     - The card is drawn only by kiki's own foreground [presenter](appendix-a-glossary.md#approvalpresenter).
     - It is never drawn by a Herdr toast, plugin, keybinding, or sidebar row.
128. As a developer, I want `t` and `T` to be two depths of the same transcript view, so that the cheap glance and the deep drill-down sit on the same letter at two different intensities. (v1.x.)
     - Lowercase `t` in the overlay surfaces a transcript-tail preview in the right pane, alongside `d` diff and `c` PR comments.
     - Shift-`T` escalates to a full-screen `kk thread transcript` reader for the cursored thread.
129. As a developer, I want `?` to toggle the [chord ribbon](appendix-a-glossary.md#chord-ribbon) listing the keys active for the current selection, so that the action set is discoverable rather than memorized. (v1.x.)

## Herdr sidebar and UI pane (opt-in)

[Herdr](appendix-a-glossary.md#herdr) is the terminal multiplexer kiki uses; its sidebar lists every thread's [terminal group](appendix-a-glossary.md#terminal-group). The UI pane is kiki's own optional [`ui` role pane](appendix-a-glossary.md#ui-role-pane). Stories 130 to 137 are all v1.x. The acceptance slice provisions the agent pane only, and it publishes only the thread's label to Herdr's sidebar.

130. As a developer, I want to opt into a UI pane in every thread's terminal group via `[ui] ui_pane = true` in my user-global config, so that I have the Stack tree permanently visible without invoking the overlay, alongside the list Herdr's sidebar gives me. (v1.x.)
     - The UI pane sits left of the agent and is `[ui] ui_pane_width` columns wide.
131. As a developer, I want `kk new <name> --ui-pane` / `--no-ui-pane` to override my UI-pane default per thread, so that one-off threads can opt in or out without changing global config. (v1.x.)
132. As a developer, I want each view to show one consistent thing, so that there is one mental model for each view regardless of where it lives and kiki does not rebuild what Herdr already draws. (v1.x.)
     - The UI pane renders the same Stack tree and inlined status the overlay does.
     - Herdr's sidebar carries the cross-repo list and attention state.
133. As a developer, I want the UI pane restricted to navigation-only keys, so that accidental focus on the UI pane cannot mutate state. (v1.x.)
     - The keys are j/k/arrows/enter/?, plus mouse click-to-focus and scroll.
     - Destructive/creative verbs are not bound.
134. As a developer, I want the [role panes](appendix-a-glossary.md#role-pane) (agent, shell, and UI) to be provisioned with the terminal group during `kk new`'s recoverable creation [saga](appendix-a-glossary.md#saga), so that the panes are reliably present. (v1.x.)
     - The saga does not assume that a database transaction can include terminal-runtime operations.
     - Navigation does not mutate my layout.
     - Each pane is launched by direct argv with an explicit working directory and environment.
     - The panes are ensured again only at `kk reopen` and at a `kk repair` terminal restart.
     - They are never ensured at `kk switch`.
135. As a developer, I want kk to NOT put back a shell or UI pane I deliberately closed until the thread is reopened or its terminal is restarted, so that my layout choices are honored. (v1.x.)
     - If I want another shell, I split one natively in Herdr.
136. As a developer, I want role panes provisioned whether or not any client is attached and whatever its size, so that thread creation never depends on which window I happened to run it from. (v1.x.)
     - Herdr's own resize and zoom handle a narrow terminal.
137. As a developer, I want toggling `[ui] ui_pane` after threads exist to take effect the next time a terminal group is provisioned, so that I'm not surprised when an existing thread stays unchanged. (v1.x.)
     - A terminal group is provisioned at `kk new`, `kk reopen`, or a terminal restart.
     - The toggle does not retroactively reshape live terminal groups.
     - A config-set warning makes the lag visible.

## Shell pane (opt-out)

Stories 137a and 137b are v1.x: the `shell` role pane is v1.x polish. In the acceptance slice, close already treats every pane in the terminal group the way story 137b describes.

137a. As a developer, I want every thread's terminal group to come up with a [shell pane](appendix-a-glossary.md#shell-pane) by default, so that direct `jj` / `gh` / test invocations live alongside the agent. (v1.x.)

- The shell pane sits alongside the agent pane in the same tab.
- Without it, I would have to spawn a separate terminal and `cd` into the workspace each time.
- The pane is positioned below the agent in the default layout, or to the right via `[ui] shell_pane_position`.
- Its cwd is set to the jj workspace.
- `KIKI_THREAD_ID` is set explicitly.
- No approval, Admin, or automation credential is in its environment.
- The rest of its environment comes from my login baseline rather than from whichever terminal ran `kk new`.
- The shell process is taken from my `$SHELL`.

137b. As a developer, I want the shell pane to end with the terminal group at `kk close`, so that the close blast radius is unambiguous. (v1.x.)

- The agent ends with it, and so do any other panes or tabs I added.
- The processes found in them are listed in the close plan, frozen, terminated by kiki, and verified gone.
- This teaches me not to leave long-running jobs in the thread's panes expecting them to survive.

## Stated non-goals

138. As a developer, I do NOT want kk to manage or cap my agent's resource consumption (CPU, RAM, tokens), so that those decisions stay in my hands.
139. As a developer, I do NOT want kk to refuse `jj`, `gh`, or native Herdr operations I run directly, so that kk remains additive infrastructure.
140. As a developer, I do NOT want kk to surface CPU/RSS for agent processes.
     - That is what Activity Monitor and htop are for.
     - Duplicating them poorly clutters kk.
141. As a developer, I do NOT expect per-thread workspace isolation to act as a security boundary in v1.
     - A security boundary here would mean filesystem ACLs (access control lists) or [sandboxing](<https://en.wikipedia.org/wiki/Sandbox_(computer_security)>).
     - That is a future-version concern.
     - v1 promises only cooperative separation.

## Headless operation

kiki must be fully operable [headless](appendix-a-glossary.md#headless). That word covers two things:

- **No UI.** Nothing needs an attached [Herdr client](appendix-a-glossary.md#herdr-client), the overlay, a popup, the UI pane, or a desktop session.
- **No human.** An activated [automation policy](appendix-a-glossary.md#automation-policy) can stand in for the person who would confirm an approval.

The operator in these stories runs kiki on a machine like a build server, a container, or a cloud host reached over SSH. Stories 142 to 154 and 156 to 158 are in the [acceptance slice](appendix-a-glossary.md#acceptance-slice). Stories 142 to 152 and 156 to 158 are built in Stage 1 of the [build sequence](15-build-sequencing.md), because kiki's own end-to-end tests need them. Stories 153 and 154 are built in Stage 2. Story 155 is v1.x. Running with no UI is a v1 [invariant](02-invariants.md).

142. As an operator, I want every kiki command, lifecycle step, and safety proof to work with no UI attached, so that kiki runs the same on a server as on my laptop.
     - The terminal server runs with zero clients attached.
     - A thread is created, reconciled, repaired, and closed the same way whether or not anyone is watching.
     - The overlay, the UI pane, and Herdr's sidebar are views. Anything they show, I can also get from a command with `--json`.
143. As an operator, I want `kk daemon install` to install and start `kkd` without asking me anything, so that a setup script can bring up a new machine.
     - A first install needs no credential. It creates the Admin bootstrap credential and prints the path of its file.
     - A later run that changes an existing installation needs my confirmation at a foreground terminal, or `--admin-credential-file <path>`.
     - The interactive first-run question stays for people at a terminal (story 4).
     - On a host with no user service manager, such as many containers and CI runners, I run `kkd --foreground` under my own supervisor. `kkd` then starts the terminal server as a detached process. On its first start it creates the Admin bootstrap credential and logs its path.
     - The same proof gate applies there: the terminal server and the agents must outlive a `kkd` crash. A platform that fails that proof is unsupported.
     - See [`kk daemon install`](09-commands.md#kk-daemon-install).
144. As an operator of a machine that never has a human, I want to activate my automation policy with the Admin credential, so that no person has to be at a keyboard to turn it on.
     - I write the rules in the `[automation]` section of my user config file. See [Configuration · Automation keys](11-configuration.md#automation-keys).
     - I run `kk automation apply --admin-credential-file <path>`.
     - On a machine with a person, the same command instead shows the full policy, and how it differs from the active one, in a foreground terminal for me to confirm.
     - The Admin credential is still never loaded automatically and never given to an agent.
     - No approval presenter needs to be enrolled on such a machine.
     - See [Authority · Activating a policy](04-authority.md#activating-a-policy).
145. As a developer, I want an edit to `[automation]` to do nothing until I activate it, so that an agent or a stray script cannot grant itself authority by editing a file.
     - `kkd` evaluates only the stored copy of the policy that was activated.
     - `kk automation status` shows the active policy, its digest, who activated it and when, and whether the file now differs from it.
     - `kk automation revoke` clears the active policy. It only removes authority, so it needs no approval.
     - Only my user config file can hold the policy. A repository, a thread, the environment, and `--config` cannot set it.
     - A policy rule can never approve activating a policy.
146. As an operator, I want a named [automation credential](appendix-a-glossary.md#automation-credential) for my scripts, so that a script can ask for approvals without holding Admin or a thread's credential.
     - I create it with `kk automation credential create <name>`. Creating or rotating one needs the same gate as activation: a person's foreground confirmation, or the Admin credential.
     - `kk automation credential revoke <name>` needs no approval, and any credential of mine may call it. `list` shows what exists.
     - It lives at `~/.config/kiki/automation/<name>.cred`, readable only by me, outside every managed workspace.
     - kiki never puts it into a harness, a hook, or a pane's environment.
     - My script presents it with `KIKI_AUTOMATION_CREDENTIAL_FILE` or `--automation-credential-file <path>`.
     - By itself it can only read repo summaries, read each thread's status and non-sensitive state, and ask for approvals. Everything consequential it does goes through the policy.
     - Even an ordinary change to a thread, such as a checkpoint, needs a rule when my script makes it, because the script is not that thread. The rule names the `thread-op` operation.
     - It can never confirm a human's approval, and it is never accepted in place of Admin.
     - See [`kk automation`](09-commands.md#kk-automation).
147. As an operator, I want to script a whole thread lifecycle with that credential, so that work can start, run, and finish with no person present.
     - The script runs `kk init`, then `kk new <name> -m "<prompt>"`, waits for the agent, reads the result, and runs `kk close`.
     - Each step that needs an approval gets one from a rule that names my credential and that operation. `kk` prints the plan and "approved by rule `<name>`", and does not prompt.
     - `kk init` run with an automation credential needs a rule that allows `init`.
     - The first prompt is given with `kk new -m`.
148. As an operator, I want the rules for unattended approval to be fully configurable, so that I decide exactly how much kiki may do without me.
     - A rule names who is asking (`principals`), which repos, which `operations`, and which [risk labels](appendix-a-glossary.md#risk-label) it will `accept`.
     - A rule either allows the plan or requires a human. A rule that requires a human wins over any rule that allows.
     - Only a rule that allows uses `accept`. A rule that requires a human matches whatever risk labels the plan has.
     - A plan that no rule matches needs a human, as it does with no policy at all.
     - An agent gets authority from the policy through rules that match its thread credential, including the wildcard principal. An agent can never confirm a human's approval.
     - I may use `*` for principals, repos, operations, and accepted risks. This grants any matching local caller every policy-eligible operation except provider consent. Consent names a purpose and a provider.
149. As an operator, I want a policy rule to replace only the human's confirmation and never a safety check, so that unattended does not mean unsafe.
     - The plan, its digest, the drift and expiry checks, the freeze, the holder scan, the final proof, and verified exit all still run.
     - A plan that a safety proof refuses is refused under any rule, even one that accepts every label.
     - The plan that `kk` prints carries what the approval card would have shown, including its risk labels.
     - A [`PolicyApproval`](appendix-a-glossary.md#policy-approval) is single-use and bound to the exact plan, like a human's approval.
150. As an operator, I want `kk` never to prompt when it has no terminal, so that a script fails fast and never hangs on a question nobody will answer.
     - Every question `kk` can ask has a flag or argument that answers it.
     - Without a terminal, `kk` fails and names the missing flag.
     - When an approval is needed and no rule allows the plan, `kk` refuses. The message names the operation, the plan's risk labels, and the reason: no rule matched, or a named rule requires a human.
151. As an operator, I want every `kk` command to end with a documented exit code, so that my script can branch on what happened without reading text.
     - `0` is success, `1` the operation failed, and `2` a usage error.
     - `3` means an approval was needed and none was available.
     - `4` means a precondition or a safety proof refused.
     - `5` means the daemon is unreachable or not installed.
     - `6` means a timeout.
     - See [Commands · Exit codes](09-commands.md#exit-codes).
152. As an operator, I want `--json` output and a live event stream, so that I can watch a headless host with scripts.
     - `--json` works on every read command and on every command's final result. It changes only how the output is drawn. See [Output for scripts](09-commands.md#output-for-scripts).
     - [`kk events`](09-commands.md#kk-events) prints the event stream for one thread or for the whole repo.
     - `--follow` keeps the stream open, and `--since <seq>` resumes after the last event my script saw.
     - This is the command-line face of the event stream in story 82.
153. As an operator, I want `kk wait [<thread>] --for <state>` to block until a thread reaches a state, so that a script can wait for an agent without polling. (Stage 2.)
     - The states are `quiescent`, `goal-complete`, `blocked`, `conflicted`, `closed`, and `issue`.
     - `--timeout <dur>` limits the wait. The command exits `0` when the state is reached and `6` on timeout.
     - See [`kk wait`](09-commands.md#kk-wait).
154. As an operator, I want a `loud` attention event to run a program I name, so that a machine with no desktop can still reach me. (Stage 2.)
     - I set `[notifications] command` to the program and its arguments. Only my user config file can set it, because it makes `kkd` run a program.
     - `kkd` runs it once for each `loud` event, with the event as JSON on standard input, with a short timeout, and never retries.
     - With `os_provider = "auto"` on a host with no desktop session, kiki uses the command when one is set and sends nothing otherwise.
     - See [Configuration · The `command` provider](11-configuration.md#the-command-provider).
155. As an operator, I want to allow transcript-egress consent for a named purpose and provider in my policy, so that a provider-backed feature can run with no person present. (v1.x, with those features.)
     - The rule must name `consent:<purpose>` and list the providers. A `*` in `operations` never matches consent.
     - A plain configuration key still cannot grant consent.
156. As an operator, I want kiki never to answer a harness's own permission prompt, so that what my agent may do stays set in the harness and not in kiki.
     - On a headless host I set the harness's own permission settings ahead of time.
     - If a prompt still appears, the agent waits and the blocked-agent event fires. It shows in `kk events` and reaches my notification command.
     - I can answer later by running `kk attach` over SSH.
157. As an operator, I want every approval a rule gives to be recorded, so that I can later see what ran without me and why it was allowed.
     - Each `PolicyApproval` writes an audit row with the rule name, the policy digest, the principal, the operation, and the risk labels.
     - Policy activation and revoke are audited at the user level. So are automation credential create, rotate, and revoke.
     - An audit reader can always tell a person's approval from a rule's.
158. As a developer who activated no policy, I want kiki to behave exactly as it did before, so that headless support costs me nothing.
     - A person confirms each approval at a foreground terminal.
     - A caller with no terminal is refused.
