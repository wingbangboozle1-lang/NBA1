#!/usr/bin/env python3
"""X01 + X02: check every stored final score against the official NBA.com values
transcribed in official_scores_2026-11-06_to_12.json, then re-derive the derived
result columns of the two backtest files. Read-only: nothing in data/ is changed.

Run from the repository root:  python3 audit/results/check_results.py
Writes audit/results/x01_x02_report.json and prints a summary.
"""
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)

official = load("audit/results/official_scores_2026-11-06_to_12.json")
off = {g["game_id"]: g for g in official["games"]}
report = {"checked_utc": "2026-11-14", "x01_games_completed": {}, "x02_backtests": {}, "mismatches": []}

def mismatch(where, game_id, field, stored, official_value):
    report["mismatches"].append({"where": where, "game_id": game_id, "field": field,
                                 "stored": stored, "official": official_value})

# ---- X01: data/raw/games_completed.json (51 rows) -------------------------------
raw = load("data/raw/games_completed.json")
cols = raw["cols"]
ix = {c: i for i, c in enumerate(cols)}
seen = set()
ok = 0
for r in raw["rows"]:
    gid = r[ix["game_id"]]
    seen.add(gid)
    o = off.get(gid)
    if o is None:
        mismatch("data/raw/games_completed.json", gid, "game_id", gid, "not on official pages")
        continue
    row_ok = True
    for f_stored, f_off in [("date", "date"), ("away", "away"), ("away_pts", "away_pts"),
                            ("home", "home"), ("home_pts", "home_pts")]:
        if r[ix[f_stored]] != o[f_off]:
            row_ok = False
            mismatch("data/raw/games_completed.json", gid, f_stored, r[ix[f_stored]], o[f_off])
    ot_official = 1 if o["status"].startswith("Final/OT") else 0
    if bool(r[ix["ot"]]) != bool(ot_official):
        row_ok = False
        mismatch("data/raw/games_completed.json", gid, "ot", r[ix["ot"]], ot_official)
    neutral_official = 1 if "Neutral" in o["status"] else 0
    if int(r[ix["neutral"]]) != neutral_official:
        row_ok = False
        mismatch("data/raw/games_completed.json", gid, "neutral", r[ix["neutral"]], neutral_official)
    ok += row_ok
missing_from_repo = sorted(set(off) - seen)
report["x01_games_completed"] = {
    "rows_in_repo": len(raw["rows"]), "rows_official": len(off), "rows_matching_all_fields": ok,
    "official_games_absent_from_repo": missing_from_repo,
}

# ---- X02a: data/derived/backtest.json (14 rows) ----------------------------------
bt = load("data/derived/backtest.json")
ok = 0
for r in bt["rows"]:
    o = off.get(r["game_id"])
    if o is None:
        mismatch("data/derived/backtest.json", r["game_id"], "game_id", r["game_id"], "not on official pages"); continue
    row_ok = True
    exp_matchup = f'{o["away"]}@{o["home"]}'
    if r["matchup"] != exp_matchup:
        row_ok = False; mismatch("data/derived/backtest.json", r["game_id"], "matchup", r["matchup"], exp_matchup)
    exp_total = o["away_pts"] + o["home_pts"]
    if r["actual_total"] != exp_total:
        row_ok = False; mismatch("data/derived/backtest.json", r["game_id"], "actual_total", r["actual_total"], exp_total)
    exp_margin = o["home_pts"] - o["away_pts"]          # home minus away (repo convention, checked on row 1)
    if r["actual_margin"] != exp_margin:
        row_ok = False; mismatch("data/derived/backtest.json", r["game_id"], "actual_margin", r["actual_margin"], exp_margin)
    exp_winner = o["home"] if o["home_pts"] > o["away_pts"] else o["away"]
    if r["actual_winner"] != exp_winner:
        row_ok = False; mismatch("data/derived/backtest.json", r["game_id"], "actual_winner", r["actual_winner"], exp_winner)
    if bool(r["ot"]) != o["status"].startswith("Final/OT"):
        row_ok = False; mismatch("data/derived/backtest.json", r["game_id"], "ot", r["ot"], o["status"])
    ok += row_ok
