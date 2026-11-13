"""Line origination.

Everything here starts from an official NBA.com snapshot. Nothing is
invented: where a number is a modelling CHOICE rather than a measured
official value it is tagged in `ASSUMPTIONS` and surfaced on the site as an
assumption (not a sourced fact).

Model family
------------
Additive four-factor-lite efficiency model (the standard published form):

    pts_per_100(home)   = ORTG(home) + DRTG(away) - L
    pts_per_100(away)   = ORTG(away) + DRTG(home) - L
    possessions         = (PACE(home) + PACE(away)) / 2
    margin(home)        = (pts100_h - pts100_a) * poss/100 + HCA + adj
    total               = (pts100_h + pts100_a) * poss/100 + adj

A useful identity of the additive form: the per-100-possession margin
collapses to NETR(home) - NETR(away). The opponent-interaction term therefore
adds nothing to the side; all of the side's signal has to come from
shrinkage, home court, rest and availability. That is stated on the Model page
because it explains why the refinements below are the whole game.
"""

import math

from common import ABBR, TEAM_NAME, mean, norm_cdf, rnd

ASSUMPTIONS = {
    "shrink_k": {
        "value": 2.8,
        "unit": "league-average games added to each team's rating as a prior",
        "status": "DERIVED, not guessed: an empirical-Bayes reliability calculation based on "
                  "the spread of net ratings and the spread of forecast residuals. The single-game "
                  "noise term in that calculation is estimated on the test window, so k is partly "
                  "test-informed. A fixed-k sensitivity sweep is published on the Validation page. "
                  "Flagged F4.",
    },
    "alpha_offense_share": {
        "value": 0.60,
        "unit": "share of an availability loss that shows up in the team's own offense",
        "status": "MODELLING CHOICE - not taken from any official source. Flagged F4.",
    },
    "injury_impact_coef": {
        "value": 15.0,
        "unit": "net-rating points per 100 possessions lost if 100% of a team's minutes were unavailable",
        "status": "MODELLING CHOICE - not taken from any official source. Sensitivity band 10 / 15 / 20 is published. Flagged F4.",
    },
    "status_weight": {
        "value": {"Out": 1.00, "Doubtful": 0.70, "Questionable": 0.35,
                  "Probable": 0.10, "Available": 0.00, "NOT YET SUBMITTED": 0.00},
        "unit": "probability-ish weight applied to a player's minute share",
        "status": "MODELLING CHOICE - not taken from any official source. Flagged F4.",
    },
    "team_minutes_per_game": {
        "value": 240.0,
        "unit": "5 players x 48 minutes - used to turn a player's minutes into a share of team minutes",
        "status": "ARITHMETIC from the published 48-minute regulation game.",
    },
}


# --------------------------------------------------------------- rating tables

class RatingTable:
    """One NBA.com Teams-Advanced window, indexed by team abbreviation."""

    def __init__(self, block, source_id, window_id, label):
        self.source_id = source_id
        self.window_id = window_id
        self.label = label
        self.teams = {}
        for row in block:
            ab = ABBR[row["team"]]
            self.teams[ab] = dict(row)
            self.teams[ab]["abbr"] = ab
            self.teams[ab]["name"] = row["team"]
        n = len(self.teams)
        self.L_off = mean([t["ortg"] for t in self.teams.values()])
        self.L_def = mean([t["drtg"] for t in self.teams.values()])
        self.L = (self.L_off + self.L_def) / 2.0
        self.L_pace = mean([t["pace"] for t in self.teams.values()])
        self.n = n

    def rating(self, ab, shrink_k=None):
        """Return a shrunk rating dict. shrink_k=None or 0 -> raw published values."""
        t = self.teams[ab]
        gp = float(t["gp"])
        if not shrink_k:
            f = 1.0
        else:
            f = gp / (gp + float(shrink_k))
        return {
            "abbr": ab,
            "name": t["name"],
            "gp": t["gp"], "w": t["w"], "l": t["l"],
            "raw_ortg": t["ortg"], "raw_drtg": t["drtg"], "raw_netr": t["netr"],
            "raw_pace": t["pace"],
            "ortg": self.L + f * (t["ortg"] - self.L),
            "drtg": self.L + f * (t["drtg"] - self.L),
            "pace": self.L_pace + f * (t["pace"] - self.L_pace),
            "tov_pct": t["tov_pct"], "efg_pct": t["efg_pct"], "ts_pct": t["ts_pct"],
            "oreb_pct": t["oreb_pct"], "dreb_pct": t["dreb_pct"], "reb_pct": t["reb_pct"],
            "ast_pct": t["ast_pct"], "pie": t["pie"], "poss": t["poss"],
            "shrink_f": f,
        }

    def ppg(self, ab, shrink_k=None):
        """Points per game implied by ORTG and PACE (official inputs only)."""
        r = self.rating(ab, shrink_k)
        return r["ortg"] * r["pace"] / 100.0

    def opp_ppg(self, ab, shrink_k=None):
        r = self.rating(ab, shrink_k)
        return r["drtg"] * r["pace"] / 100.0


