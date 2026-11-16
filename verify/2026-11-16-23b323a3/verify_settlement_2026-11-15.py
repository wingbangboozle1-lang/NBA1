#!/usr/bin/env python3
"""Independent re-grade of the 2026-11-15 settlement against the official finals.

This does NOT call settle_slate.py and does NOT read the settlement's own
`result` field to decide anything. It re-applies the published grading rule to
the official final scores and compares the answer with what the settlement file
claims. Two artefacts are checked:

  1. every final's quarters sum to its printed final  (the precondition)
  2. every settled single re-grades to the statement on file, and the units
     re-sum to the published total

Run: python3 verify/2026-11-16-23b323a3/verify_settlement_2026-11-15.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load = lambda p: json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

results = load("data/official/results_2026-11-15.json")
settle = load("data/settlement/settlement_2026-11-15.json")
fails = []

# 1 -- precondition: nine finals, each quarters row sums to the printed final
if len(results["rows"]) != 9:
    fails.append("expected 9 game rows, got %d" % len(results["rows"]))
for r in results["rows"]:
    if r.get("status") != "FINAL":
        fails.append("%s@%s is not FINAL" % (r["away"], r["home"]))
    for side in ("away", "home"):
        q, pts = r.get(side + "_quarters"), r.get(side + "_pts")
        if not q or sum(q) != pts:
            fails.append("%s@%s %s quarters %s != %s" % (r["away"], r["home"], side, q, pts))
    if not r.get("source_url"):
        fails.append("%s@%s has no official source_url" % (r["away"], r["home"]))

# 2 -- re-grade every settled single from the official finals
fin = {(r["away"], r["home"]): (r["away_pts"], r["home_pts"]) for r in results["rows"]}
units = 0.0
rows = []
for g in settle["singles"]:
    away, home = g["matchup"].split("@")
    team, line = g["pick_line"].rsplit(" ", 1)
    line = float(line)
    ap, hp = fin[(away, home)]
    margin = (hp - ap) if team == home else (ap - hp)
    if margin > -line:
        exp, u = "WIN", 1.00
    elif margin == -line:
        exp, u = "PUSH", 0.00
    else:
        exp, u = "LOSS", -1.10
    units += u
    ok = (exp == g["result"]) and abs(u - g["units"]) < 1e-9
    if not ok:
        fails.append("%s %s re-graded %s/%s, file says %s/%s"
                     % (g["matchup"], g["pick_line"], exp, u, g["result"], g["units"]))
    rows.append((g["matchup"], g["pick_line"], margin, -line, exp, ok))

pub = settle["summary"]
if abs(round(units, 2) - float(pub["singles_units_at_minus110"])) > 1e-9:
    fails.append("units re-sum to %.2f, file publishes %s"
                 % (units, pub["singles_units_at_minus110"]))
w = sum(1 for _, _, _, _, e, _ in rows if e == "WIN")
l = sum(1 for _, _, _, _, e, _ in rows if e == "LOSS")
p = sum(1 for _, _, _, _, e, _ in rows if e == "PUSH")
if "%d-%d-%d" % (w, l, p) != pub["record"]:
    fails.append("record re-grades %d-%d-%d, file publishes %s" % (w, l, p, pub["record"]))

print("matchup    pick        margin  line      re-graded")
for m, pl, mg, ln, e, ok in rows:
    print("  %-9s %-10s %+4d   %+6.1f    %-5s %s" % (m, pl, mg, ln, e, "OK" if ok else "MISMATCH"))
print("\nre-graded record %d-%d-%d, units %+.2f  (file: %s, %s)"
      % (w, l, p, units, pub["record"], pub["singles_units_at_minus110"]))
print("FAILURES: %d" % len(fails))
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
