# Project journal

The journal connects what we investigated, the evidence we kept, and the
choices that followed. For kiki's current behavior and scope, start with the
[reference book](../docs/reference/README.md).

| Question                                 | Start here                                                     |
| ---------------------------------------- | -------------------------------------------------------------- |
| What did we investigate or learn?        | [Investigations and dated outcomes](investigations/README.md)  |
| What did we choose, and why?             | [Decision log](decisions/README.md)                            |
| How can I reproduce a check?             | [Research tools](tools/README.md)                              |
| Where are the measurements and receipts? | [Evidence](evidence/README.md)                                 |
| What happened during earlier work?       | [Archived plans and implementation records](archive/README.md) |

## Adding to the journal

Start an [investigation](investigations/TEMPLATE.md) with a question and a short
conclusion. Keep measured facts, interpretations, and remaining uncertainty
distinct. Add it to the investigation index and link its tools and evidence.

Record consequential choices using the [decision process](decisions/README.md).
Update the affected reference chapters in the same change when behavior or
scope changes. Research findings and decision rationale do not silently amend
the book's contract.

Keep maintained, reusable scripts in `tools/<topic>/` and compact, dated
evidence in `evidence/<topic>/<run>/`. Temporary scripts and verbose output
belong in scratch. Preserve retained evidence; a new run gets new files.
Completed or replaced plans belong in `archive/`, with links to their successors.

The existing Herdr reports, published probes, and book design notes keep their
current paths and are indexed here. New records use this journal; avoid copying
old material into a second source of truth.

This is the repository's project history. Kiki's planned SQLite lifecycle
journals and audit records are application state with a separate contract.

The convention is adapted from Swingset; [D-0001](decisions/0001-adopt-project-journal.md)
records the adaptation and its sources.
