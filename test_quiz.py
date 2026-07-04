#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_quiz.py — Tests headless Playwright pour les quiz BobMed.

Vérifie le comportement interactif d'un quiz HTML :
  1. Verrouillage initial : Q2+ des sections DP/KFP/TCS/mDP ont class="locked"
  2. Déverrouillage : valider Q1 déverrouille Q2
  3. Score : #s-done et #s-ok s'incrémentent correctement
  4. Bouton "Tout révéler" : toutes les corrections apparaissent
  5. Bouton "Recommencer" : recharge la page (score remis à zéro)

Usage:
    python3 test_quiz.py Quiz_UE7.3_2023-2024_S1.html
    python3 test_quiz.py d2/t4/*.html          # glob
    python3 test_quiz.py Quiz.html --headed    # mode visible pour debug

Dépendances:
    pip install playwright
    (Chromium pré-installé dans /opt/pw-browsers/chromium)

Exit codes:
    0 — tous les tests passent
    1 — au moins un test échoue
"""

import sys
import re
import argparse
from pathlib import Path

# ── Couleurs terminal ─────────────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty()
def _c(code, s): return f"\033[{code}m{s}\033[0m" if _USE_COLOR else s
def red(s):   return _c("31;1", s)
def amber(s): return _c("33;1", s)
def green(s): return _c("32;1", s)
def dim(s):   return _c("2", s)
def bold(s):  return _c("1", s)

# Chromium : chemin de l'environnement distant BobMed. Sur une autre machine
# (poste local), ce chemin n'existe pas → on laisse Playwright localiser son
# propre navigateur (executable_path=None).
CHROMIUM_PATH = "/opt/pw-browsers/chromium"
LOCKED_SECTIONS_RE = re.compile(r"DP|KFP|TCS|mDP", re.IGNORECASE)


def _resolve_chromium() -> str | None:
    """Chemin Chromium explicite si présent (env distant), sinon None (défaut Playwright)."""
    import os
    if os.path.exists(CHROMIUM_PATH):   # symlink ou binaire de l'env BobMed
        return CHROMIUM_PATH
    return None                          # poste local : Playwright résout tout seul


# ── Logique de test ───────────────────────────────────────────────────────────

def test_file(html_path: Path, headed: bool) -> dict:
    """Exécute la suite de tests sur un fichier quiz. Retourne un rapport."""
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    results = []

    def ok(name, detail=""):
        results.append({"name": name, "pass": True, "detail": detail})

    def fail(name, detail=""):
        results.append({"name": name, "pass": False, "detail": detail})

    file_url = html_path.resolve().as_uri()
    html_text = html_path.read_text(encoding="utf-8", errors="replace")
    # Un quiz « plat » (révisions transversales) peut délibérément ne pas utiliser
    # le verrouillage progressif : il n'embarque alors ni initLocks ni unlockNext.
    # Le bug .wrap/.hwrap, lui, laisse initLocks présent mais inopérant → à
    # distinguer d'une absence volontaire de moteur.
    has_lock_engine = ("initLocks" in html_text) and ("unlockNext" in html_text)

    with sync_playwright() as pw:
        launch_kwargs = {"headless": not headed}
        exe = _resolve_chromium()
        if exe:
            launch_kwargs["executable_path"] = exe
        browser = pw.chromium.launch(**launch_kwargs)
        ctx = browser.new_context()
        page = ctx.new_page()

        try:
            page.goto(file_url, wait_until="domcontentloaded", timeout=15_000)
        except PlaywrightTimeout:
            fail("page_load", "Timeout au chargement de la page")
            browser.close()
            return {"file": str(html_path), "results": results}

        # ── Test 1 : Page se charge (au moins une question) ───────────────────
        # Un fichier sans .q (portail index.html, page d'accueil…) n'est pas un
        # quiz : on l'IGNORE proprement plutôt que de le marquer en échec.
        n_q = page.evaluate("() => document.querySelectorAll('.q').length")
        if n_q == 0:
            browser.close()
            return {"file": str(html_path), "results": [], "skipped": "aucune question (.q) — non-quiz"}
        ok("page_load", f"{n_q} question(s)")

        # ── Test 2 : Verrouillage initial des sections DP/KFP/TCS ─────────────
        # Repérer les sections verrouillables
        sections = page.query_selector_all(".sect")
        locked_section_names = []
        for s in sections:
            text = s.inner_text().strip()
            if LOCKED_SECTIONS_RE.search(text):
                locked_section_names.append(text)

        # Une section verrouillable n'a de Q à verrouiller que si elle compte 2+
        # questions (la 1re est toujours libre). On calcule le max de questions
        # parmi les sections DP/KFP/TCS/mDP.
        max_lockable_qs = page.evaluate("""() => {
            const wrap = document.querySelector('.wrap');
            if (!wrap) return 0;
            let inLocked = false, cnt = 0, mx = 0;
            for (const el of wrap.children) {
                if (el.classList.contains('sect')) {
                    if (inLocked) mx = Math.max(mx, cnt);
                    inLocked = /DP|KFP|TCS|mDP/i.test(el.textContent);
                    cnt = 0;
                } else if (el.classList.contains('q') && inLocked) {
                    cnt++;
                }
            }
            if (inLocked) mx = Math.max(mx, cnt);
            return mx;
        }""")
        locked_qs = page.query_selector_all(".q.locked")

        if not locked_section_names:
            ok("initial_locking", "aucune section DP/KFP/TCS/mDP — test non applicable")
        elif locked_qs:
            ok("initial_locking", f"{len(locked_qs)} question(s) verrouillée(s) initiales")
        elif max_lockable_qs < 2:
            ok("initial_locking", "sections verrouillables à 1 question — rien à verrouiller")
        elif not has_lock_engine:
            # Pas de moteur initLocks/unlockNext → quiz plat assumé (ex. révisions).
            ok("initial_locking", "quiz plat sans moteur de verrouillage (initLocks/unlockNext absents)")
        else:
            # Moteur présent mais rien de verrouillé alors qu'une section a 2+ Q :
            # c'est le bug .wrap/.hwrap (initLocks ciblant le mauvais conteneur).
            fail("initial_locking",
                 f"Sections {locked_section_names} avec {max_lockable_qs} Q mais aucune "
                 "verrouillée — initLocks() inopérant (piège .wrap/.hwrap ?).")

        # ── Test 3 : Compteurs initiaux ────────────────────────────────────────
        try:
            s_done_text = page.text_content("#s-done", timeout=2_000) or ""
            s_ok_text   = page.text_content("#s-ok",   timeout=2_000) or ""
            # Format attendu : "0/N" et "0/M"
            if re.match(r"^0/\d+$", s_done_text.strip()) and re.match(r"^0[,.]?0?/\d+", s_ok_text.strip()):
                ok("score_counters_init", f"done={s_done_text.strip()} ok={s_ok_text.strip()}")
            else:
                fail("score_counters_init", f"done={s_done_text!r} ok={s_ok_text!r}")
        except PlaywrightTimeout:
            fail("score_counters_init", "#s-done ou #s-ok introuvable")

        # ── Tests 4 & 5 : Validation Q1 et déverrouillage Q2 ────────────────
        # Stratégie : trouver Q1 d'une section lockée qui a une Q2 locked,
        # puis vérifier que la validation de Q1 déverrouille Q2.
        validated_q1 = False
        first_q = None

        # Identifier la première paire (Q1-libre, Q2-locked) dans une section lockée
        target_q1 = None
        target_q2_id = None
        try:
            pairs = page.evaluate("""() => {
                const wrap = document.querySelector('.wrap');
                if (!wrap) return null;
                let inLocked = false, lastQ1 = null;
                for (const el of wrap.children) {
                    if (el.classList.contains('sect')) {
                        inLocked = /DP|KFP|TCS|mDP/i.test(el.textContent);
                        lastQ1 = null;
                        continue;
                    }
                    if (el.classList.contains('q') && inLocked) {
                        if (!el.classList.contains('locked')) {
                            // C'est Q1 (libre)
                            lastQ1 = el;
                        } else if (lastQ1 && el.classList.contains('locked')) {
                            // C'est Q2 (locked) — on a notre paire
                            return {q1_id: lastQ1.id, q2_id: el.id};
                        }
                    }
                }
                return null;
            }""")
        except Exception:
            pairs = None

        if pairs and locked_section_names:
            target_q1 = page.query_selector(f'[id="{pairs["q1_id"]}"]')
            target_q2_id = pairs["q2_id"]
        else:
            # Pas de paire trouvée : prendre la première question validable
            q_els = page.query_selector_all(".q:not(.locked):not([data-type='QROC'])")
            target_q1 = q_els[0] if q_els else None

        first_q = target_q1
        if first_q:
            try:
                # Une question se « complète » de deux façons, toutes deux appelant
                # unlockNext() : QRM/QRU → cocher une option puis Valider ; QROC (pas
                # d'option, pas de bouton Valider) → cliquer « Voir la réponse ».
                first_opt = first_q.query_selector(".opt")
                validate_btn = first_q.query_selector(".validate")
                show_btn = first_q.query_selector(".show")
                if first_opt and validate_btn:
                    first_opt.click()
                    validate_btn.click()
                    page.wait_for_timeout(400)
                elif show_btn:
                    # QROC ou question sans option validable : révéler la réponse.
                    show_btn.click()
                    page.wait_for_timeout(400)
                else:
                    fail("validate_q1", f"Q1 ({first_q.get_attribute('id')}) sans option ni bouton d'action")
                    show_btn = None
                if first_opt or show_btn:
                    is_done = first_q.evaluate("el => el.classList.contains('done')")
                    if is_done:
                        ok("validate_q1", first_q.get_attribute("id") or "")
                        validated_q1 = True
                    else:
                        fail("validate_q1", "Classe 'done' absente après complétion de Q1")
            except Exception as e:
                fail("validate_q1", str(e))
        else:
            ok("validate_q1", "aucune question complétable — test non applicable")

        # ── Test 5 : Déverrouillage Q2 après validation Q1 ───────────────────
        if locked_section_names and validated_q1 and target_q2_id:
            try:
                page.wait_for_timeout(400)
                q2_el = page.query_selector(f'[id="{target_q2_id}"]')
                if q2_el:
                    still_locked = q2_el.evaluate("el => el.classList.contains('locked')")
                    if not still_locked:
                        ok("unlock_on_validate", f"{target_q2_id} déverrouillée")
                    else:
                        fail("unlock_on_validate", f"{target_q2_id} reste locked après validation de Q1")
                else:
                    fail("unlock_on_validate", f"{target_q2_id} introuvable dans le DOM")
            except Exception as e:
                fail("unlock_on_validate", str(e))
        elif locked_section_names and validated_q1:
            # Sections lockées mais pas de paire Q1/Q2 détectée (sections à 1 seule question)
            new_locked_count = len(page.query_selector_all(".q.locked"))
            ok("unlock_on_validate", f"sections lockées à 1 question, {new_locked_count} locked restants")
        else:
            ok("unlock_on_validate", "pas applicable (pas de sections lockées)")

        # ── Test 6 : Score mis à jour après validation ─────────────────────────
        if validated_q1:
            try:
                s_done_after = page.text_content("#s-done", timeout=1_000) or ""
                # Après 1 validation, done devrait être >= 1
                m = re.match(r"^(\d+)/(\d+)$", s_done_after.strip())
                if m and int(m.group(1)) >= 1:
                    ok("score_update", f"#s-done={s_done_after.strip()}")
                else:
                    fail("score_update", f"#s-done={s_done_after!r} après validation")
            except PlaywrightTimeout:
                fail("score_update", "#s-done introuvable")

        # ── Test 7 : Bouton "Tout révéler" ────────────────────────────────────
        try:
            reveal_btn = page.query_selector("#revealall")
            if reveal_btn:
                reveal_btn.click()
                page.wait_for_timeout(500)
                # Toutes les corrections doivent être visibles
                hidden_corrections = page.evaluate(
                    "() => document.querySelectorAll('.correction[hidden]').length"
                )
                if hidden_corrections == 0:
                    ok("reveal_all", "toutes les corrections visibles")
                else:
                    fail("reveal_all", f"{hidden_corrections} correction(s) encore cachée(s)")
            else:
                fail("reveal_all", "bouton #revealall introuvable")
        except Exception as e:
            fail("reveal_all", str(e))

        # ── Test 8 : Bouton "Recommencer" ─────────────────────────────────────
        try:
            reset_btn = page.query_selector("#reset")
            if reset_btn:
                reset_btn.click()
                page.wait_for_load_state("domcontentloaded", timeout=5_000)
                page.wait_for_timeout(300)
                # Après reset, done devrait être remis à 0
                s_done_reset = page.text_content("#s-done", timeout=2_000) or ""
                m = re.match(r"^(\d+)/\d+$", s_done_reset.strip())
                if m and int(m.group(1)) == 0:
                    ok("reset", f"#s-done={s_done_reset.strip()}")
                else:
                    fail("reset", f"#s-done={s_done_reset!r} après reset (attendu 0/N)")
            else:
                fail("reset", "bouton #reset introuvable")
        except Exception as e:
            fail("reset", str(e))

        browser.close()

    return {"file": str(html_path), "results": results}


# ── Rapport ───────────────────────────────────────────────────────────────────

def print_report(report: dict) -> bool:
    """Affiche le rapport d'un fichier. Retourne True si tous les tests passent."""
    fn = Path(report["file"]).name
    if report.get("skipped"):
        print(dim(f"– {fn} — ignoré ({report['skipped']})"))
        return True
    results = report["results"]
    passed = [r for r in results if r["pass"]]
    failed = [r for r in results if not r["pass"]]

    if not failed:
        print(green(f"✓ {fn}") + dim(f" — {len(passed)}/{len(results)} tests passés"))
        return True

    print(red(f"✗ {fn}") + dim(f" — {len(failed)} test(s) échoué(s) / {len(results)}"))
    for r in results:
        if r["pass"]:
            print(dim(f"  ✓ {r['name']}" + (f" : {r['detail']}" if r["detail"] else "")))
        else:
            print(red(f"  ✗ {r['name']}") + (dim(f" : {r['detail']}") if r["detail"] else ""))
    return False


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Tests headless Playwright pour les quiz BobMed."
    )
    parser.add_argument("files", nargs="+", help="Fichier(s) HTML à tester (glob accepté)")
    parser.add_argument("--headed", action="store_true", help="Mode navigateur visible")
    args = parser.parse_args()

    # Outillage absent → on IGNORE les tests (exit 0) sans casser le pipeline :
    # un défaut de configuration d'environnement ne doit pas bloquer une
    # publication, seul un vrai défaut de quiz le doit. Message très visible.
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print(amber(
            "⚠ Playwright non installé — tests headless IGNORÉS (non bloquant).\n"
            "  Pour les activer : pip install playwright"
        ), file=sys.stderr)
        sys.exit(0)

    paths = []
    for pattern in args.files:
        if any(c in pattern for c in ("*", "?", "[")):
            found = sorted(Path(".").glob(pattern))
        else:
            found = [Path(pattern)]
        for p in found:
            if not p.exists():
                print(amber(f"⚠ Fichier introuvable : {p}"), file=sys.stderr)
            else:
                paths.append(p)

    if not paths:
        print(red("✗ Aucun fichier à tester."), file=sys.stderr)
        sys.exit(2)

    # Sonde de lancement : si aucun navigateur n'est disponible (poste sans
    # `playwright install`), on ignore proprement plutôt que de planter.
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            launch_kwargs = {"headless": True}
            exe = _resolve_chromium()
            if exe:
                launch_kwargs["executable_path"] = exe
            pw.chromium.launch(**launch_kwargs).close()
    except Exception as e:
        print(amber(
            "⚠ Navigateur Chromium indisponible — tests headless IGNORÉS (non bloquant).\n"
            f"  Détail : {str(e).splitlines()[0] if str(e) else e}\n"
            "  Pour les activer sur un poste local : playwright install chromium"
        ), file=sys.stderr)
        sys.exit(0)

    all_pass = True
    n_fail = 0
    for p in paths:
        report = test_file(p, headed=args.headed)
        passed = print_report(report)
        if not passed:
            all_pass = False
            n_fail += 1

    if len(paths) > 1:
        total = len(paths)
        if all_pass:
            print(green(f"\n✓ {total} fichier(s) — tous les tests passés"))
        else:
            print(red(f"\n✗ {total} fichier(s) traité(s) — {n_fail} en échec"))

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
