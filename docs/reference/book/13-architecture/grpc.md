# gRPC service

[`kkd`](../appendix-a-glossary.md#kkd), kiki's background program, exposes a single stable [gRPC](https://grpc.io/) service over a unix socket. gRPC is a [remote procedure call](https://en.wikipedia.org/wiki/Remote_procedure_call) (RPC) system: one program asks another to run a named method and gets a reply. A [unix socket](https://en.wikipedia.org/wiki/Unix_domain_socket) is a file-like connection between programs on one machine.

`kk`, the [pane launcher](../appendix-a-glossary.md#pane-launcher), [`kk-hook`](../appendix-a-glossary.md#kk-hook), the optional `ui` pane, and any future UI are all clients of this service. There is no privileged internal API.

This service and the `kk` commands built on it are the complete surface of kiki. kiki is [headless](../appendix-a-glossary.md#headless): no method needs an attached Herdr client, a popup, a pane, or a desktop session. A script or a continuous-integration (CI) job is an ordinary client. It runs `kk` with an [automation credential](../appendix-a-glossary.md#automation-credential), a credential made for callers that have no human and no thread.

## Transport

- **Socket:** `~/.config/kiki/kkd.sock`, mode `0600`. (Mode `0600` is a [Unix file permission](https://en.wikipedia.org/wiki/File-system_permissions) that lets only the owning user read and write.)
- **Protocol:** gRPC (`tonic`) with a proto3 schema. ([tonic](https://github.com/hyperium/tonic) is a Rust gRPC library. proto3 is the [Protocol Buffers](https://protobuf.dev/) language that describes the messages.)
  - The schema is versioned by field-add discipline: changes add new fields.
  - Server-streaming RPCs are used for event subscriptions. In a server-streaming RPC, the server keeps sending messages on one call.
- **Credentials:** filesystem permissions on the socket are necessary but not sufficient. `AuthEnforcer` validates the credential carried on every call.

## Surfaces

The proto (the Protocol Buffers file) is partitioned by capability class. A [capability](https://en.wikipedia.org/wiki/Capability-based_security) here is the kind of permission a call needs.

- Every operational method declares its `ThreadScoped<T>` scope. (A [`ThreadScoped<T>` credential](../appendix-a-glossary.md#threadscoped-credential) is bound to one thread.)
- Every operational method also declares whether it also consumes a `HumanApproval`. That [approval](../appendix-a-glossary.md#human-approval) is bound to the method, the target, and the argument digest (a [hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function) of the arguments).
- Wherever this chapter says a method consumes a `HumanApproval`, a [`PolicyApproval`](../appendix-a-glossary.md#policy-approval) for the same plan satisfies it. A `PolicyApproval` is the one-shot approval that `kkd` issues when the active [automation policy](../appendix-a-glossary.md#automation-policy) allows the exact plan. [Authority](../04-authority.md#policyapproval) owns this rule and its exceptions. The exceptions are the methods on the Automation and Bootstrap surfaces below: they never accept a `PolicyApproval`.
- A method that consumes a one-shot approval also accepts an `AutomationScoped<name>` caller, which is a caller that presents an automation credential. The approval must be bound to that same credential. An automation credential can look up its own prompt receipt. It can read repo summaries, list repos, stream repo events, read non-sensitive thread state, and call the diagnose methods. It may begin a plan with `BeginApproval` for any registered repo or thread, for `kk init`, and for the user-scoped `replace-terminal-server` plan. It is also accepted by the revoke, status, and list methods of the Automation surface. `ConfirmApproval`, the Bootstrap mutations, and the gated Automation mutations reject an automation credential by itself.
- Admin is accepted only by bootstrap and approval-presenter enrollment endpoints, and by `BeginApproval` for the approval of `kk init`, when no thread or registration credential exists yet. It is also accepted by the two user-scoped `replace-terminal-server` calls, `DiagnoseServerRepair` and the `BeginApproval` for that plan, so they work from any directory. A caller that presents an automation credential uses that credential for `kk init` and for these two calls, not Admin. Admin can begin a presenter challenge on the gated setup methods, or call them directly with the explicit credential file. These are `ChangeDaemonInstallation`, `ApplyAutomationPolicy`, `CreateAutomationCredential`, and `RotateAutomationCredential`, which is how a machine with no human sets up automation. It is never ambient operational authority, and operational methods still reject it. `kkd` checks the [Admin credential](../appendix-a-glossary.md#bootstrap-admin-credential) against its record in the user-level database, `~/.config/kiki/state.db`, because Admin belongs to no one repo.

All local credential classes (thread, registration, automation, and Admin) may call `RevokeAutomationPolicy`, `RevokeAutomationCredential`, and, in v1.x, `RevokeEgressConsent`. These explicit exceptions need no approval, even when no policy is active.

| Surface                 | Methods (illustrative)                                                                                                                      | Capability                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bootstrap               | `EnrollApprovalPresenter`, `RecoverApprovalPresenter`, `ChangeDaemonInstallation`                                                           | Admin for enrollment or recovery; Admin or presenter-confirmed plan for an installation change                                                                                                                    |
| Approval                | `BeginApproval`, `ConfirmApproval`, `CancelApproval`                                                                                        | caller credential begins, and the reply carries a `PolicyDecision` and, when the policy allows the plan, a `PolicyApproval`; enrolled foreground presenter confirms/cancels                                       |
| Automation policy       | `ApplyAutomationPolicy`, `GetAutomationStatus`, `RevokeAutomationPolicy`                                                                    | apply: the Admin bootstrap credential, or a `HumanApproval` confirmed by the enrolled presenter, never a `PolicyApproval`; status and revoke: any valid credential of this user, no approval                      |
| Automation credentials  | `CreateAutomationCredential`, `RotateAutomationCredential`, `RevokeAutomationCredential`, `ListAutomationCredentials`                       | create and rotate: the same gate as apply; revoke and list: any valid credential of this user, no approval                                                                                                        |
| Repo registry           | `RegisterRepo`, `UnregisterRepo`, `ListRepos`                                                                                               | summary registration capability; mutations consume `HumanApproval`                                                                                                                                                |
| Thread lifecycle        | `NewThread`, `Close`, `Reopen`, `Destroy` (v1.x), `DiagnoseRepair`, `ApplyRepair`                                                           | `ThreadScoped<T>` where available; consequential plans consume `HumanApproval`                                                                                                                                    |
| Repo repair             | `DiagnoseRepoRepair`, `ApplyRepoRepair`                                                                                                     | `RegistrationScoped<repo_id>` or `ThreadScoped<T>` to diagnose; apply consumes a one-shot `HumanApproval` with repo scope                                                                                         |
| Follow-up prompts       | `SubmitPrompt`                                                                                                                              | caller credential and one-shot approval for the exact turn                                                                                                                                                        |
| Thread reads (own)      | `GetThreadState`, `StreamThreadEvents`, `GetCascadeStatus`                                                                                  | `ThreadScoped<T>`; `GetThreadState` and `GetCascadeStatus` also accept an automation credential for any registered thread and then return only non-sensitive state                                                |
| Repo summaries          | `RepoThreadSummaries` (server-streaming)                                                                                                    | least-privilege same-repo summary capability, or an automation credential for any registered repo                                                                                                                 |
| Repo events             | `StreamRepoEvents` (server-streaming)                                                                                                       | the same capability as repo summaries; carries summary-class fields only                                                                                                                                          |
| Cascade hook            | `PreToolUseDecision`, `MarkDelivered`, `MarkToolBatchComplete`                                                                              | `ThreadScoped<T>` plus exact incarnation/turn/batch identities                                                                                                                                                    |
| Terminal server         | `EnsureTerminalServer`                                                                                                                      | `RegistrationScoped<repo_id>` or `ThreadScoped<T>`; no approval; starts no agent                                                                                                                                  |
| Terminal server repair  | `DiagnoseServerRepair`, `ApplyServerRepair`                                                                                                 | explicit Admin or an automation credential to diagnose and begin the user-wide plan from any directory; apply consumes a one-shot `HumanApproval` with user scope                                                 |
| Pane launcher           | `ReportLauncherStarted`, `SuperviseLauncher` (bidirectional stream carrying `AwaitLaunchGate`), `ReportHarnessStarted`, `ReportHarnessExit` | `ThreadScoped<T>` plus the provision nonce for the first claim, one claim per `(provision_id, role)`, bound to the caller's peer credentials; after the claim is accepted, the accepted peer process identity     |
| Harness startup         | `ReportHarnessReady`                                                                                                                        | thread scope plus the incarnation id and, for a replacement, its one-use `startup_delivery_id`                                                                                                                    |
| Transcript (v1.x)       | `ReadTranscript`, `SearchTranscript`                                                                                                        | same-thread `ThreadScoped<T>`; cross-thread read consumes `HumanApproval`                                                                                                                                         |
| Provider consent (v1.x) | `ListEgressConsents`, `GrantEgressConsent`, `RevokeEgressConsent`                                                                           | reads use caller scope; revoke needs no approval and accepts any valid credential of this user; grant requires the foreground presenter or a `PolicyApproval` from a rule that names the purpose and the provider |
| Publish (v1.x)          | `Publish`                                                                                                                                   | `ThreadScoped<T>` plus a one-shot approval bound to the exact remote plan                                                                                                                                         |
| Audit                   | `GetAuditLog`, `GetThreadAudit`                                                                                                             | non-sensitive same-thread slice; detailed or cross-thread read consumes `HumanApproval`                                                                                                                           |
| Config                  | `GetConfig`, later `SetConfig`                                                                                                              | least privilege for reads; consequential scope changes consume approval                                                                                                                                           |

The rest of this section explains the surfaces that need more than one line.

### Approval

A one-shot approval is how a consequential operation gets permission to run. It comes from one of two places: a human who confirms the plan, or the active automation policy. It has separate steps so that the credential that requests an operation is never the one that confirms it.

- **`BeginApproval`** does six things:
  - It authenticates the operation requester. The requester is a thread credential, a registration credential, an automation credential, or, for the cases listed above, Admin.
  - It performs an observational preflight. It may persist challenges and audit records. It does not snapshot a workspace, integrate jj heads, or start reconciliation to build a plan. `SnapshotWorkspace` is a separate thread mutation with its own claimed approval and journal. Preflight computes the risk labels.
  - It stores a pending challenge.
  - It evaluates the active automation policy against the caller’s principal, the repo, the operation, and the plan’s risk labels. Consent plans also require the normalized provider identity and current disclosure version. `kkd` evaluates only its stored copy of the policy. It never reads the configuration file here. See [Authority](../04-authority.md#automation-policy).
  - It returns the daemon-canonical display plan, its digest, and its risk labels.
  - It returns a `PolicyDecision`: `Allowed{rule}`, `RequireHuman{rule}`, or `NoMatch`. `rule` is the name of the rule that decided.
- **`Allowed`.** `kkd` issues a `PolicyApproval` in the same reply and in the same [transaction](https://en.wikipedia.org/wiki/Database_transaction) that stores the challenge. No one calls `ConfirmApproval`. The challenge is closed, so no second approval can come from it.
  - A `PolicyApproval` is bound to the same things as a `HumanApproval`: the caller's credential identity, the method, the target repo and thread, the plan digest, and a short expiry. It is single-use.
  - The request field `require_human` tells `kkd` not to issue one. `kk --confirm` sets it. The reply still carries the decision, and the challenge stays open for the presenter.
- **`RequireHuman` or `NoMatch`.** `kkd` issues nothing. The only way forward is `ConfirmApproval`.
  - With a foreground terminal and an eligible requester, `kk` runs the presenter flow.
  - Without one, `kk` fails closed with exit code 3. Its message names the operation, the plan's risk labels, and the reason: no rule matched, or rule `<name>` requires a human. See [exit codes](../09-commands.md#exit-codes).
- A challenge begun with an automation credential is never confirmable by a presenter. If policy gives no approval or the caller sets `require_human`, return the decision and close the challenge without a grant. A person can start again with their ordinary credential.
- **`ConfirmApproval`** is accepted only with an enrolled [`ApprovalPresenter`](../appendix-a-glossary.md#approvalpresenter) credential and foreground-terminal proof.
  - It cannot change the stored plan.
  - It is refused when the presenter process is a descendant or session member of any recorded `agent`-role launcher. So a card cannot be confirmed from inside an agent's process tree. An agent gets authority only through a policy rule whose principal matches its thread credential, including the wildcard `*`.
  - That check is cooperative hygiene, not a security boundary.
  - It never accepts an automation credential.
  - `ConfirmApproval` never performs the operation itself.
- The consequential method later claims the issued approval and its operation journal atomically (in one indivisible step). This step is the same for both kinds of approval.
- The policy replaces only the confirm step. Preflight, the plan digest, the drift and expiry checks, single use, the journal, and every safety proof run the same way. A policy can never make a plan run that a safety proof refuses.
- Operational methods reject presenter and Admin credentials.
- There is no other source of approval. No request field, environment variable, or reusable token approves a plan.

**Methods the policy never approves.** `kkd` does not evaluate the policy for `ApplyAutomationPolicy`, `CreateAutomationCredential`, `RotateAutomationCredential`, or `ChangeDaemonInstallation`. A `BeginApproval` for one of them always returns `NoMatch`. Those four methods, `EnrollApprovalPresenter`, and `RecoverApprovalPresenter` each refuse a `PolicyApproval`.

### Changing the daemon installation

The first install runs locally before there is a service to call. On rerun, the installed daemon checks the user installation journal before treating a matching definition as an identical install. Resume any pending authorized change and verify the requested daemon has answered after reload. With no pending change, an identical install starts the installed service if needed. Neither opens an approval challenge.

For a change, `ChangeDaemonInstallation` takes a request id and the expected and proposed service-definition digests. The local client derives the proposed definition from the installed kiki template. The running daemon independently derives it from that template and checks both digests under the installation lock. Clients cannot supply a custom service command. The plan names the service, executable, arguments, and both digests. A caller presents Admin explicitly or consumes a human approval for that plan. For the presenter route, a thread, registration, or explicit bootstrap credential can begin the user-scoped challenge.

The daemon records the plan and its authority before replacing the definition or asking the service manager to reload it. It serializes changes. After restart it inspects the installed definition and running service, completes missing steps, and reports success only once the requested daemon answers. An unexpected third definition stops recovery for inspection. A retry of the same request returns its recorded result. A pending change to the same definition resumes even if the earlier client exited.

### Automation

The Automation surface manages the automation policy and the automation credentials. [Commands](../09-commands.md#kk-automation) owns the `kk automation` commands that call it. [Configuration](../11-configuration.md#automation-keys) owns the `[automation]` keys.

**The gate.** `ApplyAutomationPolicy`, `CreateAutomationCredential`, and `RotateAutomationCredential` add authority. Each needs one of two things:

- **A presenter confirmation.** `kk` calls `BeginApproval` for the method with a thread, registration, or Admin credential. The stored plan is the full canonical policy and its difference from the active one, or the credential's name. The enrolled presenter confirms it at a foreground terminal, and the method consumes the resulting `HumanApproval`. The challenge and the approval live in the user database, because these methods have no repository target.
- **The Admin bootstrap credential.** `kk` reads it from the file named by `--admin-credential-file` and presents it on the call. There is no challenge. This is the path for a machine that never has a human. `kk` never loads Admin by itself.

The methods:

- **`ApplyAutomationPolicy`** carries the `[automation]` tables that `kk` read from the user configuration file.
  - `kkd` canonicalizes them into one fixed form and computes the policy digest.
  - In one transaction, `kkd` marks the active `automation_policies` row superseded, inserts the new row, and swaps the policy it evaluates.
  - Editing the file changes nothing until this method succeeds. See [Authority](../04-authority.md#activating-a-policy).
- **`GetAutomationStatus`** returns the active policy's canonical text, its digest, who activated it (`Presenter` or `Admin`), and when.
  - `kk` may send the file's current `[automation]` tables with the request. `kkd` canonicalizes them and reports whether their digest differs from the active one.
  - It changes nothing.
- **`RevokeAutomationPolicy`** marks the active row superseded and inserts none. Afterward every `PolicyDecision` is `NoMatch`. A `PolicyApproval` that was already issued stays valid until its short expiry.
- **`CreateAutomationCredential(name)`** makes a new secret. `kkd` stores only its hash in `automation_credentials` and writes the secret to `~/.config/kiki/automation/<name>.cred` with mode `0600`.
- **`RotateAutomationCredential(name)`** replaces the secret and the file. The old secret stops working at once.
- **`RevokeAutomationCredential(name)`** marks the row revoked. Approvals bound to that credential can no longer be claimed.
- **`ListAutomationCredentials`** returns names and timestamps, never a secret or a hash.

The revoke methods only remove authority. So they need no approval, and they accept any valid credential of this user: thread, registration, automation, or Admin. The status and list methods accept the same credentials.

Every call on this surface writes a row to `user_audit_log`.

### Repair

Repair has a diagnose step and an apply step at each of three scopes. Diagnose changes nothing and returns the offered [repair plans](../appendix-a-glossary.md#repair-plan), each with a plan id. Apply runs one plan by its id. [Commands](../09-commands.md) owns the table of issues, plans, and approvals.

| Scope                      | Methods                                     | CLI                                                          | Plans                                                                                                                                                                                                                                                                                                                                                   |
| -------------------------- | ------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| One thread                 | `DiagnoseRepair`, `ApplyRepair`             | `kk repair`, `kk repair --apply <plan-id>`                   | every per-thread plan, such as [`restart-terminal`](../appendix-a-glossary.md#restart-terminal), [`close-without-terminal`](../appendix-a-glossary.md#close-without-terminal), [`terminate-orphans`](../appendix-a-glossary.md#terminate-orphans), [`cleanup-failed-restart`](../appendix-a-glossary.md#cleanup-failed-restart), and the bookmark plans |
| One repo                   | `DiagnoseRepoRepair`, `ApplyRepoRepair`     | `kk repair --repo`, `kk repair --repo --apply <plan-id>`     | repo-level plans; in v1 that is [`reanchor-history`](../appendix-a-glossary.md#reanchor-history)                                                                                                                                                                                                                                                        |
| The user's terminal server | `DiagnoseServerRepair`, `ApplyServerRepair` | `kk repair --server`, `kk repair --server --apply <plan-id>` | [`replace-terminal-server`](../appendix-a-glossary.md#replace-terminal-server)                                                                                                                                                                                                                                                                          |

- `kk repair --all` calls `DiagnoseRepair` for every thread in the caller's repo. It never crosses repos.
- `ApplyRepoRepair` needs a one-shot approval with repo scope. The repo is the caller's repo.
- `DiagnoseServerRepair` returns the `replace-terminal-server` plan. The plan lists every thread and every process that the replacement stops.
- `ApplyServerRepair` needs a one-shot approval. The plan is user-scoped, not thread-scoped, so no thread credential can authorize it alone. It stops the old server with [verified exit](../appendix-a-glossary.md#verified-exit) and then starts a new one.
- Every apply method claims its approval together with its operation journal, like any other consequential method.
- The three diagnose methods also accept an automation credential, for any registered repo or thread. They change nothing. An apply from that credential needs a `PolicyApproval`. For a plan that needs a one-shot approval in every context, the rule must cover `repair:<plan-name>` by name, `repair:*`, or `*`. For a plan that needs none in the thread's own context, such as `restart-agent`, the rule must cover `thread-op` by name or `*`. See [Authority](../04-authority.md#the-thread-op-operation).
- A repair plan never asks a question during apply. A choice a plan needs, such as the target of a bookmark plan, is an argument of the apply call and part of the plan digest.

For a `RecoveryRequired` intent, `DiagnoseRepair` returns the plan id, intent id, operation id, and candidate commit ids with their edit-preservation results. Omit file paths and contents from this diagnosis. `BeginApproval` binds the selected full commit id and recovery-bundle fingerprint into the plan. `ApplyRepair` rechecks the candidate set, selected commit, and workspace under the reconciliation lock and the repo jj lock before materializing. Drift requires fresh diagnosis and approval.

### Follow-up prompts

`SubmitPrompt(thread_id, incarnation_id, request_id, text, approval)` claims the approved plan and saves the request before handing text to the harness. Check before claiming the approval, then serialize submission against lifecycle work. Under the thread lock, reject an open lifecycle operation, repair, active materialization, hard pause, or incomplete tool batch. Admit a ready user turn when the cascade is waiting for the next hook. Submission itself changes no intent or barrier. The adapter must check readiness and submit as one harness operation so an intervening permission prompt cannot receive the text. The reply carries the outcome described by [`kk prompt`](../09-commands.md#kk-prompt).

On retry, authenticate the same caller before releasing any recorded result. Check for request-id reuse across all credential generations. A different requester gets a generic refusal without a receipt or another send. The CLI checks for a prior submission by caller, request id, thread and text digest before starting a new preflight. This lookup passes no incarnation id or approval and can only read the matching receipt for the authenticated caller. Return an existing receipt even if the thread has since restarted. If the record is missing, report that the request is new. Only a subsequent approved submission may send it. Reject reuse with different arguments. A replay needs no new approval and cannot submit a second turn. If acceptance is uncertain, look up the receipt in the original incarnation’s harness record. Never infer acceptance from screen contents, a hook acknowledgement, or the current incarnation’s status.

### Cascade hook

[`kk-hook`](../appendix-a-glossary.md#kk-hook) is a stateless client. Each run makes one call and exits. There is no separate hook-side process.

- `kkd` owns the [`PassThrough`](../appendix-a-glossary.md#batch-admission) cache. It lives in `kkd`'s memory, keyed by incarnation and batch. So every `PreToolUseDecision` in one [tool batch](../appendix-a-glossary.md#tool-batch) gets the same answer from `kkd` itself.
- After a `kkd` restart the cache is gone. The first `PreToolUseDecision` from an incarnation that was already running before this `kkd` start is an unknown in-flight batch, unless the hook payload proves it is the first call of a new [model turn](../appendix-a-glossary.md#model-turn).
- `kkd`, not the hook, performs the [hard pause](../appendix-a-glossary.md#hard-pause) and the replacement that follow. No RPC lets a client ask for either.
- `hook_connect` bounds connection and admission. On expiry the hook denies the call and records the gap. Only an affirmative `PassThrough` for this exact batch permits the tool.

### Provider-egress consent

[Provider-egress consent](../appendix-a-glossary.md#provider-egress-consent) is the user's permission to send transcript text to a model provider. It is durable privacy policy. It is not reusable operational Admin authority.

- `GrantEgressConsent` uses the foreground presenter to bind an exact `(repo_id, thread_id, provider_identity, purpose, disclosure_version)` tuple. The purpose is `catch_up | transcript_mcp`.
- A `PolicyApproval` can stand in for the presenter only when the rule that allowed it names the operation `consent:<purpose>` and lists the normalized provider identity. A `*` in a rule's operations never matches a consent operation. A plain configuration key still grants no consent. See [Authority](../04-authority.md#automation-policy).
- `RevokeEgressConsent` only takes permission away. It needs no approval, and it accepts any valid credential of this user.
- Agent-facing MCP ([Model Context Protocol](https://modelcontextprotocol.io/)) cannot call grant or revoke methods.
- A missing consent returns `ConsentRequired` without transcript content.

### `RestartStartup` delivery

[`RestartStartup` delivery](../appendix-a-glossary.md#restartstartup-delivery-proof) is distinct from the soft batch barrier. It delivers a saved message to a replacement [incarnation](../appendix-a-glossary.md#incarnation) (a new run of the harness process).

- The launcher is not replaced.
- The replacement incarnation receives the saved payload through the same `agent` launcher's next [launch specification](../appendix-a-glossary.md#launch-specification), with a one-use `startup_delivery_id`. The launch specification carries that id in the launcher environment, and the session-start hook reports it.
- `ReportHarnessReady(replacement_incarnation_id, startup_delivery_id, payload_sha256)` proves only that the tagged startup message was installed in the ready process. It does not acknowledge the message.
- The acknowledgement is the first `PreToolUseDecision` of a model turn in that same replacement incarnation. `kkd` matches the call to the tag by its incarnation id.
- Accepting the startup delivery is a side effect of that first `PreToolUseDecision`. It is not a separate method. In one transaction, `kkd` does three things:
  - it consumes the tag;
  - it acknowledges the intent;
  - it admits or blocks that tool according to the next unresolved intent.
- A ready report, process existence, or a call from any other incarnation is never acceptance evidence.

### Terminal server

`EnsureTerminalServer` asks `kkd` to find or start the [dedicated Herdr server](../appendix-a-glossary.md#dedicated-herdr-server). ([Herdr](https://github.com/herdrdev/herdr) is the terminal program that hosts kiki's terminals.)

- It returns the session name and the server's peer identity `(pid, start_time)`. With these, `kk` can verify that it is talking to the same instance.
- `kk attach` calls it and then uses Herdr's connect-only client mode for that session.
- The server it returns may have no attached client at all. No method in this service needs one.
- `kk` never uses a client entry point that would start a server.
- So the server is always started by `kkd`, with the regenerated and validated configuration and the constructed environment described in [Daemon](daemon.md#the-dedicated-herdr-server).
- The method creates no [terminal group](../appendix-a-glossary.md#terminal-group), starts no agent, restarts no thread, and consumes no approval.

### Pane launcher

The pane launcher surface carries the provisioning protocol in [Terminal runtime](terminal-runtime.md#provisioning).

**The nonce.** A [nonce](https://en.wikipedia.org/wiki/Cryptographic_nonce) is a secret random value with a strictly limited use. Here it admits one claim per role. (See [provision nonce](../appendix-a-glossary.md#provision-nonce).)

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
  - Each report is handled in one [transaction](https://en.wikipedia.org/wiki/Database_transaction) when it arrives. There is no table of pending reports. The transaction accepts that launcher for `(provision_id, role)` and records its identity on `terminal_panes`. Exactly one launcher is accepted for each `(provision_id, role)`.
  - The binding becomes `Bound` in the transaction that accepts the `agent` claim. `agent` is the only [required role](../appendix-a-glossary.md#required-role).
  - A `shell` or `ui` launcher that does not report within `[timeouts] launcher_report` (default `10s`) is recorded as absent. That raises a warning. It does not fail provisioning.
  - The report is idempotent, which means a repeat is safe. A repeat of an accepted report from the same peer process identity `(pid, start_time)` gets the same answer again.
  - A different process that presents for a role already claimed is refused.
  - The first accepted launcher fixes the binding's Herdr workspace. A launcher reporting from another Herdr workspace is refused.
  - A unique index over `(server_instance_id, group_ref)` for bindings that are not `Ended` keeps two bindings from naming one group.
  - Every refused caller **must** exit without starting anything.
  - For the `shell` and `ui` roles, this role-claim transaction is also what releases the launcher's gate.
  - After its claim is accepted, the launcher's later calls are authenticated by the accepted peer process identity.
- **`SuperviseLauncher`** is the `agent` launcher's long-lived stream to `kkd`. The launcher holds it for its whole life and reopens it after a daemon restart.
  - "The launcher answers" has one meaning everywhere: its OS identity is alive and not stopped, and this stream is open.
  - The stream is authenticated by the accepted peer process identity. Rotating the thread credential when an incarnation ends does not close it.
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
  - A repeat from the same launcher, for the same incarnation and the same child identity, is accepted and changes nothing.
  - A launcher that already holds a recorded child ignores a gate specification that is delivered again. It reports the existing child.
- **`ReportHarnessExit`** reports the harness child's exit status.
  - It retires the incarnation without acknowledging any delivery and sets [`AgentStatus`](../appendix-a-glossary.md#agentstatus) to `Crashed`.
  - It does not end the `agent` role, and the thread's lifecycle is unchanged.
  - `kkd` authenticates the report by the launcher's accepted peer process identity. So the credential rotation described next does not reject it.
  - The launcher then re-reads the thread credential file. `kkd` replaced that file's contents atomically, at the same stable path, when the incarnation ended.
  - The launcher then awaits the next gate.
  - `kkd` does not depend on the report. A harness that dies unreported is found by `ProcessSupervisor`.

**The end of a role.** No method reports the end of a role. `kkd` observes it from the claiming launcher's process identity. When that identity ends, or its binding or server instance is lost, the `agent` role ends and the thread raises [`TerminalMissing`](../appendix-a-glossary.md#terminalmissing).

### Harness startup

`ReportHarnessReady` is sent by `kk-hook` from the harness's session-start hook event, not by the launcher.

- It carries the incarnation id and the settings and hook fingerprints. For a replacement started by `RestartStartup`, it also carries the `startup_delivery_id`.
- `kkd` waits for it up to `[timeouts] ready_handshake` (default `60s`) from launch. On expiry a creation becomes `CreateFailed`, and a restart takes its own failure state.
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
- A caller with no attached Herdr client, such as a script, resolves `NoCallerClient`. `kk switch` then moves no one and exits with code 4. Switch and attach are the only commands that need a Herdr client, and they exist only to move or open a view.
- `kk attach` uses the same lookup to choose its initial target.

### Repo summaries

`RepoThreadSummaries` returns exactly the non-sensitive fields enumerated in [Authority](../04-authority.md#sensitive-reads).

- Its proto message is shared by `kk ls`, `kk log`, switch and attach lookup, the overlay, and the optional `ui` pane.
- Renderers cannot add fields by querying a more privileged endpoint.
- `--json` on a command prints the same message as [JSON](https://en.wikipedia.org/wiki/JSON). It changes rendering only. So the overlay and the `ui` pane show nothing that a command cannot print.
- An automation credential may read the summaries of every registered repo. Through this method it reads no more fields than a registration credential does.
- An automation credential may also read each registered thread's status and non-sensitive state, through `GetThreadState`, `GetCascadeStatus`, and the diagnose methods. This is what `kk status` and `kk repair` without `--apply` need. Those replies never carry transcript text, diff content, detailed audit arguments, or sync-intent payloads to it. Such a read needs a `sensitive-read` rule.
- Herdr's native sidebar is not a client of this service. `kkd` publishes the label and tokens it shows, one way, through `TerminalRuntime`.

(The MCP transcript surface, when it ships, lives on a separate socket (see [Roadmap](../16-roadmap.md).)

## Streaming events

UIs subscribe through server-streaming RPCs rather than polling (asking again and again):

- `StreamThreadEvents(thread_id)`: state transitions, cascade events, and transcript appends for one thread.
- `RepoThreadSummaries(repo_id)`: one-line summaries for sibling threads in the same repo. It is used by `kk ls`, the overlay, and the optional `ui` pane.
- `StreamRepoEvents(repo_id)`: the events of every thread in one repo, on one stream. An optional thread filter narrows it to one thread.
  - Each event carries its kind, its thread id, its sequence numbers, its time, and summary-class fields only. It never carries transcript text or any other [sensitive read](../04-authority.md#sensitive-reads).
  - It accepts the same credentials as `RepoThreadSummaries`: a thread or registration credential for its own repo, or an automation credential for any registered repo.

On disconnect, clients reconnect and re-subscribe. Events carry a monotonic `seq` (a number that only goes up), so clients can detect gaps.

`StreamThreadEvents.seq` is backed by the `thread_events` table in the repo database. `kkd` writes each event as a row and takes `seq` from that row. So `seq` keeps counting up across a `kkd` restart, and a client that reconnects can tell exactly which events it missed.

`StreamRepoEvents` orders events by `repo_seq`, a second number on the same row that only goes up across the whole repo. Both streams take a starting sequence number and replay the stored rows after it before they follow new ones.

**`kk events`.** [`kk events`](../09-commands.md#kk-events) is the command-line face of these two streams. With `--thread` in that thread's own context it reads `StreamThreadEvents`. Otherwise it reads `StreamRepoEvents`, with the thread filter when `--thread` is given. `--since <seq>` is the starting sequence number, and `--follow` keeps the stream open.

**`kk wait`.** `kk wait` needs no method of its own. `kk` subscribes to `StreamRepoEvents` with the thread filter, then reads the thread's current summary, and then follows the stream until the summary shows the wanted state. Subscribing first means no change can slip between the read and the stream. An already-open issue is observable through the summary’s `has_open_issue` field. Every wait state is a summary-class field, so an automation credential can wait. The timeout is counted by `kk`: exit code 0 when the state is reached and 6 on timeout.

**Audit.** Audit interception happens before method dispatch. That is, the audit layer sees every call before the call is routed to a method.

- Requests with a resolved repo write exactly one row to that repo database's `audit_log`.
- Bootstrap, registry-wide, unknown-repo, and pre-resolution failures write to `user_audit_log` in the per-user database. So do policy activation and revoke, and the creation, rotation, and revoke of an automation credential.
- The audit row of a `BeginApproval` that issues a `PolicyApproval` records the rule name, the policy digest, the principal, the operation, and the risk labels.
- Logging an unidentified caller uses a safe fingerprint and a null credential id, never raw credential bytes.

## Protocol stability

The proto file is the contract. Proto3 forward-compatibility rules apply:

- never reuse field numbers;
- never narrow types;
- prefer adding new methods over changing existing semantics (what a method means).

Breaking changes require a new service version. The daemon **may** host both versions during a transition.

## Future surfaces

A same-host native GUI can consume the unix-socket gRPC service directly.

A remote client will use the same rules for calling methods and getting
approval. The host must also verify which device sent each request and
check that its grant covers the profile and target. The first connection
to test uses Secure Shell (SSH) restricted to a kiki command.
See [Remote access through profiles](remote-access.md).

A remote grant never implies a policy rule. In v1 every policy principal is
local. A host's activated automation policy applies to remote callers only
once a remote principal kind exists, and that arrives with remote access.
