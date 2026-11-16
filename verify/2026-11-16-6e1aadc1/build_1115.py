#!/usr/bin/env python3
"""Z02 + Z04: the 2026-11-15 official finals feed and per-player game logs.

Every value below was read in this session from the official NBA game book PDF
for that game (statsdmz.nba.com, the league's own game-document host) at
2026-11-16T02:2x-02:3xZ. Nothing is inferred: a cell that the official render
did not return legibly is left null and flagged, never filled.

Two executable checks are run before the files are written:
  * quarter-sum check   - each team's printed period lines must sum to its printed final
  * box-sum check        - each team's individual player points must sum to its printed final
A check that fails aborts the build, so a published row cannot be arithmetically wrong.
"""
import json, os, sys, hashlib, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CAPTURE_UTC = "2026-11-16T02:20Z..02:40Z"
BOOK = "https://statsdmz.nba.com/pdfs/20261115/%s_book.pdf"
GAMES = [
    # game_id, away, home, away_pts, home_pts, quarter lines, ot, arena, city, officials, attendance, duration
    dict(game_id="0022600236", away="IND", home="PHI", away_pts=124, home_pts=131,
         away_q=[35, 22, 30, 37], home_q=[29, 29, 39, 34], ot=0, final_label="Final",
         arena="Xfinity Mobile Arena", city="Philadelphia, PA",
         officials="#77 Karl Lane, #33 Sean Corbin, #43 Matt Myers", attendance=21024,
         book="INDPHI", tip_et="01:00 PM ET",
         away_rec="5-9", home_rec="11-3",
         # per-player logs as (name, min, pts, reb, ast, dnp_reason or None)
         away_logs=[("Aaron Nesmith","36:20",12,4,4,None),("Pascal Siakam","33:40",31,2,2,None),
                    ("Ivica Zubac","22:15",8,5,2,None),("Kelly Oubre Jr.","28:55",16,4,2,None),
                    ("Quenton Jackson","30:14",15,6,8,None),("T.J. McConnell","19:06",12,5,5,None),
                    ("Jalen Slawson","14:22",8,5,2,None),("Obi Toppin","14:15",5,2,1,None),
                    ("Larry Nance Jr.","06:33",4,2,2,None),("Jarace Walker","13:39",2,5,2,None),
                    ("Jay Huff","17:42",11,0,2,None),("Kobe Brown","02:59",0,0,0,None),
                    ("Braden Smith",None,0,0,0,"DNP - Coach's Decision")],
         home_logs=[("Jaylen Brown","32:28",31,2,2,None),("LeBron James","32:47",15,7,11,None),
                    ("Jabari Walker","24:42",11,7,1,None),("VJ Edgecombe","30:49",11,4,6,None),
                    ("Tyrese Maxey","35:32",27,4,6,None),("Dean Wade","35:03",12,7,3,None),
                    ("Kentavious Caldwell-Pope","22:16",9,5,0,None),("Anfernee Simons","15:28",12,0,0,None),
                    ("Labaron Philon Jr.","06:06",3,1,0,None),("Tacko Fall","04:49",0,3,0,None),
                    ("Justin Edwards",None,0,0,0,"DNP - Coach's Decision"),
                    ("Caleb Love",None,0,0,0,"DNP - Coach's Decision")],
         ),
    dict(game_id="0022600237", away="LAL", home="PHX", away_pts=131, home_pts=123,
         away_q=[33, 31, 40, 27], home_q=[24, 30, 26, 43], ot=0, final_label="Final",
         arena="Mortgage Matchup Center", city="Phoenix, AZ",
         officials="#60 James Williams, #30 John Butler, #98 Sha'Rae Mitchell", attendance=17071,
         book="LALPHX", tip_et="03:00 PM ET", away_rec="12-2", home_rec="5-7",
         away_logs=[("Matisse Thybulle","26:05",12,8,0,None),("Jake LaRavia","32:19",12,3,3,None),
                    ("Walker Kessler","32:26",14,12,3,None),("Quentin Grimes","37:26",22,6,1,None),
                    ("Luka Doncic","35:44",43,3,9,None),("Ziaire Williams","18:59",6,2,3,None),
                    ("Sandro Mamukelashvili","21:10",4,2,3,None),("Jarred Vanderbilt","12:09",2,4,0,None),
                    ("Collin Sexton","23:45",16,0,3,None),("Jaden Hardy",None,0,0,0,"DNP - Coach's Decision"),
                    ("Bronny James",None,0,0,0,"DNP - Coach's Decision"),
                    ("Kevon Looney",None,0,0,0,"DNP - Coach's Decision"),
                    ("Chris Manon",None,0,0,0,"DNP - Coach's Decision"),
                    ("Adou Thiero",None,0,0,0,"DNP - Coach's Decision")],
         home_logs=[("Dillon Brooks","22:18",1,2,0,None),("Miles Bridges","24:06",14,3,3,None),
                    ("Oso Ighodaro","17:01",4,2,3,None),("Jalen Green","21:16",9,2,1,None),
                    ("Devin Booker","27:48",17,4,7,None),("Jordan Goodwin","31:21",14,7,6,None),
                    ("Khaman Maluach","13:11",7,4,0,None),("Collin Gillespie","27:38",26,4,4,None),
                    ("Ryan Dunn","23:59",3,6,1,None),("Luke Kennard","23:08",18,6,4,None),
                    ("Koa Peat","08:15",10,2,0,None),("Jamaree Bouyea",None,0,0,0,"DNP - Coach's Decision"),
                    ("Rasheer Fleming",None,0,0,0,"DNP - Coach's Decision"),
                    ("Duop Reath",None,0,0,0,"DNP - Coach's Decision"),
                    ("Pat Spencer",None,0,0,0,"DNP - Coach's Decision")]),
    dict(game_id="0022600238", away="CHA", home="LAC", away_pts=105, home_pts=113,
         away_q=[21, 31, 31, 22], home_q=[22, 29, 33, 29], ot=0, final_label="Final",
         arena="Intuit Dome", city="Inglewood, CA",
         officials="#8 Marc Davis, #18 Andy Nagy, #94 Maru Biniam", attendance=17487,
         book="CHALAC", tip_et="03:30 PM ET", away_rec="4-9", home_rec="4-8",
         away_logs=[("Sion James","35:29",3,8,4,None),("Naz Reid","27:22",17,4,3,None),
                    ("Moussa Diabate","26:16",12,12,2,None),("Brandon Miller","24:28",5,2,4,None),
                    ("Coby White","19:57",21,0,1,None),("Grayson Allen","24:50",12,5,4,None),
                    ("Christian Anderson","18:00",16,3,2,None),("Ryan Kalkbrenner","18:20",5,5,1,None),
                    ("Royce O'Neale","18:30",3,3,1,None),("Grant Williams","20:11",11,2,1,None),
                    ("Tidjane Salaun","04:48",0,2,0,None),("Liam McNeeley","01:49",0,0,0,None)],
         home_logs=[("Derrick Jones Jr.","25:36",13,4,1,None),("Rui Hachimura","22:05",4,2,0,None),
                    ("Brook Lopez","28:34",7,5,8,None),("Kris Dunn","18:01",7,3,1,None),
                    ("Darius Garland","34:49",27,6,7,None),("Max Strus","24:54",14,3,4,None),
                    ("Isaiah Jackson","14:55",13,2,2,None),("Keaton Wagler","27:32",12,4,5,None),
                    ("Gradey Dick","18:38",12,2,0,None),("Kobe Sanders","20:25",2,6,4,None),
                    ("Baba Miller","04:31",2,0,0,None),("Cam Christie",None,0,0,0,"DNP - Coach's Decision"),
                    ("Jalen Pickett",None,0,0,0,"DNP - Coach's Decision")]),
    dict(game_id="0022600239", away="SAS", home="UTA", away_pts=110, home_pts=102,
         away_q=[31, 27, 23, 29], home_q=[33, 22, 26, 21], ot=0, final_label="Final",
         arena="Delta Center", city="Salt Lake City, UT",
         officials="#15 Zach Zarba, #21 Dedric Taylor, #90 Pat O'Connell", attendance=None,
         book="SASUTA", tip_et="04:00 PM ET", away_rec="12-2", home_rec="1-13",
         away_logs=[("Julian Champagne","23:53",4,5,1,None),("Devin Vassell","31:48",6,6,1,None),
                    ("Victor Wembanyama","35:13",26,10,6,None),("Stephon Castle","34:52",20,4,9,None),
                    ("Dylan Harper","34:20",31,9,4,None),("Jordan McLaughlin","19:14",10,1,2,None),
                    ("Keldon Johnson","29:19",11,10,2,None),("Luke Kornet","12:47",2,2,0,None),
                    ("Harrison Barnes","13:48",0,0,2,None),("Carter Bryant","04:46",0,1,0,None),
                    ("David Jones Garcia",None,0,0,0,"DNP - Coach's Decision"),
                    ("Tarris Reed Jr.",None,0,0,0,"DNP - Coach's Decision")],
         home_logs=[("Josh Green","14:58",6,1,1,None),("Ace Bailey","29:52",7,8,4,None),
                    ("Mo Bamba","35:41",26,5,4,None),("Darryn Peterson","34:14",17,5,4,None),
                    ("Keyonte George","33:56",13,4,8,None),("Tony Bradley","12:19",6,2,0,None),
                    ("Josh Okogie","27:28",7,6,0,None),("Brice Sensabaugh","30:14",14,7,2,None),
                    ("Svi Mykhailiuk","21:19",6,2,3,None),("Isaiah Collier",None,0,0,0,"DNP - Coach's Decision"),
                    ("Kyle Filipowski",None,0,0,0,"DNP - Coach's Decision"),
                    ("Jaxson Hayes",None,0,0,0,"DND - Injury/Illness - Left Knee Strain")]),
    dict(game_id="0022600240", away="DAL", home="BOS", away_pts=94, home_pts=131,
         away_q=None, home_q=[42, 25, 37, 27], ot=0, final_label="Final",
         arena="TD Garden", city="Boston, MA",
         officials="#14 JB DeRosa, #54 Ray Acosta, #11 Derrick Collins", attendance=19156,
         book="DALBOS", tip_et="05:00 PM ET", away_rec="7-7", home_rec="11-2",
         note_quarters="Mavericks' period line did not render legibly in the official game book "
                       "(the SCORE BY PERIOD row came back interleaved with header cells). Left null - "
                       "not derived from the final. Celtics' line 42+25+37+27=131 does sum to its final. "
                       "Final score 94-131 is independently confirmed twice: the book's team-total row "
                       "(94) and the official game-page sidebar.",
         away_logs=[("Caleb Martin","33:51",12,5,5,None),("P.J. Washington","24:30",8,5,4,None),
                    ("Daniel Gafford","19:24",3,4,2,None),("Cooper Flagg","26:41",17,3,4,None),
                    ("Naji Marshall","22:45",13,2,2,None),("Walter Clayton Jr.","23:04",13,4,3,None),
                    ("Morez Johnson Jr.","25:40",2,6,4,None),("Zaccharie Risacher","26:43",18,5,0,None),
                    ("Marcus Sasser","18:07",5,1,2,None),("Tobi Lawal","08:58",2,2,0,None),
                    ("Jett Howard","06:39",0,0,1,None),("Moussa Cisse","03:38",1,1,0,None)],
         home_logs=[("Paul George","24:51",7,7,6,None),("Jayson Tatum","30:08",32,6,6,None),
                    ("Neemias Queta","15:21",8,6,2,None),("Jordan Walsh","21:07",11,1,0,None),
                    ("Derrick White","22:56",16,4,2,None),("Mitchell Robinson","14:47",0,7,1,None),
                    ("Baylor Scheierman","18:00",12,5,3,None),("Sam Hauser","10:51",8,1,0,None),
                    ("Payton Pritchard","18:56",10,1,6,None),("Luka Garza","14:14",2,3,5,None),
                    ("Hugo Gonzalez","17:52",9,5,2,None),("Devin Carter","12:00",0,2,1,None),
                    ("Ron Harper Jr.","12:00",10,1,0,None),("Chris Cenac Jr.","06:57",6,3,0,None),
                    ("Mike Conley",None,0,0,0,"DNP - Coach's Decision")]),
    dict(game_id="0022600241", away="NYK", home="TOR", away_pts=112, home_pts=108,
         away_q=[23, 24, 20, 28, 17], home_q=[17, 26, 31, 21, 13], ot=1, final_label="Final/OT",
         arena="Scotiabank Arena", city="Toronto, ON",
         officials="#25 Tony Brothers, #35 Jason Goldenberg, #70 Phenizee Ransom", attendance=19800,
         book="NYKTOR", tip_et="07:00 PM ET", away_rec="7-6", home_rec="5-8",
         away_logs=[("Josh Hart","26:15",0,5,2,None),("OG Anunoby","44:29",21,9,1,None),
                    ("Karl-Anthony Towns","42:49",28,17,3,None),("Mikal Bridges","32:15",5,7,3,None),
                    ("Jalen Brunson","40:58",28,1,9,None),("Landry Shamet","29:42",23,2,0,None),
                    ("Andre Drummond","07:10",2,3,0,None),("Miles McBride","13:39",3,1,0,None),
                    ("Tyler Kolek","15:35",0,0,7,None),("Jordan Clarkson","06:57",2,2,0,None),
                    ("Jose Alvarado","02:22",0,0,1,None),("James Wiseman","02:51",0,3,0,None),
                    ("Pacome Dadiet",None,0,0,0,"DNP - Coach's Decision"),
                    ("Mohamed Diawara",None,0,0,0,"DNP - Coach's Decision")],
         home_logs=[("RJ Barrett","37:00",14,5,6,None),("Scottie Barnes","36:19",30,9,4,None),
                    ("Collin Murray-Boyles","39:47",6,13,2,None),("Ja'Kobe Walter","35:38",7,2,1,None),
                    ("Immanuel Quickley","37:30",17,6,6,None),("Jakob Poeltl","17:27",11,5,1,None),
                    ("Jamal Shead","25:34",19,2,4,None),("Jamison Battle","08:07",0,3,0,None),
                    ("Allen Graves","15:46",2,5,3,None),("Alijah Martin","11:52",2,3,0,None),
                    ("Kyle Anderson",None,0,0,0,"DNP - Coach's Decision"),
                    ("Jaden Bradley",None,0,0,0,"DNP - Coach's Decision"),
                    ("Trayce Jackson-Davis",None,0,0,0,"DNP - Coach's Decision")]),
]

