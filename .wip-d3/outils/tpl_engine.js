
const $ = s => document.querySelectorAll(s);
function fmtPts(p){return(Math.round(p*100)/100).toString().replace('.',',')}
function qPoints(disc,isQRU){if(isQRU)return disc===0?1:0;return disc===0?1:(disc===1?0.5:(disc===2?0.2:0))}

function markSpecial(q){
  const opts=[...q.querySelectorAll('.opt')];
  const cits=[...q.querySelectorAll('.correction .citem')];
  opts.forEach((o,i)=>{
    const c=cits[i];if(!c)return;
    if(o.dataset.mandatory==='1'&&!c.querySelector('.tag-mandatory')){
      const t=document.createElement('span');t.className='tag-mandatory';t.textContent='indispensable';c.appendChild(t);
    }
    if(o.dataset.unacceptable==='1'&&!c.querySelector('.tag-unacceptable')){
      const t=document.createElement('span');t.className='tag-unacceptable';t.textContent='inacceptable';c.appendChild(t);
    }
  });
}

function qrocNorm(s){return (s||'').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[’'`]/g,' ').replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,' ');}
function qrocAccept(q){var raw=q.dataset.answer||'';if(!raw){var a=q.querySelector('.qrocans')||q.querySelector('.qrocmodel');raw=a?a.textContent.replace(/^[^:]*:\s*/,''):'';}return raw.split(/\s*(?:\||\/|\bou\b)\s*/i).map(qrocNorm).filter(Boolean);}
function qrocStatus(q,pts){var st=q.querySelector('.status');if(!st)return;st.textContent=(pts>=1?'1':'0')+' / 1';st.className='status '+(pts>=1?'ok':'ko');}
function qrocSelfBox(q){if(q.dataset.result==='1')return;var c=q.querySelector('.correction');if(!c||c.querySelector('.selfassess'))return;var d=document.createElement('div');d.className='selfassess';var s=document.createElement('span');s.textContent='Votre réponse comptait-elle juste ?';var y=document.createElement('button');y.type='button';y.className='sa-yes';y.textContent="J'avais juste";var n=document.createElement('button');n.type='button';n.className='sa-no';n.textContent="J'avais faux";d.appendChild(s);d.appendChild(y);d.appendChild(n);c.appendChild(d);}
function qrocSelf(q,val){var inp=q.querySelector('.qrocin');if(inp){inp.classList.remove('good','bad');inp.classList.add(val?'good':'bad');}q.dataset.pts=val?1:0;q.dataset.result=val?'1':'0';qrocStatus(q,val?1:0);var box=q.querySelector('.selfassess');if(box){box.querySelectorAll('button').forEach(function(b){b.disabled=true;});var ch=box.querySelector(val?'.sa-yes':'.sa-no');if(ch)ch.classList.add('chosen');}updateScore();}
function gradeQroc(q){if(q.classList.contains('done'))return;var inp=q.querySelector('.qrocin');var typed=qrocNorm(inp?inp.value:'');var acc=qrocAccept(q);var ok=typed.length>0&&acc.indexOf(typed)>=0;if(inp){inp.readOnly=true;inp.classList.add(ok?'good':'bad');}q.classList.add('done');var cor=q.querySelector('.correction');if(cor)cor.hidden=false;var v=q.querySelector('.validate');if(v)v.disabled=true;var nq=q.dataset.neutral==='1';q.dataset.pts=(ok||nq)?1:0;q.dataset.result=(ok||nq)?'1':'0';qrocStatus(q,(ok||nq)?1:0);if(nq){var _st=q.querySelector('.status');if(_st)_st.textContent+=' — question neutralisée (point accordé à tous)';}else if(!ok)qrocSelfBox(q);updateScore();unlockNext(q);}
function grade(q){
  if(q.dataset.type==='QROC'){gradeQroc(q);return;}
  const correct=new Set(q.dataset.correct.split(''));
  const sel=new Set([...q.querySelectorAll('.opt.sel')].map(o=>o.dataset.l));
  let disc=0;
  q.querySelectorAll('.opt').forEach(o=>{
    const l=o.dataset.l,isC=correct.has(l),isS=sel.has(l);
    o.classList.remove('sel');
    // Item neutralisé par le jury : jamais compté (ni discordance, ni bonne réponse).
    if(o.dataset.neutral==='1'){o.classList.add('neutral');const m=document.createElement('span');m.className='mark';m.textContent='neutralisé';o.appendChild(m);return;}
    if(isC&&isS)o.classList.add('correct');
    else if(!isC&&isS){o.classList.add('wrong');disc++;}
    else if(isC&&!isS){o.classList.add('missed');disc++;}
    let m=document.createElement('span');m.className='mark';
    if(isC&&isS)m.textContent='✓';
    else if(!isC&&isS)m.textContent='✗';
    else if(isC&&!isS){m.textContent='manqué';m.style.color='var(--vrai)';}
    if(m.textContent)o.appendChild(m);
  });
  const isQRU=q.dataset.type==='QRU';
  const isProp=q.dataset.type==='QRP'||q.dataset.type==='QRPL'||q.dataset.type==='QZONE';const nExp=correct.size,good=[...sel].filter(l=>correct.has(l)).length;
  let pts=isProp?(nExp>0?good/nExp:0):qPoints(disc,isQRU);
  // TCS pondérée (plusieurs réponses validées par le jury) : points = poids data-w
  // de l'option choisie, 0 si l'option n'est pas validée.
  const isW=!!q.querySelector('.opt[data-w]');
  if(isW){const _o=[...q.querySelectorAll('.opt')].find(o=>sel.has(o.dataset.l));pts=_o&&_o.dataset.w!==undefined?parseFloat(_o.dataset.w):0;q.querySelectorAll('.opt.missed .mark').forEach(m=>{m.textContent='validée';});}
  const missMandatory=[...q.querySelectorAll('.opt[data-mandatory="1"]')].some(o=>!sel.has(o.dataset.l));
  const hitUnacceptable=[...q.querySelectorAll('.opt[data-unacceptable="1"]')].some(o=>sel.has(o.dataset.l));
  if(missMandatory||hitUnacceptable)pts=0;
  // Question neutralisée par le jury : point accordé à tous, quelle que soit la réponse.
  const isNQ=q.dataset.neutral==='1';if(isNQ)pts=1;
  q.classList.add('done');
  q.querySelector('.correction').hidden=false;
  markSpecial(q);
  const st=q.querySelector('.status');st.style.color='';
  st.textContent=fmtPts(pts)+' / 1';
  if(isProp)st.textContent+=' ('+good+'/'+nExp+' bonne'+(nExp>1?'s':'')+' réponse'+(nExp>1?'s':'')+')';
  else if(!isQRU&&disc>0)st.textContent+=' ('+disc+' incohérence'+(disc>1?'s':'')+')';
  if(isW&&pts>0&&pts<1)st.textContent+=' (réponse validée, pondérée par le jury)';
  if(missMandatory)st.textContent+=' — item indispensable manqué';
  if(hitUnacceptable)st.textContent+=' — item inacceptable coché';
  if(isNQ)st.textContent+=' — question neutralisée (point accordé à tous)';
  st.className='status '+(pts===1?'ok':(pts===0?'ko':'part'));
  if(pts>0&&pts<1)st.style.color='#9a6a00';
  q.querySelector('.validate').disabled=true;
  q.dataset.pts=pts;q.dataset.result=pts===1?'1':'0';
  updateScore();unlockNext(q);
}

function reveal(q,skipUnlock){
  if(q.classList.contains('done'))return;
  if(q.dataset.type!=='QROC'){
    const correct=new Set(q.dataset.correct.split(''));
    q.querySelectorAll('.opt').forEach(o=>{o.classList.remove('sel');if(correct.has(o.dataset.l))o.classList.add('correct');if(o.dataset.neutral==='1')o.classList.add('neutral');});
    const v=q.querySelector('.validate');if(v)v.disabled=true;
  }else{
    const st=q.querySelector('.status');st.textContent='révélée';st.className='status rl';
  }
  q.classList.add('done');q.querySelector('.correction').hidden=false;
  markSpecial(q);
  if(q.dataset.pts===undefined)q.dataset.result='skip';
  updateScore();if(!skipUnlock)unlockNext(q);
}

function updateScore(){
  const qs=[...$('.q')];const all=qs.length;
  const done=qs.filter(q=>q.classList.contains('done')).length;
  const grad=qs.length;
  let pts=0;
  qs.forEach(q=>{if(q.dataset.pts!==undefined&&q.dataset.pts!=='')pts+=parseFloat(q.dataset.pts);});
  const sd=document.getElementById('s-done');if(sd)sd.textContent=done+'/'+all;
  const so=document.getElementById('s-ok');if(so)so.textContent=fmtPts(pts)+'/'+grad;
}

document.addEventListener('click',e=>{
  const li=e.target.closest('.opt');
  if(li){
    const q=li.closest('.q');
    if(!q.classList.contains('done')){
      if(q.dataset.type==='QRU'){q.querySelectorAll('.opt').forEach(o=>o.classList.remove('sel'));li.classList.add('sel');}
      else if(q.dataset.type==='QRP'||q.dataset.type==='QRPL'){const _mx=(q.dataset.correct||'').replace(/[^A-Za-z]/g,'').length;if(li.classList.contains('sel'))li.classList.remove('sel');else if(!_mx||q.querySelectorAll('.opt.sel').length<_mx)li.classList.add('sel');}
      else{li.classList.toggle('sel');}
    }
    return;
  }
  const v=e.target.closest('.validate');if(v){grade(v.closest('.q'));return;}
  const s=e.target.closest('.show');if(s){var _q=s.closest('.q');reveal(_q);if(_q.dataset.type==='QROC')qrocSelfBox(_q);return;}
  var _sy=e.target.closest('.sa-yes');if(_sy){qrocSelf(_sy.closest('.q'),1);return;}
  var _sn=e.target.closest('.sa-no');if(_sn){qrocSelf(_sn.closest('.q'),0);return;}
});

function initLocks(){
  let nextFree=false,inDP=false;
  for(const el of document.querySelector('.wrap').children){
    if(el.classList.contains('sect')){inDP=/DP|KFP|TCS/.test(el.textContent);nextFree=inDP;continue;}
    if(el.classList.contains('q')){if(nextFree){nextFree=false;}else if(inDP){el.classList.add('locked');}}
  }
}

function unlockNext(q){
  let el=q.nextElementSibling;
  while(el){
    if(el.classList.contains('sect'))break;
    if(el.classList.contains('q')&&el.classList.contains('locked')){
      el.classList.remove('locked');
      setTimeout(()=>el.scrollIntoView({behavior:'smooth',block:'nearest'}),100);
      break;
    }
    el=el.nextElementSibling;
  }
}

const rb=document.getElementById('reset');if(rb)rb.addEventListener('click',()=>location.reload());
const ra=document.getElementById('revealall');if(ra)ra.addEventListener('click',()=>{
  $('.q.locked').forEach(q=>q.classList.remove('locked'));
  $('.q').forEach(q=>reveal(q,true));
});
initLocks();updateScore();
