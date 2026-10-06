#!/usr/bin/env python3
"""Version « copie d'examen » d'un spec de quiz (sans corrigé) : strip_spec.py spec.json > blind.md"""
import json, sys
L = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
s = json.load(open(sys.argv[1], encoding='utf-8'))
print(f"# {s['title']}\n")
n = 0
for sec in s['sections']:
    print(f"\n## {sec['title']}\n")
    for qi, q in enumerate(sec['questions']):
        n += 1
        qid = f"Q{n}" if s['kind'] == 'entrainement' else f"{sec.get('code')}-Q{qi+1}"
        t = q['type']; nc = sum(1 for o in q.get('options') or [] if o.get('correct'))
        extra = f" (sélectionnez {nc} réponses)" if t in ('QRP', 'QRPL') else ''
        print(f"### {qid} [{t}]{extra}")
        if q.get('context'): print('CONTEXTE :', q['context'])
        st = q['stem'] if isinstance(q['stem'], list) else [q['stem']]
        for x in st: print('ÉNONCÉ :', x)
        for i, o in enumerate(q.get('options') or []): print(f"  {L[i]}. {o['text']}")
        if t == 'QROC': print('  (réponse courte attendue)')
        print()
