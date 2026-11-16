# Op-log watcher

The op-log watcher is `kkd`'s window into jj. It detects external operations (human, agent via Bash, sibling tools) and feeds the cascade orchestrator and the transcript backfill path.

## Mechanism

- An `OpFrontierSampler` reads the complete current set of operation heads without loading the repository. It is a versioned adapter. For the supported jj range it lists the main repository's operation-head store, `<main workspace>/.jj/repo/op_heads/heads/`, one file per head. An added workspace has no store of its own: its `.jj/repo` is a file that names the main repository's directory, and the sampler resolves that pointer before it watches or reads anything.
- `fsnotify` on that resolved `heads/` directory is change detection only. A watch on its parent `op_heads/` directory does not see head changes. Every wake-up, and a periodic timer that covers missed events, reruns the sampler; the event itself carries no meaning.
- 250ms debounce per repo before triggering cascade evaluation.
- Per-op evaluation compares before/after managed workspace commits and validates actual ancestry for affected follows edges. A live parent's exact workspace `@`/`thread_head_commit_id`, not its bookmark, drives follows classification. Bookmark changes feed [Checkpoint tracking](#checkpoint-tracking) and the projection audit only. O(threads × ancestry-depth) per op is acceptable in practice for v1.

### Frontier sampling is a proof requirement

jj 0.46.0 has no supported, side-effect-free interface that lists every operation head: no command flag, template keyword, or `jj debug` subcommand does it. The sampler therefore depends on jj's internal store layout. That dependency is confined to the adapter. The adapter checks the pinned jj version and the store's `op_heads/type` marker before trusting a listing, and it reports `Unavailable` for a layout it does not recognize. While sampling is unavailable the watcher is degraded and says so; `RefreshToFrontier` fails closed, and every lifecycle command that depends on it refuses. A stable sampler, and its behavior while jj replaces one head with another, remain open items in the implementation gate.

`jj op log` polling is not a fallback, and kiki does not use it to discover the frontier. Three measured behaviors rule it out. With more than one head, `jj op log` merges them: it writes a new "reconcile divergent operations" operation as a side effect, even under `--ignore-working-copy`. Without `--ignore-working-copy` it also snapshots the working copy. And it can only ever print one head, so it cannot report the state it just destroyed.

### Pinned reads and pinned mutations

Kiki never observes a managed repository through an unpinned jj command. Every read, and every bookmark or rebase mutation, names an exact operation id and ignores the working copy. The only unpinned jj commands are the working-copy commands listed in [Invariants](../02-invariants.md); that list is closed and is stated once, there.

- **Reads.** Every read names an exact operation and ignores the working copy: `jj --at-op=<op_id> --ignore-working-copy …`, where `<op_id>` is a full id the sampler returned or an ancestor already recorded in `op_history`. Such a read does not snapshot, does not merge heads, works in a stale workspace, and works while several heads exist.
- **`--at-op=@` is not a pin.** With one head it still snapshots the working copy unless `--ignore-working-copy` is also given. With several heads it fails. Kiki does not use it.
- **Unpinned commands are mutations.** Any jj command that loads the repository without `--at-op` merges divergent heads, and `status`, `log`, `diff`, `show`, `evolog`, `op log`, `op show`, `bookmark list`, `workspace list`, and `file list` also snapshot the working copy. Kiki treats every one of them as a mutation of a managed repository, whatever its name suggests.
- **Repository mutations.** A kiki mutation that does not need the working copy — a checkpoint's bookmark move, an explicit rebase, a planned `--no-integrate-operation` step — runs at `--at-op=<head>`, where `<head>` is the exact head the plan was validated against. Its result is a child of that head. If an external operation landed in between, the result is a second head, never a silent merge, and the next sample shows it.
- **Working-copy commands.** Some commands must touch a working copy or the workspace set, so they cannot run at a pinned operation: the boundary snapshot and `jj workspace update-stale` in a managed workspace, and the workspace-shaping lifecycle commands (`jj workspace add`, creating the initial working-copy change, `jj workspace forget`). `kkd` runs each of them under the thread's reconciliation lock or the owning lifecycle lock, only after a sample shows exactly one head, and attributes the resulting operation. It samples again afterward and reads the actual result from the resulting exact operation. It never assumes the command acted on the view it sampled first. The remaining entry in the Invariants list is not run by `kkd` at all: the body of `kk status` is a human-invoked passthrough that the `kk` CLI runs in the caller's own contextual workspace, and it may snapshot like any direct jj use. The status header, `kk status --no-jj`, `kk ls`, the watcher, and every background renderer use pinned reads only.
- **Deliberate integration.** This is the last `kkd` entry in the Invariants list. When a step needs one view and the frontier has several heads, kiki integrates on purpose, under the same lock: it runs one designated repository-loading command with `--ignore-working-copy`, samples again, and requires a single head whose parents are the heads it sampled. jj writes that operation's description, so kiki cannot prefix it; kiki records the resulting `op_id` in `op_attribution` with kind `Integration`. An integration operation is attributed but never skipped: its merged view can differ from every parent, so it is classified like any other multi-parent node.

