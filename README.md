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

Start an auth refactor. Hand the tests to another agent, then chase an unrelated bug while both agents run. That should feel normal, not like a bookkeeping stunt.

kiki (`kk`) gives each line of work a **thread**. A thread combines a [jj](https://github.com/jj-vcs/jj) workspace, a [tmux](https://github.com/tmux/tmux) session, an agent session, and a live head in the repository history. Threads can follow one another. When a parent changes, kiki waits for the child agent to reach a safe boundary, updates its workspace, and tells the agent what moved.

```sh
kk new auth-refactor
kk new add-tests --follows auth-refactor
kk new investigate-login-bug
kk switch add-tests
```

You keep using `jj`, `tmux`, and `gh` directly. kiki handles the thread bookkeeping around them.

> [!IMPORTANT]
> kiki is pre-alpha. The design is written, but implementation has not started. There is nothing to install yet.

The [reference book](docs/reference/README.md) covers commands, safety rules, architecture, scope, and the roadmap. The [orientation](docs/reference/book/01-orientation.md) is the shortest tour of the planned first release.

The [project journal](journal/README.md) connects investigations, evidence, and the [decision log](journal/decisions/README.md). Start there to understand what has been researched and why a design choice was made.

Read the spec and [open an issue](https://github.com/skeswa/kiki/issues) if a design choice looks wrong or incomplete. This is the point when objections can still reshape the implementation.

## Documentation site

The reference book is also a VitePress site. The site deploys to GitHub Pages from `main`, while pull requests run the same strict docs and production-build checks without deploying.

```sh
mise install         # install the pinned tooling
mise run setup       # install locked documentation dependencies
mise run dev         # local documentation server
mise run fmt         # format handwritten code and docs
mise run check       # formatting, links, contract terms, and production build
mise run preview     # preview the last production build
```

GitHub Pages must use **GitHub Actions** as its publishing source. The project-pages base path defaults to `/kiki/`; set `VITEPRESS_BASE` and `VITEPRESS_SITE_URL` when moving to a custom domain.

Tasks live in [mise.toml](mise.toml); `mise tasks` lists them. The existing Bun
scripts delegate to those tasks. Formatting uses pinned Oxfmt and Taplo and
works before installing the site's dependencies. Captured evidence and the
dated research reports are excluded from automatic formatting. See
[AGENTS.md](AGENTS.md) for the contributor workflow.

## License

[MIT](LICENSE) © 2026 Sandile Keswa
