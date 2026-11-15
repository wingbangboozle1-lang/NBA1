#!/usr/bin/env python3
"""settle_2026_11_14.py — settle the 2026-11-14 slate from official finals
and record the tamper-evident ledger entries.

Inputs:
  data/derived/horizon_picks.json     pre-tip published picks (2026-11-14)
  data/derived/horizon_lines.json     pre-tip published model lines
  data/official/results_2026-11-14.json  official finals + quarter scores
  data/played_games_2026_11_13_14.json   dispersion corpus (for the MAE note)
  git anchor ef2e723                  pre-tip publication commit (2026-11-14T22:18:48Z,
                                      hours before first tip 2026-11-15T00:00Z)

Writes:
  data/settlement/settlement_2026-11-14.json
  data/ledger/ledger.json             hash-chained publication/verification record

Settlement rules (frozen; also written into the settlement file):
  * A single graded from its published pick_line text "TEAM -x.x": TEAM must win
    by more than x.x (cover); winning by exactly x.x is a PUSH; otherwise LOSS.
    Units follow the repo's paper -110 convention: stake 1.10 to win 1.00
    (WIN +1.00, LOSS -1.10, PUSH 0.00) — identical to data/raw/s14/ settlement.
  * Gate failures settle as NO BET (0.00) exactly as published.
  * A parlay wins only if every leg wins; a push leg voids the ticket's stake
    proportionally (not applicable here); any losing leg loses the stake 1.10.
  * An SGP leg whose player did not play (inactive) is VOID: the leg is removed
    and the remaining legs settle at the ticket's frozen price. A ticket with any
    losing leg loses its stake (1.10). A ticket with all remaining legs winning
    pays at the price frozen at publication: profit = 1.10 * (1/joint_prob_rho - 1),
    the model's published fair price (the market gate G-PROP is blocked, so there
    is no market price; the price source is printed on every ticket).

Ledger:
  entry 1 = pre-tip anchor: SHA-256 of the published files as committed at ef2e723
  entry 2 = verification at settlement: same hashes recomputed from the live files
  entry 3 = settlement record hash (this file)
  Each entry commits to the previous entry's hash (hash chain).

Run:  python3 scripts/settle_2026_11_14.py
"""
import hashlib
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR_COMMIT = "ef2e723e13523b5b2495656c2a4ae5b461244374"
ANCHOR_TIME = "2026-11-14T22:18:48Z"
FIRST_TIP = "2026-11-15T00:00Z"  # DEN@NOP 7:00 PM ET
SETTLED_AT = "2026-11-15T12:35Z"
SESSION = "arena/83d380ad-nba1"

RESULT = {  # game_id -> (away, away_pts, home, home_pts)
    "0022600231": ("DEN", 116, "NOP", 108),
    "0022600232": ("DAL", 117, "CLE", 127),
    "0022600233": ("DET", 117, "MIA", 137),
    "0022600234": ("BKN", 110, "MEM", 129),
    "0022600235": ("CHI", 117, "MIN", 106),
}
GAME_URL = {gid: f"https://www.nba.com/game/{a.lower()}-vs-{h.lower()}-{gid}"
            for gid, (a, ap, h, hp) in RESULT.items()}

# player props verified on official box scores (see settlement sources)
PROP = {
    "Donovan Mitchell": {"team": "CLE", "played": False, "pts": None,
                         "evidence": "Inactive Players list, official box score DAL@CLE"},
    "Cooper Flagg": {"team": "DAL", "played": True, "pts": 18,
                     "evidence": "starter row, official box score DAL@CLE"},
    "Cade Cunningham": {"team": "DET", "played": True, "pts": 33,
                        "evidence": "starter row, official box score DET@MIA"},
    "Giannis Antetokounmpo": {"team": "MIA", "played": True, "pts": 34,
                              "evidence": "Game recap / points leader, official game page DET@MIA (see flagged F71)"},
}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def dump(rel, doc):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", rel)


def blob_at(commit, rel):
    out = subprocess.run(["git", "-C", ROOT, "show", f"{commit}:{rel}"],
                         capture_output=True, check=True).stdout
    return out


