# Thread lifecycle spec

## Thread identity

Each thread has a stable sqlite `thread_id`. The thread id is the join key for credentials, audit rows, transcript rows, PR links, lifecycle state, and follows links.

Mutable projections include:

- jj workspace path
- jj bookmark name
- tmux session name
- harness session id

## Creation

`kk new` atomically creates:

- sqlite thread row
- jj workspace
- bookmark
- initial jj change on that bookmark
- tmux session rooted in the workspace
- harness process
- per-thread hook credential and hook configuration

If any step fails, kiki unwinds prior steps to avoid orphaned state.

When invoked inside an existing thread, `kk new` follows the current thread by default. `--no-follow` suppresses that default. `--follows <parent>` selects an explicit parent.

## Workspace isolation

Per-thread workspaces prevent accidental file interference during normal cooperative use. They do not prevent a same-UID process from reading or writing sibling workspaces, `~/.kiki`, or shared jj repository state.

## Close

`kk close` archives a thread without deleting tracked jj work.

Close is two-phase:

1. Preflight performs no destructive mutation.
2. Commit stops the agent and tmux session, reruns loss-prevention checks, forgets the jj workspace, deletes the materialized workspace directory, and marks the thread closed.

Close must allowlist kiki-owned ephemeral workspace files such as `<workspace>/.kiki/hook-cred` and generated per-thread harness config. These files must not self-block close. User-created untracked or ignored files that would be deleted still require explicit handling.

Plain `kk close` leaves any open PR untouched. `kk close --discard-pr` is the explicit PR-closing path.

Children of a closed thread auto-detach with notification.

## Reopen

`kk reopen <thread>` restores a closed thread by recreating the workspace, tmux session, hook credentials, and harness process.

Reopen prepends a short local catch-up message composed from non-synthesized transcript rows. The catch-up is local-only and is recorded as kiki-authored synthesized transcript content.

## Destroy

`kk thread destroy <thread>` is irreversible except through jj operation recovery. It abandons the bookmark, revokes credentials, tombstones the thread row, and deletes transcript rows by default.

`--keep-log` retains transcript rows for explicit destroyed-thread views.
