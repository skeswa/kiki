# v1 invariants

These are the non-negotiable behavioral promises of v1. They cut across multiple specs and any implementation that violates one is wrong, regardless of which spec file the implementation work nominally belongs to.

- A thread has a stable `thread_id`. Bookmark names, workspace paths, tmux sessions, and harness sessions are mutable projections.
- Thread workspaces provide cooperative separation only; they are not a filesystem security boundary.
- A following child is rebased onto ancestor changes only at an agent boundary or quiescence.
- Cascade delivery is idempotent and crash-safe. Silent loss is not acceptable; duplicate delivery is acceptable in pathological retry cases.
- Human-owned revision descriptions, bookmark names, and PR descriptions are not silently overwritten.
- Thread transcripts are local-only and must not feed externally visible artifacts in v1.
- Destructive and cross-thread daemon mutations require `Admin`.
- Thread-scoped credentials cannot read sibling transcripts or mutate sibling threads.
