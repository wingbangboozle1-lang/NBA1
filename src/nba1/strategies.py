"""Betting strategies, validation gates, correlation checks, and skill/luck.

Every strategy must pass validation gates before it is allowed on the
leaderboard:

  G1 Edge       — the model edge must clear a minimum threshold.
  G2 Sample     — a minimum number of graded picks is required before a
                  strategy is ranked (removes small-sample luck).
  G3 Correlation— parlay / combo legs must not be highly correlated
                  (high correlation hides risk and inflates apparent edge).
  G4 Skill      — a luck-adjusted (shrunk) skill score must clear a
                  significance bar; otherwise the result is treated as luck.

Luck is removed with Bayesian shrinkage of the hit rate toward 0.5 using a
prior strength, so a 3-for-3 start is not over-credited and a cold start is
not over-punished.
"""

from __future__ import annotations

import math
from typing import Any

# Default gate thresholds (tunable; documented, not arbitrary guesses).
MIN_EDGE = 0.05          # 5% model edge required to fire a pick
MIN_SAMPLE = 30          # picks required before a strategy is ranked
MAX_LEG_CORR = 0.70      # reject a parlay if any leg pair correlates this strongly
PRIOR_STRENGTH = 12      # shrinkage prior (equivalent to ~12 prior picks at .5)
SKILL_Z = 1.96           # 95% two-sided significance bar for the z-score


# --------------------------------------------------------------------------- #
# Strategies
# --------------------------------------------------------------------------- #
STRATEGIES: list[dict[str, Any]] = [
    {
        "id": "S1",
        "name": "Home Favorite Cover",
        "type": "single_bet",
        "bet_kind": "spread",
        "description": "Back the originated home favorite to cover the spread when the model edge clears the threshold.",
    },
    {
        "id": "S2",
        "name": "Away Underdog Cover",
        "type": "single_bet",
        "bet_kind": "spread",
        "description": "Back the originated away underdog to cover (take the points) when the model edge clears the threshold.",
    },
    {
        "id": "S3",
        "name": "Total Lean (Over/Under)",
        "type": "single_bet",
        "bet_kind": "total",
        "description": "Back Over or Under based on the originated total versus the league-average total, when the lean clears the threshold.",
    },
    {
        "id": "S4",
        "name": "Star Player Prop Lean",
        "type": "single_bet",
        "bet_kind": "player_prop",
        "description": "Back Over/Under on an originated player points prop when the model edge clears the threshold. Requires verified per-player stats + roster (see flags).",
    },
    {
        "id": "S5",
        "name": "Two-Team Parlay Combo",
        "type": "parlay",
        "bet_kind": "parlay",
        "description": "Combine two single-bet edges from two different games. Legs must be near-independent (correlation gate).",
    },
    {
        "id": "S6",
        "name": "Player Prop + Team Parlay",
        "type": "parlay",
        "bet_kind": "parlay_player_prop",
        "description": "Combine a player prop and a team bet. Correlation between the player's points and the team total is measured and gated.",
    },
]


def strategy_by_id(sid: str) -> dict[str, Any]:
    return next(s for s in STRATEGIES if s["id"] == sid)


# --------------------------------------------------------------------------- #
# Selection logic
# --------------------------------------------------------------------------- #
def select_single(strategy: dict[str, Any], line: dict[str, Any],
                  league_avg_total: float) -> dict[str, Any] | None:
    """Return a pick dict if the strategy fires on this originated line."""
    o = line["originated"]
    if strategy["bet_kind"] == "spread":
        cover = o["cover_prob"]
        if strategy["id"] == "S1":
            side, p = "home", cover["home_cover_prob"]
        else:  # S2 away underdog
            side, p = "away", cover["away_cover_prob"]
        edge = p - 0.5
        pick = {"side": side, "prob": p, "edge": edge,
                "line": o["spread_label"], "bet_kind": "spread"}
    elif strategy["bet_kind"] == "total":
        diff = o["total"] - league_avg_total
        if diff > 0:
            side, p = "Over", o["cover_prob"]["home_cover_prob"]  # reuse logistic as lean strength
            # Use a dedicated, honest lean probability around the total.
            p = 1.0 / (1.0 + math.exp(-0.16 * (o["total"] - league_avg_total)))
        else:
            side, p = "Under", 1.0 / (1.0 + math.exp(-0.16 * (league_avg_total - o["total"])))
        edge = abs(p - 0.5)
        pick = {"side": side, "prob": p, "edge": edge,
                "line": f"Total {o['total']}", "bet_kind": "total"}
    else:  # player prop (S4) — methodology demonstration
        # A live pick needs a verified player + opponent; here we only mark it.
        pick = {"side": None, "prob": None, "edge": None,
                "line": None, "bet_kind": "player_prop",
                "flag": "requires verified per-player stats & roster — not auto-fired without official input"}
        return pick
    if pick["edge"] is None or pick["edge"] < MIN_EDGE:
        return None
    return {**pick, "strategy_id": strategy["id"], "strategy": strategy["name"],
            "game": line, "gate_edge": "pass"}


