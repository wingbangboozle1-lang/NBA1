#!/usr/bin/env python3
"""capture_stats.py — verbatim transcription of the three official team-stat pages
(models inputs), read 2026-11-16 00:10Z..00:30Z.

Columns, in the order the page prints them:
  GP W L MIN OffRtg DefRtg NetRtg AST% AST/TO AST_Ratio OREB% DREB% REB% TOV% eFG% TS% PACE PIE POSS

Pages
  https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season  (chunks 0,1 — all 30 rows)
  https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season (chunk 0 — rows printed there)
"""
import json, os
OUT = os.path.dirname(os.path.abspath(__file__))

ADV = [
    # team, GP, W, L, MIN, OffRtg, DefRtg, NetRtg, AST%, AST/TO, AST_Ratio, OREB%, DREB%, REB%, TOV%, eFG%, TS%, PACE, PIE, POSS
    ("Los Angeles Lakers", 13, 11, 2, 624.0, 121.6, 113.6, 8.0, 58.7, 1.46, 17.6, 33.2, 64.3, 49.6, 16.8, 58.7, 63.2, 100.50, 54.2, 1306),
    ("Philadelphia 76ers", 14, 11, 3, 672.0, 112.3, 110.3, 2.0, 65.5, 2.06, 18.7, 27.5, 71.4, 49.4, 12.7, 52.6, 56.7, 100.21, 50.8, 1404),
    ("San Antonio Spurs", 13, 11, 2, 629.0, 119.6, 106.6, 13.0, 65.4, 2.28, 19.4, 33.9, 71.3, 52.7, 12.3, 53.4, 57.6, 98.94, 56.7, 1298),
    ("Boston Celtics", 12, 10, 2, 581.0, 117.4, 105.6, 11.7, 67.5, 1.83, 19.1, 32.7, 67.5, 50.4, 15.1, 54.8, 58.5, 96.62, 55.9, 1168),
    ("Houston Rockets", 13, 10, 3, 624.0, 119.3, 110.2, 9.1, 64.4, 1.85, 19.0, 35.2, 67.8, 52.0, 14.8, 55.1, 59.3, 97.42, 55.8, 1266),
    ("Memphis Grizzlies", 13, 9, 4, 629.0, 119.0, 110.4, 8.5, 66.2, 1.76, 19.1, 34.2, 70.6, 52.9, 15.6, 55.8, 60.2, 100.46, 53.9, 1318),
    ("Minnesota Timberwolves", 13, 9, 4, 629.0, 116.0, 104.5, 11.5, 59.9, 1.63, 17.8, 35.4, 69.5, 52.7, 15.6, 55.5, 57.9, 101.27, 55.2, 1326),
    ("Portland Trail Blazers", 12, 9, 3, 576.0, 118.8, 111.1, 7.7, 63.7, 1.55, 17.9, 33.3, 70.2, 52.4, 16.2, 56.3, 60.9, 100.67, 53.3, 1208),
    ("Detroit Pistons", 12, 8, 4, 586.0, 114.1, 109.2, 4.9, 67.6, 1.94, 19.2, 29.8, 66.6, 48.4, 14.1, 53.9, 58.0, 99.48, 53.7, 1217),
    ("Golden State Warriors", 13, 8, 5, 629.0, 116.1, 112.0, 4.1, 70.0, 1.75, 19.4, 32.7, 68.5, 50.7, 15.9, 55.4, 59.5, 99.66, 51.8, 1307),
    ("Oklahoma City Thunder", 13, 8, 5, 624.0, 112.7, 109.0, 3.7, 55.5, 1.72, 16.6, 31.9, 68.5, 50.8, 13.5, 51.4, 55.4, 98.58, 53.3, 1282),
    ("Atlanta Hawks", 13, 7, 6, 629.0, 113.3, 111.9, 1.4, 71.6, 2.07, 20.5, 33.2, 69.2, 49.7, 14.6, 52.8, 55.7, 103.55, 48.5, 1356),
    ("Cleveland Cavaliers", 14, 7, 7, 677.0, 116.9, 115.4, 1.6, 64.8, 2.01, 19.1, 29.1, 68.1, 49.4, 13.4, 55.8, 59.1, 99.72, 51.2, 1407),
    # DAL row continues across the chunk boundary; the values are one continuous row
    ("Dallas Mavericks", 13, 7, 6, 624.0, 112.8, 112.8, 0.0, 63.2, 1.65, 18.2, 33.0, 66.5, 49.7, 15.7, 53.5, 57.2, 100.54, 49.7, 1308),
    ("Denver Nuggets", 11, 7, 4, 533.0, 116.0, 114.7, 1.3, 66.9, 2.07, 19.7, 30.2, 67.7, 49.8, 13.5, 55.0, 59.2, 97.67, 52.9, 1087),
    ("Miami Heat", 13, 7, 6, 629.0, 114.7, 116.2, -1.5, 70.9, 2.07, 20.1, 30.3, 70.1, 49.8, 13.9, 54.5, 58.1, 102.49, 50.0, 1345),
    ("New York Knicks", 12, 6, 6, 576.0, 114.5, 108.6, 5.9, 69.2, 1.86, 18.9, 37.3, 72.1, 54.4, 15.0, 51.9, 55.7, 95.63, 53.3, 1150),
    ("Indiana Pacers", 14, 5, 9, 672.0, 110.9, 112.9, -2.0, 67.9, 1.92, 19.7, 24.6, 68.5, 47.1, 14.3, 53.8, 57.4, 101.25, 49.6, 1415),
    ("Orlando Magic", 12, 5, 7, 581.0, 109.7, 113.4, -3.7, 67.7, 1.55, 18.5, 31.7, 70.2, 50.7, 17.0, 52.8, 56.6, 98.23, 47.6, 1185),
    ("Phoenix Suns", 11, 5, 6, 528.0, 113.8, 117.6, -3.8, 65.9, 1.95, 19.5, 29.1, 61.3, 45.2, 14.2, 54.4, 57.4, 98.45, 48.1, 1080),
    ("Toronto Raptors", 12, 5, 7, 576.0, 114.5, 112.8, 1.7, 67.8, 1.96, 19.1, 36.2, 66.9, 50.2, 14.4, 51.9, 55.5, 99.88, 49.3, 1197),
    ("Charlotte Hornets", 12, 4, 8, 576.0, 101.9, 113.1, -11.2, 62.6, 1.11, 15.8, 35.7, 73.7, 53.5, 20.2, 48.1, 52.0, 96.83, 42.9, 1161),
    ("New Orleans Pelicans", 14, 4, 10, 687.0, 111.3, 120.0, -8.6, 60.6, 1.51, 17.0, 29.7, 68.0, 48.6, 15.4, 51.9, 57.7, 101.83, 45.7, 1457),
    ("Washington Wizards", 13, 4, 9, 634.0, 108.7, 114.3, -5.5, 59.3, 1.56, 17.0, 29.0, 66.2, 48.3, 15.0, 51.5, 56.0, 99.63, 47.1, 1315),
    ("Brooklyn Nets", 12, 3, 9, 581.0, 109.8, 116.0, -6.2, 65.2, 1.37, 17.2, 32.1, 69.9, 50.6, 17.6, 52.9, 57.2, 99.47, 46.1, 1204),
    ("Chicago Bulls", 12, 3, 9, 581.0, 109.4, 120.3, -10.9, 67.4, 1.55, 18.2, 30.7, 65.1, 47.9, 16.5, 51.7, 56.1, 103.81, 44.9, 1257),
    ("LA Clippers", 11, 3, 8, 533.0, 110.7, 115.8, -5.1, 68.4, 1.51, 18.8, 30.4, 67.2, 48.8, 17.6, 54.3, 58.4, 100.55, 47.4, 1116),
    ("Milwaukee Bucks", 13, 1, 12, 624.0, 105.7, 120.0, -14.2, 65.6, 1.49, 17.5, 30.5, 64.3, 47.3, 16.6, 51.1, 54.3, 100.31, 42.0, 1305),
    ("Sacramento Kings", 12, 1, 11, 576.0, 107.3, 119.5, -12.2, 63.7, 1.46, 17.9, 28.4, 69.1, 48.1, 16.9, 52.6, 56.2, 101.00, 42.8, 1210),
    ("Utah Jazz", 13, 1, 12, 634.0, 105.0, 116.4, -11.3, 63.5, 1.44, 17.0, 29.5, 68.8, 48.6, 16.3, 50.4, 54.7, 100.50, 45.3, 1330),
]
ADV_COLS = ["team", "gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to",
            "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct",
            "pace", "pie", "poss"]

