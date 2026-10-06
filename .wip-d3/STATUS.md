# Chantier « mise à niveau D3 » — état au 6 octobre 2026 (EN PAUSE)

> Dossier de travail temporaire, propre à la branche `D3`. **À supprimer avant toute fusion de `D3` dans `main`** (il n'a rien à faire sur le site publié).

## Objectif
Amener D3 au niveau de complétude de `main` (D2) : justifications ◈ non officielles sur les annales, quiz d'entraînement par item, sujets types, portails, documentation.

## Fait et poussé sur `D3`
- Fusion de `main` dans `D3` (commit `d67d449`).
- Corrections : option vierge de UE 5 mars 2023 DP2-Q11 retirée ; nouveau contrôle `NJ_*` des justifications ◈ dans `validate_quiz.py`.
- **◈ sur 17 des 18 annales D3** (≈ 1 470 ◈ + 37 rappels) : toutes les UE 2, UE 5, UE 7.3, UE 9, UE 10. Les 5 annales d'UE 2 et 3 annales d'UE 5 (mars 2023, janv. 2024, fév. 2025) ont été rédigées par Opus avec auto-relecture (pas de relecteur séparé) ; les 9 autres rédigées par Sonnet puis relues de façon adversariale par Opus.
- **Entraînement D3-T1** : portail `d3/t1/entrainement/` + 6 quiz audités (items 23, 147, 151/158, 154/359/188, 161, 164/215).

## Reste à faire
1. **◈ UE 11.2 mars 2023** : JSON rédigé (Sonnet) dans `nj/UE11.2_2022-2023_S1.json`, **pas encore vérifié** par Opus → vérifier puis appliquer (`apply_nj.py`).
2. **Quiz d'entraînement** (46 restants, plan complet dans `plan_quizzes.json`) :
   - `Quiz_item269_286_…` : spec rédigé (Sonnet) dans `specs/`, **audit non fait** ;
   - pédiatrie : item 55 ; gynéco-obstétrique : 24/344, 24/26, 25/40/44, 27/30, 43/41, 300/312 ;
   - T2 : Gériatrie (9), Hématologie (8, avec les diapos de révision Braun/Rahmé 2025 du drive comme source), Oncologie (7) ;
   - T3 : Thérapeutique (7), Urgences-Réanimation (7).
   Fiches « ce qui tombe » déjà écrites : `fiches/` (8) ; les autres sont produites par le rédacteur.
3. **Sujets types** : 6 (UE 2, 5, 7.3, 9, 10, 11.2) — mode `sujet_type` de `workflows/quiz2.js`.
4. **Portails** : `gen_portals.py` (entraînement T2/T3 + sous-catégories), puis sous-catégorie « Sujet type », compteurs, accueil (descriptions des blocs D3).
5. **CLAUDE.md** : section ◈ « annales D2 et D3 », entraînement et sujets types D3, compteurs.

## Méthode retenue (choix de l'utilisateur)
- Rédaction par Sonnet, audit adversarial par Opus (un auditeur pour deux quiz, qui répond d'abord **à l'aveugle** à partir de `strip_spec.py`, puis tranche les divergences avec `compare_blind.py`).
- Quiz à plusieurs items fusionnés ⇒ davantage de questions (cibles dans `plan_quizzes.json`).
- Items déjà couverts en D2 : quiz sous l'angle D3 + lien « Voir aussi » vers le quiz D2.
- Pas de LCA. Numéros d'items : demander à l'utilisateur en cas de doute non levé en ligne.
- Un quiz n'est commité qu'après audit, avec mise à jour des portails (`approved.txt` liste les quiz publiés).

## Reprise
Les scripts ont un chemin de travail codé en dur (`SP=/tmp/claude-0/…/scratchpad`) : recopier ce dossier dans le nouveau scratchpad (`outils/*` à la racine, `workflows/*` dans `wf/`, `fiches/` → `briefs/`, `specs/`, `nj/`) et adapter la variable `SP` de chaque script. Les extraits d'annales (`ex/`) se régénèrent avec `outils/extract.py` ; les textes des diapos d'hématologie avec PyMuPDF depuis `bobmed-annales-drive` (branche `D3`, `T2/HEMATO/`).
