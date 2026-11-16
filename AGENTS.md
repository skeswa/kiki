# Working in kiki

Read [CLAUDE.md](CLAUDE.md) for repository guidance and the
[reference index](docs/reference/README.md) for the canonical contract and its
authority order. Check the checkout's actual VCS metadata before applying
the jj recipes; do not initialize or migrate it as part of unrelated work.

## Keep the project journal current

- Start at [journal/README.md](journal/README.md) for research and design
  history. The reference book remains the current behavior and scope contract.
- Record consequential choices using the
  [decision process](journal/decisions/README.md) and its template. Give each
  record the next unused ID, identify the actual decider, and update the index
  and affected current docs in the same change. Routine choices belong in the
  revision description.
- Put questions, findings, and dated outcomes in
  [investigations](journal/investigations/README.md). Link the evidence and
  separate measured facts, recommendations, and decided choices.
- Keep reusable research tools indexed, retain compact evidence, and preserve
  recorded bytes. Existing published research and book rationale keep their
  paths; the journal indexes them. See the journal's placement rules.
- A changed decision gets a new record with links in both directions. Do not
  rewrite an earlier record to make a reversal look like the original choice.
- Run `bun run docs:check` after documentation changes; it checks the journal
  and reference links and builds the documentation site.
