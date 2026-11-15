#!/usr/bin/env python3
"""build_rolling_slate_2026_11_15.py - the 2026-11-15 site pages.

    python3 scripts/build_rolling_slate_2026_11_15.py

Writes the pages that the 2026-11-15 rolling-slate build owns, and the JSON the
pages are rendered from:

    site/pages/projection.html   the PROJECTION surface: safe to publish now
    site/pages/bet.html          the BET surface: gated, and currently empty
    site/pages/results.html      the official per-game result feed + settlement
    site/pages/ledger.html       the tamper-evident ledger + the frozen
                                 pre-registration files
    site/pages/estimators.html   the two independent estimators and their
                                 disagreement, the pinned home-court advantage,
                                 the possession-based total and the
                                 market-anchored prior
    site/pages/minutes.html      per-team top-8 minutes shares and the
                                 replacement allocation
    site/pages/player-logs.html  per-player game logs for the players on the
                                 injury report
    site/pages/injury-editions.html  every official injury edition and the
                                 consecutive diffs

The two surfaces are kept apart on purpose: the projection surface carries no
pick at all, and the bet surface carries only what has cleared the gate stack.
"""

import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_dashboard as BD             # noqa: E402  (the site's own helpers)

DER = os.path.join(ROOT, "data", "derived", "rolling_slate_2026_11_15")
SITE = os.path.join(ROOT, "site")
PAGES = os.path.join(SITE, "pages")
SITE_DATA = os.path.join(SITE, "data")
LEDGER = os.path.join(ROOT, "data", "ledger")


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


def multi(*pairs):
    """Several official links in one cell."""
    out = []
    for url, label in pairs:
        if url:
            out.append(BD.srclink_url(url, label))
    return " ".join(out) if out else BD.NA


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    print("[%s] %s" % (now_utc(), msg), flush=True)


def american(p):
    if p is None or not (0 < p < 1):
        return None
    if p >= 0.5:
        return -int(round(100 * (1 - p) / p))
    return int(round(100 * p / (1 - p)))


# --------------------------------------------------------------------- pages
def build_projection(hz, minutes, results):
    rows = hz["rows"]
    b = []
    b.append(BD.banner("info", "What this surface is",
                       "<p>This is the <strong>projection surface</strong>: everything the model "
                       "knows about the next three days, published as soon as it is computed. "
                       "It contains <strong>no pick of any kind</strong> - no strategy, no side, no "
                       "line to bet. Picks live on the <a href=\"bet.html\">bet surface</a>, which is "
                       "gated, and they are not mixed with this page.</p>"))
    b.append(BD.banner("warn", "The headline is the disagreement, not the blend",
                       "<p>Two estimators are computed independently for every game. "
                       "<strong>Estimator A</strong> reads the NBA's published efficiency ratings; "
                       "<strong>estimator B</strong> rebuilds points-per-possession from the raw "
                       "official box scores of each team's last ten games and never touches those "
                       "ratings. The published headline for every game is the size of the "
                       "disagreement between them. The blend sits underneath it, and a single "
                       "blended number is never the headline.</p>"))
    tr = []
    for r in rows:
        a = r["estimator_a"]
        e = r["estimator_b"]
        ref = r.get("reference") or {}
        tr.append([
            BD.esc(r["date"]), '<b>%s</b>' % BD.esc(r["matchup"]),
            BD.esc(r.get("time_et")), BD.esc(r.get("arena_name")),
            BD.num(a["margin"]), BD.num(e["margin"]),
            '<b>%s</b>' % BD.num(r["disagreement_points"]),
            BD.num(r.get("blend_margin")),
            BD.num(ref.get("margin")),
            BD.num(r.get("total_possessions_x_ppp")),
            BD.num(ref.get("total")),
            BD.num(r.get("total_avg_of_scoring_averages")),
            BD.num(r.get("home_rest_days"), 0), BD.num(r.get("away_rest_days"), 0),
            ("H" if r.get("home_back_to_back") else "-") +
            ("/B2B" if r.get("away_back_to_back") else "") +
            ("/3-in-4" if (r.get("home_three_in_four") or r.get("away_three_in_four")) else ""),
            BD.num(r.get("away_travel_miles"), 0), BD.num(r.get("home_travel_miles"), 0),
            BD.esc(r.get("away_travel_from_city")),
            multi((r.get("slate_source_url"), "slate"),
                  (r.get("box_score_url"), "box"),
                  ("https://www.nba.com/stats/teams/advanced", "ratings")),
        ])
    b.append(BD.h2("Every game in the horizon",
                    "Estimator A and estimator B, the disagreement between them, and the blend underneath."))
    b.append(BD.table(
        ["Date", "Matchup", "Tip ET", "Arena", "A margin", "B margin",
         "DISAGREEMENT (headline)", "Blend", "Ref margin",
         "Total (poss &times; PPP)", "Ref total", "Avg-of-averages total",
         "Rest H", "Rest A", "B2B / 3-in-4", "Travel away (mi)", "Travel home (mi)",
         "Travel from", "Source"],
        tr,
        note="MARGIN SIGN CONVENTION: every margin is the projected HOME MARGIN (home minus "
             "away), so a negative number means the home team is projected to lose. The total "
             "column is possessions &times; points-per-possession, both measured; the "
             "avg-of-averages column is the old method and is shown only as a comparison. "
             "Travel is the great-circle distance between the arena cities the NBA prints, "
             "using coordinates from the U.S. Census Bureau gazetteer, and is a city-centroid "
             "distance rather than an arena-to-arena road distance."))
    b.append(BD.h2("Rotation availability",
                    "How much of each team's minutes the official injury report puts at risk."))
    av = []
    for r in rows:
        blk = next((x for x in minutes.get("redistribution", [])
                    if x["game_id"] == r["game_id"]), {})
        lost = {}
        for rr in blk.get("rows", []):
            lost[rr["team"]] = lost.get(rr["team"], 0.0) + (rr.get("share_to_replace") or 0.0)
        av.append([
            BD.esc(r["date"]), '<b>%s</b>' % BD.esc(r["matchup"]),
            BD.num(lost.get(r["home"]), 3) if r["home"] in lost else BD.NA,
            BD.num(lost.get(r["away"]), 3) if r["away"] in lost else BD.NA,
            BD.esc(r.get("arena_name")),
            multi((minutes.get("injury_edition_url"), "injury report"),
                  (r.get("slate_source_url"), "slate")),
        ])
    b.append(BD.table(
        ["Date", "Matchup", "Home minutes at risk", "Away minutes at risk", "Arena", "Source"],
        av,
        note="Minutes at risk = the player's share of the team's minutes multiplied by the "
             "status weight (Out 1.0, Doubtful 0.7, Questionable 0.35, Probable 0.1, "
             "Available 0.0). A blank means the injury edition carried no row for that team, "
             "which is a fact about the report, not an estimate."))
    return BD.page("Projection surface",
                   "The model view of the next three days: two independent estimators, their "
                   "disagreement, the schedule and travel context, and the rotation impact of "
                   "the official injury report. No picks appear on this page.",
                   "\n".join(b))


