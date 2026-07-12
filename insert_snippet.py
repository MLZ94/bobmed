#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
insert_snippet.py — Insère automatiquement un snippet de quiz dans le portail cible.

Lit le fichier *.snippet.html produit par pdf_to_quiz.py et insère la carte
<a class="qz"> dans le bon index.html, au bon endroit (ordre chronologique par UE).

Usage:
    python3 insert_snippet.py Quiz_UE7.3_2024-2025_S1.snippet.html
    python3 insert_snippet.py --dry-run Quiz_UE7.3_2024-2025_S1.snippet.html
    python3 insert_snippet.py --portal d2/t4/index.html Quiz.snippet.html

Exit codes:
    0 — insertion réussie (ou --dry-run sans erreur)
    1 — erreur (portail introuvable, UE ambiguë non résolue, doublon, etc.)

Dépendances: aucune (stdlib uniquement)
"""

import sys
import re
import argparse
from pathlib import Path

# Miroir de UE_MAP dans pdf_to_quiz.py (source de vérité)
UE_MAP = {
    "8.2":  ("Cardiologie",                          "d2/t1"),
    "7.1":  ("Pneumologie",                          "d2/t1"),
    "6":    ("Maladies transmissibles",               "d2/t1"),
    "8.1":  ("Hépato-Gastro / Chir-Dig",             "d2/t2"),
    "4.1":  ("Neurologie-MPR",                        "d2/t2"),
    "4.3":  ("Dermatologie",                          "d2/t3"),
    "7.2":  ("Médecine Interne",                      "d2/t3"),
    "8.4":  ("Néphro / Uro",                          "d2/t3"),
    "4.2":  ("ORL / Ophtalmo / Chir maxillo-faciale", "d2/t4"),
    "7.3":  ("Rhumatologie",                          "d2/t4"),
    "11.1": ("Chirurgie Orthopédique",                "d2/t4"),
    "8.3":  ("Endocrino / Nutrition",                 "d2/t4"),
    "12.1": ("Anglais",                               "d2/t4"),
    "12.2": ("LCA",                                   "d2/t4"),
    "1.1":  ("Biostatistiques (D1)",                  "d1/t4"),
    "9.2":  ("UE 9.2 (D1)",                           "d1/t4"),
    "9.3":  ("UE 9.3 (D1)",                           "d1/t4"),
    # UE 3 : ambiguïté D1 (d1/t4/) vs D2-T2 (d2/t2/) — demande interactive
    "3":    ("Agents infectieux (D1) / Psy-Addicto (D2-T2)", "AMBIGU"),
}

# ── Couleurs terminal ─────────────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty()
def _c(code, s): return f"\033[{code}m{s}\033[0m" if _USE_COLOR else s
def red(s):   return _c("31;1", s)
def amber(s): return _c("33;1", s)
def green(s): return _c("32;1", s)
def dim(s):   return _c("2", s)
def bold(s):  return _c("1", s)


# ── Extraction depuis le snippet ──────────────────────────────────────────────

def parse_snippet(snippet_path: Path) -> dict:
    """Lit le fichier snippet et extrait le href et le titre qz-t."""
    text = snippet_path.read_text(encoding="utf-8").strip()
    href_m = re.search(r'href="([^"]+)"', text)
    title_m = re.search(r'class="qz-t"[^>]*>([^<]+)<', text)
    if not href_m:
        raise ValueError(f"Aucun href trouvé dans {snippet_path}")
    href  = href_m.group(1)
    title = title_m.group(1).strip() if title_m else ""
    return {"text": text, "href": href, "title": title}


def extract_ue_from_href(href: str) -> str | None:
    """Extrait le numéro d'UE depuis un nom de fichier Quiz_UEx.y_..."""
    m = re.search(r"Quiz_UE(\d+(?:\.\d+)?)_", href, re.IGNORECASE)
    return m.group(1) if m else None


# ── Tri chronologique ─────────────────────────────────────────────────────────

def _sort_key(title: str) -> tuple:
    """Clé de tri pour un titre qz-t : (première_année, est_rattrapage)."""
    year_m = re.search(r"(\d{4})", title)
    first_year = int(year_m.group(1)) if year_m else 0
    is_rattrapage = 1 if re.search(r"rattrapage|session\s*2\b", title, re.I) else 0
    return (first_year, is_rattrapage)


# ── Recherche de la section UE dans le portail ───────────────────────────────

