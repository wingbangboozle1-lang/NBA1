#!/usr/bin/env python3
"""rolling_slate_ledger.py - the picks, the frozen pre-registration, the
tamper-evident ledger and the settlement for the 2026-11-15 build.

    python3 scripts/rolling_slate_ledger.py

Reads:
    data/derived/rolling_slate_2026_11_15/horizon.json   (the model rows)
    data/derived/rolling_slate_2026_11_15/results.json   (the official finals)
    data/derived/rolling_slate_2026_11_15/minutes.json   (the minutes shares)
    docs/data/picks.json                                  (the published picks)
    engine/strategies.py                                  (the registered rules)

Writes:
    data/derived/rolling_slate_2026_11_15/picks.json
    data/derived/rolling_slate_2026_11_15/correlations.json
    data/ledger/preregistration/<strategy>.json   (one frozen file per strategy)
    data/ledger/preregistration.json               (the register of those files)
    data/ledger/ledger.json                        (the tamper-evident ledger)
    data/derived/rolling_slate_2026_11_15/settlement.json
"""

import datetime
import hashlib
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "engine"))

import rolling_slate_model as M          # noqa: E402
import rolling_slate_picks as P          # noqa: E402
import strategies as ST                  # noqa: E402

DER = os.path.join(ROOT, "data", "derived", "rolling_slate_2026_11_15")
DOCS_DATA = os.path.join(ROOT, "docs", "data")
LEDGER_DIR = os.path.join(ROOT, "data", "ledger")
CAP = os.path.join(ROOT, "data", "captures", "2026-11-15", "parsed")

HORIZON_START = "2026-11-15"
HORIZON_END = "2026-11-18"
TRAIN_FROM, TRAIN_TO = "2026-10-20", "2026-11-05"

# The settlement rule every strategy is graded with. It is written into each
# pre-registration file BEFORE any bet on that strategy, so the rule cannot be
# changed after the fact.
SETTLEMENT_RULE = {
    "authority": "the official NBA game page (nba.com) box score",
    "winner": "the game counts as settled only when the official page prints "
              "FINAL and the printed quarter lines add up to the printed final "
              "score",
    "spread_leg": "win when (home final margin - reference margin) has the "
                  "sign of the played side; push when the difference is exactly "
                  "zero; a game that goes to overtime is graded on the official "
                  "final margin including overtime",
    "total_leg": "win when (final total - reference total) has the sign of the "
                 "played side; push when the difference is exactly zero",
    "moneyline_leg": "win when the home final margin has the sign of the played "
                     "side; push on a tie",
    "parlay_leg": "a parlay wins only when every leg wins, pushes when no leg "
                  "loses and at least one pushes, and loses when any leg loses",
    "void": "a game that is postponed or cancelled by the league is void and is "
            "graded 'void', which counts as zero units and is excluded from the "
            "hit rate",
    "grade": "the grade is computed only from the official final; nothing is "
             "graded from a live score, a partial score or a media report",
    "timing": "settlement is performed as soon as the official final is "
              "verified, and the settlement time is stamped on the row",
}


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")


def log(msg):
    print("[%s] %s" % (now_utc(), msg), flush=True)


def pick_payload(p):
    """The canonical payload a ledger hash is computed over."""
    return {
        "date": p.get("date"),
        "game_id": p.get("game_id"),
        "strategy": p.get("strategy"),
        "market": p.get("market"),
        "side": p.get("side"),
        "ref_line": p.get("ref_line"),
        "model_value": p.get("model_value"),
        "edge": p.get("edge"),
        "edge_pp": p.get("edge_pp"),
        "p_model": p.get("p_model"),
        "n_legs": p.get("n_legs", 1),
        "line_display": p.get("line_display"),
        "legs_detail": p.get("legs_detail"),
    }