def build_bet(hz, picks, ledger, prereg):
    entries = ledger.get("entries", [])
    by_game = {}
    for e in entries:
        by_game.setdefault((e.get("date"), e.get("strategy"), e.get("game_id")), []).append(e)
    b = []
    funded = 0
    b.append(BD.banner("warn", "This surface is gated, and today it publishes nothing",
                       "<p>Only a strategy that has cleared <strong>every</strong> registered "
                       "validation gate may appear here, and no strategy has. The gate stack "
                       "is the seven gates in <code>engine/strategies.py</code>: sample size, "
                       "calibration, edge over break-even, skill-not-luck, stability, the "
                       "correlation limit and availability robustness. Until a strategy clears "
                       "all seven, this surface stays empty and the candidate plays below are "
                       "shown as <em>candidates with their gate status</em>, not as "
                       "recommendations.</p>"))
    b.append(BD.tiles([
        ("Published bets", funded, "strategies that cleared every registered gate"),
        ("Candidate plays", len(picks.get("rows", [])), "generated for the horizon, not released"),
        ("Sealed in the ledger", ledger.get("counts", {}).get("entries", 0),
         "hashed before tip, verifiable after settlement"),
        ("Ledger mismatches", ledger.get("counts", {}).get("mismatches", 0),
         "a hash that no longer matches its published payload"),
    ]))
    b.append(BD.h2("Candidate plays for the horizon",
                    "Every play the registered strategy rules produced, with the seal state of "
                    "its ledger entry. These are NOT released as bets."))
    rows = []
    for p in picks.get("rows", []):
        es = by_game.get((p.get("date"), p.get("strategy"), p.get("game_id")), [])
        sealed = es[-1] if es else None
        rows.append([
            BD.esc(p.get("date")), '<b>%s</b>' % BD.esc(p.get("matchup")),
            BD.esc(p.get("strategy")), BD.esc(p.get("market")),
            BD.esc(p.get("side")), BD.esc(p.get("line_display")),
            BD.num(p.get("model_value")), BD.num(p.get("ref_line")),
            BD.num(p.get("edge"), 2) if p.get("edge") is not None else BD.NA,
            BD.num(p.get("p_model"), 4),
            BD.esc(p.get("fair_price")) if p.get("fair_price") is not None else BD.NA,
            BD.esc(p.get("naive_price")) if p.get("naive_price") is not None else BD.NA,
            BD.esc(sealed.get("seal_state")) if sealed else BD.NA,
            BD.esc(sealed.get("payload_sha256")[:16] + "...") if sealed else BD.NA,
            "NOT RELEASED - no strategy has cleared the gate stack",
            multi(("https://www.nba.com/games?date=%s" % p.get("date"), "slate"),
                  ("https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine/strategies.py",
                   "rule")),
        ])
    b.append(BD.table(
        ["Date", "Matchup", "Strategy", "Market", "Side", "Line", "Model value",
         "Ref line", "Edge", "P(model)", "Price (rho)", "Naive price", "Seal state",
         "Payload hash", "Release status", "Source"],
        rows,
        note="The price column is the parlay price computed with the MEASURED rho and the "
             "naive price column is the independent product printed beside it, so the "
             "correlation cost is visible. A single-leg play has no rho, so both price "
             "columns are blank. Every candidate is sealed in the ledger before tip; see "
             "<a href=\"ledger.html\">the sealed ledger</a>."))
    b.append(BD.h2("The gate stack",
                    "Every strategy, the gate that is blocking it, and what is still missing."))
    b.append(BD.banner("info", "Where the gate results live",
                       "<p>The graded record of every strategy is on "
                       "<a href=\"leaderboard.html\">Leaderboard &amp; Rewards</a> and the gate "
                       "definitions on <a href=\"validation.html\">Validation Gates</a>. This "
                       "page deliberately does not restate them: it only decides what may be "
                       "released.</p>"))
    return BD.page("Bet surface (gated)",
                   "The release surface. A play appears here only when its strategy has cleared "
                   "every registered validation gate. Nothing has, so nothing is released.",
                   "\n".join(b))


