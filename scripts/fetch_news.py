import json,urllib.request,xml.etree.ElementTree as ET,datetime,email.utils,re,os
feeds=[
("Yle","https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET",""),
("Yle Uusimaa","https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET_UUSIMAA","uusimaa"),
("Yle Itä-Uusimaa","https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET_ITA_UUSIMAA","ita-uusimaa"),
("Ilta-Sanomat","https://www.is.fi/rss/tuoreimmat.xml",""),
("MTV Uutiset","https://www.mtvuutiset.fi/rss","")]
out=[];seen=set()
for name,url,region in feeds:
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Uutispalvelu/1.0"})
  with urllib.request.urlopen(req,timeout=18) as r: root=ET.fromstring(r.read())
  for item in root.findall(".//item")[:70]:
   title=(item.findtext("title") or "").strip();link=(item.findtext("link") or "").strip()
   if not title or not link.startswith("https://"):continue
   key=re.sub(r"\W+","",title.lower())[:80]
   if key in seen:continue
   seen.add(key)
   raw=item.findtext("pubDate") or ""
   try:date=email.utils.parsedate_to_datetime(raw).isoformat()
   except:date=""
   out.append(dict(title=title,link=link,date=date,source=name,region=region))
  print(name,"OK")
 except Exception as e:print(name,"FAILED",str(e))
out.sort(key=lambda x:x["date"],reverse=True)
if out:
 with open("news.json","w",encoding="utf-8") as f:json.dump({"updated":datetime.datetime.now(datetime.timezone.utc).isoformat(),"items":out},f,ensure_ascii=False)
 print("Saved",len(out))
else:
 print("No feeds succeeded; keeping previous news.json")
