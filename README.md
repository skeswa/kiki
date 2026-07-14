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

Read the spec and [open an issue](https://github.com/skeswa/kiki/issues) if a design choice looks wrong or incomplete. This is the point when objections can still reshape the implementation.

## License

[MIT](LICENSE) © 2026 Sandile Keswa
