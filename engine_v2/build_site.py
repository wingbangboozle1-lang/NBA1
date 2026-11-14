"""Renders the unified static site.

Layout: a root landing dashboard (index.html) plus category subpages under
site/pages/.  No build step at deploy time, no framework, no external requests:
every page is plain HTML with one stylesheet and one small vanilla-JS helper.

Rule enforced while rendering: every table row carries a link to the official
page the row came from.  A value that could not be read from an official page is
rendered as an em dash inside a .blank cell, which is styled to be visibly
"missing", never as zero.
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime

from .common import NAMES, ROOT, load
from .content import FLAGGED, QUESTIONS, SOURCES, SUGGESTIONS
from .model import K_MARGIN, K_TOTAL
from .site_assets import CSS, JS

# GitHub Pages deploys the repository root, and that root is owned and actively
# maintained by other sessions. This build therefore claims one namespace of its
# own and touches nothing else: origination/index.html, origination/pages/,
# origination/assets/.
SITE = os.path.join(ROOT, "origination")
PAGES = os.path.join(SITE, "pages")
ASSETS = os.path.join(SITE, "assets")
DATA = os.path.join(ROOT, "data", "derived")

CAPTURE = "2026-11-14 00:42 UTC"

NAV = [
    ("Overview", [("index.html", "Executive dashboard")]),
    ("Lines and game flow", [
        ("pages/lines.html", "Originated lines"),
        ("pages/gameflow.html", "Game flow and rest"),
    ]),
    ("Strategy lab", [
        ("pages/strategies.html", "Strategy library"),
        ("pages/leaderboard.html", "Leaderboard and rewards"),
        ("pages/gates.html", "Validation gates"),
        ("pages/luck.html", "Luck removal and power"),
        ("pages/signals.html", "Signal study"),
    ]),
    ("Model and data", [
        ("pages/teams.html", "Team ratings"),
        ("pages/backtest.html", "Walk-forward backtest"),
        ("pages/gamelog.html", "Official game log"),
        ("pages/correlations.html", "Correlations and parlays"),
        ("pages/method.html", "Method"),
    ]),
    ("Availability", [
        ("pages/injuries.html", "Injuries and rotation"),
        ("pages/props.html", "Player props"),
    ]),
    ("Governance", [
        ("pages/questions.html", "Open questions"),
        ("pages/suggestions.html", "Suggestions"),
        ("pages/sources.html", "Source register"),
        ("pages/flagged.html", "Flagged for review"),
        ("pages/repo-review.html", "Repository review"),
    ]),
]

GAMES_URL = "https://www.nba.com/games?date="   # official daily scoreboard

BASE_URL = ""   # relative links: works locally, in a preview iframe and under
                # GitHub Pages' /NBA1/ project path without any build step


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def rel(href, depth):
    """Resolve a site-root-relative href against the current page's depth."""
    return ("../" * depth) + href


def plink(href, depth):
    """Site-root-relative page href -> href valid from a page at this depth."""
    if not depth:
        return href
    return href[6:] if href.startswith("pages/") else "../" + href


def localise(html_str, depth):
    """Rewrite the BASE_URL-prefixed links inside a page body for its depth."""
    if not depth:
        return html_str
    return (html_str
            .replace('href="pages/', 'href="')
            .replace('href="assets/', 'href="../assets/')
            .replace('href="index.html', 'href="../index.html'))


def e(x):
    return html.escape(str(x), quote=True)


def n2(v, dp=2):
    """Number, or an em dash styled as missing when the value is unknown."""
    if v is None or v == "":
        return '<span class="blank" title="Not available from an official source">&mdash;</span>'
    if isinstance(v, float):
        return f"{v:,.{dp}f}"
    return e(v)


def pct(v, dp=1):
    return n2(v * 100.0, dp) + "%" if isinstance(v, (int, float)) else n2(v)


def signed(v, dp=2, suffix=""):
    if v is None:
        return n2(None)
    return f"{v:+,.{dp}f}{suffix}"


def flip(name):
    """"Antetokounmpo, Giannis" -> "Giannis Antetokounmpo" for display."""
    if "," in name:
        last, first = name.split(",", 1)
        return first.strip() + " " + last.strip()
    return name


def date_links(dates, limit=14):
    """One official daily-scoreboard link per date the row's games were played."""
    ds = sorted(set(dates))
    if not ds:
        return n2(None)
    out = [f'<a class="src" href="{GAMES_URL}{d}" target="_blank" rel="noopener">{d[5:]}</a>'
           for d in ds[:limit]]
    if len(ds) > limit:
        out.append(f'<span class="small">+{len(ds) - limit} more</span>')
    return " ".join(out)


def bet_sources(bets, eval_dates=None):
    """Official links for the games a row actually rests on.

    A cell that generated no bets has no bet dates, so it falls back to the
    evaluated window: that is still the sample the row was tested on, and it is
    marked as such rather than left blank.
    """
    if bets:
        return date_links([b.get("date") for b in bets if b.get("date")])
    if eval_dates:
        return (date_links(eval_dates) +
                '<span class="small"> (no bets generated over this window)</span>')
    return n2(None)


def srclink(url, label=None):
    if not url:
        return '<span class="blank">&mdash;</span>'
    return f'<a class="src" href="{e(url)}" target="_blank" rel="noopener">{e(label or "source")}</a>'


def badge(text, kind):
    return f'<span class="badge b-{kind}">{e(text)}</span>'


def gate_mark(ok):
    return '<span class="g pass">PASS</span>' if ok else '<span class="g fail">FAIL</span>'


def tier_badge(t, name):
    kind = {0: "t0", 1: "t1", 2: "t2", 3: "t3", 4: "t4"}[t]
    return badge(f"T{t} \u00b7 {name}", kind)


def page(title, subtitle, body, active="index.html", extra_head="", depth=0):
    nav_html = []
    for group, items in NAV:
        nav_html.append(f'<div class="navgroup"><h4>{group}</h4><ul>')
        for href, label in items:
            cls = ' class="active"' if href == active else ""
            nav_html.append(f'<li><a{cls} href="{plink(href, depth)}">{label}</a></li>')
        nav_html.append("</ul></div>")
    nav_html = "\n".join(nav_html)
    return localise(f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} &middot; NBA Line Origination Desk</title>
<meta name="description" content="NBA lines originated from official NBA.com final scores, with a gated strategy leaderboard.">
<link rel="stylesheet" href="{rel('assets/style.css', depth)}">
{extra_head}
</head><body>
<div class="wrap">
<aside class="side">
  <a class="brand" href="{plink('index.html', depth)}"><span class="dot"></span>NBA&nbsp;Line&nbsp;Origination&nbsp;Desk</a>
  <div class="cap">Official capture {e(CAPTURE)}</div>
  <nav>{nav_html}</nav>
  <div class="sidenote">
    Every table row links to the official page it was read from.
    A dash means the value is not published, not that it is zero.
  </div>
</aside>
<main class="main">
  <header class="top">
    <h1>{e(title)}</h1>
    <p class="sub">{subtitle}</p>
  </header>
  <div class="banner">
    <strong>No strategy is funded.</strong> All {len(FLAGGED)} flagged items and every unvalidated number are published
    <a href="{BASE_URL}pages/flagged.html">here</a>. There is no market odds feed, so nothing on this site is a claim of real-world profit.
  </div>
  {body}
  <footer class="foot">
    <p>Session <code>arena/e32856d8-nba1</code>. Official capture {e(CAPTURE)}.
    Model inputs: official NBA.com final scores and schedule only.
    <a href="{BASE_URL}pages/sources.html">Source register</a> &middot;
    <a href="{BASE_URL}pages/method.html">Method</a> &middot;
    <a href="{BASE_URL}pages/flagged.html">Flagged for review</a> &middot;
    <a href="https://github.com/wingbangboozle1-lang/NBA1" target="_blank" rel="noopener">Repository</a></p>
  </footer>
