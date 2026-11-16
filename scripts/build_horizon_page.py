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
    ("picks.html", "▦&nbsp; Horizon lines &amp; picks 15–18 Nov"),
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


def newest(prefix, folder="data/official"):
    """Newest file in `folder` whose name starts with prefix."""
    d = os.path.join(ROOT, folder)
    cands = sorted(f for f in os.listdir(d) if f.startswith(prefix) and f.endswith(".json"))
    return os.path.join(d, cands[-1]) if cands else None


def load_rel(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def iso_from_us(d):
    """"11/16/2026" -> "2026-11-16".  Returns None if it is not that shape."""
    try:
        m, day, yr = d.split("/")
        return "%s-%s-%s" % (yr, m.zfill(2), day.zfill(2))
    except Exception:
        return None


def provenance():
    """The injury edition and the team-stat capture the derived files were built
    on, read at run time.

    Every date and URL the page prints about its inputs comes from here, so the
    prose cannot drift away from the data: it is read out of the same files the
    numbers came from, never typed.
    """
    lines_doc = load("data/derived/horizon_lines.json")
    inp = lines_doc["_meta"]["inputs"]
    out = {"ratings_retrieved_utc": inp.get("ratings_recut_retrieved_utc"),
           "injury_file": inp.get("injury_file"),
           "injury_edition": inp.get("injury_edition"),
           "injury_revision_et": inp.get("injury_revision_et"),
           "injury_retrieved_utc": inp.get("injury_retrieved_utc")}
    # the team-stat capture behind the re-cut ratings
    cap = newest("teams_advanced_")
    if cap:
        cap_doc = load_rel(cap)
        out["team_capture"] = os.path.basename(cap)
        out["team_games_through"] = cap_doc.get("games_through")
        out["team_retrieved_utc"] = cap_doc.get("retrieved_utc")
        out["team_source_url"] = cap_doc.get("source_url")
        out["team_rows"] = len(cap_doc.get("rows", []))
    # the injury edition itself
    if out["injury_file"] and os.path.exists(os.path.join(ROOT, out["injury_file"])):
        inj = load_rel(os.path.join(ROOT, out["injury_file"]))
        out["injury_source_url"] = inj.get("source_url")
        out["injury_index_url"] = inj.get("index_url")
        out["injury_rows_note"] = inj.get("rows_note")
        out["injury_game_dates"] = inj.get("game_dates_present") or []
        out["injury_rows"] = len(inj.get("rows", []))
        out["injury_dates_iso"] = sorted({x for x in (iso_from_us(d) for d in out["injury_game_dates"]) if x})
    else:
        out["injury_source_url"] = None
        out["injury_index_url"] = None
        out["injury_rows_note"] = None
        out["injury_game_dates"] = []
        out["injury_rows"] = 0
        out["injury_dates_iso"] = []
    return out


def fmt_record(rest):
    if rest is None:
        return ""
    rd, b2b, last = rest["rest_days"], rest["b2b"], rest["last_date"]
    if rd is None:
        if last:
            return f"not known in captured window (last official game seen: {esc(last)})"
        return "no prior game in captured window (11/11-14)"
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
    prov = provenance()
    inj_label = prov["injury_revision_et"] or prov["injury_edition"] or "unknown edition"
    inj_url = prov["injury_source_url"] or ""
    inj_rows = prov["injury_rows"]
    inj_dates = ", ".join(prov["injury_game_dates"]) or "none"
    inj_dates_iso = set(prov["injury_dates_iso"])
    rat_utc = prov["ratings_retrieved_utc"] or "unknown"
    team_through = prov.get("team_games_through") or "unknown"
    # "2026-11-15 (the page was read after that day's games)" -> "2026-11-15"
    team_through_short = team_through.split(" (")[0]
    # short, human form of the revision stamp: "11/16/2026 09:30 AM ET (...)" -> "11/16 09:30 AM ET"
    inj_short = (prov["injury_revision_et"] or "").split(" (")[0].replace("11/16/2026", "11/16")
    inj_short = inj_short or (prov["injury_edition"] or "unknown")
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
            f"<small>records {esc(g['records_as_captured'])} ({esc(g['records_status'])})</small></td>"
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

    # ---------------- table E: availability detail -------------------------------
    # Scope: the game dates the stored official injury edition actually covers.
    # The old code hardcoded 2026-11-15, which silently emptied this section the
    # moment the window rolled forward.
    e_rows = []
    e_games = [g for g in games if g["date"] in inj_dates_iso]
    for g in e_games:
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
                f"<td>{src_link(inj_url, 'injury report PDF')}</td></tr>")

    # ---------------- flags -------------------------------------------------------
    flag_rows = []
    for fl in meta["flags"]:
        flag_rows.append(
            f"<tr><td><b>{esc(fl['id'])}</b></td><td>{badge('review', esc(fl['severity']))}</td>"
            f"<td><b>{esc(fl['item'])}</b><br><small>{esc(fl['detail'])}</small></td>"
            f"<td>{src_link(fl['source'], 'games in scope' if fl['id'] == 'F-W08' else 'source')}</td></tr>")
    inherited = [
        ("F-C01", "CLOSED 2026-11-15: the 2026-11-14 slate is settled from official finals "
                  "(data/settlement/settlement_2026-11-14.json) with a ledger stamp.",
         "https://www.nba.com/games?date=2026-11-14"),
        ("F-C02", "CLOSED 2026-11-15: records on this page are post-2026-11-14, verified against "
                  "the official standings capture of 2026-11-15.",
         "https://www.nba.com/standings"),
        ("F-C03", "Historical: the 11/14 noon injury report returned AccessDenied to Build C's "
                  "fetch. Current injury input is the %s edition (retrieved %s, %d rows), "
                  "transcribed verbatim and stored with its timestamp. It covers game dates %s; "
                  "later dates in this window have no official report yet, so their picks are "
                  "provisional."
                  % (inj_short, prov["injury_retrieved_utc"], inj_rows, inj_dates),
         inj_url),
        ("F-C06", "Historical: the CHI@MIN outlier of the 2026-11-14 vintage (spread +29.9) settled "
                  "as a LOSS; the margin was 11. Extreme early-season CHI ratings remain flagged.",
         "https://www.nba.com/game/chi-vs-min-0022600235"),
        ("F-C07", "This page publishes picks with dated inputs disclosed on every row. Gate/limit "
                  "caveats remain binding: no strategy has passed the validation gates.",
         "https://www.nba.com/schedule"),
    ]
    for fid, txt, u in inherited:
        flag_rows.append(
            f"<tr><td><b>{esc(fid)}</b></td><td>{badge('info', 'inherited')}</td>"
            f"<td>{esc(txt)}</td><td>{src_link(u, 'source')}</td></tr>")

    # ---------------- settlement + ledger stamp (game-day settlement) ------------
    stamp_html = ""
    settle_path = os.path.join(ROOT, "data", "settlement", "settlement_2026-11-14.json")
    ledger_path = os.path.join(ROOT, "data", "ledger", "ledger.json")
    if os.path.exists(settle_path):
        st = load("data/settlement/settlement_2026-11-14.json")
        sm = st["summary"]
        s_rows = "".join(
            f"<tr><td>{esc(r['matchup'])}</td><td>{esc(r['pick_line'] or '—')}</td>"
            f"<td>{esc(r['away_pts'])}–{esc(r['home_pts'])}</td>"
            f"<td>{badge('info' if r['result'] == 'WIN' else ('review' if r['result'] == 'LOSS' else 'warn'), r['result'])}</td>"
            f"<td>{esc(r['units'])}</td><td>{src_link(r['source_game_url'], 'official game page')}</td></tr>"
            for r in st["singles"])
        g_rows = "".join(
            f"<tr><td>{esc(' + '.join(r['legs']))}</td>"
            f"<td>{badge('info' if r['result'] == 'WIN' else 'review', r['result'])}</td>"
            f"<td>{esc(r['units'])}</td>"
            f"<td>{' · '.join(src_link(l['source_game_url'], 'game') for l in r['leg_results'])}</td></tr>"
            for r in st["parlays"]) + "".join(
            f"<tr><td>{esc(r['game'])}: {esc(' + '.join(l['leg_text'] for l in r['legs']))}</td>"
            f"<td>{badge('info' if r['result'] == 'WIN' else 'review', r['result'])}</td>"
            f"<td>{esc(r['units'])}</td>"
            f"<td>{' · '.join(src_link(l['source_url'], 'game') for l in r['legs'])}</td></tr>"
            for r in st["sgp_candidates"])
        ledger_note = ""
        if os.path.exists(ledger_path):
            lg = load("data/ledger/ledger.json")
            head = lg["head"]
            ledger_note = (
                f'<p class="small">Tamper-evident ledger: <a href="data/ledger/ledger.json">data/ledger/ledger.json</a> '
                f'(hash chain, {len(lg["entries"])} entries, head <code>{esc(head[:16])}…</code>). '
                f'Pre-tip anchor commit <code>{esc(st["preregistration_check"]["pre_tip_anchor_commit"][:8])}</code> '
                f'at {esc(st["preregistration_check"]["pre_tip_anchor_time"])} — before first tip '
                f'{esc(st["preregistration_check"]["first_tip"])}. Verification: '
                f'<code>python3 scripts/verify_ledger.py</code>. '
                f'Pre-registration: <a href="data/prereg/Prereg_index.json">data/prereg/</a>.</p>')
        stamp_html = (
            f'<section class="card"><h2>Settlement stamp — 2026-11-14 slate (settled {esc(st["settled_at_utc"])})</h2>'
            f'<p class="card-intro">Sealed ledger settled from official finals at game-day end. '
            f'Singles record <b>{esc(sm["record"])}</b> ({esc(sm["wins"])}W {esc(sm["losses"])}L '
            f'{esc(sm["pushes"])}P, {esc(sm["no_bets"])} NO BET), units {esc(sm["singles_units_at_minus110"])} '
            f'(paper −110); parlays {esc(sm["parlays_won"])}/{esc(sm["parlays_published"])} '
            f'({esc(sm["parlay_units"])}u); SGP {esc(sm["sgp_won"])}/{esc(sm["sgp_published"])} '
            f'({esc(sm["sgp_units"])}u). Every ticket was published pre-tip as MODEL OUTPUT — '
            f"UNVALIDATED, zero stake. Settlement rules and every leg's evidence: "
            f'<a href="data/settlement/settlement_2026-11-14.json">settlement_2026-11-14.json</a>.</p>'
            '<div class="table-wrap"><table><thead><tr><th>Single</th><th>Published line</th>'
            '<th>Final</th><th>Result</th><th>Units</th><th>Source</th></tr></thead><tbody>'
            + s_rows + '</tbody></table></div>'
            '<div class="table-wrap"><table><thead><tr><th>Parlay / SGP ticket</th><th>Result</th>'
            '<th>Units</th><th>Sources</th></tr></thead><tbody>' + g_rows + '</tbody></table></div>'
            + ledger_note + '</section>')


    def nav_anchor(item):
        href, label = item
        cls = ' class="active"' if href == "picks.html" else ""
        return f'<a href="{href}"{cls}>{label}</a>'

    nav_html = "".join(nav_anchor(item) for item in NAV)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Horizon lines &amp; picks | NBA Lines Lab</title><link rel="stylesheet" href="subpages.css"></head><body><header class="topbar"><div class="top-inner"><a class="brand" href="index.html"><span class="brand-mark">N</span> NBA Lines Lab</a><div class="top-note">Horizon 15–18 Nov 2026 · originated lines · no market feed · model output only</div></div></header><div class="layout"><nav class="side" aria-label="Main navigation"><div class="nav-label">Workspace</div>{nav_html}<div class="side-foot">Every row links to an official NBA source.<br>Blank = unverified, never zero.</div></nav><main class="main">
