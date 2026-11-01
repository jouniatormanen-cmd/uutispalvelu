#!/usr/bin/env python3
"""Collect public Finnish authority RSS headlines, no third-party dependencies."""
import concurrent.futures, datetime as dt, email.utils, html, json, os, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT=os.path.dirname(os.path.dirname(__file__))
OUTPUT=os.path.join(ROOT,"viranomaiset","news.json")
ARCHIVE=os.path.join(ROOT,"viranomaiset","archive.json")
SOURCES=[
("Helsingin poliisilaitos","https://poliisi.fi/helsingin-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Poliisi – valtakunnallinen RSS","https://poliisi.fi/etusivu/-/asset_publisher/mhkofNyGe9wn/rss"),
 ("Hämeen poliisilaitos","https://poliisi.fi/hameen-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Itä-Suomen poliisilaitos","https://poliisi.fi/ita-suomen-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Itä-Uudenmaan poliisilaitos","https://poliisi.fi/ita-uudenmaan-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Kaakkois-Suomen poliisilaitos","https://poliisi.fi/kaakkois-suomen-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Keskusrikospoliisi","https://poliisi.fi/keskusrikospoliisi/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Lapin poliisilaitos","https://poliisi.fi/lapin-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Lounais-Suomen poliisilaitos","https://poliisi.fi/lounais-suomen-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Länsi-Uudenmaan poliisilaitos","https://poliisi.fi/lansi-uudenmaan-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Oulun poliisilaitos","https://poliisi.fi/oulun-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Pohjanmaan poliisilaitos","https://poliisi.fi/pohjanmaan-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Poliisihallitus","https://poliisi.fi/poliisihallitus/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Sisä-Suomen poliisilaitos","https://poliisi.fi/sisa-suomen-poliisilaitos/-/asset_publisher/ZtAEeHB39Lxr/rss"),
 ("Keski-Suomen pelastuslaitos","https://www.sttinfo.fi/uutishuone/keski-suomen-hyvinvointialue?publisherId=69821063"),
 ("Helsingin pelastuslaitos","https://www.sttinfo.fi/uutishuone/69817736/helsingin-kaupungin-pelastuslaitos/r"),
 ("Ilmatieteen laitos","https://www.ilmatieteenlaitos.fi/api/news/tiedote/rss"),
 ("Pirkanmaan pelastuslaitos","https://www.sttinfo.fi/uutishuone/69819808/pirkanmaan-pelastuslaitos/r"),
 ("Traficom – tieliikenne","https://www.traficom.fi/feed/rss/fi/75"),
 ("Traficom – kyberturvallisuus","https://www.traficom.fi/feed/rss/fi/117"),
]
# Nationwide coverage targets are monitored separately from verified working feeds.
POLICE_TARGETS = [
 "Helsingin", "Hämeen", "Itä-Suomen", "Itä-Uudenmaan",
 "Kaakkois-Suomen", "Lapin", "Lounais-Suomen",
 "Länsi-Uudenmaan", "Oulun", "Pohjanmaan", "Sisä-Suomen",
]
RESCUE_TARGETS = [
 "Etelä-Karjalan", "Etelä-Pohjanmaan", "Etelä-Savon", "Helsingin",
 "Itä-Uudenmaan", "Kainuun", "Kanta-Hämeen", "Keski-Pohjanmaan",
 "Keski-Suomen", "Keski-Uudenmaan", "Kymenlaakson", "Lapin",
 "Länsi-Uudenmaan", "Pirkanmaan", "Pohjanmaan", "Pohjois-Karjalan",
 "Pohjois-Pohjanmaan", "Pohjois-Savon", "Päijät-Hämeen",
 "Satakunnan", "Varsinais-Suomen",
]
class Links(HTMLParser):
 def __init__(self): super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag not in ("a","link"):return
  d=dict(attrs);u=d.get("href","")
  if u and (re.search(r"rss|feed|\.xml|atom",u,re.I) or "rss" in d.get("type","").lower()):self.links.append(u)
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Tilanneuutiset/1.0 (public RSS reader)","Accept":"application/rss+xml,application/atom+xml,application/xml,text/xml,text/html;q=0.8"})
 with urllib.request.urlopen(req,timeout=15) as response:return response.read(2500000),response.geturl()
