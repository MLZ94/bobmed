export const meta = {
  name: 'd3-nj-justifications',
  description: 'Justifications non officielles ◈ sur les 18 annales D3 : rédaction puis vérification adversariale',
  phases: [
    { title: 'Rédaction', detail: 'un rédacteur par annale (UE 2 nov. 2022 en deux)' },
    { title: 'Vérification', detail: 'relecture adversariale : exactitude, cohérence avec le corrigé, sélectivité' },
  ],
}
const SP = '/tmp/claude-0/-home-user/55cc2afb-deb2-5236-a438-a491d4be9ce0/scratchpad'
const UNITS = [
  { id: 'UE2_2022-2023_S1_novembre.p1', html: 'd3/t1/Quiz_UE2_2022-2023_S1_novembre.html', scope: 'uniquement la section SQI1 (questions SQI1-…)' },
  { id: 'UE2_2022-2023_S1_novembre.p2', html: 'd3/t1/Quiz_UE2_2022-2023_S1_novembre.html', scope: 'uniquement les sections DP1, DP2 et DP3' },
  { id: 'UE2_2022-2023_septembre', html: 'd3/t1/Quiz_UE2_2022-2023_septembre.html' },
  { id: 'UE2_2023-2024_S1_novembre', html: 'd3/t1/Quiz_UE2_2023-2024_S1_novembre.html' },
  { id: 'UE2_2024-2025_S1_novembre', html: 'd3/t1/Quiz_UE2_2024-2025_S1_novembre.html' },
  { id: 'UE2_2024-2025_S2', html: 'd3/t1/Quiz_UE2_2024-2025_S2.html' },
  { id: 'UE5_2022-2023_S1', html: 'd3/t2/Quiz_UE5_2022-2023_S1.html', reuse: 'Les questions SQI1-Q16 à SQI1-Q20 sont identiques (options dans un autre ordre possible) aux questions SQI1-Q1, Q4, Q5, Q11 et Q12 de /home/user/bobmed/d2/t2/Quiz_UE4.1_2022-2023_S1.html, qui portent déjà des justifications ◈ relues : reprends-les en appariant par le TEXTE des options (pas par la lettre), en les adaptant seulement si nécessaire.' },
  { id: 'UE5_2023-2024_S1_janvier', html: 'd3/t2/Quiz_UE5_2023-2024_S1_janvier.html' },
  { id: 'UE5_2024-2025_S1', html: 'd3/t2/Quiz_UE5_2024-2025_S1.html' },
  { id: 'UE5_2024-2025_S2', html: 'd3/t2/Quiz_UE5_2024-2025_S2.html' },
  { id: 'UE7.3_2024-2025_S1', html: 'd3/t2/Quiz_UE7.3_2024-2025_S1.html' },
  { id: 'UE9_2022-2023_S1', html: 'd3/t2/Quiz_UE9_2022-2023_S1.html' },
  { id: 'UE9_2023-2024_DFG3', html: 'd3/t2/Quiz_UE9_2023-2024_DFG3.html' },
  { id: 'UE9_2023-2024_S1', html: 'd3/t2/Quiz_UE9_2023-2024_S1.html' },
  { id: 'UE9_2024-2025_S1', html: 'd3/t2/Quiz_UE9_2024-2025_S1.html' },
  { id: 'UE10_2022-2023_S1', html: 'd3/t3/Quiz_UE10_2022-2023_S1.html' },
  { id: 'UE10_2023-2024_S1', html: 'd3/t3/Quiz_UE10_2023-2024_S1.html' },
  { id: 'UE10_2024-2025_S1', html: 'd3/t3/Quiz_UE10_2024-2025_S1.html' },
  { id: 'UE11.2_2022-2023_S1', html: 'd3/t3/Quiz_UE11.2_2022-2023_S1.html', reuse: 'Les questions DL1-Q1, Q3, Q4 et Q9 sont identiques à des questions de /home/user/bobmed/d2/t4/Quiz_UE11.1_2021-2022_S1.html (SQI1-Q1, Q3, Q6, Q15) ; elles n\'y ont pas de ◈ : traite-les normalement.' },
]
const EXTRACT = u => `${SP}/ex/Quiz_${u.id.replace(/\.p[12]$/, '')}.md`
const JSONP = u => `${SP}/nj/${u.id}.json`

