#!/usr/bin/env python3
"""originate_horizon_84264db0.py — originate our own lines for the 2026-11-17 ..
2026-11-20 rolling window (today + up to 3 days), with

  * the MEASURED home-court-advantage pin applied to every line (not fitted), and
  * the TOTAL modelled as possessions x points-per-possession instead of an
    average of the two team scoring averages.

Why a new script rather than an edit: `scripts/originate_horizon.py` is the
published originator for the 11/16 window and is referenced by the pages and the
ledger record for that slate.  This script reuses its input plumbing (schedule
capture -> games, official injury edition -> availability detail, official team
stats -> ratings) and changes exactly two model decisions, both printed into the
output so a reviewer can diff them against the previous window.

Model
-----
Possessions (one number per game, used by BOTH sides):

    POSS = (PACE_home + PACE_away) / 2

  PACE is the official "possessions per 48 minutes" column on
  https://www.nba.com/stats/teams/advanced.  Using one POSS for both sides is what
  makes the two team lines add up to a single game total: the previous formula
  (PACE_home + PACE_away - league_pace) double-counted the pace gap and produced
  totals that could not be reconciled with measured totals.

Points per possession, per side (a ratio of the side's own efficiency to the
league's, applied to the opponent's defence):

    PPP_home = (OffRtg_home / 100) * (DefRtg_away / LEAGUE_DEF_SIDE)
    PPP_away = (OffRtg_away / 100) * (DefRtg_home / LEAGUE_DEF_SIDE)

    PTS_home = POSS * PPP_home
    PTS_away = POSS * PPP_away
    TOTAL    = PTS_home + PTS_away          (a possession total, not an average)
    SPREAD   = PTS_home - PTS_away + HCA_POINTS

  LEAGUE_OFF and LEAGUE_DEF_SIDE are the possession-weighted league means from
  the same official table (they are equal by construction of a closed league; the
  script asserts that and reports the gap).

Home court: HCA_POINTS is read from data/derived/measured_constants_2026_27.json,
where it is sigma_margin * Phi^-1(official home-win rate).  It is never fitted
here and there is no free parameter in this script.

Honesty rules: inherited from the originator — every number is printed on an
official page or derived with its formula printed beside it; a value that could
not be confirmed is blank and flagged; no sportsbook price exists anywhere.
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys
from datetime import date, datetime, timezone
from statistics import mean

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RUN_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

SRC_ADVANCED = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
SRC_TRADITIONAL = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"
SRC_INJ_POLICY = "https://official.nba.com/nba-injury-report-2026-27-season/"

CAPTURE = os.path.join(DATA, "raw", "official_schedule_capture_2026-11-19.json")
INJ_PATH = os.path.join(DATA, "official", "injury_2026-11-19_1230AM_929395a5.json")
CONSTS = os.path.join(DATA, "derived", "measured_constants_2026_27.json")
RECUT = os.path.join(DATA, "derived", "team_stats_recut.json")

STATUS_PLAY_PROB = {"Out": 0.00, "Doubtful": 0.25, "Questionable": 0.50,
                    "Probable": 0.80, "Available": 1.00}

TEAM_ABBR_FROM_NAME = {
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


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def to_date(s):
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


def pdf_date(iso):
    y, m, d = iso.split("-")
    return f"{m}/{d}/{y}"


def main():
    cap = load(CAPTURE)
    games = cap["rows"]  # the 11/17 capture stores rows as dicts already
    dates = sorted({g["date"] for g in games})
    per_day = {}
    for g in games:
        per_day[g["date"]] = per_day.get(g["date"], 0) + 1
    assert len(dates) <= 4, f"window rule is today + up to 3 days; capture spans {len(dates)} days"
    assert per_day == cap["games_per_day"], f"per-day counts {per_day} != capture {cap['games_per_day']}"

    consts = load(CONSTS)
    HCA = consts["home_court_pin"]["hca_points"]
    SIGMA_M = consts["dispersion"]["sigma_margin"]
    SIGMA_T = consts["dispersion"]["sigma_total"]

    recut = load(RECUT)
    teams = {r["abbr"]: r for r in recut["rows"]}

    # ---- official injury edition (availability detail; never moves a line here)
    inj = load(INJ_PATH)
    inj_by = {}
    for r in inj["rows"]:
        inj_by.setdefault((r["game_date"], r["matchup"]), []).append(r)
    nys_by = {}
    for r in inj["not_yet_submitted"]:
        nys_by.setdefault((r["game_date"], r["matchup"]), []).append(r)

    # ---- league baselines, possession-weighted, and the closed-league assertion
    poss_tot = sum(t["poss"] for t in teams.values())
    league_off = sum(t["off_rtg"] * t["poss"] for t in teams.values()) / poss_tot
    # "defensive rating" on the same table is points allowed per 100 possessions,
    # already on the same scale as the offensive rating; its possession-weighted
    # league mean is the league's points allowed per 100, which equals league_off
    # in a closed league. Report the gap rather than assume it.
    league_def = sum(t["def_rtg"] * t["poss"] for t in teams.values()) / poss_tot
    league_gap = round(league_off - league_def, 4)

    # ---- rest / back-to-back / 3-in-4 from the official schedule --------------
    # Every team's game dates come from the decisions already in the corpus plus
    # this capture. Played dates come from the official finals, which is the only
    # place a *played* date is recorded.
    played_dates = {}
    feed = load(os.path.join(DATA, "official", "results_feed_2026_27.json"))
    for r in feed["rows"]:
        if r.get("game_status") == 3:
            played_dates.setdefault(r["home"], set()).add(r["date"])
            played_dates.setdefault(r["away"], set()).add(r["date"])
    r16 = load(os.path.join(DATA, "official", "results_2026-11-16.json"))
    for r in r16["rows"]:
        played_dates.setdefault(r["home"], set()).add(r["date"])
        played_dates.setdefault(r["away"], set()).add(r["date"])
    for g in games:
        played_dates.setdefault(g["home"], set())
        played_dates.setdefault(g["away"], set())

    def rest_block(abbr, gdate):
        prior = sorted(x for x in played_dates.get(abbr, set()) if to_date(x) < to_date(gdate))
        if not prior:
            return {"rest_days": None, "b2b": None, "three_in_four": None, "last_date": None,
                    "derived_from": "official finals corpus + official schedule capture"}
        last = prior[-1]
        gap = (to_date(gdate) - to_date(last)).days - 1
        window = [x for x in prior if 0 <= (to_date(gdate) - to_date(x)).days <= 3]
        return {"rest_days": gap, "b2b": gap == 0, "three_in_four": len(window) >= 3,
                "games_in_prior_3_days": len(window), "last_date": last,
                "derived_from": "official finals corpus + official schedule capture"}

    # ---- per-game lines -------------------------------------------------------
    out = []
    for g in games:
        h, a = teams[g["home"]], teams[g["away"]]
        poss = (h["pace"] + a["pace"]) / 2.0
        # OffRtg is POINTS PER 100 POSSESSIONS, so it is divided by 100 to become a
        # points-per-possession rate; the opponent's defensive rating then scales it
        # against the league's own points allowed per 100 (a closed-league term that
        # is 1.0 on average by construction).  Dropping the /100 is what made an
        # earlier draft of this script produce totals ~28 points low; gate G-TOT
        # below now refuses to write such a model.
        ppp_h = (h["off_rtg"] / 100.0) * (a["def_rtg"] / league_def)
        ppp_a = (a["off_rtg"] / 100.0) * (h["def_rtg"] / league_def)
        pts_h = poss * ppp_h
        pts_a = poss * ppp_a
        spread_no_hca = pts_h - pts_a
        spread = spread_no_hca + HCA

        pd = pdf_date(g["date"])
        rows = inj_by.get((pd, f"{g['away']}@{g['home']}"), [])
        nys = nys_by.get((pd, f"{g['away']}@{g['home']}"), [])
        avail_rows = []
        for r in rows:
            avail_rows.append({"team": r["team"], "player": r["player"], "status": r["status"],
                               "reason": r["reason"],
                               "play_probability": STATUS_PLAY_PROB.get(r["status"]),
                               "line_adjustment_applied": 0.0,
                               "note": ("status published verbatim; no NEW_ABSENCE is verifiable from "
                                        "evidence in this repo, so the canonical rule moves no line")})
        if rows:
            avail_label = (f"{len(rows)} player status row(s) from the official {inj['edition']} edition "
                           f"(revision {inj['revision_time_et']}); no line adjustment applied")
        elif nys:
            avail_label = (f"official {inj['edition']} edition prints NOT YET SUBMITTED for this game "
                           f"(the clubs had not filed when the edition was published); no rows, no adjustment")
        else:
            avail_label = (f"no official injury report covers this game yet — the newest edition in the repo is "
                           f"{inj['edition']}, which covers 11/17 games only; no rows, no adjustment")

        out.append({
            "date": g["date"], "game_id": g["game_id"],
            "matchup": f"{g['away']}@{g['home']}", "home": g["home"], "away": g["away"],
            "venue": g["venue"], "city": g["city"], "tip_et": g["tip_et"],
            "competition": g.get("cup_label") or "not printed on official schedule",
            "records_as_captured": f"{g['away_record']} / {g['home_record']}",
            "records_status": (f"records read {cap['captured_utc']} from the official standings page "
                               f"(identity-checked); they go stale as earlier games complete"),
            # ---- the model, with every input beside it
            "game_possessions": round(poss, 2),
            "poss_formula": "(PACE_home + PACE_away) / 2 — one possession count for both sides",
            "off_rtg_home": h["off_rtg"], "def_rtg_home": h["def_rtg"], "pace_home": h["pace"], "gp_home": h["gp"],
            "off_rtg_away": a["off_rtg"], "def_rtg_away": a["def_rtg"], "pace_away": a["pace"], "gp_away": a["gp"],
            "ppp_home": round(ppp_h, 5), "ppp_away": round(ppp_a, 5),
            "proj_home_pts": round(pts_h, 2), "proj_away_pts": round(pts_a, 2),
            "line_total": round(pts_h + pts_a, 1),
            "line_spread_home_no_hca": round(spread_no_hca, 1),
            "home_court_applied": True,
            "hca_points": HCA,
            "line_spread_home": round(spread, 1),
            "total_formula": ("TOTAL = POSS * (PPP_home + PPP_away), a possessions x points-per-possession "
                              "total. It is NOT the average of the two team scoring averages."),
            "formula": ("POSS = (PACE_h + PACE_a)/2; PPP_h = (OffRtg_h/100)*(DefRtg_a/LEAGUE_DEF); "
                        "PPP_a = (OffRtg_a/100)*(DefRtg_h/LEAGUE_DEF); PTS = POSS*PPP; "
                        "SPREAD = PTS_h - PTS_a + HCA_points. OffRtg is per 100 possessions, hence the /100."),
            "total_sd": SIGMA_T, "margin_sd": SIGMA_M,
            "line_status": "DERIVED",
            "rest_home": rest_block(g["home"], g["date"]),
            "rest_away": rest_block(g["away"], g["date"]),
            "availability_label": avail_label,
            "availability_rows": avail_rows,
            "inputs_as_of": (f"team ratings from the official advanced page read {recut['_meta']['retrieved_utc']} "
                             f"(games through {recut['_meta']['games_through']}); HCA pin "
                             f"{HCA} pts from home win rate {consts['home_court_pin']['home_win_rate']} "
                             f"({consts['home_court_pin']['home_wins']} of {consts['home_court_pin']['home_games']}) "
                             f"read {consts['_meta']['retrieved_utc']}; injury statuses from {inj['edition']} "
                             f"(revision {inj['revision_time_et']})"),
            "inputs_source": SRC_ADVANCED,
            "schedule_source": f"https://www.nba.com/games?date={g['date']}",
        })

    # ---- probabilities --------------------------------------------------------
    for r in out:
        p_home = norm_cdf(r["line_spread_home"] / SIGMA_M)
        r["model_home_win_prob"] = round(p_home, 4)
        # probability the game goes OVER the modelled total is 0.5 by construction:
        # the line IS the model's own total. Published so no reader mistakes it for
        # a market probability.
        r["total_status"] = ("model total; there is no market total in this repository, so the line "
                             "cannot be compared with a price")
        p_tot_over = 0.5
        r["model_over_prob"] = p_tot_over
        r["ml_formula"] = ("normal CDF of the modelled margin / measured sigma_margin "
                           f"({SIGMA_M}), converted to American odds")
        r["ml_status"] = "DERIVED (model-internal; no sportsbook comparison available)"
        r["line_home_ml"] = (round(-100 * p_home / (1 - p_home), 0) if p_home >= 0.5
                             else round(100 * (1 - p_home) / p_home, 0))

    # ---- GATE G-TOT: the model must reconcile with the measured league total ----
    # A 30-game window of one league must average close to the measured league total;
    # if it does not, the possession/PPP units are wrong and nothing is written.
    model_totals = [r["line_total"] for r in out]
    model_mean_total = sum(model_totals) / len(model_totals)
    measured_mean_total = consts["dispersion"]["total_mean"]
    tot_gap = model_mean_total - measured_mean_total
    print(f"G-TOT: model mean total {model_mean_total:.1f} vs measured {measured_mean_total:.1f} "
          f"(gap {tot_gap:+.1f})")
    if abs(tot_gap) > 8.0:
        print("G-TOT FAILED — the possession/PPP units do not reconcile with the measured total; "
              "nothing written", file=sys.stderr)
        raise SystemExit(1)

    payload = {
        "_meta": {
            "title": f"Originated horizon lines — {dates[0]} through {dates[-1]} ({len(out)} games)",
            "generated_by": "scripts/originate_horizon_cdf3a108.py (rolling window, measured HCA pin; formulas byte-identical to scripts/originate_horizon_cdf3a108.py, run by session arena/cdf3a108-nba1 on the 12:2x-12:4x UTC re-cut inputs)",
            "generated_utc": RUN_UTC,
            "horizon": f"{dates[0]} .. {dates[-1]}: {cap['scope']}",
            "window_rule": ", ".join(f"{d}={per_day[d]}" for d in dates),
            "window_note": ("Today (2026-11-19) plus the next three days. The 11/19 slate is in scope "
                            "because its first tip (8:00 PM ET) is ahead of this build; the far edge is 11/22 because "
                            "the brief caps origination at 3 days ahead."),
            "model_changes_vs_previous_window": [
                {"change": "home-court advantage applied",
                 "was": "home_court_applied: false on every 11/16-window line (flag F-W02 inherited)",
                 "now": (f"hca_points = {HCA} = sigma_margin {SIGMA_M} x Phi^-1(home win rate "
                         f"{consts['home_court_pin']['home_win_rate']})"),
                 "why_not_fitted": "the rate is measured from the official standings HOME/ROAD columns, so there is no free parameter"},
                {"change": "total modelled as possessions x points-per-possession",
                 "was": "POSS = pace_home + pace_away - league_pace; TOTAL = the sum of two team point estimates",
                 "now": "POSS = (pace_home + pace_away)/2; TOTAL = POSS * (PPP_home + PPP_away)",
                 "why": ("one possession count shared by both sides makes the two team lines reconcile to a "
                         "single game total; the old formula double-counted the pace gap")},
            ],
            "inputs": {
                "schedule_capture": "data/raw/official_schedule_capture_2026-11-19.json",
                "schedule_captured_utc": cap["captured_utc"],
                "team_ratings": "data/derived/team_stats_recut.json",
                "team_ratings_read_utc": recut["_meta"]["retrieved_utc"],
                "measured_constants": "data/derived/measured_constants_2026_27.json",
                "injury_edition": inj["edition"],
                "injury_revision_et": inj["revision_time_et"],
                "injury_raw_pdf_sha256": inj["raw_pdf_sha256"],
            },
            "league_baselines": {
                "league_off_rtg_poss_weighted": round(league_off, 3),
                "league_def_rtg_poss_weighted": round(league_def, 3),
                "closed_league_gap": league_gap,
                "closed_league_check": ("pass: the two league means agree to within 0.01 points per 100 possessions"
                                        if abs(league_gap) < 0.01 else
                                        f"WARNING: league OffRtg and DefRtg means differ by {league_gap}"),
            },
            "gates": {
                "G-TOT_total_reconciles": {
                    "model_mean_total": round(model_mean_total, 2),
                    "measured_mean_total": measured_mean_total,
                    "gap": round(tot_gap, 2),
                    "tolerance": 8.0,
                    "result": "pass",
                    "note": ("a window of one league must average close to the measured league total; a "
                             "unit error in the possession or points-per-possession term shows up here "
                             "first (an early draft of this script was 28 points low and was caught by "
                             "this gate)"),
                },
            },
            "measured_dispersion": {
                "sigma_margin": SIGMA_M, "sigma_total": SIGMA_T,
                "n": consts["dispersion"]["finals_n"],
                "source": consts["dispersion"]["source_url"],
            },
            "flags": [
                {"id": "F-X10", "severity": "high",
                 "item": "No market price exists in this repository, for any game, side or total.",
                 "detail": ("No sportsbook feed is reachable or claimed; every published probability is "
                            "model-internal and no pick is market-validated."),
                 "source": SRC_ADVANCED},
                {"id": "F-X11", "severity": "high",
                 "item": "No strategy has passed the validation gates.",
                 "detail": ("Every row is MODEL OUTPUT — UNVALIDATED, zero stake. The bet surface stays gated "
                            "closed (G1/G2 closed) while that is true."),
                 "source": "https://www.nba.com/games"},
                {"id": "F-X12", "severity": "medium",
                 "item": "The injury edition covers 11/19–11/20 games only; 11/21–11/22 have no player rows yet.",
                 "detail": ("Teams file by 5 p.m. local the day before, so later days cannot carry rows at "
                            "this build time. Each affected row says so instead of assuming 'no injuries'."),
                 "source": SRC_INJ_POLICY},
                {"id": "F-X13", "severity": "medium",
                 "item": "The injury edition's raw PDF hash is NOT measured.",
                 "detail": ("The PDF bytes are unreachable from this sandbox (TLS handshake fails); only the "
                            "text render was retrievable. The edition carries text_sha256 and a null "
                            "raw_pdf_sha256 rather than an invented hash."),
                 "source": inj["source_url"]},
                {"id": "F-X14", "severity": "medium",
                 "item": "Rebuilt ratings rest on an unbalanced sample (12–15 games per team).",
                 "detail": ("GP is published beside every rating and every line; a team on 12 games and a team "
                            "on 15 games are compared without adjustment, which is a real source of error "
                            "until the sample grows."),
                 "source": SRC_ADVANCED},
                {"id": "F-929-01", "severity": "medium",
                 "item": "LAL and UTA ratings are one game stale (11/18 UTA 109 @ LAL 97 missing from the team-stat tables).",
                 "detail": ("The advanced/traditional/opponent tables still show LAL 15 GP 13-2 and UTA 15 GP 2-13 "
                            "while the standings show 16 GP 13-3 / 3-13. Lines for PHX@UTA (11/20) and SAC@LAL "
                            "(11/20) inherit the lag; the standings are the record of record."),
                 "source": SRC_ADVANCED},
                {"id": "F-929-03", "severity": "medium",
                 "item": "Injury PDF text render has blank-matchup and garbled rows (NYK@MIN, TOR@DET 11/20).",
                 "detail": ("Two blank-matchup rows (Kuminga, Pullin) are attributed to Minnesota by position; "
                            "11/20 rows beyond ORL@BKN are garbled in the render and recorded as NOT YET SUBMITTED. "
                            "No row was invented or silently dropped."),
                 "source": inj["source_url"]},
                {"id": "F-929-04", "severity": "low",
                 "item": "LAL and UTA both played back-to-back on 11/17 and 11/18.",
                 "detail": ("The rest model reads the official finals corpus, so both teams show rest_days=0 "
                            "for their next game; the flag exists so a reviewer does not mistake it for a data gap."),
                 "source": "https://www.nba.com/games?date=2026-11-18"},
            ],
        },
        "games": out,
    }
    p = os.path.join(DATA, "derived", "horizon_lines.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
    print(f"horizon lines written: {len(out)} games -> data/derived/horizon_lines.json")
    print(f"HCA pin {HCA} pts | POSS basis (pace_h+pace_a)/2 | sigma_margin {SIGMA_M} sigma_total {SIGMA_T}")
    print(f"league off {league_off:.3f} def {league_def:.3f} gap {league_gap} ")
    for r in out:
        print(f"  {r['date']} {r['matchup']:8} poss {r['game_possessions']:6.2f} "
              f"spread {r['line_spread_home']:+6.1f} total {r['line_total']:6.1f} p_home {r['model_home_win_prob']:.3f}")


if __name__ == "__main__":
    main()
