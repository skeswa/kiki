# Authority

kiki's v1 authorization model limits the damage an agent can do by accident or through a bug. It does not defend against an actively malicious process running as the same OS user (the same UID). A terminal confirmation prompt is not a security boundary against such a process.

The important v1 property is narrower: a normal `kk` subprocess does not get reusable repo-wide authority just because a human ran it.

## Credential and capability classes

A credential is a secret that proves who a caller is. A capability is a grant to do one specific thing. kiki has four classes.

`ThreadScoped<thread_id>`:

- is bound to one thread — one themed line of work with its own workspace;
- is written to `~/.config/kiki/repos/<repo_id>/credentials/<thread_id>` with mode `0600` (readable only by the owning user);
- is read by `kk-hook`, by the thread's pane launcher, and by any `kk` command whose discovered context is that thread;
- is rotated — replaced with a fresh secret — when an incarnation (one live agent session for the thread) ends, and when a thread reopens;
- authorizes ordinary reads and mutations of that same thread only.

`HumanApproval`:

- is minted by the daemon (`kkd`, the background server) only after a human confirms through an interactive foreground channel;
- is bound to the credential identity, the daemon method, the target repo and thread, a digest (hash) of the security-relevant arguments, and a short expiry;
- is single-use — a single-ride ticket, not a season pass. Exactly one durable operation record claims it, atomically, before any external side effect;
- cannot be refreshed or broadened by a `ThreadScoped` caller.

`ApprovalPresenter`:

- is a local frontend identity, enrolled explicitly through Admin bootstrap;
- is stored outside managed workspaces. kiki never injects it into a harness, a hook, a shell pane environment, or an ordinary operational request;
- may confirm or cancel a pending approval challenge only while its CLI or TUI process owns the foreground controlling terminal — the terminal the user is actively typing into;
- cannot invoke thread operations, widen a challenge, or mint an approval without a daemon-issued challenge.

`Admin` is bootstrap authority. It exists for daemon setup and approval-presenter enrollment, not as ambient CLI authority. An installation may persist an Admin secret outside thread workspaces, but `kk` does not automatically load it for ordinary commands, and agents are never given it. Only explicit bootstrap and recovery endpoints accept Admin; operational thread methods reject it. After enrollment, the daemon authorizes a consequential operation by validating and claiming its `HumanApproval`. It never accepts Admin in place of that capability.

Claiming an approval and performing an external side effect cannot share one transaction. Kiki first claims the approval and creates a durable operation journal in one SQLite transaction. The journal then performs the exact approved plan idempotently — replaying it causes no extra effect — and marks the approval consumed on completion. After a crash, kiki resumes or reconciles that same operation id; it cannot reuse the approval for a second plan. If a remote outcome is unknown, kiki stops and observes. Any change to the method, target, argument digest, or repair/publish plan requires fresh approval.

## Two-phase foreground approval

Consequential commands all use one protocol. A confirmation prompt by itself is not authority:

1. The operational client authenticates with its `ThreadScoped` or registration credential and calls `BeginApproval` with the complete proposed method, target, and security-relevant arguments. The daemon runs a non-mutating preflight, canonicalizes the plan into one fixed form, stores a short-lived pending challenge bound to the requesting credential, and returns the canonical human-readable plan plus its digest.
2. The enrolled `ApprovalPresenter` proves that it owns the foreground controlling terminal. It displays the daemon-returned plan byte-for-byte, collects an explicit confirmation, and calls `ConfirmApproval(challenge_id)`. Confirmation issues one `HumanApproval` for the already-bound plan. Cancellation or expiry closes the challenge and issues nothing.
3. The operational client retries the exact method, now carrying the approval id. In one SQLite transaction, the daemon verifies the caller, method, target, digest, expiry, and unused status; claims the approval into one durable operation journal; and only then permits external effects.

The presenter credential works only in phase 2; no operational method accepts it. The operation credential is never sufficient for phase 2. A challenge cannot be edited after `BeginApproval`; any changed argument or repository observation requires a new challenge. CLI and TUI frontends may implement both roles in one process, but they keep the credentials and RPC phases distinct.

Foreground-terminal checks and presenter enrollment reduce accidental agent authority. They do not prove user presence against a malicious same-UID process, and v1 does not claim otherwise.

## Thread-scoped permissions

A thread-scoped credential may:

