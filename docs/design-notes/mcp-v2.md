# MCP v2 design note

v1 may ship a narrow read-only same-thread transcript MCP surface. Broader MCP behavior is deferred.

Deferred MCP ideas include:

- cross-thread agent messages
- agent-driven thread spawning
- causal-chain tracking
- depth caps and branch caps
- richer audit surfaces for inter-thread activity

The v1 rule remains strict: a thread-scoped credential can read only its own transcript through MCP. The URL path is routing convenience, not identity. Identity is bound to the credential.
