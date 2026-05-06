# Publishing spec

`kk publish` publishes a thread to GitHub through `gh`.

## Defaults

- PRs are draft by default.
- `--ready` opens ready for review.
- PR base is the parent thread's branch when stacked.
- Unstacked, detached, or parentless threads base on the repo default branch.
- If a parent is unpublished, `kk publish` publishes unpublished ancestors first, top-down.

## PR text

Kiki may AI-draft the PR title and body from diff and thread metadata.

The transcript is not input to PR drafting in v1.

After PR creation, title/body are human territory. Kiki does not silently overwrite them. `kk publish --refresh` is the explicit regeneration path.

## Flags

- `--no-edit`: use the draft as-is.
- `--no-ai`: open an empty editor draft.
- `-m "<title>"`: set title inline.
- `--downstack`: publish current thread plus unpublished descendants.

## GitHub events

v1 may poll GitHub through `gh`.

- merged PR: close/archive with a 5000ms (5-second) undo grace, if auto-archive ships. The TUI surfaces the grace as an actionable toast with an `undo` action.
- closed without merge: notify only.
- CI state change: notify only.
- review comment: expose read-only through `kk thread comments`.
- external force-push: mark remote divergence and require explicit reconciliation.
