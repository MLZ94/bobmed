#!/usr/bin/env python3
"""Ajoute (ou rafraîchit) la carte « Sujet type » d'une UE dans son portail de trimestre D3.

usage: add_sujet_type.py d3/t1/Quiz_UE2_sujet_type.html "thème 1, thème 2, …"

- Bloc .ue-block trouvé d'après l'UE du nom de fichier ; sous-catégorie « Sujet type »
  placée juste avant « Annales officielles » (après « Entraînement par item » s'il existe),
  comme dans les portails D2.
- Titre de la carte : le <h1> du quiz (« UE x — Matière · Sujet type (synthèse des annales …) »
  → « Sujet type — Matière (synthèse des annales …) ») ; description : « N questions —
  synthèse des thèmes les plus fréquents aux partiels : <thèmes> ».
- Compteur .cnt : ajoute « 1 sujet type » (idempotent).
"""
import html, re, sys
from pathlib import Path

R = Path('/home/user/bobmed')
BLOCK = {'2': 'gyneco-pediatrie', '5': 'geriatrie', '7.3': 'hemato', '9': 'onco', '10': 'therapeutique', '11.2': 'urgences-rea'}


def main():
    rel, themes = sys.argv[1], sys.argv[2].strip().rstrip('.')
    q = (R / rel).read_text(encoding='utf-8')
    ue = re.search(r'Quiz_UE([\d.]+)_sujet_type\.html$', rel).group(1)
    t = rel.split('/')[1]
    h1 = html.unescape(re.search(r'<h1>(.*?)</h1>', q, re.S).group(1)).strip()
    m = re.match(r'UE [\d.]+ — (.+?) · Sujet type \((.+)\)$', h1)
    if not m:
        raise SystemExit(f'titre inattendu : {h1}')
    matiere, synth = m.group(1), m.group(2)
    n = len(re.findall(r'<div class="q[ "]', q))
    e = lambda s: html.escape(s, quote=False)
    card = (f'\n  <div class="subcat"><span class="dot"></span><span class="t">Sujet type</span></div>\n'
            f'  <a class="qz" href="{rel.split("/")[-1]}">\n'
            f'    <div class="qz-t">Sujet type — {e(matiere)} ({e(synth)})</div>\n'
            f'    <div class="qz-d">{n} questions — synthèse des thèmes les plus fréquents aux partiels : {e(themes)}</div>\n'
            f'    <span class="qz-go">Ouvrir le quiz →</span>\n'
            f'  </a>')
    p = R / 'd3' / t / 'index.html'
    s = p.read_text(encoding='utf-8')
    mb = re.search(r'<div class="ue-block" id="' + BLOCK[ue] + r'">', s)
    if not mb:
        raise SystemExit(f'bloc {BLOCK[ue]} introuvable dans {p}')
    start, end = mb.start(), s.find('<div class="ue-block"', mb.end())
    end = len(s) if end < 0 else end
    blk = s[start:end]
    blk = re.sub(r'\n  <div class="subcat"><span class="dot"></span><span class="t">Sujet type</span>.*?(?=\n  <div class="subcat">)', '', blk, flags=re.S)
    i = blk.find('\n  <div class="subcat"><span class="dot"></span><span class="t">Annales officielles</span>')
    if i < 0:
        raise SystemExit('sous-catégorie « Annales officielles » introuvable')
    blk = blk[:i] + card + blk[i:]

    def cnt(mm):
        parts = [x.strip() for x in mm.group(1).split('·') if 'sujet type' not in x]
        return f'<span class="cnt">{" · ".join(parts + ["1 sujet type"])}</span>'
    blk = re.sub(r'<span class="cnt">(.*?)</span>', cnt, blk, count=1)
    s = s[:start] + blk + s[end:]
    p.write_text(s, encoding='utf-8')
    print(f'OK {p.relative_to(R)} : carte « Sujet type » UE {ue} ({n} questions)')


if __name__ == '__main__':
    main()
