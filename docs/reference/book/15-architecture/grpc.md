# gRPC service

`kkd` exposes a single stable gRPC service over a unix socket. `kk`, `kk-hook`, the persistent sidebar, and any future UI are all clients of this service. There is no privileged internal API.

## Transport

- Socket: `~/.kiki/kkd.sock`, mode `0600`.
- Protocol: gRPC (`tonic`) with proto3 schema-versioned via field-add discipline. Server-streaming RPCs are used for event subscriptions.
- Filesystem permissions on the socket are necessary but not sufficient — `AuthEnforcer` validates the credential carried on every call.

## Surfaces

The proto is partitioned by capability class. Every method declares the minimum credential class it requires (`Admin` or `ThreadScoped<T>`); `AuthEnforcer` enforces that statically declared minimum at request entry.

| Surface            | Methods (illustrative)                                     | Min capability                                                                                        |
| ------------------ | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Repo registry      | `RegisterRepo`, `UnregisterRepo`, `ListRepos`              | `Admin`                                                                                               |
| Thread lifecycle   | `NewThread`, `Close`, `Reopen`, `Destroy`                  | `Admin`                                                                                               |
| Thread reads (own) | `GetThreadState`, `StreamThreadEvents`, `ReadContextQueue` | `ThreadScoped<T>`                                                                                     |
| Repo summaries     | `RepoThreadSummaries` (server-streaming)                   | `ThreadScoped<T>` (read-only sibling summaries, same-repo only — see [Authority](../06-authority.md)) |
| Cascade hook       | `PreToolUseDecision`, `MarkDelivered`                      | `ThreadScoped<T>`                                                                                     |
| Transcript         | `ReadTranscript`, `SearchTranscript`                       | `Admin` (human CLI / TUI)                                                                             |
| Publish            | `Publish`                                                  | `Admin`                                                                                               |
| Audit              | `GetAuditLog`, `GetThreadAudit`                            | `Admin`                                                                                               |
| Config             | `GetConfig`, `SetConfig`                                   | `Admin`                                                                                               |

There is **no** `Switch` RPC. `kkd` does not own focus. The CLI decomposes switch into (i) a read-only `RepoThreadSummaries`-class lookup of the target thread's tmux session name (any valid credential, including `ThreadScoped<other>`, suffices) and (ii) a `tmux switch-client -t <session>` invocation. See [Authority](../06-authority.md).

(The MCP transcript surface, when it ships, lives on a separate socket — see [Roadmap](../18-roadmap.md).)

## Streaming events

UIs subscribe via server-streaming RPCs rather than polling:

- `StreamThreadEvents(thread_id)` — state transitions, cascade events, transcript appends for one thread.
- `RepoThreadSummaries(repo_id)` — one-line summaries for sibling threads in the same repo, used by the sidebar.

On disconnect, clients reconnect and re-subscribe; events carry monotonic `seq` so clients can detect gaps.

## Protocol stability

The proto file is the contract. Proto3 forward-compatibility rules apply: never reuse field numbers, never narrow types, prefer adding new methods over changing existing semantics. Breaking changes require a new service version; the daemon may host both versions during a transition.

## Future surfaces

A native macOS GUI, a web UI, or a remote/mobile client all consume the same gRPC service. None of them can do anything `kk` and `kk-hook` cannot do.
