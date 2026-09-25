#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quiz_agent.py — Vérification de fidélité PDF→HTML par comparaison structurée.

Compare le debug.json produit par pdf_to_quiz.py (source PDF parsée) avec le
quiz HTML final. Détecte :
  - data-correct incorrect par rapport aux options "Valide" du PDF
  - Divergences de texte (énoncé, intitulé d'option) entre PDF et HTML
  - Types de questions incorrects
  - Réponses QROC manquantes ou incomplètes

Les divergences textuelles non triviales sont envoyées à Claude Haiku pour
classification (dérive de ligature vs. erreur réelle), ce qui coûte ~1 centimes
par quiz.

Usage:
    python3 quiz_agent.py Quiz_UE7.3_2023-2024_S1.html
    python3 quiz_agent.py Quiz_UE7.3_2023-2024_S1.html --debug quiz.debug.json
    python3 quiz_agent.py Quiz.html --no-api   # vérifications mécaniques seulement

Prérequis:
    pip install beautifulsoup4 anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

Exit codes:
    0 — aucun problème détecté
    1 — au moins un problème détecté
    2 — erreur d'exécution
"""

import sys
import re
import json
import os
import argparse
import unicodedata
from pathlib import Path

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

# ── Couleurs terminal ─────────────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty()
def _c(code, s): return f"\033[{code}m{s}\033[0m" if _USE_COLOR else s
def red(s):   return _c("31;1", s)
def amber(s): return _c("33;1", s)
def green(s): return _c("32;1", s)
def dim(s):   return _c("2", s)
def bold(s):  return _c("1", s)

# ── Constantes ────────────────────────────────────────────────────────────────
TEXT_DIFF_THRESHOLD = 0.20   # 20% de différence = signalé
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Le HTML fusionne certains types : TCS est rendu data-type="QRU". QRPL et QRP
# gardent en revanche leur propre data-type (barème/plafond dédiés). Pour comparer
# debug.json (type source) au HTML, on canonicalise le type source vers son type HTML.
DEBUG_TO_HTML_TYPE = {"TCS": "QRU"}

def canon_type(t: str) -> str:
    return DEBUG_TO_HTML_TYPE.get(t, t)


# ── Extraction depuis le HTML ──────────────────────────────────────────────────

def extract_html_questions(html_path: Path) -> list[dict]:
    """Extrait les questions structurées depuis le HTML via BeautifulSoup."""
    if not _HAS_BS4:
        raise RuntimeError("beautifulsoup4 non installé — pip install beautifulsoup4")

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    questions = []

    for q_el in soup.select(".q"):
        qid = q_el.get("id", "?")
        qtype = q_el.get("data-type", "?")
        data_correct = q_el.get("data-correct", "")

        # Un énoncé peut être découpé en plusieurs .stem intercalés avec les images
        # (texte → image → texte → image, cf. split_stem_at_images de
        # pdf_to_quiz.py) : on les recolle pour comparer au texte PDF continu.
        stem = " ".join(el.get_text(" ", strip=True) for el in q_el.select(".stem"))

        opts = []
        for opt_el in q_el.select(".opt"):
            letter = opt_el.get("data-l", "?")
            otext_el = opt_el.select_one(".otext")
            text = otext_el.get_text(" ", strip=True) if otext_el else ""
            opts.append({
                "letter": letter, "text": text,
                "mandatory": opt_el.get("data-mandatory") == "1",
                "unacceptable": opt_el.get("data-unacceptable") == "1",
                "neutral": opt_el.get("data-neutral") == "1",
            })

        # Correction items (VRAI/FAUX justifications)
        correction_items = []
        for ci in q_el.select(".citem"):
            cl_el = ci.select_one(".cl")
            cv_el = ci.select_one(".cv")
            full_text = ci.get_text(" ", strip=True)
            correction_items.append({
                "label": cl_el.get_text(strip=True) if cl_el else "",
                "verdict": cv_el.get_text(strip=True) if cv_el else "",
                "text": full_text,
            })

        # QROC model answer — les quiz générés utilisent .qrocans,
        # les quiz rédigés à la main peuvent utiliser .qrocmodel.
        qroc_model = ""
        qm_el = q_el.select_one(".qrocans, .qrocmodel")
        if qm_el:
            qroc_model = qm_el.get_text(" ", strip=True)

        questions.append({
            "id": qid,
            "type": qtype,
            "data_correct": data_correct.upper(),
            "stem": stem,
            "opts": opts,
            "correction_items": correction_items,
            "qroc_model": qroc_model,
            "neutralized": q_el.get("data-neutral") == "1",
        })

    return questions


# ── Extraction depuis le debug JSON ───────────────────────────────────────────

def extract_debug_questions(debug: dict) -> list[dict]:
    """Aplatit les sections du debug JSON en liste de questions."""
    questions = []
    for section in debug.get("sections", []):
        code = section.get("code", "?")
        for q in section.get("questions", []):
            num = q.get("num", "?")
            qtype = q.get("type", "?")
            opts = q.get("options", [])
            # data_correct attendu = lettres des options valid=True
            # Un item « Neutraliser » n'est jamais une bonne réponse (ancien debug.json :
            # il y était encore marqué valid) — cf. pdf_to_quiz.py.
            correct_letters = "".join(
                sorted(o["letter"] for o in opts if o.get("valid") and not o.get("neutral"))
            ).upper()
            questions.append({
                "id": f"{code}-Q{num}",
                "type": qtype,
                "expected_correct": correct_letters,
                "stem": q.get("stem", ""),
                "opts": [{"letter": o["letter"], "text": o.get("text", ""), "expl": o.get("expl"),
                          "mandatory": bool(o.get("mandatory")),
                          "unacceptable": bool(o.get("unacceptable")),
                          "neutral": bool(o.get("neutral"))} for o in opts],
                "neutralized": bool(q.get("neutralized")),
                "qroc_answers": q.get("qroc_answers", []),
            })
    return questions


# ── Appariement par contenu ───────────────────────────────────────────────────

def _alnum(t: str) -> str:
    return re.sub(r"[^0-9a-zà-ÿ]", "", (t or "").lower())


def align_by_content(html_qs: list[dict], debug_qs: list[dict]) -> int:
    """Renomme les questions du debug.json dont l'identifiant n'existe pas dans le
    HTML (ex. « QI(20)-Q3 » côté PDF vs « SQI1-Q3 » côté site) vers la question HTML
    de même CONTENU (énoncé, sinon options). Sans cela, une annale rédigée ou
    retouchée à la main n'était comparée à rien (tout « MISSING_QUESTION ») : c'est
    ce qui a laissé passer, sur le site, des TCS mal notées, des items
    indispensable/inacceptable perdus et des réponses différentes du fichier
    réponse. Renvoie le nombre de questions ré-appariées."""
    import difflib
    html_ids = {q["id"] for q in html_qs}
    free_html = [q for q in html_qs if q["id"] not in {d["id"] for d in debug_qs}]
    todo = [d for d in debug_qs if d["id"] not in html_ids]

    def key(stem, opts):
        return _alnum(stem)[:200] + "|" + "|".join(_alnum(o["text"])[:30] for o in opts)

    cands = []
    for d in todo:
        kd = key(d["stem"], d["opts"])
        for h in free_html:
            sd, sh = _alnum(d["stem"]), _alnum(h["stem"])
            r = 0.0
            if len(sd) >= 60 and len(sh) >= 60:
                r = difflib.SequenceMatcher(None, sd[:300], sh[:300], autojunk=False).ratio()
            if r < 0.9:
                r = max(r, 0.95 * difflib.SequenceMatcher(None, kd, key(h["stem"], h["opts"]), autojunk=False).ratio())
            if r >= 0.6:
                cands.append((r, d["id"], h["id"]))
    cands.sort(reverse=True)
    used_d, used_h, n = set(), set(), 0
    by_id = {d["id"]: d for d in todo}
    for r, did, hid in cands:
        if did in used_d or hid in used_h:
            continue
        used_d.add(did); used_h.add(hid)
        by_id[did]["id"] = hid
        n += 1
    return n


def debug_from_pdf(pdf_path: Path) -> dict:
    """Génère la structure debug.json directement depuis le FICHIER RÉPONSE, via
    pdf_to_quiz.py dans un dossier temporaire (rien n'est écrit à côté du PDF)."""
    import importlib.util, io, contextlib, tempfile, shutil
    spec = importlib.util.spec_from_file_location("pdf_to_quiz", Path(__file__).with_name("pdf_to_quiz.py"))
    p2q = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(p2q)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "reponse.pdf"
        shutil.copy(pdf_path, src)
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                p2q.run(str(src), debug=True, force=True)
        except SystemExit as e:
            if e.code not in (0, None, 3):   # 3 = incohérence indispensable/inacceptable (signalée dans le HTML)
                raise RuntimeError(out.getvalue().strip().splitlines()[-4:] or f"exit {e.code}")
        js = list(Path(tmp).glob("*.debug.json"))
        if not js:
            raise RuntimeError("pdf_to_quiz.py n'a produit aucun debug.json")
        return json.loads(js[0].read_text(encoding="utf-8"))


# ── Comparaison mécanique ─────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Normalise le texte pour comparaison : NFD, minuscule, espaces simplifiés."""
    t = unicodedata.normalize("NFD", text)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")  # strip accents
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _edit_distance_ratio(a: str, b: str) -> float:
    """Ratio [0,1] de différence entre deux chaînes (0 = identique)."""
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0
    # Longueur max pour éviter une complexité O(n²) sur de grands textes
    max_len = 300
    na, nb = _normalize(a)[:max_len], _normalize(b)[:max_len]
    if na == nb:
        return 0.0
    # Algorithme de Levenshtein simplifié
    len_a, len_b = len(na), len(nb)
    if len_a == 0 or len_b == 0:
        return 1.0
    prev = list(range(len_b + 1))
    for i, ca in enumerate(na):
        curr = [i + 1]
        for j, cb in enumerate(nb):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (0 if ca == cb else 1)))
        prev = curr
    dist = prev[len_b]
    max_chars = max(len_a, len_b)
    return dist / max_chars


