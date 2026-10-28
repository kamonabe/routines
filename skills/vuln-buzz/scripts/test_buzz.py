"""buzz.py の判定（decide）の試験。ネットワークには接続しない。

実行: python3 -m unittest discover -s skills/vuln-buzz/scripts
"""

import unittest
from datetime import datetime, timezone

from buzz import decide

# JST 15:56（定時の回ではない）
NOW = datetime(2026, 10, 28, 6, 56, tzinfo=timezone.utc)


def cand(cve, score, *ats):
    return {"cve": cve, "score": score, "signals": [{"name": f"s{i}", "at": a} for i, a in enumerate(ats)]}


def hn(points, date):
    return {"points": points, "date": date, "hn": "https://news.ycombinator.com/item?id=1", "title": "RCE in X"}


class Decide(unittest.TestCase):
    def test_nothing(self):
        d = decide([], [], [], NOW)
        self.assertFalse(d["full_run"])
        self.assertFalse(d["web_search"])

    def test_old_buzz_only_is_skipped(self):
        d = decide([cand("CVE-1", 6, "2026-10-27T19:00:00Z", None)], [hn(186, "2026-10-27T13:52:12Z")], [], NOW)
        self.assertFalse(d["full_run"])

    def test_fresh_signal_on_buzz_candidate(self):
        d = decide([cand("CVE-1", 4, "2026-10-28T15:30:00+09:00")], [], [], NOW)
        self.assertTrue(d["full_run"])
        self.assertTrue(d["web_search"])

    def test_fresh_signal_below_buzz_score_is_skipped(self):
        # score 3（KEV 追加だけ など）は騒ぎにしない
        d = decide([cand("CVE-1", 3, "2026-10-28T06:50:00Z")], [], [], NOW)
        self.assertFalse(d["full_run"])

    def test_fresh_hn_story(self):
        d = decide([], [hn(120, "2026-10-28T06:30:00Z")], [], NOW)
        self.assertTrue(d["full_run"])

    def test_small_fresh_hn_story_is_skipped(self):
        d = decide([], [hn(99, "2026-10-28T06:30:00Z")], [], NOW)
        self.assertFalse(d["full_run"])

    def test_scheduled_hours(self):
        for utc_hour, expected in [(15, True), (21, True), (3, True), (9, True), (10, False)]:
            now = datetime(2026, 10, 28, utc_hour, 56, tzinfo=timezone.utc)
            self.assertEqual(decide([], [], [], now)["full_run"], expected, utc_hour)

    def test_all_sources_failed(self):
        errors = ["kev: x", "hn: x", "poc-in-github: x", "nuclei: x", "nvd: x"]
        d = decide([], [], errors, NOW)
        self.assertTrue(d["full_run"])
        self.assertFalse(d["web_search"])

    def test_partial_failure_alone_does_not_run(self):
        self.assertFalse(decide([], [], ["nvd: timeout"], NOW)["full_run"])


if __name__ == "__main__":
    unittest.main()