# traditional page, chunk 0 only (the rows the page printed in the read chunk)
TRAD = [
    # team, GP, W, L, WIN%, MIN, PTS, FGM, FGA, FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%, OREB, DREB, REB, AST, TOV, STL, BLK, BLKA, PF, PFD, +/-
    ("Los Angeles Lakers", 13, 11, 2, ".846", 48.0, 122.2, 42.1, 83.6, 50.3, 14.1, 36.8, 38.3, 23.9, 29.8, 80.4, 11.3, 29.5, 40.8, 24.7, 16.9, 11.0, 6.2, 4.2, 23.4, 24.2, 7.9),
    ("San Antonio Spurs", 13, 11, 2, ".846", 48.4, 119.5, 42.9, 92.0, 46.7, 12.5, 35.9, 34.7, 21.2, 26.5, 79.9, 13.2, 35.4, 48.6, 28.1, 12.3, 8.3, 7.3, 4.9, 20.0, 21.2, 13.2),
    ("Boston Celtics", 12, 10, 2, ".833", 48.4, 114.3, 39.8, 87.2, 45.6, 16.0, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None),
]
TRAD_COLS = ["team", "gp", "w", "l", "win_pct", "min", "pts", "fgm", "fga", "fg_pct", "fg3m", "fg3a",
             "fg3_pct", "ftm", "fta", "ft_pct", "oreb", "dreb", "reb", "ast", "tov", "stl", "blk",
             "blka", "pf", "pfd", "plus_minus"]


