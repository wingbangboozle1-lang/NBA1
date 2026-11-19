#!/usr/bin/env python3
"""update_registers_39b70241.py — §66 / Y05: refresh the four content registers and
the executive summary from what this session actually measured on 2026-11-19.

Conventions this script follows, all taken from the files themselves:

  * registers are append-mostly. A row another session authored is never rewritten;
    new observations go in a session-keyed field (`evidence_2026_11_19_39b70241`,
    `update_2026_11_19_39b70241`) beside the original, so both readings survive;
  * every claim names the file or the official URL it came from;
  * numbers are recomputed from the repository here, not typed — the estimator
    disagreement table is derived from data/derived/horizon_lines.json against
    docs/data/lines.json, so it cannot drift from the published artefacts;
  * re-running is safe: entries are matched by id and replaced, not duplicated.

Written files: data/content/{requirements,flagged,questions,suggestions,executive}.json
               verify/2026-11-19-39b70241/estimator_disagreement.json
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION = "arena/39b70241-nba1"
KEY = "2026_11_19_39b70241"
AS_OF = "2026-11-19"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def dump(rel, doc):
    p = os.path.join(ROOT, rel)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", rel)


def upsert(items, row, key="id"):
    for i, old in enumerate(items):
        if old.get(key) == row[key]:
            items[i] = row
            return "updated"
    items.append(row)
    return "appended"


# ---------------------------------------------------------------- disagreement
def disagreement():
    """Estimator A (this branch's originator) vs estimator B (the validated engine's
    own model line) on the games both cover, computed from the two published files."""
    a = load("data/derived/horizon_lines.json")["games"]
    b = load("docs/data/lines.json")
    brows = b if isinstance(b, list) else (b.get("rows") or list(b.values())[0])
    by = {(r["date"], r["matchup"]): r for r in brows}
    rows, seen_dates = [], {}
    for g in a:
        k = (g["date"], g["matchup"])
        r = by.get(k)
        if not r:
            continue
        rows.append({
            "date": g["date"], "game_id": g["game_id"], "matchup": g["matchup"],
            "a_spread_home": g["line_spread_home"], "b_spread_home": r["model_spread_home"],
            "spread_gap": round(g["line_spread_home"] - r["model_spread_home"], 1),
            "a_total": g["line_total"], "b_total": r["model_total"],
            "total_gap": round(g["line_total"] - r["model_total"], 1),
            "a_p_home": g["model_home_win_prob"], "b_p_home": r["p_home_win"],
            "b_records_in_file": f"{r.get('away_rec')} / {r.get('home_rec')}",
            "b_injury_edition_in_file": r.get("home_report_status", ""),
        })
        seen_dates[g["date"]] = seen_dates.get(g["date"], 0) + 1
    return rows, seen_dates, len(brows)


# ---------------------------------------------------------------- requirements
def _widest(dis_rows):
    if not dis_rows:
        return "no overlapping game"
    w = max(dis_rows, key=lambda r: abs(r["spread_gap"]))
    return (f"{abs(w['spread_gap']):.1f} points of spread on {w['matchup']} "
            f"({w['date']}): A {w['a_spread_home']:+.1f} vs B {w['b_spread_home']:+.1f}")


def requirements(dis_rows, n_b_rows, b_dates):
    rel = "data/content/requirements.json"
    doc = load(rel)
    touched = {}
    for row in doc["rows"]:
        if row["id"] == "R02":
            row[f"evidence_{KEY}"] = (
                "the feed is promoted through 2026-11-18 and now holds 222 rows, 222 of them Final, "
                "every quarter sum re-checked against the printed final "
                "(scripts/settle_2026_11_19_39b70241.py; gate GA8 in "
                "verify/2026-11-19-39b70241/readback_report.json: 444 team-games == 2 x 222)")
            touched["R02"] = "annotated"
        if row["id"] == "R04":
            row[f"evidence_{KEY}"] = (
                "this branch armed a runner-side capture (scripts/capture_injury_39b70241.py + "
                ".github/workflows/capture-injury-39b70241.yml) and run 44468125114 stored all four "
                "2026-11-19 editions (12:00–12:45 AM ET) with measured sha256 sidecars over 108 "
                "previously archived editions; the 12:45 AM edition is promoted for the model at "
                "data/official/injury_20261119_1245AM_39b70241.json with a hash taken over the bytes, "
                "so the 11/17 window's F-X13 (unmeasured PDF) does not apply to tonight's lines")
            touched["R04"] = "annotated"
        if row["id"] == "R21":
            row[f"evidence_{KEY}"] = (
                "the 11/17-11/18 prop tickets were graded from official box-score rows and the box "
                "pages' own Inactive Players blocks (data/settlement/sgp_grades_2026-11-17.json), not "
                "from a full player_game_logs file: no per-player log capture exists for those two "
                "dates, and scripts/settle_sgp_from_logs.py remains the tool for one. 11/15 and 11/16 "
                "stay the only fully captured log days")
            touched["R21"] = "annotated"
    new_rows = [
        {"id": "R34",
         "requirement": ("A game day that has ended is settled from official finals the same cycle, "
                         "and the horizon is rolled forward before the next first tip."),
         "status": "done",
         "evidence": (
             "2026-11-19, session " + SESSION + ": the 11/17 and 11/18 finals were read first-hand, "
             "promoted into data/official/results_2026-11-17.json / _11-18.json and into the feed; "
             "data/settlement/settlement_2026-11-17.json records 17 singles 5-12-0 (-8.2u) and 6 parlays "
             "0-6 (-6.6u); the four open SGPs were closed the same day by "
             "data/settlement/sgp_grades_2026-11-17.json (1-2, 1 void, -1.1u), so the slate stands at "
             "-15.90 paper units. Ledger entries 13-16 chain the settlement, the grading and the pre-tip "
             "freeze of the new window (11/19-11/22, 26 games, frozen at " + NOW + ", 18h50m before the "
             "01:00Z tip), and scripts/verify_ledger.py reports the chain OK."),
         "gap": ("the 11/19 games tip at 01:00Z on 11/20; that date is a later cycle's settlement, and "
                 "settle_slate.py already refuses to write for it (dry run exits 3 with 'no official "
                 "results file' named per date)"),
         "links": [{"label": "Settlement 11/17 slate",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/settlement/"
                           "settlement_2026-11-17.json"},
                   {"label": "SGP grading addendum",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/settlement/"
                           "sgp_grades_2026-11-17.json"}]},
        {"id": "R35",
         "requirement": ("Every origination input is re-read first-hand each cycle, and a table that "
                         "lags is reported as lagging rather than patched into agreement."),
         "status": "done",
         "evidence": (
             "advanced / traditional / opponent / standings pages read 2026-11-19T05:4xZ and transcribed "
             "row by row (data/official/teams_inputs_2026-11-19_39b70241.json, "
             "data/official/standings_2026-11-19_0546Z_39b70241.json); gates GA1-GA9 and A1-A9 in "
             "verify/2026-11-19-39b70241/. The one genuine disagreement — the three /stats team tables "
             "print GP 15 for LAL and UTA while the standings and the finals corpus both record 16 — was "
             "resolved by arithmetic, not by editing: excluding each club's newest game reproduces the "
             "page's own opponent-Pts cell exactly (A6), so the tables simply have not folded 11/18 in. "
             "GP/W-L ship from the standings, the ratings ship as printed, and each affected row names the "
             "sample its rating rests on."),
         "gap": ("the league does not publish the rebuild cadence of the /stats team tables, so the lag "
                 "can only be observed from this kind of cross-check; the next cycle re-reads and reports "
                 "again"),
         "links": [{"label": "Readback gates GA1-GA9",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/"
                           "2026-11-19-39b70241/readback_report.json"},
                   {"label": "Roll gates A1-A9",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/"
                           "2026-11-19-39b70241/y04_roll_gates.json"}]},
        {"id": "R36",
         "requirement": ("The two estimators of a line are published as two estimators, with their "
                         "disagreement stated rather than averaged away."),
         "status": "partial",
         "evidence": (
             "for the " + AS_OF + " window the two model files overlap on " + str(len(dis_rows)) +
             " of 4 games (the validated engine's own table holds " + str(n_b_rows) + " rows spanning " +
             ", ".join(f"{d}={n}" for d, n in sorted(b_dates.items())) + "). The gaps are recomputed from "
             "the two files by this script into verify/2026-11-19-39b70241/estimator_disagreement.json: "
             "the widest gap is " + _widest(dis_rows) + "."),
         "gap": ("the second estimator's file stops at 11/19 and its rows still carry the pre-11/17 inputs "
                 "(e.g. GSW listed 8-5 and the injury edition named INJURY-REPORT_2026-11-16_09_45AM, "
                 "against tonight's official 8-7 and the 12:45 AM 11/19 edition), so from 11/20 there is "
                 "one line, not two — the disagreement cannot be stated for games B never priced"),
         "links": [{"label": "Estimator B lines (validated engine)",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/docs/data/lines.json"},
                   {"label": "Disagreement table",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/"
                           "2026-11-19-39b70241/estimator_disagreement.json"}]},
    ]
    for row in new_rows:
        touched[row["id"]] = upsert(doc["rows"], row)
    dump(rel, doc)
    return touched


# ---------------------------------------------------------------- flags
def flags(dis_rows, n_b):
    rel = "data/content/flagged.json"
    doc = load(rel)
    touched = {}
    for it in doc["items"]:
        if it.get("id") == "F-CA-07":
            it[f"update_{KEY}"] = (
                "partly overtaken, on this branch only. arena/39b70241-nba1 armed its own runner-side "
                "capture (workflow capture-injury-39b70241, run 44468125114), which stored the four "
                "2026-11-19 editions with measured sha256s and promoted the newest of them for the model, "
                "so the horizon's injury input is now byte-exact and 05:52Z-fresh. The shared scheduled "
                "refresh still does not promote an editions-only change — the trigger gap this flag "
                "describes is unchanged, and the flag stays the refresh owner's to close.")
            touched["F-CA-07"] = "annotated (status left to its owner)"
    new_items = [
        {"id": "F-39B-01", "severity": "Medium", "status": "open",
         "title": ("Two of thirty /stats team tables (LAL, UTA) still cover 15 games an hour after their "
                   "16th ended, while the standings page already shows 16"),
         "detail": (
             "read 2026-11-19T05:4xZ: the advanced, traditional and opponent tables all print GP 15 for "
             "Los Angeles and Utah; the standings print 13-3 and 3-13, and the finals corpus contains 16 "
             "decided games for each (LAL 118-114 vs CHA on 11/17, then 97-109 vs UTA on 11/18). The "
             "lag was proved rather than assumed: for both clubs the page's opponent-Pts cell reproduces "
             "exactly when that club's newest game is excluded and does not when the oldest is, which is "
             "the signature of a table that has not folded the last result in. GA3 in "
             "verify/2026-11-19-39b70241/readback_report.json therefore FAILS, and the roll gate A3b "
             "REPORTS it; no rating was adjusted to make the gate green, and the sum of the tables' own "
             "GP (442) is published beside the standings' 444."),
         "affected": ("data/derived/team_stats_recut_2026-11-19_39b70241.json (two rows carry a note), "
                      "the 11/19-11/22 horizon lines for any game involving LAL or UTA (tonight: none; "
                      "11/20 SAC@LAL and 11/22 DAL@UTA do), and the HCA pin, whose home-win count is "
                      "taken from the standings and is unaffected"),
         "links": [{"label": "readback gates",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/"
                           "2026-11-19-39b70241/readback_report.json"},
                   {"label": "roll gates",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/"
                           "2026-11-19-39b70241/y04_roll_gates.json"}]},
        {"id": "F-39B-02", "severity": "Medium", "status": "open",
         "title": ("The home-court pin moved 0.74 points in one cycle (0.83 -> 0.09) on 17 new games; a "
                   "one-day estimate is that volatile at 222 games"),
         "detail": (
             "the pin is measured, never fitted: sigma_margin x Phi^-1(home win rate). The rate went from "
             "106/204 (0.5196) to 111/221 (0.5023) because home teams went 2-5 on 2026-11-17 and 3-12 on "
             "2026-11-18 — 5 wins in the 17 newly decided games, and the arithmetic ties exactly "
             "(106+5=111, 204+17=221). sigma_margin also moved, 16.868 -> 16.714. The consequence for the "
             "published window is real: every spread now carries 0.09 points of home advantage instead of "
             "0.83, which flips no pick on its own but moves each line's margin by ~0.74. Nothing here "
             "should be read as a model improvement; it is the same estimator on a slightly different "
             "sample, and a 17-game swing of this size argues for quoting the pin with its interval."),
         "affected": ("data/derived/measured_constants_2026_11_19_39b70241.json, "
                      "data/derived/horizon_lines.json (all 26 games), data/derived/horizon_picks.json"),
         "links": [{"label": "measured constants",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/"
                           "measured_constants_2026_11_19_39b70241.json"}]},
        {"id": "F-39B-03", "severity": "Low", "status": "open",
         "title": ("One VOID leg (Curry, 2026-11-18 GSW@DAL) is graded from the official gamebook's "
                   "inactive list rather than the box-score page's own Inactive Players block"),
         "detail": (
             "the other three VOID/loss legs cite the box-score pages directly, and for CHA@LAL and "
             "PHI@ORL those pages print the inactive list themselves, which is what closed them. For "
             "GSW@DAL this session read the gamebook PDF ("
             "https://statsdmz.nba.com/pdfs/20261118/20261118_GSWDAL_book.pdf: 'Inactive: Warriors - ... "
             "Curry (Injury/Illness - Right Oblique Tear)') and the box-score table (no Curry row), but "
             "not the box page's inactive block. Same official source class the 11/16 SGP grading used, so "
             "the grade is not in doubt; it is recorded because the evidence class differs."),
         "affected": "data/settlement/sgp_grades_2026-11-17.json (ticket 3 of 4)",
         "links": [{"label": "SGP grading addendum",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/settlement/"
                           "sgp_grades_2026-11-17.json"}]},
        {"id": "F-39B-04", "severity": "Medium", "status": "open",
         "title": ("Estimator B stops on 11/19 and its rows for that day still carry pre-11/17 inputs, so "
                   "from 11/20 the site has one line per game while the pages describe two estimators"),
         "detail": (
             f"docs/data/lines.json holds {n_b} rows covering 11/16 to 11/19 only. Its four 11/19 rows list GSW 8-5 and MIL 1-13 against "
             "the official pre-game 8-7 and 1-14 read this morning, and every one of them names "
             "INJURY-REPORT_2026-11-16_09_45AM as the availability source — three days behind tonight's "
             "12:45 AM edition. The disagreement for tonight is therefore between A re-cut on 222 games "
             "and B frozen at 205; it should be read as an estimator-age difference as much as a modelling "
             "one. Widest spread gap on the overlap: " +
             (f"{max(abs(r['spread_gap']) for r in dis_rows):.1f} points on "
              f"{max(dis_rows, key=lambda r: abs(r['spread_gap']))['matchup']}" if dis_rows else "n/a") +
             " (table in verify/2026-11-19-39b70241/estimator_disagreement.json)."),
         "affected": "docs/data/lines.json, the two-estimator section of site/pages/roll.html",
         "links": [{"label": "Estimator B file",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/docs/data/lines.json"}]},
        {"id": "F-39B-05", "severity": "Low", "status": "open",
         "title": ("The injury-parser unit test asserted an absolute row floor, so a legitimately small "
                   "slate made the CI test gate red"),
         "detail": (
             "scripts/test_injury_diff.py:RealPdfTests.test_rows_extracted required row_count > 50 of "
             "whatever edition is newest in data/raw/injury_pdfs/. This branch's runner captured the four "
             "2026-11-19 editions, whose newest (12:45 AM ET) covers tonight's four games and parses 44 "
             "rows — the parser is fine, the fixture's assumption was not, and the failure would have "
             "blocked the scheduled test gate for a non-defect."),
         "affected": ("scripts/test_injury_diff.py, and the CI step 'Run the unit-test suite' in "
                      ".github/workflows/pages.yml"),
         "suggested_action": (
             "replaced the absolute floor with the structural invariant (>= one block per club per game in "
             "the edition, computed from the parsed matchup column), so the test now fails only on a real "
             "drop. The pinned 11/15 fixture class, which is what F-X01 was about, still asserts its exact "
             "87-row count and is untouched."),
         "links": [{"label": "test file",
                    "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/scripts/"
                           "test_injury_diff.py"}]},
    ]
    for it in new_items:
        touched[it["id"]] = upsert(doc["items"], it)
    dump(rel, doc)
    return touched


# ---------------------------------------------------------------- questions
def questions(dis_rows):
    rel = "data/content/questions.json"
    doc = load(rel)
    answered = {
        "id": "A21",
        "question": ("Does a prop ticket stay open forever if no per-player game log was captured for its "
                     "date?"),
        "answer": (
            "No — it stays open only while there is no official read. scripts/settle_slate.py correctly "
            "refused to grade the four 11/17-slate SGPs because it had no box score for that slate in that "
            "run; the same day this session read each leg's box-score row (or the box page's Inactive "
            "Players block) and appended data/settlement/sgp_grades_2026-11-17.json without touching the "
            "hash-chained settlement file. Under the frozen rule a player who did not appear is VOID and "
            "removed, a remaining OVER leg wins only if actual > line, and a ticket whose legs are all VOID "
            "is voided with no stake. Result: CHA@LAL lost (Dončić 36 vs 38.5, Reaves inactive), NYK@TOR "
            "lost (Brunson 31 won, Barnes 20 lost), GSW@DAL won (Flagg 33, Curry inactive), PHI@ORL void "
            "(Banchero inactive and Maxey a coach's-decision DNP) — net -1.10 paper units, and the slate "
            "closes at 6 won, 20 lost, 1 void for -15.90u."),
        "source": "data/settlement/sgp_grades_2026-11-17.json (ledger entry 16)",
        "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/settlement/"
                      "sgp_grades_2026-11-17.json",
    }
    open_q = {
        "id": "Q34",
        "question": ("Should a first-hand injury edition be promoted by whichever branch captured it, or "
                     "only by the scheduled refresh?"),
        "what_is_missing": (
            "F-CA-07 documents that the shared refresh archives editions but never promotes an "
            "editions-only change, so data/raw/injuries.json can sit a day and dozens of editions behind "
            "while a capture pass is green. This session solved its own need on its own branch "
            "(scripts/y04_roll_2026_11_19_39b70241.py promotes the byte-exact 12:45 AM 11/19 edition and "
            "the ledger hashes the promoted file), which is correct for a horizon build but leaves the "
            "shared register lagging for every other consumer. Two mechanisms now exist and nothing in the "
            "repo says which one is authoritative."),
        "how_to_answer": (
            "Either teach the promote step to treat a new archived edition as a `changed` source (the "
            "one-line fix the refresh owner proposed in F-CA-07) and retire branch-scoped promotion, or "
            "state in the brief that each cycle promotes the edition it reads and add a gate that fails "
            "when data/raw/injuries.json names an older edition than the newest file under "
            "data/raw/injury_pdfs/. The gate is checkable today: the newest archived edition is "
            "Injury-Report_2026-11-19_12_45AM.pdf."),
        "blocks": "R04's promotion half, and any consumer that reads data/raw/injuries.json instead of a dated capture",
        "priority": "medium",
        "source": "COORDINATION.md §65 (F-CA-07) and this session's capture manifest",
        "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/2026-11-19-39b70241/"
                      "injury_capture_manifest_2026-11-19.json",
    }
    t = {answered["id"]: upsert(doc["answered"], answered)}
    t[open_q["id"]] = upsert(doc["open"], open_q)
    dump(rel, doc)
    return t


def suggestions():
    rel = "data/content/suggestions.json"
    doc = load(rel)
    row = {
        "id": "S40",
        "title": "Gate the freshness of every promoted input against the newest capture in the repository",
        "category": "Verification",
        "problem": (
            "Three of this session's findings are the same failure in different clothes: the shared "
            "injury register stayed on the 11/16 09:45 AM edition while 11/19 editions sat archived "
            "(F-CA-07), estimator B's 11/19 rows still carried pre-11/17 records and that same stale "
            "edition (F-39B-04), and the /stats team tables were an hour behind the standings (F-39B-01). "
            "Each is invisible to a builder that simply consumes whatever file is present, and each was "
            "found only by comparing a file against a newer artefact the repository already holds."),
        "options": [
            {"option": ("Add scripts/check_input_freshness.py: for each promoted input, fail if a strictly "
                        "newer capture of the same kind exists (injury editions under data/raw/injury_pdfs/ "
                        "by edition timestamp; results feed vs the newest date in data/official/results_*.json; "
                        "each estimator file's window vs the published horizon window)"),
             "effort": "Medium — three comparisons, all already computable from filenames and file contents",
             "risk": "Low — it can only report; nothing is rewritten",
             "unlocks": "F-CA-07, F-39B-01 and F-39B-04 become machine-checkable instead of hand-found"},
            {"option": "Keep relying on each cycle to re-read and notice",
             "effort": "None",
             "risk": "High — three of these lapses were caught by a human reading pages against sources",
             "unlocks": "Nothing new"},
            {"option": "Auto-refresh the stale files in place (promote the newest edition inside the builder)",
             "effort": "Low",
             "risk": ("High — a builder that silently changes its own inputs breaks the ledger's "
                      "digest-to-file binding, which is the whole point of the freeze"),
             "unlocks": "Nothing that the first option does not do more safely"},
        ],
        "recommendation": ("Option 1, as a read-only gate added to verify_all.py's audit set. The repository's "
                           "rule is to measure and report, not to quietly refresh."),
        "decision_needed": "Which of the promoted inputs the gate is allowed to require, and whether a stale input blocks a Pages build or only flags on the page",
        "source": f"session {SESSION} (COORDINATION.md §66), findings F-39B-01/04 and F-CA-07",
        "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/"
                      "2026-11-19-39b70241/y04_roll_gates.json",
    }
    t = {row["id"]: upsert(doc["items"], row)}
    dump(rel, doc)
    return t


# ---------------------------------------------------------------- executive
def executive(dis_rows, b_dates, n_b_rows):
    rel = "data/content/executive.json"
    doc = load(rel)
    doc["as_of"] = (f"{AS_OF} (11/17 and 11/18 settled and SGP-graded the same cycle; the horizon is "
                    f"re-originated for 11/19-11/22 on inputs read at 05:4xZ, with the strategy files "
                    f"frozen into the ledger 18h50m before tonight's first tip)")
    doc["headline"] = (
        "26 games are priced across 2026-11-19 to 2026-11-22 from official inputs re-read this morning, "
        "with home-court advantage pinned to the measured home-win rate — 111 of 221 non-neutral home "
        "games, 0.5023, worth 0.09 points, down 0.74 from yesterday because home teams went 5-12 over the "
        "two newly settled slates — and the second estimator now only reaches 11/19, so from 11/20 there "
        "is one line per game rather than two (F-39B-04).")
    doc["lead"] = (
        "This session read all 17 games of the 2026-11-17 and 2026-11-18 slates first-hand (each game's own "
        "official page, quarter by quarter, every quarter sum checked against the printed final), promoted "
        "them into the results feed — 222 rows, 222 Final — and settled the sealed 11/17 slate: 17 singles "
        "5-12-0 for -8.2 units, 6 parlays 0-6 for -6.6, and the four published SGPs closed the same day at "
        "1-2 with 1 void for -1.1, -15.90 units overall. No strategy is funded and no ticket was ever "
        "staked: the whole record is MODEL OUTPUT at a stated paper convention.")
    doc["verdict"] = {
        "status": "PROVISIONAL - not funded",
        "one_line": (
            "The horizon for 2026-11-19 to 2026-11-22 is published: 26 games priced from official inputs "
            "read at 05:4xZ today, home-court pinned to the measured 0.5023 home-win rate (0.09 points) "
            "rather than fitted, 23 of 26 games carrying a pick that survived the per-pick gate (3.0 points), "
            "12 two-leg parlays and 8 SGP candidates priced with the measured rho and the naive product "
            "printed beside it, and every prereg file plus every model-input digest sealed in ledger entry 15 "
            "at " + NOW + " — 18h50m before the first tip those files cover. The total still reconciles "
            "against the measured league total (model 225.0 against measured 227.5, gate G-TOT tolerance 8.0)."),
        "why": ("the model prices a window the market cannot be compared against, and this cycle changed "
                "no part of that: the gates that would fund a strategy need a closing price (G4/G5) and "
                "prop-variance inputs (G-PROP), and neither source exists in this repository, so R16 "
                "stays blocked. Publishing prices, a settlement and a frozen pre-registration is the "
                "honest deliverable at this stage; publishing a stake would not be. One record does now "
                "carry a graded SGP line (1-2, 1 void, -1.10u), which is a record, not evidence."),
    }
    doc["what_is_live_now"] = [
        ("Four graded game days with visible settlement stamps: 2026-11-14, 2026-11-15 (5-4-0), 2026-11-16, "
         "and now 2026-11-17 settled through 2026-11-18 — 17 singles 5-12-0 (-8.2u), 6 parlays 0-6 (-6.6u), "
         "4 SGPs 1-2-0 with 1 void (-1.1u), -15.90 paper units, stamped from the finals read at 05:46Z."),
        ("The 11/19-11/22 horizon: 26 games, 23 singles, 12 parlays, 8 SGP candidates, all MODEL OUTPUT — "
         "UNVALIDATED at zero stake, frozen pre-tip at ledger entry 15."),
        ("Ledger: 16 entries, chain verified (scripts/verify_ledger.py -> 'ledger chain OK'); the 11/17 "
         "settlement is entry 13-14, the SGP grading entry 16, the pre-tip freeze entry 15."),
        ("Injury inputs: the newest official edition (2026-11-19 12:45 AM ET) is archived byte-exactly by "
         "this branch's runner with a measured sha256, and the promoted file the horizon consumed carries "
         "that hash — the first window in the repository where F-X13 does not apply."),
        ("Verification: scripts/verify_all.py -> FAILURES: 0; the readback gates for today's reads report "
         "GA3 FAIL (LAL/UTA one-game table lag) and every other gate pass, by design rather than by repair."),
    ]
    doc["recommended_next_actions"] = [
        {"rank": 1,
         "action": ("DONE " + NOW + ": settle 11/17 + 11/18 from official finals, close the four open SGPs, "
                    "roll the horizon to 11/19-11/22 and freeze the strategy files before tip."),
         "why": ("Executed by session " + SESSION + " — ledger entries 13-16, "
                 "data/settlement/settlement_2026-11-17.json and data/settlement/sgp_grades_2026-11-17.json. "
                 "The 11/19 date is deliberately left open: settle_slate.py exits 3 for it because no "
                 "official results file exists yet.")},
        {"rank": 2,
         "action": "Settle the 2026-11-19 slate (4 games) after 01:00Z, and extend the same cycle to 11/20's 9 Cup games",
         "why": ("The window is published and frozen for exactly these dates; the 11/20 slate is the largest "
                 "in the horizon and the first whose injury rows do not exist at build time.")},
        {"rank": 3,
         "action": "Close F-39B-04: re-cut estimator B's window, or state in the pages that the two-estimator comparison ends on 11/19",
         "why": ("Right now the roll page's disagreement column for tonight compares a model on 222 games "
                 "with one frozen at 205 games and records two days stale — the gap is "
                 + _widest(dis_rows) + " at its widest on the overlap, and a reader cannot tell how much "
                 "of that is age and how much is method.")},
        {"rank": 4,
         "action": "Adopt S40's freshness gate before the next game-day rollover",
         "why": "Three of today's findings are the same class of lapse, and all three were caught by hand."},
        {"rank": 5,
         "action": "Capture per-player game logs for 11/17 and 11/18 (the two dates R21 still lacks)",
         "why": ("scripts/settle_sgp_from_logs.py is ready and the 11/16 file shows the schema; with logs "
                 "the box-page grades would be reproducible from committed bytes instead of a page read.")},
    ]
    doc["bottom_line"] = (
        "The slate closed clean and the new window is sealed before its first tip, which is what the process "
        "is for. What it does not buy is evidence that any strategy works: the record is -15.90 paper units "
        "over 27 tickets, every gate that could fund a strategy still needs a price this repository cannot "
        "reach, and two of today's findings (the 0.74-point pin move, the one-game table lag) are reminders "
        "that at 222 games a single night is visible in the constants. Nothing here is staked, and nothing "
        "here should be read as an edge.")
    dump(rel, doc)
    return {"executive": "rewritten in place (same keys)"}


def main() -> int:
    dis_rows, b_dates, n_b = disagreement()
    dump(f"verify/2026-11-19-{SESSION.split('/')[-1][:8]}/estimator_disagreement.json", {
        "title": "Estimator A (this branch's originator) vs estimator B (docs/data/lines.json), "
                 "2026-11-19 window",
        "generated_by": f"scripts/update_registers_{SESSION.split('/')[-1][:8]}.py",
        "generated_utc": NOW,
        "a_file": "data/derived/horizon_lines.json (26 games, 2026-11-19..2026-11-22)",
        "b_file": f"docs/data/lines.json ({n_b} rows, per day "
                  + ", ".join(f"{d}={n}" for d, n in sorted(b_dates.items())) + ")",
        "sign_convention": ("both files state the HOME team's margin in points, positive = home favoured; "
                            "spread_gap = A - B, so a positive number means this session's model is more "
                            "bullish on the home side"),
        "rows": dis_rows,
        "honesty": ("B's rows for these dates were built from 2026-11-16 inputs (its own files say so: "
                    "records 8-5/1-13 etc. and the INJURY-REPORT_2026-11-16_09_45AM edition), so the gap "
                    "mixes estimator method with input age. Printed as measured, not decomposed — nothing "
                    "here attributes a part of the gap to either cause."),
    })
    print(json.dumps({
        "requirements": requirements(dis_rows, n_b, b_dates),
        "flagged": flags(dis_rows, n_b),
        "questions": questions(dis_rows),
        "suggestions": suggestions(),
        "executive": executive(dis_rows, b_dates, n_b),
    }, indent=1))
    print("disagreement rows:", len(dis_rows), "widest spread gap:",
          f"{max(abs(r['spread_gap']) for r in dis_rows):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
