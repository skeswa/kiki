# D-0017: Keep event replay stable across working directories

- Recorded: 2026-11-18
- Decided by: project owner, who accepted the recommendations from the reference book review on 2026-11-18
- Topic: Reference book review

## Decision

Use the repo summary stream for ordinary events, even with a thread filter. A caller explicitly selects full detail with the thread's own credential. Bind each resume cursor to the registration, thread filter, stream and sequence.

## Why

The same integer can name different events on the two streams. A script should be able to move between directories and resume without silent data loss or a change in what it can read.

[Owning chapter](../../docs/reference/book/09-commands.md#kk-events) · [Review cases](../investigations/2026/2026-11-18-reference-book-failure-cases.md)
