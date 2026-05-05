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
  <a href="docs/prds/0001-kiki.md"><img alt="Status: pre-alpha" src="https://img.shields.io/badge/status-pre--alpha-orange" /></a>
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
    A ==>|"follows<br/>auto-rebase + inform on evolve"| B

    classDef trunk fill:#1a1a1a,stroke:#888,color:#fff
    classDef thread fill:#f5f5f5,stroke:#888,color:#222
    classDef affected fill:#eef4ff,stroke:#3b82f6,color:#1e3a8a
    linkStyle 2 stroke:#3b82f6,stroke-width:2.5px
```

<p align="center"><sub><i>Each thread is its own jj workspace, tmux session, and agent. <code>add-tests</code> <b>follows</b> <code>payment-refactor</code> — when its parent evolves, kiki rebases <code>add-tests</code> onto the new base and informs Agent B at the next safe boundary.</i></sub></p>

kiki is a single workflow for working on several pieces of code at once, with several AI agents at once. It ties together [jujutsu (jj)](https://github.com/jj-vcs/jj), [tmux](https://github.com/tmux/tmux), [Claude Code](https://claude.com/claude-code), and the GitHub CLI behind a single command, `kk`. Each thread — the atom of the system, sketched above — is isolated on disk so concurrent edits don't stomp on each other, and related in history so a refactor and the test-writing it implies can run alongside one another instead of one after the other. When the ground shifts under a thread, kiki rebases it and tells its agent without losing the agent's in-flight reasoning; that mechanism gets its own section below.

The complete spec is at [`docs/prds/0001-kiki.md`](docs/prds/0001-kiki.md); what's actually built today is captured in the [Status](#status) section below.

## What problem is being solved

Working with an AI agent on a single piece of code is largely a solved problem. Working with an agent — or several — on several pieces of code at once is not. The friction is in the seams. You stash, you switch branches, you launch a fresh agent on a new prompt, and three minutes later the original branch is in a state you have to reconstruct, the new agent has lost the thread of what you set out to do, and the version-control history has accreted bookkeeping artifacts of the context-switch rather than the work. Multiply this by three or four lines of inquiry in flight and the cost of opening another one becomes prohibitive enough that you don't.

This is unsatisfying for a number of reasons, but the most important is that it forces a serial discipline on what is fundamentally a parallel activity. Refactoring a function and migrating its callers is not a sequential task; it is a tree of work. Investigating a bug while keeping a feature branch healthy is not a sequential task. The right tool would let those branches of inquiry exist in parallel, without their work-trees stomping on each other, without their agents losing context when an ancestor changes, and without requiring the human to manually rebase the world every time something underneath them moves.

kiki is an attempt to build that tool.

## The design, briefly

The unit of work is a **thread**: a themed sequence of jj revisions on a bookmark, materialized in its own jj workspace, attached to its own tmux session running an agent. Threads are isolated on disk (one workspace each, no shared working copy) and related in history (they share the underlying jj repository). A thread is the thing you spawn, switch between, publish, and close.

Threads can be related: `kk new add-tests --follows payment-refactor` records a follow-edge in kiki's state. When the parent thread evolves — its bookmark advances, or a revision in its history is amended — kiki rebases the descendant onto the new base and informs its agent at the next safe boundary. The mechanism for that last step is the part of the system that warrants the most careful description, so it gets its own section below.

When the work is ready to leave the local machine, `kk publish` opens an editor with an AI-drafted PR title and body and creates a pull request against the parent thread's branch. If the parent itself has not been published yet, kiki publishes it first, walking up the stack and opening an editor for each, so that the human reviews each PR as it lands. When the PR merges upstream, kiki auto-archives the thread; when a parent merges, descendants are rebased onto `main`, force-pushed with `--force-with-lease`, and detached from the merged parent's follow-edge.

`kk close` is non-destructive. It removes the thread's workspace and tmux session and hides it from default listings, but the bookmark and revisions stay in the repository; `kk reopen` restores the workspace, rebuilds the tmux session, and resumes the agent via its session-id. (A separate `kk thread destroy` exists for actually removing the bookmark, gated behind explicit confirmation.)

## How an agent learns its base just changed

Several of the harder design questions reduce to one: when an ancestor revision is amended while a descendant thread's agent is actively editing, how does the agent come to know that its working copy has been rebased without losing the thread of what it was doing?

The honest answer is that current agent harnesses were not designed with this case in mind. Sending the agent a SIGINT and restarting it via `--resume` is reliable but disruptive — it loses the in-flight reasoning and forces a fresh framing of the work. What we want is something gentler: a mechanism that interrupts the agent at a moment when the interruption is cheap, hands it the new context in a form it already knows how to read, and lets it carry on.

Claude Code's `PreToolUse` hook turns out to be exactly that mechanism. The hook fires immediately before any tool invocation, can return arbitrary text that the agent reads as the tool's result, and can block the in-flight tool. kiki uses this primitive as a gate, coordinated by four counters: three live on the thread — `pending_cascade_seq` advances when a cascade is enqueued, `applied_cascade_seq` when the rebase actually runs, `acknowledged_cascade_seq` when the agent's next tool call confirms the synthetic result was integrated — and the fourth, `delivered_in_flight_seq`, lives on the agent's session and is set once a synthetic result has been written to the agent's stdout.

When the op-log watcher observes a change that requires rebasing a descendant thread, the daemon does not run `jj rebase` immediately. Instead it bumps the thread's `pending_cascade_seq` counter and enqueues a cascade message. On the agent's next tool call, `PreToolUse` claims the cascade lock, asks the daemon to apply the rebase under the hook's protection, advances `applied_cascade_seq`, _reads_ the cascade queue, releases the lock, and returns a synthetic tool result of the form _"Your base was rebased onto X. Files {a, b} have new contents. Re-read them before continuing."_

The hook then — and only then, after the synthetic result has actually been emitted on stdout — issues a separate `MarkDelivered` RPC to set `delivered_in_flight_seq`. This ordering is the load-bearing detail of the protocol: writing the marker last means every crash window degrades to _double delivery_ (next PreToolUse re-delivers from the un-drained queue) rather than _false acknowledgement_ (queue drained for a cascade the agent never saw).

When the agent's follow-up tool call eventually comes — and that follow-up is the strongest signal that the agent has actually integrated the synthetic result — that next `PreToolUse` runs an acknowledgement step first, promoting `delivered_in_flight_seq` into the thread's `acknowledged_cascade_seq` and draining the queue up to that point. Only then does it consider whether to deliver another cascade. PostToolUse is deliberately not part of this state machine: Claude Code does not fire PostToolUse for tools that PreToolUse blocked, so tying acknowledgement to PostToolUse would silently lose every cascade. If the agent crashes between delivery and the follow-up tool call, the queue is undrained and a fresh `--resume` session — initialized with `delivered_in_flight_seq=0` — will see `pending_cascade_seq > acknowledged_cascade_seq` and re-deliver the cascade idempotently. The blast radius is at most one tool-call interval, and the agent never sees a working copy it didn't expect or silently misses a cascade.

The invariant that falls out of this ordering is the property that makes the whole design defensible: a thread's working copy is rebased only when the agent is at a tool boundary — never when it is mid-edit. The daemon does not perform the rebase until the hook fires; the hook fires only at tool boundaries; and tool boundaries are by construction moments when no edit is in flight. When the rebase fails — that is, when it produces a textual conflict the agent must consciously resolve — kiki escalates: SIGINT the agent, restart with `--resume` and a framing message that tells it what happened, and notify the human. The cascade does not silently advance through conflicts.

```mermaid
sequenceDiagram
    autonumber
    participant agentA as Agent A
    participant kkd as kkd
    participant hookB as kk-hook for B
    participant agentB as Agent B

    agentA->>kkd: amends ancestor revision X
    Note over kkd: op-log watcher detects op<br>identifies B as affected
    kkd->>kkd: bump B.pending_cascade_seq<br>enqueue ContextMessage<br>no jj rebase yet

    agentB->>hookB: PreToolUse — next tool call
    Note over hookB: ack step: delivered_in_flight_seq=0<br>nothing to acknowledge
    hookB->>kkd: is pending_cascade_seq > acknowledged_cascade_seq?
    Note over kkd: yes — claim cascade lock<br>apply jj rebase, advance applied_cascade_seq<br>read but do not drain the queue<br>release lock
    kkd-->>hookB: synthetic tool result content
    hookB-->>agentB: writes synthetic result to stdout<br>and blocks original tool call
    Note over agentB: reads result as tool output<br>re-reads affected files — reasons further
    hookB->>kkd: MarkDelivered with session_id and applied_cascade_seq
    Note over kkd: NOW set session.delivered_in_flight_seq<br>written AFTER stdout — a crash here<br>causes double-delivery, not false-ack

    agentB->>hookB: PreToolUse — follow-up tool call
    Note over hookB: ack step: delivered_in_flight_seq > 0<br>promote into acknowledged_cascade_seq<br>drain queue, clear delivered_in_flight_seq
    hookB->>kkd: is pending_cascade_seq > acknowledged_cascade_seq?
    Note over kkd: no — fast-path pass-through
    hookB-->>agentB: tool proceeds normally
    Note over agentB,kkd: If agent crashes BEFORE the follow-up PreToolUse,<br>fresh --resume session has delivered_in_flight_seq=0<br>queue is still undrained → idempotent re-delivery
