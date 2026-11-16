# Op-log watcher

[jj](https://docs.jj-vcs.dev/latest/) records every change to a repository as an _operation_ in its [operation log](https://docs.jj-vcs.dev/latest/operation-log/) ("op log"). The [op-log watcher](../appendix-a-glossary.md#op-log-watcher) is the part of [`kkd`](../appendix-a-glossary.md#kkd), kiki's background program, that reads this log. It is `kkd`'s window into jj.

The watcher detects external operations. These are operations kiki did not run itself: a human's, an agent's through Bash, or a sibling tool's. It feeds what it finds to two consumers:

- the cascade orchestrator, which runs [cascade reconciliation](../appendix-a-glossary.md#cascade-reconciliation);
- the [transcript](../appendix-a-glossary.md#thread-transcript) backfill path.

## Mechanism

An operation _head_ is an operation that has no later operation built on it. Usually there is one head. When two jj commands run at the same time, there can be several ([jj concurrency](https://docs.jj-vcs.dev/latest/technical/concurrency/)). The set of current heads is the [operation frontier](../appendix-a-glossary.md#operation-frontier).

- **Sampling.** An [`OpFrontierSampler`](../appendix-a-glossary.md#frontier-sampler) reads the complete current set of operation heads without loading the repository.
  - It is a versioned adapter.
  - For the supported jj range, it lists the main repository's operation-head store, `<main workspace>/.jj/repo/op_heads/heads/`. That directory holds one file per head.
  - An added [workspace](../appendix-a-glossary.md#workspace) has no store of its own. Its `.jj/repo` is a file that names the main repository's directory. The sampler resolves that pointer before it watches or reads anything.
- **Change detection.** `fsnotify` (a [file-change notification](https://en.wikipedia.org/wiki/Inotify) library) watches that resolved `heads/` directory. It is change detection only.
  - A watch on its parent `op_heads/` directory does not see head changes.
  - Every wake-up reruns the sampler. So does a periodic timer that covers missed events.
  - The event itself carries no meaning.
- **Debounce.** The watcher waits 250ms per repo before it triggers cascade evaluation. This wait (a debounce) lets a burst of changes settle first.
- **Per-op evaluation.** For each operation, the watcher compares the before and after commits of each managed workspace. It validates actual ancestry for the affected [follows](../appendix-a-glossary.md#follows) edges.
  - A live parent's exact workspace `@`/`thread_head_commit_id` drives follows classification. Its [bookmark](../appendix-a-glossary.md#bookmark) does not. ([`@`](https://docs.jj-vcs.dev/latest/glossary/) is jj's name for a workspace's working-copy commit.)
  - Bookmark changes feed [Checkpoint tracking](#checkpoint-tracking) and the projection audit only.
  - The cost is O(threads × ancestry-depth) per op. That is acceptable in practice for v1.

### Frontier sampling is a proof requirement

jj 0.46.0 has no supported, side-effect-free interface that lists every operation head. No command flag, template keyword, or `jj debug` subcommand does it. The sampler therefore depends on jj's internal store layout.

That dependency is confined to the adapter:

- The adapter checks the pinned jj version and the store's `op_heads/type` marker before it trusts a listing.
- It reports `Unavailable` for a layout it does not recognize.
- While sampling is unavailable, the watcher is degraded and says so.
- While sampling is unavailable, `RefreshToFrontier` [fails closed](../appendix-a-glossary.md#fail-closed) (it refuses instead of guessing). Every lifecycle command that depends on it refuses too.

Two items remain open in the implementation gate: a stable sampler, and the sampler's behavior while jj replaces one head with another.

`jj op log` polling is not a fallback. kiki does not use it to discover the frontier. Three measured behaviors rule it out:

1. With more than one head, `jj op log` merges them. It writes a new "reconcile divergent operations" operation as a side effect, even under `--ignore-working-copy`.
2. Without `--ignore-working-copy`, it also [snapshots](https://docs.jj-vcs.dev/latest/working-copy/) the working copy. (A snapshot records the files on disk into a commit.)
3. It can only ever print one head. So it cannot report the state it just destroyed.

### Pinned reads and pinned mutations

A _pinned_ jj command names the exact operation it should run against. A [pinned read](../appendix-a-glossary.md#pinned-read) lets kiki look at the repository without changing it.

Kiki never observes a managed repository through an unpinned jj command.

- Every read names an exact operation id and ignores the working copy.
- So does every repository mutation that does not have to write a working copy.
- The only unpinned jj commands are those on the closed list in [Invariants](../02-invariants.md#operation-history-is-a-dag): the working-copy commands, [deliberate integration](../appendix-a-glossary.md#deliberate-integration), and the human passthroughs. That list is stated once, there.

The detailed rules:

- **Reads.** Every read names an exact operation and ignores the working copy: `jj --at-op=<op_id> --ignore-working-copy …`.
  - `<op_id>` is a full id the sampler returned, or an ancestor already recorded in `op_history`.
  - Such a read does not snapshot and does not merge heads.
  - It works in a [stale workspace](https://docs.jj-vcs.dev/latest/working-copy/) (one whose files are behind the repository). It works while several heads exist.
- **`--at-op=@` is not a pin.**
  - With one head, it still snapshots the working copy unless `--ignore-working-copy` is also given.
  - With several heads, it fails.
  - Kiki does not use it.
- **Unpinned commands are mutations.**
  - Any jj command that loads the repository without `--at-op` merges divergent heads.
  - `status`, `log`, `diff`, `show`, `evolog`, `op log`, `op show`, `bookmark list`, `workspace list`, and `file list` also snapshot the working copy of the workspace they run in.
  - An unpinned `jj workspace add` or `jj workspace forget` run from the main workspace snapshots the human's main working copy.
  - Kiki treats every unpinned command as a mutation of a managed repository, whatever its name suggests.
- **Pinned mutations.** These run at `--at-op=<head> --ignore-working-copy`: bookmark moves, rebases, abandons, pushes, the `jj new` and `jj edit` equivalents, and `jj workspace forget`.
  - `<head>` is the exact head the plan was validated against.
  - The result is a child of that head.
- **`jj workspace add` is pinned without the working-copy flag.**
  - It runs at `--at-op=<head>` and without `--ignore-working-copy`. It must write the new working copy, and jj refuses it otherwise.
  - It creates the workspace and its initial working-copy commit in one command, as two operations.
  - It snapshots no other working copy.
- **A pinned mutation can fork the frontier.**
  - If another operation lands between validation and the mutation, the result is a second head.
  - Pinning prevents a silent merge and a silent snapshot. It does not prevent concurrency.
  - The next sample shows both heads. [Checkpoint tracking](#checkpoint-tracking) scopes every placement by operation ancestry for exactly this reason.
- **Working-copy commands.** The [boundary snapshot](../appendix-a-glossary.md#boundary-snapshot) and `jj workspace update-stale` in a managed workspace must act on that workspace's working copy. So they cannot be pinned.
  - `kkd` runs each under the thread's [reconciliation lock](../appendix-a-glossary.md#reconciliation-lock), only after a sample shows exactly one head. It attributes the resulting operations.
  - It samples again afterward and reads the actual result from the resulting exact operation.
  - It never assumes the command acted on the view it sampled first.
  - The single-head precondition applies to these commands only.
  - [Cascade](../05-cascade.md#boundary-snapshot) defines the boundary snapshot.
- **Deliberate integration.** This is what kiki does when there are several heads and a step needs one view.
  - Under the owning lock, kiki runs one designated repository-loading command with `--ignore-working-copy`. It samples again. It requires a single head whose parents are the heads it sampled.
  - Integrating a planned `--no-integrate-operation` result with `jj op integrate` is the same act and follows the same rule.
  - An integration operation is attributed but never skipped. Its merged view can differ from every parent, so it is classified like any other multi-parent node.
- **Human passthroughs.** These are the body of `kk status`, and the overlay's `d` diff for the contextual thread.
  - The `kk` CLI runs them in the caller's own contextual workspace, at the human's explicit request.
  - `kkd` never runs them.
  - They may snapshot, like any direct jj use.
  - The status header, `kk status --no-jj`, `kk ls`, the watcher, and every background renderer use pinned reads only.

## Operation-DAG cache

jj's operations form a [DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph): a graph where an operation can have more than one parent and there are no cycles. kiki keeps its own copy of the parts it needs. This copy is the [operation-history cache](../appendix-a-glossary.md#operation-history-cache). It has four tables (see [State schema](schema.md)):

- Each observed operation node is persisted in `op_history(repo_id, op_id, committed_at, observed_at, processed_at?)`.
- Operation ancestry is normalized in `op_history_parents(repo_id, op_id, parent_op_id)`, with one row for every parent edge.
- Per-view workspace state lives in `op_workspace_heads(repo_id, op_id, workspace_id, change_id, commit_id)`.
- `op_watch_frontier(repo_id, op_id, observed_at)` stores the current known antichain of operation heads. (An antichain is a set in which no member is an ancestor of another.)

A singular `parent_op_id` or last-op cursor is not an acceptable implementation of this contract.

### Why the cache is per workspace

The **per-workspace** dimension of `op_workspace_heads` is load-bearing. jj's op log is repo-shared, but `@` is per-workspace. Two examples:

- One operation may change only workspace A's working-copy commit.
- An ancestor rewrite may evolve A, B, and C together, while each workspace retains a distinct `@`.

A repo-keyed cache cannot answer either of these questions: “what was workspace B's `@` at this op?” or “which managed workspaces evolved in this op?”

Transcript backfill uses this table to anchor rows:

- It joins `op_workspace_heads` to `op_history`.
- It may use `committed_at <= entry.timestamp` only after it restricts candidates to one operation-ancestry path that was observed for that workspace.
- If incomparable candidates have no unique ancestry maximum, the transcript row is `anchor_unknown` (see [`anchor_unknown=TRUE`](../appendix-a-glossary.md#anchor-unknown-true)).
- Wall-clock order must not choose an operation branch.

An `op_workspace_heads` row is inserted only when an op produces a _new_ `@` for the workspace in question, relative to at least one parent view. The transcript lookup uses "latest row at or before timestamp" semantics. Those semantics handle gaps only within the unique ancestry restriction above. Timestamps are never used to order or choose between incomparable jj operations.

### Updating the thread head

Sometimes a stable workspace id and canonical path identify exactly one managed workspace. Whenever they do, two writes occur in the same per-repo [transaction](https://en.wikipedia.org/wiki/Database_transaction): the insertion of a new workspace `@`, and the update of `threads.thread_head_commit_id` (the [thread head](../appendix-a-glossary.md#thread-head)).

- The row update follows the [unmerged-frontier](#unmerged-frontier) rule. It is written from a view every current head agrees on.
- This remains true when the thread is `ProjectionDiverged` solely because of a bookmark issue, [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing), or [`OrphanedProcess`](../appendix-a-glossary.md#orphanedprocess). Those issues do not make `@` ambiguous and must not freeze follows classification.
- A missing workspace record/directory or ambiguous path disables head updates until repair.

The persisted value is not copied to the bookmark.

- Kiki places the bookmark only at an explicit [placement](../appendix-a-glossary.md#checkpoint-placement): creation, publish, close, detach, or an applied bookmark repair plan (restore or adopt). Each is a journaled checkpoint.
- Between placements, the [expected bookmark target](../appendix-a-glossary.md#expected-bookmark-target) is `bookmark_expected_commit_id`. It follows jj's own rewrite successors under [Checkpoint tracking](#checkpoint-tracking).
- The expected target is never advanced because `@` advanced.

## Operation-DAG frontier

Jj operations form a DAG. They may have multiple concurrent heads, or an integration operation with multiple parents. The watcher therefore does not keep a scalar cursor (a single "last seen" position). It maintains the current observed head frontier plus per-node `processed_at`:

1. Sample the complete current head set through the [`OpFrontierSampler`](../appendix-a-glossary.md#frontier-sampler) and compare it with the durable `op_watch_frontier`. Persist newly observed heads before interpretation.
2. Discover every operation reachable from a current head whose `op_history.processed_at` is null or absent, including every parent edge.
3. Process the discovered subgraph in parent-before-child topological layers ([topological order](https://en.wikipedia.org/wiki/Topological_sorting)). Incomparable operations remain incomparable. `committed_at` never fabricates an order between them.
4. For an operation with multiple parents, query each parent's workspace views. If the result differs from more than one parent, classify against the durable follows anchors and normalized trigger set. If there is no single coherent [base transition](../appendix-a-glossary.md#base-transition), record `TopologyDiverged` rather than choosing a preferred parent.
5. Mark every completely interpreted node processed, and replace `op_watch_frontier` with the final sampled head antichain. Do both in the same per-repo transaction as the resulting `op_history`, `op_history_parents`, `op_workspace_heads`, head-cache, attribution, and intent changes.

Crash safety:

- A crash before the interpretation transaction leaves reachable nodes unprocessed. kiki safely replays them from the persisted or freshly sampled `op_watch_frontier`.
- Unique keys make replay [idempotent](https://en.wikipedia.org/wiki/Idempotence) (safe to repeat).
- An op integration may [coalesce](../appendix-a-glossary.md#coalescing) normalized trigger ids into one pre-materialization intent. It never rewrites the operation DAG into a false linear “through” range.

`RefreshToFrontier(repo_id)` is the synchronous form of this algorithm.

- It repeatedly samples the head set and processes the discovered DAG.
- It returns a pinned frontier/view only when the sampled head set is unchanged across the final persistence transaction.
- Detach, parent-close preflight, close's [post-freeze recheck](../appendix-a-glossary.md#post-freeze-recheck), and topology-sensitive repair must call it.
- Absence of an existing intent is not freshness evidence.

### Unmerged frontier

Several heads can persist until some jj command merges them. Kiki does not merge them by observing.

- **Every head is processed.** Every head's ancestry is processed as above. Some values are a function of one view: a workspace's `@`, a bookmark target, the expected checkpoint target. Such a value is evaluated per head and is never blended across heads.
- **Row caches wait for agreement.** A single-valued row cache (`threads.thread_head_commit_id`, `threads.bookmark_expected_commit_id`) is written only from a view every current head agrees on. While heads disagree about a thread:
  - its cache keeps the last agreed value;
  - status prints "frontier unmerged" in place of that thread's checkpoint relationship;
  - no [projection issue](../appendix-a-glossary.md#projection-issue) is raised from one head's view alone.
- **Callers that need one view.** Some callers of `RefreshToFrontier` need one view: a checkpoint, publish, detach, close, or an explicit rebase. Such a caller requests [deliberate integration](../appendix-a-glossary.md#deliberate-integration), then classifies the integration operation. If heads still disagree after the bounded retry, the caller fails without mutating.
- **kiki's own forks.** A kiki mutation can itself leave two heads. The [lifecycle journal](../appendix-a-glossary.md#lifecycle-journal) that made a placement owns the first integration operation after it. Under classifier rule 0, it re-evaluates the checkpoint target in the merged view and places again deterministically. It does not raise an issue against its own placement.
- **External merges.** When an external command merges the heads first, the merge is an ordinary multi-parent operation and step 4 applies. Two heads that each rewrote the same commit merge into divergent successors and a conflicted bookmark. Kiki reports that outcome and does not choose a side.

## Op attribution

Attribution means knowing which operations kiki itself wrote. jj offers no way to set an operation's description from the command line. So kiki does not mark its operations in their text. It attributes them two ways:

1. Every jj command `kkd` runs carries a per-invocation operation user and host in its configuration. jj records these on each operation the command writes.
2. `kkd` records, in `op_attribution`, every operation id each command wrote. These are the operations that are reachable from the post-command sample, are not reachable from the pre-command head, and carry that invocation's operation user.

One command can write several operations. For example, `jj workspace add` writes two. Each is recorded.

Attribution suppresses one thing only. The watcher does not open a new cascade intent in reaction to an operation the initiating handler already accounted for.

- Classification still runs on every operation, kiki's included.
- The checkpoint classifier, the workspace-head cache, and the projection audit read attributed operations exactly as they read external ones.
- A kiki rebase that carries bookmarks therefore appends a succession row for every thread whose bookmark it carried.

External ops (`op_id` not in `op_attribution`) pass through reconciliation classification. Classification is based on state, not command name:

- if the exact evolved parent base is already an ancestor of the managed child's current repository commit, record [`NativeRewrite`](../appendix-a-glossary.md#nativerewrite) with the exact old-base → evolved-base ids; the child's before/after commits are evidence, not the pinned target;
- if the parent's exact live head advances to a new tip not already in the child's ancestry, record [`ParentAdvance`](../appendix-a-glossary.md#parentadvance) with that exact destination commit;
- if the new topology is ambiguous, backward-moving, conflicted, or inconsistent with the [follows edge](../appendix-a-glossary.md#follows-edge), record [`TopologyDiverged`](../appendix-a-glossary.md#topologydiverged).

Bookmark changes are kept apart from follows classification:

- Moving, deleting, or recreating the parent bookmark never creates `ParentAdvance`.
- A bookmark change is classified only by [Checkpoint tracking](#checkpoint-tracking). Follows edges continue to use pinned commits and observed live heads.
- The two classifications are independent.
- For example, `jj abandon` deletes a bookmark on the abandoned commit by default. So one external operation can produce both [`BookmarkMissing`](../appendix-a-glossary.md#bookmarkmissing) for the bookmark and `TopologyDiverged` for the abandoned head or owned revision.
- Neither result suppresses or outranks the other.

### Linear owned-stack validation

In v1, kiki rebases a child only when the child's [owned stack](../appendix-a-glossary.md#owned-stack) is a simple straight line of commits. This section says how kiki checks that.

The classifier validates the v1 owned-stack contract against one pinned operation view. It does so before recording a rebasable `ParentAdvance`, and again immediately before executing it.

Let `B` be the exact last-synchronized base, `H` the child's exact live head, and `S` the revisions reachable from `H` after excluding ancestors of `B`. Kiki requires:

1. `B` is an ancestor of `H`.
2. `S` has exactly one root and that root's sole parent is `B`.
3. Every revision in `S` has one parent and forms one uninterrupted chain to `H`; merges, multiple roots, and conflicted topology fail validation.
4. Descendants of `S` outside that chain are completely accounted for by recursively valid registered follows children. Any unregistered or ambiguous descendant is foreign topology.

What follows from the check:

- The explicit rebase names the exact validated members of `S`. It never uses a dynamic all-descendants selector.
- Failure of any condition records `TopologyDiverged` on the intent, with the pinned evidence.
- Kiki does not choose a likely root, silently absorb a revision, or perform a partial rebase.
- The discrepancy may concern a missing/moved external projection rather than revision ancestry. In that case kiki records `ProjectionDiverged` as described below.

A single external op may logically evolve multiple workspaces in A→B→C. The watcher records a separate base-transition intent for every affected workspace. It does not pretend repository evolution occurred one hop at a time.

#### Operations do not prove freshness

The watcher detects repository transitions, not every file [materialization](../appendix-a-glossary.md#materialization) (the update of a workspace's files on disk). A direct `jj workspace update-stale` may or may not produce an operation:

- In a non-colocated repository, updating a clean stale workspace changes its files and leaves the head set unchanged.
- In a [colocated](https://docs.jj-vcs.dev/latest/git-compatibility/) repository (jj 0.46's default for `jj git init`), the same update writes a "reset git head" operation.
- Updating a dirty stale workspace writes a snapshot operation and an operation that reconciles it with the rewrite.

The presence or absence of an operation therefore proves nothing about freshness. [`WorkspaceProbe`](../appendix-a-glossary.md#workspaceprobe) at the next managed boundary is the authority on current freshness.

#### kiki's own explicit advance

For a kiki-initiated explicit advance, the watcher opens no new cascade intent, because the operation is attributed.

- Workspace heads and checkpoint tracking are still classified from it.
- Its reconciliation handler compares the starting and resulting operation views before completing the intent.
- Any other workspace jj evolved receives a `NativeRewrite` intent in the same durable result-recording step.

See [Cascade](../05-cascade.md) and [Native evolution](../17-decisions/native-evolution.md).

## Checkpoint tracking

A [bookmark](https://docs.jj-vcs.dev/latest/bookmarks/) is jj's named pointer to a commit. jj moves a bookmark along with the commit it names.

- Each of these replaces the commit with a successor and carries the bookmark to it, with no bookmark command: a snapshot, `jj describe`, a rebase, a squash into the commit, or an ancestor rewrite made from another workspace.
- The first ordinary edit after thread creation does exactly this.
- `jj new` and `jj commit` do not. They move `@` and leave the bookmark behind.

Kiki therefore keeps four facts apart ([D-0005](https://github.com/skeswa/kiki/blob/main/journal/decisions/0005-track-checkpoint-through-native-successors.md)):

1. **Placement.** Where an explicit checkpoint put the bookmark. Each placement appends an immutable `thread_checkpoints` row and sets `checkpoint_commit_id`, `checkpoint_change_id`, and `checkpoint_op_id`.
2. **Native successor tracking.** jj carried the bookmark to a proven rewrite successor, or back to an earlier one (see [native successor](../appendix-a-glossary.md#native-successor)). Kiki appends a `thread_checkpoint_successions` row and updates `bookmark_expected_commit_id`. No issue is raised.
3. **External movement.** Any other change of target is a [projection issue](../appendix-a-glossary.md#projection-issue).
4. **Head advance.** `@` moved and the bookmark stayed. That is the ordinary `current` or `behind` relationship, never an issue.

### Checkpoint target and relationship

Every checkpoint places the bookmark by one rule (the [checkpoint target](../appendix-a-glossary.md#checkpoint-target) rule):

- The target is the thread's [live head](../appendix-a-glossary.md#live-head).
- The exception: when the live head is an empty, undescribed working-copy commit whose parent is on the owned chain, the target is that parent.

jj leaves such a commit as `@` after `jj commit` and after `jj workspace add`. It carries no work, and jj refuses to push it.

Creation is a special case. Creation's initial commit has the thread's base as its parent. The base is not on the owned chain. So creation's target is the head itself.

A checkpoint refuses when its target is neither equal to nor a descendant of `bookmark_expected_commit_id`. Moving the bookmark backward or sideways is a separately approved plan. That plan is the only place kiki passes `--allow-backwards`.

The [checkpoint relationship](../appendix-a-glossary.md#checkpoint-relationship) shown by status is `current | behind | ahead | diverged`. It is defined purely by comparing `bookmark_expected_commit_id` with the live head, tested on a single-parent path between the two:

- `current` — they are equal, or the head is an empty, undescribed working-copy commit whose parent is the expected target. In the second case there is nothing new to checkpoint. It is the state right after `jj commit` and right after `kk reopen`, and it matches the checkpoint target rule;
- `behind` — the head is any other descendant of the expected target;
- `ahead` — the head is an ancestor of the expected target, for example after `jj edit` of an earlier commit;
- `diverged` — anything else.

Notes on this test:

- This test, and the successor tests below, need only a single-parent path from the thread's (evolved) base to its head, base included.
- The foreign-descendant condition of the owned-stack contract applies only to rebase and abandon plans. An unregistered descendant does not change a relationship or block successor tracking.
- Unresolved bookmark issues are reported separately, by name, beside the relationship. They do not change it.
- While the frontier is unmerged and its heads disagree about the thread, status prints "frontier unmerged" instead of a relationship.

`jj workspace add` at a checkpoint creates a new empty working-copy commit whose parent is the checkpoint. A reopened thread's live head is that new commit. So a freshly reopened thread reads `current`. The `Closed` equality concerns the archived head, which is the close checkpoint's target.

### The classifier

The classifier decides, for each operation, what happened to each thread's bookmark. The numbered rules below are tried in order.

- The classifier runs for each thread and each processed operation `O`, kiki's own operations included.
- It runs in the same per-repo transaction that records `O`'s `op_workspace_heads` rows.
- It reads only `O`'s exact view.
- Placements and successions are both scoped by operation ancestry.

Let `E` be the expected target in `O`'s parent view. That is the commit of the latest placement whose `placed_op_id` is an ancestor of `O`, updated by every succession row of that placement whose `op_id` is an ancestor of `O`.

0. If an in-flight lifecycle journal owns a bookmark change in `O`, the journal decides. This covers the journal's own placement and the first integration operation after it. This is the existing rule under [Projection audit](#projection-audit-detect-broadly-repair-narrowly).
1. Read the bookmark at `O`: whether it is present, whether it is conflicted, and its target set. If it is absent, also read every bookmark name `O` changed relative to its parent view, local and remote.
2. The bookmark is conflicted, or names more than one target: [`BookmarkConflicted`](../appendix-a-glossary.md#bookmarkconflicted). This test comes first, because jj can mark a bookmark conflicted while it still names `E` as its only target. That happens after a fetch that deleted the tracked remote bookmark while the local one had moved. It also happens after one of two divergent successors was abandoned. A conflicted bookmark is conflicted, not unchanged and not moved.
3. The target is exactly `E`: nothing changes. `jj new` and `jj commit` end here. `@` advanced and was recorded in `op_workspace_heads`; the bookmark did not move. After `jj commit` the relationship is still `current`, because the new head is empty and undescribed on top of the expected target. Once that head has content or a description, it is `behind`. If the thread has an open bookmark issue, reaching this rule resolves it automatically: a later operation shows the bookmark unconflicted on the expected target, which is the proven expected state.
4. The bookmark is absent. First test for a rename. It is a rename only when all of these hold in this one operation `O`:
   - the thread's bookmark name is gone, meaning it has no local target and no tracked remote bookmark of that name remains;
   - exactly one local bookmark name is new at `O`, it is not conflicted, and its single target is exactly `E`, or a successor of `E` that rule 5 accepts in `O` itself;
   - `O` changes no remote bookmark and no `@git` bookmark, and is not an import or a fetch;
   - no other thread holds the new name.

   Then kiki adopts the new name as the thread's bookmark name in the same transaction and appends a `thread_bookmark_renames` row.
   - A rename appends no placement row.
   - It appends a succession row only when the target also moved to a proven successor in `O`, exactly as rule 5 would.
   - When metadata ownership ships, the adopted name is marked human-owned, as [Metadata](../08-metadata.md#bookmark-names) requires.

   Anything less certain is [`BookmarkMissing`](../appendix-a-glossary.md#bookmarkmissing):
   - several new names;
   - a new name on a different target;
   - a name another thread holds;
   - a new name that appears in a later operation;
   - the old name still present anywhere in `O`'s view;
   - a rename of a published thread, whose tracked remote bookmark keeps the old name.

   `E` may be [hidden](https://docs.jj-vcs.dev/latest/glossary/) at `O`. That is the usual result of `jj abandon`. It is also the usual result of a fetch that finds a merged pull request's branch deleted and abandons the now-unreachable commit. If `E` is hidden at `O`, the issue records the evidence `CheckpointAbandoned`.

5. The bookmark names a single, unconflicted target `N ≠ E`.
   - **Undo.** kiki treats the move as an undo when all of these hold: `N` appears earlier in this placement's own history (it is the placed commit or the `to_commit_id` of one of its succession rows); `N` is visible at `O`; and `E` is hidden at `O`. Then kiki sets the expected target back to `N` and appends a succession row of kind `Reverted`. No issue is raised. This is what `jj undo`, `jj redo`, and `jj op revert` of a tracked rewrite produce.
   - **Native successor.** Otherwise `N` is a native successor only if all of these hold:
     - **Predecessor evidence.** An operation's [predecessor](https://docs.jj-vcs.dev/latest/glossary/) record lists `E` among the predecessors of `N`. The record may be `O`'s own. It may also be that of an ancestor of `O` that is not already an ancestor of the operation that established `E`. Kiki reads it at the exact operation, for example with `jj --at-op=<O> --ignore-working-copy evolog`. The entries of that command name each commit, the operation that wrote it, and its predecessors. A description, a matching tree, or a matching change id is not evidence.
     - **The old target is hidden.** `E` is no longer visible at `O`.
     - **The change is not divergent.** `N`'s change id has exactly one visible commit at `O`.
     - **Same change, or a proven place on the thread.** If `N` has the change id of `E`, the successor is accepted with kind `SameChange`. `N` may instead have a different change id. Two examples are the "remaining" commit of `jj split`, and the parent that a squash of the bookmarked commit folded into. Then the successor is accepted with kind `PredecessorOtherChange` only for a thread whose lifecycle, or whose `projection_resume_lifecycle`, is `Active`, and only when `N` is that thread's exact live head at `O` or lies on its validated path.
   - **Squash variants.** A squash of the bookmarked commit can go into a commit other than its parent: its child, or an earlier commit on the chain. Such a squash abandons `E` and moves the bookmark to `E`'s parent, while a different commit records `E` as a predecessor. For an `Active` thread, kiki accepts `N` with kind `PredecessorOtherChange` when all of these hold: `E` is hidden at `O`; `N` lies on the validated path; and a commit on that path, or the live head, records `E` as a predecessor under the evidence rule above. The row names that evidence commit.

   On acceptance, kiki appends the succession row and updates `bookmark_expected_commit_id` and `bookmark_expected_op_id`. `checkpoint_commit_id` and the placement history do not change.

6. Anything else is [`BookmarkMoved`](../appendix-a-glossary.md#bookmarkmoved): a target with no predecessor evidence, a move to an unrelated commit, a backward or sideways move that is not an undo of a tracked rewrite, a different-change successor that is off the validated path, and any different-change successor of a closed thread.

#### Closed threads

A closed thread has no workspace. Its checkpointed commit can still be rewritten when an ancestor is rewritten from another workspace.

- Only `SameChange` and `Reverted` successions are accepted for it.
- The same transaction moves the archived `thread_head_commit_id` to `N`. So the closed invariant `bookmark_expected_commit_id == thread_head_commit_id` keeps holding.

#### Additional rules

- **Several operations.** Operations are classified one at a time in topological order. So a chain `E → … → N` across several unprocessed operations is proved one step per operation. A step's operation may carry no predecessor record: it was written by an older jj, or its record was discarded. Such a step has no evidence and falls to rule 6.
- **Multi-parent operations.** Compute `E` for each parent. If the parents agree, or only one parent's side changed the bookmark, classify the merged view by rules 2–6. If both sides rewrote `E`, jj produces divergent successors and a conflicted bookmark, and rule 2 applies.
- **Unmerged heads.** [Unmerged frontier](#unmerged-frontier) applies: placement and succession rows are scoped per operation, the row cache moves only when every head agrees, and no issue is raised from one head's view.
- **An unresolved bookmark issue [freezes](../appendix-a-glossary.md#freeze) tracking.** While `BookmarkMissing`, `BookmarkMoved`, or `BookmarkConflicted` is unresolved for a thread, the classifier records later observations on that issue and does not move the expected target. The issue ends in one of two ways: rule 3 resolves it automatically, or an applied `kk repair` bookmark plan re-establishes the target.
  - Every applied plan is a placement that appends a `thread_checkpoints` row.
  - Restore recreates or moves the bookmark to the expected target, `bookmark_expected_commit_id`. It never moves it to the older placed commit.
  - Adopt places it at the chosen exact commit.
- **Restore never targets a hidden commit.** For all three issue kinds, a restore plan is offered only while the expected target is visible in the pinned view. Placing a bookmark on a hidden commit makes it visible again beside its successor and creates a [divergent change](https://docs.jj-vcs.dev/latest/glossary/). When the expected target is hidden, the plans are:
  - to adopt a visible commit; or
  - for `CheckpointAbandoned`, the [`unhide-checkpoint`](../appendix-a-glossary.md#unhide-checkpoint) plan, which first makes the abandoned commit visible again and then places the bookmark on it.

  A closed thread with `CheckpointAbandoned` may instead be destroyed.

- **A dirty stale update can conflict the bookmark.** Sometimes `jj workspace update-stale` leaves a workspace's unsnapshotted edits in a second divergent successor. Then a bookmark on that workspace's commit becomes conflicted across both successors. That is `BookmarkConflicted`. It is evidence for the edit-recovery path in [Cascade](../05-cascade.md#unsnapshotted-edit-recovery), not a reason to pick a successor.

A checkpoint placed without snapshotting names the commit jj currently records. If the working copy holds unsnapshotted edits, the next snapshot rewrites that commit and the bookmark follows. That is rule 5, not drift. Close, detach, and publish avoid the gap by taking the boundary snapshot in preflight. So the pinned head already contains every tracked edit.

### Operation history rewritten

`jj op abandon` and `jj util gc` can discard the operations kiki recorded. The watcher detects this when no current frontier head descends from any operation in `op_history`. Predecessor evidence and operation ancestry older than the surviving history are then gone. Per-thread classification across the gap is impossible.

There are two cases:

- **Nothing a thread depends on changed.** This is the case when every thread's observed bookmark equals its cached `bookmark_expected_commit_id`, and every managed workspace's `@` equals its cached `thread_head_commit_id`. Kiki [re-anchors](../appendix-a-glossary.md#re-anchoring) silently:
  - it records an `op_history_anchors` row naming the sampled heads;
  - from then on, it evaluates placements and successions relative to that anchor, with the cached expected targets as its starting values.
- **Otherwise** kiki raises exactly one repo-level issue, [`OperationHistoryRewritten`](../appendix-a-glossary.md#operationhistoryrewritten). The issue records each thread whose bookmark or head differs.
  - Kiki does not raise per-thread bookmark issues for the gap. Without the discarded record, it cannot tell a native successor from an external move.
  - While the issue is unresolved, checkpoint, publish, close, detach, and explicit rebase are blocked for the listed threads. Head observation continues from the new anchor.
  - `kk repair` resolves it with one approved plan. The plan re-anchors. For each listed thread, it either adopts the observed commit as a new placement or sends that thread to its ordinary bookmark plan.

## Projection audit: detect broadly, repair narrowly

A [projection](../appendix-a-glossary.md#projection) is something outside kiki's database that should match a thread's record: its bookmark, its jj workspace record, its path, or its [terminal group](../appendix-a-glossary.md#terminal-group). Not every projection failure is represented by a jj operation. So the [op-log watcher](../appendix-a-glossary.md#op-log-watcher) feeds a companion projection audit.

The audit runs:

- at daemon boot, after op-log catch-up;
- for every `kk ls`;
- before switch/lifecycle commands;
- after relevant filesystem or terminal-runtime notifications.

The audit compares stable database identity with what it observes:

- jj workspace records, canonical paths, and bookmark targets;
- two terminal inputs defined in [Terminal runtime](terminal-runtime.md): `TerminalRuntime` snapshots of the current [server instance](../appendix-a-glossary.md#server-instance), and `ProcessSupervisor` survivor scans of recorded process identities.

Bookmark targets are judged by [Checkpoint tracking](#checkpoint-tracking), not by equality with the last placement.

At minimum it records these durable `thread_projection_issues`:

- `WorkspaceDirectoryMissing`
- `WorkspaceRecordMissing`
- `WorkspacePathMismatch`
- [`BookmarkMissing`](../appendix-a-glossary.md#bookmarkmissing)
- [`BookmarkMoved`](../appendix-a-glossary.md#bookmarkmoved)
- [`BookmarkConflicted`](../appendix-a-glossary.md#bookmarkconflicted)
- [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing)
- [`OrphanedProcess`](../appendix-a-glossary.md#orphanedprocess)

### Terminal and process issues

`TerminalMissing` covers every way a thread can lose its bound terminal:

- the recorded server instance is gone;
- the terminal group is gone;
- the `agent` role's [pane launcher](../appendix-a-glossary.md#pane-launcher) ended;
- a [cold restore](../appendix-a-glossary.md#cold-restore) replaced every process;
- an unrequested live handoff was observed.

A [harness](../appendix-a-glossary.md#harness) that exits under a live `agent` launcher is not `TerminalMissing`. It retires that [incarnation](../appendix-a-glossary.md#incarnation), and the same launcher awaits the next gate.

`OrphanedProcess` is a standing issue with two causes (see [orphan](../appendix-a-glossary.md#orphan)):

- a recorded process identity is alive without a current binding; or
- a [harness remnant](../appendix-a-glossary.md#harness-remnant) survives. A harness remnant is a process other than the launcher in the `agent` launcher's descendant, session, or [process-group](https://en.wikipedia.org/wiki/Process_group) set after its harness was retired.

Rules for `OrphanedProcess`:

- Scans raise it at `kkd` start, when the server instance changes, and before a replacement incarnation.
- A recorded role process that is a pane member on the current instance is a terminal member, not an orphan.

An unrecorded same-UID [holder](../appendix-a-glossary.md#holder) of the workspace (a process of the same OS user that kiki never recorded) is treated differently:

- It is not a standing issue and never blocks an `Active` thread's boundaries.
- It matters only to an operation that deletes the workspace. There, it makes the result `Unknown` unless the approved plan names that exact holder identity as accepted.

A restored Herdr workspace or pane is never evidence that either issue is resolved. [Terminal runtime](terminal-runtime.md#runtime-changes-are-reconciliation) defines the cases.

### Detection and repair

Detection:

- Detection records expected and observed values before notification.
- It moves an otherwise coherent `Active` or `Closed` thread to `ProjectionDiverged`, preserving the prior lifecycle as the repair target.
- Audits are lifecycle-sensitive. A closed thread is expected to lack a workspace and a terminal binding, but it still requires its checkpoint bookmark.
- A surviving recorded process is an `OrphanedProcess` for a closed thread too. It moves that thread from `Closed` to `ProjectionDiverged`, with `Closed` as the repair target.

Automatic resolution:

- The audit may automatically resolve only a unique identity-preserving normalization. Two examples: a lexical-path mismatch where the stable jj workspace id resolves to the same filesystem object; or an external `jj bookmark rename` that one exact operation proves under classifier rule 4.
- Native successor tracking is not a repair. It is the proven expected state, recorded as it happens.
- The same holds for the undo rule, and for the automatic resolution of a bookmark issue once the bookmark is again unconflicted on the expected target.

Explicit repair:

- Each of these requires an explicit `kk repair` choice recorded in the issue and lifecycle journals:
  - recreating a workspace record;
  - adopting or restoring a bookmark target;
  - resolving a conflicted bookmark;
  - adopting a moved directory;
  - provisioning a replacement terminal group;
  - restarting an agent;
  - terminating a recorded orphan.
- Missing state is never interpreted as a successful close.
- A missing terminal group or ended `agent` role is never reported as a live `Active` agent.

### What each issue still allows

[Projection divergence](../appendix-a-glossary.md#projection-divergence) is not a blanket observation embargo. The audit derives capabilities per issue:

| Issue                                                                   | Safe observation while unresolved                                                                                       | Mutations blocked                                                                                                                               |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `BookmarkMissing` / `BookmarkMoved` / `BookmarkConflicted`              | continue exact workspace-`@` history and follows-parent classification; record later bookmark observations on the issue | checkpoint, publish, close, detach until the bookmark plan is resolved; native successor tracking for that thread                               |
| `TerminalMissing`                                                       | continue exact workspace-`@` history and follows-parent classification                                                  | agent-boundary delivery and workspace materialization; lifecycle mutation except an approved restart, `close-without-terminal`, or destroy plan |
| `OrphanedProcess`                                                       | continue exact workspace-`@` history and follows-parent classification                                                  | activating a replacement incarnation's launch gate; workspace materialization; forgetting or deleting the workspace                             |
| uniquely identified `WorkspacePathMismatch`                             | continue observation through the stable workspace id while the automatic canonicalization plan commits                  | path-dependent workspace mutation                                                                                                               |
| `WorkspaceDirectoryMissing` / `WorkspaceRecordMissing` / ambiguous path | no workspace-head observation is claimed                                                                                | all workspace and follows-source mutation                                                                                                       |

An unresolved issue may still block a thread from acting as a cascade child even while its exact head safely acts as a follows source. Consumers must request the specific capability they need. They must not branch only on `lifecycle == Active`.

### Mismatches owned by a lifecycle saga

Lifecycle [sagas](../appendix-a-glossary.md#saga) (multi-step operations such as create and close) own their expected temporary mismatches.

- The audit consults the exact lifecycle operation and completed-step journal before raising an issue. So a bookmark move during checkpoint is not misclassified. Neither is a missing terminal group after the journaled terminal-group close request.
- An unexpected mismatch first fails that operation.
- Compensation (undoing the operation's steps) then does one of two things. It restores the operation's coherent `Active` or `Closed` target. Or it records a normal [projection issue](../appendix-a-glossary.md#projection-issue) with that stable resume lifecycle and enters `ProjectionDiverged`.
- Transitional states never become an invented projection resume target.
- Conversely, an unjournaled mismatch cannot be waved away as lifecycle activity.

## Daemon-restart catch-up

On [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) restart, the watcher runs an op-log catch-up _before_ the transcript JSONL backfill. ([JSONL](https://jsonlines.org/) is a file format with one JSON record per line.)

Catch-up applies the operation-DAG frontier algorithm from every durable frontier member to the complete current head set. Then it queries each registered workspace's view at each discovered op:

```
jj -R <workspace_root> --at-op=<op_id> --ignore-working-copy log -r '@' --no-graph -T 'change_id ++ " " ++ commit_id ++ "\n"'
```

About this command:

- `<op_id>` is always a full operation id, never `@`.
- The command neither snapshots nor merges heads.
- It succeeds in a stale workspace and while several heads exist.
- The `-R <workspace_root>` is load-bearing, because jj resolves `@` from the selected workspace. There is no `jj log --workspace` flag to rely on.
- A workspace that jj has forgotten has no `@` in later views, and the query fails for it. That is `WorkspaceRecordMissing` evidence, not an empty head.

The rest of the catch-up pass:

- The same pass reads each thread's bookmark at each discovered operation and runs [the classifier](#the-classifier).
- If no current head descends from any recorded operation, catch-up applies [Operation history rewritten](#operation-history-rewritten) before anything else.
- `kkd` inserts a row for each `(op_id, workspace_id)` pair where `@` differs from the workspace's previous row. The insert is idempotent on the unique key.

## Retention

- Workspace-view rows are bounded by `op-log-size × workspace-count`.
- Normalized edges and the small frontier add `O(op-log-size)` state.
- Retention is the lifetime of the repo's registration.

## Tests

The watcher itself is tested via integration. The _logic_ of op-event interpretation is covered by `AncestryQuery` + `OpAttribution` deep-module tests (see [Testing](../14-testing.md)).
