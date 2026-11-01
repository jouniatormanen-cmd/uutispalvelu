#!/usr/bin/env python3
"""Publish current FMI CAP alerts separately from incident news."""
import datetime as dt, email.utils, json, os, urllib.request, xml.etree.ElementTree as ET
ROOT=os.path.dirname(os.path.dirname(__file__))
OUT=os.path.join(ROOT,"viranomaiset","warnings.json")
URL="https://alerts.fmi.fi/cap/feed/rss_fi-FI.rss"
def child(node,name):
 for n in node.iter():
  if n.tag.split("}")[-1].lower()==name.lower() and n.text:return n.text.strip()
 return ""
def date(value):
 if not value:return None
 try:return dt.datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(dt.timezone.utc)
 except ValueError:
  try:return email.utils.parsedate_to_datetime(value).astimezone(dt.timezone.utc)
  except (ValueError,TypeError):return None
def main():
 now=dt.datetime.now(dt.timezone.utc)
 result={"updated":now.isoformat(),"source":"Ilmatieteen laitos","status":"unavailable","items":[]}
 try:
  req=urllib.request.Request(URL,headers={"User-Agent":"Tilanneuutiset/1.0","Accept":"application/rss+xml"})
  with urllib.request.urlopen(req,timeout=20) as response:raw=response.read(2500000)
  root=ET.fromstring(raw)
  for item in root.iter():
   if item.tag.split("}")[-1]!="item":continue
   title=child(item,"title");link=child(item,"link")
   description=child(item,"description")
   # RSS publication time is not the warning expiry time.
   # Never present an alert as active without a verified CAP expiry.
   expires=date(child(item,"expires"))
   starts=date(child(item,"onset")) or date(child(item,"effective"))
   kind=child(item,"msgType")
   if kind=="Cancel" or not expires or expires<=now or (starts and starts>now+dt.timedelta(days=5)):continue
   if title and link.startswith("https://"):
    result["items"].append({"title":title,"link":link,"description":description[:500],"starts":starts.isoformat() if starts else None,"expires":expires.isoformat()})
  result["status"]="ok"
 except Exception as exc:
  print("FMI warnings unavailable:",exc)
 os.makedirs(os.path.dirname(OUT),exist_ok=True)
 with open(OUT,"w",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2)
 print("Current verified-expiry warnings:",len(result["items"]),result["status"])
if __name__=="__main__":main()
