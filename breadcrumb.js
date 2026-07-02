/**
 * breadcrumb.js — Fil d'Ariane universel BobMed
 * Ajouter avant </body> :
 *   <script src="../breadcrumb.js"></script>   (annales/, microbiologie/, exercices/, numerique/)
 *   <script src="../../breadcrumb.js"></script> (d2/tN/)
 */
(function () {
  if (!document.querySelector('style[data-bc]')) {
    var s = document.createElement('style');
    s.setAttribute('data-bc', '1');
    s.textContent =
      '.breadcrumb{display:flex;align-items:center;flex-wrap:wrap;gap:3px;' +
      'font-size:12px;color:var(--mut,#8a9baa);margin-bottom:6px;padding:0;' +
      'background:none;border:none;border-radius:0}' +
      '.breadcrumb a{color:var(--mut,#8a9baa);text-decoration:none}' +
      '.breadcrumb a:hover{text-decoration:underline;color:var(--acc,#4f46e5)}' +
      '.breadcrumb .sep{opacity:.5;font-size:11px;margin:0 1px}' +
      '.breadcrumb .current{color:var(--mut,#8a9baa);font-style:italic}';
    document.head.appendChild(s);
  }

  var path  = window.location.pathname;
  var parts = path.split('/').filter(Boolean);
  var depth = parts.length - 1;
  var root  = depth > 0 ? '../'.repeat(depth) : './';

  var pageTitle = document.title || 'Quiz';
  var quizLabel = pageTitle.split(' \u2014 ')[0].split(' | ')[0];
  if (quizLabel.length > 55) quizLabel = quizLabel.slice(0, 52) + '\u2026';

  var items = [{ href: root + 'index.html', label: 'BobMed' }];

  var inD2T     = path.match(/\/d2\/(t\d+)\//i);
  var inAnnales = path.includes('/annales/');
  var inMicro   = path.includes('/microbiologie/');
  var inExo     = path.includes('/exercices/');
  var inNum     = path.includes('/numerique/');

  if (inD2T) {
    var tNum = inD2T[1].toUpperCase();
    var tLabels = {
      T1: 'T1 \u2014 Cardio \u00b7 Pneumo \u00b7 MT',
      T2: 'T2 \u2014 H\u00e9pato-Gastro \u00b7 Neuro \u00b7 Psy',
      T3: 'T3 \u2014 Dermato \u00b7 M\u00e9d. Interne \u00b7 Nephro',
      T4: 'T4 \u2014 ORL \u00b7 Rhumato \u00b7 Endocrino \u00b7 LCA'
    };
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

  var nav = document.createElement('nav');
  nav.className = 'breadcrumb';
  nav.setAttribute('aria-label', "Fil d'Ariane");

  items.forEach(function (item, idx) {
    if (idx > 0) {
      var sep = document.createElement('span');
      sep.className = 'sep';
      sep.setAttribute('aria-hidden', 'true');
      sep.textContent = '\u203a';
      nav.appendChild(sep);
    }
    if (item.href) {
      var a = document.createElement('a');
      a.href = item.href;
      a.textContent = item.label;
      // Gestion du scroll vers l'ancre sur la même page (index.html#d1 / #d2)
      a.addEventListener('click', function (e) {
        var href = this.getAttribute('href');
        var hashIdx = href.indexOf('#');
        if (hashIdx === -1) return;
        var anchor = href.slice(hashIdx + 1);
        var hrefPath = href.slice(0, hashIdx);
        // Vérifier si on pointe vers index.html de la racine du site
        var currentPath = window.location.pathname;
        var resolvedPath = new URL(href, window.location.href).pathname;
        if (resolvedPath === currentPath) {
          // Même page : scroll direct sans rechargement
          e.preventDefault();
          var target = document.getElementById(anchor);
          if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          history.pushState(null, '', '#' + anchor);
        }
        // Sinon navigation normale vers index.html#d1/d2 :
        // le script de scroll dans index.html prendra le relais
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

  /* Insérer en haut du header sticky, sinon avant h1 */
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
