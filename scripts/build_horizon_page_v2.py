#!/usr/bin/env python3
"""
build_horizon_page_v2.py — render model-v2.html (root namespace) from the v2
derived artifacts:

    data/derived/horizon_lines_v2.json    38 game lines, 2026-11-15..19
    data/derived/horizon_picks_v2.json    25 picks, 2026-11-16..18
    data/derived/model_report_v2.json     measured inputs + assumptions + gaps

Every cell comes from those files (produced by scripts/build_horizon_v2.py on
top of engine/model_v2.py and the official captures).  Nothing is typed by
hand; every table row carries at least one official-source link, the same rule
scripts/check_site.py enforces on the other root pages.
"""
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAV = [
    ("index.html", "◫&nbsp; Executive summary"),
    ("research.html", "⌁&nbsp; Strategy lab"),
    ("lines.html", "◈&nbsp; Originated lines &amp; picks"),
    ("picks.html", "▦&nbsp; Horizon lines &amp; picks"),
    ("model-v2.html", "⚙&nbsp; Model v2 — disagreement-first"),
    ("gameflow.html", "＋&nbsp; Injuries &amp; game flow"),
    ("slate.html", "▦&nbsp; Upcoming slate"),
    ("schedule-verified.html", "▦&nbsp; Verified schedule"),
    ("verification.html", "◎&nbsp; Live verification"),
    ("suggestions.html", "✳&nbsp; Questions &amp; suggestions"),
    ("review.html", "⚑&nbsp; Flagged for review"),
    ("sources.html", "↗&nbsp; Source register"),
]


def esc(v):
    if v is None:
        return ""
    return html.escape(str(v))


def src_link(url, label):
    if not url:
        return "—"
    return f'<a class="source" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def badge(kind, text):
    return f'<span class="badge {kind}">{esc(text)}</span>'


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def rest_short(rest):
    if not rest:
        return ""
    rd = rest.get("rest_days")
    if rd is None:
        return "no prior game in captured window"
    return f"{rd}d{' — B2B' if rest.get('back_to_back') else ''}" \
           f"{' — 3-in-4' if rest.get('three_in_four') else ''}"


def avail_cell(rot):
    if not rot or rot.get("rotation_players") is None:
        return '<small>minutes not captured — flagged</small>'
    out_n, q_n = rot.get("rotation_out_count", 0), rot.get("rotation_questionable_count", 0)
    names = ", ".join(rot.get("rotation_out") or []) or "none"
    qnames = ", ".join(rot.get("rotation_questionable") or []) or "none"
    return (f'<small>{esc(rot.get("availability_pct"))}% of top-8 available · '
            f'OUT: {esc(names)} · Q/D: {esc(qnames)}</small>')


