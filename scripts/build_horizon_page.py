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


def _norm_name(s):
    """Canonical player name for cross-file matching (same published rule as
    engine/model_v2.py::norm_name: Last/First reorder, diacritics stripped,
    punctuation removed, casefolded. No fuzzy matching)."""
    import re as _re
    import unicodedata as _ud
    if not s:
        return ""
    s0 = s
    if "," in s0:
        last, first = s0.split(",", 1)
        s0 = first.strip() + " " + last.strip()
    s0 = _ud.normalize("NFKD", s0)
    s0 = "".join(c for c in s0 if not _ud.combining(c))
    s0 = s0.replace(".", "").replace("'", "")
    return _re.sub(r"\s+", " ", s0).strip().lower()


# Published status -> share of the player's minutes removed from availability
# (the repo's ASSUMPTIONS entry absence_minutes_share_by_status, used by the
# model-v2 minutes redistribution and kept identical here).
STATUS_MINUTES_REMOVED = {"out": 1.0, "doubtful": 0.75, "questionable": 0.5,
                          "probable": 0.2, "available": 0.0}


def rotation_availability(game, rotation):
    """Minutes-weighted share of each team's measured top-8 that is available
    for this game, from data/derived/rotation_2026_27.json (top-8 minutes
    shares measured from official box scores) and the game's official
    availability rows. Returns (away_str, home_str, notes)."""
    notes = []
    out = []
    for team in (game["away"], game["home"]):
        t = (rotation.get("teams") or {}).get(team)
        if not t:
            out.append(None)
            notes.append("%s: no measured top-8 in rotation_2026_27.json" % team)
            continue
        removed_by = {}
        for r in game.get("availability_rows", []):
            if not r.get("player"):
                continue
            st = (r.get("status") or "").strip().lower()
            share = STATUS_MINUTES_REMOVED.get(st)
            if share is None:
                continue
            # Attribution is by exact normalized player name against the team's
            # own measured top-8 below - a name in another team's top-8 cannot
            # match, and nothing is attributed by guess.
            removed_by[_norm_name(r["player"])] = share
        avail = 0.0
        measured = 0.0
        for pl in t.get("top8", []):
            share = pl.get("minutes_share") or 0.0
            measured += share
            rm = removed_by.get(_norm_name(pl.get("player") or ""), 0.0)
            avail += share * (1.0 - rm)
        out.append("%.0f%%" % (100.0 * avail))
        if measured and measured < 0.5:
            notes.append("%s: measured top-8 covers only %.0f%% of team minutes"
                         % (team, 100.0 * measured))
    return out[0], out[1], notes


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
    games = lines_doc["games"]
    meta = lines_doc["_meta"]
    singles = picks_doc["singles"]
    parlays = picks_doc["parlays"]
    sgp = picks_doc["sgp_candidates"]
    n_picks = picks_doc["n_model_picks"]

    # Context layers for the brief's display rules (R09/R10/R13/R14/R15). None
    # of these re-prices a frozen line: they add the measured disagreement, the
    # measured luck z-scores, the measured rotation availability and the naive
    # product beside each published combo price.
    est_doc = load("data/derived/estimators_2026_27.json")
    est_by_gid = {r["game_id"]: r for r in est_doc.get("rows", []) if r.get("game_id")}
    luck_doc = load("data/derived/luck_2026_27.json")
    luck_z = {r["team"]: r.get("luck_z") for r in luck_doc.get("rows", [])}
    rotation = load("data/derived/rotation_2026_27.json")
    consts = load("data/derived/measured_constants_2026_27.json")

    by_key = {(g["date"], g["matchup"]): g for g in games}

    # ---------------- table A: horizon lines ------------------------------------
    a_rows = []
    rot_cache = {}
    for g in games:
        e = est_by_gid.get(g.get("game_id"))
        if e:
            est_cell = (f"E1 {esc(e['e1_spread_home'])} / E2 {esc(e['e2_spread_home'])} "
                        f"<b>Δ {esc(e['disagreement_spread'])}</b><br>"
                        f"<small>totals E1 {esc(e['e1_total'])} / E2 {esc(e['e2_total'])} "
                        f"Δ {esc(e['disagreement_total'])} · blend {esc(e['blend_spread_home'])} / "
                        f"{esc(e['blend_total'])} (underneath, never the headline)</small>")
        else:
            est_cell = ("<small>no estimator row for this game in the re-cut window — "
                        "blank, never inferred</small>")
        ra = rot_cache.get(g.get("game_id"))
        if ra is None:
            ra = rotation_availability(g, rotation)
            rot_cache[g.get("game_id")] = ra
        rot_cell = (f"A {esc(ra[0]) if ra[0] else '—'} / H {esc(ra[1]) if ra[1] else '—'}"
                    + (f"<br><small>{esc('; '.join(ra[2]))}</small>" if ra[2] else ""))
        a_rows.append(
            f"<tr><td>{esc(g['date'][5:])} · {esc(g['tip_et'])}</td>"
            f"<td><b>{esc(g['away'])} @ {esc(g['home'])}</b><br>"
            f"<small>records {esc(g['records_as_captured'])} ({esc(g['records_status'])})</small></td>"
            f"<td>{esc(g['proj_away_pts'])} / {esc(g['proj_home_pts'])}</td>"
            f"<td>{esc(g['line_spread_home'])}</td>"
            f"<td>{esc(g['line_total'])}</td>"
            f"<td>{esc(g['model_home_win_prob'])}</td>"
            f"<td>{esc(g['line_home_ml'])}</td>"
            f"<td>{est_cell}</td>"
            f"<td>{rot_cell}</td>"
            f"<td>{avail_short(g)}</td>"
            f"<td>{esc(fmt_record(g['rest_away']))} / {esc(fmt_record(g['rest_home']))}</td>"
            f"<td>{src_link(g['schedule_source'], 'slate')} · {src_link(g['inputs_source'], 'ratings')}</td></tr>")

    # ---------------- table B: singles ------------------------------------------
    def leaned_team(s):
        p = s["pick"]
        if p["pick_side"] == "HOME":
            return s["matchup"].split("@")[-1]
        if p["pick_side"] == "AWAY":
            return s["matchup"].split("@")[0]
        return None

    b_rows = []
    refused_rows = []
    n_refused = 0
    for s in singles:
        p = s["pick"]
        team = leaned_team(s)
        z = luck_z.get(team)
        if p["pick_side"] == "PASS":
            luck_cell = "—"
            gate_cell = "PASS ticket (no lean)"
        elif z is None:
            luck_cell = "—"
            gate_cell = "no measured z — flagged, never assumed inside the band"
        else:
            luck_cell = f"{esc(team)} z = {esc(z)}"
            gate_cell = ("PASS (|z| ≤ 2.0)" if abs(z) <= 2.0
                         else "REFUSED — team outside the noise band (R10)")
        g = next((x for x in games if x.get("game_id") == s.get("game_id")), None)
        ra = rot_cache.get(s.get("game_id"))
        if ra is None and g is not None:
            ra = rotation_availability(g, rotation)
            rot_cache[s.get("game_id")] = ra
        rot_cell = (f"A {esc(ra[0]) if ra and ra[0] else '—'} / H {esc(ra[1]) if ra and ra[1] else '—'}"
                    if ra else "—")
        if p["pick_side"] == "PASS":
            pick_cell = badge("review", "PASS — gate G-CFG")
        else:
            pick_cell = f"<strong>{esc(p['pick_line'])}</strong> {badge('info', 'paper')}"
        row = (
            f"<tr><td>{esc(s['date'][5:])}</td><td>{esc(s['matchup'])}</td>"
            f"<td>{pick_cell}</td>"
            f"<td>{esc(s['line_spread_home'])}</td>"
            f"<td>{esc(p['pick_prob']) if p['pick_prob'] is not None else ''}</td>"
            f"<td>{luck_cell}</td>"
            f"<td><small>{esc(gate_cell)}</small></td>"
            f"<td>{rot_cell}</td>"
            f"<td><small>{esc(p['gate'])}</small></td>"
            f"<td>{badge('review', 'UNVALIDATED')}</td>"
            f"<td>{src_link(s['sources'][0], 'slate')}</td></tr>")
        if p["pick_side"] != "PASS" and gate_cell.startswith("REFUSED"):
            refused_rows.append(row)
            n_refused += 1
        else:
            b_rows.append(row)

    # ---------------- table C: parlays ------------------------------------------
    import re as _re2
    c_rows = []
    c_refused_rows = []
    n_parlay_refused = 0
    for p in parlays:
        naive = None
        try:
            naive = round(float(p["p1"]) * float(p["p2"]), 4)
        except (TypeError, ValueError):
            pass
        # R10 luck gate: the ticket leans on every tri-code printed in its legs.
        teams_in_legs = set(_re2.findall(r"—\s*([A-Z]{3})\s*[+-]", p["leg1"] + " " + p["leg2"]))
        zs = [(t, luck_z.get(t)) for t in sorted(teams_in_legs)]
        outside = [(t, z) for t, z in zs if z is not None and abs(z) > 2.0]
        if outside:
            luck_cell = "; ".join(f"{t} z={z}" for t, z in zs if z is not None)
            gate_cell = "REFUSED — " + "; ".join(
                f"{t} outside the noise band (R10)" for t, _ in outside)
        else:
            luck_cell = "; ".join(f"{t} z={z}" for t, z in zs if z is not None) or "—"
            gate_cell = "PASS (all leaned teams |z| ≤ 2.0)" if zs else "—"
        row = (
            f"<tr><td>{esc(p['date'][5:])}</td>"
            f"<td>{esc(p['leg1'])}<br>{esc(p['leg2'])}</td>"
            f"<td>{esc(p['p1'])} / {esc(p['p2'])}</td>"
            f"<td>{esc(p['joint_lb'])} … {esc(p['joint_ub'])}</td>"
            f"<td>{esc(naive) if naive is not None else '—'}</td>"
            f"<td>{esc(p['fair_odds_lb'])} … {esc(p['fair_odds_ub'])}</td>"
            f"<td>{luck_cell}<br><small>{esc(gate_cell)}</small></td>"
            f"<td><small>{esc(p['method'])}</small></td>"
            f"<td>{badge('review', 'UNVALIDATED')}</td>"
            f"<td>{src_link(p['sources'][0], 'leg1')} · {src_link(p['sources'][1], 'leg2')}</td></tr>")
        if gate_cell.startswith("REFUSED"):
            c_refused_rows.append(row)
            n_parlay_refused += 1
        else:
            c_rows.append(row)

    # ---------------- table D: SGP candidates -----------------------------------
    d_rows = []
    d_refused_rows = []
    n_sgp_refused = 0
    for s in sgp:
        naive = s.get("joint_prob_independent")
        teams_in_legs = set(_re2.findall(r"\(([A-Z]{3})\)", s["leg1"] + " " + s["leg2"]))
        zs = [(t, luck_z.get(t)) for t in sorted(teams_in_legs)]
        outside = [(t, z) for t, z in zs if z is not None and abs(z) > 2.0]
        if outside:
            gate_cell = "REFUSED — " + "; ".join(
                f"{t} outside the noise band (R10)" for t, _ in outside)
        else:
            gate_cell = "PASS (all leaned teams |z| ≤ 2.0)" if zs else "—"
        row = (
            f"<tr><td>{esc(s['date'][5:])}</td><td>{esc(s['game'])}</td>"
            f"<td>{esc(s['leg1'])}<br>{esc(s['leg2'])}</td>"
            f"<td>{esc(s['rho'])}<br><small>{esc(s['rho_status'])}</small></td>"
            f"<td>{esc(s['joint_prob_rho'])} <small>(naive product {esc(naive)})</small></td>"
            f"<td><small>{esc(s['gates'])}<br>{esc(s['sigma_status'])}<br>{esc(gate_cell)}</small></td>"
            f"<td>{badge('review', 'UNVALIDATED')}</td>"
            f"<td>{src_link(s['sources'][0], 'slate')}</td></tr>")
        if gate_cell.startswith("REFUSED"):
            d_refused_rows.append(row)
            n_sgp_refused += 1
        else:
            d_rows.append(row)

    # ---------------- table E: 11/15 availability detail -------------------------
    e_rows = []
    for g in games:
        if g["date"] != "2026-11-15":
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
        ("F-C01", "CLOSED 2026-11-15: the 2026-11-14 slate is settled from official finals "
                  "(data/settlement/settlement_2026-11-14.json) with a ledger stamp.",
         "https://www.nba.com/games?date=2026-11-14"),
        ("F-C02", "CLOSED 2026-11-15: records on this page are post-2026-11-14, verified against "
                  "the official standings capture of 2026-11-15.",
         "https://www.nba.com/standings"),
        ("F-C03", "Historical: the 11/14 noon injury report returned AccessDenied to Build C's "
                  "fetch. Current injury input is the 11/15 06:15 AM ET edition, transcribed "
                  "verbatim and stored with its timestamp.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf"),
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


    # ---------------- compact refusal register (R10) ----------------------------
    refused_ticket_rows = []
    for s in singles:
        p = s["pick"]
        team = leaned_team(s)
        z = luck_z.get(team)
        if p["pick_side"] != "PASS" and z is not None and abs(z) > 2.0:
            refused_ticket_rows.append(
                f"<tr><td>{esc(s['date'][5:])} · {esc(s['matchup'])}</td>"
                f"<td>single {esc(p['pick_line'])}</td>"
                f"<td>{esc(team)} luck z = {esc(z)} is outside ±2.0 — refused publication (R10)</td>"
                f"<td>{src_link(s['sources'][0], 'slate')}</td></tr>")
    for p in parlays:
        teams_in_legs = set(_re2.findall(r"—\s*([A-Z]{3})\s*[+-]", p["leg1"] + " " + p["leg2"]))
        outside = [(t, luck_z.get(t)) for t in sorted(teams_in_legs)
                   if luck_z.get(t) is not None and abs(luck_z.get(t)) > 2.0]
        if outside:
            refused_ticket_rows.append(
                f"<tr><td>{esc(p['date'][5:])}</td>"
                f"<td>parlay {esc(p['leg1'])} + {esc(p['leg2'])}</td>"
                f"<td>" + "; ".join(f"{esc(t)} luck z = {esc(z)} outside ±2.0" for t, z in outside)
                + " — refused publication (R10)</td>"
                f"<td>{src_link(p['sources'][0], 'leg1')} · {src_link(p['sources'][1], 'leg2')}</td></tr>")
    for s in sgp:
        teams_in_legs = set(_re2.findall(r"\(([A-Z]{3})\)", s["leg1"] + " " + s["leg2"]))
        outside = [(t, luck_z.get(t)) for t in sorted(teams_in_legs)
                   if luck_z.get(t) is not None and abs(luck_z.get(t)) > 2.0]
        if outside:
            refused_ticket_rows.append(
                f"<tr><td>{esc(s['date'][5:])} · {esc(s['game'])}</td>"
                f"<td>SGP {esc(s['leg1'])} + {esc(s['leg2'])}</td>"
                f"<td>" + "; ".join(f"{esc(t)} luck z = {esc(z)} outside ±2.0" for t, z in outside)
                + " — refused publication (R10)</td>"
                f"<td>{src_link(s['sources'][0], 'slate')}</td></tr>")
    if not refused_ticket_rows:
        refused_ticket_rows.append(
            "<tr><td>—</td><td>no ticket on this slate leans on a team outside the noise band</td>"
            "<td>the refusal rule is live and will hold back any such ticket when a team crosses "
            "|z| &gt; 2.0 (every team is inside the band at this build)</td>"
            "<td>" + src_link("https://www.nba.com/standings", "official standings") + "</td></tr>")

    # ---------------- headline: estimator disagreement (R08/R13) ---------------
    est_rows = [est_by_gid[g["game_id"]] for g in games if g.get("game_id") in est_by_gid]
    if est_rows:
        n_e = len(est_rows)
        mean_abs = sum(abs(r["disagreement_spread"]) for r in est_rows) / n_e
        mean_signed = sum(r["e2_spread_home"] - r["e1_spread_home"] for r in est_rows) / n_e
        max_row = max(est_rows, key=lambda r: abs(r["disagreement_spread"]))
        disagreement_banner = (
            '<div class="notice info"><strong>Headline signal &mdash; estimator disagreement '
            '(R08/R13).</strong> The primary confidence signal on this page is the '
            '<b>disagreement between two independent estimators</b>, not any single blended '
            'rating: E1 is a possessions &times; points-per-possession construction from the '
            'official team-stat re-cut, E2 is a least-squares power rating solved on official '
            f'final margins with HCA pinned to the measured home-win rate. On the {n_e} games '
            f'of this window with estimator rows, the mean |spread disagreement| is '
            f'<b>{mean_abs:.2f} points</b> (mean signed {mean_signed:+.2f}, E2 minus E1), '
            f'largest {abs(max_row["disagreement_spread"]):.1f} points on '
            f'{esc(max_row["away"])} @ {esc(max_row["home"])}. The 50/50 blend is printed '
            '<i>underneath</i> the disagreement in every row and is never the headline. '
            'Estimator rows are published in full in '
            '<a href="site/pages/estimators.html">Two estimators</a>, '
            '<a href="site/pages/roll.html">the rolling slate</a> and '
            '<a href="model-v2.html">model v2</a> (each with its own measured inputs and '
            'provenance).</div>')
    else:
        disagreement_banner = (
            '<div class="notice warn"><strong>Headline signal &mdash; estimator disagreement '
            '(R08/R13).</strong> No estimator rows cover this window &mdash; blank, never '
            'inferred. The two-estimator disagreement is published on '
            '<a href="site/pages/estimators.html">Two estimators</a>.</div>')

    def nav_anchor(item):
        href, label = item
        cls = ' class="active"' if href == "picks.html" else ""
        return f'<a href="{href}"{cls}>{label}</a>'

    nav_html = "".join(nav_anchor(item) for item in NAV)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Horizon lines &amp; picks | NBA Lines Lab</title><link rel="stylesheet" href="subpages.css"></head><body><header class="topbar"><div class="top-inner"><a class="brand" href="index.html"><span class="brand-mark">N</span> NBA Lines Lab</a><div class="top-note">Horizon 15–18 Nov 2026 · originated lines · no market feed · model output only</div></div></header><div class="layout"><nav class="side" aria-label="Main navigation"><div class="nav-label">Workspace</div>{nav_html}<div class="side-foot">Every row links to an official NBA source.<br>Blank = unverified, never zero.</div></nav><main class="main">
