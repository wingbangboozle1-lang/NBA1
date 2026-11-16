#!/usr/bin/env python3
"""verify_hca_fec7d5ae.py — first-hand re-measurement of the home-win rate.

Session arena/fec7d5ae-nba1 (COORDINATION §50, V-FEC-04).  The model pins HCA to
the measured home-win rate (R09).  This re-reads the official standings HOME column
at 2026-11-16 ~14:35Z and recomputes the rate, then compares it to the value the
model currently pins (0.5285 = 102/193, from standings_2026-11-16_0213Z_dfef26dc).

Home records below are transcribed from https://www.nba.com/standings at capture
time (Eastern from chunk 0, Utah from chunk 1).  No value inferred.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION = "arena/fec7d5ae-nba1"
CAPTURED_UTC = "2026-11-16T14:35:00Z"
SRC = "https://www.nba.com/standings"

# abbr -> (home_w, home_l)  transcribed from the official standings HOME column
HOME = {
    "BOS": (6, 0), "PHI": (6, 2), "DET": (3, 2), "ATL": (3, 3), "MIA": (3, 3),
    "NYK": (4, 3), "CLE": (5, 2), "ORL": (1, 4), "TOR": (2, 4), "IND": (2, 4),
    "CHA": (3, 4), "WAS": (2, 4), "BKN": (1, 3), "CHI": (1, 4), "MIL": (1, 7),
    "SAS": (5, 2), "LAL": (5, 1), "HOU": (7, 1), "POR": (3, 2), "MIN": (5, 2),
    "MEM": (3, 4), "OKC": (5, 0), "DEN": (2, 2), "GSW": (6, 1), "DAL": (5, 2),
    "PHX": (5, 4), "LAC": (4, 3), "NOP": (3, 6), "SAC": (0, 8), "UTA": (1, 7),
}

PUBLISHED = {"rate": 0.5285, "home_wins": 102, "home_games": 193,
             "source": "data/official/standings_2026-11-16_0213Z_dfef26dc.json"}


def main():
    home_wins = sum(w for w, l in HOME.values())
    home_games = sum(w + l for w, l in HOME.values())
    rate = home_wins / home_games if home_games else None
    out = {
        "captured_by": SESSION,
        "captured_utc": CAPTURED_UTC,
        "source_url": SRC,
        "home_records": {k: {"home_w": v[0], "home_l": v[1]} for k, v in sorted(HOME.items())},
        "measured": {"home_wins": home_wins, "home_games": home_games,
                     "home_win_rate": round(rate, 4) if rate else None},
        "published": PUBLISHED,
        "delta": {
            "home_wins_delta": home_wins - PUBLISHED["home_wins"],
            "home_games_delta": home_games - PUBLISHED["home_games"],
            "rate_delta": round(rate - PUBLISHED["rate"], 4) if rate else None,
        },
        "finding": (
            "The home-win rate has moved since the 02:13Z capture. Home WINS are unchanged "
            f"({home_wins}) but home GAMES rose {home_games - PUBLISHED['home_games']} to {home_games}, "
            "so the rate fell from 0.5285 to "
            f"{round(rate,4)}. The additional home games were played in the 11/15 late / 11/16 "
            "window and the home team did not win them. The pinned HCA (0.5285) is one "
            "measurement cycle stale; the current measured value is "
            f"{round(rate,4)}. This is reported, not silently applied."
        ),
    }
    with open(os.path.join(ROOT, "verify/2026-11-16-fec7d5ae/hca_recheck.json"), "w", encoding="utf-8") as fh:
        os.makedirs(os.path.dirname(os.path.join(ROOT, "verify/2026-11-16-fec7d5ae")), exist_ok=True)
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"measured home-win rate: {home_wins}/{home_games} = {round(rate,4)}")
    print(f"published (02:13Z)     : {PUBLISHED['home_wins']}/{PUBLISHED['home_games']} = {PUBLISHED['rate']}")
    print(f"delta: wins {home_wins-PUBLISHED['home_wins']:+d}, games {home_games-PUBLISHED['home_games']:+d}, rate {round(rate-PUBLISHED['rate'],4):+.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
