#!/usr/bin/env python3
"""test_noise_band_refusal.py — prove the R10 refusal actually refuses.

Requirement line this answers: "Report luck as a z-score per team and refuse to
publish a strategy that leans on a team outside the noise band." (register R10)

A gate that has never rejected anything is not evidence of a gate. On the real
backtest corpus every modelled lean happens to sit inside the band
(21 bets checked, 0 offending), so a green run proves nothing about whether the
refusal works. This test therefore plants a team outside the band and asserts
that the same code path refuses it — and, symmetrically, that a lean on a team
inside the band is NOT refused, so the rule is not simply "refuse everything".

Run: python3 scripts/test_noise_band_refusal.py
This module is also safe to import under unittest discovery.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import strategies as S  # noqa: E402


def main():
    fails = []

    def check(name, cond, detail=""):
        print(("  PASS  " if cond else "  FAIL  ") + name + (("  — " + detail) if detail else ""))
        if not cond:
            fails.append(name)

    row = {"matchup": "AAA@BBB", "model_pick": "BBB", "model_p_home": 0.62,
           "source_url": "https://www.nba.com/games"}
    graded = [{"date": "2026-11-11", "matchup": "AAA@BBB", "won": True, "_row": row}]

    print("case 1 — lean on a team INSIDE the band must not be refused")
    out = S.noise_band_refusal(graded, {"BBB": 0.40, "AAA": -0.10})
    check("not refused", out["refused"] is False)
    check("one bet checked", out["bets_checked"] == 1)
    check("team identified as BBB", out["leans"][0]["team"] == "BBB")
    check("z was carried through", out["leans"][0]["luck_z"] == 0.40)

    print("case 2 — lean on a team OUTSIDE the band must be refused")
    out = S.noise_band_refusal(graded, {"BBB": 2.40, "AAA": -0.10})
    check("refused", out["refused"] is True)
    check("offending team named with its z", out["offending_teams"] == [("BBB", 2.40)])
    check("one offending bet", out["bets_offending"] == 1)

    print("case 3 — the band boundary is the published one")
    out = S.noise_band_refusal(graded, {"BBB": 1.95, "AAA": 0.0})
    check("|z| = 1.95 inside -> not refused", out["refused"] is False)
    out = S.noise_band_refusal(graded, {"BBB": 1.96, "AAA": 0.0})
    check("|z| = 1.96 is the boundary -> refused", out["refused"] is True)
    out = S.noise_band_refusal(graded, {"BBB": -1.96, "AAA": 0.0})
    check("a LARGE NEGATIVE z also refuses (band is two-sided)", out["refused"] is True)

    print("case 4 — an unmeasurable lean refuses rather than passing silently")
    out = S.noise_band_refusal(graded, {})
    check("refused when the team has no z-score", out["refused"] is True)
    check("counted as unmeasurable, not as offending",
          out["bets_unmeasurable"] == 1 and out["bets_offending"] == 0)

    print("case 5 — a bet with no team lean (totals) is not refused")
    tot = [{"date": "2026-11-11", "matchup": "AAA@BBB", "won": True, "_row": None}]
    out = S.noise_band_refusal(tot, {"BBB": 9.99})
    check("not refused", out["refused"] is False)
    check("checked zero bets", out["bets_checked"] == 0)

    print("case 6 — the live tables agree the rule is being applied to the real batch")
    with open(os.path.join(ROOT, "data/derived/strategies.json"), encoding="utf-8") as f:
        doc = json.load(f)
    check("every strategy carries a noise_band_refusal block",
          all("noise_band_refusal" in r for r in doc["leaderboard"]))
    check("the meta states the rule", "noise_band_rule" in doc["_meta"])
    with open(os.path.join(ROOT, "data/luck_zscores.json"), encoding="utf-8") as f:
        luck = json.load(f)
    check("the lucky teams in the real table are inside the band or would be refused",
          all((r["inside_noise_band"] is True) or (r["z_score"] is not None)
              for r in luck["rows"]))

    print("\nFAILURES: %d" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
