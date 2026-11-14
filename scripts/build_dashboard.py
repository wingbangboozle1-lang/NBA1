#!/usr/bin/env python3
"""build_dashboard.py — generate the unified NBA1 site.

Writes:
  index.html            the landing page (repository root, this is what GitHub Pages serves)
  site/pages/*.html     one page per category
  site/assets/*         the stylesheet and the small script
  site/data/*.json      the exact JSON each page was built from

Every published table row carries a link to the official source it came from.
A value that could not be confirmed from an official source is rendered as an em dash,
marked "not published", and is listed on the Flagged for Review page. Nothing is inferred.

Run:  python3 scripts/build_dashboard.py
"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs", "data")
CONTENT = os.path.join(ROOT, "data", "content")
RAW = os.path.join(ROOT, "data", "raw")
SITE = os.path.join(ROOT, "site")
PAGES = os.path.join(SITE, "pages")
ASSETS = os.path.join(SITE, "assets")
SITE_DATA = os.path.join(SITE, "data")

NA = '<span class="na" title="not published - no official source confirmed this value">&mdash;</span>'


# ----------------------------------------------------------------- tiny helpers
def esc(v):
    if v is None:
        return NA
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return ("%.4g" % v)
    s = str(v)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def num(v, dp=1):
    """Format a number or render the unverified marker."""
    if v is None or v == "":
        return NA
    try:
        return ("%." + str(dp) + "f") % float(v)
    except (TypeError, ValueError):
        return esc(v)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------- navigation
# (label, filename under site/pages, blurb)
CATEGORIES = [
    ("HORIZON", None, "The next three days of NBA games and the lines we originate for them."),
    ("Lines &amp; Picks", "picks.html", "Originated spread, total and fair-moneyline for every game in the horizon, and the gated paper picks built on them."),
    ("Player Props", "props.html", "Per-player projections and prop combinations, with the minutes coverage stated next to every number."),
    ("Injuries &amp; Rotation", "injuries.html", "The official injury report, the rotation minutes it implies, and the measured production impact."),
    ("Game Flow", "gameflow.html", "Pace, expected margin and total, blow-out and overtime probability, and the rest and back-to-back context."),
    ("EVIDENCE", None, "Whether any of it is skill. The out-of-sample record, the gates, the correlations and the luck check."),
    ("Strategies &amp; Leaderboard", "strategies.html", "Ten strategies, the reward tiers, and the leaderboard that ranks them - with nothing promoted that has not passed."),
    ("Validation Gates", "validation.html", "The seven gates every strategy must clear, the definition of each, and how each strategy scored."),
    ("Correlations", "correlations.html", "Measured correlations, model-derived ones and the same-game-parlay rho used for pricing."),
    ("Luck &amp; Skill", "luck.html", "How many wins each team probably should have had, and which of them are luck."),
    ("Out-of-Sample Backtest", "backtest.html", "The 51-game test window and everything measured on it."),
    ("Model &amp; Teams", "model.html", "The efficiency model, its assumptions and the team ratings it reads."),
    ("DECISION", None, "What is still open, what could be improved, and what could not be verified."),
    ("Open Questions", "questions.html", "What we know, what we do not, and the concrete step that would answer each open item."),
    ("Suggestions", "suggestions.html", "Improvements written as options with effort, risk and what each unlocks, so a reviewer can pick a path."),
    ("Flagged for Review", "flagged.html", "Every value that could not be confirmed from an official source, with the link it would need."),
    ("Source Register", "sources.html", "Every official URL this site is built from."),
    ("Repo Review", "repo-review.html", "Line-by-line review of the repository, the irregularities found, and the verification log."),
]

NAV_SECTIONS = []
_sec = None
for _label, _file, _blurb in CATEGORIES:
    if _file is None:
        _sec = (_label, [])
        NAV_SECTIONS.append(_sec)
    else:
        _sec[1].append((_label, _file, _blurb))


def paths(depth):
    """Relative prefixes, so every generated link resolves from the page's own folder."""
    if depth == 0:
        return {"root": "", "css": "site/assets/site.css", "js": "site/assets/site.js",
                "home": "index.html", "navbase": "site/pages/"}
    return {"root": "../../", "css": "../assets/site.css", "js": "../assets/site.js",
            "home": "../../index.html", "navbase": ""}


def nav_html(pth):
    out = []
    for label, items in NAV_SECTIONS:
        out.append('<div class="nav-group"><h3>%s</h3>' % label)
        for lbl, fn, _ in items:
            out.append('<a href="%s%s">%s</a>' % (pth["navbase"], fn, lbl))
        out.append("</div>")
    return "\n".join(out)


def page(title, sub, body, depth=1, extra_head=""):
    pth = paths(depth)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s &middot; NBA1</title>
<link rel="stylesheet" href="%(css)s">
%(head)s
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <div class="wrap topbar-in">
    <a class="brand" href="%(home)s">
      <span class="mark">NBA1</span>
      <span class="brand-txt">Originated lines &amp; strategy lab</span>
    </a>
    <nav class="topnav">
      <a href="%(navbase)spicks.html">Horizon</a>
      <a href="%(navbase)sstrategies.html">Evidence</a>
      <a href="%(navbase)ssuggestions.html">Decision</a>
      <a href="%(navbase)sflagged.html">Flagged</a>
    </nav>
  </div>
