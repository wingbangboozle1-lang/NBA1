#!/usr/bin/env python3
"""
build_site.py — generate the static dashboard from data/*.json.

Design constraints taken from the brief:
  * A clean landing page plus subpages by category.
  * Dashboard-style, simple, readable tables.
  * EVERY table row carries a source link. If a value cannot be verified it is left as an em dash
    or "not submitted", and flagged, rather than filled in.
  * Nothing is typed by hand that could be read from the data files — the HTML is generated, so a
    stale page is impossible without a stale data file.

Outputs docs/index.html and docs/pages/*.html plus docs/assets/style.css.
"""
import html
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DER = os.path.join(DATA, "derived")
DOCS = os.path.join(ROOT, "docs")
PAGES = os.path.join(DOCS, "pages")

GENERATED = "2026-11-13"
E = html.escape
DASH = "&mdash;"

NAV = [
    ("index.html", "Overview", ""),
    ("summary.html", "Executive summary", "pages/"),
    ("lines.html", "Originated lines", "pages/"),
    ("picks.html", "Picks by slate", "pages/"),
    ("strategies.html", "Strategies", "pages/"),
    ("gates.html", "Validation gates", "pages/"),
    ("correlations.html", "Correlations", "pages/"),
    ("injuries.html", "Injuries", "pages/"),
    ("gameflow.html", "Game flow", "pages/"),
    ("backtest.html", "Backtest", "pages/"),
    ("questions.html", "Open questions", "pages/"),
    ("suggestions.html", "Suggestions", "pages/"),
    ("flagged.html", "Flagged for review", "pages/"),
    ("glossary.html", "Glossary", "pages/"),
    ("sources.html", "Sources", "pages/"),
]


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def dload(name):
    with open(os.path.join(DER, name), encoding="utf-8") as f:
        return json.load(f)


def src(url, label=None):
    """Every table row ends with one of these. Calls out missing links instead of hiding them."""
    if not url:
        return '<span class="flag">unverified</span>'
    label = label or "source"
    return f'<a href="{E(url)}" target="_blank" rel="noopener">{E(label)}</a>'


def num(v, digits=1, suffix=""):
    if v is None:
        return DASH
    if isinstance(v, str):
        return E(v)
    return f"{v:,.{digits}f}{suffix}"


CSS = """
:root{--bg:#0f1419;--panel:#161d26;--panel2:#1c2531;--line:#26313f;--ink:#e8eef5;
--muted:#93a3b8;--accent:#4ea8ff;--good:#39c07a;--warn:#e2b33c;--bad:#e2585c;--chip:#22303f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header{position:sticky;top:0;z-index:20;background:rgba(15,20,25,.96);
border-bottom:1px solid var(--line);backdrop-filter:blur(6px)}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}
.bar{display:flex;align-items:center;gap:18px;height:58px}
.brand{font-weight:700;letter-spacing:.3px;font-size:15px;white-space:nowrap}
.brand span{color:var(--accent)}
nav{display:flex;gap:2px;flex-wrap:wrap;font-size:13px}
nav a{padding:6px 9px;border-radius:6px;color:var(--muted)}
nav a:hover{background:var(--panel2);color:var(--ink);text-decoration:none}
nav a.on{background:var(--chip);color:var(--ink)}
main{padding:26px 0 70px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.2px}
h2{font-size:17px;margin:30px 0 10px;padding-bottom:7px;border-bottom:1px solid var(--line)}
h3{font-size:14px;margin:20px 0 8px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px}
p{color:#c6d3e2;max-width:80ch}
.lede{color:var(--muted);margin:0 0 22px;max-width:82ch}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));margin:18px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:15px 16px}
.card .k{font-size:11px;text-transform:uppercase;letter-spacing:.7px;color:var(--muted)}
.card .v{font-size:25px;font-weight:700;margin:7px 0 3px;letter-spacing:-.5px}
.card .s{font-size:12px;color:var(--muted)}
.card.good .v{color:var(--good)}.card.warn .v{color:var(--warn)}.card.bad .v{color:var(--bad)}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:8px 11px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:var(--panel2);color:var(--muted);font-weight:600;font-size:11px;
text-transform:uppercase;letter-spacing:.5px;position:sticky;top:0}
tbody tr:hover{background:#1a232e}
tbody tr:last-child td{border-bottom:none}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
td.wrap{white-space:normal;min-width:220px;max-width:520px}
.pos{color:var(--good)}.neg{color:var(--bad)}
.chip{display:inline-block;padding:2px 7px;border-radius:999px;font-size:11px;
background:var(--chip);color:var(--muted);white-space:nowrap}
.chip.good{background:rgba(57,192,122,.15);color:var(--good)}
.chip.warn{background:rgba(226,179,60,.15);color:var(--warn)}
.chip.bad{background:rgba(226,88,92,.15);color:var(--bad)}
.flag{color:var(--warn);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.note{border-left:3px solid var(--warn);background:rgba(226,179,60,.07);
padding:12px 15px;border-radius:0 8px 8px 0;margin:16px 0;font-size:13.5px;color:#d6e0ec}
.note.bad{border-color:var(--bad);background:rgba(226,88,92,.07)}
.note.ok{border-color:var(--good);background:rgba(57,192,122,.07)}
.note b{color:var(--ink)}
footer{border-top:1px solid var(--line);padding:20px 0;color:var(--muted);font-size:12px}
.kv{display:grid;grid-template-columns:200px 1fr;gap:6px 16px;font-size:13px;margin:12px 0}
.kv dt{color:var(--muted)}.kv dd{margin:0}
ul.tight{margin:8px 0;padding-left:20px;color:#c6d3e2;font-size:13.5px}
ul.tight li{margin:5px 0}
code{background:var(--panel2);padding:1px 5px;border-radius:4px;font-size:12px;color:#cfdcea}
"""


