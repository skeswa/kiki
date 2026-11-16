# gRPC service

[`kkd`](../appendix-a-glossary.md#kkd), kiki's background program, exposes a single stable [gRPC](https://grpc.io/) service over a unix socket. gRPC is a [remote procedure call](https://en.wikipedia.org/wiki/Remote_procedure_call) (RPC) system: one program asks another to run a named method and gets a reply. A [unix socket](https://en.wikipedia.org/wiki/Unix_domain_socket) is a file-like connection between programs on one machine.

`kk`, the [pane launcher](../appendix-a-glossary.md#pane-launcher), [`kk-hook`](../appendix-a-glossary.md#kk-hook), the optional `ui` pane, and any future UI are all clients of this service. There is no privileged internal API.

## Transport

- **Socket:** `~/.config/kiki/kkd.sock`, mode `0600`. (Mode `0600` is a [Unix file permission](https://en.wikipedia.org/wiki/File-system_permissions) that lets only the owning user read and write.)
- **Protocol:** gRPC (`tonic`) with a proto3 schema. ([tonic](https://github.com/hyperium/tonic) is a Rust gRPC library. proto3 is the [Protocol Buffers](https://protobuf.dev/) language that describes the messages.)
  - The schema is versioned by field-add discipline: changes add new fields.
  - Server-streaming RPCs are used for event subscriptions. In a server-streaming RPC, the server keeps sending messages on one call.
- **Credentials:** filesystem permissions on the socket are necessary but not sufficient. `AuthEnforcer` validates the credential carried on every call.

## Surfaces

The proto (the Protocol Buffers file) is partitioned by capability class. A [capability](https://en.wikipedia.org/wiki/Capability-based_security) here is the kind of permission a call needs.

- Every operational method declares its `ThreadScoped<T>` scope. (A [`ThreadScoped<T>` credential](../appendix-a-glossary.md#threadscoped-credential) is bound to one thread.)
- Every operational method also declares whether it additionally consumes a `HumanApproval`. That [approval](../appendix-a-glossary.md#human-approval) is bound to the method, the target, and the argument digest (a [hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function) of the arguments).
- Admin is accepted only by bootstrap and approval-presenter enrollment endpoints. It is never ambient operational authority.

| Surface                 | Methods (illustrative)                                                                                                                      | Capability                                                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Bootstrap               | `EnrollApprovalPresenter`, `RecoverApprovalPresenter`                                                                                       | explicit Admin bootstrap                                                                                                        |
| Approval                | `BeginApproval`, `ConfirmApproval`, `CancelApproval`                                                                                        | caller credential begins; enrolled foreground presenter confirms/cancels                                                        |
| Repo registry           | `RegisterRepo`, `UnregisterRepo`, `ListRepos`                                                                                               | summary registration capability; mutations consume `HumanApproval`                                                              |
| Thread lifecycle        | `NewThread`, `Close`, `Reopen`, `Destroy` (v1.x), `DiagnoseRepair`, `ApplyRepair`                                                           | `ThreadScoped<T>` where available; consequential plans consume `HumanApproval`                                                  |
| Thread reads (own)      | `GetThreadState`, `StreamThreadEvents`, `GetCascadeStatus`                                                                                  | `ThreadScoped<T>`                                                                                                               |
| Repo summaries          | `RepoThreadSummaries` (server-streaming)                                                                                                    | least-privilege same-repo summary capability                                                                                    |
| Cascade hook            | `PreToolUseDecision`, `MarkDelivered`, `MarkToolBatchComplete`                                                                              | `ThreadScoped<T>` plus exact incarnation/turn/batch identities                                                                  |
| Terminal server         | `EnsureTerminalServer`                                                                                                                      | `RegistrationScoped<repo_id>` or `ThreadScoped<T>`; no approval; starts no agent                                                |
| Pane launcher           | `ReportLauncherStarted`, `SuperviseLauncher` (bidirectional stream carrying `AwaitLaunchGate`), `ReportHarnessStarted`, `ReportHarnessExit` | `ThreadScoped<T>` plus the provision nonce, one claim per `(terminal_binding_id, role)`, bound to the caller's peer credentials |
| Harness startup         | `ReportHarnessReady`, `AcceptStartupDelivery`                                                                                               | thread scope plus the incarnation id and, for a replacement, its one-use `startup_delivery_id`                                  |
| Transcript (v1.x)       | `ReadTranscript`, `SearchTranscript`                                                                                                        | same-thread `ThreadScoped<T>`; cross-thread read consumes `HumanApproval`                                                       |
| Provider consent (v1.x) | `ListEgressConsents`, `GrantEgressConsent`, `RevokeEgressConsent`                                                                           | reads use caller scope; grant/revoke require the foreground presenter                                                           |
| Publish (v1.x)          | `Publish`                                                                                                                                   | `ThreadScoped<T>` plus a one-shot approval bound to the exact remote plan                                                       |
| Audit                   | `GetAuditLog`, `GetThreadAudit`                                                                                                             | non-sensitive same-thread slice; detailed or cross-thread read consumes `HumanApproval`                                         |
| Config                  | `GetConfig`, later `SetConfig`                                                                                                              | least privilege for reads; consequential scope changes consume approval                                                         |

The rest of this section explains the surfaces that need more than one line.

### Approval

An approval is how a human agrees to a consequential operation. It has separate steps so that the credential that requests an operation is never the one that confirms it.

- **`BeginApproval`** does four things:
  - It authenticates the operation requester.
  - It performs a non-mutating preflight (a check that changes nothing).
  - It stores a pending challenge.
  - It returns the daemon-canonical display plan and digest.
- **`ConfirmApproval`** is accepted only with an enrolled [`ApprovalPresenter`](../appendix-a-glossary.md#approvalpresenter) credential and foreground-terminal proof.
  - It cannot change the stored plan.
  - It is refused when the presenter process is a descendant or session member of any recorded `agent`-role launcher. So a card cannot be confirmed from inside an agent's process tree.
  - That check is cooperative hygiene, not a security boundary.
  - `ConfirmApproval` never performs the operation itself.
- The consequential method later claims the issued approval and its operation journal atomically (in one indivisible step).
- Operational methods reject presenter and Admin credentials.

### Provider-egress consent

[Provider-egress consent](../appendix-a-glossary.md#provider-egress-consent) is the user's permission to send transcript text to a model provider. It is durable privacy policy. It is not reusable operational Admin authority.

- `GrantEgressConsent` uses the foreground presenter to bind an exact `(repo_id, thread_id, provider_identity, purpose, disclosure_version)` tuple. The purpose is `catch_up | transcript_mcp`.
- Agent-facing MCP ([Model Context Protocol](https://modelcontextprotocol.io/)) cannot call grant or revoke methods.
- A missing consent returns `ConsentRequired` without transcript content.

### `RestartStartup` delivery

[`RestartStartup` delivery](../appendix-a-glossary.md#restartstartup-delivery-proof) is distinct from the soft batch barrier. It delivers a saved message to a replacement [incarnation](../appendix-a-glossary.md#incarnation) (a new run of the harness process).

- The launcher is not replaced.
- The replacement incarnation receives the saved payload through the same `agent` launcher's next [launch specification](../appendix-a-glossary.md#launch-specification), with a one-use `startup_delivery_id`.
- `ReportHarnessReady(replacement_incarnation_id, startup_delivery_id, payload_sha256)` proves only that the tagged startup message was installed in the ready process. It does not acknowledge the message.
- The replacement's first `PreToolUseDecision` **must** carry the same tag. At that point `AcceptStartupDelivery` atomically does three things:
  - it consumes the tag;
  - it acknowledges the intent;
  - it admits or blocks that tool according to the next unresolved intent.
- A ready report, process existence, or an untagged boundary is never acceptance evidence.

### Terminal server

`EnsureTerminalServer` asks `kkd` to find or start the [dedicated Herdr server](../appendix-a-glossary.md#dedicated-herdr-server). ([Herdr](https://github.com/herdrdev/herdr) is the terminal program that hosts kiki's terminals.)

- It returns the session name and the server's peer identity `(pid, start_time)`. With these, `kk` can verify that it is talking to the same instance.
- `kk attach` calls it and then uses Herdr's connect-only client mode for that session.
- `kk` never uses a client entry point that would start a server.
- So the server is always started by `kkd`, with the regenerated and validated configuration and the constructed environment described in [Daemon](daemon.md#the-dedicated-herdr-server).
- The method creates no [terminal group](../appendix-a-glossary.md#terminal-group), starts no agent, restarts no thread, and consumes no approval.

### Pane launcher

The pane launcher surface carries the provisioning protocol in [Terminal runtime](terminal-runtime.md#provisioning).

**The nonce.** A [nonce](https://en.wikipedia.org/wiki/Cryptographic_nonce) is a random value made to be used once. (See [provision nonce](../appendix-a-glossary.md#provision-nonce).)

- `kkd` mints one nonce per provision. It rotates the nonce, which gives a new hash, before any re-issued create call.
- The nonce reaches each role launcher through its launch environment. It never travels through argv (the command's argument list), because Herdr saves and exposes launch argv.
- No Herdr API or saved state exposes the launch environment. But a same-UID process (one running as the same user) can read it from the OS process table.
- The nonce is safe only because it admits one claim per role and is bound to the caller's [peer credentials](https://man7.org/linux/man-pages/man7/unix.7.html), within the cooperative model. Peer credentials are what the OS reports about the program on the other end of the socket.
- `kkd` stores only `terminal_bindings.provision_nonce_hash`.
- A launcher's argv carries only the `provision_id` and its role.

**The methods.**

- **`ReportLauncherStarted`** presents the nonce and reports the Herdr workspace, tab, and pane ids from the launcher's environment.
  - `kkd` reads the caller's process identity from the connection's peer credentials, never from the request.
  - `kkd` accepts the report only if both of these hold:
    - the caller's parent process is the current server instance's process; and
    - a fresh per-pane process query on a verified connection shows that the reported pane's root pid is that caller.
  - A report from a launcher whose parent is a previous server instance is refused.
  - In one [transaction](https://en.wikipedia.org/wiki/Database_transaction), `kkd` accepts exactly one launcher for that `(provision_id, role)`, records its identity on `terminal_panes`, and marks the binding `Bound` once its required roles are claimed.
  - The first accepted launcher fixes the binding's Herdr workspace. A launcher reporting from another Herdr workspace is refused.
  - A unique index over `(server_instance_id, group_ref)` for bindings that are not `Ended` keeps two bindings from naming one group.
  - Every refused caller **must** exit without starting anything.
  - For the `shell` and `ui` roles, this role-claim transaction is also what releases the launcher's gate.
- **`SuperviseLauncher`** is the `agent` launcher's long-lived stream to `kkd`. The launcher holds it for its whole life and reopens it after a daemon restart.
  - "The launcher answers" has one meaning everywhere: its OS identity is alive and not stopped, and this stream is open.
  - `AwaitLaunchGate` messages ride the stream.
  - Each gate is one-use. There is one per incarnation, and the same accepted launcher awaits a new one for each replacement incarnation.
  - A second, separate transaction records the incarnation in `agent_sessions` and activates its gate. That transaction requires a `Bound` binding and, for a replacement, a passed harness-remnant check.
  - The stream then delivers the launch specification that `kkd` computed through the harness adapter.
  - After a daemon restart, an activated gate delivers the same specification to the same accepted launcher identity and to no other.
- **`ReportHarnessStarted`** records the harness's identity before the harness runs.
  - The launcher creates the harness child, held before exec (before the harness program starts running), and reports the child's pid.
  - `kkd` verifies through the OS that the process is that launcher's child, records its `(pid, start_time)` on `agent_sessions`, and replies.
  - Only then does the launcher release the child.
  - The launcher reports process facts only.
- **`ReportHarnessExit`** reports the harness child's exit status.
  - It retires the incarnation without acknowledging any delivery and sets [`AgentStatus`](../appendix-a-glossary.md#agentstatus) to `Crashed`.
  - It does not end the `agent` role, and the thread's lifecycle is unchanged.
  - The launcher then re-reads the thread credential file. `kkd` replaced that file's contents atomically, at the same stable path, when the incarnation ended.
  - The launcher then awaits the next gate.
  - `kkd` does not depend on the report. A harness that dies unreported is found by `ProcessSupervisor`.

**The end of a role.** No method reports the end of a role. `kkd` observes it from the claiming launcher's process identity. When that identity ends, or its binding or server instance is lost, the `agent` role ends and the thread raises [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing).

### Harness startup

`ReportHarnessReady` is sent by `kk-hook` from the harness's session-start hook event, not by the launcher.

- It carries the incarnation id and the settings and hook fingerprints.
- It records readiness, not the pid.
- The transaction that commits it re-reads the launcher's OS identity and the open `terminal_servers` row. It fails if either no longer matches.

None of the launcher methods makes a thread `Active`.

- Entering `Active` requires the matching `ReportHarnessReady` handshake.
- Staying `Active` requires a `Bound` binding on the current server instance with a live `agent` role launcher.

### Switch and attach

There is **no** mutating `Switch` RPC. `kkd` does not own focus.

The CLI decomposes switch into two parts:

- a summary-class lookup, which returns the target thread's [terminal target](../appendix-a-glossary.md#terminal-target); and
- a [caller-local focus](../appendix-a-glossary.md#caller-local-focus) request that `kk` makes to the dedicated Herdr server through `TerminalClient`.

The terminal target is the session name, the server's peer identity `(pid, start_time)`, and the current binding's terminal-group and `agent` pane refs.

- `kk` verifies the peer identity of the server it connects to against the target before it requests focus.
- The target is a locator, valid only within that instance. It carries no authority.
- Selecting a thread consumes no human approval and mutates no terminal.
- If the runtime does not advertise [`client_targeted_focus`](../appendix-a-glossary.md#client-targeted-focus), `kk switch` fails naming that capability. `kk switch --all-clients` is the explicit form that moves every attached client.
- `kk attach` uses the same lookup to choose its initial target.

### Repo summaries

`RepoThreadSummaries` returns exactly the non-sensitive fields enumerated in [Authority](../04-authority.md#sensitive-reads).

- Its proto message is shared by `kk ls`, `kk log`, switch and attach lookup, the overlay, and the optional `ui` pane.
- Renderers cannot add fields by querying a more privileged endpoint.
- Herdr's native sidebar is not a client of this service. `kkd` publishes the label and tokens it shows, one way, through `TerminalRuntime`.

(The MCP transcript surface, when it ships, lives on a separate socket — see [Roadmap](../16-roadmap.md).)

## Streaming events

UIs subscribe through server-streaming RPCs rather than polling (asking again and again):

- `StreamThreadEvents(thread_id)` — state transitions, cascade events, and transcript appends for one thread.
- `RepoThreadSummaries(repo_id)` — one-line summaries for sibling threads in the same repo. It is used by `kk ls`, the overlay, and the optional `ui` pane.

On disconnect, clients reconnect and re-subscribe. Events carry a monotonic `seq` (a number that only goes up), so clients can detect gaps.

**Audit.** Audit interception happens before method dispatch. That is, the audit layer sees every call before the call is routed to a method.

- Requests with a resolved repo write exactly one row to that repo database's `audit_log`.
- Bootstrap, registry-wide, unknown-repo, and pre-resolution failures write to `user_audit_log` in the per-user database.
- Logging an unidentified caller uses a safe fingerprint and a null credential id, never raw credential bytes.

## Protocol stability

The proto file is the contract. Proto3 forward-compatibility rules apply:

- never reuse field numbers;
- never narrow types;
- prefer adding new methods over changing existing semantics (what a method means).

Breaking changes require a new service version. The daemon **may** host both versions during a transition.

## Future surfaces

A same-host native GUI can consume the unix-socket gRPC service directly.

Web, remote, and mobile clients **may** reuse the service semantics. But they require a future contract for four things: network transport, peer identity, approval presentation, and revocation. The local socket and filesystem credentials are not presented as a remote-ready security design.
