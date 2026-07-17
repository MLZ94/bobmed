/**
 * dynamic-header.js — Header dynamique BobMed
 *
 * Le header sticky se masque au défilement vers le bas et réapparaît au
 * défilement vers le haut (ou près du sommet de la page) → davantage de
 * surface de lecture, tout particulièrement sur l'interface mobile où la
 * barre de titre + scorebar occupe une part importante de l'écran.
 *
 * À charger avant </body> sur toute page possédant un <header> sticky :
 *   <script src="../dynamic-header.js"></script>        (annales/, microbiologie/, …)
 *   <script src="../../dynamic-header.js"></script>     (d2/tN/)
 *   <script src="../../../dynamic-header.js"></script>  (d2/tN/entrainement/)
 *
 * Aucune dépendance, injecte son propre CSS une seule fois, et ne fait rien
 * sur les pages sans <header> (accueil, portails de trimestre).
 */
(function () {
  var header = document.querySelector('header');
  if (!header) return; /* accueil / portails : pas de header sticky à animer */

  /* ── CSS injecté une seule fois ── */
  if (!document.querySelector('style[data-dh]')) {
    var st = document.createElement('style');
    st.setAttribute('data-dh', '1');
    st.textContent =
      'header{will-change:transform;' +
      'transition:transform .28s cubic-bezier(.4,0,.2,1),box-shadow .2s ease}' +
      'header.dh-up{transform:translateY(-100%)}' +
      'header.dh-scrolled{box-shadow:0 4px 16px rgba(16,24,40,.12)}' +
      '@media (prefers-reduced-motion:reduce){' +
      'header{transition:none}header.dh-up{transform:none}}';
    document.head.appendChild(st);
  }

  /* Respect de la préférence système : pas de masquage automatique, on garde
     le header sticky classique (le CSS ci-dessus neutralise déjà l'animation). */
  var reduce = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion:reduce)').matches;
  if (reduce) return;

  var lastY = window.pageYOffset || document.documentElement.scrollTop || 0;
  var ticking = false;
  var DELTA = 6; /* seuil anti-tremblement (px) */

  function update() {
    ticking = false;
    var y = window.pageYOffset || document.documentElement.scrollTop || 0;
    var h = header.offsetHeight || 0;

    /* Ombre portée dès que l'on quitte le tout début de la page */
    header.classList.toggle('dh-scrolled', y > 4);

    /* Toujours visible tant que le header n'a pas totalement défilé */
    if (y <= h) {
      header.classList.remove('dh-up');
      lastY = y;
      return;
    }

    /* Ignorer les micro-variations pour éviter le clignotement */
    if (Math.abs(y - lastY) < DELTA) return;

    if (y > lastY) header.classList.add('dh-up');    /* vers le bas → masquer */
    else header.classList.remove('dh-up');           /* vers le haut → révéler */

    lastY = y;
  }

  window.addEventListener('scroll', function () {
    if (!ticking) {
      window.requestAnimationFrame(update);
      ticking = true;
    }
  }, { passive: true });

  /* Le header doit rester visible quand une ancre/bouton redonne la main au
     sommet du contenu (ex. « Recommencer », navigation vers une question). */
  update();
})();

/**
 * ── Compaction mobile du header des annales (≤ 600 px) ──────────────────────
 *
 * Le header sticky des annales empile trois blocs qui débordent sur mobile :
 * le titre <h1> (souvent 2-3 lignes), le détail des questions .sub, et une
 * .scorebar chargée de boutons (Tout révéler, Recommencer, Minuteur, Terminé).
 * Sur un petit écran, cet en-tête sticky mange durablement l'espace de lecture.
 *
 * Cette seconde passe, indépendante de l'animation ci-dessus (elle s'applique
 * même en prefers-reduced-motion), compacte le header uniquement sous 600 px :
 *   1. <h1> tronqué sur une ligne + chevron dépliant/repliant le détail .sub
 *      (masqué par défaut sur mobile) ;
 *   2. les boutons d'action (Tout révéler, Recommencer, ✓ Terminé) repliés
 *      dans un menu « ⋯ » ; le Minuteur reste dans la barre en icône seule.
 * Sur desktop (> 600 px) rien ne change : les éléments restent dans la barre,
 * le chevron et le menu sont masqués. Ne fait rien sur une page sans
 * « header .scorebar » (accueil, portails, fiches de cours).
 *
 * Toute la logique vit ici (fichier global chargé par toutes les annales) :
 * aucun quiz HTML n'est modifié. Le CSS est injecté en fin de <head>, donc il
 * prime sur le <style> inline des quiz à spécificité égale.
 */
