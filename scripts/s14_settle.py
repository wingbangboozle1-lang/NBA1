#!/usr/bin/env python3
"""s14_settle.py — settle every published paper pick on the 2026-11-13 slate.

Input:  data/originated_lines.json           (published RecordLine-1 lines + gated picks)
        data/archive/originated_lines_2026-11-13T2245Z.json   (pre-game frozen copy)
        data/raw/s14/finals_2026-11-13.json   (official finals, per-game source URLs)

Output: data/raw/s14/settlement_2026-11-13.json

Settlement rules (printed on the site next to the table):
  * Spread picks are graded against the originated spread. HOME covers iff
    (home_pts - away_pts) + spread_home > 0; AWAY covers iff the mirrored line
    covers for the away side. Exactly equal -> PUSH.
  * Units for singles use the repo's standing -110 convention (win +1.00,
    loss -1.10, push 0). This is a convention, not a market price - no official
    price exists (flag F3).
  * Parlays are graded leg by leg and reported WIN/LOSS only; no unit number is
    computed because no official price exists for the combination either.
  * Picks that failed their gate at publication time are recorded as NO BET.
  * Nothing is inferred: every settled row carries the official game URL.

The pre-registration check compares the model blocks of the live file with the
archive frozen at 2026-11-13T22:45Z (before tip). If they match, the settled
picks are auditable as pre-game commitments rather than retrospective writes.

Run:  python3 scripts/s14_settle.py
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
S14 = os.path.join(RAW, "s14")

SETTLED_AT = "2026-11-14T10:20:00Z"
SESSION = "arena/254dd8bb-nba1"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


finals = {r["game_id"]: r for r in load(os.path.join(S14, "finals_2026-11-13.json"))["rows"]}
live = load(os.path.join(ROOT, "data", "originated_lines.json"))
arch = load(os.path.join(ROOT, "data", "archive", "originated_lines_2026-11-13T2245Z.json"))

l13 = [g for g in live["games"] if g["date"] == "2026-11-13"]
a13 = [g for g in arch.get("games", []) if g["date"] == "2026-11-13"]
pre_registered = (
    len(l13) == len(a13) == 9
    and json.dumps([g.get("model") for g in l13], sort_keys=True)
    == json.dumps([g.get("model") for g in a13], sort_keys=True)
)

GID_BY_MATCHUP = {(r["away"], r["home"]): gid for gid, r in finals.items()}


def settle_single(g):
    a, _, h = g["matchup"].partition("@")
    gid = GID_BY_MATCHUP.get((a, h))
    fin = finals.get(gid)
    m = g["model"]
    if fin is None:
        return {"date": g["date"], "game_id": gid, "matchup": g["matchup"],
                "result": "UNSETTLED - no captured final"}
    row = {
        "date": g["date"], "game_id": gid, "matchup": g["matchup"],
        "pick_side": m["pick_side"], "pick_line": m["pick_line"], "gate": m["gate"],
        "originated_spread_home": m["originated_spread_home"],
        "model_expected_margin_home": m["expected_margin_home"],
        "away_pts": fin["away_pts"], "home_pts": fin["home_pts"],
        "ot": fin["ot"],
        "source_game_url": fin["source_url"],
        "source_date_url": fin["source_date_url"],
        "source_preregistration_url":
            "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/archive/"
            "originated_lines_2026-11-13T2245Z.json",
    }
    home_margin = fin["home_pts"] - fin["away_pts"]
    row["actual_margin_home"] = home_margin
    row["model_margin_error"] = round(home_margin - m["expected_margin_home"], 1)
    if m["pick_side"] in ("HOME", "AWAY"):
        # line value for the picked side (the side lays the points)
        # HOME covers iff home_margin + spread_home > 0 (spread_home is the home line, e.g. -9.0);
        # AWAY covers iff -home_margin - spread_home > 0 (the mirrored away line, e.g. "ATL -8.0").
        edge = home_margin + m["originated_spread_home"] if m["pick_side"] == "HOME" \
            else -home_margin - m["originated_spread_home"]
        if edge > 0:
            row["result"], row["units"] = "WIN", 1.0
        elif edge < 0:
            row["result"], row["units"] = "LOSS", -1.1
        else:
            row["result"], row["units"] = "PUSH", 0.0
    else:
        row["result"], row["units"] = "NO BET (gate failed at publication)", 0.0
    return row


singles = [settle_single(g) for g in l13]

parlays = []
for p in live.get("parlays", []):
    if p.get("date") != "2026-11-13":
        continue
    legs = []
    for key in ("leg1", "leg2"):
        label = p[key]                    # e.g. "UTA@HOU — HOU -18.0"
        mu, _, line_txt = label.partition(" \u2014 ")
        mu_a, _, mu_h = mu.partition("@")
        gid = GID_BY_MATCHUP.get((mu_a, mu_h))
        fin = finals[gid]
        side = "HOME" if line_txt.startswith(mu_h) else "AWAY"
        s = float(line_txt.rsplit(" ", 1)[1])
        spread_home = s if side == "HOME" else -s
        home_margin = fin["home_pts"] - fin["away_pts"]
        edge = home_margin + spread_home if side == "HOME" else -home_margin - spread_home
        res = "WIN" if edge > 0 else ("LOSS" if edge < 0 else "PUSH")
        legs.append({"leg": label, "game_id": gid, "result": res,
                     "away_pts": fin["away_pts"], "home_pts": fin["home_pts"],
                     "source_game_url": fin["source_url"]})
    parlay_result = "WIN" if all(l["result"] == "WIN" for l in legs) else \
        ("LOSS" if any(l["result"] == "LOSS" for l in legs) else "PUSH")
    parlays.append({
        "date": "2026-11-13",
        "legs": legs,
        "p1": p["p1"], "p2": p["p2"],
        "joint_lb_frechet": p["joint_lb"], "joint_ub_frechet": p["joint_ub"],
        "note": "Joint bounds are Frechet bounds, not measurements (flag F9).",
        "result": parlay_result,
        "units": None,
        "units_note": "Not computed: no official price exists for parlays (flag F3).",
    })

graded = [r for r in singles if r["result"] in ("WIN", "LOSS", "PUSH")]
wins = sum(1 for r in graded if r["result"] == "WIN")
losses = sum(1 for r in graded if r["result"] == "LOSS")
pushes = sum(1 for r in graded if r["result"] == "PUSH")
units = round(sum(r["units"] for r in graded), 2)
errs = [abs(r["model_margin_error"]) for r in singles if "model_margin_error" in r]

out = {
    "settled_at_utc": SETTLED_AT,
    "session": SESSION,
    "title": "Settlement of every published paper pick on the 2026-11-13 slate",
    "rules": [
        "Spread picks graded against the originated spread: HOME covers iff (home_pts - away_pts) + spread_home > 0; PUSH at exactly zero.",
        "Singles units use the repo's standing -110 convention (win +1.00, loss -1.10). This is a convention, not a market price (flag F3).",
        "Parlays are graded leg by leg and reported WIN/LOSS only; no unit number is computed.",
        "Picks that failed their gate at publication are recorded as NO BET and worth 0.00.",
        "Every row links the official game page that published the final score.",
    ],
    "preregistration_check": {
        "archive": "data/archive/originated_lines_2026-11-13T2245Z.json",
        "frozen_at": "2026-11-13T22:45Z (before tip)",
        "model_blocks_identical_to_live_file": pre_registered,
    },
    "sources": [
        "https://www.nba.com/games?date=2026-11-13",
        "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/archive/originated_lines_2026-11-13T2245Z.json",
    ],
    "singles": singles,
    "parlays": parlays,
    "summary": {
        "picks_published": len(graded),
        "wins": wins, "losses": losses, "pushes": pushes,
        "record": f"{wins}-{losses}" + (f"-{pushes}" if pushes else ""),
        "units_at_minus110": units,
        "parlays_published": len(parlays),
        "parlays_won": sum(1 for p in parlays if p["result"] == "WIN"),
        "model_margin_mae_on_slate": round(sum(errs) / len(errs), 2) if errs else None,
        "no_bets": len(singles) - len(graded),
    },
}

path = os.path.join(S14, "settlement_2026-11-13.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
    f.write("\n")

print(f"settled singles: {out['summary']['record']} {units:+.2f}u "
      f"(NO BET: {out['summary']['no_bets']}); parlays {out['summary']['parlays_won']}-"
      f"{len(parlays) - out['summary']['parlays_won']}")
print(f"pre-registered (archive-identical): {pre_registered}")
print(f"model margin MAE on the 9 games: {out['summary']['model_margin_mae_on_slate']}")
print("S14 SETTLE OK")
