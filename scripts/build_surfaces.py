#!/usr/bin/env python3
"""build_surfaces.py — split the site into a publishable PROJECTION surface and a gated BET surface.

Register R07 (COORDINATION section 50, task Q03): the projection surface carries model output
only; the bet surface shows picks only when four computed gates pass; the two are never mixed.

Outputs
-------
  site/pages/projection.html   model output only (publishable). Machine-checked: no betting vocabulary,
                               no pick rows, no stake/price fields, no travel distances (Q04).
  site/pages/bet.html          closed gates + no picks while any gate fails. Picks are read from
                               data/derived/horizon_picks_v2.json ONLY when all four gates pass.
  data/derived/surface_gates.json  the four gates, their requirement, observed value, and pass flag.

The four gates (all computed here from repository files, fail-closed; ALL must pass)
-----------------------------------------------------------------------------------
  G1 validation   : at least one strategy in data/derived/strategies.json has status VALIDATED.
  G2 sample floor : at least one strategy has n_graded >= 100 (the floor written in strategies.json).
  G3 pre-register : at least one data/prereg/S*.json exists and every one has frozen_before_first_tip True.
  G4 ledger       : scripts/verify_ledger.py exits 0 and prints "ledger chain OK".

Run:  python3 scripts/build_surfaces.py
      Both modes run the separation checks; the exit code is non-zero if a rule is broken.
"""
from __future__ import annotations

import glob
import html
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DERIVED = os.path.join(ROOT, "data", "derived")
PAGES = os.path.join(ROOT, "site", "pages")

HORIZON = os.path.join(DERIVED, "horizon_lines_v2.json")
MODEL = os.path.join(DERIVED, "model_report_v2.json")
PICKS = os.path.join(DERIVED, "horizon_picks_v2.json")
STRATEGIES = os.path.join(DERIVED, "strategies.json")
GATES_OUT = os.path.join(DERIVED, "surface_gates.json")
PROJECTION = os.path.join(PAGES, "projection.html")
BET = os.path.join(PAGES, "bet.html")

SAMPLE_FLOOR = 100

# Vocabulary that must never appear on the projection surface (whole words, case-insensitive).
FORBIDDEN_ON_PROJECTION = re.compile(
    r"\b(bets?|betting|picks?|stakes?|staking|wagers?|wagering|units?|moneylines?|odds|sportsbook|"
    r"edges?|roi|parlays?|tickets?|price|prices|payout|bankroll)\b",
    re.IGNORECASE,
)
# Keys that carry stake / price / travel-distance values and must not be serialized on projection rows.
FORBIDDEN_KEYS = {"model_ml", "model_home_ml", "pick", "side", "stake", "units", "travel_away", "travel_home"}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def _pct(x, digits=1) -> str:
    return "" if x is None else ("%." + str(digits) + "f%%") % (100 * x)


def _num(x, digits=1):
    return "" if x is None else ("%." + str(digits) + "f") % x


# ---------------------------------------------------------------- gates

def gate_validation():
    s = _load(STRATEGIES)
    validated = [x["name"] for x in s["leaderboard"] if x.get("status") == "VALIDATED"]
    return {
        "id": "G1_validation",
        "requirement": "at least one strategy has status VALIDATED in data/derived/strategies.json",
        "observed": len(validated),
        "observed_detail": validated,
        "passed": len(validated) >= 1,
        "source": "data/derived/strategies.json (leaderboard[].status)",
    }


def gate_sample_floor():
    s = _load(STRATEGIES)
    counts = [(x["name"], x.get("n_graded") or 0) for x in s["leaderboard"]]
    best = max(counts, key=lambda t: t[1]) if counts else ("", 0)
    return {
        "id": "G2_sample_floor",
        "requirement": "at least one strategy has n_graded >= %d" % SAMPLE_FLOOR,
        "observed": best[1],
        "observed_detail": {"strategy": best[0], "floor": SAMPLE_FLOOR},
        "passed": best[1] >= SAMPLE_FLOOR,
        "source": "data/derived/strategies.json (leaderboard[].n_graded)",
    }