def build_results(results, settlement):
    b = []
    counts = results.get("counts", {})
    b.append(BD.tiles([
        ("Official games captured", counts.get("games", 0), "one row per game, from NBA.com"),
        ("Finals", counts.get("finals", 0), "the official page prints FINAL"),
        ("Finals whose quarters add up", counts.get("finals_reconciling", 0),
         "the quarter lines must sum to the printed final"),
        ("Picks settled", settlement.get("counts", {}).get("settled", 0),
         "graded only from the official final"),
    ]))
    b.append(BD.banner("info", "How a game is settled",
                       "<p>A game is settled only when the official page prints FINAL "
                       "<em>and</em> the printed quarter lines add up to the printed final "
                       "score. A row where they do not reconcile is published as it was read "
                       "and counted in the tile above, not corrected.</p>"))
    rows = []
    for r in results.get("rows", []):
        qa = " / ".join(str(x) for x in (r.get("away_quarter_scores") or [])) or BD.NA
        qh = " / ".join(str(x) for x in (r.get("home_quarter_scores") or [])) or BD.NA
        rows.append([
            BD.esc(r["date"]), BD.esc(r["game_id"]),
            '<b>%s</b>' % BD.esc("%s@%s" % (r["away"], r["home"])),
            BD.esc(r.get("status")),
            BD.esc(r.get("final_away_score")), BD.esc(r.get("final_home_score")),
            BD.esc(r.get("ot") or ""),
            qa, qh,
            ("yes" if r.get("quarters_reconcile") else "no"),
            multi((r.get("source_url"), "box score"),
                  (r.get("slate_source_url"), "slate")),
        ])
    b.append(BD.h2("The official result feed",
                    "One row per game: date, both teams, the final score and the "
                    "quarter-by-quarter scores."))
    b.append(BD.table(
        ["Date", "Game id", "Matchup", "Status", "Away pts", "Home pts", "OT",
         "Away quarters", "Home quarters", "Quarters reconcile", "Source"],
        rows,
        note="Quarter scores are printed in the order the official page prints them. The "
             "reconciliation column says whether the printed quarters add up to the printed "
             "final; it is a check, not a correction."))
    srows = []
    for s in settlement.get("rows", []):
        srows.append([
            BD.esc(s["date"]), '<b>%s</b>' % BD.esc(s["matchup"]),
            BD.esc(s["strategy"]), BD.esc(s["market"]), BD.esc(s["side"]),
            BD.esc(s["line_display"]),
            BD.esc(s["official_final"]),
            "<b>%s</b>" % BD.esc(s["result"]),
            BD.esc(s.get("settlement_stamp")),
            BD.srclink_url(s.get("source_url"), "official box score"),
        ])
    b.append(BD.h2("Settlement",
                    "Every published pick graded against the official final, with the "
                    "settlement stamp."))
    b.append(BD.table(
        ["Date", "Matchup", "Strategy", "Market", "Side", "Line", "Official final",
         "Result", "Settlement stamp", "Source"],
        srows,
        note="The settlement stamp is the UTC time the pick was graded together with the "
             "official page it was graded from. A pick is never graded from a live score."))
    return BD.page("Official results and settlement",
                   "The per-game official result feed - date, teams, final score and quarter "
                   "scores - and the settlement of every published pick against the official "
                   "finals.",
                   "\n".join(b))


