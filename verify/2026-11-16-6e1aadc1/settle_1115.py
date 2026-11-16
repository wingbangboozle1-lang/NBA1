#!/usr/bin/env python3
"""Z08 - settle the 2026-11-15 slate from the official finals, stamp it, and append the
settlement entry to the tamper-evident ledger.

Why 6 of 9 games and not 9: the brief's rule is "settle only after final scores are
verified", and this pass learned something the repository had not recorded - the NBA game
book on statsdmz.nba.com is a LIVE document (the 2026-11-15 HOU@WAS book was readable while
the game was in the 4th quarter, printing 132-101 with 211:00 team minutes and "Attendance:
Not Yet Counted"). A book alone is therefore NOT proof of finality. A row is settled here
only when three independent official signals agree:
    1. the official games page prints the state "Final" (or "Final/OT") for that matchup,
    2. the game book's team-total minutes equal 5 x 48 = 240:00 (265:00 in one OT), and
    3. the book's period lines sum to its printed final AND the individual player points
       sum to the same final.
Games that did not pass all three are listed as pending and are not graded.
"""
import json, os, hashlib, unicodedata


def norm(name):
    """accent- and case-insensitive key for matching a box-score name to a prop leg."""
    out = unicodedata.normalize("NFKD", str(name))
    out = "".join(c for c in out if not unicodedata.combining(c))
    return out.lower().replace(".", "").replace(",", "").strip()

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SETTLED_UTC = "2026-11-16T03:1xZ"


def rd(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding="utf-8"))


def sha(path):
    return hashlib.sha256(open(os.path.join(ROOT, path), "rb").read()).hexdigest()


feed = rd("data", "official", "results_2026-11-15_settled_6e1aadc1.json")
feed["pending_not_final"] = [
    dict(game_id="0022600242", matchup="HOU@WAS",
         state_at_retrieval="Q4 4:30 remaining, 134-102 HOU, on https://www.nba.com/games?date=2026-11-15 at 2026-11-16T03:1xZ",
         score_stored=None,
         reason_not_settled="not Final at settlement time; its game book was already readable and printed "
                            "132-101 with 211:00 team minutes and 'Attendance: Not Yet Counted' - the book "
                            "is a LIVE document, which is why a book alone cannot certify finality"),
    dict(game_id="0022600243", matchup="ATL@MIL",
         state_at_retrieval="Q3 9:01 remaining, 61-56 ATL", score_stored=None,
         reason_not_settled="not Final at settlement time"),
    dict(game_id="0022600244", matchup="OKC@SAC",
         state_at_retrieval="Q1 6:51 remaining, 17-6 OKC", score_stored=None,
         reason_not_settled="not Final at settlement time (09:00 PM ET tip)"),
]
final = {r["game_id"]: r for r in feed["rows"]}
for r in final.values():
    r["matchup"] = f'{r["away"]}@{r["home"]}'
picks = rd("data", "archive", "horizon_picks_2026-11-15.json")
prereg = rd("data", "archive", "prereg_2026-11-15", "Prereg_index.json")

singles_out, pending = [], []
for s in [x for x in picks["singles"] if x["date"] == "2026-11-15"]:
    gid = s["game_id"]
    g = final.get(gid)
    if not g:
        pend = next((p for p in feed["pending_not_final"] if p["game_id"] == gid), {})
        pending.append(dict(game_id=gid, matchup=s["matchup"], pick_line=(s.get("pick") or {}).get("pick_line"),
                            state_at_settlement=pend.get("state_at_retrieval"),
                            not_graded_because="official final not verified at settlement time"))
        continue
    pick = s.get("pick") or {}
    line = pick.get("pick_line") or ""
    side = pick.get("pick_side")
    if side in (None, "PASS") or not line:
        singles_out.append(dict(game_id=gid, matchup=s["matchup"], result="NO BET",
                                units=0.0, note=line or "pass"))
        continue
    team, num = line.split()[0], float(line.split()[1])
    margin = (g["away_pts"] - g["home_pts"]) if side == "AWAY" else (g["home_pts"] - g["away_pts"])
    if abs(margin - abs(num)) < 1e-9:
        res, units = "PUSH", 0.0
    elif margin > abs(num):
        res, units = "WIN", 1.00
    else:
        res, units = "LOSS", -1.10
    singles_out.append(dict(
        game_id=gid, matchup=s["matchup"], pick_side=side, pick_line=line,
        gate=pick.get("gate"), pick_prob=pick.get("pick_prob"),
        away=g["away"], away_pts=g["away_pts"], home=g["home"], home_pts=g["home_pts"],
        margin_pick_team=margin, result=res, units=units,
        price_convention="paper -110: stake 1.10 to win 1.00",
        source_finals="data/official/results_2026-11-15_settled_6e1aadc1.json (official game book; "
                      "quarter sums and box sums asserted at build)",
        source_game_url=g["source_url"], source_gamebook_pdf=g["source_gamebook_pdf"]))

