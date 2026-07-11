# Publishing

`kk publish` publishes a thread to GitHub through `gh`. The flag surface lives in [Commands](11-commands.md#kk-publish); this chapter owns the behavior.

Publishing is the point where local work becomes reviewer-facing. That boundary is why PR prose is human territory and why the transcript is not input to template generation or later AI drafting.

Stack-aware publishing is the first v1.x workflow planned after the coordination acceptance slice. No acceptance-slice lifecycle or cascade operation requires `gh`, a GitHub account, or network access.

## Defaults

- PRs are draft by default; opening ready-for-review is an explicit flag.
- PR base is the parent thread's branch when stacked.
- Unstacked, detached, or parentless threads base on the repo default branch.
- If a parent is unpublished, `kk publish` publishes unpublished ancestors first, top-down.
- Each PR in a stack publish gets its own editor session, top-down.

PR base resolution:

The repo default branch is resolved through `gh repo view --json defaultBranchRef` when publishing. The child base rule is evaluated after any required ancestor publication, so a newly published parent branch can become the child's PR base in the same top-down publish flow.

Stack publish:

Publishing is manual by default. Configurable eager modes may later push or open draft PRs automatically, but exploratory threads should not become reviewer-facing merely because they exist.

Before presenting the publish plan for approval, kiki pins the current operation view and exact `thread_head_commit_id`, validates the v1 linear owned stack, and includes that head in the plan digest. After approval and immediately before pushing, it proves the head is unchanged and checkpoints the thread bookmark to that exact commit. A changed head invalidates the approval and regenerates the plan; kiki never pushes whichever older commit the bookmark happened to retain.

## PR text

The first publishing release opens a deterministic, human-editable PR title/body template derived from explicit command input and non-transcript thread metadata. It performs no model call. AI drafting is deferred with the metadata execution loop; it may later draft from the diff and publishable thread metadata after explicit invocation.

The transcript is never input to PR drafting.

After PR creation, title/body are human territory. Kiki does not silently overwrite them. In the first publishing release, `kk publish --refresh` explicitly regenerates the deterministic template; after AI drafting ships, the command must state which generator it will invoke before asking for approval.

## GitHub events

Polling, comments, CI presentation, and automatic merge handling are later v1.x work after manual publishing.

- merged PR: notify and update thread/PR state; still-later auto-archive may add close/archive with a 5000ms (5-second) undo grace, surfaced in the overlay as an actionable toast with an `undo` action.
- closed without merge: notify only.
- CI state change: notify only.
- review comment: expose read-only through `kk thread comments`.
- external force-push: mark remote divergence and require explicit reconciliation.

The first publishing release uses `gh` as the GitHub backend. The architecture keeps this behind a `GitHubBackend` trait so a direct REST or GraphQL backend can replace it later.

`gh` authentication is reused from the user's machine. `kk init` never requires or validates it. `kk publish` performs the required repository and authentication preflight immediately before making remote changes; `kk doctor --github` offers the same check without publishing. Kiki does not introduce separate GitHub credentials in v1.x.

Publishing is externally visible and always uses the two-phase foreground flow. `BeginApproval` returns the exact thread heads, checkpoints, resolved remotes/bases, PR text hashes, operation, and security-relevant flags for the presenter to show. An approval for one PR or one stack plan cannot authorize a later refresh, force-push, comment, changed text, or different stack. Non-interactive publishing is unavailable in v1.x unless the authority model is explicitly revised.
