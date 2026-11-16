#!/usr/bin/env python3
"""Append this session's flags, questions and suggestions, and refresh the
executive summary to the 2026-11-15 state.

    python3 scripts/content_801ba27f.py

Session `arena/801ba27f-nba1`, COORDINATION.md §41 task H06.

Append-only: an id that already exists is never rewritten, so re-running this
script cannot change history that another session already published.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "data", "content")
DERIVED = os.path.join(ROOT, "data", "derived")
SETTLE = os.path.join(ROOT, "data", "settlement")
INJ = os.path.join(ROOT, "data", "injury_reports")

RUN_UTC = "2026-11-15T23:59Z"
GITHUB = "https://github.com/wingbangboozle1-lang/NBA1/blob/main/"
NBA_GAMES = "https://www.nba.com/games"
NBA_SCHEDULE = "https://www.nba.com/schedule"
INJ_INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"
STATS_ADV = "https://www.nba.com/stats/teams/advanced"


def load(name):
    return json.load(open(os.path.join(CONTENT, name)))


def save(name, d):
    with open(os.path.join(CONTENT, name), "w") as fh:
        json.dump(d, fh, indent=1)


def have(items, key):
    return {i[key] for i in items}


def add(items, key, new):
    existing = have(items, key)
    n = 0
    for i in new:
        if i[key] not in existing:
            items.append(i)
            n += 1
    return n


def main():
    # ------------------------------------------------------------- flags
    fl = load("flagged.json")
    new_flags = [
        {"id": "F94", "severity": "medium",
         "title": "Arena latitude/longitude are not published by the NBA, so travel distances are unverified",
         "detail": ("The arena NAME, CITY and STATE on every row of the Rest & Travel page are "
                    "official (printed on the official box score page of a game played there). "
                    "The latitude and longitude are not printed by any NBA page, so the "
                    "great-circle distances computed from them are derived, not official. They "
                    "are published with this flag attached and no travel value is used to move "
                    "a line."),
         "source_url": NBA_GAMES, "status": "open"},
        {"id": "F95", "severity": "high",
         "title": "Market-anchored prior cannot be applied: no official closing line exists anywhere in this repository",
         "detail": ("The brief asks for a market-anchored prior that blends the model line with "
                    "the closing line, weighted by measured out-of-sample log-loss. No closing "
                    "line is captured anywhere in this repo and no NBA-operated source publishes "
                    "one, so the prior weight is set to 0 and no market-blended price is "
                    "published. Inventing a closing line would be a hallucination. The weighting "
                    "machinery is in place and switches on the moment a price feed is added."),
         "source_url": GITHUB + "data/derived/horizon_picks_801ba27f.json", "status": "open"},
        {"id": "F96", "severity": "medium",
         "title": "The three official team-stat pages carry no data in an HTTP response",
         "detail": ("www.nba.com/stats/teams/traditional, /opponent and /advanced render their "
                    "tables in the browser. The raw response captured this session contains zero "
                    "team rows (no 'resultSets', two <table> elements, both date-picker "
                    "calendars). The brief asks for these pages to be re-read and the inputs "
                    "re-cut, so the same quantities were rebuilt from first principles out of "
                    "official box scores, which ARE server-rendered. Every rating therefore "
                    "traces to an official game page. The captured stat pages are committed as "
                    "evidence."),
         "source_url": STATS_ADV, "status": "open"},
        {"id": "F97", "severity": "low",
         "title": "Only 2 of the 9 games on the 2026-11-15 slate were Final at capture time",
         "detail": ("Four were still in progress and three had not tipped. Their tickets are left "
                    "PENDING and are not graded. The settlement page re-reads the official feed "
                    "and grades them as they go final; nothing is graded from a live score."),
         "source_url": "https://www.nba.com/games?date=2026-11-15", "status": "open"},
        {"id": "F98", "severity": "low",
         "title": "The injury-report index is read once; editions published after the capture are not stored",
         "detail": ("All 75 editions the official index linked for 2026-11-15 were downloaded, "
                    "hashed, stored and parsed. Editions the league publishes after the capture "
                    "run are not in the repository. The revision time and the retrieval time of "
                    "the newest stored edition are printed on the Injury PDF Ledger page."),
         "source_url": INJ_INDEX, "status": "open"},
        {"id": "F99", "severity": "low",
         "title": "Players on the injury report with no minutes this season have no measured minutes share",
         "detail": ("Rotation availability is the minutes-weighted share of a team's measured "
                    "top-8 that is not ruled out. A player who has not appeared in an official "
                    "box score this season has no measured share, so removing them changes "
                    "availability by 0.00 even when a coach would have played them. The top-8 "
                    "table shows the window each share was measured over."),
         "source_url": NBA_GAMES, "status": "open"},
    ]
    print("flagged: +%d" % add(fl["items"], "id", new_flags))
    save("flagged.json", fl)

    # --------------------------------------------------------- questions
    q = load("questions.json")
    answered = [
        {"id": "A18",
         "question": "What is the measured home-win rate, and what home-court value does it imply?",
         "answer": ("Home teams won 100 of 190 official finals from 2026-10-20 to 2026-11-15, a "
                    "rate of 0.5263. Under the empirical margin distribution (sigma 16.78) that "
                    "is 1.108 points of home court. The site now pins home court to that number "
                    "instead of fitting it: HCA = sigma_margin * Phi^-1(home_win_rate)."),
         "source": "official box scores",
         "source_url": GITHUB + "data/derived/measured_constants_2026_27.json",
         "confidence": "High for the rate (190 official finals); medium for the conversion, "
                       "which assumes the margin distribution is normal enough at the median."},
        {"id": "A19",
         "question": "Do the two estimators disagree enough for the disagreement to be a usable signal?",
         "answer": ("Yes. Across the 34 games on the 2026-11-15..18 slate the two estimators "
                    "disagree by 4.05 points on the spread on average and up to 8.8 points. "
                    "That is the same order as the edge the singles gate looks for, so it is a "
                    "real signal and not rounding noise."),
         "source": "official box scores, official schedule",
         "source_url": GITHUB + "data/derived/estimators_2026_27.json",
         "confidence": "High that the disagreement is measured; not yet established that it "
                       "predicts which estimator is right - that needs graded tickets."},
        {"id": "A20",
         "question": "Are two games on the same night correlated?",
         "answer": ("Measured, not assumed: pairing every game with every other game on the same "
                    "date across 190 official finals gives 1,546 pairs and a correlation of "
                    "0.0142 between their home margins - statistically indistinguishable from "
                    "zero. Multi-game parlays are therefore priced at essentially the naive "
                    "product, and the naive product is printed beside the rho-priced number so "
                    "the reader can see the difference."),
         "source": "official box scores",
         "source_url": GITHUB + "data/derived/rho_2026_27.json",
         "confidence": "High."},
        {"id": "A21",
         "question": "Can a player's minutes really be redistributed when a team-mate is out, from official data alone?",
         "answer": ("Yes, at the level of a measured minutes share. Minutes were summed from the "
                    "official box score of each team's last 10 completed games, giving every "
                    "player a share of team minutes. The top-8 shares and the proportional "
                    "reallocation when a player is removed are published per team. What is still "
                    "missing is who actually absorbs the minutes in a given matchup, which is a "
                    "coaching decision and cannot be read off any official page."),
         "source": "official box scores",
         "source_url": GITHUB + "data/derived/rotation_2026_27.json",
         "confidence": "High for the shares; low for the reallocation rule, which is a stated "
                       "modelling choice."},
        {"id": "A22",
         "question": "How many status changes does the official injury report actually make in a day?",
         "answer": ("On 2026-11-15 the league published 75 editions. Diffing each edition against "
                    "the one immediately before it found 28 status changes - for example T.J. "
                    "McConnell going Probable to Available at 12:15 PM ET and Andrew Nembhard "
                    "going Questionable to Out at the same minute. That is why a rotation read "
                    "built in the morning is stale by the afternoon."),
         "source": "official injury report PDFs",
         "source_url": INJ_INDEX,
         "confidence": "High - computed from the stored PDFs, not transcribed by hand."},
        {"id": "A23",
         "question": "Is the 2026-11-15 slate settled?",
         "answer": ("Partly. At capture, 2 of the 9 games were Final and both published tickets "
                    "on them won (+2.00 paper units). Four games were in progress and three had "
                    "not tipped, so their tickets are PENDING. Nothing was graded from a live "
                    "score."),
         "source": "official finals",
         "source_url": GITHUB + "data/settlement/settlement_2026-11-15.json",
         "confidence": "High."},
        {"id": "A24",
         "question": "Which teams are currently outside the luck noise band?",
         "answer": ("Luck is reported as a z-score per team from Pythagorean expectation on "
                    "official points for and against. Teams with |z| > 2.0 are outside the noise "
                    "band and the site refuses to publish a ticket that leans on them. The full "
                    "table, with each z and its band, is on the Luck z-scores page."),
         "source": "official finals",
         "source_url": GITHUB + "data/derived/luck_2026_27.json",
         "confidence": "Medium - Pythagorean exponent 13.91 is a stated modelling choice, not an "
                       "official number."},
    ]
    opened = [
        {"id": "Q24",
         "question": "Is the estimator disagreement actually predictive of error?",
         "what_is_missing": ("Graded tickets. The disagreement is measured, but nothing yet shows "
                             "that a large disagreement predicts a larger miss."),
         "how_to_answer": ("Log the disagreement for every published ticket, then regress "
                           "absolute error on disagreement once there are 100+ graded plays. "
                           "This is the single cheapest experiment available."),
         "blocks": "Whether disagreement can be used as a stake-sizing signal",
         "priority": "high",
         "source": "official finals",
         "source_url": GITHUB + "data/derived/estimators_2026_27.json"},
        {"id": "Q25",
         "question": "What is the real closing line, and how far is the model from it?",
         "what_is_missing": ("A price feed. No closing price is captured anywhere in this "
                             "repository and no NBA source publishes one, so the market-anchored "
                             "prior is switched off (F95)."),
         "how_to_answer": ("Log the closing spread, total and price for every graded play into a "
                           "new file at capture time. Until then 'units won' means model against "
                           "a naive model, not against a market."),
         "blocks": "G4/G5 market gates and the market-anchored prior",
         "priority": "highest",
         "source": "n/a - no official source exists",
         "source_url": GITHUB + "data/derived/horizon_picks_801ba27f.json"},
        {"id": "Q26",
         "question": "Do travel distance and 3-in-4 schedule spots move a line at all?",
         "what_is_missing": ("Both columns are now computed and published, but no test has been "
                             "run against them. Travel is additionally flagged because the "
                             "coordinates are not official (F94)."),
         "how_to_answer": ("Regress the model's margin and total error on rest days, back-to-back, "
                           "3-in-4 and travel miles over 190 official finals, and publish the "
                           "coefficients with standard errors before any of them is applied."),
         "blocks": "Whether schedule and travel belong in the line at all",
         "priority": "medium",
         "source": "official schedule and finals",
         "source_url": NBA_SCHEDULE},
        {"id": "Q27",
         "question": "Are the measured player-prop correlations stable?",
         "what_is_missing": ("Sample. The team-mate correlation is measured on 374 pairs and the "
                             "opponent correlation on 187 - enough to publish with a caveat, not "
                             "enough to price on."),
         "how_to_answer": ("Re-measure at the end of every month and publish the series, so a "
                           "reader can see whether it is converging or drifting."),
         "blocks": "Confident same-game-parlay pricing",
         "priority": "medium",
         "source": "official game logs",
         "source_url": GITHUB + "data/derived/rho_2026_27.json"},
        {"id": "Q28",
         "question": "Should the model inputs come from the official stats pages or from rebuilt box scores?",
         "what_is_missing": ("The stats pages carry no data in an HTTP response (F96), so this "
                             "session rebuilt the ratings from official box scores. That is a "
                             "substantial architectural choice, not a detail."),
         "how_to_answer": ("Decide explicitly: either add a headless browser to the refresh job so "
                           "the stats pages can be read as a human sees them, or keep the box-score "
                           "rebuild as the official path and document it as such. Both are "
                           "defensible; silently straddling them is not."),
         "blocks": "What the scheduled refresh job is allowed to rebuild from",
         "priority": "high",
         "source": "official stats pages and box scores",
         "source_url": STATS_ADV},
        {"id": "Q29",
         "question": "How should an in-progress slate be presented without tempting anyone to act on a live score?",
         "what_is_missing": ("A rule. On 2026-11-15 six of nine games were live or finished while "
                             "the horizon page still listed them."),
         "how_to_answer": ("Split the horizon page by official game status and grey out anything "
                           "that has tipped, or drop tipped games from the horizon entirely once "
                           "the day rolls over. The projection/bet split makes this cheap."),
         "blocks": "Whether the horizon page can be trusted at a glance in the evening",
         "priority": "medium",
         "source": "official games pages",
         "source_url": NBA_GAMES},
        {"id": "Q30",
         "question": "Does the repository need a retention rule for raw captures?",
         "what_is_missing": ("A policy. This session added 22 MB of gzipped official HTML and "
                             "7.5 MB of injury PDFs. That is fine today and will not be fine by "
                             "the All-Star break."),
         "how_to_answer": ("Keep the extracted JSON and the manifest digests in git, move the raw "
                           "bytes to build artifacts, and keep raw HTML only for the current "
                           "horizon. Document it in the repo before the next session adds more."),
         "blocks": "Repository size and Pages deploy time",
         "priority": "low",
         "source": "n/a - engineering policy",
         "source_url": GITHUB + "COORDINATION.md"},
    ]
    print("questions: +%d answered, +%d open"
          % (add(q["answered"], "id", answered), add(q["open"], "id", opened)))
    save("questions.json", q)

    # ------------------------------------------------------- suggestions
    s = load("suggestions.json")
    items = [
        {"id": "SG32",
         "title": "Make the estimator disagreement a stake-sizing signal, not just a headline",
         "category": "Model",
         "problem": ("The disagreement between the two estimators is published as the headline "
                     "confidence signal, but nothing uses it: every ticket is still printed at "
                     "the same paper unit."),
         "options": [
             {"option": "Leave it as a display-only signal",
              "effort": "none",
              "risk": "none",
              "unlocks": "nothing new"},
             {"option": "Scale stake by 1 / (1 + disagreement)",
              "effort": "low - one function in the picks builder",
              "risk": "medium - it is an untested assumption until Q24 is answered",
              "unlocks": "a principled reason to bet less when the model is unsure"},
             {"option": "Suppress any ticket whose disagreement exceeds a threshold",
              "effort": "low",
              "risk": "low - it can only remove tickets",
              "unlocks": "fewer, better-defined plays; directly answers Q24"}],
         "recommendation": ("Do the threshold first. It needs no statistical justification to be "
                            "safe, and it produces the data that answers whether the "
                            "disagreement is predictive at all."),
         "decision_needed": "Which of the three, and what threshold",
         "source": GITHUB + "data/derived/estimators_2026_27.json"},
        {"id": "SG33",
         "title": "Add a price feed so the market gates can run",
         "category": "Data",
         "problem": ("G4 and G5 are blocked and the market-anchored prior is switched off (F95) "
                     "because no closing price exists anywhere in the repository. Everything the "
                     "site calls 'units' is model against a naive model."),
         "options": [
             {"option": "Log closing prices by hand at capture time",
              "effort": "medium, and it does not scale",
              "risk": "transcription error",
              "unlocks": "G4, G5 and the market-anchored prior"},
             {"option": "Add a licensed or public odds source to the allowlist and capture it in the refresh job",
              "effort": "medium",
              "risk": "the source is not NBA-operated, so it has to be labelled as non-official",
              "unlocks": "everything above, automatically"},
             {"option": "Do nothing and rename 'units' to 'model points' throughout",
              "effort": "low",
              "risk": "none",
              "unlocks": "honesty about what is being measured"}],
         "recommendation": ("Option 3 immediately, whatever else is chosen: the current wording "
                            "invites a misreading. Then option 2."),
         "decision_needed": "Whether a non-NBA price source may enter the allowlist",
         "source": GITHUB + "data/derived/horizon_picks_801ba27f.json"},
        {"id": "SG34",
         "title": "Decide the official input path: stats pages or rebuilt box scores",
         "category": "Architecture",
         "problem": ("www.nba.com/stats carries no data in a plain HTTP response (F96). This "
                     "session rebuilt the ratings from official box scores instead, which works "
                     "and is fully traceable, but it is a different source from the one the "
                     "brief names."),
         "options": [
             {"option": "Add a headless browser to the refresh job and read the stats pages as a human sees them",
              "effort": "high",
              "risk": "fragile; the pages change layout without notice",
              "unlocks": "the exact source the brief names"},
             {"option": "Adopt the box-score rebuild as the official path and document it",
              "effort": "low - it is already built and passing every gate",
              "risk": "it will not match a reader checking nba.com/stats by eye",
              "unlocks": "a stable, cheap, fully traceable input path"},
             {"option": "Run both and publish their disagreement",
              "effort": "high",
              "risk": "two sources of truth",
              "unlocks": "a third, independent disagreement signal"}],
         "recommendation": "Option 2 now, with the caveat printed next to every rating.",
         "decision_needed": "Which path is official",
         "source": STATS_ADV},
        {"id": "SG35",
         "title": "Give the injury pipeline a live polling mode",
         "category": "Data",
         "problem": ("The league published 75 editions on 2026-11-15 and 28 of the consecutive "
                    "diffs changed a player's status. A rotation read built in the morning is "
                    "stale by the afternoon, and the pipeline currently only stores what one "
                    "capture run saw."),
         "options": [
             {"option": "Poll the index every 15 minutes and store any new edition",
              "effort": "low - the fetcher and the differ already exist",
              "risk": "storage growth (see SG37)",
              "unlocks": "a rotation read that is current at tip"},
             {"option": "Poll only on game days between 11:00 and 20:00 ET",
              "effort": "low",
              "risk": "misses late scratches on non-game days",
              "unlocks": "most of the value at a fraction of the storage"}],
         "recommendation": "Option 2, with the newest-edition banner on the Injuries page.",
         "decision_needed": "Polling cadence and retention",
         "source": INJ_INDEX},
        {"id": "SG36",
         "title": "Split the horizon page by official game status",
         "category": "Site",
         "problem": ("On 2026-11-15 six of the nine games on the horizon page had already tipped "
                     "while the page still listed them as picks (Q29)."),
         "options": [
             {"option": "Grey out any game the official page says has started",
              "effort": "low",
              "risk": "none",
              "unlocks": "an honest page at any hour"},
             {"option": "Drop tipped games from the horizon once the day rolls over",
              "effort": "low",
              "risk": "the page changes shape during the evening",
              "unlocks": "a page that is always actionable"}],
         "recommendation": "Both: grey out immediately, drop at the daily roll.",
         "decision_needed": "Which, and at what hour the day rolls",
         "source": NBA_GAMES},
        {"id": "SG37",
         "title": "Set a retention rule for raw captures before the repository outgrows git",
         "category": "Engineering",
         "problem": ("This session added 22 MB of gzipped official HTML and 7.5 MB of injury "
                     "PDFs. Extracted JSON plus a manifest digest is a few hundred kilobytes for "
                     "the same information."),
         "options": [
             {"option": "Keep extracted JSON and manifests in git; move raw bytes to build artifacts",
              "effort": "medium",
              "risk": "the raw bytes are then only as durable as GitHub's artifact retention",
              "unlocks": "a repository that stays small"},
             {"option": "Keep raw HTML for the current horizon only and prune the rest",
              "effort": "low",
              "risk": "historical captures cannot be re-parsed",
              "unlocks": "most of the saving for the least change"}],
         "recommendation": "Option 2 now, option 1 when the repo passes 100 MB.",
         "decision_needed": "Retention window",
         "source": GITHUB + "COORDINATION.md"},
        {"id": "SG38",
         "title": "Publish a requirements-coverage matrix so the brief can be audited line by line",
         "category": "Site",
         "problem": ("The brief contains twenty specific modelling instructions. A reader "
                     "currently has to read the whole site to work out which are done."),
         "options": [
             {"option": "One page, one row per requirement, with status and a link to the evidence",
              "effort": "low",
              "risk": "it goes stale unless it is regenerated",
              "unlocks": "an auditable answer to 'is it done?'"},
             {"option": "Fold it into the executive summary",
              "effort": "low",
              "risk": "it gets lost in prose",
              "unlocks": "the same answer, less visibly"}],
         "recommendation": "Option 1, regenerated by the build so it cannot drift.",
         "decision_needed": "Whether it blocks the merge",
         "source": GITHUB + "COORDINATION.md"},
    ]
    print("suggestions: +%d" % add(s["items"], "id", items))
    save("suggestions.json", s)

    # -------------------------------------------------- executive summary
    ex = load("executive.json")
    ex["as_of"] = "2026-11-15"
    ex["headline"] = ("The rolling window is 2026-11-15 to 2026-11-18: 34 games on the official "
                      "schedule, 28 of which had not tipped at publication. Behind them sit 190 "
                      "official finals, re-read line by line from NBA.com box scores.")
    ex["lead"] = ("This session re-cut the model inputs from first principles. The three official "
                  "team-stat pages render their tables in the browser and carry no data in an "
                  "HTTP response, so possessions, offensive and defensive rating and pace were "
                  "rebuilt out of official box scores for all 190 completed games of the season "
                  "instead - every number traceable to an official game page. Home court is now "
                  "pinned to the measured home-win rate (0.5263 over 190 finals, 1.108 points) "
                  "rather than fitted. Two genuinely independent estimators are published with "
                  "their disagreement as the headline; they disagree by 4.05 points on the spread "
                  "on average. The 2026-11-15 slate is partly settled from official finals: two "
                  "games were Final and both published tickets won, the other seven are PENDING.")
    ex["verdict"] = {
        "status": "PROVISIONAL - not funded",
        "one_line": ("The model is now built entirely on values read from official pages, but no "
                     "strategy has passed the validation gates and no market price exists "
                     "anywhere in the repository, so nothing here is a betting recommendation."),
        "why": ("Every gate that can run has been run and none has passed. The gates that cannot "
                "run - the two that need a closing price - are blocked on data nobody in this "
                "project has. Publishing the block rather than the number is the whole point.")
    }
    ex["findings"] = [
        {"n": 1,
         "title": "Home court is measured, not fitted: 0.5263 over 190 official finals",
         "detail": ("Home teams won 100 of 190 official finals from 2026-10-20 to 2026-11-15. "
                    "Converted through the empirical margin distribution (sigma 16.78) that is "
                    "1.108 points, and that is the number every line now uses. An earlier build "
                    "fitted home court freely and got 3.51 points with a standard error of 2.28 "
                    "- a number the data cannot support."),
         "reading": "The pinned value is smaller and honest. It is not a tweak; it removes a "
                    "free parameter that was soaking up noise."},
        {"n": 2,
         "title": "The two estimators disagree by 4.05 points on the spread on average",
         "detail": ("Estimator 1 builds the line from possessions and points per possession. "
                    "Estimator 2 uses a completely different information set: a least-squares "
                    "power rating solved from official final margins, and the teams' own scored "
                    "and allowed rates. Across the 34 games on the slate they disagree by 4.05 "
                    "points on the spread on average and up to 8.8."),
         "reading": "The disagreement is the headline number on the projection page. The 50/50 "
                    "blend sits underneath it and is never the headline."},
        {"n": 3,
         "title": "Two independent estimators are only useful if they are actually independent",
         "detail": ("The first attempt at a second estimator reused the same efficiency ratings "
                    "with different arithmetic and disagreed by 0.1 to 0.2 points - noise dressed "
                    "up as a signal. It was replaced with a margin-based power rating on a "
                    "different information set."),
         "reading": "A disagreement that is smaller than the rounding is not a confidence signal. "
                    "This is worth checking on any future estimator added to the site."},
        {"n": 4,
         "title": "The official injury report changed 28 times in one day",
         "detail": ("The league published 75 editions on 2026-11-15. Every one was downloaded, "
                    "hashed, stored and parsed, and each was diffed against the edition "
                    "immediately before it. Twenty-eight status changes were found, including "
                    "T.J. McConnell Probable to Available at 12:15 PM ET and Andrew Nembhard "
                    "Questionable to Out in the same minute."),
         "reading": "Any rotation read older than a few hours is stale. The banner on the Injury "
                    "PDF Ledger page prints the revision time and the retrieval time so the "
                    "reader can see exactly how old it is."},
        {"n": 5,
         "title": "Travel is computed and flagged, not quietly used",
         "detail": ("Arena names, cities and states are official - they are printed on the box "
                    "score of a game played there. Latitude and longitude are not published by "
                    "any NBA page, so the great-circle distances are derived and flagged (F94). "
                    "No travel value moves a line."),
         "reading": "Rest, back-to-back and 3-in-4 are computed from the official schedule and "
                    "are solid. Travel is a candidate input awaiting a source."},
        {"n": 6,
         "title": "The market-anchored prior remains switched off, and that is a finding",
         "detail": ("The brief asks for the model line to be blended with the closing line, "
                    "weighted by measured out-of-sample log-loss. No closing line exists anywhere "
                    "in this repository and no NBA-operated source publishes one, so the weight "
                    "is 0 and no blended price is published (F95)."),
         "reading": "This is the single change that would unlock the most: two validation gates "
                    "and the prior are all blocked on the same missing input."},
    ] + ex["findings"]
    ex["what_is_live_now"] = [
        "Official result feed: 222 games captured, 190 Final, quarter scores summing to the "
        "final on every one.",
        "Ratings rebuilt from official box scores for all 30 teams (pace, offensive rating, "
        "defensive rating, net rating).",
        "Two estimators with their disagreement, for all 34 games on the 2026-11-15..18 slate.",
        "Projection surface and bet surface as separate pages - they are never merged.",
        "Parlays priced with measured rho, the naive independent product printed beside them.",
        "Minutes redistribution: measured top-8 shares per team with a worked replacement.",
        "Rest, back-to-back, 3-in-4 and travel for every horizon game.",
        "Luck z-scores for all 30 teams with the refusal rule applied.",
        "75 official injury PDFs stored with revision and retrieval times, 28 status changes "
        "detected.",
        "Ledger: hash-chained, extended with the 11/15 settlement and this publication.",
    ]
    ex["recommended_next_actions"] = [
        {"rank": 1,
         "action": "Log a closing price for every graded play. It is the only missing input that "
                   "blocks two validation gates and the market-anchored prior (F95, Q25).",
         "why": "Until it exists, 'units won' measures the model against a naive model."},
        {"rank": 2,
         "action": "Decide whether the official input path is the stats pages or the box-score "
                   "rebuild (F96, Q28).",
         "why": "Two sources of truth is worse than either one chosen deliberately."},
        {"rank": 3,
         "action": "Test whether the estimator disagreement predicts error, then either use it "
                   "for stake sizing or drop it (Q24).",
         "why": "It is currently the headline number on the projection page and nothing has "
                "shown it means anything."},
        {"rank": 4,
         "action": "Regress error on rest, back-to-back, 3-in-4 and travel before any of them "
                   "enters the line (Q26).",
         "why": "All four are computed and published; none is yet justified."},
        {"rank": 5,
         "action": "Set a retention rule for raw captures (Q30, SG37).",
         "why": "22 MB of HTML and 7.5 MB of PDFs were added today and the season is young."},
    ]
    ex["bottom_line"] = ("Everything on this site is now derived from an official page or flagged "
                         "as not being. That is a real change from the position a day ago, when "
                         "the scheduled refresh had never once executed against nba.com. What it "
                         "buys is trust in the inputs, not trust in the edge: no strategy has "
                         "passed the gates, there is no market price to beat, and the honest "
                         "statement of the current position is that the machinery is sound and "
                         "the edge is unproven.")
    save("executive.json", ex)
    print("executive.json updated to as_of", ex["as_of"])


if __name__ == "__main__":
    main()
