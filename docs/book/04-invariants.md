# Invariants

These are the promises v1 relies on. They cut across the book; local chapter details should be read in light of them.

## Identity is stable

A thread has a stable `thread_id`. Bookmark names, workspace paths, tmux sessions, and harness sessions are projections. They may change. The `thread_id` must not.

This is load-bearing state. Credentials, audit rows, transcript rows, PR links, lifecycle state, and follows links all join through this identity. Code should treat bookmarks as handles, not identity.

## Workspaces are cooperative isolation

Thread workspaces prevent accidental file interference during normal use. They should not be documented, tested, or presented as filesystem security.

A same-UID process can read sibling workspaces, `~/.kiki`, and shared jj repository state. v1 accepts that fact and scopes credentials to reduce accidental blast radius, not to defeat an adversary with the user's privileges.

## Cascade happens only at safe boundaries

A following child is rebased onto ancestor changes only at an agent boundary or quiescence. kiki must not rewrite a thread's working copy while the agent is mid-edit.

It is acceptable for cascade to wait for a safe boundary. It is not acceptable for cascade to move the working copy while the agent is mid-edit.

## Cascade delivery is crash-safe

Cascade delivery must be idempotent and crash-safe. The system should prefer a rare duplicate delivery over silently dropping a cascade, provided the transcript remains idempotent.

The implementation therefore treats the outbox and acknowledgement sequence as durable protocol state.

## Human prose is owned by humans

Human-owned revision descriptions, bookmark names, and PR descriptions must not be silently overwritten.

kiki may draft. kiki may refresh when explicitly asked. It must preserve deliberate user prose unless the user opts back into regeneration.

## Transcripts stay local

Thread transcripts are local-only in v1. They may support local recall and reopen catch-up; they must not feed externally visible artifacts such as PR descriptions, auto-describe output, or auto-renames.

This is a confidentiality rule. Treat it accordingly.

## Authority is explicit

Destructive and cross-thread daemon mutations require `Admin`.

Thread-scoped credentials may operate on their own thread and may read the narrow same-repo summary surface. They must not read sibling transcripts, inspect sibling diffs, or mutate sibling threads.
