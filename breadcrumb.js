/**
 * breadcrumb.js — Fil d'Ariane universel BobMed
 * Ajouter avant </body> :
 *   <script src="../breadcrumb.js"></script>   (annales/, microbiologie/, exercices/, numerique/)
 *   <script src="../../breadcrumb.js"></script> (d2/tN/)
 *
 * Sur les portails (index.html) qui ont déjà un fil statique,
 * le script injecte uniquement le CSS et ne crée pas de doublon.
 */
(function () {
  /* ── 1. CSS unifié — injecté une seule fois ── */
  if (!document.querySelector('style[data-bc]')) {
    var s = document.createElement('style');
    s.setAttribute('data-bc', '1');
    s.textContent =
      '.breadcrumb{display:flex;align-items:center;flex-wrap:wrap;gap:4px;' +
      'font-size:12.5px;color:var(--mut,#5b6b73);margin-bottom:12px;' +
      'padding:5px 10px;background:var(--card,#fff);' +
      'border:1px solid var(--line,#dfe4e2);border-radius:8px}' +
      '.breadcrumb a{color:var(--acc,#4f46e5);text-decoration:none;font-weight:500}' +
      '.breadcrumb a:hover{text-decoration:underline}' +
      '.breadcrumb .sep{opacity:.4;font-size:11px;margin:0 2px}' +
      '.breadcrumb .current{color:var(--ink,#132025);font-style:italic}' +
      'html.dark .breadcrumb{background:var(--card,#1a1d27);border-color:var(--line,#2d3748)}';
    document.head.appendChild(s);
  }

  /* ── 2. Fil statique déjà présent → CSS seulement, pas de doublon ── */
  if (document.querySelector('.breadcrumb')) return;

  /* ── 3. Détecter le contexte depuis l'URL ── */
  var path = window.location.pathname;

  var inD2T     = path.match(/\/d2\/(t\d+)\//i);
  var inAnnales = path.includes('/annales/');
  var inMicro   = path.includes('/microbiologie/');
  var inExo     = path.includes('/exercices/');
  var inNum     = path.includes('/numerique/');

  /* Racine du site : 2 niveaux pour d2/tN, 1 niveau pour les autres sections */
  var root = inD2T ? '../../' : '../';

  /* ── 4. Label de la page courante (depuis le h1, plus fiable que le title) ── */
  var h1El = document.querySelector('h1');
  var rawTitle = h1El ? h1El.textContent.trim() : document.title;

  /* Extraire l'identifiant utile :
     - "UE 7.1 — Pneumologie · Session normale (mars 2023)" → "UE 7.1 — Pneumologie"
     - "UE 1.1 Biomédecine quantitative — Annale 2022-2023" → "UE 1.1 Biomédecine quantitative"
  */
  var labelParts = rawTitle.split(' · ')[0].split(' — ');
  var quizLabel;
  if (labelParts[0].trim().length <= 10 && labelParts[1]) {
    /* Préfixe court ("UE 7.1") : ajouter la spécialité */
    quizLabel = labelParts[0] + ' — ' + labelParts[1].split(' · ')[0];
  } else {
    /* Préfixe long ("UE 1.1 Biomédecine quantitative") : s'arrêter là */
    quizLabel = labelParts[0];
  }
  if (quizLabel.length > 55) quizLabel = quizLabel.slice(0, 52) + '…';

  /* ── 5. Construire les segments du fil ── */
  var items = [{ href: root + 'index.html', label: 'BobMed' }];

  var tLabels = {
    T1: 'T1 — Cardio · Pneumo · MT',
    T2: 'T2 — Hépato-Gastro · Neuro · Psy',
    T3: 'T3 — Dermato · Méd. Interne · Nephro',
    T4: 'T4 — ORL · Rhumato · Endocrino · LCA'
  };

  if (inD2T) {
    var tNum = inD2T[1].toUpperCase();
    items.push({ href: root + 'index.html#d2', label: 'D2' });
    items.push({ href: root + 'd2/' + inD2T[1] + '/index.html', label: tLabels[tNum] || tNum });
  } else if (inAnnales) {
    items.push({ href: root + 'index.html#d1', label: 'D1' });
    items.push({ href: root + 'annales/index.html', label: 'Annales' });
  } else if (inMicro) {
    items.push({ href: root + 'index.html#d1', label: 'D1' });
    items.push({ href: root + 'microbiologie/index.html', label: 'Microbiologie UE3' });
  } else if (inExo) {
    items.push({ href: root + 'index.html#d1', label: 'D1' });
    items.push({ href: root + 'exercices/index.html', label: 'Exercices ED' });
  } else if (inNum) {
    items.push({ href: root + 'index.html#d1', label: 'D1' });
  }

  items.push({ href: null, label: quizLabel });

  /* ── 6. Construire le <nav> ── */
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
      /* Scroll vers l'ancre si on reste sur la même page (index.html#d1 / #d2) */
      a.addEventListener('click', function (e) {
        var href = this.getAttribute('href');
        var hashIdx = href.indexOf('#');
        if (hashIdx === -1) return;
        var anchor = href.slice(hashIdx + 1);
        var resolvedPath = new URL(href, window.location.href).pathname;
        if (resolvedPath === window.location.pathname) {
          e.preventDefault();
          var target = document.getElementById(anchor);
          if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          history.pushState(null, '', '#' + anchor);
        }
      });
      nav.appendChild(a);
    } else {
      var span = document.createElement('span');
      span.className = 'current';
      span.setAttribute('aria-current', 'page');
      span.textContent = item.label;
      nav.appendChild(span);
    }
  });

  /* ── 7. Insérer en haut du header (.hwrap prioritaire), sinon avant h1 ── */
  function insert() {
    var header = document.querySelector('header .hwrap') || document.querySelector('header');
    if (header) {
      header.insertBefore(nav, header.firstChild);
      return;
    }
    var wrap = document.querySelector('.wrap') || document.body;
    var h1   = wrap.querySelector('h1');
    if (h1 && h1.closest && h1.closest('.wrap') === wrap) {
      wrap.insertBefore(nav, h1);
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
