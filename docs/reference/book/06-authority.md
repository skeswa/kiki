# Authority

kiki's v1 authorization model reduces accidental and buggy agent blast radius. It does not defend against an actively malicious same-UID process, and a terminal confirmation is not a security boundary against such a process.

The important v1 property is narrower: a normal `kk` subprocess does not receive reusable repo-wide authority merely because it is the human CLI.

## Credential and capability classes

`ThreadScoped<thread_id>`:

- is bound to one thread;
- is written to `~/.config/kiki/repos/<repo_id>/credentials/<thread_id>` with mode `0600`;
- is read by `kk-hook` and by a `kk` invocation whose discovered context is that thread;
- is rotated when an incarnation ends and when a thread reopens;
- authorizes ordinary same-thread reads and mutations only.

`HumanApproval`:

- is minted by the daemon only after confirmation through an interactive foreground human channel;
- is bound to the credential identity, daemon method, target repo and thread, a digest of security-relevant arguments, and a short expiry;
- is single-use and is atomically claimed by one durable operation record before any external side effect;
- cannot be refreshed or broadened by a `ThreadScoped` caller.

`ApprovalPresenter`:

- is a local frontend identity enrolled explicitly through Admin bootstrap;
- is stored outside managed workspaces and is never injected into a harness, hook, shell pane environment, or ordinary operational request;
- may confirm or cancel a pending approval challenge only while its CLI or TUI process owns the foreground controlling terminal;
- cannot invoke thread operations, widen a challenge, or mint an approval without a daemon-issued challenge.

`Admin` is bootstrap authority for daemon setup and approval-presenter enrollment, not ambient CLI authority. An installation may persist an Admin secret outside thread workspaces, but `kk` does not automatically load it for ordinary commands and agents are never given it. Admin is accepted only by explicit bootstrap/recovery endpoints; operational thread methods reject it. After enrollment, the daemon authorizes a consequential operation by validating and claiming its `HumanApproval`, not by accepting Admin in place of that capability.

Approval claim and an external side effect cannot share one transaction. Kiki first claims the approval and creates a durable operation journal in one SQLite transaction. The journal then performs the exact approved plan idempotently and marks the approval consumed on completion. A crash resumes or reconciles that same operation id; it cannot reuse the approval for a second plan. Unknown remote outcome stops for observation, and any changed method, target, argument digest, or repair/publish plan requires fresh approval.

## Two-phase foreground approval

Consequential commands use one protocol; a confirmation prompt by itself is not authority:

1. The operational client authenticates with its `ThreadScoped` or registration credential and calls `BeginApproval` with the complete proposed method, target, and security-relevant arguments. The daemon performs non-mutating preflight, canonicalizes the plan, stores a short-lived pending challenge bound to the requesting credential, and returns the canonical human-readable plan plus its digest.
2. The enrolled `ApprovalPresenter` proves that it owns the foreground controlling terminal, displays the daemon-returned plan byte-for-byte, collects an explicit confirmation, and calls `ConfirmApproval(challenge_id)`. Confirmation issues one `HumanApproval` for the already-bound plan; cancellation or expiry closes the challenge without issuing anything.
3. The operational client retries the exact method with the approval id. In one SQLite transaction, the daemon verifies the caller, method, target, digest, expiry, and unused status; claims the approval into one durable operation journal; and only then permits external effects.

The presenter credential is used only for phase 2 and is never accepted by an operational method. The operation credential is never sufficient for phase 2. A challenge cannot be edited after `BeginApproval`; any changed argument or repository observation requires a new challenge. CLI and TUI frontends may implement both roles in one process, but they keep the credentials and RPC phases distinct.

Foreground-terminal checks and presenter enrollment reduce accidental agent authority; they do not establish user presence against a malicious same-UID process. V1 does not claim otherwise.

## Thread-scoped permissions

A thread-scoped credential may:

- read its own thread state, working-state summary, and non-sensitive audit slice;
- read and advance cascade delivery state for its own thread through the specific hook methods;
- perform ordinary same-thread lifecycle or metadata operations that are neither destructive nor externally visible;
- read the minimal same-repo summary and tmux target needed by `kk ls` and `kk switch`.