def build_ledger(ledger, prereg):
    b = []
    b.append(BD.banner("info", "What this ledger proves",
                       "<p>Every published pick is hashed with SHA-256 over a canonical payload. "
                       "The hash is published BEFORE the game tips, and after the official "
                       "final is verified the same payload is re-hashed and compared. A "
                       "mismatch would mean the published pick had been altered after it was "
                       "sealed. The counts below are the live state of that check.</p>"))
    counts = ledger.get("counts", {})
    b.append(BD.tiles([
        ("Ledger entries", counts.get("entries", 0), "every published pick, hashed"),
        ("Sealed before tip", counts.get("sealed_before_tip", 0),
         "the hash was published before the tip time"),
        ("Settled", counts.get("settled", 0), "graded from the official final"),
        ("Hash mismatches", counts.get("mismatches", 0),
         "a payload that no longer matches its published hash"),
    ]))
    prows = []
    for p in prereg.get("strategies", []):
        prows.append([
            '<b>%s</b>' % BD.esc(p["strategy_id"]), BD.esc(p["name"]),
            BD.esc(p["family"]), BD.esc(p["signal"]), BD.esc(p["thresholds"]),
            BD.esc(p["universe"]["markets"][0] if p["universe"].get("markets") else None),
            BD.esc(p["frozen_at_utc"]),
            BD.esc(p["file_sha256"][:16] + "..."),
            ("yes" if p.get("frozen_before_first_bet_on_this_strategy") else "no - recorded"),
            BD.srclink_url("https://github.com/wingbangboozle1-lang/NBA1/blob/main/"
                           "data/ledger/preregistration/%s.json" % p["strategy_id"],
                           "file"),
        ])
    b.append(BD.h2("The frozen pre-registration, one file per strategy",
                    "Signal, thresholds, universe and the exact settlement rule, frozen before "
                    "the strategy's first bet."))
    b.append(BD.table(
        ["Id", "Strategy", "Family", "Signal", "Thresholds", "Market", "Frozen at (UTC)",
         "File SHA-256", "Frozen before first bet?", "Source"],
        prows,
        note="Each document is a file in the repository; its SHA-256 is recorded here and the "
             "document is never edited again, because an edit would change the hash. The last "
             "column is 'no - recorded' for every strategy: the picks the repository published "
             "for the 2026-11-14 slate were made on 2026-11-14, before this freeze, so for "
             "those picks the pre-registration is a reconstruction rather than a prior. That is "
             "stated in the document itself and is on the Flagged for Review page."))
    lrows = []
    for e in ledger.get("entries", []):
        lrows.append([
            BD.esc(e.get("ledger_id")), BD.esc(e.get("date")),
            BD.esc(e.get("strategy")), BD.esc(e.get("market")),
            BD.esc(e.get("side")), BD.esc(e.get("payload", {}).get("line_display")),
            BD.esc(e.get("published_at_utc")), BD.esc(e.get("tip_utc")),
            BD.esc(e.get("seal_state")),
            "<code>%s</code>" % BD.esc((e.get("payload_sha256") or "")[:20] + "..."),
            BD.esc((e.get("settlement") or {}).get("result")),
            BD.esc(e.get("verified_at_utc")),
            BD.esc(e.get("verification_result")),
            multi((e.get("settlement") or {}).get("source_url"), "official final"),
        ])
    b.append(BD.h2("The sealed ledger",
                    "Every published pick, its payload hash, when the hash was published "
                    "against the tip time, and the post-settlement verification."))
    b.append(BD.table(
        ["Ledger id", "Date", "Strategy", "Market", "Side", "Line", "Published (UTC)",
         "Tip (UTC)", "Seal state", "Payload SHA-256", "Result", "Verified (UTC)",
         "Verification", "Source"],
        lrows,
        note="The verification column compares the payload re-hashed after settlement with "
             "the hash published before tip. 'MATCH' means the published pick was not altered. "
             "The seal state says whether the hash was published before the tip time or after "
             "it - picks published on 2026-11-14 for the 2026-11-14 slate could not be sealed "
             "before their own tip, and the ledger says so instead of pretending otherwise."))
    return BD.page("Sealed ledger and pre-registration",
                   "The tamper-evident pick ledger and the frozen pre-registration file for "
                   "every strategy: hash published before tip, verified after settlement.",
                   "\n".join(b))