def parse_date(s):
 if not s:return None
 try:return email.utils.parsedate_to_datetime(s).astimezone(dt.timezone.utc).isoformat()
 except Exception:
  try:return dt.datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(dt.timezone.utc).isoformat()
  except Exception:return None
def text(node,names):
 for name in names:
  v=node.findtext(name)
  if v:return " ".join(v.split())
 return ""
def feed_items(raw,source):
 try:root=ET.fromstring(raw)
 except ET.ParseError:return []
 result=[]
 if root.tag.lower().endswith("rss") or root.tag.lower().endswith("rdf"):
  nodes=[n for n in root.iter() if n.tag.split("}")[-1]=="item"]
 else:nodes=root.findall("{http://www.w3.org/2005/Atom}entry")
 for n in nodes:
  title=html.unescape(text(n,["title","{http://www.w3.org/2005/Atom}title"]))
  link=text(n,["link"])
  if not link:
   for a in n.findall("{http://www.w3.org/2005/Atom}link"):
    if a.get("rel","alternate")=="alternate":link=a.get("href","");break
  description=html.unescape(re.sub(r"<[^>]+>"," ",text(n,["description","{http://www.w3.org/2005/Atom}summary","{http://www.w3.org/2005/Atom}content"])))
  description=" ".join(description.split())[:900]
  published=parse_date(text(n,["pubDate","{http://purl.org/dc/elements/1.1/}date","{http://www.w3.org/2005/Atom}published","{http://www.w3.org/2005/Atom}updated"]))
  if title and link and link.startswith("http"):
   result.append({"title":title,"link":link,"source":source,"date":published,"region":"","description":description})
 return result
def collect(source,page):
 try:raw,url=get(page)
 except Exception as e:print(source,"listing failed:",e);return [],"virhe: "+str(e)[:160],0
 direct=feed_items(raw,source)
 if direct:return direct,"toimii",1
 parser=Links();parser.feed(raw.decode("utf-8","replace"))
 candidates=[]
 for href in parser.links:
  absolute=urllib.parse.urljoin(url,href)
  if urllib.parse.urlsplit(absolute).netloc!=urllib.parse.urlsplit(page).netloc:continue
  if absolute not in candidates:candidates.append(absolute)
 # Prefer explicit RSS/XML URLs; avoid dozens of unrelated links.
 candidates=sorted(candidates,key=lambda u:(0 if re.search(r"rss|\.xml",u,re.I) else 1,len(u)))[:18]
 out=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  futures={pool.submit(get,u):u for u in candidates}
  for f in concurrent.futures.as_completed(futures):
   try:out.extend(feed_items(f.result()[0],source))
   except Exception:pass
 print(source,":",len(out),"headlines from",len(candidates),"candidate feeds")
 return out,("toimii" if out else "syötteistä ei saatu uutisia"),len(candidates)
# Prioritise concrete events and practical notices affecting residents.
RELEVANT=re.compile(r"rakennuspalo|savuhavainto|palohälytys|ulosajo|peräänajo|törmäys|törmäsi|puukotus|öljyvahinko|kaasuvuoto|rikos|ratti|ylinopeus|liikennevalvonta|kadonnut|löytynyt|etsii|havainto|operaati|kiinniotto|epäil|onnettomuus|kolari|tulipalo|maastopalo|palo |pelast|poliisi etsii|kadonnut|etsintä|ryöstö|murto|varkau|pahoinpitely|väkival|ampumi|liikennehäi|tie sulj|tiesul|tietyö|kiertotie|ruuhka|junaliiken|liikennekatko|sähkökatko|vesikatko|vedenkeitt|juomaves|myrsky|säävaroit|varoitus|tulva|liukka|pakkan|helle|takaisinveto|tuotevirhe|huijaus|petos|tietomurto|häiriö|katkos|palvelukatko|epidemia|tartunta|terveysriski|saastun|vaaratiedote|evaku|lakko|peruuntu|peruttu|suljettu|avataan|muuttuu|muutos|hinnat|hintojen|etuuden|etuudet|asumistuki|toimeentulotuki|työttömyys|kela",re.I)
EXCLUDE=re.compile(r"webinaari|vaalitavoitteet|yleistiedoksianto|kuulutus|hankintailmoitus|huutokauppa|lakiesitys|lausuntokierros|lausunto |lausunto:|hallitus esittää|ministeri tapasi|ministeri osallist|nimitys|nimitettiin|työryhmä|strategia|selonteko|valiokunta|eduskunnan käsittely|asetusehdotus|budjettiriihi|virkanimitys|seminaar|konferenssi|vuosikertomus|tutkimushanke",re.I)
# Enrich municipal metadata without guessing locations from the publisher's name.
# Use the same complete municipality/region map as the website, avoiding drift.
def load_municipalities():
 path=os.path.join(ROOT,"viranomaiset","index.html")
 with open(path,encoding="utf-8") as f:page=f.read()
 match=re.search(r"const municipalityMap=(\{.*?\});function norm\(",page,re.S)
 if not match:raise RuntimeError("Municipality map not found in website")
 result=json.loads(match.group(1))
 if len(result)!=19 or sum(len(v) for v in result.values())!=308:
  raise RuntimeError("Municipality map incomplete")
 return result
