# D-0016: Fence the registration before unregister removes state

- Recorded: 2026-11-18
- Decided by: project owner, who accepted the recommendations from the reference book review on 2026-11-18
- Topic: Reference book review

## Decision

Both modes of unregister stop admission, drain earlier work, and refuse to remove the records of a live thread or unfinished operation. A user-level journal owns the fence and verifies deletion or retention of the exact old directory before completing.

## Why

The user registry survives removal of a repo database. It can invalidate old credentials and finish the approved plan after a crash. Keeping the directory lets a person inspect it even though that registration has ended.

[Owning chapter](../../docs/reference/book/09-commands.md#repo-registry) · [Review cases](../investigations/2026/2026-11-18-reference-book-failure-cases.md)
