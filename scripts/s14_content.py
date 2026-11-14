#!/usr/bin/env python3
"""s14_content.py — authored-content refresh for the 2026-11-14 morning capture.

Every number written here was produced by the pipeline re-run on the refreshed
captures (data/raw/s14/) or transcribed from the official pages listed in
scripts/s14_capture.py. Nothing is estimated by hand: where a figure is quoted
in prose it is quoted from docs/data/*.json as generated at 2026-11-14T10:30Z.

Updates:
  data/content/executive.json  - headline, lead, verdict, findings, live list,
                                 next actions, bottom line (60-game window)
  data/content/flagged.json    - F13/F14 resolved; F15/F16/F19 updated; F26/F27
                                 added; intro range corrected
  data/content/questions.json  - Q9 answered (A13); A1/A2/A3/A5/A6/A11 refreshed
                                 to the 60-game numbers; Q2/Q10 updated

Run:  python3 scripts/s14_content.py
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "data", "content")


def load(name):
    with open(os.path.join(CONTENT, name), encoding="utf-8") as f:
        return json.load(f)


def save(name, obj):
    with open(os.path.join(CONTENT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")


# ------------------------------------------------------------- executive.json
executive = load("executive.json")

executive["as_of"] = "2026-11-14"
executive["headline"] = (
    "The horizon runs the full three days: 27 games from 14 to 17 November 2026, with an "
    "originated line, a paper pick and an injury read-out for every one, and a source link on "
    "every row. The 2026-11-13 finals are now captured, settled and folded into a 60-game "
    "out-of-sample window, and the newest official injury-report edition (11/14/26 04:15 AM ET) "
    "has been transcribed row by row. The honest read: a small edge on the margin, none on totals "
    "or winners, and one strategy whose record has cleared the luck gate at last (S1, 23-9, "
    "p = 0.020) - but not the calibration and stability gates, so it stays capped at a quarter "
    "unit.")
executive["lead"] = (
    "Ten strategies were written, seven validation gates were defined, and all ten were run "
    "against a strictly out-of-sample window: all 60 completed games from 2026-11-06 to "
    "2026-11-13, every one predicted using team ratings computed only from 2026-10-20 to "
    "2026-11-05. No game in the test window contributes to the ratings that predict it. On top "
    "of that the system originates a line for every game in the next three days - 14, 15, 16 and "
    "17 November - from official ratings and the newest official injury report.")
executive["verdict"] = {
    "status": "PROVISIONAL - not funded",
    "one_line": (
        "The model beats the naive reference on margin accuracy (MAE 12.98 against 13.62) and "
        "loses to it on totals (14.83 against 14.72) and on picking winners (42-18 against "
        "40-20). S1 (side edge) is now 23-9, worth +11.91 model units, and for the first time "
        "its record is outside what luck alone produces (exact binomial p = 0.020, Wilson lower "
        "bound 0.546 against the 0.524 break-even) - but it fails the calibration gate (hit rate "
        "0.719 against a mean predicted 0.627) and the stability gate (the bootstrap interval on "
        "the model's margin MAE still overlaps the reference), and the availability gate cannot "
        "run at all. Under the tier ceilings it stays a quarter-unit strategy. The 27 new lines "
        "are published as lines and paper picks, not as recommendations."),
    "why": (
        "Sixty games with a 17.4-point residual standard deviation have finally made one record "
        "statistically distinguishable from a coin flip - and that is exactly when the other "
        "gates matter most. A hit rate the model itself did not predict is a calibration failure, "
        "not a windfall; an improvement whose interval overlaps the reference is not stable; and "
        "a gate that cannot run is not passed. Selective skill means paying for the part that "
        "survives every gate and nothing else."),
}
executive["findings"] = [
    {
        "n": 1,
        "title": "The model wins on the margin and loses on totals and winners",
        "detail": (
            "Margin: MAE 12.98 against 13.62 for the naive reference, RMSE 17.12 against 17.88 - "
            "the model is better on both. Totals: MAE 14.83 against 14.72, RMSE 19.35 against "
            "19.10 - the reference is better on both. Straight up the reference went 42-18 and "
            "the model 40-20, and the reference has the better Brier score (0.2001 against "
            "0.2020) and the better log loss (0.5827 against 0.5873)."),
        "reading": (
            "The refinements buy a real but tiny margin improvement and nothing else. The "
            "probability calibration is the weakest part of the model, and it is where the "
            "remaining work should go."),
    },
    {
        "n": 2,
        "title": "Growing the window keeps changing what can be claimed - which is the point of the sample gate",
        "detail": (
            "On the 28-game window the model beat the reference on totals (MAE 14.50 against "
            "14.75). On 51 games it did not (14.86 against 14.75) - the sign flipped. On the "
            "60-game window the sign holds (14.83 against 14.72) and the gap narrowed, but the "
            "conclusion stands. Each addition of data has moved at least one claim."),
        "reading": "Any single-window result at this sample size should be treated as a hypothesis, not a finding.",
    },
    {
        "n": 3,
        "title": "S1 has cleared the luck gate at 23-9 - and failed two others, which is the honest headline",
        "detail": (
            "S1 (side edge vs the reference spread) produced 32 graded plays at 23-9, worth "
            "+11.91 model units and a 37.2% return at -110. Its exact binomial p-value against a "
            "coin flip is 0.020 and the Wilson 95% interval on its hit rate is 0.546 to 0.844 - "
            "the lower bound is now above the 0.5238 break-even, so G4 (skill, not luck) passes "
            "for the first time. But its hit rate of 0.719 against a mean predicted probability "
            "of 0.627 fails the calibration gate (gap 0.091 against a 0.08 tolerance), and the "
            "stability gate fails because the bootstrap interval on the model's margin MAE "
            "(10.2 to 15.94) still contains the reference MAE (13.62). The availability gate "
            "cannot run at all for the graded window."),
        "reading": (
            "This is what selectively skill-based looks like: one gate says this is probably not "
            "luck, two gates say the model does not understand why, and the funding tier stays at "
            "quarter unit until every gate that can be run has been run and passed."),
    },
    {
        "n": 4,
        "title": "Home court looks normal; the back-to-back penalty is large but uncertain",
        "detail": (
            "Home-court advantage estimates at +3.51 points with a standard error of 2.28 "
            "(t = 1.54) across 60 games, squarely in the historical NBA range. The back-to-back "
            "penalty estimates at -6.26 points with a standard error of 4.86 (t = -1.29); because "
            "|t| >= 1 the model applies the full 6.26, but the standard error is most of the "
            "estimate."),
        "readings": [],
        "reading": "Both are published with their standard errors and both are fitted on the test window, which is disclosed on every row they touch.",
    },
    {
        "n": 5,
        "title": "Shrinkage was derived rather than guessed, and the curve is flat where it matters",
        "detail": (
            "The empirical-Bayes calculation gives k = 2.9, weighting each team's observed net "
            "rating at 0.739. The fixed-k sweep shows margin MAE moving from 13.62 at k = 0 to "
            "12.91 at k = 4, then degrading to 13.36 by k = 20. Heavy shrinkage is clearly wrong; "
            "the choice between light and none barely matters."),
        "reading": "The constant is defensible, its sensitivity is published, and it is not a source of hidden risk.",
    },
    {
        "n": 6,
        "title": "Availability impact is a measured floor, not an estimate",
        "detail": (
            "Minutes are only known for the 50 players in the captured official table. Players "
            "outside it contribute 0.00 to the impact, so teams missing rotation players who are "
            "not top-50 scorers show a smaller number than the truth - sometimes zero. The "
            "minutes-coverage column sits next to every figure so a 0.00 is never read as "
            "'healthy'."),
        "reading": "Correct but incomplete - the Injuries page says so on every row rather than hiding it.",
    },
    {
        "n": 7,
        "title": "Correlation is measured where it can be and flagged where it cannot",
        "detail": (
            "Thirteen team-statistic pairs were measured directly on all 30 teams from the "
            "official advanced table. Net rating explains 87% of the variation in win percentage; "
            "pace is nearly unrelated to net rating (r = -0.34, p = 0.063) and assist percentage "
            "is unrelated to offensive efficiency (r = 0.02, p = 0.92). The parlay and "
            "same-game-parlay correlations that drive pricing are model-derived and labelled as "
            "such."),
        "reading": "The distinction matters most for parlays, because pricing correlated legs as independent is the classic way to overpay.",
    },
    {
        "n": 8,
        "title": "The word 'edge' on this site does not mean edge against a sportsbook",
        "detail": (
            "No sportsbook price is published by an NBA-operated source, so no official link can "
            "be attached to one. The site bets the originated line against a deliberately naive "
            "reference model built from the same official ratings. Until real prices are logged, "
            "'units won' means model-vs-naive-model units."),
        "reading": "This is the single most important caveat for anyone reading the leaderboard.",
    },
    {
        "n": 9,
        "title": "The 2026-11-13 slate is settled, and it did not go well - which is the system working",
        "detail": (
            "Every published paper pick on the 2026-11-13 slate was settled against the official "
            "finals captured on 2026-11-14. The seven gated singles went 3-4 (-1.40 units at "
            "-110) and all three two-leg parlays lost. The picks were pre-registered: the model "
            "blocks in the live file are identical to the copy frozen at 2026-11-13T22:45Z, "
            "before tip. The originated margin line was off by 12.39 points on average across "
            "the nine games - consistent with the 12.98 MAE on the wider window, and a useful "
            "reminder that a night like this is normal at this sample size."),
        "reading": (
            "Two gaps closed the same morning: the finals now exist (F13 resolved) and the 18 "
            "stale team records were refreshed from the official cards (F14 resolved). Two "
            "remain open and are published as such: at the newest injury edition five of the ten "
            "teams playing on 11/14 have still not filed, and no edition lists any player for "
            "the 11/16 and 11/17 games."),
    },
]
executive["what_is_live_now"] = [
    "Originated spreads, totals, moneylines and fair prices for all 27 games across 2026-11-14, 2026-11-15, 2026-11-16 and 2026-11-17.",
    "63 picks from the strategy library, each tagged with its strategy, its market, the reference number it is betting against, the model's number and the gap.",
    "Player projections for the top-50 scorers, with the possession, opponent-defence and teammate-availability factors broken out separately.",
    "The official injury report, 11/14/26 04:15 AM ET edition, transcribed row by row - 49 rows - with each player's status and the team's published reason.",
    "The settlement of every published paper pick on the 2026-11-13 slate against the official finals, with pre-registration provenance.",
    "Game-flow read-outs built from official pace and efficiency inputs, including probability of a close game, a blowout and overtime.",
    "60 out-of-sample games with the full seven-gate matrix, a 30-team luck decomposition, 13 measured correlations and a ten-strategy leaderboard with reward tiers.",
]
executive["recommended_next_actions"] = [
    {
        "rank": 1,
        "action": "Capture the day-of-game injury updates for 2026-11-14 (after 16:30 UTC) and re-run the pipeline",
        "why": (
            "At the newest edition (11/14/26 04:15 AM ET), the same five teams - New Orleans, "
            "Cleveland, Memphis, Chicago and Miami - have still not filed for tonight's games. "
            "The official rules require game-day reports between 11 a.m. and 1 p.m. local time, "
            "so a later edition today will contain them. Tonight's five lines currently carry "
            "no adjustment for those teams."),
        "source_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "source_label": "NBA official injury-report index",
    },
    {
        "rank": 2,
        "action": "Capture the 11/15, 11/16 and 11/17 injury-report editions as they are published",
        "why": (
            "The 04:15 AM ET edition lists all twenty team-slots for 11/15 as NOT YET SUBMITTED "
            "and lists no rows at all for 11/16 or 11/17 - exactly as the reporting deadlines "
            "predict. Until those editions exist, 18 of the 27 horizon lines carry no injury "
            "adjustment and say so."),
        "source_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "source_label": "NBA official injury-report index",
    },
    {
        "rank": 3,
        "action": "Log real closing prices",
        "why": "Until this exists, nothing here can be called profitable - only better than a naive model. Everything else is optimisation of an unvalidated target.",
        "source_url": None,
        "source_label": None,
        "source_note": "No official price source is available in this repository; a methodological action, flagged unverified.",
    },
    {
        "rank": 4,
        "action": "Backfill results for 2026-10-20 to 2026-11-05 and re-cut the split",
        "why": "Every game from 2026-11-06 onward is already in the test window, so this is now the only way to grow the sample. It would let the ratings window move earlier and the test window roughly double again.",
        "source_url": "https://www.nba.com/games",
        "source_label": "NBA.com Games & Scores index",
    },
    {
        "rank": 5,
        "action": "Complete the Players Traditional table so minutes are known for all 465 players",
        "why": "Minutes are known for 50 of them, so the availability impact is a measured lower bound and three prop strategies have no graded plays at all.",
        "source_url": "https://www.nba.com/stats/players/traditional",
        "source_label": "NBA.com Stats, Players Traditional",
    },
]
executive["bottom_line"] = (
    "The machinery works end to end: it originates lines for every game three days out, it tests "
    "ten strategies against a real out-of-sample window, it settles the previous slate's paper "
    "picks against official finals the morning after, it refuses to promote anything that has "
    "not cleared every gate that can be run, and it publishes every gap it cannot close. One "
    "strategy has now cleared the luck gate and failed two others - that is the first genuinely "
    "selective signal in the project, and the gate matrix is what keeps it honest. What the "
    "project still cannot do is prove any of it against a real price, because no NBA-operated "
    "source publishes one.")
save("executive.json", executive)

# --------------------------------------------------------------- flagged.json
flagged = load("flagged.json")
flagged["intro"] = (
    "Every item below is something the verification pass could not confirm from an official "
    "source, a value that was left blank rather than filled in, or a resolved item kept visible "
    "with its evidence. None of these blocks the site: they are published here so they can be "
    "reviewed and assigned. Each item carries the official link it relates to. Items F13 to F25 "
    "were added on 2026-11-14 by the horizon build and the refresh session; F13 and F14 were "
    "resolved the same morning by session arena/254dd8bb-nba1 and F26-F27 were added by it."
)

def set_item(fid, **kw):
    for it in flagged["items"]:
        if it["id"] == fid:
            it.update(kw)
            return
    raise KeyError(fid)

set_item(
    "F13",
    title="RESOLVED - the 2026-11-13 finals were captured and settled",
    detail=(
        "Resolved 2026-11-14T10:10Z. All nine games were Final on the official Games & Scores "
        "page and were transcribed row by row (data/raw/s14/finals_2026-11-13.json). Every "
        "published paper pick on the slate was settled against them (3-4 singles, 0-3 parlays; "
        "data/raw/s14/settlement_2026-11-13.json), and the games now extend the out-of-sample "
        "window from 51 to 60. The pre-game picks are auditable: the model blocks in the live "
        "file are identical to the copy frozen at 2026-11-13T22:45Z."),
    affected="Closed. Ratings window now ends 2026-11-13; team records current; backtest window 60 games.",
    suggested_action="None. Kept visible with its evidence for review.",
)
set_item(
    "F14",
    title="RESOLVED - team records refreshed from the official cards",
    detail=(
        "Resolved 2026-11-14T10:10Z. All 27 horizon rows were re-read from the official game "
        "cards and 22 record cells changed; every printed record was cross-checked against the "
        "official standings table through the games of 2026-11-13 (30 teams, wins = losses = "
        "183, consistent with the 174 games previously captured plus the nine 2026-11-13 "
        "finals). See data/raw/s14/horizon_cards_2026-11-14.json and "
        "data/raw/s14/standings_2026-11-14.json."),
    affected="Closed. Record columns on the Lines, Picks, Game Flow and Team pages are current as of 2026-11-14T10:10Z.",
    suggested_action="None. Kept visible with its evidence for review.",
)
set_item(
    "F15",
    title="The 11/14 injury report still covers only half the teams",
    detail=(
        "At the newest edition (11/14/26 04:15 AM ET), the same five of the ten teams playing on "
        "11/14 are printed as NOT YET SUBMITTED: New Orleans Pelicans, Cleveland Cavaliers, "
        "Memphis Grizzlies, Chicago Bulls and Miami Heat. Only Denver, Dallas, Brooklyn, "
        "Minnesota and Detroit have filed. The official rules require game-day reports between "
        "11 a.m. and 1 p.m. local time, so later editions today are expected to contain the "
        "missing five."),
    affected="Availability impact for 5 of the 10 teams on 2026-11-14 (5 of tonight's 5 games)",
    source="S10_2026-11-14-0415AM",
    source_url="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf",
    suggested_action="Capture the day-of-game editions after 16:30 UTC and re-run. The NOT YET SUBMITTED rows are published exactly as printed and are never filled in.",
)
set_item(
    "F16",
    title="No injury-report edition yet covers the 11/16 to 11/17 games",
    detail=(
        "The newest official edition (11/14/26 04:15 AM ET) now lists the 11/15 games - all "
        "twenty team-slots printed as NOT YET SUBMITTED, which is consistent with the 5 p.m. "
        "local filing deadline - but it lists no rows at all for the 11/16 and 11/17 games. "
        "Those editions do not exist yet."),
    affected="Availability impact for the 13 games on 11/16 and 11/17; their lines carry no injury adjustment",
    source="S10_2026-11-14-0415AM",
    source_url="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf",
    suggested_action="Add the 11/15, 11/16 and 11/17 editions to the refresh job as they are published. The Lines page already states, per team, that there is no entry in this edition.",
)
set_item(
    "F19",
    title="Ratings cover games through 2026-11-12 only",
    detail=(
        "The results window now runs through 2026-11-13, but the season-to-date team ratings "
        "used by the model remain the official NBA.com Teams Advanced table as it stood after "
        "the games of 2026-11-12. That table cannot be re-captured from the runners yet (F24), "
        "so the ratings are one night behind the results."),
    affected="Every line and pick for the horizon; the ratings input to the backtest",
    source="S1",
    source_url="https://www.nba.com/stats/teams/advanced",
    suggested_action="Re-capture the official Teams Advanced table through 2026-11-13 when the runner access question (F24/Q1) is resolved, and re-run the pipeline.",
)

flagged["items"].append({
    "id": "F26",
    "severity": "High",
    "title": "A leaderboard tier label could claim funding while gates had failed (defect found and fixed)",
    "detail": (
        "The line-by-line review on 2026-11-14 found that the leaderboard's score-based tiering "
        "could assign the label 'Tier 1 - Funded - passed every applicable gate' to a strategy "
        "whose gate matrix still showed failures (S1 at 23-9 passed G1/G3/G4 but failed the "
        "calibration gate G2 and the stability gate G5). The tier ceilings were corrected the "
        "same day so that no tier above 'quarter unit' can be reached while any applicable gate "
        "is failed or unrun; the score weights were not touched. Published here so the change "
        "can be reviewed against engine/leaderboard.py."),
    "affected": "The Strategies & Leaderboard and Validation pages (every tier label)",
    "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine/leaderboard.py",
    "suggested_action": "Review the ceiling rules in engine/leaderboard.py and the tier notes on the leaderboard page.",
})
flagged["items"].append({
    "id": "F27",
    "severity": "Low",
    "title": "One injury row lost its Team cell in the official PDF render (attributed, not printed)",
    "detail": (
        "In the 11/14/26 04:15 AM ET edition, the row 'Traore, Nolan | Probable | "
        "Injury/Illness - Right Calf Tightness / Soreness' rendered without its Team cell. The "
        "player is listed on the official Brooklyn Nets roster (Nolan Traore, #10), and the row "
        "sits inside the BKN@MEM block of the report, so it is transcribed with team 'Brooklyn "
        "Nets' and an explicit attribution note - it is recorded as attribution, not as printed."),
    "affected": "One row of the injury transcription (data/raw/s14/injury_report_2026-11-14_0415ET.json)",
    "source_url": "https://www.nba.com/team/1610612751/nets",
    "suggested_action": "Confirm against a later edition of the same PDF, where the cell is expected to render.",
})
save("flagged.json", flagged)

# ------------------------------------------------------------- questions.json
questions = load("questions.json")

def set_answer(aid, **kw):
    for a in questions["answered"]:
        if a["id"] == aid:
            a.update(kw)
            return
    raise KeyError(aid)

set_answer("A1", answer=(
    "Yes, slightly, on 60 out-of-sample games (2026-11-06 to 2026-11-13). Mean absolute margin "
    "error 12.98 points against 13.62 for the naive reference; RMSE 17.12 against 17.88. The "
    "model is better on both. But the bootstrap 95% interval on the model's MAE is 10.2-15.94 "
    "and the reference's is 10.69-16.61, so the two still overlap - the improvement is not "
    "statistically established."))
set_answer("A2", answer=(
    "No, not now. Mean absolute total error is 14.83 against 14.72 for the reference, and RMSE "
    "19.35 against 19.10. The reference is better on both, as it also was on the 51-game window "
    "(14.86 against 14.75) after the sign flipped away from the 28-game reading. The reference "
    "total is simply the sum of the two team efficiencies; the model's extra terms are not "
    "buying anything here."))
set_answer("A3", answer=(
    "No. The reference went 42-18 straight up on the 60-game window, the model 40-20. On the "
    "probability metrics the reference is also better: Brier 0.2001 against 0.2020, log loss "
    "0.5827 against 0.5873. The model's refinements do not translate into better winner "
    "picks."))
set_answer("A5", answer=(
    "The point estimate is +3.51 points with a standard error of 2.28 (t = 1.54) across 60 "
    "games, one of which was at a neutral site and excluded from the intercept. It is "
    "consistent with the historical NBA range but not statistically established at this "
    "sample."))
set_answer("A6", answer=(
    "The estimate is -6.26 points on the home margin with a standard error of 4.86 (t = -1.29). "
    "Because |t| >= 1 the model applies the full 6.26 penalty rather than zeroing it. That is a "
    "large number and the standard error is most of it, so it is published with the disclosure "
    "that it is fitted on the test window (in-sample)."))
set_answer("A11", answer=(
    "Partially. S1 (side edge vs reference) is 23-9 on 32 graded plays, worth +11.91 model "
    "units and a 37.2% return at -110. The exact binomial p-value against a 50% null is 0.020 "
    "and the Wilson 95% interval is 0.546-0.844, whose lower bound now clears the 0.5238 "
    "break-even: on the luck axis alone, this record is no longer explainable as a coin flip at "
    "the 5% level. But the calibration gate fails (hit rate 0.719 against a mean predicted "
    "0.627) and the stability gate fails (the MAE interval still overlaps the reference), and "
    "the availability gate cannot run. Under the tier ceilings the strategy stays at "
    "quarter-unit funding - skill on one axis, not yet on the others."))

# Q9: answered
questions["open"] = [x for x in questions["open"] if x["id"] != "Q9"]
questions["answered"].append({
    "id": "A13",
    "question": "What were the final scores of the nine 2026-11-13 games, and how do they change the horizon's lines?",
    "answer": (
        "Captured 2026-11-14T10:10Z from the official Games & Scores page: NYK 104 at IND 106; "
        "MIL 99 at ORL 107; CLE 121 at MIA 133; ATL 117 at CHI 125 (OT); MEM 142 at NOP 111; "
        "UTA 118 at HOU 125; GSW 85 at SAS 123; POR 120 at SAC 107; OKC 112 at LAC 113. The "
        "games now extend the out-of-sample window from 51 to 60, they settled every published "
        "paper pick on the slate (seven gated singles 3-4, -1.40 units at -110; three two-leg "
        "parlays, all lost), and they refreshed the 18 stale team records. The horizon's "
        "originated lines were regenerated from the refreshed inputs; the model's margin line "
        "was off by 12.39 points on average across the nine games."),
    "source": "S3_2026-11-13",
    "source_url": "https://www.nba.com/games?date=2026-11-13",
    "confidence": "High - every score was read from the official final card and cross-checked against the official standings table",
})

# Q2 and Q10 refresh
for x in questions["open"]:
    if x["id"] == "Q2":
        x["what_is_missing"] = (
            "Results for 2026-10-20 through 2026-11-05. Those games exist and are officially "
            "published, but they are currently the ratings window, so moving them into the test "
            "set requires a different split - for example ratings from the first 40 games of the "
            "season and testing on everything after. (The window grew from 51 to 60 games on "
            "2026-11-14 when the 2026-11-13 finals were captured; that growth path is now "
            "exhausted.)")
        x["how_to_answer"] = (
            "Backfill 2026-10-20 to 2026-11-05 results, then re-cut the split so the ratings "
            "window is earlier and the test window is longer. This is now the only way to grow "
            "the sample, since every game from 2026-11-06 onward is already in it.")
    if x["id"] == "Q10":
        x["what_is_missing"] = (
            "At the newest official edition (11/14/26 04:15 AM ET), five of the ten teams "
            "playing on 11/14 have not filed (New Orleans, Cleveland, Memphis, Chicago, Miami), "
            "all twenty team-slots for 11/15 are printed as NOT YET SUBMITTED, and no rows exist "
            "for 11/16 or 11/17. The five filed teams for tonight are transcribed in full (31 "
            "rows for 11/14).")
        x["how_to_answer"] = (
            "Capture the official injury-report index "
            "(https://official.nba.com/nba-injury-report-2026-27-season/) on each of 11/14 "
            "(after 16:30 UTC, when the game-day reports are due), 11/15, 11/16 and 11/17 and "
            "add each published edition to the refresh job.")

save("questions.json", questions)
print("content refreshed: executive.json, flagged.json (F13/F14 resolved, F15/F16/F19 updated, F26/F27 added), questions.json (A13 added)")
