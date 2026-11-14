#!/usr/bin/env python3
"""check_all.py — independent verification for session arena/212c2298-nba1 (tasks Z01/Z02).

Compares verify/212c2298/official_capture_2026-11-14.json (transcribed from live
official NBA.com pages) against the repository's published datasets, row by row,
and independently recomputes every published strategy statistic.

Rules honoured:
  - values that cannot be confirmed are reported as UNVERIFIED, never inferred;
  - every checked row records the official source URL;
  - stale values are only accepted when the exact arithmetic difference is
    explained by an officially observed 11/13 result (stale-explained), and are
    still reported.

Run: python3 verify/212c2298/check_all.py   (writes verify/212c2298/checks.json)
"""
import json
import math
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.join(ROOT, "verify", "212c2298")

results = {"checks": [], "mismatches": [], "unverified": [], "explained_stale": [], "notes": []}


def rec(name, status, detail):
    results["checks"].append({"check": name, "status": status, "detail": detail})


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def find_rows(o, depth=0):
    if isinstance(o, list) and o and isinstance(o[0], dict) and depth < 4:
        return o
    if isinstance(o, dict):
        for v in o.values():
            r = find_rows(v, depth + 1)
            if r:
                return r
    return None


cap = load("verify/212c2298/official_capture_2026-11-14.json")
FIN = cap["finals_2026_11_13"]["rows"]
HOR = cap["horizon_2026_11_14_to_17"]["rows"]
fin_by_id = {r["game_id"]: r for r in FIN}
hor_by_id = {r["game_id"]: r for r in HOR}

# team -> 11/13 outcome (by score, not by home/away slot)
outcome13 = {}
for r in FIN:
    if r["away_pts"] > r["home_pts"]:
        outcome13[r["away"]], outcome13[r["home"]] = "W", "L"
    else:
        outcome13[r["away"]], outcome13[r["home"]] = "L", "W"

SRC_FINALS = "https://www.nba.com/games?date=2026-11-13"
SRC_SIDEBAR = "https://www.nba.com/game/atl-vs-chi-0022600037"