</main>
</div>
<script src="{rel('assets/app.js', depth)}"></script>
</body></html>""", depth)


def table(headers, rows, cls="", caption=None, definitions=False):
    h = "".join(f"<th>{x}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    cap = f"<caption>{caption}</caption>" if caption else ""
    classes = ("tbl " + cls + (" definitions" if definitions else "")).strip()
    return (f'<div class="tablewrap"><table class="{classes}" data-sortable>'
            f"{cap}<thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>")


def card(title, body, kind=""):
    return f'<section class="card {kind}"><h3>{e(title)}</h3>{body}</section>'


def kpi(label, value, note=""):
    return (f'<div class="kpi"><div class="k-val">{value}</div>'
            f'<div class="k-lab">{e(label)}</div>'
            + (f'<div class="k-note">{note}</div>' if note else "") + "</div>")


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------
def build_index(eng, ctx):
    m, g6 = eng["meta"], eng["g6"]
    live = [s for s in eng["strategies"] if s["stats"] and s["stats"]["bets"] >= eng["min_bets"]]
    funded = [s for s in eng["strategies"] if s["tier"] >= 3]
    blocked = [s for s in eng["strategies"] if s["blocked"]]
    rest = next((s for s in eng["signal_study"] if s["label"].startswith("Rest-day")), None)

    kpis = "".join([
        kpi("Games in window", f'{m["total_games_in_window"]}',
            f'{m["captured_games"]} scores verified &middot; {m["unpublished_fixtures"]} published without scores'),
        kpi("Originated lines", f'{len(eng["slate"])}',
            "3-day slate 14&ndash;16 November 2026"),
        kpi("Out-of-sample games", f'{g6["games"]}',
            f'walk-forward, {m["eval_window"]}'),
        kpi("Model vs naive (MAE)", f'{g6["mae_margin"]:.2f}',
            f'naive {g6["mae_margin_naive"]:.2f} &middot; Brier {g6["brier"]:.3f} vs {g6["brier_naive"]:.3f}'),
        kpi("Strategy cells tested", f'{len(eng["strategies"])}',
            f'{len([s for s in eng["strategies"] if s["stats"]])} produced bets &middot; {len(blocked)} blocked'),
        kpi("Strategies funded", f'{len(funded)}', "gate result, not a preference"),
    ])

    slate_rows = []
    for g in eng["slate"]:
        slate_rows.append([
            g["date"], g["time_et"], f'{e(g["away"])} @ {e(g["home"])}',
            signed(g["spread_home"], 1), n2(g["total"], 1),
            pct(g["p_home_win"]),
            f'{n2(g["ml_home"],0)} / {n2(g["ml_away"],0)}',
            signed(g["signal_margin_shift"], 1),
            f'{n2(g["rest_away"])}/{n2(g["rest_home"])}',
            srclink(g["source_url"], "nba.com"),
        ])

    findings = [
        ("The game log is complete and verified.",
         f'All 30 teams&rsquo; game counts reconstructed from the {m["captured_games"]} captured scores '
         f'plus the {m["unpublished_fixtures"]} unpublished fixtures equal the official standings exactly '
         f'({m["total_games_in_window"]} games). This is the strongest available evidence that the log is '
         f'complete and correctly oriented.'),
        ("The line-generating model beats a naive baseline.",
         f'Out-of-sample margin error {g6["mae_margin"]:.2f} points against {g6["mae_margin_naive"]:.2f} for '
         f'a naive constant, Brier {g6["brier"]:.3f} against {g6["brier_naive"]:.3f}, and '
         f'{g6["straight_up"]} straight up ({pct(g6["straight_up_pct"])}). The line is a credible baseline '
         f'to test strategies against.'),
        ("No strategy passes the gates, and the reason is sample size, not design.",
         f'Only {len(live)} of {len(eng["strategies"])} cells reach the {eng["min_bets"]}-bet floor. The best one '
         f'shows {pct(eng["strategies"][0]["stats"]["roi"])} ROI on {eng["strategies"][0]["stats"]["bets"]} bets, '
         f'but a no-skill bettor beats {pct(eng["strategies"][0]["stats"]["luck_line_roi"])} ROI 5% of the time at '
         f'that sample. Observed performance is inside the luck band, not outside it.'),
        ("One signal is worth keeping; three are dead.",
         f'Rest-day differential moves the margin by {rest["slope"]:+.2f} points per day '
         f'(t = {rest["t"]:+.2f}, p = {rest["p"]:.3f}, n = {rest["n"]}) &mdash; not significant, but the only '
         f'candidate that is not obviously zero, and it would need about {rest["n_required"]} games to resolve. '
         f'Back-to-back, schedule density and every totals signal are indistinguishable from nothing.'),
        ("Correlations are close to zero, which is itself the answer.",
         f'Margin and total correlate at r = {eng["correlations"]["pairs"][0]["r"]:+.3f} over '
         f'{eng["correlations"]["pairs"][0]["n"]} games (p = {eng["correlations"]["pairs"][0]["p"]:.2f}), and the '
         f'out-of-sample residual correlation is r = {eng["correlations"]["pairs"][3]["r"]:+.3f}. Same-game parlays '
         f'should be priced at independence until a much larger sample says otherwise.'),
        ("Injuries are published as context, not baked into the number.",
         f'{ctx["coverage"]["players_in_latest_report"]} players are listed in the latest official report; only '
         f'{ctx["coverage"]["players_with_verified_season_average"]} of them have a verified season average in the '
         f'partial leaderboards available. Rotation minutes are not estimated anywhere.'),
    ]
    f_html = "".join(
        f'<div class="finding"><h4>{i}. {e(t)}</h4><p>{b}</p></div>'
        for i, (t, b) in enumerate(findings, 1))

    body = f"""
<section class="kpis">{kpis}</section>

<section class="card">
  <h3>Executive summary</h3>
  <p class="lede">This desk originates its own NBA lines from one input: the official final scores published by
  NBA.com. It then runs a leaderboard competition in which every strategy must beat that originated line using
  information the line itself does not use. Nothing is funded yet, and the reason is quantified rather than
  asserted.</p>
  {f_html}
  <h4>What would change the answer</h4>
  <ol class="plain">
    <li><strong>More games.</strong> The season adds roughly seven games a day. The rest signal needs about
        {rest["n_required"]} games; there are {m["captured_games"]} today.</li>
    <li><strong>A market price.</strong> Without it, &ldquo;edge&rdquo; only ever means &ldquo;beats our own number&rdquo;.</li>
    <li><strong>A player game log.</strong> It is the only thing standing between this desk and player props.</li>
  </ol>
</section>

<section class="card">
  <h3>Three-day slate at a glance &middot; {len(eng["slate"])} originated lines</h3>
  <p>Spread is from the home team&rsquo;s point of view: a positive number means the home team is getting points.
  Signal shift is the adjustment the rest and back-to-back strategies would apply; it is <em>not</em> included in
  the spread shown, because no strategy has earned the right to move it.</p>
  {table(["Date", "Tip (ET)", "Matchup", "Home spread", "Total", "P(home)", "ML home / away",
          "Signal shift", "Rest A/H", "Official source"], slate_rows)}
  <p class="tn"><a href="{BASE_URL}pages/lines.html">Full lines page with model detail</a></p>
</section>

<section class="grid2">
  {card("Where to look next", f'''
   <ul class="plain">
     <li><a href="{BASE_URL}pages/lines.html">Originated lines</a> &mdash; all 22 games, 14&ndash;16 November.</li>
     <li><a href="{BASE_URL}pages/leaderboard.html">Leaderboard</a> &mdash; every strategy cell ranked, with its luck line.</li>
     <li><a href="{BASE_URL}pages/luck.html">Luck removal</a> &mdash; why a +23% ROI is not evidence.</li>
     <li><a href="{BASE_URL}pages/signals.html">Signal study</a> &mdash; the only candidate signal, and what it needs.</li>
     <li><a href="{BASE_URL}pages/questions.html">Open questions</a> &mdash; {len(QUESTIONS)} decisions blocked by missing information.</li>
     <li><a href="{BASE_URL}pages/suggestions.html">Suggestions</a> &mdash; {len(SUGGESTIONS)} ranked options, none implemented.</li>
   </ul>''')}
  {card("Standing limitations", f'''
   <ul class="plain">
     <li>No market odds from any official source (<a href="{BASE_URL}pages/flagged.html#F2">F2</a>).</li>
     <li>No verified player game log, so no props (<a href="{BASE_URL}pages/flagged.html#F3">F3</a>).</li>
     <li>{m["unpublished_fixtures"]} games published as fixtures without scores (<a href="{BASE_URL}pages/flagged.html#F1">F1</a>).</li>
     <li>{len(FLAGGED)} items total on the <a href="{BASE_URL}pages/flagged.html">flagged page</a>.</li>
   </ul>''')}
</section>
"""
    return page("Executive dashboard",
                "Lines originated from official NBA.com final scores, and a strategy leaderboard that has not yet funded anything.",
                body, "index.html")


def build_lines(eng):
    rows = []
    for g in eng["slate"]:
        wide = abs(g["spread_home"]) >= 15
        rows.append([
            g["date"], g["time_et"], f'{e(g["away"])} @ {e(g["home"])}',
            f'{e(g["away_rec"])} / {e(g["home_rec"])}',
            (f'<strong>{signed(g["spread_home"], 1)}</strong>' +
             (badge("wide", "warn") if wide else "")),
            n2(g["total"], 1),
            f'{n2(g["pred_away_pts"], 1)} &ndash; {n2(g["pred_home_pts"], 1)}',
            pct(g["p_home_win"]),
            f'{n2(g["ml_home"], 0)} / {n2(g["ml_away"], 0)}',
            signed(g["rating_away"], 1) + " / " + signed(g["rating_home"], 1),
            signed(g["signal_margin_shift"], 2),
            srclink(g["source_url"], "game page"),
        ])
    body = f"""
