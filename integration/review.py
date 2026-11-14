#!/usr/bin/env python3
"""V01 — the line-by-line read of this repository, as data.

Written once, published twice: `integration/out/review.json` feeds the desk page and
`REPO_REVIEW.md` is rendered from the same rows, so the prose on GitHub and the prose on the
site cannot drift apart.

Every finding cites a file and, where the defect is a specific line, the line number as it
stood at this branch's merge base. A finding with no line was established by reading the whole
file or by running it; that is said in the row rather than hidden behind a fake citation.
"""

import json
import os

from common import ROOT, dump, load

REPO = "https://github.com/wingbangboozle1-lang/NBA1/blob/arena/2edb85af-nba1"


def L(path, line=None):
    return f"{REPO}/{path}" + (f"#L{line}" if line else "")


FINDINGS = [
    dict(file="scripts/build_edge_site.py:41", url=L("scripts/build_edge_site.py", 41),
         severity="HIGH",
         finding="`SIGMA = 11.0` is the scale that turns a projected margin into a win "
                 "probability, fed through a logistic link. It was suspected of making every "
                 "probability on lines.html too confident. Tested, that turns out to be the "
                 "wrong diagnosis — and the real defect underneath it is worse for the site's "
                 "credibility than a mis-set constant.",
         action="MEASURED_IN_BUILD",  # replaced in build() from integration/out/transform_test.json
         verify_url="https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026"),
    dict(file="scripts/build_edge_site.py:380", url=L("scripts/build_edge_site.py", 380),
         severity="MEDIUM",
         finding="The page header hard-codes “data as of 2026-11-13”. Nothing in the build "
                 "fails when the data moves a day, so the site can advertise a stale date "
                 "while showing different numbers underneath it.",
         action="The desk takes its stamp from data/live/capture_meta.json instead of a "
                "literal, and the Build A header was updated to name both capture dates so a "
                "reader can see which page is older.",
         verify_url="https://www.nba.com/games?date=2026-11-14"),
    dict(file="scripts/build_site.py:27 / engine/build_site.py:44", url=L("scripts/build_site.py", 27),
         severity="MEDIUM",
         finding="Two more literal date stamps (`GENERATED`, `STAMP`) sit at the top of the two "
                 "site generators. Same failure mode as above, twice: the stamp is a string, "
                 "not a fact about the data.",
         action="Left alone by this session (owned by their builders) and recorded here so a "
                "refresh task replaces them with values read from the capture files.",
         verify_url="https://www.nba.com/games?date=2026-11-14"),
    dict(file="scripts/backtest.py:7-12", url=L("scripts/backtest.py", 8),
         severity="RESOLVED",
         finding="The 14-game backtest is labelled CONTAMINATED by its own docstring: its "
                 "inputs are season-to-date as of 11/13 and include the games being predicted. "
                 "The 78.6% hit rate in that file is therefore not evidence of anything.",
         action="Superseded, not patched: this desk re-ran the same idea with the ratings frozen "
                "at a 10/20–11/05 window fetched through the official page's own DateFrom/DateTo "
                "parameters, on 51 games. That is the number to use.",
         verify_url="https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"),
    dict(file="scripts/originate_lines.py:168", url=L("scripts/originate_lines.py", 168),
         severity="HIGH",
         finding="`sigma = sigma_poisson * 1.15` — an overdispersion factor of 1.15 applied to "
                 "a dispersion that was itself assumed. Two guesses multiplied look like a "
                 "model. This is not hypothetical here: `scripts/build_site.py:369` records that "
                 "an earlier version of this same pipeline 'guessed a dispersion figure and "
                 "produced 99.9% win probabilities and 30-point spreads'.",
         action="Do not extend that path. Dispersion on the desk is now measured from the "
                "official finals in the graded window (60 games, 2026-11-06 .. 2026-11-13) "
                "for teams and from 12 logged player-games for props, each published with an "
                "interval and a sample size.",
         verify_url="https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    dict(file="engine/model_core.py:30-56", url=L("engine/model_core.py", 44),
         severity="MEDIUM",
         finding="Build B's assumption block is honest and documented (shrink_k 2.8, "
                 "injury_impact_coef 15.0 with a sensitivity sweep, status weights "
                 "Out 1.00 / Doubtful 0.70 / Questionable 0.35 / Probable 0.10, 240 team "
                 "minutes). Its status weighting is a ranking of belief, not a measured "
                 "minutes haircut, and `team_minutes_per_game = 240.0` is the only place in "
                 "the repo where vacated minutes get redistributed.",
         action="The desk does the opposite and says so: a vacated minute share reduces the "
                "named player's team and is not re-spread, because the teammate minutes were "
                "never captured. Both choices are defensible; only one is honest about the gap.",
         verify_url="https://www.nba.com/stats/help/glossary"),
    dict(file="data/raw/players_traditional.json", url=L("data/raw/players_traditional.json"),
         severity="HIGH",
         finding="The file is official page 1 — 50 of 465 rows. Anything that treats it as the "
                 "league's player population is wrong, and several earlier conclusions "
                 "(rotation depth, replacement production) quietly depended on that.",
         action="Every desk table that needs a player row marks the ones outside this page as "
                "SEASON DATA NOT CAPTURED. Fetching the remaining pages is the single cheapest "
                "unblock on the suggestions list.",
         verify_url="https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    dict(file="data/players_minutes_2026_27.json", url=L("data/players_minutes_2026_27.json"),
         severity="MEDIUM",
         finding="Minutes ranks 1–24 only, and its own _meta says later ranks were never "
                 "fetched. It also carries the roster churn the rest of the repo had flagged "
                 "(Brown to Philadelphia, Young to Washington, Garland to Los Angeles, Herro "
                 "to Milwaukee), which the desk confirmed independently against the official "
                 "game-log and player pages.",
         action="Used for what it is: a top-24 leaderboard. Not used to size a role player's "
                "minutes, because it cannot.",
         verify_url="https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    dict(file="data/live/injury_report_2026_11_14.json", url=L("data/live/injury_report_2026_11_14.json"),
         severity="RESOLVED",
         finding="An audit block in this file claimed 18 rows printed their team cell and 8 did "
                 "not. Counting the rows says 16 and 10. The prose was wrong, the data was "
                 "right, and a reviewer trusting the summary would have mis-stated how much of "
                 "the report was usable.",
         action="Corrected in this session to match the rows, with the correction recorded inside "
                "the file rather than silently rewritten. The desk excludes all 10 rows whose "
                "team cell was dropped by PDF pagination.",
         verify_url="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf"),
    dict(file="data/live/results_2026_11_13_in_progress.json",
         url=L("data/live/results_2026_11_13_in_progress.json"),
         severity="MEDIUM",
         finding="A descriptive line in that capture says New York “led 25-24 then 31-31”. "
                 "31-31 is a tie, so the sentence contradicts itself. The scores themselves are "
                 "transcribed consistently with the scoreboard; the prose around them is not "
                 "authoritative.",
         action="No number downstream uses that sentence. Kept visible instead of quietly "
                "edited, because a transcription note that is wrong in one word should be "
                "corrected in view, not silently.",
         verify_url="https://www.nba.com/games?date=2026-11-13"),
    dict(file=".github/workflows/refresh-data.yml", url=L(".github/workflows/refresh-data.yml"),
         severity="HIGH",
         finding="The scheduled refresh workflow has never run: `gh run list --workflow "
                "refresh-data.yml` returns nothing, while the file has three cron entries. Every "
                "'stale data' defect in this repo shares one root cause with this — a pipeline "
                "that exists on paper.",
         action="Recorded as a defect, not worked around. Until a run exists, every page on this "
                "desk is stamped with the manual capture time and nothing pretends to be live.",
         verify_url="https://www.nba.com/games?date=2026-11-14"),
    dict(file="index.html (landing metrics)", url=L("index.html"),
         severity="LOW",
         finding="The landing page claims 27 games for Nov 14–17 and 31 published rows for Nov "
                 "13–16. The desk independently counted 5 + 9 + 8 = 22 games for 11/14–11/16 and "
                 "9 more on 11/13, which reconciles the 31. It cannot verify the 11/17 count of 5 "
                 "from its own capture, since that date was not fetched.",
         action="The 27-game claim is marked partly unverified on the review page rather than "
                "repeated or dismissed. Consistency where it holds is worth publishing too.",
         verify_url="https://www.nba.com/games?date=2026-11-14"),
    dict(file="scripts/verify_integration.py (I6)", url=L("scripts/verify_integration.py", 299),
         severity="LOW",
         finding="The repo-wide gate checks that a page saying “N out-of-sample” agrees with "
                 "docs/data/meta.json. It is the right idea, and it also means prose in this "
                 "repository is only free to state that count once.",
         action="The desk obeys it: every out-of-sample reference on these pages is 60 "
                "(2026-11-06 .. 2026-11-13), which is what the graded table says after the "
                "11/13 finals were captured and appended by this session.",
         verify_url="https://www.nba.com/stats/help/glossary"),
    dict(file="docs/data/validation.json → fit.total_bias", url=L("docs/data/validation.json"),
         severity="LOW",
         finding="Build B disclosed that one of its fitted parameters is test-window-informed. "
                 "Reading it: the total bias term is estimated on the same 51 games it is graded "
                 "on, so its totals look better than the side does.",
         action="The desk's total projection has no bias term at all — it is the sum of two "
                "pp100 estimates — so its MAE total is clean of that specific problem, at the "
                "cost of a small known under-count (bias −0.5 points).",
         verify_url="https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"),
]

