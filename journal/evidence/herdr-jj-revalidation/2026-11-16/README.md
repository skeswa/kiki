# jj 0.46.0 revalidation, 2026-11-16

Receipts for the jj half of the 2026-11-16 Herdr and jj revalidation. They
rerun the 2026-10-30 jj semantics probe on the repository's pinned jj and add
probes for bookmark movement, operation heads, snapshotting, staged
operations, and added workspaces.

## Run

- Recorded: 2026-11-16, local time zone UTC-05:00.
- Environment: macOS 26.5.1, Darwin 25.5.0, arm64.
- Executable: `jj 0.46.0-7d382314f9420b4b8d932245b49c99492c812b9f`, the
  `mise.toml` pin, at `~/.local/share/mise/installs/jj/0.46.0/jj`; SHA-256
  `fee2fd6a09f09b43b6cd501b75921b4234655801bb7636408a25796d3fb0e51a`.
- Isolation: disposable repositories in a scratch directory, a scratch
  `JJ_CONFIG`, and experiment author identity. No command ran in this
  repository.
- Exit outcome: every script exited 0. Individual command exits are in the
  captures.

Commands, with `jj` resolved to the executable above:

```sh
python3 jj_semantics.py --output-parent <scratch>/out > run046.json
bash probes/extra.sh <scratch>/out/extra > extra-results.txt
bash probes/extra2.sh <scratch>/out/extra > extra2-results.txt
bash probes/extra3.sh <scratch>/out/extra > extra3-results.txt
```

`jj_semantics.py` was an unmodified copy of the
[published probe](../../../../docs/public/research/herdr-jj/jj_semantics.py)
(SHA-256 `a4eac4207217b6cda0c798158c2f37b43f4290de388babf8a5a781ccb5719637`).
`extra2.sh` and `extra3.sh` reuse repositories that `extra.sh` leaves in the
same directory, so they run in that order.

## Files

| File | SHA-256 | Contents |
| --- | --- | --- |
| [run046.json](run046.json) | `be9933a436df203bbccda3fb7bcbfeeb4bd22d797f9b74d5990b153509384a67` | Output of the published probe on 0.46.0, for comparison with the [0.44.0 results](../../../../docs/public/research/herdr-jj/results.json) |
| [jj-0.46.0-probe-results.txt](jj-0.46.0-probe-results.txt) | `63ba73db4bce8d0d30de6cdcbf469eba94839c8cd6b4921c7dce449833ff59fb` | The three extra captures concatenated under a short header: each command, its output, and its exit status |
| [probes/extra.sh](probes/extra.sh) | `86567cc171b8a1d28fbe8b658234a3c852dc04878c0dc01b01d9bb57bad764aa` | Sections A–F |
| [probes/extra2.sh](probes/extra2.sh) | `8c85bb26cf7e6e3e80b54f33c638a55d61023295022ac1ed8203cc6fa5aaf0a3` | Split, divergence, exact-operation reads with two and three heads |
| [probes/extra3.sh](probes/extra3.sh) | `a2a7b5d031a8fd536197bf5d6b8e08540d583f01ae517f6cf315a3e41e752dc4` | Predecessor records, `update-stale` operations, `--at-op=@` snapshotting |

The local machine's host name was replaced with the literal `host` in
`jj-0.46.0-probe-results.txt` (five `user@host` strings in `jj op show`
output) before the capture was retained. Nothing else was altered: scratch
paths, ids, timestamps, and all other bytes are as captured. `run046.json` and
the probe scripts did not contain the host name and are byte-identical to the
originals. The disposable repositories and the per-command log of the
published probe were not retained.

## Measurements

- The published probe's assertions all pass on 0.46.0. One recorded value
  changed: in a colocated repository an added workspace now has a `.git`
  worktree file and `git rev-parse` succeeds there (0.44.0: no `.git`, exit
  128). `git.colocate` defaults to `true`.
- A bookmark follows the commit it names through snapshot, `describe`,
  `rebase`, squash into it, and an ancestor rewrite from another workspace. It
  stays behind on `jj new` and `jj commit`. `jj split` and squashing the
  bookmarked commit into its parent move it to a different change id.
  `jj abandon` deletes it. Divergent successors leave it conflicted, and it
  stays conflicted with one target after one side is abandoned.
- A dirty `jj workspace update-stale` exits 0, removes the unsnapshotted file
  from disk, keeps it only in the other divergent successor, and conflicts a
  bookmark on that commit. `evolog` at an exact operation names each commit's
  operation and predecessors.
- With several operation heads, `--at-op=@` fails and changes nothing;
  `--at-op=<head id>` reads change nothing; every repository-loading command
  without `--at-op` merges the heads, with or without
  `--ignore-working-copy`. No flag, template method, or `jj debug` subcommand
  lists all heads. Head files are in `<main>/.jj/repo/op_heads/heads/`; an
  added workspace's `.jj/repo` is a pointer file.
- `status`, `log`, `diff`, `show`, `evolog`, `op log`, `op show`,
  `bookmark list`, `workspace list`, and `file list` snapshot a dirty working
  copy. `--ignore-working-copy` prevents it. `--at-op=@` alone does not.
- A clean `update-stale` leaves the head set unchanged in a non-colocated
  repository and writes a "reset git head" operation in a colocated one.
- `--no-integrate-operation` leaves the frontier unchanged; `jj op integrate`
  after an intervening operation writes a merge operation.
- `jj workspace forget` leaves the directory and its `.jj`, and removes the
  Git worktree in a colocated repository.

## Limits

- Concurrent heads were produced from historical `--at-op` views, not a timing
  race. Directory listing during a head swap was not tested.
- In `extra.sh`, the `--at-op=<id>` attempts in section C used an id from an
  earlier fixture and section A7 used a path jj rejected. `extra2.sh` sections
  C2 and A7 are the valid runs; the header of the results file says so.
- `extra.sh` repositories use the colocated default; `extra2.sh` and
  `extra3.sh` use `--no-colocate` unless a section says otherwise.
- Not tested: `--at-op=@` snapshotting on 0.44.0; predecessor records for
  operations written by older jj or after `jj op abandon`; bookmark movement
  through `jj undo`, `jj op restore`, fetch, or Git-side ref edits;
  `experimental-advance-branches`; `jj workspace remove`; staged operations
  with conflicts or crashes; filesystem-watch behavior on the head store.
