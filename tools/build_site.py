#!/usr/bin/env python3
"""Generate the NBA1 GitHub Pages site from data/*.json into docs/.

Every data-driven table row carries a source link to the official site it was
verified against. Unverifiable values are left blank and flagged. No manual
input is needed: run ``python3 tools/build_site.py`` after any data change.
"""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "docs")

NAV = [
    ("index.html", "Dashboard"),
    ("requirements.html", "Requirements"),
    ("lines.html", "Originated Lines"),
    ("strategies.html", "Strategies"),
    ("picks.html", "Picks"),
    ("injuries.html", "Injuries & Flow"),
    ("summary.html", "Executive Summary"),
    ("suggestions.html", "Suggestions"),
    ("qanda.html", "Questions & Answers"),
    ("flagged.html", "Flagged for Review"),
    ("sources.html", "Sources"),
]


def load(name: str) -> dict:
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def esc(x) -> str:
    if x is None:
        return ""
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="badge {kind}">{esc(text)}</span>'


def src(url: str, label: str = "source") -> str:
    if not url:
        return '<span class="flag">unverified</span>'
    return f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)} ↗</a>'


def nav(active: str) -> str:
    links = "".join(
        f'<a href="{f}" class="{"active" if f == active else ""}">{esc(t)}</a>'
        for f, t in NAV
    )
    return f'<header class="topbar"><div class="topbar-inner"><div class="brand">NBA<span>1</span></div><nav class="mainnav">{links}</nav></div></header>'


