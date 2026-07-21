# The kiki Reference

This directory is the implementation reference for kiki (`kk`).

Read it as a small spec book: first the reason for the tool, then the model, then the safety rules, then the user surfaces and machinery. The book is normative. It defines kiki's permitted behavior, prohibited behavior, and v1 boundaries. Ambiguity should be treated as a documentation bug to fix.

New readers should start with the [Abstract](book/00-abstract.md) and [Orientation](book/01-orientation.md). Together they carry the narrative — the hand-built workspace-per-line-of-work workflow kiki automates, its frictions, and the mechanism that answers each one — before the contract chapters tighten the screws.

## Reading order

The chapters tell the story in order; the appendices hold reference material you dip into rather than read through.

1. [Abstract](book/00-abstract.md)
2. [Orientation](book/01-orientation.md)
3. [Invariants](book/02-invariants.md)
4. [Threads](book/03-threads.md)
5. [Authority](book/04-authority.md)
6. [Cascade](book/05-cascade.md)
7. [Transcript](book/06-transcript.md)
8. [Publishing](book/07-publishing.md)
9. [Metadata Evolution](book/08-metadata.md)
10. [Commands](book/09-commands.md)
11. [Interface](book/10-interface/)
12. [Configuration](book/11-configuration.md)
13. [Observability](book/12-observability.md)
14. [Architecture](book/13-architecture/)
15. [Testing](book/14-testing.md)
16. [Build Sequencing](book/15-build-sequencing.md)
17. [Roadmap](book/16-roadmap.md)
18. [Decisions](book/17-decisions/)

Appendices:

- [Appendix A: Glossary](book/appendix-a-glossary.md)
- [Appendix B: User Stories](book/appendix-b-user-stories.md)
- [Appendix C: Naming](book/appendix-c-naming.md)

## Authority

The numbered chapters and appendices are the live contract. The Decisions chapter explains why parts of the contract look the way they do, but the behavioral chapters remain authoritative.

When two live chapters appear to conflict, use this order:

1. [Invariants](book/02-invariants.md)
2. Behavioral chapters: [Threads](book/03-threads.md), [Authority](book/04-authority.md), [Cascade](book/05-cascade.md), [Transcript](book/06-transcript.md), [Publishing](book/07-publishing.md), [Metadata Evolution](book/08-metadata.md), [Commands](book/09-commands.md), [Interface](book/10-interface/), [Configuration](book/11-configuration.md), and [Observability](book/12-observability.md)
3. [User Stories](book/appendix-b-user-stories.md), as product intent that the stricter chapters must satisfy
4. [Architecture](book/13-architecture/)
5. [Testing](book/14-testing.md), [Build Sequencing](book/15-build-sequencing.md), [Roadmap](book/16-roadmap.md), [Decisions](book/17-decisions/), and the remaining appendices

## Language

The words **must**, **must not**, **may**, and **should** are normative in the ordinary RFC sense. The voice is plain by design: kiki coordinates expensive, stateful work, and the docs should say exactly what they mean.
