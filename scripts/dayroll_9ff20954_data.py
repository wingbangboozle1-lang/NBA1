#!/usr/bin/env python3
"""dayroll_9ff20954_data.py — write the first-hand official reads of 2026-11-19.

Every value below was read first-hand this session through the web-fetch
channel from the official page named in each row's source_url. Nothing is
inferred. Quarter scores are asserted to sum to the printed final before
any file is written (the script refuses otherwise).

Outputs:
  data/official/results_2026-11-17.json   5 finals with LINESCORES quarters
  data/official/results_2026-11-18.json  12 finals with LINESCORES quarters
  data/official/standings_2026-11-19_9ff20954.json  30 rows + HOME/ROAD identity
  data/official/teams_inputs_2026-11-19_9ff20954.json  advanced table (30 rows)
  data/raw/official_schedule_capture_2026-11-19.json  11/19..11/22 fixtures (26)
  data/official/injury_2026-11-19_1230AM_9ff20954.json  newest edition rows
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = "2026-11-19T06:00Z"
BY = "arena/9ff20954-nba1"

def w(path, doc):
    p = os.path.join(ROOT, path)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False); fh.write("\n")
    print("wrote", path)

# ---------------- results: 11/17 (5 finals, all Final on the date page) ----
# (game_id, away, home, away_pts, home_pts, away_q, home_q, ot, venue, city, tip)
R17 = [
    ("0022600253", "NYK", "TOR", 111, 102, [23,31,26,31], [29,21,33,19], 0,
     "Scotiabank Arena", "Toronto, ON", "7:30 PM ET"),
    ("0022600255", "DET", "SAS", 105, 93, [26,29,23,27], [33,21,18,21], 0,
     "Frost Bank Center", "San Antonio, TX", "8:00 PM ET"),
    ("0022600254", "POR", "MIN", 105, 106, [17,31,31,26], [29,20,30,27], 0,
     "Target Center", "Minneapolis, MN", "8:00 PM ET"),
    ("0022600257", "UTA", "LAC", 132, 107, [35,23,30,44], [29,33,24,21], 0,
     "Intuit Dome", "Inglewood, CA", "10:30 PM ET"),
    ("0022600256", "CHA", "LAL", 114, 118, [34,32,28,17,3], [30,29,22,30,7], 1,
     "Crypto.com Arena", "Los Angeles, CA", "11:00 PM ET"),
]
# ---------------- results: 11/18 (12 finals) ------------------------------
R18 = [
    ("0022600259", "HOU", "IND", 119, 104, [39,23,31,26], [28,18,30,28], 0,
     "Gainbridge Fieldhouse", "Indianapolis, IN", "7:00 PM ET"),
    ("0022600261", "PHI", "ORL", 121, 116, [27,37,28,29], [40,29,28,19], 0,
     "Kia Center", "Orlando, FL", "7:00 PM ET"),
    ("0022600260", "MIL", "MIA", 130, 137, [23,25,38,44], [34,40,38,25], 0,
     "Kaseya Center", "Miami, FL", "7:00 PM ET"),
    ("0022600258", "MEM", "CLE", 124, 121, [30,41,29,24], [37,35,27,22], 0,
     "Rocket Arena", "Cleveland, OH", "7:00 PM ET"),
    ("0022600262", "CHI", "BKN", 137, 107, [37,39,35,26], [21,30,26,30], 0,
     "Barclays Center", "Brooklyn, NY", "7:30 PM ET"),
    ("0022600263", "WAS", "TOR", 103, 99, [29,20,29,25], [23,24,32,20], 0,
     "Scotiabank Arena", "Toronto, ON", "7:30 PM ET"),
    ("0022600267", "GSW", "DAL", 94, 116, [25,24,23,22], [35,27,30,24], 0,
     "American Airlines Center", "Dallas, TX", "8:00 PM ET"),
    ("0022600265", "ATL", "OKC", 117, 112, [31,33,19,34], [29,22,32,29], 0,
     "Paycom Center", "Oklahoma City, OK", "8:00 PM ET"),
    ("0022600264", "DET", "NOP", 122, 109, [31,36,25,30], [31,29,26,23], 0,
     "Smoothie King Center", "New Orleans, LA", "8:00 PM ET"),
    ("0022600266", "BOS", "DEN", 101, 105, [30,31,19,21], [24,25,31,25], 0,
     "Ball Arena", "Denver, CO", "9:30 PM ET"),
    ("0022600269", "PHX", "SAC", 128, 107, [36,29,34,29], [31,29,24,23], 0,
     "Golden 1 Center", "Sacramento, CA", "10:00 PM ET"),
    ("0022600268", "UTA", "LAL", 109, 97, [29,27,22,31], [34,20,22,21], 0,
     "Crypto.com Arena", "Los Angeles, CA", "10:00 PM ET"),
]

def results_doc(date, rows):
    out = []
    for gid, aw, hm, ap, hp, aq, hq, ot, venue, city, tip in rows:
        assert sum(aq) == ap, f"{gid} away quarters {aq} != {ap}"
        assert sum(hq) == hp, f"{gid} home quarters {hq} != {hp}"
        slug = f"{aw.lower()}-vs-{hm.lower()}-{gid}"
        out.append({
            "date": date, "game_id": gid, "away": aw, "home": hm,
            "status": "FINAL", "away_pts": ap, "home_pts": hp,
            "away_quarters": aq, "home_quarters": hq,
            "quarters_sum_check": f"away {'+'.join(map(str,aq))}={ap} ✓, home {'+'.join(map(str,hq))}={hp} ✓",
            "ot_periods": ot, "final_label": "Final/OT" if ot else "Final",
            "tip_et": tip, "venue": venue, "city": city,
            "attendance": None, "officials": None,
            "state_at_retrieval": "Final/OT" if ot else "Final",
            "source_url": f"https://www.nba.com/game/{slug}",
            "source_box_score_url": f"https://www.nba.com/game/{slug}/box-score#box-score",
            "source_date_url": f"https://www.nba.com/games?date={date}",
            "verified_at_utc": NOW,
            "verified_by_reads": [
                f"{BY}: LINESCORES on the official game page (fetch channel), quarters sum to final",
                f"{BY}: date page https://www.nba.com/games?date={date} prints Final with the same score",
            ],
            "independent_reads_agree": True,
            "independent_read_scope": "status, away_pts, home_pts (date page + game page agree); quarter scores read once (game page LINESCORES)",
        })
    return {
        "title": f"Official per-game results feed — {date} (finals verified from official game pages)",
        "captured_by": BY, "retrieved_utc": NOW,
        "rule": "One row per game. A row is marked FINAL only when the official game page prints Final and its LINESCORES quarters sum to the printed final (asserted per row by this script before writing). Nothing is inferred.",
        "rows": out,
    }

w("data/official/results_2026-11-17.json", results_doc("2026-11-17", R17))
w("data/official/results_2026-11-18.json", results_doc("2026-11-18", R18))

# ---------------- standings (30 rows, verbatim) -----------------------------
# (conf, rank, abbr, w, l, pct, gb, conf, div, home, road, neutral, ot, last10, streak)
STD = [
    ("East",1,"PHI",13,3,".813","--","13-3","4-1","6-2","7-1","0-0","0-0","8-2","W 4"),
    ("East",2,"BOS",11,4,".733","1.5","10-2","4-0","6-1","5-3","0-0","1-0","7-3","L 2"),
    ("East",3,"DET",10,4,".714","2","8-3","0-0","3-2","7-2","0-0","1-0","7-3","W 2"),
    ("East",4,"MIA",9,6,".600","3.5","5-2","1-1","5-3","4-3","0-0","1-0","8-2","W 6"),
    ("East",5,"ATL",9,6,".600","3.5","8-2","4-1","3-3","6-3","0-0","0-1","7-3","W 2"),
    ("East",6,"NYK",8,6,".571","4","8-6","3-3","4-3","4-3","0-0","1-0","7-3","W 2"),
    ("East",7,"CLE",8,8,".500","5","6-5","2-0","6-3","2-5","0-0","1-0","4-6","L 1"),
    ("East",8,"ORL",6,8,".429","6","4-5","0-2","1-5","5-3","0-0","0-1","5-5","L 1"),
    ("East",9,"TOR",5,10,".333","7.5","4-6","0-4","2-6","3-4","0-0","0-1","2-8","L 6"),
    ("East",10,"IND",5,10,".333","7.5","3-6","0-1","2-5","3-4","0-1","0-0","3-7","L 2"),
    ("East",11,"WAS",5,11,".313","8","5-8","2-3","2-5","3-6","0-0","0-1","2-8","W 1"),
    ("East",12,"CHA",4,10,".286","8","4-7","2-2","3-4","1-6","0-0","0-1","1-9","L 3"),
    ("East",13,"CHI",4,10,".286","8","3-9","1-1","1-4","3-6","0-0","1-0","3-7","W 1"),
    ("East",14,"BKN",3,11,".214","9","2-9","0-3","1-5","2-6","0-0","0-1","3-7","L 3"),
    ("East",15,"MIL",1,14,".067","11.5","1-11","1-2","1-7","0-7","0-0","0-0","0-10","L 11"),
    ("West",1,"LAL",13,3,".813","--","7-3","5-1","6-2","7-1","0-0","1-0","9-1","L 1"),
    ("West",2,"SAS",12,3,".800","0.5","11-2","2-1","5-3","7-0","0-0","1-0","9-1","L 1"),
    ("West",3,"HOU",12,4,".750","1","6-3","2-1","7-1","5-3","0-0","0-0","7-3","W 1"),
    ("West",4,"MIN",11,4,".733","1.5","7-2","3-0","7-2","4-2","0-0","0-1","8-2","W 2"),
    ("West",5,"MEM",11,4,".733","1.5","7-3","1-1","3-4","8-0","0-0","0-1","6-4","W 4"),
    ("West",6,"POR",9,5,".643","3","9-5","4-2","3-2","6-3","0-0","0-0","6-4","L 2"),
    ("West",7,"DEN",8,5,".615","3.5","5-5","0-2","3-3","4-2","1-0","1-0","7-3","W 1"),
    ("West",8,"OKC",9,6,".600","3.5","6-5","1-2","5-1","4-5","0-0","0-0","5-5","L 1"),
    ("West",9,"DAL",8,7,".533","4.5","4-5","1-3","6-2","2-5","0-0","0-0","5-5","W 1"),
    ("West",10,"GSW",8,7,".533","4.5","6-7","3-2","6-1","2-6","0-0","1-0","6-4","L 4"),
    ("West",11,"PHX",7,7,".500","5","5-7","3-2","5-4","2-3","0-0","0-0","6-4","W 2"),
    ("West",12,"NOP",5,11,".313","8","4-8","1-1","4-7","1-4","0-0","2-1","3-7","L 1"),
    ("West",13,"LAC",4,9,".308","7.5","3-7","1-4","4-4","0-5","0-0","0-1","3-7","L 1"),
    ("West",14,"UTA",3,13,".188","10","3-11","0-2","1-7","2-6","0-0","0-2","2-8","W 2"),
    ("West",15,"SAC",1,13,".071","11","1-11","0-3","0-9","1-4","0-0","0-0","1-9","L 7"),
]
rows = []
for c,r,a,ww,ll,pct,gb,cf,dv,hm,rd,nt,ot,l10,st in STD:
    rows.append({"conference":c,"rank":r,"abbr":a,"w":ww,"l":ll,"win_pct":pct,"gb":gb,
                 "conf_rec":cf,"div_rec":dv,"home":hm,"road":rd,"neutral":nt,"ot":ot,
                 "last10":l10,"streak":st})
def wl(s):
    x,y = s.split("-"); return int(x), int(y)
hw = sum(wl(r["home"])[0] for r in rows); hl = sum(wl(r["home"])[1] for r in rows)
rw = sum(wl(r["road"])[0] for r in rows); rl = sum(wl(r["road"])[1] for r in rows)
assert hw == rl and hl == rw, f"standings identity failed: home {hw}-{hl} road {rw}-{rl}"
assert sum(r["w"] for r in rows) == sum(r["l"] for r in rows)
w("data/official/standings_2026-11-19_9ff20954.json", {
    "title": "NBA 2026-27 regular-season standings, read 2026-11-19",
    "captured_by": BY, "retrieved_utc": NOW,
    "source_url": "https://www.nba.com/standings",
    "read_note": "Verbatim transcription of the 30 standings rows on https://www.nba.com/standings, read first-hand on 2026-11-19 after every 11/18 final was published. No value was adjusted, inferred or filled in.",
    "columns": ["conference","rank","abbr","w","l","win_pct","gb","conf_rec","div_rec","home","road","neutral","ot","last10","streak"],
    "rows": rows,
    "identity_checks": {
        "home_wins": hw, "home_losses": hl, "road_wins": rw, "road_losses": rl,
        "global_ok": hw == rl and hl == rw,
        "note": "closed-system identity: home wins == road losses and home losses == road wins",
    },
    "measured_home_court_anchor": {
        "home_win_rate": round(hw/(hw+hl), 4), "home_wins": hw, "home_games": hw+hl,
        "source_url": "https://www.nba.com/standings",
    },
})

# ---------------- advanced team table (30 rows, verbatim) -------------------
# (team, gp, w, l, min, off, def, net, astpct, astto, astratio, oreb, dreb, reb, tov, efg, ts, pace, pie, poss)
ADV = [
    ("Los Angeles Lakers",15,13,2,725.0,121.6,113.7,7.8,58.2,1.47,17.4,33.9,64.3,49.8,16.5,58.1,62.4,100.14,53.8,1511),
    ("Philadelphia 76ers",16,13,3,768.0,114.5,111.8,2.7,64.7,2.08,18.7,28.4,72.0,50.3,12.6,53.4,57.7,99.88,51.4,1600),
    ("Houston Rockets",16,12,4,768.0,121.1,112.1,9.0,65.4,1.89,19.4,36.7,68.7,53.2,15.0,55.6,59.7,97.41,55.3,1558),
    ("San Antonio Spurs",15,12,3,725.0,118.1,107.0,11.1,65.6,2.23,19.4,33.5,71.3,52.5,12.6,53.0,57.1,98.35,56.0,1487),
    ("Boston Celtics",15,11,4,725.0,117.0,106.0,11.0,66.7,1.85,19.1,32.9,67.7,50.3,14.9,54.6,57.9,96.76,54.7,1460),
    ("Memphis Grizzlies",15,11,4,725.0,120.6,111.9,8.7,67.6,1.82,19.8,34.2,69.8,52.7,15.7,56.9,61.1,100.27,54.3,1516),
    ("Minnesota Timberwolves",15,11,4,725.0,114.5,104.0,10.5,60.0,1.58,17.5,34.7,69.3,52.5,15.8,54.8,57.4,101.23,55.0,1528),
    ("Detroit Pistons",14,10,4,682.0,114.9,108.9,6.0,67.9,1.97,19.6,30.0,66.6,48.6,14.2,54.5,58.4,98.78,54.2,1406),
    ("Atlanta Hawks",15,9,6,725.0,112.8,110.8,1.9,71.1,2.03,20.2,32.8,69.6,49.9,14.6,52.8,55.7,103.71,49.0,1566),
    ("Miami Heat",15,9,6,725.0,116.9,116.7,0.3,70.3,2.06,20.0,30.8,68.3,49.4,14.0,55.4,59.1,102.19,50.8,1546),
    ("Oklahoma City Thunder",15,9,6,720.0,113.0,108.7,4.4,55.5,1.73,16.8,31.6,68.9,50.9,13.5,52.2,55.9,99.17,53.5,1488),
    ("Portland Trail Blazers",14,9,5,672.0,116.2,110.2,6.0,63.8,1.55,17.8,33.0,70.1,51.9,16.1,54.8,59.2,100.71,52.5,1410),
    ("Cleveland Cavaliers",16,8,8,773.0,117.5,115.5,2.0,64.7,1.99,19.3,30.9,68.7,50.4,13.7,55.8,59.1,100.01,51.0,1610),
    ("Dallas Mavericks",15,8,7,720.0,112.3,113.4,-1.1,65.5,1.64,18.6,33.1,65.9,49.5,16.3,53.6,57.3,99.97,49.4,1501),
    ("Denver Nuggets",13,8,5,629.0,114.3,113.8,0.5,64.9,1.89,19.1,30.4,66.8,49.4,14.2,54.3,58.6,98.02,52.5,1287),
    ("Golden State Warriors",15,8,7,725.0,113.4,112.8,0.6,70.5,1.70,19.1,32.7,67.9,50.3,16.2,53.9,58.1,99.41,50.3,1503),
    ("New York Knicks",14,8,6,677.0,114.8,109.0,5.8,68.6,1.83,18.9,37.1,72.2,54.5,15.2,52.4,56.3,94.87,53.6,1342),
    ("Phoenix Suns",14,7,7,672.0,115.6,116.8,-1.2,65.8,1.94,19.6,30.5,63.1,46.8,14.4,55.4,58.4,98.89,49.4,1382),
    ("Orlando Magic",14,6,8,677.0,111.3,114.0,-2.7,68.5,1.65,19.1,30.7,70.6,50.5,16.4,53.9,57.4,97.84,48.5,1375),
    ("Indiana Pacers",15,5,10,720.0,110.7,113.6,-2.9,67.2,1.92,19.7,24.4,68.1,46.8,14.3,53.9,57.4,100.90,49.4,1511),
    ("New Orleans Pelicans",16,5,11,783.0,111.7,118.9,-7.1,60.7,1.54,17.1,30.1,68.5,48.9,15.3,51.8,57.5,101.30,46.4,1652),
    ("Toronto Raptors",15,5,10,725.0,113.7,113.1,0.5,67.6,2.07,19.3,34.3,66.4,49.0,13.7,52.0,55.1,98.09,48.4,1478),
    ("Washington Wizards",16,5,11,778.0,109.9,117.1,-7.1,60.1,1.62,17.1,29.2,65.6,47.9,14.6,51.7,56.3,99.46,46.3,1612),
    ("Charlotte Hornets",14,4,10,677.0,103.1,113.7,-10.6,62.6,1.14,15.9,36.2,72.8,53.4,19.9,48.6,52.5,96.43,43.5,1360),
    ("Chicago Bulls",14,4,10,677.0,111.1,119.1,-8.0,67.9,1.61,18.7,31.6,64.6,48.0,16.5,52.7,56.8,103.80,46.2,1464),
    ("LA Clippers",13,4,9,629.0,111.4,117.0,-5.6,68.5,1.55,19.0,29.2,65.9,47.6,17.2,54.9,58.8,99.74,47.4,1306),
    ("Brooklyn Nets",14,3,11,677.0,110.5,119.0,-8.4,64.6,1.39,17.4,31.9,68.0,49.6,17.5,53.5,57.5,99.51,45.2,1404),
    ("Utah Jazz",15,2,13,730.0,107.2,115.9,-8.7,64.2,1.50,17.7,29.3,69.7,49.2,16.3,52.1,55.9,99.95,46.4,1522),
    ("Milwaukee Bucks",15,1,14,720.0,106.7,119.7,-13.0,65.1,1.46,17.4,31.1,64.5,47.6,16.8,51.4,54.7,101.00,42.4,1515),
    ("Sacramento Kings",14,1,13,672.0,106.9,120.4,-13.5,64.8,1.47,18.2,28.4,69.3,48.0,17.2,52.8,56.3,100.93,42.5,1411),
]
for r in ADV:
    assert r[1] == r[2] + r[3], f"G1 fail {r[0]}"
    assert abs(r[7] - (r[5] - r[6])) <= 0.25, f"G2 fail {r[0]}"
w("data/official/teams_inputs_2026-11-19_9ff20954.json", {
    "title": "Official team-stat inputs read first-hand on 2026-11-19 (advanced table; traditional + opponent read the same cycle, stored separately)",
    "captured_by": BY, "retrieved_utc": NOW,
    "capture_method": "official pages read live through the web-fetch channel",
    "sources": {
        "advanced": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
        "traditional": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season",
        "opponent": "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season",
    },
    "columns_advanced": ["team","gp","w","l","min","off_rtg","def_rtg","net_rtg","ast_pct","ast_to","ast_ratio","oreb_pct","dreb_pct","reb_pct","tov_pct","efg_pct","ts_pct","pace","pie","poss"],
    "advanced": [list(r) for r in ADV],
    "advanced_note": "all 30 rows transcribed from the official page as printed. PACE is possessions per 48 minutes as the official page defines it; POSS is the season total possessions.",
    "opponent_note": "the opponent page is captured for the possession-consistent cross-check only; the model uses the SAME league-average possession baseline for both sides, so it reads off_rtg/def_rtg from the advanced page rather than recomputing one side from a different column set",
})

# ---------------- schedule capture 11/19..11/22 (26 games) ------------------
# (date, game_id, away, home, tip_et, cup_label, away_rec, home_rec)
SCHED = [
    ("2026-11-19","0022600270","GSW","MEM","8:00 PM ET",None,"8-7","11-4"),
    ("2026-11-19","0022600271","POR","MIL","8:00 PM ET",None,"9-5","1-14"),
    ("2026-11-19","0022600272","NYK","MIN","8:00 PM ET",None,"8-6","11-4"),
    ("2026-11-19","0022600273","LAC","SAS","8:00 PM ET",None,"4-9","12-3"),
    ("2026-11-20","0022600043","CHA","ATL","7:00 PM ET","Emirates NBA Cup East Group C","4-10","9-6"),
    ("2026-11-20","0022600044","ORL","BKN","7:30 PM ET","Emirates NBA Cup East Group A","6-8","3-11"),
    ("2026-11-20","0022600045","IND","CLE","7:30 PM ET","Emirates NBA Cup East Group B","5-10","8-8"),
    ("2026-11-20","0022600046","TOR","DET","7:30 PM ET","Emirates NBA Cup East Group A","5-10","10-4"),
    ("2026-11-20","0022600047","WAS","CHI","8:00 PM ET","Emirates NBA Cup East Group C","5-11","4-10"),
    ("2026-11-20","0022600048","NOP","OKC","8:00 PM ET","Emirates NBA Cup West Group B","5-11","9-6"),
    ("2026-11-20","0022600049","PHX","UTA","9:30 PM ET","Emirates NBA Cup West Group A","7-7","3-13"),
    ("2026-11-20","0022600050","HOU","DEN","10:00 PM ET","Emirates NBA Cup West Group A","12-4","8-5"),
    ("2026-11-20","0022600051","SAC","LAL","10:00 PM ET","Emirates NBA Cup West Group C","1-13","13-3"),
    ("2026-11-21","0022600274","MIL","PHI","1:00 PM ET",None,"1-14","13-3"),
    ("2026-11-21","0022600275","POR","NYK","7:30 PM ET",None,"9-5","8-6"),
    ("2026-11-21","0022600276","LAC","DAL","8:00 PM ET",None,"4-9","8-7"),
    ("2026-11-21","0022600277","MEM","MIN","8:00 PM ET",None,"11-4","11-4"),
    ("2026-11-21","0022600278","NOP","SAS","8:00 PM ET",None,"5-11","12-3"),
    ("2026-11-21","0022600279","BOS","SAC","10:00 PM ET",None,"11-4","1-13"),
    ("2026-11-22","0022600280","DET","ATL","3:30 PM ET",None,"10-4","9-6"),
    ("2026-11-22","0022600281","OKC","MIA","6:00 PM ET",None,"9-6","9-6"),
    ("2026-11-22","0022600282","ORL","WAS","7:00 PM ET",None,"6-8","5-11"),
    ("2026-11-22","0022600283","DEN","CHI","7:00 PM ET",None,"8-5","4-10"),
    ("2026-11-22","0022600284","DAL","UTA","7:00 PM ET",None,"8-7","3-13"),
    ("2026-11-22","0022600285","IND","NYK","8:00 PM ET",None,"5-10","8-6"),
    ("2026-11-22","0022600286","BOS","GSW","8:30 PM ET",None,"11-4","8-7"),
]
srows = []
for d,gid,aw,hm,tip,cup,ar,hr in SCHED:
    srows.append({"date":d,"game_id":gid,"away":aw,"home":hm,"tip_et":tip,
                  "venue":None,"city":None,"cup_label":cup,"away_record":ar,"home_record":hr,
                  "records_as_of":f"{NOW} (official standings, same cycle)",
                  "source_game_url":f"https://www.nba.com/game/{aw.lower()}-vs-{hm.lower()}-{gid}"})
w("data/raw/official_schedule_capture_2026-11-19.json", {
    "captured_by": BY, "captured_utc": NOW, "captured_on_utc_date": "2026-11-19",
    "capture_method": "official pages read live through the web-fetch channel (first-hand, not inherited)",
    "scope": "rolling window 2026-11-19 .. 2026-11-22 (today + up to 3 days, 26 games)",
    "window_rule": "today (2026-11-19) + the next 3 days. The 11/19 slate tips at 8:00 PM ET, still ahead of this capture; the max-3-days-ahead rule bounds the far edge at 11/22.",
    "games_per_day": {"2026-11-19":4,"2026-11-20":9,"2026-11-21":6,"2026-11-22":7},
    "sources": ["https://www.nba.com/games?date=2026-11-19","https://www.nba.com/games?date=2026-11-20",
                "https://www.nba.com/games?date=2026-11-21","https://www.nba.com/games?date=2026-11-22",
                "https://www.nba.com/standings"],
    "cols": ["date","game_id","away","home","tip_et","venue","city","cup_label","away_record","home_record","records_as_of","source_game_url"],
    "rows": srows,
    "venue_note": "venue/city left null: not read for future fixtures this cycle; the originator does not consume them.",
})

# ---------------- injury edition 11/19 12:30 AM (newest on the index) -------
INJ = [
    ("11/19/2026","08:00 (ET)","GSW@MEM","Golden State Warriors","","","NOT YET SUBMITTED"),
    ("11/19/2026","08:00 (ET)","GSW@MEM","Memphis Grizzlies","","","NOT YET SUBMITTED"),
    ("11/19/2026","08:00 (ET)","LAC@SAS","LA Clippers","Beal, Bradley","Out","Injury/Illness - Right Knee Injury Management"),
    ("11/19/2026","08:00 (ET)","LAC@SAS","LA Clippers","Ingram, Brandon","Out","Injury/Illness - Right Heel Surgery"),
    ("11/19/2026","08:00 (ET)","LAC@SAS","LA Clippers","Martinelli, Nick","Out","G League - Two-Way"),
    ("11/19/2026","08:00 (ET)","LAC@SAS","LA Clippers","Miller, Jordan","Out","Injury/Illness - Left Rotator Cuff Surgery"),
    ("11/19/2026","08:00 (ET)","LAC@SAS","San Antonio Spurs","Brown, Maliq","Out","G League - Two-Way"),
    ("11/19/2026","08:00 (ET)","LAC@SAS","San Antonio Spurs","Gillespie, Ja'Kobi","Out","G League - Two-Way"),
    ("11/19/2026","08:00 (ET)","LAC@SAS","San Antonio Spurs","Harper, Dylan","Out","Injury/Illness - Left Hip Soreness"),
    ("11/19/2026","08:00 (ET)","LAC@SAS","San Antonio Spurs","Harris, Tobias","Out","Injury/Illness - Left Calf Strain"),
    ("11/19/2026","08:00 (ET)","LAC@SAS","San Antonio Spurs","Quaintance, Jayden","Out","Injury/Illness - Right Knee Surgery"),
    ("11/19/2026","08:00 (ET)","NYK@MIN","Minnesota Timberwolves","Beringer, Joan","Available","Injury/Illness - Face Mask"),
    ("11/19/2026","08:00 (ET)","NYK@MIN","Minnesota Timberwolves","Clark, Jaylen","Out","Injury/Illness - Right Hamstring Strain"),
    ("11/19/2026","08:00 (ET)","NYK@MIN","Minnesota Timberwolves","DiVincenzo, Donte","Out","Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("11/19/2026","08:00 (ET)","NYK@MIN","Minnesota Timberwolves","Edwards, Anthony","Out","Injury/Illness - Right Knee Arthroscopy"),
    ("11/19/2026","08:00 (ET)","POR@MIL","Portland Trail Blazers","Avdija, Deni","Questionable","Injury/Illness - Left Foot Inflammation / Soreness"),
    ("11/19/2026","08:00 (ET)","POR@MIL","Portland Trail Blazers","Camara, Toumani","Questionable","Injury/Illness - Abdominal Soreness"),
    ("11/19/2026","08:00 (ET)","POR@MIL","Portland Trail Blazers","Carlson, Branden","Available","Injury/Illness - Face Mask"),
    ("11/19/2026","08:00 (ET)","POR@MIL","Portland Trail Blazers","Krejci, Vit","Out","Injury/Illness - Left Ankle Fracture"),
    ("11/19/2026","08:00 (ET)","POR@MIL","Portland Trail Blazers","Morant, Ja","Out","Injury/Illness - Left Hamstring Strain"),
    ("11/19/2026","08:00 (ET)","POR@MIL","Portland Trail Blazers","Sharpe, Shaedon","Out","Injury/Illness - Right Meniscus Surgery"),
    ("11/19/2026","08:00 (ET)","POR@MIL","Portland Trail Blazers","Williams III, Robert","Out","Rest"),
    ("11/19/2026","08:00 (ET)","POR@MIL","Portland Trail Blazers","Youngblood, Chris","Out","Injury/Illness - Right Heel Contusion / Bone Bruise"),
    ("11/19/2026","08:00 (ET)","POR@MIL","Milwaukee Bucks","","","NOT YET SUBMITTED"),
]
# The text render also carried two rows whose matchup column was blank in the
# render (Kuminga/Pullin, GSW) — team attribution is NOT asserted from the
# render; they are recorded separately as unattributed, never guessed.
INJ_UNATTRIBUTED = [
    ("Kuminga, Jonathan","Questionable","Injury/Illness - Right Shoulder Contusion"),
    ("Pullin, Zyon","Questionable","Injury/Illness - Right Quadriceps Contusion"),
]
w("data/official/injury_2026-11-19_1230AM_9ff20954.json", {
    "title": "Official injury report edition 2026-11-19 12:30 AM ET (newest on the official index at read time)",
    "captured_by": BY, "retrieved_utc": NOW,
    "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_12_30AM.pdf",
    "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "index_read_note": "The official index page, read first-hand this cycle, listed November 19 editions 12:00 AM, 12:15 AM and 12:30 AM ET; 12:30 AM is the newest listed. The PDF was read through the web-fetch text render, not byte-exact: the render dropped the matchup cell on two rows (recorded unattributed below) and collapsed the 11/20 NOT YET SUBMITTED block. See flag F-9FF-01.",
    "revision_time_et": "11/19/2026 12:30 AM ET (printed on the official PDF)",
    "retrieval_time_utc": NOW,
    "rows": [{"game_date":d,"game_time":t,"matchup":m,"team":tm,"player":p,"status":s,"reason":r}
             for d,t,m,tm,p,s,r in INJ],
    "unattributed_rows": [{"player":p,"status":s,"reason":r,
                           "note":"matchup/team cell blank in the text render; NOT attributed (never guessed)"}
                          for p,s,r in INJ_UNATTRIBUTED],
    "future_dates": "All 11/20 matchups print NOT YET SUBMITTED in this edition (CHA@ATL, IND@CLE, ORL@BKN, TOR@DET, NOP@OKC, WAS@CHI, PHX@UTA, HOU@DEN, SAC@LAL).",
})
print("ALL DATA FILES WRITTEN")
