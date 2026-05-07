# The kiki Reference

This directory is the implementation reference for kiki (`kk`).

Read it as a small spec book: first the reason for the tool, then the model, then the safety rules, then the user surfaces and machinery. The book is normative. It defines kiki's permitted behavior, prohibited behavior, and v1 boundaries. Ambiguity should be treated as a documentation bug to fix.

## Reading order

1. [Abstract](book/00-abstract.md)
2. [Orientation](book/01-orientation.md)
3. [Glossary](book/02-glossary.md)
4. [Invariants](book/03-invariants.md)
5. [Threads](book/04-threads.md)
6. [Authority](book/05-authority.md)
7. [Cascade](book/06-cascade.md)
8. [Transcript](book/07-transcript.md)
9. [Publishing](book/08-publishing.md)
10. [Metadata Evolution](book/09-metadata.md)
11. [Commands](book/10-commands.md)
12. [Interface](book/11-interface.md)
13. [Configuration](book/12-configuration.md)
14. [Observability](book/13-observability.md)
15. [Architecture](book/14-architecture/)
16. [Testing](book/15-testing.md)
17. [Build Sequencing](book/16-build-sequencing.md)
18. [Roadmap](book/17-roadmap.md)
19. [Naming](book/18-naming.md)

Appendices contain design notes and historical PRD stubs:

- [Decisions](appendix/decisions/)
- [PRDs](appendix/prds/)

## Authority

The numbered chapters are the live contract. Appendices explain why the contract looks the way it does. The numbered chapters remain authoritative.

When two live chapters appear to conflict, use this order:

1. [Invariants](book/03-invariants.md)
2. Behavioral chapters: [Threads](book/04-threads.md), [Authority](book/05-authority.md), [Cascade](book/06-cascade.md), [Transcript](book/07-transcript.md), [Publishing](book/08-publishing.md), [Metadata Evolution](book/09-metadata.md), [Commands](book/10-commands.md), [Interface](book/11-interface.md), [Configuration](book/12-configuration.md), and [Observability](book/13-observability.md)
3. [Architecture](book/14-architecture/)
4. [Testing](book/15-testing.md), [Build Sequencing](book/16-build-sequencing.md), [Roadmap](book/17-roadmap.md), and [Naming](book/18-naming.md)
5. Appendices

The original PRD path remains as a historical stub. The numbered chapters carry the contract.

## Language

The words **must**, **must not**, **may**, and **should** are normative in the ordinary RFC sense. The voice is plain by design: kiki coordinates expensive, stateful work, and the docs should say exactly what they mean.
