# Documentation writing audit, 2026-11-17

- Profile: `docs`; mode: `rewrite`; skill: `avoid-ai-writing` 3.4.0.
- Starting revision: `ce22fc5e3d224b8e4c3529db5663ccd2b351562e`.
- Scope: 59 Markdown files and five Vue theme components.
- Result: 132 quoted edits across 36 files.
- [Review outcome](../../../investigations/2026/2026-11-17-documentation-writing-review.md).

The quoted text below records the edits. It is evidence of the review, not current
product guidance. Each file link opens the full rewritten version. Formatting may
change line wrapping; the code blocks preserve the wording recorded during editing.
Second-pass corrections are folded into the replacements.

## File inventory

| File | Writing review |
| --- | --- |
| [README.md](../../../../README.md) | Rewritten |
| [AGENTS.md](../../../../AGENTS.md) | Rewritten |
| [CLAUDE.md](../../../../CLAUDE.md) | Reviewed; no prose edit needed |
| [docs/index.md](../../../../docs/index.md) | Reviewed; no prose edit needed |
| [docs/reference/README.md](../../../../docs/reference/README.md) | Rewritten |
| [docs/reference/book/00-abstract.md](../../../../docs/reference/book/00-abstract.md) | Rewritten |
| [docs/reference/book/01-orientation.md](../../../../docs/reference/book/01-orientation.md) | Rewritten |
| [docs/reference/book/02-invariants.md](../../../../docs/reference/book/02-invariants.md) | Rewritten |
| [docs/reference/book/03-threads.md](../../../../docs/reference/book/03-threads.md) | Rewritten |
| [docs/reference/book/04-authority.md](../../../../docs/reference/book/04-authority.md) | Rewritten |
| [docs/reference/book/05-cascade.md](../../../../docs/reference/book/05-cascade.md) | Rewritten |
| [docs/reference/book/06-transcript.md](../../../../docs/reference/book/06-transcript.md) | Rewritten |
| [docs/reference/book/07-publishing.md](../../../../docs/reference/book/07-publishing.md) | Reviewed; no prose edit needed |
| [docs/reference/book/08-metadata.md](../../../../docs/reference/book/08-metadata.md) | Rewritten |
| [docs/reference/book/09-commands.md](../../../../docs/reference/book/09-commands.md) | Rewritten |
| [docs/reference/book/10-interface/README.md](../../../../docs/reference/book/10-interface/README.md) | Rewritten |
| [docs/reference/book/10-interface/spec.md](../../../../docs/reference/book/10-interface/spec.md) | Reviewed; no prose edit needed |
| [docs/reference/book/10-interface/storyboard.md](../../../../docs/reference/book/10-interface/storyboard.md) | Rewritten |
| [docs/reference/book/11-configuration.md](../../../../docs/reference/book/11-configuration.md) | Rewritten |
| [docs/reference/book/12-observability.md](../../../../docs/reference/book/12-observability.md) | Reviewed; no prose edit needed |
| [docs/reference/book/13-architecture/README.md](../../../../docs/reference/book/13-architecture/README.md) | Rewritten |
| [docs/reference/book/13-architecture/crates.md](../../../../docs/reference/book/13-architecture/crates.md) | Rewritten |
| [docs/reference/book/13-architecture/daemon.md](../../../../docs/reference/book/13-architecture/daemon.md) | Rewritten |
| [docs/reference/book/13-architecture/grpc.md](../../../../docs/reference/book/13-architecture/grpc.md) | Reviewed; no prose edit needed |
| [docs/reference/book/13-architecture/harness-adapter.md](../../../../docs/reference/book/13-architecture/harness-adapter.md) | Rewritten |
| [docs/reference/book/13-architecture/op-log-watcher.md](../../../../docs/reference/book/13-architecture/op-log-watcher.md) | Rewritten |
| [docs/reference/book/13-architecture/schema.md](../../../../docs/reference/book/13-architecture/schema.md) | Rewritten |
| [docs/reference/book/13-architecture/terminal-runtime.md](../../../../docs/reference/book/13-architecture/terminal-runtime.md) | Rewritten |
| [docs/reference/book/14-testing.md](../../../../docs/reference/book/14-testing.md) | Rewritten |
| [docs/reference/book/15-build-sequencing.md](../../../../docs/reference/book/15-build-sequencing.md) | Rewritten |
| [docs/reference/book/16-roadmap.md](../../../../docs/reference/book/16-roadmap.md) | Rewritten |
| [docs/reference/book/17-decisions/README.md](../../../../docs/reference/book/17-decisions/README.md) | Reviewed; no prose edit needed |
| [docs/reference/book/17-decisions/cascade-outbox.md](../../../../docs/reference/book/17-decisions/cascade-outbox.md) | Reviewed; no prose edit needed |
| [docs/reference/book/17-decisions/codex-adapter.md](../../../../docs/reference/book/17-decisions/codex-adapter.md) | Rewritten |
| [docs/reference/book/17-decisions/native-evolution.md](../../../../docs/reference/book/17-decisions/native-evolution.md) | Rewritten |
| [docs/reference/book/17-decisions/rejected.md](../../../../docs/reference/book/17-decisions/rejected.md) | Reviewed; no prose edit needed |
| [docs/reference/book/17-decisions/thread-head-and-sagas.md](../../../../docs/reference/book/17-decisions/thread-head-and-sagas.md) | Reviewed; no prose edit needed |
| [docs/reference/book/17-decisions/transcript-anchoring.md](../../../../docs/reference/book/17-decisions/transcript-anchoring.md) | Reviewed; no prose edit needed |
| [docs/reference/book/appendix-a-glossary.md](../../../../docs/reference/book/appendix-a-glossary.md) | Rewritten |
| [docs/reference/book/appendix-b-user-stories.md](../../../../docs/reference/book/appendix-b-user-stories.md) | Rewritten |
| [docs/reference/book/appendix-c-naming.md](../../../../docs/reference/book/appendix-c-naming.md) | Rewritten |
| [docs/research/herdr-jj.md](../../../../docs/research/herdr-jj.md) | Rewritten |
| [docs/research/herdr-terminal-runtime.md](../../../../docs/research/herdr-terminal-runtime.md) | Rewritten |
| [journal/README.md](../../../README.md) | Reviewed; no prose edit needed |
| [journal/archive/README.md](../../../archive/README.md) | Reviewed; no prose edit needed |
| [journal/decisions/0001-adopt-project-journal.md](../../../decisions/0001-adopt-project-journal.md) | Reviewed; no prose edit needed |
| [journal/decisions/0002-use-mise-for-tasks-and-formatting.md](../../../decisions/0002-use-mise-for-tasks-and-formatting.md) | Reviewed; no prose edit needed |
| [journal/decisions/0003-use-jj-and-shared-agent-guidance.md](../../../decisions/0003-use-jj-and-shared-agent-guidance.md) | Rewritten |
| [journal/decisions/0004-use-herdr-as-terminal-runtime.md](../../../decisions/0004-use-herdr-as-terminal-runtime.md) | Reviewed; no prose edit needed |
| [journal/decisions/0005-track-checkpoint-through-native-successors.md](../../../decisions/0005-track-checkpoint-through-native-successors.md) | Reviewed; no prose edit needed |
| [journal/decisions/0006-close-repair-and-proof-gaps.md](../../../decisions/0006-close-repair-and-proof-gaps.md) | Rewritten |
| [journal/decisions/README.md](../../../decisions/README.md) | Rewritten |
| [journal/decisions/TEMPLATE.md](../../../decisions/TEMPLATE.md) | Reviewed; no prose edit needed |
| [journal/evidence/README.md](../../README.md) | Reviewed; no prose edit needed |
| [journal/evidence/herdr-jj-revalidation/2026-11-16/README.md](../../herdr-jj-revalidation/2026-11-16/README.md) | Reviewed; no prose edit needed |
| [journal/investigations/2026/2026-11-16-herdr-jj-revalidation.md](../../../investigations/2026/2026-11-16-herdr-jj-revalidation.md) | Reviewed; no prose edit needed |
| [journal/investigations/README.md](../../../investigations/README.md) | Reviewed; no prose edit needed |
| [journal/investigations/TEMPLATE.md](../../../investigations/TEMPLATE.md) | Reviewed; no prose edit needed |
| [journal/tools/README.md](../../../tools/README.md) | Reviewed; no prose edit needed |
| [docs/.vitepress/theme/DocCrumb.vue](../../../../docs/.vitepress/theme/DocCrumb.vue) | Reviewed; no prose edit needed |
| [docs/.vitepress/theme/KikiHome.vue](../../../../docs/.vitepress/theme/KikiHome.vue) | Rewritten |
| [docs/.vitepress/theme/Mermaid.vue](../../../../docs/.vitepress/theme/Mermaid.vue) | Reviewed; no prose edit needed |
| [docs/.vitepress/theme/SlotCycle.vue](../../../../docs/.vitepress/theme/SlotCycle.vue) | Reviewed; no prose edit needed |
| [docs/.vitepress/theme/TreeOfWork.vue](../../../../docs/.vitepress/theme/TreeOfWork.vue) | Reviewed; no prose edit needed |