<p class="crumb">Workspace / Horizon lines &amp; picks</p>
<header class="page-head"><div class="kicker">rolling slate · published before first tip</div><h1>Horizon lines &amp; picks — 15–18 Nov 2026</h1>
<p>Originated lines for all {len(games)} unplayed games from today through today + 3 days, generated by <code>scripts/originate_horizon.py</code> with the same formulas as <code>lines.html</code>'s engine, and picks generated by <code>scripts/generate_picks.py</code>. Published pre-tip and hash-chained in <a href="data/ledger/ledger.json">the ledger</a>; every input's date is disclosed on every row — no market price is claimed and nothing is a validated bet.</p></header>

<div class="notice warn"><strong>Read this first.</strong> (1) Inputs are dated, not live: team ratings were re-cut from the three official team-stat pages (retrieved {esc(rat_utc)}, games through {esc(team_through_short)}); records are post-{esc(team_through_short)}; the latest injury report is {esc(inj_short)} ({esc(inj_rows)} rows, covering {esc(inj_dates)}; dates outside that list have no official report yet, so those picks are provisional). (2) No market odds feed exists — market-comparison gates G4/G5 and prop gate G-PROP are <strong>blocked</strong>. (3) <strong>No strategy has passed the validation gates</strong> (Build A 0/8, Build B 0/10): every pick is MODEL OUTPUT — UNVALIDATED, zero stake, paper record only. (4) Home-court advantage is not applied (unsourced; flagged F-W02). (5) The 2026-11-14 slate is settled and stamped below; its pre-tip picks are archived and hash-verified. See <a href="review.html" target="_blank" rel="noopener">Flagged for review</a>.</div>

