# Observability

kiki should make important state visible without turning every event into an interruption. The system has four observability surfaces:

- command output, for explicit inspection;
- durable lifecycle, cascade, and audit state, for diagnosis;
- notifications — OS-native or Herdr toasts — for acceptance-slice events that need attention;
- the Herdr sidebar, where each thread's terminal group appears under the label kiki publishes.

The Herdr sidebar, the deferred overlay, and the optional `ui` pane all project the same durable state. They never become new authorities — new sources of truth.

Audit logs are separate. They answer what happened and who invoked it. Notifications answer what needs the human right now.

## Attention events

The default notification vocabulary is:

| Event                                            | Default                                                                                     |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Agent hit a permission prompt                    | Loud notification; mark the thread blocked until acknowledged                               |
| Cascade reconciliation exposed textual conflicts | Loud notification; mark the cascade `conflicted`                                            |
| Follows parent merged                            | Notification once remote merge observation ships; warning if reconciliation or detach fails |
| Follows parent abandoned                         | Notification and warning; human lifecycle decision required                                 |
| PR check failed                                  | Notification and warning once GitHub polling ships                                          |
| Agent reports goal complete                      | Status mark only                                                                            |
| Agent silent beyond the silence threshold        | Dim status only; never `blocked`. The threshold is a deferred `[notifications]` key         |
| Auto-rename or auto-describe write completed     | No notification; visible in audit once metadata execution ships                             |
| External branch force-push detected              | Warning; explicit reconciliation required once remote observation ships                     |

These defaults are configurable under `[notifications]`.

## Notification transport