def mechanical_check(html_qs: list[dict], debug_qs: list[dict]) -> list[dict]:
    """Comparaison mécanique PDF vs HTML. Retourne liste de findings."""
    findings = []

    # Indexer les questions HTML par id
    html_by_id = {q["id"]: q for q in html_qs}
    debug_by_id = {q["id"]: q for q in debug_qs}

    # Questions manquantes
    for qid in debug_by_id:
        if qid not in html_by_id:
            findings.append({
                "level": "error",
                "code": "MISSING_QUESTION",
                "qid": qid,
                "message": f"[{qid}] Question présente dans le PDF mais absente du HTML.",
            })

    for qid, dq in debug_by_id.items():
        if qid not in html_by_id:
            continue
        hq = html_by_id[qid]

        dtype = dq["type"]          # type source (QRM/QRU/QROC/TCS/QRPL/QZONE)
        htype = hq["type"]          # data-type HTML (QRM/QRU/QROC/QZONE)
        dtype_html = canon_type(dtype)   # type source projeté sur le rendu HTML

        # Type — comparer après canonicalisation (TCS→QRU). QRP et QRPL ont le même
        # barème (X/N + plafond) : équivalents. En revanche QRM (discordance) ≠
        # QRP/QRPL (proportionnel) change la note : c'est une ERREUR. Vérifié sur les
        # copies du dépôt des annales : une question étiquetée QRM dans le fichier
        # réponse est TOUJOURS notée à la discordance (589/589), même si l'énoncé dit
        # « sélectionnez les 3… » ; 11 questions du site étaient notées avec l'autre barème.
        prop = {"QRP", "QRPL"}
        same_scale = dtype_html == htype or (dtype_html in prop and htype in prop)
        if not same_scale and htype not in ("?",) and dtype != "QZONE":
            scoring = {dtype_html, htype} & prop and {dtype_html, htype} & {"QRM"}
            findings.append({
                "level": "error" if scoring else "warning",
                "code": "TYPE_MISMATCH",
                "qid": qid,
                "message": (
                    f"[{qid}] Type PDF={dtype} (→{dtype_html}), HTML={htype}"
                    + (" — barème différent (discordance ≠ proportionnel) : aligner data-type sur le fichier réponse."
                       if scoring else ".")
                ),
            })

        # data-correct
        if dtype not in ("QROC", "QZONE") and htype not in ("QROC", "QZONE"):
            expected = dq["expected_correct"]          # lettres valides du PDF
            actual = hq["data_correct"]
            exp_set = set(expected)
            act_set = set(actual)

            if htype == "QRU":
                # QRU/TCS : le HTML retient UNE réponse (choix pédagogique parmi les
                # options valides). Erreur seulement si cette réponse n'est PAS valide
                # dans le PDF, ou si le PDF n'a aucune option valide.
                if exp_set and not act_set.issubset(exp_set):
                    findings.append({
                        "level": "error",
                        "code": "WRONG_CORRECT",
                        "qid": qid,
                        "pdf_correct": expected,
                        "html_correct": actual,
                        "message": (
                            f"[{qid}] QRU data-correct HTML=\"{actual}\" absent des "
                            f"options valides PDF=\"{expected}\"."
                        ),
                    })
                elif len(exp_set) > 1 and act_set != exp_set:
                    # Plusieurs réponses « Valide » dans le fichier réponse (TCS
                    # validée par plusieurs experts) : TOUTES sont justes et doivent
                    # être créditées (data-correct = toutes les lettres valides +
                    # poids data-w, cf. tcs_weights de pdf_to_quiz.py). En retenir
                    # une seule donne 0 point à une réponse validée par le jury.
                    others = sorted(exp_set - act_set)
                    findings.append({
                        "level": "error",
                        "code": "TCS_VALID_NOT_CREDITED",
                        "qid": qid,
                        "message": (
                            f"[{qid}] Le fichier réponse valide {expected} mais le HTML "
                            f"ne crédite que \"{actual}\" : {others} vaudraient 0 point. "
                            "Créditer toutes les réponses validées (data-correct + data-w)."
                        ),
                    })
            else:
                # QRM/QRPL : correspondance exacte de l'ensemble des lettres.
                if exp_set != act_set:
                    findings.append({
                        "level": "error",
                        "code": "WRONG_CORRECT",
                        "qid": qid,
                        "pdf_correct": expected,
                        "html_correct": actual,
                        "message": (
                            f"[{qid}] data-correct HTML=\"{actual}\" ≠ "
                            f"options valides PDF=\"{expected}\"."
                        ),
                    })

        # Items indispensable / inacceptable : chaque libellé du fichier réponse doit
        # se retrouver sur la bonne option du HTML (et réciproquement). Un attribut
        # perdu fausse la note sans aucun symptôme visible (bug confirmé : mDP1-Q6 E
        # « Inacceptable », UE8.2 juillet 2024, absent du HTML publié).
        h_opts = {o["letter"]: o for o in hq["opts"]}
        for po in dq["opts"]:
            ho = h_opts.get(po["letter"])
            if ho is None:
                continue
            for key, label in (("mandatory", "indispensable"), ("unacceptable", "inacceptable"),
                               ("neutral", "neutralisé")):
                if po.get(key) != ho.get(key):
                    findings.append({
                        "level": "error",
                        "code": "SPECIAL_ITEM_MISMATCH",
                        "qid": qid,
                        "message": (
                            f"[{qid}] Option {po['letter']} : item {label} "
                            f"{'dans le PDF mais absent du HTML' if po.get(key) else 'dans le HTML mais pas dans le PDF'} "
                            f"(attribut data-{key}=\"1\")."
                        ),
                    })

        # Question neutralisée par le jury : point accordé à tous (data-neutral sur la .q).
        if dq.get("neutralized") != hq.get("neutralized"):
            findings.append({
                "level": "error",
                "code": "NEUTRAL_QUESTION_MISMATCH",
                "qid": qid,
                "message": (
                    f"[{qid}] Question neutralisée "
                    f"{'dans le PDF mais pas dans le HTML' if dq.get('neutralized') else 'dans le HTML mais pas dans le PDF'} "
                    "(attribut data-neutral=\"1\" sur la .q)."
                ),
            })

        # Nombre d'options
        n_pdf = len(dq["opts"])
        n_html = len(hq["opts"])
        if n_pdf and n_html and n_pdf != n_html:
            findings.append({
                "level": "warning",
                "code": "OPT_COUNT_MISMATCH",
                "qid": qid,
                "message": f"[{qid}] {n_pdf} options dans le PDF, {n_html} dans le HTML.",
            })

        # QROC : vérifier que les réponses sont présentes
        if dq["type"] == "QROC" and dq["qroc_answers"]:
            if not hq["qroc_model"].strip():
                findings.append({
                    "level": "warning",
                    "code": "QROC_EMPTY_MODEL",
                    "qid": qid,
                    "message": f"[{qid}] QROC : le PDF indique des réponses attendues mais qrocmodel est vide.",
                })

    return findings