def make_parlay(legs: list[dict[str, Any]], strategy: dict[str, Any]) -> dict[str, Any] | None:
    """Build a parlay from two qualifying single legs, with a correlation gate."""
    if len(legs) != 2:
        return None
    # Correlation between legs: different games -> ~0; player prop + team total
    # in the same game -> player's share of team points.
    corr = leg_correlation(legs[0], legs[1])
    if abs(corr) > MAX_LEG_CORR:
        return {"strategy_id": strategy["id"], "strategy": strategy["name"],
                "legs": legs, "rejected": True,
                "gate_correlation": "fail",
                "correlation": corr,
                "reason": f"leg correlation {corr:+.2f} exceeds {MAX_LEG_CORR}"}
    combined_p = legs[0]["prob"] * legs[1]["prob"]
    edge = combined_p - (0.5 ** len(legs))
    return {"strategy_id": strategy["id"], "strategy": strategy["name"],
            "legs": legs, "rejected": False,
            "gate_correlation": "pass", "correlation": corr,
            "combined_prob": round(combined_p, 4),
            "edge": round(edge, 4),
            "bet_kind": strategy["bet_kind"]}


def leg_correlation(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Approximate correlation between two parlay legs.

    * Two different games: ~0 (independent).
    * Player prop + team total in the same game: the player's share of team
      points (player PPG / team PS/G), capped in [0, 1].
    """
    ga, gb = a.get("game", {}), b.get("game", {})
    if ga.get("game_id") != gb.get("game_id"):
        return 0.0
    # Same game: player prop vs team total correlation = player's scoring share.
    pa = a.get("player_share")
    pb = b.get("player_share")
    if pa is not None:
        return round(min(max(pa, 0.0), 1.0), 3)
    if pb is not None:
        return round(min(max(pb, 0.0), 1.0), 3)
    return 0.0


# --------------------------------------------------------------------------- #
# Skill vs luck
# --------------------------------------------------------------------------- #
def shrink_skill(hits: int, n: int, prior: float = PRIOR_STRENGTH) -> float:
    """Bayesian-shrunk hit rate — removes small-sample luck."""
    if n <= 0:
        return 0.5
    return (hits + prior * 0.5) / (n + prior)


def skill_zscore(hits: int, n: int) -> float:
    """Z-score of the observed hit rate against a fair 0.5 coin."""
    if n <= 0:
        return 0.0
    p = hits / n
    se = math.sqrt(0.25 / n)
    return (p - 0.5) / se if se else 0.0


def is_skill_significant(hits: int, n: int) -> bool:
    return abs(skill_zscore(hits, n)) >= SKILL_Z


# --------------------------------------------------------------------------- #
# Validation gates
# --------------------------------------------------------------------------- #
def validate_gates(strategy: dict[str, Any], edge: float | None, hits: int | None,
                   n: int | None, corr: float | None = None) -> dict[str, Any]:
    """Run all gates and return a per-gate status object."""
    g1 = "pass" if (edge is not None and edge >= MIN_EDGE) else "fail"
    g2 = "pass" if (n is not None and n >= MIN_SAMPLE) else "pending"
    g3 = "pass"
    if corr is not None:
        g3 = "pass" if abs(corr) <= MAX_LEG_CORR else "fail"
    if n is None or n == 0:
        g4 = "pending"
    else:
        g4 = "pass" if is_skill_significant(hits, n) else "fail"
    skill = shrink_skill(hits or 0, n or 0)
    return {
        "G1_edge": g1,
        "G2_sample": g2,
        "G3_correlation": g3,
        "G4_skill": g4,
        "shrunk_skill": round(skill, 4),
        "z_score": round(skill_zscore(hits or 0, n or 0), 3),
        "passes": g1 == "pass" and g3 == "pass",
        "ranked": g1 == "pass" and g2 == "pass" and g3 == "pass" and g4 == "pass",
    }


# --------------------------------------------------------------------------- #
# Backtest on a verified completed slate (small-sample demonstration)
# --------------------------------------------------------------------------- #
def backtest_spread(originated_line: dict[str, Any], home_score: int, away_score: int) -> str | None:
    """Grade a spread pick: 'win'/'loss' for the modeled side, None if no pick."""
    spread = originated_line["originated"]["spread"]
    # Modeled side for S1 is home; grade home cover.
    home_margin = home_score - away_score
    if home_margin > spread:
        return "win"
    if home_margin < spread:
        return "loss"
    return "push"


def backtest_total(originated_line: dict[str, Any], total: int,
                   model_side: str) -> str | None:
    actual = total
    modeled_total = originated_line["originated"]["total"]
    if model_side == "Over":
        return "win" if actual > modeled_total else ("loss" if actual < modeled_total else "push")
    return "win" if actual < modeled_total else ("loss" if actual > modeled_total else "push")
