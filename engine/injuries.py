"""Availability: official NBA injury report -> rotation impact.

Design rule for this project: the impact number is a deliberate LOWER BOUND.
A player's minutes are only known if the player appears in the captured
official players table (page 1 = top 50 scorers, source S7). Anybody else is
counted with unknown minutes, i.e. zero impact, and the row says so. The
project never substitutes a guessed minutes number.
"""

import re

from common import ABBR, TEAM_NAME, rnd
from model_core import ASSUMPTIONS

STATUS_WEIGHT = ASSUMPTIONS["status_weight"]["value"]
TEAM_MINUTES = ASSUMPTIONS["team_minutes_per_game"]["value"]
IMPACT_COEF = ASSUMPTIONS["injury_impact_coef"]["value"]
SENSITIVITY = (10.0, 15.0, 20.0)


def _norm(name):
    """Normalise 'Banchero, Paolo' and 'Paolo Banchero' to the same key."""
    if not name:
        return ""
    toks = re.findall(r"[a-z0-9']+", name.lower())
    return " ".join(sorted(toks))


class Availability:
    def __init__(self, injury_rows, player_rows):
        self.rows = injury_rows
        self.players_by_key = {}
        for p in player_rows:
            self.players_by_key[_norm(p["player"])] = p
        # how much of each team's rotation the captured minutes table actually covers
        self.coverage = {}
        for p in player_rows:
            self.coverage[p["team"]] = self.coverage.get(p["team"], 0.0) + p["min"] / TEAM_MINUTES
        self.by_game = {}      # (date, matchup) -> {team: entries}
        self.by_team_game = {}  # (date, team_abbr) -> dict
        self._group()

    def _group(self):
        for r in self.rows:
            key = (r["game_date"], r["matchup"])
            ab = ABBR.get(r["team"])
            self.by_game.setdefault(key, {}).setdefault(ab, [])
            self.by_game[key][ab].append(r)
            self.by_team_game.setdefault((r["game_date"], ab), []).extend(
                [dict(x, matchup=r["matchup"]) for x in [r]])

    def team_report(self, date, team):
        """Return the availability read-out for one team on one date."""
        entries = self.by_team_game.get((date, team), [])
        listed = [e for e in entries if e["status"] != "NOT YET SUBMITTED" and e["player"]]
        not_submitted = any(e["status"] == "NOT YET SUBMITTED" for e in entries)
        weighted = 0.0
        known_share = 0.0
        unknown_players = []
        gleague_weighted = 0.0
        out_weighted = 0.0
        detail = []
        for e in listed:
            p = self.players_by_key.get(_norm(e["player"]))
            w = STATUS_WEIGHT.get(e["status"], 0.0)
            if p is None:
                unknown_players.append(e["player"])
                share = None
                contrib = 0.0
            else:
                share = p["min"] / TEAM_MINUTES
                known_share += share
                contrib = w * share
                weighted += contrib
                if e["reason"].startswith("G League"):
                    gleague_weighted += contrib
                if e["status"] in ("Out", "Doubtful"):
                    out_weighted += contrib
            detail.append({
                "player": e["player"],
                "status": e["status"],
                "reason": e["reason"],
                "status_weight": w,
                "minutes_known": p is not None,
                "season_min": p["min"] if p else None,
                "minutes_share": rnd(share, 4) if share is not None else None,
                "weighted_share": rnd(contrib, 4),
            })
        cov = self.coverage.get(team, 0.0)
        known = len(listed) - len(unknown_players)
        if not listed:
            conf = "NONE - no entry in this edition of the report"
        elif known == len(listed) and cov >= 0.5:
            conf = "HIGH"
        elif known == 0:
            conf = "NONE - minutes unavailable for every listed player"
        elif cov < 0.5 or known < len(listed):
            conf = "LOW - minutes coverage of this roster is " + f"{cov:.0%}"
        else:
            conf = "MEDIUM"
        return {
            "date": date,
            "team": team,
            "matchup": entries[0]["matchup"] if entries else None,
            "listed": len(listed),
            "listed_with_known_minutes": known,
            "minutes_coverage": rnd(cov, 3),
            "confidence": conf,
            "not_submitted": not_submitted,
            "no_entry_in_report": len(entries) == 0,
            "weighted_lost_share": rnd(weighted, 4),
            "weighted_lost_share_out_doubtful": rnd(out_weighted, 4),
            "weighted_lost_share_gleague": rnd(gleague_weighted, 4),
            "known_minutes_share": rnd(known_share, 4),
            "unknown_minutes_players": unknown_players,
            "impact_net_rating": rnd(IMPACT_COEF * weighted, 2),
            "impact_sensitivity": {str(int(c)): rnd(c * weighted, 2) for c in SENSITIVITY},
            "impact_note": (
                "Lower bound: " + str(len(unknown_players)) +
                " listed player(s) are outside the captured official top-50 minutes "
                "table (S7) and contribute 0.00 here. G-League designations are "
                "included at full weight, which overstates impact."
            ),
            "detail": detail,
        }

    def game_loss(self, date, matchup):
        """(loss_home, loss_away) in net-rating points, plus both team reports."""
        teams = self.by_game.get((date, matchup), {})
        # matchup string is AWAY@HOME
        away, home = matchup.split("@")
        rep_home = self.team_report(date, home)
        rep_away = self.team_report(date, away)
        return rep_home["impact_net_rating"] or 0.0, rep_away["impact_net_rating"] or 0.0, rep_home, rep_away

    def teammate_lost_share(self, date, team, exclude_player):
        """Minutes share unavailable on a team, excluding the player being
        projected (used as a usage boost for the survivors). Lower bound."""
        rep = self.team_report(date, team)
        excl = self.players_by_key.get(_norm(exclude_player))
        total = rep["weighted_lost_share"] or 0.0
        if excl is not None:
            for d in rep["detail"]:
                if _norm(d["player"]) == _norm(exclude_player):
                    total -= (d["weighted_share"] or 0.0)
        return max(0.0, total)
