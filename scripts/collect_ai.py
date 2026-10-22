#!/usr/bin/env python3
"""Hourly AI intelligence candidate collector. Official GitHub releases verified; RSS leads unverified."""
import datetime as dt
import email.utils
import hashlib
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "ai.json"
TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(dt.timezone.utc)
UA = {"User-Agent": "AwareWave-Intelligence/1.0 (public-source-monitor)", "Accept": "application/vnd.github+json"}
REPOS = [
    ("anthropic", "anthropics/claude-code"),
    ("openai", "openai/codex"),
    ("google", "google-gemini/gemini-cli"),
]
SEARCHES = {
    "anthropic": [
        ('benefit', 'site:anthropic.com ("Claude for Startups" OR "startup credits" OR "free Claude" OR "Claude Team")'),
        ('update', 'site:anthropic.com/news Claude model API release'),
    ],
    "openai": [
        ('benefit', 'site:openai.com (startup credits OR free trial OR Codex promotion)'),
        ('update', 'site:openai.com/index/ model Codex API announcement'),
    ],
    "google": [
        ('benefit', 'site:cloud.google.com (startup credits OR Gemini free trial OR startup program)'),
        ('update', 'site:blog.google/technology/ai/ Gemini update'),
    ],
    "xai": [
        ('benefit', 'site:x.ai (free trial OR credits OR promotion)'),
        ('update', 'site:x.ai/news Grok API'),
    ],
    "perplexity": [
        ('benefit', 'site:perplexity.ai (free trial OR credits OR promotion)'),
        ('update', 'site:perplexity.ai/hub/blog API model'),
    ],
}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=18) as r:
        return r.read()

def clean(text):
    return re.sub(r"<[^>]+>", "", html.unescape(text or "")).strip()

def item_id(url):
    return hashlib.sha256(url.encode()).hexdigest()[:20]

def github_releases(brand, repo):
    url = "https://api.github.com/repos/" + repo + "/releases?per_page=5"
    results = []
    for release in json.loads(get(url)):
        link = release.get("html_url", "")
        if release.get("draft") or not link.startswith("https://github.com/"):
            continue
        date = release.get("published_at") or release.get("created_at") or ""
        if not date:
            continue
        published = dt.datetime.fromisoformat(date.replace("Z", "+00:00"))
        if NOW - published > dt.timedelta(days=14):
            continue
        results.append(dict(id=item_id(link), type="update", brand=brand,
            title=clean(release.get("name") or release.get("tag_name") or "Release"),
            summary="官方 GitHub 版本發布；功能細節請閱讀原始 Release Notes。",
            source="GitHub · " + repo, url=link, published_at=date[:10],
            verification="official", eligibility="", deadline=""))
    return results

def news_candidates(brand, typ, query):
    params = urllib.parse.urlencode({"q": query + " when:7d", "hl": "en-US", "gl": "US", "ceid": "US:en"})
    url = "https://news.google.com/rss/search?" + params
    root = ET.fromstring(get(url))
    result = []
    for entry in root.findall("./channel/item"):
        link = (entry.findtext("link") or "").strip()
        title = clean(entry.findtext("title"))
        if not title or not link.startswith("https://"):
            continue
        rawdate = entry.findtext("pubDate") or ""
        try:
            published = email.utils.parsedate_to_datetime(rawdate)
            if published.tzinfo is None:
                published = published.replace(tzinfo=dt.timezone.utc)
            if NOW - published > dt.timedelta(days=8):
                continue
            date = published.astimezone(TZ).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            date = "日期待確認"
        result.append(dict(id=item_id(link), type=typ, brand=brand, title=title,
            summary="Google News 搜尋候選線索；尚未獨立核對官方公告、活動是否仍有效或適用資格。",
            source=clean(entry.findtext("source")) or "Google News",
            url=link, published_at=date, verification="unverified",
            eligibility="台灣／未登記公司／個人獨立開發者是否適用：尚未確認。",
            deadline="未確認"))
        if len(result) >= 4:
            break
    return result

def main():
    previous = {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    rows = []
    failures = []
    for brand, repo in REPOS:
        try:
            rows.extend(github_releases(brand, repo))
        except Exception as exc:
            failures.append(repo + ": " + str(exc))
    for brand, searches in SEARCHES.items():
        for typ, query in searches:
            try:
                rows.extend(news_candidates(brand, typ, query))
            except Exception as exc:
                failures.append(brand + "/" + typ + ": " + str(exc))
    # Preserve recent prior records if a feed is temporarily unavailable.
    prior = previous.get("items", [])
    cutoff = (NOW - dt.timedelta(days=14)).date().isoformat()
    seen = set()
    output = []
    for row in rows + prior:
        if row.get("id") in seen or row.get("published_at", "") < cutoff:
            continue
        if row.get("brand") not in SEARCHES or row.get("type") not in ("update", "benefit"):
            continue
        seen.add(row["id"])
        output.append(row)
    output.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    result = dict(updated_at=NOW.astimezone(TZ).strftime("%Y-%m-%d %H:%M Asia/Taipei"),
        notice="GitHub 官方版本可標示已證實；Google News 搜尋結果僅為待查證線索，不代表官方確認或可申請。",
        failures=failures, items=output[:150])
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("AI intelligence records:", len(result["items"]), "source failures:", len(failures))
    for failure in failures:
        print("WARNING:", failure)

if __name__ == "__main__":
    main()
