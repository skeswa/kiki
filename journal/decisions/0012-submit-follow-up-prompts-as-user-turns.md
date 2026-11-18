# D-0012: Submit follow-up prompts as user turns

- Recorded: 2026-11-18
- Decided by: agent, in response to the owner’s request to address the open headless questions
- Topic: Headless operation
- Supersedes: —
- Superseded by: —

## Decision

Include `kk prompt` in the acceptance slice for Claude Code and Codex. A caller can send literal text to the current incarnation without attaching a viewer. Each submission needs a one-shot approval for that prompt and a harness receipt before kiki reports success. An operator can grant the `prompt` operation to a named automation credential.

## Why

A script needs a way to continue the same conversation after `kk new -m`. Typing through Herdr could send text to a permission dialog or to a different process after a restart. The harness must allow kiki to address a new user turn explicitly and to identify an earlier submission after a lost reply. This is a requirement for the adapter proof. Neither harness has passed it in kiki.

The other interface choices in D-0009 stand. A thread rule covers whoever presents that credential. A consent rule names the exact purpose and provider. Any authenticated local caller may revoke authority, including an agent. This lets the caller interrupt automation but cannot give it more power. The overlay requests human confirmation whenever it shows an approval card, even when policy would allow the plan. Scripts use the CLI for unattended approval.

## Links

[Prompt command](../../docs/reference/book/09-commands.md#kk-prompt) · [Harness proof](../../docs/reference/book/13-architecture/harness-adapter.md#capabilities) · [D-0009](0009-operate-headless-with-a-configurable-automation-policy.md)
