# Do the Herdr and jj findings still hold for the versions the redesign targets?

- Date: 2026-11-16
- Type: Investigation
- Topic: Herdr terminal runtime and jj semantics
- Related plan or decision: [D-0004](../../decisions/0004-use-herdr-as-terminal-runtime.md), [D-0005](../../decisions/0005-track-checkpoint-through-native-successors.md)

## Summary

The 2026-10-30 findings hold, with corrections. Herdr at source commit
`ee5bfb5041bb` still offers the seams the redesign uses and still lacks the
guarantees kiki must supply itself. jj 0.46.0, the repository's pinned
version, reproduces every recorded 0.44.0 result except one, and extra probes
show the checkpoint-bookmark inconsistency is broader than first reported.
Nothing here validates kiki; kiki has no implementation.

## Context

The owner chose Herdr as the terminal runtime. The earlier reports examined
Herdr source at one revision and ran a different, older released binary, and
ran jj 0.44.0. The redesign needed each capability it relies on checked
against one named revision and the pinned jj.

## Findings

**Herdr.** Source reading at `ee5bfb5041bbc3e4a49d591c72308aae3c81ecdde`
(package 0.9.5, clean tree) and headless runs of the released 0.9.5 binary
(tag commit `2ecf19a`) with disposable state, no agents, and no attached
clients. Source-only facts are marked.

- `workspace.create` takes no command and always starts a default shell.
  `layout.apply` takes per-pane argv, cwd, and env, always creates a tab, and
  replaces a tab when given its id.
- There is no request key, create-if-absent, or label uniqueness. Unknown
  request parameters are silently ignored: a `client_id` on `workspace.focus`
  and a `request_key` on `workspace.create` were both accepted and had no
  effect.
- The public API exposes no server instance identity. Workspace ids come from a
  per-process counter and recurred after a restart: `w4` was created, closed,
  and issued again by the next server lifetime. Cold restore returned the same
  workspace, tab, and pane ids with new `terminal_id` values.
- Labels persist across cold restore. Metadata tokens do not, and a second
  caller overwrote another caller's token. Launch env is neither readable nor
  persisted. Launch argv is saved but not rerun; a restored pane ran `/bin/sh`.
- Every public focus method moves all attached clients. No public method,
  pane environment, keybinding command, or plugin context names a client
  (source). Per-client navigation exists only on the private client protocol
  (source).
- `workspace.close` and `pane.close` reply `ok`. Teardown samples the child's
  session once and escalates signals; survivors produce only a log line
  (source). No fencing method exists.
- Events have a 512-entry in-memory history, no sequence on the wire, and an
  `events_lost` signal (source, partly run).
- Agent integration is installed only on request and adds a session-start hook;
  it removes older Herdr pre-tool entries (source).
- With a session name, Herdr derives the socket path and ignores an explicit
  socket override; a named session shares the default configuration file
  unless a configuration root is set (source).
- The macOS terminal-application-quit fix `b431a063` is an ancestor of the
  candidate commit and of no release tag. Live handoff is Unix-only and
  documented as experimental (source). Neither was run.

**jj 0.46.0.** Disposable repositories; receipts under
[evidence](../../evidence/herdr-jj-revalidation/2026-11-16/README.md).

- The published probe passes. One value changed: in a colocated repository an
  added workspace now has a Git worktree, and `git.colocate` defaults to true.
- A bookmark follows the commit it names through snapshot, `describe`, rebase,
  and ancestor rewrite, and stays behind on `jj new` and `jj commit`. `jj split`
  and squashing the bookmarked commit into its parent move it to a different
  change. `jj abandon` deletes it. Divergent successors leave it conflicted.
- Dirty `jj workspace update-stale` exits 0 while the edit survives only in a
  divergent successor.
- With several operation heads, `--at-op=@` fails. Reads at an exact head id
  change nothing. Every repository-loading command without `--at-op` merges the
  heads, even with `--ignore-working-copy`. Nothing supported lists all heads.
- Most read-looking commands snapshot a dirty working copy unless told to
  ignore it.

**Not established.** Server identity from socket peer credentials; the launcher
under real Claude Code or Codex; anything on Linux or Windows; live handoff;
terminal-application quit; timing races between jj writers; predecessor
records after `jj op abandon` or from older jj versions.

## Conclusion and follow-up

The findings support the contracts recorded in D-0004 and D-0005 and correct
two earlier statements: workspace ids do recur, not merely can; and an exiting
pane closes, with no configurable respawn. The open proofs are the gates in
[Build sequencing](../../../docs/reference/book/15-build-sequencing.md) and the
capability table in
[Terminal runtime](../../../docs/reference/book/13-architecture/terminal-runtime.md).

## Evidence and reproduction

- jj: [run notes, captures, and probe scripts](../../evidence/herdr-jj-revalidation/2026-11-16/README.md).
- Herdr: no capture was retained. The run used the method of the
  [published lifecycle probe](../../../docs/public/research/herdr-runtime/herdr_runtime_probe.py)
  with a temporary configuration root that was removed afterward; its
  observations are the bullets above. Source facts cite the candidate commit
  and can be rechecked there.
- Earlier reports: [Herdr terminal runtime](../../../docs/research/herdr-terminal-runtime.md), [Herdr foundations and jj integration](../../../docs/research/herdr-jj.md).
