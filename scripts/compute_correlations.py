#!/usr/bin/env python3
"""
compute_correlations.py — correlation values, split into three honesty tiers.

TIER A — EMPIRICAL (computed here, from official NBA.com team data, n=30 teams)
    Pearson r between team-level quantities across the league cross-section. This is a real
    computed number with a real n, and a two-sided significance test is reported.

TIER B — STRUCTURAL (deterministic identity, not a correlation)
    Relationships that are true by construction, e.g. NetRtg = OffRtg - DefRtg. Reported so that
    nobody "discovers" an identity as if it were an edge.

TIER C — NOT COMPUTABLE FROM OFFICIAL SOURCES IN THIS ENVIRONMENT
    Same-game-parlay correlations (e.g. "player points" vs "team total", "player rebounds" vs
    "same player points") need a player game-log / play-by-play corpus that could not be retrieved
    here. These rows are emitted with value = null and a clear reason. They are NOT guessed.
"""
import json
import math
import os
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def load(n):
    with open(os.path.join(DATA, n), encoding="utf-8") as f:
        return json.load(f)


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def p_two_sided(r, n):
    """Two-sided p-value for a Pearson r using the t approximation."""
    if r is None or n < 3 or abs(r) >= 1:
        return None
    t = r * math.sqrt((n - 2) / (1 - r * r))
    # Student-t survival via incomplete beta is overkill here; use the normal approximation and
    # label it as such. For n=30 the difference is small and is disclosed.
    z = abs(t)
    return 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))


def main():
    adv = load("teams_advanced_2026_27.json")["rows"]
    sc = load("teams_scoring_2026_27.json")["rows"]
    scor = {r["abbr"]: r for r in sc}

    cols = {}
    for t in adv:
        a = t["abbr"]
        s = scor[a]
        cols[a] = {
            "pace": t["pace"],
            "off_rtg": t["off_rtg"],
            "def_rtg": t["def_rtg"],
            "net_rtg": t["net_rtg"],
            "efg_pct": t["efg_pct"],
            "ts_pct": t["ts_pct"],
            "tov_pct": t["tov_pct"],
            "oreb_pct": t["oreb_pct"],
            "ast_pct": t["ast_pct"],
            "win_pct": t["w"] / t["gp"],
            "pts": s["pts"],
            "opp_pts": s["opp_pts"],
            "game_total": s["pts"] + s["opp_pts"],
            "plus_minus": s["plus_minus"],
            "fg3_pct": s["fg3_pct"],
            "fg3a": s["fg3a"],
        }

    pairs_of_interest = [
        ("pace", "game_total", "Pace vs that team's average game total — the core over/under driver."),
        ("pace", "pts", "Pace vs own scoring."),
        ("off_rtg", "win_pct", "Offensive rating vs win rate."),
        ("def_rtg", "win_pct", "Defensive rating vs win rate (lower DefRtg is better, so r should be negative)."),
        ("fg3_pct", "off_rtg", "Three-point percentage vs offensive rating."),
        ("fg3a", "pace", "Three-point volume vs pace."),
        ("tov_pct", "off_rtg", "Turnover rate vs offensive rating (should be negative)."),
        ("oreb_pct", "off_rtg", "Offensive rebounding vs offensive rating."),
        ("efg_pct", "off_rtg", "Effective field-goal percentage vs offensive rating."),
        ("ast_pct", "pace", "Assist rate vs pace."),
    ]

    n = len(cols)
    tier_a = []
    for a, b, why in pairs_of_interest:
        xs = [cols[k][a] for k in cols]
        ys = [cols[k][b] for k in cols]
        r = pearson(xs, ys)
        p = p_two_sided(r, n)
        tier_a.append({
            "x": a, "y": b, "r": round(r, 4) if r is not None else None,
            "r_squared": round(r * r, 4) if r is not None else None,
            "p_two_sided_approx": round(p, 5) if p is not None else None,
            "n": n,
            "significant_at_0_05": (p is not None and p < 0.05),
            "interpretation": why,
            "derivation": "EMPIRICAL — Pearson r across the 30-team cross-section of official NBA.com season-to-date values",
            "source_url": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season and https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        })

    tier_b = [
        {"relationship": "NetRtg = OffRtg - DefRtg", "value": "identity", "note": "True by definition (NBA.com glossary: 100*(PTS-OPP PTS)/POSS reduces to the difference of the two ratings).", "source_url": "https://www.nba.com/stats/help/glossary"},
        {"relationship": "PTS = 2*FGM + 3PM + FTM", "value": "identity", "note": "Scoring identity; enforced as a data check on every player row in verify_data.py.", "source_url": "https://official.nba.com/rule-no-5-scoring-and-timing/"},
        {"relationship": "Average margin ≈ NetRtg * possessions / 100 / games", "value": "near-identity",
         "note": "An earlier version of this register listed 'plus_minus vs net_rtg' as an empirical correlation. It came out at r=0.999, which is the tell: it is an identity, not a finding. It has been moved here rather than presented as an edge.",
         "source_url": "https://www.nba.com/stats/help/glossary"},
        {"relationship": "Game spread sign convention", "value": "identity", "note": "SPREAD = home points - away points, so a negative spread means the home team is favoured.", "source_url": "https://www.nba.com/stats/help/glossary"},
    ]

    tier_c = [
        {"pair": "Player points OVER + same player rebounds OVER",
         "expected_sign": "positive",
         "value": None,
         "why_missing": "Needs a player game-log corpus (per-game values for many games) to measure co-movement. NBA.com exposes per-game logs one player at a time; the volume needed (thousands of rows) could not be retrieved in this environment.",
         "how_to_obtain": "Pull https://www.nba.com/stats/players/boxscores for every player-season, or use the official NBA stats API game logs."},
        {"pair": "Player points OVER + same-game team total OVER",
         "expected_sign": "positive",
         "value": None,
         "why_missing": "Needs the joint distribution of a player's stat and the game total. Requires game logs joined to final scores.",
         "how_to_obtain": "Join per-game player box scores to final scores from https://www.nba.com/games."},
        {"pair": "Two teammates' points OVER (usage cannibalisation)",
         "expected_sign": "negative",
         "value": None,
         "why_missing": "Needs teammate game logs and controls for total team possessions.",
         "how_to_obtain": "Same corpus as above, grouped by team-game."},
        {"pair": "Team spread cover + team total OVER",
         "expected_sign": "positive (a fast game helps the favourite's total)",
         "value": None,
         "why_missing": "Needs historical closing lines to define 'cover'. No official line source is reachable here.",
         "how_to_obtain": "Requires a licensed odds archive. This is the single largest blocker in the project."},
        {"pair": "Player points OVER + opponent's defensive rating quartile",
         "expected_sign": "negative",
         "value": None,
         "why_missing": "Needs per-game player performances against specific opponents.",
         "how_to_obtain": "NBA.com player splits by opponent, aggregated across a full season."},
        {"pair": "Parlay legs from different games",
         "expected_sign": "zero (approximately independent)",
         "value": None,
         "why_missing": "Independence is an assumption, not a measurement. Two games on the same slate can share weather/travel/referee crews, so the assumption itself is unverified.",
         "how_to_obtain": "Test residual correlation of same-slate, cross-game legs against a historical results corpus."},
    ]

    out = {
        "_meta": {
            "title": "Correlation register",
            "generated_by": "scripts/compute_correlations.py",
            "generated_utc": "2026-11-13",
            "tiers": {
                "A": "Empirical — computed from official NBA.com team data, with n and a p-value.",
                "B": "Structural — true by construction, not an edge.",
                "C": "Not computed — data required is unavailable; value left null and NOT guessed."
            },
            "method_note": "p-values use the normal approximation to the t distribution. With n=30 this is close to exact but is disclosed rather than implied.",
            "multiple_comparisons_note": "10 pairs were tested. At alpha=0.05 you expect about 0.6 false positives by chance alone. Treat any single marginal result with suspicion; the site reports the count of significant pairs but does not treat them as independently confirmed.",
        },
        "tier_a_empirical": tier_a,
        "tier_b_structural": tier_b,
        "tier_c_not_computable": tier_c,
    }
    with open(os.path.join(DATA, "derived", "correlations.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f"{'x':12} {'y':12} {'r':>7} {'r^2':>7} {'p':>9}  sig")
    for row in tier_a:
        print(f"{row['x']:12} {row['y']:12} {row['r']:7.3f} {row['r_squared']:7.3f} "
              f"{row['p_two_sided_approx']:9.5f}  {'YES' if row['significant_at_0_05'] else ''}")
    print(f"\nsignificant pairs: {sum(1 for r in tier_a if r['significant_at_0_05'])}/{len(tier_a)}")
    print(f"tier C (not computable): {len(tier_c)} pairs documented as null")


if __name__ == "__main__":
    main()
