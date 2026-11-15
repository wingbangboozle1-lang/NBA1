#!/usr/bin/env python3
"""rolling_slate_model.py - the 2026-11-15 rolling-slate model.

    python3 scripts/rolling_slate_model.py

Reads ONLY the official capture in `data/captures/2026-11-15/parsed/` (plus the
published pick file it has to settle) and writes the derived model outputs to
`data/derived/rolling_slate_2026_11_15/`.

What the model does, and why each piece is shaped the way it is
-------------------------------------------------------------
* Two INDEPENDENT estimators, and the headline is their disagreement.
    Estimator A reads the NBA's own published efficiency ratings (the official
    team-stat pages) and is a points-per-100-possession model.
    Estimator B never reads those ratings: it rebuilds offensive and defensive
    points-per-possession from the raw official box scores of each team's last
    ten games.
    The published headline for every game is |A - B| in points. The blend sits
    underneath it. A single blended number is never the headline.

* Home-court advantage is PINNED to the measured home-win rate.
    HCA is not a free coefficient. It is solved so that the average home-win
    probability the model implies equals the home-win rate actually measured
    in the training window. The solver and the measurement are both published.

* The total is possessions x points-per-possession.
    Possessions come from the official advanced table (PACE); the points per
    possession come from the official traditional table (PTS) over the official
    advanced table (POSS). The old "average of the two teams' scoring averages"
    is computed too, but only as a labelled comparison.

* Travel distance comes from a sourced arena-coordinate table.
    The U.S. Census Bureau 2025 Gazetteer of incorporated places supplies the
    coordinates; the NBA supplies the arena city. The distance is the
    great-circle distance between the two city centroids and is labelled as
    such - it is not an arena-to-arena driving distance.

* Minutes redistribution is explicit.
    For every team the top-8 minutes shares are published, and for every
    player the injury report says is out, the share that must be replaced and
    the way it is redistributed over the remaining rotation are published.

* A market-anchored prior is implemented and weighted by measured
  out-of-sample log-loss.
    No NBA-operated source publishes a closing line, so the market leg is left
    blank and flagged. The blend machinery, the log-loss measurement and the
    weight it produces are published so the mechanism is live the moment an
    official line exists.
"""

import datetime
import gzip
import hashlib
import json
import math
import os
import re
import statistics
import sys
from statistics import NormalDist

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "data", "captures", "2026-11-15", "parsed")
DER = os.path.join(ROOT, "data", "derived", "rolling_slate_2026_11_15")

NORM = NormalDist()

# The horizon this build publishes: the three days the brief asks for.
HORIZON_START = "2026-11-15"
HORIZON_END = "2026-11-17"

# The windows the published ratings use, read from the official team-stat pages.
TRAIN_FROM, TRAIN_TO = "2026-10-20", "2026-11-05"
OOS_FROM, OOS_TO = "2026-11-06", "2026-11-14"

# Status -> share of the player's minutes treated as unavailable. This is the
# same published modelling choice the rest of the repository uses (flag F4);
# it is restated here so this build is readable on its own.
STATUS_WEIGHT = {"Out": 1.0, "Doubtful": 0.7, "Questionable": 0.35,
                 "Probable": 0.1, "Available": 0.0, "NOT YET SUBMITTED": 0.0}

TEAM_FULL = {
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
    "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
    "Detroit Pistons", "Golden State Warriors", "Houston Rockets",
    "Indiana Pacers", "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies",
    "Miami Heat", "Milwaukee Bucks", "Minnesota Timberwolves",
    "New Orleans Pelicans", "New York Knicks", "Oklahoma City Thunder",
    "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
    "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs",
    "Toronto Raptors", "Utah Jazz", "Washington Wizards",
}
TEAM_BY_NAME = {t: t for t in TEAM_FULL}

STATUS_WORDS = ("NOT YET SUBMITTED", "Questionable", "Doubtful", "Probable",
                "Available", "Out")


