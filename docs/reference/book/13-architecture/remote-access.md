# Remote access through profiles

In kiki's design for remote access after v1, you can leave a thread running
on a build machine and open its terminal from your laptop. The build machine
keeps the files and runs the agent. Your laptop needs permission to connect.
It can open the terminal even if you have never installed the agent's
harness, such as Claude Code or Codex, on the laptop.

## What belongs to whom

You choose a name for each profile and the machines where you want to use
it. For example, a profile you call Atlas could include a desktop and a
build machine. The desktop could also belong to another profile. Each
window remembers which profile you selected there.

| Owner          | What it keeps                                                                                                                                                                                                                                                    |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User           | Each profile's name, permanent ID, and list of hosts.                                                                                                                                                                                                            |
| Viewing device | Its own record of pairing with each host, the hosts it knows in each profile, and the summaries it has permission to save.                                                                                                                                       |
| Execution host | The kiki daemon (background program) for one operating system (OS) user on one machine. It manages access to its repos and harness accounts. It keeps the files, processes, and records for its threads. Two OS users on the same machine have separate daemons. |
| Thread         | Its permanent thread ID. The host also records the thread's repo registration and profile ID, which harness settings to use, and which history the harness may open.                                                                                             |

When you set up another device, you can bring the profile ID, name, and host
list with you. The ID stays the same if you rename the profile. If someone
creates a second profile called Atlas, it gets its own ID. Each new device
must pair with the hosts it wants to reach. Copying a profile leaves behind
device keys, access grants, harness credentials, and session history. You
can add the new device as a host if you also want to run threads there.

In the first remote release, each participating repo registration belongs to
one profile. If two profiles need the same project on one host, use separate
clones. The host must reject a second profile that tries to register the same
jj store. A local repo stays local until its owner assigns it to a profile.
To launch or resume an older thread remotely, the owner must first choose
its harness settings. The host must check which history those settings allow.

