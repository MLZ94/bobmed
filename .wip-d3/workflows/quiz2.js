export const meta = {
  name: 'd3-entrainement-quiz-lean',
  description: 'Quiz d\'entraînement par item D3 : rédaction, copie à l\'aveugle, audit adversarial',
  phases: [
    { title: 'Rédaction', detail: 'spec JSON → HTML, validate + test' },
    { title: 'Audit', detail: 'un auditeur pour deux quiz : copie à l\'aveugle puis relecture adversariale' },
  ],
}
const SP = '/tmp/claude-0/-home-user/55cc2afb-deb2-5236-a438-a491d4be9ce0/scratchpad'
const R = '/home/user/bobmed'
const QUIZZES = (args && args.quizzes) || []
const UE_LABEL = { '2': 'UE 2 Gynécologie-Obstétrique / Pédiatrie', '5': 'UE 5 Gériatrie', '7.3': 'UE 7.3 Hématologie', '9': 'UE 9 Oncologie', '10': 'UE 10 Thérapeutique', '11.2': 'UE 11.2 Urgences-Réanimation' }
const base = q => q.file.split('/').pop().replace('.html', '')

const W_SCHEMA = { type: 'object', properties: {
  file: { type: 'string' }, spec_path: { type: 'string' }, questions: { type: 'integer' },
  types: { type: 'string' }, ranks: { type: 'string' }, sections: { type: 'string' },
  validate_ok: { type: 'boolean' }, test_ok: { type: 'boolean' }, notes: { type: 'string' } },
  required: ['file', 'spec_path', 'questions', 'types', 'ranks', 'sections', 'validate_ok', 'test_ok', 'notes'] }
const B_SCHEMA = { type: 'object', properties: {
  answers_path: { type: 'string' },
  ambiguous: { type: 'array', items: { type: 'object', properties: { qid: { type: 'string' }, reason: { type: 'string' } }, required: ['qid', 'reason'] } } },
  required: ['answers_path', 'ambiguous'] }
const A_SCHEMA = { type: 'object', properties: {
  divergences: { type: 'integer' }, key_fixes: { type: 'array', items: { type: 'string' } },
  ambiguity_fixes: { type: 'array', items: { type: 'string' } }, medical_fixes: { type: 'array', items: { type: 'string' } },
  other_fixes: { type: 'array', items: { type: 'string' } }, final_questions: { type: 'integer' },
  validate_ok: { type: 'boolean' }, test_ok: { type: 'boolean' } },
  required: ['divergences', 'key_fixes', 'ambiguity_fixes', 'medical_fixes', 'other_fixes', 'final_questions', 'validate_ok', 'test_ok'] }

const P_SCHEMA = { type: 'object', properties: { quizzes: { type: 'array', items: A_SCHEMA } }, required: ['quizzes'] }

function sources(q) {
  const ex = q.ue === '7.3'
    ? `${SP}/ex/Quiz_UE7.3_2024-2025_S1.md et ${SP}/ex/D2T4_Quiz_UE7.3_2022-2023_S1_commune_hemato.md (questions d'hématologie de SQI1 seulement)`
    : `${SP}/ex/Quiz_UE${q.ue}_*.md`
  let s = `- Annales de la faculté pour cette UE (style, longueur des énoncés, formats, distracteurs, items indispensables/inacceptables) : ${ex}.`
  if (q.group === 'hemato') s += `\n- SOURCE DEMANDÉE PAR L'UTILISATEUR : les diapositives de révision d'hématologie des enseignants de la faculté (janvier 2025) — ${SP}/hemato/TB_text.md (QCM : diapo question puis diapo réponse, bonnes propositions marquées **[ROUGE]…[/ROUGE]**), ${SP}/hemato/RR_text.md, rendus ${SP}/hemato/pages/*.png. Reprends les QCM des diapos qui relèvent de ce quiz (en les complétant d'une correction justifiée option par option ; si la réponse n'est pas surlignée, tranche selon le référentiel) et appuie-toi sur leurs messages-clés : ce sont les points que les enseignants jugent importants pour le partiel.`
  return s
}

