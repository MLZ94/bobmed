#!/bin/bash
# Remet en place le chantier D3 dans un nouveau scratchpad à partir de .wip-d3/ (session qui repart à froid).
# usage : reprise.sh <SP>   — dépôts attendus : /home/claude/bobmed (branche D3) et /home/claude/bobmed-annales-drive (branche D3)
SP=$1; R=/home/claude/bobmed; W=$R/.wip-d3
mkdir -p $SP/wf $SP/briefs $SP/specs $SP/nj $SP/st $SP/blind $SP/ex/img $SP/hemato/pages $SP/prompts
cp $W/outils/* $SP/; cp $W/workflows/* $W/wf_reprise/* $SP/wf/; cp $W/fiches/* $SP/briefs/; cp $W/specs/*.json $SP/specs/
cp $W/nj/* $SP/nj/; cp $W/analyses/* $SP/st/; cp $W/blind/* $SP/blind/ 2>/dev/null
cp $W/plan_quizzes.json $W/approved.txt $SP/; cp $W/audited.txt $SP/ 2>/dev/null || touch $SP/audited.txt
cd $SP && grep -rlE "/tmp/claude-0/[^'\" ]*/scratchpad|/home/[a-z]+/bobmed" . | xargs sed -i -E "s#/tmp/claude-0/[^'\" ]*/scratchpad#$SP#g; s#/home/[a-z]+/bobmed#$R#g"
python3 -m pip install -q playwright pymupdf beautifulsoup4 2>/dev/null
cd $R && python3 $SP/extract.py
cd /home/claude/bobmed-annales-drive/T2/HEMATO 2>/dev/null && python3 -I $SP/hemato_extract.py "$(ls Revisions_TB*2025.pdf)" $SP/hemato/TB_text.md TB $SP/hemato/pages && python3 -I $SP/hemato_extract.py "$(ls R*RR*2025.pdf)" $SP/hemato/RR_text.md RR $SP/hemato/pages
echo "prêt : prompts avec  cd $SP/wf && node gen.mjs write|audit ent_all.json <noms de quiz>"
