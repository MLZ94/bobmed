# Chantier « mise à niveau D3 » — état au 16 octobre 2026

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

## Reste à faire (16 octobre 2026)
**Quiz d'entraînement : 18/52 publiés, 34 restants.**
1. **5 quiz rédigés, audit non fait** (specs complets dans `specs/`, fiches dans `fiches/`) : `Quiz_item27_30_risques_foetaux_prematurite` (44 q.), `Quiz_item300_312_cancers_col_endometre_sein` (36 q.), `Quiz_item134_135_138_douleur_antalgiques`, `Quiz_item290_291_epidemiologie_depistage_oncogenetique` (25 q.), `Quiz_item292_diagnostic_cancers` (24 q.). → les auditer (entrées avec `"skip_write": true` dans `workflows/quiz2.js`), puis publier.
2. **29 à rédiger puis auditer** : gériatrie 1/7, 66/250/267 ; hématologie 212/213, 214/215/216, 315/316, 317/275, 318, 319, 320, 191 ; oncologie 294, 295, 312, 301, 307/354 ; thérapeutique 330 ×3 (anticoagulants/antiagrégants, AINS/corticoïdes, immunosuppresseurs/biothérapies), 321/322/325, 323/326, 177, 74 ; urgences 331, 332, 337, 336/343, 359, 338, 365. Arguments prêts : `workflows/ent_args_A.json` et `ent_args_B.json` (retirer les 5 quiz du point 1).
3. Publication de chaque quiz audité : l'ajouter à `approved.txt`, `outils/gen_portals.py` (crée aussi les portails d'entraînement T2 hémato/onco et T3), `validate_quiz.py` + `test_quiz.py`, commit, push sur `D3`.
4. Fin de chantier : CLAUDE.md (paragraphe « Entraînement par item D3 » : portails T2 complet et T3), `make validate-all`, supprimer `.wip-d3/` avant toute fusion dans `main`.

## Méthode retenue (choix de l'utilisateur)
- Rédaction par Sonnet, audit adversarial par Opus (un auditeur pour deux quiz, qui répond d'abord **à l'aveugle** à partir de `strip_spec.py`, puis tranche les divergences avec `compare_blind.py`).
- Quiz à plusieurs items fusionnés ⇒ davantage de questions (cibles dans `plan_quizzes.json`).
- Items déjà couverts en D2 : quiz sous l'angle D3 + lien « Voir aussi » vers le quiz D2.
- Pas de LCA. Numéros d'items : demander à l'utilisateur en cas de doute non levé en ligne.
- Un quiz n'est commité qu'après audit, avec mise à jour des portails (`approved.txt` liste les quiz publiés).

## Reprise
**Un seul chantier actif à la fois** (les limites d'usage sont communes au compte : deux sessions en parallèle n'accélèrent pas et risquent de rédiger deux fois le même quiz ou de se marcher dessus sur les portails).
Les scripts ont un chemin de travail codé en dur (`SP=/tmp/claude-0/…/scratchpad`) : recopier ce dossier dans le nouveau scratchpad (`outils/*` à la racine, `workflows/*` dans `wf/`, `fiches/` → `briefs/`, `specs/`, `nj/`, `analyses/` → `st/`) et adapter la variable `SP` de chaque script **et des deux workflows** (`quiz2.js`, `st.js`). Les rédacteurs de `quiz2.js` lisent `st/analyse_UE*.md` (analyse de toutes les annales de l'UE, faite pour les sujets types). Les extraits d'annales (`ex/`) se régénèrent avec `outils/extract.py` ; les textes des diapos d'hématologie avec PyMuPDF depuis `bobmed-annales-drive` (branche `D3`, `T2/HEMATO/`).
