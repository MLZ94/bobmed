export const meta = {
  name: 'd3-sujets-types',
  description: 'Sujets types D3 : analyse de toutes les annales de l\'UE, rédaction d\'un sujet plausible, copie à l\'aveugle et audit adversarial',
  phases: [
    { title: 'Analyse', detail: 'lecture de toutes les annales de l\'UE : récurrences, formulations, architecture, plan du sujet' },
    { title: 'Rédaction', detail: 'spec JSON → HTML, validate + test', model: 'sonnet' },
    { title: 'Audit', detail: 'copie à l\'aveugle, puis audit adversarial (médical, fidélité aux annales, plausibilité)' },
  ],
}
const SP = '/tmp/claude-0/-home-user/55cc2afb-deb2-5236-a438-a491d4be9ce0/scratchpad'
const R = '/home/user/bobmed'
const UES = (args && args.ues) || []
const CHUNK = (args && args.chunk) || 2

const AN_SCHEMA = { type: 'object', properties: {
  analysis_path: { type: 'string' }, sessions_read: { type: 'integer' }, questions_read: { type: 'integer' },
  architecture: { type: 'string' }, total_questions: { type: 'integer' },
  top_themes: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } },
  required: ['analysis_path', 'sessions_read', 'questions_read', 'architecture', 'total_questions', 'top_themes', 'notes'] }
const W_SCHEMA = { type: 'object', properties: {
  file: { type: 'string' }, spec_path: { type: 'string' }, questions: { type: 'integer' },
  sections: { type: 'string' }, types: { type: 'string' },
  validate_ok: { type: 'boolean' }, test_ok: { type: 'boolean' }, notes: { type: 'string' } },
  required: ['file', 'spec_path', 'questions', 'sections', 'types', 'validate_ok', 'test_ok', 'notes'] }
const A_SCHEMA = { type: 'object', properties: {
  divergences: { type: 'integer' }, key_fixes: { type: 'array', items: { type: 'string' } },
  ambiguity_fixes: { type: 'array', items: { type: 'string' } }, medical_fixes: { type: 'array', items: { type: 'string' } },
  fidelity_fixes: { type: 'array', items: { type: 'string' } }, other_fixes: { type: 'array', items: { type: 'string' } },
  final_questions: { type: 'integer' }, themes_for_portal: { type: 'string' },
  validate_ok: { type: 'boolean' }, test_ok: { type: 'boolean' } },
  required: ['divergences', 'key_fixes', 'ambiguity_fixes', 'medical_fixes', 'fidelity_fixes', 'other_fixes', 'final_questions', 'themes_for_portal', 'validate_ok', 'test_ok'] }

const name = u => `UE${u.ue}_sujet_type`
const anPath = u => `${SP}/st/analyse_UE${u.ue}.md`
const specPath = u => `${SP}/specs/Quiz_${name(u)}.json`

function sources(u) {
  return u.sources.map(s => '- ' + s).join('\n')
}