def gate_prereg():
    files = sorted(glob.glob(os.path.join(ROOT, "data", "prereg", "S[0-9]*.json")))
    rows = []
    for f in files:
        d = _load(f)
        rows.append({"file": os.path.relpath(f, ROOT), "prereg_id": d.get("prereg_id"),
                     "frozen_at_utc": d.get("frozen_at_utc"),
                     "frozen_before_first_tip": str(d.get("frozen_before_first_tip")) == "True"})
    ok = len(rows) >= 1 and all(r["frozen_before_first_tip"] for r in rows)
    return {
        "id": "G3_preregistration",
        "requirement": "every pre-registration file (data/prereg/S*.json) is frozen before its first tip; at least one exists",
        "observed": len(rows),
        "observed_detail": rows,
        "passed": ok,
        "source": "data/prereg/S*.json",
    }


def gate_ledger():
    p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "verify_ledger.py")],
                       capture_output=True, text=True, cwd=ROOT)
    ok = p.returncode == 0 and "ledger chain OK" in p.stdout
    return {
        "id": "G4_ledger_integrity",
        "requirement": "scripts/verify_ledger.py exits 0 and prints 'ledger chain OK'",
        "observed": "ledger chain OK" if ok else "failed",
        "observed_detail": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[-200:],
        "passed": ok,
        "source": "data/ledger/ledger.json via scripts/verify_ledger.py",
    }


def compute_gates():
    gates = [gate_validation(), gate_sample_floor(), gate_prereg(), gate_ledger()]
    return {
        "title": "Bet-surface gates (R07)",
        "generated_by": "scripts/build_surfaces.py",
        "rule": "bet.html shows picks only when ALL four gates pass (fail-closed). Projection carries model output and is not gated.",
        "gates": gates,
        "open": all(g["passed"] for g in gates),
        "closed_by": [g["id"] for g in gates if not g["passed"]],
    }


# ---------------------------------------------------------------- projection rows

def projection_rows():
    """Model output per game, from the horizon v2 file. No picks, prices, stakes, or distances."""
    h = _load(HORIZON)
    rows, flags = [], []
    for g in h["games"]:
        a = g.get("estimator_a", {})
        b = g.get("estimator_b", {})
        bl = g.get("blend", {})
        src = g.get("source_url")
        if not src:
            flags.append({"game": g.get("matchup"), "flag": "no official source link; row omitted"})
            continue
        row = {
            "date": g["date"],
            "matchup": g["matchup"],
            "game_id": g["game_id"],
            "tip_et": g.get("tip_et"),
            "venue": g.get("venue"),
            "headline_disagreement_pp": bl.get("disagreement_pp"),
            "p_home_win_a": bl.get("p_home_win_estimator_a"),
            "p_home_win_b": bl.get("p_home_win_estimator_b"),
            "p_home_win_blend": bl.get("p_home_win_blend"),
            "margin_a": a.get("margin"),
            "margin_b": b.get("margin"),
            "margin_blend": bl.get("margin_blend"),
            "total_a": a.get("total"),
            "total_b": b.get("total"),
            "total_blend": bl.get("total_blend"),
            "possessions": a.get("game_possessions"),
            "ppp_home": a.get("ppp_proj_home"),
            "ppp_away": a.get("ppp_proj_away"),
            "source_url": src,
        }
        for k, v in row.items():
            if v is None and k not in ("venue", "tip_et"):
                flags.append({"game": g["matchup"], "flag": "blank value: %s (not inferred)" % k})
        rows.append(row)
    return rows, flags


def hca_anchor():
    m = _load(MODEL)
    hca = m["home_court_anchor"]
    return {
        "measured_home_win_rate": hca.get("measured_home_win_rate"),
        "basis": hca.get("primary_measurement"),
        "source_url": "https://www.nba.com/standings",
    }


