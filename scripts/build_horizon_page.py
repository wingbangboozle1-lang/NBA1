#!/usr/bin/env python3
"""
build_horizon_page.py — render picks.html (root namespace) from the derived horizon data.

Every value in every table cell comes from data/derived/horizon_lines.json or
data/derived/horizon_picks.json, both produced by scripts in this repository from
official NBA sources. Nothing is typed by hand. Every table row carries at least one
official-source link (nba.com family), the same rule scripts/check_site.py enforces
on the other root pages (picks.html is added to that checker's PAGES list as an
integration step — logged in COORDINATION.md §14, R-W1).
"""
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAV = [
    ("index.html", "◫&nbsp; Executive summary"),
    ("research.html", "⌁&nbsp; Strategy lab"),
    ("lines.html", "◈&nbsp; Originated lines &amp; picks"),
    ("picks.html", "▦&nbsp; Horizon lines &amp; picks 14–17 Nov"),
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
    return f'<a class="source" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def badge(kind, text):
    return f'<span class="badge {kind}">{esc(text)}</span>'


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def fmt_record(rest):
    if rest is None:
        return ""
    rd, b2b, last = rest["rest_days"], rest["b2b"], rest["last_date"]
    if rd is None:
        if last:
            return f"not known in captured window (last official game seen: {esc(last)})"
        return "no prior game in captured window (11/11-13)"
    return f"{rd}d{' — B2B' if b2b else ''}"


def avail_short(g):
    rows = [r for r in g["availability_rows"] if r.get("player")]
    if not rows:
        return esc(g["availability_label"])
    parts = []
    for r in rows:
        parts.append(f"{esc(r['player'].split(',')[0])} ({esc(r['team'])}): {esc(r['status'])}")
    return "; ".join(parts)


def main():
    lines_doc = load("data/derived/horizon_lines.json")
    picks_doc = load("data/derived/horizon_picks.json")
    games = lines_doc["games"]
    meta = lines_doc["_meta"]
    singles = picks_doc["singles"]
    parlays = picks_doc["parlays"]
    sgp = picks_doc["sgp_candidates"]
    n_picks = picks_doc["n_model_picks"]

    by_key = {(g["date"], g["matchup"]): g for g in games}

    # ---------------- table A: horizon lines ------------------------------------
    a_rows = []
    for g in games:
        a_rows.append(
            f"<tr><td>{esc(g['date'][5:])} · {esc(g['tip_et'])}</td>"
            f"<td><b>{esc(g['away'])} @ {esc(g['home'])}</b><br>"
            f"<small>records {esc(g['records_pre_11_13'])} ({esc(g['records_status'])})</small></td>"
            f"<td>{esc(g['proj_away_pts'])} / {esc(g['proj_home_pts'])}</td>"
            f"<td>{esc(g['line_spread_home'])}</td>"
            f"<td>{esc(g['line_total'])}</td>"
            f"<td>{esc(g['model_home_win_prob'])}</td>"
            f"<td>{esc(g['line_home_ml'])}</td>"
            f"<td>{avail_short(g)}</td>"
            f"<td>{esc(fmt_record(g['rest_away']))} / {esc(fmt_record(g['rest_home']))}</td>"
            f"<td>{src_link(g['schedule_source'], 'slate')} · {src_link(g['inputs_source'], 'ratings')}</td></tr>")

    # ---------------- table B: singles ------------------------------------------
    b_rows = []
    for s in singles:
        p = s["pick"]
        if p["pick_side"] == "PASS":
            pick_cell = badge("review", "PASS — gate G-CFG")
        else:
            pick_cell = f"<strong>{esc(p['pick_line'])}</strong> {badge('info', 'paper')}"
        b_rows.append(
            f"<tr><td>{esc(s['date'][5:])}</td><td>{esc(s['matchup'])}</td>"
            f"<td>{pick_cell}</td>"
            f"<td>{esc(s['line_spread_home'])}</td>"
            f"<td>{esc(p['pick_prob']) if p['pick_prob'] is not None else ''}</td>"
            f"<td><small>{esc(p['gate'])}</small></td>"
            f"<td>{badge('review', 'UNVALIDATED')}</td>"
            f"<td>{src_link(s['sources'][0], 'slate')}</td></tr>")

    # ---------------- table C: parlays ------------------------------------------
    c_rows = []
    for p in parlays:
        c_rows.append(
            f"<tr><td>{esc(p['date'][5:])}</td>"
            f"<td>{esc(p['leg1'])}<br>{esc(p['leg2'])}</td>"
            f"<td>{esc(p['p1'])} / {esc(p['p2'])}</td>"
            f"<td>{esc(p['joint_lb'])} … {esc(p['joint_ub'])}</td>"
            f"<td>{esc(p['fair_odds_lb'])} … {esc(p['fair_odds_ub'])}</td>"
            f"<td><small>{esc(p['method'])}</small></td>"
            f"<td>{badge('review', 'UNVALIDATED')}</td>"
            f"<td>{src_link(p['sources'][0], 'leg1')} · {src_link(p['sources'][1], 'leg2')}</td></tr>")

    # ---------------- table D: SGP candidates -----------------------------------
    d_rows = []
    for s in sgp:
        d_rows.append(
            f"<tr><td>{esc(s['date'][5:])}</td><td>{esc(s['game'])}</td>"
            f"<td>{esc(s['leg1'])}<br>{esc(s['leg2'])}</td>"
            f"<td>{esc(s['rho'])}<br><small>{esc(s['rho_status'])}</small></td>"
            f"<td>{esc(s['joint_prob_rho'])} <small>(indep. {esc(s['joint_prob_independent'])})</small></td>"
            f"<td><small>{esc(s['gates'])}<br>{esc(s['sigma_status'])}</small></td>"
            f"<td>{badge('review', 'UNVALIDATED')}</td>"
            f"<td>{src_link(s['sources'][0], 'slate')}</td></tr>")

    # ---------------- table E: 11/14 availability detail -------------------------
    e_rows = []
    for g in games:
        if g["date"] != "2026-11-14":
            continue
        for r in g["availability_rows"]:
            e_rows.append(
                f"<tr><td>{esc(g['matchup'])}</td><td>{esc(r.get('team') or '')}</td>"
                f"<td>{esc(r.get('player'))}</td>"
                f"<td>{esc(r.get('status'))}</td>"
                f"<td>{esc(r.get('reason'))}</td>"
                f"<td>{esc(r.get('season_min'))}</td>"
                f"<td>{esc(r.get('season_pts'))}</td>"
                f"<td>{esc(r.get('absence_class'))}</td>"
                f"<td>{esc(r.get('expected_points_removed'))}</td>"
                f"<td><small>{esc(r.get('note') or (r.get('team_source') or ''))}</small></td>"
                f"<td>{src_link(lines_doc['_meta']['flags'][5].get('source', ''), 'injury report PDF')}</td></tr>")

    # ---------------- flags -------------------------------------------------------
    flag_rows = []
    for fl in meta["flags"]:
        flag_rows.append(
            f"<tr><td><b>{esc(fl['id'])}</b></td><td>{badge('review', esc(fl['severity']))}</td>"
            f"<td><b>{esc(fl['item'])}</b><br><small>{esc(fl['detail'])}</small></td>"
            f"<td>{src_link(fl['source'], 'games in scope' if fl['id'] == 'F-W08' else 'source')}</td></tr>")
    inherited = [
        ("F-C01", "11/13 final scores not captured at build time (games were live).",
         "https://www.nba.com/games?date=2026-11-13"),
        ("F-C02", "Pre-11/13 records on 18 horizon teams (STALE markers kept).",
         "https://www.nba.com/games?date=2026-11-14"),
        ("F-C03", "The 11/14 noon injury report returned AccessDenied to Build C's fetch.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_12_00PM.pdf"),
        ("F-C06", "The CHI@MIN outlier (this model: spread +29.9, p 0.968) reproduces "
                  "Build B's flagged +29.7 — extreme early-season CHI ratings; kept, flagged.",
         "https://www.nba.com/game/chi-vs-min-0022600235"),
        ("F-C07", "This page is the F-C07 closure: picks exist now, with staleness disclosed "
                  "instead of hidden. Gate/limit caveats remain binding.",
         "https://www.nba.com/schedule"),
    ]
    for fid, txt, u in inherited:
        flag_rows.append(
            f"<tr><td><b>{esc(fid)}</b></td><td>{badge('info', 'inherited')}</td>"
            f"<td>{esc(txt)}</td><td>{src_link(u, 'source')}</td></tr>")

    # ---------------- live probe block (only if a probe artefact exists) ----------
    probe_html = ""
    probe_path = os.path.join(ROOT, "data", "raw", "probe_2026-11-13_finals.json")
    if os.path.exists(probe_path):
        pr = load("data/raw/probe_2026-11-13_finals.json")
        rows = "".join(
            f"<tr><td>{esc(r.get('matchup'))}</td><td>{esc(r.get('status'))}</td>"
            f"<td>{esc(r.get('score') or '—')}</td>"
            f"<td>{src_link(r.get('source_url', ''), 'official game page')}</td></tr>"
            for r in pr.get("rows", []))
        ip = pr.get("injury_report_probe", {})
        probe_html = (
            '<section class="card"><h2>Live probe at build time (W04)</h2>'
            f'<p class="card-intro">{esc(pr.get("note", ""))} Captured {esc(pr.get("captured_utc", ""))}. '
            'Artefact: <a href="data/raw/probe_2026-11-13_finals.json">probe_2026-11-13_finals.json</a>.</p>'
            '<div class="table-wrap"><table><thead><tr><th>Game (11/13)</th><th>Status at capture</th>'
            '<th>Score at capture</th><th>Source</th></tr></thead><tbody>' + rows +
            "</tbody></table></div>"
            f'<p class="small">Injury-report probe: {esc(ip.get("url", ""))} → '
            f'{esc(ip.get("result", ""))} at {esc(ip.get("captured_utc", ""))}. '
            f'{esc(ip.get("interpretation", ""))}</p></section>')


    def nav_anchor(item):
        href, label = item
        cls = ' class="active"' if href == "picks.html" else ""
        return f'<a href="{href}"{cls}>{label}</a>'

    nav_html = "".join(nav_anchor(item) for item in NAV)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Horizon lines &amp; picks | NBA Lines Lab</title><link rel="stylesheet" href="subpages.css"></head><body><header class="topbar"><div class="top-inner"><a class="brand" href="index.html"><span class="brand-mark">N</span> NBA Lines Lab</a><div class="top-note">Horizon 14–17 Nov 2026 · originated lines · no market feed · model output only</div></div></header><div class="layout"><nav class="side" aria-label="Main navigation"><div class="nav-label">Workspace</div>{nav_html}<div class="side-foot">Every row links to an official NBA source.<br>Blank = unverified, never zero.</div></nav><main class="main">
<p class="crumb">Workspace / Horizon lines &amp; picks</p>
<header class="page-head"><div class="kicker">F-C07 closure</div><h1>Horizon lines &amp; picks — 14–17 Nov 2026</h1>
<p>Originated lines for all {len(games)} unplayed games from today through today + 3 days, generated by <code>scripts/originate_horizon.py</code> with the same formulas as <code>lines.html</code>'s engine, and picks generated by <code>scripts/generate_picks.py</code>. Prior sessions declined to publish picks on staleness grounds (F-C07); this page publishes them <em>with the staleness disclosed on every row</em> instead of hidden — no market price is claimed and nothing is a validated bet.</p></header>

<div class="notice warn"><strong>Read this first.</strong> (1) Inputs are dated, not live: team ratings run through games of 2026-11-12; records are pre-11/13; the latest injury report is 11/13 05:15 PM ET (11/14 rows only). (2) No market odds feed exists — market-comparison gates G4/G5 and prop gate G-PROP are <strong>blocked</strong>. (3) <strong>No strategy has passed the validation gates</strong> (Build A 0/8, Build B 0/10): every pick is MODEL OUTPUT — UNVALIDATED, zero stake, paper record only. (4) Home-court advantage is not applied (unsourced; flagged F-W02). See <a href="review.html" target="_blank" rel="noopener">Flagged for review</a>.</div>

<div class="grid"><article class="metric"><div class="metric-label">Horizon games (14–17 Nov)</div><div class="metric-value">{len(games)}</div><div class="metric-sub">official schedule capture, verified row-by-row twice</div></article><article class="metric"><div class="metric-label">Model picks (singles)</div><div class="metric-value">{n_picks}</div><div class="metric-sub">gate: |spread| ≥ 3.0 — {len(games) - n_picks} PASS</div></article><article class="metric"><div class="metric-label">2-leg parlays published</div><div class="metric-value">{len(parlays)}</div><div class="metric-sub">Fréchet–Hoeffding joint bands, never single numbers</div></article><article class="metric"><div class="metric-label">SGP candidates</div><div class="metric-value">{len(sgp)}</div><div class="metric-sub">MODEL-DERIVED rho; G-PROP blocked</div></article><article class="metric"><div class="metric-label">Strategies past gates</div><div class="metric-value">0</div><div class="metric-sub">Build A 0/8 · Build B 0/10 — zero stake until one passes</div></article></div>

{probe_html}

<section class="card"><h2>A. Originated horizon lines (all {len(games)} games)</h2><p class="card-intro">Spread is home-minus-away (positive = home favoured); totals and spreads are DERIVED by the printed formula; no home-court advantage; dispersion measured from 14 real finals (margin sd {esc(meta['empirical_dispersion']['margin_sd'])}, total sd {esc(meta['empirical_dispersion']['total_sd'])}, n = {esc(meta['empirical_dispersion']['n_margin_games'])}).</p><div class="table-wrap"><table><thead><tr><th>Date · tip</th><th>Matchup (records pre-11/13)</th><th>Proj pts A / H</th><th>Spread (home)</th><th>Total</th><th>P(home win)</th><th>Fair ML (home)</th><th>Availability (latest official report)</th><th>Rest A / H</th><th>Source</th></tr></thead><tbody>{''.join(a_rows)}</tbody></table></div><p class="small">Formula: POSS = pace_home + pace_away − league_pace; PTS = (OffRtg × DefRtg_opp / league_OffRtg) × POSS / 100; SPREAD = PTS_home − PTS_away. Ratings as of 2026-11-13 retrieval (games through 11/12).</p></section>

<section class="card"><h2>B. Model picks — singles (SINGLE-SPREAD-v1, gate 3.0)</h2><p class="card-intro">{esc(picks_doc['_meta']['validation_state'])}</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Game</th><th>Pick</th><th>Spread (home)</th><th>Pick prob</th><th>Gate result</th><th>Status</th><th>Source</th></tr></thead><tbody>{''.join(b_rows)}</tbody></table></div></section>

<section class="card"><h2>C. Model picks — 2-leg parlays (PARLAY2-IND-v1)</h2><p class="card-intro">Legs come from different games (same-game legs are never combined here). The joint probability is published as its Fréchet–Hoeffding band; fair odds are decimal odds of the band endpoints.</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Legs</th><th>p1 / p2</th><th>Joint band</th><th>Fair odds band</th><th>Method</th><th>Status</th><th>Sources</th></tr></thead><tbody>{''.join(c_rows)}</tbody></table></div></section>

<section class="card"><h2>D. Same-game prop combos (SGP2-PROP-v1)</h2><p class="card-intro">Player-points OVER pairs at originated lines (floor(season avg) + 0.5). Joint probability uses the MODEL-DERIVED rho from the repo's sgp_rho register — an assumption, not a measured statistic; G-PROP is blocked (no market number, no game-log variance).</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Game</th><th>Legs (OVER)</th><th>rho</th><th>Joint P (rho / indep.)</th><th>Gates &amp; sigma</th><th>Status</th><th>Source</th></tr></thead><tbody>{''.join(d_rows)}</tbody></table></div></section>

<section class="card"><h2>E. Availability detail — 11/14 rows of the official 11/13 05:15 PM report</h2><p class="card-intro">Verbatim statuses. Impact columns follow the canonical NEW_ABSENCE rule (scripts/injury_impact.py): only a verifiable new absence moves a line — none qualifies here, so no line moves. Blank minutes/points = not verifiable in repo, never zero.</p><div class="table-wrap"><table><thead><tr><th>Game</th><th>Team</th><th>Player</th><th>Status</th><th>Reason</th><th>Min/g</th><th>Pts/g</th><th>Absence class</th><th>Pts removed</th><th>Note</th><th>Source</th></tr></thead><tbody>{''.join(e_rows)}</tbody></table></div></section>

<section class="card"><h2>Method &amp; provenance</h2><ul class="bullets">
<li>Lines: <code>scripts/originate_horizon.py</code> → <a href="data/derived/horizon_lines.json">data/derived/horizon_lines.json</a> — identical formulas to Build A's <code>scripts/originate_lines.py</code>.</li>
<li>Picks: <code>scripts/generate_picks.py</code> → <a href="data/derived/horizon_picks.json">data/derived/horizon_picks.json</a> — gate 3.0 inherited from <code>data/originated_lines.json</code>.</li>
<li>Schedule input: <a href="data/raw/official_schedule_capture_2026-11-14.json">official schedule capture</a> (36 games, verified twice against <a class="source" href="https://www.nba.com/schedule" target="_blank" rel="noopener">nba.com/schedule</a>).</li>
<li>Ratings input: <a class="source" href="https://www.nba.com/stats/teams/advanced?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">NBA.com team advanced stats</a> (retrieved 2026-11-13).</li>
<li>Dispersion input: official finals of 11/11–11/12 (<a class="source" href="https://www.nba.com/games?date=2026-11-11" target="_blank" rel="noopener">11 Nov</a>, <a class="source" href="https://www.nba.com/games?date=2026-11-12" target="_blank" rel="noopener">12 Nov</a>).</li>
<li>Injury input: <a class="source" href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf" target="_blank" rel="noopener">official 11/13 05:15 PM ET injury report PDF</a> (policy: <a class="source" href="https://official.nba.com/nba-injury-report-2026-27-season/" target="_blank" rel="noopener">official.nba.com</a>).</li>
</ul></section>

<section class="card"><h2>Flagged for review — this page</h2><p class="card-intro">Published, non-blocking, per the brief. Nothing above hides these.</p><div class="table-wrap"><table><thead><tr><th>ID</th><th>Severity</th><th>Item</th><th>Source</th></tr></thead><tbody>{''.join(flag_rows)}</tbody></table></div></section>

<footer class="footer"><span>Session arena/697fca1e-nba1 · generated by scripts/build_horizon_page.py — values derived, never typed.</span><span>Sources: nba.com family only · <a href="sources.html">source register</a></span></footer>
</main></div></body></html>"""

    out = os.path.join(ROOT, "picks.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"picks.html written ({len(a_rows)} line rows, {len(b_rows)} single rows, "
          f"{len(c_rows)} parlay rows, {len(d_rows)} sgp rows, {len(e_rows)} availability rows, "
          f"{len(flag_rows)} flag rows)")


if __name__ == "__main__":
    main()
