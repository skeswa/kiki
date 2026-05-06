# kiki docs

This directory separates product intent, normative v1 behavior, and design rationale.

## Where to read

- [Product vision](product/vision.md) explains why kiki exists and what problem it is solving.
- [v1 scope](product/v1-scope.md) names the first shippable contract and what can wait.
- [v1 spec index](specs/v1/index.md) is the authoritative entry point for implementation.
- [Design notes](design-notes/) preserve rationale, failure analysis, and future designs that are useful but not themselves the implementation contract.
- [PRDs](prds/) are historical/source documents. They are useful context, but the files under `specs/v1/` are the normative v1 contract.

## Authority model

If two docs conflict, use this order:

1. `docs/specs/v1/*`
2. `docs/product/v1-scope.md`
3. `docs/product/vision.md`
4. `docs/design-notes/*`
5. `docs/prds/*`

The PRD remains the source material for many details, but implementation should be checked against the v1 spec files.
