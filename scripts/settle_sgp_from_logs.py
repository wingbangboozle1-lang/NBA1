#!/usr/bin/env python3
"""settle_sgp_from_logs.py — resolve the prop (SGP) tickets in a settlement file
from the official per-player game logs, append the result to that settlement file's
directory as an addendum, and chain the addendum into the ledger.

Why an addendum instead of a rewrite
------------------------------------
`data/settlement/settlement_<slate>.json` is hash-chained into `data/ledger/ledger.json`
(entry type `settlement_record`). Rewriting it would break that entry's digest, and the
ledger is append-only by design. `scripts/settle_slate.py` deliberately leaves a prop
ticket UNSETTLED when it has no official box score to read — correct, but it means the
ticket stays open after the gamebooks exist. This script closes it with the official
gamebook evidence and APPENDS a new ledger entry; nothing existing is touched.

Grading rules (copied from `data/settlement/settlement_2026-11-14.json`, key
`sgp_candidates[].void_convention`, which is the frozen record of the convention):
  * a leg whose player did not appear in the official box score is VOID and removed;
  * a remaining OVER leg wins if actual points > line, loses if actual <= line;
  * any losing leg loses the stake (1.10 paper units at the -110 convention);
  * a ticket with no remaining legs is VOID with no stake.

Usage
  python3 scripts/settle_sgp_from_logs.py --settlement data/settlement/settlement_2026-11-16.json \
      --logs data/official/player_game_logs_2026-11-16.json --by "arena/... "
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = "data/ledger/ledger.json"


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(rel):
    return sha_bytes(open(os.path.join(ROOT, rel), "rb").read())


def canon(d):
    return json.dumps(d, sort_keys=True).encode()


def norm(s):
    s = s.lower()
    s = re.sub(r"[^a-z ]", " ", s)
    return " ".join(s.split())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--settlement", required=True)
    ap.add_argument("--logs", required=True)
    ap.add_argument("--by", default="scripts/settle_sgp_from_logs.py")
    ap.add_argument("--at", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    st = load(args.settlement)
    logs = load(args.logs)
    gid_by_matchup = {}
    for g in logs["games"]:
        gid_by_matchup[g["matchup"]] = g["game_id"]
    by_game = {}
    for r in logs["rows"]:
        by_game.setdefault(r["game_id"], []).append(r)

    out, unresolved = [], []
    for t in st.get("sgp_candidates", []):
        game = t.get("game")
        gid = gid_by_matchup.get(game)
        if gid is None:
            unresolved.append({"game": game, "why": "no official gamebook captured for this matchup"})
            continue
        legs_out, live_legs = [], []
        for leg_text in t.get("legs", []):
            m = re.match(r"^(.*?)\s*\((.*?)\)\s*(OVER|UNDER)\s*([\d.]+)$", leg_text.strip())
            if not m:
                unresolved.append({"game": game, "leg": leg_text,
                                   "why": "leg text does not parse as '<player> (<TEAM>) OVER <line>'"})
                continue
            player, team, direction, line = m.group(1).strip(), m.group(2), m.group(3), float(m.group(4))
            rows = [r for r in by_game[gid] if norm(r["player"]) == norm(player)]
            played = [r for r in rows if r.get("played")]
            if not played:
                note = rows[0].get("dnp_note") if rows else None
                legs_out.append({
                    "leg_text": leg_text, "player": player, "team": team, "line": line,
                    "actual_pts": None, "played": False,
                    "result": "VOID (player did not appear)"
                              + (f" — gamebook row prints {note}" if note else
                                 " — no played row in the official gamebook; the gamebook's Inactive"
                                 " line for his team names him"),
                    "evidence": f"{logs['games'][[g['game_id'] for g in logs['games']].index(gid)]['gamebook']} (official gamebook)",
                    "source_url": rows[0]["source_pdf"] if rows else
                                  next(g["source_pdf"] for g in logs["games"] if g["game_id"] == gid),
                })
                continue
            r = played[0]
            actual = r.get("pts")
            if direction == "OVER":
                res = "WIN" if actual > line else "LOSS"
            else:
                res = "WIN" if actual < line else "LOSS"
            legs_out.append({
                "leg_text": leg_text, "player": player, "team": team, "line": line,
                "actual_pts": actual, "played": True, "min": r.get("min"),
                "reb": r.get("reb"), "ast": r.get("ast"),
                "result": res,
                "evidence": "player row in the official gamebook box score",
                "source_url": r["source_pdf"], "source_text": r["source_text"],
            })
            live_legs.append(res)
        if not legs_out:
            unresolved.append({"game": game, "why": "no leg could be graded"})
            continue
        if any(x == "LOSS" for x in live_legs):
            result, units = "LOSS", -1.10
        elif live_legs and all(x == "WIN" for x in live_legs):
            result, units = "WIN", round(1.10 * 1.0, 2)
        else:
            result, units = "VOID (no live legs)", 0.0
        out.append({
            "date": t.get("date"), "game": game, "kind": t.get("kind"),
            "legs": legs_out,
            "void_convention": ("copied from data/settlement/settlement_2026-11-14.json: "
                                "an inactive player's leg is VOID and removed; any losing "
                                "remaining leg loses the stake (1.10 paper units)"),
            "frozen_price_joint_prob_rho": t.get("frozen_price_joint_prob_rho"),
            "frozen_price_independent_printed_beside": t.get("frozen_price_independent_printed_beside"),
            "previous_state": t.get("result"),
            "result": result, "units": units,
            "graded_from": "official gamebook box scores (data/official/player_game_logs_%s.json)"
                           % logs.get("coverage") and args.logs,
            "sources": sorted({l["source_url"] for l in legs_out}),
        })

    addendum = {
        "title": f"SGP settlement addendum — {os.path.basename(args.settlement)}",
        "supplements": args.settlement,
        "supplements_sha256": sha_file(args.settlement),
        "graded_at_utc": args.at or "",
        "graded_by": args.by,
        "rule": ("Prop tickets left UNSETTLED by scripts/settle_slate.py (no box score at that time) are "
                 "graded here from the official gamebook, using the void convention frozen in "
                 "data/settlement/settlement_2026-11-14.json. Nothing in the settlement file is rewritten."),
        "evidence": args.logs,
        "tickets": out,
        "unresolved": unresolved,
        "summary": {
            "tickets": len(out),
            "wins": sum(1 for t in out if t["result"] == "WIN"),
            "losses": sum(1 for t in out if t["result"] == "LOSS"),
            "voids": sum(1 for t in out if t["result"].startswith("VOID")),
            "units": round(sum(t["units"] for t in out), 2),
            "void_legs": [f"{t['game']}: {l['player']} ({l['team']}) — {l['result']}"
                          for t in out for l in t["legs"] if not l["played"]],
        },
    }
    print(json.dumps(addendum["summary"], indent=1))
    for t in out:
        print(f"  {t['game']:8s} {t['result']:5s} {t['units']:+.2f}  " +
              " | ".join(f"{l['player']} {l['result']}" for l in t["legs"]))
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    base = os.path.basename(args.settlement).replace("settlement_", "sgp_settlement_")
    out_rel = os.path.join("data/settlement", base)
    with open(os.path.join(ROOT, out_rel), "w", encoding="utf-8") as fh:
        json.dump(addendum, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", out_rel)

    ledger = load(LEDGER)
    prev = ledger["head"]
    n = ledger["entries"][-1]["entry"]
    stamp = addendum["graded_at_utc"] or "undated"
    entry = {
        "entry": n + 1,
        "type": "sgp_settlement_addendum",
        "at_utc": stamp,
        "file": out_rel,
        "sha256": sha_file(out_rel),
        "supplements": args.settlement,
        "supplements_sha256": addendum["supplements_sha256"],
        "evidence": args.logs,
        "evidence_sha256": sha_file(args.logs),
        "summary": addendum["summary"],
        "graded_by": args.by,
        "prev": prev,
    }
    ledger["entries"].append(entry)
    ledger["head"] = sha_bytes(canon(entry))
    with open(os.path.join(ROOT, LEDGER), "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"ledger entry {entry['entry']} appended; head {ledger['head'][:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
