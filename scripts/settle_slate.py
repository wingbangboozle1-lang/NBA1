#!/usr/bin/env python3
"""settle_slate.py — settle any published rolling slate from official finals.

This generalises `scripts/settle_2026_11_14.py` (which is kept unchanged as the
record for that slate, and as the specification this script reuses).  Nothing
here re-derives a rule: every grading rule is copied from the frozen 11/14
settlement file (`data/settlement/settlement_2026-11-14.json`, key `rules`) and
is printed into the output so a reader can diff the two.

Requirement this answers (brief, one line): "Settle the sealed ledger from
official finals as soon as each game day ends, and keep the settlement stamp
visible."  (register R19)

Design rules
------------
1. **Nothing is settled unless the official page says Final.**  A row is graded
   only when `data/official/results_<date>.json` holds `status == "FINAL"` for
   that game AND the quarters printed on the official page sum to the printed
   final.  A row that is in progress, not tipped, or halted is reported as
   UNSETTLED and the run refuses to write a settlement for that date (exit 3).
2. **Only pre-tip published picks are graded.**  The picks and lines are read
   from `data/archive/horizon_picks_<slate start>.json` (the byte-identical
   pre-tip archive), never from the working `data/derived/` files, which roll
   forward.  The archive digest is asserted against the ledger entry that
   committed to it, so a pick that changed after publication cannot be graded.
3. **No market price is invented.**  Units use the repository's paper -110
   convention, exactly as the 11/14 settlement states it, and every row prints
   the convention it used.
4. **Ledger entries are appended, never rewritten.**  The chain head is read
   from the existing ledger; two entries are appended (settlement record +
   a verification entry that re-hashes the archived pre-tip files).

Inputs
------
  data/ledger/ledger.json                       chain head and pre-tip entries
  data/archive/horizon_picks_<start>.json       pre-tip published picks
  data/archive/horizon_lines_<start>.json       pre-tip published lines
  data/official/results_<date>.json             official finals (LIVE FEED slot)

Outputs
-------
  data/settlement/settlement_<slate>.json
  data/ledger/ledger.json                       two entries appended

Run
---
  python3 scripts/settle_slate.py --slate 2026-11-15
  python3 scripts/settle_slate.py --slate 2026-11-15 --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LEDGER = "data/ledger/ledger.json"


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def dump(rel, doc):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", rel)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(rel: str) -> str:
    return sha256_bytes(open(os.path.join(ROOT, rel), "rb").read())


# ---------------------------------------------------------------------------
# verification of the official finals
# ---------------------------------------------------------------------------
def verify_final(row):
    """Return (ok, reasons).  A final is accepted only on the official page's
    own evidence, re-checked here rather than trusted from the capture."""
    reasons = []
    if row.get("status") != "FINAL":
        reasons.append(f"status is {row.get('status')!r}, not 'FINAL'")
    for side in ("away", "home"):
        pts = row.get(f"{side}_pts")
        qs = row.get(f"{side}_quarters")
        if pts is None or not isinstance(qs, list):
            reasons.append(f"{side}: final or quarters missing")
            continue
        if sum(qs) != pts:
            reasons.append(f"{side}: quarters {qs} sum to {sum(qs)}, printed final {pts}")
    ot = row.get("ot_periods") or 0
    if ot and isinstance(row.get("away_quarters"), list):
        if len(row["away_quarters"]) != 4 + ot:
            reasons.append(f"{ot} OT periods but {len(row['away_quarters'])} away quarters")
    if not row.get("source_url"):
        reasons.append("no official source_url on the row")
    return (not reasons), reasons


def fnum(x):
    """The repo's line convention: a minus sign is part of the number."""
    return float(x)


