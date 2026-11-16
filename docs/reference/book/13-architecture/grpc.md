# gRPC service

`kkd` exposes a single stable gRPC service over a unix socket. `kk`, the pane launcher, `kk-hook`, the optional `ui` pane, and any future UI are all clients of this service. There is no privileged internal API.

## Transport

- Socket: `~/.config/kiki/kkd.sock`, mode `0600`.
- Protocol: gRPC (`tonic`) with proto3 schema-versioned via field-add discipline. Server-streaming RPCs are used for event subscriptions.
- Filesystem permissions on the socket are necessary but not sufficient — `AuthEnforcer` validates the credential carried on every call.

## Surfaces

The proto is partitioned by capability class. Every operational method declares its `ThreadScoped<T>` scope and whether it additionally consumes a method, target, and argument-digest-bound `HumanApproval`. Admin is accepted only by bootstrap and approval-presenter enrollment endpoints, never as ambient operational authority.

| Surface                 | Methods (illustrative)                                                     | Capability                                                                              |
| ----------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Bootstrap               | `EnrollApprovalPresenter`, `RecoverApprovalPresenter`                      | explicit Admin bootstrap                                                                |
| Approval                | `BeginApproval`, `ConfirmApproval`, `CancelApproval`                       | caller credential begins; enrolled foreground presenter confirms/cancels                |
| Repo registry           | `RegisterRepo`, `UnregisterRepo`, `ListRepos`                              | summary registration capability; mutations consume `HumanApproval`                      |
| Thread lifecycle        | `NewThread`, `Close`, `Reopen`, `Destroy`, `DiagnoseRepair`, `ApplyRepair` | `ThreadScoped<T>` where available; consequential plans consume `HumanApproval`          |
| Thread reads (own)      | `GetThreadState`, `StreamThreadEvents`, `GetCascadeStatus`                 | `ThreadScoped<T>`                                                                       |
| Repo summaries          | `RepoThreadSummaries` (server-streaming)                                   | least-privilege same-repo summary capability                                            |
| Cascade hook            | `PreToolUseDecision`, `MarkDelivered`, `MarkToolBatchComplete`             | `ThreadScoped<T>` plus exact incarnation/turn/batch identities                          |
| Terminal server         | `EnsureTerminalServer`                                                     | least-privilege registration capability; no approval; starts no agent                   |
| Pane launcher           | `ReportLauncherStarted`, `AwaitLaunchGate`, `ReportHarnessExit`            | `ThreadScoped<T>` plus the provision nonce, one claim per `(terminal_binding_id, role)` |
| Harness startup         | `ReportHarnessReady`, `AcceptStartupDelivery`                              | thread scope plus replacement incarnation and one-use `startup_delivery_id`             |
| Transcript (v1.x)       | `ReadTranscript`, `SearchTranscript`                                       | same-thread `ThreadScoped<T>`; cross-thread read consumes `HumanApproval`               |
| Provider consent (v1.x) | `ListEgressConsents`, `GrantEgressConsent`, `RevokeEgressConsent`          | reads use caller scope; grant/revoke require the foreground presenter                   |
| Publish (v1.x)          | `Publish`                                                                  | `ThreadScoped<T>` plus a one-shot approval bound to the exact remote plan               |
| Audit                   | `GetAuditLog`, `GetThreadAudit`                                            | non-sensitive same-thread slice; detailed or cross-thread read consumes `HumanApproval` |
| Config                  | `GetConfig`, later `SetConfig`                                             | least privilege for reads; consequential scope changes consume approval                 |

`BeginApproval` authenticates the operation requester, performs non-mutating preflight, stores a pending challenge, and returns the daemon-canonical display plan and digest. `ConfirmApproval` is accepted only with an enrolled `ApprovalPresenter` credential and foreground-terminal proof; it cannot change the stored plan. The consequential method later claims the issued approval and its operation journal atomically. `ConfirmApproval` never performs the operation itself, and operational methods reject presenter and Admin credentials.

Provider-egress consent is durable privacy policy, not reusable operational Admin authority. `GrantEgressConsent` uses the foreground presenter to bind an exact `(repo_id, thread_id, provider_identity, purpose, disclosure_version)` tuple, where purpose is `catch_up | transcript_mcp`. Agent-facing MCP cannot call grant or revoke methods; a missing consent returns `ConsentRequired` without transcript content.

`RestartStartup` delivery is distinct from the soft batch barrier. The replacement launcher receives the saved payload with a one-use `startup_delivery_id`; `ReportHarnessReady(replacement_incarnation_id, startup_delivery_id, payload_sha256)` proves only that the tagged startup message was installed in the ready process and does not acknowledge it. The replacement's first `PreToolUseDecision` must carry the same tag, at which point `AcceptStartupDelivery` atomically consumes the tag, acknowledges the intent, and admits or blocks that tool according to the next unresolved intent. A ready report, process existence, or untagged boundary is never acceptance evidence.