function writerPrompt(q) {
  const b = base(q)
  return `Tu rédiges un quiz d'ENTRAÎNEMENT PAR ITEM pour BobMed (site de révision médicale ; D3 = 6e année ; annales de la faculté dans ${R}/d3/).
Quiz : ${q.file}
Items R2C : ${q.items.join(', ')} — ${q.title}
${UE_LABEL[q.ue]} · D3 ${q.trimestre.toUpperCase()}
Nombre de questions : AU MOINS ${q.target_questions} (davantage si la fiche de cadrage le recommande). Règle de l'utilisateur : quand plusieurs items sont fusionnés dans un même entraînement, il faut davantage de questions.
${q.note ? 'Précision du plan : ' + q.note : ''}

OBJECTIF FIXÉ PAR L'UTILISATEUR : « l'essentiel, c'est que les entraînements soient efficaces pour s'entraîner au type de question qui tombe au partiel sur cet item ». Le quiz doit donc reproduire ce qui tombe à cette faculté : mêmes notions, mêmes pièges, mêmes formats (QRM, QRU, QROC, QRP/QRPL, TCS, KFP, dossiers progressifs DP/mDP verrouillés), même style d'énoncés, mêmes usages des items indispensables/inacceptables — tout en couvrant les notions de rang A du référentiel qui n'ont pas encore été interrogées.

ENTRÉES
- Fiche de cadrage « ce qui tombe » (ton cahier des charges) : ${SP}/briefs/${b}.md. SI CE FICHIER N'EXISTE PAS, fais d'abord toi-même l'analyse : rattache à ce quiz toutes les questions des annales de l'UE qui portent sur ses items (identifiant, format, ce qui est demandé, bonnes réponses, items indispensables/inacceptables), relève le profil de format, les notions et pièges récurrents, les chiffres demandés, puis écris la fiche à ce chemin (sections : ce qui tombe ; profil de format ; notions à entraîner par priorité avec rang R2C si certain ; architecture retenue) AVANT de rédiger le quiz.
${sources(q)}
${q.see_also_d2 && q.see_also_d2.length ? `- Quiz D2 voisins déjà publiés : ${q.see_also_d2.map(f => R + '/' + f).join(', ')}. Lis-les : ton quiz doit traiter l'angle D3 (terrain pédiatrique, gériatrique, thérapeutique, urgence…) sans les dupliquer, et les citer en see_also (href relatif depuis ${q.file}, label du type « Item 151 — Méningites (D2 T1) »).` : ''}
- Exemple de quiz d'entraînement D2 (forme) : ${R}/d2/t2/entrainement/Quiz_item105_epilepsie.html
- Générateur et schéma JSON : ${SP}/render_quiz.py (lis sa docstring : champs, balises autorisées, contrôles).

RÈGLES (CLAUDE.md fait foi : sections « Quiz d'entraînement par item », « Badges de rang », « Consignes de rédaction et de qualité », « QROC », « QRP », « TCS », « Ne jamais spoiler le diagnostic »)
1. Rigueur médicale absolue : référentiels des Collèges (éditions EDN/R2C) et recommandations françaises en vigueur ; terminologie exacte ; chiffres, seuils, posologies vérifiés. En cas de doute sur un fait, ne le mets pas.
2. Questions originales. Tu peux t'inspirer étroitement d'une question d'annale (même notion, même piège) mais reformule le cas et les options ; ne recopie pas une annale telle quelle.
3. Architecture : une section « Questions isolées — Item(s) … » (non verrouillée ; son titre ne doit contenir ni « DP », ni « KFP », ni « TCS ») puis un ou plusieurs dossiers progressifs verrouillés « DP — <terrain, motif de consultation> » (ou « KFP — … », « TCS — … ») comme à l'examen : contexte (champ context) sur la 1re question uniquement, évolution du cas dans les énoncés suivants. Titre de dossier SANS le diagnostic à trouver.
4. Chaque option porte une justification (just) de 1 à 2 phrases, qui explique (seuil, mécanisme, raison) et ne reformule jamais l'option. Un rappel transversal éventuel va dans note. TCS : échelle standard des annales (improbable / peu probable / ni plus ou moins probable / probable / certain), une seule réponse, note explicative obligatoire.
5. QRM : fais varier le nombre de bonnes réponses (1 à 5) et leur position ; QRU : une seule réponse ; QRP/QRPL : nombre de bonnes réponses = nombre à sélectionner, énoncé qui le précise ; QROC : réponse courte, accept = plusieurs formulations acceptables (synonymes, abréviations, avec/sans unité).
6. Items indispensables (mandatory, uniquement sur une option juste) / inacceptables (unacceptable, uniquement sur une option fausse et dangereuse) : utilise-les comme le fait la faculté sur ce type de question, quand c'est défendable.
7. Rang (rank) de chaque question : "A", "B" ou "A/B" selon les objectifs R2C de l'item (connaissances de rang A/B du référentiel du Collège) ; null si tu n'es pas sûr — n'invente jamais un rang.
9. Auto-relecture obligatoire avant de rendre : relis chaque question comme un examinateur (une seule lecture possible, clé exacte, justifications exactes, rang sûr ou null).
8. Champs : title « Item ${q.items[0]} — <intitulé> · Entraînement par item » (ou « Items ${q.items.join('/')} — … » si plusieurs items) ; themes = liste « Thème · Thème · … » des notions couvertes ; footer « N questions · Item(s) … · D3 ${q.trimestre.toUpperCase()} ${UE_LABEL[q.ue]} · BobMed entraînement. » (N réel) ; kind "entrainement" ; file "${q.file}".

ÉTAPES (économise les allers-retours d'outils : lis les sources utiles une fois, puis écris le spec complet en une ou deux fois)
a. Écris le spec dans ${SP}/specs/${b}.json.
b. python3 ${SP}/render_quiz.py ${SP}/specs/${b}.json --check, corrige jusqu'à 0 erreur et sans avertissement « option sans justification ».
c. python3 ${SP}/render_quiz.py ${SP}/specs/${b}.json (écrit ${R}/${q.file}).
d. cd ${R} && python3 validate_quiz.py ${q.file} && python3 test_quiz.py ${q.file} — corrige le spec et recommence jusqu'à 0 erreur et tests passés.
Ne modifie aucun autre fichier du dépôt, aucune opération git.
Rends le bilan (nombre de questions, répartition des types, des rangs, sections, résultats validate/test, remarques).`
}


function stPrompt(q) {
  const b = base(q)
  return `Tu rédiges le SUJET TYPE de l'${UE_LABEL[q.ue]} (D3 ${q.trimestre.toUpperCase()}) pour BobMed : ${q.file}.
Un sujet type est une épreuve blanche complète, composée de questions ORIGINALES, qui synthétise les thèmes et les pièges qui reviennent le plus aux partiels de cette faculté. Objectif de l'utilisateur : s'entraîner efficacement au type de questions qui tombe au partiel.
Nombre de questions : environ ${q.target_questions}.

ENTRÉES
- Fiches de cadrage de tous les quiz d'entraînement de l'UE (ce qui tombe, formats, notions) : ${q.briefs.map(x => SP + '/briefs/' + x + '.md').join(', ')}
${sources(q)}
- Modèles de sujets types D2 (forme et ton) : ${R}/d2/t2/Quiz_UE4.1_sujet_type.html, ${R}/d2/t4/Quiz_UE11.1_sujet_type.html
- Générateur et schéma JSON : ${SP}/render_quiz.py (docstring). kind = "sujet_type".

ARCHITECTURE (calquée sur les épreuves réelles de cette UE — vérifie dans les annales l'enchaînement et la taille des sections) : des dossiers verrouillés (DP de 8 à 12 questions, mDP de 5 à 7, KFP de 2 à 3 à longues listes de propositions, TCS de 3 questions sur une même vignette) et une section de questions isolées SQI1 (≈ 15). Chaque section a un code (champ code : "DP1", "mDP1", "KFP1", "TCS1", "SQI1"), un titre (champ title : « DP1 — <terrain, motif> », sans le diagnostic à trouver ; « SQI1 » pour les questions isolées), un label pour le sous-titre (champ label : ex. « DP1 douleur pelvienne aiguë chez une femme de 26 ans »), locked=true pour DP/mDP/KFP/TCS. Contexte (champ context) sur la 1re question de chaque dossier ; le cas évolue ensuite dans les énoncés.
${q.ue === '2' ? 'UE 2 : le sujet doit mêler gynécologie-obstétrique ET pédiatrie dans les proportions des annales.' : ''}
RÈGLES : celles de CLAUDE.md (« Consignes de rédaction et de qualité », QROC, QRP, TCS, « Ne jamais spoiler le diagnostic ») ; rigueur médicale absolue (référentiels des Collèges, recommandations françaises en vigueur) ; chaque option justifiée (just) sans paraphrase ; QRM au nombre de bonnes réponses varié ; items indispensables/inacceptables comme le fait la faculté ; pas de rang (rank null) dans un sujet type. intro_note : 2-3 phrases qui expliquent qu'il s'agit d'un sujet type construit à partir des annales de l'UE (années couvertes) et listent les thèmes travaillés. title « UE ${q.ue} — <matière> · Sujet type (synthèse des annales <années>) ». footer « N questions · sujet type · ${UE_LABEL[q.ue]} · D3 ${q.trimestre.toUpperCase()} · BobMed. »

ÉTAPES : spec dans ${SP}/specs/${b}.json → python3 ${SP}/render_quiz.py <spec> --check → python3 ${SP}/render_quiz.py <spec> → cd ${R} && python3 validate_quiz.py ${q.file} && python3 test_quiz.py ${q.file} ; corrige jusqu'à 0 erreur et tests passés. Aucune opération git, aucun autre fichier du dépôt.
Rends le bilan.`
}

function blindPrompt(q) {
  const b = base(q)
  return `Tu es un(e) excellent(e) étudiant(e) en 6e année de médecine qui prépare l'EDN. Tu passes une copie d'entraînement À L'AVEUGLE.
1. Lance : mkdir -p ${SP}/blind && python3 ${SP}/strip_spec.py ${SP}/specs/${b}.json > ${SP}/blind/${b}.md
2. Lis UNIQUEMENT ${SP}/blind/${b}.md. Interdiction d'ouvrir le JSON du spec, le HTML du quiz, la fiche de cadrage ou tout autre fichier qui contiendrait le corrigé.
3. Réponds à chaque question selon les référentiels des Collèges et les recommandations françaises en vigueur : QRM = toutes les propositions justes ; QRU et TCS = une seule ; QRP/QRPL = exactement le nombre demandé ; QROC = réponse courte.
4. Écris ${SP}/blind/${b}.answers.json au format {"Q1": "AC", "Q2": "B", "Q7": "réponse courte", …} (identifiants exactement comme dans la copie).
5. Signale les questions ambiguës, mal posées, à plusieurs réponses défendables, comportant une erreur médicale, ou dont l'énoncé souffle la réponse.
Rends answers_path et la liste ambiguous.`
}

function auditPrompt(q, w, bl) {
  const b = base(q)
  return `Relecture ADVERSARIALE finale du quiz d'entraînement ${R}/${q.file} (spec : ${SP}/specs/${b}.json ; fiche(s) de cadrage : ${q.kind === 'sujet_type' ? q.briefs.map(x => SP + '/briefs/' + x + '.md').join(', ') : SP + '/briefs/' + b + '.md'} ; items ${q.items.join(', ')} — ${q.title}). Il a été rédigé par un autre agent : pars du principe qu'il contient des erreurs et cherche-les.${q.kind === 'sujet_type' ? "\nC'est un SUJET TYPE (épreuve blanche) : pas de rang (rank null) ; sections codées DP1/mDP1/KFP1/TCS1/SQI1 ; vérifie aussi que l'architecture reproduit celle des épreuves réelles de l'UE." : ''}
Bilan du rédacteur : ${JSON.stringify(w || {})}

1. Copie à l'aveugle : un candidat fort a répondu sans voir le corrigé (${SP}/blind/${b}.answers.json). Lance python3 ${SP}/compare_blind.py ${SP}/specs/${b}.json ${SP}/blind/${b}.answers.json. Pour CHAQUE divergence, tranche en t'appuyant sur le référentiel : corrigé faux → corrige la clé ET les justifications ; question ambiguë ou à plusieurs lectures → reformule l'énoncé ou l'option pour qu'une seule réponse soit défendable ; candidat dans l'erreur → garde, mais vérifie que la justification de l'option piège explique bien l'erreur. Ambiguïtés signalées par le candidat : ${JSON.stringify((bl && bl.ambiguous) || [])}.
2. Audit complet de chaque question : exactitude médicale (énoncé, options, verdicts, justifications, notes) au regard des référentiels des Collèges et des recommandations françaises en vigueur ; rangs A/B conformes aux objectifs R2C (null si incertain) ; justifications qui expliquent sans paraphraser ; QRM au nombre de bonnes réponses varié (1 à 5) et positions variées ; QROC avec variantes suffisantes ; TCS bien construits ; items indispensables/inacceptables défendables ; titres de dossiers sans diagnostic ; cohérence du cas d'une question à l'autre.
3. Efficacité pour le partiel (objectif de l'utilisateur) : compare au « ce qui tombe » des fiches de cadrage — les notions et pièges les plus interrogés sont-ils tous entraînés, dans les formats de l'examen ? Ajoute ou remplace des questions si besoin (au moins ${q.target_questions} questions au total).
4. Corrige directement le spec, puis : python3 ${SP}/render_quiz.py ${SP}/specs/${b}.json && cd ${R} && python3 validate_quiz.py ${q.file} && python3 test_quiz.py ${q.file} — jusqu'à 0 erreur et tests passés. Aucune opération git, aucun autre fichier du dépôt.
Rends le bilan des corrections.`
}


function auditPairPrompt(qs, ws) {
  const items = qs.map((q, i) => {
    const b = base(q)
    return `### Quiz ${i + 1} : ${R}/${q.file}
- spec : ${SP}/specs/${b}.json ; fiche(s) : ${q.kind === 'sujet_type' ? q.briefs.map(x => SP + '/briefs/' + x + '.md').join(', ') : SP + '/briefs/' + b + '.md'} ; ${q.kind === 'sujet_type' ? 'SUJET TYPE (épreuve blanche) : pas de rang, sections DP1/mDP1/KFP1/TCS1/SQI1, architecture des épreuves réelles' : 'items ' + q.items.join(', ') + ' — ' + q.title} ; au moins ${q.target_questions} questions.
- bilan du rédacteur : ${JSON.stringify(ws[i] || {})}`
  }).join('\n')
  return `Tu es l'auditeur de ${qs.length} quiz BobMed rédigés par d'autres agents. Pars du principe qu'ils contiennent des erreurs et cherche-les. Traite les quiz l'un après l'autre :
${items}

POUR CHAQUE QUIZ, dans cet ordre :
1. COPIE À L'AVEUGLE (avant toute lecture du spec, du HTML ou de la fiche) : mkdir -p ${SP}/blind && python3 ${SP}/strip_spec.py <spec> > ${SP}/blind/<nom>.md ; lis UNIQUEMENT ce fichier et réponds à chaque question comme un excellent candidat à l'EDN (QRM : toutes les justes ; QRU/TCS : une ; QRP : exactement le nombre demandé ; QROC : réponse courte), puis écris ${SP}/blind/<nom>.answers.json ({"Q1": "AC", …} — pour un sujet type, identifiants « DP1-Q1 »… comme dans la copie). Note au passage les questions ambiguës ou qui soufflent la réponse.
2. python3 ${SP}/compare_blind.py <spec> ${SP}/blind/<nom>.answers.json, puis tranche CHAQUE divergence avec le référentiel : clé fausse → corrige clé ET justifications ; question ambiguë → reformule pour qu'une seule réponse soit défendable ; ton erreur → garde, en vérifiant que la justification de l'option piège l'explique.
3. Audit complet : exactitude médicale (référentiels des Collèges, recommandations françaises en vigueur) de chaque énoncé, option, verdict, justification, note ; rangs conformes aux objectifs R2C (null si incertain) ; justifications sans paraphrase ; QRM au nombre de bonnes réponses varié ; QROC avec variantes suffisantes ; TCS bien construits ; items indispensables/inacceptables défendables ; titres de dossiers sans diagnostic ; cohérence du cas d'une question à l'autre ; couverture de « ce qui tombe » (fiche) dans les formats de l'examen.
4. Corrige directement le spec, puis python3 ${SP}/render_quiz.py <spec> && cd ${R} && python3 validate_quiz.py <fichier> && python3 test_quiz.py <fichier>, jusqu'à 0 erreur et tests passés. Aucune opération git, aucun autre fichier du dépôt.
Rends un bilan par quiz.`
}

phase('Rédaction')
const PAIRS = []
for (let i = 0; i < QUIZZES.length; i += 2) PAIRS.push(QUIZZES.slice(i, i + 2))
const res = await pipeline(PAIRS,
  pair => parallel(pair.map(q => () => q.skip_write ? Promise.resolve({ file: q.file, notes: 'déjà rédigé lors d\'un passage précédent (spec et HTML présents)' }) : agent(q.kind === 'sujet_type' ? stPrompt(q) : writerPrompt(q), { label: `quiz:${base(q)}`, phase: 'Rédaction', schema: W_SCHEMA, model: 'sonnet' }))),
  (ws, pair) => {
    const ok = pair.filter((q, i) => ws[i])
    const okw = ws.filter(Boolean)
    if (!ok.length) return pair.map(q => ({ file: q.file, writer: null, audit: null }))
    return agent(auditPairPrompt(ok, okw), { label: `audit:${ok.map(base).join('+')}`, phase: 'Audit', schema: P_SCHEMA })
      .then(a => pair.map((q, i) => ({ file: q.file, writer: ws[i], audit: a })))
  },
)
return res.flat()