def _find_ue_section(portal_text: str, ue_num: str) -> tuple[int, int] | None:
    """
    Retourne (start, end) de la plage de texte contenant les .qz de l'UE indiquée.
    start = position juste après le titre .ue de cette UE
    end   = position du prochain .ue (ou du footer/</div> de fermeture)
    """
    # Chercher class="ue" suivi du numéro UE (sous différentes formes)
    # ex: "UE 7.3", "UE7.3", "7.3"
    ue_escaped = re.escape(ue_num)
    # Pattern : div.ue contenant "UE X.X" ou "UEx.x"
    # Plusieurs blocs .ue peuvent exister pour la même UE (Entraînement + Annales)
    # → on veut le bloc "Annales officielles" ou le seul bloc si unique.
    pattern = re.compile(
        r'<div\s+class="ue"[^>]*>[^<]*(?:UE\s*' + ue_escaped + r')[^<]*</div>',
        re.IGNORECASE
    )
    matches = list(pattern.finditer(portal_text))
    if not matches:
        return None

    # Préférer le match qui contient "Annales" si plusieurs
    target_m = None
    for m in matches:
        if re.search(r"annales", m.group(0), re.I):
            target_m = m
            break
    if target_m is None:
        target_m = matches[-1]   # dernier bloc = le plus susceptible d'être les annales

    section_start = target_m.end()

    # Fin de section = prochain div.ue OU footer OU </div> du wrap
    end_pattern = re.compile(
        r'(?:<div\s+class="ue"|<footer|</div>\s*\n?\s*<script)',
        re.IGNORECASE
    )
    end_m = end_pattern.search(portal_text, section_start)
    section_end = end_m.start() if end_m else len(portal_text)

    return (section_start, section_end)


def _collect_qz_in_section(portal_text: str, start: int, end: int) -> list[dict]:
    """
    Extrait les blocs <a class="qz"> dans la plage [start, end].
    Retourne liste de {pos_start, pos_end, title, sort_key}.
    """
    # Un bloc qz peut s'étendre sur plusieurs lignes
    qz_re = re.compile(r'<a\s+class="qz"[^>]*>.*?</a>', re.DOTALL)
    items = []
    for m in qz_re.finditer(portal_text, start, end):
        title_m = re.search(r'class="qz-t"[^>]*>([^<]+)<', m.group(0))
        title = title_m.group(1).strip() if title_m else ""
        items.append({
            "pos_start": m.start(),
            "pos_end":   m.end(),
            "title":     title,
            "sort_key":  _sort_key(title),
        })
    return items


def _find_insertion_point(
    portal_text: str,
    section_start: int,
    section_end: int,
    new_sort_key: tuple,
    existing_qz: list[dict],
) -> int:
    """
    Retourne la position d'insertion (dans portal_text) pour le nouveau snippet,
    en respectant l'ordre chronologique croissant.
    """
    if not existing_qz:
        # Pas de .qz existants : insérer juste avant la fin de section (avant .empty ou le next .ue)
        # Chercher un éventuel bloc .empty dans la section
        empty_m = re.search(r'<div\s+class="empty"', portal_text[section_start:section_end])
        if empty_m:
            return section_start + empty_m.start()
        return section_end

    # Insérer après le dernier qz dont sort_key <= new_sort_key
    insert_after = section_start   # par défaut : avant le premier
    for qz in existing_qz:
        if qz["sort_key"] <= new_sort_key:
            insert_after = qz["pos_end"]
        else:
            break

    # Avancer après les espaces/newlines qui suivent ce bloc
    pos = insert_after
    while pos < len(portal_text) and portal_text[pos] in (" ", "\t", "\n", "\r"):
        pos += 1
    return insert_after   # insérer après le bloc (le \n sera ajouté)


# ── Mise à jour du footer ─────────────────────────────────────────────────────

def _update_footer(portal_text: str) -> str:
    """Incrémente le premier nombre dans le <footer> du portail."""
    def inc(m):
        n = int(m.group(1)) + 1
        return m.group(0).replace(m.group(1), str(n), 1)
    return re.sub(r"<footer>(\d+)", inc, portal_text, count=1)


# ── Workflow principal ────────────────────────────────────────────────────────

def resolve_ue3_ambiguity(snippet_href: str) -> str:
    """Demande à l'utilisateur de résoudre l'ambiguïté UE 3 (D1 vs D2-T2)."""
    print(amber("⚠ UE 3 ambiguë — existe en D1 (d1/t4/) ET en D2-T2 (d2/t2/)."))
    print(f"  Fichier : {snippet_href}")
    print("  Indices : préfixe DFG → D1 · préfixe DFA → D2.")
    while True:
        rep = input("  Portail cible [1=d1/t4, 2=d2/t2] : ").strip()
        if rep == "1":
            return "d1/t4"
        if rep == "2":
            return "d2/t2"
        print("  Répondre 1 ou 2.")


