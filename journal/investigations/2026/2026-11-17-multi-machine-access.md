# How can I pick up my threads from another machine and keep accounts separate?

2026-11-17 · Architecture investigation · Proposed design

## The experience

Suppose you leave a work agent running on an office Mac. At home you open
kiki, select Work, and see the thread, its host, and the account running it.
Attaching opens a new view of the existing terminal. Your home machine can
be signed into a different harness account. Closing the laptop ends your
view. The office Mac keeps doing the work.

You create and name your own **kiki profiles**. Each profile can span any
machines you choose, and a machine can serve several profiles. Work is
one user's example. You choose which repos and harness accounts to use
on each host. Each terminal or window selects its own profile.

I propose giving each profile a stable ID. An enrolled device could pass a
new device the profile ID, name, and host directory during setup. The new
device then obtains its own grants from the hosts it needs. Renaming a
profile preserves its ID. Creating an independent profile with the same
name gives it a different ID. Harness credentials and session history
stay on the execution host.

For example, create a profile called Atlas on a laptop and add a desktop
and a build machine. Atlas can use one Codex account on the desktop and
a different one on the build machine. From a third device you can select
Atlas and attach to either host's threads. To run a new thread on that
third device as well, add it as a host and choose its local harness account.

For example, a future CLI might offer `kk --profile work ls` and
`kk --profile work attach billing`. Both should work outside a checkout.
After selecting Work in that terminal, short commands should suffice.
If two hosts have a thread called billing, show both with their host and repo
and ask the user to pick. Remember the stable target for reconnect.
An unreachable target stays selected until the user chooses another one.

## What the book establishes

This is a reading of the reference at revision `b0e67c5f`. The book places
one daemon and one dedicated Herdr server under each OS user. A registration
identifies a local repo. The daemon holds the jj lock, records lifecycle
steps in SQLite, verifies local process identities, and supervises hooks.
A follows link depends on observing the parent's and child's history in the
repo. A second checkout of the same Git URL has its own registration and
working copies. A common origin cannot tell kiki that two live threads are
the same. See the [invariants](../../../docs/reference/book/02-invariants.md),
[daemon](../../../docs/reference/book/13-architecture/daemon.md), and
[schema](../../../docs/reference/book/13-architecture/schema.md).

The [service contract](../../../docs/reference/book/13-architecture/grpc.md)
leaves four remote questions open. They cover transport, peer identity, who
can present approvals, and how access ends. The [roadmap](../../../docs/reference/book/16-roadmap.md)
also distinguishes a remote viewer from running terminals on a different
host than their daemon. These proposals address the viewer case. No remote
protocol or harness-account behavior was tested for this investigation.

## Where state lives

| Fact                                 | Who owns it in the proposed design                                                                                                                                                                                   |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Which profile this window is showing | The client. Search, recent threads, event streams, and notifications use that selection. Background notifications from another profile require an explicit opt-in.                                                   |
| Which targets this device can reach  | Each hosting daemon grants access to its own targets for an enrolled device in a specific profile. The client keeps an address book of those grants. Renaming a profile or copying an address book grants no access. |
| Which daemon runs the thread         | One host owns the repo registration and all its threads. Route using a pinned daemon identity, repo ID, and existing thread ID. Display names and network addresses may change.                                      |
| Which account runs the agent         | A host-local harness configuration names a credential source and expected account. The host binds that configuration to the thread at creation and records its identity on each launch.                              |
| What actually happened               | The owning daemon's operation journal, audit log, workspace, and process observations. A client may cache permitted summaries with their source and last-seen time.                                                  |

Give each registration one profile in the first release. Work and Personal
can each register their own clone of a project. Two profiles claiming the
same underlying jj store would also share writes and history. Detect this at
registration and direct the user to use a separate clone. Keep follows links
inside one registration. This preserves the existing lock order and gives
each live workspace one place that can advance it.

## Account choice at launch

The host owner sets up harness configurations such as “company Codex” or “personal Claude”
and authorizes them for a profile. New-thread creation shows the resolved
profile, host, harness, and account label before launch. The same binding
applies on restart and reopen. Switching viewers changes none of those facts.

Each harness configuration covers everything the adapter can use to recover an
identity or a conversation, including its credential store, environment,
configuration, and session history. The current Codex design already requires
credentials in the launch-scoped home. Claude Code needs its own verified
path. Test each supported adapter with two accounts signed in on the same
host. If the adapter cannot verify an account, distinguish a user-assigned
account label from a verified account. For a profile requiring a verified
work account, block launch when the binding cannot be proven. Expired
credentials should lead to signing back into that account. Never silently
try the host default. See the [harness adapter](../../../docs/reference/book/13-architecture/harness-adapter.md).

Changing to another account deserves an explicit new session. Keep old
conversation history with its original profile. Copying any material to
the new account needs a separate disclosure and the applicable consent.
Existing transcript consent and publish credentials have their own scopes.
A harness login supplies neither. For a strong separation requirement,
give Work its own OS user or virtual machine, including its own repo store,
daemon, Herdr server, and credential stores. Processes under one user can
read sibling workspaces. Named profiles under that user provide an
organizational safeguard.

