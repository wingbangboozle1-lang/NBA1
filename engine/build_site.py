"""Generate every HTML page of the site from the JSON in docs/data.

Run:  python3 engine/build_site.py          (after engine/pipeline.py)

The site is plain static HTML + vanilla JS. There is no build step at deploy
time and no framework: GitHub Pages serves docs/ as-is.
"""

import datetime
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import OUT, ROOT, read_json

DOCS = os.path.join(ROOT, "docs")
# A second session published a site at docs/ (its root dashboard links to
# docs/index.html, docs/injuries.html, docs/flagged.html and docs/sources.html).
# This build is namespaced under docs/b/ so both survive the merge intact.
SUB = "b"
PAGES = os.path.join(DOCS, SUB, "pages")

NAV = [
    ("index", "", "Overview"),
    ("lines", "pages/lines.html", "Lines"),
    ("picks", "pages/picks.html", "Picks"),
    ("props", "pages/props.html", "Player Props"),
    ("injuries", "pages/injuries.html", "Injuries"),
    ("gameflow", "pages/gameflow.html", "Game Flow"),
    ("validation", "pages/validation.html", "Validation"),
    ("strategy", "pages/strategy.html", "Strategies"),
    ("correlations", "pages/correlations.html", "Correlations"),
    ("luck", "pages/luck.html", "Luck"),
    ("backtest", "pages/backtest.html", "Game Log"),
    ("teams", "pages/teams.html", "Teams"),
    ("model", "pages/model.html", "Model"),
    ("flagged", "pages/flagged.html", "Flagged"),
    ("questions", "pages/questions.html", "Questions"),
    ("suggestions", "pages/suggestions.html", "Suggestions"),
    ("sources", "pages/sources.html", "Sources"),
]

STAMP = "2026-11-14"

# Sibling builds. Build B is one of three entry points in this repository and a reader who lands
# here has no way of knowing that, so the header carries an explicit switch between them.
# Sibling builds live at the REPOSITORY root, not inside docs/b/, so their hrefs have to be built
# from how far the page sits below the repo root: docs/b/index.html is two levels down and
# docs/b/pages/*.html is three. Paths are given relative to the repo root and get that prefix.
SIBLINGS = [
    ("command-center/index.html", "Command Center", "current data, 14\u201316 Nov"),
    ("index.html", "Edge Lab", "frozen 13 Nov snapshot"),
]
ROOT_PREFIX = {0: "../../", 1: "../../../"}


def nav_html(active, depth):
    prefix = "" if depth == 0 else "../"
    out = []
    for key, path, label in NAV:
        href = prefix + (path if path else "index.html")
        cls = ' class="active"' if key == active else ""
        out.append(f'<a href="{href}"{cls}>{label}</a>')
    out.append('<span class="navsep" aria-hidden="true"></span>')
    root_prefix = ROOT_PREFIX[depth]
    for href, label, note in SIBLINGS:
        out.append(f'<a class="sib" href="{root_prefix}{href}" title="{note}">{label} \u2197</a>')
    return "\n".join(out)


def page(active, title, body, subtitle="", depth=0, wide=True,
         page_prefix=None, asset_prefix=None):
    if page_prefix is None:
        page_prefix = "" if depth == 0 else "../"
    if asset_prefix is None:
        asset_prefix = page_prefix
    prefix = page_prefix
    ap = asset_prefix
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — NBA1 Line Origination</title>
<meta name="description" content="{subtitle or title}">
<link rel="stylesheet" href="{ap}assets/site.css">
<script src="{ap}assets/site.js"></script>
</head>
<body>
<header class="top">
  <div class="top-inner">
    <a class="brand" href="{prefix}index.html">NBA<span>1</span></a>
    <nav class="main">
{nav_html(active, depth)}
    </nav>
    <span class="stamp">as of {STAMP}</span>
  </div>
</header>
<main>
  <div class="wrap">
{body}
  </div>
</main>
<footer class="bot">
  <div class="wrap">
    <p><strong>NBA1</strong> — original NBA line origination, validation and analysis.
    Every table row on this site links to the official source it came from. Values that
    could not be confirmed are left blank and listed on the
    <a href="{prefix}pages/flagged.html">Flagged for Review</a> page — they are never inferred.</p>
    <p>Not affiliated with or endorsed by the National Basketball Association.
    Data © NBA; used here with attribution and links to the official pages.</p>
  </div>
</footer>
</body>
</html>
"""


def err_box(msg="Still loading…"):
    return f'<div class="empty" id="loadmsg">{msg}</div>'


# --------------------------------------------------------------------- pages

def p_index(meta, ex):
    verdict = ex["verdict"]
    findings = "\n".join(
        f"""<details class="q">
  <summary>{i['n']}. {i['title']}</summary>
  <div class="body">
    <p>{i['detail']}</p>
    <p class="small"><strong>Reading:</strong> {i.get('reading','')}</p>
  </div>
</details>""" for i in ex["findings"])

    live = "\n".join(f"<li>{x}</li>" for x in ex["what_is_live_now"])
    def _action_source(a):
        # every row carries an official link, or is flagged unverified (never a guessed link)
        if a.get("source_url"):
            return (f'<a class="srclink" href="{html.escape(a["source_url"])}" target="_blank" '
                    f'rel="noopener">{html.escape(a["source_label"])}</a>')
        return ('<span class="flag">unverified</span> <span class="small">'
                f'{html.escape(a.get("source_note", "no official source recorded"))}</span>')
    actions = "\n".join(
        f"""<tr><td class="num strong">{a['rank']}</td><td>{a['action']}</td>
            <td class="small">{a['why']}</td><td>{_action_source(a)}</td></tr>""" for a in ex["recommended_next_actions"])

    counts = meta["counts"]
    n_sources = len(read_json(os.path.join(OUT, "sources.json"))["sources"])
    # Window labels come from the data cut, never from a literal in this file.
    slate_label = meta["data_windows"]["upcoming_slates"]
    results_label = (meta["data_windows"]["out_of_sample_window"]
                     .replace(" .. ", " to ").split(" (")[0])
    edge_note = next((f for f in ex["findings"] if f["title"].startswith("The word")), None)
    kpis = f"""
    <div class="grid k4" style="margin-bottom:16px">
      <div class="card"><h4>Strategies</h4><div class="kpi">{counts['strategies']}</div>
        <div class="kpi-sub">singles, parlays, SGPs, prop combos</div></div>
      <div class="card"><h4>Upcoming games</h4><div class="kpi">{counts['upcoming_games']}</div>
        <div class="kpi-sub">{slate_label}</div></div>
      <div class="card"><h4>Out-of-sample games</h4><div class="kpi">{counts['out_of_sample_games']}</div>
        <div class="kpi-sub">{results_label}, ratings from 11-05 or earlier</div></div>
      <div class="card"><h4>Official sources</h4><div class="kpi">{n_sources}</div>
        <div class="kpi-sub">nba.com, official.nba.com, league injury PDFs</div></div>
    </div>"""

    return f"""
  <h1>Executive Summary</h1>
  <p class="lede">{ex['headline']}</p>

  <div class="banner {'danger' if verdict['status'].startswith('PROVISIONAL') else 'ok'}">
    <div class="ico">{'⚠' if verdict['status'].startswith('PROVISIONAL') else '✓'}</div>
    <div>
      <p><strong>Verdict: {verdict['status']}.</strong> {verdict['one_line']}</p>
      <p class="small">{verdict['why']}</p>
    </div>
  </div>

  <div class="banner warn">
    <div class="ico">!</div>
    <div><p><strong>Read this before any number called an "edge".</strong>
    {edge_note['detail'] if edge_note else ''}</p></div>
  </div>

  {kpis}

  <h2>What the data says</h2>
  <p class="small">{ex['lead']}</p>
  {findings}

  <h2>Live right now</h2>
  <ul class="tight">{live}</ul>

  <h2>Recommended next actions</h2>
  <div class="tablewrap"><table class="thin">
    <thead><tr><th class="num">#</th><th>Action</th><th>Why</th><th>Official source</th></tr></thead>
    <tbody>{actions}</tbody>
  </table></div>

  <h2>How to read this site</h2>
  <div class="grid k3">
    <div class="card"><h4>Every row has a source</h4>
      <p class="small">Each table row carries a source id that links to the official page or PDF it
      came from. Click any <span class="srclink">S1</span>-style link to check it yourself.</p></div>
    <div class="card"><h4>Three kinds of number</h4>
      <p class="small"><span class="prov official">official</span> published by the NBA ·
      <span class="prov derived">derived</span> arithmetic or model on official inputs ·
      <span class="prov assumption">assumption</span> a modelling choice, listed in full.</p></div>
    <div class="card"><h4>Blanks are deliberate</h4>
      <p class="small"><span class="blank">n/a</span> means no official source value existed.
      Nothing was filled in. Those gaps are catalogued on the Flagged page.</p></div>
  </div>

  <h2>Bottom line</h2>
  <p>{ex['bottom_line']}</p>

  <div class="toc" style="margin-top:18px">
    <a href="pages/lines.html">Originated lines →</a>
    <a href="pages/validation.html">Validation &amp; leaderboard →</a>
    <a href="pages/questions.html">Open questions →</a>
    <a href="pages/suggestions.html">Suggestions →</a>
    <a href="pages/flagged.html">Flagged for review →</a>
  </div>
