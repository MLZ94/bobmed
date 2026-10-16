#!/bin/bash
# Publie des quiz audités : approved.txt, portails, validation, commit + push sur D3.
# usage : publish.sh <SP> "<message de commit>" <fichier d3/...html> [...]
SP=$1; MSG=$2; shift 2
R=/home/claude/bobmed
exec 9>/tmp/d3_git.lock; flock 9
cd $R || exit 1
for f in "$@"; do
  grep -qxF "$f" $SP/approved.txt || echo "$f" >> $SP/approved.txt
  sed -i "\#^$f\$#d" $SP/audited.txt 2>/dev/null
  python3 validate_quiz.py "$f" | tail -1 | grep -q '✓' || { echo "VALIDATE KO $f"; exit 1; }
  timeout 300 python3 test_quiz.py "$f" | tail -1 | grep -q '✓' || { echo "TEST KO $f"; exit 1; }
done
python3 $SP/gen_portals.py || exit 1
for p in d3/t1/index.html d3/t2/index.html d3/t3/index.html d3/t*/entrainement/index.html; do [ -f "$p" ] && { python3 validate_quiz.py "$p" >/dev/null 2>&1; true; }; done
mkdir -p .wip-d3/specs .wip-d3/fiches .wip-d3/blind
cp -u $SP/specs/*.json .wip-d3/specs/; cp -u $SP/briefs/*.md .wip-d3/fiches/ 2>/dev/null; cp -u $SP/blind/* .wip-d3/blind/ 2>/dev/null
cp $SP/approved.txt $SP/audited.txt .wip-d3/; python3 .wip-d3/outils/etat.py $SP > .wip-d3/ETAT.md
git add -f "$@"; git add d3/*/index.html d3/*/entrainement/index.html index.html .wip-d3 2>/dev/null
git commit -q -m "$MSG

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>" || exit 1
[ -n "$NOPUSH" ] && { git log --oneline -1; exit 0; }
for i in 1 2 3 4; do git push -q origin D3 && { git log --oneline -1; exit 0; }; sleep $((2**i)); git pull -q --rebase origin D3; done
exit 1
