#!/usr/bin/env python3
"""Insère des justifications non officielles ◈ dans une annale BobMed.

usage: apply_nj.py nj.json [--check]

nj.json :
{"file": "d3/t2/Quiz_UE9_2022-2023_S1.html",
 "nj": [{"qid": "SQI1-QA", "l": "B", "text": "Une phrase d'explication."}],
 "rappels": [{"qid": "DP1-Q3", "text": "Rappel de cours transversal."}]}

- Le ◈ se place juste après le verdict (<span class="cv">…</span>) du .citem de la
  lettre visée ; une justification ◈ déjà présente sur cet item est remplacée
  (idempotent), un item déjà justifié officiellement est refusé.
- Refuse les TCS, QROC, QZONE et items neutralisés.
- Ajoute le bandeau .nj-disclaimer (1er enfant de .wrap) et le CSS si absents.
Le fichier est modifié par chirurgie de chaînes (pas de re-sérialisation).
"""
import html, json, re, sys
from pathlib import Path

REPO = Path('/home/user/bobmed')
BANNER = ('<div class="nj-disclaimer"><span class="njm">◈</span> <b>Justifications non officielles.</b> Les explications '
          'signalées par le symbole <span class="njm">◈</span> après &laquo; VRAI &raquo;/&laquo; FAUX &raquo; ont été ajoutées '
          'par BobMed pour faciliter la révision. Elles ne proviennent pas de la correction officielle du jury et peuvent '
          'comporter des imprécisions&nbsp;: recoupez-les toujours avec votre cours.</div>')
CSS = ('/* BobMed - justifications non officielles ajoutees */.nj-disclaimer{background:#eef6ff;border:1px solid #cfe3fb;'
       'border-left:4px solid var(--acc2,#06b6d4);border-radius:10px;padding:11px 15px;font-size:13px;line-height:1.5;'
       'color:#0b3a52;margin:0 0 18px}.nj-disclaimer b{color:#084863}.nj-disclaimer .njm{color:var(--acc2,#06b6d4);'
       'font-weight:700}.citem .nj{color:var(--ink,#132025)}.citem .njm{font-weight:700;color:var(--acc2,#06b6d4);padding:0 1px}\n')
CSS_RAPPEL = '.rappel .njm{font-weight:700;color:var(--acc2,#06b6d4);padding:0 1px}\n'
ALLOWED = re.compile(r'&lt;(/?)(b|i|em|strong|sub|sup|br)\s*/?&gt;')


def tx(s):
    s = html.escape(str(s or '').strip(), quote=False)
    return ALLOWED.sub(lambda m: f'<{m.group(1)}{m.group(2)}>', s)


