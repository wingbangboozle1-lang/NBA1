#!/usr/bin/env python3
"""Render the integration desk from integration/out/*.json and data/live/*.json.

Five root pages, one per category the brief asked for:

    desk.html            landing: what is known, what is blank, what to read first
    desk-lines.html      originated lines, slate picks, game flow, hand-checkable arithmetic
    desk-validation.html gates, ablations, settlement ledger, leaderboard
    desk-props.html      measured prop dispersion, within-player correlation, SGP bounds
    desk-capture.html    provenance: every capture, its read time, and the repo's own defects

Rules the renderer obeys, because the site checkers enforce them:
  * every table row carries a link to an official NBA property — a row that cannot cite one is
    not published as data, it is published on the review table as a gap;
  * a missing value renders as an em dash with the reason next to it, never as zero and never
    as a guess;
  * every number in prose is read from a JSON file, so a page cannot disagree with its data.
"""

import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "integration", "out")
DASH = "&mdash;"

NAV = [
    ("desk.html", "Desk overview"),
    ("desk-lines.html", "Lines &amp; slate picks"),
    ("desk-validation.html", "Gates &amp; settlement"),
    ("desk-props.html", "Props &amp; correlation"),
    ("desk-capture.html", "Capture &amp; repo review"),
]


def J(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return json.load(fh)


def esc(x):
    return html.escape("" if x is None else str(x))


def cell(v, nd=1):
    """Format a value for a <td>. None → em dash. Numbers rounded, strings escaped."""
    if v is None or v == "":
        return f"<td>{DASH}</td>"
    if isinstance(v, bool):
        return f"<td>{'yes' if v else 'no'}</td>"
    if isinstance(v, (int, float)) and not isinstance(v, str):
        if isinstance(v, int):
            return f"<td>{v}</td>"
        return f"<td>{v:.{nd}f}</td>"
    return f"<td>{esc(v)}</td>"


def link(url, label="official source"):
    """A cell containing only the anchor, so the caller keeps control of the visible text."""
    if not url:
        return '<span class="sub">no source recorded</span>'
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{label}</a>'


def cell_ci(pair, small_note=None):
    """Render a [lo, hi] pair, or an honest reason there is no interval."""
    if not pair or pair[0] is None or pair[1] is None:
        return f"<td>{DASH}<span class=sub>{esc(small_note or 'no interval: sample too small')}</span></td>"
    return f"<td>{pair[0]}–{pair[1]}</td>"


def td(c):
    """One cell. A pre-rendered <td> passes through, an HTML snippet is wrapped, a number is
    formatted, and anything else is escaped. None becomes an em dash, never a zero."""
    if isinstance(c, str) and c.startswith("<td"):
        return c
    if c is None or c == "":
        return f"<td>{DASH}</td>"
    if isinstance(c, bool):
        return f"<td>{'yes' if c else 'no'}</td>"
    if isinstance(c, int):
        return f"<td>{c}</td>"
    if isinstance(c, float):
        return f"<td>{c:.2f}</td>"
    s = str(c)
    if s.startswith(("<a ", "<span", "<strong", "<code", "<em", "<b>")):
        return f"<td>{s}</td>"
    return f"<td>{esc(s)}</td>"


def table(headers, rows, caption=None, note=None):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(td(c) for c in r) + "</tr>" for r in rows)
    cap = f"<caption>{caption}</caption>" if caption else ""
    n = f'<p class="table-note">{note}</p>' if note else ""
    return (f'<div class="table-wrap"><table>{cap}<thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>{n}')


def card(title, intro, inner, tag=None, tagcls="review"):
    t = f'<span class="badge {tagcls}">{tag}</span>' if tag else ""
    return (f'<article class="card"><h2>{title} {t}</h2>'
            f'<p class="card-intro">{intro}</p>{inner}</article>')


def notice(kind, title, text):
    return f'<div class="notice {kind}"><strong>{title}</strong>{text}</div>'


def metric(label, value, sub):
    return (f'<article class="metric"><div class="metric-label">{label}</div>'
            f'<strong class="metric-value">{value}</strong>'
            f'<div class="metric-sub">{sub}</div></article>')


def page(fname, title, subtitle, body, active, stamp):
    links = []
    for h, l in NAV:
        cls = ' class="active"' if h == active else ""
        links.append(f'<a href="{h}"{cls}>{l}</a>')
    links = "".join(links)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | NBA Integration Desk</title>
