# Invariants

These are the promises v1 relies on. They cut across the book; local chapter details should be read in light of them.

## Identity is stable

A thread has a stable `thread_id`. Bookmark names, workspace paths, tmux sessions, and harness sessions are projections. They may change. The `thread_id` must not.

This is load-bearing state. Credentials, audit rows, transcript rows, PR links, lifecycle state, and follows links all join through this identity. Code should treat bookmarks as handles, not identity.

## Workspaces are cooperative isolation

Thread workspaces prevent accidental file interference during normal use. They should not be documented, tested, or presented as filesystem security.

A same-UID process can read sibling workspaces, `~/.kiki`, and shared jj repository state. v1 accepts that fact and scopes credentials to reduce accidental blast radius, not to defeat an adversary with the user's privileges.

## Cascade materializes only at safe boundaries

A parent rewrite may cause jj to evolve descendant commits immediately in repository state. Kiki must not redundantly rebase that already-evolved history. It records the exact transition from the last synchronized base to the evolved base, then materializes the child's current jj state only at an agent boundary or quiescence. It does not pin the child's working-copy commit as the target because that commit may legitimately evolve again before the boundary.

When a parent bookmark advances by adding a new revision, and the new tip is not already an ancestor of the child, kiki performs an explicit rebase of the child's owned stack at the same safe boundary. It is acceptable for either reconciliation kind to wait for a safe boundary or for `kkd` to become reachable. It is not acceptable for kiki to materialize or explicitly rebase the managed workspace while its agent is mid-edit, and it is not acceptable to silently drop pending reconciliation.

The guarantee is scoped to kiki-controlled mutations for the managed agent. A human who runs `jj` directly in a stale child workspace may explicitly update it before kiki's boundary. That command can alter files without advancing the op-log head, so kiki probes the workspace again at the next boundary rather than relying on watcher events alone. The ambient-coordinator posture does not pretend direct human commands are gated.

Kiki must not make unsnapshotted edits disappear from the visible working tree. Immediately before reconciliation it proves the stale workspace clean, or hard-pauses and enters explicit recovery. Recovery runs outside the source workspace, preserves and enumerates divergent successors, verifies where the edits landed, and resumes only after selecting a result that retains them or obtaining human direction.

## Cascade delivery is crash-safe

Cascade delivery must be idempotent and crash-safe. The system should prefer a rare duplicate delivery over silently dropping a cascade, provided the transcript remains idempotent.

The implementation therefore stores reconciliation, byte-stable delivery payload, acknowledgement, and recovery state on one durable `sync_intent`. It may derive UI state from those rows, but must not maintain a second progress protocol that can disagree with them.

## Human prose is owned by humans

Human-owned revision descriptions, bookmark names, and PR descriptions must not be silently overwritten.

kiki may draft. kiki may refresh when explicitly asked. It must preserve deliberate user prose unless the user opts back into regeneration.

## Transcripts stay local

Thread transcripts are local-only in v1. They may support local recall and reopen catch-up; they must not feed externally visible artifacts such as PR descriptions, auto-describe output, or auto-renames.

This is a confidentiality rule. Treat it accordingly.

## Authority is explicit

Destructive and cross-thread daemon mutations require `Admin`.

Thread-scoped credentials may operate on their own thread and may read the narrow same-repo summary surface. They must not read sibling transcripts, inspect sibling diffs, or mutate sibling threads.

## State is distinguishable without color

Every state kiki surfaces in any UI must be distinguishable without color. Glyphs and labels carry the signal; color is an accelerator, never the only signal.

Kiki honors `NO_COLOR=1` by emitting no ANSI color sequences. The shared `LogRenderer` and `StatusRenderer` projections must produce monochrome-distinguishable output for every state in the cascade, agent, and lifecycle vocabularies.