def q_bounds(t, qid):
    m = re.search(r'<div class="q[ "][^>]*\bid="' + re.escape(qid) + r'"', t)
    if not m:
        return None
    start = m.start()
    nxt = re.compile(r'<div class="q[ "]|<div class="sect"|<footer|<script>')
    n = nxt.search(t, m.end())
    return start, (n.start() if n else len(t))


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    check_only = '--check' in sys.argv
    path = REPO / spec['file']
    t = path.read_text(encoding='utf-8')
    errs, warns = [], []
    seen = set()
    edits = []  # (qid, letter, text)
    for e in spec.get('nj', []):
        qid, l, text = e['qid'], e['l'].strip().rstrip('.'), e['text'].strip()
        key = (qid, l)
        if key in seen:
            errs.append(f'{qid} {l} : doublon dans le JSON')
            continue
        seen.add(key)
        b = q_bounds(t, qid)
        if not b:
            errs.append(f'{qid} : question introuvable')
            continue
        blk = t[b[0]:b[1]]
        head = re.match(r'<div class="q[^>]*>', blk).group(0)
        dtype = re.search(r'data-type="([^"]+)"', head).group(1)
        qtype = re.search(r'<span class="qtype">([^<]*)</span>', blk)
        if dtype in ('QROC', 'QZONE') or (qtype and 'TCS' in qtype.group(1)):
            errs.append(f'{qid} : pas de ◈ sur une {dtype if dtype != "QRU" else "TCS"}')
            continue
        if re.search(r'data-neutral="1"', head):
            warns.append(f'{qid} : question neutralisée (◈ accepté, la correction reste affichée)')
        opt = re.search(r'<li class="opt"[^>]*data-l="' + l + r'"[^>]*>', blk)
        if opt and 'data-neutral="1"' in opt.group(0):
            errs.append(f'{qid} {l} : item neutralisé')
            continue
        cm = re.search(r'(<div class="citem v-(?:vrai|faux)"><span class="cl">' + l + r'\.</span> <span class="cv">(?:VRAI|FAUX)</span>)(.*?)(</div>)', blk)
        if not cm:
            errs.append(f'{qid} {l} : ligne de correction introuvable')
            continue
        rest = re.sub(r'\s*<span class="nj">.*</span>\s*$', '', cm.group(2))
        if re.sub(r'[\s—–-]', '', re.sub(r'<[^>]+>', '', rest)):
            errs.append(f'{qid} {l} : déjà justifié officiellement')
            continue
        if re.match(r'(VRAI|FAUX|Vrai|Faux)\b', text):
            warns.append(f'{qid} {l} : commence par VRAI/FAUX')
        nw = len(text.split())
        if nw < 6 or nw > 60:
            warns.append(f'{qid} {l} : {nw} mots')
        edits.append((qid, l, text))
    rap = []
    for r in spec.get('rappels', []):
        b = q_bounds(t, r['qid'])
        if not b:
            errs.append(f'{r["qid"]} : question introuvable (rappel)')
            continue
        rap.append((r['qid'], r['text'].strip()))
    for w in warns:
        print('AVERT', w)
    for e in errs:
        print('ERREUR', e)
    if check_only or errs:
        print(f'{len(edits)} ◈ valides, {len(rap)} rappels, {len(errs)} erreur(s)')
        sys.exit(1 if errs else 0)
    for qid, l, text in edits:
        b = q_bounds(t, qid)
        blk = t[b[0]:b[1]]
        pat = re.compile(r'(<div class="citem v-(?:vrai|faux)"><span class="cl">' + l + r'\.</span> <span class="cv">(?:VRAI|FAUX)</span>)(.*?)(</div>)')
        blk2 = pat.sub(lambda m: m.group(1) + f' <span class="nj">— <span class="njm">◈</span> {tx(text)}</span>' + m.group(3), blk, count=1)
        t = t[:b[0]] + blk2 + t[b[1]:]
    for qid, text in rap:
        b = q_bounds(t, qid)
        blk = t[b[0]:b[1]]
        newnote = f'<div class="note"><div class="rappel"><span class="njm">◈</span> {tx(text)}</div></div>'
        if newnote in blk:
            continue
        i = blk.find('<div class="citem')
        if i < 0:
            i = blk.find('</div>', blk.find('<div class="ans">'))
            i = i + len('</div>') if i >= 0 else -1
        if i < 0:
            print('ERREUR', qid, 'emplacement du rappel introuvable')
            sys.exit(1)
        blk = blk[:i] + newnote + '\n' + blk[i:]
        t = t[:b[0]] + blk + t[b[1]:]
    if 'class="nj-disclaimer"' not in t:
        t = re.sub(r'(<div class="wrap">)', r'\1' + BANNER.replace('\\', '\\\\'), t, count=1)
    if '.nj-disclaimer{' not in t:
        t = t.replace('</style>', CSS + '</style>', 1)
    if rap and '.rappel .njm' not in t:
        t = t.replace('</style>', CSS_RAPPEL + '</style>', 1)
    path.write_text(t, encoding='utf-8')
    print(f'OK {spec["file"]} : {len(edits)} ◈, {len(rap)} rappel(s)')


if __name__ == '__main__':
    main()