## Issues and replacements

### README.md

Full rewritten file: [README.md](../../../../README.md).

- Edit 1: Replace a promotional contrast with the specific coordination task.

  Original:

  ```text
  Start an auth refactor. Hand the tests to another coding agent, then chase an unrelated bug while both agents run. That should feel normal, not like a bookkeeping stunt.
  ```

  Replacement:

  ```text
  Start an auth refactor. Hand the tests to another coding agent, then investigate an unrelated bug while both agents run. Kiki tracks these lines of work and their dependencies.
  ```

- Edit 2: Remove a repeated definition and lead with the action.

  Original:

  ```text
  The reference book is also a [VitePress](https://vitepress.dev/) site (VitePress turns Markdown files into a website).
  ```

  Replacement:

  ```text
  [VitePress](https://vitepress.dev/) builds the reference website from Markdown files.
  ```

### docs/reference/README.md

Full rewritten file: [docs/reference/README.md](../../../../docs/reference/README.md).

- Edit 3: Replace metaphorical labels and a repeated definition with concrete chapter topics.

  Original:

  ```text
  Read it as a small spec book, a book that states exactly what the tool must do. It goes in this order: first the reason for the tool, then the model, then the safety rules, then the user surfaces and machinery.
  ```

  Replacement:

  ```text
  The book starts with the reason for the tool, then defines its model, safety rules, user interface, and implementation.
  ```

- Edit 4: State the contract directly instead of explaining it through a contrast.

  Original:

  ```text
  The book is normative: it sets rules, and does not only describe. It defines kiki's permitted behavior, prohibited behavior, and v1 boundaries. Ambiguity should be treated as a documentation bug to fix.
  ```

  Replacement:

  ```text
  The book defines what kiki must do, what it must not do, and what belongs in v1. Report unclear requirements as documentation bugs.
  ```

- Edit 5: Remove mixed metaphors and a forced three-item list.

  Original:

  ```text
  New readers should start with the [Abstract](book/00-abstract.md) and [Orientation](book/01-orientation.md). Together they carry the narrative, before the contract chapters tighten the screws:

  - the hand-built workflow that kiki automates, with one [workspace](book/appendix-a-glossary.md#workspace) per line of work;
  - the frictions of that workflow;
  - the mechanism that answers each friction.
  ```

  Replacement:

  ```text
  Start with the [Abstract](book/00-abstract.md) and [Orientation](book/01-orientation.md). They describe the manual workflow kiki automates: one [workspace](book/appendix-a-glossary.md#workspace) per line of work. They explain the bookkeeping this requires and how kiki handles it.
  ```

- Edit 6: Cut a repetitive explanation of reading order.

  Original:

  ```text
  The chapters tell the story in order. The appendices hold reference material. You dip into them when you need them; you do not read them straight through.
  ```

  Replacement:

  ```text
  Read the chapters in order. Use the appendices to look up terms, user stories, and names as needed.
  ```

### docs/reference/book/13-architecture/README.md

Full rewritten file: [docs/reference/book/13-architecture/README.md](../../../../docs/reference/book/13-architecture/README.md).

- Edit 7: Replace the side-door metaphor and its explanatory restatement with the requirement.

  Original:

  ```text
  Behavioral truth lives in the earlier chapters. Architecture exists to make that behavior implementable without smuggling privileged paths through the side door. In plain words: no part of the system gets a hidden shortcut around the rules.
  ```

  Replacement:

  ```text
  The earlier chapters define behavior. This architecture must enforce those rules across every program, including privileged operations.
  ```

### AGENTS.md

Full rewritten file: [AGENTS.md](../../../../AGENTS.md).

- Edit 8: Break a dense introduction into ownership and lifecycle explanations; replace metaphors, emphasis, and vague failure language.

  Original:

  ```text
  ## What kiki is, in one paragraph

  kiki (binary `kk`) is a daemon-backed coordinator that ties jujutsu (jj), the Herdr terminal multiplexer, agent harnesses (Claude Code and Codex in v1), and eventually the GitHub CLI (`gh`) into a workflow for multi-threaded agentic coding. The atom is a **thread** — a themed sequence of jj revisions whose live head is its managed workspace's `@`; its bookmark is an explicit checkpoint/publication projection that kiki tracks through jj's native rewrite successors. Each thread's terminals live in a terminal group — one Herdr workspace on a dedicated kiki Herdr server; Herdr owns the terminal, and its ids, labels, and replies are never authority for identity, readiness, or deletion. Threads can follow other threads. A managed session reserves the pre-tool hook boundary exclusively for kiki, blocks the entire triggering tool batch during reconciliation (Claude Code's parallel batch; a proven-serial Codex version's single-call batch), and acknowledges delivery only from a later model turn. kiki remains an **ambient coordinator** for direct `jj`, `gh`, and native Herdr operations, but ambiguous external projection changes fail loud into repair rather than being guessed through.

  The planned cargo workspace has four crates: `kiki-core` (library — shared types/traits/proto/migrations, no I/O), `kkd` (daemon binary), `kk` (CLI binary that also hosts the TUI as a subcommand), and `kk-hook` (harness hook sidecar). `kkd` is the gRPC server over `~/.config/kiki/kkd.sock`; local clients share that contract. State lives in `~/.config/kiki/state.db` (cross-repo registry) plus `~/.config/kiki/repos/<repo_id>/state.db` (per-repo runtime). Remote clients require a future transport and authentication contract rather than inheriting unix-socket assumptions.

  ## Implementation-stack tension to be aware of

  The architecture decision is **Rust** for `kkd` and friends (`docs/reference/book/13-architecture/crates.md`). The repo is currently bootstrapped as a **Bun + TypeScript** project (`package.json`, `tsconfig.json`, `index.ts` placeholder). This is a real divergence pending the first real `kkd` commit. If you are about to write or modify implementation code, surface this to the user before picking a language — do not silently default to either side.
  ```

  Replacement:

  ```text
  ## What kiki coordinates

  kiki (binary `kk`) coordinates jujutsu (jj), Herdr terminals, and coding agents
  (Claude Code and Codex in v1). GitHub CLI (`gh`) support comes later. Each
  thread is a named line of work with a managed jj workspace. Its live head is
  that workspace's `@`. Its bookmark points to an explicit checkpoint and represents the thread for
  publication. Kiki tracks that checkpoint through jj's native rewrite successors.

  Each thread has one Herdr workspace, called a terminal group, on a dedicated
  kiki server. Herdr owns the terminals. Kiki owns thread identity and decides
  when an agent is ready or files are safe to delete; Herdr ids, labels, and
  replies cannot establish those facts.

  Threads can follow other threads. Managed sessions reserve the pre-tool hook
  boundary exclusively for kiki. During reconciliation, kiki blocks the whole
  triggering tool batch: Claude Code's parallel batch or a proven-serial Codex
  version's single-call batch. Only a later model turn can acknowledge delivery.
  Users can still run `jj`, `gh`, and native Herdr operations directly. Ambiguous
  external changes to thread projections require repair.

  The planned Cargo workspace has four crates: `kiki-core` (shared types,
  traits, protocol definitions, and migrations, with no I/O), `kkd` (the daemon),
  `kk` (the CLI and TUI), and `kk-hook` (the harness hook sidecar). Local clients
  call `kkd` through gRPC over `~/.config/kiki/kkd.sock`. State lives in
  `~/.config/kiki/state.db` for the cross-repo registry and
  `~/.config/kiki/repos/<repo_id>/state.db` for each repo's runtime. Remote
  clients will need a separate transport and authentication contract.

  ## Implementation language

  The [architecture](docs/reference/book/13-architecture/crates.md) calls for
  Rust. The current bootstrap is Bun and TypeScript (`package.json`,
  `tsconfig.json`, and the placeholder `index.ts`). Before writing application
  code, point out this difference to the user and state which language you plan
  to use. Do not choose a language without explaining that choice.
  ```

