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
import re
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
    ("Prop Variance &amp; Rotation", "prop-variance.html", "Game-to-game dispersion measured from official game logs: the uncertainty behind every prop, the minutes-to-production elasticity, and what the injury report changed since the lines were cut."),
    ("Injuries &amp; Rotation", "injuries.html", "The official injury report, the rotation minutes it implies, and the measured production impact."),
    ("Game Flow", "gameflow.html", "Pace, expected margin and total, blow-out and overtime probability, and the rest and back-to-back context."),
    ("EVIDENCE", None, "Whether any of it is skill. The out-of-sample record, the gates, the correlations and the luck check."),
    ("Strategies &amp; Leaderboard", "strategies.html", "Ten strategies, the reward tiers, and the leaderboard that ranks them - with nothing promoted that has not passed."),
    ("Validation Gates", "validation.html", "The seven gates every strategy must clear, the definition of each, and how each strategy scored."),
    ("Correlations", "correlations.html", "Measured correlations, model-derived ones and the same-game-parlay rho used for pricing."),
    ("Luck &amp; Skill", "luck.html", "How many wins each team probably should have had, and which of them are luck."),
    ("Out-of-Sample Backtest", "backtest.html", "The full test window - every completed game after the ratings cut-off - and everything measured on it."),
    ("Model &amp; Teams", "model.html", "The efficiency model, its assumptions and the team ratings it reads."),
    ("VERIFICATION", None, "Checked line by line against NBA.com on the day of capture. Mismatches are listed, not corrected."),
    ("Official Source Check", "source-check.html", "Every horizon game and every 11/13 final compared with NBA.com, the 11/13 settlement, and the conflicts between builds."),
    ("Live Re-verification", "official-verify.html", "Every official value on this site read again at 18:40Z on 2026-11-14 and compared with what was published: 185 checks, one row and one official link each."),
    ("DECISION", None, "What is still open, what could be improved, and what could not be verified."),
    ("Open Questions", "questions.html", "What we know, what we do not, and the concrete step that would answer each open item."),
    ("Suggestions", "suggestions.html", "Improvements written as options with effort, risk and what each unlocks, so a reviewer can pick a path."),
    ("Decisions: pick a path", "decisions.html", "Six decisions in dependency order, every open question mapped to the decision that closes it, and every suggestion ranked against them. Start here before implementing anything."),
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
                "home": "index.html", "navbase": "site/pages/", "repo": ""}
    return {"root": "../../", "css": "../assets/site.css", "js": "../assets/site.js",
            "home": "../../index.html", "navbase": "", "repo": "../../"}


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
      <a href="picks.html">Horizon 14–17 (session build)</a>
      <a href="%(navbase)spicks.html">Horizon</a>
      <a href="%(navbase)sstrategies.html">Evidence</a>
      <a href="%(navbase)sdecisions.html">Decisions</a>
      <a href="%(navbase)ssuggestions.html">Suggestions</a>
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
      <code>docs/data/*.json</code>. Sources: <a href="%(navbase)ssources.html">source register</a>.
      Earlier builds, kept as archives:
      <a href="%(repo)scommand-center/index.html">Command Center</a> &middot;
      <a href="%(repo)sedge-lab/index.html">Edge Lab (frozen 11/13)</a> &middot;
      <a href="%(repo)sdesk.html">Integration Desk</a> &middot;
      <a href="%(repo)sdocs/index.html">Build A &mdash; dated NBA snapshot</a> &middot;
      <a href="%(repo)sdocs/b/index.html">Build B &mdash; backtested desk</a> &middot;
      <a href="%(repo)sschedule-verified.html">verified schedule</a> &middot;
      <a href="%(repo)sverification.html">live verification</a>.</p>
    </footer>
  </main>
</div>
<script src="%(js)s"></script>
</body>
</html>
""" % {"title": title, "sub": sub, "body": body, "nav": nav_html(pth),
       "css": pth["css"], "js": pth["js"], "home": pth["home"], "head": extra_head,
       "navbase": pth["navbase"], "repo": pth["repo"]}


# --------------------------------------------------------------- table renderer
def table(headers, rows, note=None, source_col="Source", cls="", table_id=None, src_header=None,
          anchor_pattern=None):
    """rows: list of lists. A cell may be a raw HTML string (already escaped) or a value.

    anchor_pattern: when set (e.g. r"^[A-Z]{1,2}\d+$"), the first cell of a row that matches it
    becomes the row's DOM id, so another page can link straight to that row. Deep links into these
    registers were being written as #SG10 / #Q17 and did not resolve, because the table renderer
    emitted no ids at all."""
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
        _rid = ""
        if anchor_pattern and r:
            _first = re.sub(r"<[^>]+>", "", str(r[0])).strip()
            if re.match(anchor_pattern, _first):
                _rid = ' id="%s"' % _first
        out.append("<tr%s>" % _rid)
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


# ------------------------------------------------- official source check page
def build_source_check(sources):
    """Render verify/2026-11-14/checks.json (written by scripts/source_check.py). Nothing is inferred here."""
    vdir = os.path.join(ROOT, "verify", "2026-11-14")
    chk = load(os.path.join(vdir, "checks.json"))
    off = load(os.path.join(vdir, "official_horizon.json"))
    fin = load(os.path.join(vdir, "official_finals_2026-11-13.json"))
    off_by_id = {r["game_id"]: r for r in off["rows"]}
    hs = chk["horizon_summary"]
    rs = chk["record_summary"]
    ss = chk["settlement_summary"]
    cs = chk["cross_build_summary"]
    cb = chk["build_b_sign_convention"]["counts"]
    xc = load(os.path.join(vdir, "cross_check_finals_cfb25ff0.json"))

    def link(url, label):
        return srclink_url(url, label)

    b = [banner("info", "What this page checks",
                "On 2026-11-14 (UTC) every game on the official NBA.com Games &amp; Scores pages for 11/13–11/17 "
                "was transcribed and compared with the site's data, and the nine official finals of 11/13 were "
                "used to settle the lines that were published for them. The transcription, the checker "
                "(<code>scripts/source_check.py</code>) and every raw value are in "
                "<code>verify/2026-11-14/</code>. Where the site and NBA.com disagree, the row says so and the item is on "
                "<a href=\"flagged.html\">Flagged for Review</a>.")]
    b.append(tiles([
        ("Official games 11/14–11/17", hs["official_games"], "%d matched to the site's horizon" % hs["matched"]),
        ("Missing from slate capture", hs["absent_from_slate_capture"], "11/17 games not in data/official/slate.json"),
        ("11/13 finals on NBA.com", "%d / %d" % (sum(1 for r in fin["rows"] if r["status"].startswith("Final")), len(fin["rows"])), "all shown as Final at capture"),
        ("11/13 settled (WIN / LOSS / NO BET)", "%d / %d / %d" % (ss["WIN"], ss["LOSS"], ss["NO_BET"]), "mean |model &minus; final| margin %s pts" % ss["mean_abs_margin_error"]),
        ("Cross-build disagreements", "%d of %d" % (cs["disagree_over_0.5"], cs["matchups_compared"]), "%d pick opposite favourites" % cs["opposite_favourite"]),
    ]))

    # 1. horizon schedule
    b.append(h2("1. The 27-game horizon, official vs site",
                "One row per official game. Tip times and pairings are compared with the site's horizon lines and the verbatim slate capture."))
    rows = []
    for h in chk["horizon"]:
        o = off_by_id[h["game_id"]]
        rows.append([esc(h["date"]), '<b>%s</b>' % esc(h["matchup"]), esc(h["official_tip_et"]),
                     esc(h["status"]), esc(h["slate_capture_status"]),
                     link(h["official_source"], h["game_id"])])
    b.append(table(["Date", "Game (away@home)", "Tip (official)", "Site horizon", "Slate capture file", "Source"], rows,
                   note="Official counts per day: %s. Site horizon: %d games. The slate capture file holds %d of the 27 games; "
                        "the 5 missing are the 11/17 games." % (
                            ", ".join("%s = %s" % (k[5:], v) for k, v in sorted(hs["calendar_counts_official"].items())),
                            hs["site_horizon_games"], hs["in_slate_capture"])))

    # 2. records
    stale = [r for r in chk["records"] if r["status"] == "STALE_TEAM_PLAYED_11_13"]
    b.append(h2("2. Records on the horizon rows",
                "The site prints each team's record from before 11/13. A team that played on 11/13 has a newer "
                "record on NBA.com. %d of 54 printed records match NBA.com; %d differ, every one of them for a team that "
                "played on 11/13; %d are unexplained." % (rs["MATCH"], rs["STALE_TEAM_PLAYED_11_13"], rs["UNEXPLAINED_MISMATCH"])))
    rows = []
    for r in stale:
        rows.append([esc(r["matchup"]), '<b>%s</b>' % esc(r["team"]), esc(r["site_record_pre_11_13"]),
                     esc(r["official_record_at_capture"]), esc(r["status"]),
                     link(r["official_source"], r["game_id"])])
    b.append(table(["Game", "Team", "Site record (pre-11/13)", "NBA.com record at capture", "Status", "Source"], rows))

    # 3. 11/13 settlement
    b.append(h2("3. The nine 11/13 games, settled against the official finals",
                "These are the lines published for 11/13 on the root <code>lines.html</code>, built from <code>data/originated_lines.json</code> (Build A data). The spread is read as a "
                "standard home spread: in all nine rows it equals minus the model's expected home margin, to within "
                "%s points (the largest gap). A pick covers when the picked side's margin, after the line, is above zero. "
                "The nine finals were also read independently by another session (PR #56, merged to main at 4e4d0b0): "
                "%d of %d agree, see <code>verify/2026-11-14/cross_check_finals_cfb25ff0.json</code>."
                % (ss["max_gap_spread_vs_minus_expected_margin"], xc["result"]["agree"], xc["result"]["games"])))
    rows = []
    for r in chk["settlement_2026_11_13"]:
        final = "%s %s &ndash; %s %s" % (r.get("official_away", ""), r.get("official_away_score", ""),
                                         r.get("official_home", ""), r.get("official_home_score", ""))
        pick = ("%s" % esc(r.get("pick_line"))) if r.get("pick_line") else "no pick (gate)"
        rows.append([
            '<b>%s</b>' % esc(r["matchup"]), final,
            num(r.get("official_home_margin"), 0) if r.get("official_home_margin") is not None else NA,
            num(r.get("originated_spread_home"), 1), num(r.get("model_expected_margin_home"), 1),
            pick, esc(r.get("result")),
            num(r.get("model_error_margin"), 1) if r.get("model_error_margin") is not None else NA,
            link(r.get("official_source"), "final") if r.get("official_source") else NA])
    b.append(table(["Game", "Official final (away &ndash; home)", "Official home margin", "Published spread (home)",
                    "Model expected home margin", "Pick", "Result", "|model &minus; final|", "Source"], rows,
                   note="Tally: %d WIN, %d LOSS, %d PUSH, %d NO BET. Mean absolute margin error %s points over %d games. "
                        "Nine games is far too few to measure skill; this is a single-night check, not a validation."
                        % (ss["WIN"], ss["LOSS"], ss["PUSH"], ss["NO_BET"], ss["mean_abs_margin_error"], ss["n"])))

    # 4. headline numbers
    b.append(h2("4. Numbers on the landing page",
                "Each headline figure, the place it comes from, and what the underlying data says."))
    rows = []
    for h in chk["headline_audit"]:
        rows.append([esc(h["claim"]), esc(h["site_location"]), esc(h["observed"]), '<b>%s</b>' % esc(h["status"]),
                     link(h["official_source"], "NBA.com") if h.get("official_source")
                     else nomark("internal count: no official source applies")])
    b.append(table(["Claim", "Where it appears", "What the data says", "Status", "Source"], rows,
                   note="Counts that describe this repository's own outputs have no official source; they are marked "
                        "internal rather than linked. Only the game, injury and final-score claims are checked against NBA.com."))

    # 5. cross-build
    b.append(h2("5. Two builds, two answers for the same game",
                "Build B (the site's landing page and Lines page) and Build D (the horizon lines) both project a home margin "
                "for the same game. They use different ratings windows, so they disagree. Each cell is a projected home margin: "
                "negative means the home team is projected to lose. Build B's stored <code>model_spread_home</code> holds the "
                "home margin in %d of 16 rows where a strategy pick exists; the standard home-spread reading fits 0 of them. "
                "Build D's <code>line_spread_home</code> equals the projected home margin in all 27 rows."
                % cb["home_margin_consistent"]))
    rows = []
    for c in chk["cross_build"]:
        if "difference" not in c:
            continue
        gid = next((g for g, o in off_by_id.items() if o["matchup"] == c["matchup"]), None)
        src = off_by_id[gid]["source_url"] if gid else None
        rows.append([
            '<b>%s</b>' % esc(c["matchup"]), num(c["build_b_model_home_margin"], 1),
            num(c["build_d_model_home_margin"], 1), num(c["difference"], 1),
            "yes" if (c["build_b_model_home_margin"] > 0) != (c["build_d_model_home_margin"] > 0) else "no",
            link(src, "game") if src else NA])
    b.append(table(["Game", "Build B home margin (landing page)", "Build D home margin (horizon)", "Difference (pts)",
                    "Opposite favourite?", "Source"], rows,
                   note="Build B: ratings training window 10/20–11/05/2026 per site/data/meta.json, with the season-to-date "
                        "ratings through 11/12 also listed there; the page does not say which one the horizon lines use. "
                        "Build D: team ratings through games of 11/12."))

    # 6. open questions
    b.append(h2("6. What this check could not answer",
                "Each item has the official source that would answer it. None of these is filled in by guesswork."))
    rows = [
        ["Is the 11/14 noon injury report published?", "The 11/14 12:00 PM ET edition URL returned AccessDenied at capture. The site's newest edition is 11/13 07:30 PM ET.",
         "Re-check after 17:00 UTC on 2026-11-14", link("https://official.nba.com/nba-injury-report-2026-27-season/", "NBA injury report policy")],
        ["Which ratings window do the landing-page lines use?", "site/data/meta.json lists two windows; the page does not say which one feeds the horizon lines.",
         "Ask the build owner; then state it on the page", link("https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season", "NBA.com team advanced stats")],
        ["Are the repeated pairings (NYK@TOR 11/15 and 11/17; POR@MIN 11/16 and 11/17) real?", "Both are printed on NBA.com with distinct game IDs. They are carried as printed.",
         "Confirm on the official schedule on each date", link("https://www.nba.com/games?date=2026-11-15", "NBA.com 11/15")],
        ["Did the 9 games of 11/13 settle the model's margin well?", "9 games, mean absolute margin error %s points. Too few to say." % ss["mean_abs_margin_error"],
         "Settle every new slate against official finals, with the sample stated", link("https://www.nba.com/games?date=2026-11-13", "NBA.com 11/13")],
    ]
    b.append(table(["Question", "What the check found", "What would answer it", "Source"], rows))

    return page("Official source check",
                "Line-by-line comparison of the site with NBA.com on 2026-11-14 (UTC): the horizon, the nine 11/13 finals and "
                "the settlement of the lines published for them.", "\n".join(b))


# ------------------------------------------------------- prop variance (session 24eb72c6)


_REG_CACHE = {}


DECISION_PATHS = [
    {
        "id": "P1",
        "source": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf",
        "title": "Decide whether the hour of the capture is part of the product",
        "why": ("The 18:40Z re-read found the site pricing from a 04:15 AM ET injury edition while the "
                "01:30 PM ET edition was published and four of the five teams it called unfiled had "
                "filed. Nothing about the model is wrong; the site simply had no rule for how old a "
                "capture may be before it must be labelled or refreshed. This is the cheapest decision "
                "here and it is the one that keeps every other number honest."),
        "options": [
            ("Ship a freshness label on every derived row (what this session did)",
             "Done in this session: <code>inventory_status</code> on all 27 lines, the edition named "
             "on every availability column, and a Live Re-verification page that shows the diff.",
             "Low", "Already in the tree"),
            ("Re-price the lines from the 01:30 PM ET edition and the 11/13 ratings",
             "The ratings model would have to be re-run and every pick re-cut. That changes what the "
             "site publishes, so it needs a decision, not a patch.",
             "Medium", "Blocked on P2: nobody can say which of the two line sets is the official one"),
            ("Automate a refresh before each slate and keep the label only as a fallback",
             "The refresh path exists (F7) but is manual. Worth it only after P2.",
             "High", "Blocked on P2"),
        ],
        "recommend": ("Option 1 now, and decide between options 2 and 3 only once P2 is settled. A "
                      "labelled stale number is defensible; an unlabelled one is not, and that was the "
                      "actual defect found today."),
        "questions": ["Q17", "Q18", "Q19"],
        "suggestions": ["SG10", "SG16"],
        "needs": "One rule, written down: how old a capture may be, and what the site must print when it "
                 "is older than that.",
    },
    {
        "id": "P2",
        "source": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
        "title": "Say which line set is official",
        "why": ("Two projection sets on this site disagree about the same games (F26, F27, F35) and the "
                "live re-read found a third number that matters: the published ratings are through "
                "11/13, and 19 of 30 teams moved when the 11/13 finals were folded in. Every page that "
                "quotes a spread is quoting a number computed from a window the other page may not use. "
                "Until one set is named official, no gate result can be compared across pages."),
        "options": [
            ("Nominate one line set, one ratings window and one sign convention (SG15)",
             "The Source Check page's section 5 becomes empty because there is nothing left to "
             "reconcile. This is a documentation and wiring change, not a modelling one.",
             "Medium", "Unblocks P1 option 2, the leaderboard's comparability, and every cross-page claim"),
            ("Keep both sets and print the window beside every line",
             "Cheaper today, but the reader has to do the reconciliation the site should have done.",
             "Low", "Nothing structural; the ambiguity survives"),
        ],
        "recommend": ("Option 1. It is the only item on this page that makes the leaderboard mean "
                      "something, and it is a prerequisite for the two most valuable data suggestions "
                      "(SG1, SG17)."),
        "questions": ["Q2", "Q9", "Q14"],
        "suggestions": ["SG15", "SG6", "SG12"],
        "needs": "A decision on which window the public line uses, written into the build so it cannot "
                 "drift again.",
    },
    {
        "id": "P3",
        "source": "https://www.nba.com/games",
        "title": "Buy or refuse a price feed",
        "why": ("Every 'edge' on this site is the model against a naive reference, because no "
                "NBA-operated source publishes a price (F3, Q1). The leaderboard can therefore never "
                "say whether anything is profitable, and gate GG can never close. This is not a data "
                "gap that more scraping fixes: it is a licensing decision."),
        "options": [
            ("License a closing-price feed and log it per play (SG2, option 1)",
             "Makes ROI a real number and closing-line value measurable. Introduces a non-NBA source, "
             "so every row needs its own source link and the site's one-rule guarantee has to be "
             "extended to it explicitly.",
             "Medium (build) / commercial (licence)", "Q1, Q8, the reward tiers, gate GG"),
            ("Manual closing-line log as a stopgap (SG2, option 2)",
             "No licence needed. Human transcription error is the risk, and it is daily work.",
             "Low per day", "The same answers, more slowly and less reliably"),
            ("Refuse, and keep the model-vs-reference framing permanently (SG2, option 3)",
             "Defensible and honest. The cost is that nothing on this site can ever be called a "
             "market edge, and the leaderboard stays a research ranking.",
             "None", "Nothing, but nothing is claimed either"),
        ],
        "recommend": ("Option 3 is the only one available today, because no licence exists and no "
                      "NBA-operated price is published. If a feed is bought, take option 1 and not "
                      "option 2: a manual log cannot be audited row by row, which is the rule the "
                      "rest of the site runs on."),
        "questions": ["Q1", "Q8"],
        "suggestions": ["SG2", "SG5"],
        "needs": "A yes/no on the licence, and if yes, the retention and attribution terms.",
    },
    {
        "id": "P4",
        "source": "https://www.nba.com/games?date=2026-11-14",
        "title": "Let the sample grow, or stop running strategies",
        "why": ("Every graded strategy sits under the 30-play sample gate except S1, which has 32 plays "
                "and fails calibration and stability. The out-of-sample window is now 60 games and "
                "cannot grow from the current split, because 2026-10-20 to 2026-11-05 is the ratings "
                "window. Running more strategies on the same 60 games raises the multiple-comparison "
                "problem, not the evidence (Q2, Q3, F8)."),
        "options": [
            ("Backfill 2026-10-20 to 2026-11-05 and re-cut the split (SG1)",
             "The only way to lengthen the test window. The games are officially published; the work "
             "is a walk over the day pages and a re-fit.",
             "Low-Medium", "Q2, F8, F9; every gate result becomes meaningful"),
            ("Freeze the strategy library at ten and wait for games to accumulate",
             "No new claims, no new risk of a lucky cell. Roughly two months at 60 games per week.",
             "None", "Nothing new, nothing false"),
            ("Keep adding strategies on 60 games",
             "Each new cell is another multiple comparison. This is how a lucky cell gets promoted.",
             "Low", "A false positive, eventually"),
        ],
        "recommend": ("Option 1, and freeze the library while it runs. The power calculation already on "
                      "the site says the effect sizes involved need several hundred games; adding "
                      "strategies to 60 games does not substitute for adding games."),
        "questions": ["Q2", "Q3", "Q5"],
        "suggestions": ["SG1", "SG7"],
        "needs": "Approval to spend the run, and a rule for the multiple-comparison correction before "
                 "any new strategy is added.",
    },
    {
        "id": "P5",
        "source": "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season",
        "title": "Decide what the injury report is allowed to move",
        "why": ("Availability is a measured floor, not an estimate: minutes are known for 50 of the 465 "
                "players in the official table, so a team missing rotation players who are not top-50 "
                "scorers shows 0.00 (F2, F4). Today's re-read adds a second problem: 33 status lines "
                "changed in nine hours, so the adjustment depends on when you read it. An adjustment "
                "that is both incomplete and time-dependent should not silently move a line."),
        "options": [
            ("Neutralise availability in the published line and publish the statuses beside it",
             "The line becomes reproducible from the ratings alone. The injury work becomes evidence, "
             "not an input.",
             "Low", "A line anyone can recompute; the props page keeps its own measured widths"),
            ("Complete the minutes table, then price availability properly (SG3)",
             "The official Players Traditional table has 465 players; 415 of them lack a captured "
             "minutes value. That is a capture job, not a model job.",
             "Medium", "Q4, a trustworthy availability column, and grading strategy S6"),
            ("Keep the current partial adjustment and label it",
             "What the site does now. Defensible only while every row says so.",
             "None", "Nothing"),
        ],
        "recommend": ("Option 2 if the capture can be run, option 1 until then. Option 3 is what is "
                      "live today and it is the weakest of the three."),
        "questions": ["Q4", "Q5", "Q12"],
        "suggestions": ["SG3", "SG18"],
        "needs": "A decision on whether an unmeasured adjustment may move a published number at all.",
    },
    {
        "id": "P6",
        "source": "https://www.nba.com/standings",
        "title": "Make the verification independent of this repository",
        "why": ("The gate that runs in CI checks structure: that a row has a source link, that a link "
                "resolves, that a table has the right number of cells (F34). It does not check that the "
                "value is right. Today's 185-row re-read exists only because a session chose to do it, "
                "and its artifact is a JSON file in <code>verify/</code> that nothing re-runs."),
        "options": [
            ("Make the live re-read a scheduled job that writes the artifact and fails on a new differ (SG16)",
             "The 185 checks already exist and already carry their own URLs. The job is to run them on "
             "a schedule and publish the diff instead of discovering it by hand.",
             "Medium", "Q17; a gate that tests values, not only structure"),
            ("Keep the manual re-read, and publish each one as a dated artifact",
             "What exists now. Cheap, but it depends on somebody choosing to do it.",
             "Low", "A record, not a guarantee"),
        ],
        "recommend": ("Option 1. It is the highest-leverage change on this page that costs no money and "
                      "no licence, and it converts today's one-off audit into a standing test."),
        "questions": ["Q17", "Q18"],
        "suggestions": ["SG14", "SG16", "SG10"],
        "needs": "A decision on whether a red live-check may block a merge, given that the pages it "
                 "reads change every 15 minutes by design.",
    },
]


def _qsrc(q):
    """A question's source cell: the register id when there is one, otherwise an explicit marker.

    Several open questions ask for information that no official source publishes (a book price, a
    licensed feed). Those carry a sentence instead of a URL in source_url, and rendering that
    sentence as a link produced a broken internal link. It is a "nothing to link to" fact and is
    rendered as one."""
    url = (q.get("source_url") or "")
    if q.get("source"):
        _e = _REG_CACHE.get(q["source"])
        return srclink_url(_e["url"], q["source"]) if _e else nomark(
            "source id %s is not in the register" % q["source"])
    if url.startswith("https://"):
        return srclink_url(url, "official page")
    return nomark(url or "no official source exists for this item")


def build_decisions(questions, suggestions):
    """The path-picker: every suggestion and open question, arranged so a reviewer can choose.

    Nothing here is new evidence. It is the decision layer over content that already exists in
    data/content/{questions,suggestions}.json, plus what the 2026-11-14 18:40Z re-read measured."""
    _REG_CACHE.update(load(os.path.join(RAW, "sources.json"))["sources"])
    q_open = {q["id"]: q for q in questions["open"]}
    q_ans = {q["id"]: q for q in questions["answered"]}
    sg = {s["id"]: s for s in suggestions["items"]}

    b = [banner("info", "What this page is for",
                "<p>Six decisions, in the order they unblock each other. Each one states what is "
                "actually known, the options with their real cost, which open questions it answers, "
                "which suggestions it consumes, and what a reviewer has to decide before any of it "
                "can be built. <strong>Nothing on this page has been implemented</strong> except "
                "where a row says so.</p>"
                "<p>The evidence behind every claim is on the pages linked in each row. The open "
                "questions and the suggestion catalogue are unchanged and stay published in full on "
                "<a href=\"questions.html\">Open Questions</a> and "
                "<a href=\"suggestions.html\">Suggestions</a>; this page is the reading order, not a "
                "replacement.</p>")]

    b.append(h2("Pick a path",
                "In dependency order. P1 is cheap and unblocks nothing; P2 unblocks the leaderboard; "
                "P3 is the only one that needs money; P4 and P5 are the two that change what the site "
                "publishes; P6 is the one that makes the rest stay true."))
    for p in DECISION_PATHS:
        opts = "".join(
            "<tr><td><b>%s</b></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (o[0], o[1], o[2], o[3], srclink_url(p["source"], "official page"))
            for o in p["options"])
        qs = ", ".join(
            '<a href="questions.html#%s">%s</a> <span class="chip %s">%s</span>'
            % (qid, qid,
               "ok" if qid in q_ans else "warn",
               "answered" if qid in q_ans else "open")
            for qid in p["questions"] if qid in q_open or qid in q_ans)
        sgs = ", ".join('<a href="suggestions.html#%s">%s</a>' % (sid, sid)
                        for sid in p["suggestions"] if sid in sg)
        b.append('<div class="dcard"><h3>%s &mdash; %s</h3>'
                 '<div class="dline"><b>Why it is a decision:</b> %s</div>'
                 '<table class="t"><thead><tr><th style="width:22%%">Option</th><th>What it means</th>'
                 '<th style="width:8%%">Effort</th><th style="width:15%%">What it unlocks</th>'
                 '<th style="width:11%%">Source</th></tr></thead><tbody>%s</tbody></table>'
                 '<div class="dline" style="margin-top:8px"><b>Recommended:</b> %s</div>'
                 '<div class="dline"><b>Questions it moves:</b> %s &nbsp;&middot;&nbsp; '
                 '<b>Suggestion it consumes:</b> %s</div>'
                 '<div class="dline"><b>What has to be decided:</b> %s</div></div>'
                 % (esc(p["id"]), esc(p["title"]), esc(p["why"]), opts, esc(p["recommend"]),
                    qs, sgs, esc(p["needs"])))

    # ---- every open question, with the decision that answers it
    b.append(h2("Every open question, and what would answer it",
                "The 19 open questions verbatim from the repository, each mapped to the decision above "
                "that closes it and to the concrete step that produces the missing information."))
    ans_map = {"P1": ["Q17", "Q18", "Q19"], "P2": ["Q2", "Q9", "Q14"],
               "P3": ["Q1", "Q8"], "P4": ["Q3", "Q5"], "P5": ["Q4", "Q6", "Q12"],
               "P6": ["Q10", "Q11", "Q13", "Q15", "Q16", "Q20"]}
    rows = []
    for qid in sorted(q_open):
        q = q_open[qid]
        path = next((pid for pid, ids in ans_map.items() if qid in ids), None)
        rows.append([esc(qid), esc(q.get("question")),
                     esc(q.get("what_is_missing")),
                     esc(q.get("how_to_answer")),
                     ('<span class="chip info">%s</span>' % path) if path else
                     '<span class="chip bad">no path</span>',
                     _qsrc(q)])
    b.append(table(["ID", "Question", "What is missing", "How to answer it", "Decision", "Source"],
                   rows, anchor_pattern=r"^Q\d+$"))
    b.append('<p class="fine">%d open, %d answered. An answered question is not re-opened here; it is '
             'on the <a href="questions.html">Open Questions</a> page with its number.</p>'
             % (len(q_open), len(q_ans)))

    # ---- the suggestion catalogue, with effort/risk read off the repository
    b.append(h2("The suggestion catalogue, ranked for review",
                "18 suggestions as they exist in the repository, with the recommendation the "
                "repository already makes and the decision it belongs to. Nothing has been "
                "implemented."))
    _sg_reg = load(os.path.join(RAW, "sources.json"))["sources"]
    cat = {"Data": "info", "Model": "warn", "Site / UI": "ok", "Site": "ok",
           "Operations": "info", "Trust": "bad", "Decision support": "info",
           "Verification": "bad", "Data and model": "warn"}
    rows = []
    for s in suggestions["items"]:
        path = next((pid for pid, p in [(p["id"], p) for p in DECISION_PATHS]
                     if s["id"] in p["suggestions"]), None)
        rows.append([esc(s["id"]),
                     '<span class="chip %s">%s</span>' % (cat.get(s.get("category"), "info"),
                                                         esc(s.get("category"))),
                     '<b>%s</b>' % esc(s["title"]),
                     esc(s.get("problem")),
                     esc(s.get("recommendation")),
                     ('<span class="chip info">%s</span>' % path) if path else "&mdash;",
                     (srclink_url(_sg_reg[s["source"]]["url"], s["source"])
                      if _sg_reg.get(s.get("source")) else
                      nomark("no source id on this suggestion in the catalogue"))])
    b.append(table(["ID", "Category", "Suggestion", "The problem it fixes", "What the repo recommends",
                    "Decision", "Source"], rows,
                   note=("Sources are the official pages the suggestion is built on. A suggestion that "
                         "adds a source is the only kind that can add a link here, which is why the "
                         "rows for licensed-price work point at the NBA page that shows the gap.")))

    # ---- what was found and fixed today, and what was not
    b.append(h2("What the 2026-11-14 18:40Z re-read changed, and what it did not",
                "Recorded here because a decision page that hides its own findings is not a decision "
                "page."))
    rows = [
        ["The site published 39 flags, 13 answered + 18 open questions and 16 suggestions while the "
         "repository held 46, 15 + 19 and 18",
         "FIXED in this session: <code>build_dashboard.py</code> now copies the authored files from "
         "<code>data/content</code> on every build and fails loudly if one is missing.",
         '<span class="chip ok">fixed</span>',
         srclink_url("https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/content/flagged.json",
                     "diff")],
        ["The site prices availability from the 04:15 AM ET injury edition; the newest published is "
         "01:30 PM ET, and 33 status lines changed in between",
         "LABELLED, not re-priced: every line now carries the edition it came from and says NOT "
         "RE-PRICED. Re-pricing needs decision P1.",
         '<span class="chip warn">labelled</span>',
         srclink_url("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf",
                     "official PDF")],
        ["Four of the five teams the site marks 'had not filed' had filed by 01:30 PM ET",
         "CORRECTED in the data: the listing count and the report status on all 27 lines now come from "
         "the 01:30 PM ET edition.",
         '<span class="chip ok">fixed</span>',
         srclink_url("https://official.nba.com/nba-injury-report-2026-27-season/", "official index")],
        ["19 of 30 teams moved between the published ratings window and the live Teams Advanced page",
         "NOT CHANGED BY DESIGN: the lines were computed from the published window, so re-basing the "
         "ratings table alone would make two pages disagree. The live value is shown beside the "
         "published one. Which set is official is decision P2.",
         '<span class="chip warn">needs P2</span>',
         srclink_url("https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
                     "official page")],
        ["The 18:40Z standings read disagreed with the committed copy on 18 of 30 teams",
         "NO DEFECT: the committed capture was taken at 00:45Z, before the 11/13 finals, and the site "
         "table already carried the finals. Verified, not assumed.",
         '<span class="chip ok">verified</span>',
         srclink_url("https://www.nba.com/standings", "official page")],
        ["All 18 published backtest metrics and the S1 record were re-derived from the repository's own rows",
         "NO DEFECT: 18 of 18 reproduce exactly (MAE, RMSE, bias, Brier, log loss, straight-up, and "
         "23-9 = +11.909 units at -110, Wilson 95% [0.5463, 0.8444], exact binomial p = 0.0201).",
         '<span class="chip ok">verified</span>',
         srclink_url("https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
                     "input page")],
    ]
    b.append(table(["Finding", "What was done about it", "Status", "Source"], rows))

    b.append(h2("How to use this page",
                "Three steps, in order."))
    b.append('<ol class="steps">'
             "<li>Read P1 and P6 first. Both are cheap, neither needs money, and together they stop the "
             "site from publishing a number that is older than it says it is.</li>"
             "<li>Answer P3 (price feed) before reading the leaderboard as anything other than a "
             "research ranking. Until it is answered, no strategy on this site can be called a market "
             "edge, and that is not a defect - it is the missing input.</li>"
             "<li>Treat P2, P4 and P5 as one decision about what the published line means. Changing any "
             "one of them changes what every page quotes.</li>"
             "</ol>")
    return page("Decisions: pick a path",
                "Six decisions in dependency order, the 19 open questions mapped to the decision that "
                "closes each one, and the 18 suggestions ranked for review. Nothing here is "
                "implemented unless it says so.",
                "\n".join(b))


def build_official_verify():
    """Render verify/2026-11-14-cc5a6652/compare.json (session arena/cc5a6652-nba1).

    That file is written by verify/2026-11-14-cc5a6652/capture_live.py, which transcribed the
    official pages live on 2026-11-14 18:40Z-19:10Z and compared each row with the copy
    committed here. Every row on this page carries the official URL it was read from.
    Nothing on this page is recomputed from the repository: it is the comparison itself."""
    vp = os.path.join(ROOT, "verify", "2026-11-14-cc5a6652", "compare.json")
    if not os.path.exists(vp):
        return page("Live re-verification", "the artifact is missing",
                    banner("warn", "Artifact missing",
                           "<p><code>verify/2026-11-14-cc5a6652/compare.json</code> is not present. Run "
                           "<code>python3 verify/2026-11-14-cc5a6652/capture_live.py</code>.</p>"))
    cmp = load(vp)
    chk = cmp["checks"]
    cnt = cmp["counts"]

    def sec(prefix):
        return [c for c in chk if c["section"].startswith(prefix)]

    def mark(ok):
        return ('<span class="ok">match</span>' if ok
                else '<span class="bad">differs</span>')

    def row(c, name_hdr="Row"):
        return [esc(c["item"]), esc(c["committed"]), esc(c["live"]), mark(c["match"]),
                srclink_url(c["source_url"], "official page")]

    b = [banner("info", "What this page is",
                "<p>On <strong>2026-11-14, 18:40Z-19:10Z</strong> the official pages were read again, row "
                "by row, and every value was compared with the copy this repository publishes. The "
                "transcription and the diff are one artifact: "
                "<code>verify/2026-11-14-cc5a6652/compare.json</code>, produced by "
                "<code>capture_live.py</code> in the same directory. This page renders that file.</p>"
                "<p><strong>%d checks, %d match, %d differ.</strong> A row that differs is not "
                "automatically a defect: the repository is a dated snapshot, so a value that was right at "
                "00:42Z and wrong at 19:10Z is a staleness finding and is reported as one. Where the live "
                "value is a <em>newer edition of the same official fact</em>, the fix is either to publish "
                "the newer edition or to label the old one; both are shown below.</p>"
                % (cnt["checks"], cnt["match"], cnt["differ"]))]

    b.append(h2("Summary by check",
                "Every check on this page is one row of one official table compared with the copy in the "
                "repository. Nothing is sampled and nothing is skipped."))
    rows = []
    seen = []
    for c in chk:
        if c["section"] in seen:
            continue
        seen.append(c["section"])
        ss = sec(c["section"])
        rows.append([esc(c["section"]), str(len(ss)),
                     str(sum(1 for x in ss if x["match"])),
                     str(sum(1 for x in ss if not x["match"])),
                     srclink_url(ss[0]["source_url"], "official page")])
    b.append(table(["Check", "Rows", "Match", "Differ", "Source"], rows))

    # ---- A. finals
    b.append(h2("A. The 2026-11-13 finals, 9 games",
                "Each official final score compared with <code>data/verified/finals_2026-11-13.json</code>."))
    b.append(table(["Game", "Committed", "Read live 18:40Z", "Result", "Source"],
                   [row(c) for c in sec("A.")]))

    # ---- B/C. horizon
    b.append(h2("B. The horizon, 27 games",
                "Matchup, date and tip time for every unplayed game in 11/14-11/17, compared with "
                "<code>data/derived/horizon_lines.json</code>."))
    b.append(table(["Game", "Committed", "Read live 18:40Z", "Result", "Source"],
                   [row(c) for c in sec("B.")]))
    b.append(h2("C. The records the site prints on those games",
                "Every won-lost record on the Lines page, compared with the record printed on the "
                "official game card for the same game."))
    b.append(table(["Game", "Site row", "Official card", "Result", "Source"],
                   [row(c) for c in sec("C.")]))

    # ---- D. standings
    b.append(h2("D. The standings page, all 30 teams",
                "The repository's <code>data/official/standings.json</code> was captured at 00:45Z, before "
                "the 11/13 finals. This is the same page read again at 18:40Z."))
    b.append(table(["Team", "Committed 00:45Z", "Read live 18:40Z", "Result", "Source"],
                   [row(c) for c in sec("D.")]))

    # ---- E. ratings
    b.append(h2("E. Teams Advanced, all 30 teams, every printed column",
                "All nineteen columns the page prints were compared for each team. The repository's copy "
                "runs through the games of 2026-11-12; the live page includes 2026-11-13."))
    b.append(table(["Team", "Committed window", "Read live 18:40Z", "Result", "Source"],
                   [row(c) for c in sec("E.")]))

    # ---- F. injury drift
    b.append(h2("F. What changed in the injury report between 04:15 AM ET and 01:30 PM ET",
                "The site prices its availability adjustment from the 04:15 AM ET edition. The newest "
                "edition published on the official index at read time is 01:30 PM ET. Every named row for "
                "the eleven 11/14 games is compared below; a row that appears on only one side is a player "
                "who was added or dropped between editions."))
    b.append(table(["Matchup - team - player", "04:15 AM ET", "01:30 PM ET", "Result", "Source"],
                   [row(c) for c in sec("F.")]))

    # ---- G. currency
    b.append(h2("G. Which edition the site actually uses",
                "Two rows, both of which differ: the site is pricing from a superseded edition of an "
                "official document that is still published and still correct for its time."))
    b.append(table(["Item", "Site value", "Official value at read time", "Result", "Source"],
                   [row(c) for c in sec("G.")]))

    # ---- H. filed teams
    b.append(h2("H. Teams the site marks 'had not filed'",
                "Five teams had not filed at 04:15 AM ET. Four of them had filed by 01:30 PM ET. The "
                "official submission rule is 11 a.m. to 1 p.m. local time on game day, so the site's "
                "label was true when captured and is stale now."))
    b.append(table(["Matchup - team", "Site value", "At 01:30 PM ET", "Result", "Source"],
                   [row(c) for c in sec("H.")]))
    b.append('<p class="fine">Submission rule, quoted from the official index page: '
             '&ldquo;teams are required to submit a game-day injury report between 11 a.m. and 1 p.m. '
             'local time (and between 8 and 10 a.m. for tip-offs 5 p.m. or earlier) on game days&rdquo; '
             '&mdash; ' + srclink_url(cmp["sources"]["injury_index"], "official index") + '.</p>')

    # ---- what this page does not check
    b.append(h2("What this page does not check",
                "Stated so the page cannot be read as a clean bill of health."))
    b.append("<ul>"
             "<li>It does not check any derived number. A spread, a total, a moneyline, a win "
             "probability, an ROI, a p-value or a gate result is model output, and no official page "
             "publishes a value to compare it against. Those numbers are checked on the "
             '<a href="validation.html">Validation</a> and <a href="backtest.html">Backtest</a> '
             "pages, and the ones that <em>can</em> be recomputed from this repository's own rows are "
             "recomputed there.</li>"
             "<li>It does not check that a page stays available. A 200 at read time is the only claim.</li>"
             "<li>It does not settle anything. Settlement against the 11/13 finals is on the "
             '<a href="picks.html">Lines &amp; Picks</a> page and in the settlement record.</li>'
             "<li>It reads the pages once. Two readers an hour apart can disagree, and the "
             "injury-report columns are exactly where that happens.</li>"
             "</ul>")
    b.append('<p class="fine">Read live: %s &middot; session <code>%s</code> &middot; artifact '
             '<code>verify/2026-11-14-cc5a6652/compare.json</code>.</p>'
             % (esc(cmp["read_at_utc"]), esc(cmp["session"])))
    return page("Live re-verification, 2026-11-14 18:40Z",
                "Every official value this site publishes, read again line by line and compared with what "
                "was published. %d checks, %d match, %d differ, and the differences explained one at a "
                "time." % (cnt["checks"], cnt["match"], cnt["differ"]),
                "\n".join(b))


def build_prop_variance():
    """Render data/derived/prop_variance.json (written by scripts/prop_variance.py).

    Every box score on this page is a row transcribed from an official NBA.com player page
    (data/proplogs/2026-11-14/captures.json); every derived figure is computed in the script
    and the rule that produced it is printed in the note under its table. A cell the capture
    could not read stays blank and is called out, never filled in."""
    path = os.path.join(ROOT, "data", "derived", "prop_variance.json")
    if not os.path.exists(path):
        return page("Prop variance and rotation",
                    "Measured game-to-game dispersion from official player game logs.",
                    banner("warn", "No measurement file",
                           "<code>data/derived/prop_variance.json</code> is not present. Refresh "
                           "<code>data/proplogs/</code> from NBA.com and run "
                           "<code>python3 scripts/prop_variance.py</code>."))
    v = load(path)
    hl = v["headline"]
    b = []

    b.append(tiles([
        ("Players measured", hl["players_captured"], "of %d prop rows published for 2026-11-14" % (hl["players_captured"] + 4)),
        ("Box scores transcribed", hl["games_transcribed"], "%d rows complete enough for rebounds and assists" % hl["complete_rows"]),
        ("Props now priced", hl["props_now_priced"], "a measured SD behind the projection"),
        ("Props clearing 1 SD", hl["props_clearing_one_sd"], "our line vs the season-average anchor"),
        ("Cohort CV, points", hl["cohort_cv_points"], "game-to-game SD as a share of a player's average"),
        ("Cross-check rows agreed", hl["cross_check_rows_agreeing"], "independent read of the same pages 9h earlier; %d disagreements" % hl["cross_check_disagreements"]),
    ]))

    b.append(banner("warn", "Why this page exists",
                    "<p>Until now every prop row on this site published a projection with the "
                    "<em>probability column left blank</em>, because game-to-game variance had never been "
                    "measured from official data (open question Q3, flag F2). Without a dispersion figure a "
                    "projection is a point with no width, so no prop could be sized, no prop combination could "
                    "be priced, and no prop could be graded against anything.</p>"
                    "<p>This page measures that width from the official NBA.com game-log pages for the "
                    "2026-11-14 slate cohort, states the sampling limit next to every number, and reports "
                    "what it does and does not license. It prices %d of the %d horizon prop rows; the other "
                    "%d still carry no probability, exactly as before.</p>"
                    % (hl["props_now_priced"], hl["props_total_in_horizon"], hl["props_still_unpriced"])))

    b.append(h2("1. Measured dispersion, player by player",
                "Each row is the player's own captured games. \"SD used\" is the player's sample SD shrunk "
                "toward the cohort figure; the shrinkage rule is printed below the table."))
    rows = []
    for r in v["per_player"]:
        bd = r["band"]["pts"]
        bp = r["band"]["pra"]
        rows.append([
            "<b>%s</b>" % esc(r["player"]), esc(r["team"]), esc(r["n_games_pts"]),
            num(bd["mean"]), num(bd["sd_player"]), num(bd["sd_cohort_implied"]), num(bd["sd_used"]),
            "&plusmn;%s" % num(bd["sd_uncertainty"]), num(bd["cv"], 3),
            "%s&nbsp;&ndash;&nbsp;%s" % (num(bd["band_80"][0]), num(bd["band_80"][1])),
            num(r["site_proj_pts"]), num(r["site_baseline_pts"]),
            num(bp["sd_used"]) if bp.get("sd_used") is not None else NA,
            srclink_url(r["page"], "player page"),
        ])
    b.append(table(["Player", "Team", "Games read", "Mean PTS", "SD (own)", "SD (cohort)", "SD used",
                    "SD uncertainty", "CV", "80% band on PTS", "Our proj", "Season anchor", "SD used PRA",
                    "Source"], rows,
                    note="Sample SD uses ddof&nbsp;=&nbsp;1. Because three or four games cannot pin a player's own SD, "
                         "it is shrunk toward the cohort: SD<sub>used</sub><sup>2</sup> = "
                         "((n&minus;1)&middot;SD<sub>player</sub><sup>2</sup> + 4&middot;SD<sub>cohort</sub><sup>2</sup>) / "
                         "(n&minus;1 + 4), where SD<sub>cohort</sub> = pooled CV &times; the player's mean (points CV "
                         "%s over %d rows). \"SD uncertainty\" is SD / sqrt(2(n&minus;1)) - the error on the SD itself - "
                         "and it is large on purpose: a band this wide is the honest answer at this sample size. "
                         "A dash means the cell was not readable at the chunk boundary or the player is outside the "
                         "captured season table; nothing is estimated into it."
                         % (num(v["cohort_dispersion"]["pts"]["pooled_cv"], 3), v["cohort_dispersion"]["pts"]["n_obs"])))

    b.append(h2("2. The prop signal, and why none of it clears the bar",
                "Edge here means our projection minus the player's own season average, expressed in the measured SD. "
                "It is not an edge against a book: no official source publishes a prop line (Q1, F3)."))
    rows = []
    for s in v["prop_signals"]:
        if s["status"] != "MEASURED":
            rows.append([esc(s["player"]), NA, NA, NA, NA, NA, NA,
                         '<span class="na" title="%s">not priced</span>' % esc(s.get("why", ""))])
            continue
        rows.append([
            "<b>%s</b>" % esc(s["player"]), esc(s["team"]), num(s["n_games"], 0),
            num(s["anchor_season_avg"]), num(s["our_projection"]), num(s["gap_pts"], 2),
            num(s["gap_in_sd"], 3), num(s["p_beats_anchor"], 3),
            "%s&nbsp;&ndash;&nbsp;%s" % (num(s["fair_line_low"]), num(s["fair_line_high"])),
            esc(s["tier"]), srclink_url(s["page"], "player page"),
        ])
    rows = rows  # keep column count consistent below
    b[-1:] = b[-1:]
    b.append(table(["Player", "Team", "Games", "Season anchor", "Our projection", "Gap",
                    "Gap in SD", "P(beats anchor)", "80% fair band", "Tier", "Source"], rows,
                    note="P(beats anchor) is 1 &minus; &Phi;((anchor &minus; projection) / SD<sub>used</sub>) under a "
                         "normal model on the two figures above. The desk rule this page supports: <b>a prop is "
                         "publishable only when our projection sits at least one measured SD away from the naive "
                         "anchor</b>; below that the projection is inside the player's own week-to-week noise, and the "
                         "correct action is no bet. On 2026-11-14 that is every prop in the cohort - the largest gap "
                         "measured is %s SD - which is the finding, not a shortfall of the pipeline."
                         % num(max([abs(x.get("gap_in_sd") or 0) for x in v["prop_signals"]]), 2)))

    b.append(h2("3. Every box score behind the numbers",
                "The raw transcription. One row per game, as printed on the official page, with the box score link "
                "for the same game so a reviewer can re-read it."))
    rows = []
    for r in v["per_player"]:
        for g in r["games"]:
            rows.append([esc(r["player"]), esc(r["team"]), esc(g["date"]), esc(g["matchup"]),
                         num(g["min"], 0), num(g["pts"], 0), num(g["reb"], 0), num(g["ast"], 0),
                         num(g["pra"], 0) if g.get("pra") is not None else NA,
                         num(g["fg3m"], 0) if g.get("fg3m") is not None else NA,
                         ("<em>cut at the page-chunk boundary - later cells unreadable, not zero</em>"
                          if g["row_cut_at_chunk_boundary"] else "complete"),
                         srclink_url(g["box_url"], "official box score")])
    b.append(table(["Player", "Team", "Date", "Matchup", "MIN", "PTS", "REB", "AST", "PRA", "3PM",
                    "Row state", "Source"], rows,
                    note="40 rows read from %d official pages. A row marked <em>cut</em> is excluded from every "
                         "statistic that needs the missing cells, and included for points and minutes, which sit "
                         "left of the cut. PRA is points + rebounds + assists from the same row."
                         % hl["players_captured"]))

    b.append(h2("4. Which anchor forecasts a player better",
                "The question the whole props module depends on: should a projection start from the season "
                "average, from recent form, or from the last game?"))
    rows = []
    for a in v["anchor_test"]:
        def cell(d):
            if not d or d.get("n") in (0, None):
                return NA
            return "%s (%s rows)" % (num(d["mae"], 2), d["n"])
        rows.append([esc(a["stat"]), cell(a["season_avg_baseline"]), cell(a["leave_one_out_window_mean"]),
                     cell(a["previous_game"]), cell(a["official_header_average"]),
                     ("season average wins by %s points" % num((a["leave_one_out_window_mean"]["mae"] or 0) -
                                                                (a["season_avg_baseline"]["mae"] or 0), 2))
                     if a["stat"] == "PTS" and a["season_avg_baseline"].get("mae") else "see the note",
                     nomark("derived - scored on the official rows of section 3")])
    b.append(table(["Stat", "Season average", "Recent-form mean (leave-one-out)", "Previous game",
                    "Official page average", "Verdict on points", "Source"], rows,
                    note="<b>Read this carefully.</b> All three forecasts are scored on the same captured games. "
                         "The season average is contaminated - those games are inside it - and it sees 10-12 games "
                         "while the leave-one-out form mean sees three. So the honest result is narrow: on this "
                         "sample, <b>throwing away season data for a three-game window makes the forecast worse, and "
                         "chasing the single previous game makes it worse still</b> (points MAE %s vs %s vs %s). "
                         "It is not evidence that the season average is the best possible anchor, and it is not "
                         "evidence that a properly weighted blend would lose - that test needs a longer logged "
                         "window, which is what the remaining capture would buy."
                         % (num(v["anchor_test"][0]["season_avg_baseline"]["mae"], 2),
                            num(v["anchor_test"][0]["leave_one_out_window_mean"]["mae"], 2),
                            num(v["anchor_test"][0]["previous_game"]["mae"], 2))))

    b.append(h2("5. Minutes to production - the rotation number the injury module was missing",
                "Within-player, pooled: how much of a player's game-to-game production swing travels with the "
                "minutes he actually played."))
    rows = []
    for m, e in zip(v["minutes_to_production"], v["minutes_elasticity"]):
        rows.append([esc(m["stat"]), num(m["n_rows"], 0), num(m["rho"], 3), num(m["rho_squared"], 3),
                     num(m["t_statistic"], 2),
                     ("&lt;0.0001" if (m["p_value_two_sided"] is not None and m["p_value_two_sided"] < 0.001)
                      else num(m["p_value_two_sided"], 4)),
                     num(e["beta_minutes_to_production"], 3), num(e["standard_error"], 3),
                     esc(m["reading"]),
                     nomark("derived - every input cell is an official row of section 3")])
    b.append(table(["Stat", "Rows", "rho with minutes", "R squared", "t", "p (two-sided)",
                    "Beta (elasticity)", "SE of beta", "Reading", "Source"], rows,
                    note="Deviations are taken from each player's own mean before pooling, so a starter's level "
                         "cannot masquerade as a minutes effect. Beta is a pooled within-player regression of "
                         "relative production on relative minutes: <b>a 10%% cut in minutes predicts a %.1f%% cut in "
                         "points</b> and a %.1f%% cut in PRA, while assists barely move with minutes at all. That "
                         "matters for the injury module, which currently applies a declared production-transfer "
                         "rule of 0.55 with no measured figure behind it (see its <code>model_assumptions</code>): "
                         "points transfer at roughly one-for-one with minutes, rebounds and assists do not, so a "
                         "flat 0.55 is too small for a scorer and too large for a passer. It is a fitted sample of "
                         "%d rows from 10 players, not a league fit."
                         % (abs(v["minutes_elasticity"][0]["beta_minutes_to_production"]) * 10,
                            abs([e for e in v["minutes_elasticity"] if e["stat"] == "PRA"][0]["beta_minutes_to_production"]) * 10,
                            v["minutes_to_production"][0]["n_rows"])))

    b.append(h2("6. Same-game pairs - why the parlay rho stays an assumption",
                "Every pair of captured players who shared a game, correlated on their deviations from their own "
                "means."))
    rows = []
    for c in v["same_game_correlations"]:
        rows.append([esc(c["leg_a"]), esc(c["leg_b"]), esc(c["relationship"]), num(c["games_shared"], 0),
                     num(c["rho_points"], 3), num(c["rho_pra"], 3),
                     esc(c["reading"]),
                     srclink_url("https://www.nba.com/games?date=2026-11-14", "official games")])
    b.append(table(["Leg A", "Leg B", "Relationship", "Games shared", "rho points", "rho PRA", "Reading",
                    "Source"], rows,
                    note="<b>The measured answer is that rho cannot be measured from this window.</b> The best pair "
                         "shares three games, and a three-point correlation can be anything - the Denver pair reads "
                         "%s on points while pairs with two or one shared games read as noise. The correlations page "
                         "therefore keeps pricing same-game parlays with its declared rho, and this table is the "
                         "evidence for why that number is labelled an assumption instead of a measurement. A usable "
                         "estimate needs 30-50 shared games per pair, which means a full-season game-log capture, not "
                         "a Last-5 block." % num([c for c in v["same_game_correlations"] if c["rho_points"] is not None][0]["rho_points"], 2)
                    if v["same_game_correlations"] else None))

    n_recon = sum(1 for x in v["baseline_staleness"] if (x.get("reconciliation") or "").startswith("EXPLAINED"))
    n_bad = sum(1 for x in v["baseline_staleness"] if (x.get("reconciliation") or "").startswith("NOT"))
    b.append(h2("7. Are the site's season averages stale?",
                "The props baseline was transcribed on 2026-11-13. Recomputing it from the captured games should "
                "reproduce what the official player page prints now."))
    rows = []
    for r in v["baseline_staleness"]:
        rows.append([esc(r["player"]), esc(r.get("team") or ""), num(r.get("gp_at_capture"), 0),
                     num(r.get("site_season_ppg_used")), num(r.get("official_ppg_now")),
                     num(r.get("delta"), 2), num(r.get("rel"), 3),
                     esc(r.get("reconciliation") or r.get("status") or ""),
                     srclink_url("https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame&dir=-1&sort=PTS",
                                  "official season table")])
    b.append(table(["Player", "Team", "GP at capture", "Site PPG", "Official PPG now", "Delta", "Relative",
                    "Reconciliation", "Source"], rows,
                    note="%d of %d reconcile, %d do not: the difference between the number this site published and "
                         "the number NBA.com prints now is exactly the games played since the capture, within the "
                         "rounding of a one-decimal average. So the staleness is <em>arithmetically explained</em> "
                         "rather than suspicious - but it is still staleness: every prop on the horizon is anchored "
                         "one to two games behind the league, and the tolerance that makes the check meaningful "
                         "rather than decorative is 0.05 x (1 + gp / gp+g) points, about 0.1 of a point here."
                         % (n_recon, len(v["baseline_staleness"]), n_bad)))

    b.append(h2("8. What the injury report changed after the lines were cut",
                "The newest official edition against the edition the horizon lines were originated from."))
    inj = v["injury_delta"]
    rows = []
    for g in inj["games_affected"]:
        rows.append([esc(g["matchup"]), esc(g["game_id"]), num(g["n_new_or_changed_rows"], 0),
                     esc(", ".join(g["players"]) or "none"), esc(g["report_state_at_line_build"]),
                     esc(g["line_originated"]), esc(g["note"]),
                     srclink_url(inj["new_edition"], "%s edition" % inj["new_stamp"])])
    b.append(table(["Game", "Game ID", "New or changed rows", "Players", "Report state when the line was cut",
                    "Originated line", "Reading", "Source"], rows,
                    note="Nothing changed for any 11/14 game between the 11/13 05:15 PM ET edition the lines were "
                         "built from and the newest edition read at 10:30 UTC (%s). That is a clean result, and it is "
                         "also the limit of it: at this edition five of the ten teams on the slate had still not "
                         "filed (%s), so the game-day confirmation the league rule asks for (11 a.m.-1 p.m. local) "
                         "had not happened yet. Any prop or line for those games is priced against a half-filed "
                         "report." % (inj["new_stamp"], ", ".join(inj["teams_not_yet_submitted_at_this_edition"]))))
    if inj["rows_changed_or_new"]:
        rows = []
        for d in inj["rows_changed_or_new"]:
            rows.append([esc(d["matchup"]), esc(d["team"]), esc(d["player"]), esc(d["status_new"]),
                         esc(d.get("status_in_site_edition") or ""), esc(d["change"]),
                         srclink_url(inj["new_edition"], "official edition")])
        b.append(table(["Game", "Team", "Player", "Status now", "Status in the site's edition", "Change",
                        "Source"], rows,
                        note="These rows are new or changed since the edition the site published; they are the "
                             "items a reviewer should look at before trusting the affected line."))

    b.append(h2("9. Independent second read of the same pages",
                "A separate session captured three of these players nine hours earlier from the same official URLs. "
                "Overlapping rows are compared cell for cell."))
    rows = []
    for c in v["cross_check_against_earlier_read"]:
        if "result" in c:
            rows.append([esc(c["player"]), NA, NA, NA, esc(c["result"])])
            continue
        rows.append([esc(c["player"]), num(c["rows_compared_and_agreeing"], 0),
                     num(len(c["disagreements"]), 0), num(len(c["rows_only_one_side_could_read"]), 0),
                     esc(c["window_shift"]), ])
    b.append(table(["Player", "Rows agreeing", "Disagreements", "Readable by one side only", "Note", "Source"],
                   [[r[0], r[1], r[2], r[3], r[4],
                     srclink_url("https://www.nba.com/games?date=2026-11-14", "official games")] for r in rows],
                   note="Zero disagreements. The earlier read carries an older window because it was taken before "
                        "the 11/13 games finished, which is exactly the difference between the two files - so the "
                        "agreement is a check on the transcription, not on the schedule."))

    b.append(h2("10. What is not here, and what would finish it", "Stated as a list of gaps, with the page each gap needs."))
    rows = []
    for n in v["not_captured"]:
        rows.append([esc(n["player"]), esc(n.get("team") or ""), esc(n.get("date") or ""), esc(n["reason"]),
                     srclink_url("https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame&dir=-1&sort=PTS",
                                 "nba.com season table - id source")])
    b.append(table(["Not captured", "Team", "Dates", "Why", "Source"], rows,
                   note="The blocker for the four 11/14 players is not the game-log page, it is the player id: no "
                        "committed capture in this repo carries an NBA.com id for them, and this session does not "
                        "guess one. The fix is one roster-page read per team, after which the same script prices "
                        "them with no further work. The 36 remaining horizon prop rows fail for the same reason "
                        "plus volume, not method."))


    b.append(h2("11. Today&#39;s designations, sized against the rule that moves a line",
                "The desk question is not who is out, it is whether the originated line should change. Under this "
                "repo&#39;s canonical rule only a verifiable NEW_ABSENCE moves one, because a player already missing "
                "for most of the sample is inside the team&#39;s own season numbers."))
    rows = []
    for x in v["availability_readout"]:
        rows.append([esc(x["matchup"]), esc(x["team"]), esc(x["player"]), esc(x["status"]),
                     esc(x["reason"]), esc(x["team_record_printed"]), num(x["team_games"], 0),
                     num(x["season_gp"], 0), num(x["games_already_missed"], 0),
                     num(x["season_min"]), num(x["season_pts"]),
                     num(x["play_probability"], 2), esc(x["absence_class"]),
                     '<b>%s</b>' % esc(x["line_moves"]),
                     srclink_url(x["injured_source"], "official report")])
    b.append(table(["Game", "Team", "Player", "Status", "Reason", "Team record", "Team games", "Player GP",
                    "Games already missed", "Season min", "Season pts", "P(play)", "Absence class",
                    "Line moves", "Source"], rows,
                    note="%d designations printed for the 2026-11-14 games. <b>%d of them move a line, and %d "
                         "cannot be sized at all</b> because the player sits outside every captured player table - "
                         "the official Per Game table in this repo covers 50 names, and a two-way or G-League "
                         "assignment is not in it. The one fully measurable case is Anthony Edwards (Out, right knee "
                         "arthroscopy): he has played 4 of Minnesota&#39;s 12 games, so his absence is already inside "
                         "the season ratings the CHI@MIN line was built from, and re-cutting the line for him would "
                         "count the same absence twice. That is the whole reason this report does not move today&#39;s "
                         "lines - it is not a claim that he is replaceable. Where a measured figure is wanted for a "
                         "genuinely new absence, section 5&#39;s elasticity is the number to use: losing a full "
                         "minutes share predicts about 1.29x his own scoring loss, not the flat 0.55 the injury "
                         "module carries today."
                         % (hl["designations_today"], hl["lines_that_move_today"],
                            hl["designations_unmeasurable"])))
    b.append(banner("info", "Files behind this page",
                    "<ul>"
                    "<li><code>data/proplogs/2026-11-14/captures.json</code> - the row-for-row transcription, one "
                    "source URL per player and per game.</li>"
                    "<li><code>data/proplogs/2026-11-14/injury_2026-11-14_04_30AM.json</code> - the newest official "
                    "injury edition, 31 printed rows for the 11/14 slate.</li>"
                    "<li><code>data/derived/prop_variance.json</code> - everything rendered above, as data.</li>"
                    "<li><code>scripts/prop_variance.py</code> - the computation, with its declared modelling "
                    "choices at the top of the file.</li>"
                    "</ul>"))
    return page("Prop variance and rotation",
                "Game-to-game dispersion measured from official NBA.com game logs for the 2026-11-14 slate cohort: "
                "the uncertainty behind every prop, the minutes-to-production elasticity, and the injury delta "
                "between editions. Read %s." % esc(v["_meta"]["generated_utc"]), "\n".join(b))


def link_repo(path, label):
    """Link into the repository. Used only for files inside this repo, never as a data source."""
    return ('<a href="https://github.com/wingbangboozle1-lang/NBA1/blob/main/%s" target="_blank" '
            'rel="noopener">%s</a>' % (esc(path), esc(label)))


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

    # ---- what the 18:40Z live re-read changed (session arena/cc5a6652-nba1) ----------
    _cmp = load(os.path.join(ROOT, "verify", "2026-11-14-cc5a6652", "compare.json"))
    _c = _cmp["counts"]
    body.append(card("Verified again at 18:40Z today &mdash; what moved", (
        '<p class="lead">Every official value this site publishes was read again on '
        '2026-11-14 between 18:40Z and 19:10Z and compared, row by row, with what is published '
        'here: <strong>%d checks, %d match, %d differ</strong>. The rows that differ are explained '
        'one at a time on the <a href="site/pages/official-verify.html">Live Re-verification</a> '
        'page, each with the official link it was read from.</p>'
        '<ul class="findings">'
        '<li><b>The nine 2026-11-13 finals, the 27 horizon games and every record printed on them '
        '&mdash; all 63 rows match the official pages exactly.</b> No defect. '
        '<span class="fine">Sections A, B and C of the verification page.</span></li>'
        '<li><b>A real defect, found and fixed: the site was publishing an older copy of three '
        'decision files.</b> It showed 39 flags, 13 answered + 18 open questions and 16 suggestions '
        'while the repository held 46, 15 + 19 and 18. The build now copies the authored files from '
        '<code>data/content</code> on every run and fails loudly if one is missing. '
        '<span class="fine">R-30-1 in the task board.</span></li>'
        '<li><b>The site prices availability from a nine-hour-old injury edition.</b> The newest '
        'edition on the official index is 01:30 PM ET; the site uses 04:15 AM ET, and 33 status lines '
        'changed in between. Four of the five teams the site marks &ldquo;had not filed&rdquo; had '
        'filed. Every line now carries the edition it came from and says <em>not re-priced</em>. '
        'Re-cutting them is decision <a href="site/pages/decisions.html">P1</a>.</li>'
        '<li><b>19 of 30 teams moved between the published ratings window and the live Teams '
        'Advanced page</b>, because the live page now includes 11/13. The lines were computed from '
        'the older window, so re-basing the ratings alone would make two pages disagree: the live '
        'value is published beside the used one and nothing was re-cut. Which set is official is '
        'decision <a href="site/pages/decisions.html">P2</a>.</li>'
        '<li><b>The 18:40Z standings read disagreed with the committed copy on 18 of 30 teams '
        '&mdash; and the site was right.</b> The committed capture was taken at 00:45Z, before the '
        '11/13 finals. Verified, not assumed.</li>'
        '<li><b>All 18 published backtest metrics and the whole S1 headline were re-derived from '
        'the repository\'s own rows: 18 of 18 reproduce exactly</b>, including 23-9 = +11.909 units '
        'at -110, Wilson 95%% [0.5463, 0.8444] and an exact binomial p of 0.0201.</li>'
        '</ul>'
        '<p class="fine">Read live: %s. Artifact: '
        '<code>verify/2026-11-14-cc5a6652/compare.json</code>.</p>'
        % (_c["checks"], _c["match"], _c["differ"], esc(_cmp["read_at_utc"]))
    ), "exec"))

    body.append(card("Where to go next", (
        '<p><b>If you are deciding what to build:</b> start at '
        '<a href="site/pages/decisions.html">Decisions: pick a path</a> &mdash; six decisions in '
        'dependency order, every open question mapped to the one that closes it, and every '
        'suggestion ranked against them.</p>'
        '<p><b>If you are checking a number:</b> <a href="site/pages/official-verify.html">Live '
        'Re-verification</a> for official values, '
        '<a href="site/pages/validation.html">Validation</a> for the gates and the statistics, '
        '<a href="site/pages/flagged.html">Flagged for Review</a> for everything that could not be '
        'confirmed.</p>'
        '<p><b>If you want tonight\'s games:</b> <a href="site/pages/picks.html">Lines &amp; '
        'Picks</a>, then <a href="site/pages/injuries.html">Injuries &amp; Rotation</a> for what '
        'could change the rotation, then <a href="site/pages/gameflow.html">Game Flow</a> for pace '
        'and blow-out risk. No pick on this site is a betting recommendation.</p>'
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

    body.append(card("Every build in this repository (none deleted)",
                     '<p>Several implementations of the same brief exist here. All are preserved and all are '
                     'online, so the audit trail stays intact. They read the same official captures and differ '
                     'only in presentation, data cut and how much of the pipeline they exercise. The pages '
                     'above are the current build; the rest are reachable from here.</p>'
                     '<ul class="plain">'
                     '<li><b>Current &mdash; this build.</b> The 27-game 14&ndash;17 Nov horizon, 60 gated paper picks, '
                     'the 11/14/26 04:15 AM ET injury edition, and the full strategy/evidence set. '
                     '<a href="site/pages/picks.html">Open the horizon</a>.</li>'
                     '<li><a href="command-center/index.html">Command Center</a> &mdash; a second consolidated '
                     'site built in session <code>arena/791c9114-nba1</code> from the same official captures. '
                     'It carries a narrower 22-game 14&ndash;16 Nov cut and its own rendered-page checks '
                     '(<code>check_rendered.py</code>), which this build does not have.</li>'
                     '<li><a href="edge-lab/index.html">Edge Lab</a> &mdash; Build A, the original decision '
                     'dashboard, frozen at the 11/13 data cut and archived unchanged under '
                     '<code>edge-lab/</code>. It carries the Integration Desk section added by session '
                     '<code>arena/2edb85af-nba1</code>.</li>'
                     '<li><a href="desk.html">Integration Desk</a> &mdash; the origination, gate, settlement '
                     'and prop pipeline published at the repository root by session '
                     '<code>arena/2edb85af-nba1</code>, with its own cross-check and settlement scripts.</li>'
                     '<li><a href="docs/index.html">Dated NBA data snapshot</a> &mdash; Build A\'s dated '
                     '13&ndash;15 Nov schedule and 12:00 PM injury-report transcription with every source link.</li>'
                     '<li><a href="docs/b/index.html">Line Origination Desk</a> &mdash; Build B, the earlier '
                     'backtested build (the full out-of-sample window, ten strategies, seven gates).</li>'
                     '<li><a href="picks-2026-11-14.html">Horizon picks 14&ndash;17 Nov (Build D, session '
                     '<code>arena/ebdf1d21-nba1</code>)</a> &mdash; RecordLine-1 picks regenerated with the newest '
                     'official injury edition (11/13 08:00 PM ET), a 22/22 fidelity check against the archived '
                     'Edge Lab lines, and flagged items D-01&ndash;D-11.</li>'
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

    m = back["metrics"]
    b.append(h2("Measured on the out-of-sample window", "The model against the naive reference, on %d games played after the ratings cut-off." % m["n_games"]))
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
                     "that went 23-9 might have been right 23 times, or might have been right 17 times and been "
                     "lucky 6. The gate that tests this is G4, and S1 (23-9) is the first strategy to clear it "
                     "(exact binomial p = 0.020) - which is why it is finally allowed to be called something "
                     "other than luck. It is still capped by the calibration and stability gates it did not "
                     "clear."))
    built["luck.html"] = page("Luck and skill",
                               "How many wins each team probably should have had, and which records are luck "
                               "rather than skill.", "\n".join(b))

    # === backtest ===========================================================
    _w0, _w1 = back["metrics"]["window"].split(" .. ")
    b = [h2("Out-of-sample window", "Every completed game from %s to %s, predicted using ratings computed only from 2026-10-20 to 2026-11-05. No game in the test window contributes to the ratings that predict it." % (_w0, _w1))]
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

    # --- settlement of the previous slate's published paper picks -----------
    settle_path = os.path.join(RAW, "s14", "settlement_2026-11-13.json")
    if os.path.exists(settle_path):
        with open(settle_path, encoding="utf-8") as fh:
            st = json.load(fh)
        pre_ok = st["preregistration_check"]["model_blocks_identical_to_live_file"]
        b.append(h2("Settlement - the 2026-11-13 slate",
                    "Every paper pick published before the 2026-11-13 tip-off, settled against the official "
                    "finals. Pre-registration check against the copy frozen at 2026-11-13T22:45Z: %s."
                    % ("pass" if pre_ok else "FAIL")))
        rows = []
        for r in st["singles"]:
            rows.append([esc(r.get("date")), esc(r.get("matchup")), esc(r.get("pick_side")),
                         esc(r.get("pick_line")) if r.get("pick_line") else NA,
                         esc(r.get("gate")),
                         esc("%d-%d" % (r["away_pts"], r["home_pts"])) if r.get("away_pts") is not None else NA,
                         esc(r.get("result")), num(r.get("units"), 2),
                         srclink_url(r.get("source_game_url"), "official final")])
        b.append(table(["Date", "Matchup", "Pick", "Line", "Gate at publication",
                        "Final (away-home)", "Result", "Units (-110)", "Source"], rows,
                       note="Singles units use the repo's standing -110 convention (win +1.00, loss -1.10); "
                            "this is a convention, not a market price (flag F3). Picks that failed their gate "
                            "at publication are recorded as NO BET and worth 0.00."))
        rows = []
        for p in st["parlays"]:
            legs = "; ".join("%s %s" % (l["leg"], l["result"]) for l in p["legs"])
            rows.append([esc(p.get("date")), esc(legs), esc(p.get("result")), NA,
                         esc(p.get("units_note")),
                         srclink_url(p["legs"][0].get("source_game_url"), "official final")])
        b.append(table(["Date", "Legs", "Result", "Units", "Note", "Source"], rows))
        s_ = st["summary"]
        b.append(banner("info", "Slate result",
                        "Gated singles %s (%+.2f units at -110, %d no-bets); two-leg parlays %d-%d. "
                        "The originated margin line missed by %.2f points on average across the nine games - "
                        "consistent with the window-wide MAE, and a reminder that a night like this is normal "
                        "at this sample size."
                        % (s_["record"], s_["units_at_minus110"], s_["no_bets"], s_["parlays_won"],
                           s_["parlays_published"] - s_["parlays_won"], s_["model_margin_mae_on_slate"])))
    built["backtest.html"] = page("Out-of-sample backtest",
                                   "The full test window, every game in it, the parameters the model "
                                   "was fitted on, and the settlement of the previous slate's paper picks.",
                                   "\n".join(b))

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
    b.append(table(["ID", "Question", "Answer", "Confidence", "Source"], rows,
                   anchor_pattern=r"^A\d+$"))
    b.append(h2("Open", "Questions that cannot be answered yet. Nothing on this site is decided on an open question."))
    rows = []
    for q in questions["open"]:
        rows.append([esc(q["id"]), '<b>%s</b>' % esc(q["question"]), esc(q.get("what_is_missing")),
                     esc(q.get("how_to_answer")), esc(q.get("blocks")),
                     esc(q.get("priority")),
                     srclink(sources, q.get("source")) if q.get("source")
                     else nomark(q.get("source_url") or "no official source exists")])
    b.append(table(["ID", "Question", "What is missing", "How to answer it",
                     "What it blocks", "Priority", "Source"], rows, anchor_pattern=r"^Q\d+$",
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
                    "Decision needed", "Source"], rows, anchor_pattern=r"^SG\d+$"))
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

    # === official source check (session arena/b0f2cc98-nba1, COORDINATION §23) =====
    built["source-check.html"] = build_source_check(sources)

    # === prop variance (session arena/24eb72c6-nba1, COORDINATION section 24) =====
    built["prop-variance.html"] = build_prop_variance()

    # === live re-verification (session arena/cc5a6652-nba1, COORDINATION section 30) ===
    built["official-verify.html"] = build_official_verify()

    # === decisions (session arena/cc5a6652-nba1) =================================
    built["decisions.html"] = build_decisions(questions, suggestions)

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
    # R-30-1: three decision files had gone stale in docs/data. data/content is the authored
    # source (build_site.py writes it) and the site had been publishing an older copy: 39 flags
    # against 46, 13 answered + 18 open questions against 15 + 19, 16 suggestions against 18.
    # The site must not silently publish less than the repository holds, so the authored copy wins
    # every time the site is built. Each file is named explicitly so a failure is loud.
    for _f in ("flagged.json", "questions.json", "suggestions.json", "executive.json"):
        _src = os.path.join(CONTENT, _f)
        if not os.path.exists(_src):
            raise SystemExit("missing authored content file: %s" % _src)
        shutil.copyfile(_src, os.path.join(DATA, _f))
        shutil.copyfile(_src, os.path.join(SITE_DATA, _f))
        _d = json.load(open(_src))
        _n = (len(_d["items"]) if "items" in _d
              else len(_d["answered"]) + len(_d["open"]) if "answered" in _d
              else len(_d.get("sections", [])) or 1)
        print("content: %-16s %3d items  (data/content -> docs/data + site/data)" % (_f, _n))
    for f in os.listdir(DATA):
        shutil.copyfile(os.path.join(DATA, f), os.path.join(SITE_DATA, f))
    shutil.copyfile(os.path.join(RAW, "sources.json"), os.path.join(SITE_DATA, "sources.json"))
    shutil.copyfile(os.path.join(ROOT, "data", "d", "repo_review.json"),
                    os.path.join(SITE_DATA, "repo_review.json"))
    pv = os.path.join(ROOT, "data", "derived", "prop_variance.json")
    if os.path.exists(pv):
        shutil.copyfile(pv, os.path.join(SITE_DATA, "prop_variance.json"))

    print("Wrote %d pages, assets and data to %s" % (len(built), SITE))


if __name__ == "__main__":
    main()
