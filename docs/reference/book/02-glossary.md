# Glossary

Definitions of the load-bearing terms in kiki's reference. When a term is used in multiple places, this is the canonical definition.

## Concepts

- **Thread** — the kiki atom. A stable sqlite `thread_id` representing a themed sequence of jj revisions. Bookmark name, workspace path, tmux session, and agent harness session are mutable projections of that identity.
- **Bookmark** — jj's term for a named pointer to a revision. In kiki, the bookmark is the human-facing handle and the branch pushed to GitHub. Canonical identity stays with the stable sqlite `thread_id`.
- **Follows** — a directed parent-thread link enabling live cascade.
- **Ambient coordinator** — kiki's posture: it observes and reacts to jj/tmux/gh state without gatekeeping the underlying tools.
- **Active / Closed / Destroyed** — thread lifecycle states. Active = workspace and (often) agent live. Closed = soft archive: jj forgets the workspace, kiki removes the materialized directory after loss-prevention preflight plus post-stop recheck, and bookmark + revisions + transcript remain reopenable. Destroyed = `jj abandon`, irreversible except via `jj op restore`.

## Cascade

- **Cascade rebase** — automatic rebase of descendants when an ancestor changes, with pause-propagate-resume across agents.
- **Pause-propagate-resume** — the protocol that interrupts a child agent at the next safe boundary, performs the rebase, injects a context message, and resumes the agent.
- **Core invariant** — a thread's working copy is rebased only at agent tool boundaries or quiescence — never with the agent mid-edit.
- **Soft pause / Hard escalation** — soft = inject context via PreToolUse hook synthetic tool result. Hard = SIGINT + `--resume` with prepended user message.
- **`pending_cascade_seq` / `applied_cascade_seq` / `acknowledged_cascade_seq` / `delivered_in_flight_seq`** — three per-thread counters plus one per-agent-session counter that close both the soft-pause-detection race and the delivery-acknowledgement race without depending on PostToolUse (which Claude Code does not fire for tools blocked by PreToolUse).
  - `pending_cascade_seq` (per thread): bumped when cascade work is enqueued.
  - `applied_cascade_seq` (per thread): bumped at PreToolUse's decision step after the rebase is applied; captures "working copy moved."
  - `delivered_in_flight_seq` (per agent session): records what `applied_cascade_seq` was when a synthetic result was returned to that session.
  - `acknowledged_cascade_seq` (per thread): advanced at the _next_ PreToolUse on that session — the agent's follow-up tool call is the signal that the previous synthetic result was integrated.
- **`cascade_outbox`** — per-(thread, applied_cascade_seq) row carrying the synthetic payload composed at the decision step. Pins the payload across crash + retry boundaries so the visible `thread_messages` row (written inside the `MarkDelivered` handler, conditional on actual delivery) cannot be a phantom for content the agent never saw. See [cascade outbox](20-decisions/cascade-outbox.md).

## Transcript

- **Thread transcript** — kiki's local on-disk record of human-authored, agent-authored, and kiki-authored conversational text events per thread, bound to jj change-ids. Local-only (`<repo>/.kiki/state.db`, gitignored, never pushed). Rows distinguish `author` (`human|agent|kk`) from `direction` (`inbound_to_agent|outbound_from_agent|local_record`) so kiki-authored context is not misattributed to the agent.
- **Local-only-features rule** — the constraint that the thread transcript feeds back into AI-driven kiki features only at local boundaries (`kk reopen` catch-up in v1, agent self-query when same-thread transcript MCP ships). It does NOT feed into features producing externally-published artifacts (`kk publish` PR-drafter, auto-describe, auto-rename).
- **`synthesized=TRUE`** — flag on a transcript row indicating it is kiki-composed content the agent received (cascade injections, reopen catch-up, hard-escalation framing). The flag is what lets `kk reopen` catch-up exclude prior catch-ups from its source query, breaking the recursion that would otherwise compound on every reopen.
- **`anchor_unknown=TRUE`** — flag on a backfilled transcript row whose timestamp predates the available `op_history` and cannot be reliably anchored to a `(change_id, commit_id, op_id)`. Anchor-aware queries skip these rows by default; `--recent` and FTS5 search include them. See [transcript anchoring](20-decisions/transcript-anchoring.md).
- **TranscriptAdapter** — the capture-side trait abstracting per-harness session-record discovery, tailing, projection to `(author, direction, text, dedup_key)`, and offset reporting. v1 adapter: Claude Code JSONL.