# ---------------------------------------------------------------- rendering

PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s &middot; NBA1</title>
<link rel="stylesheet" href="../assets/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar"><div class="wrap topbar-in">
  <a class="brand" href="../../index.html"><span class="mark">NBA1</span><span class="brand-txt">Originated lines &amp; strategy lab</span></a>
  <nav class="topnav"><a href="../../index.html">Home</a><a href="projection.html">Projection</a><a href="bet.html">Bet surface</a></nav>
</div></header>
<main id="main" class="wrap">
"""
PAGE_FOOT = "</main>\n</body>\n</html>\n"


def render_projection(rows, flags, hca):
    out = [PAGE_HEAD % {"title": "Projection"}]
    out.append("<h1>Projection &middot; model output</h1>")
    out.append('<p class="lede">Two independent estimators, shown side by side and blended underneath. '
               'The headline is their disagreement. Home-court advantage is pinned to the measured official home win rate. '
               'Every row links its official game page. A blank cell is a value that could not be confirmed.</p>')
    out.append('<p class="note"><strong>Home-court anchor (measured):</strong> home win rate %s '
               '(official standings HOME/ROAD columns). <a href="%s" rel="noopener">Official standings</a>.</p>'
               % (_pct(hca["measured_home_win_rate"]), _e(hca["source_url"])))
    out.append('<div class="tablewrap"><table class="dash"><thead><tr>'
               '<th>Date</th><th>Game</th><th>Tip (ET)</th><th>Disagreement (pp) &mdash; headline</th>'
               '<th>P(home) A</th><th>P(home) B</th><th>P(home) blend</th>'
               '<th>Margin A</th><th>Margin B</th><th>Margin blend</th>'
               '<th>Total blend</th><th>Possessions</th><th>PPP home</th><th>PPP away</th><th>Source</th>'
               '</tr></thead><tbody>')
    for r in rows:
        cells = [
            _e(r["date"]), _e(r["matchup"]), _e(r["tip_et"]),
            _e(_num(r["headline_disagreement_pp"])),
            _e(_pct(r["p_home_win_a"])), _e(_pct(r["p_home_win_b"])), _e(_pct(r["p_home_win_blend"])),
            _e(_num(r["margin_a"])), _e(_num(r["margin_b"])), _e(_num(r["margin_blend"])),
            _e(_num(r["total_blend"])), _e(_num(r["possessions"], 1)),
            _e(_num(r["ppp_home"], 4)), _e(_num(r["ppp_away"], 4)),
            '<a href="%s" rel="noopener">game page</a>' % _e(r["source_url"]),
        ]
        out.append("<tr>" + "".join("<td>%s</td>" % c for c in cells) + "</tr>")
    out.append("</tbody></table></div>")
    out.append('<p class="note"><strong>Flagged (F85):</strong> the margin and total outputs include an adjustment that '
               'uses an arena-distance input. That input is not from an official source, so it is flagged for review, '
               'and no distance value is published on this page.</p>')
    if flags:
        out.append("<h2>Flags</h2><ul>")
        for f in flags:
            out.append("<li>%s &middot; %s</li>" % (_e(f["game"]), _e(f["flag"])))
        out.append("</ul>")
    out.append('<p class="note">Generated by scripts/build_surfaces.py from data/derived/horizon_lines_v2.json '
               'and data/derived/model_report_v2.json.</p>')
    out.append(PAGE_FOOT)
    return "".join(out)


def render_bet(gates, picks):
    out = [PAGE_HEAD % {"title": "Bet surface"}]
    out.append("<h1>Bet surface &middot; gated</h1>")
    if not gates["open"]:
        out.append('<p class="lede"><strong>Closed.</strong> No picks are shown. Picks appear here only when all four '
                   'gates below pass. Closed gates: %s.</p>' % _e(", ".join(gates["closed_by"])))
    else:
        out.append('<p class="lede">All four gates pass. Picks follow, each with its source link.</p>')
    out.append('<div class="tablewrap"><table class="dash"><thead><tr>'
               '<th>Gate</th><th>Requirement</th><th>Observed</th><th>Status</th><th>Source</th>'
               '</tr></thead><tbody>')
    for g in gates["gates"]:
        out.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            _e(g["id"]), _e(g["requirement"]), _e(g["observed"]),
            "PASS" if g["passed"] else "CLOSED",
            '<span class="na" title="computed from a repository file, not an official value: no official link applies">&mdash;</span> '
            + _e(g["source"])))
    out.append("</tbody></table></div>")
    if gates["open"]:
        out.append('<div class="tablewrap"><table class="dash"><thead><tr>'
                   '<th>Date</th><th>Game</th><th>Pick</th><th>Source</th></tr></thead><tbody>')
        for p in picks:
            out.append("<tr><td>%s</td><td>%s</td><td>%s</td><td><a href=\"%s\" rel=\"noopener\">game page</a></td></tr>" % (
                _e(p["date"]), _e(p["matchup"]), _e(p["pick"]), _e(p["source_url"])))
        out.append("</tbody></table></div>")
    out.append('<p class="note">Generated by scripts/build_surfaces.py. Projection values are on the projection page only.</p>')
    out.append(PAGE_FOOT)
    return "".join(out)


# ---------------------------------------------------------------- checks

def check_projection_html(path):
    text = open(path, encoding="utf-8").read()
    body = text.split('<main id="main"', 1)[1]
    # strip tags and attribute text before scanning visible content
    visible = re.sub(r"<[^>]+>", " ", body)
    hits = sorted(set(m.group(0).lower() for m in FORBIDDEN_ON_PROJECTION.finditer(visible)))
    problems = []
    if hits:
        problems.append("betting vocabulary on projection: %s" % ", ".join(hits))
    if re.search(r'class="[^"]*pick', body):
        problems.append("pick row markup on projection")
    if re.search(r"\b(travel|miles)\b", visible, re.IGNORECASE):
        problems.append("travel distance on projection (Q04: not computed)")
    return problems


def check_bet_html(path, gates, picks):
    text = open(path, encoding="utf-8").read()
    problems = []
    if not gates["open"]:
        # gate closed: there must be no pick table body rows
        if "<th>Pick</th>" in text:
            problems.append("pick table rendered while gates are closed")
        if picks:
            problems.append("picks present in build while gates are closed")
    return problems


def write_outputs():
    gates = compute_gates()
    rows, flags = projection_rows()
    hca = hca_anchor()
    picks = []
    if gates["open"]:
        picks = _load(PICKS)["picks"]
    proj_html = render_projection(rows, flags, hca)
    bet_html = render_bet(gates, picks)

    os.makedirs(PAGES, exist_ok=True)
    with open(GATES_OUT, "w", encoding="utf-8") as fh:
        json.dump(gates, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with open(PROJECTION, "w", encoding="utf-8") as fh:
        fh.write(proj_html)
    with open(BET, "w", encoding="utf-8") as fh:
        fh.write(bet_html)

    # machine-checked separation
    problems = check_projection_html(PROJECTION) + check_bet_html(BET, gates, picks)
    # projection rows must not carry forbidden keys
    for r in rows:
        bad = FORBIDDEN_KEYS & set(r)
        if bad:
            problems.append("projection row carries forbidden keys: %s" % sorted(bad))
    return gates, rows, problems


def main(argv):
    gates, rows, problems = write_outputs()
    print("gates: " + ", ".join("%s=%s" % (g["id"], "PASS" if g["passed"] else "CLOSED") for g in gates["gates"]))
    print("projection rows: %d" % len(rows))
    if problems:
        for p in problems:
            print("SEPARATION FAILURE: " + p)
        return 1
    print("separation checks: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