<section class="card">
  <h3>How to read these numbers</h3>
  <ul class="plain">
    <li><strong>Home spread</strong> is from the home team&rsquo;s point of view. <code>-6.5</code> means the home
        team is favoured by 6.5; <code>+6.5</code> means it is getting 6.5 points. It is the negative of the model&rsquo;s
        predicted home margin, so by construction the model thinks each side is a coin flip against it.</li>
    <li><strong>Total</strong> is the sum of the two teams&rsquo; opponent-adjusted points predictions.</li>
    <li><strong>ML</strong> is the fair American price implied by a normal distribution around the predicted
        margin with an out-of-sample standard deviation of {eng["meta"]["sigma_margin"]:.2f} points. It carries no
        margin, because this desk is not a book.</li>
    <li><strong>Signal shift</strong> is what the rest and back-to-back strategies would add. It is shown beside
        the line and <em>not</em> inside it, because no strategy has passed a gate.</li>
    <li>Rows tagged <span class="badge b-warn">wide</span> have a spread of 15 points or more. The ratings behind
        them rest on 10&ndash;12 games per team; see <a href="{BASE_URL}pages/flagged.html#F6">F6</a>.</li>
  </ul>
</section>
<section class="card">
  <h3>Originated lines &middot; 2026-11-14 to 2026-11-16</h3>
  {table(["Date", "Tip (ET)", "Matchup", "Records A/H", "Home spread", "Total", "Pred score A&ndash;H",
          "P(home)", "ML", "Ratings A/H", "Signal shift", "Official source"], rows)}
  <p class="tn">Records are the values printed on the official game card at capture time and are carried for
  reference; the authoritative record table is the <a href="https://www.nba.com/standings" target="_blank" rel="noopener">official standings</a>.</p>
</section>
"""
    return page("Originated lines",
                "22 lines for the maximum three-day horizon, originated from official final scores only.",
                body, "pages/lines.html", depth=1)


def build_strategies(eng):
    ev = [r["date"] for r in eng["eval_games"]]
    rows = []
    for s in eng["strategies"]:
        st = s["stats"]
        rows.append([
            f'<code>{e(s["id"])}</code>', s["name"], s["kind"], bet_sources(s["bets"], ev),
            (f'{st["bets"]}' if st else n2(None)),
            (f'{st["wins"]}&ndash;{st["losses"]}' if st else n2(None)),
            (pct(st["roi"]) if st else n2(None)),
            (pct(st["p_null"], 3) if st else n2(None)),
            (pct(st["luck_line_roi"]) if st else n2(None)),
            (pct(st.get("mde_roi")) if st and st.get("mde_roi") is not None else n2(None)),
            tier_badge(s["tier"], s["tier_name"]),
        ])
    body = f"""
<section class="card">
  <h3>The library</h3>
  <p>Every strategy is the originated line plus one extra official input the line does not use. The line is the
  baseline; the strategy is the claim that something else matters. Each strategy is run at three trigger levels
  (the smallest probability edge it will bet on), and every cell is published &mdash; the trigger is not tuned.</p>
  {table(["Cell", "Strategy", "Type", "Official games", "Bets", "W&ndash;L", "ROI", "p(null)",
          "Luck line", "Min det. ROI", "Tier"], rows)}
  <p class="tn"><strong>p(null)</strong> is the share of 5,000 no-skill bettors placing the identical bet list who
  matched or beat the observed ROI. <strong>Luck line</strong> is the ROI a no-skill bettor beats only 5% of the
  time at this sample &mdash; anything below it is indistinguishable from luck. <strong>Min det. ROI</strong> is the
  smallest true ROI this many bets could detect at 80% power.</p>
</section>
<section class="card">
  <h3>What each strategy claims</h3>
  <div class="defs">
  {"".join(f'<div class="def"><h4><code>{e(s["id"])}</code> {e(s["name"])}</h4>'
           f'<p class="sig"><em>Signal:</em> {e(s["signal"])}</p><p>{e(s["description"])}</p>'
           + (f'<p class="blocked">Blocked: {e(s["block_reason"])}</p>' if s["blocked"] else "")
           + '</div>' for s in eng["strategies"] if s["trigger"] == eng["edge_triggers"][0])}
  </div>
</section>
"""
    return page("Strategy library",
                f'{len(eng["strategies"])} cells across singles, parlays, same-game parlays and prop combos.',
                body, "pages/strategies.html", depth=1)


def build_leaderboard(eng):
    ev = [r["date"] for r in eng["eval_games"]]
    rows = []
    for i, s in enumerate(eng["strategies"], 1):
        st = s["stats"]
        rows.append([
            i, f'<code>{e(s["id"])}</code>', s["name"], bet_sources(s["bets"], ev),
            (f'{st["bets"]}' if st else n2(None)),
            (pct(st["roi"]) if st else n2(None)),
            (pct(st["skill_est_roi"]) if st else n2(None)),
            (signed(st["excess_over_luck_pp"], 1, "pp") if st else n2(None)),
            (pct(st["p_null"], 3) if st else n2(None)),
            (f'{s["score"]:+.4f}' if st and s["score"] is not None else n2(None)),
            tier_badge(s["tier"], s["tier_name"]),
            f'{s["stake"]:.1f}u',
        ])
    TIER_ROWS = [
        [badge("T0 · Unranked", "t0"), "Below the sample floor, or blocked for missing data", "0",
         "Fails G1, or the data to run it does not exist"],
        [badge("T1 · Paper", "t1"), "Tracked, not trusted", "0",
         "Reaches G1 but nothing else"],
        [badge("T2 · Promising", "t2"), "Significant before multiple-comparison correction", "0",
         "Passes G2 and G3, fails G7"],
        [badge("T3 · Funded - half unit", "t3"), "Survives every gate", "0.5u",
         "All gates conjoined"],
        [badge("T4 · Funded - full unit", "t4"), "Survives every gate with size", "1.0u",
         "All gates conjoined and ROI ≥ 10%"],
    ]
    tiers = table(["Tier", "Meaning", "Stake", "Requirement"], TIER_ROWS,
                  caption="Definitions, not data: the reward ladder this project applies to its own "
                          "leaderboard, so no external source applies.",
                  definitions=True)
    body = f"""
<section class="card">
  <h3>Leaderboard</h3>
  <p>Ranked by score = ROI &times; sqrt(min(bets,100)/100) &times; (1 &minus; p<sub>null</sub>), which rewards
  return, sample size and statistical cleanliness together. A strategy that wins 6 of 10 bets does not out-rank
  one that wins 60 of 100 at the same rate.</p>
  {table(["#", "Cell", "Strategy", "Official games", "Bets", "ROI", "Skill est.", "vs luck line",
          "p(null)", "Score", "Tier", "Stake"], rows)}
</section>
<section class="card">
  <h3>Reward tiers</h3>
  {tiers}
  <p class="tn">The gates are <strong>conjoined</strong>: failing any single one blocks promotion, no matter how
  good the score. No cell has ever reached T3.</p>
