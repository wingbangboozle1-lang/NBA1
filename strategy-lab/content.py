"""Editorial content for the lab's decision page.

Numbers are deliberately kept out of this file wherever a table already carries them, so
that re-running the analysis cannot leave a sentence quoting a stale figure.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labdata import site_fit  # noqa: E402  (same inputs the tables are built from)

_PUB = site_fit()
_SITE_B2B = _PUB["b2b_penalty_applied"]
_SITE_WIN = str(_PUB["n_games"]) + " games, " + str(_PUB["window_first"]) + ".." + str(_PUB["window_last"])
_GRADE = str(_PUB["window_first"]) + ".." + str(_PUB["window_last"]) + ", " + str(_PUB["n_games"]) + " games"

NBA_DAY = "https://www.nba.com/games?date="
NBA_STATS = "https://www.nba.com/stats/teams/advanced"
BLOB = "https://github.com/wingbangboozle1-lang/NBA1/blob/main/"

CONTENT = {
 "title": "Decision register for the strategy lab",
 "how_to_use": ("Answered rows are decisions the data on hand already supports, with the table that "
                "shows them. Open rows say precisely what is missing and the step that would obtain it; "
                "nothing else in this repository may be promoted on an open row. Suggestions are options "
                "with a named owner - this session changed no file outside strategy-lab/."),
 "questions": {
   "answered": [
    {"id": "A1", "question": "Is the season game log the repository relies on complete?",
     "answer": "No. It holds every game with a published score for 2026-10-20..2026-11-12 and the nine 11/13 finals, which is 23 short of the official games-played column; the two missing dates are 2026-10-24 and 2026-11-02. Their fixtures are now in the schedule layer, their scores are not, and none was inferred.",
     "evidence": "Backfill page: per-team reconciliation and per-date calendar reconciliation, both zero mismatches.",
     "confidence": "High - three independent official instruments agree.",
     "source_url": NBA_DAY + "2026-11-02"},
    {"id": "A2", "question": "Does that gap change any pick the site has already published?",
     "answer": ("No. Every affected team-slot sits on a date outside the window the site grades on (" +
                _GRADE + "), so the leaderboard, the settled picks and the gates are unaffected. What the gap "
                "does invalidate is any October backtest, which is the base this lab used instead."),
     "evidence": "Rest page KPI: 'of them inside the window the site grades on' reads zero, and the window it is measured against is read from site/data/backtest.json at build time.",
     "confidence": "High - recomputed slot by slot against the official schedule.",
     "source_url": "https://www.nba.com/games?date=2026-10-25"},
    {"id": "A3", "question": "Does any strategy in a season-wide library beat the originated line?",
     "answer": "Not on this evidence. The best excess over the line's own expectation is small, its exact p-value is far from significant, and a shared-draw simulation of the whole library shows a luck-only library of the same size producing a best that large on essentially every run.",
     "evidence": "Leaderboard page: library table plus the luck control.",
     "confidence": "High for the conclusion 'not proven'; the window is still only a season quarter.",
     "source_url": NBA_DAY + "2026-10-20"},
    {"id": "A4", "question": "Is the back-to-back penalty the site puts into every line supported by the season?",
     "answer": "No. Measured on the completed games where both teams have a game on record, the effect is statistically indistinguishable from zero, with an interval wide enough to contain the published figure comfortably. The published number was fitted on one week.",
     "evidence": "Correlations page: the back-to-back row with its standard error and interval.",
     "confidence": "Medium-high: the sign and size are uncertain, but a 6-point line move is certainly unjustified by this sample.",
     "official_url": "https://www.nba.com/games?date=2026-10-20",
     "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/backtest.json"},
    {"id": "A5", "question": "Are the rest and back-to-back flags on the live horizon pages correct?",
     "answer": "Yes - all 27 unplayed games x both teams reproduce from the official schedule, including the 2026-11-13 games that the game log itself does not carry.",
     "evidence": "Rest page horizon check, and the Slate impact page's reproduction count.",
     "confidence": "High.",
     "source_url": NBA_DAY + "2026-11-14"},
    {"id": "A6", "question": "Is the side/total correlation the same-game parlay pricing assumes to be zero actually zero?",
     "answer": "On the season it is close to zero and not distinguishable from zero, so the assumption survives the check. The same-night leg correlation, by contrast, cannot be measured on this sample - only two dozen date-pairs exist - so parlay pricing stays where it is, labelled as an assumption.",
     "evidence": "Correlations page: the margin/total row and the leg block.",
     "confidence": "Medium for margin/total; low for same-night legs, on sample size alone.",
     "source_url": NBA_DAY + "2026-10-20"},
    {"id": "A7", "question": "Are the probability columns the game-flow page publishes consistent with what the season did?",
     "answer": "Home win and close-margin columns are within a point of the realised rates. The overtime column is not: the season went to overtime several times more often than the page's mean probability implies, and that gap is beyond what sampling noise explains at this sample size.",
     "evidence": "Gates page: the probability audit table.",
     "confidence": "High on the direction; the comparison is a distribution check, not a graded forecast, because the published rows describe unplayed games.",
     "official_url": "https://www.nba.com/games?date=2026-11-14",
     "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/gameflow.json"},
    {"id": "A8", "question": "Can this lab say whether any strategy beats a book?",
     "answer": "No, and it does not try to. No NBA-operated source publishes a closing price, so no row in this directory claims a market edge. 'Edge' here always means the model against its own naive reference.",
     "evidence": "Meta file: what this directory does not use.",
     "confidence": "Certain - the limitation is structural, not a data gap this session could close.",
     "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/README.md"},
   ],
   "open": [
    {"id": "O1", "question": "What is the true closing price on each line the site originates?",
     "what_is_missing": "A licensed, dated odds snapshot with the book's line and price for each market.",
     "how_to_get_it": "A commercial odds feed, or a documented capture policy for a named sportsbook - either way it needs an owner and a licence, not a scrape.",
     "blocks": "The market gate, on every strategy, in every build of this repository.",
     "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/questions.json"},
    {"id": "O2", "question": "What were the 23 scores on 2026-10-24 and 2026-11-02?",
     "what_is_missing": "The official day page for those dates prints FINAL with an empty score cell, and the box-score path serves the site-wide scoreboard instead of an archived box score to a non-browser client.",
     "how_to_get_it": "Either an authorised stats feed, or a capture step that renders the archived game page in a browser context and stores it; the project's own verification workflow already has a headless renderer for the site, so the capability exists.",
     "blocks": "Grading October games, so the sample stays smaller than the season.",
     "source_url": NBA_DAY + "2026-10-24"},
    {"id": "O3", "question": "How many minutes does each player actually play?",
     "what_is_missing": "Minutes are on record for the captured top-50 minutes table, not for the ~465-man league. Availability and prop impact are therefore lower bounds.",
     "how_to_get_it": "One official per-player traditional table capture, all rows, per date; the pages exist and render for the browser.",
     "blocks": "Prop projections becoming anything other than a bounded estimate, and the injury impact factor the site flags as a modelling choice.",
     "source_url": "https://www.nba.com/stats/players/traditional"},
    {"id": "O4", "question": "What does the injury report say for the games on 2026-11-15 and later?",
     "what_is_missing": "Those editions are not published until game day, per the official policy the site links.",
     "how_to_get_it": "Re-run the injury capture on the morning of each game day; the refresh path in the workflows directory already does this for the next slate.",
     "blocks": "Injury adjustment on most of the three-day horizon.",
     "source_url": "https://official.nba.com/nba-injury-report-2026-27-season/"},
    {"id": "O5", "question": "What were each team's efficiency ratings as of each historical date?",
     "what_is_missing": "Only two windows are captured: season-to-date and one training window. A walk-forward on the site's own efficiency model needs a snapshot per date.",
     "how_to_get_it": "Capture the official team table each morning into a dated store, then a real point-in-time backtest becomes available; until then a margin-based rating is the honest substitute, which is what this lab used.",
     "blocks": "Promoting the site's efficiency model - as opposed to a movement model - on more than one week of data.",
     "source_url": NBA_STATS},
    {"id": "O6", "question": "How many possessions did each team have in each game?",
     "what_is_missing": "Possessions per game are not in any captured file, so per-game offensive and defensive ratings cannot be built from the box scores alone.",
     "how_to_get_it": "Official league box scores carry the four-factor components; a per-game capture would let the totals model be measured instead of approximated.",
     "blocks": "A totals line that is comparable to the side line, and a measured pace input for the game-flow page.",
     "source_url": "https://www.nba.com/stats/help/glossary"},
    {"id": "O7", "question": "Should the back-to-back term stay in the line at 6.1 points?",
     "what_is_missing": "A decision by the owner of the model, informed by the season measurement and by the slate movement this lab publishes.",
     "how_to_get_it": "Pick one: keep, shrink toward the season estimate, or drop and label. All three are defensible; the current state - a one-week fit applied silently to every game - is not.",
     "blocks": "Any claim that the lines are calibrated.",
     "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/backtest.json"},
    {"id": "O8", "question": "Which rest and spread conventions are the site's?",
     "what_is_missing": "One definition of rest_days (gap days or days off) and one sign convention for the spread. Different builds currently use different ones, which the repository already flags.",
     "how_to_get_it": "A naming decision in the shared builders and one line of documentation; both are owned by the integration seat.",
     "blocks": "Comparing two builds' numbers, which is the point of having both.",
     "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/flagged.json"},
   ]
 },
 "suggestions": [
  {"id": "SG-L1", "title": "Feed the published fixtures into the rest history",
   "category": "Data integrity",
   "problem": "The game log's own note says the fixtures keep the rest layer complete, but the consumers build their history from games that carry a score, so they do not.",
   "options": "(a) read known_unplayed_by_source.fixtures in engine_v2/context.py and scripts/originate_horizon.py; (b) add a schedule-only file with all 183 games and make it the single rest input; (c) leave it and correct the note.",
   "cost": "Small - one input change and a re-render.",
   "unlocks": "Correct rest figures for October and 2026-11-04/05, and a defensible full-season backtest.",
   "recommendation": "(b): a schedule-only input is the structure that cannot rot again when a date goes missing.",
   "owner": "owners of engine_v2/context.py and scripts/originate_horizon.py",
   "official_url": "https://www.nba.com/games?date=2026-11-02",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine_v2/context.py"},
  {"id": "SG-L2", "title": "Re-fit or shrink the back-to-back term against the season",
   "category": "Model",
   "problem": ("A " + str(_SITE_B2B) + "-point term fitted on " + _SITE_WIN + " in-sample is applied to every "
               "line, while the season's own measurement of the same effect sits near zero with an interval of "
               "the same width as the estimate."),
   "options": "(a) keep it and publish its interval next to each line; (b) shrink it toward the season estimate; (c) drop it until a season's worth of data says otherwise.",
   "cost": "One re-fit and a slate re-publication; 11 of 27 current games move by 3+ points.",
   "unlocks": "Lines whose adjustments are supported by the sample they are fitted on.",
   "recommendation": "(b) with the interval published; it is the only option that admits the uncertainty without discarding the prior evidence.",
   "owner": "the model owner (engine/ and engine_v2/)",
   "official_url": "https://www.nba.com/games?date=2026-11-14",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine/model_core.py"},
  {"id": "SG-L3", "title": "Split rest_days into two honest field names",
   "category": "Site clarity",
   "problem": "One name carries two definitions across the site: calendar gap on one build, full days off on another, so the same situation prints 1 and 0.",
   "options": "(a) publish both, named; (b) publish gap only and rename the flag; (c) document the difference and change nothing.",
   "cost": "A field rename in the builders and the pages that read them.",
   "unlocks": "Readers comparing the slate page with the validation page without silently mis-reading rest.",
   "recommendation": "(a); this lab already publishes both under gap_days and days_off as a working example.",
   "owner": "the integration seat, which owns the shared builders",
   "official_url": "https://www.nba.com/games?date=2026-11-14",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/horizon_lines.json"},
  {"id": "SG-L4", "title": "Price overtime from the season, not from a formula",
   "category": "Model",
   "problem": "The game-flow page's overtime column sits well below the realised rate on the completed games, and the page itself notes no possession-level input was available.",
   "options": "(a) use the measured season rate as the prior and let the margin distribution scale it; (b) drop the column; (c) keep it and label it a rough approximation.",
   "cost": "Small - one measured constant already exists in this directory's correlations file.",
   "unlocks": "A game-flow column a reader can act on, and an end to a silently under-stated probability.",
   "recommendation": "(a), with the measured rate and its sample size printed next to it.",
   "owner": "the game-flow page owner",
   "official_url": "https://www.nba.com/games?date=2026-11-14",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/gameflow.json"},
  {"id": "SG-L5", "title": "Grade every strategy against the line it bets, not a coin flip",
   "category": "Validation",
   "problem": "A hit rate against a break-even constant flatters any favourite-backer; the only null this repository can defend is 'the originated line was right'.",
   "options": "(a) replace the result gate with the excess-over-model test used here, plus Benjamini-Hochberg across the library; (b) run both and publish both; (c) keep the old gate and label it.",
   "cost": "A gate definition change in the shared validation code.",
   "unlocks": "A leaderboard that cannot be topped by a strategy that merely likes heavy favourites.",
   "recommendation": "(a) for promotion, (b) for display, so the change is auditable.",
   "owner": "the integration seat and the gate owner",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/scripts/strategies.py"},
  {"id": "SG-L6", "title": "Grow the out-of-sample window automatically",
   "category": "Data",
   "problem": "Every build has been limited by whichever dates happened to be captured; the season is three times the window any verdict has been reached on.",
   "options": "(a) a scheduled job that appends each completed date's finals to the log, with the same row-level source links this repository already requires; (b) keep manual captures.",
   "cost": "One workflow and a storage convention; the render and link gates already exist to police it.",
   "unlocks": "Sample sizes that let a gate close at all.",
   "recommendation": "(a) - without it, every future session re-discovers the same ceiling.",
   "owner": "whoever owns the workflows directory",
   "official_url": "https://www.nba.com/games?date=2026-11-13",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/tree/main/.github/workflows"},
  {"id": "SG-L7", "title": "Publish one cross-build scoreboard instead of several quiet ones",
   "category": "Site structure",
   "problem": "Several builds publish lines for the same games with different conventions and no side-by-side view, which is how sign and rest disagreements survived.",
   "options": "(a) a page listing each game with every build's line and its source; (b) nominate one build as canonical and archive the rest; (c) do nothing.",
   "cost": "One generated table, or one documented decision.",
   "unlocks": "Disagreements becoming visible at publication time rather than in a review weeks later.",
   "recommendation": "(a) then (b): show the difference, then pick a canonical build in writing.",
   "owner": "the integration seat",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/index.html"},
 ],
 "flags": [
  {"id": "F-S29-01", "severity": "Medium",
   "title": "23 games of this season cannot be graded from the pages this repository may read",
   "detail": "Both affected dates print FINAL with an empty score cell, reproduced by a third session on 2026-11-14. The fixtures are now used for scheduling; their results stay blank. No score was inferred from the standings residual, although the residual does determine them.",
   "status": "Open - published, non-blocking",
   "source_url": NBA_DAY + "2026-10-24"},
  {"id": "F-S29-02", "severity": "Medium",
   "title": "The rest layer does not read the fixtures the game log publishes for exactly that purpose",
   "detail": ("46 of 366 team-slots change when the fixtures enter the history, and two back-to-back flags flip. "
               "None falls inside the window the site grades on (" + _GRADE + "), so no published pick changes; an "
               "October backtest would have been wrong. Repaired inside strategy-lab only - no site file was "
               "touched, because those files belong to other sessions."),
   "status": "Open - fix proposed to the owners of the two consumers",
   "official_url": "https://www.nba.com/games?date=2026-10-25",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine_v2/context.py"},
  {"id": "F-S29-03", "severity": "High",
   "title": "The back-to-back penalty in every line is a short-window in-sample fit that the season does not support",
   "detail": ("Published penalty " + str(_SITE_B2B) + " points, fitted on " + str(_PUB["n_games"]) +
              " games and disclosed by the site itself as in-sample with its own standard error at " +
              str(_PUB["b2b_se"]) + " (t = " + str(_PUB["b2b_t"]) + ", applied because |t| >= 1). The season "
              "measurement of the same quantity is +0.016 with a standard error of 4.426 on 144 games, p 0.997. "
              "11 of the 27 unplayed horizon games move by 3 points or more between the two positions."),
   "status": "Open - decision requested from the model owner",
   "official_url": "https://www.nba.com/games?date=2026-11-14",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/backtest.json"},
  {"id": "F-S29-04", "severity": "Low",
   "title": "rest_days means two different things on two pages of the same site",
   "detail": "Calendar gap on the out-of-sample pages, full days off on the horizon pages, so an identical situation prints 1 in one place and 0 in the other. Both figures are correct under their own definition; the shared name is the defect.",
   "status": "Open - naming decision for the integration seat",
   "official_url": "https://www.nba.com/games?date=2026-11-14",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/horizon_lines.json"},
  {"id": "F-S29-05", "severity": "Medium",
   "title": "The published overtime probability is materially below the realised season rate",
   "detail": "Mean published probability across the 27 horizon rows against the realised share of the completed games, 8 of 160, exact p 0.012. A distribution check rather than a graded forecast, since the published rows describe unplayed games, but the gap is large enough to act on.",
   "status": "Open - published for the game-flow owner",
   "official_url": "https://www.nba.com/games?date=2026-10-20",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/gameflow.json"},
  {"id": "F-S29-06", "severity": "Low",
   "title": "This lab's figures are pinned to a commit, and main is moving under it",
   "detail": "Other sessions are promoting the 11/13 finals into the derived data now. If main's inputs change, re-running this directory reproduces its own numbers against the new inputs; the pages state the commit they were built from.",
   "status": "Informational",
   "source_url": "https://github.com/wingbangboozle1-lang/NBA1/commit/7623c02"},
 ],
}

def write_out():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "content.json"), "w", encoding="utf-8") as f:
        json.dump(CONTENT, f, indent=1, ensure_ascii=False)
    print("content.json written")


if __name__ == "__main__":
    write_out()