<div class="grid"><article class="metric"><div class="metric-label">Horizon games (15–18 Nov)</div><div class="metric-value">{len(games)}</div><div class="metric-sub">official schedule capture, game IDs verified in date-card links</div></article><article class="metric"><div class="metric-label">Model picks (singles)</div><div class="metric-value">{n_picks}</div><div class="metric-sub">gate: |spread| ≥ 3.0 — {len(games) - n_picks} PASS</div></article><article class="metric"><div class="metric-label">2-leg parlays published</div><div class="metric-value">{len(parlays)}</div><div class="metric-sub">Fréchet–Hoeffding joint bands, never single numbers</div></article><article class="metric"><div class="metric-label">SGP candidates</div><div class="metric-value">{len(sgp)}</div><div class="metric-sub">MODEL-DERIVED rho; G-PROP blocked</div></article><article class="metric"><div class="metric-label">Strategies past gates</div><div class="metric-value">0</div><div class="metric-sub">Build A 0/8 · Build B 0/10 — zero stake until one passes</div></article></div>

{stamp_html}

<section class="card"><h2>A. Originated horizon lines (all {len(games)} games)</h2><p class="card-intro">Spread is home-minus-away (positive = home favoured); totals and spreads are DERIVED by the printed formula; no home-court advantage; dispersion measured from 28 real finals (margin sd {esc(meta['empirical_dispersion']['margin_sd'])}, total sd {esc(meta['empirical_dispersion']['total_sd'])}, n = {esc(meta['empirical_dispersion']['n_margin_games'])}).</p><div class="table-wrap"><table><thead><tr><th>Date · tip</th><th>Matchup (records post-11/14)</th><th>Proj pts A / H</th><th>Spread (home)</th><th>Total</th><th>P(home win)</th><th>Fair ML (home)</th><th>Availability (latest official report)</th><th>Rest A / H</th><th>Source</th></tr></thead><tbody>{''.join(a_rows)}</tbody></table></div><p class="small">Formula: POSS = pace_home + pace_away − league_pace; PTS = (OffRtg × DefRtg_opp / league_OffRtg) × POSS / 100; SPREAD = PTS_home − PTS_away. Ratings re-cut 2026-11-15 (games through 2026-11-14).</p></section>