</section>
"""
    return page("Leaderboard and rewards",
                "Every strategy cell ranked, with the reward tier it has actually earned.",
                body, "pages/leaderboard.html", depth=1)


def build_gates(eng):
    ev = [r["date"] for r in eng["eval_games"]]
    g6 = eng["g6"]
    GATE_ROWS = [
        ["<strong>G1</strong> Sample floor", f'≥ {eng["min_bets"]} bets',
         "Below this, a record cannot be distinguished from noise at any plausible effect size."],
        ["<strong>G2</strong> Positive return", "ROI &gt; 0 at the baseline price", "Non-negotiable."],
        ["<strong>G3</strong> Significance",
         "p<sub>null</sub> ≤ 0.05 against 5,000 Monte-Carlo no-skill bettors",
         "The luck test proper: the null takes the identical bet list with outcomes drawn at the baseline probability."],
        ["<strong>G4</strong> Stability", "ROI &gt; 0 in both halves of the window",
         "Stops one hot week carrying a strategy."],
        ["<strong>G5</strong> No look-ahead", "Mechanical",
         "Every forecast is fitted only on games strictly before the game being forecast."],
        ["<strong>G6</strong> Baseline sanity", "Brier ≤ 0.25 and MAE better than naive",
         "If the line itself is junk, nothing measured against it means anything."],
        ["<strong>G7</strong> Multiple comparisons", f'p<sub>null</sub> ≤ {eng["sidak_alpha"]:.5f}',
         f'Šidák correction across all {sum(1 for s in eng["strategies"] if s["stats"] and s["stats"]["bets"] >= eng["min_bets"])} '
         f'cells that reach the floor. Testing {len(eng["strategies"])} cells at α = 0.05 would produce false '
         f'positives by construction.'],
    ]
    g6_src = date_links([r["date"] for r in eng["eval_games"]])
    g6rows = [
        ["Baseline Brier score &le; 0.25", f'{g6["brier"]:.4f}',
         f'naive constant-forecast Brier {g6["brier_naive"]:.4f}', gate_mark(g6["brier"] <= 0.25),
         g6_src],
        ["Baseline beats naive on margin MAE", f'{g6["mae_margin"]:.3f}',
         f'naive {g6["mae_margin_naive"]:.3f}', gate_mark(g6["mae_margin"] < g6["mae_margin_naive"]),
         g6_src],
    ]
    rows = []
    for s in eng["strategies"]:
        g = s["gates"]
        st = s["stats"]
        rows.append([
            f'<code>{e(s["id"])}</code>', bet_sources(s["bets"], ev),
            f'{st["bets"]}' if st else n2(None),
            gate_mark(g["G1_sample"]), gate_mark(g["G2_positive"]),
            gate_mark(g["G3_significance"]), gate_mark(g["G4_stability"]),
            gate_mark(g["G5_no_lookahead"]), gate_mark(g["G6_baseline"]),
            gate_mark(g["G7_sidak"]),
            gate_mark(g["all_pass"]),
        ])
    body = f"""
<section class="card">
  <h3>The gates</h3>
  {table(["Gate", "Requirement", "Why it exists"], GATE_ROWS,
         caption="Definitions, not data: these are this project's rules, so no external source applies.",
         definitions=True)}

</section>
<section class="card">
  <h3>G6 &mdash; is the line worth testing against?</h3>
  {table(["Check", "Value", "Comparison", "Result", "Official games"], g6rows,
         caption="Measured over the 101 out-of-sample forecasts; each of those games is listed with its "
                 "official game link on the backtest page.")}
  <p class="tn">Straight up {e(g6["straight_up"])} ({pct(g6["straight_up_pct"])}) against a home-team win rate of
  {pct(g6["home_win_rate"])}. Out-of-sample spread &sigma;<sub>margin</sub> = {g6["sigma_margin"]:.2f} points,
  &sigma;<sub>total</sub> = {g6["sigma_total"]:.2f} points.</p>
</section>
<section class="card">
  <h3>Every cell against every gate</h3>
  {table(["Cell", "Official games", "Bets", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "All"], rows)}
  <p class="tn">The null control (S0) fails G2 and G3 at all three triggers, which is the point: a strategy with
  no signal does not get through.</p>
</section>
"""
    return page("Validation gates",
                "Seven conjoined gates. Failing any one blocks promotion regardless of score.",
                body, "pages/gates.html", depth=1)


def build_luck(eng):
    ev = [r["date"] for r in eng["eval_games"]]
    rows = []
    for s in eng["strategies"]:
        st = s["stats"]
        if not st:
            continue
        over = st["roi"] > st["luck_line_roi"]
        rows.append([
            f'<code>{e(s["id"])}</code>', s["name"], bet_sources(s["bets"], ev), st["bets"],
            pct(st["roi"]), pct(st["null_median_roi"]), pct(st["luck_line_roi"]),
            pct(st["skill_est_roi"]),
            signed(st["excess_over_luck_pp"], 1, "pp"),
            pct(st["p_null"], 3),
            pct(st.get("mde_roi")) if st.get("mde_roi") is not None else n2(None),
            badge("above luck line", "ok") if over else badge("inside luck band", "warn"),
        ])
    best = eng["strategies"][0]
    bs = best["stats"]
    body = f"""
<section class="card">
  <h3>Removing luck</h3>
  <p>A bettor taking <em>n</em> even-money bets at a fair price has an ROI distribution centred on zero with a
  spread that shrinks only as 1/&radic;n. At {bs["bets"]} bets that spread is enormous. So instead of asking
  &ldquo;did it win?&rdquo;, this page asks the only question that matters:</p>
  <blockquote>Given this exact bet list, how often would a bettor with no skill at all have done at least this well?</blockquote>
  <p>Every row below answers it with 5,000 Monte-Carlo simulations of a no-skill bettor placing the identical
  bets, at the same prices, in the same order. The 95th percentile of that distribution is the
  <strong>luck line</strong>.</p>
  {table(["Cell", "Strategy", "Official games", "Bets", "Observed ROI", "Null median",
          "Luck line (95th pct)", "Skill estimate", "vs luck line", "p(null)", "Min det. ROI",
          "Verdict"], rows)}
</section>
<section class="card">
  <h3>Worked example: the current leader</h3>
  <p><code>{e(best["id"])}</code> &mdash; {e(best["name"])} went {bs["wins"]}&ndash;{bs["losses"]} on
  {bs["bets"]} bets, an ROI of {pct(bs["roi"])}. Read alone that looks like a winner. Read against its own null it
  does not:</p>
  <ul class="plain">
    <li>A no-skill bettor placing those same {bs["bets"]} bets has a median ROI of {pct(bs["null_median_roi"])}.</li>
    <li>Five per cent of no-skill bettors beat {pct(bs["luck_line_roi"])} ROI purely by chance.</li>
    <li>This strategy returned {pct(bs["roi"])} &mdash; <strong>{signed(bs["excess_over_luck_pp"], 1, " percentage points")} against the luck line</strong>.</li>
    <li>{pct(bs["p_null"] * 100, 1)} of no-skill bettors matched or beat it.</li>
    <li>The smallest true ROI this sample could even detect at 80% power is {pct(bs.get("mde_roi"))}.</li>
  </ul>
  <p>The strategy is not wrong. It is simply unproven, and at {bs["bets"]} bets it could not be otherwise.</p>
</section>
<section class="card">
  <h3>How many games are needed</h3>
  {table(["Signal", "Official games", "Slope", "t", "p", "n now", "n required (80% power)"],
         [[s["label"], date_links(ev), signed(s["slope"], 3), signed(s["t"], 2), f'{s["p"]:.3f}', s["n"],
           (f'{s["n_required"]:,}' if s.get("n_required") and s["n_required"] < 10 ** 6 else "no detectable effect")]
          for s in eng["signal_study"]])}
  <p class="tn">&ldquo;No detectable effect&rdquo; means the estimated slope is so close to zero that no realistic
  amount of data would distinguish it from nothing. That is a result, not a failure.</p>
</section>
"""
    return page("Luck removal and power",
                "Monte-Carlo nulls, luck lines and the sample each signal would need.",
                body, "pages/luck.html", depth=1)


def build_signals(eng):
    games_src = date_links([r["date"] for r in eng["eval_games"]])
    rows = []
    for s in eng["signal_study"]:
        sig = abs(s["slope"]) / s["se"] >= 1.96
        rows.append([
            s["label"], s["n"], games_src, signed(s["slope"], 3), f'{s["se"]:.3f}',
            f'[{s["lo"]:+.3f}, {s["hi"]:+.3f}]',
            signed(s["t"], 2), f'{s["p"]:.4f}',
            f'{s["r2"]:.4f}' if s["r2"] is not None else n2(None),
            (f'{s["n_required"]:,}' if s.get("n_required") and s["n_required"] < 10 ** 6 else "no detectable effect"),
            badge("significant", "ok") if sig else badge("not significant", "warn"),
        ])
    body = f"""
<section class="card">
  <h3>Testing the signal, not the bet record</h3>
  <p>A bet-level test can only use the handful of games that clear a trigger &mdash; on this window that is 6 to 25
  games, far too few to conclude anything. So the signal itself is tested on <strong>every</strong> evaluated game
  instead: regress the model&rsquo;s out-of-sample error on the signal.</p>
  <ul class="plain">
    <li>A slope reliably away from zero means the signal contains information the line missed.</li>
    <li>A slope near zero means it does not, and no amount of extra data will help.</li>
    <li>For the two rows labelled &ldquo;slope 1 = correctly sized&rdquo;, a slope of 1.0 would mean the strategy&rsquo;s
        weights are right as well as real. A slope of 0 means the shift adds nothing; a slope of 2 means it should
        be doubled.</li>
  </ul>
  {table(["Signal &rarr; forecast error", "n", "Official games", "Slope", "SE", "95% CI", "t", "p",
          "R&sup2;", "n required", "Verdict"], rows)}