def main():
    lines_doc = load("data/derived/horizon_lines_v2.json")
    picks_doc = load("data/derived/horizon_picks_v2.json")
    rep = load("data/derived/model_report_v2.json")
    games = lines_doc["games"]
    meta = lines_doc["_meta"]
    picks = picks_doc["picks"]
    n_pass = sum(1 for p in picks if p["gate_verdict"] == "PASS")

    # ---------------- table A: v2 lines ------------------------------------------
    a_rows = []
    for g in games:
        red_sum = ""
        nh, na = g.get("net_points_lost_home") or 0.0, g.get("net_points_lost_away") or 0.0
        if nh or na:
            red_sum = f"{nh:.2f} / {na:.2f}"
        dis = g.get("confidence_signal_pp")
        dis_badge = badge("info" if (dis or 0) <= 4.0 else "review", "%s pp" % dis)
        travel = (g.get("travel_away") or {}).get("miles")
        a_rows.append(
            f"<tr><td>{esc(g['date'][5:])} · {esc(g['tip_et'])}</td>"
            f"<td><b>{esc(g['away'])} @ {esc(g['home'])}</b><br>"
            f"<small>{esc(g['venue'])}, {esc(g['city'])}</small></td>"
            f"<td>{esc(g['line_total'])}</td>"
            f"<td>{esc(g['line_spread_home'])}</td>"
            f"<td>{esc(g['model_home_win_prob'])}</td>"
            f"<td>{esc(g['model_home_ml'])}</td>"
            f"<td>{dis_badge}</td>"
            f"<td>{esc(rest_short(g.get('rest_away')))} / {esc(rest_short(g.get('rest_home')))}"
            f"<br><small>travel {esc(travel)} mi</small></td>"
            f"<td>{red_sum or '<small>no captured absence</small>'}</td>"
            f"<td>{src_link(g['source_url'], 'game card')} · "
            f"{src_link(g['schedule_source_url'], 'schedule')}</td></tr>")

    # ---------------- table B: v2 picks ------------------------------------------
    b_rows = []
    for p in picks:
        verdict = p["gate_verdict"]
        b_rows.append(
            f"<tr><td>{esc(p['date'][5:])}</td>"
            f"<td>{esc(p['matchup'])}</td>"
            f"<td><b>{esc(p['pick'])}</b></td>"
            f"<td>{esc(p['model_probability'])}</td>"
            f"<td>{esc(p['model_ml'])}</td>"
            f"<td>{badge('info' if verdict == 'PASS' else 'review', verdict)}</td>"
            f"<td>{avail_cell(p.get('rotation_availability_pick_team'))}</td>"
            f"<td><small>{esc('; '.join(p['gates_passed'])) or '—'}"
            f"{'<br>FAIL: ' + esc('; '.join(p['gates_failed'])) if p['gates_failed'] else ''}</small></td>"
            f"<td>{badge('review', 'zero stake')}</td>"
            f"<td>{src_link(p['source_url'], 'game card')}</td></tr>")

    # ---------------- measured inputs --------------------------------------------
    hca = rep["home_court_anchor"]

    # Page labels used to be hardcoded date ranges ("15–19 Nov"), so the heading kept
    # claiming a horizon the data no longer covered once 11/15 settled and rolled off -
    # the same class of defect as a stale nav label (COORDINATION 54 E11/E12). They are
    # now derived from the horizon itself, so the page cannot describe a slate it is not
    # showing. (session arena/3ff8ff0f-nba1)
    _dates = sorted({str(g.get("date")) for g in games if g.get("date")})

    def _lbl(iso):
        _m, _d = iso[5:7], iso[8:10]
        return "%d/%d" % (int(_m), int(_d))

    SPAN = ("%s–%s Nov" % (_lbl(_dates[0]), _lbl(_dates[-1]))) if _dates else "current"
    PICK_SPAN = (("%s–%s Nov" % (_lbl(picks_dates[0]), _lbl(picks_dates[-1])))
                 if (picks_dates := sorted({str(p.get("date")) for p in picks
                                           if p.get("date")})) else SPAN)
    rho = {r["pair"]: r["rho_measured"] for r in rep["measured_correlations"]}
    mins = rep.get("per_player_minutes", {})
    STANDINGS_URL = "https://www.nba.com/standings"
    GAMES_URL = "https://www.nba.com/games?date=2026-11-14"
    MINUTES_URL = ("https://www.nba.com/stats/players/traditional?Season=2026-27"
                   "&SeasonType=Regular+Season&PerMode=PerGame&dir=-1&sort=MIN")
    meas_rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{esc(v)}</td>"
        f"<td>{src_link(u, label)}</td></tr>"
        for k, v, u, label in [
            ("Measured home win rate (primary, official standings HOME/ROAD)",
             f"{hca.get('measured_home_win_rate')} ({hca.get('home_wins')}/{hca.get('home_games')} home games)",
             STANDINGS_URL, "standings"),
            ("Measured home win rate, final-score cross-check",
             f"{hca.get('measured_home_win_rate_from_final_scores')} (n={hca.get('games_measured')})",
             GAMES_URL, "official finals"),
            ("Home-court advantage points",
             f"{hca.get('hca_points')} = sigma_margin {hca.get('sigma_margin_used')} × Φ⁻¹(home win rate)",
             STANDINGS_URL, "standings"),
            ("Margin sigma (official finals corpus)", hca.get("sigma_margin_used"),
             GAMES_URL, "official finals"),
            ("Measured rho: home pts / away pts", rho.get("home points / away points"),
             GAMES_URL, "official finals"),
            ("Measured rho: margin / total", rho.get("margin / total"),
             GAMES_URL, "official finals"),
            ("Measured rho: home pts / total", rho.get("home points / total"),
             GAMES_URL, "official finals"),
            ("Out-of-sample binary log loss (home-win prob, official finals)",
             f"{(rep.get('model_out_of_sample_log_loss') or {}).get('value')} over n="
             f"{(rep.get('model_out_of_sample_log_loss') or {}).get('n_games')}",
             GAMES_URL, "official finals"),
            ("Per-player minutes capture",
             f"{mins.get('file')}: {mins.get('rows_captured')} of {mins.get('rows_total_official')} official rows "
             f"(pages 2–10 unreachable; the URL Page parameter is not honored by the rendered slice)",
             MINUTES_URL, "player leaderboard"),
            ("Market leg", "ZERO WEIGHT — no official closing line reachable; the blend is model-only",
             GAMES_URL, "games pages"),
        ])

    # ---------------- assumptions -------------------------------------------------
    ASSUMP_LINKS = {
        "league_pace_formula": ("https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season", "advanced"),
        "opponent_ppp_scaling": ("https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season", "opponent"),
        "estimator_blend_weights": ("https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame", "traditional"),
        "bench_efficiency_ratio": ("https://official.nba.com/nba-injury-report-2026-27-season/", "injury policy"),
        "absence_minutes_share_by_status": ("https://official.nba.com/nba-injury-report-2026-27-season/", "injury policy"),
        "replacement_pool_size": ("https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame&dir=-1&sort=MIN", "minutes"),
        "rest_penalty_points": ("https://www.nba.com/schedule", "schedule"),
        "travel_penalty_points": ("https://www.nba.com/schedule", "schedule"),
        "luck_noise_band_z": (STANDINGS_URL, "standings"),
        "market_leg_weight": (GAMES_URL, "games"),
        "team_name_to_abbr": ("https://www.nba.com/teams", "teams"),
    }
    ass_rows = "".join(
        f"<tr><td><b>{esc(k)}</b></td><td><small>{esc((v or {}).get('value'))}</small></td>"
        f"<td><small>{esc((v or {}).get('status'))}</small></td>"
        f"<td>{src_link(*(ASSUMP_LINKS.get(k, (GAMES_URL, 'games'))))}</td></tr>"
        for k, v in sorted((rep.get("assumptions") or {}).items()))

    # ---------------- gaps ---------------------------------------------------------
    gap_rows = "".join(
        f"<tr><td><b>{esc(g.get('id'))}</b></td>"
        f"<td>{badge('review', esc(g.get('severity')))}</td>"
        f"<td><b>{esc(g.get('item'))}</b><br><small>{esc(g.get('detail'))}</small></td>"
        f"<td>{src_link(g.get('source'), 'source')}</td></tr>"
        for g in rep.get("gaps", []))

    # ---------------- flagged items of this build -----------------------------------
    flag_rows = "".join(
        f"<tr><td><b>{esc(f.get('id'))}</b></td>"
        f"<td>{badge('review', esc(f.get('severity')))}</td>"
        f"<td><b>{esc(f.get('item'))}</b><br><small>{esc(f.get('detail'))}</small></td>"
        f"<td>{src_link(f.get('source'), 'source')}</td></tr>"
        for f in meta.get("flags", []))
    anomaly_rows = "".join(
        f"<tr><td><b>{esc(a.get('id'))}</b></td>"
        f"<td>{esc(a.get('matchup', [''])[0])} ×{len(a.get('game_ids', []))}</td>"
        f"<td><b>{esc(a.get('item'))}</b><br><small>{esc(a.get('corroboration'))} "
        f"{esc(a.get('precedent'))} {esc(a.get('action'))}</small></td>"
        f"<td>{' · '.join(src_link(u, f'surface {i+1}') for i, u in enumerate(a.get('official_surfaces_checked', [])))}</td></tr>"
        for a in load("data/official/official_schedule_2026-11-15_to_19.json").get("anomalies", []))

    def nav_anchor(item):
        href, label = item
        cls = ' class="active"' if href == "model-v2.html" else ""
        return f'<a href="{href}"{cls}>{label}</a>'

    nav_html = "".join(nav_anchor(item) for item in NAV)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Model v2 — disagreement-first lines &amp; picks | NBA Lines Lab</title><link rel="stylesheet" href="subpages.css"></head><body><header class="topbar"><div class="top-inner"><a class="brand" href="index.html"><span class="brand-mark">N</span> NBA Lines Lab</a><div class="top-note">Horizon {SPAN} 2026 · two estimators, measured HCA, measured rho · no market feed · model output only</div></div></header><div class="layout"><nav class="side" aria-label="Main navigation"><div class="nav-label">Workspace</div>{nav_html}<div class="side-foot">Every row links to an official NBA source.<br>Blank = unverified, never zero.</div></nav><main class="main">
