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
"Question N: (Type: XXX) score/1" avec cases ☐/☑ (QRM/QRPL/QRP) ou ◎/◉ (QRU/QTCS)
et libellés Faux/Valide/Indispensable. Si la plateforme source change son
gabarit d'export, les regex ci-dessous devront être ajustées.
"""

import sys
import os
import re
import json
import html
import base64
import hashlib
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
    "1.1": ("Biostatistiques (D1)", "d1/t4"),
    "9.2": ("UE 9.2 (D1)", "d1/t4"),
    "9.3": ("UE 9.3 (D1)", "d1/t4"),
    # UE 3 existe en D1 (Agents infectieux et hygiène, d1/t4/) ET en D2-T2
    # (Psy/Addicto, d2/t2/) : ambiguïté réelle, laissée à vérifier manuellement
    # (cf. avertissement console ; préfixe DFG = D1, DFA = D2).
    "3": ("Agents infectieux (D1) / Psy-Addicto (D2-T2) — VERIFIER", "d1/t4 OU d2/t2"),
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
    # QRP : notation proportionnelle (bonnes cochées / nb attendu) et nombre
    # d'items sélectionnables plafonné au nb d'items vrais — distinct des QRPL
    # (rendues en QRM/barème EDN). Ne PAS fusionner avec QRPL.
    "QRP": "QRP",
    # Pointage de zone sur une image (clic direct sur une radio/schéma dans la
    # plateforme source) : pas d'options lettrées côté PDF, donc pas de parsing
    # automatique possible. Produit un stub [A VERIFIER] explicite plutôt que de
    # tomber silencieusement en QRM vide (cf. section QZONE du CLAUDE.md pour le
    # gabarit HTML/CSS/JS à compléter à la main : coordonnées de zone en %,
    # estimées visuellement sur l'image).
    "QZONE": "QZONE",
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
    re.compile(r"Référence\s*:\s*[^\x00\s]+\s+Session\s*:\s*(?:Session\s+)?[^\x00\s]+\s*"),
    # Certains exports n'ont qu'un "Référence: <code>" isolé (sans "Session:") en
    # pied de page : sans ce nettoyage, il se colle au texte de la dernière
    # option de la dernière question de la page (bug confirmé sur DFA1-UE7.1-
    # NOVEMBRE2025, où "Référence: DFA1-UE7.1-NOVEMBRE2025" polluait plusieurs options).
    re.compile(r"Référence\s*:\s*[^\x00\s]+\s*"),
]

# Fragments de pied de page ISOLÉS (un span PyMuPDF par ligne). Quand la colonne
# du pied de page est lue span par span, les champs se détachent de leur label
# ("Session:" seul, la valeur timestamp "2023-08-28-16:21:55" sans son "Date de
# création:", le "8/17" sans "Page:", le "1" sans "Version:"). NOISE_FIELD_RES,
# qui exige label+valeur collés, ne les reconnaît alors PAS : dans la remontée
# couleur de _trailing_notes_from_spans, un tel fragment (noir, non-bruit) casse
# la collecte de la note bleue du jury qui le précède — la note n'est jamais
# détachée et fuit dans la dernière option (bug confirmé : note bleue « majorer
# la dose… L'explication de l'insulinothérapie… » de UE8.3 2022-2023, perdue car
# suivie de « Session: … » en span isolé). Ces motifs, LOCAUX à la remontée de
# note (jamais appliqués au texte des questions), permettent de sauter le pied de
# page fragmenté et d'atteindre la note. Ne peut que RÉVÉLER une note à détacher —
# le détachement lui-même reste protégé par le match exact de strip_general_note.
_FOOTER_SPAN_RES = [
    re.compile(r"^\s*Session\s*:"),
    re.compile(r"^\s*Référence\s*:"),
    re.compile(r"^\s*Date de création\s*:?\s*$"),
    re.compile(r"^\s*\d{4}-\d{2}-\d{2}[-:\d]*\s*$"),
    re.compile(r"^\s*Version\s*:?\s*$"),
    re.compile(r"^\s*Page\s*:?\s*$"),
    re.compile(r"^\s*\d+\s*/\s*\d+\s*$"),
    re.compile(r"^\s*\d{1,3}\s*$"),
]

LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl",
    # Certaines polices d'export (observe sur DEC22_HGEUE8.1.pdf) remappent les
    # glyphes de ligature "f"/"fi"/"fl"/"ff" vers des codepoints de zone privee
    # Unicode (PUA) au lieu de les resoudre ou de les laisser vides. Invisibles
    # a l'affichage, ils avalent silencieusement toutes les lettres "f" du
    # texte si non traites : verifier au cas par cas si le bug "ligature
    # absente" reapparait (cf. checklist CLAUDE.md pt.2).
    "": "f", "": "fi", "": "fl", "": "ff",
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


# Un code de section long ("PARTIE2-RANG A/B-DP1") peut être coupé par un retour
# à la ligne PDF au milieu du token (aucun espace réel dans le code source) :
# sans ce recollage, SECTION_RE (qui capture \S+, un seul token) ne matche
# plus rien et la section entière disparaît silencieusement.
_WRAPPED_SECTION_RE = re.compile(r"(Element d'épreuve\s*:\s*)(.+?)\s+([\d.]+\s*/\s*\d+)", re.DOTALL)


def fix_wrapped_section_codes(text: str) -> str:
    def repl(m):
        return m.group(1) + re.sub(r"\s+", "", m.group(2)) + " " + m.group(3)
    return _WRAPPED_SECTION_RE.sub(repl, text)


def clean_span(text: str) -> str:
    """Collapse whitespace within a captured stem/option snippet."""
    text = re.sub(r"\x00PAGE\d+\x00", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Couleur des justifications/explications du jury dans l'export Uness (bleu). Le
# texte des options, lui, est en noir (#000000). Cette distinction est FIABLE et
# sert à détacher la « note générale du jury » (placée après la dernière option)
# de cette dernière option, où le flux de texte PDF la colle sans séparateur —
# cause des justifications mal découpées (ex. SQI1-Q8 « cyphoscolise <note> » et
# DP1-Q1-E « La température <note> » de l'annale UE7.1 mars 2024). On raisonne sur
# la couleur, jamais sur une heuristique de coupure du texte (trop risquée : une
# note peut contenir mot pour mot le libellé d'une autre option, cf. « saturation
# en oxygène »). Dégrade proprement : un PDF sans span de cette couleur ne produit
# aucune note (comportement inchangé).
JUSTIF_COLORS = {0x00A1FE}


def _alnum(text: str) -> str:
    """Réduit un texte à ses seuls caractères alphanumériques, en minuscules —
    pour comparer deux extractions PDF d'un même passage sans se soucier des
    différences d'espaces ni de ponctuation (ex. « respiratoire. Le » vs
    « respiratoire.Le »)."""
    return re.sub(r"[^0-9A-Za-zÀ-ÿ]", "", text).lower()


def _trailing_notes_from_spans(doc_spans):
    """Depuis la liste ordonnée des spans du document [(texte, couleur), …],
    renvoie, DANS L'ORDRE DES QUESTIONS, la « note générale du jury » de chaque
    question : la suite CONTIGUË de spans de couleur justification placée juste
    après la dernière option (avant la question/section suivante), en ignorant le
    pied de page. Une entrée vaut None quand il n'y a pas de note bleue en fin de
    question. La liste est alignée 1:1 sur l'ordre plat des questions du PDF.

    L'en-tête « Question N: (Type: … ) » est souvent éclaté sur plusieurs spans
    (changements de style : « Question 1: », « (Type: QRP) », score coloré) : on
    repère donc les débuts de question sur la CONCATÉNATION des spans, puis on
    rattache chaque span à sa question via son décalage de caractères."""
    import bisect
    seg_re = re.compile(r"Question\s+(?:[A-Z]+|\d+)\s*:\s*\(Type", re.IGNORECASE)
    sec_re = re.compile(r"Element\s+d'épreuve\s*:", re.IGNORECASE)

    def is_noise(t):
        tt = fix_ligatures(t).strip()
        return (any(rx.match(tt) for rx in NOISE_FIELD_RES)
                or any(rx.match(tt) for rx in _FOOTER_SPAN_RES))

    texts = [t for t, _ in doc_spans]
    colors = [c for _, c in doc_spans]
    offsets, pos = [], 0
    for t in texts:
        offsets.append(pos)
        pos += len(t)
    concat = "".join(texts)
    starts = [m.start() for m in seg_re.finditer(concat)]
    if not starts:
        return []

    seg_of = [bisect.bisect_right(starts, o) - 1 for o in offsets]
    notes = [None] * len(starts)
    for seg in range(len(starts)):
        idxs = [i for i in range(len(texts)) if seg_of[i] == seg]
        run = []
        for i in reversed(idxs):
            t = texts[i]
            if not t.strip() or is_noise(t) or sec_re.search(t):
                continue  # pied de page / marqueur de section : ignorer, ne pas casser le run
            if colors[i] in JUSTIF_COLORS:
                run.append(t)
            else:
                break  # premier span non-bleu de contenu : fin de la note
        if run:
            notes[seg] = clean_span(fix_ligatures("".join(reversed(run)))) or None
    return notes


def strip_general_note(option_text, note):
    """Si `option_text` (dernière option d'une question) se termine par `note`
    (comparaison alphanumérique, insensible espaces/ponctuation, alignée sur les
    mots), retire la note et renvoie (texte_option_nettoyé, note). Sinon renvoie
    (None, None) — on ne modifie jamais l'option si le suffixe ne correspond pas
    exactement (garde-fou : évite de sur-découper une option légitimement longue
    ou dont la justification entre parenthèses a déjà été extraite)."""
    if not note:
        return None, None
    a_note = _alnum(note)
    if len(a_note) < 10:
        return None, None
    words = option_text.split()
    for k in range(len(words) - 1, -1, -1):
        acc = _alnum(" ".join(words[k:]))
        if acc == a_note:
            head = " ".join(words[:k]).strip()
            return (head, note) if head else (None, None)
        if len(acc) > len(a_note):
            break
    # Repli tolérant : la note captée depuis les spans DÉBORDE parfois de ce qui a
    # réellement fuité dans l'option (elle inclut la suite de la correction, absente
    # du flux plat de l'option) — l'égalité exacte échoue alors, et la fuite reste
    # collée (ex. UE8.3 2022-2023 DP2-QF « … population générale Apprendre en
    # discutant… », note plus longue que la portion fuitée). On coupe donc au point
    # où le suffixe de l'option devient un PRÉFIXE de la note : ce suffixe EST le
    # début de la note bleue (= correction du jury), jamais du texte d'option.
    # Ancrage ≥ 20 car. alnum partagés → collision accidentelle quasi impossible.
    best_k = None
    for k in range(len(words) - 1, -1, -1):
        acc = _alnum(" ".join(words[k:]))
        if len(acc) < 20:
            continue
        if a_note.startswith(acc):
            best_k = k          # suffixe encore préfixe de la note : on peut agrandir
        elif best_k is not None:
            break               # on vient d'entrer dans le texte d'option : stop
    if best_k is not None:
        head = " ".join(words[:best_k]).strip()
        if head:
            return head, note
    return None, None


# ----------------------------------------------------------------------------
# 2. Regex de structure
# ----------------------------------------------------------------------------

SECTION_RE = re.compile(r"Element d'épreuve\s*:\s*(\S+)\s+(?:\(\d+\)\s+)?[\d.]+\s*/\s*\d+")
# Le marqueur "(Type: XXX)" est l'ancre fiable d'un début de question ; le score
# qui le suit ("1/1", "0/3", "0.4/2", "Non corrigé"…) est purement décoratif et
# NE DOIT PAS conditionner la détection. L'ancienne version exigeait "…/1", ce qui
# faisait disparaître silencieusement toute question notée sur 2, sur 3, ou "Non
# corrigé" : elle était alors fusionnée dans la question précédente (data-correct
# concaténés, lettres d'option en double). On rend donc le score optionnel et de
# format libre — quand il est présent on le consomme (pour qu'il ne déborde pas
# dans l'énoncé), quand il manque ou change de forme la question reste détectée.
QUESTION_RE = re.compile(
    r"Question\s+([A-Z]+|\d+)\s*:\s*\(Type\s*:\s*(\w+)\)"
    r"(?:\s*(?:[\d.]+\s*/\s*\d+|Non\s+corrigé))?"
    r"\s*(Question neutralisée)?"
)
OPTION_START_RE = re.compile(r"[☐☑◎◉]")
# Regex de découpe par entrée d'option. La case (☐/☑/◎/◉) est optionnelle car
# elle peut apparaître APRÈS le libellé "Valide X." en cas de saut de page dans
# le PDF (la colonne des cases est lue séparément de la colonne de texte par
# PyMuPDF). On gère aussi les labels "Inacceptable" (item éliminatoire, traité
# comme Faux côté validité) et "Neutraliser" (item neutralisé par le jury). Sans
# "Neutraliser" dans cette alternative, l'entrée n'était pas reconnue comme un
# début d'option : l'item disparaissait (fusionné dans l'option précédente,
# lettres décalées) — bug confirmé sur l'annale UE7.1 mars 2024 (mDP1-Q2 items A
# et D, SQI1-Q15 item E, tous "Neutraliser", absents ou fusionnés).
_OPT_ENTRY_RE = re.compile(
    r"([☐☑◎◉])?\s*(Faux|Valide|Indispensable|Inacceptable|Neutraliser)\s+([A-Z])\.\s*"
)
_STRAY_GLYPH_RE = re.compile(r"[☐☑◎◉]")
# Marqueur de début de la liste des réponses valides d'une QROC. On ne capture
# QUE le début : l'ancienne version bornait la capture au premier "(\d+)", ce qui
# (a) ratait les pondérations décimales "(0.5)"/"(0.2)" et s'arrêtait donc au
# premier "(1)" rencontré — fusionnant plusieurs réponses en une seule chaîne —
# et (b) ne distinguait pas les réponses créditées des distracteurs "(0)".
REPONSES_VALIDES_START_RE = re.compile(r"Réponses\s+valides\s*:\s*", re.IGNORECASE)
# Chaque réponse valide est de la forme "<texte> (<points>)", une par ligne,
# les points pouvant être entiers ou décimaux (0.2, 0.5, 1). On extrait chaque
# couple (texte, points) indépendamment ; le texte est capturé en non-gourmand
# jusqu'à sa propre pondération, ce qui segmente correctement une liste collée
# sur une seule ligne à l'extraction PDF.
QROC_ENTRY_RE = re.compile(r"(.+?)\s*\(\s*(\d+(?:[.,]\d+)?)\s*\)", re.DOTALL)
SELECT_N_RE = re.compile(r"[Ss]électionnez\s*(jusqu.à\s*)?(\d+)\s*items?")
REPONSES_ATTENDUES_RE = re.compile(r"\(\s*(\d+)\s*réponses?\s*attendues?\s*\)", re.IGNORECASE)
MAX_N_RE = re.compile(r"\(\s*max\.?\s*(\d+)\s*\)", re.IGNORECASE)
EPREUVE_RE = re.compile(r"Epreuve\s*:\s*(\S+)")

# Détection d'une question qui ANNONCE une image (radio, IRM, scanner…). Sert à
# (1) corriger un mauvais placement d'image et (2) signaler une image attendue
# mais absente. L'ancienne version ne reconnaissait que « <imagerie> … est la
# suivante : » et « ci-dessous … <imagerie> » (ci-dessous AVANT l'imagerie) — elle
# ratait « l'IRM … Diffusion, ci-dessous » (imagerie AVANT ci-dessous) et « cf
# image … ». On rend la détection bidirectionnelle et on ajoute « cf image »,
# « images jointes », « voici … ». Ratait aussi « <imagerie> que voici » (voici
# APRÈS l'imagerie, jamais couvert — seul le sens inverse l'était) et « <imagerie>
# a été réalisée » (tournure au passé composé, sans « voici »/« ci-dessous » ni
# « suivante ») : les deux repérées sur l'annale UE7.1 2023-2024 S1 (SQI1 Q4 et
# Q10), où leur absence a empêché la correction de repositionnement de rattraper
# le décalage d'image constaté (cf. commentaire sur owner_for_image plus bas).
_IMAGING = (
    r"(radiographie|scanner|tdm|tep|irm|ecg|électrocardiogramme|angio"
    r"|coupe|cliché|iconographie|imagerie|image|figure|photo|schéma|fond d.?œil|rx\b)"
)
IMG_EXPECTED_RE = re.compile(
    rf"{_IMAGING}[^.!?]{{0,120}}(est (?:la|le|l.) suivante?|sont les suivants?)\s*:"
    rf"|ci[- ]?(?:dessous|apr[èe]s|contre|joints?|jointe?s?)[^.!?]{{0,90}}{_IMAGING}"
    rf"|{_IMAGING}[^.!?]{{0,90}}ci[- ]?(?:dessous|apr[èe]s|contre|joints?|jointe?s?)"
    rf"|cf\.?\s*(?:image|images|photo|figure|cliché|iconographie)"
    rf"|images?\s+jointes?"
    rf"|voici[^.!?]{{0,40}}{_IMAGING}"
    rf"|{_IMAGING}[^.!?]{{0,40}}voici"
    rf"|{_IMAGING}[^.!?]{{0,60}}a\s+(?:été|ete)\s+réalisée?s?",
    re.I,
)


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
            # Un item "Neutraliser" (annulé par le jury) est compté valide pour
            # tout le monde : on le traite donc comme une réponse correcte, avec
            # une mention "(item neutralisé)" dans la correction (cf. render_citems).
            "valid":   validity in ("Valide", "Indispensable", "Neutraliser"),
            # Case cochée = réponse choisie par CET étudiant (indice pour resolve_qru).
            "checked": glyph in ("☑", "◉") if glyph else False,
            "expl":    expl,
            "text":    main_text,
            "mandatory":    validity == "Indispensable",
            "unacceptable": validity == "Inacceptable",
            "neutral":      validity == "Neutraliser",
        })
    return opts


def parse_qroc_block(blob):
    """Retourne (stem, answers) où answers est une liste de couples
    (texte, points) — points = crédit accordé par le jury (1 = réponse exacte,
    0.5/0.2 = réponse partielle acceptée, 0 = distracteur explicitement faux).
    L'appelant filtre ensuite sur points > 0 pour l'auto-correction (un
    distracteur "(0)" ne doit jamais être accepté)."""
    m = REPONSES_VALIDES_START_RE.search(blob)
    if not m:
        return clean_span(blob), []
    stem_and_junk = blob[: m.start()]
    idx = stem_and_junk.rfind("?")
    stem = stem_and_junk[: idx + 1] if idx != -1 else stem_and_junk
    stem = clean_span(stem)

    answers_blob = clean_span(blob[m.end():])
    answers = []
    for em in QROC_ENTRY_RE.finditer(answers_blob):
        text = em.group(1).strip().rstrip(".").strip()
        try:
            pts = float(em.group(2).replace(",", "."))
        except ValueError:
            pts = 1.0
        if text:
            answers.append((text, pts))
    if not answers:
        # Repli : aucune paire "(points)" détectée — conserver le bloc brut comme
        # réponse unique (à relire) plutôt que de perdre l'information.
        raw = answers_blob.rstrip(".").strip()
        if raw:
            answers.append((raw, 1.0))
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

    if qtype == "QZONE":
        # Pas d'options lettrées à parser côté PDF (pointage libre sur l'image) :
        # on garde tout le bloc brut comme stem, à nettoyer manuellement, et on
        # laisse render_question produire un stub [A VERIFIER] à compléter avec
        # de vraies zones (cf. section QZONE du CLAUDE.md).
        q["stem"] = clean_span(raw_block)
        warnings.append(
            f"{section_code} Q{qnum} (QZONE): pointage de zone détecté — stub "
            f"[A VERIFIER] généré, zones à positionner à la main (cf. CLAUDE.md § QZONE)."
        )
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

    # Note : la détection d'une justification du jury collée à l'intitulé (option
    # anormalement longue) est faite plus tard, dans run(), APRÈS le détachement
    # par couleur — là seulement on sait si une note bleue a été détachée (option
    # nettoyée, pas de faux positif) ou non (fuite réelle à signaler avec le point
    # de coupe). L'ancien contrôle « len > 100 » ici se déclenchait sur toute
    # option légitimement longue (≈ 25 faux positifs par annale) : supprimé au
    # profit du contrôle précis, couleur-aware, de run() (cf. « fuite précise »).

    # Le tag "(Type: ...)" du PDF source est incohérent d'une plateforme à l'autre :
    # certains exports taguent ces questions "QRM" (avec "Sélectionnez (jusqu'à) N
    # items" dans l'énoncé), d'autres taguent directement "QRPL"/"QRP" mais formulent
    # le nombre attendu différemment ("(N réponses attendues)" ou "(max N)"). On
    # détecte donc le nombre via les trois formulations connues, indépendamment du
    # tag brut.
    sm = SELECT_N_RE.search(stem)
    ra = REPONSES_ATTENDUES_RE.search(stem)
    mx = MAX_N_RE.search(stem)
    if (sm or ra or mx) and qtype in ("QRM", "QRPL"):
        qtype = q["type"] = "QRPL"
        if sm:
            q["select_max"] = bool(sm.group(1))
            q["select_n"] = int(sm.group(2))
        elif ra:
            q["select_max"] = False
            q["select_n"] = int(ra.group(1))
        else:
            q["select_max"] = True
            q["select_n"] = int(mx.group(1))
    elif qtype == "QRPL" and not sm and not ra and not mx:
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
        parts = []
        if o.get("expl"):
            parts.append(esc(o["expl"]))
        if o.get("neutral"):
            # Item annulé par le jury : compté valide, mais on le signale pour ne
            # pas laisser croire qu'il s'agit d'une affirmation médicalement juste.
            parts.append("item neutralisé par le jury (compté valide)")
        tail = " — " + " · ".join(parts) if parts else ""
        rows.append(
            f'<div class="citem {cls}"><span class="cl">{o["letter"]}.</span> '
            f'<span class="cv">{verdict}</span>{tail}</div>'
        )
    return "\n".join(rows)


def render_option_li(opt):
    extra_attrs = ""
    if opt.get("mandatory"):
        extra_attrs += ' data-mandatory="1"'
    if opt.get("unacceptable"):
        extra_attrs += ' data-unacceptable="1"'
    return (
        f'<li class="opt" data-l="{opt["letter"]}" data-correct="{1 if opt["valid"] else 0}"{extra_attrs}>'
        f'<span class="box">{opt["letter"]}</span><span class="otext">{esc(opt["text"])}</span></li>'
    )


def qroc_answer_data(answers):
    """À partir de la liste (texte, points) d'une QROC, calcule :
      - accepted : toutes les réponses créditées (points > 0), pour l'auto-
        correction par mots-clés (data-answer, séparées par « | ») ;
      - display  : les réponses exactes (points maximum) pour l'affichage
        « Réponse attendue : … » (les partielles restent auto-acceptées mais on
        met en avant la formulation attendue).
    Un distracteur "(0)" n'est jamais accepté ni affiché.
    Tolère l'ancien format (liste de chaînes) au cas où."""
    norm = []
    for a in answers:
        if isinstance(a, (list, tuple)):
            norm.append((a[0], float(a[1])))
        else:
            norm.append((a, 1.0))
    credited = [(t, p) for t, p in norm if p > 0] or norm
    accepted = [t for t, _ in credited]
    max_pts = max((p for _, p in credited), default=1.0)
    exact = [t for t, p in credited if p >= max_pts] or accepted
    return accepted, exact


def render_question(section_code, q, image_html="", is_d2=False):
    qid = f'{section_code}-Q{q["num"]}'
    qnum_label = f'{section_code} Q{q["num"]}'
    dpctx_html = ""

    if q["type"] == "QROC":
        answers = q["qroc_answers"] or [("[A VERIFIER — réponse non détectée]", 1.0)]
        accepted, exact = qroc_answer_data(answers)
        display = " / ".join(exact)
        data_answer = " | ".join(accepted)
        if is_d2:
            # D2 : auto-correction par mots-clés (data-answer) + bouton Valider,
            # avec repli auto-évaluation « juste/faux » (cf. moteur QROC injecté).
            return f'''<div class="q" id="{qid}" data-answer="{esc(data_answer)}" data-correct="" data-type="QROC">
<div class="qhead"><span class="qnum">{qnum_label}</span><span class="qtype">QROC</span><span class="status" aria-live="polite"></span></div>
{dpctx_html}<div class="stem">{esc(q["stem"])}</div>
{image_html}<textarea class="qrocin" rows="2" placeholder="Réponds, puis « Valider »"></textarea>
<div class="actions"><button class="validate">Valider</button><button class="show" type="button">Voir la réponse</button></div>
<div class="correction" hidden>
<div class="qrocans">Réponse attendue : {esc(display)}</div>
</div>
</div>'''
        # D1 : auto-correction par l'étudiant à la lecture du modèle (pas de
        # notation automatique ni d'auto-évaluation — choix délibéré, cf. CLAUDE.md).
        return f'''<div class="q" id="{qid}" data-correct="" data-type="QROC">
<div class="qhead"><span class="qnum">{qnum_label}</span><span class="qtype">QROC</span><span class="status" aria-live="polite"></span></div>
{dpctx_html}<div class="stem">{esc(q["stem"])}</div>
{image_html}<textarea class="qrocin" rows="2" placeholder="Votre réponse…"></textarea>
<div class="actions"><button class="show" type="button">Voir la réponse</button></div>
<div class="correction" hidden>
<div class="qrocans">Réponse attendue : {esc(display)}</div>
</div>
</div>'''

    if q["type"] == "QZONE":
        # Stub à compléter à la main : convertir l'.extra simple en .extra.zonewrap,
        # ajouter les <div class="zone"> positionnées en % et le CSS .zonewrap/.zone
        # (cf. section QZONE du CLAUDE.md — ne PAS publier tel quel).
        return f'''<div class="q" id="{qid}" data-correct="[A VERIFIER]" data-type="QZONE">
<div class="qhead"><span class="qnum">{qnum_label}</span><span class="qtype">QZONE</span><span class="status" aria-live="polite"></span></div>
{dpctx_html}<div class="stem">{esc(q["stem"])}</div>
{image_html}<!-- [A VERIFIER] QZONE : remplacer .extra par .extra.zonewrap et ajouter les <div class="zone" data-l="…" style="left:%;top:%;width:%;height:%"> (cf. CLAUDE.md § QZONE) -->
<ul class="opts">
</ul>
<div class="actions"><button class="validate">Valider</button><button class="show" type="button">Voir la réponse</button></div>
<div class="correction" hidden><div class="ans">Réponse : [A VERIFIER]</div>
</div>
</div>'''

    opts = q["options"]
    neutral_note = ' <div class="note">Question neutralisée : tous les items sont comptés valides.</div>' if q["neutralized"] else ""
    # Note générale du jury détachée de la dernière option (cf. strip_general_note) :
    # rendue en encart « rappel », avant les verdicts par item — jamais collée à
    # l'intitulé d'une option (règle « justifications » du CLAUDE.md).
    general_note = f'<div class="note"><div class="rappel">{esc(q["general_note"])}</div></div>' if q.get("general_note") else ""

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
            correction = f'<div class="ans">Réponse : {ans_text}</div>{extra_note}{general_note}{option_notes}{neutral_note}'
        else:
            # QRU clinique classique : verdict VRAI/FAUX par option, au format D1.
            citems = render_citems(opts)
            correction = f'<div class="ans">Réponse : {primary}</div>{neutral_note}{general_note}\n{citems}'

        return f'''<div class="q" id="{qid}" data-correct="{primary}" data-type="QRU">
<div class="qhead"><span class="qnum">{qnum_label}</span><span class="qtype">{badge}</span><span class="status" aria-live="polite"></span></div>
{dpctx_html}<div class="stem">{esc(q["stem"])}</div>
{image_html}<ul class="opts">
{opts_html}
</ul>
<div class="actions"><button class="validate">Valider</button><button class="show" type="button">Voir la réponse</button></div>
<div class="correction" hidden>{correction}</div>
</div>'''

    # QRM / QRPL / QRP
    correct_letters = "".join(o["letter"] for o in opts if o["valid"])
    data_type = "QRM"
    badge = "QRM"
    if q["type"] == "QRPL":
        # QRPL = « QRP longue » : notation R2C proportionnelle X/N (identique à la
        # QRP), plafond de sélection = N = nombre de bonnes réponses (cf. grade()
        # et click handler). Se distingue de la QRP seulement par le nombre
        # d'options (liste longue).
        data_type = "QRPL"
        n = sum(1 for o in opts if o["valid"])
        badge = f'QRPL · {n} réponse{"s" if n > 1 else ""}'
    elif q["type"] == "QRP":
        # Notation proportionnelle X/N : N = nb d'items vrais, qui plafonne aussi
        # le nombre d'items sélectionnables côté JS (cf. click handler).
        data_type = "QRP"
        n = sum(1 for o in opts if o["valid"])
        badge = f'QRP · {n} réponse{"s" if n > 1 else ""}'
    opts_html = "\n".join(render_option_li(o) for o in opts)
    ans_display = ", ".join(correct_letters) if correct_letters else "[A VERIFIER]"
    citems = render_citems(opts)
    return f'''<div class="q" id="{qid}" data-correct="{correct_letters}" data-type="{data_type}">
<div class="qhead"><span class="qnum">{qnum_label}</span><span class="qtype">{badge}</span><span class="status" aria-live="polite"></span></div>
{dpctx_html}<div class="stem">{esc(q["stem"])}</div>
{image_html}<ul class="opts">
{opts_html}
</ul>
<div class="actions"><button class="validate">Valider</button><button class="show" type="button">Voir la réponse</button></div>
<div class="correction" hidden><div class="ans">Réponse : {ans_display}</div>{neutral_note}{general_note}
{citems}
</div>
</div>'''


HTML_TEMPLATE = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" type="image/svg+xml" href="{favicon_href}">
<link rel="stylesheet" href="{theme_href}">
<title>Quiz — {title_plain}</title><style>
:root{{--bg:#f7f8f9;--card:#fff;--ink:#132025;--mut:#5b6b73;--line:#dfe4e2;--vrai:#15803d;--vraibg:#eaf7ef;--faux:#b91c1c;--fauxbg:#fbeceb;--neu:#b45309;--acc:#4f46e5;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 'DM Sans',-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
header{{position:sticky;top:0;z-index:5;background:rgba(247,248,249,.95);backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:14px 18px}}
.wrap{{max-width:820px;margin:0 auto;padding:0 16px 80px}}
.hwrap{{max-width:820px;margin:0 auto}}
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
.q.done .opt[data-mandatory="1"]{{border-left:3px solid var(--neu)}}
.q.done .opt[data-mandatory="1"] .box{{position:relative}}
.q.done .opt[data-mandatory="1"] .box::after{{content:'★';font-size:9px;color:var(--neu);position:absolute;top:-5px;right:-6px}}
.q.done .opt[data-unacceptable="1"]{{border-left:3px solid var(--faux)}}
.q.done .opt[data-unacceptable="1"] .box{{position:relative}}
.q.done .opt[data-unacceptable="1"] .box::after{{content:'✕';font-size:9px;color:var(--faux);position:absolute;top:-5px;right:-6px}}
.citem .tag-mandatory,.citem .tag-unacceptable{{display:inline-block;font-size:11px;font-weight:700;border-radius:5px;padding:1px 7px;margin-left:8px;vertical-align:middle}}
.citem .tag-mandatory{{color:var(--neu);background:var(--neubg,#fdf3e7);border:1px solid var(--neu)}}
.citem .tag-unacceptable{{color:var(--faux);background:var(--fauxbg);border:1px solid var(--faux)}}
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

function markSpecial(q){{
  const opts=[...q.querySelectorAll('.opt')];
  const cits=[...q.querySelectorAll('.correction .citem')];
  opts.forEach((o,i)=>{{
    const c=cits[i];if(!c)return;
    if(o.dataset.mandatory==='1'&&!c.querySelector('.tag-mandatory')){{
      const t=document.createElement('span');t.className='tag-mandatory';t.textContent='indispensable';c.appendChild(t);
    }}
    if(o.dataset.unacceptable==='1'&&!c.querySelector('.tag-unacceptable')){{
      const t=document.createElement('span');t.className='tag-unacceptable';t.textContent='inacceptable';c.appendChild(t);
    }}
  }});
}}

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
  const isProp=q.dataset.type==='QRP'||q.dataset.type==='QRPL'||q.dataset.type==='QZONE';const nExp=correct.size,good=[...sel].filter(l=>correct.has(l)).length;
  let pts=isProp?(nExp>0?good/nExp:0):qPoints(disc,isQRU);
  const missMandatory=[...q.querySelectorAll('.opt[data-mandatory="1"]')].some(o=>!sel.has(o.dataset.l));
  const hitUnacceptable=[...q.querySelectorAll('.opt[data-unacceptable="1"]')].some(o=>sel.has(o.dataset.l));
  if(missMandatory||hitUnacceptable)pts=0;
  q.classList.add('done');
  q.querySelector('.correction').hidden=false;
  markSpecial(q);
  const st=q.querySelector('.status');st.style.color='';
  st.textContent=fmtPts(pts)+' / 1';
  if(isProp)st.textContent+=' ('+good+'/'+nExp+' bonne'+(nExp>1?'s':'')+' réponse'+(nExp>1?'s':'')+')';
  else if(!isQRU&&disc>0)st.textContent+=' ('+disc+' incohérence'+(disc>1?'s':'')+')';
  if(missMandatory)st.textContent+=' — item indispensable manqué';
  if(hitUnacceptable)st.textContent+=' — item inacceptable coché';
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
  markSpecial(q);
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
      else if(q.dataset.type==='QRP'||q.dataset.type==='QRPL'){{const _mx=(q.dataset.correct||'').replace(/[^A-Za-z]/g,'').length;if(li.classList.contains('sel'))li.classList.remove('sel');else if(!_mx||q.querySelectorAll('.opt.sel').length<_mx)li.classList.add('sel');}}
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


# CSS des états d'auto-correction / auto-évaluation QROC (D2 uniquement).
QROC_ENGINE_CSS = (
    ".qrocin.good,html.dark .qrocin.good{border-color:var(--vrai)!important;background:var(--vraibg)!important}\n"
    ".qrocin.bad,html.dark .qrocin.bad{border-color:var(--faux)!important;background:var(--fauxbg)!important}\n"
    ".selfassess{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px;font-size:13.5px;color:var(--mut)}\n"
    ".selfassess button{font:inherit;font-size:13px;padding:3px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}\n"
    ".selfassess .sa-yes{color:var(--vrai);border-color:var(--vrai)}\n"
    ".selfassess .sa-no{color:var(--faux);border-color:var(--faux)}\n"
    ".selfassess button:disabled{opacity:.55;cursor:default}\n"
    ".selfassess .sa-yes.chosen{background:var(--vraibg)}\n"
    ".selfassess .sa-no.chosen{background:var(--fauxbg)}\n"
)

# Moteur JS QROC (D2) : auto-correction par mots-clés (qrocAccept lit data-answer
# ou le texte de .qrocans/.qrocmodel, normalise et compare) puis, si l'auto-
# correction échoue, propose une auto-évaluation « juste/faux » (qrocSelfBox /
# qrocSelf). Barème 1/0 volontaire (cf. CLAUDE.md § QROC). Repris à l'identique
# du moteur des annales D2 rédigées à la main pour rester cohérent.
QROC_ENGINE_JS = r'''function qrocNorm(s){return (s||'').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[’'`]/g,' ').replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,' ');}
function qrocAccept(q){var raw=q.dataset.answer||'';if(!raw){var a=q.querySelector('.qrocans')||q.querySelector('.qrocmodel');raw=a?a.textContent.replace(/^[^:]*:\s*/,''):'';}return raw.split(/\s*(?:\||\/|\bou\b)\s*/i).map(qrocNorm).filter(Boolean);}
function qrocStatus(q,pts){var st=q.querySelector('.status');if(!st)return;st.textContent=(pts>=1?'1':'0')+' / 1';st.className='status '+(pts>=1?'ok':'ko');}
function qrocSelfBox(q){if(q.dataset.result==='1')return;var c=q.querySelector('.correction');if(!c||c.querySelector('.selfassess'))return;var d=document.createElement('div');d.className='selfassess';var s=document.createElement('span');s.textContent='Votre réponse comptait-elle juste ?';var y=document.createElement('button');y.type='button';y.className='sa-yes';y.textContent="J'avais juste";var n=document.createElement('button');n.type='button';n.className='sa-no';n.textContent="J'avais faux";d.appendChild(s);d.appendChild(y);d.appendChild(n);c.appendChild(d);}
function qrocSelf(q,val){var inp=q.querySelector('.qrocin');if(inp){inp.classList.remove('good','bad');inp.classList.add(val?'good':'bad');}q.dataset.pts=val?1:0;q.dataset.result=val?'1':'0';qrocStatus(q,val?1:0);var box=q.querySelector('.selfassess');if(box){box.querySelectorAll('button').forEach(function(b){b.disabled=true;});var ch=box.querySelector(val?'.sa-yes':'.sa-no');if(ch)ch.classList.add('chosen');}updateScore();}
function gradeQroc(q){if(q.classList.contains('done'))return;var inp=q.querySelector('.qrocin');var typed=qrocNorm(inp?inp.value:'');var acc=qrocAccept(q);var ok=typed.length>0&&acc.indexOf(typed)>=0;if(inp){inp.readOnly=true;inp.classList.add(ok?'good':'bad');}q.classList.add('done');var cor=q.querySelector('.correction');if(cor)cor.hidden=false;var v=q.querySelector('.validate');if(v)v.disabled=true;q.dataset.pts=ok?1:0;q.dataset.result=ok?'1':'0';qrocStatus(q,ok?1:0);if(!ok)qrocSelfBox(q);updateScore();unlockNext(q);}
'''


def upgrade_qroc_engine_d2(html):
    """Greffe le moteur QROC D2 (auto-correction + auto-évaluation) sur le HTML
    produit par le gabarit : CSS, fonctions JS, aiguillage de grade() vers
    gradeQroc, comptage des QROC dans le score (grad = toutes les questions),
    gestion du clic « J'avais juste/faux » et affichage de l'auto-évaluation à la
    révélation. Remplacements ancrés sur des chaînes uniques du gabarit — sans
    effet si le gabarit évolue (à re-vérifier dans ce cas)."""
    html = html.replace("</style></head>", QROC_ENGINE_CSS + "</style></head>", 1)
    html = html.replace(
        "if(q.dataset.type==='QROC')return;",
        "if(q.dataset.type==='QROC'){gradeQroc(q);return;}",
        1,
    )
    html = html.replace(
        "const grad=qs.filter(q=>q.dataset.type!=='QROC').length;",
        "const grad=qs.length;",
        1,
    )
    html = html.replace("function grade(q){", QROC_ENGINE_JS + "function grade(q){", 1)
    html = html.replace(
        "const s=e.target.closest('.show');if(s){reveal(s.closest('.q'));return;}",
        "const s=e.target.closest('.show');if(s){var _q=s.closest('.q');reveal(_q);"
        "if(_q.dataset.type==='QROC')qrocSelfBox(_q);return;}\n"
        "  var _sy=e.target.closest('.sa-yes');if(_sy){qrocSelf(_sy.closest('.q'),1);return;}\n"
        "  var _sn=e.target.closest('.sa-no');if(_sn){qrocSelf(_sn.closest('.q'),0);return;}",
        1,
    )
    return html


def build_html(sections, title_html, title_plain, sub_html, images_by_qid=None,
               favicon_href="../favicon.svg", is_d2=False):
    images_by_qid = images_by_qid or {}
    total_q = sum(len(s["questions"]) for s in sections)
    # En D2, les QROC sont notées (auto-correction + auto-évaluation « juste/faux »)
    # et comptent donc dans le dénominateur du score ; en D1 elles en sont exclues
    # (auto-correction seule à la lecture du modèle, cf. CLAUDE.md § QROC).
    if is_d2:
        graded_q = total_q
    else:
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
            block = render_question(s["code"], q, image_html=img_html, is_d2=is_d2)
            if i == 0 and s["dpctx"]:
                block = block.replace(
                    '<div class="stem">',
                    f'<div class="dpctx">{esc(s["dpctx"])}</div>\n<div class="stem">',
                    1,
                )
            body_parts.append(block)

    body_html = "\n\n".join(body_parts)
    out = HTML_TEMPLATE.format(
        title_plain=esc(title_plain),
        title_html=esc(title_html),
        sub_html=sub_html,
        total_q=total_q,
        graded_q=graded_q,
        body_html=body_html,
        favicon_href=favicon_href,
        theme_href=favicon_href.replace("favicon.svg", "theme.css"),
    )
    if is_d2:
        out = upgrade_qroc_engine_d2(out)
    return out


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

def run(pdf_path, debug=False, strict=False, force=False):
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

    # Pré-passe : certains exports PDF intègrent les glyphes de case à cocher
    # (☑/☐/◎/◉) comme images bitmap répétées à chaque option de chaque question.
    # Ces icônes décoratives passent le filtre de taille en pixels (elles font
    # parfois jusqu'à 512×512) mais se distinguent des vraies images cliniques
    # par leur répétition : une image dont le contenu (hash) apparaît plus de
    # 2 fois dans tout le document est presque certainement une icône. On
    # exclut aussi (cf. plus bas) toute image dont la taille d'AFFICHAGE sur
    # la page (bbox en points, indépendante de la résolution pixel) est petite
    # — un glyphe de case à cocher s'affiche toujours à ~10-15pt quelle que
    # soit sa résolution interne, alors qu'une vraie image clinique est
    # affichée à une taille lisible (100pt+).
    _hash_counts = {}
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                h = hashlib.md5(pix.samples).hexdigest()
                _hash_counts[h] = _hash_counts.get(h, 0) + 1
            except Exception:
                continue

    page_texts = []
    pages_images = []   # [(ext, data), …] par page — utilisé en fallback
    image_events = []   # (page, y, ext, data) — pour l'assignation positionnelle
    q_page_y = []       # (page, y) de chaque bloc "Question N: (Type:" dans le PDF
    sec_page_y = []     # (page, y) de chaque marqueur "Element d'épreuve:" (frontière de section)
    doc_spans = []      # (texte, couleur) de chaque span, en ordre de lecture — pour
                        # détacher la note du jury de la dernière option (couleur)
    _Q_BLOCK_RE = re.compile(r'Question\s+(?:[A-Z]+|\d+)\s*:\s*\(Type', re.IGNORECASE)
    _SEC_BLOCK_RE = re.compile(r"Element\s+d'épreuve\s*:", re.IGNORECASE)
    for pno, page in enumerate(doc):
        page_texts.append(page.get_text())
        imgs = []
        try:
            for info in page.get_image_info(xrefs=True):
                w, h = info.get("width", 0), info.get("height", 0)
                if w < 100 or h < 100:
                    continue
                bbox = info.get("bbox", (0, 0, 0, 0))
                if (bbox[2] - bbox[0]) < 40 or (bbox[3] - bbox[1]) < 40:
                    continue  # affiché en icône (~10-15pt) : glyphe décoratif, pas une image clinique
                xref = info["xref"]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if _hash_counts.get(hashlib.md5(pix.samples).hexdigest(), 0) > 2:
                        continue  # icône décorative répétée, pas une image clinique
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
                    pix = fitz.Pixmap(doc, xref)
                    if _hash_counts.get(hashlib.md5(pix.samples).hexdigest(), 0) > 2:
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
                if _SEC_BLOCK_RE.search(bt):
                    sec_page_y.append((pno, block["bbox"][1]))
                for ln in block["lines"]:
                    for sp in ln["spans"]:
                        if sp["text"]:
                            doc_spans.append((sp["text"], sp["color"]))
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
    full_text = fix_wrapped_section_codes(full_text)

    sections = parse_sections(full_text, warnings)

    # Détacher la « note générale du jury » de la dernière option de chaque
    # question (bug « justification collée à l'option » — cf. strip_general_note).
    # On s'appuie sur la COULEUR des spans (note = bleu, option = noir), fiable, et
    # on n'agit que si le suffixe correspond exactement (sinon on laisse tel quel).
    # Puis on émet un avertissement de fuite PRÉCIS (couleur-aware) : seulement là
    # où une vraie fuite subsiste, avec le point de coupe — pas sur les options
    # légitimement longues (l'ancien contrôle « len > 100 » de parse_question en
    # produisait ≈ 25 par annale, presque tous faux positifs).
    flat = [(s["code"], q) for s in sections for q in s["questions"]]
    trailing_notes = _trailing_notes_from_spans(doc_spans)
    aligned = len(trailing_notes) == len(flat)
    if not aligned:
        warnings.append(
            f"[note jury] Décompte questions/spans divergent "
            f"({len(flat)} vs {len(trailing_notes)}) — détachement par couleur "
            "désactivé ; contrôle de fuite par longueur ci-dessous (relire les "
            "dernières options)."
        )
    for idx, (code, q) in enumerate(flat):
        if not q["options"]:
            continue
        last = q["options"][-1]
        note = trailing_notes[idx] if aligned else None
        # 1. Détachement de la note bleue (SÛR : ne coupe QUE si la note est le
        #    suffixe alnum exact de l'option — cf. strip_general_note). Ne peut
        #    jamais corrompre une option : au pire elle ne coupe pas.
        if note and q["type"] in ("QRM", "QRP", "QRPL", "QRU", "TCS"):
            head, gnote = strip_general_note(last["text"], note)
            if head is not None:
                last["text"] = head
                q["general_note"] = gnote
                note = None  # note consommée
        # 2. Avertissement de fuite PRÉCIS — deux signatures réelles seulement :
        L = len(last["text"])
        if note and L > 100:
            # (a) note bleue détectée mais NON détachée (le texte de l'option et
            #     celui de la note divergent) : fuite quasi certaine → point de coupe.
            warnings.append(
                f"{code} Q{q['num']} option {last['letter']}: justification bleue du "
                f"jury vraisemblablement collée à l'intitulé — couper avant "
                f"« {note[:60].strip()}… » (vérifier sur le PDF)."
            )
        elif not note and L > 200:
            # (b) pas de note bleue mais dernière option anormalement longue : puces
            #     de correction NOIRES probables (non séparables par couleur, donc
            #     jamais coupées automatiquement — on signale pour coupe manuelle).
            warnings.append(
                f"{code} Q{q['num']} option {last['letter']}: dernière option très "
                f"longue ({L} car.) sans note bleue — vérifier une fuite de "
                f"correction (liste de puces noires) en fin d'intitulé."
            )

    # Identifiants et « texte d'attente d'image » à plat, calculés une seule fois
    # et INDÉPENDAMMENT de la présence d'images : le contrôle « image attendue mais
    # absente » (plus bas) doit tourner même quand l'extraction n'a produit aucune
    # image (échec silencieux). Le texte d'attente inclut le contexte clinique
    # (dpctx) de la 1re question de chaque section — une consigne « cf image …
    # ci-dessous » vit souvent dans ce contexte, pas dans l'énoncé.
    flat_q_ids = [f'{s["code"]}-Q{q["num"]}' for s in sections for q in s["questions"]]
    flat_ctx = []
    for s in sections:
        for i, q in enumerate(s["questions"]):
            ctx = q["stem"]
            if i == 0 and s.get("dpctx"):
                ctx = f'{s["dpctx"]} {ctx}'
            flat_ctx.append(ctx)

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

        if image_events and len(q_page_y) == len(flat_q_ids):
            # Assignation positionnelle SECTION-AWARE.
            #
            # Base : une image appartient à la question « active » = la dernière
            # question dont l'en-tête « Question N: » précède l'image (par (page,
            # y)). Gère les images placées après l'énoncé et celles étalées sur
            # plusieurs pages.
            #
            # Correction de frontière de section (cause du décalage historique) :
            # si un marqueur « Element d'épreuve: » (début de section) s'intercale
            # ENTRE la question active et l'image, l'image n'appartient pas à la
            # question active (= dernière question de la section précédente) mais à
            # la 1re question de la nouvelle section — c'est l'illustration
            # d'ouverture de section, affichée en haut de page avant le premier
            # « Question N: ». Sans cette correction, l'image d'une 1re question
            # (souvent une section verrouillée DP/KFP/mDP) atterrissait sur la
            # dernière question de la section d'avant.
            #
            # LIMITE CONNUE (décalage intra-section, sans frontière de section) :
            # certains exports placent une image dans un emplacement de mise en
            # page FIXE en haut de la page qui la suit (souvent y≈60, juste après
            # un saut de page forcé pour lui faire de la place), AVANT le reliquat
            # d'options de la question précédente qui déborde sur cette même page,
            # alors que l'image illustre en réalité la question SUIVANTE (celle
            # dont l'en-tête n'apparaît que plus bas sur cette page). Vu par
            # (page, y), rien ne distingue ce cas d'une image qui appartient
            # légitimement à la question encore active (même forme : image en
            # haut de page suivie d'un reliquat d'options). Impossible à trancher
            # de façon fiable par la seule position — voir IMG_EXPECTED_RE et la
            # correction de repositionnement plus bas, qui rattrapent les cas où
            # l'énoncé annonce explicitement une image, mais ne couvrent pas les
            # questions qui montrent une image sans jamais la nommer dans le
            # texte (ex. un simple tableau de gaz du sang introduit sans mot-clé
            # « radio/scanner/… »). D'où l'obligation de relecture visuelle
            # (point 6 et 10 de la checklist CLAUDE.md) : ne jamais publier un
            # quiz généré sans vérifier chaque image à l'œil, en particulier
            # toute question dont l'image se trouve juste après un saut de page.
            def owner_for_image(ipos):
                active, active_pos = -1, (-1, -1)
                for i in range(len(q_page_y)):
                    if q_page_y[i] <= ipos and q_page_y[i] > active_pos:
                        active, active_pos = i, q_page_y[i]
                sec_between = [s for s in sec_page_y if active_pos < s <= ipos]
                if sec_between:
                    last_sec = max(sec_between)
                    cands = [(q_page_y[i], i) for i in range(len(q_page_y)) if q_page_y[i] > last_sec]
                    if cands:
                        return min(cands)[1]  # 1re question après le marqueur de section
                return active

            for pno, y, ext, img_data in image_events:
                owner = owner_for_image((pno, y))
                if owner < 0:
                    continue
                qid = flat_q_ids[owner]
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

    # Post-processing : corrige le mauvais placement d'image quand une question
    # attend une image ("est la suivante", "ci-dessous", "cf image"…) mais n'en a
    # pas reçu, alors que la question adjacente en a une sans en avoir besoin.
    for i in range(len(flat_q_ids) - 1):
        qid_curr, qid_next = flat_q_ids[i], flat_q_ids[i + 1]
        curr_expects = bool(IMG_EXPECTED_RE.search(flat_ctx[i]))
        next_expects = bool(IMG_EXPECTED_RE.search(flat_ctx[i + 1]))
        if curr_expects and qid_curr not in images_by_qid and qid_next in images_by_qid and not next_expects:
            images_by_qid[qid_curr] = images_by_qid.pop(qid_next)
            warnings.append(
                f"[images] Image de {qid_next} déplacée vers {qid_curr} "
                f"(le contexte de {qid_curr} attend une image — positionnement PDF corrigé)."
            )

    # Garde-fou : une question dont le contexte/énoncé ANNONCE une image
    # ("ci-dessous", "cf image", "images jointes"…) mais à laquelle AUCUNE image
    # n'a été associée. Couvre l'échec silencieux où l'extraction ne produit rien
    # (image vectorielle/non bitmap, ou filtrée par la taille) : sans ce contrôle,
    # le quiz sortait sans la moindre image ET sans le moindre message.
    missing_img = [
        flat_q_ids[i] for i in range(len(flat_q_ids))
        if IMG_EXPECTED_RE.search(flat_ctx[i]) and flat_q_ids[i] not in images_by_qid
    ]
    if missing_img:
        warnings.append(
            f"[images] {len(missing_img)} question(s) annoncent une image mais n'en ont "
            f"reçu aucune : {', '.join(missing_img)}. L'image est probablement absente de "
            "l'extraction (image vectorielle/non bitmap, ou filtrée par la taille) — "
            "vérifier le PDF source et l'ajouter à la main."
        )

    if images_by_qid:
        n_multi = sum(1 for v in images_by_qid.values() if v.count('<div class="extra">') > 1)
        msg = f"[info] {len(images_by_qid)} image(s) associée(s) automatiquement"
        if n_multi:
            msg += f" (dont {n_multi} question(s) avec {n_multi if n_multi > 1 else 'plusieurs'} images)"
        print(msg + " — vérifie leur placement.")

    meta = guess_metadata(epreuve_code, warnings)

    total_q = sum(len(s["questions"]) for s in sections)
    # D2 : QROC notées (comptées) ; D1 : QROC hors score (cf. build_html).
    if meta["is_d2_guess"]:
        graded_q = total_q
    else:
        graded_q = sum(1 for s in sections for q in s["questions"] if q["type"] != "QROC")

    sub_bits = []
    for s in sections:
        locked = bool(re.search(r"DP|KFP|TCS", s["code"], re.IGNORECASE))
        n = len(s["questions"])
        sub_bits.append(f'{esc(s["code"])} ({n}{", verrouillé" if locked else ""})')
    sub_html = f"{total_q} questions : " + " · ".join(sub_bits)

    # Calcul du chemin relatif au favicon selon la profondeur du dossier.
    # d1/tN/ et d2/tN/ sont à 2 niveaux de la racine (annale à plat dans le
    # dossier de trimestre) ; tout autre dossier éventuel reste à 1 niveau.
    _bc_folder = meta.get("folder", "d1/t4")
    favicon_depth = "../../" if str(_bc_folder).startswith(("d1/", "d2/")) else "../"
    favicon_href = favicon_depth + "favicon.svg"

    out_html = build_html(sections, meta["title_html"], meta["title_html"], sub_html,
                          images_by_qid, favicon_href, is_d2=meta["is_d2_guess"])
    # Injection automatique des quatre scripts globaux, dans l'ordre standard des
    # annales : fil d'Ariane, header dynamique, minuteur d'examen, suivi de
    # progression local. Toute annale officielle (Quiz_UE*.html) doit charger les
    # quatre (cf. « Assets globaux » dans CLAUDE.md) ; timer.js et dynamic-header.js
    # sont inoffensifs sur une page sans « header .scorebar »/« header ».
    _bc_depth  = favicon_depth
    out_html   = out_html.replace(
        "</body>",
        f'<script src="{_bc_depth}breadcrumb.js"></script>\n'
        f'<script src="{_bc_depth}dynamic-header.js"></script>\n'
        f'<script src="{_bc_depth}timer.js"></script>\n'
        f'<script src="{_bc_depth}progress.js"></script>\n</body>',
        1,
    )

    base_dir = os.path.dirname(os.path.abspath(pdf_path))
    out_name = meta["filename"] if meta["ue"] else os.path.splitext(os.path.basename(pdf_path))[0] + ".html"
    out_path = os.path.join(base_dir, out_name)
    # Garde-fou anti-écrasement. Le nom de sortie est DÉDUIT du code d'épreuve
    # (UE + année académique + session). Deux annales distinctes peuvent produire
    # le même nom — ex. une session « BIS » de septembre mal rattachée à l'année
    # suivante — et s'écraser l'une l'autre en silence ; pire, le nom déduit peut
    # entrer en collision avec une annale DÉJÀ publiée et l'écraser. On refuse
    # donc d'écraser un fichier existant sans --force explicite.
    overwrite = os.path.exists(out_path)
    if overwrite and not force:
        print("=" * 70)
        print(f"✗ REFUS D'ÉCRASEMENT : {out_path} existe déjà.")
        print("  Le nom est déduit du code d'épreuve : deux annales différentes")
        print("  peuvent tomber sur le même nom, ou tu t'apprêtes à écraser une")
        print("  annale déjà publiée. Vérifie le nom de sortie attendu, renomme")
        print("  si besoin, puis relance avec --force si l'écrasement est voulu.")
        print("=" * 70)
        sys.exit(2)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_html)
    if overwrite:
        warnings.insert(0, f"[écrasement] {out_name} existait déjà et a été régénéré (--force).")

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

    # ── Scan post-génération : PUA restants et [A VERIFIER] ──────────────────
    pua_re = re.compile(r"[-]")
    pua_found = pua_re.findall(out_html)
    if pua_found:
        unique_pua = list(dict.fromkeys(pua_found))
        hex_list = ", ".join(f"U+{ord(c):04X}" for c in unique_pua[:8])
        warnings.append(
            f"[ligatures] {len(pua_found)} caractère(s) PUA non résolus dans le HTML "
            f"({hex_list}{'…' if len(unique_pua) > 8 else ''}). "
            "Ajouter ces codepoints à la table LIGATURES de ce script, "
            "ou corriger manuellement dans le HTML généré."
        )
    a_verifier_count = out_html.count("[A VERIFIER]")

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

    if strict and (a_verifier_count or pua_found):
        print(f"\n[--strict] Sortie avec code 1 : "
              f"{a_verifier_count} [A VERIFIER], {len(pua_found)} PUA restants.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Convertit une annale PDF en quiz HTML BobMed.")
    parser.add_argument("pdf", help="Chemin du fichier PDF à convertir")
    parser.add_argument("--debug",  action="store_true", help="Écrit aussi un .debug.json")
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 si des marqueurs [A VERIFIER] ou des PUA non résolus restent dans le HTML."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Autorise l'écrasement d'un fichier de sortie existant (sinon refus + exit 2)."
    )
    args = parser.parse_args()
    run(args.pdf, debug=args.debug, strict=args.strict, force=args.force)


if __name__ == "__main__":
    main()
