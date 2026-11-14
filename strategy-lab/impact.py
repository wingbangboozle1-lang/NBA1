"""Module 6 - what the unsupportable parameter is worth, game by game, on the live slate.

`engine/model_core.py` puts a back-to-back penalty into every line:

    margin += HCA - b2b_penalty * (home_b2b - away_b2b)

and `site/data/backtest.json` publishes the fitted value and the window it was fitted on, both
read from that file at run time rather than quoted here. Measured on the 144 games of this season
where both teams have a game on
record, the same effect is 0.02 points with a standard error of 4.43 - a band wide enough to
contain the site's number and too wide to justify spending 6.1 points of line on it.

This module prices the disagreement on the games that are actually about to be played, so the
decision is made with a number attached instead of an argument.
"""
from __future__ import annotations

from labdata import load, rest_maps, site_fit
from statools import rnd




def run(ctx, measured=None):
    pub = site_fit()
    SITE_B2B = pub["b2b_penalty_applied"] or 0.0
    season = {"coef": None, "se": None, "n": None}
    if measured:
        season = {"coef": measured["coef"], "se": measured["se"], "n": measured["n"],
                  "ci": measured["ci95"]}

    yes, _ = rest_maps(ctx["games"], True)
    rows = []
    for h in load("site", "data", "lines.json")["rows"]:
        hb = 1 if (h.get("home_b2b") or 0) else 0
        ab = 1 if (h.get("away_b2b") or 0) else 0
        adj_site = SITE_B2B * (hb - ab)
        adj_season = (season["coef"] or 0.0) * (hb - ab)
        a, b = yes(h["home"], h["date"]), yes(h["away"], h["date"])
        rows.append({
            "date": h["date"], "time_et": h.get("time_et"), "matchup": h["matchup"],
            "game_id": h["game_id"],
            "home_b2b_published": hb, "away_b2b_published": ab,
            "home_b2b_recomputed": 1 if a["b2b"] else 0, "away_b2b_recomputed": 1 if b["b2b"] else 0,
            "home_last_game": a["last"], "away_last_game": b["last"],
            "rest_matches_this_session": bool(a["b2b"]) == bool(hb) and bool(b["b2b"]) == bool(ab),
            "line_adjustment_from_site_parameter": rnd(-adj_site, 2),
            "line_adjustment_from_season_estimate": rnd(-adj_season, 2),
            "disagreement_points": rnd(abs(adj_site - adj_season), 2),
            "model_spread_home_published": h.get("model_spread_home"),
            "source_url": "https://www.nba.com/game/"
                          f"{h['away'].lower()}-vs-{h['home'].lower()}-{h['game_id']}",
        })
    n_shift = sum(1 for r in rows if r["disagreement_points"] >= 3.0)
    disagree = [r["disagreement_points"] for r in rows]
    return {
        "published_parameter": {"b2b_penalty": SITE_B2B,
                                "fitted_on": f'{pub["n_games"]} games, {pub["window_first"]}..{pub["window_last"]}',
                                "site_se": pub["b2b_se"], "site_t": pub["b2b_t"],
                                "site_disclosure": pub["b2b_disclosure"],
                                "source_url": pub["source_url"]},
        "season_measurement": dict(season, source_url="https://www.nba.com/games?date=2026-10-20"),
        "rows": rows,
        "summary": {
            "horizon_games": len(rows),
            "games_where_the_two_positions_differ_by_3_points_or_more": n_shift,
            "mean_abs_disagreement_points": rnd(sum(disagree) / len(disagree), 2) if disagree else None,
            "max_abs_disagreement_points": rnd(max(disagree), 2) if disagree else None,
            "rest_flags_reproduced_from_the_official_schedule": sum(1 for r in rows if r["rest_matches_this_session"]),
            "decision_this_informs": ("keep, shrink or drop the back-to-back term. Dropping it moves "
                                      "these lines by up to 6.1 points, so it has to be a decision, not a "
                                      "silent re-fit"),
        },
        "recommendation": {
            "action": "shrink the term toward the season estimate and publish the interval on the line",
            "why": ("a parameter fitted on one week is being applied to every game; the season band is "
                    "an order of magnitude wider than the difference between 0 and 6.1, so the honest "
                    "line carries the uncertainty rather than picking the point estimate"),
            "cost": "one re-fit and a re-published slate",
            "risk_if_ignored": "lines move by up to 6.1 points in whichever direction a one-week fit happened to point",
        },
    }
