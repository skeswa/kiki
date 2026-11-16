<div align="center">

<br />

<h1>
  💅🏾
  <br />
  kiki
</h1>

<h3>Give every agent its own thread.</h3>

<p>Coordinate several lines of coding work without losing the plot.</p>

<p>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg" /></a>
  <a href="docs/reference/README.md"><img alt="Status: pre-alpha" src="https://img.shields.io/badge/status-pre--alpha-orange" /></a>
  <a href="https://github.com/jj-vcs/jj"><img alt="VCS: jujutsu" src="https://img.shields.io/badge/vcs-jujutsu-purple" /></a>
</p>

</div>

Start an auth refactor. Hand the tests to another coding agent, then chase an unrelated bug while both agents run. That should feel normal, not like a bookkeeping stunt.

kiki (`kk`) gives each line of work a **[thread](docs/reference/book/appendix-a-glossary.md#thread)**. A thread combines four things:

- a [jj](https://github.com/jj-vcs/jj) [workspace](docs/reference/book/appendix-a-glossary.md#workspace): its own working directory in [Jujutsu](https://docs.jj-vcs.dev/latest/), a version-control tool that works with [Git](https://git-scm.com/);
- a [terminal group](docs/reference/book/appendix-a-glossary.md#terminal-group) in [Herdr](https://github.com/herdrdev/herdr), a [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer) (a program that runs many terminals at once);
- an agent session, such as [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) or [Codex](https://github.com/openai/codex);
- a [live head](docs/reference/book/appendix-a-glossary.md#live-head): the thread's newest commit in the repository history.

Threads can [follow](docs/reference/book/appendix-a-glossary.md#follows) one another. When a parent thread changes, kiki does three things:

1. It waits for the child agent to reach a [safe boundary](docs/reference/book/appendix-a-glossary.md#safe-boundary), a moment when the agent is not in the middle of an edit.
2. It updates the child's workspace.
3. It tells the agent what moved.

```sh
kk new auth-refactor
kk new add-tests --follows auth-refactor
kk new investigate-login-bug
kk switch add-tests
```

You keep using `jj`, [`gh`](https://cli.github.com/) (the GitHub command-line tool), and Herdr's own terminal controls directly. kiki handles the thread bookkeeping around them.

> [!IMPORTANT]
> kiki is pre-alpha, which means it is not built yet. The design is written, but implementation has not started. There is nothing to install.

The [reference book](docs/reference/README.md) covers commands, safety rules, architecture, scope, and the roadmap. The [orientation](docs/reference/book/01-orientation.md) is the shortest tour of the planned first release.

The [project journal](journal/README.md) connects investigations, evidence, and the [decision log](journal/decisions/README.md). Start there to learn what has been researched and why a design choice was made.

Read the spec. If a design choice looks wrong or incomplete, [open an issue](https://github.com/skeswa/kiki/issues). Objections can still reshape the implementation at this point.

## Documentation site

The reference book is also a [VitePress](https://vitepress.dev/) site (VitePress turns Markdown files into a website). The site deploys to GitHub Pages from `main`. [Pull requests](https://docs.github.com/en/pull-requests) run the same strict docs and production-build checks without deploying.

```sh
mise install         # install the pinned tooling
mise run vcs:init    # once per Git clone: initialize colocated jj
mise run setup       # install locked documentation dependencies
mise run dev         # local documentation server
mise run fmt         # format handwritten code and docs
mise run check       # formatting, links, contract terms, and production build
mise run preview     # preview the last production build
```

GitHub Pages must use **GitHub Actions** as its publishing source. The project-pages base path defaults to `/kiki/`. Set `VITEPRESS_BASE` and `VITEPRESS_SITE_URL` when moving to a custom domain.

Tasks live in [mise.toml](mise.toml), and `mise tasks` lists them. (mise is
the tool that installs this project's pinned tools and runs its tasks.) The
existing Bun scripts hand off to those tasks. Formatting uses pinned Oxfmt and
Taplo. It works before you install the site's dependencies. Captured evidence
and the dated research reports are excluded from automatic formatting. See
[AGENTS.md](AGENTS.md) for the contributor workflow.

Use `jj` for version control. The checkout is
[colocated](https://docs.jj-vcs.dev/latest/git-compatibility/): jj and Git
share the same directory. GitHub remains the remote host, and `main` tracks
`main@origin`. Each logical change gets a described jj revision. The
[VCS guidance](AGENTS.md#version-control) covers draft changes and the
commands for an authorized commit or push.

## License

[MIT](LICENSE) © 2026 Sandile Keswa
