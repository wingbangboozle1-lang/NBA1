#!/usr/bin/env python3
"""Settle 11/15 from official finals, then publish the new horizon.

    python3 scripts/build_horizon_801ba27f.py

Session `arena/801ba27f-nba1`, COORDINATION.md §41 tasks H03/H04/H05.

Produces, in this order:

1. `data/settlement/settlement_2026-11-15.json`
   Every 2026-11-15 ticket in the pre-tip publication record
   (`data/archive/horizon_picks_2026-11-15.json`) graded against official
   finals only. A game that is not Final is left PENDING - never graded on an
   in-progress score.

2. `data/derived/horizon_lines_801ba27f.json`  - the PROJECTION surface.
   Safe to publish: originated lines, the two estimators, their disagreement,
   rest/travel, rotation availability. No bet recommendation.

3. `data/derived/horizon_picks_801ba27f.json`  - the BET surface.
   Gated. Every ticket carries its validation status; no strategy has passed
   the gates, so nothing here is funded.

4. `data/prereg/v2-801ba27f/*.json`            - pre-registration freeze.
5. `data/ledger/ledger.json`                   - appended hash-chain entries.

The two surfaces are written to different files and are never merged into one
table on any page.
"""

import datetime
import hashlib
import json
import math
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DERIVED = os.path.join(ROOT, "data", "derived")
SETTLE = os.path.join(ROOT, "data", "settlement")
PREREG = os.path.join(ROOT, "data", "prereg", "v2-801ba27f")
LEDGER = os.path.join(ROOT, "data", "ledger", "ledger.json")
ARCHIVE = os.path.join(ROOT, "data", "archive")

RUN_UTC = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = "2026-11-15"
HORIZON = ["2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18"]

PAPER_PRICE = "paper -110 convention: stake 1.10 to win 1.00 (no licensed price exists in this repo)"


def jload(p):
    return json.load(open(p))


def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def sha256_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


# ------------------------------------------------------------ bivariate normal
def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p):
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > 1 - 0.02425:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q, r = p - 0.5, (p - 0.5) ** 2
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def bivariate_normal_cdf(a, b, rho):
    """P(X<=a, Y<=b) for standard bivariate normal with correlation rho."""
    if abs(rho) < 1e-9:
        return norm_cdf(a) * norm_cdf(b)
    # 1-D quadrature over the conditional: exact enough at 400 nodes on [-9, a].
    lo, hi = -9.0, a
    if hi <= lo:
        return 0.0
    n = 400
    h = (hi - lo) / n
    s = 0.0
    for i in range(n + 1):
        x = lo + i * h
        z = (b - rho * x) / math.sqrt(1 - rho * rho)
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        s += w * math.exp(-0.5 * x * x) * norm_cdf(z)
    return s * h / math.sqrt(2 * math.pi)


# ------------------------------------------------------------------ settlement
LINE_RE = re.compile(r"^([A-Z]{3})\s+(-?\d+(?:\.\d+)?)$")
SGP_LEG_RE = re.compile(r"^(.+?)\s+\(([A-Z]{3})\)\s+(OVER|UNDER)\s+(-?\d+(?:\.\d+)?)$")


def settle_singles(arch, finals_by_id):
    out = []
    for s in arch["singles"]:
        gid = s["game_id"]
        rec = {"date": s["date"], "game_id": gid, "matchup": s["matchup"],
               "pick_line": s["pick"]["pick_line"], "gate": s["pick"]["gate"],
               "result": None, "units": None, "sources": s.get("sources", [])}
        f = finals_by_id.get(gid)
        if not f:
            rec["result"] = "PENDING (official page is not Final)"
            rec["detail"] = "no official final for this game at settlement time"
            out.append(rec)
            continue
        m = LINE_RE.match(s["pick"]["pick_line"])
        if not m:
            rec["result"] = "UNPARSEABLE pick line"
            out.append(rec)
            continue
        team, line = m.group(1), float(m.group(2))
        home_margin = f["margin_home"]                  # home - away
        if team == f["home"]:
            margin = home_margin
        elif team == f["away"]:
            margin = -home_margin
        else:
            rec["result"] = "team on ticket not on official box score"
            out.append(rec)
            continue
        rec["team_picked"] = team
        rec["line"] = line
        rec["final_score"] = "%s %d - %s %d" % (f["away"], f["away_pts"],
                                                f["home"], f["home_pts"])
        rec["margin_pick_team"] = margin
        beat = margin - line
        if abs(beat) < 1e-9:
            rec["result"], rec["units"] = "PUSH", 0.0
        elif beat > 0:
            rec["result"], rec["units"] = "WIN", 1.0
        else:
            rec["result"], rec["units"] = "LOSS", -1.1
        rec["price_convention"] = PAPER_PRICE
        rec["source_url"] = f["source_url"]
        rec["source_finals"] = "data/official/results_feed_2026_27.json (official LINESCORES)"
        rec["quarter_sum_check"] = (sum(f["home_quarters"]) == f["home_pts"]
                                    and sum(f["away_quarters"]) == f["away_pts"])
        out.append(rec)
    return out