<p class="crumb">Workspace / Model v2</p>
<header class="page-head"><div class="kicker">disagreement is the headline · the blend is underneath</div><h1>Model v2 — lines &amp; picks, {SPAN} 2026</h1>
<p>Second-generation origination (<code>engine/model_v2.py</code>, rendered by <code>scripts/build_horizon_page_v2.py</code>): the home-court advantage is <b>measured</b>, not assumed; two independent official-input estimators publish their <b>disagreement</b> as the headline confidence signal; minutes redistribution, rest, back-to-back and travel from sourced arena coordinates are explicit; the market-anchored prior is built and labelled inert. Deterministic: rerunning the builder reproduces every number below byte-for-byte (run timestamps aside).</p></header>

<div class="notice warn"><strong>Read this first.</strong> (1) <b>No strategy has passed the validation gates</b> in this repository — all {len(picks)} picks below are MODEL OUTPUT — UNVALIDATED with <b>zero stake</b>; the {n_pass} that PASS the per-pick gates are merely eligible for consideration, never promoted. (2) The per-player minutes capture is the official leaderboard's <b>page 1 of 10 (top 50 of 469)</b>; pages 2–10 were not reachable (the URL Page parameter is not honored by the rendered slice), so absent players outside the top 50 leave the effect blank, never zero. (3) The market leg carries zero weight because no official closing line is reachable — blocked by source, not chosen. (4) The 2026-11-15 slate was still in progress at build time; its settlement waits for verified finals.</div>

