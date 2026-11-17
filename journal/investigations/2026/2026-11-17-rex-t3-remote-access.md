# What can kiki learn from Rex and T3 Code about remote work?

2026-11-17 · Comparative investigation

Both systems let another device reach work that belongs to a host. Rex
documents what happens when several people reach the same Unix account.
T3 Code documents what happens when several AI provider accounts can open
the same conversation. Kiki needs to make both choices visible. The
[earlier proposal](2026-11-17-multi-machine-access.md) gives each thread
one execution host. The findings below refine how to identify that host,
resume a conversation, and revoke access.

## Superlogical's Rex

A Rex server keeps sessions alive between viewers. The CLI can save an SSH
host under a name such as `build`. Inside a managed terminal, commands already
know their server, session, and block. A person can target a different server
explicitly. When a session name matches twice, Rex lists the matches and
stops. Rex recommends SSH for personal remote access. Its beta relies on the
connection method to identify the caller. Its Linux guide also calls out a
practical limit on persistence. Logging out can end a personal server's
sessions unless the user's service is allowed to linger.
[Rex CLI](https://www.superlogical.com/rex/docs/automate/cli) ·
[Remote access](https://www.superlogical.com/rex/docs/linux/remote-access)

Rex offers three server modes on Linux and FreeBSD. A personal server
runs as its owner. A shared server runs programs as one account, and every
member can type into every session. A login server checks which OS accounts
the caller may use, then connects them to that account's server. A default
can save a selection step, but the access check still runs. Reloading the
login policy closes connections that lost access and leaves the underlying
sessions running. This is a model for removing a viewer while their former
teammate's build keeps running.
[Server modes](https://www.superlogical.com/rex/docs/linux/server-modes) ·
[Shared server](https://www.superlogical.com/rex/docs/linux/shared-server) ·
[Login server](https://www.superlogical.com/rex/docs/linux/login-server)

An OS account and a harness login answer different questions. Rex's agent
setup respects `CLAUDE_CONFIG_DIR` and `CODEX_HOME` when finding settings.
That establishes where Rex installs its integration. The guide gives no
proof of which provider account will pay for a particular resumed turn.
[Rex agent setup](https://www.superlogical.com/rex/docs/automate/agent-skill)

## T3 Code

An environment owns its projects, threads, files, and providers. Its identity
survives endpoint changes. One client can remember several routes to it,
including a local network address, SSH, Tailscale, or T3 Connect. T3 checks
the expected environment before sending credentials to a direct route and
checks authorization before replacing a working connection. Two clones can
appear together in the UI while their threads stay on their respective
machines. Optional load balancing chooses a host for a new draft and keeps
that choice stable once made. [Remote architecture][t3-architecture] ·
[Remote access][t3-access]

A one-time pairing link enrolls a client for later connections. The host can
revoke the resulting session. Direct pairing and T3 Connect can give the
same device different permissions. There is also a recovery path worth
testing in kiki. If a desktop still has SSH login rights, it can pair again
after its T3 session is revoked. Losing one session and losing the ability
to obtain the next one are different outcomes. [Remote access][t3-access] ·
[Pairing grant implementation][t3-pairing]

T3 makes the conversation-sharing choice concrete for each harness.

| Harness     | Documented behavior                                                                                                                                                                                                                                                                                                                   |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Codex       | Two instances can use distinct logins and share session history and settings through a common Codex home and a shadow home. This allows an account switch inside an existing thread. Separate Codex homes keep separate history and settings and prevent continuing that thread from the other home. [Codex provider guide][t3-codex] |
| Claude Code | Each account can have its own configuration directory on the execution machine. Existing threads can switch between instances using the same directory. The guide asks the user to check the reported account after login. [Claude provider guide][t3-claude]                                                                         |

Provider names are local to the environment. A T3 mobile regression test
gives two environments the same provider instance ID and checks that each
thread gets the settings from its own environment. That is exactly the case
kiki will face when two hosts both label a local harness account “work”.
[Thread provider resolution test][t3-test]

T3 also distinguishes a human connecting from a second device from an agent
delegating work to a second machine. The latter uses a separately approved
peer link. A new task can start a child thread on the destination. That host
checks the request against the link grant and the calling agent's limits.
The linked-environments feature is documented as a beta. For kiki, this is a
precedent for making delegation a separate future capability. Simply adding
a host to a person's Work view should grant their agents no cross-host
powers. [Peer links][t3-architecture]

## Changes I recommend for kiki

1. **Save an execution environment per OS user.** Two accounts on one Mac
   can own separate daemons. Pair with the intended daemon and keep its
   stable identity alongside its authenticated routes. Persist the repo and
   thread IDs with that choice. A new network address, an identical repo
   URL, or a familiar profile name cannot redirect a thread. Start with one
   SSH route. When a second route ships, require the same profile grant and
   recheck the authenticated peer before sending private data.
2. **Bind both login and history at creation.** Record the environment,
   portable profile ID, host-local harness configuration ID, expected provider account where verifiable, and
   which session store the adapter may resume from. Check them again on
   reopen. Keep each user-defined profile’s history separate by default. If
   the provider reports a different login after reauthentication, pause
   before giving it the prompt. A shared-history feature would need its own
   explicit disclosure. Keep kiki's launch-specific hooks and settings
   under the existing [harness contract](../../../docs/reference/book/13-architecture/harness-adapter.md).
3. **Make sharing say what the recipient gets.** “View status for this
   repo” and “use terminals as this OS user” describe very different
   grants. Use the first for a friend's status view. Give interactive
   shared work its own OS account or virtual machine when other profiles
   must stay private. Show the selected profile, host, and harness account
   together when creating or resuming work.
4. **Test revocation through every way back in.** Revoke a paired laptop
   during an attach. Its stream should close, its unused approvals should
   expire, and pairing again with the old enrollment should fail. Another
   authorized viewer and the agent should keep running. If the laptop has
   independent OS login rights, explain that those rights are managed on
   the host. Kiki cannot revoke an independent shell login.

For the first end-to-end trial, put Work and Personal on one host with
separate accounts and histories. Give both a repo and thread of the same
name. From a laptop with a different harness login, attach to Work, lose
the connection, and reconnect. Check the same thread ID and agent
incarnation. Then sign the Work profile’s harness in with a different account
and try a reopen. Verify the host detects the change before disclosing any
history. Finally revoke the laptop and try each saved route. This exercises
the distinctions a smooth demo with one user and one account would miss.

## Evidence and limits

Reviewed the public Rex beta manuals on the date above. T3 links below
pin its project documentation, pairing code, and provider-resolution test
to commit `1063b42768cb2ae43f123a220b6a2188df4b5998`. These are documented
behaviors and source observations. This investigation did not run either
product or test provider billing, history isolation, or live revocation.
The kiki recommendations are proposals. The
[remote service contract](../../../docs/reference/book/13-architecture/grpc.md)
still leaves remote authority for future work.

[t3-architecture]: https://github.com/pingdotgg/t3code/blob/1063b42768cb2ae43f123a220b6a2188df4b5998/docs/internals/remote.md
[t3-access]: https://github.com/pingdotgg/t3code/blob/1063b42768cb2ae43f123a220b6a2188df4b5998/docs/user/remote-access.md
[t3-codex]: https://github.com/pingdotgg/t3code/blob/1063b42768cb2ae43f123a220b6a2188df4b5998/docs/user/providers-codex.md
[t3-claude]: https://github.com/pingdotgg/t3code/blob/1063b42768cb2ae43f123a220b6a2188df4b5998/docs/user/providers-claude.md
[t3-test]: https://github.com/pingdotgg/t3code/blob/1063b42768cb2ae43f123a220b6a2188df4b5998/apps/mobile/src/features/threads/thread-provider-instance.test.ts
[t3-pairing]: https://github.com/pingdotgg/t3code/blob/1063b42768cb2ae43f123a220b6a2188df4b5998/apps/server/src/auth/PairingGrantStore.ts