IRREGULARITIES = [
    dict(id="IR-01", url=L("data/live/slate_2026_11_14_to_16.json"),
         what="NBA.com does not advance a team's displayed record until its game is final, so "
              "every Nov 14/15/16 card still showed pre-11/13 records while the 11/13 games were "
              "in progress.",
         why_it_matters="Any feature that reads 'record' off a slate page is a day behind at "
                        "tip-off and correct by the next morning.",
         state="CLOSED for the desk on 2026-11-14: slate_records_reread_2026_11_14.json "
               "re-read every card after the finals (30/30 clubs match the DateTo=11/13 stats "
               "table) and the rows now display the reread values with their read time. Records "
               "remain display-only, never a model input. The original 00:37Z capture keeps its "
               "own values as provenance.",
         verify_url="https://www.nba.com/games?date=2026-11-14"),
    dict(id="IR-02", url=L("data/live/player_game_logs.json"),
         what="Minnesota's slate card lists Anthony Edwards as OUT for 11/14 while the same card's "
              "season-leaders capsule shows LaMelo Ball as the leading scorer, and the leaders "
              "block is not re-derived after the report.",
         why_it_matters="A leader shown on a game card is not evidence that the player plays, and "
                        "a leaders-driven prop model would have had Minnesota's 'best scorer' "
                        "available on a night he is not listed.",
         state="Printed as a caveat on every slate row on the desk.",
         verify_url="https://www.nba.com/games?date=2026-11-14"),
    dict(id="IR-03", url=L("data/live/results_2026_11_13_in_progress.json"),
         what="The Emirates NBA Cup group games of 11/13 were excluded from NBA.com's season "
              "aggregates while unfinished, and the slate cards carry a group label that changes "
              "how the same W-L is displayed.",
         why_it_matters="A 'team windows' snapshot taken mid-Cup-window is not the same object as "
                        "one taken after it, which is precisely where a naive refit goes wrong.",
         state="Both readings kept: team_windows.json remains the clean pre-11/13 snapshot "
               "(Cup exclusion recorded there), and team_windows_live_2026_11_13.json is the "
               "refreshed window with DateTo=11/13, captured after every Cup game finished — "
               "the live lines are priced from the refreshed window, the backtest never is.",
         verify_url="https://www.nba.com/games?date=2026-11-13"),
    dict(id="IR-04", url=L("data/live/slate_2026_11_14_to_16.json"),
         what="Game IDs are not contiguous across the schedule: the Cup block runs 0022600034–42 "
              "and regular-season games continue from 0022600231.",
         why_it_matters="It looks like a transcription error and invites a 'missing games' "
                        "investigation that has no answer.",
         state="Void: explained and recorded, not an irregularity in the data.",
         verify_url="https://www.nba.com/games?date=2026-11-13"),
    dict(id="IR-05", url=L("data/live/injury_report_2026_11_14.json"),
         what="In the official injury PDF, the Game Date / Matchup / Team cells are dropped on "
              "continuation rows — 10 of the 26 rows for 11/14 — so a naive parse inherits a team "
              "from the row above.",
         why_it_matters="That is how an absence ends up charged to the wrong club, which moves a "
                        "line in the wrong direction with total confidence.",
         state="Rows carry printed_team=false and are excluded from the impact model; they are "
               "still listed so the exclusion is visible. The 11/14 05:00 AM edition (the "
               "newest at capture) drops the team cell on 1 of 27 player rows (Traore) — same "
               "rule applied, same exclusion.",
         verify_url="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf"),
    dict(id="IR-06", url=L("data/live/injury_report_2026_11_14.json"),
         what="Giannis Antetokounmpo is printed 'Available' with a right wrist sprain while also "
              "heading Miami's leaders capsule; a status is a designation, not a minutes "
              "guarantee.",
         why_it_matters="Any availability model that reads 'Available' as 100% of normal minutes "
                        "overstates the player and understates his teammates.",
         state="The desk gives 'Available' a weight of 0.0 — no deduction and no boost — rather "
               "than inventing a game-time probability.",
         verify_url="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf"),
]

