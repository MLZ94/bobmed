#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_to_quiz.py — Convertit une annale PDF (export type "Question N: (Type: ...)")
en quiz HTML autonome au format BobMed.

Usage :
    python pdf_to_quiz.py chemin/vers/annale.pdf

Produit, à côté du PDF :
    - annale.html            : le quiz prêt à publier
    - annale.snippet.html    : le bloc <a class="qz">...</a> à coller dans le portail
    - annale.debug.json      : (option --debug) structure intermédiaire parsée

Dépendance : PyMuPDF
    pip install pymupdf

IMPORTANT — ce script est un outil d'assistance, pas une baguette magique :
relis toujours le HTML généré avant de le publier (titres de section, images,
questions marquées [A VERIFIER]). Le format visé est celui des exports PDF
"Question N: (Type: XXX) score/1" avec cases ☐/☑ (QRM/QRPL) ou ◎/◉ (QRU/QTCS)
et libellés Faux/Valide/Indispensable. Si la plateforme source change son
gabarit d'export, les regex ci-dessous devront être ajustées.
"""

import sys
import os
import re
import json
import html
import base64
import argparse

# ----------------------------------------------------------------------------
# 0. Constantes / tables de connaissance du site BobMed
# ----------------------------------------------------------------------------

# UE -> (nom affiché, dossier de destination). Cf. table CLAUDE.md du dépôt.
UE_MAP = {
    "8.2": ("Cardiologie", "d2/t1"),
    "7.1": ("Pneumologie", "d2/t1"),
    "6":   ("Maladies transmissibles", "d2/t1"),
    "8.1": ("Hépato-Gastro / Chir-Dig", "d2/t2"),
    "4.1": ("Neurologie-MPR", "d2/t2"),
    "4.3": ("Dermatologie", "d2/t3"),
    "7.2": ("Médecine Interne", "d2/t3"),
    "8.4": ("Néphro / Uro", "d2/t3"),
    "4.2": ("ORL / Ophtalmo / Chir maxillo-faciale", "d2/t4"),
    "7.3": ("Rhumatologie", "d2/t4"),
    "11.1": ("Chirurgie Orthopédique", "d2/t4"),
    "8.3": ("Endocrino / Nutrition", "d2/t4"),
    "12.1": ("Anglais", "d2/t4"),
    "12.2": ("LCA", "d2/t4"),
    "1.1": ("Biostatistiques (D1)", "annales"),
    "9.2": ("UE 9.2 (D1)", "annales"),
    "9.3": ("UE 9.3 (D1)", "annales"),
    # UE 3 existe en D1 (Psy/Addicto, annales/) ET en D2-T2 (Psy/Addicto aussi) :
    # ambiguïté réelle, laissée à vérifier manuellement (cf. avertissement console).
    "3": ("Psychiatrie / Addictologie — VERIFIER D1 vs D2-T2", "annales OU d2/t2"),
}

MONTHS_FR = {
    "JANVIER": "janvier", "JAN": "janvier",
    "FEVRIER": "février", "FÉVRIER": "février", "FEV": "février", "FÉV": "février",
    "MARS": "mars",
    "AVRIL": "avril", "AVR": "avril",
    "MAI": "mai",
    "JUIN": "juin",
    "JUILLET": "juillet", "JUIL": "juillet",
    "AOUT": "août", "AOÛT": "août", "AOU": "août",
    "SEPTEMBRE": "septembre", "SEP": "septembre", "SEPT": "septembre",
    "OCTOBRE": "octobre", "OCT": "octobre",
    "NOVEMBRE": "novembre", "NOV": "novembre",
    "DECEMBRE": "décembre", "DÉCEMBRE": "décembre", "DEC": "décembre", "DÉC": "décembre",
}

TYPE_MAP = {
    "QRM": "QRM", "QCM": "QRM",
    "QRU": "QRU", "QCS": "QRU",
    "QROC": "QROC",
    "QTCS": "TCS", "TCS": "TCS",
    "QRPL": "QRPL",
}

# ----------------------------------------------------------------------------
# 1. Nettoyage du texte brut (en-têtes/pieds de page répétés à chaque page PDF)
# ----------------------------------------------------------------------------

# Chaque page du PDF répète un bloc "furniture" (date, version, pagination,
# référence/session). L'ORDRE de ces 4 champs varie selon la plateforme/export
# (observé dans les deux sens : Date+Version+Page avant OU après Référence+Session) :
# on les élimine donc CHACUN INDÉPENDAMMENT plutôt qu'avec un seul bloc figé,
# pour rester robuste peu importe l'ordre réel du PDF traité.
NOISE_FIELD_RES = [
    re.compile(r"Date de création\s*:\s*[\d\-:]+\s*"),
    re.compile(r"Version\s*:\s*\d+\s*"),
    re.compile(r"Page\s*:\s*\d+\s*/\s*\d+\s*"),
    # Référence/Session : bornée à quelques tokens pour éviter de dévorer du
    # texte de question légitime si ces mots apparaissaient par ailleurs.
    re.compile(r"Référence\s*:\s*\S+\s+Session\s*:\s*(?:Session\s+)?\S+\s*"),
]

LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl",
}


def fix_ligatures(text: str) -> str:
    for lig, rep in LIGATURES.items():
        text = text.replace(lig, rep)
    return text


def strip_noise(text: str) -> str:
    text = fix_ligatures(text)
    for rx in NOISE_FIELD_RES:
        text = rx.sub(" ", text)
    return text


def clean_span(text: str) -> str:
    """Collapse whitespace within a captured stem/option snippet."""
    text = re.sub(r"\x00PAGE\d+\x00", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ----------------------------------------------------------------------------
# 2. Regex de structure
# ----------------------------------------------------------------------------

SECTION_RE = re.compile(r"Element d'épreuve\s*:\s*(\S+)\s+[\d.]+\s*/\s*20")
QUESTION_RE = re.compile(
    r"Question\s+([A-Z]+|\d+)\s*:\s*\(Type\s*:\s*(\w+)\)\s*[\d.]+\s*/\s*1\s*(Question neutralisée)?"
)
OPTION_START_RE = re.compile(r"[☐☑◎◉]")
# Regex de découpe par entrée d'option. La case (☐/☑/◎/◉) est optionnelle car
# elle peut apparaître APRÈS le libellé "Valide X." en cas de saut de page dans
# le PDF (la colonne des cases est lue séparément de la colonne de texte par
# PyMuPDF). On gère aussi le label "Inacceptable" (4e label de certaines
# plateformes, traité comme Faux côté validité).
_OPT_ENTRY_RE = re.compile(
    r"([☐☑◎◉])?\s*(Faux|Valide|Indispensable|Inacceptable)\s+([A-Z])\.\s*"
)
_STRAY_GLYPH_RE = re.compile(r"[☐☑◎◉]")
REPONSES_VALIDES_RE = re.compile(r"Réponses\s+valides\s*:\s*(.+?)\(\d+\)", re.DOTALL)
SELECT_N_RE = re.compile(r"[Ss]électionnez\s*(jusqu.à\s*)?(\d+)\s*items?")
REPONSES_ATTENDUES_RE = re.compile(r"\(\s*(\d+)\s*réponses?\s*attendues?\s*\)", re.IGNORECASE)
EPREUVE_RE = re.compile(r"Epreuve\s*:\s*(\S+)")


# ----------------------------------------------------------------------------
# 3. Parsing
# ----------------------------------------------------------------------------

def split_trailing_paren(text):
    """Sépare un texte d'option de sa justification entre parenthèses en fin de
    chaîne (ex: "Hépatite alcoolique (les transaminases ne dépassent jamais...)").
    Cette justification du jury est fréquente dans les PDF source et, non
    séparée, se retrouve collée à l'intitulé de l'option — illisible.

    Gère les parenthèses imbriquées (ex: une justification qui cite elle-même
    des exemples entre parenthèses) en comptant la profondeur depuis la fin.

    Ignore volontairement :
    - les sigles/abréviations sans espace, ex "(DCI)", "(AMM)", "(s)" de pluriel ;
    - les valeurs/normes biologiques, ex "(N < 40)", "(N<0,010)" — qui contiennent
      bien un espace mais aucun mot français réel, seulement des symboles/nombres.
    Ces deux cas font partie intégrante du texte de l'option, pas d'une
    justification à extraire.
    """
    t = text.rstrip()
    if not t.endswith(")"):
        return text, None
    depth = 0
    start = None
    for i in range(len(t) - 1, -1, -1):
        c = t[i]
        if c == ")":
            depth += 1
        elif c == "(":
            depth -= 1
            if depth == 0:
                start = i
                break
    if start is None:
        return text, None
    note = t[start + 1: -1].strip()
    main = t[:start].rstrip()
    # Une vraie justification contient au moins un mot français de 4 lettres ou
    # plus (pas seulement des symboles/valeurs comme "N", "<", "40").
    has_word = re.search(r"[A-Za-zÀ-ÿ]{4,}", note) is not None
    if not main or " " not in note or not has_word:
        return text, None
    return main, note


def parse_option_block(blob):
    # Pré-nettoyer les marqueurs de page et le bruit PDF avant l'analyse.
    # Sans ce nettoyage, un saut de page entre la case ☐ et son libellé
    # "Valide X." (possible quand les deux colonnes sont lues séparément par
    # PyMuPDF) fait rater la correspondance et absorbe l'option dans la
    # précédente (bug confirmé sur mDP2-Q5 de l'annale UE 7.1 JUIN23).
    clean_blob = re.sub(r"\x00PAGE\d+\x00", " ", blob)
    for rx in NOISE_FIELD_RES:
        clean_blob = rx.sub(" ", clean_blob)

    entries = list(_OPT_ENTRY_RE.finditer(clean_blob))
    if not entries:
        return []

    opts = []
    for i, em in enumerate(entries):
        glyph    = em.group(1)  # None si la case est après le libellé (saut de page)
        validity = em.group(2)
        letter   = em.group(3)

        # Texte de l'option : de la fin de ce match jusqu'au début du suivant.
        text_start = em.end()
        text_end   = entries[i + 1].start() if i + 1 < len(entries) else len(clean_blob)
        raw_text   = clean_blob[text_start:text_end]

        # Cas "case après libellé" (saut de page) : chercher la case orpheline
        # dans la fenêtre entre la fin de l'entrée précédente et ce libellé.
        if glyph is None and i > 0:
            prev_end = entries[i - 1].end()
            window   = clean_blob[prev_end : em.start()]
            strays   = _STRAY_GLYPH_RE.findall(window)
            if strays:
                glyph = strays[-1]

        # Supprimer les cases parasites restantes du texte (résidus du saut de page).
        raw_text  = _STRAY_GLYPH_RE.sub("", raw_text)
        text      = clean_span(raw_text)
        main_text, expl = split_trailing_paren(text)

        opts.append({
            "letter":  letter,
            "valid":   validity in ("Valide", "Indispensable"),
            # Case cochée = réponse choisie par CET étudiant (indice pour resolve_qru).
            "checked": glyph in ("☑", "◉") if glyph else False,
            "expl":    expl,
            "text":    main_text,
        })
    return opts


def parse_qroc_block(blob):
    m = REPONSES_VALIDES_RE.search(blob)
    if not m:
        return clean_span(blob), []
    answers_blob = m.group(1)
    stem_and_junk = blob[: m.start()]
    idx = stem_and_junk.rfind("?")
    stem = stem_and_junk[: idx + 1] if idx != -1 else stem_and_junk
    stem = clean_span(stem)
    answers = [clean_span(a) for a in answers_blob.split(",")]
    answers = [a.rstrip(".").strip() for a in answers if a.strip()]
    return stem, answers


def parse_question(qtype_raw, neutralized, raw_block, warnings, section_code, qnum):
    qtype = TYPE_MAP.get(qtype_raw.upper())
    if qtype is None:
        warnings.append(
            f"{section_code} Q{qnum}: type inconnu '{qtype_raw}', traité comme QRM."
        )
        qtype = "QRM"

    q = {
        "type": qtype,
        "neutralized": bool(neutralized),
        "stem": "",
        "options": [],
        "qroc_answers": [],
        "select_n": None,
        "select_max": False,
    }

    if qtype == "QROC":
        stem, answers = parse_qroc_block(raw_block)
        q["stem"] = stem
        q["qroc_answers"] = answers
        if not answers:
            warnings.append(f"{section_code} Q{qnum} (QROC): aucune réponse attendue détectée.")
        return q

    m = OPTION_START_RE.search(raw_block)
    if m:
        stem = raw_block[: m.start()]
        opts_blob = raw_block[m.start():]
    else:
        # Fallback : PDF sans glyphes ☐/☑ — les options commencent directement par
        # "Valide A." / "Faux A." (format lettre-sans-case, ex. exports DEC22).
        first_opt = _OPT_ENTRY_RE.search(raw_block)
        if first_opt:
            stem = raw_block[: first_opt.start()]
            opts_blob = raw_block[first_opt.start():]
        else:
            stem = raw_block
            opts_blob = ""

    q["stem"] = clean_span(stem)
    q["options"] = parse_option_block(opts_blob)

    if not q["options"]:
        warnings.append(f"{section_code} Q{qnum}: aucune option détectée — à vérifier manuellement.")

    # La justification du jury est parfois collée à l'intitulé SANS parenthèses
    # (donc invisible pour split_trailing_paren) : rencontré en pratique sur des
    # options d'ordinaire courtes qui deviennent anormalement longues. On ne
    # tente pas de deviner le point de coupure (risque de mal couper une phrase
    # légitimement longue) — on signale juste pour relecture manuelle.
    for o in q["options"]:
        if o.get("expl") is None and len(o["text"]) > 100:
            warnings.append(
                f"{section_code} Q{qnum} option {o['letter']}: texte long ({len(o['text'])} car.) "
                f"sans justification entre parenthèses détectée — vérifier qu'une explication du "
                f"jury n'est pas collée sans séparateur à l'intitulé."
            )

    # Le tag "(Type: ...)" du PDF source est incohérent d'une plateforme à l'autre :
    # certains exports taguent ces questions "QRM" (avec "Sélectionnez (jusqu'à) N
    # items" dans l'énoncé), d'autres taguent directement "QRPL" mais formulent le
    # nombre attendu différemment ("(N réponses attendues)"). On détecte donc le
    # nombre via les deux formulations connues, indépendamment du tag brut.
    sm = SELECT_N_RE.search(stem)
    ra = REPONSES_ATTENDUES_RE.search(stem)
    if (sm or ra) and qtype in ("QRM", "QRPL"):
        qtype = q["type"] = "QRPL"
        if sm:
            q["select_max"] = bool(sm.group(1))
            q["select_n"] = int(sm.group(2))
        else:
            q["select_max"] = False
            q["select_n"] = int(ra.group(1))
    elif qtype == "QRPL" and not sm and not ra:
        warnings.append(f"{section_code} Q{qnum} (QRPL): nombre de réponses attendues non détecté.")

    # Une QRM avec une seule lettre valide et plusieurs options est souvent en
    # réalité une question à réponse unique mal taguée par la plateforme
    # source (rencontré en pratique) : on ne corrige pas automatiquement
    # (risque de faux positif sur une vraie QRM à réponse unique), mais on
    # signale pour relecture manuelle.
    if q["type"] == "QRM" and len(q["options"]) > 1:
        n_valid = sum(1 for o in q["options"] if o["valid"])
        if n_valid == 1:
            warnings.append(
                f"{section_code} Q{qnum}: QRM avec une seule réponse valide — "
                f"vérifie si ce n'est pas en réalité une QRU (choix unique)."
            )

    return q


def parse_sections(full_text, warnings):
    sections = []
    sec_matches = list(SECTION_RE.finditer(full_text))
    for i, sm in enumerate(sec_matches):
        code = sm.group(1)
        start = sm.end()
        end = sec_matches[i + 1].start() if i + 1 < len(sec_matches) else len(full_text)
        block = full_text[start:end]

        q_matches = list(QUESTION_RE.finditer(block))
        dpctx = clean_span(block[: q_matches[0].start()]) if q_matches else ""

        questions = []
        for j, qm in enumerate(q_matches):
            qnum_raw = qm.group(1)
            qnum = int(qnum_raw) if qnum_raw.isdigit() else qnum_raw
            qtype_raw = qm.group(2)
            neutralized = qm.group(3)
            qstart = qm.end()
            qend = q_matches[j + 1].start() if j + 1 < len(q_matches) else len(block)
            raw = block[qstart:qend]
            q = parse_question(qtype_raw, neutralized, raw, warnings, code, qnum)
            q["num"] = qnum
            questions.append(q)

        if not questions:
            warnings.append(f"Section {code}: aucune question détectée.")

        sections.append({"code": code, "dpctx": dpctx, "questions": questions})
    if not sections:
        warnings.append("Aucune section ('Element d'épreuve: ...') détectée dans le PDF.")
    return sections


# ----------------------------------------------------------------------------
# 4. Résolution des bonnes réponses / génération HTML
# ----------------------------------------------------------------------------

def resolve_qru(options):
    """Retourne (lettre_principale, lettres_alternatives_valides).

    Priorité à l'option cochée par l'étudiant SI elle est valide (c'est le
    meilleur indice disponible de la réponse "canonique" mise en avant par
    la plateforme) ; sinon on retombe sur la première option valide.
    Quand plusieurs options sont marquées Valide (TCS à réponses multiples
    acceptées par le jury), les lettres non retenues comme primaire sont
    remontées en "extra" pour être mentionnées dans une note.
    """
    valid_letters = [o["letter"] for o in options if o["valid"]]
    checked = next((o for o in options if o.get("checked")), None)
    if checked is not None and checked["valid"]:
        primary = checked["letter"]
    elif valid_letters:
        primary = valid_letters[0]
    else:
        primary = options[0]["letter"] if options else "A"
    extra = [l for l in valid_letters if l != primary]
    return primary, extra


def esc(s):
    return html.escape(s or "", quote=False)


def build_option_notes(opts):
    """Regroupe les justifications par option (extraites par split_trailing_paren)
    en un unique <div class="note"> lisible, une ligne par option concernée.
    Réservé au TCS (cf. render_citems pour QRM/QRPL/QRU classiques)."""
    parts = [f'{o["letter"]} — {esc(o["expl"])}' for o in opts if o.get("expl")]
    if not parts:
        return ""
    return '<div class="note">' + '<br>'.join(parts) + '</div>'


def render_citems(opts):
    """Rendu "VRAI/FAUX + justification" par option, au format des annales D1
    (.citem / .v-vrai / .v-faux) : chaque option affiche son verdict et, si
    disponible, sa justification extraite par split_trailing_paren. N'est PAS
    utilisé pour les TCS, dont les options (improbable/.../certain) ne sont pas
    des affirmations vraies/fausses."""
    rows = []
    for o in opts:
        verdict = "VRAI" if o["valid"] else "FAUX"
        cls = "v-vrai" if o["valid"] else "v-faux"
        tail = f' — {esc(o["expl"])}' if o.get("expl") else ""
        rows.append(
            f'<div class="citem {cls}"><span class="cl">{o["letter"]}.</span> '
            f'<span class="cv">{verdict}</span>{tail}</div>'
        )
    return "\n".join(rows)


def render_option_li(opt):
    return (
        f'<li class="opt" data-l="{opt["letter"]}" data-correct="{1 if opt["valid"] else 0}">'
        f'<span class="box">{opt["letter"]}</span><span class="otext">{esc(opt["text"])}</span></li>'
    )


def render_question(section_code, q, image_html=""):
    qid = f'{section_code}-Q{q["num"]}'
    qnum_label = f'{section_code} Q{q["num"]}'
    dpctx_html = ""

    if q["type"] == "QROC":
        answers = q["qroc_answers"] or ["[A VERIFIER — réponse non détectée]"]
        primary, *alt = answers
        alt_html = f" ({', '.join(alt)})" if alt else ""
        return f'''<div class="q" id="{qid}" data-correct="" data-type="QROC">
<div class="qhead"><span class="qnum">{qnum_label}</span><span class="qtype">QROC</span><span class="status" aria-live="polite"></span></div>
{dpctx_html}<div class="stem">{esc(q["stem"])}</div>
{image_html}<textarea class="qrocin" rows="2" placeholder="Votre réponse…"></textarea>
<div class="actions"><button class="show" type="button">Voir la réponse</button></div>
<div class="correction" hidden>
<div class="qrocans">Réponse attendue : {esc(primary)}{esc(alt_html)}</div>
</div>
</div>'''

    opts = q["options"]
    neutral_note = ' <div class="note">Question neutralisée : tous les items sont comptés valides.</div>' if q["neutralized"] else ""

    if q["type"] == "QRU" or q["type"] == "TCS":
        primary, extra = resolve_qru(opts)
        badge = "TCS" if q["type"] == "TCS" else "QRU"
        opts_html = "\n".join(render_option_li(o) for o in opts)
        primary_opt = next((o for o in opts if o["letter"] == primary), None)

        if q["type"] == "TCS":
            # Options du TCS = degrés de probabilité (improbable...certain), pas des
            # affirmations vraies/fausses : on garde le format "réponse + note jury".
            ans_text = f'{primary}' + (f' — {esc(primary_opt["text"])}' if primary_opt else "")
            extra_note = ""
            if extra:
                extra_note = f'<div class="note">Réponse(s) {", ".join(extra)} également valorisée(s) par le jury.</div>'
            option_notes = build_option_notes(opts)
            correction = f'<div class="ans">Réponse : {ans_text}</div>{extra_note}{option_notes}{neutral_note}'
        else:
            # QRU clinique classique : verdict VRAI/FAUX par option, au format D1.
            citems = render_citems(opts)
            correction = f'<div class="ans">Réponse : {primary}</div>{neutral_note}\n{citems}'

        return f'''<div class="q" id="{qid}" data-correct="{primary}" data-type="QRU">
<div class="qhead"><span class="qnum">{qnum_label}</span><span class="qtype">{badge}</span><span class="status" aria-live="polite"></span></div>
{dpctx_html}<div class="stem">{esc(q["stem"])}</div>
{image_html}<ul class="opts">
{opts_html}
</ul>
<div class="actions"><button class="validate">Valider</button><button class="show" type="button">Voir la réponse</button></div>
<div class="correction" hidden>{correction}</div>
</div>'''

    # QRM / QRPL
    correct_letters = "".join(o["letter"] for o in opts if o["valid"])
    badge = "QRM"
    if q["type"] == "QRPL":
        n = q["select_n"]
        if n:
            badge = f'QRPL · {n} réponse{"s" if n > 1 else ""}' + (" max" if q["select_max"] else "")
        else:
            badge = "QRPL"
    opts_html = "\n".join(render_option_li(o) for o in opts)
    ans_display = ", ".join(correct_letters) if correct_letters else "[A VERIFIER]"
    citems = render_citems(opts)
    return f'''<div class="q" id="{qid}" data-correct="{correct_letters}" data-type="QRM">
<div class="qhead"><span class="qnum">{qnum_label}</span><span class="qtype">{badge}</span><span class="status" aria-live="polite"></span></div>
{dpctx_html}<div class="stem">{esc(q["stem"])}</div>
{image_html}<ul class="opts">
{opts_html}
</ul>
<div class="actions"><button class="validate">Valider</button><button class="show" type="button">Voir la réponse</button></div>
<div class="correction" hidden><div class="ans">Réponse : {ans_display}</div>{neutral_note}
{citems}
</div>
</div>'''


HTML_TEMPLATE = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quiz — {title_plain}</title><style>
:root{{--bg:#f5f6f4;--card:#fff;--ink:#132025;--mut:#5b6b73;--line:#dfe4e2;--vrai:#15803d;--vraibg:#eaf7ef;--faux:#b91c1c;--fauxbg:#fbeceb;--neu:#b45309;--acc:#4f46e5;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
header{{position:sticky;top:0;z-index:5;background:rgba(245,246,244,.95);backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:14px 18px}}
.wrap,.hwrap{{max-width:820px;margin:0 auto;padding:0 16px 80px}}
h1{{font-size:20px;font-weight:600;margin:0}}
.sub{{color:var(--mut);font-size:13px;margin-top:2px}}
.scorebar{{max-width:820px;margin:8px auto 0;display:flex;gap:10px;flex-wrap:wrap;align-items:center;font-size:14px}}
.pill{{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:4px 12px}}
.pill b{{color:var(--acc)}}
.sect{{font-size:14px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--mut);margin:30px 2px 10px}}
.dpctx{{background:#eef2ff;border:1px solid #dbe4ff;border-left:4px solid var(--acc);border-radius:10px;padding:12px 16px;font-size:14px;color:#1e2a5e;margin-bottom:16px}}
.q{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:0 0 16px;scroll-margin-top:90px}}
.q.done{{border-color:#cfcdc4}}
.q.locked{{opacity:.2;filter:blur(3px);pointer-events:none;user-select:none}}
.q{{transition:opacity .35s ease,filter .35s ease}}
.qhead{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.qnum{{font-size:12px;font-weight:600;color:#fff;background:var(--acc);border-radius:6px;padding:2px 8px}}
.qtype{{font-size:11px;font-weight:600;color:var(--mut);border:1px solid var(--line);border-radius:5px;padding:1px 6px}}
.status{{margin-left:auto;font-size:13px;font-weight:600}}
.status.ok{{color:var(--vrai)}}.status.ko{{color:var(--faux)}}.status.rl{{color:var(--mut)}}.status.part{{color:var(--neu)}}
.stem{{font-weight:500;margin-bottom:10px}}
.opts{{list-style:none;margin:0;padding:0}}
.opt{{display:flex;gap:10px;align-items:flex-start;border:1px solid var(--line);border-radius:9px;padding:9px 11px;margin:7px 0;cursor:pointer;transition:.12s}}
.opt:hover{{border-color:#c7d2fe;background:#f8f9ff}}
.opt .box{{flex:none;width:24px;height:24px;border:1.5px solid #b9b7ad;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;color:var(--mut)}}
.opt.sel{{border-color:var(--acc);background:#eef2ff}}
.opt.sel .box{{background:var(--acc);border-color:var(--acc);color:#fff}}
.q.done .opt{{cursor:default}}
.opt.correct{{border-color:var(--vrai);background:var(--vraibg)}}
.opt.correct .box{{background:var(--vrai);border-color:var(--vrai);color:#fff}}
.opt.wrong{{border-color:var(--faux);background:var(--fauxbg)}}
.opt.wrong .box{{background:var(--faux);border-color:var(--faux);color:#fff}}
.opt.missed{{border-style:dashed;border-color:var(--vrai)}}
.opt.missed .box{{color:var(--vrai);border-color:var(--vrai)}}
.mark{{margin-left:auto;font-size:13px;font-weight:600;align-self:center}}
.qrocin{{width:100%;font:inherit;font-size:15px;padding:9px 11px;border:1px solid var(--line);border-radius:9px;background:#fff}}
.qrocin:focus{{outline:none;border-color:var(--acc);box-shadow:0 0 0 3px #eef2ff}}
.qrocans{{color:var(--vrai);font-weight:600}}
.actions{{display:flex;gap:8px;margin-top:10px}}
button{{font:inherit;font-size:14px;border:1px solid var(--line);background:#fff;border-radius:8px;padding:7px 16px;cursor:pointer}}
button.validate{{background:var(--acc);color:#fff;border-color:var(--acc);font-weight:500}}
button.validate:hover{{filter:brightness(1.05)}}
button.show:hover{{background:#e0e7ff}}
button:disabled{{opacity:.5;cursor:default}}
.correction{{margin-top:12px;border-top:1px dashed var(--line);padding-top:10px}}
.ans{{font-weight:600;margin-bottom:8px}}
.note{{background:#fffaeb;border:1px solid #fedf89;border-left:3px solid #b45309;border-radius:9px;padding:10px 14px;font-size:13.5px;margin:8px 0 10px;color:#6b3d0a}}
.citem{{font-size:14.5px;padding:5px 0;border-bottom:1px solid #f0efe9}}
.citem:last-child{{border-bottom:0}}
.cl{{font-weight:600}}
.v-vrai .cv{{color:var(--vrai);font-weight:600}}
.v-faux .cv{{color:var(--faux);font-weight:600}}
.back{{display:inline-block;margin-top:32px;color:var(--acc);font-size:14px;font-weight:500;text-decoration:none}}
.back:hover{{text-decoration:underline}}
.q{{border-radius:16px;box-shadow:0 1px 2px rgba(16,24,40,.05),0 1px 3px rgba(16,24,40,.06)}}
.opt{{border-radius:12px}}
.opt .box{{border-radius:8px}}
.q[data-type="QRU"] .opt .box{{border-radius:999px}}
.qnum{{border-radius:7px}}
button{{border-radius:10px}}
button.validate{{background:var(--acc);border-color:var(--acc);color:#fff}}
button.validate:hover{{filter:brightness(1.08)}}
header{{box-shadow:0 1px 2px rgba(16,24,40,.04)}}
</style></head><body>
<header><div class="hwrap">
<h1>{title_html}</h1>
<div class="sub">{sub_html}</div>
<div class="scorebar">
<span class="pill">Validées : <b id="s-done">0/{total_q}</b></span>
<span class="pill">Score : <b id="s-ok">0/{graded_q}</b></span>
<span class="pill"><button id="revealall" style="padding:2px 10px">Tout révéler</button></span>
<span class="pill"><button id="reset" style="padding:2px 10px">Recommencer</button></span>
</div>
</div></header>
<div class="wrap">

{body_html}

<a class="back" href="index.html">← Retour</a>
</div>

<script>
const $ = s => document.querySelectorAll(s);
function fmtPts(p){{return(Math.round(p*100)/100).toString().replace('.',',')}}
function qPoints(disc,isQRU){{if(isQRU)return disc===0?1:0;return disc===0?1:(disc===1?0.5:(disc===2?0.2:0))}}

function grade(q){{
  if(q.dataset.type==='QROC')return;
  const correct=new Set(q.dataset.correct.split(''));
  const sel=new Set([...q.querySelectorAll('.opt.sel')].map(o=>o.dataset.l));
  let disc=0;
  q.querySelectorAll('.opt').forEach(o=>{{
    const l=o.dataset.l,isC=correct.has(l),isS=sel.has(l);
    o.classList.remove('sel');
    if(isC&&isS)o.classList.add('correct');
    else if(!isC&&isS){{o.classList.add('wrong');disc++;}}
    else if(isC&&!isS){{o.classList.add('missed');disc++;}}
    let m=document.createElement('span');m.className='mark';
    if(isC&&isS)m.textContent='✓';
    else if(!isC&&isS)m.textContent='✗';
    else if(isC&&!isS){{m.textContent='manqué';m.style.color='var(--vrai)';}}
    if(m.textContent)o.appendChild(m);
  }});
  const isQRU=q.dataset.type==='QRU';
  const pts=qPoints(disc,isQRU);
  q.classList.add('done');
  q.querySelector('.correction').hidden=false;
  const st=q.querySelector('.status');st.style.color='';
  st.textContent=fmtPts(pts)+' / 1';
  if(!isQRU&&disc>0)st.textContent+=' ('+disc+' incohérence'+(disc>1?'s':'')+')';
  st.className='status '+(pts===1?'ok':(pts===0?'ko':'part'));
  if(pts>0&&pts<1)st.style.color='#9a6a00';
  q.querySelector('.validate').disabled=true;
  q.dataset.pts=pts;q.dataset.result=pts===1?'1':'0';
  updateScore();unlockNext(q);
}}

function reveal(q,skipUnlock){{
  if(q.classList.contains('done'))return;
  if(q.dataset.type!=='QROC'){{
    const correct=new Set(q.dataset.correct.split(''));
    q.querySelectorAll('.opt').forEach(o=>{{o.classList.remove('sel');if(correct.has(o.dataset.l))o.classList.add('correct');}});
    const v=q.querySelector('.validate');if(v)v.disabled=true;
  }}else{{
    const st=q.querySelector('.status');st.textContent='révélée';st.className='status rl';
  }}
  q.classList.add('done');q.querySelector('.correction').hidden=false;
  if(q.dataset.pts===undefined)q.dataset.result='skip';
  updateScore();if(!skipUnlock)unlockNext(q);
}}

function updateScore(){{
  const qs=[...$('.q')];const all=qs.length;
  const done=qs.filter(q=>q.classList.contains('done')).length;
  const grad=qs.filter(q=>q.dataset.type!=='QROC').length;
  let pts=0;
  qs.forEach(q=>{{if(q.dataset.pts!==undefined&&q.dataset.pts!=='')pts+=parseFloat(q.dataset.pts);}});
  const sd=document.getElementById('s-done');if(sd)sd.textContent=done+'/'+all;
  const so=document.getElementById('s-ok');if(so)so.textContent=fmtPts(pts)+'/'+grad;
}}

document.addEventListener('click',e=>{{
  const li=e.target.closest('.opt');
  if(li){{
    const q=li.closest('.q');
    if(!q.classList.contains('done')){{
      if(q.dataset.type==='QRU'){{q.querySelectorAll('.opt').forEach(o=>o.classList.remove('sel'));li.classList.add('sel');}}
      else{{li.classList.toggle('sel');}}
    }}
    return;
  }}
  const v=e.target.closest('.validate');if(v){{grade(v.closest('.q'));return;}}
  const s=e.target.closest('.show');if(s){{reveal(s.closest('.q'));return;}}
}});

function initLocks(){{
  let nextFree=false,inDP=false;
  for(const el of document.querySelector('.wrap').children){{
    if(el.classList.contains('sect')){{inDP=/DP|KFP|TCS/.test(el.textContent);nextFree=inDP;continue;}}
    if(el.classList.contains('q')){{if(nextFree){{nextFree=false;}}else if(inDP){{el.classList.add('locked');}}}}
  }}
}}

function unlockNext(q){{
  let el=q.nextElementSibling;
  while(el){{
    if(el.classList.contains('sect'))break;
    if(el.classList.contains('q')&&el.classList.contains('locked')){{
      el.classList.remove('locked');
      setTimeout(()=>el.scrollIntoView({{behavior:'smooth',block:'nearest'}}),100);
      break;
    }}
    el=el.nextElementSibling;
  }}
}}

const rb=document.getElementById('reset');if(rb)rb.addEventListener('click',()=>location.reload());
const ra=document.getElementById('revealall');if(ra)ra.addEventListener('click',()=>{{
  $('.q.locked').forEach(q=>q.classList.remove('locked'));
  $('.q').forEach(q=>reveal(q,true));
}});
initLocks();updateScore();
</script>
</body></html>
"""


