# Testing

Tests should target what can be observed from outside: what the system does and what it stores. They should not target private implementation details.

## Required high-value modules

[Orientation](01-orientation.md) is the only ledger that says which tier ships each surface. The two lists below only name the modules that need deep tests. They do not assign scope.

These modules sit behind the first-tier surfaces:

- `AncestryQuery`
- `OpAttribution`
- `CascadeOrchestrator`
- `ThreadLifecycleSaga`
- `ProjectionReconciler`
- `TerminalRuntime`
- `TerminalClient`
- `ProcessSupervisor`
- `ConfigLoader`
- `ContextDiscovery`
- `AuthEnforcer`
- `ApprovalBroker`
- `LogRenderer`
- `StatusRenderer`

These modules are also required. Each one is tested alongside the later surface that ships it, as Orientation stages it:

- `AICompose`
- `MetadataLedger`
- `ThreadTranscriptStore`
- `UiPaneController`
- `PaneLifecycle`
- `OverlayController`. Its tests cover:
  - opening and closing
  - NAVIGATE-mode transitions
  - preview-mode toggling (`t`/`d`/`c`)
  - the [chord ribbon](appendix-a-glossary.md#chord-ribbon) adapting to the current selection
  - graceful degradation in narrow terminals
  - mouse click-to-focus
- `ToastQueue`. A toast is a short pop-up message. Its tests cover:
  - expiry when a toast's TTL (time-to-live) runs out
  - dismissal on click
  - dismissal when the toast's action is invoked
  - dismissal when its row gains focus and is thereby acknowledged
  - coalescing (merging) of cascade-applied events
- `FormController`. Its tests cover:
  - field navigation in the spawn card
  - the approval-card flow that the [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) issues

## Regression tests for resolved spec conflicts

Each test below guards a point where the spec once disagreed with itself and has since been settled. A regression test keeps a fixed problem from coming back.

Some terms used throughout this section:

- A [thread](appendix-a-glossary.md#thread) is kiki's unit of work: a named sequence of revisions in [jj](https://docs.jj-vcs.dev/latest/), the version-control system kiki drives.
- A [workspace](appendix-a-glossary.md#workspace) is a jj [working copy](https://docs.jj-vcs.dev/latest/working-copy/): an extra working directory attached to the same repository.
- A [harness](appendix-a-glossary.md#harness) is the coding-agent program, such as [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) or [Codex](https://github.com/openai/codex).
- A pre-tool hook is a program that runs before each of the agent's tool calls. See [PreToolUse](appendix-a-glossary.md#pretooluse).
- [`kkd`](appendix-a-glossary.md#kkd) is kiki's background [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>). [`kk-hook`](appendix-a-glossary.md#kk-hook) is the small helper program the harness runs at each hook.
- [Herdr](appendix-a-glossary.md#herdr) is the [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer) kiki uses. A [terminal group](appendix-a-glossary.md#terminal-group) is one thread's set of terminals in Herdr.
- Crash injection means the test kills a program at a chosen step, then checks the state that is left behind.
- A fixture is a prepared test setup. A fake is a stand-in for a real dependency (see [Fakes](#fakes)).

### Listing, settings, and setup

- `kk ls --all` includes closed threads. It does not widen repo scope.
- `kk ls --all-repos` widens repo scope. It does so independently of lifecycle scope.
- Workspace isolation is cooperative, not a security boundary. The docs say so, and no test claims security isolation.
- Kiki keeps its launch settings and centralized state outside the workspace, so they do not block `kk close`.
  - The `.claude/settings.local.json` fallback is the one file kiki may own inside the workspace.
  - Kiki records a [hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function) of the bytes it wrote there.
  - `kk close` ignores that file only while it still matches kiki's recorded bytes.
- Untracked or ignored files that the user created still block or prompt during `kk close`.
- A turn-completion (stop) hook is installed only where its behavior is specified and tested.
  - The Codex adapter's `Stop` lifecycle event is part of its specified contract.
  - A Claude Code stop hook is not installed in v1 unless it is promoted with specified, tested behavior.
- Managed sessions of every v1 harness prove that kiki is the sole matching pre-tool hook.
  - A project or user pre-tool fixture must not execute in the managed process.
  - No test may claim that kiki merely runs before concurrently dispatched user hooks.
- Launch-scoped settings isolation leaves the tracked `.claude/settings.json` and the user's global settings byte-identical. Where the fallback is exercised instead:
  - It merges only `.claude/settings.local.json`.
  - It restores that file only from the expected kiki-owned hash.
  - If the user edited the file concurrently, it reports that instead of overwriting.
- A managed Codex session launches under the generated `CODEX_HOME`, with authentication provisioned into it.
  - The user's real `~/.codex/` configuration is untouched and unread.
  - Hook fixtures from the workspace `.codex/`, from plugins, and from managed policy must not execute in the managed process.
  - Nothing under `<workspace>/.codex/` is created, modified, or deleted.
  - There is no workspace-merge fallback. A failed isolation proof fails the [incarnation](appendix-a-glossary.md#incarnation) (one launch of the harness process) before the agent receives a prompt.
- Unrelated harness hook events stay enabled only for an adapter/version fixture that proves two things:
  - they cannot race workspace reconciliation, and
  - they cannot add another matching pre-tool hook.
- `kk init` is [idempotent](https://en.wikipedia.org/wiki/Idempotence) in an already-registered repo: running it again changes nothing. It prints status and exits 0 without mutating anything.
- `kk init` does not pre-validate harness binaries. A missing-harness error surfaces only at `kk new` time.
- `kk init` succeeds when [`gh`](https://cli.github.com/) is missing or unauthenticated. The first GitHub-backed command performs the check. It reports an actionable error without corrupting local state.
- If a thread's workspace directory is deleted out of band, the thread records `ProjectionDiverged { reason: WorkspaceDirectoryMissing }` at daemon boot or `kk ls`.
  - It fires exactly one notification.
  - It is neither recreated nor reclassified automatically.

### Codex boundary proof

- **Codex serial-dispatch proof.** The Codex adapter/version fixture proves its boundary before `parallel_batch_boundary` is claimed. The proof covers the following.
  - **Serial dispatch.**
    - No two tool calls of one turn run concurrently. That includes calls originated by subagents.
    - A new tool is requested only after the model has consumed the previous call's result.
  - **Deny behavior.**
    - A deny decision returns the saved payload to the model byte-identically, and the denied tool never executes.
    - A barrier is a block that holds the agent's [tool batch](appendix-a-glossary.md#tool-batch) during reconciliation. When the hook sidecar is dead under an active barrier, the [hook launcher](appendix-a-glossary.md#hook-launcher) answers with a generic blocking deny. So a barrier-covered call never fails open.
  - **Batch completion.**
    - A denied call fires no post-tool event.
    - So the blocked single-call batch's `batch_completed_at` is recorded by the next turn-scoped hook event's admission [transaction](https://en.wikipedia.org/wiki/Database_transaction). That is a crash-surviving report driven by the harness.
    - It is never recorded by the emitting hook's own [RPC](https://en.wikipedia.org/wiki/Remote_procedure_call).
  - **Acknowledgement.**
    - Acknowledgement requires a `PreToolUse` with a distinct, serially later `tool_use_id`.
    - A same-or-later Codex `turn_id` alone never suffices, because one `turn_id` spans many model steps.
    - Acknowledgement always requires the [delivery receipt](appendix-a-glossary.md#delivery-receipt): the session record's byte-identical deny result for the blocked `tool_use_id`.
    - `MarkDelivered` alone never suffices.
  - **Crash and fault injection** covers these cases. An intent ([`sync_intent`](appendix-a-glossary.md#sync-intent)) is the durable record of one unit of pending cascade work.
    - Hook death before stdout: the hook launcher answers with a generic deny, and the contrary receipt redelivers on the arriving batch.
    - Stdout written but timed out or rejected by the harness: `MarkDelivered` is recorded, the receipt is contrary, and the intent is redelivered. It is never acknowledged.
    - Persistent output rejection:
      - A second contrary receipt for the same intent fails over to [`RestartStartup`](appendix-a-glossary.md#restartstartup-delivery-proof) instead of redelivering again.
      - Exhausted bounded restart attempts [hard-pause](appendix-a-glossary.md#hard-pause) with a loud [attention event](appendix-a-glossary.md#attention-event) rather than looping.
    - Daemon restart between and after those attempts: the attempt history and exhaustion state are read from the intent.
      - So a restart after the first contrary receipt still treats the next one as the second.
      - A restart after exhaustion re-surfaces the blocked thread without minting a new attempt.
    - The two repair exits:
      - A [`retry-delivery`](appendix-a-glossary.md#retry-delivery) plan re-arms exactly one fresh bounded cycle by incrementing the [delivery epoch](appendix-a-glossary.md#delivery-epoch). So bounds count only attempt rows stamped with the current epoch. A prior-epoch row can never consume the fresh cycle. No bound ever compares timestamps, even under clock skew or rollback.
      - A [`discard-delivery`](appendix-a-glossary.md#discard-delivery) plan acknowledges without delivery proof only under a one-shot approval bound to that plan, and records the human resolution.
      - No other write is accepted against an [exhausted intent](appendix-a-glossary.md#exhausted-intent).
    - Receipt unreadable at the completing arrival: acknowledgement defers when no delivery is pending, and takes `RestartStartup` when one is.
    - Matching receipt: acknowledge.
  - **Beyond the fault cases.**
    - The generated config pins the harness-side hook timeout above the slow-path bound.
    - The fixture proves the session record durably contains deny results exactly as returned to the model.
    - Every workspace-observing tool in the pinned version fires `PreToolUse` or is disabled by the generated config.

### Creation, launchers, and provisioning

A [pane launcher](appendix-a-glossary.md#pane-launcher) is the kiki process that starts first in each pane kiki sets up. It waits at a [launch gate](appendix-a-glossary.md#launch-gate) until `kkd` lets it start the harness.

- **Creation crash injection.** Crash injection at every creation [journal](appendix-a-glossary.md#lifecycle-journal) step leaves the thread in `Creating` or `CreateFailed`.
  - Gate activation and harness start remain `Creating`.
  - Only the matching [ready handshake](appendix-a-glossary.md#ready-handshake) may enter `Active`.
  - The pane launcher cannot pass its database-backed gate before these are durable: the credentials, exclusive hooks, [live head](appendix-a-glossary.md#live-head), checkpoint, and a `Bound` [terminal binding](appendix-a-glossary.md#terminal-binding).
  - Accepting a launcher and activating a gate are two transactions.
    - The first accepts exactly one launcher for `(provision_id, role)`, records its OS-read process identity, and marks the binding `Bound`.
    - The second records the incarnation and activates its gate. It is refused without a `Bound` binding.
  - The [provision nonce](appendix-a-glossary.md#provision-nonce) (a one-use secret) reaches the launcher only through its launch [environment](https://en.wikipedia.org/wiki/Environment_variable).
    - It never appears in argv or in Herdr's saved state.
    - Only its hash is stored.
    - It is rotated before any re-issued create call.
  - The harness is always the launcher's child.
    - It is started from the [launch specification](appendix-a-glossary.md#launch-specification) `kkd` computed through `Harness::launch_spec`.
    - The launcher never replaces itself with the harness.
    - The launcher holds the child before exec until `ReportHarnessStarted` has recorded its identity. So a crash at any point leaves either no harness or a recorded one.
  - The ready handshake arrives from `kk-hook` at the harness's session-start event.
    - Its commit re-reads the launcher's OS identity and the open `terminal_servers` row.
    - A launcher or server that changed in between fails the handshake.
- **Launcher report acceptance.** `kkd` accepts a launcher's start report only from the real root process of the reported pane.
  - A `ReportLauncherStarted` is accepted only when both of these hold:
    - the caller's [peer-credential](https://man7.org/linux/man-pages/man7/unix.7.html) identity has the current [server instance](appendix-a-glossary.md#server-instance)'s process as its parent, and
    - a fresh per-pane process query shows the reported pane's root [pid](https://en.wikipedia.org/wiki/Process_identifier) is that caller.
  - Refused cases:
    - a process that is not a pane root presenting a copied nonce
    - a launcher left over from a previous server instance reporting after a restart
    - a launcher reporting a pane id that belongs to another process
    - a second launcher for an already-claimed role
    - a launcher reporting from a different Herdr workspace than the binding's first accepted launcher
  - Two non-`Ended` bindings can never name the same `(server_instance_id, group_ref)`.
  - The [final proof](appendix-a-glossary.md#final-proof), before anything is terminated, includes a fresh observation. The observation shows that each listed container still holds the binding's recorded launcher process. For a [remnant](appendix-a-glossary.md#remnant-container) or [unbound container](appendix-a-glossary.md#unbound-container), it shows that the container holds the exact processes listed in the approved plan. Otherwise nothing is terminated and no close request is sent.
- **Compensation limits.** Compensation is the automatic undo of a half-finished create or reopen. It runs only in a narrow case.
  - Automatic create and reopen compensation closes the provisioned group and removes the new jj workspace only while all three of these hold:
    - the gate was never activated,
    - `ProcessSupervisor` shows nothing in the group but kiki's own blocked launchers, and
    - the workspace still equals its initial [materialization](appendix-a-glossary.md#materialization).
  - A fixture breaks one of these before the failure: it activates the gate, adds a [`user` pane](appendix-a-glossary.md#user-pane), or writes one file into the workspace. The [saga](appendix-a-glossary.md#saga) then stops in `CreateFailed` (or the failed reopen state) with [projections](appendix-a-glossary.md#projection) intact.
  - Cleanup then requires an approved [repair plan](appendix-a-glossary.md#repair-plan) that runs the close machinery.
- **Harness exit versus launcher exit.** The two exits are handled differently.
  - When the harness exits under a live launcher:
    - The launcher reports it, re-reads the atomically replaced thread credential, and awaits the next gate.
    - The incarnation is retired without acknowledgement.
    - [`AgentStatus`](appendix-a-glossary.md#agentstatus) is `Crashed`, and the display state is `blocked`.
    - The `agent` role and the thread's lifecycle are unchanged.
    - No surface shows the thread as working.
  - A replacement incarnation is a new `agent_sessions` row and a new one-use gate claimed by the same accepted launcher, with no terminal provisioning.
  - Kiki's own protocol restarts — a cascade hard restart or `RestartStartup` replacement — need no `HumanApproval`.
  - The `kk repair` plan [`restart-agent`](appendix-a-glossary.md#restart-agent) restarts a crashed harness on the live launcher. It uses `RestartStartup` when an intent is pending. It needs no approval in thread context.
  - When the launcher itself exits, or its binding or server instance is lost:
    - The `agent` role ends.
    - The thread raises [`TerminalMissing`](appendix-a-glossary.md#terminalmissing).
    - The restart plan needs approval.
    - In an agent-only group the launcher's exit also removes the Herdr workspace. Kiki reads that from a snapshot, not from a workspace-closed event.
  - A harness killed without a report is found by `ProcessSupervisor` and handled as a harness exit.
  - "The launcher answers" is tested as both conditions: its OS identity is alive and not stopped, and its supervision stream is open. A stopped launcher with an open stream does not answer.
- **Replacement-incarnation remnant check.** A retired harness leaves a tool child running in the launcher's descendant, session, or [process-group](https://en.wikipedia.org/wiki/Process_group) set.
  - The replacement's gate is not activated and no materialization runs.
  - The thread raises [`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess) with harness-remnant evidence.
  - Hard-pause and `terminate` record and cover the harness's whole process tree, so the ordinary path leaves no remnant.
  - The test injects one that escaped the tree but stayed in the session.
- **Provisioning moves no viewer.** Two clients are attached to different terminal groups.
  - Each of these leaves both clients where they were:
    - creation
    - reopen
    - a terminal-restart repair
    - a replacement incarnation
    - duplicate-group cleanup
  - This has not yet been run with attached clients at the candidate revision. It is an integration gate, not an assumed fact.
  - The gate also records Herdr's known exceptions rather than hiding them:
    - the first Herdr workspace created on an empty server takes focus
    - applying a layout over the active tab switches its viewers to the new tab
    - a client viewing a replaced tab falls back to the server default
- **Provisioning after a lost reply.** The runtime's create or layout reply is lost, or the daemon crashes before the binding transaction.
  - Recovery takes a fresh snapshot and collects launcher reports before it issues any new call.
  - A fault that produces two terminal groups for one `provision_id` ends with exactly one accepted launcher per `(provision_id, role)` and one gate claim.
  - Every other launcher is refused and exits without starting anything.
  - The duplicate group is closed only after `ProcessSupervisor` shows it holds nothing but refused, exited launchers. Otherwise it stays and is reported as unbound.
  - No fault order yields two harness processes.
- **A runtime reply is never an outcome.** Kiki never treats a success reply from the terminal runtime as proof that something happened.
  - Fakes return success for create, layout, input, focus, and close while one of these is true:
    - the launcher never reports
    - the harness never becomes ready
    - the focus moved nobody
    - a process survives
  - In every case kiki's state follows the launcher report, the ready handshake, the cascade protocol, or the `ProcessSupervisor` proof. It never follows the reply.
  - Three things change neither `AgentStatus`, [agent quiescence](appendix-a-glossary.md#agent-quiescence), the [process quiescence proof](appendix-a-glossary.md#process-quiescence-proof), nor any delivery or acknowledgement state: Herdr's agent detection, `agent.wait`, and text accepted into a pane's input queue.

### Reopen, close, and destroy

Closing a thread deletes its workspace directory, so kiki first proves that nothing is still writing there. To do that it [freezes](appendix-a-glossary.md#freeze) (stops, without killing) every process in the thread's terminals, checks the files, and only then removes anything. The tests below pin each step of that order.

- **Reopen.** Reopen keeps the thread `Closed` while its durable journal recreates projections.
  - Its preflight verifies that the [bookmark](appendix-a-glossary.md#bookmark) names `bookmark_expected_commit_id`. That is the latest placement updated by recorded successions (see [expected bookmark target](appendix-a-glossary.md#expected-bookmark-target)).
  - It recreates the jj workspace at that exact commit.
  - The reopened head is the new empty working-copy commit on top of it, and the relationship reads `current`.
  - A closed thread whose checkpointed commit was natively rewritten since close reopens at the successor without repair.
  - Crash injection at every step either adopts the exact resource, [compensates](appendix-a-glossary.md#compensation) back to `Closed`, or records a stable repair plan.
  - It never exposes `Active` before a matching ready handshake.
  - Every new incarnation independently re-proves exclusive hook control.
- **Close wants a quiet agent.** [Agent quiescence](appendix-a-glossary.md#agent-quiescence) is the harness adapter's proof that the agent is idle.
  - Where the adapter proves agent quiescence, `kk close` preflight requires it. With a working agent, preflight reports that and exits with no mutation, no freeze, and no approval challenge.
  - For an adapter version with `quiescence_detection: false`, preflight proceeds with a warning. A working agent then produces [approval drift](appendix-a-glossary.md#approval-drift) and a [verified resume](appendix-a-glossary.md#verified-resume), never a loss.
  - In both cases preflight takes the [boundary snapshot](appendix-a-glossary.md#boundary-snapshot) so that the pinned head contains every tracked edit.
- **Close freeze and step order.** Close finds every process to freeze, records each one before signalling it, and runs its steps in a fixed order.
  - Roots:
    - Close takes its roots from every pane in the terminal group — [role panes](appendix-a-glossary.md#role-pane) and `user` panes alike — plus every process identity recorded for the binding.
    - It re-reads each root from the OS.
    - A pane root is trusted only if its parent is the current server process.
  - The freeze is write-ahead. Each discovered identity is committed to `process_records`, with its prior stop state and the freeze's lifecycle operation id, before it is signalled.
  - It freezes roots, descendants, session members, and process-group members to a fixed point (until a repeat scan finds nothing new).
  - Its journaled steps run in this order:
    1. freeze
    2. [post-freeze recheck](appendix-a-glossary.md#post-freeze-recheck)
    3. checkpoint
    4. each child step
    5. final proof
    6. termination of the [frozen set](appendix-a-glossary.md#frozen-set) with [verified exit](appendix-a-glossary.md#verified-exit)
    7. terminal-group close request
    8. [post-exit filesystem recheck](appendix-a-glossary.md#post-exit-filesystem-recheck)
    9. workspace forget
    10. directory delete
  - The **post-freeze recheck** runs immediately after the freeze and before the checkpoint.
    - It binds the frozen state to the approved fingerprint.
    - It must show that no frozen member holds an open [descriptor](https://en.wikipedia.org/wiki/File_descriptor) under the repository's `.jj` directory.
  - The checkpoint pins the exact commit with a pinned, working-copy-ignoring jj command.
  - Children are synchronously reconciled or detached.
  - The **final proof** runs after the checkpoint and all child work. It re-asserts that every member is stopped, plus membership, holders, the runtime pane set, the filesystem generation, and the fingerprint.
  - The final proof is the recovery boundary.
    - A failure at or before it takes the verified-resume path before returning `Active`. A failed resume becomes `CloseFailed`.
    - A crash after it resumes the idempotent journal forward and never returns to `Active`.
  - Close never guesses from filesystem presence.
- **Teardown order.** Kiki itself terminates the frozen set while it is still stopped, before it asks the runtime to close the group.
  - Per identity, kiki confirms the process is still stopped and still the recorded `(pid, start_time)`, sends `SIGKILL`, and verifies the process is gone. (`SIGKILL` is the [signal](<https://en.wikipedia.org/wiki/Signal_(IPC)>) a process cannot catch or ignore.) A [zombie](https://en.wikipedia.org/wiki/Zombie_process) counts as exited.
  - Two fixtures are both dead before the close request is sent: one that traps or ignores every catchable signal, and one that would be continued by a hangup. Neither runs a single instruction after the final proof.
  - A process whose identity changed after it was stopped is continued and treated as unknown, never killed.
  - Where the OS offers a [process handle](https://man7.org/linux/man-pages/man2/pidfd_open.2.html), signals go through the handle.
  - The terminal-group close request is cleanup only, and its reply is never evidence.
  - The **post-exit filesystem recheck** then requires the generation and fingerprint to equal the final proof's journaled values.
    - It is re-read after a `kkd` crash, because the watch is lost with the process.
    - Any mismatch is `CloseFailed` with files preserved. Forget and delete do not run.
- **Write-ahead freeze crash.** `kkd` is killed after stopping some members and before stopping others, and again after the freeze completes.
  - On restart the frozen set is rebuilt from `process_records`, never from memory or a re-discovery.
  - Verified resume continues exactly the members recorded as previously running.
  - No member is left stopped without a row.
  - No row names a process that was never signalled as one that must be continued.
- **Frozen-step deadlines.** Every step taken while the set is frozen has a deadline.
  - A checkpoint, child step, or runtime call that exceeds it takes verified resume. The thread is never left frozen behind a stalled step.
  - A frozen member holding a descriptor under `.jj` — a jj process stopped while holding repository locks — fails the post-freeze recheck. It takes verified resume before any jj command is attempted.
- **Destroy order.** Destroy runs its steps in this order:
  1. freeze
  2. post-freeze recheck
  3. final proof
  4. termination of the frozen set with verified exit
  5. group close request
  6. post-exit filesystem recheck
  7. then bookmark deletion
  8. optional exact abandon
  9. workspace forget and delete
  10. credential revocation
  11. tombstone
  - Drift before termination takes verified resume.
  - Process termination is the first irreversible step. Crash injection after it yields only `DestroyFailed` or completion of the same plan.
- **Approval scope.** A close, destroy, or restart approval covers every process in the listed terminal containers at freeze time.
  - The rendered plan lists the preflight process inventory and states that scope.
  - A process that appears in a listed container between preflight and freeze is terminated under that statement and is not drift.
  - A [workspace holder](appendix-a-glossary.md#holder) outside every listed container is accepted only when the approved plan names that exact identity (see [accepted holder](appendix-a-glossary.md#accepted-holder)). Any other holder is drift.
- **Two kinds of quiescence.** The process quiescence proof is the `ProcessSupervisor` freeze fixed point.
  - Only close, destroy, and repair use it.
  - The cascade's boundary is agent quiescence — the harness adapter's `AgentStatus::Quiescent` — and never the process freeze.
  - Terminal observations satisfy neither.
- **Process quiescence proof cases.** These are driven through the `ProcessSupervisor` fake and repeated against real processes at the integration gate:
  - Fixed-point growth:
    - A member that forks during discovery grows the set on a later round.
    - The proof holds only after two identical complete samples with every member observed stopped.
    - A set that does not stabilize within the bound is `Unknown`.
  - Prior stop state:
    - A process that was already stopped before the freeze stays stopped after an aborted close.
    - A process that was running is continued.
  - A root whose OS start time disagrees with the record is a different process. It is treated as unknown, never as the recorded one.
  - Unknown holder:
    - A same-UID process outside the frozen set that holds the workspace makes the result `Unknown`, unless the approved plan names that exact identity as accepted.
    - Files are preserved.
    - The result reports each offending pid, its command line, and the step that clears it.
    - `kkd`, its child processes, and the invoking `kk` are excluded from the scan.
    - A process running as another user is invisible to the scan, and no test or message claims otherwise.
    - A member stopped by a debugger makes the result `Unknown`.
    - An unrecorded holder never blocks an `Active` thread's cascade boundaries and raises no standing issue.
  - Split during freeze:
    - A pane or tab added to the terminal group after the freeze is drift at the final proof.
    - Where the runtime advertises [`mutation_fence`](appendix-a-glossary.md#mutation-fence), the split is refused instead.
    - Neither case proceeds to an irreversible step.
    - Without a fence kiki detects pane-set and tab-set changes only. It makes no claim about terminal input sent to a frozen pane.
  - Drift found by the post-freeze recheck or the final proof preserves files and takes the verified-resume path. Drift means any of these:
    - a changed member set
    - a new holder
    - a changed runtime pane set
    - a new filesystem generation
    - a changed fingerprint
  - Verified resume:
    - Members are continued children before parents, session leaders last.
    - Every member keeps its recorded identity, and none that was running is left stopped.
    - Resume requires the role-launcher identities and the terminal group, and the `agent` launcher must answer.
    - A `user`-pane process that exited during the freeze is reported and is not a failure.
    - Only then may the thread return to `Active`.
    - An unprovable resume is `CloseFailed` with the workspace present.
    - If a tool batch was in flight when the freeze began, the incarnation's batch state is unknown after resume. The unknown-batch rule then applies: hard restart to a clean boundary with files untouched.
  - Verified exit:
    - Exit is verified per recorded identity by kiki's own termination, before the runtime is asked to close anything.
    - Two fake runtimes change nothing: one that replies success to a close request while a process survives, and one that never replies.
    - Workspace deletion depends only on every frozen identity being gone, the holder scan, and the post-exit filesystem recheck.
    - If exit cannot be verified, the files stay and the lifecycle fails loudly.
- **Close approval binding.** A close approval is bound to the rendered plan and the preflight fingerprint.
  - Drift discovered after the freeze causes a verified resume and a fresh plan and approval.
  - The daemon never prompts while leaving a terminal group frozen.
- **Destroy keeps revisions by default.** `kk thread destroy` deletes kiki projections and records only after an exact plan is confirmed.
  - It preserves jj revisions by default.
  - `--abandon-revisions` may abandon only the validated, unreferenced, single-parent owned chain named in a separate approved plan.
  - It refuses shared, foreign, followed, or ambiguous topology.
- **Destroy crash injection.** Crashes are injected before and after each of these: bookmark deletion, optional exact revision abandonment, terminal-group and workspace cleanup, and tombstoning.
  - They yield only the recorded `DestroyCommit`, `DestroyFailed`, or `Destroyed` outcome.
  - After the first irreversible step, no recovery path relabels the thread `Active`, `Closed`, or `ProjectionDiverged`.
  - `kk repair` can only finish the exact approved plan, or invoke explicit jj operation recovery where that applies.

### Projection issues and the terminal runtime

A [projection](appendix-a-glossary.md#projection) is a changeable outside thing that stands for a thread, such as its bookmark, workspace path, or terminal group. [Projection divergence](appendix-a-glossary.md#projection-divergence) means one of them no longer matches kiki's records.

- **[Projection issues](appendix-a-glossary.md#projection-issue).** Workspace-record, path, bookmark, and terminal mismatches all produce durable projection issues.
  - Only a unique, identity-preserving normalization may auto-repair.
  - Every ambiguous plan uses a stable repair id, and that id goes stale when the observed state changes.
  - Bookmark-only divergence continues safe workspace-head tracking and follows classification.
  - Terminal divergence continues observation but suspends boundary mutation.
  - Workspace identity or path ambiguity suspends both.
- **`TerminalMissing` causes and role identity.** `TerminalMissing` is raised for each of its causes, and a role belongs to one process identity.
  - The causes are:
    - a missing or changed server instance
    - a server instance `kkd` did not start
    - a missing terminal group
    - an ended `agent` role launcher
    - a [cold restore](appendix-a-glossary.md#cold-restore)
    - an observed live handoff
  - A role is bound to the claiming process identity `(pid, start_time)`.
    - It survives a `shell` or `ui` launcher replacing itself with the shell or UI program.
    - It ends when that identity ends.
    - A pane with no claiming identity has no role; `user` names that absence.
  - While `TerminalMissing` is open, boundary delivery, materialization, and lifecycle mutation are blocked. The exceptions are approved restart, [`close-without-terminal`](appendix-a-glossary.md#close-without-terminal), and destroy plans.
  - A match on a different server instance never rebinds a thread. That holds for a matching Herdr workspace, tab, or pane id, label, working directory, or metadata token.
- **No container reuse.** A terminal restart never binds a remnant or unbound container, whatever its label or working directory.
  - The restart plan does these things:
    1. It lists every remnant or unbound container whose processes hold the workspace, with those processes, for approval.
    2. It closes each through freeze, termination with verified exit, and a close request.
    3. It re-runs the holder scan.
    4. It provisions a fresh terminal group with new launchers.
  - The same steps run in `close-without-terminal` and in destroy from `ProjectionDiverged`.
  - A restored login shell sitting in the jj workspace is found as a holder and listed. It is never adopted and never silently killed.
- **Context resolution.** Resolution by Herdr pane identity succeeds only when `kkd` verifies one thing from the CLI connection's peer credentials: the caller is a descendant or session member of that pane's root process on the current server instance.
  - Refused cases:
    - ids copied into an unrelated process's environment
    - ids from another Herdr server
    - ids left stale by a native pane move
    - ids from a previous server instance
  - A popup or keybinding invocation resolves through `HERDR_ACTIVE_*` only as a locator for read-only and navigation commands. A mutation invoked that way still requires the thread credential and any approval.
  - Herdr ids never substitute for a credential.
- **Presenter under an agent.** The presenter is the foreground program that shows an approval to the human (see [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter)).
  - `ConfirmApproval` is refused when the presenter process is a descendant or session member of any recorded `agent`-role launcher. That includes a presenter started by an agent's tool call in its own pane.
  - The same presenter in a `shell` or `user` pane is accepted.
- **Harness environment.** The test checks which [environment variables](https://en.wikipedia.org/wiki/Environment_variable) each pane sees.
  - The harness process and its tool children see no `HERDR_*` variable.
  - The `agent` pane keeps `KIKI_THREAD_ID`.
  - No pane of any role sees a redirected `XDG_CONFIG_HOME` or `XDG_STATE_HOME`.
  - No pane of any role sees a variable that came from the terminal that happened to invoke `kk`, such as that terminal's `TERM_PROGRAM`, window id, or multiplexer variables.
  - Panes inherit only the constructed login baseline, Herdr's own variables, and the role's explicit variables.
  - `HERDR_CONFIG_PATH` is visible in panes, and the test records that as expected.
- **Server start and configuration.** `kkd` regenerates the Herdr configuration file and validates it with its own parser immediately before every server start.
  - A file rewritten by Herdr's settings screen is replaced.
  - A generated file that fails validation prevents the start. The server is never started on a file that Herdr would silently replace with defaults, because those defaults turn agent resume on.
  - The start uses `--session` and `HERDR_CONFIG_PATH` only.
  - `kk attach` connects in connect-only mode. With no server running and `kkd` unreachable, it fails instead of starting a server.
  - A server that `kkd` did not start is unverified: nothing is provisioned on it and its threads read `TerminalMissing`.
- **Service placement.** On macOS `kkd` runs as a [launchd](https://en.wikipedia.org/wiki/Launchd) user agent and starts the Herdr server from there. On Linux it is a [systemd](https://en.wikipedia.org/wiki/Systemd) user unit.
  - With `kk` first invoked from inside a terminal application, quitting that application leaves `kkd`, the server, and every agent running.
  - This is an integration gate on each platform.
  - No Herdr release containing its own terminal-quit fix is required, because that fix applies only to a server Herdr starts for itself.
- **Cold restore.** The [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) stops and restarts with its saved layout.
  - What the runtime does:
    - The fake and the real runtime both return the same public workspace, tab, and pane ids with new processes. They may reuse a closed group's workspace id for a new group.
    - Launch argv is saved but not rerun.
    - Launch environment and tokens are not kept.
    - A restored pane whose saved directory is gone has no process.
  - What kiki does:
    - It records a new `server_instance_id`.
    - It ends every binding from the old instance.
    - It retires every incarnation without acknowledgement.
    - It runs the [orphan scan](appendix-a-glossary.md#orphan-scan).
    - It raises `TerminalMissing` for each affected thread.
  - What does not happen:
    - No restored pane is ever reported `Active`.
    - `kk status --no-jj` and `kk ls` do not show a ready agent for it.
    - No boundary mutation runs against it.
    - Kiki publishes no label to a remnant container.
  - The generated Herdr configuration disables automatic agent resume. A fixture with a resumable harness session proves the runtime starts no agent on restore.
  - A restart happens only through an approved `kk repair` plan with a fresh credential, launch settings, gate, and handshake, in a freshly provisioned group.
- **Daemon restart with a surviving server.** `kkd` reconnects, verifies the `server_instance_id` against its record, snapshots, and reconciles. Bindings whose recorded process identities are still live under the same instance continue without a new incarnation.
- **Orphan recovery.** An [orphan](appendix-a-glossary.md#orphan) is a process kiki recorded that is alive where kiki's records say none should be.
  - A worker that ignores hangup survives a `SIGKILL` of the dedicated server and is absent from every terminal view.
  - The orphan scan runs at daemon start, at the instance change, and before a replacement. It finds the worker by recorded identity and raises `OrphanedProcess`.
  - The fixture's worker is a recorded identity — the harness itself.
  - A second fixture uses a tool child that kiki never recorded.
    - It raises no `OrphanedProcess`.
    - Instead the [`restart-terminal`](appendix-a-glossary.md#restart-terminal) plan's holder scan reports it by pid and command.
    - The plan stops until it names the process as accepted or the process is gone.
    - Kiki does not signal it.
  - While the issue is unresolved, kiki activates no gate and materializes nothing in that workspace.
  - The approved repair plan stops, re-verifies, and terminates only the exact recorded identities and verifies their exit.
  - Recorded role processes that are pane members on the current instance are terminal members and raise no orphan issue.
  - An unrecorded same-UID holder raises no standing issue. It surfaces only as an `Unknown` result in an operation that would delete the workspace.
- **Event loss and resync.** The runtime fake reports lost events, drops the connection, and changes instance between a subscription and its snapshot.
  - In every case `kkd` resubscribes, takes a fresh snapshot, reconciles every binding against the snapshot and the OS, and republishes presentation.
  - No decision is reconstructed from the runtime's event history.
  - A label renamed by another socket peer is republished to its bound terminal group and is never read back as input.
  - The matching cases for [sidebar tokens](appendix-a-glossary.md#sidebar-token) — overwritten, expired, or lost at restart, then republished — are tested with the later sidebar-token surface, not here.
- **Caller-local focus with two attached clients.** [Caller-local focus](appendix-a-glossary.md#caller-local-focus) moves only the viewer who ran the command.
  - With [`client_targeted_focus`](appendix-a-glossary.md#client-targeted-focus) advertised, `kk switch <thread>` moves only the invoking client. The other client's location is unchanged.
  - A command with no viewer — an agent's tool call, a script, a pane nobody is showing — resolves `NoCallerClient` and moves no one.
  - Without the capability, `kk switch <thread>` fails naming the missing capability and moves no client. It never falls back to the broadcast focus.
  - `kk switch --all-clients <thread>` is the only form that moves every attached client.
  - Capability detection reads the runtime's advertised capabilities. A fake that silently ignores the unknown client parameter must not be mistaken for support.
  - No form of switch creates, closes, or re-ensures a pane, and none consumes a `HumanApproval`.
- **`TerminalMissing` repair.** A `TerminalMissing` repair can restart the thread to `Active`, or execute a stable `close-without-terminal` plan to `Closed`.
  - That plan's [loss inventory](appendix-a-glossary.md#loss-inventory) runs in preflight.
  - Claiming its approval enters `CloseCommit`.
  - Its journaled `CloseCommit` steps run in this order:
    1. Listed remnant and unbound containers that hold the workspace are frozen and rechecked, which records their identities.
    2. They are then terminated with verified exit and closed.
    3. Then come the holder scan, the checkpoint, child steps, the final proof, the post-exit filesystem recheck, forget, and delete.
  - An abort before the first irreversible step takes `CloseCommit --> ProjectionDiverged`, mirroring `DestroyCommit`.
  - Crash injection at each step resumes the same plan and never returns the thread to `Active`.

### Hook outages and barriers

- **Daemon unreachable from the hook.** `kk-hook` returns the harness's non-blocking decision (Claude Code's `continue`, Codex's `allow`) when it cannot reach `kkd` within its connect and overall budget. It also writes to `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log`.
  - It does not block the agent's tool call.
  - A reconciliation pending during the outage must still be delivered on the next successful PreToolUse round-trip.
  - If the watcher saw the trigger, durable state lives in `sync_intents`.
  - Otherwise, restart catch-up reconstructs it from jj's [op log](https://docs.jj-vcs.dev/latest/operation-log/) (jj's record of every operation run against the repo).
  - If the agent edited the stale tree during the outage, the next probe enters `RecoveryRequired` rather than treating the tree as clean.
- **Active barrier during an outage.** Once a cascade [delivery barrier](appendix-a-glossary.md#delivery-barrier) is active, a daemon outage no longer lets tools pass through. Every call in that tool batch stays blocked until a matching `PostToolBatch` completes the barrier or the adapter takes the hard-restart path.
- **Barrier before mutation.** The `Block` admission and the complete soft-barrier identity commit before the first reconciliation mutation. Crash injection between every probe, jj, filesystem, and [SQLite](https://www.sqlite.org/) step must never leave changed files with an unbound batch.

### Cascade classification and materialization

A cascade carries a parent thread's changes into the threads that [follow](appendix-a-glossary.md#follows) it. A change that needs reconciliation is one of two kinds. In a [`NativeRewrite`](appendix-a-glossary.md#nativerewrite), jj has already rewritten the child's commits. In a [`ParentAdvance`](appendix-a-glossary.md#parentadvance), the parent gained a new commit and kiki [rebases](https://git-scm.com/docs/git-rebase) the child. [Materialization](appendix-a-glossary.md#materialization) means updating a workspace's files on disk to match. A [safe boundary](appendix-a-glossary.md#safe-boundary) is a moment when the agent is not in the middle of an edit.

- **Native ancestor evolution.** Amending thread A causes jj to evolve thread B's repository working-copy commit.
  - The classifier records `NativeRewrite` with the exact old-base → evolved-base ids.
  - It performs no redundant rebase.
  - At B's safe boundary, it verifies that B's current commit still contains that base before materializing it (updating B's files to match).
- **Parent-head advance.** Adding revision A2 in A's managed workspace updates A's persisted [live head](appendix-a-glossary.md#live-head).
  - A's checkpoint bookmark remains on A1, and `bookmark_expected_commit_id` does not change.
  - No bookmark issue is raised. Once A2 has content or a description, status shows the relationship `behind`.
  - The classifier records `ParentAdvance` from the exact live head.
  - B's boundary rebases only the validated single-parent owned chain (see [owned stack](appendix-a-glossary.md#owned-stack)).
  - Merge, multiple-root, or foreign topology stops as [`TopologyDiverged`](appendix-a-glossary.md#topologydiverged).
- **`ParentAdvance` result is persisted.** A successful `ParentAdvance` persists B's actual result as `threads.thread_head_commit_id`, in the same transaction as the materialized intent.
  - The watcher does not re-trigger cascade for the attributed jj operation.
  - The head advance is not lost; checkpoint classification still runs on it.
- **Multi-workspace cascade in A→B→C.** One jj operation may logically evolve both B and C.
  - Both receive independent `NativeRewrite` intents immediately, from comparing the before and result operations.
  - B and C materialize at their own boundaries.
  - If an explicit advance of B evolves C, the initiating reconciliation handler records C's intent. It does so even though the watcher does not re-trigger cascade for the attributed op.
- **Direct human materialization.** A person may run `jj workspace update-stale` directly in stale B.
  - In a non-colocated repository that changes B's files without creating a new op-log head.
  - In a [colocated](https://docs.jj-vcs.dev/latest/git-compatibility/) repository (one shared with Git) it also records a "reset git head" operation. The watcher classifies that as no [base transition](appendix-a-glossary.md#base-transition).
  - In both cases the boundary probe detects `FreshClean` or `FreshDirty`, performs no duplicate update, and still delivers context for the unresolved intent.
- **Coalescing.** Coalescing updates one pre-materialization intent's base transition and its normalized trigger rows. Once payload preparation begins, later work receives a new ordered intent and cannot mutate the saved delivery.
- **Stale workspace with hidden edits.** A stale workspace with unsnapshotted edits, or an `Unknown` probe result, enters `RecoveryRequired`.
  - Recovery hard-pauses the agent and enumerates [divergent](https://docs.jj-vcs.dev/latest/glossary/) successors outside the workspace (see [`WorkspaceRecovery`](appendix-a-glossary.md#workspacerecovery)).
  - It never resumes on a clean successor that hides those edits.
  - The `JjBackend` fake and real jj both return success from a dirty `jj workspace update-stale` while the edited file is gone from disk and present only in the other divergent successor.
  - The test fails any implementation that treats that exit status as preservation.
- **Textual conflicts.** A reconciliation whose result contains [jj conflicts](https://docs.jj-vcs.dev/latest/conflicts/) sets `result_has_conflicts` on the intent and adds no state.
  - The payload lists the conflicted commits and paths and says they must be resolved.
  - Derived cascade status is `conflicted` before and after acknowledgement.
  - It leaves `conflicted` only when a later operation's view shows the thread's chain conflict-free.
  - A textual conflict alone does not hard-pause the agent.
- **Replacement incarnation precondition.** A replacement's launch gate is not activated while a tool child of the retired harness survives in the `agent` launcher's descendant, session, or process-group set.
  - The survivor raises `OrphanedProcess` with harness-remnant evidence. It blocks the gate and workspace materialization.
  - A hard-pause terminates the harness's whole process tree by recorded identity and leaves the launcher alive.
  - Cascade restarts need no human approval.
- **`restart-agent`.** A harness that crashed under a live launcher is restarted by this `kk repair` plan.
  - The restart runs on the same launcher through a fresh gate.
  - It uses `RestartStartup` when an intent is pending.
  - It needs no approval in thread context.
  - When the launcher itself is gone the intent waits behind `TerminalMissing` repair.
- **Unknown batch after a freeze.** A tool batch was in flight at the start of a close, destroy, or repair freeze, and the operation takes verified resume. The incarnation's batch state is then unknown.
  - Kiki hard-restarts it to a clean boundary with files untouched.
  - It performs no mid-batch mutation.
- **[Follows edges](appendix-a-glossary.md#follows-edge) pin a view.** Creating a follows edge and detaching one both pin an exact operation view.
  - Both synchronously refresh the affected live heads before choosing or discarding an anchor.
  - A lagging asynchronous watcher cannot make either command lose a parent or child advance.

### Reading and changing jj at an exact operation

jj records every change to a repository as an [operation](https://docs.jj-vcs.dev/latest/operation-log/). Operations can form a branching graph, a [DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph), and its newest ends are called heads. The set of current heads is the [operation frontier](appendix-a-glossary.md#operation-frontier). A [pinned read](appendix-a-glossary.md#pinned-read) names one exact operation and does not look at the working copy.

- **Watcher restart over a branching graph.** Watcher restart from a multi-parent or divergent jj operation graph traverses all reachable, unprocessed ancestors from the persisted frontier, in [topological order](https://en.wikipedia.org/wiki/Topological_sorting). Tests must fail any implementation that stores one parent or advances one linear cursor through the operation DAG.
- **Pinned reads.** Every observation kiki makes of a managed repository names a full operation id and ignores the working copy.
  - The test runs against real jj, with a dirty working copy and with two and three operation heads.
  - These create no operation, snapshot nothing, and leave the head set byte-identical:
    - a complete watcher pass
    - a projection audit
    - `kk ls`
    - the `kk status` header
    - `kk status --no-jj`
  - The human passthroughs are the exception. The `kk` CLI, never `kkd`, runs the body of `kk status` and the overlay's `d` diff for the contextual thread in the caller's contextual workspace. They may snapshot like any direct jj use.
  - The `JjBackend` fake fails any read issued without an exact operation id, and any read issued with `--at-op=@`.
- **Frontier sampler.** The [`OpFrontierSampler`](appendix-a-glossary.md#frontier-sampler) returns every head for one, two, and three heads. It does so from the main workspace and from an added workspace whose `.jj/repo` is a pointer file.
  - A watch on the parent of the head store is shown to miss head changes.
  - An unrecognized store marker or jj version yields `Unavailable`. Then the watcher reports itself degraded, `RefreshToFrontier` [fails closed](appendix-a-glossary.md#fail-closed), and no `jj op log` fallback runs.
- **Unmerged frontier.** The [unmerged frontier](appendix-a-glossary.md#unmerged-frontier) case is when two heads disagree about a thread's `@` or bookmark. While they disagree:
  - The row caches keep the last agreed value.
  - Status prints "frontier unmerged" instead of a checkpoint relationship.
  - No projection issue is raised from one head's view.
  - A lifecycle command that needs one view integrates deliberately. It records the resulting operation in `op_attribution` with kind `Integration`, and still classifies it as a multi-parent operation.
  - When an external command merges the heads first, the merge operation is classified the same way.
- **Pinned mutation.** Bookmark moves, rebases, abandons, pushes, and `jj workspace forget` run at the exact head their plan validated with the working copy ignored.
  - `jj workspace add` runs at that exact head without `--ignore-working-copy`. It writes the workspace and its initial working-copy commit as two operations. Run while the main workspace is dirty, it snapshots nothing there.
  - An external operation injected between validation and mutation yields two heads and never a silent merge. The next sample observes both, and the saga re-validates instead of assuming its view.
  - A placement that lands beside a concurrent operation applies only to views that descend from it. The journal that made it re-places deterministically at the first integration operation instead of raising an issue.
  - The only unpinned commands are the closed list in [Invariants](02-invariants.md#operation-history-is-a-dag): the working-copy commands, [deliberate integration](appendix-a-glossary.md#deliberate-integration), and the human passthroughs.
  - Each working-copy command `kkd` runs is taken under its lock only after a single-head sample, is attributed, and is followed by a new sample.
- **Attribution.** Kiki sets no operation description.
  - Each kiki-run command carries a per-invocation operation user and host.
  - Every operation id it wrote is recorded, including both operations of one `jj workspace add`.
  - An external operation is never attributed, whatever its description says.
- **Operation history rewritten.** `jj op abandon` and `jj util gc` leave no frontier head descending from a recorded operation.
  - Kiki [re-anchors](appendix-a-glossary.md#re-anchoring) silently when every thread's bookmark and every workspace `@` equal their cached values.
  - When any differs, kiki does these things:
    - It raises exactly one repo-level [`OperationHistoryRewritten`](appendix-a-glossary.md#operationhistoryrewritten) issue listing those threads.
    - It raises no per-thread bookmark issue for the gap.
    - It blocks checkpoint, publish, close, detach, and explicit rebase for the listed threads until the repair plan re-anchors.
- **Boundary snapshot.** A [boundary snapshot](appendix-a-glossary.md#boundary-snapshot) is a snapshot of the working copy that kiki itself runs at a safe moment.
  - It is taken at agent quiescence or a held harness boundary. For a harness that cannot prove quiescence, it is taken at a lifecycle preflight.
  - It is taken under the thread lock, after a single-head sample. It is attributed and followed by a new sample.
  - Close, detach, and publish preflight take it so the pinned head contains every tracked edit.
  - A `ParentAdvance` whose probe returns `FreshDirty` takes it and proceeds only when the second probe returns `FreshClean`.
  - `StaleDirty` and `Unknown` never take it and go to recovery.
  - The probe itself never snapshots.

### Checkpoints and bookmark tracking

A thread's [bookmark](appendix-a-glossary.md#bookmark) is a named pointer that marks its last checkpoint. A [checkpoint placement](appendix-a-glossary.md#checkpoint-placement) is kiki putting the bookmark on an exact commit. When jj rewrites that commit, jj moves the bookmark to the new version, called a [native successor](appendix-a-glossary.md#native-successor). Kiki follows those moves in `bookmark_expected_commit_id`, the [expected bookmark target](appendix-a-glossary.md#expected-bookmark-target). The tests below say which moves kiki follows and which it reports as an issue.

- **Checkpoint succession, same change.** After `kk new`, the first edit and snapshot rewrites the checkpointed commit and jj moves the bookmark.
  - Kiki appends a `SameChange` row to `thread_checkpoint_successions`.
  - It advances `bookmark_expected_commit_id`.
  - It leaves `checkpoint_commit_id` and `thread_checkpoints` unchanged.
  - It raises no issue.
  - The same holds for `jj describe`, a rebase, a squash into the bookmarked commit, and an ancestor rewrite made from another workspace.
  - A chain across several unprocessed operations is proved one operation at a time.
- **Checkpoint succession, other change.** `jj split` of the bookmarked commit, and a squash of the bookmarked commit into its parent, move the bookmark to a commit with a different change id.
  - For an `Active` thread the move is accepted as `PredecessorOtherChange` only when both hold:
    - the operation's predecessor record names the old target, and
    - the new target is the exact live head or on the validated owned chain.
  - Off the owned chain it is [`BookmarkMoved`](appendix-a-glossary.md#bookmarkmoved).
  - For a `Closed` thread every different-change successor is `BookmarkMoved`.
  - Squash variants: squashing the bookmarked commit into its child, or into an earlier commit on the chain, moves the bookmark to the old target's parent while another commit records the predecessor.
    - For an `Active` thread that is accepted when two things hold. The new target is on the validated path. And a commit on that path, or the live head, records the old target as a predecessor.
    - The row names that evidence commit.
    - Evidence may come from the classified operation. It may also come from an ancestor of it that is not an ancestor of the operation that established the expected target.
- **Closed-thread succession.** An ancestor rewrite from another workspace rewrites a closed thread's checkpointed commit.
  - Kiki accepts the `SameChange` successor and advances the archived `thread_head_commit_id` in the same transaction.
  - So `bookmark_expected_commit_id == thread_head_commit_id` still holds and the thread stays `Closed`.
- **Successor evidence is required.** Each of these is `BookmarkMoved`:
  - a move to a commit with the same tree or description but no operation predecessor record
  - a move while the old target is still visible
  - an operation whose predecessor record is absent
  - `jj bookmark move`
  - a sideways move
  - a backward move that is not an undo of a tracked rewrite
- **[`BookmarkConflicted`](appendix-a-glossary.md#bookmarkconflicted).** Two situations produce divergent successors and a conflicted bookmark:
  - two operations that each rewrite the checkpointed commit and then merge
  - a dirty `jj workspace update-stale` on a workspace whose `@` carries the bookmark
  - Both are `BookmarkConflicted`, never a chosen successor.
  - The conflict flag is tested before the unchanged-target rule. A bookmark that jj marks conflicted while its only target is still the expected target is `BookmarkConflicted`, not unchanged. That happens:
    - after one divergent side is abandoned, or
    - after a fetch that deleted the tracked remote bookmark while the local one had moved.
- **External bookmark rename.** One operation that removes the thread's bookmark name and adds exactly one new local name on the expected target is a normalization. That is so provided the operation changes no remote or `@git` bookmark and is not an import or fetch.
  - Kiki adopts the new name on the thread row.
  - It appends a `thread_bookmark_renames` row and appends no placement row.
  - It raises no issue and keeps the thread's lifecycle.
  - Each weaker case is [`BookmarkMissing`](appendix-a-glossary.md#bookmarkmissing):
    - two new names in that operation
    - a new name on a different target
    - a name another thread already holds
    - a delete followed by a create in a later operation
    - the old name still present in the view
    - a fetch or colocated Git import that removes one name and adds another on the same commit
    - a rename of a published thread, whose tracked remote bookmark keeps the old name
- **Abandoned checkpoint.** `jj abandon` of the checkpointed commit deletes the bookmark and is `BookmarkMissing` with evidence `CheckpointAbandoned`.
  - A fetch after a merged [pull request](https://docs.github.com/en/pull-requests)'s branch was deleted abandons the unreachable checkpointed commit and deletes the bookmark. That is the same issue, for an active thread and for a closed one.
  - Its plans are to make the commit visible again and re-place the bookmark on it, or, for a closed thread, to destroy.
  - When the abandoned commit is also a live head or an owned revision, follows classification records `TopologyDiverged` independently. Neither result suppresses the other.
- **Unresolved bookmark issue.** While a bookmark issue is unresolved, later bookmark observations are recorded on that issue and no succession row is appended.
  - Head tracking and follows classification continue.
  - The issue resolves automatically, with no plan, when a later operation shows the bookmark unconflicted on the expected target.
- **Undo rule.** After a tracked `jj describe` rewrite, `jj undo` returns the bookmark to the earlier commit while the later one becomes hidden.
  - Kiki appends a `Reverted` succession row, sets the expected target back, and raises no issue.
  - `jj redo` is handled the same way, and so is `jj commit` followed by `jj undo`.
  - A backward move to a commit that is not in the placement's own history, or while the later commit is still visible, is `BookmarkMoved`.
- **Restore never targets a hidden commit.** For `BookmarkMissing`, `BookmarkMoved`, and `BookmarkConflicted`, no restore plan is offered while the expected target is hidden. A test that forces one shows the divergent change it would create and fails.
- **Checkpoint target rule.** Every checkpoint places the bookmark on its [checkpoint target](appendix-a-glossary.md#checkpoint-target). That is the live head, or its parent when the head is an empty, undescribed working-copy commit whose parent is on the owned chain.
  - Creation places it on the initial commit itself.
  - A checkpoint whose target is neither equal to nor a descendant of the expected target refuses without mutating.
  - Only a separately approved backward or sideways plan passes `--allow-backwards`.
- **Checkpoint relationship.** The [checkpoint relationship](appendix-a-glossary.md#checkpoint-relationship) says where the live head sits compared with the expected target:
  - `current` when the expected target equals the head, and when the head is an empty, undescribed working-copy commit on top of it (right after `jj commit` and right after `kk reopen`)
  - `behind` for any other descendant head
  - `ahead` after `jj edit` of an earlier commit
  - `diverged` otherwise
  - An unregistered descendant of the chain changes neither the relationship nor successor tracking. It blocks only rebase and abandon plans.
- **Classification runs on kiki's own operations.** An explicit `ParentAdvance` rebase that carries a child's and a grandchild's bookmarks appends a succession row for each affected thread. It opens no second cascade intent for the attributed operation.
- **Journaled checkpoint.** A journaled lifecycle checkpoint appends exactly one `thread_checkpoints` row and resets the expected target to the placed commit. A checkpoint placed on a workspace with unsnapshotted edits is followed by a `SameChange` succession at the next snapshot, not by an issue.

### Rendering

- `LogRenderer` and `StatusRenderer` produce output that stays readable in monochrome when [`NO_COLOR=1`](https://no-color.org/) is set. Every state in the cascade, agent, and lifecycle vocabularies has a distinct glyph or label that does not depend on color.

## Cascade crash tests

A cascade is how kiki carries a parent [thread](appendix-a-glossary.md#thread)'s changes into the threads that follow it. These tests crash a program in the middle of a cascade and check what is left.

Some terms used in this section:

- An intent ([`sync_intent`](appendix-a-glossary.md#sync-intent)) is the durable record of one cascade reconciliation.
- A [tool batch](appendix-a-glossary.md#tool-batch) is the group of tool calls the agent sends together.
- `PreToolUse` and `PostToolBatch` are kiki's [hook entry points](appendix-a-glossary.md#pretooluse-posttoolbatch-hooks). They run before each tool call and after a batch finishes.
- An [incarnation](appendix-a-glossary.md#incarnation) is one launch of the [harness](appendix-a-glossary.md#harness) process.
- [`kkd`](appendix-a-glossary.md#kkd) is kiki's background [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>).

The cascade tests must cover each case below.

### Hook crashes and delivery

- a hook crash before it writes stdout
- a pre-stdout hook crash followed by a newly enqueued cascade
- a crash between stdout and `MarkDelivered`
- a crash after `MarkDelivered`
- an agent crash after delivery but before acknowledgement
- a resume with a delivered-but-unacknowledged intent
- multiple cascades before the first hook, coalescing into one delivery
- deliverable-intent lookup and byte-identical retry for both `Materialized` and `Delivered`
- daemon crash and recovery at every `sync_intent` state, including `RecoveryRequired`

### Batch admission

- Two or more concurrent `PreToolUse` calls [race](https://en.wikipedia.org/wiki/Race_condition) to reconcile the same intent.
  - Exactly one [materialization](appendix-a-glossary.md#materialization) occurs.
  - Every call in the triggering batch is blocked.
- Permutations in which each logical tool is the first hook to arrive for a batch with pending work.
  - Whichever arrives first fixes `Block`.
  - No arrival order lets a sibling tool execute.
- A batch whose first admission is [`PassThrough`](appendix-a-glossary.md#batch-admission).
  - An intent detected before a later sibling hook is deferred to the next batch.
  - It does not partially block a batch that was already admitted.
- A [hook launcher](appendix-a-glossary.md#hook-launcher) or daemon restart after a `PassThrough` admission loses the cache.
  - An unknown in-flight batch leaves files untouched and hard-restarts the incarnation to establish a clean boundary.
  - An active durable `Block` stays [fail-closed](appendix-a-glossary.md#fail-closed).
- A concurrent sibling `PreToolUse` arrives after payload emission but before `MarkDelivered`.
  - It receives the byte-identical payload.
  - It cannot acknowledge the intent.

### Batch completion and acknowledgement

- Matching, duplicate, stale, missing, and reordered `PostToolBatch` events.
  - Only the matching event marks batch completion.
  - None of them acknowledges delivery.
- A new batch in the same [model turn](appendix-a-glossary.md#model-turn) after `PostToolBatch`. It cannot acknowledge merely because its batch id differs.
- The first `PreToolUse` from a provably later model turn.
  - It acknowledges the delivered intent.
  - It then evaluates the next ordered intent before deciding whether its tool may run.
  - If `MarkDelivered` was lost, the same exact proof atomically repairs delivery and advances `Materialized -> Acknowledged`.
- Hook, daemon, and agent crashes before and after durable barrier creation, and before and after `batch_completed_at`. Ambiguous completion always hard-restarts with the saved payload.

### Hard restart

- The hard-restart fallback when an adapter cannot expose an unambiguous batch-completion boundary.
  - The replacement row and the byte-stable startup payload are durable before the harness starts.
  - The payload is the replacement's first startup message.
  - Its first managed boundary proves startup processing before acknowledgement.
  - No interrupted tool is replayed automatically.
- A process restart with a reused harness session id.
  - It retires the old runtime incarnation without acknowledgement.
  - It re-proves exclusive hook control.
  - It injects the saved payload before any replacement-process tool may run.
  - A crash before its first boundary redelivers to another replacement.

### Workspace probe and recovery

- [`WorkspaceProbe`](appendix-a-glossary.md#workspaceprobe) returning `FreshClean`, `FreshDirty`, `StaleClean`, `StaleDirty`, and `Unknown`, plus fingerprint drift immediately before mutation.
- `jj workspace update-stale` in each of these situations:
  - with clean files
  - with unsnapshotted edits (a successful exit that leaves the edits only in another divergent successor)
  - with conflicts
  - with direct materialization that creates no new operation
  - with direct materialization in a [colocated](https://docs.jj-vcs.dev/latest/git-compatibility/) repository that creates one
  - with a concurrently advanced [base transition](appendix-a-glossary.md#base-transition)
- Recovery verifies edit-bearing divergent successors before choosing the visible result. Ambiguous recovery requires a human to choose.
- `--no-integrate-operation` plus `jj op integrate` feasibility for a planned [`ParentAdvance`](appendix-a-glossary.md#parentadvance), including concurrent external operations.

### Worked scenarios

They must also cover the six worked scenarios in [Cascade](05-cascade.md#worked-scenarios):

1. a clean ancestor rewrite
2. an ancestor rewrite after an agent edit
3. a parent adding a revision
4. direct human reconciliation
5. an agent crash after delivery
6. a parallel tool batch

These are scenario tests over observable state, not assertions about private function boundaries.

## Module-specific obligations

Each module below has its own list of things its tests cover.

### `MetadataLedger`

`MetadataLedger` tests cover:

- content-hash ownership
- trailer independence
- sticky renames of human bookmarks
- squash inheritance toward human ownership
- opt-back-in refresh

### `AuthEnforcer` and `ApprovalBroker`

`AuthEnforcer` and `ApprovalBroker` tests cover thread-scoped rejection across siblings and operational rejection of Admin. They also cover:

- broker enrollment
- persisted begin/display/confirm/cancel challenges
- binding of the [nonce](https://en.wikipedia.org/wiki/Cryptographic_nonce), channel, method, target, arguments, and rendered plan
- atomic [capability](https://en.wikipedia.org/wiki/Capability-based_security) issuance after confirmation
- atomic claim with one durable operation id
- crash resume of only that plan
- final consumption
- expiry and replay
- plan-digest drift
- non-interactive failure

Audit tests cover accepted, rejected, unidentified, bootstrap, registration, invalid-repo, and `ListRepos` attempts. Each attempt writes exactly one row. The row is routed to the per-repo or per-user [SQLite](https://www.sqlite.org/) sink. Nullable credential and approval identities are represented explicitly.

### `ThreadTranscriptStore`

The [thread transcript](appendix-a-glossary.md#thread-transcript) is kiki's locally stored record of the conversation in a thread. `ThreadTranscriptStore` tests cover:

- FTS ([full-text search](https://www.sqlite.org/fts5.html))
- author and direction preservation
- change-aligned reads
- tombstoned and redirected changes
- recovery from [JSONL](https://jsonlines.org/) rotation and truncation
- offset and row insertion in one [transaction](https://en.wikipedia.org/wiki/Database_transaction)
- prevention of [reopen catch-up](appendix-a-glossary.md#catch-up) recursion
- [`pending_kkd_prepends`](appendix-a-glossary.md#pending-kkd-prepends) FIFO (first-in, first-out) matching
- [idempotent](https://en.wikipedia.org/wiki/Idempotence) cascade-injection rows
- intent-pinned anchors

Provider-egress cases are about transcript text sent to a model provider. They cover:

- first consent
- remembered consent
- revocation
- a configured-provider change
- local preview without egress
- denial of same-thread transcript [MCP](https://modelcontextprotocol.io/) until an active purpose-bound grant exists

### `LogRenderer`

[`LogRenderer`](appendix-a-glossary.md#logrenderer) tests cover:

- stack-aware expansion
- collapsed siblings and unrelated threads
- `--no-stack`
- `--all`
- `--wide`
- `-r <revset>` disabling collapse (a [revset](https://docs.jj-vcs.dev/latest/revsets/) is jj's query language for picking revisions)
- parser errors when `-r` is combined with collapse flags

### `StatusRenderer`

[`StatusRenderer`](appendix-a-glossary.md#statusrenderer) tests cover:

- the exact [live head](appendix-a-glossary.md#live-head)
- the checkpoint [bookmark](appendix-a-glossary.md#bookmark) and its expected commit (`bookmark_expected_commit_id`)
- the `current | behind | ahead | diverged` [checkpoint relationship](appendix-a-glossary.md#checkpoint-relationship), computed purely from that expected commit and the live head, including:
  - `current` right after `jj commit` and `kk reopen`
  - `behind` once the head has content or a description
  - `current` after a tracked native succession
  - `ahead` after `jj edit` of an earlier commit
  - `diverged` for every other relation
- unresolved bookmark issues listed by name beside the relationship without changing it
- "frontier unmerged" printed in place of the relationship while heads disagree
- omission of unavailable v1.x PR fields
- follows and children rows
- the three-valued cascade state
- `--diff`
- `--diff --stat`
- `--no-jj`

### `TerminalRuntime`, `TerminalClient`, and `ProcessSupervisor`

These are the [three modules](appendix-a-glossary.md#terminalruntime-terminalclient-processsupervisor) that face the terminal runtime and the operating system.

`TerminalRuntime` tests cover:

- capability derivation from the version, protocol, and object of named flags the ping reply returns, including that `live_handoff: true` is not read as support
- `ensure_server` with configuration regeneration and validation
- rejection of a handle from another [server instance](appendix-a-glossary.md#server-instance) before any call
- the provisioning protocol under lost replies and crashes
- `subscribe`-then-`snapshot` ordering, with the snapshot built from the session snapshot plus per-pane process queries and re-read from the OS
- a capability-gated `fence` whose returned guard releases the fence when dropped
- one-way presentation publishing
- `notify` as a global toast whose reply is not a display receipt

`TerminalClient` tests cover:

- caller resolution
- the three `FocusOutcome` values
- verification of the server's peer identity against the [terminal target](appendix-a-glossary.md#terminal-target)
- `kk attach` connecting in connect-only mode to the named session after `kkd` ensured the server

`ProcessSupervisor` tests cover every result type's `Unknown` outcome and the evidence each result carries. They also cover:

- `terminate` taking recorded identities through stop, verify, kill
- `reprove` over a `FrozenSet` rebuilt from rows
- the filesystem watch handle belonging to the `FrozenSet`

### UI controllers

`UiPaneController`, `OverlayController`, `ToastQueue`, `FormController`, and `PaneLifecycle` tests cover:

- navigation versus consequential-action gating
- contextual-thread previews versus exact sibling-read approval
- daemon-issued approval cards
- disconnected and reconnecting rendering
- cursor preservation across event streams
- toast TTL/click/action behavior
- spawn form navigation
- terminal-too-narrow warnings
- rejection of repo-shared `[ui]` config

`PaneLifecycle` covers the `shell` and `ui` [role panes](appendix-a-glossary.md#role-pane):

- Each is ensured at creation, at `kk reopen`, and at a terminal-restart repair.
- Neither is re-ensured at `kk switch` or respawned after the user closes it.

`UiPaneController` drives the Stack tree in the optional [`ui` role pane](appendix-a-glossary.md#ui-role-pane), which never receives a toast.

`LogRenderer`, `StatusRenderer`, the overlay, and the `ui` pane render lifecycle, cascade, and [agent display states](appendix-a-glossary.md#agent-display-states) through one shared renderer. A golden test compares output against a saved, known-good copy. Here it asserts that the same summary row produces the same glyph and label on every surface.

If that pane is the only visible kiki surface, eligible events use the OS-notification fallback, while durable row state remains visible.

### Publishing

Publishing tests prove that the first publishing tranche uses a human-authored or static template, not transcript or AI drafting.

- Parent-merge local reconciliation may complete without approval.
- Force-push and PR-base mutation remain a pending named remote plan until a foreground one-shot approval claims it.
- A failure retains the [follows edge](appendix-a-glossary.md#follows-edge) and is safe to retry.

## Fakes

Deep-module tests should use fakes for the dependencies below. A fake is a stand-in implementation that acts like the real dependency but runs in-process.

- `JjBackend`
- `TerminalRuntime`
- `TerminalClient`
- `ProcessSupervisor`
- `GitHubBackend`
- `Harness`
- `TranscriptAdapter`
- notification sink
- clock
- filesystem event source

The fakes should expose edge cases directly:

- op storms
- hook crashes
- parallel tool batches
- concurrent hook arrival
- missing and reordered batch completion
- model-turn identity
- settings-source discovery
- JSONL rotation
- out-of-order timestamps
- remote divergence
- agent session restart

The terminal fakes expose:

- lost replies after a successful create
- duplicate groups
- recurring and restored ids
- a changed server instance
- lost events
- renamed labels and clobbered tokens
- a silently ignored unknown parameter
- a success reply with surviving processes
- a growing process set
- an external workspace holder

## Integration-only surfaces

Some parts can only be tested for real, against the actual programs. These are smoke-tested or integration-tested:

- the real [`jj`](https://docs.jj-vcs.dev/latest/)
- [`gh`](https://cli.github.com/)
- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview)
- [Codex](https://github.com/openai/codex)
- the [ratatui](https://ratatui.rs/) terminal loop
- real [Herdr](appendix-a-glossary.md#herdr) at the pinned candidate build
- real OS process inspection behind `ProcessSupervisor`
- the fsnotify watcher (file-change notification)

The Herdr integration runs against a disposable [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) and never the user's default Herdr server. Its unproven gates are listed in [Terminal runtime](13-architecture/terminal-runtime.md#what-exists-what-kiki-builds-what-herdr-must-add).

Each shipped [harness](appendix-a-glossary.md#harness)'s integration is still a release gate.

- For Claude Code, the gate covers:
  - exclusive `PreToolUse` settings isolation
  - stable model-turn and tool-batch identity
  - concurrent hook behavior
  - `PostToolBatch` completion
- For Codex, the gate covers:
  - `CODEX_HOME` isolation with kiki's hooks pre-trusted
  - the serial-dispatch proof
  - byte-identical visibility of deny payloads
  - `Stop`/`SessionStart` lifecycle behavior

An upstream version that fails its probes uses hard restart or is unsupported. It is never modeled optimistically.

Core interpretation logic belongs in deep-module tests against fakes.
