import sys, pymupdf
src, out, tag = sys.argv[1], sys.argv[2], sys.argv[3]
pages_dir = sys.argv[4]
doc = pymupdf.open(src)
lines = [f"# {src}\n"]
for i, page in enumerate(doc, 1):
    lines.append(f"\n## Diapo {i}\n")
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            parts = []
            for s in l["spans"]:
                t = s["text"]
                if not t.strip(): parts.append(t); continue
                c = s["color"]; r, g, bl = (c >> 16) & 255, (c >> 8) & 255, c & 255
                red = r > 150 and g < 100 and bl < 100
                parts.append(f"**[ROUGE]{t}[/ROUGE]**" if red else t)
            txt = "".join(parts).strip()
            if txt: lines.append(txt)
    page.get_pixmap(dpi=60).save(f"{pages_dir}/{tag}_{i:03d}.png")
open(out, "w").write("\n".join(lines))
print(src, len(doc), "pages")