def build_estimators(hz, est):
    ev = est.get("evaluation", {})
    hca = hz.get("hca_pinning") or {}
    b = []
    b.append(BD.banner("info", "Two estimators, and the disagreement between them",
                       "<p><strong>Estimator A</strong> reads the NBA's published efficiency "
                       "ratings from the official team-stat pages. <strong>Estimator B</strong> "
                       "rebuilds offensive and defensive points-per-possession from the raw "
                       "official box scores of each team's last ten games and never reads those "
                       "ratings. The <strong>disagreement between them is the published "
                       "headline</strong>; the blend is printed underneath it and is never the "
                       "headline on its own.</p>"))
    b.append(BD.h2("Home-court advantage, pinned to the measured home-win rate",
                    "HCA is not a free coefficient: it is the points shift that makes the "
                    "model's average implied home-win probability equal the home-win rate "
                    "actually measured on the official results."))
    b.append(BD.table(
        ["Measurement", "Value", "Source"],
        [
            ["Measured home-win rate (training window)",
             BD.num(hca.get("measured_home_win_rate"), 4), BD.srclink_url(
                 "https://www.nba.com/games?date=2026-11-05", "official results")],
            ["Home wins / games measured",
             "%s / %s" % (hca.get("measured_home_wins"), hca.get("measured_games")),
             BD.srclink_url("https://www.nba.com/games", "official results")],
            ["Measurement window",
             BD.esc("%s .. %s" % (hca.get("measurement_window", {}).get("from"),
                                  hca.get("measurement_window", {}).get("to"))),
             BD.srclink_url("https://www.nba.com/games", "official results")],
            ["Margin sigma used by the solver (points)",
             BD.num(hca.get("margin_sigma_points"), 2),
             BD.srclink_url("https://www.nba.com/games", "official results")],
            ["Pinned HCA (points)",
             BD.num(hca.get("hca_points_pinned"), 2),
             BD.srclink_url("https://www.nba.com/stats/teams/advanced", "ratings")],
            ["Mean implied home-win rate after pinning",
             BD.num(hca.get("mean_implied_home_win_rate_after_pinning"), 4),
             BD.srclink_url("https://www.nba.com/stats/teams/advanced", "ratings")],
            ["Solver", BD.esc(hca.get("solver")), BD.srclink_url(
                "https://github.com/wingbangboozle1-lang/NBA1/blob/main/scripts/"
                "rolling_slate_model.py", "code")],
        ],
        source_col="Source",
        note="The pinned HCA is applied to BOTH estimators, so the published disagreement "
             "between them is a disagreement about the teams, not about the home court."))
    b.append(BD.h2("Out-of-sample comparison",
                    "Measured on the official games of the out-of-sample window."))
    b.append(BD.table(
        ["Measure", "Estimator A", "Estimator B", "Reference line", "Source"],
        [
            ["Games scored", BD.esc(ev.get("n_A")), BD.esc(ev.get("n_B")),
             BD.esc(ev.get("n_reference")),
             BD.srclink_url("https://www.nba.com/games", "official results")],
            ["Log loss (lower is better)", BD.num(ev.get("log_loss_A"), 4),
             BD.num(ev.get("log_loss_B"), 4), BD.num(ev.get("log_loss_reference"), 4),
             BD.srclink_url("https://www.nba.com/games", "official results")],
            ["Brier score", BD.num(ev.get("brier_A"), 4), BD.num(ev.get("brier_B"), 4),
             BD.num(ev.get("brier_reference"), 4),
             BD.srclink_url("https://www.nba.com/games", "official results")],
            ["Margin MAE (points)", BD.num(ev.get("mae_margin_A"), 2),
             BD.num(ev.get("mae_margin_B"), 2), BD.num(ev.get("mae_margin_reference"), 2),
             BD.srclink_url("https://www.nba.com/games", "official results")],
            ["Total MAE (points)", BD.num(ev.get("mae_total_A"), 2), BD.NA,
             BD.num(ev.get("mae_total_reference"), 2),
             BD.srclink_url("https://www.nba.com/games", "official results")],
            ["Blend weight from the measured log loss",
             BD.num(ev.get("blend_weight_A"), 4), BD.num(ev.get("blend_weight_B"), 4),
             BD.NA, BD.srclink_url("https://github.com/wingbangboozle1-lang/NBA1/blob/"
                                   "main/scripts/rolling_slate_build.py", "code")],
        ],
        note=BD.esc(ev.get("note") or "")))
    b.append(BD.h2("The total: possessions &times; points-per-possession",
                    "The model total is the game's possessions multiplied by the measured "
                    "points per possession of the two teams, instead of an average of the two "
                    "teams' scoring averages."))
    trows = []
    for r in hz["rows"]:
        trows.append([
            BD.esc(r["date"]), '<b>%s</b>' % BD.esc(r["matchup"]),
            BD.num(r.get("possessions"), 1),
            BD.num(r.get("total_ppp_home"), 4), BD.num(r.get("total_ppp_away"), 4),
            BD.num(r.get("total_possessions_x_ppp"), 1),
            BD.num(r.get("total_avg_of_scoring_averages"), 1),
            BD.num(r.get("estimator_b", {}).get("total"), 1),
            multi((r.get("slate_source_url"), "slate"),
                  ("https://www.nba.com/stats/teams/advanced", "ratings"),
                  ("https://www.nba.com/stats/teams/traditional", "traditional")),
        ])
    b.append(BD.table(
        ["Date", "Matchup", "Possessions", "PPP home", "PPP away",
         "Total (poss &times; PPP)", "Avg-of-averages total", "Estimator B total", "Source"],
        trows,
        note="PPP home is the average of the home team's offensive rating and the away "
             "team's defensive rating, divided by 100; possessions come from the official "
             "PACE column. The avg-of-averages column is the method the brief rules out and "
             "is published only so the difference is visible."))
    ma = est.get("market_anchored_prior", {})
    b.append(BD.h2("The market-anchored prior",
                    "The blend machinery, the measured weight, and the market leg - which is "
                    "blank because no NBA-operated source publishes a closing line."))
    b.append(BD.table(
        ["Item", "Value", "Source"],
        [
            ["Rule", BD.esc(ma.get("rule")), BD.srclink_url(
                "https://github.com/wingbangboozle1-lang/NBA1/blob/main/scripts/"
                "rolling_slate_build.py", "code")],
            ["Measured weight on the model (out-of-sample log loss)",
             BD.num(ma.get("measured_weight_model"), 4),
             BD.srclink_url("https://www.nba.com/games", "official results")],
            ["Market line (closing line)", BD.NA, BD.srclink_url(
                "https://www.nba.com/games?date=2026-11-15", "no closing line here")],
            ["Market leg status", BD.esc(ma.get("market_line_status")), BD.NA],
            ["Flag", BD.esc(ma.get("flag")), BD.srclink_url(
                "https://github.com/wingbangboozle1-lang/NBA1/blob/main/"
                "data/content/flagged.json", "flag register")],
        ],
        note="The weight is measured, not chosen: it is the logistic of the out-of-sample "
             "log-loss difference between the model and the anchor. The market leg itself is "
             "left blank and flagged, because filling it in would mean inventing a price."))
    return BD.page("Two estimators and the disagreement",
                   "The two independent estimators, the home-court advantage pinned to the "
                   "measured home-win rate, the possession-based total, the market-anchored "
                   "prior and the measured out-of-sample comparison.",
                   "\n".join(b))