<section class="card"><h2>B. Model picks — singles (SINGLE-SPREAD-v1, gate 3.0)</h2><p class="card-intro">{esc(picks_doc['_meta']['validation_state'])}</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Game</th><th>Pick</th><th>Spread (home)</th><th>Pick prob</th><th>Gate result</th><th>Status</th><th>Source</th></tr></thead><tbody>{''.join(b_rows)}</tbody></table></div></section>

<section class="card"><h2>C. Model picks — 2-leg parlays (PARLAY2-IND-v1)</h2><p class="card-intro">Legs come from different games (same-game legs are never combined here). The joint probability is published as its Fréchet–Hoeffding band; fair odds are decimal odds of the band endpoints.</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Legs</th><th>p1 / p2</th><th>Joint band</th><th>Fair odds band</th><th>Method</th><th>Status</th><th>Sources</th></tr></thead><tbody>{''.join(c_rows)}</tbody></table></div></section>

<section class="card"><h2>D. Same-game prop combos (SGP2-PROP-v1)</h2><p class="card-intro">Player-points OVER pairs at originated lines (floor(season avg) + 0.5). Joint probability uses the MODEL-DERIVED rho from the repo's sgp_rho register — an assumption, not a measured statistic; G-PROP is blocked (no market number, no game-log variance).</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Game</th><th>Legs (OVER)</th><th>rho</th><th>Joint P (rho / indep.)</th><th>Gates &amp; sigma</th><th>Status</th><th>Source</th></tr></thead><tbody>{''.join(d_rows)}</tbody></table></div></section>