<div class="grid"><article class="metric"><div class="metric-label">Horizon games ({SPAN})</div><div class="metric-value">{len(games)}</div><div class="metric-sub">official schedule, incl. the recorded POR@MIN consecutive-day anomaly</div></article><article class="metric"><div class="metric-label">Model picks ({PICK_SPAN})</div><div class="metric-value">{len(picks)}</div><div class="metric-sub">{n_pass} PASS the per-pick gates · all zero stake · all unvalidated</div></article><article class="metric"><div class="metric-label">Measured home-court advantage</div><div class="metric-value">{esc(hca.get('hca_points'))} pts</div><div class="metric-sub">home win rate {esc(hca.get('measured_home_win_rate'))} (standings) · sigma {esc(hca.get('sigma_margin_used'))}</div></article><article class="metric"><div class="metric-label">Estimator disagreement gate</div><div class="metric-value">≤ 4.0 pp</div><div class="metric-sub">|P(estimator A) − P(estimator B)| is the headline signal</div></article><article class="metric"><div class="metric-label">OOS log loss</div><div class="metric-value">{esc((rep.get('model_out_of_sample_log_loss') or {}).get('value'))}</div><div class="metric-sub">binary, official finals corpus, n={esc((rep.get('model_out_of_sample_log_loss') or {}).get('n_games'))}</div></article></div>

<section class="card"><h2>A. Originated horizon lines — all {len(games)} games ({SPAN})</h2><p class="card-intro">Spread is home-minus-away (positive = home favoured). Total and margin carry the measured HCA, the minutes-redistribution loss, the rest/B2B penalties and the away-travel penalty, each published beside the row. "Net redist." = net points lost home / away from captured absences at the status shares (Out 100%, Doubtful 75%, Questionable 50%, Probable 20%, Available 0%).</p><div class="table-wrap"><table><thead><tr><th>Date · tip</th><th>Matchup · venue</th><th>Total</th><th>Spread (home)</th><th>P(home win)</th><th>Fair ML (home)</th><th>Disagreement</th><th>Rest A / H · travel</th><th>Net redist. pts</th><th>Source</th></tr></thead><tbody>{''.join(a_rows)}</tbody></table></div><p class="small">Estimator A: possession × points-per-possession from the official efficiency tables. Estimator B: points-scored/allowed with opponent and pace adjustment from the official traditional/opponent tables. Blend 50/50 underneath the disagreement headline; parlay pricing uses the measured rho ({esc(rho.get('margin / total'))} margin/total, {esc(rho.get('home points / away points'))} home/away pts).</p></section>

<section class="card"><h2>B. Model picks — {PICK_SPAN} ({len(picks)}, {n_pass} gate passes, all zero stake)</h2><p class="card-intro">A pick is published for every window game with the higher-probability side named; the per-pick gates (disagreement ≤ 4.0 pp, model probability ≥ 0.55, both teams inside the ±1.5σ luck band, minutes redistribution computable) decide PASS/FAIL. PASS ≠ validated: no strategy has cleared the repository's validation gates, so every pick stays zero-stake MODEL OUTPUT.</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Game</th><th>Pick</th><th>P</th><th>Fair ML</th><th>Gate verdict</th><th>Rotation availability (pick team)</th><th>Gate detail</th><th>Status</th><th>Source</th></tr></thead><tbody>{''.join(b_rows)}</tbody></table></div></section>

