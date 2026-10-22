#!/usr/bin/env python3
"""Google News RSS HEADLINE INDEX only. Not fact checked and no generated analysis."""
import datetime as dt, hashlib, html, json, pathlib, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET, email.utils
ROOT=pathlib.Path(__file__).resolve().parents[1]
QUERY={
"tw-policy":"台灣 政策 法規 立法院","tw-economy":"台灣 經濟 出口 央行 物價","tw-tech":"台灣 科技 半導體 AI 台積電","tw-security":"台灣 國防 兩岸 安全","tw-safety":"台灣 災害 颱風 公共安全 交通","tw-social":"台灣 教育 社會 勞動",
"int-politics":"國際 外交 美國 中國 歐洲","int-security":"全球 安全 俄烏 中東 衝突","int-economy":"全球 經濟 金融 聯準會","int-tech":"全球 AI 科技 半導體 產品","int-energy":"全球 能源 氣候 電力 石油","int-regulation":"國際 AI 法規 隱私 監管"}
def clean(s):
 return re.sub(r"<[^>]*>","",html.unescape(s or "")).strip()
def normalized_title(title):
 title=re.sub(r"\\s*[-|｜]\\s*[^-|｜]{2,35}$","",title)
 title=re.sub(r"[^\\w\\u3400-\\u9fff]","",title.casefold())
 for w in ("最新消息","最新","快訊","新聞","報導","曝光","獨家","宣布","指出","今日","今天","台灣時間"):
  title=title.replace(w,"")
 return title
def grams(text):
 return {text[i:i+2] for i in range(max(0,len(text)-1))}
def duplicate(title,accepted):
 t=normalized_title(title)
 if not t:return True
 for other in accepted:
  if t==other:return True
  if min(len(t),len(other))>=12 and (t in other or other in t):return True
  a,b=grams(t),grams(other)
  if len(a|b) and len(a&b)/len(a|b)>=0.55:return True
 return False
def main():
 tz=dt.timezone(dt.timedelta(hours=8)); now=dt.datetime.now(tz); items=[]; seen=[]
 for category,term in QUERY.items():
  params=urllib.parse.urlencode({"q":term+" when:7d","hl":"zh-TW","gl":"TW","ceid":"TW:zh-Hant"})
  url="https://news.google.com/rss/search?"+params
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
   with urllib.request.urlopen(req,timeout=20) as res: root=ET.fromstring(res.read())
   count=0
   for entry in root.findall("./channel/item"):
    title=clean(entry.findtext("title")); link=(entry.findtext("link") or "").strip()
    if not title or not link.startswith("https://"):continue
    try: published=email.utils.parsedate_to_datetime(entry.findtext("pubDate"))
    except (ValueError,TypeError):continue
    if published.tzinfo is None:published=published.replace(tzinfo=dt.timezone.utc)
    if published<now-dt.timedelta(days=7):continue
    key=re.sub(r"\s+-\s+[^-]+$","",title).casefold()
    if key in seen:continue
    seen.add(key); count+=1
    items.append({"id":hashlib.sha256(key.encode()).hexdigest()[:20],"category":category,"title":title,
     "summary":"此為新聞聚合索引標題，未經獨立查核；請由來源連結確認原文。",
     "source":clean(entry.findtext("source")) or "Google News",
     "url":link,"published_at":published.astimezone(tz).strftime("%Y-%m-%d %H:%M"),
     "background":"","impact":"","follow_up":""})
    if count>=10:break
  except Exception as ex:print(category,type(ex).__name__,str(ex))
 data={"date":now.strftime("%Y-%m-%d"),"updated_at":now.strftime("%Y-%m-%d %H:%M Asia/Taipei"),
  "notice":"各領域最多10則、最近7天的新聞標題索引；跨媒體同事件採標題相似度去重，仍可能有漏網或誤判。不是已查證的深度新聞分析。","articles":items}
 (ROOT/"news.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Total headlines:",len(items))
if __name__=="__main__":main()