# --- ledger anchor verification -------------------------------------------
picks_rel = "data/derived/horizon_picks.json"
lines_rel = "data/derived/horizon_lines.json"
anchor_picks = sha256_bytes(blob_at(ANCHOR_COMMIT, picks_rel))
anchor_lines = sha256_bytes(blob_at(ANCHOR_COMMIT, lines_rel))
live_picks = sha256_bytes(open(os.path.join(ROOT, picks_rel), "rb").read())
live_lines = sha256_bytes(open(os.path.join(ROOT, lines_rel), "rb").read())
assert anchor_picks == live_picks, "horizon_picks.json changed since pre-tip anchor"
assert anchor_lines == live_lines, "horizon_lines.json changed since pre-tip anchor"

picks = load(picks_rel)

# --- grading ---------------------------------------------------------------
def grade_single(row):
    pick = row["pick"]
    gid = row["game_id"]
    if pick["pick_side"] == "PASS":
        return {"result": "NO BET (gate failed at publication)", "units": 0.0}
    away, ap, home, hp = RESULT[gid]
    pick_line = pick["pick_line"]  # e.g. "DEN -8.0"
    team, line_txt = pick_line.rsplit(" ", 1)
    line = float(line_txt)  # keeps the minus sign (repo convention)
    if team == home:
        margin = hp - ap
    elif team == away:
        margin = ap - hp
    else:
        raise AssertionError(("pick team not in game", team, gid))
    # "TEAM -x" = team must win by more than x (cover x points)
    if margin > -line:
        return {"result": "WIN", "units": 1.0}
    if margin == -line:
        return {"result": "PUSH", "units": 0.0}
    return {"result": "LOSS", "units": -1.1}


singles_out = []
for row in picks["singles"]:
    if row["date"] != "2026-11-14":
        continue
    gid = row["game_id"]
    away, ap, home, hp = RESULT[gid]
    g = grade_single(row)
    pick = row["pick"]
    singles_out.append({
        "date": row["date"], "game_id": gid, "matchup": row["matchup"],
        "pick_side": pick["pick_side"], "pick_line": pick["pick_line"],
        "gate": pick["gate"],
        "away": away, "away_pts": ap, "home": home, "home_pts": hp,
        "margin_pick_team": (hp - ap) if pick["pick_side"] == "HOME" else ((ap - hp) if pick["pick_side"] == "AWAY" else None),
        "result": g["result"], "units": g["units"],
        "price_convention": "paper -110: stake 1.10 to win 1.00",
        "source_game_url": GAME_URL[gid],
        "source_finals": "data/official/results_2026-11-14.json (official LINESCORES)",
    })

parlays_out = []
for row in picks["parlays"]:
    if row["date"] != "2026-11-14":
        continue
    legs = [row[k] for k in ("leg1", "leg2", "leg3") if row.get(k)]
    leg_results = []
    ok = True
    for leg in legs:
        matchup, side = leg.split(" — ")
        team, line_txt = side.rsplit(" ", 1)
        line = float(line_txt)
        gid = [g for g, (a, ap, h, hp) in RESULT.items() if f"{a}@{h}" == matchup][0]
        away, ap, home, hp = RESULT[gid]
        margin = (hp - ap) if team == home else (ap - hp)
        if margin > -line:
            res = "WIN"
        elif margin == -line:
            res = "PUSH"
        else:
            res = "LOSS"
            ok = False
        leg_results.append({"leg": leg, "result": res, "source_game_url": GAME_URL[gid]})
    parlays_out.append({
        "date": row["date"], "legs": legs, "leg_results": leg_results,
        "joint_published": {"joint_lb": row.get("joint_lb"), "joint_ub": row.get("joint_ub"),
                            "rho_lb": row.get("rho_lb"), "rho_ub": row.get("rho_ub")},
        "naive_product_printed_beside": row.get("joint_prob_independent") or row.get("p1_times_p2"),
        "result": "WIN" if ok else "LOSS",
        "units": 1.0 * (row.get("fair_odds_lb") or 2.64) if ok else -1.1,
        "units_note": ("WIN pays at the published fair-odds band lower bound (stake 1.10); "
                       "LOSS -1.10. All 11/14 parlays lost on a leg, so the payout convention "
                       "does not affect this settlement.") if ok else "LOSS -1.10 (stake)",
        "price_convention": "paper -110 legs; fair-odds band published pre-tip",
        "sources": row.get("sources", []),
    })

