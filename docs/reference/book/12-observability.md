# Observability

kiki should make important state visible without turning every event into an interruption. The system has three observability surfaces:

- command output, for explicit inspection;
- durable lifecycle, cascade, and audit state, for diagnosis;
- OS/tmux notifications, for acceptance-slice events that need attention.

The deferred overlay and sidebar renderers project the same durable state. They never become new authorities — new sources of truth.

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
| Agent silent beyond configured threshold         | Dim status only                                                                             |
| Auto-rename or auto-describe write completed     | No notification; visible in audit once metadata execution ships                             |
| External branch force-push detected              | Warning; explicit reconciliation required once remote observation ships                     |

These defaults are configurable under `[notifications]`.

## Notification transport

In the acceptance slice, the attention channel is an OS-native or tmux notification. (tmux is the terminal multiplexer kiki runs sessions inside.) Once UI surfaces ship, transient in-UI toasts render in the overlay only (see [Interface](10-interface/spec.md)). The persistent sidebar stays a passive state renderer. It reflects lifecycle/cascade glyph changes, but it never hosts toasts or toast actions. If only the sidebar is visible, an attention event still uses the configured OS/tmux transport.

The cross-platform default is the `notify-rust` crate, a Rust library for desktop notifications. On macOS, `notify-rust` requires a signed application bundle, so kiki falls back to shelling out to `osascript -e 'display notification ...'`. The transport is configurable under `[notifications]`:

- `os_provider`: `auto | notify-rust | osascript | tmux | off` (default `auto`).
- `auto` resolves to `notify-rust` on Linux and Windows, and to `osascript` on macOS.
- `tmux` routes notifications to `tmux display-message` on the user's running tmux client. This is useful when the terminal kiki runs in always lives inside tmux.
- `off` disables OS notifications entirely. A currently open overlay may still render its toast after that surface ships.

Per-event behavior (`loud | soft | silent`) is independent of transport. It is configured per-event under `[notifications]`.

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