function analysisPrompt(u) {
  return `Tu prépares le SUJET TYPE de l'UE ${u.ue} — ${u.matiere} (D3 ${u.trimestre.toUpperCase()}, 6e année de médecine) pour BobMed, site de révision médicale. Ta tâche ici est l'ANALYSE ; un autre agent rédigera le sujet à partir de ton analyse.

Demande de l'utilisateur, à suivre à la lettre : « le sujet type sera inspiré par la lecture de toutes les annales disponibles sur l'UE, l'analyse des questions qui reviennent le plus, des différentes formulations ou manières d'aborder les sujets, et la réplique d'un sujet qui aurait été susceptible de tomber ».

SI ${anPath(u)} EXISTE DÉJÀ et se termine par la ligne « <!-- FIN DE L'ANALYSE --> » (passage précédent interrompu après coup), ne refais rien : relis-le et rends son résumé.

SOURCES — lis-les EN ENTIER (chaque question, chaque option, chaque corrigé VRAI/FAUX, chaque note du jury) :
${sources(u)}
- Compléments facultatifs : les items au programme de l'UE tels que classés sur le portail (${R}/d3/${u.trimestre}/index.html, bloc de l'UE, chips « Items au programme », triées par nombre de questions dans les annales)${u.briefs && u.briefs.length ? ` ; fiches « ce qui tombe » déjà rédigées pour les quiz d'entraînement de l'UE (par item) : ${u.briefs.map(b => SP + '/briefs/' + b + '.md').join(', ')}` : ''}. Les images des annales sont dans ${SP}/ex/img/ si tu dois en voir une.

ÉCRIS ${anPath(u)} (mkdir -p ${SP}/st), en français, avec ces sections :
1. **Inventaire des sessions** : pour chaque annale, date, architecture (sections dans l'ordre, type et nombre de questions), total, répartition des types de questions (QRM, QRU, QROC, QRP/QRPL, TCS, KFP…), usage des items indispensables/inacceptables.
2. **Évolution du format** et **architecture d'épreuve recommandée** pour un sujet qui tomberait à la prochaine session : sections dans l'ordre, codes (SQI1, DP1, mDP1, KFP1, TCS1…), nombre de questions par section, total (aligne-toi sur les sessions les plus récentes ; ${u.size_hint}).
3. **Thèmes et items par récurrence** : tableau de TOUS les thèmes interrogés (item R2C si tu es sûr du numéro), avec nombre de questions, nombre de sessions où le thème apparaît, sessions concernées, formats utilisés. Trie par récurrence.
4. **Questions qui reviennent** : pour chaque thème récurrent (≥ 2 sessions, ou très lourd dans une session), les DIFFÉRENTES manières dont il a été abordé — formulations d'énoncés (cite-les en abrégé, avec la référence de la question : session + identifiant), angle (diagnostic, examen, traitement, surveillance, complication, prévention, chiffre/seuil, physiopathologie…), pièges et distracteurs récurrents, chiffres et seuils demandés, items indispensables/inacceptables. C'est le cœur de l'analyse : sois exhaustif.
5. **Dossiers cliniques** : terrains et motifs des DP/mDP/KFP/TCS déjà tombés, et schéma de progression des questions d'un dossier (ex. Q1 hypothèses → Q2 examens → Q3 interprétation → Q4 traitement → Q5 complication/surveillance).
6. **Ce qui est susceptible de tomber** : thèmes à forte probabilité (récurrents, ou importants au programme et pas encore ou plus interrogés depuis longtemps), en justifiant brièvement.${u.extra_analysis ? '\n   ' + u.extra_analysis : ''}
7. **Plan du sujet type** : pour chaque section de l'architecture recommandée, le terrain et le motif (titre SANS le diagnostic à trouver), le thème visé, puis la liste des questions prévues (une ligne chacune : format, notion et angle, piège visé, question(s) d'annale dont elle s'inspire). Le sujet doit ressembler à une vraie épreuve de cette faculté (style et longueur des énoncés, nombre d'options, proportions de formats), couvrir en priorité les thèmes et formulations qui reviennent le plus, varier les angles d'approche d'un même thème, et ne recopier aucune question telle quelle.
Termine le fichier par la ligne « <!-- FIN DE L'ANALYSE --> ».

Aucune modification du dépôt, aucune opération git. Rends le résumé demandé (chemin, sessions et questions lues, architecture recommandée en une ligne, nombre total de questions prévu, thèmes principaux, remarques — notamment les limites des sources).`
}

