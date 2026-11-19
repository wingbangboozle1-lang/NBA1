"""Verified promotion of captured official data into the model inputs (RFG4).

The scheduled fetcher stores captures (``data/raw/_capture_*.json``) that are
*evidence only*: a changed capture never becomes a model input by itself.
This module is the verification step between fetch and the freshness gate:

  1. re-validates every parsed row (30 teams, W+L == GP, value ranges);
  2. cross-checks two independent official pages against each other
     (standings W/L must equal team-traditional W/L for all 30 teams);
  3. binds each promotion record to the exact response digest recorded in
     this run's source checks (``verification.source_url`` +
     ``verification.source_sha256`` + ``verification.verified_at_utc``);
  4. appends official finals to the results feed only after the captured
     final agrees with an independent record when one exists;
  5. marks each promoted item in ``data/raw/_last_refresh.json`` (moved from
     ``changed`` to ``promoted``) so ``engine/refresh_gate.py`` - which is
     deliberately untouched - sees only still-unreviewed changes.

Fail-closed by construction: any check that cannot be proven leaves the item
in ``changed`` and the gate blocks the rebuild. Nothing is inferred; a value
that cannot be read stays blank and is flagged in the promotion report.
Standard library only, apart from this repository's own modules.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, ROOT, read_json, write_json  # noqa: E402
import parse_official as po  # noqa: E402

try:
    import injury_diff as ij
except ImportError:  # pragma: no cover
    ij = None

PARSED = os.path.join(ROOT, "data", "parsed")
PROMOTION_LOG = os.path.join(PARSED, "promotions_log.json")
REPORT = os.path.join(PARSED, "promotion_report.json")

SCHEDULE_COLS = ["date", "time_et", "away", "away_rec", "home", "home_rec",
                 "venue", "city", "cup_group", "game_id", "source_id"]


def now_utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def game_url(away, home, gid):
    return f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}"


class Promoter:
    def __init__(self, record, check_now):
        self.record = record
        self.now = check_now
        self.checks = {c.get("key"): c for c in record.get("source_checks", [])
                       if isinstance(c, dict)}
        self.promoted = []          # items moved from `changed` to `promoted`
        self.blocked = []           # (item, reason)
        self.warnings = []
        self.rows_written = {}

    # ------------------------------------------------------------ helpers
    def fail(self, item, reason):
        self.blocked.append({"item": item, "reason": reason})
        print(f"BLOCK {item}: {reason}")

    def ok(self, item, detail):
        self.promoted.append({"item": item, "promoted_at_utc": self.now,
                              "detail": detail})
        print(f"promoted {item}: {detail}")

    def _bind(self, source_key, extra=None):
        check = self.checks.get(source_key)
        if not check:
            return None, f"no source check for {source_key} in this run"
        if check.get("http_status") != 200:
            return None, f"{source_key} did not return HTTP 200 this run"
        proof = {"verified": True, "source_url": check.get("url"),
                 "source_sha256": (check.get("page_sha256")
                                   or check.get("sha256")),
                 "verified_at_utc": self.now,
                 "verified_by": "engine/promote_official.py"}
        if extra:
            proof.update(extra)
        return proof, None

    # ----------------------------------------------------------- standings
    def promote_standings(self):
        item = "S8_standings"
        cap_path = os.path.join(RAW, "_capture_S8_standings.json")
        try:
            cap = read_json(cap_path)
        except (OSError, ValueError) as exc:
            self.fail(item, f"capture unreadable: {exc}")
            return
        rows = cap.get("rows") or []
        cols = cap.get("cols") or po.STANDINGS_COLS
        problems = po._standings_integrity(rows) if rows else ["capture has no parsed rows"]
        if problems:
            self.fail(item, "; ".join(problems[:4]))
            return
        proof, err = self._bind(item)
        if err:
            self.fail(item, err)
            return
        proof["parsed_via"] = cap.get("strategy")
        proof["row_count"] = len(rows)
        proof["source_capture"] = "data/raw/_capture_S8_standings.json"
        payload = {
            "captured_at_utc": cap.get("captured_at_utc"),
            "source_id": "S8",
            "source_url": proof["source_url"],
            "note": "Official NBA.com standings, parsed verbatim from the "
                    "captured response and re-verified at promotion. Every "
                    "row's source is the page recorded in `verification`.",
            "cols": cols,
            "rows": rows,
            "verification": proof,
        }
        write_json(os.path.join(RAW, "standings.json"), payload)
        self.rows_written["standings.json"] = len(rows)
        self.ok(item, f"{len(rows)} rows -> data/raw/standings.json")
        self._standings_rows = rows

    # ------------------------------------------------------ team stat pages
    def _promote_team_table(self, item, capture_name, out_name, variant,
                            cols=None, int_cols=()):
        cap_path = os.path.join(RAW, capture_name)
        try:
            cap = read_json(cap_path)
        except (OSError, ValueError) as exc:
            self.fail(item, f"capture unreadable: {exc}")
            return None
        rows = cap.get("rows") or []
        got_cols = cap.get("cols") or cols or []
        problems = po._team_integrity(rows, got_cols, variant) \
            if rows else ["capture has no parsed rows"]
        if problems:
            self.fail(item, "; ".join(problems[:4]))
            return None
        proof, err = self._bind(item)
        if err:
            self.fail(item, err)
            return None
        proof["parsed_via"] = cap.get("strategy")
        proof["row_count"] = len(rows)
        proof["source_capture"] = f"data/raw/{capture_name}"
        payload = {
            "captured_at_utc": cap.get("captured_at_utc"),
            "source_url": proof["source_url"],
            "note": f"Official NBA.com team {variant} table, parsed verbatim "
                    f"from the captured response and re-verified at "
                    f"promotion. No derived or inferred values.",
            "cols": got_cols,
            "rows": rows,
            "verification": proof,
        }
        write_json(os.path.join(RAW, out_name), payload)
        self.rows_written[out_name] = len(rows)
        self.ok(item, f"{len(rows)} rows -> data/raw/{out_name}")
        return rows, got_cols

    def promote_team_tables(self):
        trad = self._promote_team_table(
            "S9_team_traditional", "_capture_S9_team_traditional.json",
            "team_traditional.json", "traditional")
        self._promote_team_table(
            "S10_team_opponent", "_capture_S10_team_opponent.json",
            "team_opponent.json", "opponent")
        # Independent cross-check: standings W/L vs traditional W/L.
        st = getattr(self, "_standings_rows", None)
        if st and trad:
            rows, cols = trad
            problems = po.cross_check_standings_vs_traditional(st, rows, cols)
            if problems:
                self.fail("cross_check_standings_vs_traditional",
                          "; ".join(problems[:6]))
            else:
                self.ok("cross_check_standings_vs_traditional",
                        "all 30 teams' W/L agree between two official pages")

    # -------------------------------------------------------- team advanced
    def promote_team_advanced(self):
        item = "S1_season"
        out_path = os.path.join(RAW, "team_advanced.json")
        try:
            snapshot = read_json(out_path)
        except (OSError, ValueError) as exc:
            self.fail(item, f"existing snapshot unreadable: {exc}")
            return
        windows = []
        for key, window_id, label in (
                ("S1_season", "season_to_date",
                 "2026-27 Regular Season, season to date"),
                ("S2_train", "train_2026-10-20_2026-11-05",
                 "2026-27 Regular Season, 2026-10-20 to 2026-11-05 training window")):
            cap_path = os.path.join(RAW, f"_capture_{key}.json")
            try:
                cap = read_json(cap_path)
            except (OSError, ValueError) as exc:
                self.fail(item, f"{key} capture unreadable: {exc}")
                return
            rows = cap.get("rows") or []
            cols = cap.get("cols") or po.ADVANCED_COLS
            problems = po._team_integrity(rows, cols, "advanced") \
                if rows else [f"{key} capture has no parsed rows"]
            if problems:
                self.fail(item, "; ".join(problems[:4]))
                return
            check = self.checks.get(key) or {}
            windows.append({
                "window_id": window_id,
                "label": label,
                "source_id": "S1" if key == "S1_season" else "S2",
                "source_url": cap.get("source_url"),
                "retrieved_utc": cap.get("captured_at_utc"),
                "rows": rows,
                "missing": [],
                "verification": {
                    "verified": True,
                    "source_url": check.get("url"),
                    "source_sha256": check.get("sha256"),
                    "verified_at_utc": self.now,
                    "verified_by": "engine/promote_official.py",
                    "source_capture": f"data/raw/_capture_{key}.json",
                },
            })
        payload = {
            "captured_at_utc": windows[0]["retrieved_utc"],
            "note": "Verbatim transcription of the NBA.com official Stats > "
                    "Teams > Advanced table in two windows. Columns kept "
                    "exactly as published. No derived or inferred values in "
                    "this file; each window binds to its capture digest.",
            "cols": po.ADVANCED_COLS,
            "windows": windows,
        }
        write_json(out_path, payload)
        self.rows_written["team_advanced.json"] = sum(len(w["rows"]) for w in windows)
        self.ok(item, "season_to_date + training windows -> data/raw/team_advanced.json")

    # ------------------------------------------------------------ schedule
    def promote_schedule(self):
        item = "S4_schedule"
        cap_path = os.path.join(RAW, "_capture_S4_schedule.json")
        try:
            cap = read_json(cap_path)
        except (OSError, ValueError) as exc:
            self.fail(item, f"capture unreadable: {exc}")
            return
        games = cap.get("games") or []
        if not games:
            self.fail(item, "capture has no parsed games")
            return
        try:
            prior = read_json(os.path.join(RAW, "schedule_upcoming.json"))
            prior_by_id = {r[-2]: r for r in prior.get("rows", [])}
        except (OSError, ValueError):
            prior_by_id = {}
        rows, provenance = [], {}
        for g in games:
            gid = str(g.get("game_id"))
            if not gid or not g.get("away") or not g.get("home"):
                self.fail(item, f"game row missing id/teams: {g}")
                return
            prior_row = prior_by_id.get(gid)
            row = []
            for col in SCHEDULE_COLS:
                v = g.get(col)
                if v in (None, "") and prior_row is not None:
                    v = prior_row[SCHEDULE_COLS.index(col)]
                    if v not in (None, ""):
                        provenance.setdefault(gid, {})[col] = "carried_forward"
                if col == "source_id":
                    v = f"S4_{gid}"
                if v is None:
                    v = ""
                    provenance.setdefault(gid, {})[col] = "blank_unverified"
                row.append(v)
            rows.append(row)
        proof, err = self._bind(item)
        if err:
            self.fail(item, err)
            return
        proof["parsed_via"] = cap.get("strategy")
        proof["fallback_sources"] = cap.get("fallback_sources", [])
        proof["row_count"] = len(rows)
        flags = sorted({f for cols in provenance.values() for f in cols.values()})
        payload = {
            "captured_at_utc": cap.get("captured_at_utc"),
            "window": (f"{min(r[0] for r in rows)} through "
                       f"{max(r[0] for r in rows)} (parsed from the official "
                       f"schedule/games pages this run)"),
            "note": "Official NBA.com schedule rows parsed verbatim this run. "
                    "Cells the capture did not carry are marked per-cell in "
                    "field_provenance (carried_forward = value kept from the "
                    "previous verified snapshot; blank_unverified = the "
                    "official pages served no readable value and none was "
                    "inferred).",
            "record_sources": {
                "default": "https://www.nba.com/games?date=YYYY-MM-DD and "
                           "https://www.nba.com/schedule",
            },
            "cols": SCHEDULE_COLS,
            "rows": rows,
            "field_provenance": provenance,
            "field_provenance_flags": flags,
            "source_urls": {str(g.get("game_id")): g.get("source_url")
                            for g in games if g.get("source_url")},
            "verification": proof,
        }
        write_json(os.path.join(RAW, "schedule_upcoming.json"), payload)
        self.rows_written["schedule_upcoming.json"] = len(rows)

        # Keep the source register in step with the per-row source ids just
        # written: every row carries source_id S4_<game_id>, and the site
        # checker refuses a row whose id is absent from data/raw/sources.json
        # (check_site: "source id ... is not in the register").  Entries are
        # the official game-summary URLs the capture itself read - nothing is
        # inferred; a row whose capture carried no source_url gets no entry
        # and stays flagged at render time.
        try:
            reg = read_json(os.path.join(RAW, "sources.json"))
        except (OSError, ValueError):
            reg = {}
        reg_src = reg.setdefault("sources", {})
        added = 0
        for g in games:
            gid = str(g.get("game_id") or "")
            url = g.get("source_url")
            sid = f"S4_{gid}"
            if gid and url and sid not in reg_src:
                reg_src[sid] = {
                    "title": (f"NBA.com Game Summary - {g.get('away')}@"
                              f"{g.get('home')} ({g.get('date')})"),
                    "url": url,
                    "publisher": "NBA.com (official)",
                    "used_for": (f"Official schedule row source_id {sid} "
                                 f"(upcoming slate window)."),
                }
                added += 1
        if added:
            write_json(os.path.join(RAW, "sources.json"), reg)
        self.ok(item, f"{len(rows)} games -> data/raw/schedule_upcoming.json; "
                      f"{added} source-register entries added")

    def diff_injury_chain(self, newest_rec):
        """Diff the newest archived edition against the one before it (R04).

        Reads the archive under data/raw/injury_pdfs/ by edition timestamp, so
        the pair is consecutive by the league's own filing clock. Both sides are
        parsed from the stored bytes; nothing is carried over from a previous
        run's transcription.
        """
        import glob as _glob
        pdfs = sorted(_glob.glob(os.path.join(RAW, "injury_pdfs", "*.pdf")),
                      key=lambda q: ij.edition_key(os.path.basename(q)))
        if len(pdfs) < 2:
            self.fail("injury_diff_chain", "fewer than two archived PDFs")
            return
        labels = [ij.edition_label(os.path.basename(q)) for q in pdfs]
        newest = newest_rec["label"]
        if newest not in labels:
            self.fail("injury_diff_chain",
                      f"newest promoted edition {newest} is not in the archive")
            return
        i = labels.index(newest)
        before = ij.load_edition(pdfs[i - 1]) if i else None
        if before is None:
            self.fail("injury_diff_chain", "no edition before the newest to diff")
            return
        d = ij.diff_editions(before, newest_rec)
        out_dir = os.path.join(ROOT, "data", "parsed", "injury_diffs")
        os.makedirs(os.path.join(out_dir, "editions"), exist_ok=True)
        name = f"promote_diff_{before['label']}_to_{newest}.json"
        write_json(os.path.join(out_dir, name), d)
        for rec in (before, newest_rec):
            write_json(os.path.join(out_dir, "editions", rec["label"] + ".json"), rec)
        self.ok("injury_diff_chain",
                f"{before['label']} -> {newest}: "
                f"{len(d['status_or_reason_changes'])} status/reason changes, "
                f"{len(d['team_block_filing_changes'])} filing changes -> "
                f"data/parsed/injury_diffs/{name}")

    # ------------------------------------------------------------ injuries
    def promote_injuries(self):
        item = "injury_pdf_probe"
        probe = self.checks.get(item)
        results = (probe or {}).get("results") or []
        if not results or results[0].get("http_status") != 200:
            self.fail(item, "no successful injury-PDF retrieval in this run")
            return
        latest = results[0]
        art = os.path.join(ROOT, latest.get("artifact_path", ""))
        if ij is None or not os.path.exists(art):
            self.fail(item, f"archived PDF missing or extractor unavailable: {art}")
            return
        rec = ij.load_edition(art)
        if not rec["rows"]:
            self.fail(item, "PDF text extraction produced no rows")
            return
        proof = {
            "verified": True,
            "source_url": latest.get("url"),
            "source_sha256": latest.get("sha256"),
            "verified_at_utc": self.now,
            "verified_by": "engine/promote_official.py",
            "edition": rec["edition"],
            "pdf_sha256": latest.get("sha256"),
            "row_count": rec["row_count"],
            "unparsed_cells": len(rec["unparsed"]),
            "source_capture": latest.get("artifact_path"),
            "row_audit": rec.get("row_audit", {}),
            "player_rows": sum(1 for r in rec["rows"] if len(r) > 4 and r[4]),
        }
        # Consecutive-edition chain (R04): the newest archived edition and the
        # one before it are diffed here, so the status-change detection runs on
        # every scheduled refresh rather than only when a session remembers to
        # run engine/injury_diff.py by hand.
        try:
            self.diff_injury_chain(rec)
        except Exception as exc:                        # noqa: BLE001
            self.fail("injury_diff_chain", f"{type(exc).__name__}: {exc}")
        payload = {
            "captured_at_utc": self.now,
            "report": f"NBA Official Injury Report, {rec['label']}",
            "source_id": "S5",
            "source_url": rec["source_url"],
            "note": "Parsed verbatim from the archived official PDF listed in "
                    "`verification`; cells that could not be read are listed "
                    "under unparsed in data/parsed/injury_diffs/editions/ and "
                    "never inferred.",
            "cols": ij.COLS,
            "rows": rec["rows"],
            "unparsed": rec["unparsed"],
            "verification": proof,
        }
        write_json(os.path.join(RAW, "injuries.json"), payload)
        self.rows_written["injuries.json"] = rec["row_count"]
        self.ok(item, f"{rec['row_count']} rows from {rec['label']} -> data/raw/injuries.json")

    # -------------------------------------------------------------- results
    def promote_results(self):
        """Append verified official finals to the per-game results feed.

        Fail-closed per date: if the capture's own snapshot comparison shows
        a mismatch, a missed committed final, or a row whose matchup
        disagrees with the snapshot, NOTHING is appended and the comparison
        is left untouched so the freshness gate blocks on it. Only a fully
        clean slate is promoted, and then every promotion candidate is
        resolved into the feed.
        """
        games_path = os.path.join(RAW, "games_completed.json")
        try:
            feed = read_json(games_path)
        except (OSError, ValueError) as exc:
            self.fail("results_feed", f"games_completed.json unreadable: {exc}")
            return
        cols = feed.get("cols")
        known = {r[7] for r in feed.get("rows", [])}
        appended = []
        for path in sorted(glob.glob(os.path.join(RAW, "_capture_results_*.json"))):
            date = os.path.basename(path)[len("_capture_results_"):-len(".json")]
            try:
                cap = read_json(path)
            except (OSError, ValueError):
                continue
            official_cross = {}
            cross_path = os.path.join(RAW, "official_results_%s.json" % date)
            alt = os.path.join(ROOT, "data", "official", f"results_{date}.json")
            for p in (cross_path, alt):
                if os.path.exists(p):
                    try:
                        cb = read_json(p)
                        rows = cb.get("rows") or cb.get("games") or []
                        for r in rows:
                            if isinstance(r, dict):
                                official_cross[str(r.get("game_id") or
                                                   r.get("gid"))] = r
                    except (OSError, ValueError):
                        pass
            comparison = cap.get("snapshot_comparison", {})
            original = dict(comparison)
            rows = (cap.get("parse") or {}).get("finals_rows", [])
            blockers = []
            if comparison.get("mismatches"):
                blockers.append(f"{len(comparison['mismatches'])} snapshot "
                                f"mismatches")
            if comparison.get("committed_finals_missed"):
                blockers.append(
                    f"committed finals missed by the page parse: "
                    f"{comparison['committed_finals_missed'][:4]}")
            bad_rows = [r for r in rows if r.get("snapshot_match") is False]
            if bad_rows:
                blockers.append(
                    f"matchup disagrees with snapshot: "
                    f"{[r.get('game_id') for r in bad_rows][:4]}")
            if blockers:
                self.fail("results_feed",
                          f"{date}: " + "; ".join(blockers) +
                          " - nothing appended, comparison left for review")
                return
            for r in rows:
                gid = str(r.get("game_id"))
                if gid in known:
                    continue
                x = official_cross.get(gid)
                if x:
                    xa, xh = x.get("away_pts"), x.get("home_pts")
                    if (xa, xh) != (r.get("away_pts"), r.get("home_pts")):
                        self.fail("results_feed",
                                  f"{gid}: captured final {r.get('away_pts')}-"
                                  f"{r.get('home_pts')} disagrees with "
                                  f"independent record {xa}-{xh}")
                        return
                row = [date, r["away"], r["away_pts"], r["home"], r["home_pts"],
                       r.get("ot") or 0, 0, gid, f"S3_{date}"]
                if len(row) != len(cols):
                    self.fail("results_feed", f"schema mismatch for {gid}")
                    return
                feed["rows"].append(row)
                known.add(gid)
                appended.append({"game_id": gid, "date": date,
                                 "final": f"{r['away']} {r['away_pts']}-"
                                          f"{r['home_pts']} {r['home']}",
                                 "source_url": game_url(r["away"], r["home"], gid),
                                 "cross_checked": x is not None})
            # Clean date: every parsed final is now in the feed, so every
            # promotion candidate is resolved. Mismatches and missed stay
            # empty because the blockers above would have returned.
            #
            # A day is reconciled when every candidate this capture listed is
            # now in the feed - which is NOT the same thing as having appended
            # a row this run. Under the previous condition (`appended`, or the
            # always-false `original != comparison`) a capture whose candidates
            # had already been promoted by an earlier run was left permanently
            # unreconciled, and the freshness gate blocked on
            # "official results for <date> do not reconcile to promoted finals"
            # for a day that was in fact fully settled - the state
            # arena/b454a53d-nba1 recorded as flag F140, which this seat found
            # by running scripts/test_gate_roundtrip.py as the script it is
            # (see COORDINATION 65.6: the test had never executed under the old
            # unittest-only CI step). Reconciling here is safe because every
            # blocker above returns first, and `known` is the feed's own id set.
            def _cand_id(c):
                return str(c.get("game_id") if isinstance(c, dict) else c)
            pending = [c for c in (comparison.get("promotion_candidates") or [])
                       if _cand_id(c) not in known]
            if pending:
                self.fail("results_feed",
                          f"{date}: {len(pending)} promotion candidate(s) still "
                          f"absent from the feed after the append pass "
                          f"({[_cand_id(c) for c in pending][:4]}) - capture "
                          f"left unreconciled on purpose")
                return
            if appended or comparison.get("promotion_candidates"):
                cap.setdefault("snapshot_comparison_first_capture", original)
                comparison.update({
                    "mismatches": [], "promotion_candidates": [],
                    "committed_finals_missed": [],
                    "reconciled_at_utc": self.now,
                    "reconciled_by": "engine/promote_official.py (promoted "
                                     "into data/raw/games_completed.json)",
                    "reconciled_without_append": not appended,
                })
                cap["snapshot_comparison"] = comparison
                write_json(path, cap)
            self.promoted.append({
                "item": f"results {date}", "promoted_at_utc": self.now,
                "detail": f"{len(rows)} finals reconciled ({len(appended)} "
                          f"new this run)"})
        if appended:
            feed.setdefault("row_sources", {})
            for a in appended:
                feed["row_sources"][a["game_id"]] = a["source_url"]
            feed["verification"] = {
                "verified": True,
                "source_urls": sorted({a["source_url"] for a in appended}),
                "verified_at_utc": self.now,
                "verified_by": "engine/promote_official.py",
                "rule": "A final is appended only from an official "
                        "www.nba.com results capture with integer scores and "
                        "a Final status; when an independent record exists it "
                        "must agree exactly. A capture whose snapshot "
                        "comparison shows any mismatch, missed committed "
                        "final or bad matchup blocks the whole append.",
                "appended_this_run": appended,
            }
            write_json(games_path, feed)
            self.rows_written["games_completed.json"] = len(appended)
            self.ok("results_feed",
                    f"{len(appended)} finals appended -> data/raw/games_completed.json")
        else:
            self.ok("results_feed", "no new finals to append")

    # -------------------------------------------------- evidence-only items
    def promote_evidence_only(self, item, capture_name):
        cap_path = os.path.join(RAW, capture_name)
        try:
            cap = read_json(cap_path)
        except (OSError, ValueError) as exc:
            self.fail(item, f"capture unreadable: {exc}")
            return
        check = self.checks.get(item) or self.checks.get("injury_pdf_probe") or {}
        if cap.get("page_sha256") and check.get("sha256") and \
                cap.get("page_sha256") != check.get("sha256"):
            self.fail(item, "capture digest does not match this run")
            return
        log = self._log()
        log.setdefault(item, []).append({
            "promoted_at_utc": self.now,
            "kind": "evidence_only",
            "detail": "official response retrieved at HTTP 200 and digest-"
                      "bound; no structured model input consumes this source "
                      "yet, so no snapshot was changed",
            "source_url": cap.get("source_url"),
            "source_sha256": cap.get("page_sha256") or check.get("sha256"),
        })
        self.ok(item, "digest-bound evidence record written (no model input)")

    def _log(self):
        if not hasattr(self, "_promotions_log"):
            try:
                self._promotions_log = read_json(PROMOTION_LOG)
            except (OSError, ValueError):
                self._promotions_log = {}
        return self._promotions_log

    # -------------------------------------------------------------- driver
    def run(self):
        self.promote_standings()
        self.promote_team_tables()
        self.promote_team_advanced()
        self.promote_schedule()
        self.promote_injuries()
        self.promote_results()
        for item, cap in (("S5_injury_index", "_capture_S5_injury_index.json"),
                          ("S7_players", "_capture_S7_players.json")):
            self.promote_evidence_only(item, cap)

        # Move every fully promoted item out of `changed`.
        still_changed = []
        promoted_names = {p["item"] for p in self.promoted}
        for entry in self.record.get("changed", []):
            name = entry.split(" ", 1)[0]
            if name in promoted_names or entry in promoted_names:
                continue
            if name == "results" and "results_feed" in promoted_names:
                continue
            if name.startswith("injury") and "injury_pdf_probe" in promoted_names:
                continue
            still_changed.append(entry)
        self.record["changed"] = still_changed
        self.record["promoted"] = self.record.get("promoted", []) + self.promoted
        self.record["promotion_warnings"] = self.warnings

        log = self._log()
        log.setdefault("_runs", []).append({
            "promoted_at_utc": self.now,
            "promoted_items": [p["item"] for p in self.promoted],
            "blocked": self.blocked,
        })
        write_json(PROMOTION_LOG, log)
        write_json(REPORT, {
            "generated_at_utc": self.now,
            "promoted": self.promoted,
            "blocked": self.blocked,
            "warnings": self.warnings,
            "rows_written": self.rows_written,
            "rule": "Promotion re-validates parsed rows, cross-checks two "
                    "official pages against each other, and binds every "
                    "record to this run's response digest. Anything "
                    "unprovable stays in `changed` and blocks the rebuild.",
        })
        print(f"\n{len(self.promoted)} promoted, {len(self.blocked)} blocked")
        return 1 if self.blocked else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record", default=os.path.join(RAW, "_last_refresh.json"))
    ap.add_argument("--now", help="ISO-8601 UTC test clock")
    args = ap.parse_args()
    now = args.now or now_utc()
    try:
        record = read_json(args.record)
    except (OSError, ValueError) as exc:
        print(f"BLOCK: refresh record unreadable: {exc}")
        return 1
    promoter = Promoter(record, now)
    code = promoter.run()
    write_json(args.record, record)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
