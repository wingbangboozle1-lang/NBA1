#!/usr/bin/env python3
"""Build the fresh 3-day slate page (slate.html) and its audit record from official captures.

Inputs (all official-sourced, already in-repo):
  data/slate_2026_11_14.json            captured 2026-11-14T00:48Z: nba.com schedule + games pages
                                        (27 games, records, venues, season leaders) and the official
                                        injury-report PDF 11/13/26 07:30 PM ET edition (11/14 rows)
  data/teams_advanced_2026_27.json      official NBA.com team advanced stats (through 11/12 games)
  data/teams_scoring_2026_27.json       official NBA.com team scoring splits (through 11/12 games)
  data/played_games_2026_11_11_12.json  official NBA.com final scores (measured dispersion)

Models (both pre-existing in this repository, unchanged):
  RecordLine-1   spread/moneyline/pick  — identical constants to scripts/build_edge_site.py
  Engine v0      additive total/spread  — identical formula to scripts/originate_lines.py (HCA=0)

Integrity gates (fail -> exit 1):
  * every game/injury/leader row carries an https source on an allowed official host
  * captured per-date slate sizes match the official calendar strip (11/13:9, 11/14:5, 11/15:9, 11/16:8, 11/17:5)
  * every captured record (W-L) matches data/teams_advanced_2026_27.json (w, l, gp) — two
    independent official captures must agree
  * every rendered <tbody> row contains at least one official-source link

Outputs:
  slate.html                          rendered page
  data/originated_lines_refresh.json  audit record of every model output
"""
import html
import json
import math
import os
import sys
from datetime import date
from statistics import mean, pstdev
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

ALLOWED_HOSTS = {
    "www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com", "cdn.nba.com",
}

# ---- RecordLine-1 constants — IDENTICAL to scripts/build_edge_site.py ----
PRIOR_W, PRIOR_G = 3.0, 6.0     # smoothing: +3 wins / +6 games toward .500
HCA = 2.5                        # home-court points (documented assumption, flag E-01)
K = 35.0                         # points per 1.000 smoothed win-pct difference
SIGMA = 11.0                     # points scale for win probability
CONF_MARGIN = 3.0                # pick gate: |expected margin| >= 3.0
PROP_ROUND = 0.5                 # prop combo line rounding step

errors = []