def build_html(sections, title_html, title_plain, sub_html, images_by_qid=None):
    images_by_qid = images_by_qid or {}
    total_q = sum(len(s["questions"]) for s in sections)
    graded_q = sum(1 for s in sections for q in s["questions"] if q["type"] != "QROC")

    body_parts = []
    for s in sections:
        body_parts.append(f'<div class="sect">{esc(s["code"])}</div>')
        if s["dpctx"]:
            # dpctx affiché uniquement sur la 1re question (cf. gabarit BobMed) :
            # on l'injecte manuellement dans le rendu de la 1re question ci-dessous.
            pass
        for i, q in enumerate(s["questions"]):
            qid = f'{s["code"]}-Q{q["num"]}'
            img_html = images_by_qid.get(qid, "")
            block = render_question(s["code"], q, image_html=img_html)
            if i == 0 and s["dpctx"]:
                block = block.replace(
                    '<div class="stem">',
                    f'<div class="dpctx">{esc(s["dpctx"])}</div>\n<div class="stem">',
                    1,
                )
            body_parts.append(block)

    body_html = "\n\n".join(body_parts)
    return HTML_TEMPLATE.format(
        title_plain=esc(title_plain),
        title_html=esc(title_html),
        sub_html=sub_html,
        total_q=total_q,
        graded_q=graded_q,
        body_html=body_html,
    )