```

## kiki does not gatekeep

A design choice that pervades the rest of the system: kiki watches the jj op log and reacts to whatever it sees, regardless of who initiated the operation. A human running `jj rebase` directly in a thread's workspace, an agent invoking `jj` via Bash, kkd itself rebasing a child onto a parent's new tip — all three flow through the same code path. The daemon does not refuse direct jj or gh or tmux invocations, does not require its CLI to be the channel for repository operations, and does not maintain a separate, authoritative copy of the world. The op log is the source of truth.

This is not a small choice. Building kiki as a gatekeeper — wrapping every jj invocation, intercepting every tmux command — would be a substantial undertaking and would degrade the user's existing relationship with those tools. Building it as an ambient coordinator that observes and reacts is harder in some ways (the daemon must distinguish its own operations from external ones to avoid self-triggered loops; it must coalesce rapid-fire op storms into single cascades) but produces a tool that is additive rather than invasive. The tmux-server analogy is exact: tmux does not refuse to let you `cd` somewhere weird in a pane, and it does not get upset if you launch a process outside a session. kiki holds the same posture.

## A durable record of what was said

Diffs are a record of what changed; they are not a record of what was _said_. That distinction matters more than it sounds. If you spent forty minutes investigating a bug, watched the agent trace through three dead ends, and finally landed on the right two-line change — the diff captures the two lines. The reasoning, the false starts, the user prompts that nudged the investigation, the moment the agent noticed that the test was wrong rather than the code: all of it lives in the agent's session and dies with the agent's session.

kiki keeps it.

For each thread, kkd captures the interleaved text exchange between the user and the agent — what the user typed, what the agent said back, the synthetic tool results kiki itself injected during cascade — and binds each message to the jj change-id that was `@` when the message was captured. The result is a log that travels with the work: change-ids are preserved by `jj rebase`, so when a descendant cascades onto a new base its message bindings come along for free, no re-anchoring required. When the agent crashes and `kk reopen` brings it back, kkd seeds the resumed session with a catch-up message synthesized from the log, so the resume is not a cold start.

Two things the log is _not_. It is not a published artifact: messages live in `<repo>/.kiki/state.db`, gitignored, and never leave the local machine — agent prose contains dead ends, tool errors, and quoted file contents that should not surface in a PR description. And it is not a structured event log: it captures the narrative (`source: user | agent`, `text`), not the token-streaming deltas, the tool-call arguments, or the extended-thinking blocks. The diff still tells you _what_; the log tells you _why_.

Two surfaces read it. The human reads the log via `kk thread log [<change>]`, with full-text search over the whole thread. The agent reads its own thread's log via a small MCP server kkd hosts — four tools, all read-only, all bounded to the calling thread. Cross-thread reads are deliberately a v2 concern: an agent in B reading agent A's transcript is a pleasing idea with a quiet failure mode (context pollution, prompt leakage between threads), and v1 is the wrong place to ship it without the v2 substrate's safety mechanisms.

The log feeds back into AI-driven kiki features only at _local_ boundaries — the `kk reopen` catch-up, the agent's own MCP query mid-task. It is deliberately _not_ read by `kk publish`'s PR-drafter or by auto-describe / auto-rename. A boring PR description costs you nothing irreversible; a PR description that quotes "the user said their boss is being unreasonable about the deadline" costs you a hard-to-undo embarrassment. The local-only stance only holds if local-only-features is a discipline, not a default.

The capture path itself is abstracted behind a `TranscriptAdapter` trait — Claude Code is the v1 implementor, Codex slots in for v2 — so the schema and read API stay harness-neutral while the way bytes flow into the log can vary per harness.

## Architecture

```mermaid
graph TD
    kkd["<b>kkd</b> daemon<br/>Owns all state and behavior<br/>Single user-scoped process"]
    socket[/"Stable gRPC contract over ~/.kiki/kkd.sock"/]
    mcp[/"Read-only MCP over ~/.kiki/kkd-mcp.sock<br/>(thread-log tools, calling thread only)"/]
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
    mcp --> agent
    socket -.-> gui
    socket -.-> remote

    classDef future stroke-dasharray: 5 5,opacity:0.6
    class gui,remote future
