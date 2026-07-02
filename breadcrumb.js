/**
 * breadcrumb.js — Fil d'Ariane universel BobMed
 * Injecter dans n'importe quel quiz HTML via :
 *   <script src="../../breadcrumb.js"></script>  (depuis d2/tN/)
 *   <script src="../breadcrumb.js"></script>      (depuis annales/)
 *
 * Le script détecte automatiquement le contexte depuis l'URL :
 *   d2/tN/Quiz_*.html  →  BobMed › D2 › TN — <titre> › <quiz>
 *   annales/Quiz_*.html →  BobMed › D1 — Annales › <quiz>
 *   microbiologie/...   →  BobMed › Microbiologie › <quiz>
 *   exercices/...       →  BobMed › Exercices ED › <quiz>
 *   numerique/...       →  BobMed › Quiz numérique › <quiz>
 *
 * Dépendances : CSS .breadcrumb doit être présent dans la page (voir portails).
 * Si absent, le style minimal est injecté automatiquement.
 */
(function () {
  /* ── 1. Injecter le CSS si la page ne l'a pas encore ── */
  if (!document.querySelector('style[data-bc]')) {
    var s = document.createElement('style');
    s.setAttribute('data-bc', '1');
    s.textContent = [
      '.breadcrumb{display:flex;align-items:center;flex-wrap:wrap;gap:4px;font-size:13px;',
      'color:var(--mut,#5b6b73);margin-bottom:18px;padding:7px 12px;',
      'background:var(--card,#fff);border:1px solid var(--line,#dfe4e2);border-radius:10px}',
      '.breadcrumb a{color:var(--acc,#4f46e5);text-decoration:none;font-weight:500}',
      '.breadcrumb a:hover{text-decoration:underline}',
      '.breadcrumb .sep{color:var(--line,#dfe4e2);font-size:15px;margin:0 2px}',
      '.breadcrumb .current{color:var(--ink,#132025);font-weight:600}',
      'html.dark .breadcrumb{background:#1a1d27;border-color:#2d3748}'
    ].join('');
    document.head.appendChild(s);
  }

  /* ── 2. Analyser l'URL ── */
  var path = window.location.pathname;
  var parts = path.split('/').filter(Boolean);

  /* Trouver la racine (index.html) relative */
  var depth = parts.length - 1; /* nombre de segments de dossier au-dessus */
  var root = '';
  for (var i = 0; i < depth; i++) root += '../';
  if (!root) root = './';

  /* Label du quiz courant = title de la page, tronqué */
  var pageTitle = document.title || 'Quiz';
  /* Raccourcir : garder avant le premier ' — ' ou '|' si trop long */
  var quizLabel = pageTitle.split(' — ')[0].split(' | ')[0];
  if (quizLabel.length > 55) quizLabel = quizLabel.slice(0, 52) + '…';

  /* ── 3. Construire les items selon le contexte ── */
  var items = [{ href: root + 'index.html', label: '🏠 BobMed' }];

  var inD2T = path.match(/\/d2\/(t\d+)\//i);
  var inAnnales = path.includes('/annales/');
  var inMicro = path.includes('/microbiologie/');
  var inExo = path.includes('/exercices/');
  var inNum = path.includes('/numerique/');

  if (inD2T) {
    var tNum = inD2T[1].toUpperCase(); /* T1, T2… */
    var tLabels = {
      T1: 'T1 — Cardio · Pneumo · Mal. transmissibles',
      T2: 'T2 — Hépato-Gastro · Neuro · Psy',
      T3: 'T3 — Dermato · Méd. Interne · Nephro/Uro',
      T4: 'T4 — ORL/Ophtalmo · Rhumato · Endocrino · LCA'
    };
    items.push({ href: root + 'index.html#d2', label: 'D2' });
    items.push({ href: root + 'd2/' + inD2T[1] + '/index.html', label: tLabels[tNum] || tNum });
  } else if (inAnnales) {
    items.push({ href: root + 'annales/index.html', label: 'D1 — Annales' });
  } else if (inMicro) {
    items.push({ href: root + 'microbiologie/index.html', label: 'Microbiologie UE3' });
  } else if (inExo) {
    items.push({ href: root + 'exercices/index.html', label: 'Exercices ED' });
  } else if (inNum) {
    items.push({ href: root + 'index.html', label: 'BobMed' }); /* déjà présent, on skip */
  }

  /* Dernière miette = page courante (non cliquable) */
  items.push({ href: null, label: quizLabel });

  /* ── 4. Supprimer doublon éventuel BobMed ── */
  items = items.filter(function (it, idx) {
    return !(idx > 0 && it.href && it.href === items[0].href);
  });

  /* ── 5. Construire le DOM ── */
  var nav = document.createElement('nav');
  nav.className = 'breadcrumb';
  nav.setAttribute('aria-label', "Fil d'Ariane");

  items.forEach(function (item, idx) {
    if (idx > 0) {
      var sep = document.createElement('span');
      sep.className = 'sep';
      sep.setAttribute('aria-hidden', 'true');
      sep.textContent = '›';
      nav.appendChild(sep);
    }
    if (item.href) {
      var a = document.createElement('a');
      a.href = item.href;
      a.textContent = item.label;
      nav.appendChild(a);
    } else {
      var span = document.createElement('span');
      span.className = 'current';
      span.setAttribute('aria-current', 'page');
      span.textContent = item.label;
      nav.appendChild(span);
    }
  });

  /* ── 6. Insérer avant le premier <h1> ou en haut du <body> ── */
  function insert() {
    /* Chercher le conteneur principal */
    var wrap = document.querySelector('.wrap') || document.body;
    var h1 = wrap.querySelector('h1');
    /* Sur les quiz, le header sticky est en dehors de .wrap — insérer dans .wrap avant h1 */
    if (h1 && h1.closest('.wrap') === wrap) {
      wrap.insertBefore(nav, h1);
    } else if (h1) {
      /* h1 dans le header sticky : insérer en haut de .wrap */
      wrap.insertBefore(nav, wrap.firstChild);
    } else {
      wrap.insertBefore(nav, wrap.firstChild);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', insert);
  } else {
    insert();
  }
})();
