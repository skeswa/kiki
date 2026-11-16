#!/bin/bash
# Extra jj 0.46.0 probes. Usage: extra.sh <workdir>   (disposable; logs to stdout)
set -u
W="$1"; mkdir -p "$W"; cd "$W"
export JJ_CONFIG="$W/cfg.toml"
printf '[user]\nname="Experiment"\nemail="experiment@example.invalid"\n[ui]\neditor="true"\ncolor="never"\npaginate="never"\n' > "$JJ_CONFIG"
r() { echo "\$ $*"; "$@" 2>&1 | sed 's/^/    /'; echo "    [exit ${PIPESTATUS[0]}]"; }
sec() { echo; echo "=================== $* ==================="; }
heads() { # print op heads dir listing (12-char prefixes) for a workspace
  local repo="$1/.jj/repo"; [ -f "$repo" ] && repo="$(cd "$1/.jj" && cd "$(cat repo)" && pwd)"
  echo "    op_heads($1): $(ls "$repo/op_heads/heads" | cut -c1-12 | tr '\n' ' ')"; }
BT='name ++ " -> " ++ if(conflict, "CONFLICTED ", "") ++ if(present, "", "ABSENT ") ++ added_targets.map(|c| c.change_id().short(8) ++ "/" ++ c.commit_id().short(8)).join(",") ++ " removed=[" ++ removed_targets.map(|c| c.commit_id().short(8)).join(",") ++ "]\n"'
LT='change_id.short(8) ++ "/" ++ commit_id.short(8) ++ " wc=" ++ working_copies ++ " bm=[" ++ bookmarks ++ "] div=" ++ divergent ++ " empty=" ++ empty ++ " " ++ description.first_line() ++ "\n"'
bm() { r jj -R "$1" --ignore-working-copy bookmark list -T "$BT"; r jj -R "$1" --ignore-working-copy log -G -r 'all() ~ root()' -T "$LT"; }
newrepo() { rm -rf "$W/$1"; jj git init "$W/$1" >/dev/null 2>&1; echo f1 > "$W/$1/f1"; echo f2 > "$W/$1/f2"; jj -R "$W/$1" describe -m base >/dev/null 2>&1; jj -R "$W/$1" bookmark create cp -r @ >/dev/null 2>&1; }

r jj --version

sec "A1 snapshot rewrite: bookmark on @ follows snapshot successor"
newrepo a1; bm a1
echo edit >> a1/f1
r jj -R a1 status
bm a1
r jj -R a1 evolog -G -r cp -T 'commit.commit_id().short(8) ++ " op=" ++ operation.id().short(8) ++ " preds=[" ++ predecessors.map(|c| c.commit_id().short(8)).join(",") ++ "] " ++ operation.description() ++ "\n"'

sec "A2 describe"
r jj -R a1 describe -m 'base described'; bm a1

sec "A3 jj new: bookmark stays behind"
r jj -R a1 new -m child; bm a1

sec "A4a squash child(@) into bookmarked parent"
echo childedit >> a1/f2
r jj -R a1 squash -u; bm a1

sec "A4b squash bookmarked @ into its parent (bookmark on source)"
newrepo a4; r jj -R a4 new -m top; echo t > a4/t; r jj -R a4 bookmark create topbm -r @; bm a4
r jj -R a4 squash -u; bm a4

sec "A5 rebase bookmarked commit"
newrepo a5; r jj -R a5 new 'root()' -m other; r jj -R a5 rebase -r cp -d @; bm a5

sec "A6a abandon bookmarked commit (default)"
newrepo a6; r jj -R a6 new -m top; r jj -R a6 abandon cp; bm a6
sec "A6b abandon --retain-bookmarks"
newrepo a6b; r jj -R a6b new -m top; r jj -R a6b abandon --retain-bookmarks cp; bm a6b
sec "A6c abandon bookmarked @ working copy commit itself (default)"
newrepo a6c; r jj -R a6c abandon @; bm a6c

sec "A7 split bookmarked @"
newrepo a7; r jj -R a7 split -m 'first half' f1; bm a7
sec "A7b split bookmarked non-@ commit"
newrepo a7b; r jj -R a7b new -m top; r jj -R a7b split -r cp -m 'first half' f1; bm a7b

