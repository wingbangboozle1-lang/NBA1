#!/usr/bin/env python3
"""Content layer for the 2026-11-15 day roll (session arena/e3ebc423-nba1, COORDINATION R05/R07).

Appends the flagged items, open questions and suggestions the roll produced, and refreshes the
executive summary's horizon/window commitments. Additive: nothing is deleted or renumbered, so
the F- and Q- ids every other page already links to keep resolving.

Run:  python3 scripts/content_2026_11_15.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "data", "content")
SESSION = "arena/e3ebc423-nba1"
DAY = "2026-11-15"
GH = "https://github.com/wingbangboozle1-lang/NBA1/blob/main/"


def rd(name):
    with open(os.path.join(C, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def wr(name, d):
    with open(os.path.join(C, name + ".json"), "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


# ------------------------------------------------------------------ flagged
FLAGGED = [
    {
        "id": "F69",
        "severity": "High",
        "title": "Player-prop and parlay picks cannot be settled from any source this site may cite",
        "detail": (
            "Of the 17 picks published on the 2026-11-14 slate, 13 grade against the official finals and 4 do "
            "not: three Player-points rows and one Player-PRA row need a per-player box score, and the official "
            "game-log endpoints answer 403 to this build while the gamebook PDF host is not on the allowed source "
            "list. Those four rows are now marked 'not gradable' with the reason attached, rather than settled "
            "from a source the site cannot cite. Until a per-player source is registered, no player-prop "
            "strategy (S7, S8) can ever accumulate a settled record, whatever its gate thresholds say."),
        "affected": "S7 / S8 rows on the picks page; every prop strategy's path to a funded tier",
        "source": None,
        "source_url": "https://www.nba.com/game/chi-vs-min-0022600235",
        "suggested_action": (
            "Register one per-player source the site may cite - the box-score table on each NBA.com game page "
            "prints MIN/PTS/REB/AST and is already an allowed host - and re-grade the four rows from it. "
            "See F75: the capture path now exists in the scheduled job, so this becomes executable on the "
            "next CI run rather than waiting on a parser."),
    },
    {
        "id": "F75",
        "severity": "Medium",
        "title": "The four new capture stages are written but have never been executed by a session - only by CI",
        "detail": (
            "The scheduled job now fetches the other two official team-stat pages (traditional, opponent), "
            "the standings page, and per-player box scores for the most recent completed games "
            "(stats.nba.com boxscoretraditionalv2, whose response carries its own headers array so no column "
            "meaning is inferred from position). All four are capture-only: they write "
            "data/raw/_capture_*.json and never a committed snapshot. None of them has been run from this "
            "sandbox, where stats.nba.com answers 403; they will execute on the runner, which carries the "
            "web-client header set the probe record proves returns 200. Until a capture exists, nothing from "
            "these stages appears on a published page - the code is not a result."),
        "affected": "Refresh coverage for standings, team traditional/opponent and per-player game logs",
        "source": "S20",
        "source_url": "https://www.nba.com/stats/teams/traditional",
        "suggested_action": (
            "On the next refresh run, read data/raw/_capture_S1t_traditional.json, _capture_S1o_opponent.json, "
            "_capture_S9_standings.json and the newest _capture_gamelog_*.json; where teams_parsed != 30 the "
            "capture carries failure_evidence with the raw excerpt, which is the thing to write a real parser "
            "against."),
    },
    {
        "id": "F70",
        "severity": "Medium",
        "title": "Travel distance is still not in the model: the term exists, its input table does not",
        "detail": (
            "engine/model_core.py now carries travel_load() and engine/home_court.py carries "
            "travel_leg_miles()/haversine_miles(), so the arithmetic is written and self-checked (New York to "
            "Denver: 1,627 miles). The coefficient is 0.0 and stays 0.0 because the model refuses to price with "
            "distances it cannot source: no NBA-operated page reachable from this build publishes arena "
            "latitudes and longitudes, and coordinates written from memory are exactly the untraceable numbers "
            "the verification rule exists to keep out. The one travel fact the official cards do print - whether "
            "a team's next game is in the city it is already in - is published on the day-roll page as a "
            "stand-in, with the limitation named beside it."),
        "affected": "Rest / back-to-back pricing on every line; the 3-in-4 nights load rule",
        "source": None,
        "source_url": "https://www.nba.com/standings",
        "suggested_action": (
            "Add data/official/arena_coordinates.json - arena name, the city as printed on the game card, "
            "lat/lon, the URL each value was read from and the read time - then fit the coefficient on the "
            "results feed instead of assuming it."),
    },
    {
        "id": "F71",
        "severity": "High",
        "title": "Home court: the published lines still use an assumption, and it is more than double the measured rate",
        "detail": (
            "Three values are in play. 2.5 points is the hard-coded project assumption used by every published "
            "line (flag E-01). 3.508 points is what engine/validate.py fits on holdout residuals - in-sample, "
            "and disclosed as such. 1.053 points is home court pinned to the measured home-win rate: 0.5469 on "
            "the 64 non-neutral games in the results feed and 0.5294 on the 187 home games in the official "
            "standings HOME column. The pin is computed, published and reproducible "
            "(scripts/pin_home_court.py writes data/derived/home_court_pin.json), but it is NOT applied to the "
            "current horizon: the 60 picks are frozen and hashed in data/live/ledger_2026-11-15.json, and moving "
            "their lines after tip would void the pre-registration the ledger exists to protect. The published "
            "lines are therefore priced with a home edge this site states is too large."),
        "affected": "Every margin on the Lines, Picks and Game Flow pages; every side pick's edge",
        "source": None,
        "source_url": GH + "data/derived/home_court_pin.json",
        "suggested_action": (
            "Adopt the pin at the next freeze (adopted_for_pricing in data/derived/home_court_pin.json) and "
            "re-grade the window with it as a labelled second column. The day-roll page prints the whole "
            "sensitivity: -1.447 points on every home margin, zero on totals."),
    },
    {
        "id": "F72",
        "severity": "Low",
        "title": "Most horizon venues are carried forward, and the 12 games added for 11/18 have none at all",
        "detail": (
            "The 34-game horizon (2026-11-15 to 11-18) is priced with tip times, matchups and records read from "
            "the official date cards today. Venue and city for the 22 games dated 11/15-11/17 are the values "
            "captured from each game's own NBA.com page on 11/14 - carried forward deliberately, because arenas "
            "do not move, and labelled as carried in data/raw/schedule_upcoming.json. The 12 games added for "
            "11/18 carry venue = null, because the only official block that lists them prints tip times and "
            "records and no arena. Nothing was filled in from memory."),
        "affected": "Venue column on the horizon tables; travel legs for the 11/18 slate",
        "source": None,
        "source_url": "https://www.nba.com/games?date=2026-11-18",
        "suggested_action": "Fetch the twelve 11/18 game pages on the next run and promote their venues row by row.",
    },
    {
        "id": "F73",
        "severity": "Medium",
        "title": "One game in five has no quarter scores in the new results feed",
        "detail": (
            "The 2026-11-14 result feed carries one row per game with date, teams, final, quarter scores and the "
            "game id. Four of the five games have a LINESCORES split and every captured split sums to the printed "
            "final on both sides. CHI@MIN (0022600235) does not: the fetch channel refused that game page four "
            "times, so its quarter cells read 'not captured' and its quarter check reads 'uncheckable'. The final "
            "itself is safe - 117-106 appears on the date card and on the game's own header and agrees - but a "
            "quarter split solved backwards from a final would be a fabricated number, so it is left blank."),
        "affected": "Quarter-score column for 0022600235; game-flow reads that want per-quarter margins for that game",
        "source": None,
        "source_url": "https://www.nba.com/game/chi-vs-min-0022600235",
        "suggested_action": "Re-fetch that game page from a run that can reach it and promote the four cells.",
    },
    {
        "id": "F74",
        "severity": "Medium",
        "title": "Until today the scheduled job could not see the newest injury report on a game day",
        "detail": (
            "parse_injury_index() in engine/fetch_official.py matched only names ending in 'PM.pdf', while the "
            "official hub republishes the report every 15 minutes from 12:00 a.m. ET: on 2026-11-15 the newest "
            "edition was the 06:15 a.m. one, and the job's first PM candidate was 12:00 p.m. - so a morning run "
            "either missed the day's report or fell back to the previous evening's. The pattern now accepts AM "
            "and PM, the fixed fallback list includes the morning window and is used only when the index cannot "
            "be read, and scripts/check_injury_editions.py fails the build if either regresses. Historical "
            "captures are NOT back-filled: the editions behind settled slates stay as they were, because "
            "pretending the job had read a newer report would misstate what those lines were priced from."),
        "affected": "Every injury row behind lines published before 2026-11-15; the freshness of today's roll",
        "source": "S5",
        "source_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "suggested_action": "Nothing further for the past; the new check keeps the future honest.",
    },
]

# ------------------------------------------------------------------ questions
QUESTIONS = [
    {
        "id": "Q22",
        "question": "Which home-court value governs the next line freeze - the fitted 3.508, the assumption 2.5, or the measured pin 1.053?",
        "what_is_missing": (
            "The pin is computed and published, and the sensitivity of every published line to it is arithmetic "
            "the site already prints (-1.447 points on home margins, zero on totals). What is missing is the "
            "decision, because adopting it changes the price the strategy records were graded against: "
            "re-freezing with 1.053 makes the settled 60-game window and the new horizon two different models."),
        "how_to_answer": (
            "Set adopted_for_pricing in data/derived/home_court_pin.json, re-run scripts/build_slate_refresh.py "
            "and scripts/generate_picks_d.py, and publish the new pre-registration with the pin inside its "
            "ASSUMPTIONS block before the first tip of that slate. Then re-grade the window with the pin as a "
            "second, labelled column rather than replacing the first."),
        "blocks": "Whether the next slate is priced with a number the site has already called too large",
        "priority": "High",
        "source": "F71",
        "source_url": GH + "data/derived/home_court_pin.json",
    },
    {
        "id": "Q23",
        "question": "Does the results feed require quarter scores for every game, or is an explicit 'not captured' acceptable?",
        "what_is_missing": (
            "The brief asks for one row per game with date, teams, final and quarter scores. Four of the five "
            "rows on 2026-11-14 have them; one does not, because the official summary page would not load in "
            "this session's fetch window. Nothing in the repository says which way the feed should behave when a "
            "source is unreachable for one game in five."),
        "how_to_answer": (
            "Decide between (a) leave the cell blank and flagged, as now - the row publishes and the gap is "
            "visible; (b) hold the whole slate's settlement until every quarter split is readable, which would "
            "have delayed the 11/14 settlement by a day; or (c) accept the gamebook PDF as a secondary source, "
            "which requires adding its host to the allowed list in scripts/verify_dashboard.py."),
        "blocks": "Whether the settlement pipeline may stall on one unreadable page",
        "priority": "Medium",
        "source": "F73",
        "source_url": "https://www.nba.com/game/chi-vs-min-0022600235",
    },
    {
        "id": "Q24",
        "question": "What is the registered source for per-player game logs, now that the roll publishes a real prop slate?",
        "what_is_missing": (
            "Four published prop picks cannot be settled because no allowed host gives this build a per-player "
            "box score (F69), and the minutes-coverage column on the props page is computed from season averages "
            "for the same reason. The requirement to capture per-player game logs for at least the players on an "
            "injury report is therefore still unmet for every date, including the one just rolled."),
        "how_to_answer": (
            "Pick one: parse the box-score table on each NBA.com game page (same host as the finals already "
            "cited, prints MIN/PTS/REB/AST per player), or register the league's public JSON endpoint and put its "
            "host on the allowed list. Then re-run the roll with logs present so prop rows grade and minutes "
            "coverage stops being an estimate."),
        "blocks": "Settlement of S7/S8; the minutes-redistribution column on the props page; prop elasticity",
        "priority": "High",
        "source": "F69",
        "source_url": "https://www.nba.com/game/den-vs-nop-0022600231",
    },
    {
        "id": "Q25",
        "question": "Should the day roll become a scheduled promotion instead of a session act?",
        "what_is_missing": (
            "scripts/roll_2026_11_15.py runs 17 freshness and provenance gates, refuses to write if any fails, "
            "and merges into the committed snapshots instead of replacing them - but its inputs are captures a "
            "session writes by hand. The scheduled job captures into data/raw/_capture_*.json and never "
            "promotes, which is why the horizon went a day stale between sessions."),
        "how_to_answer": (
            "Parameterise the roll by date and call it from refresh-data.yml after the fetch step, gated on the "
            "same 17 checks, and have it open a pull request rather than commit. Until then the horizon ages "
            "whenever no session runs, and the site's own staleness banners are the only defence."),
        "blocks": "Whether tomorrow's slate is priced at all if no session runs",
        "priority": "Medium",
        "source": "F74",
        "source_url": GH + "scripts/roll_2026_11_15.py",
    },
]

# ------------------------------------------------------------------ suggestions
SUGGESTIONS = [
    {
        "id": "SG30",
        "title": "Adopt the measured home-court pin at the next freeze",
        "category": "Model",
        "problem": (
            "Home court enters every published line as +2.5 points, a value this repository itself calls an "
            "assumption. The measured home-win rate pins it at 1.053 points; the fitted residual intercept says "
            "3.508. Pricing side picks with a home edge the league's own results do not support is how a "
            "systematic bias hides inside a profitable-looking record."),
        "options": [
            {
                "option": "Set adopted_for_pricing, re-freeze, and re-grade the window with the pin as a labelled second column",
                "effort": "Low - scripts/pin_home_court.py already writes the file; the rest is one build",
                "risk": "Medium - it changes the price the settled record was graded against, so the old column must stay published beside it",
                "unlocks": "Closes Q22 and F71; home court becomes a measurement instead of a flag",
            },
            {
                "option": "Keep 2.5 and publish the pin as a documented dissent",
                "effort": "None",
                "risk": "High - the site keeps pricing with a number it states is wrong, and the brief's pinning requirement stays open",
                "unlocks": "Nothing",
            },
        ],
        "decision_needed": "Whether the model's home edge is an assumption or a measurement",
        "recommendation": "Adopt the pin at the next freeze and keep 2.5 published as the pre-change column.",
        "source": "F71",
    },
    {
        "id": "SG31",
        "title": "Give the travel term a sourced coordinate table, then measure its coefficient",
        "category": "Data",
        "problem": (
            "Rest is measured from the official schedule, but a 3-in-4 night with a cross-country leg and a "
            "3-in-4 night in the same city are priced identically, because no arena-coordinate table exists. The "
            "term and the great-circle arithmetic are already written and self-checked; only the input is missing."),
        "options": [
            {
                "option": "Read the 30 arenas' names and cities from each franchise's NBA.com page and their lat/lon from one public gazetteer, storing a URL per value",
                "effort": "Medium - 30 pages, one table, one gate",
                "risk": "Low - additive; the coefficient stays 0.0 until it is fitted",
                "unlocks": "Closes F70; turns the rest term into a distance term; feeds game-flow fatigue",
            },
            {
                "option": "Fit travel_coef on the 65 completed games before switching the term on",
                "effort": "Medium - one regression, published with its standard error either way",
                "risk": "Low - a coefficient that does not clear noise stays 0.0, and that is itself the finding",
                "unlocks": "Turns the term on with evidence rather than with a guess",
            },
        ],
        "decision_needed": "Whether to accept a non-NBA gazetteer as the source for coordinates the league does not publish",
        "recommendation": "Fetch the table, keep the coefficient at 0.0 until a fit justifies moving it, and publish the fit with its standard error whichever way it lands.",
        "source": "F70",
    },
    {
        "id": "SG32",
        "title": "Register a per-player box-score source so props can settle",
        "category": "Data",
        "problem": (
            "Four of the 17 published picks on 2026-11-14 cannot be graded, and the props page's minutes column "
            "is an estimate, because no allowed host gives this build a per-player box score. Every player-prop "
            "strategy is therefore untestable no matter how sound its gates are."),
        "options": [
            {
                "option": "Parse the box-score table on each NBA.com game page - same host as every source already cited",
                "effort": "Low - one parser, one fixture, reuse the row-provenance gate",
                "risk": "Low - it lands in data/official/ and is promoted row by row like the finals",
                "unlocks": "Settles S7/S8, replaces estimated minutes with measured ones, satisfies the game-log requirement",
            },
            {
                "option": "Ask for the league's JSON host to be added to the allowed list",
                "effort": "Low code, but it changes the site's source policy",
                "risk": "Medium - widens what counts as citable, which is a reviewer call, not an integration step",
                "unlocks": "The same, plus full-season logs in one call",
            },
        ],
        "decision_needed": "Which source the site is willing to cite for a player's night",
        "recommendation": "Parse the game-page box score first: it needs no policy change and settles the four pending rows.",
        "source": "F69",
    },
    {
        "id": "SG33",
        "title": "Run the day roll from the schedule, behind its own gates",
        "category": "Process",
        "problem": (
            "The horizon went a day stale because promotion is a session act: cron captures, a session promotes. "
            "The roll script already refuses to write unless all 17 gates pass, and it merges into the "
            "committed snapshots instead of overwriting them, so it is safe to automate."),
        "options": [
            {
                "option": "Parameterise the roll by date and call it after the fetch step in refresh-data.yml, publishing a pull request",
                "effort": "Low - the gate logic exists; the date is the only new input",
                "risk": "Medium - an automated run would touch committed data, so it must stay behind the same gates and never push to main",
                "unlocks": "Closes Q25; the horizon cannot age between sessions",
            },
            {
                "option": "Leave promotion to sessions",
                "effort": "None",
                "risk": "Medium - on any day without a session the published horizon and injury read go stale",
                "unlocks": "Nothing",
            },
        ],
        "decision_needed": "Whether an automated run may promote a snapshot after passing the gates",
        "recommendation": "Automate it behind the gates and publish to a pull request - the gate record is the review.",
        "source": "F74",
    },
]


def main():
    f = rd("flagged")
    have = {x["id"] for x in f["items"]}
    added = [x for x in FLAGGED if x["id"] not in have]
    f["items"].extend(added)
    note = (" Session <code>%s</code> added F69-F74 on %s: the day roll, the settlement wiring, the "
            "home-court pin and the injury-edition fix." % (SESSION, DAY))
    if "F69-F74" not in f.get("intro", ""):
        f["intro"] = f.get("intro", "").rstrip() + note
    wr("flagged", f)

    q = rd("questions")
    have = {x["id"] for x in q["open"]}
    q["open"].extend([x for x in QUESTIONS if x["id"] not in have])
    wr("questions", q)

    s = rd("suggestions")
    have = {x["id"] for x in s["items"]}
    s["items"].extend([x for x in SUGGESTIONS if x["id"] not in have])
    wr("suggestions", s)
    print("flagged +%d -> %d | questions +%d -> %d | suggestions +%d -> %d"
          % (len(added), len(f["items"]), len(QUESTIONS), len(q["open"]), len(SUGGESTIONS), len(s["items"])))


if __name__ == "__main__":
    main()
