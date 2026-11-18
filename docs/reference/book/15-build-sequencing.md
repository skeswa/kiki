# Build Sequencing

This chapter says in what order to build kiki, and what each step has to prove before the next one starts.

The riskiest v1 assumption is the cascade path. (The cascade is how kiki carries a parent [thread](appendix-a-glossary.md#thread)'s changes into the threads that [follow](appendix-a-glossary.md#follows) it.) That path crosses four hard pieces:

- [jj](https://docs.jj-vcs.dev/latest/)'s native descendant evolution: jj rewrites a child commit by itself when its ancestor changes;
- stale-workspace [materialization](appendix-a-glossary.md#materialization): updating a [workspace](appendix-a-glossary.md#workspace)'s files after its commit changed;
- explicit parent-tip advance;
- each [harness](appendix-a-glossary.md#harness)'s tool boundary: [Claude Code](https://docs.claude.com/en/docs/claude-code/overview)'s parallel batch and [Codex](https://github.com/openai/codex)'s proven-serial hook coverage. (A harness is the coding-agent program.)

Validate that path before investing in the full [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>). A sequential single-hook demo is not sufficient evidence for Claude Code. And Claude Code's proofs are not evidence for Codex.

The second risk is the terminal runtime. Kiki hosts threads in [Herdr](appendix-a-glossary.md#herdr), a [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer). Herdr does not itself provide these four things (see [Terminal runtime](13-architecture/terminal-runtime.md)):

- [idempotent](https://en.wikipedia.org/wiki/Idempotence) provisioning (setup that is safe to repeat),
- a managed restore,
- [caller-local focus](appendix-a-glossary.md#caller-local-focus), or
- proof that processes exited.

Those are kiki contracts with their own proofs. The implementation therefore starts with one managed thread. It then proves restart, reconciliation, and safe close. Only then does it build follows and cascade on top.

The cascade proof of concept below needs no daemon and no terminal runtime. Three of its proofs are entry gates for Stage 1, because Stage 1 cannot bring a thread to `Active` without them: the launch-isolation and session-start proofs of step 2 and of step 2a, one pair for each harness, and step 13 (the frontier sampler). The rest of the proof of concept runs in parallel with the stages from the first day. That includes the Codex boundary proofs in step 2a.

## Proof of concept

Before committing to the full architecture, build a one-shot proof of concept (PoC). Each numbered step is one thing to build or prove.

1. Create two jj [workspaces](appendix-a-glossary.md#workspace) that share a parent revision. (A jj workspace is an extra working directory attached to the same repository.)
2. Launch a Claude Code agent in the descendant workspace with a generated, launch-scoped settings source.
   - Prove that kiki is the only matching [`PreToolUse`](appendix-a-glossary.md#pretooluse) hook, even when user-global, project, and project-local fixtures define competing `PreToolUse` hooks. (A hook is a program the harness runs at a set moment; this one runs before each tool call. A fixture is a prepared test setup.)
   - Prove that the tracked `.claude/settings.json` is untouched.
   - If launch isolation is unavailable, exercise the ownership-tracked `.claude/settings.local.json` fallback instead. Prove both inherited-hook exclusion and conflict-safe restoration.
   - Prove that the generated settings declare kiki's session-start hook, and that it fires exactly once per [incarnation](appendix-a-glossary.md#incarnation) (one launch of the harness process), before any tool, on a fresh start and on a resume. If this fails, the pinned Claude Code version is unsupported, and that is recorded as a new decision record.
   - Prove that the generated settings pin the harness-side hook timeout above `[timeouts] slow_path` plus a margin.
   - Prove that when the `kk-hook` process dies before it answers, the pinned Claude Code version does not run the tool as if the hook had allowed it. If this fails, that version is unsupported for cascade delivery.
   - Also establish, or record as unavailable, a proof of turn completion and [agent quiescence](appendix-a-glossary.md#agent-quiescence) (the agent is idle) for the pinned Claude Code version. This is a proof that does not depend on a stop hook.
   - Without it, three things follow: the adapter reports `quiescence_detection: false`, `kk ls` shows `working` whenever the harness is alive and not blocked (never `idle` or `finished`), and cascade delivery relies on tool boundaries alone.
   - Establish, or record as unavailable, the `attention_events` proof: name the harness event that reports a permission prompt and show that it fires. Without it, permission-prompt detection for this harness is v1.x. Crash detection still gives `blocked`.

   2a. Launch a Codex agent the same way, under a generated `CODEX_HOME` with kiki's hooks pre-trusted and authentication provisioned.
   - This step has two parts. The launch-isolation proof (the first one below) and the session-start proof are Stage 1 entry gates. Every other proof in this step is a Codex boundary proof. The boundary proofs run in parallel with Stages 1 and 2.
   - Prove that hook fixtures from the user-global `~/.codex/`, the workspace `.codex/`, plugins, and managed policy do not execute in the managed process.
   - Prove the pinned version dispatches tools serially (subagents included) and requests a new tool only after the model has consumed the previous call's result.
   - Prove it fires `PreToolUse` for every workspace-observing tool, or that the generated config disables the rest.
   - Prove it returns a deny payload to the model byte-identically while the denied tool never executes.
   - Prove it emits `Stop` on turn completion.
   - Prove that a denied call fires no post-tool event. So the blocked single-call batch's completion must be reported by the next turn-scoped hook event, not by the emitting hook's own crash-fragile [RPC](https://en.wikipedia.org/wiki/Remote_procedure_call).
   - Prove that a barrier-covered call never fails open. [`kk-hook`](appendix-a-glossary.md#kk-hook) answers an admitted call with a generic blocking deny when `slow_path` expires or the reconciliation's owner crashes. A `kk-hook` process that dies before it answers must not let the tool run either: the pinned Codex version must not run the tool as if the hook had allowed it. If this fails, that version is unsupported for cascade delivery. While `kkd` is unreachable, a hook that finds the thread's [barrier marker](appendix-a-glossary.md#barrier-marker) answers with the generic blocking deny.
   - Prove that the session record durably contains each tool result as returned to the model. Then acknowledgement can require the byte-identical [delivery receipt](appendix-a-glossary.md#delivery-receipt), while a contrary receipt redelivers on the arriving batch.
   - Prove that the generated config pins the harness-side hook timeout above `[timeouts] slow_path` (the [slow-path bound](appendix-a-glossary.md#slow-path-bound), default `30s`) plus a margin.
   - Prove that acknowledgement keys on a serially later `tool_use_id`, not on Codex's `turn_id`, which spans many model steps.
   - Prove that the generated config declares the `SessionStart` hook, and that it fires exactly once per incarnation, before any tool, on a fresh start and on a resume. If this fails, the pinned Codex version is unsupported, and that is recorded as a new decision record.
   - Establish, or record as unavailable, the `attention_events` proof, as in step 2.
   - A failed isolation proof marks the version unsupported. A failed boundary proof drops that version to [`RestartStartup`](appendix-a-glossary.md#restartstartup-delivery-proof) delivery, which step 15 proves regardless.

3. Amend the ancestor revision from the parent workspace. Prove that jj evolves the descendant in repository state while leaving its files stale.
4. Prove that kiki can classify that exact [base transition](appendix-a-glossary.md#base-transition) as [`NativeRewrite`](appendix-a-glossary.md#nativerewrite) without pinning the volatile child tip. Then use [`WorkspaceProbe`](appendix-a-glossary.md#workspaceprobe) to distinguish `FreshClean`, `FreshDirty`, `StaleClean`, `StaleDirty`, and `Unknown` at a PreToolUse boundary.
5. Prove that the parent workspace's `@` (its current working-copy commit) advances independently of its [bookmark](appendix-a-glossary.md#bookmark).
   - Persist that exact [live head](appendix-a-glossary.md#live-head), and classify [`ParentAdvance`](appendix-a-glossary.md#parentadvance) from it.
   - Explicitly rebase only a validated single-parent child chain.
   - Prove that merge, multiple-root, and foreign-descendant fixtures stop as [`TopologyDiverged`](appendix-a-glossary.md#topologydiverged).
6. Prove that A→B→C repository evolution can affect multiple descendant commits at once, while B and C materialize independently at their own boundaries.
7. Prove clean native materialization, and direct human materialization that creates no new [op-log](https://docs.jj-vcs.dev/latest/operation-log/) head. For unsnapshotted edits:
   - create an external [recovery bundle](appendix-a-glossary.md#recovery-bundle),
   - enumerate divergent successors, and
   - prove that kiki never resumes on a clean tree that hides the edits.
8. Evaluate `--no-integrate-operation` plus `jj op integrate` as the planned-rebase mechanism. Include conflicts, concurrent operations, and crash recovery.
   - It passes when all of these hold on the pinned jj version:
     - a rebase run with `--no-integrate-operation` leaves the operation heads and every workspace's files unchanged until `jj op integrate` runs;
     - a rebase that produces conflicts can be inspected at its own operation id before it is integrated;
     - an external operation that lands in between yields two heads after integration, never a silent merge and never a lost operation;
     - a crash between the rebase and the integration leaves an operation that kiki can find by id and then integrate or leave unintegrated.
   - If any of these fails, the mechanism is not used. The planned rebase then runs as an ordinary pinned mutation, as [Reading and changing jj](14-testing.md#reading-and-changing-jj-at-an-exact-operation) describes, and the choice is written down as a decision record.
9. Make one assistant response issue at least three parallel tools. Permute which logical tool's hook arrives first with pending work.
   - Prove that the first admission fixes `Block`.
   - Prove that every call in the batch is blocked.
   - Prove that exactly one materialization occurs.
   - Prove that concurrent hooks receive a byte-identical payload.
   - Also prove that a first-admission [`PassThrough`](appendix-a-glossary.md#batch-admission) defers work detected later in that batch.
10. For every soft-delivery adapter, prove that all writers have stopped at the boundary and that a receipt for the exact payload belongs to the later model turn's conversation. Test a timeout before admission on one sibling and generic denials on all siblings. Use `RestartStartup` if the installed version fails these proofs.
    - Exercise duplicate, missing, stale, reordered, and crash-interrupted completion events.
    - If the adapter cannot prove model-turn and batch identity, demonstrate the hard-restart fallback before allowing any replacement-process tool.
11. Prove that one [`sync_intent`](appendix-a-glossary.md#sync-intent) owns reconciliation, the embedded payload, the [delivery barrier](appendix-a-glossary.md#delivery-barrier), and acknowledgement, through crash injection at every transition. (Crash injection means killing a program at a chosen step.) In-memory batch state must be reconstructible and must never be authoritative.
12. Prove that the agent receives a synthetic result, re-reads the affected files, and continues coherently.
13. Prove the [operation-frontier](appendix-a-glossary.md#operation-frontier) sampler ([`OpFrontierSampler`](appendix-a-glossary.md#frontier-sampler)) on the pinned jj version. This step is a Stage 1 entry gate. It passes when all of these hold:
    - The sampler lists every operation head for one, two, and three heads, from the main workspace and from an added workspace.
    - A sample creates no operation, merges no heads, and snapshots nothing. That holds while another process is writing.
    - A sample taken while jj replaces one head with another returns an antichain: a set in which no head is an ancestor of another. If the sample is not an antichain, the sampler retries within `[timeouts] frontier_retry` (default `2s`). It never returns a set that contains both a head and its ancestor.
    - Every read kiki needs works at an exact operation id with the working copy ignored, in a stale workspace and with several heads.

    If no supported sampler passes, the outcome is to read the operation store through jj-lib (jj's own Rust library), and that choice is recorded as a decision. If that fails too, stop: the build does not go on.

14. Prove `RestartStartup` delivery for Claude Code. This proof is required. It does not depend on any other proof failing first. Prove all three facts on the pinned version:
    - The launch specification makes the saved payload the mandatory first harness input, and it carries the startup delivery id in the launcher environment.
    - The session-start hook reports that exact id with `ReportHarnessReady`.
    - The first pre-tool hook call of a [model turn](appendix-a-glossary.md#model-turn) in that incarnation arrives only after the model has taken in the startup input, so it can serve as the acknowledgement.

15. Prove the same three facts for Codex, on a fresh start and on `codex resume`.

If step 14 or step 15 fails for a harness, that harness ships managed sessions without cascade delivery, so its threads cannot follow other threads. That scope cut is a new decision record.

The PoC needs no daemon, no terminal runtime, no [TUI](https://en.wikipedia.org/wiki/Text-based_user_interface), and no polished CLI. Shell scripts are enough. It should demonstrate safe cascade reconciliation and context delivery for each harness.

Failure of exclusive hook isolation makes the affected harness version unsupported. Failure of batch-boundary identification blocks soft cascade delivery. v1 must then use hard restart with `RestartStartup` delivery for that version, as proved in step 14 or 15.

## First commit

Scaffold the [Rust](https://www.rust-lang.org/) [workspace](https://doc.rust-lang.org/cargo/reference/workspaces.html):

- `kiki-core` library;
- [`kkd`](appendix-a-glossary.md#kkd) daemon binary;
- `kk` CLI binary;
- [`kk-hook`](appendix-a-glossary.md#kk-hook) sidecar binary.

Get [gRPC](https://grpc.io/) working end-to-end over a [unix socket](https://en.wikipedia.org/wiki/Unix_domain_socket), with a ping/pong call and one test.

## Implementation sequence

There are three stages, in order.

- Each stage ends at a gate with observable acceptance criteria.
- A later stage does not start on a failed gate. It either fixes the proof or narrows the contract in the owning chapter first.
- The stages build the [acceptance slice](appendix-a-glossary.md#acceptance-slice) in [Orientation](01-orientation.md). They are an order of work, not a second scope list.

Every stage runs against one explicitly pinned [Herdr](appendix-a-glossary.md#herdr) build and one pinned [jj](https://docs.jj-vcs.dev/latest/) version.

- The Herdr candidate is source commit `ee5bfb5041bb`.
- Every Herdr capability this book uses, other than the [client-targeted focus](appendix-a-glossary.md#client-targeted-focus) extension, was also observed in release 0.9.5.
- Pin exactly one build per stage. Results from one build are not evidence for another.
- So the [acceptance gate](appendix-a-glossary.md#acceptance-gate) re-runs every stage gate on the build that carries the client-targeted focus extension. A stage gate passed on an earlier build does not count there.
- The deadline for deciding what to do if the extension has not landed is the Stage 2 exit. See [Upstream dependencies](#upstream-dependencies).

### Stage 1: one managed thread

Build the smallest end-to-end path: `kk init`, `kk new <name>`, `kk attach`, and the read-only `kk ls`. That path needs more than it looks like, and all of it belongs to this stage:

- the approval broker that `kk init` and `kk new` require;
- the [automation policy](appendix-a-glossary.md#automation-policy) engine, [`PolicyApproval`](04-authority.md#policyapproval), [automation credentials](appendix-a-glossary.md#automation-credential), and [`kk automation`](09-commands.md#kk-automation). They are here because kiki's own end-to-end tests need unattended approvals: those tests present an automation credential and rely on an activated policy;
- [`kk daemon install`](09-commands.md#kk-daemon-install), the [exit codes](09-commands.md#exit-codes), [`--json`](09-commands.md#output-for-scripts) on every command this stage ships, and [`kk events`](09-commands.md#kk-events) with the `StreamRepoEvents` call behind every summary view, including a thread filter;
- the attach half of [`TerminalClient`](appendix-a-glossary.md#terminalclient);
- the minimal `ConfigLoader`;
- [`kkd`](appendix-a-glossary.md#kkd) bootstrapped under the user's service manager, or run as `kkd --foreground` on a host that has none;
- the inventory half of [`ProcessSupervisor`](appendix-a-glossary.md#processsupervisor), for the [orphan scan](appendix-a-glossary.md#orphan-scan) and launcher verification;
- [`kk-hook`](appendix-a-glossary.md#kk-hook), with two jobs only: the session-start ready report, and a pre-tool hook that always passes through (no cascade exists yet);
- both harness adapters' `launch_spec`, and the exclusive-hook proof for each;
- the Stage 1 subset of the op-log watcher:
  - `OpFrontierSampler`,
  - the op-DAG cache (kiki's stored copy of jj's operation graph),
  - classifier rules 0–6 (the checkpoint and bookmark rules in [Op-log watcher](13-architecture/op-log-watcher.md)),
  - attribution of kiki's own operations,
  - the ancestry query for the [owned chain](appendix-a-glossary.md#owned-stack),
  - detection of rewritten operation history, with silent [re-anchoring](appendix-a-glossary.md#re-anchoring), and
  - restart catch-up for bookmarks and rewrites, so that a gate that restarts `kkd` in Stage 1 or Stage 2 needs nothing from Stage 3; and
- the part of the projection audit that raises [`TerminalMissing`](appendix-a-glossary.md#terminalmissing) and the bookmark issues, plus the orphan scan that raises [`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess).

Repairing those issues is Stage 2.

Stage 1 has three entry gates from the proof of concept: the launch-isolation and session-start proofs of step 2, the same two proofs of step 2a, and step 13. It does not start until they pass. The Codex boundary proofs in step 2a are not entry gates. They run in parallel with Stages 1 and 2.

1. Start, find, and verify the [dedicated Herdr server](appendix-a-glossary.md#dedicated-herdr-server) with kiki's generated and validated configuration and a constructed environment. Record the [server instance](appendix-a-glossary.md#server-instance).
2. Create the jj [workspace](appendix-a-glossary.md#workspace) and the initial working-copy change. Persist the [live head](appendix-a-glossary.md#live-head) and place the checkpoint [bookmark](appendix-a-glossary.md#bookmark) at that exact commit.
3. Prepare the thread credential and the isolated launch settings.
4. Provision the [terminal group](appendix-a-glossary.md#terminal-group) through the journaled protocol, with the [pane launcher](appendix-a-glossary.md#pane-launcher) as the direct child of the `agent` pane.
5. Open the [launch gate](appendix-a-glossary.md#launch-gate), start the harness as the launcher's child, and enter `Active` only on the [ready handshake](appendix-a-glossary.md#ready-handshake).
6. Track the checkpoint bookmark through [native successors](appendix-a-glossary.md#native-successor) as the agent edits.

Stage 1 gate:

- **Isolation.** The dedicated server is kept apart from the user's own Herdr.
  - The dedicated server uses kiki's configuration file and its own socket and saved session.
  - The user's default Herdr server, its configuration file, and its terminals are byte-identical and undisturbed before and after.
  - A pane's [environment](https://en.wikipedia.org/wiki/Environment_variable) carries no redirected base-directory variables and nothing from the terminal that first ran `kk`.
  - jj, git, and the user's shell inside a thread read the user's ordinary configuration.
- **Configuration.** A corrupted or hand-edited generated configuration is regenerated before the server starts.
  - A file that fails kiki's validation prevents the start.
  - In no run does Herdr resume an agent, show onboarding, or check for updates.
- **Placement.** On macOS, quitting the terminal application that first ran `kk` leaves `kkd`, the server, and every agent running.
- **The server outlives `kkd`.** `kkd` starts the Herdr server as its own service-manager unit, not as a child inside `kkd`'s unit. That is a separate launchd job on macOS and a separate transient systemd user unit on Linux.
  - Under each real service manager, kill `kkd`, restart it, and upgrade it, each in turn.
  - Each time, the server and every agent keep running, with the same process identities.
  - When `kkd` comes back it finds the same [server instance](appendix-a-glossary.md#server-instance).
  - Two more placement modes must pass the same proof. Both are unproven gates, and a mode that fails is unsupported:
    - a host with no user service manager, such as many containers and CI runners. `kkd --foreground` runs under the operator's own supervisor and starts the Herdr server as a detached process in its own session;
    - macOS over SSH with no GUI login, where `kkd` and the server use launchd's per-user domain, not the GUI domain.
- **Server start record.** `kkd` writes a `terminal_servers` row in state `Starting` before it spawns a server, and moves it to `Open` once it has read the server's peer identity. Killing `kkd` between those two points leaves a state that the next start recovers from. It never leaves two servers.
- **Approvals.** `kk init` and `kk new` each run only after a one-shot approval of their plan. That is a human approval through the enrolled presenter, or a [policy approval](appendix-a-glossary.md#policy-approval) from a matching rule. A replayed or expired approval is refused and changes nothing. A caller with no terminal is refused with exit code 3 when no rule matches, and nothing changes.
- **Automation policy.** An activated policy can stand in for the human's confirmation, and for nothing else.
  - A matching `allow` rule lets `kk init` and `kk new` run with no terminal and no prompt. `kk` prints the plan and the rule's name.
  - A matching `require-human` rule beats any `allow` rule, and it matches whatever labels the plan carries. An `allow` rule does not match a plan that carries a [risk label](appendix-a-glossary.md#risk-label) the rule does not accept.
  - An edited `[automation]` section changes nothing until `kk automation apply` [activates](04-authority.md#activating-a-policy) it, with a foreground presenter confirmation or the Admin credential.
  - A `PolicyApproval` is single-use and bound to the plan digest. A replayed, expired, or drifted one is refused.
  - A plan that a safety proof refuses is still refused under `accept = ["*"]`.
  - Each `PolicyApproval` writes one audit row with the rule name, policy digest, principal, operation, and risk labels.
- **Headless first run.** On a machine with no human, no desktop session, and no enrolled presenter, this sequence succeeds from flags alone: `kk daemon install`; `kk automation apply --admin-credential-file <path>`; `kk automation credential create <name> --admin-credential-file <path>`; then `kk init` and `kk new` with the automation credential.
  - `kk daemon install` asks no question. This first install needs no credential, creates the Admin bootstrap credential, and prints its path.
  - `kk init` begins its approval with the automation credential, not Admin, and needs an `init` rule.
  - An operation with no matching rule fails closed with exit code 3.
- **No UI.** The whole Stage 1 path runs with zero attached Herdr clients and no desktop session. The Herdr server starts and serves with no client. See [headless](appendix-a-glossary.md#headless).
- **No prompt without a terminal.** With no terminal, `kk` never prompts. A command that would ask a question fails, changes nothing, and names the flag that answers it.
- **Scripting surface.** Every Stage 1 command prints its final result as JSON under `--json`, and the flag changes rendering only.
  - Each exit code from `0` to `5` is observed in its own case. Code `6` is observed with `kk wait` in Stage 2.
  - `kk events` prints one thread's events and the repo-wide events, replays from `--since <cursor>` with no gap, and keeps printing under `--follow`.
- **Launcher verification.** A launcher report is refused when its caller is not a child of the current server process, or when its pane's root process is not the caller. A report left over from a previous server lifetime that names a recycled Herdr id binds nothing and closes nothing.
  - A repeat of an accepted report from the same process identity gets the same answer. A different process presenting for a consumed role is refused and exits.
  - `agent` is the only [required role](appendix-a-glossary.md#required-role). A `shell` or `ui` launcher that does not report within `[timeouts] launcher_report` is recorded as absent with a warning, and provisioning still succeeds.
- **Gated launch.** With crash injection at every creation step, the harness never runs before these are durable: the journal, credential, exclusive settings, live head, checkpoint, and [terminal binding](appendix-a-glossary.md#terminal-binding).
  - The thread is `Creating` or `CreateFailed` until the matching ready handshake.
  - The ready handshake comes from `kk-hook` at the harness's session-start hook. It reaches `Active` for real Claude Code and for real Codex.
  - A handshake that does not arrive within `[timeouts] ready_handshake` ends in `CreateFailed`.
  - Each launch proves that kiki's hook is the only matching pre-tool hook. A competing hook fixture fails the launch before the agent receives a prompt.
  - A Herdr success reply, a visible pane, or an activated gate alone never produces `Active`.
- **Duplicate provisioning.** Drop the reply to the create call, drop the reply to the layout call, and crash `kkd` between them and after them, each in turn.
  - Recovery ends with exactly one bound terminal group and exactly one harness process for the thread.
  - If a second group was created, its launchers were refused and never started a harness. Its disappearance is confirmed from a snapshot and the OS rather than assumed.
  - No run produces two harness processes in one workspace.
- **Harness exit.** The harness exiting and the launcher exiting give different results.
  - Killing the harness under a live launcher retires the [incarnation](appendix-a-glossary.md#incarnation) and shows the agent `blocked`. The thread is not `ProjectionDiverged`.
  - Killing the launcher raises `TerminalMissing`. In a group with only an agent pane, the Herdr workspace disappears with it.
- **Compensation limits.** Compensation is the automatic cleanup of a failed creation.
  - A creation that fails before the gate opens, in a group holding only kiki's launchers, cleans up after itself.
  - A creation that fails after the harness ran, or after the human opened a pane, stops in `CreateFailed` with the workspace and the terminal group intact.
- **Launcher transparency.** Through the launcher, real Claude Code and real Codex each receive input, resize, interrupt, and paste correctly, and copy mode and scrollback work. The harness exiting leaves the pane and an exit report, not a vanished pane.
- **Checkpoint evolution, part one.** Kiki tracks the checkpoint bookmark through jj's own rewrites and reports other moves.
  - `jj undo` of a tracked succession pops the [expected target](appendix-a-glossary.md#expected-bookmark-target) back with no issue.
  - A conflicted bookmark is reported as conflicted even when one of its targets is the expected commit.
  - The first edit after `kk new` snapshots, rewrites the checkpointed commit, and moves the bookmark. Kiki records a native succession and raises no issue.
  - `jj new` and `jj commit` leave the bookmark where it was. Status reads `current` while the new head is empty and undescribed, and `behind` once it has content.
  - `jj describe` and a rebase are successions.
  - An external `jj bookmark move` raises [`BookmarkMoved`](appendix-a-glossary.md#bookmarkmoved).
  - Divergent successors raise [`BookmarkConflicted`](appendix-a-glossary.md#bookmarkconflicted).
  - `jj abandon` of the bookmarked commit hides the commit and deletes the bookmark. It raises [`CheckpointAbandoned`](appendix-a-glossary.md#checkpointabandoned).
  - `jj split` of the bookmarked live head is accepted as a different-change succession on the owned chain.
  - A different-change successor that lands on the thread's base is `BookmarkMoved`, because the base is not on the owned chain.
  - `jj op abandon` of an operation in the middle of the log is detected as rewritten operation history. The watcher does not treat the changed operation ids as new work.
- **Audit at start.** Killing the launcher, or the server, while `kkd` is down is found at the next `kkd` start. The audit raises `TerminalMissing`. The orphan scan raises `OrphanedProcess` for a recorded process that survived.
- **jj reads.** Every jj read `kkd` runs is pinned to an exact operation id and ignores the working copy (a [pinned read](appendix-a-glossary.md#pinned-read)).
  - The only unpinned commands are the closed list in [Invariants](02-invariants.md#operation-history-is-a-dag). Each runs under the per-repo [repo jj lock](appendix-a-glossary.md#repo-jj-lock), and the working-copy commands run only after a single-head sample.
  - A test that counts operations shows `kk ls` and the watcher create none, snapshot nothing, and never merge operation heads.

### Stage 2: restart, reconciliation, and safe close

Add `kk switch`, `kk close`, `kk reopen`, `kk repair`, the rest of the projection audit, and the freeze, resume, and termination halves of [`ProcessSupervisor`](appendix-a-glossary.md#processsupervisor). Add [`kk wait`](09-commands.md#kk-wait) and the `command` notification provider, and extend `--json` to the commands this stage ships.

Add a second thread and a second attached client at the start of this stage. They expose wrong-target actions and focus broadcasts that a single-pane demo hides.

Stage 2 gate:

- **Follow-up prompt.** For each supported Claude Code and Codex version, prove a later turn in the same running session with no viewer. Race submission with a permission prompt, agent replacement, and a lost reply. See [`kk prompt`](09-commands.md#kk-prompt). A missing proof blocks acceptance for that harness until the interface exists or a new decision changes scope.

- **Client changes.** Detaching a client, killing a client, and attaching a second client change nothing in kiki's state and stop no process.
- **`kkd` restart.** Killing and restarting `kkd` while agents run leaves every agent running, except an incarnation the unknown-batch rule must restart, once Stage 3 ships.
  - `kkd` verifies the same server instance, reconciles from a snapshot, and continues the same bindings and incarnations, with that one exception.
  - In-flight [sagas](appendix-a-glossary.md#saga) resume from their journals.
- **Provisioning moves no one.** Two clients are attached and viewing two different threads.
  - Creating a thread, reopening one, a terminal-restart repair, and cleaning up a duplicate group move neither client's view, apart from the exceptions [Terminal runtime](13-architecture/terminal-runtime.md#caller-local-focus) lists.
  - If this fails, the outcome is a second required upstream extension, recorded as a new decision record. The criterion is not dropped.
- **Cold restore.** Stop and restart the Herdr server gracefully, and separately kill it. (See [cold restore](appendix-a-glossary.md#cold-restore).)
  - Afterwards:
    - the server instance differs;
    - workspace, tab, and pane ids recur;
    - launch environment and [metadata tokens](appendix-a-glossary.md#sidebar-token) are gone;
    - panes hold plain shells.
  - Every thread bound to the old instance reads `ProjectionDiverged` with `TerminalMissing`, and none reads `Active`.
  - Herdr resumes no agent on its own.
  - A `kk repair` restart ([`restart-terminal`](appendix-a-glossary.md#restart-terminal)) does these things before `Active`:
    - it lists the [remnant](appendix-a-glossary.md#remnant-container) and [unbound containers](appendix-a-glossary.md#unbound-container) with their processes;
    - it checks that no recorded process survives outside the listed containers;
    - it freezes their processes and proves that each listed container holds exactly the processes recorded at freeze;
    - it disposes of them with [verified exit](appendix-a-glossary.md#verified-exit);
    - it runs the holder scan and the orphan scan again;
    - it provisions a fresh terminal group;
    - it issues a rotated credential, regenerated settings, a new gate, and a new handshake.
  - A copy of the agent that the human started by hand in a restored pane is on that list and is gone before the new agent starts.
  - No restored container is reused. A relabeled or reordered restored layout binds nothing to the wrong thread.
- **Failed terminal restart.** `restart-terminal` is a journaled lifecycle operation with its own step list.
  - Fail it after provisioning. `TerminalMissing` stays open and the thread stays `ProjectionDiverged`.
  - The half-made group is removed by [`cleanup-failed-restart`](appendix-a-glossary.md#cleanup-failed-restart), under the same limits as `cleanup-failed-create`.
  - If its freeze of remnant processes returns `Unknown`, it takes verified resume and the plan stops.
- **Unbound container.** Kill the `agent` launcher in a group that also holds a `user` pane, so the group survives.
  - The binding ends and the thread raises `TerminalMissing`. The surviving group is an unbound container.
  - Its processes are terminal members. No `OrphanedProcess` is raised for them.
  - `restart-terminal` and [`close-without-terminal`](appendix-a-glossary.md#close-without-terminal) each list that container with its processes and dispose of it.
- **Close without a terminal.** `close-without-terminal` follows the general close order. Nothing is terminated before the final proof. A failure before the final proof resumes the frozen processes and leaves every file in place.
- **Server replacement.** Change `[terminal] session`, `herdr_bin`, or `[paths] herdr_dir` while a server instance is open.
  - `kkd` does not start a second server. It keeps the old one and reports that a change is pending.
  - `kk repair --server` offers [`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server). The plan lists every thread and process the replacement stops, and it needs a one-shot approval.
  - Once approved, it stops the old server with verified exit and then starts a new one.
  - The same plan is the exit for a server that `kkd` did not start.
- **Event loss.** Force the event stream to drop and to report loss.
  - Kiki resyncs from a snapshot, detects a group closed during the gap, and republishes the label.
  - A label overwritten by another socket caller is republished and is never read as input.
  - The same holds for sidebar tokens when that v1.x surface ships.
- **Caller-local focus.** Two clients are attached and viewing different threads.
  - `kk switch` typed in one client moves only that client.
  - A `kk switch` run by an agent's tool call or from a pane nobody is viewing moves no one.
  - Without the `client_targeted_focus` capability, `kk switch` fails naming the capability and moves no one.
  - `kk switch --all-clients` moves every client and says so.
  - The capability-absent half of this criterion is what Stage 2 must pass.
  - The two-client half cannot pass until the client-targeted focus extension exists in the pinned build. It stays open without blocking Stage 3. It blocks the [acceptance gate](appendix-a-glossary.md#acceptance-gate). The contract is not weakened to close it.
  - If the extension has not landed by the Stage 2 exit, the choice between carrying a patch and changing the `kk switch` contract is made then, as a new decision record.
- **Orphan recovery.** Use a harness fixture that ignores hangup and writes into the workspace, then kill the terminal server.
  - The harness survives and appears in no terminal view.
  - Kiki reports [`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess) with the harness's recorded identity, starts no replacement agent in that workspace, and refuses to forget or delete it.
  - The repair plan is [`terminate-orphans`](appendix-a-glossary.md#terminate-orphans), with a one-shot approval. It terminates exactly the recorded identities, verifies their exit, and unblocks.
  - Repeat with a harness that leaves its session during a graceful server stop.
  - Repeat with a harness remnant: kill the harness under a live `agent` launcher while its tool child keeps running, so no incarnation is live. The child is an orphan even though kiki never recorded it. `terminate-orphans` runs freeze discovery rooted at the launcher, records what it finds under the approval, and terminates it with verified exit.
  - Then repeat the server kill with a tool child kiki never recorded. Its launcher is gone, so it is not a harness remnant, and no `OrphanedProcess` is raised. The [`restart-terminal`](appendix-a-glossary.md#restart-terminal) plan's holder scan names the child by pid and command and stops. Kiki does not signal it.
- **Quiescence.** Freeze a group with an agent, a shell, a [`user` pane](appendix-a-glossary.md#user-pane), a background job, and a process that forks during the freeze. (To freeze is to stop processes without killing them.)
  - The discovered set grows until two consecutive samples match.
  - A process that was already stopped stays stopped after resume.
  - An unrecorded process holding a file in the workspace makes the result `Unknown`.
  - Each of these preserves the files and takes [verified resume](appendix-a-glossary.md#verified-resume):
    - a pane split during the freeze,
    - a file written between the freeze and the [final proof](appendix-a-glossary.md#final-proof),
    - a frozen process holding a jj repository lock,
    - a step that runs past `[timeouts] frozen_step` before termination begins, or
    - a set that does not stabilize within `[timeouts] freeze_stabilize`.
  - A process that joins a listed container between preflight and the freeze is not drift. It is covered by the plan's container-scope statement, recorded at the freeze, and terminated with the rest.
  - Verified resume proves every role that was live at freeze time. A pane the user had closed before the freeze does not fail it.
  - Killing `kkd` in the middle of a freeze leaves no process stopped: recovery resumes every journaled row.
  - A [holder](appendix-a-glossary.md#holder) the approved plan names is accepted. Any other makes the result `Unknown`, and the report names its pid, its command, and how to clear it.
  - Where the adapter proves agent quiescence, `kk close` on a working agent stops in preflight and says why. Where it does not, preflight goes on with the warning, and a working agent shows up as approval drift and a verified resume.
  - A failed final check resumes and verifies the same processes and the same terminal group. A failed resume becomes `CloseFailed`, never a dead `Active`.
- **Termination order.** Close a group containing a process that handles hangup by writing a file.
  - Kiki kills each frozen process while it is still stopped and before the runtime closes anything. So the handler never runs and nothing is written after the final proof.
  - A write that does land after the final proof is caught by the [post-exit filesystem recheck](appendix-a-glossary.md#post-exit-filesystem-recheck): the directory remains and the thread is `CloseFailed`.
  - Herdr's success reply decides nothing.
  - Once termination has begun, a failure or an expired `[timeouts] verified_exit` wait is `CloseFailed`. It is never a resume.
- **Replacement incarnation.** Kill a harness while its tool child keeps running. The [`restart-agent`](appendix-a-glossary.md#restart-agent) plan refuses to open a gate until the launcher's process tree is empty, and reports the remnant as `OrphanedProcess`. The same check for the cascade's own replacement is a Stage 3 criterion.
- **Context resolution.** A process that survived an earlier server lifetime with a stale Herdr id in its environment resolves no thread from that id.
- **Close under restart.** Crash `kkd`, and separately restart the Herdr server, at every `CloseCommit` step.
  - Before the final proof the thread resumes or fails loudly.
  - After it, recovery re-verifies exit by recorded identity and completes.
  - No path deletes a workspace on the strength of a restored layout or a missing pane.
- **Checkpoint evolution, part two.** Close a thread, then rewrite one of its ancestors from another workspace.
  - The closed thread's bookmark follows to a same-change successor.
  - Kiki advances the expected target and the archived head together and raises no issue.
  - `kk reopen` recreates the workspace at that commit.
  - A different-change move on a closed thread raises `BookmarkMoved`.
- **Bookmark repair.** Each bookmark plan does what [Commands](09-commands.md) says, and no more.
  - [`restore-bookmark`](appendix-a-glossary.md#restore-bookmark) puts the bookmark back on the expected target, with no approval in the thread's own context. It is not offered while the expected target is hidden.
  - [`adopt-bookmark`](appendix-a-glossary.md#adopt-bookmark) and [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target) place the bookmark on the live head or on a commit on the owned chain, after a one-shot approval. That includes a commit behind the expected target. Both refuse a commit off the owned chain.
  - After `jj edit` of an earlier commit the relationship reads `ahead`. `kk close` refuses until `choose-bookmark-target` is applied.
  - [`unhide-checkpoint`](appendix-a-glossary.md#unhide-checkpoint) makes an abandoned expected target visible again. A closed thread with an abandoned checkpoint appears on `kk ls --all` and `kk repair`, raises no loud attention event, and blocks only `kk reopen`.
  - An ordinary checkpoint never passes `--allow-backwards`. Only those four plans may.
- **Rewritten operation history.** Run `jj op abandon` on an operation in the middle of the log, then move one thread's bookmark by hand.
  - Kiki raises one repo-level [`OperationHistoryRewritten`](appendix-a-glossary.md#operationhistoryrewritten) issue and no per-thread bookmark issue for the gap.
  - `kk repair --repo` shows the [`reanchor-history`](appendix-a-glossary.md#reanchor-history) plan with every affected thread and its observed bookmark state.
  - After a one-shot approval with repo scope, each thread whose bookmark is on its live head or owned chain gets a fresh placement. Every other listed thread gets its ordinary per-thread issue.
- **Workspace repair.** Delete a thread's workspace directory, forget its jj workspace record, and move its directory, each in turn. Kiki raises `WorkspaceDirectoryMissing`, `WorkspaceRecordMissing`, and `WorkspacePathMismatch`. The plans [`recreate-workspace`](appendix-a-glossary.md#recreate-workspace), [`reattach-workspace`](appendix-a-glossary.md#reattach-workspace), and [`repoint-workspace`](appendix-a-glossary.md#repoint-workspace) clear them.
- **Failed lifecycle states.** A `CloseFailed` thread is finished by [`retry-close`](appendix-a-glossary.md#retry-close). A `CreateFailed` thread and a failed reopen are cleaned up by `cleanup-failed-create` and `cleanup-failed-reopen`.
- **Thread identity.** A thread keeps the same `thread_id` through close, reopen, a terminal restart, and adoption of an external bookmark rename.
- **Unregister.** Both modes refuse live or unfinished work. A matching approval fences the registration and drains existing work before removal. A successful delete removes the old state directory. A successful keep preserves it. Both invalidate old credentials, preserve source history, and allow a fresh registration with a new UUID only after completion.
- **Attention notifications.** Each of these fires exactly one notification at its configured level: a blocked agent, a crashed agent, a failed lifecycle operation, and a projection issue. Setting an event's key to `silent` stops the notification and leaves the status mark.
- **Command notifications.** With `[notifications] command` set in the user config file and no desktop session, `os_provider = "auto"` resolves to `command`. `kkd` runs the program once per `loud` event, with the event as JSON on its standard input. A slow or failing program is stopped at the timeout and is not retried. With no `command` set on such a host, `auto` resolves to `off`.
- **`kk wait`.** `kk wait --for <state>` exits 0 when the thread reaches `quiescent`, `blocked`, `closed`, or `issue`, and exits 6 when `--timeout` runs out first. The `conflicted` and `goal-complete` states are checked in Stage 3, with the cascade and the goal report that produce them.
- **Headless lifecycle.** With zero attached Herdr clients, and under an automation credential and an activated policy, `kk close`, `kk reopen`, and the `restart-agent` repair each run to their end state. Every safety proof still runs. The script is not the thread, so the `restart-agent` repair needs a rule that allows `thread-op`.
  - A close whose plan carries `live-processes` or `work-loss` runs only under a rule that accepts those labels. Otherwise it is refused with exit code 3 and nothing is frozen.
  - With proven `attention_events`, a harness permission prompt raises `agent_blocked` in `kk events`. Without that proof, check that a crash reports the blocked state. Kiki does not answer the prompt.

### Stage 3: follows and cascade

Promote the cascade proof of concept into the daemon: the rest of `OpLogWatcher`, `OpAttribution`, and `AncestryQuery`; `CascadeOrchestrator`; [`WorkspaceProbe`](appendix-a-glossary.md#workspaceprobe); [`WorkspaceRecovery`](appendix-a-glossary.md#workspacerecovery); the cascade half of `kk-hook`; and then `kk thread detach`, `kk log`, `kk status`, `kk config get|show`, and the audit reads.

Stage 3 gate:

- every numbered proof in the proof of concept, now through the daemon and with the harness running under the pane launcher in a terminal group;
- **Hook budget.** Stop `kkd` and verify the tool is denied at `hook_connect`, with and without a marker. Hold reconciliation past `slow_path` and verify each sibling gets a blocking denial.
- **Admission cache.** Restart `kkd` while a `PassThrough` batch is in flight. The next pre-tool call from that incarnation is treated as an unknown in-flight batch, unless its payload proves it is the first call of a new model turn. `kkd` blocks it, hard-pauses the incarnation with files untouched, and starts a replacement.
- **Unknown batch after a freeze.** Start a close while a tool batch is in flight, and force a verified resume. Kiki hard-restarts the incarnation to a clean boundary with files untouched.
- **Cascade replacement.** Kill a harness while its tool child keeps running, with an intent pending. The cascade's replacement refuses to open a gate until the launcher's process tree is empty, and reports the remnant as `OrphanedProcess`.
- **Hard pause recovery.** Kill `kkd` in the middle of a hard pause, at each `pause_state`. Recovery rolls the pause forward to the kill. It never resumes the harness that was being retired.
- **Close a parent that has children.** Close a thread that two threads follow, one with an idle agent and one with a working agent.
  - Each child is reconciled or detached inside the close, in the journaled child steps.
  - Parent thread lock, then child thread lock, then the repo jj lock is the only lock order taken.
  - A crash at any child step resumes the same plan.
  - Without `--discard-pending`, no pending parent work is thrown away.
- **Reconciliation with no agent.** A thread whose harness has exited, and whose remnant check has passed, is reconciled at once. It does not wait for a hook that will never come.
- **`RestartStartup`.** For each harness, a replacement incarnation receives the saved payload as its first input, its session-start hook reports the startup delivery id, and its first pre-tool call acknowledges the intent.
- **Conflict notification.** A cascade whose result contains jj conflicts fires exactly one attention notification, and the thread's cascade state reads `conflicted`.
- **Exhausted delivery and abandoned parent.** An intent whose delivery attempts are exhausted fires exactly one attention notification. So does abandoning a followed parent's live head or owned revisions; the child then shows topology divergence.
- **Goal complete.** An agent that reports its goal complete gets the `finished` status mark at `soft`, and no OS notification. `kk wait --for goal-complete` then exits 0, and `kk wait --for conflicted` exits 0 for a conflicted cascade.
- **Detach.** `kk thread detach` with no argument detaches the contextual thread from its parent. The child keeps its commits and stops receiving cascades. The parent's later commits raise no intent for it.
- **`kk log` and `kk status`.** For a three-thread stack, `kk log` prints the stack with the current thread expanded. `kk status` prints the live head, the bookmark, the checkpoint relationship, and the cascade state. Both stay readable with `NO_COLOR=1`, and both print the same facts under `--json`.
- **Configuration reads.** `kk config get <key>` prints the effective value and the layer it came from. `kk config show` prints the merged configuration with the layer each value came from.
- **Audit reads.** `kk thread audit` lists the contextual thread's own rows. `kk audit log` runs only after a one-shot approval, and every accepted and rejected call made during the gate appears exactly once.
- **jj concurrency.** Produce two operation heads from concurrent commands.
  - The watcher records both, classifies each head's view without merging them, and blocks checkpoint-dependent lifecycle steps while the views disagree.
  - Kiki's own mutations name one exact head. When another operation lands at the same moment and leaves two heads, the journal that made the mutation owns the integration and raises no issue.
  - When a lifecycle step needs a single view, kiki integrates deliberately and attributes that operation.
  - A run of `kk ls`, `kk status --no-jj`, and watcher polling during the divergence creates no operation.
- **Dirty stale update.** `jj workspace update-stale` over unsnapshotted edits exits successfully while the edits live only in a divergent successor. Kiki never treats that success as preservation:
  - recovery enumerates successors at exact operations, and a headless caller selects a verified result through the Stage 3 `choose-recovery-successor` repair,
  - verifies where the edits are, and
  - does not resume on the tree that hides them.
- **Terminal signals are not boundaries.** The agent's screen is idle, Herdr reports the agent idle, and text is queued in the pane. Even so, no reconciliation runs and no intent is acknowledged until the harness boundary proofs in [Cascade](05-cascade.md) hold.
- **Cascade across a terminal restart.** Restart the Herdr server with an intent `Materialized` or `Delivered` but unacknowledged. The old incarnation is retired without acknowledgement. The restarted incarnation receives the saved payload through `RestartStartup` before any tool runs.

## Foundation order

Within the stages, build modules in this order. Each item names the stage that delivers it.

1. **Stage 1.** Minimal `ConfigLoader`; `kk daemon install`; `kkd` under the user's service manager, with the Herdr server as its own service-manager unit, and `kkd --foreground` with a detached server where no service manager exists; [`TerminalRuntime`](appendix-a-glossary.md#terminalruntime) with its Herdr adapter and fake, the pane launcher, server-instance tracking, and `TerminalClient::attach`.
2. **Stage 1.** `AuthEnforcer`, the enrolled foreground presenter, the two-phase one-shot approval broker, and scoped/unscoped [SQLite](https://www.sqlite.org/) audit interception. Then the automation policy engine with risk labels, `PolicyApproval`, automation credentials, and `kk automation`. The end-to-end tests of every later item use an automation credential.
3. **Stage 1.** `ProcessSupervisor` inventory with its OS adapter and fake, and the [orphan scan](appendix-a-glossary.md#orphan-scan); `ThreadLifecycleSaga` for creation; the database-backed harness gate; both adapters' `launch_spec` and exclusive-hook proof; `kk-hook` with the session-start ready report and a pass-through pre-tool hook.
4. **Stage 1.** The watcher subset: `OpFrontierSampler`, the op-DAG cache, classifier rules 0–6, attribution of kiki's own operations (`OpAttribution`), the ancestry query for the owned chain (`AncestryQuery`), detection of rewritten operation history with silent re-anchoring, and restart catch-up for bookmarks and rewrites; bookmark checkpointing with successor tracking; and the audit that raises `TerminalMissing` and the bookmark issues.
5. **Stage 1.** The exit codes, `--json` output, `StreamRepoEvents`, and `kk events`.
6. **Stage 2.** The rest of `ProcessSupervisor` (freeze, resume, and termination), then freeze/recheck close, and reopen.
7. **Stage 2.** `ProjectionReconciler`, the rest of the projection audit, stable repair plans, `kk repair`, `kk repo unregister`, attention notifications with the `command` provider, and `kk wait`.
8. **Stage 2.** `TerminalClient` caller resolution and `kk switch`.
9. **Stage 3.** The rest of `OpLogWatcher`, `OpAttribution`, and `AncestryQuery`: follows classification, and restart catch-up for follows and cascade intents.
10. **Stage 3.** `CascadeOrchestrator` base-transition classification; `WorkspaceProbe`/`WorkspaceRecovery`; the intent-owned batch barrier and delivery; native materialization; and explicit advance, integrated with the cascade half of `kk-hook` and `PostToolBatch`.
11. **Stage 3.** `kk config get|show`, `LogRenderer`, `StatusRenderer`, `kk log`, `kk status`, `kk thread detach`, and the audit-read commands.

[v1.x polish](appendix-a-glossary.md#v1-x-polish) (enumerated in [Orientation](01-orientation.md)) builds on top of that, in this order:

1. Stack-aware `kk publish`, lazy GitHub validation, and editor integration.
2. Transcript capture, human reads, durable provider-consent management, consented [reopen catch-up](appendix-a-glossary.md#catch-up), and then consent-gated same-thread [MCP](https://modelcontextprotocol.io/).
3. Metadata ownership, plus [auto-describe](appendix-a-glossary.md#auto-describe)/[auto-rename](appendix-a-glossary.md#auto-rename) and the full configuration mutation surface.
4. The `shell` and `ui` [role panes](appendix-a-glossary.md#role-pane), [Herdr sidebar](appendix-a-glossary.md#herdr-sidebar-projection) tokens, the [overlay TUI](appendix-a-glossary.md#overlay-tui), GitHub polling and comments, and auto-archive.

## Upstream dependencies

One thing must exist in [Herdr](appendix-a-glossary.md#herdr) before the [acceptance gate](appendix-a-glossary.md#acceptance-gate) can pass. It blocks no stage.

- **[Client-targeted focus](appendix-a-glossary.md#client-targeted-focus)**, as specified in [Terminal runtime](13-architecture/terminal-runtime.md#caller-local-focus). Propose it upstream at the start of Stage 1. If it has not landed by the Stage 2 exit, there is a choice between carrying a patch and changing the `kk switch` contract. That choice is made at the Stage 2 exit. It is a new decision record, not an implementation detail.

  If the Stage 2 criterion "provisioning moves no one" fails, a second upstream extension becomes required. That too is a new decision record.

  The optional extensions each replace adapter work that is already safe without them. They are:
  - a state-root option that is not exported to panes,
  - request keys,
  - a public boot id,
  - a [mutation fence](appendix-a-glossary.md#mutation-fence),
  - a termination receipt, and
  - an event cursor.

  Request one only when a stage shows the adapter path is too slow or too fragile.

## Acceptance integration gate

[Orientation](01-orientation.md#v1-contract) is the sole enumeration of the [acceptance slice](appendix-a-glossary.md#acceptance-slice). The integration gate exercises every item in that ledger together, against:

- a real jj repo,
- a real [dedicated Herdr server](appendix-a-glossary.md#dedicated-herdr-server) at the pinned candidate build, and
- each shipped harness: Claude Code and Codex, on each supported platform.

The gate runs on the build that carries the client-targeted focus extension. It re-runs every stage gate above on that build, because results from an earlier build are not evidence for it.

The gate runs unattended. It presents an automation credential and relies on an activated policy. It attaches a Herdr client, or uses a foreground presenter, only for the criteria that are about a client or a human.

Each ledger item has one observable criterion in a stage gate. The ones that are easy to miss are:

| Ledger item              | Stage gate criterion                                                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| approvals                | Stage 1, "Approvals"                                                                                                                 |
| automation policy        | Stage 1, "Automation policy"                                                                                                         |
| headless operation       | Stage 1, "Headless first run", "No UI", and "No prompt without a terminal"; Stage 2, "Headless lifecycle"                            |
| exit codes and `--json`  | Stage 1, "Scripting surface"                                                                                                         |
| `kk events`              | Stage 1, "Scripting surface"                                                                                                         |
| `kk wait`                | Stage 2, "`kk wait`"; Stage 3, "Goal complete"                                                                                       |
| `command` notifications  | Stage 2, "Command notifications"                                                                                                     |
| `kk repo unregister`     | Stage 2, "Unregister"                                                                                                                |
| attention notifications  | Stage 2, "Attention notifications"; Stage 3, "Conflict notification", "Exhausted delivery and abandoned parent", and "Goal complete" |
| `kk thread detach`       | Stage 3, "Detach"                                                                                                                    |
| `kk log` and `kk status` | Stage 3, "`kk log` and `kk status`"                                                                                                  |
| `kk config get\|show`    | Stage 3, "Configuration reads"                                                                                                       |
| audit reads              | Stage 3, "Audit reads"                                                                                                               |

A conflicted cascade's notification is checked in Stage 3 ("Conflict notification"), with the cascade that raises it.

This chapter defines build order, not a second scope list. Passing the gate requires neither [`gh`](https://cli.github.com/) nor network access beyond the configured harness. V1.x work deepens the accepted coordinator; it cannot substitute for a missing ledger item.

## Budget

The expected v1 build budget is:

- acceptance slice: 8-11 weeks, plus up to 1 week for the second harness adapter's launch-isolation and boundary proofs.
  - Three to four of those weeks are the terminal runtime adapter, the pane launcher, and `ProcessSupervisor`, which the earlier tmux-based estimate did not carry.
  - The estimate excludes waiting for upstream Herdr changes.
  - The protocol, sidecar, and orchestrator are shared. The Codex-specific work is the generated `CODEX_HOME`, the version fixtures, and the gate.
  - That extra week is not work left for the end. Stage 1 needs both adapters. So the Codex launch-isolation part of the week (the two entry-gate proofs of step 2a: launch isolation, which covers the generated `CODEX_HOME`, `launch_spec`, and the exclusive-hook proof, and the session-start hook) is spent before Stage 1 starts. The Codex boundary proofs (serial dispatch, the delivery receipt, and `RestartStartup`) take the rest of it, in parallel with Stages 1 and 2;
- first v1.x workflow tranche (publish and transcript): 3-5 additional weeks;
- edge-case buffer: 1-2 weeks.

The buffer belongs to these cases:

- terminal reconciliation and process-supervision cases,
- core op-log classification and restart catch-up cases,
- exclusive hook-settings compatibility,
- parallel-batch barriers,
- lifecycle compensation,
- projection repair,
- jj op-id dedupe, and
- cascade retry paths.

Additional harness and version diagnostics, and non-core op-log compatibility cases, remain in their v1.x tranche. Transcript and UI-pane edge cases likewise do not consume the acceptance buffer.
