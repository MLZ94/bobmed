import sys, re, base64, os, glob, json
from bs4 import BeautifulSoup
SP='/tmp/claude-0/-home-user/55cc2afb-deb2-5236-a438-a491d4be9ce0/scratchpad/ex'
def T(el): return el.get_text(' ', strip=True) if el else ''
def extract(path, only_sect=None):
    s = BeautifulSoup(open(path,encoding='utf-8').read(),'html.parser')
    name = os.path.basename(path)[:-5]
    out = [f"# {name}  ({path})", f"Titre : {T(s.select_one('header h1'))}", f"Sous-titre : {T(s.select_one('header .sub'))}", ""]
    wrap = s.select_one('.wrap'); sect='?'; imgn=0
    for el in wrap.find_all(recursive=False):
        cls = el.get('class') or []
        if 'sect' in cls:
            sect = T(el); out.append(f"\n## Section {sect}\n"); continue
        if 'q' not in cls: continue
        if only_sect and not re.match(only_sect, sect): continue
        q = el; qt = T(q.select_one('.qtype'))
        flags = []
        if q.get('data-neutral')=='1': flags.append('QUESTION NEUTRALISÉE')
        out.append(f"### {q.get('id')} [{q.get('data-type')} | badge {qt}] data-correct={q.get('data-correct','')!r}" + (f" data-answer={q.get('data-answer')!r}" if q.get('data-answer') else '') + (' '+' '.join(flags) if flags else ''))
        for child in q.find_all(recursive=False):
            c = child.get('class') or []
            if 'dpctx' in c: out.append("CONTEXTE: " + T(child))
            elif 'stem' in c: out.append("ÉNONCÉ: " + T(child))
            elif 'extra' in c:
                for im in child.select('img'):
                    src = im.get('src','')
                    m = re.match(r'data:image/(\w+);base64,(.*)', src)
                    if m:
                        imgn += 1; fn = f"{SP}/img/{name}_{q.get('id')}_{imgn}.{ 'jpg' if m.group(1)=='jpeg' else m.group(1)}"
                        open(fn,'wb').write(base64.b64decode(m.group(2))); out.append(f"[IMAGE: {fn}]")
                zones = child.select('.zone')
                for z in zones: out.append(f"  ZONE {z.get('data-l')} ({z.get('title','')}) style={z.get('style')}")
            elif child.name=='ul' and 'opts' in c:
                for o in child.select('.opt'):
                    tags=[]
                    if o.get('data-mandatory')=='1': tags.append('INDISPENSABLE')
                    if o.get('data-unacceptable')=='1': tags.append('INACCEPTABLE')
                    if o.get('data-neutral')=='1': tags.append('NEUTRALISÉ')
                    if o.get('data-w'): tags.append('poids '+o.get('data-w'))
                    l=o.get('data-l'); ok = l in (q.get('data-correct') or '')
                    out.append(f"  {l}. {T(o.select_one('.otext'))}  => {'VRAI' if ok else 'FAUX'}{(' ['+', '.join(tags)+']') if tags else ''}")
            elif 'correction' in c:
                for n in child.select('.note'): out.append("  NOTE OFFICIELLE: " + T(n))
                for ci in child.select('.citem'):
                    txt=T(ci); m=re.split(r'\b(VRAI|FAUX|NEUTRALISÉ)\b', txt, maxsplit=1)
                    after=re.sub(r'^\s*[—–-]\s*','',m[2]).strip() if len(m)>2 else ''
                    if after: out.append(f"  JUSTIF OFFICIELLE {T(ci.select_one('.cl'))} {after}")
                qa = child.select_one('.qrocans') or child.select_one('.qrocmodel')
                if qa: out.append("  RÉPONSE QROC: " + T(qa))
                if q.get('data-type')!='QROC' and not q.select('.opt'):
                    a = child.select_one('.ans'); out.append("  " + T(a))
                if 'TCS' in qt:
                    a = child.select_one('.ans'); out.append("  " + T(a))
        out.append("")
    return name, '\n'.join(out)
files = sorted(glob.glob('d3/t*/Quiz_*.html'))
for f in files:
    n, txt = extract(f); open(f"{SP}/{n}.md",'w').write(txt)
n, txt = extract('d2/t4/Quiz_UE7.3_2022-2023_S1.html'); open(f"{SP}/D2T4_Quiz_UE7.3_2022-2023_S1_commune_hemato.md",'w').write(txt)
print('ok')