```

Cleanly stated: `kkd` is a single user-scoped daemon (one process per user, opted into per-repository via `kk init`) that owns all state and behavior — thread lifecycle, the jj op-log watcher, the cascade orchestrator, the agent harness adapters, the thread-log capture path, the AI background queue, the GitHub poller. `kk`, the TUI (a subcommand of `kk`), and the small `kk-hook` PreToolUse sidecar are clients of a stable gRPC contract over a unix socket. The agent itself is a client of a sibling socket: a narrowly-scoped read-only MCP server exposing exactly the thread-log retrieval tools, bounded to the calling thread (broader cross-thread MCP is the v2 substrate). There is no privileged internal API. A native macOS GUI written next year will consume the same gRPC surface today's clients do; that is the property that makes the design durable.

State is partitioned. `~/.kiki/state.db` is the user-scoped registry of which repositories are managed and where the daemon is reachable. `<repo>/.kiki/state.db` holds the per-repository runtime state — threads, workspaces, agent sessions, hook state, the AI queue, the metadata-ownership ledger, the op-attribution dedupe table. Removing one repository's `.kiki/` directory wipes that repository's kiki state without disturbing any other.

The implementation language for `kkd` and its CLI clients, per the PRD, is Rust — driven by the long-term path to embedding [jj-lib](https://github.com/jj-vcs/jj) directly in the daemon, by the Send/Sync guarantees the cascade-coordination code wants, and by the maturity of `tonic`/`notify`/`rusqlite`/`ratatui`. The repository as it stands is a Bun+TypeScript scaffold for tooling experiments; the language decision is the first major implementation milestone, gated by the proof-of-concept described in the PRD's _Suggested build sequencing_ section.

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

# Publish the stack, top-down
$ kk publish

# Close when done; the workspace is removed but revisions persist
$ kk close
```