def build_minutes(minutes):
    b = []
    b.append(BD.banner("info", "How the minutes are modelled",
                       "<p>Every team's top-8 minutes shares are measured from the official box "
                       "scores of its last ten games. When the official injury report says a "
                       "player is out, the share of the team's minutes that player holds is "
                       "replaced, and the replacement is allocated over the remaining rotation "
                       "in proportion to current minutes share. The rule is printed with every "
                       "row so it can be checked.</p>"))
    rows = []
    for team, players in sorted(minutes.get("top8_minutes_shares", {}).items()):
        for i, p in enumerate(players):
            rows.append([
                BD.esc(team), BD.esc(i + 1), BD.esc(p["player"]),
                BD.num(p["minutes_per_game"], 1), BD.num(p["minutes_share"], 4),
                BD.num(p["points_per_game"], 1), BD.num(p["rebounds_per_game"], 1),
                BD.num(p["assists_per_game"], 1),
                BD.srclink_url("https://www.nba.com/games", "official box scores"),
            ])
    b.append(BD.h2("Top-8 minutes shares, every team",
                    "Measured from the official box scores of the last ten games."))
    b.append(BD.table(
        ["Team", "Rank", "Player", "Min / game", "Minutes share", "Pts / game",
         "Reb / game", "Ast / game", "Source"],
        rows,
        note="A minutes share is the player's minutes divided by the team's total minutes "
             "(240 per game) over the games used. The share is the unit the injury impact is "
             "computed in."))
    rrows = []
    for blk in minutes.get("redistribution", []):
        for r in blk.get("rows", []):
            alloc = "; ".join("%s +%.4f" % (a["player"], a["replacement_share"])
                              for a in r.get("replacement_allocation", [])[:5])
            rrows.append([
                BD.esc(blk["date"]), BD.esc(blk["matchup"]), BD.esc(r["team"]),
                BD.esc(r["player"]), BD.esc(r["status"]),
                BD.num(r["status_weight"], 2),
                BD.num(r["player_minutes_share"], 4),
                BD.num(r["share_to_replace"], 4),
                BD.esc(alloc) if alloc else BD.NA,
                BD.esc(r.get("reason")),
                BD.srclink_url(minutes.get("injury_edition_url"), "injury report"),
            ])
    b.append(BD.h2("Minutes redistribution",
                    "Every player the official report lists, the share that has to be "
                    "replaced, and where it goes."))
    b.append(BD.table(
        ["Date", "Matchup", "Team", "Player", "Status", "Status weight",
         "Player's minutes share", "Share to replace", "Replacement allocation",
         "Reason printed", "Source"],
        rrows,
        note="Status weights: Out 1.0, Doubtful 0.7, Questionable 0.35, Probable 0.1, "
             "Available 0.0. The replacement allocation lists the rotation players who "
             "absorb the share and how much each takes."))
    return BD.page("Minutes redistribution",
                   "Per-team top-8 minutes shares measured from the official box scores, and "
                   "the explicit replacement of the minutes a player loses when the official "
                   "injury report rules them out.",
                   "\n".join(b))


