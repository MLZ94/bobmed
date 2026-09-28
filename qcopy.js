/* qcopy.js — chip .qnum cliquable : copie la question (type, contexte clinique,
   énoncé(s), items, image(s)) dans le presse-papiers pour un chat IA.
   Ne lit jamais .correction/.citem/data-correct : identique avant/après réponse.
   Chargé sur tous les quiz (cf. CLAUDE.md § « Chip de copie de question »). */
function qClipText(el) {
  if (!el) return '';
  const c = el.cloneNode(true);
  c.querySelectorAll('br').forEach(br => br.replaceWith('\n'));
  return c.textContent.replace(/[ \t]+/g, ' ').replace(/\n\s+/g, '\n').trim();
}
function qLoadImage(img) {
  return new Promise(resolve => {
    const im = new Image();
    im.onload = () => resolve(im);
    im.onerror = () => resolve(null);
    im.src = img.src;
  });
}
function qCombineImages(imgs) {                 // empile plusieurs images en un seul PNG
  return Promise.all(imgs.map(qLoadImage)).then(loaded => {
    loaded = loaded.filter(Boolean);
    if (!loaded.length) return null;
    const gap = loaded.length > 1 ? 16 : 0;
    const width = Math.max(...loaded.map(im => im.naturalWidth));
    const height = loaded.reduce((h, im) => h + im.naturalHeight, 0) + gap * (loaded.length - 1);
    const cv = document.createElement('canvas'); cv.width = width; cv.height = height;
    const ctx = cv.getContext('2d'); ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, width, height);
    let y = 0; loaded.forEach(im => { ctx.drawImage(im, 0, y); y += im.naturalHeight + gap; });
    return new Promise(resolve => cv.toBlob(resolve, 'image/png'));
  });
}
function buildQuestionClipboard(q) {
  const parts = []; const images = [];
  const qt = q.querySelector('.qhead .qtype'); if (qt) parts.push(qClipText(qt));
  q.querySelectorAll('.dpctx, .stem, .extra').forEach(el => {
    if (el.classList.contains('extra')) el.querySelectorAll('img').forEach(img => { images.push(img); parts.push('[Image]'); });
    else parts.push(qClipText(el));
  });
  q.querySelectorAll('.opts > .opt, .extra.zonewrap > .zone').forEach(it => {
    const l = it.dataset.l; if (!l) return;
    const otext = it.querySelector('.otext');
    const txt = otext ? qClipText(otext) : (it.getAttribute('title') || '').trim();
    parts.push(l + ' ' + txt);
  });
  return { text: parts.filter(Boolean).join('\n'), images };
}
function copyQuestion(q, chip) {
  if (!q) return;
  const data = buildQuestionClipboard(q);
  const prevText = chip.textContent;
  const done = ok => {
    chip.classList.add('copied');
    chip.textContent = ok ? '✓ Copié !' : 'Échec';
    setTimeout(() => { chip.classList.remove('copied'); chip.textContent = prevText; }, 1400);
  };
  const writeTextOnly = () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(data.text).then(() => done(true)).catch(() => done(false));
    } else done(false);
  };
  if (window.ClipboardItem && navigator.clipboard && navigator.clipboard.write) {
    (data.images.length ? qCombineImages(data.images) : Promise.resolve(null)).then(imgBlob => {
      const payload = { 'text/plain': new Blob([data.text], { type: 'text/plain' }) };
      if (imgBlob) payload['image/png'] = imgBlob;
      return navigator.clipboard.write([new ClipboardItem(payload)]);      // 1 seul ClipboardItem : Chrome refuse un tableau de plusieurs items
    }).then(() => done(true)).catch(() => writeTextOnly());
  } else writeTextOnly();
}
document.addEventListener('click', e => {
  const qn = e.target.closest('.qnum'); if (qn) copyQuestion(qn.closest('.q'), qn);
});
document.addEventListener('keydown', e => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.classList && e.target.classList.contains('qnum')) {
    e.preventDefault(); copyQuestion(e.target.closest('.q'), e.target);
  }
});
document.querySelectorAll('.qnum').forEach(el => {
  el.tabIndex = 0; el.setAttribute('role', 'button');
  el.title = 'Copier la question pour un chat IA';
  el.setAttribute('aria-label', 'Copier la question ' + el.textContent + ' pour un chat IA');
});