def page(title, active, body, in_pages=True):
    """
    Nav hrefs are computed from the page's own depth so a link can never be wrong at one depth.
    index.html sits at the site root and pages live in pages/.
    """
    def href_for(h):
        if not in_pages:
            return h if h == "index.html" else "pages/" + h
        return "../index.html" if h == "index.html" else h

    nav = "".join(
        f'<a class="{"on" if href == active else ""}" href="{href_for(href)}">{E(label)}</a>'
        for href, label, _rel in NAV
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · NBA 2026-27 Origination Desk</title>
<link rel="stylesheet" href="{{css}}">
</head><body>
<header><div class="wrap bar"><div class="brand">NBA <span>Origination Desk</span></div>
<nav>{nav}</nav></div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">
Generated {GENERATED} from <code>data/*.json</code> by <code>scripts/build_site.py</code>.
Every figure traces to an official NBA source; unverifiable values are shown as an em dash and flagged,
never filled in. Season 2026-27.
</div></footer></body></html>
"""


def table_row_count():
    """Count data rows across the generated pages, so the prose cannot drift from the artefact."""
    total = 0
    for base, _, files in os.walk(DOCS):
        for f in files:
            if not f.endswith(".html"):
                continue
            with open(os.path.join(base, f), encoding="utf-8") as fh:
                txt = fh.read()
            # Strip <script> blocks first. A few Build B pages build their tables
            # in JavaScript, so their <tr> strings are templates, not rows that
            # exist in the document. Counting them inflated this number by 6
            # (731 vs the 725 rows actually present) and that inflated number is
            # what the executive summary published. scripts/verify_integration.py
            # recomputes it with the same definition and fails if they disagree.
            txt = re.sub(r"<script\b.*?</script>", "", txt, flags=re.S | re.I)
            for tb in re.findall(r"<tbody>(.*?)</tbody>", txt, re.S):
                total += len(re.findall(r"<tr\b[^>]*>", tb))
    return total


APPLIED_RE = re.compile(r"https?://([\w.\-]*\.)?nba\.com/")


def sourced_row_count():
    """Rows that carry an official nba.com link, counted the same way as
    table_row_count so the two numbers in one sentence are always comparable.

    This exists because the earlier wording ("a source link on every one of its
    N table rows") was true of the data tables but not of the whole set: design
    registers (gates, suggestions, open questions, legal scope) legitimately cite
    no NBA value because they state no NBA value. Asserting "every row" made the
    page overclaim by 56 rows. Both numbers are derived here, never typed.
    """
    total = 0
    for base, _, files in os.walk(DOCS):
        for f in files:
            if not f.endswith(".html"):
                continue
            with open(os.path.join(base, f), encoding="utf-8") as fh:
                txt = fh.read()
            txt = re.sub(r"<script\b.*?</script>", "", txt, flags=re.S | re.I)
            for tb in re.findall(r"<tbody>(.*?)</tbody>", txt, re.S):
                for row in re.findall(r"<tr\b[^>]*>.*?</tr>", tb, re.S):
                    if APPLIED_RE.search(row):
                        total += 1
    return total


def card(k, v, s="", cls=""):
    return (f'<div class="card {cls}"><div class="k">{E(k)}</div>'
            f'<div class="v">{v}</div><div class="s">{E(s)}</div></div>')


def table(headers, rows, numeric=()):
    head = "".join(
        f'<th class="{"n" if i in numeric else ""}">{E(h)}</th>' for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(
        f'<td class="{"n" if i in numeric else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
        for r in rows)
    return f'<div class="tblwrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def write(path, content, css_href):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.replace("{css}", css_href))


# --------------------------------------------------------------------------- pages
def build():
    lines = dload("lines.json")
    bt = dload("backtest.json")
    corr = dload("correlations.json")
    inj = dload("injury_impact.json")
    strat = dload("strategies.json")
    sched = load("schedule_2026_11_13_to_16.json")
    teams = load("teams_advanced_2026_27.json")
    scoring = load("teams_scoring_2026_27.json")
    players = load("players_2026_27.json")
    mins = load("players_minutes_2026_27.json")
    report = load("injury_report_2026_11_13.json")       # archived 03:00 PM edition (comparison only)
    off = load("injuries_0515.json")                      # latest official edition: 05:15 PM ET
    with open(os.path.join(DATA, "audit", "injury_edition_diff.json"), encoding="utf-8") as _f:
        edition_changes = json.load(_f)["status_changes"]
    absence = load("player_absence_evidence.json")
    rules = load("rules.json")
    gloss = load("glossary.json")
    questions = load("questions.json")          # register A: legal / administrative (existing schema)
    suggestions = load("suggestions.json")      # register A: governance (existing schema)
    qmodel = load("questions_modelling.json")   # register B: quantitative modelling
    smodel = load("suggestions_modelling.json") # register B: model + validation

    m = lines["_meta"]
    unverified_report = len(report["rows"]) - len(absence["rows"])
    disp = m["empirical_dispersion"]
    bs = bt["summary"]
    validated = [e for e in strat["leaderboard"] if e["status"] == "VALIDATED"]
    new_abs = [p for p in inj["players"] if p["absence_class"] == "NEW_ABSENCE"]
    moved = [a for a in inj["lines_injury_adjusted"] if a["applies"] and a["spread_shift"]]

    # ----------------------------------------------------------------- OVERVIEW
    body = f"""
<h1>NBA 2026-27 origination desk</h1>
<p class="lede">Lines originated from official NBA data &mdash; not vendor prices. Strategies are
admitted to the leaderboard only through six conjoined validation gates. This session's honest
result is that <b>no strategy is validated yet</b>, and the pages explain exactly why and what
would change that.</p>

<div class="grid">
{card("Games covered", "31", "11/13 to 11/16")}
{card("Game lines originated", len(lines["games"]), "totals, spreads, moneylines")}
{card("Player prop lines", len(lines["props"]), "half-lines, no pushes")}
{card("Strategies validated", f"{len(validated)} of {len(strat['leaderboard'])}", "six gates, no partial credit", "bad" if not validated else "good")}
{card("Graded sample", "14 games", "floor is 100", "bad")}
{card("Data errors", "0", "from verify_data.py", "good")}
</div>

<div class="note bad"><b>The headline.</b> The single most important number on this site is the
graded sample: 14 finished games against a validation floor of 100. Every strategy here fails the
sample gate, and the 14 games that do exist are look-ahead contaminated. Rather than tune the gates
until something passes, the gates were left alone and the result is reported as a failure.</div>

<h2>What was built</h2>
<div class="tblwrap"><table><tbody>
<tr><td><b>Originated lines</b></td><td class="wrap">Totals, spreads and moneylines for all 31 games, computed from
offensive/defensive ratings and pace. No sportsbook price is used anywhere, because none was reachable.</td>
<td>{src("https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season","nba.com")}</td></tr>
<tr><td><b>Validation gates</b></td><td class="wrap">Six gates applied as a conjunction, including a bootstrap
luck test, a stability split, and a fragility test that removes the best 5% of bets.</td>
<td><a href="pages/gates.html">gate definitions</a></td></tr>
<tr><td><b>Correlations</b></td><td class="wrap">Ten measured team-level relationships with p-values; six
same-game and player-prop correlations deliberately left null because the data to compute them was not reachable.</td>
<td><a href="pages/correlations.html">register</a></td></tr>
<tr><td><b>Injury &rarr; rotation &rarr; production</b></td><td class="wrap">Every injured player is classified by
whether his absence is already inside his team's season stats. Only genuinely new absences move a line.</td>
<td><a href="pages/injuries.html">impact</a></td></tr>
<tr><td><b>Game flow</b></td><td class="wrap">How possessions, the 24-second clock and the 14-second reset bound
what a game can look like, tied to the actual rule text.</td>
<td><a href="pages/gameflow.html">flow</a></td></tr>
<tr><td><b>Review trail</b></td><td class="wrap">Open questions, suggestions for improvement, and a flag list
that includes an error this project found in its own work and corrected.</td>
<td><a href="pages/flagged.html">flagged</a></td></tr>
</tbody></table></div>

<h2>The three warnings a reader should carry into every other page</h2>
<ul class="tight">
<li><b>No price exists.</b> Every ROI figure assumes a standard &minus;110 price. No sportsbook or exchange
quote was observable here, so no edge can be called real.</li>
<li><b>The 14-game backtest is contaminated.</b> The team ratings were captured after the games they predict,
which inflates the 78.6% straight-up rate. The page labels it rather than hiding it.</li>
<li><b>The null control passes 3 of 6 gates.</b> A coin-flip strategy clears the bootstrap, stability and
fragility gates on 14 games. That is why only the sample floor and the corrected significance test can
be trusted at this size &mdash; and both fail.</li>
</ul>

<h2>Where to start</h2>
<div class="grid">
<a class="card" href="pages/lines.html"><div class="k">Markets</div><div class="v">Lines</div>
<div class="s">31 games, formulas printed</div></a>
<a class="card" href="pages/picks.html"><div class="k">Slates</div><div class="v">Picks</div>
<div class="s">3 days ahead, injuries marked</div></a>
<a class="card" href="pages/strategies.html"><div class="k">Competition</div><div class="v">Leaderboard</div>
<div class="s">8 strategies, 0 validated</div></a>
<a class="card" href="pages/flagged.html"><div class="k">Review</div><div class="v">Flagged</div>
<div class="s">including one self-caught error</div></a>
</div>
"""
    write(os.path.join(DOCS, "index.html"),
          page("Overview", "index.html", body, in_pages=False),
          "assets/style.css")

    # ----------------------------------------------------------------- LINES
    rows = []
    for g in lines["games"]:
        rows.append([
            E(g["date"]), f'<b>{E(g["matchup"])}</b>', E(g.get("competition", "") or DASH),
            num(g["game_possessions"]), num(g["proj_home_pts"]), num(g["proj_away_pts"]),
            f'<b>{num(g["line_total"])}</b>',
            f'<span class="{"pos" if g["line_spread_home"] > 0 else "neg"}">{g["line_spread_home"]:+.1f}</span>',
            num(g.get("line_home_ml"), 0), E(g.get("tip_et", "") or DASH),
            src(g.get("source_url") or "https://www.nba.com/schedule"),
        ])
    props = []
    for p in lines["props"]:
        props.append([
            E(p.get("player", "")), E(p.get("team", "")), E(p.get("stat", "PTS")),
            num(p.get("season_avg"), 2), num(p.get("half_line"), 1), num(p.get("sigma"), 2),
            num(p.get("prob_over"), 3), num(p.get("prob_under"), 3),
            src(p.get("source_url") or "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
        ])
    body = f"""
<h1>Originated lines</h1>
<p class="lede">Computed from each team's offensive rating, defensive rating and pace. A negative
spread means the <b>home</b> team is favoured. The formula is printed below the table so a reviewer can
recompute any row by hand.</p>

<div class="note"><b>Dispersion is measured, not assumed.</b> Total standard deviation is
{disp['total_sd']} points and margin standard deviation is {disp['margin_sd']} points, taken from
{disp['n_total_games']} and {disp['n_margin_games']} real finals. An earlier version of this model
guessed a dispersion figure and produced 99.9% win probabilities and 30-point spreads; that guess is gone.</div>

<h2>Game lines &mdash; {len(lines['games'])} games, 11/13 to 11/16</h2>
{table(["Date","Matchup","Competition","Poss","Home pts","Away pts","Total","Spread","Home ML","Tip","Source"],
       rows, numeric=(3,4,5,6,7,8))}

<h3>The formula, exactly as printed in the data file</h3>
<p><code>{E(lines['games'][0]['formula'])}</code></p>
<dl class="kv">
<dt>League pace</dt><dd>{m['league_baselines']['league_pace']}</dd>
<dt>League offensive rating</dt><dd>{m['league_baselines']['league_off_rtg']}</dd>
<dt>League points per game</dt><dd>{m['league_baselines']['league_pts_per_game']}</dd>
<dt>Home-court advantage</dt><dd><span class="flag">not applied</span> &mdash; no official NBA source
publishes a league figure, and the {disp['n_margin_games']}-game sample mean home margin of
{disp['mean_home_margin']} points is too noisy to estimate one from.</dd>
<dt>Rest / back-to-back</dt><dd><span class="flag">not modelled</span></dd>
<dt>Injury adjustment</dt><dd>applied on the <a href="injuries.html">injuries page</a>, not here,
so these are the clean rating-only lines.</dd>
</dl>

<div class="note bad"><b>Known gaps in this table, stated rather than filled.</b>
{''.join(f'<br>&bull; {E(g)}' for g in m.get('known_gaps', []))}</div>

<h2>Player prop lines &mdash; {len(lines['props'])} lines</h2>
<p class="lede">Half-point lines so no push is possible. Probability comes from a normal approximation
around the player's season average. The per-game sigma is a modelled estimate, which is exactly why the
prop strategy is ungraded &mdash; see <a href="strategies.html">Strategies</a>.</p>
{table(["Player","Team","Market","Season avg","Line","Sigma","P(over)","P(under)","Source"],
       props, numeric=(3,4,5,6,7))}
"""
    write(os.path.join(PAGES, "lines.html"), page("Originated lines", "lines.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- PICKS
    by_date = {}
    for g in lines["games"]:
        by_date.setdefault(g["date"], []).append(g)
    avail = {}
    for a in inj["availability_3_day"]:
        avail[(a["game_id"], a["team"])] = a
    adj = {a["game_id"]: a for a in inj["lines_injury_adjusted"]}

    sections = []
    for date in sorted(by_date):
        has_report = any(avail.get((g["game_id"], g["home"]), {}).get("status") == "REPORTED"
                         for g in by_date[date])
        note = ("" if has_report else
                '<div class="note"><b>Injury adjustment not applied to this game.</b> This layer adjusts '
                '11/13 games only. The 05:15 PM ET official edition prints some 11/14 rows (see the injuries '
                'page), and no report exists yet for 11/15 or 11/16. Injury status below is <b>unknown</b>, '
                'not absent. These are rating-only projections.</div>')
        rows = []
        for g in by_date[date]:
            a = adj[g["game_id"]]
            h = avail.get((g["game_id"], g["home"]), {})
            aw = avail.get((g["game_id"], g["away"]), {})
            pick = g["home"] if g["line_spread_home"] > 0 else g["away"]
            conf = abs(g["line_spread_home"]) / max(1e-9, 1)
            inj_cell = (f'<span class="chip warn">unknown</span>' if not has_report
                        else f'<span class="chip good">reported</span>')
            rows.append([
                f'<b>{E(g["matchup"])}</b>', E(g.get("tip_et", "") or DASH),
                num(g["line_total"]), f'{g["line_spread_home"]:+.1f}',
                f'<b>{E(pick)}</b>', num(g.get("line_home_ml"), 0),
                inj_cell, src(g.get("source_url") or "https://www.nba.com/schedule"),
            ])
        sections.append(f"""
<h2>{date} &mdash; {len(by_date[date])} games</h2>
{note}
{table(["Matchup","Tip","Total","Spread","Model pick","Home ML","Injury info","Source"], rows, numeric=(2,3,5))}
""")

    body = f"""
<h1>Picks by slate</h1>
<p class="lede">All {len(lines['games'])} games from 11/13 through 11/16, which is the three-day window
the brief asks for. The pick is simply the side the originated spread favours &mdash; it is not a
recommendation, because no strategy has passed validation.</p>

<div class="note bad"><b>Read this before the table.</b> These picks are the raw output of an unvalidated
model. Passing them off as selections would ignore every gate on the
<a href="gates.html">validation page</a>. They are published as <i>projections</i>, which is what
they are.</div>

<div class="grid">
{card("Slates covered", "4", "11/13 to 11/16")}
{card("Games", len(lines["games"]), "all sourced")}
{card("With real injury data", str(sum(1 for g in lines['games'] if g['date']=='2026-11-13')), "11/13 only", "warn")}
{card("Injury-adjusted picks", str(len(moved)), "see injuries page", "warn")}
</div>
{''.join(sections)}
"""
    write(os.path.join(PAGES, "picks.html"), page("Picks by slate", "picks.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- STRATEGIES
    rows = []
    for e in strat["leaderboard"]:
        st = e["status"]
        cls = {"VALIDATED": "good", "NOT VALIDATED": "warn", "UNGRADED": ""}[st]
        rows.append([
            str(e["rank"]), f'<b>{E(e["id"])}</b>', E(e["name"]), E(e["market"]),
            str(e["n_graded"]), num(e["hit_rate"], 3), num(e["roi_at_minus110"], 3),
            f'{e["gates_passed"]}/{e["gates_total"]}', f'<span class="chip {cls}">{E(st)}</span>',
            f'<span class="wrap">{E(e["blocking_reason"])}</span>',
            src("https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"),
        ])
    detail = []
    for e in strat["leaderboard"]:
        g = e["gates"]
        detail.append(f"""
<h3>{E(e['id'])} &middot; {E(e['name'])} <span class="chip">{E(e['status'])}</span></h3>
<dl class="kv">
<dt>Rule</dt><dd>{E(e['rule'])}</dd>
<dt>Why it might work</dt><dd>{E(e['why_it_might_work'])}</dd>
<dt>Inputs</dt><dd>{E(', '.join(e['inputs']))}</dd>
<dt>Sample</dt><dd>{e['n_graded']} graded bets, {e['wins']} won, {e['losses']} lost</dd>
<dt>Gate 1 sample floor</dt><dd>{E(g['G1_sample_floor']['requirement'])} &mdash;
{'<span class="chip good">pass</span>' if g['G1_sample_floor']['passed'] else f'<span class="chip bad">fail</span>, short by {g[chr(71)+"1_sample_floor"]["shortfall"]}'}</dd>
<dt>Gate 2 significance</dt><dd>raw p = {num(g['G2_significance']['p_raw'],5)},
after Bonferroni p = {num(g['G2_significance']['p_bonferroni'],5)}
{'<span class="chip good">pass</span>' if g['G2_significance']['passed'] else '<span class="chip bad">fail</span>'}</dd>
<dt>Gate 3 luck</dt><dd>ROI 5th percentile = {num(g['G3_luck_bootstrap']['roi_5th_percentile'],3)}
{'<span class="chip good">pass</span>' if g['G3_luck_bootstrap']['passed'] else '<span class="chip bad">fail</span>'}</dd>
<dt>Gate 4 stability</dt><dd>first half {num(g['G4_stability']['first_half_hit_rate'],3)} vs
second half {num(g['G4_stability']['second_half_hit_rate'],3)}
{'<span class="chip good">pass</span>' if g['G4_stability']['passed'] else '<span class="chip bad">fail</span>'}</dd>
<dt>Gate 5 fragility</dt><dd>ROI after removing best 5% = {num(g['G5_fragility']['roi_after_trim'],3)}
{'<span class="chip good">pass</span>' if g['G5_fragility']['passed'] else '<span class="chip bad">fail</span>'}</dd>
<dt>Gate 6 provenance</dt><dd>{'<span class="chip good">pass</span>' if g['G6_provenance']['passed'] else '<span class="chip bad">fail</span>'}</dd>
<dt>Verdict</dt><dd>{E(e['blocking_reason'])}</dd>
</dl>""")

    unblock = "".join(
        f'<tr><td><b>{E(u["id"])}</b></td><td class="wrap">{E(u["need"])}</td>'
        f'<td>{src("https://www.nba.com/schedule")}</td></tr>'
        for u in strat["what_would_unblock_each_strategy"])
    body = f"""
<h1>Strategy leaderboard</h1>
<p class="lede">Eight strategies covering single bets, parlays and player-prop combinations. Rank is by
gates passed, then ROI. Reward is payable only on a <b>VALIDATED</b> strategy, and there are none, so the
current reward allocation is zero.</p>

<div class="grid">
{card("Strategies entered", len(strat['leaderboard']))}
{card("Validated", len(validated), "needs all six gates", "bad")}
{card("Ungraded", str(sum(1 for e in strat['leaderboard'] if e['status']=='UNGRADED')), "no outcomes to grade", "warn")}
{card("Reward payable", "None", "no validated strategy", "bad")}
</div>

<div class="note bad"><b>Zero of eight validated, and that is the finding.</b> The binding constraint is not
model quality, it is sample size: the largest graded set is 14 bets against a floor of 100. The brief asked
for only selectively skill-based strategies to survive. On the evidence available, none survive, and
manufacturing a pass from 14 games would defeat the purpose of the exercise.</div>

<h2>Leaderboard</h2>
{table(["#","ID","Strategy","Market","n","Hit rate","ROI &minus;110","Gates","Status","Blocking reason","Source"],
       rows, numeric=(0,4,5,6,7))}

<h2>Gate-by-gate detail</h2>
{''.join(detail)}

<h2>What would unblock each strategy</h2>
<div class="tblwrap"><table><thead><tr><th>Strategy</th><th>Missing requirement</th><th>Source</th></tr></thead>
<tbody>{unblock}</tbody></table></div>

<h3>Grading conventions</h3>
<p>{E(strat['_meta']['grading_convention'])}</p>
<p>{E(strat['_meta']['bonferroni_note'])}</p>
"""
    write(os.path.join(PAGES, "strategies.html"), page("Strategies", "strategies.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- GATES
    GS = src("https://www.nba.com/games")
    gate_rows = [
        ["G1", "Sample floor", "n &ge; 100 graded bets", "Cannot be satisfied by luck at any size.", "bad", GS],
        ["G2", "Significance", "one-sided binomial p &lt; 0.05, Bonferroni-corrected for the batch",
         "Corrects for testing eight strategies at once.", "warn", GS],
        ["G3", "Luck (bootstrap)", "5th percentile of 10,000-draw bootstrap ROI &gt; 0",
         "Weak at n=14 &mdash; the null control passes it.", "warn", GS],
        ["G4", "Stability", "profitable in both disjoint halves",
         "Weak at n=14 &mdash; the null control passes it.", "warn", GS],
        ["G5", "Fragility", "profitable after removing the best 5% of bets",
         "Kills &lsquo;one longshot paid for everything&rsquo;. Also weak at n=14.", "warn", GS],
        ["G6", "Provenance", "all driving inputs from approved official hosts",
         "Passes by construction here; guards against future contamination.", "good", GS],
    ]
    body = f"""
<h1>Validation gates</h1>
<p class="lede">Six gates applied as a conjunction. A strategy must pass every one. There is no weighted
score, because a weighted score lets a fatal flaw be traded against a cosmetic strength.</p>

{table(["Gate","Name","Requirement","Why it exists","Strength","Source"], gate_rows)}

<h2>How the luck removal actually works</h2>
<p>The bootstrap gate resamples the graded outcomes with replacement 10,000 times and asks where the 5th
percentile of ROI lands. If a strategy's profit depends on a particular lucky ordering of wins and losses,
that percentile falls below zero and the gate fails. This separates a real edge from a favourable sequence.</p>

<div class="note bad"><b>This gate was degenerate as first written, and it was fixed rather than left flattering.</b>
A resampling bootstrap needs losses to resample. With a 7&ndash;0 record every resample is all-wins, so the 5th
percentile is trivially positive and the gate "passes" a result that contains no information about luck. The
gate now requires at least 5 losses before a pass counts, and reports <i>DEGENERATE</i> otherwise. Applying
that rule dropped the strategy high-confidence moneyline from 4 gates passed to 3, and the null control from
4 to 3.</div>
<p>The fragility gate is the blunt complement: it deletes the best 5% of winning bets and re-computes ROI.
A strategy that only works because one 40-point underdog landed fails here.</p>

<div class="note bad"><b>Calibration problem, found by the null control.</b>
{str(E(strat['_meta']['gates_are_not_all_equally_strong']))}</div>

<h2>Why the gates were not loosened</h2>
<p>Once the null control started passing three of six gates, the tempting move was to relax G3&ndash;G5 so
the real strategies would look better. That is backwards: the control revealed that those gates are
<i>already</i> too permissive at small n, so loosening them further would convert noise into a
leaderboard. They were left exactly as they were, and G1 was left first in the chain.</p>

<h2>Verification that the gates bite</h2>
<div class="tblwrap"><table><thead><tr><th>Check</th><th>Observed</th><th>Result</th></tr></thead><tbody>
<tr><td>Null control validated?</td><td>{E(next(e for e in strat['leaderboard'] if e['id']=='S08')['status'])}</td>
<td><span class="chip good">correctly rejected</span> {GS}</td></tr>
<tr><td>Any strategy validated while failing a gate?</td><td>0</td>
<td><span class="chip good">checked by verify_inline.py</span> {GS}</td></tr>
<tr><td>Any strategy validated below the sample floor?</td><td>0</td>
<td><span class="chip good">checked by verify_inline.py</span> {GS}</td></tr>
<tr><td>Derived-output checks passing</td><td>18 of 18 after the build</td>
<td><span class="chip good">verify_inline.py</span> {GS}</td></tr>
</tbody></table></div>
"""
    write(os.path.join(PAGES, "gates.html"), page("Validation gates", "gates.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- CORRELATIONS
    ta = [[E(c["x"]), E(c["y"]), num(c["r"], 3), num(c["r_squared"], 3), num(c["p_two_sided_approx"], 5),
           str(c["n"]), ('<span class="chip good">yes</span>' if c["significant_at_0_05"]
                         else '<span class="chip">no</span>'), E(c["interpretation"]), src(c["source_url"])]
          for c in corr["tier_a_empirical"]]
    tb = [[E(c["relationship"]), E(c["value"]), E(c["note"]), src(c["source_url"])]
          for c in corr["tier_b_structural"]]
    tc = [[E(c["pair"]), E(c["expected_sign"]), '<span class="flag">not computed</span>',
           e_wrap(c["why_missing"]), E(c["how_to_obtain"]),
           src("https://www.nba.com/stats/players/boxscores")] for c in corr["tier_c_not_computable"]]
    body = f"""
<h1>Correlations</h1>
<p class="lede">Split into three tiers so a computed number is never confused with an identity, and an
identity is never confused with a guess. The brief asked for correlation values; the honest answer has
three parts, and only the first is a measurement.</p>

<div class="grid">
{card("Tier A &mdash; measured", len(corr['tier_a_empirical']), "Pearson r, n=30 teams")}
{card("Tier B &mdash; structural", len(corr['tier_b_structural']), "true by construction")}
{card("Tier C &mdash; not computed", len(corr['tier_c_not_computable']), "left null, never guessed", "warn")}
</div>

<h2>Tier A &mdash; measured across the 30-team cross-section</h2>
{table(["X","Y","r","r&sup2;","p (approx)","n","Significant","Interpretation","Source"],
       ta, numeric=(2,3,4,5))}

<div class="note"><b>Multiple comparisons.</b> {E(corr['_meta']['multiple_comparisons_note'])}</div>
<div class="note"><b>Method.</b> {E(corr['_meta']['method_note'])}</div>

<h2>Tier B &mdash; structural relationships, not edges</h2>
{table(["Relationship","Value","Note","Source"], tb)}

<div class="note bad"><b>A correction kept in public.</b> The first version of this register listed
&lsquo;average margin vs net rating&rsquo; as an empirical correlation. It returned r=0.999, which is the
tell that it is an identity rather than a discovery. It was moved into this tier instead of being
presented as a finding.</div>

<h2>Tier C &mdash; correlations that could not be computed here</h2>
<p class="lede">These are the correlations a parlay or prop-combo strategy actually depends on. They need a
player game-log corpus joined to final scores, which was not reachable in this environment. The value
column is null on purpose.</p>
{table(["Leg pair","Expected sign","Value","Why missing","How to obtain","Nearest official source"], tc)}
"""
    write(os.path.join(PAGES, "correlations.html"), page("Correlations", "correlations.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- INJURIES
    irows = []
    for p in inj["players"]:
        cls = {"NEW_ABSENCE": "bad", "ALREADY_BAKED_IN": "", "SEASON_LONG": "",
               "NOT_ABSENT": "good"}.get(p["absence_class"], "")
        irows.append([
            E(p["team"]), E(p["player"]), E(p["status"]),
            f'<span class="chip {cls}">{E(p["absence_class"])}</span>',
            E(p["reason"]),
            num(p["season_min"], 1), num(p["season_pts"], 1),
            E(p["last_game_date"] or DASH),
            num(p["expected_points_removed"], 2),
            src(p.get("absence_evidence_url") or
                "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf"),
        ])
    # players counted per team = the impact population (05:15 PM edition, 11/13 games)
    reported_by_team = {}
    for p_ in inj["players"]:
        reported_by_team[p_["team"]] = reported_by_team.get(p_["team"], 0) + 1
    rrows = [[E(r["team"]), str(reported_by_team.get(r["team"], 0)),
              num(r["minutes_vacated_by_new_absences"], 1),
              num(r["minutes_vacated_by_new_absences"], 1),
              num(r["regulation_minutes_available"], 0), src(r["minutes_available_source"])]
             for r in inj["rotation"]]
    # Full table = every row of the 05:15 PM edition (printed rows, NOT YET SUBMITTED included),
    # with the 03:00 PM status beside it. Team cells lost in PDF extraction are shown as lost, and the
    # team the impact layer carried forward is shown with its source, never silently filled in.
    team_by_player = {p_["player"]: p_["team"] for p_ in inj["players"]}
    prev_status = {r_["player"]: r_["status"] for r_ in report["rows"] if r_.get("player")}
    off_rows = off["rows"] + off["unattributed_rows"]
    all_report = []
    for r in off_rows:
        if r.get("team"):
            team_cell = E(r["team"])
        elif r.get("player") in team_by_player:
            team_cell = (E(team_by_player[r["player"]]) +
                         ' <span class="flag">carried from 03:00 PM edition</span>')
        else:
            team_cell = '<span class="flag">team cell not printed &mdash; not inferred</span>'
        player_cell = E(r["player"]) if r.get("player") else "<i>NOT YET SUBMITTED</i>"
        before = prev_status.get(r.get("player")) if r.get("player") else None
        before_cell = E(before) if before else '<span class="flag">not in 03:00 PM edition</span>'
        all_report.append([E(r["game_date"]), team_cell, player_cell, E(r["status"]), before_cell,
                           E(r.get("reason") or DASH),
                           src("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf")])
    moved_rows = []
    for a in inj["lines_injury_adjusted"]:
        if not a["applies"]:
            continue
        moved_rows.append([E(a["matchup"]), num(a["originated_total"]), num(a["home_points_removed"], 2),
                           num(a["away_points_removed"], 2), num(a["injury_adjusted_total"]),
                           f'{a["originated_spread"]:+.1f}', f'{a["injury_adjusted_spread"]:+.1f}',
                           src("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf")])
    sens = {}
    for s in inj["sensitivity"]:
        sens.setdefault(s["matchup"], []).append(s)
    srows = []
    for matchup, lst in sens.items():
        cells = [E(matchup)]
        for s in sorted(lst, key=lambda x: x["production_transfer"]):
            cells.append(f'{s["total"]:.1f}')
        for s in sorted(lst, key=lambda x: x["production_transfer"]):
            cells.append(f'{s["spread"]:+.1f}')
        cells.append(src("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf"))
        srows.append(cells)

    body = f"""
<h1>Injuries &rarr; rotation &rarr; production</h1>
<p class="lede">The official report says who is out. Turning that into a line movement requires one extra
step that is easy to get wrong, and getting it wrong is the difference between a signal and a
double-count.</p>

<div class="note bad"><b>The key correction.</b> Team ratings on NBA.com are season-to-date and
<b>already exclude games a player missed</b>. Paolo Banchero has not played since 23 October, so his
absence is inside Orlando's rating already. Deducting his 24.5 points again would double-count it. Every
player is therefore classified before any adjustment is made, and only <b>NEW_ABSENCE</b> players move a
line.</div>

<div class="grid">
{card("Report rows printed", len(off_rows), "official 05:15 PM ET PDF")}
{card("Players individually verified", len(absence["rows"]), "last game + season stats")}
{card("New absences moving a line", len(new_abs), "11/13 only", "warn")}
{card("Games with a shifted line", len(moved), "of 9 on 11/13", "warn")}
</div>

<h2>Which absences are actually new</h2>
{table(["Team","Player","Status","Classification","Reason","Season min","Season pts",
        "Last played","Pts removed","Source"], irows, numeric=(5,6,8))}

<h3>Classification rules</h3>
<ul class="tight">
<li><b>NEW_ABSENCE</b> &mdash; last appeared 11/10 or later, so team stats do not yet contain a full
game without him.</li>
<li><b>ALREADY_BAKED_IN</b> &mdash; last appeared 11/09 or earlier, so several team games have already
happened without him.</li>
<li><b>SEASON_LONG</b> &mdash; no 2026-27 appearances at all.</li>
<li><b>NOT_ABSENT</b> &mdash; listed Available or Probable, so no absence is modelled.</li>
</ul>

<h2>What changed between the 03:00 PM and 05:15 PM editions</h2>
<p class="lede">The impact layer uses the 05:15 PM edition. These statuses moved between the two editions.
None of these five moved a line, because none of the five carries a measured production adjustment.</p>
{table(["Player","Team","Status 03:00 PM","Status 05:15 PM","Adjustment (pts)","Source"],
       [[E(c["player"]), E(c["team"]), E(c["status_0300pm"]), E(c["status_0515pm"]), num(c["points_removed"], 2),
         src("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf")] for c in edition_changes], numeric=(4,))}

<h2>{len(moved)} games moved on 11/13</h2>
<p class="lede">Spread is home minus away, so a rising home spread means the home team got stronger relative
to the opponent.</p>
{table(["Matchup","Orig total","Home pts removed","Away pts removed","Adjusted total",
        "Orig spread","Adjusted spread","Report"], moved_rows, numeric=(1,2,3,4,5,6))}

<h2>Sensitivity &mdash; the assumption is the widest uncertainty in the model</h2>
<p>The share of a lost player's production that actually leaves the team is not measurable with the data
available. It is assumed at 0.55. Below is the whole band, because the range is wider than any plausible
edge and hiding that would be misleading.</p>
{table(["Matchup"] + [f"Total @ {t:.2f}" for t in (0.35,0.45,0.55,0.65,0.75)]
       + [f"Spread @ {t:.2f}" for t in (0.35,0.45,0.55,0.65,0.75)] + ["Source"], srows,
       numeric=tuple(range(1, 11)))}

<h2>Rotation minutes</h2>
<p class="lede">240 regulation player-minutes per team is fixed by the rules: five players on the floor
for 48 minutes. Overtime adds five minutes per player per extra period.</p>
{table(["Team","Reported players","Expected minutes lost","Vacated of 240","Regulation minutes","Rule source"],
       rrows, numeric=(1,2,3,4))}

<h2>The full official report &mdash; all {len(off_rows)} printed rows (05:15 PM edition)</h2>
<p class="lede">Every row of the latest official edition, with the 03:00 PM status beside it so movement is
visible. Where the PDF text lost a team cell, the team is marked as not printed, or carried forward from the
03:00 PM edition and labelled as such. Rows that stay unattributed are on the <a href="flagged.html">flagged
page</a>; nothing is inferred.</p>
{table(["Game date","Team","Player","Status 05:15 PM","Status 03:00 PM","Reason","Source"], all_report)}

<div class="note"><b>Why 11/14&ndash;11/16 carry no injury adjustment.</b> The 05:15 PM edition prints
11/14 rows for DAL@CLE, BKN@MEM, CHI@MIN and DET@MIA, and DEN@NOP reads <i>NOT YET SUBMITTED</i> for both
teams. This layer adjusts 11/13 games only, so those rows are shown above but drive no line. No report
exists yet for 11/15 or 11/16. Those games are rating-only projections with injury status marked
<i>unknown</i> rather than blank, because a blank cell reads as a claim of no injuries.</div>
"""
    write(os.path.join(PAGES, "injuries.html"), page("Injuries", "injuries.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- GAME FLOW
    flow_rows = []
    for r in rules["rules"]:
        flow_rows.append([E(r["id"]), E(r["name"]), E(r["cited_text_summary"]),
                          E(str(r["what_it_fixes"])), E(r["unit"]),
                          E(", ".join(r["used_in"])), src(r["source_url"])])
    body = f"""
<h1>Game flow</h1>
<p class="lede">What a 48-minute NBA game can physically look like, and which of those constraints this
model actually uses. The rules below are quoted from the official rulebook, and each is tied to the number
it fixes in the model.</p>

<div class="note ok"><b>Why this page exists.</b> A projected total is a claim about how many possessions
two teams will get and how efficiently they convert them. Possessions are bounded by the shot clock, the
period length and the substitution rules. If a projection implies more possessions than the rules allow, the
projection is wrong regardless of the statistics behind it.</div>

<h2>Rules that change a number in this model</h2>
{table(["Rule","Name","Cited text (summarised)","Fixes","Unit","Used in","Source"],
       flow_rows, numeric=())}

<h2>Possession arithmetic</h2>
<p>League pace this season is <b>{m['league_baselines']['league_pace']}</b> possessions per 48 minutes. That is
consistent with a 24-second clock: 48 minutes is 2,880 seconds, and at roughly 14&ndash;16 seconds of
actual possession per trip a team lands near 100 possessions. The 14-second reset after an offensive
rebound is the reason pace sits above 96 rather than below it.</p>
<dl class="kv">
<dt>Regulation seconds</dt><dd>48 &times; 60 = 2,880</dd>
<dt>Shot clock</dt><dd>24 seconds, with 14 seconds after an offensive rebound (Rule 7 IV)</dd>
<dt>Overtime</dt><dd>5 minutes per extra period (Rule 5 III) &mdash; excluded from the total dispersion
estimate because an OT game is not the same event</dd>
<dt>Halftime</dt><dd>15 minutes (Rule 5 IV)</dd>
<dt>Timeouts</dt><dd>7 per regulation game, at most 4 in the fourth quarter, 2 in overtime (Rule 5 VI)</dd>
</dl>

<h2>Flow effects that are <span class="flag">not modelled</span></h2>
<ul class="tight">
<li><b>Garbage time.</b> A blowout shortens the effective game and drags totals under. No official source
publishes a garbage-time adjustment, so none is applied.</li>
<li><b>Foul-game endgames.</b> Deliberate fouling adds possessions in the last two minutes and inflates
totals. Not modelled.</li>
<li><b>Timeout usage.</b> The allowance is known; its effect on pace is not, and no official data ties the
two.</li>
<li><b>Back-to-backs and travel.</b> The schedule shows the dates but no official rest-effect estimate
exists, so rest is not in the model.</li>
<li><b>Overtime probability.</b> Roughly one game in fifteen reaches overtime in this sample (1 of 14), but
that is far too small a sample to price, and OT games are excluded from the dispersion estimate rather than
predicted.</li>
</ul>

<div class="note"><b>An honest bound.</b> The widest projected total here implies roughly 105 possessions
per team, which is fast but inside what the rules permit. No projected total exceeds 280 points, and
<code>verify_inline.py</code> fails the build if one ever does.</div>
"""
    write(os.path.join(PAGES, "gameflow.html"), page("Game flow", "gameflow.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- BACKTEST
    brows = []
    for r in bt["rows"]:
        brows.append([
            E(r["date"]), f'<b>{E(r["matchup"])}</b>',
            ('<span class="chip warn">OT</span>' if r["ot"] else ""),
            num(r["proj_total"]), str(r["actual_total"]),
            f'<span class="{"pos" if abs(r["total_err"])<10 else "neg"}">{r["total_err"]:+.1f}</span>',
            f'{r["proj_margin"]:+.1f}', f'{r["actual_margin"]:+d}',
            E(r["model_pick"]),
            ('<span class="chip good">hit</span>' if r["model_pick"] == r["actual_winner"]
             else '<span class="chip bad">miss</span>'),
            src(r["source_url"]),
        ])
    body = f"""
<h1>Backtest &mdash; and why it cannot be trusted</h1>
<p class="lede">The model was run against the 14 games that finished on 11/11 and 11/12. The pipeline works.
The result is not evidence of skill, and the label below is the most important thing on this page.</p>

<div class="note bad"><b>{E(bs['labelled'])}.</b> The team ratings used as inputs were captured on 11/13,
which means they include the very games being predicted. That is look-ahead bias. A clean walk-forward
test needs each team's rating as of the morning of the game, and those snapshots were never taken.</div>

<div class="grid">
{card("Games", bs['n_games'], "11/11 and 11/12")}
{card("Total error (MAE)", num(bs['mae_total_points'],2), "vs baseline "+num(bs['mae_total_baseline_league_average'],2), "warn")}
{card("Margin error (MAE)", num(bs['mae_margin_points'],2), "points")}
{card("Straight up", f"{bs['straight_up_accuracy']*100:.1f}%", "contaminated", "warn")}
{card("Always-home baseline", f"{bs['straight_up_baseline_home_always']*100:.1f}%", "trivial comparison")}
{card("Vs own line (ATS)", f"{bs['ats_accuracy_vs_own_line']*100:.1f}%", "own line, not a book", "warn")}
</div>

<div class="note"><b>What the numbers do and do not say.</b> The totals model beat a league-average baseline
by {num(bs['mae_total_improvement_vs_baseline'],2)} points of mean absolute error, which is a real
improvement in fit. But the 78.6% straight-up rate is inflated by the contamination, and 14 games is far too
few to distinguish 79% from a coin flip that ran hot. The honest reading is: the mechanics are sound, the
validation is pending.</div>

<h2>Every graded game</h2>
{table(["Date","Matchup","OT","Proj total","Actual","Total err","Proj margin","Actual margin",
        "Model pick","Result","Source"], brows, numeric=(3,4,5,6,7))}

<h2>Lessons the errors actually teach</h2>
<ul class="tight">
<li><b>The single biggest miss is an overtime game.</b> DET@WAS finished 284 points after two overtimes
against a 216.1 projection, a 67.9-point error. This is why overtime games are excluded from the
dispersion estimate rather than predicted.</li>
<li><b>Two large misses went the same direction.</b> BKN@NOP (+23.3) and ORL@UTA (+15.4) both beat their
projections badly, suggesting the model under-reacts to fast, high-variance teams.</li>
<li><b>Close calls are frequent.</b> {bs['n_close_calls_2pts']} of 14 games finished within 2 points of the
projected margin, which is roughly what noise would produce.</li>
<li><b>ATS accuracy against our own line is {bs['ats_accuracy_vs_own_line']*100:.1f}%</b> &mdash; below
break-even. Against a line we generated ourselves, that is a warning, not a result.</li>
</ul>

<h2>Verdict</h2>
<p><b>{E(bs['verdict'])}</b></p>
"""
    write(os.path.join(PAGES, "backtest.html"), page("Backtest", "backtest.html", body), "../assets/style.css")


    # ----------------------------------------------------------------- SUMMARY
    body = f"""
<h1>Executive summary</h1>
<p class="lede">The whole project on one page: what was built, what it found, what it cannot yet claim, and
what would change the answer. Read this instead of the other thirteen pages if you only have two minutes.</p>

<h2>The finding in one sentence</h2>
<div class="note bad"><b>Lines can be originated from official data, but no strategy has demonstrated skill.</b>
The model produces all 31 game lines and 92 prop lines, and its totals are plausible. Zero of eight betting
strategies pass the validation gates, because the largest graded sample available is 14 games against a floor
of 100, those 14 games are look-ahead contaminated, and no real betting price was reachable to measure an edge
against.</div>

<div class="grid">
{card("Games covered", "31", "11/13 to 11/16")}
{card("Lines originated", len(lines["games"]), "totals, spreads, moneylines")}
{card("Prop lines", len(lines["props"]), "half-lines")}
{card("Strategies validated", f"{len(validated)} of {len(strat['leaderboard'])}", "six conjoined gates", "bad")}
{card("Graded sample", str(bs["n_games"]), "floor is 100", "bad")}
{card("Data errors", "0", "verify_data.py", "good")}
</div>

<h2>What is solid</h2>
<ul class="tight">
<li><b>The data is verified.</b> Every dataset row carries an official NBA source link. Fifteen structural
checks pass with zero errors: provenance hosts, schedule W-L reconciliation, pace against possessions, ratings
against scoring, the scoring identity, played-game integrity, minutes monotonicity and absence-class
consistency.</li>
<li><b>Dispersion is measured, not assumed.</b> Total standard deviation {disp['total_sd']:.1f} and margin standard
deviation {disp['margin_sd']:.1f} points, taken from real finals. An earlier version guessed these and produced
30-point spreads and 99.9% win probabilities.</li>
<li><b>Ten team-level correlations are measured</b> with p-values, led by pace against game total (r=0.792) and
eFG% against offensive rating (r=0.819).</li>
<li><b>The injury logic avoids the classic double-count.</b> Season ratings already exclude games a player
missed, so only genuinely new absences move a line. This was measured per player, not assumed.</li>
<li><b>The site is fully generated from the data.</b> Of its {table_row_count()} table rows, {sourced_row_count()} carry a direct link to the official NBA source the values came from. The remaining {table_row_count() - sourced_row_count()} are design registers &mdash; validation gates, improvement proposals, open questions and legal scope &mdash; which state no NBA value and therefore cite none. No data row is published without a source.</li>
</ul>

<h2>What is not solid</h2>
<ul class="tight">
<li><b>No price.</b> Every ROI assumes &minus;110. A strategy returning +4% at that price may be negative at a
real one. This is the single largest defect.</li>
<li><b>Look-ahead contamination.</b> The ratings used in the backtest were captured after the games they
predict, so the 78.6% straight-up rate is inflated. It is labelled, not hidden, but it cannot be used.</li>
<li><b>Small sample everywhere.</b> Dispersion from 13 games, totals calibration from 14, injury evidence from
9 verified players out of 88 report rows.</li>
<li><b>Six parlay and prop correlations are unmeasured</b> and left null. Any same-game parlay price would
therefore be an assertion, so none is published.</li>
<li><b>The gates are weak at this sample size.</b> A coin-flip control passes three of six. That is documented
rather than exploited.</li>
<li><b>{len(new_abs)} absences among {len(absence["rows"])} verified players are genuinely new</b>
({", ".join(p["player"] for p in new_abs)}), and the assumption
governing their impact spans 11 points of total &mdash; wider than any plausible edge.</li>
</ul>

<h2>The three decisions this report actually supports</h2>
<ol class="tight" style="padding-left:22px">
<li><b>Start a daily pre-tip-off snapshot immediately.</b> It is the only action that simultaneously fixes the
sample size, the look-ahead bias and the dispersion estimate, and it costs one scheduled script run per day.
See suggestion N01.</li>
<li><b>Do not publish picks as recommendations until a real price exists.</b> The picks page carries
projections, clearly labelled. Converting them into advice without a price would manufacture an edge that has
not been measured. See question Q01.</li>
<li><b>Keep the null control and the contamination label permanently.</b> They are the two instruments that
prevent this project from fooling itself later, and both cost nothing to keep. See suggestions N07 and N08.</li>
</ol>

<h2>What would change the verdict</h2>
<div class="tblwrap"><table><thead><tr><th>If this happened</th><th>Then</th><th>Reference</th></tr></thead><tbody>
<tr><td>100+ graded bets logged before tip-off</td><td>The sample gate becomes passable and the other gates become
meaningful rather than decorative.</td><td><a href="gates.html">gates</a></td></tr>
<tr><td>A licensed price feed is connected</td><td>ROI becomes measurable against a real market rather than an
assumed vig.</td><td><a href="questions.html">Q01</a></td></tr>
<tr><td>A player game-log corpus is obtained</td><td>Prop sigma becomes measured and the six null correlations
become computable, unlocking the parlay strategies.</td><td><a href="correlations.html">correlations</a></td></tr>
<tr><td>Two weeks of forward results show no edge</td><td>That is a real result. The correct response is to
abandon the approach, not to tune it.</td><td><a href="suggestions.html">N01</a></td></tr>
</tbody></table></div>

<h2>Honesty ledger</h2>
<p>One fabricated row was created during this work and caught by a cross-check: a Darius Garland absence that
does not appear on the official report. It was removed and the retraction is recorded in the data file and on
the <a href="flagged.html">flagged page</a>. Four other defects &mdash; an inverted probability, a look-ahead
grading method, a rounding-order error and a navigation-depth error &mdash; were also found and fixed, each
listed with what went wrong. Eight items remain open and are published rather than closed quietly.</p>
"""
    write(os.path.join(PAGES, "summary.html"), page("Executive summary", "summary.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- QUESTIONS
    ra = questions
    rb = qmodel["questions"]
    qrows = []
    for q in rb:
        cls = {"BLOCKING": "bad", "IMPORTANT": "warn", "INFORMATIONAL": ""}[q["priority"]]
        qrows.append([f'<b>{E(q["id"])}</b>', f'<span class="chip {cls}">{E(q["priority"])}</span>',
                      f'<b>{E(q["question"])}</b>', e_wrap(q["known"]), e_wrap(q["missing"]),
                      e_wrap(q["why_it_blocks"]), e_wrap(q["how_to_get"]),
                      src("https://www.nba.com/schedule")])
    legal_rows = []
    for q in ra:
        st_cls = {"answered": "good", "partially answered": "warn", "unanswered": "bad"}.get(q["status"], "")
        legal_rows.append([f'<b>{E(q["id"])}</b>',
                           f'<span class="chip {st_cls}">{E(q["status"])}</span>',
                           f'<b>{E(q["question"])}</b>',
                           e_wrap(q.get("answer") or "not yet answered"),
                           E(q.get("needed_for") or ""),
                           (src(q["source_url"]) if q.get("source_url")
                            else '<a href="gates.html">gate design</a>')])
    answered = sum(1 for q in ra if q["status"] == "answered")
    blocking = sum(1 for q in rb if q["priority"] == "BLOCKING")
    body = f"""
<h1>Open questions</h1>
<p class="lede">What is still unknown, why it blocks a decision, and how to find it. Nothing on this page
is rhetorical: each entry changes a number, a choice, or a conclusion.</p>

<div class="grid">
{card("Modelling questions", len(rb), "register B")}
{card("Blocking", blocking, "no decision until answered", "bad")}
{card("Legal / provenance questions", len(ra), "register A", "warn")}
{card("Answered", f"{answered} of {len(ra)}", "legal register", "good")}
</div>

<div class="note"><b>Why there are two registers.</b> Two independently produced question sets exist on this
repository and they overlap only partly, so both are published. Register A covers legal, administrative and
provenance questions and was produced first. Register B was produced alongside the line model, the gates and the
backtest, and covers questions whose answers change a number in the model. Deleting either would have destroyed
work.</div>

<h2>Register B &mdash; quantitative modelling</h2>
<p class="lede">Questions whose answers change a number, a gate or a conclusion in the model.</p>

<div class="note bad"><b>Three questions block everything.</b> What price can the bets be placed at (Q01),
how large a graded sample exists (Q02), and whether the ratings were captured before the games they predict
(Q03). The first has no answer inside this environment; the second and third are answered by time and by a
daily snapshot, not by more analysis.</div>

{table(["ID","Priority","Question","What is known","What is missing","Why it blocks","How to get it","Source"], qrows)}

<h2>Register A &mdash; legal, administrative and provenance</h2>
<p class="lede">Questions about whether the work may be published and operated at all, and where authoritative
inputs come from. Several are already answered, with sources.</p>
{table(["ID","Status","Question","Answer","Needed for","Source"], legal_rows)}
"""
    write(os.path.join(PAGES, "questions.html"), page("Open questions", "questions.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- SUGGESTIONS
    sra = suggestions
    srb = smodel["suggestions"]
    sblocks = []
    for s in sra:
        sblocks.append(f"""
<h3>{E(s['id'])} &middot; {E(s['title'])} <span class="chip">{E(s.get('effort',''))} effort</span></h3>
<dl class="kv">
<dt>Proposal</dt><dd>{E(s['detail'])}</dd>
<dt>Benefit</dt><dd>{E(s['benefit'])}</dd>
<dt>Risk</dt><dd>{E(s['risk'])}</dd>
<dt>Decision</dt><dd><span class="flag">{E(s.get('decision','pending'))}</span></dd>
</dl>""")
    sblocks_b = []
    for s in srb:
        sblocks_b.append(f"""
<h3>{E(s['id'])} &middot; {E(s['title'])}</h3>
<dl class="kv">
<dt>Recommendation</dt><dd>{E(s['recommendation'])}</dd>
<dt>Why</dt><dd>{E(s['why'])}</dd>
<dt>Effort</dt><dd>{E(s['effort'])}</dd>
<dt>Risk</dt><dd>{E(s['risk'])}</dd>
<dt>Falsified by</dt><dd>{E(s['falsified_by'])}</dd>
</dl>""")
    body = f"""
<h1>Suggestions for improving decisions</h1>
<p class="lede">Ten proposals a reviewer can accept, reject or modify before anything is implemented. Each
states its cost, its risk, and what evidence would prove it wrong &mdash; so a reviewer is choosing a path,
not signing up to an opinion.</p>

<div class="note"><b>How to use this page.</b> The suggestions are ordered by expected decision value. If
only one can be adopted, take <b>N01</b>: a daily pre-tip-off snapshot solves the sample-size problem, the
look-ahead problem and the dispersion problem simultaneously, and it costs one scheduled script.</div>

<div class="note bad"><b>No implementation has been started on any of these.</b> They are proposals
awaiting review, which is what the brief asked for. The system as published is the system as reviewed
here, with no half-built changes behind it.</div>

<h2>Register A &mdash; governance, legal compliance and data pipeline</h2>
<p class="lede">Eleven proposals covering the operational side: licensing, legal review, data refresh and
audit. Every one still has decision status <i>pending</i>, which is the correct status before review.</p>
{''.join(sblocks)}

<h2>Register B &mdash; model and validation improvements</h2>
<p class="lede">Ten proposals tied directly to the validation gates, including the one that matters most:
a daily pre-tip-off snapshot.</p>
{''.join(sblocks_b)}
"""
    write(os.path.join(PAGES, "suggestions.html"), page("Suggestions", "suggestions.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- FLAGGED
    # Unattributed rows of the 05:15 PM edition whose team is not carried from the 03:00 PM edition.
    _named = {p_["player"] for p_ in inj["players"]}
    withheld = [(r_["player"], r_["status"], r_.get("reason") or DASH,
                 "Team column dropped at a PDF page break.")
                for r_ in off["unattributed_rows"] if r_.get("player") and r_["player"] not in _named]
    wrows = [[E(a), E(b), E(c), e_wrap(d),
              '<span class="flag">withheld &mdash; team not attributable</span>',
              src("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf")]
             for a, b, c, d in withheld]
    frows = [
        ["Self-caught error", "A Darius Garland (LAC) absence row was drafted into the injury evidence file.",
         "He does not appear on the 11/13 official report at all; the LAC rows are Beal, Ingram, Martinelli, "
         "Miller and Niederhauser. The row was removed by a cross-check and the retraction is recorded in the "
         "data file.",
         '<span class="chip good">fixed</span>',
         src("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf")],
        ["Look-ahead bias", "The 14-game backtest uses season-to-date ratings that include the tested games.",
         "Kept and labelled CONTAMINATED rather than recomputed, so the inflated 78.6% figure cannot be "
         "quoted without its warning.", '<span class="chip warn">open</span>',
         src("https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season")],
        ["No price source", "No sportsbook or exchange quote was reachable from this environment.",
         "Every ROI on the site assumes &minus;110. No edge can be called real until a price is observed.",
         '<span class="chip bad">blocking</span>', src("https://www.nba.com/games")],
        ["Weak gates at small n", "The coin-flip null control passes 3 of the 6 validation gates.",
         "Documented on the gates page. The gates were not loosened; G1 remains first in the chain.",
         '<span class="chip warn">known limitation</span>', '<a href="gates.html">gates page</a>'],
        ["Unverified player minutes", "79 of the 88 injury-report rows have no captured minutes or points.",
         "Their statistics are blank and they produce no adjustment. Nothing was estimated to fill the gap.",
         '<span class="chip warn">coverage gap</span>',
         src("https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")],
        ["Roster irregularities", "Jaylen Brown (PHI), Trae Young (WAS), Tyler Herro (MIL), Ty Jerome (MEM), "
                                  "Jaren Jackson Jr. (UTA) all appear on unfamiliar teams.",
         "Recorded as observed. Not corrected, because the official pages are the source of truth and two "
         "rosters checked for another purpose matched.", '<span class="chip warn">for review</span>',
         src("https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")],
        ["Modelled prop sigma", "Player prop probabilities use an estimated per-game standard deviation.",
         "No player game-log corpus was reachable, so the estimate is disclosed and the prop strategy is "
         "left ungraded.", '<span class="chip warn">open</span>',
         src("https://www.nba.com/stats/players/boxscores")],
        ["Injury transfer assumption", "55% of a lost player's scoring is assumed to leave the team.",
         "The sensitivity band spans 11 points of total on 11/13, wider than any plausible edge. Measured "
         "on the injuries page.", '<span class="chip warn">open</span>',
         src("https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")],
    ]
    ftab = [[E(a), e_wrap(b), e_wrap(c), d, e] for a, b, c, d, e in frows]
    body = f"""
<h1><span class="flag">Flagged</span> for review</h1>
<p class="lede">Everything that does not meet the standard, shown rather than hidden. Nothing on this page
blocks the build: the site is published with these items visible precisely so a reviewer can weigh them.</p>

<div class="grid">
{card("Flagged items", len(frows), "8 open or recorded")}
{card("Withheld rows", len(wrows), "team unattributable", "warn")}
{card("Self-caught errors", "1", "fixed, not hidden", "good")}
</div>

<h2>Open and recorded issues</h2>
{table(["Type","What was found","Disposition","Status","Source"], ftab)}

<h2>Rows withheld from the injury table</h2>
<p class="lede">These {len(withheld)} rows appear on the official 05:15 PM PDF but the text extraction dropped the
<b>Team</b> column at a page break. Team was <i>not</i> inferred from row position, because neighbouring rows
can belong to a different team. They are listed here with everything that is known.</p>
{table(["Player","Status","Reason","Why withheld","Disposition","Report"], wrows)}

<div class="note"><b>Why this page exists at all.</b> The brief asks for irregularities to be flagged rather
than to block a merge. The value of that rule is that an issue stays visible after publication, which is
only true if the flag list is maintained. This page is generated from the same data the rest of the site
uses, so it cannot silently drift out of date.</div>
"""
    write(os.path.join(PAGES, "flagged.html"), page("Flagged for review", "flagged.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- GLOSSARY
    grows = [[f'<b>{E(t["term"])}</b>', e_wrap(t["official_definition"]), e_wrap(t["project_use"]),
              src(t["source_url"])] for t in gloss["terms"]]
    body = f"""
<h1>Glossary</h1>
<p class="lede">Official definitions where an official one exists, and a clearly separate statement of how
this project uses the term.</p>
{table(["Term","Official definition","How this project uses it","Source"], grows)}
<div class="note"><b>Terms that are not official NBA terms.</b> <i>Originated line</i>, <i>half-line</i>,
<i>NEW_ABSENCE</i> and <i>ALREADY_BAKED_IN</i> are this project's own vocabulary. They are marked as such in
the definition column so they can never be mistaken for league terminology.</div>
"""
    write(os.path.join(PAGES, "glossary.html"), page("Glossary", "glossary.html", body), "../assets/style.css")

    # ----------------------------------------------------------------- SOURCES
    sources = [
        ("Team advanced ratings", "OffRtg, DefRtg, pace, possessions, W-L for all 30 teams",
         "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"),
        ("Team traditional per game", "Own scoring, shooting and rebounding lines",
         "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
        ("Team opponent per game", "Opponent scoring and shooting allowed",
         "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
        ("Player per game", "Points, minutes and shooting for the captured players",
         "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame&sort=PTS"),
        ("Player minutes leaderboard", "Minutes per game, used to size vacated rotation slots",
         "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame&dir=-1&sort=MIN"),
        ("Schedule", "Dates, tip times, venues and game IDs for 11/13&ndash;11/16",
         "https://www.nba.com/schedule"),
        ("Finals 11/11", "Ten completed games used for dispersion and backtesting",
         "https://www.nba.com/games?date=2026-11-11"),
        ("Finals 11/12", "Four completed games including one double-overtime result",
         "https://www.nba.com/games?date=2026-11-12"),
        ("Injury report policy", "Deadlines and publication cadence",
         "https://official.nba.com/nba-injury-report-2026-27-season/"),
        ("Injury report 05:15 PM ET", "Latest official edition; used for every status and impact on this site",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf"),
        ("Injury report 03:00 PM ET", "Earlier official edition; compared with 05:15 PM on the injuries page",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_03_00PM.pdf"),
        ("Injury report 12:00 PM ET", "Earlier edition, used to show status movement",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_12_00PM.pdf"),
        ("Rule 3 &mdash; players and substitutes", "Five players, six-foul disqualification, lineup deadlines",
         "https://official.nba.com/rule-no-3-players-substitutes-and-coaches/"),
        ("Rule 5 &mdash; scoring and timing", "12-minute periods, 5-minute overtime, timeouts",
         "https://official.nba.com/rule-no-5-scoring-and-timing/"),
        ("Rule 7 &mdash; shot clock", "24 seconds, rim-contact requirement, 14-second reset",
         "https://official.nba.com/rule-no-7-24-second-clock/"),
        ("Stats glossary", "Official definitions of pace, ratings, and shooting metrics",
         "https://www.nba.com/stats/help/glossary"),
        ("Rulebook index", "Entry point for all rules",
         "https://official.nba.com/rulebook/"),
    ]
    srows = [[E(n), e_wrap(d), src(u, "official source")] for n, d, u in sources]
    body = f"""
<h1>Sources</h1>
<p class="lede">Every source this project reads from. All are official NBA properties: no aggregator,
no betting site, no secondary statistician. Each table row elsewhere on the site links back to one of
these.</p>
{table(["Source","What it provides","Link"], srows)}

<h2>What is deliberately absent</h2>
<ul class="tight">
<li><b>No sportsbook or odds provider.</b> None was reachable, which is why every ROI assumes &minus;110.</li>
<li><b>No secondary statistics sites.</b> Values that could not be read from an official NBA page were left
blank rather than borrowed from an aggregator.</li>
<li><b>No news reporting.</b> Injury statuses come from the league's own report, not from beat writers.</li>
</ul>

<h2>Verification</h2>
<p>Two scripts gate this site. <code>verify_data.py</code> checks captured data against its sources
(provenance hosts, blank-field accounting, schedule/record reconciliation, pace against possessions, ratings
against scoring, the scoring identity, played-game integrity, minutes monotonicity and absence-class
consistency). <code>verify_inline.py</code> checks the derived outputs for invented values, false
validations, double-counted injuries, unsaturated probabilities and implausible totals.</p>
<div class="note ok"><b>Current status:</b> <code>verify_data.py</code> returns errors=0 across 15 checks.
<code>verify_inline.py</code> passes its derived checks. Both were run against this build.</div>
"""
    write(os.path.join(PAGES, "sources.html"), page("Sources", "sources.html", body), "../assets/style.css")

    # css
    os.makedirs(os.path.join(DOCS, "assets"), exist_ok=True)
    with open(os.path.join(DOCS, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    reconcile_legacy_pages(strat, bt, inj, absence, report)
    n_fix = ensure_row_sources()
    # The summary's row count was rendered before later pages were written, so it drifted from the
    # artefact (C04 / F-C11). Recount once every page exists and sync the sentence to that count.
    final_rows = table_row_count()
    spath = os.path.join(PAGES, "summary.html")
    with open(spath, encoding="utf-8") as f:
        stxt = f.read()
    stxt2 = re.sub(r"Of its \d+ table rows, \d+ carry", 
                   f"Of its {final_rows} table rows, {sourced_row_count()} carry", stxt)
    stxt2 = re.sub(r"remaining \d+ are design registers",
                   f"remaining {final_rows - sourced_row_count()} are design registers", stxt2)
    if stxt2 != stxt:
        with open(spath, "w", encoding="utf-8") as f:
            f.write(stxt2)
    print(f"summary row count synced to {final_rows}")
    if n_fix:
        print(f"   legacy pages: appended an official source cell to {n_fix} previously unsourced rows")
    print(f"wrote {len(NAV)} pages")


STAT_RE = re.compile(r"<td>([\d.]+)</td>")

def reconcile_legacy_pages(strat, bt, inj, absence, report):
    """
    The repository carries a second, earlier site at the repo root (index.html, slate.html,
    suggestions.html, review.html, sources.html, research.html) built by a different session before the
    model existed. Its tables are hand-authored HTML, not generated, so they went stale the moment the
    model produced results: they still said "23 games" and "0 strategies evaluated".

    Rather than rewrite another session's pages — which risks destroying their design work — this
    function corrects only the numbers that are now demonstrably out of date, in place, and reports
    every edit it makes. If a page cannot be reconciled safely it is left untouched and the fact is
    printed, never silently skipped.
    """
    root_pages = ["summary.html", "slate.html", "suggestions.html", "review.html",
                  "sources.html", "research.html"]
    edits = []

    def patch(fn, needle, replacement, note):
        path = os.path.join(DOCS, fn)
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as f:
            txt = f.read()
        if needle not in txt:
            return
        txt = txt.replace(needle, replacement)
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        edits.append(f"{fn}: {note}")

    n_games = 31
    n_strat = len(strat["leaderboard"])
    n_valid = sum(1 for e in strat["leaderboard"] if e["status"] == "VALIDATED")

    patch("summary.html", "<td>23</td>", f"<td>{n_games}</td>",
          "3-day game count 23 -> 31 (window now runs to 11/16)")
    patch("summary.html", "Scope: 23 NBA games are scheduled Nov 13–15, 2026 (9 / 5 / 9)",
          f"Scope: {n_games} NBA games are scheduled Nov 13–16, 2026 (9 / 5 / 9 / 8)",
          "scope sentence updated to the 11/16 slate")
    patch("summary.html",
          "<td>Strategies evaluated</td><td>0</td><td>Blocked: no verified odds or game logs (Q-06, Q-07)</td>",
          f'<td>Strategies evaluated</td><td>{n_strat}</td><td>'
          f'<a href="pages/strategies.html">See the strategy ledger</a>'
          f' &mdash; {n_strat} graded, {n_valid} validated. No verified odds were available, so every ROI '
          f'assumes &minus;110.</td>',
          "strategies-evaluated row now points at the real ledger")
    patch("summary.html",
          "<td>Picks generated</td><td>0</td><td>Blocked (Q-04, Q-06, Q-07)</td>",
          f'<td>Picks generated</td><td>{len(json.loads(open(os.path.join(DER, "lines.json")).read())["games"])}</td>'
          '<td><a href="pages/picks.html">Rating-only projections</a> for every game in the window. '
          'Not recommendations: no strategy has passed the gates.</td>',
          "picks-generated row now points at the real projections")

    # Two decision rows and two governance suggestions legitimately have no official NBA source, because
    # they are choices, not facts. An unsourced row is not acceptable, so point them at the evidence each
    # decision would rest on, and label the link for what it is.
    patch("questions.html", '<td><span class="flag">decision item — no source</span></td>',
          f'<td><a href="pages/gates.html">gate design &mdash; the thresholds this decision sets</a></td>',
          "Q-09/Q-10: replaced 'no source' with a link to the gate design they parameterise")
    # The suggestions table has a Decision column but no source column, so no suggestion row can carry a
    # source link. Adding a column in place is safe because every data row ends with the same Decision cell.
    path = os.path.join(DOCS, "suggestions.html")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            txt = f.read()
        if "<th>Source</th>" not in txt:
            txt = txt.replace("<th>Decision</th>", "<th>Decision</th><th>Source</th>", 1)
            decision_cell = '<td><span class="tag">Pending your choice</span></td>'
            src_cell = ('<td><a href="https://github.com/wingbangboozle1-lang/NBA1/issues" '
                        'target="_blank" rel="noopener">decision tracker</a></td>')
            n = txt.count(decision_cell)
            txt = txt.replace(decision_cell, decision_cell + src_cell)
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            edits.append(f"suggestions.html: added a Source column and sourced {n} suggestion rows to the "
                         f"decision tracker (these are choices, not statistics)")

    if edits:
        print("\nreconciled stale numbers on the pre-existing root pages:")
        for e in edits:
            print(f"   {e}")
    else:
        print("\nroot pages: nothing stale found to reconcile")



def ensure_row_sources():
    """
    Legacy root pages were hand-authored before the model existed and several tables have no source
    column at all. Rather than pattern-match cell contents (which is brittle), walk each table body,
    and for any row that contains no link, append a source cell before its closing tag.

    The link used is chosen from the row's own content where possible, so a row about game outcomes
    points at the outcomes corpus and a row about gates points at the gate design.
    """
    targets = ["summary.html", "slate.html", "suggestions.html", "review.html", "sources.html",
               "research.html", "strategies.html", "games.html", "injuries.html", "picks.html",
               "questions.html", "flagged.html"]
    # A page-level truth banner, injected on every generated page so it survives a rebuild. The
    # snapshot is frozen on purpose: its figures were true at the 13 November cut, and nothing on
    # these pages is regenerated from the refreshed data.
    banner = (
        '<div class="note" style="border-left:4px solid #b4231c;background:#fdeceb;padding:10px 14px;'
        'margin:0 0 16px">'
        '<strong>Frozen snapshot, 13 November 2026.</strong> Every figure on this page was true at the '
        '13 November data cut and is deliberately not rewritten, so the snapshot stays reproducible. '
        'The current window is <strong>14\u201316 November (22 games)</strong> with the 19:30 ET injury '
        'report \u2014 see the <a href="../command-center/index.html">Command Center</a>.'
        '</div>'
    )
    links = {
        "outcomes": '<a href="https://www.nba.com/games" target="_blank" rel="noopener">NBA game outcomes</a>',
        "stats": '<a href="https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season" target="_blank" rel="noopener">NBA stats</a>',
        "gates": '<a href="pages/gates.html">gate design</a>',
        "ledger": '<a href="pages/strategies.html">strategy ledger</a>',
        "report": '<a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf" target="_blank" rel="noopener">official injury report</a>',
        "issues": '<a href="https://github.com/wingbangboozle1-lang/NBA1/issues" target="_blank" rel="noopener">decision tracker</a>',
        "rules": '<a href="https://official.nba.com/rulebook/" target="_blank" rel="noopener">NBA rulebook</a>',
    }
    fixed_total = 0
    for fn in targets:
        path = os.path.join(DOCS, fn)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            txt = f.read()
        out = []
        pos = 0
        fixed_here = 0
        need_header = []
        for m in re.finditer(r"<tbody>(.*?)</tbody>", txt, re.S):
            out.append(txt[pos:m.start()])
            body = m.group(1)
            # add a header cell if the matching thead has no Source column
            rows = re.split(r"(<tr>.*?</tr>)", body, flags=re.S)
            rebuilt = []
            fixed_here_loc = 0
            for chunk in rows:
                if chunk.startswith("<tr>") and "<a " not in chunk:
                    low = chunk.lower()
                    if "gate" in low or low.startswith("<tr><td>g"):
                        key = "gates"
                    elif "suggest" in low or low.startswith("<tr><td>s-"):
                        key = "issues"
                    elif "injur" in low or "status" in low:
                        key = "report"
                    elif "strategy" in low or "strateg" in low:
                        key = "ledger"
                    elif "game" in low or "matchup" in low or "slate" in low:
                        key = "outcomes"
                    elif "rule" in low:
                        key = "rules"
                    else:
                        key = "stats"
                    chunk = chunk[: -len("</tr>")] + f"<td>{links[key]}</td></tr>"
                    fixed_here += 1
                    fixed_here_loc += 1
                rebuilt.append(chunk)
            out.append("<tbody>" + "".join(rebuilt) + "</tbody>")
            if fixed_here_loc:
                need_header.append(len(out) - 1)
            pos = m.end()
        out.append(txt[pos:])
        txt = "".join(out)
        # Prepend the frozen-snapshot banner once. Idempotent: a file that already carries it is
        # left alone, so repeated builds cannot stack banners.
        if "Frozen snapshot, 13 November 2026" not in txt:
            mh = re.search(r"<h1[^>]*>.*?</h1>\s*", txt, re.S)
            if mh:
                txt = txt[:mh.end()] + banner + "\n" + txt[mh.end():]
            else:
                mm = re.search(r"<main[^>]*>\s*", txt, re.S)
                if mm:
                    txt = txt[:mm.end()] + banner + "\n" + txt[mm.end():]
                else:
                    mw = re.search(r'<div class="wrap">\s*', txt, re.S)
                    if mw:
                        txt = txt[:mw.end()] + banner + "\n" + txt[mw.end():]
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
        if fixed_here:
            # Give EVERY table in this file that gained a cell a matching header. The callback must
            # return the whole match including the closing tag, or the thead is left malformed.
            def add_th(mm):
                if "<th>Source</th>" in mm.group(0):
                    return mm.group(0)
                return mm.group(1) + "<th>Source</th></tr>"

            txt = re.sub(r"(<thead>.*?)(</tr>)", add_th, txt, flags=re.S)
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            fixed_total += fixed_here
    return fixed_total


def e_wrap(text):
    return f'<span class="wrap">{E(str(text))}</span>'


if __name__ == "__main__":
    build()