## Agent and harness

- **Harness** — an agent runtime kiki spawns and coordinates with (Claude Code in v1; Codex and others deferred). Exposes a `Harness` factory trait + `RunningAgent` instance trait.
- **Capabilities** — typed struct returned by a `Harness` describing what it supports (`soft_pause`, `session_resume`, `structured_tool_hooks`, `mcp_client`, `quiescence_detection`). The cascade orchestrator branches on this struct to degrade gracefully.
- **PreToolUse hook** — the Claude Code hook point kiki uses to intercept tool calls for cascade delivery. Implemented by `kk-hook`. Cascade does not use PostToolUse because Claude Code does not fire it for tools blocked by PreToolUse.
- **`ContextMessage`** — `{ kind: MessageKind, text: String, structured: Option<JSON> }` — the unit of cascade communication queued for a thread's agent.

## Auth

- **`Admin` credential** — required for global, cross-thread, or destructive daemon mutations. Stored at `~/.kiki/admin-cred` (mode `0600`). Read by the human CLI / TUI on each invocation.
- **`ThreadScoped<T>` credential** — bound to one thread. Stored at `<workspace>/.kiki/hook-cred` (mode `0600`). Read by `kk-hook`, the persistent sidebar, and the same-thread MCP client when MCP ships. Rotated on close and reopen.
- **Repo-summary read scope** — the small expansion of `ThreadScoped<T>` allowing a sidebar process to subscribe to read-only one-line summaries of sibling threads in the same repo. Same-repo only, read-only, summaries only (no diffs, no transcripts). The single cross-thread read a `ThreadScoped<T>` credential can perform.

## State

- **`op_history`** — per-(repo, op_id, workspace_id) cache of `(committed_at, change_id, commit_id, parent_op_id)` populated by the live op-log watcher and by the daemon-restart op-log catch-up. The per-workspace key is load-bearing: jj's op log is repo-shared but `@` is per-workspace. Consulted by the transcript backfill path.
- **`pending_kkd_prepends`** — TTL-bounded sidecar table the JSONL projector consults to recognize kiki-composed `--resume` prepended messages and capture them as `synthesized=TRUE`.

## UI

- **Overlay TUI** — the interactive `kk` UI invoked from inside tmux via `prefix+k` (or by running bare `kk` inside a registered repo). Two-pane: left sidebar with Stack and Activity sections, right content pane (transcript / diff / PR comments). Carries the full action set (spawn, publish, close, interrupt) gated behind confirmation modals for destructive verbs. Dismissed with `q` / `esc`.
- **Persistent sidebar pane** — opt-in left tmux pane (default 32 cols) running a long-running `kk sidebar --thread <id>` ratatui process. Renders the same Stack + Activity sections as the overlay sidebar, restricted to navigation-only keybindings.
- **Stack-aware collapse** — `kk log`'s default topology rule: the current thread plus its full follows-ancestor chain renders revision-by-revision; siblings, descendants-not-on-the-current-line, and unrelated threads collapse to one-line summaries; trunk renders as its own root.
- **`LogRenderer` / `StatusRenderer`** — pure-function rendering modules in `kiki-core`. `LogRenderer` produces the stack-aware revision view; `StatusRenderer` produces the kk-shaped header used by `kk status` and reused by the sidebar via `--no-jj`. Single source of truth across CLI, overlay TUI, and persistent sidebar pane.

## v2 / future

- **Causal chain** — UUID stamped on each MCP-driven post, used to detect cycles, depth excess, and branch fan-out in inter-thread messaging. See [Roadmap](18-roadmap.md).
