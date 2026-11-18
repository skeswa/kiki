# D-0013: Prove tool admission and message delivery

- Recorded: 2026-11-18
- Decided by: project owner, who accepted the recommendations from the reference book review on 2026-11-18
- Topic: Reference book review
- Supersedes: the outage rule in [D-0006](0006-close-repair-and-proof-gaps.md) and the original [soft-delivery recovery rule](../../docs/reference/book/17-decisions/cascade-outbox.md)

## Decision

A managed tool needs a positive decision for its batch. Kiki changes files only after it accounts for every writer. Every soft delivery needs a matching harness receipt, batch completion, and a later turn in the conversation that received the message. Use the bounded restart path on versions that cannot prove these facts.

## Why

One hook can time out just before a sibling reaches the daemon. A whole batch can also finish on generic denials after the daemon saves a message. These rules cost tool availability during an outage and require live adapter tests.

[Owning chapter](../../docs/reference/book/05-cascade.md#delivery-protocol) · [Review cases](../investigations/2026/2026-11-18-reference-book-failure-cases.md)