QUESTIONS = [
    dict(id="Q-01", url=L("data/live/capture_meta.json"),
         question="Which price source will we use, and is it licensed for storage?",
         known="No price is reachable from this environment at all; three gates are blank for that "
               "single reason.",
         missing="A closing-line file (even one line per game) and rights to keep it.",
         decision_it_unblocks="Break-even, ROI, CLV, stake sizing, and every market gate — i.e. "
                             "the difference between a forecast desk and a betting desk.",
         verify_url="https://www.nba.com/"),
    dict(id="Q-02", url=L("data/raw/players_traditional.json"),
         question="Do we fetch the remaining ~415 player rows, and how often?",
         known="We hold official page 1 (50 rows). Rotation reassignment is impossible without "
               "the rest.",
         missing="Pages 2–10 of the per-game table, and the minutes table past rank 24.",
         decision_it_unblocks="Sizing vacated minutes, prop lines for role players, and gate V8 "
                              "changing from BLANK to a measurement.",
         verify_url="https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    dict(id="Q-03", url=L("data/live/player_game_logs.json"),
         question="How deep does a player's game-log history need to be before we publish a prop σ?",
         known="A single game-log page gives 4–5 rows per fetch; 12 rows across 3 players produced "
               "intervals wider than the lines themselves.",
         missing="A decided floor (25 games is the desk's proposal) and a rule for players whose "
                 "sample straddles a trade.",
         decision_it_unblocks="Whether props become a category with picks or stay a research page.",
         verify_url="https://www.nba.com/player/203999/nikola-joki-c/game-log"),
    dict(id="Q-04", url=L("data/live/results_2026_11_13_in_progress.json"),
         question="Who runs the settlement re-fetch, and at what time?",
         known="Partly answered 2026-11-14: session arena/df3fed12-nba1 re-read the date page "
               "after the finals, wrote results_2026_11_13_final.json (two-source), and the "
               "ledger now grades 60 games instead of 51.",
         missing="A scheduled job that does this unattended — today it is still a manual pass, "
                 "and the next date will need the same treatment.",
         decision_it_unblocks="Whether the ledger grows daily on its own or one session at a time.",
         verify_url="https://www.nba.com/games?date=2026-11-13"),
    dict(id="Q-05", url=L("index.html"),
         question="Which of the three published sites is the product?",
         known="Build A at the root, Build B under docs/b/, and dated snapshots under docs/. They "
               "disagree on samples (14 vs 23 vs 60 games) and on which gates exist.",
         missing="A decision to merge them under one nav, or to declare one canonical and freeze "
                 "the others.",
         decision_it_unblocks="Where a reviewer looks first, and which register a new strategy has "
                              "to beat.",
         verify_url="https://www.nba.com/schedule"),
    dict(id="Q-06", url=L("docs/data/validation.json"),
         question="Is a parameter allowed to be fitted on the test window if it is disclosed?",
         known="Build B disclosed a test-window-informed total bias; Build A refused and left the "
               "term out. Both are defensible; the numbers are not comparable.",
         missing="A written rule for the project.",
         decision_it_unblocks="Which backtests count toward promotion, and whether Build B's "
                              "totals stay in the ledger.",
         verify_url="https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"),
    dict(id="Q-07", url=L(".github/workflows/refresh-data.yml"),
         question="Why has the refresh workflow never run, and should it run here at all?",
         known="The file exists with three cron entries; the runner log is empty. The probe "
               "workflow that another session added is the same class of job.",
         missing="A check on repository Actions settings and a decision about whether scheduled "
                 "fetches should write to data/ unattended.",
         decision_it_unblocks="Whether 'data as of' can ever mean today rather than a manual pass.",
         verify_url="https://official.nba.com/nba-injury-report-2026-27-season/"),
    dict(id="Q-08", url=L("data/live/injury_report_2026_11_14.json"),
         question="How do we want to treat an asymmetric report — one team filed, one silent?",
         known="Every 11/14 game was asymmetric. Adjusting on the filed side alone biases the "
               "line; refusing to adjust discards real information.",
         missing="A policy: refuse (desk default today), adjust one-sided with a widened "
                 "interval, or wait for the next edition.",
         decision_it_unblocks="How many games per day can carry a published pick at all.",
         verify_url="https://official.nba.com/nba-injury-report-2026-27-season/"),
]