### docs/reference/book/00-abstract.md

Full rewritten file: [docs/reference/book/00-abstract.md](../../../../docs/reference/book/00-abstract.md).

- Edit 9: Replace unsupported broad claims, rhetorical questions, and extended metaphors with an example and the exact coordination sequence.

  Original:

  ```text
  # Abstract

  kiki (`kk`) coordinates multi-threaded agentic coding: several AI coding agents working on separate lines of work at the same time. It binds together the pieces you already use: [jj](appendix-a-glossary.md#ext-jj) [workspaces](appendix-a-glossary.md#ext-workspace), persistent terminals, and coding agents such as [Claude Code](appendix-a-glossary.md#ext-claude-code) and [Codex](appendix-a-glossary.md#ext-codex). It binds them into **[threads](appendix-a-glossary.md#thread)**. A thread is a named line of work that runs in parallel with other threads. A background [daemon](appendix-a-glossary.md#ext-daemon) (a program that keeps running behind the scenes) keeps each thread isolated, visible, and in step with the work it builds on.

  kiki exists because agents made working in parallel easy, while the tooling around them still assumes one line of work at a time. That difference is paid for in human attention.

  <TreeOfWork />

  Real work branches. You chase a lead, hit a wall, back up, and try two other angles at once. Coding agents multiply this: give three of them room and by lunch you have five live lines of work. Your tools still assume a single line: one terminal, one branch, one train of thought.

  Nobody designs the workflow that copes with this; you arrive at it. Push agents hard enough and you build it by hand:

  - a jj workspace per line of work, so edits never collide;
  - a persistent terminal per workspace, so nothing dies when you look away. This is a [tmux](https://github.com/tmux/tmux) session or a workspace in another [terminal multiplexer](appendix-a-glossary.md#ext-terminal-multiplexer) (a program that keeps many terminals running);
  - an agent in every terminal;
  - a [bookmark](appendix-a-glossary.md#ext-bookmark) (jj's named pointer to a commit) naming every chain.

  It works, but it leaks. Which workspace has the auth fix? Which agent has been waiting an hour for a yes? Standing up line six means another workspace, another terminal, another name, another bookmark, all by hand. Meanwhile `main` moved, five workspaces went stale, and `jj log` braids everyone's history into one long scroll.

  The cost lands somewhere worse than your afternoon: it teaches you to stop branching. A dull knife changes what you cook. Expensive context switching changes what you build in the same way. The ambitious version of the work is usually a tree, and the tree is exactly what the tooling punishes.

  kiki makes the tree affordable by making the thread first-class: a real, named object that the tool tracks for you. A thread is the thing you were maintaining by hand. It is one line of work with its own jj workspace, its own [terminal group](appendix-a-glossary.md#terminal-group), its own agent, and its own bookmark. You create it in one command, and you can see it from anywhere.

  The terminals live in [Herdr](https://github.com/herdrdev/herdr), a terminal multiplexer built for agent work. kiki runs one [dedicated Herdr server](appendix-a-glossary.md#dedicated-herdr-server) and gives every thread a Herdr workspace in it.

  A thread's live tip is whatever [revision](appendix-a-glossary.md#ext-revision) its workspace sits on; jj calls that `@` (see [live head](appendix-a-glossary.md#live-head)). Its bookmark is a saved checkpoint. Think of a bookmark left between pages, not the page you are on.

  Threads [follow](appendix-a-glossary.md#follows) threads. When a parent changes, kiki does three things:

  1. It waits for a safe moment: the child's agent is between actions. The book calls this a [safe boundary](appendix-a-glossary.md#safe-boundary).
  2. It brings the child's files up to date. This works whether jj already rewrote the child's history or kiki must [rebase](appendix-a-glossary.md#ext-rebase) the child's chain.
  3. It tells the agent what changed.

  A new branch costs a command instead of a ritual. Staying in step with a parent becomes kiki's job, not yours.

  jj, Herdr, [gh](appendix-a-glossary.md#ext-gh) (GitHub's command-line tool), and the agent [harness](appendix-a-glossary.md#harness) (the program that runs the agent) stay the tools underneath. kiki watches them and keeps the tree honest. This book is the contract for that layer: the vocabulary, the rules, and the machinery.
  ```

  Replacement:

  ```text
  # Abstract

  kiki (`kk`) coordinates several AI coding agents working on separate lines of
  work. It groups a [jj](appendix-a-glossary.md#ext-jj)
  [workspace](appendix-a-glossary.md#ext-workspace), persistent terminals, and a
  coding agent into a named [thread](appendix-a-glossary.md#thread). The agent
  can run in [Claude Code](appendix-a-glossary.md#ext-claude-code) or
  [Codex](appendix-a-glossary.md#ext-codex). A background
  [daemon](appendix-a-glossary.md#ext-daemon) tracks the threads and coordinates
  updates between related work.

  <TreeOfWork />

  For example, an authentication refactor may need a separate test effort while
  another agent investigates an unrelated bug. You can set this up by hand:

  - Give each line of work its own jj workspace so its edits stay separate.
  - Keep a persistent terminal for each workspace. This may be a
    [tmux](https://github.com/tmux/tmux) session or a workspace in another
    [terminal multiplexer](appendix-a-glossary.md#ext-terminal-multiplexer).
  - Run an agent in each terminal.
  - Name each revision chain with a
    [bookmark](appendix-a-glossary.md#ext-bookmark), jj's named pointer to a commit.

  You then have to remember which workspace contains each change, which agent
  is waiting for an answer, and which revision chains depend on one another.
  Starting another line of work repeats the setup. When `main` or a parent
  revision changes, you must also update the affected workspaces and explain
  the changes to their agents. Switching among these tasks takes time away
  from the work itself.

  Kiki stores those relationships as threads. Each thread has its own workspace,
  [terminal group](appendix-a-glossary.md#terminal-group), agent, and bookmark.
  You create a thread with one command and can list it from any directory.

  The terminals run in [Herdr](https://github.com/herdrdev/herdr), a terminal
  multiplexer built for agent work. Kiki uses one
  [dedicated Herdr server](appendix-a-glossary.md#dedicated-herdr-server), with
  one Herdr workspace per thread.

  A thread's [live head](appendix-a-glossary.md#live-head) is the
  [revision](appendix-a-glossary.md#ext-revision) at its workspace's `@`.
  Its bookmark points to a saved checkpoint. These pointers can differ.

  Threads can [follow](appendix-a-glossary.md#follows) other threads. When a
  parent changes, kiki waits for the child's agent to reach a
  [safe boundary](appendix-a-glossary.md#safe-boundary) between actions. It then
  updates the child's files and tells the agent what changed. If jj already
  rewrote the child's history, kiki applies that repository state to the files.
  If the parent added a new revision, kiki may need to
  [rebase](appendix-a-glossary.md#ext-rebase) the child's chain first.

  You still use jj, Herdr, [gh](appendix-a-glossary.md#ext-gh) (GitHub's
  command-line tool), and the agent [harness](appendix-a-glossary.md#harness)
  directly. Kiki tracks their state and coordinates related threads. This book
  defines the rules and implementation for that coordination.
  ```

### docs/reference/book/01-orientation.md

Full rewritten file: [docs/reference/book/01-orientation.md](../../../../docs/reference/book/01-orientation.md).

- Edit 10: Replace a claim about what engineers converge on with the specific setup.

  Original:

  ```text
  kiki did not invent a workflow. It formalizes one that engineers who push agents hard converge on by hand:
  ```

  Replacement:

  ```text
  Kiki automates this setup for parallel agent work:
  ```

- Edit 11: Replace a symmetrical three-part slogan with concrete responsibilities.

  Original:

  ```text
  Every column of that picture pulls its weight:

  - jj workspaces give isolation;
  - the [terminal multiplexer](appendix-a-glossary.md#ext-terminal-multiplexer) (the program that keeps many terminals running) gives persistence;
  - the agents give initiative.
  ```

  Replacement:

  ```text
  The workspaces separate file edits. The [terminal multiplexer](appendix-a-glossary.md#ext-terminal-multiplexer) keeps terminals running, and the agents work in those terminals.
  ```

