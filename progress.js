/**
 * progress.js — Suivi de progression local BobMed
 *
 * Suivi 100 % local (localStorage, clé `bobmed:progress:v1`) : aucune donnée
 * ne quitte le navigateur, aucun compte, aucun serveur — même modèle que le
 * mode sombre. Le script détecte seul son contexte :
 *
 *   · Page quiz (header .scorebar + .q) : pastille « ✓ Terminé N× » dans la
 *     scorebar. La complétion est détectée automatiquement quand toutes les
 *     questions sont validées/révélées (#s-done plein) — sauf via « Tout
 *     révéler », qui ne compte pas comme une vraie passe. Un clic sur la
 *     pastille permet de corriger le nombre de passes à la main (saisie
 *     directe) si le tracking a été mauvais, ou de marquer une passe faite
 *     ailleurs.
 *   · Portail (cartes a.qz / a.card hors fiches) : badge discret par carte
 *     « ✓ Fait N× · dernier score · le JJ/MM/AAAA ».
 *   · Accueil (.year-block) : résumé global + boutons Exporter / Importer
 *     (fichier .json) pour transférer la progression entre navigateurs.
 *
 * À charger avant </body> sur les quiz, les portails et l'accueil :
 *   <script src="progress.js"></script>            (racine)
 *   <script src="../../progress.js"></script>      (d1/tN/, d2/tN/)
 *   <script src="../../../progress.js"></script>   (sous-portails)
 *
 * Aucune dépendance, injecte son propre CSS une seule fois, ne fait rien si
 * localStorage est indisponible (navigation privée stricte).
 */
