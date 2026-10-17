# Fiche de cadrage — Quiz_item336_343_coma_troubles_conscience

- **Fichier cible** : `d3/t3/entrainement/Quiz_item336_343_coma_troubles_conscience.html`
- **Items** : 336 (coma non traumatique de l'adulte et de l'enfant) + 343 (troubles de la conscience, confusion ; chip « Troubles de conscience (score de Glasgow) » du portail D3-T3 UE 11.2). L'angle gériatrique de l'item 343 (confusion du sujet âgé) est déjà couvert par `d3/t2/entrainement/Quiz_item343_confusion_sujet_age.html` : ici, angle urgences/réanimation de l'adulte et de l'enfant.
- **UE** : 11.2 Urgences-Réanimation (D3-T3). **Une seule annale** disponible : `Quiz_UE11.2_2022-2023_S1` (mars 2023, M23 : SQI1 10 + DL1 10 + DP1 12, QRM 75 % / QRU 25 %, 5 options, vignettes courtes, rôle explicite « Vous êtes de garde aux urgences… »).
- **Cible** : 2 items fusionnés -> **32 questions**.
- **Quiz voisins (ne pas dupliquer)** : D3-T3 item 337 intoxications (paracétamol, tricycliques, opioïdes : traités là-bas), 331 ACR, 332 états de choc, sujet type UE 11.2 (Glasgow Y1V2M4 = 7, intubation GCS 6 sans antidote, flumazénil et tricycliques, rhabdomyolyse), D3-T2 item 343 (confusion du sujet âgé), D2 items 340 (AVC), 341 (hémorragie méningée), 105 (épilepsie), 151 (méningites), 76 (alcool), 247 (diabète).

## a. Ce qui tombe (annale M23 + fonds de l'épreuve)

| Id | Format | Ce qui est demandé | Bonnes réponses | Indisp./inacc. |
|---|---|---|---|---|
| M23 DP1-Q5 | QRU (5 valeurs) | Glasgow d'une patiente qui ne s'éveille pas, grogne et a un « mouvement adapté » : Y1 V2 M5 | **8** (piège M5 localisation vs M4 retrait) | — |
| M23 DP1-Q6 | QRU (4 options argumentées) | Faut-il intuber à Glasgow 8 ? | **non, car il existe un antidote** ; « GCS ≤ 8 donc on intube » et « désature » faux | — |
| M23 DP1-Q1 | QRM | Dosages toxicologiques d'une patiente consciente | **Aucun** (alcoolémie seulement si trouble de conscience ; paracétamolémie à H4) | — |
| M23 DP1-Q7/Q8 | QRU/QRM | Antidote du coma opioïde ; modalités de la naloxone | naloxone, titration jusqu'à la FR (objectif éveil faux) | — |
| M23 DP1-Q4 | QRM | Toxidrome attendu : coma, hypotonie, myosis | convulsions faux | — |
| UE 2 nov. 2022 SQI1 | QRM | Critères d'admission en réanimation d'une méningite | Glasgow ≤ 11 (indispensable) | 2 indisp. |
| UE 2 nov. 2024 mDP2-Q1 | QRM | ATB avant PL : purpura fulminans, instabilité, délai > 90 min, trouble de la vigilance | — | 2 indisp. |
| UE 5 (4 sessions) | QRM/DP/KFP | Confusion : altération de la vigilance, Glasgow 10-13 n'est pas un coma, glycémie capillaire devant une agitation | — | — |
| UE 10 (3 sessions) | QRM | Hypoglycémie sous sulfamide : vomissements, AINS, insuffisance rénale | — | — |

**Constats** : la faculté interroge le coma par la **conduite à tenir** (premier examen, intuber ou non, antidote) et par le **score de Glasgow chiffré**, jamais par la sémiologie fine du tronc cérébral. Aucun item 336 pur dans l'UE 11.2 ; les notions sont attendues dans des dossiers toxiques/neuro/infectieux.