"""


def p_lines():
    return f"""
  <h1>Originated Lines</h1>
  <p class="lede">Spreads, totals and moneylines produced by the model for every game on the next
  three slates, shown next to the naive reference line they are being tested against.</p>

  <div class="banner info">
    <div class="ico">i</div>
    <div><p><strong>"Reference" is a deliberately naive model, not a sportsbook.</strong>
    No book price is published by an NBA-operated source, so none can be linked. The reference is
    raw net rating + a flat +2.0 home edge for the side, and the two teams' published scoring
    averages added together for the total. <em>Model gap</em> is the difference between the two
    models — it is not edge against a market. See
    <a href="flagged.html">F3</a>.</p></div>
  </div>

  <div class="toolbar">
    <label>Slate
      <select id="f-date"><option value="">All dates</option></select>
    </label>
    <label>Team
      <select id="f-team"><option value="">All teams</option></select>
    </label>
    <label>Min |model gap|
      <select id="f-edge">
        <option value="0">Any</option><option value="2">2.0+</option>
        <option value="3">3.0+</option><option value="5">5.0+</option>
      </select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="tbl">{err_box()}</div>

  <h3>Column notes</h3>
  <dl class="kv">
    <dt>Ref spread</dt><dd>Naive reference home spread. Negative = home favoured.</dd>
    <dt>Model spread</dt><dd>Originated home spread: efficiency + shrinkage + home court + rest + availability.</dd>
    <dt>Gap</dt><dd>Model minus reference. Positive = the model likes the home side more than the reference does.</dd>
    <dt>P(home cover)</dt><dd>Probability the home side covers the reference spread, from the fitted margin spread.</dd>
    <dt>P(over)</dt><dd>Probability the game goes over the reference total.</dd>
    <dt>Fair ML</dt><dd>Vig-free American price implied by the model win probability.</dd>
    <dt>Avail. loss</dt><dd>Net-rating points per 100 possessions removed for official injury-report
      unavailability. A floor — see <a href="flagged.html">F2</a>.</dd>
  </dl>
"""


def p_picks():
    return f"""
  <h1>Picks</h1>
  <p class="lede">Every play the strategy library generates for the upcoming slates: singles,
  parlays, same-game parlays and player-prop combos. Each row names the strategy that produced it
  and the reference number it is being measured against.</p>

  <div class="banner warn">
    <div class="ico">!</div>
    <div><p><strong>No strategy is funded.</strong> Every strategy is capped at quarter-unit or
    research-only because none has cleared the 30-play sample gate — see the
    <a href="validation.html">Validation</a> page and <a href="flagged.html">F8</a>.
    These plays are what the system produces; they are not recommendations to stake.</p></div>
  </div>

  <div class="toolbar">
    <div class="chipbar" id="f-date"></div>
    <div class="spacer"></div>
    <label>Market
      <select id="f-market"><option value="">All markets</option></select>
    </label>
    <label>Strategy
      <select id="f-strat"><option value="">All strategies</option></select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="tbl">{err_box()}</div>

  <h3>How parlays are priced</h3>
  <p class="small">Two-leg parlays show both the probability under the modelled correlation and the
  probability you would get by naively multiplying the legs. Where they differ, the difference is
  the amount you would overpay by pricing correlated legs as independent. The correlation values
  themselves are model-derived, not measured — see <a href="correlations.html">Correlations</a>
  and <a href="flagged.html">F6</a>.</p>
"""


def p_props():
    return f"""
  <h1>Player Props</h1>
  <p class="lede">Per-game projections for every player in the captured official minutes table,
  shown against their own season average, with each adjustment broken out separately.</p>

  <div class="banner danger">
    <div class="ico">!</div>
    <div><p><strong>No probability is published here, on purpose.</strong> The model can produce a
    projection, but game-to-game variance has never been measured — that needs player game logs,
    which were not captured. Publishing a probability without a measured variance would be
    inventing a number, so the column is left blank. See
    <a href="flagged.html">F2</a> and <a href="questions.html">Q3</a>.</p></div>
  </div>

  <div class="toolbar">
    <div class="chipbar" id="f-date"></div>
    <div class="spacer"></div>
    <label>Team
      <select id="f-team"><option value="">All teams</option></select>
    </label>
    <label>Stat
      <select id="f-stat">
        <option value="pts">Points</option><option value="reb">Rebounds</option>
        <option value="ast">Assists</option><option value="fg3m">3-pointers made</option>
        <option value="pts_reb_ast">PRA</option>
      </select>
    </label>
    <label>Min |change|
      <select id="f-delta">
        <option value="0">Any</option><option value="1">1.0+</option>
        <option value="2">2.0+</option><option value="3">3.0+</option>
      </select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="tbl">{err_box()}</div>

  <h3>What each factor does</h3>
  <dl class="kv">
    <dt>Possessions</dt><dd>Expected game possessions ÷ the team's season pace.</dd>
    <dt>Opponent defence</dt><dd>1 + (opponent DefRtg − league average) ÷ league average. Applies to points, assists and threes.</dd>
    <dt>Rebound rate</dt><dd>1 − 0.5 × (opponent DREB% − league average) ÷ league average.</dd>
    <dt>Usage</dt><dd>1 + 0.35 × (teammate minutes unavailable). Only counted when the minutes are known, so it is a floor.</dd>
    <dt>Season avg</dt><dd>The player's own official per-game average. This is the number being projected away from.</dd>
  </dl>
  <p class="small faint">The three multipliers are modelling choices, not official measurements —
  see <a href="flagged.html">F4</a>.</p>
"""


def p_injuries():
    return f"""
  <h1>Injuries &amp; Rotation</h1>
  <p class="lede">The official NBA injury report transcribed row by row, plus the rotation impact
  derived from it. Every status and reason is exactly as the team published it.</p>

  <div class="banner danger">
    <div class="ico">!</div>
    <div><p><strong>The impact column is a measured floor, not an estimate.</strong>
    A player's minutes are only known if he appears in the captured official top-50 minutes table.
    Anyone else contributes 0.00 to the impact, so a team missing a rotation player who is not a
    top-50 scorer will show a smaller number than the truth — sometimes zero. The
    <em>Minutes known</em> and <em>Coverage</em> columns sit next to every figure so a 0.00 is
    never read as "healthy". See <a href="flagged.html">F2</a>.</p></div>
  </div>

  <h2>Team impact, by game</h2>
  <div class="toolbar">
    <div class="chipbar" id="f-date"></div>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>
  <div id="tbl-team">{err_box()}</div>

  <h2>Every listed player</h2>
  <div class="toolbar">
    <div class="chipbar" id="f-date2"></div>
    <div class="spacer"></div>
    <label>Team
      <select id="f-team"><option value="">All teams</option></select>
    </label>
    <label>Status
      <select id="f-status"><option value="">All statuses</option></select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt2"></span>
  </div>
  <div id="tbl-player">{err_box()}</div>

  <h3>Method</h3>
  <div class="eq">weighted minutes at risk = Σ (status weight × player minutes ÷ 240)
impact (net rating points per 100) = 15.0 × weighted minutes at risk</div>
  <p class="small">Status weights: Out 1.00 · Doubtful 0.70 · Questionable 0.35 · Probable 0.10 ·
  Available 0.00. The 15.0 coefficient is a declared modelling choice, not an official figure, and
  a sensitivity band of 10 / 15 / 20 is published for every team on the
  <a href="flagged.html">Flagged</a> page. See <a href="flagged.html">F4</a>.</p>
"""


def p_gameflow():
    return f"""
  <h1>Game Flow</h1>
  <p class="lede">What the official pace and efficiency data says about how each game should be
  played, and the probabilities that follow from the fitted outcome spread.</p>

  <div class="banner info">
    <div class="ico">i</div>
    <div><p><strong>Scope limit.</strong> Possession-level flow — runs, timeout patterns, quarter
    splits — needs play-by-play data, which was not captured. Nothing of that kind is published
    here. Everything below follows from official pace and efficiency inputs plus the fitted spread
    of game margins. See <a href="questions.html">Q5</a>.</p></div>
  </div>

  <div class="toolbar">
    <div class="chipbar" id="f-date"></div>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="tbl">{err_box()}</div>

  <h3>Reading the probabilities</h3>
  <dl class="kv">
    <dt>Within 5</dt><dd>Probability the final home margin lands between −5 and +5 — a one-possession game.</dd>
    <dt>20+</dt><dd>Probability either side wins by 20 or more. Relevant to the NBA Cup, where point differential is a tiebreaker.</dd>
    <dt>P(OT)</dt><dd>Approximate probability the game is tied after regulation, from the density of the margin distribution at zero.</dd>
    <dt>Pace vs league</dt><dd>Expected possessions per 48 minutes minus the league average of 99.85.</dd>
  </dl>
"""


def p_validation():
    return f"""
  <h1>Validation &amp; Leaderboard</h1>
  <p class="lede">Out-of-sample results, the gate set every strategy has to clear, and the
  leaderboard that scores them.</p>

  <div class="banner info">
    <div class="ico">i</div>
    <div><p><strong>Information discipline.</strong> The test window is 2026-11-06 to 2026-11-13
    (60 games — every completed game captured, and all of them after the ratings cut-off).
    Ratings come only from 2026-10-20 to 2026-11-05, so no test game contributes to
    the ratings that predict it. Two parameters — home court and the back-to-back penalty — are
    fitted <em>on the test window</em>; that is disclosed on every row they touch, and a
    zeroed-parameter variant is published below so you can see how much they matter.</p></div>
  </div>

  <h2>Headline metrics</h2>
  <div id="kpis">{err_box()}</div>

  <h2>Leaderboard</h2>
  <div class="tablewrap"><table id="lb" class="thin"></table></div>
  <p class="small" id="lbnote"></p>

  <h2>Gate results by strategy</h2>
  <div class="toolbar">
    <label>Strategy
      <select id="f-strat"><option value="">All strategies</option></select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>
  <div id="tbl-gates">{err_box()}</div>

  <h2>Gate definitions</h2>
  <div id="gatedefs"></div>

  <h2>Gate detail by strategy</h2>
  <div id="gatedef"></div>

  <h2>Fitted parameters</h2>
  <div id="fit"></div>

  <h2>Shrinkage sensitivity</h2>
  <p class="small">The shrinkage constant is derived rather than guessed; the single-game noise term
  it depends on is estimated on the test window, so it is partly test-informed. This sweep refits
  home court and the back-to-back term at each fixed value of k.</p>
  <div id="sweep"></div>

  <h2>Luck decomposition of the model's own record</h2>
  <div id="luckbox"></div>
"""


def p_strategy():
    return f"""
  <h1>Strategy Library</h1>
  <p class="lede">Ten strategies covering single bets, parlays, same-game parlays and player-prop
  combos. Each states the exact rule that makes it play, the threshold, and why it might work.</p>

  <div class="banner warn">
    <div class="ico">!</div>
    <div><p><strong>Graded vs ungraded.</strong> A strategy is only graded if its inputs were
    actually captured. S6 needs archived injury reports, and S7/S8 need player game logs; none were
    captured, so they are shown as <em>ungraded</em> rather than being scored with substituted
    numbers. See <a href="flagged.html">F5</a> and <a href="questions.html">Q3</a>.</p></div>
  </div>

  <div class="toolbar">
    <label>Family
      <select id="f-family"><option value="">All families</option></select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="cards"></div>
