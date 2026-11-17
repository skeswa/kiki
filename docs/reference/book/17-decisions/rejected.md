# Alternatives and rejected directions

This note lists designs that were considered and turned down, with the reason for each.

## Per-repo daemon

Rejected for v1. kiki uses one user-scoped [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) (one background program per user, not one per repository). That keeps cross-repo visibility and daemon lifecycle simple for the user.

## Security boundary via workspaces

Rejected as a v1 claim. [Workspaces](../appendix-a-glossary.md#workspace) are useful cooperative separation. But they do not constrain same-UID agents, which are agents running as the same operating-system user.

## Mirroring jj flags

Rejected. kiki provides [thread](../appendix-a-glossary.md#thread)-aware porcelain (friendly commands on top of a lower-level tool). Users should run [`jj`](https://docs.jj-vcs.dev/latest/) directly for arbitrary jj behavior.

## Transcript-fed publishing

Rejected. [Transcript](../appendix-a-glossary.md#thread-transcript) prose is locally stored and often contains sensitive or dead-end context. Publishing and auto metadata features must not consume it (see the [no-publication rule](../appendix-a-glossary.md#no-publication-rule)).

Consented catch-up or transcript-[MCP](https://modelcontextprotocol.io/) output to a configured model provider is a separate, explicitly disclosed egress boundary. It needs a thread/provider/purpose-bound grant.

## General-purpose hook dispatcher in v1

Rejected. [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) runs matching [hooks](https://docs.claude.com/en/docs/claude-code/hooks) concurrently. Kiki requires exclusive [`PreToolUse`](../appendix-a-glossary.md#pretooluse) control for managed v1 sessions. It does not reimplement Claude's hook merging, timeout, output, and failure semantics. A dispatcher may be reconsidered only after the cascade boundary is proven.

## Hidden live-head bookmark

Rejected. The managed workspace's `@` is the [live thread head](../appendix-a-glossary.md#thread-head). The human [bookmark](../appendix-a-glossary.md#bookmark) is an explicit checkpoint and publication [projection](../appendix-a-glossary.md#projection). A second hidden bookmark would create another pointer that can drift without solving a v1 requirement.

## Arbitrary owned-stack DAGs in v1

Rejected. V1 explicitly rebases only a provable single-parent chain from [synchronized base](../appendix-a-glossary.md#synchronized-base) to thread head (the [owned stack](../appendix-a-glossary.md#owned-stack)). Merge commits, foreign descendants, or multiple roots become [`TopologyDiverged`](../appendix-a-glossary.md#topologydiverged). Kiki does not infer a broader source [revset](https://docs.jj-vcs.dev/latest/revsets/).

Note added 2026-11-16: the chain starts just after the synchronized base. The base itself is not on the owned chain. See [Checkpoint target and relationship](../13-architecture/op-log-watcher.md#checkpoint-target-and-relationship).

## Mirrored audit sinks and tamper-evident chaining

Rejected for v1. Each parseable attempt has exactly one authoritative [SQLite](https://www.sqlite.org/) destination:

- the target repo's `audit_log` when its repo resolves;
- otherwise the user database's `user_audit_log`.

Two additions were considered: mirroring the same attempt to [JSONL](https://jsonlines.org/) or both databases, and adding [hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function) chaining. They would create another consistency protocol without defending against the documented same-UID threat model.

## Blanket `--yes` and other approval shortcuts

Rejected, and still rejected. A blanket `--yes` flag, confirmation piped in on standard input, approval through an environment variable, approval by an ordinary config key, and a reusable approval token would each let any caller skip the plan-bound approval. An agent could use them by accident.

Note added 2026-11-17: kiki must now run [headless](../appendix-a-glossary.md#headless), with no human present. The supported path for unattended approval is an activated [automation policy](../04-authority.md#automation-policy). It differs from the shortcuts above in three ways. The owner writes rules that name the caller, the operation, and the accepted [risk labels](../04-authority.md#risk-labels). The policy does nothing until the enrolled presenter or the Admin credential activates it. Each approval it gives is still single-use and bound to one exact plan.

## Automatic transcript redaction

Rejected for v1. Heuristic or model-based redaction creates false confidence. It may also erase the context recall is meant to preserve. Kiki discloses [provider egress](../appendix-a-glossary.md#provider-egress) and asks for consent instead.

Note added 2026-11-17: on a host with no human, that consent can come from an activated [automation policy](../04-authority.md#automation-policy) rule that names both the purpose and the provider. No wildcard rule and no plain config key can grant it.
