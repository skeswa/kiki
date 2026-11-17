# State schema

kiki keeps its state in two [SQLite](https://www.sqlite.org/) databases. SQLite is a small database engine that stores a whole database in one file.

- Every table is versioned through [migrations](https://en.wikipedia.org/wiki/Schema_migration). A migration is a scripted change to the layout of a database.
- When the [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) (kiki's background program, [`kkd`](../appendix-a-glossary.md#kkd)) restarts, it recovers by reading from sqlite.
- Because of this, [threads](../appendix-a-glossary.md#thread) survive crashes and reboots.

## Database split

One database belongs to the user. The other belongs to one registered repository, and there is one of those per repository.

| Path                                      | Scope    | Contents                                                                                                 |
| ----------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------- |
| `~/.config/kiki/state.db`                 | per-user | repo registry, daemon meta, terminal server instances, the Admin credential, presenters, unscoped audit  |
| `~/.config/kiki/repos/<repo_id>/state.db` | per-repo | threads, thread events, terminal bindings, process records, agent sessions, transcripts, cascades, audit |

Both databases live under `~/.config/kiki/`. This is kiki's centralized state directory.

- The source repo's own filesystem holds no kiki state.
- The per-repo `state.db` lives at `~/.config/kiki/repos/<repo_id>/state.db`.
- `<repo_id>` is a UUID (a long random id). kiki assigns it at `kk init` and records it in the per-user `repos` table.
- The user-level database knows which repos [`kkd`](../appendix-a-glossary.md#kkd) watches.
- The per-repo database holds everything that lives or dies with the repo.

### What happens when the source repo is moved

The `<repo_id>` UUID gives the centralized directory a stable name during one registration. The name is opaque: it says nothing about the repo. It is **not** an identity that survives the source repo being moved outside kiki.

kiki leaves no marker file inside the source repo. So its only handle on a registered repo is the repo's `canonical_path`.

If the user moves the tree with `mv`:

- `kk` run from the new location reports the repo as unregistered, because no `canonical_path` matches.
- The earlier `<repo_id>` and its centralized state stay in `~/.config/kiki/repos/<old_repo_id>/` until `kk repo unregister` is run against the original path.

v1 offers two ways to recover:

1. Move the source tree back, so the registered `canonical_path` matches again.
2. Run `kk repo unregister`, then run `kk init` at the new location. This starts a fresh registration with a new `repo_id`.

`kk repo unregister` has two modes:

- By default, it removes both the registry row and the centralized state directory.
- With `--keep-state`, it keeps the directory on disk so a person can inspect it by hand. kiki offers no managed recovery from it. A later `kk init` at the same canonical path creates a fresh `<repo_id>` with no link to the preserved bytes.

See [Commands · Repo registry](../09-commands.md#repo-registry). A move-aware `kk repo relocate` command is not in v1.

## Tables

The list below is table-level. Column-level definitions are derived from the behavioral chapters.

Each entry below has the same shape: what the table stores, its columns, and then its rules, one per bullet. A `?` after a column name means the column may be empty (null).

### Per-user (`~/.config/kiki/state.db`)

- **`repos`**: the registry of source repositories that kiki knows about.
  - Columns: `(repo_id, canonical_path, registered_at, opt_in_metadata)`.
  - `repo_id` is a UUID assigned at `kk init`. It is the key for the per-repo state directory at `~/.config/kiki/repos/<repo_id>/`.
  - `canonical_path` is the realpath (the full path with all symbolic links resolved) of the registered source repo at registration time. It is the only handle kiki has for matching a future invocation back to this row.
  - `repo_id` is stable for the life of the registration. This keeps the centralized directory's name from changing while kkd is running.
  - `repo_id` is **not** preserved across `kk repo unregister` + `kk init`. That pair is a fresh registration with a new UUID.
  - kiki cannot detect an out-of-band `mv` of the source tree by itself. See the move rules in the section above.

- **`daemon_meta`**: facts about the daemon itself.
  - It holds daemon startup info, the last-known socket path, and the schema version.

- **`terminal_servers`**: one row per lifetime of the [dedicated terminal server](../appendix-a-glossary.md#dedicated-herdr-server), started or observed. Each lifetime is a [server instance](../appendix-a-glossary.md#server-instance).
  - Columns: `(server_instance_id, state: Starting | Open | Unverified | Ended, runtime_kind, session_name, socket_path, peer_pid?, peer_start_time?, runtime_version?, protocol?, capabilities_json?, first_seen_at, ended_at?, ended_reason?)`.
  - **States.**
    - `kkd` writes the row in state `Starting` before it spawns a server. The peer and version columns are still empty.
    - `kkd` moves the row to `Open` once it has read the server's peer identity. That transaction fills the peer and version columns.
    - So a `kkd` crash between the spawn and the first connection is recoverable. On restart, `kkd` finds the `Starting` row and connects to the recorded socket. It either completes the row from the peer identity it reads, or ends the row as a failed start.
    - `Unverified` is the state of a row for a peer that `kkd` did not start. kiki provisions nothing on that server. The row never moves to `Open`; it only moves to `Ended`.
    - `Ended` is final. An ended row is never reopened.
    - At most one row is not `Ended`.
  - **Replacement.** If `[terminal] session`, `[terminal] herdr_bin`, or `[paths] herdr_dir` changes while a row is `Open`, or the current row is `Unverified`, `kkd` does not start a second server and writes no new row. It keeps the old instance, reports that a change is pending, and requires the user-scoped [`replace-terminal-server`](../appendix-a-glossary.md#replace-terminal-server) plan (`kk repair --server`). That plan lists every thread and process the replacement stops, needs a one-shot approval, stops the old server with [verified exit](../appendix-a-glossary.md#verified-exit), ends its row, and then starts a new one through `Starting`. Its journal lives in `user_approved_operations`, because it has no repository target.
  - `server_instance_id` is kiki's own row id for one observed socket peer `(pid, start_time)`. It is not a value the runtime supplies. (A socket peer is the process on the other end of a [Unix domain socket](https://en.wikipedia.org/wiki/Unix_domain_socket); a pid is a [process id](https://en.wikipedia.org/wiki/Process_identifier).)
  - The server is per-user, so the row lives in this database. Per-repo rows name it by `server_instance_id`.
  - Identity is the socket peer's `(peer_pid, peer_start_time)`. kiki verifies it on every connection.
  - A session name, a socket path, or a version string is never identity.
  - `runtime_version`, `protocol`, and `capabilities_json` are the values the server reported when that instance started. `RuntimeCapabilities` was derived from them.
  - A server `kkd` started is recognised by the peer identity on its `Open` row.
  - If the socket's peer differs from the `Open` row, the peer is a server `kkd` did not start. That includes the new server process after Herdr's own handoff or upgrade. kiki ends the `Open` row and inserts a new row in `Unverified` for the new peer. kiki does not re-prove survivors: each repo database ends the bindings of the old instance and raises `TerminalMissing`.
  - kiki provisions nothing on an `Unverified` server. The fix is `replace-terminal-server`, and after it [`restart-terminal`](../appendix-a-glossary.md#restart-terminal) for each thread.
  - An instance change where `kkd` itself started the new server, for example after a server crash, goes through `Starting` to `Open`. Each thread then needs only `restart-terminal`.
  - The [`TerminalRuntime`, `TerminalClient`, and `ProcessSupervisor`](../appendix-a-glossary.md#terminalruntime-terminalclient-processsupervisor) [traits](https://doc.rust-lang.org/book/ch10-02-traits.html) are defined in `kiki-core`. `HerdrRuntime` is the adapter for [Herdr](../appendix-a-glossary.md#herdr). `runtime_kind` names the adapter that observed the row.
  - See [Terminal runtime](terminal-runtime.md#identity).

- **`user_credentials`**: the [bootstrap Admin credential](../appendix-a-glossary.md#bootstrap-admin-credential).
  - Columns: `(cred_id, kind: 'Admin', credential_hash, issued_at, revoked_at?)`.
  - The `Admin` credential belongs to the user, not to a repository. So it lives in this database and never in a per-repo `credentials` table.
  - Admin is accepted only by the bootstrap, presenter-enrollment, and presenter-recovery endpoints, and by `BeginApproval` for the approvals of `kk init` and first run. No thread or registration credential exists yet at that point. It is also accepted by the diagnose call and the `BeginApproval` of the user-scoped `replace-terminal-server` plan, which work from any directory.
  - Operational calls cannot substitute Admin for [human approval](../appendix-a-glossary.md#human-approval).

- **`approval_presenters`**: enrollments of foreground channels. A presenter (an [`ApprovalPresenter`](../appendix-a-glossary.md#approvalpresenter)) is an interactive CLI or TUI through which a human confirms an action.
  - Columns: `(presenter_id, frontend_kind, credential_hash, channel_binding, enrolled_at, last_seen_at, revoked_at?)`.
  - Enrollment requires the [bootstrap Admin credential](../appendix-a-glossary.md#bootstrap-admin-credential). Enrollment is not approval for an operation.
  - A presenter proves that a confirmation came from a registered interactive CLI or TUI channel.
  - A presenter cannot mint a [capability](https://en.wikipedia.org/wiki/Capability-based_security) without completing a persisted challenge.

- **`user_approval_challenges` and `user_human_approvals`**: approval records for operations that have no repository target.
  - The approvals for `kk init` and first run are stored here. Their requester is the user's Admin bootstrap credential, because the repo has no registration credential yet.
  - They are the same two-phase challenge and one-use-capability records described below for `approval_challenges` and `human_approvals`.
  - Repository-scoped confirmations are stored only in the target repository database.

- **`user_approved_operations` and `user_approved_operation_steps`**: durable records of approved operations whose authority must survive without a repo database.
  - They are durable claim envelopes and [idempotent](https://en.wikipedia.org/wiki/Idempotence) step journals. An idempotent step is safe to run again.
  - They cover registration, unregister, and `replace-terminal-server`, among others.
  - Their shape matches the per-repo tables below.
  - Unregister completes its user-level journal only after the target repo state is deleted.

- **`user_audit_log`**: an append-only log of attempts that have no valid repository target.
  - These attempts include bootstrap, `ListRepos`, registration, malformed repo selectors, and authorization failures that happen before a repo can be resolved.
  - Its row shape matches per-repo `audit_log`.
  - It permits null credential, approval, and presenter identities.

### Per-repo (`~/.config/kiki/repos/<repo_id>/state.db`)

#### Threads, checkpoints, and lifecycle

- **`threads`**: one row per [thread](../appendix-a-glossary.md#thread). It carries the thread's stable identity and the facts kiki tracks about it.
  - The row carries:
    - the stable identity;
    - references to the thread's [projections](../appendix-a-glossary.md#projection): the [bookmark](../appendix-a-glossary.md#bookmark) name, the [workspace](../appendix-a-glossary.md#workspace), the current [terminal binding](../appendix-a-glossary.md#terminal-binding), and the [harness](../appendix-a-glossary.md#harness);
    - `thread_head_commit_id`;
    - the checkpoint fields `checkpoint_commit_id`, `checkpoint_change_id`, `checkpoint_op_id`, `bookmark_expected_commit_id`, and `bookmark_expected_op_id`;
    - `owned_stack_base_commit_id`;
    - a `lifecycle` column with values `Creating | Active | CreateFailed | ClosePreflight | CloseCommit | CloseFailed | Closed | ProjectionDiverged | DestroyCommit | DestroyFailed | Destroyed` (see [Threads](../03-threads.md) and [thread lifecycle states](../appendix-a-glossary.md#thread-lifecycle-states)).
  - `projection_resume_lifecycle` is null except in `ProjectionDiverged`. There, it records whether a successful repair must restore the `Active` invariants or the `Closed` invariants.
  - **Live head.** For an active coherent thread, the managed workspace's exact [`@`](https://docs.jj-vcs.dev/latest/glossary/) (jj's name for the working-copy commit) is the [live head](../appendix-a-glossary.md#live-head). `thread_head_commit_id` is the last exact value kiki observed for it.
  - **Latest placement.** `checkpoint_commit_id`, with `checkpoint_change_id` and `checkpoint_op_id`, records the latest explicit [placement](../appendix-a-glossary.md#checkpoint-placement). That is the exact commit, change, and [operation](https://docs.jj-vcs.dev/latest/operation-log/) where kiki last put the bookmark.
    - It changes only when a journaled checkpoint places the bookmark.
    - The placed commit follows the [checkpoint target](../appendix-a-glossary.md#checkpoint-target) rule, stated in [Op-log watcher](op-log-watcher.md#checkpoint-target-and-relationship). The target is the live head. When the head is empty and undescribed, kiki walks back along the owned chain to the nearest commit that is not both empty and undescribed. If the walk reaches the expected target first, the bookmark stays where it is. If the walk leaves the owned chain without finding either, the checkpoint refuses with "nothing to checkpoint". Creation is the one exception: it places the bookmark on the new thread's first, empty commit.
    - The owned chain starts just after the thread's base. The base is not on it.
  - **Expected target.** `bookmark_expected_commit_id` is the [expected bookmark target](../appendix-a-glossary.md#expected-bookmark-target). The projection audit, publish, and reopen all use it. `bookmark_expected_op_id` is the operation that established it.
    - It starts equal to the placement.
    - Afterwards it changes only through a recorded succession.
    - It never changes because `@` moved.
  - **Checkpoint relationship.** The [checkpoint relationship](../appendix-a-glossary.md#checkpoint-relationship) `current | behind | ahead | diverged` is not stored. kiki derives it from the expected target and the live head, on the owned chain:
    - `current` when the expected target equals the head, or equals the commit the checkpoint target rule picks;
    - `behind` when the head is any other descendant of the expected target;
    - `ahead` when the head is an ancestor of the expected target;
    - `diverged` otherwise.
    - `ahead` and `diverged` are not issues. Publish, close, and detach stay blocked for them until `choose-bookmark-target` is applied.
  - **Bookmark name.** The bookmark name is a projection reference, not identity.
    - A proven external rename replaces it in place, under the rename rule in [Op-log watcher](op-log-watcher.md#the-classifier).
    - Each such change is appended to `thread_bookmark_renames`.
  - **Terminal binding reference.** The current terminal binding reference names at most one non-`Ended` `terminal_bindings` row. A Herdr ref, label, or path stored anywhere else is a locator or a hint. It is never the binding.
  - **[Owned-stack base](../appendix-a-glossary.md#owned-stack-base).** `owned_stack_base_commit_id` survives the deletion of a [follows](../appendix-a-glossary.md#follows) edge. It advances only with a completed reconciliation. So detach, and later destroy validation, keep an exact structural base for the [owned stack](../appendix-a-glossary.md#owned-stack).
  - Cascade progress is not projected onto this row. It is derived from `sync_intents`.

- **`thread_links`**: the directed [follows](../appendix-a-glossary.md#follows) edges between threads.
  - Edges are DAG-validated at insert time. (A [DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph) is a graph with no cycles, so no thread can end up following itself.)
  - Each edge includes `last_synchronized_parent_commit_id`.
  - The initial parent anchor comes from the parent's exact live head in a pinned, revalidated operation view (a [pinned read](../appendix-a-glossary.md#pinned-read)). It never comes from the parent's bookmark or from a stale cache.
  - Immediately before an explicit rebase, kiki checks the child's commits. Every commit after the thread's exact owned-stack base, through its exact live head, must form one strict single-parent chain. Every one of those commits must be owned by that child.
  - Merge commits, multiple roots, [conflicts](https://docs.jj-vcs.dev/latest/conflicts/), or foreign commits produce [`TopologyDiverged`](../appendix-a-glossary.md#topologydiverged).
  - kiki never infers a broader source [revset](https://docs.jj-vcs.dev/latest/revsets/) (a jj expression that selects commits). It never trusts a remembered “root” identity in place of validating the path.

- **`thread_checkpoints`**: the append-only history of [checkpoint placements](../appendix-a-glossary.md#checkpoint-placement). Each row is one time kiki explicitly put a thread's bookmark on a commit.
  - Columns: `(checkpoint_id, thread_id, seq, lifecycle_op_id, reason: Creation | Publish | Close | Detach | RepairRestore | RepairAdopt | RepairChoose | RepairUnhide | Reanchor, placed_change_id, placed_commit_id, placed_op_id, placed_at)` with `UNIQUE (thread_id, seq)`.
  - Every explicit placement appends one row. The explicit placements are creation, publish, close, detach, and every applied bookmark [repair plan](../appendix-a-glossary.md#repair-plan).
  - The row is appended in the transaction that verifies the bookmark's resulting target and operation.
  - **Checkpoints only move forward.** A checkpoint placement (`Creation | Publish | Close | Detach`) only moves the bookmark forward along the owned chain. It is refused unless the placed commit equals or descends from the expected target. It never passes `--allow-backwards`.
  - **Repair placements.** Each applied bookmark plan writes its own `reason` with that plan's `lifecycle_op_id`:

    | `reason`        | Plan                                                                          | Placed commit                                       | Approval                                                                      |
    | --------------- | ----------------------------------------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------- |
    | `RepairRestore` | [`restore-bookmark`](../appendix-a-glossary.md#restore-bookmark)              | the expected target (`bookmark_expected_commit_id`) | none in the thread's own context; one-shot when applied to a different thread |
    | `RepairAdopt`   | [`adopt-bookmark`](../appendix-a-glossary.md#adopt-bookmark)                  | the single observed target                          | one-shot                                                                      |
    | `RepairChoose`  | [`choose-bookmark-target`](../appendix-a-glossary.md#choose-bookmark-target)  | the live head or an on-chain commit the human picks | one-shot                                                                      |
    | `RepairUnhide`  | [`unhide-checkpoint`](../appendix-a-glossary.md#unhide-checkpoint)            | the expected target, made visible again             | one-shot                                                                      |
    | `Reanchor`      | [`reanchor-history`](../appendix-a-glossary.md#reanchor-history) (repo level) | the observed commit, where the bookmark already is  | one-shot, repo scope                                                          |

  - `RepairRestore` never places the bookmark at an older placed commit. jj may see the restore as a backward move, so the plan may pass `--allow-backwards`.
  - `RepairAdopt` and `RepairChoose` may place the bookmark on the live head or on any commit on the validated owned chain. That includes a commit behind the expected target, so these plans may pass `--allow-backwards`. `RepairUnhide` may pass it too.
  - No placement of any reason puts the bookmark on a commit that is off the owned chain. v1 has no plan for that. The human first fixes the shape with jj and then adopts or chooses.
  - `RepairRestore` is refused while the expected target is [hidden](https://docs.jj-vcs.dev/latest/glossary/) (no longer visible in jj). `RepairUnhide` is exempt from that refusal, because making the target visible again is its job. It is offered only when unhiding would not create a divergent change.
  - `Reanchor` has no exemption. It is written only for a bookmark that is present, not conflicted, and on the live head or the owned chain. It records the bookmark where it already is, against the current operation, and moves nothing.
  - Placements are scoped by operation ancestry, exactly like successions. A placement applies to an operation view only when `placed_op_id` is that view's operation or an ancestor of it. The reason: a pinned placement can land beside a concurrent operation.
  - Rows are never updated or deleted while the thread exists. A later rewrite of the placed commit does not change them.

- **`thread_checkpoint_successions`**: the append-only record of [native successors](../appendix-a-glossary.md#native-successor). Each row says that jj itself moved the bookmark after a placement.
  - Columns: `(checkpoint_id, seq, kind: SameChange | PredecessorOtherChange | Reverted, from_commit_id, to_commit_id, to_change_id, op_id, evidence_op_id?, evidence_commit_id?, reverted_to_checkpoint_id?, reverted_to_seq?, observed_at)` with `UNIQUE (checkpoint_id, seq)` and `UNIQUE (checkpoint_id, op_id)`.
  - A row records that jj itself carried the bookmark from `from_commit_id` to `to_commit_id` in operation `op_id`. The classifier in [Op-log watcher](op-log-watcher.md#checkpoint-tracking) decides this.
  - `SameChange` and `PredecessorOtherChange` are proved by an operation [predecessor](https://docs.jj-vcs.dev/latest/glossary/) record.
    - `evidence_op_id` names the operation whose record was used, when that operation is not `op_id`.
    - `evidence_commit_id` names the commit that recorded the predecessor, when that commit is not `to_commit_id`. This happens for a squash into a commit other than the parent.
  - `PredecessorOtherChange` is accepted only when `to_commit_id` is the live head or lies on the owned chain. The base is not on that chain. A successor that lands on the base, on a parent thread's commit, or on trunk is `BookmarkMoved`, and no row is written.
  - `Reverted` records an undo. Kiki accepts one on two pieces of evidence at the observed operation: (a) the bookmark is exactly on a commit that an earlier placement or succession row recorded as this thread's expected target, and (b) no successor recorded after that row is still visible. This holds whoever made the move. A real `jj undo` or `jj op restore` hides the later successors. A move back to an earlier recorded target while a later recorded successor is still visible is `BookmarkMoved`. This rule needs a proof test on the pinned jj version.
    - The undo rule covers the thread's whole placement and succession history, not only the current placement. So `to_commit_id` may be the placed commit of any earlier `thread_checkpoints` row of the thread, or the `to_commit_id` of any earlier succession row.
    - `reverted_to_checkpoint_id` and `reverted_to_seq` name that earlier row. `reverted_to_seq` is empty when the row is a placement.
    - Every placement and succession row recorded after the named row is thereby marked reverted for views that descend from `op_id`. Those rows are not edited or deleted.
    - This includes a human `jj undo` of kiki's own placement operation.
    - It needs no predecessor record.
  - Rows are written for kiki's own operations as well as external ones.
  - Rows attach to the placement they succeed. A `Reverted` row attaches to the latest placement that applies to its operation.
  - The expected target in any operation view is the latest placement that applies to that view, updated by that placement's rows whose `op_id` is an ancestor of that view. When the latest such row is `Reverted`, the expected target is the commit of the earlier row it names.
  - `threads.bookmark_expected_commit_id` caches that value for the agreed frontier.

- **`thread_bookmark_renames`**: the append-only journal of bookmark renames that kiki adopted. Adopting a proven rename is a normalization: it brings kiki's record back in line without changing identity.
  - Columns: `(rename_id, thread_id, from_name, to_name, op_id, target_commit_id, observed_at)` with `UNIQUE (thread_id, op_id)`.
  - A row records all of these facts:
    - one exact operation removed the thread's bookmark name;
    - that operation created exactly one new local name. The new name is on the expected target, or on a successor of it that classifier rule 5 accepts in the same operation;
    - that operation changed no remote or `@git` bookmark, and was not an import or fetch;
    - kiki adopted the new name.
  - The row is written in the transaction that updates the thread row's bookmark name.
  - By itself, it appends no placement and no succession. A succession row is appended only when the target also moved to a proven successor in that operation.

- **`thread_lifecycle_ops`**: the durable [sagas](../appendix-a-glossary.md#saga) for creation, close, reopen, checkpoint, repair, terminal restart, and later destroy. A saga is a multi-step operation that kiki can retry or undo step by step. Together with `thread_lifecycle_steps`, this is the [lifecycle journal](../appendix-a-glossary.md#lifecycle-journal).
  - Columns: `(lifecycle_op_id, thread_id, kind, state, started_at, updated_at, completed_at?, last_error?, context_json)`.
  - `kind` includes `RestartTerminal`. The [`restart-terminal`](../appendix-a-glossary.md#restart-terminal) plan is a journaled lifecycle operation with its own step list (see `thread_lifecycle_steps`).
  - A lifecycle operation holds the thread's [lifecycle lock](../appendix-a-glossary.md#lifecycle-lock) from start to finish. The lifecycle lock is the thread's [reconciliation lock](../appendix-a-glossary.md#reconciliation-lock) held for the length of the operation. [Invariants](../02-invariants.md) defines it.
  - `context_json` contains the pinned ids and [fingerprints](https://en.wikipedia.org/wiki/Cryptographic_hash_function) needed to retry. It is not a substitute for normalized thread or step state.
  - Some plans delete a workspace: close, destroy, [`close-without-terminal`](../appendix-a-glossary.md#close-without-terminal), [`cleanup-failed-create`](../appendix-a-glossary.md#cleanup-failed-create), and [`cleanup-failed-reopen`](../appendix-a-glossary.md#cleanup-failed-reopen). For those plans, `context_json` also holds:
    - the approved plan's accepted workspace-holder identities (see [accepted holder](../appendix-a-glossary.md#accepted-holder)), each an exact `(pid, start_time)` with its command line;
    - the [remnant](../appendix-a-glossary.md#remnant-container) or [unbound](../appendix-a-glossary.md#unbound-container) terminal containers the plan lists, with their processes.
  - `restart-terminal` deletes no workspace, but it disposes of containers. Its `context_json` holds the same list of remnant and unbound containers with their processes.
  - An unbound container is a terminal container on the current server instance with no current binding. That includes a group whose binding ended because its `agent` launcher died while the group itself survived.
  - `restart-terminal` and `close-without-terminal` both require that no recorded process survives outside the listed containers.
  - **The frozen record.** For every operation that freezes processes, `context_json` also holds the set of roles that had already ended before the freeze. Together with the frozen `process_records` rows, this is the frozen record. [Verified resume](../appendix-a-glossary.md#verified-resume) proves every role that was live at freeze time. A role in the ended set, such as a `shell` pane the user closed earlier, does not fail the resume.
  - A [holder](../appendix-a-glossary.md#holder) outside the listed containers that the plan does not name is drift.

- **`thread_lifecycle_steps`**: the step-by-step journal of each lifecycle operation. kiki appends and updates rows here.
  - It is keyed by `(lifecycle_op_id, ordinal)`.
  - Columns: `(name, state: Pending | Started | Completed | Compensating | Compensated | Failed, attempt, started_at?, completed_at?, input_fingerprint?, result_json?, error?)`.
  - A step is marked `Started` before its external side effect. It records the stable external identity that kiki needs to detect work that already completed.
  - Creation and reopen compensation run completed steps in reverse order. (Compensation means undoing a step.)
  - **Close** records these steps, in this order and separately. Preflight inventory and the plan come first, and the approval claims `CloseCommit`. Then:
    1. freeze;
    2. [post-freeze recheck](../appendix-a-glossary.md#post-freeze-recheck);
    3. holder scan;
    4. checkpoint;
    5. each child step (a reconcile, checkpoint, or detach);
    6. [final proof](../appendix-a-glossary.md#final-proof);
    7. kiki-side termination of the [frozen set](../appendix-a-glossary.md#frozen-set) with [verified exit](../appendix-a-glossary.md#verified-exit);
    8. the terminal-container close request;
    9. [post-exit filesystem recheck](../appendix-a-glossary.md#post-exit-filesystem-recheck);
    10. workspace forget;
    11. directory delete.
  - **This one list also covers [`close-without-terminal`](../appendix-a-glossary.md#close-without-terminal).** That plan uses the same steps in the same order, preceded by its own preflight inventory and approval. The only difference is what is frozen and closed: the processes in the listed remnant and unbound containers, and those containers, in place of the thread's bound terminal group. Nothing is terminated before the final proof.
  - Rules for the close steps:
    - **The freeze is write-ahead.** kiki commits each discovered identity to `process_records`, with its prior stop state and this operation's id, before it [signals](<https://en.wikipedia.org/wiki/Signal_(IPC)>) the process. So a crash in the middle of a freeze is recovered from those rows by [verified resume](../appendix-a-glossary.md#verified-resume).
    - **The post-freeze recheck** runs immediately after the freeze and before the checkpoint. It binds to the approved fingerprint. It shows that no frozen member holds an open [descriptor](https://en.wikipedia.org/wiki/File_descriptor) under the repository's `.jj` directory.
    - **The holder scan** looks for workspace holders outside the frozen set. A holder the approved plan does not name is drift.
    - **The final proof** runs after the checkpoint and all child work. It asserts again that every member is stopped. It checks that each listed container still holds the recorded launcher, if it had one, and exactly the processes recorded at freeze. It repeats the checks of holders, the container set, the filesystem generation, and the fingerprint. It journals the generation and fingerprint it saw. It is the recovery boundary.
    - **Termination.** kiki then terminates the frozen set itself. It does this while the set is still stopped, and before it asks the runtime to close anything. For each identity, kiki confirms the process is still stopped and is still the recorded `(pid, start_time)`, kills it, and verifies that it is gone within `[timeouts] verified_exit`.
    - **The terminal-container close request** is cleanup only. Its reply is not evidence.
    - **The post-exit filesystem recheck** requires the generation and fingerprint to equal the final proof's journaled values. kiki re-reads it after any `kkd` crash, because the watch does not survive a crash. Any mismatch is `CloseFailed`, with files preserved.
    - Every step taken while frozen has a deadline, `[timeouts] frozen_step`. When it expires before termination begins, kiki takes verified resume. Once termination has begun, a failure is `CloseFailed`, never resume.
    - A failure before the final proof takes verified resume of the frozen processes.
    - Child work completes while the parent remains frozen.
    - If a `close-without-terminal` plan aborts before its irreversible step, kiki takes verified resume of the frozen processes and `CloseCommit` returns to `ProjectionDiverged`.
  - **`RestartTerminal`** records these steps, in this order and separately. [Terminal runtime](terminal-runtime.md#restarting-the-terminal) owns the list:
    1. preflight inventory and plan, which lists the remnant and unbound containers and their processes;
    2. the approval claim;
    3. freeze of the processes in the listed containers;
    4. proof that each listed container holds exactly the processes recorded at freeze, then termination with verified exit and each container's close request;
    5. the holder scan and the orphan scan, run again;
    6. provisioning of a fresh terminal group, with a fresh credential, launch settings, gate, and ready handshake.
  - Rules for the restart steps:
    - If the freeze returns `Unknown`, kiki takes verified resume and the plan stops.
    - If the restart fails after provisioning, `TerminalMissing` stays open and the thread stays `ProjectionDiverged`.
    - The half-made group is then removed by [`cleanup-failed-restart`](../appendix-a-glossary.md#cleanup-failed-restart), under the same limits as `cleanup-failed-create`. It never removes the jj workspace.
    - `TerminalMissing` is resolved only by the ready-handshake transaction of the new group.
  - **Destroy** records these steps, in this order and separately:
    1. freeze;
    2. post-freeze recheck;
    3. holder scan;
    4. final proof;
    5. termination of the frozen set with verified exit;
    6. the terminal-group close request;
    7. post-exit filesystem recheck;
    8. bookmark deletion;
    9. optional exact revision abandonment;
    10. workspace forget and directory delete;
    11. credential revocation;
    12. tombstoning.
  - Rules for the destroy steps:
    - Drift before termination takes verified resume.
    - Process termination is destroy's first irreversible step.
    - After it, only two things apply: `DestroyFailed`, or finishing the plan. So a failure after an irreversible step cannot masquerade as an intact lifecycle.

- **`thread_projection_issues`**: the repair ledger for one thread. Each row is one observed [projection divergence](../appendix-a-glossary.md#projection-divergence): a mismatch between kiki's record and the outside world.
  - Columns: `(issue_id, thread_id, kind, expected_json, observed_json, detected_at, notified_at?, resolved_at?, resolution?)`.
  - Kinds include `WorkspaceDirectoryMissing | WorkspaceRecordMissing | WorkspacePathMismatch | BookmarkMissing | BookmarkMoved | BookmarkConflicted | CheckpointAbandoned | TerminalMissing | OrphanedProcess`.
  - **Bookmark issues.**
    - `expected_json` carries the expected target with its placement and latest succession.
    - `observed_json` carries the observed target set, the conflict flag, the exact operation, whether the expected target is hidden, and whatever predecessor evidence exists.
    - `CheckpointAbandoned` means: the bookmark is absent, the expected target is hidden at the observed operation, and no visible successor is accepted by classifier rule 5. A bookmark that is present on a commit kiki does not accept is `BookmarkMoved`, even when the expected target is hidden; `choose-bookmark-target` is its exit. `CheckpointAbandoned`'s plans are `choose-bookmark-target` and, when unhiding would not create a divergent change, `unhide-checkpoint`.
    - Sometimes the expected target becomes hidden while another bookmark issue is already open and tracking is paused. Then the open row stays as it is, and `observed_json` notes that the target is now hidden. No second row is added. `restore-bookmark` is withdrawn, and `choose-bookmark-target` is the exit.
    - A **closed** thread with `CheckpointAbandoned` is common after a squash-merged pull request and a fetch. The thread stays `Closed`; it does not move to `ProjectionDiverged`. The issue is reported on `kk ls --all` and `kk repair`. It is not a loud attention event. It blocks only `kk reopen`. It has three exits: `unhide-checkpoint` followed by reopen; `choose-bookmark-target` onto a visible commit of the thread's archived owned chain, followed by reopen; or destroy when destroy ships.
    - A bookmark issue is resolved without a plan when a later operation shows the bookmark unconflicted on the expected target. `resolution` then records that operation.
  - **[`TerminalMissing`](../appendix-a-glossary.md#terminalmissing)** records the ended binding and the observed cause.
  - **[`OrphanedProcess`](../appendix-a-glossary.md#orphanedprocess)** records one of two things (see [orphan](../appendix-a-glossary.md#orphan)):
    - a survivor: a recorded process identity that is alive with no current binding and is not a member of a container on the current server instance; or
    - a [harness remnant](../appendix-a-glossary.md#harness-remnant): any descendant of a live `agent` launcher, other than the launcher, while no incarnation is live. A remnant need not have been recorded before.
  - A member process of an [unbound container](../appendix-a-glossary.md#unbound-container) is a terminal member, not an orphan.
  - The plan that resolves `OrphanedProcess` is [`terminate-orphans`](../appendix-a-glossary.md#terminate-orphans), with a one-shot approval.
  - An unrecorded same-UID workspace holder is not an `OrphanedProcess`. It is not stored as an issue. (Same-UID means it runs as the same operating-system user.)
  - An unresolved issue places an otherwise coherent active or closed thread in `ProjectionDiverged`. There are two exceptions. One is a temporary mismatch owned by an in-progress lifecycle journal. The other is a `Closed` thread with `CheckpointAbandoned`: it stays `Closed`, and the issue blocks only `kk reopen`.
  - **What an issue blocks** is derived from `kind`:
    - Bookmark-only issues (`BookmarkMissing`, [`BookmarkMoved`](../appendix-a-glossary.md#bookmarkmoved), [`BookmarkConflicted`](../appendix-a-glossary.md#bookmarkconflicted)) and `CheckpointAbandoned` block checkpoint, publish, close, and detach. They also pause native successor tracking for that thread. For a closed thread, `CheckpointAbandoned` blocks only `kk reopen`. They do not block unambiguous workspace-head observation or follows classification.
    - `TerminalMissing` permits head observation. It blocks boundary delivery, workspace [materialization](../appendix-a-glossary.md#materialization), and lifecycle mutation other than an approved `restart-terminal`, `cleanup-failed-restart`, `close-without-terminal`, or destroy plan.
    - `OrphanedProcess` permits head observation. It blocks exactly replacement, materialization, and deletion. "Replacement" covers two things: provisioning a replacement terminal group, and opening a replacement [incarnation](../appendix-a-glossary.md#incarnation)'s [launch gate](../appendix-a-glossary.md#launch-gate). So in schema terms it blocks those two, workspace materialization, and workspace forget or deletion.
    - Workspace identity or path ambiguity blocks both.
  - **What may resolve automatically.**
    - Only identity-preserving, unique normalization may resolve automatically.
    - A proven bookmark rename is such a normalization and raises no issue.
    - Restore, adopt, choose, unhide, recreate, reattach, repoint, restart, and terminate choices require a recorded `kk repair` resolution.
    - A recorded native succession is not a resolution and raises no issue.

- **`repo_issues`**: the repair ledger for the whole repo.
  - Columns: `(issue_id, kind: OperationHistoryRewritten, expected_json, observed_json, detected_at, notified_at?, resolved_at?, resolution?)`.
  - [`OperationHistoryRewritten`](../appendix-a-glossary.md#operationhistoryrewritten) is raised once per repo when both of these hold:
    - operation history was rewritten: a recorded operation that was an ancestor of the last recorded frontier is no longer reachable from the current frontier (jj's constant root operation is never counted); and
    - at least one thread's observed bookmark or workspace `@` differs from its cached value.
  - The check is made for each recorded operation, not only for the heads. So it catches an ordinary `jj op abandon` in the middle of the log, which keeps the older operation ids and changes the newer ones. `jj op abandon`, and anything else that rewrites the head's ancestry, is the cause. `jj util gc` is not: it only removes operations that are already unreachable.
  - `observed_json` lists those threads, each with its observed bookmark state.
  - It replaces per-thread bookmark issues for that gap until the plan is approved.
  - While it is unresolved, checkpoint, publish, close, detach, and explicit rebase are blocked for the listed threads.
  - The exit is the repo-level [`reanchor-history`](../appendix-a-glossary.md#reanchor-history) plan (`kk repair --repo`), with a one-shot approval of repo scope. It works per thread. On approval, for each listed thread:
    - if the bookmark is present, not conflicted, and on the live head or the owned chain, kiki appends a `thread_checkpoints` row with `reason = Reanchor` at the observed commit, against the current operation;
    - for every other listed thread, kiki raises the matching `thread_projection_issues` row at the new anchor (`BookmarkMissing`, `BookmarkConflicted`, or `BookmarkMoved`), and the ordinary plans fix it.

#### Terminals and processes

- **`terminal_bindings`**: one row per provisioned [terminal group](../appendix-a-glossary.md#terminal-group) for one thread on one [server instance](../appendix-a-glossary.md#server-instance). This is the [terminal binding](../appendix-a-glossary.md#terminal-binding).
  - Columns: `(terminal_binding_id, thread_id, server_instance_id, provision_id UNIQUE, provision_nonce_hash, lifecycle_op_id, group_ref, state: Provisioning | Bound | Ended, ended_reason?, created_at, ended_at?)`.
  - **`provision_id`.** kiki persists `provision_id` before it asks the runtime to create anything. A [pane launcher](../appendix-a-glossary.md#pane-launcher)'s report names it. So a lost reply or a duplicate group resolves to one accepted binding.
  - **The provision nonce.** `provision_nonce_hash` is the [hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function) of the [provision nonce](../appendix-a-glossary.md#provision-nonce) (a secret random value; see [nonce](https://en.wikipedia.org/wiki/Cryptographic_nonce)).
    - There is one nonce per provision.
    - It reaches each role launcher through its launch environment ([environment variables](https://en.wikipedia.org/wiki/Environment_variable)). It never travels through argv (the command-line arguments), because the runtime saves launch argv.
    - argv carries only `provision_id` and the role.
    - The nonce itself is never stored.
    - Before any re-issued create call for the same provision, kiki rotates the nonce and replaces the hash. So a launcher from the earlier call cannot claim.
  - **Launcher reports.**
    - A launcher report authenticates with the [thread-scoped credential](../appendix-a-glossary.md#threadscoped-credential) plus that nonce.
    - `kkd` reads the launcher's process identity from the OS through the socket's [peer credentials](https://man7.org/linux/man-pages/man7/unix.7.html). It does not trust a reported identity.
    - `group_ref` is the Herdr workspace ref. It is meaningful only together with `server_instance_id`.
    - The first accepted launcher fixes `group_ref`. A launcher that reports the same `provision_id` from another Herdr workspace is refused.
    - A report is accepted only when both of these hold: the caller's OS identity has the current server instance's process as its parent; and a fresh per-pane process query shows the reported pane's root process is that caller.
  - **Reports and gates are separate transactions.**
    - Each launcher report is handled in one transaction, when it arrives. There is no table of pending reports.
    - That transaction accepts exactly one launcher for `(provision_id, role)` and records its OS-read process identity. The key is always `(provision_id, role)`.
    - The binding becomes `Bound` in the transaction that accepts the `agent` claim. `agent` is the only [required role](../appendix-a-glossary.md#required-role).
    - A `shell` or `ui` launcher that does not report within `[timeouts] launcher_report` is recorded as absent on the provisioning step's `result_json`. That raises a warning. It does not fail provisioning, and it writes no `terminal_panes` row.
    - A separate, later transaction records a new incarnation and activates its launch gate. It requires a `Bound` binding.
  - **Reports are [idempotent](https://en.wikipedia.org/wiki/Idempotence).**
    - A repeat of an accepted report from the same peer process identity `(pid, start_time)` gets the same answer again. It changes nothing.
    - A different process that presents for a consumed role is refused and must exit.
  - A binding is `Ended` when it is closed, when it is replaced, when its server instance ends, or when its `agent` launcher dies. An ended binding is never revived.

- **`terminal_panes`**: the [role panes](../appendix-a-glossary.md#role-pane) of a binding. A role pane is a pane kiki created for a declared job.
  - Columns: `(terminal_binding_id, role: agent | shell | ui, tab_ref, pane_ref, terminal_ref?, launcher_pid, launcher_start_time, nonce_consumed_at, claimed_at, ended_at?)`.
  - A row exists only because a pane launcher claimed `(provision_id, role)` through the gate. Pane position, label, and title never assign a role.
  - `nonce_consumed_at` records that this role's claim consumed the provision nonce. The nonce admits one claim per `(provision_id, role)`. A second presentation for a consumed role from a different process is refused, and that process must exit. A repeat from the accepted process identity gets the same answer again and writes nothing.
  - `agent` is the only [required role](../appendix-a-glossary.md#required-role). A binding may have no `shell` or `ui` row: that role's launcher did not report in time and was recorded as absent.
  - `launcher_pid` and `launcher_start_time` are the claiming process identity, as read from peer credentials. The role is bound to that identity.
    - The role survives a `shell` or `ui` launcher replacing itself with the shell or UI program, because replacement keeps `(pid, start_time)`.
    - The role ends when that process identity ends. `kkd` observes that end from the OS; it is not reported.
    - The launcher identity is a different fact from the harness process identity on `agent_sessions`. The `agent` launcher stays alive as the harness's parent, so both identities are live at once.
  - `terminal_ref` holds Herdr's `terminal_id`. It is a change hint only.
  - `user` is not a role; it is the absence of one. So [`user` panes](../appendix-a-glossary.md#user-pane) are observed in runtime snapshots and never stored here.

- **`process_records`**: the OS process identities kiki recorded for a thread.
  - Columns: `(record_id, thread_id, terminal_binding_id?, agent_session_id?, pid, start_time, os_session_id, process_group_id, source: Launcher | Harness | HarnessTree | FreezeDiscovery, recorded_at, prior_stop_state?, freeze_lifecycle_op_id?, exit_verified_at?)`.
  - These are the identities the [orphan](../appendix-a-glossary.md#orphan) scan looks for, and the identities [verified exit](../appendix-a-glossary.md#verified-exit) checks.
  - A process is the recorded one only when both `pid` and `start_time` match.
  - `HarnessTree` rows are the harness's descendants. kiki records them when it terminates or [hard-pauses](../appendix-a-glossary.md#hard-pause) a harness. This covers the harness's whole process tree.
  - `FreezeDiscovery` rows are processes found by freeze discovery. A lifecycle freeze writes them. So does the [`terminate-orphans`](../appendix-a-glossary.md#terminate-orphans) plan: for a harness remnant it runs freeze discovery rooted at the `agent` launcher, and it records what it finds as `FreezeDiscovery` rows under its approval. A remnant need not have been recorded before that. For a survivor, the plan uses the identities already recorded here. Either way it terminates them with verified exit.
  - `prior_stop_state` and `freeze_lifecycle_op_id` are set for members of a frozen set. The row is committed before the process is signalled. So the frozen set can be rebuilt from rows, and [verified resume](../appendix-a-glossary.md#verified-resume) restores exactly the prior states.
  - `exit_verified_at` is written only by `ProcessSupervisor`, after it observed that exact identity gone. A runtime reply never sets it.
  - kiki signals only identities present in this table. It terminates one only after the process is stopped and its identity has been re-read. This is why `terminate-orphans` records a remnant before it signals it.

- **`agent_sessions`**: one row per runtime process [incarnation](../appendix-a-glossary.md#runtime-agent-incarnation). An incarnation is one run of a harness process that kiki manages.
  - Columns: `(agent_session_id, thread_id, harness_session_id, terminal_binding_id, launcher_pid, launcher_start_time, harness_pid?, harness_start_time?, started_at, retired_at?, launch_gate_id?, gate_activated_at?, harness_started_at?, pause_state: None | Stopping | Stopped | Killed, ready_fingerprint?, exclusive_hook_fingerprint?, exclusive_hook_proven_at?, delivered_intent_id?, startup_intent_id?, startup_intent_epoch?, startup_delivery_id?, startup_payload_sha256?, startup_proven_at?)`.
  - **Identity of an incarnation.**
    - `agent_session_id` changes on every process start, even when `--resume` reuses `harness_session_id`.
    - Every incarnation must independently prove exclusive hook control before it is ready or may mutate a managed workspace.
    - The incarnation belongs to the `agent` role pane of `terminal_binding_id`.
  - **Launcher and harness identities.**
    - The launcher identity is copied from the binding's live `agent` row in `terminal_panes`.
    - The harness identity is recorded by `ReportHarnessStarted`, in these steps:
      1. The launcher creates the harness child, held before it runs.
      2. The launcher reports the child's pid.
      3. `kkd` verifies from the OS that the process is that launcher's child, and records `(harness_pid, harness_start_time)`.
      4. Only then does the launcher release the child.
    - `ReportHarnessStarted` is idempotent. A repeat from the same launcher for the same incarnation and the same child identity is accepted as a no-op. A launcher that already holds a recorded child ignores a re-delivered gate specification and reports the existing child.
    - The harness identity is therefore recorded before the harness runs. The [ready handshake](../appendix-a-glossary.md#ready-handshake) records readiness, not the pid.
    - `kkd` resolves the [launch specification](../appendix-a-glossary.md#launch-specification) through the harness adapter. The pane launcher only executes it.
  - **Hard-pause.** A hard-pause retires the incarnation by terminating the harness process tree through `ProcessSupervisor`. It leaves the launcher alive.
    - A hard pause is journaled in `pause_state`. `kkd` writes each value before it takes the matching step: `Stopping` before it signals anything, `Stopped` once the whole recorded tree is stopped and re-verified, and `Killed` once every recorded identity is verified gone. `None` means no hard pause has begun.
    - Recovery after a `kkd` crash rolls a hard pause forward to the kill. It never resumes a harness that was being retired.
  - **The launcher outlives incarnations.**
    - The `agent` launcher outlives incarnations.
    - Each incarnation has its own one-use `launch_gate_id`. The same accepted launcher awaits successive gates. "One-use" describes a gate, not the launcher.
    - When the harness exits, the launcher reports the child's exit status and awaits the next gate.
    - The incarnation is then retired without acknowledgement. The `agent` role and the binding stay live. The thread's lifecycle is unchanged.
  - **Replacement incarnations.**
    - A replacement incarnation is a new row and a new gate on that launcher. It involves no terminal provisioning.
    - Its gate is activated only after an inventory rooted at the `agent` launcher shows no process other than the launcher itself.
    - A survivor is an `OrphanedProcess` harness remnant and blocks the gate until `terminate-orphans` resolves it.
  - **Credential file.** The thread credential's file path is stable. Its contents are replaced atomically when an incarnation ends, and at reopen or terminal restart. The launcher re-reads it after reporting the harness exit.
  - **Creation.**
    - During creation, a launcher blocks on `launch_gate_id`.
    - Activation authorizes the harness start but leaves the thread `Creating`.
    - A validated ready handshake records the harness and hook fingerprints. Only that transaction completes the saga and enters `Active`.
  - **Delivery pointers.** Delivery pointers name a synthetic result awaiting acknowledgement. It waits in one of two ways: through a soft batch barrier, or as the byte-stable, one-use-tagged first startup message of a replacement process.

#### Metadata and cascade

- **`metadata_writes`**: a ledger of content hashes that shows which descriptions and bookmark names kk wrote (kk-ownership).

- **`sync_intents`**: the sole durable authority for reconciliation, the [embedded outbox](../appendix-a-glossary.md#embedded-cascade-outbox), and delivery. Each row is one [`sync_intent`](../appendix-a-glossary.md#sync-intent): one ordered [cascade reconciliation](../appendix-a-glossary.md#cascade-reconciliation).
  - Columns: `(intent_id, thread_id, seq, kind, from_base_commit_id, to_base_commit_id, classification_op_id, state, planned_op_id?, result_op_id?, result_workspace_commit_id?, payload?, anchor_change_id?, anchor_commit_id?, anchor_op_id?, prepared_at?, delivery_mode?, delivered_at?, acknowledged_at?, transcript_row_id?, barrier_incarnation_id?, barrier_model_turn_id?, barrier_tool_batch_id?, barrier_bound_at?, batch_completed_at?, soft_redelivery_count, restart_incarnation_id?, restart_startup_delivery_id?, restart_startup_proven_at?, delivery_exhausted_at?, delivery_epoch, delivery_rearmed_at?, recovery_reason?, recovery_bundle_path?, recovery_fingerprint?, recovery_details?, result_has_conflicts, conflicts_cleared_op_id?)`.
  - Enum values:
    - kind is `NativeRewrite | ParentAdvance` (see [`NativeRewrite`](../appendix-a-glossary.md#nativerewrite) and [`ParentAdvance`](../appendix-a-glossary.md#parentadvance));
    - `delivery_mode` is `SoftBatch | RestartStartup` (see the [`SoftBatch`](../appendix-a-glossary.md#softbatch-delivery-proof) and [`RestartStartup`](../appendix-a-glossary.md#restartstartup-delivery-proof) delivery proofs);
    - state is `Detected | Reconciling | Materialized | Delivered | Acknowledged | RecoveryRequired | TopologyDiverged | Superseded`.
  - **Conflicts.** `result_has_conflicts` (default false) records that the reconciliation result contains jj [conflicts](https://docs.jj-vcs.dev/latest/conflicts/). It is a flag, not a state. `conflicts_cleared_op_id` names the operation whose view first showed the thread's chain conflict-free.
  - **Proof fields.** Soft-barrier and restart-startup proof fields are embedded on the intent. They are not stored in another progress table.
  - **Delivery-attempt bounds** are durable on the same row. The limit is `[cascade] delivery_attempts` (default `3`):
    - `soft_redelivery_count` (default 0) counts barrier rebinds after contrary [delivery receipts](../appendix-a-glossary.md#delivery-receipt).
    - Replacement attempts are counted from the persisted `agent_sessions` rows whose `(startup_intent_id, startup_intent_epoch)` match the intent and its current [`delivery_epoch`](../appendix-a-glossary.md#delivery-epoch).
    - [`delivery_exhausted_at`](../appendix-a-glossary.md#exhausted-intent) stops all further delivery attempts for the intent until a human acts.
  - **Ordering.** `UNIQUE (thread_id, seq)` orders intents. Sequence allocation and insertion occur in one transaction.
  - **Recovery bundles** live under `~/.config/kiki/repos/<repo_id>/recovery/<intent_id>/`, outside the source workspace.
  - **Locking.** No lock is stored in the database. Restart recovery resumes from intent state, exact operation ids, and durable delivery proof. The runtime locks are in memory:
    - The [reconciliation lock](../appendix-a-glossary.md#reconciliation-lock) is a `tokio::sync::Mutex` keyed by `thread_id`.
    - The [lifecycle lock](../appendix-a-glossary.md#lifecycle-lock) is that same lock, held for the length of a lifecycle operation. It is not a second mutex.
    - The [repo jj lock](../appendix-a-glossary.md#repo-jj-lock) is one mutex per repository. `kkd` holds it around every unpinned working-copy command and every operation-head integration, from the frontier sample that the step depends on until the re-sample. It is short and innermost, and it is never held across a wait.
    - Lock order: the parent thread's lock, then the child thread's lock, then the repo jj lock.
    - The human-invoked passthroughs (the body of `kk status` and the overlay's diff for the caller's own thread) are run by `kk`, not by `kkd`. They take none of `kkd`'s locks.
  - See [Cascade](../05-cascade.md) and the [embedded-outbox design note](../17-decisions/cascade-outbox.md).

- **`sync_intent_triggers`**: the operations that triggered each intent, one row per pair.
  - The rows are normalized `(intent_id, op_id)` rows with `UNIQUE (intent_id, op_id)`.
  - Coalescing (folding several triggers into one intent) adds observed operation ids here. It also updates `classification_op_id` to the exact view used for reclassification. It does both only while the intent remains pre-materialization.
  - Coalescing does not impose a false linear “through” order on jj's operation DAG.

- **`op_attribution`**: every operation id that a kiki-run jj command wrote. kiki uses it to recognize its own operations.
  - Columns: `(op_id, invocation_id, kind, lifecycle_op_id?, intent_id?, recorded_at)`.
  - One command may write several operations. Each gets a row under the same `invocation_id`.
  - Attribution is by recorded id, and by the per-invocation operation user and host that jj stores on the operation. kiki sets no operation description.
  - Attribution suppresses only cascade re-triggering. Every attributed operation is still classified for workspace heads and checkpoint tracking.
  - Kind `Integration` marks a deliberate merge of operation heads.

#### Operation-history cache

Four of these tables form the [operation-history cache](../appendix-a-glossary.md#operation-history-cache), kiki's copy of the parts of jj's [operation log](https://docs.jj-vcs.dev/latest/operation-log/) that it needs: `op_history`, `op_history_parents`, `op_workspace_heads`, and `op_watch_frontier`. The fifth, `op_history_anchors`, records [re-anchoring](../appendix-a-glossary.md#re-anchoring) of that cache.

- **`op_history`**: the cache of operation nodes.
  - Columns: `(repo_id, op_id, committed_at, observed_at, processed_at?)` with `UNIQUE (repo_id, op_id)`.
  - A row is processed only after every relevant workspace transition for that node has been classified durably.

- **`op_history_anchors`**: re-anchoring records. An anchor is a new starting point for kiki's view of operation history.
  - Columns: `(repo_id, anchor_id, head_op_ids_json, reason: Silent | Repair, repo_issue_id?, recorded_at)`.
  - A row is written when operation history was rewritten: a recorded operation that was an ancestor of the last recorded frontier is no longer reachable from the current frontier. jj's constant root operation is never counted.
  - `Silent` is written when no thread's bookmark or head differs from its cached value. `Repair` is written when the approved `reanchor-history` plan is applied, and it names the repo issue. Between detection and that approval, no anchor row exists: bookmark classification is paused in that repo, and it resumes from the anchor recorded on approval.
  - Placements and successions recorded before an anchor are evaluated through the cached expected targets as of that anchor.
  - Operation ancestry is computed only from the anchor forward.

- **`op_history_parents`**: the edges of the operation DAG, one row per parent link.
  - Columns: `(repo_id, op_id, parent_op_id)` with `UNIQUE (repo_id, op_id, parent_op_id)`.
  - No code path may collapse an operation with multiple parents to one cursor predecessor.

- **`op_workspace_heads`**: for each operation view, where each workspace's `@` was.
  - Columns: `(repo_id, op_id, workspace_id, change_id, commit_id)` with `UNIQUE (repo_id, op_id, workspace_id)`.
  - The workspace key is load-bearing, because `@` is workspace-local.

- **`op_watch_frontier`**: the current known set of operation heads (the [operation frontier](../appendix-a-glossary.md#operation-frontier)).
  - Columns: `(repo_id, op_id, observed_at)` with `UNIQUE (repo_id, op_id)`.
  - Restart catch-up walks every not-yet-processed ancestor reachable from this frontier, in [topological order](https://en.wikipedia.org/wiki/Topological_sorting) (parents before children).
  - It is not a singular “last cursor to head” scan.

#### Publishing, config, credentials, and approvals

- **`pr_links`**: links each thread to its [pull request](https://docs.github.com/en/pull-requests) (thread → PR).

- **`thread_config`**: the per-thread config layer: key/value/updated_at.

- **`credentials`**: the repo-scoped credentials kiki has issued.
  - Columns: `(cred_id, kind: 'ThreadScoped' | 'RegistrationScoped', thread_id?, repo_id?, issued_at, revoked_at?)`.
  - The `Admin` credential is not stored here. It lives in the user-level database, in `user_credentials`.
  - Operational calls cannot substitute Admin for [human approval](../appendix-a-glossary.md#human-approval).

- **`approval_challenges`**: foreground confirmations that are still pending.
  - Columns: `(challenge_id, requester_cred_id, presenter_id?, method, repo_id, thread_id?, args_digest, rendered_plan, nonce, created_at, expires_at, confirmed_at?, confirmed_foreground_tty?, cancelled_at?)`.
  - `BeginApproval` persists the exact plan before returning it for display.
  - Only an enrolled foreground presenter may bind itself and confirm the nonce and digest.
  - Presenter binding, confirmation evidence, and capability issuance occur in one target-database [transaction](https://en.wikipedia.org/wiki/Database_transaction).

- **`human_approvals`**: one-use capabilities. Each row is one [human approval](../appendix-a-glossary.md#human-approval).
  - Columns: `(approval_id, challenge_id, requesting_cred_id, approving_presenter_id, method, repo_id?, thread_id?, args_digest, issued_at, expires_at, claimed_at?, operation_id?, consumed_at?, consuming_audit_id?)`.
  - Claim and creation of the exact `approved_operations` envelope occur atomically, before external effects.
  - A claimed approval can resume only that operation id. It cannot authorize another plan.
  - Completion marks it consumed.
  - Approvals fail closed (kiki refuses them) when they are expired, replayed, method-mismatched, target-mismatched, argument-drifted, unconfirmed, or channel-mismatched.

- **`approved_operations`**: the generic approval-claim envelope. It ties one approval to the one operation it authorized.
  - Columns: `(operation_id, approval_id UNIQUE, kind, thread_id?, plan_digest, state: Claimed | Running | Completed | Failed | OutcomeUnknown, claimed_at, updated_at, completed_at?, result_digest?, last_error?)`.
  - Lifecycle operations link their envelope to `thread_lifecycle_ops`.
  - Publish, parent-merge remote updates, sensitive snapshots, and other consequential methods use this envelope directly.
  - One approval creates one immutable envelope. Recovery may resume only its stored plan.

- **`approved_operation_steps`**: the idempotent journal of external effects for an approved operation.
  - Columns: `(operation_id, ordinal, name, state, input_fingerprint, result_json?, error?)`, unique by `(operation_id, ordinal)`.
  - Remote push and PR-base mutation are separate steps.
  - An unknown remote result becomes `OutcomeUnknown` until observation proves success or failure.
  - Read-only approved snapshots record their repository observation and result digest as one completed step. They do not leave an unjournaled reusable capability.

- **`audit_log`**: the append-only log of attempts against this repo.
  - Columns: `(audit_id, timestamp, cred_id?, approval_id?, presenter_id?, transport_peer, declared_scope?, method, args_summary, outcome)`.
  - Null identities explicitly represent unidentified or rejected callers.
  - Parseable attempts with a resolved repo go here. Attempts without a resolvable repo go to per-user `user_audit_log`. So there is exactly one authoritative row per attempt.

#### Thread events

- **`thread_events`**: the append-only event log behind `StreamThreadEvents`.
  - Columns: `(thread_id, seq, kind, payload_json, recorded_at)` with `UNIQUE (thread_id, seq)`.
  - Each row is one event for one thread: a state transition, a cascade event, or a transcript append.
  - `seq` is the monotonic number that `StreamThreadEvents` carries. It only goes up, per thread. `kkd` allocates it and inserts the row in the same transaction as the change the event reports. So `seq` survives a `kkd` restart and never repeats or goes backward.
  - A client that reconnects compares the `seq` values it receives with the last one it saw. A gap tells it that it missed events.
  - A row is a notice, not authority. The tables above remain the source of truth for state. See [gRPC](grpc.md).

#### Transcript

- **`thread_messages`**: per-thread transcript rows (the [thread transcript](../appendix-a-glossary.md#thread-transcript)).
  - Columns: `(thread_id, change_id?, commit_id?, op_id?, session_id, seq, captured_at, author, direction, text, dedup_key, synthesized, anchor_unknown)` with `UNIQUE (thread_id, dedup_key)`.
  - There is an [FTS5](https://www.sqlite.org/fts5.html) virtual table over `text`. FTS5 is SQLite's full-text search.
  - A CHECK constraint binds `anchor_unknown` to the nullability of the `(change_id, commit_id, op_id)` triple. (See [`anchor_unknown=TRUE`](../appendix-a-glossary.md#anchor-unknown-true).)
  - See [Transcript](../06-transcript.md).

- **`thread_changes`**: one row per (thread, change_id) pair.
  - It carries `tombstoned_at?` (abandon) and `redirected_to?` (squash).

- **`transcript_offsets`**: where transcript capture last stopped, per (thread, session_id).
  - Columns: `(byte_offset, last_row_uuid)`. They let tailing resume safely after a crash.
  - Both fields advance in the same transaction as the corresponding `thread_messages` insert.

- **`pending_kkd_prepends`**: a short-lived table of messages that kiki prepended (see [`pending_kkd_prepends`](../appendix-a-glossary.md#pending-kkd-prepends)). It is TTL-bounded: rows expire after a time limit.
  - Columns: `(prepend_id PRIMARY KEY, thread_id, text_sha256, inserted_at)`.
  - Duplicate `(thread_id, text_sha256)` rows are allowed. They are consumed FIFO (first in, first out).
  - The match key omits `session_id`, so fresh-session reopens match correctly.

- **`provider_egress_consents`**: remembered, revocable grants that allow transcript text to be sent to a model provider.
  - Columns: `(consent_id, thread_id, provider_identity, purpose: 'catch_up' | 'transcript_mcp', disclosure_version, granted_at, granted_by_presenter_id, revoked_at?)`.
  - Consent is valid only for the exact thread, configured provider identity, purpose, and disclosed policy version.
  - Local preview is not [provider egress](../appendix-a-glossary.md#provider-egress).
  - Returning transcript-derived text through a hosted-model [MCP](https://modelcontextprotocol.io/) call is provider egress. It must check an active `transcript_mcp` grant before reading rows.

### v2-only

- `causal_chains`, `causal_chain_visits`: deferred until the broader MCP substrate ships. See [Roadmap](../16-roadmap.md) and [causal chain](../appendix-a-glossary.md#causal-chain).

<a id="constraints-and-transactional-invariants-worth-calling-out"></a>

## Constraints and transactional invariants

This section lists rules that must hold across columns and tables. Several of them say that two changes must happen in the same [transaction](https://en.wikipedia.org/wiki/Database_transaction): either both are saved or neither is.

### `threads`

- **Required ids.**
  - `thread_head_commit_id`, `checkpoint_commit_id`, `checkpoint_change_id`, `checkpoint_op_id`, `bookmark_expected_commit_id`, `bookmark_expected_op_id`, and `owned_stack_base_commit_id` are required in `Active`, `ClosePreflight`, `CloseCommit`, `CloseFailed`, `Closed`, and `ProjectionDiverged`.
  - Destroy states retain every still-valid id until the corresponding journaled deletion or abandonment step.
  - These ids may be null only in two cases: while the corresponding creation step has not completed, or after its exact destructive step is recorded.
- **Checkpoint fields.**
  - `bookmark_expected_commit_id` is the [expected bookmark target](../appendix-a-glossary.md#expected-bookmark-target). It need not equal `thread_head_commit_id` while active.
  - `checkpoint_commit_id` must equal the latest `thread_checkpoints` row's `placed_commit_id`.
  - `bookmark_expected_commit_id` must equal that placement, updated by its `thread_checkpoint_successions` rows on the agreed frontier.
  - A placement resets the expected target to the placed commit in the same transaction that appends its row.
- **`Closed`.**
  - Entering `Closed` sets the archived `thread_head_commit_id` to the close checkpoint's target. So it requires `bookmark_expected_commit_id == thread_head_commit_id`.
  - The equality must keep holding while `Closed`. A `SameChange` or `Reverted` succession for a closed thread moves the archived `thread_head_commit_id` in the transaction that appends it. No other succession kind is valid there.
  - A reopened thread's live head is the new empty working-copy commit that `jj workspace add` creates on the checkpoint. So it reads `current`.
  - `Closed` may have one unfinished or failed `Reopen` operation. The reason: reopen does not expose an active thread until its ready handshake commits. Other lifecycle kinds are disallowed there.
- **`Active`.**
  - Entering `Active` requires the [ready-handshake](../appendix-a-glossary.md#ready-handshake) transaction.
  - The ready-handshake commit re-reads the launcher's OS identity and the `Open` `terminal_servers` row before it enters `Active`.
  - Staying `Active` requires all of these:
    - no unresolved `thread_projection_issues`;
    - no unfinished lifecycle operation other than a checkpoint operation (publish and detach run on `Active` threads);
    - a current `terminal_bindings` row in `Bound` whose `server_instance_id` is the current `Open` `terminal_servers` row, with a live `agent` role in `terminal_panes`.
  - Staying `Active` does not require a live incarnation. A harness that exited under a live launcher leaves the thread `Active` with [`AgentStatus`](../appendix-a-glossary.md#agentstatus) `Crashed`. It is never shown as working.
- **`ProjectionDiverged`.**
  - `ProjectionDiverged` requires at least one unresolved [projection issue](../appendix-a-glossary.md#projection-issue) and `projection_resume_lifecycle IN ('Active', 'Closed')`.
  - Other states require `projection_resume_lifecycle` to be null.
- **Failed states.**
  - `CreateFailed`, `CloseFailed`, or `DestroyFailed` requires the corresponding failed unfinished lifecycle operation.
  - A thread cannot return to `Active` from failed close until the journal records one of two things: a verified resume of the frozen process set and its terminal binding, or an explicit restart repair.
  - After destroy's first irreversible step, a thread cannot return to `Active`, `Closed`, or `ProjectionDiverged` by inference.
- **Mismatches inside a saga.** Projection mismatches caused inside `Creating`, `CloseCommit`, reopen, or `DestroyCommit` belong to that lifecycle journal. They fail the owning saga. They do not manufacture an invalid projection-resume state.

### `threads` bookmark name

- A non-destroyed thread's bookmark name is unique within the repo.
- A rename normalization may not adopt a name another thread holds.

### `thread_checkpoints` and `thread_checkpoint_successions`

- Both are append-only.
- A succession row requires `from_commit_id` to equal the expected target in the parent view of `op_id`.
- `SameChange` and `PredecessorOtherChange` require the predecessor evidence the classifier names.
- `Reverted` requires `to_commit_id` to be a commit that an earlier placement or succession row of the same thread recorded as the expected target. The earlier row need not belong to the same placement. `reverted_to_checkpoint_id` names it. It also requires that no successor recorded after that row is still visible at `op_id`.
- `PredecessorOtherChange` requires `to_commit_id` to be the live head or on the owned chain. The base is not on the owned chain.
- `PredecessorOtherChange` is valid only for a thread whose lifecycle or `projection_resume_lifecycle` is `Active`.
- No succession row may be appended while the thread has an unresolved bookmark issue.
- A `Creation`, `Publish`, `Close`, or `Detach` row requires the placed commit to equal or descend from the expected target.
- No row of any reason may place the bookmark off the owned chain.
- A bookmark repair through `kk repair` is a new placement row with reason `RepairRestore`, `RepairAdopt`, `RepairChoose`, or `RepairUnhide`. It is never an edited succession.
- A `Reanchor` row requires an applied `reanchor-history` plan and a bookmark that is present, not conflicted, and on the live head or the owned chain.

### `terminal_bindings`, `terminal_panes`, and `process_records`

- **Uniqueness.** Three partial unique indexes apply. (A partial unique index enforces uniqueness only over the rows that match a condition.)
  - One allows at most one non-`Ended` binding per thread.
  - Another covers `(server_instance_id, group_ref)` for non-`Ended` bindings, so one Herdr workspace backs at most one binding.
  - Another allows one live (`ended_at IS NULL`) pane row per `(terminal_binding_id, role)`.
- **`Bound`.** `Bound` requires a live `agent` pane row with `nonce_consumed_at` set. It is entered only by the transaction that accepts the `agent` claim. It does not require a `shell` or `ui` row.
- **`terminal_servers`.** At most one row is not `Ended`. `Open` requires `peer_pid` and `peer_start_time`. A binding may name only a row that is `Open` or `Ended`, never one that is `Starting`.
- **Nonce use.**
  - A pane row is inserted only in the transaction that verifies the presented nonce against `provision_nonce_hash` and sets `nonce_consumed_at`.
  - The nonce cannot be reused for another binding.
  - A repeat of an accepted report from the same `(pid, start_time)` inserts nothing and returns the earlier answer.
- **Ending and retiring.**
  - Ending a binding ends its pane rows and retires its non-retired `agent_sessions` rows in the same transaction. It does this without acknowledging any intent.
  - Retiring an incarnation does not end a pane row or a binding.
  - Ending a `terminal_servers` row ends every binding that names it. The two tables live in different databases. So each repo database applies that rule when it next observes the instance change, before any binding of that instance is used.
- **Process records.** `process_records` rows are never deleted while the thread exists.
- **Before deleting a workspace.** A workspace-forget or directory-delete step may start only when all of these hold:
  - every `process_records` row of the [frozen set](../appendix-a-glossary.md#frozen-set) has `exit_verified_at`;
  - the holder scan recorded with verified exit shows no holder other than the identities the approved plan accepted;
  - the post-exit filesystem recheck equals the final proof's journaled generation and fingerprint.

### `thread_lifecycle_steps`

- `(lifecycle_op_id, ordinal)` is unique.
- Step transitions are monotonic (they only move forward). The one exception: a failed idempotent step may return to `Started` with an incremented attempt.
- A lifecycle operation may have only one in-flight step.
- `Completed` requires `result_json` sufficient to recognize or compensate the external effect.
- Gate activation requires the credential, hook configuration, workspace head, bookmark checkpoint, and a `Bound` terminal binding whose `agent` launcher holds the gate claim. Gate activation does not enter `Active`.
- Only a ready-handshake transaction with a matching incarnation and settings fingerprint completes creation and enters `Active`.
- An activated gate alone is never success evidence.

### `thread_events`

- `(thread_id, seq)` is unique, and `seq` only goes up per thread.
- A row is inserted only in the transaction that commits the change it reports.
- Rows are never updated.

### `thread_messages`

- The CHECK constraint is: `(anchor_unknown=FALSE AND change_id IS NOT NULL AND commit_id IS NOT NULL AND op_id IS NOT NULL) OR (anchor_unknown=TRUE AND change_id IS NULL AND commit_id IS NULL AND op_id IS NULL)`.
- In plain words: a row either has a full anchor and is not marked unknown, or has no anchor and is marked unknown. The two states cannot drift apart.

### `approved_operations`

- `approval_id` is unique and immutable.
- `plan_digest` must equal the claimed approval's argument/rendered-plan digest.
- External steps cannot start before `state = Claimed`.
- Completion consumes the approval in the same transaction that commits the final result digest.
- `Failed` and `OutcomeUnknown` retain the claim. They can only retry or observe the same step plan. They never release the approval for reuse.

### `sync_intents`

- **Bases.** Both exact base commits are required.
- **Prepared states.** `Materialized`, `Delivered`, and `Acknowledged` require a result workspace commit, [byte-stable payload](../appendix-a-glossary.md#byte-stable-payload), complete anchor triple, and `prepared_at`.
- **Soft path (`SoftBatch`).**
  - Before any soft-path workspace mutation, the transaction sets `delivery_mode = SoftBatch` and the complete `(barrier_incarnation_id, barrier_model_turn_id, barrier_tool_batch_id, barrier_bound_at)` tuple. Partial tuples are invalid.
  - `batch_completed_at` requires that tuple. It may be written only by an idempotent completion report carrying the same identities.
  - Soft acknowledgement requires both that completion and a later model-turn identity.
  - If `MarkDelivered` was lost, that exact later-turn proof may atomically repair `delivered_at` and advance `Materialized -> Acknowledged`. A different batch, or stdout alone, is insufficient.
- **Restart path (`RestartStartup`).** `RestartStartup`:
  - clears the retired soft tuple without claiming acknowledgement;
  - requires the complete `(restart_incarnation_id, restart_startup_delivery_id)` pair;
  - acknowledges only at the first pre-tool hook call of a model turn in that replacement incarnation, matched by incarnation id, after the session-start hook reported the one-use id with `ReportHarnessReady`.
- **Recovery.** `RecoveryRequired` requires `recovery_reason`, `recovery_bundle_path`, and `recovery_fingerprint`. It is entered only in the transaction that records those bundle fields.
- **Conflict flag.** `result_has_conflicts` may be set only together with a result workspace commit. `conflicts_cleared_op_id` may be set only when `result_has_conflicts` is set.
- **Superseding.** Only a pre-materialization intent may become `Superseded`.
- **Rebinding and retry bounds.**
  - A barrier tuple may be rebound to a new batch after a contrary delivery receipt only in a transaction that increments `soft_redelivery_count`.
  - Retry bounds are evaluated against that column and the persisted replacement-incarnation rows. They are never evaluated against an in-memory counter.
- **Exhaustion.**
  - [`delivery_exhausted_at`](../appendix-a-glossary.md#exhausted-intent) may be set only by the transaction that abandons the final permitted attempt.
  - While it is set, exactly two writes are valid. Both are human-directed `kk repair` plans: a retry plan and a discard plan.
  - **Retry plan.** In one journaled transaction, a retry plan clears `delivery_exhausted_at`, increments [`delivery_epoch`](../appendix-a-glossary.md#delivery-epoch) (an integer starting at 0, monotonic per intent), records `delivery_rearmed_at` for display, and resets `soft_redelivery_count`.
  - Every replacement attempt is stamped with the intent's `delivery_epoch` at creation.
  - Attempt bounds count only rows whose stamp matches the current epoch. This is an exact id comparison, never a timestamp one. So clock skew or rollback cannot move an attempt between epochs.
  - A re-armed intent therefore gets exactly one fresh cycle and may exhaust again.
  - **Discard plan.** A one-shot-approved discard plan is the sole path to `Acknowledged` without delivery proof. It must record the human resolution in `recovery_details`.
  - Absent either plan:
    - no new barrier tuple or replacement incarnation may reference the intent;
    - restart recovery re-surfaces the blocked thread instead of retrying;
    - the thread's derived cascade status is `conflicted`.

### `agent_sessions`

- **Binding and identity.**
  - `terminal_binding_id` must name a binding of the same thread.
  - Its launcher identity must equal the live `agent` row of that binding in `terminal_panes`.
  - Its harness identity, once recorded, must differ from the launcher identity.
  - A non-retired incarnation requires that binding to be non-`Ended`.
  - `thread_id` must equal the binding's thread.
- **Delivery pointer.**
  - `delivered_intent_id`, when non-null, must reference a same-thread `Materialized` or `Delivered` intent assigned to that incarnation's delivery mode.
  - A partial unique index allows at most one non-retired incarnation to claim an intent.
- **Replacement processes.** Starting a replacement process does all of the following:
  - it retires the old incarnation;
  - before the harness starts, it records `startup_intent_id`, `startup_intent_epoch` copied from that intent's current `delivery_epoch`, and the saved payload hash;
  - it supplies that payload as the first startup message.
- Delivery-attempt bounds count only rows whose stamped epoch matches the intent's current one.
- The replacement's first managed boundary must re-prove exclusive hooks and the startup proof. Only then does it atomically acknowledge and clear both pointers.
- If the process exits earlier, the next replacement receives the same saved payload. No interrupted tool is replayed automatically.
- **`pause_state`.** It moves only forward: `None`, then `Stopping`, then `Stopped`, then `Killed`. Each value is written before the matching step. A row found in `Stopping` or `Stopped` at `kkd` start is rolled forward to `Killed`. An incarnation whose `pause_state` is not `None` is never resumed, and it is retired once `Killed` is recorded.

## Migrations

Every schema change ships as a [migration](https://en.wikipedia.org/wiki/Schema_migration).

- Migrations are forward-only: there is no downgrade path.
- Once a release is cut, schema changes must preserve upgrade compatibility.
- The migration runner is part of `kiki-core`.
