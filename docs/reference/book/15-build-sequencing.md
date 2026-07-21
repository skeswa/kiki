# Build Sequencing

The riskiest v1 assumption is the cascade path. (The cascade is how kiki carries a parent thread's changes into the threads that follow it.) That path crosses four hard pieces: jj's native descendant evolution, stale-workspace materialization, explicit parent-tip advance, and each harness's tool boundary — Claude Code's parallel batch and Codex's proven-serial hook coverage. Validate that path before investing in the full daemon. A sequential single-hook demo is not sufficient evidence for Claude Code. And Claude Code's proofs are not evidence for Codex.

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
13. Crash thread creation at every external step. Prove the blocked harness launcher cannot execute before the journal, credentials, exclusive settings, live head, checkpoint, and tmux projections are durable.
14. Freeze a session containing agent, shell, and child processes. Prove that a failed final close check resumes and verifies that same session, while a failed resume becomes `CloseFailed` — never a dead `Active`.

The PoC needs no daemon, no TUI, and no polished CLI. Shell scripts are enough. It should answer one question: is the hardest coordination primitive real? Failure of exclusive hook isolation or batch-boundary identification blocks soft cascade delivery; v1 must then use hard restart for the affected harness version or declare it unsupported.

## First commit

Scaffold the Rust workspace:

- `kiki-core` library;
- `kkd` daemon binary;
- `kk` CLI binary;
- `kk-hook` sidecar binary.

Get gRPC working end-to-end over a unix socket, with a ping/pong call and one test.

## First feature slice

After the PoC:

1. `kk init`
2. `kk new <name>`
3. `kk switch <name>`
4. jj workspace and initial working-copy change creation
5. persisted live head, plus a bookmark checkpoint at that exact commit
6. credential and isolated hook-settings preparation
7. tmux session creation behind the database-backed launch gate
8. harness exec (Claude Code or Codex) as the final creation step

This slice should spawn a thread, attach to it, and start the agent only after exclusive hook ownership has been verified. No cascade, AI metadata, publish flow, or TUI is required.

## Foundation order

Build upward in this order:

1. `OpLogWatcher`, `OpAttribution`, and `AncestryQuery`.
2. `CascadeOrchestrator` base-transition classification; `WorkspaceProbe`/`WorkspaceRecovery`; the intent-owned batch barrier and delivery; native materialization; and explicit advance, integrated with `kk-hook` and `PostToolBatch`.
3. `ThreadLifecycleSaga`, the database-backed harness gate, bookmark checkpointing, and freeze/recheck close.
4. `ProjectionReconciler`, stable repair plans, `kk repair`, `AuthEnforcer`, the enrolled foreground presenter, the two-phase one-shot approval broker, and scoped/unscoped SQLite audit interception.
5. Minimal `ConfigLoader`, `LogRenderer`, `StatusRenderer`, `kk log`, `kk status`, `kk thread detach`, and the audit-read commands.

v1.x polish (enumerated in [Orientation](01-orientation.md)) builds on top of that, in this order:

1. Stack-aware `kk publish`, lazy GitHub validation, and editor integration.
2. Transcript capture, human reads, durable provider-consent management, consented reopen catch-up, and then consent-gated same-thread MCP.
3. Metadata ownership, plus auto-describe/auto-rename and the full configuration mutation surface.
4. Overlay TUI, persistent sidebar, GitHub polling and comments, and auto-archive.

## Acceptance integration gate

[Orientation](01-orientation.md#v1-contract) is the sole enumeration of the acceptance slice. The integration gate exercises every item in that ledger together, against a real jj repo, real tmux, and each shipped harness — Claude Code and Codex. This chapter defines build order, not a second scope list. Passing the gate requires neither `gh` nor network access beyond the configured harness. V1.x work deepens the accepted coordinator; it cannot substitute for a missing ledger item.

## Budget

The expected v1 build budget is:

- acceptance slice: 5-7 weeks, plus up to 1 week for the second harness adapter's launch-isolation and boundary proofs. The protocol, sidecar, and orchestrator are shared; the Codex-specific work is the generated `CODEX_HOME`, the version fixtures, and the gate;
- first v1.x workflow tranche (publish and transcript): 3-5 additional weeks;
- edge-case buffer: 1-2 weeks.

The buffer belongs to core op-log classification and restart catch-up cases, exclusive hook-settings compatibility, parallel-batch barriers, lifecycle compensation, projection repair, jj op-id dedupe, and cascade retry paths. Additional harness and version diagnostics, and non-core op-log compatibility cases, remain in their v1.x tranche. Transcript and sidebar edge cases likewise do not consume the acceptance buffer.