"""


def p_correlations():
    return f"""
  <h1>Correlations</h1>
  <p class="lede">Two deliberately separate tables: what was measured from official data, and what
  had to be derived from the model.</p>

  <h2>Measured on official data</h2>
  <p class="small">Pearson correlations computed across all 30 teams from the official advanced
  table. Every pair reports r, r² and a two-sided p-value. These are reproducible from the source
  link on each row.</p>
  <div id="tbl-measured">{err_box()}</div>

  <h2>Model-derived, for parlay pricing</h2>
  <div class="banner danger">
    <div class="ico">!</div>
    <div><p><strong>These are not measurements.</strong> Correlations between bet legs need
    play-by-play, which was not captured. The values below follow from the structure of the model,
    not from data. They are labelled MODEL-DERIVED everywhere they appear and must not be quoted as
    official. The side/total value of 0.00 is a mathematical property of the additive model under
    equal team-score variances; the player-market values are estimates. See
    <a href="flagged.html">F6</a>.</p></div>
  </div>
  <div id="tbl-derived">{err_box()}</div>

  <h2>What correlation does to a two-leg price</h2>
  <p class="small">Holding both leg probabilities fixed, the table shows how the true joint
  probability moves with rho, and how much you overpay by pricing the legs as independent.
  Positive rho helps the bettor and hurts the book; negative rho does the opposite.</p>
  <div class="toolbar">
    <label>Leg probability
      <select id="f-p"><option value="">All</option></select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>
  <div id="tbl-grid">{err_box()}</div>
"""


def p_luck():
    return f"""
  <h1>Luck</h1>
  <p class="lede">How much of each team's record is real. Pythagorean expectation applied to the
  official offensive and defensive ratings, compared against actual wins.</p>

  <div class="eq">pythag = OffRtg^13.91 ÷ (OffRtg^13.91 + DefRtg^13.91)
expected wins = games played × pythag
luck (wins)  = actual wins − expected wins
z            = luck ÷ √(games × pythag × (1 − pythag))</div>

  <p class="small">The z-score divides the gap by the binomial standard deviation over the games a
  team has actually played, so it is comparable across teams with different schedules. With 10–13
  games played, roughly two thirds of the league should sit inside ±1 — and it does, which is the
  point: this early, most of the spread in the standings is noise.</p>

  <div class="toolbar">
    <label>Direction
      <select id="f-dir">
        <option value="all">All teams</option>
        <option value="over">Overperformers (lucky)</option>
        <option value="under">Underperformers (unlucky)</option>
      </select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="tbl">{err_box()}</div>

  <h3>What this is used for</h3>
  <p class="small">A team whose record outruns its efficiency ratings tends to regress. That is a
  reason to be careful backing them and a reason not to write them off when they are behind their
  ratings. It is deliberately <em>not</em> wired into the model as an automatic correction: with
  10–13 games per team that would be fitting noise. See
  <a href="questions.html">A4</a>.</p>
"""


def p_backtest():
    return f"""
  <h1>Out-of-Sample Game Log</h1>
  <p class="lede">All 60 games in the test window, with the actual official final score next to both
  the reference forecast and the model forecast.</p>

  <div class="banner info">
    <div class="ico">i</div>
    <div><p><strong>Ratings window.</strong> Every forecast on this page was produced from team
    ratings computed on 2026-10-20 to 2026-11-05 only. No game on this page contributed to those
    ratings. The final scores are official. One game — Denver 114, Indiana 102 on 2026-11-07 —
    was the NBA Mexico City Game, labelled "Neutral Site" by the official page; home-court
    advantage is set to zero for it in both the forecast and the HCA regression
    (<a href="flagged.html">F12</a>).</p></div>
  </div>

  <div class="toolbar">
    <div class="chipbar" id="f-date"></div>
    <div class="spacer"></div>
    <label>Show
      <select id="f-show">
        <option value="all">All games</option>
        <option value="model_better">Model beat the reference (margin)</option>
        <option value="ref_better">Reference beat the model (margin)</option>
        <option value="big">Absolute margin error 20+</option>
      </select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="tbl">{err_box()}</div>

  <h2>Error distribution</h2>
  <div id="dist"></div>
"""


def p_teams():
    return f"""
  <h1>Team Ratings</h1>
  <p class="lede">The official advanced team table, published verbatim, plus two arithmetic
  columns. This is the input to every line on this site.</p>

  <div class="toolbar">
    <label>Sort by
      <select id="f-sort">
        <option value="netr">Net rating</option>
        <option value="ortg">Offensive rating</option>
        <option value="drtg">Defensive rating (best first)</option>
        <option value="pace">Pace</option>
        <option value="win_pct">Win percentage</option>
        <option value="efg_pct">Effective FG%</option>
        <option value="tov_pct">Turnover % (best first)</option>
        <option value="pie">PIE</option>
      </select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="tbl">{err_box()}</div>

  <h3>Notes</h3>
  <p class="small">Points and opponent points per game are arithmetic
  (OffRtg × Pace ÷ 100) on the two official columns — they are labelled
  <span class="prov derived">derived</span>. Every other column is published verbatim by NBA.com and
  labelled <span class="prov official">official</span>. Ratings are per 100 possessions; pace is
  possessions per 48 minutes.</p>
"""


def p_model():
    return f"""
  <h1>Model</h1>
  <p class="lede">Exactly how a line is produced, including the parts that are chosen rather than
  measured.</p>

  <h2>The core</h2>
  <div class="eq">points per 100 (home) = OffRtg(home) + DefRtg(away) − L
points per 100 (away) = OffRtg(away) + DefRtg(home) − L
possessions           = (Pace(home) + Pace(away)) ÷ 2
margin (home)         = (pts100_home − pts100_away) × poss ÷ 100
total                 = (pts100_home + pts100_away) × poss ÷ 100</div>

  <p class="small">L is the league average of the two ratings (112.94 this season). This is the
  standard additive form.</p>

  <div class="banner warn">
    <div class="ico">!</div>
    <div><p><strong>An honest property of this form.</strong> Substituting the definitions shows the
    per-100-possession margin collapses to NetRtg(home) − NetRtg(away): the opponent-interaction
    term cancels. So the side's forecast carries no opponent-adjustment signal at all beyond the
    ratings themselves. Home court, rest, availability and shrinkage are the entire game for the
    side — which is exactly why they are modelled explicitly and reported separately.</p></div>
  </div>

  <h2>Shrinkage</h2>
  <p class="small">Each team's rating is pulled toward the league average before use:</p>
  <div class="eq">f = G ÷ (G + k)        rating_used = L + f × (rating_observed − L)</div>
  <p class="small">k is derived, not guessed: the spread of forecast residuals on the test window
  implies a single-game team noise of s, and combining that with the observed spread of net ratings
  gives k = s² ÷ Var(true). The calculation and a fixed-k sensitivity sweep are on the
  <a href="validation.html">Validation</a> page.</p>

  <h2>Adjustments</h2>
  <div class="eq">margin += HCA − b2b_penalty × (home_b2b − away_b2b) + (loss_away − loss_home) × poss ÷ 100
total  += total_bias + total_b2b_coef × (home_b2b + away_b2b) − (1 − 2α) × (loss_home + loss_away) × poss ÷ 100</div>
  <p class="small">α = 0.60 is the share of an availability loss landing on the team's own offence;
  the rest lands on its defence, so the total moves by −(1 − 2α) × the combined loss. An
  availability loss is symmetric in the margin by construction — it moves the side only through the
  difference between the two teams' losses.</p>

  <h2>Every modelling choice, in the open</h2>
  <div id="assump">{err_box()}</div>

  <h2>What the model does not do</h2>
  <ul class="tight">
    <li>No market prices — there is no official source for them, so none is used
      (<a href="flagged.html">F3</a>).</li>
    <li>No possession-level simulation — no play-by-play was captured.</li>
    <li>No player-tracking or line-up data — not published in the captured tables.</li>
    <li>No automatic luck correction in the ratings — with 10–13 games per team that would fit noise.
      The luck numbers are published separately instead.</li>
    <li>No inferred values anywhere. Where the official source has nothing, the cell is blank.</li>
  </ul>
"""


def p_flagged():
    return f"""
  <h1>Flagged for Review</h1>
  <p class="lede">Everything the verification pass could not confirm from an official source, or
  every value left blank rather than filled in. None of these blocks the site — they are published
  so they can be reviewed and assigned.</p>

  <div class="banner info">
    <div class="ico">i</div>
    <div><p>Each item carries the official link it relates to and a suggested action. Items marked
    <span class="badge high">High</span> materially limit what the site can claim today.</p></div>
  </div>

  <div class="toolbar">
    <label>Severity
      <select id="f-sev"><option value="">All</option></select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="items"></div>
"""


def p_questions():
    return f"""
  <h1>Open Questions</h1>
  <p class="lede">Split in two: what the data on hand can actually answer, and what it cannot.
  Nothing on this site is decided on an open question.</p>

  <div class="banner info">
    <div class="ico">i</div>
    <div><p>Every answered question carries the number, the source link and a confidence note.
    Every open question carries what is missing, the concrete step that would answer it, and what
    it currently blocks.</p></div>
  </div>

  <h2>Answered</h2>
  <div id="answered"></div>

  <h2>Open — ranked by what they block</h2>
  <div id="open"></div>
"""


def p_suggestions():
    return f"""
  <h1>Suggestions</h1>
  <p class="lede">Improvements to the site and to the decision process, written so a reviewer can
  pick a path rather than inherit one. Each item states the problem, the options with their effort,
  risk and what they unlock, and a recommendation.</p>

  <div class="banner info">
    <div class="ico">i</div>
    <div><p><strong>Nothing here has been implemented.</strong> Each card ends with the specific
    decision a reviewer needs to make. Items are grouped by category.</p></div>
  </div>

  <div class="toolbar">
    <label>Category
      <select id="f-cat"><option value="">All</option></select>
    </label>
    <div class="spacer"></div>
    <span class="count" id="cnt"></span>
  </div>

  <div id="items"></div>
