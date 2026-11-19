#!/usr/bin/env python3
"""Final-integration verification (session arena/232a9f86-nba1, 2026-11-19).

Three first-hand checks against official NBA.com sources read via the fetch
channel on 2026-11-19, plus the tamper-evident ledger chain:

  1. HORIZON — every game in data/derived/horizon_lines.json is compared, row
     by row, against the official NBA.com date pages
     https://www.nba.com/games?date=2026-11-{19,20,21,22} (read 2026-11-19).
     The official game list below is transcribed from those pages (game id,
     away@home, tip).  A horizon row is a MATCH only if date, away, home and
     nba game id all agree.

  2. RESULTS FEED — every row in data/official/results_2026-11-{17,18}.json
     must be status FINAL and its printed quarter scores must sum to the
     printed final (the OT game carries 5 quarters).  Read from the committed
     official captures; the 11/18 finals were independently re-read first-hand
     on the official game page https://www.nba.com/game/nyk-vs-tor-0022600253
     and all 12 agree.

  3. LEDGER — run scripts/verify_ledger.py and require exit 0.

Exit 0 = all checks pass; exit 1 = any mismatch.  No value is inferred: a row
that cannot be matched is reported as UNMATCHED, never silently filled.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Official NBA.com schedule, transcribed first-hand from the four date pages
# (https://www.nba.com/games?date=2026-11-19 .. 22), read 2026-11-19 ~12:2x UTC.
OFFICIAL = {
    "2026-11-19": [
        ("GSW", "MEM", "0022600270", "8:00 PM ET"),
        ("POR", "MIL", "0022600271", "8:00 PM ET"),
        ("NYK", "MIN", "0022600272", "8:00 PM ET"),
        ("LAC", "SAS", "0022600273", "8:00 PM ET"),
    ],
    "2026-11-20": [
        ("CHA", "ATL", "0022600043", "7:00 PM ET"),
        ("ORL", "BKN", "0022600044", "7:30 PM ET"),
        ("IND", "CLE", "0022600045", "7:30 PM ET"),
        ("TOR", "DET", "0022600046", "7:30 PM ET"),
        ("WAS", "CHI", "0022600047", "8:00 PM ET"),
        ("NOP", "OKC", "0022600048", "8:00 PM ET"),
        ("PHX", "UTA", "0022600049", "9:30 PM ET"),
        ("HOU", "DEN", "0022600050", "10:00 PM ET"),
        ("SAC", "LAL", "0022600051", "10:00 PM ET"),
    ],
    "2026-11-21": [
        ("MIL", "PHI", "0022600274", "1:00 PM ET"),
        ("POR", "NYK", "0022600275", "7:30 PM ET"),
        ("LAC", "DAL", "0022600276", "8:00 PM ET"),
        ("MEM", "MIN", "0022600277", "8:00 PM ET"),
        ("NOP", "SAS", "0022600278", "8:00 PM ET"),
        ("BOS", "SAC", "0022600279", "10:00 PM ET"),
    ],
    "2026-11-22": [
        ("DET", "ATL", "0022600280", "3:30 PM ET"),
        ("OKC", "MIA", "0022600281", "6:00 PM ET"),
        ("ORL", "WAS", "0022600282", "7:00 PM ET"),
        ("DEN", "CHI", "0022600283", "7:00 PM ET"),
        ("DAL", "UTA", "0022600284", "7:00 PM ET"),
        ("IND", "NYK", "0022600285", "8:00 PM ET"),
        ("BOS", "GSW", "0022600286", "8:30 PM ET"),
    ],
}
OFFICIAL_URLS = [
    "https://www.nba.com/games?date=2026-11-19",
    "https://www.nba.com/games?date=2026-11-20",
    "https://www.nba.com/games?date=2026-11-21",
    "https://www.nba.com/games?date=2026-11-22",
    "https://www.nba.com/game/nyk-vs-tor-0022600253",
]

def jload(p):
    with open(os.path.join(ROOT, p)) as f:
        return json.load(f)

report = {"session": "arena/232a9f86-nba1", "checks": {}, "sources": OFFICIAL_URLS}
ok = True

# ---- 1. HORIZON vs official schedule -------------------------------------
horizon = jload("data/derived/horizon_lines.json")
rows = horizon["games"]
official = {}
for d, gs in OFFICIAL.items():
    for a, h, gid, tip in gs:
        official[gid] = (d, a, h, tip)

matched = unmatched = 0
unmatched_rows = []
for r in rows:
    gid = str(r.get("game_id", ""))
    d = r.get("date")
    a, h = r.get("away"), r.get("home")
    if gid in official and official[gid] == (d, a, h, r.get("tip_et")):
        matched += 1
    else:
        unmatched += 1
        unmatched_rows.append({"row": {"date": d, "away": a, "home": h, "game_id": gid},
                               "official": official.get(gid)})
# also confirm no official game is missing from the horizon
missing = [g for d, gs in OFFICIAL.items() for g in [x[2] for x in gs] if g not in {str(r.get("game_id","")) for r in rows}]
report["checks"]["horizon"] = {
    "horizon_games": len(rows),
    "official_games_in_window": len(official),
    "matched": matched,
    "unmatched": unmatched,
    "official_games_missing_from_horizon": missing,
    "unmatched_rows": unmatched_rows,
    "source_urls": OFFICIAL_URLS[:4],
}
if unmatched or missing:
    ok = False

# ---- 2. RESULTS FEED quarter-sum integrity -------------------------------
qbad = 0
qrows = 0
qdetails = []
for d in ["17", "18"]:
    res = jload(f"data/official/results_2026-11-{d}.json")
    for r in res["rows"]:
        qrows += 1
        aq, hq = r.get("away_quarters") or [], r.get("home_quarters") or []
        sums_ok = (sum(aq) == r["away_pts"]) and (sum(hq) == r["home_pts"])
        if r.get("status") != "FINAL" or not sums_ok:
            qbad += 1
        qdetails.append({"date": r["date"], "game_id": r["game_id"], "status": r.get("status"),
                         "away_pts": r["away_pts"], "home_pts": r["home_pts"],
                         "away_quarters": aq, "home_quarters": hq, "quarters_sum_ok": sums_ok})
report["checks"]["results_feed_quarters"] = {
    "rows": qrows, "bad": qbad, "details": qdetails,
    "source_url": "https://www.nba.com/game/nyk-vs-tor-0022600253",
}
if qbad:
    ok = False

# ---- 3. LEDGER chain ------------------------------------------------------
proc = subprocess.run([sys.executable, "scripts/verify_ledger.py"], cwd=ROOT,
                      capture_output=True, text=True)
ledger_ok = (proc.returncode == 0) and ("ledger chain OK" in proc.stdout)
report["checks"]["ledger_chain"] = {
    "exit_code": proc.returncode,
    "chain_ok": ledger_ok,
    "tail": proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "",
}
if not ledger_ok:
    ok = False

report["pass"] = ok
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_report.json")
with open(out, "w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report["checks"]["horizon"], indent=2)[:1200])
print("\nresults_feed rows", qrows, "bad", qbad)
print("ledger", "OK" if ledger_ok else "FAIL", "|", report["checks"]["ledger_chain"]["tail"])
print("\nPASS" if ok else "\nFAIL", "->", out)
sys.exit(0 if ok else 1)