const W_SCHEMA = { type: 'object', properties: {
  eligible_options: { type: 'integer' }, nj_count: { type: 'integer' }, rappel_count: { type: 'integer' },
  doubtful_official_answers: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } },
  required: ['eligible_options', 'nj_count', 'rappel_count', 'doubtful_official_answers', 'notes'] }
const V_SCHEMA = { type: 'object', properties: {
  nj_count_before: { type: 'integer' }, nj_count_after: { type: 'integer' }, corrected: { type: 'integer' },
  removed: { type: 'integer' }, added: { type: 'integer' }, medical_errors_fixed: { type: 'array', items: { type: 'string' } },
  doubtful_official_answers: { type: 'array', items: { type: 'string' } }, check_ok: { type: 'boolean' } },
  required: ['nj_count_before', 'nj_count_after', 'corrected', 'removed', 'added', 'medical_errors_fixed', 'doubtful_official_answers', 'check_ok'] }

const COMMON = `Contexte : BobMed, site de révision médicale. Les annales D3 (6e année) de /home/user/bobmed/d3/ reproduisent fidèlement les épreuves officielles avec la correction VRAI/FAUX du fichier réponse du jury, presque jamais justifiée. On ajoute a posteriori des justifications NON OFFICIELLES ◈, selon la section « Justifications non officielles ◈ » de CLAUDE.md (format, sélectivité, rédaction, texte à proscrire) — relis-la attentivement, elle fait foi.

Règles clés (rappel) :
- SÉLECTIVITÉ : surtout pas tous les items. Justifier les items qui reposent sur un raisonnement (seuil chiffré, indication/contre-indication, mécanisme, chronologie, diagnostic différentiel, piège tentant, définition facilement confondue). Ne pas justifier les évidences. Ordre de grandeur : 30 à 55 % des options éligibles de l'annale. Priorité aux items INDISPENSABLES et INACCEPTABLES et à leurs voisins : c'est là que se jouent les points.
- EXCLUS : TCS, QROC, QZONE, items neutralisés, items qui ont déjà une justification officielle (ligne « JUSTIF OFFICIELLE » de l'extrait) ou dont l'explication est déjà dans une NOTE OFFICIELLE de la question.
- RÉDACTION : une phrase de 15 à 35 mots, qui commence directement par l'explication (jamais « VRAI »/« FAUX »), vocabulaire médical exact, conforme aux référentiels des Collèges et recommandations françaises en vigueur. Elle explique le verdict officiel et ne le contredit JAMAIS ; si le verdict officiel paraît faux, énoncer le fait médical exact puis ajouter « ; la correction officielle compte pourtant cette proposition vraie/fausse. ». Questions à énoncé inversé (« laquelle est fausse ») : préfixe court « Proposition vraie : … » / « C'est la proposition fausse : … ».
- À PROSCRIRE : reprendre l'option (même phrase, synonyme, simple négation), renvois à la mécanique du sujet (« cf. item A », « cf. énoncé »), « à recouper avec le cours », « point d'attention », humour. Ne jamais décrire une image sans l'avoir regardée (chemins [IMAGE: …] dans l'extrait, à lire avec Read).
- Rappels ◈ : rares (0 à 4 par annale), seulement pour une notion transversale utile à toute la question et absente des notes officielles.

Format du fichier JSON (lu par le script d'insertion) :
{"file": "<chemin html relatif au dépôt>", "nj": [{"qid": "SQI1-Q3", "l": "B", "text": "…"}], "rappels": [{"qid": "DP1-Q2", "text": "…"}]}
Balises autorisées dans text : <sub> <sup> <b> <i>. Contrôle : python3 ${SP}/apply_nj.py <json> --check (doit afficher 0 erreur ; il refuse TCS/QROC/QZONE, items neutralisés et items déjà justifiés). N'exécute JAMAIS apply_nj.py sans --check, ne modifie aucun fichier du dépôt, aucune opération git.`