- Edit 12: Replace rhetorical questions, repeated metaphors, and bold mini-headings with a list of concrete bookkeeping tasks.

  Original:

  ```text
  The trouble is the glue. Which workspace pairs with which terminal? Which bookmark names which chain? Which agent is waiting on what? All of it lives in the engineer's head, and the tax compounds with every added line of work:

  - **Where is that work?** Nothing maps a half-remembered change to the workspace that holds it.
  - **Who needs me right now?** An agent blocked on a permission prompt in terminal three looks exactly like an agent making progress.
  - **What is in flight?** There is no single view of the tree of work; assembling one means visiting every terminal.
  - **Another one is a ritual.** New workspace, `cd`, new terminal, name it, create the bookmark, launch the agent: every time, by hand.
  - **Staleness is homework.** Keeping N workspaces current against a moving trunk, and against each other, is a [rebase](appendix-a-glossary.md#ext-rebase)-and-[conflict](appendix-a-glossary.md#ext-conflict) chore that grows with N.
  - **`jj log` stops scaling.** Every workspace's revisions interleave in one log; finding your own chain means scrolling past everyone else's.
  - **A second machine multiplies all of it.** The state lives in one machine's terminal server and filesystem, so moving between machines means rebuilding the picture by hand.

  kiki's move is to register the hand-maintained tuple (workspace, terminal, agent, bookmark) as one durable object with a name: the **[thread](appendix-a-glossary.md#thread)**.
  ```

  Replacement:

  ```text
  Managing the connections between these tools takes repeated work:

  - Find the workspace that contains a particular change.
  - Check whether an agent is working or waiting for a permission prompt.
  - Visit the terminals to see all work in progress.
  - Create a workspace, terminal, bookmark, and agent session for each new task.
  - Keep workspaces current as their parent revisions change, including any
    [rebases](appendix-a-glossary.md#ext-rebase) and
    [conflicts](appendix-a-glossary.md#ext-conflict).
  - Find the relevant chain in a `jj log` that includes every workspace's revisions.
  - Rebuild this view when moving to another machine, because the terminal and
    filesystem state are local.

  Kiki records each workspace, terminal, agent, and bookmark together as a named,
  persistent [thread](appendix-a-glossary.md#thread).
  ```

- Edit 13: Remove abstract first-class framing and metaphorical ownership.

  Original:

  ```text
  Once the tuple is a first-class thing that a [daemon](appendix-a-glossary.md#ext-daemon) (a background program) watches, each friction has an owner:
  ```

  Replacement:

  ```text
  A [daemon](appendix-a-glossary.md#ext-daemon), or background program, watches the registered threads and handles this bookkeeping:
  ```

- Edit 14: State the creation steps instead of calling them a ritual.

  Original:

  ```text
  `kk new <name>` runs the whole ritual (workspace, initial change, bookmark checkpoint, hooks, terminal group, agent) as one durable, crash-recoverable [saga](appendix-a-glossary.md#saga).
  ```

  Replacement:

  ```text
  `kk new <name>` creates the workspace, initial change, bookmark checkpoint, hooks, terminal group, and agent through one durable, crash-recoverable [saga](appendix-a-glossary.md#saga).
  ```

- Edit 15: Replace vague emphasis and personification with the conditions requiring help.

  Original:

  ```text
  It interrupts the human only for true ambiguity: textual conflicts, or topology it refuses to guess through.
  ```

  Replacement:

  ```text
  It asks the human to resolve textual conflicts or ambiguous revision topology.
  ```

- Edit 16: Cut an unsupported claim about the shape of all work.

  Original:

  ```text
  Because a thread can follow another thread, the flat sibling picture above generalizes to the shape work actually takes, a tree:
  ```

  Replacement:

  ```text
  Follows relationships can connect the threads into a tree:
  ```

- Edit 17: Use a direct description of the linked document.

  Original:

  ```text
  For a scene-by-scene dramatization of the whole workflow, see the [storyboard](10-interface/storyboard.md).
  ```

  Replacement:

  ```text
  The [storyboard](10-interface/storyboard.md) walks through the workflow.
  ```

- Edit 18: Replace a broad promise and inflated contrast with the task kiki performs.

  Original:

  ```text
  The point is to make parallel work cheap. Today, switching between agent-led lines of work means stashes, branches, rebases, lost terminals, and rebuilt context. kiki runs the coordination in the background instead:
  ```

  Replacement:

  ```text
  Kiki tracks work that would otherwise require checking terminals and revision histories by hand:
  ```

- Edit 19: Replace a slogan with the rule; retain the following security limitation.

  Original:

  ```text
  **Threads keep each other out of the way, not out.**
  ```

  Replacement:

  ```text
  **Workspaces separate edits.**
  ```

- Edit 20: Name the safety requirement instead of using a slogan.

  Original:

  ```text
  **Safety beats eagerness.**
  ```

  Replacement:

  ```text
  **Workspace changes wait for a safe boundary.**
  ```

- Edit 21: Replace the table label with a concrete task.

  Original:

  ```text
  Another one is a ritual
  ```

  Replacement:

  ```text
  Starting another task
  ```

- Edit 22: Replace a metaphorical table label.

  Original:

  ```text
  Staleness is homework
  ```

  Replacement:

  ```text
  Updating stale workspaces
  ```

### docs/.vitepress/theme/KikiHome.vue

Full rewritten file: [docs/.vitepress/theme/KikiHome.vue](../../../../docs/.vitepress/theme/KikiHome.vue).

- Edit 23: Replace a decorative aside with the recorded relationship.

  Original:

  ```text
  follow edge recorded — related in history
  ```

  Replacement:

  ```text
  follow edge recorded between the threads
  ```

- Edit 24: Replace a formulaic contrast with the user action.

  Original:

  ```text
  be additive, not invasive
  ```

  Replacement:

  ```text
  keep using your tools
  ```

- Edit 25: State the shared authority rule directly.

  Original:

  ```text
  The gRPC service is the product surface. CLI and TUI are clients, not privileged exceptions.
  ```

  Replacement:

  ```text
  The CLI and TUI use the same gRPC service and follow the same access rules.
  ```

- Edit 26: Replace a slogan with the intended behavior.

  Original:

  ```text
  fail loud, not silent
  ```

  Replacement:

  ```text
  report uncertain state
  ```

- Edit 27: Remove personification while keeping the uncertainty rule.

  Original:

  ```text
  When the system cannot determine the right action, it stops and asks rather than guessing.
  ```

  Replacement:

  ```text
  When kiki cannot determine the next action, it stops and asks for a human decision.
  ```

- Edit 28: Replace a compressed string of technical nouns with actions.

  Original:

  ```text
  Thread atom, recoverable lifecycle, linear live-follow cascade, batch-safe delivery, and projection repair.
  ```

  Replacement:

  ```text
  Create and recover threads, coordinate updates along linear revision chains, deliver context safely, and repair mismatches.
  ```

- Edit 29: Replace a vague roadmap label.

  Original:

  ```text
  "the substrate"
  ```

  Replacement:

  ```text
  "more integrations"
  ```

- Edit 30: Replace absolute marketing promises with supported properties.

  Original:

  ```text
  'without the stash.',
              'without the rebase.',
              'without losing context.',
  ```

  Replacement:

  ```text
  'in separate workspaces.',
              'with linked threads.',
              'with tracked dependencies.',
  ```

- Edit 31: Remove an unqualified harness promise; the v1 spec supports only these two.

  Original:

  ```text
  ['Claude Code', 'Codex', 'bring your own']
  ```

  Replacement:

  ```text
  ['Claude Code', 'Codex']
  ```

- Edit 32: Replace a metaphor and invented timing with the bookkeeping problem.

  Original:

  ```text
  The friction is in the seams. You stash, you switch branches, and three minutes later the
            original branch is a state you have to reconstruct — and the agent has lost the thread.
  ```

  Replacement:

  ```text
  Several agents can work at once, but you still have to track their workspaces, terminals,
            and revision chains. Switching tasks means finding where each agent left off.
  ```

- Edit 33: Replace broad assertions and hyperbole with a concrete dependency example.

  Original:

  ```text
  Multiply that by three or four lines of inquiry in flight and the cost of opening another
            becomes prohibitive. But refactoring a function and migrating its callers is not a
            sequential task; it is a tree of work. The right tool lets those branches exist in
            parallel without worktrees colliding or people manually rebasing the world.
  ```

  Replacement:

  ```text
  A refactor may have separate tasks for tests and callers. When the shared code changes,
            those tasks need updated files and an explanation of what moved. Kiki tracks the
            dependencies and coordinates those updates.
  ```

- Edit 34: Give the project status instead of a generic aspiration.

  Original:

  ```text
  <p>kiki is an attempt to build that tool.</p>
  ```

  Replacement:

  ```text
  <p>The design is written. Implementation has not started.</p>
  ```