"""


def p_sources():
    return f"""
  <h1>Sources</h1>
  <p class="lede">Every official source this site uses, and exactly what each one was used for.
  Each table row on the site links back to one of these.</p>

  <div class="banner info">
    <div class="ico">i</div>
    <div><p><strong>Verification rule.</strong> Every value published here is traceable to one of
    the sources below. Where a source could not supply a value, the cell is left blank and the gap
    is recorded on the <a href="flagged.html">Flagged for Review</a> page. Nothing is inferred and
    nothing is filled in.</p></div>
  </div>

  <div id="tbl">{err_box()}</div>

  <h2>Data files</h2>
  <p class="small">The raw snapshots behind every number are committed to the repository under
  <code>data/raw/</code>, each with the exact URL and capture time inside it:</p>
  <ul class="plain small">
    <li><code>team_advanced.json</code> — official team advanced stats, season to date and the 2026-10-20…2026-11-05 window</li>
    <li><code>games_completed.json</code> — official final scores</li>
    <li><code>schedule_upcoming.json</code> — official schedule, venues, tip times</li>
    <li><code>injuries.json</code> — the official league injury report, transcribed row by row</li>
    <li><code>players_traditional.json</code> — official player per-game averages</li>
    <li><code>sources.json</code> — this page, in machine-readable form</li>
  </ul>

  <h2>Refresh</h2>
  <p class="small">A scheduled job re-fetches the schedule, results and the newest injury report and
  commits only when something actually changed. If the job fails, the previously committed snapshot
  stays live — a failure cannot break the site. See <a href="flagged.html">F7</a>.</p>
"""


# --------------------------------------------------------------- page scripts

SCRIPTS = {

"lines": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("lines.json"));
  const rows = d.rows;
  const dates = uniq(rows.map(r => r.date)).sort();
  const teams = uniq(rows.flatMap(r => [r.home, r.away])).sort();
  fillSelect("#f-date", dates);
  fillSelect("#f-team", teams);

  const st = {date:"", team:"", edge:0};
  const draw = () => {
    let rs = rows.filter(r =>
      (!st.date || r.date === st.date) &&
      (!st.team || r.home === st.team || r.away === st.team) &&
      (Math.abs(r.spread_edge) >= st.edge || Math.abs(r.total_edge) >= st.edge));
    rs = sortBy(rs, "date");
    setText("#cnt", rs.length + " of " + rows.length + " games");
    const cols = [
      {key:"date", label:"Date", cls:"date"},
      {key:"time_et", label:"Tip (ET)"},
      {key:"matchup", label:"Matchup", cls:"lbl"},
      {key:"away_rec", label:"Away rec"},
      {key:"home_rec", label:"Home rec"},
      {key:"ref_spread_home", label:"Ref spread", num:true, signed:true, d:1, prov:"derived"},
      {key:"model_spread_home", label:"Model spread", num:true, signed:true, d:1, prov:"derived"},
      {key:"spread_edge", label:"Gap", num:true, signed:true, d:2, prov:"derived"},
      {key:"ref_total", label:"Ref total", num:true, d:1, prov:"derived"},
      {key:"model_total", label:"Model total", num:true, d:1, prov:"derived"},
      {key:"total_edge", label:"Gap", num:true, signed:true, d:2, prov:"derived"},
      {key:"model_possessions", label:"Poss", num:true, d:1, cls:"muted", prov:"derived"},
      {key:"p_home_cover_ref", label:"P(home cover)", fmt: v => pct(v), prov:"derived"},
      {key:"p_over_ref_total", label:"P(over)", fmt: v => pct(v), prov:"derived"},
      {key:"ml_home_fair", label:"Fair ML home", fmt: v => price(v), prov:"derived"},
      {key:"ml_away_fair", label:"Fair ML away", fmt: v => price(v), prov:"derived"},
      {key:"home_availability_loss", label:"Home avail.", num:true, d:2, cls:"muted", prov:"assumption"},
      {key:"away_availability_loss", label:"Away avail.", num:true, d:2, cls:"muted", prov:"assumption"},
      {key:"cup_group", label:"Cup"},
      {key:"venue", label:"Venue"},
      {key:"src", label:"Src", src:true},
    ];
    setHTML("#tbl", table(cols, rs, {thin:true}));
  };
  bind("#f-date", v => {st.date=v; draw();});
  bind("#f-team", v => {st.team=v; draw();});
  bind("#f-edge", v => {st.edge=parseFloat(v)||0; draw();});
  draw();
})().catch(e => setHTML("#tbl", '<div class="empty">Failed to load: '+e.message+'</div>'));
""",

"picks": """
(async () => {
  await initSources();
  const [d, lb, vd] = await Promise.all([
    loadJSON(DATA("picks.json")),
    loadJSON(DATA("leaderboard.json")),
    loadJSON(DATA("validation.json"))
  ]);
  const rows = d.rows;
  const tier = {};
  for (const r of lb.rows) tier[r.id] = r;
  // link each single-game play to its own official game page; parlays link to the first leg
  for (const r of rows) r.src = "S8_" + String(r.game_id).split("+")[0];
  const dates = uniq(rows.map(r => r.date)).sort();
  const markets = uniq(rows.map(r => r.market)).sort();
  fillChipbar("#f-date", dates, v => {st.date=v; draw();}, "All dates");
  fillSelect("#f-market", markets);
  fillSelect("#f-strat", uniq(rows.map(r => r.strategy)).sort());

  const st = {date:"", market:"", strat:""};
  const draw = () => {
    let rs = rows.filter(r =>
      (!st.date || r.date === st.date) &&
      (!st.market || r.market === st.market) &&
      (!st.strat || r.strategy === st.strat));
    rs = sortBy(rs, "date");
    setText("#cnt", rs.length + " of " + rows.length + " plays");
    const cols = [
      {key:"date", label:"Date", cls:"date"},
      {key:"time_et", label:"Tip (ET)"},
      {key:"strategy", label:"Strat", fmt: v => {
        const t = tier[v];
        const cls = t ? (t.tier.startsWith("Tier 1") ? "t1" : t.tier.startsWith("Tier 2") ? "t2" :
                         t.tier.startsWith("Tier 3") ? "t3" : "t0") : "na";
        return `<span class="badge ${cls}" title="${esc(t?t.tier:"")}">${esc(v)}</span>`;
      }},
      {key:"market", label:"Market"},
      {key:"matchup", label:"Game", cls:"lbl"},
      {key:"line_display", label:"Play", cls:"lbl"},
      {key:"ref_line", label:"Ref line", num:true, d:1, cls:"muted"},
      {key:"model_value", label:"Model", num:true, d:1, cls:"muted"},
      {key:"edge", label:"Gap", num:true, signed:true, d:2},
      {key:"p_model", label:"P(model)", fmt: v => pct(v)},
      {key:"p_if_independent", label:"P(if indep.)", fmt: v => pct(v)},
      {key:"fair_price", label:"Fair price", fmt: v => price(v)},
      {key:"rho", label:"rho", num:true, d:2, cls:"muted"},
      {key:"status", label:"Status", fmt: v => badge(v, "na")},
      {key:"src", label:"Src", src:true},
    ];
    setHTML("#tbl", table(cols, rs, {thin:true}));
  };
  bind("#f-market", v => {st.market=v; draw();});
  bind("#f-strat", v => {st.strat=v; draw();});
  draw();
})().catch(e => setHTML("#tbl", '<div class="empty">Failed to load: '+e.message+'</div>'));
""",

