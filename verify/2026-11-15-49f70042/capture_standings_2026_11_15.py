#!/usr/bin/env python3
"""capture_standings_2026_11_15.py — persist the official NBA standings page
and derive the MEASURED home-court advantage anchor from it.

Source: https://www.nba.com/standings  (read 2026-11-15T23:47Z..23:49Z)

Every row below is transcribed verbatim from the official standings table:
columns W, L, WIN%, GB, CONF, DIV, HOME, ROAD, NEUTRAL, OT, LAST10, STREAK.

The measured home-court anchor is computed from the HOME and ROAD columns:
    home_win_rate = sum(home wins) / sum(home games)
    road_win_rate = sum(road wins) / sum(road games)
    home_edge     = home_win_rate - road_win_rate
The HCA that is pinned into the model is the MARGIN-POINT equivalent of that
edge: the number of points the home team must be given so that a model with
no home advantage reproduces the measured home win rate. That conversion is
done in engine/model_core.py (hca_from_measured_home_win_rate) because it
needs the fitted outcome dispersion; this file only stores the measurement.

Run: python3 verify/2026-11-15-49f70042/capture_standings_2026_11_15.py
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OFF = os.path.join(ROOT, "data", "official")
SOURCE_URL = "https://www.nba.com/standings"
RETRIEVED = "2026-11-15T23:47Z..23:49Z"
RETRIEVAL_WINDOW = {
    "earliest_possible_utc": "2026-11-15T23:34Z",
    "latest_possible_utc": "2026-11-15T23:45:56Z",
    "basis": ("the session clock was measured at 2026-11-15T23:45:56Z and the "
              "standings page was read immediately after that measurement"),
}

# abbr, team, conf, w, l, gb, conf_record, div_record, home, road, neutral, ot, last10, streak
ROWS = [
    ("BOS", "Boston Celtics", "East", 10, 2, "--", "10-1", "4-0", "5-0", "5-2", "0-0", "1-0", "9-1", "W 5"),
    ("PHI", "Philadelphia 76ers", "East", 11, 3, "--", "11-3", "3-1", "6-2", "5-1", "0-0", "0-0", "8-2", "W 2"),
    ("DET", "Detroit Pistons", "East", 8, 4, "2", "8-3", "0-0", "3-2", "5-2", "0-0", "1-0", "6-4", "L 1"),
    ("MIA", "Miami Heat", "East", 7, 6, "3.5", "4-2", "1-1", "3-3", "4-3", "0-0", "1-0", "7-3", "W 4"),
    ("ATL", "Atlanta Hawks", "East", 7, 6, "3.5", "7-2", "4-1", "3-3", "4-3", "0-0", "0-1", "5-5", "L 2"),
    ("CLE", "Cleveland Cavaliers", "East", 7, 7, "4", "5-5", "1-0", "5-2", "2-5", "0-0", "1-0", "4-6", "W 1"),
    ("NYK", "New York Knicks", "East", 6, 6, "4", "6-6", "1-3", "4-3", "2-3", "0-0", "0-0", "6-4", "L 2"),
    ("TOR", "Toronto Raptors", "East", 5, 7, "5", "4-3", "0-2", "2-3", "3-4", "0-0", "0-0", "3-7", "L 3"),
    ("ORL", "Orlando Magic", "East", 5, 7, "5", "3-4", "0-2", "1-4", "4-3", "0-0", "0-1", "5-5", "W 3"),
    ("IND", "Indiana Pacers", "East", 5, 9, "6", "3-6", "0-1", "2-4", "3-4", "0-1", "0-0", "3-7", "L 1"),
    ("CHA", "Charlotte Hornets", "East", 4, 8, "6", "4-7", "2-2", "3-4", "1-4", "0-0", "0-0", "3-7", "L 1"),
    ("WAS", "Washington Wizards", "East", 4, 9, "6.5", "4-8", "2-3", "2-3", "2-6", "0-0", "0-1", "2-8", "L 6"),
    ("BKN", "Brooklyn Nets", "East", 3, 9, "7", "2-7", "0-2", "1-3", "2-6", "0-0", "0-1", "3-7", "L 1"),
    ("CHI", "Chicago Bulls", "East", 3, 9, "7", "2-8", "1-0", "1-4", "2-5", "0-0", "1-0", "2-8", "W 2"),
    ("MIL", "Milwaukee Bucks", "East", 1, 12, "9.5", "1-9", "1-2", "1-6", "0-6", "0-0", "0-0", "1-9", "L 9"),
    ("SAS", "San Antonio Spurs", "West", 11, 2, "--", "10-2", "2-1", "5-2", "6-0", "0-0", "1-0", "10-0", "W 11"),
    ("LAL", "Los Angeles Lakers", "West", 11, 2, "--", "6-3", "4-1", "5-1", "6-1", "0-0", "0-0", "8-2", "W 7"),
    ("HOU", "Houston Rockets", "West", 10, 3, "1", "6-3", "2-1", "7-1", "3-2", "0-0", "0-0", "7-3", "W 3"),
    ("POR", "Portland Trail Blazers", "West", 9, 3, "1.5", "9-3", "4-0", "3-2", "6-1", "0-0", "0-0", "7-3", "W 3"),
    ("MIN", "Minnesota Timberwolves", "West", 9, 4, "2", "5-2", "1-0", "5-2", "4-2", "0-0", "0-1", "6-4", "L 1"),
    ("MEM", "Memphis Grizzlies", "West", 9, 4, "2", "7-3", "1-1", "3-4", "6-0", "0-0", "0-1", "6-4", "W 2"),
    ("DEN", "Denver Nuggets", "West", 7, 4, "3", "5-4", "0-2", "2-2", "4-2", "1-0", "1-0", "7-3", "W 2"),
    ("GSW", "Golden State Warriors", "West", 8, 5, "3", "6-5", "3-2", "6-1", "2-4", "0-0", "1-0", "8-2", "L 2"),
    ("OKC", "Oklahoma City Thunder", "West", 8, 5, "3", "5-5", "1-2", "5-0", "3-5", "0-0", "0-0", "5-5", "L 3"),
    ("DAL", "Dallas Mavericks", "West", 7, 6, "4", "3-5", "1-3", "5-2", "2-4", "0-0", "0-0", "6-4", "L 2"),
    ("PHX", "Phoenix Suns", "West", 5, 6, "5", "3-6", "2-1", "5-3", "0-3", "0-0", "0-0", "5-5", "W 2"),
    ("NOP", "New Orleans Pelicans", "West", 4, 10, "7.5", "3-8", "1-1", "3-6", "1-4", "0-0", "2-1", "4-6", "L 6"),
    ("LAC", "LA Clippers", "West", 3, 8, "7", "3-6", "1-4", "3-3", "0-5", "0-0", "0-1", "2-8", "W 1"),
    ("SAC", "Sacramento Kings", "West", 1, 11, "9.5", "1-9", "0-2", "0-7", "1-4", "0-0", "0-1", "1-9", "L 5"),
    ("UTA", "Utah Jazz", "West", 1, 12, "10", "1-10", "0-2", "1-6", "0-6", "0-0", "0-2", "0-10", "L 11"),
]


def split(rec):
    w, l = rec.split("-")
    return int(w), int(l)


def main():
    rows = []
    for (ab, team, conf, w, l, gb, conf_rec, div_rec, home, road, neutral,
         ot, last10, streak) in ROWS:
        hw, hl = split(home)
        rw, rl = split(road)
        nw, nl = split(neutral)
        ow, ol = split(ot)
        lw, ll = split(last10)
        rows.append({
            "abbr": ab, "team": team, "conference": conf,
            "w": w, "l": l, "win_pct": round(w / (w + l), 3), "games_back": gb,
            "conf_record": conf_rec, "div_record": div_rec,
            "home_w": hw, "home_l": hl, "road_w": rw, "road_l": rl,
            "neutral_w": nw, "neutral_l": nl,
            "ot_w": ow, "ot_l": ol, "last10": last10, "streak": streak,
            "source_url": SOURCE_URL,
        })

    hw = sum(r["home_w"] for r in rows)
    hg = hw + sum(r["home_l"] for r in rows)
    rw = sum(r["road_w"] for r in rows)
    rg = rw + sum(r["road_l"] for r in rows)
    nw = sum(r["neutral_w"] for r in rows)
    ng = nw + sum(r["neutral_l"] for r in rows)

    # consistency self-check: home + road + neutral must equal the overall record
    for r in rows:
        assert r["home_w"] + r["road_w"] + r["neutral_w"] == r["w"], r["abbr"]
        assert r["home_l"] + r["road_l"] + r["neutral_l"] == r["l"], r["abbr"]

    home_win_rate = hw / hg
    road_win_rate = rw / rg
    neutral_win_rate = (nw / ng) if ng else None

    doc = {
        "title": "NBA.com standings, 2026-27 regular season (read 2026-11-15 evening ET)",
        "source_url": SOURCE_URL,
        "retrieved_utc": RETRIEVED,
        "retrieval_window_utc": RETRIEVAL_WINDOW,
        "captured_by": "arena/49f70042-nba1",
        "as_of_note": ("the official page reflects every game completed at read time; "
                       "games still in progress on 2026-11-15 are not counted, so these "
                       "records move as the rest of the 2026-11-15 slate finishes"),
        "measured_home_court_anchor": {
            "home_games": hg, "home_wins": hw,
            "home_win_rate": round(home_win_rate, 4),
            "road_games": rg, "road_wins": rw,
            "road_win_rate": round(road_win_rate, 4),
            "neutral_games": ng, "neutral_wins": nw,
            "neutral_win_rate": round(neutral_win_rate, 4) if neutral_win_rate else None,
            "home_edge_win_rate": round(home_win_rate - road_win_rate, 4),
            "formula": ("home_win_rate = sum(home wins) / sum(home games) over all 30 "
                        "official teams; road_win_rate likewise. The model pins its "
                        "home-court advantage to this measurement (see "
                        "engine/model_core.hca_from_measured_home_win_rate)."),
            "status": "MEASURED from the official standings page",
            "source_url": SOURCE_URL,
        },
        "rows": rows,
    }
    out = os.path.join(OFF, "standings_2026-11-15_2347Z.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote", out)
    a = doc["measured_home_court_anchor"]
    print("home %d-%d = %.4f | road %d-%d = %.4f | neutral %d-%d | edge %+.4f" % (
        a["home_wins"], a["home_games"] - a["home_wins"], a["home_win_rate"],
        a["road_wins"], a["road_games"] - a["road_wins"], a["road_win_rate"],
        a["neutral_wins"], a["neutral_games"] - a["neutral_wins"], a["home_edge_win_rate"]))


if __name__ == "__main__":
    main()
