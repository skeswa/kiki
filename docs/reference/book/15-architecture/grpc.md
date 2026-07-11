# gRPC service

`kkd` exposes a single stable gRPC service over a unix socket. `kk`, `kk-hook`, the persistent sidebar, and any future UI are all clients of this service. There is no privileged internal API.

## Transport

- Socket: `~/.kiki/kkd.sock`, mode `0600`.
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
| Harness startup         | `ReportHarnessReady`, `AcceptStartupDelivery`                              | thread scope plus replacement incarnation and one-use `startup_delivery_id`             |
| Transcript (v1.x)       | `ReadTranscript`, `SearchTranscript`                                       | same-thread `ThreadScoped<T>`; cross-thread read consumes `HumanApproval`               |
| Provider consent (v1.x) | `ListEgressConsents`, `GrantEgressConsent`, `RevokeEgressConsent`          | reads use caller scope; grant/revoke require the foreground presenter                   |
| Publish (v1.x)          | `Publish`                                                                  | `ThreadScoped<T>` plus a one-shot approval bound to the exact remote plan               |
| Audit                   | `GetAuditLog`, `GetThreadAudit`                                            | non-sensitive same-thread slice; detailed or cross-thread read consumes `HumanApproval` |
| Config                  | `GetConfig`, later `SetConfig`                                             | least privilege for reads; consequential scope changes consume approval                 |

`BeginApproval` authenticates the operation requester, performs non-mutating preflight, stores a pending challenge, and returns the daemon-canonical display plan and digest. `ConfirmApproval` is accepted only with an enrolled `ApprovalPresenter` credential and foreground-terminal proof; it cannot change the stored plan. The consequential method later claims the issued approval and its operation journal atomically. `ConfirmApproval` never performs the operation itself, and operational methods reject presenter and Admin credentials.

Provider-egress consent is durable privacy policy, not reusable operational Admin authority. `GrantEgressConsent` uses the foreground presenter to bind an exact `(repo_id, thread_id, provider_identity, purpose, disclosure_version)` tuple, where purpose is `catch_up | transcript_mcp`. Agent-facing MCP cannot call grant or revoke methods; a missing consent returns `ConsentRequired` without transcript content.

`RestartStartup` delivery is distinct from the soft batch barrier. The replacement launcher receives the saved payload with a one-use `startup_delivery_id`; `ReportHarnessReady(replacement_incarnation_id, startup_delivery_id, payload_sha256)` proves only that the tagged startup message was installed in the ready process and does not acknowledge it. The replacement's first `PreToolUseDecision` must carry the same tag, at which point `AcceptStartupDelivery` atomically consumes the tag, acknowledges the intent, and admits or blocks that tool according to the next unresolved intent. A ready report, process existence, or untagged boundary is never acceptance evidence.

There is **no** mutating `Switch` RPC. `kkd` does not own focus. The CLI decomposes switch into a summary-class lookup of the target tmux session and `tmux switch-client`; selecting a session consumes no human approval.

`RepoThreadSummaries` returns exactly the non-sensitive fields enumerated in [Authority](../06-authority.md#sensitive-reads). Its proto message is shared by `kk ls`, `kk log`, switch lookup, overlay, and sidebar; renderers cannot add fields by querying a more privileged endpoint.

(The MCP transcript surface, when it ships, lives on a separate socket — see [Roadmap](../18-roadmap.md).)

## Streaming events

UIs subscribe via server-streaming RPCs rather than polling:

- `StreamThreadEvents(thread_id)` — state transitions, cascade events, transcript appends for one thread.
- `RepoThreadSummaries(repo_id)` — one-line summaries for sibling threads in the same repo, used by the sidebar.

On disconnect, clients reconnect and re-subscribe; events carry monotonic `seq` so clients can detect gaps.

Audit interception happens before method dispatch. Requests with a resolved repo write exactly one row to that repo database's `audit_log`; bootstrap, registry-wide, unknown-repo, and pre-resolution failures write to `user_audit_log` in the per-user database. Logging an unidentified caller uses a safe fingerprint and null credential id, never raw credential bytes.

## Protocol stability

The proto file is the contract. Proto3 forward-compatibility rules apply: never reuse field numbers, never narrow types, prefer adding new methods over changing existing semantics. Breaking changes require a new service version; the daemon may host both versions during a transition.

## Future surfaces

A same-host native GUI can consume the unix-socket gRPC service directly. Web, remote, and mobile clients may reuse the service semantics, but require a future network transport, peer identity, approval presentation, and revocation contract; the local socket and filesystem credentials are not presented as a remote-ready security design.