`EnsureTerminalServer` asks `kkd` to find or start the dedicated Herdr server and returns its address — kiki's Herdr configuration root and session name — with the current `server_instance_id`. `kk attach` calls it before attaching a client, so that the server is always started by `kkd` with the generated configuration and never by a client with defaults. It creates no terminal group, starts no agent, restarts no thread, and consumes no approval.

The pane launcher surface carries the provisioning protocol in [Terminal runtime](terminal-runtime.md#provisioning). `kkd` mints one nonce per provision. It reaches each role launcher through its launch environment, never through argv, because Herdr saves launch argv. `kkd` stores only `terminal_bindings.provision_nonce_hash`. The nonce admits exactly one claim per `(terminal_binding_id, role)`. A launcher's argv carries only the `provision_id` and its role.

- `ReportLauncherStarted` presents the nonce and reports the Herdr workspace, tab, and pane ids from the launcher's environment. `kkd` reads the caller's process identity from the OS, never from the request, and ties the report to the current `server_instance_id`. In one transaction `kkd` accepts exactly one launcher for that `(provision_id, role)`, records its OS-read process identity on `terminal_panes`, and marks the binding `Bound` once its required roles are claimed. Every other caller presenting that nonce for the role is refused and must exit without starting anything.
- `AwaitLaunchGate` blocks an accepted launcher on a database-backed, one-use gate. "One-use" describes each gate, not the launcher: there is one gate per incarnation, and the same accepted `agent` launcher awaits a new one for each replacement incarnation. A second, separate transaction records the incarnation in `agent_sessions` and activates its gate; that transaction requires a `Bound` binding. The call then returns the launch specification that `kkd` computed through the harness adapter. It is safe to call again after a daemon restart: an activated gate returns the same specification to the same accepted launcher identity and to no other.
- `ReportHarnessExit` reports the harness child's exit status. It retires the incarnation without acknowledging any delivery and sets `AgentStatus` to `Crashed`; it does not end the `agent` role, and the thread's lifecycle is unchanged. The launcher then awaits the next gate. `kkd` does not depend on the report: a harness that dies unreported is found by `ProcessSupervisor`.

No method reports the end of a role. `kkd` observes it from the claiming launcher's process identity: when that identity ends, or its binding or server instance is lost, the `agent` role ends and the thread raises `TerminalMissing`.

None of these methods makes a thread `Active`. Entering `Active` requires the matching `ReportHarnessReady` handshake. Staying `Active` requires a `Bound` binding on the current server instance with a live `agent` role launcher.

There is **no** mutating `Switch` RPC. `kkd` does not own focus. The CLI decomposes switch into a summary-class lookup, which returns the target thread's terminal target, and a caller-local focus request that `kk` makes to the dedicated Herdr server through `TerminalClient`. The terminal target is the server address, the `server_instance_id`, and the current binding's terminal-group and `agent` pane refs; it is a locator, valid only within that instance, and carries no authority. Selecting a thread consumes no human approval and mutates no terminal. If the runtime does not advertise `client_targeted_focus`, `kk switch` fails naming that capability; `kk switch --all-clients` is the explicit form that moves every attached client. `kk attach` uses the same lookup to choose its initial target.

`RepoThreadSummaries` returns exactly the non-sensitive fields enumerated in [Authority](../04-authority.md#sensitive-reads). Its proto message is shared by `kk ls`, `kk log`, switch and attach lookup, the overlay, and the optional `ui` pane; renderers cannot add fields by querying a more privileged endpoint. Herdr's native sidebar is not a client of this service: `kkd` publishes the label and tokens it shows, one way, through `TerminalRuntime`.

(The MCP transcript surface, when it ships, lives on a separate socket — see [Roadmap](../16-roadmap.md).)

## Streaming events

UIs subscribe via server-streaming RPCs rather than polling:

- `StreamThreadEvents(thread_id)` — state transitions, cascade events, transcript appends for one thread.
- `RepoThreadSummaries(repo_id)` — one-line summaries for sibling threads in the same repo, used by `kk ls`, the overlay, and the optional `ui` pane.

On disconnect, clients reconnect and re-subscribe; events carry monotonic `seq` so clients can detect gaps.

Audit interception happens before method dispatch. Requests with a resolved repo write exactly one row to that repo database's `audit_log`; bootstrap, registry-wide, unknown-repo, and pre-resolution failures write to `user_audit_log` in the per-user database. Logging an unidentified caller uses a safe fingerprint and null credential id, never raw credential bytes.

## Protocol stability

The proto file is the contract. Proto3 forward-compatibility rules apply: never reuse field numbers, never narrow types, prefer adding new methods over changing existing semantics. Breaking changes require a new service version; the daemon may host both versions during a transition.

## Future surfaces

A same-host native GUI can consume the unix-socket gRPC service directly. Web, remote, and mobile clients may reuse the service semantics, but require a future network transport, peer identity, approval presentation, and revocation contract; the local socket and filesystem credentials are not presented as a remote-ready security design.