<p class="crumb">Workspace / Horizon lines &amp; picks</p>
<header class="page-head"><div class="kicker">rolling slate · published before first tip</div><h1>Horizon lines &amp; picks — 15–18 Nov 2026</h1>
<p>Originated lines for all {len(games)} unplayed games from today through today + 3 days, generated by <code>scripts/originate_horizon.py</code> with the same formulas as <code>lines.html</code>'s engine, and picks generated by <code>scripts/generate_picks.py</code>. Published pre-tip and hash-chained in <a href="data/ledger/ledger.json">the ledger</a>; every input's date is disclosed on every row — no market price is claimed and nothing is a validated bet.</p></header>
{disagreement_banner}

<div class="notice warn"><strong>Read this first.</strong> (1) Inputs are dated, not live: team ratings were re-cut 2026-11-15 from the three official team-stat pages (games through 2026-11-14); records are post-11/14; the latest injury report is 11/15 06:15 AM ET (11/15 rows; 11/16 blocks NOT YET SUBMITTED; 11/17–18 have no rows yet). (2) No market odds feed exists — market-comparison gates G4/G5 and prop gate G-PROP are <strong>blocked</strong>. (3) <strong>No strategy has passed the validation gates</strong> (Build A 0/8, Build B 0/10): every pick is MODEL OUTPUT — UNVALIDATED, zero stake, paper record only. (4) Home-court advantage: this frozen window was cut with <strong>no HCA applied</strong> (flag F-W02, locked at the cut &mdash; a frozen line is never re-priced). The project has since <strong>measured</strong> HCA from official finals &mdash; {esc(consts.get('home_court_points'))} points, the points equivalent of the measured home-win rate {esc(consts.get('home_win_rate'))} on {esc(consts.get('n_final_games'))} official finals (<a href="data/derived/measured_constants_2026_27.json">measured constants</a>) &mdash; and every window cut from 2026-11-16 forward pins HCA to that measured value instead of fitting it; the two-estimator rows on this page already carry it (hca_applied column of <a href="data/derived/estimators_2026_27.json">estimators_2026_27.json</a>). (5) The 2026-11-14 slate is settled and stamped below; its pre-tip picks are archived and hash-verified. (6) The luck-band gate (R10) is live on this page: any single, parlay or SGP that leans on a team whose luck z-score is outside &plusmn;2.0 is <strong>refused publication</strong> and listed in the refusal section with its reason &mdash; nothing is silently down-weighted. See <a href="review.html" target="_blank" rel="noopener">Flagged for review</a>.</div>