function writerPrompt(u, an) {
  return `Tu rédiges le SUJET TYPE de l'UE ${u.ue} — ${u.matiere} (D3 ${u.trimestre.toUpperCase()}) pour BobMed : ${u.file}.
Demande de l'utilisateur : « le sujet type sera inspiré par la lecture de toutes les annales disponibles sur l'UE, l'analyse des questions qui reviennent le plus, des différentes formulations ou manières d'aborder les sujets, et la réplique d'un sujet qui aurait été susceptible de tomber ». L'analyse est faite : ${anPath(u)} (résumé : ${JSON.stringify(an || {})}). Ton sujet doit être cette réplique plausible d'une épreuve de la faculté.

SI ${specPath(u)} EXISTE DÉJÀ (passage précédent interrompu), repars de ce fichier : complète-le et termine les étapes plutôt que de tout réécrire.

ENTRÉES
- L'analyse ${anPath(u)} : suis son architecture recommandée (§2) et son plan (§7), et appuie-toi sur ses §3-§6 (thèmes récurrents, formulations, pièges, chiffres, progression des dossiers).
- Les annales elles-mêmes, pour caler le style (longueur et ton des énoncés, nombre d'options, formulations) : ${u.annales.join(', ')}.
- Générateur et schéma JSON : ${SP}/render_quiz.py (lis sa docstring). kind = "sujet_type".
- Modèle de forme d'un sujet type déjà publié (D2) : ${R}/d2/t2/Quiz_UE4.1_sujet_type.html.

RÈGLES (CLAUDE.md fait foi : « Consignes de rédaction et de qualité », QROC, QRP/QRPL, TCS, « Ne jamais spoiler le diagnostic »)
1. Questions ORIGINALES : même notion, même piège, même manière d'aborder le sujet qu'aux annales, mais cas cliniques, énoncés et options reformulés ; ne recopie aucune question d'annale. Varie les angles d'un même thème comme l'analyse les a relevés.
2. Rigueur médicale absolue : référentiels des Collèges (EDN/R2C) et recommandations françaises en vigueur ; chiffres, seuils et posologies vérifiés ; en cas de doute sur un fait, ne le mets pas.
3. Sections : champ code ("SQI1", "DP1", "mDP1", "KFP1", "TCS1"…), title (« DP1 — <terrain, motif> », SANS le diagnostic à trouver ; « SQI1 » pour les questions isolées), label (pour le sous-titre, ex. « DP1 douleur pelvienne aiguë chez une femme de 26 ans »), locked = true pour DP/mDP/KFP/TCS (et seulement eux). Contexte (champ context) sur la 1re question de chaque dossier ; le cas évolue ensuite dans les énoncés, de façon cohérente d'une question à l'autre.
4. Chaque option porte une justification (just) d'une à deux phrases qui explique (seuil, mécanisme, raison) sans reformuler l'option ; un rappel transversal va dans note. TCS : échelle des annales (improbable / peu probable / ni plus ou moins probable / probable / certain), une seule réponse, note explicative obligatoire.
5. QRM au nombre de bonnes réponses varié (1 à 5) et aux positions variées ; QRU : une seule réponse ; QRP/QRPL : nombre de bonnes réponses = nombre à sélectionner, énoncé qui le précise ; QROC : réponse courte avec plusieurs variantes acceptées (accept), sans « ou » ni « / » à l'intérieur d'une variante.
6. Items indispensables (mandatory, sur une option juste) / inacceptables (unacceptable, sur une option fausse et dangereuse) : comme la faculté les emploie, quand c'est défendable.
7. Pas de rang dans un sujet type : rank = null partout. Le générateur ne gère pas les images : donne en texte les résultats d'imagerie, d'ECG, de biologie ou d'anatomopathologie ; pas de QZONE (remplace-la par une QRU/QRM équivalente).
8. title « UE ${u.ue} — ${u.matiere} · Sujet type (synthèse des annales ${u.years}) » ; intro_note : 2-3 phrases expliquant que le sujet a été construit à partir de la lecture de toutes les annales de l'UE disponibles (${u.years}), de l'analyse des questions qui reviennent le plus et de leurs différentes formulations, et listant les thèmes travaillés ; footer « N questions · sujet type · UE ${u.ue} ${u.matiere} · D3 ${u.trimestre.toUpperCase()} · BobMed. » (N réel) ; file "${u.file}".
9. Auto-relecture avant de rendre : relis chaque question comme un examinateur (une seule lecture possible, clé exacte, justifications exactes, aucune question qui souffle la réponse d'une autre).

ÉTAPES (économise les allers-retours d'outils : écris le spec en une ou deux fois)
a. Spec dans ${specPath(u)}.
b. python3 ${SP}/render_quiz.py ${specPath(u)} --check → corrige jusqu'à 0 erreur et sans avertissement « option sans justification ».
c. python3 ${SP}/render_quiz.py ${specPath(u)} (écrit ${R}/${u.file}).
d. cd ${R} && python3 validate_quiz.py ${u.file} && python3 test_quiz.py ${u.file} → corrige et recommence jusqu'à 0 erreur et tests passés.
Aucune autre modification du dépôt, aucune opération git. Rends le bilan.`
}