def parse_rec(s):
    m = re.match(r"^(\d+)-(\d+)$", str(s or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def rec_consistent(repo_rec, off_rec, team):
    """repo_rec + 11/13 outcome == off_rec ?"""
    a, b = parse_rec(repo_rec), parse_rec(off_rec)
    if a is None or b is None:
        return None
    if a == b:
        return "match"
    res = outcome13.get(team)
    if res == "W" and (a[0] + 1, a[1]) == b:
        return "stale-explained"
    if res == "L" and (a[0], a[1] + 1) == b:
        return "stale-explained"
    return "UNEXPLAINED"


# ---------------------------------------------------------------- finals
def check_finals():
    name = "finals: capture vs data/verified/finals_2026-11-13.json"
    try:
        repo = load("data/verified/finals_2026-11-13.json")
    except FileNotFoundError:
        rec(name, "MISSING", "file not found")
        return
    rows = repo["rows"]
    ok = bad = 0
    for c in FIN:
        m = [r for r in rows if r["game_id"] == c["game_id"]]
        if not m:
            results["mismatches"].append({"where": name, "row": c["game_id"], "detail": "missing in repo file"})
            bad += 1
            continue
        r = m[0]
        fields = [("away",), ("away_pts",), ("home",), ("home_pts",)]
        for (f,) in fields:
            if r[f] != c[f]:
                results["mismatches"].append({"where": name, "row": c["game_id"], "field": f,
                                              "repo": r[f], "official": c[f], "src": c["source_url"]})
                bad += 1
        if r.get("status_label") != c["status_label"]:
            results["mismatches"].append({"where": name, "row": c["game_id"], "field": "status_label",
                                          "repo": r.get("status_label"), "official": c["status_label"], "src": c["source_url"]})
            bad += 1
        # ot: repo keeps null for ATL-CHI; official box score period filter shows OT1
        if c["game_id"] == "0022600037" and r.get("ot") in (None, 0) and c["ot"] == 1:
            results["mismatches"].append({"where": name, "row": "0022600037", "field": "ot",
                                          "repo": r.get("ot"), "official": 1,
                                          "detail": "official box-score period filter prints 'Q1 Q2 Q3 Q4 OT1'; recap headline 'Bulls outlast Hawks in OT'. Repo deliberately left null (was unconfirmed); this capture confirms 1 OT.",
                                          "src": "https://www.nba.com/game/atl-vs-chi-0022600037/box-score"})
            bad += 1
        elif r.get("ot") != c["ot"]:
            results["mismatches"].append({"where": name, "row": c["game_id"], "field": "ot",
                                          "repo": r.get("ot"), "official": c["ot"], "src": c["source_url"]})
            bad += 1
        ok += 1
    rec(name, "PASS" if bad == 0 else "MISMATCH", f"{len(FIN)} rows compared; {ok} present; {bad} field mismatches (see mismatches)")


def check_finals_consistency():
    name = "finals: post-game records cross-consistent with horizon sidebar"
    bad = 0
    hor_rec = {}
    for r in HOR:
        hor_rec[r["away"]] = r["away_rec"]
        hor_rec[r["home"]] = r["home_rec"]
    for c in FIN:
        for team, key in ((c["away"], "away_rec_after"), (c["home"], "home_rec_after")):
            if team in hor_rec and hor_rec[team] != c[key]:
                results["mismatches"].append({"where": name, "row": team,
                                              "repo": c[key], "official_sidebar": hor_rec[team], "src": SRC_SIDEBAR})
                bad += 1
    rec(name, "PASS" if bad == 0 else "MISMATCH",
        "every team that played 11/13 and appears in the 11/14-11/17 sidebar carries the same post-game record on both official readings")


def check_games_completed():
    name = "finals: promotion state in data/raw/games_completed.json"
    g = load("data/raw/games_completed.json")
    dates = sorted({(r[0] if isinstance(r, list) else r.get("date")) for r in g["rows"]})
    has13 = any(d == "2026-11-13" for d in dates)
    if has13:
        rec(name, "PASS", f"2026-11-13 rows present; window {dates[0]}..{dates[-1]}")
    else:
        rec(name, "FLAG", f"window ends {dates[-1]}: the 9 verified 11/13 finals are NOT promoted "
                          f"(open item F-C01 / request R-X1). data/verified/finals_2026-11-13.json holds them.")


def check_settlement():
    name = "settlement: integration/out/settlement.json vs official finals"
    s = load("integration/out/settlement.json")
    rows13 = [r for r in (s.get("cannot_settle") or []) if r.get("date") == "2026-11-13"]
    urls = {r.get("source_url") for r in rows13}
    bad = 0
    for r in rows13:
        mu = re.match(r"^([A-Z]{2,3})@([A-Z]{2,3})$", r.get("matchup", ""))
        c = fin_by_id.get(r.get("game_id"))
        if not c or not mu:
            results["mismatches"].append({"where": name, "row": r.get("game_id"), "detail": "cannot match to capture"})
            bad += 1
            continue
        if mu.group(1) != c["away"] or mu.group(2) != c["home"]:
            results["mismatches"].append({"where": name, "row": r.get("game_id"), "detail": "matchup mismatch",
                                          "repo": r.get("matchup"), "official": f"{c['away']}@{c['home']}", "src": c["source_url"]})
            bad += 1
    if len(urls) == 1 and rows13:
        results["mismatches"].append({"where": name, "row": "all 9 rows of 2026-11-13",
                                      "field": "source_url", "detail":
                                      f"all rows share one source_url ({urls.pop()}) that is a different game — known irregularity R-X2/§20 item 1. The finals ARE now public and verified; these rows are stale ('IN PROGRESS' snapshots)."})
        bad += 1
    rec(name, "FLAG" if bad else "PASS",
        f"{len(rows13)} rows dated 2026-11-13 sit in cannot_settle with pre-final snapshots; "
        f"matchups/game_ids vs official: {'all match' if bad <= 1 else 'see mismatches'}; "
        f"graded rows so far: {s.get('graded_count')}")

    # settlement arithmetic spot-check: rebuild actual margins/totals from the score strings
    n_ok = n_bad = 0
    for r in s["rows"]:
        if not r.get("settled") or not r.get("final_score"):
            continue
        m = re.match(r"^([A-Z]{2,3}) (\d+) @ ([A-Z]{2,3}) (\d+)$", r["final_score"])
        if not m:
            continue
        aw, ap, hm, hp = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        margin = hp - ap
        total = hp + ap
        if abs(r["actual_margin_home"] - margin) < 1e-9 and abs(r["actual_total"] - total) < 1e-9:
            n_ok += 1
        else:
            n_bad += 1
            results["mismatches"].append({"where": "settlement arithmetic", "row": r.get("game_id"),
                                          "detail": f"final_score {r['final_score']} implies margin {margin} total {total}; "
                                                    f"row says {r['actual_margin_home']} / {r['actual_total']}"})
    rec("settlement: actual margins/totals recomputed from final-score strings",
        "PASS" if n_bad == 0 else "MISMATCH", f"{n_ok} settled rows recomputed, {n_bad} inconsistent")


# ---------------------------------------------------------------- horizon
def check_horizon_lines():
    name = "horizon: site/data/lines.json vs official capture"
    site = load("site/data/lines.json")
    rows = find_rows(site)
    by_id = {r["game_id"]: r for r in rows}
    bad = stale = ok = 0
    for c in HOR:
        r = by_id.get(c["game_id"])
        if not r:
            results["mismatches"].append({"where": name, "row": c["game_id"], "detail": "game missing in site lines"})
            bad += 1
            continue
        for f in ("date", "time_et"):
            if r.get(f) != c[f]:
                results["mismatches"].append({"where": name, "row": c["game_id"], "field": f,
                                              "repo": r.get(f), "official": c[f], "src": c["source_url"]})
                bad += 1
        mu = f"{c['away']}@{c['home']}"
        if r.get("matchup") != mu:
            results["mismatches"].append({"where": name, "row": c["game_id"], "field": "matchup",
                                          "repo": r.get("matchup"), "official": mu, "src": c["source_url"]})
            bad += 1
        for team, repo_key, off_key in ((c["away"], "away_rec", "away_rec"), (c["home"], "home_rec", "home_rec")):
            st = rec_consistent(r.get(repo_key), c[off_key], team)
            if st == "match":
                ok += 1
            elif st == "stale-explained":
                stale += 1
                results["explained_stale"].append({"where": name, "row": c["game_id"], "team": team,
                                                   "repo": r.get(repo_key), "official": c[off_key],
                                                   "explanation": f"team played 11/13 ({outcome13[team]}); repo record is pre-11/13 (flag F29/F-C02)",
                                                   "src": c["source_url"]})
            else:
                bad += 1
                results["mismatches"].append({"where": name, "row": c["game_id"], "field": repo_key,
                                              "team": team, "repo": r.get(repo_key), "official": c[off_key],
                                              "src": c["source_url"]})
    rec(name, "PASS" if bad == 0 else "MISMATCH",
        f"{len(HOR)} games compared (date/tip/matchup/game_id + 54 record cells): "
        f"{ok} record cells match current official cards, {stale} stale-but-explained by 11/13 results, "
        f"{bad} unexplained (see mismatches)")


def check_horizon_official_slate():
    name = "horizon: data/official/slate.json vs official capture"
    s = load("data/official/slate.json")
    rows = find_rows(s)
    by_id = {r["game_id"]: r for r in rows}
    bad = ok = 0
    for c in HOR:
        if c["date"] > "2026-11-16":
            continue  # F30: file stops at 11/16
        r = by_id.get(c["game_id"])
        if not r:
            results["mismatches"].append({"where": name, "row": c["game_id"], "detail": "missing"})
            bad += 1
            continue
        good = (r.get("date") == c["date"] and r.get("time_et") == c["time_et"]
                and r.get("away") == c["away"] and r.get("home") == c["home"])
        if good:
            ok += 1
        else:
            bad += 1
            results["mismatches"].append({"where": name, "row": c["game_id"], "detail": "field mismatch",
                                          "repo": {k: r.get(k) for k in ("date", "time_et", "away", "home")},
                                          "official": {k: c[k] for k in ("date", "time_et", "away", "home")},
                                          "src": c["source_url"]})
    missing_days = sorted({c["date"] for c in HOR if c["game_id"] not in by_id})
    rec(name, "FLAG" if missing_days else ("PASS" if bad == 0 else "MISMATCH"),
        f"{ok} rows match on date/tip/teams; {bad} mismatch; days absent from this file: {missing_days or 'none'} (F30)")


def check_horizon_engine():
    name = "horizon: data/derived/horizon_lines.json games vs official capture"
    h = load("data/derived/horizon_lines.json")
    games = h.get("games") or []
    by_key = {}
    for g in games:
        key = g.get("game_id") or f"{g.get('away')}@{g.get('home')}|{g.get('date')}"
        by_key[key] = g
    bad = ok = 0
    for c in HOR:
        g = by_key.get(c["game_id"]) or by_key.get(f"{c['away']}@{c['home']}|{c['date']}")
        if not g:
            results["mismatches"].append({"where": name, "row": c["game_id"], "detail": "missing in horizon_lines"})
            bad += 1
            continue
        probs = []
        for f in ("date", "away", "home"):
            if g.get(f) != c[f]:
                probs.append(f"{f}: repo={g.get(f)} official={c[f]}")
        tm = g.get("time_et") or g.get("tip_et") or g.get("time")
        if tm and tm != c["time_et"]:
            probs.append(f"time: repo={tm} official={c['time_et']}")
        if probs:
            bad += 1
            results["mismatches"].append({"where": name, "row": c["game_id"], "detail": "; ".join(probs), "src": c["source_url"]})
        else:
            ok += 1
    rec(name, "PASS" if bad == 0 else "MISMATCH", f"{len(HOR)} games: {ok} match on date/teams/time, {bad} differ")


def check_picks_rows():
    name = "picks: every published pick row maps to an official horizon game"
    bad = ok = 0
    for path in ("site/data/picks.json",):
        p = load(path)
        rows = find_rows(p)
        for r in rows:
            gid = (r.get("game_id") or "").split("+")[0]
            c = hor_by_id.get(gid)
            if not c:
                # window may include graded 11/06-11/12 games; only horizon dates checked here
                if (r.get("date") or "") >= "2026-11-13":
                    results["mismatches"].append({"where": path, "row": r.get("game_id"),
                                                  "detail": f"pick dated {r.get('date')} has no official horizon game"})
                    bad += 1
                continue
            if r.get("date") != c["date"] or r.get("away") != c["away"] or r.get("home") != c["home"]:
                results["mismatches"].append({"where": path, "row": r.get("game_id"), "detail": "date/teams mismatch",
                                              "src": c["source_url"]})
                bad += 1
            else:
                ok += 1
    rec(name, "PASS" if bad == 0 else "MISMATCH", f"{ok} pick rows map 1:1 to official horizon games; {bad} bad")


def check_calendar_counts():
    name = "horizon: per-day game counts vs official calendar badges"
    cb = {k: v for k, v in cap["games_per_day_calendar_badge"].items() if re.match(r"^\d{4}-\d{2}-\d{2}$", k)}
    counts = Counter(r["date"] for r in HOR)
    bad = [d for d, n in cb.items() if d >= "2026-11-14" and counts.get(d, 0) != n]
    tot = sum(counts.values())
    rec(name, "PASS" if not bad and tot == 27 else "MISMATCH",
        f"captured rows per day {dict(counts)} vs badges { {d: n for d, n in cb.items() if d >= '2026-11-14'} }; total {tot}")


# ---------------------------------------------------------------- stats (Z02)
def binom_two_sided(w, n):
    if n == 0:
        return None
    def tail_ge(k):
        return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
    if w > n / 2:
        p = 2 * tail_ge(w)
    elif w < n / 2:
        p = 2 * tail_ge(n - w)
    else:
        p = 1.0
    return min(1.0, p)


def wilson(w, n, z=1.96):
    if n == 0:
        return None
    phat = w / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return [round(center - half, 4), round(center + half, 4)]


def check_strategies():
    name = "stats: binomial p, Wilson CI, hit rate, units recomputed (site/data/validation.json)"
    v = load("site/data/validation.json")
    bad = notes = 0
    detail = []
    for s in v["strategies"]:
        w, l, pu = s["wins"], s["losses"], s["pushes"]
        n = w + l
        if n:
            p = round(binom_two_sided(w, n), 4)
            if abs(p - s["binomial_p"]) > 0.0002:
                bad += 1
                results["mismatches"].append({"where": name, "row": s["id"], "field": "binomial_p",
                                              "repo": s["binomial_p"], "recomputed": p})
            hr = round(w / n, 4)
            if abs(hr - (s["hit_rate"] or 0)) > 0.0002:
                bad += 1
                results["mismatches"].append({"where": name, "row": s["id"], "field": "hit_rate",
                                              "repo": s["hit_rate"], "recomputed": hr})
            wci = wilson(w, n)
            pub = s.get("wilson_95")
            if pub and (abs(pub[0] - wci[0]) > 0.005 or abs(pub[1] - wci[1]) > 0.005):
                bad += 1
                results["mismatches"].append({"where": name, "row": s["id"], "field": "wilson_95",
                                              "repo": pub, "recomputed": wci})
        # units: sum of graded play rows must equal the published figure
        rows = [r for r in v["graded_plays"] if r["strategy"] == s["id"]]
        tot = round(sum(r.get("units") or 0 for r in rows), 4)
        flat = round(w * (100 / 110) - l, 4) if n else 0.0
        pub_u = round(s["units_at_minus110"], 4)
        if abs(tot - pub_u) > 0.01:
            bad += 1
            results["mismatches"].append({"where": name, "row": s["id"], "field": "units_at_minus110",
                                          "repo": pub_u, "sum_of_rows": tot})
        elif abs(flat - pub_u) > 0.01:
            notes += 1
            results["notes"].append(f"{s['id']}: published units {pub_u} = sum of graded rows ({tot}) but NOT flat -110 grading ({flat}) — "
                                    f"market '{s.get('market')}' is priced differently; the metric name 'units_at_minus110' is misleading for this strategy.")
        detail.append(f"{s['id']}: n={n} p_binom={s['binomial_p']} units={pub_u}")
    rec(name, "PASS" if bad == 0 else "MISMATCH",
        f"10 strategies: {bad} recomputation mismatches; {notes} unit-label notes (see notes); " + "; ".join(detail[:4]) + " …")


def check_metrics():
    name = "stats: window metrics reproduced from docs/data/backtest.json rows"
    v = load("site/data/validation.json")
    b = load("docs/data/backtest.json")
    rows = find_rows(b)
    m = v["metrics"]
    bad = 0
    n = len(rows)
    em = [abs(r["err_model_margin"]) for r in rows]
    et = [abs(r["err_model_total"]) for r in rows]
    mae_m = round(sum(em) / n, 2)
    mae_t = round(sum(et) / n, 2)
    rmse_m = round(math.sqrt(sum(x * x for x in em) / n), 2)
    rmse_t = round(math.sqrt(sum(x * x for x in et) / n), 2)
    bias_m = round(sum(r["actual_margin_home"] - r["model_spread_home"] for r in rows) / n, 2)
    # sign convention (F27): in this file model_spread_home is the predicted HOME MARGIN
    su = sum(1 for r in rows if r["home_won"] is not None and ((r["model_spread_home"] > 0) == bool(r["home_won"])))
    su_str = f"{su}-{n - su}"
    exp = {
        "mae_margin_model": (m["mae_margin_model"], mae_m),
        "mae_total_model": (m["mae_total_model"], mae_t),
        "rmse_margin_model": (m["rmse_margin_model"], rmse_m),
        "rmse_total_model": (m["rmse_total_model"], rmse_t),
        "bias_margin_model": (m["bias_margin_model"], bias_m),
        "straight_up_model": (m["straight_up_model"], su_str),
    }
    for k, (pub, mine) in exp.items():
        ok = (pub == mine) if isinstance(pub, str) else abs(pub - mine) <= 0.011
        if not ok:
            bad += 1
            results["mismatches"].append({"where": name, "field": k, "repo": pub,
                                          "recomputed_from_backtest_rows": mine, "n": n})
    rec(name, "PASS" if bad == 0 else "MISMATCH",
        f"n={n} rows: MAE margin {mae_m} vs {m['mae_margin_model']}, MAE total {mae_t} vs {m['mae_total_model']}, "
        f"RMSE {rmse_m}/{rmse_t}, bias {bias_m}, straight-up {su_str} vs {m['straight_up_model']}; {bad} mismatches")

    # cross-ledger: the settlement ledger carries different model numbers for the same games
    s = load("integration/out/settlement.json")
    settled = {r["game_id"]: r for r in s["rows"] if r.get("settled")}
    shared = [r for r in rows if r["game_id"] in settled]
    eq = sum(1 for r in shared if abs(r["model_spread_home"] - settled[r["game_id"]]["model_margin_home"]) < 0.05)
    sm = [abs(settled[r["game_id"]]["abs_err_margin"]) for r in shared]
    results["notes"].append(
        f"cross-ledger (F26 evidence): docs/data/backtest.json model_spread_home vs integration/out/settlement.json "
        f"model_margin_home agree on {eq}/{len(shared)} shared games (same 51-game window); settlement-ledger MAE would be "
        f"{round(sum(sm)/len(sm),2)} vs published {m['mae_margin_model']}. Two engine lineages describe the same window; "
        f"each ledger is internally consistent but the pages do not label which engine produced which number.")
    st = [abs(r["abs_err_margin"]) for r in s["rows"] if r.get("settled")]
    if st:
        su2 = Counter(r["side_pick_correct"] for r in s["rows"] if r.get("settled") and r.get("side_pick_correct") is not None)
        rec("stats: settlement-ledger metrics recomputed (integration/out/settlement.json)", "NOTE",
            f"n={len(st)} settled rows: MAE margin {round(sum(st)/len(st),2)}, straight-up {su2.get(True,0)}-{su2.get(False,0)} "
            f"— different model numbers than the published metrics; see cross-ledger note (F26).")


def check_correlations():
    name = "stats: correlation register recomputed from committed team data"
    c = load("data/derived/correlations.json")
    adv = load("data/teams_advanced_2026_27.json")
    sc = load("data/teams_scoring_2026_27.json")
    A = {r["abbr"]: r for r in find_rows(adv)}
    S = {r["abbr"]: r for r in find_rows(sc)}

    # same committed inputs as scripts/compute_correlations.py (teams_advanced + teams_scoring),
    # each of which carries its own official nba.com source_url per row
    cols = {}
    for t in sorted(A):
        a, s = A[t], S[t]
        cols[t] = {
            "pace": a["pace"], "off_rtg": a["off_rtg"], "def_rtg": a["def_rtg"],
            "efg_pct": a["efg_pct"], "tov_pct": a["tov_pct"], "oreb_pct": a["oreb_pct"],
            "ast_pct": a["ast_pct"], "win_pct": a["w"] / a["gp"],
            "pts": s["pts"], "game_total": s["pts"] + s["opp_pts"],
            "fg3_pct": s["fg3_pct"], "fg3a": s["fg3a"],
        }

    def pearson(xs, ys):
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        return sxy / math.sqrt(sxx * syy)

    def p_two(r, n):
        t = r * math.sqrt((n - 2) / (1 - r * r))
        z = abs(t)
        return 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))

    bad = ok = 0
    for row in c["tier_a_empirical"]:
        key = (row["x"], row["y"])
        if row["x"] not in next(iter(cols.values())) or row["y"] not in next(iter(cols.values())):
            results["unverified"].append({"where": name, "row": f"{key}", "detail": "pair not mapped in checker"})
            continue
        xs = [cols[t][row["x"]] for t in cols]
        ys = [cols[t][row["y"]] for t in cols]
        if len(xs) < 3 or len(xs) != row["n"]:
            results["unverified"].append({"where": name, "row": f"{key}", "detail": f"n mismatch: got {len(xs)} usable rows, register n={row['n']}"})
            continue
        r = pearson(xs, ys)
        p = p_two(r, len(xs))
        if round(r, 4) == row["r"] and round(p, 5) == row["p_two_sided_approx"]:
            ok += 1
        else:
            bad += 1
            results["mismatches"].append({"where": name, "row": f"{key}", "repo": (row["r"], row["p_two_sided_approx"]),
                                          "recomputed": (round(r, 4), round(p, 5))})
    rec(name, "PASS" if bad == 0 else "MISMATCH",
        f"{ok} of {len(c['tier_a_empirical'])} Tier-A pairs reproduce exactly from teams_advanced/scoring (r and normal-approx p); {bad} differ")


check_finals()
check_finals_consistency()
check_games_completed()
check_settlement()
check_horizon_lines()
check_horizon_official_slate()
check_horizon_engine()
check_picks_rows()
check_calendar_counts()
check_strategies()
check_metrics()
check_correlations()

out = os.path.join(HERE, "checks.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=1)

fails = [c for c in results["checks"] if c["status"] in ("MISMATCH", "MISSING")]
flags = [c for c in results["checks"] if c["status"] == "FLAG"]
print(f"checks: {len(results['checks'])}  PASS: {sum(1 for c in results['checks'] if c['status']=='PASS')}  "
      f"FLAG: {len(flags)}  MISMATCH/MISSING: {len(fails)}")
for c in results["checks"]:
    print(f"  [{c['status']:8}] {c['check']}")
print(f"mismatches recorded: {len(results['mismatches'])}  explained-stale: {len(results['explained_stale'])}  "
      f"unverified: {len(results['unverified'])}  notes: {len(results['notes'])}")
print("wrote", out)