sec "A8 divergence: two visible successors of bookmarked commit via concurrent ops"
newrepo a8; r jj -R a8 new -m top
BASE=$(jj -R a8 --ignore-working-copy op log -G -n1 -T 'id')
r jj -R a8 --at-op="$BASE" describe -r cp -m left
r jj -R a8 --at-op="$BASE" describe -r cp -m right
heads a8
r jj -R a8 --ignore-working-copy op log -G -n3 -T 'id.short(8) ++ " parents=" ++ parents.map(|p| p.id().short(8)).join(",") ++ " " ++ description ++ "\n"'
heads a8
bm a8
r jj -R a8 --ignore-working-copy log -G -r cp -T "$LT"
r jj -R a8 --ignore-working-copy log -G -r 'bookmarks(cp)' -T "$LT"

sec "A9 bookmark set backwards/sideways/delete are plain ops"
newrepo a9; r jj -R a9 new -m top; r jj -R a9 bookmark move cp --to @ ; r jj -R a9 bookmark delete cp; bm a9
r jj -R a9 op log -G -n3 -T 'id.short(8) ++ " " ++ description ++ "\n"'

sec "B dirty update-stale with bookmark on CHILD workspace @"
rm -rf b-parent b-child; jj git init b-parent >/dev/null 2>&1; echo base-v1 > b-parent/base.txt
jj -R b-parent describe -m parent >/dev/null 2>&1
r jj -R b-parent workspace add --name child -r @ "$W/b-child"
echo childwork > b-child/child.txt; r jj -R b-child describe -m child
r jj -R b-child bookmark create childcp -r @
bm b-parent
echo 'must preserve' > b-child/unsnap.txt
echo base-v2 > b-parent/base.txt; r jj -R b-parent status
heads b-parent
r jj -R b-child status
r jj -R b-child workspace update-stale
heads b-parent
ls b-child | sed 's/^/    ls b-child: /'
bm b-parent
r jj -R b-parent --ignore-working-copy log -G -r 'bookmarks(childcp)' -T "$LT"
CH=$(jj -R b-child --ignore-working-copy log -G -r @ -T 'change_id')
r jj -R b-parent --ignore-working-copy log -G -r "change_id($CH)" -T 'commit_id.short(8) ++ " offset=" ++ change_offset ++ " div=" ++ divergent ++ " conflict=" ++ conflict ++ " files=" ++ diff.files().map(|f| f.path()).join(",") ++ "\n"'
r jj -R b-parent --ignore-working-copy evolog -G -r "change_id($CH)" -T 'commit.commit_id().short(8) ++ " op=" ++ operation.id().short(8) ++ " preds=[" ++ predecessors.map(|c| c.commit_id().short(8)).join(",") ++ "] " ++ operation.description() ++ "\n"'
r jj -R b-parent --ignore-working-copy op log -G -n5 -T 'id.short(8) ++ " parents=" ++ parents.map(|p| p.id().short(8)).join(",") ++ " " ++ description ++ "\n"'
TOP=$(jj -R b-parent --ignore-working-copy op log -G -n1 -T 'id')
r jj -R b-parent --at-op="$TOP" op show --no-graph "$TOP"
r jj -R b-parent --at-op="$TOP" log -G -r 'working_copies()' -T "$LT"
r jj -R b-child status
bm b-parent

sec "C op DAG: which commands merge two heads"
mkfork() { rm -rf "$W/c" "$W/c-ws"; jj git init "$W/c" >/dev/null 2>&1; echo x > "$W/c/x"; jj -R "$W/c" describe -m c >/dev/null 2>&1
  jj -R "$W/c" workspace add --name ws2 "$W/c-ws" >/dev/null 2>&1
  CB=$(jj -R "$W/c" --ignore-working-copy op log -G -n1 -T 'id')
  jj -R "$W/c" --at-op="$CB" bookmark create left -r 'root()' >/dev/null 2>&1; jj -R "$W/c" --at-op="$CB" bookmark create right -r 'root()' >/dev/null 2>&1; }