A persistent tmux status-line strip surfaces threads needing attention; OS-native notifications fire when an agent hits a permission prompt, when a cascade encounters a conflict, when a parent thread merges or is abandoned, or when a CI check fails on a thread's pull request. From inside any thread session, a tmux keybinding overlays the TUI for fast switching and spawning.

## Roadmap

| Milestone              | Highlights                                                                                                                                                                                                                                                                                                                                                                                                            |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **v1 — the demo**      | Thread atom, live-follow cascade, PreToolUse-based pause-propagate-resume, AI auto-rename and auto-describe with content-hash ownership ledger, change-id-aligned thread log with same-thread read-only MCP surface and `kk reopen` catch-up, `kk publish` with stack recursion, `kk close`/`kk reopen`, ratatui TUI, GitHub PR auto-archive on merge, Claude Code adapter. Estimated 7–10 weeks of focused work.     |
| **v1.x**               | Polish: hook-config diagnostics, op-log watcher edge cases, more `kk thread` subcommands, status-line themes.                                                                                                                                                                                                                                                                                                         |
| **v2 — the substrate** | MCP surface expanded beyond v1's read-only same-thread log: agents in one thread can post messages to siblings, spawn children, request human review — with causal-chain cycle detection, depth and branching caps, and a complete audit trail. Codex harness adapter (slotting into the v1 `TranscriptAdapter` trait). Native macOS GUI. Direct GitHub REST/GraphQL. PR review-comment ingestion into agent context. |
| **v3+**                | jj-lib embedded directly in kkd. Web dashboard. Cross-repository coordinated agent tasks.                                                                                                                                                                                                                                                                                                                             |

The full spec — including v2's MCP design, captured in the same document so it is not lost between revisions — lives in [`docs/prds/0001-kiki.md`](docs/prds/0001-kiki.md).

## On the name

There are two reasons the tool is called kiki, and they reinforce each other.

The first is a small ergonomic joke. The CLI binary is `kk`, which sits on the home row immediately to the right of `jj` — and `jj`, of course, is the version control system the entire design rests on. Typing `jj` and `kk` next to each other on the home row, day after day, is a quiet acknowledgement that one of these tools is working underneath the other.

