#!/usr/bin/env python3
"""Generate useful, crawlable location pages from published authority news."""
import json, html, re, unicodedata
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

ROOT=Path("viranomaiset")
BASE="https://jouniatormanen-cmd.github.io/uutispalvelu/viranomaiset/"
def slug(s):
    s=unicodedata.normalize("NFKD",s.lower())
    return re.sub(r"[^a-z0-9]+","-", "".join(c for c in s if not unicodedata.combining(c))).strip("-")
def esc(s): return html.escape(str(s),quote=True)
def page(label,kind,items):
    title=f"{label} – viranomaistiedotteet ja tilanneuutiset | Tilanneuutiset"
    links="\n".join(f'<li><a href="{esc(x["link"])}" rel="noopener noreferrer">{esc(x["title"])}</a> <small>— {esc(x.get("source",""))}, {esc(x.get("date","")[:10])}</small></li>' for x in items[:100])
    return f"""<!doctype html><html lang="fi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(label)}: ajankohtaiset poliisin ja muiden viranomaisten tiedotteet sekä turvallisuustilanteet."><style>body{{font:16px system-ui,sans-serif;margin:0;color:#18304b;background:#f3f6fa}}header{{background:#103457;color:white;padding:22px}}header a{{color:white}}main{{max-width:850px;margin:auto;padding:20px}}li{{margin:0 0 15px}}a{{color:#174b7a}}small{{color:#52657a}}.note{{background:white;padding:15px;border-radius:8px}}</style></head><body><header><a href="{BASE}">Tilanneuutiset – etusivu</a></header><main><h1>{esc(label)} – tilanneuutiset</h1><p class="note">Alueen ajankohtaiset viranomaistiedotteet. Tiedot perustuvat alkuperäisiin lähteisiin; palvelu ei ole viranomaisen ylläpitämä. Näytetään saatavilla olevat viimeisen 30 päivän uutiset.</p><ul>{links}</ul><p><a href="{BASE}">Hae muita paikkakuntia ja uutisia Tilanneuutisista</a></p></main></body></html>"""
def main():
    data=json.loads((ROOT/"news.json").read_text(encoding="utf-8"))
    items=data.get("items",[])
    cutoff=datetime.now(timezone.utc)-timedelta(days=30)
    groups={}
    for x in items:
        try:
            d=datetime.fromisoformat(x.get("date","").replace("Z","+00:00"))
            if d.tzinfo is None or d<cutoff: continue
        except ValueError: continue
        for kind,key in (("maakunta","province"),("paikkakunta","municipality")):
            name=x.get(key)
            if name and name not in ("Tuntematon","Koko Suomi"):
                groups.setdefault((kind,name),[]).append(x)
    urls=[BASE,BASE+"varoitukset.html"]
    generated=[]
    for (kind,name),rows in sorted(groups.items()):
        if len(rows)<2: continue
        path=ROOT/"alueet"/kind/(slug(name)+".html")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(page(name,kind,rows),encoding="utf-8")
        generated.append(path)
        urls.append(BASE+"alueet/"+kind+"/"+quote(slug(name))+".html")
    for path in (ROOT/"alueet").glob("**/*.html"):
        if path not in generated: path.unlink()
    sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{esc(url)}</loc></url>\n' for url in urls)+'</urlset>\n'
    (ROOT/"sitemap.xml").write_text(sitemap,encoding="utf-8")
    print(f"Generated {len(generated)} location pages")
if __name__=="__main__": main()
