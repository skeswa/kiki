# Remote access through profiles

This chapter defines the planned multi-machine design after v1. Imagine you
create a profile called Atlas, add your laptop and a build machine, and run
a thread on the build machine. From a third device you can select Atlas and
return to that thread. The build machine keeps its workspace, terminal, and
signed-in agent. The third device needs permission to view the work. It can
be a viewer even if it has no harness installed.

## What belongs to whom

| Owner          | State it keeps                                                                                                                                                                                                                      |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User           | A profile with a stable ID, a name the user can change, and a directory of participating hosts. Users can create their own profiles. Each profile can span machines, and each machine can serve several profiles.                   |
| Viewing device | Its own enrollment, the hosts it knows for each profile, and any permitted cached summaries. Each window chooses its own profile.                                                                                                   |
| Execution host | One user's daemon on a machine. It owns the grants for its registrations, the available harness accounts, and all the files, processes, and durable records for threads it runs. Two OS users on one machine have separate daemons. |
| Thread         | Its existing stable thread ID. The host records its repo registration, profile ID, and the local harness configuration and session history it may use.                                                                              |

A profile keeps its ID when renamed or added to another device. Independently
created profiles with the same name have different IDs. During setup a user
can transfer a profile's ID, name, and host directory to a new device.
The device pairs with each host it wants to reach. Profile transfer excludes
device keys, grants, harness credentials, and session history. Adding a
viewer as an execution host is a separate choice.