def insert(snippet_path: Path, portal_path: Path | None, dry_run: bool) -> int:
    # ── 1. Lire le snippet ────────────────────────────────────────────────────
    try:
        snippet = parse_snippet(snippet_path)
    except Exception as e:
        print(red(f"✗ Impossible de lire {snippet_path} : {e}"))
        return 1

    href  = snippet["href"]
    title = snippet["title"]

    # ── 2. Détecter le portail cible ──────────────────────────────────────────
    if portal_path is None:
        ue_num = extract_ue_from_href(href)
        if not ue_num:
            print(red(f"✗ Impossible d'extraire le numéro d'UE depuis : {href}"))
            print("  Utiliser --portal pour indiquer l'index.html cible.")
            return 1

        if ue_num not in UE_MAP:
            print(red(f"✗ UE {ue_num} absente de UE_MAP — portail inconnu."))
            return 1

        _, folder = UE_MAP[ue_num]
        if folder == "AMBIGU":
            folder = resolve_ue3_ambiguity(href)

        # Chercher l'index.html depuis la racine du dépôt (le script est à la racine)
        repo_root = Path(__file__).parent
        portal_path = repo_root / folder / "index.html"

    if not portal_path.exists():
        print(red(f"✗ Portail introuvable : {portal_path}"))
        return 1

    # ── 3. Vérifier que le quiz n'est pas déjà présent ───────────────────────
    portal_text = portal_path.read_text(encoding="utf-8")
    if href in portal_text:
        print(amber(f"⚠ {href} est déjà présent dans {portal_path} — insertion ignorée."))
        return 0

    # ── 4. Extraire le numéro d'UE pour trouver la bonne section ─────────────
    ue_num = extract_ue_from_href(href)
    section = _find_ue_section(portal_text, ue_num) if ue_num else None

    if section is None:
        # Portail sans section .ue pour cette UE (ex: annales/ compact)
        # → insérer juste avant le <footer>
        footer_m = re.search(r"<footer", portal_text, re.IGNORECASE)
        insert_pos = footer_m.start() if footer_m else len(portal_text)
        existing_qz = []
        new_sort_key = _sort_key(title)
    else:
        sec_start, sec_end = section
        existing_qz = _collect_qz_in_section(portal_text, sec_start, sec_end)
        new_sort_key = _sort_key(title)
        insert_pos = _find_insertion_point(
            portal_text, sec_start, sec_end, new_sort_key, existing_qz
        )

    # ── 5. Construire le texte à insérer ──────────────────────────────────────
    snippet_block = "\n" + snippet["text"] + "\n"

    # ── 6. Afficher un diff lisible (dry-run ou avant écriture) ───────────────
    context_before = portal_text[max(0, insert_pos-80):insert_pos].strip()[-60:]
    context_after  = portal_text[insert_pos:insert_pos+80].strip()[:60:]

    print(bold(f"\nPortail : {portal_path}"))
    print(f"  UE {ue_num} · \"{title}\"")
    print(f"  {len(existing_qz)} quiz existant(s) dans cette section")
    print(f"  Clé de tri : {new_sort_key} (année, est_rattrapage)")
    if context_before:
        print(dim(f"  Contexte avant : …{context_before}"))
    print(green(f"  Insertion : {snippet['text'][:80]}…"))
    if context_after:
        print(dim(f"  Contexte après : {context_after}…"))

    if dry_run:
        print(amber("\n[dry-run] Aucune modification écrite."))
        return 0

    # ── 7. Insérer et mettre à jour le footer ─────────────────────────────────
    new_text = portal_text[:insert_pos] + snippet_block + portal_text[insert_pos:]
    new_text = _update_footer(new_text)

    portal_path.write_text(new_text, encoding="utf-8")
    print(green(f"\n✓ {portal_path} mis à jour — footer incrémenté."))
    print(dim("  Prochaine étape : git diff pour vérifier, puis commit."))
    return 0


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Insère un snippet de quiz dans le portail BobMed cible."
    )
    parser.add_argument(
        "snippet", help="Fichier .snippet.html produit par pdf_to_quiz.py"
    )
    parser.add_argument(
        "--portal", metavar="INDEX_HTML",
        help="Portail cible explicite (ignorer la détection automatique via UE_MAP)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Afficher ce qui serait fait sans modifier le portail"
    )
    args = parser.parse_args()

    snippet_path = Path(args.snippet)
    if not snippet_path.exists():
        print(red(f"✗ Fichier introuvable : {snippet_path}"), file=sys.stderr)
        sys.exit(1)

    portal_path = Path(args.portal) if args.portal else None
    sys.exit(insert(snippet_path, portal_path, args.dry_run))


if __name__ == "__main__":
    main()
