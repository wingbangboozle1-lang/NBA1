"""Spot-check of the repo's 2026-11-15 results feed against the official nba.com games page.

Official values were read on 2026-11-16 (~14:20-14:25 UTC) from
https://www.nba.com/games?date=2026-11-15 (page 1 and page 2 of the fetch).
Official final scores are transcribed from that page as (away_pts, home_pts).
Quarter scores are NOT on that page and are therefore not compared.
"""
import json, sys

OFFICIAL = {  # matchup (away@home) -> (game_id, official status text, away_pts, home_pts, official game URL)
    "IND@PHI": ("0022600236", "Final", 124, 131, "https://www.nba.com/game/ind-vs-phi-0022600236"),
    "LAL@PHX": ("0022600237", "Final", 131, 123, "https://www.nba.com/game/lal-vs-phx-0022600237"),
    "CHA@LAC": ("0022600238", "Final", 105, 113, "https://www.nba.com/game/cha-vs-lac-0022600238"),
    "SAS@UTA": ("0022600239", "Final", 110, 102, "https://www.nba.com/game/sas-vs-uta-0022600239"),
    "DAL@BOS": ("0022600240", "Final", 94, 131, "https://www.nba.com/game/dal-vs-bos-0022600240"),
    "NYK@TOR": ("0022600241", "Final/OT", 112, 108, "https://www.nba.com/game/nyk-vs-tor-0022600241"),
    "HOU@WAS": ("0022600242", "Final", 147, 119, "https://www.nba.com/game/hou-vs-was-0022600242"),
    "ATL@MIL": ("0022600243", "Final", 113, 106, "https://www.nba.com/game/atl-vs-mil-0022600243"),
    "OKC@SAC": ("0022600244", "Final", 125, 103, "https://www.nba.com/game/okc-vs-sac-0022600244"),
}

repo = json.load(open("data/official/results_2026-11-15.json"))
rows = {f"{r['away']}@{r['home']}": r for r in repo["rows"]}

out = ["| Matchup | Game ID | Official page (nba.com) | Repo status | Repo score | Result |", "|---|---|---|---|---|---|"]
mism = 0
for m, (gid, st, a, h, url) in OFFICIAL.items():
    r = rows.get(m)
    if r is None:
        out.append(f"| {m} | {gid} | {st} {a}-{h} | (missing row) | — | MISMATCH |"); mism += 1; continue
    ok = r["status"] == "FINAL" and (r["away_pts"], r["home_pts"]) == (a, h) and r["game_id"] == gid
    if not ok: mism += 1
    repo_txt = f"{r['status']} {r['away_pts']}-{r['home_pts']}" if r["away_pts"] is not None else f"{r['status']} (no score)"
    out.append(f"| [{m}]({url}) | {gid} | {st} {a}-{h} | {repo_txt} | {'' if r['away_pts'] is None else 'ok'} | {'MATCH' if ok else 'STALE / MISMATCH'} |")
print("\n".join(out))
print(f"\nmismatches or stale rows: {mism} of {len(OFFICIAL)}")
sys.exit(0)
