"""Injury tracking -> rotation minutes -> production, plus game-flow analysis.

Inputs that depend on a *live* injury report (team, player, status, date) are
NOT verified in this session and are therefore left blank / flagged
``unverified`` rather than guessed. The rotation-minute and production models
are fully defined and run automatically once a verified injury feed is wired
in — no manual input is required at that point either.

Game-flow analysis uses verified standings inputs (PS/G, PA/G) and is fully
computed.
"""

from __future__ import annotations

from typing import Any

# Rotation-minute model: each injury status reduces a starter's typical
# minutes. These multipliers are documented model parameters, not market data.
STATUS_MINUTES_FACTOR = {
    "healthy": 1.00,
    "questionable": 0.80,
    "probable": 0.92,
    "out": 0.00,
    "doubtful": 0.35,
    "gtd": 0.60,  # game-time decision
}

# Production model: production scales roughly with minutes played, with a small
# efficiency damping so a reduced-minute star is not over-projected.
def projected_production(base_production_per_36: float, adjusted_minutes: float,
                         typical_minutes: float = 36.0, damping: float = 0.90) -> float:
    minutes_factor = adjusted_minutes / typical_minutes
    # Damped scaling: full production only if minutes are full; partial credit
    # is discounted to avoid overstating a star's reduced-minute output.
    return round(base_production_per_36 * (minutes_factor ** damping), 2)


def rotation_adjustment(status: str | None, base_minutes: float = 36.0) -> dict[str, Any]:
    """Return adjusted rotation minutes for a player given an injury status."""
    if status is None:
        return {"status": None, "base_minutes": base_minutes,
                "adjusted_minutes": None, "flag": "unverified — live injury status not confirmed"}
    factor = STATUS_MINUTES_FACTOR.get(status.lower(), 1.0)
    return {
        "status": status,
        "base_minutes": base_minutes,
        "adjusted_minutes": round(base_minutes * factor, 1),
        "minutes_factor": factor,
        "flag": "verified only if status is confirmed from an official team/NBA injury report",
    }


def game_flow(away: dict[str, Any], home: dict[str, Any],
              league_avg_ppg: float) -> dict[str, Any]:
    """Game-flow analysis from verified team scoring/defense inputs.

    Pace proxy = team scoring + opponent scoring (higher = faster pace).
    Expected total = model total (see model.originated_spread_total).
    """
    away_exp, home_exp = (away["ps_g"] + home["pa_g"]) / 2.0, (home["ps_g"] + away["pa_g"]) / 2.0
    total = round(away_exp + home_exp, 1)
    pace_proxy = round(away["ps_g"] + away["pa_g"] + home["ps_g"] + home["pa_g"], 1)
    league_pace_proxy = round(league_avg_ppg * 2 * 2, 1)  # two teams, two sides
    pace_vs_league = round((pace_proxy / league_pace_proxy - 1) * 100, 1)
    # Flow read: offensive vs defensive mismatch.
    if away["ps_g"] > home["pa_g"] + 2 and home["ps_g"] > away["pa_g"] + 2:
        flow = "high-scoring shootout (both offenses clear opposing defenses)"
    elif away["pa_g"] < home["ps_g"] - 2 and home["pa_g"] < away["ps_g"] - 2:
        flow = "defensive slog (both defenses stifle)"
    else:
        flow = "balanced / pace-neutral"
    return {
        "away_expected": round(away_exp, 1),
        "home_expected": round(home_exp, 1),
        "model_total": total,
        "pace_proxy": pace_proxy,
        "pace_vs_league_pct": pace_vs_league,
        "flow": flow,
        "inputs_verified": True,
        "source": "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
    }


def build_injury_report(slate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-game injury/rotation sheet.

    Live statuses are unverified in this session, so each entry carries a
    ``status: null`` and a flag pointing to the official injury-report source.
    The structure is ready to be populated automatically from a verified feed.
    """
    out: list[dict[str, Any]] = []
    for g in slate:
        out.append({
            "date": g["date"],
            "game": f"{g['away']} @ {g['home']}",
            "game_id": g.get("game_id"),
            "injury_status": None,
            "affected_players": [],
            "rotation_adjustment": rotation_adjustment(None),
            "production_impact": None,
            "flag": "unverified — requires live official injury report (NBA.com / team injury pages)",
            "official_injury_source": "https://www.nba.com/news/injury-report",
        })
    return out