try() { mkfork; echo "--- try: jj -R c $*"; heads c; r jj -R c "$@"; heads c; }
try --at-op=@ op log -G -n1 -T 'id.short(8) ++ "\n"'
try --at-op=@ --ignore-working-copy log -G -r @ -T 'commit_id.short(8) ++ "\n"'
H1=$(ls c/.jj/repo/op_heads/heads | head -1)
try --at-op="$H1" op log -G -n2 -T 'id.short(8) ++ "\n"'
try --at-op="$H1" log -G -r @ -T 'commit_id.short(8) ++ "\n"'
try --at-op="$H1" bookmark list
try --ignore-working-copy op log -G -n1 -T 'id.short(8) ++ "\n"'
try --ignore-working-copy log -G -r @ -T 'commit_id.short(8) ++ "\n"'
try --ignore-working-copy bookmark list
try --ignore-working-copy workspace list
try --ignore-working-copy workspace root
try op log -G -n1 -T 'id.short(8) ++ "\n"'
try status
try debug working-copy
try --ignore-working-copy debug working-copy
try debug local-working-copy
try version
try --ignore-working-copy config list user.name
try --ignore-working-copy util gc --help
try --ignore-working-copy op log -G -T 'id.short(8) ++ " parents=" ++ parents.map(|p| p.id().short(8)).join(",") ++ " " ++ description ++ "\n"'
echo "--- from added workspace"
mkfork; heads c; heads c-ws
echo "    c/.jj/repo is $(test -d c/.jj/repo && echo dir || echo file); c-ws/.jj/repo is $(test -d c-ws/.jj/repo && echo dir || echo "file containing: $(cat c-ws/.jj/repo)")"
ls c/.jj c/.jj/repo c/.jj/repo/op_heads c-ws/.jj 2>&1 | sed 's/^/    /'
r jj -R c-ws --at-op=@ --ignore-working-copy op log -G -n1
r jj -R c --at-op='@-' op log -G -n1 -T 'id.short(8) ++ "\n"'
heads c
echo "--- template keyword search for heads"
r jj -R c --at-op="$H1" op log -G -n1 -T 'self.heads()'
r jj -R c --at-op="$H1" op log -G -n1 -T 'current_operation ++ " root=" ++ root ++ " snapshot=" ++ snapshot ++ " ws=" ++ workspace_name ++ "\n"'
r jj -R c --at-op="$H1" debug object operation "$H1"
r jj -R c debug object --help
heads c

sec "D which read-only-looking commands snapshot / create ops"
dtry() { rm -rf "$W/d"; jj git init "$W/d" >/dev/null 2>&1; echo x > "$W/d/x"; jj -R "$W/d" describe -m d >/dev/null 2>&1; jj -R "$W/d" bookmark create cp -r @ >/dev/null 2>&1
  local before=$(ls "$W/d/.jj/repo/op_heads/heads"); local cb=$(jj -R "$W/d" --ignore-working-copy log -G -r @ -T commit_id)
  echo dirty >> "$W/d/x"; echo new > "$W/d/untracked"
  jj -R "$W/d" "$@" >/dev/null 2>"$W/d.err"; local rc=$?
  local after=$(ls "$W/d/.jj/repo/op_heads/heads"); local ca=$(jj -R "$W/d" --ignore-working-copy log -G -r @ -T commit_id)
  local desc=$(jj -R "$W/d" --ignore-working-copy op log -G -n1 -T description)
  printf '    %-55s exit=%s new_op=%s wc_commit_changed=%s last_op="%s"\n' "jj $*" "$rc" "$([ "$before" = "$after" ] && echo no || echo YES)" "$([ "$cb" = "$ca" ] && echo no || echo YES)" "$desc"; }
dtry status
dtry log
dtry diff
dtry show
dtry evolog
dtry op log
dtry op show
dtry bookmark list
dtry workspace list
dtry workspace root
dtry file list
dtry config list
dtry version
dtry debug working-copy
dtry debug local-working-copy
dtry --ignore-working-copy status
dtry --ignore-working-copy log
dtry --ignore-working-copy diff
dtry --ignore-working-copy op log
dtry --ignore-working-copy bookmark list
dtry --ignore-working-copy workspace list
dtry --at-op=@ status
dtry --at-op=@ log
dtry --at-op=@ diff
dtry --at-op=@ op log
dtry --config snapshot.auto-track='none()' status
echo "--- stale workspace: read commands"
stry() { rm -rf "$W/s" "$W/s-ws"; jj git init "$W/s" >/dev/null 2>&1; echo x > "$W/s/x"; jj -R "$W/s" describe -m s >/dev/null 2>&1
  jj -R "$W/s" workspace add --name ws2 -r @ "$W/s-ws" >/dev/null 2>&1; echo y >> "$W/s/x"; jj -R "$W/s" status >/dev/null 2>&1
  local before=$(ls "$W/s/.jj/repo/op_heads/heads")
  jj -R "$W/s-ws" "$@" >/dev/null 2>"$W/s.err"; local rc=$?
  local after=$(ls "$W/s/.jj/repo/op_heads/heads")
  printf '    %-45s exit=%s new_op=%s files_updated=%s err="%s"\n' "(stale ws) jj $*" "$rc" "$([ "$before" = "$after" ] && echo no || echo YES)" "$(grep -q y "$W/s-ws/x" && echo YES || echo no)" "$(head -1 "$W/s.err")"; }