report["x02_backtests"]["data_derived_backtest_14"] = {"rows": len(bt["rows"]), "rows_matching": ok,
    "summary_stated_n_games": bt["summary"]["n_games"]}

# ---- X02b: docs/data/backtest.json (51 rows, Build B) ----------------------------
b2 = load("docs/data/backtest.json")
ok = 0
for r in b2["rows"]:
    gid = r["game_id"]
    o = off.get(gid)
    if o is None:
        mismatch("docs/data/backtest.json", gid, "game_id", gid, "not on official pages"); continue
    row_ok = True
    for f_stored, f_off in [("away", "away"), ("home", "home"), ("away_pts", "away_pts"), ("home_pts", "home_pts"), ("date", "date")]:
        if r[f_stored] != o[f_off]:
            row_ok = False; mismatch("docs/data/backtest.json", gid, f_stored, r[f_stored], o[f_off])
    exp_total = o["away_pts"] + o["home_pts"]
    if r["actual_total"] != exp_total:
        row_ok = False; mismatch("docs/data/backtest.json", gid, "actual_total", r["actual_total"], exp_total)
    exp_margin = o["home_pts"] - o["away_pts"]
    if r["actual_margin_home"] != exp_margin:
        row_ok = False; mismatch("docs/data/backtest.json", gid, "actual_margin_home", r["actual_margin_home"], exp_margin)
    if r["home_won"] != (1 if o["home_pts"] > o["away_pts"] else 0):
        row_ok = False; mismatch("docs/data/backtest.json", gid, "home_won", r["home_won"], int(o["home_pts"] > o["away_pts"]))
    ok += row_ok

# Re-derive headline metrics from the stored row fields (not from the stored summary).
rows = b2["rows"]
n = len(rows)
su_model = sum(1 for r in rows if (1 if r["p_home_model"] >= 0.5 else 0) == r["home_won"])
su_ref = sum(1 for r in rows if (1 if r["p_home_ref"] >= 0.5 else 0) == r["home_won"])
mae_margin_model = sum(abs(r["err_model_margin"]) for r in rows) / n
mae_total_model = sum(abs(r["err_model_total"]) for r in rows) / n
brier_model = sum((r["p_home_model"] - r["home_won"]) ** 2 for r in rows) / n
brier_ref = sum((r["p_home_ref"] - r["home_won"]) ** 2 for r in rows) / n
stated = b2["metrics"]
report["x02_backtests"]["docs_data_backtest_51"] = {
    "rows": n, "rows_matching_official_fields": ok,
    "rederived": {
        "straight_up_model": f"{su_model}-{n - su_model}", "straight_up_model_stated": stated["straight_up_model"],
        "straight_up_ref": f"{su_ref}-{n - su_ref}", "straight_up_ref_stated": stated["straight_up_ref"],
        "mae_margin_model": round(mae_margin_model, 2), "mae_margin_model_stated": stated["mae_margin_model"],
        "mae_total_model": round(mae_total_model, 2), "mae_total_model_stated": stated["mae_total_model"],
        "brier_model": round(brier_model, 4), "brier_model_stated": stated["brier_model"],
        "brier_ref": round(brier_ref, 4), "brier_ref_stated": stated["brier_ref"],
    },
    "note": "Re-derived from each row's stored p_home_*, err_* and home_won fields. Errors are compared to stored values at the printed precision; a mismatch is recorded, not corrected.",
}

report["mismatch_count"] = len(report["mismatches"])
out = os.path.join(ROOT, "audit/results/x01_x02_report.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print(json.dumps({k: v for k, v in report.items() if k != "mismatches"}, indent=1))
print("mismatches:", report["mismatch_count"])
for m in report["mismatches"][:40]:
    print("  ", m)
