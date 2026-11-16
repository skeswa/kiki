# Thread head and lifecycle sagas

## Decision

An active thread's live head is the exact commit at its managed workspace's `@`, persisted as `thread_head_commit_id`. Its bookmark is a human-facing checkpoint, reopen handle, and publication projection. Kiki places that bookmark only at explicit checkpoints such as activation, publish, detach, and close; it does not assume jj moves a bookmark when `jj new` creates a child revision.

V1 defines the thread's owned stack as the provable single-parent chain from its exact synchronized base to `thread_head_commit_id`. A merge, multiple candidate roots, or foreign topology becomes `TopologyDiverged` and requires a human decision.

Thread creation, close, reopen, repair, and destroy are durable sagas. Every external step and compensation is journaled. Creation launches the harness last, after credentials and isolated hook settings are durable, and enters `Active` only after that incarnation proves exclusive boundary control in its ready handshake. Reopen remains `Closed` under the same rule. Close freezes the complete managed process tree, proves the final plan still matches the foreground approval, checkpoints the exact frozen commit without snapshotting, reconciles child detaches, and closes the thread's terminal group only after those steps succeed. Crash recovery continues from persisted saga state rather than claiming SQLite, jj, the filesystem, the terminal runtime, and a harness process share one transaction.

Destroy removes kiki's thread identity and local projections but preserves jj revisions by default. Optional revision abandonment is a separately approved mode naming only the exact validated, unreferenced linear chain. Once an irreversible destroy step is recorded, failure enters `DestroyFailed`; recovery may finish that plan but may not infer that the old active or closed thread still exists intact.

## Why

Jj has no active bookmark that automatically follows ordinary child creation. (A bookmark does follow a rewrite of the commit it names; see the note below.) Treating the bookmark as a live thread tip can therefore make follows classification and publication silently target an older commit. The workspace view is already the authoritative live projection; persisting its exact head makes that relationship explicit.

Likewise, cross-system “atomic spawn” and “atomic close” are not implementable promises. A durable saga exposes partial progress, makes compensation idempotent, and prevents a failed post-stop check from returning a thread whose agent and terminal group are gone to `Active`.

## Deliberate limits

Kiki does not move the bookmark to follow `@` after every observed jj operation, maintain a hidden second bookmark, infer arbitrary DAG ownership, or attempt universal automatic repair. Projection mismatches are repaired automatically only when the intended state is provable; otherwise `ProjectionDiverged` and `kk repair` keep the choice with the human.

## Later records

Added 2026-11-16. Two numbered records supersede specific parts of this note. The decision itself — the workspace `@` is the live head, the bookmark is a checkpoint, lifecycle work is a durable saga — stands.

- [D-0005](https://github.com/skeswa/kiki/blob/main/journal/decisions/0005-track-checkpoint-through-native-successors.md) supersedes the original wording that kiki "moves that bookmark only at explicit checkpoints" and the fixed expected target that followed from it. Kiki still _places_ the bookmark only at explicit checkpoints. Between placements jj itself carries the bookmark to rewrite successors of the commit it names — the first snapshot after creation does this — and kiki tracks a proven successor instead of raising a projection issue. `jj new` still leaves the bookmark behind, which is the case this note reasoned from.
- [D-0004](https://github.com/skeswa/kiki/blob/main/journal/decisions/0004-use-herdr-as-terminal-runtime.md) supersedes this note's tmux commitments. Threads are hosted in terminal groups on a dedicated Herdr server. The saga reasoning is unchanged and carries one more consequence: a terminal runtime's close reply is not proof that processes exited, so close verifies exit by OS process identity before it forgets the jj workspace.
