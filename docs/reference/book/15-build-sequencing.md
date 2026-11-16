# Build Sequencing

The riskiest v1 assumption is the cascade path. (The cascade is how kiki carries a parent thread's changes into the threads that follow it.) That path crosses four hard pieces: jj's native descendant evolution, stale-workspace materialization, explicit parent-tip advance, and each harness's tool boundary — Claude Code's parallel batch and Codex's proven-serial hook coverage. Validate that path before investing in the full daemon. A sequential single-hook demo is not sufficient evidence for Claude Code. And Claude Code's proofs are not evidence for Codex.

The second risk is the terminal runtime. Kiki hosts threads in Herdr, and Herdr does not itself provide idempotent provisioning, a managed restore, caller-local focus, or proof that processes exited (see [Terminal runtime](13-architecture/terminal-runtime.md)). Those are kiki contracts with their own proofs. The implementation therefore starts with one managed thread, then proves restart, reconciliation, and safe close, and only then builds follows and cascade on top. The cascade proof of concept below can run in parallel from the first day, because it needs no daemon and no terminal runtime.

## Proof of concept

Before committing to the full architecture, build a one-shot proof of concept:

1. Create two jj workspaces that share a parent revision. (A jj workspace is an extra working directory attached to the same repository.)
2. Launch a Claude Code agent in the descendant workspace with a generated, launch-scoped settings source. Prove that kiki is the only matching `PreToolUse` hook, even when user-global, project, and project-local fixtures define competing `PreToolUse` hooks. Prove that the tracked `.claude/settings.json` is untouched. If launch isolation is unavailable, exercise the ownership-tracked `.claude/settings.local.json` fallback instead, and prove both inherited-hook exclusion and conflict-safe restoration.
   2a. Launch a Codex agent the same way, under a generated `CODEX_HOME` with kiki's hooks pre-trusted and authentication provisioned. Prove that hook fixtures from the user-global `~/.codex/`, the workspace `.codex/`, plugins, and managed policy do not execute in the managed process. Prove the pinned version dispatches tools serially (subagents included) and requests a new tool only after the model has consumed the previous call's result. Prove it fires `PreToolUse` for every workspace-observing tool, or that the generated config disables the rest. Prove it returns a deny payload to the model byte-identically while the denied tool never executes. Prove it emits `Stop` on turn completion. Prove that a denied call fires no post-tool event, so the blocked single-call batch's completion must be reported by the next turn-scoped hook event, not by the emitting hook's own crash-fragile RPC. Prove that the launcher converts a dead sidecar under an active barrier into a generic blocking deny. Prove that the session record durably contains each tool result as returned to the model, so acknowledgement can require the byte-identical delivery receipt, while a contrary receipt redelivers on the arriving batch. Prove that the generated config pins the harness-side hook timeout above the slow-path bound. Prove that acknowledgement keys on a serially later `tool_use_id`, not on Codex's `turn_id`, which spans many model steps. A failed proof drops that version to `RestartStartup` or marks it unsupported.
3. Amend the ancestor revision from the parent workspace. Prove that jj evolves the descendant in repository state while leaving its files stale.
4. Prove that kiki can classify that exact base transition as `NativeRewrite` without pinning the volatile child tip. Then use `WorkspaceProbe` to distinguish `FreshClean`, `FreshDirty`, `StaleClean`, `StaleDirty`, and `Unknown` at a PreToolUse boundary.
5. Prove that the parent workspace's `@` (its current working-copy commit) advances independently of its bookmark. Persist that exact live head, and classify `ParentAdvance` from it. Explicitly rebase only a validated single-parent child chain. Prove that merge, multiple-root, and foreign-descendant fixtures stop as `TopologyDiverged`.
6. Prove that A→B→C repository evolution can affect multiple descendant commits at once, while B and C materialize independently at their own boundaries.
7. Prove clean native materialization, and direct human materialization that creates no new op-log head. For unsnapshotted edits: create an external recovery bundle, enumerate divergent successors, and prove that kiki never resumes on a clean tree that hides the edits.
8. Evaluate `--no-integrate-operation` plus `jj op integrate` as the planned-rebase mechanism. Include conflicts, concurrent operations, and crash recovery.
9. Make one assistant response issue at least three parallel tools. Permute which logical tool's hook arrives first with pending work. Prove that the first admission fixes `Block`, that every call in the batch is blocked, that exactly one materialization occurs, and that concurrent hooks receive a byte-identical payload. Also prove that a first-admission `PassThrough` defers work detected later in that batch.
10. Prove that `PostToolBatch` marks only batch completion, and that acknowledgement occurs only at a `PreToolUse` from a provably later model turn. Exercise duplicate, missing, stale, reordered, and crash-interrupted completion events. If the adapter cannot prove model-turn and batch identity, demonstrate the hard-restart fallback before allowing any replacement-process tool.
11. Prove that one `sync_intent` owns reconciliation, the embedded payload, the delivery barrier, and acknowledgement, through crash injection at every transition. In-memory batch state must be reconstructible and must never be authoritative.
12. Prove that the agent receives a synthetic result, re-reads the affected files, and continues coherently.
13. Evaluate the operation-frontier sampler on the pinned jj version: list every operation head without creating, merging, or snapshotting anything, including while another process is writing. Prove that every read kiki needs works at an exact operation id with the working copy ignored, in a stale workspace and with several heads.

The PoC needs no daemon, no terminal runtime, no TUI, and no polished CLI. Shell scripts are enough. It should answer one question: is the hardest coordination primitive real? Failure of exclusive hook isolation or batch-boundary identification blocks soft cascade delivery; v1 must then use hard restart for the affected harness version or declare it unsupported.

## First commit

Scaffold the Rust workspace:

- `kiki-core` library;
- `kkd` daemon binary;
- `kk` CLI binary;
- `kk-hook` sidecar binary.

Get gRPC working end-to-end over a unix socket, with a ping/pong call and one test.

## Implementation sequence

Three stages, in order. Each stage ends at a gate with observable acceptance criteria. A later stage does not start on a failed gate; it either fixes the proof or narrows the contract in the owning chapter first. The stages build the acceptance slice in [Orientation](01-orientation.md); they are an order of work, not a second scope list.

Every stage runs against one explicitly pinned Herdr build and one pinned jj version. The Herdr candidate is a build at or after source commit `ee5bfb5041bb`, which contains the macOS terminal-application-quit fix that release 0.9.5 lacks. Results from one build are not evidence for another.

### Stage 1 — one managed thread

Build the smallest end-to-end path: `kk init`, `kk new <name>`, `kk attach`, and the read-only `kk ls`, with the approval broker that `kk init` and `kk new` require and the attach half of `TerminalClient`.

1. Start, find, and verify the dedicated Herdr server with kiki's generated configuration. Record the server instance.
2. Create the jj workspace and the initial working-copy change. Persist the live head and place the checkpoint bookmark at that exact commit.
3. Prepare the thread credential and the isolated launch settings.
4. Provision the terminal group through the journaled protocol, with the pane launcher as the direct child of the `agent` pane.
5. Open the launch gate, start the harness as the launcher's child, and enter `Active` only on the ready handshake.
6. Track the checkpoint bookmark through native successors as the agent edits.

Stage 1 gate:

- **Isolation.** The dedicated server uses only kiki's configuration, socket, and state. The user's default Herdr server, its configuration, and its terminals are byte-identical and undisturbed before and after.
- **Gated launch.** With crash injection at every creation step, the harness never runs before the journal, credential, exclusive settings, live head, checkpoint, and terminal binding are durable. The thread is `Creating` or `CreateFailed` until the matching ready handshake. A Herdr success reply, a visible pane, or an activated gate alone never produces `Active`.
- **Duplicate provisioning.** Drop the reply to the create call, drop the reply to the layout call, and crash `kkd` between them and after them, each in turn. Recovery ends with exactly one bound terminal group and exactly one harness process for the thread. If a second group was created, its launchers were refused and never started a harness, and the group is removed only after its processes are verified gone. No run produces two harness processes in one workspace.
- **Harness exit.** Killing the harness under a live launcher retires the incarnation and shows the agent `blocked`; the thread is not `ProjectionDiverged`, and a replacement incarnation starts on the same launcher through a fresh gate. Killing the launcher raises `TerminalMissing`.
- **Launcher transparency.** Through the launcher, real Claude Code and real Codex each receive input, resize, interrupt, and paste correctly, and copy mode and scrollback work. The harness exiting leaves the pane and an exit report, not a vanished pane.
- **Checkpoint evolution, part one.** The first edit after `kk new` snapshots, rewrites the checkpointed commit, and moves the bookmark; kiki records a native succession and raises no issue. `jj new` leaves the bookmark behind and status reads `behind`. `jj describe` and a rebase are successions. An external `jj bookmark move` raises `BookmarkMoved`. Divergent successors raise `BookmarkConflicted`. `jj abandon` of the bookmarked commit raises `BookmarkMissing`. `jj split` of the bookmarked live head is accepted as a different-change succession on the owned chain.
- **Provisioning moves no one.** With two clients attached and viewing other threads, creating a thread, cleaning up a duplicate group, and restarting a terminal group move neither client's view.
- **jj reads.** Every jj read `kkd` runs is pinned to an exact operation id and ignores the working copy. The only unpinned commands are the closed list in [Invariants](02-invariants.md#operation-history-is-a-dag), each under its lock and single-head precondition. A test that counts operations shows `kk ls`, `kk status --no-jj`, and the watcher create none, snapshot nothing, and never merge operation heads.

### Stage 2 — restart, reconciliation, and safe close

Add `kk switch`, `kk close`, `kk reopen`, `kk repair`, the projection audit, and `ProcessSupervisor`. Add a second thread and a second attached client at the start of this stage; they expose wrong-target actions and focus broadcasts that a single-pane demo hides.

Stage 2 gate:

- **Client changes.** Detaching a client, killing a client, and attaching a second client change nothing in kiki's state and stop no process.
- **`kkd` restart.** Killing and restarting `kkd` while agents run leaves every agent running. `kkd` verifies the same server instance, reconciles from a snapshot, and continues the same bindings and incarnations. In-flight sagas resume from their journals.
- **Cold restore.** Stop and restart the Herdr server gracefully, and separately kill it. Afterwards the server instance differs; workspace, tab, and pane ids recur; launch environment and metadata tokens are gone; panes hold plain shells. Every thread bound to the old instance reads `ProjectionDiverged` with `TerminalMissing`, and none reads `Active`. Herdr resumes no agent on its own. A `kk repair` restart issues a rotated credential, regenerated settings, a new gate, and a new handshake, and re-proves exclusive hooks before `Active`. A thread is never bound from a restored id or label; a relabeled or reordered restored layout binds nothing to the wrong thread.
- **Event loss.** Force the event stream to drop and to report loss. Kiki resyncs from a snapshot, detects a group closed during the gap, and republishes the label. A label overwritten by another socket caller is republished and is never read as input. The same holds for sidebar tokens when that v1.x surface ships.
- **Caller-local focus.** With two clients attached and viewing different threads, `kk switch` typed in one client moves only that client; a keybinding-invoked switch moves only the invoking client; a `kk switch` run by an agent's tool call or from a pane nobody is viewing moves no one. Without the `client_targeted_focus` capability, `kk switch` fails naming the capability and moves no one. `kk switch --all-clients` moves every client and says so. This criterion cannot pass until the client-targeted focus extension exists in the pinned build; until then the gate stays open, and the contract is not weakened to close it.
- **Orphan recovery.** Run a worker that ignores hangup and writes into the workspace, then kill the terminal server. The worker survives and appears in no terminal view. Kiki reports `OrphanedProcess` with the worker's recorded identity, starts no replacement agent in that workspace, and refuses to forget or delete it. The approved repair terminates exactly the recorded identities, verifies their exit, and unblocks. Repeat with a worker that leaves its session during a graceful server stop.
- **Quiescence.** Freeze a group with an agent, a shell, a `user` pane, a background job, and a process that forks during the freeze. The discovered set grows until two consecutive samples match. A process that was already stopped stays stopped after resume. An unrecorded process holding a file in the workspace makes the result `Unknown`. A pane split during the freeze, a file written after the final proof, or a set that never stabilizes preserves the files and takes verified resume. A failed final check resumes and verifies the same processes and the same terminal group; a failed resume becomes `CloseFailed`, never a dead `Active`.
- **Verified exit.** Close a group containing a process that survives Herdr's teardown. Herdr replies success; kiki still finds the survivor by its recorded identity, terminates it, verifies exit, and only then forgets and deletes the workspace. When exit cannot be verified the directory remains and the thread is `CloseFailed`.
- **Close under restart.** Crash `kkd`, and separately restart the Herdr server, at every `CloseCommit` step. Before the final proof the thread resumes or fails loudly; after it, recovery re-verifies exit by recorded identity and completes. No path deletes a workspace on the strength of a restored layout or a missing pane.
- **Checkpoint evolution, part two.** Close a thread, then rewrite one of its ancestors from another workspace. The closed thread's bookmark follows to a same-change successor; kiki advances the expected target and the archived head together and raises no issue, and `kk reopen` recreates the workspace at that commit. A different-change move on a closed thread raises `BookmarkMoved`.

### Stage 3 — follows and cascade

Promote the cascade proof of concept into the daemon: `OpLogWatcher`, `OpAttribution`, `AncestryQuery`, `CascadeOrchestrator`, `WorkspaceProbe`, `WorkspaceRecovery`, `kk-hook`, and then `kk thread detach`, `kk log`, `kk status`, and the audit reads.

Stage 3 gate:

- every numbered proof in the proof of concept, now through the daemon and with the harness running under the pane launcher in a terminal group;
- **jj concurrency.** Produce two operation heads from concurrent commands. The watcher records both, classifies each head's view without merging them, and blocks checkpoint-dependent lifecycle steps while the views disagree. Kiki's own mutations name one exact head and create no fork. When a lifecycle step needs a single view, kiki integrates deliberately and attributes that operation. A run of `kk ls`, `kk status --no-jj`, and watcher polling during the divergence creates no operation.
- **Dirty stale update.** `jj workspace update-stale` over unsnapshotted edits exits successfully while the edits live only in a divergent successor. Kiki never treats that success as preservation: recovery enumerates successors at exact operations, verifies where the edits are, and does not resume on the tree that hides them.
- **Terminal signals are not boundaries.** With the agent's screen idle, Herdr reporting the agent idle, and text queued in the pane, no reconciliation runs and no intent is acknowledged until the harness boundary proofs in [Cascade](05-cascade.md) hold.
- **Cascade across a terminal restart.** Restart the Herdr server with an intent `Materialized` or `Delivered` but unacknowledged. The old incarnation is retired without acknowledgement, and the restarted incarnation receives the saved payload through `RestartStartup` before any tool runs.

## Foundation order

Within the stages, build modules in this order:

1. `TerminalRuntime` with its Herdr adapter and fake, the pane launcher, server-instance tracking, and `TerminalClient::attach`.
2. `AuthEnforcer`, the enrolled foreground presenter, the two-phase one-shot approval broker, and scoped/unscoped SQLite audit interception.
3. `ThreadLifecycleSaga` for creation, the database-backed harness gate, and bookmark checkpointing with successor tracking.
4. `ProcessSupervisor` with its OS adapter and fake, then freeze/recheck close, reopen, and the orphan scan.
5. `ProjectionReconciler`, stable repair plans, and `kk repair`.
6. `TerminalClient` caller resolution and `kk switch`.
7. `OpLogWatcher` with the frontier sampler, `OpAttribution`, and `AncestryQuery`.
8. `CascadeOrchestrator` base-transition classification; `WorkspaceProbe`/`WorkspaceRecovery`; the intent-owned batch barrier and delivery; native materialization; and explicit advance, integrated with `kk-hook` and `PostToolBatch`.
9. Minimal `ConfigLoader`, `LogRenderer`, `StatusRenderer`, `kk log`, `kk status`, `kk thread detach`, and the audit-read commands.

v1.x polish (enumerated in [Orientation](01-orientation.md)) builds on top of that, in this order:

1. Stack-aware `kk publish`, lazy GitHub validation, and editor integration.
2. Transcript capture, human reads, durable provider-consent management, consented reopen catch-up, and then consent-gated same-thread MCP.
3. Metadata ownership, plus auto-describe/auto-rename and the full configuration mutation surface.
4. The `shell` and `ui` role panes, Herdr sidebar tokens, the overlay TUI, GitHub polling and comments, and auto-archive.

## Upstream dependencies

Two things must exist in Herdr before the acceptance gate can pass; neither blocks Stage 1.

- **Client-targeted focus**, as specified in [Terminal runtime](13-architecture/terminal-runtime.md#caller-local-focus). Propose it upstream at the start of Stage 1. If it cannot land, the choice between carrying a patch and changing the `kk switch` contract is a new decision record, not an implementation detail.
- **A release containing the macOS terminal-application-quit fix.** Until one exists, macOS testing pins a source build.

The optional extensions — request keys, a public boot id, a mutation fence, a termination receipt, and an event cursor — each replace adapter work that is already safe without them. Request one only when a stage shows the adapter path is too slow or too fragile.

## Acceptance integration gate

[Orientation](01-orientation.md#v1-contract) is the sole enumeration of the acceptance slice. The integration gate exercises every item in that ledger together, against a real jj repo, a real dedicated Herdr server at the pinned candidate build, and each shipped harness — Claude Code and Codex, on each supported platform. This chapter defines build order, not a second scope list. Passing the gate requires neither `gh` nor network access beyond the configured harness. V1.x work deepens the accepted coordinator; it cannot substitute for a missing ledger item.

## Budget

The expected v1 build budget is:

- acceptance slice: 7-10 weeks, plus up to 1 week for the second harness adapter's launch-isolation and boundary proofs. Two to three of those weeks are the terminal runtime adapter, the pane launcher, and `ProcessSupervisor`, which the earlier tmux-based estimate did not carry. The estimate excludes waiting for upstream Herdr changes. The protocol, sidecar, and orchestrator are shared; the Codex-specific work is the generated `CODEX_HOME`, the version fixtures, and the gate;
- first v1.x workflow tranche (publish and transcript): 3-5 additional weeks;
- edge-case buffer: 1-2 weeks.

The buffer belongs to terminal reconciliation and process-supervision cases, core op-log classification and restart catch-up cases, exclusive hook-settings compatibility, parallel-batch barriers, lifecycle compensation, projection repair, jj op-id dedupe, and cascade retry paths. Additional harness and version diagnostics, and non-core op-log compatibility cases, remain in their v1.x tranche. Transcript and sidebar edge cases likewise do not consume the acceptance buffer.