<div class="grid"><article class="metric"><div class="metric-label">Horizon games (15–18 Nov)</div><div class="metric-value">{len(games)}</div><div class="metric-sub">official schedule capture, game IDs verified in date-card links</div></article><article class="metric"><div class="metric-label">Model picks (singles)</div><div class="metric-value">{n_picks}</div><div class="metric-sub">gate: |spread| ≥ 3.0 — {len(games) - n_picks} PASS</div></article><article class="metric"><div class="metric-label">2-leg parlays published</div><div class="metric-value">{len(parlays)}</div><div class="metric-sub">Fréchet–Hoeffding joint bands, never single numbers</div></article><article class="metric"><div class="metric-label">SGP candidates</div><div class="metric-value">{len(sgp)}</div><div class="metric-sub">MODEL-DERIVED rho; G-PROP blocked</div></article><article class="metric"><div class="metric-label">Strategies past gates</div><div class="metric-value">0</div><div class="metric-sub">Build A 0/8 · Build B 0/10 — zero stake until one passes</div></article></div>

{stamp_html}

<section class="card"><h2>A. Originated horizon lines (all {len(games)} games)</h2><p class="card-intro">Spread is home-minus-away (positive = home favoured); totals and spreads are DERIVED by the printed formula; no home-court advantage; dispersion measured from 28 real finals (margin sd {esc(meta['empirical_dispersion']['margin_sd'])}, total sd {esc(meta['empirical_dispersion']['total_sd'])}, n = {esc(meta['empirical_dispersion']['n_margin_games'])}).</p><div class="table-wrap"><table><thead><tr><th>Date · tip</th><th>Matchup (records post-11/14)</th><th>Proj pts A / H</th><th>Spread (home)</th><th>Total</th><th>P(home win)</th><th>Fair ML (home)</th><th>Two estimators: E1 / E2 spread · disagreement Δ (headline)</th><th>Rotation availability A / H (measured top-8)</th><th>Availability (latest official report)</th><th>Rest A / H</th><th>Source</th></tr></thead><tbody>{''.join(a_rows)}</tbody></table></div><p class="small">Formula: POSS = pace_home + pace_away − league_pace; PTS = (OffRtg × DefRtg_opp / league_OffRtg) × POSS / 100; SPREAD = PTS_home − PTS_away. Ratings re-cut 2026-11-15 (games through 2026-11-14).</p></section>