def collect_text_divergences(html_qs: list[dict], debug_qs: list[dict]) -> list[dict]:
    """Collecte les paires (PDF text, HTML text) qui diffèrent significativement."""
    divs = []
    debug_by_id = {q["id"]: q for q in debug_qs}

    for hq in html_qs:
        qid = hq["id"]
        if qid not in debug_by_id:
            continue
        dq = debug_by_id[qid]

        # Stem
        ratio = _edit_distance_ratio(dq["stem"], hq["stem"])
        if ratio > TEXT_DIFF_THRESHOLD and dq["stem"]:
            divs.append({
                "qid": qid,
                "field": "stem",
                "pdf": dq["stem"][:250],
                "html": hq["stem"][:250],
                "ratio": round(ratio, 3),
            })

        # Options
        pdf_opts = {o["letter"]: o for o in dq["opts"]}
        for ho in hq["opts"]:
            letter = ho["letter"]
            if letter not in pdf_opts:
                continue
            po = pdf_opts[letter]
            ratio_opt = _edit_distance_ratio(po["text"], ho["text"])
            if ratio_opt > TEXT_DIFF_THRESHOLD and po["text"]:
                divs.append({
                    "qid": qid,
                    "field": f"opt_{letter}",
                    "pdf": po["text"][:200],
                    "html": ho["text"][:200],
                    "ratio": round(ratio_opt, 3),
                })

    return divs