MUNICIPALITIES=load_municipalities()

# Only title and description are used: publisher coverage does not imply event location.
# Match actual Finnish place-name forms; do not infer an event's location from its publisher.
PLACE_ALIASES={
 "Helsinki":["Helsinki","Helsingissä","Helsingistä","Helsinkiin","Helsingin","Helsingille"],
 "Turku":["Turku","Turussa","Turusta","Turkuun","Turun"],
 "Tampere":["Tampere","Tampereella","Tampereelta","Tampereelle","Tampereen"],
 "Lahti":["Lahti","Lahdessa","Lahdesta","Lahteen","Lahden"],
 "Oulu":["Oulu","Oulussa","Oulusta","Ouluun","Oulun"],
 "Pori":["Pori","Porissa","Porista","Poriin","Porin"],
 "Kemi":["Kemi","Kemissä","Kemistä","Kemiin","Kemin"],
 "Kotka":["Kotka","Kotkassa","Kotkasta","Kotkaan","Kotkan"],
 "Hämeenlinna":["Hämeenlinna","Hämeenlinnassa","Hämeenlinnasta","Hämeenlinnaan","Hämeenlinnan"],
 "Jyväskylä":["Jyväskylä","Jyväskylässä","Jyväskylästä","Jyväskylään","Jyväskylän"],
 "Porvoo":["Porvoo","Porvoossa","Porvoosta","Porvooseen","Porvoon"],
 "Vantaa":["Vantaa","Vantaalla","Vantaalta","Vantaalle","Vantaan"],
 "Espoo":["Espoo","Espoossa","Espoosta","Espooseen","Espoon"],
 "Sipoo":["Sipoo","Sipoossa","Sipoosta","Sipooseen","Sipoon"],
 "Loviisa":["Loviisa","Loviisassa","Loviisasta","Loviisaan","Loviisan"],
 "Kitee":["Kitee","Kiteellä","Kiteeltä","Kiteelle","Kiteen"],
}
PLACE_PATTERNS=[
 (place,province,re.compile(r"(?<!\w)(?:"+ "|".join(re.escape(v) for v in PLACE_ALIASES.get(place,[place,place+"ssa",place+"ssä",place+"sta",place+"stä",place+"lla",place+"llä",place+"lta",place+"ltä",place+"lle",place+"n"])) +r")(?!\w)",re.I))
 for province,places in MUNICIPALITIES.items() for place in places
]
def enrich_location(item):
 content=" ".join((item.get("title",""),item.get("description","")))
 found={(place,province) for place,province,pattern in PLACE_PATTERNS if pattern.search(content)}
 # Retained news is checked again instead of trusting old, potentially incorrect metadata.
 item["municipality"]=item["province"]=item["region"]=""
 if len(found)==1:
  place,province=next(iter(found))
  item.update(municipality=place,province=province,region=place)
 return item