- Edit 35: Explain a thread without a compressed slogan.

  Original:

  ```text
  A themed sequence of jj revisions with a live head, one workspace, one terminal group, and
            one agent. Isolated on disk, related in history.
  ```

  Replacement:

  ```text
  A named line of work with a live jj head, a workspace, a terminal group, and an agent.
            Each thread edits its own files and can follow related threads.
  ```

- Edit 36: Replace vague topology language and personification with the condition.

  Original:

  ```text
  telling the agent. Never mid-edit. Ambiguous topology stops for a human instead of
            guessing.
  ```

  Replacement:

  ```text
  telling the agent. It does not change files mid-edit. If the revision relationships are
            ambiguous, kiki stops for a human decision.
  ```

- Edit 37: Describe the commands actually shown instead of a counted slogan.

  Original:

  ```text
  Spawn, relate, inspect, switch, publish, close. Six verbs.
  ```

  Replacement:

  ```text
  Create two related threads, inspect them, switch to one, and close it.
  ```

- Edit 38: Remove editorial scaffolding.

  Original:

  ```text
  Stated up front, because the reference book’s coherence depends on them.
  ```

  Replacement:

  ```text
  These rules guide the implementation.
  ```

- Edit 39: Use plain language for the scope source.

  Original:

  ```text
  The canonical scope ledger lives in the book’s Orientation chapter.
  ```

  Replacement:

  ```text
  The Orientation chapter defines what ships in each release.
  ```

- Edit 40: Preserve the name and personality while cutting inflated symbolism.

  Original:

  ```text
  <strong>kk</strong> sits on the home row immediately beside <strong>jj</strong>, a quiet
            acknowledgement that one tool works underneath the other. And a kiki is a gathering where
            everyone shows up as themselves and the room is richer for the multiplicity. 💅🏾
  ```

  Replacement:

  ```text
  <strong>kk</strong> sits beside <strong>jj</strong> on the keyboard’s home row. The names
            reflect how the tools work together. A kiki is a gathering, which fits a project about
            several agents and a person working together. 💅🏾
  ```

- Edit 41: Remove a contradictory contrast about a settled design.

  Original:

  ```text
  The spec is settled; the code is not. Feedback filed now changes the design.
  ```

  Replacement:

  ```text
  Implementation has not started. Feedback can still change the design.
  ```

### docs/reference/book/10-interface/README.md

Full rewritten file: [docs/reference/book/10-interface/README.md](../../../../docs/reference/book/10-interface/README.md).

- Edit 42: Use a direct sentence to introduce the reference list.

  Original:

  ```text
  [Specification](spec.md) — the rules for every surface. It covers:
  ```

  Replacement:

  ```text
  [Specification](spec.md) defines the rules for each part of the interface. It covers:
  ```

- Edit 43: Replace the decorative separator and vague end-to-end label.

  Original:

  ```text
  [Storyboard](storyboard.md) — one developer's end-to-end story.
  ```

  Replacement:

  ```text
  [Storyboard](storyboard.md) follows one developer through a project.
  ```

- Edit 44: Replace a movie metaphor with the document precedence rule.

  Original:

  ```text
  The specification is the rulebook; the storyboard is the movie. When they disagree, the specification wins, and the storyboard has the bug.
  ```

  Replacement:

  ```text
  If the storyboard disagrees with the specification, correct the storyboard. The specification is authoritative.
  ```

- Edit 45: Remove a repeated metaphor while keeping the exact restriction.

  Original:

  ```text
  The storyboard invents nothing: no new commands, flags, output strings, glyphs, or screen elements. Every beat in it (every step of the story) traces back to one of these:
  ```

  Replacement:

  ```text
  Every command, flag, output string, glyph, and screen element in the storyboard must come from these chapters:
  ```

- Edit 46: State the instruction directly.

  Original:

  ```text
  If a beat seems to need behavior the rest of the book does not authorize, that is a bug to report. It is not permission to extend the interface.
  ```

  Replacement:

  ```text
  Report any step that requires behavior the rest of the book does not authorize. Do not extend the interface to make the example work.
  ```

### docs/reference/book/10-interface/storyboard.md

Full rewritten file: [docs/reference/book/10-interface/storyboard.md](../../../../docs/reference/book/10-interface/storyboard.md).

- Edit 47: Cut unnecessary narrative framing.

  Original:

  ```text
  The protagonist is unnamed. The work is to port the iOS Kestrel app to Android.
  ```

  Replacement:

  ```text
  The developer is porting the iOS Kestrel app to Android.
  ```

- Edit 48: Replace theatrical and abstract language with the requirement.

  Original:

  ```text
  Every beat in it grounds out in the normative (binding) chapters:
  ```

  Replacement:

  ```text
  Every step must follow the chapters that define behavior:
  ```

- Edit 49: Replace an unexplained metaphor.

  Original:

  ```text
  Where a beat is load-bearing, it cites the chapter that authorizes it.
  ```

  Replacement:

  ```text
  Each step that depends on a specific rule cites the chapter that defines it.
  ```

- Edit 50: Remove metaphor and abstract process language.

  Original:

  ```text
  Where a beat would require behavior the rest of the book does not authorize, that gap is a finding. It is not a license to extend the surface here.
  ```

  Replacement:

  ```text
  Report steps that require behavior outside the specification. Do not add interface behavior to make the example work.
  ```

- Edit 51: Give the reason for the choice instead of a vague endorsement.

  Original:

  ```text
  With one thread there is no tree worth pinning. So the developer leaves the optional UI pane off for now
  ```

  Replacement:

  ```text
  With only one thread, the sidebar is enough, so the developer leaves the optional UI pane off for now
  ```

- Edit 52: Replace first-class framing with the observed behavior.

  Original:

  ```text
  Both demonstrate that direct `jj` operations are first-class inputs to the coordinator, not gated by it.
  ```

  Replacement:

  ```text
  Both show kiki responding to direct `jj` operations without blocking them.
  ```

### docs/reference/book/11-configuration.md

Full rewritten file: [docs/reference/book/11-configuration.md](../../../../docs/reference/book/11-configuration.md).

- Edit 53: Replace an extended analogy with the precedence rule.

  Original:

  ```text
  It is also layered: several sources stack on top of each other, and higher layers win. Think of a stack of transparency sheets: the topmost sheet with a value written on it is the one you see.
  ```

  Replacement:

  ```text
  Settings can come from several sources. For each key, the highest-priority source that sets it determines the value.
  ```

- Edit 54: Replace a rhetorical question and metaphor with the inspection requirement.

  Original:

  ```text
  Configuration must answer two questions clearly: what value is effective, and where did it come from. Anything else is a tax the user pays every time they debug a machine they forgot they configured.
  ```

  Replacement:

  ```text
  Configuration inspection must show each effective value and the source that set it. This lets users trace an unexpected setting.
  ```

- Edit 55: Use a direct description of the required behavior.

  Original:

  ```text
  cannot just be applied
  ```

  Replacement:

  ```text
  cannot take effect immediately
  ```

### docs/reference/book/02-invariants.md

Full rewritten file: [docs/reference/book/02-invariants.md](../../../../docs/reference/book/02-invariants.md).

- Edit 56: Replace a moral description with the required state.

  Original:

  ```text
  a persisted journal and an honest lifecycle state.
  ```

  Replacement:

  ```text
  a persisted journal and a lifecycle state that reflects the completed steps.
  ```

- Edit 57: Remove personification while preserving the rule.

  Original:

  ```text
  It does not pretend direct human commands are gated.
  ```

  Replacement:

  ```text
  It does not gate direct human commands.
  ```

### docs/reference/book/03-threads.md

Full rewritten file: [docs/reference/book/03-threads.md](../../../../docs/reference/book/03-threads.md).

- Edit 58: State what makes the error clear.

  Original:

  ```text
  Unsupported harness names error clearly.
  ```

  Replacement:

  ```text
  An unsupported harness name returns a clear error.
  ```

- Edit 59: Name the validation outcome.

  Original:

  ```text
  They either leave one valid chain or make validation stop loud.
  ```

  Replacement:

  ```text
  They either leave one valid chain or cause validation to report an error.
  ```

- Edit 60: Replace reassurance and dismissive wording with the preservation rule.

  Original:

  ```text
  Close is intentionally boring. You should be able to close a thread confident that tracked work survives and that local junk is not silently swept away.
  ```

  Replacement:

  ```text
  Close preserves tracked work and does not silently delete local files that jj does not track.
  ```