# ── Appel à Claude Haiku ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Tu es un assistant de contrôle qualité pour des quiz médicaux HTML. \
On te soumet des divergences de texte entre une source PDF (brut parsé) et le HTML final. \
Ta tâche : classer chaque divergence en catégorie et décider si elle nécessite une correction.

Catégories:
- LIGATURE : un caractère "fi"/"fl"/"ff" a disparu dans la source PDF (le HTML est vraisemblablement meilleur)
- ACCENTS : différence d'accentuation ou de casse sans impact sur le sens
- CORRECTION_REQUISE : le HTML diffère du PDF de façon substantielle et doit être corrigé
- BRUIT_PDF : le PDF source contenait du bruit parasite absent du HTML (le HTML est meilleur)
- INCERTAIN : impossible de trancher sans voir le PDF original

Réponds uniquement par un objet JSON : {"divergences": [{"id": "qid:field", "category": "...", "note": "..."}]}
"""


def call_claude(divergences: list[dict]) -> list[dict]:
    """Envoie les divergences à Claude Haiku et retourne les classifications."""
    try:
        import anthropic
    except ImportError:
        print(amber("⚠ anthropic non installé — classifications Claude désactivées."), file=sys.stderr)
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(amber("⚠ ANTHROPIC_API_KEY non défini — classifications Claude désactivées."), file=sys.stderr)
        return []

    client = anthropic.Anthropic(api_key=api_key)

    # Construire le message utilisateur compact
    items = []
    for d in divergences[:30]:  # max 30 divergences par appel
        items.append(
            f'id="{d["qid"]}:{d["field"]}" '
            f'pdf="{d["pdf"][:150]}" '
            f'html="{d["html"][:150]}" '
            f'ratio={d["ratio"]}'
        )
    user_msg = "Divergences à classifier :\n" + "\n---\n".join(items)

    try:
        resp = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        # Récupérer le premier bloc texte (robuste si un bloc thinking précède).
        raw = ""
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                raw = block.text.strip()
                break
        if not raw:
            print(amber("⚠ Réponse Claude sans bloc texte exploitable."), file=sys.stderr)
            return []
        # Extraire le JSON de la réponse
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            return data.get("divergences", [])
        print(amber("⚠ Réponse Claude sans JSON exploitable."), file=sys.stderr)
    except Exception as e:
        print(amber(f"⚠ Erreur API Claude : {e}"), file=sys.stderr)

    return []


# ── Rapport ───────────────────────────────────────────────────────────────────

def print_report(
    html_path: Path,
    mechanical: list[dict],
    text_divs: list[dict],
    claude_results: list[dict],
    use_api: bool,
) -> None:
    fn = html_path.name
    errors   = [f for f in mechanical if f["level"] == "error"]
    warnings = [f for f in mechanical if f["level"] == "warning"]

    # Enrichir les divergences texte avec les classifications Claude.
    # Règle : rien n'est masqué silencieusement. Une divergence est classée
    # bénigne (ligature/accent/bruit PDF) UNIQUEMENT si Claude l'a explicitement
    # jugée telle ; sinon elle est signalée pour relecture.
    claude_by_id = {d["id"]: d for d in claude_results}
    benign_cats = {"LIGATURE", "ACCENTS", "BRUIT_PDF"}
    needs_correction = []   # (td, cl|None)
    for td in text_divs:
        key = f"{td['qid']}:{td['field']}"
        cl = claude_by_id.get(key)
        if cl and cl.get("category") in benign_cats:
            continue   # bénigne, confirmée par Claude → non signalée
        needs_correction.append((td, cl))

    total_issues = len(errors) + len(needs_correction)

    print()
    if total_issues == 0 and not warnings:
        print(green(f"✓ {fn}") + dim(" — aucun problème de fidélité détecté"))
    else:
        status = red(f"✗ {fn}") if errors or needs_correction else amber(f"⚠ {fn}")
        print(status + dim(f" — {len(errors)} erreur(s) · {len(warnings)} avertissement(s) · {len(needs_correction)} divergence(s) texte"))

    for f in mechanical:
        lvl = red("ERREUR") if f["level"] == "error" else amber("AVERT ")
        print(f"  {lvl} [{f['code']}] {f['message']}")

    if needs_correction:
        print(bold("\n  Divergences texte à relire :"))
        for td, cl in needs_correction:
            note = cl.get("note", "") if cl else ""
            cat  = cl.get("category", "INCERTAIN") if cl else "NON_VERIFIE"
            blocking = (cat == "CORRECTION_REQUISE")
            head = f"  {'✗' if blocking else '⚠'} [{td['qid']}:{td['field']}] {cat} (ratio={td['ratio']})"
            print(red(head) if blocking else amber(head))
            print(dim(f"      PDF  : {td['pdf'][:100]}"))
            print(dim(f"      HTML : {td['html'][:100]}"))
            if note:
                print(dim(f"      Note : {note}"))

    benign = [td for td in text_divs
              if f"{td['qid']}:{td['field']}" in claude_by_id
              and claude_by_id[f"{td['qid']}:{td['field']}"].get("category") in benign_cats]
    if benign:
        print(dim(f"\n  {len(benign)} divergence(s) texte bénigne(s) (ligatures/accents/bruit PDF)."))


def build_json_report(
    html_path: Path,
    mechanical: list[dict],
    text_divs: list[dict],
    claude_results: list[dict],
    use_api: bool,
) -> dict:
    claude_by_id = {d["id"]: d for d in claude_results}
    enriched_divs = []
    for td in text_divs:
        key = f"{td['qid']}:{td['field']}"
        cl = claude_by_id.get(key)
        enriched_divs.append({**td, "claude": cl})

    errors = [f for f in mechanical if f["level"] == "error"]
    warnings = [f for f in mechanical if f["level"] == "warning"]
    blocking_text = any(
        (cl or {}).get("category") == "CORRECTION_REQUISE"
        for cl in (claude_by_id.get(f"{td['qid']}:{td['field']}") for td in text_divs)
    )
    return {
        "file": str(html_path),
        "mechanical_findings": mechanical,
        "text_divergences": enriched_divs,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "blocking": bool(errors) or blocking_text,
        "api_used": use_api,
    }


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Vérification de fidélité PDF→HTML pour les quiz BobMed."
    )
    parser.add_argument("html", help="Fichier quiz HTML généré par pdf_to_quiz.py")
    parser.add_argument(
        "--debug", metavar="DEBUG_JSON",
        help="Fichier .debug.json produit par pdf_to_quiz.py --debug "
             "(auto-détecté si absent)"
    )
    parser.add_argument(
        "--pdf", metavar="FICHIER_REPONSE_PDF",
        help="Fichier réponse de l'annale (PDF Uness) : le debug.json est généré à la "
             "volée via pdf_to_quiz.py — permet d'auditer n'importe quelle annale publiée"
    )
    parser.add_argument(
        "--no-api", action="store_true",
        help="Désactiver l'appel à Claude (vérifications mécaniques seulement)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Sortie JSON seule"
    )
    args = parser.parse_args()

    html_path = Path(args.html)
    if not html_path.exists():
        print(red(f"✗ Fichier introuvable : {html_path}"), file=sys.stderr)
        sys.exit(2)

    if not _HAS_BS4:
        print(red("✗ beautifulsoup4 non installé — pip install beautifulsoup4"), file=sys.stderr)
        sys.exit(2)

    # Auto-détection du debug JSON
    debug_path = Path(args.debug) if args.debug else html_path.with_suffix(".debug.json")
    if args.pdf:
        debug_path = None
    elif not debug_path.exists():
        # Chercher dans le même dossier avec le même stem
        alt = html_path.parent / (html_path.stem + ".debug.json")
        if alt.exists():
            debug_path = alt
        else:
            print(amber(
                f"⚠ debug.json introuvable ({debug_path}). "
                "Régénérer avec : python3 pdf_to_quiz.py --debug annale.pdf\n"
                "  → Seules les vérifications internes HTML seront effectuées."
            ), file=sys.stderr)
            debug_path = None

    # Extraction HTML
    try:
        html_qs = extract_html_questions(html_path)
    except Exception as e:
        print(red(f"✗ Erreur lecture HTML : {e}"), file=sys.stderr)
        sys.exit(2)

    # Extraction debug JSON
    debug_qs = []
    if args.pdf:
        try:
            debug_qs = extract_debug_questions(debug_from_pdf(Path(args.pdf)))
        except Exception as e:
            print(red(f"✗ Lecture du fichier réponse impossible : {e}"), file=sys.stderr)
            sys.exit(2)
    elif debug_path:
        try:
            debug = json.loads(debug_path.read_text(encoding="utf-8"))
            debug_qs = extract_debug_questions(debug)
        except Exception as e:
            print(amber(f"⚠ Erreur lecture {debug_path} : {e}"), file=sys.stderr)
    if debug_qs:
        realigned = align_by_content(html_qs, debug_qs)
        if realigned and not args.json:
            print(dim(f"  {realigned} question(s) appariée(s) par contenu (identifiants PDF ≠ HTML)."))

    # Vérifications mécaniques
    mechanical = mechanical_check(html_qs, debug_qs) if debug_qs else []

    # Divergences texte
    text_divs = collect_text_divergences(html_qs, debug_qs) if debug_qs else []

    # Appel Claude (si activé et si divergences à classer)
    use_api = not args.no_api
    claude_results = []
    if use_api and text_divs:
        claude_results = call_claude(text_divs)

    if args.json:
        report = build_json_report(html_path, mechanical, text_divs, claude_results, use_api)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(html_path, mechanical, text_divs, claude_results, use_api)
        if not debug_qs:
            print(dim("\n  Aucun debug.json — comparaison PDF/HTML non effectuée."))

    errors = [f for f in mechanical if f["level"] == "error"]
    # Divergences texte classées CORRECTION_REQUISE comptent comme erreurs bloquantes
    claude_by_id = {d["id"]: d for d in claude_results}
    blocking_text = any(
        claude_by_id.get(f"{td['qid']}:{td['field']}", {}).get("category") == "CORRECTION_REQUISE"
        for td in text_divs
    )
    if errors or blocking_text:
        sys.exit(1)


if __name__ == "__main__":
    main()
