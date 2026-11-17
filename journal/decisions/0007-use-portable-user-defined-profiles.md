# D-0007: Let users define profiles and use them across machines

- Recorded: 2026-11-17
- Decided by: project owner, 2026-11-17, when clarifying the remote-access proposal
- Topic: Profiles in the planned remote system
- Supersedes: —
- Superseded by: —

## Decision

Users create and configure their own profiles. Personal, Work, and Friends
were examples. Users choose which machines participate in each profile and
can use the same profile across machines with different harness accounts.

## Why

A person may work on the same project from several machines and use one
machine for several projects. Their choice of name and where they work can
change independently of the account a host uses to run an agent.

The [roadmap](../../docs/reference/book/16-roadmap.md#later-architecture)
records this product requirement. Profile IDs, transfer between devices,
and host enrollment are still [design proposals](../investigations/2026/2026-11-17-multi-machine-access.md).