stry status
stry log
stry op log
stry bookmark list
stry workspace list
stry --ignore-working-copy log
stry --at-op=@ log
stry workspace update-stale
stry debug working-copy

sec "E --no-integrate-operation / op integrate"
rm -rf e e-ws; jj git init e >/dev/null 2>&1; echo x > e/x; jj -R e describe -m e-parent >/dev/null 2>&1
jj -R e workspace add --name ws2 -r @ "$W/e-ws" >/dev/null 2>&1; echo c > e-ws/c; jj -R e-ws describe -m e-child >/dev/null 2>&1
r jj -R e new 'root()' -m newbase
heads e
r jj -R e --no-integrate-operation rebase -r 'description(exact:"e-child\n")' -d 'description(exact:"newbase\n")' --ignore-working-copy
heads e
r jj -R e --no-integrate-operation --ignore-working-copy describe -r @ -m planned
heads e
PLAN=$(jj -R e --no-integrate-operation --ignore-working-copy describe -r 'ws2@' -m planned-child 2>&1 | grep -oE 'requested: [0-9a-f]+' | cut -d' ' -f2)
echo "    PLAN=$PLAN"
r jj -R e --ignore-working-copy op log -G -n2 -T 'id.short(12) ++ " " ++ description ++ "\n"'
r jj -R e --at-op="$PLAN" log -G -r 'ws2@' -T "$LT"
r jj -R e --at-op="$PLAN" op log -G -n2 -T 'id.short(12) ++ " parents=" ++ parents.map(|p| p.id().short(8)).join(",") ++ " " ++ description ++ "\n"'
r jj -R e --no-integrate-operation status
echo intervening >> e/x; r jj -R e status
r jj -R e --ignore-working-copy op integrate "$PLAN"
heads e
r jj -R e --ignore-working-copy op log -G -n4 -T 'id.short(12) ++ " parents=" ++ parents.map(|p| p.id().short(8)).join(",") ++ " " ++ description ++ "\n"'
heads e
r jj -R e --ignore-working-copy op integrate "$PLAN"
r jj -R e-ws status
r jj -R e --ignore-working-copy op integrate deadbeef

sec "F added workspace .git, forget, root, list"
for mode in --no-colocate --colocate; do
  rm -rf f f-ws; r jj git init $mode f; echo x > f/x; jj -R f describe -m f >/dev/null 2>&1
  r jj -R f workspace add --name ws2 "$W/f-ws"
  ls -la f-ws | sed 's/^/    f-ws: /'
  [ -e f-ws/.git ] && { echo "    f-ws/.git type: $(test -d f-ws/.git && echo dir || echo file)"; [ -f f-ws/.git ] && sed 's/^/    .git content: /' f-ws/.git; }
  r git -C f-ws rev-parse --show-toplevel
  r git -C f worktree list
  r jj -R f workspace list
  r jj -R f workspace list -T 'name ++ " " ++ target.commit_id().short(8) ++ " root=" ++ root ++ "\n"'
  r jj -R f-ws workspace root
  r jj -R f workspace root --name ws2
  r jj -R f workspace forget ws2
  echo "    f-ws exists after forget: $(test -d f-ws && echo yes || echo no); .jj: $(test -d f-ws/.jj && echo yes || echo no); x: $(test -f f-ws/x && echo yes || echo no)"
  r jj -R f workspace list
  r jj -R f-ws workspace root
  r jj -R f workspace root --name ws2
  r jj -R f-ws status
  r jj -R f-ws --ignore-working-copy log -G -r @ -T "$LT"
  r git -C f worktree list
done
r jj workspace remove --help
