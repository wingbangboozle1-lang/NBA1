"""Tests for the rebuild-reach work — COORDINATION.md section 79.

Background: the scheduled rebuild was unreachable for four days because two
classes of requirement could never be satisfied from a GitHub runner —
  1. the S8/S9/S10 promoted snapshots (0 commits ever; §73's declaration
     mechanism), and
  2. the S1_season capture + advanced-table comparison (0 commits ever; the
     page is a client-rendered shell and the stats.nba.com fallback timed
     out five times on 2026-11-19 alone).

Sessions `arena/fb91550a-nba1` (§77/PR #200) and `arena/cdf3a108-nba1`
(§78/PR #204) unioned the fix on `main`; this seat (§79) yielded its
duplicated implementation and kept the tests, re-based them on the delivered
behaviour, plus the §79 hardening. What these tests pin:

  * the undeclared-S1 state blocks in every way (the pre-fix situation);
  * a live, evidence-backed S1_season/S2_train declaration passes the gate —
    visibly (PASS BY DECLARATION), with the consumed `team_advanced.json`
    staleness published WITH its measured age, and with the consumed file
    itself re-read so a missing/unreadable one blocks here instead of
    crashing engine/pipeline.py a step later (§79's hardening);
  * anti-rot: the moment a rows-bearing capture exists, the declaration is
    refused and the original requirement returns;
  * promotion routes a declared S1_season to `blocked_unreadable` only when
    its parse-failure evidence exists on disk, and the run's exit code is
    not poisoned by it;
  * S7_players stays outside both the required and the declared-only sets.

Import-safe under `python3 -m unittest discover -s scripts -p 'test_*.py'`
(no side effects at import; see COORDINATION §74).
"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))

from engine.refresh_gate import evaluate_with_report  # noqa: E402

NOW = dt.datetime(2026, 11, 15, 12, 0, tzinfo=dt.timezone.utc)
DIGEST = "a" * 64
PDF_BYTES = b"%PDF-1.7\nrebuild-reach-test\n"
import hashlib  # noqa: E402

PDF_DIGEST = hashlib.sha256(PDF_BYTES).hexdigest()

S1_URL = "https://www.nba.com/stats/teams/advanced"
S2_URL = ("https://www.nba.com/stats/teams/advanced"
          "?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026"
          "&SeasonType=Regular+Season")

URLS = {
    "S1_season": S1_URL,
    "S2_train": S2_URL,
    "S4_schedule": "https://www.nba.com/schedule",
    "S5_injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "S8_standings": "https://www.nba.com/standings",
    "S9_team_traditional": "https://www.nba.com/stats/teams/traditional",
    "S10_team_opponent": "https://www.nba.com/stats/teams/opponent",
}

CAPTURE_NAMES = {
    "S1_season": "_capture_S1_season.json",
    "S4_schedule": "_capture_S4_schedule.json",
    "S5_injury_index": "_capture_S5_injury_index.json",
    "S8_standings": "_capture_S8_standings.json",
    "S9_team_traditional": "_capture_S9_team_traditional.json",
    "S10_team_opponent": "_capture_S10_team_opponent.json",
}


class GateDeclarationReachTests(unittest.TestCase):
    """The gate must pass behind a live S1/S2 declaration — loudly."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.old_root = os.environ.get("NBA1_REPO_ROOT")
        os.environ["NBA1_REPO_ROOT"] = self.root
        raw = os.path.join(self.root, "data/raw")
        os.makedirs(os.path.join(raw, "injury_pdfs"), exist_ok=True)
        pdf_rel = ("data/raw/injury_pdfs/Injury-Report_2026-11-15_12_00PM__"
                   + PDF_DIGEST + ".pdf")
        with open(os.path.join(self.root, pdf_rel), "wb") as fh:
            fh.write(PDF_BYTES)

        # S1_season and S2_train FAILED this run (the live situation), and no
        # capture files exist for them — that is the premise.
        self.record = {
            "captured_at_utc": "2026-11-15T11:55:00Z",
            "failed": [
                ["S1_season", "expected 30 team rows, parsed 0 (html_tr=12 "
                              "team_links=0 rowSet=0 parse_problems=5)"],
                ["S2_train", "expected 30 team rows, parsed 0 (html_tr=12 "
                             "team_links=0 rowSet=0 parse_problems=5)"],
            ],
            "changed": [],
            "source_checks": [
                {"key": k, "url": u, "checked_at_utc": "2026-11-15T11:55:00Z",
                 "http_status": 200, "bytes": 12345, "sha256": DIGEST}
                for k, u in URLS.items()
            ] + [
                {"key": "results_2026-11-15",
                 "url": "https://www.nba.com/games?date=2026-11-15",
                 "checked_at_utc": "2026-11-15T11:55:00Z", "http_status": 200,
                 "sha256": DIGEST},
                {"key": "results_2026-11-14",
                 "url": "https://www.nba.com/games?date=2026-11-14",
                 "checked_at_utc": "2026-11-15T11:55:00Z", "http_status": 200,
                 "sha256": DIGEST},
                {"key": "injury_pdf_probe",
                 "checked_at_utc": "2026-11-15T11:55:00Z",
                 "results": [{"edition": "Injury-Report_2026-11-15_12_00PM.pdf",
                              "url": ("https://ak-static.cms.nba.com/referee/"
                                      "injury/Injury-Report_2026-11-15_12_00PM.pdf"),
                              "http_status": 200, "sha256": PDF_DIGEST,
                              "pdf_valid": True, "artifact_path": pdf_rel}]},
            ],
        }

        # Captures for every source EXCEPT S1_season/S2_train (never exist).
        for key in ("S4_schedule", "S5_injury_index", "S8_standings",
                    "S9_team_traditional", "S10_team_opponent"):
            payload = {"source_url": URLS[key], "page_sha256": DIGEST}
            if key == "S4_schedule":
                payload["games"] = [{"game_id": "0022600001"}]
            with open(os.path.join(raw, CAPTURE_NAMES[key]), "w") as fh:
                json.dump(payload, fh)

        # Parse-failure evidence for S1/S2, shaped like the live records
        # (source_url present — that is what lets the gate prove the response
        # came from the official URL this run).
        for key in ("S1_season", "S2_train"):
            with open(os.path.join(raw, f"_capture_evidence_{key}.json"), "w") as fh:
                json.dump({"status": "parse_failed", "source_url": URLS[key],
                           "captured_at_utc": "2026-11-15T11:55:00Z",
                           "api_attempt": {"parse_note": "TimeoutError: The read operation timed out"},
                           "problems": ["expected 30 team rows, parsed 0"]}, fh)

        # Promoted snapshots for S8/S9/S10 (present and verified — the
        # section-73 declarations are not needed in this fixture).
        for key, filename in (("S8_standings", "standings.json"),
                              ("S9_team_traditional", "team_traditional.json"),
                              ("S10_team_opponent", "team_opponent.json")):
            payload = {"rows": [{"team": "Example", "value": 1}],
                       "verification": {"verified": True,
                                        "source_url": URLS[key],
                                        "source_sha256": DIGEST,
                                        "verified_at_utc": "2026-11-15T11:57:00Z"}}
            with open(os.path.join(raw, filename), "w") as fh:
                json.dump(payload, fh)

        # Fresh promotions for the inputs this run's digest covers.
        for filename, source, digest, rows in (
            ("schedule_upcoming.json", URLS["S4_schedule"], DIGEST,
             [{"game_id": "0022600001", "away": "AAA", "home": "BBB"}]),
            ("injuries.json",
             ("https://ak-static.cms.nba.com/referee/injury/"
              "Injury-Report_2026-11-15_12_00PM.pdf"),
             PDF_DIGEST, [{"player": "Example Player", "status": "Available"}]),
        ):
            payload = {"rows": rows,
                       "verification": {"verified": True, "source_url": source,
                                        "source_sha256": digest,
                                        "verified_at_utc": "2026-11-15T11:57:00Z"}}
            with open(os.path.join(raw, filename), "w") as fh:
                json.dump(payload, fh)

        # The consumed advanced snapshot in the shape the merged gate
        # (arena/4eef6d3b-nba1, §79) demands when S1 is declared: exists,
        # carries an explicit session verification on an official URL, is
        # within SESSION_INPUT_MAX_AGE_HOURS (72 h) of this run, and its
        # season_to_date window is a complete 30-row W+L==GP table.
        with open(os.path.join(raw, "team_advanced.json"), "w") as fh:
            json.dump({"captured_at_utc": "2026-11-11T00:38:00Z",
                       "verification": {"verified": True,
                                        "source_url": S1_URL,
                                        "verified_at_utc": "2026-11-15T08:00:00Z",
                                        "verified_by": "test fixture"},
                       "cols": ["team", "gp", "w", "l"],
                       "windows": [{"window_id": "season_to_date",
                                    "rows": [["Team %02d" % i, 1, 1, 0]
                                             for i in range(30)]}]}, fh)

        for date in ("2026-11-14", "2026-11-15"):
            payload = {"snapshot_comparison": {"mismatches": [],
                                               "promotion_candidates": [],
                                               "committed_finals_missed": []}}
            with open(os.path.join(raw, f"_capture_results_{date}.json"), "w") as fh:
                json.dump(payload, fh)

    def tearDown(self):
        self.tmp.cleanup()
        if self.old_root is None:
            os.environ.pop("NBA1_REPO_ROOT", None)
        else:
            os.environ["NBA1_REPO_ROOT"] = self.old_root

    def _declare(self, keys=("S1_season", "S2_train")):
        entries = [{"source_key": k,
                    "required_snapshot": ("data/raw/_capture_%s.json" % k),
                    "expires_at_utc": "2026-12-19T00:00:00Z",
                    "review_flag": "F-F3C-03",
                    "evidence": ["data/raw/_capture_evidence_%s.json" % k],
                    "reason": "client-rendered page proved by committed evidence"}
                   for k in keys]
        with open(os.path.join(self.root, "data/raw/unreadable_sources.json"), "w") as fh:
            json.dump({"declarations": entries}, fh)

    def test_undeclared_s1_and_s2_block_every_way(self):
        """Without declarations the live7-block situation is reproduced."""
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("fetcher reported 2 failed" in e for e in errors), errors)
        self.assertTrue(any("missing/invalid payload capture for S1_season" in e
                            for e in errors), errors)
        self.assertTrue(any("missing/invalid structured capture" in e for e in errors),
                        errors)
        self.assertTrue(any("cannot be compared" in e for e in errors), errors)
        self.assertEqual(report["declarations_applied"], [])

    def test_live_declarations_pass_and_report_the_stale_input_age(self):
        self._declare()
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertEqual(errors, [], errors)
        applied = {d["source_key"] for d in report["declarations_applied"]}
        self.assertEqual(applied, {"S1_season", "S2_train"})
        # The pass is visibly a pass-by-declaration AND a pass on the
        # session-maintained input (the merged gate's branch (b)).
        accepted = [w for w in report["warnings"]
                    if "accepted via session verification" in w]
        self.assertEqual(len(accepted), 1, report["warnings"])
        self.assertTrue(any("no parsed payload by design" in w
                            and "declared unreadable" in w
                            for w in report["warnings"]), report["warnings"])

    def test_session_verification_older_than_72_hours_blocks(self):
        """The declaration must not hide an aged-out consumed input."""
        self._declare()
        path = os.path.join(self.root, "data/raw/team_advanced.json")
        with open(path) as fh:
            snap = json.load(fh)
        # Verified 100 h before NOW (2026-11-15T12:00Z) > 72 h.
        snap["verification"]["verified_at_utc"] = "2026-11-11T08:00:00Z"
        with open(path, "w") as fh:
            json.dump(snap, fh)
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("advanced team input is stale" in e
                            and "100.0h old" in e for e in errors), errors)

    def test_anti_rot_a_rows_bearing_capture_refuses_the_declaration(self):
        """If the page ever parses, the requirement comes back immediately."""
        self._declare()
        with open(os.path.join(self.root, "data/raw/_capture_S1_season.json"), "w") as fh:
            json.dump({"source_url": S1_URL, "page_sha256": DIGEST,
                       "row_count": 30,
                       "cols": ["team", "gp"],
                       "rows": [["Team %02d" % i, 1] for i in range(30)]}, fh)
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("DECLARATION STALE" in w for w in report["warnings"]),
                        report["warnings"])
        applied = {d["source_key"] for d in report["declarations_applied"]}
        self.assertNotIn("S1_season", applied)
        # The original requirements are back: the undeclared parse failure in
        # the record must block again (in production the fetcher would simply
        # not record a failure once the page parses; this fixture keeps the
        # failure to prove the undeclared path is live). Silence would be the
        # bug — the gate must not pass a run whose S1 declaration was refused.
        self.assertTrue(errors, "a refused declaration must leave the gate blocking")
        self.assertTrue(any("fetcher reported" in e for e in errors), errors)

    def test_declared_s1_with_missing_consumed_snapshot_still_blocks(self):
        """The declaration excuses the CAPTURE, never the consumed file."""
        self._declare()
        os.remove(os.path.join(self.root, "data/raw/team_advanced.json"))
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("session-maintained) missing or unreadable" in e
                            and "team_advanced.json" in e for e in errors), errors)

    def test_evidence_url_must_match_this_runs_check(self):
        self._declare()
        with open(os.path.join(self.root,
                               "data/raw/_capture_evidence_S1_season.json"), "w") as fh:
            json.dump({"status": "parse_failed",
                       "problems": ["expected 30 team rows, parsed 0"]}, fh)
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("S1_season" in e and "provenance URL mismatch" in e
                            for e in errors), errors)
        # The declaration itself may be admitted (its evidence FILE exists);
        # what must never happen is the PASS — the per-source URL check is
        # what makes an evidence record without a source_url fatal.
        self.assertTrue(errors, "evidence without a source_url must block")

    def test_only_s2_declared_leaves_s1_blocking(self):
        self._declare(keys=("S2_train",))
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("fetcher reported 1 failed" in e for e in errors), errors)
        self.assertTrue(any("missing/invalid payload capture for S1_season" in e
                            for e in errors), errors)

    def test_s7_players_remains_outside_both_sets(self):
        """S7 has nothing for a declaration to excuse; it must stay refused."""
        self._declare(keys=("S7_players",))
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertEqual(report["declarations_applied"], [])
        self.assertTrue(any("not a source this gate requires" in w
                            for w in report["warnings"]), report["warnings"])
        # ...and the S1/S2 blocks are untouched by the bogus entry.
        self.assertTrue(any("missing/invalid payload capture for S1_season" in e
                            for e in errors), errors)

    def test_expired_s1_declaration_blocks_again(self):
        self._declare()
        with open(os.path.join(self.root, "data/raw/unreadable_sources.json")) as fh:
            reg = json.load(fh)
        for entry in reg["declarations"]:
            entry["expires_at_utc"] = "2026-11-15T11:00:00Z"
        with open(os.path.join(self.root, "data/raw/unreadable_sources.json"), "w") as fh:
            json.dump(reg, fh)
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertEqual(report["declarations_applied"], [])
        self.assertTrue(any("missing/invalid payload capture for S1_season" in e
                            for e in errors), errors)
        self.assertTrue(any("EXPIRED" in w for w in report["warnings"]),
                        report["warnings"])

    # ------------------------------------------------ catch-up ("steady state")
    # Measured failure without them: run 44533474414 (2026-11-19T13:27Z) had
    # every index-listed edition already archived, probed the fixed-clock
    # editions (all expected 403), and the gate blocked the rebuild on
    # results[0] — a probe edition that is not even on the index.

    def _make_catch_up(self):
        """Probe state of a run that owes no new retrieval (all listed archived)."""
        akamai = ("https://ak-static.cms.nba.com/referee/injury/"
                  "Injury-Report_2026-11-15_12_00PM.pdf")
        listed = "Injury-Report_2026-11-15_12_00PM.pdf"
        probe_results = []
        for future in ("03_00PM", "05_15PM", "07_30PM"):
            probe_results.append({
                "edition": f"Injury-Report_2026-11-15_{future}.pdf",
                "url": ("https://ak-static.cms.nba.com/referee/injury/"
                        f"Injury-Report_2026-11-15_{future}.pdf"),
                "http_status": 403, "listed_on_official_index": False,
            })
        for check in self.record["source_checks"]:
            if check.get("key") == "injury_pdf_probe":
                check["results"] = probe_results
                check["newest_listed"] = listed
        # The archive sidecar for the listed edition (the PDF itself was
        # written by setUp, content-addressed as <name>__<PDF_DIGEST>.pdf).
        stem = f"Injury-Report_2026-11-15_12_00PM__{PDF_DIGEST}"
        with open(os.path.join(self.root, f"data/raw/injury_pdfs/{stem}.json"), "w") as fh:
            json.dump({"edition": listed, "source_url": akamai,
                       "retrieved_at_utc": "2026-11-15T09:00:00Z",
                       "sha256": PDF_DIGEST, "bytes": len(PDF_BYTES)}, fh)
        # injuries.json already binds to this exact edition/digest (setUp) —
        # the same pair promote will bind in this state.
        return listed

    def test_catch_up_run_passes_via_the_archived_newest_listed_edition(self):
        self._declare()
        listed = self._make_catch_up()
        errors, report = evaluate_with_report(self.record, NOW)
        self.assertEqual(errors, [], errors)
        hits = [w for w in report["warnings"] if "already archived" in w]
        self.assertEqual(len(hits), 1, report["warnings"])
        self.assertIn(listed, hits[0])
        self.assertIn("retrieved 2026-11-15T09:00:00Z", hits[0])

    def test_catch_up_with_newest_listed_unarchived_still_blocks(self):
        """No fresh retrieval AND no archive = the rebuild must not run."""
        self._make_catch_up()
        for fn in os.listdir(os.path.join(self.root, "data/raw/injury_pdfs")):
            if fn.startswith("Injury-Report_2026-11-15_12_00PM"):
                os.remove(os.path.join(self.root, "data/raw/injury_pdfs", fn))
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertTrue(any("latest indexed injury PDF was not retrieved successfully" in e
                            for e in errors), errors)

    def test_fetched_state_ignores_the_403_probes_and_binds_results(self):
        """When something WAS fetched, the newest 200 is canonical — not results[0]."""
        self._declare()
        self._make_catch_up()
        akamai_old = ("https://ak-static.cms.nba.com/referee/injury/"
                      "Injury-Report_2026-11-15_09_45AM.pdf")
        # Newer 403 (listed) sits at results[0]; older 9:45AM fetched 200.
        good = {"edition": "Injury-Report_2026-11-15_09_45AM.pdf", "url": akamai_old,
                "http_status": 200, "sha256": PDF_DIGEST, "pdf_valid": True,
                "listed_on_official_index": True,
                "artifact_path": (f"data/raw/injury_pdfs/"
                                  f"Injury-Report_2026-11-15_12_00PM__{PDF_DIGEST}.pdf")}
        bad = {"edition": "Injury-Report_2026-11-15_10_00AM.pdf",
               "url": ("https://ak-static.cms.nba.com/referee/injury/"
                       "Injury-Report_2026-11-15_10_00AM.pdf"),
               "http_status": 403, "listed_on_official_index": True}
        for check in self.record["source_checks"]:
            if check.get("key") == "injury_pdf_probe":
                check["results"] = [bad, good]
                check["newest_listed"] = bad["edition"]
        # Rebind injuries.json to the edition that will actually be promoted
        # (the newest SUCCESSFUL retrieval — promote's F-CA-07 rule).
        with open(os.path.join(self.root, "data/raw/injuries.json")) as fh:
            inj = json.load(fh)
        inj["verification"]["source_url"] = akamai_old
        inj["verification"]["source_sha256"] = PDF_DIGEST
        with open(os.path.join(self.root, "data/raw/injuries.json"), "w") as fh:
            json.dump(inj, fh)
        # The artifact for the fetched edition must carry those bytes; reuse
        # the same content-addressed file under the fetched name.
        src = os.path.join(self.root,
                           f"data/raw/injury_pdfs/Injury-Report_2026-11-15_12_00PM__{PDF_DIGEST}.pdf")
        dst_name = f"Injury-Report_2026-11-15_09_45AM__{PDF_DIGEST}.pdf"
        with open(src, "rb") as fh:
            body = fh.read()
        with open(os.path.join(self.root, "data/raw/injury_pdfs", dst_name), "wb") as fh:
            fh.write(body)
        good["artifact_path"] = f"data/raw/injury_pdfs/{dst_name}"
        errors, _ = evaluate_with_report(self.record, NOW)
        self.assertEqual(errors, [], errors)