</section>
<section class="card">
  <h3>Reading</h3>
  <ul class="plain">
    <li><strong>Rest days is the only live candidate.</strong> Each extra day of rest a team holds over its
        opponent is worth {eng["signal_study"][0]["slope"]:+.2f} points of margin in this sample. It is not
        statistically significant (p = {eng["signal_study"][0]["p"]:.3f}) but it is the only signal here that is
        not sitting on zero, and it has a concrete resolution point at about
        {eng["signal_study"][0]["n_required"]} games.</li>
    <li><strong>Back-to-back alone is weaker than it looks.</strong> The raw differential is
        {eng["signal_study"][1]["slope"]:+.2f} points but with p = {eng["signal_study"][1]["p"]:.3f} &mdash; mostly
        because it is a noisier version of the rest variable.</li>
    <li><strong>Schedule density is nothing here.</strong> {eng["signal_study"][2]["slope"]:+.2f} points per extra
        game in four days, p = {eng["signal_study"][2]["p"]:.3f}.</li>
    <li><strong>The totals market shows no fatigue effect at all.</strong> Each team on the second night of a
        back-to-back moves the total by {eng["signal_study"][4]["slope"]:+.3f} points, p =
        {eng["signal_study"][4]["p"]:.3f}. If there is an edge in totals it is not here.</li>
  </ul>
</section>
"""
    return page("Signal study",
                "Does the signal carry information the line missed? Tested on all out-of-sample games.",
                body, "pages/signals.html", depth=1)


def build_teams(eng):
    rows = [[r["abbr"], e(r["name"]), r["gp"], signed(r["rating"], 2), n2(r["off"], 1),
             n2(r["def"], 1), signed(r["off"] - r["def"], 2),
             srclink("https://www.nba.com/standings", "standings")]
            for r in eng["ratings"]]
    sens_src = date_links([r["date"] for r in eng["eval_games"]])
    sens = [[f'{r["k_margin"]}', r["games"], sens_src, n2(r["mae_margin"], 3), n2(r["mae_total"], 3),
             f'{r["brier"]:.4f}', f'{r["su"]}&ndash;{r["games"] - r["su"]}',
             badge("declared", "ok") if r["declared"] else ""]
            for r in eng["shrinkage_sensitivity"]]
    body = f"""
<section class="card">
  <h3>Ratings</h3>
  <p>Two separable models, both fitted on the {eng["meta"]["captured_games"]} official final scores:</p>
  <ul class="plain">
    <li><strong>Rating</strong> &mdash; Simple Rating System: a team&rsquo;s average margin adjusted for the
        ratings of its opponents, shrunk toward zero with {K_MARGIN:.0f} pseudo-games. Drives the spread and the moneyline.</li>
    <li><strong>Offence / defence</strong> &mdash; opponent-adjusted points scored and points allowed, shrunk
        toward the league mean with {K_TOTAL:.0f} pseudo-games. Drives the total.</li>
  </ul>
  <p>These are points-per-game scale, <em>not</em> NBA.com&rsquo;s per-100-possession efficiency: possessions are
  not published on any page reachable here
  (<a href="{BASE_URL}pages/flagged.html#F5">F5</a>).</p>
  {table(["", "Team", "GP", "Rating", "Offence", "Defence", "Net", "Official source"], rows,
         caption="Ratings are computed from the captured final scores; the link in each row is the official "
                 "standings page, the independent record of the same games.")}
  <p class="tn">Home-court advantage estimated from the data: {eng["ratings"][0]["hca"]:.2f} points. League mean
  points per game: {eng["ratings"][0]["league_pts"]:.2f}.</p>
</section>
<section class="card">
  <h3>Shrinkage sensitivity</h3>
  <p>Shrinkage was declared before any run (K = {K_MARGIN:.0f} pseudo-games). This table shows what the walk-forward would have
  produced at other values. It is <em>reported</em>, not used to re-tune: K = 4 turns out to be the best of the
  grid on margin MAE, so the declared value sits on a plateau rather than a cliff edge.</p>
  {table(["K", "Games", "Official games", "Margin MAE", "Total MAE", "Brier", "Straight up", ""], sens)}
</section>
"""
    return page("Team ratings",
                "Ratings fitted on official final scores, with the shrinkage sensitivity that justifies them.",
                body, "pages/teams.html", depth=1)


def build_backtest(eng):
    rows = []
    for r in eng["eval_games"]:
        correct = (r["pred_margin_home"] > 0) == (r["actual_margin_home"] > 0)
        rows.append([
            r["date"], f'{e(r["away"])} @ {e(r["home"])}',
            f'{r["away_pts"]}&ndash;{r["home_pts"]}',
            signed(r["actual_margin_home"], 0),
            signed(r["pred_margin_home"], 1),
            signed(r["resid_margin"], 1),
            n2(r["actual_total"], 0), n2(r["pred_total"], 1), signed(r["resid_total"], 1),
            pct(r["p_home_win"]),
            badge("hit", "ok") if correct else badge("miss", "bad"),
            f'{n2(r["rest_away"])}/{n2(r["rest_home"])}',
            r["train_games"],
            srclink(r["source_url"], "game page"),
        ])
    g6 = eng["g6"]
    body = f"""
<section class="card">
  <h3>Walk-forward design</h3>
  <p>For each date from {eng["meta"]["eval_window"].split(" to ")[0]} onward, the model is refitted from scratch on
  every game <em>strictly before</em> that date, and only then forecasts that date&rsquo;s games. No game can ever
  be forecast using information from itself or from a later date. Games where either team had fewer than three
  games in the training set are skipped.</p>
  <ul class="plain">
    <li>Games evaluated: <strong>{g6["games"]}</strong></li>
    <li>Margin MAE {g6["mae_margin"]:.2f} vs naive {g6["mae_margin_naive"]:.2f}</li>
    <li>Total MAE {g6["mae_total"]:.2f}</li>
    <li>Brier {g6["brier"]:.4f} vs naive {g6["brier_naive"]:.4f}</li>
    <li>Straight up {e(g6["straight_up"])} ({pct(g6["straight_up_pct"])})</li>
    <li>Residual &sigma;: margin {g6["sigma_margin"]:.2f}, total {g6["sigma_total"]:.2f}</li>
  </ul>
</section>
<section class="card">
  <h3>Every forecast</h3>
  {table(["Date", "Matchup", "Final", "Margin", "Pred margin", "Error", "Total", "Pred total", "Error",
          "P(home)", "Winner", "Rest A/H", "Train games", "Official source"], rows)}
</section>
"""
    return page("Walk-forward backtest",
                f'{g6["games"]} out-of-sample forecasts, each fitted only on earlier games.',
                body, "pages/backtest.html", depth=1)


def build_gamelog(eng, raw):
    rows = []
    for g in raw["games"]:
        rows.append([
            g["date"], e(g["away"]), n2(g["away_pts"], 0), e(g["home"]), n2(g["home_pts"], 0),
            ("OT" if g["ot"] else ""), ("neutral" if g.get("neutral") else ""),
            e(g["game_id"]),
            srclink(g["source_url"], "game page"),
        ])
    fx = raw["known_unplayed_by_source"]["fixtures"]
    fxrows = [[f["date"], e(f["away"]), n2(None), e(f["home"]), n2(None), "", "", e(f["game_id"]),
               srclink(f["source_url"], "game page")] for f in fx]
    v = raw["verification"]
    body = f"""
<section class="card">
  <h3>Verification against the official standings</h3>
  <p>{e(v["method"])} {e(v["result"])}</p>
  <p>{e(v["win_residual_note"])}</p>
  <p>Standings source: <a href="{e(v["standings_source_url"])}" target="_blank" rel="noopener">{e(v["standings_source_url"])}</a>,
  captured {e(v["standings_captured_at_utc"])}.</p>
</section>
<section class="card">
  <h3>{len(raw["games"])} verified final scores</h3>
  {table(["Date", "Away", "Pts", "Home", "Pts", "OT", "Neutral", "Game ID", "Official source"], rows)}
  <p class="tn">On nba.com/games the first team listed is the away team and the second is the home team; this is
  confirmed by the game-detail URL pattern <code>/game/&lt;away&gt;-vs-&lt;home&gt;-&lt;id&gt;</code>.</p>
</section>
<section class="card warncard">
  <h3>{len(fx)} games published as fixtures without scores &middot; <a href="{BASE_URL}pages/flagged.html#F1">F1</a></h3>
  <p>{e(raw["known_unplayed_by_source"]["irregularity"])}</p>
  <p>{e(raw["known_unplayed_by_source"]["handling"])}</p>
  {table(["Date", "Away", "Pts", "Home", "Pts", "OT", "Neutral", "Game ID", "Official source"], fxrows)}
