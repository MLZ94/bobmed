# Chantier « mise à niveau D3 » — état au 16 octobre 2026

> **17 octobre 2026 : chantier terminé.** Les 52 quiz d'entraînement par item prévus (`plan_quizzes.json`) sont rédigés, audités à l'aveugle et commités, portails T1, T2 et T3 compris (`ETAT.md`). Restent les décisions d'Ichai : pousser D3 (historique réécrit pour retirer les liens de session des commits), puis supprimer ce dossier et fusionner D3 dans `main`.

> Dossier de travail temporaire, propre à la branche `D3`. **À supprimer avant toute fusion de `D3` dans `main`** (il n'a rien à faire sur le site publié).

## Objectif
Amener D3 au niveau de complétude de `main` (D2) : justifications ◈ non officielles sur les annales, quiz d'entraînement par item, sujets types, portails, documentation.

## Fait et poussé sur `D3`
- Fusion de `main` dans `D3` (commit `d67d449`).
- Corrections : option vierge de UE 5 mars 2023 DP2-Q11 retirée ; nouveau contrôle `NJ_*` des justifications ◈ dans `validate_quiz.py`.
- **◈ sur les 18 annales D3** (≈ 1 520 ◈ + rappels) : UE 2, UE 5, UE 7.3, UE 9, UE 10, UE 11.2. Les 5 annales d'UE 2 et 3 annales d'UE 5 (mars 2023, janv. 2024, fév. 2025) ont été rédigées par Opus avec auto-relecture (pas de relecteur séparé) ; les 10 autres rédigées par Sonnet puis relues de façon adversariale par Opus.
- **Entraînement D3-T1** : portail `d3/t1/entrainement/` + 12 quiz audités (items 23, 24/26, 24/344, 25/40/44, 43/41, 55, 147, 151/158, 154/359/188, 161, 164/215, 269/286).
- **Entraînement D3-T2** : portail `d3/t2/entrainement/` + 6 quiz de gériatrie audités (items 120/133, 123/130, 131, 132, 139/140/141, 343).

## Stratégie (décision de l'utilisateur, 10 octobre 2026)
**Priorité aux 6 sujets types**, puis seulement ensuite reprise des quiz d'entraînement par item. Chaque sujet type s'inspire de la lecture de TOUTES les annales de l'UE : analyse des questions qui reviennent le plus et de leurs différentes formulations / manières d'aborder le sujet, puis réplique d'une épreuve qui aurait été susceptible de tomber (architecture et style des sessions récentes). Workflow `workflows/st.js` (arguments : `workflows/st_args.json`) : analyse (Opus, `st/analyse_UE*.md`) → rédaction (Sonnet) → copie à l'aveugle + audit adversarial (Opus). Publication : `outils/add_sujet_type.py <quiz> "<thèmes>"` (carte « Sujet type » + compteur du portail).
Lot d'entraînement clos avant le changement : les 4 brouillons 25/40/44, 43/41, 120/133, 139/140/141 ont été audités et publiés ; les rédactions interrompues (27/30, 300/312, 134/135/138, 1/7, 66/250/267 — scripts `build_item*.py` partiels dans le scratchpad) reprendront après les sujets types.

- **Sujets types publiés** : UE 2 (37 q.), UE 5 (37 q.) — chacun audité deux fois —, UE 7.3 (35 q.), UE 9 (31 q.), UE 10 (35 q.), UE 11.2 (32 q.) : **les 6 sujets types sont publiés**. Analyses des annales des 6 UE dans `analyses/` (base des quiz d'entraînement restants).
- ⚠️ Reprise d'un workflow (`resumeFromRunId`) : le cache ne vaut que pour le préfixe d'appels inchangé ; avec des appels concurrents, l'ordre change et des agents déjà terminés sont relancés. Pour reprendre, relancer plutôt un nouveau run limité aux éléments restants.

## Reste à faire (mis à jour en continu)
**L'état quiz par quiz est dans `ETAT.md`** (généré par `outils/etat.py` à chaque sauvegarde : publié / audité à publier / rédigé à auditer / à rédiger). `audited.txt` liste les quiz audités pas encore publiés, `approved.txt` les quiz publiés.
Ordre des lots : (1) audit des 6 quiz rédigés (27/30, 300/312, 134/135/138, 290/291, 292, 295) ; (2) gériatrie 1/7, 66/250/267 et oncologie 294, 312, 301, 307/354 ; (3) hématologie (8, avec les diapos de révision) ; (4) thérapeutique (7) et urgences-réanimation (7), portail d'entraînement T3 ; (5) fin de chantier : CLAUDE.md (paragraphe « Entraînement par item D3 »), `make validate-all`, puis suppression de `.wip-d3/` et fusion dans `main` **uniquement avec l'accord explicite de l'utilisateur**.
Publication d'un quiz audité : l'ajouter à `approved.txt`, `python3 $SP/gen_portals.py`, `validate_quiz.py` + `test_quiz.py`, commit, push sur `D3`.

## Méthode retenue (choix de l'utilisateur)
- Rédaction par Sonnet, audit adversarial par Opus (un auditeur pour deux quiz, qui répond d'abord **à l'aveugle** à partir de `strip_spec.py`, puis tranche les divergences avec `compare_blind.py`).
- Quiz à plusieurs items fusionnés ⇒ davantage de questions (cibles dans `plan_quizzes.json`).
- Items déjà couverts en D2 : quiz sous l'angle D3 + lien « Voir aussi » vers le quiz D2.
- Pas de LCA. Numéros d'items : demander à l'utilisateur en cas de doute non levé en ligne.
- Un quiz n'est commité qu'après audit, avec mise à jour des portails (`approved.txt` liste les quiz publiés).

## Reprise (session qui repart à froid)
**Un seul chantier actif à la fois** (limites d'usage communes au compte).
1. Dépôts : `/home/claude/bobmed` sur la branche `D3`, `/home/claude/bobmed-annales-drive` sur la branche `D3` (diapos d'hématologie).
2. `bash .wip-d3/outils/reprise.sh <scratchpad>` : recopie le chantier dans le scratchpad, corrige les chemins codés en dur, installe playwright/pymupdf/bs4, régénère `ex/` (extraits d'annales) et `hemato/` (textes des diapos).
3. Lire `ETAT.md`. Un quiz « rédigé, à auditer » a son spec dans `specs/` : le rendre (`render_quiz.py <spec>`) puis l'auditer ; un quiz « à rédiger » repart de zéro (ou d'un spec partiel s'il existe).
4. Prompts : `cd <scratchpad>/wf && node gen.mjs write ent_all.json <noms>` (un prompt de rédaction par quiz) et `node gen.mjs audit ent_all.json <nom1> <nom2>` (un auditeur pour deux quiz). Sans l'outil Workflow, lancer un agent par prompt avec l'outil Agent (rédaction : modèle sonnet ; audit : modèle opus), en parallèle. Les rédacteurs et les auditeurs lisent l'analyse de toutes les annales de l'UE (`st/analyse_UE*.md`).
5. Sauvegarde : `bash <scratchpad>/save_wip.sh <scratchpad> "<message>"` recopie specs, fiches, copies à l'aveugle et état dans `.wip-d3/`, puis commit + push sur `D3` (verrou `/tmp/d3_git.lock`). Une boucle de fond la lance toutes les 10 minutes ; la lancer aussi après chaque étape.
