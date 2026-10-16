#!/usr/bin/env python3
"""État généré automatiquement de chaque quiz du plan (publié / audité / rédigé / à rédiger)."""
import json, sys, datetime
from pathlib import Path
SP = Path(sys.argv[1]); R = Path('/home/claude/bobmed')
plan = json.loads((SP / 'plan_quizzes.json').read_text())
rd = lambda f: set((SP / f).read_text().split()) if (SP / f).exists() else set()
appr, aud = rd('approved.txt'), rd('audited.txt')
rows = {'publié': [], 'audité, à publier': [], 'rédigé, à auditer': [], 'à rédiger': []}
for q in plan:
    f = q['file']; b = f.split('/')[-1][:-5]
    st = 'publié' if f in appr else 'audité, à publier' if f in aud else 'rédigé, à auditer' if (SP / 'specs' / f'{b}.json').exists() else 'à rédiger'
    rows[st].append(f)
print(f"# État des quiz d'entraînement D3 (généré le {datetime.datetime.now(datetime.UTC):%Y-%m-%d %H:%M} UTC par outils/etat.py)\n")
for k, v in rows.items():
    print(f"## {k} ({len(v)})"); print('\n'.join(f'- {x}' for x in v) or '- (aucun)'); print()
