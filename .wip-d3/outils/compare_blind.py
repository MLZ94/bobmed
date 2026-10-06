#!/usr/bin/env python3
"""compare_blind.py spec.json answers.json — compare les réponses à l'aveugle au corrigé.
answers.json : {"Q1": "AC", "Q2": "B", "Q7": "texte libre QROC", ...}"""
import json, sys, re, unicodedata
L = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
def norm(x):
    x = unicodedata.normalize('NFD', x.lower()); x = ''.join(c for c in x if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', x).strip()
s = json.load(open(sys.argv[1], encoding='utf-8')); a = json.load(open(sys.argv[2], encoding='utf-8'))
n = 0; diff = 0; tot = 0
for sec in s['sections']:
    for qi, q in enumerate(sec['questions']):
        n += 1; tot += 1
        qid = f"Q{n}" if s['kind'] == 'entrainement' else f"{sec.get('code')}-Q{qi+1}"
        got = a.get(qid, '')
        if q['type'] == 'QROC':
            ok = norm(got) in [norm(v) for v in q.get('accept', [])]
            if not ok:
                diff += 1; print(f"{qid} QROC : réponse aveugle « {got} » ∉ variantes {q.get('accept')}")
            continue
        key = ''.join(L[i] for i, o in enumerate(q['options']) if o.get('correct'))
        g = ''.join(sorted(set(re.sub(r'[^A-Z]', '', str(got).upper()))))
        if g != key:
            diff += 1; print(f"{qid} {q['type']} : corrigé {key} / réponse aveugle {g or '∅'}")
print(f"--- {diff} divergence(s) sur {tot} questions")
