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
