# Research tools

Keep maintained tools that answer recurring research questions under
`journal/tools/<topic>/`. Give each tool an index entry linking its purpose,
inputs, supported environment, and investigation. One-off scripts belong in
scratch. If a tool becomes part of normal development or product behavior,
move it into the appropriate maintained code rather than growing a parallel
implementation here.

## Existing reproduction probes

The published 2026-10-30 probes retain their original paths. They reproduce
bounded experiments and do not establish kiki's acceptance guarantees. Check
their source and investigation for versions, side effects, and cleanup before
running them from the repository root.

| Probe                                                                              | Purpose                                                                           | Investigation                                                     |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [jj semantics](../../docs/public/research/herdr-jj/jj_semantics.py)                | Native evolution, stale workspaces, bookmarks, and operation views with jj 0.44.0 | [Herdr and jj](../../docs/research/herdr-jj.md)                   |
| [Herdr smoke](../../docs/public/research/herdr-jj/herdr_smoke.py)                  | Host a jj-only directory in an isolated Herdr server                              | [Herdr and jj](../../docs/research/herdr-jj.md)                   |
| [Herdr lifecycle](../../docs/public/research/herdr-runtime/herdr_runtime_probe.py) | Direct launch, restore, close, and server death                                   | [Terminal runtime](../../docs/research/herdr-terminal-runtime.md) |
| [tmux lifecycle](../../docs/public/research/herdr-runtime/tmux_runtime_probe.py)   | Compare terminal lifecycle behavior                                               | [Terminal runtime](../../docs/research/herdr-terminal-runtime.md) |
| [tmux orphan probe](../../docs/public/research/herdr-runtime/tmux_orphan_probe.py) | Observe HUP-ignoring fixture processes after server exit                          | [Terminal runtime](../../docs/research/herdr-terminal-runtime.md) |

These probes create disposable repositories or terminal sessions and retain
output in temporary directories. The terminal probes stop their own servers
and fixture processes. Pass an explicit executable with `--herdr` where
required; consult the reports for complete commands. Recorded results are
indexed under [evidence](../evidence/README.md).
