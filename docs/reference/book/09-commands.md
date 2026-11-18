# Commands

`kk` is kiki's command-line program (its CLI). It is porcelain, a friendly front end, over the [thread](appendix-a-glossary.md#thread) model. A thread is one line of work: a themed series of [jj](https://docs.jj-vcs.dev/latest/) revisions with its own workspace, terminals, and coding agent.

The `kk` CLI should make common kiki operations obvious. It does not try to replace `jj`, `gh` (the [GitHub CLI](https://cli.github.com/)), or native [Herdr](appendix-a-glossary.md#herdr) use. Herdr is the [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer) that hosts kiki's terminals. Panes, splits, tabs, scrollback, and Herdr's own navigation stay Herdr's; see [Terminal runtime](13-architecture/terminal-runtime.md#native-and-custom-ui).

`kk` does not automatically load reusable [Admin](appendix-a-glossary.md#bootstrap-admin-credential) authority. A credential is the secret a program shows to prove what it is allowed to do. Which credential `kk` shows depends on where it runs:

- **Inside a thread**, it presents that thread's [`ThreadScoped`](appendix-a-glossary.md#threadscoped-credential) credential, which works only for that thread.
- **Outside a thread**, summary-only commands use the repo's [`RegistrationScoped`](appendix-a-glossary.md#registrationscoped) credential, issued at `kk init`. That credential authorizes [repo-summary reads](appendix-a-glossary.md#repo-summary-read-scope) and `BeginApproval` for that repo and nothing else.
- **With an automation credential**, `kk` presents that credential in place of the two above. An [automation credential](appendix-a-glossary.md#automation-credential) is a named secret for scripts and other unattended callers. `kk` uses one only when the caller names it, with `--automation-credential-file <path>` or the `KIKI_AUTOMATION_CREDENTIAL_FILE` environment variable (see [`kk automation`](#kk-automation)).

Kiki is fully [headless](appendix-a-glossary.md#headless): every command in this chapter works with no terminal window attached to kiki's Herdr server, and no command needs the overlay, a popup, or a desktop session. The `kk` CLI and the gRPC service behind it are the complete surface. Whether a command also works with no person present depends on the approval rules below.

Riskier operations enter the one-shot [approval flow](#foreground-approval-flow) defined by [Authority](04-authority.md). "One-shot" means each approval is good for exactly one operation. The approval comes from one of two places: a person who confirms at a foreground terminal, or a rule in the activated [automation policy](appendix-a-glossary.md#automation-policy). The riskier operations are:

- mutating (changing) another thread;
- destructive actions;
- sensitive reads;
- killing a [process](https://en.wikipedia.org/wiki/Process_identifier);
- anything visible outside the machine.

The command sections below call out the consequential cases, but that chapter is normative: where the two differ, [Authority](04-authority.md) decides.

## Context resolution

Many commands act on "the current thread" without being told which one. This section says how `kk` works out which [thread](appendix-a-glossary.md#thread) you mean.

Commands that act on a thread figure out which thread you mean in this order:

1. explicit CLI target
2. `KIKI_THREAD_ID` in the environment
3. Herdr pane identity
4. current working directory

This order selects the target. For the caller’s identity, skip the target argument and resolve the calling environment, verified pane, or working directory. Load only the caller’s credential. Outside a thread, use the repo registration credential where applicable. An explicit automation credential identifies the caller directly. For example, `kk prompt B` run inside A presents A’s credential, even though B is the target. In every case, [`kkd`](appendix-a-glossary.md#kkd) (kiki's background [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>)) authorizes the call against that credential (see [Authority](04-authority.md)).

- **Environment.** Kiki sets the [environment variable](https://en.wikipedia.org/wiki/Environment_variable) `KIKI_THREAD_ID` explicitly on every [role pane](appendix-a-glossary.md#role-pane) it provisions. A role pane is a terminal pane kiki creates for a fixed job, such as running the agent.
  - A value that names no registered thread is an error. It does not fall through to a later step.
- **Herdr pane identity.** [Herdr](appendix-a-glossary.md#herdr) gives every pane `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, `HERDR_PANE_ID`, and `HERDR_SOCKET_PATH`.
  - `kk` uses them only when `HERDR_SOCKET_PATH` is the socket of kiki's [dedicated server](appendix-a-glossary.md#dedicated-herdr-server), the one Herdr server kiki runs for itself.
  - `kk` then asks `kkd` to resolve the Herdr workspace id against the current [server instance](appendix-a-glossary.md#server-instance)'s [terminal bindings](appendix-a-glossary.md#terminal-binding). A terminal binding is kiki's record that ties a thread to its terminals on one run of the server.
  - `kkd` accepts the ids only after it verifies who is calling. It reads the CLI connection's [peer credentials](https://man7.org/linux/man-pages/man7/unix.7.html), which the operating system supplies. From them it verifies that the calling process is a descendant or [session](https://en.wikipedia.org/wiki/Process_group) member of that pane's root process on the current server instance.
  - An id that a process merely claims resolves nothing.
  - This is how a pane the user split natively resolves its thread. Herdr does not copy a role pane's explicit environment into a split, so such a pane has no `KIKI_THREAD_ID`.
  - A pane on the user's default Herdr server resolves nothing here. Neither does an id that matches no current binding.
  - A Herdr id recorded under an earlier server instance never resolves a thread.
  - Pane ids in a pane's environment can go stale after a native pane move. A stale id fails the verification, and resolution falls through to the working directory.
- **Popup and keybinding invocations.** A `kk` process that Herdr starts from a keybinding or as a popup has no `HERDR_PANE_ID`.
  - Herdr supplies `HERDR_ACTIVE_WORKSPACE_ID`, `HERDR_ACTIVE_TAB_ID`, and `HERDR_ACTIVE_PANE_ID` instead.
  - `kkd` verifies the active pane's [terminal group](appendix-a-glossary.md#terminal-group) against the current server instance in the same way. A terminal group is the set of terminals that belongs to one thread.
  - The result is a locator for read-only and navigation commands only.
  - A mutation invoked from a popup still needs the thread credential and, where required, approval.
- **Automation credential.** A caller that presents an [automation credential](appendix-a-glossary.md#automation-credential) is not inside a thread as far as authority goes. Context resolution still locates the thread or repo the command is about, but `kk` loads no thread credential for it.
- **Authority.** A Herdr id never authorizes anything and never substitutes for a credential. A verified ref only locates the caller's contextual thread. The thread's own credential is what authorizes.
- **Working directory.** `kk` matches the canonical current [working directory](https://en.wikipedia.org/wiki/Working_directory) against registered [jj workspace](appendix-a-glossary.md#workspace) paths.

If no thread resolves but the command is repo-scoped, the command may fall back to the registered repo. If no registered repo resolves either, commands that need repo state must return an error explaining how to proceed.

## Foreground approval flow

For some risky operations, kiki requires a fresh approval of each one, right before it runs. That requirement is called [`HumanApproval`](appendix-a-glossary.md#human-approval). This section describes how `kk` gets it.

There are two ways to satisfy it:

- **A person confirms.** A person at a foreground terminal reads the plan and says yes. This is the default, and it is the only way when no policy is active.
- **A policy rule allows it.** [`kkd`](appendix-a-glossary.md#kkd) issues a [`PolicyApproval`](appendix-a-glossary.md#policy-approval) when a rule in the activated [automation policy](appendix-a-glossary.md#automation-policy) allows the exact plan. Wherever this book says an operation needs a `HumanApproval`, a `PolicyApproval` for the same plan satisfies it (see [Authority](04-authority.md#policyapproval)). The few exceptions are listed under [What a policy can never approve](#what-a-policy-can-never-approve).

This chapter says "one-shot approval" when either kind will do. The policy is checked first. A person is asked only when the policy does not allow the plan.

### The steps

When an operation requires a one-shot approval, `kk`:

1. runs a non-mutating preflight through `BeginApproval`, using the credential it already holds: a thread credential, a registration credential, or an automation credential. Two cases have no thread or registration credential to use: `kk init`, and the user-scoped `replace-terminal-server` plan. For those, `kk` uses the automation credential when the caller presents one, and otherwise the user's [Admin bootstrap credential](appendix-a-glossary.md#bootstrap-admin-credential);
2. receives and displays the daemon's canonical view of the request: method, target, consequential arguments, [risk labels](appendix-a-glossary.md#risk-label), [plan digest](appendix-a-glossary.md#plan-digest), and expiry. The same reply carries the daemon's `PolicyDecision` for this plan;
3. gets the approval by the [policy path](#the-policy-path) or the [human path](#the-human-path), as the decision says;
4. retries the exact operation with the issued approval id. The daemon claims that id into one durable operation journal before any external effects happen.

A preflight is a check that runs first and changes nothing. A plan digest is a [fingerprint](https://en.wikipedia.org/wiki/Cryptographic_hash_function) of the exact plan, so a changed plan no longer matches. A risk label is a short fixed name for one dangerous thing a plan does, such as `live-processes` for a plan that ends running processes. `kkd` works out the labels in preflight. [Authority](04-authority.md#risk-labels) owns the full list.

### The policy path

`kkd` compares the plan with the activated policy. It looks at four things: who is calling (the principal), the repo, the operation, and the plan's risk labels. A rule that allows matches only when it accepts every label on the plan. A rule that requires a human ignores the labels. The `PolicyDecision` is one of three values:

- **`Allowed{rule}`.** A rule allows this plan. `kkd` issues a `PolicyApproval` in the same reply. `kk` prints the plan and the line "approved by rule `<name>`", then goes to step 4. It asks nothing.
- **`RequireHuman{rule}`.** A rule says a person must confirm this plan. Such a rule matches whatever risk labels the plan has, and it wins over any rule that allows the plan.
- **`NoMatch`.** No rule covers this plan. An empty or missing policy always gives this answer.

`--confirm` forces the human path even when a rule allows the plan. Every command that can need an approval accepts it.

A `PolicyApproval` is bound to the same things as a `HumanApproval`: the caller's credential, the method, the target repo and thread, and the plan digest. It expires quickly and works once. Each one writes an audit row with the rule name, the policy digest, the principal, the operation, and the risk labels.

### The human path

An automation credential can claim only a policy approval. If its call gets `RequireHuman` or `NoMatch`, or requests `--confirm`, it exits with code 3. A person can begin a fresh plan with their normal command credential.

For such a caller, on `RequireHuman` or `NoMatch`:

1. `kk` verifies that its stdin/stdout terminal is in the [foreground](<https://en.wikipedia.org/wiki/Job_control_(Unix)>).
2. The person confirms or cancels the challenge. `kk` sends the answer with its separately enrolled [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter) credential.

`ConfirmApproval` is refused when the presenter process is a descendant or [session](https://en.wikipedia.org/wiki/Process_group) member of any recorded `agent`-role launcher. So a `kk` started by an agent cannot confirm. An agent gets approvals only from a policy rule whose principal matches its thread credential, either explicitly or through `*`. This is approval hygiene under the cooperative model, not a security boundary.

### When no approval is available

Without a foreground terminal, `kk` never prompts. On `RequireHuman` or `NoMatch` it stops with [exit code](#exit-codes) 3 and changes nothing. The message names:

- the operation;
- the plan's risk labels;
- the reason: no rule matched, or rule `<name>` requires a human.

An automation credential never confirms a human challenge. It is never accepted in place of Admin or the presenter.

### What a policy replaces, and what it does not

A policy replaces one thing: the person's confirmation in step 3. Everything else is the same on both paths:

- the preflight, the canonical plan, and the plan digest;
- the drift and expiry checks;
- single use, and the claim into the operation journal;
- [freeze](appendix-a-glossary.md#freeze), holder scans, the [final proof](appendix-a-glossary.md#final-proof), and [verified exit](appendix-a-glossary.md#verified-exit).

A policy can never make a plan run that a safety proof refuses. A rule that accepts every risk label still gets the same refusal a person would get.

The flow [fails closed](appendix-a-glossary.md#fail-closed): it stops rather than guessing. It stops on any of these:

- plan drift (the plan changed after it was approved);
- expiry;
- terminal loss on the human path;
- cancellation;
- replay (an approval used a second time);
- a process with no foreground terminal and no rule that allows the plan.

### What a policy can never approve

These setup operations never accept a `PolicyApproval`:

- activating a policy (`kk automation apply`);
- creating or rotating an automation credential;
- enrolling or recovering the approval presenter with Admin;
- changing an existing daemon installation.

Presenter enrollment and recovery require explicit Admin and a person at the terminal. For the other setup operations, either the enrolled presenter or explicit Admin can authorize the change. See [`kk automation`](#kk-automation) and [First run](#first-run).

### What does not exist

`--yes`, piped confirmation, environment approval, and reusable approval tokens or files do not exist. Commands never accept a raw approval token from a flag. Unattended approval comes only from the activated policy.

### Admin

Commands do not accept a reusable [Admin](appendix-a-glossary.md#bootstrap-admin-credential) credential from a flag, with three exceptions. These setup commands take `--admin-credential-file <path>`:

- `kk automation apply`;
- `kk automation credential create` and `kk automation credential rotate`;
- [`kk daemon install`](#kk-daemon-install), when it changes an installation that already exists.

This is the path for a machine with no human. Admin is still never loaded automatically and never given to agents.

Explicit Admin bootstrap is used for these things only:

- to enroll or recover an approval presenter;
- to begin the approval for `kk init` when the caller presents no automation credential (see [First run](#first-run));
- to diagnose and begin the approval of the user-scoped `replace-terminal-server` plan when the caller presents no automation credential;
- to activate a policy, to create or rotate an automation credential, or to change an existing daemon installation, on a machine with no presenter.

Operational methods reject Admin and presenter credentials.

## Output for scripts

Scripts and other programs drive kiki through the same `kk` commands a person types. Three rules make that work.

### `--json`

Every read command accepts `--json`. So does every other command, for its final result. Examples are `kk ls`, `kk status`, `kk log`, `kk new`, `kk close`, `kk repair` (both diagnose and apply), `kk automation status`, and `kk thread audit`.

- `--json` changes rendering only. It changes no behavior, no authority, and no approval rule.
- The result is written to [standard output](https://en.wikipedia.org/wiki/Standard_streams) as JSON. A stream, such as `kk events --follow --json`, writes one JSON object per line.
- A failed command also prints its result as JSON, with the reason. For an approval that was needed and not available, the result names the operation, the risk labels, and the reason. The [exit code](#exit-codes) is the same with and without `--json`.

### Views are not the only source

The overlay, the `ui` pane, and Herdr's sidebar are views. Anything they show is also available from a command with `--json`. No command, lifecycle step, or safety proof needs one of them, an attached Herdr client, or a desktop session.

### No prompt without a flag

Every question `kk` can ask for a choice or a value has a flag or an argument that answers it. Examples:

| Question                                          | Answer                                                  |
| ------------------------------------------------- | ------------------------------------------------------- |
| install and start the daemon?                     | run [`kk daemon install`](#kk-daemon-install)           |
| enroll the approval presenter?                    | `kk init --enroll-presenter` or `--no-enroll-presenter` |
| which commit should `choose-bookmark-target` use? | `--target <commit>`                                     |
| which recovery successor should become visible?   | `--target <full-commit-id>`                             |
| which path should `repoint-workspace` record?     | `--path <path>`                                         |
| which outside holder does a deleting plan accept? | `--accept-holder <pid>`                                 |
| which plan should `kk repair` apply?              | `--apply <repair-id>`                                   |
| accept the generated PR text without an editor?   | `kk publish --no-edit` (v1.x)                           |

Without a terminal, `kk` never prompts. When a command cannot go on without an answer, it fails with exit code 2 and names the missing flag. Two rows above have their own outcome: a missing daemon is exit code 5, and `kk init` with no enrollment answer goes on without enrolling a presenter.

Two questions are different, because they are not choices of a value. They are a person's confirmation:

- the confirmation of a one-shot approval;
- [provider-egress consent](appendix-a-glossary.md#provider-egress-consent).

No flag answers either one. Without a person, only a matching rule in the activated policy does.

## Exit codes

Every `kk` command ends with one of these [exit codes](https://en.wikipedia.org/wiki/Exit_status). This chapter owns the list.

| Code | Meaning                                       |
| ---- | --------------------------------------------- |
| `0`  | success                                       |
| `1`  | the operation failed                          |
| `2`  | usage error                                   |
| `3`  | an approval was needed and none was available |
| `4`  | refused by a precondition or a safety proof   |
| `5`  | the daemon is unreachable or not installed    |
| `6`  | timeout                                       |

Notes:

- Code 3 means the plan was valid, and neither a rule nor a person approved it. Nothing was changed. The fix is a policy rule or a person at a terminal.
- Code 4 means kiki refused before or during the work because a check did not pass. Examples are a working agent at close preflight, a stale repair id, plan drift, and `kk switch` with `NoCallerClient`. No policy rule changes a code 4 into a success.
- Code 1 is a failure after the work began. The thread's lifecycle state and `kk repair` say what to do next.
- Code 6 is used by [`kk wait`](#kk-wait) when its `--timeout` runs out.

## First run

A new machine has no running daemon, no enrolled approval presenter, and no active automation policy. This section says how each one comes to exist. Nothing here happens silently.

There are two paths. A machine with a person at a terminal follows the first three subsections. A machine with no person follows [A machine with no human](#a-machine-with-no-human).

### Installing and starting the daemon

The first `kk` command that needs [`kkd`](appendix-a-glossary.md#kkd) finds no daemon to talk to.

- On an interactive terminal, `kk` asks once whether to install and start `kkd`. On a yes, it does what [`kk daemon install`](#kk-daemon-install) does, and then runs the command that was typed.
- On a no, the command exits with code 5 and says how to install the daemon. Nothing is installed.
- When `kk` is not running on a terminal, it does not ask. The command exits with code 5 and names `kk daemon install`. Nothing is installed.
- `kk daemon install` installs and starts `kkd` without asking. It works with or without a terminal.
- The question is asked once. Later commands find the daemon running, or the service manager starts it.

### Enrolling the approval presenter

A person's approval needs an enrolled [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter): the local program that shows a plan to a person at the keyboard and collects the answer.

- `kk init` on a terminal offers to enroll the presenter when none is enrolled. It first shows what is being enrolled, and it enrolls only after the person confirms.
- `kk init --enroll-presenter` answers that question with yes, and `--no-enroll-presenter` answers it with no. The person still confirms the enrollment itself at the terminal.
- The enrollment uses the [Admin bootstrap credential](appendix-a-glossary.md#bootstrap-admin-credential).
- `kk init --recover-presenter` replaces a lost presenter. It also uses the Admin bootstrap credential, shows what it will replace, and needs a foreground terminal.
- A presenter is a program a person uses at a terminal. So without a terminal, no presenter is enrolled, and `--enroll-presenter` or `--recover-presenter` is a usage error.
- A policy rule can never enroll or recover a presenter.
- A machine can run with no presenter at all. Then every approval comes from the activated policy, and an operation with no matching rule fails closed with exit code 3.

### Which credential begins registration

An approval is normally begun with a thread credential or a repo's registration credential. During `kk init`, neither exists yet: the registration credential is issued only when the registration completes.

- When the caller presents an [automation credential](appendix-a-glossary.md#automation-credential), `kk init` begins its approval with that credential, not with Admin. The policy then needs a rule that allows the `init` operation for that credential.
- Otherwise the approval for `kk init` is begun under the user's [Admin bootstrap credential](appendix-a-glossary.md#bootstrap-admin-credential).
- Admin only begins the challenge. It is not a policy principal, so the enrolled presenter still confirms the challenge on a foreground terminal. The registration still consumes the one-shot approval.
- Enrolling the presenter and beginning this approval are the only things `kk init` uses Admin for. Once a repo is registered, its commands use the registration, thread, or automation credential.

### A machine with no human

On a supported host with a user service manager, a setup script can use these commands without a terminal. On a qualified host without a service manager, start supervised `kkd --foreground` in place of the first command and use the Admin path it logs.

1. `kk daemon install` installs and starts `kkd`. It creates the Admin bootstrap credential and prints the path of the credential file.
2. `kk automation apply --admin-credential-file <path>` activates the `[automation]` policy written in the user config file.
3. `kk automation credential create <name> --admin-credential-file <path>` creates an automation credential and prints the path of its file.
4. `kk init`, run with that automation credential, registers a repo. Every later command uses the automation credential too.

For example:

```sh
kk daemon install
kk automation apply --admin-credential-file ~/.config/kiki/admin-cred
kk automation credential create ci --admin-credential-file ~/.config/kiki/admin-cred
export KIKI_AUTOMATION_CREDENTIAL_FILE=~/.config/kiki/automation/ci.cred
kk init
kk new fix-login -m "Fix the login redirect"
```

The Admin path in the example stands for whatever path `kk daemon install` printed.

- No presenter needs to be enrolled on such a machine.
- Every consequential thing the automation credential does goes through the policy. An operation with no matching rule fails closed with exit code 3.
- The Admin credential file is used for steps 2 and 3 and for later policy or credential changes. The operator keeps it away from agents and scripts that do not need it. Kiki never loads it automatically.

## `kk daemon install`

`kk daemon install` installs [`kkd`](appendix-a-glossary.md#kkd) and starts it. It asks nothing, so it works from a script and without a terminal. It ships in the [acceptance slice](appendix-a-glossary.md#acceptance-slice).

- It installs `kkd` under the user's service manager: [launchd](https://en.wikipedia.org/wiki/Launchd) on macOS, a [systemd](https://en.wikipedia.org/wiki/Systemd) user unit on Linux. Then it starts the daemon.
- A first install creates the [Admin bootstrap credential](appendix-a-glossary.md#bootstrap-admin-credential) and prints the path of its file. The file is outside every managed workspace.
- A first install requires both the service definition and prior bootstrap state to be absent. A missing definition alongside existing state reports an incomplete installation and preserves the existing Admin identity. A first install needs no approval and no credential. No daemon exists yet to give an approval, and the command registers no repo and starts no agent.
- A rerun first resumes any pending installation journal. Once the requested daemon is verified and no change is pending, it reports that the daemon is installed and running, prints the same credential path, and creates no second credential.
- A later run that would change an existing installation, such as replacing the service definition after an upgrade, needs a confirmation at a foreground terminal or `--admin-credential-file <path>`.
- With `--json`, the result includes the service state and the credential path.
- It exits with code 0 once the requested daemon answers and any installation journal has completed. It exits with code 4 when the host has no supported user service manager, and the message names `kkd --foreground`.

On a changed install, `kk` starts the existing service definition if needed and contacts that daemon. If it cannot reach the daemon it exits with code 5 and leaves the definition in place. The bootstrap call binds the change to the installed and proposed definitions. An identical rerun after a lost reply resumes the same change. The initial install question is local to `kk`. The first approval for a repo is its registration by `kk init`.

### Hosts with no user service manager

Many containers and CI ([continuous integration](https://en.wikipedia.org/wiki/Continuous_integration)) runners have no launchd and no systemd user session. On such a host the operator runs `kkd --foreground` under whatever supervisor the host already uses.

- `kkd --foreground` stays attached to the process that started it and does not register a service.
- On its first start it creates the Admin bootstrap credential and logs the path of its file. This does what a first `kk daemon install` does on other hosts.
- It starts the dedicated Herdr server as a detached process in its own [session](https://en.wikipedia.org/wiki/Process_group), and must pass the survival test below under the actual supervisor.

Two things here are [acceptance gates](appendix-a-glossary.md#acceptance-gate), not established facts:

- **Survival under `kkd --foreground`.** The Herdr server and the agents must outlive a `kkd` crash in this mode, as they must under a service manager. A platform mode that fails this proof is unsupported.
- **macOS over SSH with no GUI login.** There `kk daemon install` uses launchd's per-user domain, not the GUI domain. That this domain keeps `kkd` and the server running is not yet proven.

## `kk automation`

`kk automation` manages the two things that let kiki work with no person present: the activated [automation policy](appendix-a-glossary.md#automation-policy) and the [automation credentials](appendix-a-glossary.md#automation-credential). It ships in the [acceptance slice](appendix-a-glossary.md#acceptance-slice).

| Command                                  | What it does                                         | What it needs                    |
| ---------------------------------------- | ---------------------------------------------------- | -------------------------------- |
| `kk automation apply`                    | activates the policy written in the user config file | presenter confirmation, or Admin |
| `kk automation status`                   | shows the active policy and whether the file differs | nothing                          |
| `kk automation revoke`                   | clears the active policy                             | no approval                      |
| `kk automation credential create <name>` | creates a named automation credential                | presenter confirmation, or Admin |
| `kk automation credential rotate <name>` | replaces that credential's secret                    | presenter confirmation, or Admin |
| `kk automation credential revoke <name>` | makes that credential stop working                   | no approval                      |
| `kk automation credential list`          | lists the credentials                                | nothing                          |

The two revoke commands only remove authority. They need no approval, and any credential of this user may call them: a thread, registration, or automation credential, or Admin. The status and list commands accept the same credentials.

The policy itself is the `[automation]` table in the user config file. [Configuration](11-configuration.md#automation-keys) owns its keys, and [Authority](04-authority.md#automation-policy) owns what a rule means.

### `kk automation apply`

Editing the config file does nothing by itself. A policy takes effect only when it is activated, and `kk automation apply` is the one way to activate it (see [Authority](04-authority.md#activating-a-policy)).

1. `kk` reads the `[automation]` table from the user config file. No other config layer can set it.
2. `kkd` puts the policy in one canonical form and computes a policy digest, a fingerprint of that exact policy.
3. The activation is confirmed in one of two ways:
   - **By a person.** On a foreground terminal, the enrolled `ApprovalPresenter` shows the full canonical policy and a diff against the active one. The person confirms or cancels.
   - **By Admin.** `--admin-credential-file <path>` presents the Admin bootstrap credential. This is the path for a machine that never has a person.
4. `kkd` stores the policy as the active one. From then on it evaluates only the stored copy, never the file.

More rules:

- A `PolicyApproval` can never activate a policy. A policy cannot widen itself.
- Without a foreground terminal and without `--admin-credential-file`, the command exits with code 3 and names that flag.
- A policy that does not parse, or that names an unknown operation or risk label, is refused with exit code 2. The active policy stays as it was.
- This step is the reason an agent cannot grant itself authority by editing a config file. As with presenter enrollment, it is hygiene under the cooperative same-user model, not a security boundary.

The policy can be as wide as the user wants, including `principals = ["*"]`, `operations = ["*"]`, and `accept = ["*"]`. That policy allows any matching local credential to approve policy-eligible plans except provider consent, and the confirmation screen says so.

### `kk automation status`

`kk automation status` shows:

- the active policy, in its canonical form;
- its digest;
- who activated it (`Presenter` or `Admin`) and when;
- whether the `[automation]` table in the file now differs from the active policy.

A file that differs is not an error. It means the edit has not been applied, and the old policy is still the one in force. `kk doctor` reports the same difference when it ships.

### `kk automation revoke`

`kk automation revoke` clears the active policy. After it, no rule matches, and every approval needs a person again.

It only removes authority, so it needs no approval. The file is not changed. A later `kk automation apply` activates the file's policy again, with a fresh confirmation.

A revoke stops new approvals. A `PolicyApproval` that `kkd` already issued stays valid until its short expiry. Revoking the credential it is bound to is different: that approval can then no longer be claimed.

### `kk automation credential`

An automation credential is a named secret that a script, a CI job, or another unattended caller presents to `kkd`.

- **`create <name>`** creates the credential and writes it to `~/.config/kiki/automation/<name>.cred` with mode 0600. It prints that path. It needs the same confirmation as `kk automation apply`: the presenter on a foreground terminal, or `--admin-credential-file <path>`. A `PolicyApproval` never satisfies it.
- **`rotate <name>`** replaces the secret in the same file. The old secret stops working at once. It needs the same confirmation as `create`.
- **`revoke <name>`** makes the credential stop working. It only removes authority, so it needs no approval. A `PolicyApproval` bound to the credential can no longer be claimed.
- **`list`** shows each credential's name and the times it was created, rotated, and revoked. It never prints a secret.

A caller presents the credential in one of two ways:

- the environment variable `KIKI_AUTOMATION_CREDENTIAL_FILE=<path>`;
- the flag `--automation-credential-file <path>`, which every `kk` command accepts.

What the credential is:

- It belongs to the user, not to one repo or thread. A policy rule names it as the principal `credential:<name>`.
- For repo and thread work it starts with these permissions. It can also look up its own prompt receipts and use the local status, list, and revoke commands.
  - read the repo summary of every registered repo;
  - read each registered thread's status and non-sensitive state. That is what `kk status`, `kk ls`, `kk events`, `kk wait`, and `kk repair` without `--apply` need. A sensitive read, such as a transcript or a diff, still needs a rule that allows `sensitive-read`;
  - call `BeginApproval` for any registered repo or thread, for `kk init`, and for the user-scoped `replace-terminal-server` plan.
- Everything consequential it does goes through the policy. With no matching rule, the operation fails closed.
- It is no thread's own credential. So even an ordinary change that a thread makes to itself with no approval, such as a checkpoint, needs a one-shot approval when this credential makes it. In a policy rule that operation is `thread-op` (see [Authority](04-authority.md#the-thread-op-operation)).
- It never confirms a human challenge. It is never accepted in place of Admin or the presenter.
- The file lives outside every managed workspace. Kiki never puts it into a harness, a hook, or a pane's environment.

### Audit

Policy activation and revocation, and credential creation, rotation, and revocation, are each recorded in the per-user `user_audit_log`. Read them with [`kk audit log --user`](#kk-audit).

## `kk init`

`kk init` opts a git+jj repository into kiki management. A repository must be registered this way before kiki manages threads in it.

### What it checks

It verifies prerequisites:

- [jj](https://docs.jj-vcs.dev/latest/) is initialized, hard error if not. The message names `jj git init --colocate` as the typical fix. (A [colocated](https://docs.jj-vcs.dev/latest/git-compatibility/) repository holds jj and [Git](https://git-scm.com/) data side by side.)
- [`kkd`](appendix-a-glossary.md#kkd) can write the per-repo state directory at `~/.config/kiki/repos/<repo_id>/`, hard error if it cannot.
  - kiki writes nothing into the source repo itself.
  - The only kiki file that may live there is the optional committed `<repo>/.kiki.toml` (the repo-shared config layer), and `kk init` does not create it.

### What it does not check

`kk init` does not require `gh`, network access, or GitHub authentication. Those checks happen lazily at `kk publish`. Once publishing ships, `kk doctor --github` is the explicit non-mutating preflight.

`kk init` does **not** verify that any specific harness binary is installed. A [harness](appendix-a-glossary.md#harness) is the coding-agent program kiki runs inside a thread. The harness contract is pluggable (see [Harness adapter](13-architecture/harness-adapter.md)).

- v1 ships the `claude-code` and `codex` adapters, for [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) and [Codex](https://github.com/openai/codex).
- kiki does not refuse registration on a host with no harness installed.
- The check happens at `kk new` instead: spawning a thread errors if the configured default harness's binary is missing.

### Approval

On a terminal, `kk init` offers to enroll the foreground approval presenter when none is enrolled. It shows what is being enrolled first, and it uses [Admin bootstrap](appendix-a-glossary.md#bootstrap-admin-credential) for that one step (see [First run](#first-run)). `--enroll-presenter` and `--no-enroll-presenter` answer the question ahead of time. Without a terminal, `kk init` asks nothing and enrolls no presenter.

Registering a repo is a one-shot approved operation (see [Foreground approval flow](#foreground-approval-flow)). The approval is bound to the repo's canonical path and derived repo id. In a policy rule the operation is `init`. The repo has no registration credential yet, so the approval is begun in one of two ways:

- **With an automation credential.** When the caller presents an [automation credential](appendix-a-glossary.md#automation-credential), `kk init` begins the approval with it. The registration runs when a rule allows `init` for that credential. The repo has no id yet, so the rule's `repos` must match it by canonical path or by `*`.
- **With Admin.** Otherwise the approval is begun under the user's Admin bootstrap credential. Admin is not a policy principal, so no rule matches, and the enrolled presenter confirms on a foreground terminal.

Without a terminal and without a rule that allows the plan, `kk init` exits with code 3 and registers nothing.

`kk init --recover-presenter` replaces a lost presenter using the Admin bootstrap credential. It registers nothing.

`kk init` never turns bootstrap Admin into ambient CLI authority. The already-registered idempotent path is read-only and needs no new approval.

### Running it again

`kk init` is [idempotent](https://en.wikipedia.org/wiki/Idempotence) in an already-registered repo: running it again changes nothing. It prints a status summary and exits with [status](https://en.wikipedia.org/wiki/Exit_status) 0. The summary shows:

- registration path and time;
- active and closed thread counts;
- state.db location.

Re-registering after `kk repo unregister` is the explicit re-registration path.

`kk init` does not create a starter thread. Thread creation is explicit.

## `kk`

What `kk` does with no arguments depends on whether the TUI has shipped and on where you run it.

- Bare `kk` opens the [overlay TUI](appendix-a-glossary.md#overlay-tui) in `NAVIGATE` mode (see [Interface](10-interface/spec.md)) once the TUI ships. A TUI is a [text-based user interface](https://en.wikipedia.org/wiki/Text-based_user_interface) drawn inside the terminal.
- Whenever no overlay is available, bare `kk` prints the [`kk ls`](#kk-ls) listing. That covers three cases: before the TUI ships, outside a registered repo, and when `kk` is not running on an interactive terminal.

## `kk new`

`kk new [<name>]` creates a [thread](appendix-a-glossary.md#thread), as specified in [Threads](03-threads.md).

### The name

`<name>` is optional. It sets the thread's display name and its bookmark name.

- With `<name>`, the thread uses that name. The name is human-owned, so the v1.x [auto-rename](appendix-a-glossary.md#auto-rename) feature never changes it.
- Without `<name>`, the thread gets the placeholder name `unnamed-<short-hex>`, which kiki owns. In the [acceptance slice](appendix-a-glossary.md#acceptance-slice) this is true even when a prompt is supplied.
- Deriving a name from the prompt is v1.x work.

### Approval

Thread creation requires a one-shot [approval](#foreground-approval-flow). In a policy rule the operation is `new`. The approval is bound to:

- the resolved base/head;
- the follows choice;
- the workspace path;
- the harness and its ordered, resolved arguments, including the permission and sandbox settings the launcher will use;
- a digest of the initial input.

Resolve settings before approval. Save and launch that exact argument list. A change between preflight and claim invalidates the plan.

With no policy rule, only a person at a foreground terminal can approve a new thread. So by default an agent cannot spawn one. An agent can create threads only when the activated policy has a rule that allows `new` for the `thread:any` or `*` principal. Neither path gives the CLI reusable Admin authority.

Without a terminal and without a rule that allows the plan, `kk new` exits with code 3 and creates nothing.

### Flags

Important flags:

- `--follows <parent>` creates a live [follows](appendix-a-glossary.md#follows) edge: a link that makes this thread track a parent thread;
- `--no-follow` suppresses contextual following;
- a request to make the new thread follow another is refused when the new thread's harness failed its [`RestartStartup`](appendix-a-glossary.md#restartstartup-delivery-proof) proof. That harness runs managed sessions without cascade delivery, so its threads cannot follow. The refusal names that reason. This covers `--follows <parent>` and the contextual default alike; `--no-follow` creates the thread with no edge;
- `-m "<prompt>"` supplies an initial prompt, delivered to the [harness](appendix-a-glossary.md#harness) as the first user turn;
- `--harness <name>` selects a harness for the thread;
- `--harness-arg <arg>` passes harness-specific arguments;
- `--ui-pane` / `--no-ui-pane` are reserved for the v1.x [`ui` role pane](appendix-a-glossary.md#ui-role-pane), the optional pane that keeps the Stack tree permanently visible (see [Interface](10-interface/spec.md#ui-pane)). They override `[ui] ui_pane` for one thread. Herdr's native sidebar is not controlled by these flags.

### The initial prompt

The initial prompt can come from `-m` or [stdin](https://en.wikipedia.org/wiki/Standard_streams) (standard input).

- If both are supplied, `-m` wins.
- If neither is supplied, `kk new` proceeds without an initial prompt, and the agent starts with no first-turn input.

It is fine to spawn a thread before you know what it is about.

### Terminals and focus

`kk new` provisions the thread's [terminal group](appendix-a-glossary.md#terminal-group) on the [dedicated Herdr server](appendix-a-glossary.md#dedicated-herdr-server) whether or not any client is attached. A client is one terminal window that is viewing the server.

After the thread is `Active`, `kk` requests [caller-local focus](appendix-a-glossary.md#caller-local-focus) on the new agent pane under the same contract as [`kk switch`](#kk-switch). Caller-local focus moves only the view of the person who ran the command. That request is navigation, not part of the creation [saga](appendix-a-glossary.md#saga) (the journaled series of steps that creates the thread). If no caller client resolves or the capability is missing:

- creation still succeeds;
- nobody's view moves;
- `kk` prints how to reach the thread (`kk attach <thread>`).

That is the normal case for a script, and it is not an error: `kk new` still exits with code 0. With `--json`, the result carries the new thread's id and name, so the script can pass them to later commands.

Provisioning itself must move no attached client's view. That is the contract for `kk new`, `kk reopen`, a repair restart, and duplicate cleanup alike. The only view that may move is the caller's, through the explicit focus request above.

This is an [acceptance gate](appendix-a-glossary.md#acceptance-gate), not an established fact. Herdr's create and layout calls default to not taking focus, but the behavior has not been run with clients attached. Three exceptions are already known from source and sit inside the gate:

- the first Herdr workspace created on an empty server takes focus;
- applying a layout over the tab a client is viewing switches that client to the new tab;
- a client viewing a replaced tab falls back to the server default.

See [Terminal runtime](13-architecture/terminal-runtime.md#what-exists-what-kiki-builds-what-herdr-must-add).

### Transcript

When v1.x [transcript](appendix-a-glossary.md#thread-transcript) capture is enabled, the first-turn prompt is projected as `author=human`, `direction=inbound_to_agent`. Thread creation does not depend on that projection.

## `kk prompt`

Use `kk prompt <thread> -m "Run the unit tests" --request-id <uuid> --json` to start a later user turn in the running conversation. The caller supplies the text with `-m` or standard input, with the same precedence as `kk new`. Empty input is a usage error. The request id is optional for a single submission. A script that might reconnect supplies its own id before the first attempt and reuses it with the same thread and text.

Every submission needs a one-shot approval for the `prompt` operation. The plan shows the target thread and quoted prompt, and binds the exact bytes, request id, and live incarnation. A thread calling across threads also needs the `cross-thread` risk label. The daemon records the claim before submitting. Summary events and audit arguments omit the text.

The harness must accept the text as a fresh user turn in that incarnation while it is ready for one. A busy agent, permission question, active workspace mutation, hard pause, incomplete tool batch, repair, or missing adapter proof returns code 4. A cascade waiting for the next safe hook may need this turn to make progress. In particular, when a completed batch has left an intent `Delivered`, the caller can submit the next user turn. Only the normal later hook can acknowledge the intent. Kiki sends no keystrokes and queues nothing for later. An expired approval requires a fresh plan. A new submission to a replacement agent needs a fresh plan and request id.

Success returns the request id, thread id, incarnation id, and harness turn receipt. It means the harness accepted the turn. The agent may still be working. If the connection breaks, repeat the request with the same id. With a replaced credential, reuse of an existing id is refused (code 4). With the original credential, the caller gets the recorded outcome or an explicit unknown outcome (code 1) while acceptance cannot be proved. Kiki never resubmits an uncertain request to another incarnation.

## `kk switch`

`kk switch <thread>` moves your terminal view to another thread. More exactly, it moves the caller's [Herdr client](appendix-a-glossary.md#herdr-client), the terminal view the person who ran the command is attached with, to the target thread's agent pane. It moves that one client and no other.

See [Terminal runtime · Caller-local focus](13-architecture/terminal-runtime.md#caller-local-focus) for the mechanism and [Authority](04-authority.md) for why it needs no approval.

### Steps

The command runs entirely in `kk`, through [`TerminalClient`](appendix-a-glossary.md#terminalclient):

1. **Look up the target.** A summary-class read returns the thread's [terminal target](appendix-a-glossary.md#terminal-target):
   - the [dedicated server](appendix-a-glossary.md#dedicated-herdr-server)'s session;
   - the server process's peer identity `(pid, start_time)` that kiki recorded as the current [server instance](appendix-a-glossary.md#server-instance);
   - the current [binding](appendix-a-glossary.md#terminal-binding)'s [terminal group](appendix-a-glossary.md#terminal-group) and agent pane refs.

   A thread with no current binding has no terminal target. `kk switch` then fails and names the reason. A `Closed` thread points to `kk reopen`. A thread with a [`TerminalMissing`](appendix-a-glossary.md#terminalmissing) issue points to `kk repair`.

2. **Verify the instance.** `kk` connects to the dedicated server and checks that the socket's peer is that recorded `(pid, start_time)`. A mismatch fails the command. A ref from another instance is never used.
3. **Resolve the caller.**
   - For a command typed in a pane, the caller is the foreground client. It is accepted only when that client is currently showing the pane the command runs in.
   - For a keybinding or plugin invocation, the caller is the client id Herdr supplies. Keybinding-invoked switch ships with the v1.x overlay.
4. **Focus.** `kk` asks Herdr to move that client to the target pane.

### Outcomes

Outcomes:

- **Focused.** The caller's client now shows the target thread. Other attached clients are unchanged.
- **`NoCallerClient`.** No attached client can be identified as the caller. This happens when the command ran from an agent's tool call, a script, a pane nobody is viewing, or a terminal that is not attached to the kiki server. `kk switch` moves no one, exits with [code](#exit-codes) 4, and names `kk attach <thread>` as the way to open a view on that thread.
- **Missing capability.** [Caller-local focus](appendix-a-glossary.md#caller-local-focus) requires the Herdr extension [`client_targeted_focus`](appendix-a-glossary.md#client-targeted-focus), which the server advertises as a capability. It is a required extension, not an optional one. When the server does not advertise it, `kk switch <thread>` fails with a message that names `client_targeted_focus` and moves no one.

### Moving every client

`kk switch --all-clients <thread>` is a separate, explicit operation.

- It moves every client attached to the kiki server to the target through Herdr's public focus method, and its output says so.
- It needs neither a resolved caller nor `client_targeted_focus`.
- Kiki never substitutes it for the caller-local form: not as a fallback, not by configuration, and not from the overlay's `enter`.

### What it never does

`kk switch` performs no terminal mutation:

- it creates no pane;
- it does not re-create a closed `shell` or `ui` pane;
- it starts no agent;
- it repairs nothing.

It does not mutate daemon focus state either. [`kkd`](appendix-a-glossary.md#kkd) does not own focus, records no current thread, and exposes no mutating `Switch` RPC ([remote procedure call](https://en.wikipedia.org/wiki/Remote_procedure_call)).

## `kk attach`

`kk attach [<thread>]` opens a [Herdr](appendix-a-glossary.md#herdr) client on kiki's [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) in the current terminal. It is how a terminal becomes a view onto kiki's threads. The user passes no Herdr options.

- `kk attach` first asks [`kkd`](appendix-a-glossary.md#kkd) to ensure the dedicated server is running. Only `kkd` starts the server, and it verifies the server's version and capabilities.
- `kk` then runs Herdr's connect-only client for kiki's named session (`[terminal] session`, default `kiki`), with `HERDR_CONFIG_PATH` set to kiki's generated configuration file.
  - It never uses a client entry point that would start a server on its own.
  - So it cannot create a server `kkd` did not start, and it cannot land on the user's default Herdr server.
- With `<thread>`, the new client opens on that thread's agent pane.
  - Placement applies to the new client only.
  - If the runtime cannot place one client without moving the others, `kk attach` attaches at Herdr's default location and says so. It never uses the broadcast focus method.
  - A thread with no [terminal target](appendix-a-glossary.md#terminal-target) is reported the same way as in `kk switch`, and the client still attaches.
- Without `<thread>`, the client opens wherever Herdr places a new client. `kk attach` does not apply [context resolution](#context-resolution).
- Run from a pane that is already inside the kiki server, `kk attach` refuses to nest a client and points to `kk switch`.
- It requires an interactive terminal, because it opens a view for a person. Without one it exits with code 4. No other command needs a client to be attached.

The dedicated server is a separate server process, socket, saved session, and configuration file. It is not a separate directory tree: Herdr keeps the named session's socket and saved state under its own directories, keyed by session name.

### Attaching changes nothing

Attaching is a view, not a lifecycle event. It changes no thread state, starts no agent, and proves nothing about any thread.

In particular, `kk attach` can cause `kkd` to start the server after a reboot or a server stop. Herdr then restores layouts as [remnant containers](appendix-a-glossary.md#remnant-container): restored terminals that kiki never adopts or reuses. In that case:

- every affected thread shows a [`TerminalMissing`](appendix-a-glossary.md#terminalmissing) issue until `kk repair` restarts it;
- none is `Active` (see [Terminal runtime](13-architecture/terminal-runtime.md#runtime-changes-are-reconciliation)).

A running [server instance](appendix-a-glossary.md#server-instance) that `kkd` did not start is unverified. That includes the server left by Herdr's own handoff or upgrade. `kkd` provisions nothing on it, and the threads that were bound to the old server read `TerminalMissing`. The fix is the approved [`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server) plan (see [`kk repair --server`](#the-terminal-server-replace-terminal-server)), and after it `restart-terminal` for each thread.

Detaching and reattaching a client changes nothing in kiki's state.

## `kk ls`

`kk ls` lists your threads and the state each one is in.

It lists operational threads: `Active` threads plus threads in visible creation, close, failure, and projection-repair states. (See [thread lifecycle states](appendix-a-glossary.md#thread-lifecycle-states).) Every non-Active row includes its lifecycle label spelled out in text; color is never the only signal. `Closed` stays outside the default lifecycle scope, with one exception.

The exception is a reopen in progress. A `Closed` thread with a `Reopen` operation in progress appears in the default listing, marked with the `…` glyph and the words that say a reopen is running. The overlay shows the same row.

### Where the list comes from

`kk ls` reads kiki's state, not Herdr's. It works with no client attached and with the [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) stopped.

- A thread whose [terminal group](appendix-a-glossary.md#terminal-group), [server instance](appendix-a-glossary.md#server-instance), or agent role is gone is listed as `ProjectionDiverged` with the reason [`TerminalMissing`](appendix-a-glossary.md#terminalmissing).
- A thread with an [orphan](appendix-a-glossary.md#orphan) is listed with the reason [`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess). An orphan is one of two things: a recorded process that is alive with no current binding and outside every container on the current server instance, or a [harness remnant](appendix-a-glossary.md#harness-remnant). A harness remnant is a process left behind by a harness that already ended.
- Neither is ever listed as `Active`, whatever Herdr's sidebar or a restored pane shows.
- A thread whose [harness](appendix-a-glossary.md#harness) crashed under a live launcher stays `Active` with the agent state shown as blocked.

`kk ls --all-repos` reads each repo with that repo's registration credential.

### Scope

Repo scope and lifecycle scope are independent:

- Inside a registered repo, the default scope is the current repo.
- Outside a registered repo, the default scope is all registered repos, and the output includes a `repo` column.
- `--all-repos` widens repo scope from the current repo to all registered repos.
- `--all` adds closed threads to the operational states. A closed thread with an open [`CheckpointAbandoned`](appendix-a-glossary.md#checkpointabandoned) issue is shown here with that reason. It is not a loud attention event.
- Destroyed threads stay hidden unless an explicit destroyed-thread flag is added.

`--all` must not change repo scope.

## `kk log`

`kk log` shows revision history arranged by thread. It is [stack-aware](appendix-a-glossary.md#stack-aware-collapse) revision porcelain: a smaller, thread-aware view of revision history. It keeps its surface smaller than `jj log` and decorates the thread model kiki owns.

### What it shows

- By default it expands the current thread plus its [follows](appendix-a-glossary.md#follows) ancestors (the threads it tracks, directly or through other threads).
- Siblings, descendants off the current line, and unrelated threads collapse to summaries.
- `--no-stack` expands only the current thread.
- `--all` includes closed threads as collapsed lines.
- `--wide` (`-w`) enriches collapsed summaries.
- `-r <revset>` passes through to jj [revset](https://docs.jj-vcs.dev/latest/revsets/) selection (jj's query language for picking revisions). It disables collapse logic, and it errors if combined with `--no-stack`, `--all`, or `--wide`.

Collapsed line format:

- Default: `<status-glyph> <bookmark> [#<pr>] <agent-glyph> "<last-revision-description>"`.
- `--wide`: adds the literal PR state (`draft`, `ready`, `merged`, `closed`), a CI roll-up, agent state with age, and relative last activity.

A PR is a GitHub [pull request](https://docs.github.com/en/pull-requests). CI is [continuous integration](https://en.wikipedia.org/wiki/Continuous_integration), the automated checks that run on a PR.

PR number, PR state, and CI fields appear only after their v1.x integrations ship. The acceptance renderer omits unavailable fields instead of printing placeholders.

### Only one jj-shaped flag

`kk log` adopts no other jj-log flags: `-r <revset>` is the only jj-shaped flag in v1. Other `jj log` affordances (patches, templates, reverse order, custom color) remain direct `jj log` usage. This avoids a near-mirror CLI that drifts as jj evolves.

The escape hatch for arbitrary revision selection is `jj` itself. kiki decorates the model it owns; it does not clone every flag of the tools beneath it.

### Without a current thread

Inside a registered repo with no resolved thread, `kk log` renders the trunk in detail and every thread in the repo as a collapsed line. It prints them under a header line that says no current thread was resolved.

Outside a registered repo, `kk log` errors and points to `kk ls`.

### Where the data comes from

Revision lines are repository data that any workspace can already read with `jj log`. Only the per-thread decorations come from kiki's summary rows (see [Authority](04-authority.md)).

## `kk status`

`kk status` shows the state of the current thread. It prints a kiki header followed by the literal output of `jj st`.

### Two parts, made differently

The two parts are produced differently:

- **The header** comes from [`kkd`](appendix-a-glossary.md#kkd) and uses [pinned reads](appendix-a-glossary.md#pinned-read) only: every jj read names an exact [operation](https://docs.jj-vcs.dev/latest/operation-log/) id and ignores the [working copy](https://docs.jj-vcs.dev/latest/working-copy/). `kk status --no-jj` prints only this part and never touches the working copy.
- **The body** is an explicit, human-invoked passthrough.
  - The `kk` CLI, never `kkd`, runs `jj st` (and the `--diff` forms) in the caller's own contextual jj workspace, exactly as if the human had typed it.
  - Like any direct jj use it may snapshot the working copy. (A snapshot is jj recording the current files as a commit.)
  - It is allowed only for an explicit user command against the caller's contextual workspace.
  - It is one of the two human-invoked CLI passthroughs in the closed list of unpinned commands in [Invariants](02-invariants.md). The other is the overlay's `d` diff for the contextual thread.
  - `kk ls`, the watcher, the `ui` pane, overlay polling, and every background renderer never run either.

### Flags

Flags:

- `--diff` (`-p`) appends the working-copy [patch](<https://en.wikipedia.org/wiki/Patch_(Unix)>) (the line-by-line changes).
- `--diff --stat` emits a diffstat (a per-file count of changed lines) instead of a patch.
- `--no-jj` suppresses the jj body and emits only the header.

### The checkpoint line

The header identifies the exact live `thread_head_commit_id` and a checkpoint line. The [live head](appendix-a-glossary.md#live-head) is the commit the thread's workspace is currently on. A checkpoint is a deliberate placement of the thread's [bookmark](appendix-a-glossary.md#bookmark) (jj's name for a movable label on a commit); see [checkpoint placement](appendix-a-glossary.md#checkpoint-placement).

The checkpoint line shows three facts:

- the **placed checkpoint**: the bookmark name and `checkpoint_commit_id`, the commit where kiki last explicitly placed it;
- the **tracked expected target**: `bookmark_expected_commit_id`, the commit the bookmark is expected to name now, after any rewrite [successors](appendix-a-glossary.md#native-successor) jj carried it to (see [expected bookmark target](appendix-a-glossary.md#expected-bookmark-target));
- the **relationship** of the tracked expected target to the live head, exactly one of `current`, `behind`, `ahead`, or `diverged` (see [checkpoint relationship](appendix-a-glossary.md#checkpoint-relationship)).

The relationship is defined purely on `bookmark_expected_commit_id` and the live head, tested on a single-parent path between them:

| value      | meaning                                                                                                                                                         |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `current`  | the expected target is the live head, or it is the commit the checkpoint target rule below picks: the state right after `jj commit` and right after `kk reopen` |
| `behind`   | the live head is any other descendant of the expected target; the detailed label is `checkpoint behind head`                                                    |
| `ahead`    | the live head is an ancestor of the expected target, for example after `jj edit` of an earlier commit                                                           |
| `diverged` | anything else                                                                                                                                                   |

`behind` is the ordinary reading once work continues past a checkpoint.

The [checkpoint target](appendix-a-glossary.md#checkpoint-target) is the commit a checkpoint would place the bookmark on. The rule is:

- The target is the live head.
- When the head is empty and undescribed, kiki walks back along the owned chain to the nearest commit that is not both empty and undescribed. That commit is the target.
- If the walk reaches the expected target first, the bookmark stays where it is.
- If the walk leaves the owned chain without finding either, the checkpoint refuses with "nothing to checkpoint".
- Creation is the one exception: it places the bookmark on the new thread's first, empty commit.

A thread reads `current` when the expected target equals the commit this rule picks, or equals the head.

The placed checkpoint and the tracked expected target differ whenever jj has carried the bookmark to a successor since the last placement. That difference is normal and is not an issue.

### When a checkpoint refuses

A checkpoint (at creation, publish, close, or detach) only moves the bookmark forward along the owned chain. It never moves it backward or sideways, and it never passes jj's `--allow-backwards` flag.

So a checkpoint refuses when its target is not equal to or a descendant of the expected target. While a thread reads `ahead` or `diverged`, publish, close, and detach stop at their checkpoint and say why.

The exit is the approved [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target) repair plan (see [Bookmark plans](#bookmark-plans)). It is offered for an `ahead` or `diverged` thread even when no issue is open. Two common ways to get there are `jj edit` of an earlier commit, and `jj rebase -r` of the bookmarked commit to somewhere else. Publish, close, and detach stay blocked until that plan is applied.

### Issues shown in the header

Open bookmark issues are reported separately. An open [`BookmarkMissing`](appendix-a-glossary.md#bookmarkmissing), [`BookmarkMoved`](appendix-a-glossary.md#bookmarkmoved), [`BookmarkConflicted`](appendix-a-glossary.md#bookmarkconflicted), or [`CheckpointAbandoned`](appendix-a-glossary.md#checkpointabandoned) issue is printed by name beside the relationship, with the observed target or targets, and points to `kk repair`. It does not change the relationship word.

The repository's [operation frontier](appendix-a-glossary.md#operation-frontier) can be [unmerged](appendix-a-glossary.md#unmerged-frontier): jj has more than one newest operation. When it is unmerged and its heads disagree about the head or the bookmark, the header prints `frontier unmerged` instead of a relationship. Kiki does not merge operation heads to answer a status query.

A trailing checkpoint is normal between explicit checkpoints and must not be mislabeled as a cascade conflict.

The header also names any open terminal issue ([`TerminalMissing`](appendix-a-glossary.md#terminalmissing), [`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess)) by reason. It never prints an agent state for a thread that has no ready [incarnation](appendix-a-glossary.md#incarnation) (one running lifetime of the agent).

The [cascade](appendix-a-glossary.md#cascade-reconciliation) state indicator is exactly one of `in sync`, `pending`, or `conflicted`; it does not include counts.

## `kk events`

`kk events [--thread <t>] [--follow] [--since <seq>] [--json]` prints kiki's events as they are recorded. An event is one thing that happened to a thread, such as a state change, a cascade step, or an [attention event](appendix-a-glossary.md#attention-event). It ships in the [acceptance slice](appendix-a-glossary.md#acceptance-slice).

It is how a script, or a person with no overlay, watches kiki. It reads kiki's own event log, so it works with no Herdr client attached.

- **Without `--thread`**, it prints the events of every thread in the caller's repo, through the `StreamRepoEvents` RPC. This is true even when the command runs inside a thread.
- **With `--thread <t>`**, it prints one thread's events. Run in that thread's own context, it reads the thread's full stream through `StreamThreadEvents`. Run from anywhere else, it reads the repo stream narrowed to that thread.
- `--since <seq>` starts after that sequence number. Every event carries a sequence number that only goes up, so a caller that reconnects can ask for exactly the events it missed.
- `--follow` keeps the stream open and prints new events as they happen. Without it, the command prints the stored events and exits with code 0.
- `--json` prints one JSON object per line.

The repo stream carries summary-class fields only: the same kind of data as [`kk ls`](#kk-ls). It never carries transcript text or other content that needs a [sensitive read](04-authority.md#sensitive-reads). So it needs no approval, and a registration credential or an automation credential can read it.

When a harness with proven `attention_events` stops to ask its own permission question, the stream shows `agent_blocked`. Kiki never answers a harness's own prompt. On a machine with no person, the operator sets the harness's own permission settings ahead of time. A person can also answer later, through `kk attach` over SSH.

## `kk wait`

`kk wait [<thread>] --for <state> [--timeout <dur>]` blocks until a thread reaches a state, and then exits. It lets a script wait for an agent without polling. It ships in Stage 2 of the [build sequence](15-build-sequencing.md), after the rest of the acceptance slice's headless surface.

The target defaults to the contextual thread (see [Context resolution](#context-resolution)). `--for` takes one of these states:

| State           | Reached when                                                                                                   |
| --------------- | -------------------------------------------------------------------------------------------------------------- |
| `quiescent`     | the harness adapter proves the agent is idle (see [agent quiescence](appendix-a-glossary.md#agent-quiescence)) |
| `goal-complete` | the agent reports its goal complete                                                                            |
| `blocked`       | the agent is blocked: it waits on a permission prompt, or it crashed                                           |
| `conflicted`    | the thread's cascade state is `conflicted`                                                                     |
| `closed`        | the thread's lifecycle state is `Closed`                                                                       |
| `issue`         | the thread has any open issue that `kk repair` would report                                                    |

- If the thread is already in the state, `kk wait` exits at once.
- It exits with [code](#exit-codes) 0 when the state is reached, and with code 6 when `--timeout` runs out first. Without `--timeout` it waits until the state is reached.
- `--for` is required. Without it the command exits with code 2.
- It reads summary-class data only, so it needs no approval. It changes nothing and proves nothing: a later command still runs its own preflight.
- With `--json`, the result carries the thread's summary at the moment the wait ended.

## `kk publish`

`kk publish` sends a thread's work to GitHub as a [pull request](https://docs.github.com/en/pull-requests) (PR). It is a v1.x command that publishes the resolved thread to GitHub through `gh`; see [Publishing](07-publishing.md). It is not part of the coordination [acceptance slice](appendix-a-glossary.md#acceptance-slice).

When invoked, it validates `gh` installation, authentication, repository identity, and remote state. It then requires a one-shot [approval](#foreground-approval-flow) for the exact publish plan. In a policy rule the operation is `publish`, and every publish plan carries the `externally-visible` risk label. `publish` rules arrive with this command.

Without a terminal, `kk publish` opens no editor. It needs `--no-edit`, and without it the command exits with code 2 and names that flag.

Important flags:

- `--no-edit` accepts the generated non-transcript template without opening an editor.
- `-m "<title>"` sets the PR title inline.
- `--ready` opens the PR ready for review instead of as a draft.
- `--downstack` publishes the current thread plus its unpublished descendants, top-down.
- `--refresh` regenerates title/body for an existing PR, and only when explicitly requested.
- `--review-stack` names the default top-down, editor-session-per-PR stack publish; it is an uncommitted alias that may not ship.

The first publishing release generates a deterministic template from explicit input and non-transcript metadata. AI drafting flags are deferred along with the metadata execution loop and are not part of that release.

## `kk thread snapshot`

`kk thread snapshot [<thread>]` records fresh tracked edits before a later close, detach, or publish. An explicit invocation requests one `snapshot` approval, including when the caller owns the thread. `SnapshotWorkspace` binds the workspace identity, exact starting head and operation, file inventory and fingerprint, and caller to the plan. A thread caller targeting another thread also needs the `cross-thread` risk label. The ordinary CLI and JSON approval flow applies.

After claim, recheck those inputs at a safe boundary under the thread and repo jj locks. A stale, uncertain, or changed workspace stops before the snapshot. Journal the attributed result and report the new pinned head. A retry of the same operation returns that outcome. A later close, detach, or publish starts a separate plan. Declining it leaves the completed snapshot in place. None of these commands requests a snapshot on the caller's behalf.

## `kk close`

`kk close [<thread>]` archives a thread without deleting tracked jj work; see [Threads](03-threads.md#close). It stops the thread's processes, removes its terminals and workspace directory, and keeps its revisions.

### Approval

Closing terminates live processes, so it requires a one-shot [approval](#foreground-approval-flow). The approval is bound to the final preflight and becomes invalid if the close plan changes before commit.

In a policy rule the operation is `close`. A close plan can carry these [risk labels](appendix-a-glossary.md#risk-label):

- `live-processes`, when it ends running processes in the thread's containers;
- `outside-holders`, when it accepts a holder outside the listed containers;
- `work-loss`, when its [loss inventory](appendix-a-glossary.md#loss-inventory) is not empty.

A rule allows the close only when it accepts every label on the plan. Without a terminal and without such a rule, `kk close` exits with code 3 and changes nothing.

### Preflight: a quiet agent

Close wants a quiet agent. [Agent quiescence](appendix-a-glossary.md#agent-quiescence) means the agent is not in the middle of work.

- Where the harness adapter can prove agent quiescence, preflight requires it. If the agent is working, preflight reports that and exits with code 4 and no mutation. The caller waits and runs `kk close` again. A person can also interrupt the agent in its pane first. A script can wait with [`kk wait --for quiescent`](#kk-wait).
- For a harness version that cannot prove quiescence, preflight proceeds and warns that a working agent will make the [approval drift](appendix-a-glossary.md#approval-drift).

Preflight probes files without snapshotting, integrating operation heads, or starting reconciliation. If tracked edits need preparation, exit with code 4 and identify the workspace and `kk thread snapshot` command. A clean workspace gives the exact head for the plan.

### What the plan covers

The plan covers the whole [terminal group](appendix-a-glossary.md#terminal-group), not only the agent: every [role pane](appendix-a-glossary.md#role-pane) and every pane or tab the user added.

The rendered plan lists the process inventory found at preflight. The plan card also shows the container-scope statement, in these words: the approval covers every process in the listed terminal containers at freeze time.

The approval's [fingerprint](appendix-a-glossary.md#close-plan-fingerprint) covers:

- the set of terminal containers;
- the role launcher identities;
- the set of [holders](appendix-a-glossary.md#holder) outside those containers;
- the workspace state;
- the [checkpoint target](appendix-a-glossary.md#checkpoint-target);
- incoming and outgoing follows links, their frontier, and any exact pending intents to discard.

It does not cover the list of processes inside each container. Those processes are covered by the container-scope statement and are recorded at freeze. So a process that joins a listed container between preflight and freeze is covered: it is terminated under that statement, and it is not [drift](appendix-a-glossary.md#drift). A "membership change" that counts as drift means a change in the container set, in a role launcher's identity, or in the holders outside the listed containers.

### Order of steps

Close [freezes](appendix-a-glossary.md#freeze) (pauses) and accounts for all of those processes before it changes anything. Then, in order:

1. **Freeze.** Kiki freezes every process in the terminal group.
2. **Post-freeze recheck.** Kiki repeats its loss checks against the frozen workspace (the [post-freeze recheck](appendix-a-glossary.md#post-freeze-recheck)).
3. **Holder scan.** Kiki scans for [holders](appendix-a-glossary.md#holder) of the workspace outside the frozen set.
4. **Checkpoint.** Kiki places the checkpoint.
5. **Each child step.** Kiki does every approved child step.
6. **Final proof.** Kiki runs the [final proof](appendix-a-glossary.md#final-proof). It checks that each listed container still holds its recorded launcher (if it had one) and exactly the processes recorded at freeze. Nothing is terminated before it.
7. **Kiki-side termination with verified exit.** Kiki itself terminates the [frozen set](appendix-a-glossary.md#frozen-set) while it is still stopped, and verifies each exit by recorded identity (see [verified exit](appendix-a-glossary.md#verified-exit)).
8. **Terminal-container close request.** Only then does kiki ask Herdr to close the terminal group. That request is cleanup, and its reply is not evidence.
9. **Post-exit filesystem recheck.** A filesystem recheck follows (the [post-exit filesystem recheck](appendix-a-glossary.md#post-exit-filesystem-recheck)).
10. **Workspace forget.** Kiki forgets the jj workspace.
11. **Directory delete.** Kiki deletes the workspace directory.

Every close uses this one list. [`close-without-terminal`](appendix-a-glossary.md#close-without-terminal) runs the same steps after its own preflight inventory and approval.

A failure before the final proof takes [verified resume](appendix-a-glossary.md#verified-resume): the frozen processes run again and the thread returns to `Active`. If the resume itself cannot be proved, the thread becomes `CloseFailed`. Any single step taken while processes are frozen must finish within `[timeouts] frozen_step`; if that time runs out before termination begins, kiki also takes verified resume.

Once termination has begun there is no resume. If exit cannot be verified within `[timeouts] verified_exit`, or the recheck fails, the files stay and the thread becomes `CloseFailed`. `kk repair` then offers [`retry-close`](appendix-a-glossary.md#retry-close).

### Processes outside the listed containers

A same-UID process can hold the workspace from outside the listed containers: an editor opened elsewhere, for example. "Same-UID" means it runs as the same [user](https://en.wikipedia.org/wiki/User_identifier). Such a [holder](appendix-a-glossary.md#holder) is not a standing issue and never blocks an `Active` thread.

At close it makes the result `Unknown`, and the files are kept, unless the approved plan names that exact holder as accepted (an [accepted holder](appendix-a-glossary.md#accepted-holder)).

The caller names a holder to accept with `--accept-holder <pid>`, once for each holder. Preflight resolves each pid to the exact process identity it found, and the plan lists it. Such a plan carries the `outside-holders` risk label. A holder the caller did not name is never accepted, by a person or by a policy rule.

Every `Unknown` result reports each offending pid, its command line, and the step that clears it. Writers running as another user are invisible to this scan.

### Closing from inside the thread

A `kk close` typed inside the group it closes is itself in the frozen set. That is safe: the approval is claimed and the journal written before the freeze.

- On an aborted close, it resumes with everything else and reports the outcome.
- On a completed close, it ends with the group, and `kk ls` and the journal carry the result.

### Focus after close

This applies when `kk close` ran outside the closed terminal group. After a successful close, it requests [caller-local focus](appendix-a-glossary.md#caller-local-focus) on the parent thread's agent pane when the parent thread is `Active` with a bound terminal group. The request follows the same contract as [`kk switch`](#kk-switch).

The request is best-effort navigation and is not part of the close journal. Every client that was showing the closed terminal group and was not moved this way is placed by Herdr; kiki does not steer it.

### Flags

Important flags:

- `--accept-holder <pid>` names one process outside the listed containers that the plan accepts (see [Processes outside the listed containers](#processes-outside-the-listed-containers)). It can be given more than once.
- `--confirm` asks a person to confirm even when a policy rule allows the plan.
- `--discard-pending` requests discard of the listed pending transitions or deliveries on the closing thread's incoming or outgoing edges. The approved plan must accept `discard-pending`. Unresolved file recovery still blocks close.
- `--discard-pr` ships with publishing. It also closes the open PR. Plain close stays local.

Nothing closes a thread without a one-shot approval. The v1.x auto-archive on PR merge only proposes a close plan; see [Publishing](07-publishing.md).

## `kk reopen`

`kk reopen <thread>` restores a closed thread so work can continue; see [Threads](03-threads.md#reopen). [Acceptance-slice](appendix-a-glossary.md#acceptance-slice) reopen restores lifecycle state without reading or sending transcript text.

### Approval

A closed thread has no live thread credential, and reopen starts a new process [incarnation](appendix-a-glossary.md#incarnation). So reopen requires a one-shot [approval](#foreground-approval-flow) bound to the target, the restored head, the workspace path, and the harness. In a policy rule the operation is `reopen`.

Without a terminal and without a rule that allows the plan, `kk reopen` exits with code 3 and changes nothing.

### What it does

- Reopen provisions a new [terminal group](appendix-a-glossary.md#terminal-group) with fresh role panes. It does not look for or adopt an earlier one.
- Before provisioning, kiki scans for recorded processes of the thread that are still alive. A survivor raises [`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess) and stops the reopen before any agent starts.
- The reopened head is a new empty working-copy commit whose parent is the checkpoint. So `kk status` reads `current` until work is added.
- After the thread is `Active`, `kk` requests caller-local focus on the new agent pane as `kk new` does.

### When reopen fails

Kiki does not clean up automatically if reopen fails after any of these:

- its [launch gate](appendix-a-glossary.md#launch-gate) was activated (the gate that holds the agent back until kiki allows it to start);
- anything but kiki's own blocked launchers ran in the group;
- the workspace changed from its initial [materialization](appendix-a-glossary.md#materialization) (the files kiki first wrote into it).

The projections stay, and cleanup is the approved [`cleanup-failed-reopen`](appendix-a-glossary.md#cleanup-failed-reopen) plan in `kk repair`.

### Catch-up

`--catch-up` ships with the v1.x transcript feature. It requests transcript-backed context and triggers the [provider-egress consent](appendix-a-glossary.md#provider-egress-consent) flow described in [Transcript](06-transcript.md#reopen-catch-up). [Provider egress](appendix-a-glossary.md#provider-egress) means sending content to the AI provider behind the harness.

- When catch-up needs fresh interactive consent, preflight requests a presenter-confirmed reopen even if a rule allows reopen. An automation credential with no consent exits with code 3 before claim.
- Because the closed credential is revoked, the daemon releases the preview only to the foreground presenter. It does so after the reopen approval is claimed and before the harness starts.
- Declining catch-up continues cold unless the user cancels reopen entirely.
- Without the flag, reopen never reads transcript rows for harness input.

The consent question has no flag that answers it. With no person present, consent can come from two places only: a grant the person remembered earlier, or a rule in the activated policy that names `consent:catch_up` and lists that provider. A rule that gives the reopen approval does not give this consent, and `*` in a rule's `operations` never matches it.

- When such a consent exists, the catch-up is sent and no preview is released to anyone.
- When it does not, and there is no foreground terminal, `kk reopen --catch-up` exits with code 3 at preflight and changes nothing. The message names the missing consent. Running `kk reopen` without `--catch-up` reopens cold.

## `kk thread transcript`

`kk thread transcript [<thread>] [<change>]` reads the locally stored [transcript](appendix-a-glossary.md#thread-transcript) for a thread: the record of what the human and the agent said. It is a v1.x command.

- A contextual same-thread read uses [`ThreadScoped`](appendix-a-glossary.md#threadscoped-credential).
- Reading another thread's transcript requires a one-shot [approval](#foreground-approval-flow) for the exact query and an immutable result snapshot. In a policy rule the operation is `sensitive-read`.
- Changing search, range, or filter arguments requires a new approval. So does refreshing after repository state changes.

Important flags:

- `--search <query>` runs [full-text search](https://en.wikipedia.org/wiki/Full-text_search).
- `--range <from>..<to>` reads a span of changes.
- `--recent <n>` reads the tail of the thread.
- `--include-unanchored` includes rows with unknown change anchors.
- `--include-tombstoned` includes rows for tombstoned or redirected changes.
- `--no-synthesized` hides kiki-authored [synthesized](appendix-a-glossary.md#synthesized-true) rows.

## `kk thread comments`

`kk thread comments [<thread>]` lists GitHub PR review comments for the thread's PR. It is deferred v1.x work.

The first comments surface is read-only. Feeding review comments into agent context is future work.

## `kk thread interrupt`

`kk thread interrupt [<thread>]` stops an agent that is stuck or off track. It is a v1.x management command. The target is optional and defaults to the contextual thread (see [Context resolution](#context-resolution)).

It hard-stops the thread's agent and reframes it through the harness resume path. It is the explicit escape hatch for a stuck or off-track agent, and it uses the same [hard-escalation](appendix-a-glossary.md#hard-escalation) shape as cascade conflict handling.

Interrupt destroys a process at a caller's request, so it requires a one-shot [approval](#foreground-approval-flow), even for the contextual thread. In a policy rule the operation is `interrupt`, and the plan carries the `live-processes` risk label. Without a terminal and without a rule that allows the plan, the command exits with code 3. Kiki's own protocol restarts, such as a cascade hard restart, are daemon-initiated steps of the delivery protocol and need no approval.

## `kk thread restart`

`kk thread restart <thread> --harness <new>` moves a thread to a different [harness](appendix-a-glossary.md#harness), the coding-agent program that runs in the thread. It is a v1.x command; [Orientation](01-orientation.md) records the tier.

A thread cannot change its harness in place. This command is the only way to change it:

- It ends the thread's current agent and starts a new one under the new harness.
- The new agent is a new [incarnation](appendix-a-glossary.md#incarnation). It goes through the same [launch gate and ready handshake](appendix-a-glossary.md#launch-gate) as creation and reopen, and it must prove exclusive hook control again before the thread counts as ready.
- If a cascade delivery is waiting, the new agent receives the saved payload first, through [`RestartStartup`](appendix-a-glossary.md#restartstartup-delivery-proof).
- `--harness` accepts the same names as `kk new --harness`. An unsupported name is an error.

Ending a live agent is process-destructive, so the command requires a one-shot approval (see [Authority](04-authority.md#operations-that-require-human-approval)). In a policy rule the operation is `restart`, and the plan carries the `live-processes` risk label.

This command is not the `restart-agent` repair plan. That plan restarts the same harness after it has already exited, ships in the acceptance slice, and needs no approval in the thread's own context (see [`kk repair`](#kk-repair)).

The rest of the command's behavior is settled when it ships. [Harness adapter](13-architecture/harness-adapter.md#per-thread-harness-selection) reserves these rules now so that no later change edits a thread's harness identity in place.

## `kk thread describe`

`kk thread describe --refresh` hands a revision's description back to kiki. It is a v1.x command and ships with [auto-describe](appendix-a-glossary.md#auto-describe), the feature that writes revision descriptions.

It exists because kiki never overwrites words a human wrote. Once a human edits a description that kiki wrote, that description becomes human-owned, and kiki leaves it alone. `--refresh` is the explicit way to opt back in:

- It marks the description as kiki-owned again and queues a new auto-describe job for it.
- The job follows every auto-describe rule in [Metadata Evolution](08-metadata.md#revision-descriptions). In particular, it does not read the thread transcript.
- Without `--refresh`, kiki does not rewrite a human-owned description.

How the command selects a revision other than the thread's current one is settled when the feature ships.

## `kk thread detach`

`kk thread detach [<thread>]` removes the thread's live [follows](appendix-a-glossary.md#follows) edge, so the thread stops tracking its parent. The target is optional and defaults to the contextual thread (see [Context resolution](#context-resolution)). See [Cascade](05-cascade.md#detach-and-graph-surgery) for what detach does and does not touch.

### Order of steps

Before detach decides that no reconciliation is pending, it does these things:

1. It synchronously runs [`RefreshToFrontier`](appendix-a-glossary.md#refreshtofrontier), which brings kiki's records up to date with jj's newest operations.
2. It refreshes the parent and child [live heads](appendix-a-glossary.md#live-head) from that pinned view.
3. It creates any transition a lagging watcher had not yet recorded.

The caller must reconcile that exact transition or explicitly discard it. Pending parent work is discarded only with `--discard-pending`; without that flag, detach refuses while a transition is pending and says so. Only then does detach checkpoint the child at its [checkpoint target](appendix-a-glossary.md#checkpoint-target) and delete the edge.

Follows graph surgery, `kk thread attach` and `kk thread reparent`, is out of v1. When those commands ship, they refuse the same way as `kk new --follows` for a thread whose harness failed its `RestartStartup` proof.

### Approval

A same-thread detach with no pending reconciliation uses thread-scoped authority. Two cases require one-shot [approval](#foreground-approval-flow) bound to that choice:

- discarding a pending transition with `--discard-pending`. The plan carries the `discard-pending` risk label;
- detaching an explicitly targeted different thread. For a thread-scoped caller, the plan carries the `cross-thread` risk label.

In a policy rule the operation is `detach`. Without a terminal and without a rule that allows the plan, these two cases exit with code 3. The pending transition and the edge stay as they were.

## `kk thread destroy`

`kk thread destroy <thread>` permanently removes kiki's records of a thread. It is a v1.x management command.

It permanently removes kiki's thread [projections](appendix-a-glossary.md#projection) and management state; see [Threads](03-threads.md#destroy). Tracked jj revisions are preserved by default.

### Flags

Important flags:

- `--keep-log` retains the thread's transcript rows instead of deleting them. The view that reads those kept rows is future work; until it ships, no command shows them.
- `--abandon-revisions` also abandons revisions, but only the exact validated linear owned chain named in the approval plan.
  - The plan lists every change/commit id and every affected registered descendant.
  - Ambiguous topology, foreign commits, or plan drift refuses the operation rather than widening the revset.

### Order of steps

For an active thread, destroy stops processes before it touches history. The order is:

1. freeze;
2. [post-freeze recheck](appendix-a-glossary.md#post-freeze-recheck);
3. holder scan;
4. [final proof](appendix-a-glossary.md#final-proof);
5. terminate the [frozen set](appendix-a-glossary.md#frozen-set) with [verified exit](appendix-a-glossary.md#verified-exit);
6. terminal-group close request;
7. [post-exit filesystem recheck](appendix-a-glossary.md#post-exit-filesystem-recheck);
8. then bookmark deletion;
9. the optional exact abandon;
10. workspace forget and delete;
11. credential revocation;
12. and the tombstone.

Drift before termination takes the [verified-resume](appendix-a-glossary.md#verified-resume) path. Process termination is the first irreversible step. After it the thread can only finish the plan or become `DestroyFailed`. From `DestroyFailed`, `kk repair` offers [`retry-destroy`](appendix-a-glossary.md#retry-destroy), which resumes that exact plan.

The approval covers every process in the listed terminal containers at freeze time, as for close. A destroy from `ProjectionDiverged` lists and closes [remnant](appendix-a-glossary.md#remnant-container) or [unbound](appendix-a-glossary.md#unbound-container) containers tied to the thread in the same way as a repair plan.

### Approval

Destroy requires a one-shot [approval](#foreground-approval-flow) even when revisions are preserved.

- `--abandon-revisions` has a distinct method/argument digest and cannot reuse an approval issued for ordinary destroy.
- A plain yes/no prompt detached from a method-and-target-bound capability is insufficient.
- In a policy rule the operation is `destroy`. The plan carries `abandon-revisions` when that flag is given, and the same labels as close for what it stops and deletes: `live-processes`, `outside-holders`, and `work-loss`. `--accept-holder <pid>` works as it does for close.
- Without a terminal, destroy runs only when a rule allows `destroy` and accepts every label on the plan. Otherwise it exits with code 3 and changes nothing.

## `kk repair`

`kk repair [<thread>]` diagnoses a thread whose state went wrong and offers named plans to fix it. With `--repo` or `--server` it does the same for the repo or for the terminal server.

It is the explicit recovery surface for a `ProjectionDiverged`, `CreateFailed`, `CloseFailed`, `DestroyFailed`, exhausted-delivery, or other repairable lifecycle condition. The lifecycle and projection chapters own those states; this command owns their shared interaction shape.

### Diagnose first, then apply

Without an apply flag, `kk repair` is read-only. It reports:

- the observed [projections](appendix-a-glossary.md#projection) (the outside things that mirror kiki's records, such as a bookmark or a terminal group);
- the durable kiki authority;
- zero or more named [repair plans](appendix-a-glossary.md#repair-plan).

Each plan states which records, workspace paths, bookmarks, terminal groups, processes, or revisions it would change.

With `--json`, the diagnosis lists each plan's id, its name, its [risk labels](appendix-a-glossary.md#risk-label), and any argument the plan needs. A script can read that list and pick a plan.

Kiki may repair provably idempotent projection drift automatically in the background. But it must never silently choose among multiple plausible heads, paths, or topologies. A policy rule does not change that: a rule can approve a plan, and it never picks one.

`--apply <repair-id>` applies exactly the plan emitted by the current diagnosis.

- If repository state has changed, the id is stale, and kiki diagnoses again instead of adapting the old plan. The apply exits with code 4.
- A same-thread, non-destructive projection repair may use [`ThreadScoped`](appendix-a-glossary.md#threadscoped-credential).
- Any destructive, revision-rewriting, topology-changing, or cross-thread plan requires a one-shot [approval](#foreground-approval-flow) bound to the repair id and target. In a policy rule the operation is `repair:<plan-name>`, for example `repair:terminate-orphans`. `repair:*` covers every such plan.
- A plan that needs no approval in the thread's own context, such as `restart-agent`, needs one when any other caller applies it. In a policy rule that operation is `thread-op`, not `repair:<plan-name>`.
- If the plan needs a fresh approval and none is available, a headless apply exits with code 3. A same-thread plan that needs no approval, or a retry that continues an approved journal, can proceed.

Some plans need the caller to choose something. Each such choice is an argument to `--apply`, and it is part of the plan digest:

| Plan                                                                      | Argument                    | What it names                                                 |
| ------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------- |
| [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target) | `--target <commit>`         | the commit the bookmark is placed on                          |
| [`repoint-workspace`](appendix-a-glossary.md#repoint-workspace)           | `--path <path>`             | the workspace path kiki records                               |
| `choose-recovery-successor`                                               | `--target <full-commit-id>` | one edit-preserving candidate from the recovery diagnosis     |
| any plan that deletes the workspace                                       | `--accept-holder <pid>`     | one outside [holder](appendix-a-glossary.md#holder) to accept |

On a terminal, `kk` may ask for a missing choice. Without a terminal it does not ask: the apply exits with code 2 and names the missing argument. No other plan in v1 needs a choice. Where an issue has more than one plan, the caller chooses by plan id.

### Scopes: thread, repo, and server

`kk repair` works at four scopes.

- **One thread.** `kk repair [<thread>]` diagnoses one thread. The target defaults to the contextual thread.
- **Every thread in the repo.** `kk repair --all` diagnoses every thread in the caller's repo, including closed threads with an open issue. It never crosses repos, and it does not apply plans.
- **The repo.** `kk repair --repo` diagnoses repo-level issues for the caller's repo. `kk repair --repo --apply <plan-id>` applies one. It needs a one-shot approval with repo scope. The one repo-level issue in v1 is [`OperationHistoryRewritten`](#repository-operation-history).
- **The terminal server.** `kk repair --server` diagnoses the user's [dedicated Herdr server](appendix-a-glossary.md#dedicated-herdr-server). `kk repair --server --apply <plan-id>` applies the user-scoped [`replace-terminal-server`](#the-terminal-server-replace-terminal-server) plan under a one-shot approval.

### Every issue and its plan

This table is the full list. It names the plan for each issue or failed state and says what approval the plan needs. Other chapters use these plan names.

"One-shot" means a one-shot approval from the [approval flow](#foreground-approval-flow). Either kind satisfies it: a person's confirmation at a foreground terminal, or a [`PolicyApproval`](appendix-a-glossary.md#policy-approval) from a rule that allows `repair:<plan-name>` and accepts the plan's risk labels.

| Issue or failed state                             | Plan                                                                                                                         | Approval                                                                                                           |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [`TerminalMissing`][i-tm]                         | [`restart-terminal`][p-rt], or [`close-without-terminal`][p-cwt]                                                             | one-shot                                                                                                           |
| crashed harness under a live launcher             | [`restart-agent`][p-ra]                                                                                                      | none in the thread's own context                                                                                   |
| [`OrphanedProcess`][i-op]                         | [`terminate-orphans`][p-to]                                                                                                  | one-shot                                                                                                           |
| unverified or changed terminal server             | [`replace-terminal-server`][p-rts] (`kk repair --server`)                                                                    | one-shot, user scope                                                                                               |
| `CreateFailed`                                    | [`cleanup-failed-create`][p-cfc]                                                                                             | one-shot                                                                                                           |
| failed reopen                                     | [`cleanup-failed-reopen`][p-cfr]                                                                                             | one-shot                                                                                                           |
| failed terminal restart                           | [`cleanup-failed-restart`][p-cfrs]                                                                                           | one-shot                                                                                                           |
| `CloseFailed`                                     | [`retry-close`][p-rc]                                                                                                        | none; it continues the plan that was already approved                                                              |
| `DestroyFailed`                                   | [`retry-destroy`][p-rd]                                                                                                      | none; it continues the plan that was already approved                                                              |
| [`WorkspaceDirectoryMissing`][i-wdm]              | [`recreate-workspace`][p-rw]                                                                                                 | none in the thread's own context; one-shot from anywhere else                                                      |
| [`WorkspaceRecordMissing`][i-wrm]                 | [`reattach-workspace`][p-raw]                                                                                                | none in the thread's own context; one-shot from anywhere else                                                      |
| [`WorkspacePathMismatch`][i-wpm]                  | [`repoint-workspace`][p-rpw]                                                                                                 | none in the thread's own context; one-shot from anywhere else                                                      |
| `RecoveryRequired` with ambiguous successors      | [`choose-recovery-successor`](05-cascade.md#recovery-steps)                                                                  | one-shot, bound to intent, operation, bundle fingerprint and selected commit                                       |
| [exhausted intent][i-ei]                          | [`retry-delivery`][p-rdl], or [`discard-delivery`][p-dd]                                                                     | none in the thread's own context for retry; one-shot for discard                                                   |
| [`BookmarkMissing`][i-bm]                         | [`restore-bookmark`][p-rb] while the expected target is visible; [`choose-bookmark-target`][p-cbt]                           | restore: none in the thread's own context; one-shot when applied to a different thread; choose: one-shot           |
| [`BookmarkMoved`][i-bmv]                          | [`restore-bookmark`][p-rb] while the expected target is visible; [`adopt-bookmark`][p-ab]; [`choose-bookmark-target`][p-cbt] | restore: none in the thread's own context; one-shot when applied to a different thread; adopt and choose: one-shot |
| [`BookmarkConflicted`][i-bc]                      | [`restore-bookmark`][p-rb] while the expected target is visible; [`choose-bookmark-target`][p-cbt]                           | restore: none in the thread's own context; one-shot when applied to a different thread; choose: one-shot           |
| [`CheckpointAbandoned`][i-ca]                     | [`unhide-checkpoint`][p-uc] when unhiding would not create a divergent change; [`choose-bookmark-target`][p-cbt]             | one-shot                                                                                                           |
| no open issue, relationship `ahead` or `diverged` | [`choose-bookmark-target`][p-cbt]                                                                                            | one-shot                                                                                                           |
| [`OperationHistoryRewritten`][i-ohr] (repo level) | [`reanchor-history`][p-rh] (`kk repair --repo`)                                                                              | one-shot, repo scope                                                                                               |

[i-tm]: appendix-a-glossary.md#terminalmissing
[i-op]: appendix-a-glossary.md#orphanedprocess
[i-wdm]: appendix-a-glossary.md#workspacedirectorymissing
[i-wrm]: appendix-a-glossary.md#workspacerecordmissing
[i-wpm]: appendix-a-glossary.md#workspacepathmismatch
[i-ei]: appendix-a-glossary.md#exhausted-intent
[i-bm]: appendix-a-glossary.md#bookmarkmissing
[i-bmv]: appendix-a-glossary.md#bookmarkmoved
[i-bc]: appendix-a-glossary.md#bookmarkconflicted
[i-ca]: appendix-a-glossary.md#checkpointabandoned
[i-ohr]: appendix-a-glossary.md#operationhistoryrewritten
[p-rt]: appendix-a-glossary.md#restart-terminal
[p-cwt]: appendix-a-glossary.md#close-without-terminal
[p-ra]: appendix-a-glossary.md#restart-agent
[p-to]: appendix-a-glossary.md#terminate-orphans
[p-rts]: appendix-a-glossary.md#replace-terminal-server
[p-cfc]: appendix-a-glossary.md#cleanup-failed-create
[p-cfr]: appendix-a-glossary.md#cleanup-failed-reopen
[p-cfrs]: appendix-a-glossary.md#cleanup-failed-restart
[p-rc]: appendix-a-glossary.md#retry-close
[p-rd]: appendix-a-glossary.md#retry-destroy
[p-rw]: appendix-a-glossary.md#recreate-workspace
[p-raw]: appendix-a-glossary.md#reattach-workspace
[p-rpw]: appendix-a-glossary.md#repoint-workspace
[p-rdl]: appendix-a-glossary.md#retry-delivery
[p-dd]: appendix-a-glossary.md#discard-delivery
[p-rb]: appendix-a-glossary.md#restore-bookmark
[p-ab]: appendix-a-glossary.md#adopt-bookmark
[p-cbt]: appendix-a-glossary.md#choose-bookmark-target
[p-uc]: appendix-a-glossary.md#unhide-checkpoint
[p-rh]: appendix-a-glossary.md#reanchor-history

Three notes on the approval column:

- "None in the thread's own context" means the plan uses `ThreadScoped` when it is applied from inside that thread. Applied to a different thread, every plan needs one-shot approval, as any cross-thread change does. So does a plan applied with an automation credential, which is no thread's own. For a plan this column marks "none in the thread's own context", the operation in a policy rule is then `thread-op`. For a plan marked "one-shot", it is `repair:<plan-name>` for every caller.
- `retry-close` and `retry-destroy` continue the journal of a plan that was already approved. They never widen it. If the plan can no longer be finished as approved, the diagnosis says so and offers a fresh plan that needs a new approval.
- A closed thread, a `CreateFailed` thread, and a `DestroyFailed` thread may also be destroyed through the [destroy](03-threads.md#destroy) preflight once that command ships.

### Failed close and destroy

- **[`retry-close`](appendix-a-glossary.md#retry-close)** resumes a `CloseFailed` thread's close journal from the step that failed. It re-runs exit verification by recorded identity and re-reads the workspace fingerprint before it forgets or deletes anything. Where the diagnosis instead proves a live terminal group and a responsive agent, it reports that the thread can return to `Active`.
- **[`retry-destroy`](appendix-a-glossary.md#retry-destroy)** resumes a `DestroyFailed` thread's destroy journal in the same way. It applies exactly the approved plan, including the exact revision list when `--abandon-revisions` was approved.

### Workspace plans

Three issues are about the thread's jj [workspace](appendix-a-glossary.md#workspace). Kiki fixes such an issue by itself only when it can prove that exactly one fix is possible (see [Threads](03-threads.md#projection-divergence-and-repair)). Otherwise `kk repair` offers these plans:

- **[`recreate-workspace`](appendix-a-glossary.md#recreate-workspace)** is for [`WorkspaceDirectoryMissing`](appendix-a-glossary.md#workspacedirectorymissing): the directory is gone. The plan creates the directory again from the checkpoint. Edits that were never recorded in jj are not recovered, and the plan says so.
- **[`reattach-workspace`](appendix-a-glossary.md#reattach-workspace)** is for [`WorkspaceRecordMissing`](appendix-a-glossary.md#workspacerecordmissing): jj has forgotten the workspace, but the directory is still there. The plan creates the jj workspace record again for that directory.
- **[`repoint-workspace`](appendix-a-glossary.md#repoint-workspace)** is for [`WorkspacePathMismatch`](appendix-a-glossary.md#workspacepathmismatch): the workspace is at a different path from the one kiki recorded. The plan records the path the caller gives with `--path <path>`. Kiki does this by itself only when jj's stable workspace id proves the moved directory is the same one.

While one of these issues is open, kiki makes no change that depends on the broken workspace record, path, or directory.

### Exhausted delivery

An intent is kiki's durable record of one update it owes an agent (see [`sync_intent`](appendix-a-glossary.md#sync-intent)). An intent whose [delivery attempts are exhausted](appendix-a-glossary.md#exhausted-intent) (see [Cascade](05-cascade.md#delivery-protocol)) diagnoses to exactly two named plans.

- **[`retry-delivery`](appendix-a-glossary.md#retry-delivery)** re-arms the intent in one journaled transaction:
  - it clears `delivery_exhausted_at`;
  - it increments the intent's [`delivery_epoch`](appendix-a-glossary.md#delivery-epoch);
  - it resets the soft-redelivery count.

  It then permits one fresh [`RestartStartup`](appendix-a-glossary.md#restartstartup-delivery-proof) cycle of at most `[cascade] delivery_attempts` attempts (default 3). Those attempts are stamped with and counted under the new epoch. It is run after changing whatever made delivery fail, such as upgrading the harness.

- **[`discard-delivery`](appendix-a-glossary.md#discard-delivery)** acknowledges the intent without delivery proof. It runs under a one-shot approval bound to the plan, and it records the resolution on the intent, with the approval that allowed it. The payload is then never delivered to the agent, and the plan says so before it is approved.

### Agent, terminal, and process plans

#### A crashed harness: `restart-agent`

The `agent` [pane launcher](appendix-a-glossary.md#pane-launcher) is the small kiki process that starts the [harness](appendix-a-glossary.md#harness) inside the agent pane. It outlives harness [incarnations](appendix-a-glossary.md#incarnation). A harness that exits or crashes under a live launcher is not [`TerminalMissing`](appendix-a-glossary.md#terminalmissing):

- the incarnation is retired without acknowledgement;
- the agent state becomes `Crashed` (displayed as blocked);
- the thread's lifecycle is unchanged.

A dead harness under a live launcher is never shown as working.

- **[`restart-agent`](appendix-a-glossary.md#restart-agent).** This is the explicit restart path for that case.
  - It starts a replacement incarnation on the live launcher. That means a fresh one-use [launch gate](appendix-a-glossary.md#launch-gate), awaited by the same accepted launcher, with `RestartStartup` delivery if an intent is pending.
  - Its precondition is an inventory rooted at the `agent` launcher that shows no process other than the launcher itself.
  - A surviving tool child of the retired harness is a [harness remnant](appendix-a-glossary.md#harness-remnant): it raises [`OrphanedProcess`](appendix-a-glossary.md#orphanedprocess) and blocks the gate until [`terminate-orphans`](appendix-a-glossary.md#terminate-orphans) clears it.
  - The plan provisions nothing in the terminal.
  - Applied in the thread's own context it uses `ThreadScoped` and needs no approval.

#### A missing terminal: `TerminalMissing`

`TerminalMissing` is raised only when the `agent` role itself ends: the launcher's own process exits, or its [binding](appendix-a-glossary.md#terminal-binding) or [server instance](appendix-a-glossary.md#server-instance) is lost. In a terminal group whose only pane is the agent pane, the launcher's exit removes the whole Herdr workspace, so the group is gone as well.

While the issue is open, boundary delivery, materialization, and lifecycle mutation are blocked, except for the approved plans below.

A `TerminalMissing` issue covers a missing server instance, a missing terminal group, an ended `agent` role, a [cold restore](appendix-a-glossary.md#cold-restore), and an observed handoff. The diagnosis says which, with the recorded and observed server instance, binding, and process identities.

Two kinds of leftover container matter to both plans below. Kiki never reuses either kind.

- A [remnant container](appendix-a-glossary.md#remnant-container) is one Herdr restored after a cold restore.
- An [unbound container](appendix-a-glossary.md#unbound-container) is a terminal container on the current server instance with no current binding. That includes a group whose binding ended because its `agent` launcher died while the group itself survived. Kiki ties an unbound container to a thread in two ways only: by kiki's record of a binding that ended on the same server instance, or by OS evidence that its processes hold the thread's workspace.

The processes in these containers are terminal members, not [orphans](appendix-a-glossary.md#orphan). Both plans list the remnant and unbound containers with their processes and dispose of them. Both plans share one precondition: no recorded process survives outside the listed containers. A survivor outside them is an orphan and must be resolved first with [`terminate-orphans`](appendix-a-glossary.md#terminate-orphans).

The diagnosis offers:

- **Restart the terminal and agent ([`restart-terminal`](appendix-a-glossary.md#restart-terminal)).** This is a journaled lifecycle operation with its own step list.
  - Its steps run in this order. [Terminal runtime](13-architecture/terminal-runtime.md#restarting-the-terminal) owns the list:
    1. Preflight inventory and plan. The plan lists every remnant or unbound container tied to the thread (by an ended binding on the same server instance, or by OS evidence that its processes hold the thread's workspace), with the processes in each.
    2. The approval is claimed with the operation journal.
    3. Kiki freezes the processes in the listed containers. If the freeze returns `Unknown`, the plan takes [verified resume](appendix-a-glossary.md#verified-resume) and stops. Nothing is terminated.
    4. Kiki proves that each listed container holds exactly the processes recorded at freeze. Then it terminates them with verified exit and requests each container's close.
    5. Kiki runs the holder scan and the orphan scan again.
    6. Only then does it provision a fresh terminal group.
  - It starts a new incarnation with a fresh credential, launch settings, launch gate, and [ready handshake](appendix-a-glossary.md#ready-handshake).
  - It provisions the `shell` and `ui` role panes as at creation.
  - The thread returns to `Active` only when the ready handshake commits. The handshake must arrive within `[timeouts] ready_handshake`.
  - A pending delivery reaches the new incarnation through the [cascade protocol](05-cascade.md#delivery-protocol); the plan never marks it delivered.
  - The restart plan requires one-shot approval, and that approval covers every process in the listed terminal containers at freeze time.
  - **If it fails after provisioning,** `TerminalMissing` stays open and the thread stays `ProjectionDiverged`. The half-made terminal group is removed by [`cleanup-failed-restart`](appendix-a-glossary.md#cleanup-failed-restart), under the same limits as `cleanup-failed-create` (see [A failed terminal restart](#a-failed-terminal-restart)).
- **[`close-without-terminal`](appendix-a-glossary.md#close-without-terminal).** The thread goes from `ProjectionDiverged` to `CloseCommit` without a live agent. It is offered after a reboot or server restart without the user first closing restored shells. It uses the same order as an ordinary close, and nothing is terminated before the final proof:

  1. Preflight runs the same [workspace loss inventory](appendix-a-glossary.md#loss-inventory) as ordinary close and produces the plan. The plan lists every remnant or unbound container tied to the thread (by an ended binding on the same server instance, or by OS evidence that its processes hold the thread's workspace), and the processes in each.
  2. Claiming the one-shot approval enters `CloseCommit`. The approval covers every process in the listed terminal containers at freeze time.
  3. Kiki [freezes](appendix-a-glossary.md#freeze) the processes in the listed remnant and unbound containers, which records their identities.
  4. The [post-freeze recheck](appendix-a-glossary.md#post-freeze-recheck) runs.
  5. The holder scan runs.
  6. Kiki places the checkpoint.
  7. Kiki does each child step.
  8. The [final proof](appendix-a-glossary.md#final-proof) runs: each listed container holds exactly the processes recorded at freeze.
  9. Kiki itself terminates those processes with [verified exit](appendix-a-glossary.md#verified-exit).
  10. Kiki sends the terminal-container close request for each listed container.
  11. The [post-exit filesystem recheck](appendix-a-glossary.md#post-exit-filesystem-recheck) runs.
  12. Kiki forgets the jj workspace.
  13. Kiki deletes the directory.

  A failure before the final proof takes verified resume of the frozen processes. The plan stops, and the thread returns to `ProjectionDiverged` with its issue unchanged. A failure after termination has begun is `CloseFailed`.

- **Destroy**, through the [destroy](03-threads.md#destroy) preflight, once that command ships. It lists and closes the same containers.

#### The terminal server: `replace-terminal-server`

Some problems belong to the dedicated server, not to one thread:

- the running server is one [`kkd`](appendix-a-glossary.md#kkd) did not start, so it is unverified. That includes the server left by Herdr's own handoff or upgrade. `kkd` recognises a server it started by the peer identity on its `Open` `terminal_servers` row. For any other peer, it ends the old row, which ends its bindings and raises `TerminalMissing`, and it records the new peer as `Unverified`. It provisions nothing on an unverified server;
- `[terminal] session`, `[terminal] herdr_bin`, or `[paths] herdr_dir` changed while a server instance is open. `kkd` does not start a second server. It keeps the old one and reports that a change is pending.

The fix is [`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server). It is a user-scoped plan, not a thread-scoped one, and it is applied with `kk repair --server`.

- The plan lists every thread and every process that the replacement stops, across all of the user's repos.
- It needs a one-shot approval. The plan belongs to the user, not to a repo, so no thread or registration credential can begin it. A caller with an automation credential begins it with that credential. Any other caller begins it under the user's Admin bootstrap credential, and the presenter then confirms on a foreground terminal. It works from any directory.
- The plan carries the `server-wide` risk label. It belongs to no repo, so a rule matches it only when the rule's `repos` is `*`.
- On approval, kiki stops the old server with [verified exit](appendix-a-glossary.md#verified-exit), then starts a new one.
- Every thread that was bound to the old server then reads `TerminalMissing`, and each one is brought back with `restart-terminal`.

An instance change where `kkd` itself started the new server is not this case. One example is a start after a server crash. That server is verified, and each thread needs only `restart-terminal`.

Kiki never replaces a running server without this plan, because stopping the server ends every thread's processes.

#### Panes restored after a cold restore

After a cold restore, the panes Herdr restored are **remnant panes** (see [remnant pane](appendix-a-glossary.md#remnant-pane)): plain shells the runtime started, usually with their working directory inside the thread's jj workspace.

- Their launch command is not rerun.
- They are accounted terminal members, not orphans, because the current runtime observation names each one's pane and root process.
- Kiki ties a remnant container to a thread only by OS evidence, a pane process that holds that thread's workspace, never by the container's id or label.

No plan adopts or reuses a restored or surviving pane. A thread never returns to `Active` because a pane, a label, or a Herdr agent state reappeared.

#### Leftover processes: `OrphanedProcess`

`OrphanedProcess` is a standing issue with two causes (see [orphan](appendix-a-glossary.md#orphan)):

- **A survivor.** A recorded process identity is alive, has no current binding, and is not a member of a container on the current server instance.
- **A [harness remnant](appendix-a-glossary.md#harness-remnant).** Any descendant of a live `agent` launcher, other than the launcher itself, while no incarnation is live. A remnant need not have been recorded before.

The orphan scan raises it. The scan runs at these times:

- at [`kkd`](appendix-a-glossary.md#kkd) start, before any thread is reported `Active`, and whenever the `server_instance_id` changes;
- before provisioning a replacement terminal group or opening a gate for a replacement incarnation;
- before any step that forgets or deletes a jj workspace, where it runs together with the holder scan.

Processes that are members of a container on the current server instance are terminal members, not orphans, except a harness remnant under a live `agent` launcher. That holds for a bound terminal group and for an [unbound container](appendix-a-glossary.md#unbound-container) alike.

While the issue is open, kiki blocks exactly replacement, materialization, and deletion for that thread: it starts no replacement agent and provisions no replacement terminal group for that workspace, changes no files there, and deletes nothing. It offers:

- **[`terminate-orphans`](appendix-a-glossary.md#terminate-orphans).** This plan needs a one-shot approval.
  - For a survivor, it uses the recorded identities.
  - For a harness remnant, it runs freeze discovery rooted at the `agent` launcher, which finds and stops the launcher's descendants. The launcher itself is left alone.
  - Either way, kiki records `FreezeDiscovery` rows under the approval, so every process it will signal is on record first.
  - It terminates those processes and no others, then verifies their exit within `[timeouts] verified_exit`.
  - The issue clears only on [verified exit](appendix-a-glossary.md#verified-exit). If exit cannot be verified, the issue stays.
- **Leave blocked.** Nothing is signalled. The thread stays blocked, and the issue stays open until a later diagnosis finds the processes gone.

#### Holders kiki never recorded

An unrecorded same-UID [holder](appendix-a-glossary.md#holder) of the workspace is not `OrphanedProcess` and never blocks an `Active` thread's boundaries. It matters only to a plan that deletes the workspace: close, destroy, `close-without-terminal`, and the failed-create and failed-reopen cleanups.

- There the result is `Unknown`, and the files are kept, unless the approved plan names that exact holder identity as accepted. The caller names it with `--accept-holder <pid>`, and the plan then carries the `outside-holders` risk label.
- A holder the plan did not name is drift.
- The diagnosis reports each such holder's pid, its command line, and the step that clears it.
- Kiki never [signals](<https://en.wikipedia.org/wiki/Signal_(IPC)>) a process whose identity it did not record. (A harness remnant is recorded by freeze discovery under the `terminate-orphans` approval before it is signalled.)
- The scan does not count `kkd`, its own child processes, or the invoking `kk` process.
- The scan cannot see writers running as another user.

### Failed creation and reopen

Automatic compensation (undoing the finished steps) of a failed `kk new` or `kk reopen` is narrow. Kiki closes the provisioned group and removes the new jj workspace on its own only while all three of these hold:

- the [launch gate](appendix-a-glossary.md#launch-gate) was never activated;
- [`ProcessSupervisor`](appendix-a-glossary.md#processsupervisor) shows the group holds nothing but kiki's own blocked launchers;
- the workspace still equals its initial materialization.

Otherwise the [saga](appendix-a-glossary.md#saga) stops with its projections intact: `CreateFailed` for creation, and for reopen the outcome defined in [Threads](03-threads.md#reopen).

`kk repair` then offers the [`cleanup-failed-create`](appendix-a-glossary.md#cleanup-failed-create) plan, or [`cleanup-failed-reopen`](appendix-a-glossary.md#cleanup-failed-reopen) for a reopen.

- It uses the close machinery: freeze, loss inventory, final proof, terminate, verified exit.
- It requires one-shot approval with the same container-scope statement as close.

`CreateFailed` has no retry plan. Its exit is `cleanup-failed-create`; after that, `kk new` is run again.

#### A failed terminal restart

A [`restart-terminal`](appendix-a-glossary.md#restart-terminal) can fail after it provisioned a new terminal group, for example, when the ready handshake did not arrive within `[timeouts] ready_handshake`. `kk repair` then offers [`cleanup-failed-restart`](appendix-a-glossary.md#cleanup-failed-restart).

- It has the same limits as `cleanup-failed-create`: the close machinery, and a one-shot approval with the container-scope statement.
- It removes the half-made terminal group.
- `TerminalMissing` stays open and the thread stays `ProjectionDiverged` until a later `restart-terminal` succeeds.

Retry plans exist only for the failed states that name one: [`retry-close`](appendix-a-glossary.md#retry-close) for `CloseFailed` and [`retry-destroy`](appendix-a-glossary.md#retry-destroy) for `DestroyFailed`. A failed creation is not retried, and a failed terminal restart is cleaned up and then applied again as a new `restart-terminal`.

### Bookmark plans

Kiki tracks the checkpoint [bookmark](appendix-a-glossary.md#bookmark) through jj's [native rewrite successors](appendix-a-glossary.md#native-successor) without raising an issue (see [Threads](03-threads.md#thread-identity)). A successor is the new commit jj makes when it rewrites an old one.

- A `jj new` or `jj commit` leaves the bookmark where it was. The relationship stays `current` while the new head is empty and undescribed, and becomes the ordinary `behind` once it has content.
- An issue also resolves by itself when a later operation shows the bookmark unconflicted on the expected target, for example after a `jj undo`.

`kk repair` handles only what remains.

There are four per-thread bookmark plans and one repo-level plan. This table is the source for them; other chapters agree with it.

| Plan                                                                       | Offered for                                                                                                                                                                        | Target                                                             | Approval                                                                      | Placement `reason` |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------- | ------------------ |
| [`restore-bookmark`](appendix-a-glossary.md#restore-bookmark)              | `BookmarkMissing`, `BookmarkMoved`, `BookmarkConflicted`, only while the expected target is visible                                                                                | the expected target                                                | none in the thread's own context; one-shot when applied to a different thread | `RepairRestore`    |
| [`adopt-bookmark`](appendix-a-glossary.md#adopt-bookmark)                  | `BookmarkMoved` when the single observed target is the live head or on the owned chain                                                                                             | the observed target                                                | one-shot                                                                      | `RepairAdopt`      |
| [`choose-bookmark-target`](appendix-a-glossary.md#choose-bookmark-target)  | any bookmark issue (`BookmarkMissing`, `BookmarkMoved`, `BookmarkConflicted`, `CheckpointAbandoned`); also a thread with no open issue whose relationship is `ahead` or `diverged` | the live head or an on-chain commit named with `--target <commit>` | one-shot                                                                      | `RepairChoose`     |
| [`unhide-checkpoint`](appendix-a-glossary.md#unhide-checkpoint)            | `CheckpointAbandoned`, only when unhiding would not create a divergent change                                                                                                      | the expected target, made visible again                            | one-shot                                                                      | `RepairUnhide`     |
| [`reanchor-history`](appendix-a-glossary.md#reanchor-history) (repo level) | `OperationHistoryRewritten`                                                                                                                                                        | see [Repository operation history](#repository-operation-history)  | one-shot, repo scope                                                          | `Reanchor`         |

The "placement `reason`" column is the value kiki records on the placement-history row when the plan is applied.

What each issue means:

| issue                                                               | meaning                                                                                                                            |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| [`BookmarkMissing`](appendix-a-glossary.md#bookmarkmissing)         | the bookmark is absent                                                                                                             |
| [`BookmarkMoved`](appendix-a-glossary.md#bookmarkmoved)             | the bookmark names a single commit that is not an accepted successor of the expected target                                        |
| [`BookmarkConflicted`](appendix-a-glossary.md#bookmarkconflicted)   | the bookmark is conflicted or names more than one target; the diagnosis lists every observed target                                |
| [`CheckpointAbandoned`](appendix-a-glossary.md#checkpointabandoned) | the bookmark is absent, the expected target is hidden at the observed operation, and no visible successor is accepted in its place |

Notes on the plans:

- **`restore-bookmark`** puts the bookmark back on the tracked expected target (`bookmark_expected_commit_id`), never on the older placed commit. It never targets a hidden commit, so it is offered only while the expected target is visible. It does not change where publish or reopen will point, so in the thread's own context it uses `ThreadScoped` and needs no approval.
- **`adopt-bookmark`** accepts the single observed target as the checkpoint. It changes where publish and reopen will point, so it requires one-shot approval.
- **`choose-bookmark-target`** sets the bookmark to exactly one commit the caller names with `--target <commit>`: the live head, or a commit on the validated owned chain. Kiki never picks, and neither does a policy rule. It is the exit whenever the expected target is hidden. It is also the exit for a thread that reads `ahead` or `diverged`.
- **`unhide-checkpoint`** first makes the hidden expected target visible again and then places the bookmark on it. It is not offered when unhiding would create a divergent change (two visible commits for one change).

#### Who may move the bookmark where

One rule covers every bookmark move kiki makes:

- **A checkpoint only moves forward.** A checkpoint (at creation, publish, close, or detach) only moves the bookmark forward along the owned chain. It never moves it backward or sideways, and it never passes jj's `--allow-backwards` flag.
- **Adopt and choose may place it anywhere on the chain.** The approved plans `adopt-bookmark` and `choose-bookmark-target` may place the bookmark on the live head or on any commit on the validated owned chain. That includes a commit behind the expected target. These plans may pass `--allow-backwards`.
- **Restore goes back to the expected target.** `restore-bookmark` puts the bookmark back on the expected target. jj may see that as a backward move, so the plan may pass `--allow-backwards`. It still needs no approval in the thread's own context; applied to a different thread, it needs a one-shot approval.
- **Unhide may pass the flag too.** `unhide-checkpoint` may also pass `--allow-backwards`.
- **A backward move is labeled.** Any plan that passes `--allow-backwards` carries the `backward-bookmark` risk label, so a policy rule must accept that label to approve it.
- **Never off the chain.** Kiki never places the bookmark on a commit that is off the owned chain. v1 has no plan for that. The shape is first fixed with jj (for example, a rebase that puts the commit on the chain), and then an adopt or choose plan is applied.

For a `Closed` thread, adopt and choose must also validate the retained owned chain and every follows child, and they advance the archived `thread_head_commit_id` with the checkpoint. The full adoption rule is in [Threads](03-threads.md#projection-divergence-and-repair).

#### An abandoned checkpoint

[`CheckpointAbandoned`](appendix-a-glossary.md#checkpointabandoned) is the case where the checkpoint commit itself is hidden and the bookmark is gone with it. More exactly, three things hold: the bookmark is absent, the expected target is hidden, and no visible successor is accepted. `jj abandon` does this. So does a fetch that finds a merged pull request's remote branch deleted.

A bookmark that is still present, on a commit kiki does not accept, is [`BookmarkMoved`](appendix-a-glossary.md#bookmarkmoved), even when the expected target is hidden. Its exit is `choose-bookmark-target`.

- Its exits are `unhide-checkpoint` and `choose-bookmark-target`. `restore-bookmark` is not offered, because the expected target is hidden.
- Sometimes another bookmark issue is already open, tracking is paused, and the expected target becomes hidden later. Then the open issue stays as it is and no second issue is added. `restore-bookmark` is withdrawn, and `choose-bookmark-target` is the exit.
- A **closed** thread with `CheckpointAbandoned` is common after a squash-merged pull request and a fetch. The thread stays `Closed`; it does not move to `ProjectionDiverged`. It is reported on `kk ls --all` and `kk repair`. It is not a loud attention event, and it blocks only `kk reopen`. It has three exits: `unhide-checkpoint` followed by reopen; `choose-bookmark-target` onto a visible commit of the thread's archived owned chain, followed by reopen; or destroy when that command ships.

#### While an issue is open, and after a plan applies

While a bookmark issue is open on an active thread, checkpoint, publish, close, and detach are blocked for that thread.

Every applied bookmark plan is an explicit placement, alongside creation, publish, close, and detach. Each applied plan:

- appends a placement-history row with the `reason` from the table above;
- sets both the placed checkpoint and the tracked expected target to the chosen commit;
- is verified against the resulting jj operation.

### Repository operation history

jj keeps an [operation log](https://docs.jj-vcs.dev/latest/operation-log/): a history of every change made to the repository. Kiki records operations from that log. `jj op abandon`, and anything else that rewrites the ancestry of the newest operation, can remove or replace operations kiki recorded. (`jj util gc` is not a cause. It only removes operations that are already unreachable.)

Kiki decides that history was rewritten by one test: some recorded operation that was an ancestor of the last recorded [frontier](appendix-a-glossary.md#operation-frontier) is no longer reachable from the current frontier. jj's constant root operation is never counted. This test catches an ordinary `jj op abandon` in the middle of the log, where older operation ids stay the same and newer ones change.

When that happens:

- Kiki [re-anchors](appendix-a-glossary.md#re-anchoring) silently if every thread's bookmark still equals its expected target and every managed workspace's `@` still equals its cached head. (`@` is jj's name for a workspace's current commit.)
- Otherwise it raises one repo-level issue, [`OperationHistoryRewritten`](appendix-a-glossary.md#operationhistoryrewritten), listing the threads that differ. Before approval, it raises no per-thread bookmark issue for the gap.

While `OperationHistoryRewritten` is open, checkpoint, publish, close, detach, and explicit rebase are blocked for the listed threads; head observation continues. Between detection and approval, no anchor row exists. Bookmark classification is paused in that repo, and it resumes from the anchor recorded on approval.

`kk repair --repo` diagnoses the issue and offers the [`reanchor-history`](appendix-a-glossary.md#reanchor-history) plan. `kk repair --repo --apply <plan-id>` applies it under a one-shot approval with repo scope. The plan carries the `history-rewrite` risk label.

The plan works thread by thread. It lists every affected thread with its observed bookmark state. On approval, for each listed thread:

- **The bookmark is usable.** If the bookmark is present, not conflicted, and on the live head or the owned chain, kiki records a fresh placement (`reason = Reanchor`) at the observed commit against the current operation.
- **The bookmark is not usable.** For every other listed thread, kiki raises the matching per-thread issue at the new anchor: `BookmarkMissing`, `BookmarkConflicted`, or `BookmarkMoved`. The ordinary [bookmark plans](#bookmark-plans) then fix it.

## `kk doctor`

`kk doctor` is a diagnostic command. It ships in v1.x.

`--github` checks `gh` installation, authentication, repository resolution, and the permissions the future publish path needs, without mutating GitHub. GitHub failure never changes registration health and never causes `kk init` to fail.

`kk doctor` also reports when the `[automation]` table in the user config file differs from the active policy, as [`kk automation status`](#kk-automation-status) does.

## `kk privacy consent`

`kk privacy consent` manages your permission to send transcript content to an AI provider. It is a v1.x command.

That permission is called [provider-egress consent](appendix-a-glossary.md#provider-egress-consent). It ships with transcript-backed provider features:

- `kk privacy consent list` shows purpose, normalized provider identity, thread scope, disclosure version, grant time, and revocation state for the contextual thread. It never exposes credentials.
- `kk privacy consent grant transcript-mcp` resolves the contextual thread and its managed harness provider.
  - It discloses that same-thread MCP tool results may be sent to that provider.
  - The grant needs a confirmation. On a foreground terminal, the enrolled presenter collects it from a person. With no person, an activated policy rule can give it, and only a rule that names `consent:transcript_mcp` and lists that provider in `providers`. With neither, the command exits with code 3 and records nothing.
  - This pre-grant exists because an agent-facing MCP call cannot open a human prompt.
  - MCP is the [Model Context Protocol](https://modelcontextprotocol.io/), a standard way for an agent to call outside tools.
- `kk privacy consent revoke <purpose> [--provider <identity>]` immediately revokes matching remembered grants for the contextual thread.
  - Omitting `--provider` revokes every provider for that thread and purpose.
  - Revoking only takes permission away. So it needs no approval, and any credential of this user may call it.
  - On a foreground terminal, it shows the exact set first and asks before it revokes. That question is a safeguard against a typing mistake, not an approval. Without a terminal it asks nothing: it revokes the set and prints it.

`kk reopen --catch-up` offers approve-once or remember during its actual payload preview. There is no standalone remembered-grant command for `catch_up`.

A plain config key, the environment, MCP, a generic one-shot approval, and command flags cannot grant [provider egress](appendix-a-glossary.md#provider-egress). Besides a person at the presenter, one thing can: a rule in the activated [automation policy](appendix-a-glossary.md#automation-policy) that names `consent:<purpose>` and lists the provider.

- `*` in a rule's `operations` never matches a consent operation, and there is no `*` for providers.
- The rule counts only after `kk automation apply` activates it.
- A consent given by a rule is recorded like any other, and `kk privacy consent list` shows it.
- Revoking that record does not change the policy. While the rule stays active, it can give the consent again. To stop that, remove the rule and apply the policy again.

Revocation prevents future sends. It cannot recall content already delivered.

## `kk audit`

The audit commands show kiki's record of which operations were requested and what happened to each one. There are two: `kk thread audit` for one thread, and `kk audit log` for a wider view.

### One thread

`kk thread audit [<thread>]` reads an operational audit slice. For the contextual thread, its default output is non-sensitive and uses [`ThreadScoped`](appendix-a-glossary.md#threadscoped-credential): timestamp, method, declared scope, and outcome, with argument and approval details redacted.

Three cases require a one-shot [approval](#foreground-approval-flow) bound to the exact filters and an immutable result snapshot:

- an explicitly targeted different thread;
- `--details`;
- any query that exposes arguments.

In a policy rule the operation for these three is `sensitive-read`.

A row for an operation that a policy rule approved shows the rule name, the policy digest, the principal, the operation, and the risk labels.

### A repo, the user, or everything

`kk audit log` reads a broader audit authority, so it always requires a one-shot approval. In a policy rule the operation is `audit-log`. Without a terminal and without a rule that allows the exact query, it exits with code 3 and prints no rows.

Its sources and filters:

- inside a repo, the default source is that repo's [SQLite](https://www.sqlite.org/) `audit_log`;
- `--user` selects the per-user `user_audit_log` sink, which records bootstrap, registry-wide, unknown-repo, and pre-resolution attempts. It also records policy activation and revocation, and the creation, rotation, and revocation of automation credentials;
- `--all-repos` selects every registered repo plus the user sink;
- `--since <time>`, `--method <name>`, and `--outcome <value>` constrain the approved query;
- `--json` changes rendering only, and it is included in the approval digest.

Rows identify the authoritative SQLite source. Kiki does not read or merge an `audit.log` file, and this command is not an export authority. A future explicit export may render rows elsewhere without making that output authoritative.

## `kk config`

`kk config` shows kiki's settings and where each value came from.

The [acceptance slice](appendix-a-glossary.md#acceptance-slice) provides `kk config get|show` for the minimal supported configuration; see [Configuration](11-configuration.md). `set|unset|edit` and the full layering surface are v1.x additions.

- `kk config get <key>` reports the effective value and the layer it came from.
- `kk config show` prints the whole merged configuration. Beside each value it names the layer the value came from.
- Unknown keys warn rather than error.
- Structural key changes must tell the user which of three things applies: they hot-reload, they take effect at the next lifecycle event, or they require daemon restart.

## Deferred thread management commands

Scope tiers are recorded in [Orientation](01-orientation.md).

The headless surface is part of the [acceptance slice](appendix-a-glossary.md#acceptance-slice), because kiki's own end-to-end tests need approvals with no person present. [Build Sequencing](15-build-sequencing.md) stages it:

- **Stage 1:** [`kk daemon install`](#kk-daemon-install), [`kk automation`](#kk-automation) with the policy engine and automation credentials, [`kk events`](#kk-events), [`--json`](#output-for-scripts), and the [exit codes](#exit-codes).
- **Stage 2:** [`kk prompt`](#kk-prompt), [`kk wait`](#kk-wait), and the `command` notification provider (see [Configuration](11-configuration.md#the-command-provider)).
- **With the features they gate:** `publish` rules arrive with `kk publish`, and `consent:<purpose>` rules arrive with the transcript features.

Two groups of commands are not in the acceptance slice:

- **v1.x:** `kk publish`, `kk thread transcript`, `kk thread comments`, `kk thread destroy`, `kk thread interrupt`, `kk thread restart --harness`, `kk thread describe --refresh`, `kk doctor`, and `kk privacy consent`.
- **Out of v1:** follows graph surgery, `kk thread attach` and `kk thread reparent`. `kk thread attach` would re-establish a follows link; it is unrelated to [`kk attach`](#kk-attach), which opens a terminal view.

Re-pointing a thread at a moved workspace is the [`repoint-workspace`](appendix-a-glossary.md#repoint-workspace) plan in `kk repair`, so recovery does not need a second command protocol.

## Internal commands

One `kk` subcommand is hidden. It does not appear in help output, and people do not run it.

- **`kk ui-pane`** is the long-lived process that draws the v1.x [`ui` role pane](appendix-a-glossary.md#ui-role-pane). Only the `ui` [pane launcher](appendix-a-glossary.md#pane-launcher) runs it: the launcher claims the `ui` role and then replaces itself with `kk ui-pane`.
  - It reads through [pinned reads](appendix-a-glossary.md#pinned-read) only and never snapshots a working copy.
  - Its keys are navigation only.
  - Run by hand outside a `ui` role pane, it exits with an error.

See [Interface](10-interface/spec.md#ui-pane) for what the pane shows.

## Repo registry

`kk repo unregister <path>` removes a repo from the per-user registry, kiki's list of the repositories it manages. It is the explicit counterpart to `kk init`.

### What it removes

By default, `kk repo unregister` removes two things:

- the row in `~/.config/kiki/state.db`'s `repos` table;
- the centralized state directory at `~/.config/kiki/repos/<repo_id>/` (threads, optional transcript rows, SQLite audit rows, credentials, per-thread error logs, and any workspace-recovery bundles).

The action is irreversible: there is no kiki-managed undo, matching the shape of `kk thread destroy` (see [Threads · destroy](03-threads.md#destroy)).

- It therefore requires a one-shot [approval](#foreground-approval-flow) bound to the canonical repo path, the repo id, and whether state is retained.
- In a policy rule the operation is `unregister`. Without a terminal and without a rule that allows the plan, the command exits with code 3 and removes nothing.
- If recovery bundles exist, the command prints their paths in its preflight; `--keep-state` is required to retain them.

### Keeping the state directory

`--keep-state` keeps the centralized state directory on disk while still removing the registry row.

- The preserved directory becomes orphaned bytes. It is useful only to an operator who wants to inspect or copy the contents before deleting them by hand.
- It does **not** enable any kiki-managed recovery. A future `kk init` at the same canonical path mints a fresh `repo_id` and a fresh state directory, and the preserved directory has no link to the new registration.
- The flag exists because losing transcripts and audit logs to a mistyped path is a high cost.

`--keep-state` is the careful-operator escape hatch, not a recovery contract.

### Moved repositories

Source-repo moves are not auto-detected. kiki leaves no breadcrumb inside the source tree, so a moved repo looks unregistered to `kk` from the new path. v1 offers two recoveries:

- Move the source tree back so its path matches the registered `canonical_path`.
- Or run `kk repo unregister` (with `--keep-state` first if you want to copy state out before re-init) and then `kk init` at the new location, which starts a fresh registration with a new `repo_id`.

A move-aware `kk repo relocate` command is not in v1.
