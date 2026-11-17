#!/usr/bin/env python3
"""Grade the two 2026-11-16 SGP tickets that scripts/settle_slate.py leaves UNSETTLED
(it cannot read player box scores). Inputs are the official nba.com box-score rows read
first-hand (fetch_page, 2026-11-17 UTC). Rule copied from data/settlement/settlement_2026-11-16.json
rules.sgp: a leg whose player did not play is VOID and removed; the remaining legs settle at the
frozen price; any losing leg loses the stake (1.10, paper -110). Writes
data/settlement/sgp_grades_2026-11-16.json and appends ONE hash-chained ledger entry that
commits to that file. Existing ledger entries and the settlement file are not modified.
"""
import hashlib, json, os, datetime

ROOT = "/home/user/NBA1"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
settle = json.load(open(os.path.join(ROOT, "data/settlement/settlement_2026-11-16.json")))
sgp_in = [g for g in settle["sgp_candidates"] if g["date"] == "2026-11-16"]

# Official box-score evidence (player: appeared?, points) — transcribed from the box-score rows.
BOX = {
    ("ORL@BOS", "Paolo Banchero"): {"appeared": False, "pts": None, "box": "https://www.nba.com/game/orl-vs-bos-0022600245/box-score",
        "note": "No row in either team table (active or DNP). ORL team PTS 115 reconciles to the 113 listed points + 2 from A. Cain's row without him."},
    ("ORL@BOS", "Jayson Tatum"): {"appeared": True, "pts": 24, "box": "https://www.nba.com/game/orl-vs-bos-0022600245/box-score",
        "note": "BOS table: 36:03 min, 24 PTS."},
    ("MEM@WAS", "Ty Jerome"): {"appeared": False, "pts": None, "box": "https://www.nba.com/game/mem-vs-was-0022600247/box-score",
        "note": "No row in the MEM table. MEM rows sum to 136 (team final) without him. AP recap on the same page: out with a sore right hip."},
    ("MEM@WAS", "Anthony Davis"): {"appeared": True, "pts": 23, "box": "https://www.nba.com/game/mem-vs-was-0022600247/box-score",
        "note": "WAS table: 34:41 min, 23 PTS."},
}
LINE = {}
out = []
for g in sgp_in:
    legs_out = []
    leg_units_ok = []
    for leg in g["legs"]:
        name, rest = leg.split(" (")
        team_part, side_line = rest.split(") ", 1)
        side, line = side_line.rsplit(" ", 1)
        line = float(line)
        ev = BOX[(g["game"], name)]
        if not ev["appeared"]:
            res = "VOID"
        else:
            if side == "OVER":
                res = "WIN" if ev["pts"] > line else ("PUSH" if ev["pts"] == line else "LOSS")
            else:
                res = "WIN" if ev["pts"] < line else ("PUSH" if ev["pts"] == line else "LOSS")
        legs_out.append({"leg": leg, "player": name, "side": side, "line": line,
                         "official_pts": ev["pts"], "appeared": ev["appeared"], "result": res,
                         "source_box_score_url": ev["box"], "note": ev["note"]})
    live = [l for l in legs_out if l["result"] != "VOID"]
    if any(l["result"] == "LOSS" for l in live):
        ticket, units = "LOSS", -1.10
    elif live and all(l["result"] == "WIN" for l in live):
        ticket, units = "WIN", None  # payout at frozen price; not needed here
    else:
        ticket, units = "UNSETTLED", None
    out.append({"date": "2026-11-16", "game": g["game"], "kind": g["kind"], "legs": legs_out,
                "frozen_price_joint_prob_rho": g["frozen_price_joint_prob_rho"],
                "result": ticket, "units": units,
                "price_convention": "paper -110: a losing ticket loses the 1.10 stake",
                "sources": sorted({l["source_box_score_url"] for l in legs_out} | {"https://www.nba.com/games?date=2026-11-16"})})

assert [o["result"] for o in out] == ["LOSS", "LOSS"], out
doc = {
    "title": "SGP grading record — 2026-11-16 (player legs graded from official box scores)",
    "graded_by": "arena/b454a53d-nba1 (verify/2026-11-17-b454a53d/grade_sgp_2026_11_16.py)",
    "graded_at_utc": NOW,
    "why": "scripts/settle_slate.py cannot read box scores and leaves SGP tickets UNSETTLED. This record grades them from the official box-score rows, under the frozen rule in settlement_2026-11-16.json.",
    "rule": settle["rules"]["sgp"],
    "tickets": out,
    "summary": {"tickets": len(out), "lost": sum(o["result"] == "LOSS" for o in out),
                "won": sum(o["result"] == "WIN" for o in out),
                "units": round(sum(o["units"] or 0 for o in out), 2)},
    "validation_note": "MODEL OUTPUT — UNVALIDATED, unfunded, zero-stake paper output.",
}
path = os.path.join(ROOT, "data/settlement/sgp_grades_2026-11-16.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=1, ensure_ascii=False); fh.write("\n")
print("wrote", path, doc["summary"])

# --- append exactly one hash-chained ledger entry (same chain rule as settle_slate.py) ---
lp = os.path.join(ROOT, "data/ledger/ledger.json")
L = json.load(open(lp, encoding="utf-8"))
sha = lambda b: hashlib.sha256(b).hexdigest()
n = L["entries"][-1]["entry"]
rel = "data/settlement/sgp_grades_2026-11-16.json"
e = {"entry": n + 1, "type": "sgp_grading_record", "at_utc": NOW, "file": rel,
     "sha256": sha(open(path, "rb").read()),
     "graded_from": ["data/settlement/settlement_2026-11-16.json"],
     "summary": doc["summary"], "prev": L["head"]}
L["entries"].append(e)
L["head"] = sha(json.dumps(e, sort_keys=True).encode())
with open(lp, "w", encoding="utf-8") as fh:
    json.dump(L, fh, indent=1, ensure_ascii=False); fh.write("\n")
print("appended ledger entry", e["entry"], "head", L["head"])