class PromoteDeclaredReachTests(unittest.TestCase):
    """promote_official must classify a declared S1_season as unreadable."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raw = os.path.join(self.tmp.name, "data", "raw")
        os.makedirs(self.raw, exist_ok=True)
        import promote_official  # noqa: E402 - imported per-test after path setup
        self.promote = promote_official
        self.real = (promote_official.RAW, promote_official.ROOT,
                     promote_official.PROMOTION_LOG, promote_official.REPORT)
        promote_official.RAW = self.raw
        promote_official.ROOT = self.tmp.name
        promote_official.PROMOTION_LOG = os.path.join(
            self.tmp.name, "data", "parsed", "promotions_log.json")
        promote_official.REPORT = os.path.join(
            self.tmp.name, "data", "parsed", "promotion_report.json")
        # The consumed snapshot exists (promote reads it first), and the
        # parse-failure evidence record exists (the fetcher always writes it
        # for a page it PROVED is a shell) — but the rows-bearing capture
        # files never do. That is the live situation. Without the evidence
        # record, promote must still BLOCK (a declaration never excuses a
        # page that was not even attempted — pinned by
        # scripts/test_promote_official.py, honoured here by supplying it).
        with open(os.path.join(self.raw, "team_advanced.json"), "w") as fh:
            json.dump({"captured_at_utc": "2026-11-14T00:38:00Z",
                       "cols": ["team"], "windows": []}, fh)
        with open(os.path.join(self.raw, "_capture_evidence_S1_season.json"), "w") as fh:
            json.dump({"status": "parse_failed", "source_url": S1_URL,
                       "captured_at_utc": "2026-11-15T11:55:00Z"}, fh)
        # The merged promote routes a missing capture to `blocked_unreadable`
        # only if THIS run attempted the fetch (an HTTP-200 source check) —
        # section 74's rule. Without the attempt it must still block.
        self.record = {
            "changed": [],
            "source_checks": [
                {"key": "S1_season", "url": S1_URL,
                 "checked_at_utc": "2026-11-15T11:55:00Z",
                 "http_status": 200, "bytes": 12345, "sha256": DIGEST},
            ],
        }

    def tearDown(self):
        (self.promote.RAW, self.promote.ROOT,
         self.promote.PROMOTION_LOG, self.promote.REPORT) = self.real
        self.tmp.cleanup()

    def _register(self, keys=("S1_season", "S2_train")):
        with open(os.path.join(self.raw, "unreadable_sources.json"), "w") as fh:
            json.dump({"declarations": [
                {"source_key": k, "expires_at_utc": "2026-12-19T00:00:00Z",
                 "review_flag": "F-F3C-03"} for k in keys]}, fh)

    def test_declared_s1_is_unreadable_not_blocked(self):
        self._register()
        promoter = self.promote.Promoter(dict(self.record), "2026-11-15T11:55:00Z")
        promoter.promote_team_advanced()
        self.assertEqual(promoter.blocked, [], promoter.blocked)
        self.assertEqual([u["item"] for u in promoter.unreadable], ["S1_season"])
        self.assertIn("no parsed rows", promoter.unreadable[0]["reason"])

    def test_undeclared_s1_still_blocks_promotion(self):
        promoter = self.promote.Promoter(dict(self.record), "2026-11-15T11:55:00Z")
        promoter.promote_team_advanced()
        self.assertEqual([b["item"] for b in promoter.blocked], ["S1_season"])
        self.assertEqual(promoter.unreadable, [])

    def test_declared_run_exit_code_is_not_poisoned(self):
        """The full driver returns 0 when the only failure is declared."""
        self._register()
        promoter = self.promote.Promoter(dict(self.record), "2026-11-15T11:55:00Z")
        # Stub every other promotion stage: this test is about the exit-code
        # classification of S1_season, not about schedule/results parsing.
        for name in ("promote_standings", "promote_team_tables",
                     "promote_schedule", "promote_injuries", "promote_results"):
            setattr(promoter, name, lambda *a, **k: None)
        original_evidence = promoter.promote_evidence_only
        promoter.promote_evidence_only = lambda *a, **k: None
        try:
            code = promoter.run()
        finally:
            promoter.promote_evidence_only = original_evidence
        self.assertEqual(code, 0)
        self.assertEqual([u["item"] for u in promoter.unreadable], ["S1_season"])


class CatchUpPromoteTests(unittest.TestCase):
    """Steady-state promotion: bind from the archive, or still block.

    Measured failure without this behaviour: run 44533474414 (13:27Z) had
    every index-listed edition archived, so no result returned 200 and
    `promote_injuries` failed the whole item on the fixed-clock probe's
    expected 403s — which then left injuries.json stale and the gate
    blocked three more ways.
    """

    def setUp(self):
        import promote_official  # noqa: E402 - path set at module import
        self.promote = promote_official
        self.tmp = tempfile.TemporaryDirectory()
        self.raw = os.path.join(self.tmp.name, "data", "raw")
        os.makedirs(os.path.join(self.raw, "injury_pdfs"), exist_ok=True)
        self.real = (promote_official.RAW, promote_official.ROOT,
                     promote_official.PROMOTION_LOG, promote_official.REPORT,
                     promote_official.ij)
        promote_official.RAW = self.raw
        promote_official.ROOT = self.tmp.name
        promote_official.PROMOTION_LOG = os.path.join(
            self.tmp.name, "data", "parsed", "promotions_log.json")
        promote_official.REPORT = os.path.join(
            self.tmp.name, "data", "parsed", "promotion_report.json")
        # The extractor is stubbed: these tests pin WHICH edition gets bound
        # and when promotion refuses, not the PDF reader (pinned separately
        # by scripts/test_promote_official.py and the injury-diff suite).
        class _StubIJ:
            COLS = ["date", "matchup", "team", "player", "status", "reason"]

            @staticmethod
            def load_edition(path):
                return {"edition": "Injury-Report_2026-11-15_12_00PM.pdf",
                        "label": "11/15/2026 12:00 PM ET",
                        "source_url": ("https://ak-static.cms.nba.com/referee/"
                                       "injury/Injury-Report_2026-11-15_12_00PM.pdf"),
                        "rows": [["11/15", "AAA vs BBB", "AAA", "Example Player",
                                  "Out", "Injury"]],
                        "row_count": 1, "unparsed": [], "row_audit": {}}
        promote_official.ij = _StubIJ
        self.listed = "Injury-Report_2026-11-15_12_00PM.pdf"
        self.akamai = ("https://ak-static.cms.nba.com/referee/injury/"
                       + self.listed)
        self.record = {"changed": ["injury probe"], "source_checks": [
            {"key": "injury_pdf_probe",
             "checked_at_utc": "2026-11-15T11:55:00Z",
             "newest_listed": self.listed,
             "results": [{"edition": "Injury-Report_2026-11-15_12_00PM.pdf",
                          "url": self.akamai, "http_status": 403,
                          "listed_on_official_index": False}]},
        ]}

    def tearDown(self):
        (self.promote.RAW, self.promote.ROOT,
         self.promote.PROMOTION_LOG, self.promote.REPORT,
         self.promote.ij) = self.real
        self.tmp.cleanup()

    def _archive(self):
        name_sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        stem = f"Injury-Report_2026-11-15_12_00PM__{name_sha}"
        with open(os.path.join(self.raw, f"injury_pdfs/{stem}.pdf"), "wb") as fh:
            fh.write(PDF_BYTES)
        with open(os.path.join(self.raw, f"injury_pdfs/{stem}.json"), "w") as fh:
            json.dump({"edition": self.listed, "source_url": self.akamai,
                       "retrieved_at_utc": "2026-11-15T09:00:00Z",
                       "sha256": name_sha, "bytes": len(PDF_BYTES)}, fh)

    def _promoter(self):
        promoter = self.promote.Promoter(
            json.loads(json.dumps(self.record)), "2026-11-15T11:55:00Z")
        promoter.diff_injury_chain = lambda rec: None
        return promoter

    def test_steady_state_binds_promotion_from_the_archive(self):
        self._archive()
        promoter = self._promoter()
        for name in ("promote_standings", "promote_team_tables",
                     "promote_team_advanced", "promote_schedule",
                     "promote_results", "promote_evidence_only"):
            setattr(promoter, name, lambda *a, **k: None)
        code = promoter.run()
        self.assertEqual(code, 0, promoter.blocked)
        self.assertEqual(promoter.blocked, [], promoter.blocked)
        self.assertEqual([p["item"] for p in promoter.promoted], ["injury_pdf_probe"])
        with open(os.path.join(self.raw, "injuries.json")) as fh:
            payload = json.load(fh)
        proof = payload["verification"]
        self.assertEqual(proof["source_url"], self.akamai)
        self.assertIn("archived steady state", proof["bound_from"])
        # The probe's expected-403 result must not leave the capture awaiting
        # promotion: the run's `changed` list is settled by this promotion.
        self.assertEqual(promoter.record["changed"], [])

    def test_steady_state_without_an_archive_still_blocks_with_the_same_reason(self):
        promoter = self._promoter()
        promoter.promote_injuries()
        self.assertEqual(promoter.promoted, [])
        self.assertEqual(len(promoter.blocked), 1)
        self.assertEqual(promoter.blocked[0]["item"], "injury_pdf_probe")
        self.assertTrue(promoter.blocked[0]["reason"].startswith(
            "no successful injury-PDF retrieval in this run"), promoter.blocked)

    def test_mismatched_sidecar_sha_refuses_the_archive_binding(self):
        self._archive()
        stem = f"Injury-Report_2026-11-15_12_00PM__{'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}"
        sidecar = os.path.join(self.raw, f"injury_pdfs/{stem}.json")
        with open(sidecar) as fh:
            meta = json.load(fh)
        meta["sha256"] = "b" * 64
        with open(sidecar, "w") as fh:
            json.dump(meta, fh)
        promoter = self._promoter()
        promoter.promote_injuries()
        self.assertEqual([b["item"] for b in promoter.blocked], ["injury_pdf_probe"])
        self.assertIn("sidecar sha256 does not match", promoter.blocked[0]["reason"])


if __name__ == "__main__":
    unittest.main()
