# Research evidence

Keep compact receipts and measurements under `journal/evidence/<topic>/<run>/`.
Use a dated run name and link each run from its investigation. Record the
command, time, environment, source and executable versions, exit outcome, and
the measurements needed to assess the finding. Include hashes when a claim
depends on exact bytes.

Retained evidence keeps its original bytes, dates, and paths inside captures.
Do not hand-edit or reformat results to fit a later conclusion. A correction
or new run gets a separate record that explains what changed. Keep verbose
logs and disposable outputs in scratch; retain only what supports the finding.
Do not store credentials or private environment files.

## Existing Herdr evidence

These captures remain at their published download paths. Their source checkout
and tested executable were different revisions; read the investigation before
drawing a compatibility conclusion. A new run must not overwrite these files.

| Recorded | Evidence | Investigation |
| --- | --- | --- |
| 2026-10-30 | [jj semantics and Herdr smoke results](../../docs/public/research/herdr-jj/results.json) | [Herdr and jj](../../docs/research/herdr-jj.md) |
| 2026-10-30 | [Herdr and tmux lifecycle results](../../docs/public/research/herdr-runtime/results.json) | [Terminal runtime](../../docs/research/herdr-terminal-runtime.md) |

The [research tools index](../tools/README.md) links the corresponding probes.

## Runs

| Recorded | Evidence | Investigation |
| --- | --- | --- |
| 2026-11-16 | [jj 0.46.0 revalidation: probe rerun and bookmark, operation-head, and snapshot probes](herdr-jj-revalidation/2026-11-16/README.md) | [2026-11-16 Herdr and jj revalidation](../investigations/2026/2026-11-16-herdr-jj-revalidation.md) |