## Operation-DAG cache

Each observed operation node is persisted in `op_history(repo_id, op_id, committed_at, observed_at, processed_at?)`. Operation ancestry is normalized in `op_history_parents(repo_id, op_id, parent_op_id)`, with one row for every parent edge. Per-view workspace state lives in `op_workspace_heads(repo_id, op_id, workspace_id, change_id, commit_id)`. `op_watch_frontier(repo_id, op_id, observed_at)` stores the current known antichain of operation heads. A singular `parent_op_id` or last-op cursor is not an acceptable implementation of this contract.

The **per-workspace** dimension of `op_workspace_heads` is load-bearing. jj's op log is repo-shared, but `@` is per-workspace. One operation may change only A's working-copy commit, or an ancestor rewrite may evolve A, B, and C together while each workspace retains a distinct `@`. A repo-keyed cache cannot answer either “what was workspace B's `@` at this op?” or “which managed workspaces evolved in this op?” Transcript backfill joins `op_workspace_heads` to `op_history` and may use `committed_at <= entry.timestamp` only after restricting candidates to one operation-ancestry path that was observed for that workspace. If incomparable candidates have no unique ancestry maximum, the transcript row is `anchor_unknown`; wall-clock order must not choose an operation branch.

An `op_workspace_heads` row is inserted only when an op produces a _new_ `@` for the workspace in question relative to at least one parent view. The transcript lookup's "latest row at or before timestamp" semantics handle gaps only within the unique ancestry restriction above; timestamps are never used to order or choose between incomparable jj operations.