def build_player_logs(logs):
    b = []
    rows = []
    for p in logs.get("players", []):
        for g in p["games"]:
            rows.append([
                BD.esc(p["player"]), BD.esc(p["team"]), BD.esc(g["date"]),
                BD.esc(g["opponent"]), BD.esc(g["minutes"]), BD.esc(g["points"]),
                BD.esc(g["rebounds"]), BD.esc(g["assists"]),
                BD.srclink_url(g.get("source_url"), "official box score"),
            ])
    b.append(BD.banner("info", "What this is",
                       "<p>Per-player game logs for every player who appears on the official "
                       "injury report, read straight out of the official box scores: minutes, "
                       "points, rebounds, assists and the opponent. This is the raw material "
                       "for the prop variance work and for the minutes redistribution.</p>"))
    b.append(BD.h2("Game logs for the players on the injury report",
                    "One row per player per game."))
    b.append(BD.table(
        ["Player", "Team", "Date", "Opponent", "Minutes", "Points", "Rebounds",
         "Assists", "Source"],
        rows,
        note="Minutes are printed exactly as the official box score prints them (for "
             "example 36:12). The games shown are the most recent official box scores "
             "available in the capture window."))
    return BD.page("Player game logs",
                   "Per-player game logs - minutes, points, rebounds, assists and the "
                   "opponent - for every player who appears on the official injury report.",
                   "\n".join(b))


