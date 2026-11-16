#!/usr/bin/env python3
"""Rebuild verify/2026-11-16-2823d556/drift.json from the committed captures.

    python3 verify/2026-11-16-2823d556/rebuild_drift.py

The LIVE side of this comparison is the block of records at the top of this file.
They were read from the official pages at the timestamps stated next to them and
are reproduced verbatim; this script does not re-fetch them (the official pages
move by the minute, and a re-run would silently change the finding).

The COMMITTED side is read from the repository each time, so re-running this
script after a committed capture changes will show the new comparison — and
check.py will flag that the published finding no longer reproduces.
"""

from __future__ import annotations

import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

GAMES_1115 = "https://www.nba.com/games?date=2026-11-15"
GAMES_1116 = "https://www.nba.com/games?date=2026-11-16"

# ---------------------------------------------------------------------------
# LIVE readings. Read from the official pages; recorded verbatim, never edited.
# ---------------------------------------------------------------------------

# Records as printed by the official 11/15 games page, read at 2026-11-16T02:27Z.
LIVE_RECORDS_1115 = {
    "HOU": "10-3", "WAS": "4-9", "ATL": "7-6", "MIL": "1-12", "OKC": "8-5", "SAC": "1-11",
    "IND": "5-9", "PHI": "11-3", "LAL": "12-2", "PHX": "5-7", "CHA": "4-9", "LAC": "4-8",
    "SAS": "12-2", "UTA": "1-13", "NYK": "7-6", "TOR": "5-8", "DAL": "7-7", "BOS": "11-2",
}
# Records as printed by the official 11/16 games page, read at 2026-11-16T02:20Z.
LIVE_RECORDS_1116 = {
    "ORL": "5-7", "BOS": "11-2", "CHI": "3-9", "CLE": "7-7", "MEM": "9-4", "WAS": "4-9",
    "PHI": "11-3", "BKN": "3-9", "HOU": "10-3", "MIA": "7-6", "POR": "9-3", "MIN": "9-4",
    "GSW": "8-5", "NOP": "4-10", "PHX": "5-7", "DEN": "7-4",
}
LIVE_READ_AT = {"11_15": "2026-11-16T02:27Z", "11_16": "2026-11-16T02:20Z"}

# The 2026-11-16 slate exactly as the official page printed it at 02:20Z.
LIVE_SLATE_1116 = [
    # game_id, away, home, tip_et
    ("0022600245", "ORL", "BOS", "7:00 PM ET"),
    ("0022600246", "CHI", "CLE", "7:00 PM ET"),
    ("0022600247", "MEM", "WAS", "7:00 PM ET"),
    ("0022600248", "PHI", "BKN", "7:30 PM ET"),
    ("0022600249", "HOU", "MIA", "7:30 PM ET"),
    ("0022600250", "POR", "MIN", "8:00 PM ET"),
    ("0022600251", "GSW", "NOP", "8:00 PM ET"),
    ("0022600252", "PHX", "DEN", "9:00 PM ET"),
]

# The five 2026-11-15 games that finished AFTER the committed stats snapshot was
# read, i.e. the games whose result the published 11/16 ratings do not contain.
LATE_GAMES = [
    ("0022600237", "LAL", "PHX", "Final 131-123", ["LAL"], ["PHX"]),
    ("0022600240", "DAL", "BOS", "Final 94-131", ["BOS"], ["DAL"]),
    ("0022600239", "SAS", "UTA", "Final 110-102", ["SAS"], ["UTA"]),
    ("0022600241", "NYK", "TOR", "Final/OT 112-108", ["NYK"], ["TOR"]),
    ("0022600238", "CHA", "LAC", "Final 105-113", ["LAC"], ["CHA"]),
]
STILL_LIVE = [
    ("0022600242", "HOU", "WAS", "Q4 5:24 at 2026-11-16T02:27Z"),
    ("0022600243", "ATL", "MIL", "Q3 10:42 at 2026-11-16T02:27Z"),
    ("0022600244", "OKC", "SAC", "Q1 7:59 at 2026-11-16T02:27Z"),
]


