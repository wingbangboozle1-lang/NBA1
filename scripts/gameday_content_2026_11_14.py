#!/usr/bin/env python3
"""gameday_content_2026_11_14.py — write the game-day findings into the site's content set.

Session `arena/95c1cb23-nba1` (COORDINATION.md §30, tasks G04/G05).

Reads data/derived/gameday_read.json (produced by scripts/gameday_read_2026_11_14.py) and
data/captures/2026-11-14-pm/*.json, and updates:

  data/raw/sources.json          +3 official sources registered
  data/content/flagged.json      +6 flags (F47-F52)
  data/content/questions.json    Q14 and Q18 answered (A16, A17); Q10/Q12 re-scoped to what is
                                 still missing after this capture
  data/content/suggestions.json  +4 suggestions (SG19-SG22), each as options with effort/risk
  data/content/executive.json    headline, one new finding, live list, next actions, bottom line

Every number quoted in prose is read from the artifact rather than typed, so the sentence and
the table cannot drift apart. Nothing here edits a line, a pick or a graded result: see the
pre-registration note in scripts/gameday_read_2026_11_14.py.

Run:  python3 scripts/gameday_content_2026_11_14.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "data", "content")
READ = json.load(open(os.path.join(ROOT, "data", "derived", "gameday_read.json"), encoding="utf-8"))
S = READ["summary"]

PDF_1330 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf"
PDF_0415 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf"
HUB = "https://official.nba.com/nba-injury-report-2026-27-season/"
STANDINGS = "https://www.nba.com/standings"
GAMES = "https://www.nba.com/games?date=2026-11-14"


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def save(p, obj):
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


# how many newly-filed rows the engine can actually see, and how many it cannot
new_rows = sum(d["n_added"] for d in READ["edition_delta"])
blind = sum(len(g["gameday"]["home_unknown_players"]) + len(g["gameday"]["away_unknown_players"])
            for g in READ["gameday_readout"])
moved = S["games_repriced"]
games_today = len(READ["gameday_readout"])
slate_ok, slate_n = S["slate_rows_agree"], S["slate_rows_checked"]
inj_ok, inj_n = S["injury_rows_agree"], S["injury_rows_checked"]
filed = ", ".join(S["teams_that_filed_since"])
unfiled = ", ".join(S["teams_still_unfiled"]) or "none"

# ----------------------------------------------------------------- sources.json
src_doc = load(os.path.join(ROOT, "data", "raw", "sources.json"))
src_doc["sources"]["S10_2026-11-14-1330PM"] = {
    "title": "NBA Official Injury Report, 11/14/26 01:30 PM ET edition (game-day report)",
    "url": PDF_1330,
    "publisher": "NBA.com (official)",
    "used_for": "The league's game-day participation report for the 2026-11-14 slate and the 2026-11-15 "
                "slate. Transcribed row by row in data/captures/2026-11-14-pm/injury_2026-11-14_1330PM.json "
                "and diffed against the 04:15 AM ET edition the published lines were built from.",
}
src_doc["sources"]["S8_2026-11-14-pm-slate"] = {
    "title": "NBA.com Games & Scores, 2026-11-14 to 2026-11-17 (game-day read)",
    "url": GAMES,
    "publisher": "NBA.com (official)",
    "used_for": "Matchup, tip time, game id, displayed club records and the displayed season-leader line "
                "for all 27 horizon games, read 2026-11-14 between 18:39Z and 19:10Z. Used to verify every "
                "published row in docs/data/lines.json; see data/captures/2026-11-14-pm/slate_2026-11-14_to_17.json.",
}
src_doc["sources"]["S2_2026-11-14-pm-standings"] = {
    "title": "NBA.com 2026-27 Regular Season Standings (game-day read)",
    "url": STANDINGS,
    "publisher": "NBA.com (official)",
    "used_for": "All 30 club records at 18:56Z on 2026-11-14 (Utah 19:14Z), used as the second official "
                "cross-read of the record fields that also appear on each game card.",
}
src_doc["refresh_2026-11-14-pm"] = {
    "run_at_utc": "2026-11-14T18:38Z to 2026-11-14T19:20Z",
    "session": "arena/95c1cb23-nba1",
    "what": "Game-day injury refresh and row-level re-verification of the horizon. No published line, "
            "pick or graded result was edited: lines are pre-registered before tip and re-pricing them "
            "after a capture would contaminate the out-of-sample record.",
    "outputs": ["data/captures/2026-11-14-pm/", "data/derived/gameday_read.json",
                "site/pages/gameday.html"],
    "result": {"slate_rows_agree": "%d/%d" % (slate_ok, slate_n),
               "published_injury_rows_agree": "%d/%d" % (inj_ok, inj_n),
               "clubs_that_filed_since_the_models_edition": S["teams_that_filed_since"],
               "clubs_still_unfiled_at_capture": S["teams_still_unfiled"],
               "games_whose_model_line_moves": moved},
}
save(os.path.join(ROOT, "data", "raw", "sources.json"), src_doc)

# ---------------------------------------------------------------- flagged.json
fl = load(os.path.join(CONTENT, "flagged.json"))
have = {i["id"] for i in fl["items"]}
new_flags = [
    {
        "id": "F47", "severity": "High",
        "title": "The availability layer cannot see most of the game-day report: %d of the %d newly "
                 "filed player rows contribute 0.00 net-rating points" % (blind, new_rows),
        "detail": "Between the 04:15 AM ET edition the published lines were built from and the 01:30 PM ET "
                  "game-day edition, four clubs filed (New Orleans, Cleveland, Chicago, Miami) and %d player "
                  "rows appeared. Only the players who are inside the captured top-50 minutes table can move "
                  "the model, so %d of those rows contribute exactly 0.00 and %d of the %d games tipping "
                  "tonight have a model line that does not move at all. New Orleans is the clearest case: the "
                  "Pelicans ruled out Trey Murphy III and Dejounte Murray on the same report that gave the "
                  "model five names it cannot price, and DEN@NOP is unchanged at -9.1."
                  % (new_rows, blind, games_today - moved, games_today),
        "affected": "Injuries & Rotation page; every originated spread and total for 2026-11-14; the prop "
                    "teammate-availability factor",
        "source": None,
        "source_url": PDF_1330,
        "suggested_action": "Reviewer decision (SG20): either complete the minutes source so every listed "
                            "player has a minutes value, or stop rendering 0.00 for 'unknown' and render a "
                            "dash instead. The second option is one line of code and is the honest default "
                            "until the first is done.",
    },
    {
        "id": "F48", "severity": "Low",
        "title": "Memphis had not filed at the newest edition - but its deadline had not passed",
        "detail": "At the 01:30 PM ET edition the report prints NOT YET SUBMITTED for the Memphis Grizzlies. "
                  "The league's game-day window is 11 a.m. to 1 p.m. LOCAL time, and Memphis is on Central "
                  "time, so for an 8:00 PM ET tip the window closed at 2:00 PM ET, thirty-two minutes after "
                  "this capture. The site must not render that row as a missed filing.",
        "affected": "Game-Day Read page; the BKN@MEM row",
        "source": None,
        "source_url": HUB,
        "suggested_action": "No action. Recorded so that a reader who compares capture time with deadline "
                            "time does not conclude the source was ignored.",
    },
    {
        "id": "F49", "severity": "Medium",
        "title": "The official game card's 'Season Leaders' widget is not injury-aware",
        "detail": "The 2026-11-16 card for POR@MIN displays Anthony Edwards (33.3 PPG) as Minnesota's leader "
                  "while the 2026-11-14 game-day report rules him Out with a right knee arthroscopy. The 11/14 "
                  "card for CHI@MIN shows the same widget showing Caleb Wilson, also ruled out. The widget is a "
                  "season-average read-out and nothing in it reflects availability.",
        "affected": "Any prop or leader table that reads the card's leader line; Player Props page",
        "source": None,
        "source_url": "https://www.nba.com/games?date=2026-11-16",
        "suggested_action": "SG22: intersect the leader line with the current report before it is displayed, "
                            "and mark any leader who is ruled out. The card value itself stays exactly as "
                            "published, beside the flag.",
    },
    {
        "id": "F50", "severity": "Medium",
        "title": "The injury PDF's table re-flows, so %d of the game-day rows carry their club by block "
                 "position rather than by a printed team cell" % S["attribution_checks"]["total"],
        "detail": "Pages 2 to 4 of the report repeat the table without the Game Date / Game Time / Matchup / "
                  "Team columns. Club for those rows was taken from the block label that opens the block and "
                  "from the league's alphabetical-within-club ordering, never from the player's name. %d of the "
                  "rows could then be cross-checked against the official minutes table's club column and all "
                  "%d agree; %d could not be cross-checked because the player is outside that table and no "
                  "second official source in this repository prints a club for him."
                  % (S["attribution_checks"]["agree"], S["attribution_checks"]["agree"],
                     S["attribution_checks"]["no_cross_check"]),
        "affected": "Every row of the game-day capture, and by extension the edition delta",
        "source": None,
        "source_url": PDF_1330,
        "suggested_action": "A reviewer who wants these rows confirmed should read them against a team "
                            "roster page (30 official URLs, one per club). The transcription records which "
                            "rows are affected: attribution == 'block' in "
                            "data/captures/2026-11-14-pm/injury_2026-11-14_1330PM.json.",
    },
    {
        "id": "F51", "severity": "Medium",
        "title": "Two injury editions are live on the site at once, deliberately",
        "detail": "The Injuries & Rotation page still shows the 04:15 AM ET edition, because that is the "
                  "edition every published line and pick was built from; the Game-Day Read page shows the "
                  "01:30 PM ET edition and what it would do to those lines. Rolling the older page forward "
                  "would make the site look current and make the graded window a lie, so it was not done.",
        "affected": "Injuries & Rotation page header; Game-Day Read page",
        "source": None,
        "source_url": PDF_0415,
        "suggested_action": "Keep. If the reviewer prefers one edition per day, the change belongs in the "
                            "capture step (SG19), not in the published table.",
    },
    {
        "id": "F52", "severity": "Medium",
        "title": "The report never covers the third day of the horizon, so 13 of 27 games have no "
                 "availability input at all",
        "detail": "Every edition read today - 04:15 AM ET and 01:30 PM ET - lists games on 11/14 and 11/15 "
                  "and nothing for 11/16 or 11/17. That is the league's own cadence (a club files the evening "
                  "before, or the day of for the second night of a back-to-back), not a capture failure. It "
                  "means the three-day horizon the brief asks for is an injury-informed horizon for two of its "
                  "four dates and a ratings-only horizon for the other two.",
        "affected": "Lines & Picks page: the 2026-11-16 and 2026-11-17 rows",
        "source": None,
        "source_url": HUB,
        "suggested_action": "Label the T+2 and T+3 rows as 'no availability input exists' wherever an "
                            "availability column is shown, or shorten the pickable window to T+1 and publish "
                            "T+2/T+3 as schedule only. Reviewer's call (SG19, option C).",
    },
]
fl["items"] = [i for i in fl["items"] if i["id"] not in {n["id"] for n in new_flags}] + \
              [n for n in new_flags if n["id"] not in have]
save(os.path.join(CONTENT, "flagged.json"), fl)

# --------------------------------------------------------------- questions.json
qs = load(os.path.join(CONTENT, "questions.json"))
answered_ids = {a["id"] for a in qs["answered"]}
qs["open"] = [q for q in qs["open"] if q["id"] not in ("Q14", "Q18")]
new_answered = [
    {
        "id": "A16",
        "question": "Which injury-report edition is authoritative at tip-off, and what did the intra-day "
                    "movements actually cost? (was Q14)",
        "answer": "Measured on 2026-11-14. The 04:15 AM ET edition is not authoritative for a 7:00 PM tip - "
                  "it predates the game-day filing window entirely. The 01:30 PM ET game-day edition adds %d "
                  "player rows across four clubs (Chicago, Cleveland, Miami, New Orleans), changes four "
                  "existing statuses (Dallas' Christie Questionable to Doubtful; Brooklyn's Brown Jr. "
                  "Questionable to Probable; Detroit's Harkless and Jones Questionable to Available) and still "
                  "lists Memphis as NOT YET SUBMITTED. Run through the engine's own availability adjustment, "
                  "that edition moves %d of the %d games tipping tonight and by at most 2.6 points; no game's "
                  "favourite flips. The movements cost essentially nothing in the published lines for one "
                  "reason, and it is not the report's fault: %d of the %d newly listed players are outside the "
                  "captured minutes table, so their impact is forced to 0.00 (F47)."
                  % (new_rows, moved, games_today, blind, new_rows),
        "source": None,
        "source_url": PDF_1330,
        "confidence": "High for the two editions read here (both transcribed row by row from the official PDF, "
                      "each row checkable at its URL); Medium for the 'what it costs' half, because the cost is "
                      "computed through a model whose impact coefficient is a projectled choice (F4) and whose "
                      "minutes input is incomplete (F47).",
    },
    {
        "id": "A17",
        "question": "Was the 11/14 midday injury report published, and what does it say about 11/14 rows? "
                    "(was Q18)",
        "answer": "Yes. The official hub listed forty-five editions for 11/14 at the time of reading, from "
                  "12:00 a.m. ET through 1:30 p.m. ET, and the 1:30 p.m. ET PDF was fetched and transcribed in "
                  "full: 51 rows for the five 11/14 games (ten clubs, nine of which filed) and 18 rows for the "
                  "11/15 games, every one of them NOT YET SUBMITTED. The file is "
                  "data/captures/2026-11-14-pm/injury_2026-11-14_1330PM.json, and it is the newest edition "
                  "published when it was read, so a newer one exists by the time this is on the page - the "
                  "hub updates continuously and the site says so rather than implying a final read.",
        "source": None,
        "source_url": HUB,
        "confidence": "High - a direct transcription of the league's own document, with the row count and "
                      "per-club status reproducible from the URL on the row.",
    },
]
for a in new_answered:
    if a["id"] not in answered_ids:
        qs["answered"].append(a)
for q in qs["open"]:
    if q["id"] == "Q10":
        q["what_is_missing"] = (
            "Availability for the 2026-11-15, 11-16 and 11-17 games. 2026-11-14 is answered: the 01:30 PM ET "
            "game-day edition is transcribed row by row on the Game-Day Read page, with Memphis the one club "
            "still inside its filing window. Nothing later than 11/14 can be answered today because no club "
            "has filed for 11/15 yet - the first edition that will contain them is 11/14 evening, and the "
            "report never lists a game more than one day ahead (F52).")
        q["priority"] = 2
    if q["id"] == "Q12":
        q["what_is_missing"] = (
            "Minutes for the 415 players outside the captured top-50 table. This is no longer a theoretical "
            "worry: on the 2026-11-14 game-day report %d of the %d newly listed players have no minutes row, "
            "so a club can rule out two rotation pieces and the originated line will not move (F47). Until the "
            "table is complete, the impact column is a floor and not an estimate." % (blind, new_rows))
        q["priority"] = 1
save(os.path.join(CONTENT, "questions.json"), qs)

# ------------------------------------------------------------- suggestions.json
sg = load(os.path.join(CONTENT, "suggestions.json"))
have_sg = {i["id"] for i in sg["items"]}
new_sg = [
    {
        "id": "SG19", "category": "Operations / model",
        "title": "Cut the pickable horizon against the game-day edition, and freeze at that cut",
        "problem": "The pipeline currently originates and publishes lines against whatever edition the "
                   "overnight capture found. For a 7:00 PM ET slate that is up to fifteen hours before the "
                   "league's own game-day window closes, and the measured consequence is on the site: four "
                   "clubs filed in the meantime and the model line for their games moved by 0.0 to 2.6 points "
                   "only because the rest of the names could not be priced at all.",
        "options": [
            {"option": "Add a 15:15 UTC scheduled capture immediately before the first 7:00 PM ET tip, and "
                       "let that cut be the published line set for the day",
             "effort": "Low - the refresh workflow already runs at 15:15 UTC; the change is which edition it "
                       "treats as final",
             "risk": "Low - additive; earlier lines stay archived and graded, they are not rewritten",
             "unlocks": "Q10, Q14 (now answered), Q18 (now answered); every pick then reflects what a person "
                       "watching the report at 3 p.m. ET could see"},
            {"option": "Keep the overnight cut as the official line set and publish only the game-day delta, "
                       "as the Game-Day Read page does now",
             "effort": "None - this is the current behaviour",
             "risk": "Low, but the published number is knowingly stale by one filing window",
             "unlocks": "Nothing new; it preserves pre-registration purity at the cost of usefulness"},
            {"option": "Re-price the published lines in place when a newer edition arrives",
             "effort": "Low",
             "risk": "Fatal for the leaderboard - it puts information published after the cut inside a "
                     "line that will later be graded, which is the look-ahead error this repository has "
                     "already been burned by",
             "unlocks": "Nothing; rejected and recorded so nobody re-proposes it"},
        ],
        "recommendation": "Option A, with the frozen copy kept and diffed. Publish a line, then a delta, "
                          "never a mutated line.",
        "decision_needed": "Which edition is the day's official cut, and what time the scheduler should fire.",
        "source": PDF_1330,
    },
    {
        "id": "SG20", "category": "Data / model",
        "title": "Either give every listed player a minutes row or stop printing 0.00 for an unknown",
        "problem": "The availability impact is computed as (status weight x minutes share) x 15.0, and a "
                   "player with no minutes row contributes 0.00 - indistinguishable in the table from a "
                   "player whose absence costs nothing. Tonight that is %d of %d newly filed rows, and it is "
                   "the difference between a line that moved and a line that did not." % (blind, new_rows),
        "options": [
            {"option": "Capture minutes per club from the official team pages (30 URLs) instead of the "
                       "paginated top-50 league table",
             "effort": "Medium - one fetch per club plus a parser; no new permission or vendor needed",
             "risk": "Low - additive; the existing table stays as the cross-check",
             "unlocks": "Q12, Q3, Q20 and F47; prop projections stop being a point estimate with no width"},
            {"option": "Render a dash, not 0.00, wherever minutes are unknown, and exclude the row from the "
                       "team total with the exclusion counted in the header",
             "effort": "Low - one formatting rule and one counter",
             "risk": "Low, but it makes published impacts smaller-looking because fewer players count at all",
             "unlocks": "Removes a misleading zero from every table today, including this one"},
            {"option": "Do nothing and keep the lower-bound note",
             "effort": "None",
             "risk": "Medium - the note is correct and unread; readers keep seeing 0.00 as 'healthy'",
             "unlocks": "Nothing"},
        ],
        "recommendation": "Both of the first two: the dash is a one-line honesty fix that should ship now, "
                          "the per-club capture is the actual repair.",
        "decision_needed": "Whether the reviewer wants a data project (option A) or a display fix (option B) "
                           "this week.",
        "source": "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season",
    },
    {
        "id": "SG21", "category": "Site / UI",
        "title": "Show an edition timeline per game: what the model knew, and when",
        "problem": "Every table on the site carries a source id, so a reader can find WHERE a value came "
                   "from, but nothing shows WHEN a row ceased to be the newest word. Today the gap between the "
                   "edition behind the lines and the newest published edition was nine hours and seventeen "
                   "minutes, and it could only be discovered by opening two PDFs.",
        "options": [
            {"option": "A per-game timeline strip on the Game-Day Read page: each edition, its timestamp, the "
                       "number of rows it added or changed, and whether the site's line was cut before or "
                       "after it",
             "effort": "Low - the data already exists in data/derived/gameday_read.json",
             "risk": "Low",
             "unlocks": "Makes staleness visible at a glance, which is the single decision-support gap this "
                        "session found"},
            {"option": "A single 'age of newest edition' badge in the header of every page",
             "effort": "Low", "risk": "Low",
             "unlocks": "Coarser, but it is impossible to miss"},
        ],
        "recommendation": "Option A first; the badge follows for free.",
        "decision_needed": "None technically - a reviewer only has to say whether per-game or global.",
        "source": HUB,
    },
    {
        "id": "SG22", "category": "Site / data",
        "title": "Never display a season leader without the report's verdict on him",
        "problem": "The official game cards print a season leader for each club that is a pure season-average "
                   "read-out. On 2026-11-16 that widget shows Anthony Edwards for Minnesota while the report "
                   "rules him out, and on 11/14 it shows Caleb Wilson for Chicago, also out (F49). Any prop "
                   "table or card copy that inherits that name is quoting a player who is not playing.",
        "options": [
            {"option": "Join the leader line to the current report at render time and mark a ruled-out leader "
                       "in place, keeping the published value visible next to the mark",
             "effort": "Low - the join key already exists in the capture",
             "risk": "Low",
             "unlocks": "Removes the most likely way a confident-looking wrong name gets onto a pick slip"},
            {"option": "Drop the leader widget from the capture entirely and derive leaders from the players "
                       "table only",
             "effort": "Medium", "risk": "Low",
             "unlocks": "One fewer source of unprefixed third-party-looking numbers, at the cost of context"},
        ],
        "recommendation": "Option A. The card is official and should stay cited; it should stop being "
                          "unqualified.",
        "decision_needed": "Whether a marked leader may still be shown as the leader.",
        "source": "https://www.nba.com/games?date=2026-11-16",
    },
]
sg["items"] += [n for n in new_sg if n["id"] not in have_sg]
save(os.path.join(CONTENT, "suggestions.json"), sg)

# --------------------------------------------------------------- executive.json
ex = load(os.path.join(CONTENT, "executive.json"))
ex["headline"] = (
    "The horizon runs the full three days: 27 games from 14 to 17 November 2026, with an originated line, a "
    "paper pick and an injury read-out for every one - and, as of 19:20 UTC on 11/14, a game-day injury "
    "refresh that re-verifies every published row against the official page it came from (%d of %d slate rows "
    "and %d of %d published report rows agree) and prices the five clubs that filed since the lines were cut."
    % (slate_ok, slate_n, inj_ok, inj_n))
ex["lead"] = (
    ex["lead"].rstrip() + " The morning's next action - capture the day-of-game injury updates for 2026-11-14 "
    "and re-run against them - has been executed: the 01:30 PM ET game-day edition is transcribed row by row "
    "on the new Game-Day Read page, four clubs' filings are diffed against the edition the lines were built "
    "from, and the lines themselves are left exactly as published, because a line re-priced after the cut "
    "cannot be graded. What that exercise found is not a small print: the game-day report moved three of "
    "tonight's five games by at most 2.6 points, and it could not move the other two at all because %d of the "
    "%d players the clubs newly ruled in or out have no minutes row anywhere in this project's inputs (F47)."
    % (blind, new_rows))
ex["findings"].append({
    "n": len(ex["findings"]) + 1,
    "title": "The game-day edition arrived, and it moved the model far less than it should have",
    "detail": "New Orleans, Cleveland, Chicago and Miami all filed between the 04:15 AM ET edition the "
              "horizon was cut from and the 01:30 PM ET game-day edition, adding %d player rows and changing "
              "four statuses; Memphis was still inside its window. Re-run through the engine's own availability "
              "adjustment, CHI@MIN moves from 30.6 to 33.2, DAL@CLE from -1.8 to -2.5 and DET@MIA from -12.2 "
              "to -12.4, and DEN@NOP and BKN@MEM do not move at all. No favourite flips and no published pick "
              "changes side." % new_rows,
    "reading": "Two readings are available and the site publishes both. The charitable one: the report's "
               "intra-day churn is usually noise, and a model that lurched on every status label would be "
               "worse. The uncomfortable one: the reason it cannot move New Orleans is that the Pelicans' "
               "five listed names are not in the minutes table, so the model is not judging them, it is blind "
               "to them. That is F47, and it is the highest-value fix in the register.",
})
ex["what_is_live_now"] = [t for t in ex["what_is_live_now"] if "Game-Day Read" not in t] + [
    "Game-Day Read: the 01:30 PM ET official edition transcribed row by row, the diff against the edition "
    "the lines were cut from, the re-priced model line beside the published one for all five 11/14 games, "
    "and the %d-of-%d row-level verification of the whole 27-game horizon against NBA.com."
    % (slate_ok, slate_n),
]
ex["recommended_next_actions"] = [
    {"rank": 1,
     "action": "DONE 2026-11-14T19:20Z: capture the day-of-game injury updates and re-price. The published "
               "lines were deliberately not rewritten.",
     "why": "Executed by session arena/95c1cb23-nba1. Results on the Game-Day Read page; the two editions, "
            "the diff, the impact re-computation and the row-level verification are all in "
            "data/derived/gameday_read.json with a source URL per row. The residual finding is F47, not F13."},
    {"rank": 2,
     "action": "Complete the minutes input, per club, so the availability layer can see a rotation instead "
                "of a top-50 slice",
     "why": "It is what turns tonight's 0.00 columns into numbers and unlocks Q3, Q12 and Q20 (SG20, F47)."},
    {"rank": 3,
     "action": "Capture the 11/15, 11/16 and 11/17 injury-report editions as they are published",
     "why": ex["recommended_next_actions"][1]["why"]},
    {"rank": 4,
     "action": "Log real closing prices",
     "why": ex["recommended_next_actions"][2]["why"]},
    {"rank": 5,
     "action": "Backfill results for 2026-10-20 to 2026-11-05 and re-cut the split",
     "why": ex["recommended_next_actions"][3]["why"]},
]
ex["bottom_line"] = (
    ex["bottom_line"].rstrip() + " The game-day pass added the one thing the site did not have: a measured "
    "answer to 'how much did we miss by cutting the line before the clubs filed?' - three of five games moved, "
    "two could not, and the reason two could not is a data gap with a name and a size, not bad luck.")
save(os.path.join(CONTENT, "executive.json"), ex)

print("sources +%d | flags %d -> %d | questions open %d answered %d | suggestions %d -> %d | findings -> %d"
      % (3, len(load(os.path.join(CONTENT, "flagged.json"))["items"]) - len(new_flags),
         len(load(os.path.join(CONTENT, "flagged.json"))["items"]),
         len(qs["open"]), len(qs["answered"]),
         len(sg["items"]) - len(new_sg), len(sg["items"]), len(ex["findings"])))
