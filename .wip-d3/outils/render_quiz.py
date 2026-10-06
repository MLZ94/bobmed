#!/usr/bin/env python3
"""Rend un quiz BobMed (entraînement par item ou sujet type) à partir d'un JSON.

usage: render_quiz.py spec.json [--check]   (--check : contrôles seuls, n'écrit rien)

Schéma JSON :
{
  "file": "d3/t2/entrainement/Quiz_item320_myelome.html",   # chemin relatif au dépôt
  "kind": "entrainement" | "sujet_type",
  "title": "Item 320 — Myélome multiple · Entraînement par item",   # <h1>
  "themes": "Électrophorèse · CRAB/SLiM · …",   # entraînement : .sub = "N questions — <themes>"
  "intro_note": "…",            # sujet type : encart .note sous le bandeau (facultatif)
  "footer": "… · BobMed entraînement.",
  "see_also": [{"href": "../../../d2/t1/entrainement/Quiz_item151_meningites.html", "label": "Item 151 — Méningites (D2 T1)"}],   # facultatif
  "sections": [
    {"title": "Questions isolées — Item 320", "code": "SQI1", "locked": false, "label": "SQI1",
     "questions": [
       {"type": "QRM|QRU|QRP|QRPL|QROC|TCS", "rank": "A|B|A/B|null",
        "context": "contexte (1re question d'un DP/KFP/TCS seulement)",
        "stem": "énoncé" | ["partie 1", "partie 2"],
        "options": [{"text": "…", "correct": true, "mandatory": false, "unacceptable": false, "just": "justification"}],
        "accept": ["variante 1", "variante 2"], "answer": "réponse attendue (QROC)",
        "note": "rappel transversal (facultatif)"}]}]
}
Balises autorisées dans les textes : <b> <i> <em> <strong> <sub> <sup> <br>.
"""
import html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path('/home/user/bobmed')
STYLE = (HERE / 'tpl_style.css').read_text(encoding='utf-8')
ENGINE = (HERE / 'tpl_engine.js').read_text(encoding='utf-8')
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
TCS_SCALES = [
    ['improbable', 'peu probable', 'ni plus ou moins probable', 'probable', 'certain'],
]
EXTRA_CSS = """
.qrank{font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:1px 7px;border-radius:20px;border:1px solid}
.rang-a{background:#dcfce7;color:#15803d;border-color:#86efac}
.rang-b{background:#dbeafe;color:#1d4ed8;border-color:#93c5fd}
.rang-mixte{background:#ede9fe;color:#6d28d9;border-color:#c4b5fd}
footer{color:var(--mut);font-size:12.5px;margin-top:30px;border-top:1px solid var(--line);padding-top:16px}
"""
NJ_CSS = ("/* BobMed - justifications non officielles ajoutees */.nj-disclaimer{background:#eef6ff;border:1px solid #cfe3fb;"
          "border-left:4px solid var(--acc2,#06b6d4);border-radius:10px;padding:11px 15px;font-size:13px;line-height:1.5;"
          "color:#0b3a52;margin:0 0 18px}.nj-disclaimer b{color:#084863}\n")
SUJET_BANNER = ('<div class="nj-disclaimer"><b>Sujet type — justifications non officielles.</b> Ce quiz est composé de '
                'questions originales rédigées par BobMed : l\'ensemble des corrections et justifications ci-dessous sont '
                'pédagogiques et ne proviennent d\'aucune correction officielle du jury. Elles peuvent comporter des '
                'imprécisions&nbsp;: recoupez-les toujours avec votre cours.</div>')

ALLOWED = re.compile(r'&lt;(/?)(b|i|em|strong|sub|sup|br)\s*/?&gt;')


def tx(s):
    s = html.escape(str(s or '').strip(), quote=False)
    return ALLOWED.sub(lambda m: f'<{m.group(1)}{m.group(2)}>', s)


def attr(s):
    return html.escape(str(s or ''), quote=True)


class SpecError(Exception):
    pass


