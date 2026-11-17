# Publishing

`kk publish` publishes a [thread](appendix-a-glossary.md#thread) to GitHub through [`gh`](https://cli.github.com/), GitHub's official command-line tool. (A thread is kiki's unit of work: a themed sequence of revisions.) The flag surface lives in [Commands](09-commands.md#kk-publish); this chapter owns the behavior.

Publishing is the moment local work becomes visible to reviewers. It opens a [pull request](https://docs.github.com/en/pull-requests) (PR), a request to merge a branch that others can review. That boundary is why PR prose belongs to the human. It is also why the agent [transcript](appendix-a-glossary.md#thread-transcript) is never used as input to template generation or to later AI drafting.

Stack-aware publishing is the first [v1.x](appendix-a-glossary.md#v1-x-polish) workflow planned after the coordination [acceptance slice](appendix-a-glossary.md#acceptance-slice) (kiki's first shippable milestone). No acceptance-slice lifecycle or cascade operation requires `gh`, a GitHub account, or network access.

## Defaults

This section lists what `kk publish` does when you give it no extra instructions. It also says how kiki makes sure it pushes exactly the commit the human approved.

- PRs open as drafts by default. Opening one ready-for-review requires an explicit flag.
- When a thread is stacked on a parent, its PR base, the branch the PR merges into, is the parent thread's branch. (A thread is stacked on a parent when it [follows](appendix-a-glossary.md#follows) that parent thread.)
- Unstacked, detached, or parentless threads use the repo default branch as the base.
- If a parent is unpublished, `kk publish` publishes the unpublished ancestors first, top-down.
- Each PR in a stack publish gets its own editor session, top-down.

PR base resolution:

At publish time, kiki resolves the repo default branch through `gh repo view --json defaultBranchRef`. kiki evaluates the child's base rule after publishing any required ancestors. So a parent branch published moments earlier can become the child's PR base in the same top-down publish flow.

Stack publish:

Publishing is manual by default. Configurable eager modes may later push or open draft PRs automatically. Even then, exploratory threads should not become reviewer-facing merely because they exist.

### Pinning the head before the push

Before presenting the publish plan for approval, kiki does two things in order:

1. It takes the [boundary snapshot](appendix-a-glossary.md#boundary-snapshot) under the same rule as close preflight. The boundary snapshot records the workspace's tracked edits in [jj](https://docs.jj-vcs.dev/latest/), the version-control tool kiki drives.
2. It then pins the current [operation](https://docs.jj-vcs.dev/latest/operation-log/) view and the exact `thread_head_commit_id`, the commit at the thread's [live head](appendix-a-glossary.md#live-head).

It validates the v1 linear [owned stack](appendix-a-glossary.md#owned-stack). It includes that head in the [plan digest](appendix-a-glossary.md#plan-digest) (a [hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function) of the plan).

### The checkpoint target

Publish pushes the thread [bookmark](appendix-a-glossary.md#bookmark), so it first picks where the bookmark should go. A bookmark is jj's named pointer to a revision. The place is the [checkpoint target](appendix-a-glossary.md#checkpoint-target) for the pinned head, chosen by the one rule in [Threads](03-threads.md#what-a-checkpoint-does):

- It is the head itself, unless the head is empty and undescribed.
- For an empty, undescribed head, kiki walks back along the owned chain to the nearest commit that is not both empty and undescribed. jj leaves such an empty commit behind after `jj commit`, and it has nothing to publish.
- If the walk leaves the owned chain without finding one, publish refuses with "nothing to checkpoint".

### The description check

jj refuses to push a commit that has no description. So publish checks first, before it places the bookmark. It looks at every commit the push would send: the checkpoint target and each commit below it on the owned chain that the remote does not have yet.

If any of those commits has no description, publish refuses and names the commits. Nothing is placed and nothing is pushed. The human adds the descriptions and runs `kk publish` again.

### Placing the bookmark and pushing

After approval, and immediately before pushing, kiki proves the head is unchanged. It then checkpoints the thread bookmark to the checkpoint target.

That checkpoint is an explicit placement (see [checkpoint placement](appendix-a-glossary.md#checkpoint-placement)). It records the placement and resets the [expected bookmark target](appendix-a-glossary.md#expected-bookmark-target) to the pushed commit. Like every checkpoint, it only moves the bookmark forward along the owned chain.

Four things stop the push:

- An unresolved bookmark [projection issue](appendix-a-glossary.md#projection-issue) ([`BookmarkMissing`](appendix-a-glossary.md#bookmarkmissing), [`BookmarkMoved`](appendix-a-glossary.md#bookmarkmoved), [`BookmarkConflicted`](appendix-a-glossary.md#bookmarkconflicted), or `CheckpointAbandoned`) blocks the checkpoint. So kiki never pushes through a bookmark whose target it cannot explain.
- A [checkpoint relationship](appendix-a-glossary.md#checkpoint-relationship) of `ahead` or `diverged` blocks the checkpoint, because the placement would move the bookmark backward or sideways. Publish stays blocked until the human applies [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target).
- A commit without a description fails the description check above.
- If the head has changed, the approval is invalid and kiki regenerates the plan.

kiki never pushes whichever older commit the bookmark happened to retain.

## PR text

This section says where the PR's title and body come from, and who owns them afterward. The short version: kiki fills in a plain template, and after that the words belong to the human.

The first publishing release opens a deterministic, human-editable PR title/body template. Deterministic means the same input always gives the same text.

- The template is built from explicit command input and non-transcript thread metadata.
- It performs no model call.

AI drafting is deferred; it ships with the metadata execution loop (see [Metadata Evolution](08-metadata.md)). Once it ships, it may draft from the diff and publishable thread metadata, and only after explicit invocation.

The transcript is never input to PR drafting.

After PR creation, the title and body are human territory. kiki does not silently overwrite them. In the first publishing release, `kk publish --refresh` explicitly regenerates the deterministic template. After AI drafting ships, the command must state which generator it will invoke before asking for approval.

## GitHub events

After a PR exists, things happen to it on GitHub: it gets merged, closed, tested, or commented on. This section says how kiki will react to each event, and how publishing is authenticated and approved.

Polling, comments, [CI](https://en.wikipedia.org/wiki/Continuous_integration) (continuous integration, automated checks on each change) presentation, and automatic merge handling are later v1.x work, after manual publishing.

- **Merged PR:** kiki notifies and updates thread/PR state. Still later, auto-archive may propose closing the merged thread: a toast whose `review` action opens the ordinary close approval card. (A toast is a small pop-up notice.) Auto-archive never closes a thread by itself; a close always consumes a one-shot approval.
- **Closed without merge:** kiki notifies only.
- **CI state change:** kiki notifies only.
- **Review comment:** kiki exposes it read-only through `kk thread comments`.
- **External force-push:** someone rewrote the remote branch's history from outside kiki. kiki marks remote divergence and requires explicit reconciliation.

### Backend and authentication

The first publishing release uses `gh` as the GitHub backend. The architecture keeps this behind a `GitHubBackend` [trait](https://doc.rust-lang.org/book/ch10-02-traits.html), a swappable interface, so a direct REST or GraphQL backend can replace it later.

kiki reuses the `gh` authentication already on the user's machine.

- `kk init` never requires or validates it.
- `kk publish` performs the required repository and authentication preflight immediately before making remote changes.
- `kk doctor --github` offers the same check without publishing.
- kiki does not introduce separate GitHub credentials in v1.x.

### Approval

Publishing is externally visible, so it always uses the two-phase foreground flow: kiki presents a plan, and pushes only after the human approves that exact plan (see [human approval](appendix-a-glossary.md#human-approval)).

`BeginApproval` returns these items for the presenter to show:

- the exact thread heads;
- checkpoints;
- resolved remotes/bases;
- PR text hashes;
- the operation; and
- security-relevant flags.

An approval covers one PR or one stack plan. It cannot authorize a later refresh, force-push, comment, changed text, or different stack. Non-interactive publishing is unavailable in v1.x unless the authority model is explicitly revised.