# ----------------------------------------------------------------------------
# 5. Titre / métadonnées à partir du code d'épreuve
# ----------------------------------------------------------------------------

def guess_metadata(epreuve_code, warnings):
    """epreuve_code ex: 'DFA1-UE8.1-DECEMBRE2023' ou 'DFA1-UE8.1-JUILLET2024-RATTRAPAGE'"""
    ue_m = re.search(r"UE(\d+(?:\.\d+)?)", epreuve_code, re.IGNORECASE)
    ue = ue_m.group(1) if ue_m else None

    month, year = None, None
    for key, val in MONTHS_FR.items():
        # Accepte 2 ou 4 chiffres : certains exports encodent l'année sur 2 chiffres
        # (ex : "JUIN23" au lieu de "JUIN2023") — on normalise en ajoutant 2000.
        m = re.search(rf"{key}(\d{{2,4}})", epreuve_code, re.IGNORECASE)
        if m:
            yr = int(m.group(1))
            if yr < 100:
                yr += 2000
            month, year = val, yr
            break

    rattrapage = "RATTRAP" in epreuve_code.upper()
    is_d2 = epreuve_code.upper().startswith("DFA")

    if ue is None:
        warnings.append(f"Code UE non détecté dans '{epreuve_code}' — à renseigner manuellement.")
    if month is None:
        warnings.append(f"Mois/année non détectés dans '{epreuve_code}' — à renseigner manuellement.")

    topic, folder = UE_MAP.get(ue, ("[À COMPLETER]", "[À COMPLETER]"))

    if year is not None:
        acad_year = f"{year}-{year+1}" if (month and MONTHS_FR.get(month.upper(), "") ) else f"{year}"
        # règle académique : mois >= septembre -> année N/N+1, sinon (N-1)/N
        month_num = {
            "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
            "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
        }.get(month, 1)
        if month_num >= 9:
            acad_year = f"{year}-{year+1}"
        else:
            acad_year = f"{year-1}-{year}"
    else:
        acad_year = "[ANNEE]"

    session_label = "Rattrapage" if rattrapage else "Session normale"
    suffix = "S2" if rattrapage else "S1"
    # Pour les sessions de début d'année académique (oct-jan), ajouter le mois dans le
    # nom de fichier pour éviter les collisions avec la session de fin d'année (S1 de juin).
    month_num_for_suffix = {
        "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
    }.get(month, 0) if month else 0
    if not rattrapage and month_num_for_suffix >= 10:
        suffix = f"S1_{month}"
    elif not rattrapage and month_num_for_suffix == 1:
        suffix = "S1_janvier"

    title_html = f"UE {ue or '?'} — {topic} · {session_label}" + (f" ({month} {year})" if month else "")
    filename = f"Quiz_UE{ue or 'X'}_{acad_year}_{suffix}.html"

    return {
        "ue": ue, "topic": topic, "folder": folder,
        "month": month, "year": year, "acad_year": acad_year,
        "rattrapage": rattrapage, "is_d2_guess": is_d2,
        "title_html": title_html, "filename": filename,
    }


