<div align="center">

<br />

<h1>
  💅🏾
  <br />
  kiki
</h1>

<h4>A daemon-backed coordinator for multi-threaded coding with AI agents</h4>

<p>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg" /></a>
  <a href="docs/reference/README.md"><img alt="Status: pre-alpha" src="https://img.shields.io/badge/status-pre--alpha-orange" /></a>
  <a href="https://github.com/jj-vcs/jj"><img alt="VCS: jujutsu" src="https://img.shields.io/badge/vcs-jujutsu-purple" /></a>
  <a href="https://claude.com/claude-code"><img alt="Harness: Claude Code" src="https://img.shields.io/badge/harness-claude_code-9b59ff" /></a>
</p>

<br />

</div>

---

```mermaid
graph TD
    main[("main")]:::trunk

    A["payment-refactor<br/><sub>Agent A</sub>"]:::thread
    C["bug-investigation<br/><sub>Agent C</sub>"]:::thread
    B["add-tests<br/><sub>Agent B</sub>"]:::affected

    main --> A
    main --> C
    A ==>|"follows<br/>reconcile + inform on evolve"| B

    classDef trunk fill:#1a1a1a,stroke:#888,color:#fff
    classDef thread fill:#f5f5f5,stroke:#888,color:#222
    classDef affected fill:#eef4ff,stroke:#3b82f6,color:#1e3a8a
    linkStyle 2 stroke:#3b82f6,stroke-width:2.5px
```

<p align="center"><sub><i>Each thread is its own jj workspace, tmux session, and agent. <code>add-tests</code> <b>follows</b> <code>payment-refactor</code> — when its parent evolves, jj updates repository history and kiki reconciles <code>add-tests</code>'s files and informs Agent B at the next safe boundary.</i></sub></p>

