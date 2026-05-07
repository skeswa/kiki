# Observability

kiki should make important state visible without turning every event into an interruption. The system has three observability surfaces:

- command output for explicit inspection;
- TUI and sidebar state for ambient orientation;
- notifications for events that need attention.

Audit logs are separate. They answer what happened and who invoked it; notifications answer what needs the human now.

## Attention events

The default notification vocabulary is:

Notification defaults:

| Event                                        | Default                                                                                                |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Agent hit a permission prompt                | Loud notification; mark the thread blocked until acknowledged in the TUI                               |
| Cascade rebase produced textual conflicts    | Loud notification; mark the thread `Conflicted`                                                        |
| Follows parent merged                        | Notification on success; warning if detach, rebase, force-push, or PR-base update is pending or failed |
| Follows parent abandoned                     | Notification and warning; human lifecycle decision required                                            |
| PR check failed                              | Notification and warning                                                                               |
| Agent reports goal complete                  | Status mark only                                                                                       |
| Agent silent beyond configured threshold     | Dim status only                                                                                        |
| Auto-rename or auto-describe write completed | No notification; visible in audit                                                                      |
| External branch force-push detected          | Warning; explicit reconciliation required                                                              |

These defaults are configurable under `[notifications]`.

## CI and PR comments

CI status changes on a PR are informational. kiki surfaces them; it does not automatically attempt fixes.

PR review comments are visible through `kk thread comments` and the TUI PR-comments preview. v1 treats them as read-only GitHub data. Feeding review comments into an agent as task context is future work.

## Parent lifecycle events

When a parent thread merges, each following child is rebased onto the repo default branch, force-pushed with `--force-with-lease` if needed, and detached only after local and remote updates succeed.

When a parent bookmark is abandoned externally, kiki surfaces the condition and waits for a human decision. It does not guess a new topology.

## Audit

Every parseable daemon transport attempt is written to the append-only audit log with:

- timestamp;
- method or path;
- credential identity when identifiable;
- declared scope;
- compact argument summary;
- outcome.

`kk audit log` is Admin-only. `kk thread audit` exposes per-thread slices. Audit entries are not transcript entries; they are operational records.
