# D-0009: Operate fully headless, with a configurable automation policy

- Recorded: 2026-11-17
- Decided by: project owner, 2026-11-17, for the two requirements ("kiki should be able to fully operate headlessly", in both senses, and "automation rules should be fully configurable"); agent, 2026-11-17, for the design that meets them. The owner has not yet ratified the individual design choices.
- Topic: Headless operation and unattended approval
- Supersedes: the "No unattended approval" rule in [Authority](../../docs/reference/book/04-authority.md) and every "unavailable non-interactively" line in [Commands](../../docs/reference/book/09-commands.md)
- Superseded by: [D-0015](0015-create-only-bookmarks-and-preserve-revisions.md) for the revision-abandonment operation and its risk label.

## Decision

"Headless" means two things here, and kiki must support both.

1. **No UI.** Nothing in kiki needs an attached terminal client, the overlay,
   a popup, the UI pane, or a desktop session. The `kk` command line and the
   daemon's service are the whole surface. Every screen is a view of state
   that a command can also print as JSON.
2. **No human.** A script, a CI job, or another agent can run every command
   with nobody at a keyboard.

Before this decision, most lifecycle commands needed a person to confirm at
a foreground terminal, and kiki ruled out any unattended approval. The
owner's choice reverses that. The agent's design keeps as much of the old
safety as it can:

- **An automation policy stands in for the human's confirmation.** The
  policy is a list of rules in the user's config file. Each rule names who
  is calling, which repos, which operations, and which risks it accepts.
  Every part can be a wildcard, so the rules are fully configurable.
- **A policy does nothing until it is activated.** Activation needs a person
  at a terminal or the Admin bootstrap credential. Editing the file changes
  nothing. So an agent cannot grant itself authority by writing config.
- **A policy replaces the confirmation and nothing else.** The plan is still
  computed, fingerprinted, bound to one caller, used once, and journaled.
  Freezes, holder scans, and the final proof still run. A policy can never
  make a plan run that a safety proof refuses.
- **Risky choices are named.** A plan that kills processes, loses work,
  abandons revisions, or moves a bookmark backward carries a risk label for
  each. A rule matches only when it accepts every label on the plan.
- **No rule, no change.** With an empty policy, kiki behaves as it did
  before: a human confirms, and a caller with no terminal is refused.
- **Automation has its own credential.** A named automation credential is
  kept outside every workspace and is never given to an agent. Agents get
  unattended authority only when a rule names thread callers.
- **A machine with no human can be set up.** `kk daemon install` runs
  without questions, and Admin can activate the policy and create the first
  automation credential.
- **Scripts can see what happens.** Commands print JSON on request, exit
  with stable codes, and never prompt without a terminal. `kk events` and
  `kk wait` follow thread state. A notification can run a program.

A plain `--yes` flag, approval through an environment variable, and reusable
approval tokens stay rejected.

## Why

The owner called headless operation crucial. Orchestration by scripts and by
other agents is a main use of a tool that coordinates many agent threads,
and such callers have no keyboard.

The old rule existed for one reason: an agent should not be able to approve
its own destructive actions by accident. Activation, the separate automation
credential, and risk labels keep that protection for anyone who wants it,
while a user who wants everything unattended can write one wildcard rule.

## Alternatives and consequences

- **A `--yes` flag.** Simplest. Any process running as the user, including an
  agent, could then approve anything. Rejected again.
- **A fixed list of operations that always need a human.** The owner asked
  for fully configurable rules, so no operation is fixed. Provider consent
  is the one place a wildcard does not reach: a rule must name the purpose
  and the provider.
- **Rules that take effect when the file is saved.** An agent editing the
  file would grant itself authority. Activation prevents that.

Consequences and limits:

- Like presenter enrollment, activation is a guard against accidents. It is
  not a defense against a hostile program running as the same user.
- A wildcard policy hands every approval to every local caller. The book
  says so plainly.
- Two platform modes are unproven and are gates: the daemon on a host with
  no service manager, and macOS reached over SSH with no desktop login.
- kiki still never answers a harness's own permission prompt. On a headless
  host the operator sets the harness's permissions.
- Open question for the owner: there is no `kk` command to send a later
  prompt to a running agent. The first prompt comes from `kk new -m`. A
  headless caller that wants to send more must use Herdr's own tools today.
  - Resolved on 2026-11-18 in [D-0012](0012-submit-follow-up-prompts-as-user-turns.md).
- The rule keys, risk-label names, exit codes, and command names are the
  agent's choices and can change before implementation.

## Links

- Contract: [Authority](../../docs/reference/book/04-authority.md#automation-policy), [Commands](../../docs/reference/book/09-commands.md#kk-automation), [Configuration](../../docs/reference/book/11-configuration.md#automation-keys)
- Related: [D-0006](0006-close-repair-and-proof-gaps.md), [D-0008](0008-keep-execution-and-remote-grants-on-the-host.md)
