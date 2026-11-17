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