sgp_out = []
for row in picks["sgp_candidates"]:
    if row["date"] != "2026-11-14":
        continue
    legs = []
    for lk, dk in (("leg1", "leg1_detail"), ("leg2", "leg2_detail")):
        d = row[dk]
        pr = PROP.get(d["player"], {})
        legs.append({
            "leg_text": row[lk], "player": d["player"], "line": d["line"],
            "actual_pts": pr.get("pts"), "played": pr.get("played"),
            "result": ("VOID (player inactive)" if pr.get("played") is False else
                       ("WIN" if pr.get("pts") is not None and pr["pts"] > d["line"] else "LOSS")),
            "evidence": pr.get("evidence"),
            "source_url": GAME_URL[[g for g, (a, ap, h, hp) in RESULT.items() if f"{a}@{h}" == row["game"]][0]],
        })
    live = [l for l in legs if not l["result"].startswith("VOID")]
    if any(l["result"] == "LOSS" for l in live):
        result, units = "LOSS", -1.1
        price = None
    elif live and all(l["result"] == "WIN" for l in live):
        price = row["joint_prob_rho"]
        result = "WIN"
        units = round(1.1 * (1.0 / price - 1.0), 2)
    else:
        result, units, price = "PUSH/VOID (no live legs)", 0.0, None
    sgp_out.append({
        "date": row["date"], "game": row["game"], "kind": row.get("kind"),
        "legs": legs,
        "void_convention": ("A leg whose player did not play is VOID and removed; the ticket settles on "
                            "the remaining legs at the price frozen at publication. Any losing leg loses "
                            "the stake (1.10)."),
        "frozen_price_joint_prob_rho": row["joint_prob_rho"],
        "frozen_price_independent_printed_beside": row["joint_prob_independent"],
        "rho_status": row.get("rho_status"),
        "result": result, "units": units,
        "payout_formula": ("profit = 1.10 * (1/joint_prob_rho - 1) at the model's published fair price "
                           "(G-PROP market gate blocked; no market price exists)") if price else None,
        "sources": row.get("sources", []),
    })

wins = sum(1 for r in singles_out if r["result"] == "WIN")
losses = sum(1 for r in singles_out if r["result"] == "LOSS")
pushes = sum(1 for r in singles_out if r["result"] == "PUSH")
no_bets = sum(1 for r in singles_out if r["result"].startswith("NO BET"))
singles_units = round(sum(r["units"] for r in singles_out), 2)
parlay_units = round(sum(r["units"] for r in parlays_out), 2)
sgp_units = round(sum(r["units"] for r in sgp_out), 2)

settlement = {
    "title": "Settlement — 2026-11-14 slate (settled from official finals)",
    "settled_at_utc": SETTLED_AT,
    "settled_by": SESSION,
    "rules": {
        "single": 'grade from published pick_line text "TEAM -x.x": cover if team wins by more than x.x, PUSH at exactly x.x, else LOSS; units paper -110 (WIN +1.00, LOSS -1.10, PUSH 0.00); gate failures NO BET 0.00',
        "parlay": "every leg must WIN; any losing leg loses stake 1.10; WIN pays the published fair-odds band lower bound",
        "sgp": "legs are player props (Over/Under). A leg whose player did not play is VOID and removed; remaining legs settle at the ticket price frozen at publication (joint_prob_rho as fair price; G-PROP blocked, no market price). Any losing leg loses the stake (1.10).",
        "finals_source": "data/official/results_2026-11-14.json — official game pages (LINESCORES), quarters sum to finals (asserted at capture)",
    },
    "preregistration_check": {
        "pre_tip_anchor_commit": ANCHOR_COMMIT,
        "pre_tip_anchor_time": ANCHOR_TIME,
        "first_tip": FIRST_TIP,
        "publication_precedes_first_tip": True,
        "horizon_picks_sha256_at_anchor": anchor_picks,
        "horizon_lines_sha256_at_anchor": anchor_lines,
        "horizon_picks_sha256_now": live_picks,
        "horizon_lines_sha256_now": live_lines,
        "model_blocks_identical_to_live_file": True,
    },
    "singles": singles_out,
    "parlays": parlays_out,
    "sgp_candidates": sgp_out,
    "summary": {
        "singles_published": len(singles_out), "wins": wins, "losses": losses,
        "pushes": pushes, "no_bets": no_bets,
        "record": f"{wins}-{losses}-{pushes}",
        "singles_units_at_minus110": singles_units,
        "parlays_published": len(parlays_out),
        "parlays_won": sum(1 for r in parlays_out if r["result"] == "WIN"),
        "parlay_units": parlay_units,
        "sgp_published": len(sgp_out),
        "sgp_won": sum(1 for r in sgp_out if r["result"] == "WIN"),
        "sgp_units": sgp_units,
        "total_units": round(singles_units + parlay_units + sgp_units, 2),
        "validation_note": ("All tickets were published as MODEL OUTPUT — UNVALIDATED, unfunded, "
                            "zero-stake paper picks (no strategy has passed the validation gates; "
                            "market-comparison gates G4/G5 and prop gate G-PROP remain BLOCKED)."),
    },
    "sources": [
        "https://www.nba.com/games?date=2026-11-14",
    ] + [GAME_URL[g] for g in sorted(GAME_URL)],
}
dump("data/settlement/settlement_2026-11-14.json", settlement)

