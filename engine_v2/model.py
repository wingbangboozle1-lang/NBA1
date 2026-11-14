"""Rating engine: originates NBA lines from official final scores only.

Everything here is derived from one input: the 151 official final scores in
data/official/gamelog.json.  No possessions, no play-by-play, no odds feed is
used, because none of those is available from an official source in this
environment (see the Flagged for Review page).

Two separable models, both standard and both fully auditable:

  MARGIN  - Simple Rating System (SRS): a team rating plus a home-court term,
            solved by iteration with shrinkage toward zero.  Drives the spread
            and the moneyline.

  TOTAL   - Opponent-adjusted offensive / defensive points ratings, solved by
            iteration with shrinkage toward the league mean.  Drives the total.

Prediction = rating difference + home term.  Residual standard deviations used
to turn a point prediction into a probability are measured OUT OF SAMPLE by the
walk-forward in pipeline.py - never in sample.
"""
from __future__ import annotations

from .common import TEAMS, mean

# Shrinkage constants.  Chosen BEFORE any out-of-sample run and applied to every
# window identically, so no test data was used to select them.
K_MARGIN = 4.0    # pseudo-games of "0 rating" added to each team's margin record
K_TOTAL = 6.0     # pseudo-games of "league average" added to each team's scoring record
ITERS = 60        # rating iteration count (converged well before this)


class Ratings:
    """Ratings fitted on a set of completed games."""

    def __init__(self, games, k_margin=K_MARGIN, k_total=K_TOTAL):
        self.games = list(games)
        self.k_margin = k_margin
        self.k_total = k_total
        self.gp = {t: 0 for t in TEAMS}
        self._margin_fit()
        self._total_fit()

    # ---------------------------------------------------------------- margin
    def _margin_fit(self):
        g = self.games
        self.n_games = len(g)
        S = {t: 0.0 for t in TEAMS}      # sum of point differentials
        N = {t: 0 for t in TEAMS}
        opp = {t: [] for t in TEAMS}
        for gm in g:
            m = gm["home_pts"] - gm["away_pts"]
            S[gm["home"]] += m
            S[gm["away"]] -= m
            N[gm["home"]] += 1
            N[gm["away"]] += 1
            opp[gm["home"]].append(gm["away"])
            opp[gm["away"]].append(gm["home"])
        self.gp = dict(N)
        hca = 0.0
        R = {t: 0.0 for t in TEAMS}
        for _ in range(ITERS):
            # home-court: mean home margin not explained by the ratings
            num = den = 0.0
            for gm in g:
                if gm.get("neutral"):
                    continue
                num += (gm["home_pts"] - gm["away_pts"]) - (R[gm["home"]] - R[gm["away"]])
                den += 1
            hca = (num / den) if den else 0.0
            new = {}
            for t in TEAMS:
                if N[t] == 0:
                    new[t] = 0.0
                    continue
                sos = sum(R[o] for o in opp[t]) / len(opp[t])
                new[t] = (S[t] + len(opp[t]) * sos) / (N[t] + self.k_margin)
            R = new
        self.hca = hca
        self.rating = R
        # keep the rating scale honest: recentre on zero
        c = mean([R[t] for t in TEAMS])
        self.rating = {t: R[t] - c for t in TEAMS}

    # ----------------------------------------------------------------- total
    def _total_fit(self):
        g = self.games
        pts = {t: [] for t in TEAMS}
        allowed = {t: [] for t in TEAMS}
        opp = {t: [] for t in TEAMS}
        for gm in g:
            pts[gm["home"]].append(gm["home_pts"])
            pts[gm["away"]].append(gm["away_pts"])
            allowed[gm["home"]].append(gm["away_pts"])
            allowed[gm["away"]].append(gm["home_pts"])
            opp[gm["home"]].append(gm["away"])
            opp[gm["away"]].append(gm["home"])
        allpts = [x for t in TEAMS for x in pts[t]]
        L = mean(allpts) if allpts else 0.0
        self.league_pts = L
        # shrinkage of the raw per-game averages toward the league mean
        a0, b0 = {}, {}
        for t in TEAMS:
            n = len(pts[t])
            a0[t] = ((n * mean(pts[t]) if n else 0) + self.k_total * L) / (n + self.k_total) if n else L
            b0[t] = ((n * mean(allowed[t]) if n else 0) + self.k_total * L) / (n + self.k_total) if n else L
        off, deff = dict(a0), dict(b0)
        for _ in range(ITERS):
            no, nd = {}, {}
            for t in TEAMS:
                if not opp[t]:
                    no[t], nd[t] = L, L
                    continue
                no[t] = a0[t] - mean([deff[o] for o in opp[t]]) + L
                nd[t] = b0[t] - mean([off[o] for o in opp[t]]) + L
            off, deff = no, nd
        self.off = off
        self.def_ = deff
        # home scoring edge (half of the home-court margin, by construction)
        num = den = 0.0
        for gm in g:
            if gm.get("neutral"):
                continue
            num += (gm["home_pts"] - gm["away_pts"])
            den += 1
        self.home_pts_edge = ((num / den) / 2.0) if den else 0.0

    # ------------------------------------------------------------ prediction
    def predict(self, home, away, neutral=0):
        hc = 0.0 if neutral else self.hca
        margin = self.rating[home] - self.rating[away] + hc
        he = 0.0 if neutral else self.home_pts_edge
        ph = self.off[home] + self.def_[away] - self.league_pts + he
        pa = self.off[away] + self.def_[home] - self.league_pts - he
        return {
            "pred_margin_home": margin,
            "pred_total": ph + pa,
            "pred_home_pts": ph,
            "pred_away_pts": pa,
            "home_gp": self.gp[home],
            "away_gp": self.gp[away],
            "rating_home": self.rating[home],
            "rating_away": self.rating[away],
            "hca": hc,
        }
