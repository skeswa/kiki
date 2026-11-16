# Publishing

`kk publish` publishes a thread to GitHub through `gh`, GitHub's official command-line tool. The flag surface lives in [Commands](09-commands.md#kk-publish); this chapter owns the behavior.

Publishing is the moment local work becomes visible to reviewers. That boundary is why PR prose belongs to the human. It is also why the agent transcript is never used as input to template generation or to later AI drafting.

Stack-aware publishing is the first v1.x workflow planned after the coordination acceptance slice (kiki's first shippable milestone). No acceptance-slice lifecycle or cascade operation requires `gh`, a GitHub account, or network access.

## Defaults

- PRs open as drafts by default. Opening one ready-for-review requires an explicit flag.
- When a thread is stacked on a parent, its PR base — the branch the PR merges into — is the parent thread's branch.
- Unstacked, detached, or parentless threads use the repo default branch as the base.
- If a parent is unpublished, `kk publish` publishes the unpublished ancestors first, top-down.
- Each PR in a stack publish gets its own editor session, top-down.

PR base resolution:

At publish time, kiki resolves the repo default branch through `gh repo view --json defaultBranchRef`. kiki evaluates the child's base rule after publishing any required ancestors. So a parent branch published moments earlier can become the child's PR base in the same top-down publish flow.

Stack publish:

Publishing is manual by default. Configurable eager modes may later push or open draft PRs automatically. Even then, exploratory threads should not become reviewer-facing merely because they exist.

Before presenting the publish plan for approval, kiki pins the current operation view and the exact `thread_head_commit_id` — the commit at the thread's live head. It validates the v1 linear owned stack. It includes that head in the plan digest. After approval, and immediately before pushing, kiki proves the head is unchanged. It then checkpoints the thread bookmark to that exact commit. That checkpoint is an explicit placement: it records the placement and resets the expected bookmark target to the pushed commit. An unresolved bookmark projection issue (`BookmarkMissing`, `BookmarkMoved`, or `BookmarkConflicted`) blocks it, so kiki never pushes through a bookmark whose target it cannot explain. If the head has changed, the approval is invalid and kiki regenerates the plan. kiki never pushes whichever older commit the bookmark happened to retain.

## PR text

The first publishing release opens a deterministic, human-editable PR title/body template. The template is built from explicit command input and non-transcript thread metadata. It performs no model call. AI drafting is deferred; it ships with the metadata execution loop. Once it ships, it may draft from the diff and publishable thread metadata, and only after explicit invocation.

The transcript is never input to PR drafting.

After PR creation, the title and body are human territory. kiki does not silently overwrite them. In the first publishing release, `kk publish --refresh` explicitly regenerates the deterministic template. After AI drafting ships, the command must state which generator it will invoke before asking for approval.

## GitHub events

Polling, comments, CI presentation, and automatic merge handling are later v1.x work, after manual publishing.

- merged PR: kiki notifies and updates thread/PR state. Still later, auto-archive may add close/archive with a 5000ms (5-second) undo grace, shown in the overlay as an actionable toast with an `undo` action.
- closed without merge: kiki notifies only.
- CI state change: kiki notifies only.
- review comment: kiki exposes it read-only through `kk thread comments`.
- external force-push: someone rewrote the remote branch's history from outside kiki. kiki marks remote divergence and requires explicit reconciliation.

The first publishing release uses `gh` as the GitHub backend. The architecture keeps this behind a `GitHubBackend` trait — a swappable interface — so a direct REST or GraphQL backend can replace it later.

kiki reuses the `gh` authentication already on the user's machine. `kk init` never requires or validates it. `kk publish` performs the required repository and authentication preflight immediately before making remote changes. `kk doctor --github` offers the same check without publishing. kiki does not introduce separate GitHub credentials in v1.x.

Publishing is externally visible, so it always uses the two-phase foreground flow: kiki presents a plan, and pushes only after the human approves that exact plan. `BeginApproval` returns the exact thread heads, checkpoints, resolved remotes/bases, PR text hashes, operation, and security-relevant flags for the presenter to show. An approval covers one PR or one stack plan. It cannot authorize a later refresh, force-push, comment, changed text, or different stack. Non-interactive publishing is unavailable in v1.x unless the authority model is explicitly revised.
