# Alternatives and rejected directions

## Per-repo daemon

Rejected for v1. kiki uses one user-scoped daemon so cross-repo visibility and daemon lifecycle are simple for the user.

## Security boundary via workspaces

Rejected as a v1 claim. Workspaces are useful cooperative separation, but they do not constrain same-UID agents.

## Mirroring jj flags

Rejected. kiki provides thread-aware porcelain. Users should run `jj` directly for arbitrary jj behavior.

## Transcript-fed publishing

Rejected. Transcript prose is locally stored and often contains sensitive or dead-end context. Publishing and auto metadata features must not consume it. Consented catch-up or transcript-MCP output to a configured model provider is a separate, explicitly disclosed egress boundary with a thread/provider/purpose-bound grant.

## General-purpose hook dispatcher in v1

Rejected. Claude Code runs matching hooks concurrently. Kiki requires exclusive `PreToolUse` control for managed v1 sessions instead of reimplementing Claude's hook merging, timeout, output, and failure semantics. A dispatcher may be reconsidered only after the cascade boundary is proven.

## Hidden live-head bookmark

Rejected. The managed workspace's `@` is the live thread head; the human bookmark is an explicit checkpoint and publication projection. A second hidden bookmark would create another pointer that can drift without solving a v1 requirement.

## Arbitrary owned-stack DAGs in v1

Rejected. V1 explicitly rebases only a provable single-parent chain from synchronized base to thread head. Merge commits, foreign descendants, or multiple roots become `TopologyDiverged`; kiki does not infer a broader source revset.

## Mirrored audit sinks and tamper-evident chaining

Rejected for v1. Each parseable attempt has exactly one authoritative SQLite destination: the target repo's `audit_log` when its repo resolves, otherwise the user database's `user_audit_log`. Mirroring the same attempt to JSONL or both databases, and adding hash chaining, would create another consistency protocol without defending against the documented same-UID threat model.

## Automatic transcript redaction

Rejected for v1. Heuristic or model-based redaction creates false confidence and may erase the context recall is meant to preserve. Kiki discloses provider egress and asks for consent instead.
