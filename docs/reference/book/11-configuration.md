# Configuration

Configuration is how you change kiki's settings. It is written in [TOML](https://toml.io/), a plain-text settings format. Settings can come from several sources. For each key, the highest-priority source that sets it determines the value.

Configuration inspection must show each effective value and the source that set it. This lets users trace an unexpected setting.

The [acceptance slice](appendix-a-glossary.md#acceptance-slice) is the part of kiki that v1 needs to be accepted. It implements only the layers and keys needed to:

- run the [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) (kiki's background program, [`kkd`](appendix-a-glossary.md#kkd));
- select a [harness](appendix-a-glossary.md#harness) (the coding-agent program kiki runs in a thread);
- locate the terminal runtime;
- place state and workspaces;
- deliver critical notifications;
- approve operations when no human is present, through the [automation policy](appendix-a-glossary.md#automation-policy). This is part of running kiki [headless](appendix-a-glossary.md#headless): with no UI attached and with no person at the keyboard.

The full layering and the feature-specific sections below are staged according to the sole scope ledger in [Orientation](01-orientation.md).

## Precedence

Precedence is the order in which layers win. From lowest to highest:

1. hardcoded defaults
2. user config: `~/.config/kiki/config.toml`
3. repo-local config: `~/.config/kiki/repos/<repo_id>/config.toml` (it lives outside the repository, so it is never committed)
4. `KIKI_*` environment
5. CLI flags

"`KIKI_*` environment" means [environment variables](https://en.wikipedia.org/wiki/Environment_variable) whose names start with `KIKI_`. The exact forms are:

- **Environment variable:** `KIKI_<SECTION>_<KEY>`, in upper case. For example, `KIKI_AGENT_DEFAULT_HARNESS=codex` sets `[agent] default_harness`.
- **CLI flag:** `--config section.key=value`. For example, `--config agent.default_harness=codex`.

### Keys that only the user config file can set

Some keys count only when they are in the user config file. There are two groups.

- **Keys that are structural to the daemon:** every key in `[terminal]`, and `[paths] herdr_dir`. They shape the one terminal server that [`kkd`](appendix-a-glossary.md#kkd) runs for the user, and `kkd` does not run inside anyone's terminal.
- **Keys that grant authority or run a program:** the whole `[automation]` section, and `[notifications] command`.
  - `[automation]` holds the rules that let kiki approve an operation with no human present. See [Automation keys](#automation-keys).
  - `[notifications] command` names a program that `kkd` runs. See [The `command` provider](#the-command-provider).
  - A repository, a thread, or the terminal that happened to run `kk` must not be able to set either one.

For these keys, only the user config file counts. The environment and the flags of the terminal that invoked `kk` are ignored for them, with a warning. Repo-local config is ignored for them too. So are the two v1.x layers described next, repo-shared config and per-thread config.

Being in the user config file is not enough for `[automation]`. The section does nothing until it is activated. See [The file does nothing until it is activated](#the-file-does-nothing-until-it-is-activated).

Those five layers are the acceptance-slice precedence. v1.x ([later polish](appendix-a-glossary.md#v1-x-polish)) inserts two more layers:

- repo-shared committed config (`<repo>/.kiki.toml`), below user config;
- per-thread [SQLite](https://www.sqlite.org/) config, above repo-local config.

Adding those layers must not change the relative order of the acceptance layers.

## Commands

The acceptance slice supports:

- `get`
- `show`

`kk config get <key>` reports both the effective value and the layer it came from.

`kk config show` prints the whole merged configuration. Beside each value it names the layer the value came from.

`set`, `unset`, and `edit` ship with the v1.x full-layering surface. Until then, users edit the user or repo-local TOML file directly and use `show` to verify the result.

Unknown keys warn, not error.

## Structural keys

A changed setting does not always apply right away. This section says when each kind of key takes effect.

- **Structural keys** require a daemon restart. Examples are the daemon socket and the state-database paths.
- **Terminal-server keys** are structural too, but a daemon restart is not enough to apply them. They are `[terminal] session`, `[terminal] herdr_bin`, and `[paths] herdr_dir`. If one changes while a [server instance](appendix-a-glossary.md#server-instance) is open, `kkd` does not start a second server. It keeps the old one, reports that a change is pending, and requires the approved [`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server) plan (`kk repair --server`). See [Terminal keys](#terminal-keys).
- **The default harness** takes effect at the next `kk new`. It does not restart live threads.
- **`workspaces_root`** applies to the next `kk new`. Existing workspaces stay where they are.
- **`[timeouts]` keys and `[cascade] delivery_attempts`** reload live. A new value applies to the next wait that starts.
- **`[automation]`** never reloads. Not even a daemon restart applies an edit. A changed section takes effect only when `kk automation apply` activates it. See [Automation keys](#automation-keys).
- **Cosmetic keys** may hot-reload: the change applies immediately.
- **Some keys** take effect at the next thread-lifecycle event (`kk new` or `kk reopen`) rather than hot-reloading or requiring a daemon restart.
- **Deferred UI keys** may instead take effect at the next overlay open.

Keys that wait for a lifecycle event or an overlay open are not reapplied retroactively to live [terminal groups](appendix-a-glossary.md#terminal-group) or [incarnations](appendix-a-glossary.md#incarnation). A terminal group is the set of terminals that belongs to one thread. An incarnation is one running lifetime of a thread's agent.

Configuration is deserialized (read from text) into strongly typed [Rust](https://www.rust-lang.org/) structs. Each field declares its reload behavior as `hot`, `lifecycle`, or `restart`. The daemon uses that metadata to decide what happens when a value changes:

- apply it immediately;
- wait for the next lifecycle event; or
- warn and name the required restart.

Values merge across layers in one of two ways:

- Map-like config values merge by key across layers.
- List-like values replace as a unit, unless a later chapter explicitly gives that key append semantics.

## Sections

A TOML file groups keys into named sections, written in square brackets.

Acceptance-slice sections:

- `[agent]`: the default harness and harness-specific args.
  - The key is `default_harness = "claude-code" | "codex"`, initially `claude-code`. These name [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) and [Codex](https://github.com/openai/codex).
  - Set `[agent.args] codex` to a list of arguments, one string per argument. For example, in `~/.config/kiki/config.toml`:

    ```toml
    [agent.args]
    codex = ["--ask-for-approval", "never", "--sandbox", "workspace-write"]
    ```

    This asks Codex to return a failure when a command needs extra permission. Set the list before creating the thread. The creation plan displays the effective settings and binds the ordered list to its digest. Kiki records those approved launch arguments with the thread and uses them on reopen and replacement. A repeated `--harness-arg` supplies a replacement list for that launch configuration. The adapter refuses settings that defeat its hook isolation or conflict with enforced host restrictions before releasing the launch gate.
- `[notifications]`: per-event `loud | soft | silent` behavior for acceptance-slice [attention events](appendix-a-glossary.md#attention-event), plus `os_provider` (`auto | notify-rust | osascript | herdr | command | off`) and `command`.
  - Per-event keys hot-reload.
  - `os_provider` and `command` resolve at the next dispatch.
  - `command` is the program the `command` provider runs. Only the user config file can set it. The `command` provider ships in Stage 2 of the [build sequence](15-build-sequencing.md).
  - See [Notification keys](#notification-keys) and [Observability](12-observability.md).
- `[automation]`: the rules of the [automation policy](appendix-a-glossary.md#automation-policy). An activated rule can approve an operation in place of a human. Only the user config file can set it, and it does nothing until it is activated. See [Automation keys](#automation-keys).
- `[paths]`: overrides for state, socket, generated-Herdr-configuration, and workspace-root paths.
- `[terminal]`: where the [Herdr](appendix-a-glossary.md#herdr) executable is and which named Herdr server kiki owns. Herdr is the [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer) that hosts kiki's terminals. See [Terminal keys](#terminal-keys).
- `[timeouts]`: how long kiki waits at each step that has a time limit. See [Timeout keys](#timeout-keys).
- `[cascade]`: `delivery_attempts`, the limit on delivery retries. See [Timeout keys](#timeout-keys).

Deferred v1.x sections:

- `[github]`: backend selection (initially `gh`, the [GitHub CLI](https://cli.github.com/)) and, once polling ships, poll cadence.
- `[autorename]`: [auto-describe](appendix-a-glossary.md#auto-describe) and [auto-rename](appendix-a-glossary.md#auto-rename) triggers and cadence. The metadata ledger and execution loop ship together with that feature; they are not acceptance foundations.
- `[ui]`: personal-preference keys for the [overlay TUI](appendix-a-glossary.md#overlay-tui), the optional [`ui` role pane](appendix-a-glossary.md#ui-role-pane), and the `shell` [role pane](appendix-a-glossary.md#role-pane).
- `[reopen]`: `catchup_pairs` (default `10`) controls explicitly requested `kk reopen --catch-up` text.
- `[ai]`: provider, model, and credential-source settings for provider-backed v1.x features.

### Consent is not configuration

Transcript-egress consent is your permission to send [transcript](appendix-a-glossary.md#thread-transcript) content to an AI provider. Remembered transcript-egress consent is durable privacy state, not a configuration layer.

- It is keyed in the registered repo's SQLite database by thread, normalized provider identity, purpose (`catch_up | transcript_mcp`), and disclosure version.
- You can inspect it, grant it for MCP (the [Model Context Protocol](https://modelcontextprotocol.io/)), and revoke it through `kk privacy consent`.
- No plain configuration key can grant it. That holds for every layer: the user config file, repo-local config, committed TOML, the environment, and CLI flags. MCP cannot grant it, and neither can a generic operational approval.
- A grant comes from one of two places:
  - the enrolled foreground presenter, after the provider-specific disclosure. (The presenter is the [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter): the enrolled local program that shows a plan to a person at the keyboard and collects the answer.)
  - an activated [automation policy](appendix-a-glossary.md#automation-policy) rule that names both the purpose and the provider.

The second path exists so that a machine with no human can still use a provider-backed feature. It is deliberately narrow:

- The rule must list the operation as `consent:<purpose>`, for example `consent:catch_up`. A `*` in `operations` never matches a consent operation.
- The rule must also carry `providers`, a list of normalized provider identities. A consent rule without `providers` is invalid. There is no `*` for providers.
- The canonical rule shown at activation includes the current disclosure version. A disclosure change requires the operator to apply the rule again. Writing it in the file grants nothing. See [The file does nothing until it is activated](#the-file-does-nothing-until-it-is-activated).
- The rule stands in for the human's confirmation of that one grant. The grant is still recorded in the repo database under the same key, and `kk privacy consent` can still inspect and revoke it.

Consent rules ship with the provider-backed features they gate, which are v1.x. [Automation keys](#automation-keys) owns the rule schema.

## Notification keys

`[notifications]` holds one key per [attention event](appendix-a-glossary.md#attention-event). Each key takes a level: `loud`, `soft`, or `silent`. It also holds two transport keys, `os_provider` and `command`. This chapter owns the key names and what each level does. [Observability](12-observability.md#attention-events) describes the events themselves.

### What each level does

kiki has five places to show an event. A level decides which of them it uses.

| Level    | OS notification                                           | Herdr toast                        | Notification command                 | Overlay toast (v1.x) | Status mark |
| -------- | --------------------------------------------------------- | ---------------------------------- | ------------------------------------ | -------------------- | ----------- |
| `loud`   | yes, unless `os_provider` is `herdr`, `command`, or `off` | only when `os_provider` is `herdr` | only when `os_provider` is `command` | yes                  | yes         |
| `soft`   | no                                                        | no                                 | no                                   | yes                  | yes         |
| `silent` | no                                                        | no                                 | no                                   | no                   | yes         |

In this table, "`os_provider` is" means the value after `auto` has been resolved. See [Transport keys](#transport-keys).

- **OS notification, Herdr toast, and notification command** are the three forms of the configured transport, `os_provider`. Exactly one of them is used for a `loud` event: the OS notification on a desktop by default, the Herdr [toast](appendix-a-glossary.md#toast) when `os_provider = "herdr"`, or the notification command when `os_provider = "command"`. With `os_provider = "off"`, none is sent.
- **Overlay toast** is kiki's own toast inside the [overlay](appendix-a-glossary.md#overlay-tui). It appears only while an overlay is open, and only after the overlay ships.
- **Status mark** is the event's durable state, shown by `kk ls`, `kk status`, `kk events`, and the sidebar projection. No level turns it off. A level changes how hard kiki tries to get your attention; it never hides state.

### Transport keys

| Key           | Type            | Default | Who can set it                 |
| ------------- | --------------- | ------- | ------------------------------ |
| `os_provider` | string          | `auto`  | any layer                      |
| `command`     | list of strings | empty   | the user config file, and only |

`os_provider` takes `auto`, `notify-rust`, `osascript`, `herdr`, `command`, or `off`. [Observability](12-observability.md#choosing-a-provider) describes each provider.

`auto` picks a provider each time kiki sends a notification. The choice depends on whether the host has a desktop session. A desktop session is a logged-in graphical session where the operating system can draw a notification. A server reached only over SSH, a container, and a CI runner have none.

| Host                 | `command` is set | `auto` resolves to |
| -------------------- | ---------------- | ------------------ |
| Linux with a desktop | either           | `notify-rust`      |
| macOS with a desktop | either           | `osascript`        |
| no desktop session   | yes              | `command`          |
| no desktop session   | no               | `off`              |

`auto` never resolves to `herdr`.

### The `command` provider

The `command` provider hands each `loud` event to a program you choose. It is how a headless host tells something outside kiki that a thread needs attention: a chat webhook, a pager, or a log collector. It ships in Stage 2 of the [build sequence](15-build-sequencing.md).

```toml
[notifications]
os_provider = "command"
command     = ["/usr/local/bin/kiki-notify", "--channel", "builds"]
```

- `command` is a list. The first item is the program and the rest are its arguments. Give the program's full path. `kkd` runs the program directly, not through a shell.
- `kkd` runs it once for each `loud` event. It writes the event to the program's standard input as one JSON object. This is the same object that [`kk events --json`](09-commands.md#kk-events) prints for that event.
- `kkd` waits for the program for a short time, the [`notification_command`](#timeout-keys) timeout. A program still running then is stopped.
- `kkd` never retries. A program that fails, or that is stopped at the timeout, loses that one notification. It does not lose the event: the status mark and the event stream still carry it.
- The program runs as you, with the same constructed environment `kkd` gives the terminal server (see [Who starts the server](#who-starts-the-server)). It gets no kiki credential.
- Only the user config file can set `command`, because the key makes `kkd` run a program. A value from repo-local config, the environment, or `--config` is ignored with a warning. `os_provider` itself may still come from any layer; choosing `command` there runs only the program the user config file named.
- If `os_provider` is `command` and `command` is empty, nothing is sent, and `kk config show` warns.

### Event keys

| Key                   | Event                                                                                    | Default  | Tier             |
| --------------------- | ---------------------------------------------------------------------------------------- | -------- | ---------------- |
| `agent_blocked`       | the agent is waiting on a permission prompt                                              | `loud`   | acceptance slice |
| `agent_crashed`       | the harness exited or crashed under a live launcher                                      | `loud`   | acceptance slice |
| `cascade_conflicted`  | a cascade reconciliation exposed textual conflicts                                       | `loud`   | acceptance slice |
| `lifecycle_failed`    | a lifecycle operation failed (`CreateFailed`, `CloseFailed`, a failed reopen or restart) | `loud`   | acceptance slice |
| `projection_issue`    | a [projection issue](appendix-a-glossary.md#projection-issue) opened on an active thread | `loud`   | acceptance slice |
| `delivery_exhausted`  | an intent's delivery attempts are [exhausted](appendix-a-glossary.md#exhausted-intent)   | `loud`   | acceptance slice |
| `parent_abandoned`    | a follows parent's head or owned revisions were abandoned locally                        | `loud`   | acceptance slice |
| `goal_complete`       | the agent reports its goal complete                                                      | `soft`   | acceptance slice |
| `agent_silent`        | the agent has been silent past the silence threshold                                     | `silent` | v1.x             |
| `parent_merged`       | a follows parent's pull request merged                                                   | `loud`   | v1.x             |
| `pr_check_failed`     | a pull-request check failed                                                              | `loud`   | v1.x             |
| `external_force_push` | an external force-push of the thread's branch was seen                                   | `loud`   | v1.x             |
| `metadata_written`    | an auto-rename or auto-describe write completed                                          | `silent` | v1.x             |

Notes:

- `agent_blocked` depends on the harness adapter proving its permission-prompt signal. For a harness without that proof, permission-prompt detection is v1.x. A crashed agent still shows `blocked` through `agent_crashed`. See [Observability](12-observability.md#attention-events).
- A closed thread's `CheckpointAbandoned` issue does not fire `projection_issue`. It is reported on `kk ls --all` and `kk repair` only.
- `goal_complete` at `soft` is a status mark plus an overlay toast. Before the overlay ships, only the status mark shows.
- The acceptance-slice events are the ones in the scope ledger in [Orientation](01-orientation.md): a blocked or crashed agent, a conflicted cascade, an exhausted delivery, a followed parent abandoned, a failed lifecycle operation, and a projection issue. `goal_complete` is also in the slice, as a `soft` status mark with an overlay toast.
- v1.x keys are ignored with a warning until their feature ships. The state behind a v1.x event still shows in `kk ls` and `kk status` where the slice already tracks it.
- The silence threshold for `agent_silent` is a separate deferred key.

## Automation keys

`[automation]` holds the rules of the [automation policy](appendix-a-glossary.md#automation-policy). The policy is how kiki runs with no human present.

Many kiki operations need a one-shot approval before they run. Normally a person gives it: they read the plan in a terminal and confirm it. That is a [`HumanApproval`](appendix-a-glossary.md#human-approval). A policy rule can stand in for that person. When an activated rule allows the exact plan, `kkd` issues a [`PolicyApproval`](appendix-a-glossary.md#policy-approval) and the operation goes ahead without a prompt.

This chapter owns the rule schema: every key, its allowed values, and its default. [Authority](04-authority.md#automation-policy) owns what a rule means: how `kkd` evaluates it, what a [`PolicyApproval`](04-authority.md#policyapproval) is bound to, and what a policy can never do. [Commands](09-commands.md#kk-automation) owns `kk automation`.

Three facts frame everything below:

- **The default is no policy.** With an empty or absent `[automation]` section, kiki asks a human for every approval, and a caller with no terminal is refused.
- **A rule replaces only the human's confirmation.** Every safety check still runs: the plan, its digest, the drift and expiry checks, the freeze, the holder scan, and the final proof. No rule can make kiki run a plan that those checks refuse.
- **Only the user config file counts.** See [Keys that only the user config file can set](#keys-that-only-the-user-config-file-can-set).

The policy engine and `kk automation` are in the acceptance slice, in Stage 1 of the [build sequence](15-build-sequencing.md). kiki's own end-to-end tests need unattended approvals.

### The file does nothing until it is activated

Editing `[automation]` changes nothing by itself. `kkd` never reads the section to decide an approval. It decides from a stored copy, and only one command writes that copy:

1. You edit `[automation]` in `~/.config/kiki/config.toml`.
2. You run `kk automation apply`. `kkd` reads the section, puts it in a canonical form, and computes a digest of it.
3. The activation must be approved in one of two ways:
   - a person confirms it in a foreground terminal, where the enrolled [`ApprovalPresenter`](appendix-a-glossary.md#approvalpresenter) shows the full policy and how it differs from the active one; or
   - the caller passes the Admin bootstrap credential with `--admin-credential-file <path>`. This is the path for a machine that never has a human.
4. `kkd` stores the activated policy. From then on it evaluates that stored copy and nothing else.

A `PolicyApproval` can never approve an activation. A policy cannot widen itself.

`kk automation status` shows the active policy and says whether the file now differs from it. `kk automation revoke` clears the active policy. Revoking only removes authority, so it needs no approval, and any credential of this user may run it.

This step is why an agent cannot give itself authority by editing a config file. It is hygiene, not a security boundary: kiki's processes and the agents all run as the same user, and kiki does not claim to stop a hostile process running as that user. [Authority](04-authority.md#activating-a-policy) owns the full activation contract.

### Rule keys

A policy is a list of rules. Each rule is one `[[automation.rule]]` table. The double brackets are TOML's way of writing one entry of a list. `[automation]` has no other keys.

| Key          | Type            | Allowed values                                                                       | Default                               |
| ------------ | --------------- | ------------------------------------------------------------------------------------ | ------------------------------------- |
| `name`       | string          | any non-empty string, unique among the rules                                         | none; required                        |
| `principals` | list of strings | see [`principals`](#principals)                                                      | none; required                        |
| `repos`      | list of strings | repo ids, canonical repo paths, or `*`                                               | none; required                        |
| `operations` | list of strings | see [`operations`](#operations)                                                      | none; required                        |
| `accept`     | list of strings | [risk labels](appendix-a-glossary.md#risk-label), or `*`. Used by `allow` rules only | empty: the rule accepts no risk label |
| `effect`     | string          | `allow` or `require-human`                                                           | none; required                        |
| `providers`  | list of strings | normalized provider identities                                                       | empty; required on a consent rule     |

`name` identifies the rule. It appears in every audit row the rule produces and in the message `kk` prints when the rule approves or refuses a plan.

`repos` says which registered repos the rule covers. A repo id is the UUID that `kk init` assigned. A canonical repo path is the repo's real path with symbolic links resolved. `kk init` matches its canonical path or `*` before registration. The user-wide `replace-terminal-server` plan requires `repos = ["*"]` because it can stop agents across every repo.

`kk automation apply` checks the whole section before it activates anything. It refuses the policy if a rule lacks a required key, repeats a `name`, uses a value outside the allowed set, or has a key this table does not list. The active policy then stays as it was. This is stricter than the general rule that unknown keys only warn. A mistyped key in a rule about authority must not pass silently.

#### `principals`

A principal is who is asking. A rule matches a caller when the caller is at least one of the principals it lists.

| Value               | The caller is…                                                                                                                  |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `credential:<name>` | a process that presents the [automation credential](appendix-a-glossary.md#automation-credential) called `<name>`               |
| `thread:self`       | a thread-scoped caller, such as a thread's agent, acting on its own thread                                                      |
| `thread:descendant` | a thread-scoped caller acting on a thread that [follows](appendix-a-glossary.md#follows) its own thread, directly or indirectly |
| `thread:any`        | a thread-scoped caller acting on any thread in its repo, or creating a thread there                                             |
| `registration`      | a caller that holds only the repo's registration credential                                                                     |
| `*`                 | any caller at all                                                                                                               |

An automation credential is a named credential made for scripts. It is created with `kk automation credential create <name>` and kept in `~/.config/kiki/automation/<name>.cred`. kiki never gives it to an agent. An agent uses its thread credential. Rules can match it through a `thread:` principal or the wildcard `*`.

A `thread:` principal covers any holder of the thread's credential. That is the thread's agent, and it is also a person who runs `kk` in that thread's workspace. kiki cannot tell the two apart, so a `thread:` rule applies to both.

#### `operations`

An operation is the kind of thing being approved. A rule matches a plan when the plan's operation is in the rule's list.

| Value                | Approves…                                                                                          |
| -------------------- | -------------------------------------------------------------------------------------------------- |
| `init`               | registering a repo with `kk init`                                                                  |
| `new`                | creating a thread with `kk new`                                                                    |
| `reopen`             | `kk reopen`                                                                                        |
| `close`              | `kk close`                                                                                         |
| `destroy`            | `kk thread destroy`                                                                                |
| `unregister`         | `kk repo unregister`                                                                               |
| `detach`             | `kk thread detach`, where it needs approval                                                        |
| `interrupt`          | `kk thread interrupt`                                                                              |
| `restart`            | `kk thread restart`, where it needs approval                                                       |
| `publish`            | `kk publish` (v1.x)                                                                                |
| `audit-log`          | `kk audit log`                                                                                     |
| `sensitive-read`     | a read of another thread's transcript, diff, PR comments, or detailed audit arguments              |
| `snapshot` | prepare one workspace by recording its fresh tracked edits in jj |
| `prompt` | submit a later user turn to the target’s live agent |
| `thread-op`          | any ordinary change to a thread that needs approval only because the caller is not that thread     |
| `repair:<plan-name>` | one named [repair plan](appendix-a-glossary.md#repair-plan), for example `repair:restart-terminal` |
| `repair:*`           | every repair plan that has a `repair:` name                                                        |
| `consent:<purpose>`  | a transcript-egress consent grant for one purpose (v1.x). Needs `providers`                        |
| `*`                  | every operation above except `consent:<purpose>`                                                   |

`publish` and `consent:<purpose>` rules arrive with the features they gate. [Consent is not configuration](#consent-is-not-configuration) explains the consent rule.

`thread-op` is one name for many small changes. A thread may checkpoint itself, describe itself, or restart its own harness after the harness exited, all with no approval. The same change needs an approval when someone else makes it: a script holding an automation credential, or another thread. `thread-op` is the operation for that case. For a thread-scoped caller the plan carries the `cross-thread` risk label. For an automation credential it carries no label.

Repair plans follow the same split. `repair:<plan-name>` names a plan that needs an approval whoever applies it, such as `restart-terminal` or `terminate-orphans`. A plan that needs no approval in the thread's own context, such as `restart-agent` or `restore-bookmark`, has no `repair:` name. When a caller that is not the thread applies it, the operation is `thread-op`. The [repair table](09-commands.md#every-issue-and-its-plan) in Commands shows which plans need which approval, and [Authority](04-authority.md#the-thread-op-operation) owns the rule.

Policy activation, credential creation or rotation, and changes to an existing daemon installation need Admin or the enrolled presenter. Only Admin can enroll or recover the presenter. None of these setup actions accepts a policy approval.

#### `accept`

Some plans carry risk. `kkd` works out the risk of each plan before it asks for approval and attaches a [risk label](appendix-a-glossary.md#risk-label) for each kind. For example, a close that would stop running processes carries `live-processes`, and a plan that would lose uncommitted work carries `work-loss`. [Authority](04-authority.md#risk-labels) owns the closed list of labels and what each one means.

`accept` lists the labels an `allow` rule is willing to take on. An `allow` rule matches a plan only if every label on the plan is in the rule's `accept` list. With `accept` left empty, the rule matches only plans that carry no label.

Only `allow` rules use `accept`. A `require-human` rule ignores it. Such a rule matches on `principals`, `repos`, and `operations`, plus the provider for a consent rule. It applies whatever labels the plan carries.

#### `effect`

`effect` says what a matching rule does.

- `allow`: `kkd` approves the plan with a `PolicyApproval`.
- `require-human`: a person must confirm the plan, as if no policy existed.

When several rules match one plan, `require-human` wins over any `allow`. The order of the rules in the file does not matter. When no rule matches, a person must confirm.

So a plan ends in one of three ways:

| Result                                                  | What `kk` does                                                                                                                                                                     |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| allowed by a rule                                       | prints the plan and "approved by rule `<name>`", then runs it. No prompt. `--confirm` forces the human prompt anyway                                                               |
| a human is required, and `kk` has a foreground terminal | shows the ordinary approval prompt                                                                                                                                                 |
| a human is required, and `kk` has no terminal           | refuses with [exit code](09-commands.md#exit-codes) 3. The message names the operation, the plan's risk labels, and the reason: no rule matched, or rule `<name>` requires a human |

### A worked example

```toml
[[automation.rule]]
name       = "ci-lifecycle"
principals = ["credential:ci"]
repos      = ["*"]
operations = ["init", "new", "reopen", "close", "repair:restart-terminal"]
accept     = ["live-processes"]
effect     = "allow"

[[automation.rule]]
name       = "people-destroy-threads"
principals = ["*"]
repos      = ["*"]
operations = ["destroy"]
effect     = "require-human"
```

The first rule lets a script holding the `ci` automation credential register repos, create threads, reopen them, close them, and restart a thread's missing terminal, in every repo. The second rule says that destroying a thread always needs a person, whoever asks and whatever the risk. It has no `accept` key, because a `require-human` rule ignores risk labels.

After `kk automation apply`, this is what a script holding the `ci` credential sees:

| The script runs…                                                                                          | Labels on the plan            | Result                                                                                                                                    |
| --------------------------------------------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `kk new fix-login -m "…"`                                                                                 | none                          | approved by rule `ci-lifecycle`                                                                                                           |
| `kk close fix-login`, with a shell still running                                                          | `live-processes`              | approved by rule `ci-lifecycle`; the processes are frozen, terminated, and verified gone as in any close                                  |
| `kk close fix-login`, with work the close would lose                                                      | `live-processes`, `work-loss` | refused, exit code 3: no rule matched, because `ci-lifecycle` does not accept `work-loss`                                                 |
| `kk close fix-login`, and an editor outside the thread's terminals opens the workspace after the approval | `live-processes`              | approved by the rule, then refused by the final holder scan with exit code 4. The files are kept. A rule never overrides a safety proof   |
| `kk thread destroy fix-login`                                                                             | any                           | refused, exit code 3: rule `people-destroy-threads` requires a human                                                                      |
| `kk repair`, applying the `terminate-orphans` plan                                                        | `live-processes`              | refused, exit code 3: no rule matched, because `ci-lifecycle` lists only `repair:restart-terminal`                                        |
| `kk repair`, applying the `restart-agent` plan to a harness that exited                                   | none                          | refused, exit code 3: no rule matched. The script is not the thread, so the operation is `thread-op`, and `ci-lifecycle` does not list it |

An agent in a thread gets nothing from this policy. No rule names a `thread:` principal, so every approval an agent asks for still needs a person.

### What `*` gives away

Every key that takes a list also takes `*`, and kiki does not stop you from using it everywhere:

```toml
[[automation.rule]]
name       = "everything"
principals = ["*"]
repos      = ["*"]
operations = ["*"]
accept     = ["*"]
effect     = "allow"
```

Once activated, this rule allows any matching local credential to approve policy-eligible plans except provider consent. Any process running as you can then close and destroy threads, lose uncommitted work, and stop the whole terminal server, with no person asked. That includes every agent and every script an agent starts. The safety proofs still run, and consent still needs its own rule. Nothing else stands in the way.

Each `*` gives away one thing:

- `principals = ["*"]` lets every caller use the rule, agents included.
- `repos = ["*"]` covers every repo, including ones registered later.
- `operations = ["*"]` covers every operation except consent, including operations a later kiki version adds.
- `accept = ["*"]` accepts every risk label, including `work-loss` and labels a later kiki version adds.

Prefer a rule that names one credential, the operations a script really runs, and the labels you have decided to accept.

## Timeout keys

Many steps in kiki wait for something, and each wait has a limit. `[timeouts]` names every one of those limits. When another chapter says a step is "bounded" or has a "deadline", it names one of these keys.

| Key                    | Default | Used for                                                                                                                        |
| ---------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `launcher_report`      | `10s`   | waiting for role launchers to report                                                                                            |
| `ready_handshake`      | `60s`   | launch until the [ready handshake](appendix-a-glossary.md#ready-handshake); expiry is `CreateFailed` (or the restart's failure) |
| `freeze_stabilize`     | `5s`    | the [freeze](appendix-a-glossary.md#freeze) reaching a fixed point (two passes that find the same set of processes)             |
| `frozen_step`          | `30s`   | any single step while processes are frozen                                                                                      |
| `verified_exit`        | `10s`   | waiting for a terminated process to be gone                                                                                     |
| `hook_connect`         | `1s`    | [`kk-hook`](appendix-a-glossary.md#kk-hook) connecting to `kkd` and being admitted                                              |
| `slow_path`            | `30s`   | one reconciliation holding a tool batch (the [slow-path bound](appendix-a-glossary.md#slow-path-bound))                         |
| `frontier_retry`       | `2s`    | [frontier sampler](appendix-a-glossary.md#frontier-sampler) retries                                                             |
| `notification_command` | `5s`    | one run of the [notification command](#the-command-provider); on expiry `kkd` stops the program and does not retry              |

One more limit lives in its own section:

| Key                           | Default | Used for                                                                                                         |
| ----------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------- |
| `[cascade] delivery_attempts` | `3`     | how many times kiki retries a delivery before the intent is [exhausted](appendix-a-glossary.md#exhausted-intent) |

Rules for these keys:

- All of them are user-config keys. They are ignored with a warning in repo-local config.
- They reload live. A new value applies to the next wait that starts; a wait already running keeps the limit it started with.
- Values are durations written as a number and a unit, such as `500ms`, `10s`, or `2m`.
- A `frozen_step` expiry before termination begins takes [verified resume](appendix-a-glossary.md#verified-resume). Once termination has begun, a failure is `CloseFailed` (or the plan's failed state), never a resume.
- On `hook_connect` expiry, the hook denies the tool. A missing barrier marker cannot authorize execution.
- Each harness adapter pins the harness's own hook timeout above `slow_path` plus a margin. Raising `slow_path` therefore takes effect for a thread's harness at its next [incarnation](appendix-a-glossary.md#incarnation).

## Path keys

`[paths]` is the central place to relocate kiki's filesystem footprint: the files and directories kiki uses. All keys are optional; defaults are listed below.

| key               | type   | default                             | scope                                                   |
| ----------------- | ------ | ----------------------------------- | ------------------------------------------------------- |
| `user_state_dir`  | string | `~/.config/kiki/`                   | structural: daemon restart                              |
| `user_state_db`   | string | `<user_state_dir>/state.db`         | structural: daemon restart                              |
| `kkd_socket`      | string | `<user_state_dir>/kkd.sock`         | structural: daemon restart                              |
| `repo_state_dir`  | string | `<user_state_dir>/repos/<repo_id>/` | structural: daemon restart                              |
| `herdr_dir`       | string | `<user_state_dir>/herdr/`           | structural: user config only; `replace-terminal-server` |
| `workspaces_root` | string | `<parent-of-repo>/`                 | applies to the next `kk new`                            |

### The MCP socket and audit tables

`kkd_mcp_socket` (default `<user_state_dir>/kkd-mcp.sock`) is the path of the separate socket for the deferred MCP transcript surface. The key ships with that surface and is ignored with a warning until then.

There is no `audit_log` path key. The audit record lives in database tables, not in a file:

- Attempts resolved to a repo write to that repo database's SQLite `audit_log`.
- Bootstrap, registry-wide, unknown-repo, and pre-resolution attempts write to the per-user database's SQLite `user_audit_log`.
- Each attempt has exactly one authoritative row; neither table is mirrored to a file.

### `workspaces_root`

`workspaces_root` does not embed `<repo>` or `<slug>`. kiki always materializes the [workspace](appendix-a-glossary.md#workspace) (a thread's own directory of files) as `<workspaces_root>/<repo>-kiki-<slug>/`.

For example, setting `workspaces_root = ~/work/kk-workspaces/` puts every thread's workspace under that directory instead of next to its source repo.

### `repo_state_dir`

`repo_state_dir` defaults to a centralized location under `<user_state_dir>`, keyed by the repo's `<repo_id>`. The `<repo_id>` is a [UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier) assigned at `kk init` and recorded in the per-user `repos` table.

Per-repo state lives under that directory:

- the per-repo `state.db` containing audit rows;
- the repo-local `config.toml`;
- `errors/<thread_id>.log`;
- `credentials/` (one file per thread plus the repo's `registration` credential);
- `harness/<thread_id>/` (launch-scoped harness settings);
- `recovery/` (data kiki needs to restore files it changed).

The source repo's own filesystem carries no kiki state. The one exception is the deferred optional `<repo>/.kiki.toml` committed config layer, which may live there when a team deliberately adds one.

### `herdr_dir`

`herdr_dir` holds exactly one thing: the Herdr configuration file kiki generates, `<herdr_dir>/config.toml`. `kkd` passes that file to the [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) through `HERDR_CONFIG_PATH`. The dedicated server is the one Herdr server kiki runs for itself.

`herdr_dir` is not a root for Herdr's other files. Herdr has no configuration-directory option:

- it keeps the named session's socket, saved state, and logs under its own directories, keyed by the session name;
- it shares its plugin registry and state directory with the user's other Herdr use.

Kiki does not redirect `XDG_CONFIG_HOME` or `XDG_STATE_HOME` to change that. (These are the [XDG base directory](https://specifications.freedesktop.org/basedir-spec/latest/) variables that tell programs where to keep settings and state.) The reason is that every pane inherits the server's environment. jj, git, gh, and shells in every thread would then read their configuration from the wrong place.

What separates kiki's server from the user's default Herdr server is therefore a separate server process, socket, saved session, and configuration file, not a separate directory tree.

## Terminal keys

`[terminal]` selects the terminal runtime kiki drives. Both keys are structural to the daemon, so only the user config file counts for them. `KIKI_*` environment variables and `--config` flags from the terminal that invoked `kk` are ignored for them, with a warning. So is repo-local config. The same holds for `[paths] herdr_dir`. (See [Keys that only the user config file can set](#keys-that-only-the-user-config-file-can-set).)

| key         | type   | default           | scope                                                   |
| ----------- | ------ | ----------------- | ------------------------------------------------------- |
| `herdr_bin` | string | `herdr` on `PATH` | structural: user config only; `replace-terminal-server` |
| `session`   | string | `kiki`            | structural: user config only; `replace-terminal-server` |

"`herdr` on `PATH`" means the `PATH` of the constructed environment described under [Who starts the server](#who-starts-the-server), not the `PATH` of the terminal that invoked `kk`.

### Changing a terminal key while a server is running

A change to `session`, `herdr_bin`, or `[paths] herdr_dir` cannot take effect immediately, because the server that is running was started with the old values.

- If a [server instance](appendix-a-glossary.md#server-instance) is open, `kkd` does not start a second server. It keeps the old one and keeps using the old values for it.
- `kkd` reports that a change is pending. `kk repair --server` shows it.
- The change takes effect only through the approved [`replace-terminal-server`](appendix-a-glossary.md#replace-terminal-server) plan, applied with `kk repair --server`. That plan lists every thread and process the replacement stops, stops the old server with verified exit, and starts a new one with the new values.
- If no server instance is open, the new values are used the next time `kkd` starts the server.

### What the two keys mean

`herdr_bin` is the executable [`kkd`](appendix-a-glossary.md#kkd) uses to start the [dedicated server](appendix-a-glossary.md#dedicated-herdr-server) and `kk attach` uses to attach a client.

`session` is the [Herdr](appendix-a-glossary.md#herdr) session name of that server, and it is the server's address. `kkd` starts the server with `--session <name>` and `HERDR_CONFIG_PATH=<herdr_dir>/config.toml`, and nothing else selects it.

- A Herdr session is a server namespace, not a per-thread object; kiki runs exactly one.
- The name must not be `default` or any session name the user already uses.
- `kkd` checks that the longest socket name Herdr derives for it fits the platform's socket-path limit.

### Who starts the server

Only `kkd` starts the server. But the server must outlive `kkd`, so `kkd` does not run it as a child inside its own service unit. It asks the service manager to run the server as a unit of its own:

- on macOS, a separate [launchd](https://en.wikipedia.org/wiki/Launchd) job;
- on Linux, a separate transient [systemd](https://en.wikipedia.org/wiki/Systemd) user unit.

launchd and systemd are the system services that keep background programs running. A "transient" unit is one created at run time by a command, with no unit file on disk.

Some hosts have no user service manager. Many containers and CI runners are like this. There the operator runs `kkd --foreground` under a supervisor of their own choosing, and `kkd` starts the server as a detached process in its own session. ("Detached" means the process is not tied to `kkd`'s own lifetime or terminal.) On macOS reached over SSH with no graphical login, `kkd` uses launchd's per-user domain, not the GUI one. Both modes are unproven and sit behind the same gate described next. A platform mode that fails it is unsupported. See [`kk daemon install`](09-commands.md#kk-daemon-install).

A `kkd` crash, restart, or upgrade must not stop the server, because stopping the server ends every thread's processes. This is a proof gate, not an assumption: the test kills `kkd` under each real service manager, and in the `kkd --foreground` mode, and checks that the server and the agents keep running (see [Testing](14-testing.md)).

`kkd` starts the server with a constructed environment: the user's login baseline of `HOME`, `USER`, `SHELL`, `PATH`, and locale. It never uses the environment of the terminal that invoked `kk`.

- Panes inherit that environment plus Herdr's own variables and each role pane's explicit ones.
- `HERDR_CONFIG_PATH` is visible inside panes.
- `kk attach` uses Herdr's connect-only client mode and never starts a server.
- `kkd` recognises a server it started by the peer identity on its `Open` `terminal_servers` row. A running server `kkd` did not start is unverified. That includes one left by Herdr's own handoff or upgrade. `kkd` ends the old row, which ends its bindings and raises [`TerminalMissing`](appendix-a-glossary.md#terminalmissing), and records the new peer as `Unverified`. It provisions nothing on an unverified server. The fix is the `replace-terminal-server` plan, and after it `restart-terminal` for each thread.
- An instance change where `kkd` itself started the new server, for example after a server crash, needs only `restart-terminal`.

### Supported Herdr versions

Kiki pins a supported Herdr version range. When `kkd` starts or connects to the dedicated server, it checks three things against that range:

- the version;
- the protocol number;
- the object of named capability flags returned by the ping reply.

An unsupported or missing Herdr fails terminal lifecycle commands with an error that names the found and required versions. It does not corrupt recorded thread state.

[`client_targeted_focus`](appendix-a-glossary.md#client-targeted-focus) is the one required Herdr extension, and it must arrive as a new flag in that object. It lets kiki move one viewer's screen without moving anyone else's (see [caller-local focus](appendix-a-glossary.md#caller-local-focus)). Until the server advertises it, caller-local `kk switch` fails by naming the capability. It does not degrade to a focus change that moves every client.

`kkd` never stops a running dedicated server on its own to apply a changed key: stopping it ends every thread's processes. Only the approved `replace-terminal-server` plan stops it (see [Changing a terminal key while a server is running](#changing-a-terminal-key-while-a-server-is-running)).

### The generated Herdr configuration file

Kiki generates the dedicated server's Herdr configuration file and owns it. These Herdr settings are fixed by kiki and are not exposed as kiki keys:

- automatic agent resume on restore is off (`[session] resume_agents_on_restore = false`);
- onboarding is off;
- Herdr's update, version, and manifest checks are off;
- toast delivery is set to Herdr's own [toasts](appendix-a-glossary.md#toast) (`[ui.toast] delivery = "herdr"`), which Herdr leaves off by default;
- sidebar rows and width are sized for kiki's label;
- the sidebar row layout that displays the tokens kiki publishes. This is a v1.x surface; the generated file declares no [sidebar tokens](appendix-a-glossary.md#sidebar-token) until it ships;
- the keybinding that opens the overlay and the plugin or command entries it invokes (v1.x);
- Herdr's agent-integration installer is never invoked against a managed harness's settings.

A toast is a small message that pops up briefly and then goes away.

`kkd` regenerates the file and validates it with its own parser immediately before every server start. It refuses to start the server on any diagnostic. This is not optional tidiness:

- Herdr's client can rewrite the file from its settings screen.
- When Herdr cannot parse the file, it silently loads its defaults, which turn agent resume on.

Edits to the generated file are therefore overwritten at the next start.

Some Herdr preferences are ones kiki does not need to control: theme, Herdr's own keybindings, mouse and scrollback behavior. They are not kiki configuration keys in v1, and kiki's generated file leaves them at Herdr's defaults.

The user's default Herdr server and its configuration file are never read or changed.

## UI keys

This entire section is deferred until the v1.x UI surfaces ship.

"Next terminal-group provisioning" below means the next `kk new`, `kk reopen`, or terminal-restart repair. `mouse_enabled` and `theme` apply to kiki's own surfaces, the [overlay](appendix-a-glossary.md#overlay-tui) and the [`ui` pane](appendix-a-glossary.md#ui-role-pane), not to Herdr.

All `[ui]` keys are personal preference. They are valid in user and per-thread config, but invalid in repo-shared config. If set in repo-shared config, kiki warns and ignores them.

| key                   | type   | default       | hot-reload                           |
| --------------------- | ------ | ------------- | ------------------------------------ |
| `ui_pane`             | bool   | `false`       | no: next terminal-group provisioning |
| `ui_pane_width`       | int    | `32`          | no: next terminal-group provisioning |
| `shell_pane`          | bool   | `true`        | no: next terminal-group provisioning |
| `shell_pane_position` | string | `"below"`     | no: next terminal-group provisioning |
| `shell_pane_size_pct` | int    | `25`          | no: next terminal-group provisioning |
| `mouse_enabled`       | bool   | `true`        | yes                                  |
| `overlay_min_cols`    | int    | `80`          | no: next overlay open                |
| `toast_ttl_ms`        | int    | `4000`        | yes                                  |
| `theme`               | string | `"soft-dark"` | yes                                  |

### `theme`

`theme` selects the palette (the set of colors). The canonical alternates are `soft-dark` (default), `soft-light`, and `high-contrast`. Unknown theme values warn and fall back to `soft-dark`.

### `shell_pane_position`

`shell_pane_position` accepts one of two values:

- `below` (horizontal split below the agent pane, default); or
- `right` (vertical split to the right of the agent pane).

Unknown values warn and fall back to `below`. The `shell` role pane (see [shell pane](appendix-a-glossary.md#shell-pane)) always lives in the same tab as the `agent` pane; routing it to a separate tab is intentionally omitted.

### The `ui_pane*` keys

The `ui_pane*` keys replace the former persistent-sidebar keys. Herdr's native sidebar now carries the cross-thread list and attention state. So the `ui` role pane exists only for users who want a permanently visible Stack ([follows](appendix-a-glossary.md#follows)) tree.

Kiki's generated Herdr configuration sizes Herdr's sidebar for kiki's label. That width is not a kiki key, and the user can still hide or collapse the sidebar in Herdr.

### When role-pane keys apply

Role-pane keys are `lifecycle` keys. They apply when kiki provisions a [terminal group](appendix-a-glossary.md#terminal-group):

- at `kk new`;
- at `kk reopen`;
- when a `kk repair` plan restarts a thread's terminal after a terminal-runtime restart.

`kk switch` performs no terminal mutation. So it never applies these keys and never re-creates a pane the user closed. A user who wants another shell splits natively in Herdr.

The full lifecycle, degradation, and authority semantics for the shell pane live in [Interface · Shell pane](10-interface/spec.md#shell-pane).

The semantics, wireframes, and degradation rules for these keys live in [Interface](10-interface/spec.md).
