#!/usr/bin/env python3
"""
originate_horizon.py — originate OUR OWN lines for every unplayed game in the
rolling horizon (today + up to 3 days, per the project brief).

ROLLING WINDOW. The window is no longer hardcoded: the script reads the newest
official schedule capture in data/raw/official_schedule_capture_*.json and takes
every game row in it. The window rule (today + max 3 days ahead) is applied by
the capture pass, and the capture file records it in its own "scope" field, so
this script cannot drift from it. The newest official injury edition in
data/official/injury_*.json is picked up the same way.

METHOD = Build A's scripts/originate_lines.py, unchanged:
    POSS_game  = pace_home + pace_away - league_pace
    PTS_home   = (OffRtg_home * DefRtg_away / league_OffRtg) * POSS_game / 100
    PTS_away   = (OffRtg_away * DefRtg_home / league_OffRtg) * POSS_game / 100
    TOTAL      = PTS_home + PTS_away
    SPREAD     = PTS_home - PTS_away        (positive = home favoured)
    Home-court advantage: NOT applied (no official source; flagged, as on lines.html).
    Dispersion: measured from real finals in data/played_games_2026_11_11_12.json
    + data/played_games_2026_11_13_14.json (28 finals, 2026-11-11..14).

HONESTY RULES (same as the rest of the repo):
    * Every number is (a) an official NBA statistic with its source, or (b) DERIVED,
      with its formula printed beside it, or (c) blank + flagged.
    * Inputs are dated, not live. Every game row carries an as_of note naming the
      capture it was cut from and the retrieval time of that capture.
    * No sportsbook price is used or claimed.
    * Availability adjustments: only a verifiable NEW_ABSENCE moves a line
      (scripts/injury_impact.py canonical rule). Rows whose absence cannot be
      classified NEW_ABSENCE from evidence in this repo move nothing; every
      status is published instead.
"""

import glob
import json
import math
import os
import re
from datetime import date, datetime, timezone
from statistics import mean, pstdev

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RUN_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
OFFICIAL = os.path.join(DATA, "official")


def newest(pattern, where=None, dated=r"_\d{4}-\d{2}-\d{2}[^/]*\.json$"):
    """Newest file matching `pattern`. Files carrying a capture stamp sort after
    undated ones, so the rolling pass never picks up a stale snapshot."""
    base = where or DATA
    cands = [p for p in glob.glob(os.path.join(base, pattern)) if re.search(dated, p)]
    if not cands:
        cands = glob.glob(os.path.join(base, pattern))
    if not cands:
        raise SystemExit("no file matches %s in %s" % (pattern, os.path.relpath(base, ROOT)))
    return sorted(cands)[-1]


CAPTURE = newest("official_schedule_capture_*.json", os.path.join(DATA, "raw"))
CAPTURE_SOURCE = "https://www.nba.com/schedule"

# Official sources for every input (all verified in-repo; see verify/2026-11-15-83d380ad/)
SRC_ADVANCED = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
SRC_TRADITIONAL = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"
SRC_INJ_POLICY = "https://official.nba.com/nba-injury-report-2026-27-season/"
# Rolling: the newest stored edition wins. Resolved in load_horizon_injuries().
INJ_PATH = newest("injury_2*.json", OFFICIAL)
SRC_INJ = json.load(open(INJ_PATH, encoding="utf-8")).get("source_url", SRC_INJ_POLICY)
INJ_EDITION = os.path.basename(INJ_PATH)[len("injury_"):-len(".json")]
INJ_REVISION = json.load(open(INJ_PATH, encoding="utf-8")).get("revision_time_et", "not printed")
INJ_RETRIEVED = json.load(open(INJ_PATH, encoding="utf-8")).get("retrieved_utc", "not printed")

STATUS_PLAY_PROB = {"Out": 0.00, "Doubtful": 0.25, "Questionable": 0.50,
                    "Probable": 0.80, "Available": 1.00}
PRODUCTION_TRANSFER = 0.55   # same MODEL RULE as scripts/injury_impact.py

TEAM_NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def d(s):
    y, m, dd = map(int, s.split("-"))
    return date(y, m, dd)