# ----------------------------------------------------------------------------
# 6. Point d'entrée
# ----------------------------------------------------------------------------

def run(pdf_path, debug=False):
    warnings = []
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ERREUR : le module PyMuPDF n'est pas installé.")
        print("Lance d'abord :  pip install pymupdf")
        sys.exit(1)

    if not os.path.isfile(pdf_path):
        print(f"ERREUR : fichier introuvable : {pdf_path}")
        sys.exit(1)

    doc = fitz.open(pdf_path)
    page_texts = []
    pages_images = []   # [(ext, data), …] par page — utilisé en fallback
    image_events = []   # (page, y, ext, data) — pour l'assignation positionnelle
    q_page_y = []       # (page, y) de chaque bloc "Question N: (Type:" dans le PDF
    _Q_BLOCK_RE = re.compile(r'Question\s+(?:[A-Z]+|\d+)\s*:\s*\(Type', re.IGNORECASE)
    for pno, page in enumerate(doc):
        page_texts.append(page.get_text())
        imgs = []
        try:
            for info in page.get_image_info(xrefs=True):
                w, h = info.get("width", 0), info.get("height", 0)
                if w < 100 or h < 100:
                    continue
                xref = info["xref"]
                try:
                    extracted = doc.extract_image(xref)
                    imgs.append((extracted["ext"], extracted["image"]))
                    image_events.append((pno, info["bbox"][1], extracted["ext"], extracted["image"]))
                except Exception:
                    continue
        except AttributeError:
            # PyMuPDF < 1.18 : pas de get_image_info → fallback sans position y
            for img in page.get_images(full=True):
                xref = img[0]
                try:
                    info = doc.extract_image(xref)
                    if info.get("width", 0) < 100 or info.get("height", 0) < 100:
                        continue
                    imgs.append((info["ext"], info["image"]))
                except Exception:
                    continue
        pages_images.append(imgs)
        for block in page.get_text("dict")["blocks"]:
            if block["type"] == 0:
                bt = "".join(s["text"] for ln in block["lines"] for s in ln["spans"])
                if _Q_BLOCK_RE.search(bt):
                    q_page_y.append((pno, block["bbox"][1]))
    doc.close()

    raw_first_page = page_texts[0] if page_texts else ""
    epr_m = EPREUVE_RE.search(raw_first_page)
    epreuve_code = epr_m.group(1) if epr_m else ""
    if not epreuve_code:
        warnings.append("Ligne 'Epreuve: ...' introuvable en page 1 — titre non déductible automatiquement.")

    full_text = "".join(
        f"\x00PAGE{i}\x00{t}" for i, t in enumerate(page_texts)
    )
    full_text = strip_noise(full_text)

    sections = parse_sections(full_text, warnings)

    # Images : assignées par position (page × ordonnée y) pour gérer correctement
    # les questions dont les illustrations s'étalent sur plusieurs pages PDF.
    images_by_qid = {}
    if any(pages_images):
        page_marker_re = re.compile(r"\x00PAGE(\d+)\x00")
        cursor_text = "".join(f"\x00PAGE{i}\x00{t}" for i, t in enumerate(page_texts))
        raw_positions = [m.start() for m in re.finditer(r"Question\s+(?:[A-Z]+|\d+)\s*:\s*\(Type", cursor_text)]
        marks = [(m.start(), int(m.group(1))) for m in page_marker_re.finditer(cursor_text)]

        def page_at(offset):
            p = 0
            for pos, num in marks:
                if pos <= offset:
                    p = num
                else:
                    break
            return p

        flat_q_ids = [f'{s["code"]}-Q{q["num"]}' for s in sections for q in s["questions"]]

        if image_events and len(q_page_y) == len(flat_q_ids):
            # Approche positionnelle : trie toutes les questions et images par (page, y)
            # et assigne chaque image à la question la plus récemment rencontrée.
            # Cela gère : images sur la même page que la question, images sur des pages
            # intermédiaires entières, et images en haut d'une page dont la question
            # précédente commence sur une page antérieure.
            events = []
            for i in range(len(flat_q_ids)):
                events.append((q_page_y[i][0], q_page_y[i][1], "q", i))
            for pno, y, ext, data in image_events:
                events.append((pno, y, "img", (ext, data)))
            events.sort(key=lambda e: (e[0], e[1]))

            current_q_idx = -1
            for _, _, etype, data in events:
                if etype == "q":
                    current_q_idx = data
                elif etype == "img" and current_q_idx >= 0:
                    qid = flat_q_ids[current_q_idx]
                    ext, img_data = data
                    b64 = base64.b64encode(img_data).decode("ascii")
                    img_html = (
                        f'<div class="extra"><img src="data:image/{ext};base64,{b64}" '
                        f'style="max-width:100%;border-radius:8px;margin:8px 0 12px"></div>\n'
                    )
                    images_by_qid[qid] = images_by_qid.get(qid, "") + img_html
        else:
            # Fallback (PyMuPDF ancien ou écart de comptage) : une image par question,
            # sur la page où commence le texte de la question.
            if image_events and len(q_page_y) != len(flat_q_ids):
                warnings.append(
                    f"[images] Écart (blocs PDF: {len(q_page_y)}, sections: {len(flat_q_ids)}) "
                    "— heuristique simplifiée utilisée pour les images."
                )
            for qid, offset in zip(flat_q_ids, raw_positions):
                p = page_at(offset)
                if p < len(pages_images) and pages_images[p]:
                    ext, data = pages_images[p].pop(0)
                    b64 = base64.b64encode(data).decode("ascii")
                    images_by_qid[qid] = (
                        f'<div class="extra"><img src="data:image/{ext};base64,{b64}" '
                        f'style="max-width:100%;border-radius:8px;margin:8px 0 12px"></div>\n'
                    )

    if images_by_qid:
        n_multi = sum(1 for v in images_by_qid.values() if v.count('<div class="extra">') > 1)
        msg = f"[info] {len(images_by_qid)} image(s) associée(s) automatiquement"
        if n_multi:
            msg += f" (dont {n_multi} question(s) avec {n_multi if n_multi > 1 else 'plusieurs'} images)"
        print(msg + " — vérifie leur placement.")

    meta = guess_metadata(epreuve_code, warnings)

    total_q = sum(len(s["questions"]) for s in sections)
    graded_q = sum(1 for s in sections for q in s["questions"] if q["type"] != "QROC")

    sub_bits = []
    for s in sections:
        locked = bool(re.search(r"DP|KFP|TCS", s["code"], re.IGNORECASE))
        n = len(s["questions"])
        sub_bits.append(f'{esc(s["code"])} ({n}{", verrouillé" if locked else ""})')
    sub_html = f"{total_q} questions : " + " · ".join(sub_bits)

    out_html = build_html(sections, meta["title_html"], meta["title_html"], sub_html, images_by_qid)

    base_dir = os.path.dirname(os.path.abspath(pdf_path))
    out_name = meta["filename"] if meta["ue"] else os.path.splitext(os.path.basename(pdf_path))[0] + ".html"
    out_path = os.path.join(base_dir, out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_html)

    snippet = f'''<a class="qz" href="{out_name}">
  <div class="qz-t">{meta["acad_year"]} · {"Rattrapage" if meta["rattrapage"] else "Session normale"}{f" ({meta['month']} {meta['year']})" if meta['month'] else ""}</div>
  <div class="qz-d">{total_q} questions — {" · ".join(sub_bits)}</div>
  <span class="qz-go">Ouvrir le quiz →</span>
</a>'''
    snippet_path = os.path.splitext(out_path)[0] + ".snippet.html"
    with open(snippet_path, "w", encoding="utf-8") as f:
        f.write(snippet)

    if debug:
        debug_path = os.path.splitext(out_path)[0] + ".debug.json"
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "sections": sections, "warnings": warnings}, f,
                       ensure_ascii=False, indent=2)
        print(f"[debug] structure écrite dans {debug_path}")

    print("=" * 70)
    print(f"OK : {out_path}")
    print(f"     {total_q} questions ({graded_q} notées), {len(sections)} sections")
    print(f"     UE détectée : {meta['ue'] or '?'} -> dossier suggéré : {meta['folder']}")
    print(f"     Extrait de portail écrit dans : {snippet_path}")
    if warnings:
        print("-" * 70)
        print(f"{len(warnings)} point(s) à vérifier manuellement :")
        for w in warnings:
            print(f"  - {w}")
    print("=" * 70)
    print("Rappel : relis le HTML généré (titres de section, texte exact, images,")
    print("questions marquées [A VERIFIER]) avant de le publier sur le site.")


def main():
    parser = argparse.ArgumentParser(description="Convertit une annale PDF en quiz HTML BobMed.")
    parser.add_argument("pdf", help="Chemin du fichier PDF à convertir")
    parser.add_argument("--debug", action="store_true", help="Écrit aussi un .debug.json")
    args = parser.parse_args()
    run(args.pdf, debug=args.debug)


if __name__ == "__main__":
    main()