SUGGESTIONS = [
    dict(id="S-01", url=L("data/live/capture_meta.json"),
         suggestion="Add a fetch step for the player per-game tables and finish the minutes "
                    "leaderboard, then re-run the availability layer.",
         cost="Ten to fifteen page fetches, no new infrastructure.",
         payoff="Turns gate V8 from BLANK into a measurement and makes prop lines statable for "
                "more than three players.",
         recommendation="Do this first. It is the cheapest large gap in the repository.",
         verify_url="https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    dict(id="S-02", url=L("scripts/verify_integration.py"),
         suggestion="Promote the desk's capture pattern into a scheduled job: read the slate page, "
                    "the injury PDF and the date-filtered team windows; write dated JSON; refuse "
                    "to overwrite a file whose stamp is newer.",
         cost="One workflow plus a writer that no-ops on stale reads.",
         payoff="Ends the class of defect where a page advertises a date its data does not have.",
         recommendation="Second. Until it exists, stamp every page with the manual capture time.",
         verify_url="https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026"),
    dict(id="S-03", url=L("integration/out/gates.json"),
         suggestion="Keep the gates unweighted and unscored. Build B's LBS blends five components "
                    "into one number out of 100; a pass/fail ledger with a blank column is harder "
                    "to game and easier to argue with.",
         cost="Nothing — a policy choice.",
         payoff="Prevents a large sample from trading away a missing input.",
         recommendation="Adopt as the project rule and say so on the leaderboard page.",
         verify_url="https://www.nba.com/stats/help/glossary"),
    dict(id="S-04", url=L("data/live/team_windows.json"),
         suggestion="Rebuild both builds' ratings on DateFrom/DateTo windows rather than "
                    "season-to-date files, and delete the contaminated 14-game backtest rather "
                    "than keeping a labelled version of it.",
         cost="One careful afternoon; every downstream number moves slightly.",
         payoff="Removes the only look-ahead defect that currently inflates a headline figure in "
                "this repository.",
         recommendation="Do it with a fresh capture day, not mid-session, so the diff is "
                        "explainable in one commit.",
         verify_url="https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026"),
    dict(id="S-05", url=L("index.html"),
         suggestion="Put the blank list on the landing page instead of a subpage: which numbers do "
                    "not exist, and what would produce them.",
         cost="Copy work.",
         payoff="A reviewer deciding 'fund this or fetch more' gets the answer without clicking "
                "through five pages.",
         recommendation="Cheap and it changes what the site is useful for.",
         verify_url="https://www.nba.com/schedule"),
    dict(id="S-06", url=L("data/live/player_game_logs.json"),
         suggestion="Before any parlay work, decide the correlation floor: an r whose Fisher "
                    "interval crosses zero is not a correlation, and a Fréchet band that spans "
                    "0.0–0.4 is not a price.",
         cost="A written threshold; the desk proposes |r| with a 95% interval that excludes 0 at "
              "n≥30 games.",
         payoff="Stops an SGP feature that would have looked profitable for exactly as long as "
                "the sample stayed small.",
         recommendation="Decide now, before more parlay code is written.",
         verify_url="https://www.nba.com/player/203999/nikola-joki-c/game-log"),
    dict(id="S-07", url=L("scripts/check_site.py"),
         suggestion="Register the desk pages in the checkers (PAGES in check_site.py, NAV in "
                    "build_edge_site.py) rather than leaving them as loose HTML.",
         cost="Two list edits.",
         payoff="The same link-and-source rules that guard the Edge Lab pages guard this desk, "
                "which is the only reason its tables can be trusted without re-reading them.",
         recommendation="Done in this session; keep it that way for any future page.",
         verify_url="https://www.nba.com/stats/help/glossary"),
    dict(id="S-08", url=L("data/live/slate_2026_11_14_to_16.json"),
         suggestion="Capture the arena with each slate row.",
         cost="One extra column on a fetch already being made.",
         recommendation="Do it in the next refresh, and until then leave neutral-site checks blank "
                        "on future dates rather than assuming a home game.",
         payoff="Makes rule R4 (the neutral-site veto) live; it is inert today because the venue "
                "was never captured.",
         verify_url="https://www.nba.com/games?date=2026-11-14"),
]