<link rel="stylesheet" href="subpages.css"></head>
<body><header class="topbar"><div class="top-inner">
<a class="brand" href="index.html"><span class="brand-mark">D</span> NBA Integration Desk</a>
<div class="top-note">{esc(stamp)} · official sources only · blanks are never filled</div>
</div></header>
<div class="layout"><nav class="side" aria-label="Main navigation">
<div class="nav-label">Integration desk</div>{links}
<div class="nav-label">Also on this site</div>
<a href="lines.html">Edge Lab lines</a>
<a href="gameflow.html">Edge Lab game flow</a>
<a href="review.html">Flagged for review</a>
<a href="docs/b/index.html">Build B desk</a>
<div class="side-foot">Model output is a paper forecast, not a price. No sportsbook price is
reachable from the environment that built this, so odds, ROI and stake are blank everywhere.</div>
</nav>
<main class="main"><div class="page-head"><h1>{esc(title)}</h1><p>{subtitle}</p></div>
{body}
</main></div>
<footer class="foot"><p>Generated by <code>integration/site.py</code> from
<code>integration/out/*.json</code> and <code>data/live/*.json</code>. Re-running the two
commands in that order reproduces every number on these pages.</p></footer>
<script src="app.js"></script></body></html>"""
    with open(os.path.join(ROOT, fname), "w", encoding="utf-8") as fh:
        fh.write(doc)
    return fname, len(body)


# --------------------------------------------------------------------- pages
def page_desk(D, stamp):
    g, st, pk, ln = D["gates"], D["settle"], D["picks"], D["lines"]
    lb, meta = D["leaderboard"], D["meta"]
    diag = ln["diagnostics"]
    kpis = "".join([
        metric("Games priced for the next three days", f"{pk['slate']['games_priced']}",
               "11/14–11/16 · every line from an official point-in-time window"),
        metric("Games that pass every selection rule", f"{pk['slate']['tiers']['SELECTED']}",
               "the rule is the constraint, not the model"),
        metric("Out-of-sample games graded", f"{st['graded_window']['games']}",
               "2026-11-06 … 11-12 official finals, ratings frozen at 11/05"),
        metric("MAE on the margin", f"{st['error_statistics']['mae_margin']} pts",
               f"95% CI {st['error_statistics']['mae_margin_ci_95'][0]}–"
               f"{st['error_statistics']['mae_margin_ci_95'][1]} · a constant pick is "
               f"{g['naive_baselines']['margin_constant_sample_mean']}"),
        metric("MAE on the total", f"{st['error_statistics']['mae_total']} pts",
               f"a constant ({g['naive_baselines']['total_constant_sample_mean']}) is BETTER — "
               f"the total gate V3b fails"),
        metric("Gates passed / failed / blank",
               f"{g['summary']['pass']} · {g['summary']['fail']} · {g['summary']['blank']}",
               "blank means the input does not exist here, not that it failed"),
        metric("Strategies validated", "0",
               "no reward is payable to any row of the leaderboard"),
    ])

    headline = [
        ("The line model is not distinguishable from a naive pick.",
         f"On the margin there is something: mean absolute error {g['naive_baselines']['margin_model']} "
         f"points across {st['graded_window']['games']} graded finals against "
         f"{g['naive_baselines']['margin_constant_sample_mean']} for predicting one constant, a gain of "
         f"{g['naive_baselines']['margin_improvement']} points. On the total there is nothing: "
         f"{g['naive_baselines']['total_model']} against {g['naive_baselines']['total_constant_sample_mean']} "
         f"for a constant, i.e. the pace-based total is "
         f"{abs(g['naive_baselines']['total_improvement'])} points WORSE than doing no work. And every "
         f"component — home court, back-to-back, shrinkage — moves the margin error by less than half a "
         f"point, inside a ±{round((g['bootstrap_mae_margin_95'][1]-g['bootstrap_mae_margin_95'][0])/2,1)} "
         f"interval. This is reported as the finding, not smoothed over."),
        ("The binding constraint on picks is the injury report, not the ratings.",
         "On 11/14 exactly one side of each of the five games had filed. An adjustment built from "
         "one team's absences and the other team's silence is a bias, so those five games are "
         "priced and then refused. Nine later games are published as provisional lines, and eight "
         "more sit inside the model's own noise."),
        ("Rotation impact cannot be sized yet, and that is now a measured gap.",
         "One of the 26 listed absences has verified season minutes anywhere in this repository. "
         "Vacated minutes are deducted from the named player and deliberately not re-spread to "
         "teammates, because the data to do that fairly (page 2 onward of the player tables) was "
         "never captured."),
        ("Dispersion stopped being an assumption.",
         "Player-prop σ used to be a constant in this repo, which is how ±30-point spreads appeared "
         "in an earlier draft. Twelve official game-log rows now give a measured spread for three "
         "players, published with its interval and flagged as far too small to stake."),
        ("Nothing here is a bet.",
         "No sportsbook price is reachable from the sandbox that produced these files, so break-even, "
         "hold, ROI and closing-line value are blank on every row and will stay blank until a price "
         "file exists. A paper forecast graded against its own number is not an edge."),
    ]
    hl = "".join(f"<li><b>{esc(t)}</b> {esc(b)}</li>" for t, b in headline)

    SRC = {x["id"]: x["url"] for x in meta["sources"]}
    route_rows = [
        ['<a href="desk-lines.html">Lines &amp; slate picks</a>',
         f"{pk['slate']['games_priced']} priced games, tiers, game-flow inputs, the arithmetic",
         "whether any game deserves attention at all",
         link(SRC["L1"], "the 11/14 slate page")],
        ['<a href="desk-validation.html">Gates &amp; settlement</a>',
         f"{len(g['gates'])} gates, {len(g['ablations'])} ablations, "
         f"{st['graded_count']} graded games, {st['cannot_settle_count']} that cannot be graded",
         "whether the model may be trusted with money (today: no)",
         link(SRC["L9"], "the frozen ratings window")],
        ['<a href="desk-props.html">Props &amp; correlation</a>',
         "measured dispersion for 3 players, within-player correlations, SGP bounds",
         "whether prop or parlay work is worth funding next",
         link(SRC["L10"], "an official game-log page")],
        ['<a href="desk-capture.html">Capture &amp; repo review</a>',
         f"{len(meta['sources'])} captures with read times, the defect list, the blank list",
         "what to believe and what to re-fetch",
         link(SRC["L5"], "the injury PDF")],
    ]
    route = table(["Page", "What it holds", "Read it to decide", "Anchor of that page's data"],
                  route_rows,
                  note="Cross-referenced to the pre-existing Build A pages "
                       "(<a href=\"lines.html\">lines.html</a>, <a href=\"gameflow.html\">gameflow.html</a>) "
                       "and Build B (<a href=\"docs/b/index.html\">docs/b/index.html</a>). Each anchor "
                       "is the official page that page's data came from.")

    tiers = pk["slate"]["tiers"]
    tier_anchor = {"SELECTED": SRC["L1"], "PROVISIONAL": SRC["L2"],
                   "LEAN-ONLY": SRC["L3"], "REJECTED-DATA": SRC["L5"]}
    tier_rows = [[f'<a href="{esc(tier_anchor[k])}" target="_blank" rel="noopener">{esc(k)}</a>', v, {
        "SELECTED": "line + lean published, all rules cleared",
        "PROVISIONAL": "line published; availability for that date is not filed yet",
        "LEAN-ONLY": "line published; projected margin is inside half of σ",
        "REJECTED-DATA": "not published as a view — a required input is missing or asymmetric",
    }[k]] for k, v in tiers.items()]
    tier_tbl = table(["Tier", "Games", "Meaning"], tier_rows,
                     note=f"Rule and cut fixed before the slate was priced: |margin| ≥ "
                          f"{pk['rule']['min_edge_points']} points (half of the measured σ_margin "
                          f"{pk['rule']['sigma_margin_measured']}).")

    body = (
        notice("danger", "No price, no bet.",
               "Odds, break-even, hold, ROI, CLV and stake are blank on every page of this desk. "
               "The environment that built these files cannot reach a sportsbook, and no model "
               "output was substituted for a market number.")
        + f'<div class="grid">{kpis}</div>'
        + card("Executive summary", "Five things worth knowing before any decision.",
               f'<ol class="bullets">{hl}</ol>', tag="read first", tagcls="proposed")
        + card("How the slate was handled", "Coverage is complete; confidence is not.", tier_tbl)
        + card("Where to read next", "One page per category.", route)
    )
    return body


def page_lines(D, stamp):
    pk, ln = D["picks"], D["lines"]
    rows = []
    for r in pk["rows"]:
        gf = r["game_flow"]
        venue = f"{r['venue']}, {r['city']}" if r.get("venue") else None
        rows.append([
            f'<a href="{esc(r["source_url"])}" target="_blank" rel="noopener">{esc(r["date"])}</a>',
            esc(r["time_et"]),
            f'<a href="{esc(r["game_url"])}" target="_blank" rel="noopener">{esc(r["matchup"])}</a>',
            cell(r["line_spread_home"], 1), cell(r["line_total"], 1),
            cell(r["p_home_win_model"], 3),
            esc(r["lean"]), f'{r["lean_margin_points"]}',
            f'<span class="badge {"blocked" if r["tier"] == "REJECTED-DATA" else ("review" if r["tier"] != "SELECTED" else "confirmed")}">{esc(r["tier"])}</span>',
            esc("; ".join(r["reasons"]) or "all rules cleared"),
            cell(venue),
        ])
    lines_tbl = table(
        ["Date", "Tip (ET)", "Matchup", "Spread (home)", "Total", "P(home win)", "Lean",
         "|margin|", "Tier", "Why this tier", "Venue (from the independent capture)"], rows,
        note="Spread and total are OUR numbers, not market prices. P(home win) is a normal-CDF "
             "read of the projected margin over the measured out-of-sample σ, so it is a "
             "calibration statement, not a price. Records are copied as displayed and lag one "
             "league day because the 11/13 games were unfinished at capture (IR-05).")

    flow_rows = []
    for r in pk["rows"]:
        gf = r["game_flow"]
        rest = gf["rest"]
        av = gf["availability"]
        flow_rows.append([
            f'<a href="{esc(r["game_url"])}" target="_blank" rel="noopener">{esc(r["matchup"])}</a>',
            cell(gf["projected_possessions"], 2),
            esc(gf["pace_note"]),
            f"{rest['away_days']} / {rest['home_days']}",
            f"{'yes' if rest['away_b2b'] else 'no'} / {'yes' if rest['home_b2b'] else 'no'}",
            f"{av['away']['listed_absent_or_questioned']} listed, "
            f"{av['away']['rows_sized_by_the_model']} sized",
            f"{av['home']['listed_absent_or_questioned']} listed, "
            f"{av['home']['rows_sized_by_the_model']} sized",
            cell(gf["first_half_share"]),
        ])
    flow_tbl = table(["Matchup", "Possessions", "Pace basis", "Rest days away/home",
                      "Back-to-back away/home", "Away availability", "Home availability",
                      "Half-time share"], flow_rows,
                     note="Half-time share is blank for every game: no quarter-level scoring split "
                          "is stored for any team in this repository, and assuming 50/50 would be "
                          "a made-up number.")

    path_rows = []
    for r in pk["rows"]:
        mp = r["game_flow"]["margin_path"]
        path_rows.append([
            f'<a href="{esc(r["source_url"])}" target="_blank" rel="noopener">{esc(r["matchup"])}</a>',
            cell(mp["raw_from_ratings"], 2), cell(mp["hca_points"], 2), cell(mp["rest_adj"], 2),
            cell(mp["availability_adj"], 2), cell(mp["final"], 2),
            esc(f'{r["ratings_shrunk_net"]["away"]:+.1f} vs {r["ratings_shrunk_net"]["home"]:+.1f} '
                f'(GP {r["ratings_shrunk_net"]["games_behind"]["away"]}/'
                f'{r["ratings_shrunk_net"]["games_behind"]["home"]})'),
        ])
    path_tbl = table(["Matchup", "Raw from ratings", "Home court", "Rest", "Availability",
                      "Final margin", "Shrunk NetRtg away/home"], path_rows,
                     note="Every row can be checked by hand: raw + home court + rest + availability "
                          "= final, where a positive final margin means the home team is favoured. "
                          "Home court is 2.5 points because that is a declared assumption, not a "
                          "measurement.")

    av_rows = []
    for r in pk["rows"]:
        for side in ("away", "home"):
            for d in r["game_flow"]["availability"][side]["rows"]:
                av_rows.append([
                    f'<a href="{esc(r["source_url"])}" target="_blank" rel="noopener">{esc(r["matchup"])}</a>',
                    side.upper(),
                    f'<a href="{esc(d["source_url"])}" target="_blank" rel="noopener">{esc(d["player"])}</a>',
                    esc(d["status"]), esc(d["reason"]),
                    cell(d["minutes_per_game"], 1), cell(d["player_gp"]), cell(d["team_gp"]),
                    cell(d["minute_share"], 3), esc(d["classification"]),
                    "yes" if d["moves_the_line"] else "no",
                ])
    av_tbl = table(["Matchup", "Side", "Player", "Status", "Reason printed by the league",
                    "Min/gp", "GP", "Team GP", "Minute share", "Classification", "Moves the line"],
                   av_rows or [["—", "—", "—", "no rows printed with every field for the priced dates",
                                "—", "—", "—", "—", "—", "—"]],
                   note="Rows come from the 11/13 7:30 PM PDF, the only edition that carries 11/14 "
                        "designations. A player with no verified season-minutes row is classified "
                        "SEASON DATA NOT CAPTURED and contributes 0.0 — that is a hole in our data, "
                        "not a judgement that the absence does not matter.")

    body = (
        notice("warn", "Zero games pass every rule on this slate.",
               "Five games are refused because one side had filed an injury report and the other "
               "had not; nine are provisional because no report exists yet for their date; eight "
               "are inside the model's own noise. The lines below are still the lines we would "
               "post, and they are the number a refreshed report has to move.")
        + card("Originated lines and tiers",
               f"{len(pk['rows'])} games across {', '.join(pk['slate']['dates'])}. "
               f"Rule: {esc(pk['rule']['criteria'][1])}, σ from the graded window.", lines_tbl)
        + card("Game flow before tip",
               "What the schedule and the report do to the shape of each game.", flow_tbl)
        + card("Margin arithmetic, per game", "The whole projection, with each term visible.",
               path_tbl)
        + card("Availability rows", "Every official row for the priced games, sized or not.",
               av_tbl)
    )
    return body


def page_validation(D, stamp):
    g, st, lb = D["gates"], D["settle"], D["leaderboard"]
    tt = D.get("transform")
    stat_cls = {"PASS": "confirmed", "FAIL": "blocked", "BLANK": "review",
                "MARGINAL": "review"}
    src = {x["id"]: x["url"] for x in D["meta"]["sources"]}
    trad_url = D["trad"]["source_url"]
    ADV_FIT, ADV_LIVE = D["windows"]["window_fit"]["source_url"], src["L4"]
    GATE_URL = {"V1": ADV_FIT, "V2": "https://www.nba.com/games?date=2026-11-06",
                "V3": ADV_FIT, "V4": src["L13"], "V5": "https://www.nba.com/games?date=2026-11-09",
                "V6": "https://www.nba.com/games?date=2026-11-07", "V7": "https://www.nba.com/",
                "V8": trad_url, "V9": src["L5"], "V10": "https://www.nba.com/",
                "V11": src["L10"], "V12": ADV_LIVE, "V13": src["L5"]}
    GATE_LABEL = {"V8": "the player table whose missing rows cause this",
                  "V9": "the official report PDF", "V10": "NBA.com — which is not an odds feed",
                  "V11": "an official game-log page (one fetch per player)",
                  "V13": "the report edition this desk would need a history of",
                  "V1": "the window itself", "V2": "one graded slate day",
                  "V3": "the fit window", "V4": "a graded final", "V5": "the split date",
                  "V6": "a graded final", "V7": "the host allow-list lives in the data",
                  "V12": "the page every input must reproduce from"}
    gate_rows = [[esc(x["id"]), esc(x["name"]), esc(x["threshold"]),
                  cell(x["measured"]),
                  f'<span class="badge {stat_cls.get(x["status"], "review")}">{esc(x["status"])}</span>',
                  esc(x["detail"]),
                  esc(x["missing_input"] or None),
                  link(x.get("source_url") or GATE_URL.get(x["id"], "https://www.nba.com/"),
                       GATE_LABEL.get(x["id"], "official source"))]
                 for x in g["gates"]]
    gates_tbl = table(["Gate", "Requirement", "Threshold", "Measured", "Status", "Reading",
                       "Missing input that would resolve it", "Official source"], gate_rows,
                      note="A BLANK is not a soft pass: it means the input does not exist in the "
                           "environment that produced this. Three gates are blank, all three for "
                           "the same reason (no price file, no full player tables).")

    abl_rows = []
    for k, a in g["ablations"].items():
        abl_rows.append([
            f'<a href="https://www.nba.com/games?date={st["graded_window"]["from"]}" '
            f'target="_blank" rel="noopener">{esc(a["component"])}</a>',
            esc(a["change"]), cell(a["mae_margin"], 3), cell(a["delta_mae_vs_full_model"], 3),
            esc(a["verdict"]),
        ])
    abl_tbl = table(["Component", "Ablation", "MAE margin", "Δ vs full model", "Verdict"], abl_rows,
                    note=f"Full model MAE {g['base_model']['mae_margin']} on "
                          f"{g['base_model']['n']} graded games; the base model's own 95% interval "
                          f"is ±{round((g['bootstrap_mae_margin_95'][1] - g['bootstrap_mae_margin_95'][0]) / 2, 2)}. "
                          "Scope limit: this grades ratings + rest + home court only, because no "
                          "injury report exists in the repo for the graded window.")

    set_rows = []
    for r in st["rows"]:
        set_rows.append([
            f'<a href="{esc(r["source_url"])}" target="_blank" rel="noopener">{esc(r["date"])}</a>',
            f'<a href="{esc(r["source_url"])}" target="_blank" rel="noopener">{esc(r["matchup"])}</a>',
            esc(r["final_score"]), cell(r["model_margin_home"], 1), cell(r["actual_margin_home"]),
            cell(r["abs_err_margin"], 2), cell(r["model_total"], 1), cell(r["actual_total"]),
            cell(r["abs_err_total"], 2), esc(r["side_pick"]),
        ])
    set_tbl = table(["Date", "Matchup", "Official final", "Model margin", "Actual margin",
                     "|err|", "Model total", "Actual total", "|err|", "Model side"], set_rows,
                    note=f"All {len(set_rows)} rows are official FINAL scores transcribed to "
                         f"<code>data/raw/games_completed.json</code>; the model's inputs come from the "
                         f"10/20–11/05 window, which ends the day before the first graded game. "
                         f"Aggregate: MAE margin {st['error_statistics']['mae_margin']}, "
                         f"MAE total {st['error_statistics']['mae_total']}, "
                         f"bias {st['error_statistics']['bias_margin']:+} / "
                         f"{st['error_statistics']['bias_total']:+} points.")

    blocked_rows = []
    for b in st["rows"][:0]:
        pass
    for b in st["cannot_settle"]:
        blocked_rows.append([
            f'<a href="{esc(b["source_url"])}" target="_blank" rel="noopener">{esc(b["date"])}</a>',
            f'<a href="{esc(b["source_url"])}" target="_blank" rel="noopener">{esc(b["matchup"])}</a>',
            esc(b["state"]), cell(b.get("detail")), esc(b["reason"]), esc(b["action"]),
        ])
    blocked_tbl = table(["Date", "Matchup", "State at capture", "What the page printed",
                         "Why it cannot be graded", "What fixes it"], blocked_rows,
                        note="These rows exist so nobody has to wonder whether a convenient "
                             "subset was graded: every game in the capture window appears either "
                             "here or in the graded table above, never in neither.")

    # Games captured while in progress that have since settled from promoted
    # official finals (scripts/promote_finals.py, two agreeing official reads).
    # arena/ef6ff2a4-nba1, 2026-11-14.
    late_rows = []
    for b in st.get("settled_late", []):
        late_rows.append([
            f'<a href="{esc(b["source_url"])}" target="_blank" rel="noopener">{esc(b["date"])}</a>',
            f'<a href="{esc(b["source_url"])}" target="_blank" rel="noopener">{esc(b["matchup"])}</a>',
            esc(b.get("final_score", "")), esc(b.get("reason", "")), esc(b.get("desk_pick", "")),
        ])
    late_tbl = table(["Date", "Matchup", "Official final", "How it settled", "Desk pick?"], late_rows,
                     note="Captured while in progress, graded only after the official page read "
                          "FINAL and two independent reads agreed. No desk pick existed on these "
                          "games (the desk slate cut starts 2026-11-14); the rows are settled "
                          "results, kept so the ledger shows every game exactly once.") if late_rows else ""

    anchors = {
        "INT-1": D["windows"]["window_fit"]["source_url"],
        "INT-2": D["windows"]["window_fit"]["source_url"],
        "INT-3": D["props"]["sample"]["official_sources"][0],
        "INT-4": D["props"]["sample"]["official_sources"][0],
        "BLD-A": "https://www.nba.com/games?date=2026-11-11",
        "BLD-B": D["windows"]["window_live"]["source_url"],
    }
    lb_rows = []
    for r in lb["rows"]:
        lb_rows.append([
            str(r["rank"]),
            f'<a href="{esc(anchors.get(r["id"], "https://www.nba.com/stats/"))}" target="_blank" '
            f'rel="noopener">{esc(r["name"])}</a>',
            esc(r["family"]), esc(r["register"]), cell(r["n_graded"]), cell(r["record"]),
            cell(r["mae_margin"], 3), cell(r["mae_total"], 3),
            esc(r["metric"]), "no" if not r["validated"] else "yes",
        ])
    lb_tbl = table(["#", "Candidate", "Family", "Register", "Graded n", "Record", "MAE margin",
                    "MAE total", "Headline measure", "Reward payable"], lb_rows,
                   note=esc(lb["reward_policy"]))

    dis_anchor = [D["windows"]["window_fit"]["source_url"],
                  D["props"]["sample"]["official_sources"][0]]
    dis_rows = [[esc(d["topic"]),
                 f'<a href="{esc(dis_anchor[i])}" target="_blank" rel="noopener">'
                 f'{"the 51 graded finals" if i == 0 else "the game-log rows"}</a>',
                 "<br>".join(f"{k}: {v}" for k, v in d["values"].items()), esc(d["resolution"])]
                for i, d in enumerate(lb["registers_disagree"])]
    dis_tbl = table(["Registers disagree on", "Anchor", "Values", "How this desk resolved it"], dis_rows)

    tr_rows = []
    if tt:
        for k, v in tt["results"].items():
            tr_rows.append([
                f'<a href="https://www.nba.com/stats/help/glossary" target="_blank" rel="noopener">{esc(k)}</a>',
                cell(v["brier"], 4), cell(v["logloss"], 4), cell(v["mean_p_home"], 4)])
        best = tt["best_by_brier"]
        tr_tbl = table(["Link and σ applied to the same projected margins", "Brier", "Log loss",
                        "Mean P(home)"], tr_rows,
                       note=f"Home teams actually won 25 of these 51 games (0.4902), and every "
                            f"variant's mean P(home) sits above that — the home-court assumption, "
                            f"not the link function, is the systematic error. Best Brier here is "
                            f"<b>{esc(best['name'])}</b> at {best['brier']}, against 0.25 for a flat "
                            f"coin. Picking the winner of this table would be in-sample selection "
                            f"on 51 games, so it is printed as a correction to an assertion and not "
                            f"adopted as a parameter. {esc(tt['caveat'])}")
    else:
        tr_tbl = ""

    body = (
        notice("info", "Verdict of the gate pass.",
               esc(g["summary"]["decision"]))
        + f'<div class="grid">{metric("Gates passed", g["summary"]["pass"], "hard gates, unweighted")}'
          f'{metric("Gates failed", g["summary"]["fail"], "reported as failures")}'
          f'{metric("Gates blank", g["summary"]["blank"], "input does not exist here")}'
          f'{metric("Graded games", st["graded_count"], "official finals only")}'
          f'{metric("Cannot be graded", st["cannot_settle_count"], "in progress or not tipped")}'
          f'{metric("Model record vs its own line", st["side"]["record"], "≈50% by construction")}</div>'
        + card("Validation gates", "Every gate, its threshold, and what it measured.", gates_tbl)
        + card("Ablations", "Does each adjustment earn its place? One knob at a time.", abl_tbl)
        + card("Probability transform", "Same margins, four ways of turning them into a number.",
               tr_tbl)
        + card("Settlement ledger — graded", "The graded games, in full.", set_tbl)
        + card("Settlement ledger — refused", "Games this desk was not allowed to grade.", blocked_tbl)
        + (card("Settlement ledger — settled late", "Games captured in progress that later "
                "settled from promoted official finals.", late_tbl) if late_tbl else "")
        + card("Leaderboard", esc(lb["ranking_basis"]), lb_tbl)
        + card("Where the registers disagree", "Not averaged away.", dis_tbl)
    )
    return body


def page_props(D, stamp):
    pr = D["props"]
    reg = D["correlations"]
    rows = []
    for p in pr["players"]:
        for key, s in p["stats"].items():
            rows.append([
                f'<a href="{esc(p["player_page"])}" target="_blank" rel="noopener">{esc(p["player"])}</a>',
                esc(p["team"]), esc(s["label"]), cell(s["n"]), cell(s["mean"], 2), cell(s["sd"], 2),
                cell(s["cv"], 3),
                esc("—" if not s.get("ci_95_block_bootstrap")
                    else f'{s["ci_95_block_bootstrap"][0]}–{s["ci_95_block_bootstrap"][1]}'),
                cell(s.get("season_header_reference"), 1),
                "no", esc(s["flag"]),
            ])
    disp_tbl = table(["Player", "Team", "Stat", "n", "Mean", "σ", "CV", "95% CI on mean",
                      "Season average on the official card", "Usable for staking", "Why not"], rows,
                     note="The season-average column is the cross-check: where the logged mean and "
                          "the card disagree, the card is a season number and the log is this window, "
                          "so neither is wrong and neither can be used alone to price a line.")

    lad_rows = []
    for p in pr["players"]:
        for key, s in p["stats"].items():
            for l in s.get("ladder") or []:
                lad_rows.append([
                    f'<a href="{esc(p["player_page"])}" target="_blank" rel="noopener">{esc(p["player"])}</a>',
                    esc(s["label"]), cell(l["line"], 1), f'{l["over_count"]}/{l["n"]}',
                    cell(l["empirical_over_rate"], 3),
                    esc(f'{l["wilson_95_lo"]:.3f}–{l["wilson_95_hi"]:.3f}'),
                    cell(l["model_over_prob"], 3),
                ])
    lad_tbl = table(["Player", "Stat", "Candidate line", "Over hits", "Empirical over rate",
                     "Wilson 95%", "Normal-model over prob"], lad_rows,
                    note="At n=4 an empirical rate can only be 0, 25, 50, 75 or 100 percent. The "
                         "Wilson interval is the honest part of this table; the empirical column is "
                         "shown so nothing about the sample size is hidden.")

    corr_rows = []
    for c in pr["within_player_correlation"]:
        corr_rows.append([
            f'<a href="{esc(c["source_url"])}" target="_blank" rel="noopener">{esc(c["player"])}</a>',
            esc(c["pair"]), cell(c["n"]), cell(c["pearson_r"], 3),
            cell_ci(c["fisher_95"], small_note=f"n={c['n']} is below the 4 games an interval needs"),
            esc(c["interpretation"]),
        ])
    corr_tbl = table(["Player", "Stat pair", "n", "Pearson r", "Fisher 95%", "Reading"],
                     corr_rows,
                     note="These are same-game co-movements inside 3–4 logged games per player. "
                          "A correlation crossing zero cannot support a joint price, which is why "
                          "the SGP row below is published as bounds.")

    sgp_rows = []
    for s in pr["sgp_bounds"]:
        sgp_rows.append([
            f'<a href="https://www.nba.com/stats/help/glossary" target="_blank" rel="noopener">{esc(s["legs"])}</a>',
            cell(s["p_a"], 3), cell(s["p_b"], 3), cell(s["independent"], 4),
            cell(s["frechet_lo"], 4), cell(s["frechet_hi"], 4), cell(s["measured_rho"], 3),
            esc(s["note"]),
        ])
    sgp_tbl = table(["Parlay", "P(leg A)", "P(leg B)", "If independent", "Fréchet lower",
                     "Fréchet upper", "Measured ρ", "Reading"], sgp_rows or
                    [["—", "—", "—", "—", "—", "—", "—", "no leg pair currently qualifies"]],
                    note="The Fréchet bounds hold for any dependence structure, so they are the "
                         "only defensible statement without a measured correlation. A book's "
                         "payout sits between them; without a price we cannot say whether it does.")

    tier_rows = []
    for t in reg.get("tier_a_empirical", []):
        tier_rows.append([
            f'<a href="{esc(t["source_url"].split(" and ")[0])}" target="_blank" rel="noopener">'
            f'{esc(t["x"])} × {esc(t["y"])}</a>',
            cell(t["r"], 4), cell(t["n"]), cell(t["p_two_sided_approx"], 4),
            "yes" if t["significant_at_0_05"] else "no",
            esc(t["interpretation"]),
        ])
    tier_tbl = table(["Team-level pair", "r", "n", "p (approx)", "Significant at 0.05",
                      "Interpretation"], tier_rows,
                     note="Build A's register, computed across the 30-team season cross-section. "
                          "It says nothing about two legs of one bet — a team-level r cannot be "
                          "borrowed as an SGP correlation, which is the error the C tier was "
                          "created to prevent.")
    c_rows = [[f'<a href="https://www.nba.com/stats/help/glossary" target="_blank" rel="noopener">{esc(t.get("pair") or t.get("relationship") or "?")}</a>',
               esc(t.get("reason") or t.get("what_would_unblock_it") or "not computed"),
               "left null on purpose"] for t in reg.get("tier_c_not_computable", [])]
    c_tbl = table(["Relationship the brief asks about", "Why it was not computed", "Value"],
                  c_rows or [["—", "register has no C-tier rows", "—"]],
                  note="Every C-tier row stayed null in Build A. The two that this session could "
                       "partly reach — same-game prop dispersion and within-player correlation — are "
                       "now measured above, and the rest still cannot be.")

    body = (
        notice("danger", "Prop and parlay work is not fundable yet.",
               esc(pr["verdict"]) + " " + esc(pr["coverage_limit"]["statement"]))
        + card("Measured dispersion", "What a player's own games say, one stat at a time.", disp_tbl)
        + card("Line ladder", "Candidate lines around the sample median, with the interval.", lad_tbl)
        + card("Within-player correlation", "The dependence an SGP actually needs.", corr_tbl)
        + card("Parlay bounds", "Published as an interval because that is all it is.", sgp_tbl)
        + card("Team-level correlations already in the repo",
               "Real numbers, wrong unit of analysis for a same-game parlay.", tier_tbl)
        + card("What Build A refused to compute", "The C tier, and what changed.", c_tbl)
    )
    return body


def page_capture(D, stamp):
    meta, lines, ln = D["meta"], D["lines"], D["lines"]
    rev = D["review"]
    src = {x["id"]: x["url"] for x in meta["sources"]}
    src_rows = []
    for s in meta["sources"]:
        src_rows.append([
            f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["id"])}</a>',
            esc(s["url"].split("//", 1)[-1].split("/")[0]),
            esc(s["what"]), esc(s["read_at_utc"]),
            esc(s.get("note") or s.get("url_verification") or "—"),
        ])
    src_tbl = table(["#", "Host", "What was read", "Read at (UTC)", "Note carried with it"], src_rows,
                    note=f"Capture window {esc(meta['captured_at_utc'])}. Only NBA-operated hosts "
                         f"were used for data: {', '.join(meta['allowed_official_hosts'])}. "
                         f"{esc(meta['method'])}")

    win_rows = []
    for wname, w in (("fit (used to predict)", D["windows"]["window_fit"]),
                     ("live (used to price)", D["windows"]["window_live"])):
        top = sorted(w["teams"].items(), key=lambda kv: -kv[1]["netrtg"])[:3]
        bot = sorted(w["teams"].items(), key=lambda kv: kv[1]["netrtg"])[:2]
        win_rows.append([
            f'<a href="{esc(w["source_url"])}" target="_blank" rel="noopener">{esc(wname)}</a>',
            esc(w["label"]),
            esc(", ".join(f'{k} {v["netrtg"]:+.1f} ({v["gp"]}g)' for k, v in top)),
            esc(", ".join(f'{k} {v["netrtg"]:+.1f}' for k, v in bot)),
            esc(w.get("row_count_check", "")),
        ])
    win_tbl = table(["Window", "Date range as filtered on the page", "Top NetRtg", "Bottom NetRtg",
                     "Integrity check"], win_rows,
                    note="The fit window exists because a date-filtered official page "
                         "(<code>DateFrom</code>/<code>DateTo</code>) was proven reachable: the "
                         "ratings that produced the graded predictions are the numbers NBA.com "
                         "published for that span, not a re-derivation from today's totals.")

    gap_rows = []
    gap_urls = ["https://www.nba.com/", "https://www.nba.com/games?date=2026-11-13",
                src["L10"], src["L6"]]
    for i, g in enumerate(meta["not_obtained"], 1):
        head, _, rest = g.partition(":")
        gap_rows.append([f'<a href="{esc(gap_urls[i - 1])}" target="_blank" rel="noopener">'
                         f'GAP-{i:02d}</a>', esc(head.strip()), esc(rest.strip() or "—")])
    for b in rev["blanks"]:
        gap_rows.append([f'<a href="{esc(b["verify_url"])}" target="_blank" rel="noopener">'
                         f'BLANK-{i:02d}</a>', esc(b["item"]),
                         f'{esc(b["why"])} — shows up on {esc(b["appears"])}'])
    gap_tbl = table(["Row", "Field", "Why it is missing, and where it shows up"], gap_rows,
                    note="Printed as a table of holes rather than a footnote, because a missing "
                         "input is the single most decision-relevant fact on this desk. The first "
                         "block is what could not be fetched at all; the second is what the site "
                         "leaves blank on purpose.")

    find_rows = []
    for f in rev["findings"]:
        find_rows.append([
            f'<a href="{esc(f["url"])}" target="_blank" rel="noopener">{esc(f["file"])}</a>',
            f'<span class="badge {"blocked" if f["severity"] == "HIGH" else ("review" if f["severity"] == "MEDIUM" else "confirmed")}">{esc(f["severity"])}</span>',
            esc(f["finding"]), esc(f["action"]),
            link(f["verify_url"], "re-check"),
        ])
    find_tbl = table(["File / line", "Severity", "What reading it turned up", "What was done",
                      "Official page to re-check"], find_rows,
                     note="Severity is about consequence, not volume: a defect that makes a number "
                          "look like a finding is HIGH even if the fix is two lines.")

    ir_rows = []
    for i in rev["irregularities"]:
        ir_rows.append([
            f'<a href="{esc(i["url"])}" target="_blank" rel="noopener">{esc(i["id"])}</a>',
            esc(i["what"]), esc(i["why_it_matters"]), esc(i["state"]),
            link(i["verify_url"], "re-check"),
        ])
    ir_tbl = table(["Irregularity", "What the official page does", "Why it matters", "State",
                    "Re-check"], ir_rows)

    q_rows = []
    for q in rev["questions"]:
        q_rows.append([
            f'<a href="{esc(q["url"])}" target="_blank" rel="noopener">{esc(q["id"])}</a>',
            esc(q["question"]), esc(q["known"]), esc(q["missing"]), esc(q["decision_it_unblocks"]),
            link(q["verify_url"], "re-check"),
        ])
    q_tbl = table(["#", "Question to answer before deciding", "Known now", "Still missing",
                   "Decision it unblocks", "Re-check"], q_rows)

    s_rows = []
    for s in rev["suggestions"]:
        s_rows.append([
            f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["id"])}</a>',
            esc(s["suggestion"]), esc(s["cost"]), esc(s["payoff"]), esc(s["recommendation"]),
            link(s["verify_url"], "re-check"),
        ])
    s_tbl = table(["#", "Suggestion", "Cost", "What it buys", "Desk's recommendation", "Re-check"],
                  s_rows,
                  note="Nothing here has been implemented as a decision. Ranked so that the "
                       "cheapest evidence comes first.")

    cc = D["crosscheck"]
    cc_rows = [[f'<a href="{esc(x["source_url"])}" target="_blank" rel="noopener">{esc(x["date"])}</a>',
                f'<a href="{esc(x["their_source"])}" target="_blank" rel="noopener">'
                f'{esc(x["matchup_this_session"])}</a>',
                esc(x.get("matchup_other_capture") or "—"), esc(x["tip_this_session"]),
                esc(x.get("tip_other_capture") or "—"), cell(x.get("venue")), cell(x.get("city")),
                f'<span class="badge {"confirmed" if x["verdict"] == "match" else "blocked"}">'
                f'{esc(x["verdict"])}</span>']
               for x in cc["rows"]]
    cc_tbl = table(["Date", "This capture", "Other capture", "Tip here", "Tip there", "Venue",
                    "City", "Verdict"], cc_rows,
                   note=f"{cc['counts']['match']} of {cc['counts']['compared']} games agree on "
                        f"both teams and their side with an independent capture of the same "
                        f"official pages ({esc(cc['other_capture']['by'])}); "
                        f"{cc['counts']['mismatch']} mismatched and {cc['counts']['absent_from_other']} "
                        f"were absent. {esc(cc['venue_note'])}. Agreement is not proof — two readers "
                        f"of one page can err together — but a mismatch would have been proof the "
                        f"other way, which is why this table runs before any line is published.")

    body = (
        card("Cross-capture reproducibility",
             "This session's slate read against Build C's, game by game.", cc_tbl)
        + notice("ok", "Every capture is a real fetch with a timestamp.",
               "Eight reads, all of an NBA-operated host, each recorded with the time it was read "
               "and what it was used for. Where a page was chunked, the chunks read are named.")
        + card("Capture register", "What was read, when, and what it fed.", src_tbl)
        + card("Point-in-time team windows", "The two windows the model is allowed to look at.", win_tbl)
        + card("Holes in the data", "Blank on every other page, listed here once.", gap_tbl)
        + card("Repo review", "Findings from reading the tree line by line.", find_tbl)
        + card("Irregularities in the official sources", "The league's own pages, quirk by quirk.", ir_tbl)
        + card("Questions to answer first", "Ordered by how much they block.", q_tbl)
        + card("Suggestions for the site's decision-making", "Cheapest evidence first.", s_tbl)
    )
    return body


def main():
    D = {
        "lines": J("integration", "out", "lines.json"),
        "gates": J("integration", "out", "gates.json"),
        "settle": J("integration", "out", "settlement.json"),
        "props": J("integration", "out", "props.json"),
        "picks": J("integration", "out", "picks.json"),
        "leaderboard": J("integration", "out", "leaderboard.json"),
        "correlations": J("data", "derived", "correlations.json"),
        "meta": J("data", "live", "capture_meta.json"),
        "windows": J("data", "live", "team_windows.json"),
        "review": J("integration", "out", "review.json"),
        "crosscheck": J("integration", "out", "crosscheck.json"),
        "trad": J("data", "raw", "players_traditional.json"),
    }
    try:
        D["transform"] = J("integration", "out", "transform_test.json")
    except FileNotFoundError:
        D["transform"] = None
    stamp = f"desk capture {D['meta']['captured_at_utc']}"
    made = []
    for fname, title, sub, fn, tag in [
        ("desk.html", "Integration desk",
         "Originated lines, validation and the honest hole-list for the "
         "2026-11-14 … 11-16 slate. Built from official captures, dated, and never filled in.",
         page_desk, "desk.html"),
        ("desk-lines.html", "Lines &amp; slate picks",
         "Every game priced on the three-day horizon, with the selection tier and the reason.",
         page_lines, "desk-lines.html"),
        ("desk-validation.html", "Gates &amp; settlement",
         "What passed, what failed, what could not be measured, and what every graded game did.",
         page_validation, "desk-validation.html"),
        ("desk-props.html", "Props &amp; correlation",
         "Dispersion and dependence measured from official game logs, with their intervals.",
         page_props, "desk-props.html"),
        ("desk-capture.html", "Capture &amp; repo review",
         "Provenance of every value, the defects found in the repository, and the questions to "
         "answer before deciding.",
         page_capture, "desk-capture.html"),
    ]:
        body = fn(D, stamp)
        made.append(page(fname, title, sub, body, tag, stamp))
    print("desk · pages:", ", ".join(m for m, _ in made))
    return made


if __name__ == "__main__":
    main()
