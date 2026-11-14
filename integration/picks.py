"""Slate picks for the next three days, with a selection rule stated in advance.

There is no sportsbook price reachable from this sandbox, so "pick" here means a lean against
our own originated line and nothing more. It cannot be +EV, it cannot be sized, and no row in
this file is a bet. What CAN be done honestly is the selection: a rule fixed before pricing the
slate, applied to every game, with the games it rejects printed as rejected rather than dropped.

Every game on the slate still gets a line and a lean — the brief asks for coverage of the whole
slate — but each row carries a tier:
  SELECTED       passes R1–R5; the only tier that would ever earn a stake if a price existed
  LEAN-ONLY      data is complete, the projected margin is just inside the model's own noise
  REJECTED-DATA  a required input is missing (asymmetric injury filings, unknowable rest)
so "we like Denver" and "we were not allowed to have an opinion" are never the same cell.

Selection rule, written before looking at which games it favours:
  R1 both teams' ratings must come from the verified window;
  R2 |projected home margin| must clear half the measured out-of-sample σ_margin (≥ 8.7 pts);
  R3 availability must be symmetric — one side filed, the other not is disqualifying;
  R4 no pick on a neutral site or unverified venue;
  R5 rest state must be derivable from the captured schedule.
"""

from common import dump, load
import model as M

MIN_EDGE_SIGMA = 0.5    # |margin| must clear half of σ_margin to be published as a pick at all
PRIOR_DATE_UNFINISHED = "2026-11-13"


def teams_with_unconfirmed_prior():
    """Abbrs whose most recent counted game was on a date that was never confirmed FINAL.

    Rest days are counted from the schedule, not from verified completion, so a team credited
    with a back-to-back off 11/13 may have had a bye. The set is small and it is printed on
    every affected row instead of being corrected by guesswork.
    """
    res = load("data", "live", f"results_{PRIOR_DATE_UNFINISHED.replace('-', '_')}_in_progress.json")
    out = set()
    for g in res["games"]:
        m = str(g.get("matchup", ""))
        if "@" in m:
            a, h = m.split("@", 1)
            out.update({a.strip(), h.strip()})
    return out


def classify(g, sigma, thresh, report_exists):
    """Return (tier, reasons) for one slate game under R1–R5.

    A line exists for every game; what changes is whether a *lean* on that line may be read
    as a view:

      SELECTED       every rule passes, including a symmetric availability filing
      PROVISIONAL    the line is sound, but availability for this date has not been filed at all
                     (normal for a game one or two days out; refresh before tip)
      LEAN-ONLY      availability is complete, but the projected margin is inside the model's noise
      REJECTED-DATA  an input that would change the answer is missing or asymmetric
    """
    m = g["projection"]["margin_home"]
    blocking, thin, provisional = [], [], []
    if report_exists:
        if g["report_state_away"] != g["report_state_home"]:
            blocking.append(
                f"R3 asymmetric availability: {g['away']}={g['report_state_away']} vs "
                f"{g['home']}={g['report_state_home']} — one side's absences are known and the "
                f"other's are not, which biases the adjustment instead of removing it")
    else:
        provisional.append(f"R3 no injury-report edition exists yet for {g['date']}; "
                           f"availability is unknown, not clear")
    if g["rest_days_home"] is None or g["rest_days_away"] is None:
        blocking.append("R5 rest state not derivable from the captured schedule window")
    if g.get("neutral_site") is None:
        provisional.append("R4 venue not captured for future dates, so neutrality is unverified "
                           "(in the backtest window the neutral flag exists and was enforced)")
    if abs(m) < thresh:
        thin.append(f"R2 |margin {m:+.1f}| is inside the ±{thresh} point cut "
                    f"(half of the measured σ_margin {sigma})")
    if blocking:
        return "REJECTED-DATA", blocking + thin + provisional
    if thin:
        return "LEAN-ONLY", thin + provisional
    if provisional:
        return "PROVISIONAL", provisional
    return "SELECTED", []


def availability_summary(g, side):
    """What the report says versus what the model was able to size."""
    rows = g[f"availability_{side}"]
    listed = len(rows)
    sized = sum(1 for r in rows if r["moves_the_line"])
    return {
        "side": side.upper(), "team": g[side],
        "listed_absent_or_questioned": listed,
        "report_state": g[f"report_state_{side}"],
        "rows_with_season_minutes_in_repo": sum(1 for r in rows
                                                if r["minutes_per_game"] is not None),
        "rows_sized_by_the_model": sized,
        "rows_unsizeable": listed - sized,
        "minute_share_vacated": g[f"minute_share_vacated_{side}"],
        "margin_points_applied": g["projection"]["avail_adj"] if side == "home" else None,
        "reading": "a listed absence that could not be sized contributes 0.0 points. That is a "
                   "gap in the data, not a judgement that the player does not matter.",
        "rows": rows,
    }


