#!/usr/bin/env bash
# Paso 0 de M8 (K-04, P9 y P11). Uso: bash stash_merge_tree.sh
# Crea un repo temporal y comprueba:
#  P9a  `git stash create` no cambia el árbol, el índice ni la lista de stashes (modificados, en el índice y sin seguimiento);
#  P9b  el commit de `stash create` no incluye los ficheros sin seguimiento;
#  P9c  alternativa con GIT_INDEX_FILE aparte: incluye los sin seguimiento y tampoco toca nada;
#  P11  `git merge-tree --write-tree --name-only` da los ficheros en conflicto (cambios incompatibles) y sale limpio con cambios compatibles.
# No toca nada fuera del directorio temporal. Imprime OK/FALLO por comprobación.
set -u
fallos=0
ok() { echo "OK    $1"; }
ko() { echo "FALLO $1"; fallos=$((fallos + 1)); }
git --version
case $(git version | sed 's/[^0-9.]*\([0-9]*\)\.\([0-9]*\).*/\1 \2/') in
  2\ 3[89]*|2\ [4-9][0-9]*|[3-9]*) ok "Git >= 2.38 (merge-tree --write-tree)" ;;
  *) ko "Git < 2.38: merge-tree --write-tree no existe" ;;
esac

t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
cd "$t" && git init -q -b main r && cd r
git config user.email p@e.st; git config user.name prueba; git config core.autocrlf false
printf 'uno\ndos\ntres\n' > f1.txt; printf 'a\nb\n' > f2.txt; printf 'x\n' > f3.txt; printf '*.log\n' > .gitignore
git add . && git commit -qm base

# Estado sucio: f1 modificado sin añadir, f2 modificado y añadido, n.txt nuevo y añadido, u.txt sin seguimiento, ignorado.log ignorado
printf 'uno\nDOS\ntres\n' > f1.txt
printf 'a\nB\n' > f2.txt; git add f2.txt
printf 'nuevo\n' > n.txt; git add n.txt
printf 'sin seguimiento\n' > u.txt
printf 'ruido\n' > ignorado.log

foto() {  # estado observable: status, índice, contenido del árbol, stashes, HEAD
  { git status --porcelain=v1 --untracked-files=all
    echo "--indice"; git ls-files -s
    echo "--arbol"; for f in f1.txt f2.txt f3.txt n.txt u.txt ignorado.log; do printf '%s ' "$f"; git hash-object "$f"; done
    echo "--stash"; git stash list
    echo "--head"; git rev-parse HEAD; } 2>&1
}
antes=$(foto)

s=$(git stash create)
[ -n "$s" ] && ok "stash create devuelve un commit ($s)" || ko "stash create no devuelve nada"
[ "$(foto)" = "$antes" ] && ok "P9a: árbol, índice, stashes y HEAD idénticos tras stash create" || { ko "P9a: algo cambió tras stash create"; diff <(echo "$antes") <(foto); }
git cat-file -e "$s:f1.txt" && [ "$(git show "$s:f1.txt" | sed -n 2p)" = DOS ] && ok "el commit lleva el cambio sin añadir de f1" || ko "el commit no lleva el cambio de f1"
git cat-file -e "$s:n.txt" 2>/dev/null && ok "el commit lleva n.txt (añadido)" || ko "el commit no lleva n.txt"
git cat-file -e "$s:u.txt" 2>/dev/null && ko "P9b: el commit lleva u.txt (no se esperaba)" || ok "P9b: el commit NO lleva u.txt (sin seguimiento), como dice la doc"

# P9c: índice temporal para incluir los sin seguimiento (respeta .gitignore)
gd=$(git rev-parse --git-dir)
cp "$gd/index" "$t/indice"
w=$(GIT_INDEX_FILE="$t/indice" sh -c 'git add -A && git write-tree')
c=$(git commit-tree "$w" -p HEAD -m wip)
[ "$(foto)" = "$antes" ] && ok "P9c: nada cambia con GIT_INDEX_FILE aparte" || { ko "P9c: algo cambió"; diff <(echo "$antes") <(foto); }
git cat-file -e "$c:u.txt" 2>/dev/null && ok "P9c: el commit lleva u.txt" || ko "P9c: el commit no lleva u.txt"
git cat-file -e "$c:ignorado.log" 2>/dev/null && ko "P9c: lleva el ignorado" || ok "P9c: no lleva ignorado.log"

# P11: merge-tree por pares
git checkout -q -b izq main 2>/dev/null || true
git stash -q -u && git checkout -q main
git checkout -q -b A main; printf 'uno\nDOS-A\ntres\n' > f1.txt; git commit -qam A
git checkout -q -b B main; printf 'uno\nDOS-B\ntres\n' > f1.txt; git commit -qam B
git checkout -q -b C main; printf 'a\nb\nc\n' > f2.txt; git commit -qam C
salida=$(git merge-tree --write-tree --name-only --no-messages A B); rc=$?
[ $rc -eq 1 ] && printf '%s\n' "$salida" | sed -n 2p | grep -qx f1.txt && ok "P11: A×B en conflicto en f1.txt (rc=1)" || ko "P11: A×B rc=$rc «$salida»"
salida=$(git merge-tree --write-tree --name-only --no-messages A C); rc=$?
[ $rc -eq 0 ] && ok "P11: A×C sin conflicto (rc=0)" || ko "P11: A×C rc=$rc «$salida»"
antes2=$(git status --porcelain; git rev-parse HEAD)
git merge-tree --write-tree A B >/dev/null
[ "$(git status --porcelain; git rev-parse HEAD)" = "$antes2" ] && ok "merge-tree no toca árbol ni HEAD" || ko "merge-tree cambió algo"

echo "Fallos: $fallos"
exit $fallos