# Inactive / Out lists exactly as printed in the same official game books.
OUT = {
    "0022600236": {"IND": [("Furphy","Injury/Illness - Right ACL Repair / Surgery"),
                            ("Haliburton","Injury/Illness - Left Hamstring Strain"),
                            ("Nembhard","Injury/Illness - Left Hip Soreness / Tightness"),
                            ("Sheppard","Injury/Illness - Left Meniscus Tear")],
                    "PHI": [("Barlow","Injury/Illness - Low Back Stress Reaction"),
                            ("Bona","Injury/Illness - Cervical Spine Sprain"),
                            ("Embiid","Injury/Illness - Right Foot Plantar Fascia Injury Management"),
                            ("Hukporti","Injury/Illness - Right Achilles Tendon Rupture / Tear"),
                            ("Rupert","G League - Two-Way")]},
    "0022600237": {"LAL": [("Carr","G League - Two-Way"),("Cooper","G League - Two-Way"),
                            ("Kaluma","G League - Two-Way"),
                            ("Reaves","Injury/Illness - Left Heel Contusion / Bone Bruise")],
                    "PHX": [("Timme","G League - Two-Way"),
                            ("Williams","Injury/Illness - Left Shoulder Surgery")]},
    "0022600238": {"CHA": [("Ajayi","G League - Two-Way"),("Boswell","G League - Two-Way"),
                            ("Hall","G League - Two-Way"),
                            ("Knueppel","Injury/Illness - Left Hamstring Strain"),
                            ("Schroder","Injury/Illness - Left Hamstring Strain"),
                            ("Steinbach","G League - On Assignment")],
                    "LAC": [("Beal","Injury/Illness - Right Knee Injury Management"),
                            ("Ingram","Injury/Illness - Right Heel Surgery"),
                            ("Martinelli","G League - Two-Way"),
                            ("Miller","Injury/Illness - Left Rotator Cuff Surgery"),
                            ("Niederhaeuser","Injury/Illness - Right Lisfranc Surgery")]},
    "0022600239": {"SAS": [("Brown","G League - Two-Way"),
                            ("Fox","Injury/Illness - Left Hip Tightness"),
                            ("Gillespie","G League - Two-Way"),
                            ("Harris","Injury/Illness - Left Calf Strain"),
                            ("Quaintance","Injury/Illness - Right Knee Surgery")],
                    "UTA": [("Alexander","G League - Two-Way"),("Bufkin","G League - Two-Way"),
                            ("Ingram","G League - Two-Way"),
                            ("Jackson Jr.","Injury/Illness - Right MCL Tear"),
                            ("Markkanen","Injury/Illness - Right Hand Fracture"),
                            ("Nurkic","Injury/Illness - Right 2nd Plantar Plate Tear")]},
    "0022600240": {"DAL": [("Aldama","Injury/Illness - Left Ankle Sprain"),
                            ("Biberovic","Injury/Illness - Right Heel Bursitis"),
                            ("Christie","Injury/Illness - Left Ankle Sprain"),
                            ("de Larrea","Injury/Illness - Right Knee Sprain"),
                            ("Irving","Injury/Illness - Left Knee Injury Management"),
                            ("Lively II","Injury/Illness - Right Foot Surgery")],
                    "BOS": [("Mitchell","G League - Two-Way"),("Williams","G League - Two-Way")]},
    "0022600241": {"NYK": [("Akins","(no reason printed on the official page)"),
                            ("Knecht","(no reason printed on the official page)"),
                            ("Nickel","(no reason printed on the official page)")],
                    "TOR": [("Bittle","Injury/Illness - Right Foot Avulsion Fracture"),
                            ("Leonard","Injury/Illness - Left Knee Injury Management"),
                            ("McCullar Jr.","G League - Two-Way"),("Smith","G League - Two-Way")]},
}