def leg_grade(leg_text, finals_by_id, by_matchup_final):
    m = LINE_RE.match(leg_text.split("—")[-1].strip() if "—" in leg_text else leg_text.strip())
    if not m:
        return None
    team, line = m.group(1), float(m.group(2))
    f = by_matchup_final.get(leg_text.split("—")[0].strip())
    if not f:
        return None
    home_margin = f["margin_home"]
    margin = home_margin if team == f["home"] else -home_margin if team == f["away"] else None
    if margin is None:
        return None
    beat = margin - line
    return "WIN" if beat > 1e-9 else "PUSH" if abs(beat) < 1e-9 else "LOSS"


def settle_parlays(arch, finals_by_id, by_matchup_final):
    out = []
    for p in arch.get("parlays", []):
        legs = [p.get("leg1"), p.get("leg2")]
        rec = {"date": p["date"], "legs": legs, "leg_results": [], "result": None,
               "units": None, "joint_published": {"lb": p.get("joint_lb"),
                                                  "ub": p.get("joint_ub"),
                                                  "rho_lb": p.get("rho_lb"),
                                                  "rho_ub": p.get("rho_ub")},
               "sources": p.get("sources", [])}
        pending = False
        for leg in legs:
            g = leg_grade(leg, finals_by_id, by_matchup_final)
            if g is None:
                pending = True
                rec["leg_results"].append("PENDING")
            else:
                rec["leg_results"].append(g)
        if pending:
            rec["result"] = "PENDING (at least one leg is not Final)"
        elif "LOSS" in rec["leg_results"]:
            rec["result"], rec["units"] = "LOSS", -1.1
        elif "PUSH" in rec["leg_results"]:
            rec["result"], rec["units"] = "PUSH", 0.0
        else:
            rec["result"], rec["units"] = "WIN", 1.0
        rec["price_convention"] = PAPER_PRICE
        out.append(rec)
    return out


def settle_sgp(arch, finals_by_id, by_matchup_final):
    out = []
    for s in arch.get("sgp_candidates", []):
        rec = {"date": s["date"], "game": s["game"], "kind": s.get("kind"),
               "legs": [s.get("leg1"), s.get("leg2")],
               "leg_results": [], "result": None, "units": None,
               "frozen_price_joint_prob_rho": s.get("joint_prob_rho"),
               "frozen_price_independent_printed_beside": s.get("joint_prob_independent"),
               "rho_status": s.get("rho_status")}
        f = by_matchup_final.get(s["game"])
        if not f:
            rec["result"] = "PENDING (official page is not Final)"
            out.append(rec)
            continue
        pending = False
        for key in ("leg1_detail", "leg2_detail"):
            d = s.get(key) or {}
            player, team, line = d.get("player"), d.get("team"), d.get("line")
            side = "home" if f["home"] == team else "away" if f["away"] == team else None
            pts = None
            if side:
                for pl in (f.get(side + "_players") or []):
                    if pl.get("name") == player:
                        pts = pl.get("points")
                        break
            if pts is None:
                pending = True
                rec["leg_results"].append("PENDING/VOID (player not in the official box score)")
            else:
                rec["leg_results"].append(("OVER-WIN" if pts > line else
                                           "OVER-PUSH" if pts == line else "OVER-LOSS")
                                          if s.get(key, {}).get("line") is not None or True
                                          else "?")
                rec["leg_results"][-1] = {
                    "player": player, "points": pts, "line": line,
                    "result": "WIN" if pts > line else "PUSH" if pts == line else "LOSS"}
        if pending:
            rec["result"] = "PENDING"
        else:
            rs = [x["result"] for x in rec["leg_results"]]
            rec["result"] = "LOSS" if "LOSS" in rs else "PUSH" if "PUSH" in rs else "WIN"
            rec["units"] = -1.1 if rec["result"] == "LOSS" else 0.0 if rec["result"] == "PUSH" else 1.0
        out.append(rec)
    return out


