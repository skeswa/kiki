# Commands

The `kk` CLI is porcelain — a friendly front end — over the thread model. It should make common kiki operations obvious. It does not try to replace `jj`, `tmux`, or `gh`.

`kk` does not automatically load reusable Admin authority. Inside a thread, it presents that thread's `ThreadScoped` credential, which works only for that thread. Outside a thread, summary-only commands use a least-privilege registration capability. Riskier operations — mutating another thread, destructive actions, sensitive reads, killing a process, or anything visible outside the machine — enter the one-shot foreground approval flow defined by [Authority](04-authority.md). The command sections below call out the consequential cases, but that chapter is normative.

## Context resolution

Commands that act on a thread figure out which thread you mean in this order:

1. explicit CLI target
2. environment
3. tmux session name
4. current working directory

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
- `--sidebar` / `--no-sidebar` are reserved for the v1.x persistent-sidebar release.

The initial prompt can come from `-m` or stdin. If both are supplied, `-m` wins. If neither is supplied, `kk new` proceeds without an initial prompt: the placeholder name becomes `unnamed-<short-hex>` (kk-owned), and the agent starts with no first-turn input. It is fine to spawn a thread before you know what it is about.

When v1.x transcript capture is enabled, the first-turn prompt is projected as `author=human`, `direction=inbound_to_agent`. Thread creation does not depend on that projection.

## `kk switch`

`kk switch <thread>` switches the tmux client — the terminal view you are attached to — to the target thread's tmux session. It does not mutate daemon focus state; see [Authority](04-authority.md).

## `kk ls`

`kk ls` lists operational threads: `Active` threads plus threads in visible creation, close, failure, and projection-repair states. Every non-Active row includes its lifecycle label spelled out in text; color is never the only signal. `Closed` stays outside the default lifecycle scope.

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

- `--diff` appends the working-copy patch.
- `--diff --stat` emits a diffstat instead of a patch.
- `--no-jj` suppresses the jj body and emits only the header.

The header identifies the exact live `thread_head_commit_id`, the checkpoint bookmark and its commit, and how they relate: `checkpoint current`, `checkpoint behind head`, or `projection diverged`. A trailing checkpoint is normal between explicit checkpoints and must not be mislabeled as a cascade conflict. The cascade state indicator is exactly one of `in sync`, `pending`, or `conflicted`; it does not include counts.

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

Closing terminates a live process, so it requires one-shot human approval. The approval is bound to the final preflight and becomes invalid if the close plan changes before commit. Non-interactive close is unavailable in v1.

Important flags:

- `--discard-pr` becomes available with the v1.x publishing integration; it also closes the open PR. Plain acceptance-slice `kk close` is local. It never requires `gh` and never changes remote state.

## `kk reopen`

`kk reopen <thread>` restores a closed thread; see [Threads](03-threads.md#reopen). Acceptance-slice reopen restores lifecycle state without reading or sending transcript text.

A closed thread has no live thread credential, and reopen starts a new process incarnation. So reopen requires one-shot foreground approval bound to the target, the restored head, the workspace path, and the harness.

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

`kk thread detach <thread>` removes the thread's live follows edge; see [Cascade](05-cascade.md#detach-and-graph-surgery) for what detach does and does not touch. Before it decides that no reconciliation is pending, it synchronously runs `RefreshToFrontier`, refreshes the parent and child live heads from that pinned view, and creates any transition a lagging watcher had not yet recorded. The user must reconcile that exact transition or explicitly discard it. Only then does detach checkpoint the child's exact live head and delete the edge. `attach` and `reparent` are deferred beyond the acceptance slice.

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

Without an apply flag, `kk repair` is read-only: it reports the observed projections, the durable kiki authority, and zero or more named repair plans. Each plan states which records, workspace paths, bookmarks, sessions, or revisions it would change. Kiki may repair provably idempotent projection drift automatically in the background, but it must never silently choose among multiple plausible heads, paths, or topologies.

`--apply <repair-id>` applies exactly the plan emitted by the current diagnosis. If repository state has changed, the id is stale, and kiki diagnoses again instead of adapting the old plan. A same-thread, non-destructive projection repair may use `ThreadScoped`. Any destructive, revision-rewriting, topology-changing, or cross-thread plan requires one-shot approval bound to the repair id and target. `--all` diagnoses all registered threads but does not apply plans.

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

`attach` and `reparent` are deferred graph-surgery commands. Re-pointing a thread at an unambiguously moved workspace is instead a named `kk repair` plan, so recovery does not need a second command protocol.

## Repo registry

`kk repo unregister <path>` removes a repo from the per-user registry. It is the explicit counterpart to `kk init`.

By default, `kk repo unregister` removes two things: the row in `~/.config/kiki/state.db`'s `repos` table, and the centralized state directory at `~/.config/kiki/repos/<repo_id>/` (threads, optional transcript rows, SQLite audit rows, credentials, per-thread error logs, and any workspace-recovery bundles). The action is irreversible — there is no kiki-managed undo, matching the shape of `kk thread destroy` (see [Threads · destroy](03-threads.md#destroy)). It therefore requires a one-shot foreground approval bound to the canonical repo path, the repo id, and whether state is retained. Non-interactive unregister is unavailable in v1. If recovery bundles exist, the command prints their paths in its preflight; `--keep-state` is required to retain them.

`--keep-state` keeps the centralized state directory on disk while still removing the registry row. The preserved directory becomes orphaned bytes. It is useful only to an operator who wants to inspect or copy the contents before deleting them by hand. It does **not** enable any kiki-managed recovery: a future `kk init` at the same canonical path mints a fresh `repo_id` and a fresh state directory, and the preserved directory has no link to the new registration. The flag exists because losing transcripts and audit logs to a mistyped path is a high cost. `--keep-state` is the careful-operator escape hatch, not a recovery contract.

Source-repo moves are not auto-detected. kiki leaves no breadcrumb inside the source tree, so a moved repo looks unregistered to `kk` from the new path. v1 offers two recoveries. Move the source tree back so its path matches the registered `canonical_path`. Or run `kk repo unregister` (with `--keep-state` first if you want to copy state out before re-init) and then `kk init` at the new location, which starts a fresh registration with a new `repo_id`. A move-aware `kk repo relocate` command is not in v1.
