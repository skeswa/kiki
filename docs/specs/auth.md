# Auth spec

kiki's v1 authorization model reduces accidental and buggy agent blast radius. It does not defend against an actively malicious same-UID process.

## Credential classes

`Admin`:

- required for global, cross-thread, or destructive daemon mutations
- read by human CLI and TUI from `~/.kiki/admin-cred`

`ThreadScoped<thread_id>`:

- bound to one thread
- written to `<workspace>/.kiki/hook-cred`
- read by `kk-hook`, sidebar, and the same-thread MCP client when MCP ships
- rotated on close and reopen

## Thread-scoped permissions

Thread-scoped credentials may:

- read their own thread state
- participate in cascade acknowledgement and delivery for their own thread
- read and drain their own context queue according to the cascade protocol
- write kiki-owned metadata only where explicitly allowed
- subscribe to same-repo thread summaries if the sidebar ships

Thread-scoped credentials must not:

- mutate sibling threads
- read sibling transcripts
- read sibling diffs
- publish, close, destroy, or reparent threads

## Repo summary exception

The persistent sidebar may need same-repo sibling summaries. This is the only v1 cross-thread read allowed to `ThreadScoped` credentials.

Allowed fields are summary-only: name, status, PR number, last description, and similar one-line display data. No transcripts, diffs, cascade counters, or write operations are included.

The same scope serves both the overlay's Stack and Activity sections and the persistent sidebar's two sections — they are one renderer reading one row set. The Activity section adds _ordering_ (most-recent agent event), not new fields.

## Switch is not Admin-gated

`kk switch <thread>` is not a daemon mutation and is not gated on `Admin`. "Active thread" is not `kkd`-owned state — `kkd` discovers focus via `ContextDiscovery` (env → tmux session name → cwd), it does not store it. Switch decomposes into:

1. A read-only daemon lookup of the target thread's tmux session name. Any valid credential — including a `ThreadScoped<other>` credential held by the persistent sidebar — is sufficient. This is a `RepoThreadSummaries`-class read.
2. A `tmux switch-client -t <session>` invocation that targets tmux, not `kkd`.

There is no cross-thread state mutation to authorize. `kk switch` may emit a `thread.switch_invoked` audit-log row when invoked from a credentialed CLI subprocess (the `kk` binary always reads `~/.kiki/admin-cred`); the audit emission is the only daemon write in the flow and it records the invoker, not the target. This is what lets the persistent sidebar drive switches without escalating beyond `ThreadScoped + RepoThreadSummaries`.

## Audit

Every parseable daemon transport attempt is logged with method/path, credential identity when identifiable, declared scope, compact args summary, outcome, and timestamp.

`kk audit log` is Admin-only. `kk thread audit` exposes per-thread slices.
