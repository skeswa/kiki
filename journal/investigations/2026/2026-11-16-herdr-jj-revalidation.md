# Do the Herdr and jj findings still hold for the versions the redesign targets?

- Date: 2026-11-16
- Type: Investigation
- Topic: Herdr terminal runtime and jj semantics
- Related plan or decision: [D-0004](../../decisions/0004-use-herdr-as-terminal-runtime.md), [D-0005](../../decisions/0005-track-checkpoint-through-native-successors.md)

## Summary

The 2026-10-30 findings hold, with corrections.

- [Herdr](https://github.com/herdrdev/herdr) is the [terminal multiplexer](https://en.wikipedia.org/wiki/Terminal_multiplexer) kiki plans to use. At
  source commit `ee5bfb5041bb` it still offers the seams (connection points)
  the redesign uses. It still lacks the guarantees kiki must supply itself.
- [jj](https://docs.jj-vcs.dev/latest/) is the version-control tool kiki drives. jj 0.46.0, the
  repository's pinned version, reproduces every recorded 0.44.0 result except
  one.
- Extra probes show the checkpoint-[bookmark](../../../docs/reference/book/appendix-a-glossary.md#bookmark) inconsistency is
  broader than first reported.

Nothing here validates kiki; kiki has no implementation.

## Context

The owner chose Herdr as the terminal runtime. The earlier reports examined
Herdr source at one revision. They ran a different, older released binary, and
they ran jj 0.44.0. The redesign needed each capability it relies on checked
against one named revision and the pinned jj.

## Findings

**Herdr.** The method was two-part. The first part was source reading at
`ee5bfb5041bb3e4a49d591c72308aae3c81ecdde` (package 0.9.5, clean tree). The
second was headless runs (no screen attached) of the released 0.9.5 binary
(tag commit `2ecf19a`) with disposable state, no agents, and no attached
clients. Source-only facts are marked "(source)".

- `workspace.create` takes no command and always starts a default shell.
  `layout.apply` takes per-pane argv, cwd, and env, always creates a tab, and
  replaces a tab when given its id.
- There is no request key, create-if-absent, or label uniqueness. Unknown
  request parameters are silently ignored: a `client_id` on `workspace.focus`
  and a `request_key` on `workspace.create` were both accepted and had no
  effect.
- The public API exposes no [server instance](../../../docs/reference/book/appendix-a-glossary.md#server-instance) identity.
  Workspace ids come from a per-process counter and recurred after a restart:
  `w4` was created, closed, and issued again by the next server lifetime.
  [Cold restore](../../../docs/reference/book/appendix-a-glossary.md#cold-restore) returned the same workspace, tab, and pane
  ids with new `terminal_id` values.
- Labels persist across cold restore. Metadata tokens do not, and a second
  caller overwrote another caller's token. Launch env (the
  [environment variables](https://en.wikipedia.org/wiki/Environment_variable) given at launch) is neither readable nor
  persisted. Launch argv is saved but not rerun; a restored pane ran `/bin/sh`.
- Every public focus method moves all attached clients. No public method,
  pane environment, keybinding command, or plugin context names a client
  (source). Per-client navigation exists only on the private client protocol
  (source).
- `workspace.close` and `pane.close` reply `ok`. Teardown samples the child's
  session once and escalates [signals](<https://en.wikipedia.org/wiki/Signal_(IPC)>). Processes that survive
  produce only a log line (source). No fencing method exists.
- Events have a 512-entry in-memory history, no sequence on the wire, and an
  `events_lost` signal (source, partly run).
- Agent integration is installed only on request and adds a session-start
  hook. It removes older Herdr pre-tool entries (source).
- With a session name, Herdr derives the socket path and ignores an explicit
  socket override. A named session shares the default configuration file
  unless a configuration root is set (source).
- The macOS terminal-application-quit fix `b431a063` is an ancestor of the
  candidate commit and of no release tag. Live handoff is Unix-only and
  documented as experimental (source). Neither was run.

**jj 0.46.0.** The runs used disposable repositories. Receipts are under
[evidence](../../evidence/herdr-jj-revalidation/2026-11-16/README.md).

- The published probe passes. One value changed: in a
  [colocated](https://docs.jj-vcs.dev/latest/git-compatibility/) repository (one shared with Git) an added
  [workspace](../../../docs/reference/book/appendix-a-glossary.md#workspace) now has a [Git worktree](https://git-scm.com/docs/git-worktree), and
  `git.colocate` defaults to true.
- A bookmark follows the commit it names through snapshot, `describe`, rebase,
  and ancestor rewrite, and stays behind on `jj new` and `jj commit`. `jj split`
  and squashing the bookmarked commit into its parent move it to a different
  change. `jj abandon` deletes it. Divergent successors leave it conflicted.
- Dirty `jj workspace update-stale` exits 0 while the edit survives only in a
  divergent successor.
- With several [operation](https://docs.jj-vcs.dev/latest/operation-log/) heads, `--at-op=@` fails. Reads at an
  exact head id change nothing. Every repository-loading command without `--at-op` merges the
  heads, even with `--ignore-working-copy`. Nothing supported lists all heads.
- Most read-looking commands [snapshot](https://docs.jj-vcs.dev/latest/working-copy/) a dirty working copy unless
  told to ignore it.

**Later the same day**, adversarial reviews of the redesign added facts, again
from source at the candidate commit and headless runs of 0.9.5:

- The API socket is served by the server process itself. On macOS the socket
  peer [pid](https://en.wikipedia.org/wiki/Process_identifier) equalled the server pid across two lifetimes (run).
- Panes inherit the server's whole environment, including redirected
  [XDG](https://specifications.freedesktop.org/basedir-spec/latest/) variables (run). Herdr has no option to relocate session state.
- A Herdr workspace disappears when its last pane's command exits, with only a
  pane-exit event (run). Layout application over a tab appends a new tab with
  new ids (run). The first workspace on an empty server takes focus (run).
- Workspace ids resume above the highest surviving id: after `w1` and `w4` were
  closed, the next lifetime issued `w6`. An id recurs only when it was the
  highest, as in the earlier `w4` observation.
- Toasts are off by default and the reply is not a display receipt. The ping
  capabilities are an object of flags, and the live-handoff flag is already
  true. A parse failure of the configuration loads defaults (source).
- The macOS terminal-quit fix applies only to servers Herdr auto-spawns
  (source).
- A launch environment value is absent from every Herdr API and saved file but
  readable through `ps` by the same user (run).
- jj (all run):
  - `jj undo` returns a bookmark to the pre-succession commit.
  - A pinned mutation racing another operation leaves two heads.
  - `jj workspace add` and `forget` can be pinned.
  - `jj op abandon` rewrites recorded operation ids.
  - A backward bookmark move needs `--allow-backwards`.

**Not established.** These were not checked:

- server identity from [socket peer credentials](https://man7.org/linux/man-pages/man7/unix.7.html) on Linux;
- the launcher under real [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) or [Codex](https://github.com/openai/codex);
- anything on Linux or Windows;
- live handoff;
- terminal-application quit;
- timing races between jj writers;
- predecessor records after `jj op abandon` or from older jj versions.

## Conclusion and follow-up

The findings support the contracts recorded in D-0004 and D-0005. They also
correct two earlier statements:

- a workspace id can be issued again by a later server lifetime; and
- an exiting pane closes, with no configurable respawn outside live-handoff
  imports.

The open proofs are the gates in
[Build sequencing](../../../docs/reference/book/15-build-sequencing.md) and the
capability table in
[Terminal runtime](../../../docs/reference/book/13-architecture/terminal-runtime.md).

## Evidence and reproduction

- jj: [run notes, captures, and probe scripts](../../evidence/herdr-jj-revalidation/2026-11-16/README.md).
- Herdr: no capture was retained. The run used the method of the
  [published lifecycle probe](../../../docs/public/research/herdr-runtime/herdr_runtime_probe.py)
  with a temporary configuration root that was removed afterward. Its
  observations are the bullets above. Source facts cite the candidate commit
  and can be rechecked there.
- Earlier reports: [Herdr terminal runtime](../../../docs/research/herdr-terminal-runtime.md), [Herdr foundations and jj integration](../../../docs/research/herdr-jj.md).
