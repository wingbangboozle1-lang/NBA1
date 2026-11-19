"""Unit tests for the scheduled refresh's fail-closed publication gate."""
import datetime as dt
import hashlib
import json
import os
import tempfile
import unittest

from engine.refresh_gate import evaluate, evaluate_with_report

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


class DeclarationTests(unittest.TestCase):
    """COORDINATION.md section 69: declared-unreadable sources.

    The property under test is narrow and load-bearing: a declaration may
    remove an UNSATISFIABLE snapshot requirement, and may never do anything
    else. Each test pins one of the ways that could go wrong.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.old_root = os.environ.get("NBA1_REPO_ROOT")
        os.environ["NBA1_REPO_ROOT"] = self.root
        raw = os.path.join(self.root, "data/raw")
        os.makedirs(os.path.join(raw, "injury_pdfs"), exist_ok=True)
        pdf_rel = "data/raw/injury_pdfs/Injury-Report_2026-11-15_12_00PM__" + PDF_DIGEST + ".pdf"
        with open(os.path.join(self.root, pdf_rel), "wb") as fh:
            fh.write(PDF_BYTES)
        urls = {
            "S1_season": "https://www.nba.com/stats/teams/advanced",
            "S4_schedule": "https://www.nba.com/schedule",
            "S5_injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
            "S8_standings": "https://www.nba.com/standings",
            "S9_team_traditional": "https://www.nba.com/stats/teams/traditional",
            "S10_team_opponent": "https://www.nba.com/stats/teams/opponent",
        }
        self.record = {
            "captured_at_utc": "2026-11-15T11:55:00Z",
            "failed": [],
            "changed": [],
            "source_checks": [
                {"key": k, "url": u, "checked_at_utc": "2026-11-15T11:55:00Z",
                 "http_status": 200, "bytes": 12345, "sha256": DIGEST}
                for k, u in urls.items()
            ] + [
                {"key": "results_2026-11-15", "url": "https://www.nba.com/games?date=2026-11-15",
                 "checked_at_utc": "2026-11-15T11:55:00Z", "http_status": 200, "sha256": DIGEST},
                {"key": "results_2026-11-14", "url": "https://www.nba.com/games?date=2026-11-14",
                 "checked_at_utc": "2026-11-15T11:55:00Z", "http_status": 200, "sha256": DIGEST},
                {"key": "injury_pdf_probe", "checked_at_utc": "2026-11-15T11:55:00Z",
                 "results": [{"edition": "Injury-Report_2026-11-15_12_00PM.pdf",
                              "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_12_00PM.pdf",
                              "http_status": 200, "sha256": PDF_DIGEST,
                              "pdf_valid": True, "artifact_path": pdf_rel}]},
            ],
        }
        for key, url in urls.items():
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
            # S8/S9/S10 captures deliberately carry NO rows: that is what an
            # unparsed client-rendered page produces, and it is the premise of
            # every declaration test.
            with open(os.path.join(raw, name), "w") as fh:
                json.dump(payload, fh)
        for key, name in (("S8_standings", "_capture_evidence_S8_standings.json"),
                          ("S9_team_traditional", "_capture_evidence_S9_team_traditional.json"),
                          ("S10_team_opponent", "_capture_evidence_S10_team_opponent.json")):
            # Shape copied from the real evidence records in data/raw: the
            # source_url is present, which is what lets the gate prove a
            # declared source's response came from the official URL this run.
            with open(os.path.join(raw, name), "w") as fh:
                json.dump({"status": "parse_failed", "source_url": urls[key],
                           "captured_at_utc": "2026-11-15T11:55:00Z",
                           "problems": ["html_table: no header row with a Team column found"]}, fh)
        # Promoted inputs the pipeline really consumes, plus NO standings /
        # traditional / opponent snapshot: the terminal state on main.
        for filename, source, digest, rows in (
            ("schedule_upcoming.json", urls["S4_schedule"], DIGEST,
             [{"game_id": "0022600001", "away": "AAA", "home": "BBB"}]),
            ("injuries.json",
             "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_12_00PM.pdf",
             PDF_DIGEST, [{"player": "Example Player", "status": "Available"}]),
        ):
            payload = {"rows": rows, "verification": {"verified": True,
                       "source_url": source, "source_sha256": digest,
                       "verified_at_utc": "2026-11-15T11:57:00Z"}}
            with open(os.path.join(raw, filename), "w") as fh:
                json.dump(payload, fh)
        with open(os.path.join(raw, "_capture_S1_season.json"), encoding="utf-8") as fh:
            advanced_capture = json.load(fh)
        with open(os.path.join(raw, "team_advanced.json"), "w") as fh:
            json.dump({"cols": advanced_capture["cols"],
                       "windows": [{"window_id": "season_to_date",
                                    "rows": advanced_capture["rows"]}]}, fh)
        for date in ("2026-11-14", "2026-11-15"):
            payload = {"snapshot_comparison": {"mismatches": [],
                       "promotion_candidates": [], "committed_finals_missed": []}}
            with open(os.path.join(raw, f"_capture_results_{date}.json"), "w") as fh:
                json.dump(payload, fh)

    def tearDown(self):
        self.tmp.cleanup()
        if self.old_root is None:
            os.environ.pop("NBA1_REPO_ROOT", None)
        else:
            os.environ["NBA1_REPO_ROOT"] = self.old_root

    def _declare(self, keys=("S8_standings", "S9_team_traditional", "S10_team_opponent"),
                 expires="2026-12-19T00:00:00Z", **extra):
        entries = []
        for key in keys:
            entry = {"source_key": key,
                     "required_snapshot": f"data/raw/{key}.json",
                     "expires_at_utc": expires,
                     "review_flag": "F1",
                     "reason": "client-rendered page proved by committed evidence"}
            entry.update(extra)
            entries.append(entry)
        with open(os.path.join(self.root, "data/raw/unreadable_sources.json"), "w") as fh:
            json.dump({"declarations": entries}, fh)

    def test_without_a_declaration_the_three_snapshots_block(self):
        errors, report = evaluate_with_report(self.record, NOW)
        blocking = [e for e in errors if "lacks structured, verified promoted data" in e]
        self.assertEqual(len(blocking), 3, errors)
        self.assertEqual(report["declarations_applied"], [])

    def test_live_declaration_lets_the_gate_pass_and_is_reported(self):
        self._declare()
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertEqual(errors, [], errors)
        applied = {d["source_key"] for d in report["declarations_applied"]}
        self.assertEqual(applied,
                         {"S8_standings", "S9_team_traditional", "S10_team_opponent"})
        # The declaration is surfaced with its expiry and evidence, so a green
        # gate on a declaration cannot be mistaken for a green gate on data.
        for entry in report["declarations_applied"]:
            self.assertEqual(entry["expires_at_utc"], "2026-12-19T00:00:00Z")
            self.assertTrue(entry["evidence"].endswith(".json"))

    def test_expired_declaration_blocks_again(self):
        self._declare(expires="2026-11-15T11:00:00Z")   # one hour before NOW
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("lacks structured, verified promoted data" in e for e in errors))
        self.assertEqual(report["declarations_applied"], [])
        self.assertTrue(any("EXPIRED" in w for w in report["warnings"]), report["warnings"])

    def test_declaration_is_refused_once_the_capture_parses_rows(self):
        """The anti-rot rule: if the page becomes readable, the gate must fail."""
        self._declare()
        path = os.path.join(self.root, "data/raw/_capture_S8_standings.json")
        with open(path) as fh:
            payload = json.load(fh)
        payload["rows"] = [{"team": "AAA", "w": 1, "l": 0}]
        with open(path, "w") as fh:
            json.dump(payload, fh)
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("S8_standings lacks structured" in e for e in errors), errors)
        self.assertTrue(any("DECLARATION STALE" in w for w in report["warnings"]),
                        report["warnings"])

    def test_declaration_without_evidence_on_disk_is_refused(self):
        self._declare()
        os.remove(os.path.join(self.root,
                               "data/raw/_capture_evidence_S9_team_traditional.json"))
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("S9_team_traditional lacks structured" in e for e in errors))
        self.assertTrue(any("no bounded parse-failure evidence" in w
                            for w in report["warnings"]), report["warnings"])

    def test_declaration_for_a_source_not_checked_this_run_is_refused(self):
        self._declare()
        self.record["source_checks"] = [c for c in self.record["source_checks"]
                                        if c["key"] != "S10_team_opponent"]
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("S10_team_opponent" in e for e in errors))
        self.assertTrue(any("not checked at HTTP 200" in w for w in report["warnings"]))

    def test_declaration_cannot_mask_a_source_outside_the_required_set(self):
        self._declare(keys=("S7_players",))
        errors, report = evaluate_with_report(self.record, NOW)
        # S7 was never required, so declaring it changes nothing at all.
        self.assertEqual(report["declarations_applied"], [])
        self.assertTrue(any("not a source this gate requires" in w
                            for w in report["warnings"]))
        self.assertEqual(len([e for e in errors
                              if "lacks structured, verified promoted data" in e]), 3)

    def test_declaration_evidence_without_its_source_url_blocks(self):
        """The evidence must prove the response, not merely exist."""
        self._declare()
        path = os.path.join(self.root, "data/raw/_capture_evidence_S10_team_opponent.json")
        with open(path, "w") as fh:
            json.dump({"status": "parse_failed",
                       "problems": ["no header row with a Team column found"]}, fh)
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("S10_team_opponent" in e and "provenance URL mismatch" in e
                            for e in errors), errors)

    def test_a_stale_rows_bearing_capture_does_not_excuse_the_digest(self):
        """A declared source that DID parse rows is not excused at all."""
        self._declare()
        path = os.path.join(self.root, "data/raw/_capture_S9_team_traditional.json")
        with open(path) as fh:
            payload = json.load(fh)
        payload["rows"] = [{"team": "AAA"}]
        with open(path, "w") as fh:
            json.dump(payload, fh)
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("DECLARATION STALE" in w for w in report["warnings"]))
        # The point is not WHICH error appears, it is that the requirement
        # comes back the moment the page proves readable. Both the missing
        # snapshot and a mismatched digest are acceptable news; silence is not.
        self.assertTrue(any("S9_team_traditional" in e for e in errors), errors)

    def test_a_wildly_overlong_expiry_is_refused(self):
        self._declare(expires="2030-01-01T00:00:00Z")
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertEqual(report["declarations_applied"], [])
        self.assertTrue(any("days out" in w for w in report["warnings"]))

    def test_malformed_register_is_ignored_not_trusted(self):
        with open(os.path.join(self.root, "data/raw/unreadable_sources.json"), "w") as fh:
            fh.write("{not json")
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertEqual(report["declarations_applied"], [])
        self.assertEqual(len([e for e in errors
                              if "lacks structured, verified promoted data" in e]), 3)

    def test_a_declaration_never_relaxes_freshness_or_provenance(self):
        """The declaration is narrow: unrelated gate failures still block."""
        self._declare()
        self.record["captured_at_utc"] = "2026-11-14T00:00:00Z"
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("stale" in e for e in errors))


class Section77Tests(unittest.TestCase):
    """COORDINATION.md section 77 - runner-unreadable, agent-readable sources.

    S1_season is readable by the agent's fetch channel but unreachable from a
    GitHub Actions runner (three measured dead routes). Two rules keep the
    declaration honest rather than permissive:
      * a companion failure-only declaration (S2_train) excuses only its own
        `failed` entry;
      * while S1 is declared, the consumed team_advanced.json must be a
        session read inside the freshness bound - a declaration excuses the
        parse, never the input.
    """

    setUp = DeclarationTests.setUp
    tearDown = DeclarationTests.tearDown
    _declare = DeclarationTests._declare

    def _declare_s1(self, keys=("S1_season",), with_evidence=True):
        entries = []
        for key in keys:
            entry = {"source_key": key,
                     "required_snapshot": "data/raw/team_advanced.json",
                     "expires_at_utc": "2026-12-19T00:00:00Z",
                     "review_flag": "F-70D-01",
                     "reason": "runner-side parse terminal (three dead routes)"}
            if with_evidence:
                entry["evidence"] = [f"data/raw/_capture_evidence_{key}.json"]
            entries.append(entry)
        with open(os.path.join(self.root, "data/raw/unreadable_sources.json"),
                  "w") as fh:
            json.dump({"declarations": entries}, fh)
        if with_evidence:
            for key in keys:
                with open(os.path.join(
                        self.root, f"data/raw/_capture_evidence_{key}.json"),
                        "w") as fh:
                    json.dump({"status": "parse_failed",
                               "source_url": URLS.get(key) or
                               "https://www.nba.com/stats/teams/advanced"
                               "?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026"
                               "&SeasonType=Regular+Season"}, fh)

    def _break_s1_parse(self):
        # The fetcher writes the structured capture only `if rows:`; on a
        # runner it never exists at all. Removing it reproduces the runner.
        os.remove(os.path.join(self.root, "data/raw/_capture_S1_season.json"))

    def _write_team_advanced(self, verified_at):
        payload = {"cols": ["team", "gp"],
                   "windows": [{"window_id": "season_to_date", "rows": []}]}
        if verified_at is not None:
            payload["verification"] = {
                "verified": True, "verified_at_utc": verified_at,
                "verified_by": "arena/70d0e760-nba1 (platform web-fetch channel)"}
        with open(os.path.join(self.root, "data/raw/team_advanced.json"),
                  "w") as fh:
            json.dump(payload, fh)

    def test_declared_s1_with_a_fresh_session_read_passes_and_names_it(self):
        self._declare_s1()
        self._break_s1_parse()
        self._write_team_advanced("2026-11-15T10:00:00Z")  # 2h before NOW
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertEqual([], [e for e in errors if "advanced" in e
                              or "S1_season" in e
                              or "structured capture" in e], errors)
        self.assertTrue(any("within the 72h bound" in w
                            for w in report["warnings"]), report["warnings"])
        self.assertIn("S1_season",
                      [d["source_key"] for d in report["declarations_applied"]])

    def test_stale_session_read_blocks_with_the_read_time_printed(self):
        self._declare_s1()
        self._break_s1_parse()
        self._write_team_advanced("2026-11-12T10:00:00Z")  # 74h before NOW
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("session-read freshness bound" in e
                            and "2026-11-12T10:00:00Z" in e for e in errors),
                        errors)

    def test_input_without_a_verification_block_blocks(self):
        self._declare_s1()
        self._break_s1_parse()
        self._write_team_advanced(None)
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("no explicit session-read verification block" in e
                            for e in errors), errors)

    def test_freshness_bound_is_configurable(self):
        self._declare_s1()
        self._break_s1_parse()
        self._write_team_advanced("2026-11-15T10:00:00Z")  # 2h before NOW
        errors, _ = evaluate_with_report(self.record, NOW,
                                         max_input_age_hours=1)
        self.assertTrue(any("session-read freshness bound" in e
                            for e in errors), errors)

    def test_without_the_declaration_the_old_requirement_returns(self):
        self._break_s1_parse()
        self._write_team_advanced("2026-11-15T10:00:00Z")
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("S1_season" in e for e in errors), errors)

    def test_failure_only_companion_excuses_only_its_failed_entry(self):
        self._declare_s1(keys=("S1_season", "S2_train"))
        self._break_s1_parse()
        self._write_team_advanced("2026-11-15T10:00:00Z")
        # The declaration may only stand for a source the run actually
        # checked, so S2_train needs its own source check like S1_season's.
        self.record["source_checks"].append(
            {"key": "S2_train",
             "url": ("https://www.nba.com/stats/teams/advanced"
                     "?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026"
                     "&SeasonType=Regular+Season"),
             "checked_at_utc": "2026-11-15T11:55:00Z",
             "http_status": 200, "bytes": 12345, "sha256": DIGEST})
        self.record["failed"] = [["S1_season", "expected 30 team rows, parsed 0"],
                                 ["S2_train", "expected 30 team rows, parsed 0"],
                                 ["S4_schedule", "something genuinely broken"]]
        errors, report = evaluate_with_report(self.record, NOW)
        # The two declared failures are notes; the undeclared one still blocks.
        self.assertTrue(any("fetcher reported 1 failed" in e for e in errors),
                        errors)
        applied = {d["source_key"]: d for d in report["declarations_applied"]}
        self.assertIn("S1_season", applied)
        self.assertIn("S2_train", applied)
        self.assertTrue(applied["S2_train"].get("failure_only"))
        self.assertFalse(applied["S1_season"].get("failure_only"))

    def test_newest_failed_injury_edition_falls_back_to_the_newest_success(self):
        """A rate-limited newest edition must not block the verification side
        when promote binds to the newest SUCCESSFUL retrieval (F-CA-07's
        promote-side rule). Section 77 makes the gate bind to the same."""
        injury = next(c for c in self.record["source_checks"]
                      if c["key"] == "injury_pdf_probe")
        ok = dict(injury["results"][0])
        injury["results"] = [
            {"edition": "Injury-Report_2026-11-15_01_00PM.pdf",
             "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_01_00PM.pdf",
             "http_status": 403},
            ok,
        ]
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertFalse(any("retrieved successfully" in e for e in errors),
                         errors)
        self.assertTrue(any("was not retrieved" in w for w in report["warnings"]),
                        report["warnings"])


class AuditHistoryTests(unittest.TestCase):
    """The audit must read git history, not infer it from one run record.

    This session published "rebuild has ever run: no" on the live site from
    the CURRENT record's `build_outcome: skipped`. That is not evidence about
    2026-11-14, and it was wrong (COORDINATION.md section 73.2). These tests
    pin the two ways the mistake could return.
    """

    def test_audit_reads_history_rather_than_the_current_record(self):
        import importlib
        audit = importlib.import_module("scripts.f3cb4a98_refresh_path_audit")
        history = audit.rebuild_history()
        if history.get("error"):
            self.skipTest(f"history unavailable in this environment: {history['error']}")
        self.assertFalse(os.path.exists(os.path.join(audit.ROOT, ".git", "shallow")))
        # The repository has a real success in its history (2026-11-15T12:43:11Z).
        self.assertTrue(history["rebuild_has_ever_run"], history)
        self.assertGreaterEqual(history["records_read"], 5)
        self.assertEqual(history["last_success_utc"], "2026-11-15T12:43:11Z")

    def test_audit_reports_shallow_clones_instead_of_guessing(self):
        """The guard must DESCRIBE the checkout, and must not fail the suite.

        The first version of this test asserted that the checkout was
        unshallowed. `actions/checkout` is shallow on CI, so that assertion
        failed the whole `Publish static site` workflow on main (run
        44479540069) while the same suite passed locally in an unshallowed
        sandbox. A test that asserts a property of the environment rather than
        the behaviour of the code is a bad test: this one now pins the
        behaviour, which is that the guard answers truthfully either way.
        """
        import importlib
        audit = importlib.import_module("scripts.f3cb4a98_refresh_path_audit")
        warning = audit.assert_full_history()
        shallow = os.path.exists(os.path.join(audit.ROOT, ".git", "shallow"))
        if shallow:
            self.assertIsInstance(warning, str)
            self.assertIn("SHALLOW CLONE", warning)
        else:
            self.assertIsNone(warning)

    def test_history_result_is_honest_in_either_checkout(self):
        """In a shallow clone the audit must decline, not answer 'False'."""
        import importlib
        audit = importlib.import_module("scripts.f3cb4a98_refresh_path_audit")
        history = audit.rebuild_history()
        if os.path.exists(os.path.join(audit.ROOT, ".git", "shallow")):
            self.assertIsNotNone(history.get("error"))
            self.assertNotIn("rebuild_has_ever_run", history)


if __name__ == "__main__":
    unittest.main()
