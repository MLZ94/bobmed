# BobMed — Instructions pour Claude Code

## Contexte général

Site de révision médicale statique (HTML/CSS/JS, zéro build system). Chaque quiz est un fichier HTML autonome : CSS, JS et images (base64) tous embarqués dans le même fichier.

Branche de développement par défaut : `main`  
Ne jamais inclure de lien vers la session Claude dans les commits, PR, commentaires ou code.

**Règle absolue** : à chaque création d'une nouvelle annale (quiz HTML), mettre à jour **dans le même geste** la page d'index correspondante (portail de trimestre `dX/tY/index.html` et/ou `annales/index.html`) pour y ajouter le lien d'accès — jamais d'annale orpheline sans navigation. Par défaut, pousser directement sur `main` (sauf instruction contraire explicite de l'utilisateur).

---

## Structure du site

```
index.html           ← page d'accueil (blocs D1 et D2, source de vérité pour la navigation)
annales/index.html   ← portail annales D1 (UE 1.1, UE 3, UE 9.2, UE 9.3 — pas de subdivision par trimestre)
annales/Quiz_*.html  ← quiz D1 (toutes UE confondues, session normale/rattrapage)
exercices/           ← entraînement par thème (biostat UE 1.1), hors trimestre
microbiologie/       ← portail + fiches + quiz UE3 (révisions transversales), hors trimestre
numerique/           ← quiz numérique biostat, hors trimestre
d2/tN/index.html     ← portail du trimestre N de D2 (N = 1 à 4)
d2/tN/Quiz_*.html    ← quiz UE de D2-TN, fichier physique dans le dossier du trimestre
```

**IMPORTANT — D1 n'a PAS de sous-dossiers de trimestre** (`d1/t1/`, `d1/t2/`, etc. n'existent pas et ne doivent pas être créés). Toutes les annales D1 vivent à plat dans `annales/`. Seul **D2** est subdivisé par trimestre (`d2/t1/` à `d2/t4/`).

### Table de correspondance UE ↔ trimestre D2 (page d'accueil = source de vérité)

| Trimestre | UE couvertes |
|---|---|
| `d2/t1/` | UE 8.2 Cardiologie · UE 7.1 Pneumologie · UE 6 Maladies transmissibles |
| `d2/t2/` | UE 8.1 Hépato-Gastro/Chir-Dig · UE 4.1 Neurologie-MPR · **UE 3 Psy/Addicto** |
| `d2/t3/` | UE 4.3 Dermatologie · UE 7.2 Médecine Interne · UE 8.4 Nephro/Uro |
| `d2/t4/` | UE 4.2 ORL/Ophtalmo/Chir maxillo-faciale · UE 7.3 Rhumatologie · UE 11.1 Chir Orthopédique · UE 8.3 Endocrino/Nutrition · UE 12.1 Anglais · UE 12.2 LCA |

