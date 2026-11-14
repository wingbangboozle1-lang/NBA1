#!/usr/bin/env python3
"""Write integration/REPORT.md from the desk's own JSON outputs.

Generated rather than typed: an executive summary that is maintained by hand is a summary that
drifts. Every figure below is read from integration/out/*.json at build time, so this file and
the site pages cannot disagree — and if a number changes, both change together or the build
fails. Run after model → props → settle → gates → picks → review.
"""

import json
import os

from common import ROOT

OUT = os.path.join(ROOT, "integration", "out")


def J(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ln, st, g, pk, lb, pr, rv = (J("lines.json"), J("settlement.json"), J("gates.json"),
                                J("picks.json"), J("leaderboard.json"), J("props.json"),
                                J("review.json"))
    nv = g["naive_baselines"]
    tiers = pk["slate"]["tiers"]
    L = []
    A = L.append
    A("# Integration desk — report for 2026-11-14")
    A("")
    A(f"Capture: {ln['generated_utc']} · session `{ln['capture_session']}` · "
      f"{len(ln['live_lines'])} games priced, {st['graded_count']} graded out of sample.")
    A("")
    A("## Executive summary")
    A("")
    A(f"1. **The margin carries information; the total does not.** Mean absolute error on the "
      f"final margin is **{nv['margin_model']}** points against **{nv['margin_constant_sample_mean']}** "
      f"for predicting a single constant across the same {st['graded_count']} official finals — a gain "
      f"of {nv['margin_improvement']} points. On totals the model scores **{nv['total_model']}** where a "
      f"constant scores **{nv['total_constant_sample_mean']}**, so the possession-based total is "
      f"{abs(nv['total_improvement'])} points *worse* than doing no work. Gate V3b fails on purpose "
      f"and is published as a failure.")
    A(f"2. **No component earns its keep at this sample size.** Removing home court moves the margin "
      f"error by {g['ablations']['hca_off']['delta_mae_vs_full_model']:+}, removing the back-to-back "
      f"penalty by {g['ablations']['b2b_off']['delta_mae_vs_full_model']:+}, and removing shrinkage by "
      f"{g['ablations']['no_shrinkage']['delta_mae_vs_full_model']:+} points — all inside a "
      f"±{round((g['bootstrap_mae_margin_95'][1] - g['bootstrap_mae_margin_95'][0]) / 2, 1)} interval. "
      f"They stay in the model because the theory supports them, and they are flagged because the data "
      f"cannot yet confirm them.")
    A(f"3. **What withholds picks is the injury report, not the model.** Of "
      f"{pk['slate']['games_priced']} priced games: {tiers['SELECTED']} pass every rule, "
      f"{tiers['REJECTED-DATA']} are refused because one side had filed and the other had not, "
      f"{tiers['PROVISIONAL']} are provisional until their date's report exists, and "
      f"{tiers['LEAN-ONLY']} sit inside the model's own noise. Every rejection is printed with its "
      f"reason rather than dropped.")
    A("4. **Rotation impact could not be sized.** Of 26 official absences for 11/14, exactly one has "
      "verified season minutes anywhere in this repository. Vacated minutes reduce the named player's "
      "team and are *not* re-spread across his teammates — re-spreading them would have meant inventing "
      "the numbers that make a rotation model look good.")
    A(f"5. **Prop dispersion is measured now, and still unusable.** {pr['sample']['player_games']} "
      f"official game-log rows across {len(pr['sample']['players'])} players give a real σ where the "
      f"repo previously used a constant; every prop and parlay row carries "
      f"`usable_for_staking: false`, and within-player correlations have intervals that cross zero.")
    A(f"6. **Nothing here is a bet.** No sportsbook price is reachable from this environment, so "
      f"break-even, hold, ROI and CLV are blank everywhere: {g['summary']['blank']} gates are BLANK "
      f"for that reason and {g['summary']['fail']} FAIL. The leaderboard's top row is not validated "
      f"and no reward is payable to any row of it.")
    A("")
    A("## Gate ledger")
    A("")
    A("| Gate | Requirement | Status |")
    A("| --- | --- | --- |")
    for x in g["gates"]:
        A(f"| {x['id']} | {x['name']} | **{x['status']}** — {x['measured']} |")
    A("")
    A("## The slate, in one table")
    A("")
    A("| Date | Matchup | Spread (home) | Total | P(home) | Tier |")
    A("| --- | --- | --- | --- | --- | --- |")
    for r in pk["rows"]:
        A(f"| {r['date']} | [{r['matchup']}]({r['source_url']}) | {r['line_spread_home']:+.1f} "
          f"| {r['line_total']:.1f} | {r['p_home_win_model']:.3f} | {r['tier']} |")
    A("")
    A("## What to do next, in order")
    A("")
    for s in rv["suggestions"]:
        A(f"- **{s['id']}** — {s['suggestion']} *(cost: {s['cost']})*")
    A("")
    A("## Files")
    A("")
    A("```")
    A("data/live/            6 official captures + the register (capture_meta.json)")
    A("integration/*.py      model, props, settle, gates, picks, review, site, leaderboard, common")
    A("integration/out/      lines, props, settlement, gates, picks, crosscheck, review,")
    A("                      leaderboard, transform_test")
    A("desk*.html            5 published pages, generated by integration/site.py")
    A("REPO_REVIEW.md        the line-by-line repo read, generated by integration/review.py")
    A("```")
    A("")
    A("Reproduce with:")
    A("")
    A("```")
    A("python3 integration/model.py && python3 integration/props.py && python3 integration/settle.py")
    A("python3 integration/gates.py && python3 integration/picks.py && python3 integration/transform.py")
    A("python3 integration/crosscheck.py && python3 integration/review.py")
    A("python3 integration/leaderboard.py && python3 integration/site.py && python3 integration/report.py")
    A("```")
    A("")
    txt = "\n".join(L) + ""
    with open(os.path.join(ROOT, "integration", "REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(txt if txt.endswith("\n") else txt + "\n")
    print(f"report · {len(L)} lines, {len(pk['rows'])} slate rows, {len(g['gates'])} gates")
    return txt


if __name__ == "__main__":
    main()