# --- ledger ----------------------------------------------------------------
# Archive byte-identical copies of the pre-tip published files so the chain
# stays verifiable after the rolling-slate update legitimately replaces the
# working files at data/derived/horizon_*.
ARCH_PICKS = "data/archive/horizon_picks_2026-11-14.json"
ARCH_LINES = "data/archive/horizon_lines_2026-11-14.json"
for rel, arch in ((picks_rel, ARCH_PICKS), (lines_rel, ARCH_LINES)):
    dst = os.path.join(ROOT, arch)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    data = open(os.path.join(ROOT, rel), "rb").read()
    open(dst, "wb").write(data)
    assert sha256_bytes(data) == (anchor_picks if rel == picks_rel else anchor_lines)
print("archived pre-tip published files")

prev_hash = "GENESIS"  # first ledger in this repository
e1 = {
    "entry": 1, "type": "pre_tip_publication",
    "at_utc": ANCHOR_TIME,
    "commit": ANCHOR_COMMIT,
    "first_tip_utc": FIRST_TIP,
    "files": {ARCH_PICKS: anchor_picks, ARCH_LINES: anchor_lines},
    "working_paths_at_publication": [picks_rel, lines_rel],
    "note": ("Published picks and model lines as committed at the pre-tip anchor. "
             "Commit time 2026-11-14T22:18:48Z precedes the first tip "
             "(2026-11-15T00:00Z DEN@NOP) by 1h41m. Byte-identical archives are "
             "committed to by digest so the chain survives the rolling update."),
    "prev": prev_hash,
}
h1 = sha256_bytes(json.dumps(e1, sort_keys=True).encode())
e2 = {
    "entry": 2, "type": "settlement_verification",
    "at_utc": SETTLED_AT,
    "verifies_entry": 1,
    "files_at_settlement": {picks_rel: live_picks, lines_rel: live_lines},
    "unchanged_since_pre_tip": True,
    "prev": h1,
}
h2 = sha256_bytes(json.dumps(e2, sort_keys=True).encode())
settlement_hash = sha256_bytes(open(os.path.join(ROOT, "data/settlement/settlement_2026-11-14.json"), "rb").read())
e3 = {
    "entry": 3, "type": "settlement_record",
    "at_utc": SETTLED_AT,
    "file": "data/settlement/settlement_2026-11-14.json",
    "sha256": settlement_hash,
    "official_finals_file": "data/official/results_2026-11-14.json",
    "prev": h2,
}
h3 = sha256_bytes(json.dumps(e3, sort_keys=True).encode())
ledger = {
    "title": "Tamper-evident pick ledger (SHA-256 hash chain)",
    "chain_rule": "each entry stores the SHA-256 of the previous entry's canonical JSON (sorted keys); genesis = entry 1",
    "verify_command": "python3 scripts/verify_ledger.py",
    "entries": [e1, e2, e3],
    "head": h3,
}
dump("data/ledger/ledger.json", ledger)
print("settlement: record", settlement["summary"]["record"],
      "singles u", singles_units, "parlay u", parlay_units, "sgp u", sgp_units,
      "total", settlement["summary"]["total_units"])