# Identify explicitly mentioned locations, not the publisher's headquarters.
LOCAL_PLACES={"Uusimaa":"Porvoo Sipoo Loviisa Askola Lapinjärvi Myrskylä Pukkila Helsinki Espoo Vantaa Kerava Tuusula Järvenpää","Varsinais-Suomi":"Turku Salo Raisio Naantali","Pirkanmaa":"Tampere Nokia Kangasala","Päijät-Häme":"Lahti Heinola","Kymenlaakso":"Kotka Kouvola Hamina","Keski-Suomi":"Jyväskylä Jämsä","Pohjois-Pohjanmaa":"Oulu Raahe","Lappi":"Rovaniemi Kemi Tornio"}
def add_area(n):
 if n.get("municipality"):return n
 headline=n.get("title","")
 matches=[]
 for province,names in LOCAL_PLACES.items():
  for name in names.split():
   if re.search(r"(?<!\w)"+re.escape(name)+r"(?:ssa|ssä|sta|stä|lla|llä|lta|ltä|n)?(?!\w)",headline,re.I):
    matches.append((name,province))
 if len(matches)==1:
  n["municipality"],n["province"]=matches[0]
  n["region"]=matches[0][0]
 return n

def consumer_relevant(n):
 title=n.get("title","")
 return bool(RELEVANT.search(title)) and not bool(EXCLUDE.search(title))

def main():
 old=[]
 try:
  with open(OUTPUT,encoding="utf-8") as f:old=json.load(f).get("items",[])
 except (OSError,ValueError):pass
 try:
  with open(ARCHIVE,encoding="utf-8") as f:old+=json.load(f).get("items",[])
 except (OSError,ValueError):pass
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  futures=[pool.submit(collect,*s) for s in SOURCES]
  results=[f.result() for f in futures]
  fresh=[n for result in results for n in result[0]]
  monitoring=[{"source":source,"status":result[1],"fetched":len(result[0]),"feeds_checked":result[2]} for (source,_),result in zip(SOURCES,results)]
 working={source for (source,_),result in zip(SOURCES,results) if result[1]=="toimii" and result[0]}
 coverage={
  "police_active":[x for x in POLICE_TARGETS if x+" poliisilaitos" in working],
  "police_missing":[x for x in POLICE_TARGETS if x+" poliisilaitos" not in working],
  "rescue_active":[x for x in RESCUE_TARGETS if x+" pelastuslaitos" in working],
  "rescue_missing":[x for x in RESCUE_TARGETS if x+" pelastuslaitos" not in working],
  "aland_police_verified":False,
  "aland_rescue_verified":False,
 }
 print("Nationwide coverage gaps:",json.dumps(coverage,ensure_ascii=False))
 now=dt.datetime.now(dt.timezone.utc);items={}
 if not fresh:print("WARNING: no fresh feed entries; retaining previous valid data")
 for n in old+fresh:
  # Active weather alerts belong only on the separate warnings page.
  if n.get("source")=="Ilmatieteen laitos – säävaroitukset":continue
  try:published=dt.datetime.fromisoformat(n["date"]) if n.get("date") else now
  except ValueError:continue
  if published>now+dt.timedelta(hours=12):continue
  if not consumer_relevant(n):continue
  if not n.get("date"):continue
  key=n["link"].split("?")[0].rstrip("/")
  if key not in items or (not items[key].get("description") and n.get("description")):items[key]=n
 ordered=sorted((enrich_location(n) for n in items.values()),key=lambda n:n.get("date") or "",reverse=True)
 os.makedirs(os.path.dirname(OUTPUT),exist_ok=True)
 with open(ARCHIVE,"w",encoding="utf-8") as f:json.dump({"updated":now.isoformat(),"items":ordered},f,ensure_ascii=False,indent=2)
 recent=[n for n in ordered if now-dt.datetime.fromisoformat(n["date"])<=dt.timedelta(days=30)][:1500]
 with open(OUTPUT,"w",encoding="utf-8") as f:json.dump({"updated":now.isoformat(),"items":recent,"sources":[x[0] for x in SOURCES],"newly_fetched":len(fresh),"monitoring":monitoring,"coverage":coverage},f,ensure_ascii=False,indent=2)
 print("Saved",len(ordered),"authority headlines; new fetched",len(fresh))
if __name__=="__main__":main()
