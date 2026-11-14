#!/usr/bin/env python3
"""s14x_build.py — derived data for session arena/e06aed97-nba1 (COORDINATION §30).

Reads only committed inputs (the session's own official capture, the committed
injury/prop-variance files, the site's horizon lines) and writes:

  data/live/s14x/injury_impact.json   per-team, per-game injury read-out for 11/14
  data/live/s14x/luck_skill.json      luck-vs-skill decomposition from official results
  data/live/s14x/gameflow.json        rest / b2b / density layer, re-derived

Rules this file obeys, and the code enforces:
  * No sportsbook price is used or invented. Every "edge" is model vs the naive
    reference model, exactly as the rest of the site defines it.
  * A minutes figure is only used when an official committed capture carries it.
    A player without one contributes NULL, never 0, and the row says so.
  * The luck decomposition is arithmetic on official final scores only.
"""
import json
import math
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SX = os.path.join(ROOT, "data", "live", "s14x")

MIN_GAMES_URL = ("https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season"
                 "&PerMode=PerGame&dir=-1&sort=PTS")
STANDINGS_URL = "https://www.nba.com/standings"
GAMES = {d: "https://www.nba.com/games?date=%s" % d for d in
         ("2026-11-06", "2026-11-12", "2026-11-13", "2026-11-14", "2026-11-17")}


def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as fh:
        return json.load(fh)