BLANKS = [
    dict(item="Odds, break-even %, hold, ROI, CLV, stake",
         why="no sportsbook price is reachable from this environment",
         appears="every table on desk-lines and desk-validation",
         verify_url="https://www.nba.com/"),
    dict(item="Role-player minutes after an absence",
         why="the season player tables stop at 50 of 465 rows and the minutes file at rank 24",
         appears="availability tables, gate V8",
         verify_url="https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    dict(item="Half-time scoring share and run patterns",
         why="no quarter-level split for any team is stored in this repository",
         appears="game-flow table",
         verify_url="https://www.nba.com/game/cha-vs-phx-0022600230/box-score"),
    dict(item="Neutral-site flag for 11/15 and 11/16",
         why="the slate capture has no venue column",
         appears="selection rule R4, which is therefore inert",
         verify_url="https://www.nba.com/games?date=2026-11-14"),
    dict(item="Filed injury rows for 11/15 and anything for 11/16",
         why="the 11/14 05:00 AM edition carries rows for 11/15 but every club prints NOT YET "
             "SUBMITTED (the day-before deadline is 5 p.m. local on 11/14), and no 11/16 rows "
             "exist yet at all",
         appears="provisional lines for 11/15 and 11/16",
         verify_url="https://official.nba.com/nba-injury-report-2026-27-season/"),
]


