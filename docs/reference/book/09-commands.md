# Commands

The `kk` CLI is porcelain — a friendly front end — over the thread model. It should make common kiki operations obvious. It does not try to replace `jj`, `gh`, or native Herdr use. Panes, splits, tabs, scrollback, and Herdr's own navigation stay Herdr's; see [Terminal runtime](13-architecture/terminal-runtime.md#native-and-custom-ui).

`kk` does not automatically load reusable Admin authority. Inside a thread, it presents that thread's `ThreadScoped` credential, which works only for that thread. Outside a thread, summary-only commands use a least-privilege registration capability. Riskier operations — mutating another thread, destructive actions, sensitive reads, killing a process, or anything visible outside the machine — enter the one-shot foreground approval flow defined by [Authority](04-authority.md). The command sections below call out the consequential cases, but that chapter is normative.

## Context resolution

Commands that act on a thread figure out which thread you mean in this order:

1. explicit CLI target
2. `KIKI_THREAD_ID` in the environment
3. Herdr pane identity
4. current working directory

Each step is a lookup, not a grant. Whatever step resolves the thread, the CLI then loads only that thread's credential, and `kkd` authorizes the call against that credential (see [Authority](04-authority.md)).

- **Environment.** Kiki sets `KIKI_THREAD_ID` explicitly on every role pane it provisions. A value that names no registered thread is an error; it does not fall through to a later step.
- **Herdr pane identity.** Herdr gives every pane `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, `HERDR_PANE_ID`, and `HERDR_SOCKET_PATH`. `kk` uses them only when `HERDR_SOCKET_PATH` is the socket Herdr derived for kiki's dedicated server. It then asks `kkd` to resolve the Herdr workspace id against the current server instance's terminal bindings. This is how a pane the user split natively resolves its thread: Herdr does not copy a role pane's explicit environment into a split, so such a pane has no `KIKI_THREAD_ID`. A pane on the user's default Herdr server, or an id that matches no current binding, resolves nothing here. A Herdr id recorded under an earlier server instance never resolves a thread. A Herdr id never authorizes anything and never substitutes for a credential: a ref observed under the current server instance that matches a current binding only locates the caller's contextual thread, and the thread's own credential is what authorizes.
- **Working directory.** The canonical current directory is matched against registered jj workspace paths.

If no thread resolves but the command is repo-scoped, the command may fall back to the registered repo. If no registered repo resolves either, commands that need repo state must error with an actionable message.

## Foreground approval flow

Commands never accept a reusable Admin credential from a flag. They never accept a raw approval token from a flag either. When an operation requires `HumanApproval`, `kk`:

1. runs a non-mutating preflight through `BeginApproval`, using its ordinary thread or registration credential;
2. receives and displays the daemon's canonical view of the request: method, target, consequential arguments, plan digest, and expiry;
3. verifies that its stdin/stdout terminal is in the foreground, then confirms or cancels the challenge with its separately enrolled `ApprovalPresenter` credential;
4. retries the exact operation with the issued approval id. The daemon claims that id into one durable operation journal before any external effects happen.

The flow fails closed — it stops rather than guessing — on plan drift, expiry, terminal loss, cancellation, replay, or a non-interactive process. `--yes`, piped confirmation, environment approval, and reusable approval files do not exist. The first installation may use explicit Admin bootstrap, but only to enroll or recover an approval presenter. Operational methods reject Admin and presenter credentials.

## `kk init`

`kk init` opts a git+jj repository into kiki management.

It verifies prerequisites:

- jj is initialized — hard error if not. The message names `jj init --colocate` as the typical fix.
- `kkd` can write the per-repo state directory at `~/.config/kiki/repos/<repo_id>/` — hard error if it cannot. kiki writes nothing into the source repo itself. The only kiki file that may live there is the optional committed `<repo>/.kiki.toml` (the repo-shared config layer), and `kk init` does not create it.

`kk init` does not require `gh`, network access, or GitHub authentication. Those checks happen lazily at `kk publish`. Once publishing ships, `kk doctor --github` is the explicit non-mutating preflight.

`kk init` does **not** verify that any specific harness binary is installed. A harness is the coding-agent program kiki runs inside a thread. The harness contract is pluggable (see [Harness adapter](13-architecture/harness-adapter.md)). v1 ships the `claude-code` and `codex` adapters, but kiki does not refuse registration on a host with no harness installed. The check happens at `kk new` instead: spawning a thread errors if the configured default harness's binary is missing.

The first installation may explicitly use Admin bootstrap to enroll the foreground approval presenter. Registering a repo is then a one-shot approved operation bound to the repo's canonical path and derived repo id. `kk init` never turns bootstrap Admin into ambient CLI authority. The already-registered idempotent path is read-only and needs no new approval.

`kk init` is idempotent in an already-registered repo: running it again changes nothing. It prints a status summary (registration path and time, active and closed thread counts, state.db location) and exits with status 0. Re-registering after `kk repo unregister` is the explicit re-registration path.

`kk init` does not create a starter thread. Thread creation is explicit.

## `kk`

Bare `kk` opens the overlay TUI in `NAVIGATE` mode (see [Interface](10-interface/spec.md)) once the TUI ships. Before the TUI ships, it prints a short command summary and points to `kk ls`. Outside a registered repo, `kk` falls back to the command summary plus `kk ls` even after the TUI ships.

## `kk new`

`kk new` creates a thread as specified in [Threads](03-threads.md).

Thread creation requires one-shot foreground approval. The approval is bound to the resolved base/head, the follows choice, the workspace path, the harness, and a digest of the initial input. This keeps agent-driven spawning out of v1 without granting the CLI reusable Admin authority.

Important flags:

- `--follows <parent>` creates a live follows edge — a link that makes this thread track a parent thread;
- `--no-follow` suppresses contextual following;
- `-m "<prompt>"` supplies an initial prompt, delivered to the harness as the first user turn;
- `--harness <name>` selects a harness for the thread;
- `--harness-arg <arg>` passes harness-specific arguments;
- `--sidebar` / `--no-sidebar` are reserved for the v1.x `ui` role pane, the optional pane that keeps the Stack tree permanently visible (see [Interface](10-interface/spec.md#ui-pane)). They override `[ui] ui_pane` for one thread. Herdr's native sidebar is not controlled by these flags.

The initial prompt can come from `-m` or stdin. If both are supplied, `-m` wins. If neither is supplied, `kk new` proceeds without an initial prompt: the placeholder name becomes `unnamed-<short-hex>` (kk-owned), and the agent starts with no first-turn input. It is fine to spawn a thread before you know what it is about.

`kk new` provisions the thread's terminal group on the dedicated Herdr server whether or not any client is attached. After the thread is `Active`, `kk` requests caller-local focus on the new agent pane under the same contract as [`kk switch`](#kk-switch). That request is navigation, not part of the creation saga: if no caller client resolves or the capability is missing, creation still succeeds, nobody's view moves, and `kk` prints how to reach the thread (`kk attach <thread>`).

Provisioning itself must move no attached client's view. That is the contract for `kk new`, `kk reopen`, a repair restart, and duplicate cleanup alike: the only view that may move is the caller's, through the explicit focus request above. Herdr's create and layout calls default to not taking focus, but this has not yet been run with clients attached. It is an acceptance gate, not an established fact (see [Terminal runtime](13-architecture/terminal-runtime.md#what-exists-what-kiki-builds-what-herdr-must-add)).

When v1.x transcript capture is enabled, the first-turn prompt is projected as `author=human`, `direction=inbound_to_agent`. Thread creation does not depend on that projection.

## `kk switch`

`kk switch <thread>` moves the caller's Herdr client — the terminal view the person who ran the command is attached with — to the target thread's agent pane. It moves that one client and no other. See [Terminal runtime · Caller-local focus](13-architecture/terminal-runtime.md#caller-local-focus) for the mechanism and [Authority](04-authority.md) for why it needs no approval.

The command runs entirely in `kk`, through `TerminalClient`:

1. **Look up the target.** A summary-class read returns the thread's terminal target: the dedicated server's address, the `server_instance_id`, and the current binding's terminal group and agent pane refs. A thread with no current binding has no terminal target. `kk switch` then fails and names the reason: a `Closed` thread points to `kk reopen`; a thread with a `TerminalMissing` issue points to `kk repair`.
2. **Verify the instance.** `kk` connects to the dedicated server and checks that it is the recorded server instance. A mismatch fails the command; a ref from another instance is never used.
3. **Resolve the caller.** The caller is the client id that Herdr supplied to a keybinding or plugin invocation. Otherwise, for a command typed in a pane, it is the foreground client, accepted only when that client is currently showing the pane the command runs in.
4. **Focus.** `kk` asks Herdr to move that client to the target pane.

Outcomes:

- **Focused.** The caller's client now shows the target thread. Other attached clients are unchanged.
- **`NoCallerClient`.** No attached client can be identified as the caller: the command ran from an agent's tool call, a script, a pane nobody is viewing, or a terminal that is not attached to the kiki server. `kk switch` moves no one, exits non-zero, and names `kk attach <thread>` as the way to open a view on that thread.
- **Missing capability.** Caller-local focus requires the Herdr extension `client_targeted_focus`, which the server advertises as a capability. It is a required extension, not an optional one. When the server does not advertise it, `kk switch <thread>` fails with a message that names `client_targeted_focus` and moves no one.

`kk switch --all-clients <thread>` is a separate, explicit operation. It moves every client attached to the kiki server to the target through Herdr's public focus method, and its output says so. It needs neither a resolved caller nor `client_targeted_focus`. Kiki never substitutes it for the caller-local form: not as a fallback, not by configuration, and not from the overlay's `enter`.

`kk switch` performs no terminal mutation. It creates no pane, does not re-create a closed `shell` or `ui` pane, starts no agent, and repairs nothing. It does not mutate daemon focus state either: `kkd` does not own focus, records no current thread, and exposes no mutating `Switch` RPC.

## `kk attach`

`kk attach [<thread>]` opens a Herdr client on kiki's dedicated server in the current terminal. It is how a terminal becomes a view onto kiki's threads. `kk attach` addresses the server itself, by kiki's configuration root (`[paths] herdr_dir`, default `<user_state_dir>/herdr/`) plus the session name; Herdr derives the socket and saved state beneath that root. The user never passes any of it, and the client never touches the user's default Herdr server.

- `kk attach` first asks `kkd` to ensure the dedicated server is running. `kkd` starts it if needed and verifies its version and capabilities. `kk` never starts the server on its own. Then `kk` attaches.
- With `<thread>`, the new client opens on that thread's agent pane. Placement applies to the new client only. If the runtime cannot place one client without moving the others, `kk attach` attaches at Herdr's default location and says so; it never uses the broadcast focus method. A thread with no terminal target is reported the same way as in `kk switch`, and the client still attaches.
- Without `<thread>`, the client opens wherever Herdr places a new client. `kk attach` does not apply context resolution.
- Run from a pane that is already inside the kiki server, `kk attach` refuses to nest a client and points to `kk switch`.
- It requires an interactive terminal.

Attaching is a view, not a lifecycle event. It changes no thread state, starts no agent, and proves nothing about any thread. In particular, when `kk attach` is what starts the server after a reboot or a server stop, Herdr restores layouts as empty containers: every affected thread shows a `TerminalMissing` issue until `kk repair` restarts it, and none is `Active` (see [Terminal runtime](13-architecture/terminal-runtime.md#runtime-changes-are-reconciliation)). Detaching and reattaching a client changes nothing in kiki's state.

## `kk ls`

`kk ls` lists operational threads: `Active` threads plus threads in visible creation, close, failure, and projection-repair states. Every non-Active row includes its lifecycle label spelled out in text; color is never the only signal. `Closed` stays outside the default lifecycle scope.

`kk ls` reads kiki's state, not Herdr's. It works with no client attached and with the dedicated server stopped. A thread whose terminal group, server instance, or agent role is gone is listed as `ProjectionDiverged` with the reason `TerminalMissing`, and a thread with a surviving recorded process and no current binding with the reason `OrphanedProcess`. Neither is ever listed as `Active`, whatever Herdr's sidebar or a restored pane shows.

Repo scope and lifecycle scope are independent:

- Inside a registered repo, the default scope is the current repo.
- Outside a registered repo, the default scope is all registered repos, and the output includes a `repo` column.
- `--all-repos` widens repo scope from the current repo to all registered repos.
- `--all` adds closed threads to the operational states.
- Destroyed threads stay hidden unless an explicit destroyed-thread flag is added.

`--all` must not change repo scope.

## `kk log`

`kk log` is stack-aware revision porcelain: a smaller, thread-aware view of revision history. It keeps its surface smaller than `jj log` and decorates the thread model kiki owns.

- By default it expands the current thread plus its follows ancestors.
- Siblings, descendants off the current line, and unrelated threads collapse to summaries.
- `--no-stack` expands only the current thread.
- `--all` includes closed threads as collapsed lines.
- `--wide` enriches collapsed summaries.
- `-r <revset>` passes through to jj revset selection (jj's query language for picking revisions), disables collapse logic, and errors if combined with `--no-stack`, `--all`, or `--wide`.

Collapsed line format:

- Default: `<status-glyph> <bookmark> [#<pr>] <agent-glyph> "<last-revision-description>"`.
- `--wide`: adds the literal PR state (`draft`, `ready`, `merged`, `closed`), a CI roll-up, agent state with age, and relative last activity.

PR number, PR state, and CI fields appear only after their v1.x integrations ship. The acceptance renderer omits unavailable fields instead of printing placeholders.

`kk log` adopts no other jj-log flags: `-r <revset>` is the only jj-shaped flag in v1. Other `jj log` affordances — patches, templates, reverse order, custom color — remain direct `jj log` usage. This avoids a near-mirror CLI that drifts as jj evolves.

Outside a registered repo, `kk log` errors and points to `kk ls`.

The escape hatch for arbitrary revision selection is `jj` itself. kiki decorates the model it owns; it does not clone every flag of the tools beneath it.

## `kk status`

`kk status` prints a kiki header followed by the literal output of `jj st`.

The two parts are produced differently:

- **The header** comes from `kkd` and uses pinned reads only: every jj read names an exact operation id and ignores the working copy. `kk status --no-jj` prints only this part and never touches the working copy.
- **The body** is an explicit, human-invoked passthrough. The `kk` CLI — never `kkd` — runs `jj st` (and the `--diff` forms) in the caller's own contextual jj workspace, exactly as if the human had typed it. Like any direct jj use it may snapshot the working copy. It is allowed only for an explicit user command against the caller's contextual workspace; it is one of the working-copy commands listed in [Invariants](02-invariants.md). `kk ls`, the watcher, the `ui` pane, overlay polling, and every background renderer never run it.

- `--diff` appends the working-copy patch.
- `--diff --stat` emits a diffstat instead of a patch.
- `--no-jj` suppresses the jj body and emits only the header.

The header identifies the exact live `thread_head_commit_id` and a checkpoint line. The checkpoint line shows three facts:

- the **placed checkpoint** — the bookmark name and `checkpoint_commit_id`, the commit where kiki last explicitly placed it;
- the **tracked expected target** — `bookmark_expected_commit_id`, the commit the bookmark is expected to name now, after any rewrite successors jj carried it to;
- the **relationship** of the tracked expected target to the live head, exactly one of `current`, `behind`, or `diverged`.

The relationship is defined purely on `bookmark_expected_commit_id` and the live head. `current` means they are equal. `behind` means the expected target is an ancestor of the live head on the thread's owned chain; the detailed label is `checkpoint behind head`. `diverged` is every other relation. The placed checkpoint and the tracked expected target differ whenever jj has carried the bookmark to a successor since the last placement; that difference is normal and is not an issue.

Open bookmark issues are reported separately. An open `BookmarkMissing`, `BookmarkMoved`, or `BookmarkConflicted` issue is printed by name beside the relationship, with the observed target or targets, and points to `kk repair`. It does not change the relationship word.

When the repository's operation frontier is unmerged and its heads disagree about the head or the bookmark, the header prints `frontier unmerged` instead of a relationship. Kiki does not merge operation heads to answer a status query.

A trailing checkpoint is normal between explicit checkpoints and must not be mislabeled as a cascade conflict. The header also names any open terminal issue (`TerminalMissing`, `OrphanedProcess`) by reason; it never prints an agent state for a thread that has no ready incarnation. The cascade state indicator is exactly one of `in sync`, `pending`, or `conflicted`; it does not include counts.

## `kk publish`

`kk publish` is a v1.x command that publishes the resolved thread to GitHub through `gh`; see [Publishing](07-publishing.md). It is not part of the coordination acceptance slice. When invoked, it validates `gh` installation, authentication, repository identity, and remote state. It then requires one-shot human approval for the exact publish plan.

Important flags:

- `--no-edit` accepts the generated non-transcript template without opening an editor.
- `-m "<title>"` sets the PR title inline.
- `--ready` opens the PR ready for review instead of as a draft.
- `--downstack` publishes the current thread plus its unpublished descendants, top-down.
- `--refresh` regenerates title/body for an existing PR, and only when explicitly requested.
- `--review-stack` names the default top-down, editor-session-per-PR stack publish; it is an uncommitted alias that may not ship.

The first publishing release generates a deterministic template from explicit input and non-transcript metadata. AI drafting flags are deferred along with the metadata execution loop and are not part of that release.

## `kk close`

`kk close [<thread>]` archives a thread without deleting tracked jj work; see [Threads](03-threads.md#close).

Closing terminates live processes, so it requires one-shot human approval. The approval is bound to the final preflight and becomes invalid if the close plan changes before commit. Non-interactive close is unavailable in v1.

The plan covers the whole terminal group, not only the agent: every role pane and every pane or tab the user added, with the processes found in them. Close freezes and accounts for all of them before it changes anything. Herdr's reply to the close request is not treated as an outcome. Kiki forgets the jj workspace and deletes its directory only after `ProcessSupervisor` verifies that every frozen process identity has exited and that no other process holds the workspace. If that cannot be verified, the files stay and the thread becomes `CloseFailed`.

A `kk close` typed inside the group it closes is itself in the frozen set. That is safe: the approval is claimed and the journal written before the freeze. On an aborted close it resumes with everything else and reports the outcome; on a completed close it ends with the group, and `kk ls` and the journal carry the result.

When `kk close` ran outside the closed terminal group, after a successful close it requests caller-local focus on the parent thread's agent pane when that thread is `Active`, under the same contract as [`kk switch`](#kk-switch). The request is best-effort navigation and is not part of the close journal. Every client that was showing the closed terminal group and was not moved this way is placed by Herdr; kiki does not steer it.

Important flags:

- `--discard-pr` becomes available with the v1.x publishing integration; it also closes the open PR. Plain acceptance-slice `kk close` is local. It never requires `gh` and never changes remote state.

## `kk reopen`

`kk reopen <thread>` restores a closed thread; see [Threads](03-threads.md#reopen). Acceptance-slice reopen restores lifecycle state without reading or sending transcript text.

A closed thread has no live thread credential, and reopen starts a new process incarnation. So reopen requires one-shot foreground approval bound to the target, the restored head, the workspace path, and the harness.

Reopen provisions a new terminal group with fresh role panes; it does not look for or adopt an earlier one. Before provisioning, kiki scans for surviving recorded processes and workspace holders. A survivor raises `OrphanedProcess` and stops the reopen before any agent starts. After the thread is `Active`, `kk` requests caller-local focus on the new agent pane as `kk new` does.

`--catch-up` ships with the v1.x transcript feature. It requests transcript-backed context and triggers the provider-egress consent flow described in [Transcript](06-transcript.md#reopen-catch-up). Because the closed credential is revoked, the daemon releases the preview only to the foreground presenter — after the reopen approval is claimed and before the harness starts. Declining catch-up continues cold unless the user cancels reopen entirely. Without the flag, reopen never reads transcript rows for harness input.

## `kk thread transcript`

`kk thread transcript [<thread>] [<change>]` is a v1.x command that reads the locally stored transcript for a thread. A contextual same-thread read uses `ThreadScoped`. Reading another thread's transcript requires one-shot approval for the exact query and an immutable result snapshot. Changing search, range, or filter arguments requires a new approval. So does refreshing after repository state changes.

Important flags:

- `--search <query>` runs full-text search.
- `--range <from>..<to>` reads a span of changes.
- `--recent <n>` reads the tail of the thread.
- `--include-unanchored` includes rows with unknown change anchors.
- `--include-tombstoned` includes rows for tombstoned or redirected changes.
- `--no-synthesized` hides kiki-authored synthesized rows.

## `kk thread comments`

`kk thread comments [<thread>]` is deferred v1.x work. It lists GitHub PR review comments for the thread's PR.

The first comments surface is read-only. Feeding review comments into agent context is future work.

## `kk thread interrupt`

`kk thread interrupt <thread>` is a v1.x management command. It hard-stops the thread's agent and reframes it through the harness resume path. It is the explicit human escape hatch for a stuck or off-track agent, and it uses the same hard-escalation shape as cascade conflict handling.

Interrupt destroys a process, so it requires one-shot foreground approval — even for the contextual thread.

## `kk thread detach`

`kk thread detach <thread>` removes the thread's live follows edge; see [Cascade](05-cascade.md#detach-and-graph-surgery) for what detach does and does not touch. Before it decides that no reconciliation is pending, it synchronously runs `RefreshToFrontier`, refreshes the parent and child live heads from that pinned view, and creates any transition a lagging watcher had not yet recorded. The user must reconcile that exact transition or explicitly discard it. Only then does detach checkpoint the child's exact live head and delete the edge. `kk thread attach` and `kk thread reparent` are deferred beyond the acceptance slice.

A same-thread detach with no pending reconciliation uses thread-scoped authority. Three cases require one-shot approval bound to that choice: discarding a pending transition, rewriting revisions, or detaching an explicitly targeted different thread.

## `kk thread destroy`

`kk thread destroy <thread>` is a v1.x management command. It permanently removes kiki's thread projections and management state; see [Threads](03-threads.md#destroy). Tracked jj revisions are preserved by default.

Important flags:

- `--keep-log` retains transcript rows for explicit destroyed-thread views.
- `--abandon-revisions` additionally abandons revisions — but only the exact validated linear owned chain named in the approval plan. The plan lists every change/commit id and every affected registered descendant. Ambiguous topology, foreign commits, or plan drift refuses the operation rather than widening the revset.

Destroy requires one-shot foreground approval even when revisions are preserved. `--abandon-revisions` has a distinct method/argument digest and cannot reuse an approval issued for ordinary destroy. A plain yes/no prompt detached from a method-and-target-bound capability is insufficient. Non-interactive destroy is unavailable in v1.

## `kk repair`

`kk repair [<thread>]` is the human-directed recovery surface for a `ProjectionDiverged`, `CreateFailed`, `CloseFailed`, `DestroyFailed`, exhausted-delivery, or other repairable lifecycle condition. The lifecycle and projection chapters own those states; this command owns their shared interaction shape.

An intent whose delivery attempts are exhausted (see [Cascade](05-cascade.md#delivery-protocol)) diagnoses to exactly two named plans. `retry-delivery` re-arms the intent in one journaled transaction: it clears `delivery_exhausted_at`, increments the intent's `delivery_epoch`, and resets the soft-redelivery count. It then permits one fresh bounded `RestartStartup` cycle whose attempts are stamped with and counted under the new epoch. The human runs it after changing whatever made delivery fail, such as upgrading the harness. `discard-delivery` acknowledges the intent without delivery proof, under a one-shot approval bound to the plan, and records the human resolution on the intent. The payload is then never delivered to the agent, and the plan says so before it is approved.

Without an apply flag, `kk repair` is read-only: it reports the observed projections, the durable kiki authority, and zero or more named repair plans. Each plan states which records, workspace paths, bookmarks, terminal groups, processes, or revisions it would change. Kiki may repair provably idempotent projection drift automatically in the background, but it must never silently choose among multiple plausible heads, paths, or topologies.

`--apply <repair-id>` applies exactly the plan emitted by the current diagnosis. If repository state has changed, the id is stale, and kiki diagnoses again instead of adapting the old plan. A same-thread, non-destructive projection repair may use `ThreadScoped`. Any destructive, revision-rewriting, topology-changing, or cross-thread plan requires one-shot approval bound to the repair id and target. `--all` diagnoses all registered threads but does not apply plans.

### Terminal and process plans

The `agent` pane launcher outlives harness incarnations. A harness that exits or crashes under a live launcher is not `TerminalMissing`: the incarnation is retired without acknowledgement, the agent state becomes `Crashed` (displayed as blocked), and the thread's lifecycle is unchanged. A replacement incarnation is a new one-use launch gate awaited by the same accepted launcher, after the orphan scan. It needs no terminal provisioning and no approval beyond what the cascade or explicit restart path already requires. A dead harness under a live launcher is never shown as working.

`TerminalMissing` is raised only when the `agent` role itself ends: the launcher's own process exits, or its binding or server instance is lost. While it is open, boundary delivery, materialization, and lifecycle mutation are blocked, except for the approved plans below.

A `TerminalMissing` issue covers a missing server instance, a missing terminal group, an ended `agent` role, a cold restore, and an observed handoff. The diagnosis says which, with the recorded and observed server instance, binding, and process identities. It offers:

- **Restart the terminal and agent.** Kiki first runs the orphan scan. It then provisions a terminal group for the thread and starts a new incarnation with a fresh credential, launch settings, launch gate, and ready handshake. The `shell` and `ui` role panes are ensured as at creation. The thread returns to `Active` only when the ready handshake commits. A pending delivery reaches the new incarnation through the [cascade protocol](05-cascade.md#delivery-protocol); the plan never marks it delivered. The plan names what it does with each remnant container: reuse it, replacing its first tab with the role layout and leaving any other restored panes as `user` panes, or close it. The restart plan requires one-shot approval.
- **`close-without-terminal`.** The thread goes from `ProjectionDiverged` to `CloseCommit` without a live agent. It is offered when the orphan scan shows that no recorded process identity survives and that every holder of the workspace belongs to a pane in the current runtime snapshot. It is offered after a reboot or server restart without the user first closing restored shells. Its order is fixed:

  1. Preflight runs the same workspace loss inventory as ordinary close and produces the plan, which lists every remnant container whose processes hold the workspace.
  2. Claiming the one-shot approval enters `CloseCommit`.
  3. Each listed remnant container is closed, with verified exit, as a journaled `CloseCommit` step.
  4. Then, in order: the holder scan, the checkpoint, the child steps, the final proof, workspace forget, and directory delete.

- **Destroy**, through the [destroy](03-threads.md#destroy) preflight, once that command ships.

After a cold restore, the panes Herdr restored are **remnant panes**: plain shells the runtime started, usually with their working directory inside the thread's jj workspace. They are accounted terminal members, not orphans, because the current runtime snapshot names each one's pane and root process. Kiki ties a remnant container to a thread only by OS evidence — a pane process that holds that thread's workspace — never by the container's id or label. A reused container grants nothing; the new binding comes only from new launchers and their handshakes.

No plan adopts a restored or surviving pane as the agent, and a thread never returns to `Active` because a pane, a label, or a Herdr agent state reappeared.

An `OrphanedProcess` issue is raised for a recorded process that survives without a current binding, and for a workspace holder that belongs to no pane in the current runtime snapshot. A holder inside a pane — a `user` pane or a remnant pane — is not an orphan; close or the plans above handle it. The issue names each surviving recorded process by its `(pid, start_time)` and lists every other orphaned holder. While it is open, kiki starts no replacement agent in that workspace and deletes nothing. It offers:

- **Terminate and verify.** Under one-shot approval bound to the exact recorded identities, kiki terminates those processes and no others, then verifies their exit and re-runs the holder scan. The issue clears only on verified exit. If exit cannot be verified, the issue stays.
- **Leave blocked.** Nothing is signalled. The thread stays blocked, and the issue stays open until a later diagnosis finds the processes gone.

Kiki never signals a process whose identity it did not record. A holder kiki did not start is reported with its pid and command, and no plan touches it; the human resolves it, and the next diagnosis re-reads the OS.

### Bookmark plans

Kiki tracks the checkpoint bookmark through jj's native rewrite successors without raising an issue (see [Threads](03-threads.md#thread-identity)). A `jj new` or `jj commit` that leaves the bookmark behind the head is the ordinary `behind` relationship. `kk repair` handles only the remaining cases:

- **`BookmarkMissing`** — the bookmark is absent. Plans: restore it by recreating it at the tracked expected target (`bookmark_expected_commit_id`), never at the older placed commit, when that target is still visible; or adopt another exact commit under the adoption rule below.
- **`BookmarkMoved`** — the bookmark names a single commit that is not an accepted successor of the expected target. Plans: restore it to the tracked expected target; or adopt the observed target under the adoption rule.
- **`BookmarkConflicted`** — the bookmark is conflicted or names more than one target. The diagnosis lists every observed target. Plans: set it to the tracked expected target; or set it to exactly one listed target under the adoption rule. Kiki never picks among the targets.

The adoption rule is the one in [Threads](03-threads.md#projection-divergence-and-repair). For an `Active` thread, a commit may be adopted only when it is the live head or lies on the validated owned chain. For a `Closed` thread, adoption must validate the retained owned chain and every follows child, and it advances the archived `thread_head_commit_id` with the checkpoint. Any other target is topology repair and needs a separately approved revision plan.

While a bookmark issue is open, checkpoint, publish, close, and detach are blocked for that thread.

Every applied bookmark plan, restore or adopt, is an explicit placement, alongside creation, publish, close, and detach. It appends a placement-history row, sets both the placed checkpoint and the tracked expected target to the chosen commit, and is verified against the resulting jj operation.

## `kk doctor`

`kk doctor` is a v1.x diagnostic command. `--github` checks `gh` installation, authentication, repository resolution, and the permissions the future publish path needs, without mutating GitHub. GitHub failure never changes registration health and never causes `kk init` to fail.

## `kk privacy consent`

Provider-egress consent — permission to send transcript content to an AI provider — ships with transcript-backed provider features:

- `kk privacy consent list` shows purpose, normalized provider identity, thread scope, disclosure version, grant time, and revocation state for the contextual thread. It never exposes credentials.
- `kk privacy consent grant transcript-mcp` resolves the contextual thread and its managed harness provider. It discloses that same-thread MCP tool results may be sent to that provider, and it requires the enrolled foreground presenter. This pre-grant exists because an agent-facing MCP call cannot open a human prompt.
- `kk privacy consent revoke <purpose> [--provider <identity>]` uses the foreground presenter. It immediately revokes matching remembered grants for the contextual thread. Omitting `--provider` revokes every provider for that thread and purpose, after showing the exact set.

`kk reopen --catch-up` offers approve-once or remember during its actual payload preview; there is no standalone remembered-grant command for `catch_up`. Config, environment, MCP, generic `HumanApproval`, and non-interactive flags cannot grant provider egress. Revocation prevents future sends. It cannot recall content already delivered.

## `kk audit`

`kk thread audit [<thread>]` reads an operational audit slice. For the contextual thread, its default output is non-sensitive and uses `ThreadScoped`: timestamp, method, declared scope, and outcome, with argument and approval details redacted. Three cases require one-shot approval bound to the exact filters and an immutable result snapshot: an explicitly targeted different thread, `--details`, or any query that exposes arguments.

`kk audit log` reads a broader audit authority, so it always requires foreground one-shot approval:

- inside a repo, the default source is that repo's SQLite `audit_log`;
- `--user` selects the per-user `user_audit_log` sink, which records bootstrap, registry-wide, unknown-repo, and pre-resolution attempts;
- `--all-repos` selects every registered repo plus the user sink;
- `--since <time>`, `--method <name>`, and `--outcome <value>` constrain the approved query;
- `--json` changes rendering only, and it is included in the approval digest.

Rows identify the authoritative SQLite source. Kiki does not read or merge an `audit.log` file, and this command is not an export authority. A future explicit export may render rows elsewhere without making that output authoritative.

## `kk config`

The acceptance slice provides `kk config get|show` for the minimal supported configuration; see [Configuration](11-configuration.md). `set|unset|edit` and the full layering surface are v1.x additions.

`kk config get <key>` reports the effective value and the layer it came from. Unknown keys warn rather than error. Structural key changes must tell the user whether they hot-reload, take effect at the next lifecycle event, or require daemon restart.

## Deferred thread management commands

`kk thread attach` and `kk thread reparent` are deferred graph-surgery commands. `kk thread attach` re-establishes a follows link; it is unrelated to [`kk attach`](#kk-attach), which opens a terminal view. Re-pointing a thread at an unambiguously moved workspace is instead a named `kk repair` plan, so recovery does not need a second command protocol.

## Repo registry

`kk repo unregister <path>` removes a repo from the per-user registry. It is the explicit counterpart to `kk init`.

By default, `kk repo unregister` removes two things: the row in `~/.config/kiki/state.db`'s `repos` table, and the centralized state directory at `~/.config/kiki/repos/<repo_id>/` (threads, optional transcript rows, SQLite audit rows, credentials, per-thread error logs, and any workspace-recovery bundles). The action is irreversible — there is no kiki-managed undo, matching the shape of `kk thread destroy` (see [Threads · destroy](03-threads.md#destroy)). It therefore requires a one-shot foreground approval bound to the canonical repo path, the repo id, and whether state is retained. Non-interactive unregister is unavailable in v1. If recovery bundles exist, the command prints their paths in its preflight; `--keep-state` is required to retain them.

`--keep-state` keeps the centralized state directory on disk while still removing the registry row. The preserved directory becomes orphaned bytes. It is useful only to an operator who wants to inspect or copy the contents before deleting them by hand. It does **not** enable any kiki-managed recovery: a future `kk init` at the same canonical path mints a fresh `repo_id` and a fresh state directory, and the preserved directory has no link to the new registration. The flag exists because losing transcripts and audit logs to a mistyped path is a high cost. `--keep-state` is the careful-operator escape hatch, not a recovery contract.

Source-repo moves are not auto-detected. kiki leaves no breadcrumb inside the source tree, so a moved repo looks unregistered to `kk` from the new path. v1 offers two recoveries. Move the source tree back so its path matches the registered `canonical_path`. Or run `kk repo unregister` (with `--keep-state` first if you want to copy state out before re-init) and then `kk init` at the new location, which starts a fresh registration with a new `repo_id`. A move-aware `kk repo relocate` command is not in v1.
