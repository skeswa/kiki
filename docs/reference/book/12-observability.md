# Observability

Observability means how you find out what kiki is doing and what it needs from you.

kiki should make important state visible without turning every event into an interruption. The system has four observability surfaces:

- command output, for explicit inspection. Every read command can print JSON for a script, and `kk events` prints changes as they happen (see [Observing a headless host](#observing-a-headless-host));
- durable lifecycle, cascade, and audit state, for diagnosis;
- notifications for [acceptance-slice](appendix-a-glossary.md#acceptance-slice) events that need attention: OS-native, Herdr [toasts](appendix-a-glossary.md#toast), or a program you configure;
- the Herdr sidebar, where each thread's [terminal group](appendix-a-glossary.md#terminal-group) appears under the label kiki publishes.

Some terms used here:

- A [thread](appendix-a-glossary.md#thread) is one line of work with its own agent, files, and terminals.
- A terminal group is the set of terminals that belongs to one thread.
- [Herdr](appendix-a-glossary.md#herdr) is the [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer) that hosts those terminals.
- A toast is a small message that pops up briefly and then goes away.
- A [cascade](appendix-a-glossary.md#cascade-reconciliation) is kiki updating a thread after the work it builds on has changed.
- "Durable" state is state kiki has saved to its database, so it survives a restart.

The Herdr sidebar, the deferred [overlay](appendix-a-glossary.md#overlay-tui), and the optional [`ui` pane](appendix-a-glossary.md#ui-role-pane) all project the same durable state. They never become new authorities, meaning new sources of truth.

None of those three views is required. kiki runs [headless](appendix-a-glossary.md#headless): with no Herdr client attached, no overlay, and no desktop session. Anything a view shows is also available from a command. [Observing a headless host](#observing-a-headless-host) says how.

Audit logs are separate. They answer what happened and who invoked it. Notifications answer what needs the human right now.

## Attention events

An [attention event](appendix-a-glossary.md#attention-event) is something that happened in a thread that a person may need to know about. The table lists each event, the tier it ships in, and what kiki does about it by default.

The scope ledger in [Orientation](01-orientation.md) decides which events are in the acceptance slice: a blocked or crashed agent, a conflicted cascade, an exhausted delivery, a followed parent abandoned, a failed lifecycle operation, and a [projection issue](appendix-a-glossary.md#projection-issue). The rest of the vocabulary is v1.x, except where the table says otherwise.

The default notification vocabulary is:

| Event                                            | Tier             | Default level | What kiki does                                                                                                |
| ------------------------------------------------ | ---------------- | ------------- | ------------------------------------------------------------------------------------------------------------- |
| Agent hit a permission prompt                    | acceptance slice | `loud`        | Notification; mark the agent `blocked` until acknowledged. Needs the adapter proof described below            |
| Agent crashed                                    | acceptance slice | `loud`        | Notification; mark the agent `blocked`. `kk repair` offers `restart-agent`                                    |
| Cascade reconciliation exposed textual conflicts | acceptance slice | `loud`        | Notification; mark the cascade `conflicted`                                                                   |
| Lifecycle operation failed                       | acceptance slice | `loud`        | Notification; the thread shows its failed state (`CreateFailed`, `CloseFailed`, a failed reopen or restart)   |
| Projection issue opened                          | acceptance slice | `loud`        | Notification; the thread shows `ProjectionDiverged` with the reason, and points to `kk repair`                |
| Delivery attempts exhausted                      | acceptance slice | `loud`        | Notification; the agent stays hard-paused until `retry-delivery` or `discard-delivery`                        |
| Follows parent abandoned                         | acceptance slice | `loud`        | Notification and warning; the child shows topology divergence, and an explicit lifecycle decision is required |
| Agent reports goal complete                      | acceptance slice | `soft`        | Status mark (`finished`), plus an overlay toast once the overlay ships                                        |
| Follows parent merged                            | v1.x             | `loud`        | Notification once remote merge observation ships; warning if reconciliation or detach fails                   |
| PR check failed                                  | v1.x             | `loud`        | Notification and warning once GitHub polling ships                                                            |
| External branch force-push detected              | v1.x             | `loud`        | Warning; explicit reconciliation required once remote observation ships                                       |
| Agent silent beyond the silence threshold        | v1.x             | `silent`      | Dim status only; never `blocked`. The threshold is a deferred `[notifications]` key                           |
| Auto-rename or auto-describe write completed     | v1.x             | `silent`      | No notification; visible in audit once metadata execution ships                                               |

In the table, a "follows parent" is the thread that another thread [follows](appendix-a-glossary.md#follows) (tracks). A PR is a GitHub [pull request](https://docs.github.com/en/pull-requests).

Some notes on the rows:

- **Projection issue.** One case is quiet. A closed thread's [`CheckpointAbandoned`](appendix-a-glossary.md#checkpointabandoned) issue is common after a squash-merged pull request. It is reported on `kk ls --all` and `kk repair`, and it is not a loud attention event.
- **Exhausted delivery.** See [exhausted intent](appendix-a-glossary.md#exhausted-intent).
- **Follows parent abandoned.** The parent's live head or owned revisions were abandoned locally. Kiki sees this in jj's operation log, so the event needs no remote polling.
- **Acceptance-slice list.** The acceptance-slice rows match the scope ledger in [Orientation](01-orientation.md): a blocked or crashed agent, a conflicted cascade, an exhausted delivery, a followed parent abandoned, a failed lifecycle operation, and a projection issue, plus goal complete at `soft`.
- **Goal complete.** At `soft`, the event is a status mark plus an overlay toast. No OS notification is sent.

These defaults are configurable under `[notifications]`. [Configuration](11-configuration.md#notification-keys) owns the key for each event and the table of what `loud`, `soft`, and `silent` do on each surface.

### Detecting a permission prompt

Kiki cannot see a permission prompt by looking at the terminal. It learns of one only from the harness.

- The harness adapter must declare the capability `attention_events`. The capability names the harness event that fires when the agent waits on a permission prompt.
- The capability counts only after a proof step shows that the named event fires for a real prompt.
- For a harness without that proof, permission-prompt detection is v1.x. Kiki then raises no "permission prompt" event for that harness.
- Crash detection does not depend on this. A harness that exits or crashes under a live launcher still shows `blocked`, on every harness.

See [Harness adapter](13-architecture/harness-adapter.md#capabilities).

### Permission prompts when no human is present

A permission prompt is the harness's own question, such as "may I run this command?". It is not a kiki approval, and the two never mix.

- Kiki never answers a harness's permission prompt. No kiki setting, approval, or [automation policy](appendix-a-glossary.md#automation-policy) rule answers one. The policy approves kiki's own operations only.
- On a host with no human, the operator decides ahead of time what the agent may do. They do that in the harness's own permission settings, so that the agent does not stop to ask.
- If a prompt appears anyway, the agent waits. Where the adapter proves `attention_events`, the "permission prompt" event fires, the agent shows `blocked`, and the event appears in `kk events`. With the [`command` provider](#choosing-a-provider) set, the operator's program is told too.
- A person can answer later. They connect to the host over SSH, run `kk attach`, and answer the prompt in the agent's pane.

## Notification transport

The transport is the channel kiki uses to put a notification in front of you.

In the [acceptance slice](appendix-a-glossary.md#acceptance-slice), the attention channel is an OS-native notification or a Herdr toast. (Herdr is the terminal multiplexer that hosts kiki's terminal groups; see [Terminal runtime](13-architecture/terminal-runtime.md).) Stage 2 of the [build sequence](15-build-sequencing.md) adds a third channel for hosts with no desktop: a program that kiki runs for each event.

Once UI surfaces ship, kiki's own transient [toasts](appendix-a-glossary.md#toast) render in the overlay only (see [Interface](10-interface/spec.md)). The Herdr sidebar and the optional `ui` pane stay passive state renderers:

- They reflect lifecycle and cascade changes.
- They never host kiki toasts or toast actions.

If no overlay is open, a `loud` [attention event](appendix-a-glossary.md#attention-event) still uses the configured transport. A `soft` event then shows only its status mark.

### Choosing a provider

The cross-platform default is the `notify-rust` crate, a [Rust](https://www.rust-lang.org/) library for desktop notifications. On macOS, `notify-rust` requires a [signed](https://en.wikipedia.org/wiki/Code_signing) application bundle. So on macOS kiki falls back to shelling out to `osascript -e 'display notification ...'`. (`osascript` is the macOS command that runs [AppleScript](https://en.wikipedia.org/wiki/AppleScript).)

The transport is configurable under `[notifications]`:

- `os_provider`: `auto | notify-rust | osascript | herdr | command | off` (default `auto`).
- `auto` depends on whether the host has a desktop session: a logged-in graphical session where the operating system can draw a notification.
  - With a desktop session, it resolves to `notify-rust` on Linux and to `osascript` on macOS.
  - With no desktop session, it resolves to `command` when `[notifications] command` is set, and to `off` otherwise.
  - It never resolves to `herdr`.
- `herdr` shows the notification as a toast in Herdr, through the [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) (the one Herdr server kiki runs for itself).
  - It is useful when the user's attention lives inside the kiki Herdr server.
  - Herdr's toasts are off by default; kiki's generated Herdr configuration turns them on.
- `command` runs a program you name in `[notifications] command`, once for each `loud` event.
  - `kkd` writes the event to the program's standard input as JSON.
  - `kkd` gives the program a short time to finish and never retries. A failed run loses that one notification and nothing else: the durable state and `kk events` still carry the event.
  - It is the provider for a host with no desktop. The program can post to a chat channel, page someone, or write to a log collector.
  - Only the user config file can set the program, because the key makes `kkd` run it.
  - A run of the program is not a record and not an action, in the same way a Herdr toast is not.
  - [Configuration](11-configuration.md#the-command-provider) owns the key and its exact rules.
- `off` disables notifications through this transport entirely. A currently open overlay may still render its toast after that surface ships.

### Limits of the `herdr` provider

The `herdr` provider has these semantics, and kiki does not present it as more:

- **Global.** Herdr sends the toast to every client attached to the kiki server. (A client is one terminal window viewing the server.)
  - It cannot target one client or one terminal group.
  - Kiki-originated attention events are about a thread, not about a caller, so a global toast is acceptable.
  - The toast text names the thread.
- **Best-effort.**
  - With no client attached, nothing is shown.
  - Herdr accepts one API toast per second and drops the rest.
  - Its reply is not a display receipt. Each attached client applies its own toast policy, so a reply that says the toast was sent does not say any client drew it.
  - These behaviors are read from Herdr's source at the candidate revision and have not been run with attached clients. They are an integration gate, and kiki depends on none of them.
  - Kiki does not queue, retry, or fall back to another provider for a toast that was not shown.
- **Not a record.** A shown toast proves nothing about delivery to a human.
  - The thread's durable state, its blocked mark, cascade state, or [projection issue](appendix-a-glossary.md#projection-issue), is what persists.
  - `kk status`, `kk ls`, and the sidebar projection show that state whether or not any toast appeared.
- **Not an action.** A toast carries no approval and no authority. Acting on the event goes through the ordinary command and approval flow.

### Per-event behavior

Per-event behavior (`loud | soft | silent`) is independent of transport. It is configured per-event under `[notifications]`.

- `loud` sends the event through the configured transport, shows an overlay toast, and sets the status mark.
- `soft` shows an overlay toast and sets the status mark. It sends nothing through the transport.
- `silent` sets the status mark only.

The status mark is durable state, so no level turns it off. See [Configuration](11-configuration.md#notification-keys) for the full table.

## Observing a headless host

A headless host is a machine where kiki runs with no UI attached, and often with no person present. A build server and a cloud machine reached only over SSH are examples. There is no sidebar to glance at and no desktop to show a notification. Everything kiki knows is still reachable from the command line.

[Commands](09-commands.md) owns each command named here. This section says what each one is for.

- **Read state with `--json`.** Every read command takes `--json`: `kk ls`, `kk status`, `kk log`, `kk thread audit`, `kk automation status`, and the rest. Every other command takes it for its final result, for example `kk new`, `kk close`, and `kk repair`. The flag changes only how the output is drawn. It never changes what the command does. See [Output for scripts](09-commands.md#output-for-scripts).
- **Follow changes with [`kk events`](09-commands.md#kk-events).** It prints the daemon's event stream: state changes, [attention events](appendix-a-glossary.md#attention-event), and cascade progress.
  - `--thread <t>` follows one thread. Without it, the command follows the whole repo.
  - `--follow` keeps the stream open.
  - `--since <seq>` starts after an event the script already saw, so a script that reconnects misses nothing.
  - `--json` prints one JSON object per event.
- **Block until something happens with [`kk wait`](09-commands.md#kk-wait).** `kk wait [<thread>] --for <state>` returns when the thread reaches the named state: `quiescent`, `goal-complete`, `blocked`, `conflicted`, `closed`, or `issue`. `--timeout <dur>` sets how long to wait. `kk wait` ships in Stage 2 of the [build sequence](15-build-sequencing.md); the other commands here are Stage 1.
- **Branch on the exit code.** Every `kk` command ends with one of a small, fixed set of [exit codes](09-commands.md#exit-codes), so a script can tell what happened without reading text:

  | Code | Meaning                                       |
  | ---- | --------------------------------------------- |
  | `0`  | success                                       |
  | `1`  | the operation failed                          |
  | `2`  | usage error                                   |
  | `3`  | an approval was needed and none was available |
  | `4`  | refused by a precondition or a safety proof   |
  | `5`  | the daemon is unreachable or not installed    |
  | `6`  | timeout                                       |

  Code `3` is the one a headless operator meets first. It means no person was there to confirm and no activated [automation policy](appendix-a-glossary.md#automation-policy) rule allowed the plan. The message names the operation, the plan's [risk labels](appendix-a-glossary.md#risk-label), and the reason.

- **Get told with the `command` provider.** A `loud` attention event can run a program of yours. See [Choosing a provider](#choosing-a-provider).

`kk` never asks a question when it has no terminal. Where it would have prompted, it fails and names the flag that answers the question.

A typical script puts these together: `kk new` with a prompt, then `kk wait --for goal-complete`, then `kk status --json` to read the result, then `kk close`. The approvals in that script come from the activated policy; see [Configuration · Automation keys](11-configuration.md#automation-keys).

## Herdr sidebar projection

Herdr's native sidebar lists the [terminal groups](appendix-a-glossary.md#terminal-group) on the [dedicated server](appendix-a-glossary.md#dedicated-herdr-server). Kiki uses it as a display: it publishes a label for each thread there (see [Herdr sidebar projection](appendix-a-glossary.md#herdr-sidebar-projection)).

The sidebar is the ambient cross-repo view of threads and takes the place of a kiki-drawn status strip. The user can hide or collapse it, so no [attention event](appendix-a-glossary.md#attention-event) relies on it alone. Its default width is 26 columns, adjustable between 18 and 36. The generated configuration sizes its rows and width for kiki's label.

### What kiki publishes

- **The label (acceptance slice).** [`kkd`](appendix-a-glossary.md#kkd), kiki's background [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>), publishes one label per terminal group as its [Herdr workspace label](appendix-a-glossary.md#sidebar-label). The label holds the repo directory name, the thread's display name, and a short provisioning tag.
  - The label is what the sidebar and Herdr's own navigation show.
  - It is the only kiki presentation in the acceptance slice besides notifications.
- **Tokens (v1.x).** In v1.x, `kkd` also publishes [metadata tokens](appendix-a-glossary.md#sidebar-token) that the generated Herdr configuration places in sidebar rows. The tokens are lifecycle state, cascade state, [agent display state](appendix-a-glossary.md#agent-display-states), and follows parent.
  - An unacknowledged attention event shows through the agent display state `blocked`.
  - The generated configuration declares those tokens only when this surface ships.
  - A sidebar row layout may hold several rows of tokens.
  - A token key is at most 32 characters of `[A-Za-z0-9_-]`, and a value is at most 80 characters.
  - Kiki's values are short state words, never free text.
  - Kiki publishes its tokens without a [time-to-live](https://en.wikipedia.org/wiki/Time_to_live), so they do not expire on their own.

### Rules for publishing

- **Only to bound groups.** Kiki publishes only to a terminal group with a current [binding](appendix-a-glossary.md#terminal-binding) (kiki's record tying the group to a thread). A [remnant container](appendix-a-glossary.md#remnant-container), a Herdr workspace restored without a binding, keeps whatever label Herdr restored and receives no kiki tokens.
- **One-way.** Publishing is one-way. Kiki never reads a label or token back, and nothing a user or another process writes into them changes kiki's state.
  - Any process on the server's socket can rename a Herdr workspace or overwrite a token.
  - All tokens vanish when the server restarts.
  - `kkd` republishes the label on every display-name change and after every resync. In v1.x it does the same for tokens. So a clobbered or lost value heals.
- **Herdr's own indicator is only a hint.** Herdr computes its own agent indicator (`idle | working | blocked | done | unknown`) from the screen and the process.
  - It may appear beside kiki's tokens as a hint.
  - It is not kiki's agent display state, and the two can disagree.
  - Kiki's commands and tokens are the ones backed by durable state.
- **A row is not proof.** A row in the sidebar is not evidence that a thread is `Active`.
  - After a [cold restore](appendix-a-glossary.md#cold-restore) (Herdr bringing back saved layouts after a restart), the sidebar shows remnant containers under their restored labels. Meanwhile the threads they once hosted are `ProjectionDiverged { reason: TerminalMissing }`.
  - Kiki publishes nothing to those containers.
  - `kk ls` and the attention notification carry the state until a repair plan binds a terminal group again.

The sidebar renders what `kkd` already made durable. An attention event that fails to appear there is a presentation fault, never a lost event.

## CI and PR comments

CI is [continuous integration](https://en.wikipedia.org/wiki/Continuous_integration): the automated checks that run on a [pull request](https://docs.github.com/en/pull-requests) (PR).

CI and PR comment observation are deferred v1.x surfaces. CI status changes on a PR are informational. kiki surfaces them once polling ships. It does not automatically attempt fixes.

PR review comments later become visible through `kk thread comments` and an overlay preview. They remain read-only GitHub data. Feeding review comments into an agent as task context is future work.

## Parent lifecycle events

A thread can [follow](appendix-a-glossary.md#follows) a parent thread, which means it builds on the parent's work. This section says what kiki does when the parent changes.

### The parent's head advances

In the acceptance slice, when a parent thread's head advances, kiki creates a [`ParentAdvance`](appendix-a-glossary.md#parentadvance) reconciliation targeting the exact recorded commit. Rebase and workspace [materialization](appendix-a-glossary.md#materialization) occur only at the child's [safe boundary](appendix-a-glossary.md#safe-boundary): a point where changing the child's files cannot race its agent.

### The parent is merged

Once GitHub polling ships, a merged parent creates the same shape of intent, targeting the exact merged default-branch commit. Local reconciliation may complete at the safe boundary.

Remote force-push and PR-base mutation, however, remain a named pending plan. They wait for a separate one-shot approval of that exact plan. A human gives it through the two-phase [foreground approval flow](09-commands.md#foreground-approval-flow). An activated [automation policy](04-authority.md#automation-policy) rule that covers the plan can give it in the human's place. The child detaches only after the approved remote updates succeed.

### The parent's bookmark or revisions go away

Deleting or moving only a parent's checkpoint [bookmark](appendix-a-glossary.md#bookmark) creates a projection-repair condition. It does not change the pinned [follows edge](appendix-a-glossary.md#follows-edge): the recorded parent-child link.

If the parent's live head or owned revisions are abandoned, kiki surfaces topology divergence and waits for an explicit decision. A person makes it, or an operator's script does through the same commands. It does not guess a new head or parent.

## Audit

The audit record is kiki's log of every attempt to call its daemon that kiki can parse, and what happened to each one.

kiki inserts every parseable daemon transport attempt into exactly one authoritative [SQLite](https://www.sqlite.org/) audit table. Each row records:

- request id;
- timestamp;
- method or path;
- credential and approval identity when identifiable;
- declared scope;
- compact argument summary;
- outcome.

An approval that came from the automation policy is marked as such. A [`PolicyApproval`](appendix-a-glossary.md#policy-approval) is the approval `kkd` issues when an activated policy rule allows a plan, in place of a human's confirmation. Each one writes an audit row that also records:

- the name of the rule that allowed the plan;
- the digest of the active policy;
- the principal: who asked, as the policy saw them;
- the operation;
- the plan's [risk labels](appendix-a-glossary.md#risk-label).

So an audit reader can always tell a human's approval from a rule's, and can tell which rule and which version of the policy it was. [Authority](04-authority.md#policyapproval) owns the capability.

### Which table a row goes to

Once a valid target repo is resolved, the authoritative row belongs to that repo database's `audit_log`. Some requests belong to the per-user database's `user_audit_log` instead:

- bootstrap and approval-presenter enrollment;
- automation policy activation (`kk automation apply`) and revoke;
- automation credential create, rotate, and revoke;
- registry-wide calls;
- registration before a repo exists;
- unknown-repo targets;
- failures before repo resolution.

kiki represents an unidentified caller with null credential/approval ids and a safe presented-identity [fingerprint](https://en.wikipedia.org/wiki/Cryptographic_hash_function), never raw credential bytes. A request is not mirrored across the two tables.

### Reading and trusting the tables

The table is [append-only](https://en.wikipedia.org/wiki/Append-only) through the daemon API: rows can be added but not changed. Even so, kiki does not claim it is tamper-proof against a process running as the same user (same [UID](https://en.wikipedia.org/wiki/User_identifier)).

- Reading a thread's own non-sensitive slice uses thread-scoped authority.
- Repo-wide, cross-thread, or detailed-argument reads require a method-bound one-shot approval: a [human approval](appendix-a-glossary.md#human-approval), or a `PolicyApproval` from an activated rule that lists the `audit-log` or `sensitive-read` operation.

Audit entries are operational records, not transcript entries. A future export command may produce [JSONL](https://jsonlines.org/), but an exported file is never a second authority.

### Commands

`kk thread audit` renders the redacted current-thread slice. `kk audit log` queries a repo or the user-level unscoped sink. It is approval-gated because it crosses threads or exposes detailed arguments. [Commands](09-commands.md#kk-audit) owns the exact flags and output.
