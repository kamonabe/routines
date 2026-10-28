#!/usr/bin/env python3
"""AI×開発（aidev）の候補を集める: AI コーディングツールの更新と、開発手法・実践例の記事。

使い方: python3 collect_aidev.py raw.json [時間=24]
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
from email.utils import parsedate_to_datetime

HOURS = int(sys.argv[2]) if len(sys.argv) > 2 else 24
NOW = datetime.now(timezone.utc)
SINCE = NOW - timedelta(hours=HOURS)
UA = {"User-Agent": "Mozilla/5.0 (ai-dev-news digest)"}


def get(url, as_json=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        data = r.read()
    return json.loads(data) if as_json else data.decode("utf-8", "replace")


def in_window(dt):
    return dt is not None and SINCE <= dt <= NOW + timedelta(minutes=5)


out = {"since": SINCE.isoformat(), "until": NOW.isoformat(), "tools": [], "pages": [], "articles": [], "errors": []}


def guard(name, fn):
    try:
        fn()
    except Exception as e:  # noqa: BLE001 取得元ごとに失敗を記録して続ける
        out["errors"].append(f"{name}: {e}")


def npm(pkg, label):
    d = get("https://registry.npmjs.org/" + pkg.replace("/", "%2F"), True)
    for ver, ts in d["time"].items():
        if ver in ("created", "modified") or re.search(r"-(alpha|beta|rc|nightly|preview)", ver):
            continue
        if in_window(datetime.fromisoformat(ts.replace("Z", "+00:00"))):
            out["tools"].append({"tool": label, "version": ver, "date": ts})


def claude_changelog():
    md = get("https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md")
    vers = {t["version"] for t in out["tools"] if t["tool"] == "Claude Code"}
    for sec in re.split(r"\n(?=## )", md):
        m = re.match(r"## (\S+)", sec)
        if m and m.group(1) in vers:
            for t in out["tools"]:
                if t["tool"] == "Claude Code" and t["version"] == m.group(1):
                    t["notes"] = sec[:1500]


def html_text(url, maxlen=6000):
    h = get(url)
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"<[^>]+>", "\n", h))[:maxlen]


def pages():
    for label, url in [("Kiro", "https://kiro.dev/changelog/"), ("Cursor", "https://cursor.com/changelog")]:
        guard(label, lambda label=label, url=url: out["pages"].append({"tool": label, "url": url, "head": html_text(url)}))


def copilot():
    root = ET.fromstring(get("https://github.blog/changelog/feed/"))
    for it in root.iter("item"):
        title = it.findtext("title") or ""
        dt = parsedate_to_datetime(it.findtext("pubDate"))
        if in_window(dt) and re.search(r"copilot|agent|model", title, re.I):
            out["tools"].append({"tool": "GitHub Copilot", "title": title, "url": it.findtext("link"),
                                 "date": dt.isoformat()})


seen = set()


def add(a):
    if a["url"] in seen:
        return
    seen.add(a["url"])
    out["articles"].append(a)


def zenn():
    for topic in ["claudecode", "kiro", "cursor", "githubcopilot", "codex", "aiagent", "ai", "llm", "mcp", "specdriven"]:
        try:
            root = ET.fromstring(get(f"https://zenn.dev/topics/{topic}/feed"))
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"zenn {topic}: {e}")
            continue
        for it in root.iter("item"):
            dt = parsedate_to_datetime(it.findtext("pubDate"))
            if in_window(dt):
                add({"src": "Zenn", "topic": topic, "title": it.findtext("title"), "url": it.findtext("link"),
                     "date": dt.isoformat(), "desc": (it.findtext("description") or "")[:200]})


def qiita():
    tags = ["ClaudeCode", "Kiro", "Cursor", "GitHubCopilot", "Codex", "AIエージェント", "AI駆動開発", "仕様駆動開発", "MCP", "生成AI"]
    q = " OR ".join(f"tag:{t}" for t in tags)
    url = "https://qiita.com/api/v2/items?" + urllib.parse.urlencode(
        {"per_page": 100, "query": f"({q}) created:>={SINCE.date().isoformat()}"})
    for it in get(url, True):
        if in_window(datetime.fromisoformat(it["created_at"])):
            add({"src": "Qiita", "title": it["title"], "url": it["url"], "date": it["created_at"],
                 "likes": it.get("likes_count", 0), "tags": [t["name"] for t in it.get("tags", [])]})


def hn():
    ts = int(SINCE.timestamp())
    for q in ["claude code", "cursor", "copilot", "codex", "coding agent", "AI coding", "spec-driven", "kiro", "agentic",
              "LLM code", "MCP"]:
        url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
            {"query": q, "tags": "story", "numericFilters": f"created_at_i>{ts},points>=20", "hitsPerPage": 20})
        for h in get(url, True)["hits"]:
            add({"src": "HN", "title": h["title"], "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
                 "points": h["points"], "date": h["created_at"]})
        time.sleep(0.3)


def hatena():
    # はてなブックマーク テクノロジー人気エントリー(RSS 1.0)。Xなどで話題になった記事を拾う目的。
    # 人気入りは公開から遅れることがあるので、公開72時間以内のものを対象にする。
    def ln(e):
        return e.tag.rsplit("}", 1)[-1]
    root = ET.fromstring(get("https://b.hatena.ne.jp/hotentry/it.rss"))
    for it in root.iter():
        if ln(it) != "item":
            continue
        f = {ln(c): (c.text or "").strip() for c in it}
        url = f.get("link", "")
        try:
            dt = datetime.fromisoformat(f.get("date", ""))
        except ValueError:
            continue
        if not url or dt < NOW - timedelta(hours=72):
            continue
        n = int(f.get("bookmarkcount") or 0)
        hit = next((a for a in out["articles"] if a["url"] == url), None)
        if hit:
            hit["hatebu"] = n
            continue
        add({"src": "はてブ", "title": f.get("title", ""), "url": url, "date": dt.isoformat(), "hatebu": n,
             "desc": f.get("description", "")[:200]})


guard("npm claude-code", lambda: npm("@anthropic-ai/claude-code", "Claude Code"))
guard("npm codex", lambda: npm("@openai/codex", "Codex CLI"))
guard("npm gemini-cli", lambda: npm("@google/gemini-cli", "Gemini CLI"))
guard("claude changelog", claude_changelog)
pages()
guard("copilot", copilot)
guard("zenn", zenn)
guard("qiita", qiita)
guard("hn", hn)
guard("hatena", hatena)
out["counts"] = {"articles": dict(Counter(a["src"] for a in out["articles"])), "tool_updates": len(out["tools"])}
with open(sys.argv[1], "w") as fp:
    json.dump(out, fp, ensure_ascii=False, indent=1)
print(out["counts"], "errors:", out["errors"])
