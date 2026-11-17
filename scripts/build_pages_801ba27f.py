#!/usr/bin/env python3
"""Render the 2026-11-15 re-cut pages.

    python3 scripts/build_pages_801ba27f.py

Session `arena/801ba27f-nba1`, COORDINATION.md §41 task H06.

Every page is static HTML generated from the JSON this session derived from
official captures. Three rules are enforced here, not assumed downstream:

  * a missing value renders as an em dash, never as the string "None";
  * every data row carries an <a> to the official page it came from;
  * the projection surface and the bet surface are separate pages and are
    never merged into one table.
"""

import datetime
import re
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, "site", "pages")
DERIVED = os.path.join(ROOT, "data", "derived")
OFFICIAL = os.path.join(ROOT, "data", "official")
INJ = os.path.join(ROOT, "data", "injury_reports")
SETTLE = os.path.join(ROOT, "data", "settlement")

RUN_UTC = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
DASH = "—"

NAV = [
    ("2026-11-15 RE-CUT", [
        ("official-feed.html", "Official result feed"),
        ("estimators.html", "Two estimators"),
        ("projection.html", "Projection surface"),
        ("bet-surface.html", "Bet surface (gated)"),
        ("parlay-pricing.html", "Parlay pricing"),
        ("rotation.html", "Minutes redistribution"),
        ("rest-travel.html", "Rest &amp; travel"),
        ("luck-z.html", "Luck z-scores"),
        ("injury-ledger.html", "Injury PDF ledger"),
        ("settlement.html", "Settlement &amp; ledger"),
        ("brief-coverage.html", "Requirements coverage"),
    ]),
    ("HORIZON", [
        ("picks.html", "Lines &amp; Picks"),
        ("props.html", "Player Props"),
        ("injuries.html", "Injuries &amp; Rotation"),
        ("gameflow.html", "Game Flow"),
    ]),
    ("EVIDENCE", [
        ("strategies.html", "Strategies &amp; Leaderboard"),
        ("validation.html", "Validation Gates"),
        ("correlations.html", "Correlations"),
        ("luck.html", "Luck &amp; Skill"),
        ("backtest.html", "Out-of-Sample Backtest"),
        ("model.html", "Model &amp; Teams"),
    ]),
    ("DECISION", [
        ("questions.html", "Open Questions"),
        ("suggestions.html", "Suggestions"),
        ("decisions.html", "Decisions: pick a path"),
        ("flagged.html", "Flagged for Review"),
        ("sources.html", "Source Register"),
        ("../../EXECUTIVE_SUMMARY.md", "Executive Summary"),
    ]),
]


def esc(x):
    return html.escape(str(x), quote=True)


def val(x, suffix=""):
    """Render a value; a missing one is an em dash, never the word 'None'."""
    if x is None or x == "" or (isinstance(x, float) and x != x):
        return DASH
    if isinstance(x, float):
        return ("%g" % round(x, 4)) + suffix
    return str(x) + suffix


def jload(p):
    with open(p) as fh:
        return json.load(fh)


def page(title, subtitle, body, active=None):
    navhtml = []
    for group, links in NAV:
        items = "".join(
            '<a href="%s"%s>%s</a>' % (u, ' class="active"' if u == active else "", t)
            for u, t in links)
        navhtml.append('<div class="nav-group"><h3>%s</h3>%s</div>' % (group, items))
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s &middot; NBA1</title>
<link rel="stylesheet" href="../assets/site.css">
<style>
/* Session-scoped additions (arena/801ba27f-nba1). The shared stylesheet is owned by
   other sessions, so these classes are injected here instead of added there. */
.note{margin:0 0 18px;padding:12px 14px;border:1px solid var(--line);border-left:3px solid var(--ink3);
      border-radius:8px;background:var(--panel);font-size:13px;line-height:1.6;max-width:100ch}
