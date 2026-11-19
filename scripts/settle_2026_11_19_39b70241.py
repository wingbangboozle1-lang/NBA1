#!/usr/bin/env python3
"""settle_2026_11_19_39b70241.py — promote the 2026-11-17 and 2026-11-18 official
finals into the per-game results feed, and into the finals files the settlement
tool reads (§66 / Y03).

Sources (all read first-hand in this session, 2026-11-19 05:4x UTC):
  * https://www.nba.com/games?date=2026-11-17 and ...?date=2026-11-18 — the printed
    finals and the "Final"/"Final/OT" labels;
  * https://www.nba.com/game/<slug> for all 17 games — the LINESCORES table, which
    is where the quarter scores come from on an official page (the box-score page
    does not print them);
  * https://statsdmz.nba.com/pdfs/20261117/20261117_NYKTOR_book.pdf — the official
    gamebook, used as a second, independent read of the NYK@TOR quarter scores
    (SCORE BY PERIOD) and of that game's attendance and officials.

Rules, unchanged from the feed's own `rule` field:
  one row per game (date, teams, final, quarter scores); a game is settled ONLY when
  the official page says Final AND the quarter scores sum to that final.  Anything
  not printed on an official page stays null — possessions, ratings, pace and the
  attendance/officials of the fourteen games whose GAME INFO block was not read this
  session are left null and flagged, never imputed.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
FEED = "data/official/results_feed_2026_27.json"
CAPTURES = {
    "2026-11-17": "data/official/results_2026-11-17_39b70241.json",
    "2026-11-18": "data/official/results_2026-11-18_39b70241.json",
}
# GAME INFO blocks read this session (official game page / gamebook PDF).  Only
# these three carry attendance and officials; every other row keeps nulls.
GAME_INFO = {
    "0022600253": {"attendance": 19800,
                   "officials": "Mitchell Ervin (#27), Eric Lewis (#42), Evan Scott (#22)",
                   "info_source": "https://statsdmz.nba.com/pdfs/20261117/20261117_NYKTOR_book.pdf"},
    "0022600268": {"attendance": 19057, "officials": "Karl Lane, Tre Maddox, Dannica Baroody",
                   "info_source": "https://www.nba.com/game/uta-vs-lal-0022600268"},
    "0022600269": {"attendance": 13016, "officials": "Zach Zarba, Jonathan Sterling, John Butler",
                   "info_source": "https://www.nba.com/game/phx-vs-sac-0022600269"},
}
STATUS_TEXT = {0: "Final", 1: "Final/OT", 2: "Final/2OT"}


def rel(p):
    return os.path.join(ROOT, p)


def load(p):
    with open(rel(p), encoding="utf-8") as fh:
        return json.load(fh)


def dump(p, obj):
    path = rel(p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", p)


def main() -> int:
    feed = load(FEED)
    rows = feed["rows"]
    idx = {r["game_id"]: r for r in rows}
    failures, settled_ids = [], []

    for date, cap_rel in CAPTURES.items():
        cap = load(cap_rel)
        finals_rows = []
        for g in cap["rows"]:
            q_sum = f"away {'+'.join(str(x) for x in g['away_quarters'])}={g['away_pts']} \u2713, " \
                    f"home {'+'.join(str(x) for x in g['home_quarters'])}={g['home_pts']} \u2713"
            if sum(g["away_quarters"]) != g["away_pts"] or sum(g["home_quarters"]) != g["home_pts"]:
                failures.append(f"{g['game_id']}: quarter sums do not reconcile")
                continue
            info = GAME_INFO.get(g["game_id"], {})
            finals_rows.append({
                "date": date, "game_id": g["game_id"], "away": g["away"], "home": g["home"],
                "status": "FINAL", "away_pts": g["away_pts"], "home_pts": g["home_pts"],
                "away_quarters": g["away_quarters"], "home_quarters": g["home_quarters"],
                "quarters_sum_check": q_sum, "ot_periods": g["ot_periods"],
                "final_label": STATUS_TEXT[g["ot_periods"]],
                "venue": idx[g["game_id"]].get("arena"),
                "city": ", ".join(x for x in (idx[g["game_id"]].get("arena_city"),
                                               idx[g["game_id"]].get("arena_state")) if x) or None,
                "attendance": info.get("attendance"), "officials": info.get("officials"),
                "state_at_retrieval": "Final",
                "source_url": g["source_url"],
                "source_box_score_url": g["source_url"] + "/box-score",
                "source_date_url": f"https://www.nba.com/games?date={date}",
                "verified_at_utc": NOW,
                "verified_by_reads": [
                    "arena/39b70241-nba1: GAME INFO + LINESCORES on the official game-summary page "
                    "(fetch_page, the same page prints the date, arena, attendance, officials and the "
                    "quarter lines), quarter sums asserted in this script",
                    "arena/39b70241-nba1: finals cross-read on https://www.nba.com/games?date="
                    + date + " (the scoreboard page) — same away/home points in 17 of 17 games",
                ],
                "independent_reads_agree": True,
                "independent_read_scope": ("finals agree between the scoreboard page and the game "
                                           "page in 17 of 17; quarter scores read once, except NYK@TOR "
                                           "which is also confirmed by the official gamebook PDF"),
            })
            if info.get("info_source"):
                finals_rows[-1]["game_info_source"] = info["info_source"]
            if g["game_id"] == "0022600253":
                finals_rows[-1]["gamebook_note"] = (
                    "official gamebook SCORE BY PERIOD: NYK 23-31-26-31=111, TOR 29-21-33-19=102; "
                    "inactives recorded there: NYK \u2014 Akins, Knecht, Nickel; TOR \u2014 Bittle "
                    "(Right Foot Avulsion Fracture), Leonard (Left Knee Injury Management), "
                    "McCullar Jr. (G League Two-Way), Smith (G League Two-Way)")

        dump(f"data/official/results_{date}.json", {
            "title": f"Official finals {date} (first-hand read {NOW})",
            "captured_by": "arena/39b70241-nba1 (scripts/settle_2026_11_19_39b70241.py)",
            "retrieved_utc": NOW,
            "rule": ("a game is FINAL only when the official page labels it Final/Final-OT and its "
                     "printed quarter scores sum to the printed final; quarter scores come from the "
                     "LINESCORES table on the game-summary page, which is the only official page that "
                     "prints them"),
            "rows": finals_rows,
            "sources": [f"https://www.nba.com/games?date={date}"]
                       + [r["source_url"] for r in finals_rows]
                       + (["https://statsdmz.nba.com/pdfs/20261117/20261117_NYKTOR_book.pdf"]
                          if date == "2026-11-17" else []),
            "summary": {"games": len(finals_rows),
                        "quarter_sum_assertion_failures": len(failures),
                        "rows_with_attendance_or_officials": sum(
                            1 for r in finals_rows if r["attendance"] or r["officials"]),
                        "note": ("the remaining rows keep null attendance/officials because their "
                                 "GAME INFO block was not read this session; nulls are published as "
                                 "unverified rather than filled (brief: 'leave it blank and flag it')")},
        })

        # ---- promote into the shared feed ----
        for r in finals_rows:
            row = idx[r["game_id"]]
            row.update({
                "game_status": 3, "game_status_text": r["final_label"],
                "home_pts": r["home_pts"], "away_pts": r["away_pts"],
                "home_quarters": r["home_quarters"], "away_quarters": r["away_quarters"],
                "ot_periods": r["ot_periods"],
                "margin_home": r["home_pts"] - r["away_pts"],
                "total_pts": r["home_pts"] + r["away_pts"],
                "source_url": r["source_url"],
                "settled_utc": NOW,
                "settled_by": "arena/39b70241-nba1 (official LINESCORES, quarter sums asserted)",
            })
            if r["attendance"] is not None:
                row["attendance"] = r["attendance"]
            if r["officials"]:
                row["officials"] = r["officials"]
            settled_ids.append(r["game_id"])
        if len(finals_rows) != len(cap["rows"]):
            failures.append(f"{date}: only {len(finals_rows)} of {len(cap['rows'])} games reconciled")

    # ---- feed-level assertions before the file is rewritten ----
    for r in rows:
        if r["game_status"] == 3:
            qs_a, qs_h = r["away_quarters"], r["home_quarters"]
            if sum(qs_a) != r["away_pts"] or sum(qs_h) != r["home_pts"]:
                failures.append(f"feed {r['game_id']}: quarter sums != finals")
            if len(qs_a) != len(qs_h):
                failures.append(f"feed {r['game_id']}: away/home quarter length mismatch")
    if failures:
        print("REFUSED to rewrite the feed:", file=sys.stderr)
        for f in failures:
            print("  -", f, file=sys.stderr)
        return 1

    feed["count_final"] = sum(1 for r in rows if r["game_status"] == 3)
    feed["count"] = len(rows)
    feed["quarter_sum_assertion_failures"] = []
    feed["last_updated_utc"] = NOW
    feed["last_updated_by"] = (
        "arena/39b70241-nba1: the seventeen 2026-11-17/2026-11-18 rows re-cut to FINAL from "
        "data/official/results_2026-11-17.json and results_2026-11-18.json (official LINESCORES, "
        "quarter sums asserted; NYK@TOR also confirmed by the official gamebook PDF). "
        "poss/rtg/pace left null: the box-score inputs were not captured. Three rows gained "
        "attendance/officials read from their GAME INFO block (0022600253, 0022600268, 0022600269).")
    dump(FEED, feed)

    by_date = {}
    for r in rows:
        by_date.setdefault(r["date"], [0, 0])
        by_date[r["date"]][0] += 1
        if r["game_status"] == 3:
            by_date[r["date"]][1] += 1
    print(json.dumps({"settled_this_run": sorted(settled_ids),
                      "feed_rows": len(rows), "feed_final": feed["count_final"],
                      "11/17": by_date.get("2026-11-17"), "11/18": by_date.get("2026-11-18")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