function auditPrompt(u, an, w) {
  const b = name(u)
  return `Tu es l'auditeur du SUJET TYPE ${R}/${u.file} (UE ${u.ue} — ${u.matiere}, D3 ${u.trimestre.toUpperCase()}), rédigé par un autre agent à partir de l'analyse ${anPath(u)}. Spec : ${specPath(u)}. Pars du principe qu'il contient des erreurs et cherche-les.
Bilan de l'analyse : ${JSON.stringify(an || {})}
Bilan du rédacteur : ${JSON.stringify(w || {})}
Objectif de l'utilisateur : une réplique d'une épreuve qui aurait été susceptible de tomber à cette faculté, construite à partir des questions qui reviennent le plus aux annales et de leurs différentes formulations.

1. COPIE À L'AVEUGLE, avant toute lecture du spec, du HTML ou de l'analyse : mkdir -p ${SP}/blind && python3 ${SP}/strip_spec.py ${specPath(u)} > ${SP}/blind/${b}.md ; lis UNIQUEMENT ce fichier et réponds à chaque question comme un excellent candidat à l'EDN (QRM : toutes les justes ; QRU/TCS : une ; QRP : exactement le nombre demandé ; QROC : réponse courte) ; écris ${SP}/blind/${b}.answers.json ({"SQI1-Q1": "AC", "DP1-Q1": "B", …}, identifiants exactement comme dans la copie). Note les questions ambiguës ou qui soufflent la réponse. (Si ${SP}/blind/${b}.answers.json existe déjà — passage précédent interrompu —, réutilise-le.)
2. python3 ${SP}/compare_blind.py ${specPath(u)} ${SP}/blind/${b}.answers.json, puis tranche CHAQUE divergence avec le référentiel : clé fausse → corrige clé ET justifications ; question ambiguë → reformule pour qu'une seule réponse soit défendable ; ton erreur → garde, en vérifiant que la justification de l'option piège l'explique.
3. Audit médical complet : exactitude de chaque énoncé, option, verdict, justification et note (référentiels des Collèges, recommandations françaises en vigueur) ; justifications sans paraphrase ; QRM au nombre de bonnes réponses varié ; QROC avec variantes suffisantes ; TCS bien construits ; items indispensables/inacceptables défendables ; titres de dossiers sans diagnostic ; cohérence du cas d'une question à l'autre ; rank null partout.
4. FIDÉLITÉ AUX ANNALES et PLAUSIBILITÉ : relis l'analyse puis, par sondage, les annales (${u.annales.join(', ')}). Vérifie que l'architecture reproduit celle des épreuves récentes ; que les thèmes et questions qui reviennent le plus sont bien entraînés, sous des angles et formulations variés ; que l'analyse n'a pas oublié un thème récurrent (si oui, ajoute ou remplace des questions) ; qu'aucune question n'est recopiée d'une annale ; que le style (longueur et ton des énoncés, nombre d'options, proportions de formats, difficulté) est celui de cette faculté — bref, qu'un enseignant de l'UE aurait pu poser ce sujet.
5. Corrige directement le spec, puis python3 ${SP}/render_quiz.py ${specPath(u)} && cd ${R} && python3 validate_quiz.py ${u.file} && python3 test_quiz.py ${u.file}, jusqu'à 0 erreur et tests passés. Aucune opération git, aucun autre fichier du dépôt.
Rends le bilan des corrections, et dans themes_for_portal une liste de 8 à 14 thèmes (séparés par des virgules, sans diagnostic de dossier verrouillé) pour la carte du portail.`
}

const out = []
for (let i = 0; i < UES.length; i += CHUNK) {
  const chunk = UES.slice(i, i + CHUNK)
  log(`Sujets types : ${chunk.map(u => 'UE ' + u.ue).join(', ')}`)
  const res = await pipeline(chunk,
    u => agent(analysisPrompt(u), { label: `analyse:UE${u.ue}`, phase: 'Analyse', schema: AN_SCHEMA }),
    (an, u) => agent(writerPrompt(u, an), { label: `sujet:UE${u.ue}`, phase: 'Rédaction', schema: W_SCHEMA, model: 'sonnet' }).then(w => ({ an, w })),
    (x, u) => agent(auditPrompt(u, x.an, x.w), { label: `audit:UE${u.ue}`, phase: 'Audit', schema: A_SCHEMA }).then(a => ({ ue: u.ue, file: u.file, analysis: x.an, writer: x.w, audit: a })),
  )
  out.push(...res.map((r, j) => r || { ue: chunk[j].ue, file: chunk[j].file, failed: true }))
}
return out
