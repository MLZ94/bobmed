# Chantier « mise à niveau D3 » — état au 10 octobre 2026

> Dossier de travail temporaire, propre à la branche `D3`. **À supprimer avant toute fusion de `D3` dans `main`** (il n'a rien à faire sur le site publié).

## Objectif
Amener D3 au niveau de complétude de `main` (D2) : justifications ◈ non officielles sur les annales, quiz d'entraînement par item, sujets types, portails, documentation.

## Fait et poussé sur `D3`
- Fusion de `main` dans `D3` (commit `d67d449`).
- Corrections : option vierge de UE 5 mars 2023 DP2-Q11 retirée ; nouveau contrôle `NJ_*` des justifications ◈ dans `validate_quiz.py`.
- **◈ sur les 18 annales D3** (≈ 1 520 ◈ + rappels) : UE 2, UE 5, UE 7.3, UE 9, UE 10, UE 11.2. Les 5 annales d'UE 2 et 3 annales d'UE 5 (mars 2023, janv. 2024, fév. 2025) ont été rédigées par Opus avec auto-relecture (pas de relecteur séparé) ; les 10 autres rédigées par Sonnet puis relues de façon adversariale par Opus.
- **Entraînement D3-T1** : portail `d3/t1/entrainement/` + 10 quiz audités (items 23, 24/26, 24/344, 55, 147, 151/158, 154/359/188, 161, 164/215, 269/286).
- **Entraînement D3-T2** : portail `d3/t2/entrainement/` + 4 quiz de gériatrie audités (items 123/130, 131, 132, 343).

## Stratégie (décision de l'utilisateur, 10 octobre 2026)
**Priorité aux 6 sujets types**, puis seulement ensuite reprise des quiz d'entraînement par item. Chaque sujet type s'inspire de la lecture de TOUTES les annales de l'UE : analyse des questions qui reviennent le plus et de leurs différentes formulations / manières d'aborder le sujet, puis réplique d'une épreuve qui aurait été susceptible de tomber (architecture et style des sessions récentes). Workflow `workflows/st.js` (arguments : `workflows/st_args.json`) : analyse (Opus, `st/analyse_UE*.md`) → rédaction (Sonnet) → copie à l'aveugle + audit adversarial (Opus). Publication : `outils/add_sujet_type.py <quiz> "<thèmes>"` (carte « Sujet type » + compteur du portail).
Lot d'entraînement clos avant le changement : audit des 4 brouillons 25/40/44, 43/41, 120/133, 139/140/141 ; les rédactions interrompues (27/30, 300/312, 134/135/138, 1/7, 66/250/267 — scripts `build_item*.py` partiels dans le scratchpad) reprendront après les sujets types.

## Reste à faire
1. ~~◈ UE 11.2~~ : fait (vérifié par Opus, appliqué).
2. **Quiz d'entraînement** (38 restants, plan complet dans `plan_quizzes.json`) :
   - rédigés, **audit non fait** (specs dans `specs/`) : 25/40/44 (gynéco-obstétrique), 120/133 (gériatrie) ;
   - gynéco-obstétrique à rédiger : 27/30, 43/41, 300/312 ;
   - T2 : Gériatrie (4 à rédiger : 139/140/141, 134/135/138, 1/7, 66/250/267), Hématologie (8, avec les diapos de révision Braun/Rahmé 2025 du drive comme source), Oncologie (7) ;
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
