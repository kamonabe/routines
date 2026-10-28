#!/usr/bin/env python3
"""vuln-buzz: 脆弱性の「騒ぎ」のシグナルを集め、この回で詳しく調べる必要があるかを判定する。

使い方:
    python3 buzz.py raw.json [時間=48]

raw.json に候補とシグナルを書き、標準出力に件数と判定（decision）を出す。
判定（decision）:
    full_run   true なら SKILL.md の手順 2 以降（Slack の既出確認・判定・投稿）に進む。false なら何もせずに終了してよい
    web_search true なら手順 3 の補助の Web 検索を行う
    reasons    判定の理由

full_run になるのは次のどれか:
    - 定時の回（JST の 0・6・12・18 時台）。新しいシグナルを取りこぼしても、最大 6 時間で拾い直すため
    - 騒ぎの条件（score 4 以上、または HN 100pt 以上の脆弱性の話題）を満たし、
      直近 FRESH 以内に新しいシグナルが付いた候補がある
    - 取得元がすべて失敗した（失敗の通知を出すかを判断するため）
"""

import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

NOW = datetime.now(timezone.utc)
SINCE = NOW - timedelta(hours=48)  # main() で引数の時間に置き換える
JST = timezone(timedelta(hours=9))
FRESH = timedelta(minutes=75)  # 毎時の実行。起動の揺れの分だけ前の回と重ねる（取りこぼしは定時の回で拾い直す）
FULL_RUN_HOURS_JST = {0, 6, 12, 18}
BUZZ_SCORE = 4
BUZZ_HN_POINTS = 100
UA = {"User-Agent": "Mozilla/5.0 (vuln-buzz watcher)"}
CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.I)
VULN_WORDS = re.compile(
    r"\b(cve|vulnerab\w*|exploit\w*|rce|remote code|zero[- ]?day|0[- ]?day|backdoor|patch(ed|es)? now|"
    r"security (flaw|bug|update|advisory)|bypass|takeover|ransomware)\b", re.I)
SOURCES = ["kev", "hn", "poc-in-github", "nuclei", "nvd"]


def get(url, as_json=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        d = r.read()
    return json.loads(d) if as_json else d.decode("utf-8", "replace")


out = {"since": SINCE.isoformat(), "until": NOW.isoformat(), "cves": {}, "hn_vuln_stories": [], "errors": []}


def cve(cid):
    return out["cves"].setdefault(cid.upper(), {"signals": [], "score": 0})


def sig(cid, name, pts, at=None, **kw):
    """シグナルを足す。at はそのシグナルが出た時刻（ISO 8601）。分からなければ None。"""
    c = cve(cid)
    if any(s["name"] == name for s in c["signals"]):
        return
    c["signals"].append({"name": name, "at": at, **kw})
    c["score"] += pts


def guard(name, fn):
    try:
        fn()
    except Exception as e:  # noqa: BLE001 取得元ごとに失敗を記録して続ける
        out["errors"].append(f"{name}: {e}")


def kev():
    d = get("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json", True)
    # 追加日は日付しか無い。カタログの最終更新時刻（dateReleased）を、最新の追加日の分の時刻として使う
    released = d.get("dateReleased")
    latest = max((v["dateAdded"] for v in d["vulnerabilities"]), default="")
    for v in d["vulnerabilities"]:
        if v["dateAdded"] >= SINCE.date().isoformat():
            at = released if v["dateAdded"] == latest else None
            sig(v["cveID"], "KEV追加", 3, at=at, date=v["dateAdded"], vendor=v["vendorProject"],
                product=v["product"], name_=v["vulnerabilityName"])


def hn():
    ts = int(SINCE.timestamp())
    seen = set()
    for q in ["CVE", "vulnerability", "exploit", "RCE", "zero-day", "0day", "security flaw", "patch"]:
        url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
            {"query": q, "tags": "story", "numericFilters": f"created_at_i>{ts},points>=15", "hitsPerPage": 50})
        for h in get(url, True)["hits"]:
            if h["objectID"] in seen:
                continue
            seen.add(h["objectID"])
            title = h.get("title") or ""
            if not (CVE_RE.search(title) or VULN_WORDS.search(title)):
                continue
            item = {"title": title, "url": h.get("url") or "",
                    "hn": f"https://news.ycombinator.com/item?id={h['objectID']}",
                    "points": h.get("points", 0), "comments": h.get("num_comments", 0), "date": h["created_at"]}
            out["hn_vuln_stories"].append(item)
            for c in {m.upper() for m in CVE_RE.findall(title + " " + item["url"])}:
                pts = 3 if item["points"] >= 150 else 2 if item["points"] >= 50 else 1
                sig(c, "HN話題", pts, at=item["date"], points=item["points"], hn=item["hn"])
        time.sleep(0.3)
    out["hn_vuln_stories"].sort(key=lambda x: -x["points"])


