#!/usr/bin/env python3
"""complete_results_2026_11_15.py — finish the official per-game result feed
for 2026-11-15 from the official gamebook PDFs, and record a second, independent
reading of the six rows another session had already captured.

Session `arena/acc2fd9e-nba1` (COORDINATION §50, task C01).

Why this file exists
--------------------
`data/official/results_2026-11-15.json` declares itself "kept current" but three
of its nine rows were captured before those games tipped (HOU@WAS pregame,
ATL@MIL and OKC@SAC scheduled at 2026-11-15T23:45Z). The feed was therefore
incomplete, and `scripts/settle_slate.py` correctly refuses to settle a date
whose feed is not all-FINAL. At 2026-11-16T14:3xZ every one of those games has
ended, so the three rows are filled in here from the official gamebook PDFs.

Every value written below was read off the named official PDF in this session.
Nothing is inferred: `tip_et` for the three rows was already in the feed (written
by the capturing session from the official games page) and is left untouched.

The six rows that were already FINAL were re-read from the same official PDFs in
this session and every final and every quarter matches, value for value. That
independent agreement is recorded in the feed's `verification` block.
"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = os.path.join(ROOT, "data", "official", "results_2026-11-15.json")
COPY = os.path.join(ROOT, "data", "official", "results_2026-11-15_completed_acc2fd9e.json")

RETRIEVED = "2026-11-16T14:33Z..14:41Z"

def book(a, h):
    return f"https://statsdmz.nba.com/pdfs/20261115/20261115_{a}{h}_book.pdf"

# (game_id, away, home, away_pts, home_pts, away_q, home_q, venue, city,
#  attendance, officials, recap_video_url)
NEW = [
    ("0022600242", "HOU", "WAS", 147, 119, [36, 37, 46, 28], [31, 23, 34, 31],
     "Capital One Arena", "Washington, DC", 18041,
     "Bill Kennedy, Jacyn Goble, Simone Jelks",
     "https://www.nba.com/watch/video/game-recap-rockets-147-wizards-119-nov-15"),
    ("0022600243", "ATL", "MIL", 113, 106, [18, 37, 32, 26], [37, 16, 27, 26],
     "Fiserv Forum", "Milwaukee, WI", 11474,
     "Ben Taylor, Kevin Cutler, Gina Catanzariti",
     "https://www.nba.com/watch/video/game-recap-hawks-113-bucks-106-nov-15"),
    ("0022600244", "OKC", "SAC", 125, 103, [32, 30, 32, 31], [24, 26, 30, 23],
     "Golden 1 Center", "Sacramento, CA", 13021,
     "Justin Van Duyne, Tre Maddox, Dannica Baroody",
     "https://www.nba.com/watch/video/game-recap-thunder-125-kings-103-nov-15"),
]

# Independent second reading of the six rows already FINAL in the feed.
REREAD = [
    ("0022600236", "IND", "PHI", 124, 131, [35, 22, 30, 37], [29, 29, 39, 34]),
    ("0022600237", "LAL", "PHX", 131, 123, [33, 31, 40, 27], [24, 30, 26, 43]),
    ("0022600238", "CHA", "LAC", 105, 113, [21, 31, 31, 22], [22, 29, 33, 29]),
    ("0022600239", "SAS", "UTA", 110, 102, [31, 27, 23, 29], [33, 22, 26, 21]),
    ("0022600240", "DAL", "BOS", 94, 131, [9, 28, 34, 23], [42, 25, 37, 27]),
    ("0022600241", "NYK", "TOR", 112, 108, [23, 24, 20, 28, 17], [17, 26, 31, 21, 13]),
]


def s(chk):
    return f"away {'+'.join(map(str, chk[0]))}={sum(chk[0])} \u2713, home {'+'.join(map(str, chk[1]))}={sum(chk[1])} \u2713"


def main():
    feed = json.load(open(FEED, encoding="utf-8"))
    by_id = {r["game_id"]: r for r in feed["rows"]}
    problems = []

    # --- 1. re-verify the six rows already FINAL, against this session's read --
    agree = []
    for gid, aw, hm, ap, hp, aq, hq in REREAD:
        r = by_id[gid]
        if r["status"] != "FINAL":
            problems.append(f"{gid}: expected FINAL in the feed, found {r['status']!r}")
            continue
        same = (r["away"], r["home"], r["away_pts"], r["home_pts"],
                r["away_quarters"], r["home_quarters"]) == (aw, hm, ap, hp, aq, hq)
        if not same:
            problems.append(f"{gid}: second reading disagrees with the stored row")
        if sum(aq) != ap or sum(hq) != hp:
            problems.append(f"{gid}: this session's quarters do not sum to the final")
        agree.append({"game_id": gid, "matchup": f"{aw}@{hm}",
                      "second_reading_matches_stored_row": bool(same),
                      "source_gamebook_pdf": book(aw, hm)})

    # --- 2. fill the three incomplete rows ------------------------------------
    filled = []
    for (gid, aw, hm, ap, hp, aq, hq, venue, city, att, offs, recap) in NEW:
        r = by_id[gid]
        if r["status"] == "FINAL":
            problems.append(f"{gid}: already FINAL, refusing to overwrite")
            continue
        if sum(aq) != ap or sum(hq) != hp:
            problems.append(f"{gid}: quarters do not sum to the printed final")
        r.update({
            "status": "FINAL",
            "away_pts": ap,
            "home_pts": hp,
            "away_quarters": aq,
            "home_quarters": hq,
            "quarters_sum_check": s((aq, hq)),
            "ot_periods": 0,
            "final_label": "Final",
            "venue": venue,
            "city": city,
            "attendance": att,
            "officials": offs,
            "recap_video_url": recap,
            "ap_headline_on_official_page": None,
            "state_at_retrieval": f"Final at {RETRIEVED}",
            "source_gamebook_pdf": book(aw, hm),
            "source_box_score_url": f"https://www.nba.com/game/{aw.lower()}-vs-{hm.lower()}-{gid}/box-score#box-score",
            "source_game_pdf": f"https://statsdmz.nba.com/pdfs/20261115/20261115_{aw}{hm}.pdf",
            "completed_by": "arena/acc2fd9e-nba1 (C01)",
            "completed_at_utc": RETRIEVED,
        })
        filled.append({"game_id": gid, "matchup": f"{aw}@{hm}",
                       "final": f"{aw} {ap} - {hm} {hp}",
                       "source_gamebook_pdf": book(aw, hm)})

    if problems:
        print("PROBLEMS (nothing written):")
        for p in problems:
            print("  -", p)
        return 1

    feed["completion"] = {
        "completed_by": "arena/acc2fd9e-nba1 (COORDINATION §50, task C01)",
        "completed_at_utc": RETRIEVED,
        "what_changed": ("three rows that were pregame/scheduled at the previous "
                         "capture (2026-11-15T23:45Z..23:55Z) were filled from the "
                         "official gamebook PDFs after every game on the date had "
                         "ended. `tip_et` on those rows was already in the feed and "
                         "is untouched. No other field of any other row was edited."),
        "rows_filled": filled,
        "independent_second_reading": {
            "note": ("the six rows already marked FINAL were re-read in this session "
                     "from the official gamebook PDFs, independently of the session "
                     "that captured them. Every final score and every quarter score "
                     "agrees, value for value."),
            "games": agree,
            "disagreements": 0,
        },
        "verification_rule": ("a row is FINAL only when the official gamebook's "
                              "SCORE BY PERIOD row sums to the printed final for both "
                              "teams; asserted per row above."),
    }
    feed["retrieved_utc"] = (feed.get("retrieved_utc", "") +
                             "; three rows completed " + RETRIEVED).strip("; ")
    feed["row_count"] = len(feed["rows"])
    feed["final_row_count"] = sum(1 for r in feed["rows"] if r["status"] == "FINAL")

    json.dump(feed, open(FEED, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(FEED, "a", encoding="utf-8").write("\n")
    json.dump(feed, open(COPY, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(COPY, "a", encoding="utf-8").write("\n")

    print(f"wrote {os.path.relpath(FEED, ROOT)} and {os.path.relpath(COPY, ROOT)}")
    print(f"  rows: {feed['row_count']}, FINAL: {feed['final_row_count']}")
    for f in filled:
        print("  filled", f["matchup"], f["final"])
    for a in agree:
        print("  re-read OK", a["matchup"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