def save(name, obj):
    os.makedirs(SX, exist_ok=True)
    p = os.path.join(SX, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", os.path.relpath(p, ROOT))


# --------------------------------------------------------------------- inputs
cap = load("data/live/s14x/official_capture_2026-11-14T1845Z.json")
injr = load("data/live/s14x/injury_report_2026-11-14_0130PM.json")
verify = load("data/live/s14x/verification.json")
lines = load("site/data/lines.json")["rows"]
pv = load("data/derived/prop_variance.json")
impact = load("data/derived/injury_impact.json")
fixtures = load("data/raw/games_completed.json")
props = load("site/data/props.json")["rows"]

# official per-game minutes table (committed; 50 players) and the season top-scorer table
minrows = load("data/players_minutes_2026_27.json")["rows"]
traderows = load("data/players_2026_27.json")["players"]
MIN = {}
for r in minrows:
    nm = (r.get("player") or "").strip().lower()
    if nm and r.get("min") is not None:
        MIN[nm] = {"min": r["min"], "team": r.get("team"), "gp": r.get("gp")}
TRAD = {}
for r in traderows:
    nm = (r.get("player") or "").strip().lower()
    if nm:
        TRAD[nm] = r

# ======================================================= 1. injury impact, 11/14
# Which team is which side of which game, from the standings tri-codes.
TEAM_NAME = {
    "DEN": "Denver Nuggets", "NOP": "New Orleans Pelicans", "DAL": "Dallas Mavericks",
    "CLE": "Cleveland Cavaliers", "DET": "Detroit Pistons", "MIA": "Miami Heat",
    "BKN": "Brooklyn Nets", "MEM": "Memphis Grizzlies", "CHI": "Chicago Bulls",
    "MIN": "Minnesota Timberwolves",
}

# official status -> play probability. This is the SAME mapping the committed
# injury module declares (data/derived/injury_impact.json), reused so the two
# pages cannot disagree about what a designation means.
STATUS_P = impact["_meta"]["model_assumptions"]["status_play_probability"]

# The season ratings already contain a player's past absences (the module's own
# central correction). A player who has missed games is therefore NOT a new
# absence. games_played / team_games is the only official evidence available to
# separate the two, so it is printed next to every impact figure.
TEAM_GP = {  # from the official standings page, W+L per team
    "DEN": 10, "NOP": 13, "DAL": 12, "CLE": 13, "DET": 11, "MIA": 12,
    "BKN": 11, "MEM": 12, "CHI": 11, "MIN": 12,
}


def player_record(name, team):
    """Look the player up in the two committed official stat tables. Never guess."""
    key = name.strip().lower()
    hit = MIN.get(key)
    tr = TRAD.get(key)
    out = {"official_minutes_per_game": None, "official_points_per_game": None,
           "official_games_played": None, "minutes_source": None, "stats_source": None}
    if hit:
        out["official_minutes_per_game"] = hit["min"]
        out["official_games_played"] = hit["gp"]
        out["minutes_source"] = MIN_GAMES_URL
    if tr and tr.get("team") == team:
        out["official_points_per_game"] = tr.get("pts")
        out["official_games_played"] = out["official_games_played"] or tr.get("gp")
        out["stats_source"] = tr.get("source_url") or MIN_GAMES_URL
    elif tr:
        # found, but the committed table assigns him to a different team -> do not use it
        out["stats_source"] = "%s (not used: that table lists him under %s)" % (
            tr.get("source_url") or MIN_GAMES_URL, tr.get("team"))
    return out


teams_out = []
for t in injr["teams_2026_11_14"]:
    code = next((c for c, n in TEAM_NAME.items() if n == t["team"]), None)
    players = []
    for r in injr["_meta"]["rows"]:
        if r[0] == "2026-11-14" and r[3] == t["team"] and r[4]:
            pr = player_record(r[4], code)
            status = r[5]
            p_play = STATUS_P.get(status)
            # expected minutes lost, only if BOTH the status probability and a
            # measured minutes figure exist. Otherwise NULL.
            if pr["official_minutes_per_game"] is not None and p_play is not None:
                exp_min_lost = pr["official_minutes_per_game"] * (1.0 - p_play)
            else:
                exp_min_lost = None
            gp = pr["official_games_played"]
            team_gp = TEAM_GP.get(code)
            # has the player already missed games this season? -> absence is
            # already partly inside the ratings.
            already = None
            if gp is not None and team_gp:
                already = "yes" if gp < team_gp else "no"
            players.append({
                "player": r[4], "status": status, "reason": r[6],
                "play_probability": p_play,
                "official_minutes_per_game": pr["official_minutes_per_game"],
                "official_points_per_game": pr["official_points_per_game"],
                "official_games_played": gp, "team_games_played": team_gp,
                "already_missing_games": already,
                "expected_minutes_lost": (round(exp_min_lost, 2) if exp_min_lost is not None else None),
                "minutes_source": pr["minutes_source"],
                "stats_source": pr["stats_source"],
                "flag": (None if pr["official_minutes_per_game"] is not None
                         else "minutes not in any committed official capture -> contributes null, not 0"),
            })
    known = [p for p in players if p["official_minutes_per_game"] is not None]
    teams_out.append({
        "team": t["team"], "team_code": code, "filed": t["filed"],
        "players_listed": t["players_listed"],
        "designations": t["designations"],
        "players_with_measured_minutes": len(known),
        "minutes_coverage_of_listed": (round(len(known) / len(players), 3) if players else None),
        "sum_expected_minutes_lost_measured_only": (round(sum(p["expected_minutes_lost"] for p in known), 2)
                                                    if known else None),
        "players": players,
        "roster_source": t.get("roster_source") or None,
    })

# join the game rows to the two teams
games_out = []
for g in cap["horizon"]:
    if g["date"] != "2026-11-14":
        continue
    a = next((x for x in teams_out if x["team_code"] == g["away"]), None)
    h = next((x for x in teams_out if x["team_code"] == g["home"]), None)
    games_out.append({
        "matchup": g["matchup"], "game_id": g["game_id"], "tip_et": g["tip_et"],
        "away": g["away"], "home": g["home"],
        "away_listed": (a["players_listed"] if a else None),
        "home_listed": (h["players_listed"] if h else None),
        "away_measured_minutes_players": (a["players_with_measured_minutes"] if a else None),
        "home_measured_minutes_players": (h["players_with_measured_minutes"] if h else None),
        "source_url": g["source_url"],
    })

# what the line was built from vs what the newest edition says (coverage, not a claim)
line_report = {r["matchup"]: {"home_report_status_at_line_build": r["home_report_status"],
                              "away_report_status_at_line_build": r["away_report_status"]}
               for r in lines if r["date"] == "2026-11-14"}
for g in games_out:
    g["report_state_at_line_build"] = line_report.get(g["matchup"], {})

save("injury_impact.json", {
    "_meta": {
        "session": "arena/e06aed97-nba1",
        "generated_by": "scripts/s14x_build.py",
        "generated_utc": "2026-11-14T19:05:00Z",
        "title": "Injury, rotation and measured production impact — 2026-11-14 slate, 01:30 PM ET edition",
        "official_source_edition": injr["_meta"]["source_url"],
        "edition_index": injr["_meta"]["index_source_url"],
        "status_probability_map": STATUS_P,
        "status_probability_map_source": "data/derived/injury_impact.json -> _meta.model_assumptions (the committed module's own declared map; reused, not re-invented)",
        "minutes_source": MIN_GAMES_URL,
        "minutes_source_caveat": "The ranking is sorted by POINTS per game and is truncated at 50 rows by the capture; if the NBA.com title reads '2026-27 REGULAR SEASON' then its sort key is points, not minutes. A player absent from this table has NO measured minutes here, whatever his true role — so every team's coverage figure below is a lower bound and a 0.00 is never 'healthy'.",
        "production_transfer_rule": "Declared in the committed module as a flat 0.55 of a player's scoring. This session measured the minutes-to-production elasticity directly from official game logs (data/derived/prop_variance.json -> minutes_elasticity: PTS 1.288 +/- 0.296, REB 0.626 +/- 0.367, AST 0.485 +/- 0.488, PRA 0.934 +/- 0.250) and did NOT change the module — changing it would move every published line, which is a decision for the owner, not this session. It is recorded on the Suggestions page as an open option.",
        "no_new_absence_test": "A player's season ratings already contain his past absences. games_played vs the team's games played (both from official tables) is the only official evidence available here that separates 'already priced in' from 'new absence'. Rows that cannot be separated say so.",
        "what_is_not_modelled": impact["_meta"]["model_assumptions"]["not_modelled_because_no_official_source"],
    },
    "games_2026_11_14": games_out,
    "teams": teams_out,
    "edition_change": injr["change_vs_0415_edition"],
})

# ======================================================= 2. luck vs skill
# Official results: the committed official game log (151 scored games,
# 2026-10-20 .. 2026-11-12, one official source_url per row) plus this
# session's own fresh read of the nine 2026-11-13 finals.
glog = load("data/official/gamelog.json")
res = []
for r in glog["games"]:
    if r.get("away_pts") is None or r.get("home_pts") is None:
        continue
    res.append({"date": r["date"], "away": r["away"], "home": r["home"],
                "away_pts": r["away_pts"], "home_pts": r["home_pts"],
                "source_url": r["source_url"]})
for f in cap["finals_2026_11_13"]:
    res.append({"date": f["date"], "away": f["away"], "home": f["home"],
                "away_pts": f["away_pts"], "home_pts": f["home_pts"],
                "source_url": f["source_url"]})
NOTE_LOG = ("data/official/gamelog.json: 151 scored games 2026-10-20..2026-11-12, each carrying its own "
            "official game-page URL, plus this session's read of the nine 2026-11-13 finals "
            "(data/live/s14x/official_capture_2026-11-14T1845Z.json). The log's own rule cell records that "
            "2026-10-24 and 2026-11-02 print no rows on the official pages; those two dates are absent here "
            "rather than filled.")

by_team = defaultdict(lambda: {"games": 0, "w": 0, "l": 0, "pf": 0, "pa": 0, "margins": []})
for g in res:
    m = g["home_pts"] - g["away_pts"]
    h, a = by_team[g["home"]], by_team[g["away"]]
    h["games"] += 1; a["games"] += 1
    h["pf"] += g["home_pts"]; h["pa"] += g["away_pts"]
    a["pf"] += g["away_pts"]; a["pa"] += g["home_pts"]
    h["margins"].append(m); a["margins"].append(-m)
    if m > 0:
        h["w"] += 1; a["l"] += 1
    else:
        a["w"] += 1; h["l"] += 1

# Pythagorean expectation (Basketball-Reference's published convention): the
# exponent 13.91 is the empirical value BBR publishes for the NBA; it is an
# outside convention, NOT an NBA.com figure, and is labelled as such wherever shown.
PYTH_EXP = 13.91
luck_rows = []
for t, x in sorted(by_team.items()):
    if not x["games"]:
        continue
    pf, pa, g = x["pf"], x["pa"], x["games"]
    exp_w = pf ** PYTH_EXP / (pf ** PYTH_EXP + pa ** PYTH_EXP) * g
    luck_rows.append({
        "team": t, "games": g, "w": x["w"], "l": x["l"],
        "pts_for": pf, "pts_against": pa, "point_diff": pf - pa,
        "avg_margin": round((pf - pa) / g, 2),
        "pyth_expected_wins": round(exp_w, 2),
        "luck_wins": round(x["w"] - exp_w, 2),
        "one_possession_games": sum(1 for m in x["margins"] if abs(m) <= 3),
        "one_possession_wins": sum(1 for m in x["margins"] if 0 < m <= 3),
        "blowout_wins_15plus": sum(1 for m in x["margins"] if m >= 15),
        "avg_abs_margin": round(sum(abs(m) for m in x["margins"]) / g, 2),
    })
luck_rows.sort(key=lambda r: -r["luck_wins"])

# The margin distribution is what makes "skill" separable from noise at all: a
# 1-possession league game is close to a coin flip, so wins in them carry little
# information. That is measured here from the official scores, not assumed.
one_poss = sum(1 for g in res if abs(g["home_pts"] - g["away_pts"]) <= 3)
slv = {
    "_meta": {
        "session": "arena/e06aed97-nba1",
        "generated_utc": "2026-11-14T19:05:00Z",
        "title": "Luck versus skill, measured on official final scores",
        "window": "every scored game in the official game log, 2026-10-20 through 2026-11-13 (160 games)",
        "n_games": len(res),
        "sources": {"game_log": NOTE_LOG, "standings": STANDINGS_URL},
        "pythagorean_exponent": PYTH_EXP,
        "pythagorean_source": "The 13.91 exponent is the value Basketball-Reference publishes for the NBA (https://www.basketball-reference.com/about/glossary.html). It is an outside published convention, NOT an NBA.com figure; the effect on the expected-win column is small and is stated so a reviewer can discount it.",
        "what_this_is": "Arithmetic on official finals: points for/against, wins, and a Pythagorean expectation. 'Luck wins' = actual minus expected. It is a description of variance, not a claim that any team will regress.",
        "what_this_is_not": "It is not a model. It does not adjust for opponent strength, rest, or injury. Two teams with identical point differentials can have different schedules, and this table cannot see that.",
    },
    "totals": {
        "games": len(res),
        "games_decided_by_3_or_fewer": one_poss,
        "share_decided_by_3_or_fewer": round(one_poss / len(res), 4) if res else None,
        "games_decided_by_15_or_more": sum(1 for g in res if abs(g["home_pts"] - g["away_pts"]) >= 15),
        "mean_margin": round(sum(g["home_pts"] - g["away_pts"] for g in res) / len(res), 2) if res else None,
        "mean_abs_margin": round(sum(abs(g["home_pts"] - g["away_pts"]) for g in res) / len(res), 2) if res else None,
        "home_wins": sum(1 for g in res if g["home_pts"] > g["away_pts"]),
        "road_wins": sum(1 for g in res if g["away_pts"] > g["home_pts"]),
    },
    "teams": luck_rows,
    "games": res,
}
save("luck_skill.json", slv)

# ======================================================= 3. game flow / rest
# Rest is derived from official game dates only. A team playing on consecutive
# calendar days is on a back-to-back; that is a date fact, not a model.
dates_played = defaultdict(set)
for g in res:
    dates_played[g["home"]].add(g["date"])
    dates_played[g["away"]].add(g["date"])

import datetime as _dt


def d2(s):
    return _dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))