# --------------------------------------------------------------- line origination

def base_line(table, home, away, shrink_k=None):
    """The un-adjusted efficiency line. home/away are team abbreviations."""
    h = table.rating(home, shrink_k)
    a = table.rating(away, shrink_k)
    L = table.L
    poss = (h["pace"] + a["pace"]) / 2.0
    h100 = h["ortg"] + a["drtg"] - L
    a100 = a["ortg"] + h["drtg"] - L
    h_pts = h100 * poss / 100.0
    a_pts = a100 * poss / 100.0
    return {
        "poss": poss,
        "h100": h100, "a100": a100,
        "h_pts": h_pts, "a_pts": a_pts,
        "margin": h_pts - a_pts,
        "total": h_pts + a_pts,
        "home": home, "away": away,
        "home_shrink_f": h["shrink_f"], "away_shrink_f": a["shrink_f"],
    }


def apply_availability(line, loss_home=0.0, loss_away=0.0, alpha=None):
    """Apply net-rating-point losses (rest, injury) to a base line.

    loss_* are POSITIVE numbers = net-rating points per 100 possessions the
    team is weakened by. alpha = share of the loss that lands on the team's own
    offense; the remainder lands on its defense, so the total moves by
    -(1 - 2*alpha) * (loss_home + loss_away).
    """
    if alpha is None:
        alpha = ASSUMPTIONS["alpha_offense_share"]["value"]
    poss = line["poss"]
    scale = poss / 100.0
    margin = line["margin"] + (loss_away - loss_home) * scale
    total = line["total"] - (1.0 - 2.0 * alpha) * (loss_home + loss_away) * scale
    out = dict(line)
    out["margin"] = margin
    out["total"] = total
    out["loss_home"] = loss_home
    out["loss_away"] = loss_away
    out["margin_adj"] = (loss_away - loss_home) * scale
    out["total_adj"] = -(1.0 - 2.0 * alpha) * (loss_home + loss_away) * scale
    return out


def reference_line(table, home, away, flat_hca=2.0):
    """The REFERENCE line we bet against.

    Deliberately naive and public: raw published net rating (no shrinkage,
    no rest, no availability), a flat +2.0 home edge, and a total that is
    simply the two teams' published scoring averages added together (no
    defensive adjustment at all).

    Why a model stands in for the market: no sportsbook price is published by
    an NBA-operated source, so no official link can be attached to one. See
    Flagged for Review F3.
    """
    base = base_line(table, home, away, shrink_k=None)
    naive_total = table.ppg(home) + table.ppg(away)
    return {
        "poss": base["poss"],
        "h_pts": base["h_pts"] + flat_hca / 2.0,
        "a_pts": base["a_pts"] - flat_hca / 2.0,
        "margin": base["margin"] + flat_hca,
        "total": naive_total,
        "h100": base["h100"], "a100": base["a100"],
        "home": home, "away": away,
        "hca": flat_hca,
    }


def model_line(table, home, away, params, loss_home=0.0, loss_away=0.0,
               home_b2b=0, away_b2b=0, shrink_k=None):
    """Full originated line: efficiency + shrinkage + HCA + rest + availability."""
    base = base_line(table, home, away, shrink_k=shrink_k)
    rest_home = params.get("b2b_penalty", 0.0) * (1 if home_b2b else 0)
    rest_away = params.get("b2b_penalty", 0.0) * (1 if away_b2b else 0)
    line = apply_availability(base,
                              loss_home=loss_home + rest_home,
                              loss_away=loss_away + rest_away)
    line["margin"] += params.get("hca", 0.0)
    line["hca"] = params.get("hca", 0.0)
    line["rest_home"] = rest_home
    line["rest_away"] = rest_away
    return line


def price_game(margin, total, sigma_margin, sigma_total):
    """Turn a margin/total forecast into probabilities (normal model)."""
    z = margin / sigma_margin if sigma_margin else 0.0
    p_home = norm_cdf(z)
    p_cover = {}   # filled by the caller, which knows the reference number
    return {
        "p_home_win": p_home,
        "p_away_win": 1.0 - p_home,
        "p_home_cover": p_cover,
        "sigma_margin": sigma_margin,
        "sigma_total": sigma_total,
    }


def cover_probability(model_margin, ref_spread, sigma):
    """P(home margin covers ref_spread) where ref_spread is the home spread
    (negative means home favoured). Home covers when (margin - spread) > 0."""
    return 1.0 - norm_cdf((ref_spread - model_margin) / sigma) if sigma else 0.5


def total_probability(model_total, ref_total, sigma_total, side):
    """P(over) or P(under) for a reference total."""
    p_over = 1.0 - norm_cdf((ref_total - model_total) / sigma_total) if sigma_total else 0.5
    return p_over if side == "over" else 1.0 - p_over


# ------------------------------------------------------------------ game flow

