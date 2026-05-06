# v1 spec index

These files are the normative v1 implementation contract.

- [CLI](cli.md)
- [Thread lifecycle](thread-lifecycle.md)
- [Cascade](cascade.md)
- [Transcript](transcript.md)
- [Auth](auth.md)
- [Publishing](publishing.md)
- [Config](config.md)
- [TUI](tui.md)
- [Testing](testing.md)

## Non-negotiable invariants

- A thread has a stable `thread_id`. Bookmark names, workspace paths, tmux sessions, and harness sessions are mutable projections.
- Thread workspaces provide cooperative separation only; they are not a filesystem security boundary.
- A following child is rebased onto ancestor changes only at an agent boundary or quiescence.
- Cascade delivery is idempotent and crash-safe. Silent loss is not acceptable; duplicate delivery is acceptable in pathological retry cases.
- Human-owned revision descriptions, bookmark names, and PR descriptions are not silently overwritten.
- Thread transcripts are local-only and must not feed externally visible artifacts in v1.
- Destructive and cross-thread daemon mutations require `Admin`.
- Thread-scoped credentials cannot read sibling transcripts or mutate sibling threads.