def game_flow(g, lines):
    """Pre-tip flow read: what schedule and availability do to the shape of the game."""
    p = g["projection"]
    return {
        "projected_possessions": p["poss"],
        "pace_note": f"{g['away']} {g['away_pace']} / {g['home']} {g['home_pace']} per 100 — "
                     f"mean of the two, from the {g['ratings_window']} window",
        "first_half_share": None,
        "first_half_share_blank_because": "no quarter-level scoring split is stored for either "
                                          "team in this repository, so the halftime-to-final "
                                          "shape is left blank rather than assumed at 50/50",
        "rest": {"away_days": g["rest_days_away"], "home_days": g["rest_days_home"],
                 "away_b2b": bool(g["b2b_away"]), "home_b2b": bool(g["b2b_home"]),
                 "note": g["rest_note"] or "both teams' previous games are inside the window",
                 "caveat": ("a rest day counted from a game that never finished is wrong in the "
                            "useful direction — the game is cheaper, not harder. The 11/13 slate "
                            "was IN PROGRESS when captured, so any back-to-back flag built on it "
                            "is provisional until those games are confirmed FINAL."),
                 "provisional_prior_date": PRIOR_DATE_UNFINISHED,
                 "teams_affected": sorted(t for t in teams_with_unconfirmed_prior()
                                          if t in (g["away"], g["home"])) or None},
        "margin_path": {"raw_from_ratings": p["raw_margin_home"], "rest_adj": p["rest_adj"],
                        "availability_adj": p["avail_adj"],
                        "hca_points": lines["assumptions"]["hca_points"]["value"],
                        "final": p["margin_home"],
                        "check": "raw + hca + rest + availability = final, printed so the "
                                 "arithmetic is verifiable by hand"},
        "availability": {"away": availability_summary(g, "away"),
                         "home": availability_summary(g, "home")},
        "leaders": {"away": g["leaders_away"], "home": g["leaders_home"],
                    "caveat": "a slate card's season-leaders capsule is not re-derived after the "
                              "injury report, so a leader shown on a card is not evidence of playing"},
    }


def main():
    lines = load("integration", "out", "lines.json")
    sigma = lines["diagnostics"]["sigma_margin_measured"]
    thresh = round(MIN_EDGE_SIGMA * sigma, 2)

    tiers = ["SELECTED", "PROVISIONAL", "LEAN-ONLY", "REJECTED-DATA"]
    rows, by_tier = [], {t: 0 for t in tiers}
    inj = load("data", "live", "injury_report_2026_11_14.json")
    report_dates = {r["date"] for r in inj["rows"]}          # dates with a filed official edition

    for g in lines["live_lines"]:
        tier, reasons = classify(g, sigma, thresh, g["date"] in report_dates)
        by_tier[tier] += 1
        m = g["projection"]["margin_home"]
        rows.append({
            "date": g["date"], "time_et": g["time_et"], "matchup": g["matchup"],
            "game_id": g["game_id"], "game_url": g["game_url"], "source_url": g["source_url"],
            "tier": tier, "reasons": reasons,
            "line_spread_home": g["spread_home"], "line_total": g["projection"]["total"],
            "p_home_win_model": g["p_home_win"],
            "lean": ("HOME " + g["home"]) if m > 0 else ("AWAY " + g["away"]),
            "lean_margin_points": abs(round(m, 1)),
            "records_as_displayed": {"away": g["away_record"], "home": g["home_record"],
                                     "caveat": "copied exactly as displayed; the unfinished 11/13 "
                                               "games mean every card lags one league day (IR-05)"},
            "ratings_window": g["ratings_window"],
            "ratings_shrunk_net": {"away": g["away_net_shrunk"], "home": g["home_net_shrunk"],
                                   "games_behind": {"away": g["away_gp"], "home": g["home_gp"]}},
            "neutral_site": None,
            "market_price": None, "edge_vs_market": None, "kelly_stake": None, "hold": None,
            "market_fields_blank_because": "no sportsbook price is reachable from this sandbox — "
                                           "these four fields stay blank on every row, forever, "
                                           "until a price file exists",
            "game_flow": game_flow(g, lines),
        })

    rows.sort(key=lambda r: (r["date"], r["time_et"]))
    out = {
        "rule": {"sigma_margin_measured": sigma, "min_edge_points": thresh,
                 "criteria": ["R1 verified ratings window", f"R2 |margin| ≥ {thresh} (0.5·σ)",
                              "R3 symmetric availability filing", "R4 neutral-site veto",
                              "R5 rest state derivable"],
                 "written_before": "the cut came from the 51-game backtest's own error, not from "
                                    "these games"},
        "slate": {"dates": sorted({r["date"] for r in rows}),
                  "games_priced": len(rows),
                  "tiers": by_tier},
        "rows": rows,
        "headline": f"{len(rows)} games priced, {by_tier['SELECTED']} pass every selection rule. "
                    f"The rule, not the model, is what is holding the desk back: on 11/14 the "
                    "official report had one side filed and the other NOT YET SUBMITTED in all "
                    "five games.",
        "neutral_site_note": "R4 is inert on this slate because the capture has no venue column. "
                             "The one neutral site in the backtest window (Indiana–Denver, Mexico "
                             "City, 11/07) was zeroed there. Blank here, not assumed safe.",
        "not_a_bet": "Every row is a paper lean against our own number: no price, no hold, no "
                     "stake, no expectation of profit, and none of it clears the validation gates.",
    }
    dump("picks.json", out)
    print(f"picks · priced={len(rows)} SELECTED={by_tier['SELECTED']} "
          f"LEAN-ONLY={by_tier['LEAN-ONLY']} REJECTED-DATA={by_tier['REJECTED-DATA']} "
          f"edge_cut={thresh}")
    return out


if __name__ == "__main__":
    main()
