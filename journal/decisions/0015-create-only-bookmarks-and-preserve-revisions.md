# D-0015: Create bookmarks only under free names and preserve revisions on destroy

- Recorded: 2026-11-18
- Decided by: project owner, who accepted the recommendations from the reference book review on 2026-11-18
- Topic: Reference book review
- Supersedes: the optional abandonment mode in [Thread head and lifecycle sagas](../../docs/reference/book/17-decisions/thread-head-and-sagas.md) and its risk label in [D-0009](0009-operate-headless-with-a-configurable-automation-policy.md)

## Decision

A thread claims its first bookmark with a create-only operation. A retry needs the attributed jj operation that introduced it. Destroy removes kiki's resources and preserves revision history. The planned v1.x destroy command has no revision abandonment mode.

## Why

An existing bookmark can move forward without warning. Abandoning a linear chain can delete an unrelated bookmark, even when the chain has no outside descendants. Users retain direct control over history through jj.

[Owning chapter](../../docs/reference/book/03-threads.md#destroy) · [Review cases](../investigations/2026/2026-11-18-reference-book-failure-cases.md)