"props": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("props.json"));
  const rows = d.rows;
  const dates = uniq(rows.map(r => r.date)).sort();
  fillChipbar("#f-date", dates, v => {st.date=v; draw();}, "All dates");
  fillSelect("#f-team", uniq(rows.map(r => r.team)).sort());
  const st = {date:"", team:"", stat:"pts", delta:0};
  const S = {pts:["pts","Points"], reb:["reb","Rebounds"], ast:["ast","Assists"],
             fg3m:["fg3m","3PM"], pts_reb_ast:["pts_reb_ast","PRA"]};
  const draw = () => {
    const [k, label] = S[st.stat];
    let rs = rows.filter(r =>
      (!st.date || r.date === st.date) &&
      (!st.team || r.team === st.team) &&
      Math.abs(Number(r["delta_"+k] ?? 0)) >= st.delta);
    rs = sortBy(rs, "delta_"+k, -1);
    setText("#cnt", rs.length + " of " + rows.length + " player games");
    const cols = [
      {key:"date", label:"Date", cls:"date"},
      {key:"matchup", label:"Game", cls:"lbl"},
      {key:"player", label:"Player", cls:"lbl"},
      {key:"team", label:"TM"},
      {key:"opponent", label:"vs"},
      {key:"gp", label:"GP", num:true, d:0, cls:"muted"},
      {key:"season_min", label:"MPG", num:true, d:1, cls:"muted"},
      {key:"season_avg", label:"Season avg", num:true, d:1, cls:"muted",
        fmt:(v,r)=>num(r["baseline_"+st.stat],1,"muted")},
      {key:"proj", label:"Projection", num:true, d:1, cls:"strong", prov:"derived",
        fmt:(v,r)=>num(r["proj_"+st.stat],1,"strong")},
      {key:"delta", label:"Change", num:true, signed:true, d:2, prov:"derived",
        fmt:(v,r)=>signed(r["delta_"+st.stat],2)},
      {key:"poss_factor", label:"Poss", num:true, d:3, cls:"muted", prov:"derived"},
      {key:"def_factor", label:"Opp def", num:true, d:3, cls:"muted", prov:"derived"},
      {key:"reb_factor", label:"Reb", num:true, d:3, cls:"muted", prov:"derived"},
      {key:"usage_factor", label:"Usage", num:true, d:3, cls:"muted", prov:"derived"},
      {key:"probability", label:"P(over)", fmt: v =>
        v === null ? '<span class="blank" title="No measured variance - see F2/Q3">n/a</span>' : pct(v)},
      {key:"src_baseline", label:"Src", src:true},
    ];
    setHTML("#tbl", table(cols, rs, {thin:true}));
  };
  bind("#f-team", v => {st.team=v; draw();});
  bind("#f-stat", v => {st.stat=v; draw();});
  bind("#f-delta", v => {st.delta=parseFloat(v)||0; draw();});
  draw();
})().catch(e => setHTML("#tbl", '<div class="empty">Failed to load: '+e.message+'</div>'));
""",

"injuries": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("injuries.json"));
  const rows = d.rows;
  const dates = uniq(rows.map(r => r.date)).sort();
  fillChipbar("#f-date", dates, v => {st.date=v; drawTeam();}, "All dates");
  fillChipbar("#f-date2", dates, v => {st2.date=v; drawPlayer();}, "All dates");
  fillSelect("#f-team", uniq(rows.map(r => r.team)).filter(Boolean).sort());
  fillSelect("#f-status", uniq(rows.map(r => r.status)).filter(Boolean).sort());

  const st = {date:""}, st2 = {date:"", team:"", status:""};

  function drawTeam() {
    const seen = new Set(); const out = [];
    for (const r of rows) {
      if (st.date && r.date !== st.date) continue;
      const k = r.matchup + "|" + r.team;
      if (seen.has(k)) continue;
      seen.add(k);
      out.push(r);
    }
    setText("#cnt", out.length + " team reports");
    const cols = [
      {key:"date", label:"Date", cls:"date"},
      {key:"matchup", label:"Game", cls:"lbl"},
      {key:"team", label:"Team", cls:"lbl"},
      {key:"team_listed", label:"Listed", num:true, d:0, cls:"muted"},
      {key:"team_weighted_lost_share", label:"Min at risk", prov:"assumption",
        fmt: v => v === null || v === undefined
          ? '<span class="blank" title="No entry in this edition">n/a</span>'
          : `<span class="num ${v>=0.15?"neg":v>0?"muted":"muted"}">${(v*100).toFixed(1)}%</span>`},
      {key:"team_impact_net_rating", label:"Impact (net rtg)", prov:"assumption",
        fmt: v => v === null || v === undefined
          ? '<span class="blank" title="No entry in this edition">n/a</span>'
          : `<span class="num ${v>0?"neg":"muted"}">${(-v).toFixed(2)}</span>`},
      {key:"impact_sensitivity", label:"Sensitivity 10/15/20", fmt: v => {
        if (!v) return '<span class="blank">n/a</span>';
        const a = v["10"], b = v["15"], c = v["20"];
        if (a === null || a === undefined) return '<span class="blank">n/a</span>';
        return `<span class="num muted mono">${(-a).toFixed(1)} / ${(-b).toFixed(1)} / ${(-c).toFixed(1)}</span>`;
      }},
      {key:"minutes_coverage", label:"Coverage",
        fmt: v => v === null || v === undefined ? '<span class="blank">n/a</span>'
          : `<span class="num ${v>=0.5?"pos":"neg"}">${(v*100).toFixed(0)}%</span>`},
      {key:"confidence", label:"Confidence", fmt: v => {
        if (!v) return "";
        const k = v.startsWith("HIGH") ? "pass" : v.startsWith("MEDIUM") ? "prov" : v.startsWith("LOW") ? "prov" : "na";
        const parts = v.split(" - ");
        return badge(parts[0], k) + (parts.length > 1 ? `<div class="small faint">${esc(parts.slice(1).join(" - "))}</div>` : "");
      }},
      {key:"src", label:"Src", src:true},
    ];
    setHTML("#tbl-team", table(cols, sortBy(out, "team_weighted_lost_share", -1), {thin:true}));
  }

  function drawPlayer() {
    let rs = rows.filter(r =>
      (!st2.date || r.date === st2.date) &&
      (!st2.team || r.team === st2.team) &&
      (!st2.status || r.status === st2.status) &&
      r.player);
    rs = sortBy(rs, "weighted_share", -1);
    setText("#cnt2", rs.length + " player rows");
    const cols = [
      {key:"date", label:"Date", cls:"date"},
      {key:"matchup", label:"Game", cls:"lbl"},
      {key:"team", label:"TM"},
      {key:"player", label:"Player", cls:"lbl"},
      {key:"status", label:"Status", fmt: v => {
        const k = v === "Out" ? "fail" : v === "Doubtful" ? "prov" :
                  v === "Questionable" ? "prov" : v === "Probable" ? "pass" :
                  v === "Available" ? "pass" : "na";
        return badge(v, k);
      }},
      {key:"reason", label:"Reason as published"},
      {key:"status_weight", label:"Weight", num:true, d:2, cls:"muted"},
      {key:"season_min", label:"MPG", num:true, d:1, cls:"muted"},
      {key:"minutes_share", label:"Min share", fmt: v =>
        v === null || v === undefined
          ? '<span class="blank" title="Outside the captured top-50 minutes table (F2)">unknown</span>'
          : `<span class="num muted">${(v*100).toFixed(1)}%</span>`},
      {key:"weighted_share", label:"Weighted", num:true, d:3, cls:"muted"},
      {key:"src", label:"Src", src:true},
    ];
    setHTML("#tbl-player", table(cols, rs, {thin:true}));
  }
  bind("#f-team", v => {st2.team=v; drawPlayer();});
  bind("#f-status", v => {st2.status=v; drawPlayer();});
  drawTeam(); drawPlayer();
})().catch(e => {setHTML("#tbl-team",'<div class="empty">'+e.message+'</div>');
                 setHTML("#tbl-player",'<div class="empty">'+e.message+'</div>');});
""",