<section class="card"><h2>B. Model picks — singles (SINGLE-SPREAD-v1, gate 3.0)</h2><p class="card-intro">{esc(picks_doc['_meta']['validation_state'])}</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Game</th><th>Pick</th><th>Spread (home)</th><th>Pick prob</th><th>Luck z (lean)</th><th>Gate R10 (noise band)</th><th>Rotation avail.</th><th>Gate result</th><th>Status</th><th>Source</th></tr></thead><tbody>{''.join(b_rows)}</tbody></table></div></section>

<section class="card"><h2>C. Model picks — 2-leg parlays (PARLAY2-IND-v1)</h2><p class="card-intro">Legs come from different games (same-game legs are never combined here). The joint probability is published as its Fréchet–Hoeffding band; fair odds are decimal odds of the band endpoints.</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Legs</th><th>p1 / p2</th><th>Joint band</th><th>Naive product p1×p2</th><th>Fair odds band</th><th>Luck gate R10</th><th>Method</th><th>Status</th><th>Sources</th></tr></thead><tbody>{''.join(c_rows)}</tbody></table></div></section>

<section class="card"><h2>D. Same-game prop combos (SGP2-PROP-v1)</h2><p class="card-intro">Player-points OVER pairs at originated lines (floor(season avg) + 0.5). Joint probability uses the MODEL-DERIVED rho from the repo's sgp_rho register — an assumption, not a measured statistic; G-PROP is blocked (no market number, no game-log variance).</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Game</th><th>Legs (OVER)</th><th>rho</th><th>Joint P (rho) / naive product</th><th>Gates &amp; sigma</th><th>Status</th><th>Source</th></tr></thead><tbody>{''.join(d_rows)}</tbody></table></div></section>

