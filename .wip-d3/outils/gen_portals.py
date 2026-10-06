#!/usr/bin/env python3
"""Génère d3/tN/entrainement/index.html à partir des specs des quiz (plan_quizzes.json)
et met à jour la sous-catégorie « Entraînement par item » des portails d3/tN/index.html.

usage: gen_portals.py [--dry-run]
"""
import html, json, re, sys
from pathlib import Path

SP = Path('/tmp/claude-0/-home-user/55cc2afb-deb2-5236-a438-a491d4be9ce0/scratchpad')
R = Path('/home/user/bobmed')
PLAN = json.loads((SP / 'plan_quizzes.json').read_text(encoding='utf-8'))
DRY = '--dry-run' in sys.argv

GROUPS = {
    'gyneco':        dict(t='t1', anchor='gyneco', emoji='🤰', nav='Gynécologie-Obstétrique', ue='2', block='gyneco-pediatrie',
                          head='UE 2 — Gynécologie-Obstétrique · Quiz par item', card='UE 2 Gynécologie-Obstétrique'),
    'pediatrie':     dict(t='t1', anchor='pediatrie', emoji='🧸', nav='Pédiatrie', ue='2', block='gyneco-pediatrie',
                          head='UE 2 — Pédiatrie · Quiz par item', card='UE 2 Pédiatrie'),
    'geriatrie':     dict(t='t2', anchor='geriatrie', emoji='🧓', nav='Gériatrie', ue='5', block='geriatrie',
                          head='UE 5 — Gériatrie · Quiz par item', card='UE 5 Gériatrie'),
    'hemato':        dict(t='t2', anchor='hemato', emoji='🩸', nav='Hématologie', ue='7.3', block='hemato',
                          head='UE 7.3 — Hématologie · Quiz par item', card='UE 7.3 Hématologie'),
    'onco':          dict(t='t2', anchor='onco', emoji='🎗️', nav='Oncologie', ue='9', block='onco',
                          head='UE 9 — Oncologie · Quiz par item', card='UE 9 Oncologie'),
    'therapeutique': dict(t='t3', anchor='therapeutique', emoji='💊', nav='Thérapeutique', ue='10', block='therapeutique',
                          head='UE 10 — Thérapeutique · Quiz par item', card='UE 10 Thérapeutique'),
    'urgences':      dict(t='t3', anchor='urgences', emoji='🚑', nav='Urgences-Réanimation', ue='11.2', block='urgences-rea',
                          head='UE 11.2 — Urgences-Réanimation · Quiz par item', card='UE 11.2 Urgences-Réanimation'),
}
T_TITLE = {'t1': 'D3 T1', 't2': 'D3 T2', 't3': 'D3 T3'}

PORTAL_CSS = """:root{--bg:#f7f8f9;--card:#fff;--ink:#132025;--mut:#5b6b73;--line:#dfe4e2;--acc:#4f46e5}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 'DM Sans',-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:32px 18px 80px}
.breadcrumb{font-size:12.5px;color:var(--mut);margin-bottom:18px}
.breadcrumb a{color:var(--mut);text-decoration:none}.breadcrumb a:hover{color:var(--acc)}
.breadcrumb .sep{margin:0 5px}
.badge{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#fff;background:var(--acc);border-radius:7px;padding:3px 12px;margin-bottom:12px}
h1{font-size:24px;font-weight:700;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--mut);font-size:14px;margin-bottom:20px;max-width:600px}
.secnav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}
.secnav a{font-size:13px;font-weight:600;text-decoration:none;color:var(--acc);background:#eef2ff;border:1px solid #dbe4ff;border-radius:20px;padding:5px 14px;transition:.12s}
.secnav a:hover{background:var(--acc);color:#fff}
.ue{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:30px 2px 10px;border-bottom:1px solid var(--line);padding-bottom:6px;scroll-margin-top:16px}
.qz{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:12px;padding:14px 16px;margin:0 0 10px;transition:.12s}
.qz:hover{border-color:var(--acc);box-shadow:0 2px 10px rgba(79,70,229,.12);transform:translateY(-1px)}
.qz-t{font-weight:600;font-size:15px;margin-bottom:2px}
.qz-d{color:var(--mut);font-size:13.5px}
.qz-go{display:inline-block;margin-top:8px;font-size:13px;font-weight:600;color:var(--acc)}
.seealso{font-size:12.5px;color:var(--mut);margin:-4px 2px 12px 6px}
.seealso a{color:var(--acc);text-decoration:none}.seealso a:hover{text-decoration:underline}
.rank-pill{display:inline-block;font-size:10.5px;font-weight:700;padding:1px 8px;border-radius:20px;border:1px solid;margin-left:6px;vertical-align:middle}
.rang-a{background:#dcfce7;color:#15803d;border-color:#86efac}
.rang-b{background:#dbeafe;color:#1d4ed8;border-color:#93c5fd}
.rang-mixte{background:#ede9fe;color:#6d28d9;border-color:#c4b5fd}
footer{color:var(--mut);font-size:12.5px;margin-top:30px;border-top:1px solid var(--line);padding-top:16px}
"""


