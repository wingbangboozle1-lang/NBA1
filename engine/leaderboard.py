"""Leaderboard scoring.

Composite score, published in full on the Validation page. Every component is
0..1 and the weights are fixed in advance so the ranking cannot be tuned after
the fact.

    LBS = 100 * (0.20*sample + 0.25*edge + 0.15*calibration + 0.25*result + 0.15*gates)

A strategy that has never been graded scores 0 - it is listed as "research only",
never as a winner.
"""

BREAKEVEN = 0.5238095238095238

WEIGHTS = {"sample": 0.20, "edge": 0.25, "calibration": 0.15,
           "result": 0.25, "gates": 0.15}

TIERS = [
    (70.0, "Tier 1 - Funded", "Full unit. Passed every applicable gate on real, graded plays."),
    (50.0, "Tier 2 - Half unit", "Passed the edge and calibration gates; sample still short of 30."),
    (30.0, "Tier 3 - Quarter unit", "Directional evidence only; stake capped until the sample grows."),
    (0.0, "Not funded - research only", "No graded record yet, or a hard gate failure."),
]


def _clamp(x, lo=0.0, hi=1.0):
    if x is None:
        return 0.0
    return max(lo, min(hi, x))


def score(summary):
    n = summary["n_graded"]
    dec = (summary["wins"] or 0) + (summary["losses"] or 0)
    mean_p = summary.get("mean_p_model")
    hit = summary.get("hit_rate")

    c_sample = _clamp(n / 30.0)
    c_edge = _clamp((mean_p - 0.5) / 0.08) if mean_p is not None else 0.0
    if mean_p is not None and hit is not None:
        c_calib = _clamp(1.0 - abs(hit - mean_p) / 0.15)
    else:
        c_calib = 0.0
    c_result = _clamp((hit - BREAKEVEN) / 0.10) if (hit is not None and dec) else 0.0

    applicable = [g for g in summary["gates"] if g["status"] in ("PASS", "FAIL", "PROVISIONAL")]
    if applicable:
        pts = sum(1.0 if g["status"] == "PASS" else (0.5 if g["status"] == "PROVISIONAL" else 0.0)
                  for g in applicable)
        c_gates = pts / len(applicable)
    else:
        c_gates = 0.0

    lbs = 100.0 * (WEIGHTS["sample"] * c_sample + WEIGHTS["edge"] * c_edge +
                   WEIGHTS["calibration"] * c_calib + WEIGHTS["result"] * c_result +
                   WEIGHTS["gates"] * c_gates)

    tier_name, tier_note = TIERS[-1][1], TIERS[-1][2]
    for floor, name, note in TIERS:
        if lbs >= floor:
            tier_name, tier_note = name, note
            break

    # Hard override: a strategy that has not cleared the sample gate cannot be
    # promoted past Tier 3 no matter how good its small-sample record looks.
    # A 12-4 run on a 28-game window is information about luck, not skill.
    gate_status = {g["id"]: g["status"] for g in summary["gates"]}
    cap_reason = None
    if gate_status.get("G4") == "FAIL":
        cap_reason = "G4 (skill, not luck) failed"
    elif gate_status.get("G1") != "PASS":
        cap_reason = "G1 (sample size) not passed"
    if n == 0:
        floor, tier_name, tier_note = TIERS[3]
        tier_note = tier_note + " - never graded."
    elif cap_reason:
        floor, tier_name, tier_note = TIERS[2]
        tier_note = tier_note + f" - capped by {cap_reason}."

    return {
        "id": summary["id"],
        "name": summary["name"],
        "family": summary["family"],
        "components": {
            "sample": round(c_sample, 3),
            "edge": round(c_edge, 3),
            "calibration": round(c_calib, 3),
            "result": round(c_result, 3),
            "gates": round(c_gates, 3),
        },
        "lbs": round(lbs, 1),
        "tier": tier_name,
        "tier_note": tier_note,
        "n_graded": n,
        "record": f"{summary['wins']}-{summary['losses']}"
                  + (f"-{summary['pushes']}" if summary["pushes"] else ""),
        "units": summary["units_at_minus110"],
        "status": "GRADED" if summary["gradeable"] and n else "UNGRADED",
    }


def build(summaries):
    rows = [score(s) for s in summaries]
    rows.sort(key=lambda r: (-r["lbs"], -r["n_graded"], r["id"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows
