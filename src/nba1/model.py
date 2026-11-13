"""Originated lines, implied probabilities, and correlation values.

All *inputs* come from verified official sources (captured in data/*.json).
Everything produced here is our own originated number — we do not copy a
sportsbook's line. Where a value would require data we have not verified
(e.g. a live book's odds, a live injury report, a player's current roster
team), it is left as None and flagged, never inferred.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_json(name: str) -> dict[str, Any]:
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def standings_map(standings_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["abbr"]: row for row in standings_doc["standings"]}


def league_average_ppg(standings_doc: dict[str, Any]) -> float:
    """League-average points scored and allowed per game (verified)."""
    vals = [r["ps_g"] for r in standings_doc["standings"]]
    return sum(vals) / len(vals)


# --------------------------------------------------------------------------- #
# Originated team lines
# --------------------------------------------------------------------------- #
# Simple-rating expected score: a team's expected points vs an opponent are the
# average of its own scoring (PS/G) and the opponent's points allowed (PA/G).
# This is our own originated estimate, not a book line.
def expected_scores(away: dict[str, Any], home: dict[str, Any]) -> tuple[float, float]:
    away_exp = (away["ps_g"] + home["pa_g"]) / 2.0
    home_exp = (home["ps_g"] + away["pa_g"]) / 2.0
    return round(away_exp, 1), round(home_exp, 1)


def originated_spread_total(away: dict[str, Any], home: dict[str, Any]) -> dict[str, Any]:
    """Originate a point spread and total for a matchup.

    Spread convention: positive = home favored. Half-points are avoided so the
    model does not fabricate a push-avoiding number without a market to compare
    to; we round to the nearest whole point and note it.
    """
    away_exp, home_exp = expected_scores(away, home)
    spread = round(home_exp - away_exp)          # home-favored positive
    total = round(away_exp + home_exp)
    expected_margin = home_exp - away_exp
    return {
        "away_expected": away_exp,
        "home_expected": home_exp,
        "spread": spread,                       # home spread (e.g. -4 means home favored by 4)
        "spread_label": f"{home['abbr']} {spread:+d}" if spread >= 0 else f"{home['abbr']} {spread}",
        "total": total,
        "expected_margin": round(expected_margin, 2),
        "pace_note": "model-originated; inputs PS/G & PA/G verified from Basketball-Reference",
    }


def implied_win_prob(expected_margin: float, k: float = 0.16) -> dict[str, float]:
    """Logistic mapping of expected margin to win probability (originated)."""
    p_home = 1.0 / (1.0 + math.exp(-k * expected_margin))
    return {"home_win_prob": round(p_home, 4), "away_win_prob": round(1 - p_home, 4)}


def implied_prob_cover(spread: int, home_win_prob: float) -> dict[str, float]:
    """Approximate cover probability given the originated spread.

    A home spread of ``spread`` means the home team must win by more than
    ``spread`` to cover. We shift the win-probability curve by the spread.
    """
    # Treat each point of spread as ~0.16 in probability (same k as above).
    k = 0.16
    p_home_cover = 1.0 / (1.0 + math.exp(-k * (expected_margin_from_spread(spread, home_win_prob))))
    # Simpler, self-consistent approach: derive margin from home_win_prob then
    # shift by the spread.
    margin = math.log(home_win_prob / (1 - home_win_prob)) / k
    shifted = margin - spread
    p_cover = 1.0 / (1.0 + math.exp(-k * shifted))
    return {
        "home_cover_prob": round(p_cover, 4),
        "away_cover_prob": round(1 - p_cover, 4),
    }


def expected_margin_from_spread(spread: int, home_win_prob: float) -> float:
    k = 0.16
    return math.log(home_win_prob / (1 - home_win_prob)) / k


# --------------------------------------------------------------------------- #
# Originated player props
# --------------------------------------------------------------------------- #
def originated_player_prop(player_ppg: float, opponent_pa_g: float,
                           league_avg: float, minutes_factor: float = 1.0) -> dict[str, Any]:
    """Originate a points prop for a player from verified per-game scoring.

    opponent_pa_g is the opponent's verified points-allowed-per-game; we blend
    the player's own scoring with the opponent's defensive strength and the
    league average to produce our own prop total.
    """
    # Blend: 50% player rate, 25% opponent defensive rate, 25% league average.
    raw = 0.50 * player_ppg + 0.25 * opponent_pa_g + 0.25 * league_avg
    prop_total = round(raw * minutes_factor, 1)
    # Probability the player exceeds the prop: logistic on (raw - prop_total).
    k = 0.18
    p_over = 1.0 / (1.0 + math.exp(-k * (raw - prop_total)))
    return {
        "player_ppg_input": player_ppg,
        "opponent_pa_g_input": opponent_pa_g,
        "league_avg_input": round(league_avg, 2),
        "prop_total": prop_total,
        "prob_over": round(p_over, 4),
        "prob_under": round(1 - p_over, 4),
        "note": "model-originated; player PPG and opponent PA/G must be verified from official sources before use",
    }


# --------------------------------------------------------------------------- #
# Correlation values
# --------------------------------------------------------------------------- #
def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return 0.0 if den == 0 else num / den


def correlation_matrix(standings_doc: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Pearson correlation among key team metrics (verified inputs).

    These values inform strategy design — e.g. how closely scoring, defense,
    and winning are related, and whether parlay legs are correlated.
    """
    metrics = ["ps_g", "pa_g", "srs", "wl_pct"]
    rows = standings_doc["standings"]
    cols = {m: [float(r[m]) for r in rows] for m in metrics}
    out: dict[str, dict[str, float]] = {}
    for a in metrics:
        out[a] = {}
        for b in metrics:
            out[a][b] = round(pearson(cols[a], cols[b]), 3)
    return out