(function () {
  if (window.__bobmedHeaderCompact) return;   /* garde-fou : pas de double init */
  window.__bobmedHeaderCompact = true;

  var header = document.querySelector('header');
  if (!header) return;                         /* accueil / portails : rien à compacter */
  var scorebar = header.querySelector('.scorebar');
  if (!scorebar) return;                       /* fiches (sans barre de score) : idem */

  var MQ = '(max-width:600px)';

  var ICON_CHEVRON =
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" ' +
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M6 9l6 6 6-6"/></svg>';
  var ICON_DOTS =
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">' +
    '<circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/></svg>';

  /* ── 1. CSS injecté une seule fois (en fin de <head> → prime sur l'inline) ── */
  if (!document.querySelector('style[data-dhm]')) {
    var st = document.createElement('style');
    st.setAttribute('data-dhm', '1');
    st.textContent = [
      /* chevron du détail .sub : masqué hors mobile */
      'header .dhm-sub-toggle{display:none;flex:none;align-items:center;justify-content:center;',
      'width:27px;height:27px;padding:0;border:1px solid var(--line,#dfe4e2);border-radius:8px;',
      'background:var(--card,#fff);color:var(--mut,#5b6b73);cursor:pointer}',
      'header .dhm-sub-toggle svg{transition:transform .2s ease}',
      'header.dhm-sub-open .dhm-sub-toggle svg{transform:rotate(180deg)}',
      /* menu ⋯ : masqué hors mobile (les items restent alors dans la barre) */
      'header .dhm-menu{display:none;position:relative}',
      'header .dhm-menu-btn{line-height:0;padding:5px 9px}',
      'header .dhm-menu-pop{position:absolute;top:calc(100% + 8px);right:0;z-index:20;min-width:190px;',
      'background:var(--card,#fff);border:1px solid var(--line,#dfe4e2);border-radius:12px;',
      'box-shadow:0 8px 28px rgba(16,24,40,.16);padding:8px;display:flex;flex-direction:column;gap:6px}',
      'header .dhm-menu-pop[hidden]{display:none}',
      /* Anti « bouton dans un bouton » : une .pill à bordure qui enveloppe un
         bouton (Tout révéler, Recommencer, Minuteur, ✓ Terminé) faisait
         apparaître deux cadres imbriqués. On neutralise la pill englobante :
         seul le bouton reste visible comme unique contrôle. Les pills de
         statut (Validées, Score), sans bouton, gardent leur allure de chip. */
      'header .scorebar .pill:has(button){padding:0;border:0;background:none}',
      /* dans le menu, chaque item d'action occupe une ligne pleine, texte centré */
      'header .dhm-menu-pop .pill{display:flex;margin:0;padding:0;border:0;background:none;border-radius:0}',
      'header .dhm-menu-pop .pill>button{flex:1;width:100%;text-align:center;padding:9px 12px}',
      'html.dark header .dhm-sub-toggle,html.dark header .dhm-menu-pop{',
      'background:var(--card,#1a1d27);border-color:var(--line,#2d3748)}',
      'html.dark header .dhm-sub-toggle{color:var(--mut,#8a9baa)}',
      /* ── passage en mode compact sous 600 px ── */
      '@media ' + MQ + '{',
      'header{padding:10px 14px}',
      'header h1{font-size:17px}',
      'header h1.dhm-h1{display:flex;align-items:center;gap:8px}',
      'header h1 .dhm-txt{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      /* détail déplié : le titre complet se déroule (plus d'ellipsis), le chevron
         reste calé en haut face au titre devenu multiligne */
      'header.dhm-sub-open h1.dhm-h1{align-items:flex-start}',
      'header.dhm-sub-open h1 .dhm-txt{overflow:visible;text-overflow:clip;white-space:normal}',
      'header .dhm-sub-toggle{display:inline-flex}',
      'header .sub{display:none}',
      'header.dhm-sub-open .sub{display:block;margin-top:8px}',
      'header .scorebar{gap:6px;margin-top:8px;font-size:13px}',
      'header .scorebar>.pill{padding:3px 10px}',
      'header .dhm-menu{display:inline-flex}',
      /* fil d'Ariane sur une seule ligne : le dernier segment (titre de la page)
         fait doublon avec le <h1> juste en dessous → masqué (avec son séparateur),
         le chemin de navigation parent restant intact et cliquable */
      'header .breadcrumb{flex-wrap:nowrap;overflow:hidden;margin-bottom:7px}',
      'header .breadcrumb a{white-space:nowrap}',
      'header .breadcrumb .current,header .breadcrumb .sep:nth-last-child(2){display:none}',
      /* Minuteur réduit à sa seule icône (le libellé « Minuteur » est masqué) */
      'header #tm-trigger{font-size:0;gap:0;padding:5px 9px}',
      '}'
    ].join('');
    document.head.appendChild(st);
  }

  /* ── 2. Construction (différée à DOMContentLoaded pour que timer.js et
   *       progress.js aient déjà injecté leurs pastilles dans la scorebar). ── */
  function build() {
    /* (a) Chevron dépliant le détail .sub */
    var h1 = header.querySelector('h1');
    var sub = header.querySelector('.sub');
    if (h1 && sub && !h1.querySelector('.dhm-sub-toggle')) {
      h1.classList.add('dhm-h1');
      var txt = document.createElement('span');
      txt.className = 'dhm-txt';
      while (h1.firstChild) txt.appendChild(h1.firstChild);
      h1.appendChild(txt);
      var chev = document.createElement('button');
      chev.type = 'button';
      chev.className = 'dhm-sub-toggle';
      chev.setAttribute('aria-expanded', 'false');
      chev.setAttribute('aria-label', 'Afficher le détail des questions');
      chev.innerHTML = ICON_CHEVRON;
      chev.addEventListener('click', function () {
        var open = header.classList.toggle('dhm-sub-open');
        chev.setAttribute('aria-expanded', open ? 'true' : 'false');
        chev.setAttribute('aria-label',
          open ? 'Masquer le détail des questions' : 'Afficher le détail des questions');
      });
      h1.appendChild(chev);
    }

    /* (b) Menu ⋯ regroupant les boutons d'action */
    var menu = document.createElement('span');
    menu.className = 'dhm-menu';
    menu.innerHTML =
      '<button type="button" class="dhm-menu-btn" aria-haspopup="true" aria-expanded="false" ' +
      'aria-label="Plus d\'actions">' + ICON_DOTS + '</button>' +
      '<div class="dhm-menu-pop" hidden role="menu"></div>';
    scorebar.appendChild(menu);
    var menuBtn = menu.querySelector('.dhm-menu-btn');
    var menuPop = menu.querySelector('.dhm-menu-pop');

    /* Éléments d'action à replier : « Tout révéler », « Recommencer » (inline
       dans chaque quiz) et « ✓ Terminé » (injecté par progress.js). Le Minuteur
       reste dans la barre (icône) pour garder son popover ancré simplement. */
    function actionItems() {
      var out = [];
      var rev = scorebar.querySelector('#revealall'); if (rev) out.push(rev.closest('.pill'));
      var res = scorebar.querySelector('#reset');     if (res) out.push(res.closest('.pill'));
      var prg = scorebar.querySelector('.bmp-pill');   if (prg) out.push(prg);
      return out.filter(function (x) { return x && x !== menu; });
    }

    var folded = false;
    function toMenu() {
      if (folded) return;
      folded = true;
      actionItems().forEach(function (el) {
        var ph = document.createElement('span');     /* repère la position d'origine */
        ph.className = 'dhm-ph';
        ph.hidden = true;
        el.parentNode.insertBefore(ph, el);
        el._dhmPh = ph;
        menuPop.appendChild(el);
      });
    }
    function toBar() {
      if (!folded) return;
      folded = false;
      [].slice.call(menuPop.children).forEach(function (el) {
        var ph = el._dhmPh;
        if (ph && ph.parentNode) { ph.parentNode.insertBefore(el, ph); ph.remove(); }
        el._dhmPh = null;
      });
      closeMenu();
    }

    function openMenu() { menuPop.hidden = false; menuBtn.setAttribute('aria-expanded', 'true'); }
    function closeMenu() { menuPop.hidden = true; menuBtn.setAttribute('aria-expanded', 'false'); }
    menuBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      menuPop.hidden ? openMenu() : closeMenu();
    });
    menuPop.addEventListener('click', function (e) { if (e.target.closest('button')) closeMenu(); });
    document.addEventListener('click', function (e) {
      if (!menuPop.hidden && !menu.contains(e.target)) closeMenu();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !menuPop.hidden) closeMenu();
    });

    /* (c) Reflow selon la largeur : replié sous 600 px, restauré au-delà. */
    var mql = window.matchMedia(MQ);
    function apply() { mql.matches ? toMenu() : toBar(); }
    apply();
    if (mql.addEventListener) mql.addEventListener('change', apply);
    else if (mql.addListener) mql.addListener(apply);   /* Safari ancien */
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', build, { once: true });
  } else {
    build();
  }
})();