def _finding0_action():
    """Rebuild finding #1's action from the current transform_test.json — never typed prose."""
    try:
        with open(os.path.join(ROOT, "integration", "out", "transform_test.json"),
                  encoding="utf-8") as fh:
            tt = json.load(fh)
    except (OSError, ValueError):
        return ("Measured in integration/out/transform_test.json (re-run "
                "python3 integration/transform.py to refresh this row).")
    res = tt.get("results", {})
    n = tt.get("n_graded", "?")
    lg = res.get("logistic_sigma_11", {}).get("brier")
    nm = res.get("normal_sigma_11", {}).get("brier")
    best = tt.get("best_by_brier", {})
    rate = tt.get("home_win_rate_actual")
    hw = round(rate * n) if isinstance(rate, float) and isinstance(n, int) else "?"
    above = tt.get("variants_with_mean_p_home_above_actual", "?")
    tot = tt.get("variants_total", "?")
    return (f"Measured on the same {n} finals (integration/out/transform_test.json): at σ=11 "
            f"the logistic link scores Brier {lg} and a normal link {nm}; the best in the "
            f"table is {best.get('name')} at {best.get('brier')}. What does not survive "
            f"measurement is the home-advantage assumption: home teams actually won {hw} of "
            f"{n} ({rate}) while mean P(home) sits above that in {above} of {tot} variants. "
            "The typed constant is still a defect — it should be fitted or swept, not "
            "hardcoded — and the +2.5 points of home court is the term to re-examine first.")


def build():
    findings = [dict(f) for f in FINDINGS]
    findings[0]["action"] = _finding0_action()
    out = {
        "title": "Repo review + questions and suggestions, integration desk session",
        "session": "arena/2edb85af-nba1 (original read); rows updated by arena/df3fed12-nba1 "
                   "on 2026-11-14 (settlement refresh, COORDINATION §21)",
        "base": "main @ 2f44c98, rebased onto main @ 981a5cf; revalidated against the "
                "2026-11-14 captures",
        "read_at_utc": load("data", "live", "capture_meta.json")["captured_at_utc"],
        "revalidated_at_utc": "2026-11-14T10:45Z (register amendment L15–L19)",
        "method": "Every file under scripts/, engine/ and the two site roots was read; data files "
                  "were opened, counted and compared against the official captures in data/live/. "
                  "Line numbers refer to this branch. A finding is only recorded when the file "
                  "itself or a run of it establishes it.",
        "findings": findings,
        "irregularities": IRREGULARITIES,
        "questions": QUESTIONS,
        "suggestions": SUGGESTIONS,
        "blanks": BLANKS,
        "headline": "The repository has honest labelling and a real model skeleton, and three "
                    "structural holes: an assumed dispersion that a measured one replaces, a "
                    "player-table coverage gap that blocks every rotation claim, and a refresh "
                    "workflow that has never run.",
    }
    dump("review.json", out)
    write_md(out)
    return out