function writerPrompt(u) {
  return `${COMMON}

TA TÂCHE : rédiger les justifications ◈ de l'annale /home/user/bobmed/${u.html}${u.scope ? ` — ${u.scope}` : ''}.
Entrée principale : l'extrait texte ${EXTRACT(u)} (énoncés, contextes, options avec verdict officiel « => VRAI/FAUX », items INDISPENSABLE/INACCEPTABLE, NOTES et JUSTIF OFFICIELLES, images). Consulte le HTML si besoin.
${u.reuse ? 'Réutilisation : ' + u.reuse : ''}
Pour chaque question éligible, décide option par option si une justification apporte quelque chose, puis rédige-la. Avant de rendre, relis toi-même chaque entrée de façon critique, comme un relecteur adversarial (exactitude médicale stricte, cohérence avec le verdict officiel et la bonne lettre, pas de paraphrase, sélectivité) : il n'y aura pas d'autre relecture. Écris le JSON dans ${JSONP(u)} (champ "file" = "${u.html}"), puis lance le contrôle --check et corrige jusqu'à 0 erreur.
Rends : nombre d'options éligibles de ton périmètre, nombre de ◈, nombre de rappels, et la liste des questions où le verdict officiel te paraît douteux (identifiant + raison).`
}
function verifierPrompt(u, w) {
  return `${COMMON}

TA TÂCHE : relecture ADVERSARIALE des justifications ◈ proposées par un autre rédacteur pour /home/user/bobmed/${u.html}${u.scope ? ` — ${u.scope}` : ''}, dans ${JSONP(u)}. Pars du principe que des erreurs s'y cachent et cherche-les.
Pour CHAQUE entrée, vérifie :
1. Exactitude médicale stricte (référentiels des Collèges, recommandations françaises actuelles : HAS, sociétés savantes) — chiffres, seuils, posologies, classifications.
2. Cohérence avec le verdict officiel de l'option (extrait ${EXTRACT(u)}, « => VRAI/FAUX ») : la justification doit l'expliquer, jamais le contredire ; attention aux lettres décalées (qid/l qui ne correspondent pas à l'option visée).
3. Valeur pédagogique : pas de reprise de l'option, pas de banalité, 15-35 mots, aucune formule proscrite, pas de description d'image non vérifiée (regarde les images citées).
Puis vérifie la SÉLECTIVITÉ globale : supprime les ◈ sur des évidences ; ajoute les ◈ manquants sur des items à raisonnement, en priorité les items INDISPENSABLES/INACCEPTABLES et les pièges. Cible : 30 à 55 % des options éligibles.
Le rédacteur signalait : ${JSON.stringify(w || {})}
Corrige directement ${JSONP(u)}, relance le contrôle --check jusqu'à 0 erreur. Rends le bilan (nombre avant/après, corrigés, supprimés, ajoutés, erreurs médicales corrigées, verdicts officiels douteux confirmés).`
}

phase('Rédaction')
const SEL = UNITS.filter(u => (args && args.units ? args.units.includes(u.id) : true))
const NOVERIFY = !!(args && args.noverify)
const VONLY = new Set((args && args.verify_only) || [])
const res = await pipeline(SEL,
  u => (VONLY.has(u.id) ? Promise.resolve({ eligible_options: 0, nj_count: 0, rappel_count: 0, doubtful_official_answers: [], notes: 'JSON rédigé lors d\'un passage précédent (rédacteur Sonnet) : relis-le en entier.' }) : agent(writerPrompt(u), { label: `nj:${u.id}`, phase: 'Rédaction', schema: W_SCHEMA, model: (args && args.writer_model) || undefined })),
  (w, u) => (NOVERIFY || !w) ? ({ unit: u.id, writer: w, verifier: null }) : agent(verifierPrompt(u, w), { label: `verif:${u.id}`, phase: 'Vérification', schema: V_SCHEMA }).then(v => ({ unit: u.id, writer: w, verifier: v })),
)
return res