For the first remote release, assign each participating repo registration to
one profile. Use separate clones when two profiles need the same project.
Reject a second profile's registration of the same underlying jj store on
that host. An existing local registration stays local until its owner assigns
it. Before remotely launching or resuming an older thread, the owner must
select its harness binding and the host must verify the permitted history. A follows link stays inside its registration, where one daemon can
observe both workspaces and enforce the [lock order](../02-invariants.md#locks-and-their-order).

## Finding and resuming work

From outside a checkout, a human can select a profile, list authorized
threads across its hosts, and attach to one. For example, the intended flow
can be written as `kk --profile atlas ls` followed by
`kk --profile atlas attach billing`. Command spelling is illustrative.
Show the host and repo beside each match. If a name is ambiguous, require a
choice before acting. Bind the choice to the authenticated daemon, repo ID,
and thread ID. A Git URL, display name, network address, or restored pane
cannot establish any of those identities.

Scope search, recent threads, cached results, and subscriptions to the
selected profile. When a window switches profiles, discard late results from
the old view. Background notifications from another profile require opt-in.
A managed agent keeps the scope of its thread. Adding a host to a person's
profile gives their agents no right to delegate work there.

If a host sleeps, show the last permitted summary with its observation time.
Wait for that host before performing a mutation. On reconnect, recheck
access and refresh host state after any gap in the event stream. Attach
opens a view of the current binding and moves only the invoking viewer.
If the host rebooted, show its actual repair state. A lost connection gives
no other machine ownership of a running thread. Herdr, the hooks, the jj
workspace, and OS process checks all stay with the owning daemon.

## Harness accounts and conversation history

At creation, resolve the profile, execution host, and harness configuration.
Show the selected account and distinguish a user-supplied label from an
account the provider verified. The same profile may use different accounts
on different hosts. The viewing device's login has no role in this choice.

Persist the host-local configuration ID, expected account when verifiable,
and permitted session store before the agent receives its first prompt.
On restart or reopen, check them again before releasing the launch gate
or disclosing history. If the login expired or identifies another account,
stop and name the binding that needs attention. If the profile requires
account verification and the harness cannot supply it, block launch.
A profile that permits an unverified login may start a fresh session. To
resume or replay earlier history, the host must prove continuity with the
account that received it. The same directory, label, or configuration ID
cannot prove that. If proof is missing, offer a fresh session with an empty
history and no automatic catch-up.
Apply the [harness adapter's exclusive hook settings](harness-adapter.md)
to every launch, including a resume.

Keep conversation histories separate across profiles by default. Changing
accounts requires an explicit new session. Sending prior conversation
material to the new account requires separate disclosure and the applicable
[transcript consent](../11-configuration.md#consent-is-not-configuration).
A portable profile alone grants no permission to disclose a transcript.

## Connecting and granting access

Start with a restricted Secure Shell (SSH) connection to a host-side kiki
command. Verify the host when pairing and bind the device's own key to the
intended daemon. The host owner grants that device specific actions on
specific targets in a profile. Negotiate supported protocol versions and
actions before use. Each route to that daemon must verify the peer before
sending private data and enforce the same limits on the grant. A changed
identity requires explicit pairing. The exact wire protocol and enrollment
exchange require testing before release.

The host checks the device, profile, target, method, and existing approval
requirements on every request. At enrollment or grant issuance, the host
records the caller scope it is delegating. A grant to act as a specific
thread carries that thread's scope, including its cross-thread approval
rules. Outside a thread, a viewer starts with registration scope for each
granted repo. That permits its summaries and beginning an approval.
Choosing a target thread never changes the caller scope. Apply the host's
existing approval flow when a request needs wider authority. Record the device and profile on the
existing audit row. A host-side bridge must preserve the caller's identity.
Keep bootstrap, hooks, launcher reports, and OS process proofs on the host.
Neither forwarding the local daemon socket nor passing a reusable local
credential to the viewer satisfies this contract.

Use the [existing repo summary fields](../appendix-a-glossary.md#repo-summary-read-scope)
for summary reads. Grant terminal access separately. A summary reader may
see only the permitted repo summaries. Full terminal access can expose every
pane on the dedicated Herdr server and files readable by its OS user. Limit
the initial attach feature to viewers trusted with that execution environment.
Use separate OS users or virtual machines when profiles require protection
from each other's processes. A profile name supplies organizational separation
within a shared OS account.

For a consequential action, the host prepares the exact plan and identifies
the profile, host, and affected account where applicable. Use the host's
enrolled foreground presenter and the existing [one-use approval](../04-authority.md#two-phase-foreground-approval).
A future presenter on a viewing device requires separate enrollment and
proof of fresh human confirmation outside the agent's control. Keep remote
confirmation disabled until that platform can supply the proof.

A client gives each mutation a request ID. Within the caller and profile,
the host binds the ID to the method, target, arguments, and operation journal
before side effects. An exact retry after a lost reply returns the existing
operation to a still-authorized caller. Conflicting reuse fails. Concurrent
retries must produce one operation. Where approval is required, claim it in
the same transaction that creates the journal.

When a grant expires or is revoked, the host closes streams and terminal
attachments using that grant, rejects its use on every route, and invalidates
its unused challenges and approvals. A separate valid grant on the same
device can still be used. Removing the device's enrollment ends all grants
under it and prevents the old enrollment from pairing again. Already claimed
operations recover from their host journals. Other authorized viewers and
the agent can keep working.

For a profile spanning hosts, report removal per host. Show unreachable
hosts as pending. Grants expire at a finite time that the host enforces on
open connections as well as new requests. Independent SSH shell access
remains under the host owner's control.

## Checks before release

| Capability             | What a two-host test must show                                                                                                                                                                                                                                                                                                                  |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Profile discovery      | Import a user-named profile on a third device. It lists only its own grants. Rename it, create another profile with the same name, and put identically named threads on two hosts. Each command still reaches its chosen target.                                                                                                                |
| Reconnect and attach   | Disconnect one of two viewers during a live session. The agent keeps the same incarnation and the other viewer keeps focus. Reconnect after an event gap, after a reboot, and with a changed host identity. Each case must show its actual state.                                                                                               |
| Launch and resume      | Exercise Claude Code and Codex with two accounts and distinct histories. Check create, restart, and reopen. Expire a login and then replace it with the wrong account. Repeat with an unverified replacement login in the same history directory. Verify the old history is never replayed.                                                     |
| Requests and approvals | Drop a reply after an approved mutation starts. Retry concurrently, then retry with a changed target. Observe one journal and one effect. From registration scope, select a thread and confirm that targeting it confers no same-thread authority. Reject confirmation without presenter proof.                                                 |
| Sharing and revocation | Give a second device summary access to one repo. Direct requests for another profile, a transcript, or a terminal must fail. Revoke only attach while connected. Summary access must survive. Let a live grant expire without reconnecting. Remove the device and try every saved route, including after an offline host processes the removal. |

Start with summary reads. Before each capability ships, test unauthorized
requests, expiry on open connections, and revocation for that capability.
Attach also requires caller-local focus and uninterrupted host execution.
Remote mutations require account and history checks where applicable,
retry safety, and the required approval proof. Live thread
migration, agent delegation across hosts, and running Herdr apart from its
daemon have separate proof requirements. See the [roadmap](../16-roadmap.md).