def check(spec):
    errs, warns = [], []
    kind = spec.get('kind')
    if kind not in ('entrainement', 'sujet_type'):
        errs.append('kind doit valoir entrainement ou sujet_type')
    f = spec.get('file', '')
    if kind == 'entrainement' and not re.match(r'd3/t[123]/entrainement/Quiz_item\d+(_\d+)*_[a-z0-9_]+\.html$', f):
        errs.append(f'nom de fichier non conforme : {f}')
    if kind == 'sujet_type' and not re.match(r'd3/t[123]/Quiz_UE[\d.]+_sujet_type\.html$', f):
        errs.append(f'nom de fichier non conforme : {f}')
    n = 0
    for si, sec in enumerate(spec.get('sections', [])):
        title = sec.get('title', '')
        locked = bool(sec.get('locked'))
        if locked != bool(re.search(r'DP|KFP|TCS', title)):
            errs.append(f'section « {title} » : locked={locked} incohérent avec le titre (initLocks verrouille les titres contenant DP/KFP/TCS)')
        qs = sec.get('questions', [])
        if not qs:
            errs.append(f'section « {title} » vide')
        for qi, q in enumerate(qs):
            n += 1
            where = f'§{si + 1} Q{qi + 1} ({title[:30]})'
            t = q.get('type')
            if t not in ('QRM', 'QRU', 'QRP', 'QRPL', 'QROC', 'TCS'):
                errs.append(f'{where} type inconnu {t}')
                continue
            if q.get('context') and qi > 0:
                warns.append(f'{where} contexte hors 1re question de section (affiché en .dpctx)')
            if locked and qi == 0 and not q.get('context'):
                warns.append(f'{where} 1re question d\'une section verrouillée sans contexte')
            if not q.get('stem'):
                errs.append(f'{where} énoncé vide')
            if kind == 'entrainement' and q.get('rank') not in ('A', 'B', 'A/B', None):
                errs.append(f'{where} rang invalide {q.get("rank")}')
            if t == 'QROC':
                if not q.get('accept') or not q.get('answer'):
                    errs.append(f'{where} QROC sans accept/answer')
                continue
            opts = q.get('options') or []
            nc = sum(1 for o in opts if o.get('correct'))
            if len(opts) < 4:
                errs.append(f'{where} moins de 4 options')
            if len(opts) > 26:
                errs.append(f'{where} trop d\'options')
            for o in opts:
                if not str(o.get('text', '')).strip():
                    errs.append(f'{where} option vide')
                if o.get('mandatory') and not o.get('correct'):
                    errs.append(f'{where} item indispensable non correct')
                if o.get('unacceptable') and o.get('correct'):
                    errs.append(f'{where} item inacceptable marqué correct')
                if t != 'TCS' and not str(o.get('just', '')).strip():
                    warns.append(f'{where} option sans justification')
            if t in ('QRU', 'TCS') and nc != 1:
                errs.append(f'{where} {t} avec {nc} bonne(s) réponse(s)')
            if t == 'QRM' and nc < 1:
                errs.append(f'{where} QRM sans bonne réponse')
            if t in ('QRP', 'QRPL') and nc < 2:
                errs.append(f'{where} {t} avec moins de 2 bonnes réponses')
            if t == 'TCS' and len(opts) != 5:
                errs.append(f'{where} TCS à {len(opts)} options (5 attendues)')
            if t == 'TCS' and not str(q.get('note', '')).strip():
                warns.append(f'{where} TCS sans note explicative')
    for s in spec.get('see_also') or []:
        target = (REPO / spec.get('file', '')).parent / s.get('href', '')
        if not s.get('label') or not target.resolve().exists():
            errs.append(f"see_also introuvable : {s.get('href')}")
    if n == 0:
        errs.append('aucune question')
    return errs, warns, n


def render_q(q, qid, qnum, kind):
    t = q['type']
    dtype = 'QRU' if t == 'TCS' else t
    opts = q.get('options') or []
    correct = ''.join(LETTERS[i] for i, o in enumerate(opts) if o.get('correct'))
    badge = t
    if t in ('QRP', 'QRPL'):
        badge = f'{t} · {len(correct)} réponses'
    out = []
    extra_attr = ''
    if t == 'QROC':
        variants = [v.strip() for v in q['accept'] if v and v.strip()]
        extra_attr = f' data-answer="{attr(" | ".join(variants))}"'
        correct = ''
    out.append(f'<div class="q" id="{qid}" data-type="{dtype}" data-correct="{correct}"{extra_attr}>')
    rank = ''
    if kind == 'entrainement' and q.get('rank'):
        cls = {'A': 'rang-a', 'B': 'rang-b', 'A/B': 'rang-mixte'}[q['rank']]
        rank = f'<span class="qrank {cls}">Rang {q["rank"]}</span>'
    out.append(f'  <div class="qhead"><span class="qnum">{qnum}</span>{rank}<span class="qtype">{badge}</span>'
               f'<span class="status" aria-live="polite"></span></div>')
    if q.get('context'):
        out.append(f'  <div class="dpctx">{tx(q["context"])}</div>')
    stems = q['stem'] if isinstance(q['stem'], list) else [q['stem']]
    for s in stems:
        out.append(f'  <div class="stem">{tx(s)}</div>')
    if t == 'QROC':
        out.append('  <textarea class="qrocin" rows="2" placeholder="Réponds, puis « Valider »"></textarea>')
    else:
        out.append('  <ul class="opts">')
        for i, o in enumerate(opts):
            a = f' data-l="{LETTERS[i]}" data-correct="{1 if o.get("correct") else 0}"'
            if o.get('mandatory'):
                a += ' data-mandatory="1"'
            if o.get('unacceptable'):
                a += ' data-unacceptable="1"'
            out.append(f'    <li class="opt"{a}><span class="box">{LETTERS[i]}</span><span class="otext">{tx(o["text"])}</span></li>')
        out.append('  </ul>')
    out.append('  <div class="actions"><button class="validate">Valider</button><button class="show" type="button">Voir la réponse</button></div>')
    out.append('  <div class="correction" hidden>')
    if t == 'QROC':
        out.append(f'    <div class="qrocans">Réponse attendue : {tx(q["answer"])}</div>')
        if q.get('note'):
            out.append(f'    <div class="note"><div class="rappel">{tx(q["note"])}</div></div>')
    elif t == 'TCS':
        i = next(i for i, o in enumerate(opts) if o.get('correct'))
        out.append(f'    <div class="ans">Réponse : {LETTERS[i]} — {tx(opts[i]["text"])}</div>')
        if q.get('note'):
            out.append(f'    <div class="note">{tx(q["note"])}</div>')
    else:
        out.append(f'    <div class="ans">Réponse : {", ".join(correct)}</div>')
        if q.get('note'):
            out.append(f'    <div class="note"><div class="rappel">{tx(q["note"])}</div></div>')
        for i, o in enumerate(opts):
            v = 'VRAI' if o.get('correct') else 'FAUX'
            j = str(o.get('just', '')).strip()
            out.append(f'    <div class="citem v-{v.lower()}"><span class="cl">{LETTERS[i]}.</span> <span class="cv">{v}</span>'
                       + (f' — {tx(j)}' if j else '') + '</div>')
    out.append('  </div>')
    out.append('</div>')
    return '\n'.join(out)