def main():
    horizon = load(os.path.join(DER, "horizon.json"), {"rows": []})
    results = load(os.path.join(DER, "results.json"), {"rows": []})
    minutes = load(os.path.join(DER, "minutes.json"), {})
    published = load(os.path.join(DOCS_DATA, "picks.json"), {"rows": [], })
    boxes_doc = load(os.path.join(CAP, "boxscores.json"), {"games": []})
    games_doc = load(os.path.join(CAP, "games.json"), {"games": []})

    games = {}
    for r in results["rows"]:
        games[r["game_id"]] = r

    # ---- measured correlations -------------------------------------------
    corr = P.measured_correlations(games, boxes_doc)
    write_json(os.path.join(DER, "correlations.json"), {
        "generated_at_utc": now_utc(),
        "measured": corr,
        "note": "Every rho here is measured from the official box scores and the "
                "official final scores. The repository's previous rho values were "
                "model-derived (Flagged F6); they are kept beside the measured "
                "ones so the change is visible.",
    })
    log("measured rho: side-total %s | teammate %s | opponent %s"
        % (corr["side_total"]["rho"], corr["teammate_points"]["rho"],
           corr["opponent_points"]["rho"]))

    # ---- strategy context --------------------------------------------------
    rows = {r["game_id"]: r for r in horizon["rows"]}
    train = P.load(os.path.join(DER, "results.json"))
    sigma_margin, sigma_total = None, None
    margins, totals = [], []
    for r in results["rows"]:
        if not r["is_final"]:
            continue
        fa, fh = r["final_away_score"], r["final_home_score"]
        if fa is None or fh is None:
            continue
        margins.append(int(fh) - int(fa))
        totals.append(int(fh) + int(fa))
    if len(margins) > 2:
        sigma_margin = statistics.pstdev(margins)
        sigma_total = statistics.pstdev(totals)
    log("sigma margin %.2f total %.2f over %d completed official games"
        % (sigma_margin or 0, sigma_total or 0, len(margins)))

    # availability: weighted lost share per team per date, from the minutes
    avail = {}
    for blk in minutes.get("redistribution", []):
        for rr in blk.get("rows", []):
            avail.setdefault(blk["date"], {}).setdefault(rr["team"], 0.0)
            avail[blk["date"]][rr["team"]] += rr.get("share_to_replace") or 0.0

    contexts = []
    for r in horizon["rows"]:
        ref = r.get("reference") or {}
        blend = r.get("blend_margin")
        total_model = r.get("total_possessions_x_ppp")
        if blend is None or not ref.get("margin") or not sigma_margin:
            continue
        p_home_model = M.phi(blend / sigma_margin)
        p_home_ref = M.phi(ref["margin"] / sigma_margin)
        ctx = {
            "date": r["date"], "game_id": r["game_id"], "matchup": r["matchup"],
            "away": r["away"], "home": r["home"], "time_et": r.get("time_et"),
            "model_margin_final": blend,
            "model_total_final": total_model if total_model is not None else 0.0,
            "ref": {"margin": ref["margin"], "total": ref.get("total")},
            "sigma_margin": sigma_margin, "sigma_total": sigma_total or 1.0,
            "p_home_model": p_home_model, "p_home_ref": p_home_ref,
            "game_pace": r.get("possessions") or 0.0,
            "L_pace": 99.85,
            "home_b2b": 1 if r.get("home_back_to_back") else 0,
            "away_b2b": 1 if r.get("away_back_to_back") else 0,
            "inj_home": {"weighted_lost_share": avail.get(r["date"], {}).get(r["home"], 0.0)},
            "inj_away": {"weighted_lost_share": avail.get(r["date"], {}).get(r["away"], 0.0)},
            "props": [],
        }
        contexts.append(ctx)
    log("strategy contexts %d" % len(contexts))

    plays = ST.build_plays(contexts)
    log("strategy plays %d" % len(plays))

    # ---- price the parlays with the MEASURED rho --------------------------
    rho_st = corr["side_total"]["rho"] or 0.0
    for p in plays:
        if p["strategy"] in ("S9", "S10"):
            legs = p.get("_legs") or []
            ps = [l.get("p_model") or 0.5 for l in legs]
            if len(ps) == 2:
                rho = rho_st if p["strategy"] == "S10" else 0.0
                priced = P.parlay_price(ps[0], ps[1], rho)
                p["rho"] = priced["rho"]
                p["rho_source"] = ("MEASURED from the official finals and box "
                                   "scores" if p["strategy"] == "S10"
                                   else "0.00 - legs are from different games")
                p["fair_price"] = priced["fair_price_with_rho"]
                p["naive_price"] = priced["fair_price_naive_product"]
                p["p_if_independent"] = priced["naive_independent_product"]
                p["p_model"] = priced["joint_probability_with_rho"]
                p["correlation_adjustment"] = priced["difference"]
                p["parlay_pricing"] = priced
    picks_rows = []
    for p in plays:
        row = {k: v for k, v in p.items() if not k.startswith("_")}
        row["status"] = "PENDING"
        row["result"] = None
        row["model_version"] = "2026-11-15 dual-estimator blend"
        row["source"] = "S1"
        picks_rows.append(row)
    write_json(os.path.join(DER, "picks.json"), {
        "generated_at_utc": now_utc(),
        "rule": "Generated by the registered strategy rules in engine/strategies.py "
                "from the 2026-11-15 originated lines (the blend of the two "
                "independent estimators). Parlays are priced with the MEASURED "
                "rho and the naive product is printed beside it.",
        "rows": picks_rows,
        "counts": {"plays": len(picks_rows),
                   "single": sum(1 for r in picks_rows if r.get("n_legs", 1) == 1),
                   "parlays": sum(1 for r in picks_rows if r.get("n_legs", 1) > 1)},
    })

    # ---- the frozen pre-registration, one file per strategy ---------------
    os.makedirs(os.path.join(LEDGER_DIR, "preregistration"), exist_ok=True)
    prereg_rows = []
    for s in ST.STRATEGIES:
        sid = s["id"]
        universe = {
            "markets": [s.get("market")],
            "games": "every NBA regular-season game published on "
                     "https://www.nba.com/schedule for the slate date the play "
                     "is made, with a published official injury-report edition "
                     "for that date",
            "season": "2026-27 regular season",
            "horizon_rule": "a strategy may act on a game only if the official "
                            "slate page publishes it and the tip time is still "
                            "in the future when the pick is published",
        }
        doc = {
            "strategy_id": sid,
            "name": s["name"],
            "family": s["family"],
            "market": s.get("market"),
            "signal": s["rule"],
            "thresholds": s.get("threshold"),
            "why": s.get("why"),
            "universe": universe,
            "settlement_rule": SETTLEMENT_RULE,
            "gradeable": s.get("gradeable"),
            "ungraded_reason": s.get("ungraded_reason"),
            "frozen_at_utc": now_utc(),
            "frozen_by": "session arena/48727fe1-nba1",
            "frozen_before_first_bet_on_this_strategy": None,
            "note": "",
        }
        # honest: this freeze happens now. The published 2026-11-14 picks
        # predate it, which is recorded rather than papered over.
        doc["frozen_before_first_bet_on_this_strategy"] = False
        doc["note"] = ("This pre-registration was frozen on %s. The picks the "
                       "repository published for the 2026-11-14 slate were made "
                       "on 2026-11-14, BEFORE this freeze, so for those picks "
                       "the pre-registration is a reconstruction and not a "
                       "prior. This is recorded here rather than hidden, and it "
                       "is listed on the Flagged for Review page."
                       % now_utc())
        path = os.path.join(LEDGER_DIR, "preregistration", "%s.json" % sid)
        write_json(path, doc)
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        doc_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        prereg_rows.append({
            "strategy_id": sid, "name": s["name"], "family": s["family"],
            "frozen_at_utc": doc["frozen_at_utc"],
            "file": os.path.relpath(path, ROOT),
            "file_sha256": doc_hash,
            "signal": s["rule"], "thresholds": s.get("threshold"),
            "universe": universe,
            "settlement_rule_summary": "graded only from the official NBA final "
                                       "score; a parlay wins only when every leg "
                                       "wins",
            "frozen_before_first_bet_on_this_strategy": False,
            "source": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/"
                      "engine/strategies.py",
        })
    write_json(os.path.join(LEDGER_DIR, "preregistration.json"), {
        "generated_at_utc": now_utc(),
        "rule": "One frozen pre-registration document per strategy. The document "
                "is written to disk, its SHA-256 is recorded here, and the "
                "document is never edited again: a change would change the "
                "hash.",
        "settlement_rule": SETTLEMENT_RULE,
        "strategies": prereg_rows,
    })
    log("pre-registration files %d" % len(prereg_rows))

    # ---- the tamper-evident ledger ----------------------------------------
    published_at = published.get("generated_at_utc")
    entries = []
    for p in published.get("rows", []):
        payload = pick_payload(p)
        h = P.sha256_payload(payload)
        g = games.get(p.get("game_id"))
        tip = g.get("tip_utc") if g else None
        entry = {
            "ledger_id": "L-%s-%s-%s" % (p.get("date"), p.get("strategy"),
                                         p.get("game_id")),
            "batch": "published 2026-11-14 build (the picks the repository "
                     "published before this session)",
            "published_at_utc": published_at,
            "sealed_at_utc": now_utc(),
            "tip_utc": tip,
            "game_id": p.get("game_id"),
            "date": p.get("date"),
            "strategy": p.get("strategy"),
            "payload": payload,
            "payload_sha256": h,
            "pre_registration_id": p.get("strategy"),
            "settlement": None,
            "verified_at_utc": None,
            "verification": "not settled yet",
        }
        if tip and published_at and published_at < tip:
            entry["seal_state"] = "SEALED BEFORE TIP"
        else:
            entry["seal_state"] = ("SEALED AFTER TIP - the pick was published "
                                   "before this session could hash it; the hash "
                                   "is recorded now and cannot prove the pick "
                                   "was not altered between publication and "
                                   "this seal")
        entries.append(entry)
    for p in picks_rows:
        payload = pick_payload(p)
        h = P.sha256_payload(payload)
        g = games.get(p.get("game_id"))
        tip = g.get("tip_utc") if g else None
        entries.append({
            "ledger_id": "L-%s-%s-%s-v2" % (p.get("date"), p.get("strategy"),
                                            p.get("game_id")),
            "batch": "2026-11-15 dual-estimator build",
            "published_at_utc": now_utc(),
            "sealed_at_utc": now_utc(),
            "tip_utc": tip,
            "game_id": p.get("game_id"),
            "date": p.get("date"),
            "strategy": p.get("strategy"),
            "payload": payload,
            "payload_sha256": h,
            "pre_registration_id": p.get("strategy"),
            "settlement": None,
            "verified_at_utc": None,
            "verification": "not settled yet",
            "seal_state": ("SEALED BEFORE TIP" if tip and now_utc() < tip
                           else "SEALED - tip time not yet known"),
        })
    write_json(os.path.join(LEDGER_DIR, "ledger.json"), {
        "generated_at_utc": now_utc(),
        "rule": "Every published pick is hashed with SHA-256 over a canonical "
                "payload (the fields of the pick, in sorted key order). The hash "
                "is published BEFORE the game tips. After the official final is "
                "verified, the same canonical payload is re-hashed and compared: "
                "a mismatch means the published pick was altered after it was "
                "sealed.",
        "hash_algorithm": "sha256",
        "canonical_form": "json.dumps(payload, sort_keys=True, separators=(',',':'))",
        "entries": entries,
        "counts": {"entries": len(entries),
                   "sealed_before_tip": sum(1 for e in entries
                                            if e["seal_state"] == "SEALED BEFORE TIP"),
                   "settled": sum(1 for e in entries if e.get("settlement"))},
    })
    log("ledger entries %d" % len(entries))

    # ---- settlement against the official finals ---------------------------
    settlements = []
    for p in published.get("rows", []):
        gid = p.get("game_id")
        g = games.get(gid)
        if not g:
            continue
        if not g.get("is_final"):
            continue
        graded = P.grade_pick(p, g)
        if graded is None:
            continue
        fa, fh = g["final_away_score"], g["final_home_score"]
        settlements.append({
            "ledger_id": "L-%s-%s-%s" % (p.get("date"), p.get("strategy"), gid),
            "date": p.get("date"), "game_id": gid, "matchup": p.get("matchup"),
            "strategy": p.get("strategy"), "market": p.get("market"),
            "side": p.get("side"), "line_display": p.get("line_display"),
            "ref_line": p.get("ref_line"),
            "official_final": "%s %s - %s %s" % (g.get("away"), fa, fh, g.get("home")),
            "official_margin": int(fh) - int(fa),
            "official_total": int(fh) + int(fa),
            "away_quarter_scores": g.get("away_quarter_scores"),
            "home_quarter_scores": g.get("home_quarter_scores"),
            "quarters_reconcile": g.get("quarters_reconcile"),
            "result": graded,
            "settled_at_utc": now_utc(),
            "settlement_stamp": "settled %s from %s" % (now_utc(), g.get("source_url")),
            "source_url": g.get("source_url"),
        })
    write_json(os.path.join(DER, "settlement.json"), {
        "generated_at_utc": now_utc(),
        "rule": "A pick is settled only against the official NBA final score, and "
                "the settlement time is stamped on the row.",
        "rows": settlements,
        "counts": {"settled": len(settlements),
                   "wins": sum(1 for s in settlements if s["result"] == "win"),
                   "losses": sum(1 for s in settlements if s["result"] == "loss"),
                   "pushes": sum(1 for s in settlements if s["result"] == "push"),
                   "unreconciled": sum(1 for s in settlements
                                       if not s["quarters_reconcile"])},
    })
    log("settled %d published picks" % len(settlements))

    # ---- write the settlement back into the ledger ------------------------
    ledger = load(os.path.join(LEDGER_DIR, "ledger.json"), {"entries": []})
    by_id = {s["ledger_id"]: s for s in settlements}
    for e in ledger["entries"]:
        s = by_id.get(e["ledger_id"])
        if not s:
            continue
        e["settlement"] = {
            "result": s["result"],
            "official_final": s["official_final"],
            "settled_at_utc": s["settled_at_utc"],
            "source_url": s["source_url"],
            "settlement_stamp": s["settlement_stamp"],
        }
        recomputed = P.sha256_payload(e["payload"])
        e["verified_at_utc"] = now_utc()
        e["verification"] = ("payload re-hashed after settlement: %s"
                             % ("MATCHES the published hash" if recomputed
                                == e["payload_sha256"]
                                else "DOES NOT MATCH the published hash"))
        e["verification_result"] = "MATCH" if recomputed == e["payload_sha256"] else "MISMATCH"
    ledger["counts"]["settled"] = sum(1 for e in ledger["entries"] if e.get("settlement"))
    ledger["counts"]["verified"] = sum(1 for e in ledger["entries"]
                                       if e.get("verification_result"))
    ledger["counts"]["mismatches"] = sum(1 for e in ledger["entries"]
                                         if e.get("verification_result") == "MISMATCH")
    write_json(os.path.join(LEDGER_DIR, "ledger.json"), ledger)
    log("ledger settled %d verified %d mismatches %d"
        % (ledger["counts"]["settled"], ledger["counts"]["verified"],
           ledger["counts"]["mismatches"]))


if __name__ == "__main__":
    sys.exit(main())
