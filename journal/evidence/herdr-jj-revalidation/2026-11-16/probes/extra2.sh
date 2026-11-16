#!/bin/bash
set -u
W="$1"; cd "$W"
export JJ_CONFIG="$W/cfg.toml"
r() { echo "\$ $*"; "$@" 2>&1 | sed 's/^/    /'; echo "    [exit ${PIPESTATUS[0]}]"; }
sec() { echo; echo "=================== $* ==================="; }
heads() { echo "    op_heads($1): $(ls "$1/.jj/repo/op_heads/heads" | cut -c1-12 | tr '\n' ' ')"; }
BT='name ++ if(remote, "@" ++ remote, "") ++ " -> " ++ if(conflict, "CONFLICTED ", "") ++ added_targets.map(|c| c.change_id().short(8) ++ "/" ++ c.commit_id().short(8)).join(",") ++ " removed=[" ++ removed_targets.map(|c| c.commit_id().short(8)).join(",") ++ "]\n"'
LT='change_id.short(8) ++ "/" ++ commit_id.short(8) ++ " wc=" ++ working_copies ++ " bm=[" ++ local_bookmarks ++ "] div=" ++ divergent ++ " empty=" ++ empty ++ " " ++ description.first_line() ++ "\n"'
bm() { r jj -R "$1" --ignore-working-copy bookmark list -T "$BT"; r jj -R "$1" --ignore-working-copy log -G -r 'all() ~ root()' -T "$LT"; }
newrepo() { rm -rf "$W/$1"; jj git init --no-colocate "$W/$1" >/dev/null 2>&1; echo f1 > "$W/$1/f1"; echo f2 > "$W/$1/f2"; jj -R "$W/$1" describe -m base >/dev/null 2>&1; jj -R "$W/$1" bookmark create cp -r @ >/dev/null 2>&1; }
r jj config list --include-defaults git.colocate
r bash -c 'jj config list --include-defaults | grep -iE "advance|split\.|auto-update-stale|bookmark" '

sec "A7 split bookmarked @ (root: fileset)"
newrepo a7; bm a7; r jj -R a7 split -m 'first half' root:f1; bm a7
sec "A7b split bookmarked non-@ commit"
newrepo a7b; r jj -R a7b new -m top; r jj -R a7b split -r cp -m 'first half' root:f1; bm a7b
sec "A7c split --parallel bookmarked @"
newrepo a7c; r jj -R a7c split --parallel -m 'first half' root:f1; bm a7c
sec "A10 jj commit / jj edit / jj prev with bookmark on @"
newrepo a10; r jj -R a10 commit -m committed; bm a10
r jj -R a10 new 'root()' -m elsewhere; bm a10
sec "A11 abandon one divergent side resolves conflicted bookmark?"
newrepo a11; r jj -R a11 new -m top
BASE=$(jj -R a11 --ignore-working-copy op log -G -n1 -T 'id')
jj -R a11 --at-op="$BASE" describe -r cp -m left >/dev/null 2>&1; jj -R a11 --at-op="$BASE" describe -r cp -m right >/dev/null 2>&1
bm a11
RIGHT=$(jj -R a11 --ignore-working-copy log -G -r 'description(exact:"right\n")' -T commit_id)
r jj -R a11 --ignore-working-copy abandon "$RIGHT"; bm a11
sec "A12 bookmark on child ws @, ancestor rewritten from parent ws (clean child)"
rm -rf p q; jj git init --no-colocate p >/dev/null 2>&1; echo v1 > p/base; jj -R p describe -m parent >/dev/null 2>&1
jj -R p workspace add --name child -r @ "$W/q" >/dev/null 2>&1; echo c > q/c; jj -R q describe -m child >/dev/null 2>&1; jj -R q bookmark create childcp -r @ >/dev/null 2>&1
bm p; echo v2 > p/base; r jj -R p status; bm p
r jj -R p --ignore-working-copy evolog -G -r childcp -n2 -T 'commit.commit_id().short(8) ++ " op=" ++ operation.id().short(8) ++ " preds=[" ++ predecessors.map(|c| c.commit_id().short(8)).join(",") ++ "] " ++ operation.description() ++ "\n"'
OPID=$(jj -R p --ignore-working-copy op log -G -n1 -T id)
r jj -R p --at-op="$OPID" op show --no-graph "$OPID"
r jj -R q --at-op="$OPID" log -r @ --no-graph -T 'change_id ++ " " ++ commit_id ++ "\n"'
r jj -R q --at-op=@ --ignore-working-copy log -r @ --no-graph -T 'change_id.short(8) ++ " " ++ commit_id.short(8) ++ "\n"'

sec "B2 inspect dirty-stale reconcile op in existing b-parent"
RO=$(jj -R b-parent --ignore-working-copy op log -G -T 'if(description.contains("reconcile"), id ++ "\n")' | head -1)
r jj -R b-parent --at-op="$RO" op show --no-graph "$RO"
r jj -R b-parent --at-op="$RO" op log -G -n1 -T 'id.short(8) ++ " parents=" ++ parents.map(|p| p.id().short(8)).join(",") ++ " snapshot=" ++ snapshot ++ " tags=" ++ tags ++ "\n"'

sec "C2 --at-op=<head id> with two/three heads"
mkfork() { rm -rf "$W/c" "$W/c-ws"; jj git init --no-colocate "$W/c" >/dev/null 2>&1; echo x > "$W/c/x"; jj -R "$W/c" describe -m c >/dev/null 2>&1
  jj -R "$W/c" workspace add --name ws2 "$W/c-ws" >/dev/null 2>&1
  CB=$(jj -R "$W/c" --ignore-working-copy op log -G -n1 -T 'id')
  for n in "$@"; do jj -R "$W/c" --at-op="$CB" bookmark create $n -r 'root()' >/dev/null 2>&1; done
  H1=$(ls "$W/c/.jj/repo/op_heads/heads" | head -1); }
try() { echo "--- try: $*"; heads c; r jj -R c "$@"; heads c; }
mkfork left right; echo dirty >> c/x
try --at-op="$H1" op log -G -n2 -T 'id.short(8) ++ " parents=" ++ parents.map(|p| p.id().short(8)).join(",") ++ " " ++ description ++ "\n"'
try --at-op="$H1" log -G -r @ -T 'commit_id.short(8) ++ "\n"'
try --at-op="$H1" bookmark list
try --at-op="$H1" workspace list
try --at-op="$H1" status
try --at-op="$H1" debug object operation "$H1"
try --at-op="$H1" op log -G -n1 -T 'self.heads()'
try --at-op="$H1" --ignore-working-copy bookmark create viaold -r 'root()'
mkfork left right third
try --at-op=@ --ignore-working-copy op log -G -n1
r bash -c 'jj -R c --at-op=@ --ignore-working-copy op log -G -n1 2>&1 | grep -oE "[0-9a-f]{12}" | sort | tr "\n" " "; echo; ls c/.jj/repo/op_heads/heads | cut -c1-12 | sort | tr "\n" " "'
try --at-op='@-' --ignore-working-copy op log -G -n1
try --ignore-working-copy op log -G -n2 -T 'id.short(8) ++ " parents=" ++ parents.map(|p| p.id().short(8)).join(",") ++ " " ++ description ++ "\n"'
echo "--- op heads dir layout"
r find c/.jj/repo/op_heads -maxdepth 2
r cat c/.jj/repo/op_heads/type
r find c-ws/.jj -maxdepth 2
r cat c-ws/.jj/repo
r jj -R c-ws --ignore-working-copy debug working-copy