def git_added(repo, name, pts, path_filter):
    d = tempfile.mkdtemp()
    since_day = (SINCE - timedelta(days=1)).date().isoformat()
    subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", f"--shallow-since={since_day}",
                    f"https://github.com/{repo}", d], check=True, timeout=180)
    log = subprocess.run(["git", "-C", d, "log", f"--since={SINCE.isoformat()}", "--diff-filter=A", "--name-only",
                          "--pretty=format:@%cI"], capture_output=True, text=True, check=True).stdout
    min_year = NOW.year - 1
    at = None
    for line in log.splitlines():
        if line.startswith("@"):
            at = line[1:]
            continue
        if not path_filter(line):
            continue
        for c in CVE_RE.findall(line):
            if int(c.split("-")[1]) >= min_year:
                sig(c, name, pts, at=at, path=line)


def nvd_critical():
    def fmt(t):
        return t.strftime("%Y-%m-%dT%H:%M:%S.000")
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0?" + urllib.parse.urlencode(
        {"pubStartDate": fmt(SINCE), "pubEndDate": fmt(NOW), "cvssV3Severity": "CRITICAL", "resultsPerPage": 200})
    for v in get(url, True).get("vulnerabilities", []):
        c = v["cve"]
        desc = next((d["value"] for d in c.get("descriptions", []) if d["lang"] == "en"), "")
        published = c.get("published")
        sig(c["id"], "NVD CRITICAL新規", 1, at=(published + "Z") if published and "Z" not in published else published,
            desc=desc[:200])


def epss():
    ids = list(out["cves"].keys())
    for i in range(0, len(ids), 80):
        d = get("https://api.first.org/data/v1/epss?cve=" + ",".join(ids[i:i + 80]), True)
        for r in d.get("data", []):
            c = out["cves"][r["cve"].upper()]
            e = float(r["epss"])
            c["epss"] = round(e, 4)
            c["epss_pct"] = round(float(r["percentile"]), 3)
            if e >= 0.1:
                c["score"] += 1
                c["signals"].append({"name": f"EPSS {e:.2f}", "at": None})


def parse(s):
    if not s:
        return None
    try:
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def decide(candidates, hn_stories, errors, now):
    """この回で手順 2 以降に進むか（full_run）と、Web 検索をするか（web_search）を決める。"""
    reasons = []
    fresh_after = now - FRESH
    buzz = [c for c in candidates if c["score"] >= BUZZ_SCORE]
    fresh_cves = [c["cve"] for c in buzz
                  if any((parse(s.get("at")) or datetime.min.replace(tzinfo=timezone.utc)) >= fresh_after
                         for s in c["signals"])]
    big_hn = [s for s in hn_stories if s["points"] >= BUZZ_HN_POINTS]
    fresh_hn = [s["hn"] for s in big_hn if (parse(s["date"]) or now) >= fresh_after]
    scheduled = now.astimezone(JST).hour in FULL_RUN_HOURS_JST
    failed = {e.split(":", 1)[0] for e in errors}
    all_failed = all(s in failed for s in SOURCES)
    if scheduled:
        reasons.append("定時の回（JST 0・6・12・18 時台）")
    if fresh_cves:
        reasons.append("新しいシグナルの付いた候補: " + ", ".join(fresh_cves))
    if fresh_hn:
        reasons.append(f"新しい HN の話題 {len(fresh_hn)} 件")
    if all_failed:
        reasons.append("取得元がすべて失敗")
    full_run = bool(scheduled or fresh_cves or fresh_hn or all_failed)
    web_search = bool(scheduled or fresh_cves or fresh_hn)
    if not full_run:
        reasons.append(f"騒ぎの候補 {len(buzz)} 件・HN {len(big_hn)} 件はあるが、直近 {int(FRESH.total_seconds() // 60)} 分の新しいシグナルは無い"
                       if (buzz or big_hn) else "騒ぎの条件を満たす候補が無い")
    return {"full_run": full_run, "web_search": web_search, "reasons": reasons}


def main():
    global SINCE
    if len(sys.argv) < 2:
        sys.exit("使い方: python3 buzz.py raw.json [時間=48]")
    SINCE = NOW - timedelta(hours=int(sys.argv[2]) if len(sys.argv) > 2 else 48)
    out["since"] = SINCE.isoformat()
    guard("kev", kev)
    guard("hn", hn)
    guard("poc-in-github", lambda: git_added("nomi-sec/PoC-in-GitHub", "PoC初出(GitHub)", 2,
                                             lambda p: p.endswith(".json")))
    guard("nuclei", lambda: git_added("projectdiscovery/nuclei-templates", "nucleiテンプレート追加", 2,
                                      lambda p: p.endswith(".yaml") and "/cves/" in p))
    guard("nvd", nvd_critical)
    guard("epss", epss)
    ranked = sorted(out["cves"].items(), key=lambda kv: -kv[1]["score"])
    out["candidates"] = [{"cve": k, **v} for k, v in ranked if v["score"] >= 3][:30]
    out["counts"] = {"cves_seen": len(out["cves"]), "candidates": len(out["candidates"]),
                     "hn_vuln_stories": len(out["hn_vuln_stories"])}
    del out["cves"]
    out["hn_vuln_stories"] = out["hn_vuln_stories"][:25]
    out["decision"] = decide(out["candidates"], out["hn_vuln_stories"], out["errors"], NOW)
    with open(sys.argv[1], "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"counts": out["counts"], "errors": out["errors"], "decision": out["decision"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