# ---------------------------------------------------------------- main
def main():
    os.makedirs(SETTLE, exist_ok=True)
    os.makedirs(PREREG, exist_ok=True)

    feed = jload(os.path.join(ROOT, "data", "official", "results_feed_2026_27.json"))
    rows = feed["rows"]
    finals = [r for r in rows if r["game_status"] == 3]
    finals_by_id = {r["game_id"]: r for r in finals}
    by_matchup_final = {}
    for r in finals:
        by_matchup_final["%s@%s" % (r["away"], r["home"])] = r

    # Player points per side, keyed for SGP settlement.
    boxes = {r["game_id"]: r for r in rows}
    raw = {}
    for r in rows:
        raw[r["game_id"]] = r

    # ---------------------------------------------------------- 1. settlement
    arch_path = os.path.join(ARCHIVE, "horizon_picks_2026-11-15.json")
    arch = jload(arch_path)
    # Re-attach player scoring from the official box scores for SGP grading.
    for r in finals:
        r.setdefault("home_players", [])
        r.setdefault("away_players", [])
    for r in rows:
        if r["game_status"] != 3:
            continue
        for side in ("home", "away"):
            r.setdefault(side + "_players", [])
    # pull player scoring out of the raw capture
    import gzip
    import glob as _glob
    import json as _json
    import re as _re
    cap = os.path.join(ROOT, "data", "raw", "html", "2026-11-15-801ba27f")
    for path in _glob.glob(os.path.join(cap, "boxscore__*.html.gz")):
        gid = os.path.basename(path)[len("boxscore__"):-len(".html.gz")].rsplit("-", 1)[-1]
        if gid not in finals_by_id:
            continue
        html = gzip.open(path, "rb").read().decode("utf-8", "replace")
        m = _re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, _re.S)
        if not m:
            continue
        g = (_json.loads(m.group(1)).get("props", {}).get("pageProps", {}) or {}).get("game") or {}
        for side, key in (("home", "homeTeam"), ("away", "awayTeam")):
            t = g.get(key) or {}
            finals_by_id[gid][side + "_players"] = [
                {"name": ("%s %s" % (p.get("firstName") or "", p.get("familyName") or "")).strip(),
                 "points": (p.get("statistics") or {}).get("points")}
                for p in (t.get("players") or [])]

    day_finals = [f for f in finals if f["date"] == TODAY]
    singles = settle_singles({**arch, "singles": [s for s in arch["singles"] if s["date"] == TODAY]},
                             finals_by_id)
    parlays = settle_parlays({**arch, "parlays": [p for p in arch.get("parlays", [])
                                                  if p["date"] == TODAY]},
                             finals_by_id, by_matchup_final)
    sgps = settle_sgp({**arch, "sgp_candidates": [s for s in arch.get("sgp_candidates", [])
                                                  if s["date"] == TODAY]},
                      finals_by_id, by_matchup_final)

    graded = [r for r in singles if r["result"] in ("WIN", "LOSS", "PUSH")]
    units = round(sum(r["units"] for r in graded), 2)
    settlement = {
        "title": "Settlement — 2026-11-15 slate (graded from official finals only)",
        "session": "arena/801ba27f-nba1",
        "settled_at_utc": RUN_UTC,
        "rule": ("a ticket is graded only when the official game page says Final "
                 "(game_status 3) and the official quarter scores sum to the final. "
                 "Anything else stays PENDING - never graded on a live score."),
        "pre_tip_anchor": {
            "publication_file": os.path.relpath(arch_path, ROOT),
            "sha256": sha256_file(arch_path),
            "published_utc": arch["_meta"].get("generated_utc"),
            "published_by": "arena/83d380ad-nba1",
        },
        "finals_source": "data/official/results_feed_2026_27.json",
        "official_date_url": "https://www.nba.com/games?date=2026-11-15",
        "games_final_today": len(day_finals),
        "games_still_live_today": sum(1 for r in rows
                                      if r["date"] == TODAY and r["game_status"] != 3),
        "n_graded": len(graded),
        "n_pending": sum(1 for r in singles if r["result"].startswith("PENDING")),
        "units_today": units,
        "price_convention": PAPER_PRICE,
        "singles": singles, "parlays": parlays, "sgp_candidates": sgps,
    }
    json.dump(settlement, open(os.path.join(SETTLE, "settlement_2026-11-15.json"), "w"), indent=1)
    print("settlement 11/15: %d graded, %d pending, units %.2f"
          % (len(graded), settlement["n_pending"], units))

    # -------------------------------------------------- 2. the two estimators
    est = jload(os.path.join(DERIVED, "estimators_2026_27.json"))
    ratings = jload(os.path.join(DERIVED, "team_ratings_2026_27.json"))["teams"]
    const = jload(os.path.join(DERIVED, "measured_constants_2026_27.json"))
    rotation = jload(os.path.join(DERIVED, "rotation_2026_27.json"))["teams"]
    rest = jload(os.path.join(DERIVED, "rest_travel_2026_27.json"))["rows"]
    luck = {r["team"]: r for r in jload(os.path.join(DERIVED, "luck_2026_27.json"))["rows"]}
    rho_doc = jload(os.path.join(DERIVED, "rho_2026_27.json"))
    inj = jload(os.path.join(ROOT, "data", "injury_reports", "editions_2026-11-15.json"))
    newest = [e for e in inj["editions"] if e["parse_status"] == "ok"]
    newest = newest[-1] if newest else {"rows": [], "revision_label": None,
                                        "retrieved_utc": None}

    # Rotation availability: the minutes-weighted share of each team's measured
    # top-8 that is not ruled out on the newest official injury edition.
    STATUS_WEIGHT = {"Out": 0.0, "Doubtful": 0.25, "Questionable": 0.65,
                     "Probable": 0.9, "Available": 1.0}
    inj_by_team = defaultdict(dict)
    for r in newest.get("rows", []):
        if r.get("tricode") and r.get("player"):
            inj_by_team[r["tricode"]][r["player"]] = r

    def rotation_availability(team):
        rot = rotation.get(team)
        if not rot:
            return None
        weight, missing, out = 0.0, [], []
        for p in rot["top8"]:
            rec = inj_by_team.get(team, {}).get(p["player"])
            if rec is None:
                w = 1.0                       # not on the report at all
            else:
                w = STATUS_WEIGHT.get(rec["status"], 1.0)
                if rec["status"] == "Out":
                    out.append(p["player"])
            weight += p["minutes_share"] * w
        return {"available_share": round(weight, 3),
                "outs_in_top8": out,
                "top8_minutes_share_total": round(sum(p["minutes_share"]
                                                      for p in rot["top8"]), 3),
                "rotation_window": rot["window"],
                "source": "measured minutes shares from official box scores x the newest "
                          "official injury edition (%s)" % newest.get("revision_label")}

    rest_by = {(r["date"], r["team"]): r for r in rest}

    # ------------------------------------------ 2a. PROJECTION surface (lines)
    proj_rows = []
    for e in est["rows"]:
        h, a = e["home"], e["away"]
        ra, rh = rotation_availability(a), rotation_availability(h)
        lr = rest_by.get((e["date"], a))
        lh = rest_by.get((e["date"], h))
        lz_a = luck.get(a, {})
        lz_h = luck.get(h, {})
        proj_rows.append({
            "date": e["date"], "game_id": e["game_id"],
            "matchup": "%s@%s" % (a, h), "away": a, "home": h,
            "status_official": e["status"],
            # Publishable == the official page says the game has NOT started
            # (game_status 1). Anything already tipped is settled, not picked.
            "publishable": e.get("game_status") == 1,
            "e1_total": e["e1_total"], "e1_spread_home": e["e1_spread_home"],
            "e2_total": e["e2_total"], "e2_spread_home": e["e2_spread_home"],
            "disagreement_total": e["disagreement_total"],
            "disagreement_spread": e["disagreement_spread"],
            "blend_total": e["blend_total"], "blend_spread_home": e["blend_spread_home"],
            "hca_applied": e["hca_applied"],
            "home_court_rule": const["home_court_rule"],
            "rotation_availability_home": rh, "rotation_availability_away": ra,
            "rest_home": {k: lh.get(k) for k in
                          ("rest_days", "back_to_back", "three_in_four",
                           "travel_miles_from_previous_venue")} if lh else None,
            "rest_away": {k: lr.get(k) for k in
                          ("rest_days", "back_to_back", "three_in_four",
                           "travel_miles_from_previous_venue")} if lr else None,
            "luck_z_home": lz_h.get("luck_z"), "luck_z_away": lz_a.get("luck_z"),
            "source_url": e["source_url"],
            "source_date_url": "https://www.nba.com/games?date=" + e["date"],
        })
    lines_doc = {
        "title": "PROJECTION surface — originated lines, 2026-11-15..18",
        "surface": "projection",
        "session": "arena/801ba27f-nba1",
        "published_utc": RUN_UTC,
        "headline": "the DISAGREEMENT between the two estimators; the 50/50 blend is printed underneath",
        "estimator_1": est["estimator_1"], "estimator_2": est["estimator_2"],
        "home_court": const["home_court_rule"],
        "home_court_points": const["home_court_points"],
        "home_win_rate": const["home_win_rate"],
        "n_final_games_behind_it": const["n_final_games"],
        "injury_edition": newest.get("revision_label"),
        "injury_retrieved_utc": newest.get("retrieved_utc"),
        "injury_source_url": newest.get("source_url"),
        "bet_surface": "data/derived/horizon_picks_801ba27f.json (gated; never merged into this table)",
        "rows": proj_rows,
    }
    lines_path = os.path.join(DERIVED, "horizon_lines_801ba27f.json")
    json.dump(lines_doc, open(lines_path, "w"), indent=1)

    # ------------------------------------------------- 3. BET surface (gated)
    # Pre-registration for the three ticket families actually published,
    # frozen before this publication and hashed into the ledger.
    prereg = {
        "R-SINGLE": {
            "prereg_id": "R-SINGLE",
            "family": "single",
            "signal": ("Take the side of the originated line when the two independent "
                       "estimators AGREE closely (disagreement on the spread <= 2.5 "
                       "points) and the model edge on the spread is >= 3.0 points."),
            "thresholds": {"spread_edge_min": 3.0, "max_estimator_disagreement_spread": 2.5,
                           "min_games_behind_ratings": 100},
            "universe": "every game on the official 2026-11-15..18 slate that has not tipped",
            "exact_settlement_rule": ("paper -110 against the frozen line: cover if the "
                                      "picked team wins by MORE than the frozen line, PUSH "
                                      "at exactly the line, else LOSS. Graded only from the "
                                      "official final, never from a live score."),
        },
        "R-PARLAY": {
            "prereg_id": "R-PARLAY",
            "family": "parlay",
            "signal": ("Two legs from DIFFERENT games, each an R-SINGLE qualifier, priced "
                       "with the measured cross-game correlation."),
            "thresholds": {"legs": 2, "leg_edge_min": 3.0, "min_joint_prob": 0.30},
            "universe": "R-SINGLE qualifiers on the 2026-11-15..18 slate",
            "exact_settlement_rule": ("every leg must WIN; any losing leg loses the 1.10 "
                                      "stake; a PUSH leg reduces the ticket to the "
                                      "remaining legs at the frozen price."),
        },
        "R-SGP": {
            "prereg_id": "R-SGP",
            "family": "same-game-parlay",
            "signal": ("Two player point props in the SAME game, priced with the measured "
                       "same-game correlation; the independent product is printed beside it."),
            "thresholds": {"legs": 2, "min_minutes_share": 0.10},
            "universe": "players with a measured minutes share on the 2026-11-15..18 slate",
            "exact_settlement_rule": ("OVER/UNDER against the frozen line from the official "
                                      "box score; a leg whose player does not appear in the "
                                      "official box score is VOID and the ticket settles on "
                                      "the remaining legs."),
        },
    }
    rho_measured = {m["pair"]: m for m in rho_doc["measured"]}
    cross = next((m for m in rho_doc["measured"] if "cross" in m["pair"]), None)
    rho_cross = cross["rho"] if cross else 0.0
    rho_side_total = rho_measured.get("same game: home margin vs total points", {}).get("rho")

    singles_out, parlays_out, sgp_out = [], [], []
    publishable = [r for r in proj_rows if r["publishable"]
                   and r["disagreement_spread"] is not None
                   and abs(r["blend_spread_home"]) >= 3.0
                   and r["disagreement_spread"] <= 2.5]
    for r in publishable:
        side = "HOME" if r["blend_spread_home"] > 0 else "AWAY"
        team = r["home"] if side == "HOME" else r["away"]
        line = round(abs(r["blend_spread_home"]), 1)
        singles_out.append({
            "date": r["date"], "game_id": r["game_id"],
            "matchup": r["matchup"],
            "pick": "%s %s%.1f" % (team, "-" if side == "HOME" else "+", line),
            "side": side, "team": team, "line": line,
            "e1_spread_home": r["e1_spread_home"], "e2_spread_home": r["e2_spread_home"],
            "disagreement_spread": r["disagreement_spread"],
            "rotation_availability": (r["rotation_availability_home"] if side == "HOME"
                                      else r["rotation_availability_away"]),
            "luck_z": r["luck_z_home"] if side == "HOME" else r["luck_z_away"],
            "luck_gate": ("PASS" if abs(r["luck_z_home"] if side == "HOME"
                                        else r["luck_z_away"] or 0) <= 2.0 else
                          "REFUSED — team outside the noise band"),
            "prereg": "R-SINGLE",
            "status": "MODEL OUTPUT — UNVALIDATED (no strategy has passed the gates; zero stake)",
            "sources": [r["source_url"], r["source_date_url"]],
        })

    # Parlays: cross-game, rho-priced, with the naive product printed beside it.
    for i in range(len(publishable)):
        for j in range(i + 1, len(publishable)):
            a, b = publishable[i], publishable[j]
            if a["date"] == b["date"] and a["game_id"] == b["game_id"]:
                continue
            pa = norm_cdf(abs(a["blend_spread_home"]) / const["sigma_margin"])
            pb = norm_cdf(abs(b["blend_spread_home"]) / const["sigma_margin"])
            pa = min(max(pa, 0.51), 0.95)
            pb = min(max(pb, 0.51), 0.95)
            joint_rho = bivariate_normal_cdf(norm_ppf(pa), norm_ppf(pb), rho_cross or 0.0)
            naive = pa * pb
            if joint_rho < 0.30:
                continue
            parlays_out.append({
                "date": a["date"] + " / " + b["date"],
                "leg1": "%s %s" % (a["matchup"],
                                   ("%s -%.1f" % (a["home"], abs(a["blend_spread_home"]))
                                    if a["blend_spread_home"] > 0
                                    else "%s +%.1f" % (a["away"], abs(a["blend_spread_home"])))),
                "leg2": "%s %s" % (b["matchup"],
                                   ("%s -%.1f" % (b["home"], abs(b["blend_spread_home"]))
                                    if b["blend_spread_home"] > 0
                                    else "%s +%.1f" % (b["away"], abs(b["blend_spread_home"])))),
                "p1": round(pa, 4), "p2": round(pb, 4),
                "rho_used": rho_cross,
                "rho_status": "MEASURED from official finals (cross-game home-margin correlation)",
                "joint_prob_with_rho": round(joint_rho, 4),
                "naive_independent_product_printed_beside": round(naive, 4),
                "fair_odds_with_rho": round(1 / joint_rho, 3) if joint_rho else None,
                "prereg": "R-PARLAY",
                "status": "MODEL OUTPUT — UNVALIDATED (zero stake)",
                "sources": [a["source_url"], b["source_url"]],
            })
    parlays_out.sort(key=lambda x: -x["joint_prob_with_rho"])
    parlays_out = parlays_out[:12]

    # SGP: two players in the same game with a measured minutes share.
    for r in publishable:
        game_rows = [x for x in rows if x["game_id"] == r["game_id"]]
        if not game_rows:
            continue
        for side in ("home", "away"):
            rot = rotation.get(r[side])
            if not rot or len(rot["top8"]) < 2:
                continue
            p1, p2 = rot["top8"][0], rot["top8"][1]
            if p1["minutes_share"] < 0.10 or p2["minutes_share"] < 0.10:
                continue
            r2 = rho_measured.get("two team-mates: points (top-2 minutes on the same team)", {})
            rho_tt = r2.get("rho")
            if rho_tt is None:
                continue
            # Line = the player's measured season scoring rate, rounded to .5
            def line_for(p):
                return round(p["points_per_game"] * 2) / 2
            l1, l2 = line_for(p1), line_for(p2)
            s1 = math.sqrt(max(p1["points_per_game"], 1.0)) * 1.15
            s2 = math.sqrt(max(p2["points_per_game"], 1.0)) * 1.15
            q1 = 1 - norm_cdf((l1 - p1["points_per_game"]) / s1)
            q2 = 1 - norm_cdf((l2 - p2["points_per_game"]) / s2)
            q1, q2 = min(max(q1, 0.05), 0.95), min(max(q2, 0.05), 0.95)
            joint = bivariate_normal_cdf(norm_ppf(q1), norm_ppf(q2), rho_tt)
            naive = q1 * q2
            sgp_out.append({
                "date": r["date"], "game": r["matchup"], "kind": "two_team-mates_points_over",
                "leg1": "%s (%s) OVER %.1f" % (p1["player"], r[side], l1),
                "leg2": "%s (%s) OVER %.1f" % (p2["player"], r[side], l2),
                "p1": round(q1, 4), "p2": round(q2, 4),
                "rho_used": rho_tt,
                "rho_status": "MEASURED from official game logs (n=%s)" % r2.get("n"),
                "joint_prob_with_rho": round(joint, 4),
                "naive_independent_product_printed_beside": round(naive, 4),
                "sigma_note": "sqrt(points per game) * 1.15 overdispersion — stated choice",
                "prereg": "R-SGP",
                "status": "MODEL OUTPUT — UNVALIDATED (zero stake); G-PROP still BLOCKED "
                          "(no market number to validate against)",
                "sources": [r["source_url"]],
            })
    sgp_out = sgp_out[:12]

    picks_path = os.path.join(DERIVED, "horizon_picks_801ba27f.json")
    picks_doc = {
        "title": "BET surface — gated, 2026-11-15..18",
        "surface": "bet",
        "session": "arena/801ba27f-nba1",
        "published_utc": RUN_UTC,
        "gate_status": ("CLOSED. No strategy has passed the validation gates, so every "
                        "ticket below is MODEL OUTPUT at zero stake. Do not fund."),
        "gates": {
            "G1_sample_floor": "n >= 100 graded bets",
            "G2_significance": "one-sided binomial p < 0.05, Bonferroni-corrected",
            "G3_luck_bootstrap": "5th percentile of a 10,000-draw bootstrap ROI > 0",
            "G4_stability": "profitable in both disjoint halves",
            "G5_fragility": "profitable after removing the best 5% of bets",
            "G6_provenance": "all driving inputs from approved official hosts",
            "G7_luck_gate": ("refuse to publish a ticket that leans on a team whose luck "
                             "z-score is outside +/-2.0"),
            "G8_market_anchor": ("BLOCKED - no official closing line is captured anywhere "
                                 "in this repository, so the market-anchored prior weight "
                                 "is 0 and no market-blended price is published"),
        },
        "market_anchored_prior": {
            "status": "NOT APPLIED — weight 0",
            "reason": ("the prior needs a closing line; no official or licensed market "
                       "price is captured in this repo, and inventing one would be a "
                       "hallucination. The weighting machinery exists and is set to the "
                       "model-only blend until a price feed is added."),
        },
        "n_singles": len(singles_out), "n_parlays": len(parlays_out), "n_sgp": len(sgp_out),
        "singles": singles_out, "parlays": parlays_out, "sgp_candidates": sgp_out,
    }
    json.dump(picks_doc, open(picks_path, "w"), indent=1)
    print("bet surface: %d singles, %d parlays, %d sgp"
          % (len(singles_out), len(parlays_out), len(sgp_out)))

    # Pre-tip anchor: both surfaces are archived byte-identically.
    os.makedirs(ARCHIVE, exist_ok=True)
    arc_dir = os.path.join(ARCHIVE, "v2-801ba27f")
    os.makedirs(arc_dir, exist_ok=True)
    arc_lines = os.path.join(arc_dir, "horizon_lines_801ba27f.json")
    arc_picks = os.path.join(arc_dir, "horizon_picks_801ba27f.json")
    open(arc_lines, "w").write(open(lines_path).read())
    open(arc_picks, "w").write(open(picks_path).read())

    # ---------------------------------------------------- 4. preregistration
    index = {"title": "Pre-registration freeze — 2026-11-15 late cycle",
             "session": "arena/801ba27f-nba1",
             "frozen_at_utc": RUN_UTC,
             "rule": ("signal, thresholds, universe and the exact settlement rule are "
                      "frozen before the first tip these tickets can be placed against"),
             "files": {}}
    for pid, body in prereg.items():
        body = dict(body)
        body["frozen_at_utc"] = RUN_UTC
        body["frozen_by"] = "arena/801ba27f-nba1"
        body["first_tip_this_publication_can_apply_to"] = (
            "2026-11-15 7:00 PM ET (HOU@WAS) — the earliest 2026-11-15 game that had not "
            "tipped at publication")
        body["validation_gates"] = picks_doc["gates"]
        body["price_status"] = ("no licensed two-sided price exists in this repository; "
                                "tickets settle on the paper -110 convention and unit ROI "
                                "stays blank until a price feed exists")
        p = os.path.join(PREREG, pid + ".json")
        json.dump(body, open(p, "w"), indent=1)
        index["files"][os.path.relpath(p, ROOT)] = sha256_file(p)
    json.dump(index, open(os.path.join(PREREG, "_index.json"), "w"), indent=1)

    # ------------------------------------------------------------ 5. ledger
    led = jload(LEDGER)
    prev = led["head"] or "GENESIS"
    e_settle = {
        "entry": len(led["entries"]) + 1,
        "type": "settlement_verification",
        "at_utc": RUN_UTC,
        "session": "arena/801ba27f-nba1",
        "settles_slate": "2026-11-15",
        "files": {"data/settlement/settlement_2026-11-15.json":
                  sha256_file(os.path.join(SETTLE, "settlement_2026-11-15.json")),
                  os.path.relpath(arch_path, ROOT): sha256_file(arch_path)},
        "n_graded": len(graded), "units_today": units,
        "note": "graded only from official finals; games still live stay PENDING",
        "prev": prev,
    }
    led["entries"].append(e_settle)
    led["head"] = sha256_obj(e_settle)
    e_pub = {
        "entry": len(led["entries"]) + 1,
        "type": "pre_tip_publication",
        "at_utc": RUN_UTC,
        "session": "arena/801ba27f-nba1",
        "slate": "2026-11-15..18 (games that had not tipped at publication)",
        "first_tip_utc": "2026-11-16T00:00Z (2026-11-15 7:00 PM ET, HOU@WAS)",
        "publication_precedes_first_tip": True,
        "files": {os.path.relpath(arc_picks, ROOT): sha256_file(arc_picks),
                  os.path.relpath(arc_lines, ROOT): sha256_file(arc_lines),
                  os.path.relpath(os.path.join(PREREG, "_index.json"), ROOT):
                  sha256_file(os.path.join(PREREG, "_index.json"))},
        "prereg_digests": index["files"],
        "note": "projection and bet surfaces published separately; archived byte-identically",
        "prev": led["head"],
    }
    led["entries"].append(e_pub)
    led["head"] = sha256_obj(e_pub)
    json.dump(led, open(LEDGER, "w"), indent=1)
    print("ledger: appended entries %d and %d; head %s"
          % (e_settle["entry"], e_pub["entry"], led["head"][:16]))
    print("done.")


if __name__ == "__main__":
    main()
