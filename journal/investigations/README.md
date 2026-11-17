# Investigations and dated outcomes

Investigations explain a question, what was examined, and what the evidence
showed. Preserve their dates, source versions, and limits. A recommendation
does not establish a decision, and a successful experiment does not establish
that kiki implements the behavior.

Use the [template](TEMPLATE.md) for new records under
`journal/investigations/<year>/YYYY-MM-DD-short-topic.md`. Index each record
here by the question it answers. Link conclusions to their
[evidence](../evidence/README.md), [tools](../tools/README.md), and any resulting
[decision](../decisions/README.md). If later work changes a conclusion, link
the records in both directions while preserving the earlier finding.

## Herdr and jj

The 2026-10-30 investigations predate the journal and retain their published paths.
Their findings remain limited to the versions and environments they examined.
The owner later chose Herdr as the terminal runtime; see [D-0004](../decisions/0004-use-herdr-as-terminal-runtime.md).

| Date       | Question                                                                           | Investigation                                                           |
| ---------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| 2026-10-30 | Which Herdr foundations can kiki reuse, and how does jj fit?                       | [Herdr foundations and jj integration](../../docs/research/herdr-jj.md) |
| 2026-10-30 | Can Herdr replace tmux's terminal-hosting role?                                    | [Herdr terminal runtime](../../docs/research/herdr-terminal-runtime.md) |
| 2026-11-16 | Do those findings hold for the Herdr revision and jj version the redesign targets? | [Herdr and jj revalidation](2026/2026-11-16-herdr-jj-revalidation.md)   |

Current behavior and scope remain in the [reference book](../../docs/reference/README.md).

## Documentation

| Date       | Question                                                | Outcome                                                                         |
| ---------- | ------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 2026-11-17 | Which writing patterns needed revision across the docs? | [Documentation writing review](2026/2026-11-17-documentation-writing-review.md) |

## Remote access

- 2026-11-17 — [How can I pick up my threads from another machine and keep accounts separate?](2026/2026-11-17-multi-machine-access.md)