</section>
"""
    return page("Official game log",
                "Every official final score in the window, plus the games published without results.",
                body, "pages/gamelog.html", depth=1)


def build_correlations(eng):
    rows = []
    eval_dates = date_links([r["date"] for r in eng["eval_games"]])
    log_dates = date_links([g["date"] for g in load("gamelog.json")["games"]])
    for c in eng["correlations"]["pairs"]:
        basis = c["basis"]
        src = eval_dates if "walk-forward" in basis or "slate" in basis else log_dates
        rows.append([
            e(c["label"]),
            c["n"], src,
            (f'{c["r"]:+.4f}' if c["r"] is not None else "joint probability"),
            (f'[{c["lo"]:+.3f}, {c["hi"]:+.3f}]' if c.get("lo") is not None else n2(None)),
            (f'{c["p"]:.4f}' if c["p"] is not None else n2(None)),
            (f'{c["joint"]:.4f}' if c.get("joint") is not None else n2(None)),
            (f'{c["independent"]:.4f}' if c.get("independent") is not None else n2(None)),
            (signed(c["delta_pp"], 1, "pp") if c.get("delta_pp") is not None else n2(None)),
            e(c["note"]),
            e(c["basis"]),
        ])
    # only pairs that actually overlap: the other 187 pairs are identically zero
    # and would bury the ones that matter
    ov = [[f'<code>{e(o["a"])}</code>', f'<code>{e(o["b"])}</code>', eval_dates, f'{o["shared"]}',
           f'{o["jaccard"]:.3f}', f'{o["a_bets"]}', f'{o["b_bets"]}']
          for o in eng["correlations"]["strategy_overlap"] if o["shared"] > 0]
    j = next((c for c in eng["correlations"]["pairs"] if c.get("joint") is not None), None)
    import math
    se = math.sqrt(0.25 * 0.75 / j["n"]) if j else 0
    z = (j["joint"] - 0.25) / se if se else 0
    body = f"""
<section class="card">
  <h3>Measured correlations</h3>
  <p>Every number here is measured, not assumed. Where a value could not be measured it is left blank rather than
  borrowed from another sport, another season or a textbook.</p>
  {table(["Quantity", "n", "Official games", "r", "95% CI", "p", "Joint", "Independent", "Gap",
          "Why it matters", "Basis"], rows)}
</section>
<section class="card">
  <h3>What this means for parlays</h3>
  <ul class="plain">
    <li><strong>Same-game parlays:</strong> the measured joint probability of the home side covering
        <em>and</em> the game going over is {j["joint"]:.4f} against an independence value of
        {j["independent"]:.4f} &mdash; a gap of {signed(j["delta_pp"], 1, " percentage points")}. On
        {j["n"]} games the standard error of that joint estimate is {se:.4f}, so the gap is
        {abs(z):.2f} standard errors from independence: <strong>not significant</strong>
        (Fréchet bounds for two 0.50 events are [{j["frechet_lo"]:.2f}, {j["frechet_hi"]:.2f}]).
        Price same-game parlays at independence until this resolves.</li>
    <li><strong>Cross-game parlays:</strong> the correlation between cover outcomes of different games on the
        same slate is r = {eng["correlations"]["pairs"][5]["r"]:+.3f} over
        {eng["correlations"]["pairs"][5]["n"]} ordered pairs (p =
        {eng["correlations"]["pairs"][5]["p"]:.2f}). Independence across games is a defensible assumption here.</li>
    <li><strong>Margin and total are close to uncorrelated:</strong> r =
        {eng["correlations"]["pairs"][0]["r"]:+.3f} over {eng["correlations"]["pairs"][0]["n"]} games. A blowout
        does not reliably change the scoring environment in this sample.</li>
  </ul>
</section>
<section class="card">
  <h3>Strategy overlap</h3>
  <p>How often two strategies bet the same game in the same market. High overlap means the strategies are not
  independent discoveries &mdash; and that a portfolio of them is less diversified than the count suggests.
  Only the {len(ov)} pairs that share at least one bet are listed; the remaining pairs are identically zero.</p>
  {table(["Strategy A", "Strategy B", "Official games", "Shared bets", "Jaccard", "Bets A", "Bets B"], ov)}
</section>
"""
    return page("Correlations and parlays",
                "Measured correlation values and what they mean for parlay and SGP pricing.",
                body, "pages/correlations.html", depth=1)


def build_method(eng):
    m = eng["meta"]
    body = f"""
<section class="card">
  <h3>Inputs</h3>
  <p>One input only: the official final scores and schedule published by NBA.com. Every figure on this site
  derives from {m["captured_games"]} verified scores. There is no odds feed, no possession data, no play-by-play
  and no player game log, because none is published by an official source that can be read here.</p>
</section>
<section class="card">
  <h3>The line</h3>
  <ol class="plain">
    <li><strong>Margin.</strong> Simple Rating System: rating = average margin + average opponent rating, solved
        by iteration, shrunk toward zero with 4 pseudo-games. Predicted home margin = rating difference +
        home-court ({eng["ratings"][0]["hca"]:.2f} points, estimated from the data; zero for neutral-site games).</li>
    <li><strong>Total.</strong> Opponent-adjusted points scored and points allowed, solved by iteration, shrunk
        toward the league mean with 6 pseudo-games. Predicted total = home offence + away defence &minus; league
        mean, plus the mirror image, plus the home scoring edge.</li>
    <li><strong>Probability.</strong> Normal CDF around the point prediction with the out-of-sample residual
        standard deviation: {m["sigma_margin"]:.2f} points for margin, {m["sigma_total"]:.2f} for total. These are
        measured out of sample, not in sample. See <a href="{BASE_URL}pages/flagged.html#F10">F10</a> for the one
        caveat.</li>
    <li><strong>Price.</strong> American odds = the reciprocal of the probability. No margin is added &mdash;
        this desk originates lines, it does not make a book.</li>
  </ol>
</section>
<section class="card">
  <h3>How a strategy can beat the line</h3>
  <p>A bettor using the same information as the line cannot beat it, by construction. So each strategy is required
  to add one input the line does not use &mdash; rest days, back-to-back status or schedule density, all read from
  consecutive official schedule dates. Each bet is then struck at the line&rsquo;s own fair price
  (1 / p<sub>baseline</sub>) and settled there. A strategy profits only if its extra input genuinely moves the
  probability in a direction reality confirms.</p>
  <p>Each strategy is run at three trigger levels ({", ".join(str(t) for t in eng["edge_triggers"])} probability
  points) and every cell is published. The trigger is not tuned to the results.</p>
</section>
<section class="card">
  <h3>Luck removal</h3>
  <p>Each cell&rsquo;s ROI is compared against {eng["null_reps"]:,} Monte-Carlo simulations of a no-skill bettor
  placing the identical bet list at the identical prices. Three things come out of it: the null median (the luck
  baseline), the 95th percentile (the luck line), and p<sub>null</sub> (how often pure luck did at least this
  well). A separate power calculation reports the smallest true ROI this sample could detect at all.</p>
  <p>Random seed {20261114}; every figure on this site is reproducible from the repository.</p>
</section>
<section class="card">
  <h3>Reproduce it</h3>
  <pre class="code">python3 -m engine_v2.pipeline      # rebuild every number
python3 -m engine_v2.build_site    # rebuild every page</pre>
</section>
"""
    return page("Method",
                "Exactly how each number is produced, and what each one is allowed to claim.",
                body, "pages/method.html", depth=1)


def build_injuries(ctx):
    cov = ctx["coverage"]
    rows = []
    for ig in ctx["injury_games"]:
        outs = ", ".join(flip(p["player"]) for t in ig["teams"] for p in t["players"]
                         if p["status"] == "Out")
        ns = sum(1 for t in ig["teams"] if t["not_submitted"])
        rows.append([
            ig["date"], ig["game_time_et"], e(ig["matchup"]),
            f'{ig["players_listed"]}',
            f'{ig["counts"].get("Out", 0)} / {ig["counts"].get("Questionable", 0)} / '
            f'{ig["counts"].get("Probable", 0)} / {ig["counts"].get("Available", 0)}',
            f'{ig["players_with_verified_production"]}',
            f'{ig["coverage_pct"]:.0f}%' if ig["coverage_pct"] is not None else n2(None),
            f'{ns}' if ns else n2(None),
            (f'<span class="small">{e(outs)}</span>' if outs else n2(None)),
            srclink(ig["source_url"], "report PDF"),
        ])
    prows = [[e(p["player"]), e(p["team"]), n2(p["gp"], 0), n2(p["min"], 1), n2(p["pts"], 1),
              n2(p["reb"], 1), n2(p["ast"], 1), e(p["leaderboard"]),
              srclink(p["source_url"], "nba.com stats")]
             for p in ctx["player_reference"]]
    body = f"""
