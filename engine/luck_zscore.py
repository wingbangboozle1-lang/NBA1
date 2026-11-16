"""Luck as a z-score per team.

Reads the official team advanced stats (OffRtg, DefRtg, GP, W, L) and computes
Pythagorean expected wins, then luck = actual - expected, z-scored by the
binomial SD over games played.

A team outside the noise band (|z| >= 1.96, i.e. p < 0.05 two-sided) is
flagged: a strategy leaning on such a team is refusing to publish (its edge
cannot be distinguished from luck).
"""
import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json

PYTHAG_EXPONENT = 13.91  # published NBA Pythagorean exponent; documented as an assumption

def pythag_expected_wins(ortg, drtg, gp, exponent=PYTHAG_EXPONENT):
    """Pythagorean win probability from OffRtg/DefRtg (points per 100 poss)."""
    if gp == 0:
        return 0.0
    pf = ortg ** exponent
    pa = drtg ** exponent
    return gp * pf / (pf + pa)

def luck_zscore(actual_wins, expected_wins, gp):
    """z = (actual - expected) / sqrt(gp * p * (1-p)) where p = expected/gp."""
    if gp == 0:
        return 0.0, 0.0, 0.0
    p = expected_wins / gp
    var = gp * p * (1 - p)
    sd = math.sqrt(max(var, 1e-9))
    z = (actual_wins - expected_wins) / sd
    return expected_wins, actual_wins - expected_wins, z

def main():
    adv = read_json("data/teams_advanced_2026_27.json")
    rows = adv["rows"]
    out = []
    for r in rows:
        gp = r["gp"]; w = r["w"]; l = r["l"]
        ortg = r["off_rtg"]; drtg = r["def_rtg"]
        exp_w, luck, z = luck_zscore(w, pythag_expected_wins(ortg, drtg, gp), gp)
        noise_band = abs(z) < 1.96
        out.append({
            "team": r["team"], "abbr": r["abbr"], "gp": gp, "w": w, "l": l,
            "win_pct": round(w/gp, 4) if gp else None,
            "off_rtg": ortg, "def_rtg": drtg, "net_rtg": r["net_rtg"],
            "expected_wins": round(exp_w, 2),
            "luck": round(luck, 2),
            "z_score": round(z, 3),
            "inside_noise_band": noise_band,
            "source_url": r.get("source_url"),
        })
    out.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    write_json("data/luck_zscores.json", {
        "_meta": {
            "method": "Pythagorean expectation (exp 13.91) on official OffRtg/DefRtg; "
                      "luck = actual wins - expected wins; z divides by binomial SD.",
            "exponent": PYTHAG_EXPONENT,
            "noise_band_rule": "|z| < 1.96 => inside the noise band (not distinguishable from luck at 5%). "
                               "Strategies leaning on teams outside the band are refused publication.",
            "source": "data/teams_advanced_2026_27.json (official NBA.com team advanced stats)",
        },
        "rows": out,
    })
    print(f"Wrote data/luck_zscores.json: {len(out)} teams")
    for r in out[:5]:
        print(f"  {r['abbr']:>3} z={r['z_score']:+.3f} luck={r['luck']:+.2f} band={r['inside_noise_band']}")

if __name__ == "__main__":
    main()