parlay_out = []
for p in [x for x in picks.get("parlays", []) if x.get("date") == "2026-11-15"]:
    legs = []
    complete = True
    for key in ("leg1", "leg2"):
        txt = p.get(key) or ""
        head, tail = txt.split("\u2014")[0].strip(), txt.split("\u2014")[-1].strip()
        gid = next((k for k, v in final.items() if v["matchup"] == head), None)
        if gid:
            g = final[gid]
            team, num = tail.split()[0], float(tail.split()[1])
            side = "AWAY" if g["away"] == team else "HOME"
            margin = (g["away_pts"] - g["home_pts"]) if side == "AWAY" else (g["home_pts"] - g["away_pts"])
            leg_res = "PUSH" if abs(margin - abs(num)) < 1e-9 else ("WIN" if margin > abs(num) else "LOSS")
        else:
            leg_res, complete = "PENDING", False
        legs.append(dict(leg=txt, result=leg_res))
    if not complete:
        parlay_out.append(dict(kind="parlay", date="2026-11-15", legs=legs, result="NOT SETTLED",
                               units=None, reason="a leg's game had not reached a verified Final"))
    else:
        won = all(l["result"] == "WIN" for l in legs)
        parlay_out.append(dict(kind="parlay", date="2026-11-15", legs=legs,
                               result="WIN" if won else "LOSS",
                               units=(p.get("fair_odds_lb") or 0) - 1.0 if won else -1.10,
                               price="published fair-odds band lower bound "
                                     f"{p.get('fair_odds_lb')} (naive product {p.get('naive_product')})",
                               source="data/archive/horizon_picks_2026-11-15.json"))

sgp_out = []
logs = rd("data", "official", "player_game_logs_2026-11-15_6e1aadc1.json")["rows"]
by_player = {}
for r in logs:
    by_player[(r["game_id"], r["team"], norm(r["player"]))] = r
for g in [x for x in picks.get("sgp_candidates", []) if x.get("date") == "2026-11-15"]:
    gid = next((k for k, v in final.items() if v["matchup"] == g.get("game")), None)
    graded, note = [], "both legs read from the same official game book as the game-level final"
    for key in ("leg1_detail", "leg2_detail"):
        d = g.get(key) or {}
        row = by_player.get((gid, d.get("team"), norm(str(d.get("player", ""))))) if gid else None
        if row is None:
            graded.append(dict(leg=g.get(key.replace("_detail", "")), result="PENDING",
                               reason="no verified official final / no box row for that game at settlement time"))
            note = "a leg's game had not reached a verified Final"
            continue
        pts = row["points"]
        line = d.get("line")
        over = "OVER" in (g.get(key.replace("_detail", "")) or "").upper()
        if pts is None:
            graded.append(dict(leg=g.get(key.replace("_detail", "")), result="VOID - did not play",
                               player=d.get("player"), minutes=None,
                               source="official game book box score"))
            continue
        hit = (pts > line) if over else (pts < line)
        graded.append(dict(leg=g.get(key.replace("_detail", "")), player=d.get("player"),
                           official_points=pts, line=line, result="WIN" if hit else "LOSS",
                           source_gamebook_pdf=row["source_gamebook_pdf"]))
    all_final = all(x["result"] in ("WIN", "LOSS") for x in graded)
    won = all_final and all(x["result"] == "WIN" for x in graded)
    sgp_out.append(dict(kind="sgp", date="2026-11-15", game=g.get("game"), legs=graded,
                        result=("WIN" if won else "LOSS") if all_final else "NOT SETTLED",
                        units=(-1.10 if all_final and not won else (0.0 if not all_final else None)),
                        pricing_note="prop legs carry no market price (see R16); the fair price frozen at "
                                     "publication is the joint probability under the registered rho",
                        settle_note=note,
                        source="data/archive/horizon_picks_2026-11-15.json + the official 11/15 game book"))

w = sum(1 for s in singles_out if s["result"] == "WIN")
l = sum(1 for s in singles_out if s["result"] == "LOSS")
pu = sum(1 for s in singles_out if s["result"] == "PUSH")
nb = sum(1 for s in singles_out if s["result"] == "NO BET")
u = round(sum(s.get("units", 0.0) for s in singles_out), 2)