<section class="card">
  <h3>Latest official report</h3>
  <p>Source: <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf"
  target="_blank" rel="noopener">NBA Official Injury Report, 11/13/26 07:30 PM edition</a> &mdash; the most recent
  edition published at capture time.
  <a href="https://official.nba.com/nba-injury-report-2026-27-season/" target="_blank" rel="noopener">Index and
  reporting policy</a>.</p>
  <p>{cov["players_in_latest_report"]} players are listed. Of those,
  <strong>{cov["players_with_verified_season_average"]}</strong> have a verified season average in the partial
  official leaderboards available ({cov["minutes_leaderboard_size"]} players by minutes,
  {cov["scoring_leaderboard_size"]} by scoring). The remaining
  {cov["players_in_latest_report"] - cov["players_with_verified_season_average"]} have no published production
  figure, so the production at risk cannot be sized for them and is left blank.</p>
  <p class="warnbox">{e(cov["limit"])}</p>
  {table(["Game date", "Tip (ET)", "Matchup", "Players listed", "Out / Ques / Prob / Avail",
          "With verified production", "Coverage", "Not submitted", "Out players", "Official source"], rows)}
  <p class="tn">&ldquo;Not submitted&rdquo; counts teams the report prints as <code>NOT YET SUBMITTED</code>. That is a
  fact about the source, not an assumption that the team is healthy.</p>
</section>
<section class="card">
  <h3>Rotation impact</h3>
  <p>The question the brief asks &mdash; how an absence changes the rotation and therefore the production &mdash;
  needs two things this project does not have: the absent player&rsquo;s minutes and usage, and the replacement&rsquo;s.
  Neither is published in game-by-game form anywhere reachable here. So:</p>
  <ul class="plain">
    <li>Where a listed player appears in one of the official leaderboards, their verified season minutes and
        points are shown in the player-reference table below.</li>
    <li>Where they do not, the cells are blank and flagged.</li>
    <li><strong>No injury adjustment is applied to any originated line.</strong> Every spread and total on this
        site is computed without it, and is labelled as such.</li>
  </ul>
</section>
<section class="card">
  <h3>Player reference &middot; the only verified player data in the repository</h3>
  <p>Season averages, not game logs. Captured 2026-11-13 by an earlier session from the official NBA.com Stats
  leaderboards; this session could not re-read those tables because they render client-side
  (<a href="{BASE_URL}pages/flagged.html#F4">F4</a>).</p>
  {table(["Player", "Team", "GP", "MIN", "PTS", "REB", "AST", "Leaderboard", "Official source"], prows)}
</section>
"""
    return page("Injuries and rotation",
                "Official participation status, and an explicit statement of what cannot be sized.",
                body, "pages/injuries.html", depth=1)


def build_props(ctx):
    cov = ctx["coverage"]
    body = f"""
<section class="card">
  <h3>Status: blocked, not started</h3>
  <p>Player props are the largest part of the modern betting menu and the entire basis of same-game-parlay demand.
  They are also the one part of this brief that cannot be attempted honestly with the data available.</p>
  <p class="warnbox">{e(cov["limit"])}</p>
</section>
<section class="card">
  <h3>What originating a prop line actually requires</h3>
  <ol class="plain">
    <li><strong>A game-by-game log for that player.</strong> A prop line is a point on a distribution, so the
        distribution is the input. A season average of 27.8 points tells you nothing about the shape &mdash; and the
        shape is what decides whether over 25.5 is a good bet.</li>
    <li><strong>Minutes, with the rotation context.</strong> A player averaging 32 minutes in games he starts is
        a different proposition the night a teammate returns.</li>
    <li><strong>The opponent&rsquo;s scheme and pace.</strong> Rebounds and assists are strongly opponent-dependent.</li>
    <li><strong>Correlations between the legs of a combo.</strong> Points and rebounds for the same player are
        positively correlated; points and assists for two players on the same team often are not. Pricing a combo
        at independence would be wrong, and by how much is exactly what needs measuring.</li>
  </ol>
  <p>None of the four is available from an official source here. Item 4 is partly available for
  <em>team</em> outcomes &mdash; see the <a href="{BASE_URL}pages/correlations.html">correlations page</a> &mdash;
  but not for players.</p>
</section>
<section class="card">
  <h3>What is available</h3>
  <p>Two partial official leaderboards, {cov["minutes_leaderboard_size"]} players by minutes and
  {cov["scoring_leaderboard_size"]} by scoring, listed in full on the
  <a href="{BASE_URL}pages/injuries.html">injuries page</a>. They are enough to size the production at risk for
  {cov["players_with_verified_season_average"]} of the {cov["players_in_latest_report"]} players in the latest
  injury report. They are not enough to originate a single prop line.</p>
</section>
<section class="card">
  <h3>What would unblock it</h3>
  <p>A game-by-game box-score feed. One exists for money; the NBA stats API would also serve if it were reachable
  from this environment, which it is not. Until one is licensed this workstream should be formally closed rather
  than left open &mdash; see <a href="{BASE_URL}pages/questions.html#Q3">Q3</a>.</p>
</section>
"""
    return page("Player props",
                "What is missing, why it is missing, and what it would take to unblock.",
                body, "pages/props.html", depth=1)


def build_gameflow(ctx, eng):
    rows = []
    for g in ctx["slate_flow"]:
        edge = g["rest_edge"]
        tag = ""
        if edge is not None:
            if edge >= 2:
                tag = badge("rest edge home", "ok")
            elif edge <= -2:
                tag = badge("rest edge away", "warn")
        rows.append([
            g["date"], g["time_et"], e(g["matchup"]),
            f'{n2(g["rest_away"])} / {n2(g["rest_home"])}',
            (", ".join(x for x in (("away" if g["b2b_away"] else ""),
                                   ("home" if g["b2b_home"] else "")) if x) or n2(None)),
            f'{g["games_last4_away"]} / {g["games_last4_home"]}',
            f'{n2(g["away_ppg"], 1)} / {n2(g["home_ppg"], 1)}',
            f'{n2(g["away_papg"], 1)} / {n2(g["home_papg"], 1)}',
            n2(g["injury_out"], 0) if g["injury_rows"] else n2(None),
            n2(g["injury_questionable"], 0) if g["injury_rows"] else n2(None),
            n2(g["injury_not_submitted"], 0) if g["injury_rows"] else n2(None),
            tag,
            srclink(g["source_url"], "game page"),
        ])
    frows = []
    for r in ctx["team_form"]:
        frows.append([
            r["team"], e(r["name"]), f'{r["w"]}&ndash;{r["l"]}',
            n2(r["ppg"], 1), n2(r["papg"], 1), signed(r["mov"], 1),
            e(r["home"]), e(r["away"]),
            f'{r["ot_games"]} ({r["ot_pct"]:.0f}%)',
            f'{r["blowout_20"]} ({r["blowout_pct"]:.0f}%)',
            srclink("https://www.nba.com/standings", "standings"),
        ])
    body = f"""
<section class="card">
  <h3>Slate game flow</h3>
  <p>Rest and density are counted from consecutive official schedule dates. The nine 2026-11-13 games that were
  in progress at capture time are included: they are scheduled, so they belong in the rest calculation, even
  though their scores are not yet published. Injury counts are the rows in the latest official report for that
  matchup; where no report exists yet the cells are blank rather than zero.</p>
  {table(["Date", "Tip (ET)", "Matchup", "Rest A/H", "Back-to-back", "Games last 4 A/H",
          "PPG A/H", "PAPG A/H", "Out", "Ques", "Not sub.", "Signal", "Official source"], rows)}
</section>
<section class="card">
  <h3>Team form from the game log</h3>
  <p>Counted directly from the {eng["meta"]["captured_games"]} verified final scores. No adjustment for opponent
  quality is applied here &mdash; that is what the ratings page is for.</p>
  {table(["", "Team", "W&ndash;L", "PPG", "PAPG", "MOV", "Home", "Away", "OT games", "20+ pt games",
          "Official source"], frows)}
</section>
<section class="card">
  <h3>What game-flow analysis cannot say here</h3>
  <p>Genuine game-flow work &mdash; how a team performs when leading or trailing, how a run changes pace, how a
  coach&rsquo;s rotation responds to foul trouble &mdash; needs play-by-play or at least quarter-by-quarter data.
  Neither is published in the pages reachable here. What is above is the honest subset: schedule-derived fatigue,
  and scoring and margin profiles from final scores.</p>
</section>
"""
    return page("Game flow and rest",
                "Schedule-derived fatigue, scoring profiles and the limits of what can be measured.",
                body, "pages/gameflow.html", depth=1)


def build_questions():
    order = {"Blocking": 0, "High": 1, "Medium": 2, "Low": 3}
    qs = sorted(QUESTIONS, key=lambda q: order[q["priority"]])
    rows = [[f'<span class="badge b-{q["priority"].lower()}">{e(q["priority"])}</span>',
             f'<a id="{e(q["id"])}"></a><strong>{e(q["id"])}. {e(q["question"])}</strong>',
             e(q["know"]), e(q["unknown"]), e(q["why"]), e(q["how"]),
             srclink(q["url"], "official source")]
            for q in qs]
    body = f"""