def grade_single(pick, away, away_pts, home, home_pts):
    """Copied rule (11/14 settlement, key rules.single): TEAM -x.x must win by
    more than x.x; exactly x.x is a PUSH."""
    if pick["pick_side"] == "PASS" or not pick.get("pick_line"):
        return {"result": "NO BET (gate failed at publication)", "units": 0.0}
    team, line_txt = pick["pick_line"].rsplit(" ", 1)
    line = fnum(line_txt)
    if team == home:
        margin = home_pts - away_pts
    elif team == away:
        margin = away_pts - home_pts
    else:
        raise AssertionError(f"pick team {team} is not in {away}@{home}")
    if margin > -line:
        return {"result": "WIN", "units": 1.0, "margin": margin}
    if margin == -line:
        return {"result": "PUSH", "units": 0.0, "margin": margin}
    return {"result": "LOSS", "units": -1.10, "margin": margin}


def grade_leg(leg_text, finals_by_matchup):
    """leg_text is '<AWAY>@<HOME> — <TEAM> -x.x' as published."""
    matchup, side = leg_text.split(" — ")
    team, line_txt = side.rsplit(" ", 1)
    line = fnum(line_txt)
    row = finals_by_matchup[matchup]
    away, home = row["away"], row["home"]
    if team == home:
        margin = row["home_pts"] - row["away_pts"]
    else:
        margin = row["away_pts"] - row["home_pts"]
    if margin > -line:
        res = "WIN"
    elif margin == -line:
        res = "PUSH"
    else:
        res = "LOSS"
    return {"leg": leg_text, "result": res, "margin": margin,
            "source_game_url": row["source_url"]}


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--slate", required=True,
                    help="slate start date, e.g. 2026-11-15 (matches "
                         "data/archive/horizon_picks_<date>.json)")
    ap.add_argument("--settle-date", action="append", default=None,
                    help="date to settle (repeatable). Default: every date in "
                         "the archive. A date is settled only if all its games "
                         "are verified finals.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--at", default=None, help="settled_at stamp (UTC, ISO)")
    ap.add_argument("--by", default="scripts/settle_slate.py",
                    help="who/what settled it (session id or script)")
    args = ap.parse_args(argv)

    picks_base = f"horizon_picks_{args.slate}.json"
    lines_base = f"horizon_lines_{args.slate}.json"
    if not os.path.exists(os.path.join(ROOT, LEDGER)):
        print(f"MISSING input {LEDGER}", file=sys.stderr)
        return 2
    ledger = load(LEDGER)

    # The archive that settles is the LATEST pre-tip seal the ledger committed
    # to for this slate.  A pre-tip amendment (same basenames, later archive
    # directory, entry type pre_tip_publication carrying supersedes_entry) is a
    # legal seal under the brief's "publish the hash before tip" rule and
    # supersedes the earlier one; the ledger's `files` map is the seal index.
    # Every candidate must hash to its recorded digest at its recorded path —
    # a pick that changed after publication cannot be graded.
    picks_rel = lines_rel = committed = None
    for e in ledger["entries"]:
        files = e.get("files") or {}
        cand_p = [f for f, h in files.items()
                  if os.path.basename(f) == picks_base
                  and os.path.exists(os.path.join(ROOT, f)) and sha256_file(f) == h]
        cand_l = [f for f, h in files.items()
                  if os.path.basename(f) == lines_base
                  and os.path.exists(os.path.join(ROOT, f)) and sha256_file(f) == h]
        if cand_p and cand_l:
            picks_rel, lines_rel, committed = cand_p[0], cand_l[0], e
    if committed is None:
        print(f"REFUSED: no pre-tip seal for {args.slate} (searched every ledger "
              f"entry's files map for {picks_base} / {lines_base} and re-hashed each "
              f"candidate). A pick that changed after publication cannot be graded.",
              file=sys.stderr)
        return 4

    picks = load(picks_rel)
    lines = load(lines_rel)
    picks_sha = sha256_file(picks_rel)
    lines_sha = sha256_file(lines_rel)
    print(f"pre-tip archive verified against ledger entry {committed['entry']} "
          f"({committed.get('at_utc')}), sha {picks_sha[:16]}…")
    if committed.get("supersedes_entry"):
        print(f"note: entry {committed['entry']} is a pre-tip amendment superseding "
              f"entry {committed['supersedes_entry']}; this run grades the amended "
              f"seal ({picks_rel})")

    # Slate dates present in the archive.
    slate_dates = sorted({r["date"] for r in picks["singles"]} |
                         {r["date"] for r in picks.get("parlays", [])} |
                         {r["date"] for r in picks.get("sgp_candidates", [])})
    dates = args.settle_date or slate_dates

    settled_dates, unsettled = [], {}
    finals_by_matchup, finals_by_id = {}, {}
    for date in dates:
        rel = f"data/official/results_{date}.json"
        if not os.path.exists(os.path.join(ROOT, rel)):
            unsettled[date] = [f"no official results file ({rel})"]
            continue
        feed = load(rel)
        rows = [r for r in feed["rows"] if r.get("date") == date]
        problems = []
        for r in rows:
            ok, why = verify_final(r)
            if not ok:
                problems.append(f"{r.get('away')}@{r.get('home')} "
                                f"{r.get('game_id')}: " + "; ".join(why))
        if not rows:
            problems.append("no games on the official feed for this date")
        if problems:
            unsettled[date] = problems
            continue
        for r in rows:
            r = dict(r, date=date)
            finals_by_matchup[f"{r['away']}@{r['home']}"] = r
            finals_by_id[r["game_id"]] = r
        settled_dates.append(date)

    print(f"dates in archive : {', '.join(slate_dates)}")
    print(f"ready to settle  : {', '.join(settled_dates) or '(none)'}")
    for d, why in unsettled.items():
        print(f"UNSETTLED {d}: {len(why)} game(s) not verified final")
        for w in why[:6]:
            print("   -", w)

    if not settled_dates:
        print("Nothing to settle: no date has every game verified final.",
              file=sys.stderr)
        return 3

    rules = load("data/settlement/settlement_2026-11-14.json")["rules"]
    rules = dict(rules)
    rules["source"] = ("grading rules copied verbatim from "
                       "data/settlement/settlement_2026-11-14.json (frozen)")

    singles_out = []
    for row in picks["singles"]:
        if row["date"] not in settled_dates:
            continue
        g = finals_by_id[row["game_id"]]
        res = grade_single(row["pick"], g["away"], g["away_pts"], g["home"], g["home_pts"])
        singles_out.append({
            "date": row["date"], "game_id": row["game_id"], "matchup": row["matchup"],
            "pick_side": row["pick"].get("pick_side"),
            "pick_line": row["pick"].get("pick_line"),
            "pick_prob": row["pick"].get("pick_prob"),
            "gate": row["pick"].get("gate"),
            "away": g["away"], "away_pts": g["away_pts"],
            "home": g["home"], "home_pts": g["home_pts"],
            "away_quarters": g.get("away_quarters"),
            "home_quarters": g.get("home_quarters"),
            "ot_periods": g.get("ot_periods"),
            "margin_pick_team": res.get("margin"),
            "result": res["result"], "units": res["units"],
            "price_convention": "paper -110: stake 1.10 to win 1.00",
            "source_game_url": g["source_url"],
            "source_finals": f"data/official/results_{row['date']}.json (official LINESCORES)",
        })

    parlays_out = []
    for row in picks.get("parlays", []):
        if row["date"] not in settled_dates:
            continue
        legs = [row[k] for k in ("leg1", "leg2", "leg3") if row.get(k)]
        leg_results = [grade_leg(l, finals_by_matchup) for l in legs]
        ok = all(l["result"] == "WIN" for l in leg_results)
        parlays_out.append({
            "date": row["date"], "legs": legs, "leg_results": leg_results,
            "joint_published": {k: row.get(k) for k in
                                ("joint_lb", "joint_ub", "rho_lb", "rho_ub", "joint_prob_rho")},
            "naive_product_printed_beside": (row.get("joint_prob_independent")
                                             or row.get("p1_times_p2")),
            "result": "WIN" if ok else "LOSS",
            "units": (1.10 * ((row.get("fair_odds_lb") or 2.64) - 1) if ok else -1.10),
            "price_convention": "paper -110 legs; fair-odds band published pre-tip",
            "sources": row.get("sources", []),
        })

    # SGP: a leg whose player did not appear is VOID.  Appearance is only known
    # from an official box score; this script records the legs and marks the
    # ticket UNSETTLED rather than guessing.  (11/14 was graded by hand from
    # official box scores in settle_2026_11_14.py, which is kept as the record.)
    sgp_out = []
    for row in picks.get("sgp_candidates", []):
        if row["date"] not in settled_dates:
            continue
        sgp_out.append({
            "date": row["date"], "game": row.get("game"), "kind": row.get("kind"),
            "legs": [row[k] for k in ("leg1", "leg2") if row.get(k)],
            "frozen_price_joint_prob_rho": row.get("joint_prob_rho"),
            "frozen_price_independent_printed_beside": row.get("joint_prob_independent"),
            "result": "UNSETTLED — player appearance requires the official box score",
            "units": None,
            "why_not_settled": ("Grading a prop needs that player's official box-score "
                                "row (did he appear?). No box score was captured for "
                                "this slate in this run, so the ticket is left open "
                                "rather than graded on inference."),
            "sources": row.get("sources", []),
        })

    settled_units = [r["units"] for r in singles_out] + \
                    [r["units"] for r in parlays_out]
    summary = {
        "dates_settled": settled_dates,
        "dates_unsettled": sorted(unsettled),
        "singles_published": len(singles_out),
        "wins": sum(1 for r in singles_out if r["result"] == "WIN"),
        "losses": sum(1 for r in singles_out if r["result"] == "LOSS"),
        "pushes": sum(1 for r in singles_out if r["result"] == "PUSH"),
        "no_bets": sum(1 for r in singles_out if r["result"].startswith("NO BET")),
        "singles_units_at_minus110": round(sum(r["units"] for r in singles_out), 2),
        "parlays_published": len(parlays_out),
        "parlays_won": sum(1 for r in parlays_out if r["result"] == "WIN"),
        "parlay_units": round(sum(r["units"] for r in parlays_out), 2),
        "sgp_published": len(sgp_out),
        "sgp_settled": sum(1 for r in sgp_out if r["units"] is not None),
        "total_units_settled": round(sum(settled_units), 2),
        "validation_note": ("Every ticket was published as MODEL OUTPUT — UNVALIDATED, "
                            "unfunded, zero-stake paper output. No strategy is funded."),
    }
    summary["record"] = f"{summary['wins']}-{summary['losses']}-{summary['pushes']}"

    settlement = {
        "title": f"Settlement — {args.slate} slate (settled from official finals)",
        "settled_at_utc": args.at,
        "settled_by": args.by,
        "slate_archive": {"picks": picks_rel, "picks_sha256": picks_sha,
                          "lines": lines_rel, "lines_sha256": lines_sha,
                          "ledger_entry_committing_it": committed["entry"]},
        "rules": rules,
        "official_finals_rule": ("A game is graded only when its official page printed "
                                 "Final and its quarter scores sum to the printed final; "
                                 "data/official/results_<date>.json rows are re-checked "
                                 "by verify_final() at settlement time."),
        "singles": singles_out,
        "parlays": parlays_out,
        "sgp_candidates": sgp_out,
        "summary": summary,
        "sources": sorted({r["source_url"] for r in finals_by_id.values()} |
                          {f"data/official/results_{d}.json" for d in settled_dates}),
    }

    print(json.dumps(summary, indent=1))
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    # --- idempotency guard (2026-11-16, session arena/0e9c924f-nba1, §50 N03) --
    # The scheduled workflow's settle step re-runs settle_slate after every
    # successful fetch. If no new date has become settleable since the record
    # was written, re-running would overwrite data/settlement/<slate>.json and
    # append duplicate verification/settlement ledger entries. verify_ledger
    # re-hashes that settlement file against the digest recorded at entry 7,
    # so the overwrite alone would turn the chain check red. Exit 0 without
    # touching anything when every date settleable right now is already in the
    # existing record; a genuinely new settleable date still takes the normal
    # path (with the vintage-mismatch caveat flagged in F126 (renumbered from F115 at merge)).
    out_rel_existing = f"data/settlement/settlement_{args.slate}.json"
    existing_path = os.path.join(ROOT, out_rel_existing)
    # A date is "already settled" if THIS file covers it OR any settlement
    # record already hash-chained into the ledger graded it (slates overlap:
    # e.g. the 11/14 archive also carries 11/15 games, which entries 6-7
    # already settled from the 11/15 slate). Without the chain-wide half, the
    # scheduled re-settle of an overlapping slate re-grades a date another
    # entry froze, overwrites the older settlement file and breaks that
    # entry's digest (observed 2026-11-16T15:23Z, dropped in the same class
    # as main's e9f1d1f).
    chain_settled = set()
    for _e in ledger["entries"]:
        if _e.get("type") == "settlement_record":
            chain_settled |= set((_e.get("summary") or {}).get("dates_settled") or [])
        chain_settled |= set(_e.get("settled_dates") or [])
    if os.path.exists(existing_path):
        existing = json.load(open(existing_path, encoding="utf-8"))
        prev_settled = set(existing.get("summary", {}).get("dates_settled") or [])
        if settled_dates and set(settled_dates) <= (prev_settled | chain_settled):
            print(f"already settled: {out_rel_existing} covers "
                  f"{sorted(prev_settled)} and the ledger chain covers "
                  f"{sorted(chain_settled)}; nothing new to settle "
                  f"({sorted(settled_dates)} is a subset) - "
                  "idempotent skip, no ledger append")
            return 0
    elif settled_dates and set(settled_dates) <= chain_settled:
        print(f"already settled in the ledger chain: {sorted(chain_settled)}; "
              f"{sorted(settled_dates)} adds nothing - idempotent skip, "
              "no settlement file written, no ledger append")
        return 0

    stamp = args.at or __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    settlement["settled_at_utc"] = stamp
    out_rel = f"data/settlement/settlement_{args.slate}.json"
    dump(out_rel, settlement)

    # --- ledger: append, never rewrite -------------------------------------
    prev = ledger["head"]
    n = ledger["entries"][-1]["entry"]
    e_ver = {
        "entry": n + 1, "type": "settlement_settlement_verification",
        "at_utc": stamp,
        "verifies_entry": committed["entry"],
        "files_at_settlement": {picks_rel: picks_sha, lines_rel: lines_sha},
        "unchanged_since_pre_tip": True,
        "settled_dates": settled_dates,
        "prev": prev,
    }
    prev = sha256_bytes(json.dumps(e_ver, sort_keys=True).encode())
    e_set = {
        "entry": n + 2, "type": "settlement_record",
        "at_utc": stamp,
        "file": out_rel,
        "sha256": sha256_file(out_rel),
        "official_finals_files": [f"data/official/results_{d}.json" for d in settled_dates],
        "settled_by": args.by,
        "summary": {k: summary[k] for k in
                    ("record", "singles_units_at_minus110", "parlay_units",
                     "total_units_settled", "dates_settled", "dates_unsettled")},
        "prev": prev,
    }
    ledger["entries"].extend([e_ver, e_set])
    ledger["head"] = sha256_bytes(json.dumps(e_set, sort_keys=True).encode())
    dump(LEDGER, ledger)
    print(f"ledger entries {e_ver['entry']} and {e_set['entry']} appended; "
          f"head {ledger['head']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
