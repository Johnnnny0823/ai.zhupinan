import sys, re, html, pathlib
src = pathlib.Path(sys.argv[1]); dst = pathlib.Path(sys.argv[2])
t = src.read_text(encoding="utf-8", errors="replace")
name = re.search(r'id="hlLawName"[^>]*>([^<]+)<', t)
date = re.search(r'修正日期：</th>\s*<td>([^<]+)<', t) or re.search(r'公布日期：</th>\s*<td>([^<]+)<', t)
out = [f"# {name.group(1) if name else src.stem}", f"修正日期：{date.group(1).strip() if date else '?'}", ""]
for m in re.finditer(r'<div class="col-no">\s*<a[^>]*>([^<]+)</a>.*?<div class="law-article">(.*?)</div>\s*</div>\s*</div>', t, re.S):
    no = m.group(1).strip()
    body = re.sub(r'<[^>]+>', '\n', m.group(2))
    body = "\n".join(l.strip() for l in html.unescape(body).splitlines() if l.strip())
    out.append(f"## {no}\n{body}\n")
dst.write_text("\n".join(out), encoding="utf-8")
print(dst, len(out)-3, "articles")
