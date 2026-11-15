"""Unit tests for the scheduled refresh's fail-closed publication gate."""
import datetime as dt
import hashlib
import json
import os
import tempfile
import unittest

from engine.refresh_gate import evaluate

NOW = dt.datetime(2026, 11, 15, 12, 0, tzinfo=dt.timezone.utc)
URLS = {
    "S1_season": "https://www.nba.com/stats/teams/advanced",
    "S4_schedule": "https://www.nba.com/schedule",
    "S5_injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "S8_standings": "https://www.nba.com/standings",
    "S9_team_traditional": "https://www.nba.com/stats/teams/traditional",
    "S10_team_opponent": "https://www.nba.com/stats/teams/opponent",
}
DIGEST = "a" * 64
PDF_BYTES = b"%PDF-1.7\nrefresh-gate-test\n"
PDF_DIGEST = hashlib.sha256(PDF_BYTES).hexdigest()


class RefreshGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.old_root = os.environ.get("NBA1_REPO_ROOT")
        os.environ["NBA1_REPO_ROOT"] = self.root
        os.makedirs(os.path.join(self.root, "data/raw/injury_pdfs"), exist_ok=True)
        pdf_rel = "data/raw/injury_pdfs/Injury-Report_2026-11-15_12_00PM__" + PDF_DIGEST + ".pdf"
        with open(os.path.join(self.root, pdf_rel), "wb") as pdf_file:
            pdf_file.write(PDF_BYTES)
        self.record = {
            "captured_at_utc": "2026-11-15T11:55:00Z",
            "failed": [],
            "changed": [],
            "source_checks": [
                {"key": k, "url": url, "checked_at_utc": "2026-11-15T11:55:00Z",
                 "http_status": 200, "bytes": 12345, "sha256": DIGEST}
                for k, url in URLS.items()
            ] + [{"key": "results_2026-11-15", "url": "https://www.nba.com/games?date=2026-11-15",
                  "checked_at_utc": "2026-11-15T11:55:00Z", "http_status": 200,
                  "sha256": DIGEST},
                 {"key": "results_2026-11-14", "url": "https://www.nba.com/games?date=2026-11-14",
                  "checked_at_utc": "2026-11-15T11:55:00Z", "http_status": 200,
                  "sha256": DIGEST},
                 {"key": "injury_pdf_probe", "checked_at_utc": "2026-11-15T11:55:00Z",
                  "results": [{"edition": "Injury-Report_2026-11-15_12_00PM.pdf",
                               "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_12_00PM.pdf",
                               "http_status": 200, "sha256": PDF_DIGEST,
                               "pdf_valid": True, "artifact_path": pdf_rel}]}],
        }
        for key, url in URLS.items():
            name = {
                "S1_season": "_capture_S1_season.json",
                "S4_schedule": "_capture_S4_schedule.json",
                "S5_injury_index": "_capture_S5_injury_index.json",
                "S8_standings": "_capture_S8_standings.json",
                "S9_team_traditional": "_capture_S9_team_traditional.json",
                "S10_team_opponent": "_capture_S10_team_opponent.json",
            }[key]
            payload = {"source_url": url, "page_sha256": DIGEST}
            if key == "S1_season":
                cols = ["team", "gp"]
                rows = [[f"Team {i:02d}", 1] for i in range(30)]
                payload.update(cols=cols, row_count=30, rows=rows)
            if key == "S4_schedule":
                payload["games"] = [{"game_id": "0022600001"}]
            with open(os.path.join(self.root, "data/raw", name), "w") as fh:
                json.dump(payload, fh)
        for key, filename in (("S8_standings", "standings.json"),
                              ("S9_team_traditional", "team_traditional.json"),
                              ("S10_team_opponent", "team_opponent.json")):
            source = URLS[key]
            payload = {"rows": [{"team": "Example", "value": 1}],
                       "verification": {"verified": True, "source_url": source,
                                        "source_sha256": DIGEST,
                                        "verified_at_utc": "2026-11-15T11:57:00Z"}}
            with open(os.path.join(self.root, "data/raw", filename), "w") as fh:
                json.dump(payload, fh)

        promotion_time = "2026-11-15T11:57:00Z"
        for filename, source, digest, rows in (
            ("schedule_upcoming.json", URLS["S4_schedule"], DIGEST,
             [{"game_id": "0022600001", "away": "AAA", "home": "BBB"}]),
            ("injuries.json",
             "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_12_00PM.pdf",
             PDF_DIGEST, [{"player": "Example Player", "status": "Available"}]),
        ):
            payload = {"rows": rows, "verification": {"verified": True,
                       "source_url": source, "source_sha256": digest,
                       "verified_at_utc": promotion_time}}
            with open(os.path.join(self.root, "data/raw", filename), "w") as fh:
                json.dump(payload, fh)

        with open(os.path.join(self.root, "data/raw/_capture_S1_season.json"), encoding="utf-8") as fh:
            advanced_capture = json.load(fh)
        with open(os.path.join(self.root, "data/raw/team_advanced.json"), "w") as fh:
            json.dump({"cols": advanced_capture["cols"],
                       "windows": [{"window_id": "season_to_date",
                                    "rows": advanced_capture["rows"]}]}, fh)

        for date in ("2026-11-14", "2026-11-15"):
            payload = {"snapshot_comparison": {"mismatches": [],
                       "promotion_candidates": [], "committed_finals_missed": []}}
            with open(os.path.join(self.root, f"data/raw/_capture_results_{date}.json"), "w") as fh:
                json.dump(payload, fh)

    def tearDown(self):
        self.tmp.cleanup()
        if self.old_root is None:
            os.environ.pop("NBA1_REPO_ROOT", None)
        else:
            os.environ["NBA1_REPO_ROOT"] = self.old_root

    def test_complete_current_verified_capture_set_passes(self):
        self.assertEqual(evaluate(self.record, NOW), [])

    def test_stale_run_is_blocked(self):
        self.record["captured_at_utc"] = "2026-11-14T00:00:00Z"
        errors = evaluate(self.record, NOW)
        self.assertTrue(any("stale" in e for e in errors))

    def test_non_official_host_is_blocked(self):
        self.record["source_checks"][0]["url"] = "https://example.com/stats"
        errors = evaluate(self.record, NOW)
        self.assertTrue(any("non-official" in e for e in errors))

    def test_changed_unpromoted_capture_is_blocked(self):
        self.record["changed"] = ["S9_team_traditional"]
        errors = evaluate(self.record, NOW)
        self.assertTrue(any("awaits verified promotion" in e for e in errors))

    def test_capture_hash_must_match_current_run(self):
        path = os.path.join(self.root, "data/raw/_capture_S8_standings.json")
        with open(path, "w") as stream:
            json.dump({"source_url": URLS["S8_standings"], "page_sha256": "b" * 64}, stream)
        errors = evaluate(self.record, NOW)
        self.assertTrue(any("digest does not match" in e for e in errors))

    def test_missing_pdf_or_source_blocks(self):
        self.record["source_checks"] = [c for c in self.record["source_checks"] if c["key"] != "injury_pdf_probe"]
        errors = evaluate(self.record, NOW)
        self.assertTrue(any("injury PDF" in e for e in errors))

    def test_tampered_archived_pdf_blocks(self):
        result = next(c for c in self.record["source_checks"] if c["key"] == "injury_pdf_probe")["results"][0]
        with open(os.path.join(self.root, result["artifact_path"]), "wb") as pdf_file:
            pdf_file.write(b"not the captured pdf")
        errors = evaluate(self.record, NOW)
        self.assertTrue(any("bytes do not match" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
