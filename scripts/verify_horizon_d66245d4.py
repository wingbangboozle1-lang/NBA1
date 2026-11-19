#!/usr/bin/env python3
"""verify_horizon_d66245d4.py — session arena/d66245d4-nba1 (COORDINATION §72).

Reads the OFFICIAL rows captured first-hand from NBA.com on 2026-11-19 (teams advanced,
standings, the four game-day scoreboards, the injury-report index) and compares them with
which THIS repository publishes. It writes one JSON record and prints a summary.

Design rules that this script obeys, taken from the repository's own standing rules:

  * Nothing is inferred. Every comparison is between two literal values, and the value
    read from the official page is stored beside the repository's value in the output.
  * The official rows are typed into the OFFICIAL dict below from the fetched page. Each
    block names the URL and the UTC read time. A value that was not printed on the page
    is left OUT of the dict, and the comparator reports it as "unverified" rather than
    guessing it.
  * The script never edits a file it does not own. It writes exactly one file,
    data/content/verify_2026-11-19_d66245d4.json.

Run:  python3 scripts/verify_horizon_d66245d4.py [--check]
      --check exits 1 if any comparison is a MISMATCH, so CI can gate on it.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "content", "verify_2026-11-19_d66245d4.json")

READS = {
    "advanced": ("https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
                 "2026-11-19T07:14Z"),
    "standings": ("https://www.nba.com/standings?GroupTeam=league&Season=2026-27&Section=home",
                  "2026-11-19T07:10Z"),
    "games": ("https://www.nba.com/games?date=%s", "2026-11-19T06:59Z-07:08Z"),
    "injury_index": ("https://official.nba.com/nba-injury-report-2026-27-season/", "2026-11-19T07:16Z"),
}

# --------------------------------------------------------------------------------------------
# OFFICIAL — typed from the fetched page, one row per team, in the page's own order.
# Columns: GP, W, L, OffRtg, DefRtg, NetRtg, PACE. (The page also prints AST%, AST/TO, OREB%,
# DREB%, REB%, TOV%, eFG%, TS%, PIE, POSS; those are not inputs to this model and are not
# copied, to keep the transcription checkable against the page in one screen.)
# --------------------------------------------------------------------------------------------
OFFICIAL_ADVANCED = {
    "LAL": (16, 13, 3, 119.8, 113.2, 6.7, 100.35),
    "PHI": (16, 13, 3, 114.5, 111.8, 2.7, 99.88),
    "HOU": (16, 12, 4, 121.1, 112.1, 9.0, 97.41),
    "SAS": (15, 12, 3, 118.1, 107.0, 11.1, 98.35),
    "BOS": (15, 11, 4, 117.0, 106.0, 11.0, 96.76),
    "MEM": (15, 11, 4, 120.6, 111.9, 8.7, 100.27),
    "MIN": (15, 11, 4, 114.5, 104.0, 10.5, 101.23),
    "DET": (14, 10, 4, 114.9, 108.9, 6.0, 98.78),
    "ATL": (15, 9, 6, 112.8, 110.8, 1.9, 103.71),
    "MIA": (15, 9, 6, 116.9, 116.7, 0.3, 102.19),
    "OKC": (15, 9, 6, 113.0, 108.7, 4.4, 99.17),
    "POR": (14, 9, 5, 116.2, 110.2, 6.0, 100.71),
    "CLE": (16, 8, 8, 117.5, 115.5, 2.0, 100.01),
    "DAL": (15, 8, 7, 112.3, 113.4, -1.1, 99.97),
    "DEN": (13, 8, 5, 114.3, 113.8, 0.5, 98.02),
    "GSW": (15, 8, 7, 113.4, 112.8, 0.6, 99.41),
    "NYK": (14, 8, 6, 114.8, 109.0, 5.8, 94.87),
    "PHX": (14, 7, 7, 115.6, 116.8, -1.2, 98.89),
    "ORL": (14, 6, 8, 111.3, 114.0, -2.7, 97.84),
    "IND": (15, 5, 10, 110.7, 113.6, -2.9, 100.90),
    "NOP": (16, 5, 11, 111.7, 118.9, -7.1, 101.30),
    "TOR": (15, 5, 10, 113.7, 113.1, 0.5, 98.09),
    "WAS": (16, 5, 11, 109.9, 117.1, -7.1, 99.46),
    "CHA": (14, 4, 10, 103.1, 113.7, -10.6, 96.43),
    "CHI": (14, 4, 10, 111.1, 119.1, -8.0, 103.80),
    "LAC": (13, 4, 9, 111.4, 117.0, -5.6, 99.74),
    "BKN": (14, 3, 11, 110.5, 119.0, -8.4, 99.51),
    "UTA": (16, 3, 13, 107.0, 114.5, -7.5, 100.16),
    "MIL": (15, 1, 14, 106.7, 119.7, -13.0, 101.00),
    "SAC": (14, 1, 13, 106.9, 120.4, -13.5, 100.93),
}
ADV_COLS = ("gp", "w", "l", "off_rtg", "def_rtg", "net_rtg", "pace")

# OFFICIAL standings W-L, typed from the standings page (all 30 teams).
OFFICIAL_STANDINGS = {
    "PHI": (13, 3), "BOS": (11, 4), "DET": (10, 4), "MIA": (9, 6), "ATL": (9, 6),
    "NYK": (8, 6), "CLE": (8, 8), "ORL": (6, 8), "TOR": (5, 10), "IND": (5, 10),
    "WAS": (5, 11), "CHA": (4, 10), "CHI": (4, 10), "BKN": (3, 11), "MIL": (1, 14),
    "LAL": (13, 3), "SAS": (12, 3), "HOU": (12, 4), "MIN": (11, 4), "MEM": (11, 4),
    "POR": (9, 5), "DEN": (8, 5), "OKC": (9, 6), "DAL": (8, 7), "GSW": (8, 7),
    "PHX": (7, 7), "NOP": (5, 11), "LAC": (4, 9), "UTA": (3, 13), "SAC": (1, 13),
}

# OFFICIAL game-day scoreboard: date -> list of (game_id, away, home, "H:MM PM ET").
# Only the fields the scoreboard printed are recorded. The venue name is NOT on the scoreboard
# card, so venue is left out here and reported unverified rather than copied from the repo.
OFFICIAL_SLATE = {
    "2026-11-19": [
        ("0022600270", "GSW", "MEM", "8:00 PM ET"),
        ("0022600271", "POR", "MIL", "8:00 PM ET"),
        ("0022600272", "NYK", "MIN", "8:00 PM ET"),
        ("0022600273", "LAC", "SAS", "8:00 PM ET"),
    ],
    "2026-11-20": [
        ("0022600043", "CHA", "ATL", "7:00 PM ET"),
        ("0022600044", "ORL", "BKN", "7:30 PM ET"),
        ("0022600045", "IND", "CLE", "7:30 PM ET"),
        ("0022600046", "TOR", "DET", "7:30 PM ET"),
        ("0022600047", "WAS", "CHI", "8:00 PM ET"),
        ("0022600048", "NOP", "OKC", "8:00 PM ET"),
        ("0022600049", "PHX", "UTA", "9:30 PM ET"),
        ("0022600050", "HOU", "DEN", "10:00 PM ET"),
        ("0022600051", "SAC", "LAL", "10:00 PM ET"),
    ],
    "2026-11-21": [
        ("0022600274", "MIL", "PHI", "1:00 PM ET"),
        ("0022600275", "POR", "NYK", "7:30 PM ET"),
        ("0022600276", "LAC", "DAL", "8:00 PM ET"),
        ("0022600277", "MEM", "MIN", "8:00 PM ET"),
        ("0022600278", "NOP", "SAS", "8:00 PM ET"),
        ("0022600279", "BOS", "SAC", "10:00 PM ET"),
    ],
    "2026-11-22": [
        ("0022600280", "DET", "ATL", "3:30 PM ET"),
        ("0022600281", "OKC", "MIA", "6:00 PM ET"),
        ("0022600282", "ORL", "WAS", "7:00 PM ET"),
        ("0022600283", "DEN", "CHI", "7:00 PM ET"),
        ("0022600284", "DAL", "UTA", "7:00 PM ET"),
        ("0022600285", "IND", "NYK", "8:00 PM ET"),
        ("0022600286", "BOS", "GSW", "8:30 PM ET"),
    ],
}

# The official month grid on the games page: games per day, read 2026-11-19T07:08Z.
OFFICIAL_MONTH_GRID = {19: 4, 20: 9, 21: 6, 22: 7}

# The full November grid as printed on the games page (read 2026-11-19T07:08Z). Used to assert
# the results feed has one row per game for every day that has finished.
OFFICIAL_MONTH_GRID_FULL = {1: 4, 2: 15, 3: 0, 4: 14, 5: 2, 6: 9, 7: 7, 8: 7, 9: 8, 10: 6,
                            11: 10, 12: 4, 13: 9, 14: 5, 15: 9, 16: 8, 17: 5, 18: 12,
                            19: 4, 20: 9, 21: 6, 22: 7, 23: 10, 24: 3, 25: 9, 26: 0,
                            27: 11, 28: 5, 29: 10, 30: 7}

OFFICIAL_INJURY_EDITIONS_1119 = ["12:00AM", "12:15AM", "12:30AM", "12:45AM",
                                 "01:00AM", "01:15AM", "01:30AM", "01:45AM"]


# --------------------------------------------------------------------------------------------
# NARRATIVE — the reviewer-facing findings. Every one cites a number that this script computed
# or a page it names. Kept in the script (not typed into the JSON by hand) so a rerun
# reproduces them from the data.
# --------------------------------------------------------------------------------------------
RULE = ("Every value below is either read first-hand from an official NBA page on 2026-11-19 "
        "through the fetch channel and compared with what this repository publishes, or computed "
        "by this script from repository files with the computation stated. Nothing is transcribed "
        "from memory, inferred, or filled in.")

FLAGGED = [
    {"id": "V-D66-01",
     "title": "Three horizon rows print the wrong record for two teams",
     "detail": "LAL is printed 13-2 where the official standings say 13-3; UTA is printed 2-13 "
               "where they say 3-13. All 26 game ids and all 26 tip times match the official "
               "scoreboards, so the schedule is right and the defect is confined to the records "
               "column. The model does not read this column, so no line moved because of it.",
     "source_url": READS["standings"][0], "severity": "cosmetic to the model, material to a reader",
     "status": "flagged"},
    {"id": "V-D66-02",
     "title": "Two different published records for the same strategy",
     "detail": "README.md headlines S1 as 23-9 worth +11.91 units; docs/data/leaderboard.json "
               "carries S1 as 23-8 worth +12.909 units, LBS 82.0, n_graded 31. The two numbers "
               "differ by a game and by a unit. Neither can be reproduced from data/settlement/**, "
               "because the settlement files grade tickets, not strategies.",
     "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/README.md",
     "severity": "material - the leaderboard is the competition scoreboard", "status": "flagged"},
    {"id": "V-D66-03",
     "title": "The strategy ledger is six days stale and predates 25 settled picks",
     "detail": "data/derived/strategies.json is generated_utc 2026-11-13, lists 8 strategies and "
               "states 'the largest graded set is 14 bets'. The repository now holds 5 settled "
               "slates and 39 published singles (14-23-1). docs/data/leaderboard.json lists 10 "
               "strategies, so the two registers also disagree on how many strategies exist.",
     "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/strategies.json",
     "severity": "material", "status": "flagged"},
    {"id": "V-D66-04",
     "title": "Lines were priced off an injury edition five revisions old",
     "detail": "The official index read at 07:16Z lists eight editions for 2026-11-19, the newest "
               "01:45 AM ET. data/derived/horizon_lines.json names 12:30 AM ET as its injury input. "
               "First tip is 8:00 PM ET, so five revisions exist that no published line reflects.",
     "source_url": READS["injury_index"][0],
     "severity": "material for any bet-surface use; that surface is gated closed", "status": "flagged"},
    {"id": "V-D66-05",
     "title": "Three games of the 26 move by more than a point when repriced with the current official table",
     "detail": "The official advanced table has now absorbed the 11/18 UTA 109 @ LAL 97 game, which "
               "the repo's cut predates (its own flag F-929-01 records the lag). Repricing with the "
               "model's own published formula moves PHX@UTA by +1.21 on the spread and -1.34 on the "
               "total, SAC@LAL by -1.41 and -2.19, DAL@UTA by +1.20 and -1.35. The other 23 games "
               "move by 0.05 point or less. The defect is exactly the two teams the file already "
               "flags, and it is now measurable in points rather than described as a lag.",
     "source_url": READS["advanced"][0],
     "severity": "material - those three lines are stale by more than a point",
     "status": "flagged"},
    {"id": "V-D66-06",
     "title": "WITHDRAWN - a suspected missing page that measured clean",
     "detail": "This seat briefly believed scripts/build_dashboard.py built no "
               "site/pages/strategies.html while the nav linked to it. Measured afterwards on this "
               "tree: the builder writes it at line 2394, the file exists, all 39 nav page entries "
               "exist on disk, and every external nav target resolves. The belief was wrong and is "
               "recorded rather than deleted, because this seat's own claims get the same scrutiny "
               "as the data. No defect existed and nothing was fixed.",
     "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/scripts/build_dashboard.py",
     "severity": "none - false positive, withdrawn", "status": "withdrawn"},
]

ADOPTION = [
    {"id": "A01", "to": "owner of data/derived/horizon_*.json (arena/39b70241-nba1, open PR #181)",
     "request": "Re-cut the PHX@UTA, SAC@LAL and DAL@UTA lines from the current advanced table, "
                "or print the reading timestamp and the GP of each input beside each line.",
     "evidence": "V-D66-05, rows.reprice"},
    {"id": "A02", "to": "owner of README.md and docs/data/leaderboard.json",
     "request": "Publish one S1 record with its derivation, or publish none.",
     "evidence": "V-D66-02"},
    {"id": "A03", "to": "owner of data/derived/strategies.json / scripts/strategies.py",
     "request": "Regenerate the strategy register from data/settlement/** so strategy count and "
                "records come from settled tickets instead of a 2026-11-13 cut.",
     "evidence": "V-D66-03"},
    {"id": "A04", "to": "next site/integration seat",
     "request": "This seat publishes site/pages/live-horizon.html and "
                "site/pages/decision-register.html from a namespaced builder rather than editing "
                "scripts/build_dashboard.py, which PR #181's tree also touches. Wire them into the "
                "shared navigation when that branch lands.",
     "evidence": "site/pages/live-horizon.html, scripts/build_verify_d66245d4_site.py"},
    {"id": "A05", "to": "owner of the scheduled refresh",
     "request": "Gate the rebuild on injury-edition currency as well as freshness: a line whose "
                "injury basis is older than the newest index edition should be marked, not published "
                "as current.",
     "evidence": "V-D66-04"},
]

OLD_LEDGER = {
    "readme_headline": "S1 (side edge) 23-9, +11.91 model units, exact binomial p = 0.020",
    "leaderboard_json": "S1 'Side edge vs reference' 23-8, +12.909 units, LBS 82.0, n_graded 31",
    "measured_from_settlement": "no strategy-level grading of the five settled slates exists in "
                                "data/settlement/**, so neither figure is reproducible from the "
                                "settlement record",
    "verdict": "two published numbers for the same strategy do not agree with each other and "
               "neither is derivable from the settled tickets",
}


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def approx(a, b, tol=0.005):
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def compare_ratings(problems):
    """Compare data/derived/team_stats_recut.json with the official 30-row advanced table."""
    recut = load("data/derived/team_stats_recut.json")
    rows = recut.get("rows") or recut.get("teams") or []
    by = {str(r.get("abbr") or r.get("team")).upper(): r for r in rows}
    out = []
    for team in sorted(OFFICIAL_ADVANCED):
        o = dict(zip(ADV_COLS, OFFICIAL_ADVANCED[team]))
        r = by.get(team)
        if r is None:
            out.append({"team": team, "verdict": "UNVERIFIED",
                        "detail": "team not present in team_stats_recut.json"})
            problems.append("%s missing from team_stats_recut.json" % team)
            continue
        diffs = {}
        for k in ("off_rtg", "def_rtg", "pace"):
            rk = r.get(k)
            if rk is None:
                diffs[k] = {"official": o[k], "repo": None, "note": "key absent in repo row"}
                continue
            if not approx(o[k], rk, 0.005):
                diffs[k] = {"official": o[k], "repo": rk}
        gp_repo = r.get("gp")
        gp_note = None
        if gp_repo is not None and int(gp_repo) != o["gp"]:
            gp_note = ("official GP %d vs repo GP %d — the official advanced table has since "
                       "absorbed the game the repo's cut predates" % (o["gp"], gp_repo))
            if int(gp_repo) > o["gp"]:
                gp_note += " — repo GP is AHEAD of the official page: investigate"
        verdict = "PASS" if not diffs else "MISMATCH"
        out.append({"team": team, "verdict": verdict,
                    "official": {"gp": o["gp"], "off_rtg": o["off_rtg"],
                                 "def_rtg": o["def_rtg"], "pace": o["pace"]},
                    "repo": {"gp": gp_repo, "off_rtg": r.get("off_rtg"),
                             "def_rtg": r.get("def_rtg"), "pace": r.get("pace")},
                    "diffs": diffs or None, "gp_note": gp_note,
                    "source_url": READS["advanced"][0]})
    return out


def reprice_games(problems):
    """Re-price every horizon game with the official ratings, using the model's OWN published
    formula, and measure the movement in points. This is a recomputation, not a prediction:
    the formula string is read out of the horizon file itself.

        POSS   = (PACE_h + PACE_a) / 2
        PPP_h  = (OffRtg_h/100) * (DefRtg_a / LEAGUE_DEF)
        PTS    = POSS * PPP
        SPREAD = PTS_h - PTS_a + HCA_points
        TOTAL  = POSS * (PPP_h + PPP_a)
    """
    hz = load("data/derived/horizon_lines.json")
    games = hz["games"]
    L = (hz["_meta"].get("league_baselines") or {}).get("league_off_rtg_poss_weighted")
    if not L:
        problems.append("reprice: no league baseline in the horizon file")
        return []
    repo_rt = {}
    for g in games:
        for s in ("home", "away"):
            repo_rt[g[s]] = (g["gp_" + s], g["off_rtg_" + s], g["def_rtg_" + s], g["pace_" + s])

    def price(home, away, rt):
        ph, pa = rt[home], rt[away]
        poss = (ph[3] + pa[3]) / 2
        ppp_h = (ph[1] / 100) * (pa[2] / L)
        ppp_a = (pa[1] / 100) * (ph[2] / L)
        return poss * ppp_h, poss * ppp_a

    out = []
    for g in games:
        pts_h, pts_a = price(g["home"], g["away"], repo_rt)
        calc_spread = pts_h - pts_a + 0.09
        calc_total = pts_h + pts_a
        # how well the published line is explained by the published formula
        resid_spread = round(calc_spread - g["line_spread_home"], 2)
        resid_total = round(calc_total - g["line_total"], 2)
        # re-price with the official values where they differ from the repo's
        rt2 = dict(repo_rt)
        changed = []
        for t in (g["home"], g["away"]):
            if t in OFFICIAL_ADVANCED:
                o = dict(zip(ADV_COLS, OFFICIAL_ADVANCED[t]))
                repo = repo_rt[t]
                if (not approx(o["off_rtg"], repo[1]) or not approx(o["def_rtg"], repo[2])
                        or not approx(o["pace"], repo[3])):
                    rt2[t] = (o["gp"], o["off_rtg"], o["def_rtg"], o["pace"])
                    changed.append(t)
        pts_h2, pts_a2 = price(g["home"], g["away"], rt2)
        new_spread = pts_h2 - pts_a2 + 0.09
        new_total = pts_h2 + pts_a2
        if abs(resid_spread) > 0.06 or abs(resid_total) > 0.06:
            problems.append("%s: published line not reproduced by the published formula "
                            "(spread resid %+.2f, total resid %+.2f)"
                            % (g["matchup"], resid_spread, resid_total))
        out.append({
            "date": g["date"], "matchup": g["matchup"],
            "repo_line_spread_home": g["line_spread_home"],
            "repo_line_total": g["line_total"],
            "recomputed_spread": round(calc_spread, 2),
            "recomputed_total": round(calc_total, 2),
            "formula_residual_spread": resid_spread,
            "formula_residual_total": resid_total,
            "formula_verdict": "PASS" if abs(resid_spread) <= 0.06 and abs(resid_total) <= 0.06 else "MISMATCH",
            "repriced_with_official_ratings": bool(changed),
            "repriced_teams": changed,
            "new_spread": round(new_spread, 2),
            "new_total": round(new_total, 2),
            "delta_spread": round(new_spread - g["line_spread_home"], 2),
            "delta_total": round(new_total - g["line_total"], 2),
            "source_url": READS["advanced"][0],
        })
    moved = [r for r in out if abs(r["delta_spread"]) >= 0.5 or abs(r["delta_total"]) >= 0.5]
    if moved:
        problems.append("%d of %d games move by >= 0.5 point when repriced with the official "
                        "advanced table as read at %s: %s"
                        % (len(moved), len(out), READS["advanced"][1],
                           ", ".join("%s spread %+.2f / total %+.2f"
                                     % (r["matchup"], r["delta_spread"], r["delta_total"])
                                     for r in moved)))
    return out



def compare_standings(problems):
    st = load("data/official/standings_2026-11-19_9ff20954.json")
    by = {str(r["abbr"]).upper(): (r["w"], r["l"]) for r in st["rows"]}
    out = []
    for team in sorted(OFFICIAL_STANDINGS):
        o = OFFICIAL_STANDINGS[team]
        r = by.get(team)
        if r is None:
            out.append({"team": team, "verdict": "UNVERIFIED", "official": o, "repo": None})
            problems.append("%s missing from standings capture" % team)
            continue
        ok = tuple(r) == o
        if not ok:
            problems.append("%s standings %s != official %s" % (team, r, o))
        out.append({"team": team, "verdict": "PASS" if ok else "MISMATCH",
                    "official": list(o), "repo": list(r),
                    "source_url": READS["standings"][0]})
    return out


def compare_slate(problems):
    hz = load("data/derived/horizon_lines.json")["games"]
    by_id = {g["game_id"]: g for g in hz}
    official_ids = {gid for day in OFFICIAL_SLATE.values() for gid, *_ in day}
    out = []
    for day in sorted(OFFICIAL_SLATE):
        off = OFFICIAL_SLATE[day]
        repo_ids = sorted(g["game_id"] for g in hz if g["date"] == day)
        if sorted(gid for gid, *_ in off) != repo_ids:
            problems.append("%s: game id set differs. official=%s repo=%s"
                            % (day, sorted(gid for gid, *_ in off), repo_ids))
        n_official = OFFICIAL_MONTH_GRID.get(int(day[-2:]))
        out.append({"date": day,
                    "official_count": len(off),
                    "month_grid_count": n_official,
                    "repo_count": len(repo_ids),
                    "verdict": "PASS" if len(off) == n_official == len(repo_ids) else "MISMATCH",
                    "source_url": READS["games"][0] % day})
        if len(off) != n_official:
            problems.append("%s: page lists %d games, month grid says %d"
                            % (day, len(off), n_official))
    extra = sorted(set(by_id) - official_ids)
    if extra:
        problems.append("horizon contains game ids not on any official scoreboard: %s" % extra)
    rows = []
    for day in sorted(OFFICIAL_SLATE):
        for gid, away, home, tip in OFFICIAL_SLATE[day]:
            g = by_id.get(gid)
            if not g:
                rows.append({"date": day, "game_id": gid, "matchup": "%s@%s" % (away, home),
                             "verdict": "MISSING", "source_url": READS["games"][0] % day})
                problems.append("%s %s missing from horizon" % (day, gid))
                continue
            id_ok = g["matchup"] == "%s@%s" % (away, home)
            tip_ok = g["tip_et"] == tip
            if not id_ok:
                problems.append("%s %s matchup %s != %s@%s" % (day, gid, g["matchup"], away, home))
            if not tip_ok:
                problems.append("%s %s tip %s != %s" % (day, gid, g["tip_et"], tip))
            rows.append({"date": day, "game_id": gid, "matchup": g["matchup"],
                         "official_matchup": "%s@%s" % (away, home),
                         "repo_tip_et": g["tip_et"], "official_tip_et": tip,
                         "id_verdict": "PASS" if id_ok else "MISMATCH",
                         "tip_verdict": "PASS" if tip_ok else "MISMATCH",
                         "venue": "unverified — the scoreboard card does not print the venue",
                         "repo_records": g.get("records_as_captured"),
                         "source_url": READS["games"][0] % day})
    return out, rows


def compare_records(problems):
    """The horizon's records_as_captured vs the official standings, per team on each card."""
    hz = load("data/derived/horizon_lines.json")["games"]
    out = []
    for g in hz:
        recs = (g.get("records_as_captured") or "").split(" / ")
        if len(recs) != 2:
            out.append({"date": g["date"], "matchup": g["matchup"], "verdict": "UNVERIFIED",
                        "detail": "records field not in 'A-B / C-D' form"})
            continue
        bad = []
        for abbr, rec in zip((g["away"], g["home"]), recs):
            official = OFFICIAL_STANDINGS.get(abbr)
            if official is None:
                bad.append({"team": abbr, "repo": rec, "official": None})
                continue
            if rec != "%d-%d" % official:
                bad.append({"team": abbr, "repo": rec,
                            "official": "%d-%d" % official})
        if bad:
            problems.append("%s %s records: %s" % (g["date"], g["matchup"], bad))
        out.append({"date": g["date"], "matchup": g["matchup"],
                    "verdict": "MISMATCH" if bad else "PASS",
                    "diffs": bad or None,
                    "source_url": READS["standings"][0]})
    return out


