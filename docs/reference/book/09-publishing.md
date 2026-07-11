# Publishing

`kk publish` publishes a thread to GitHub through `gh`. The flag surface lives in [Commands](11-commands.md#kk-publish); this chapter owns the behavior.

Publishing is the point where local work becomes reviewer-facing. That boundary is why PR prose is human territory and why the transcript is not input to the drafter.

## Defaults

- PRs are draft by default; opening ready-for-review is an explicit flag.
- PR base is the parent thread's branch when stacked.
- Unstacked, detached, or parentless threads base on the repo default branch.
- If a parent is unpublished, `kk publish` publishes unpublished ancestors first, top-down.
- Each PR in a stack publish gets its own editor session, top-down.

PR base resolution:

The repo default branch is resolved through `gh repo view --json defaultBranchRef` in v1. The child base rule is evaluated after any required ancestor publication, so a newly published parent branch can become the child's PR base in the same top-down publish flow.

Stack publish:

Publishing is manual by default. Configurable eager modes may later push or open draft PRs automatically, but exploratory threads should not become reviewer-facing merely because they exist.

## PR text

Kiki may AI-draft the PR title and body from diff and thread metadata.

The transcript is not input to PR drafting in v1.

After PR creation, title/body are human territory. Kiki does not silently overwrite them. `kk publish --refresh` is the explicit regeneration path.

## GitHub events

v1 may poll GitHub through `gh`.

- merged PR: notify and update thread/PR state; that is the acceptance-slice behavior. The v1.x auto-archive polish adds close/archive with a 5000ms (5-second) undo grace, surfaced in the TUI as an actionable toast with an `undo` action.
- closed without merge: notify only.
- CI state change: notify only.
- review comment: expose read-only through `kk thread comments`.
- external force-push: mark remote divergence and require explicit reconciliation.

v1 uses `gh` as the GitHub backend. The architecture keeps this behind a `GitHubBackend` trait so a direct REST or GraphQL backend can replace it later.

`gh` authentication is reused from the user's machine. kiki does not introduce separate GitHub credentials in v1.