"gameflow": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("gameflow.json"));
  const rows = d.rows;
  const dates = uniq(rows.map(r => r.date)).sort();
  fillChipbar("#f-date", dates, v => {st.date=v; draw();}, "All dates");
  const st = {date:""};
  const draw = () => {
    let rs = rows.filter(r => !st.date || r.date === st.date);
    setText("#cnt", rs.length + " games");
    const cols = [
      {key:"date", label:"Date", cls:"date"},
      {key:"time_et", label:"Tip (ET)"},
      {key:"matchup", label:"Matchup", cls:"lbl"},
      {key:"home_rest_days", label:"Home rest", num:true, d:0, cls:"muted"},
      {key:"away_rest_days", label:"Away rest", num:true, d:0, cls:"muted"},
      {key:"possessions", label:"Poss", num:true, d:1},
      {key:"pace_vs_league", label:"Pace vs Lg", num:true, signed:true, d:1},
      {key:"expected_total", label:"Exp total", num:true, d:1, prov:"derived"},
      {key:"expected_margin_home", label:"Exp margin (home)", num:true, signed:true, d:1, prov:"derived"},
      {key:"p_home_win", label:"P(home)", fmt: v => pct(v) + bar(v*100, v>0.5?"good":"bad"), prov:"derived"},
      {key:"p_margin_within_5", label:"P(within 5)", fmt: v => pct(v), prov:"derived"},
      {key:"p_margin_20plus", label:"P(20+)", fmt: v => pct(v), prov:"derived"},
      {key:"p_overtime_approx", label:"P(OT)", fmt: v => pct(v,2), prov:"derived"},
      {key:"src", label:"Src", src:true},
    ];
    setHTML("#tbl", table(cols, rs, {thin:true}));
  };
  draw();
})().catch(e => setHTML("#tbl", '<div class="empty">'+e.message+'</div>'));
""",

"validation": """
(async () => {
  await initSources();
  const [vd, lb, bt] = await Promise.all([
    loadJSON(DATA("validation.json")),
    loadJSON(DATA("leaderboard.json")),
    loadJSON(DATA("backtest.json"))
  ]);
  const m = vd.metrics;

  const kpi = (label, val, sub, cls) =>
    `<div class="card"><h4>${label}</h4><div class="kpi ${cls||""}">${val}</div>
     <div class="kpi-sub">${sub}</div></div>`;
  const better = (a,b) => a < b ? "good" : a > b ? "bad" : "";
  setHTML("#kpis", `<div class="grid k4">
    ${kpi("Margin MAE", m.mae_margin_model, `reference ${m.mae_margin_ref}`, better(m.mae_margin_model, m.mae_margin_ref))}
    ${kpi("Total MAE", m.mae_total_model, `reference ${m.mae_total_ref}`, better(m.mae_total_model, m.mae_total_ref))}
    ${kpi("Brier (win prob)", m.brier_model, `reference ${m.brier_ref} - lower is better`, better(m.brier_model, m.brier_ref))}
    ${kpi("Straight up", m.straight_up_model, `reference ${m.straight_up_ref}`, "")}
    ${kpi("Test games", m.n_games, m.window, "")}
    ${kpi("Margin RMSE", m.rmse_margin_model, `reference ${m.rmse_margin_ref}`, better(m.rmse_margin_model, m.rmse_margin_ref))}
    ${kpi("Residual SD", m.sigma_margin, "points of game margin", "")}
    ${kpi("Zeroed params", m.mae_margin_zeroed_params, "MAE with HCA and B2B set to 0", "")}
  </div>`);

  // leaderboard
  const lcols = [
    {key:"rank", label:"#", num:true, d:0, cls:"strong"},
    {key:"id", label:"Strat", cls:"lbl"},
    {key:"name", label:"Strategy"},
    {key:"family", label:"Family"},
    {key:"lbs", label:"LBS", num:true, d:1, cls:"strong"},
    {key:"tier", label:"Tier", fmt: v => {
      const cls = v.startsWith("Tier 1")?"t1":v.startsWith("Tier 2")?"t2":v.startsWith("Tier 3")?"t3":"t0";
      return badge(v, cls);
    }},
    {key:"n_graded", label:"Graded", num:true, d:0},
    {key:"record", label:"Record"},
    {key:"units", label:"Units", num:true, signed:true, d:2},
    {key:"components", label:"Components (samp/edge/calib/result/gates)", fmt: v =>
      `<span class="num muted mono">${v.sample.toFixed(2)} ${v.edge.toFixed(2)} ${v.calibration.toFixed(2)} ${v.result.toFixed(2)} ${v.gates.toFixed(2)}</span>`},
  ];
  document.querySelector("#lb").innerHTML =
    "<thead><tr>" + lcols.map(c=>`<th class="${c.num?"num":""}">${c.label}</th>`).join("") +
    "</tr></thead><tbody>" + lb.rows.map(r =>
      "<tr>" + lcols.map(c => {
        const v = r[c.key];
        const html = c.fmt ? c.fmt(v,r) : c.num ? num(v,c.d,c.cls) : esc(v ?? "—");
        return `<td class="${c.num?"num":""}">${html}</td>`;
      }).join("") + "</tr>").join("") + "</tbody>";
  setHTML("#lbnote", `<strong>Formula:</strong> <code>${esc(lb.formula)}</code>.
    <strong>Hard cap:</strong> a strategy that fails G4 (skill, not luck) or has not passed G1
    (sample size) cannot be promoted past Tier 3 regardless of its score — an 8-4 run on 12 plays
    is information about luck, not skill.`);

  // gates
  fillSelect("#f-strat", vd.strategies.map(s => ({v:s.id, l:s.id + " " + s.name})));
  const st = {strat:""};
  const draw = () => {
    let ss = vd.strategies.filter(s => !st.strat || s.id === st.strat);
    setText("#cnt", ss.length + " strategies");
    const cols = [
      {key:"id", label:"Strat", cls:"lbl"},
      {key:"name", label:"Strategy"},
      {key:"rule", label:"Rule", fmt: v => `<span class="small">${esc(v)}</span>`},
      {key:"threshold", label:"Threshold", cls:"mono"},
      {key:"n_graded", label:"Graded", num:true, d:0},
      {key:"record", label:"Record", fmt:(v,r)=>`${r.wins}-${r.losses}${r.pushes?"-"+r.pushes:""}`},
      {key:"hit_rate", label:"Hit rate", fmt: v => v===null?'<span class="blank">n/a</span>':pct(v)},
      {key:"wilson_95", label:"Wilson 95%", fmt: v => v ? `<span class="num muted mono">${pct(v[0],3)} – ${pct(v[1],3)}</span>` : ""},
      {key:"binomial_p", label:"Exact p", num:true, d:3, cls:"muted"},
      {key:"units_at_minus110", label:"Units", num:true, signed:true, d:2},
      {key:"gates", label:"Gates", fmt: v => `<div class="pill-row">` +
        v.map(g => `${gateBadge(g.status)}<span class="small faint">${g.id}</span>`).join("") + `</div>`},
    ];
    setHTML("#tbl-gates", table(cols, ss, {thin:true}));
    // detail rows
    let html = "";
    for (const s of ss) {
      html += `<details class="q"><summary>${esc(s.id)} — ${esc(s.name)}: gate detail</summary><div class="body">`;
      html += `<p class="small"><strong>Why this might work:</strong> ${esc(s.why)}</p>`;
      html += `<div class="tablewrap"><table class="thin"><thead><tr>
        <th>Gate</th><th>Name</th><th>Status</th><th>Detail</th><th>Threshold</th></tr></thead><tbody>`;
      for (const g of s.gates) {
        html += `<tr><td class="lbl">${esc(g.id)}</td><td>${esc(g.name)}</td>
          <td>${gateBadge(g.status)}</td><td class="small">${esc(g.detail)}</td>
          <td class="small faint mono">${esc(g.threshold)}</td></tr>`;
      }
      html += `</tbody></table></div>`;
      if (!s.gradeable) html += `<p class="small"><span class="badge fail">UNGRADED</span> ${esc(s.ungraded_reason||"")}</p>`;
      html += `</div></details>`;
    }
    setHTML("#gatedef", html);
  };
  bind("#f-strat", v => {st.strat=v; draw();});
  draw();

  // gate definitions (rendered once, in their own container)
  setHTML("#gatedefs", `<div class="tablewrap"><table class="thin"><thead><tr>
    <th>Gate</th><th>Name</th><th>Definition</th></tr></thead><tbody>` +
    vd.gate_definitions.map(g => `<tr><td class="lbl">${esc(g.id)}</td><td>${esc(g.name)}</td>
      <td class="small">${esc(g.definition)}</td></tr>`).join("") + `</tbody></table></div>`);

  // fit
  const f = vd.fit;
  const frow = (k, o) => `<tr><td class="lbl">${k}</td>
    <td class="num ${o.est>0?"pos":"neg"}">${o.est}</td>
    <td class="num muted">${o.se}</td><td class="num muted">${o.t}</td>
    <td>${o.used===true?badge("used","pass"):o.used===false?badge("set to 0","fail"):badge(String(o.used),"na")}</td>
    <td class="small faint">${esc(o.disclosure||"")}</td></tr>`;
  setHTML("#fit", `<div class="tablewrap"><table class="thin"><thead><tr>
    <th>Parameter</th><th class="num">Estimate</th><th class="num">Std err</th>
    <th class="num">t</th><th>Applied?</th><th>Disclosure</th></tr></thead><tbody>
    ${frow("Home court advantage", f.hca)}
    ${frow("B2B effect on home margin", f.b2b_coef_on_home_margin)}
    ${frow("Totals bias", f.total_bias)}
    ${frow("Totals B2B coefficient", f.total_b2b_coef)}
    </tbody></table></div>
    <p class="small">n = ${f.n}. Back-to-backs detected: ${f.b2b_detected_home} home,
    ${f.b2b_detected_away} away. <span class="faint">${esc(f.b2b_caveat)}</span></p>`);

  // sweep
  const sd = f.shrink_derivation;
  const sw = `<div class="tablewrap"><table class="thin"><thead><tr>
    <th class="num">k</th><th class="num">HCA</th><th class="num">B2B applied</th>
    <th class="num">Residual SD</th><th class="num">Margin MAE</th><th class="num">Margin RMSE</th>
    <th class="num">Brier</th><th>Selected</th></tr></thead><tbody>` +
    f.shrink_sweep.map(s => `<tr>
      <td class="num ${s.selected?"strong":"muted"}">${s.k}</td>
      <td class="num muted">${s.hca}</td><td class="num muted">${s.b2b_penalty_applied}</td>
      <td class="num muted">${s.sigma_margin}</td>
      <td class="num ${s.selected?"strong":"muted"}">${s.mae_margin}</td>
      <td class="num muted">${s.rmse_margin}</td><td class="num muted">${s.brier}</td>
      <td>${s.selected?badge("selected","pass"):""}</td></tr>`).join("") + `</tbody></table></div>`;
  setHTML("#sweep", `
    <div class="grid k4" style="margin-bottom:12px">
      <div class="card"><h4>Derived k</h4><div class="kpi">${sd.shrink_k_derived}</div>
        <div class="kpi-sub">weight ${sd.shrink_weight_at_G} on the observed rating</div></div>
      <div class="card"><h4>Games per rating</h4><div class="kpi">${sd.games_behind_each_rating_G}</div>
        <div class="kpi-sub">G in the training window</div></div>
      <div class="card"><h4>Single-game noise (s)</h4><div class="kpi">${sd.implied_single_game_team_noise_s}</div>
        <div class="kpi-sub">net rating points per 100</div></div>
      <div class="card"><h4>Implied true spread</h4><div class="kpi">${sd.implied_var_of_true_net_rating}</div>
        <div class="kpi-sub">variance of true net rating</div></div>
    </div>
    <p class="small"><code>${esc(sd.formula)}</code> — ${esc(sd.disclosure)}</p>
    ${sw}`);

  // luck decomposition of the record
  const dec = bt.rows.length;
  const wins = bt.rows.filter(r => r.home_won === 1).length;
  setHTML("#luckbox", `<p class="small">The model's straight-up record on the test window was
    <strong>${m.straight_up_model}</strong> against the reference's
    <strong>${m.straight_up_ref}</strong>. With a residual standard deviation of
    ${m.sigma_margin} points and only ${dec} games, a swing of two or three games is well inside
    one standard deviation of pure chance — which is precisely why gate G4 exists and why nothing
    here is promoted on the strength of this window. See
    <a href="flagged.html">F8</a>.</p>`);
})().catch(e => setHTML("#kpis", '<div class="empty">'+e.message+'</div>'));
""",

"strategy": """
(async () => {
  await initSources();
  const vd = await loadJSON(DATA("validation.json"));
  const ss = vd.strategies;
  fillSelect("#f-family", uniq(ss.map(s => s.family)).sort());
  const st = {family:""};
  const draw = () => {
    let rs = ss.filter(s => !st.family || s.family === st.family);
    setText("#cnt", rs.length + " strategies");
    let html = '<div class="grid k2">';
    for (const s of rs) {
      const gates = s.gates.map(g => `${gateBadge(g.status)} ${g.id}`).join(" ");
      html += `<div class="card">
        <div style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">
          <strong>${esc(s.id)}</strong> <span>${esc(s.name)}</span>
          <span class="badge na">${esc(s.family)}</span>
          ${s.gradeable ? "" : badge("UNGRADED","fail")}
        </div>
        <p class="small" style="margin:8px 0"><strong>Rule:</strong> ${esc(s.rule)}</p>
        <p class="small faint mono" style="margin:0 0 8px">threshold: ${esc(s.threshold)}</p>
        <p class="small" style="margin:0 0 10px"><strong>Why:</strong> ${esc(s.why)}</p>
        ${s.ungraded_reason ? `<p class="small"><span class="badge fail">cannot grade yet</span> ${esc(s.ungraded_reason)}</p>` : ""}
        <div class="pill-row">${gates}</div>
        <div class="small faint" style="margin-top:8px">
          Graded plays: ${s.n_graded} · record ${s.wins}-${s.losses}${s.pushes?"-"+s.pushes:""}
          ${s.n_graded ? ` · ${s.units_at_minus110>=0?"+":""}${s.units_at_minus110} units` : ""}
        </div>
      </div>`;
    }
    html += "</div>";
    setHTML("#cards", html);
  };
  bind("#f-family", v => {st.family=v; draw();});
  draw();
})().catch(e => setHTML("#cards", '<div class="empty">'+e.message+'</div>'));
""",

"correlations": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("correlations.json"));
  const meas = sortBy(d.measured, "r", -1);
  setHTML("#tbl-measured", table([
    {key:"x", label:"Variable A", cls:"lbl"},
    {key:"y", label:"Variable B", cls:"lbl"},
    {key:"r", label:"r", num:true, signed:true, d:3},
    {key:"r_squared", label:"r²", num:true, d:3, cls:"muted"},
    {key:"p_value", label:"p (two-sided)", fmt: v =>
      `<span class="num ${v<0.05?"pos":"muted"}">${v<0.0001?"<0.0001":v.toFixed(4)}</span>`},
    {key:"n", label:"n", num:true, d:0, cls:"muted"},
    {key:"status", label:"Provenance", fmt: v => prov("official","official")},
    {key:"why", label:"Why it matters", fmt: v => `<span class="small faint">${esc(v)}</span>`},
  ], meas, {thin:true}));

  setHTML("#tbl-derived", table([
    {key:"leg_1", label:"Leg 1", cls:"lbl"},
    {key:"leg_2", label:"Leg 2", cls:"lbl"},
    {key:"rho_model", label:"rho", num:true, signed:true, d:2},
    {key:"status", label:"Provenance", fmt: v => prov("assumption","model-derived")},
    {key:"derivation", label:"Where it comes from", fmt: v => `<span class="small faint">${esc(v)}</span>`},
  ], d.model_derived, {thin:true}));

  const g = d.parlay_pricing_grid;
  fillSelect("#f-p", uniq(g.map(r => r.leg_prob)).sort((a,b)=>a-b));
  const st = {p:""};
  const draw = () => {
    let rs = g.filter(r => st.p === "" || Math.abs(r.leg_prob - st.p) < 1e-9);
    setText("#cnt", rs.length + " rows");
    setHTML("#tbl-grid", table([
      {key:"leg_prob", label:"Leg prob", num:true, d:2, cls:"muted"},
      {key:"rho", label:"rho", num:true, signed:true, d:2},
      {key:"true_joint_prob", label:"True joint P", num:true, d:4},
      {key:"independent_product", label:"If priced independent", num:true, d:4, cls:"muted"},
      {key:"difference", label:"Difference", num:true, signed:true, d:4},
      {key:"fair_price_true", label:"Fair price", fmt: v => price(v)},
      {key:"price_if_priced_independent", label:"Naive price", fmt: v => price(v)},
      {key:"bettor_edge_if_priced_independent_pct", label:"Bettor edge if mispriced",
       num:true, signed:true, d:2},
      {key:"rho", label:"Provenance", fmt: v => prov("assumption","model-derived")},
    ], rs, {thin:true}));
  };
  bind("#f-p", v => {st.p = v === "" ? "" : parseFloat(v); draw();});
  draw();
})().catch(e => setHTML("#tbl-measured", '<div class="empty">'+e.message+'</div>'));
""",

