# Roadmap

This chapter records deferred surfaces whose design affects v1 boundaries. Deferred does not mean vague. It means the book draws the boundary now, so v1 does not accidentally grow half of a future substrate.

## v1.x polish

The [v1.x tier](appendix-a-glossary.md#v1-x-polish) is enumerated once, in [Orientation](01-orientation.md). This chapter does not keep a second list. What follows records design boundaries for deferred surfaces that need them. Only the scope ledger can promote a surface into the [acceptance slice](appendix-a-glossary.md#acceptance-slice).

## Terminal runtime

Kiki hosts [threads](appendix-a-glossary.md#thread) in a dedicated local [Herdr](appendix-a-glossary.md#herdr) server (see [Terminal runtime](13-architecture/terminal-runtime.md)). Herdr is a [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer): a program that runs many terminals and keeps them alive. A thread is kiki's unit of work.

The items below are deferred. Each is gated: it ships only after the named evidence exists. None of them is implied by Herdr already supporting the underlying feature.

| Item                       | What it would add                                                                                                                                                                                                                                                                                                   | Gate                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Live handoff               | Moving a running server's processes and [PTYs](https://en.wikipedia.org/wiki/Pseudoterminal) to a new Herdr server process without restarting agents. v1 never starts a handoff. After an observed one, it raises `TerminalMissing` and records the new server as unverified; the fix is `replace-terminal-server`. | Two things: a stability commitment for the handoff path upstream, and a passing test of a handoff under a managed agent. In that test every [binding](appendix-a-glossary.md#terminal-binding) and [incarnation](appendix-a-glossary.md#incarnation) is re-proven rather than assumed.                                                                                                                                                                                                                                |
| Windows                    | Running [`kkd`](appendix-a-glossary.md#kkd), the dedicated server, and threads on Windows.                                                                                                                                                                                                                          | [`ProcessSupervisor`](appendix-a-glossary.md#processsupervisor) evidence on Windows for process identity, freeze, [verified resume](appendix-a-glossary.md#verified-resume), [holder](appendix-a-glossary.md#holder) inventory, and [verified exit](appendix-a-glossary.md#verified-exit). Herdr running on Windows is not that evidence.                                                                                                                                                                             |
| Remote terminal hosting    | A dedicated Herdr server, and the threads' processes, on a machine other than the one running `kkd`.                                                                                                                                                                                                                | A way to obtain `ProcessSupervisor` proofs on the remote host. A remote Herdr endpoint cannot supply kiki's deletion proof. So this waits on the same transport and authentication contract as daemon-to-daemon coordination under [Later architecture](#later-architecture).                                                                                                                                                                                                                                         |
| Fork or library extraction | Maintaining a Herdr fork, or extracting its [crates](https://doc.rust-lang.org/cargo/reference/workspaces.html), instead of integrating across the process boundary.                                                                                                                                                | Only if the required upstream extension cannot land. Client-targeted focus is the only one. No particular Herdr release is required for the macOS terminal-application-quit case, because `kkd` runs as a [launchd](https://en.wikipedia.org/wiki/Launchd) user agent (a [systemd](https://en.wikipedia.org/wiki/Systemd) user unit on Linux) outside the terminal application, and the server is its own service-manager unit that outlives `kkd`. Without that trigger kiki does not fork Herdr or link its crates. |

[Client-targeted focus](appendix-a-glossary.md#client-targeted-focus) is the one required upstream extension. It is an acceptance-gate dependency rather than a roadmap item.

The optional upstream Herdr extensions below would each replace adapter work that v1 already makes safe on its own. Kiki adopts one only when the server advertises its capability. It never adopts one by sending a parameter and inferring support from the absence of an error.

- **Request keys** on create and layout calls. With them, a repeated provisioning call after a lost reply is [idempotent](https://en.wikipedia.org/wiki/Idempotence) (safe to repeat) at the runtime. Until then the journal, launcher reports, and single gate claim provide exactly-once effect.
- **Boot id** in the ping and snapshot replies, as a public [server-instance](appendix-a-glossary.md#server-instance) identity. Until then `server_instance_id` is kiki's row id for one observed socket peer `(pid, start_time)`.
- **[Mutation fence](appendix-a-glossary.md#mutation-fence)** on a [terminal group](appendix-a-glossary.md#terminal-group). With it, a split or new tab during freeze is prevented instead of detected. Until then snapshot comparison detects drift and forces a retry.
- **Termination receipt** on close, listing what the runtime signalled and what remained. It would be one more input to `ProcessSupervisor`, never a substitute for its OS-level verification.
- **Event cursor**: a wire sequence and resumable cursor on the event stream. Until then every gap is handled by a fresh snapshot.
- **Configuration and state root**: an option that places a server's configuration, socket, and saved state under a directory kiki names, without exporting that choice to panes. Until then:
  - kiki sets `HERDR_CONFIG_PATH` and a session name;
  - Herdr keeps the session's socket and saved state under its own directories;
  - kiki does not redirect `XDG_CONFIG_HOME` or `XDG_STATE_HOME`, because panes inherit the server's [environment](https://en.wikipedia.org/wiki/Environment_variable).

None of these changes a guarantee. Each narrows a window that the adapter already closes by journaling, re-reading the OS, or resynchronizing.

## v2 MCP substrate

MCP (the [Model Context Protocol](https://modelcontextprotocol.io/)) is a standard interface that lets agents call tools and read resources. The narrow read-only same-thread [transcript](appendix-a-glossary.md#thread-transcript) MCP surface may ship before v2. Broader MCP behavior waits for a dedicated substrate.

Deferred MCP behavior includes:

- cross-thread agent messages;
- agent-driven thread spawning;
- cross-thread read resources;
- [causal-chain](appendix-a-glossary.md#causal-chain) tracking;
- depth, cycle, and branch caps;
- richer audit surfaces for inter-thread activity.

## MCP identity

MCP uses a separate [unix socket](https://en.wikipedia.org/wiki/Unix_domain_socket). URL paths route requests; credentials supply identity. Think of the URL as the address on an envelope and the credential as the ID you show at the door: only the ID grants access.

A thread-scoped credential may read its own transcript. A URL such as `/threads/<uuid>` does not authorize the caller to act as that thread. Authorization is always bound to the credential presented on the request.

When the same-thread transcript MCP surface ships, each call is checked in this order, and the status codes are part of the contract:

1. Credentials that are missing, malformed, revoked, or carry an invalid signature get `Unauthenticated`.
2. Well-formed credentials that are not [`ThreadScoped<T>`](appendix-a-glossary.md#threadscoped-credential) get `PermissionDenied`. Neither reusable Admin authority nor one-shot [human approvals](appendix-a-glossary.md#human-approval) are exposed through the narrow transcript MCP surface.
3. If the request names a thread both in the URL path and in an explicit argument, and the two differ, the request gets `InvalidArgument`.
4. If the credential authorizes thread T and the request asks for thread U, where U is not T, the request gets `PermissionDenied`.

The [daemon](<https://en.wikipedia.org/wiki/Daemon_(computing)>) must not silently re-dispatch a request to the thread the credential authorizes. That would hide client bugs and make audit rows harder to interpret.

## Tool tiers

The v2 substrate divides tools by how much authority they need:

- Same-thread, low-risk tools may be self-acting, such as setting status or requesting human attention.
- Publish and close may be requested only as intents. Those intents stop at the foreground one-shot [human-approval](appendix-a-glossary.md#human-approval) boundary.
- Cross-thread summaries may be auto-allowed only within the minimal summary policy. Sensitive cross-thread reads require a foreground one-shot approval, so they are not autonomous MCP tools.
- Cross-thread posts and agent-driven spawns are rate-limited and causal-chain tracked.
- Cross-thread close, destroy, publish, and revision rewriting remain unavailable to agents. An agent request cannot itself satisfy or retain the human approval.

Destroy is not exposed to agents at all, including on the caller's own thread.

## Causal chains

Every agent-originated cross-thread post or spawn carries a `causal_chain_id`. A [causal chain](appendix-a-glossary.md#causal-chain) is a paper trail: it records which agent action caused which, so runaway agent-to-agent loops can be detected and capped.

Rules:

- a human-originated action starts a fresh chain;
- an agent action caused by an incoming context message inherits that message's chain;
- revisiting a thread within the same chain is a cycle, and a cycle quarantines the chain;
- the default depth cap is 5 hops;
- the default branch cap is 4 distinct threads;
- the default spawn cap is 1 agent-driven spawn per minute per parent thread;
- a human reply terminates the chain, and future actions start fresh.

The intended tables are `causal_chains` and `causal_chain_visits`. Both are deferred until the substrate ships.

## Later architecture

Likely later swaps:

- [harness](appendix-a-glossary.md#harness) adapters beyond `claude-code` and `codex`, behind the existing `Harness` and [`TranscriptAdapter`](appendix-a-glossary.md#transcriptadapter) [traits](https://doc.rust-lang.org/book/ch10-02-traits.html);
- direct GitHub REST or GraphQL, behind `GitHubBackend`;
- jj-lib (the [jj](https://docs.jj-vcs.dev/latest/) library), behind `JjBackend`;
- a native GUI, a web dashboard, or remote clients over the same [gRPC](https://grpc.io/) service;
- daemon-to-daemon coordination, so one machine's `kk` can observe, and eventually drive, threads whose [workspaces](appendix-a-glossary.md#workspace) live on another machine's `kkd`.

Working across machines is part of the product vision, not an accident of scope. The same-host boundary exists for one reason. Peer daemons, like remote clients, wait on the future transport and authentication contract. They do not inherit unix-socket assumptions.
