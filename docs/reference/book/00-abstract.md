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