<section class="card">
  <h3>Decisions that cannot be made yet</h3>
  <p>Every row states what is known, what is not, why the gap blocks a decision, and the cheapest way to close it.
  &ldquo;Known&rdquo; is limited to what an official source publishes. Where the answer would require inference the
  row says so instead of offering one.</p>
</section>
<section class="card">
  {table(["", "Question", "What we know", "What we do not know", "Why it blocks a decision",
          "How to find out", "Source"], rows)}
</section>
"""
    return page("Open questions",
                f'{len(QUESTIONS)} decisions blocked by missing information, each with a way to unblock it.',
                body, "pages/questions.html", depth=1)


def build_suggestions():
    order = {"High": 0, "Medium": 1, "Low": 2, "None": 3}
    ss = sorted(SUGGESTIONS, key=lambda s: (order[s["impact"]], s["id"]))
    rows = [[f'<a id="{e(s["id"])}"></a><strong>{e(s["id"])}. {e(s["title"])}</strong>',
             e(s["category"]),
             f'<span class="badge b-{s["impact"].lower()}">{e(s["impact"])}</span> impact',
             f'<span class="badge b-{s["effort"].lower()}">{e(s["effort"])}</span> effort',
             f'<span class="badge b-{s["risk"].lower()}">{e(s["risk"])}</span> risk',
             e(s["unlocks"]), e(s["detail"]),
             f'<strong>Recommendation:</strong> {e(s["recommendation"])}',
             srclink(s["url"], "official source")]
            for s in ss]
    body = f"""
<section class="card">
  <h3>Suggestions, ranked &mdash; none implemented</h3>
  <p>This page exists so that a change is chosen before it is made. Nothing here has been built: the whole point
  is that these are options for someone to review and pick between. Each row states what it unlocks, what it
  costs, what could go wrong, and what the recommendation would be.</p>
</section>
<section class="card">
  {table(["Suggestion", "Area", "Impact", "Effort", "Risk", "Unlocks", "Detail", "Recommendation", "Source"], rows)}
  <p class="tn">Ranked by impact, then effort. The top three are the ones that change what this project can
  conclude; the rest change how well it concludes it.</p>
</section>
"""
    return page("Suggestions",
                f'{len(SUGGESTIONS)} ranked options for improving the site and the decision-making, none implemented.',
                body, "pages/suggestions.html", depth=1)


def build_sources():
    rows = [[f'<code>{e(s["id"])}</code>', e(s["title"]), e(s["publisher"]), e(s["used_for"]),
             e(s["captured"]), srclink(s["url"], s["url"].split("//")[-1])]
            for s in SOURCES]
    body = f"""
<section class="card">
  <h3>Source register</h3>
  <p>Every figure on this site traces to one of these. A value that cannot be traced to one of them is left blank
  and flagged rather than estimated. All hosts are official NBA properties or GitHub.</p>
  {table(["ID", "Source", "Publisher", "What it is used for", "Captured", "Link"], rows)}
</section>
<section class="card">
  <h3>What is deliberately not used</h3>
  <ul class="plain">
    <li><strong>Efficiency numbers from earlier sessions.</strong> They were captured from NBA.com Stats tables
        that render client-side and could not be re-read here, so they could not be re-verified this session.
        Nothing in this build depends on them.</li>
    <li><strong>Any odds source.</strong> None is official.</li>
    <li><strong>Any inferred result.</strong> The {23} games published without scores are listed as fixtures with
        blank scores, even though the standings residual would determine them.</li>
  </ul>
</section>
"""
    return page("Source register",
                "Every official source used, what it is used for, and what was deliberately left out.",
                body, "pages/sources.html", depth=1)


def build_flagged():
    order = {"High": 0, "Medium": 1, "Low": 2}
    fs = sorted(FLAGGED, key=lambda f: order[f["severity"]])
    rows = [[f'<a id="{e(f["id"])}"></a><code>{e(f["id"])}</code>',
             f'<span class="badge b-{f["severity"].lower()}">{e(f["severity"])}</span>',
             e(f["area"]), f'<strong>{e(f["title"])}</strong>', e(f["detail"]), e(f["action"]),
             srclink(f["url"], "official source")]
            for f in fs]
    body = f"""
<section class="card">
  <h3>Flagged for review</h3>
  <p>Things that are wrong, missing, unverifiable or simply too thin to rely on. None of them blocks publication;
  all of them are published here with the source link so they can be reviewed and challenged.</p>
  {table(["ID", "Severity", "Area", "Item", "Detail", "Suggested action", "Source"], rows)}
</section>
"""
    return page("Flagged for review",
                f"{len(FLAGGED)} items that are missing, unverifiable or too thin to rely on.",
                body, "pages/flagged.html", depth=1)


def build_repo_review(review):
    body = f"""
<section class="card">
  <h3>Repository review</h3>
  {review}
</section>
"""
    return page("Repository review",
                "A line-by-line read of the repository at the base commit, with links for manual review.",
                body, "pages/repo-review.html", depth=1)


# --------------------------------------------------------------------------
def main():
    os.makedirs(PAGES, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    eng = json.load(open(os.path.join(DATA, "engine_v2.json"), encoding="utf-8"))
    ctx = eng.get("context")
    if ctx is None:  # back-compat: the context block used to be a separate file
        ctx = json.load(open(os.path.join(DATA, "context.json"), encoding="utf-8"))
    raw = load("gamelog.json")

    review_path = os.path.join(ROOT, "REVIEW_2026-11-14.md")
    review_html = "<p>Not generated.</p>"
    if os.path.exists(review_path):
        md = open(review_path, encoding="utf-8").read()
        review_html = md_to_html(md)

    jobs = {
        "index.html": build_index(eng, ctx),
        "pages/lines.html": build_lines(eng),
        "pages/gameflow.html": build_gameflow(ctx, eng),
        "pages/strategies.html": build_strategies(eng),
        "pages/leaderboard.html": build_leaderboard(eng),
        "pages/gates.html": build_gates(eng),
        "pages/luck.html": build_luck(eng),
        "pages/signals.html": build_signals(eng),
        "pages/teams.html": build_teams(eng),
        "pages/backtest.html": build_backtest(eng),
        "pages/gamelog.html": build_gamelog(eng, raw),
        "pages/correlations.html": build_correlations(eng),
        "pages/method.html": build_method(eng),
        "pages/injuries.html": build_injuries(ctx),
        "pages/props.html": build_props(ctx),
        "pages/questions.html": build_questions(),
        "pages/suggestions.html": build_suggestions(),
        "pages/sources.html": build_sources(),
        "pages/flagged.html": build_flagged(),
        "pages/repo-review.html": build_repo_review(review_html),
    }
    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    with open(os.path.join(ASSETS, "app.js"), "w", encoding="utf-8") as fh:
        fh.write(JS)
    for rel, htmlstr in jobs.items():
        path = os.path.join(SITE, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(htmlstr)
    print("wrote", len(jobs), "pages")


def md_to_html(md: str) -> str:
    """A very small markdown subset renderer - enough for the review document."""
    out, in_list, in_code = [], False, False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append("<pre class=\"code\">" if in_code else "</pre>")
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if not line.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if line.startswith("### "):
            out.append(f"<h4>{html.escape(line[4:])}</h4>")
        elif line.startswith("## "):
            out.append(f"<h3>{html.escape(line[3:])}</h3>")
        elif line.startswith("# "):
            out.append(f"<h2>{html.escape(line[2:])}</h2>")
        elif line.startswith("|"):
            out.append(html.escape(line))
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul class=\"plain\">")
                in_list = True
            out.append(f"<li>{inline(line[2:])}</li>")
        else:
            out.append(f"<p>{inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    txt = "\n".join(out)
    # join consecutive table lines into real tables
    lines = txt.split("\n")
    res, i = [], 0
    while i < len(lines):
        if lines[i].startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            res.append(md_table(block))
        else:
            res.append(lines[i])
            i += 1
    return "\n".join(res)


def md_table(block):
    cells = []
    for ln in block:
        parts = [c.strip() for c in ln.strip().strip("|").split("|")]
        cells.append(parts)
    if len(cells) < 2:
        return html.escape("\n".join(block))
    head, body = cells[0], cells[2:]
    th = "".join(f"<th>{inline(c)}</th>" for c in head)
    tb = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="tablewrap"><table class="tbl" data-sortable><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>'


def inline(s):
    s = html.escape(s)
    s = re_link(s)
    s = re_code(s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return s


import re


def re_code(s):
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def re_link(s):
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)


if __name__ == "__main__":
    main()