(function () {
  if (window.__bobmedProgress) return;   /* garde-fou : pas de double init */
  window.__bobmedProgress = true;

  /* ── Stockage ───────────────────────────────────────────────────────── */
  var KEY = 'bobmed:progress:v1';

  function loadData() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return { v: 1, quizzes: {} };
      var d = JSON.parse(raw);
      if (!d || d.v !== 1 || typeof d.quizzes !== 'object' || !d.quizzes) return { v: 1, quizzes: {} };
      return d;
    } catch (e) { return null; }         /* localStorage bloqué → pas de suivi */
  }
  function saveData(d) { try { localStorage.setItem(KEY, JSON.stringify(d)); } catch (e) {} }

  var data = loadData();
  if (data === null) return;

  /* ── Identifiants : chemin relatif à la racine du site ──────────────────
     La racine se déduit de l'URL de CE script (progress.js vit à la racine
     du dépôt) : l'identifiant d'un quiz est donc stable quel que soit
     l'hébergement (GitHub Pages avec préfixe /bobmed/, serveur local, …)
     et identique entre la page quiz et la carte du portail. */
  var _cs = document.currentScript;
  var ROOT = _cs && _cs.src ? safeDecode(_cs.src).replace(/progress\.js(\?.*)?$/, '') : '';

  function safeDecode(u) { try { return decodeURI(u); } catch (e) { return u; } }
  function relId(url) {
    try {
      var abs = safeDecode(new URL(url, location.href).href).split('#')[0].split('?')[0];
      return ROOT && abs.indexOf(ROOT) === 0 ? abs.slice(ROOT.length) : abs;
    } catch (e) { return String(url); }
  }

  /* ── Helpers de formatage (conventions du site : virgule décimale) ───── */
  function fmtPts(p) { return (Math.round(p * 100) / 100).toString().replace('.', ','); }
  function fmtDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
    return m ? m[3] + '/' + m[2] + '/' + m[1] : (iso || '');
  }
  function today() {
    var d = new Date(), p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }

  /* ── CSS (une seule injection, variables du thème + repli clair) ─────── */
  function injectCSS() {
    if (document.getElementById('bmp-css')) return;
    var s = document.createElement('style');
    s.id = 'bmp-css';
    s.textContent =
      '.bmp-badge{display:block;font-size:12px;color:var(--mut,#5b6b73);margin-top:6px;line-height:1.5}' +
      '.bmp-badge .ck{color:var(--vrai,#15803d);font-weight:600}' +
      '.bmp-dash{background:var(--card,#fff);border:1px solid var(--line,#dfe4e2);border-left:4px solid var(--vrai,#15803d);border-radius:12px;padding:11px 16px;margin:26px 0 0;font-size:14px;color:var(--mut,#5b6b73)}' +
      '.bmp-dash b{color:var(--ink,#132025)}' +
      '.bmp-tools{display:inline-block;margin-left:10px;white-space:nowrap}' +
      '.bmp-btn{cursor:pointer;border:1px solid var(--line,#dfe4e2);background:var(--card,#fff);color:inherit;border-radius:7px;font:inherit;font-size:12px;font-weight:600;padding:1px 8px}' +
      '.bmp-btn:hover{border-color:var(--vrai,#15803d);color:var(--vrai,#15803d)}' +
      '.bmp-flash{background:var(--vraibg,#eaf7ef)!important;border-color:var(--vrai,#15803d)!important;transition:background .3s,border-color .3s}';
    document.head.appendChild(s);
  }

  /* ── Page quiz ────────────────────────────────────────────────────────── */
  function initQuiz() {
    var scorebar = document.querySelector('header .scorebar');
    if (!scorebar || !document.querySelector('.q')) return false;
    injectCSS();

    var id = relId(location.href);
    var h1 = document.querySelector('h1');

    function ensure() {
      if (!data.quizzes[id]) data.quizzes[id] = { count: 0 };
      if (h1) data.quizzes[id].title = h1.textContent.trim();
      return data.quizzes[id];
    }

    /* Pastille dans la scorebar : un seul bouton « ✓ Terminé N× ».
       Un clic ouvre une saisie directe du nombre de passes (correction
       manuelle ou marquage d'une passe faite ailleurs). */
    var pill = document.createElement('span');
    pill.className = 'pill bmp-pill';
    pill.innerHTML =
      '<button type="button" class="bmp-btn bmp-mark" ' +
      'title="Nombre de fois où cette annale a été terminée — cliquer pour corriger">' +
      '✓ Terminé <b class="bmp-n">0×</b></button>';
    scorebar.appendChild(pill);
    var nEl = pill.querySelector('.bmp-n');
    function refresh() {
      var r = data.quizzes[id];
      nEl.textContent = (r && r.count > 0 ? r.count : 0) + '×';
    }
    refresh();

    /* Lecture de l'état affiché par le moteur du quiz (aucune modification
       du JS embarqué : on observe #s-done / #s-ok, déjà tenus à jour par
       updateScore() dans chaque fichier). */
    function fullDone() {
      var sd = document.getElementById('s-done');
      var m = sd && /(\d+)\s*\/\s*(\d+)/.exec(sd.textContent);
      return !!(m && +m[2] > 0 && m[1] === m[2]);
    }
    function currentScore() {
      var so = document.getElementById('s-ok');
      var m = so && /([\d.,]+)\s*\/\s*(\d+)/.exec(so.textContent);
      if (!m) return null;
      return { pts: parseFloat(m[1].replace(',', '.')), max: parseInt(m[2], 10) };
    }

    var counted = false, skipAuto = false;
    function complete() {
      if (counted) return;
      counted = true;                     /* une seule passe par chargement */
      var r = ensure();
      r.count = (r.count || 0) + 1;
      r.lastDone = today();
      if (fullDone()) {                   /* score mémorisé si la passe est complète */
        var sc = currentScore();
        if (sc) {
          r.lastScore = sc;
          if (r.bestPts === undefined || sc.pts > r.bestPts) r.bestPts = sc.pts;
        }
      }
      saveData(data);
      refresh();
      pill.classList.add('bmp-flash');
      setTimeout(function () { pill.classList.remove('bmp-flash'); }, 1600);
    }

    pill.querySelector('.bmp-mark').addEventListener('click', function () {
      var cur = data.quizzes[id] ? (data.quizzes[id].count || 0) : 0;
      var v = prompt('Nombre de fois où cette annale a été terminée :', cur);
      if (v === null) return;
      var n = parseInt(v, 10);
      if (isNaN(n) || n < 0) return;
      var r = ensure();
      if (n > (r.count || 0)) r.lastDone = today();   /* on l'augmente = on vient de la faire */
      r.count = n;
      saveData(data);
      refresh();
    });

    /* « Tout révéler » n'est pas une vraie passe : on n'auto-compte pas. */
    var ra = document.getElementById('revealall');
    if (ra) ra.addEventListener('click', function () { skipAuto = true; }, true);

    var sd = document.getElementById('s-done');
    if (sd) {
      var check = function () { if (!skipAuto && !counted && fullDone()) complete(); };
      new MutationObserver(check).observe(sd, { childList: true, characterData: true, subtree: true });
      check();
    }
    return true;
  }

  /* ── Portail (cartes de quiz) ─────────────────────────────────────────── */
  function quizCards() {
    return [].slice.call(document.querySelectorAll('a.qz[href], a.card[href]')).filter(function (a) {
      if (a.classList.contains('fiche')) return false;
      var h = safeDecode(a.getAttribute('href') || '');
      return /(^|\/)Quiz_[^\/]+\.html$/.test(h);
    });
  }

  function initPortal() {
    var cards = quizCards();
    if (!cards.length) return false;
    injectCSS();

    /* Badge discret par carte déjà faite — rien d'autre : pas de tableau
       de bord de trimestre (le nombre d'annales tentées n'aide pas à
       réviser), pas de badge sur les cartes jamais faites. */
    cards.forEach(function (a) {
      var r = data.quizzes[relId(a.getAttribute('href'))];
      if (!r || !(r.count > 0)) return;
      var txt = ' Fait ' + r.count + '×';
      if (r.lastScore) txt += ' · ' + fmtPts(r.lastScore.pts) + '/' + r.lastScore.max;
      if (r.lastDone) txt += ' · le ' + fmtDate(r.lastDone);
      var b = document.createElement('span');
      b.className = 'bmp-badge';
      b.innerHTML = '<span class="ck">✓</span>' + txt;
      a.appendChild(b);
    });
    return true;
  }

  /* ── Accueil : résumé global + Exporter / Importer ────────────────────── */
  function initHome() {
    if (!document.querySelector('.year-block')) return false;
    injectCSS();

    var ids = Object.keys(data.quizzes).filter(function (k) { return data.quizzes[k].count > 0; });
    var last = '';
    ids.forEach(function (k) { var d0 = data.quizzes[k].lastDone || ''; if (d0 > last) last = d0; });

    var box = document.createElement('div');
    box.className = 'bmp-dash bmp-home';
    var t = '📊 Progression locale : <b>' + ids.length + '</b> quiz fait' + (ids.length > 1 ? 's' : '');
    if (last) t += ' · dernière session le <b>' + fmtDate(last) + '</b>';
    t += '<span class="bmp-tools">' +
         '<button type="button" class="bmp-btn" id="bmp-export" title="Télécharger la progression de ce navigateur (.json)">Exporter</button> ' +
         '<button type="button" class="bmp-btn" id="bmp-import" title="Restaurer une progression exportée (.json)">Importer</button>' +
         '</span>';
    box.innerHTML = t;
    var footer = document.querySelector('footer');
    if (footer) footer.parentNode.insertBefore(box, footer);
    else document.body.appendChild(box);

    box.querySelector('#bmp-export').addEventListener('click', function () {
      var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'bobmed-progression-' + today() + '.json';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
    });

    var inp = document.createElement('input');
    inp.type = 'file'; inp.accept = '.json,application/json'; inp.style.display = 'none';
    document.body.appendChild(inp);
    box.querySelector('#bmp-import').addEventListener('click', function () { inp.value = ''; inp.click(); });
    inp.addEventListener('change', function () {
      var f = inp.files && inp.files[0];
      if (!f) return;
      var rd = new FileReader();
      rd.onload = function () {
        try {
          var d = JSON.parse(rd.result);
          if (!d || d.v !== 1 || typeof d.quizzes !== 'object' || !d.quizzes) throw new Error('format');
          var n = Object.keys(d.quizzes).length;
          if (!confirm('Remplacer la progression locale de ce navigateur par celle du fichier (' + n + ' quiz) ?')) return;
          saveData(d);
          location.reload();
        } catch (e) {
          alert('Fichier de progression invalide (attendu : export BobMed .json).');
        }
      };
      rd.readAsText(f);
    });
    return true;
  }

  /* ── Dispatch selon le contexte de la page ────────────────────────────── */
  if (!initQuiz() && !initPortal()) initHome();
})();
