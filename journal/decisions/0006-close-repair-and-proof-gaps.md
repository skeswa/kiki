# D-0006: Close the repair, locking, and proof gaps found in the third review

- Recorded: 2026-11-16
- Decided by: agent, 2026-11-16, while carrying out the owner's instruction "Spawn some adversarial review subagents and then address their feedback"; the owner has not yet ratified the individual choices below; source: five independent review reports of the same date, including jj 0.46.0 runs in throwaway repositories
- Topic: Repair plans, process safety order, locking, and proof gates
- Supersedes: —
- Superseded by: [D-0013](0013-prove-admission-and-delivery.md) for admission when the marker is absent. The marker and slow-path deadline still apply.

## Decision

A third review found places where the reference book gave two answers, no
answer, or an answer that could not be built. These choices settle them. Each
one refines [D-0004](0004-use-herdr-as-terminal-runtime.md) or
[D-0005](0005-track-checkpoint-through-native-successors.md); neither is
reversed.

**Checkpoint bookmark**

1. A checkpoint only moves the
   [bookmark](../../docs/reference/book/appendix-a-glossary.md#bookmark)
   forward along the thread's
   [owned chain](../../docs/reference/book/appendix-a-glossary.md#owned-stack).
   The approved repair plans `adopt-bookmark` and `choose-bookmark-target` may
   place it on the live head or on any commit on that chain, including an
   earlier one. Kiki never places it on a commit off the chain.
2. The thread's base is not part of the owned chain. A rewrite that carries
   the bookmark onto the base is an outside move and goes to repair.
3. `choose-bookmark-target` is the way out whenever the expected target is
   hidden, and whenever a thread reads `ahead` or `diverged`. Before this, some
   reachable states had no exit.
4. `reanchor-history` works thread by thread. It re-anchors each thread whose
   bookmark is in a good place and raises the ordinary bookmark issue for each
   one that is not.
5. Operation history counts as rewritten when any recorded operation that used
   to be an ancestor of the frontier no longer is. The earlier test missed an
   ordinary `jj op abandon` in the middle of the log.
6. The undo rule covers a thread's whole placement history. The expected
   target pops back when the bookmark returns to a commit recorded earlier as
   that thread's expected target and no later recorded successor is still
   visible. Publish checks that every commit it would push has a description
   before it moves anything.
7. `CheckpointAbandoned` is its own issue. It is raised only when the bookmark
   is gone and the expected target is hidden. A closed thread with this issue
   stays `Closed`; the issue blocks only reopen.

**Process safety**

8. `close-without-terminal` follows the same order as an ordinary close.
   Nothing is terminated before the
   [final proof](../../docs/reference/book/appendix-a-glossary.md#final-proof).
9. A close approval binds the set of terminal containers and the holders
   outside them. It does not bind the list of processes inside a container. A
   process that joins a listed container before the freeze is covered by the
   plan's container-scope statement.
10. Launcher reports can be repeated safely by the same process. Only the
    `agent` role is required for a terminal group to be bound.
11. New named plans: `terminate-orphans`, `replace-terminal-server`,
    `cleanup-failed-restart`, `retry-close`, `retry-destroy`,
    `recreate-workspace`, `reattach-workspace`, and `repoint-workspace`.
12. `kkd` starts the Herdr server as its own service-manager unit, so a `kkd`
    crash or upgrade does not stop the server or the agents. This is a proof
    gate, not yet a measured fact.
13. Each bound and deadline has a name and a default in a `[timeouts]`
    configuration table. The defaults are first guesses.

**Locks and hooks**

14. A per-repo jj lock guards every unpinned working-copy command. Lock order
    is parent thread, then child thread, then the repo jj lock.
15. `kkd` owns the pass-through admission cache. `kk-hook` keeps no state.
16. A hook call that `kkd` has admitted into a reconciliation waits up to the
    slow-path bound. If that runs out, the answer is a blocking deny, never
    "continue".

**Build order and proofs**

17. Stage 1 includes `kk-hook`, both harness adapters' launch specifications,
    and the exclusive-hook proof, because a thread cannot become `Active`
    without them.
18. Each outside fact the design depends on has a proof step and a stated
    outcome if the proof fails. For `RestartStartup` and for the session-start
    hook, a harness that fails the proof loses cascade delivery or support,
    recorded as a new decision.

**Later the same day**

19. When `kkd` blocks a thread's tool calls for a reconciliation, it first
    writes a small barrier marker file. A `kk-hook` call that cannot reach
    `kkd` checks for that file and blocks the tool call if it is there.
20. A failed creation has no retry plan. The way out is
    `cleanup-failed-create`, and then the human runs `kk new` again.
21. A Herdr server that `kkd` did not start is recorded as unverified. Kiki
    provisions nothing on it, and `replace-terminal-server` is the fix. This
    covers Herdr's own handoff or upgrade.

## Why

The reviewers showed concrete failures. Three chapters disagreed on which plan
could move a bookmark backward. A recovery plan killed processes before the
proof that was meant to protect them. A launcher that retried after a lost
reply would have been refused and its pane destroyed. The first build stage
could not pass its own gate. Leaving these open would push the choices onto
whoever writes the code, and a wrong guess in several of them is unsafe.

## Alternatives and consequences

- **Add a plan that places the bookmark off the owned chain.** Rejected for
  v1. The human can reshape history with jj and then adopt.
- **Bind the close approval to the exact process list.** Rejected. A busy
  terminal group changes its processes all the time, so close might never
  pass.
- **Keep per-thread locking only.** Rejected. The operation frontier belongs
  to the whole repo, so two threads could interleave unpinned commands.
- **Re-prove surviving processes after a Herdr server handoff.** Deferred. v1
  ends the bindings and restarts the terminal.

The new plans add options to `kk repair`, and the `[timeouts]` table adds
configuration settings. The timeout defaults, the service-manager unit shape, and the
fallbacks for failed proofs are untested and may change once measured.

## Links

- Contract: [Threads](../../docs/reference/book/03-threads.md), [Commands](../../docs/reference/book/09-commands.md), [Terminal runtime](../../docs/reference/book/13-architecture/terminal-runtime.md), [Op-log watcher](../../docs/reference/book/13-architecture/op-log-watcher.md), [Build sequencing](../../docs/reference/book/15-build-sequencing.md)
- Related: [D-0004](0004-use-herdr-as-terminal-runtime.md), [D-0005](0005-track-checkpoint-through-native-successors.md)