def game_flow(model_line_out, sigma_margin, sigma_total):
    """Game-flow read-outs that follow from the published pace/efficiency data
    and the fitted spread of outcomes. Anything that would need play-by-play
    (possession-level runs, actual timeout patterns) is NOT produced."""
    mu = model_line_out["margin"]
    tot = model_line_out["total"]
    poss = model_line_out["poss"]
    p_blowout = (1 - norm_cdf((20 - abs(mu)) / sigma_margin)) + \
                norm_cdf((-20 - abs(mu)) / sigma_margin) if abs(mu) < 20 else \
                (norm_cdf((mu - 20) / sigma_margin) + (1 - norm_cdf((mu + 20) / sigma_margin)))
    p_close = norm_cdf((5 - mu) / sigma_margin) - norm_cdf((-5 - mu) / sigma_margin)
    # P(game tied at the end of regulation) ~= density of the margin near 0
    p_ot = (norm_cdf((0.5 - mu) / sigma_margin) - norm_cdf((-0.5 - mu) / sigma_margin))
    return {
        "possessions": rnd(poss, 1),
        "pace_vs_league": rnd(model_line_out.get("pace_delta"), 1),
        "expected_total": rnd(tot, 1),
        "expected_margin_home": rnd(mu, 1),
        "p_home_win": rnd(norm_cdf(mu / sigma_margin), 3),
        "p_margin_within_5": rnd(p_close, 3),
        "p_margin_20plus": rnd(p_blowout, 3),
        "p_overtime_approx": rnd(p_ot, 4),
        "note": "Derived from official pace/efficiency inputs plus the fitted outcome spread. "
                "No play-by-play or possession-level input was available, so no run/timeout "
                "or quarter-split metric is published.",
    }


# ------------------------------------------------------------- player projections

def project_player(player, table_team_pace, game_poss, opp, league,
                   teammate_lost_share=0.0, usage_boost_coef=0.35):
    """Project a player's counting stats for one game.

    Inputs are all official: the player's own per-game averages (S7), the
    team's published pace (S1/S2) and the opponent's published defensive
    rating and rebounding rate (S1/S2).

    The three multipliers are MODELLING CHOICES (flagged F4):
      poss_factor    = game possessions / team season pace
      def_factor     = 1 + (opp.DRTG - L) / L                [points, assists]
      reb_factor     = 1 - 0.5 * (opp.DREB% - L_DREB%) / L_DREB%
      usage_factor   = 1 + usage_boost_coef * teammate_lost_share
    """
    L = league["L"]
    L_dreb = league["L_dreb"]
    poss_factor = game_poss / table_team_pace if table_team_pace else 1.0
    def_factor = 1.0 + (opp["drtg"] - L) / L
    reb_factor = 1.0 - 0.5 * (opp["dreb_pct"] - L_dreb) / L_dreb
    usage_factor = 1.0 + usage_boost_coef * teammate_lost_share

    def proj(avg, f):
        return avg * f if avg is not None else None

    pts = proj(player["pts"], poss_factor * def_factor * usage_factor)
    reb = proj(player["reb"], poss_factor * reb_factor * usage_factor)
    ast = proj(player["ast"], poss_factor * def_factor * usage_factor)
    stl = proj(player["stl"], poss_factor)
    blk = proj(player["blk"], poss_factor)
    fg3m = proj(player["fg3m"], poss_factor * def_factor * usage_factor)
    tov = proj(player["tov"], poss_factor)
    return {
        "player": player["player"], "team": player["team"],
        "gp": player["gp"], "season_min": player["min"],
        "poss_factor": rnd(poss_factor, 4),
        "def_factor": rnd(def_factor, 4),
        "reb_factor": rnd(reb_factor, 4),
        "usage_factor": rnd(usage_factor, 4),
        "proj_pts": rnd(pts, 1), "proj_reb": rnd(reb, 1), "proj_ast": rnd(ast, 1),
        "proj_fg3m": rnd(fg3m, 1), "proj_stl": rnd(stl, 1), "proj_blk": rnd(blk, 1),
        "proj_tov": rnd(tov, 1),
        "proj_pts_reb_ast": rnd((pts or 0) + (reb or 0) + (ast or 0), 1)
        if pts is not None else None,
        "proj_pts_reb": rnd((pts or 0) + (reb or 0), 1) if pts is not None else None,
        "proj_pts_ast": rnd((pts or 0) + (ast or 0), 1) if pts is not None else None,
        "baseline_pts": player["pts"], "baseline_reb": player["reb"],
        "baseline_ast": player["ast"], "baseline_fg3m": player["fg3m"],
        "baseline_pts_reb_ast": rnd(player["pts"] + player["reb"] + player["ast"], 1),
        "delta_pts": rnd(pts - player["pts"], 1) if pts is not None else None,
        "delta_reb": rnd(reb - player["reb"], 1) if reb is not None else None,
        "delta_ast": rnd(ast - player["ast"], 1) if ast is not None else None,
        "delta_fg3m": rnd(fg3m - player["fg3m"], 1) if fg3m is not None else None,
        "delta_pts_reb_ast": rnd((pts + reb + ast) - (player["pts"] + player["reb"] + player["ast"]), 1)
        if pts is not None else None,
    }