The second reason is more important. A [_kiki_](<https://en.wikipedia.org/wiki/Kiki_(social_gathering)>) is a social gathering with roots in Black and Latin American queer ballroom culture: a flourishing space where people show up as themselves, with their own intent and their own style, and the gathering is richer for the multiplicity. That is the spirit the tool is reaching for. A development environment in which humans and agents — of varying capabilities, varying harnesses, varying purposes — can show up alongside one another, productively, without stepping on each other's work, and produce something that none of them would produce alone. The 💅🏾 is the logo for the same reason: a small reminder that craft, presence, and ease can coexist with seriousness of purpose.

## Status

Pre-alpha. Spec phase. The PRD is complete and has survived one Codex review pass; implementation has not begun. The repository's TypeScript scaffolding is provisional and exists to make tooling decisions easier; the production code is slated to be Rust per the spec, and the language decision will be revisited at the gating proof-of-concept.

If this looks like a tool that would change how you work, the most useful thing you can do today is read the PRD and file an issue on anything that strikes you as wrong, missing, or under-specified. The spec is durable enough that pre-implementation feedback is genuinely actionable.

## Building

```sh
mise install         # provision pinned tooling (Bun, currently)
bun install          # install dev dependencies (oxfmt, types)
bun run fmt          # format
```

Once the v1 build begins this section will gain `cargo build`, `cargo test`, and `kk` invocations.

## Design principles, explicit

A few principles, stated up front, because the PRD's coherence depends on them:

1. **Be additive, not invasive.** The user can keep using jj, gh, and tmux as they always have. kiki reacts to what they do; it does not refuse, intercept, or wrap.
2. **Trust human prose.** Auto-rename and auto-describe are useful, but the moment a human types their own description, kiki steps off permanently. There is no path where kiki silently overwrites human-authored content.
3. **One stable contract; many UIs.** The gRPC service is the product surface. The CLI and TUI are first clients, not privileged ones. A native GUI built later sees the same API.
4. **High cohesion, low coupling.** kkd owns state and behavior; UIs are pure views. Internally, per-thread controllers are isolated from cross-cutting concerns, so killing one thread never destabilizes the daemon.
5. **Fail loud, not silent.** Cycle detection, force-push reconciliation, parent-thread-abandoned prompts: when the system genuinely cannot determine the right action, it stops and asks rather than guessing.
6. **No resource policing.** kiki does not cap concurrent agents, model spend, or laptop CPU. Those are the user's decisions, made with the user's tools.
7. **Local recall, never silent leak.** The thread log is captured for human and agent recall and lives only on the local machine. It feeds back into AI features only at local boundaries (`kk reopen` catch-up, agent self-query); it does not feed into features that produce externally-published artifacts (PR drafts, auto-described revisions). The local-only stance only holds if local-only-features is a discipline, not a default.

## Built on the shoulders of

- [**jujutsu (jj)**](https://github.com/jj-vcs/jj) — the version control system whose first-class workspaces, op log, and rebase semantics make the entire design viable. kiki is not possible without jj.
- [**tmux**](https://github.com/tmux/tmux) — both a runtime dependency and the architectural anchor for the system's shape. A single user-scoped daemon serving sessions across any directory, with thin clients over a stable IPC, is the model kiki imitates.
- [**Claude Code**](https://claude.com/claude-code) — the agent harness whose `PreToolUse` hook system makes the cascade-aware context-injection mechanism viable.
- [**GitHub CLI (`gh`)**](https://cli.github.com) — for publishing, PR state inspection, and review comments.

## Contributing

The PRD is [`docs/prds/0001-kiki.md`](docs/prds/0001-kiki.md). Some expectations for substantial changes:

1. Open an issue describing the change. PRDs for substantial work go in `docs/prds/`, numbered.
2. PRDs in this repository are expected to survive a [Codex](https://github.com/openai/codex) review pass — the first PRD's review surfaced three v1-scope contradictions, all resolved in the same revision. Keep Out of Scope, User Stories, and Implementation Decisions consistent with each other.
3. Commits follow a one-line imperative subject plus a multi-paragraph body; `jj log` has examples.
4. Future Claude Code instances reading the repository should consult [`CLAUDE.md`](CLAUDE.md) first.

## License

[MIT](LICENSE) © 2026 Sandile Keswa
