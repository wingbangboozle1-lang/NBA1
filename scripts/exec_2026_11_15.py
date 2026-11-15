#!/usr/bin/env python3
"""Executive-summary content for the 2026-11-15 day roll.

Rewrites the parts of data/content/executive.json whose numbers the roll moved (horizon length,
window length, injury edition in force), records the two model inputs the roll turned into
measurements (the home-court pin and the travel gap), and re-ranks the next actions so a reader
sees what changed today before what is still open. Findings are appended, never renumbered.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "content", "executive.json")
DAY = "2026-11-15"
SESSION = "arena/e3ebc423-nba1"

e = json.load(open(PATH, encoding="utf-8"))

e["as_of"] = DAY
e["roll_2026_11_15"] = {
    "at_utc": "2026-11-15T12:10:00Z",
    "session": SESSION,
    "gates": "17 freshness + provenance gates run, 0 failed (data/live/gates_2026-11-15.json); the roll "
             "refuses to write a snapshot when any gate fails",
    "horizon_games": 34,
    "horizon_dates": "2026-11-15 (9), 11-16 (8), 11-17 (5), 11-18 (12)",
    "completed_games": 65,
    "oos_window": "2026-11-06 to 2026-11-14",
    "settled_slate": "2026-11-14: 3-10 on the 13 gradable published picks, -5.80 units at the -110 "
                     "convention; 4 rows not gradable (F69). Parlays 0-2.",
    "injury_edition": "11/15/26 06:15 AM ET, 101 rows, diffed against the 06:00 AM edition (0 status "
                      "changes); 11/16 rows NOT YET SUBMITTED at that edition",
    "ledger": "60 pick hashes + chain head published (data/live/ledger_2026-11-15.json), anchored to git "
              "blob 1b962a91275c of the frozen picks file",
}

e["headline"] = (
    "The horizon runs the full three days after a day roll: 34 games from 15 to 18 November 2026, each one "
    "re-read from the official date cards and cross-checked against the standings page read in the same "
    "window. The 2026-11-14 slate is settled against official finals - 3-10 on the 13 gradable picks, "
    "-5.80 units at the repo's -110 convention, with 4 rows left ungraded because no per-player box score "
    "is citable - and every published pick now carries a hash, a before-tip attestation and a settlement "
    "stamp on the page. Home court is finally a measurement rather than a constant, and it disagrees with "
    "the constant by a factor of more than two.")

e["lead"] = (
    "Ten strategies were written, seven validation gates were defined, and all ten were run against a "
    "strictly out-of-sample window: all 65 completed games from 2026-11-06 to 2026-11-14, every one "
    "predicted using team ratings computed only from 2026-10-20 to 2026-11-05, so no game in the test "
    "window contributes to the ratings that predict it. On top of that the system originates a line for "
    "every game in the next three days - 15, 16, 17 and 18 November - from official ratings and the newest "
    "official injury report, now the 11/15/26 06:15 AM ET edition, diffed against the 06:00 AM edition "
    "published fifteen minutes earlier.\n\n"
    "What the last twenty-four hours changed is procedural, and it matters more than any single line. The "
    "injury report the site had been reading was PM-only: the league republishes its report every 15 "
    "minutes from 12:00 a.m. ET, and the index parser only accepted names ending in PM, so a morning run "
    "walked past the newest edition of the day. That is fixed, unit-checked and gated (F74). The picks "
    "table and the settlement ledger, which previously lived in separate files and agreed on nothing, are "
    "now wired: each row carries a settled flag, the final, the distance to its own published line and "
    "the git blob it was graded against. And home court - until today a hard-coded 2.5-point assumption - "
    "has been pinned to the measured league home-win rate, 0.5294 on 187 home games in the standings and "
    "0.5469 on the 64 non-neutral games in our own results feed, which converts to 1.053 points under the "
    "model's margin spread. The published lines still use 2.5, because they are frozen and hashed and "
    "re-pricing a line after tip would void the pre-registration; the pin takes effect at the next freeze, "
    "and the sensitivity of every un-tipped row is printed instead of being applied quietly (F71, Q22).\n\n"
    "What did not become possible: travel distance is still not in the model. The term, the great-circle "
    "arithmetic and the data contract are all written and self-checked, but no NBA-operated page reachable "
    "from this build publishes arena coordinates, and coordinates copied from memory would be untraceable "
    "numbers in a table whose entire purpose is traceability. So the coefficient stays 0.0, and the only "
    "travel fact the official cards do state - whether a team's next game is in the city it is already in "
    "- is published in its place, with the gap named beside it (F70, SG31).")

_n = len(e["findings"])
NEW_FINDINGS = [{
    "n": _n + 1,
    "title": "Home court, measured: the assumption was more than double the rate the league's own results support",
    "detail": ("Pinned to the measured home-win rate, home court is 1.053 points (0.5294 on the 187 home games "
               "in the official standings HOME column; 0.5469 on the 64 non-neutral games in the committed "
               "results feed; sigma 11.0 points). The published lines use 2.5, flagged E-01 as an assumption, and "
               "engine/validate.py's in-sample residual intercept says 3.508. The three are printed beside each "
               "other on the day-roll page and are not averaged: the disagreement is the finding. Applying the "
               "pin to the un-tipped horizon shifts every home margin by -1.447 points, changes no total, and "
               "flips the model's favourite on a minority of rows - all of which is published as a sensitivity "
               "table rather than applied silently, because the picks are frozen and hashed."),
    "source_url": "https://www.nba.com/standings",
    "reading": ("Home court is the single biggest input the site had never measured, and measuring it moves "
                "the price of a home team by more than the model's entire shrinkage adjustment. The honest "
                "move was to publish the pin, quantify what it would do, and take it up at the next freeze - "
                "not to quietly re-price a slate whose picks are already hashed."),
}] + [{
    "n": _n + 2,
    "title": "Settling a slate is now the same act as publishing one, and a losing slate publishes as a losing slate",
    "detail": ("The 2026-11-14 slate settles 3-10 on the 13 gradable published picks, -5.80 units at the -110 "
               "convention, with the parlays 0-2 and four player-prop rows marked not gradable because no "
               "allowed host gives this build a per-player box score. Each row links the official date card that "
               "published its final, each is graded against the frozen git blob of the picks file rather than the "
               "working copy, and the whole set is chained by sha256 (60 hashes, chain head published). One "
               "slate of 13 picks is nowhere near evidence of anything, in either direction, and the page says "
               "so; the point of the table is that the loss, the ungradable rows and the reason for each are all "
               "visible in the same place as the record."),
    "source_url": "https://www.nba.com/games?date=2026-11-14",
    "reading": ("A 3-10 slate against your own number is not a verdict on the model - it is one night inside a "
                "distribution with no vig and no market in it. What it does prove is that the settlement path "
                "runs end to end: the picks, the hashes, the finals and the graded rows all agree, and the "
                "rows that could not be graded say why instead of disappearing."),
}]
_titles = {f["title"] for f in e["findings"]}
e["findings"].extend([f for f in NEW_FINDINGS if f["title"] not in _titles])

live = [x for x in e["what_is_live_now"] if "27 games across" not in x and "11/14/26 04:15 AM ET edition" not in x]
live = [x.replace("60 gated picks", "60 gated picks") for x in live]
e["what_is_live_now"] = [
    ("Originated spreads, totals, moneylines and fair prices for the horizon, with the horizon itself rolled "
     "today: 34 games across 2026-11-15, 11-16, 11-17 and 11-18, every tip time and record re-read from the "
     "official date cards and cross-checked against the standings table read in the same window (30/30 teams "
     "agree)."),
    ("The official per-game result feed for 2026-11-14: one row per game with date, teams, final, OT flag, "
     "venue, attendance, officials and quarter scores - 4 of 5 games carry a LINESCORES split and each "
     "captured split sums to the printed final; the fifth says 'not captured' rather than being solved "
     "backwards (F73)."),
    ("The official injury report, 11/15/26 06:15 AM ET edition, transcribed row by row (101 rows including "
     "the NOT YET SUBMITTED clubs for 11/16), with the report's own revision time and this build's retrieval "
     "time both printed on the page, and diffed against the 06:00 AM edition: 0 status changes in the 15 "
     "minutes between them, one row whose Team cell the earlier render dropped at a page break."),
    ("Settlement of every published paper pick on the 2026-11-14 slate against the official finals, with the "
     "pre-registration attestation (git blob 1b962a91275c of docs/data/picks.json), per-row result, distance "
     "to the published line, units at the -110 convention, and a 'settled' flag on each of the 60 rows of the "
     "picks table so the table and the ledger cannot drift apart."),
] + live
seen, ded = [], set()
for x in e["what_is_live_now"]:
    if x[:60] not in ded:
        ded.add(x[:60]); seen.append(x)
e["what_is_live_now"] = seen

e["recommended_next_actions"] = [
    {"rank": 1,
     "action": "Register a citable per-player box-score source and settle the four pending prop rows",
     "why": ("It is the only thing standing between the prop strategies (S7, S8) and a settled record: the "
             "lines exist, the picks exist, the finals exist, and the minutes/production input does not. "
             "Parsing the box-score table on each NBA.com game page needs no policy change - same host, "
             "already allowed - and it also replaces the estimated minutes column on the props page "
             "(F69, Q24, SG32).")},
    {"rank": 2,
     "action": "Adopt the measured home-court pin at the next freeze (Q22, SG30)",
     "why": ("data/derived/home_court_pin.json is written and reproducible; setting adopted_for_pricing "
             "before the next slate's pre-registration is what stops the site pricing home games with a "
             "number it publishes as too large. Keep 2.5 published as the pre-change column so the settled "
             "window stays interpretable (F71).")},
    {"rank": 3,
     "action": "Add data/official/arena_coordinates.json and fit travel_coef on the 65 completed games",
     "why": ("The travel term and its arithmetic are already in the model, switched off for lack of input. "
             "A published coefficient of 0.0 after fitting would itself be the finding, and would close the "
             "brief's travel requirement honestly (F70, SG31).")},
    {"rank": 4,
     "action": "Complete the minutes input, per club, so the availability layer can see a rotation instead of a top-50 slice",
     "why": "It is what turns tonight's 0.00 columns into numbers, and it unlocks Q3, Q12 and Q20 (SG20, F47)."},
    {"rank": 5,
     "action": "Automate the day roll behind its own gates (Q25, SG33)",
     "why": ("scripts/roll_2026_11_15.py already refuses to write unless all 17 freshness and provenance "
             "gates pass and merges into the committed snapshots instead of replacing them, so the horizon "
             "no longer has to age between sessions.")},
]

if "As of 2026-11-15 the machinery" not in e["bottom_line"]:
    e["bottom_line"] = (e["bottom_line"].rstrip() + " As of 2026-11-15 the machinery also rolls itself forward and settles itself: 34 games "
                    "re-read, one slate settled against official finals with the loss published as a loss, 60 "
                    "hashes chained, the injury report read at its newest edition and diffed against the one "
                    "before it, and home court measured instead of assumed. What is still missing is narrow and "
                    "specific - a citable per-player box score and a sourced arena-coordinate table - and both "
                    "gaps are named on the page that prices with them closed, not papered over.")

with open(PATH, "w", encoding="utf-8") as fh:
    json.dump(e, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
print("executive.json: as_of %s, findings %d, live rows %d, next actions %d"
      % (e["as_of"], len(e["findings"]), len(e["what_is_live_now"]), len(e["recommended_next_actions"])))