def main() -> int:
    adv = json.load(open(os.path.join(ROOT, "data/official/teams_advanced_2026-11-15_2345Z.json"),
                         encoding="utf-8"))
    adv_by = {r["abbr"]: r for r in adv["rows"]}
    gp_total = sum(r["gp"] for r in adv["rows"])

    cap = json.load(open(os.path.join(ROOT, "data/raw/official_schedule_capture_2026-11-16.json"),
                         encoding="utf-8"))
    cols = cap["cols"]
    cap_rows = [dict(zip(cols, r)) for r in cap["rows"] if r[0] == "2026-11-16"]
    cap_by = {r["game_id"]: r for r in cap_rows}

    # ---- 11/16 slate: committed capture vs live page -------------------------
    slate_cmp = []
    for (gid, away, home, tip) in LIVE_SLATE_1116:
        c = cap_by.get(gid)
        if c is None:
            slate_cmp.append({"game_id": gid, "away": away, "home": home, "tip_et": tip,
                              "in_committed_capture": False,
                              "finding": "on the live official page but NOT in the committed capture"})
            continue
        row = {
            "game_id": gid, "away": away, "home": home,
            "in_committed_capture": True,
            "matchup_agrees": c["away"] == away and c["home"] == home,
            "tip_agrees": c["tip_et"] == tip,
            "away_record_committed": c["away_record"],
            "away_record_live": LIVE_RECORDS_1116[away],
            "home_record_committed": c["home_record"],
            "home_record_live": LIVE_RECORDS_1116[home],
            "source_committed": "data/raw/official_schedule_capture_2026-11-16.json",
            "source_live": GAMES_1116,
        }
        row["records_agree"] = (row["away_record_committed"] == row["away_record_live"]
                                and row["home_record_committed"] == row["home_record_live"])
        row["fully_agrees"] = bool(row["matchup_agrees"] and row["tip_agrees"]
                                  and row["records_agree"])
        slate_cmp.append(row)

    # ---- team records: committed advanced table vs live pages ----------------
    team_cmp = []
    for abbr in sorted(set(list(LIVE_RECORDS_1115) + list(LIVE_RECORDS_1116))):
        a = adv_by.get(abbr)
        committed = f'{a["w"]}-{a["l"]}' if a else None
        srcs = []
        if abbr in LIVE_RECORDS_1115:
            srcs.append(GAMES_1115)
        if abbr in LIVE_RECORDS_1116:
            srcs.append(GAMES_1116)
        both = None
        if abbr in LIVE_RECORDS_1115 and abbr in LIVE_RECORDS_1116:
            both = LIVE_RECORDS_1115[abbr] == LIVE_RECORDS_1116[abbr]
        live = LIVE_RECORDS_1116.get(abbr) or LIVE_RECORDS_1115.get(abbr)
        team_cmp.append({
            "abbr": abbr,
            "committed_team_advanced_record": committed,
            "committed_gp": a["gp"] if a else None,
            "live_record": live,
            "live_record_from_11_15_page": LIVE_RECORDS_1115.get(abbr),
            "live_record_from_11_16_page": LIVE_RECORDS_1116.get(abbr),
            "the_two_live_pages_agree": both,
            "agrees_with_committed": committed == live,
            "delta": None if committed == live else f"{committed} -> {live}",
            "source_committed": adv["source_url"],
            "source_live": srcs,
        })

    doc = {
        "title": ("Drift between the committed official captures behind the published "
                  "11/16 horizon and the official pages read live at "
                  "2026-11-16T02:20Z-02:27Z"),
        "session": "arena/2823d556-nba1",
        "board_section": "47",
        "computed_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "live_read_at_utc": LIVE_READ_AT,
        "committed_inputs": {
            "schedule_capture": "data/raw/official_schedule_capture_2026-11-16.json",
            "schedule_captured_on_utc_date": cap["captured_on_utc_date"],
            "team_advanced": "data/official/teams_advanced_2026-11-15_2345Z.json",
            "team_advanced_retrieved_utc": adv["retrieved_utc"],
            "team_advanced_source_url": adv["source_url"],
            "team_advanced_games_counted": gp_total / 2,
            "team_advanced_games_counted_note": (
                "sum(gp) over the 30 rows / 2. The number of completed games the official "
                "table itself had ingested when the committed snapshot was taken. Measured "
                "from the committed file, not assumed."),
        },
        "published_downstream": {
            "lines": "data/derived/horizon_lines.json — 25 games, 2026-11-16..2026-11-18",
            "picks": ("data/archive/horizon_picks_2026-11-16.json — 25 singles / 24 model "
                      "picks / 9 parlays"),
            "picks_as_of": ("ratings re-cut from the official team-stat captures retrieved "
                            "2026-11-15T23:38Z..23:52Z; injury statuses from the official "
                            "2026-11-15_0615PM edition"),
        },
        "slate_11_16_row_comparison": slate_cmp,
        "slate_11_16_rows_compared": len(slate_cmp),
        "slate_11_16_rows_fully_agreeing": sum(1 for d in slate_cmp if d.get("fully_agrees")),
        "slate_11_16_rows_with_record_drift": [d["game_id"] for d in slate_cmp
                                               if d.get("records_agree") is False],
        "games_finished_after_the_committed_stats_snapshot": [
            {"game_id": g, "away": a, "home": h, "official_state_at_02_27Z": st,
             "winner": w, "loser": l,
             "source_url": GAMES_1115,
             "box_score_url": (f"https://www.nba.com/game/{a.lower()}-vs-{h.lower()}-{g}"
                               f"/box-score#box-score")}
            for (g, a, h, st, w, l) in LATE_GAMES
        ],
        "games_still_in_progress_at_02_27Z": [
            {"game_id": g, "away": a, "home": h, "official_state_at_retrieval": st,
             "source_url": GAMES_1115}
            for (g, a, h, st) in STILL_LIVE
        ],
        "team_record_comparison": team_cmp,
        "team_records_compared": len(team_cmp),
        "team_records_differing": [t["abbr"] for t in team_cmp if not t["agrees_with_committed"]],
        "team_records_differing_count": sum(1 for t in team_cmp if not t["agrees_with_committed"]),
        "the_two_live_pages_disagree_on": [t["abbr"] for t in team_cmp
                                           if t["the_two_live_pages_agree"] is False],
    }

    with open(os.path.join(HERE, "drift.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
    print("wrote drift.json")
    print("  slate rows compared :", doc["slate_11_16_rows_compared"],
          "| fully agreeing:", doc["slate_11_16_rows_fully_agreeing"])
    print("  record-drift games  :", doc["slate_11_16_rows_with_record_drift"])
    print("  team records compared:", doc["team_records_compared"],
          "| differing:", doc["team_records_differing_count"], doc["team_records_differing"])
    print("  live pages disagree on:", doc["the_two_live_pages_disagree_on"])
    print("  games counted by the committed advanced table:",
          doc["committed_inputs"]["team_advanced_games_counted"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