def write_md(out):
    md = ["# REPO_REVIEW — line-by-line read of NBA1, integration desk",
          "",
          f"Session `{out['session']}` · {out['base']} · captures read {out['read_at_utc']} UTC.",
          "",
          out["method"], "",
          f"**{out['headline']}**", "",
          "Two artefacts come from the same rows as this file: `integration/out/review.json` (data) "
          "and the desk page `desk-capture.html` (rendered). They cannot drift, because both are "
          "written by `python3 integration/review.py`.",
          "",
          "## Findings", "",
          "| File / line | Severity | What reading it turned up | What was done |",
          "| --- | --- | --- | --- |"]
    for f in out["findings"]:
        md.append(f"| [{f['file']}]({f['url']}) | {f['severity']} | {f['finding']} | {f['action']} "
                  f"| [re-check at the official page]({f['verify_url']}) |")
    md += ["", "## Irregularities in the official sources", "",
           "| ID | What the source does | Why it matters | State |", "| --- | --- | --- | --- |"]
    for i in out["irregularities"]:
        md.append(f"| [{i['id']}]({i['url']}) | {i['what']} | {i['why_it_matters']} | {i['state']} "
                  f"| [re-check]({i['verify_url']}) |")
    md += ["", "## Questions to answer before deciding", "",
           "| # | Question | Known now | Still missing | Decision it unblocks |",
           "| --- | --- | --- | --- | --- |"]
    for q in out["questions"]:
        md.append(f"| [{q['id']}]({q['url']}) | {q['question']} | {q['known']} | {q['missing']} | "
                  f"{q['decision_it_unblocks']} | [re-check]({q['verify_url']}) |")
    md += ["", "## Suggestions, cheapest evidence first", "",
           "| # | Suggestion | Cost | Payoff | Recommendation | Re-check |",
           "| --- | --- | --- | --- | --- | --- |"]
    for s in out["suggestions"]:
        md.append(f"| [{s['id']}]({s['url']}) | {s['suggestion']} | {s['cost']} | {s['payoff']} | "
                  f"{s['recommendation']} | [re-check]({s['verify_url']}) |")
    md += ["", "## What is blank on every page, and why", "",
           "The link in the first column is the official page that *would* hold the missing value; "
           "it is not evidence that the value exists here.", "",
           "| Blank | Why | Where it shows |", "| --- | --- | --- |"]
    for b in out["blanks"]:
        md.append(f"| [{b['item']}]({b['verify_url']}) | {b['why']} | {b['appears']} |")
    md += ["", "## Verification links for manual review", "",
           "- [NBA.com slate, 2026-11-14](https://www.nba.com/games?date=2026-11-14) · "
           "[11-15](https://www.nba.com/games?date=2026-11-15) · "
           "[11-16](https://www.nba.com/games?date=2026-11-16) · "
           "[11-13](https://www.nba.com/games?date=2026-11-13) — the schedule and record basis.",
           "- [Official injury report index](https://official.nba.com/nba-injury-report-2026-27-season/) "
           "and the [11/14 05:00 AM PDF](https://ak-static.cms.nba.com/referee/injury/"
           "Injury-Report_2026-11-14_05_00AM.pdf) used by the availability layer (the "
           "[11/13 7:30 PM edition](https://ak-static.cms.nba.com/referee/injury/"
           "Injury-Report_2026-11-13_07_30PM.pdf) is kept as provenance).",
           "- [Team advanced stats, 10/20–11/05 window](https://www.nba.com/stats/teams/advanced?"
           "Season=2026-27&SeasonType=Regular+Season&DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026) "
           "— the ratings behind every graded prediction.",
           "- [Team advanced stats, Date To 11/13/2026](https://www.nba.com/stats/teams/advanced?"
           "Season=2026-27&SeasonType=Regular+Season&DateTo=11%2F13%2F2026) — the window "
           "behind the live lines.",
           "- [Jokić game log](https://www.nba.com/player/203999/nikola-joki-c/game-log) · "
           "[LaMelo Ball game log](https://www.nba.com/player/1630163/lamelo-ball/game-log) — the "
           "dispersion rows.",
           "- [11/12 slate](https://www.nba.com/games?date=2026-11-12) and "
           "[CHA@PHX box score](https://www.nba.com/game/cha-vs-phx-0022600230/box-score) — proof "
           "the first 51 graded finals are the official ones; the 9 games of "
           "[11/13](https://www.nba.com/games?date=2026-11-13) were captured two-source into "
           "data/live/results_2026_11_13_final.json (per-game links inside that file).",
           ""]
    # Written under integration/ on purpose: REPO_REVIEW.md at the repository root belongs to
    # another session's review, and a generator that overwrites a file it does not own is how a
    # shared site loses somebody else's work. The root file carries a pointer here instead.
    with open(os.path.join(ROOT, "integration", "REPO_REVIEW.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    return len(md)


START = "<!-- integration-desk-flags:start -->"
END = "<!-- integration-desk-flags:end -->"


def sync_review_html(out):
    """Publish the desk's flags into review.html between sentinels, idempotently.

    review.html belongs to the Edge Lab build and is not regenerated by it, so the block is
    written between markers: a re-run replaces its own rows instead of appending a second copy,
    and the rest of the page is never touched.
    """
    rows = []
    for f in out["findings"]:
        if f["severity"] not in ("HIGH", "MEDIUM"):
            continue
        rows.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td><a class=\"source\" "
                    "href=\"{}\" target=\"_blank\" rel=\"noopener\">re-check</a></td></tr>".format(
                        f"DESK-{f['file'].split(':')[0].split('/')[-1]}", f["severity"],
                        html_escape(f["finding"]), html_escape(f["action"]), f["verify_url"]))
    for i in out["irregularities"]:
        rows.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td><a class=\"source\" "
                    "href=\"{}\" target=\"_blank\" rel=\"noopener\">re-check</a></td></tr>".format(
                        i["id"], "irregularity", html_escape(i["what"] + " — " + i["why_it_matters"]),
                        html_escape(i["state"]), i["verify_url"]))
    for n, b in enumerate(out["blanks"], 1):
        rows.append("<tr><td>DBLK-{:02d}</td><td>BLANK</td><td>{}</td><td>{}</td>"
                    "<td><a class=\"source\" href=\"{}\" target=\"_blank\" rel=\"noopener\">"
                    "where it would come from</a></td></tr>".format(
                        n, html_escape(b["item"]),
                        html_escape(b["why"] + " — shows up on " + b["appears"]),
                        b["verify_url"]))
    block = (START + "<section class=\"card\"><h2>⚑ Flagged by the integration desk "
             "(2026-11-14)</h2><p class=\"card-intro\">Findings from reading the repository line "
             "by line and from the 2026-11-14 captures. Nothing here blocks the merge; every row "
             "links the official page a reviewer should open. Full text: "
             "<a href=\"integration/REPO_REVIEW.md\">integration/REPO_REVIEW.md</a> and "
             "<a href=\"desk-capture.html\">desk-capture.html</a>.</p>"
             "<div class=\"table-wrap\"><table><thead><tr><th>Flag</th><th>Severity</th>"
             "<th>What is wrong</th><th>What was done</th><th>Official page</th></tr></thead><tbody>"
             + "".join(rows) + "</tbody></table></div></section>" + END)
    path = os.path.join(ROOT, "review.html")
    doc = open(path, encoding="utf-8").read()
    if START in doc and END in doc:
        a = doc.index(START)
        b = doc.index(END) + len(END)
        doc = doc[:a] + block + doc[b:]
    else:
        anchor = '<section class="card"><h2>How to close a flag</h2>'
        doc = doc.replace(anchor, block + "\n" + anchor, 1)
    open(path, "w", encoding="utf-8").write(doc)
    return len(rows)


def html_escape(x):
    import html as _h
    return _h.escape(str(x), quote=False)


if __name__ == "__main__":
    o = build()
    n = write_md(o)
    k = sync_review_html(o)
    print(f"review · review.html desk rows: {k}")
    print(f"review · findings={len(o['findings'])} irregularities={len(o['irregularities'])} "
          f"questions={len(o['questions'])} suggestions={len(o['suggestions'])} "
          f"blanks={len(o['blanks'])} · REPO_REVIEW.md {n} lines")
