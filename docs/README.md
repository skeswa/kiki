# kiki docs

This directory separates product intent, normative v1 behavior, architectural structure, design rationale, and roadmap.

## Where to read

- [Product overview](product/overview.md) — vision, v1 scope, non-goals.
- [v1 invariants](specs/invariants.md) — non-negotiable behavioral promises that cut across multiple specs.
- [v1 specs](specs/) — normative implementation contract for v1 behavior.
- [Architecture](architecture/) — structural decisions: crates, gRPC surface, schema, daemon shape, op-log watcher, harness adapter.
- [Glossary](glossary.md) — canonical definitions for the load-bearing terms.
- [Decisions](decisions/) — design rationale and rejected alternatives.
- [Roadmap](roadmap/) — v2 surfaces deliberately deferred.
- [PRDs](prds/) — historical source documents. Frozen once their content has migrated into specs and architecture.

## Authority model

If two docs conflict, use this order:

1. `specs/invariants.md`
2. `specs/*`
3. `architecture/*`
4. `product/overview.md`
5. `decisions/*`
6. `roadmap/*`
7. `prds/*`

The PRD remains source material for many details, but implementation should be checked against the spec files and the architecture docs.

## Layout

```
docs/
├── README.md
├── glossary.md
├── product/
│   └── overview.md
├── specs/
│   ├── invariants.md
│   ├── cli.md
│   ├── thread-lifecycle.md
│   ├── cascade.md
│   ├── transcript.md
│   ├── auth.md
│   ├── publishing.md
│   ├── config.md
│   ├── tui.md
│   └── testing.md
├── architecture/
│   ├── crates.md
│   ├── grpc.md
│   ├── schema.md
│   ├── daemon.md
│   ├── op-log-watcher.md
│   └── harness-adapter.md
├── decisions/
│   ├── cascade-outbox.md
│   ├── transcript-anchoring.md
│   └── rejected.md
├── roadmap/
│   └── mcp-v2.md
└── prds/
    └── 0001-kiki.md
```