</header>
<div class="wrap layout">
  <aside class="sidebar">
    <div class="side-h">Sections</div>
    %(nav)s
    <div class="side-note">
      <strong>Reading rule.</strong> Every table row links to the official source it
      came from. A blank cell means the value could not be confirmed from an official
      source &mdash; it is never filled in by guesswork. See
      <a href="%(navbase)sflagged.html">Flagged for Review</a>.
    </div>
  </aside>
  <main id="main">
    <div class="page-head">
      <h1>%(title)s</h1>
      <p class="sub">%(sub)s</p>
    </div>
    %(body)s
    <footer class="foot">
      <p>NBA1 &mdash; a research workspace for originating NBA lines and testing whether the
      signal is skill or luck. Nothing on this site is a betting recommendation, and no
      market price is used anywhere: every "edge" is against a naive model that stands in
      for the market, because no official NBA-operated price feed exists.</p>
      <p class="foot-l">Generated by <code>scripts/build_dashboard.py</code> from
      <code>docs/data/*.json</code>. Sources: <a href="%(navbase)ssources.html">source register</a>.</p>
    </footer>
  </main>
</div>
<script src="%(js)s"></script>
</body>
</html>
""" % {"title": title, "sub": sub, "body": body, "nav": nav_html(pth),
       "css": pth["css"], "js": pth["js"], "home": pth["home"], "head": extra_head,
       "navbase": pth["navbase"]}


# --------------------------------------------------------------- table renderer
def table(headers, rows, note=None, source_col="Source", cls="", table_id=None, src_header=None):
    """rows: list of lists. A cell may be a raw HTML string (already escaped) or a value."""
    out = ['<div class="tablewrap">', '<table class="tbl %s"' % cls]
    if table_id:
        out.append(' id="%s"' % table_id)
    out.append(">")
    out.append("<thead><tr>")
    hs = list(headers)
    if hs and hs[-1] == source_col:
        hs = hs[:-1]                       # the source column is added by this function
    for h in hs:
        out.append("<th>%s</th>" % h)
    if source_col:
        out.append('<th class="src">%s</th>' % (src_header or source_col))
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        cells = r[:-1] if source_col else r
        for c in cells:
            out.append("<td>%s</td>" % c)
        if source_col:
            out.append('<td class="src">%s</td>' % (r[-1] if r else ""))
        out.append("</tr>")
    out.append("</tbody></table></div>")
    if note:
        out.append('<p class="tnote">%s</p>' % note)
    return "\n".join(out)


def srclink(sources, sid):
    """Render a link to the official source id. Unknown ids render as a marked blank."""
    if not sid:
        return '<span class="na" title="no source id on this row">&mdash;</span>'
    s = sources.get(sid)
    if not s:
        return '<span class="na" title="source id %s is not in the register">&mdash;</span>' % esc(sid)
    return ('<a href="%s" target="_blank" rel="noopener">%s</a>'
            % (esc(s["url"]), esc(sid)))


def srclink_url(url, label):
    if not url:
        return '<span class="na" title="no official source">&mdash;</span>'
    return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(url), esc(label))


def nomark(reason):
    """An explicit 'there is no official source for this' marker."""
    return '<span class="na" title="%s">&mdash;</span>' % esc(reason)


def card(title, body, cls=""):
    return ('<section class="card %s"><h2>%s</h2>%s</section>' % (cls, title, body))


def tiles(items):
    out = ['<div class="tiles">']
    for label, value, sub in items:
        out.append('<div class="tile"><div class="tile-v">%s</div>'
                   '<div class="tile-l">%s</div><div class="tile-s">%s</div></div>'
                   % (value, label, sub))
    out.append("</div>")
    return "\n".join(out)


def banner(kind, title, body):
    return ('<div class="banner %s"><div class="b-t">%s</div><div class="b-b">%s</div></div>'
            % (kind, title, body))


def h2(title, sub=""):
    return '<h2 class="sec">%s</h2>%s' % (title, ('<p class="secsub">%s</p>' % sub) if sub else "")


# ------------------------------------------------------------------------- main
def main():
    sources = load(os.path.join(RAW, "sources.json"))["sources"]
    src_reg = load(os.path.join(RAW, "sources.json"))
    meta = load(os.path.join(DATA, "meta.json"))
    lines = load(os.path.join(DATA, "lines.json"))["rows"]
    picks = load(os.path.join(DATA, "picks.json"))
    props = load(os.path.join(DATA, "props.json"))["rows"]
    injs = load(os.path.join(DATA, "injuries.json"))
    flow = load(os.path.join(DATA, "gameflow.json"))["rows"]
    back = load(os.path.join(DATA, "backtest.json"))
    val = load(os.path.join(DATA, "validation.json"))
    corr = load(os.path.join(DATA, "correlations.json"))
    luck = load(os.path.join(DATA, "luck.json"))
    lb = load(os.path.join(DATA, "leaderboard.json"))
    teams = load(os.path.join(DATA, "teams.json"))
    execu = load(os.path.join(CONTENT, "executive.json"))
    flagged = load(os.path.join(CONTENT, "flagged.json"))
    questions = load(os.path.join(CONTENT, "questions.json"))
    suggestions = load(os.path.join(CONTENT, "suggestions.json"))

    for d in (SITE, PAGES, ASSETS, SITE_DATA):
        os.makedirs(d, exist_ok=True)

    # ------------------------------------------------------------------ pages
    built = {}

    # === index.html (landing) =============================================
    horizon = sorted({r["date"] for r in lines})
    n_games = len(lines)
    n_picks = len(picks["rows"])
    n_flags = len(flagged["items"])
    body = []
    body.append(tiles([
        ("Games in horizon", n_games, "14&ndash;17 Nov 2026 (today + 3 days)"),
        ("Originated lines", n_games, "spread, total and fair moneyline per game"),
        ("Paper picks", n_picks, "gated; none is market-validated"),
        ("Strategies tested", len(lb["rows"]), "%d capped at a quarter unit &middot; %d research-only"
         % (sum(1 for r in lb["rows"] if "Not funded" not in r["tier"]),
            sum(1 for r in lb["rows"] if "Not funded" in r["tier"]))),
        ("Out-of-sample games", back["metrics"]["n_games"], "every one predicted out of sample"),
        ("Open flags", n_flags, "published, non-blocking"),
    ]))

    body.append(banner("warn", "What this site is, and what it is not",
                       "<p>This is an <strong>origination and research</strong> workspace. It produces its own "
                       "lines from official NBA data and then tries hard to prove that those lines carry skill. "
                       "As of this build <strong>no strategy has cleared the skill gate</strong>: the best one is "
                       "%s at %s, which is inside what luck alone produces. Every strategy is therefore capped at a "
                       "quarter unit or held back as research-only, and that is the result, not an obstacle to be "
                       "worked around.</p>"
                       "<p>No sportsbook price is used anywhere, because no NBA-operated source publishes one. "
                       "&ldquo;Edge&rdquo; on this site means <em>the model against a deliberately naive reference "
                       "model built from the same official ratings</em>. It does not mean an edge against a book.</p>"
                       % (esc(lb["rows"][0]["record"]), esc(lb["rows"][0]["tier"]))))

    body.append(card("Executive summary", (
        '<p class="lead">%s</p><p>%s</p>'
        '<div class="verdict"><div class="v-t">Verdict &mdash; %s</div><div class="v-b">%s</div>'
        '<div class="v-w"><strong>Why:</strong> %s</div></div>'
        '<ol class="findings">%s</ol>'
        % (esc(execu["headline"]), esc(execu["lead"]),
           esc(execu["verdict"]["status"]), esc(execu["verdict"]["one_line"]), esc(execu["verdict"]["why"]),
           "".join('<li><b>%s</b> &mdash; %s<br><span class="fine">%s</span></li>'
                   % (esc(f["title"]), esc(f["detail"]), esc(f["reading"]))
                   for f in execu["findings"]))
    ), "exec"))

    # horizon at a glance
    glance = []
    for r in lines:
        glance.append([
            esc(r["date"]), esc(r["time_et"]), '<b>%s</b>' % esc(r["matchup"]),
            esc(r["away_rec"]), esc(r["home_rec"]),
            num(r["model_spread_home"]), num(r["model_total"]),
            ("%+.2f" % r["spread_edge"]) if r["spread_edge"] is not None else NA,
            ("%+.2f" % r["total_edge"]) if r["total_edge"] is not None else NA,
            num(r["p_home_win"], 3),
            ("B2B" if (r["home_b2b"] or r["away_b2b"]) else ""),
            srclink(sources, r["src"]),
        ])
    body.append(h2("Horizon at a glance", "Every game in the window, with the originated line, the reference line and the difference between them."))
    body.append(table(
        ["Date", "Tip ET", "Matchup", "Away rec", "Home rec", "Model spread", "Model total",
         "Spread edge", "Total edge", "P(home)", "Rest", "Source"],
        glance,
        note="Spread and total are the originated lines (model). Edge is the model minus the naive reference line "
             "built from the same official ratings; positive spread edge means the model likes the home side more "
             "than the reference does. Rest flags a back-to-back. Every row links to the official NBA.com game page."))

    # category grid
    grid = []
    for label, fn, blurb in CATEGORIES:
        if fn is None:
            continue
        grid.append('<a class="cardlink" href="site/pages/%s"><span class="cl-t">%s</span>'
                    '<span class="cl-b">%s</span></a>' % (fn, label, blurb))
    body.append(h2("Browse by category"))
    body.append('<div class="linkgrid">%s</div>' % "".join(grid))

    body.append(card("Earlier builds (kept, not deleted)",
                     '<p>Two earlier implementations of the same brief live in this repository. They are preserved '
                     'and remain online so the audit trail stays intact; the pages above are the current build.</p>'
                     '<ul class="plain">'
                     '<li><a href="docs/index.html">Dated NBA data snapshot</a> &mdash; a frozen 13&ndash;15 Nov '
                     'schedule and 12:00 PM injury-report transcription with every source link.</li>'
                     '<li><a href="docs/b/index.html">Line Origination Desk</a> &mdash; the earlier backtested '
                     'build (51 out-of-sample games, ten strategies, seven gates).</li>'
                     '<li><a href="schedule-verified.html">Verified schedule 14&ndash;17 Nov</a> &mdash; the '
                     'row-by-row schedule check and its flagged items.</li>'
                     '<li><a href="verification.html">Live verification</a> &mdash; the official-source '
                     'reachability probe and the integration checks from session '
                     '<code>arena/2509073f-nba1</code>.</li>'
                     '<li><a href="review.html">Flagged items (earlier build)</a> and '
                     '<a href="sources.html">source register (earlier build)</a>.</li>'
                     '</ul>'))

    landing = page("NBA1 &mdash; NBA line origination and strategy lab",
                    "Originated lines, validation gates, measured correlations and a luck check for every NBA "
                    "game in the next three days. Every row links to the official source it came from.",
                    "\n".join(body), depth=0)
    built["index.html"] = landing

    # === picks =============================================================
    b = [h2("Originated lines for every game in the horizon",
            "Spread, total and fair moneyline originated from official team ratings, shown against the naive "
            "reference line the model has to beat.")]
    rows = []
    for r in lines:
        rows.append([
            esc(r["date"]), esc(r["time_et"]), '<b>%s</b>' % esc(r["matchup"]),
            esc(r["away_rec"]), esc(r["home_rec"]), esc(r.get("venue")),
            num(r["ref_spread_home"]), num(r["model_spread_home"]),
            ("%+.2f" % r["spread_edge"]) if r["spread_edge"] is not None else NA,
            num(r["ref_total"]), num(r["model_total"]),
            ("%+.2f" % r["total_edge"]) if r["total_edge"] is not None else NA,
            num(r["p_home_win"], 3),
            esc(r["ml_home_fair"]) if r["ml_home_fair"] is not None else NA,
            esc(r["ml_away_fair"]) if r["ml_away_fair"] is not None else NA,
            ("H " + num(r["home_rest_days"], 0) + " / A " + num(r["away_rest_days"], 0))
            if (r["home_rest_days"] is not None or r["away_rest_days"] is not None) else NA,
            esc(r["home_report_status"]), esc(r["away_report_status"]),
            srclink(sources, r["src"]),
        ])
    b.append(table(
        ["Date", "Tip ET", "Matchup", "Away", "Home", "Venue", "Ref spread", "Model spread",
         "Spread edge", "Ref total", "Model total", "Total edge", "P(home)", "Fair ML home",
         "Fair ML away", "Rest days H/A", "Home injury status", "Away injury status", "Source"],
        rows,
        note="A negative spread means the home team is favoured. Fair moneyline is the model's own break-even "
             "price (no market price is used). Rest days: number of days since that team's previous game, taken "
             "from the official schedule; a blank means the team's previous game falls outside the captured "
             "window. Injury status is the official report read-out for that team on that date."))

    b.append(h2("Paper picks", "Every play the strategy library produced for the horizon, with its gate status."))
    prows = []
    for r in picks["rows"]:
        prows.append([
            esc(r["date"]), '<b>%s</b>' % esc(r["matchup"]), esc(r["strategy"]),
            esc(r["market"]), esc(r["side"]), esc(r["line_display"]),
            num(r["model_value"]), num(r["ref_line"]),
            ("%+.2f" % r["edge"]) if r["edge"] is not None else NA,
            num(r["p_model"], 3), str(r["n_legs"]), esc(r["status"]),
            srclink(sources, "S1"),
        ])
    b.append(table(
        ["Date", "Matchup", "Strategy", "Market", "Side", "Line", "Model value", "Ref line",
         "Edge", "P(model)", "Legs", "Status", "Source"],
        prows,
        note="Status is PENDING for every row: these games have not been played yet, so no result exists and "
             "none is written. A settled record and ROI column stays blank until an official final score exists."))

    b.append(card("How a pick becomes a pick",
                   "<p>Each strategy is a rule over the originated lines. A play is only published when the "
                   "strategy's own rule fires; a strategy that has not cleared the sample and skill gates is "
                   "capped at a quarter unit or held back as research-only, and that cap is shown on the "
                   "leaderboard. <strong>No pick here is market-validated</strong>, because no official price "
                   "feed exists; a win would mean the model beat a naive model, not that it beat a book.</p>"))
    built["picks.html"] = page("Lines &amp; picks",
                                "Originated spread, total and moneyline for all %d games in the horizon, and the "
                                "gated paper picks built on them." % n_games, "\n".join(b))

    # === props =============================================================
    b = [h2("Player projections", "Per-player points, rebounds, assists, threes and PRA, projected from official season averages adjusted for pace, opponent and availability.")]
    prows = []
    for r in props:
        prows.append([
            esc(r["date"]), '<b>%s</b>' % esc(r["matchup"]), esc(r["player"]), esc(r["team"]),
            esc(r["opponent"]), num(r["season_min"]), num(r["baseline_pts"]), num(r["proj_pts"]),
            num(r["delta_pts"]), num(r["baseline_reb"]), num(r["proj_reb"]),
            num(r["baseline_ast"]), num(r["proj_ast"]),
            num(r["baseline_fg3m"]), num(r["proj_fg3m"]),
            num(r["baseline_pts_reb_ast"]), num(r["proj_pts_reb_ast"]),
            srclink(sources, r["src_baseline"]),
        ])
    b.append(table(
        ["Date", "Matchup", "Player", "Team", "Opp", "Season min", "Base PTS", "Proj PTS",
         "&Delta;PTS", "Base REB", "Proj REB", "Base AST", "Proj AST", "Base 3PM", "Proj 3PM",
         "Base PRA", "Proj PRA", "Source"],
        prows,
        note="Season min is the player's official minutes per game from the captured Players Traditional table; "
             "it is blank for any player outside that table. Delta columns are the projection minus the season "
             "average. A PRA combination line is the sum of the projected points, rebounds and assists."))
    b.append(banner("warn", "Coverage limit, stated next to the numbers",
                     "The official Players Traditional table publishes 465 rows across ten pages and only page 1 "
                     "(the 50 highest scorers) is present in the page source a plain fetch can read. "
                     "<strong>Minutes are known for those players only.</strong> Players outside that page carry a "
                     "blank minutes value and a projection of zero impact rather than an estimate. See "
                     "<a href=\"flagged.html\">Flagged for Review</a>."))
    built["props.html"] = page("Player props",
                                "Player-level lines and projection combinations for the horizon, with the "
                                "minutes coverage stated on every page.", "\n".join(b))

    # === injuries ==========================================================
    b = [h2("Injury report read-out", "One row per official injury-report line, with the minutes it implies and the impact it carries.")]
    rows = []
    for r in injs["rows"]:
        rows.append([
            esc(r["date"]), esc(r["matchup"]), esc(r["team"]), esc(r["side"]),
            esc(r.get("player")), esc(r["status"]), esc(r.get("reason")),
            esc(r.get("status_weight")) if r.get("status_weight") is not None else NA,
            num(r.get("season_min")), num(r.get("minutes_share"), 3),
            num(r.get("team_weighted_lost_share"), 3),
            num(r.get("team_impact_net_rating"), 2),
            esc(r.get("confidence")),
            srclink(sources, r.get("src")),
        ])
    b.append(table(
        ["Date", "Matchup", "Team", "Side", "Player", "Status", "Reason", "Status weight",
         "Season min", "Min share", "Team lost share", "Impact (net rtg)", "Confidence", "Source"],
        rows,
        note="Season min and min share are blank when the player is outside the captured minutes table. "
             "Team lost share and the impact figure are a measured LOWER BOUND: only players with known minutes "
             "can contribute. Confidence is the engine's own statement of how much of the rotation the report "
             "covers."))
    b.append(banner("info", "Report edition in use",
                     "%s. Source: %s. Rows for a team that had not filed at this edition are recorded with status "
                     "<em>NOT YET SUBMITTED</em> exactly as published; they are never filled in."
                     % (esc(injs["report"]), srclink(sources, injs["src"]))))
    built["injuries.html"] = page("Injuries, rotation and production impact",
                                  "The official injury report for the horizon, what it does to rotation minutes, "
                                  "and the measured effect on a team's net rating.", "\n".join(b))

    # === gameflow ==========================================================
    b = [h2("Game flow", "Pace, expected margin and total, and the shape of the game that follows from them.")]
    rows = []
    for r in flow:
        rows.append([
            esc(r["date"]), esc(r["time_et"]), '<b>%s</b>' % esc(r["matchup"]),
            esc(r["away_rec"]), esc(r["home_rec"]),
            num(r["possessions"]), num(r["pace_vs_league"]),
            num(r["expected_total"]), num(r["expected_margin_home"]),
            num(r["p_home_win"], 3), num(r["p_margin_within_5"], 3),
            num(r["p_margin_20plus"], 3), num(r["p_overtime_approx"], 4),
            ("H " + num(r["home_rest_days"], 0) + "d / A " + num(r["away_rest_days"], 0) + "d")
            if (r["home_rest_days"] is not None or r["away_rest_days"] is not None) else NA,
            ("B2B" if (r["home_b2b"] or r["away_b2b"]) else "-"),
            srclink(sources, r.get("src")),
        ])
    b.append(table(
        ["Date", "Tip ET", "Matchup", "Away", "Home", "Possessions", "Pace vs lg",
         "Exp total", "Exp margin (home)", "P(home win)", "P(margin &le;5)", "P(margin &ge;20)",
         "P(OT)", "Rest", "B2B", "Source"],
        rows,
        note="Expected margin is from the home team's point of view: positive means the home team is favoured. "
             "P(margin &le;5) is the probability the game is decided by five points or fewer; P(margin &ge;20) is "
             "the probability of a twenty-point blow-out; P(OT) is the model's overtime probability. These come "
             "from official pace and efficiency inputs plus the fitted outcome spread &mdash; no play-by-play "
             "input exists, so no run, timeout or quarter-split metric is published."))
    built["gameflow.html"] = page("Game flow analysis",
                                  "Pace, expected score, blow-out and overtime probability, and the rest and "
                                  "back-to-back context for every game in the horizon.", "\n".join(b))

    # === strategies =========================================================
    b = [h2("Leaderboard", "Ranked by the reward score. The tier is capped by the gates, not by the score: a strategy that fails the skill gate cannot be promoted past a quarter unit however high it scores.")]
    rows = []
    for r in lb["rows"]:
        rows.append([
            str(r["rank"]), '<b>%s</b>' % esc(r["id"]), esc(r["name"]), esc(r["family"]),
            str(r["n_graded"]), esc(r["record"]),
            num(r["units"], 2), num(r["lbs"], 1), esc(r["tier"]), esc(r.get("tier_note")),
            srclink(sources, "S1"),
        ])
    b.append(table(
        ["#", "ID", "Strategy", "Family", "Graded", "Record", "Units", "Score", "Tier", "Cap note", "Source"],
        rows,
        note="Units assume the standard -110 price, which is a disclosed convention, not an observed price: no "
             "sportsbook price was observable anywhere in this environment. A blank or 0 record means the "
             "strategy has no graded plays, never a loss."))
    b.append(h2("Reward tiers", "What a strategy earns once it clears the gates it must clear."))
    rows = []
    for t in lb["tiers"]:
        rows.append([esc(t.get("tier")), esc(t.get("name")), esc(t.get("rule")),
                     esc(t.get("min_score")), srclink(sources, "S1")])
    b.append(table(["Tier", "Name", "Rule", "Minimum score", "Source"], rows))
    b.append(h2("The strategy library", "What each strategy actually is, and why it was written."))
    rows = []
    for s in val["strategies"]:
        rows.append([esc(s["id"]), '<b>%s</b>' % esc(s["name"]), esc(s["family"]), esc(s["market"]),
                     esc(s.get("rule")), esc(s.get("threshold")), esc(s.get("why")),
                     esc(s.get("ungraded_reason")) if s.get("ungraded_reason") else NA,
                     srclink(sources, "S1")])
    b.append(table(["ID", "Name", "Family", "Market", "Rule", "Threshold", "Why", "Ungraded reason", "Source"], rows))
    built["strategies.html"] = page("Strategies and leaderboard",
                                    "Ten strategies, the reward tiers they earn, and the leaderboard that ranks "
                                    "them &mdash; with nothing promoted that has not cleared every gate.",
                                    "\n".join(b))

    # === validation =========================================================
    b = [h2("The seven gates", "Every strategy must clear all seven. A gate that has not been run is recorded as NOT RUN, never as a pass.")]
    rows = []
    for g in val["gate_definitions"]:
        rows.append([esc(g["id"]), '<b>%s</b>' % esc(g["name"]), esc(g["definition"]), srclink(sources, "S1")])
    b.append(table(["ID", "Gate", "Definition", "Source"], rows))

    b.append(h2("Gate matrix", "Each strategy against each gate. This is the table that decides what gets funded."))
    headers = ["ID", "Strategy"] + [g["id"] for g in val["gate_definitions"]]
    rows = []
    for s in val["strategies"]:
        r = [esc(s["id"]), esc(s["name"])]
        for g in s["gates"]:
            cls = {"PASS": "gp", "FAIL": "gf", "PROVISIONAL": "gprov", "N/A": "gna",
                   "NOT RUN": "gnr"}.get(g["status"], "")
            r.append('<span class="g %s">%s</span>' % (cls, esc(g["status"])))
        r.append(srclink(sources, "S1"))
        rows.append(r)
    b.append(table(headers, rows,
                   note="Hover a gate cell for the reason it was given. PASS = green, FAIL = red, "
                        "PROVISIONAL = amber (passed, but the sample is too small to rely on), "
                        "N/A = not applicable to this strategy, NOT RUN = could not be evaluated."))

    b.append(h2("Measured on the out-of-sample window", "The model against the naive reference, on 51 games played after the ratings cut-off."))
    m = back["metrics"]
    rows = [
        ["Games in the window", str(m["n_games"]), esc(m["window"]), esc(m["ratings_window"]), srclink(sources, "S1")],
        ["Margin MAE", num(m["mae_margin_model"], 2), num(m["mae_margin_ref"], 2),
         ("model better" if m["mae_margin_model"] < m["mae_margin_ref"] else "reference better"), srclink(sources, "S1")],
        ["Margin RMSE", num(m["rmse_margin_model"], 2), num(m["rmse_margin_ref"], 2),
         ("model better" if m["rmse_margin_model"] < m["rmse_margin_ref"] else "reference better"), srclink(sources, "S1")],
        ["Total MAE", num(m["mae_total_model"], 2), num(m["mae_total_ref"], 2),
         ("model better" if m["mae_total_model"] < m["mae_total_ref"] else "reference better"), srclink(sources, "S1")],
        ["Total RMSE", num(m["rmse_total_model"], 2), num(m["rmse_total_ref"], 2),
         ("model better" if m["rmse_total_model"] < m["rmse_total_ref"] else "reference better"), srclink(sources, "S1")],
        ["Brier score", num(m["brier_model"], 4), num(m["brier_ref"], 4),
         ("model better" if m["brier_model"] < m["brier_ref"] else "reference better"), srclink(sources, "S1")],
        ["Log loss", num(m["logloss_model"], 4), num(m["logloss_ref"], 4),
         ("model better" if m["logloss_model"] < m["logloss_ref"] else "reference better"), srclink(sources, "S1")],
        ["Straight up", esc(m["straight_up_model"]), esc(m["straight_up_ref"]), esc(m.get("straight_up_note", "")), srclink(sources, "S1")],
        ["Residual sigma (margin / total)", num(m["sigma_margin"], 2) + " / " + num(m["sigma_total"], 2), NA, NA, srclink(sources, "S1")],
    ]
    b.append(table(["Metric", "Model", "Reference", "Reading", "Source"], rows))
    built["validation.html"] = page("Validation gates",
                                    "The seven gates every strategy must clear, how each strategy scored, and the "
                                    "out-of-sample metrics the gates are read against.", "\n".join(b))

    # === correlations =======================================================
    b = [h2("Measured correlations", "Computed across the 30-team official cross-section. The p-value is reported so a marginal result can be judged.")]
    rows = []
    for c in corr["measured"]:
        rows.append([esc(c["x"]), esc(c["y"]), num(c["r"], 3), num(c.get("r_squared"), 3),
                     num(c.get("p_value"), 4), str(c.get("n")), esc(c.get("why")),
                     esc(c.get("status")), srclink(sources, "S1")])
    b.append(table(["X", "Y", "r", "r&sup2;", "p (two-sided)", "n", "What it answers", "Status", "Source"], rows,
                   note="A p-value of 0.0000 means below the reporting precision, not exactly zero. With 13 pairs "
                        "tested, roughly 0.65 false positives are expected by chance alone at a 5% level, so no "
                        "single marginal result here is treated as independently confirmed."))
    b.append(h2("Model-derived correlations", "Not measured on data. These are structural values the model assumes, and they are priced with them."))
    rows = []
    for c in corr.get("model_derived", []):
        rows.append([esc(c.get("x")), esc(c.get("y")), num(c.get("rho"), 3),
                     esc(c.get("why")), esc(c.get("status")),
                     srclink(sources, "S1")])
    b.append(table(["X", "Y", "rho", "Why it matters", "Status", "Source"], rows))
    b.append(h2("Same-game-parlay rho", "The correlation values used to price a two-leg same-game parlay."))
    rows = []
    for k, v in corr.get("sgp_rho", {}).items():
        rows.append([esc(k.replace("_", " ")), num(v, 2), srclink(sources, "S1")])
    b.append(table(["Leg pair", "rho", "Source"], rows))
    b.append(h2("Parlay pricing grid", "Joint probability against a supplied margin of safety, so a parlay can be priced rather than guessed."))
    grid = corr.get("parlay_pricing_grid", [])
    if grid:
        rows = []
        for r in grid:
            rows.append([num(r.get("leg_prob"), 3), num(r.get("rho"), 2),
                         num(r.get("true_joint_prob"), 4), num(r.get("independent_product"), 4),
                         num(r.get("difference"), 4), num(r.get("fair_price_true"), 0),
                         num(r.get("price_if_priced_independent"), 0),
                         num(r.get("bettor_edge_if_priced_independent_pct"), 2),
                         srclink(sources, "S1")])
        b.append(table(["Leg prob", "rho", "True joint", "Independent", "Difference",
                        "Fair price (true)", "Price if priced independent", "Bettor edge %", "Source"], rows,
                       note="A negative difference means the true joint probability is lower than the product of "
                            "the legs, so a parlay priced as if the legs were independent gives the bettor less "
                            "than it looks. This is the arithmetic behind the correlation limit gate (G6)."))
    built["correlations.html"] = page("Correlations",
                                      "Measured correlations on official data, the model-derived ones it prices "
                                      "with, and the parlay rho table.", "\n".join(b))

    # === luck ===============================================================
    b = [h2("Luck decomposition", "How many games each team probably should have won, and how far its actual record sits from that.")]
    rows = []
    for r in luck["rows"]:
        z = r.get("luck_z")
        cls = "zhot" if (z is not None and z > 1.5) else ("zcold" if (z is not None and z < -1.5) else "")
        rows.append([esc(r["team"]), esc(r["name"]), str(r["gp"]), esc("%d-%d" % (r["w"], r["l"])),
                     num(r["netr"]), num(r["pyth_win_pct"], 3), num(r["expected_wins"], 2),
                     num(r["luck_wins"], 2), num(r["sd_wins"], 2),
                     '<span class="%s">%s</span>' % (cls, num(z, 2)), srclink(sources, "S1")])
    b.append(table(
        ["T", "Team", "GP", "Record", "Net rtg", "Pyth win %", "Expected W", "Luck W",
         "SD of W", "Luck z", "Source"],
        rows,
        note="Expected wins come from Pythagorean expectation on the team's official net rating; luck wins are "
             "actual wins minus expected wins; z is luck wins divided by the standard deviation of a binomial "
             "with that many games. z above +1.5 is a team that has been lucky; below -1.5, unlucky. "
             "A team with a large positive luck figure is a candidate to fade, not to follow."))
    b.append(banner("info", "Why this page exists",
                     "Luck is the thing that has to be removed before a record can be read as skill. A strategy "
                     "that went 16-7 might have been right 16 times, or might have been right 11 times and been "
                     "lucky 5. The gate that tests this is G4, and it is the gate that no strategy currently "
                     "clears."))
    built["luck.html"] = page("Luck and skill",
                               "How many wins each team probably should have had, and which records are luck "
                               "rather than skill.", "\n".join(b))

    # === backtest ===========================================================
    b = [h2("Out-of-sample window", "Every completed game from 2026-11-06 to 2026-11-12, predicted using ratings computed only from 2026-10-20 to 2026-11-05. No game in the test window contributes to the ratings that predict it.")]
    rows = []
    for g in back["rows"]:
        rows.append([esc(g.get("date")), esc(g.get("matchup")), esc(g.get("game_id")),
                     num(g.get("proj_total")), num(g.get("actual_total")),
                     num(g.get("total_err")), num(g.get("proj_margin")), num(g.get("actual_margin")),
                     num(g.get("margin_err")), num(g.get("model_p_home"), 3),
                     esc(g.get("model_pick")), esc(g.get("actual_winner")),
                     esc(g.get("ats_pick")) if g.get("ats_pick") else NA,
                     esc(g.get("ats_cover")) if g.get("ats_cover") is not None else NA,
                     srclink(sources, g.get("src") or "S1")])
    b.append(table(
        ["Date", "Matchup", "Game id", "Proj total", "Actual total", "Total err",
         "Proj margin", "Actual margin", "Margin err", "P(home)", "Model pick", "Winner",
         "ATS pick", "ATS cover", "Source"],
        rows,
        note="Positive margin error means the model expected the home team to out-score the away team by more "
             "than it did. Final scores are transcribed from the NBA.com Games &amp; Scores pages; every row "
             "links to the official page for its date."))
    b.append(h2("Model fit", "The parameters the model was fitted on, and how it was fitted."))
    fit = back.get("fit", {})
    rows = [[esc(k), esc(v) if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False),
             srclink(sources, "S1")] for k, v in fit.items()]
    b.append(table(["Parameter", "Value", "Source"], rows))
    built["backtest.html"] = page("Out-of-sample backtest",
                                   "The 51-game test window, every game in it, and the parameters the model "
                                   "was fitted on.", "\n".join(b))

    # === model ==============================================================
    b = [h2("Team ratings", "The official season-to-date efficiency numbers the model reads. Every column except the two implied ones is published verbatim by NBA.com.")]
    rows = []
    for r in teams["rows"]:
        rows.append([esc(r["abbr"]), esc(r["team"]), str(r["gp"]), esc("%d-%d" % (r["w"], r["l"])),
                     num(r["win_pct"], 3), num(r["ortg"]), num(r["drtg"]), num(r["netr"]),
                     num(r["pace"]), num(r["efg_pct"]), num(r["ts_pct"]), num(r["tov_pct"]),
                     num(r["oreb_pct"]), num(r["dreb_pct"]), num(r["ast_pct"]), num(r["pie"]),
                     num(r["ppg_implied"]), num(r["opp_ppg_implied"]),
                     srclink(sources, r.get("src"))])
    b.append(table(
        ["T", "Team", "GP", "Record", "Win %", "Off rtg", "Def rtg", "Net rtg", "Pace",
         "eFG %", "TS %", "TOV %", "ORB %", "DRB %", "AST %", "PIE", "PPG (impl)", "Opp PPG (impl)", "Source"],
        rows,
        note="PPG (impl) and Opp PPG (impl) are arithmetic (OffRtg x Pace / 100) on official inputs, shown so "
             "the scoring level can be read directly."))
    b.append(h2("Model assumptions", "Everything the model takes on faith, stated in one place."))
    assump = meta.get("assumptions", {})
    rows = []
    for k, v in assump.items():
        if isinstance(v, dict):
            rows.append([esc(k), esc(v.get("value")), esc(v.get("why", v.get("note", ""))),
                         esc(v.get("source", "")), srclink(sources, "S1")])
        else:
            rows.append([esc(k), esc(v), NA, NA, srclink(sources, "S1")])
    b.append(table(["Assumption", "Value", "Why", "Note", "Source"], rows))
    built["model.html"] = page("Model and team ratings",
                                "The efficiency model, every assumption it makes, and the official team ratings "
                                "it reads.", "\n".join(b))

    # === questions ==========================================================
    b = [h2("Answered", "Questions the data on hand can actually answer, with the number and the confidence.")]
    rows = []
    for q in questions["answered"]:
        rows.append([esc(q["id"]), '<b>%s</b>' % esc(q["question"]), esc(q.get("answer")),
                     esc(q.get("confidence")), srclink(sources, q.get("source"))])
    b.append(table(["ID", "Question", "Answer", "Confidence", "Source"], rows))
    b.append(h2("Open", "Questions that cannot be answered yet. Nothing on this site is decided on an open question."))
    rows = []
    for q in questions["open"]:
        rows.append([esc(q["id"]), '<b>%s</b>' % esc(q["question"]), esc(q.get("what_is_missing")),
                     esc(q.get("how_to_answer")), esc(q.get("blocks")),
                     esc(q.get("priority")),
                     srclink(sources, q.get("source")) if q.get("source")
                     else nomark(q.get("source_url") or "no official source exists")])
    b.append(table(["ID", "Question", "What is missing", "How to answer it",
                     "What it blocks", "Priority", "Source"], rows,
                   note="Where a row says no official source exists, that is the honest answer: no NBA-operated "
                        "page publishes the missing item (a closing price, for instance)."))
    built["questions.html"] = page("Open questions",
                                   "What is already answered with a number, what is still open, and the "
                                   "concrete step that would answer each open item.", "\n".join(b))

    # === suggestions ========================================================
    b = [banner("info", "How to read this page",
                "Each suggestion states the problem, the options with their effort and risk, what each option "
                "unlocks, and a recommendation. <strong>Nothing here has been implemented.</strong> Pick a path "
                "and it can be executed; the <em>decision needed</em> line tells you what has to be decided.")]
    rows = []
    for s in suggestions["items"]:
        rows.append([esc(s["id"]), esc(s.get("category")), '<b>%s</b>' % esc(s["title"]),
                     esc(s.get("problem")),
                     "<br>".join("- " + esc(o["option"]) + " <span class='fine'>(effort: " + esc(o["effort"])
                                + "; risk: " + esc(o["risk"]) + "; unlocks: " + esc(o["unlocks"]) + ")</span>"
                                for o in s.get("options", [])),
                     esc(s.get("recommendation")), esc(s.get("decision_needed")),
                     srclink(sources, s.get("source"))])
    b.append(table(["ID", "Category", "Title", "Problem", "Options", "Recommendation",
                    "Decision needed", "Source"], rows))
    built["suggestions.html"] = page("Suggestions",
                                     "Improvements to the site and to the decision-making process, written as "
                                     "options with effort, risk and what each unlocks.", "\n".join(b))

    # === flagged ============================================================
    b = [banner("warn", "Non-blocking by design",
                "Every item below is either a value that could not be confirmed from an official source, or a "
                "limitation that a reviewer should know about before relying on any number here. "
                "<strong>None of these blocks the site.</strong> They are published with the official link that "
                "would resolve them, so they can be reviewed and assigned.")]
    rows = []
    for f in flagged["items"]:
        rows.append([esc(f["id"]), esc(f.get("severity")), '<b>%s</b>' % esc(f["title"]),
                     esc(f.get("detail")), esc(f.get("affected")),
                     esc(f.get("suggested_action")),
                     srclink(sources, f.get("source")) if f.get("source") else srclink_url(f.get("source_url"), "link")])
    b.append(table(["ID", "Severity", "Item", "What was found", "What it affects",
                    "Suggested action", "Source"], rows))
    built["flagged.html"] = page("Flagged for review",
                                 "Every value that could not be confirmed from an official source, and every "
                                 "limitation a reviewer should know about before relying on a number here.",
                                 "\n".join(b))

    # === sources ============================================================
    b = [banner("info", "The rule", esc(src_reg["rule"]))]
    rows = []
    for sid, s in sorted(src_reg["sources"].items()):
        rows.append([esc(sid), '<b>%s</b>' % esc(s["title"]),
                     esc(s.get("publisher")), esc(s.get("used_for")),
                     srclink_url(s["url"], s["url"])])
    b.append(table(["ID", "Title", "Publisher", "Used for"], rows, src_header="Official URL",
                   note="Snapshot taken %s. Every source id used by a table row on this site resolves to one "
                        "of the URLs below." % esc(src_reg.get("captured_at_utc"))))
    built["sources.html"] = page("Source register",
                                 "Every official URL this site is built from, and what each one is used for.",
                                 "\n".join(b))

    # === repo review ========================================================
    review = load(os.path.join(ROOT, "data", "d", "repo_review.json"))
    b = [h2("What was reviewed", esc(review["summary"]))]
    rows = []
    for r in review["checks"]:
        rows.append([esc(r["item"]), esc(r["method"]), esc(r["result"]),
                     srclink_url(r.get("source"), "open")])
    b.append(table(["Item", "Method", "Result", "Source"], rows))
    b.append(h2("Irregularities found", "Things a reviewer should look at. None of them is a fabricated value; each one is a documented gap or a conflict between two official readings."))
    rows = []
    for i in review["irregularities"]:
        rows.append([esc(i["id"]), esc(i.get("severity")), '<b>%s</b>' % esc(i["title"]),
                     esc(i.get("detail")), esc(i.get("resolution")),
                     srclink_url(i.get("source_url"), "link") if i.get("source_url") else NA])
    b.append(table(["ID", "Severity", "Irregularity", "Detail", "Resolution", "Source"], rows))
    b.append(h2("Verification log", "What was checked, and what the check returned."))
    rows = []
    for v in review["log"]:
        rows.append([esc(v["when"]), esc(v["check"]), esc(v["result"]), esc(v.get("note")),
                     srclink_url(v.get("source_url"), "open")])
    b.append(table(["When (UTC)", "Check", "Result", "Note", "Source"], rows))
    built["repo-review.html"] = page("Repository review and irregularities",
                                     "Line-by-line review of the repository and every official capture behind "
                                     "it, with the irregularities listed and the links to review them.",
                                     "\n".join(b))

    # ------------------------------------------------------------------ write
    for name, html in built.items():
        path = os.path.join(ROOT, name) if name == "index.html" else os.path.join(PAGES, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
    for name, html in built.items():
        if name != "index.html":
            continue
    # assets
    shutil.copyfile(os.path.join(ROOT, "scripts", "assets", "site.css"),
                    os.path.join(ASSETS, "site.css"))
    shutil.copyfile(os.path.join(ROOT, "scripts", "assets", "site.js"),
                    os.path.join(ASSETS, "site.js"))
    # data
    for f in os.listdir(DATA):
        shutil.copyfile(os.path.join(DATA, f), os.path.join(SITE_DATA, f))
    for f in os.listdir(CONTENT):
        shutil.copyfile(os.path.join(CONTENT, f), os.path.join(SITE_DATA, f))
    shutil.copyfile(os.path.join(RAW, "sources.json"), os.path.join(SITE_DATA, "sources.json"))
    shutil.copyfile(os.path.join(ROOT, "data", "d", "repo_review.json"),
                    os.path.join(SITE_DATA, "repo_review.json"))

    print("Wrote %d pages, assets and data to %s" % (len(built), SITE))


if __name__ == "__main__":
    main()
