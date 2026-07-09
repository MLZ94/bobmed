/**
 * timer.js — Minuteur d'examen réglable BobMed
 *
 * Ajoute, dans le header sticky des annales (à côté de « Tout révéler » et
 * « Recommencer »), un bouton « Minuteur » qui laisse l'étudiant choisir une
 * durée, puis affiche dans le header un encadré avec le temps restant — dans
 * l'esprit du minuteur d'examen Uness. Un bouton masquer/démasquer, à côté de
 * l'encadré, permet de cacher le temps restant (pour réviser sans la pression
 * du chrono) et de le réafficher à la demande.
 *
 * À charger avant </body> sur toute page annale possédant un <header> avec
 * une .scorebar :
 *   <script src="../timer.js"></script>        (annales/, …)
 *   <script src="../../timer.js"></script>     (d2/tN/)
 *
 * Aucune dépendance, injecte son propre CSS une seule fois, et ne fait rien
 * sur les pages sans .scorebar (accueil, portails de trimestre, fiches).
 */
(function () {
  if (window.__bobmedTimer) return;      /* garde-fou : pas de double init */
  window.__bobmedTimer = true;

  var scorebar = document.querySelector('header .scorebar');
  if (!scorebar) return;                 /* page sans barre de score : rien à faire */

  /* ── Icônes SVG (héritent de currentColor) ── */
  var ICON_CLOCK =
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>';
  var ICON_EYE =
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>';
  var ICON_EYE_OFF =
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 ' +
    '5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19' +
    'm-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

  /* ── 1. CSS injecté une seule fois ── */
  if (!document.querySelector('style[data-tm]')) {
    var st = document.createElement('style');
    st.setAttribute('data-tm', '1');
    st.textContent = [
      /* bouton Minuteur : même allure que les autres boutons de la scorebar */
      '.tm-trigger{display:inline-flex;align-items:center;gap:5px}',
      '.tm-trigger svg{margin-top:-1px}',
      /* conteneur relatif pour ancrer le popover sous le bouton */
      '.tm-ctrl{position:relative}',
      /* popover de choix de la durée */
      '.tm-pop{position:absolute;top:calc(100% + 8px);right:0;z-index:20;width:250px;',
      'background:var(--card,#fff);border:1px solid var(--line,#dfe4e2);border-radius:12px;',
      'box-shadow:0 8px 28px rgba(16,24,40,.16);padding:12px 13px;font-size:13px}',
      '.tm-pop[hidden]{display:none}',
      '.tm-pop-title{font-weight:600;font-size:12px;letter-spacing:.02em;color:var(--mut,#5b6b73);',
      'text-transform:uppercase;margin:0 0 9px}',
      '.tm-presets{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:10px}',
      '.tm-presets button{padding:6px 4px;font-size:12.5px;font-weight:500;border-radius:8px;',
      'border:1px solid var(--line,#dfe4e2);background:var(--card,#fff);color:var(--ink,#132025);cursor:pointer}',
      '.tm-presets button:hover{border-color:var(--acc,#4f46e5);background:#eef2ff}',
      '.tm-presets button.sel{border-color:var(--acc,#4f46e5);background:#eef2ff;color:var(--acc,#4f46e5);font-weight:600}',
      '.tm-custom{display:flex;align-items:center;gap:6px;margin-bottom:11px;color:var(--mut,#5b6b73)}',
      '.tm-custom input{width:64px;font:inherit;font-size:13px;padding:5px 7px;border:1px solid var(--line,#dfe4e2);',
      'border-radius:8px;background:var(--card,#fff);color:var(--ink,#132025)}',
      '.tm-custom input:focus{outline:none;border-color:var(--acc,#4f46e5);box-shadow:0 0 0 3px #eef2ff}',
      '.tm-pop-actions{display:flex;gap:7px}',
      '.tm-pop-actions button{flex:1;padding:8px 6px;font-size:13px;font-weight:600;border-radius:9px;cursor:pointer}',
      '.tm-start{background:var(--acc,#4f46e5);border:1px solid var(--acc,#4f46e5);color:#fff}',
      '.tm-start:hover{filter:brightness(1.08)}',
      '.tm-stop{background:var(--card,#fff);border:1px solid var(--faux,#b91c1c);color:var(--faux,#b91c1c)}',
      '.tm-stop:hover{background:var(--fauxbg,#fbeceb)}',
      '.tm-stop[hidden]{display:none}',
      /* encadré du temps restant + bouton masquer, groupés */
      '.tm-display{display:inline-flex;align-items:center;gap:6px}',
      '.tm-display[hidden]{display:none}',
      '.tm-box{display:inline-flex;align-items:center;gap:7px;padding:4px 12px;border-radius:20px;',
      'border:1px solid var(--acc,#4f46e5);background:#eef2ff;color:var(--acc,#4f46e5);',
      'font-variant-numeric:tabular-nums;transition:background .25s,border-color .25s,color .25s}',
      '.tm-box svg{opacity:.85}',
      '.tm-time{font-size:15px;font-weight:700;letter-spacing:.5px;line-height:1;',
      'font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}',
      /* paliers d'alerte (rappel visuel façon examen) */
      '.tm-box.tm-warn{border-color:var(--neu,#b45309);background:var(--neubg,#fdf3e7);color:var(--neu,#b45309)}',
      '.tm-box.tm-crit{border-color:var(--faux,#b91c1c);background:var(--fauxbg,#fbeceb);color:var(--faux,#b91c1c);',
      'animation:tm-pulse 1s ease-in-out infinite}',
      '.tm-box.tm-ended{border-color:var(--faux,#b91c1c);background:var(--fauxbg,#fbeceb);color:var(--faux,#b91c1c);font-weight:800}',
      /* temps masqué : neutre, ne laisse fuiter aucune alerte */
      '.tm-box.tm-masked{border-color:var(--line,#dfe4e2);background:var(--card,#fff);color:var(--mut,#5b6b73);animation:none}',
      '@keyframes tm-pulse{0%,100%{opacity:1}50%{opacity:.55}}',
      '@media (prefers-reduced-motion:reduce){.tm-box.tm-crit{animation:none}}',
      /* bouton œil masquer/afficher */
      '.tm-eye{display:inline-flex;align-items:center;justify-content:center;padding:5px;line-height:0;',
      'border:1px solid var(--line,#dfe4e2);border-radius:8px;background:var(--card,#fff);',
      'color:var(--mut,#5b6b73);cursor:pointer}',
      '.tm-eye:hover{border-color:var(--acc,#4f46e5);color:var(--acc,#4f46e5)}',
      /* variantes sombres */
      'html.dark .tm-pop{background:var(--card,#1a1d27);border-color:var(--line,#2d3748)}',
      'html.dark .tm-presets button{background:#232734;border-color:var(--line,#2d3748);color:var(--ink,#e2e8f0)}',
      'html.dark .tm-presets button:hover,html.dark .tm-presets button.sel{background:#1e1b4b;border-color:var(--acc,#818cf8);color:var(--acc,#818cf8)}',
      'html.dark .tm-custom input{background:#232734;border-color:var(--line,#2d3748);color:var(--ink,#e2e8f0)}',
      'html.dark .tm-box{background:#1e1b4b;border-color:var(--acc,#818cf8);color:#c7d2fe}',
      'html.dark .tm-box.tm-warn{background:#2a1c05;border-color:var(--neu,#fbbf24);color:var(--neu,#fbbf24)}',
      'html.dark .tm-box.tm-crit,html.dark .tm-box.tm-ended{background:#3a0d0d;border-color:var(--faux,#f87171);color:var(--faux,#f87171)}',
      'html.dark .tm-box.tm-masked{background:#232734;border-color:var(--line,#2d3748);color:var(--mut,#8a9baa)}',
      'html.dark .tm-eye{background:#232734;border-color:var(--line,#2d3748);color:var(--mut,#8a9baa)}',
      'html.dark .tm-stop:hover{background:#3a0d0d}'
    ].join('');
    document.head.appendChild(st);
  }

  /* ── 2. Construction du DOM (bouton + popover + encadré) ── */
  var PLACEHOLDER = '––:––';

  var ctrl = document.createElement('span');
  ctrl.className = 'pill tm-ctrl';
  ctrl.innerHTML =
    '<button id="tm-trigger" class="tm-trigger" style="padding:2px 10px" ' +
    'aria-haspopup="true" aria-expanded="false">' + ICON_CLOCK + 'Minuteur</button>' +
    '<div class="tm-pop" id="tm-pop" hidden role="dialog" aria-label="Réglage du minuteur">' +
      '<p class="tm-pop-title">Durée du minuteur</p>' +
      '<div class="tm-presets" id="tm-presets">' +
        '<button data-min="30">30 min</button>' +
        '<button data-min="45">45 min</button>' +
        '<button data-min="60">1 h</button>' +
        '<button data-min="90">1 h 30</button>' +
        '<button data-min="120">2 h</button>' +
        '<button data-min="180">3 h</button>' +
      '</div>' +
      '<div class="tm-custom">' +
        '<label for="tm-input">Personnalisé :</label>' +
        '<input type="number" id="tm-input" min="1" max="600" step="1" inputmode="numeric" placeholder="min">' +
        '<span>min</span>' +
      '</div>' +
      '<div class="tm-pop-actions">' +
        '<button class="tm-start" id="tm-start">Démarrer</button>' +
        '<button class="tm-stop" id="tm-stop" hidden>Arrêter</button>' +
      '</div>' +
    '</div>';

  var display = document.createElement('span');
  display.className = 'tm-display';
  display.id = 'tm-display';
  display.hidden = true;
  display.innerHTML =
    '<span class="tm-box" id="tm-box">' + ICON_CLOCK +
      '<span class="tm-time" id="tm-time" aria-live="polite">' + PLACEHOLDER + '</span>' +
    '</span>' +
    '<button class="tm-eye" id="tm-eye" title="Masquer le temps restant" ' +
    'aria-label="Masquer le temps restant">' + ICON_EYE + '</button>';

  /* insérer juste après le bouton « Recommencer » (ou en fin de scorebar) */
  var resetBtn = scorebar.querySelector('#reset');
  var resetPill = resetBtn ? resetBtn.closest('.pill') : null;
  if (resetPill && resetPill.parentNode === scorebar) {
    resetPill.insertAdjacentElement('afterend', ctrl);
  } else {
    scorebar.appendChild(ctrl);
  }
  ctrl.insertAdjacentElement('afterend', display);

  /* ── 3. Références + état ── */
  var trigger  = ctrl.querySelector('#tm-trigger');
  var pop      = ctrl.querySelector('#tm-pop');
  var presets  = ctrl.querySelector('#tm-presets');
  var input    = ctrl.querySelector('#tm-input');
  var startBtn = ctrl.querySelector('#tm-start');
  var stopBtn  = ctrl.querySelector('#tm-stop');
  var box      = display.querySelector('#tm-box');
  var timeEl   = display.querySelector('#tm-time');
  var eyeBtn   = display.querySelector('#tm-eye');

  var tickId  = null;   /* id du setInterval */
  var endAt   = 0;      /* timestamp (ms) de fin */
  var totalS  = 0;      /* durée choisie (s) — pour calibrer les paliers d'alerte */
  var masked  = false;  /* temps caché ? */
  var ended   = false;  /* minuteur arrivé à 0 ? */

  /* ── 4. Utilitaires ── */
  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function fmt(sec) {
    if (sec < 0) sec = 0;
    var h = Math.floor(sec / 3600);
    var m = Math.floor((sec % 3600) / 60);
    var s = sec % 60;
    return h > 0 ? h + ':' + pad(m) + ':' + pad(s) : pad(m) + ':' + pad(s);
  }
  function remaining() { return Math.max(0, Math.round((endAt - Date.now()) / 1000)); }

  /* Rafraîchit l'encadré (texte + palier de couleur) selon l'état courant. */
  function render() {
    box.classList.remove('tm-warn', 'tm-crit', 'tm-ended', 'tm-masked');
    if (masked) {
      timeEl.textContent = PLACEHOLDER;
      box.classList.add('tm-masked');
      return;
    }
    var r = ended ? 0 : remaining();
    timeEl.textContent = fmt(r);
    if (ended || r === 0)      box.classList.add('tm-ended');
    else if (r <= 60)          box.classList.add('tm-crit');
    else if (r <= 300)         box.classList.add('tm-warn');
  }

  function stopTick() { if (tickId) { clearInterval(tickId); tickId = null; } }

  function tick() {
    if (remaining() <= 0) {
      ended = true;
      stopTick();
      if (masked) setMasked(false);   /* fin de temps : on révèle même si masqué */
      render();
      return;
    }
    render();
  }

  function startTimer(minutes) {
    totalS = Math.round(minutes * 60);
    endAt  = Date.now() + totalS * 1000;
    ended  = false;
    stopTick();
    render();
    display.hidden = false;
    tickId = setInterval(tick, 250);
    stopBtn.hidden = false;         /* le popover propose désormais « Arrêter » */
    closePop();
  }

  function stopTimer() {
    stopTick();
    endAt = 0; totalS = 0; ended = false;
    display.hidden = true;
    box.className = 'tm-box';
    timeEl.textContent = PLACEHOLDER;
    stopBtn.hidden = true;
    closePop();
  }

  function setMasked(on) {
    masked = on;
    eyeBtn.innerHTML = on ? ICON_EYE_OFF : ICON_EYE;
    var label = on ? 'Afficher le temps restant' : 'Masquer le temps restant';
    eyeBtn.title = label;
    eyeBtn.setAttribute('aria-label', label);
    render();
  }

  /* ── 5. Popover : ouverture / fermeture ── */
  function openPop() {
    pop.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
    setTimeout(function () { input.focus(); }, 0);
  }
  function closePop() {
    pop.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
  }
  function togglePop() { pop.hidden ? openPop() : closePop(); }

  /* ── 6. Câblage des événements ── */
  trigger.addEventListener('click', function (e) { e.stopPropagation(); togglePop(); });

  presets.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-min]');
    if (!b) return;
    input.value = b.dataset.min;
    [].forEach.call(presets.querySelectorAll('button'), function (x) { x.classList.remove('sel'); });
    b.classList.add('sel');
  });

  /* saisie manuelle → on déselectionne les presets qui ne correspondent plus */
  input.addEventListener('input', function () {
    [].forEach.call(presets.querySelectorAll('button'), function (x) {
      x.classList.toggle('sel', x.dataset.min === input.value);
    });
  });

  function handleStart() {
    var mins = parseFloat(input.value);
    if (!(mins > 0)) { input.focus(); return; }
    if (mins > 600) mins = 600;      /* garde-fou : 10 h max */
    startTimer(mins);
  }
  startBtn.addEventListener('click', handleStart);
  input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); handleStart(); } });
  stopBtn.addEventListener('click', stopTimer);

  eyeBtn.addEventListener('click', function () { setMasked(!masked); });

  /* fermer le popover au clic à l'extérieur ou sur Échap */
  document.addEventListener('click', function (e) {
    if (!pop.hidden && !ctrl.contains(e.target)) closePop();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !pop.hidden) closePop();
  });
})();
