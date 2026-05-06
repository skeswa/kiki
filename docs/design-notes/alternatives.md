# Alternatives and rejected directions

## Per-repo daemon

Rejected for v1. kiki uses one user-scoped daemon so cross-repo visibility and daemon lifecycle are simple for the user.

## Security boundary via workspaces

Rejected as a v1 claim. Workspaces are useful cooperative separation, but they do not constrain same-UID agents.

## Mirroring jj flags

Rejected. kiki provides thread-aware porcelain. Users should run `jj` directly for arbitrary jj behavior.

## Transcript-fed publishing

Rejected for v1. Transcript prose is local-only and often contains sensitive or dead-end context. Publishing and auto metadata features must not consume it.