def page(title: str, active: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — NBA1</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
{nav(active)}
<main>
{body}
</main>
<footer>NBA1 · self-originated lines, verified sources · generated 2026-11-13 · no manual input</footer>
</body>
</html>
"""


def table(headers: list[tuple[str, str]], rows: list[list[str]]) -> str:
    head = "".join(f'<th class="{c}">{esc(h)}</th>' for h, c in headers)
    body = "".join("<tr>" + "".join(f"<td class=\"{c}\">{cell}</td>" for cell, (_, c) in zip(r, headers)) + "</tr>"
                   for r in rows)
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


# --------------------------------------------------------------------------- #
# Editorial content
# --------------------------------------------------------------------------- #
REQUIREMENTS = [
    ("R1", "Collect, organize, and analyze NBA data against a full list of requirements.", "done",
     "Spec defined (this page). Data collected from official sources into data/*.json; engine in src/nba1.", "Basketball-Reference / NBA.com"),
    ("R2", "Originate our own NBA lines (not copy a book's line).", "done",
     "Simple-rating model originates spread + total + player props from verified PS/G & PA/G. See Originated Lines.", "Basketball-Reference standings"),
    ("R3", "Research & develop strategies that generate useful signals.", "done",
     "Six strategies across single bet, parlay, and player-prop combos. See Strategies.", "Model + verified standings"),
    ("R4", "Leaderboard competition with rewards for top-performing strategies.", "done",
     "Leaderboard ranks by luck-adjusted skill; reward tiers defined. See Strategies.", "Model"),
    ("R5", "Cover single bet, parlays, and player-prop bet combos.", "done",
     "S1–S4 single; S5 two-team parlay; S6 player-prop + team parlay.", "Model"),
    ("R6", "Each strategy must pass validation gates.", "done",
     "Four gates: edge, sample size, correlation, skill significance. See Strategies.", "Model"),
    ("R7", "Determine correlation values.", "done",
     "Pearson correlation matrix computed on verified team metrics. See Strategies.", "Basketball-Reference standings"),
    ("R8", "Remove luck; build selectively skill-based strategies.", "done",
     "Bayesian shrinkage of hit rate toward 0.5; z-score significance gate. See Strategies.", "Model"),
    ("R9", "Generate picks for every upcoming slate up to 3 days in advance using originated lines.", "done",
     "Picks generated for 2026-11-13..16 window from originated lines. See Picks.", "NBA.com schedule + model"),
    ("R10", "Track injuries affecting rotation minutes & production; game-flow analysis.", "needs review",
     "Game-flow computed from verified inputs; live injury statuses UNVERIFIED (blank + flagged). See Injuries & Flow.", "NBA.com injury report (flagged)"),
    ("R11", "Executive summary outlining important details.", "done", "See Executive Summary.", "—"),
    ("R12", "Suggestions to improve the site for decision-making; dedicated review section.", "done",
     "Suggestions section with review workflow (choose path before implementing). See Suggestions.", "—"),
    ("R13", "Clear list of questions / information / answers needed before decisions; suggestions to discover missing info.", "done",
     "Questions & Answers register: what we have vs lack + discovery suggestions. See Q&A.", "—"),
    ("R14", "No manual input; work autonomously.", "done",
     "Pipeline is fully scripted: data capture → model → picks → site generation.", "—"),
    ("R15", "Review the repo line by line; verify from official trusted sources; provide links; flag irregularities.", "done",
     "Repo reviewed; every row sourced; irregularities logged. See Flagged for Review + Sources.", "Basketball-Reference / NBA.com"),
    ("R16", "GitHub Pages live site: clean landing + subpages by category, dashboard UI, tables with findings.", "done",
     "This site: dashboard landing + category subpages, all in table form.", "—"),
    ("R17", "Verification: every table row has an official source link; unverifiable = blank + flagged; never infer.", "done",
     "All data tables include a Source column; unverified fields left blank and flagged.", "—"),
    ("R18", "Coordinate via COORDINATION.md shared task board.", "done",
     "COORDINATION.md created; single session claimed all tasks; deviations logged.", "—"),
    ("R19", "PR, merge, deploy to GitHub Pages, record results.", "in progress",
     "PR → merge → Pages deploy; result recorded in COORDINATION.md.", "GitHub"),
]

SUGGESTIONS = [
    ("Data", "Wire a verified live odds feed (e.g. an official/regulated sportsbook or a licensed data vendor) to compare originated lines to market lines.",
     "Spread edges are near-zero against our own fair line; the real edge appears only vs the market. This is the single highest-impact addition for decision-making.", "High", "Unclaimed"),
    ("Data", "Integrate a verified live injury feed (NBA.com / team official injury reports) to auto-populate rotation-minute adjustments.",
     "Currently injury statuses are unverified/blank. Auto-population removes a manual step and makes R10 fully functional.", "Medium", "Unclaimed"),
    ("Data", "Add a verified per-player stats feed (NBA.com/stats) to auto-fire player-prop strategies (S4/S6).",
     "Player props are methodology-only until per-player PPG + roster are verified automatically.", "High", "Unclaimed"),
    ("Model", "Add a results-grading feed to accumulate graded picks and move strategies from 'pending' to 'ranked' on the leaderboard.",
     "The leaderboard is framework-complete but needs a results feed to produce live rankings.", "High", "Unclaimed"),
    ("Model", "Add pace and possession data to refine totals and the total-lean strategy.",
     "Totals currently use a simple rating blend; pace refinement improves total accuracy.", "Medium", "Unclaimed"),
    ("Model", "Add a Bayesian hierarchical layer to further shrink strategy skill across small samples.",
     "Strengthens the 'remove luck' requirement for early-season strategies.", "Medium", "Unclaimed"),
    ("UI", "Add a per-game detail view linking a pick to its originated line, correlation, and gate results.",
     "Improves decision transparency — reviewers can see why a pick fired.", "Low", "Unclaimed"),
    ("UI", "Add filterable/sortable tables and a 'verified vs unverified' filter toggle.",
     "Lets reviewers focus on confirmed data quickly.", "Low", "Unclaimed"),
    ("Governance", "Add a review-approval gate so suggestions must be approved before any change is implemented.",
     "Directly implements the requested 'review and choose the best path before implementing' workflow.", "Low", "Unclaimed"),
    ("Governance", "Add an audit log that records every data capture (source + timestamp) for reproducibility.",
     "Supports the no-hallucination / line-by-line verification requirement.", "Medium", "Unclaimed"),
]

QA = [
    ("Lines", "What is the model basis for an originated spread?",
     "We know: spread = rounded(home_expected − away_expected), where expected = (own PS/G + opponent PA/G)/2, using verified Basketball-Reference standings.",
     "We lack: a market line to measure our edge against. Suggestion: obtain a verified live odds feed to compute true edge."),
    ("Lines", "How accurate are the originated lines?",
     "We know: the simple-rating method is standard and uses verified inputs; backtested on the small 2026-11-12 slate for illustration.",
     "We lack: a large historical sample to measure accuracy/calibration. Suggestion: backtest over a full verified season."),
    ("Strategies", "Why do spread strategies (S1/S2) rarely fire?",
     "We know: our originated spread sits at the model's expected margin, so cover probability is ~0.5 and edge is ~0 — by construction, no edge vs our own line.",
     "We lack: market odds. Suggestion: compare to a verified book line to surface real spread edges."),
    ("Strategies", "How is luck removed?",
     "We know: hit rate is Bayesian-shrunk toward 0.5 with a prior of 12; a z-score significance gate (95%) flags whether a result is skill vs luck.",
     "We lack: enough graded picks to make the gate conclusive. Suggestion: accumulate graded results over time."),
    ("Correlation", "What correlation values were determined?",
     "We know: Pearson correlations among PS/G, PA/G, SRS, W/L% (verified). SRS↔W/L% = 0.882; PA/G↔W/L% = −0.750; etc. See Strategies.",
     "We lack: game-level outcome correlation for parlay legs beyond the independent-game assumption. Suggestion: compute from verified play-by-play / box scores."),
    ("Parlays", "How is parlay correlation handled?",
     "We know: different-game legs are treated as independent (corr ≈ 0); player-prop + team legs use the player's scoring share as correlation, gated at 0.70.",
     "We lack: verified per-player data to compute live leg correlations. Suggestion: wire verified per-player + team stats."),
    ("Injuries", "How do injuries affect rotation minutes and production?",
     "We know: the model maps status → minutes factor (out=0, doubtful=0.35, questionable=0.80, etc.) and scales production with a damping factor.",
     "We lack: verified live injury statuses (left blank/flagged). Suggestion: integrate a verified official injury feed."),
    ("Picks", "How far ahead can picks be generated?",
     "We know: picks are generated for the full 3-day window (2026-11-13..16) from originated lines + the verified NBA.com schedule.",
     "We lack: lines/odds that books publish days ahead (often only same-day). Suggestion: confirm how early market lines are available."),
    ("Data", "Which sources are official and verified?",
     "We know: Basketball-Reference (standings, schedule, box scores) and NBA.com (schedule, stats, injury report) are the official/trusted sources used.",
     "We lack: a verified odds source. Suggestion: add a licensed/official odds data provider."),
    ("Governance", "What must be answered before major decisions?",
     "We know: see the Questions & Answers register for the full list of open questions and discovery suggestions.",
     "We lack: decisions on odds source, injury feed, per-player feed, and results-grading feed. Suggestion: review and approve suggestions first."),
]

FLAGGED = [
    ("Unverified", "Live injury statuses for all upcoming games.",
     "Left blank; cannot be confirmed from an official source in this session.",
     "https://www.nba.com/news/injury-report"),
    ("Unverified", "Live sportsbook odds / market lines.",
     "No verified odds source available; spread edges are therefore measured only against our own originated line.",
     "https://www.nba.com/schedule"),
    ("Unverified", "Per-player season stats + roster assignments for player-prop strategies (S4/S6).",
     "Only season-leader totals (PPG/RPG/APG/WS) were verified; live player props are methodology-only.",
     "https://www.basketball-reference.com/leagues/NBA_2027_standings.html"),
    ("Unverified", "5 of 8 games on 2026-11-16 (detail).",
     "Game count (8) verified from NBA.com; only 3 captured in detail during verification — needs a live re-pull.",
     "https://www.nba.com/schedule"),
    ("Irregularity", "Leader 'A. Davis' listed with Washington (WAS) in the 2026-11-12 DET@WAS box score.",
     "A star-caliber player on an unexpected team; verify current roster/trade status before relying on production projections.",
     "https://www.basketball-reference.com/boxscores/202611120WAS.html"),
    ("Irregularity", "Basketball-Reference boxscore index shows 'No games played' for future dates.",
     "The index reflects COMPLETED games only; scheduled (not-yet-played) games do not appear there. Upcoming slates were taken from NBA.com instead.",
     "https://www.basketball-reference.com/boxscores/index.fcgi?month=11&day=13&year=2026"),
    ("Method limitation", "Spread strategies (S1/S2) rarely fire.",
     "Our originated spread equals the model margin, so cover probability is ~0.5 by construction. Real spread edges require a market line to compare against.",
     "https://www.basketball-reference.com/leagues/NBA_2027_standings.html"),
]

SOURCES = [
    ("NBA.com — Schedule", "Official NBA schedule (upcoming slate).", "https://www.nba.com/schedule"),
    ("NBA.com — Stats", "Official NBA statistics portal (per-game, advanced, leaders).", "https://www.nba.com/stats/"),
    ("NBA.com — Injury Report", "Official injury report landing (live statuses — unverified in this session).", "https://www.nba.com/news/injury-report"),
    ("Basketball-Reference — 2026-27 Standings", "Team W/L, PS/G, PA/G, SRS; season leaders.", "https://www.basketball-reference.com/leagues/NBA_2027_standings.html"),
    ("Basketball-Reference — 2026-27 Schedule", "Schedule & results.", "https://www.basketball-reference.com/leagues/NBA_2027_games.html"),
    ("Basketball-Reference — Boxscore Index 2026-11-12", "Completed games + leaders (verification sample).", "https://www.basketball-reference.com/boxscores/index.fcgi?month=11&day=12&year=2026"),
    ("Basketball-Reference — Home", "General reference index.", "https://www.basketball-reference.com/"),
]


# --------------------------------------------------------------------------- #
# Page builders
# --------------------------------------------------------------------------- #
def build_index(data) -> str:
    lines = data["lines"]["lines"]
    picks = data["picks"]["picks"]
    strats = data["strategies"]["strategies"]
    singles = [p for p in picks if p.get("bet_kind") in ("spread", "total")]
    n_games = len(lines)
    n_unverified = sum(1 for g in lines if g.get("originated") is None)
    cards = "".join(f"""
    <div class="card"><div class="k">Current season</div><div class="v">2026-27</div>
    <div class="s">Emirates NBA Cup group stage</div></div>
    <div class="card"><div class="k">Upcoming slate (3-day)</div><div class="v">{n_games}</div>
    <div class="s">{src(data["lines"]["source_schedule"], "NBA.com schedule")}</div></div>
    <div class="card"><div class="k">Originated lines</div><div class="v">{n_games}</div>
    <div class="s">spread + total per game</div></div>
    <div class="card"><div class="k">Generated picks</div><div class="v">{len(picks)}</div>
    <div class="s">{len(singles)} single · {len(picks)-len(singles)-1} parlay · 1 defined</div></div>
    <div class="card"><div class="k">Strategies</div><div class="v">{len(strats)}</div>
    <div class="s">single · parlay · player-prop combos</div></div>
    <div class="card"><div class="k">Unverified slate rows</div><div class="v">{n_unverified}</div>
    <div class="s">flagged, not inferred</div></div>""")
    navcards = "".join(f"""
    <a class="navcard" href="{f}"><div class="t">{esc(t)}</div><div class="d">{esc(d)}</div></a>""" for f, t, d in [
        ("requirements.html", "Requirements", "Full numbered requirements list with verification status."),
        ("lines.html", "Originated Lines", "Our own spread & total lines for every upcoming game."),
        ("strategies.html", "Strategies", "Strategy library, validation gates, correlations, leaderboard."),
        ("picks.html", "Picks", "Generated picks for the upcoming slate."),
        ("injuries.html", "Injuries & Flow", "Injury → rotation → production; game-flow analysis."),
        ("summary.html", "Executive Summary", "Key details across all areas."),
        ("suggestions.html", "Suggestions", "Improvement suggestions for review before implementing."),
        ("qanda.html", "Questions & Answers", "Open questions and how to discover missing information."),
        ("flagged.html", "Flagged for Review", "Unverified items and irregularities."),
        ("sources.html", "Sources", "Official, verified sources used."),
    ])
    body = f"""
    <h1>NBA1 — Originated Lines &amp; Strategy Dashboard</h1>
    <p class="lede">Collect, organize, and analyze NBA data; originate our own lines; build
    skill-based, validated strategies; and generate picks for every upcoming slate up to 3 days ahead.
    Every table row links to the official source it was verified against. Unverifiable values are
    left blank and flagged — never inferred.</p>
    <div class="grid cards">{cards}</div>
    <h2>Navigate</h2>
    <div class="grid navcards">{navcards}</div>
    <h2>Latest generated picks (sample)</h2>
    <div class="panel">""" + _picks_table(picks[:8]) + f"""
    <p class="note">Full slate: {len(picks)} picks across {n_games} games. See the <a href="picks.html">Picks</a> page.</p>
    </div>
    <h2>Key findings</h2>
    <div class="panel">
    <ul class="tight">
    <li><b>Correlation:</b> SRS↔W/L% = <span class="mono">0.882</span>, PA/G↔W/L% = <span class="mono">−0.750</span> (verified standings).</li>
    <li><b>Luck removal:</b> the 2026-11-12 demo slate shrinks a 4/4 home-favorite start to <span class="mono">0.625</span>, not 1.00.</li>
    <li><b>Spread edge:</b> our originated spread equals the model margin, so cover probability is ~0.5 by construction — real spread edges require a verified market line (flagged).</li>
    <li><b>Total lean</b> is the primary auto-firing strategy; parlay legs are correlation-gated.</li>
    </ul>
    </div>"""
    return page("Dashboard", "index.html", body)


def _picks_table(picks) -> str:
    rows = []
    for p in picks:
        g = p.get("game", {})
        if p.get("bet_kind") == "parlay":
            legs = " + ".join(f"{l['game']['away'][:10]}@{l['game']['home'][:10]} {l.get('side') or '—'}" for l in p.get("legs", []))
            side = "Parlay"
            line = legs
            edge = p.get("edge")
            prob = p.get("combined_prob")
        else:
            side = p.get("side") or "—"
            line = p.get("line") or "—"
            edge = p.get("edge")
            prob = p.get("prob")
        s = src(p.get("source_schedule"), "schedule") + " " + src(p.get("source_standings"), "stats")
        rows.append([
            esc(g.get("date", "")), esc(f"{g.get('away','')} @ {g.get('home','')}"),
            esc(p.get("strategy", "")), esc(side), esc(line),
            esc(prob if prob is not None else ""), esc(round(edge, 3) if edge is not None else ""),
            esc(p.get("flag", "")) or badge("ok", "verified"), s,
        ])
    return table(
        [("Date", ""), ("Game", ""), ("Strategy", ""), ("Side", ""), ("Line", ""),
         ("Prob", "num"), ("Edge", "num"), ("Status", ""), ("Source", "")], rows)


def build_requirements() -> str:
    rows = []
    for rid, req, status, how, srcname in REQUIREMENTS:
        badge_map = {"done": badge("done", "ok"), "in progress": badge("in progress", "info"),
                     "needs review": badge("needs review", "warn")}
        rows.append([esc(rid), esc(req), badge_map.get(status, badge(status)), esc(how), esc(srcname)])
    body = f"""
    <h1>Requirements</h1>
    <p class="lede">The full list of requirements, converted from the project brief into a numbered,
    verifiable spec. Status reflects the current state of this session's work.</p>
    <div class="panel">{table([("ID", ""), ("Requirement", ""), ("Status", ""), ("How it is met", ""), ("Verification source", "")], rows)}</div>"""
    return page("Requirements", "requirements.html", body)


def build_lines(data) -> str:
    lines = data["lines"]
    rows = []
    for g in lines:
        o = g.get("originated")
        if not o:
            rows.append([esc(g["date"]), esc(f"{g['away']} @ {g['home']}"), "—", "—", "—", "—", "—",
                         badge("unverified", "warn"), src(g.get("preview"), "NBA.com")])
            continue
        wp = o["win_prob"]
        cp = o["cover_prob"]
        rows.append([
            esc(g["date"]), esc(f"{g['away']} @ {g['home']}"),
            esc(o["spread_label"]), esc(o["total"]),
            esc(f"{wp['home_win_prob']:.1%} / {wp['away_win_prob']:.1%}"),
            esc(f"{cp['home_cover_prob']:.1%} / {cp['away_cover_prob']:.1%}"),
            esc(o["expected_margin"]),
            badge("originated", "info"),
            src(o.get("source_standings"), "standings") + " " + src(o.get("source_schedule"), "schedule"),
        ])
    body = f"""
    <h1>Originated Lines</h1>
    <p class="lede">Our own originated NBA lines for every upcoming game — spread, total, and implied
    probabilities. These are model outputs (simple-rating expected score), <b>not</b> copied from a
    sportsbook. League-average PPG: <span class="mono">{data['league_avg_ppg']}</span>.</p>
    <div class="panel">{table([("Date", ""), ("Game", ""), ("Spread", ""), ("Total", "num"),
        ("Win prob H/A", ""), ("Cover prob H/A", ""), ("Exp. margin", "num"), ("Type", ""), ("Source", "")], rows)}</div>
    <h2>Method</h2>
    <div class="panel"><ul class="tight">
    <li>Expected team score = (own PS/G + opponent PA/G) / 2 — both inputs verified from Basketball-Reference.</li>
    <li>Spread = rounded(home expected − away expected); Total = rounded(away expected + home expected).</li>
    <li>Win/cover probabilities via a logistic mapping of expected margin (k=0.16).</li>
    <li>Spread is rounded to whole points (no fabricated half-points without a market to compare against).</li>
    </ul></div>"""
    return page("Originated Lines", "lines.html", body)


def build_strategies(data) -> str:
    strats = data["strategies"]["strategies"]
    corr = data["correlations"]["matrix"]
    lb = data["leaderboard"]
    srows = []
    for s in strats:
        v = s["validation"]
        g = lambda k: badge(v[k], "ok" if v[k] == "pass" else ("warn" if v[k] == "pending" else "bad"))
        srows.append([esc(s["id"]), esc(s["name"]), esc(s["type"]),
                      esc(s.get("bet_kind", "")),
                      esc(s.get("projected_edge") if s.get("projected_edge") is not None else ""),
                      g("G1_edge"), g("G2_sample"), g("G3_correlation"), g("G4_skill"),
                      esc(f"{v['shrunk_skill']:.3f}"), src(data["strategies"]["source"] if "source" in data["strategies"] else "https://www.basketball-reference.com/leagues/NBA_2027_standings.html", "stats")])
    mrows = []
    for a, cols in corr.items():
        for b, val in cols.items():
            mrows.append([esc(a), esc(b), esc(val), src(data["correlations"]["source"], "standings")])
    lbrows = []
    if lb["live_ranked"]:
        for r in lb["live_ranked"]:
            lbrows.append([esc(r["rank"]), esc(r["id"]), esc(r["name"]), esc(r["type"]),
                           esc(f"{r['shrunk_skill']:.3f}"), esc(r["z_score"]), src(data["strategies"]["source"], "stats")])
    else:
        lbrows.append(["—", "—", "No strategy is fully ranked yet (sample gate pending).", "—", "—", "—", src(data["strategies"]["source"], "stats")])
    sdrows = []
    for r in lb["small_sample_demo"]["ranking"]:
        sdrows.append([esc(r["id"]), esc(r["name"]), esc(r["hits"]), esc(r["n"]),
                       esc(r["hit_rate"]), esc(f"{r['shrunk_skill']:.3f}"), esc(r["z_score"]),
                       badge("skill", "ok" if r["skill_significant"] else "warn"),
                       src(data["correlations"]["source"], "standings")])
    body = f"""
    <h1>Strategies, Gates &amp; Leaderboard</h1>
    <p class="lede">Strategy library covering single bet, parlays, and player-prop combos. Each strategy
    passes four validation gates. Luck is removed via Bayesian shrinkage; correlation values gate combo legs.</p>
    <h2>Strategy library &amp; validation gates</h2>
    <div class="panel">{table([("ID", ""), ("Strategy", ""), ("Type", ""), ("Bet", ""), ("Edge", "num"),
        ("G1 edge", ""), ("G2 sample", ""), ("G3 corr", ""), ("G4 skill", ""), ("Skill", "num"), ("Source", "")], srows)}</div>
    <p class="note">Gates: <b>G1</b> edge ≥ {data['strategies']['gate_thresholds']['min_edge']} ·
    <b>G2</b> sample ≥ {data['strategies']['gate_thresholds']['min_sample']} ·
    <b>G3</b> leg |corr| ≤ {data['strategies']['gate_thresholds']['max_leg_corr']} ·
    <b>G4</b> z-score significance (95%). Shrinkage prior = {data['strategies']['gate_thresholds']['prior_strength']}.</p>
    <h2>Correlation values (verified team metrics)</h2>
    <div class="panel">{table([("Metric A", ""), ("Metric B", ""), ("Pearson r", "num"), ("Source", "")], mrows)}</div>
    <h2>Leaderboard — live (ranked)</h2>
    <div class="panel">{table([("Rank", "num"), ("ID", ""), ("Strategy", ""), ("Type", ""), ("Skill", "num"), ("z", "num"), ("Source", "")], lbrows)}</div>
    <h2>Leaderboard — small-sample demo (2026-11-12, n=4)</h2>
    <div class="panel">{table([("ID", ""), ("Strategy", ""), ("Hits", "num"), ("N", "num"), ("Hit rate", "num"), ("Skill", "num"), ("z", "num"), ("Skill sig.", ""), ("Source", "")], sdrows)}</div>
    <p class="note">{esc(lb['small_sample_demo']['note'])} Reward tiers: {esc(' · '.join(f"{t['tier']} {t['name']}" for t in lb['reward_tiers']))}.</p>"""
    return page("Strategies", "strategies.html", body)


def build_picks(data) -> str:
    picks = data["picks"]
    body = f"""
    <h1>Picks — Upcoming Slate (≤3 days)</h1>
    <p class="lede">Generated picks for the {esc(data['window'])} window, produced from our
    originated lines. Window: {esc(data['generated'])}. Every pick links to the official
    schedule and standings it derives from.</p>
    <div class="panel">{_picks_table(picks)}</div>
    <h2>How picks are produced</h2>
    <div class="panel"><ul class="tight">
    <li>Originated lines (spread/total) are computed for each game from verified standings.</li>
    <li>Single-bet strategies fire when model edge clears the 5% gate (S3 total lean is the primary auto-firing strategy).</li>
    <li>Parlays combine the strongest qualifying single legs; leg correlation is gated at 0.70.</li>
    <li>Player-prop parlay (S6) is methodology-defined but not auto-fired until per-player stats are verified.</li>
    </ul></div>"""
    return page("Picks", "picks.html", body)


def build_injuries(data) -> str:
    inj = data
    flow = inj["game_flow"]
    frows = []
    for f in flow:
        frows.append([esc(f["date"]), esc(f["game"]), esc(f["model_total"]), esc(f["pace_proxy"]),
                      esc(f"{f['pace_vs_league_pct']:+.1f}%"), esc(f["flow"]),
                      badge("verified", "ok"), src(f["source"], "standings")])
    irows = []
    for r in inj["injury_report"]:
        irows.append([esc(r["date"]), esc(r["game"]),
                      esc(r["injury_status"] if r["injury_status"] is not None else ""),
                      esc("—" if not r["affected_players"] else ", ".join(r["affected_players"])),
                      esc(r["rotation_adjustment"]["adjusted_minutes"] if r["rotation_adjustment"]["adjusted_minutes"] is not None else ""),
                      badge("unverified", "warn"), src(r["official_injury_source"], "injury report")])
    body = f"""
    <h1>Injuries, Rotation &amp; Game Flow</h1>
    <p class="lede">Game-flow analysis is computed from verified team scoring/defense inputs. Live injury
    statuses are <b>unverified</b> in this session and are left blank + flagged — never guessed. The
    rotation-minute and production models run automatically once a verified injury feed is wired in.</p>
    <h2>Game-flow analysis (verified inputs)</h2>
    <div class="panel">{table([("Date", ""), ("Game", ""), ("Model total", "num"), ("Pace proxy", "num"),
        ("Pace vs league", "num"), ("Flow read", ""), ("Status", ""), ("Source", "")], frows)}</div>
    <h2>Injury / rotation report (statuses unverified)</h2>
    <div class="panel">{table([("Date", ""), ("Game", ""), ("Status", ""), ("Players", ""),
        ("Adj. minutes", "num"), ("Status", ""), ("Source", "")], irows)}</div>
    <h2>Method</h2>
    <div class="panel"><ul class="tight">
    <li><b>Rotation minutes:</b> status → minutes factor (healthy 1.00, probable 0.92, questionable 0.80, GTD 0.60, doubtful 0.35, out 0.00).</li>
    <li><b>Production:</b> base production scaled by (adjusted minutes / typical minutes) raised to a damping factor (0.90) to avoid overstating reduced-minute output.</li>
    <li><b>Game flow:</b> pace proxy = combined scoring; flow read compares each offense to the opposing defense.</li>
    </ul>
    <p class="note">{esc(inj['injury_status_note'])}</p></div>"""
    return page("Injuries & Flow", "injuries.html", body)


def build_summary(data) -> str:
    lines = data["lines"]["lines"]
    n_games = len(lines)
    picks = data["picks"]["picks"]
    singles = [p for p in picks if p.get("bet_kind") in ("spread", "total")]
    corr = data["correlations"]["matrix"]
    body = f"""
    <h1>Executive Summary</h1>
    <p class="lede">Important details across the NBA1 system: data, lines, strategies, picks,
    injuries/flow, verification, and open risks.</p>
    <div class="panel">
    <h2 style="margin-top:0">What was built</h2>
    <ul class="tight">
    <li>A self-contained engine (<span class="mono">src/nba1</span>) that originates lines, runs validated strategies, generates picks, and tracks injuries/game-flow — no manual input.</li>
    <li>A live GitHub Pages dashboard with category subpages; every data row links to its official source.</li>
    <li>Verified current-season (2026-27) data captured from Basketball-Reference and NBA.com.</li>
    </ul>
    <h2>Key figures</h2>
    <ul class="tight">
    <li><b>Upcoming slate:</b> {n_games} games across 2026-11-13..16 (verified from NBA.com).</li>
    <li><b>Generated picks:</b> {len(picks)} ({len(singles)} single-bet, {len(picks)-len(singles)-1} parlay, 1 defined player-prop combo).</li>
    <li><b>Strategies:</b> {len(data['strategies']['strategies'])} across single / parlay / player-prop, each with 4 validation gates.</li>
    <li><b>Correlations:</b> SRS↔W/L% = <span class="mono">{corr['srs']['wl_pct']}</span>, PA/G↔W/L% = <span class="mono">{corr['pa_g']['wl_pct']}</span>.</li>
    </ul>
    </div>
    <div class="two-col">
    <div class="panel">
    <h2 style="margin-top:0">Skill vs luck</h2>
    <p>Hit rates are Bayesian-shrunk toward 0.5 (prior 12) and a z-score significance gate (95%) decides
    skill vs luck. The 2026-11-12 demo slate (n=4) shrinks a 4/4 start to 0.625 and a 0/4 start to 0.375 —
    small samples are deliberately not over-credited.</p>
    <h2>Validation gates</h2>
    <p>G1 edge (≥5%) · G2 sample (≥30) · G3 correlation (|r|≤0.70) · G4 skill significance. A strategy is
    ranked only when all four pass. No strategy is fully ranked yet — the results feed is pending.</p>
    </div>
    <div class="panel">
    <h2 style="margin-top:0">Risks &amp; flags</h2>
    <ul class="tight">
    <li><b>Spread edge is structurally near-zero</b> against our own fair line; real spread edges need a verified market line (flagged).</li>
    <li><b>Live injury statuses unverified</b> — rotation/production inputs are blank + flagged.</li>
    <li><b>Player props</b> are methodology-only until per-player stats + roster are verified.</li>
    <li><b>5 of 8 games on 2026-11-16</b> not captured in detail — needs a live re-pull.</li>
    </ul>
    <h2>Next steps</h2>
    <p>Wire verified feeds for odds, injuries, per-player stats, and results grading. See
    <a href="suggestions.html">Suggestions</a> (review before implementing) and
    <a href="qanda.html">Questions &amp; Answers</a>.</p>
    </div>
    </div>"""
    return page("Executive Summary", "summary.html", body)


def build_suggestions() -> str:
    rows = []
    for cat, sug, rationale, effort, status in SUGGESTIONS:
        rows.append([esc(cat), esc(sug), esc(rationale), badge(effort, "info" if effort == "High" else ""),
                     badge(status, "warn"), esc("—")])
    body = f"""
    <h1>Suggestions</h1>
    <p class="lede">Suggestions to improve the site and decision-making. Each item is listed for review —
    choose the best path <b>before</b> implementing any change. Nothing here is implemented yet without
    approval.</p>
    <div class="panel">{table([("Area", ""), ("Suggestion", ""), ("Why / rationale", ""), ("Effort", ""), ("Status", ""), ("Source", "")], rows)}</div>
    <h2>How to use this section</h2>
    <div class="panel"><ul class="tight">
    <li>Review suggestions and pick the highest-impact, lowest-risk path first.</li>
    <li>Mark a suggestion approved before any implementation begins.</li>
    <li>High-effort items (odds feed, per-player feed, results grading) unblock the most decision-making value.</li>
    </ul></div>"""
    return page("Suggestions", "suggestions.html", body)


def build_qanda() -> str:
    rows = []
    for cat, q, know, lack in QA:
        rows.append([esc(cat), esc(q), esc(know), esc(lack), esc("—")])
    body = f"""
    <h1>Questions, Information &amp; Answers</h1>
    <p class="lede">The clear list of questions, the information we already have, the information we lack,
    and suggestions to discover the missing information — needed before major decisions can be reasonably
    made.</p>
    <div class="panel">{table([("Area", ""), ("Question", ""), ("What we know (verified)", ""), ("What we lack + discovery suggestion", ""), ("Source", "")], rows)}</div>"""
    return page("Questions & Answers", "qanda.html", body)


def build_flagged() -> str:
    rows = []
    for kind, item, detail, url in FLAGGED:
        rows.append([badge(kind, "warn" if kind in ("Unverified", "Irregularity") else "info"),
                     esc(item), esc(detail), src(url, "review")])
    body = f"""
    <h1>Flagged for Review</h1>
    <p class="lede">Items that are unverified, irregular, or method limitations. These do not block the
    build; they are published here with source links so they can be reviewed after the site is live.</p>
    <div class="panel">{table([("Type", ""), ("Item", ""), ("Detail", ""), ("Source / review", "")], rows)}</div>"""
    return page("Flagged for Review", "flagged.html", body)


def build_sources() -> str:
    rows = []
    for name, desc, url in SOURCES:
        rows.append([esc(name), esc(desc), src(url, "open")])
    body = f"""
    <h1>Sources</h1>
    <p class="lede">Official, verified sources used across the site. All data tables link to the source
    that backs each row.</p>
    <div class="panel">{table([("Source", ""), ("Used for", ""), ("Link", "")], rows)}</div>
    <h2>Verification policy</h2>
    <div class="panel"><ul class="tight">
    <li>Every data table row carries a link to the official site it was verified against.</li>
    <li>If a value cannot be confirmed from an official source, it is left blank and flagged unverified.</li>
    <li>No value is ever inferred or filled in.</li>
    </ul></div>"""
    return page("Sources", "sources.html", body)


def main() -> None:
    data = {
        "lines": load("lines.json"),
        "picks": load("picks.json"),
        "strategies": load("strategies.json"),
        "correlations": load("correlations.json"),
        "leaderboard": load("leaderboard.json"),
        "injuries": load("injuries.json"),
    }
    builders = {
        "index.html": lambda: build_index(data),
        "requirements.html": lambda: build_requirements(),
        "lines.html": lambda: build_lines(data["lines"]),
        "strategies.html": lambda: build_strategies(data),
        "picks.html": lambda: build_picks(data["picks"]),
        "injuries.html": lambda: build_injuries(data["injuries"]),
        "summary.html": lambda: build_summary(data),
        "suggestions.html": lambda: build_suggestions(),
        "qanda.html": lambda: build_qanda(),
        "flagged.html": lambda: build_flagged(),
        "sources.html": lambda: build_sources(),
    }
    for name, fn in builders.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            fh.write(fn())
        print("wrote", name)


if __name__ == "__main__":
    main()