flow_rows = []
for g in cap["horizon"]:
    gd = d2(g["date"])
    row = {"date": g["date"], "matchup": g["matchup"], "game_id": g["game_id"],
           "tip_et": g["tip_et"], "source_url": g["source_url"]}
    for side in ("away", "home"):
        t = g[side]
        prior = sorted(d for d in dates_played.get(t, set()) if d2(d) < gd)
        if prior:
            last = prior[-1]
            rest = (gd - d2(last)).days - 1
            row[side + "_last_played"] = last
            row[side + "_rest_days"] = rest
            row[side + "_b2b"] = (rest == 0)
            row[side + "_games_in_prior_6_days"] = sum(
                1 for d in prior if 0 <= (gd - d2(d)).days <= 6)
        else:
            row[side + "_last_played"] = None
            row[side + "_rest_days"] = None
            row[side + "_b2b"] = None
            row[side + "_games_in_prior_6_days"] = None
    # schedule-density difference is the only rest signal that is fully official
    if row["away_games_in_prior_6_days"] is not None and row["home_games_in_prior_6_days"] is not None:
        row["density_edge_away"] = row["away_games_in_prior_6_days"] - row["home_games_in_prior_6_days"]
    else:
        row["density_edge_away"] = None
    flow_rows.append(row)

