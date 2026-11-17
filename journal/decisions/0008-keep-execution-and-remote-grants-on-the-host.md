# D-0008: Keep execution and remote grants on the thread's host

- Recorded: 2026-11-17
- Decided by: agent, 2026-11-17, applying the owner's request to incorporate the remote-access refinements into the kiki design
- Topic: Remote clients, portable profiles, and harness history
- Supersedes: —
- Superseded by: —

## Decision

Build on [D-0007](0007-use-portable-user-defined-profiles.md). Give each
profile a stable ID and a directory a user can bring to another device.
Each host pairs with devices and checks what each may do. The thread
stays on the host that runs it. That host records which account runs the
agent and which conversation history it may open. Start with repo summaries
over a Secure Shell (SSH) connection restricted to a kiki command.

## Why

A person can change devices while the owning daemon keeps the evidence it
needs to supervise the agent, reconcile jj changes, and protect files.
Rex shows why a terminal needs its own grant. A person who can type into
a shell can read files available to its operating system user. T3 Code
shows why the host also needs to check history. Two provider accounts can
use the same conversation directory.

The [remote design](../../docs/reference/book/13-architecture/remote-access.md)
defines the checks required before release. The
[comparison](../investigations/2026/2026-11-17-rex-t3-remote-access.md)
and [initial proposal](../investigations/2026/2026-11-17-multi-machine-access.md)
record the evidence and its limits.
