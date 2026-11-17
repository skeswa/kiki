# D-0008: Keep execution and remote grants on the thread's host

- Recorded: 2026-11-17
- Decided by: agent, 2026-11-17, applying the owner's request to incorporate the remote-access refinements into the kiki design
- Topic: Remote clients, portable profiles, and harness history
- Supersedes: —
- Superseded by: —

## Decision

Build on [D-0007](0007-use-portable-user-defined-profiles.md). Give each
profile a stable ID and a directory a user can bring to another device.
Each host enrolls devices and checks their grants for its own targets.
Keep the thread, its harness account binding, and its permitted session
history on one host. Start with summary access over restricted SSH.

## Why

A person can change devices while the owning daemon keeps the evidence it
needs to supervise the agent, reconcile jj changes, and protect files.
The Rex and T3 Code research exposed two independent sharing choices.
Access to an interactive terminal can convey an OS user's privileges.
Two provider logins can also share conversation history. Both choices
need explicit handling even when the host and profile names are familiar.

The [remote design](../../docs/reference/book/13-architecture/remote-access.md)
defines the checks required before release. The
[comparison](../investigations/2026/2026-11-17-rex-t3-remote-access.md)
and [initial proposal](../investigations/2026/2026-11-17-multi-machine-access.md)
record the evidence and its limits.