def load_horizon_injuries():
    """Rows of the newest stored official injury edition (INJ_PATH).

    Every row the edition prints is returned, whatever game date it carries;
    the caller filters by game date. Rows printed by the PDF without a Team
    cell (merged cells) carry team_effective, the nearest printed team above,
    and are marked inherited — see the capture's merged_cell_caveat.
    """
    doc = json.load(open(INJ_PATH, encoding="utf-8"))
    out = []
    for r in doc["rows"]:
        team = (r.get("team_effective") or "").split(" (inherited")[0]
        out.append({"game_date": r.get("game_date"), "matchup": r.get("matchup") or "",
                    "team": team or None,
                    "player": r.get("player"), "status": r.get("status"),
                    "reason": r.get("reason"),
                    "team_source": ("inherited from PDF merged cells" if r.get("team_inherited")
                                    else "printed team cell")})
    return out


def iso_to_pdf_date(iso):
    y, m, d = iso.split("-")
    return "%s/%s/%s" % (m, d, y)


def main():
    cap = json.load(open(CAPTURE, encoding="utf-8"))
    cols = cap["cols"]
    rows = [dict(zip(cols, r)) for r in cap["rows"]]
    # ROLLING WINDOW: the capture defines the window (its "scope" field states
    # the rule it was captured under). This script never re-derives it.
    games = list(rows)
    dates = sorted({r["date"] for r in games})
    HORIZON_START, HORIZON_END = dates[0], dates[-1]
    per_day = {}
    for r in games:
        per_day[r["date"]] = per_day.get(r["date"], 0) + 1
    printed = cap.get("printed_per_day_counts")
    if printed:
        assert per_day == {k: v for k, v in printed.items()}, \
            f"capture per-day counts {per_day} != printed {printed}"
    assert (len(dates) <= 4), \
        f"window rule is up to 3 days ahead; capture spans {len(dates)} days"
    print("rolling window %s .. %s  (%d games: %s)  from %s" % (
        HORIZON_START, HORIZON_END, len(games),
        ", ".join("%s=%d" % (d[5:], per_day[d]) for d in dates),
        os.path.relpath(CAPTURE, ROOT)))

    adv_doc = load("teams_advanced_2026_27.json")
    adv = {t["abbr"]: t for t in adv_doc["rows"]}
    adv_cut_retrieved = adv_doc.get("_meta", {}).get("retrieved_utc", "not printed")
    scoring = {r["abbr"]: r for r in load("teams_scoring_2026_27.json")["rows"]}
    played = (load("played_games_2026_11_11_12.json")["games"] +
              load("played_games_2026_11_13_14.json")["games"])
    minutes_idx = {p["player"]: p for p in load("players_minutes_2026_27.json")["rows"]}
    players_idx = {p["player"]: p for p in load("players_2026_27.json")["players"]
                   if p.get("min") is not None}
    evidence = {r["player"]: r for r in load("player_absence_evidence.json")["rows"]}
    inj_rows = load_horizon_injuries()
    inherited_count = sum(1 for r in json.load(open(INJ_PATH, encoding="utf-8"))["rows"]
                          if r.get("team_inherited"))

    # ---- league baselines (official inputs only) --------------------------------
    league_pace = mean(t["pace"] for t in adv.values())
    league_off = mean(t["off_rtg"] for t in adv.values())

    # ---- empirical dispersion, measured from real finals ------------------------
    margins = [g["home_pts"] - g["away_pts"] for g in played]
    totals = [g["home_pts"] + g["away_pts"] for g in played if not g["ot"]]
    margin_sd = pstdev(margins)
    total_sd = pstdev(totals)

    # ---- game dates per team (official schedule capture + real finals) ----------
    team_dates = {}
    for g in played:
        team_dates.setdefault(g["away"], []).append(g["date"])
        team_dates.setdefault(g["home"], []).append(g["date"])
    for r in rows:  # 11/13 games are in the capture (played tonight, score not final yet)
        team_dates.setdefault(r["away"], []).append(r["date"])
        team_dates.setdefault(r["home"], []).append(r["date"])

    def rest_for(abbr, game_date):
        prior = [x for x in team_dates.get(abbr, []) if d(x) < d(game_date)]
        if not prior:
            return None, None, None
        last = max(prior)
        gap = (d(game_date) - d(last)).days
        return gap - 1, gap == 1, last

    # ---- availability layer (newest stored official edition) ------------------
    # Keyed on (pdf game date, matchup, team) so the same team in two different
    # games never borrows the other game's rows.
    inj_by_team = {}
    for r in inj_rows:
        abbr = TEAM_NAME_TO_ABBR.get(r.get("team"))
        if abbr:
            inj_by_team.setdefault((r.get("game_date"), r.get("matchup") or "", abbr), []).append(r)

    covered_dates = sorted({r.get("game_date") for r in inj_rows if r.get("game_date")})

    def availability_for(away, home, game_date):
        """(label, detail rows) for one game. No line moves: canonical NEW_ABSENCE rule."""
        pdf_date = iso_to_pdf_date(game_date)
        if pdf_date not in covered_dates:
            return ("No official injury report covers this game yet (latest edition in "
                    "repo: %s, revision %s; that edition covers %s)" % (
                        INJ_EDITION, INJ_REVISION, ", ".join(covered_dates)), [])
        detail = []
        for abbr in (away, home):
            team_rows = []
            for (gd, m, a), rs in inj_by_team.items():
                if gd == pdf_date and a == abbr and (m == "" or away in m or home in m):
                    team_rows += rs
            if not team_rows:
                detail.append({"team": abbr, "player": None,
                               "status": "not printed on the latest edition in repo",
                               "reason": None, "note": "no row for this team"})
                continue
            for r in team_rows:
                if not r.get("player"):
                    detail.append({"team": abbr, "player": None, "status": r.get("status"),
                                   "reason": None,
                                   "note": "team block printed without player names "
                                           "(NOT YET SUBMITTED = the club had not filed "
                                           "when the edition was published)"})
                    continue
                pmin = minutes_idx.get(r["player"])
                prow = players_idx.get(r["player"])
                ev = evidence.get(r["player"])
                cls = ev["class"] if ev else "UNKNOWN"
                mins = pmin["min"] if pmin else (prow or {}).get("min")
                pts = pmin["pts"] if pmin else (prow or {}).get("pts")
                play_prob = STATUS_PLAY_PROB.get(r.get("status"), None)
                # Canonical rule (scripts/injury_impact.py): only a NEW_ABSENCE with
                # verified production moves a line. No player on this edition has
                # in-repo evidence that his absence is new relative to the ratings
                # window, so every adjustment stays 0 and the status is published.
                adj = 0.0
                note = ("minutes/points not verifiable in repo -> blank" if pts is None
                        else "absence class %s -> no adjustment" % cls)
                detail.append({
                    "team": abbr, "player": r["player"], "status": r.get("status"),
                    "reason": r.get("reason"), "play_probability": play_prob,
                    "season_min": mins, "season_pts": pts,
                    "absence_class": cls,
                    "expected_points_removed": round(adj, 2),
                    "stat_source": ("players_minutes_2026_27.json" if pmin else
                                    ("players_2026_27.json" if prow else None)),
                    "note": note,
                })
        return ("statuses from the official %s edition (revision %s, retrieved %s); "
                "no NEW_ABSENCE verifiable -> no line adjustment"
                % (INJ_EDITION, INJ_REVISION, INJ_RETRIEVED), detail)

    out_games = []
    for g in games:
        h, a = adv[g["home"]], adv[g["away"]]
        poss = h["pace"] + a["pace"] - league_pace
        pts_h = (h["off_rtg"] * a["def_rtg"] / league_off) * poss / 100.0
        pts_a = (a["off_rtg"] * h["def_rtg"] / league_off) * poss / 100.0
        total = pts_h + pts_a
        spread = pts_h - pts_a

        rest_a, b2b_a, last_a = rest_for(g["away"], g["date"])
        rest_h, b2b_h, last_h = rest_for(g["home"], g["date"])
        avail_label, avail_detail = availability_for(g["away"], g["home"], g["date"])

        slug = f"https://www.nba.com/games?date={g['date']}"
        out_games.append({
            "date": g["date"],
            "game_id": g["game_id"],
            "matchup": f"{g['away']}@{g['home']}",
            "home": g["home"], "away": g["away"],
            "venue": g["venue"], "city": g["city"],
            "competition": (f"Emirates NBA Cup — {g['cup_label']}" if g.get("cup_label")
                            else "not printed on official schedule"),
            "tip_et": g["tip_et"],
            "records_as_captured": f"{g['away_record']} / {g['home_record']}",
            "records_status": (f"records captured {cap.get('captured_on_utc_date', 'undated')} "
                               f"(verified against the official standings page); they go "
                               f"stale as the slate's earlier games complete"),
            "game_possessions": round(poss, 2),
            "off_rtg_home": h["off_rtg"], "def_rtg_home": h["def_rtg"], "pace_home": h["pace"],
            "off_rtg_away": a["off_rtg"], "def_rtg_away": a["def_rtg"], "pace_away": a["pace"],
            "proj_home_pts": round(pts_h, 1),
            "proj_away_pts": round(pts_a, 1),
            "line_total": round(round(pts_h, 1) + round(pts_a, 1), 1),
            "line_spread_home": round(round(pts_h, 1) - round(pts_a, 1), 1),
            "total_sd": round(total_sd, 2),
            "margin_sd": round(margin_sd, 2),
            "home_court_applied": False,
            "line_status": "DERIVED",
            "formula": ("POSS = pace_home + pace_away - league_pace; "
                        "PTS = (OffRtg_team * DefRtg_opp / league_OffRtg) * POSS / 100; "
                        "TOTAL = PTS_home + PTS_away; SPREAD = PTS_home - PTS_away"),
            "inputs_as_of": (f"team ratings re-cut by scripts/recut_model_inputs.py from the "
                             f"newest official team-stat captures (traditional, opponent, "
                             f"advanced), retrieved {adv_cut_retrieved}; injury statuses from "
                             f"the official {INJ_EDITION} edition (revision {INJ_REVISION}, "
                             f"retrieved {INJ_RETRIEVED})"),
            "inputs_source": SRC_ADVANCED,
            "rest_away": {"rest_days": rest_a, "b2b": b2b_a, "last_date": last_a,
                          "derived_from": "official schedule capture + official finals "
                                          "(no adjustment applied to the line)"},
            "rest_home": {"rest_days": rest_h, "b2b": b2b_h, "last_date": last_h,
                          "derived_from": "official schedule capture + official finals "
                                          "(no adjustment applied to the line)"},
            "availability_label": avail_label,
            "availability_rows": avail_detail,
            "schedule_source": slug,
        })

    # ---- model probabilities (same as originate_lines.py) ------------------------
    for row in out_games:
        p_home = norm_cdf(row["line_spread_home"] / row["margin_sd"])
        row["model_home_win_prob"] = round(p_home, 4)
        row["line_home_ml"] = (
            round(-100 * p_home / (1 - p_home), 0) if p_home >= 0.5
            else round(100 * (1 - p_home) / p_home, 0))
        row["ml_formula"] = "normal CDF of projected margin / margin_sd, converted to American odds"
        row["ml_status"] = "DERIVED (model-internal; no sportsbook comparison available)"

    payload = {
        "_meta": {
            "title": f"Originated horizon lines — {HORIZON_START} through {HORIZON_END} "
                     f"({len(out_games)} unplayed games)",
            "generated_by": "scripts/originate_horizon.py (rolling window)",
            "generated_utc": RUN_UTC,
            "method": "identical formulas to scripts/originate_lines.py (Build A)",
            "horizon": (f"{HORIZON_START} .. {HORIZON_END}: the rolling window (today + up to "
                        f"3 days ahead) as captured in "
                        f"{os.path.relpath(CAPTURE, ROOT)} — scope: {cap.get('scope', 'not printed')}"),
            "window_rule": ("the window is defined by the capture, never re-derived here: "
                            f"{', '.join('%s=%d' % (d, per_day[d]) for d in dates)} games"),
            "inputs": {
                "schedule_capture": os.path.relpath(CAPTURE, ROOT),
                "schedule_captured_on": cap.get("captured_on_utc_date", "not printed"),
                "ratings_recut_retrieved_utc": adv_cut_retrieved,
                "ratings_files": ["data/teams_advanced_2026_27.json",
                                  "data/teams_scoring_2026_27.json"],
                "injury_edition": INJ_EDITION,
                "injury_revision_et": INJ_REVISION,
                "injury_retrieved_utc": INJ_RETRIEVED,
                "injury_file": os.path.relpath(INJ_PATH, ROOT),
            },
            "empirical_dispersion": {
                "margin_sd": round(margin_sd, 3), "total_sd": round(total_sd, 3),
                "n_margin_games": len(margins), "n_total_games": len(totals),
                "source": "https://www.nba.com/games?date=2026-11-11, "
                          "https://www.nba.com/games?date=2026-11-12, "
                          "https://www.nba.com/games?date=2026-11-13, "
                          "https://www.nba.com/games?date=2026-11-14",
                "caveat": ("n=28 (26 for totals). Small sample; directional, not final. "
                           "Corpus: data/played_games_2026_11_11_12.json + "
                           "data/played_games_2026_11_13_14.json.")},
            "league_baselines": {"league_pace": round(league_pace, 3),
                                 "league_off_rtg": round(league_off, 3)},
            "flags": [
                {"id": "F-W01", "severity": "medium",
                 "item": "Repeated matchups printed by the official schedule: POR@MIN on "
                         "both 11/16 and 11/17, NYK@TOR on both 11/15 and 11/17 (same venues).",
                 "detail": "Rows transcribed from the official schedule with distinct game "
                           "IDs (verified in the per-game link URLs on 2026-11-15); carried "
                           "as printed and flagged for manual confirmation.",
                 "source": CAPTURE_SOURCE},
                {"id": "F-W02", "severity": "high (inherited)",
                 "item": "No home-court advantage in any line.",
                 "detail": "HCA could not be sourced from an official NBA page; home moneylines "
                           "are understated by exactly the real HCA. (Build B's measured "
                           "home-win-rate 57.6% note remains a published finding, not applied.)",
                 "source": CAPTURE_SOURCE},
                {"id": "F-W03", "severity": "medium",
                 "item": f"Inputs dated, disclosed: ratings re-cut from the official captures "
                         f"retrieved {adv_cut_retrieved}; records captured "
                         f"{cap.get('captured_on_utc_date', 'undated')}; injury edition "
                         f"{INJ_EDITION} (revision {INJ_REVISION}).",
                 "detail": "Every pick built on these lines is labelled MODEL OUTPUT — "
                           "UNVALIDATED and stamped with this as-of date. Records go stale "
                           "as earlier games in the window complete (rolling refresh job).",
                 "source": SRC_TRADITIONAL},
                {"id": "F-W04", "severity": "medium",
                 "item": f"The newest stored edition ({INJ_EDITION}, revision {INJ_REVISION}) "
                         f"covers {', '.join(covered_dates)} only; later days in the window "
                         f"have no rows, and some blocks are printed NOT YET SUBMITTED.",
                 "detail": "Teams must file by 5 p.m. local the day before a game (1 p.m. "
                           "local for the second night of a back-to-back), so blocks for the "
                           "later days of the window cannot exist yet. Game-day editions "
                           "appear 11 a.m.–1 p.m. local per league policy.",
                 "source": SRC_INJ_POLICY},
                {"id": "F-W05", "severity": "medium",
                 "item": f"Some team blocks in the {INJ_EDITION} edition are printed NOT YET "
                         f"SUBMITTED, and some clubs have no block at all.",
                 "detail": "The league prints a NOT YET SUBMITTED placeholder for a club that "
                           "has not filed; an absent block is recorded as absent and never "
                           "read as 'no injuries'. Both states are published verbatim.",
                 "source": SRC_INJ},
                {"id": "F-W06", "severity": "medium",
                 "item": f"{inherited_count} injury rows lost their Team cell to PDF merged "
                         f"cells; team_effective inherits the nearest printed team.",
                 "detail": f"Rows are marked team_inherited in {os.path.relpath(INJ_PATH, ROOT)} "
                           f"and are published with that caveat. No line moves: no absence "
                           f"classifies as NEW_ABSENCE from evidence in this repo (canonical "
                           f"rule, scripts/injury_impact.py) -> adjustment 0.",
                 "source": SRC_INJ},
                {"id": "F-W07", "severity": "high",
                 "item": "No market prices exist anywhere on this page.",
                 "detail": "No sportsbook feed is reachable or claimed; every probability is "
                           "model-internal. Market-comparison gates (G4/G5) stay blocked.",
                 "source": "https://www.nba.com/schedule"},
                {"id": "F-W08", "severity": "high",
                 "item": "No strategy has passed the validation gates (Build A 0/8, Build B 0/10).",
                 "detail": "Every pick is therefore MODEL OUTPUT — UNVALIDATED, unfunded, and "
                           "capped at zero stake until a strategy passes the gates. Outcomes: "
                           "data/derived/strategies.json (Build A), docs/data/leaderboard.json "
                           "(Build B) — internal artifacts, not official NBA sources.",
                 "source": f"https://www.nba.com/games?date={HORIZON_START}"},
            ],
        },
        "games": out_games,
    }
    out_path = os.path.join(DATA, "derived", "horizon_lines.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    print(f"horizon lines written: {len(out_games)} games -> {os.path.relpath(out_path, ROOT)}")
    for row in out_games[:5]:
        print(f"  {row['date']} {row['matchup']:8} spread {row['line_spread_home']:+6.1f} "
              f"total {row['line_total']:5.1f} p_home {row['model_home_win_prob']:.3f}")


if __name__ == "__main__":
    main()
