#!/bin/bash
# Sauvegarde le travail du scratchpad dans .wip-d3/ puis commit + push sur D3.
# usage : save_wip.sh <SP> [message]   (verrou partagé : /tmp/d3_git.lock)
SP=$1; MSG=${2:-"D3 : sauvegarde automatique du chantier (brouillons et état)"}
R=/home/claude/bobmed; W=$R/.wip-d3
exec 9>/tmp/d3_git.lock; flock 9
cd $R || exit 1
mkdir -p $W/specs $W/fiches $W/blind
cp -u $SP/specs/*.json $W/specs/ 2>/dev/null
cp -u $SP/briefs/*.md $W/fiches/ 2>/dev/null
cp -u $SP/blind/* $W/blind/ 2>/dev/null
cp $SP/approved.txt $SP/audited.txt $W/ 2>/dev/null
python3 $W/outils/etat.py $SP > $W/ETAT.md 2>/dev/null
git add .wip-d3
git diff --cached --quiet && exit 0
git commit -q -m "$MSG

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
for i in 1 2 3 4; do git push -q origin D3 && exit 0; sleep $((2**i)); git pull -q --rebase origin D3; done
