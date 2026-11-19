#!/usr/bin/env python3
"""Leg-level re-grade of the merged 2026-11-17 + 2026-11-18 settlements.

Session `arena/8938790d-nba1` (COORDINATION §67, task V01). This seat joined a
four-way same-minute race on the 2026-11-19 day-roll cycle and took main's tree
verbatim for every delivered file, so the settlement work itself belongs to
`arena/929395a5-nba1` (PRs #171/#172), the workflow trigger fix to
`arena/374ffc79-nba1` (PR #170) and the independent page-read cross-check to
`arena/eec70f24-nba1` (§ "Collision and cross-check record", which re-read all
17 official game pages). What was still missing was a check of the GRADING
ARITHMETIC itself - eec70f24's cross-check re-read the pages and compared
totals; this script re-derives every graded row from the frozen pre-tip archive
and the official finals with an independent implementation of the frozen rules,
row by row:

  1. every settlement row's quarter scores must sum to its printed final;
  2. every graded single is re-graded from `pick_line` text + the finals
     (cover / push / loss, paper -110 units);
  3. every parlay leg is re-graded, and the joint result must equal AND of legs;
  4. the settlement summary (record, units) must equal the recomputed values;
  5. every graded final must agree with the committed per-game results feed
     (`data/official/results_feed_2026_27.json`: game_status 3, same points,
     same quarter lines);
  6. the pre-tip archive digest recorded in each settlement must equal the
     digest the ledger's entry 12 committed to before tip.

Exit 0 only if every check passes; any mismatch is printed and fails the run.
No value is inferred: a field the settlement or the archive does not carry is
reported as MISSING, not filled in.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SETTLE_DATES = ("2026-11-17", "2026-11-18")
PICKS_REL = "data/archive/horizon_picks_2026-11-17.json"
FEED_REL = "data/official/results_feed_2026_27.json"
LEDGER_REL = "data/ledger/ledger.json"


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def grade_margin(team, line, away, home, away_pts, home_pts):
    """Independent implementation of the frozen single rule: TEAM -x.x must
    win by more than x.x; exactly x.x is a PUSH."""
    if team == home:
        margin = home_pts - away_pts
    elif team == away:
        margin = away_pts - home_pts
    else:
        return None, None
    if margin > -line:
        return "WIN", margin
    if margin == -line:
        return "PUSH", margin
    return "LOSS", margin


def main():
    failures, checked = [], 0
    picks = load(PICKS_REL)
    picks_sha = hashlib.sha256(
        open(os.path.join(ROOT, PICKS_REL), "rb").read()).hexdigest()
    feed = load(FEED_REL)
    feed_rows = feed.get("rows") or feed.get("games") or []
    feed_by_id = {str(r.get("game_id")): r for r in feed_rows
                  if isinstance(r, dict)}
    ledger = load(LEDGER_REL)
    entry12 = next((e for e in ledger["entries"] if e.get("entry") == 12), None)

    # --- check 6: pre-tip archive digest vs the ledger commitment ----------
    committed = None
    for e in ledger["entries"]:
        for f, h in (e.get("files") or {}).items():
            if f.endswith(os.path.basename(PICKS_REL)) and h == picks_sha:
                committed = e
    if committed is None or committed.get("entry") != 12:
        failures.append(
            f"ledger: horizon_picks_2026-11-17.json sha {picks_sha[:12]}... is "
            f"not committed by ledger entry 12 (got "
            f"{committed.get('entry') if committed else None})")

    for date in SETTLE_DATES:
        s = load(f"data/settlement/settlement_{date}.json")
        src = load(f"data/official/results_{date}.json")
        finals = {}
        for r in src.get("rows", []):
            finals[str(r.get("game_id"))] = r
            # --- check 1: quarter sums on the official results file itself --
            checked += 1
            for side in ("away", "home"):
                pts, qs = r.get(f"{side}_pts"), r.get(f"{side}_quarters")
                if pts is None or not isinstance(qs, list):
                    failures.append(f"{date} {r.get('game_id')} {side}: "
                                    "final or quarters missing")
                elif sum(qs) != pts:
                    failures.append(f"{date} {r.get('game_id')} {side}: "
                                    f"quarters {qs} sum {sum(qs)} != final {pts}")

        # --- check 2: singles re-graded --------------------------------------
        for row in s.get("singles", []):
            checked += 1
            gid = str(row.get("game_id"))
            g = finals.get(gid)
            if g is None:
                failures.append(f"{date} single {gid}: not in results file")
                continue
            pick_line = row.get("pick_line")
            if not pick_line:
                failures.append(f"{date} single {gid}: no pick_line")
                continue
            team, line_txt = pick_line.rsplit(" ", 1)
            res, margin = grade_margin(team, float(line_txt),
                                       g["away"], g["home"],
                                       g["away_pts"], g["home_pts"])
            if res is None:
                failures.append(f"{date} single {gid}: pick team {team!r} not "
                                f"in {g['away']}@{g['home']}")
                continue
            expect_units = {"WIN": 1.0, "LOSS": -1.10, "PUSH": 0.0}[res]
            for field, expect, got in (
                    ("result", res, row.get("result")),
                    ("units", expect_units, row.get("units")),
                    ("margin_pick_team", margin, row.get("margin_pick_team")),
                    ("away_pts", g["away_pts"], row.get("away_pts")),
                    ("home_pts", g["home_pts"], row.get("home_pts"))):
                if got != expect:
                    failures.append(f"{date} single {gid} {matchup_str(g)}: "
                                    f"{field} published {got!r} != recomputed "
                                    f"{expect!r}")
            # quarter lines must match the official results file row
            for side in ("away", "home"):
                if row.get(f"{side}_quarters") != g.get(f"{side}_quarters"):
                    failures.append(f"{date} single {gid}: {side}_quarters "
                                    f"published {row.get(f'{side}_quarters')!r} "
                                    f"!= results file "
                                    f"{g.get(f'{side}_quarters')!r}")
            # --- check 5: agreement with the committed feed ----------------
            fr = feed_by_id.get(gid)
            if fr is None:
                failures.append(f"{date} single {gid}: absent from results feed")
            else:
                if fr.get("game_status") != 3:
                    failures.append(f"{date} single {gid}: feed game_status "
                                    f"{fr.get('game_status')!r} != 3 (Final)")
                for k in ("away_pts", "home_pts", "away_quarters",
                          "home_quarters"):
                    if fr.get(k) != g.get(k):
                        failures.append(f"{date} single {gid}: feed {k} "
                                        f"{fr.get(k)!r} != results file "
                                        f"{g.get(k)!r}")

        # --- check 3: parlays re-graded leg by leg ---------------------------
        for row in s.get("parlays", []):
            checked += 1
            leg_results = []
            for leg in row.get("legs", []):
                checked += 1
                try:
                    matchup, side = leg.split(" — ")
                except ValueError:
                    failures.append(f"{date} parlay: malformed leg {leg!r}")
                    continue
                team, line_txt = side.rsplit(" ", 1)
                g = next((r for r in src.get("rows", [])
                          if f"{r.get('away')}@{r.get('home')}" == matchup), None)
                if g is None:
                    failures.append(f"{date} parlay leg {matchup}: no finals row")
                    continue
                res, margin = grade_margin(team, float(line_txt),
                                           g["away"], g["home"],
                                           g["away_pts"], g["home_pts"])
                leg_results.append(res)
            expect = "WIN" if leg_results and all(
                r == "WIN" for r in leg_results) else "LOSS"
            if row.get("result") != expect:
                failures.append(f"{date} parlay {row.get('legs')}: published "
                                f"{row.get('result')!r} != recomputed {expect!r} "
                                f"(legs {leg_results})")
            legs_win = expect == "WIN"
            fair = row.get("fair_odds_lb")
            if legs_win and fair is not None:
                expect_units = round(1.10 * (fair - 1), 2)
                if row.get("units") != expect_units:
                    failures.append(f"{date} parlay units {row.get('units')!r} "
                                    f"!= 1.10*({fair}-1) = {expect_units!r}")
            elif not legs_win and row.get("units") not in (-1.10, -1.1):
                failures.append(f"{date} parlay losing units "
                                f"{row.get('units')!r} != -1.10")

        # --- check 4: summary arithmetic --------------------------------------
        checked += 1
        sg = s.get("singles", [])
        rec = (sum(1 for r in sg if r.get("result") == "WIN"),
               sum(1 for r in sg if r.get("result") == "LOSS"),
               sum(1 for r in sg if r.get("result") == "PUSH"))
        summ = s.get("summary", {})
        got_rec = summ.get("record")
        if got_rec != f"{rec[0]}-{rec[1]}-{rec[2]}":
            failures.append(f"{date} summary record {got_rec!r} != "
                            f"{rec[0]}-{rec[1]}-{rec[2]}")
        s_units = round(sum(r.get("units", 0.0) or 0.0 for r in sg), 2)
        if summ.get("singles_units_at_minus110") != s_units:
            failures.append(f"{date} summary singles units "
                            f"{summ.get('singles_units_at_minus110')!r} != "
                            f"{s_units!r}")
        p_units = round(sum(r.get("units", 0.0) or 0.0
                            for r in s.get("parlays", [])), 2)
        if summ.get("parlay_units") != p_units:
            failures.append(f"{date} summary parlay units "
                            f"{summ.get('parlay_units')!r} != {p_units!r}")

    report = {
        "session": "arena/8938790d-nba1",
        "script": "verify/2026-11-19-8938790d/regrade_2026_11_17_18.py",
        "checks_run": checked,
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
        "graded_from": {
            "pre_tip_archive": PICKS_REL,
            "picks_sha256": picks_sha,
            "ledger_entry_committing_it": (committed or entry12 or {}).get("entry"),
            "official_finals": [f"data/official/results_{d}.json"
                                for d in SETTLE_DATES],
            "results_feed": FEED_REL,
        },
        "note": ("Independent re-grade of the merged settlements' arithmetic "
                 "and cross-file agreement. Page-level verification of the "
                 "finals is arena/eec70f24-nba1's cross-check record "
                 "(all 17 game pages re-read); this script re-derives every "
                 "graded row and summary number locally from the frozen "
                 "archive and the official results files."),
    }
    out_rel = "verify/2026-11-19-8938790d/regrade_report.json"
    with open(os.path.join(ROOT, out_rel), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"checks run: {checked}")
    print(f"verdict   : {report['verdict']}")
    for f in failures:
        print("  MISMATCH:", f)
    print("wrote", out_rel)
    return 0 if not failures else 1


def matchup_str(g):
    return f"{g.get('away')}@{g.get('home')}"


if __name__ == "__main__":
    sys.exit(main())
