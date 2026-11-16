# Abstract

kiki (`kk`) coordinates multi-threaded agentic coding. It binds the pieces you already use (jj workspaces, persistent terminals, and coding agents such as Claude Code and Codex) into **threads**: named, parallel lines of work that a background daemon keeps isolated, visible, and in step with the work they build on. It exists because agents made working in parallel easy while the tooling around them still assumes one line at a time, and that difference is paid for in human attention.

<TreeOfWork />

Real work branches. You chase a lead, hit a wall, back up, and try two other angles at once. Coding agents multiply this: give three of them room and by lunch you have five live lines of work. Your tools still assume a single line: one terminal, one branch, one train of thought.

Nobody designs the workflow that copes with this; you arrive at it. Push agents hard enough and you build it by hand: a jj workspace per line of work so edits never collide, a persistent terminal per workspace — a tmux session, a multiplexer workspace — so nothing dies when you look away, an agent in every terminal, a bookmark naming every chain. It works, but it leaks. Which workspace has the auth fix? Which agent has been waiting an hour for a yes? Standing up line six means another workspace, another terminal, another name, another bookmark, all by hand. Meanwhile `main` moved, five workspaces went stale, and `jj log` braids everyone's history into one long scroll.

The cost lands somewhere worse than your afternoon: it teaches you to stop branching. A dull knife changes what you cook, and expensive context switching changes what you build in the same way. The ambitious version of the work is usually a tree, and the tree is exactly what the tooling punishes.

kiki makes the tree affordable by making the thread first-class. A thread is the thing you were maintaining by hand: one line of work with its own jj workspace, its own terminal group, its own agent, its own bookmark, created in one command and visible from anywhere. The terminals live in [Herdr](https://github.com/herdrdev/herdr), a terminal multiplexer built for agent work: kiki runs one dedicated Herdr server and gives every thread a Herdr workspace in it. A thread's live tip is whatever revision its workspace sits on; jj calls that `@`. Its bookmark is a saved checkpoint, a bookmark left between pages rather than the page you are on. Threads follow threads: when a parent changes, kiki waits for a safe moment (the child's agent between actions), brings the child's files up to date, whether jj already rewrote its history or kiki must rebase its chain, and tells the agent what changed. A new branch costs a command instead of a ritual, and staying in step with a parent becomes kiki's job rather than yours.

jj, Herdr, gh, and the agent harness stay the tools underneath; kiki watches them and keeps the tree honest. This book is the contract for that layer: the vocabulary, the rules, and the machinery.
