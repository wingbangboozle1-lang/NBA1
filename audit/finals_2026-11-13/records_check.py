#!/usr/bin/env python3
"""X04 — post-2026-11-13 records for the 18 teams that played on 11/13.

derived  = pre-11/13 record (data/games.json, as_of_retrieval 2026-11-13) + W/L from the verified finals
official = record printed on the official nba.com schedule card, where the card was read in capture.json
           (values transcribed from the fetch_page output of https://www.nba.com/schedule)
A derived record that disagrees with an official card is reported as FAIL.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
fin = json.load(open(os.path.join(ROOT, "data", "verified", "finals_2026-11-13.json")))["rows"]
games = json.load(open(os.path.join(ROOT, "data", "games.json")))["games"]

ABBR = {"New York Knicks": "NYK", "Indiana Pacers": "IND", "Milwaukee Bucks": "MIL", "Orlando Magic": "ORL",
        "Cleveland Cavaliers": "CLE", "Miami Heat": "MIA", "Atlanta Hawks": "ATL", "Chicago Bulls": "CHI",
        "Memphis Grizzlies": "MEM", "New Orleans Pelicans": "NOP", "Utah Jazz": "UTA", "Houston Rockets": "HOU",
        "Golden State Warriors": "GSW", "San Antonio Spurs": "SAS", "Portland Trail Blazers": "POR",
        "Sacramento Kings": "SAC", "Oklahoma City Thunder": "OKC", "LA Clippers": "LAC"}
pre = {}
for g in games:
    if g["date"] == "2026-11-13":
        pre[ABBR[g["away"]]] = g["away_record"]
        pre[ABBR[g["home"]]] = g["home_record"]
# official cards read from https://www.nba.com/schedule (cards dated 11/14–11/15); None = card not read in this capture
official = {"NYK": "6-6", "IND": "5-8", "CLE": "6-7", "MIA": "6-6", "MEM": "8-4", "NOP": "4-9", "HOU": "10-3",
            "UTA": "1-12", "SAS": "11-2", "CHI": "2-9", "LAC": "3-8",
            "MIL": None, "ORL": None, "ATL": None, "GSW": None, "POR": None, "SAC": None, "OKC": None}
# nba.com game-page recap text (official page) also states MIL 1-12 ("the Bucks (1-12)")
rows, failed = [], 0
wl = {}
for r in fin:
    a, h = r["away"], r["home"]
    if r["away_pts"] > r["home_pts"]:
        wl[a] = "W"; wl[h] = "L"
    else:
        wl[a] = "L"; wl[h] = "W"
for team in sorted(wl):
    w, l = (int(x) for x in pre[team].split("-"))
    d = f"{w+1}-{l}" if wl[team] == "W" else f"{w}-{l+1}"
    off = official.get(team)
    ok = (off is None) or (off == d)
    if not ok: failed += 1
    rows.append({"team": team, "pre_11_13": pre[team], "result_11_13": wl[team], "derived_post_11_13": d,
                 "official_card": off, "agrees": ok if off else "not read"})
out = {"rows": rows, "teams": len(rows), "official_cards_read": sum(1 for x in official.values() if x),
       "failed": failed, "pre_source": "data/games.json (as_of_retrieval 2026-11-13)",
       "official_source": "https://www.nba.com/schedule"}
json.dump(out, open(os.path.join(HERE, "records.json"), "w"), indent=1)
for x in rows: print(x)
print(f"\n{len(rows)} teams, {out['official_cards_read']} official cards read, {failed} disagreements")
sys.exit(1 if failed else 0)