## b. Profil de format
- QRM à 5 options (1 à 5 bonnes réponses, « Aucun » possible), QRU pour les choix uniques (valeur de score, premier geste, décision argumentée). Énoncés courts avec rôle de l'étudiant ; dans les dossiers, chaque énoncé suivant livre la réponse de la question précédente.
- Items indispensables rares et réservés à l'item décisif (lecture diagnostique, critère de gravité) ; inacceptables absents en M23 mais fréquents ailleurs sur la plateforme DFA2.
- Pièges : GCS ≤ 8 n'impose pas l'intubation si cause rapidement réversible ; M5 vs M4 ; réponse verbale chez l'intubé ; Glasgow 10-13 = confusion/somnolence et non coma ; glycémie capillaire d'abord ; imagerie avant PL mais **sans retarder l'antibiothérapie** ; thiamine avant glucose chez l'alcoolique ; flumazénil non systématique.

## c. Notions à entraîner (par priorité, rang R2C)
1. Score de Glasgow : composantes, calcul chiffré, meilleure réponse motrice, patient intubé — rang A.
2. Premières mesures devant un coma : voies aériennes, oxygène, **glycémie capillaire**, voie veineuse, NaCl 0,9 % (pas de glucosé 5 %) — rang A.
3. Indications de l'intubation (GCS ≤ 8, engagement, détresse respiratoire, vomissements) et exception des causes rapidement réversibles — rang A.
4. Hypoglycémie : coma du diabétique sous sulfamide, resucrage IV, surveillance prolongée, prévention — rang A.
5. Causes de coma (toxique, métabolique, neurologique, infectieuse, épileptique) ; scanner normal n'élimine pas une cause — rang A.
6. Signes de localisation, engagement temporal (mydriase aréactive + triade de Cushing), scanner sans injection, mesures de neuroprotection — rang A/B.
7. Coma fébrile : hémocultures, antibiothérapie + aciclovir sans attendre, scanner avant PL si troubles de conscience/crise, PCR HSV, IRM — rang A/B.
8. Confusion aiguë de l'adulte, délirium tremens, encéphalopathie de Gayet-Wernicke (thiamine) — rang A.
9. Coma de l'enfant : glycémie capillaire d'abord — rang A.
10. Pupilles, décortication/décérébration, états proches (végétatif, conscience minimale, locked-in), score FOUR — rang B ou non précisé (null quand non sûr).

## d. Architecture retenue (32 questions)
1. **Questions isolées — Items 336 et 343** (12, libre) : Glasgow (structure, calcul), mesures immédiates, intubation, scanner normal, pupilles, sémiologie, antidotes, anomalies biologiques, états de conscience, confusion aiguë, coma de l'enfant.
2. **DP — Homme de 63 ans retrouvé inanimé au pied de son lit** (5, verrouillé) : hypothèses -> imagerie -> lecture du scanner -> neuroprotection -> évaluation sous sédation (FOUR).
3. **DP — Femme de 34 ans, fièvre et céphalées depuis trois jours** (4, verrouillé) : éléments orientant vers l'atteinte encéphalitique -> stratégie avant la PL -> traitement -> confirmation.
4. **DP — Homme de 49 ans, agitation et désorientation depuis 36 heures** (5, verrouillé) : diagnostic -> causes à rechercher -> traitement -> QROC vitamine -> complication carentielle.
5. **KFP — Homme de 52 ans diabétique retrouvé inconscient** (3, verrouillé) : QROC premier examen -> QRPL conduite -> QRM prévention.
6. **TCS — Femme de 71 ans, somnolence progressive** (3, verrouillé).
Titres de dossiers sans diagnostic.

## e. Sources
Collège de réanimation/médecine d'urgence, référentiel R2C items 336 et 343 ; SFAR/SRLF (prise en charge du coma, intubation) ; SPILF 2017 (méningites et méningo-encéphalites : antibiothérapie avant PL, imagerie préalable, aciclovir) ; Teasdale & Jennett (Glasgow), Wijdicks (FOUR score) ; recommandations SFD (hypoglycémie sévère).