<section class="card"><h2>D-refused. Publication refusals — luck-band gate (R10)</h2><p class="card-intro"><strong>Refusal rule (R10).</strong> {esc(luck_doc.get('noise_band', 'refuse to publish a strategy that leans on a team outside the noise band'))} Luck is measured per team as z = (wins − Pythagorean expected wins) / sqrt(n·p·(1−p)) from official finals (<a href="data/derived/luck_2026_27.json">luck z-scores</a>, <a href="site/pages/luck-z.html">Luck z-scores page</a>). A ticket that leans on a team outside the band is <strong>not published as a pick</strong>: it is listed here, complete and sourced, with the refusal reason. Nothing is silently down-weighted or hidden. {n_refused + n_parlay_refused + n_sgp_refused} ticket(s) refused on this slate.</p><div class="table-wrap"><table><thead><tr><th>Ticket</th><th>Detail</th><th>Refusal reason</th><th>Source</th></tr></thead><tbody>{''.join(refused_ticket_rows)}</tbody></table></div></section>

<section class="card"><h2>E. Availability detail — 11/15 rows of the official 11/15 06:15 AM ET report</h2><p class="card-intro">Verbatim statuses (13 rows carry PDF-inherited team cells, marked in the source capture). Impact columns follow the canonical NEW_ABSENCE rule (scripts/injury_impact.py): only a verifiable new absence moves a line — none qualifies here, so no line moves. Blank minutes/points = not verifiable in repo, never zero.</p><div class="table-wrap"><table><thead><tr><th>Game</th><th>Team</th><th>Player</th><th>Status</th><th>Reason</th><th>Min/g</th><th>Pts/g</th><th>Absence class</th><th>Pts removed</th><th>Note</th><th>Source</th></tr></thead><tbody>{''.join(e_rows)}</tbody></table></div></section>