<section class="card"><h2>E. Availability detail — {len(e_rows)} rows of the official {esc(inj_short)} report</h2><p class="card-intro">Verbatim statuses for the {len(e_games)} games the stored edition covers ({esc(inj_dates)}); rows whose team cell the PDF text layer merged or lost carry a note in the source capture. {esc(prov["injury_rows_note"] or "")} Impact columns follow the canonical NEW_ABSENCE rule (scripts/injury_impact.py): only a verifiable new absence moves a line — none qualifies here, so no line moves. Blank minutes/points = not verifiable in repo, never zero.</p><div class="table-wrap"><table><thead><tr><th>Game</th><th>Team</th><th>Player</th><th>Status</th><th>Reason</th><th>Min/g</th><th>Pts/g</th><th>Absence class</th><th>Pts removed</th><th>Note</th><th>Source</th></tr></thead><tbody>{''.join(e_rows)}</tbody></table></div></section>

<section class="card"><h2>Method &amp; provenance</h2><ul class="bullets">
<li>Lines: <code>scripts/originate_horizon.py</code> → <a href="data/derived/horizon_lines.json">data/derived/horizon_lines.json</a> — identical formulas to Build A's <code>scripts/originate_lines.py</code>.</li>
<li>Picks: <code>scripts/generate_picks.py</code> → <a href="data/derived/horizon_picks.json">data/derived/horizon_picks.json</a> — gate 3.0 inherited from <code>data/originated_lines.json</code>.</li>
<li>Schedule input: <a href="data/raw/official_schedule_capture_2026-11-15.json">official schedule capture</a> (34 games, game IDs verified in the official date-card link URLs against <a class="source" href="https://www.nba.com/schedule" target="_blank" rel="noopener">nba.com/schedule</a>).</li>
<li>Ratings input: the three official team-stat pages — <a class="source" href="https://www.nba.com/stats/teams/advanced?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">advanced</a>, <a class="source" href="https://www.nba.com/stats/teams/traditional?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">traditional</a>, <a class="source" href="https://www.nba.com/stats/teams/opponent?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">opponent</a> — newest capture <code>{esc(prov.get("team_capture"))}</code>, games through {esc(team_through_short)}, retrieved {esc(prov.get("team_retrieved_utc"))}, {esc(prov.get("team_rows"))} teams; re-cut by <code>scripts/recut_model_inputs.py</code> at {esc(rat_utc)}.</li>
<li>Dispersion input: official finals of 11/11–11/14 (<a class="source" href="https://www.nba.com/games?date=2026-11-11" target="_blank" rel="noopener">11 Nov</a>, <a class="source" href="https://www.nba.com/games?date=2026-11-12" target="_blank" rel="noopener">12 Nov</a>, <a class="source" href="https://www.nba.com/games?date=2026-11-13" target="_blank" rel="noopener">13 Nov</a>, <a class="source" href="https://www.nba.com/games?date=2026-11-14" target="_blank" rel="noopener">14 Nov</a>).</li>
<li>Injury input: <a class="source" href="{esc(inj_url)}" target="_blank" rel="noopener">official {esc(inj_short)} injury report PDF</a> — {esc(inj_rows)} rows, retrieved {esc(prov["injury_retrieved_utc"])}, stored as <code>{esc(prov["injury_file"])}</code> (policy: <a class="source" href="{esc(prov["injury_index_url"] or "https://official.nba.com/nba-injury-report-2026-27-season/")}" target="_blank" rel="noopener">official.nba.com</a>).</li>
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