- Edit 61: Remove personification from a precondition.

  Original:

  ```text
  It does not pretend a complete owned stack exists.
  ```

  Replacement:

  ```text
  It does not assume a complete owned stack exists.
  ```

- Edit 62: Remove personification while preserving the rule.

  Original:

  ```text
  jj does not leave a bookmark alone between checkpoints, and kiki does not pretend otherwise. Five different things can happen, and kiki keeps them apart:
  ```

  Replacement:

  ```text
  A bookmark can change between checkpoints. Kiki distinguishes five cases:
  ```

### docs/reference/book/04-authority.md

Full rewritten file: [docs/reference/book/04-authority.md](../../../../docs/reference/book/04-authority.md).

- Edit 63: State the authorization limit directly.

  Original:

  ```text
  The important v1 property is narrower: a normal `kk` subprocess does not get reusable repo-wide authority just because a human ran it.
  ```

  Replacement:

  ```text
  In v1, running a normal `kk` subprocess as a human does not grant that subprocess reusable repo-wide authority.
  ```

- Edit 64: Remove an analogy that repeats the defined rule.

  Original:

  ```text
  is single-use: a single-ride ticket, not a season pass. Exactly one durable operation record claims it, atomically, before any external side effect;
  ```

  Replacement:

  ```text
  is single-use. Exactly one durable operation record claims it, atomically, before any external side effect;
  ```

### docs/reference/book/08-metadata.md

Full rewritten file: [docs/reference/book/08-metadata.md](../../../../docs/reference/book/08-metadata.md).

- Edit 65: Make the deferred status explicit.

  Original:

  ```text
  kiki may eventually help keep three kinds of text current as work changes:
  ```

  Replacement:

  ```text
  The planned metadata features would keep three kinds of text current as work changes:
  ```

- Edit 66: Remove an analogy that adds no information to the ownership rule.

  Original:

  ```text
  The ledger works like a sign-out sheet: kiki may only edit prose it can prove it wrote last.
  ```

  Replacement:

  ```text
  Kiki may only edit prose it can prove it wrote last.
  ```

### docs/reference/book/09-commands.md

Full rewritten file: [docs/reference/book/09-commands.md](../../../../docs/reference/book/09-commands.md).

- Edit 67: Use a direct description of the required behavior.

  Original:

  ```text
  must error with an actionable message
  ```

  Replacement:

  ```text
  must return an error explaining how to proceed
  ```

### docs/reference/book/13-architecture/crates.md

Full rewritten file: [docs/reference/book/13-architecture/crates.md](../../../../docs/reference/book/13-architecture/crates.md).