def rows(records, cols, src):
    out = []
    for rec in records:
        d = {c: v for c, v in zip(cols, rec)}
        d["source_url"] = src
        out.append(d)
    return out


if __name__ == "__main__":
    # the page prints each team once; 30 distinct rows
    assert len({r[0] for r in ADV}) == 30, "advanced rows must be 30 distinct teams"
    assert all(len(r) == len(ADV_COLS) for r in ADV), "column count"
    # internal arithmetic the page itself implies
    for r in ADV:
        assert r[2] + r[3] == r[1], f"W+L must equal GP: {r[0]}"
        assert abs(r[5] - r[6] - r[7]) <= 0.15, f"OffRtg-DefRtg must equal NetRtg: {r[0]} {r[5]} {r[6]} {r[7]}"
    for r in TRAD:
        if r[6] is not None:
            assert r[2] + r[3] == r[1], f"W+L must equal GP: {r[0]}"
    doc = {
        "title": "Official team-stat captures (model inputs), read 2026-11-16 00:10Z..00:30Z",
        "retrieved_utc": "2026-11-16T00:10Z..00:30Z",
        "advanced": rows(ADV, ADV_COLS, "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"),
        "traditional_chunk0_only": rows(TRAD, TRAD_COLS, "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"),
        "rounding_note": ("The page prints NetRtg rounded independently of the printed OffRtg/DefRtg, so OffRtg-DefRtg differs from the printed NetRtg by up to 0.1 for some teams (BOS 117.4-105.6=11.8 vs printed 11.7; CLE 116.9-115.4=1.5 vs printed 1.6). Any derived check must allow that rounding; it is not a transcription error and it is not corrected here."),
        "note": ("The advanced table was read to completion (both chunks, all 30 rows). "
                 "The traditional table was read only in its first chunk in this pass, so only the "
                 "three rows printed there are recorded; every other traditional/opponent cell is "
                 "reported as NOT RE-READ IN THIS PASS, not as verified."),
    }
    json.dump(doc, open(os.path.join(OUT, "capture_stats.json"), "w"), indent=1, ensure_ascii=False)
    print("advanced rows", len(doc["advanced"]), "traditional rows", len(doc["traditional_chunk0_only"]))