kiki is a single workflow for working on several pieces of code at once, with several AI agents at once. It ties together [jujutsu (jj)](https://github.com/jj-vcs/jj), [tmux](https://github.com/tmux/tmux), [Claude Code](https://claude.com/claude-code), and the GitHub CLI behind a single command, `kk`. Each thread — the atom of the system, sketched above — is isolated on disk so concurrent edits don't stomp on each other, and related in history so a refactor and the test-writing it implies can run alongside one another instead of one after the other. When the ground shifts under a thread, jj may evolve its history immediately; kiki waits for a safe boundary before materializing that state in the thread's files and telling its agent. That mechanism gets its own section below.

The complete reference book is at [`docs/reference/README.md`](docs/reference/README.md); its Orientation chapter is the sole scope ledger, and what's actually built today is captured in the [Status](#status) section below.

## What problem is being solved

Working with an AI agent on a single piece of code is largely a solved problem. Working with an agent — or several — on several pieces of code at once is not. The friction is in the seams. You stash, you switch branches, you launch a fresh agent on a new prompt, and three minutes later the original branch is in a state you have to reconstruct, the new agent has lost the thread of what you set out to do, and the version-control history has accreted bookkeeping artifacts of the context-switch rather than the work. Multiply this by three or four lines of inquiry in flight and the cost of opening another one becomes prohibitive enough that you don't.

This is unsatisfying for a number of reasons, but the most important is that it forces a serial discipline on what is fundamentally a parallel activity. Refactoring a function and migrating its callers is not a sequential task; it is a tree of work. Investigating a bug while keeping a feature branch healthy is not a sequential task. The right tool would let those branches of inquiry exist in parallel, without their work-trees stomping on each other, without their agents losing context when an ancestor changes, and without requiring the human to manually rebase the world every time something underneath them moves.

kiki is an attempt to build that tool.

## The design, briefly

The unit of work is a **thread**: a themed sequence of jj revisions with a live head at its managed workspace's `@`, attached to its own tmux session running an agent. A bookmark is an explicit checkpoint and publication projection; it is not assumed to move merely because `jj new` created another revision. Threads are isolated on disk (one workspace each, no shared working copy) and related in history (they share the underlying jj repository). A thread is the thing you spawn, switch between, publish, and close.

Threads can be related: `kk new add-tests --follows payment-refactor` records a follow-edge in kiki's state. When an ancestor is amended, jj itself evolves descendants in repository state and may leave their workspace files stale; kiki materializes each affected workspace and informs its agent at that agent's next safe boundary. When the parent's live head instead gains a new commit, kiki explicitly rebases the child's provably linear owned stack onto that exact commit at the same boundary. Ambiguous or merged topology stops for a human instead of expanding an inferred revset. The distinction is load-bearing, so it gets its own section below.

After the coordination core is proven, the first v1.x `kk publish` flow checkpoints the thread bookmark, opens an editor with a deterministic title/body template, and creates a pull request against the parent thread's branch. It makes no model call; AI drafting arrives later with metadata evolution. If the parent itself has not been published yet, kiki publishes it first, walking up the stack and opening an editor for each, so that the human reviews each PR as it lands. When a parent merges, descendants reconcile locally onto the exact merged `main` commit at their safe boundaries. The resulting lease-protected force-push and PR-base update remain a named remote plan until separately approved in the foreground; the follow-edge is removed only after those effects are observed coherent.

`kk close` is non-destructive. It freezes the managed process tree, rechecks the exact approved loss-safety plan, checkpoints without snapshotting, reconciles child detaches, and only then removes the tmux session and workspace. A failed recheck or child step resumes and verifies the original session instead of leaving a dead thread labeled active. `kk reopen` runs a durable saga that remains closed until the replacement is ready. A later, separately approved `kk thread destroy` removes kiki's thread identity and local projections while preserving jj revisions by default; `--abandon-revisions` requires its own exact-chain approval.

## How an agent learns its base just changed

Several of the harder design questions reduce to one: when an ancestor revision is amended while a descendant thread's agent is actively editing, how does the agent come to know that jj evolved its working-copy commit without changing the thread's files underneath it?

The honest answer is that current agent harnesses were not designed with this case in mind. Sending the agent a SIGINT and restarting it via `--resume` is reliable but disruptive — it loses the in-flight reasoning and forces a fresh framing of the work. What we want is something gentler: a mechanism that interrupts the agent at a moment when the interruption is cheap, hands it the new context in a form it already knows how to read, and lets it carry on.

Claude Code's `PreToolUse` hook supplies that boundary, but only when kiki can prove exclusive control of that hook class for the managed session; current Claude Code runs matching handlers concurrently, so v1 does not pretend user `PreToolUse` hooks can safely run after kiki. Kiki first classifies the jj transition from before/after operation views. A `NativeRewrite` pins a **base transition**: jj already evolved the descendant's repository commits from `from_base_commit` onto `to_base_commit`, so kiki normally needs only to materialize the stale workspace. A `ParentAdvance` means the parent's exact live head is outside the child's ancestry, so kiki explicitly rebases the child's validated single-parent owned stack onto `to_base_commit`.

Each transition lives in one durable `sync_intents` row. That row is the protocol authority: it owns the ordered intent sequence, normalized trigger operation ids, state, planned and result operation ids, result workspace commit, recovery details, and the byte-stable payload and transcript anchor used for delivery. There are no shadow progress counters, context queue, or separate cascade-outbox table whose state can disagree with it.

On the agent's next tool batch, the first `PreToolUse` claims the reconciliation lock and atomically binds the intent's durable `Block` barrier to the runtime incarnation, model turn, and tool batch **before** probing or mutating the workspace. Every sibling call observes that same decision, including after a hook or daemon restart. A provably clean stale workspace may then be materialized with `jj workspace update-stale`; a stale workspace with dirty or indeterminate on-disk edits enters `RecoveryRequired` and hard-pauses the agent. Recovery runs outside the source workspace, preserves and enumerates jj's divergent successors, verifies where the edits landed, and resumes only when kiki can prove the visible result still contains them.

After successful reconciliation, kiki atomically records the result, transcript anchor, payload, and `Materialized` state while preserving the already-bound barrier. The hook emits that saved payload and only then calls `MarkDelivered(intent_id, incarnation_id, model_turn_id, tool_batch_id)`. `MarkDelivered` records delivery; it does not arm the barrier. Writing delivery after stdout makes a crash cause idempotent redelivery rather than false acknowledgement.

`PostToolBatch` closes the delivery barrier after every call in the triggering batch has been blocked. Only a later `PreToolUse` produced by a later model turn may acknowledge the intent; another concurrent call from the original batch is never acknowledgement evidence. If the agent or hook crashes before that later turn, the replacement incarnation gets the exact saved payload again. A harness without a reliable batch-completion boundary uses `RestartStartup`: the replacement receives the payload as its first one-use-tagged startup message, reports ready with that `startup_delivery_id`, and only its first matching tagged `PreToolUse` proves acceptance and acknowledges delivery.

The resulting invariant is deliberately about the workspace, not the shared repository: kiki materializes evolved files or performs an explicit follows rebase only at the managed agent's boundary, never mid-edit. A direct human `jj` command in a stale child workspace is an explicit escape hatch and may materialize it earlier; kiki discovers the current file state at its next boundary rather than pretending every command was gated or observable in the op log. If reconciliation exposes a conflicted jj commit, kiki escalates: SIGINT the agent, restart with `--resume` and a framing message, and notify the human.

```mermaid
sequenceDiagram
    autonumber
    participant agentA as Agent A
    participant kkd as kkd
    participant hookB as kk-hook for B
    participant agentB as Agent B

    agentA->>kkd: amends ancestor revision X
    Note over kkd: jj evolves B in repository state<br>B's on-disk workspace is stale
    kkd->>kkd: classify NativeRewrite X1→X2<br>insert sync intent in Detected

    agentB->>hookB: PreToolUse — tool batch begins
    Note over hookB: no prior delivery barrier<br>claim reconciliation lock
    hookB->>kkd: request oldest unresolved intent
    Note over kkd: claim reconciliation lock<br>bind durable Block barrier first<br>probe workspace immediately<br>StaleClean → jj workspace update-stale<br>save result + payload as Materialized<br>while preserving barrier
    kkd-->>hookB: synthetic tool result content
    hookB-->>agentB: writes synthetic result to stdout<br>and blocks every call in this batch
    hookB->>kkd: MarkDelivered(intent + incarnation + turn + batch)
    Note over kkd: mark intent Delivered<br>preserve pre-bound barrier<br>written AFTER stdout — a crash here<br>causes double-delivery, not false-ack

    agentB->>hookB: PostToolBatch — triggering batch closed
    hookB->>kkd: MarkToolBatchComplete(incarnation + turn + batch)
    Note over hookB: barrier becomes awaiting-later-turn<br>payload will enter the next model request
    Note over agentB: reads result, re-reads affected files,<br>and produces a later model turn
    agentB->>hookB: PreToolUse — later-turn tool call
    Note over hookB: acknowledge delivered intent<br>clear delivery barrier
    hookB->>kkd: request oldest unresolved intent
    Note over kkd: none — fast-path pass-through
    hookB-->>agentB: tool proceeds normally
    Note over agentB,kkd: A concurrent PreToolUse from the original batch never acks.<br>If the agent crashes before the later turn,<br>replacement gets a new incarnation id<br>and byte-identical RestartStartup delivery;<br>its first matching tagged boundary proves acceptance.
```

## kiki does not gatekeep

A design choice that pervades the rest of the system: kiki watches the jj op log and reacts to whatever it sees, regardless of who initiated the operation. An agent invoking `jj` via Bash and kkd advancing a child onto a parent's new tip both become before/after jj views that the same classifier interprets. A human updating a stale workspace directly is also supported, although the file materialization may produce no new op and is then discovered by the boundary probe. The daemon does not refuse direct jj or gh or tmux invocations and does not maintain a competing version-history model. The op log is the source of truth for repository evolution; the current filesystem and jj workspace metadata are the source of truth for materialization.

This is not a small choice. Building kiki as a gatekeeper — wrapping every jj invocation, intercepting every tmux command — would be a substantial undertaking and would degrade the user's existing relationship with those tools. Building it as an ambient coordinator that observes and reacts is harder in some ways (the daemon must distinguish its own operations from external ones to avoid self-triggered loops; it must coalesce rapid-fire op storms into single cascades) but produces a tool that is additive rather than invasive. The tmux-server analogy is exact: tmux does not refuse to let you `cd` somewhere weird in a pane, and it does not get upset if you launch a process outside a session. kiki holds the same posture.

## A durable record of what was said

Diffs are a record of what changed; they are not a record of what was _said_. That distinction matters more than it sounds. If you spent forty minutes investigating a bug, watched the agent trace through three dead ends, and finally landed on the right two-line change — the diff captures the two lines. The reasoning, the false starts, the user prompts that nudged the investigation, the moment the agent noticed that the test was wrong rather than the code: all of it lives in the agent's session and dies with the agent's session.

kiki keeps it.

In the v1.x transcript layer, kkd captures the interleaved text exchange between the user and the agent — what the user typed, what the agent said back, and the synthetic results kiki injected during cascade — and binds each message to the jj change-id that was `@` when captured. Change-ids survive rebase, so the local recall surface follows the work. An opt-in `kk reopen --catch-up` can preview and send a short transcript-derived catch-up to the resumed harness.

Two things the log is _not_. It is not a published artifact: rows live in the per-repo runtime database under `~/.kiki/repos/<repo_id>/state.db`, never in the source repo, and never feed PR descriptions or automatic revision metadata. “Stored locally” does not mean “never leaves the machine”: when the user opts into catch-up, that selected text may be sent to the configured model provider. It is also not a structured event log: it captures narrative text, not token deltas, structured tool payloads, or extended-thinking blocks.

The v1.x transcript work starts with the human reader: `kk thread transcript [<change>]`, with full-text search over the whole thread. A narrow same-thread MCP reader may follow after that CLI proves stable. Cross-thread reads remain a v2 concern because context pollution and prompt leakage need a stronger substrate.

The log feeds back into AI-driven features only through explicit, provider-aware consent: catch-up in v1.x, and same-thread self-query only if the later MCP surface ships. MCP is local IPC on its first hop, but its tool result normally becomes hosted-model input, so missing `transcript_mcp` consent fails closed before any row is returned. The log is deliberately not read by PR drafting, auto-describe, or auto-rename. Local storage and no-publication are separate promises from provider egress, and the UI must say which boundary an action crosses.

The v1.x capture path itself is abstracted behind a `TranscriptAdapter` trait — Claude Code is the first implementor, and later harnesses can add projectors — so the schema and read API stay harness-neutral while the way bytes flow into the log can vary per harness.

## Architecture

```mermaid
graph TD
    kkd["<b>kkd</b> daemon<br/>Owns all state and behavior<br/>Single user-scoped process"]
    socket[/"Stable gRPC contract over ~/.kiki/kkd.sock"/]
    mcp[/"Read-only MCP over ~/.kiki/kkd-mcp.sock<br/>(same-thread transcript tools; v1.x polish)"/]
    cli["<b>kk</b> CLI"]
    tui["<b>kk</b> TUI<br/>(ratatui)"]
    hook["<b>kk-hook</b><br/>PreToolUse sidecar"]
    agent["agent<br/>(Claude Code)"]
    gui["Conductor-style<br/>native macOS GUI"]
    remote["web · remote ..."]

    kkd === socket
    kkd === mcp
    socket --> cli
    socket --> tui
    socket --> hook
    mcp -.-> agent
    socket -.-> gui
    socket -.-> remote

    classDef future stroke-dasharray: 5 5,opacity:0.6
    class mcp,gui,remote future
```

Cleanly stated: `kkd` is a single user-scoped daemon, opted into per repository via `kk init`, that owns durable lifecycle sagas, live-head and projection state, jj op-log interpretation, cascade recovery, batch-safe harness delivery, repair plans, and the two-phase approval broker. An operational client first requests a daemon-canonical challenge; a separately enrolled foreground presenter confirms that exact plan; the operation then atomically claims its one-use approval into a durable journal. `kk` and `kk-hook` are local clients of one gRPC contract over a unix socket; transcript, metadata, GitHub, and richer UI services join behind that contract in v1.x. A same-host native GUI can reuse it directly. Remote clients require a future network transport and authentication design rather than inheriting local-socket claims.

State is partitioned into one per-user database and one database per registered repo. `~/.kiki/state.db` is the user-scoped registry of managed repositories, daemon metadata, and audit rows for bootstrap, registry-wide, unknown-repo, and pre-resolution attempts. Each registered repository gets its own runtime database at `~/.kiki/repos/<repo_id>/state.db`, keyed by the UUID minted at `kk init`; that database holds threads, workspaces, agent sessions, hook state, cascades, and repo-resolved audit rows, with transcript and metadata tables added by their v1.x migrations. The source repository's filesystem holds no kiki runtime state; the only kiki file that may live there is optional committed `.kiki.toml`. Removing `~/.kiki/repos/<repo_id>/` removes that repository's kiki runtime state without disturbing other registered repos; `kk repo unregister` is the intended command path.

The implementation language for `kkd` and its CLI clients, per the reference book, is Rust — driven by the long-term path to embedding [jj-lib](https://github.com/jj-vcs/jj) directly in the daemon, by the Send/Sync guarantees the cascade-coordination code wants, and by the maturity of `tonic`/`notify`/`rusqlite`/`ratatui`. The repository as it stands is a Bun+TypeScript scaffold for tooling experiments; the language decision is the first major implementation milestone, gated by the proof-of-concept described in [Build Sequencing](docs/reference/book/17-build-sequencing.md).

## A small worked example

```sh
# Opt a repository in
$ cd ~/code/my-project
$ kk init

# Spawn a thread off main
$ kk new auth-refactor

# Spawn a child off it
$ kk new add-tests --follows auth-refactor

# Inspect the world
$ kk ls
  STATUS    THREAD            FOLLOWS         AGENT
  running   auth-refactor     -               claude-code
  running   add-tests         auth-refactor   claude-code

# Move between sessions
$ kk switch auth-refactor

# v1.x: publish the stack, top-down
$ kk publish

# Close when done; the workspace is removed but revisions persist
$ kk close
```

When the v1.x UI polish ships, a persistent tmux status-line strip can surface threads needing attention and a tmux keybinding can overlay the TUI for fast switching and spawning. Toasts exist only inside the overlay; a visible persistent sidebar remains state-only, so OS/tmux notifications still carry attention events when the overlay is closed. Core notifications cover permission prompts, cascade conflicts, and local parent lifecycle events; failed PR checks join only with v1.x GitHub polling.

## Roadmap

- **v1 — the acceptance slice.** The thread atom with explicit live-head semantics, recoverable create/close, provably linear live-follow cascade, batch-safe Claude Code delivery, projection repair, and basic `ls` / `log` / `status` / minimal configuration.
- **v1.x — workflow completion and polish.** Stacked publishing, local transcript capture and consented reopen catch-up, metadata ownership and later AI evolution, the overlay TUI and sidebar, GitHub polling, auto-archive, and same-thread transcript MCP reads.
- **v2 — the substrate.** Cross-thread agent messaging with causal-chain auditing, the Codex adapter, a native macOS GUI, direct GitHub REST/GraphQL.
- **v3+.** jj-lib embedded directly in kkd, a web dashboard, cross-repository coordination.

The canonical scope ledger — which surface belongs to which tier — is the book's [Orientation chapter](docs/reference/book/01-orientation.md); the full spec, including v2's MCP design, lives in the [`docs/reference/`](docs/reference/README.md) reference book.

## On the name

There are two reasons the tool is called kiki, and they reinforce each other.

The first is a small ergonomic joke. The CLI binary is `kk`, which sits on the home row immediately to the right of `jj` — and `jj`, of course, is the version control system the entire design rests on. Typing `jj` and `kk` next to each other on the home row, day after day, is a quiet acknowledgement that one of these tools is working underneath the other.

The second reason is more important. A [_kiki_](<https://en.wikipedia.org/wiki/Kiki_(social_gathering)>) is a social gathering with roots in Black and Latin American queer ballroom culture: a flourishing space where people show up as themselves, with their own intent and their own style, and the gathering is richer for the multiplicity. That is the spirit the tool is reaching for. A development environment in which humans and agents — of varying capabilities, varying harnesses, varying purposes — can show up alongside one another, productively, without stepping on each other's work, and produce something that none of them would produce alone. The 💅🏾 is the logo for the same reason: a small reminder that craft, presence, and ease can coexist with seriousness of purpose.

## Status

Pre-alpha. Spec phase. The reference book has absorbed the original PRD and multiple adversarial review passes; implementation has not begun. The repository's TypeScript scaffolding is provisional and exists to make tooling decisions easier; the production code is slated to be Rust per the spec, and the language decision will be revisited at the gating proof-of-concept.

If this looks like a tool that would change how you work, the most useful thing you can do today is read the reference book and file an issue on anything that strikes you as wrong, missing, or under-specified. The spec is durable enough that pre-implementation feedback is genuinely actionable.

## Building

```sh
mise install         # provision pinned tooling (Bun, currently)
bun install          # install dev dependencies (oxfmt, types)
bun run fmt          # format
bun run check:docs   # verify local links, anchors, and stale contract terms
```

Once the v1 build begins this section will gain `cargo build`, `cargo test`, and `kk` invocations.

## Design principles, explicit

A few principles, stated up front, because the reference book's coherence depends on them:

1. **Be additive, not invasive.** The user can keep using jj, gh, and tmux as they always have. kiki reacts to what they do; it does not refuse, intercept, or wrap.
2. **Trust human prose.** Auto-rename and auto-describe are useful, but the moment a human types their own description, kiki steps off permanently. There is no path where kiki silently overwrites human-authored content.
3. **One stable contract; many UIs.** The gRPC service is the product surface. The CLI and TUI are first clients, not privileged ones. A native GUI built later sees the same API.
4. **High cohesion, low coupling.** kkd owns state and behavior; UIs are pure views. Internally, per-thread controllers are isolated from cross-cutting concerns, so killing one thread never destabilizes the daemon.
5. **Fail loud, not silent.** Cycle detection, force-push reconciliation, parent-thread-abandoned prompts: when the system genuinely cannot determine the right action, it stops and asks rather than guessing.
6. **No resource policing.** kiki does not cap concurrent agents, model spend, or laptop CPU. Those are the user's decisions, made with the user's tools.
7. **Locally stored, explicit egress, never silent publication.** Transcript rows live under `~/.kiki/` and never feed PR drafts or automatic revision metadata. Sending selected text for catch-up or returning it through an agent-facing MCP tool is provider egress and requires purpose-specific remembered consent.

## Built on the shoulders of

- [**jujutsu (jj)**](https://github.com/jj-vcs/jj) — the version control system whose first-class workspaces, op log, and rebase semantics make the entire design viable. kiki is not possible without jj.
- [**tmux**](https://github.com/tmux/tmux) — both a runtime dependency and the architectural anchor for the system's shape. A single user-scoped daemon serving sessions across any directory, with thin clients over a stable IPC, is the model kiki imitates.
- [**Claude Code**](https://claude.com/claude-code) — the agent harness whose `PreToolUse` hook system makes the cascade-aware context-injection mechanism viable.
- [**GitHub CLI (`gh`)**](https://cli.github.com) — for publishing, PR state inspection, and review comments.

## Contributing

The reference book starts at [`docs/reference/README.md`](docs/reference/README.md). Some expectations for substantial changes:

1. Open an issue describing the change. Substantial work should update the reference book directly.
2. Spec changes in this repository are expected to survive a [Codex](https://github.com/openai/codex) review pass — the first PRD's review surfaced three v1-scope contradictions, all resolved before its contents were folded into the book. Keep neighboring chapters consistent with each other.
3. Commits follow a one-line imperative subject plus a multi-paragraph body; `jj log` has examples.
4. Future Claude Code instances reading the repository should consult [`CLAUDE.md`](CLAUDE.md) first.

## License

[MIT](LICENSE) © 2026 Sandile Keswa