- Edit 68: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  The split exists so the [gRPC](https://grpc.io/) service surface is a real seam. A seam is a clean boundary between parts. [`kkd`](../appendix-a-glossary.md#kkd) is the only privileged process, and every UI is a client of the same protocol.
  ```

  Replacement:

  ```text
  The [gRPC](https://grpc.io/) service separates privileged operations from clients. [`kkd`](../appendix-a-glossary.md#kkd) is the only privileged process, and every UI uses the same protocol.
  ```

- Edit 69: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  pending the first real `kkd` commit
  ```

  Replacement:

  ```text
  until implementation of `kkd` begins
  ```

### docs/reference/book/13-architecture/terminal-runtime.md

Full rewritten file: [docs/reference/book/13-architecture/terminal-runtime.md](../../../../docs/reference/book/13-architecture/terminal-runtime.md).

- Edit 70: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  Each module has a real second adapter (a second implementation): an in-process fake that drives the deep-module tests. Because the second adapter really exists, each interface is a real seam, not a speculative one. A seam is a place where one implementation can be swapped for another.
  ```

  Replacement:

  ```text
  Each module has two implementations: the production adapter and an in-process fake used by the deep-module tests. Running both through the same interface tests whether implementations can be swapped without changing their callers.
  ```

- Edit 71: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  It exists so that a single-viewer setup works today without pretending to be local.
  ```

  Replacement:

  ```text
  A single-viewer setup can use it, with the explicit understanding that it moves all attached clients.
  ```

### docs/reference/book/13-architecture/op-log-watcher.md

Full rewritten file: [docs/reference/book/13-architecture/op-log-watcher.md](../../../../docs/reference/book/13-architecture/op-log-watcher.md).

- Edit 72: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  It does not pretend repository evolution occurred one hop at a time.
  ```

  Replacement:

  ```text
  It does not assume repository evolution occurred one hop at a time.
  ```

### docs/reference/book/13-architecture/harness-adapter.md

Full rewritten file: [docs/reference/book/13-architecture/harness-adapter.md](../../../../docs/reference/book/13-architecture/harness-adapter.md).

- Edit 73: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  kiki's delivery protocol is written in terms of model turns and tool batches. This section says how the Codex adapter maps Codex's events onto those terms, and what must be proved for each mapping.
  ```

  Replacement:

  ```text
  The Codex adapter maps Codex's events onto the model turns and tool batches used by kiki's delivery protocol. Each mapping below has its own proof requirements.
  ```

### docs/reference/book/14-testing.md

Full rewritten file: [docs/reference/book/14-testing.md](../../../../docs/reference/book/14-testing.md).

- Edit 74: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  If exit cannot be verified, the files stay and the lifecycle fails loudly.
  ```

  Replacement:

  ```text
  If exit cannot be verified, the files stay and the lifecycle reports a failure.
  ```

- Edit 75: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  Some parts can only be tested for real, against the actual programs. These are smoke-tested or integration-tested:
  ```

  Replacement:

  ```text
  These integrations require smoke tests or integration tests that run against the programs or OS facilities themselves:
  ```

### docs/reference/book/15-build-sequencing.md

Full rewritten file: [docs/reference/book/15-build-sequencing.md](../../../../docs/reference/book/15-build-sequencing.md).

- Edit 76: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  It should answer one question: is the hardest coordination primitive real?
  ```

  Replacement:

  ```text
  It should demonstrate safe cascade reconciliation and context delivery for each harness.
  ```

### docs/reference/book/appendix-b-user-stories.md

Full rewritten file: [docs/reference/book/appendix-b-user-stories.md](../../../../docs/reference/book/appendix-b-user-stories.md).

- Edit 77: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  is real rather than configuration-order folklore.
  ```

  Replacement:

  ```text
  does not depend on hook configuration order.
  ```

- Edit 78: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  follow my checkpoint bookmark through jj's own rewrite successors without complaint, and to catch real projection problems,
  ```

  Replacement:

  ```text
  follow my checkpoint bookmark through jj's own rewrite successors and detect projection failures,
  ```

- Edit 79: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  leaves an honest repairable state.
  ```

  Replacement:

  ```text
  leaves a recorded state that supports repair.
  ```

- Edit 80: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  gracefully degrade to proof-carrying restart+resume for context delivery, so that the tool still works, just less smoothly.
  ```

  Replacement:

  ```text
  fall back to proof-carrying restart+resume for context delivery, so that delivery can continue at the cost of restarting the agent.
  ```

- Edit 81: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  I want the trust model documented honestly.
  ```

  Replacement:

  ```text
  I want the trust model to state its protections and limits.
  ```

- Edit 82: Replace inflated or figurative phrasing with the concrete behavior.

  Original:

  ```text
  This does not pretend that the terminal runtime participates in a database transaction.
  ```

  Replacement:

  ```text
  The saga does not assume that a database transaction can include terminal-runtime operations.
  ```

- Edit 83: Remove personification while preserving the rule.

  Original:

  ```text
  Kiki does not pretend that A's [bookmark](appendix-a-glossary.md#bookmark) automatically followed `jj new`.
  ```

  Replacement:

  ```text
  Kiki does not assume that A's [bookmark](appendix-a-glossary.md#bookmark) automatically followed `jj new`.
  ```

### docs/reference/book/17-decisions/codex-adapter.md

Full rewritten file: [docs/reference/book/17-decisions/codex-adapter.md](../../../../docs/reference/book/17-decisions/codex-adapter.md).

- Edit 84: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  That rested on the assumption that Codex had no hook surface worth building a boundary on.
  ```

  Replacement:

  ```text
  That rested on the assumption that Codex had no hook API that could enforce the required boundary.
  ```

- Edit 85: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  The deferral was a statement about Codex's hook surface, not about kiki's architecture. That surface changed. Codex now ships a lifecycle-hook system with these parts:
  ```

  Replacement:

  ```text
  Codex's lifecycle-hook system changed after that deferral. It now has these parts:
  ```

- Edit 86: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  Every one of them now exists to be proven rather than approximated.
  ```

  Replacement:

  ```text
  The new hooks provide a candidate for each requirement. The integration gate still has to prove that each one works.
  ```

- Edit 87: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  Meanwhile nothing in the protocol was ever Claude-shaped. [`PreToolUse` and `PostToolBatch`](../appendix-a-glossary.md#pretooluse-posttoolbatch-hooks) are kiki's entry points. [`SoftBatch`](../appendix-a-glossary.md#softbatch-delivery-proof) binds an [incarnation](../appendix-a-glossary.md#incarnation), [model turn](../appendix-a-glossary.md#model-turn), and [tool batch](../appendix-a-glossary.md#tool-batch) without caring how the harness spells them. Deferring Codex bought no simplification beyond one fewer integration gate.
  ```

  Replacement:

  ```text
  Kiki's protocol already supports multiple harnesses. [`PreToolUse` and `PostToolBatch`](../appendix-a-glossary.md#pretooluse-posttoolbatch-hooks) are its entry points. [`SoftBatch`](../appendix-a-glossary.md#softbatch-delivery-proof) binds an [incarnation](../appendix-a-glossary.md#incarnation), [model turn](../appendix-a-glossary.md#model-turn), and [tool batch](../appendix-a-glossary.md#tool-batch); each adapter maps its harness's events to those terms. Deferring Codex removed one integration gate but did not simplify the protocol.
  ```

- Edit 88: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  Codex's hard case is the opposite. It dispatches the tool calls of a [model turn](../appendix-a-glossary.md#model-turn) serially (one at a time) and has no batch-completion event. So the question is what a "batch" even is.
  ```

  Replacement:

  ```text
  Codex dispatches the tool calls of a [model turn](../appendix-a-glossary.md#model-turn) serially (one at a time) and has no batch-completion event. Its adapter therefore needs a different way to identify a batch and its completion.
  ```

- Edit 89: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  The answer keeps the protocol untouched: `parallel_batch_boundary` requires an unambiguous boundary, not parallelism.
  ```

  Replacement:

  ```text
  The `parallel_batch_boundary` capability requires an unambiguous batch boundary. Tool calls need not run in parallel.
  ```

- Edit 90: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  The proof is version-scoped on purpose. A Codex version that starts dispatching concurrently without a provable completion boundary silently loses nothing. It loses the capability at the next incarnation check and runs with `RestartStartup` delivery only.
  ```

  Replacement:

  ```text
  The proof applies to one Codex version. If a version starts dispatching concurrently without a provable completion boundary, the next incarnation check removes the capability. That version runs with `RestartStartup` delivery only.
  ```

- Edit 91: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  Completion and consumption each took three attempts to get right, and the failures are worth recording.
  ```

  Replacement:

  ```text
  The completion design went through three approaches. The first two failed because they could not provide evidence after a denied call or a hook crash.
  ```

- Edit 92: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  1. The obvious completion mapping is the single call's `PostToolUse` event. It is wrong for exactly the case that matters. A blocked call is denied. A denied call never executes. A call that never executes fires no post-tool event. So soft delivery would wait forever on a proof that structurally cannot arrive.
  ```

  Replacement:

  ```text
  1. The first approach used the single call's `PostToolUse` event. A denied call never executes and fires no post-tool event, so soft delivery would wait forever for completion evidence.
  ```

- Edit 93: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  3. What actually survives a hook crash is the harness's next event.
  ```

  Replacement:

  ```text
  3. The third approach uses the harness's next event, which can arrive even after a hook crash.
  ```

- Edit 94: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  Consumption has the same trap one layer deeper.
  ```

  Replacement:

  ```text
  Recording that a hook wrote a result does not prove the model received it.
  ```

- Edit 95: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  Such a hook writes into a void while the model receives a substituted result.
  ```

  Replacement:

  ```text
  The harness then gives the model a substituted result.
  ```

- Edit 96: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  The proof that closes the gap is the harness's own bookkeeping.
  ```

  Replacement:

  ```text
  The harness's session record provides the missing evidence.
  ```

- Edit 97: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  A receipt that keeps coming back contrary is no longer a transient. It is evidence the deny channel itself rejects this payload on this version. Redelivering down a channel proven defective is an infinite loop wearing a retry's clothes.
  ```

  Replacement:

  ```text
  A second contrary receipt is evidence that this version's deny channel rejects the payload. Repeated retries would keep using the same failed delivery path.
  ```

- Edit 98: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  Bounded restart attempts that keep failing their handshake stop loud rather than looping:
  ```

  Replacement:

  ```text
  When the bounded restart attempts exhaust their handshake retries,
  ```

- Edit 99: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  The bound obeys the same single-authority rule as everything else on the intent. Attempts and exhaustion are durable intent state, written in the transactions that make them. An in-memory retry counter is a loop that merely waits for a [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) restart to forget it.
  ```

  Replacement:

  ```text
  Attempts and exhaustion are durable intent state, written in the transactions that make them. An in-memory retry counter would reset on a [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) restart and allow retries beyond the bound.
  ```

- Edit 100: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  A dead end that only a human can enter must be one a human can leave. `kk repair` gives an [exhausted intent](../appendix-a-glossary.md#exhausted-intent) exactly two exits:
  ```

  Replacement:

  ```text
  A human can use `kk repair` to resolve an [exhausted intent](../appendix-a-glossary.md#exhausted-intent) in exactly two ways:
  ```

- Edit 101: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  "After the re-arm" is exactly the kind of wall-clock ordering the rest of the book refuses to trust. The epoch id makes the fresh cycle unambiguous under skew, rollback, or restart.
  ```

  Replacement:

  ```text
  A wall-clock timestamp cannot reliably identify the fresh cycle under clock skew, rollback, or restart. The epoch id can.
  ```

- Edit 102: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  Claude Code's exclusivity story needs two mechanisms because its settings sources always layer:
  ```

  Replacement:

  ```text
  Claude Code needs two mechanisms to enforce hook exclusivity because its settings sources always layer:
  ```

- Edit 103: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  The relocation has one sharp edge: `CODEX_HOME` also moves authentication.
  ```

  Replacement:

  ```text
  Changing `CODEX_HOME` also changes where Codex looks for authentication.
  ```

- Edit 104: Replace rhetorical framing with the protocol requirement or failure condition.

  Original:

  ```text
  A launch that would fall back to the user's real home for auth is a failed proof, not a convenience.
  ```

  Replacement:

  ```text
  A launch that would fall back to the user's real home for authentication fails the isolation proof.
  ```

### docs/reference/book/17-decisions/native-evolution.md

Full rewritten file: [docs/reference/book/17-decisions/native-evolution.md](../../../../docs/reference/book/17-decisions/native-evolution.md).

- Edit 105: Describe multi-workspace evolution directly.

  Original:

  ```text
  Repository evolution does not pretend to move one [follows edge](../appendix-a-glossary.md#follows-edge) at a time. A single jj operation may logically evolve B and C in A→B→C.
  ```

  Replacement:

  ```text
  A single jj operation may logically evolve B and C in A→B→C, across several [follows edges](../appendix-a-glossary.md#follows-edge) at once.
  ```

### docs/reference/book/05-cascade.md

Full rewritten file: [docs/reference/book/05-cascade.md](../../../../docs/reference/book/05-cascade.md).

- Edit 106: State the behavior directly and remove unnecessary emphasis.

  Original:

  ```text
  So an operation, or its absence, is not freshness evidence. kiki discovers actual workspace freshness at the next managed boundary. It does not pretend every [materialization](appendix-a-glossary.md#materialization), every actual change to on-disk files, shows up in the op log, jj's record of repository operations.
  ```

  Replacement:

  ```text
  An operation, or its absence, is not freshness evidence. Kiki checks workspace freshness at the next managed boundary. A [materialization](appendix-a-glossary.md#materialization) changes files on disk but does not always appear in the op log, jj's record of repository operations.
  ```

- Edit 107: State the behavior directly and remove unnecessary emphasis.

  Original:

  ```text
  Recovery is deliberately loud:
  ```

  Replacement:

  ```text
  Recovery pauses the agent and preserves the files at risk:
  ```

- Edit 108: State the behavior directly and remove unnecessary emphasis.

  Original:

  ```text
  Everything below exists to keep that sequence honest when batches are concurrent, hooks crash, harnesses differ, or the workspace holds unsnapshotted edits.
  ```

  Replacement:

  ```text
  The rules below preserve that sequence when batches run concurrently, hooks crash, harnesses differ, or the workspace holds unsnapshotted edits.
  ```

- Edit 109: State the behavior directly and remove unnecessary emphasis.

  Original:

  ```text
  So clock skew cannot smuggle a stale attempt into the fresh cycle, or a fresh one out of it.
  ```

  Replacement:

  ```text
  Clock skew therefore cannot change which cycle an attempt belongs to.
  ```

### docs/reference/book/06-transcript.md

Full rewritten file: [docs/reference/book/06-transcript.md](../../../../docs/reference/book/06-transcript.md).

- Edit 110: State the behavior directly and remove unnecessary emphasis.

  Original:

  ```text
  The [thread transcript](appendix-a-glossary.md#thread-transcript) is a local recall surface. It is a searchable record of conversational text written by the human, by the agent, and by kiki itself.
  ```

  Replacement:

  ```text
  The [thread transcript](appendix-a-glossary.md#thread-transcript) is a local, searchable record of conversational text written by the human, the agent, and kiki.
  ```

### docs/reference/book/13-architecture/daemon.md

Full rewritten file: [docs/reference/book/13-architecture/daemon.md](../../../../docs/reference/book/13-architecture/daemon.md).

- Edit 111: State the behavior directly and remove unnecessary emphasis.

  Original:

  ```text
  Reconciliation means comparing kiki's records with what really exists.
  ```

  Replacement:

  ```text
  Reconciliation means comparing kiki's records with the observed resources.
  ```

### docs/reference/book/13-architecture/schema.md

Full rewritten file: [docs/reference/book/13-architecture/schema.md](../../../../docs/reference/book/13-architecture/schema.md).

- Edit 112: State the behavior directly and remove unnecessary emphasis.

  Original:

  ```text
  ## Constraints and transactional invariants worth calling out
  ```

  Replacement:

  ```text
  <a id="constraints-and-transactional-invariants-worth-calling-out"></a>

  ## Constraints and transactional invariants
  ```

### docs/reference/book/appendix-a-glossary.md

Full rewritten file: [docs/reference/book/appendix-a-glossary.md](../../../../docs/reference/book/appendix-a-glossary.md).

- Edit 113: State the behavior directly and remove unnecessary emphasis.

  Original:

  ```text
  This appendix defines the important terms in kiki's reference.
  ```

  Replacement:

  ```text
  This appendix defines the terms used in kiki's reference.
  ```

- Edit 114: State the behavior directly and remove unnecessary emphasis.

  Original:

  ```text
  kiki does not guess its way through merge commits, multiple candidate roots, or foreign topology. Those cases produce [`TopologyDiverged`](#topologydiverged) and need a human choice.
  ```

  Replacement:

  ```text
  Merge commits, multiple candidate roots, or foreign topology produce [`TopologyDiverged`](#topologydiverged) and need a human choice.
  ```

### docs/research/herdr-jj.md

Full rewritten file: [docs/research/herdr-jj.md](../../../../docs/research/herdr-jj.md).

- Edit 115: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  The most useful first foundation for kiki is its terminal runtime, agent display, and CLI/socket interface.
  ```

  Replacement:

  ```text
  Kiki can reuse its terminal runtime, agent display, and CLI/socket interface.
  ```

- Edit 116: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  This is the strongest existing reuse seam.
  ```

  Replacement:

  ```text
  Kiki can call these operations without replacing Herdr's frontend.
  ```

- Edit 117: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  they simply do not establish kiki's stronger guarantees.
  ```

  Replacement:

  ```text
  they do not establish the guarantees kiki requires.
  ```

- Edit 118: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  `WorkspaceProbe` and `WorkspaceRecovery` remain hard implementation work, including untracked files, ignored files, sparse checkouts, modes, symlinks, and concurrent writers.
  ```

  Replacement:

  ```text
  `WorkspaceProbe` and `WorkspaceRecovery` still need implementations that handle untracked files, ignored files, sparse checkouts, modes, symlinks, and concurrent writers.
  ```

- Edit 119: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  configuration, and CLI machinery;
  ```

  Replacement:

  ```text
  configuration, and CLI;
  ```

### docs/research/herdr-terminal-runtime.md

Full rewritten file: [docs/research/herdr-terminal-runtime.md](../../../../docs/research/herdr-terminal-runtime.md).

- Edit 120: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  it owns real PTYs,
  ```

  Replacement:

  ```text
  it hosts PTYs,
  ```

- Edit 121: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  The strongest reason to choose it is the integrated agent interface and recovery experience.
  ```

  Replacement:

  ```text
  Its agent interface and recovery features are reasons to choose it.
  ```

- Edit 122: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  It adds real lifecycle tests and a tmux baseline
  ```

  Replacement:

  ```text
  It adds process lifecycle tests and a tmux baseline
  ```

- Edit 123: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  Track the actual launcher/harness incarnation independently of terminal IDs.
  ```

  Replacement:

  ```text
  Track the launcher/harness incarnation independently of terminal IDs.
  ```

- Edit 124: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  A robust adapter needs verified server-instance evidence and process start identity.
  ```

  Replacement:

  ```text
  The adapter needs to verify the server instance and process start identity.
  ```

### journal/decisions/0003-use-jj-and-shared-agent-guidance.md

Full rewritten file: [journal/decisions/0003-use-jj-and-shared-agent-guidance.md](../../../decisions/0003-use-jj-and-shared-agent-guidance.md).

- Edit 125: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  Initializing jj makes the documented workflow real.
  ```

  Replacement:

  ```text
  Initializing jj lets contributors use the documented workflow.
  ```

### journal/decisions/0006-close-repair-and-proof-gaps.md

Full rewritten file: [journal/decisions/0006-close-repair-and-proof-gaps.md](../../../decisions/0006-close-repair-and-proof-gaps.md).

- Edit 126: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  The new plans and the `[timeouts]` table add surface to `kk repair` and to
  configuration.
  ```

  Replacement:

  ```text
  The new plans add options to `kk repair`, and the `[timeouts]` table adds
  configuration settings.
  ```

### journal/decisions/README.md

Full rewritten file: [journal/decisions/README.md](../../../decisions/README.md).

- Edit 127: Replace general praise or abstract wording with a concrete capability or requirement.

  Original:

  ```text
  Surface a disagreement and reconcile the
  owning chapter;
  ```

  Replacement:

  ```text
  Report a disagreement and update the
  chapter that defines the behavior;
  ```

### docs/reference/book/16-roadmap.md

Full rewritten file: [docs/reference/book/16-roadmap.md](../../../../docs/reference/book/16-roadmap.md).

- Edit 128: Replace a forced contrast and metaphor with the purpose of the roadmap.

  Original:

  ```text
  This chapter records deferred surfaces whose design affects v1 boundaries. Deferred does not mean vague. It means the book draws the boundary now, so v1 does not accidentally grow half of a future substrate.
  ```

  Replacement:

  ```text
  This chapter records deferred features whose design affects v1. Defining their scope now helps keep that work out of the first release.
  ```

- Edit 129: Remove a mixed analogy that repeats the access rule.

  Original:

  ```text
  Think of the URL as the address on an envelope and the credential as the ID you show at the door: only the ID grants access.
  ```

  Replacement:

  ```text
  Only the credential grants access.
  ```

### docs/reference/book/appendix-c-naming.md

Full rewritten file: [docs/reference/book/appendix-c-naming.md](../../../../docs/reference/book/appendix-c-naming.md).

- Edit 130: Remove jargon that immediately needed a definition.

  Original:

  ```text
  Daily-driver verbs are the commands you use every day. They should be short and single-word:
  ```

  Replacement:

  ```text
  Commands used every day should have short, single-word names:
  ```

- Edit 131: Explain the naming choice without announcing its symbolism.

  Original:

  ```text
  The closeness is useful for typing. It is also a symbol: kiki works with jj and does not hide it.
  ```

  Replacement:

  ```text
  The nearby keys are easy to type, and the paired names reflect how the tools work together.
  ```

- Edit 132: Replace an abstract tone instruction with where it should apply.

  Original:

  ```text
  The name also points at kiki as a gathering: multiple lines of work, multiple agents, and a human engineer sharing a space without stepping on one another. The product should retain that spirit. It can be precise without becoming sterile.
  ```

  Replacement:

  ```text
  The name also suggests a gathering: a human engineer working with several agents on separate tasks. Keep that informal tone in the interface and documentation.
  ```