In the acceptance slice, the attention channel is an OS-native notification or a Herdr toast. (Herdr is the terminal multiplexer that hosts kiki's terminal groups; see [Terminal runtime](13-architecture/terminal-runtime.md).) Once UI surfaces ship, kiki's own transient toasts render in the overlay only (see [Interface](10-interface/spec.md)). The Herdr sidebar and the optional `ui` pane stay passive state renderers. They reflect lifecycle and cascade changes, but they never host kiki toasts or toast actions. If no overlay is open, an attention event still uses the configured transport.

The cross-platform default is the `notify-rust` crate, a Rust library for desktop notifications. On macOS, `notify-rust` requires a signed application bundle, so kiki falls back to shelling out to `osascript -e 'display notification ...'`. The transport is configurable under `[notifications]`:

- `os_provider`: `auto | notify-rust | osascript | herdr | off` (default `auto`).
- `auto` resolves to `notify-rust` on Linux and to `osascript` on macOS. It never resolves to `herdr`.
- `herdr` shows the notification as a toast in Herdr, through the dedicated server. It is useful when the user's attention lives inside the kiki Herdr server. Herdr's toasts are off by default; kiki's generated Herdr configuration turns them on.
- `off` disables notifications through this transport entirely. A currently open overlay may still render its toast after that surface ships.

The `herdr` provider has these semantics, and kiki does not present it as more:

- **Global.** Herdr sends the toast to every client attached to the kiki server. It cannot target one client or one terminal group. Kiki-originated attention events are about a thread, not about a caller, so a global toast is acceptable; the toast text names the thread.
- **Best-effort.** With no client attached, nothing is shown. Herdr accepts one API toast per second and drops the rest. Its reply is not a display receipt: each attached client applies its own toast policy, so a reply that says the toast was sent does not say any client drew it. These behaviors are read from Herdr's source at the candidate revision and have not been run with attached clients; they are an integration gate, and kiki depends on none of them. Kiki does not queue, retry, or fall back to another provider for a toast that was not shown.
- **Not a record.** A shown toast proves nothing about delivery to a human. The thread's durable state — its blocked mark, cascade state, or projection issue — is what persists, and `kk status`, `kk ls`, and the sidebar projection show it whether or not any toast appeared.
- **Not an action.** A toast carries no approval and no authority. Acting on the event goes through the ordinary command and approval flow.

Per-event behavior (`loud | soft | silent`) is independent of transport. It is configured per-event under `[notifications]`.

## Herdr sidebar projection

Herdr's native sidebar lists the terminal groups on the dedicated server. It is the ambient cross-repo view of threads and takes the place of a kiki-drawn status strip. The user can hide or collapse it, so no attention event relies on it alone. Its default width is 26 columns, adjustable between 18 and 36; the generated configuration sizes its rows and width for kiki's label.

- In the acceptance slice, `kkd` publishes one label per terminal group as its Herdr workspace label: the repo directory name, the thread's display name, and a short provisioning tag. The label is what the sidebar and Herdr's own navigation show. It is the only kiki presentation in the acceptance slice besides notifications.
- In v1.x, `kkd` also publishes metadata tokens that the generated Herdr configuration places in sidebar rows: lifecycle state, cascade state, agent display state, and follows parent. An unacknowledged attention event shows through the agent display state `blocked`. The generated configuration declares those tokens only when this surface ships. A sidebar row layout may hold several rows of tokens. A token key is at most 32 characters of `[A-Za-z0-9_-]` and a value at most 80 characters; kiki's values are short state words, never free text. Kiki publishes its tokens without a time-to-live, so they do not expire on their own.
- Kiki publishes only to a terminal group with a current binding. A remnant container — a Herdr workspace restored without a binding — keeps whatever label Herdr restored and receives no kiki tokens.
- Publishing is one-way. Kiki never reads a label or token back, and nothing a user or another process writes into them changes kiki's state. Any process on the server's socket can rename a Herdr workspace or overwrite a token, and all tokens vanish when the server restarts. `kkd` republishes the label on every display-name change and after every resync, and in v1.x does the same for tokens, so a clobbered or lost value heals.
- Herdr computes its own agent indicator (`idle | working | blocked | done | unknown`) from the screen and the process. It may appear beside kiki's tokens as a hint. It is not kiki's agent display state, and the two can disagree; kiki's commands and tokens are the ones backed by durable state.
- A row in the sidebar is not evidence that a thread is `Active`. After a cold restore the sidebar shows remnant containers under their restored labels while the threads they once hosted are `ProjectionDiverged { reason: TerminalMissing }`. Kiki publishes nothing to those containers; `kk ls` and the attention notification carry the state until a repair plan binds a terminal group again.

The sidebar renders what `kkd` already made durable. An attention event that fails to appear there is a presentation fault, never a lost event.

## CI and PR comments

CI and PR comment observation are deferred v1.x surfaces. CI status changes on a PR are informational. kiki surfaces them once polling ships. It does not automatically attempt fixes.

PR review comments later become visible through `kk thread comments` and an overlay preview. They remain read-only GitHub data. Feeding review comments into an agent as task context is future work.

## Parent lifecycle events

In the acceptance slice, when a parent thread's head advances, kiki creates a `ParentAdvance` reconciliation targeting the exact recorded commit. Rebase and workspace materialization occur only at the child's safe boundary — a point where changing the child's files cannot race its agent.

Once GitHub polling ships, a merged parent creates the same shape of intent, targeting the exact merged default-branch commit. Local reconciliation may complete at the safe boundary. Remote force-push and PR-base mutation, however, remain a named pending plan until the human separately confirms them through the two-phase foreground approval flow. The child detaches only after the approved remote updates succeed.

Deleting or moving only a parent's checkpoint bookmark creates a projection-repair condition. It does not change the pinned follows edge — the recorded parent-child link. If the parent's live head or owned revisions are abandoned, kiki surfaces topology divergence and waits for a human decision. It does not guess a new head or parent.

## Audit

kiki inserts every parseable daemon transport attempt into exactly one authoritative SQLite audit table. Each row records:

- request id;
- timestamp;
- method or path;
- credential and approval identity when identifiable;
- declared scope;
- compact argument summary;
- outcome.

Once a valid target repo is resolved, the authoritative row belongs to that repo database's `audit_log`. Some requests belong to the per-user database's `user_audit_log` instead: bootstrap and approval-presenter enrollment, registry-wide calls, registration before a repo exists, unknown-repo targets, and failures before repo resolution. kiki represents an unidentified caller with null credential/approval ids and a safe presented-identity fingerprint — never raw credential bytes. A request is not mirrored across the two tables.

The table is append-only through the daemon API. Even so, kiki does not claim it is tamper-proof against a process running as the same user (same UID). Reading a thread's own non-sensitive slice uses thread-scoped authority. Repo-wide, cross-thread, or detailed-argument reads require method-bound one-shot human approval. Audit entries are operational records, not transcript entries. A future export command may produce JSONL, but an exported file is never a second authority.

`kk thread audit` renders the redacted current-thread slice. `kk audit log` queries a repo or the user-level unscoped sink. It is approval-gated because it crosses threads or exposes detailed arguments. [Commands](09-commands.md#kk-audit) owns the exact flags and output.
