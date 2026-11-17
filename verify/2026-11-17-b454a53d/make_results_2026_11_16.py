#!/usr/bin/env python3
"""Build data/official/results_2026-11-16.json from the official nba.com game pages.

Every value below was read first-hand (fetch_page, 2026-11-17 UTC) from
https://www.nba.com/game/<slug>-<game_id> (LINESCORES table, GAME INFO block)
and https://www.nba.com/games?date=2026-11-16 (final scores). The script does not
infer anything: it transcribes the printed numbers and asserts that each
quarter row sums to the printed final before writing.
"""
import json, os, datetime

ROOT = "/home/user/NBA1"
READ_BY = "arena/b454a53d-nba1 (LINESCORES + GAME INFO on the official game page, fetch_page chunk 2 of 3)"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

# game_id, away, home, away_q, home_q, away_pts, home_pts, tip_et, venue, city, state, attendance, officials, slug
GAMES = [
    ("0022600245", "ORL", "BOS", [20, 30, 25, 40], [17, 24, 36, 28], 115, 105, "7:00 PM ET", "TD Garden", "Boston", "MA", 19156, "Kevin Scott, Nate Green, Matt Kallio", "orl-vs-bos"),
    ("0022600246", "CHI", "CLE", [31, 17, 31, 36], [25, 32, 31, 38], 115, 126, "7:00 PM ET", "Rocket Arena", "Cleveland", "OH", 19432, "Rodney Mott, Curtis Blair, Ray Acosta", "chi-vs-cle"),
    ("0022600247", "MEM", "WAS", [33, 26, 42, 35], [35, 34, 18, 33], 136, 120, "7:00 PM ET", "Capital One Arena", "Washington", "DC", 16307, "Sean Wright, Tyler Ricks, Mousa Dagher", "mem-vs-was"),
    ("0022600248", "PHI", "BKN", [33, 45, 27, 30], [26, 33, 36, 28], 135, 123, "7:30 PM ET", "Barclays Center", "Brooklyn", "NY", 17548, "JB DeRosa, Jacyn Goble, Jenna Reneau", "phi-vs-bkn"),
    ("0022600249", "HOU", "MIA", [15, 31, 35, 29], [29, 33, 39, 27], 110, 128, "7:30 PM ET", "Kaseya Center", "Miami", "FL", 19662, "Marat Kogut, Gediminas Petraitis, John Conley", "hou-vs-mia"),
    ("0022600250", "POR", "MIN", [26, 25, 22, 25], [26, 33, 28, 19], 98, 106, "8:00 PM ET", "Target Center", "Minneapolis", "MN", 18236, "Eric Dalen, Tyler Ford, JD Ralls", "por-vs-min"),
    ("0022600251", "GSW", "NOP", [11, 25, 29, 29], [35, 26, 32, 22], 94, 115, "8:00 PM ET", "Smoothie King Center", "New Orleans", "LA", 16624, "Michael Smith, Brian Forte, Mark Lindsay", "gsw-vs-nop"),
    ("0022600252", "PHX", "DEN", [20, 36, 34, 27], [24, 29, 29, 23], 117, 105, "9:00 PM ET", "Ball Arena", "Denver", "CO", 19520, "Nick Buchert, Dedric Taylor, Suyash Mehta", "phx-vs-den"),
]

rows = []
for gid, away, home, aq, hq, ap, hp, tip, venue, city, state, att, offs, slug in GAMES:
    assert sum(aq) == ap, f"{away} quarters {aq} sum {sum(aq)} != printed {ap}"
    assert sum(hq) == hp, f"{home} quarters {hq} sum {sum(hq)} != printed {hp}"
    src = f"https://www.nba.com/game/{slug}-{gid}"
    rows.append({
        "date": "2026-11-16", "game_id": gid, "away": away, "home": home,
        "status": "FINAL", "away_pts": ap, "home_pts": hp,
        "away_quarters": aq, "home_quarters": hq,
        "quarters_sum_check": f"away {'+'.join(map(str, aq))}={ap} \u2713, home {'+'.join(map(str, hq))}={hp} \u2713",
        "ot_periods": 0, "final_label": "Final", "tip_et": tip,
        "venue": venue, "city": f"{city}, {state}", "attendance": att, "officials": offs,
        "state_at_retrieval": "Final",
        "source_url": src,
        "source_box_score_url": f"{src}/box-score#box-score",
        "source_date_url": "https://www.nba.com/games?date=2026-11-16",
        "verified_at_utc": NOW,
        "verified_by_reads": [READ_BY],
        "independent_reads_agree": None,
    })

doc = {
    "title": "Official per-game results feed \u2014 2026-11-16 (finals verified from official game pages)",
    "captured_by": "arena/b454a53d-nba1",
    "retrieved_utc": NOW,
    "rule": ("One row per game. A row is marked FINAL only when the official game page prints Final and its "
             "LINESCORES quarters sum to the printed final (asserted per row by this script before writing). "
             "Nothing is inferred; possessions, offensive/defensive rating and pace are NOT captured for these rows and are left out."),
    "rows": rows,
    "sources": [
        "https://www.nba.com/games?date=2026-11-16",
        "https://www.nba.com/game/<slug>-<game_id> (LINESCORES, GAME INFO)",
        "https://statsdmz.nba.com/pdfs/20261116/ (gamebook PDFs linked from each game page; not parsed in this cycle)",
    ],
    "summary": {"games": len(rows), "final": sum(1 for r in rows if r["status"] == "FINAL"),
                "quarter_sum_failures": 0},
}
out = os.path.join(ROOT, "data", "official", "results_2026-11-16.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
print("wrote", out, doc["summary"], NOW)