def build_injury_editions(inj):
    b = []
    editions = inj.get("editions", [])
    live = [e for e in editions if e.get("http_status") == 200]
    b.append(BD.tiles([
        ("Editions probed", len(editions), "every 15-minute slot of the rolling window"),
        ("Editions stored", len(live), "PDF bytes kept, with sha256 and fetch time"),
        ("Consecutive diffs", len(inj.get("diffs", [])), "one diff per published pair"),
    ]))
    b.append(BD.banner("info", "How the archive works",
                       "<p>Every injury-report edition the league publishes is fetched, stored "
                       "byte for byte, and recorded with its publication time, the URL it came "
                       "from, the moment it was fetched and the SHA-256 of the bytes. The "
                       "archive is then diffed edition against edition, so a status change "
                       "between two publications is visible rather than inferred.</p>"))
    rows = []
    for e in live:
        rows.append([
            BD.esc(e["edition_id"]), BD.esc(e.get("revision_time_et")),
            BD.esc(e.get("fetched_at_utc")), BD.esc(e.get("bytes")),
            "<code>%s</code>" % BD.esc((e.get("sha256") or "")[:20] + "..."),
            BD.esc(len(e.get("rows") or [])),
            BD.srclink_url(e.get("url"), "official PDF"),
        ])
    b.append(BD.h2("Every stored edition",
                    "Publication time, retrieval time, byte length and content hash."))
    b.append(BD.table(
        ["Edition", "Revision time (ET)", "Retrieved (UTC)", "Bytes", "SHA-256",
         "Rows read", "Source"],
        rows,
        note="The revision time is the edition's own publication time (the time printed on "
             "the official PDF); the retrieval time is when this repository fetched it. The "
             "two are different things and are both shown."))
    drows = []
    for d in inj.get("diffs", []):
        for c in d.get("changes", []):
            drows.append([
                BD.esc(d["date"]),
                BD.esc(d["from_revision_time_et"]), BD.esc(d["to_revision_time_et"]),
                BD.esc(c.get("team")), BD.esc(c.get("player")),
                BD.esc(c.get("from_status")), BD.esc(c.get("to_status")),
                BD.esc(c.get("change")),
                multi((d.get("from_source_url"), "from"), (d.get("to_source_url"), "to")),
            ])
    b.append(BD.h2("Status changes between consecutive editions",
                    "Every movement detected by diffing one edition against the one before it."))
    b.append(BD.table(
        ["Date", "From", "To", "Team", "Player", "Was", "Now", "Change", "Source"],
        drows,
        note="A row is present only when the status actually moved. 'added' means the player "
             "appeared in the newer edition and 'removed' means the player disappeared "
             "from it."))
    return BD.page("Injury-report archive",
                   "Every official injury-report edition in the rolling window, stored with "
                   "its timestamp and content hash, and the status changes detected by "
                   "diffing consecutive editions.",
                   "\n".join(b))


def build_into(built):
    """Add this build's pages to the page dict `scripts/build_dashboard.py` is
    about to write, and write the JSON the pages were rendered from."""
    pages, data = build_pages()
    built.update(pages)
    for name, payload in data.items():
        write_json(os.path.join(SITE_DATA, name), payload)
    log("added %d rolling-slate pages" % len(pages))
    return built


def build_pages():
    os.makedirs(PAGES, exist_ok=True)
    os.makedirs(SITE_DATA, exist_ok=True)
    hz = load(os.path.join(DER, "horizon.json"))
    est = load(os.path.join(DER, "estimates.json"))
    results = load(os.path.join(DER, "results.json"))
    settlement = load(os.path.join(DER, "settlement.json"))
    minutes = load(os.path.join(DER, "minutes.json"))
    picks = load(os.path.join(DER, "picks.json"))
    corr = load(os.path.join(DER, "correlations.json"))
    inj = load(os.path.join(DER, "injury_editions.json"))
    logs = load(os.path.join(DER, "player_logs.json"))
    luck = load(os.path.join(DER, "luck.json"))
    ledger = load(os.path.join(LEDGER, "ledger.json"))
    prereg = load(os.path.join(LEDGER, "preregistration.json"))
    if not hz:
        raise SystemExit("no horizon.json - run scripts/rolling_slate_build.py first")

    built = {
        "projection.html": build_projection(hz, minutes, results),
        "bet.html": build_bet(hz, picks, ledger, prereg),
        "results.html": build_results(results, settlement),
        "ledger.html": build_ledger(ledger, prereg),
        "estimators.html": build_estimators(hz, est),
        "minutes.html": build_minutes(minutes),
        "player-logs.html": build_player_logs(logs or {"players": []}),
        "injury-editions.html": build_injury_editions(inj),
    }
    data_files = {}
    for src, dst in (("horizon.json", "horizon.json"), ("estimates.json", "estimators.json"),
                     ("results.json", "results.json"), ("settlement.json", "settlement.json"),
                     ("minutes.json", "minutes.json"), ("picks.json", "picks_new.json"),
                     ("correlations.json", "correlations_measured.json"),
                     ("injury_editions.json", "injury_editions.json"),
                     ("player_logs.json", "player_logs.json"),
                     ("luck.json", "luck_z.json")):
        payload = load(os.path.join(DER, src))
        if payload is not None:
            data_files[dst] = payload
    for src, dst in (("ledger.json", "ledger.json"),
                     ("preregistration.json", "preregistration.json")):
        payload = load(os.path.join(LEDGER, src))
        if payload is not None:
            data_files[dst] = payload
    return built, data_files


def main():
    pages, data = build_pages()
    for name, html in pages.items():
        with open(os.path.join(PAGES, name), "w", encoding="utf-8") as fh:
            fh.write(html)
    for name, payload in data.items():
        write_json(os.path.join(SITE_DATA, name), payload)
    log("wrote %d pages" % len(pages))


if __name__ == "__main__":
    sys.exit(main())
