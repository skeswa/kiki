# The kiki Reference

This directory is the implementation reference for kiki (`kk`). kiki is a tool that coordinates coding agents, the version-control tool [jj](book/appendix-a-glossary.md#ext-jj), and terminals.

The book starts with the reason for the tool, then defines its model, safety rules, user interface, and implementation.

The book defines what kiki must do, what it must not do, and what belongs in v1. Report unclear requirements as documentation bugs.

Start with the [Abstract](book/00-abstract.md) and [Orientation](book/01-orientation.md). They describe the manual workflow kiki automates: one [workspace](book/appendix-a-glossary.md#workspace) per line of work. They explain the bookkeeping this requires and how kiki handles it.

If you meet a term you do not know, look it up in the [Glossary](book/appendix-a-glossary.md). The chapters link to it the first time they use a special term.

## Reading order

Read the chapters in order. Use the appendices to look up terms, user stories, and names as needed.

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

The numbered chapters and appendices are the live contract: the rules that are in force now. The Decisions chapter explains why parts of the contract look the way they do, but the behavioral chapters remain authoritative.

The repository's [project journal](https://github.com/skeswa/kiki/tree/main/journal) holds investigations, evidence, and the [numbered decision log](https://github.com/skeswa/kiki/blob/main/journal/decisions/README.md). Journal entries preserve findings and rationale (the reasons behind a choice). Changes to behavior or scope must also update the owning chapters here.

When two live chapters appear to conflict, use this order. A chapter higher in the list wins:

1. [Invariants](book/02-invariants.md)
2. Behavioral chapters: [Threads](book/03-threads.md), [Authority](book/04-authority.md), [Cascade](book/05-cascade.md), [Transcript](book/06-transcript.md), [Publishing](book/07-publishing.md), [Metadata Evolution](book/08-metadata.md), [Commands](book/09-commands.md), [Interface](book/10-interface/), [Configuration](book/11-configuration.md), and [Observability](book/12-observability.md)
3. [User Stories](book/appendix-b-user-stories.md), as product intent that the stricter chapters must satisfy
4. [Architecture](book/13-architecture/)
5. [Testing](book/14-testing.md), [Build Sequencing](book/15-build-sequencing.md), [Roadmap](book/16-roadmap.md), [Decisions](book/17-decisions/), and the remaining appendices

## Language

The words **must**, **must not**, **may**, and **should** are normative in the ordinary RFC sense. That sense is defined in [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119), a short standard for requirement words:

- **must** and **must not** are absolute rules;
- **should** is a strong recommendation;
- **may** marks something that is allowed but optional.

The voice is plain by design. kiki coordinates expensive, stateful work, and the docs should say exactly what they mean.