def render(spec):
    kind = spec['kind']
    depth = '../../../' if kind == 'entrainement' else '../../'
    total = sum(len(s['questions']) for s in spec['sections'])
    body = []
    n = 0
    for sec in spec['sections']:
        body.append(f'<div class="sect">{tx(sec["title"])}</div>\n')
        code = sec.get('code') or ''
        for qi, q in enumerate(sec['questions']):
            n += 1
            if kind == 'entrainement':
                qid, qnum = f'Q{n}', f'Q{n}'
            else:
                qid, qnum = f'{code}-Q{qi + 1}', f'{code} Q{qi + 1}'
            body.append(render_q(q, qid, qnum, kind) + '\n')
    if kind == 'entrainement':
        sub = f'{total} questions — {tx(spec["themes"])}'
    else:
        bits = []
        for sec in spec['sections']:
            lab = tx(sec.get('label') or sec['code'])
            k = len(sec['questions'])
            bits.append(f'{lab} ({k}, verrouillé)' if sec.get('locked') else f'{lab} ({k})')
        sub = f'{total} questions : ' + ' · '.join(bits)
    title_txt = re.sub(r'<[^>]+>', '', spec['title'])
    page_title = spec.get('page_title') or (f'{title_txt} · BobMed')
    css = STYLE + EXTRA_CSS + (NJ_CSS if kind == 'sujet_type' else '')
    head = (f'<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<link rel="icon" type="image/svg+xml" href="{depth}favicon.svg">\n'
            f'<link rel="stylesheet" href="{depth}theme.css">\n'
            f'<title>{html.escape(page_title)}</title>\n<style>{css}</style>\n'
            "<script>(()=>{if(localStorage.theme==='dark')document.documentElement.classList.add('dark')})()</script>\n"
            '</head><body>\n')
    header = (f'<header><div class="hwrap">\n<h1>{tx(spec["title"])}</h1>\n<div class="sub">{sub}</div>\n'
              '<div class="scorebar">\n'
              f'<span class="pill">Validées : <b id="s-done">0/{total}</b></span>\n'
              f'<span class="pill">Score : <b id="s-ok">0/{total}</b></span>\n'
              '<span class="pill"><button id="revealall" style="padding:2px 10px">Tout révéler</button></span>\n'
              '<span class="pill"><button id="reset" style="padding:2px 10px">Recommencer</button></span>\n'
              '</div>\n</div></header>\n')
    wrap = ['<div class="wrap">']
    if kind == 'sujet_type':
        wrap.append(SUJET_BANNER)
        if spec.get('intro_note'):
            wrap.append(f'<div class="note" style="margin:0 0 24px">{tx(spec["intro_note"])}</div>')
    wrap.append('')
    wrap.extend(body)
    links = ''
    if spec.get('see_also'):
        links = ' · Voir aussi : ' + ' · '.join(f'<a href="{attr(s["href"])}">{tx(s["label"])}</a>' for s in spec['see_also'])
    wrap.append(f'<footer>{tx(spec["footer"])}{links}</footer>')
    wrap.append('</div>')
    scripts = ['breadcrumb.js', 'dynamic-header.js'] + (['timer.js'] if kind == 'sujet_type' else []) + ['progress.js', 'qcopy.js']
    tail = f'\n<script>{ENGINE}</script>\n' + '\n'.join(f'<script src="{depth}{s}"></script>' for s in scripts) + '\n</body></html>\n'
    return head + header + '\n'.join(wrap) + tail


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    spec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    errs, warns, n = check(spec)
    for w in warns:
        print('AVERT', w)
    for e in errs:
        print('ERREUR', e)
    if errs:
        sys.exit(1)
    if '--check' in sys.argv:
        print(f'OK ({n} questions, contrôles seuls)')
        return
    out = REPO / spec['file']
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(spec), encoding='utf-8')
    print(f'OK {out} ({n} questions)')


if __name__ == '__main__':
    main()