- read its own thread state, working-state summary, and non-sensitive audit slice;
- read and advance cascade delivery state — the record of updates flowing from a followed thread — for its own thread, through the specific hook methods;
- perform ordinary same-thread lifecycle or metadata operations that are neither destructive nor externally visible;
- read the minimal same-repo summary and terminal target (where the thread's terminal group currently lives) that `kk ls` and `kk switch` need.

It must not, by itself:

- mutate a sibling or unrelated thread;
- read another thread's transcript, diff, detailed audit arguments, or sync-intent payload;
- destroy or irreversibly discard state;
- publish, close a remote PR, post a comment, force-push, or take any other externally visible action;
- mint approval capabilities or invoke Admin methods.

The transport checks both the credential's scope and the requested target. Supplying an explicit target never changes the identity the credential conveys.

## Operations that require human approval

The following require a `HumanApproval` bound to the exact method and target, even when the caller already holds a valid thread credential:

- any mutation of a thread other than the caller's contextual thread;
- destructive operations, including thread destroy, repo unregister, discarding pending reconciliation, and any repair that deletes or rewrites state;
- sensitive reads, including another thread's transcript or diff, and repo-wide detailed audit arguments;
- externally visible actions, including publish, remote branch rewriting, PR mutation, and comments;
- process-destructive operations, such as interrupting or closing a live agent session;
- topology surgery whose result cannot be derived unambiguously from already recorded intent.

The CLI displays the exact method, target, and consequential arguments before it asks the foreground user to approve. Non-interactive invocations fail closed — they stop rather than proceed. v1 provides no unattended destructive automation, no approval-by-config, no blanket `--yes`, and no reusable approval token.

An approval proves that an interactive confirmation happened. Under the cooperative same-UID threat model, it does not prove the confirmer is immune to UI spoofing. Filesystem sandboxing and OS-backed user presence remain out of scope.

## Sensitive reads

Same-thread transcript reads, once transcript capture ships, use `ThreadScoped<T>`. Reading thread U while authorized as thread T requires a one-shot approval for that exact read. The same rule covers sibling diffs, detailed audit arguments, and any other content that exposes working state.

The repo summary is the only cross-thread read available without approval. Its complete field set is:

- repo and thread id, display name, bookmark display name, and the followed parent's id/name;
- lifecycle state, three-valued cascade state, agent display state, and checkpoint relationship (`current | behind | diverged`);
- terminal target (the dedicated server's address and instance, and the current binding's terminal-group and agent-pane refs), one-line revision description, and the last-agent-event category and timestamp that Activity ordering uses;
- after GitHub integration ships: PR number, PR state, and CI roll-up.

It contains no transcript text, no diff content or paths, no sync-intent payloads or internals, no audit arguments, no prompts, no tool content, no model/context-window telemetry, and no write methods. `kk ls`, `kk switch`, `kk log`, and future read-only renderers all consume this same row set. Adding a field is an authority-model change, not a renderer convenience.

## Command context and switch

The CLI resolves a contextual thread as described in [Commands](09-commands.md#context-resolution) and loads only that thread's credential. Outside a thread context, repo-summary reads use a separate least-privilege registration capability. Commands that need stronger authority start an interactive approval flow.

`kk switch <thread>` does two things: a summary-class lookup of the target thread's terminal target, then a caller-local focus request to the terminal runtime through `TerminalClient`. It moves the invoking viewer's terminal and no other. It does not mutate daemon focus state, and it creates, closes, or changes no terminal resource, so selecting a thread does not require cross-thread mutation approval. Any audit emission records the invoker and the lookup; it does not turn switch into an Admin operation.

Moving someone else's view is a different act. The terminal runtime's public focus methods move every attached client, so kiki uses them only for the explicitly named `kk switch --all-clients`, never as a fallback for the local form. When the caller cannot be tied to one attached client, `kk switch` moves no one. See [Terminal runtime · Caller-local focus](13-architecture/terminal-runtime.md#caller-local-focus).

## Terminal runtime authority

Herdr's socket has a different authority model from kiki's, and kiki does not borrow it. Any same-UID process that can reach the dedicated server's socket can create, close, relabel, or send input to any terminal group. That includes every process running inside a pane, which inherits the socket path. Herdr has no per-thread credential and no plan-bound approval.

Kiki therefore draws the line on its own side:

- Kiki's rules bind kiki's operations. A lifecycle saga closes a terminal group only inside an approved, journaled plan, whatever the runtime would allow an arbitrary caller to do.
- A terminal change kiki did not journal is an external projection change. It is observed, classified, and repaired under the same rules as an out-of-band `jj` command; it is never treated as a kiki decision.
- Nothing read from the runtime is authority. Labels, metadata tokens, working directories, pane placement, and Herdr ids never authorize a mutation, substitute for a credential, or prove that a directory may be deleted. A Herdr ref observed under the current server instance and matching a current binding may _locate_ the caller's contextual thread, as [Commands](09-commands.md#context-resolution) describes; what then authorizes the call is that thread's own credential.
- A Herdr keybinding, plugin action, or sidebar click may start a `kk` process or request navigation. It is never a `HumanApproval`, and it gives that process no authority beyond its own credential. Approval still requires an enrolled `ApprovalPresenter` that owns its foreground terminal.
- Kiki never places an `ApprovalPresenter` or Admin credential in a pane's launch environment, a metadata token, or the generated Herdr configuration.

This is the cooperative model again, not enforcement against a same-UID adversary.

## Audit

Every parseable daemon transport attempt produces exactly one authoritative SQLite audit row. The row records the request id, method/path, credential and approval identity when identifiable, declared scope, a compact argument summary, the outcome, and a timestamp.

- Once a valid target repo is resolved, the row belongs to that repo's `audit_log` table.
- Bootstrap, approval-presenter enrollment, repo listing, registration attempts before a repo exists, unknown-repo targets, and requests that fail before repo resolution all belong to the per-user `user_audit_log` table in `~/.config/kiki/state.db`.
- Unauthenticated rows may carry null credential/approval ids and keep only a safe fingerprint of the presented identity. Audit logging must not persist raw credentials.

An attempt is written to one sink, never mirrored to both. If the target repo resolves during registration, the registration request stays in the user-level sink where it began; later repo-scoped calls use the new per-repo sink.

The table is append-only through the daemon API. That is an operational invariant, not tamper evidence — a same-UID process can still edit the database directly. Same-thread non-sensitive slices use thread authority. Cross-thread or detailed reads require one-shot human approval. A future export command may render the SQLite authority as JSONL, but no second audit store is authoritative.
