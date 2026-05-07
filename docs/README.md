# The kiki Reference

This directory is the implementation reference for kiki (`kk`).

Read it as a small spec book: first the reason for the tool, then the model, then the safety rules, then the user surfaces and machinery. The book is normative. It defines kiki's permitted behavior, prohibited behavior, and v1 boundaries. Ambiguity should be treated as a documentation bug to fix.

## Reading order

1. [Abstract](book/00-abstract.md)
2. [Orientation](book/01-orientation.md)
3. [Glossary](book/02-glossary.md)
4. [User Stories](book/03-user-stories.md)
5. [Invariants](book/04-invariants.md)
6. [Threads](book/05-threads.md)
7. [Authority](book/06-authority.md)
8. [Cascade](book/07-cascade.md)
9. [Transcript](book/08-transcript.md)
10. [Publishing](book/09-publishing.md)
11. [Metadata Evolution](book/10-metadata.md)
12. [Commands](book/11-commands.md)
13. [Interface](book/12-interface.md)
14. [Configuration](book/13-configuration.md)
15. [Observability](book/14-observability.md)
16. [Architecture](book/15-architecture/)
17. [Testing](book/16-testing.md)
18. [Build Sequencing](book/17-build-sequencing.md)
19. [Roadmap](book/18-roadmap.md)
20. [Naming](book/19-naming.md)

Appendices contain design notes and historical PRD stubs:

- [Decisions](appendix/decisions/)
- [PRDs](appendix/prds/)

## Authority

The numbered chapters are the live contract. Appendices explain why the contract looks the way it does. The numbered chapters remain authoritative.

When two live chapters appear to conflict, use this order:

1. [Invariants](book/04-invariants.md)
2. Behavioral chapters: [Threads](book/05-threads.md), [Authority](book/06-authority.md), [Cascade](book/07-cascade.md), [Transcript](book/08-transcript.md), [Publishing](book/09-publishing.md), [Metadata Evolution](book/10-metadata.md), [Commands](book/11-commands.md), [Interface](book/12-interface.md), [Configuration](book/13-configuration.md), and [Observability](book/14-observability.md)
3. [User Stories](book/03-user-stories.md), as product intent that the stricter chapters must satisfy
4. [Architecture](book/15-architecture/)
5. [Testing](book/16-testing.md), [Build Sequencing](book/17-build-sequencing.md), [Roadmap](book/18-roadmap.md), and [Naming](book/19-naming.md)
6. Appendices

The original PRD path remains as a historical stub. The numbered chapters carry the contract.

## Language

The words **must**, **must not**, **may**, and **should** are normative in the ordinary RFC sense. The voice is plain by design: kiki coordinates expensive, stateful work, and the docs should say exactly what they mean.