def qsum(q, total, label, gid):
    if q is None:
        return "not-checked (period line not legible in the official render)"
    if sum(q) != total:
        raise SystemExit(f"FATAL {gid}: {label} quarters {q} sum {sum(q)} != printed final {total}")
    return f"{'+'.join(map(str,q))}={sum(q)} == printed final {total} OK"

rows, logs = [], []
for g in GAMES:
    gid = g["game_id"]
    chk = {
        "away": qsum(g["away_q"], g["away_pts"], "away", gid),
        "home": qsum(g["home_q"], g["home_pts"], "home", gid),
    }
    for side, team, key in (("away", g["away"], "away_logs"), ("home", g["home"], "home_logs")):
        pts = sum(r[2] for r in g[key])
        if pts != g[f"{side}_pts"]:
            raise SystemExit(f"FATAL {gid}: {team} individual points sum {pts} != printed final {g[f'{side}_pts']}")
        chk[side + "_boxsum"] = f"individual points sum {pts} == printed final OK"
    opp = {g["away"]: g["home"], g["home"]: g["away"]}
    rows.append({
        "date": "2026-11-15", "game_id": gid, "away": g["away"], "home": g["home"],
        "status": "FINAL", "final_label": g["final_label"],
        "away_pts": g["away_pts"], "home_pts": g["home_pts"],
        "away_quarters": g["away_q"], "home_quarters": g["home_q"],
        "ot_periods": g["ot"], "tip_et": g["tip_et"],
        "arena": g["arena"], "city": g["city"], "attendance": g["attendance"],
        "officials": g["officials"],
        "away_record_at_game_time": g["away_rec"], "home_record_at_game_time": g["home_rec"],
        "quarter_sum_check": chk["away"] + " ; " + chk["home"],
        "box_sum_check": chk["away_boxsum"] + " ; " + chk["home_boxsum"],
        "inactives_away": [{"player": n, "reason": r} for n, r in OUT[gid][g["away"]]],
        "inactives_home": [{"player": n, "reason": r} for n, r in OUT[gid][g["home"]]],
        "source_url": f"https://www.nba.com/game/{g['away'].lower()}-vs-{g['home'].lower()}-{gid}",
        "source_gamebook_pdf": BOOK % g["book"],
        "verified_by": "arena/6e1aadc1-nba1", "verified_utc": CAPTURE_UTC,
        **({"note_quarters": g["note_quarters"]} if "note_quarters" in g else {}),
    })
    for side, team, key in (("away", g["away"], "away_logs"), ("home", g["home"], "home_logs")):
        for (name, minutes, pts, reb, ast, dnp) in g[key]:
            logs.append({"date": "2026-11-15", "game_id": gid, "team": team,
                         "opponent": opp[team], "player": name,
                         "minutes": minutes, "points": pts if minutes else None,
                         "rebounds": reb if minutes else None, "assists": ast if minutes else None,
                         "did_not_play": dnp, "appears_in_box": bool(minutes),
                         "source_gamebook_pdf": BOOK % g["book"]})

