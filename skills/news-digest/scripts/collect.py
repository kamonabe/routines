#!/usr/bin/env python3
"""はてなブックマークの人気エントリーと Hacker News から、ニュースの候補を集める。

使い方: python3 collect.py <it|ai|world|game> raw.json [時間=24]
AI×開発（aidev）は別のスクリプト collect_aidev.py を使う。
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone

SECTION = sys.argv[1]
OUT = sys.argv[2]
HOURS = int(sys.argv[3]) if len(sys.argv) > 3 else 24
NOW = datetime.now(timezone.utc)
SINCE = NOW - timedelta(hours=HOURS)
UA = {"User-Agent": "Mozilla/5.0 (news digest)"}
AI_RE = re.compile(r"\b(AI|LLM|GPT|ChatGPT|Claude|Gemini|Copilot|OpenAI|Anthropic|DeepMind|agent|Llama|Mistral|DeepSeek|Grok|Sora|Kimi|Qwen|Gemma|Midjourney|NVIDIA)\b|生成AI|人工知能|機械学習|大規模言語モデル|エージェント", re.I)


def get(url, as_json=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        d = r.read()
    return json.loads(d) if as_json else d.decode("utf-8", "replace")


out = {"section": SECTION, "since": SINCE.isoformat(), "until": NOW.isoformat(), "articles": [], "errors": []}
seen = {}


def add(a):
    if a["url"] in seen:
        seen[a["url"]].setdefault("also", []).append(a["src"])
        return
    seen[a["url"]] = a
    out["articles"].append(a)


def guard(name, fn):
    try:
        fn()
    except Exception as e:  # noqa: BLE001 取得元ごとに失敗を記録して続ける
        out["errors"].append(f"{name}: {e}")


def hatena(feed, label, min_users=0, hours=72, filt=None):
    # はてブの人気エントリーは公開から遅れて入るので、公開72時間以内を対象にする
    def ln(e):
        return e.tag.rsplit("}", 1)[-1]
    root = ET.fromstring(get(feed))
    for it in root.iter():
        if ln(it) != "item":
            continue
        f = {ln(c): (c.text or "").strip() for c in it}
        try:
            dt = datetime.fromisoformat(f.get("date", ""))
        except ValueError:
            continue
        if dt < NOW - timedelta(hours=hours):
            continue
        n = int(f.get("bookmarkcount") or 0)
        if n < min_users:
            continue
        title = f.get("title", "")
        if filt and not filt(title + " " + f.get("description", "")):
            continue
        add({"src": label, "title": title, "url": f.get("link", ""), "date": dt.isoformat(), "users": n,
             "desc": f.get("description", "")[:160]})


def hn_front(filt=None, min_points=100):
    ts = int(SINCE.timestamp())
    url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
        {"tags": "story", "numericFilters": f"created_at_i>{ts},points>={min_points}", "hitsPerPage": 100})
    for h in get(url, True)["hits"]:
        t = h.get("title") or ""
        if filt and not filt(t):
            continue
        add({"src": "HN", "title": t, "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
             "hn": f"https://news.ycombinator.com/item?id={h['objectID']}", "points": h["points"],
             "comments": h.get("num_comments", 0), "date": h["created_at"]})


def hn_query(queries, min_points=30, filt=None):
    ts = int(SINCE.timestamp())
    for q in queries:
        url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
            {"query": q, "tags": "story", "numericFilters": f"created_at_i>{ts},points>={min_points}", "hitsPerPage": 30})
        for h in get(url, True)["hits"]:
            if filt and not filt(h.get("title") or ""):
                continue
            add({"src": "HN", "title": h.get("title") or "",
                 "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
                 "hn": f"https://news.ycombinator.com/item?id={h['objectID']}", "points": h["points"],
                 "comments": h.get("num_comments", 0), "date": h["created_at"]})
        time.sleep(0.3)


HB = "https://b.hatena.ne.jp/hotentry/"


def is_ai(s):
    return bool(AI_RE.search(s))


if SECTION == "it":
    guard("hatena it", lambda: hatena(HB + "it.rss", "はてブ"))
    guard("hn front", lambda: hn_front(filt=lambda t: not is_ai(t), min_points=150))
elif SECTION == "ai":
    guard("hatena it(AI)", lambda: hatena(HB + "it.rss", "はてブ", filt=is_ai))
    guard("hatena all(AI)", lambda: hatena(HB + "all.rss", "はてブ", filt=is_ai))
    guard("hatena search AI", lambda: hatena("https://b.hatena.ne.jp/q/%E7%94%9F%E6%88%90AI?mode=rss&sort=hot&users=50",
                                             "はてブ", hours=48))
    guard("hn ai", lambda: hn_query(["AI", "LLM", "OpenAI", "Anthropic", "Gemini", "GPT", "Claude", "DeepSeek",
                                     "model release"], min_points=80, filt=is_ai))
elif SECTION == "world":
    guard("hatena economics", lambda: hatena(HB + "economics.rss", "はてブ(政治と経済)"))
    guard("hatena social", lambda: hatena(HB + "social.rss", "はてブ(世の中)"))
    guard("hn world", lambda: hn_query(["war", "election", "government", "president", "climate", "sanctions", "EU",
                                        "China"], min_points=150, filt=lambda t: not is_ai(t)))
elif SECTION == "game":
    guard("hatena game", lambda: hatena(HB + "game.rss", "はてブ(アニメとゲーム)"))
    guard("hn game", lambda: hn_query(["game", "Nintendo", "PlayStation", "Xbox", "Steam", "Valve"], min_points=80,
                                      filt=lambda t: re.search(r"\b(game|gaming|Nintendo|PlayStation|Xbox|Steam|Valve|Switch)\b",
                                                               t, re.I)))
else:
    sys.exit(f"未知のセクション: {SECTION}（it / ai / world / game）")

out["articles"].sort(key=lambda a: -(a.get("users", 0) + a.get("points", 0)))
out["counts"] = dict(Counter(a["src"] for a in out["articles"]))
with open(OUT, "w") as fp:
    json.dump(out, fp, ensure_ascii=False, indent=1)
print(out["counts"], "errors:", out["errors"])