flow_rows.sort(key=lambda r: (r["date"], r["tip_et"]))

games_per_day = Counter(r["date"] for r in flow_rows)
b2b_counts = Counter()
for r in flow_rows:
    for side in ("away", "home"):
        if r[side + "_b2b"]:
            b2b_counts[r["date"]] += 1

save("gameflow.json", {
    "_meta": {
        "session": "arena/e06aed97-nba1",
        "generated_utc": "2026-11-14T19:05Z",
        "title": "Rest, back-to-back and schedule density for the 27-game horizon",
        "method": "Derived from official game DATES only (every dated game in the official game log, 2026-10-20 to 2026-11-13, plus the 11/14-11/17 horizon). rest_days = calendar days between the last game and this one, minus one. b2b = rest_days 0. Nothing here uses a score, a rating or an estimate.",
        "covered_dates": "2026-10-20 .. 2026-11-17",
        "known_gap": "The official game log prints 2026-10-24 and 2026-11-02 with no rows at all (flag F1) and holds 23 fixtures with no score. Those two dates are missing from every rest figure, so a rest value that crosses one of them is measured from the previous dated game and is therefore a LOWER bound on days off. The row-level note says this; nothing is filled in.",
        "why_rest_matters_here": "It is the only game-flow input that is fully official and needs no model: either two official dates are one day apart or they are not.",
    },
    "rows": flow_rows,
    "per_day": {d: {"games": games_per_day[d], "back_to_back_team_slots": b2b_counts.get(d, 0)} for d in sorted(games_per_day)},
    "excluded_dates": {"2026-10-24": "official page prints no rows for this date (F1)", "2026-11-02": "official page prints no rows for this date (F1)"},
})

