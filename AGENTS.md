# Working in kiki

## Read this first

The canonical contract for what this repo is building lives in the reference book under `docs/reference/book/`. Start at `docs/reference/README.md` for navigation, then read in this order based on what you're doing:

- For behavior questions (what does `kk x` do?): `docs/reference/book/02-invariants.md` first, then the relevant chapter in `docs/reference/book/`.
- For structure questions (which crate, which sqlite table, which gRPC method?): `docs/reference/book/13-architecture/`.
- For "why is it this way?": `journal/decisions/README.md` for the numbered decision log and links to earlier book rationale.
- For investigations, supporting evidence, and reproduction tools: `journal/README.md`.
- For deferred surfaces (v2 MCP substrate, etc.): `docs/reference/book/16-roadmap.md`.
- For terminology: `docs/reference/book/appendix-a-glossary.md`.
- For product intent and v1 scope: `docs/reference/book/00-abstract.md`, `docs/reference/book/01-orientation.md`, and `docs/reference/book/appendix-b-user-stories.md`.

The original PRD has been folded into the reference book. Treat the book as the contract.

If something in the code disagrees with the spec or architecture, that is a finding to surface, not silently align with.

## What kiki is, in one paragraph

kiki (binary `kk`) is a daemon-backed coordinator that ties jujutsu (jj), tmux, agent harnesses (Claude Code and Codex in v1), and eventually the GitHub CLI (`gh`) into a workflow for multi-threaded agentic coding. The atom is a **thread** — a themed sequence of jj revisions whose live head is its managed workspace's `@`; its bookmark is an explicit checkpoint/publication projection. Threads can follow other threads. A managed session reserves the pre-tool hook boundary exclusively for kiki, blocks the entire triggering tool batch during reconciliation (Claude Code's parallel batch; a proven-serial Codex version's single-call batch), and acknowledges delivery only from a later model turn. kiki remains an **ambient coordinator** for direct `jj`/`gh`/`tmux` operations, but ambiguous external projection changes fail loud into repair rather than being guessed through.

The planned cargo workspace has four crates: `kiki-core` (library — shared types/traits/proto/migrations, no I/O), `kkd` (daemon binary), `kk` (CLI binary that also hosts the TUI as a subcommand), and `kk-hook` (harness hook sidecar). `kkd` is the gRPC server over `~/.config/kiki/kkd.sock`; local clients share that contract. State lives in `~/.config/kiki/state.db` (cross-repo registry) plus `~/.config/kiki/repos/<repo_id>/state.db` (per-repo runtime). Remote clients require a future transport and authentication contract rather than inheriting unix-socket assumptions.

## Implementation-stack tension to be aware of

The architecture decision is **Rust** for `kkd` and friends (`docs/reference/book/13-architecture/crates.md`). The repo is currently bootstrapped as a **Bun + TypeScript** project (`package.json`, `tsconfig.json`, `index.ts` placeholder). This is a real divergence pending the first real `kkd` commit. If you are about to write or modify implementation code, surface this to the user before picking a language — do not silently default to either side.

## Version control

This is a colocated jj/Git checkout: `.jj/` and `.git/` sit side by side.
Use `jj` for version control. Use `jj git fetch` and `jj git push` for GitHub;
do not use Git write commands such as `add`, `commit`, `checkout`, `stash`,
`rebase`, or `push`. Read-only Git commands are acceptable when a jj equivalent
is awkward, but prefer jj. Never edit VCS metadata by hand.

For a fresh Git clone, run `mise install` and `mise run vcs:init`. That task
preserves the existing checkout, initializes jj if needed, sets the local
`snapshot.max-new-file-size` to `16MiB`, tracks `main@origin`, and sets
`trunk()` to `main@origin`. It can be rerun. Generated artifacts still belong
in the ignore rules. The remote is `origin` at `git@github.com:skeswa/kiki.git`.
Documentation setup and CI do not require initializing jj.

### Separate and describe draft changes

Each logical change gets its own described jj revision. jj snapshots the
working copy automatically; there is no staging step. Inspect `jj status`
before editing and preserve existing work. Use `jj describe -m '<message>'`
for the current change, then `jj new -m '<message>'` before starting another.
Do not fold a second unrelated change into the first or leave nonempty work
undescribed. These local draft operations are part of ordinary authorized work.

Finalize with `jj commit`, move `main`, or push only when the user asks.
Published trunk history must only advance: do not force-push, rewrite it, or
bypass immutable-revision checks. Before an authorized push, fetch and confirm
that the proposed `main` is a descendant of the fetched `main@origin`.

| Task                                            | Command                       |
| ----------------------------------------------- | ----------------------------- |
| Inspect work                                    | `jj status` and `jj diff`     |
| Inspect history                                 | `jj log`                      |
| Describe the current draft                      | `jj describe -m '<message>'`  |
| Start a separate draft                          | `jj new -m '<message>'`       |
| Fetch remote changes                            | `jj git fetch`                |
| Finalize and open an empty change, when asked   | `jj commit -m '<message>'`    |
| Advance main to the finished change, when asked | `jj bookmark set main -r @-`  |
| Push main, when asked                           | `jj git push --bookmark main` |

Descriptions use an imperative subject, a blank line, and a plain-language
body explaining why. Use real newlines, not literal `\n` sequences:

```sh
jj describe -m 'Use a shared contributor guide

Keep the journal, formatting, task, and version-control rules in one place
so contributors and agents follow the same workflow.'
```

### Non-interactive agent commands

Always pass `-m` to `describe`, `new`, and `commit` when creating a described
change. Never invoke an editor or interactive selector from an agent session.
For a change that needs splitting, use `jj split <path>... -m '<message>'`;
this puts the named paths in the first change and the remainder in the second.
Inspect and describe both results. For an authorized squash, use
`jj squash --from <rev> --into <rev> -m '<message>'`, or
`--use-destination-message` when keeping the destination description.
Do not pass `-i`, `--interactive`, `--tool`, or `--editor`. Do not abandon,
restore over, or rewrite someone else's work to organize your own changes.

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

## Codex stop-time review gate

A stop-time Codex review gate is enabled for this repo (set up via `/codex-jj:setup --enable-review-gate`). Before stop, a fresh Codex review may be required. The plugin lives outside this repo at `/Users/skeswa/repos/skeswa/codex-plugin-cc`.

## PRD and spec review precedent

Spec changes in this repo are expected to survive a Codex review pass. The first PRD's review found three v1-scope contradictions (config layering, Codex harness, `kk reopen`), all resolved before the PRD was folded into the book. When editing the reference book, cross-check against `docs/reference/book/02-invariants.md` and neighboring chapters before publishing.
