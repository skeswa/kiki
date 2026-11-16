# Appendix A: Glossary

This appendix defines the important terms in kiki's reference. When a term is used in more than one place, the definition here is the canonical one.

## How to use this glossary

The chapters of this book link here the first time they use a special term. You can also read this appendix on its own.

- **Each entry starts with one plain sentence** that says what the thing is. The sentences after it say why the thing exists, or how it differs from a similar term. Most entries end with a link to the chapter section that holds the full rules.
- **kiki's own terms are grouped by topic**, from [Concepts](#concepts) to [v2 / future](#v2-future).
- **Terms from the wider industry** are in [Outside terms](#outside-terms) at the end. These are words such as "daemon", "commit", and "pane" that kiki did not invent. Each one has a short definition and a link to an outside reference.
- **Words in `code font`** are exact names. They appear in kiki's commands, its database, or its code, and they are spelled the same way everywhere.

## Concepts

- <a id="thread"></a>**Thread** — one named line of work, and the basic unit (the "atom") of kiki. kiki identifies a thread by a stable `thread_id` stored in sqlite ([SQLite](#ext-sqlite), a small database). The thread stands for a themed sequence of [jj](#ext-jj) [revisions](#ext-revision). While the thread is active, its [live head](#live-head) is the current `@` of its managed [workspace](#workspace), and kiki saves that head as `thread_head_commit_id`. The [bookmark](#bookmark) name, workspace path, [terminal group](#terminal-group), and agent [harness](#harness) session are mutable [projections](#projection) of that identity: they may change while the thread stays the same thread. See [Thread identity](03-threads.md#thread-identity).
- <a id="thread-head"></a>**Thread head** — the exact [commit](#ext-commit) at the managed workspace's current `@` (jj's name for the [working-copy commit](#ext-working-copy-commit)). kiki saves it after each workspace [operation](#ext-operation) it observes. It is the live source that [follows](#follows) synchronization uses. kiki does not infer it from the thread bookmark. When kiki creates a follows edge, it refreshes the parent's head from a [pinned](#pinned-read) jj operation view. It does not trust the cached head, which may lag behind. See [Thread identity](03-threads.md#thread-identity).
- <a id="live-head"></a>**Live head** — another name for the [thread head](#thread-head): the exact `@` commit of an active thread's managed workspace. kiki stores the last `@` it observed as `thread_head_commit_id`. That stored value is a cache of a fact that lives in the workspace, not a second source of truth. The bookmark is never the live head. See [Thread identity](03-threads.md#thread-identity).
- <a id="owned-stack"></a>**Owned stack** — the chain of commits that belongs to one thread. In v1 it is the provable single-parent chain that starts after the thread's exact owned-stack base and runs through the thread head. For a following thread, that base is the follows edge's synchronized base. kiki does not guess its way through merge commits, multiple candidate roots, or foreign topology. Those cases produce [`TopologyDiverged`](#topologydiverged) and need a human choice. See [V1 owned-stack contract](03-threads.md#v1-owned-stack-contract).
- <a id="topologydiverged"></a>**`TopologyDiverged`** — the result kiki records when the shape of the commit history is too unclear to act on safely. It has two uses with the same meaning: it is a classification of a parent change (`TopologyDiverged { reason }`), and it is a state of a [`sync_intent`](#sync-intent). kiki records it in these cases:
  - the parent moved backward;
  - the follows anchors no longer describe the real topology;
  - the relevant jj state is conflicted or ambiguous;
  - the owned stack contains merge commits, multiple candidate roots, conflicts, or descendants outside the registered follows graph;
  - an operation with several parents has no single coherent base transition.

  When this happens, kiki does not build a [revset](#ext-revset) of "owned" commits and does not try a [rebase](#ext-rebase). It stops and waits for a human choice. See [Classification](05-cascade.md#classification) and [V1 owned-stack contract](03-threads.md#v1-owned-stack-contract).

- <a id="bookmark"></a>**Bookmark** — jj's term for a named pointer to a revision (see [the jj meaning](#ext-bookmark)). In kiki, the thread's bookmark has three jobs: it is a checkpoint that humans can see, a handle for reopening the thread, and the branch that is pushed to a remote. kiki places it explicitly, at lifecycle and publication boundaries. Between placements, jj does two things on its own:
  - jj carries the bookmark to rewrite successors. kiki tracks this (see [native successor](#native-successor)).
  - jj leaves the bookmark where it was when `@` gains a child. This case reads `behind` once the new head has content.

  The canonical identity stays with `thread_id`, and the live state stays with the thread head. See [What happens to the bookmark between checkpoints](03-threads.md#what-happens-to-the-bookmark-between-checkpoints).

- <a id="checkpoint-placement"></a>**Checkpoint placement** — one explicit act of putting the thread bookmark on an exact commit. kiki records each placement with its [change](#ext-change) and operation, and that record is never edited afterward. `checkpoint_commit_id` is the latest placement. See [Checkpoint tracking](13-architecture/op-log-watcher.md#checkpoint-tracking).
- <a id="expected-bookmark-target"></a>**Expected bookmark target** — the commit where kiki expects to find the thread bookmark, stored as `bookmark_expected_commit_id`. It is the latest placement, carried forward through every native successor kiki has proved, and popped back when jj undoes one. The projection audit compares the bookmark it observes with this value. See [Checkpoint tracking](13-architecture/op-log-watcher.md#checkpoint-tracking).
- <a id="checkpoint-target"></a>**Checkpoint target** — the commit that a checkpoint places the bookmark on. It is the live head. The one exception: when the head is an empty, undescribed working-copy commit and its parent is on the owned chain, the target is that parent. A checkpoint refuses a target that is behind or beside the expected target. See [Checkpoint target and relationship](13-architecture/op-log-watcher.md#checkpoint-target-and-relationship).
- <a id="checkpoint-relationship"></a>**Checkpoint relationship** — where the live head sits compared with the expected bookmark target. It has four values: `current | behind | ahead | diverged`. See [Checkpoint target and relationship](13-architecture/op-log-watcher.md#checkpoint-target-and-relationship).
- <a id="boundary-snapshot"></a>**Boundary snapshot** — a [snapshot](#ext-snapshot) of a managed [working copy](#ext-working-copy) that kiki itself runs at a safe moment. It exists so that a pinned head contains every tracked edit before a checkpoint that comes before deletion or publication. See [Boundary snapshot](05-cascade.md#boundary-snapshot).
- <a id="native-successor"></a>**Native successor** — a commit that jj moved the bookmark to because the expected commit was rewritten. The operation's predecessor record proves the move. kiki always tracks a successor that has the same change. It tracks a successor with a different change only for an active thread, and only on that thread's owned chain. Tracking a successor records where jj moved the bookmark. It is not a placement. See [Checkpoint tracking](13-architecture/op-log-watcher.md#checkpoint-tracking).
- <a id="workspace"></a>**Workspace** — when this book says "workspace" with no other word, it always means a [jj workspace](#ext-workspace): a working copy with its own files and its own `@`. Herdr also has an object called a workspace. This book writes that one as "Herdr workspace" or, in kiki's terms, a [terminal group](#terminal-group). See [Workspace layout](03-threads.md#workspace-layout).
- <a id="follows"></a>**Follows** — a directed link from one thread to a parent thread. It turns on the live [cascade](#cascade-reconciliation): when the parent changes, kiki brings the following thread up to date. See [Cascade](05-cascade.md).
- <a id="ambient-coordinator"></a>**Ambient coordinator** — kiki's posture toward the tools under it. kiki observes the state of jj, [Herdr](#herdr), and [gh](#ext-gh) and reacts to it. It does not stand in front of those tools as a gatekeeper. See [Principles](01-orientation.md#principles).
- <a id="projection"></a>**Projection** — an outside object that stands in for a thread, but is not the thread itself. The mutable projections are the jj workspace path, the jj bookmark name, the terminal group, and the harness session id. Projections may change, be repaired, or be recreated. The `thread_id` must not change. See [Thread identity](03-threads.md#thread-identity) and [Identity is stable](02-invariants.md#identity-is-stable).
- <a id="projection-divergence"></a>**Projection divergence** — a mismatch that kiki observes between a thread's database row and one of its mutable outside projections. The cases are:
  - a missing jj workspace record;
  - a mismatched path;
  - a bookmark that is missing, conflicted, or moved by something outside kiki;
  - a missing terminal group or agent role (`TerminalMissing`);
  - a recorded process that is still alive when it should not be (`OrphanedProcess`).

  kiki repairs a case automatically only when it can prove that exactly one fix is possible. Otherwise `kk repair` shows the human the explicit outcomes to choose from. See [Projection divergence and repair](03-threads.md#projection-divergence-and-repair).

- <a id="thread-lifecycle-states"></a>**Thread lifecycle states** — the named stages a thread can be in: `Creating | Active | CreateFailed | ClosePreflight | CloseCommit | CloseFailed | Closed | ProjectionDiverged | DestroyCommit | DestroyFailed | Destroyed`. Creation, close, reopen, and the later destroy surface are durable [sagas](#saga). Three states need a note:
  - `ProjectionDiverged` means one of two things. Either a mutable projection (such as the bookmark, jj workspace record, path, or terminal group) no longer matches the recorded state and cannot be repaired unambiguously, or a recorded process survives where none should. The older `Orphaned` case, which covered only a missing directory, is now `ProjectionDiverged { reason: WorkspaceDirectoryMissing }`.
  - `Closed` is a soft archive. It keeps the checkpoint bookmark and the revisions.
  - `Destroyed` tombstones kiki's thread identity: kiki marks the thread as permanently gone. The jj revisions remain, unless a separately approved `--abandon-revisions` plan named an exact safe chain.

  See [Lifecycle states](03-threads.md#lifecycle-states).

- <a id="saga"></a>**Saga** — a job with several steps that writes each step into a journal as it goes, like a checklist that survives a power cut. It is a common industry pattern ([outside reference](https://microservices.io/patterns/data/saga.html)). kiki uses sagas for creating, closing, reopening, repairing, and destroying a thread. Each of these jobs touches SQLite, jj, the filesystem, the terminal runtime, and a harness process, so it cannot be one all-or-nothing [transaction](#ext-transaction). If a step crashes, or a cleanup step fails, kiki must leave behind a saved journal and an honest lifecycle state. Restart recovery or an explicit command can then continue from that record. See [Lifecycle work is recoverable](02-invariants.md#lifecycle-work-is-recoverable).
- <a id="lifecycle-journal"></a>**Lifecycle journal** — the saved record of one saga and its steps. It lives in the `thread_lifecycle_ops` and `thread_lifecycle_steps` tables. kiki marks a step `Started` before the step's outside effect happens, and records the stable outside identity it needs to detect work that already completed. Only a failed [idempotent](#ext-idempotent) step may be retried. While a journal is in flight, a temporary projection change that it caused belongs to that journal. Such a change fails or resumes the journal. It does not count as a separate projection divergence. See [State schema](13-architecture/schema.md#tables).
- <a id="repair-plan"></a>**Repair plan** — a named, exact list of changes that `kk repair` offers to fix a thread. Each plan states which records, workspace paths, bookmarks, terminal groups, processes, or revisions it would change. Without an apply flag, `kk repair` is read-only and only reports the plans. `--apply <repair-id>` applies exactly the plan that the current diagnosis produced. kiki must never silently choose among several plausible heads, paths, or topologies, so the human picks the plan. See [`kk repair`](09-commands.md#kk-repair).
- <a id="close-without-terminal"></a>**`close-without-terminal`** — the repair plan that closes a thread that has no live agent. It takes the thread from `ProjectionDiverged` to `CloseCommit`. kiki offers it when no recorded process identity survives, for example after a reboot or a server restart. The user does not have to close the restored shells first. The plan lists every [remnant](#remnant-container) or [unbound container](#unbound-container) whose processes hold the workspace, and it lists those processes. It needs a one-shot [human approval](#human-approval). If it fails before the first termination, the plan is aborted and the thread returns to `ProjectionDiverged` with its issue unchanged. See [Agent, terminal, and process plans](09-commands.md#agent-terminal-and-process-plans).
- <a id="kkd"></a>**`kkd`** — the kiki [daemon](#ext-daemon): the background program that does kiki's work. There is one `kkd` per user, and a repository opts in through `kk init`. It runs as a per-user service, so it keeps running after you close your terminal. `kkd` is the only privileged process. It owns all state and behavior, and it serves [gRPC](#ext-grpc) over the [Unix socket](#ext-unix-socket) `~/.config/kiki/kkd.sock`. Every other kiki program is a client that asks `kkd` to act. See [Daemon](13-architecture/daemon.md).
- <a id="kk"></a>**`kk`** — the kiki command-line program that people type. It also hosts the [overlay TUI](#overlay-tui) and the [pane launcher](#pane-launcher) as subcommands. It is a pure client of `kkd`'s gRPC service. It is also a Herdr client for [caller-local focus](#caller-local-focus) and attach. See [Commands](09-commands.md) and [Crate layout](13-architecture/crates.md).
- <a id="follows-edge"></a>**Follows edge** — one [follows](#follows) link, stored as a record: this child thread follows that parent thread. The edge also stores the last [synchronized base](#synchronized-base). The edges together form the follows graph, which is a [DAG](#ext-dag): kiki rejects an edge that would create a cycle. See [Recorded anchors](03-threads.md#recorded-anchors).
- <a id="base"></a><a id="base-transition"></a><a id="owned-stack-base"></a><a id="synchronized-base"></a>**Base, base transition, owned-stack base, synchronized base** — four related words about the commit a thread builds on.
  - A **base** is the exact parent commit that a thread's own commits sit on top of.
  - The **owned-stack base** is the exact base recorded when the thread is created. The [owned stack](#owned-stack) starts after it. It stays on the thread when a follows edge is detached. It advances only when a completed reconciliation records a new synchronized base.
  - The **synchronized base** is the parent commit that a following child was last brought in step with. Creating a follows edge records the parent's exact `thread_head_commit_id` as the first one.
  - A **base transition** is a move from the last synchronized parent commit to a new exact parent commit. Every cascade is one base transition.

  See [Recorded anchors](03-threads.md#recorded-anchors) and [Cascade](05-cascade.md).

- <a id="preflight"></a>**Preflight** — the first phase of a lifecycle operation such as close or destroy. Preflight checks everything and builds the exact plan, but it performs no destructive mutation. The plan it produces is what the human approves. The second phase, commit, then does the work. See [The two phases](03-threads.md#the-two-phases).
- <a id="loss-inventory"></a>**Loss inventory** — the list that preflight makes of what deleting a workspace could lose. It inventories loss-sensitive files, every process in the terminal group, and every other [holder](#holder) of the workspace. An example of a loss-sensitive file is a file the user created that jj does not track. The inventory goes into the plan that the human approves. See [The two phases](03-threads.md#the-two-phases).
- <a id="close-plan-fingerprint"></a><a id="plan-digest"></a>**Close-plan fingerprint / plan digest** — a [hash](#ext-hash) of an exact plan, so that an approval covers that plan and no other.
  - A **plan digest** is the hash of the canonical plan that the daemon shows during approval. A [human approval](#human-approval) is bound to it.
  - The **close-plan fingerprint** is the one for close. It covers the exact thread head, the operation evidence for this thread and its child edges, the workspace inventory and byte fingerprint, the process and holder inventory, the expected projections, the child-edge decisions, the checkpoint target, and the security-relevant flags.

  See [The approval and its fingerprint](03-threads.md#the-approval-and-its-fingerprint) and [Two-phase foreground approval](04-authority.md#two-phase-foreground-approval).

- <a id="drift"></a><a id="approval-drift"></a>**Drift (approval drift)** — a difference between what the human approved and what kiki finds when it checks again. During close, drift is any of these: a filesystem event, fingerprint drift, a membership change, a new holder, or a terminal change. "Still safe, but different" is still drift. On drift, kiki keeps the files, takes the [verified-resume](#verified-resume) path, and presents a fresh plan for a new approval. See [What counts as drift](03-threads.md#what-counts-as-drift).
- <a id="compensation"></a>**Compensation** — an undo step in a [saga](#saga). When a saga cannot finish, kiki compensates the completed steps in reverse order. Creation and reopen use compensation. See [How the saga recovers](03-threads.md#how-the-saga-recovers).
- <a id="fail-closed"></a>**Fail closed** — a safety rule: when kiki cannot prove that an action is safe, it blocks the action. The opposite would be to let the action through and hope. See [Delivery protocol](05-cascade.md#delivery-protocol).
- <a id="auto-describe"></a>**Auto-describe** — the v1.x feature that writes a revision's description for you. It may read the revision diff, ancestor descriptions, the current bookmark name, and kiki-owned metadata state. It must not read the thread transcript, and it does not rewrite text a human owns. See [Revision descriptions](08-metadata.md#revision-descriptions).
- <a id="auto-rename"></a>**Auto-rename** — the v1.x feature that proposes short names for thread bookmarks that kiki owns. It does not rename a bookmark a human named. See [Bookmark names](08-metadata.md#bookmark-names).
- <a id="projection-issue"></a>**Projection issue** — one recorded case of [projection divergence](#projection-divergence), stored as a row in `thread_projection_issues`. Each issue has a kind, such as [`TerminalMissing`](#terminalmissing) or [`BookmarkMoved`](#bookmarkmoved). An unresolved issue blocks only the operations that depend on the broken projection. See [Projection divergence and repair](03-threads.md#projection-divergence-and-repair).
- <a id="terminalmissing"></a>**`TerminalMissing`** — the projection issue raised when the `agent` role itself ends: the launcher's own process exits, or its binding or server instance is lost. It covers a missing server instance, a missing terminal group, an ended `agent` role, a cold restore, and an observed handoff. While it is open, boundary delivery, materialization, and lifecycle mutation are blocked, except for approved repair plans. A harness that crashes under a live launcher is not `TerminalMissing`. See [A missing terminal: `TerminalMissing`](09-commands.md#a-missing-terminal-terminalmissing).
- <a id="orphanedprocess"></a>**`OrphanedProcess`** — the projection issue raised for an [orphan](#orphan). It has two causes: a recorded process identity that is alive without a current binding, and a [harness remnant](#harness-remnant) under a live launcher. While it is open, kiki starts no replacement agent in that workspace and deletes nothing. `kk repair` offers to terminate the exact recorded identities and verify their exit, or to leave the thread blocked. See [Leftover processes: `OrphanedProcess`](09-commands.md#leftover-processes-orphanedprocess).
- <a id="bookmarkmissing"></a>**`BookmarkMissing`** — the projection issue that says the thread's bookmark is absent. When the checkpoint commit itself was abandoned, the issue carries the evidence `CheckpointAbandoned`. See [Bookmark plans](09-commands.md#bookmark-plans).
- <a id="bookmarkmoved"></a>**`BookmarkMoved`** — the projection issue that says the bookmark names a single commit that is not an accepted successor of the [expected target](#expected-bookmark-target). See [Bookmark plans](09-commands.md#bookmark-plans).
- <a id="bookmarkconflicted"></a>**`BookmarkConflicted`** — the projection issue that says the bookmark is conflicted or names more than one target. The diagnosis lists every observed target. See [Bookmark plans](09-commands.md#bookmark-plans).
- <a id="operationhistoryrewritten"></a>**`OperationHistoryRewritten`** — the one issue that belongs to a whole repo, not to one thread. kiki raises it when jj's operation history was rewritten (for example by `jj op abandon`), no current operation head descends from any operation kiki recorded, and some thread's bookmark or head differs from what kiki cached. It lists the threads that differ. While it is open, checkpoint, publish, close, detach, and explicit rebase are blocked for the listed threads; head observation continues. See [Operation history rewritten](13-architecture/op-log-watcher.md#operation-history-rewritten).
- <a id="restart-agent"></a>**`restart-agent`** — the [repair plan](#repair-plan) for a harness that exited or crashed under a live `agent` launcher. It starts a replacement incarnation on that launcher and provisions nothing in the terminal. Its precondition is that an inventory rooted at the launcher shows no process other than the launcher itself. Applied in the thread's own context, it needs no approval. See [A crashed harness: `restart-agent`](09-commands.md#a-crashed-harness-restart-agent).
- <a id="restart-terminal"></a>**`restart-terminal`** — the repair plan for `TerminalMissing` that restarts the terminal and the agent. It closes each listed remnant or unbound container with verified exit, re-runs the holder scan, and only then provisions a fresh terminal group and a new incarnation. It requires one-shot approval. The thread returns to `Active` only when the ready handshake commits. See [A missing terminal: `TerminalMissing`](09-commands.md#a-missing-terminal-terminalmissing).
- <a id="cleanup-failed-create"></a><a id="cleanup-failed-reopen"></a>**`cleanup-failed-create` / `cleanup-failed-reopen`** — the repair plans that clean up after a creation or a reopen that failed and could not be undone automatically. They use the close machinery: freeze, loss inventory, final proof, terminate, verified exit. They require one-shot approval. See [Failed creation and reopen](09-commands.md#failed-creation-and-reopen).
- <a id="restore-bookmark"></a>**`restore-bookmark`** — the repair plan that puts the bookmark back on the tracked expected target (`bookmark_expected_commit_id`). It never targets a hidden commit. It does not change where publish or reopen will point, so in the thread's own context it needs no approval. See [Bookmark plans](09-commands.md#bookmark-plans).
- <a id="adopt-bookmark"></a>**`adopt-bookmark`** — the repair plan that accepts the single observed bookmark target as the checkpoint, under the adoption rule. It changes where publish and reopen will point, so it requires one-shot approval. See [Bookmark plans](09-commands.md#bookmark-plans).
- <a id="choose-bookmark-target"></a>**`choose-bookmark-target`** — the repair plan that sets the bookmark to exactly one commit that the human picks from the listed candidates, under the adoption rule. It requires one-shot approval. kiki never picks. See [Bookmark plans](09-commands.md#bookmark-plans).
- <a id="unhide-checkpoint"></a>**`unhide-checkpoint`** — the repair plan for `BookmarkMissing` with the evidence `CheckpointAbandoned`. It first makes the abandoned commit visible again and then places the bookmark on it, under approval. See [Bookmark plans](09-commands.md#bookmark-plans).
- <a id="reanchor-history"></a>**`reanchor-history`** — the repair plan for [`OperationHistoryRewritten`](#operationhistoryrewritten). It shows the observed bookmark and head for each listed thread. On one-shot approval, it records them as fresh placements against the current operation. See [Repository operation history](09-commands.md#repository-operation-history).
- <a id="retry-delivery"></a>**`retry-delivery`** — the repair plan that re-arms an [exhausted intent](#exhausted-intent). In one journaled transaction it clears `delivery_exhausted_at`, increments the intent's `delivery_epoch`, and resets the soft-redelivery count. It then permits one fresh bounded `RestartStartup` cycle. See [Exhausted delivery](09-commands.md#exhausted-delivery).
- <a id="discard-delivery"></a>**`discard-delivery`** — the repair plan that acknowledges an exhausted intent without delivery proof. It runs under a one-shot approval bound to the plan and records the human's decision on the intent. The payload is then never delivered to the agent, and the plan says so before it is approved. See [Exhausted delivery](09-commands.md#exhausted-delivery).

## Scope tiers

- <a id="acceptance-slice"></a>**Acceptance slice** — the set of features that v1 must ship to be accepted. The canonical list lives in [Orientation](01-orientation.md) and nowhere else. Other chapters describe behavior and link to that ledger for when a feature ships.
- <a id="v1-x-polish"></a>**v1.x polish** — work that comes after acceptance and deepens v1. It must not block the acceptance slice unless it is explicitly promoted. It is listed in the same [Orientation](01-orientation.md) ledger.
- <a id="acceptance-gate"></a>**Acceptance gate** — a test that has to pass before kiki relies on a behavior. The acceptance integration gate is the final one: it exercises every item in the [acceptance slice](#acceptance-slice) together, against a real jj repo, a real dedicated Herdr server, and each shipped harness. See [Acceptance integration gate](15-build-sequencing.md#acceptance-integration-gate).

## Cascade

- <a id="cascade-reconciliation"></a>**Cascade reconciliation** — the process that keeps a following thread in step with its parent. It is aware of [follows](#follows) links. It has five parts:
  1. classify the parent change;
  2. wait for the affected managed agent's [safe boundary](#safe-boundary);
  3. make the workspace reflect the desired [jj](#ext-jj) state;
  4. inject context, which means telling the agent what changed;
  5. acknowledge delivery.

  Each reconciliation is one of two kinds: [`NativeRewrite`](#nativerewrite) or [`ParentAdvance`](#parentadvance). See [Cascade](05-cascade.md).

- <a id="nativerewrite"></a>**`NativeRewrite`** — the kind of reconciliation where jj has already done the history work. An ancestor was rewritten, so jj has already evolved the descendant's [commits](#ext-commit) in repository state. The intent pins the exact transition from the old base to the evolved base. It does not pin the descendant's working-copy commit, which keeps changing. kiki does not [rebase](#ext-rebase) the descendant again. At a safe boundary it checks that the current descendant still contains the evolved base. Then it normally materializes the result with `jj workspace update-stale`. See [`NativeRewrite` reconciliation](05-cascade.md#nativerewrite-reconciliation).
- <a id="parentadvance"></a>**`ParentAdvance`** — the kind of reconciliation where kiki must do the history work. A parent's saved thread head gained a new exact commit, and that commit is not already an ancestor of the following child. At a safe boundary, kiki explicitly rebases the child's provably linear [owned stack](#owned-stack) onto that exact commit. Then it materializes the result. See [`ParentAdvance` reconciliation](05-cascade.md#parentadvance-reconciliation).
- <a id="materialization"></a>**Materialization** — updating the files on disk in a workspace so they match the working-copy commit that jj already recorded for that workspace in repository state. jj can change the repository's history first and the files later. These are two separate events. See [Native evolution and workspace materialization](17-decisions/native-evolution.md).
- <a id="safe-boundary"></a>**Safe boundary** — a moment when a thread's managed agent is not in the middle of an edit, so kiki may change the workspace's files. It is like waiting for someone to finish their sentence before handing them a note. Only two things establish a safe boundary: the managed harness's pre-tool [hook](#ext-hook), or [agent quiescence](#agent-quiescence). Nothing seen in a terminal counts. An idle-looking screen is not a safe boundary. See [Invariant](05-cascade.md#invariant) and [Cascade materializes only at safe boundaries](02-invariants.md#cascade-materializes-only-at-safe-boundaries).
- <a id="pause-propagate-resume"></a>**Pause-propagate-resume** — the protocol kiki follows to update a child agent. It interrupts the agent at the next safe boundary. It reconciles and materializes the desired state. It injects a context message. Then it resumes the agent. See [Delivery protocol](05-cascade.md#delivery-protocol).
- <a id="core-invariant"></a>**Core invariant** — the central safety rule of the cascade. While a workspace's managed agent is mid-edit, kiki does not materialize evolved state in that managed workspace, and it does not perform an explicit follows rebase there. kiki also does not resume the agent from a working tree that may hide unsnapshotted edits. Direct human `jj` operations are an explicit escape hatch: they may materialize a stale workspace earlier. See [Invariant](05-cascade.md#invariant).
- <a id="soft-pause-hard-escalation"></a><a id="soft-pause"></a><a id="hard-escalation"></a>**Soft pause / Hard escalation** — the two ways kiki delivers a cascade update to an agent.
  - **Soft** means kiki injects context through the exclusive `PreToolUse` boundary, using a [`SoftBatch`](#softbatch-delivery-proof) proof. The agent process keeps running.
  - **Hard** means kiki [hard-pauses](#hard-pause) the agent. It retires the old [incarnation](#incarnation) by terminating the harness's whole process tree. It then starts a replacement incarnation, which receives the pending payload through [`RestartStartup`](#restartstartup-delivery-proof). That delivery carries its own proof. A message that was only prepended, without tracking, is not evidence of delivery.

  See [Delivery protocol](05-cascade.md#delivery-protocol).

- <a id="hard-pause"></a>**Hard-pause** — stopping an agent by ending its process, instead of holding it at a hook. A hard-pause retires the incarnation: kiki terminates the harness's whole process tree through `ProcessSupervisor`, by recorded identity. It leaves the `agent` [pane launcher](#pane-launcher) alive, so a replacement incarnation can start. kiki hard-pauses when the soft path cannot be proved safe. Two examples: a workspace probe returns `StaleDirty | Unknown`, or kiki lost its record of whether a tool call in the current batch was already admitted. See [Delivery protocol](05-cascade.md#delivery-protocol) and [Unsnapshotted-edit recovery](05-cascade.md#unsnapshotted-edit-recovery).
- <a id="tool-batch"></a>**Tool batch** — the group of tool calls that an agent's model sends out together in one turn. kiki makes one pass-or-block decision for the whole batch, because it cannot take back a call that was already let through. For Claude Code, the batch is the parallel tool batch. For Codex's proven-serial dispatch, it is a single tool call. See [Delivery protocol](05-cascade.md#delivery-protocol).
- <a id="workspaceprobe"></a>**`WorkspaceProbe`** — a check that kiki runs immediately before reconciliation, and that does not change any files. It returns a filesystem [fingerprint](#ext-fingerprint) and puts the workspace in one of five classes: `FreshClean`, `FreshDirty`, `StaleClean`, `StaleDirty`, or `Unknown`. A backend that cannot prove the workspace is clean returns `Unknown`. kiki handles `Unknown` like dirty state before any mutation. See [Workspace probe](05-cascade.md#workspace-probe).
- <a id="workspacerecovery"></a>**`WorkspaceRecovery`** — the recovery path for a [stale workspace](#ext-stale-workspace) that has unsnapshotted edits, or edits kiki cannot be sure about. The agent is hard-paused while it runs. It runs outside the source workspace. It invokes jj's stale-workspace recovery and lists the divergent successors. Before anything resumes, it checks which result still holds the edits. See [Unsnapshotted-edit recovery](05-cascade.md#unsnapshotted-edit-recovery).
- <a id="sync-intent"></a>**`sync_intent`** — the one durable record of one ordered cascade reconciliation. No other record has authority over the protocol. It owns:
  - the kind and the base transition;
  - the normalized trigger operations and the result ids;
  - the state: `Detected | Reconciling | Materialized | Delivered | Acknowledged | RecoveryRequired | TopologyDiverged | Superseded`;
  - recovery details;
  - the byte-stable payload and anchor (byte-stable means the bytes never change once stored);
  - one exact `SoftBatch` or `RestartStartup` delivery proof;
  - the durable history of delivery attempts, with its exhaustion state.

  The user interface and delivery queries work out progress from these rows, not from separate shadow counters. Retry limits are checked against these rows too, not against in-memory counts that a restart would forget. See [Synchronization intent: the sole protocol authority](05-cascade.md#synchronization-intent-the-sole-protocol-authority).

- <a id="embedded-cascade-outbox"></a>**Embedded cascade outbox** — the payload, anchor, transcript id, and delivery timestamps that are stored on a materialized `sync_intent`. It pins what the agent sees, so that a crash or a retry cannot change the message. It does this without creating a second authority over the protocol. See the [embedded-outbox design note](17-decisions/cascade-outbox.md).
- <a id="softbatch-delivery-proof"></a>**`SoftBatch` delivery proof** — state stored inside the intent for a soft delivery. It stops an already-dispatched tool batch from treating a second, concurrent `PreToolUse` as an acknowledgement. It works like this:
  - The first admitted call binds `Block` before reconciliation may change any files, and every call in that batch is blocked.
  - `PostToolBatch` records the exact completion of the batch.
  - Only a later model turn may acknowledge the delivery and clear the proof.
  - For Claude Code, the batch is the parallel tool batch.
  - For Codex's proven-serial dispatch, the batch is a single tool call. The harness's next turn-scoped hook event reports that the blocked call completed. This is needed because a denied call never runs, fires no post-tool event, and the hook that emitted the denial takes its own [RPC](#ext-rpc) down with it when it exits.

  See [Delivery protocol](05-cascade.md#delivery-protocol).

- <a id="restartstartup-delivery-proof"></a>**`RestartStartup` delivery proof** — the proof used when delivery happens through a hard restart. It binds a pending payload to a replacement incarnation and to a one-use `startup_delivery_id`. The payload is mandatory startup input. An acceptance handshake marks it delivered. Only the first model turn that results from that input, and that causally echoes the id, may acknowledge it. See [Delivery protocol](05-cascade.md#delivery-protocol).
- <a id="intent"></a>**Intent** — short for [`sync_intent`](#sync-intent): kiki's durable record of one update that it owes a following thread's agent. See [Synchronization intent: the sole protocol authority](05-cascade.md#synchronization-intent-the-sole-protocol-authority).
- <a id="coalescing"></a>**Coalescing** — folding several waiting parent changes into one intent. An intent in `Detected` may absorb later compatible parent transitions: kiki replaces `to_base` with the newest exact base, reclassifies the intent's kind, and records every contributing operation. Once reconciliation starts, absorption stops, and later transitions create a new intent. See [Coalescing](05-cascade.md#coalescing).
- <a id="reconciliation-lock"></a>**Reconciliation lock** — a per-thread lock that makes concurrent hook decisions and recovery for one thread run one at a time. It is held in memory by `CascadeOrchestrator`. Crash recovery comes from the durable intent state, not from the lock. See [Reconciliation lock and ordering](05-cascade.md#reconciliation-lock-and-ordering).
- <a id="recovery-bundle"></a>**Recovery bundle** — a saved copy of the files at risk, made before kiki touches a stale workspace that has unrecorded edits. [`WorkspaceRecovery`](#workspacerecovery) creates it at `~/.config/kiki/repos/<repo_id>/recovery/<intent_id>/`, outside the source workspace. See [Recovery steps](05-cascade.md#recovery-steps).
- <a id="batch-admission"></a>**Batch admission (`Block` / `PassThrough`)** — kiki's decision, for one [tool batch](#tool-batch), to either block it (`Block`) or let it run (`PassThrough`). The first admitted call fixes the decision for the whole batch. The in-memory copy is only a cache. A durable `Block` can be rebuilt from the intent. A lost `PassThrough` is never guessed: kiki restarts the incarnation instead. See [Batch admission is only a cache](05-cascade.md#batch-admission-is-only-a-cache).
- <a id="delivery-barrier"></a>**Delivery barrier** — the durable `Block` decision bound to one tool batch. While the barrier stands, every call in that batch is blocked. It is [fail-closed](#fail-closed), because workspace files may already have changed. See [Delivery protocol](05-cascade.md#delivery-protocol).
- <a id="byte-stable-payload"></a>**Byte-stable payload** — the message text for the agent, saved once on the intent so that every retry sends exactly the same bytes. See [What the row holds](05-cascade.md#what-the-row-holds).
- <a id="model-turn"></a>**Model turn** — one response from the agent's model. A turn may send out a [tool batch](#tool-batch). Only a later model turn can acknowledge a delivery. See [Delivery protocol](05-cascade.md#delivery-protocol).
- <a id="delivery-epoch"></a><a id="exhausted-intent"></a>**Delivery epoch and exhausted intent** — two terms about delivery retries that keep failing.
  - An **exhausted intent** is an intent whose bounded delivery attempts have all failed. kiki stops retrying. It leaves the intent unacknowledged with its saved payload intact, keeps the agent hard-paused, and raises a loud attention event. Resuming is an explicit human action through [`retry-delivery`](#retry-delivery) or [`discard-delivery`](#discard-delivery).
  - The **delivery epoch** is a counter on the intent that marks each fresh round of attempts. Every attempt is stamped with its epoch, and retry limits count only attempts from the current epoch.

  See [Hard-restart fallback](05-cascade.md#hard-restart-fallback) and [Repairing an exhausted intent](05-cascade.md#repairing-an-exhausted-intent).

## Transcript

- <a id="thread-transcript"></a>**Thread transcript** — kiki's locally stored record of the conversation in each thread. It holds text events written by the human, by the agent, and by kiki, and it ties them to jj change-ids (the ids of jj [changes](#ext-change)).
  - Rows live in `~/.config/kiki/repos/<repo_id>/state.db`. They are never pushed, and they do not enter the source repo.
  - One thing may still leave the machine: a catch-up that the user explicitly consented to may send selected text to the configured model provider.
  - Each row separates `author` (`human|agent|kk`) from `direction` (`inbound_to_agent|outbound_from_agent|local_record`). This keeps context written by kiki from being credited to the agent.

  See [Transcript](06-transcript.md).

- <a id="local-storage-no-publication-rule"></a><a id="local-storage"></a><a id="no-publication-rule"></a>**Local-storage / no-publication rule** — the rule about where transcript rows live and where they may go. Transcript rows are stored under `~/.config/kiki/`. They do not feed anything that kiki publishes outside: `kk publish` PR drafting (a PR is a [pull request](#ext-pull-request)), auto-describe, or auto-rename. Sending catch-up text or [MCP](#ext-mcp) output that comes from the transcript to a hosted harness is a different boundary, called provider egress. It needs remembered consent for the exact thread, provider, purpose, and disclosure version. See [Transcript storage and egress are explicit](02-invariants.md#transcript-storage-and-egress-are-explicit).
- <a id="synthesized-true"></a>**`synthesized=TRUE`** — a flag on a transcript row. It says the row is content that kiki composed and the agent received: cascade injections, reopen catch-up, and hard-escalation framing. The flag lets `kk reopen` catch-up leave earlier catch-ups out of its source query. Without it, each reopen would summarize the previous summaries, and the text would compound on every reopen. See [Reopen catch-up](06-transcript.md#reopen-catch-up).
- <a id="anchor-unknown-true"></a>**`anchor_unknown=TRUE`** — a flag on a backfilled transcript row. It says the row's timestamp is older than the available `op_history`, so kiki cannot reliably tie the row to a `(change_id, commit_id, op_id)`. Queries that depend on anchors skip these rows by default. `--recent` and FTS5 search (SQLite's full-text search) include them. See [transcript anchoring](17-decisions/transcript-anchoring.md).
- <a id="transcriptadapter"></a>**TranscriptAdapter** — the v1.x interface (a Rust trait) on the capture side that hides the differences between harnesses. For each harness it covers four jobs: finding the session record, tailing it, projecting it to `(author, direction, text, dedup_key)`, and reporting offsets. Its first implementations read Claude Code session JSONL and Codex rollout JSONL. (JSONL is a file format with one JSON value per line.) See [Capture](06-transcript.md#capture).
- <a id="catch-up"></a>**Catch-up** — a message that gives a reopened thread's agent some context from the earlier conversation. kiki composes it from recent transcript rows where `synthesized=false`. Plain `kk reopen` sends no transcript text. `kk reopen --catch-up` requests a catch-up, and kiki sends it only after the human consents to provider egress. See [Reopen catch-up](06-transcript.md#reopen-catch-up).
- <a id="backfill"></a>**Backfill** — importing transcript rows that were written while kiki was not watching. Backfill ties rows to jj history through the [operation-history cache](#operation-history-cache). If no reliable anchor exists, the row is marked [`anchor_unknown=TRUE`](#anchor-unknown-true). See [Backfill](06-transcript.md#backfill).
- <a id="provider-egress"></a><a id="provider-egress-consent"></a>**Provider egress and provider-egress consent** — **provider egress** is transcript text leaving the machine to go to a model provider. **Provider-egress consent** is the human's recorded permission for that. Each record covers one repo, one thread, one provider identity, one purpose (`catch_up` or `transcript_mcp`), and one disclosure-policy version. A change in any of these fails closed and asks again. It is a privacy record. It is not a `HumanApproval` and not configuration. See [Provider-egress consent](06-transcript.md#provider-egress-consent).

## Agent and harness

- <a id="harness"></a>**Harness** — an agent runtime that kiki starts and coordinates with: the program that runs a coding agent. In v1 the harnesses are [Claude Code](#ext-claude-code) and [Codex](#ext-codex); others are deferred. In code, a harness exposes a `Harness` factory trait plus a `RunningAgent` instance trait. See [Harness adapter](13-architecture/harness-adapter.md).
- <a id="runtime-agent-incarnation"></a>**Runtime agent incarnation** — one harness [process](#ext-process) that kiki manages. kiki identifies it by its own UUID (a unique id). That id is separate from the harness's conversation or session id, which the harness can resume. Delivery acknowledgement belongs to the incarnation. So restarting with the same harness session cannot falsely acknowledge output that only the earlier process saw. See [Trait pair](13-architecture/harness-adapter.md#trait-pair).
- <a id="incarnation"></a>**Incarnation** — short for [runtime agent incarnation](#runtime-agent-incarnation): one life of a managed harness process, from its start to its exit. `agent_session_id` identifies it and changes on every restart. The protocol calls the same value `incarnation_id`. `harness_session_id` is different: it identifies the harness's conversation and may be reused by `--resume`, so one conversation can span several incarnations. See [Trait pair](13-architecture/harness-adapter.md#trait-pair).
- <a id="capabilities"></a>**Capabilities** — a typed struct that a `Harness` returns to say what it can prove. Its fields are `soft_pause`, `session_resume`, `structured_tool_hooks`, `parallel_batch_boundary`, `exclusive_pre_tool_use`, `restart_startup_delivery`, `mcp_client`, and `quiescence_detection`. The cascade orchestrator chooses its path from these proofs of behavior. It does not choose from the settings mechanism that was used to get them. See [Capabilities](13-architecture/harness-adapter.md#capabilities).
- <a id="agent-display-states"></a>**Agent display states** — the four values that people see for an agent: `idle`, `working`, `finished`, and `blocked`. They are a projection of `AgentStatus` plus turn-completion and attention signals, defined in [Harness adapter](13-architecture/harness-adapter.md#agent-display-states). They are for display only. The orchestrator makes decisions from `AgentStatus`, never from these values.
- <a id="pretooluse-posttoolbatch-hooks"></a><a id="pretooluse"></a><a id="posttoolbatch-hooks"></a>**PreToolUse / PostToolBatch hooks** — kiki's two protocol entry points around an agent's tool calls. A [hook](#ext-hook) is a point where the harness runs a small outside program. Each adapter maps these two names onto its own harness's hook events.
  - kiki exclusively owns the pre-tool boundary in every managed v1 process incarnation.
  - The first admitted call fixes the pass-or-block decision for the whole [tool batch](#tool-batch), before any mutation. Once the payload is prepared, a blocked batch emits the saved payload for every call.
  - `PostToolBatch` marks only that exact `SoftBatch` complete. A later model turn performs the acknowledgement.
  - Claude Code's `PostToolUse` event is not part of the protocol.
  - Codex's `PostToolUse` event cannot be part of it. A denied call never executes and fires no post-tool event. So a proven-serial Codex adapter reports its single-call batch complete through the next turn-scoped hook event, which cannot arrive before the blocked call resolved.
  - `RestartStartup` uses its tagged startup-input proof instead.

  See [Hook](13-architecture/harness-adapter.md#hook) and [Delivery protocol](05-cascade.md#delivery-protocol).

- <a id="kk-hook"></a>**`kk-hook`** — the hook sidecar: the small kiki program that the managed harness's hooks run (Claude Code and Codex). It handles exclusive `PreToolUse` admission and reports `PostToolBatch` completion. From the harness's session-start event it also sends the [ready handshake](#ready-handshake). It is a pure client of `kkd`'s [gRPC](#ext-grpc) service and reads the thread's [`ThreadScoped<T>` credential](#threadscoped-credential). The per-thread [hook launcher](#hook-launcher) ships in the same crate. See [Hook](13-architecture/harness-adapter.md#hook) and [Crate layout](13-architecture/crates.md).
- <a id="delivery-receipt"></a>**Delivery receipt** — the Codex adapter's authoritative evidence that the model consumed a payload. It is the result that the harness session record saved for a blocked `tool_use_id`. Before acknowledgement, that result must match the saved payload byte for byte.
  - `MarkDelivered` proves only that the hook wrote stdout.
  - The receipt proves that the model received the payload itself, and not a result substituted after a timeout or a generic result from the hook launcher.
  - A contrary receipt (one that does not match) causes a redelivery on the arriving batch, at most once per intent. A repeat fails over to `RestartStartup`, which does not ride the hook output.
  - An unreadable receipt defers, or fails closed into `RestartStartup`.

  See [Codex boundary mapping](13-architecture/harness-adapter.md#codex-boundary-mapping).

- <a id="contextmessage"></a>**`ContextMessage`** — the message kiki sends to a thread's agent about a cascade. Its shape is `{ kind: ContextMessageKind, text: String, structured: Option<JsonValue> }`. It is byte-stable, and it is embedded in a materialized intent for delivery to the thread's agent. See [ContextMessage](13-architecture/harness-adapter.md#contextmessage).
- <a id="agentstatus"></a>**`AgentStatus`** — the harness adapter's report of what an agent is doing. Its values are `Running | Quiescent | Stuck(duration) | Crashed`. It is derived only from the harness's own hooks and lifecycle events, the pane launcher's exit report, and `ProcessSupervisor`. The terminal runtime never feeds it. The cascade makes decisions from it; people see the [agent display states](#agent-display-states). See [Agent status](13-architecture/harness-adapter.md#agent-status).
- <a id="launch-specification"></a>**Launch specification** — the exact recipe for starting a harness: argv (the command line), environment, working directory, and settings paths. In code it is a `LaunchSpec`. `kkd` computes it through the harness adapter's `launch_spec`. The `agent` [pane launcher](#pane-launcher) receives it through its gate and executes exactly that. It removes every `HERDR_*` variable from the harness's environment. See [The adapter never starts a process](13-architecture/harness-adapter.md#the-adapter-never-starts-a-process).

## Auth

- <a id="bootstrap-admin-credential"></a>**Bootstrap Admin credential** — the secret that holds the [daemon](#ext-daemon)'s bootstrap authority, used for first setup. It is stored at `~/.config/kiki/admin-cred` (mode `0600`, readable only by the owning user). It is not presented automatically by every CLI invocation. It is not, by itself, evidence that a human is present. See [Credential and capability classes](04-authority.md#credential-and-capability-classes).
- <a id="human-approval"></a>**Human approval** — a short-lived, one-use grant that lets one consequential action happen. It is bound to one requesting credential, method, target, argument digest (a [hash](#ext-hash) of the arguments), and plan rendered by the daemon. kiki issues it only after an enrolled foreground [`ApprovalPresenter`](#approvalpresenter) confirms a saved challenge. Before any outside effect, kiki atomically claims the approval into one durable operation journal. After a crash, kiki may resume only that exact plan. It never reuses the approval for another action. See [Two-phase foreground approval](04-authority.md#two-phase-foreground-approval).
- <a id="approvalpresenter"></a>**`ApprovalPresenter`** — the identity of a local program that is allowed to show an approval plan to a human and collect the answer. It is enrolled explicitly through Admin bootstrap.
  - It is stored outside managed workspaces. kiki never injects it into a harness, a hook, a shell pane environment, or an ordinary operational request.
  - It may confirm or cancel a pending approval challenge only while its CLI or TUI process owns the foreground controlling terminal: the terminal the user is actively typing into.
  - It cannot invoke thread operations, widen a challenge, or mint an approval without a challenge that the daemon issued.

  It exists so that an agent does not approve its own request by accident. See [Credential and capability classes](04-authority.md#credential-and-capability-classes).

- <a id="threadscoped-credential"></a>**`ThreadScoped<T>` credential** — a secret that is bound to one thread and authorizes work on that thread only.
  - It is stored at `~/.config/kiki/repos/<repo_id>/credentials/<thread_id>` (mode `0600`).
  - It is read by `kk-hook`, by contextual `kk`, and later by same-thread readers.
  - Launch-scoped harness settings refer to it by absolute path. Those settings are Claude Code's generated settings file or Codex's generated `CODEX_HOME`.
  - Claude Code's ownership-tracked fallback merges only `.claude/settings.local.json`.
  - kiki never writes the tracked `.claude/settings.json` or anything under `<workspace>/.codex/`.

  See [Credential and capability classes](04-authority.md#credential-and-capability-classes).

- <a id="registrationscoped"></a>**`RegistrationScoped<repo_id>` credential** — a secret that is bound to one registered repo. The short form is `RegistrationScoped`. It lets `kk` do a small amount of work when it is not inside any thread.
  - kiki issues it when `kk init` registers a repo, and revokes it at `kk repo unregister`.
  - It is written to `~/.config/kiki/repos/<repo_id>/credentials/registration` with mode `0600`.
  - `kk` reads it when no thread context resolves.
  - It authorizes the [repo-summary read](#repo-summary-read-scope) and `BeginApproval` for that repo, and nothing else. `kk ls --all-repos` presents each repo's own registration credential.

  See [Credential and capability classes](04-authority.md#credential-and-capability-classes).

- <a id="repo-summary-read-scope"></a>**Repo-summary read scope** — the one cross-thread read that needs no approval. Any `ThreadScoped<T>` or `RegistrationScoped` credential may read the fixed set of summary fields for threads in the same repo, including each thread's terminal target. The read is same-repo only, read-only, and summaries only (no diffs, no transcripts). It is the single cross-thread read that a `ThreadScoped<T>` credential can perform. See [Sensitive reads](04-authority.md#sensitive-reads).

## Terminal runtime

- <a id="herdr"></a>**Herdr** — the [terminal multiplexer](#ext-terminal-multiplexer) that kiki uses as its terminal runtime (see also the [outside entry](#ext-herdr)). Herdr owns [PTYs](#ext-pty), [panes](#ext-pane), [tabs](#ext-tab), layout, input, rendering, and a native sidebar. Its hierarchy is session → workspace → tab → pane. See [Terminal runtime](13-architecture/terminal-runtime.md).
- <a id="dedicated-herdr-server"></a>**Dedicated Herdr server** — the one named Herdr server that [`kkd`](#kkd) starts for each user. Its session name is `kiki` by default. `kkd` starts it with a configuration file that kiki generates and with a constructed environment, under the user's service manager. It is separate from the user's default Herdr server in four ways: process, socket, saved session, and configuration file. A Herdr _session_ is this server namespace. It is not a per-thread object. See [Topology](13-architecture/terminal-runtime.md#topology).
- <a id="terminal-group"></a>**Terminal group** — the terminal home of one thread: one Herdr workspace on the dedicated server. It is a mutable [projection](#projection) of the thread. See [Topology](13-architecture/terminal-runtime.md#topology).
- <a id="role-pane"></a>**Role pane** — a pane that kiki provisions with a declared role: `agent`, `shell`, or `ui`. The role comes from the gate claim made by the pane's [pane launcher](#pane-launcher). The role stays with the identity of the process that claimed it. It never comes from the pane's position or label. Any other pane in the group is a [`user` pane](#user-pane). See [Topology](13-architecture/terminal-runtime.md#topology).
- <a id="user-pane"></a>**`user` pane** — any pane or tab in a terminal group that is not a role pane, such as a split the human opened. `user` is the absence of a role, not a role. A pane with no live claiming process is also a `user` pane, whatever its id or label says. kiki never recreates a `user` pane, but close observes and accounts for every process in it. See [Topology](13-architecture/terminal-runtime.md#topology) and [Identity](13-architecture/terminal-runtime.md#identity).
- <a id="hook-launcher"></a>**Hook launcher** — the per-thread process on the hook side. It caches a batch's first admission decision. When the sidecar is dead and a barrier is active, it answers with a generic blocking deny. It has nothing to do with the pane launcher. See [Hook](13-architecture/harness-adapter.md#hook).
- <a id="pane-launcher"></a>**Pane launcher** — the kiki process that is the direct PTY child of every role pane. Herdr starts it by direct argv (an exact command and arguments, not text typed into a shell), with an explicit working directory (cwd) and environment. It works like this:
  1. On start it presents a [provision nonce](#provision-nonce), usable once per role, in `ReportLauncherStarted`.
  2. It blocks on a database-backed gate, after `kkd` has checked its process identity from the operating system (OS). The `agent` launcher waits on its gate through a supervision stream to `kkd` that it keeps open for its whole life.
  3. For `agent`, it then creates the harness as its child. The child is held until `kkd` records the child's identity.

  The `agent` launcher stays alive across incarnations as the role's supervisor. See [Provisioning](13-architecture/terminal-runtime.md#provisioning).

- <a id="provision-nonce"></a>**Provision nonce** — a one-time token (a [nonce](#ext-nonce)) that `kkd` places in a pane launcher's environment when it creates a role pane. The launcher presents it in `ReportLauncherStarted` to claim its role, and it can be used once per role. It is never placed in argv, because Herdr saves and exposes launch argv. It is not a secret to rely on, because any process of the same user can read another process's starting environment. It is safe only because it is one-use per role and `kkd` binds the claim to the caller's process identity. See [Provisioning](13-architecture/terminal-runtime.md#provisioning).
- <a id="server-instance"></a>**Server instance** — one lifetime of the dedicated server process, from start to exit. It is identified by the socket peer's `(pid, start_time)`. Herdr ids are locators that are valid only within one server instance. See [Identity](13-architecture/terminal-runtime.md#identity).
- <a id="launch-gate-ready-handshake"></a><a id="launch-gate"></a><a id="ready-handshake"></a>**Launch gate / ready handshake** — the two checks between "a pane exists" and "the thread is `Active`".
  - The **launch gate** is the one-use, database-backed gate that a pane launcher waits on before it may start a harness. There is one per incarnation.
  - The **ready handshake** is the settings-bound report that `kk-hook` sends from the harness's session-start event. Only this report lets a thread enter `Active`.

  See [Provisioning](13-architecture/terminal-runtime.md#provisioning).

- <a id="terminal-binding"></a>**Terminal binding** — kiki's record that one provisioned terminal group, on one server instance, belongs to one thread. Launcher handshakes establish it. Close, replacement, or the end of the instance ends it. See [Identity](13-architecture/terminal-runtime.md#identity).
- <a id="terminalruntime-terminalclient-processsupervisor"></a><a id="terminalruntime"></a><a id="terminalclient"></a><a id="processsupervisor"></a>**`TerminalRuntime` / `TerminalClient` / `ProcessSupervisor`** — the three modules that face the terminal runtime and the OS.
  - `TerminalRuntime` (in `kkd`) provisions, observes, closes, and publishes.
  - `TerminalClient` (in `kk`) handles caller-local focus and attach.
  - `ProcessSupervisor` (in `kkd`) handles OS process identity, freeze, verified resume, verified exit, and holder inventory.

  See [Terminal runtime](13-architecture/terminal-runtime.md).

- <a id="agent-quiescence"></a>**Agent quiescence** — the harness adapter's proof that the agent is idle (`AgentStatus::Quiescent`). It is the cascade's [safe boundary](#safe-boundary) when no hook is involved. It is never inferred from the terminal. See [Invariant](05-cascade.md#invariant).
- <a id="process-quiescence-proof"></a>**Process quiescence proof** — the supervisor's evidence that every process in the listed terminal containers, and every other [holder](#holder) of the workspace, is accounted for and stopped. Only close, destroy, and repair use it. It is built from seven parts:
  - write-ahead recording;
  - fixed-point discovery (repeating the search until two full passes find the same set);
  - prior stop states;
  - a holder scan;
  - a repository-lock check;
  - an armed filesystem watch;
  - a terminal mutation fence.

  If the result is `Unknown`, kiki keeps the files and names each offending process. See [Process quiescence proof](13-architecture/terminal-runtime.md#process-quiescence-proof).

- <a id="post-freeze-recheck-final-proof-post-exit-filesystem-recheck"></a><a id="post-freeze-recheck"></a><a id="final-proof"></a><a id="post-exit-filesystem-recheck"></a>**Post-freeze recheck / final proof / post-exit filesystem recheck** — the three checks around a close.
  - The **post-freeze recheck** binds the frozen state to the approved fingerprint.
  - The **final proof** runs after the checkpoint and the child work, immediately before kiki terminates anything. It is the recovery boundary.
  - The **post-exit filesystem recheck** confirms, after termination, that the files still match what the final proof saw.

  See [Process quiescence proof](13-architecture/terminal-runtime.md#process-quiescence-proof) and [Termination and verified exit before deletion](13-architecture/terminal-runtime.md#termination-and-verified-exit-before-deletion).

- <a id="verified-resume-verified-exit"></a><a id="verified-resume"></a><a id="verified-exit"></a>**Verified resume / verified exit** — the two proofs that end a freeze.
  - **Verified resume** comes after an aborted operation. It is proof that the role launchers answer under their recorded identities and that the terminal group is intact.
  - **Verified exit** comes before deletion. It is proof from the OS that every frozen process identity is gone. kiki gets this proof by killing each process itself while the process is still stopped.

  Neither proof is inferred from a reply by the terminal runtime. See [Verified resume](13-architecture/terminal-runtime.md#verified-resume) and [Termination and verified exit before deletion](13-architecture/terminal-runtime.md#termination-and-verified-exit-before-deletion).

- <a id="orphan"></a>**Orphan** — a process that kiki recorded and that is alive where kiki's records say none should be. There are two kinds: a recorded identity without a current terminal binding, and a harness remnant left under the `agent` launcher by a retired incarnation. Orphans are possible under any terminal host. An orphan blocks replacement, materialization, and deletion until it is resolved. A holder that kiki never recorded is not an orphan. It matters only to an operation that deletes the workspace. See [Orphans](13-architecture/terminal-runtime.md#orphans).
- <a id="holder"></a>**Workspace holder** — a process that is using a thread's workspace directory. More exactly, it is a process of the same user (same UID) whose working directory, root, mapped file, or open [file descriptor](#ext-file-descriptor) refers to the workspace. `kkd`, `kkd`'s own child processes, and the invoking `kk` are excluded. An editor, a file watcher, or a shell in another terminal can be a holder. A holder that kiki never recorded never blocks an `Active` thread's boundaries. It matters only to an operation that deletes the workspace. There, a holder outside the frozen set makes the result `Unknown`, unless the plan names it as an [accepted holder](#accepted-holder). See [Process quiescence proof](13-architecture/terminal-runtime.md#process-quiescence-proof) and [Orphans](13-architecture/terminal-runtime.md#orphans).
- <a id="accepted-holder"></a>**Accepted holder** — a process outside the frozen set that holds the workspace, and that an approved deletion plan names by exact identity. An example is an editor that the human chose to leave open. Any holder that the plan does not name makes the result `Unknown`. See [Process quiescence proof](13-architecture/terminal-runtime.md#process-quiescence-proof).
- <a id="remnant-container-remnant-pane"></a><a id="remnant-container"></a><a id="remnant-pane"></a>**Remnant container / remnant pane** — a Herdr workspace and its panes, as the runtime restored them after a [cold restore](#cold-restore). Usually each pane is a plain shell with no launcher and no role. kiki never adopts or reuses them. A repair plan lists the remnant containers whose processes hold the workspace, and it disposes of them with verified exit. See [Runtime changes are reconciliation](13-architecture/terminal-runtime.md#runtime-changes-are-reconciliation).
- <a id="unbound-container"></a>**Unbound container** — a Herdr workspace on the dedicated server that has no binding and is not a restore remnant. An example is the default shell that is left behind when provisioning stopped between its two calls. kiki handles it like a remnant container. See [Runtime changes are reconciliation](13-architecture/terminal-runtime.md#runtime-changes-are-reconciliation).
- <a id="cold-restore"></a>**Cold restore** — what happens when a new server instance rebuilds layout, labels, and working directories from saved state, with new processes. It is different from a client reconnect, a pane exit, and a live handoff. kiki always treats it as reconciliation and never as readiness. See [Runtime changes are reconciliation](13-architecture/terminal-runtime.md#runtime-changes-are-reconciliation).
- <a id="caller-local-focus"></a>**Caller-local focus** — navigation that moves only the Herdr client of the viewer who ran the command. Other viewers stay where they are. It is the contract of `kk switch`, and it requires Herdr's client-targeted focus capability. See [Caller-local focus](13-architecture/terminal-runtime.md#caller-local-focus).
- <a id="herdr-client"></a>**Herdr client** — the Herdr program a person runs to look at and control a Herdr server. Several clients can be attached to the dedicated server at once. Which terminal a human is looking at belongs to each client. See [Ownership](13-architecture/terminal-runtime.md#ownership).
- <a id="client-targeted-focus"></a>**Client-targeted focus (`client_targeted_focus`)** — the Herdr extension that [caller-local focus](#caller-local-focus) needs: a way to move one named client and no other. Herdr advertises it through the `client_targeted_focus` capability flag. Until it is advertised, `kk switch <thread>` fails with a message that names the missing capability. `kk switch --all-clients <thread>` is the separate, explicit operation that moves every attached client. See [Caller-local focus](13-architecture/terminal-runtime.md#caller-local-focus).
- <a id="terminal-target"></a>**Terminal target** — where a thread's terminal group currently lives. It is the dedicated server's address and instance, plus the current binding's terminal-group and agent-pane refs. `kk ls` and `kk switch` read it. A thread with no current binding has no terminal target. See [`kk switch`](09-commands.md#kk-switch) and [Sensitive reads](04-authority.md#sensitive-reads).
- <a id="freeze"></a><a id="frozen-set"></a>**Freeze and frozen set** — a **freeze** is `ProcessSupervisor` stopping (pausing) every process in the listed terminal containers, so that nothing can write to the workspace while kiki checks it. The **frozen set** is the exact set of process identities that the freeze recorded and stopped. Close, destroy, and repair use a freeze. The cascade never does. See [Process quiescence proof](13-architecture/terminal-runtime.md#process-quiescence-proof).
- <a id="mutation-fence"></a>**Mutation fence** — a guard that stops the terminal server from changing a terminal group during a freeze, for example when a user splits a pane. It exists only where the runtime advertises `mutation_fence`. Where it does not, kiki records the group's pane and tab set with the frozen set and treats any later difference as [drift](#drift). See [Process quiescence proof](13-architecture/terminal-runtime.md#process-quiescence-proof).
- <a id="harness-remnant"></a>**Harness remnant** — a process left behind by a retired harness. More exactly, it is any process other than the launcher itself that is found in an inventory rooted at the `agent` launcher when no incarnation is live. A tool that the dead harness was running is the usual case. It is one kind of [orphan](#orphan). It raises `OrphanedProcess` and blocks the gate for a replacement incarnation. See [Orphans](13-architecture/terminal-runtime.md#orphans).
- <a id="orphan-scan"></a>**Orphan scan** — `kkd` asking `ProcessSupervisor` which recorded process identities are still alive where none should be. It runs at daemon start before any thread is reported `Active`, whenever the `server_instance_id` changes, before a replacement terminal group or incarnation, and before any step that forgets or deletes a jj workspace. See [Orphan scan](13-architecture/daemon.md#orphan-scan) and [Orphans](13-architecture/terminal-runtime.md#orphans).

## State

- <a id="operation-frontier"></a>**Operation frontier** — the complete current set of head operations in jj's [operation log](#ext-operation-log). A head is an operation that no later operation builds on. There is usually one head. There can be several when operations happened at the same time, because jj's operation history is a [DAG](#ext-dag) and not a straight line. kiki reads the frontier with the `OpFrontierSampler`, without loading the repository, and saves what it observed in `op_watch_frontier`. It tracks a frontier plus a `processed_at` mark on each operation, not a single cursor. See [Operation-DAG frontier](13-architecture/op-log-watcher.md#operation-dag-frontier).
- <a id="unmerged-frontier"></a>**Unmerged frontier** — an operation frontier that has several heads which no jj command has merged yet. kiki does not merge them just by observing.
  - kiki works out each head's view on its own. It never blends a workspace's `@`, a bookmark target, or the expected checkpoint target across heads.
  - kiki writes the single-valued caches `threads.thread_head_commit_id` and `threads.bookmark_expected_commit_id` only from a view that every current head agrees on.
  - While heads disagree about a thread, status prints "frontier unmerged" in place of that thread's checkpoint relationship. kiki raises no projection issue from one head's view alone.
  - A step that needs one view (a checkpoint, publish, detach, close, or an explicit rebase) asks for deliberate integration first. If heads still disagree after the bounded retry, the step fails without changing anything.

  See [Unmerged frontier](13-architecture/op-log-watcher.md#unmerged-frontier).

- <a id="pinned-read"></a>**Pinned read** — a jj read that names one exact operation id and ignores the working copy: `jj --at-op=<op_id> --ignore-working-copy …`. A pinned read does not [snapshot](#ext-snapshot), does not merge heads, works in a stale workspace, and works while several heads exist. It exists because many jj commands that look read-only are not: without a pin they snapshot the working copy or merge divergent heads. So kiki treats every unpinned command as a mutation. `--at-op=@` is not a pin. The only unpinned commands kiki runs are on the closed list in [Operation history is a DAG](02-invariants.md#operation-history-is-a-dag). See [Pinned reads and pinned mutations](13-architecture/op-log-watcher.md#pinned-reads-and-pinned-mutations).
- <a id="operation-history-cache"></a>**Operation-history cache** — kiki's saved copy of jj's operation history. It has four parts: normalized `op_history` nodes, `op_history_parents` DAG edges, per-view `op_workspace_heads`, and the `op_watch_frontier`. Live watching and restart catch-up fill it.
  - The workspace dimension matters. jj's op log is shared by the whole repo, but `@` belongs to one workspace.
  - No single parent column or cursor may flatten operations that cannot be ordered against each other.
  - Transcript backfill reads this cache, and it leaves ambiguous anchors unknown.

  See [Operation-DAG cache](13-architecture/op-log-watcher.md#operation-dag-cache).

- <a id="pending-kkd-prepends"></a>**`pending_kkd_prepends`** — a side table whose rows expire after a set time (TTL-bounded). The JSONL projector reads it to recognize `--resume` prepended messages that kiki composed, and to capture them as `synthesized=TRUE`. See [Capture](06-transcript.md#capture).
- <a id="op-log-watcher"></a>**Op-log watcher** — the part of `kkd` that watches jj's [operation log](#ext-operation-log). It detects operations that kiki did not run itself, such as a human or an agent using `jj` directly. It feeds the cascade and the transcript backfill. See [Op-log watcher](13-architecture/op-log-watcher.md).
- <a id="frontier-sampler"></a>**Frontier sampler** — the adapter, named `OpFrontierSampler`, that reads the complete current set of operation heads (the [operation frontier](#operation-frontier)) without loading the repository. jj has no supported interface for this yet, so the sampler depends on jj's internal store layout and is tied to known jj versions. For a layout it does not recognize, it reports `Unavailable`. See [Frontier sampling is a proof requirement](13-architecture/op-log-watcher.md#frontier-sampling-is-a-proof-requirement).
- <a id="deliberate-integration"></a>**Deliberate integration** — what kiki does when there are several operation heads and a step needs one view. Under the owning lock, kiki runs one designated jj command that merges the heads, with `--ignore-working-copy`. It samples again and requires a single head whose parents are the heads it sampled. kiki never lets a status query merge heads by accident. See [Pinned reads and pinned mutations](13-architecture/op-log-watcher.md#pinned-reads-and-pinned-mutations).
- <a id="re-anchoring"></a>**Re-anchoring** — starting kiki's record of jj operations again from the current heads, after jj discarded the operations kiki had recorded. If every thread's bookmark and head still match kiki's cached values, kiki re-anchors silently and records an `op_history_anchors` row. Otherwise it raises [`OperationHistoryRewritten`](#operationhistoryrewritten). See [Operation history rewritten](13-architecture/op-log-watcher.md#operation-history-rewritten).

## UI

- <a id="overlay-tui"></a>**Overlay TUI** — the interactive `kk` screen (a [TUI](#ext-tui) is a text-based user interface).
  - It opens as a Herdr popup from a keybinding that kiki generates. It also opens inline in any terminal when you run bare `kk` inside a registered repo.
  - It has two panes: a left thread list with Stack and Activity sections, and a right preview pane (transcript / diff / PR comments).
  - It carries the full action set (spawn, publish, close, interrupt). Consequential verbs are gated by foreground approval cards that the daemon issues.
  - You dismiss it with `q` / `esc`.

  See [Interface](10-interface/).

- <a id="herdr-sidebar-projection"></a>**Herdr sidebar projection** — the thread's row in Herdr's native sidebar. It shows the terminal group's label. In v1.x it also shows kiki's metadata tokens for lifecycle, cascade state, agent display state, and follows parent. `kkd` publishes it one way and republishes it after every resync. It replaces the earlier tmux status-line strip and the Activity role of the earlier persistent sidebar pane. It is never an input to any decision. See [Herdr sidebar projection](12-observability.md#herdr-sidebar-projection).
- <a id="ui-role-pane"></a>**`ui` role pane** — an optional v1.x pane that runs a long-lived kiki UI process. It keeps the Stack (follows) tree always visible. Its keybindings are restricted to navigation only. See [Interface](10-interface/).
- <a id="shell-pane"></a>**Shell pane** — the v1.x `shell` role pane (on by default). In it, the pane launcher is replaced by the user's `$SHELL`, at the thread's workspace cwd.
  - It sits beside the agent pane in the same tab. The default position is below, and it can be configured to the right.
  - It exists so that direct `jj` / `gh` / test invocations live alongside the agent without leaving the thread.
  - kiki ensures it at creation, at `kk reopen`, and at a terminal-restart repair. kiki does not recreate it at `kk switch`.
  - kiki does not manage what runs in it. But close observes and accounts for every process in it, as it does for `user` panes.

  See [Interface](10-interface/).

- <a id="stack-aware-collapse"></a>**Stack-aware collapse** — the default rule `kk log` uses to decide what to show in full.
  - The current thread and its full chain of follows ancestors render revision by revision.
  - Siblings, descendants that are not on the current line, and unrelated threads collapse to one-line summaries.
  - Trunk renders as its own root.

  See [`kk log`](09-commands.md#kk-log).

- <a id="logrenderer-statusrenderer"></a><a id="logrenderer"></a><a id="statusrenderer"></a>**`LogRenderer` / `StatusRenderer`** — two rendering modules in `kiki-core`. They are pure functions: they turn data into text and do nothing else.
  - `LogRenderer` produces the stack-aware revision view.
  - `StatusRenderer` produces the kk-shaped header that `kk status` uses. The `ui` pane reuses it through `--no-jj`.

  They are the single source of truth across the CLI, the overlay TUI, and the `ui` pane. See [Crate layout](13-architecture/crates.md).

- <a id="porcelain"></a>**Porcelain** — a friendly command layer over a more detailed model. The word comes from Git. `kk` is porcelain over the thread model. See [Commands](09-commands.md).
- <a id="attention-event"></a>**Attention event** — something that happened in a thread that a person may need to know about, such as an agent hitting a permission prompt. Each event has a default response, from a loud notification to a status mark. See [Attention events](12-observability.md#attention-events).
- <a id="toast"></a>**Toast** — a small message that pops up briefly and then goes away. In the overlay, a toast is a floating pill in the top-right corner that dismisses itself after `[ui] toast_ttl_ms` (default 4000). A Herdr toast is a different thing: Herdr's own notification, which kiki uses as one way to deliver attention events. See [Vocabulary](10-interface/spec.md#vocabulary).
- <a id="sidebar-label"></a><a id="sidebar-token"></a>**Sidebar label and sidebar token** — the two things kiki publishes into Herdr's sidebar.
  - The **sidebar label** is the one label per terminal group. It holds the repo directory name, the thread's display name, and a short provisioning tag. It is in the acceptance slice.
  - A **sidebar token** is a short state word that kiki publishes in v1.x: lifecycle state, cascade state, agent display state, and follows parent.

  See [Herdr sidebar projection](12-observability.md#herdr-sidebar-projection).

- <a id="thread-list"></a>**Thread list** — the left column of the overlay, holding the Stack and Activity sections. See [Vocabulary](10-interface/spec.md#vocabulary).
- <a id="preview-pane"></a>**Preview pane** — the right two-thirds of the overlay, showing a transcript tail, a working-copy diff, or PR comments. See [Vocabulary](10-interface/spec.md#vocabulary).
- <a id="chord-ribbon"></a>**Chord ribbon** — a one-line keybinding hint at the bottom edge of the overlay, toggled by `?`. See [Vocabulary](10-interface/spec.md#vocabulary).
- <a id="context-strip"></a>**Context strip** — the bottom-most line of the overlay or the UI pane: one compressed sentence of status. See [Vocabulary](10-interface/spec.md#vocabulary).

## Testing

- <a id="fixture"></a>**Fixture** — a prepared test setup: files, programs, or data arranged in a known state before a test runs. See [Testing](14-testing.md).
- <a id="fake"></a>**Fake** — a stand-in for a real dependency in a test, such as a pretend harness or a pretend terminal runtime that the test fully controls. See [Fakes](14-testing.md#fakes).

## v2 / future

- <a id="causal-chain"></a>**Causal chain** — a UUID (a unique id) stamped on each post that is driven by MCP (the [Model Context Protocol](#ext-mcp)). kiki uses it to detect cycles, too much depth, and branch fan-out in messaging between threads. See [Roadmap](16-roadmap.md).

## Outside terms

These terms come from the wider industry, not from kiki. Each entry gives a short plain definition and a link to an outside reference.

### Version control

- <a id="ext-jj"></a>**jj (Jujutsu)** — the version-control tool that kiki drives. Like Git, it records the history of a project's files. It can share a repository with Git. [jj documentation](https://docs.jj-vcs.dev/latest/)
- <a id="ext-git"></a>**Git** — the most widely used version-control tool. jj can store its history in a Git repository and exchange work with Git remotes. [Git](https://git-scm.com/)
- <a id="ext-commit"></a>**Commit** — one saved snapshot of the project's files, with a message and a pointer to the commit or commits before it. Each commit has a commit id that changes whenever the commit is rewritten. [jj glossary](https://docs.jj-vcs.dev/latest/glossary/)
- <a id="ext-change"></a>**Change** — in jj, one piece of work as it evolves over time. A change keeps the same change id while its commit is rewritten, so a change id is a stable name for "this piece of work". [jj glossary](https://docs.jj-vcs.dev/latest/glossary/)
- <a id="ext-revision"></a>**Revision** — jj's word for a commit. This book uses "revision" and "commit" for the same thing. [jj glossary](https://docs.jj-vcs.dev/latest/glossary/)
- <a id="ext-working-copy"></a>**Working copy** — the actual files on disk that you edit, as opposed to the history stored in the repository. [jj working copy](https://docs.jj-vcs.dev/latest/working-copy/)
- <a id="ext-working-copy-commit"></a>**Working-copy commit (`@`)** — the commit that jj keeps in step with the files on disk. jj writes it as `@`. It is the "page you are on right now". [jj glossary](https://docs.jj-vcs.dev/latest/glossary/)
- <a id="ext-snapshot"></a>**Snapshot** — the act of jj reading the files on disk and recording their current content into the working-copy commit. Most jj commands snapshot first, even ones that look read-only. [jj working copy](https://docs.jj-vcs.dev/latest/working-copy/)
- <a id="ext-workspace"></a>**Workspace (jj)** — one working copy attached to a repository. A repository can have several workspaces. Each has its own directory of files and its own `@`, and all of them share one history. [jj working copy](https://docs.jj-vcs.dev/latest/working-copy/)
- <a id="ext-stale-workspace"></a>**Stale workspace** — a workspace whose files on disk are behind, because its working-copy commit was changed from another workspace. `jj workspace update-stale` brings the files up to date. [jj working copy](https://docs.jj-vcs.dev/latest/working-copy/)
- <a id="ext-bookmark"></a>**Bookmark (jj's meaning)** — a named pointer to a commit, like a Git branch. It does not move forward on its own when you add new commits. For kiki's use of it, see [Bookmark](#bookmark). [jj bookmarks](https://docs.jj-vcs.dev/latest/bookmarks/)
- <a id="ext-operation"></a>**Operation** — one recorded action that changed a jj repository, such as a commit, a rebase, or a bookmark move. Each has an operation id. [jj operation log](https://docs.jj-vcs.dev/latest/operation-log/)
- <a id="ext-operation-log"></a>**Operation log (op log)** — jj's record of every operation on a repository. It lets jj undo actions and show the repository as it was at an earlier operation. [jj operation log](https://docs.jj-vcs.dev/latest/operation-log/)
- <a id="ext-rebase"></a>**Rebase** — moving a commit, or a chain of commits, so that it builds on a different parent commit. The content of the work stays; its starting point changes. [jj command reference](https://docs.jj-vcs.dev/latest/cli-reference/)
- <a id="ext-revset"></a>**Revset** — a short expression in jj's query language that selects a set of revisions, such as "all ancestors of this commit". [jj revsets](https://docs.jj-vcs.dev/latest/revsets/)
- <a id="ext-conflict"></a>**Conflict** — what happens when two versions of the same content cannot be combined automatically. jj records the conflict inside the commit and lets work continue until someone resolves it. [jj conflicts](https://docs.jj-vcs.dev/latest/conflicts/)
- <a id="ext-colocated-repository"></a>**Colocated repository** — a checkout where jj and Git share one directory: `.jj/` and `.git/` sit side by side, and both tools see the same history. [jj and Git](https://docs.jj-vcs.dev/latest/git-compatibility/)
- <a id="ext-gh"></a>**GitHub CLI (`gh`)** — GitHub's command-line program for working with pull requests and other GitHub features. [GitHub CLI](https://cli.github.com/)
- <a id="ext-pull-request"></a>**Pull request (PR)** — a request on GitHub to merge one branch into another, with a place for review and discussion. [GitHub pull requests](https://docs.github.com/en/pull-requests)
- <a id="ext-ci"></a>**Continuous integration (CI)** — a service that automatically builds and tests each proposed change. [Continuous integration](https://en.wikipedia.org/wiki/Continuous_integration)

### Terminals

- <a id="ext-terminal-multiplexer"></a>**Terminal multiplexer** — a program that runs many terminal sessions inside one window and keeps them running when you disconnect. tmux is a well-known example. [Terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer)
- <a id="ext-herdr"></a>**Herdr** — a terminal multiplexer built for agent work. It is the one kiki uses. For kiki's use of it, see [Herdr](#herdr). [Herdr](https://github.com/herdrdev/herdr)
- <a id="ext-pane"></a>**Pane** — one rectangular terminal inside a multiplexer window. Several panes can share the screen side by side. [Terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer)
- <a id="ext-tab"></a>**Tab** — one screenful of panes inside a multiplexer. You switch between tabs the way you do in a web browser. [Herdr](https://github.com/herdrdev/herdr)
- <a id="ext-pty"></a>**PTY (pseudoterminal)** — the operating-system object that connects a program to a terminal window. The program reads and writes the PTY as if a person were typing at a real terminal. [Pseudoterminal](https://en.wikipedia.org/wiki/Pseudoterminal)
- <a id="ext-tui"></a>**TUI (text-based user interface)** — an interactive screen drawn with text characters inside a terminal. [Text-based user interface](https://en.wikipedia.org/wiki/Text-based_user_interface)

### Operating system

- <a id="ext-daemon"></a>**Daemon** — a program that runs in the background, without a window, and waits to do work for other programs. [Daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>)
- <a id="ext-process"></a>**Process** — one running instance of a program. The operating system gives each process a number called a process id (pid). [Process identifier](https://en.wikipedia.org/wiki/Process_identifier)
- <a id="ext-process-group"></a><a id="ext-session"></a>**Process group and session** — two ways the operating system bundles related processes. A process group is a set of processes that can be signalled together, such as one shell command and its helpers. A session is a set of process groups, usually everything started from one terminal. This OS session is unrelated to a Herdr session or a harness session. [Process group](https://en.wikipedia.org/wiki/Process_group)
- <a id="ext-signal"></a>**Signal** — a short message the operating system delivers to a process, for example to stop it, continue it, or kill it. [Signal](<https://en.wikipedia.org/wiki/Signal_(IPC)>)
- <a id="ext-file-descriptor"></a>**File descriptor** — a number a process uses to refer to a file, socket, or terminal it has open. [File descriptor](https://en.wikipedia.org/wiki/File_descriptor)
- <a id="ext-environment-variable"></a>**Environment variable** — a named value handed to a program when it starts, such as `HOME` or `PATH`. [Environment variable](https://en.wikipedia.org/wiki/Environment_variable)
- <a id="ext-unix-socket"></a>**Unix socket** — a special file that two programs on the same machine use to talk to each other. Its full name is Unix domain socket. [Unix domain socket](https://en.wikipedia.org/wiki/Unix_domain_socket)

### Software building blocks

- <a id="ext-rpc"></a><a id="ext-grpc"></a>**RPC and gRPC** — a remote procedure call (RPC) is one program asking another program to run a named function and send back the result. gRPC is a widely used system for defining and making such calls. [Remote procedure call](https://en.wikipedia.org/wiki/Remote_procedure_call), [gRPC](https://grpc.io/)
- <a id="ext-sqlite"></a>**SQLite** — a small database that lives in a single file and needs no separate server. This book also writes it as "sqlite". [SQLite](https://www.sqlite.org/)
- <a id="ext-transaction"></a>**Transaction** — a group of database changes that either all happen or all do not happen. A crash cannot leave it half done. [Database transaction](https://en.wikipedia.org/wiki/Database_transaction)
- <a id="ext-hash"></a><a id="ext-fingerprint"></a>**Hash, fingerprint, digest** — a short, fixed-size value computed from some data. If the data changes at all, the value changes too, so comparing two hashes shows whether two things are identical. [Cryptographic hash function](https://en.wikipedia.org/wiki/Cryptographic_hash_function)
- <a id="ext-nonce"></a>**Nonce** — a value that is meant to be used only once, so that an old message cannot be replayed. [Cryptographic nonce](https://en.wikipedia.org/wiki/Cryptographic_nonce)
- <a id="ext-idempotent"></a>**Idempotent** — safe to repeat. Doing an idempotent step twice has the same effect as doing it once. [Idempotence](https://en.wikipedia.org/wiki/Idempotence)
- <a id="ext-dag"></a>**DAG (directed acyclic graph)** — a set of items joined by one-way arrows that never loop back. An item can have several parents, so a DAG can branch and merge, unlike a straight line. [Directed acyclic graph](https://en.wikipedia.org/wiki/Directed_acyclic_graph)
- <a id="ext-race-condition"></a>**Race condition** — a bug where the result depends on which of two things happens first, and the order is not controlled. [Race condition](https://en.wikipedia.org/wiki/Race_condition)

### Coding agents

- <a id="ext-harness"></a>**Harness (agent harness)** — the program that runs an AI coding agent: it talks to the model, runs the tools the model asks for, and shows the conversation. Claude Code and Codex are harnesses. For kiki's use of the word, see [Harness](#harness). [Claude Code overview](https://docs.claude.com/en/docs/claude-code/overview)
- <a id="ext-claude-code"></a>**Claude Code** — Anthropic's coding-agent harness. [Claude Code overview](https://docs.claude.com/en/docs/claude-code/overview)
- <a id="ext-codex"></a>**Codex** — OpenAI's coding-agent harness, a command-line program. [Codex](https://github.com/openai/codex)
- <a id="ext-hook"></a>**Hook** — a point where a program stops and runs an outside command that you configured, then uses the command's answer. Agent harnesses offer hooks around tool calls, for example "before any tool runs". [Claude Code hooks](https://docs.claude.com/en/docs/claude-code/hooks)
- <a id="ext-mcp"></a>**MCP (Model Context Protocol)** — a standard way for an AI agent to connect to outside tools and data sources. [Model Context Protocol](https://modelcontextprotocol.io/)