"luck": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("luck.json"));
  const rows = d.rows;
  const st = {dir:"all"};
  const draw = () => {
    let rs = rows.filter(r => st.dir === "all" || (st.dir === "over" ? r.luck_z > 0 : r.luck_z < 0));
    rs = sortBy(rs, "luck_z", -1);
    setText("#cnt", rs.length + " teams");
    const cols = [
      {key:"team", label:"TM", cls:"lbl"},
      {key:"name", label:"Team"},
      {key:"gp", label:"GP", num:true, d:0, cls:"muted"},
      {key:"w", label:"W", num:true, d:0},
      {key:"l", label:"L", num:true, d:0, cls:"muted"},
      {key:"netr", label:"Net rtg", num:true, signed:true, d:1},
      {key:"ortg", label:"Off rtg", num:true, d:1, cls:"muted"},
      {key:"drtg", label:"Def rtg", num:true, d:1, cls:"muted"},
      {key:"pyth_win_pct", label:"Pythag", num:true, d:3, cls:"muted", prov:"derived"},
      {key:"expected_wins", label:"Exp W", num:true, d:2, cls:"muted", prov:"derived"},
      {key:"actual_wins", label:"Act W", num:true, d:0, prov:"official"},
      {key:"luck_wins", label:"Luck (W)", num:true, signed:true, d:2, prov:"derived"},
      {key:"luck_z", label:"z", prov:"derived", fmt: v => `${signed(v,2)}${bar(Math.min(100, Math.abs(v)/2.5*100), v>0?"good":"bad")}`},
      {key:"src", label:"Src", src:true},
    ];
    setHTML("#tbl", table(cols, rs, {thin:true}));
  };
  bind("#f-dir", v => {st.dir=v; draw();});
  draw();
})().catch(e => setHTML("#tbl", '<div class="empty">'+e.message+'</div>'));
""",

"backtest": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("backtest.json"));
  const rows = d.rows;
  const dates = uniq(rows.map(r => r.date)).sort();
  fillChipbar("#f-date", dates, v => {st.date=v; draw();}, "All dates");
  const st = {date:"", show:"all"};
  const draw = () => {
    let rs = rows.filter(r => {
      if (st.date && r.date !== st.date) return false;
      if (st.show === "model_better") return Math.abs(r.err_model_margin) < Math.abs(r.err_ref_margin);
      if (st.show === "ref_better") return Math.abs(r.err_model_margin) > Math.abs(r.err_ref_margin);
      if (st.show === "big") return Math.abs(r.err_model_margin) >= 20;
      return true;
    });
    setText("#cnt", rs.length + " games");
    const cols = [
      {key:"date", label:"Date", cls:"date"},
      {key:"matchup", label:"Matchup", cls:"lbl"},
      {key:"away_pts", label:"Away", num:true, d:0, cls:"muted"},
      {key:"home_pts", label:"Home", num:true, d:0, cls:"muted"},
      {key:"ot", label:"OT", num:true, d:0, cls:"muted"},
      {key:"neutral", label:"Neutral", fmt: v => v ? badge("neutral site","prov") : ""},
      {key:"actual_margin_home", label:"Act margin", num:true, signed:true, d:0, cls:"strong", prov:"official"},
      {key:"ref_spread_home", label:"Ref", num:true, signed:true, d:1, cls:"muted", prov:"derived"},
      {key:"model_spread_home", label:"Model", num:true, signed:true, d:1, cls:"muted", prov:"derived"},
      {key:"err_ref_margin", label:"Ref err", num:true, signed:true, d:1, cls:"muted"},
      {key:"err_model_margin", label:"Model err", num:true, signed:true, d:1, prov:"derived"},
      {key:"actual_total", label:"Act total", num:true, d:0, cls:"strong", prov:"official"},
      {key:"ref_total", label:"Ref T", num:true, d:1, cls:"muted", prov:"derived"},
      {key:"model_total", label:"Model T", num:true, d:1, cls:"muted", prov:"derived"},
      {key:"err_model_total", label:"Model err T", num:true, signed:true, d:1, prov:"derived"},
      {key:"home_b2b", label:"H B2B", num:true, d:0, cls:"muted"},
      {key:"away_b2b", label:"A B2B", num:true, d:0, cls:"muted"},
      {key:"src", label:"Src", src:true},
    ];
    setHTML("#tbl", table(cols, rs, {thin:true}));

    // error distribution
    const buckets = [0,5,10,15,20,25,30];
    let html = `<div class="tablewrap"><table class="thin"><thead><tr>
      <th>Absolute margin error</th><th class="num">Model</th><th class="num">Reference</th>
      <th class="num">Model share</th><th class="num">Reference share</th></tr></thead><tbody>`;
    for (let i=0;i<buckets.length;i++){
      const lo = buckets[i], hi = i+1<buckets.length ? buckets[i+1] : 1e9;
      const m = rows.filter(r => Math.abs(r.err_model_margin)>=lo && Math.abs(r.err_model_margin)<hi).length;
      const f = rows.filter(r => Math.abs(r.err_ref_margin)>=lo && Math.abs(r.err_ref_margin)<hi).length;
      html += `<tr><td class="lbl">${lo} – ${hi===1e9?"∞":hi}</td>
        <td class="num">${m}</td><td class="num muted">${f}</td>
        <td class="num muted">${(100*m/rows.length).toFixed(0)}%</td>
        <td class="num muted">${(100*f/rows.length).toFixed(0)}%</td></tr>`;
    }
    html += `</tbody></table></div>
      <p class="small">n = ${rows.length}. Mean absolute margin error: model
      ${d.metrics.mae_margin_model}, reference ${d.metrics.mae_margin_ref}.
      Bias (mean signed error): ${d.metrics.bias_margin_model}.</p>`;
    setHTML("#dist", html);
  };
  bind("#f-show", v => {st.show=v; draw();});
  draw();
})().catch(e => setHTML("#tbl", '<div class="empty">'+e.message+'</div>'));
""",

"teams": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("teams.json"));
  let rows = d.rows;
  fillSelect("#f-sort", [
    {v:"netr",l:"Net rating"},{v:"ortg",l:"Offensive rating"},{v:"drtg",l:"Defensive rating (best first)"},
    {v:"pace",l:"Pace"},{v:"win_pct",l:"Win percentage"},{v:"efg_pct",l:"Effective FG%"},
    {v:"tov_pct",l:"Turnover % (best first)"},{v:"pie",l:"PIE"}
  ]);
  const st = {sort:"netr"};
  const draw = () => {
    let rs = sortBy(rows, st.sort, st.sort==="drtg"||st.sort==="tov_pct" ? 1 : -1);
    setText("#cnt", rs.length + " teams");
    const cols = [
      {key:"abbr", label:"TM", cls:"lbl"},
      {key:"team", label:"Team"},
      {key:"gp", label:"GP", num:true, d:0, cls:"muted"},
      {key:"w", label:"W", num:true, d:0},
      {key:"l", label:"L", num:true, d:0, cls:"muted"},
      {key:"win_pct", label:"Win%", num:true, d:3, prov:"derived"},
      {key:"ortg", label:"Off rtg", num:true, d:1},
      {key:"drtg", label:"Def rtg", num:true, d:1},
      {key:"netr", label:"Net rtg", num:true, signed:true, d:1, cls:"strong"},
      {key:"pace", label:"Pace", num:true, d:2, cls:"muted"},
      {key:"ppg_implied", label:"PPG", num:true, d:1, cls:"muted", prov:"derived"},
      {key:"opp_ppg_implied", label:"Opp PPG", num:true, d:1, cls:"muted", prov:"derived"},
      {key:"efg_pct", label:"eFG%", num:true, d:1, cls:"muted"},
      {key:"ts_pct", label:"TS%", num:true, d:1, cls:"muted"},
      {key:"tov_pct", label:"TOV%", num:true, d:1, cls:"muted"},
      {key:"oreb_pct", label:"OREB%", num:true, d:1, cls:"muted"},
      {key:"dreb_pct", label:"DREB%", num:true, d:1, cls:"muted"},
      {key:"ast_pct", label:"AST%", num:true, d:1, cls:"muted"},
      {key:"pie", label:"PIE", num:true, d:1, cls:"muted"},
      {key:"src", label:"Src", src:true},
    ];
    setHTML("#tbl", table(cols, rs, {thin:true}));
  };
  bind("#f-sort", v => {st.sort=v; draw();});
  draw();
})().catch(e => setHTML("#tbl", '<div class="empty">'+e.message+'</div>'));
""",

"model": """
(async () => {
  await initSources();
  const m = await loadJSON(DATA("meta.json"));
  const rows = Object.entries(m.assumptions).map(([k,v]) => ({key:k, ...v}));
  setHTML("#assump", table([
    {key:"key", label:"Constant", cls:"lbl mono"},
    {key:"value", label:"Value", fmt: v => typeof v === "object"
      ? `<span class="mono small">${esc(JSON.stringify(v))}</span>`
      : `<span class="num strong">${v}</span>`},
    {key:"unit", label:"What it means", fmt: v => `<span class="small">${esc(v)}</span>`},
    {key:"status", label:"Provenance", fmt: v => {
      const k = v.startsWith("ARITHMETIC") ? "derived" : v.startsWith("DERIVED") ? "derived" : "assumption";
      return prov(k, k) + `<div class="small faint" style="margin-top:4px">${esc(v)}</div>`;
    }},
  ], rows, {thin:true}));
})().catch(e => setHTML("#assump", '<div class="empty">'+e.message+'</div>'));
""",

"flagged": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("flagged.json"));
  const rows = d.items;
  fillSelect("#f-sev", uniq(rows.map(r => r.severity)));
  const st = {sev:""};
  const draw = () => {
    let rs = rows.filter(r => !st.sev || r.severity === st.sev);
    const order = {High:0, Medium:1, Low:2, Informational:3};
    rs.sort((a,b) => (order[a.severity]??9) - (order[b.severity]??9));
    setText("#cnt", rs.length + " items");
    let html = "";
    for (const it of rs) {
      const cls = it.severity === "High" ? "high" : it.severity === "Medium" ? "medium" :
                  it.severity === "Informational" ? "info" : "low";
      html += `<details class="q" open><summary>
        <span class="badge ${cls}">${esc(it.severity)}</span>
        <span class="mono faint">${esc(it.id)}</span> ${esc(it.title)}</summary>
        <div class="body">
          <p>${esc(it.detail)}</p>
          <dl class="kv">
            <dt>Affects</dt><dd>${esc(it.affected)}</dd>
            <dt>Source</dt><dd>${srcLink(it.source, it.source + " — " + (SOURCE_IDX[it.source]||{}).title)}</dd>
            <dt>Suggested action</dt><dd>${esc(it.suggested_action)}</dd>
          </dl>
        </div></details>`;
    }
    setHTML("#items", html);
  };
  bind("#f-sev", v => {st.sev=v; draw();});
  draw();
})().catch(e => setHTML("#items", '<div class="empty">'+e.message+'</div>'));
""",

