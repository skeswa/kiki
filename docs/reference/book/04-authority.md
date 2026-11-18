# Authority

Authority means who is allowed to do what. kiki's v1 authorization model limits the damage an agent can do by accident or through a bug.

It does not defend against an actively malicious process running as the same OS user (the same UID). A terminal confirmation prompt is not a security boundary against such a process.

In v1, running a normal `kk` subprocess as a human does not grant that subprocess reusable repo-wide authority.

kiki can also run [headless](appendix-a-glossary.md#headless): with no UI attached, and with no human present. Running with no human does not weaken this model. A consequential operation still needs a one-shot approval for its exact plan. What changes is who may give it. By default only a human can. An [automation policy](#automation-policy) that someone has activated can also give it, for the plans its rules allow.

## Credential and capability classes

A credential is a secret that proves who a caller is. A [capability](https://en.wikipedia.org/wiki/Capability-based_security) is a grant to do one specific thing. kiki has seven classes.

### `ThreadScoped<thread_id>`

A [`ThreadScoped<thread_id>`](appendix-a-glossary.md#threadscoped-credential) credential:

- is bound to one [thread](appendix-a-glossary.md#thread): one themed line of work with its own workspace;
- is written to `~/.config/kiki/repos/<repo_id>/credentials/<thread_id>` with mode `0600` ([readable only by the owning user](https://en.wikipedia.org/wiki/File-system_permissions));
- is read by [`kk-hook`](appendix-a-glossary.md#kk-hook), by the thread's [pane launcher](appendix-a-glossary.md#pane-launcher), and by any `kk` command whose discovered context is that thread;
- is rotated, replaced with a fresh secret, at three moments:
  - when an [incarnation](appendix-a-glossary.md#incarnation) (one live agent session for the thread) ends;
  - when a [terminal group](appendix-a-glossary.md#terminal-group) is restarted;
  - when a thread reopens;
- authorizes ordinary reads and mutations of that same thread only.

Rotation keeps the file in one place. The file's path is stable and its contents are replaced atomically (all at once). The pane launcher re-reads it after reporting a [harness](appendix-a-glossary.md#harness) exit. `kk` and `kk-hook` read it on every invocation.

Rotation does not cut off a running pane launcher. A launcher presents the credential once, with its claim. After `kkd` accepts that claim, the launcher's calls are authenticated by the accepted peer process identity: the `(pid, start_time)` that `kkd` read from the OS. So rotating the credential when an incarnation ends does not close the launcher's `SuperviseLauncher` stream, and it does not reject the launcher's `ReportHarnessExit`.

### `RegistrationScoped<repo_id>`

A [`RegistrationScoped<repo_id>`](appendix-a-glossary.md#registrationscoped) credential:

- is issued when `kk init` registers a repo, and revoked by `kk repo unregister`;
- is written to `~/.config/kiki/repos/<repo_id>/credentials/registration` with mode `0600`;
- is read by `kk` when no thread context resolves;
- authorizes the [repo-summary read](appendix-a-glossary.md#repo-summary-read-scope) and `BeginApproval` for that repo, and the [approval-free revokes](#revokes-that-need-no-approval) and setup reads available to all local credentials.

`kk ls --all-repos` presents each repo's own registration credential.

### `AutomationScoped<name>`

An [`AutomationScoped<name>`](appendix-a-glossary.md#automation-credential) credential is an **automation credential**: a named secret for a script, a [CI](https://en.wikipedia.org/wiki/Continuous_integration) job, or any other caller that runs with no human present. It:

- is created by `kk automation credential create <name>` and replaced by `kk automation credential rotate <name>`. Both need the same gate as [activating a policy](#activating-a-policy): a foreground confirmation by the enrolled presenter, or the Admin bootstrap credential;
- is removed by `kk automation credential revoke <name>`. Revoking only takes authority away, so it needs no approval, and any credential of this user may call it. `kk automation credential list` shows the names;
- is written to `~/.config/kiki/automation/<name>.cred` with mode `0600`, outside every managed workspace. kiki never injects it into a harness, a hook, or a pane environment;
- is presented by a caller through the `KIKI_AUTOMATION_CREDENTIAL_FILE` environment variable or the `--automation-credential-file <path>` flag;
- is user-scoped. It belongs to no single repo and no single thread.

For repo and thread work, an automation credential has these starting permissions. It can also look up its own prompt receipts and use the local status, list, and revoke methods described below.

- read the [repo summary](appendix-a-glossary.md#repo-summary-read-scope) for every registered repo;
- read the status and non-sensitive state of each registered thread. This is what `kk status`, `kk ls`, `kk events`, `kk wait`, and the diagnose step of `kk repair` need. A [sensitive read](#sensitive-reads) still needs a rule that allows `sensitive-read`;
- call `BeginApproval` for any registered repo or thread, for `kk init`, and for the user-scoped `replace-terminal-server` plan.

A plan begun with this credential can only receive a policy approval. Even with a terminal, a presenter cannot confirm that challenge. A person may begin a fresh plan with their own command credential.

Every consequential thing it does goes through the [automation policy](#automation-policy). A rule names the credential as the principal `credential:<name>`. With no rule that allows the plan, the call fails closed.

An automation credential is no thread's own credential. So every change it makes to a thread needs a one-shot approval, even an ordinary one that the thread itself could make freely, such as a checkpoint. In a policy rule that kind of change is the [`thread-op`](#the-thread-op-operation) operation.

An automation credential never confirms a human challenge. It is never accepted in place of Admin or the presenter.

See [`kk automation`](09-commands.md#kk-automation) for the commands.

### `HumanApproval`

A [`HumanApproval`](appendix-a-glossary.md#human-approval) capability:

- is minted (created) by the [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) only after a human confirms through an interactive foreground channel. The daemon is [`kkd`](appendix-a-glossary.md#kkd), the background server;
- is bound to the credential identity, the daemon method, the target repo and thread, a digest ([hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function)) of the security-relevant arguments, and a short expiry;
- is single-use. Exactly one durable operation record claims it, atomically, before any external side effect;
- cannot be refreshed or broadened by a `ThreadScoped` caller.

### `PolicyApproval`

A [`PolicyApproval`](appendix-a-glossary.md#policy-approval) capability is the sibling of `HumanApproval`. It stands in for the human's confirmation when the active [automation policy](#automation-policy) allows the exact plan. It:

- is minted by `kkd`, and only when a rule in the active policy allows the exact plan. No client, credential, or config file can mint one;
- is bound to the same things as a `HumanApproval`: the caller's credential identity, the daemon method, the target repo and thread, the plan digest, and a short expiry;
- is single-use. It is claimed into the same durable operation journal, atomically, before any external side effect;
- cannot be refreshed, broadened, or reused for a second plan;
- records the name of the rule that allowed it and the digest of the policy it came from.

This book uses **one-shot approval** to mean either capability. The rule that connects them is stated once, in [Operations that require human approval](#operations-that-require-human-approval): wherever the book asks for a `HumanApproval`, a `PolicyApproval` for the same plan satisfies it.

These setup operations can never be approved by a `PolicyApproval`:

- activating a policy;
- creating or rotating an automation credential;
- enrolling or recovering the approval presenter with Admin;
- changing an existing daemon installation.

An enrolled presenter or explicit Admin can authorize an installation change, policy activation, or automation credential creation or rotation. Presenter enrollment and recovery require Admin and a person at the terminal.

### `ApprovalPresenter`

An [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter) is the part of kiki that shows a plan to the human and collects the answer. It:

- is a local frontend identity, enrolled explicitly through Admin bootstrap;
- is stored outside managed workspaces. kiki never injects it into a harness, a hook, a shell pane environment, or an ordinary operational request;
- may confirm or cancel a pending approval challenge only while its CLI or [TUI](https://en.wikipedia.org/wiki/Text-based_user_interface) process owns the foreground [controlling terminal](<https://en.wikipedia.org/wiki/Job_control_(Unix)>), the terminal the user is actively typing into;
- cannot invoke thread operations, widen a challenge, or mint an approval without a daemon-issued challenge.

A host that never has a human does not need an enrolled presenter. On such a host, an operation that no policy rule allows fails closed.

### `Admin`

`Admin` is bootstrap (first-time setup) authority. See [Bootstrap Admin credential](appendix-a-glossary.md#bootstrap-admin-credential).

- It exists for daemon setup, approval-presenter enrollment, and automation setup, not as ambient CLI authority.
- A first `kk daemon install` creates the Admin bootstrap credential and prints its path. That first install needs no credential, because none exists yet. On a host with no user service manager, `kkd --foreground` creates the credential on its first start and logs its path. The installation keeps the secret outside thread workspaces. `kk` never loads it automatically, and agents are never given it.
- Only explicit bootstrap, recovery, and automation-setup endpoints accept Admin. Operational thread methods reject it.
- A command takes Admin only from an explicit `--admin-credential-file <path>` flag, and only these commands accept that flag:
  - `kk automation apply`, to [activate a policy](#activating-a-policy);
  - `kk automation credential create` and `kk automation credential rotate`, to issue an [automation credential](appendix-a-glossary.md#automation-credential);
  - `kk daemon install`, when a later run changes an installation that already exists. That run needs a foreground confirmation or this flag.

  This is the path for a machine that never has a human. On a machine with a person, the enrolled presenter can confirm the same actions at a foreground terminal instead.

- There is one more use. When a human runs `kk init`, the approval is begun under the user's Admin bootstrap credential, because no thread credential or registration credential exists yet. So `kk init` calls `BeginApproval` for a repo registration with Admin. The user-scoped `replace-terminal-server` plan (`kk repair --server`) is begun the same way, because it belongs to no repo. Admin can only begin these challenges. Admin is not a policy principal, so no rule matches a challenge begun under Admin. The enrolled presenter must still confirm it, and the registration still consumes the resulting `HumanApproval`.
- A caller that presents an automation credential does not use Admin for these. It begins `kk init` and `replace-terminal-server` with the automation credential, and the active policy must have a rule that allows the plan.
- After enrollment, the daemon authorizes a consequential operation by validating and claiming its one-shot approval. It never accepts Admin in place of that capability.

### Claiming an approval

Claiming an approval and performing an external side effect cannot share one [transaction](https://en.wikipedia.org/wiki/Database_transaction). So kiki works in this order:

1. Kiki first claims the approval and creates a durable operation journal in one [SQLite](https://www.sqlite.org/) transaction.
2. The journal then performs the exact approved plan [idempotently](https://en.wikipedia.org/wiki/Idempotence), so replaying it causes no extra effect.
3. The journal marks the approval consumed on completion.

After a crash, kiki resumes or reconciles that same operation id. It cannot reuse the approval for a second plan. If a remote outcome is unknown, kiki stops and observes. Any change to the method, target, argument digest, or repair/publish plan requires fresh approval.

## Two-phase foreground approval

Consequential commands all use one protocol. A confirmation prompt by itself is not authority:

1. **Begin.** The operational client authenticates with its `ThreadScoped`, registration, or automation credential. For a setup change the requester may also begin under explicit Admin and have the enrolled presenter confirm. The other exceptions are `kk init` and the user-scoped `replace-terminal-server` plan when the caller has no automation credential: no thread or registration credential applies, so that approval is begun under the user's [Admin bootstrap credential](appendix-a-glossary.md#bootstrap-admin-credential). It calls `BeginApproval` with the complete proposed method, target, and security-relevant arguments. The daemon then:
   - runs a non-mutating preflight;
   - canonicalizes the plan into one fixed form;
   - computes the plan's [risk labels](#risk-labels) and shows them in the rendered plan;
   - stores a short-lived pending challenge bound to the requesting credential;
   - evaluates the active [automation policy](#automation-policy) against the plan;
   - returns the canonical human-readable plan, its digest, and the [policy decision](#the-policy-decision).
2. **Confirm.** Exactly one of two things supplies the confirmation.
   - **A policy rule.** When the decision is `Allowed`, `kkd` issues one [`PolicyApproval`](#policyapproval) for the already-bound plan in the same reply. Nobody is asked.
   - **A human.** For a requester eligible for the human path, the enrolled [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter) proves that it owns the foreground controlling terminal. It displays the daemon-returned plan byte-for-byte, collects an explicit confirmation, and calls `ConfirmApproval(challenge_id)`. Confirmation issues one `HumanApproval` for the already-bound plan. Cancellation or expiry closes the challenge and issues nothing.
3. **Retry with the approval.** The operational client retries the exact method, now carrying the approval id. In one SQLite transaction, the daemon:
   - verifies the caller, method, target, digest, expiry, and unused status;
   - claims the approval into one durable operation journal;
   - only then permits external effects.

The two credentials never stand in for each other:

- The presenter credential works only in phase 2. No operational method accepts it.
- The operation credential is never sufficient for phase 2. That includes an automation credential: it never confirms a human challenge.
- A challenge cannot be edited after `BeginApproval`. Any changed argument or repository observation requires a new challenge.
- CLI and TUI frontends may implement both roles in one process, but they keep the credentials and [RPC](https://en.wikipedia.org/wiki/Remote_procedure_call) phases distinct.

Foreground-terminal checks and presenter enrollment reduce accidental agent authority. They do not prove user presence against a malicious same-UID process, and v1 does not claim otherwise.

### The policy decision

The policy decision is `kkd`'s answer to one question: does the active policy allow this exact plan? `kkd` evaluates the caller's principal, the repo, the operation, and the plan's risk labels, as [How `kkd` evaluates a plan](#how-kkd-evaluates-a-plan) describes. The answer is a `PolicyDecision` with one of three values:

- **`Allowed{rule}`.** `kkd` issues a `PolicyApproval` in the same reply. The client retries the method with it, and phase 3 runs unchanged. `kk` prints the plan and the line "approved by rule `<name>`". It does not prompt. Passing `--confirm` forces the human prompt anyway.
- **`RequireHuman{rule}`.** A rule says a human must confirm this plan.
- **`NoMatch`.** No rule covers the plan. This is always the answer when no policy is active.

For `RequireHuman` and `NoMatch`, what happens next depends on the caller:

- **With an automation credential,** stop with code 3. This includes `--confirm`, which asks for an approval that this credential cannot use.
- **For other requesters with a foreground terminal,** the presenter flow runs as in phase 2.
- **Without a terminal,** the command [fails closed](appendix-a-glossary.md#fail-closed). It exits with [code 3](09-commands.md#exit-codes). Its message names the operation, the plan's risk labels, and the reason: no rule matched, or rule `<name>` requires a human.

`kkd` still refuses `ConfirmApproval` from a process that is a descendant or session member of an agent launcher. So an agent can never confirm a human challenge. An agent gets approval authority only through a rule whose principal matches its thread credential, including the wildcard `*`.

## Thread-scoped permissions

A [thread-scoped credential](appendix-a-glossary.md#threadscoped-credential) may:

- read its own thread state, working-state summary, and non-sensitive audit slice;
- read and advance cascade delivery state, the record of updates flowing from a followed thread, for its own thread, through the specific hook methods;
- perform ordinary same-thread lifecycle or metadata operations that are neither destructive nor externally visible, and that are not on the approval list below;
- read the minimal same-repo summary and [terminal target](appendix-a-glossary.md#terminal-target) (where the thread's [terminal group](appendix-a-glossary.md#terminal-group) currently lives) that `kk ls` and `kk switch` need.

It must not, by itself:

- mutate a sibling or unrelated thread;
- read another thread's [transcript](appendix-a-glossary.md#thread-transcript), diff, detailed audit arguments, or sync-intent payload;
- destroy or irreversibly discard state;
- publish, close a remote [PR](https://docs.github.com/en/pull-requests), post a comment, force-push, or take any other externally visible action;
- mint approval capabilities or invoke Admin methods.

A one-shot approval is what lifts an item on this list for one exact plan. A human can give it. So can an activated [automation policy](#automation-policy) rule whose principal is `thread:self`, `thread:descendant`, or `thread:any`. A thread-scoped caller can never give it to itself.

The transport checks both the credential's scope and the requested target. Supplying an explicit target never changes the identity the credential conveys.

## Operations that require human approval

The following require a [`HumanApproval`](appendix-a-glossary.md#human-approval) bound to the exact method and target, even when the caller already holds a valid thread credential.

One general rule applies to this list and to the whole book. Wherever the book says an operation needs a `HumanApproval`, a [`PolicyApproval`](#policyapproval) for the same plan satisfies it. The book keeps the name `HumanApproval` in those places and does not repeat this rule each time. [Setup operations](#policyapproval) have their own bootstrap rules.

The list:

- repo registration with `kk init`;
- thread creation with `kk new`, `kk reopen`, and each follow-up user turn submitted with `kk prompt`;
- any mutation of a thread other than the caller's contextual thread. A caller with an automation credential has no contextual thread, so this covers every thread change it makes. When the change is an ordinary one that needs approval for this reason alone, its operation is [`thread-op`](#the-thread-op-operation);
- explicit preparation with `SnapshotWorkspace`, even from the thread's own context;
- destructive operations, including thread destroy, repo unregister, discarding pending reconciliation (for example `kk thread detach --discard-pending`), and any repair that deletes or rewrites state;
- repairs that place or re-create the checkpoint bookmark under approval: [`adopt-bookmark`](appendix-a-glossary.md#adopt-bookmark), [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target), [`unhide-checkpoint`](appendix-a-glossary.md#unhide-checkpoint), and the repo-level [`reanchor-history`](appendix-a-glossary.md#reanchor-history). `restore-bookmark` only puts the bookmark back on the expected target, so it needs no approval in the thread's own context; applied to a different thread, it needs a one-shot approval;
- sensitive reads, including another thread's transcript or diff, and repo-wide detailed audit arguments;
- externally visible actions, including publish, remote branch rewriting, PR mutation, and comments;
- process-destructive operations a human requests, such as interrupting or closing a live agent session. The approval covers every process in the listed terminal containers at freeze time, and the rendered plan says so;
- [`terminate-orphans`](appendix-a-glossary.md#terminate-orphans), which ends leftover processes, and [`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server), which stops the whole dedicated server and every process in it;
- topology surgery whose result cannot be derived unambiguously from already recorded intent. (Topology is the shape of the commit graph.)

### Restarts that need no approval

Kiki's own protocol restarts are not on this list.

- The cascade's delivery protocol may retire an [incarnation](appendix-a-glossary.md#incarnation) and start a replacement to deliver a saved payload. That is a daemon-initiated step of a contract that was accepted when the thread was set to follow another. It consumes no approval.
- Applying [`restart-agent`](appendix-a-glossary.md#restart-agent) in the thread's own context to a harness that has already exited destroys nothing. It needs no approval either. Applied by any other caller, it is a [`thread-op`](#the-thread-op-operation) and needs a one-shot approval.
- [`retry-close`](appendix-a-glossary.md#retry-close) and [`retry-destroy`](appendix-a-glossary.md#retry-destroy) need no new approval. They continue a plan that already has its approval, and they never widen it.

The approval each repair plan needs is listed in one table, [Every issue and its plan](09-commands.md#every-issue-and-its-plan) in Commands. That table is the owner; this chapter states the rules behind it.

### Revokes that need no approval

Three commands only take authority or permission away:

- `kk automation revoke`, which clears the active policy;
- `kk automation credential revoke <name>`, which makes one automation credential stop working;
- `kk privacy consent revoke`, which withdraws a remembered provider-egress consent.

The permission to revoke is an explicit addition to the thread, registration, automation, and Admin credential allowlists. None of them needs an approval. Any credential of this user may call them: a thread, registration, or automation credential, or Admin.

### Unattended approval

Unattended approval comes from one place only: a rule in an activated [automation policy](#automation-policy). The policy is empty by default, so a fresh install approves nothing without a human.

The CLI displays the exact method, target, consequential arguments, and risk labels for every plan. Then one of three things happens, as [The policy decision](#the-policy-decision) describes:

- a rule allows the plan, and the command proceeds with a `PolicyApproval`;
- no rule allows it and the caller has a foreground terminal, so the CLI asks the human to approve;
- no rule allows it and the caller has no terminal, so the command fails closed with exit code 3. It stops instead of proceeding.

kiki still provides none of these shortcuts:

- a blanket `--yes`;
- confirmation piped in on standard input;
- approval through an environment variable;
- approval from an ordinary config key or from a policy file that was edited but not activated;
- a reusable approval token.

`kk` also never asks a question that only a keyboard can answer. Every interactive question has a flag or argument that answers it. Examples are the target of `choose-bookmark-target`, the daemon install question, and presenter enrollment. Without a terminal, `kk` does not prompt. It fails and names the missing flag.

A `HumanApproval` proves that an interactive confirmation happened. Under the cooperative same-UID threat model, it does not prove the confirmer is immune to UI spoofing (a fake prompt). A `PolicyApproval` proves that the activated policy allowed the plan. It does not prove that a person looked at it. Filesystem [sandboxing](<https://en.wikipedia.org/wiki/Sandbox_(computer_security)>) and OS-backed user presence remain out of scope.

## Automation policy

An [automation policy](appendix-a-glossary.md#automation-policy) is a list of rules. Each rule says which plans `kkd` may approve with no human present, and for which callers.

Three facts frame the rest of this section:

- **The policy is empty by default.** With an empty or absent policy, kiki behaves exactly as the sections above describe. A human confirms at a foreground terminal, and a caller with no terminal fails closed.
- **The policy lives in the user config file only.** The rules are `[[automation.rule]]` entries in the `[automation]` section. A repo config file, a thread layer, an environment variable, and `--config` cannot set them. [Configuration](11-configuration.md#automation-keys) owns the key syntax. This chapter owns what the rules mean.
- **Editing the file does nothing by itself.** A policy takes effect only when it is [activated](#activating-a-policy).

### What a rule says

```toml
[[automation.rule]]
name       = "ci-lifecycle"
principals = ["credential:ci"]
repos      = ["*"]
operations = ["init", "new", "reopen", "close", "repair:restart-terminal"]
accept     = ["live-processes"]
effect     = "allow"
```

This rule lets the automation credential named `ci` register repos, create, reopen, and close threads, and restart a thread's missing terminal, in any repo. It accepts plans that end live processes. It accepts no other risk.

| Field        | Meaning                                                                                                                                                                                                                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`       | A unique string. It appears in audit rows and in the "approved by rule" line.                                                                                                                                                                                                                           |
| `principals` | Who is calling. The values are listed below.                                                                                                                                                                                                                                                            |
| `repos`      | Repo ids or canonical repo paths, or `*` for every repo. A repo that `kk init` has not registered yet has no id, so a rule matches it by path or by `*`. A plan that belongs to no repo, such as `replace-terminal-server`, matches only `*`.                                                           |
| `operations` | Which operations the rule covers: `init`, `new`, `prompt`, `snapshot`, `reopen`, `close`, `destroy`, `unregister`, `detach`, `interrupt`, `restart`, `publish` (v1.x), `audit-log`, `sensitive-read`, `thread-op`, `repair:<plan-name>`, `repair:*` for every repair plan, `consent:<purpose>`, or `*`. |
| `accept`     | The [risk labels](#risk-labels) an `allow` rule accepts, or `*` for all of them. The default is empty: the rule accepts no risk. A `require-human` rule ignores this field.                                                                                                                             |
| `effect`     | `allow` or `require-human`.                                                                                                                                                                                                                                                                             |

A principal is the kind of caller a rule applies to. `kkd` works it out from the credential the caller presented and the target of the plan. The caller cannot claim one.

| Principal           | The caller…                                                                                               |
| ------------------- | --------------------------------------------------------------------------------------------------------- |
| `credential:<name>` | presents the automation credential with that name                                                         |
| `thread:self`       | holds a thread-scoped credential and acts on its own thread                                               |
| `thread:descendant` | holds a thread-scoped credential and acts on a thread that follows its own thread, directly or indirectly |
| `thread:any`        | holds a thread-scoped credential and acts on any thread in its repo, or creates one                       |
| `registration`      | holds only the repo's registration credential                                                             |
| `*`                 | is any of the above                                                                                       |

One call can fit more than one value. A thread closing itself is both `thread:self` and `thread:any`.

A thread-scoped credential is read by every `kk` command run in that thread's context. That includes commands the thread's agent runs. So a `thread:` principal covers any holder of the thread credential, human or agent. A rule with a `thread:` principal hands that approval to the agent as well as to a human typing in the same workspace.

#### The `thread-op` operation

`thread-op` is one operation name for many small changes. It covers any ordinary change to a thread that needs approval for one reason only: the caller is not that thread. Examples are a checkpoint, a describe, and a restart of a harness that has already exited, when an automation credential or another thread runs them. The thread itself can do each of these with no approval.

- A `thread-op` plan carries the `cross-thread` [risk label](#risk-labels) when the caller is thread-scoped. It carries no label when the caller presents an automation credential.
- An operation that has its own name in the list keeps that name, whoever calls: `close`, `destroy`, `detach`, `interrupt`, `restart`, and the rest. `thread-op` covers only the changes that have no name of their own.
- The same split applies to repair plans. `repair:<plan-name>` names a plan that needs a one-shot approval in every context, such as `repair:restart-terminal`. A plan that needs none in the thread's own context, such as `restart-agent` or `restore-bookmark`, has no `repair:` name. Applied from outside the thread, its operation is `thread-op`. [Every issue and its plan](09-commands.md#every-issue-and-its-plan) says which plans are which.

Everything is configurable, including the widest possible rule:

```toml
[[automation.rule]]
name       = "everything"
principals = ["*"]
repos      = ["*"]
operations = ["*"]
accept     = ["*"]
effect     = "allow"
```

This rule hands every policy-eligible approval except provider-egress consent to any matching local caller, including every agent. kiki allows it because the owner decides the policy. It is not a default, and nothing sets it without an explicit activation.

### Risk labels

A [risk label](appendix-a-glossary.md#risk-label) names one kind of harm a plan can do. Some choices used to need a human's informed consent, such as ending live processes or accepting lost work. Each of those choices is now a label.

`kkd` computes the label set of each plan during preflight and shows it in the rendered plan. A caller cannot add or remove a label. The set is closed, and this chapter owns it:

| Label                | The plan…                                                   |
| -------------------- | ----------------------------------------------------------- |
| `live-processes`     | terminates running processes in the thread's containers     |
| `outside-holders`    | accepts a holder outside the listed containers              |
| `work-loss`          | has a non-empty loss inventory                              |
| `discard-pending`    | discards pending reconciliation (`--discard-pending`)       |
| `backward-bookmark`  | moves a bookmark backward (`--allow-backwards`)             |
| `server-wide`        | stops the whole terminal server (`replace-terminal-server`) |
| `cross-thread`       | mutates or reads a thread other than the caller's own       |
| `externally-visible` | publishes, pushes, or changes a PR or comment (v1.x)        |
| `history-rewrite`    | re-anchors operation history (`reanchor-history`)           |

Two notes on the table:

- A plan with no labels still needs a one-shot approval when its operation is on the [approval list](#operations-that-require-human-approval). Labels describe risk. They do not decide whether approval is needed.
- `cross-thread` applies to a caller that has a thread of its own, which means a thread-scoped caller. An automation credential and a registration credential have no thread of their own. Their reach is set by the rule's `repos` and `operations`.

Adding a label is an authority-model change. It is made here first.

### How `kkd` evaluates a plan

`kkd` evaluates the stored copy of the activated policy and nothing else. It never reads the config file to make a decision.

A rule matches a plan when all of these hold:

1. `principals` contains a value that fits the caller.
2. `repos` contains the plan's repo, or `*`.
3. For consent, the rule explicitly lists the purpose and normalized provider, and its activation covers the current disclosure version. This applies to both effects.
4. `operations` contains the plan's operation. `repair:*` covers every repair plan that has a `repair:` name, and `*` covers every operation except consent.
5. For an `allow` rule only: every risk label of the plan is in `accept`. A plan with a label the rule does not accept is not matched by that rule.

A `require-human` rule ignores `accept`. It matches on principals, repos, and operations, and on provider for a consent rule. Risk labels cannot narrow it.

Then `kkd` picks the decision:

1. If any matching rule has `effect = "require-human"`, the decision is `RequireHuman`. `require-human` wins over any `allow`.
2. Otherwise, if any matching rule has `effect = "allow"`, the decision is `Allowed`.
3. Otherwise the decision is `NoMatch`, and a human is required.

When several rules of the winning kind match, the decision names the first one in file order.

So only `allow` rules use `accept`. A `require-human` rule that names an operation requires a human for every plan of that operation, and it beats every `allow` rule that matches the same plan.

Provider-egress consent has a stricter rule. The `*` operation never matches `consent:<purpose>`. A consent rule must name the purpose, and it must also carry `providers = ["<normalized provider identity>", …]`. A plain config key still cannot grant consent. An activated policy rule that names both the purpose and the provider can. `publish` and `consent:` rules arrive with the features they gate.

### Policy replaces confirmation, never proof

A policy replaces one thing: the human's confirmation in phase 2. Everything else in the protocol is unchanged:

- the non-mutating preflight and the canonical plan;
- the plan digest, and the drift and expiry checks;
- single use, and the claim into the operation journal;
- freeze, [holder](appendix-a-glossary.md#holder) scans, and the [final proof](appendix-a-glossary.md#final-proof);
- [verified exit](appendix-a-glossary.md#verified-exit) before deletion.

So a policy can never make a plan run that the safety proofs refuse. Under `accept = ["*"]`, a close that finds an unknown writer still preserves the files and stops. If the plan changes after approval, the `PolicyApproval` is void and the caller must begin again, exactly as with a `HumanApproval`.

### Activating a policy

Activation is the step that turns the rules in the config file into the policy `kkd` enforces.

`kk automation apply` reads the `[automation]` section. `kkd` canonicalizes the rules into one fixed form and computes a policy digest. Then activation needs one of two things:

- **A foreground confirmation by the enrolled `ApprovalPresenter`.** The presenter shows the full canonical policy and a diff against the active one.
- **The Admin bootstrap credential,** passed as `--admin-credential-file <path>`. This is the path for a machine that never has a human. Admin is still never loaded automatically and never given to agents.

A `PolicyApproval` can never activate a policy.

After activation:

- `kkd` stores the active policy and evaluates only that stored copy.
- `kk automation status` shows the active policy, its digest, who activated it and when, and whether the file now differs from it. `kk doctor` reports the same drift when it ships.
- `kk automation revoke` clears the active policy. It only removes authority, so it needs no approval, and any credential of this user may call it.

A revoke stops new approvals. A `PolicyApproval` that was already issued stays valid until its short expiry, even after the policy is revoked or replaced. It does not survive a revoke of the credential it is bound to: after that, it can no longer be claimed.

This is the reason an agent cannot grant itself authority by editing a config file. An edited file that nobody applied changes nothing.

Like presenter enrollment, activation is hygiene under the cooperative same-UID model. It is not a security boundary. A malicious process running as the same user can read the Admin credential file or edit the database directly. Activation stops accidents and bugs, which is what this chapter promises.

See [`kk automation`](09-commands.md#kk-automation) for the commands.

## Sensitive reads

Same-thread [transcript](appendix-a-glossary.md#thread-transcript) reads, once transcript capture ships, use `ThreadScoped<T>`. Reading thread U while authorized as thread T requires a one-shot approval for that exact read. In a policy rule, that operation is `sensitive-read`, and the plan carries the `cross-thread` label. The same rule covers sibling diffs, detailed audit arguments, and any other content that exposes working state.

For a thread-scoped or registration caller, the repo summary is the only cross-thread read available without approval. See [repo-summary read scope](appendix-a-glossary.md#repo-summary-read-scope).

An automation credential belongs to no thread, so it has no "own thread" to read. Without approval it may read the repo summary of every registered repo, and each registered thread's status and non-sensitive state. That is what `kk status`, `kk ls`, `kk events`, `kk wait`, and the diagnose step of `kk repair` show: lifecycle and cascade state, the checkpoint relationship, open issues and their plans, and summary-class events. Thread repair diagnosis also exposes a narrow recovery choice to authorized diagnose callers. It returns the opaque intent and plan ids, exact operation id, candidate commit ids, and one edit-preservation answer per candidate. These fields are available only from diagnosis. Paths, file content, recovery bundles, and other intent details require a sensitive read.

The repo summary's complete field set is:

- repo and thread id, display name, bookmark display name, and the followed parent's id/name;
- lifecycle state, three-valued cascade state, [agent display state](appendix-a-glossary.md#agent-display-states), and [checkpoint relationship](appendix-a-glossary.md#checkpoint-relationship) (`current | behind | ahead | diverged`);
- [terminal target](appendix-a-glossary.md#terminal-target) (the dedicated server's address and instance, and the current binding's terminal-group and agent-pane refs), one-line revision description, and the last-agent-event category and timestamp that Activity ordering uses;
- a `has_open_issue` boolean for `kk wait --for issue`, including on closed threads;
- after GitHub integration ships: PR number, PR state, and [CI](https://en.wikipedia.org/wiki/Continuous_integration) roll-up.

It contains none of the following:

- transcript text;
- diff content or paths;
- sync-intent payloads or internals;
- audit arguments;
- prompts;
- tool content;
- model/context-window telemetry;
- write methods.

`kk ls`, `kk switch`, `kk log`, and future read-only renderers all consume this same row set for everything they say about a thread.

The revision lines `kk log` prints are a different kind of data. They come from the shared jj repository, which every workspace of the repo can already read with `jj log`. They expose nothing that the shared repository does not.

Adding a field is an authority-model change, not a renderer convenience.

## Command context and switch

The CLI resolves a contextual thread as described in [Commands](09-commands.md#context-resolution) and loads only that thread's credential. Outside a thread context, repo-summary reads use a separate [least-privilege](https://en.wikipedia.org/wiki/Principle_of_least_privilege) registration capability. Commands that need stronger authority start the [approval flow](#two-phase-foreground-approval). A policy rule or a human at a foreground terminal then approves the plan, or the command fails closed.

`kk switch <thread>` does two things:

1. a summary-class lookup of the target thread's [terminal target](appendix-a-glossary.md#terminal-target);
2. a [caller-local focus](appendix-a-glossary.md#caller-local-focus) request to the terminal runtime through [`TerminalClient`](appendix-a-glossary.md#terminalclient).

It moves the invoking viewer's terminal and no other. It does not mutate daemon focus state. It creates, closes, or changes no terminal resource. So selecting a thread does not require cross-thread mutation approval. Any audit emission records the invoker and the lookup. It does not turn switch into an Admin operation.

Moving someone else's view is a different act. The terminal runtime's public focus methods move every attached client. So kiki uses them only for the explicitly named `kk switch --all-clients`, never as a fallback for the local form. When the caller cannot be tied to one attached client, `kk switch` moves no one. See [Terminal runtime · Caller-local focus](13-architecture/terminal-runtime.md#caller-local-focus).

## Terminal runtime authority

[Herdr](appendix-a-glossary.md#herdr) is the terminal multiplexer kiki uses. Herdr's [socket](https://en.wikipedia.org/wiki/Unix_domain_socket) has a different authority model from kiki's, and kiki does not borrow it.

Any same-UID process that can reach the [dedicated server's](appendix-a-glossary.md#dedicated-herdr-server) socket can create, close, relabel, or send input to any terminal group. That includes every process running inside a pane, which inherits the socket path. Herdr has no per-thread credential and no plan-bound approval.

Kiki therefore draws the line on its own side:

- **Kiki's rules bind kiki's operations.** A lifecycle [saga](appendix-a-glossary.md#saga) closes a terminal group only inside an approved, journaled plan. This holds whatever the runtime would allow an arbitrary caller to do.
- **An unjournaled terminal change is external.** A terminal change kiki did not journal is an external projection change. It is observed, classified, and repaired under the same rules as an out-of-band `jj` command. It is never treated as a kiki decision.
- **Nothing read from the runtime is authority.** Labels, [metadata tokens](appendix-a-glossary.md#sidebar-token), working directories, pane placement, and Herdr ids never authorize a mutation, substitute for a credential, or prove that a directory may be deleted.
  - A Herdr ref may _locate_ the caller's contextual thread, as [Commands](09-commands.md#context-resolution) describes. It may do so only when it is observed under the current [server instance](appendix-a-glossary.md#server-instance) and matches a current binding.
  - What then authorizes the call is that thread's own credential.
- **A Herdr action is not an approval.** A Herdr keybinding, plugin action, or sidebar click may start a `kk` process or request navigation. It is never a `HumanApproval`. It gives that process no authority beyond its own credential. Approval still requires an enrolled `ApprovalPresenter` that owns its foreground terminal, or a `PolicyApproval` that `kkd` issued under the activated policy.
- **Strong credentials stay out of panes.** Kiki never places an `ApprovalPresenter`, Admin, or automation credential in a pane's launch environment, a metadata token, or the generated Herdr configuration.
- **Two measures close the accidental path.** The harness is started with every `HERDR_*` variable removed from its [environment](https://en.wikipedia.org/wiki/Environment_variable). Also, `kkd` refuses a confirmation from a presenter process that is a descendant or session member of any `agent` launcher. An agent that goes looking can still find the socket. These measures close the accidental path, not the deliberate one.

This is the cooperative model again, not enforcement against a same-UID adversary.

## Audit

Every parseable daemon transport attempt produces exactly one authoritative SQLite audit row. The row records:

- the request id;
- the method/path;
- the credential and approval identity, when identifiable. The approval's kind is `Human` or `Policy`;
- the declared scope;
- a compact argument summary;
- the outcome;
- a timestamp.

Every `PolicyApproval` writes an audit row that also records the rule name, the policy digest, the principal, the operation, and the plan's risk labels. So the log always shows which rule approved which plan, and under which version of the policy.

Where the row goes depends on the request:

- Unregister and attempts against a fenced registration go to `user_audit_log`. For other resolved repos, the row belongs to the repo's `audit_log` table.
- Some requests belong to the per-user `user_audit_log` table in `~/.config/kiki/state.db` instead. These are bootstrap, approval-presenter enrollment, repo listing, registration attempts before a repo exists, unknown-repo targets, and requests that fail before repo resolution.
- Automation setup is audited in `user_audit_log` as well: policy activation and revoke, and automation credential create, rotate, and revoke. The user database also keeps every activated policy with its digest, its canonical text, and whether the presenter or Admin activated it.
- Unauthenticated rows may carry null credential/approval ids and keep only a safe fingerprint of the presented identity. Audit logging must not persist raw credentials.

An attempt is written to one sink (destination), never mirrored to both. If the target repo resolves during registration, the registration request stays in the user-level sink where it began. Later repo-scoped calls use the new per-repo sink.

The table is append-only through the daemon API. That is an operational invariant, not tamper evidence. A same-UID process can still edit the database directly.

Who may read the audit log:

- Same-thread non-sensitive slices use thread authority.
- Cross-thread or detailed reads require a one-shot approval. In a policy rule, the repo-wide detailed read is the `audit-log` operation.

A future export command may render the SQLite authority as [JSONL](https://jsonlines.org/). But no second audit store is authoritative.

## Remote authority after v1

The host checks each request against the device's grant for that profile.
It also checks what the requested action requires. For example, a device
can have permission to reach a thread and still need a person's approval
to close it. The host's enrolled presenter collects that approval. A viewer
on another machine needs its own way to prove the person confirmed the plan
before kiki can accept approval there. See [Remote access through profiles](13-architecture/remote-access.md#connecting-and-granting-access).

A remote grant never implies an automation policy rule. A host's activated
policy applies to remote callers only once a remote principal kind exists,
and that arrives with remote access. Until then, policy principals are local.
