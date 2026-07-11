# Glossary

Definitions of the load-bearing terms in kiki's reference. When a term is used in multiple places, this is the canonical definition.

## Concepts

- **Thread** — the kiki atom. A stable sqlite `thread_id` representing a themed sequence of jj revisions. Bookmark name, workspace path, tmux session, and agent harness session are mutable projections of that identity.
- **Bookmark** — jj's term for a named pointer to a revision. In kiki, the bookmark is the human-facing handle and the branch pushed to GitHub. Canonical identity stays with the stable sqlite `thread_id`.
- **Follows** — a directed parent-thread link enabling live cascade.
- **Ambient coordinator** — kiki's posture: it observes and reacts to jj/tmux/gh state without gatekeeping the underlying tools.
- **Active / Closed / Orphaned / Destroyed** — thread lifecycle states. Active = workspace and (often) agent live. Closed = soft archive: jj forgets the workspace, kiki removes the materialized directory after loss-prevention preflight plus post-stop recheck, and bookmark + revisions + transcript remain reopenable. Orphaned = the materialized workspace directory is missing while the thread row still says Active (e.g., user ran `rm -rf`, the disk filled, or the dir was moved); kiki notifies once and waits for explicit human resolution via `kk reopen`, `kk thread destroy`, or a future `kk thread restore --to <path>`. Destroyed = `jj abandon`, irreversible except via `jj op restore`.

## Scope tiers

- **Acceptance slice** — what v1 must ship to be accepted. The canonical enumeration lives in [Orientation](01-orientation.md) and nowhere else; chapters describe behavior and link to the ledger for when it ships.
- **v1.x polish** — post-acceptance work that deepens v1 but must not block the acceptance slice unless explicitly promoted. Enumerated in the same [Orientation](01-orientation.md) ledger.

## Cascade

- **Cascade reconciliation** — the follows-aware process that classifies a parent change, waits for the affected managed agent's safe boundary, makes the workspace reflect the desired jj state, injects context, and acknowledges delivery. The reconciliation is either `NativeRewrite` or `ParentAdvance`.
- **`NativeRewrite`** — jj has already evolved a descendant's commits in repository state because an ancestor was rewritten. The intent pins the exact old-base → evolved-base transition, not the descendant's volatile working-copy commit. Kiki does not rebase the descendant again; at a safe boundary it verifies the current descendant still contains the evolved base and normally materializes it with `jj workspace update-stale`.
- **`ParentAdvance`** — a parent bookmark gained a new tip that is not already an ancestor of the following child. Kiki explicitly rebases the child's owned stack onto the exact new parent commit at a safe boundary, then materializes the result.
- **Materialization** — updating a workspace's on-disk files to the working-copy commit already recorded for that workspace in jj repository state. Repository evolution and workspace materialization are separate events.
- **Pause-propagate-resume** — the protocol that interrupts a child agent at the next safe boundary, reconciles and materializes the desired state, injects a context message, and resumes the agent.
- **Core invariant** — kiki does not materialize evolved state or perform an explicit follows rebase in a managed workspace while that workspace's managed agent is mid-edit, and it does not resume from a working tree that may hide unsnapshotted edits. Direct human `jj` operations are an explicit escape hatch and may materialize a stale workspace earlier.
- **Soft pause / Hard escalation** — soft = inject context via PreToolUse hook synthetic tool result. Hard = SIGINT + `--resume` with prepended user message.
- **`WorkspaceProbe`** — a non-materializing check run immediately before reconciliation. It returns a filesystem fingerprint and classifies the workspace as `FreshClean`, `FreshDirty`, `StaleClean`, `StaleDirty`, or `Unknown`; a backend that cannot prove cleanliness returns `Unknown`, which is handled like dirty state before any mutation.
- **`WorkspaceRecovery`** — the hard-paused recovery path for a stale workspace with unsnapshotted or indeterminate edits. It runs outside the source workspace, invokes jj's stale-workspace recovery, enumerates divergent successors, and verifies which result retains the edits before anything resumes.
- **`sync_intent`** — the sole durable record of one ordered cascade reconciliation. It owns kind, base transition, normalized trigger operations, result ids, state (`Detected | Reconciling | Materialized | Delivered | Acknowledged | RecoveryRequired | TopologyDiverged | Superseded`), recovery details, and the byte-stable delivery payload and anchor. UI and delivery queries derive progress from these rows rather than shadow counters.
- **Embedded cascade outbox** — the payload, anchor, transcript id, and delivery timestamps stored on a materialized `sync_intent`. It pins what the agent sees across crash and retry boundaries without creating a second protocol authority. See the [embedded-outbox design note](20-decisions/cascade-outbox.md).

## Transcript

- **Thread transcript** — kiki's local on-disk record of human-authored, agent-authored, and kiki-authored conversational text events per thread, bound to jj change-ids. Local-only (`~/.kiki/repos/<repo_id>/state.db`, never pushed; the source repo's filesystem holds no kiki state). Rows distinguish `author` (`human|agent|kk`) from `direction` (`inbound_to_agent|outbound_from_agent|local_record`) so kiki-authored context is not misattributed to the agent.
- **Local-only-features rule** — the constraint that the thread transcript feeds back into AI-driven kiki features only at local boundaries (`kk reopen` catch-up in v1, agent self-query when same-thread transcript MCP ships). It does NOT feed into features producing externally-published artifacts (`kk publish` PR-drafter, auto-describe, auto-rename).
- **`synthesized=TRUE`** — flag on a transcript row indicating it is kiki-composed content the agent received (cascade injections, reopen catch-up, hard-escalation framing). The flag is what lets `kk reopen` catch-up exclude prior catch-ups from its source query, breaking the recursion that would otherwise compound on every reopen.
- **`anchor_unknown=TRUE`** — flag on a backfilled transcript row whose timestamp predates the available `op_history` and cannot be reliably anchored to a `(change_id, commit_id, op_id)`. Anchor-aware queries skip these rows by default; `--recent` and FTS5 search include them. See [transcript anchoring](20-decisions/transcript-anchoring.md).
- **TranscriptAdapter** — the capture-side trait abstracting per-harness session-record discovery, tailing, projection to `(author, direction, text, dedup_key)`, and offset reporting. v1 adapter: Claude Code JSONL.