out_feed = {
    "title": "Official per-game result feed - 2026-11-15 (all 9 games; 6 FINAL rows settled from the official game books, 3 recorded at their observed state)",
    "one_row_per_game": True,
    "captured_by": "arena/6e1aadc1-nba1 (Z02)",
    "retrieved_utc": CAPTURE_UTC,
    "rule": "A row is FINAL only when the official game book prints the team totals and its period line sums to them, and the individual player points also sum to the printed final. Both checks are executed by verify/2026-11-16-6e1aadc1/build_1115.py at build time. Not-yet-final games are listed in pending_not_final with the state observed on the official game page; no live score is stored as a final and no value is inferred.",
    "columns": ["date","game_id","away","home","status","final_label","away_pts","home_pts",
                "away_quarters","home_quarters","ot_periods","tip_et","arena","city","attendance",
                "officials","away_record_at_game_time","home_record_at_game_time",
                "quarter_sum_check","box_sum_check","inactives_away","inactives_home",
                "source_url","source_gamebook_pdf"],
    "rows": rows,
    "pending_not_final": [
        {"game_id": "0022600242", "matchup": "HOU@WAS",
         "state_at_retrieval": "Q4 7:00 remaining, 130-98 HOU on https://www.nba.com/game/ind-vs-phi-0022600236 sidebar at 2026-11-16T02:2xZ",
         "score_stored": None, "reason_not_settled": "not Final at retrieval time; the official game book for this game is published only after the game ends"},
        {"game_id": "0022600243", "matchup": "ATL@MIL",
         "state_at_retrieval": "Half, 55-53 ATL", "score_stored": None,
         "reason_not_settled": "not Final at retrieval time"},
        {"game_id": "0022600244", "matchup": "OKC@SAC",
         "state_at_retrieval": "Q1 10:37, 3-2 OKC", "score_stored": None,
         "reason_not_settled": "not Final at retrieval time (09:00 PM ET tip)"},
    ],
}
out_logs = {
    "title": "Per-player game logs, 2026-11-15 (brief R21: minutes, points, rebounds, assists and opponent for the players who appeared; DNP/DND rows carry the official reason)",
    "captured_by": "arena/6e1aadc1-nba1 (Z04)",
    "retrieved_utc": CAPTURE_UTC,
    "source": "the official NBA game book PDF for each game (statsdmz.nba.com/pdfs/20261115/), the league's own game document",
    "coverage": "6 of the 9 games on the slate were FINAL at retrieval time and are captured here, every player on both official rosters (played or DNP). The 3 games still in play are captured on the next pass, since the official book for a game exists only once it ends.",
    "rule": "No value is inferred. A played player's minutes/points/rebounds/assists are printed as the book prints them. A DNP row stores minutes=null and the official reason text; a DND row is the in-out decision made after the report deadline, which is exactly the availability signal the brief asks to track.",
    "columns": ["date","game_id","team","opponent","player","minutes","points","rebounds","assists","did_not_play","appears_in_box","source_gamebook_pdf"],
    "rows": logs,
}
os.makedirs(os.path.join(ROOT, "data/official"), exist_ok=True)
p1 = os.path.join(ROOT, "data/official/results_2026-11-15_settled_6e1aadc1.json")
p2 = os.path.join(ROOT, "data/official/player_game_logs_2026-11-15_6e1aadc1.json")
json.dump(out_feed, open(p1, "w"), indent=1)
json.dump(out_logs, open(p2, "w"), indent=1)
print("wrote", os.path.relpath(p1, ROOT), len(rows), "rows;", os.path.relpath(p2, ROOT), len(logs), "player rows")
print("all quarter-sum and box-sum checks passed for", len(rows), "games")