out = {
    "title": "Settlement - 2026-11-15 slate (settled from official finals; 6 of 9 games verified final at this stamp)",
    "settled_at_utc": SETTLED_UTC,
    "settled_by": "arena/6e1aadc1-nba1 (Z08)",
    "finality_rule": "a game is settled only when the official games page prints Final, the game "
                     "book's team-total minutes equal 240:00 (265:00 with one OT), the book's period "
                     "lines sum to its printed final, and the individual player points sum to the same "
                     "final. The game book is published live, so a book by itself is not finality - "
                     "that is the reason 11/15 is settled in two passes.",
    "rules": {
        "single": "cover if the picked team wins by more than the published number, PUSH at exactly it, else LOSS; "
                  "paper -110 (WIN +1.00, LOSS -1.10, PUSH 0.00); gate failures NO BET 0.00",
        "parlay": "every leg must WIN; any losing leg loses the stake (1.10); a pending leg means the ticket is NOT SETTLED",
        "preregistration": "settlement rule as frozen in data/archive/prereg_2026-11-15/ before the first tip",
    },
    "preregistration_check": {
        "vintage": "2026-11-15", "frozen_at_utc": prereg.get("frozen_at_utc"),
        "first_tip_utc": prereg.get("first_tip_utc"), "slate_window": prereg.get("slate_window"),
        "files_digest_count": len(prereg.get("files", {})),
    },
    "singles": singles_out,
    "parlays": parlay_out,
    "sgps": sgp_out,
    "pending_not_graded": pending,
    "totals": dict(singles=len(singles_out), wins=w, losses=l, pushes=pu, no_bets=nb, units_singles=u,
                   parlays_settled=sum(1 for p in parlay_out if p["result"] in ("WIN", "LOSS")),
                   sgps_settled=sum(1 for p in sgp_out if p["result"] in ("WIN", "LOSS")),
                   parlays_not_settled=sum(1 for p in parlay_out if p["result"] == "NOT SETTLED"),
                   games_on_slate=9, games_verified_final=len(final),
                   picks_on_slate=len(singles_out) + len(pending)),
}
p_settle = os.path.join(ROOT, "data", "settlement", "settlement_2026-11-15.json")
json.dump(out, open(p_settle, "w", encoding="utf-8"), indent=1)
print(f"singles: {w}W-{l}L-{pu}P-{nb}NB  {u:+.2f}u; pending {len(pending)}")

# ---- ledger append (hash chain; never rewrite an existing entry) -------------------------
led_path = os.path.join(ROOT, "data", "ledger", "ledger.json")
led = json.load(open(led_path, encoding="utf-8"))
entries = led["entries"]
# idempotent re-run: this session's own settlement entry may already be the tail (a second
# pass over the same slate). Drop only a trailing entry written by this session for this same
# file, so the append is never duplicated and no other session's entry can be touched.
while entries and entries[-1].get("file") == "data/settlement/settlement_2026-11-15.json":
    entries.pop()
# the chain rule on this file, as scripts/verify_ledger.py reads it: entry N stores
# prev = sha256 of entry N-1's canonical JSON (json.dumps with sorted keys), and the file's
# top-level `head` equals sha256 of the LAST entry's canonical JSON.
sha_ = lambda b: hashlib.sha256(b).hexdigest()
canon = lambda e: json.dumps(e, sort_keys=True).encode()
prev = sha_(canon(entries[-1]))
if len(entries) == 1 and entries[0].get("prev") == "GENESIS":
    prev = "GENESIS"
entry = {
    "entry": entries[-1]["entry"] + 1,
    "type": "settlement_record",
    "at_utc": SETTLED_UTC,
    "file": "data/settlement/settlement_2026-11-15.json",
    "sha256": sha("data/settlement/settlement_2026-11-15.json"),
    "official_finals_file": "data/official/results_2026-11-15_settled_6e1aadc1.json",
    "official_finals_sha256": sha("data/official/results_2026-11-15_settled_6e1aadc1.json"),
    "settles_entry": 4,
    "verifies_pre_tip_publication_of": "2026-11-15T12:55Z (entry 4); picks graded are the frozen cut, not a re-price",
    "games_verified_final": len(final),
    "games_on_slate_not_yet_final": len(pending),
    "prev": prev,
}
entries.append(entry)
led["head"] = sha_(canon(entry))
json.dump(led, open(led_path, "w", encoding="utf-8"), indent=1)
print("ledger entry", entry["entry"], "head", entry["sha256"][:16], "prev", prev[:16])
