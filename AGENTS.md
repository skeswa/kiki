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
- Run `mise run check` after changes; it checks formatting, journal and
  reference links, and the production documentation build.

## Tooling and tasks

Use `mise run <task>` as the task interface. [mise.toml](mise.toml) owns tool
versions and task definitions; `package.json` scripts are compatibility aliases.
`mise install` installs pinned tools and `mise run setup` installs the site's
locked dependencies. `mise tasks` lists the available commands.

| Task                           | Command               |
| ------------------------------ | --------------------- |
| Serve the documentation        | `mise run dev`        |
| Build the documentation        | `mise run build`      |
| Preview the last build         | `mise run preview`    |
| Check links and contract terms | `mise run docs:links` |
| Check and build documentation  | `mise run docs:check` |
| Run all current checks         | `mise run check`      |

These are repository tooling tasks. The application is still pre-implementation;
add Rust build and test tasks when that implementation exists.

## Formatting

`mise run fmt` is the formatting entry point. Taplo owns TOML; Oxfmt owns
TypeScript, JavaScript, Vue, CSS, JSON, Markdown, and YAML. Both formatters and
their runtimes are pinned exactly in `mise.toml`. Formatting requires only
mise, without the site's `node_modules` or an activated shell environment.
Use `mise run fmt:check` for a check without writes; CI runs it through `check`.

Run formatting before handing off handwritten edits. Update formatter pins
deliberately, then reformat and validate. Exclusions live in
[.prettierignore](.prettierignore) and [.taplo.toml](.taplo.toml): generated
output, dependency files, fixtures, retained evidence, published probes, and
dated research reports keep their bytes. The formatters do not own lockfiles.
Add new captured paths to the exclusions instead of reformatting them.
