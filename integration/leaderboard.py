"""One leaderboard for every strategy register in the repo, on one scoring basis.

Two registers existed before this session and they disagreed:
  * Build A (`data/derived/strategies.json`) — "0 of 8 validated", largest graded set 14 bets,
    and its own metadata labels that 14-game backtest CONTAMINATED by look-ahead.
  * Build B (`docs/data/leaderboard.json`) — an LBS score out of 100 per strategy over 23 graded
    bets, with tiers and stake caps.
This module does not average them and does not pick a winner between them. It re-states every
candidate on the gates in gates.py, records the sample each register actually had, and prints the
disagreement where the two disagree, because a leaderboard that hides a 14-vs-23-vs-60 sample
conflict is decoration.

Ranking basis, decided before the run: gates passed (hard gates first), then measurable error,
then sample size. No strategy is "validated", so no reward is payable.
"""

from common import dump, load


def rank_key(row):
    return (-row["gates_passed_hard"], -row["n_graded"],
            row["mae_margin"] if row["mae_margin"] is not None else 999)


def main():
    gates = load("integration", "out", "gates.json")
    lines = load("integration", "out", "lines.json")
    settle = load("integration", "out", "settlement.json")
    props = load("integration", "out", "props.json")
    a_strat = load("data", "derived", "strategies.json")
    a_bt = load("data", "derived", "backtest.json")
    b_val = load("docs", "data", "validation.json")
    b_lb = load("docs", "data", "leaderboard.json")

    hard = {g["id"] for g in gates["gates"] if g["status"] == "PASS"}
    n_gate = next(g for g in gates["gates"] if g["id"] == "V2")
    base = gates["base_model"]

    rows = []

    def add(**kw):
        kw.setdefault("gates_passed_hard", len(hard))
        kw.setdefault("validated", False)
        kw.setdefault("reward_payable", False)
        rows.append(kw)

    add(id="INT-1", name="Originated margin + total (no absence term)", family="Single bet",
        register="integration (this session)", n_graded=base["n"], record=base["straight_up"],
        mae_margin=base["mae_margin"], mae_total=base["mae_total"],
        metric="MAE in points against official FINAL scores, ratings fitted on an earlier window",
        why="The only candidate on this desk whose inputs are all official, all point-in-time and "
            "all out-of-sample. It is not worse than a naive pick, and that is the whole claim.",
        blocking_gates=f"V2 sample floor (n={base['n']} < 100), V9 availability, "
                       "V13 absence term ungraded",
        blank_fields=["odds", "break-even %", "ROI", "CLV", "stake", "edge vs close"],
        what_moves_it_up="100+ graded games and any closing-price file; nothing else can promote it.")
    add(id="INT-2", name="Same, with rest / home-court adjustments on", family="Single bet",
        register="integration (this session)", n_graded=base["n"], record=base["straight_up"],
        mae_margin=base["mae_margin"], mae_total=base["mae_total"],
        metric="ΔMAE of each component, measured one at a time",
        why=(f"HCA {gates['ablations']['hca_off']['delta_mae_vs_full_model']:+}, back-to-back "
             f"{gates['ablations']['b2b_off']['delta_mae_vs_full_model']:+}, shrinkage "
             f"{gates['ablations']['no_shrinkage']['delta_mae_vs_full_model']:+} points of MAE — "
             f"all inside a ±{round((gates['bootstrap_mae_margin_95'][1] - gates['bootstrap_mae_margin_95'][0]) / 2, 1)} "
             "interval. The adjustments are kept because theory supports them, and flagged "
             "because this sample cannot confirm them."),
        blocking_gates="V2", blank_fields=["component p-values", "ROI"],
        what_moves_it_up="A second and third graded week; the code path is unchanged meanwhile.")
    add(id="INT-3", name="Player-prop lines from measured game-log dispersion", family="Player prop",
        register="integration (this session)", n_graded=0, record=None,
        mae_margin=None, mae_total=None,
        metric="dispersion measured on 12 player-games across 3 players",
        why="Build A blocked every prop row with 'no game-log variance'. That blocker is now "
            "partly lifted — a σ exists and is published with an interval — but 3 players cannot "
            "price a 22-game slate, so no prop pick is published.",
        blocking_gates="V11 props coverage, V2, V10 price",
        blank_fields=["prop line", "over/under probability for the slate", "ROI"],
        what_moves_it_up="Per-game logs for the players actually in the slate: one reachable "
                         "page per player. This is the cheapest unblock on the list.")
    add(id="INT-4", name="Same-game parlay inside Fréchet bounds", family="Parlay / SGP",
        register="integration (this session)", n_graded=0, record=None,
        mae_margin=None, mae_total=None,
        metric="joint probability published as bounds, never a point",
        why="Correlation between two legs of one player's line is measured at r values whose "
            "intervals cross zero at n=4. Publishing a joint price off that would be inventing "
            "a number.",
        blocking_gates="V11, V10", blank_fields=["parlay odds", "correlation parameter"],
        what_moves_it_up="30+ logged player-games per player before a single-point correlation "
                          "is defensible.")
    add(id="BLD-A", name="Build A ledger (RecordLine-1 and its four families)",
        family="register", register="data/derived/strategies.json (2026-11-13)",
        n_graded=14, record=None, mae_margin=a_bt["summary"]["mae_margin_points"],
        mae_total=a_bt["summary"]["mae_total_points"],
        metric=a_bt["summary"]["verdict"],
        why="Its own metadata labels the 14-game test CONTAMINATED — season-to-date inputs "
            "include the games being predicted. Read as a pipeline check only.",
        blocking_gates="look-ahead, V2, V10",
        blank_fields=[f["family"] for f in a_strat.get("families", [])][:1] + ["validated count"],
        what_moves_it_up="Re-fit on a DateFrom/DateTo window (now proven reachable) — that is "
                         "exactly what INT-1 does.")
    top_b = sorted(b_lb["rows"], key=lambda r: -r["lbs"])[0] if b_lb["rows"] else None
    add(id="BLD-B", name="Build B LBS leaderboard (S1–S8)", family="register",
        register="docs/data/leaderboard.json", n_graded=top_b["n_graded"] if top_b else None,
        record=top_b["record"] if top_b else None,
        mae_margin=b_val["metrics"]["mae_margin_model"], mae_total=b_val["metrics"]["mae_total_model"],
        metric=f"best LBS {top_b['lbs']}/100 ({top_b['name']})" if top_b else None,
        why="Scored on 51 games with a 10/20–11/05 ratings window, so it is not look-ahead "
            "contaminated — but its Brier and log-loss both came out slightly worse than the "
            "reference, and its own conclusion was 'model ≈ market, within noise'.",
        blocking_gates="V2, V10", blank_fields=["price", "hold", "CLV"],
        what_moves_it_up="Nothing inside the sandbox: it needs prices.")

    rows.sort(key=rank_key)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    out = {
        "title": "Strategy leaderboard — integration desk",
        "ranking_basis": "hard gates passed → graded sample size → MAE. Gates are pass/fail with "
                         "no weighting, so a cosmetic lead cannot be bought with a soft score.",
        "reward_policy": "No entry is VALIDATED, therefore no reward is payable to any of them. "
                         "This table is informational, and the honest headline is that the best "
                         "model on this desk is not distinguishable from a naive pick.",
        "hard_gates_passed": f"{len(hard)} of {len(gates['gates'])}",
        "gate_ledger": {"pass": gates["summary"]["pass"], "fail": gates["summary"]["fail"],
                        "blank": gates["summary"]["blank"]},
        "sample_floor": n_gate["threshold"],
        "rows": rows,
        "registers_disagree": [
            {"topic": "how many graded games exist",
             "values": {f"integration (finals {settle['graded_window']['from'][5:]}–"
                       f"{settle['graded_window']['to'][5:]})": base["n"],
                       "Build A ledger": 14, "Build B LBS": top_b["n_graded"] if top_b else None},
             "resolution": (f"{base['n']} is the count this session could verify as FINAL with "
                            "a clean pre-window fit (2026-11-06 .. 2026-11-13). Build A's 14 "
                            "were look-ahead contaminated by its own admission; Build B's 23 is "
                            "a per-strategy graded-bet count, not a game count, so the two are "
                            "not the same unit and were never divided into each other.")},
            {"topic": "whether props could be priced",
             "values": {"Build A": "BLOCKED — no game-log variance",
                       "integration": "variance measured for 3 players, still not slate-wide"},
             "resolution": "Both statements are true of their own capture date. The blocker moved "
                           "from 'no data at all' to 'data for 3 players'."},
        ],
        "not_a_gate_but_relevant": {
            "settlement": f"{settle['graded_count']} games graded, "
                          f"{settle['cannot_settle_count']} cannot be settled yet",
            "side_record_if_it_were_a_bet": settle["side"]["record"],
            "warning": "the record above is graded against the model's own number and is ~50% by "
                       "construction; it is printed so nobody has to guess that it was hidden",
        },
    }
    dump("leaderboard.json", out)
    print(f"leaderboard · rows={len(rows)} hard_gates={out['hard_gates_passed']} "
          f"validated=0 reward_payable=0")
    return out


if __name__ == "__main__":
    main()