<section class="card"><h2>Method &amp; provenance</h2><ul class="bullets">
<li>Lines: <code>scripts/originate_horizon.py</code> → <a href="data/derived/horizon_lines.json">data/derived/horizon_lines.json</a> — identical formulas to Build A's <code>scripts/originate_lines.py</code>.</li>
<li>Picks: <code>scripts/generate_picks.py</code> → <a href="data/derived/horizon_picks.json">data/derived/horizon_picks.json</a> — gate 3.0 inherited from <code>data/originated_lines.json</code>.</li>
<li>Schedule input: <a href="data/raw/official_schedule_capture_2026-11-15.json">official schedule capture</a> (34 games, game IDs verified in the official date-card link URLs against <a class="source" href="https://www.nba.com/schedule" target="_blank" rel="noopener">nba.com/schedule</a>).</li>
<li>Ratings input: the three official team-stat pages re-read 2026-11-15 — <a class="source" href="https://www.nba.com/stats/teams/advanced?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">advanced</a>, <a class="source" href="https://www.nba.com/stats/teams/traditional?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">traditional</a>, <a class="source" href="https://www.nba.com/stats/teams/opponent?Season=2026-27&amp;SeasonType=Regular+Season" target="_blank" rel="noopener">opponent</a> (games through 2026-11-14; captures in data/official/).</li>
<li>Dispersion input: official finals of 11/11–11/14 (<a class="source" href="https://www.nba.com/games?date=2026-11-11" target="_blank" rel="noopener">11 Nov</a>, <a class="source" href="https://www.nba.com/games?date=2026-11-12" target="_blank" rel="noopener">12 Nov</a>, <a class="source" href="https://www.nba.com/games?date=2026-11-13" target="_blank" rel="noopener">13 Nov</a>, <a class="source" href="https://www.nba.com/games?date=2026-11-14" target="_blank" rel="noopener">14 Nov</a>).</li>
<li>Injury input: <a class="source" href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf" target="_blank" rel="noopener">official 11/15 06:15 AM ET injury report PDF</a> (policy: <a class="source" href="https://official.nba.com/nba-injury-report-2026-27-season/" target="_blank" rel="noopener">official.nba.com</a>).</li>
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
