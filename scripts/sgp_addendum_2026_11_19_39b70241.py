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
  GAMEBOOK    the official gamebook PDF's inactive list;
Both of a ticket's legs can be VOID — the frozen rule then voids the ticket with no
stake, which is what happens to the PHI@ORL ticket here: Maxey was a coach's-decision
DNP and Banchero was inactive.
Every leg on the four published tickets has such a read, so nothing is left open by
this addendum. Each evidence string names the page and the row it came from, so the
grades can be re-checked against the same official source.
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
        "LOSS", 36, "BOX_TABLE",
        "official box-score page for 0022600256 (2026-11-17 CHA@LAL, FINAL 118-114): Dončić "
        "42:20, 13-34 FG, 5-16 3PT, 5-7 FT, 7 REB, 7 AST, 1 STL, 1 BLK, 5 TO, 5 PF, +2 — 36 points. "
        "36 <= 38.5, so the OVER loses. (The game page's own recap sentence “After scoring at least 40 "
        "points in seven games already this season, Luka Doncic took a back seat with 36” agrees with "
        "the box row, so the leg does not rest on recap text.)",
        "https://www.nba.com/game/cha-vs-lal-0022600256/box-score"),
    "Austin Reaves (LAL) OVER 24.5": (
        "VOID", None, "BOX_INACTIVE_LIST",
        "the same official box-score page closes with an “Inactive Players” block printing "
        "“LAL: Chris Manon, Austin Reaves, Walker Kessler, Arthur Kaluma”, and Reaves has no row in "
        "the Lakers table; the official gamebook for the same game (fetched in this session) gives the "
        "reason: “Reaves (Injury/Illness - Left Heel Contusion / Bone Bruise)”. A leg whose player "
        "did not appear is VOID and removed under the frozen rule.",
        "https://www.nba.com/game/cha-vs-lal-0022600256/box-score"),
    "Jalen Brunson (NYK) OVER 26.5": (
        "WIN", 31, "BOX_TABLE",
        "official box-score page for 0022600253 (2026-11-17 NYK@TOR, FINAL 111-102): Brunson 34:26, "
        "10-22 FG, 4-11 3PT, 7-7 FT, 5 REB, 5 AST, 0 STL, 1 BLK, 2 TO, 2 PF, +4 — 31 points > 26.5.",
        "https://www.nba.com/game/nyk-vs-tor-0022600253/box-score"),
    "Scottie Barnes (TOR) OVER 23.5": (
        "LOSS", 20, "BOX_TABLE",
        "official box-score page for 0022600253: Barnes 34:06, 7-14 FG, 1-2 3PT, 5-6 FT, 4 REB, 2 AST, "
        "0 STL, 2 BLK, 0 TO, 5 PF, -8 — 20 points <= 23.5.",
        "https://www.nba.com/game/nyk-vs-tor-0022600253/box-score"),
    "Cooper Flagg (DAL) OVER 24.5": (
        "WIN", 33, "BOX_TABLE",
        "official box-score page for 0022600267 (2026-11-18 GSW@DAL, FINAL 116-94): Flagg 33:59, "
        "11-15 FG, 3-5 3PT, 8-8 FT, 5 REB, 9 AST, 4 STL, 0 BLK, 5 TO, 3 PF, +32 — 33 points > 24.5. "
        "The page's own recap headline (“Flagg's 33 paces Mavs”) agrees with the row.",
        "https://www.nba.com/game/gsw-vs-dal-0022600267/box-score"),
    "Stephen Curry (GSW) OVER 27.5": (
        "VOID", None, "GAMEBOOK",
        "official gamebook for 2026-11-18 GSW@DAL, inactive list: “Inactive: Warriors - … Curry "
        "(Injury/Illness - Right Oblique Tear)”; Curry has no row in the Warriors table on the "
        "box-score page either. VOID leg, removed. (The box page's own “Inactive Players” block "
        "was not re-read for this game in this session — see flag F-Y01.)",
        "https://statsdmz.nba.com/pdfs/20261118/20261118_GSWDAL_book.pdf"),
    "Tyrese Maxey (PHI) OVER 26.5": (
        "VOID", None, "BOX_TABLE",
        "official box-score page for 0022600261 (2026-11-18 PHI@ORL, FINAL 121-116) prints Maxey's row "
        "as “DNP - Coach's Decision” — active (he is not in the “Inactive Players” block, "
        "which reads “PHI: Jaylen Brown, Ariel Hukporti, Dominick Barlow, Adem Bona”) but he did "
        "not appear, so the leg is VOID.",
        "https://www.nba.com/game/phi-vs-orl-0022600261/box-score"),
    "Paolo Banchero (ORL) OVER 24.5": (
        "VOID", None, "BOX_INACTIVE_LIST",
        "the same box-score page's “Inactive Players” block prints “ORL: Noah Penda, Izaiyah "
        "Nelson, Colin Castleton, Paolo Banchero, Jonathan Isaac”, and Banchero has no row in the Magic "
        "table (its printed TOTALS are 44-84 FG, 19-37 3PT, 9-17 FT, 37 REB, 31 AST, 116 PTS — the "
        "final score, so no row is missing). VOID leg, removed.",
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

    # The settlement's own open-ticket list is the driver: it is exactly the set of
    # tickets that were published on this slate and left UNSETTLED. The archive
    # carries candidates for later days too (they are live tickets now, not this
    # slate's business), so grading from the archive would reach into the future.
    arch_by = {(r["date"], r.get("game")): r for r in slate.get("sgp_candidates", [])}
    tickets, skipped = [], []
    for row in settlement.get("sgp_candidates", []):
        arch = arch_by.get((row["date"], row.get("game")), {})
        legs = []
        for txt in row.get("legs", []):
            if txt not in LEG_EVIDENCE:
                skipped.append({"date": row["date"], "game": row.get("game"), "leg": txt,
                                "why": "no official read in this session; left ungraded"})
                legs.append({"leg": txt, "result": "UNREAD", "actual_pts": None,
                             "evidence_grade": "NONE",
                             "evidence": "not read from an official source in this session",
                             "source_url": None})
                continue
            status, pts, grade, ev, url = LEG_EVIDENCE[txt]
            legs.append({"leg": txt, "result": status, "actual_pts": pts,
                         "evidence_grade": grade, "evidence": ev, "source_url": url})
        remaining = [l for l in legs if l["result"] in ("WIN", "LOSS")]
        unread = [l for l in legs if l["result"] == "UNREAD"]
        if unread:
            result, units = "UNSETTLED", None
            why = ("at least one leg has no official box-score read yet — the ticket stays "
                   "open rather than being graded on inference")
        elif not remaining:
            result, units, why = "VOID", 0.0, ("every leg VOID (the named player did not appear) — "
                                              "the frozen rule voids the ticket with no stake")
        elif all(l["result"] == "WIN" for l in remaining):
            result, units = "WIN", round(1.10 * 1.0, 2)
            why = (f"remaining leg(s) won; paid +1.10 paper units, the frozen SGP convention this "
                   f"repo's own scripts/settle_sgp_from_logs.py used for the 2026-11-16 slate "
                   f"(no market price exists, so the frozen price joint_prob_rho "
                   f"{arch.get('joint_prob_rho')} is printed beside the ticket, never as a payout)")
        else:
            result, units = "LOSS", -1.10
            why = ("a determinate losing leg loses the 1.10-unit stake, whatever the other leg did "
                   "(VOID legs are removed first, never auto-won)")
        tickets.append({
            "date": row["date"], "game": row.get("game"), "kind": row.get("kind"),
            "legs": legs,
            "frozen_price_joint_prob_rho": row.get("frozen_price_joint_prob_rho"),
            "frozen_price_independent_printed_beside": row.get("frozen_price_independent"),
            "previous_state": row.get("result"),
            "previous_why_not_settled": row.get("why_not_settled"),
            "result": result, "units": units, "why": why,
            "rho_provenance": arch.get("rho_status"),
            "leg_details_from_prereg": {k: arch.get(k) for k in ("leg1_detail", "leg2_detail")
                                        if arch.get(k)},
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
        "combined_with_sealed_settlement": {
            "sealed_settlement_units": settlement["summary"]["total_units_settled"],
            "sealed_record": settlement["summary"].get("record"),
            "addendum_units": round(sum(t["units"] or 0.0 for t in tickets), 2),
            "slate_total_units": round(settlement["summary"]["total_units_settled"]
                                       + sum(t["units"] or 0.0 for t in tickets), 2),
            "slate_line_by_family": ("singles 5-12 (-8.2u), parlays 0-6 (-6.6u), SGPs 1-2 with 1 void "
                                     "(-1.1u); 27 tickets in total"),
            "note": ("the sealed file's `record` field counts the 17 singles only (5-12); its parlay and SGP "
                     "lines sit in their own keys. With this addendum the 11/17-11/18 slate stands at 6 won, "
                     "20 lost and 1 void for -15.90 paper units. The sealed file is not rewritten — this is "
                     "arithmetic on published numbers, printed here so a reader does not have to add them up"),
        },
        "not_graded_legs": skipped,
        "summary": {
            "tickets": len(tickets),
            "won": sum(1 for t in tickets if t["result"] == "WIN"),
            "lost": sum(1 for t in tickets if t["result"] == "LOSS"),
            "void": sum(1 for t in tickets if t["result"] == "VOID"),
            "unsettled": sum(1 for t in tickets if t["result"] == "UNSETTLED"),
            "legs_void": sum(1 for t in tickets for l in t["legs"] if l["result"] == "VOID"),
            "legs_graded": sum(1 for t in tickets for l in t["legs"]
                               if l["result"] in ("WIN", "LOSS")),
            "units": round(sum(t["units"] or 0.0 for t in tickets), 2),
        },
        "validation_note": ("Paper, unfunded, zero-stake output. Every ticket here was published as "
                            "MODEL OUTPUT \u2014 UNVALIDATED; grading it does not make any strategy funded."),
        "flags": [
            {"id": "F-Y01", "severity": "low",
             "item": "Curry's VOID leg rests on the gamebook inactive list, not on a re-read of the box page's own Inactive Players block.",
             "detail": ("the gamebook is the same official source class this repo used to grade the 2026-11-16 "
                        "slate's props, and Curry has no row in the box-score table either, so the grade is not "
                        "in doubt; it is recorded here because the evidence grade differs from the other three "
                        "VOID/loss legs, which cite the box-score page directly")},
            {"id": "F-Y02", "severity": "medium",
             "item": "No market price exists for these tickets, so the WIN payout is the frozen +1.10 convention, not a priced number.",
             "detail": ("the frozen joint probability under the measured rho (printed beside each ticket as "
                        "frozen_price_joint_prob_rho) is the model's own number; with no sportsbook price in "
                        "this repository a won ticket cannot be paid at anything but the convention the "
                        "2026-11-16 SGP addendum used")},
            {"id": "F-Y03", "severity": "high",
             "item": "Every ticket graded here is MODEL OUTPUT — UNVALIDATED, unfunded, zero stake.",
             "detail": ("grading a paper ticket settles the record, not the strategy: no family has passed the "
                        "validation gates (Build A 0/8, Build B 0/10), and the bet surface stays gated closed")},
        ],
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
        "note": ("All four published tickets on the 11/17 slate are graded from official box-score rows, "
                 "official box-score Inactive Players blocks and one official gamebook inactive list, all "
                 "read in this session on 2026-11-19. Net -1.10 paper units (1 won, 2 lost, 1 void); the "
                 "sealed settlement file is not rewritten, and the slate's combined paper result becomes "
                 "-15.90 units across singles, parlays and SGPs."),
        "prev": head,
    }
    ledger["entries"].append(entry)
    # canonicalisation must match scripts/verify_ledger.py and scripts/freeze_prereg.py
    # exactly: json.dumps(sort_keys=True) with DEFAULT separators. An earlier draft used
    # compact separators, which hashes to a different head and broke chain verification.
    canon = json.dumps(entry, sort_keys=True).encode()
    ledger["head"] = hashlib.sha256(canon).hexdigest()
    with open(os.path.join(ROOT, LEDGER), "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"ledger entry {entry['entry']} appended; head {ledger['head'][:16]}\u2026")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