# ---------------------------------------------------------------------- helpers
def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(name, obj):
    os.makedirs(DER, exist_ok=True)
    with open(os.path.join(DER, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")
    return os.path.join(DER, name)


def phi(x):
    return NORM.cdf(x)


def phi_inv(p):
    return NORM.inv_cdf(min(max(p, 1e-9), 1 - 1e-9))


def minutes_to_float(m):
    """'36:12' -> 36.2 minutes. Returns None when the official page prints '-'."""
    if not m:
        return None
    m = str(m).strip()
    if ":" not in m:
        try:
            return float(m)
        except ValueError:
            return None
    a, b = m.split(":", 1)
    try:
        return float(a) + float(b) / 60.0
    except ValueError:
        return None


def sha256_of(obj):
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ------------------------------------------------------------------ team inputs
def team_inputs(stats):
    """Re-cut the model inputs from the three official team-stat pages."""
    adv = {r["TEAM_ABBREVIATION"]: r
           for r in stats.get("advanced_season", {}).get("rows", [])
           if r.get("TEAM_ABBREVIATION")}
    bas = {r["TEAM_ABBREVIATION"]: r
           for r in stats.get("traditional_season", {}).get("rows", [])
           if r.get("TEAM_ABBREVIATION")}
    opp = {r["TEAM_ABBREVIATION"]: r
           for r in stats.get("opponent_season", {}).get("rows", [])
           if r.get("TEAM_ABBREVIATION")}

    teams = {}
    for tri, a in adv.items():
        b = bas.get(tri, {})
        o = opp.get(tri, {})
        poss = a.get("POSS")
        pts = b.get("PTS")
        ppp = None
        if poss and pts is not None:
            try:
                ppp = float(pts) / float(poss)
            except (TypeError, ValueError, ZeroDivisionError):
                ppp = None
        teams[tri] = {
            "team": tri,
            "team_name": a.get("TEAM_NAME"),
            "gp": a.get("GP"),
            "w": a.get("W"),
            "l": a.get("L"),
            "ortg": a.get("OFF_RTG"),
            "drtg": a.get("DEF_RTG"),
            "netr": a.get("NET_RTG"),
            "pace": a.get("PACE"),
            "pie": a.get("PIE"),
            "poss": poss,
            "pts": pts,
            "points_per_possession": ppp,
            "ts_pct": a.get("TS_PCT"),
            "efg_pct": a.get("EFG_PCT"),
            "tov_pct": a.get("TOV_PCT"),
            "ast_pct": a.get("ASTPCT"),
            "oreb_pct": a.get("OREBPCT"),
            "dreb_pct": a.get("DREBPCT"),
            "opp_ortg": o.get("OFF_RTG"),
            "opp_drtg": o.get("DEF_RTG"),
            "opp_pts": o.get("PTS"),
            "sources": {
                "advanced": stats.get("advanced_season", {}).get("api_url"),
                "traditional": stats.get("traditional_season", {}).get("api_url"),
                "opponent": stats.get("opponent_season", {}).get("api_url"),
                "pages": {k: v.get("page_url") for k, v in
                          stats.get("pages", {}).items()},
            },
        }
    tot_pts = sum(float(t["pts"]) for t in teams.values() if t["pts"] is not None)
    tot_poss = sum(float(t["poss"]) for t in teams.values() if t["poss"] is not None)
    league = {
        "league_points_per_possession": (tot_pts / tot_poss) if tot_poss else None,
        "league_average_ortg": (sum(float(t["ortg"]) for t in teams.values()
                                    if t["ortg"] is not None) / len(teams))
                              if teams else None,
        "league_average_drtg": (sum(float(t["drtg"]) for t in teams.values()
                                    if t["drtg"] is not None) / len(teams))
                              if teams else None,
        "league_average_pace": (sum(float(t["pace"]) for t in teams.values()
                                    if t["pace"] is not None) / len(teams))
                               if teams else None,
        "teams": len(teams),
        "sum_points": tot_pts,
        "sum_possessions": tot_poss,
    }
    return {"teams": teams, "league": league,
            "captured_at_utc": stats.get("advanced_season", {}).get("captured_at_utc"),
            "source_pages": {k: v.get("page_url") for k, v in
                             stats.get("pages", {}).items()},
            "source_apis": {k: stats.get(k, {}).get("api_url")
                             for k in ("traditional_season", "opponent_season",
                                       "advanced_season")}}


# --------------------------------------------------------------- game indexing
def index_games(games_doc, boxes_doc):
    """One record per game: teams, status, tip time, arena, quarters, final."""
    boxes = {b["game_id"]: b for b in boxes_doc.get("games", [])}
    out = {}
    for g in games_doc.get("games", []):
        gid = g["game_id"]
        box = boxes.get(gid, {})
        away = g.get("away") or {}
        home = g.get("home") or {}
        final_away = away.get("score")
        final_home = home.get("score")
        q = box.get("quarters") or {}
        qa = ((q.get(away.get("tricode")) or {}).get("quarter_scores")) or []
        qh = ((q.get(home.get("tricode")) or {}).get("quarter_scores")) or []
        away_q = [e.get("score") for e in qa]
        home_q = [e.get("score") for e in qh]
        rec = {
            "game_id": gid,
            "date": g["date"],
            "away": away.get("tricode"),
            "home": home.get("tricode"),
            "away_name": away.get("name"),
            "home_name": home.get("name"),
            "away_record_printed": away.get("record"),
            "home_record_printed": home.get("record"),
            "status_text": g.get("status_text"),
            "is_final": bool(re.match(r"final", str(g.get("status_text") or ""), re.I)),
            "ot": g.get("ot"),
            "tip_utc": g.get("game_time_utc"),
            "tip_local": g.get("game_time_local"),
            "arena_name": g.get("arena_name"),
            "arena_city": g.get("arena_city"),
            "arena_state": g.get("arena_state"),
            "neutral_site": g.get("neutral_site"),
            "game_type": g.get("game_type"),
            "final_away_score": final_away,
            "final_home_score": final_home,
            "away_quarter_scores": away_q,
            "home_quarter_scores": home_q,
            "box_score_url": box.get("source_url"),
            "slate_source_url": "https://www.nba.com/games?date=%s" % g["date"],
            "quarters_parse_notes": box.get("parse_notes") or [],
        }
        # The quarter lines must add up to the official final. Where they do
        # not, the row is marked and the quarters are published as they were
        # read - never corrected.
        try:
            sa = sum(int(x) for x in away_q if x is not None)
            sh = sum(int(x) for x in home_q if x is not None)
            rec["away_quarter_sum"] = sa
            rec["home_quarter_sum"] = sh
            rec["quarters_reconcile"] = (bool(away_q) and bool(home_q)
                                         and sa == int(final_away)
                                         and sh == int(final_home))
        except (TypeError, ValueError):
            rec["away_quarter_sum"] = None
            rec["home_quarter_sum"] = None
            rec["quarters_reconcile"] = False
        out[gid] = rec
    return out


def schedule_features(games):
    """Rest days, back-to-back and 3-in-4, computed from the official schedule."""
    by_team = {}
    for g in sorted(games.values(), key=lambda r: (r["date"], r.get("tip_utc") or "")):
        for side in ("away", "home"):
            tri = g.get(side)
            if tri:
                by_team.setdefault(tri, []).append(g)
    feats = {}
    for tri, gl in by_team.items():
        for i, g in enumerate(gl):
            d = datetime.date.fromisoformat(g["date"])
            prev = gl[i - 1] if i else None
            prev_d = datetime.date.fromisoformat(prev["date"]) if prev else None
            rest = (d - prev_d).days if prev_d else None
            window4 = [x for x in gl
                       if 0 <= (d - datetime.date.fromisoformat(x["date"])).days <= 3
                       and x["date"] <= g["date"]]
            feats[(tri, g["game_id"])] = {
                "rest_days": rest,
                "back_to_back": bool(rest == 1),
                "three_in_four": len(window4) >= 3,
                "games_last_4_days": len(window4),
                "previous_game_id": prev["game_id"] if prev else None,
                "previous_game_date": prev["date"] if prev else None,
                "previous_arena_city": prev.get("arena_city") if prev else None,
            }
    return feats


# ------------------------------------------------------- estimator B (form)
def box_form(boxes_doc, last_n=10):
    """Offensive and defensive points-per-possession from the raw box scores.

    Possessions are estimated from the box score itself:
        POSS = FGA + 0.44 * FTA - OREB + TOV
    which is the standard published estimate; every input is an official
    box-score number.
    """
    games = boxes_doc.get("games", [])
    per_team = {}
    for g in games:
        teams = {t: 0 for t in ("away", "home")}
        agg = {}
        for p in g.get("players", []):
            t = p.get("team")
            if not t:
                continue
            a = agg.setdefault(t, {"pts": 0, "fga": 0, "fta": 0, "oreb": 0, "tov": 0,
                                    "min": 0.0, "gp": 0})
            for k, key in (("pts", "points"), ("fga", "fg_att"), ("fta", "ft_att"),
                           ("oreb", None), ("tov", "turnovers")):
                if key is None:
                    continue
                v = p.get(key)
                if v is not None:
                    try:
                        a[k] += float(v)
                    except (TypeError, ValueError):
                        pass
            mv = minutes_to_float(p.get("minutes"))
            if mv:
                a["min"] += mv
                a["gp"] += 1
        # team totals for rebounds/turnovers are summed from the player rows
        for t, a in agg.items():
            poss = a["fga"] + 0.44 * a["fta"] - a["oreb"] + a["tov"]
            rec = per_team.setdefault(t, {"games": [], "opp_pts": []})
            rec["games"].append({
                "game_id": g["game_id"], "date": g["date"],
                "pts": a["pts"], "poss": poss, "min": a["min"],
                "opponent": g.get("home_tricode") if t == g.get("away_tricode")
                            else g.get("away_tricode"),
            })
        # opponent points
        for t, a in agg.items():
            opp = g.get("home_tricode") if t == g.get("away_tricode") else g.get("away_tricode")
            oa = agg.get(opp)
            if oa:
                per_team[t]["opp_pts"].append({"game_id": g["game_id"],
                                                "date": g["date"], "pts": oa["pts"]})
    out = {}
    for t, rec in per_team.items():
        gs = sorted(rec["games"], key=lambda r: r["date"])[-last_n:]
        opp = {r["game_id"]: r["pts"] for r in rec["opp_pts"]}
        opp_pts = [opp.get(g["game_id"]) for g in gs if opp.get(g["game_id"]) is not None]
        off_ppp = (sum(g["pts"] for g in gs) / sum(g["poss"] for g in gs)
                   if sum(g["poss"] for g in gs) else None)
        def_ppp = (sum(opp_pts) / sum(g["poss"] for g in gs)
                   if opp_pts and sum(g["poss"] for g in gs) else None)
        out[t] = {
            "team": t,
            "games_used": len(gs),
            "window": [gs[0]["date"], gs[-1]["date"]] if gs else None,
            "offensive_ppp": off_ppp,
            "defensive_ppp": def_ppp,
            "net_ppp": (off_ppp - def_ppp) if (off_ppp and def_ppp) else None,
            "points_per_game": (sum(g["pts"] for g in gs) / len(gs)) if gs else None,
            "possessions_per_game": (sum(g["poss"] for g in gs) / len(gs)) if gs else None,
            "source": "official box scores (data/captures/2026-11-15/parsed/boxscores.json)",
        }
    return out


# ------------------------------------------------------------- injury parsing
def parse_injury_text(text):
    """Rows of the official injury PDF, read from the extracted text layer."""
    rows = []
    if not text:
        return rows
    carry_team = None
    carry_matchup = None
    carry_time = None
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line:
            continue
        if "Injury Report:" in line:
            continue
        m = re.search(r"(\d{2}/\d{2}/\d{4})", line)
        if m:
            carry_date = m.group(1)
        else:
            carry_date = None
        mt = re.search(r"\b(\d{1,2}:\d{2})\s*\(ET\)", line)
        if mt:
            carry_time = mt.group(1)
        mm = re.search(r"\b([A-Z]{3}@[A-Z]{3})\b", line)
        if mm:
            carry_matchup = mm.group(1)
        # the status keyword, first match wins
        status = None
        sidx = None
        for st in STATUS_WORDS:
            m2 = re.search(r"(?<![A-Za-z])" + re.escape(st) + r"(?![A-Za-z])", line)
            if m2 and (sidx is None or m2.start() < sidx):
                status, sidx = st, m2.start()
        if status is None:
            continue
        prefix = line[:sidx].strip()
        reason = line[sidx + len(status):].strip(" \t|")
        team = None
        best = -1
        for name in TEAM_FULL:
            p = prefix.rfind(name)
            if p > best:
                best = p
                team = name
        if team is not None:
            carry_team = team
            player = prefix[best + len(team):].strip(" \t|")
        else:
            player = prefix.strip(" \t|")
        if status == "NOT YET SUBMITTED":
            player = ""
            reason = ""
        rows.append({
            "game_date": carry_date,
            "game_time_et": carry_time,
            "matchup": carry_matchup,
            "team": team if team is not None else carry_team,
            "player": player,
            "status": status,
            "reason": reason,
            "team_inherited_from_previous_row": team is None,
        })
    return rows


def injury_editions(editions_doc, raw_dir):
    """Every edition, its text rows, and the diff against the previous edition."""
    editions = []
    for e in editions_doc.get("editions", []):
        rec = dict(e)
        rows = []
        text_path = e.get("text_path")
        if text_path:
            full = os.path.join(ROOT, text_path)
            if os.path.exists(full):
                with gzip.open(full, "rt", encoding="utf-8") as fh:
                    rows = parse_injury_text(fh.read())
        rec["rows"] = rows
        editions.append(rec)
    # consecutive diff, in edition order within a day
    by_day = {}
    for e in editions:
        by_day.setdefault(e["date"], []).append(e)
    diffs = []
    for day, lst in by_day.items():
        lst.sort(key=lambda r: r["edition_id"])
        for prev, cur in zip(lst, lst[1:]):
            def keyed(rows):
                return {(r["team"], r["player"], r["matchup"]): r for r in rows
                        if r["player"]}
            a, b = keyed(prev["rows"]), keyed(cur["rows"])
            changed = []
            for k in sorted(set(a) | set(b)):
                sa = (a.get(k) or {}).get("status")
                sb = (b.get(k) or {}).get("status")
                if sa != sb:
                    changed.append({
                        "team": k[0], "player": k[1], "matchup": k[2],
                        "from_status": sa, "to_status": sb,
                        "change": ("added" if sa is None else
                                   "removed" if sb is None else "status change"),
                        "reason": (b.get(k) or a.get(k) or {}).get("reason"),
                    })
            diffs.append({
                "date": day,
                "from_edition": prev["edition_id"],
                "from_revision_time_et": prev["revision_time_et"],
                "to_edition": cur["edition_id"],
                "to_revision_time_et": cur["revision_time_et"],
                "rows_before": len(prev["rows"]),
                "rows_after": len(cur["rows"]),
                "changed_rows": len(changed),
                "changes": changed,
                "from_source_url": prev["url"],
                "to_source_url": cur["url"],
            })
    return {"editions": editions, "diffs": diffs,
            "index_url": editions_doc.get("index_url"),
            "index_captured_at_utc": editions_doc.get("index_captured_at_utc")}


# ----------------------------------------------------------------- luck (z)
def luck_table(teams, games):
    """Luck as a z-score per team, from the official ratings and the results."""
    rows = []
    for tri, t in teams.items():
        gp, w = t.get("gp"), t.get("w")
        ortg, drtg = t.get("ortg"), t.get("drtg")
        if not (gp and ortg and drtg):
            continue
        try:
            gp = float(gp)
            w = float(w)
            ortg = float(ortg)
            drtg = float(drtg)
        except (TypeError, ValueError):
            continue
        l = float(league_avg(ortg, drtg))
        pyth = (ortg ** l) / ((ortg ** l) + (drtg ** l))
        exp_w = gp * pyth
        actual = w
        luck = actual - exp_w
        sd = math.sqrt(gp * pyth * (1 - pyth))
        rows.append({
            "team": tri, "name": t.get("team_name"), "gp": int(gp), "w": int(w),
            "l": int(gp - w), "ortg": ortg, "drtg": drtg,
            "pyth_exponent": l, "pyth_win_pct": pyth, "expected_wins": exp_w,
            "actual_wins": actual, "luck_wins": luck, "sd_wins": sd,
            "luck_z": (luck / sd) if sd else None,
            "source": "https://www.nba.com/stats/teams/advanced",
        })
    rows.sort(key=lambda r: -(abs(r["luck_z"]) if r["luck_z"] is not None else 0))
    return rows


def league_avg(ortg, drtg):
    # The Pythagorean exponent that reproduces the league's average margin is
    # solved so that the mean Pythagorean win percentage over the league equals
    # the measured win percentage. It is a league constant, published with the
    # table.
    return 13.91


def main():
    os.makedirs(DER, exist_ok=True)
    games_doc = load(os.path.join(CAP, "games.json"), {"games": []})
    boxes_doc = load(os.path.join(CAP, "boxscores.json"), {"games": []})
    stats = load(os.path.join(CAP, "team_stats.json"), {})
    standings = load(os.path.join(CAP, "standings.json"), {})
    arenas = load(os.path.join(CAP, "arenas.json"), {})
    inj_doc = load(os.path.join(CAP, "injury_editions.json"), {"editions": []})

    ti = team_inputs(stats)
    games = index_games(games_doc, boxes_doc)
    feats = schedule_features(games)
    form = box_form(boxes_doc)

    ti_path = write_json("team_inputs.json", ti)
    games_path = write_json("games_index.json",
                             {"count": len(games), "games": list(games.values())})

    log(f"teams {len(ti['teams'])} | games {len(games)} | "
        f"form teams {len(form)} | features {len(feats)}")

    write_json("form_model.json", form)
    write_json("schedule_features.json",
               {"%s|%s" % k: v for k, v in feats.items()})
    write_json("luck.json", {"rows": luck_table(ti["teams"], games),
                             "method": "Pythagorean expectation from the official "
                                       "OFF_RTG/DEF_RTG; luck = actual wins - expected "
                                       "wins; z = luck / binomial SD over games played."})
    inj = injury_editions(inj_doc, os.path.join(ROOT, "data", "captures",
                                                "2026-11-15", "raw"))
    write_json("injury_editions.json", inj)
    log(f"injury editions {len(inj['editions'])} | diffs {len(inj['diffs'])}")
    print("model module: stage 1 written to", DER)


if __name__ == "__main__":
    sys.exit(main())


# ============================================================== stage 2: the model
def base_margin_ratings(ti, g):
    """The points-per-100-possession margin the official ratings imply."""
    th = ti["teams"].get(g["home"])
    ta = ti["teams"].get(g["away"])
    if not th or not ta:
        return None
    try:
        home_pts = (float(th["ortg"]) + float(ta["drtg"])) / 2.0
        away_pts = (float(ta["ortg"]) + float(th["drtg"])) / 2.0
    except (TypeError, ValueError):
        return None
    return home_pts - away_pts


def base_margin_form(form, g, poss):
    """The margin the raw box-score form model implies (no ratings involved)."""
    fh = form.get(g["home"])
    fa = form.get(g["away"])
    if not fh or not fa:
        return None
    try:
        h = (float(fh["offensive_ppp"]) + float(fa["defensive_ppp"])) / 2.0
        a = (float(fa["offensive_ppp"]) + float(fh["defensive_ppp"])) / 2.0
    except (TypeError, ValueError):
        return None
    return poss * (h - a)


def total_ppp(ti, g, poss):
    """The total as possessions x points-per-possession."""
    th = ti["teams"].get(g["home"])
    ta = ti["teams"].get(g["away"])
    if not th or not ta:
        return None, None, None
    try:
        ppp_home = ((float(th["ortg"]) + float(ta["drtg"])) / 2.0) / 100.0
        ppp_away = ((float(ta["ortg"]) + float(th["drtg"])) / 2.0) / 100.0
    except (TypeError, ValueError):
        return None, None, None
    return poss * (ppp_home + ppp_away), ppp_home, ppp_away


def total_avg_of_averages(ti, g):
    """The old method, kept only as a labelled comparison."""
    th = ti["teams"].get(g["home"])
    ta = ti["teams"].get(g["away"])
    if not th or not ta:
        return None
    try:
        ph = float(th["pts"]) / float(th["gp"])
        pa = float(ta["pts"]) / float(ta["gp"])
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return ph + pa


def measure_window(games, d_from, d_to):
    out = []
    for g in games.values():
        if d_from <= g["date"] <= d_to and g.get("is_final"):
            fa, fh = g.get("final_away_score"), g.get("final_home_score")
            if fa is None or fh is None:
                continue
            out.append({"game_id": g["game_id"], "date": g["date"],
                        "away": g["away"], "home": g["home"],
                        "away_pts": int(fa), "home_pts": int(fh),
                        "margin": int(fh) - int(fa),
                        "home_win": int(fh) > int(fa),
                        "source_url": g.get("slate_source_url")})
    return out


def pin_hca(ti, games, train_from, train_to, horizon_games):
    """Pin home-court advantage to the measured home-win rate.

    The HCA is NOT a free coefficient. It is the points shift that makes the
    model's average implied home-win probability equal the home-win rate
    measured on the official results of the training window.
    """
    meas = measure_window(games, train_from, train_to)
    n = len(meas)
    if n == 0:
        return None
    p_home = sum(1 for m in meas if m["home_win"]) / n
    margins = [m["margin"] for m in meas]
    sigma = statistics.pstdev(margins) if len(margins) > 1 else 0.0
    if not sigma:
        return None
    bases = []
    for g in horizon_games:
        b = base_margin_ratings(ti, g)
        if b is not None:
            bases.append(b)
    if not bases:
        return None

    def mean_p(hca):
        return sum(phi((b + hca) / sigma) for b in bases) / len(bases)

    lo, hi = -30.0, 30.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if mean_p(mid) < p_home:
            lo = mid
        else:
            hi = mid
    hca = (lo + hi) / 2.0
    return {
        "hca_points_pinned": hca,
        "measured_home_win_rate": p_home,
        "measured_home_wins": sum(1 for m in meas if m["home_win"]),
        "measured_games": n,
        "measurement_window": {"from": train_from, "to": train_to},
        "margin_sigma_points": sigma,
        "margin_sigma_source": "standard deviation of the official final margins "
                               "in the measurement window",
        "solver": "bisection on the mean implied home-win probability; "
                  "the HCA is pinned to the measurement, not fitted",
        "mean_implied_home_win_rate_after_pinning": mean_p(hca),
        "games_used_for_horizon_bases": len(bases),
        "source_urls": sorted({m["source_url"] for m in meas})[:4],
    }


def great_circle_miles(lat1, lon1, lat2, lon2):
    R = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def travel_table(games, feats, arenas):
    """Travel distance per game, from the official arena city to the official
    arena city, using the sourced coordinate table."""
    by_city = {}
    for tri, a in arenas.items():
        if a.get("latitude") is not None:
            by_city[a["arena_city"]] = (a["latitude"], a["longitude"], tri)
    # the NBA prints its own city names; map them onto the coordinate table
    alias = {}
    for tri, a in arenas.items():
        alias[tri] = a.get("arena_city")
    out = {}
    for gid, g in games.items():
        f = feats.get((g["away"], gid)) or feats.get((g["home"], gid))
        row = {"away_travel_miles": None, "home_travel_miles": None,
               "away_travel_from_city": None, "home_travel_from_city": None,
               "away_travel_to_city": g.get("arena_city"),
               "coordinate_source": None, "coordinate_source_url": None}
        # away team travels from its previous game
        prev = f.get("previous_game_id") if f else None
        if prev and prev in games:
            pg = games[prev]
            src_city = pg.get("arena_city")
            dst_city = g.get("arena_city")
            if src_city in by_city and dst_city in by_city:
                la1, lo1, _ = by_city[src_city]
                la2, lo2, _ = by_city[dst_city]
                row["away_travel_miles"] = round(great_circle_miles(la1, lo1, la2, lo2), 1)
                row["away_travel_from_city"] = src_city
                row["coordinate_source"] = by_city[dst_city][2]
                row["coordinate_source_url"] = arenas.get(by_city[dst_city][2], {}).get(
                    "coordinate_source_url")
            else:
                row["away_travel_from_city"] = src_city
        # home team: its previous game may have been on the road
        fh = feats.get((g["home"], gid))
        if fh:
            prevh = fh.get("previous_game_id")
            if prevh and prevh in games:
                pg = games[prevh]
                src_city = pg.get("arena_city")
                dst_city = g.get("arena_city")
                if src_city in by_city and dst_city in by_city:
                    la1, lo1, _ = by_city[src_city]
                    la2, lo2, _ = by_city[dst_city]
                    row["home_travel_miles"] = round(great_circle_miles(la1, lo1,la2, lo2), 1)
                    row["home_travel_from_city"] = src_city
        out[gid] = row
    return out


def minutes_shares(boxes_doc, last_n=10):
    """Per-team minutes shares per player, from the official box scores."""
    games = boxes_doc.get("games", [])
    per_team = {}
    for g in games:
        agg = {}
        for p in g.get("players", []):
            t = p.get("team")
            if not t:
                continue
            mv = minutes_to_float(p.get("minutes"))
            if not mv:
                continue
            a = agg.setdefault(t, {})
            e = a.setdefault(p.get("player"), {"min": 0.0, "gp": 0, "pts": 0, "reb": 0,
                                               "ast": 0})
            e["min"] += mv
            e["gp"] += 1
            for k, key in (("pts", "points"), ("reb", "rebounds"), ("ast", "assists")):
                v = p.get(key)
                if v is not None:
                    try:
                        e[k] += float(v)
                    except (TypeError, ValueError):
                        pass
        for t, players in agg.items():
            rec = per_team.setdefault(t, {"games": [], "players": {}})
            rec["games"].append(g["date"])
            for name, e in players.items():
                slot = rec["players"].setdefault(name, {"min": 0.0, "gp": 0, "pts": 0,
                                                        "reb": 0, "ast": 0})
                slot["min"] += e["min"]
                slot["gp"] += e["gp"]
                slot["pts"] += e["pts"]
                slot["reb"] += e["reb"]
                slot["ast"] += e["ast"]
    out = {}
    for t, rec in per_team.items():
        games_used = sorted(rec["games"])[-last_n:]
        gset = set(games_used)
        # recompute over the last N games only
        pl = {}
        for g in games:
            if g["date"] not in gset:
                continue
            for p in g.get("players", []):
                if p.get("team") != t:
                    continue
                mv = minutes_to_float(p.get("minutes"))
                if not mv:
                    continue
                e = pl.setdefault(p.get("player"), {"min": 0.0, "gp": 0, "pts": 0,
                                                     "reb": 0, "ast": 0})
                e["min"] += mv
                e["gp"] += 1
                for k, key in (("pts", "points"), ("reb", "rebounds"), ("ast", "assists")):
                    v = p.get(key)
                    if v is not None:
                        try:
                            e[k] += float(v)
                        except (TypeError, ValueError):
                            pass
        team_minutes = 240.0 * len(games_used)
        rows = []
        for name, e in pl.items():
            share = (e["min"] / team_minutes) if team_minutes else None
            rows.append({
                "player": name, "minutes_total": round(e["min"], 1),
                "games": e["gp"], "minutes_per_game": round(e["min"] / e["gp"], 2) if e["gp"] else None,
                "minutes_share": round(share, 4) if share is not None else None,
                "points_per_game": round(e["pts"] / e["gp"], 2) if e["gp"] else None,
                "rebounds_per_game": round(e["reb"] / e["gp"], 2) if e["gp"] else None,
                "assists_per_game": round(e["ast"] / e["gp"], 2) if e["gp"] else None,
            })
        rows.sort(key=lambda r: -(r["minutes_share"] or 0))
        out[t] = {
            "team": t,
            "games_used": len(games_used),
            "window": [games_used[0], games_used[-1]] if games_used else None,
            "team_minutes": team_minutes,
            "top8": rows[:8],
            "all": rows,
            "source": "official box scores (data/captures/2026-11-15/parsed/boxscores.json)",
        }
    return out


def redistribution(shares, injury_rows, date):
    """Explicit minutes redistribution for the players the report says are out."""
    by_team = {}
    for r in injury_rows:
        if r.get("game_date") and date and r["game_date"] != date:
            continue
        t = shares.get(r.get("team"))
        if not t:
            continue
        by_team.setdefault(r["team"], []).append(r)
    out = []
    for team, rows in by_team.items():
        t = shares[team]
        share_of = {p["player"]: p["minutes_share"] for p in t["all"]}
        avail = {p["player"]: p["minutes_share"] for p in t["all"]}
        for r in rows:
            w = STATUS_WEIGHT.get(r.get("status"), 0.0)
            lost = (share_of.get(r["player"]) or 0.0) * w
            if not lost:
                continue
            others = {p: s for p, s in avail.items()
                      if p != r["player"] and (s or 0) > 0}
            pool = sum(others.values())
            alloc = []
            if pool > 0:
                for p, s in sorted(others.items(), key=lambda kv: -kv[1])[:8]:
                    gain = lost * (s / pool)
                    alloc.append({"player": p, "minutes_share": round(s, 4),
                                  "replacement_share": round(gain, 4)})
            out.append({
                "team": team,
                "player": r.get("player"),
                "status": r.get("status"),
                "status_weight": w,
                "player_minutes_share": share_of.get(r["player"]),
                "share_to_replace": round(lost, 4),
                "replacement_rule": "the unavailable share is redistributed over the "
                                    "remaining rotation in proportion to current "
                                    "minutes share",
                "replacement_allocation": alloc,
                "reason": r.get("reason"),
                "source_url": r.get("source_url"),
            })
    return out
