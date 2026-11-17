# Documentation writing review

- Date: 2026-11-17
- Type: Outcome
- Topic: Clear documentation and removal of AI writing patterns
- Request: “Please $avoid-ai-writing on all kiki docs”

## Summary

Reviewed all 59 Markdown files and the text in five Vue theme components using
the `avoid-ai-writing` skill, version 3.4.0, in rewrite mode with its `docs`
profile. The review produced 132 edits across 36 source files. The
[audit](../../evidence/documentation-writing/2026-11-17/audit.md) quotes each
original passage and its replacement, and lists every file reviewed.

Most changes were in introductions, site copy, and explanations around the
technical rules. The reference lists, glossary, command examples, and test
scenarios mostly needed no writing changes.

## Context

The project requires high-school-level English for all documentation. This
review started at revision `ce22fc5e3d224b8e4c3529db5663ccd2b351562e`, which
already contained earlier documentation edits. Those edits were preserved.
The review used small, described jj revisions for each group of changes.

This was a writing review. It did not reassess the product design, re-run the
Herdr or jj probes, or establish new compatibility claims.

## Issues found

- Inflated or vague descriptions, such as “a real seam” and “the strongest
  existing reuse seam,” were replaced with the interface's purpose or the
  capability kiki can reuse.
- Metaphors such as “the contract chapters tighten the screws” and “an infinite
  loop wearing a retry's clothes” were replaced with the rule or failure they
  described.
- Rhetorical framing, such as “is the hardest coordination primitive real?”,
  was replaced with what the proof of concept must demonstrate.
- General assurances, such as “an honest lifecycle state,” were replaced with
  the state or evidence the reader should expect.

The full list, with quoted originals, is in the
[audit's issues and replacements](../../evidence/documentation-writing/2026-11-17/audit.md#issues-and-replacements).
These are writing judgments, not claims about who wrote the text.

## Rewritten version

The edited files contain the full rewritten documentation. The audit links
to each one. Start with the [README](../../../README.md),
[Abstract](../../../docs/reference/book/00-abstract.md), and
[Orientation](../../../docs/reference/book/01-orientation.md).

The rewrites use concrete tasks and failure conditions, shorter explanations,
and direct statements of responsibility. Technical terms keep their defined
meanings. For example, “harness” names a coding-agent program, “actionable
toast” names an interface category, and `loud` names a notification level.
Those terms remain. Lists, bold labels, and technical qualifiers also remain
where the docs profile permits them and they help readers find a rule.

## Second-pass audit

The second pass checked the replacements against the original wording and
nearby requirements. It clarified that a bookmark serves as both a checkpoint
and a publication projection. It also removed an added error-message detail
that the original requirement did not specify. A shortened schema heading
keeps its old anchor so existing links still work.

The final scan found no further edits needed under the docs profile. The
remaining flagged words had technical meanings, described test fakes, or
appeared in quoted evidence. Existing fenced examples were byte-for-byte
unchanged. No captured research results, probes, license text, source pins,
decision dates, or attributed user quotations were changed.

## Validation

- `mise run fmt` formatted the handwritten edits.
- `mise run check` passed formatting, documentation links, and the production
  VitePress build. The build still reported its existing bundle-size warning.
- A comparison with the starting revision found no changes to existing fenced
  code examples or captured research evidence.
- `git diff --check` against the starting revision found no whitespace errors.

The audit records wording changes, not a readability score or a formal proof
that every requirement is equivalent. No product behavior change was intended.

## Evidence and reproduction

The [audit](../../evidence/documentation-writing/2026-11-17/audit.md) retains
the file inventory and exact before-and-after passages. Compare the starting
revision with the completed revision using `jj diff --from ce22fc5e --to @`.
For a later checkout, use the completed review revision in place of `@`.
Run `mise run check` to repeat the repository checks.
