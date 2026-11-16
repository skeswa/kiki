# D-0004: Host threads in a dedicated Herdr server instead of tmux

- Recorded: 2026-11-16
- Decided by: owner, 2026-11-16, for the direction and topology; source: the redesign instruction, "The chosen direction is to use Herdr as kiki’s terminal foundation, replacing tmux, while retaining jj as the VCS." The agent carrying out that instruction chose to keep `kk switch` caller-local through an upstream extension and to keep the pane launcher alive as the agent pane's direct child; the instruction asked for those points to be resolved explicitly.
- Topic: Terminal runtime ownership and topology
- Supersedes: the tmux commitments in [Thread head and lifecycle sagas](../../docs/reference/book/17-decisions/thread-head-and-sagas.md) and the tmux-shaped daemon anchor formerly in the Daemon chapter
- Superseded by: —

## Decision

Herdr is kiki's terminal runtime. Kiki runs one dedicated, named Herdr server per
user, separate from the user's default Herdr server in process, socket, saved
session, and configuration file. `kkd` alone starts it, under the user's
service manager. Each thread gets one Herdr
workspace, called a terminal group, with role panes for the managed agent, the
human shell, and an optional kiki UI.

`kkd` stays a separate coordinator. It owns thread identity, SQLite, jj
workspace creation and deletion, follows, journals, approvals, harness launch
and delivery, and OS process proofs. Herdr owns PTYs, layout, input, rendering,
and its native sidebar. Kiki integrates through Herdr's executable, JSON socket
API, configuration, and plugin facilities. It does not fork Herdr, and it never
uses Herdr's Git worktree methods.

`kk switch` stays caller-local. Kiki requires an upstream client-targeted focus
extension instead of adopting Herdr's broadcast focus.

## Why

The 2026-10-30 investigations showed Herdr can host a jj workspace through its
plain workspace and layout methods, launch a direct argv command with explicit
cwd and env, and survive client detach. Its integrated agent workspace UI is the
product reason to adopt it. The same evidence showed what it does not provide:
idempotent provisioning, a public server identity, caller-targeted focus,
durable metadata, a managed restore, or proof that processes exited. Tmux
provides none of those proofs either, and the orphan-writer behavior was
reproduced under both. Those gaps are therefore kiki adapter contracts, not
reasons to keep tmux. The 2026-11-16 revalidation against Herdr commit
`ee5bfb5041bb` confirmed each gap and the available seams.

Adoption is a contract change, not a validation claim. The Herdr-backed
acceptance gate is unproven, and one part of it depends on an upstream change:
client-targeted focus. Two adversarial reviews on 2026-11-16 corrected earlier
wording: Herdr's macOS terminal-quit fix covers only servers Herdr spawns
itself, so kiki places `kkd` and the server under the service manager instead
of requiring a Herdr release; and Herdr cannot relocate its state without
leaking environment into panes, so isolation is by session name and
configuration file, not by directory.

## Alternatives and consequences

- **Keep tmux, optionally nested in Herdr.** Preserves direct tmux workflows but
  gives up the native agent UI and adds nested-terminal behavior to test.
- **One Herdr session per thread or per repo.** A Herdr session is a server; this
  multiplies servers and sockets and complicates cross-repo switching.
- **The user's default Herdr server.** Couples kiki's restore and configuration
  policy to unrelated terminals.
- **Fork Herdr or extract its libraries.** Larger ownership with no evidence yet
  that the process boundary is insufficient. Revisit if the required extensions
  cannot land upstream.

Direct `tmux` use is no longer part of the ambient-coordinator promise; direct
`jj`, `gh`, and native Herdr use are. Kiki takes on a version-pinned dependency
and a small set of upstream requests.

## Links

- Contract: [Terminal runtime](../../docs/reference/book/13-architecture/terminal-runtime.md), [Threads](../../docs/reference/book/03-threads.md), [Build sequencing](../../docs/reference/book/15-build-sequencing.md)
- Evidence: [Herdr terminal runtime](../../docs/research/herdr-terminal-runtime.md), [Herdr foundations and jj integration](../../docs/research/herdr-jj.md), [2026-11-16 revalidation](../investigations/2026/2026-11-16-herdr-jj-revalidation.md)
- Related: [D-0005](0005-track-checkpoint-through-native-successors.md)
