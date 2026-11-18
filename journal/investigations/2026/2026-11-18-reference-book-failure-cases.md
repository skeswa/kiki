# Where can two implementations follow the book and produce different outcomes?

Reviewed on 2026-11-18 against jj revision `6418db6a`. The first six findings concern effects a caller could see on files, bookmarks, or a live agent. The remaining four concern lifecycle recovery and scripts. Each example gives a case for an acceptance test. The proposed changes are recommendations.

## Findings

### 1. One tool can run while its sibling changes the workspace

Take two Claude Code calls from the same batch. The first hook times out waiting for admission. It sees no marker and lets the tool run. The same daemon admits the second hook a moment later. It has no cached decision for the first call, so a pending intent lets it block the batch and change the files while the first tool is working. The unknown-batch check applies after a daemon restart. This case needs no restart. Require proof that no sibling was allowed through before the daemon changes files, or make an admission timeout block the call. [Hook timeout](../../../docs/reference/book/13-architecture/harness-adapter.md#hook-degradation) · [First admission](../../../docs/reference/book/05-cascade.md#the-first-call-fixes-the-batch-decision)

### 2. An entire batch can finish without receiving the cascade message

Suppose the daemon saves the reconciliation result and payload as `Materialized`, then dies before replying to either hook in a parallel batch. Both hooks can return a generic denial. If the daemon is back for the batch-completion event and the next model turn, the lost-delivery rule lets it mark the payload acknowledged. Those two events also occur when the model saw only the generic denials. Require evidence that the harness delivered the saved bytes for at least one call, or redeliver when the two outcomes cannot be distinguished. [Generic denial](../../../docs/reference/book/13-architecture/harness-adapter.md#hook-degradation) · [Lost delivery mark](../../../docs/reference/book/05-cascade.md#recovering-a-lost-delivery-mark)

### 3. A refused close can rewrite the target

Give a thread an unsnapshotted tracked edit and call `kk close` from a script with no matching rule. Commands promises exit 3 and no change. The same command requires preflight to snapshot the edit before it builds the plan. That snapshot rewrites the working-copy commit and can move the checkpoint bookmark and evolve descendants. A credential that can only begin a plan can reach this point. Specify how authorization and the snapshot fit together, and test the operation frontier and bookmark after refusal. [Close preflight](../../../docs/reference/book/09-commands.md#preflight-a-quiet-agent) · [Approval protocol](../../../docs/reference/book/13-architecture/grpc.md#approval) · [Snapshot effects](../../../docs/reference/book/05-cascade.md#boundary-snapshot)

### 4. Unregister can remove the only record of a running agent

The unregister plan can delete the repo database, credentials, and barrier files while a thread is active or a lifecycle journal is unfinished. The workspace normally lives elsewhere, and the terminal server and agent have their own lifetimes. Registering the path again assigns a new repo ID. The new registration cannot resume the old journal or verify the old processes from the deleted records. Require a repo-wide check for live work and unfinished operations, and prevent new work from starting between that check and removal. [Unregister](../../../docs/reference/book/09-commands.md#what-it-removes) · [Workspace layout](../../../docs/reference/book/03-threads.md#workspace-layout) · [Registration identity](../../../docs/reference/book/13-architecture/schema.md#what-happens-when-the-source-repo-is-moved)

### 5. Creating a thread can take over an existing jj bookmark

Suppose a repo already has a human-created `release` bookmark and no kiki thread with that name. `kk new release` uses that exact name. Creation says to create or move the bookmark to the new working-copy commit. The database uniqueness check covers only other threads. When the old target is the new commit's parent, a forward move succeeds. Later thread operations now control the human's bookmark. Require the name to be free in jj and distinguish a placement by this creation journal from a pre-existing bookmark when retrying. [Command name](../../../docs/reference/book/09-commands.md#the-name) · [Creation steps](../../../docs/reference/book/03-threads.md#the-order-of-steps) · [Database uniqueness](../../../docs/reference/book/13-architecture/schema.md#threads-bookmark-name)

### 6. Abandoning an owned chain can delete someone else's bookmark

Put a second local bookmark on the tip of an otherwise private, linear thread. It adds no descendant. Both conditions for `destroy --abandon-revisions` pass, but abandoning the tip deletes the second bookmark too. Testing requires an unreferenced chain. The behavioral rule needs to check other references into the exact commit set and bind that check to the plan before abandonment. This affects the planned v1.x destroy command. [Abandoning revisions](../../../docs/reference/book/03-threads.md#abandoning-revisions) · [Destroy tests](../../../docs/reference/book/14-testing.md)

### 7. Closing a follower leaves its own follows link unsettled

Let B follow A, then close B while A stays active. Close handles every child of B, but gives no step for B's edge to A. If that edge stays, a new commit on A targets a follower with no workspace to update. If the edge is silently deleted, B can lose pending work from A. Specify what close does with the incoming edge and queued deliveries, and what reopen restores. Test by advancing A while B is closed. [Close sequence](../../../docs/reference/book/03-threads.md#the-two-phases) · [Per-edge classification](../../../docs/reference/book/05-cascade.md#what-kiki-compares) · [Reopen](../../../docs/reference/book/03-threads.md#reopen)

### 8. Keeping repo state prevents the unregister journal from completing

`kk repo unregister --keep-state` promises the directory survives for manual inspection. The schema permits the user-level journal to finish only after that state is deleted. A retry must know which outcome fulfills the approved plan. Define separate completion checks for the two modes and restart the daemon after registry removal in each test. [Keep-state contract](../../../docs/reference/book/09-commands.md#keeping-the-state-directory) · [User-level operation journals](../../../docs/reference/book/13-architecture/schema.md#tables)

### 9. An aborted close cannot meet both rules for returning to Active

After a post-freeze check finds drift, close resumes the same processes and returns the thread to `Active` once it verifies their identities and the launcher. The schema requires a ready-handshake transaction for **every** entry into `Active`. The resumed harness has no new session-start event. Enumerate the evidence for returning to an existing incarnation separately from starting a new one. [Post-freeze recheck](../../../docs/reference/book/03-threads.md#the-post-freeze-recheck) · [Thread state constraints](../../../docs/reference/book/13-architecture/schema.md#threads)

### 10. An event cursor changes meaning when the caller moves

From the source repo, `kk events --thread B` reads the filtered repo stream. Inside B the identical command reads the thread stream. A repo cursor of 900 might correspond to B's ninth event. Resuming inside B with `--since 900` silently skips B's tenth event. Expose a cursor bound to its stream and scope, or use one sequence for this CLI filter in both contexts. [Events command](../../../docs/reference/book/09-commands.md#kk-events) · [Stream sequence numbers](../../../docs/reference/book/13-architecture/grpc.md#streaming-events)

## Evidence and reproduction

The review followed each scenario through the [invariants](../../../docs/reference/book/02-invariants.md), the owning chapters, and the architecture and testing chapters. Kiki is still at the design stage. The failures above describe outcomes allowed by the text.

For findings 5 and 6, a scratch repository with jj 0.46.0 confirmed the underlying bookmark behavior. Create a bookmark on a base commit, create a child with `jj new`, then set that bookmark to the child. jj reports a successful forward move. Create a second bookmark on that child and abandon just the child. jj reports both bookmark names under `Deleted bookmarks`. These checks used no project revisions or bookmarks.
