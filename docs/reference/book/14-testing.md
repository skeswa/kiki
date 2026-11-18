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
- `kk init` succeeds when [`gh`](https://cli.github.com/) is missing or unauthenticated. The first GitHub-backed command performs the check. It reports an error that says what to do, without corrupting local state.
- **Headless first run.** A machine with no human and no desktop session finishes setup from flags alone. ([Headless](appendix-a-glossary.md#headless) means no screen attached, no person present, or both.)
  - [`kk daemon install`](09-commands.md#kk-daemon-install) installs and starts `kkd` without asking a question. A first install needs no credential. It creates the Admin bootstrap credential and prints its path. A second run creates no second credential. A later run that changes an existing installation is refused without a foreground confirmation or `--admin-credential-file`. Under `kkd --foreground`, the first start creates the credential and logs its path.
  - `kk automation apply --admin-credential-file <path>` activates the [automation policy](appendix-a-glossary.md#automation-policy). `kk automation credential create <name> --admin-credential-file <path>` creates an [automation credential](appendix-a-glossary.md#automation-credential).
  - `kk init` run with that automation credential begins its approval with that credential, not with Admin. It succeeds under a matching `init` rule. With no `init` rule it exits with code 3 and registers nothing.
  - No presenter is enrolled at any point in the run.
  - Retry an installation change after writing the new definition but before reload, while the old daemon still answers. The retry finishes the existing journal and verifies the running version.
  - For an install change, try a stale definition, a lost response, and a daemon restart after the definition is written. Verify the old or requested definition, one journaled change, and the existing Admin identity. An unreachable installed daemon cannot authorize an overwrite.
  - At a terminal, the first-run question about installing the daemon is still asked.
- **No prompt without a terminal.** With no terminal, `kk` never prompts.
  - Each command that would ask a question fails instead, changes nothing, and names the flag that answers the question. The cases include the target of [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target), the daemon install question, and presenter enrollment.
  - The same command with that flag runs with no terminal.
  - No `--yes` flag, piped confirmation, environment variable, or reusable token produces an approval. Unattended approval comes only from the activated policy.
- **[Exit codes](09-commands.md#exit-codes).** One case observes each code:
  - `0` for success;
  - `1` for an operation that failed;
  - `2` for a usage error;
  - `3` for an approval that is needed when none is available;
  - `4` for a refusal by a precondition or a safety proof, including `kk switch` with `NoCallerClient`;
  - `5` for a daemon that is unreachable or not installed;
  - `6` for a timeout.
- **[`--json`](09-commands.md#output-for-scripts).** Every read command, and the final result of every other command, can be printed as JSON.
  - The flag changes rendering only. The same command with and without it makes the same daemon calls and the same state changes.
  - The output parses as JSON, and it carries every fact the plain rendering shows.
  - A refused or failed command still prints a JSON result and keeps its exit code.
- **[`kk events`](09-commands.md#kk-events).** The command is the CLI face of the event streams.
  - `kk events --thread <t>` prints the events `StreamThreadEvents` serves for that thread, in sequence order.
  - Without `--thread` it prints the repo-wide events that `StreamRepoEvents` serves.
  - `--since <seq>` starts after that sequence number, with no gap and no repeated event.
  - `--follow` keeps the stream open and prints new events as they happen. Without it the command prints what exists and exits 0.
  - `--json` prints each event as JSON.
  - On adapters with proven `attention_events`, a harness permission prompt produces `agent_blocked` in the stream. Without that proof, use a crash to test the blocked state. Kiki never answers the harness's own prompt.
  - All of this works with zero attached Herdr clients.
- **[`kk wait`](09-commands.md#kk-wait).** `kk wait [<thread>] --for <state>` blocks until the thread reaches the state.
  - Each state is covered: `quiescent`, `goal-complete`, `blocked`, `conflicted`, `closed`, and `issue`.
  - It exits 0 when the state is reached, and at once when the thread is already in it.
  - It exits 6 when `--timeout` runs out first.
- **The `command` notification provider.** `[notifications] command` names a program that `kkd` runs for each `loud` [attention event](appendix-a-glossary.md#attention-event).
  - With `os_provider = "command"`, `kkd` runs the program once per `loud` event, with the event as JSON on its standard input.
  - A `soft` or `silent` event does not run it.
  - A program that runs past the short timeout is stopped. A timeout or a non-zero exit is not retried, and it does not hold back the event's status mark or its `kk events` row.
  - Only the user config file can set `command`. A value from a repo, thread, environment, or `--config` layer does not take effect.
  - `os_provider = "auto"` on a host with no desktop session resolves to `command` when `command` is set, and to `off` when it is not.
- If a thread's workspace directory is deleted out of band, the thread records `ProjectionDiverged { reason: WorkspaceDirectoryMissing }` at daemon boot or `kk ls`.
  - It fires exactly one notification.
  - It is neither recreated nor reclassified automatically.
- **The three workspace issues and their repairs.** Each issue is raised once, blocks boundary mutation for that thread, and is cleared only by its named `kk repair` plan.
  - `WorkspaceDirectoryMissing`: the directory is gone. [`recreate-workspace`](appendix-a-glossary.md#recreate-workspace) rebuilds the workspace from the checkpoint.
  - `WorkspaceRecordMissing`: jj's workspace record is gone (for example after a direct `jj workspace forget`) while the directory remains. [`reattach-workspace`](appendix-a-glossary.md#reattach-workspace) restores the record.
  - `WorkspacePathMismatch`: the workspace is at a different path than kiki recorded. [`repoint-workspace`](appendix-a-glossary.md#repoint-workspace) updates the recorded path. Kiki corrects the path by itself only when the stable jj workspace id uniquely identifies the same filesystem object.
  - After each repair the thread keeps its `thread_id`, its bookmark, and its lifecycle history.
  - A plan computed for one issue goes stale when the observed state changes, and a stale plan is refused.
- **Thread identity is stable.** One thread keeps the same `thread_id` through all of these:
  - close and reopen
  - a `restart-terminal` repair and a `restart-agent` repair
  - adoption of an external bookmark rename
  - Its credentials, [terminal binding](appendix-a-glossary.md#terminal-binding), incarnation, and workspace directory may all change across them. Its audit rows, checkpoints, and follows edges stay attached to the one id.
  - No test finds a thread by its bookmark name, workspace path, or Herdr id.

### Codex boundary proof

- **Codex serial-dispatch proof.** The Codex adapter/version fixture proves its boundary before `parallel_batch_boundary` is claimed. The proof covers the following.
  - **Serial dispatch.**
    - No two tool calls of one turn run concurrently. That includes calls originated by subagents.
    - A new tool is requested only after the model has consumed the previous call's result.
  - **Deny behavior.**
    - A deny decision returns the saved payload to the model byte-identically, and the denied tool never executes.
    - A barrier is a block that holds the agent's [tool batch](appendix-a-glossary.md#tool-batch) during reconciliation. Once `kkd` has admitted a call into a reconciliation, `kk-hook` waits up to `[timeouts] slow_path`. If that expires, or the reconciliation's owner crashes, it answers with a generic blocking deny. So a barrier-covered call never fails open.
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
    - Hook death before stdout: the tool does not run as if the hook had allowed it, the model sees a generic result, and the contrary receipt redelivers on the arriving batch.
    - Stdout written but timed out or rejected by the harness: `MarkDelivered` is recorded, the receipt is contrary, and the intent is redelivered. It is never acknowledged.
    - Persistent output rejection:
      - A second contrary receipt for the same intent fails over to [`RestartStartup`](appendix-a-glossary.md#restartstartup-delivery-proof) instead of redelivering again.
      - Exhausted bounded restart attempts [hard-pause](appendix-a-glossary.md#hard-pause) with a loud [attention event](appendix-a-glossary.md#attention-event) rather than looping.
    - Daemon restart between and after those attempts: the attempt history and exhaustion state are read from the intent.
      - So a restart after the first contrary receipt still treats the next one as the second.
      - A restart after exhaustion re-surfaces the blocked thread without minting a new attempt.
    - The two repair exits:
      - A [`retry-delivery`](appendix-a-glossary.md#retry-delivery) plan re-arms exactly one fresh bounded cycle by incrementing the [delivery epoch](appendix-a-glossary.md#delivery-epoch). So bounds count only attempt rows stamped with the current epoch. A prior-epoch row can never consume the fresh cycle. No bound ever compares timestamps, even under clock skew or rollback.
      - A [`discard-delivery`](appendix-a-glossary.md#discard-delivery) plan acknowledges without delivery proof only under a one-shot approval bound to that plan, and records the resolution with the approval that allowed it.
      - No other write is accepted against an [exhausted intent](appendix-a-glossary.md#exhausted-intent).
    - Receipt unreadable at the completing arrival: acknowledgement defers when no delivery is pending, and takes `RestartStartup` when one is.
    - Matching receipt: acknowledge.
  - **Beyond the fault cases.**
    - The generated config pins the harness-side hook timeout above `[timeouts] slow_path` (the [slow-path bound](appendix-a-glossary.md#slow-path-bound)) plus a margin.
    - The fixture proves the session record durably contains deny results exactly as returned to the model.
    - Every workspace-observing tool in the pinned version fires `PreToolUse` or is disabled by the generated config.

### Creation, launchers, and provisioning

A [pane launcher](appendix-a-glossary.md#pane-launcher) is the kiki process that starts first in each pane kiki sets up. It waits at a [launch gate](appendix-a-glossary.md#launch-gate) until `kkd` lets it start the harness.

- **Creation crash injection.** Crash injection at every creation [journal](appendix-a-glossary.md#lifecycle-journal) step leaves the thread in `Creating` or `CreateFailed`.
  - Gate activation and harness start remain `Creating`.
  - Only the matching [ready handshake](appendix-a-glossary.md#ready-handshake) may enter `Active`.
  - The pane launcher cannot pass its database-backed gate before these are durable: the credentials, exclusive hooks, [live head](appendix-a-glossary.md#live-head), checkpoint, and a `Bound` [terminal binding](appendix-a-glossary.md#terminal-binding).
  - Accepting a launcher and activating a gate are separate transactions.
    - Each launcher report is handled when it arrives, in one transaction per report. That transaction accepts that launcher for `(provision_id, role)` and records its OS-read process identity. No table of pending reports exists.
    - The binding becomes `Bound` in the transaction that accepts the `agent` claim, and in no other.
    - The gate transaction records the incarnation and activates its gate. It is refused without a `Bound` binding.
  - `agent` is the only [required role](appendix-a-glossary.md#required-role).
    - A `shell` or `ui` launcher that does not report within `[timeouts] launcher_report` is recorded as absent and raises a warning. Provisioning still succeeds.
    - A missing `agent` report within that bound fails provisioning.
  - The [provision nonce](appendix-a-glossary.md#provision-nonce) (a one-use secret) reaches the launcher only through its launch [environment](https://en.wikipedia.org/wiki/Environment_variable).
    - It never appears in argv or in Herdr's saved state.
    - Only its hash is stored.
    - It is rotated before any re-issued create call.
  - The harness is always the launcher's child.
    - It is started from the [launch specification](appendix-a-glossary.md#launch-specification) `kkd` computed through `Harness::launch_spec`.
    - The launcher never replaces itself with the harness.
    - The launcher holds the child before exec until `ReportHarnessStarted` has recorded its identity. So a crash at any point leaves either no harness or a recorded one.
    - `ReportHarnessStarted` is idempotent. A repeat from the same launcher, for the same incarnation and the same child identity, is accepted as a no-op.
    - A launcher that already holds a recorded child ignores a re-delivered gate specification. It starts no second child and reports the existing one.
    - A report naming a different child for an incarnation that already has one is refused.
  - The ready handshake arrives from `kk-hook` at the harness's session-start event.
    - Both generated harness configurations declare that session-start hook. For each harness it fires exactly once per incarnation, before any tool, on a fresh start and on a resume. A harness version that fails this is unsupported.
    - Its commit re-reads the launcher's OS identity and the open `terminal_servers` row.
    - A launcher or server that changed in between fails the handshake.
    - A handshake that has not arrived within `[timeouts] ready_handshake` of the launch is `CreateFailed`. In a restart it is that restart's failure.
- **Launcher report acceptance.** `kkd` accepts a launcher's start report only from the real root process of the reported pane.
  - A `ReportLauncherStarted` is accepted only when both of these hold:
    - the caller's [peer-credential](https://man7.org/linux/man-pages/man7/unix.7.html) identity has the current [server instance](appendix-a-glossary.md#server-instance)'s process as its parent, and
    - a fresh per-pane process query shows the reported pane's root [pid](https://en.wikipedia.org/wiki/Process_identifier) is that caller.
  - Refused cases:
    - a process that is not a pane root presenting a copied nonce
    - a launcher left over from a previous server instance reporting after a restart
    - a launcher reporting a pane id that belongs to another process
    - a different process presenting for a role that is already consumed; it must exit
    - a launcher reporting from a different Herdr workspace than the binding's first accepted launcher
  - Reports are idempotent, so a retry after a lost reply is accepted.
    - A repeat of an accepted report from the same peer process identity `(pid, start_time)` gets the same answer again.
    - The repeat writes no second row and claims nothing new.
    - A process with the same pid but a different start time is a different process and is refused.
  - After its claim is accepted, a launcher's calls are authenticated by the accepted peer process identity.
    - Rotating the thread credential when an incarnation ends does not close `SuperviseLauncher`.
    - It does not reject that launcher's `ReportHarnessExit` either.
  - Two non-`Ended` bindings can never name the same `(server_instance_id, group_ref)`.
  - The [final proof](appendix-a-glossary.md#final-proof), before anything is terminated, includes a fresh observation. The observation shows that each listed container still holds its recorded launcher process, if it had one, and exactly the processes recorded at the freeze. That is the same check for a bound group, a [remnant container](appendix-a-glossary.md#remnant-container), and an [unbound container](appendix-a-glossary.md#unbound-container). Otherwise nothing is terminated and no close request is sent.
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
  - Kiki's own protocol restarts, a cascade hard restart or `RestartStartup` replacement, need no `HumanApproval`.
  - The `kk repair` plan [`restart-agent`](appendix-a-glossary.md#restart-agent) restarts a crashed harness on the live launcher. It uses `RestartStartup` when an intent is pending. It needs no approval in thread context.
  - When the launcher itself exits, or its binding or server instance is lost:
    - The `agent` role ends.
    - The thread raises [`TerminalMissing`](appendix-a-glossary.md#terminalmissing).
    - The restart plan needs approval.
    - In an agent-only group the launcher's exit also removes the Herdr workspace. Kiki reads that from a snapshot, not from a workspace-closed event.
  - A harness killed without a report is found by `ProcessSupervisor` and handled as a harness exit.
  - A group whose `agent` launcher died while a `user` pane kept the group alive is an [unbound container](appendix-a-glossary.md#unbound-container). Its processes are terminal members and raise no orphan issue.
  - "The launcher answers" is tested as both conditions: its OS identity is alive and not stopped, and its supervision stream is open. A stopped launcher with an open stream does not answer.
- **Replacement-incarnation remnant check.** A retired harness leaves a tool child running in the launcher's descendant, session, or [process-group](https://en.wikipedia.org/wiki/Process_group) set.
  - The replacement's gate is not activated and no materialization runs.
  - The thread raises [`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess) with harness-remnant evidence.
  - The remnant counts as an orphan even though kiki never recorded it. Any descendant of a live `agent` launcher, other than the launcher, is a remnant while no incarnation is live.
  - Hard-pause and `terminate` record and cover the harness's whole process tree, so the ordinary path leaves no remnant.
  - The test injects one that escaped the tree but stayed in the session.
  - The [`terminate-orphans`](appendix-a-glossary.md#terminate-orphans) plan clears it. See **Orphan recovery** below.
- **Hard pause is journaled.** `agent_sessions.pause_state` moves `None → Stopping → Stopped → Killed`.
  - `Stopping` is written before any process is signalled.
  - `kkd` is killed at each state in turn. Recovery rolls the hard pause forward to the kill every time.
  - Recovery never continues a harness that was being retired, and never returns its incarnation to service.
  - The launcher stays alive throughout.
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
  - A launcher whose own report reply was lost sends the report again. The repeat comes from the same process identity, so it is accepted with the same answer.
  - A fault that produces two terminal groups for one `provision_id` ends with exactly one accepted launcher per `(provision_id, role)` and one gate claim.
  - Every other launcher is a different process presenting for a consumed role. It is refused and exits without starting anything.
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
  - Close a follower with an incoming pending intent. Verify deferral or exact approved discard, then advance its parent while it is closed. Reopen independently with no stale delivery. Repeat with a late transition at the post-freeze check and with a crash after edge removal.
  - Crash injection at every step either adopts the exact resource, compensates back to `Closed`, or records a stable repair plan.
  - It never exposes `Active` before a matching ready handshake.
  - Every new incarnation independently re-proves exclusive hook control.
- **Close wants a quiet agent.** [Agent quiescence](appendix-a-glossary.md#agent-quiescence) is the harness adapter's proof that the agent is idle.
  - Where the adapter proves agent quiescence, `kk close` preflight requires it. With a working agent, preflight reports that and exits with no mutation, no freeze, and no approval challenge.
  - For an adapter version with `quiescence_detection: false`, preflight proceeds with a warning. A working agent then produces [approval drift](appendix-a-glossary.md#approval-drift) and a [verified resume](appendix-a-glossary.md#verified-resume), never a loss.
  - Begin or refuse a dirty close. Verify the workspace bytes, operation frontier, checkpoint and descendants are unchanged. Authorize only `snapshot`, prepare the workspace, then decline close. Verify the new head is recorded and the agent remains active.
- **No quiescence proof.** These hold for an adapter version with `quiescence_detection: false`:
  - `kk ls` shows `working` whenever the harness is alive and not blocked.
  - It never shows `idle` or `finished`.
  - A child with fresh tracked edits needs a separate snapshot approval before the parent can close. The snapshot waits for a proven boundary.
- **Codex permissions without a desktop.** With an empty workspace config and different settings in the real Codex home, launch with the documented user-config arguments. Verify a permitted workspace edit and a denied request outside the sandbox without a prompt. Repeat after reopen and replacement. Check that a conflicting launch argument cannot replace the generated home or hooks.
- **Follow-up prompt.** On each real supported harness, submit a multiline prompt with command-like text and no attached viewer. Verify one literal user turn with the expected request id in the original conversation. Try a permission prompt between preflight and submission, a busy agent, a pending barrier, an incarnation change, and an unauthorized caller. None receives input. Lose the reply, restart the daemon, then retry concurrently with the same request id. Prove at most one turn and return its receipt when available. Refuse changed text under the same id. No prompt body appears in summaries or audit arguments.
  - Run `kk prompt B` from unrelated thread A with only a `thread:self` allow rule. Verify refusal, then allow the cross-thread plan explicitly. After credential replacement, retry the old request id and verify refusal without a second turn.
  - Leave an intent `Delivered` after the turn’s final tool call. Submit a prompt with no viewer. Verify that it starts the next turn and that acknowledgement waits for the proven hook evidence.
- **Permission-prompt signal.** With `attention_events` proved, the named harness event makes the agent read `blocked`. Without that proof, a permission prompt changes nothing, and a crash still gives `blocked`.
- **Close freeze and step order.** Close finds every process to freeze, records each one before signalling it, and runs its steps in a fixed order.
  - Roots:
    - Close takes its roots from every pane in the terminal group, [role panes](appendix-a-glossary.md#role-pane) and `user` panes alike, plus every process identity recorded for the binding.
    - It re-reads each root from the OS.
    - A pane root is trusted only if its parent is the current server process.
  - The freeze is write-ahead. Each discovered identity is committed to `process_records`, with its prior stop state and the freeze's lifecycle operation id, before it is signalled.
  - It freezes roots, descendants, session members, and process-group members to a fixed point (until a repeat scan finds nothing new).
  - Its journaled steps run in this order:
    1. freeze
    2. [post-freeze recheck](appendix-a-glossary.md#post-freeze-recheck)
    3. holder scan
    4. checkpoint
    5. each child step
    6. final proof
    7. kiki-side termination of the [frozen set](appendix-a-glossary.md#frozen-set) with [verified exit](appendix-a-glossary.md#verified-exit)
    8. terminal-container close request
    9. [post-exit filesystem recheck](appendix-a-glossary.md#post-exit-filesystem-recheck)
    10. workspace forget
    11. directory delete
  - This one list is the order for every close, including `close-without-terminal`. Nothing is terminated before the final proof.
  - The **post-freeze recheck** runs immediately after the freeze and before the checkpoint.
    - It binds the frozen state to the approved fingerprint.
    - It must show that no frozen member holds an open [descriptor](https://en.wikipedia.org/wiki/File_descriptor) under the repository's `.jj` directory.
  - The checkpoint pins the exact commit with a pinned, working-copy-ignoring jj command.
  - Children are synchronously reconciled or detached.
  - The **final proof** runs after the checkpoint and all child work. It re-asserts that every member is stopped, and it re-checks holders, the runtime pane set, the filesystem generation, and the fingerprint. For membership, it checks that each listed container still holds its recorded launcher (if it had one) and exactly the processes recorded at the freeze.
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
- **Frozen-step deadlines.** Every single step taken while the set is frozen is limited by `[timeouts] frozen_step` (default `30s`).
  - A checkpoint, child step, or runtime call that exceeds it before termination begins takes verified resume. The thread is never left frozen behind a stalled step.
  - Once termination has begun, a failure is `CloseFailed` (or the plan's failed state). It is never a resume.
  - Waiting for a terminated process to be gone is limited by `[timeouts] verified_exit` (default `10s`). Expiry there is also `CloseFailed`, with files preserved.
  - A frozen member holding a descriptor under `.jj` (a jj process stopped while holding repository locks) fails the post-freeze recheck. It takes verified resume before any jj command is attempted.
- **Destroy order.** Destroy runs its steps in this order:
  1. freeze
  2. post-freeze recheck
  3. holder scan
  4. final proof
  5. termination of the frozen set with verified exit
  6. group close request
  7. post-exit filesystem recheck
  8. then bookmark deletion
  9. workspace forget and delete
  10. credential revocation
  11. tombstone
  - Drift before termination takes verified resume.
  - Process termination is the first irreversible step. Crash injection after it yields only `DestroyFailed` or completion of the same plan.
- **Approval scope.** A close, destroy, or restart approval covers every process in the listed terminal containers at freeze time.
  - The rendered plan lists the preflight process inventory and states that scope. The plan card shows the container-scope statement.
  - The approval fingerprint covers exactly these: the set of terminal containers, the role launcher identities, the holder set outside those containers, the workspace state, the [checkpoint target](appendix-a-glossary.md#checkpoint-target), and the children.
  - The fingerprint does not cover the per-container process list. Processes inside a listed container are covered by container scope and are recorded at the freeze.
  - A process that joins a listed container between preflight and freeze is covered. It is recorded at the freeze, terminated under that statement, and is not drift.
  - "Membership change" drift means one of three things: a changed container set, a changed role launcher identity, or a changed set of holders outside the listed containers.
  - A [workspace holder](appendix-a-glossary.md#holder) outside every listed container is accepted only when the approved plan names that exact identity (see [accepted holder](appendix-a-glossary.md#accepted-holder)). Any other holder is drift.
- **Two kinds of quiescence.** The process quiescence proof is the `ProcessSupervisor` freeze fixed point.
  - Only close, destroy, and repair use it.
  - The cascade's boundary is agent quiescence, the harness adapter's `AgentStatus::Quiescent`, and never the process freeze.
  - Terminal observations satisfy neither.
- **Process quiescence proof cases.** These are driven through the `ProcessSupervisor` fake and repeated against real processes at the integration gate:
  - Fixed-point growth:
    - A member that forks during discovery grows the set on a later round.
    - The proof holds only after two identical complete samples with every member observed stopped.
    - A set that does not stabilize within `[timeouts] freeze_stabilize` (default `5s`) is `Unknown`.
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
    - a changed container set
    - a changed role launcher identity
    - at the final proof, a listed container that no longer holds exactly the processes recorded at the freeze
    - a new holder outside the listed containers
    - a changed runtime pane set
    - a new filesystem generation
    - a changed fingerprint
  - Verified resume:
    - Members are continued children before parents, session leaders last.
    - Every member keeps its recorded identity, and none that was running is left stopped.
    - Resume proves every role that was live at freeze time. It requires those role-launcher identities and the terminal group, and the `agent` launcher must answer.
    - The set of roles that had already ended is part of the frozen record. A `shell` or `ui` pane the user closed before the freeze does not fail the resume.
    - A `user`-pane process that exited during the freeze is reported and is not a failure.
    - Only then may the thread return to `Active`. Resume the same incarnation without a new handshake, then repeat with a reused PID or missing launcher. Both failures preserve the workspace.
    - An unprovable resume is `CloseFailed` with the workspace present.
    - If a tool batch was in flight when the freeze began, the incarnation's batch state is unknown after resume. The unknown-batch rule then applies: hard restart to a clean boundary with files untouched.
  - Verified exit:
    - Exit is verified per recorded identity by kiki's own termination, before the runtime is asked to close anything.
    - Two fake runtimes change nothing: one that replies success to a close request while a process survives, and one that never replies.
    - Workspace deletion depends only on every frozen identity being gone, the holder scan, and the post-exit filesystem recheck.
    - If exit cannot be verified, the files stay and the lifecycle reports a failure.
- **Close approval binding.** A close approval is bound to the rendered plan and the preflight fingerprint.
  - Drift discovered after the freeze causes a verified resume and a fresh plan and approval.
  - The daemon never prompts while leaving a terminal group frozen.
- **Bookmark creation and retry.** Try a human bookmark at the base, then race native creation at the exact proposed target. Crash after jj creates the name but before the placement row commits. Only the attributed create operation may be adopted or compensated. A competing name survives.
- **Destroy keeps revisions.** Put extra bookmarks on the tip and on an interior commit. Destroy removes the managed bookmark and preserves both other names and their targets. A request to abandon revisions is rejected before any side effect.
- **Destroy crash injection.** Crash around bookmark deletion, terminal and workspace cleanup, and tombstoning.
  - They yield only the recorded `DestroyCommit`, `DestroyFailed`, or `Destroyed` outcome.
  - After the first irreversible step, no recovery path relabels the thread `Active`, `Closed`, or `ProjectionDiverged`.
  - `kk repair` can only finish the exact approved plan, through `retry-destroy`.

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
  - While `TerminalMissing` is open, boundary delivery, materialization, and lifecycle mutation are blocked. The exceptions are approved restart, `cleanup-failed-restart`, [`close-without-terminal`](appendix-a-glossary.md#close-without-terminal), and destroy plans.
  - A match on a different server instance never rebinds a thread. That holds for a matching Herdr workspace, tab, or pane id, label, working directory, or metadata token.
- **Observed server handoff.** The server instance changes while `kkd` is watching, and the new peer is one `kkd` did not start. Herdr's own handoff or upgrade is one way to get there.
  - Kiki ends the old `terminal_servers` row, which ends its bindings and raises `TerminalMissing`. It does not re-prove survivors.
  - It records the new peer as `Unverified` and provisions nothing on it.
  - The fix is `replace-terminal-server`, and after it `restart-terminal` for each thread.
- **Instance change that `kkd` made.** `kkd` itself starts a new server, for example after a server crash. The new row is `Open`, and each thread needs only `restart-terminal`.
- **Unbound containers.** An unbound container is a terminal container on the current server instance with no current binding.
  - A group whose binding ended because its `agent` launcher died, while the group itself survived, is one.
  - Its member processes are terminal members, not orphans. No `OrphanedProcess` is raised for them.
  - `restart-terminal` and `close-without-terminal` both list it, with its processes, and dispose of it.
- **No container reuse.** A terminal restart never binds a remnant or unbound container, whatever its label or working directory.
  - The plan's precondition is that no recorded process survives outside the listed containers. If one does, the plan stops and [`terminate-orphans`](appendix-a-glossary.md#terminate-orphans) comes first.
  - The restart plan does these things:
    1. It lists every remnant and unbound container, with its processes, for approval.
    2. It claims the approval with the operation journal.
    3. It freezes the processes in the listed containers.
    4. It proves that each listed container holds exactly the processes recorded at freeze. Then it terminates them with verified exit and sends each container a close request.
    5. It runs the holder scan and the orphan scan again.
    6. It provisions a fresh terminal group with new launchers.
  - The same disposal runs in `close-without-terminal` and in destroy from `ProjectionDiverged`.
- **Failed terminal restart.** `restart-terminal` is a journaled lifecycle operation with its own step list.
  - Crash injection at every step resumes the same plan.
  - A failure after provisioning leaves `TerminalMissing` open and the thread `ProjectionDiverged`.
  - The half-made group is then removed by [`cleanup-failed-restart`](appendix-a-glossary.md#cleanup-failed-restart). That plan has the same limits as `cleanup-failed-create`.
  - If the freeze of remnant processes returns `Unknown`, the plan takes verified resume and stops. Nothing is terminated.
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
  - `kkd` recognises a server it started by the peer identity on its `Open` row. A server that `kkd` did not start is unverified. `kkd` ends the old row, which ends its bindings and raises `TerminalMissing`, and records the new peer as `Unverified`. Nothing is provisioned on it. Its exit is the `replace-terminal-server` plan below, followed by `restart-terminal` for each thread.
  - A `terminal_servers` row is in one of four states: `Starting | Open | Unverified | Ended`.
  - After a failed start, `kkd` does not start again at once. It starts a server on demand, the next time a command needs one.
  - `kkd` writes a `terminal_servers` row in state `Starting` before it spawns a server. It moves the row to `Open` once it has read the server's peer identity.
    - `kkd` is killed between the two. On restart it finds the `Starting` row and recovers from it, as [Terminal runtime](13-architecture/terminal-runtime.md) describes.
    - No fault order leaves two servers running for one session.
- **[`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server).** This plan is user-scoped, not thread-scoped. It is applied with `kk repair --server`.
  - `[terminal] session`, `herdr_bin`, or `[paths] herdr_dir` is changed while an instance is open. `kkd` starts no second server. It keeps the old one and reports that a change is pending.
  - For those keys only the user config file counts. A value from the invoking terminal's environment or flags is ignored.
  - The plan lists every thread and process the replacement stops.
  - It needs a one-shot approval. Without one, nothing is stopped.
  - Once approved, it stops the old server with verified exit and only then starts a new one.
  - A crash at any step resumes the same plan and never leaves two servers.
- **Service placement.** On macOS `kkd` runs as a [launchd](https://en.wikipedia.org/wiki/Launchd) user agent. On Linux it is a [systemd](https://en.wikipedia.org/wiki/Systemd) user unit.
  - `kkd` starts the Herdr server as its own service-manager unit, not as a child inside `kkd`'s unit. That is a separate launchd job on macOS and a separate transient systemd user unit on Linux.
  - After a reboot or a login, the service manager does not start the server unit by itself. `kkd` starts it on demand, the next time a command needs it.
  - **The server must outlive `kkd`.** This is a proof gate under each real service manager, not a fake:
    - `kkd` is crashed with `SIGKILL`, restarted through the service manager, and upgraded.
    - Each time, the server and every agent keep running with unchanged process identities.
    - The returning `kkd` verifies the same server instance and continues the same bindings.
  - With `kk` first invoked from inside a terminal application, quitting that application leaves `kkd`, the server, and every agent running.
  - This is an integration gate on each platform.
  - No Herdr release containing its own terminal-quit fix is required, because that fix applies only to a server Herdr starts for itself.
- **No service manager.** Many containers and CI runners have no user service manager. There, `kkd --foreground` runs under whatever supervisor the operator uses.
  - `kkd` starts the Herdr server as a detached process in its own [session](appendix-a-glossary.md#ext-session), not as a child that dies with `kkd`.
  - The survival proof above is a gate for this mode too: `kkd` is crashed with `SIGKILL`, restarted, and upgraded, and each time the server and every agent keep running with unchanged process identities.
  - The returning `kkd` verifies the same server instance and continues the same bindings.
  - A platform mode that fails the proof is unsupported. It is not shipped with a weaker promise.
- **macOS over SSH with no GUI login.** `kkd` and the server run in launchd's per-user domain, not the GUI domain.
  - Start on a host with no graphical login. Disconnect the last SSH session after setup, reconnect, then run the crash, restart, and upgrade tests. A test in a graphical login cannot qualify this mode.
  - For both headless modes, retain the OS version, supervisor and job settings, service domain or session, process ids **and start times** before and after each step, and the returning daemon’s observed binding. Qualify only the configuration tested. Until that evidence exists, report the mode as unverified and refuse unsupported setup with code 4.
- **A full lifecycle with zero attached clients.** No Herdr client, overlay, popup, `ui` pane, or desktop session exists at any point in the test.
  - Under an automation credential and an activated policy, the test runs `kk init`, `kk new`, `kk close`, `kk reopen`, and a `kk repair` restart.
  - Each step reaches the same end state as it does with a client attached, and every safety proof runs.
  - `kk ls --json` and `kk events` report what the overlay would show.
  - `kk attach` over SSH later connects a client to the running thread. Attaching and detaching change nothing in kiki's state.
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
- **Orphan recovery.** An [orphan](appendix-a-glossary.md#orphan) is one of two things:
  - a recorded process identity that is alive with no current binding and is not a member of a container on the current server instance; or
  - a harness remnant: any descendant of a live `agent` launcher, other than the launcher, while no incarnation is live. A remnant need not have been recorded before.

  The cases:
  - A worker that ignores hangup survives a `SIGKILL` of the dedicated server and is absent from every terminal view.
  - The orphan scan runs at daemon start, at the instance change, and before a replacement. It finds the worker by recorded identity and raises `OrphanedProcess`.
  - The fixture's worker is a recorded identity: the harness itself.
  - A second fixture uses a tool child that kiki never recorded, and whose `agent` launcher died with the server.
    - It is neither a recorded identity nor a descendant of a live launcher, so it raises no `OrphanedProcess`.
    - Instead the [`restart-terminal`](appendix-a-glossary.md#restart-terminal) plan's holder scan reports it by pid and command.
    - The plan stops until it names the process as accepted or the process is gone.
    - Kiki does not signal it.
  - A third fixture is a harness remnant: the harness dies under a live `agent` launcher and leaves an unrecorded tool child. It raises `OrphanedProcess`.
  - While the issue is unresolved, kiki blocks replacement, materialization, and deletion for that workspace. It activates no gate there.
  - The plan that resolves `OrphanedProcess` is [`terminate-orphans`](appendix-a-glossary.md#terminate-orphans). It needs a one-shot approval.
    - For a survivor it uses the recorded identities. For a remnant it runs freeze discovery rooted at the launcher.
    - It records `FreezeDiscovery` rows under the approval before it signals anything.
    - It stops, re-verifies, and terminates only those exact identities, and verifies their exit.
    - A remnant's launcher is left alive.
  - Recorded role processes that are pane members on the current instance are terminal members and raise no orphan issue. That includes the members of an unbound container.
  - An unrecorded same-UID holder raises no standing issue. It surfaces only as an `Unknown` result in an operation that would delete the workspace.

- **Event loss and resync.** The runtime fake reports lost events, drops the connection, and changes instance between a subscription and its snapshot.
  - In every case `kkd` resubscribes, takes a fresh snapshot, reconciles every binding against the snapshot and the OS, and republishes presentation.
  - No decision is reconstructed from the runtime's event history.
  - A label renamed by another socket peer is republished to its bound terminal group and is never read back as input.
  - The matching cases for [sidebar tokens](appendix-a-glossary.md#sidebar-token) (overwritten, expired, or lost at restart, then republished) are tested with the later sidebar-token surface, not here.
- **Caller-local focus with two attached clients.** [Caller-local focus](appendix-a-glossary.md#caller-local-focus) moves only the viewer who ran the command.
  - With [`client_targeted_focus`](appendix-a-glossary.md#client-targeted-focus) advertised, `kk switch <thread>` moves only the invoking client. The other client's location is unchanged.
  - A command with no viewer (an agent's tool call, a script, a pane nobody is showing) resolves `NoCallerClient` and moves no one. `kk switch` then exits with code 4.
  - Without the capability, `kk switch <thread>` fails naming the missing capability and moves no client. It never falls back to the broadcast focus.
  - `kk switch --all-clients <thread>` is the only form that moves every attached client.
  - Capability detection reads the runtime's advertised capabilities. A fake that silently ignores the unknown client parameter must not be mistaken for support.
  - No form of switch creates, closes, or re-ensures a pane, and none consumes a `HumanApproval`.
- **`TerminalMissing` repair.** A `TerminalMissing` repair can restart the thread to `Active`, or execute a stable `close-without-terminal` plan to `Closed`.
  - That plan's [loss inventory](appendix-a-glossary.md#loss-inventory) runs in preflight.
  - Claiming its approval enters `CloseCommit`.
  - Its precondition is that no recorded process survives outside the listed containers.
  - Its journaled `CloseCommit` steps use the general close order. Nothing is terminated before the final proof.
    1. The processes in the listed remnant and unbound containers are frozen, which records their identities.
    2. The post-freeze recheck runs.
    3. The holder scan runs.
    4. The checkpoint is placed.
    5. Each child step runs.
    6. The final proof shows that each listed container holds exactly the processes recorded at the freeze.
    7. Kiki terminates the frozen processes itself, with verified exit.
    8. The terminal-container close request is sent for each listed container.
    9. The post-exit filesystem recheck runs.
    10. The jj workspace is forgotten.
    11. The directory is deleted.
  - A failure before the final proof takes verified resume of the frozen processes. Files are preserved, and the thread goes `CloseCommit --> ProjectionDiverged`, mirroring `DestroyCommit`.
  - A fixture that terminates any listed process before the final proof fails the test.
  - Crash injection at each step resumes the same plan and never returns the thread to `Active`.

### Hook outages and barriers

- **Daemon unreachable from the hook.** When `kk-hook` cannot connect to `kkd` and be admitted within `[timeouts] hook_connect` (default `1s`), it checks the thread's [barrier marker](appendix-a-glossary.md#barrier-marker). It also writes to `~/.config/kiki/repos/<repo_id>/errors/<thread_id>.log`.
  - **Marker absent.** Deny the call. Time out the first sibling, then admit the second on the same daemon with a pending intent. Neither tool may run during the update. Hold an earlier writer open and verify that mutation waits for proof it has stopped.
  - **Marker present.** The hook answers with the generic blocking deny. The tool call does not run.
  - `hook_connect` covers only connecting and being admitted. A test that stalls `kkd` after admission never sees the non-blocking decision.
  - A reconciliation pending during the outage must still be delivered on the next successful PreToolUse round-trip.
  - If the watcher saw the trigger, durable state lives in `sync_intents`.
  - Otherwise, restart catch-up reconstructs it from jj's [op log](https://docs.jj-vcs.dev/latest/operation-log/) (jj's record of every operation run against the repo).
  - If the agent edited the stale tree during the outage, the next probe enters `RecoveryRequired` rather than treating the tree as clean.
- **Active barrier during an outage.** With a durable marker every tool in the batch stays blocked across a restart.
- **Hook budget after admission.** Once `kkd` has admitted a call into a reconciliation, `kk-hook` waits up to `[timeouts] slow_path` (default `30s`).
  - A reconciliation that finishes inside the bound answers every call in the batch with the saved payload.
  - If the bound expires, the answer is a generic blocking deny ("kiki is reconciling; try again").
  - If the reconciliation's owner crashes, the answer is the same generic blocking deny.
  - In neither case is the answer "continue", and no tool in the batch runs.
  - Each adapter's generated configuration pins the harness-side hook timeout above `slow_path` plus a margin. A fixture with the pin at or below `slow_path` fails the launch proof.
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
  - With two edit-preserving successors, diagnose in JSON and apply one full commit id without a terminal under a `repair:choose-recovery-successor` rule. Check the chosen tree, retained bundle, and audit record. A missing target returns 2, missing approval returns 3, and a stale or non-preserving target returns 4. Each leaves recovery paused. Crash after selection and after the jj write, and verify one repair completes.
  - It never resumes on a clean successor that hides those edits.
  - The `JjBackend` fake and real jj both return success from a dirty `jj workspace update-stale` while the edited file is gone from disk and present only in the other divergent successor.
  - The test fails any implementation that treats that exit status as preservation.
- **Textual conflicts.** A reconciliation whose result contains [jj conflicts](https://docs.jj-vcs.dev/latest/conflicts/) sets `result_has_conflicts` on the intent and adds no state.
  - The payload lists the conflicted commits and paths and says they must be resolved.
  - Derived cascade status is `conflicted` before and after acknowledgement.
  - It leaves `conflicted` only when a later operation's view shows the thread's chain conflict-free.
  - A textual conflict alone does not hard-pause the agent.
- **Replacement incarnation precondition.** A replacement's launch gate is not activated while a tool child of the retired harness survives in the `agent` launcher's descendant, session, or process-group set.
  - The survivor raises `OrphanedProcess` with harness-remnant evidence. It blocks replacement, materialization, and deletion: the gate is not activated, nothing is written into the workspace, and nothing is deleted.
  - A hard-pause terminates the harness's whole process tree by recorded identity and leaves the launcher alive.
  - Cascade restarts need no human approval.
- **`restart-agent`.** A harness that crashed under a live launcher is restarted by this `kk repair` plan.
  - The restart runs on the same launcher through a fresh gate.
  - It uses `RestartStartup` when an intent is pending.
  - It needs no approval in thread context.
  - When the launcher itself is gone the intent waits behind `TerminalMissing` repair.
- **Third safe boundary.** Reconciliation may also run when the thread has no live incarnation and the remnant check has passed.
  - A thread whose harness has exited, with an empty launcher process tree, is reconciled without waiting for a hook.
  - With a surviving tool child the remnant check fails. Nothing is materialized and `OrphanedProcess` is raised.
  - The payload still waits on the intent and reaches the next incarnation through `RestartStartup`.
- **`RestartStartup` mechanism.** Each harness has its own proof of all three facts.
  - The launch specification carries the startup delivery id in the launcher environment.
  - The session-start hook reports that id with `ReportHarnessReady`. A missing or different id fails the handshake.
  - The first pre-tool hook call of a model turn in that incarnation is the acknowledgement. No separate acknowledgement call exists.
  - A harness whose proof fails runs managed sessions without cascade delivery. A thread on that harness cannot follow another thread, and a request to make it follow is refused with that reason.
- **Lock order.** The [lifecycle lock](appendix-a-glossary.md#lifecycle-lock) is the thread's reconciliation lock, held for the length of a lifecycle operation. The [repo jj lock](appendix-a-glossary.md#repo-jj-lock) is per repo.
  - Locks are taken in one order only: parent thread lock, then child thread lock, then the repo jj lock.
  - The repo jj lock is held around every unpinned working-copy command and every operation-head integration, from the frontier sample that the step depends on until the re-sample.
  - It is the innermost lock. It is short, and it is never held across a wait: not across a hook wait, an approval, a frozen step, or a runtime call.
  - A parent close that reconciles two children, run beside a child's own cascade boundary, never deadlocks.
  - A fake that records lock acquisitions fails any path that takes them in another order.
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
  - A sample taken while jj replaces one head with another must be an antichain: no head in it is an ancestor of another.
    - If it is not, the sampler retries within `[timeouts] frontier_retry` (default `2s`).
    - If the bound expires it returns `Unavailable`. It never returns a set that holds both a head and its ancestor.
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
  - Each working-copy command `kkd` runs is taken under the repo jj lock only after a single-head sample, is attributed, and is followed by a new sample. The lock is held from that sample to the re-sample.
- **Attribution.** Kiki sets no operation description.
  - Each kiki-run command carries a per-invocation operation user and host.
  - Every operation id it wrote is recorded, including both operations of one `jj workspace add`.
  - An external operation is never attributed, whatever its description says.
- **Operation history rewritten.** History was rewritten when any recorded operation that was an ancestor of the last recorded frontier is no longer reachable from the current frontier. jj's constant root operation is never counted.
  - `jj op abandon` of an operation in the middle of the log is detected. On jj 0.46.0 that command keeps the older operation ids and changes the newer ones, so some recorded ancestors become unreachable while others stay.
  - `jj op abandon` of the oldest operations is detected the same way.
  - `jj util gc` alone is not a cause. It only removes operations that are already unreachable, and it raises nothing.
  - A normal new operation, a second head, and a merge of two heads are not rewrites.
  - Kiki [re-anchors](appendix-a-glossary.md#re-anchoring) silently when every thread's bookmark and every workspace `@` equal their cached values.
  - When any differs, kiki does these things:
    - It raises exactly one repo-level [`OperationHistoryRewritten`](appendix-a-glossary.md#operationhistoryrewritten) issue listing those threads.
    - It raises no per-thread bookmark issue for the gap before approval.
    - It blocks checkpoint, publish, close, detach, and explicit rebase for the listed threads until the repair plan re-anchors.
- **[`reanchor-history`](appendix-a-glossary.md#reanchor-history) is per thread.** The plan lists every affected thread with its observed bookmark state.
  - `kk repair --repo` diagnoses repo-level issues for the caller's repo. `kk repair --repo --apply <plan-id>` applies one. It needs a one-shot approval with repo scope.
  - On approval, each listed thread is handled by itself:
    - If its bookmark is present, not conflicted, and on the live head or the owned chain, kiki records a fresh placement with `reason = Reanchor` at the observed commit, against the current operation.
    - For every other listed thread kiki raises the matching per-thread issue at the new anchor: `BookmarkMissing`, `BookmarkConflicted`, or `BookmarkMoved`. The ordinary plans then fix it.
  - A `Reanchor` placement is exempt from nothing. A fixture with one thread's bookmark off the owned chain gets `BookmarkMoved`, never a placement.
  - `kk repair --all` covers every thread in the caller's repo and never crosses repos.
- **Boundary snapshot.** A [boundary snapshot](appendix-a-glossary.md#boundary-snapshot) is a snapshot of the working copy that kiki itself runs at a safe moment.
  - A snapshot requires a proven safe boundary, including a passed remnant scan when there is no live incarnation.
  - It is taken under the thread lock and, inside it, the repo jj lock, after a single-head sample. It is attributed and followed by a new sample.
  - Close, detach, and publish preflight are observational. Repeat the refusal case with a dirty child and with a frontier that needs integration.
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
  - The base is not on the owned chain. The chain starts just after the base. So each of these is `BookmarkMoved`, even with a predecessor record:
    - a successor that lands on the base (for example the first owned commit squashed into the base)
    - a successor that lands on a parent thread's commit
    - a successor that lands on trunk
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
  - a backward move that is not an undo under the undo rule
- **[`BookmarkConflicted`](appendix-a-glossary.md#bookmarkconflicted).** Two situations produce divergent successors and a conflicted bookmark:
  - two operations that each rewrite the checkpointed commit and then merge
  - a dirty `jj workspace update-stale` on a workspace whose `@` carries the bookmark
  - Both are `BookmarkConflicted`, never a chosen successor.
  - The conflict flag is tested before the unchanged-target rule. A bookmark that jj marks conflicted while its only target is still the expected target is `BookmarkConflicted`, not unchanged. That happens:
    - after one divergent side is abandoned, or
    - after a fetch that deleted the tracked remote bookmark while the local one had moved.
- **External bookmark rename.** One operation that removes the thread's bookmark name and adds exactly one new local name is a normalization. The new name must be on the expected target, or on a successor of it that the succession rule accepts in the same operation. That is so provided the operation changes no remote or `@git` bookmark and is not an import or fetch.
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
- **Abandoned checkpoint.** `CheckpointAbandoned` means the bookmark is absent, the expected target is hidden at the observed operation, and no visible successor is accepted by the succession rule.
  - A bookmark that is still present, on a commit kiki does not accept, is `BookmarkMoved` even when the expected target is hidden. Its exit is `choose-bookmark-target`.
  - `jj abandon` of the checkpointed commit deletes the bookmark and is reported as `CheckpointAbandoned`.
  - A fetch after a merged [pull request](https://docs.github.com/en/pull-requests)'s branch was deleted abandons the unreachable checkpointed commit and deletes the bookmark. That is the same issue, for an active thread and for a closed one.
  - Its plans are [`unhide-checkpoint`](appendix-a-glossary.md#unhide-checkpoint) and [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target). `restore-bookmark` is not offered, because the expected target is hidden.
  - A **closed** thread with `CheckpointAbandoned` is common after a squash-merged pull request and a fetch.
    - The thread stays `Closed`. It does not move to `ProjectionDiverged`.
    - It is reported on `kk ls --all` and `kk repair`.
    - It is not a loud attention event.
    - It blocks only `kk reopen`. Every other command behaves as before.
    - It has three exits: `unhide-checkpoint` followed by reopen; `choose-bookmark-target` onto a visible commit of the thread's archived owned chain, followed by reopen; or destroy when that ships.
  - When the abandoned commit is also a live head or an owned revision, follows classification records `TopologyDiverged` independently. Neither result suppresses the other.
- **Unresolved bookmark issue.** An unresolved bookmark issue pauses successor tracking. Later bookmark observations are recorded on that issue and no succession row is appended.
  - Head tracking and follows classification continue.
  - The issue resolves automatically, with no plan, when a later operation shows the bookmark unconflicted on the expected target.
  - While tracking is paused under an open bookmark issue, the expected target later becomes hidden. Then:
    - the open issue stays as it is;
    - no second issue is added;
    - `restore-bookmark` is withdrawn; and
    - `choose-bookmark-target` is the exit.
- **Undo rule.** After a tracked `jj describe` rewrite, `jj undo` returns the bookmark to the earlier commit while the later one becomes hidden.
  - Kiki appends a `Reverted` succession row, sets the expected target back, and raises no issue.
  - `jj redo` is handled the same way, and so is `jj commit` followed by `jj undo`.
  - A backward move to a commit that no earlier row recorded as this thread's expected target, or while a later recorded successor is still visible, is `BookmarkMoved`.
- **Undo evidence (proof test on the pinned jj).** The expected target pops back when (a) the bookmark at the observed operation is exactly a commit that an earlier placement or succession row recorded as this thread's expected target, and (b) no successor recorded after that row is still visible at the observed operation. This holds whoever made the move.
  - After a tracked rewrite, each of `jj undo`, `jj op revert`, and `jj op restore` to the earlier operation hides the later successor. The expected target pops back and no issue is raised.
  - After the same tracked rewrite, `jj bookmark set --allow-backwards` to the earlier commit (made visible again by hand) leaves the later successor visible. That is `BookmarkMoved`.
  - The same hand-made move, made after the later successor is already hidden, passes both tests. The expected target pops back and no issue is raised.
  - An undo of a placement with no later succession row has no successor to hide, so test (b) holds and the expected target pops back.
  - The proof must show on the pinned jj version that a real undo or restore always hides the later successors. If it does not, the rule is reopened as a decision.
- **Undo across a placement.** The undo rule covers the thread's whole placement and succession history, not only the current placement.
  - The fixture is: a placement on commit X, a tracked rewrite to X′, a kiki checkpoint that places the bookmark on a later commit Y, and then a human `jj undo` of kiki's own placement operation.
  - The bookmark returns to X′, which an earlier row recorded as this thread's expected target.
  - Kiki pops the expected target back to X′ and marks the reverted rows `Reverted`. It raises no issue.
  - A second `jj undo` that reverts the rewrite pops the expected target back to X the same way.
  - An undo that lands the bookmark on a commit no earlier row recorded as this thread's expected target is still `BookmarkMoved`.
- **Bookmark repair plans.** There are four per-thread plans and one repo-level plan. [Commands](09-commands.md) owns the table, and the tests follow it.
  - [`restore-bookmark`](appendix-a-glossary.md#restore-bookmark):
    - It is offered for `BookmarkMissing`, `BookmarkMoved`, and `BookmarkConflicted`, and only while the expected target is visible.
    - It puts the bookmark back on the expected target and records `reason = RepairRestore`. It needs no approval in the thread's own context, and a one-shot approval when applied to a different thread.
  - [`adopt-bookmark`](appendix-a-glossary.md#adopt-bookmark):
    - It is offered for `BookmarkMoved` when the single observed target is the live head or on the owned chain.
    - It makes the observed target the expected target, needs a one-shot approval, and records `RepairAdopt`.
    - It is not offered when the observed target is off the owned chain, or on the base.
  - [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target):
    - It is offered for any bookmark issue: `BookmarkMissing`, `BookmarkMoved`, `BookmarkConflicted`, and `CheckpointAbandoned`.
    - It is also offered for a thread with no open issue whose relationship is `ahead` or `diverged`.
    - Its target is the live head or an on-chain commit the caller names with `--target <commit>`. It needs a one-shot approval and records `RepairChoose`.
    - It is the exit whenever the expected target is hidden.
  - [`unhide-checkpoint`](appendix-a-glossary.md#unhide-checkpoint):
    - It is offered for `CheckpointAbandoned`, and only when unhiding would not create a divergent change.
    - It makes the expected target visible again, needs a one-shot approval, and records `RepairUnhide`.
    - `RepairUnhide` is the one placement reason allowed while the expected target is hidden.
  - [`reanchor-history`](appendix-a-glossary.md#reanchor-history) is the repo-level plan. See **Operation history rewritten** above.
  - No plan places the bookmark on a commit that is off the owned chain. A fixture that asks for one is refused. The human first fixes the shape with jj, for example with a rebase that puts the commit on the chain, and then adopts or chooses.
- **Restore never targets a hidden commit.** For `BookmarkMissing`, `BookmarkMoved`, and `BookmarkConflicted`, no restore plan is offered while the expected target is hidden. A test that forces one shows the divergent change it would create and fails.
- **Checkpoint target rule.** Every checkpoint places the bookmark on its [checkpoint target](appendix-a-glossary.md#checkpoint-target).
  - The target is the live head.
  - When the head is empty and undescribed, kiki walks back along the owned chain to the nearest commit that is not both empty and undescribed. A fixture with two stacked empty, undescribed commits walks past both.
  - If the walk reaches the expected target first, the bookmark stays where it is.
  - If the walk leaves the owned chain without finding either, the checkpoint refuses with "nothing to checkpoint" and mutates nothing.
  - Creation is the one exception. It places the bookmark on the new thread's first, empty commit.
  - A checkpoint whose target is neither equal to nor a descendant of the expected target refuses without mutating.
- **Who may move the bookmark where.** The tests pin one rule.
  - A checkpoint (creation, publish, close, or detach) only moves the bookmark forward along the owned chain. It never moves it backward or sideways, and it never passes `--allow-backwards`.
  - `adopt-bookmark` and `choose-bookmark-target` may place the bookmark on the live head or on any commit on the validated owned chain. That includes a commit behind the expected target. These plans may pass `--allow-backwards`.
  - `restore-bookmark` puts the bookmark back on the expected target. jj may see that as a backward move, so it may pass `--allow-backwards`. It still needs no approval in the thread's own context; applied to a different thread, it needs a one-shot approval.
  - `unhide-checkpoint` may also pass the flag.
  - The `JjBackend` fake fails any bookmark command that carries `--allow-backwards` outside those four repair plans.
  - Kiki never places the bookmark on a commit that is off the owned chain. v1 has no plan for that.
- **Checkpoint relationship.** The [checkpoint relationship](appendix-a-glossary.md#checkpoint-relationship) says where the live head sits compared with the expected target:
  - `current` when the expected target equals the head, or equals what the checkpoint target rule picks. That covers a head that is an empty, undescribed working-copy commit on top of the expected target (right after `jj commit` and right after `kk reopen`).
  - `behind` for any other descendant head
  - `ahead` after `jj edit` of an earlier commit
  - `diverged` otherwise, for example after `jj rebase -r` moves the bookmarked commit somewhere else
  - Publish, close, and detach stay blocked for `ahead` and `diverged` until `choose-bookmark-target` is applied. No bookmark issue is raised for those two relationships.
  - An unregistered descendant of the chain changes neither the relationship nor successor tracking. It blocks only explicit rebase plans.
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
- A daemon restart after a `PassThrough` admission loses the cache. `kkd` owns that cache, in memory, keyed by incarnation and batch. `kk-hook` is a stateless one-call client and holds none.
  - The first pre-tool call from an incarnation that was already running before this `kkd` start is an unknown in-flight batch.
  - The one exception is a hook payload that proves the call is the first call of a new model turn. That call is admitted normally.
  - For an unknown in-flight batch, `kkd`, not the hook, blocks the call, hard-pauses the incarnation, and starts the replacement. Files are left untouched.
  - An incarnation started after this `kkd` start is never treated as unknown for this reason.
  - An active durable `Block` stays [fail-closed](appendix-a-glossary.md#fail-closed).
- **Barrier marker.**
  - `kkd` writes the marker durably before it binds `Block` and before any workspace file changes. Crash injection between each pair of steps never leaves changed files without a marker.
  - Stop `kkd` while a `Block` is bound. Hooks on both a marked thread and an unmarked thread deny admission.
  - `kkd` removes the marker when the barrier lifts. After a crash, recovery removes it only after the reconciliation is resolved, never before.
  - `kk-hook` never writes or removes the marker.
- **Hook process dies before answering.** For each pinned harness version, kill `kk-hook` before it prints an answer. The harness must not run the tool as if the hook had allowed it. A harness version that fails this proof is unsupported for cascade delivery.
  - Two `kk-hook` runs for sibling calls share no state except through `kkd`. Killing one changes nothing for the other.
- A concurrent sibling `PreToolUse` arrives after payload emission but before `MarkDelivered`.
  - It receives the byte-identical payload.
  - It cannot acknowledge the intent.

### Batch completion and acknowledgement

- Matching, duplicate, stale, missing, and reordered `PostToolBatch` events.
  - Only the matching event marks batch completion.
  - None of them acknowledges delivery.
- A new batch in the same [model turn](appendix-a-glossary.md#model-turn) after `PostToolBatch`. It cannot acknowledge merely because its batch id differs.
- The first `PreToolUse` from a provably later model turn.
  - Require an exact harness receipt from the same conversation before acknowledging. Crash after saving `Materialized` and return generic denials to every sibling. Completion and a later turn must leave the intent unacknowledged. Repeat with a valid receipt from a different conversation.
  - It then evaluates the next ordered intent before deciding whether its tool may run.
  - If `MarkDelivered` was lost, the same exact proof atomically repairs delivery and advances `Materialized -> Acknowledged`.
- Hook, daemon, and agent crashes before and after durable barrier creation, and before and after `batch_completed_at`. Ambiguous completion always hard-restarts with the saved payload.

### Hard restart

- The hard-restart fallback when an adapter cannot expose an unambiguous batch-completion boundary.
  - The replacement row and the byte-stable startup payload are durable before the harness starts.
  - The payload is the replacement's first startup message.
  - The session-start hook reports the startup delivery id with `ReportHarnessReady`.
  - Its first managed boundary, the first pre-tool hook call of a model turn, proves startup processing and is the acknowledgement.
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
- Recovery verifies edit-bearing divergent successors before choosing the visible result. Ambiguous recovery waits for the caller to name a verified successor.
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

- `BeginApproval` under explicit Admin can begin registration, user-scoped server replacement, and the presenter route for policy activation, credential creation or rotation, and installation changes. Admin cannot act as the confirming presenter
- Admin passed with `--admin-credential-file` is accepted only by `kk automation apply`, `kk automation credential create` and `rotate`, and a `kk daemon install` that changes an existing installation; a first install needs no credential, and every operational method still rejects Admin
- `kk init` begun by an automation credential uses that credential for `BeginApproval`, not Admin
- the user-scoped `replace-terminal-server` plan begun by an automation credential uses that credential too; it runs only under a rule that allows `repair:replace-terminal-server`, accepts `server-wide`, and has `repos = ["*"]`
- broker enrollment
- persisted begin/display/confirm/cancel challenges
- binding of the [nonce](https://en.wikipedia.org/wiki/Cryptographic_nonce), channel, method, target, arguments, and rendered plan
- atomic [capability](https://en.wikipedia.org/wiki/Capability-based_security) issuance after confirmation
- atomic claim with one durable operation id
- crash resume of only that plan
- final consumption
- expiry and replay
- plan-digest drift
- a caller with no terminal: with no matching rule, or with a rule that requires a human, the call is refused with exit code 3 and changes nothing

[Automation policy](04-authority.md#automation-policy) tests cover the rules that let a [`PolicyApproval`](04-authority.md#policyapproval) stand in for the human's confirmation:

- **Match.** A rule that matches the principal, repo, operation, and labels gives `Allowed`. `BeginApproval` returns a `PolicyApproval` in the same reply, the retried method runs, and `kk` prints the plan and "approved by rule `<name>`" with no prompt.
- **No match.** With no matching rule the [decision](appendix-a-glossary.md#policy-decision) is `NoMatch`. At a foreground terminal the presenter flow runs for a thread or registration caller. An automation requester gets code 3 even at a terminal. With no terminal the call exits with code 3, and the message names the operation, the plan's risk labels, and the reason.
- **`require-human` beats `allow`.** When both kinds of rule match, the decision is `RequireHuman`, whatever order the rules are in.
- **`require-human` ignores `accept`.** A `require-human` rule with no `accept` key matches a plan that carries risk labels, and a plan that carries none. It checks principals, repos, and operations. For consent it also checks the named provider and disclosure version. Adding an `accept` list to it changes nothing.
- **A label that is not accepted means no match.** An `allow` rule matches only if every [risk label](appendix-a-glossary.md#risk-label) on the plan is in its `accept` list. An `allow` rule with no `accept` key matches only a plan with no labels.
- **`thread-op`.** An ordinary thread change, such as a checkpoint or a `restart-agent` repair, needs no approval in the thread's own context. Run with an automation credential or from another thread, it needs a one-shot approval, and only a rule that includes `thread-op` by name or by `*` allows it. A rule that lists `repair:*` does not. The plan carries `cross-thread` for a thread-scoped caller and no label for an automation credential.
- **Risk labels.** For each label in the closed set, a plan that does the labelled thing carries the label, and the rendered plan shows it. A plan with no labels still needs an approval when its operation is on the approval list.
- **An edited but unapplied file changes nothing.** `kkd` evaluates only the stored, activated copy. `kk automation status` reports that the file differs from it.
- **[Activation](04-authority.md#activating-a-policy).** `kk automation apply` takes effect only after a foreground confirmation by the enrolled presenter, which shows the full canonical policy and a diff against the active one, or with the Admin credential. A thread credential, an automation credential, or a `PolicyApproval` cannot activate a policy.
- **Layers.** An `[automation]` section in a repo, thread, environment, or `--config` layer is not read.
- **Revoke.** `kk automation revoke` needs no approval, and any credential of this user may call it. After it, every evaluation is `NoMatch`. A `PolicyApproval` issued before the revoke can still be claimed until it expires. One whose credential was revoked cannot.
- With no active policy, each local credential class can revoke a policy, credential, or consent. Test an automation requester with a foreground terminal and `--confirm`. It gets code 3 and no presenter challenge.
- Open a projection issue on a closed thread before starting `kk wait --for issue`. With no further events, the first summary satisfies the wait.
- Change Codex’s resolved sandbox argument after creation preflight. A stale approval cannot launch with the new permissions.
- Allow reopen by policy but provide no consent for catch-up. On the interactive path, bind the presenter before claim and show the preview only to that presenter. An unattended caller gets code 3.
- **Consent records.** Grant by policy with no enrolled presenter and verify its approval id and exact disclosure version. Change only the provider, then only the disclosure version. Neither old grant is valid.
- **Consent is never matched by `*`.** A rule with `operations = ["*"]` does not match `consent:*`. Only a rule that names `consent:<purpose>` and lists the provider in `providers` does.
- **A safety-proof refusal still refuses.** Under a rule with `accept = ["*"]`, each of these stops the plan exactly as it does for a human approval: drift, an `Unknown` freeze result, an unaccepted holder, a failed final proof, and a failed verified exit.
- **`PolicyApproval` single use and drift.** A second claim of the same approval is refused. An expired one is refused. A changed plan digest is refused and needs a fresh `BeginApproval`. The approval is claimed into the operation journal before any external effect, and a crash resumes only that plan.
- **What a `PolicyApproval` can never satisfy.** Activating a policy, creating or rotating an automation credential, changing the daemon installation, and enrolling or recovering the presenter are each refused when offered a `PolicyApproval`.
- **Principals.** `credential:<name>`, `thread:self`, `thread:descendant`, `thread:any`, `registration`, and `*` each match exactly the callers they name. A thread acting on a sibling does not match `thread:self` or `thread:descendant`.
- **`--confirm`.** With a matching `allow` rule, `--confirm` still runs the human prompt.
- **Agents.** `ConfirmApproval` from a descendant of an `agent` launcher stays refused. Exercise the same `thread:self` rule from an agent and from a person holding its credential. Also verify that the wildcard principal matches both. An unrelated credential cannot claim that thread identity.
- **[Automation credentials](appendix-a-glossary.md#automation-credential).** A credential reads repo summaries for every registered repo. It also reads each registered thread's status and non-sensitive state: `kk status`, `kk ls`, `kk events`, `kk wait`, and `kk repair` diagnose all work with it. A sensitive read is refused without a `sensitive-read` rule. It calls `BeginApproval` for any registered repo or thread, for `kk init`, and for the `replace-terminal-server` plan. It cannot confirm a human challenge, and it is refused wherever Admin or the presenter is required. Creating or rotating one needs the presenter or Admin. Revoking one needs no approval, and a revoked or rotated-out credential is rejected. The file is mode `0600` and never appears in a harness, hook, or pane environment.
- **Audit.** Each `PolicyApproval` writes exactly one audit row with the rule name, policy digest, principal, operation, and risk labels. Policy activation and revoke, and credential create, rotate, and revoke, each write exactly one row in `user_audit_log`.

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
- consent from an activated policy rule that names `consent:<purpose>` and the provider, and no consent from a rule whose `operations` is `*`
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
- Publish preflight checks that every commit it would push has a description, before it places the bookmark.
  - If any commit has none, publish refuses and names those commits.
  - Nothing is placed, nothing is pushed, and the expected target is unchanged.
  - With every commit described, the same publish goes on to its checkpoint.
- Force-push and PR-base mutation remain a pending named remote plan until a one-shot approval claims it. That is a foreground human approval, or a policy approval from a `publish` rule that accepts the `externally-visible` risk label.
- A failure retains the [follows edge](appendix-a-glossary.md#follows-edge) and is safe to retry.

## Fakes

Deep-module tests should use fakes for the dependencies below. A fake is a stand-in implementation that acts like the real dependency but runs in-process.

- `JjBackend`
- `OpFrontierSampler`
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

The `OpFrontierSampler` fake exposes:

- one, two, and three heads
- a sample taken in the middle of a head replacement, which holds both a head and its ancestor
- an `Unavailable` result
- a frontier from which recorded operations are no longer reachable (rewritten history)

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

These integrations require smoke tests or integration tests that run against the programs or OS facilities themselves:

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
- For both, the gate also covers:
  - the session-start hook firing once per incarnation, before any tool, on a fresh start and on a resume
  - the `RestartStartup` proof
  - the harness-side hook timeout pinned above `[timeouts] slow_path` plus a margin
  - the `attention_events` proof, where the adapter claims it

The service-manager gate is also integration-only. Under real launchd and real systemd, the Herdr server and the agents must keep running through a `kkd` crash, restart, and upgrade.

Two more placement modes carry the same gate, and both are unproven until they pass on a real host:

- `kkd --foreground` on a host with no user service manager, with the Herdr server as a detached process in its own session;
- macOS over SSH with no GUI login, in launchd's per-user domain.

A mode that fails the gate is unsupported.

Kiki's own end-to-end tests run unattended. They present an automation credential and rely on an activated policy, and they attach no Herdr client unless the test is about a client.

An upstream version that fails its probes uses hard restart or is unsupported. It is never modeled optimistically.

Core interpretation logic belongs in deep-module tests against fakes.

## Multi-machine checks after v1

Test each remote feature with a client on one machine and the thread's
daemon on another. For example, revoke a viewer's terminal access while
the connection is open. Its terminal should close while the agent keeps
running. See the [checks before release](13-architecture/remote-access.md#checks-before-release)
for profile setup, account selection, reconnects, and retries.