**Avant de créer un portail de trimestre ou de placer une annale**, toujours relire `index.html` (page d'accueil) pour vérifier si le bloc D2/TN correspondant existe déjà et quelles UE lui sont attribuées — ne jamais deviner ou inventer un trimestre. En cas de doute sur le trimestre d'une UE non listée ci-dessus, demander à l'utilisateur plutôt que de supposer.

### Ordre de classement des annales dans un portail de trimestre

À l'intérieur d'un portail (`annales/index.html` ou `d2/tN/index.html`), les annales sont groupées **par UE** (un bloc/titre `.ue` par UE), puis à l'intérieur de chaque groupe UE, classées **par ordre chronologique croissant** (session la plus ancienne en premier, la plus récente en dernier), à l'image de ce qui existe déjà dans `annales/index.html` (ex. UE 1.1 : 2022-2023 S1 → S2 → 2023-2024 S1 → S2 → 2024-2025 S1 → S2). Une session normale précède toujours son rattrapage de la même année. Respecter cet ordre à chaque ajout d'une nouvelle annale, quel que soit le portail concerné.

Couleur accent par défaut : `--acc:#b06800` (ambré/brun doré, utilisé pour D2/T4).

---

## Design système des quiz (à respecter rigoureusement)

### Variables CSS racine

```css
:root {
  --bg:#f6f5f1; --card:#fff; --ink:#1d1d1b; --mut:#6a6a66;
  --line:#e3e1d8; --vrai:#1a7f37; --vraibg:#e9f6ec;
  --faux:#c0392b; --fauxbg:#fbecea; --neu:#9a6a00; --acc:#b06800;
}
```

### Header sticky (scorebar)

```html
<header>
  <h1>UE X.X — Titre · Session (mois année)</h1>
  <div class="sub">N questions : SQI1 (n) · DP1 (n, verrouillé) · ...</div>
  <div class="scorebar">
    <span class="pill">Validées : <b id="s-done">0/N</b></span>
    <span class="pill">Score : <b id="s-ok">0/M</b></span>
    <span class="pill"><button id="revealall" style="padding:2px 10px">Tout révéler</button></span>
    <span class="pill"><button id="reset" style="padding:2px 10px">Recommencer</button></span>
  </div>
</header>
```

M = nombre de questions notées (hors QROC).

### Structure d'une question

Chaque question `<div class="q">` contient dans cet ordre :
1. `<div class="qhead">` — numéro + type + status
2. `<div class="dpctx">` — contexte clinique DP (optionnel, uniquement Q1 du DP)
3. `<div class="stem">` — énoncé
4. `<div class="extra">` — image (optionnel)
5. `<ul class="opts">` ou `<textarea class="qrocin">` — options ou zone de saisie
6. `<div class="actions">` — boutons
7. `<div class="correction" hidden>` — correction

```html
<div class="q [locked]" id="SEC-Qn" data-correct="AB" data-type="QRM">
  <div class="qhead">
    <span class="qnum">SEC Q1</span>
    <span class="qtype">QRM</span>
    <span class="status" aria-live="polite"></span>
  </div>
  <!-- contexte DP uniquement sur Q1 -->
  <div class="dpctx">Données du cas clinique…</div>
  <div class="stem">Énoncé de la question…</div>
  <!-- image si présente -->
  <div class="extra"><img src="data:image/jpeg;base64,…" style="max-width:100%;border-radius:8px;margin:8px 0 12px"></div>
  <ul class="opts">
    <li class="opt" data-l="A" data-correct="1"><span class="box">A</span><span class="otext">Texte option A</span></li>
    <li class="opt" data-l="B" data-correct="0"><span class="box">B</span><span class="otext">Texte option B</span></li>
  </ul>
  <div class="actions">
    <button class="validate">Valider</button>
    <button class="show" type="button">Voir la réponse</button>
  </div>
  <div class="correction" hidden>
    <div class="ans">Réponse : A, B</div>
    <div class="note">Explication…</div>
  </div>
</div>
```

### Attributs data importants

| Attribut | Valeur | Description |
|---|---|---|
| `data-type` | `QRM` / `QRU` / `QROC` | Type de question |
| `data-correct` | `"AB"` / `"C"` / `""` | Lettres correctes concaténées (vide pour QROC) |
| `data-l` sur `.opt` | `"A"` … | Lettre de l'option |
| `class="q locked"` | — | Question verrouillée (blur + pointer-events:none) |
| `id` | `"SQI1-Q3"` | Identifiant unique |

### CSS clés

```css
/* Verrouillage par flou — NE PAS utiliser display:none ni animation */
.q.locked { opacity:.2; filter:blur(3px); pointer-events:none; user-select:none; }
.q { transition: opacity .35s ease, filter .35s ease; }

/* Badges question */
.qnum { font-size:12px; font-weight:600; color:#fff; background:var(--acc); border-radius:6px; padding:2px 8px; }
.qtype { font-size:11px; font-weight:600; color:var(--mut); border:1px solid var(--line); border-radius:5px; padding:1px 6px; }

/* Options */
.opt { display:flex; gap:10px; align-items:flex-start; border:1px solid var(--line); border-radius:9px; padding:9px 11px; margin:7px 0; cursor:pointer; }
.opt .box { flex:none; width:24px; height:24px; border:1.5px solid #b9b7ad; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:600; }
.opt.sel { border-color:var(--acc); background:#fdf3e0; }
.opt.sel .box { background:var(--acc); border-color:var(--acc); color:#fff; }
.opt.correct { border-color:var(--vrai); background:var(--vraibg); }
.opt.correct .box { background:var(--vrai); border-color:var(--vrai); color:#fff; }
.opt.wrong { border-color:var(--faux); background:var(--fauxbg); }
.opt.missed { border-style:dashed; border-color:var(--vrai); }

/* Contexte clinique DP */
.dpctx { background:#fef8ec; border:1px solid #f0dfa0; border-left:4px solid var(--acc); border-radius:8px; padding:10px 14px; font-size:14px; color:#4a3200; margin-bottom:14px; }

/* Note de correction */
.note { background:#fef8ec; border:1px solid #f0dfa0; border-radius:8px; padding:9px 12px; font-size:14px; margin:6px 0 10px; color:#4a3200; }
```

---

## Types de questions et règles

### QRM (Question à Réponses Multiples)
- Plusieurs options cochables (toggle)
- `data-type="QRM"` — `data-correct="ABC"` (lettres concaténées)
- Barème EDN : 0 discordance = 1 pt · 1 = 0,5 pt · 2 = 0,2 pt · ≥3 = 0 pt
- Après validation : options correctes en vert (`.correct`), mauvaises cochées en rouge (`.wrong`), correctes non cochées en vert pointillé (`.missed`)

### QRU (Question à Réponse Unique)
- Une seule option sélectionnable à la fois (radio-like)
- `data-type="QRU"` — `data-correct="B"` (une seule lettre)
- Barème binaire : bonne réponse = 1 pt, mauvaise = 0 pt

### QROC (Question à Réponse Ouverte et Courte)
- Zone de texte libre, auto-correction par l'étudiant
- `data-type="QROC"` — `data-correct=""` (toujours vide)
- Non notée dans le score (exclue du compteur M)
- Bouton "Voir la réponse" uniquement (pas de "Valider")
- Correction dans `<div class="qrocmodel"><p>…</p></div>`

### QRPL (Question à Réponses Partiellement Liées)
- Traiter comme QRM avec EDN standard
- Indiquer le nombre de réponses attendues dans l'énoncé : `<em>(4 réponses attendues)</em>`

### TCS (Test de Concordance de Script)
- Traiter comme QRU
- Options fixes : A = improbable · B = peu probable · C = ni plus ou moins probable · D = probable · E = certain
- `data-correct` = réponse de l'expert principal
- Dans la correction : mentionner les autres réponses validées par les experts

---

## Système de verrouillage des DP/KFP/TCS

Les sections DP, KFP et TCS sont verrouillées question par question : on ne peut accéder à Q2 qu'après avoir validé Q1, etc.

**IMPORTANT** : utiliser le système de **flou progressif** (`.locked`) — ne jamais utiliser `display:none` ni des animations `@keyframes`.

La **première question** de chaque section DP/KFP/TCS est libre (non verrouillée). Les suivantes sont ajoutées dynamiquement par `initLocks()`.

```javascript
function initLocks() {
  let nextFree = false, inDP = false;
  for (const el of document.querySelector('.wrap').children) {
    if (el.classList.contains('sect')) {
      inDP = /DP|KFP|TCS/.test(el.textContent);
      nextFree = inDP;
      continue;
    }
    if (el.classList.contains('q')) {
      if (nextFree) { nextFree = false; }
      else if (inDP) { el.classList.add('locked'); }
    }
  }
}

function unlockNext(q) {
  let el = q.nextElementSibling;
  while (el) {
    if (el.classList.contains('sect')) break;
    if (el.classList.contains('q') && el.classList.contains('locked')) {
      el.classList.remove('locked');
      setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 100);
      break;
    }
    el = el.nextElementSibling;
  }
}
```

Les sections SQI sont toutes libres (pas de verrouillage).

---

## JS complet de référence

```javascript
const $ = s => document.querySelectorAll(s);
function fmtPts(p) { return (Math.round(p * 100) / 100).toString().replace('.', ','); }
function qPoints(disc, isQRU) {
  if (isQRU) return disc === 0 ? 1 : 0;
  return disc === 0 ? 1 : (disc === 1 ? 0.5 : (disc === 2 ? 0.2 : 0));
}

function grade(q) {
  if (q.dataset.type === 'QROC') return;
  const correct = new Set(q.dataset.correct.split(''));
  const sel = new Set([...q.querySelectorAll('.opt.sel')].map(o => o.dataset.l));
  let disc = 0;
  q.querySelectorAll('.opt').forEach(o => {
    const l = o.dataset.l, isC = correct.has(l), isS = sel.has(l);
    o.classList.remove('sel');
    if (isC && isS) o.classList.add('correct');
    else if (!isC && isS) { o.classList.add('wrong'); disc++; }
    else if (isC && !isS) { o.classList.add('missed'); disc++; }
    let m = document.createElement('span'); m.className = 'mark';
    if (isC && isS) m.textContent = '✓';
    else if (!isC && isS) m.textContent = '✗';
    else if (isC && !isS) { m.textContent = 'manqué'; m.style.color = 'var(--vrai)'; }
    if (m.textContent) o.appendChild(m);
  });
  const isQRU = q.dataset.type === 'QRU';
  const pts = qPoints(disc, isQRU);
  q.classList.add('done');
  q.querySelector('.correction').hidden = false;
  const st = q.querySelector('.status'); st.style.color = '';
  st.textContent = fmtPts(pts) + ' / 1';
  if (!isQRU && disc > 0) st.textContent += ' (' + disc + ' incohérence' + (disc > 1 ? 's' : '') + ')';
  st.className = 'status ' + (pts === 1 ? 'ok' : (pts === 0 ? 'ko' : 'part'));
  if (pts > 0 && pts < 1) st.style.color = '#9a6a00';
  q.querySelector('.validate').disabled = true;
  q.dataset.pts = pts; q.dataset.result = pts === 1 ? '1' : '0';
  updateScore(); unlockNext(q);
}

function reveal(q, skipUnlock) {
  if (q.classList.contains('done')) return;
  if (q.dataset.type !== 'QROC') {
    const correct = new Set(q.dataset.correct.split(''));
    q.querySelectorAll('.opt').forEach(o => { o.classList.remove('sel'); if (correct.has(o.dataset.l)) o.classList.add('correct'); });
    const v = q.querySelector('.validate'); if (v) v.disabled = true;
  } else {
    const st = q.querySelector('.status'); st.textContent = 'révélée'; st.className = 'status rl';
  }
  q.classList.add('done'); q.querySelector('.correction').hidden = false;
  if (q.dataset.pts === undefined) q.dataset.result = 'skip';
  updateScore(); if (!skipUnlock) unlockNext(q);
}

function updateScore() {
  const qs = [...$('.q')]; const all = qs.length;
  const done = qs.filter(q => q.classList.contains('done')).length;
  const grad = qs.filter(q => q.dataset.type !== 'QROC').length;
  let pts = 0;
  qs.forEach(q => { if (q.dataset.pts !== undefined && q.dataset.pts !== '') pts += parseFloat(q.dataset.pts); });
  const sd = document.getElementById('s-done'); if (sd) sd.textContent = done + '/' + all;
  const so = document.getElementById('s-ok'); if (so) so.textContent = fmtPts(pts) + '/' + grad;
}

document.addEventListener('click', e => {
  const li = e.target.closest('.opt');
  if (li) {
    const q = li.closest('.q');
    if (!q.classList.contains('done')) {
      if (q.dataset.type === 'QRU') { q.querySelectorAll('.opt').forEach(o => o.classList.remove('sel')); li.classList.add('sel'); }
      else { li.classList.toggle('sel'); }
    }
    return;
  }
  const v = e.target.closest('.validate'); if (v) { grade(v.closest('.q')); return; }
  const s = e.target.closest('.show'); if (s) { reveal(s.closest('.q')); return; }
});

const rb = document.getElementById('reset'); if (rb) rb.addEventListener('click', () => location.reload());
const ra = document.getElementById('revealall'); if (ra) ra.addEventListener('click', () => {
  $('.q.locked').forEach(q => q.classList.remove('locked'));
  $('.q').forEach(q => reveal(q, true));
});
initLocks(); updateScore();
```

---

## Règle absolue : texte identique au PDF

Le texte des énoncés, données cliniques et items doit être **rigoureusement identique** au PDF source :
- Orthographe, ponctuation, casse, abréviations : copier-coller exact
- Nombre d'options : respecter scrupuleusement (certaines questions ont 4 options A–D, pas 5)
- Typos présentes dans le PDF : les conserver telles quelles

---

## Images

- Extraire avec PyMuPDF (`fitz`) depuis les PDF sources
- Encoder en base64 JPEG et embarquer directement dans le HTML
- Placer dans `<div class="extra"><img src="data:image/jpeg;base64,…" style="max-width:100%;border-radius:8px;margin:8px 0 12px"></div>`
- Positionner après `<div class="stem">` et avant `<ul class="opts">`

---

## Portails de trimestre (index.html)

```html
<!-- Carte quiz -->
<a class="qz" href="Quiz_UE7.3_2024.html">
  <div class="qz-t">2023-2024 · Session normale (juin 2024)</div>
  <div class="qz-d">N questions — SQI1 (n) · DP1 (n, verrouillé) · …</div>
  <span class="qz-go">Ouvrir le quiz →</span>
</a>
<!-- Lien retour -->
<a class="back" href="../../index.html">← Accueil BobMed</a>
```

---

## Sécurité

Ne jamais inclure de lien vers une session Claude (`claude.ai/code/session_…`) dans :
- les messages de commit
- les corps de PR
- les commentaires de code
- tout fichier poussé dans le dépôt
