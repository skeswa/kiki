# D-0011: Select a verified recovery successor by commit id

- Recorded: 2026-11-18
- Decided by: agent, in response to the owner’s request to address the open headless questions
- Topic: Headless operation
- Supersedes: —
- Superseded by: —

## Decision

When several jj successors could become visible after cascade recovery, a person or script can select one by full commit id through the existing repair command. Kiki binds that choice to the paused intent, the recovery bundle, and the exact jj operation. The choice requires one-shot approval. Every selectable result must retain the saved edits.

## Why

A policy can say who may make the choice. It cannot tell which branch of the work the caller wants. Accepting an arbitrary revision, or choosing the first successor jj lists, could hide the edits that caused kiki to pause. The same diagnosis and proof apply with and without a terminal.

## Links

[Recovery steps](../../docs/reference/book/05-cascade.md#recovery-steps) · [Repair plans](../../docs/reference/book/09-commands.md#every-issue-and-its-plan) · [D-0009](0009-operate-headless-with-a-configurable-automation-policy.md)