# --------------------------------------------------------------------------- #
# Line origination for a full slate
# --------------------------------------------------------------------------- #
def originate_slate(slate_doc: dict[str, Any], sm: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Originate a spread + total + win/cover probabilities for every game."""
    out: list[dict[str, Any]] = []
    for g in slate_doc["slate"]:
        away = sm.get(_abbr(g["away"], sm))
        home = sm.get(_abbr(g["home"], sm))
        if away is None or home is None:
            out.append({**g, "originated": None,
                        "flag": "team abbreviation not matched in verified standings — unverified"})
            continue
        line = originated_spread_total(away, home)
        probs = implied_win_prob(line["expected_margin"])
        cover = implied_prob_cover(line["spread"], probs["home_win_prob"])
        out.append({
            "date": g["date"], "away": g["away"], "home": g["home"],
            "time_et": g.get("time_et"), "arena": g.get("arena"), "group": g.get("group"),
            "game_id": g.get("game_id"), "preview": g.get("preview"),
            "away_abbr": away["abbr"], "home_abbr": home["abbr"],
            "originated": {**line, "win_prob": probs, "cover_prob": cover,
                           "source_standings": slate_doc.get("source"),
                           "source_schedule": slate_doc.get("source_schedule") or "https://www.nba.com/schedule"},
        })
    return out


def _abbr(team_name: str, sm: dict[str, dict[str, Any]]) -> str:
    """Resolve a full team name to its abbreviation against verified standings."""
    name = team_name.replace(" ", "").lower()
    for abbr, row in sm.items():
        if row["team"].replace(" ", "").lower() == name:
            return abbr
    # Try a couple of common aliases so nicknames still match (spaces removed).
    aliases = {
        "losangeleslakers": "LAL", "laclippers": "LAC", "newyorkknicks": "NYK",
        "oklahomacitythunder": "OKC", "goldenstatewarriors": "GSW",
        "portlandtrailblazers": "POR", "sacramentokings": "SAC",
        "sanantonioSpurs": "SAS", "sanantonio spurs": "SAS",
        "indiana pacers": "IND", "philadelphia76ers": "PHI", "philadelphia 76ers": "PHI",
        "la clippers": "LAC", "la lakers": "LAL", "ny knicks": "NYK",
    }
    key = team_name.replace(" ", "").lower()
    return aliases.get(key, team_name.upper()[:3])


if __name__ == "__main__":
    sd = load_json("standings_2026_27.json")
    sm = standings_map(sd)
    print("League avg PPG:", round(league_average_ppg(sd), 2))
    print("Correlations:", json.dumps(correlation_matrix(sd), indent=2))
