# Project decisions

A decision record states a choice and its reason, ideally on one screen.
Create a record for a choice a future reader could reasonably want to reverse:

- a change to the domain model, identity rules, architecture, supported
  integrations, or a promise in the reference book;
- a policy for ownership, retention, publication, or external effects;
- moving, rewriting, or deleting retained evidence; or
- reversing or narrowing an earlier decision.

Routine implementation choices belong in the revision description. Scheduling
and implementation sequencing belong in the existing build sequence or roadmap.
An investigation may recommend a choice without recording it as decided.

## Recording a decision

1. Use the next unused four-digit number and a descriptive filename,
   `NNNN-short-choice.md`. The stable identifier is `D-NNNN`; coordinate the
   number when several contributors are working at once.
2. Copy the [template](TEMPLATE.md). State the decision, why it was made, who
   actually decided it, and the instruction or evidence behind it. Do not
   invent an owner approval or an earlier decision date.
3. Add the record to this index and update affected current documentation in
   the same change. A record documents a choice; it does not claim the choice
   has been implemented or validated.
4. To change a choice, write a new record linking the earlier one. Add a
   `Superseded by` link to the earlier record and annotate its index entry.
   Preserve its original reasoning. Corrections and link repairs may be made
   in place when they do not change the choice.

A record's existence means the named decider made the choice. There is no
status workflow or additional approval step for already authorized work.
Recording a decision does not grant permission for an action, and this
convention does not import Swingset's separate blanket delegation policy.

The [reference book's authority order](../../docs/reference/README.md#authority)
still governs product behavior. Report a disagreement and update the
chapter that defines the behavior; do not use a journal entry to override it silently.

## Decision index

| ID                                                                       | Choice                                                                   | Topic                                         |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | --------------------------------------------- |
| [D-0001](0001-adopt-project-journal.md)                                  | Separate current guidance, research history, and consequential decisions | Documentation                                 |
| [D-0002](0002-use-mise-for-tasks-and-formatting.md)                      | Use pinned mise tooling for tasks and formatting                         | Development workflow                          |
| [D-0003](0003-use-jj-and-shared-agent-guidance.md)                       | Use colocated jj and one shared contributor guide                        | Version control and contributor workflow      |
| [D-0004](0004-use-herdr-as-terminal-runtime.md)                          | Host threads in a dedicated Herdr server instead of tmux                 | Terminal runtime ownership and topology       |
| [D-0005](0005-track-checkpoint-through-native-successors.md)             | Track the checkpoint bookmark through jj's native successors             | Checkpoint bookmark and projection audit      |
| [D-0006](0006-close-repair-and-proof-gaps.md)                            | Close the repair, locking, and proof gaps found in the third review      | Repair plans, process safety, and proof gates |
| [D-0007](0007-use-portable-user-defined-profiles.md)                     | Let users define profiles and use them across machines                   | Remote access                                 |
| [D-0008](0008-keep-execution-and-remote-grants-on-the-host.md)           | Keep execution and remote grants on the thread’s host                    | Remote architecture                           |
| [D-0009](0009-operate-headless-with-a-configurable-automation-policy.md) | Operate fully headless, with a configurable automation policy            | Headless operation and unattended approval    |
| [D-0010](0010-define-headless-setup.md)                                  | Define headless setup and installation changes                           | Headless operation                            |
| [D-0011](0011-select-a-verified-recovery-successor.md)                   | Select a verified recovery successor by commit id                        | Headless operation                            |
| [D-0012](0012-submit-follow-up-prompts-as-user-turns.md)                 | Submit follow-up prompts as user turns                                   | Headless operation                            |
| [D-0013](0013-prove-admission-and-delivery.md) | Prove tool admission and message delivery | Reference book review |
| [D-0014](0014-prepare-dirty-checkpoints-separately.md) | Keep checkpoint previews read-only and end follows links on close | Reference book review |
| [D-0015](0015-create-only-bookmarks-and-preserve-revisions.md) | Create bookmarks only under free names and preserve revisions on destroy | Reference book review |

## Earlier design rationale

These notes predate the numbered log. They keep their published locations and
are not retroactively assigned dates, deciders, or acceptance claims. New
decisions can supersede a linked note or a specific part of it.

| Note                                                                                                                                                                                                                                                                                 | Topic                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------- |
| [Embedded cascade outbox](../../docs/reference/book/17-decisions/cascade-outbox.md)                                                                                                                                                                                                  | Reliable delivery             |
| [Native evolution and workspace materialization](../../docs/reference/book/17-decisions/native-evolution.md)                                                                                                                                                                         | jj reconciliation             |
| [Transcript anchoring](../../docs/reference/book/17-decisions/transcript-anchoring.md)                                                                                                                                                                                               | Transcript                    |
| [Thread head and lifecycle sagas](../../docs/reference/book/17-decisions/thread-head-and-sagas.md): tmux commitments superseded by [D-0004](0004-use-herdr-as-terminal-runtime.md); fixed bookmark target superseded by [D-0005](0005-track-checkpoint-through-native-successors.md) | Thread identity and lifecycle |
| [Codex as a second v1 harness](../../docs/reference/book/17-decisions/codex-adapter.md)                                                                                                                                                                                              | Harness integration           |
| [Rejected alternatives](../../docs/reference/book/17-decisions/rejected.md)                                                                                                                                                                                                          | Design boundaries             |