def load(name):
    with open(os.path.join(DATA, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def esc(v):
    return html.escape("" if v is None else str(v))


def check_url(url, where):
    if not url:
        errors.append(f"{where}: missing source link")
        return False
    p = urlparse(url)
    if p.scheme != "https" or p.netloc not in ALLOWED_HOSTS:
        errors.append(f"{where}: source host not allowed: {url}")
        return False
    return True


def a(url, label):
    check_url(url, f"link {label}")
    return f'<a class="source" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def fmt(v, nd=1):
    return "—" if v is None else f"{v:.{nd}f}"


def parse_rec(rec):
    if not rec or "-" not in rec:
        return None, None
    w, l = rec.split("-")
    return int(w), int(l)


def smoothed(w, g):
    return (w + PRIOR_W) / (g + PRIOR_G)


def home_margin(p_home, p_away):
    return K * (p_home - p_away) + HCA


def p_home_win(margin):
    return 1.0 / (1.0 + math.exp(-margin / SIGMA))


def round_half(x):
    return round(x * 2) / 2


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def rho_bounds(p1, p2):
    denom = math.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
    if denom == 0:
        return None, None
    lb_joint = max(0.0, p1 + p2 - 1.0)
    ub_joint = min(p1, p2)
    rho_lb = (lb_joint - p1 * p2) / denom
    rho_ub = (ub_joint - p1 * p2) / denom
    return rho_lb, rho_ub


def name_key(name):
    import re
    parts = re.split(r"[^A-Za-z]+", name.lower())
    return frozenset(p for p in parts if p)


# ---------------------------------------------------------------- load
cap = load("slate_2026_11_14")
teams_adv = load("teams_advanced_2026_27")["rows"]
teams_score = load("teams_scoring_2026_27")["rows"]
played = load("played_games_2026_11_11_12")["games"]

games = cap["games"]
inj = cap["injuries_2026_11_14"]
prior = cap["prior_slate_2026_11_13"]
leaders = {l["team"]: l for l in cap["leaders"]}

adv = {t["abbr"]: t for t in teams_adv}
scoring = {r["abbr"]: r for r in teams_score}

# ---------------------------------------------------------------- integrity gates
for s_id, s in cap["_meta"]["source_index"].items():
    check_url(s["url"], f"source_index {s_id}")

if len(games) != 27:
    errors.append(f"expected 27 window games, found {len(games)}")
by_date = {}
for g in games:
    by_date.setdefault(g["date"], []).append(g)
expected_counts = {"2026-11-14": 5, "2026-11-15": 9, "2026-11-16": 8, "2026-11-17": 5}
for d, n in expected_counts.items():
    if len(by_date.get(d, [])) != n:
        errors.append(f"slate {d}: expected {n} games, found {len(by_date.get(d, []))}")
# prior slate completeness (official calendar strip: Nov 13 -> 9 games)
if len(prior["games"]) != 9:
    errors.append(f"prior slate 2026-11-13: expected 9 games, found {len(prior['games'])}")
check_url(prior["source_url"], "prior slate source")

for g in games:
    check_url(g["source_url"], f"game {g['date']} {g['away']}@{g['home']}")
    check_url(g["preview_url"], f"preview {g['date']} {g['away']}@{g['home']}")
    w, l = parse_rec(g["away_record"])
    t = adv.get(g["away"])
    if t is None:
        errors.append(f"game {g['away']}@{g['home']}: away team missing from teams_advanced")
    elif (w, l, w + l) != (t["w"], t["l"], t["gp"]):
        errors.append(
            f"record mismatch {g['away']} on {g['date']}: captured {g['away_record']} "
            f"vs teams_advanced w={t['w']} l={t['l']} gp={t['gp']}")
    w, l = parse_rec(g["home_record"])
    t = adv.get(g["home"])
    if t is None:
        errors.append(f"game {g['away']}@{g['home']}: home team missing from teams_advanced")
    elif (w, l, w + l) != (t["w"], t["l"], t["gp"]):
        errors.append(
            f"record mismatch {g['home']} on {g['date']}: captured {g['home_record']} "
            f"vs teams_advanced w={t['w']} l={t['l']} gp={t['gp']}")

check_url(inj["meta"]["source_url"], "injury report")
check_url(inj["meta"]["source_index_url"], "injury report index")
for r in inj["rows"]:
    check_url(r["source_url"], f"injury row {r.get('player') or r.get('team')}")
    if r["team_source"] == "roster" and not r.get("team_source_url"):
        errors.append(f"injury row {r.get('player')}: roster attribution without roster url")
    if r["team_source"] == "roster":
        check_url(r["team_source_url"], f"injury roster url {r.get('player')}")

for abbr, lg in leaders.items():
    check_url(lg["source_url"], f"leader {abbr}")

# ---------------------------------------------------------------- rest / back-to-back
# Complete captured slates: 2026-11-13 (9 games, official calendar strip) and the full
# window 11/14-11/17. A team not appearing on the immediately preceding captured slate
# did not play the previous day -> rest_days >= 1 -> NOT a back-to-back (derivable, not
# inferred). Exact rest_days is only reported when the previous appearance is captured.
last_game = {}  # team -> (date, source_url)
rest_info = {}  # (date, team) -> dict

prior_by_date = {"2026-11-13": (prior["games"], prior["source_url"])}
window_dates = sorted(by_date.keys())  # includes 2026-11-14; process each date exactly once


def slate_of(d):
    if d in prior_by_date:
        return prior_by_date[d]
    return None


# teams whose last game is at most 2026-11-12 (not on the complete 11/13 slate)
for g in prior["games"]:
    for t in (g["away"], g["home"]):
        last_game[t] = ("2026-11-13", prior["source_url"])

for d in window_dates:
    if d not in by_date:
        continue
    dd = date.fromisoformat(d)
    for g in by_date[d]:
        for t, url in ((g["away"], g["source_url"]), (g["home"], g["source_url"])):
            lg = last_game.get(t)
            if lg is None:
                # not on 11/13 slate (complete) and not in window before this date:
                # last game <= 11/12 -> rest >= 1 day -> not a back-to-back
                rest_info[(d, t)] = {"rest_days": None, "b2b": False, "exact": False,
                                     "last_date": None, "last_slate_url": None,
                                     "note": "No game on the immediately preceding captured slate(s); last game on/before 2026-11-12 (games page records include games through 11/12)."}
            else:
                ld = date.fromisoformat(lg[0])
                rest_days = (dd - ld).days - 1
                if rest_days < 0:
                    errors.append(f"rest derivation: negative rest for {t} on {d} (last {lg[0]})")
                rest_info[(d, t)] = {"rest_days": rest_days, "b2b": rest_days == 0,
                                     "exact": True, "last_date": lg[0],
                                     "last_slate_url": lg[1], "note": None}
        for t, url in ((g["away"], g["source_url"]), (g["home"], g["source_url"])):
            last_game[t] = (d, g["source_url"])

# ---------------------------------------------------------------- engine v0 (totals)
league_pace = mean(t["pace"] for t in teams_adv)
league_off = mean(t["off_rtg"] for t in teams_adv)

margins = [x["home_pts"] - x["away_pts"] for x in played]
totals = [x["home_pts"] + x["away_pts"] for x in played if not x["ot"]]
margin_sd_emp = pstdev(margins)
total_sd_emp = pstdev(totals)

# ---------------------------------------------------------------- RecordLine-1 + v0 per game
for g in games:
    aw, al = parse_rec(g["away_record"])
    hw, hl = parse_rec(g["home_record"])
    p_a = smoothed(aw, aw + al)
    p_h = smoothed(hw, hw + hl)
    margin = home_margin(p_h, p_a)
    ph = p_home_win(margin)
    spread_home = -round_half(margin)
    if spread_home == 0:
        spread_home = 0.0
    if margin >= CONF_MARGIN:
        pick_side, pick_line = "HOME", f"{g['home']} {spread_home:+.1f}"
    elif margin <= -CONF_MARGIN:
        pick_side, pick_line = "AWAY", f"{g['away']} {-spread_home:+.1f}"
    else:
        pick_side, pick_line = "PASS", None

    # engine v0 additive total/spread (no HCA — flagged)
    h, aw_t = adv[g["home"]], adv[g["away"]]
    poss = h["pace"] + aw_t["pace"] - league_pace
    pts_h = (h["off_rtg"] * aw_t["def_rtg"] / league_off) * poss / 100.0
    pts_a = (aw_t["off_rtg"] * h["def_rtg"] / league_off) * poss / 100.0
    total_v0 = round(round(pts_h, 1) + round(pts_a, 1), 1)
    spread_v0 = round(round(pts_h, 1) - round(pts_a, 1), 1)

    # injury context for this game's teams (11/14 only; later dates have no reports yet)
    g_inj = {}
    for side in ("away", "home"):
        team_name = g[f"{side}_name"]
        rows = [r for r in inj["rows"] if r["team"] == team_name and r["game_date"] == g["date"]]
        if g["date"] != "2026-11-14":
            rows = []
        nys = any(r["status"] == "NOT YET SUBMITTED" for r in rows)
        g_inj[side] = {
            "n_rows": len([r for r in rows if r["player"]]),
            "nys": nys,
            "out": sum(1 for r in rows if r["status"] == "Out" and r["player"]),
            "doubtful": sum(1 for r in rows if r["status"] == "Doubtful" and r["player"]),
            "questionable": sum(1 for r in rows if r["status"] == "Questionable" and r["player"]),
            "probable": sum(1 for r in rows if r["status"] == "Probable" and r["player"]),
            "available": sum(1 for r in rows if r["status"] == "Available" and r["player"]),
        }

    provisional = (g["date"] == "2026-11-14" and
                   (g_inj["away"]["nys"] or g_inj["home"]["nys"]))
    no_report_date = g["date"] != "2026-11-14"

    g["model"] = {
        "p_home_smoothed": round(p_h, 3),
        "p_away_smoothed": round(p_a, 3),
        "expected_margin_home": round(margin, 1),
        "originated_spread_home": spread_home,
        "p_home_win": round(ph, 3),
        "ml_home_decimal": round(1.0 / ph, 2),
        "ml_away_decimal": round(1.0 / (1.0 - ph), 2),
        "pick_side": pick_side,
        "pick_line": pick_line,
        "provisional_injury": provisional,
        "gate": ("G-CFG pass (|margin| >= 3.0); paper pick — G4/G5 market gates blocked"
                 if pick_side != "PASS" else "G-CFG fail (|margin| < 3.0) — no bet"),
        "v0": {
            "game_possessions": round(poss, 2),
            "proj_home_pts": round(pts_h, 1),
            "proj_away_pts": round(pts_a, 1),
            "line_total": total_v0,
            "line_spread_home": spread_v0,
            "model_home_win_prob": round(norm_cdf(spread_v0 / margin_sd_emp), 4),
            "home_court_applied": False,
        },
        "injuries": g_inj,
    }

n_picks = sum(1 for g in games if g["model"]["pick_side"] != "PASS")
n_prov = sum(1 for g in games if g["model"]["provisional_injury"])
n_b2b_games = sum(1 for g in games
                  if rest_info[(g["date"], g["away"])]["b2b"] or rest_info[(g["date"], g["home"])]["b2b"])

# ---------------------------------------------------------------- prop anchors + gates
prop_rows = []
for g in games:
    for side in ("away", "home"):
        abbr = g[side]
        lg = leaders.get(abbr)
        if lg is None:
            errors.append(f"prop anchor missing for {abbr} ({g['date']})")
            continue
        src = lg["source_url"]
        combo = round((lg["ppg"] + lg["rpg"] + lg["apg"]) / PROP_ROUND) * PROP_ROUND
        team_name = g[f"{side}_name"]
        if g["date"] != "2026-11-14":
            status, status_reason = "Report not yet published for this date", None
            sig = "BLOCKED — status report not yet due/published (G-INJ)"
            inj_src = inj["meta"]["source_index_url"]
        else:
            nys_team = g["model"]["injuries"][side]["nys"]
            st = None
            for r in inj["rows"]:
                if r["team"] == team_name and r["player"] and \
                        name_key(r["player"]) == name_key(lg["player"]):
                    st = (r["status"], r["reason"])
            if nys_team and st is None:
                status, status_reason = "NOT YET SUBMITTED (team)", None
                sig = "BLOCKED — team report not yet submitted (G-INJ)"
            elif st is None:
                status, status_reason = "Not listed on report", None
                sig = "BLOCKED — no market number, no game-log variance (G-PROP)"
            else:
                status, status_reason = st
                if status in ("Out", "Doubtful"):
                    sig = "NO BET — officially out/doubtful"
                elif status == "Questionable":
                    sig = "PASS — availability risk unquantified"
                else:
                    sig = "BLOCKED — no market number, no game-log variance (G-PROP)"
            inj_src = inj["meta"]["source_url"]
        prop_rows.append({
            "date": g["date"], "game": f"{g['away']}@{g['home']}", "team": team_name,
            "player": lg["player"], "ppg": lg["ppg"], "rpg": lg["rpg"], "apg": lg["apg"],
            "line": combo, "status": status, "status_reason": status_reason,
            "signal": sig, "src_leader": src, "src_inj": inj_src,
        })

# ---------------------------------------------------------------- parlays (Fréchet bounds)
parlay_rows = []
by_date_picks = {}
for g in games:
    if g["model"]["pick_side"] != "PASS":
        by_date_picks.setdefault(g["date"], []).append(g)
for d, picks in sorted(by_date_picks.items()):
    picks = sorted(picks, key=lambda x: -x["model"]["p_home_win"]
                   if x["model"]["pick_side"] == "HOME" else -(1 - x["model"]["p_home_win"]))
    for i, j in [(0, 1), (0, 2), (1, 2)]:
        if i >= len(picks) or j >= len(picks):
            continue
        g1, g2 = picks[i], picks[j]

        def leg_prob(gg):
            m = gg["model"]
            return m["p_home_win"] if m["pick_side"] == "HOME" else 1 - m["p_home_win"]

        p1, p2 = leg_prob(g1), leg_prob(g2)
        rlb, rub = rho_bounds(p1, p2)
        lb_joint = max(0.0, p1 + p2 - 1.0)
        ub_joint = min(p1, p2)
        parlay_rows.append({
            "date": d,
            "leg1": f"{g1['away']}@{g1['home']} — {g1['model']['pick_line']}",
            "leg2": f"{g2['away']}@{g2['home']} — {g2['model']['pick_line']}",
            "p1": round(p1, 3), "p2": round(p2, 3),
            "joint_lb": round(lb_joint, 3), "joint_ub": round(ub_joint, 3),
            "rho_lb": None if rlb is None else round(rlb, 3),
            "rho_ub": None if rub is None else round(rub, 3),
            "fair_odds_lb": round(1.0 / ub_joint, 2) if ub_joint > 0 else None,
            "fair_odds_ub": round(1.0 / lb_joint, 2) if lb_joint > 0 else None,
            "src1": g1["preview_url"], "src2": g2["preview_url"],
        })

if errors:
    print("BUILD FAILED — integrity gates:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

# ---------------------------------------------------------------- audit record
audit = {
    "_meta": {
        "title": "Originated lines — fresh 3-day window 2026-11-14 to 2026-11-17 (captured 2026-11-14T00:48Z)",
        "generated_by": "scripts/build_slate_refresh.py",
        "inputs": {
            "capture": "data/slate_2026_11_14.json",
            "capture_sources": [s["url"] for s in cap["_meta"]["source_index"].values()],
            "team_stats": "data/teams_advanced_2026_27.json (through 2026-11-12 games)",
            "team_scoring": "data/teams_scoring_2026_27.json (through 2026-11-12 games)",
            "dispersion": "data/played_games_2026_11_11_12.json (official finals, measured sd)",
        },
        "recordline1_constants": {
            "PRIOR_W": PRIOR_W, "PRIOR_G": PRIOR_G, "HCA": HCA, "K": K, "SIGMA": SIGMA,
            "CONF_MARGIN": CONF_MARGIN,
            "note": "Identical to scripts/build_edge_site.py (model RecordLine-1). Assumptions, not official values — flagged E-01.",
        },
        "engine_v0_formula": (
            "POSS = pace_home + pace_away - league_pace; "
            "PTS = (OffRtg_team * DefRtg_opp / league_OffRtg) * POSS / 100; "
            "TOTAL = PTS_home + PTS_away; SPREAD = PTS_home - PTS_away; HCA NOT applied (flagged)"),
        "measured_dispersion": {
            "margin_sd": round(margin_sd_emp, 3), "total_sd": round(total_sd_emp, 3),
            "n_margin_games": len(margins), "n_total_games": len(totals),
            "source": "data/played_games_2026_11_11_12.json (official NBA.com finals)",
        },
        "b2b_derivation": (
            "Complete captured slates 2026-11-13 (9 games, official calendar strip) through "
            "2026-11-17. b2b=True only when the team appears on the immediately preceding "
            "captured slate; b2b=False is derivable (not inferred) because the preceding "
            "slates are complete; exact rest_days only when the previous appearance is captured."),
        "integrity_gates_passed": [
            "27 window games; per-date counts match the official calendar strip (5/9/8/5) and the 11/13 slate (9)",
            "all captured records match teams_advanced (w, l, gp) — two independent official captures agree",
            "every row carries an official NBA source link; hosts allow-listed",
        ],
        "flags": [
            "E-01: RecordLine-1 constants (HCA 2.5, K 35, SIGMA 11, smoothing 3/6, gate 3.0) are project assumptions, not official values.",
            "Records were captured before any 2026-11-13 game finished (two were LIVE); inputs are therefore through 11/12 games.",
            "Injury designations for 11/14 games are from the 11/13 07:30 PM ET edition; five teams read NOT YET SUBMITTED; later window dates have no reports yet.",
            "POR@MIN appears on both 11/16 and 11/17 per the official schedule (ids 0022600250 / 0022600254) — transcribed verbatim; the 11/17 game is a B2B for both teams.",
        ],
        "n_games": len(games), "n_model_picks": n_picks, "n_provisional": n_prov,
        "n_b2b_games": n_b2b_games,
    },
    "games": [],
    "props": prop_rows,
    "parlays": parlay_rows,
    "injuries_2026_11_14": inj,
}
for g in games:
    audit["games"].append({
        "date": g["date"], "tip_et": g["time_et"], "matchup": f"{g['away']}@{g['home']}",
        "away": g["away"], "home": g["home"],
        "away_record": g["away_record"], "home_record": g["home_record"],
        "venue": g["venue"],
        "rest": {side: rest_info[(g["date"], g[side])] for side in ("away", "home")},
        "model": g["model"],
        "sources": [g["source_url"], g["preview_url"]],
    })

with open(os.path.join(DATA, "originated_lines_refresh.json"), "w", encoding="utf-8") as f:
    json.dump(audit, f, indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- render slate.html
SCHED_URL = cap["_meta"]["source_index"]["schedule"]["url"]
HUB_URL = inj["meta"]["source_index_url"]


def rest_cell(date_key, team_abbr):
    ri = rest_info[(date_key, team_abbr)]
    if ri["b2b"]:
        return '<span class="badge blocked">B2B</span>'
    return "—"


def status_badge(status):
    if status in ("Out", "Doubtful"):
        return f'<span class="badge blocked">{esc(status)}</span>'
    if status in ("Questionable", "Probable"):
        return f'<span class="badge review">{esc(status)}</span>'
    if status == "Available":
        return f'<span class="badge confirmed">{esc(status)}</span>'
    if status == "NOT YET SUBMITTED":
        return '<span class="badge blocked">NOT YET SUBMITTED</span>'
    return f'<span class="badge proposed">{esc(status)}</span>'


game_rows = []
for g in games:
    m = g["model"]
    if m["pick_side"] != "PASS":
        prov = ' <span class="badge review">provisional — opposing report not yet submitted</span>' \
            if m["provisional_injury"] else ""
        pick_html = f'<span class="badge confirmed">{esc(m["pick_line"])}</span>{prov}<span class="sub">{esc(m["gate"])}</span>'
    else:
        pick_html = f'<span class="badge review">PASS</span><span class="sub">{esc(m["gate"])}</span>'
    game_rows.append(
        f"<tr><td>{esc(g['date'][5:])} <span class=\"sub\">{esc(g['time_et'])} ET</span></td>"
        f"<td><b>{esc(g['away'])} @ {esc(g['home'])}</b>"
        f"<span class=\"sub\">{esc(g['venue'])}</span></td>"
        f"<td>{esc(g['away_record'])} / {esc(g['home_record'])}</td>"
        f"<td>{rest_cell(g['date'], g['away'])} / "
        f"{rest_cell(g['date'], g['home'])}</td>"
        f"<td>{fmt(m['expected_margin_home'])} <span class=\"sub\">p(home) {fmt(m['p_home_win'], 3)}</span></td>"
        f"<td>{m['originated_spread_home']:+.1f} <span class=\"sub\">ML {fmt(m['ml_home_decimal'], 2)} / {fmt(m['ml_away_decimal'], 2)}</span></td>"
        f"<td>{fmt(m['v0']['line_total'])} <span class=\"sub\">spread {m['v0']['line_spread_home']:+.1f} · HCA 0</span></td>"
        f"<td>{pick_html}</td>"
        f"<td>{a(g['preview_url'], 'Game page')} {a(g['source_url'], 'Slate')}</td></tr>")

inj_rows = []
for r in inj["rows"]:
    if r["player"]:
        team_cell = esc(r["team"])
        if r["team_source"] == "roster":
            team_cell += f' <span class="sub">team confirmed via {a(r["team_source_url"], "roster")}</span>'
        inj_rows.append(
            f"<tr><td>11/14</td><td>{esc(r['matchup'])}</td><td>{team_cell}</td>"
            f"<td><b>{esc(r['player'])}</b></td><td>{status_badge(r['status'])}</td>"
            f"<td>{esc(r['reason'])}</td>"
            f"<td>{a(r['source_url'], 'PDF 7:30 PM')}</td></tr>")
    else:
        inj_rows.append(
            f"<tr><td>11/14</td><td>{esc(r['matchup'])}</td><td>{esc(r['team'])}</td>"
            f"<td>—</td><td>{status_badge(r['status'])}</td><td>—</td>"
            f"<td>{a(r['source_url'], 'PDF 7:30 PM')}</td></tr>")

prop_trs = []
for p in prop_rows:
    badge = ("badge blocked" if p["signal"].startswith("BLOCKED")
             else "badge review" if p["signal"].startswith(("PASS", "NO BET"))
             else "badge proposed")
    if p["signal"].startswith("NO BET"):
        badge = "badge blocked"
    prop_trs.append(
        f"<tr><td>{esc(p['date'][5:])} <span class=\"sub\">{esc(p['game'])}</span></td>"
        f"<td>{esc(p['team'])}</td><td><b>{esc(p['player'])}</b></td>"
        f"<td>{fmt(p['ppg'])}</td><td>{fmt(p['rpg'])}</td><td>{fmt(p['apg'])}</td>"
        f"<td><b>{fmt(p['line'])}</b> <span class=\"sub\">(P+R+A)/2 rounding 0.5</span></td>"
        f"<td>{status_badge(p['status'])}</td>"
        f"<td><span class=\"badge {badge}\">{esc(p['signal'])}</span></td>"
        f"<td>{a(p['src_leader'], 'Leaders')} {a(p['src_inj'], 'Report')}</td></tr>")

par_trs = []
for p in parlay_rows:
    par_trs.append(
        f"<tr><td>{esc(p['date'][5:])}</td>"
        f"<td><b>{esc(p['leg1'])}</b><span class=\"sub\">p = {fmt(p['p1'], 3)}</span></td>"
        f"<td><b>{esc(p['leg2'])}</b><span class=\"sub\">p = {fmt(p['p2'], 3)}</span></td>"
        f"<td>{fmt(p['joint_lb'], 3)} – {fmt(p['joint_ub'], 3)}</td>"
        f"<td>{fmt(p['rho_lb'], 3)} – {fmt(p['rho_ub'], 3)}</td>"
        f"<td>{fmt(p['fair_odds_lb'], 2)} – {fmt(p['fair_odds_ub'], 2)}</td>"
        f"<td>{a(p['src1'], 'Leg 1')} {a(p['src2'], 'Leg 2')}</td></tr>")

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Upcoming Slate | NBA Lines Lab</title><link rel="stylesheet" href="subpages.css"></head><body><header class="topbar"><div class="top-inner"><a class="brand" href="index.html"><span class="brand-mark">N</span> NBA Lines Lab</a><div class="top-note">Fresh official capture 2026-11-14 00:48 UTC · window: 3 days ahead · 27 games</div></div></header><div class="layout"><nav class="side" aria-label="Main navigation"><div class="nav-label">Workspace</div><a href="index.html"><span class="nav-icon">◫</span>Executive summary</a><a href="lines.html"><span class="nav-icon">◈</span>Lines &amp; picks (11/13–16)</a><a class="active" href="slate.html"><span class="nav-icon">▦</span>Upcoming slate</a><a href="gameflow.html"><span class="nav-icon">＋</span>Injuries &amp; game flow</a><a href="research.html"><span class="nav-icon">⌁</span>Strategy lab</a><a href="schedule-verified.html"><span class="nav-icon">▦</span>Verified schedule</a><a href="verification.html"><span class="nav-icon">◎</span>Live verification</a><a href="suggestions.html"><span class="nav-icon">✳</span>Questions &amp; suggestions</a><a href="review.html"><span class="nav-icon">⚑</span>Flagged for review</a><a href="sources.html"><span class="nav-icon">↗</span>Source register</a><div class="side-foot">Window: 0–72h+ (max 3 days ahead).<br>No value is fabricated; blanks are flagged.</div></nav><main class="main"><p class="crumb">Workspace / Upcoming slate</p><header class="page-head"><div class="kicker">Daily decision view · captured 2026-11-14T00:48Z</div><h1>Upcoming slate — November 14–17, 2026</h1><p>The maximum 3-day horizon, captured from official NBA.com pages: <b>27 games</b> (Nov 14: 5 · Nov 15: 9 · Nov 16: 8 · Nov 17: 5), with originated RecordLine-1 spreads/moneylines and engine-v0 totals. Per-date game counts were cross-checked against the official calendar strip, and every captured team record was cross-checked against a second official capture (NBA.com Teams Advanced) — all 30 match.</p></header>
<div class="notice warn"><strong>Read the capture caveats before anything else.</strong>Capture happened at 00:48 UTC on Nov 14 (7:48 PM ET, Nov 13) while the nine Nov 13 games were in progress, so <b>team records include completed games through Nov 12 only</b>. Injury designations for Nov 14 games come from the league's 11/13 07:30 PM ET edition — five teams still read NOT YET SUBMITTED — and <b>no designations exist yet for Nov 15–17 games</b> (deadlines not reached). All picks are paper picks; market gates stay blocked (no odds feed). See <a href="review.html">Flagged for review</a>.</div>
<div class="grid"><article class="metric"><div class="metric-label">Window games (official)</div><div class="metric-value">27</div><div class="metric-sub">5 + 9 + 8 + 5 · calendar-verified · <a href="{SCHED_URL}">schedule</a></div></article><article class="metric"><div class="metric-label">RecordLine-1 paper picks</div><div class="metric-value">{n_picks}</div><div class="metric-sub">{n_prov} provisional on injury info · gate |margin| ≥ 3.0</div></article><article class="metric"><div class="metric-label">Games with a B2B team</div><div class="metric-value">{n_b2b_games}</div><div class="metric-sub">derived from complete captured slates · see rest column</div></article></div>
<section class="card"><h2>Model and assumptions (unchanged from lines.html)</h2><p class="card-intro">RecordLine-1 is this project's own line-origination model. Its constants are documented assumptions, not official values (flag E-01). The engine-v0 total is additive ratings math with HCA deliberately not applied.</p><div class="formula">RecordLine-1: p_smoothed = (W+3)/(G+6) · margin = 35·(p_home − p_away) + 2.5 (HCA) · spread_home = −½round(margin) · p_win = 1/(1+e^(−margin/11)) · pick when |margin| ≥ 3.0<br>Engine v0: POSS = pace_h + pace_a − lg_pace · PTS = (OffRtg·DefRtg_opp/lg_OffRtg)·POSS/100 · TOTAL = PTS_h + PTS_a · SPREAD = PTS_h − PTS_a · HCA not applied (flagged)</div><p class="small">RecordLine-1 constants are identical to <a href="lines.html">lines.html</a> (scripts/build_edge_site.py); the v0 total formula is identical to scripts/originate_lines.py. Dispersion is measured from official finals (margin sd {margin_sd_emp:.2f}, total sd {total_sd_emp:.2f}, n={len(margins)} games). Sources: <a href="https://www.nba.com/stats/teams/advanced?Season=2026-27&amp;SeasonType=Regular+Season">NBA Teams Advanced</a> · <a href="https://www.nba.com/stats/teams/traditional?Season=2026-27&amp;SeasonType=Regular+Season&amp;PerMode=PerGame">NBA Teams Traditional</a> · <a href="https://www.nba.com/games?date=2026-11-11">finals 11/11</a> · <a href="https://www.nba.com/games?date=2026-11-12">finals 11/12</a>.</p></section>
<section class="card"><h2>Originated lines and paper picks — all 27 window games</h2><p class="card-intro">Records (away/home) are as rendered on each official games page at capture time (through 11/12 games). Rest flags are derived from complete captured slates: a team that played the previous day shows B2B; a team that did not shows — (derivable, not assumed). Picks are paper picks; G4/G5 market gates remain blocked.</p><div class="table-wrap"><table><thead><tr><th>Date · Tip</th><th>Matchup · Venue</th><th>Records A/H</th><th>Rest A/H</th><th>RL-1 margin (home)</th><th>RL-1 spread (home) · fair ML</th><th>v0 total · spread</th><th>Paper pick · gate</th><th>Sources</th></tr></thead><tbody>
{chr(10).join(game_rows)}
</tbody></table></div><p class="small">Pick gate: |expected margin| ≥ 3.0. “Provisional” marks 11/14 picks where the opposing team's report read NOT YET SUBMITTED at capture — the pick stands only until that report lands. All 11/15–11/17 games additionally lack any injury designations (day-before reports not yet due).</p></section>
<section class="card"><h2>Official injury report — games of 11/14 (league edition 11/13 07:30 PM ET)</h2><p class="card-intro">First designations for the five 11/14 games, transcribed verbatim from the league-issued PDF. Rows whose Team cell was lost in PDF-to-text extraction are attributed <b>only</b> after confirmation against the team's official roster page (“team confirmed via roster”). Five teams read NOT YET SUBMITTED and carry zero rows.</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Matchup</th><th>Team</th><th>Player</th><th>Status</th><th>Reason</th><th>Source</th></tr></thead><tbody>
{chr(10).join(inj_rows)}
</tbody></table></div><p class="small">Reporting rules: day-before 5 p.m. local; second-day-of-B2B 1 p.m. local game day; game-day 11 a.m.–1 p.m. local. Reports update continually — statuses here are a dated snapshot, not a forecast. <a href="{HUB_URL}">Official report hub</a> · <a href="{inj['meta']['source_url']}">PDF 11/13 07:30 PM ET</a>.</p></section>
<section class="card"><h2>Injury coverage for 11/15–11/17 games</h2><p class="card-intro">No league designations exist yet for these 24 games; the columns are left blank and the slates carry zero injury information by rule, not by omission.</p><div class="table-wrap"><table><thead><tr><th>Slate</th><th>Games</th><th>Designations available at capture</th><th>Submission deadline</th><th>Source</th></tr></thead><tbody>
<tr><td>2026-11-15</td><td>9</td><td><span class="badge blocked">None — day-before reports not yet due</span></td><td>5 p.m. local 11/14 (11/15 DAL@BOS second-day DAL report: 1 p.m. local 11/15)</td><td>{a(HUB_URL, 'Report hub')}</td></tr>
<tr><td>2026-11-16</td><td>8</td><td><span class="badge blocked">None</span></td><td>5 p.m. local 11/15; B2B second-day (BOS, WAS, PHI, HOU) 1 p.m. local 11/16</td><td>{a(HUB_URL, 'Report hub')}</td></tr>
<tr><td>2026-11-17</td><td>5</td><td><span class="badge blocked">None</span></td><td>5 p.m. local 11/16; B2B second-day (POR, MIN) 1 p.m. local 11/17</td><td>{a(HUB_URL, 'Report hub')}</td></tr>
</tbody></table></div></section>
<section class="card"><h2>Prop anchors and gates — team season leaders (official games-page tables)</h2><p class="card-intro">Each window team's displayed season leader with the engine's P+R+A combo anchor. Gates follow the Edge Lab convention: no market number and no game-log variance exist in this repository, so every combo stays BLOCKED regardless of status; Out/Doubtful leaders would be NO BET; Questionable is a PASS-with-risk. Statuses are looked up against the 11/14 report only; other dates have no reports yet.</p><div class="table-wrap"><table><thead><tr><th>Date · Game</th><th>Team</th><th>Leader</th><th>PPG</th><th>RPG</th><th>APG</th><th>Combo line</th><th>Report status</th><th>Signal</th><th>Sources</th></tr></thead><tbody>
{chr(10).join(prop_trs)}
</tbody></table></div></section>
<section class="card"><h2>Parlay cards with Fréchet correlation bounds (per date)</h2><p class="card-intro">For each date, the top picks' pairs with joint-probability bounds and the correlation bounds implied by the Fréchet–Hoeffding limits. Legs of the same game-day card are treated as dependent-by-default; the fair-odds band is what the model would need to be offered, not a market quote (no odds feed).</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Leg 1</th><th>Leg 2</th><th>Joint p bounds</th><th>ρ bounds</th><th>Fair odds band</th><th>Sources</th></tr></thead><tbody>
{chr(10).join(par_trs)}
</tbody></table></div><p class="small">ρ bounds are the tightest correlation interval consistent with the two marginal probabilities (Fréchet–Hoeffding). They are bounds, not estimates; empirical same-game correlations remain unpublished in this repo (see research.html).</p></section>
<section class="card"><h2>Cross-checks performed on this capture</h2><div class="table-wrap"><table><thead><tr><th>Check</th><th>Result</th><th>Evidence</th></tr></thead><tbody>
<tr><td>Per-date game counts vs official calendar strip</td><td><span class="badge confirmed">pass</span> Nov 14: 5 · Nov 15: 9 · Nov 16: 8 · Nov 17: 5 · Nov 13: 9</td><td>{a(SCHED_URL, 'Schedule')} {a('https://www.nba.com/games?date=2026-11-14', 'Calendar')}</td></tr>
<tr><td>Captured records vs second official capture (Teams Advanced, w/l/gp)</td><td><span class="badge confirmed">pass</span> all 30 teams match exactly</td><td>{a('https://www.nba.com/stats/teams/advanced?Season=2026-27&amp;SeasonType=Regular+Season', 'Teams Advanced')}</td></tr>
<tr><td>Team pages corroborate records and upcoming games</td><td><span class="badge confirmed">pass</span> DAL “7-5, 10th in West” + Nov 14/15 games listed; DET “8-3, 3rd in East” + Nov 14/17 games listed</td><td>{a('https://www.nba.com/team/1610612742/mavericks/roster', 'DAL page')} {a('https://www.nba.com/team/1610612765/pistons/roster', 'DET page')}</td></tr>
<tr><td>POR@MIN listed on both 11/16 and 11/17</td><td><span class="badge review">verbatim</span> different game ids (0022600250 / 0022600254), same venue; recorded for review, not “corrected”</td><td>{a('https://www.nba.com/games?date=2026-11-16', '11/16 page')} {a('https://www.nba.com/games?date=2026-11-17', '11/17 page')}</td></tr>
<tr><td>Injury team-cell attribution after PDF extraction loss</td><td><span class="badge confirmed">pass</span> 10 lost-cell rows confirmed against official roster pages before attribution</td><td>{a('https://www.nba.com/team/1610612742/mavericks/roster', 'DAL roster')} {a('https://www.nba.com/team/1610612765/pistons/roster', 'DET roster')}</td></tr>
</tbody></table></div></section>
<div class="notice info"><strong>Refresh path.</strong>This page is a dated snapshot built by <code>scripts/build_slate_refresh.py</code> from <code>data/slate_2026_11_14.json</code>. Re-capture the schedule/games pages and the newest injury-report edition, then re-run the script; the automation proposal (scheduled ingestion with freshness alarms) remains open on <a href="suggestions.html">Questions &amp; Suggestions</a>. Audit record: <code>data/originated_lines_refresh.json</code>.</div>
<footer class="footer"><a href="lines.html">Originated lines (11/13–16)</a> · <a href="gameflow.html">Injuries &amp; game flow</a> · <a href="review.html">Flagged items</a> · <a href="sources.html">Source register</a> · <a href="COORDINATION.md">Coordination log</a></footer></main></div></body></html>"""

with open(os.path.join(ROOT, "slate.html"), "w", encoding="utf-8") as f:
    f.write(page)

# ---------------------------------------------------------------- self-audit: every tbody row sourced
import re as _re
from html.parser import HTMLParser


class RowScan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_tbody = False
        self.in_row = False
        self.row_links = []
        self.bad = []
        self.n_rows = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "tbody":
            self.in_tbody = True
        if tag == "tr" and self.in_tbody:
            self.in_row = True
            self.row_links = []
        if tag == "a" and d.get("href") and self.in_row:
            self.row_links.append(d["href"])

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_row:
            self.n_rows += 1
            ok = False
            for h in self.row_links:
                p = urlparse(h)
                if p.scheme == "https" and p.netloc in ALLOWED_HOSTS:
                    ok = True
            if not ok:
                self.bad.append(self.getpos())
            self.in_row = False
        if tag == "tbody":
            self.in_tbody = False


scan = RowScan()
scan.feed(page)
if scan.bad:
    print(f"RENDER AUDIT FAILED — {len(scan.bad)} rows without an official link at {scan.bad[:5]}")
    sys.exit(1)

print(f"slate.html rebuilt: {len(games)} games, {n_picks} picks ({n_prov} provisional), "
      f"{n_b2b_games} B2B games, {len(inj['rows'])} injury rows, {len(prop_rows)} prop anchors, "
      f"{len(parlay_rows)} parlay cards; {scan.n_rows} rendered rows all sourced.")
print("data/originated_lines_refresh.json written.")