Whenever a stable workspace id and canonical path identify exactly one managed workspace, insertion of a new workspace `@` and update of `threads.thread_head_commit_id` occur in the same per-repo transaction. The row update follows the [unmerged-frontier](#unmerged-frontier) rule: it is written from a view every current head agrees on. This remains true when the thread is `ProjectionDiverged` solely because of a bookmark issue, `TerminalMissing`, or `OrphanedProcess`: those issues do not make `@` ambiguous and must not freeze follows classification. A missing workspace record/directory or ambiguous path disables head updates until repair. The persisted value is not copied to the bookmark. Kiki places the bookmark only at an explicit placement: creation, publish, close, detach, or an applied bookmark repair plan (restore or adopt). Each is a journaled checkpoint. Between placements the expected bookmark target is `bookmark_expected_commit_id`, which follows jj's own rewrite successors under [Checkpoint tracking](#checkpoint-tracking); it is never advanced because `@` advanced.

## Operation-DAG frontier

Jj operations form a DAG and may have multiple concurrent heads or an integration operation with multiple parents. The watcher therefore maintains the current observed head frontier plus per-node `processed_at`, not a scalar cursor:

1. Sample the complete current head set through the `OpFrontierSampler` and compare it with the durable `op_watch_frontier`; persist newly observed heads before interpretation.
2. Discover every operation reachable from a current head whose `op_history.processed_at` is null or absent, including every parent edge.
3. Process the discovered subgraph in parent-before-child topological layers. Incomparable operations remain incomparable; `committed_at` never fabricates an order between them.
4. For an operation with multiple parents, query each parent's workspace views. If the result differs from more than one parent, classify against the durable follows anchors and normalized trigger set; if there is no single coherent base transition, record `TopologyDiverged` rather than choosing a preferred parent.
5. In the same per-repo transaction as the resulting `op_history`, `op_history_parents`, `op_workspace_heads`, head-cache, attribution, and intent changes, mark every completely interpreted node processed and replace `op_watch_frontier` with the final sampled head antichain.

Crash before the interpretation transaction leaves reachable nodes unprocessed and safely replays them from the persisted or freshly sampled `op_watch_frontier`. Unique keys make replay idempotent. An op integration may coalesce normalized trigger ids into one pre-materialization intent, but never rewrites the operation DAG into a false linear “through” range.

`RefreshToFrontier(repo_id)` is the synchronous form of this algorithm. It repeatedly samples the head set, processes the discovered DAG, and returns a pinned frontier/view only when the sampled head set is unchanged across the final persistence transaction. Detach, parent-close preflight, close's post-freeze recheck, and topology-sensitive repair must call it; absence of an existing intent is not freshness evidence.

### Unmerged frontier

Several heads can persist until some jj command merges them. Kiki does not merge them by observing.

- Every head's ancestry is processed as above. A value that is a function of one view — a workspace's `@`, a bookmark target, the expected checkpoint target — is evaluated per head and is never blended across heads.
- A single-valued row cache (`threads.thread_head_commit_id`, `threads.bookmark_expected_commit_id`) is written only from a view every current head agrees on. While heads disagree about a thread, its cache keeps the last agreed value, status prints "frontier unmerged" in place of that thread's checkpoint relationship, and no projection issue is raised from one head's view alone.
- A caller of `RefreshToFrontier` that needs one view — a checkpoint, publish, detach, close, or an explicit rebase — requests deliberate integration, then classifies the integration operation. If heads still disagree after the bounded retry, the caller fails without mutating.
- When an external command merges the heads first, the merge is an ordinary multi-parent operation and step 4 applies. Two heads that each rewrote the same commit merge into divergent successors and a conflicted bookmark; kiki reports that outcome and does not choose a side.

## Op attribution

`kkd` dedupes its own jj operations by recording every kk-initiated `op_id` in the `op_attribution` table and prefixing the op message with `kk:`. The watcher checks attribution before reacting; self-attributed ops do not re-trigger cascade. A deliberate integration is the exception described under [Pinned reads and pinned mutations](#pinned-reads-and-pinned-mutations): it is attributed by id, carries jj's own description, and is still classified.

External ops (no `kk:` prefix, op_id not in `op_attribution`) pass through reconciliation classification. Classification is based on state, not command name:

- if the exact evolved parent base is already an ancestor of the managed child's current repository commit, record `NativeRewrite` with the exact old-base → evolved-base ids; the child's before/after commits are evidence, not the pinned target;
- if the parent's exact live head advances to a new tip not already in the child's ancestry, record `ParentAdvance` with that exact destination commit;
- if the new topology is ambiguous, backward-moving, conflicted, or inconsistent with the follows edge, record `TopologyDiverged`.

Moving, deleting, or recreating the parent bookmark never creates `ParentAdvance`. A bookmark change is classified only by [Checkpoint tracking](#checkpoint-tracking); follows edges continue to use pinned commits and observed live heads. The two classifications are independent. `jj abandon` deletes a bookmark on the abandoned commit by default, so one external operation can produce both `BookmarkMissing` for the bookmark and `TopologyDiverged` for the abandoned head or owned revision. Neither result suppresses or outranks the other.

### Linear owned-stack validation

Before recording a rebasable `ParentAdvance`, and again immediately before executing it, the classifier validates the v1 owned-stack contract against one pinned operation view. Let `B` be the exact last-synchronized base, `H` the child's exact live head, and `S` the revisions reachable from `H` after excluding ancestors of `B`. Kiki requires:

1. `B` is an ancestor of `H`.
2. `S` has exactly one root and that root's sole parent is `B`.
3. Every revision in `S` has one parent and forms one uninterrupted chain to `H`; merges, multiple roots, and conflicted topology fail validation.
4. Descendants of `S` outside that chain are completely accounted for by recursively valid registered follows children. Any unregistered or ambiguous descendant is foreign topology.

The explicit rebase names the exact validated members of `S`; it never uses a dynamic all-descendants selector. Failure of any condition records `TopologyDiverged` on the intent with the pinned evidence. Kiki does not choose a likely root, silently absorb a revision, or perform a partial rebase. If the discrepancy concerns a missing/moved external projection rather than revision ancestry, it records `ProjectionDiverged` as described below.

A single external op may logically evolve multiple workspaces in A→B→C. The watcher records a separate base-transition intent for every affected workspace; it does not pretend repository evolution occurred one hop at a time.

The watcher detects repository transitions, not every file materialization. A direct `jj workspace update-stale` may or may not produce an operation. In a non-colocated repository, updating a clean stale workspace changes its files and leaves the head set unchanged. In a colocated repository — jj 0.46's default for `jj git init` — the same update writes a "reset git head" operation. Updating a dirty stale workspace writes a snapshot operation and an operation that reconciles it with the rewrite. The presence or absence of an operation therefore proves nothing about freshness. `WorkspaceProbe` at the next managed boundary is the authority on current freshness.

Kiki-initiated explicit advances are `op_attribution`-skipped by the watcher, but their reconciliation handler compares the starting and resulting operation views before completing the intent. Any other workspace jj evolved receives a `NativeRewrite` intent in the same durable result-recording step. See [Cascade](../05-cascade.md) and [Native evolution](../17-decisions/native-evolution.md).

## Checkpoint tracking

jj moves a bookmark along with the commit it names. A snapshot, `jj describe`, a rebase, a squash into the commit, or an ancestor rewrite made from another workspace each replace the commit with a successor and carry the bookmark to it, with no bookmark command. The first ordinary edit after thread creation does exactly this. `jj new` and `jj commit` do not: they move `@` and leave the bookmark behind. Kiki therefore keeps four facts apart ([D-0005](https://github.com/skeswa/kiki/blob/main/journal/decisions/0005-track-checkpoint-through-native-successors.md)):

1. **Placement.** Where an explicit checkpoint put the bookmark. Each placement appends an immutable `thread_checkpoints` row and sets `checkpoint_commit_id`, `checkpoint_change_id`, and `checkpoint_op_id`.
2. **Native successor tracking.** jj carried the bookmark to a proven rewrite successor. Kiki appends a `thread_checkpoint_successions` row and advances `bookmark_expected_commit_id`. No issue is raised.
3. **External movement.** Any other change of target is a projection issue.
4. **Head advance.** `@` moved and the bookmark stayed. That is the ordinary `behind` relationship.

The checkpoint relationship shown by status stays `current | behind | diverged`. It is defined purely by comparing `bookmark_expected_commit_id` with the live head: `current` when they are equal, `behind` when the expected target is an ancestor of the head on the validated owned chain, and `diverged` for every other relation. Unresolved bookmark issues are reported separately, by name, beside the relationship; they do not change it. While the frontier is unmerged and its heads disagree about the thread, status prints "frontier unmerged" instead of a relationship.

### The classifier

The classifier runs for each thread and each processed operation `O`, in the same per-repo transaction that records `O`'s `op_workspace_heads` rows. It reads only `O`'s exact view. Let `E` be the expected target in the parent view: the latest placement, advanced by every succession row whose `op_id` is an ancestor of `O`.

0. If an in-flight lifecycle journal owns a bookmark change in `O`, the journal decides. This is the existing rule under [Projection audit](#projection-audit-detect-broadly-repair-narrowly).
1. Read the bookmark at `O`: whether it is present, whether it is conflicted, and its target set. If it is absent, also read every local bookmark name that `O` added relative to its parent view.
2. The target is exactly `E`: nothing changes. `jj new` and `jj commit` end here. `@` advanced and was recorded in `op_workspace_heads`; the bookmark did not move; the relationship is `behind`.
3. The bookmark is absent. First test for a rename. It is a rename only when all of these hold in this one operation `O`: the thread's bookmark name is gone; exactly one local bookmark name is new at `O`; that bookmark is not conflicted and its single target is exactly `E`, or a successor of `E` that the tests of rule 5 accept in `O` itself; and no other thread holds that name. Then kiki adopts the new name as the thread's bookmark name in the same transaction and appends a `thread_bookmark_renames` row. A rename appends no placement row. It appends a succession row only when the target also moved to a proven successor in `O`, exactly as rule 5 would. When metadata ownership ships, the adopted name is marked human-owned, as [Metadata](../08-metadata.md#bookmark-names) requires. Anything less certain is `BookmarkMissing`: several new names, a new name on a different target, a name another thread holds, a new name that appears in a later operation than the one that removed the old name, or the old name still present anywhere in `O`'s view.
4. The bookmark is conflicted, or names more than one target: `BookmarkConflicted`. A bookmark that jj still marks conflicted while naming a single target is conflicted, not moved.
5. The bookmark names a single target `N ≠ E`. `N` is a native successor only if all of these hold at `O`:
   - **Predecessor evidence.** `O`'s own predecessor record lists `E` among the predecessors of `N`. Kiki reads it from the operation, for example with `jj --at-op=<O> --ignore-working-copy evolog`, whose entries name each commit, the operation that wrote it, and its predecessors. A description, a matching tree, or a matching change id is not evidence.
   - **The old target is hidden.** `E` is no longer visible at `O`.
   - **The change is not divergent.** `N`'s change id has exactly one visible commit at `O`.
   - **Same change, or a proven place on the thread.** If `N` has the change id of `E`, the successor is accepted with kind `SameChange`. If `N` has a different change id — the "remaining" commit of `jj split`, or the parent that a squash of the bookmarked commit folded into — it is accepted with kind `PredecessorOtherChange` only for a thread whose lifecycle, or whose `projection_resume_lifecycle`, is `Active`, and only when `N` is that thread's exact live head at `O` or lies on its validated owned chain.

   On acceptance, kiki appends the succession row and advances `bookmark_expected_commit_id` and `bookmark_expected_op_id`. `checkpoint_commit_id` and the placement history do not change.

6. Anything else is `BookmarkMoved`: a target with no predecessor evidence, a move to an unrelated commit, a backward or sideways move, a different-change successor that is off the owned chain, and any different-change successor of a closed thread.

A closed thread has no workspace, but its checkpointed commit can still be rewritten when an ancestor is rewritten from another workspace. Only a `SameChange` successor is accepted for it, and the same transaction advances the archived `thread_head_commit_id` to `N`, so the closed invariant `bookmark_expected_commit_id == thread_head_commit_id` keeps holding.

Additional rules:

- **Several operations.** Operations are classified one at a time in topological order, so a chain `E → … → N` across several unprocessed operations is proved one step per operation. A step whose operation carries no predecessor record — an operation written by an older jj, or one whose record was discarded — has no evidence and falls to rule 6.
- **Multi-parent operations.** Compute `E` for each parent. If the parents agree, or only one parent's side changed the bookmark, classify the merged view by rules 2–6. If both sides rewrote `E`, jj produces divergent successors and a conflicted bookmark, and rule 4 applies.
- **Unmerged heads.** [Unmerged frontier](#unmerged-frontier) applies: succession rows are appended per operation, the row cache advances only when every head agrees, and no issue is raised from one head's view.
- **An unresolved bookmark issue freezes tracking.** While `BookmarkMissing`, `BookmarkMoved`, or `BookmarkConflicted` is unresolved for a thread, the classifier records later observations on that issue and does not advance the expected target. Only an applied `kk repair` bookmark plan re-establishes it, and every applied plan is a placement that appends a `thread_checkpoints` row. Restore recreates or moves the bookmark to the expected target, `bookmark_expected_commit_id`, never to the older placed commit. Adopt places it at the chosen exact commit.
- **A dirty stale update can conflict the bookmark.** When `jj workspace update-stale` leaves a workspace's unsnapshotted edits in a second divergent successor, a bookmark on that workspace's commit becomes conflicted across both successors. That is `BookmarkConflicted`, and it is evidence for the edit-recovery path in [Cascade](../05-cascade.md#unsnapshotted-edit-recovery), not a reason to pick a successor.

A checkpoint placed without snapshotting names the commit jj currently records as `@`. If the working copy holds unsnapshotted edits, the next snapshot rewrites that commit and the bookmark follows. That is rule 5, not drift.

## Projection audit: detect broadly, repair narrowly

The op-log watcher feeds a companion projection audit because not every projection failure is represented by a jj operation. The audit runs at daemon boot, after op-log catch-up, for every `kk ls`, before switch/lifecycle commands, and after relevant filesystem or terminal-runtime notifications. It compares stable database identity with observed jj workspace records, canonical paths, and bookmark targets, and with two terminal inputs defined in [Terminal runtime](terminal-runtime.md): `TerminalRuntime` snapshots of the current server instance, and `ProcessSupervisor` survivor scans of recorded process identities and workspace holders. Bookmark targets are judged by [Checkpoint tracking](#checkpoint-tracking), not by equality with the last placement.

At minimum it records these durable `thread_projection_issues`:

- `WorkspaceDirectoryMissing`
- `WorkspaceRecordMissing`
- `WorkspacePathMismatch`
- `BookmarkMissing`
- `BookmarkMoved`
- `BookmarkConflicted`
- `TerminalMissing`
- `OrphanedProcess`

`TerminalMissing` covers every way a thread can lose its bound terminal: the recorded server instance is gone, the terminal group is gone, the `agent` role's pane launcher ended, a cold restore replaced every process, or an unrequested live handoff was observed. A harness that exits under a live `agent` launcher is not `TerminalMissing`: it retires that incarnation, and the same launcher awaits the next gate. `OrphanedProcess` means either that a recorded process identity is alive without a current binding, or that a same-UID process holds the jj workspace and belongs to no pane in the current runtime snapshot. A process that is a member of a pane in that snapshot — a `user` pane or a remnant pane included — is accounted for and is not an orphan. A restored Herdr workspace or pane is never evidence that either issue is resolved; [Terminal runtime](terminal-runtime.md#runtime-changes-are-reconciliation) defines the cases.

Detection records expected and observed values before notification and moves an otherwise coherent `Active` or `Closed` thread to `ProjectionDiverged`, preserving the prior lifecycle as the repair target. Audits are lifecycle-sensitive: a closed thread is expected to lack a workspace and a terminal binding, but still requires its checkpoint bookmark, and a surviving recorded process is an `OrphanedProcess` for a closed thread too. The audit may automatically resolve only a unique identity-preserving normalization—for example, a lexical-path mismatch where the stable jj workspace id resolves to the same filesystem object, or an external `jj bookmark rename` that one exact operation proves under classifier rule 3. Native successor tracking is not a repair: it is the proven expected state, recorded as it happens. Recreating a workspace record, adopting or restoring a bookmark target, resolving a conflicted bookmark, adopting a moved directory, provisioning a replacement terminal group, restarting an agent, or terminating a recorded orphan requires an explicit `kk repair` choice recorded in the issue and lifecycle journals. Missing state is never interpreted as a successful close, and a missing terminal group or ended `agent` role is never reported as a live `Active` agent.

Projection divergence is not a blanket observation embargo. The audit derives capabilities per issue:

| Issue                                                                   | Safe observation while unresolved                                                                                       | Mutations blocked                                                                                                                               |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `BookmarkMissing` / `BookmarkMoved` / `BookmarkConflicted`              | continue exact workspace-`@` history and follows-parent classification; record later bookmark observations on the issue | checkpoint, publish, close, detach until the bookmark plan is resolved; native successor tracking for that thread                               |
| `TerminalMissing`                                                       | continue exact workspace-`@` history and follows-parent classification                                                  | agent-boundary delivery and workspace materialization; lifecycle mutation except an approved restart, `close-without-terminal`, or destroy plan |
| `OrphanedProcess`                                                       | continue exact workspace-`@` history and follows-parent classification                                                  | a replacement terminal group or agent incarnation in that workspace; workspace materialization; forgetting or deleting the workspace            |
| uniquely identified `WorkspacePathMismatch`                             | continue observation through the stable workspace id while the automatic canonicalization plan commits                  | path-dependent workspace mutation                                                                                                               |
| `WorkspaceDirectoryMissing` / `WorkspaceRecordMissing` / ambiguous path | no workspace-head observation is claimed                                                                                | all workspace and follows-source mutation                                                                                                       |

An unresolved issue may still block a thread from acting as a cascade child even while its exact head safely acts as a follows source. Consumers must request the specific capability they need; they must not branch only on `lifecycle == Active`.

Lifecycle sagas own their expected temporary mismatches. The audit consults the exact lifecycle operation and completed-step journal before raising an issue so that a bookmark move during checkpoint, or a missing terminal group after the journaled terminal-group close request, is not misclassified. An unexpected mismatch first fails that operation. Compensation either restores the operation's coherent `Active` or `Closed` target, or records a normal projection issue with that stable resume lifecycle and enters `ProjectionDiverged`. Transitional states never become an invented projection resume target. Conversely, an unjournaled mismatch cannot be waved away as lifecycle activity.

## Daemon-restart catch-up

On daemon restart, the watcher runs an op-log catch-up _before_ the transcript JSONL backfill. Catch-up applies the operation-DAG frontier algorithm from every durable frontier member to the complete current head set, then queries each registered workspace's view at each discovered op:

```
jj -R <workspace_root> --at-op=<op_id> --ignore-working-copy log -r '@' --no-graph -T 'change_id ++ " " ++ commit_id ++ "\n"'
```

`<op_id>` is always a full operation id, never `@`. The command neither snapshots nor merges heads, and it succeeds in a stale workspace and while several heads exist. The `-R <workspace_root>` is load-bearing because jj resolves `@` from the selected workspace; there is no `jj log --workspace` flag to rely on. A workspace that jj has forgotten has no `@` in later views, and the query fails for it; that is `WorkspaceRecordMissing` evidence, not an empty head. The same catch-up pass reads each thread's bookmark at each discovered operation and runs [the classifier](#the-classifier). `kkd` inserts a row for each `(op_id, workspace_id)` pair where `@` differs from the workspace's previous row (idempotent on the unique key).

## Retention

Workspace-view rows are bounded by `op-log-size × workspace-count`; normalized edges and the small frontier add `O(op-log-size)` state. Retention is the lifetime of the repo's registration.

## Tests

The watcher itself is tested via integration; the _logic_ of op-event interpretation is covered by `AncestryQuery` + `OpAttribution` deep-module tests (see [Testing](../14-testing.md)).
