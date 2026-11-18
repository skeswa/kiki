# D-0010: Define headless setup and installation changes

- Recorded: 2026-11-18
- Decided by: agent, in response to the owner’s request to address the open headless questions
- Topic: Headless operation
- Supersedes: —
- Superseded by: —

## Decision

First run consists of installing the daemon, optionally enrolling a presenter, and approving repo registration. Only a change to an existing service definition goes through the daemon’s installation-change method. It records the exact change before restarting. An operator can also supply Codex’s permission arguments in kiki’s user config for every launch of a thread.

## Why

A first install has no daemon to issue a challenge. Once installed, a stopped or unreachable daemon must not turn an upgrade into a fresh bootstrap. Recording the change lets a restarted daemon finish it. Supplying Codex arguments at launch works with an empty workspace and preserves the generated home that isolates kiki’s hooks.

The foreground-supervisor and SSH-only macOS modes remain unverified. Each requires a real survival test in its own environment before support can be claimed.

## Links

[First run](../../docs/reference/book/09-commands.md#first-run) · [Bootstrap call](../../docs/reference/book/13-architecture/grpc.md#changing-the-daemon-installation) · [Codex settings](../../docs/reference/book/11-configuration.md#sections) · [D-0009](0009-operate-headless-with-a-configurable-automation-policy.md)