## Connecting and exercising authority

Start with a direct client connection. One address-book entry can point to a
local daemon and another to the office host. The client asks each permitted
host for its own summaries and combines the results within the selected
profile. No central account or always-online coordination service is needed
for this first slice. It assumes the client can reach the host, for example
over a work network or VPN. A later relay could solve reachability while the
host continues to authenticate callers and decide each request.

Prototype SSH with a dedicated device key restricted to a fixed kiki command
and forwarding disabled. Pin the host during pairing. The host owner approves
the device, profile, targets, and permitted actions through a trusted local
flow. Bind the host-side session to that enrolled key and daemon identity.
Negotiate protocol version and capabilities before exposing any commands.
OpenSSH supports forced commands and per-key restrictions.
[OpenSSH server manual](https://man.openbsd.org/sshd.8#AUTHORIZED_KEYS_FILE_FORMAT)

Put remote access checks in front of the existing daemon operations. A
restricted bridge must convey the authenticated device to the daemon through
a trusted channel. The daemon checks the intersection of the device grant,
target scope, and method's existing requirements. Forwarding the raw Unix
socket would lose the distinction between a remote caller and a local peer.
Keep hook, launcher, process-proof, and bootstrap methods local. Include
device and profile in the owning daemon's existing audit record.

Start with repo-summary access. Listing a thread need not reveal its prompt,
transcript, terminal output, or even the names of other registrations.
Interactive attach deserves a separate grant. A full Herdr client can reach
other panes, and a shell can read files available to its OS user. Initially
offer full attach only to the trusted owner of that whole execution
environment. For a friend's project, the owner can use a separate OS user
and dedicated runtime. Sharing with the friend would require their own
enrollment and grants. Offer narrow summary sharing first. A thread-only
terminal grant needs evidence that the viewer, input, and accessible
processes really are confined to that scope.

Consequential actions still need the host's exact plan and a one-use
approval. Start with confirmation by an enrolled presenter on the host. To
approve from the couch, separately enroll a presenter on the viewing device.
It must display the host-issued plan with the profile, host, and account,
prove a fresh human confirmation outside agent control, and bind it to the
requesting identity, target, plan digest, and expiry. A remote terminal by
itself cannot supply the local foreground and process ancestry checks. Gate
remote confirmation on a reviewed proof for the supported client platform.
[Authority](../../../docs/reference/book/04-authority.md)

On revocation the owning daemon rejects new calls, closes existing viewer
and event streams, and invalidates outstanding grants and unused challenges
for that device. An operation that already claimed its approval stays under
its host journal. Removing a device that has grants on three hosts must show
which hosts have acknowledged revocation. An unreachable host remains
pending. Expiring grants bound that window. Copies of data already delivered
cannot be recalled.

## Build order and proof gates

1. **Find work from a second machine.** Pair two devices, list approved
   summaries from two hosts in one profile, and open Personal beside Work.
   Enroll a fresh device into an existing profile and check that it can reach
   both hosts with its own grants. Create a second profile of the same name
   and verify that its listings stay separate. Exercise a changed host key, an unsupported version, an
   offline host, and a revoked device. Switching profiles must discard late
   responses from the previous view. A stale summary shows when it was read.
2. **Return to the same terminal.** Attach two owner devices, switch threads
   on one, disconnect it, and reconnect. Verify the other viewer keeps its
   focus and the host still has the same agent incarnation. If the host
   rebooted, show its actual repair state. Check revocation during attach.
3. **Drive work remotely.** Launch under two profiles, expire one harness login, then try
   restart and reopen. Check the selected account, history, and hook setup.
   Drop the connection after the host accepts a create or close. Give each
   mutation a client-generated request ID. The host durably binds it to
   caller, profile, target, method, and arguments before side effects. A
   retry returns the existing operation, and changed arguments are rejected.
   Refresh from host state after an event gap. Disable offline mutations.
4. **Broaden access after the proofs pass.** Verify remote confirmation,
   revocation, and profile isolation before allowing sensitive actions from
   another device. Test with a friend's read grant on a host also serving
   Work. Attempts to enumerate Work, attach, confirm, or read transcripts
   must fail at the host, including direct protocol calls.

A sleeping office Mac is the main product trade-off. Other devices can show
its last known state and reconnect when it wakes. For work that must run
overnight, choose an always-on host when creating the thread. Moving an
already running thread is a separate design problem. It would need a way
to prove the old host has surrendered ownership, preserve unpublished work
and pending operations, and establish a fresh account-bound incarnation at
the destination. Losing contact with the old host proves none of that.

The [Rex and T3 Code comparison](2026-11-17-rex-t3-remote-access.md)
refines this proposal with evidence about route changes, account-specific
conversation history, and what happens when a client loses access.