def e(s):
    return html.escape(str(s), quote=False)


APPROVED = set((SP / 'approved.txt').read_text().split()) if (SP / 'approved.txt').exists() else None


def load(entry):
    if APPROVED is not None and entry['file'] not in APPROVED:
        return None
    b = entry['file'].split('/')[-1].replace('.html', '')
    p = SP / 'specs' / f'{b}.json'
    if not p.exists() or not (R / entry['file']).exists():
        return None
    s = json.loads(p.read_text(encoding='utf-8'))
    n = sum(len(sec['questions']) for sec in s['sections'])
    ranks = {q.get('rank') for sec in s['sections'] for q in sec['questions']}
    short = re.sub(r'\s*·\s*Entraînement par item\s*$', '', re.sub(r'<[^>]+>', '', s['title']))
    return dict(entry=entry, spec=s, n=n, ranks=ranks, short=short, fname=entry['file'].split('/')[-1])


def card(q):
    pills = ''
    if 'A' in q['ranks'] or 'A/B' in q['ranks']:
        pills += '<span class="rank-pill rang-a">Rang A</span>'
    if 'B' in q['ranks'] or 'A/B' in q['ranks']:
        pills += '<span class="rank-pill rang-b">Rang B</span>'
    out = [f'<a class="qz" href="{q["fname"]}">',
           f'  <div class="qz-t">{e(q["short"])} {pills}</div>',
           f'  <div class="qz-d">{q["n"]} questions — {e(q["spec"]["themes"])}</div>',
           '  <span class="qz-go">Ouvrir le quiz →</span>', '</a>']
    sa = q['spec'].get('see_also') or []
    if sa:
        links = ' · '.join(f'<a href="{s["href"]}">{e(s["label"])}</a>' for s in sa)
        out.append(f'<div class="seealso">Voir aussi, en D2 : {links}</div>')
    return '\n'.join(out)


def build_entrainement(t, groups):
    tl = T_TITLE[t]
    nav = '\n'.join(f'  <a href="#{GROUPS[g]["anchor"]}">{GROUPS[g]["emoji"]} {GROUPS[g]["nav"]}</a>' for g in groups if groups[g])
    body = []
    tot_q = 0
    tot_n = 0
    parts = []
    for g, qs in groups.items():
        if not qs:
            continue
        body.append(f'\n<!-- ─── {GROUPS[g]["head"]} ─── -->')
        body.append(f'<div class="ue" id="{GROUPS[g]["anchor"]}">{e(GROUPS[g]["head"])}</div>\n')
        for q in qs:
            body.append(card(q) + '\n')
            tot_q += q['n']
        tot_n += len(qs)
        parts.append(f'{GROUPS[g]["card"]} ({len(qs)})')
    multi = len([g for g in groups if groups[g]]) > 1
    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="../../../favicon.svg">
<link rel="stylesheet" href="../../../theme.css">
<title>Entraînement par item — {tl} · BobMed</title>
<style>
{PORTAL_CSS}</style>
<script>(()=>{{if(localStorage.theme==='dark')document.documentElement.classList.add('dark')}})()</script>
</head>
<body>
<div class="wrap">

<nav class="breadcrumb">
  <a href="../../../index.html">BobMed</a><span class="sep">›</span>
  <a href="../../../index.html#d3">D3</a><span class="sep">›</span>
  <a href="../index.html">{t.upper()}</a><span class="sep">›</span>
  <span>Entraînement par item</span>
</nav>

