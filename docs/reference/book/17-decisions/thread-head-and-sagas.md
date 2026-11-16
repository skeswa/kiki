# Thread head and lifecycle sagas

A [thread](../appendix-a-glossary.md#thread) is kiki's unit of work: a named sequence of revisions in [jj](https://docs.jj-vcs.dev/latest/). This note records two decisions. The first is which commit counts as a thread's current tip. The second is how kiki runs multi-step actions, such as creating or closing a thread, so that a crash partway through does no harm.

## Decision

### The live head and the bookmark

An active thread's [live head](../appendix-a-glossary.md#live-head) is the exact commit at its managed [workspace](../appendix-a-glossary.md#workspace)'s `@`, persisted as `thread_head_commit_id`. (`@` is jj's name for a workspace's current working-copy commit.)

Its [bookmark](../appendix-a-glossary.md#bookmark) is a human-facing checkpoint, reopen handle, and publication [projection](../appendix-a-glossary.md#projection). Kiki moves that bookmark only at explicit checkpoints such as activation, publish, detach, and close. It does not assume jj moves a bookmark when `jj new` creates a child revision.

### The owned stack

V1 defines the thread's [owned stack](../appendix-a-glossary.md#owned-stack) as the provable single-parent chain from its exact [synchronized base](../appendix-a-glossary.md#synchronized-base) to `thread_head_commit_id`. A merge, multiple candidate roots, or foreign topology becomes [`TopologyDiverged`](../appendix-a-glossary.md#topologydiverged) and requires a human decision.

### Lifecycle sagas

Thread creation, close, reopen, repair, and destroy are durable [sagas](../appendix-a-glossary.md#saga). A saga is a multi-step action where each step is written down before it runs. Every external step and compensation (undo step) is journaled.

- Creation launches the [harness](../appendix-a-glossary.md#harness) last, after credentials and isolated hook settings are durable. It enters `Active` only after that [incarnation](../appendix-a-glossary.md#incarnation) proves exclusive boundary control in its [ready handshake](../appendix-a-glossary.md#ready-handshake).
- Reopen remains `Closed` under the same rule.
- Close runs these steps:
  1. It [freezes](../appendix-a-glossary.md#freeze) the complete managed process tree.
  2. It proves the final plan still matches the foreground approval.
  3. It checkpoints the exact frozen commit without snapshotting.
  4. It reconciles child detaches.
  5. It closes the thread's [terminal group](../appendix-a-glossary.md#terminal-group) only after those steps succeed.

Crash recovery continues from persisted saga state. It does not claim that [SQLite](https://www.sqlite.org/), jj, the filesystem, the terminal runtime, and a harness process share one [transaction](https://en.wikipedia.org/wiki/Database_transaction).

### Destroy

Destroy removes kiki's thread identity and local projections but preserves jj revisions by default. Optional revision abandonment is a separately approved mode naming only the exact validated, unreferenced linear chain.

Once an irreversible destroy step is recorded, failure enters `DestroyFailed`. Recovery may finish that plan. It may not infer that the old active or closed thread still exists intact.

## Why

Jj has no active bookmark that automatically follows ordinary child creation. (A bookmark does follow a rewrite of the commit it names; see the note below.) Treating the bookmark as a live thread tip can therefore make [follows](../appendix-a-glossary.md#follows) classification and publication silently target an older commit. The workspace view is already the authoritative live projection. Persisting its exact head makes that relationship explicit.

Likewise, cross-system “atomic spawn” and “atomic close” are not implementable promises. ("Atomic" means all-or-nothing.) A durable saga does three things:

- it exposes partial progress;
- it makes compensation [idempotent](https://en.wikipedia.org/wiki/Idempotence) (safe to repeat); and
- it prevents a failed post-stop check from returning a thread whose agent and terminal group are gone to `Active`.

## Deliberate limits

Kiki does not do any of these:

- move the bookmark to follow `@` after every observed jj operation,
- maintain a hidden second bookmark,
- infer arbitrary [DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph) ownership, or
- attempt universal automatic repair.

Projection mismatches are repaired automatically only when the intended state is provable. Otherwise `ProjectionDiverged` and `kk repair` keep the choice with the human.

## Later records

Added 2026-11-16. Two numbered records supersede specific parts of this note. The decision itself — the workspace `@` is the live head, the bookmark is a checkpoint, lifecycle work is a durable saga — stands.

- [D-0005](https://github.com/skeswa/kiki/blob/main/journal/decisions/0005-track-checkpoint-through-native-successors.md) supersedes the original wording that kiki "moves that bookmark only at explicit checkpoints" and the fixed expected target that followed from it. Kiki still _places_ the bookmark only at explicit checkpoints. Between placements jj itself carries the bookmark to rewrite successors of the commit it names — the first snapshot after creation does this — and kiki tracks a proven successor instead of raising a [projection issue](../appendix-a-glossary.md#projection-issue). `jj new` still leaves the bookmark behind, which is the case this note reasoned from.
- [D-0004](https://github.com/skeswa/kiki/blob/main/journal/decisions/0004-use-herdr-as-terminal-runtime.md) supersedes this note's tmux commitments. Threads are hosted in terminal groups on a dedicated Herdr server. The saga reasoning is unchanged and carries one more consequence: a terminal runtime's close reply is not proof that processes exited, so close verifies exit by OS process identity before it forgets the jj workspace.