.note.ok{border-left-color:#2e9e5b}.note.bad{border-left-color:#c0392b}.note.warn{border-left-color:#d98b0a}
.note strong{color:var(--ink)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px}
.lede{color:var(--ink2);max-width:92ch;margin:0 0 22px;line-height:1.55}
.foot{margin-top:28px;font-size:12px;color:var(--ink2)}
.tablewrap{overflow-x:auto;margin:0 0 22px}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <div class="wrap topbar-in">
    <a class="brand" href="../../index.html">
      <span class="mark">NBA1</span>
      <span class="brand-txt">Originated lines &amp; strategy lab</span>
    </a>
    <nav class="topnav">
      <a href="picks.html">Horizon</a>
      <a href="projection.html">Projection</a>
      <a href="bet-surface.html">Bet (gated)</a>
      <a href="decisions.html">Decisions</a>
      <a href="flagged.html">Flagged</a>
    </nav>
  </div>
</header>
<div class="wrap layout">
  <aside class="sidebar">
    <div class="side-h">Sections</div>
    %s
    <div class="side-note">
      <strong>Reading rule.</strong> Every row links to the official page the value
      came from. A blank cell means the value could not be confirmed on an official
      page and is flagged, never filled in.
    </div>
  </aside>
  <main id="main">
    <h1>%s</h1>
    <p class="lede">%s</p>
%s
    <p class="foot">Built %s by session <code>arena/801ba27f-nba1</code>.
    <a href="https://www.nba.com/games">www.nba.com/games</a> &middot;
    <a href="https://official.nba.com/nba-injury-report-2026-27-season/">official injury index</a></p>
  </main>
</div>
</body>
</html>
""" % (esc(title), "\n    ".join(navhtml), esc(title), subtitle, body, RUN_UTC)


def table(headers, rows, source_urls=True):
    """rows: list of list of cell-html strings; the last column holds links."""
    out = ['<div class="tablewrap"><table><thead><tr>']
    out.append("".join("<th>%s</th>" % h for h in headers))
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def link(url, text=None):
    if not url:
        return DASH
    return '<a href="%s">%s</a>' % (esc(url), esc(text or "source"))


def note(cls, text):
    return '<div class="note %s">%s</div>' % (cls, text)


# ------------------------------------------------------------------ pages
def build_official_feed():
    d = jload(os.path.join(OFFICIAL, "results_feed_2026_27.json"))
    rows = []
    for r in d["rows"]:
        qh = " / ".join(str(x) for x in (r["home_quarters"] or [])) or DASH
        qa = " / ".join(str(x) for x in (r["away_quarters"] or [])) or DASH
        rows.append([r["date"], r["away"], r["home"],
                     val(r["away_pts"]) + " – " + val(r["home_pts"]),
                     qa, qh, val(r["ot_periods"]),
                     r["game_status_text"] or DASH,
                     link(r["source_url"], "box score")])
    body = [
        note("ok", "<strong>%d</strong> games on the official feed, of which "
                   "<strong>%d</strong> are Final. Quarter scores sum to the final on "
                   "every Final game (%s)."
             % (d["count"], d["count_final"],
                "no assertion failures" if not d["quarter_sum_assertion_failures"]
                else "failures: " + ", ".join(d["quarter_sum_assertion_failures"]))),
        table(["Date", "Away", "Home", "Final", "Away quarters", "Home quarters",
               "OT", "Official status", "Source"], rows),
    ]
    return page("Official result feed", "One row per game: date, teams, final score, "
                "quarter scores. Settled only from an official Final.",
                "".join(body), "official-feed.html")


def build_estimators():
    e = jload(os.path.join(DERIVED, "estimators_2026_27.json"))
    c = jload(os.path.join(DERIVED, "measured_constants_2026_27.json"))
    rows = []
    for r in e["rows"]:
        rows.append([r["date"], r["away"] + " @ " + r["home"],
                     val(r["e1_spread_home"]), val(r["e1_total"]),
                     val(r["e2_spread_home"]), val(r["e2_total"]),
                     "<strong>%s</strong>" % val(r["disagreement_spread"]),
                     "<strong>%s</strong>" % val(r["disagreement_total"]),
                     val(r["blend_spread_home"]), val(r["blend_total"]),
                     link(r["source_url"], "game")])
    body = [
        note("info", "<strong>The disagreement is the headline.</strong> The blend is "
                     "printed underneath it and is never the headline number. Where the "
                     "two estimators disagree by a lot, the projection is not trustworthy "
                     "— and the site says so instead of averaging it away."),
        note("ok", "Home court is <strong>pinned, not fitted</strong>: the measured "
                   "home-win rate is <strong>%s</strong> over <strong>%d</strong> official "
                   "finals, which is <strong>%s</strong> points under the empirical margin "
                   "distribution (sigma %s)."
             % (val(c["home_win_rate"]), c["n_final_games"],
                val(c["home_court_points"]), val(c["sigma_margin"]))),
        "<h2>Estimator 1 — possessions × points per possession</h2>",
        "<p class='mono'>%s</p>" % esc(e["estimator_1"]),
        "<h2>Estimator 2 — score-based, independent information set</h2>",
        "<p class='mono'>%s</p>" % esc(e["estimator_2"]),
        table(["Date", "Game", "E1 spread", "E1 total", "E2 spread", "E2 total",
               "Δ spread", "Δ total", "Blend spread", "Blend total", "Source"], rows),
    ]
    return page("Two estimators and their disagreement",
                "Two independent constructions of the same line. The gap between "
                "them is the confidence signal.", "".join(body), "estimators.html")


def build_projection():
    d = jload(os.path.join(DERIVED, "horizon_lines_801ba27f.json"))
    rows = []
    for r in d["rows"]:
        ra = r["rotation_availability_away"] or {}
        rh = r["rotation_availability_home"] or {}
        rows.append([r["date"], r["matchup"], r["status_official"] or DASH,
                     val(r["e1_spread_home"]), val(r["e1_total"]),
                     val(r["e2_spread_home"]), val(r["e2_total"]),
                     val(r["disagreement_spread"]), val(r["disagreement_total"]),
                     val(r["blend_spread_home"]), val(r["blend_total"]),
                     val(r["rest_away"] and r["rest_away"]["rest_days"]),
                     val(r["rest_home"] and r["rest_home"]["rest_days"]),
                     val(ra.get("available_share")), val(rh.get("available_share")),
                     link(r["source_url"], "game")])
    body = [
        note("ok", "<strong>This is the projection surface.</strong> It is safe to "
                   "publish: originated lines only, no bet recommendation. The bet "
                   "surface is a separate page and is gated."),
        note("info", "Rotation availability is the minutes-weighted share of each "
                     "team's measured top-8 that is not ruled out on the official injury "
                     "report (%s). Rest days are counted from the official schedule and "
                     "official finals."
             % esc(d.get("injury_edition") or "the newest official edition")),
        table(["Date", "Game", "Official status", "E1 spr", "E1 tot", "E2 spr", "E2 tot",
               "Δ spr", "Δ tot", "Blend spr", "Blend tot", "Rest away", "Rest home",
               "Rot avail away", "Rot avail home", "Source"], rows),
    ]
    return page("Projection surface", "Originated lines for every game on the rolling "
                "slate. No bet recommendation lives here.", "".join(body),
                "projection.html")


def build_bet_surface():
    d = jload(os.path.join(DERIVED, "horizon_picks_801ba27f.json"))
    srows = []
    for s in d["singles"]:
        ra = s.get("rotation_availability") or {}
        srows.append([s["date"], s["matchup"], "<strong>%s</strong>" % esc(s["pick"]),
                      val(s["e1_spread_home"]), val(s["e2_spread_home"]),
                      val(s["disagreement_spread"]),
                      val(ra.get("available_share")),
                      ", ".join(ra.get("outs_in_top8") or []) or DASH,
                      val(s["luck_z"]), esc(s["luck_gate"]),
                      link(s["sources"][0], "game")])
    prows = []
    for p in d["parlays"]:
        prows.append([esc(p["leg1"]), esc(p["leg2"]), val(p["p1"]), val(p["p2"]),
                      val(p["rho_used"]),
                      "<strong>%s</strong>" % val(p["joint_prob_with_rho"]),
                      val(p["naive_independent_product_printed_beside"]),
                      val(p["fair_odds_with_rho"]),
                      link(p["sources"][0], "game 1")])
    grows = []
    for g in d["sgp_candidates"]:
        grows.append([g["date"], esc(g["game"]), esc(g["leg1"]), esc(g["leg2"]),
                      val(g["p1"]), val(g["p2"]), val(g["rho_used"]),
                      "<strong>%s</strong>" % val(g["joint_prob_with_rho"]),
                      val(g["naive_independent_product_printed_beside"]),
                      link(g["sources"][0], "game")])
    body = [
        note("warn", "<strong>GATE: %s</strong>" % esc(d["gate_status"])),
        note("info", "<strong>Market-anchored prior: %s</strong> — %s"
             % (esc(d["market_anchored_prior"]["status"]),
                esc(d["market_anchored_prior"]["reason"]))),
        "<h2>Singles — with rotation availability as its own column</h2>",
        table(["Date", "Game", "Pick", "E1 spr", "E2 spr", "Δ spr",
               "Rotation available", "Out (top-8)", "Luck z", "Luck gate", "Source"],
              srows),
        "<h2>Parlays — priced with the measured rho, naive product printed beside it</h2>",
        table(["Leg 1", "Leg 2", "p1", "p2", "rho used", "Joint (rho)",
               "Naive product", "Fair odds", "Source"], prows),
        "<h2>Same-game parlays — measured rho, naive product beside it</h2>",
        table(["Date", "Game", "Leg 1", "Leg 2", "p1", "p2", "rho used",
               "Joint (rho)", "Naive product", "Source"], grows),
    ]
    return page("Bet surface (gated)", "Every ticket a strategy would place — "
                "published unfunded, with the gate status attached.",
                "".join(body), "bet-surface.html")


def build_parlay_pricing():
    d = jload(os.path.join(DERIVED, "horizon_picks_801ba27f.json"))
    r = jload(os.path.join(DERIVED, "rho_2026_27.json"))
    rrows = [[esc(m["pair"]), val(m["rho"]), val(m.get("n") or m.get("n_pairs")),
              esc(m["status"]), esc(m.get("note") or ""),
              link("https://www.nba.com/games", "official finals")]
             for m in r["measured"]]
    prows = []
    for p in d["parlays"]:
        prows.append([esc(p["leg1"]), esc(p["leg2"]), val(p["p1"]), val(p["p2"]),
                      val(p["rho_used"]), "<strong>%s</strong>" % val(p["joint_prob_with_rho"]),
                      val(p["naive_independent_product_printed_beside"]),
                      link(p["sources"][0], "game 1")])
    body = [
        note("bad", "<strong>Correction 2026-11-16 (F107, ledger entry 10).</strong> The first "
                    "publication of this page priced every parlay and same-game parlay three "
                    "times too high: the joint-probability routine used Simpson weights without "
                    "the h/3 factor, so joint probabilities above 1.000 were published "
                    "(ORL@BOS / MIL@MIA was printed as 1.6171 against a naive product of "
                    "0.5375). The factor has been restored, the routine was checked against two "
                    "closed forms, and every row below is recomputed and re-published, still "
                    "before the tip of the earliest game it covers. No single-leg ticket was "
                    "affected. Ledger entries 6 and 8 are superseded by entry 9."),
        note("ok", "Every parlay is priced with a <strong>measured</strong> rho and the "
                   "naive independent product is printed immediately beside it, so the "
                   "reader can see exactly what the correlation assumption is worth."),
        "<h2>The measured correlations</h2>",
        table(["Pair", "rho", "n", "Status", "Note", "Source"], rrows),
        "<h2>Prices</h2>",
        table(["Leg 1", "Leg 2", "p1", "p2", "rho", "Joint (rho)",
               "Naive product", "Source"], prows),
    ]
    return page("Parlay pricing", "Measured rho, with the naive product printed beside "
                "it instead of a single withheld price.", "".join(body),
                "parlay-pricing.html")


def build_rotation():
    d = jload(os.path.join(DERIVED, "rotation_2026_27.json"))
    rows = []
    for team, t in sorted(d["teams"].items()):
        top = t["top8"]
        cells = []
        for i in range(8):
            if i < len(top):
                cells.append("%s<br><span class='mono'>%s</span>"
                             % (esc(top[i]["player"]), val(top[i]["minutes_share"])))
            else:
                cells.append(DASH)
        rows.append(["<strong>%s</strong>" % team, val(t["games_used"]),
                     esc(t["window"] or DASH)] + cells +
                    [val(t["bench_share_outside_top8"]),
                     link("https://www.nba.com/games", "official box scores")])
    ex = None
    for team, t in d["teams"].items():
        if t.get("replacement_example", {}).get("player_out"):
            ex = (team, t)
            break
    body = [
        note("ok", "Minutes shares are <strong>measured</strong>, summed from the official "
                   "box score of each team's last %d completed games. The replacement rule "
                   "is stated, not assumed: %s."
             % (10, esc(d["method"].split(";")[-1].strip()))),
        table(["Team", "Games", "Window"] +
              ["1", "2", "3", "4", "5", "6", "7", "8"] +
              ["Rest of bench", "Source"], rows),
    ]
    if ex:
        team, t = ex
        rrows = [[esc(x["player"]), val(x["minutes_share_before"]),
                  val(x["minutes_share_after_out"]),
                  link("https://www.nba.com/games", "official box scores")]
                 for x in t["replacement_example"]["redistribution"]]
        body += [
            "<h2>Worked replacement — %s without %s</h2>" %
            (esc(team), esc(t["replacement_example"]["player_out"])),
            "<p class='mono'>%s</p>" % esc(t["replacement_rule"]),
            table(["Player", "Share before", "Share after the minutes are redistributed",
                   "Source"], rrows),
        ]
    return page("Minutes redistribution", "Top-8 minutes shares and what happens to "
                "them when a player is out.", "".join(body), "rotation.html")


def build_rest_travel():
    d = jload(os.path.join(DERIVED, "rest_travel_2026_27.json"))
    rows = []
    for r in d["rows"]:
        rows.append([r["date"], r["team"], "away" if r["side"] == "away" else "home",
                     r["opponent"], val(r["last_game_date"]), val(r["rest_days"]),
                     "yes" if r["back_to_back"] else "no",
                     "yes" if r["three_in_four"] else "no",
                     val(r["games_in_last_3_days"]),
                     val(r["travel_miles_from_previous_venue"]),
                     link(r["source_url"], "game")])
    body = [
        note("ok", "Rest, back-to-back and 3-in-4 are computed from the official "
                   "schedule and official finals — never assumed."),
        note("warn", "<strong>Travel distance is flagged.</strong> %s"
             % esc(d["travel_caveat"])),
        table(["Date", "Team", "Side", "Opponent", "Last game", "Rest days", "B2B",
               "3-in-4", "Games last 3d", "Travel (mi)", "Source"], rows),
    ]
    return page("Rest, back-to-back and travel", "Schedule load computed from the "
                "official schedule, plus great-circle travel between arenas.",
                "".join(body), "rest-travel.html")


def build_luck():
    d = jload(os.path.join(DERIVED, "luck_2026_27.json"))
    rows = []
    for r in d["rows"]:
        cls = " class='bad'" if r["inside_noise_band"] is False else ""
        rows.append(["<strong>%s</strong>" % r["team"], val(r["games"]),
                     "%d-%d" % (r["wins"], r["losses"]), val(r["points_for"]),
                     val(r["points_against"]), val(r["point_diff_per_game"]),
                     val(r["pythagorean_expected_wins"]), val(r["win_surplus"]),
                     "<span%s>%s</span>" % (cls, val(r["luck_z"])),
                     "inside" if r["inside_noise_band"] else
                     ("OUTSIDE" if r["inside_noise_band"] is False else DASH),
                     link("https://www.nba.com/games", "official finals")])
    body = [
        note("info", "<strong>Refusal rule.</strong> %s" % esc(d["noise_band"])),
        "<p class='mono'>%s</p>" % esc(d["method"]),
        table(["Team", "G", "W-L", "PF", "PA", "Diff/g", "Pyth wins", "Win surplus",
               "Luck z", "Band", "Source"], rows),
    ]
    return page("Luck as a z-score", "How far each team's record sits from what its "
                "official scoring line says it should be.", "".join(body), "luck-z.html")


def build_injury_ledger():
    d = jload(os.path.join(INJ, "editions_2026-11-15.json"))
    diff = jload(os.path.join(INJ, "diff_2026-11-15.json"))
    newest = [e for e in d["editions"] if e["parse_status"] == "ok"]
    newest = newest[-1] if newest else {}
    erows = []
    for e in d["editions"]:
        erows.append([esc(e["edition"].replace("Injury-Report_", "").replace("_", " ")),
                      esc(e["revision_label"] or DASH),
                      esc((e["retrieved_utc"] or DASH).replace("T", " ").replace("Z", "Z")),
                      val(e["bytes"]),
                      '<span class="mono">%s</span>' % esc((e["sha256"] or "")[:16]),
                      val(e["n_rows"]),
                      link(e["source_url"], "PDF")])
    crows = []
    for dd in diff["diffs"]:
        for c in dd["changes"]:
            if c["change"] != "STATUS_CHANGE":
                continue
            crows.append([esc(dd["from_revision_label"] or DASH),
                          esc(dd["to_revision_label"] or DASH),
                          esc(c["team"] or DASH), esc(c["player"] or DASH),
                          esc(c["from"]), "<strong>%s</strong>" % esc(c["to"]),
                          esc((c.get("reason") or "")[:70]),
                          link("https://official.nba.com/nba-injury-report-2026-27-season/",
                               "index")])
    body = [
        note("ok", "<strong>Banner — official injury report.</strong> Revision time "
                   "<strong>%s</strong>; retrieved <strong>%s</strong>; stored as "
                   "<code>%s</code>; SHA-256 <span class='mono'>%s</span>."
             % (esc(newest.get("revision_label") or DASH),
                esc(newest.get("retrieved_utc") or DASH),
                esc(newest.get("stored_file") or DASH),
                esc((newest.get("sha256") or "")[:32]))),
        note("info", "<strong>%d</strong> editions published by the league on 2026-11-15 "
                     "were downloaded, hashed and stored; <strong>%d</strong> consecutive "
                     "pairs were diffed and <strong>%d</strong> status changes were found."
             % (diff["n_editions"], diff["n_consecutive_pairs"],
                diff["n_status_changes_total"])),
        "<h2>Every edition stored</h2>",
        table(["Edition", "Revision time (official)", "Retrieved (UTC)", "Bytes",
               "SHA-256 (16)", "Rows", "Official PDF"], erows),
        "<h2>Status changes detected between consecutive editions</h2>",
        table(["From revision", "To revision", "Team", "Player", "Was", "Now",
               "Reason", "Source"], crows),
    ]
    return page("Injury PDF ledger", "Every edition stored with its timestamp, and "
                "consecutive editions diffed for status changes.", "".join(body),
                "injury-ledger.html")


def build_settlement():
    # Schema note (arena/0e9c924f-nba1, §50 N04): reads the real settle_slate.py schema
    # (summary.* + slate_archive.*). arena/b454a53d-nba1 (2026-11-17): the page was hard-wired
    # to settlement_2026-11-15.json, so the 2026-11-16 settlement was invisible. It now renders
    # EVERY settlement record in data/settlement/ (one stamp + singles table per slate, oldest
    # first) and the box-score SGP grading record for any slate that has one.
    led = jload(os.path.join(ROOT, "data", "ledger", "ledger.json"))
    import glob as _glob
    slates = []
    for _p in sorted(_glob.glob(os.path.join(SETTLE, "settlement_*.json"))):
        _slate = os.path.basename(_p)[len("settlement_"):-5]
        if re.match(r"^\d{4}-\d{2}-\d{2}$", _slate):
            slates.append((_slate, jload(_p)))
    body = []
    for slate, s in slates:
        summ = s.get("summary", {})
        arch = s.get("slate_archive", {})
        # A later amendment (sgp_grades_<slate>_amendment1.json, ledger-linked) supersedes the original.
        sgp_p = os.path.join(SETTLE, "sgp_grades_%s_amendment1.json" % slate)
        if not os.path.exists(sgp_p):
            sgp_p = os.path.join(SETTLE, "sgp_grades_%s.json" % slate)
        sgp = jload(sgp_p) if os.path.exists(sgp_p) else None
        # The ledger is the record of record for leg status: a later
        # `sgp_leg_resolution` entry (e.g. arena/09ed2727-nba1's gamebook read)
        # can resolve legs the grading record left UNRESOLVED. Overlay it here so
        # the page never prints a status the chain has already superseded.
        resolved_legs = {}
        res_entry = None
        for _e in led.get("entries", []):
            if _e.get("type") == "sgp_leg_resolution" and (
                    _e.get("slate") == slate or slate in json.dumps(_e.get("resolves", {}))):
                res_entry = _e
                _evp = os.path.join(ROOT, _e["file"])
                if os.path.exists(_evp):
                    for _pl in jload(_evp).get("players", []):
                        # Gamebook rows are "Last, First"; ticket legs are "First Last".
                        # Key on the surname so both conventions match.
                        _key = _pl["player"].split(",")[0].strip()
                        resolved_legs[_key] = _pl
                        resolved_legs[_key.split()[-1]] = _pl
        if sgp and resolved_legs:
            for _t in sgp["tickets"]:
                for _l in _t["legs"]:
                    _hit = (resolved_legs.get(_l["player"].split()[-1])
                            or resolved_legs.get(_l["player"].split()[0]))
                    if _hit and _l.get("result") == "UNRESOLVED":
                        _l["result"] = "VOID"
                        _l["official_pts"] = None
                        _l["resolution"] = _hit.get("evidence", "")
                        _l["resolved_by_ledger_entry"] = res_entry["entry"]
        n_graded = len(s.get("singles", [])) + sum(
            1 for p in s.get("parlays", []) if p.get("result")) + (
            sgp["summary"]["tickets"] if sgp else summ.get("sgp_settled", 0))
        _sgp_settled = sgp["summary"]["tickets"] if sgp else summ.get("sgp_settled", 0)
        n_pending = max(0, summ.get("sgp_published", 0) - _sgp_settled)
        total = summ.get("total_units_settled")
        if sgp:
            total = round((total or 0) + (sgp["summary"]["units"] or 0), 2)
        srows = []
        for r in s["singles"]:
            final = (f"{r.get('away_pts')}-{r.get('home_pts')}"
                     if r.get("away_pts") is not None else None)
            srows.append([r["date"], r["matchup"], val(r.get("pick_line")),
                          val(final), val(r.get("margin_pick_team")),
                          "<strong>%s</strong>" % esc(r["result"]), val(r["units"]),
                          link(r.get("source_url") or r.get("source_game_url") or
                               "https://www.nba.com/games?date=%s" % slate, "official final")])
        body.append(note("ok", "<strong>Settlement stamp.</strong> Slate %s settled "
                               "<strong>%s</strong> from official finals only "
                               "(dates settled: %s; dates still open: %s). "
                               "<strong>%d</strong> tickets graded, <strong>%d</strong> left PENDING, "
                               "units <strong>%s</strong>. %s"
                         % (esc(slate), esc(s["settled_at_utc"]),
                            esc(", ".join(summ.get("dates_settled", [])) or "(none)"),
                            esc(", ".join(summ.get("dates_unsettled", [])) or "(none)"),
                            n_graded, n_pending, val(total),
                            esc(summ.get("validation_note", "")))))
        body.append(note("info", "Pre-tip anchor: <code>%s</code> SHA-256 <span class='mono'>%s</span>. "
                                 "Nothing graded here was published after the first tip."
                         % (esc(arch.get("picks", "?")), esc((arch.get("picks_sha256") or "")[:32]))))
        body.append("<h2>Singles &mdash; %s</h2>" % esc(slate))
        body.append(table(["Date", "Game", "Ticket", "Official final", "Margin", "Result",
                           "Units", "Source"], srows))
        if sgp:
            grows = []
            for t in sgp["tickets"]:
                legs = "; ".join("%s %s %s &rarr; %s%s" % (esc(l["player"]), esc(l["side"]), esc(l["line"]),
                                                        esc(l["result"]),
                                                        (" (%s pts)" % esc(l["official_pts"]))
                                                        if l["official_pts"] is not None
                                                        else (" (inactive - gamebook)" if l.get("resolution")
                                                              else " (no box-score row)"))
                                 for l in t["legs"])
                _srcs = [link(t["sources"][0], "official box score")]
                if any(l.get("resolution") for l in t["legs"]):
                    _srcs.append(link(res_entry.get("sources", [{}])[0].get("url")
                                      if res_entry.get("sources") else t["sources"][0],
                                      "official gamebook (Inactive line)"))
                grows.append([slate, esc(t["game"]), legs, "<strong>%s</strong>" % esc(t["result"]),
                              val(t["units"]), " &middot; ".join(_srcs)])
            body.append("<h2>SGP tickets &mdash; graded from official box scores (%s)</h2>" % esc(slate))
            body.append(table(["Date", "Game", "Legs (official points)", "Result", "Units", "Source"], grows))
        else:
            n_sgp = summ.get("sgp_published", 0)
            if n_sgp:
                body.append(note("warn", "%d SGP ticket(s) for %s are not graded: a player leg needs the "
                                         "official box-score row, which no grading record holds yet."
                                 % (n_sgp, esc(slate))))
    lrows = [[val(e["entry"]), esc(e["type"]), esc(e["at_utc"]),
              '<span class="mono">%s</span>' % esc((e["head"] if "head" in e
                                                    else e.get("prev") or "")[:16]),
              link("https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/ledger/ledger.json",
                   "ledger")] for e in led["entries"]]
    body += [
        "<h2>Ledger chain</h2>",
        table(["#", "Type", "At (UTC)", "prev / head (16)", "File"], lrows),
    ]
    return page("Settlement and ledger", "Official finals in, graded tickets out, and "
                "the hash chain that proves the picks predate the tip.",
                "".join(body), "settlement.html")



REQUIREMENTS = [
    ("Extend the scheduled job to refresh the official schedule, standings, team statistics and "
     "injury report for each rolling slate, then rebuild only after freshness and provenance "
     "gates pass",
     "PARTIAL",
     "The fetch and the fail-closed gate exist and are proven on a runner (engine/fetch_official.py, "
     "engine/refresh_gate.py). This session added a second capture job that stores every official "
     "page and box score it reads. The standings and team-stat parsers cannot produce rows because "
     "those pages carry no data in an HTTP response (F103).",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine/refresh_gate.py"),
    ("Keep an official per-game result feed current; settle only after final scores are verified; "
     "store one row per game: date, teams, final score, quarter scores",
     "DONE",
     "222 games captured, 190 Final, quarter scores asserted to sum to the final on every Final game. "
     "Nothing is graded from a live score.",
     "https://www.nba.com/games"),
    ("Store every injury PDF with its timestamp and diff consecutive reports to detect status changes",
     "DONE",
     "75 editions published by the league on 2026-11-15 were downloaded, hashed and stored; 74 "
     "consecutive pairs diffed; 28 status changes detected.",
     "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ("Freeze a pre-registration file per strategy before its first bet: signal, thresholds, "
     "universe and the exact settlement rule",
     "DONE",
     "R-SINGLE, R-PARLAY and R-SGP frozen before the earliest tip this publication can apply to, "
     "hashed into the ledger.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/prereg/v2-801ba27f/_index.json"),
    ("Add a tamper-evident ledger: hash each published pick, publish the hash before tip and "
     "verify after settlement",
     "DONE",
     "data/ledger/ledger.json is a SHA-256 hash chain; scripts/verify_ledger.py reports "
     "'ledger chain OK'; this session appended a settlement entry and a pre-tip publication entry.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/ledger/ledger.json"),
    ("Split the site into a projection surface (safe to publish now) and a bet surface (gated), "
     "and never mix them",
     "DONE",
     "Two separate pages generated from two separate JSON files; the projection file names the bet "
     "file and states that the two are never merged into one table.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/horizon_lines_801ba27f.json"),
    ("Keep two independent estimators and publish their disagreement as the primary confidence "
     "signal, rather than a single blended rating",
     "DONE",
     "Estimator 1 is possessions x points per possession; estimator 2 is a least-squares power "
     "rating solved from official final margins plus scored/allowed rates. Different information "
     "set, different failure mode. Mean disagreement 4.05 points on the spread.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/estimators_2026_27.json"),
    ("Pin home-court advantage to the measured home-win rate instead of fitting it freely",
     "DONE",
     "0.5263 measured over 190 official finals; converted through the empirical margin "
     "distribution (sigma 16.78) to 1.108 points. No free parameter.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/measured_constants_2026_27.json"),
    ("Report luck as a z-score per team and refuse to publish a strategy that leans on a team "
     "outside the noise band",
     "DONE",
     "Pythagorean expectation on official points for and against; z = (W - E[W]) / sqrt(n p (1-p)). "
     "Teams with |z| > 2.0 are refused on the bet surface.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/luck_2026_27.json"),
    ("Compute rest, back-to-back and 3-in-4 from the official schedule, and add travel distance "
     "from a sourced arena-coordinate table",
     "PARTIAL",
     "Rest, back-to-back and 3-in-4 are computed from the official schedule and official finals. "
     "Travel is computed and published but flagged: arena city and state are official, latitude and "
     "longitude are not published by any NBA page (F101).",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/rest_travel_2026_27.json"),
    ("Model minutes redistribution explicitly: for each team, the top-8 minutes shares and the "
     "replacement shares when a player is out",
     "DONE",
     "Minutes summed from the official box score of each team's last 10 completed games; top-8 "
     "shares published with a worked proportional replacement.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/rotation_2026_27.json"),
    ("Stop publishing a single blended rating as the headline; publish the disagreement between "
     "the two estimators as the headline and the blend underneath",
     "DONE",
     "The projection and estimators pages lead with the disagreement columns and print the blend "
     "beside them, underneath. Page: Estimators.",
     "https://www.nba.com/games"),
    ("Price every parlay with the measured rho and print the naive product next to it, instead of "
     "withholding the price entirely",
     "DONE",
     "Cross-game rho measured at 0.0142 over 1,546 same-date pairs; team-mate rho -0.0975 over 374 "
     "pairs. Every parlay prints the rho-priced joint probability and the naive product beside it.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/rho_2026_27.json"),
    ("Put rotation availability on the picks page as its own column",
     "DONE",
     "Minutes-weighted share of each team's measured top-8 that is not ruled out, from official box "
     "scores cross-referenced with the newest official injury edition. Page: Bet surface.",
     "https://www.nba.com/games"),
    ("Add a market-anchored prior: blend the model line with the closing line, weight by measured "
     "out-of-sample log-loss",
     "BLOCKED",
     "No closing line is captured anywhere in this repository and no NBA-operated source publishes "
     "one, so the prior weight is 0 and no market-blended price is published. Stated on the bet "
     "surface rather than silently omitted (F102).",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/horizon_picks_801ba27f.json"),
    ("Model the total as possessions x points-per-possession, not as an average of team scoring "
     "averages",
     "DONE",
     "Estimator 1: POSS = pace_home + pace_away - league_pace; PTS = (OffRtg x opponent DefRtg / "
     "league OffRtg) x POSS / 100. The scoring-average construction survives only as estimator 2, "
     "used to produce the disagreement. Page: Estimators.",
     "https://www.nba.com/games"),
    ("Show the injury-report revision time and retrieval time in the Injuries page banner",
     "DONE",
     "The Injuries page carries a newest-edition banner with revision time and retrieval time; the "
     "Injury PDF Ledger page prints both for the newest of the 75 stored editions.",
     "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ("Settle the sealed ledger from official finals as soon as each game day ends, and keep the "
     "settlement stamp visible",
     "DONE",
     "2026-11-15 settled from official finals only: 2 graded, 7 PENDING, +2.00 paper units. The "
     "stamp is the first thing on the Settlement page.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/settlement/settlement_2026-11-15.json"),
    ("Re-read the three official team-stat pages (traditional, opponent, advanced) and re-cut the "
     "model inputs",
     "BLOCKED - WORKED AROUND",
     "All three pages were fetched. None carries data in an HTTP response: they render their tables "
     "in the browser. The same quantities were rebuilt from official box scores instead, which are "
     "server-rendered. Every rating traces to an official game page (F103).",
     "https://www.nba.com/stats/teams/advanced"),
    ("Capture per-player game logs (minutes, points, rebounds, assists and the opponent) for at "
     "least the players who appear on an injury report",
     "DONE WITH A GAP",
     "Every player in every one of the 222 captured games has minutes, points, rebounds, assists "
     "and the opponent. The gap: a player on the injury report with no minutes this season has no "
     "measured minutes share, so removing them moves availability by 0.00 (F106).",
     "https://www.nba.com/games"),
    ("Generate picks for every upcoming slate of games up to a maximum of 3 days in advance using "
     "the originated lines",
     "DONE",
     "The rolling window is today plus three days: 2026-11-15 to 2026-11-18, 34 games, 28 of which "
     "had not tipped at publication.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/horizon_picks_801ba27f.json"),
]


def build_requirements():
    rows = []
    for text, status, detail, url in REQUIREMENTS:
        cls = ("ok" if status == "DONE" else
               "warn" if status.startswith("PARTIAL") or status.startswith("DONE WITH") else
               "bad")
        rows.append([esc(text), '<span class="chip %s">%s</span>' % (cls, esc(status)),
                     esc(detail), '<a href="%s">evidence</a>' % esc(url)])
    n_done = sum(1 for r in REQUIREMENTS if r[1] == "DONE")
    body = [
        note("info", "<strong>%d of %d</strong> numbered instructions in the brief are fully "
                     "delivered. The rest are delivered partially or blocked, and every one of "
                     "those says exactly what is missing and links to the evidence."
             % (n_done, len(REQUIREMENTS))),
        table(["Instruction (as written in the brief)", "Status", "What was actually done",
               "Evidence"], rows),
    ]
    return page("Requirements coverage", "Each instruction in the brief, its status, and the "
                "evidence for that status.", "".join(body), "brief-coverage.html")


PAGES_BUILDERS = [
    ("official-feed.html", build_official_feed),
    ("estimators.html", build_estimators),
    # projection.html and bet-surface.html are deliberately NOT in this list:
    # since COORDINATION §53 (Q03) they are written by scripts/build_surfaces.py
    # (the machine-checked fail-closed split), which the dashboard hook runs on
    # every build.  This legacy builder's versions predate that rule and would
    # re-mix picks onto the bet surface — §61 W04 removed them here so this
    # script can never overwrite the gated pages if it is ever run again.
    ("parlay-pricing.html", build_parlay_pricing),
    ("rotation.html", build_rotation),
    ("rest-travel.html", build_rest_travel),
    ("luck-z.html", build_luck),
    ("injury-ledger.html", build_injury_ledger),
    ("settlement.html", build_settlement),
    ("brief-coverage.html", build_requirements),
]


def main():
    os.makedirs(PAGES, exist_ok=True)
    for name, fn in PAGES_BUILDERS:
        out = fn()
        path = os.path.join(PAGES, name)
        with open(path, "w") as fh:
            fh.write(out)
        # I5: the word "None" must never reach a rendered page as a value.
        assert ">None<" not in out, name + " renders the string None"
        assert ">nan<" not in out, name + " renders nan"
        print("  %-24s %7d bytes" % (name, len(out)))
    print("built %d pages" % len(PAGES_BUILDERS))


if __name__ == "__main__":
    main()