<div class="badge">D3 · {t.upper()} · Entraînement</div>
<h1>Entraînement par item — {tl}</h1>
<div class="sub">Quiz d'entraînement thématiques par item, construits à partir de ce qui tombe aux partiels de la faculté (mêmes notions, mêmes pièges, mêmes formats : QRM, QRU, QROC, QRP, TCS, dossiers progressifs), en complément des annales officielles. Questions originales avec indication du rang A / B (lorsqu'il est connu), corrections détaillées et barème EDN/R2C intégré.</div>
{('<nav class="secnav">' + chr(10) + nav + chr(10) + '</nav>') if multi else ''}
{chr(10).join(body)}
<footer>{tot_n} quiz d'entraînement par item ({tot_q} questions) · {' · '.join(parts)} · {tl} · BobMed révisions.</footer>

</div>
<script src="../../../breadcrumb.js"></script>
<script src="../../../progress.js"></script>
</body></html>
"""


def item_label(q):
    nums = '/'.join(str(i) for i in q['entry']['items'])
    name = re.sub(r'^Items? [\d/]+ — ', '', q['short'])
    return f"{'Items' if len(q['entry']['items']) > 1 else 'Item'} {nums} {name}"


def update_trimester(t, groups):
    p = R / 'd3' / t / 'index.html'
    s = p.read_text(encoding='utf-8')
    by_block = {}
    for g, qs in groups.items():
        if qs:
            by_block.setdefault(GROUPS[g]['block'], []).append((g, qs))
    for block, lst in by_block.items():
        m = re.search(r'<div class="ue-block" id="' + block + r'">', s)
        if not m:
            raise SystemExit(f'bloc {block} introuvable dans {p}')
        start = m.start()
        end = s.find('<div class="ue-block"', m.end())
        end = len(s) if end < 0 else end
        blk = s[start:end]
        # retire une éventuelle sous-catégorie entraînement générée précédemment
        blk = re.sub(r'\n  <div class="subcat"><span class="dot"></span><span class="t">Entraînement par item</span>.*?(?=\n  <div class="subcat">)', '', blk, flags=re.S)
        nq = sum(len(qs) for _, qs in lst)
        cards = []
        for g, qs in lst:
            tot = sum(q['n'] for q in qs)
            lab = GROUPS[g]['card']
            desc = ' · '.join(item_label(q) for q in qs)
            cards.append(f'''  <a class="qz" href="entrainement/index.html#{GROUPS[g]["anchor"]}">
    <div class="qz-t">Quiz d'entraînement par item — {e(lab)}</div>
    <div class="qz-d">{len(qs)} quiz thématique{'s' if len(qs) > 1 else ''} ({tot} questions) : {e(desc)} — avec rang A/B et corrections détaillées</div>
    <span class="qz-go">Accéder à l'entraînement →</span>
  </a>''')
        sub = (f'\n  <div class="subcat"><span class="dot"></span><span class="t">Entraînement par item</span><span class="n">{nq} quiz</span></div>\n'
               + '\n'.join(cards))
        i = blk.find('\n  <div class="subcat">')
        blk = blk[:i] + sub + blk[i:]
        # compteur
        def cnt(mm):
            parts = [x.strip() for x in mm.group(1).split('·')]
            parts = [x for x in parts if 'entraîn' not in x]
            ann = [x for x in parts if 'annale' in x]
            rest = [x for x in parts if 'annale' not in x]
            return f'<span class="cnt">{" · ".join(ann + [f"{nq} entraîn."] + rest)}</span>'
        blk = re.sub(r'<span class="cnt">(.*?)</span>', cnt, blk, count=1)
        s = s[:start] + blk + s[end:]
    if not DRY:
        p.write_text(s, encoding='utf-8')
    return s


def main():
    by_t = {'t1': {}, 't2': {}, 't3': {}}
    for g, meta in GROUPS.items():
        by_t[meta['t']][g] = []
    missing = []
    for entry in PLAN:
        q = load(entry)
        if q is None:
            missing.append(entry['file'])
            continue
        by_t[entry['trimestre']][entry['group']].append(q)
    for t in by_t:
        for g in by_t[t]:
            by_t[t][g].sort(key=lambda q: (q['entry']['items'][0], q['fname']))
    for t, groups in by_t.items():
        if not any(groups.values()):
            continue
        out = R / 'd3' / t / 'entrainement' / 'index.html'
        page = build_entrainement(t, groups)
        if not DRY:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(page, encoding='utf-8')
        update_trimester(t, groups)
        print(t, {g: len(v) for g, v in groups.items()})
    if missing:
        print('MANQUANTS :', *missing, sep='\n  ')


if __name__ == '__main__':
    main()