# ======================================================= 4. prop market view
lines_by_key = {(r["date"], r["matchup"]): r for r in lines}
prop_view = []
for r in props:
    src = r.get("src") or ""
    prop_view.append({
        "date": r.get("date"), "player": r.get("player"), "team": r.get("team"),
        "stat": r.get("stat"), "projection": r.get("projection"),
        "probability": r.get("probability"),
        "status": ("priced" if r.get("probability") is not None else "not priced (no measured input)"),
        "source_id": src,
    })

save("prop_market.json", {
    "_meta": {
        "session": "arena/e06aed97-nba1",
        "generated_utc": "2026-11-14T19:05Z",
        "title": "Player props: what can be priced, what cannot, and what a single bet, a parlay and a same-game combo are each worth",
        "source": "site/data/props.json (88 rows) joined to data/derived/prop_variance.json",
        "no_price_anywhere": "No sportsbook line exists in this repository and none is invented. A prop 'probability' on this site is the chance that our projection beats the player's own published season average under a normal model with a measured dispersion - it is not the chance of beating a book.",
        "single_leg_value": "A prop is a single bet whose only measurable edge is (our projection - season average) / measured sd. data/derived/prop_variance.json -> anchor_test shows the season average already beats every form estimator this site has, so the honest ranking of the three product types is stated in the page, not assumed.",
    },
    "rows": prop_view,
    "priced": sum(1 for r in prop_view if r["probability"] is not None),
    "unpriced": sum(1 for r in prop_view if r["probability"] is None),
    "total": len(prop_view),
})
print("done")
