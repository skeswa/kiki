#!/bin/bash
set -u
W="$1"; cd "$W"
export JJ_CONFIG="$W/cfg.toml"
r() { echo "\$ $*"; "$@" 2>&1 | sed 's/^/    /'; echo "    [exit ${PIPESTATUS[0]}]"; }
sec() { echo; echo "=================== $* ==================="; }
ET='commit.change_id().short(8) ++ "/" ++ commit.commit_id().short(8) ++ " op=" ++ operation.id().short(8) ++ " preds=[" ++ predecessors.map(|c| c.change_id().short(8) ++ "/" ++ c.commit_id().short(8)).join(",") ++ "] " ++ operation.description() ++ "\n"'
sec "G1 evolog/predecessors after split (existing a7) and squash-source (existing a4)"
r jj -R a7 --ignore-working-copy evolog -G -r cp -n2 -T "$ET"
r jj -R a7 --ignore-working-copy evolog -G -r 'cp-' -n2 -T "$ET"
r jj -R a4 --ignore-working-copy evolog -G -r cp -n3 -T "$ET"
OP=$(jj -R a7 --ignore-working-copy op log -G -n1 -T id)
r bash -c "jj -R a7 --at-op=$OP debug object operation $OP | sed -n '/commit_predecessors/,\$p'"
r jj -R a7 --at-op="$OP" op show --no-graph "$OP"
sec "G2 clean update-stale: new op? colocated vs not"
for mode in --no-colocate --colocate; do
  rm -rf s s-ws; jj git init $mode s >/dev/null 2>&1; echo x > s/x; jj -R s describe -m s >/dev/null 2>&1
  jj -R s workspace add --name ws2 -r @ "$W/s-ws" >/dev/null 2>&1; echo c > s-ws/c; jj -R s-ws describe -m child >/dev/null 2>&1
  echo y >> s/x; jj -R s status >/dev/null 2>&1
  echo "    mode=$mode heads before: $(ls s/.jj/repo/op_heads/heads | cut -c1-12 | tr '\n' ' ')"
  r jj -R s-ws workspace update-stale
  echo "    mode=$mode heads after:  $(ls s/.jj/repo/op_heads/heads | cut -c1-12 | tr '\n' ' ')"
  r jj -R s --ignore-working-copy op log -G -n2 -T 'id.short(12) ++ " " ++ description ++ "\n"'
done
sec "G3 --at-op=@ snapshots? (single head, dirty wc)"
rm -rf g; jj git init --no-colocate g >/dev/null 2>&1; echo x > g/x; jj -R g describe -m g >/dev/null 2>&1
echo dirty >> g/x
for flags in "--at-op=@" "--at-op=@ --ignore-working-copy"; do
  echo "    before: $(ls g/.jj/repo/op_heads/heads | cut -c1-12)"
  r jj -R g $flags log -G -r @ -T 'commit_id.short(8) ++ "\n"'
  echo "    after:  $(ls g/.jj/repo/op_heads/heads | cut -c1-12)"
  echo dirty2 >> g/x
done
FULL=$(ls g/.jj/repo/op_heads/heads)
echo "    before: $(ls g/.jj/repo/op_heads/heads | cut -c1-12)"
r jj -R g --at-op="$FULL" log -G -r @ -T 'commit_id.short(8) ++ "\n"'
echo "    after:  $(ls g/.jj/repo/op_heads/heads | cut -c1-12)"
sec "G4 non-snapshotting checkpoint: bookmark set with --ignore-working-copy on dirty workspace, then snapshot"
r jj -R g --ignore-working-copy bookmark create cp -r @
r jj -R g --ignore-working-copy bookmark list
r jj -R g status
r jj -R g --ignore-working-copy bookmark list
