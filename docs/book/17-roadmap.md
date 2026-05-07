# Roadmap

This chapter captures deferred surfaces whose design affects v1 boundaries. Deferred does not mean vague; it means the book records the boundary now so v1 does not accidentally grow half of a future substrate.

## v1.x polish

Likely post-acceptance work:

- hook configuration diagnostics;
- op-log watcher edge cases;
- additional `kk thread` management commands;
- status-line and TUI polish;
- AI auto-describe and auto-rename execution loop once the ownership ledger is proven;
- PR merge polling and auto-archive if it misses the first acceptance slice;
- narrow same-thread transcript MCP reads if the human CLI surface is stable.

## v2 MCP substrate

The narrow read-only same-thread transcript MCP surface may ship before v2. Broader MCP behavior waits for a dedicated substrate.

Deferred MCP behavior includes:

- cross-thread agent messages;
- agent-driven thread spawning;
- cross-thread read resources;
- causal-chain tracking;
- depth, cycle, and branch caps;
- richer audit surfaces for inter-thread activity.

## MCP identity

MCP uses a separate unix socket. URL paths route requests; credentials supply identity.

A thread-scoped credential may read its own transcript. A URL such as `/threads/<uuid>` does not authorize the caller to act as that thread. Authorization is always bound to the credential presented on the request.

## Tool tiers

The v2 substrate divides tools by authority:

- same-thread, low-risk tools may be self-acting, such as setting status or requesting human attention;
- publish and close may be exposed only as human-confirmed same-thread intents;
- cross-thread reads may be auto-allowed only within explicit policy;
- cross-thread posts and agent-driven spawns are rate-limited and causal-chain tracked;
- cross-thread close, destroy, publish, and revision rewriting remain unavailable to agents.

Destroy is not exposed to agents, including on the caller's own thread.

## Causal chains

Every agent-originated cross-thread post or spawn carries a `causal_chain_id`.

Rules:

- a human-originated action starts a fresh chain;
- an agent action caused by an incoming context message inherits that message's chain;
- revisiting a thread within the same chain is a cycle and quarantines the chain;
- default depth cap is 5 hops;
- default branch cap is 4 distinct threads;
- default spawn cap is 1 agent-driven spawn per minute per parent thread;
- a human reply terminates the chain and future actions start fresh.

The intended tables are `causal_chains` and `causal_chain_visits`, deferred until the substrate ships.

## Later architecture

Likely later swaps:

- Codex and other harness adapters behind the existing `Harness` and `TranscriptAdapter` traits;
- direct GitHub REST or GraphQL behind `GitHubBackend`;
- jj-lib behind `JjBackend`;
- native GUI, web dashboard, or remote clients over the same gRPC service.
