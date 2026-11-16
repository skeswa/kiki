#!/usr/bin/env python3
"""Disposable jj 0.44 experiments; no source/global configuration mutations."""
import argparse, json, os, pathlib, subprocess, tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-parent', type=pathlib.Path, default=pathlib.Path(tempfile.gettempdir()),
                    help='Existing directory for a new disposable jj-experiment-* directory')
options = parser.parse_args()
ROOT = pathlib.Path(tempfile.mkdtemp(prefix='jj-experiment-', dir=options.output_parent))
(ROOT / 'empty.toml').write_text('')
ENV = dict(os.environ, JJ_CONFIG=str(ROOT / 'empty.toml'))
LOG = []
RESULT = {'root': str(ROOT)}

def run(workspace, *args, ok=True):
    cmd = ['jj', '--no-pager', '--color=never', '--config=user.name=Experiment',
           '--config=user.email=experiment@example.invalid']
    if workspace:
        cmd += ['-R', str(workspace)]
    cmd += list(args)
    p = subprocess.run(cmd, env=ENV, text=True, capture_output=True, cwd=ROOT)
    LOG.append({'argv': cmd, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
    (ROOT / 'commands.json').write_text(json.dumps(LOG, indent=2))
    if ok and p.returncode:
        raise RuntimeError(json.dumps(LOG[-1]))
    return p

def ids(ws, rev='@'):
    return run(ws, '--at-op=@', '--ignore-working-copy', 'log', '-G', '-r', rev,
               '-T', 'change_id ++ " " ++ commit_id ++ "\\n"').stdout.strip().split()

def frontier(ws):
    repo = ws / '.jj' / 'repo'
    if repo.is_file():
        repo = (repo.parent / repo.read_text().strip()).resolve()
    # 0.44.0 uses op_heads/heads/<id>; older versions used op_heads/<id>.
    heads = repo / 'op_heads' / 'heads'
    if not heads.is_dir():
        heads = repo / 'op_heads'
    result = sorted(p.name for p in heads.iterdir() if p.is_file() and len(p.name) == 128)
    assert result, str(heads)
    return result

def fixture(name, colocated=False):
    a, b = ROOT / (name + '-parent'), ROOT / (name + '-child')
    run(None, 'git', 'init', '--colocate' if colocated else '--no-colocate', str(a))
    (a / 'base.txt').write_text('base-v1\n')
    run(a, 'describe', '-m', name + ' parent')
    run(a, 'bookmark', 'create', 'checkpoint', '-r', '@')
    run(a, 'workspace', 'add', '--name', 'child', '-r', '@', str(b))
    (b / 'child.txt').write_text('child work\n')
    run(b, 'describe', '-m', name + ' child')
    return a, b

RESULT['version'] = run(None, '--version').stdout.strip()
a, b = fixture('native')
old_parent, old_child = ids(a), ids(b)
before_heads = frontier(a)
(a / 'base.txt').write_text('base-v2\n')
run(a, 'status')
new_parent, new_child = ids(a), ids(b)
assert old_parent[0] == new_parent[0] and old_parent[1] != new_parent[1]
assert old_child[0] == new_child[0] and old_child[1] != new_child[1]
assert (b / 'base.txt').read_text() == 'base-v1\n'
stale_heads = frontier(a)
stale_status = run(b, 'status', ok=False)
assert frontier(a) == stale_heads
run(b, 'workspace', 'update-stale')
assert (b / 'base.txt').read_text() == 'base-v2\n'
assert frontier(a) == stale_heads
RESULT['native_rewrite'] = {'old_parent': old_parent, 'new_parent': new_parent,
    'old_child': old_child, 'new_child': new_child,
    'stale_status_exit': stale_status.returncode, 'stale_status_stderr': stale_status.stderr,
    'update_stale_op_heads_unchanged': True, 'op_heads': stale_heads,
    'parent_dot_git_exists': (a / '.git').exists(), 'child_dot_git_exists': (b / '.git').exists()}

# New revision advances live @; checkpoint and child parent stay behind.
run(a, 'new', '-m', 'parent advance')
advance_parent, after_advance_child = ids(a), ids(b)
checkpoint = ids(a, 'checkpoint')
assert advance_parent[0] != new_parent[0] and checkpoint == new_parent
assert after_advance_child == new_child
ancestor = run(a, '--at-op=@', 'log', '-G', '-r',
    'commit_id(' + advance_parent[1] + ') & ::child@', '-T', 'commit_id').stdout
assert ancestor == ''
run(b, '--ignore-working-copy', 'rebase', '-r', 'commit_id(' + new_child[1] + ')',
    '--onto', 'commit_id(' + advance_parent[1] + ')')
rebased_child = ids(b)
assert rebased_child[0] == new_child[0] and rebased_child[1] != new_child[1]
run(b, 'workspace', 'update-stale')
RESULT['head_advance'] = {'parent_head': advance_parent, 'checkpoint': checkpoint,
    'child_unchanged_until_explicit_rebase': True, 'child_after_rebase': rebased_child}

# Ordinary read command snapshots; exact-operation inspection does not.
snap_before = ids(b)
(b / 'unsnapshotted.txt').write_text('pending local edit\n')
assert ids(b) == snap_before
snapshot_heads = frontier(a)
run(b, 'status')
snap_after = ids(b)
assert snap_before[0] == snap_after[0] and snap_before[1] != snap_after[1]
assert frontier(a) != snapshot_heads
RESULT['read_snapshot'] = {'before': snap_before, 'after_status': snap_after}

# Dirty stale workspace behavior is deliberately observed, not presumed safe.
c, d = fixture('dirty')
dirty_old = ids(d)
(d / 'unsnapshotted.txt').write_text('must preserve this edit\n')
(c / 'base.txt').write_text('base-v2\n')
run(c, 'status')
dirty_evolved = ids(d)
dirty_update = run(d, 'workspace', 'update-stale', ok=False)
dirty_successors = run(c, '--at-op=@', 'log', '-G', '-r', 'change_id(' + dirty_old[0] + ')',
    '-T', 'commit_id ++ " " ++ divergent ++ " " ++ conflict ++ "\\n"')
RESULT['dirty_stale'] = {'old_child': dirty_old, 'evolved_child': dirty_evolved,
    'update_exit': dirty_update.returncode, 'update_stderr': dirty_update.stderr,
    'edit_remains_on_disk': (d / 'unsnapshotted.txt').exists(),
    'visible_successors': dirty_successors.stdout}
preserved = []
for row in dirty_successors.stdout.splitlines():
    commit = row.split()[0]
    # Filesets use workspace-root-relative syntax because cwd is outside workspace.
    contents = run(c, '--at-op=@', 'file', 'show', '-r', 'commit_id(' + commit + ')',
        'root:unsnapshotted.txt', ok=False)
    if contents.returncode == 0 and contents.stdout == 'must preserve this edit\n':
        preserved.append(commit)
assert preserved
RESULT['dirty_stale']['successors_preserving_edit'] = preserved

# Historical mutations simulate concurrent operations from the same starting op.
e, f = fixture('dag')
fork_base = frontier(e)[0]
run(e, '--at-op=' + fork_base, 'bookmark', 'create', 'left', '-r', '@')
run(e, '--at-op=' + fork_base, 'bookmark', 'create', 'right', '-r', '@')
fork_heads = frontier(e)
assert len(fork_heads) == 2
ambiguous_read = run(e, '--at-op=@', '--ignore-working-copy', 'op', 'log', '-G', '-n', '1', ok=False)
assert ambiguous_read.returncode != 0
run(e, '--ignore-working-copy', 'op', 'log', '-G', '-n', '1', '-T', 'id ++ "\\n"')
merged_heads = frontier(e)
assert len(merged_heads) == 1
op_dag = run(e, '--at-op=' + merged_heads[0], 'op', 'log', '-G', '-n', '4',
    '-T', 'id ++ " " ++ parents.map(|p| p.id()).join(" ") ++ "\\n"').stdout
assert fork_heads[0] in op_dag and fork_heads[1] in op_dag
RESULT['operation_dag'] = {'base': fork_base, 'fork_heads': fork_heads,
    'ambiguous_read_stderr': ambiguous_read.stderr, 'merged_heads': merged_heads,
    'operation_and_parents': op_dag}

# Metadata-only proof: a planned describe remains outside frontier until integration.
# This does not prove planned rebases, conflict handling, concurrent integration,
# workspace cleanliness, or crash recovery.
plan_heads = frontier(e)
planned = run(e, '--at-op=' + plan_heads[0], '--no-integrate-operation',
    'describe', '-r', '@', '-m', 'planned metadata change')
assert frontier(e) == plan_heads
import re
planned_ids = re.findall(r'requested: ([0-9a-f]+)', planned.stderr + planned.stdout)
assert planned_ids, planned.stderr
planned_id = planned_ids[-1]
run(e, '--at-op=' + planned_id, 'log', '-G', '-r', '@', '-T', 'description')
run(e, '--ignore-working-copy', 'op', 'integrate', planned_id)
assert frontier(e) != plan_heads
RESULT['planned_operation'] = {'unintegrated_id': planned_id, 'output': planned.stderr,
    'frontier_unchanged_until_integration': True}

g, h = fixture('colocated', colocated=True)
git_child = subprocess.run(['git', '-C', str(h), 'rev-parse', '--show-toplevel'],
    text=True, capture_output=True, env=ENV)
RESULT['colocated'] = {'main_dot_git_exists': (g / '.git').exists(),
    'added_workspace_dot_git_exists': (h / '.git').exists(),
    'git_in_added_workspace_exit': git_child.returncode, 'git_stderr': git_child.stderr}
(ROOT / 'results.json').write_text(json.dumps(RESULT, indent=2))
print(json.dumps(RESULT, indent=2))