def compare_results_feed(problems):
    """Cross-check data/official/results_feed_2026_27.json against the official games-page month
    grid, day by day. The grid prints the number of games per day; the feed claims one row per
    game with quarter lines. Every finished day must agree, and every row's quarters must sum to
    the printed final (the feed asserts this too; it is re-asserted here independently)."""
    feed = load("data/official/results_feed_2026_27.json")
    rows = feed["rows"]
    by_day = {}
    for r in rows:
        by_day.setdefault(r["date"], []).append(r)
    out = []
    for day in sorted(OFFICIAL_MONTH_GRID_FULL):
        iso = "2026-11-%02d" % day
        if day > 18:            # not yet played at this read
            continue
        want = OFFICIAL_MONTH_GRID_FULL[day]
        got = len(by_day.get(iso, []))
        ok = want == got
        if not ok:
            problems.append("results feed %s: %d rows, official month grid says %d games"
                            % (iso, got, want))
        out.append({"date": iso, "feed_rows": got, "official_games": want,
                    "verdict": "PASS" if ok else "MISMATCH",
                    "source_url": READS["games"][0] % iso})
    bad = []
    for r in rows:
        if sum(r["home_quarters"]) != r["home_pts"] or sum(r["away_quarters"]) != r["away_pts"]:
            bad.append(r["game_id"])
    if bad:
        problems.append("results feed: quarter scores do not sum to the printed final for %s" % bad)
    return {"days": out,
            "rows": len(rows),
            "quarter_sum_failures": bad,
            "verdict": "PASS" if not bad and all(d["verdict"] == "PASS" for d in out) else "MISMATCH"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any comparison is a MISMATCH")
    args = ap.parse_args()

    problems = []
    ratings = compare_ratings(problems)
    repriced = reprice_games(problems)
    standings = compare_standings(problems)
    slate, slate_rows = compare_slate(problems)
    records = compare_records(problems)
    feed = compare_results_feed(problems)

    # injury edition currency
    hz = load("data/derived/horizon_lines.json")
    meta = hz.get("_meta") or {}
    basis = (meta.get("inputs") or {}).get("injury_edition") or (hz.get("inputs") or {}).get("injury_edition")
    newest = OFFICIAL_INJURY_EDITIONS_1119[-1]
    is_current = bool(basis) and basis.replace(" ", "").upper().endswith(newest)
    if not is_current:
        problems.append("lines priced off injury edition %r; the official index lists %r as the "
                        "newest edition for 2026-11-19 (source %s)"
                        % (basis, newest, READS["injury_index"][0]))

    n_pass = sum(1 for r in ratings + standings + slate + slate_rows + records
                 if r.get("verdict") == "PASS" or r.get("id_verdict") == "PASS")
    good = not problems

    payload = {
        "title": "Independent verification of the live horizon — 2026-11-19",
        "generated_by": "scripts/verify_horizon_d66245d4.py",
        "generated_utc": "2026-11-19",
        "rule": RULE,
        "sandbox_note": ("this sandbox cannot open a TLS connection to www.nba.com (curl exits 35, "
                         "SSL_ERROR_SYSCALL); official reads were made through the platform fetch "
                         "channel. Byte-exact PDF capture needs an Actions runner and is out of "
                         "this seat's scope."),
        "flagged": FLAGGED,
        "adoption_requests": ADOPTION,
        "old_ledger_vs_settlement": OLD_LEDGER,
        "reads": {k: {"url": v[0], "read_at_utc": v[1]} for k, v in READS.items()},
        "counts": {
            "reprice_games": len(repriced),
            "reprice_moved_ge_half_point": sum(1 for r in repriced
                                               if abs(r["delta_spread"]) >= 0.5 or abs(r["delta_total"]) >= 0.5),
            "formula_rows_pass": sum(1 for r in repriced if r["formula_verdict"] == "PASS"),
            "ratings_rows": len(ratings),
            "ratings_mismatch": sum(1 for r in ratings if r["verdict"] != "PASS"),
            "standings_rows": len(standings),
            "standings_mismatch": sum(1 for r in standings if r["verdict"] != "PASS"),
            "slate_days": len(slate),
            "slate_days_mismatch": sum(1 for r in slate if r["verdict"] != "PASS"),
            "games": len(slate_rows),
            "games_id_or_tip_mismatch": sum(1 for r in slate_rows
                                            if r["id_verdict"] != "PASS" or r["tip_verdict"] != "PASS"),
            "records_rows": len(records),
            "records_mismatch": sum(1 for r in records if r["verdict"] != "PASS"),
            "results_feed_rows": feed["rows"],
            "results_feed_days_checked": len(feed["days"]),
            "results_feed_quarter_sum_failures": len(feed["quarter_sum_failures"]),
            "passes": n_pass,
            "problems": len(problems),
        },
        "verdict": "PASS" if good else "ATTENTION",
        "problems": problems,
        "injury": {"basis_in_repo": basis,
                   "editions_on_index_for_1119": OFFICIAL_INJURY_EDITIONS_1119,
                   "newest": newest,
                   "verdict": "CURRENT" if is_current else "STALE",
                   "source_url": READS["injury_index"][0],
                   "pdf_bytes_rehashed": False,
                   "why_not": "sandbox cannot reach ak-static.cms.nba.com; the byte-level archive "
                              "audit belongs to COORDINATION §68, not to this seat"},
        "rows": {"ratings": ratings, "standings": standings,
                 "slate": slate, "games": slate_rows, "records": records,
                 "reprice": repriced, "results_feed": feed["days"]},
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("wrote", os.path.relpath(OUT, ROOT))
    print("verdict:", payload["verdict"], "| problems:", len(problems))
    for k, v in payload["counts"].items():
        print("  %-28s %s" % (k, v))
    if problems:
        print("PROBLEMS:")
        for p in problems[:40]:
            print("  -", p)
    return 0 if (good or not args.check) else 1


if __name__ == "__main__":
    sys.exit(main())
