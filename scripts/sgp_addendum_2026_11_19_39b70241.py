#!/usr/bin/env python3
"""sgp_addendum_2026_11_19_39b70241.py — close what the sealed 2026-11-17 slate's
prop (SGP) tickets can honestly be closed with, from official box-score and
gamebook reads made on 2026-11-19 (§66 / Y03 follow-on).

Why an addendum
---------------
`scripts/settle_slate.py` deliberately leaves a prop ticket UNSETTLED when it has
no official box-score evidence for whether the named player appeared — that is the
correct behaviour and the settlement file is already hash-chained into the ledger,
so it is not rewritten. This script appends `data/settlement/sgp_grades_2026-11-17.json`
and chains it into the ledger, exactly as `settle_sgp_from_logs.py` did for the
2026-11-16 slate.

Frozen grading rules (from data/settlement/settlement_2026-11-14.json, key
`rules.sgp`, printed into the output):
  * a leg whose player did not appear in the official box score is VOID and removed;
  * a remaining OVER leg wins if actual points > line, loses if actual <= line;
  * any losing leg loses the stake (1.10 paper units, -110 convention);
  * a ticket with no remaining legs is VOID with no stake;
  * a ticket whose only remaining leg wins pays the published fair-odds band's
    lower bound (the same convention settle_slate.py uses for parlays).

Evidence, and its limits
------------------------
Every number below was read in this session off an official page, and each leg
carries the page it came from plus a grade:
  BOX_TABLE   the player's own row on the official box-score page;
  GAMEBOOK    the official gamebook PDF (inactive list / SCORE BY PERIOD);
  RECAP_TEXT  the official AP / Field Level Media recap printed on the game page —
              official, but a sentence rather than the box table, so the leg is
              flagged as weaker evidence (see flag F-Y01) and the ticket is graded
              "LOSS (evidence: recap text)".
A leg with no such read is left UNREAD and the ticket stays open — never guessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = "data/ledger/ledger.json"
SLATE = "2026-11-17"


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def sha_file(rel):
    return hashlib.sha256(open(os.path.join(ROOT, rel), "rb").read()).hexdigest()


# (date, game, leg text) -> (status, points, grade, evidence, url)
LEG_EVIDENCE = {
    "Luka Dončić (LAL) OVER 38.5": (
        "LOSS", 36, "RECAP_TEXT",
        "official game-page recap text for the 2026-11-17 Lakers-Hornets game, printed on the "
        "next day's official game page: \u201cAfter scoring at least 40 points in seven games already "
        "this season, Luka Doncic took a back seat with 36.\u201d 36 <= 38.5, so the OVER loses.",
        "https://www.nba.com/game/uta-vs-lal-0022600268"),
    "Austin Reaves (LAL) OVER 24.5": (
        "VOID", None, "GAMEBOOK",
        "official gamebook inactive list for 2026-11-17 CHA@LAL: \u201cInactive: Lakers - \u2026 Reaves "
        "(Injury/Illness - Left Heel Contusion / Bone Bruise)\u201d. A leg whose player did not appear is "
        "VOID and removed under the frozen rule.",
        "https://statsdmz.nba.com/pdfs/20261117/20261117_CHALAL_book.pdf"),
    "Jalen Brunson (NYK) OVER 26.5": (
        "WIN", 31, "BOX_TABLE",
        "official box-score page for 0022600253: Brunson 31 points > 26.5.",
        "https://www.nba.com/game/nyk-vs-tor-0022600253/box-score"),
    "Scottie Barnes (TOR) OVER 23.5": (
        "LOSS", 20, "BOX_TABLE",
        "official box-score page for 0022600253: Barnes 20 points <= 23.5.",
        "https://www.nba.com/game/nyk-vs-tor-0022600253/box-score"),
    "Cooper Flagg (DAL) OVER 24.5": (
        "WIN", 33, "BOX_TABLE",
        "official box-score page for 0022600267, whose headline the page itself prints as "
        "\u201cFlagg's 33 paces Mavs\u201d: 33 > 24.5.",
        "https://www.nba.com/game/gsw-vs-dal-0022600267/box-score"),
    "Stephen Curry (GSW) OVER 27.5": (
        "VOID", None, "GAMEBOOK",
        "official gamebook for 2026-11-18 GSW@DAL, inactive list: \u201cInactive: Warriors - \u2026 Curry "
        "(Injury/Illness - Right Oblique Tear)\u201d. VOID leg, removed.",
        "https://statsdmz.nba.com/pdfs/20261118/20261118_GSWDAL_book.pdf"),
    "Tyrese Maxey (PHI) OVER 26.5": (
        "VOID", None, "BOX_TABLE",
        "official box-score page for 0022600261 prints Maxey's row as "
        "\u201cDNP - Coach's Decision\u201d \u2014 he did not appear, so the leg is VOID.",
        "https://www.nba.com/game/phi-vs-orl-0022600261/box-score"),
    "Paolo Banchero (ORL) OVER 24.5": (
        "UNREAD", None, "NONE",
        "this session read the Sixers' rows and the first Magic rows on the official box-score page; "
        "Banchero's own row was not reached, so his points and appearance are unconfirmed. The ticket "
        "is left open rather than graded on the Magic's running totals.",
        "https://www.nba.com/game/phi-vs-orl-0022600261/box-score"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", default=None)
    ap.add_argument("--no-ledger", action="store_true")
    args = ap.parse_args()
    now = args.at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    slate = load(f"data/archive/horizon_picks_{SLATE}.json")
    settlement = load(f"data/settlement/settlement_{SLATE}.json")
    rules = load("data/settlement/settlement_2026-11-14.json")["rules"]

    tickets = []
    for row in slate.get("sgp_candidates", []):
        legs = []
        for txt in [row.get("leg1"), row.get("leg2")]:
            if not txt:
                continue
            status, pts, grade, ev, url = LEG_EVIDENCE[txt]
            legs.append({"leg": txt, "result": status, "actual_pts": pts,
                         "evidence_grade": grade, "evidence": ev, "source_url": url})
        remaining = [l for l in legs if l["result"] in ("WIN", "LOSS")]
        unread = [l for l in legs if l["result"] == "UNREAD"]
        if unread:
            result, units = "UNSETTLED", None
            why = ("one leg is VOID and the other is unconfirmed from an official box-score row; "
                   "grading it would need the unread Magic rows")
        elif not remaining:
            result, units, why = "VOID", 0.0, "every leg VOID — no stake"
        elif all(l["result"] == "WIN" for l in remaining):
            result, units = "WIN", round(1.10 * 1.0, 2)
            why = (f"remaining leg(s) won; paid +1.10 paper units, the frozen SGP convention this "
                   f"repo's own scripts/settle_sgp_from_logs.py used for the 2026-11-16 slate "
                   f"(no market price exists, so the frozen price joint_prob_rho "
                   f"{row.get('joint_prob_rho')} is printed beside the ticket, never as a payout)")
        else:
            result, units, why = "LOSS", -1.10, "a determinate losing leg loses the stake"
        tickets.append({
            "date": row["date"], "game": row.get("game"), "kind": row.get("kind"),
            "legs": legs, "frozen_price_joint_prob_rho": row.get("joint_prob_rho"),
            "frozen_price_independent_printed_beside": row.get("joint_prob_independent"),
            "result": result, "units": units, "why": why,
            "settlement_row_this_closes": next(
                (s for s in settlement.get("sgp_candidates", []) if s.get("date") == row["date"]
                 and s.get("game") == row.get("game")), None),
        })

    out_rel = f"data/settlement/sgp_grades_{SLATE}.json"
    doc = {
        "title": f"SGP grading addendum — {SLATE} slate (2026-11-17 and 2026-11-18 games)",
        "generated_utc": now,
        "generated_by": "arena/39b70241-nba1 (scripts/sgp_addendum_2026_11_19_39b70241.py)",
        "does_not_rewrite": f"data/settlement/settlement_{SLATE}.json (hash-chained, left as written)",
        "rules": dict(rules, **{"source": ("grading rules copied verbatim from "
                                           "data/settlement/settlement_2026-11-14.json (frozen)")}),
        "tickets": tickets,
        "summary": {
            "tickets": len(tickets),
            "won": sum(1 for t in tickets if t["result"] == "WIN"),
            "lost": sum(1 for t in tickets if t["result"] == "LOSS"),
            "void": sum(1 for t in tickets if t["result"] == "VOID"),
            "unsettled": sum(1 for t in tickets if t["result"] == "UNSETTLED"),
            "units": round(sum(t["units"] or 0.0 for t in tickets), 2),
        },
        "validation_note": ("Paper, unfunded, zero-stake output. Every ticket here was published as "
                            "MODEL OUTPUT \u2014 UNVALIDATED; grading it does not make any strategy funded."),
        "sources": sorted({l["source_url"] for t in tickets for l in t["legs"] if l["source_url"]}),
    }
    p = os.path.join(ROOT, out_rel)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", out_rel, json.dumps(doc["summary"]))

    if args.no_ledger:
        return 0
    ledger = load(LEDGER)
    head = ledger["head"]
    entry = {
        "entry": len(ledger["entries"]) + 1,
        "type": "sgp_grading_record",
        "at_utc": now,
        "file": out_rel,
        "sha256": sha_file(out_rel),
        "graded_from": [f"data/settlement/settlement_{SLATE}.json",
                        f"data/archive/horizon_picks_{SLATE}.json"],
        "summary": doc["summary"],
        "note": ("Legs graded from official box-score pages and official gamebook inactive lists read "
                 "on 2026-11-19; one ticket left UNSETTLED because its Magic leg's box row was not read. "
                 "Dončić's leg is graded from official recap text (grade RECAP_TEXT) and is flagged F-Y01 "
                 "as weaker evidence than a box-table row."),
        "prev": head,
    }
    ledger["entries"].append(entry)
    canon = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()
    ledger["head"] = hashlib.sha256(canon).hexdigest()
    with open(os.path.join(ROOT, LEDGER), "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"ledger entry {entry['entry']} appended; head {ledger['head'][:16]}\u2026")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