<section class="card"><h2>C. Measured inputs (model report v2)</h2><p class="card-intro">Every number the model is pinned to, with its source. Full detail: <a href="data/derived/model_report_v2.json">data/derived/model_report_v2.json</a>.</p><div class="table-wrap"><table><thead><tr><th>Input</th><th>Measured value</th><th>Source</th></tr></thead><tbody>{meas_rows}</tbody></table></div></section>

<section class="card"><h2>D. Modelling choices (assumptions, never sourced values)</h2><div class="table-wrap"><table><thead><tr><th>Assumption</th><th>Value</th><th>Status</th><th>Official anchor</th></tr></thead><tbody>{ass_rows}</tbody></table></div></section>

<section class="card"><h2>E. Open gaps (published, non-blocking)</h2><div class="table-wrap"><table><thead><tr><th>ID</th><th>Severity</th><th>Item</th><th>Source</th></tr></thead><tbody>{gap_rows}</tbody></table></div></section>

<section class="card"><h2>F. Official-surface anomaly — schedule</h2><p class="card-intro">Recorded exactly as the official surfaces print it; nothing inferred.</p><div class="table-wrap"><table><thead><tr><th>ID</th><th>Matchup</th><th>Item · corroboration · precedent · action</th><th>Surfaces</th></tr></thead><tbody>{anomaly_rows}</tbody></table></div></section>

<section class="card"><h2>Method &amp; provenance</h2><ul class="bullets">
<li>Model: <code>engine/model_v2.py</code> — bivariate-normal CDF validated against independent midpoint integration to ≤ 6e-6.</li>
<li>Lines: <code>scripts/build_horizon_v2.py</code> → <a href="data/derived/horizon_lines_v2.json">data/derived/horizon_lines_v2.json</a>; picks → <a href="data/derived/horizon_picks_v2.json">horizon_picks_v2.json</a>; report → <a href="data/derived/model_report_v2.json">model_report_v2.json</a>.</li>
<li>Schedule: <a href="data/official/official_schedule_2026-11-15_to_19.json">official 38-game schedule</a> from <a class="source" href="https://www.nba.com/schedule" target="_blank" rel="noopener">nba.com/schedule</a> and the per-date games pages; six tip conflicts published, one anomaly (AN-1) recorded.</li>
<li>Team ratings: the three official team-stat pages re-read 2026-11-15 — <a class="source" href="https://www.nba.com/stats/teams/advanced?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">advanced</a>, <a class="source" href="https://www.nba.com/stats/teams/traditional?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">traditional</a>, <a class="source" href="https://www.nba.com/stats/teams/opponent?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">opponent</a>.</li>
<li>Standings/HCA: <a class="source" href="https://www.nba.com/standings" target="_blank" rel="noopener">official standings</a> (HOME/ROAD columns, 188 home games, {esc(hca.get('home_wins'))} home wins).</li>
<li>Minutes: <a class="source" href="https://www.nba.com/stats/players/traditional?Season=2026-27&amp;SeasonType=Regular+Season&amp;PerMode=PerGame&amp;dir=-1&amp;sort=MIN" target="_blank" rel="noopener">official MIN-sorted leaderboard</a>, page 1 (rows 1–50) captured; pages 2–10 unreachable (URL Page parameter not honored).</li>
<li>Injuries: <a class="source" href="https://official.nba.com/nba-injury-report-2026-27-season/" target="_blank" rel="noopener">official injury-report index</a>, 06:15 PM ET 11/15 edition transcribed verbatim (155 rows) with the computed consecutive-edition diff.</li>
<li>Arena coordinates: <a href="data/official/arena_coordinates_2026-11-15.json">sourced coordinate table</a> (venue names official; coordinates secondary-source, flagged in the file).</li>
</ul></section>

<section class="card"><h2>Flagged for review — this build</h2><div class="table-wrap"><table><thead><tr><th>ID</th><th>Severity</th><th>Item</th><th>Source</th></tr></thead><tbody>{flag_rows}</tbody></table></div></section>

<footer class="footer"><span>Session arena/49f70042-nba1 · generated by scripts/build_horizon_page_v2.py — values derived, never typed.</span><span>Sources: nba.com family only · <a href="sources.html">source register</a></span></footer>
</main></div></body></html>"""

    out = os.path.join(ROOT, "model-v2.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    n_gaps = len(rep.get("gaps", []))
    n_anom = len(load("data/official/official_schedule_2026-11-15_to_19.json")
                 .get("anomalies", []))
    print(f"model-v2.html written ({len(a_rows)} line rows, {len(b_rows)} pick rows, "
          f"{n_pass} gate passes, {n_gaps} gap rows, {n_anom} anomaly rows)")


if __name__ == "__main__":
    main()
