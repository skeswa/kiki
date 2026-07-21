# Roadmap

This chapter records deferred surfaces whose design affects v1 boundaries. Deferred does not mean vague. It means the book draws the boundary now, so v1 does not accidentally grow half of a future substrate.

## v1.x polish

The v1.x tier is enumerated once, in [Orientation](01-orientation.md); this chapter does not keep a second list. What follows records design boundaries for deferred surfaces that need them. Only the scope ledger can promote a surface into the acceptance slice.

## v2 MCP substrate

MCP (the Model Context Protocol) is a standard interface that lets agents call tools and read resources. The narrow read-only same-thread transcript MCP surface may ship before v2. Broader MCP behavior waits for a dedicated substrate.

Deferred MCP behavior includes:

- cross-thread agent messages;
- agent-driven thread spawning;
- cross-thread read resources;
- causal-chain tracking;
- depth, cycle, and branch caps;
- richer audit surfaces for inter-thread activity.

## MCP identity

MCP uses a separate unix socket. URL paths route requests; credentials supply identity. Think of the URL as the address on an envelope and the credential as the ID you show at the door — only the ID grants access.

A thread-scoped credential may read its own transcript. A URL such as `/threads/<uuid>` does not authorize the caller to act as that thread. Authorization is always bound to the credential presented on the request.

When the same-thread transcript MCP surface ships, each call is checked in this order:

MCP-specific status-code contract:

1. Credentials that are missing, malformed, revoked, or carry an invalid signature get `Unauthenticated`.
2. Well-formed credentials that are not `ThreadScoped<T>` get `PermissionDenied`. Neither reusable Admin authority nor one-shot human approvals are exposed through the narrow transcript MCP surface.
3. If the request names a thread both in the URL path and in an explicit argument, and the two differ, the request gets `InvalidArgument`.
4. If the credential authorizes thread T and the request asks for thread U, where U is not T, the request gets `PermissionDenied`.

The daemon must not silently re-dispatch a request to the thread the credential authorizes. That would hide client bugs and make audit rows harder to interpret.

## Tool tiers

The v2 substrate divides tools by how much authority they need:

- same-thread, low-risk tools may be self-acting — for example, setting status or requesting human attention;
- publish and close may be requested only as intents, and those intents stop at the foreground one-shot human-approval boundary;
- cross-thread summaries may be auto-allowed only within the minimal summary policy; sensitive cross-thread reads require a foreground one-shot approval, so they are not autonomous MCP tools;
- cross-thread posts and agent-driven spawns are rate-limited and causal-chain tracked;
- cross-thread close, destroy, publish, and revision rewriting remain unavailable to agents; an agent request cannot itself satisfy or retain the human approval.

Destroy is not exposed to agents at all, including on the caller's own thread.

## Causal chains

Every agent-originated cross-thread post or spawn carries a `causal_chain_id`. A causal chain is a paper trail: it records which agent action caused which, so runaway agent-to-agent loops can be detected and capped.

Rules:

- a human-originated action starts a fresh chain;
- an agent action caused by an incoming context message inherits that message's chain;
- revisiting a thread within the same chain is a cycle, and a cycle quarantines the chain;
- the default depth cap is 5 hops;
- the default branch cap is 4 distinct threads;
- the default spawn cap is 1 agent-driven spawn per minute per parent thread;
- a human reply terminates the chain, and future actions start fresh.

The intended tables are `causal_chains` and `causal_chain_visits`. Both are deferred until the substrate ships.

## Later architecture

Likely later swaps:

- harness adapters beyond `claude-code` and `codex`, behind the existing `Harness` and `TranscriptAdapter` traits;
- direct GitHub REST or GraphQL, behind `GitHubBackend`;
- jj-lib, behind `JjBackend`;
- a native GUI, a web dashboard, or remote clients over the same gRPC service;
- daemon-to-daemon coordination, so one machine's `kk` can observe — and eventually drive — threads whose workspaces live on another machine's `kkd`. Working across machines is part of the product vision, not an accident of scope. The same-host boundary exists because peer daemons, like remote clients, wait on the future transport and authentication contract rather than inheriting unix-socket assumptions.
