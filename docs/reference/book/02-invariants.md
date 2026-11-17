# Invariants

An invariant is a promise that always holds. These are the promises v1 relies on. They cut across the whole book. Each chapter's local details should be read in light of them.

## Identity is stable

Every [thread](appendix-a-glossary.md#thread) has one stable ID: `thread_id`. A thread is kiki's unit of work. It is a themed sequence of revisions in [jj](https://docs.jj-vcs.dev/latest/), the version-control tool kiki drives.

A thread's [live head](appendix-a-glossary.md#live-head) is the current `@` of its managed [workspace](appendix-a-glossary.md#workspace). In jj, `@` names the [working-copy commit](https://docs.jj-vcs.dev/latest/glossary/): the change being edited right now. kiki saves that head as `thread_head_commit_id`.

Everything else is a [projection](appendix-a-glossary.md#projection): an outward reflection of the thread, not the thread itself. [Bookmark](appendix-a-glossary.md#bookmark) names, workspace paths, [terminal groups](appendix-a-glossary.md#terminal-group), and [harness](appendix-a-glossary.md#harness) sessions are all projections. Projections may change. The `thread_id` must not.

This identity is state that other things depend on. Credentials, audit rows, [transcript](appendix-a-glossary.md#thread-transcript) rows, [PR](https://docs.github.com/en/pull-requests) links, lifecycle state, and [follows](appendix-a-glossary.md#follows) links all join through it.

Code should treat a jj bookmark like a bookmark left in a book. It marks a checkpoint or a publication point, not the page you are actually on. A bookmark is not identity. It is also not the live source of truth for a running thread.

## External projections fail loud

[Projections](appendix-a-glossary.md#projection) can change, so kiki observes them instead of assuming it still owns them. kiki must classify each of these cases explicitly:

- a missing, conflicted, or externally moved [bookmark](appendix-a-glossary.md#bookmark), or a checkpoint whose commit was abandoned;
- a missing jj [workspace](appendix-a-glossary.md#workspace) record;
- a mismatched workspace path;
- a missing [terminal group](appendix-a-glossary.md#terminal-group);
- a surviving [orphaned](appendix-a-glossary.md#orphan) process.

kiki may repair a projection automatically only when it can prove what the correct result is. Otherwise the thread enters `ProjectionDiverged`. It then waits for `kk repair` or another explicit human choice. See [projection divergence](appendix-a-glossary.md#projection-divergence).

A broken projection does not erase the abilities kiki can still prove:

- **Only the bookmark is bad.** Checkpoint, publish, close, and detach are blocked. Unambiguous workspace-head tracking and follows classification keep working. On a closed thread, an abandoned checkpoint blocks only `kk reopen`.
- **The terminal group or its `agent` role is missing, or a recorded process or a harness remnant survives where none should.** kiki can still observe the head. A missing terminal group or `agent` role blocks boundary mutation. A surviving recorded process or harness remnant ([`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess)) blocks exactly three things: replacement, materialization, and deletion.
- **The workspace's identity or path is ambiguous.** Only this case suspends both head observation and boundary mutation.

An in-flight [lifecycle journal](appendix-a-glossary.md#lifecycle-journal) may own a temporary projection change. If so, that change fails or resumes the journal. It does not create a competing [state machine](https://en.wikipedia.org/wiki/Finite-state_machine).

## Lifecycle work is recoverable

Creating, closing, reopening, repairing, and destroying a thread each touch five systems: [SQLite](https://www.sqlite.org/), jj, the filesystem, the terminal runtime, and a [harness](appendix-a-glossary.md#harness) process. No single [transaction](https://en.wikipedia.org/wiki/Database_transaction) can cover all five.

These operations are therefore durable [sagas](appendix-a-glossary.md#saga). A saga is a multi-step job that records its progress as it goes. It is not an atomic transaction across systems.

- If a step crashes, or a [compensating](appendix-a-glossary.md#compensation) cleanup step fails, kiki must leave behind a persisted journal and a lifecycle state that reflects the completed steps.
- Restart recovery or an explicit command can then continue from that record.
- A reopened thread stays `Closed` until the replacement [incarnation's](appendix-a-glossary.md#incarnation) [ready handshake](appendix-a-glossary.md#ready-handshake) commits.
- No recovery path may leave a thread that looks `Active` after its managed agent and [terminal group](appendix-a-glossary.md#terminal-group) were already destroyed.

### Locks and their order

Kiki uses two kinds of lock. Both live in `kkd`'s memory. Crash recovery comes from the journals, never from a lock.

- **The lifecycle lock.** Each thread has one [reconciliation lock](appendix-a-glossary.md#reconciliation-lock). It makes cascade reconciliation for that thread run one step at a time. The [lifecycle lock](appendix-a-glossary.md#lifecycle-lock) is that same lock, held for the whole length of a lifecycle operation such as close, detach, reopen, or a repair. It is not a second lock. So a lifecycle operation and a reconciliation of the same thread can never run at the same moment.
- **The repo jj lock.** Each repo has one [repo jj lock](appendix-a-glossary.md#repo-jj-lock). `kkd` holds it around every unpinned working-copy command it runs and around every integration of operation heads. It is held from the frontier sample that the step depends on until the re-sample. For a working-copy command that sample shows a single head. A deliberate integration starts from a sample with several heads. It is short and innermost. It is never held across a wait: not for a human, not for an agent, and not for a hook.

Locks are always taken in one order:

1. the parent thread's lock;
2. the child thread's lock;
3. the repo jj lock.

A step that needs only some of these takes them in the same order and skips the rest. One fixed order means two operations can never each hold a lock the other is waiting for.

## The terminal runtime is a projection, not an authority

Kiki hosts each thread's terminals in a [terminal group](appendix-a-glossary.md#terminal-group) on a [dedicated Herdr server](appendix-a-glossary.md#dedicated-herdr-server) (see [Terminal runtime](13-architecture/terminal-runtime.md)). [Herdr](https://github.com/herdrdev/herdr) is a [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer): a program that runs and arranges many terminals. Herdr is the terminal's owner and never the thread's. Five consequences hold everywhere.

**Identities stay separate.**

- These are distinct recorded facts: `thread_id`, the [server instance](appendix-a-glossary.md#server-instance), the [terminal binding](appendix-a-glossary.md#terminal-binding), Herdr's workspace, tab, and pane ids, a pane's role, an OS [process identity](https://en.wikipedia.org/wiki/Process_identifier), and a harness [incarnation](appendix-a-glossary.md#runtime-agent-incarnation).
- A Herdr id is a locator valid only within one server instance.
- Restored or recurring ids, labels, working directories, [metadata tokens](appendix-a-glossary.md#sidebar-token), and pane placement never bind a thread. They never authorize a mutation. They never prove that files are safe to delete.

**A runtime reply is not an outcome.**

- A successful create, layout, input, focus, or close reply proves that Herdr accepted a request. It proves nothing more.
- Readiness is proved only by the [launch gate](appendix-a-glossary.md#launch-gate) and [ready handshake](appendix-a-glossary.md#ready-handshake).
- Delivery is proved only by the cascade protocol.
- Process exit is proved only by [`ProcessSupervisor`](appendix-a-glossary.md#processsupervisor) against OS process identities.
- Screen idleness, Herdr's agent detection, `agent.wait`, queued terminal input, and asynchronous plugin hooks prove none of these.

**Restore is reconciliation.**

- A restored layout is a set of empty containers. Kiki never adopts or reuses one. See [cold restore](appendix-a-glossary.md#cold-restore).
- Kiki, not the runtime, issues each incarnation's credential, launch settings, gate, and handshake.
- Automatic agent resume by the runtime is disabled.
- Kiki distinguishes client reconnect, pane exit, cold restore, and live handoff. None of them can make a thread `Active`.

**Absence from the terminal is not absence from the machine.**

- A process can outlive its pane, its terminal group, and the terminal server. This is true under any terminal host.
- Kiki scans for surviving recorded processes and harness remnants before it starts a replacement agent.
- Kiki scans for every [holder](appendix-a-glossary.md#holder) of the workspace before it deletes one. A holder is a process that still has the workspace open.
- Kiki ends processes itself, by verified identity, before it asks the terminal to close anything. It rechecks the files afterwards.
- An unknown writer, an unstable process set, or drift after the [final proof](appendix-a-glossary.md#final-proof) preserves the files.

**Navigation is caller-local.**

- `kk switch` moves the invoking viewer's terminal and no other. See [caller-local focus](appendix-a-glossary.md#caller-local-focus).
- Kiki never substitutes a focus change that moves every attached client unless the user asked for exactly that by name.

Herdr's events are bounded, and its metadata is mutable and short-lived. After any gap, kiki takes an authoritative snapshot, reconciles, and republishes. Kiki's journals and jj's [operation history](https://docs.jj-vcs.dev/latest/operation-log/) remain the durable record.

## Workspaces are cooperative isolation

Each [thread](appendix-a-glossary.md#thread) gets its own [workspace](appendix-a-glossary.md#workspace) so threads do not trample each other's files during normal use. That isolation is cooperative, not security. It should not be documented, tested, or presented as filesystem security.

Any process running as the same user can read sibling workspaces, `~/.config/kiki`, and shared jj repository state. v1 accepts that fact.

Credential scoping exists to shrink the damage an accident can do. It does not exist to defeat an adversary who already has the user's privileges.

## Cascade materializes only at safe boundaries

A cascade is how a change in a parent thread reaches the child threads that [follow](appendix-a-glossary.md#follows) it. See [cascade reconciliation](appendix-a-glossary.md#cascade-reconciliation). To [materialize](appendix-a-glossary.md#materialization) means to update a workspace's files on disk to match the commit jj already recorded for it.

### When jj has already rewritten the child

When a parent commit is rewritten, jj may immediately evolve the descendant commits in repository state on its own. kiki must not redundantly rebase history that jj already evolved. ([Rebase](https://git-scm.com/docs/git-rebase) means moving commits onto a new base.)

Instead, kiki does two things:

1. It records the exact transition, from the [last synchronized base](appendix-a-glossary.md#synchronized-base) to the evolved base.
2. It materializes the child's current jj state only at a [safe boundary](appendix-a-glossary.md#safe-boundary). There are three: an agent boundary, [agent quiescence](appendix-a-glossary.md#agent-quiescence), or a moment when the thread has no live [incarnation](appendix-a-glossary.md#incarnation) and the check for leftover harness processes has passed.

Agent quiescence is a moment when the [harness](appendix-a-glossary.md#harness) adapter proves the agent is idle. This is distinct from the [process quiescence proof](appendix-a-glossary.md#process-quiescence-proof) that close uses.

kiki does not pin the child's working-copy commit as the target. That commit may legitimately evolve again before the boundary.

### When the parent's head advances

The other case is a head advance. Suppose a parent's saved [live head](appendix-a-glossary.md#live-head) advances by adding a new revision, and that exact new head is not already an ancestor of the child. kiki then performs an explicit rebase of the child's [owned stack](appendix-a-glossary.md#owned-stack) at the same kind of [safe boundary](appendix-a-glossary.md#safe-boundary).

In v1, an owned stack must be a provable single-parent chain from the synchronized base to the child's live head. If the topology (the shape of the commit graph) is ambiguous, merged, or foreign, kiki stops and marks the thread [`TopologyDiverged`](appendix-a-glossary.md#topologydiverged).

Waiting is acceptable. Either reconciliation kind may wait for a safe boundary. Either may also wait for [`kkd`](appendix-a-glossary.md#kkd), the kiki [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>), to become reachable.

Two things are not acceptable:

- kiki must not materialize or explicitly rebase the managed workspace while its agent is mid-edit.
- kiki must not silently drop pending reconciliation.

### What the guarantee covers

This guarantee covers kiki-controlled mutations for the managed agent, and only those. A human may run `jj` directly in a [stale](https://docs.jj-vcs.dev/latest/working-copy/) child workspace and explicitly update it before kiki's boundary.

Depending on the repository, that command may or may not record a new operation in the op-log (jj's [operation log](https://docs.jj-vcs.dev/latest/operation-log/)). Its success also does not prove that edits were preserved. So kiki probes the workspace again at the next boundary instead of relying on watcher events alone.

kiki is an [ambient coordinator](appendix-a-glossary.md#ambient-coordinator). It does not pretend direct human commands are gated.

### Unsnapshotted edits must not vanish

Unsnapshotted edits are file changes jj has not yet recorded. kiki must not make them disappear from the visible working tree.

Immediately before reconciliation, kiki proves the stale workspace is clean. If it cannot, it [hard-pauses](appendix-a-glossary.md#hard-pause) and enters explicit recovery. Recovery follows these rules:

- It runs outside the source workspace.
- It preserves and lists [divergent](https://docs.jj-vcs.dev/latest/glossary/) successors.
- It verifies where the edits landed.
- It resumes only after selecting a result that retains the edits, or after obtaining human direction.

See [`WorkspaceRecovery`](appendix-a-glossary.md#workspacerecovery).

### Delivery at the pre-tool boundary

Delivery rides on the harness's pre-tool boundary. That is the [hook](appendix-a-glossary.md#pretooluse) that fires before an agent's tool call runs.

For every v1 adapter, [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) and [Codex](https://github.com/openai/codex) alike, kiki exclusively owns that boundary in the managed session. It re-proves that exclusive ownership for every process incarnation. It must not race user-defined pre-tool handlers.

A batch is the set of tool calls the harness dispatches together. See [tool batch](appendix-a-glossary.md#tool-batch). The rules for a batch are:

- If one tool in a dispatched batch triggers reconciliation, kiki durably binds `Block` and the complete batch identity before it changes the workspace.
- Before it binds the `Block`, `kkd` writes a durable [barrier marker](appendix-a-glossary.md#barrier-marker) file for the thread. While that file exists, a hook that cannot reach `kkd` blocks the tool call instead of letting it through. `kkd` removes the file when the barrier lifts.
- Every tool call in that batch is blocked.
- Batch completion establishes soft-delivery proof: evidence that the payload reached the harness. See [`SoftBatch` delivery proof](appendix-a-glossary.md#softbatch-delivery-proof).
- Only a later [model turn](appendix-a-glossary.md#model-turn) may acknowledge the payload.
- Another concurrent `PreToolUse` event from the same batch is never acknowledgement evidence.

### Batches differ by harness

What counts as a batch, and how its completion is proved, is an adapter/version proof.

- **Claude Code** dispatches tools in parallel. Its batch closes with an explicit completion signal.
- **Codex** dispatches tools serially, one at a time. That serial behavior is itself proven, so each Codex batch is a single tool call.

A denied Codex call never runs and fires no post-tool event. The crash-surviving completion report is therefore the next turn-scoped hook event to arrive. The serial proof shows that this event cannot come before the blocked call's resolution.

Codex acknowledgement requires one thing more. The harness session record must contain a byte-identical [delivery receipt](appendix-a-glossary.md#delivery-receipt). The reason is that hook-side write evidence cannot prove the model received the payload rather than a substituted result.

If a safe batch boundary cannot be proved, a replacement process receives the saved payload as its first startup message. It must prove it processed that message before acknowledgement. See [`RestartStartup` delivery proof](appendix-a-glossary.md#restartstartup-delivery-proof).

## Cascade delivery is crash-safe

[Cascade](appendix-a-glossary.md#cascade-reconciliation) delivery must be [idempotent](https://en.wikipedia.org/wiki/Idempotence) and crash-safe. Idempotent means running it twice has the same effect as running it once.

The system should prefer a rare duplicate delivery over silently dropping a cascade. When optional [transcript](appendix-a-glossary.md#thread-transcript) projection ships, it must remain idempotent too.

The implementation therefore stores four things on one durable [`sync_intent`](appendix-a-glossary.md#sync-intent): reconciliation state, the byte-stable delivery payload, acknowledgement, and recovery state. It may derive UI state from those rows. It must not maintain a second progress protocol that can disagree with them.

## Operation history is a DAG

jj records every repository operation in a log, the [operation log](https://docs.jj-vcs.dev/latest/operation-log/). That history is a DAG: a [directed acyclic graph](https://en.wikipedia.org/wiki/Directed_acyclic_graph), not a straight line. An operation may have multiple parents, and heads may temporarily diverge. A head is an operation with nothing after it yet.

### Kiki reads without changing

Kiki observes that history without changing it. This takes care, for two reasons:

- Most jj commands that look read-only [snapshot](https://docs.jj-vcs.dev/latest/working-copy/) the working copy. A snapshot records the current files into the working-copy commit.
- Any command that loads the repository without naming an operation merges [divergent heads](https://docs.jj-vcs.dev/latest/technical/concurrency/) as a side effect.

So kiki follows two rules:

- Every kiki read names one exact operation id and ignores the working copy. See [pinned read](appendix-a-glossary.md#pinned-read).
- Every bookmark, rebase, or other repository mutation names the exact head it builds on.

### The commands that are not pinned

A closed list of commands is not pinned that way:

- **The [boundary snapshot](appendix-a-glossary.md#boundary-snapshot) and `jj workspace update-stale` in a managed workspace.** Both act on a working copy. The boundary snapshot is a kiki-run snapshot of a managed workspace. Kiki takes it at [agent quiescence](appendix-a-glossary.md#agent-quiescence) or a held harness boundary. For a harness that cannot prove quiescence, kiki may also take it at a lifecycle preflight, after warning the human that the agent may be working. The same warned rule covers a child's snapshot during a parent's close. Its purpose is that a pinned head contains every tracked edit before a checkpoint that precedes deletion or publication.
- **[Deliberate integration](appendix-a-glossary.md#deliberate-integration) of divergent operation heads.** This is what kiki does when a step needs one view and there are several.
- **The human-invoked passthroughs.** These are the body of `kk status`, and the overlay's diff preview for the caller's own thread. The `kk` CLI runs these in the caller's own workspace as an explicit human request, exactly as if the human had typed the jj command.

The first two entries are the commands `kkd` runs. They run under strict conditions:

- The working-copy commands run only under the thread's lock: the reconciliation lock, or the same lock held as the lifecycle lock. See [Locks and their order](#locks-and-their-order).
- The working-copy commands and integration both run under the [repo jj lock](appendix-a-glossary.md#repo-jj-lock). It is taken last and held only from the frontier sample to the fresh sample.
- The working-copy commands run only after a frontier sample shows a single head. (The [operation frontier](appendix-a-glossary.md#operation-frontier) is the current set of operation heads.)
- The working-copy commands are followed by a fresh sample.
- Integration also runs under the thread lock of the step that needs the single view.
- Kiki attributes every operation any of these commands writes. One command can write more than one.

The passthroughs are direct human jj use that happens to be spelled `kk`. `kkd` never runs them, so they take none of `kkd`'s locks. Kiki treats the operations they write like any other human jj command. No background renderer, watcher, or polling path runs them either.

### Everything else is pinned

Everything else is pinned, including the workspace-shaping commands:

- `jj workspace add` names the exact head it builds on. It is the one pinned command that must not ignore the working copy, because its job is to write a new one.
- `jj workspace forget`, bookmark placement, rebase, abandon, and push name an exact head and ignore the working copy.

A pinned mutation does not snapshot the human's own working copy. It can still leave two operation heads when another operation lands at the same moment. That is one more reason kiki treats several heads as normal.

### Working with several heads

With several heads, kiki evaluates each head's view, or it integrates them deliberately and attributes that operation. It never lets a status query do it by accident.

Listing the complete set of heads without side effects has no supported jj interface yet. So the [frontier sampler](appendix-a-glossary.md#frontier-sampler) is a versioned adapter and a standing proof requirement.

Restart catch-up therefore stores normalized parent edges. It traverses every unprocessed ancestor reachable from the observed frontier, in [topological order](https://en.wikipedia.org/wiki/Topological_sorting) (parents before children).

A singular parent column is not an acceptable approximation. Neither is a "last cursor to head" scan. Either one can silently skip a workspace transition.

## Human prose is owned by humans

Revision descriptions, [bookmark](appendix-a-glossary.md#bookmark) names, and [PR](https://docs.github.com/en/pull-requests) descriptions that a human wrote must not be silently overwritten.

kiki may draft. kiki may refresh when explicitly asked. It must preserve deliberate user prose unless the user opts back into regeneration.

## Transcript storage and egress are explicit

kiki stores [thread transcripts](appendix-a-glossary.md#thread-transcript) locally. Transcripts must not feed externally visible artifacts such as PR descriptions, [auto-describe](appendix-a-glossary.md#auto-describe) output, or auto-renames. See the [no-publication rule](appendix-a-glossary.md#no-publication-rule).

Some flows do send data out. Egress means data leaving the machine. Two flows may leave the machine for the configured provider:

- a catch-up sent to a hosted [harness](appendix-a-glossary.md#harness);
- a transcript-derived [MCP](https://modelcontextprotocol.io/) result returned to a hosted model.

Before that happens, kiki must disclose the boundary and obtain a grant. The grant is remembered, revocable, and bound to the thread, the provider, and the purpose.

This is a confidentiality rule. Treat it accordingly.

## Authority is explicit

Some daemon actions are high-stakes: destructive actions, cross-thread actions, sensitive reads, and externally visible actions. Each one requires a one-shot [human approval](appendix-a-glossary.md#human-approval). That approval:

- is bound to the method, target, arguments, and rendered plan;
- is issued through a persisted begin/display/confirm exchange with an enrolled interactive [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter).

A reusable [Admin credential](appendix-a-glossary.md#bootstrap-admin-credential) must not be loaded automatically by every `kk` subprocess. It cannot replace confirmation for an operational call.

[Thread-scoped credentials](appendix-a-glossary.md#threadscoped-credential) may operate on their own thread. They may also read the narrow same-repo summary surface (the [repo-summary read scope](appendix-a-glossary.md#repo-summary-read-scope)). They must not read sibling transcripts, inspect sibling diffs, or mutate sibling threads.

See [Authority](04-authority.md) for the full model.

## State is distinguishable without color

Every state kiki surfaces in any UI must be distinguishable without color. Glyphs and labels carry the signal. Color is an accelerator, never the only signal.

kiki honors [`NO_COLOR=1`](https://no-color.org/) by emitting no [ANSI color sequences](https://en.wikipedia.org/wiki/ANSI_escape_code). The shared [`LogRenderer` and `StatusRenderer`](appendix-a-glossary.md#logrenderer-statusrenderer) projections must produce monochrome-distinguishable output for every state in the cascade, agent, and lifecycle vocabularies.