It must not by itself:

- mutate a sibling or unrelated thread;
- read another thread's transcript, diff, detailed audit arguments, or sync-intent payload;
- destroy or irreversibly discard state;
- publish, close a remote PR, post a comment, force-push, or perform another externally visible action;
- mint approval capabilities or invoke Admin methods.

The transport checks both credential scope and requested target. Supplying an explicit target never changes the identity conveyed by the credential.

## Operations that require human approval

The following require a method-and-target-bound `HumanApproval`, even when the caller already has a valid thread credential:

- any mutation of a thread other than the caller's contextual thread;
- destructive operations, including thread destroy, repo unregister, discarding pending reconciliation, and any repair that deletes or rewrites state;
- sensitive reads, including another thread's transcript or diff and repo-wide detailed audit arguments;
- externally visible actions, including publish, remote branch rewriting, PR mutation, and comments;
- process-destructive operations such as interrupting or closing a live agent session;
- topology surgery whose result cannot be derived unambiguously from already recorded intent.

The CLI displays the exact method, target, and consequential arguments before asking the foreground user to approve. Non-interactive invocations fail closed. v1 does not provide unattended destructive automation, approval-by-config, a blanket `--yes`, or a reusable approval token.

An approval proves an interactive confirmation occurred; under the cooperative same-UID threat model it does not prove that the confirmer is immune to UI spoofing. Filesystem sandboxing and OS-backed user presence remain out of scope.

## Sensitive reads

Same-thread transcript reads, when transcript capture ships, use `ThreadScoped<T>`. Reading thread U while authorized as T requires a one-shot approval for that exact read. The same rule covers sibling diffs, detailed audit arguments, and other content that exposes working state.

The repo summary is the only cross-thread read available without approval. Its complete field set is:

- repo and thread id, display name, bookmark display name, and follows parent id/name;
- lifecycle state, three-valued cascade state, agent display state, and checkpoint relationship (`current | behind | diverged`);
- tmux session target, one-line revision description, and last-agent-event category and timestamp used for Activity ordering;
- after GitHub integration ships, PR number, PR state, and CI roll-up.

It contains no transcript text, diff content or paths, sync-intent payloads or internals, audit arguments, prompts, tool content, model/context-window telemetry, or write methods. `kk ls`, `kk switch`, `kk log`, and future read-only renderers consume this same row set. Adding a field is an authority-model change, not a renderer convenience.

## Command context and switch

The CLI resolves a contextual thread as described in [Commands](11-commands.md#context-resolution) and loads only that thread's credential. Outside a thread context, repo-summary reads use a separate least-privilege registration capability; commands needing stronger authority start an interactive approval flow.

`kk switch <thread>` consists of a summary-class lookup of the target tmux session followed by `tmux switch-client`. It does not mutate daemon focus state, so selecting a thread does not require cross-thread mutation approval. Any audit emission records the invoker and lookup; it does not turn switch into an Admin operation.

## Audit

Every parseable daemon transport attempt produces exactly one authoritative SQLite audit row with request id, method/path, credential and approval identity when identifiable, declared scope, compact argument summary, outcome, and timestamp.

- Once a valid target repo is resolved, the row belongs to that repo's `audit_log` table.
- Bootstrap, approval-presenter enrollment, repo listing, registration attempts before a repo exists, unknown-repo targets, and requests that fail before repo resolution belong to the per-user `user_audit_log` table in `~/.config/kiki/state.db`.
- Unauthenticated rows allow null credential/approval ids and retain only a safe presented-identity fingerprint; audit logging must not persist raw credentials.

An attempt is written to one sink, never mirrored to both. If the target resolves during registration, the registration request remains in the user-level sink where it began; later repo-scoped calls use the new per-repo sink.

The table is append-only through the daemon API; this is an operational invariant, not tamper evidence against a same-UID process that can edit the database. Same-thread non-sensitive slices use thread authority. Cross-thread or detailed reads require one-shot human approval. A future export command may render the SQLite authority as JSONL, but no second audit store is authoritative.
