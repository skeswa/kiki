# D-0014: Keep checkpoint previews read-only and end follows links on close

- Recorded: 2026-11-18
- Decided by: project owner, who accepted the recommendations from the reference book review on 2026-11-18
- Topic: Reference book review

## Decision

A preview pins existing clean heads. The caller can prepare a dirty workspace with a separate approved snapshot. Close settles and ends every live follows link of the closing thread. Reopen starts independently at its archived checkpoint. A verified resume after an aborted close restores the original binding and prior agent status.

## Why

Previewing a close used to risk rewriting the head before approval. A closed workspace cannot receive a cascade, and a resumed process cannot send a new session-start event. Separate outcomes give each step evidence it can actually check.

[Owning chapter](../../docs/reference/book/03-threads.md#close) · [Review cases](../investigations/2026/2026-11-18-reference-book-failure-cases.md)