Keep both ends of a follows link in the same registration. That way one
daemon can watch both workspaces and take their [locks in order](../02-invariants.md#locks-and-their-order).

## Finding and resuming work

You can list and attach to threads from outside a checkout. For example,
`kk --profile atlas ls` would list the threads you can see in Atlas, and
`kk --profile atlas attach billing` would open the billing thread. These
commands illustrate the planned interface. If two threads match, show the
host and repo for each and ask which one to open. Remember the verified
daemon, repo ID, and thread ID for that choice. A Git URL, display name,
network address, or restored pane cannot identify the thread.

A window shows search results, recent threads, saved summaries, and live
updates for its selected profile. If a reply from Atlas arrives after you
switch profiles, discard it. Notifications from another profile require
your opt-in. An agent keeps its thread's permissions when you switch views.
Adding a host to your profile gives the agent no right to send work there.

If the build machine sleeps, show the last summary you had permission to
see and the time the host reported it. Changes must wait until the host is
reachable. When you reconnect, the host checks access again. If the viewer
missed events, it reads the current state from the host. Attaching opens
the terminal currently bound to the thread and moves only your view. If the
host rebooted, show whether the thread needs repair. Losing a connection
never transfers ownership. The host's daemon still checks OS processes and
keeps Herdr, the hooks, and the jj workspace on that machine.

## Harness accounts and conversation history

When you create a thread, kiki shows the profile, execution host, harness
settings, and selected account. You may have called an account “company.”
Show whether the provider has verified who is signed in. One profile can
use different accounts on different hosts. Signing in on the viewing device
has no effect on the choice.

Before the agent gets its first prompt, the host records the ID of its
local harness settings, the expected account when it can verify one, and
where the harness may read session history. Check all three again on
restart or reopen, before opening the [launch gate](../appendix-a-glossary.md#launch-gate)
or sharing any history. If the login has expired or the provider reports a
different account, stop and tell the user which login needs attention.
Apply the [exclusive hook settings](harness-adapter.md) on every launch,
including when an agent resumes.

Some profiles require a verified account. If the harness cannot verify the
login, block launch for those profiles. When a profile allows an unverified
login, the user may start a fresh session. To resume a conversation or
replay its history, the host must verify that the same account that received
the history is still signed in. A familiar directory, account label, or
settings ID cannot prove that. If the host cannot verify the earlier account, offer an empty session
only when the profile allows the current login. Turn off automatic catch-up
for that session.

By default, each profile keeps its conversation history separate. To change
accounts, the user must explicitly start a new session. Before sending any
of the old conversation to the new account, explain what will be sent and
obtain the required [transcript consent](../11-configuration.md#consent-is-not-configuration).
Copying a profile to another device grants no such consent.

## Connecting and granting access

The first connection to test uses Secure Shell (SSH), restricted to a kiki
command on the host. During pairing, the device verifies the host and links
its own key to that host's daemon. The host owner chooses which actions the
device may take and which targets it may use in the profile. These permissions
make up a grant. Before use, the device and host agree on a protocol version
and supported actions. Every route must verify the other end before sending
private data and enforce the same grant. If the host's identity changes,
pair again. Test the message format and pairing procedure before release.

### How the host checks a request

For every request, the host checks who is calling, the selected profile,
the action, its target, and any approval the action requires. When it enrolls
a device or issues a grant, it records who the device may act as. A device
allowed to act as a particular thread has that thread's limits, including
the approval rules for acting on another thread.

Outside a thread, the viewer starts with repo registration scope for each
repo in its grant. This lets it read the permitted summaries and request
approval. Selecting the billing thread tells the host which thread you want
to reach. To act as billing, the device still needs a grant for that thread.
Use the existing approval process for requests that need wider authority.

Include the device and profile in the existing audit record for the request.
Any program passing the request to the daemon must preserve the caller's
identity. Keep initial daemon setup, hooks, launcher reports, and OS process
checks on the host. Forwarding the daemon's local socket would bypass those
identity checks. Giving the viewer a reusable local credential would do
the same.

### Summary reads and terminal access

A grant to read summaries covers only the allowed repos and the
[existing summary fields](../appendix-a-glossary.md#repo-summary-read-scope).
Opening a terminal needs a separate grant. Someone with full terminal access
may reach every pane on the dedicated Herdr server and every file its OS
user can read. In the first release, grant attach access only to people you
trust with that whole environment. Profiles organize work under one OS
account. Use separate OS users or virtual machines if processes in one
profile must be kept out of another's files.

### Approvals and retries

For an action that needs human approval, the host prepares the exact plan.
It names the profile, host, and any affected account. The host's enrolled
presenter shows the plan to the person at the keyboard and asks for
[one-use approval](../04-authority.md#two-phase-foreground-approval). To
confirm from a viewing device in a future release, its presenter must enroll
separately. Remote confirmation stays disabled until that platform can prove
a person confirmed this request outside the agent's control.

Suppose you ask kiki to create a thread and the connection drops before you
get a reply. The client retries with the same request ID. For each request
that changes state, the host records the ID for that caller and profile.
Before making any change, it binds the ID to the action, target, arguments,
and operation journal (the saved record of the job). If the action needs
approval, the host claims that approval in the same database transaction
that creates the journal.

If you still have access, an exact retry returns the original operation.
The host must carry out the operation only once, even if two retries
arrive together. In this example, you get one thread. The host
rejects reuse of that ID with different arguments, a different action, or
a different target.

### When access ends

Say a laptop has two grants, one to read summaries and one to attach. If
the owner revokes its attach grant, the host closes all streams and terminal
views using that grant. It rejects the grant on every route and cancels all pending requests for approval and unused approvals tied to it. The laptop can still use its
summary grant. Expiration has the same effect as revocation, even on an
open connection.

Removing a device's enrollment ends every grant under that enrollment.
The host must refuse any attempt to pair again using the old enrollment. If an operation already claimed
approval, the host uses its journal to recover the operation. The agent
and other authorized viewers can keep working.

Show the result of removing a device on each host. If one host is offline,
show its removal as pending. Every grant has an expiry time, which the host
enforces on open connections and new requests alike. The host owner manages
any separate SSH shell access.

## Checks before release

Start with summary reads. Before shipping each kind of access, test a
request without permission, revoke a grant in use, and let a grant expire
with its connection open.

| Feature                | What to test with two hosts                                                                                                                                                                                                                                                                                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Profile selection      | Import a user-named profile on a third device. Check that it lists only threads its grants allow. Rename the profile, create another with the same name, and give two threads on different hosts the same name. Each command must reach the target the user chose.                                                                                                      |
| Reconnect and attach   | Disconnect one of two viewers. The same agent process must keep running and the other viewer must keep focus. After missed events, check that the viewer reads fresh state. After a reboot, check the repair state. After a host identity change, require pairing.                                                                                                      |
| Launch and resume      | Test create, restart, and reopen with two accounts and separate histories in both Claude Code and Codex. Expire a login, then replace it with the wrong account. Try an unverified replacement login in the same history directory. Check that the replacement never receives the old history.                                                                          |
| Requests and approvals | Drop the reply after an approved change starts. Retry twice at the same time, then change the target and try again. Check for one journal and one effect. Select a thread using repo registration scope. Verify that this gives no permission to act as that thread. Reject confirmation without proof from the enrolled presenter.                                     |
| Sharing and removal    | Give a device summary access to one repo. Try direct requests for another profile, a transcript, and a terminal. All must fail. Grant attach access, connect, and revoke only that grant. Summary reads must still work. Let a live grant expire without reconnecting. Remove the device and try every saved route. Repeat after an offline host processes the removal. |

Moving a running thread to another machine, letting an agent delegate work
to another host, and running Herdr apart from its daemon each need their
own tests before they can ship. See the [roadmap](../16-roadmap.md).