"questions": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("questions.json"));
  let html = "";
  for (const a of d.answered) {
    html += `<details class="q"><summary>
      <span class="badge pass">ANSWERED</span>
      <span class="mono faint">${esc(a.id)}</span> ${esc(a.question)}</summary>
      <div class="body">
        <p>${esc(a.answer)}</p>
        <dl class="kv">
          <dt>Source</dt><dd>${srcLink(a.source, (SOURCE_IDX[a.source]||{}).title || a.source)}</dd>
          <dt>Confidence</dt><dd>${esc(a.confidence)}</dd>
        </dl>
      </div></details>`;
  }
  setHTML("#answered", html);

  const open = [...d.open].sort((x,y) => x.priority - y.priority);
  html = "";
  for (const q of open) {
    html += `<details class="q" ${q.priority<=2?"open":""}><summary>
      <span class="badge fail">OPEN</span>
      <span class="mono faint">${esc(q.id)} · priority ${q.priority}</span> ${esc(q.question)}</summary>
      <div class="body">
        <dl class="kv">
          <dt>What is missing</dt><dd>${esc(q.what_is_missing)}</dd>
          <dt>How to answer it</dt><dd>${esc(q.how_to_answer)}</dd>
          <dt>What it blocks</dt><dd>${esc(q.blocks)}</dd>
        </dl>
      </div></details>`;
  }
  setHTML("#open", html || '<div class="empty">No open questions.</div>');
})().catch(e => setHTML("#answered", '<div class="empty">'+e.message+'</div>'));
""",

"suggestions": """
(async () => {
  await initSources();
  const d = await loadJSON(DATA("suggestions.json"));
  const rows = d.items;
  fillSelect("#f-cat", uniq(rows.map(r => r.category)).sort());
  const st = {cat:""};
  const draw = () => {
    let rs = rows.filter(r => !st.cat || r.category === st.cat);
    setText("#cnt", rs.length + " suggestions");
    let html = "";
    for (const s of rs) {
      let opts = `<div class="tablewrap"><table class="thin"><thead><tr>
        <th>Option</th><th>Effort</th><th>Risk</th><th>Unlocks</th></tr></thead><tbody>`;
      for (const o of s.options) {
        const rk = o.risk.startsWith("Low") ? "pass" : o.risk.startsWith("Medium") ? "prov" : "fail";
        opts += `<tr><td>${esc(o.option)}</td><td class="small">${esc(o.effort)}</td>
          <td>${badge(o.risk.split(" - ")[0], rk)}</td>
          <td class="small">${esc(o.unlocks)}</td></tr>`;
      }
      opts += `</tbody></table></div>`;
      html += `<details class="q"><summary>
        <span class="badge na">${esc(s.category)}</span>
        <span class="mono faint">${esc(s.id)}</span> ${esc(s.title)}</summary>
        <div class="body">
          <p><strong>Problem:</strong> ${esc(s.problem)}</p>
          <h4>Options</h4>${opts}
          <p style="margin-top:12px"><strong>Recommendation:</strong> ${esc(s.recommendation)}</p>
          <p class="small"><strong>Decision needed:</strong> ${esc(s.decision_needed)}</p>
        </div></details>`;
    }
    setHTML("#items", html);
  };
  bind("#f-cat", v => {st.cat=v; draw();});
  draw();
})().catch(e => setHTML("#items", '<div class="empty">'+e.message+'</div>'));
""",

"sources": """
(async () => {
  await initSources();
  const rows = Object.entries(SOURCES.sources).map(([id,s]) => ({id, ...s}));
  setHTML("#tbl", table([
    {key:"id", label:"ID", cls:"lbl mono"},
    {key:"title", label:"Source", fmt:(v,r)=>`<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(v)}</a>
       <div class="small faint mono">${esc(r.url)}</div>`},
    {key:"publisher", label:"Publisher"},
    {key:"used_for", label:"Used for", fmt: v => `<span class="small">${esc(v)}</span>`},
  ], rows, {thin:true}));
})().catch(e => setHTML("#tbl", '<div class="empty">'+e.message+'</div>'));
""",
}


# extra helpers injected into site.js
EXTRA_JS = """
function pct(v, d=1) {
  if (v === null || v === undefined || Number.isNaN(v)) return '<span class="blank">n/a</span>';
  return `<span class="num ${v>=0.5?"pos":"neg"}">${(v*100).toFixed(d)}%</span>`;
}
function fillSelect(sel, options) {
  const e = document.querySelector(sel);
  if (!e) return;
  const cur = e.value;
  for (const o of options) {
    if (o && typeof o === "object" && o.v !== undefined) {
      const op = document.createElement("option");
      op.value = o.v; op.textContent = o.l; e.appendChild(op);
    } else {
      const op = document.createElement("option");
      op.value = o; op.textContent = o; e.appendChild(op);
    }
  }
  if (cur) e.value = cur;
}
function fillChipbar(sel, options, onChange, allLabel) {
  const el = document.querySelector(sel);
  if (!el) return;
  el.innerHTML = "";
  const mk = (val, label) => {
    const b = document.createElement("button");
    b.className = "chip" + (val === "" ? " on" : "");
    b.textContent = label;
    b.onclick = () => {
      [...el.children].forEach(c => c.classList.remove("on"));
      b.classList.add("on");
      onChange(val);
    };
    el.appendChild(b);
  };
  mk("", allLabel || "All");
  for (const o of options) mk(o, o);
}
function bind(sel, fn) {
  const e = document.querySelector(sel);
  if (e) e.addEventListener("change", ev => fn(ev.target.value));
}
"""


def main():
    os.makedirs(PAGES, exist_ok=True)
    meta = read_json(os.path.join(OUT, "meta.json"))
    ex = read_json(os.path.join(OUT, "executive.json"))

    # index (namespaced)
    write(os.path.join(DOCS, SUB, "index.html"),
          page("index", "Executive Summary", p_index(meta, ex),
               subtitle="Original NBA line origination, validation and analysis",
               depth=0, page_prefix="", asset_prefix="../"))

    bodies = {
        "lines": ("Originated Lines", p_lines()),
        "picks": ("Picks", p_picks()),
        "props": ("Player Props", p_props()),
        "injuries": ("Injuries & Rotation", p_injuries()),
        "gameflow": ("Game Flow", p_gameflow()),
        "validation": ("Validation & Leaderboard", p_validation()),
        "strategy": ("Strategy Library", p_strategy()),
        "correlations": ("Correlations", p_correlations()),
        "luck": ("Luck", p_luck()),
        "backtest": ("Out-of-Sample Game Log", p_backtest()),
        "teams": ("Team Ratings", p_teams()),
        "model": ("Model", p_model()),
        "flagged": ("Flagged for Review", p_flagged()),
        "questions": ("Open Questions", p_questions()),
        "suggestions": ("Suggestions", p_suggestions()),
        "sources": ("Sources", p_sources()),
    }
    for key, (title, body) in bodies.items():
        script = SCRIPTS.get(key, "")
        if script:
            body += f"\n<script>\n{script}\n</script>\n"
        write(os.path.join(PAGES, key + ".html"),
              page(key, title, body, depth=1,
                   page_prefix="../", asset_prefix="../../"))

    # append helpers to site.js
    js_path = os.path.join(DOCS, "assets", "site.js")
    src = open(js_path, encoding="utf-8").read()
    marker = "function pct(v, d=1) {"
    if marker not in src:
        src = src.rstrip() + "\n\n/* ---- form + formatting helpers ---- */\n" + EXTRA_JS
        open(js_path, "w", encoding="utf-8").write(src)

    # .nojekyll so GitHub Pages serves directories starting with underscore, if any
    open(os.path.join(DOCS, ".nojekyll"), "w").write("")
    print(f"Wrote {len(bodies)+1} pages to {DOCS}")


def write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


if __name__ == "__main__":
    main()