## Agent and harness

- **Harness** — an agent runtime kiki spawns and coordinates with (Claude Code in v1; Codex and others deferred). Exposes a `Harness` factory trait + `RunningAgent` instance trait.
- **Runtime agent incarnation** — one kiki-managed harness process, identified by a kiki UUID separately from the harness's resumable conversation/session id. Delivery acknowledgement belongs to the incarnation, so restarting with the same harness session cannot falsely acknowledge output seen only by the prior process.
- **Capabilities** — typed struct returned by a `Harness` describing what it supports (`soft_pause`, `session_resume`, `structured_tool_hooks`, `mcp_client`, `quiescence_detection`). The cascade orchestrator branches on this struct to degrade gracefully.
- **Agent display states** — the four-value human-facing projection (`idle`, `working`, `finished`, `blocked`) of `AgentStatus` plus turn-completion and attention signals, defined in [Harness adapter](15-architecture/harness-adapter.md#agent-display-states). Display-only; the orchestrator branches on `AgentStatus`, never on these.
- **PreToolUse hook** — the Claude Code hook point kiki uses to intercept tool calls for cascade delivery. Implemented by `kk-hook`. Cascade does not use PostToolUse because Claude Code does not fire it for tools blocked by PreToolUse.
- **`ContextMessage`** — `{ kind: MessageKind, text: String, structured: Option<JSON> }` — the byte-stable cascade communication embedded in a materialized intent for delivery to the thread's agent.

## Auth

- **`Admin` credential** — required for global, cross-thread, or destructive daemon mutations, and for sensitive cross-thread reads (transcripts, diffs, the audit log). Stored at `~/.kiki/admin-cred` (mode `0600`). Read by the human CLI / TUI on each invocation.
- **`ThreadScoped<T>` credential** — bound to one thread. Stored at `~/.kiki/repos/<repo_id>/credentials/<thread_id>` (mode `0600`). Read by `kk-hook`, the persistent sidebar, and the same-thread MCP client when MCP ships. The hook's harness config (e.g., the `<workspace>/.claude/settings.json` Claude Code requires in the workspace tree) references that absolute path. Rotated on close and reopen.
- **Repo-summary read scope** — the small expansion of `ThreadScoped<T>` allowing a sidebar process to subscribe to read-only one-line summaries of sibling threads in the same repo. Same-repo only, read-only, summaries only (no diffs, no transcripts). The single cross-thread read a `ThreadScoped<T>` credential can perform.

## State

- **`op_history`** — per-(repo, op_id, workspace_id) cache of `(committed_at, change_id, commit_id, parent_op_id)` populated by the live op-log watcher and by the daemon-restart op-log catch-up. The per-workspace key is load-bearing: jj's op log is repo-shared but `@` is per-workspace. Consulted by the transcript backfill path.
- **`pending_kkd_prepends`** — TTL-bounded sidecar table the JSONL projector consults to recognize kiki-composed `--resume` prepended messages and capture them as `synthesized=TRUE`.

## UI

- **Overlay TUI** — the interactive `kk` UI invoked from inside tmux via `prefix+k` (or by running bare `kk` inside a registered repo). Two-pane: left sidebar with Stack and Activity sections, right content pane (transcript / diff / PR comments). Carries the full action set (spawn, publish, close, interrupt) gated behind confirmation modals for destructive verbs. Dismissed with `q` / `esc`.
- **Persistent sidebar pane** — opt-in left tmux pane (default 32 cols) running a long-running `kk sidebar --thread <id>` ratatui process. Renders the same Stack + Activity sections as the overlay sidebar, restricted to navigation-only keybindings.
- **Shell pane** — opt-out tmux pane (default on) running the user's `$SHELL` at the thread's workspace cwd, laid out alongside the agent pane in the same tmux window (default position: below; configurable to the right). The pane kiki manages — singular — so direct `jj` / `gh` / test invocations live alongside the agent without leaving the thread. Spawned at thread birth, re-ensured idempotently at `kk switch` / `kk reopen`, not auto-respawned after a user-initiated kill in the same continuous attach. Transparent to kkd after spawn — kkd does not track its state or processes. Additional panes the user splits into the session via native tmux are not "shell panes" in kiki's vocabulary; they are just tmux panes and kiki ignores them.
- **Stack-aware collapse** — `kk log`'s default topology rule: the current thread plus its full follows-ancestor chain renders revision-by-revision; siblings, descendants-not-on-the-current-line, and unrelated threads collapse to one-line summaries; trunk renders as its own root.
- **`LogRenderer` / `StatusRenderer`** — pure-function rendering modules in `kiki-core`. `LogRenderer` produces the stack-aware revision view; `StatusRenderer` produces the kk-shaped header used by `kk status` and reused by the sidebar via `--no-jj`. Single source of truth across CLI, overlay TUI, and persistent sidebar pane.

## v2 / future

- **Causal chain** — UUID stamped on each MCP-driven post, used to detect cycles, depth excess, and branch fan-out in inter-thread messaging. See [Roadmap](18-roadmap.md).
