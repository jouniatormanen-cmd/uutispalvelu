import json, urllib.request, xml.etree.ElementTree as ET, datetime, email.utils, re, concurrent.futures
FEEDS=[
("Yle","https://yle.fi/rss/uutiset/tuoreimmat",""),
("Yle","https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET",""),
("Yle Urheilu","https://yle.fi/rss/urheilu",""),
("Yle","https://yle.fi/rss/t/18-34837/fi",""),
("Yle","https://yle.fi/rss/t/18-34953/fi",""),
("Yle","https://yle.fi/rss/t/18-19274/fi",""),
("Yle","https://yle.fi/rss/t/18-35138/fi",""),
("Yle","https://yle.fi/rss/t/18-12/fi",""),
("Yle Uusimaa","https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET_UUSIMAA","uusimaa"),
("Yle Itä-Uusimaa","https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET_ITA_UUSIMAA","ita-uusimaa"),
("Ilta-Sanomat","https://www.is.fi/rss/tuoreimmat.xml",""),
("Iltalehti","https://www.iltalehti.fi/rss/uutiset.xml",""),
("Helsingin Sanomat","https://www.hs.fi/rss/tuoreimmat.xml",""),
("Aamulehti","https://www.aamulehti.fi/rss/tuoreimmat.xml","tampere"),
("Kauppalehti","https://feeds.kauppalehti.fi/rss/main",""),
("Kauppalehti","https://feeds.kauppalehti.fi/rss/klnyt",""),
("MTV Uutiset","https://www.mtvuutiset.fi/api/feed/rss/mtv_uusimmat_100",""),
("MTV Uutiset","https://www.mtvuutiset.fi/rss","")]
def fetch(feed):
 name,url,region=feed
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; Uutispalvelu RSS reader)"})
  with urllib.request.urlopen(req,timeout=14) as response:root=ET.fromstring(response.read(2000000))
  items=root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
  result=[]
  for item in items[:120]:
   title=(item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
   link=(item.findtext("link") or "").strip()
   if not link:
    atom=item.find("{http://www.w3.org/2005/Atom}link")
    if atom is not None:link=atom.get("href","")
   if not title or not link.startswith("https://"):continue
   raw=item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}updated") or ""
   try:date=email.utils.parsedate_to_datetime(raw).astimezone(datetime.timezone.utc).isoformat()
   except (ValueError,TypeError):
    try:date=datetime.datetime.fromisoformat(raw.replace("Z","+00:00")).astimezone(datetime.timezone.utc).isoformat()
    except ValueError:date=""
   result.append(dict(title=title,link=link,date=date,source=name,region=region))
  print(name,len(result),url,flush=True)
  return result
 except Exception as e:
  print("FAILED",name,url,str(e),flush=True)
  return []
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:batches=list(pool.map(fetch,FEEDS))
old=[]
try:
 with open("news.json",encoding="utf-8") as f:old=json.load(f).get("items",[])
except (OSError,ValueError):pass
new=[item for batch in batches for item in batch]
if not new:
 print("No feeds succeeded; keeping previous news.json")
 raise SystemExit(0)
cutoff=datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=7)
seen=set();merged=[]
for item in new+old:
 title=item.get("title","");link=item.get("link","")
 if not title or not link:continue
 try:
  if datetime.datetime.fromisoformat(item.get("date","")).astimezone(datetime.timezone.utc)<cutoff:continue
 except (ValueError,TypeError):pass
 key=(item.get("source","").replace("Yle Urheilu","Yle").replace("Yle Uusimaa","Yle").replace("Yle Itä-Uusimaa","Yle"),re.sub(r"\W+","",title.casefold())[:120])
 if key in seen:continue
 seen.add(key);merged.append(item)
merged.sort(key=lambda item:item.get("date",""),reverse=True)
merged=merged[:2000]
with open("news.json","w",encoding="utf-8") as f:json.dump({"updated":datetime.datetime.now(datetime.timezone.utc).isoformat(),"items":merged},f,ensure_ascii=False)
print("Saved",len(merged),"stories")
