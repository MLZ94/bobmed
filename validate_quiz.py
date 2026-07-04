#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_quiz.py — Validateur automatique de quiz HTML BobMed.

Remplace la relecture manuelle des 13 points de checklist. S'exécute en < 1 s
sur n'importe quel quiz HTML et sort un rapport structuré.

Usage:
    python3 validate_quiz.py Quiz_UE7.3_2024-2025_S1.html
    python3 validate_quiz.py d2/t4/*.html          # glob
    python3 validate_quiz.py --json Quiz.html      # sortie JSON seule

Exit codes:
    0 — aucune erreur bloquante (publication possible)
    1 — au moins une erreur bloquante (publication bloquée)

Dépendances:
    pip install beautifulsoup4
"""

import sys
import re
import json
import argparse
from pathlib import Path

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

# ── Affichage terminal coloré ─────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty()
def _c(code, s): return f"\033[{code}m{s}\033[0m" if _USE_COLOR else s
def red(s):   return _c("31;1", s)
def amber(s): return _c("33;1", s)
def green(s): return _c("32;1", s)
def dim(s):   return _c("2", s)
def bold(s):  return _c("1", s)

# ── PUA Unicode (ligatures non résolues) ──────────────────────────────────────
# Plage Private Use Area — signe d'une ligature PDF non traitée dans LIGATURES.
PUA_RE = re.compile(r"[-]")

# ── Mots tronqués par ligature perdue (haute confiance uniquement) ────────────
# Ces formes N'EXISTENT PAS en français — elles ne peuvent résulter que de la
# perte d'une ligature (fi/fl/ff) dans l'extraction PDF.
# Ne pas ajouter de patterns qui matchent des sous-chaînes de mots valides.
_BROKEN_WORDS = [
    # fl disparu : réflexe → réexe, réexion ; inflammation → inammation
    (re.compile(r"\bréexe",        re.I), True),
    (re.compile(r"\bréex",         re.I), True),
    (re.compile(r"\binamm?ati",    re.I), True),   # inammation / inflammation
    (re.compile(r"\binamm?atoire", re.I), True),
    (re.compile(r"\buide\b",       re.I), True),   # fluide → uide
    # fi disparu : efficace → ecace, profil → prol
    (re.compile(r"\becace\b",      re.I), True),
    (re.compile(r"\becacité\b",    re.I), True),
    (re.compile(r"\bprol\b",       re.I), True),   # profil → prol
    # ff disparu : effet → efet, suffisant → sufisant
    (re.compile(r"\befet\b",       re.I), True),
    (re.compile(r"\befets\b",      re.I), True),
    (re.compile(r"\bsufsant",      re.I), True),   # suffisant → sufsant
]


# ── Checks individuels ────────────────────────────────────────────────────────

def _check_a_verifier(html_text: str) -> list[dict]:
    count = html_text.count("[A VERIFIER]")
    if not count:
        return []
    # Identifier quels contextes (pour aider l'utilisateur)
    positions = [m.start() for m in re.finditer(r"\[A VERIFIER\]", html_text)]
    samples = []
    for pos in positions[:3]:
        snippet = html_text[max(0, pos-40):pos+50].replace("\n", " ").strip()
        samples.append(snippet)
    return [{
        "level":   "error",
        "code":    "A_VERIFIER",
        "message": f"{count} marqueur(s) [A VERIFIER] non résolus — publication bloquée.",
        "count":   count,
        "samples": samples,
    }]


def _check_pua(plain_text: str) -> list[dict]:
    matches = PUA_RE.findall(plain_text)
    if not matches:
        return []
    unique = list(dict.fromkeys(matches))
    hex_list = ", ".join(f"U+{ord(c):04X}" for c in unique[:8])
    return [{
        "level":      "error",
        "code":       "PUA_LIGATURE",
        "message":    (
            f"{len(matches)} caractère(s) PUA non résolus (ligature absente). "
            f"Codepoints: {hex_list}{'…' if len(unique) > 8 else ''}. "
            "Ajouter à la table LIGATURES de pdf_to_quiz.py."
        ),
        "count":      len(matches),
        "codepoints": [f"U+{ord(c):04X}" for c in unique],
    }]


def _check_header_wrap(html_text: str) -> list[dict]:
    """Détecte un <div class="wrap"> interne dans le <header> — aveugle initLocks()."""
    m = re.search(r"<header[^>]*>(.*?)</header>", html_text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    inner = m.group(1)
    if not re.search(r'class=["\'][^"\']*\bwrap\b', inner):
        return []
    return [{
        "level":   "error",
        "code":    "HEADER_WRAP",
        "message": (
            "Le <header> contient un <div class=\"wrap\"> interne — "
            "initLocks() ciblera ce .wrap vide, le verrouillage DP/KFP/TCS sera cassé. "
            "Renommer en .hwrap."
        ),
    }]


def _check_data_correct(soup) -> list[dict]:
    """Cohérence data-correct ↔ lettres d'options réelles ; QROC doit être vide."""
    if soup is None:
        return []
    findings = []
    for q in soup.select(".q"):
        qid   = q.get("id", "?")
        qtype = q.get("data-type", "")
        raw   = q.get("data-correct", "")

        # Questions à réponse numérique (quiz biostat) : notation par data-exp /
        # data-tol (valeur attendue ± tolérance), pas par data-correct/options.
        # Format valide — ne pas exiger de data-correct.
        if q.has_attr("data-exp"):
            continue

        if qtype == "QROC":
            if raw.strip():
                findings.append({
                    "level":   "warning",
                    "code":    "QROC_NONEMPTY_CORRECT",
                    "message": f"[{qid}] QROC avec data-correct non vide : \"{raw}\"",
                })
            continue

        if not raw.strip():
            if qtype not in ("QROC",):
                findings.append({
                    "level":   "warning",
                    "code":    "EMPTY_CORRECT",
                    "message": f"[{qid}] data-correct vide sur une question de type {qtype or '?'}.",
                })
            continue

        opts = q.select(".opt")
        if not opts:
            continue
        opt_letters  = {o.get("data-l", "") for o in opts} - {""}
        corr_letters = set(raw.upper()) - {""}

        unknown = corr_letters - opt_letters
        if unknown:
            findings.append({
                "level":   "warning",
                "code":    "CORRECT_LETTER_UNKNOWN",
                "message": (
                    f"[{qid}] data-correct=\"{raw}\" contient {sorted(unknown)} "
                    f"absentes des options réelles ({sorted(opt_letters)})."
                ),
            })

        if qtype == "QRU" and len(corr_letters) > 1:
            findings.append({
                "level":   "warning",
                "code":    "QRU_MULTI_CORRECT",
                "message": (
                    f"[{qid}] QRU mais data-correct=\"{raw}\" — "
                    "une seule lettre attendue."
                ),
            })
    return findings


def _check_section_titles(soup) -> list[dict]:
    """Sections DP/KFP/TCS/mDP sans intitulé médical (juste le code brut)."""
    if soup is None:
        return []
    findings = []
    # Seules les sections qui seront verrouillées ont besoin d'un sujet clinique.
    # SQI sont libres et n'ont pas de contexte clinique associé.
    NEEDS_TITLE = re.compile(r"^(DP|KFP|TCS|mDP)\s*\d+$", re.I)
    for el in soup.select(".sect"):
        title = el.get_text(strip=True)
        if NEEDS_TITLE.match(title):
            findings.append({
                "level":   "warning",
                "code":    "SECTION_NO_TITLE",
                "message": (
                    f"Section \"{title}\" sans sujet clinique — "
                    "ajouter le thème (ex : DP1 — Cancer du pancréas)."
                ),
            })
    return findings


def _check_broken_words(plain_text: str) -> list[dict]:
    """Détecte des mots qui ressemblent à des mots médicaux tronqués par ligature."""
    findings = []
    for pattern, high_conf in _BROKEN_WORDS:
        m = pattern.search(plain_text)
        if m:
            findings.append({
                "level":   "error" if high_conf else "warning",
                "code":    "BROKEN_WORD",
                "message": f"Mot potentiellement tronqué : \"{m.group(0)}\" — ligature absente probable.",
                "match":   m.group(0),
            })
    return findings


def _check_initlocks_call(html_text: str) -> list[dict]:
    """Vérifie que initLocks() est appelé dans le script."""
    if "initLocks()" not in html_text:
        return [{
            "level":   "warning",
            "code":    "NO_INITLOCKS",
            "message": "initLocks() absent du script — le verrouillage DP/KFP/TCS ne fonctionnera pas.",
        }]
    return []


# ── Entrée principale ─────────────────────────────────────────────────────────

def validate_file(path: Path) -> dict:
    try:
        html_text = path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "file": str(path), "findings": [],
            "error_count": 0, "warning_count": 0,
            "blocking": True, "read_error": str(e),
        }

    soup = None
    if _HAS_BS4:
        soup = BeautifulSoup(html_text, "html.parser")
        plain = soup.get_text(" ", strip=True)
    else:
        plain = re.sub(r"<[^>]+>", " ", html_text)

    findings = (
        _check_a_verifier(html_text)
        + _check_pua(plain)
        + _check_header_wrap(html_text)
        + _check_data_correct(soup)
        + _check_section_titles(soup)
        + _check_broken_words(plain)
        + _check_initlocks_call(html_text)
    )

    errors   = [f for f in findings if f["level"] == "error"]
    warnings = [f for f in findings if f["level"] == "warning"]

    return {
        "file":          str(path),
        "findings":      findings,
        "error_count":   len(errors),
        "warning_count": len(warnings),
        "blocking":      bool(errors),
    }


def print_report(report: dict) -> None:
    fn = Path(report["file"]).name

    if "read_error" in report:
        print(red(f"✗ {fn}") + f" — erreur de lecture : {report['read_error']}")
        return

    ec = report["error_count"]
    wc = report["warning_count"]

    if ec == 0 and wc == 0:
        print(green(f"✓ {fn}") + dim(" — aucun problème détecté"))
        return

    status = red(f"✗ {fn}") if ec else amber(f"⚠ {fn}")
    print(status + dim(f" — {ec} erreur(s) bloquante(s), {wc} avertissement(s)"))

    for f in report["findings"]:
        lvl = red("ERREUR") if f["level"] == "error" else amber("AVERT ")
        print(f"  {lvl} [{f['code']}] {f['message']}")
        if "samples" in f:
            for s in f["samples"]:
                print(dim(f"         ↳ …{s}…"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validateur de quiz HTML BobMed — remplace la relecture manuelle."
    )
    parser.add_argument("files", nargs="+", help="Fichier(s) HTML à valider (glob accepté)")
    parser.add_argument("--json", action="store_true", help="Sortie JSON seule (machine-readable)")
    args = parser.parse_args()

    if not _HAS_BS4:
        print(amber(
            "⚠ BeautifulSoup4 absent — checks de cohérence data-correct désactivés. "
            "pip install beautifulsoup4"
        ), file=sys.stderr)

    reports = []
    for pattern in args.files:
        # Résolution glob ou chemin direct
        if any(c in pattern for c in ("*", "?", "[")):
            paths = sorted(Path(".").glob(pattern))
        else:
            paths = [Path(pattern)]

        for p in paths:
            if not p.exists():
                print(red(f"✗ {p} — introuvable"), file=sys.stderr)
                continue
            r = validate_file(p)
            reports.append(r)
            if not args.json:
                print_report(r)

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    elif reports:
        total_e = sum(r["error_count"] for r in reports)
        total_w = sum(r["warning_count"] for r in reports)
        blocking = sum(1 for r in reports if r["blocking"])
        if len(reports) > 1:
            summary = f"\n{len(reports)} fichier(s) · {total_e} erreur(s) · {total_w} avertissement(s)"
            if blocking:
                print(red(summary + f" — {blocking} bloquant(s)"))
            else:
                print(green(summary + " — publication possible"))

    sys.exit(1 if any(r.get("blocking") for r in reports) else 0)


if __name__ == "__main__":
    main()
