# Authority

Authority means who is allowed to do what. kiki's v1 authorization model limits the damage an agent can do by accident or through a bug.

It does not defend against an actively malicious process running as the same OS user (the same UID). A terminal confirmation prompt is not a security boundary against such a process.

In v1, running a normal `kk` subprocess as a human does not grant that subprocess reusable repo-wide authority.

## Credential and capability classes

A credential is a secret that proves who a caller is. A [capability](https://en.wikipedia.org/wiki/Capability-based_security) is a grant to do one specific thing. kiki has five classes.

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
- authorizes the [repo-summary read](appendix-a-glossary.md#repo-summary-read-scope) and `BeginApproval` for that repo, and nothing else.

`kk ls --all-repos` presents each repo's own registration credential.

### `HumanApproval`

A [`HumanApproval`](appendix-a-glossary.md#human-approval) capability:

- is minted (created) by the [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) only after a human confirms through an interactive foreground channel. The daemon is [`kkd`](appendix-a-glossary.md#kkd), the background server;
- is bound to the credential identity, the daemon method, the target repo and thread, a digest ([hash](https://en.wikipedia.org/wiki/Cryptographic_hash_function)) of the security-relevant arguments, and a short expiry;
- is single-use. Exactly one durable operation record claims it, atomically, before any external side effect;
- cannot be refreshed or broadened by a `ThreadScoped` caller.

### `ApprovalPresenter`

An [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter) is the part of kiki that shows a plan to the human and collects the answer. It:

- is a local frontend identity, enrolled explicitly through Admin bootstrap;
- is stored outside managed workspaces. kiki never injects it into a harness, a hook, a shell pane environment, or an ordinary operational request;
- may confirm or cancel a pending approval challenge only while its CLI or [TUI](https://en.wikipedia.org/wiki/Text-based_user_interface) process owns the foreground [controlling terminal](<https://en.wikipedia.org/wiki/Job_control_(Unix)>), the terminal the user is actively typing into;
- cannot invoke thread operations, widen a challenge, or mint an approval without a daemon-issued challenge.

### `Admin`

`Admin` is bootstrap (first-time setup) authority. See [Bootstrap Admin credential](appendix-a-glossary.md#bootstrap-admin-credential).

- It exists for daemon setup and approval-presenter enrollment, not as ambient CLI authority.
- An installation may persist an Admin secret outside thread workspaces. But `kk` does not automatically load it for ordinary commands, and agents are never given it.
- Only explicit bootstrap and recovery endpoints accept Admin. Operational thread methods reject it.
- There is one more use. The approvals for `kk init` and first run are begun under the user's Admin bootstrap credential, because no thread credential or registration credential exists yet. So `kk init` calls `BeginApproval` for a repo registration with Admin. The user-scoped `replace-terminal-server` plan (`kk repair --server`) is begun the same way, because it belongs to no repo. Admin can only begin these challenges. The enrolled presenter must still confirm it, and the registration still consumes the resulting `HumanApproval`.
- After enrollment, the daemon authorizes a consequential operation by validating and claiming its `HumanApproval`. It never accepts Admin in place of that capability.

### Claiming an approval

Claiming an approval and performing an external side effect cannot share one [transaction](https://en.wikipedia.org/wiki/Database_transaction). So kiki works in this order:

1. Kiki first claims the approval and creates a durable operation journal in one [SQLite](https://www.sqlite.org/) transaction.
2. The journal then performs the exact approved plan [idempotently](https://en.wikipedia.org/wiki/Idempotence), so replaying it causes no extra effect.
3. The journal marks the approval consumed on completion.

After a crash, kiki resumes or reconciles that same operation id. It cannot reuse the approval for a second plan. If a remote outcome is unknown, kiki stops and observes. Any change to the method, target, argument digest, or repair/publish plan requires fresh approval.

## Two-phase foreground approval

Consequential commands all use one protocol. A confirmation prompt by itself is not authority:

1. **Begin.** The operational client authenticates with its `ThreadScoped` or registration credential. The exceptions are `kk init`, first run, and the user-scoped `replace-terminal-server` plan: no thread or registration credential applies, so that approval is begun under the user's [Admin bootstrap credential](appendix-a-glossary.md#bootstrap-admin-credential). It calls `BeginApproval` with the complete proposed method, target, and security-relevant arguments. The daemon then:
   - runs a non-mutating preflight;
   - canonicalizes the plan into one fixed form;
   - stores a short-lived pending challenge bound to the requesting credential;
   - returns the canonical human-readable plan plus its digest.
2. **Confirm.** The enrolled [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter) proves that it owns the foreground controlling terminal. It displays the daemon-returned plan byte-for-byte, collects an explicit confirmation, and calls `ConfirmApproval(challenge_id)`.
   - Confirmation issues one `HumanApproval` for the already-bound plan.
   - Cancellation or expiry closes the challenge and issues nothing.
3. **Retry with the approval.** The operational client retries the exact method, now carrying the approval id. In one SQLite transaction, the daemon:
   - verifies the caller, method, target, digest, expiry, and unused status;
   - claims the approval into one durable operation journal;
   - only then permits external effects.

The two credentials never stand in for each other:

- The presenter credential works only in phase 2. No operational method accepts it.
- The operation credential is never sufficient for phase 2.
- A challenge cannot be edited after `BeginApproval`. Any changed argument or repository observation requires a new challenge.
- CLI and TUI frontends may implement both roles in one process, but they keep the credentials and [RPC](https://en.wikipedia.org/wiki/Remote_procedure_call) phases distinct.

Foreground-terminal checks and presenter enrollment reduce accidental agent authority. They do not prove user presence against a malicious same-UID process, and v1 does not claim otherwise.

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

The transport checks both the credential's scope and the requested target. Supplying an explicit target never changes the identity the credential conveys.

## Operations that require human approval

The following require a [`HumanApproval`](appendix-a-glossary.md#human-approval) bound to the exact method and target, even when the caller already holds a valid thread credential:

- repo registration with `kk init`;
- thread creation with `kk new`, and `kk reopen`;
- any mutation of a thread other than the caller's contextual thread;
- destructive operations, including thread destroy, repo unregister, discarding pending reconciliation (for example `kk thread detach --discard-pending`), and any repair that deletes or rewrites state;
- repairs that place or re-create the checkpoint bookmark under approval: [`adopt-bookmark`](appendix-a-glossary.md#adopt-bookmark), [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target), [`unhide-checkpoint`](appendix-a-glossary.md#unhide-checkpoint), and the repo-level [`reanchor-history`](appendix-a-glossary.md#reanchor-history). `restore-bookmark` only puts the bookmark back on the expected target, so it needs no approval in the thread's own context; applied to a different thread, it needs a one-shot approval;
- sensitive reads, including another thread's transcript or diff, and repo-wide detailed audit arguments;
- externally visible actions, including publish, remote branch rewriting, PR mutation, and comments;
- process-destructive operations a human requests, such as interrupting or closing a live agent session. The approval covers every process in the listed terminal containers at freeze time, and the rendered plan says so;
- [`terminate-orphans`](appendix-a-glossary.md#terminate-orphans), which ends leftover processes, and [`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server), which stops the whole dedicated server and every process in it;
- topology surgery whose result cannot be derived unambiguously from already recorded intent. (Topology is the shape of the commit graph.)

### Restarts that need no approval

Kiki's own protocol restarts are not on this list.

- The cascade's delivery protocol may retire an [incarnation](appendix-a-glossary.md#incarnation) and start a replacement to deliver a saved payload. That is a daemon-initiated step of a contract the human already accepted by following a thread. It consumes no approval.
- Applying [`restart-agent`](appendix-a-glossary.md#restart-agent) in the thread's own context to a harness that has already exited destroys nothing. It needs no approval either.
- [`retry-close`](appendix-a-glossary.md#retry-close) and [`retry-destroy`](appendix-a-glossary.md#retry-destroy) need no new approval. They continue a plan the human already approved, and they never widen it.

The approval each repair plan needs is listed in one table, [Every issue and its plan](09-commands.md#every-issue-and-its-plan) in Commands. That table is the owner; this chapter states the rules behind it.

### No unattended approval

The CLI displays the exact method, target, and consequential arguments before it asks the foreground user to approve. Non-interactive invocations fail closed: they stop rather than proceed.

v1 provides none of these:

- unattended destructive automation;
- approval-by-config;
- a blanket `--yes`;
- a reusable approval token.

An approval proves that an interactive confirmation happened. Under the cooperative same-UID threat model, it does not prove the confirmer is immune to UI spoofing (a fake prompt). Filesystem [sandboxing](<https://en.wikipedia.org/wiki/Sandbox_(computer_security)>) and OS-backed user presence remain out of scope.

## Sensitive reads

Same-thread [transcript](appendix-a-glossary.md#thread-transcript) reads, once transcript capture ships, use `ThreadScoped<T>`. Reading thread U while authorized as thread T requires a one-shot approval for that exact read. The same rule covers sibling diffs, detailed audit arguments, and any other content that exposes working state.

The repo summary is the only cross-thread read available without approval. See [repo-summary read scope](appendix-a-glossary.md#repo-summary-read-scope). Its complete field set is:

- repo and thread id, display name, bookmark display name, and the followed parent's id/name;
- lifecycle state, three-valued cascade state, [agent display state](appendix-a-glossary.md#agent-display-states), and [checkpoint relationship](appendix-a-glossary.md#checkpoint-relationship) (`current | behind | ahead | diverged`);
- [terminal target](appendix-a-glossary.md#terminal-target) (the dedicated server's address and instance, and the current binding's terminal-group and agent-pane refs), one-line revision description, and the last-agent-event category and timestamp that Activity ordering uses;
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

The CLI resolves a contextual thread as described in [Commands](09-commands.md#context-resolution) and loads only that thread's credential. Outside a thread context, repo-summary reads use a separate [least-privilege](https://en.wikipedia.org/wiki/Principle_of_least_privilege) registration capability. Commands that need stronger authority start an interactive approval flow.

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
- **A Herdr action is not an approval.** A Herdr keybinding, plugin action, or sidebar click may start a `kk` process or request navigation. It is never a `HumanApproval`. It gives that process no authority beyond its own credential. Approval still requires an enrolled `ApprovalPresenter` that owns its foreground terminal.
- **Strong credentials stay out of panes.** Kiki never places an `ApprovalPresenter` or Admin credential in a pane's launch environment, a metadata token, or the generated Herdr configuration.
- **Two measures close the accidental path.** The harness is started with every `HERDR_*` variable removed from its [environment](https://en.wikipedia.org/wiki/Environment_variable). Also, `kkd` refuses a confirmation from a presenter process that is a descendant or session member of any `agent` launcher. An agent that goes looking can still find the socket. These measures close the accidental path, not the deliberate one.

This is the cooperative model again, not enforcement against a same-UID adversary.

## Audit

Every parseable daemon transport attempt produces exactly one authoritative SQLite audit row. The row records:

- the request id;
- the method/path;
- the credential and approval identity, when identifiable;
- the declared scope;
- a compact argument summary;
- the outcome;
- a timestamp.

Where the row goes depends on the request:

- Once a valid target repo is resolved, the row belongs to that repo's `audit_log` table.
- Some requests belong to the per-user `user_audit_log` table in `~/.config/kiki/state.db` instead. These are bootstrap, approval-presenter enrollment, repo listing, registration attempts before a repo exists, unknown-repo targets, and requests that fail before repo resolution.
- Unauthenticated rows may carry null credential/approval ids and keep only a safe fingerprint of the presented identity. Audit logging must not persist raw credentials.

An attempt is written to one sink (destination), never mirrored to both. If the target repo resolves during registration, the registration request stays in the user-level sink where it began. Later repo-scoped calls use the new per-repo sink.

The table is append-only through the daemon API. That is an operational invariant, not tamper evidence. A same-UID process can still edit the database directly.

Who may read the audit log:

- Same-thread non-sensitive slices use thread authority.
- Cross-thread or detailed reads require one-shot human approval.

A future export command may render the SQLite authority as [JSONL](https://jsonlines.org/). But no second audit store is authoritative.

## Remote authority after v1

In the planned remote system, the execution host checks both the device's
grant for the selected profile and the authority required by the method.
Profile membership alone cannot authorize an action. The enrolled host
presenter confirms consequential plans until a remote presenter can meet
its own proof requirements. See [Remote access through profiles](13-architecture/remote-access.md#connecting-and-granting-access).
