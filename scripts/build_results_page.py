#!/usr/bin/env python3
"""build_results_page.py — two pages that make the settling machinery visible.

1. `site/pages/results.html` — the official per-game result feed for the slate
   being settled, one row per game: date, teams, final score, quarter scores,
   whether every game of that game day is verified final, and the settlement
   stamp if the day has been settled.  Requirement R02 says "store one row per
   game: date, teams, final score, quarter scores" and R19 says "keep the
   settlement stamp visible" — this page is where both are read.
2. `site/pages/player-logs.html` — the per-player game logs parsed from the
   official gamebook (requirement R21), with the report cross-reference.

Nothing is computed from anything but the committed files:
  data/official/results_<date>.json
  data/settlement/settlement_<slate>.json
  data/ledger/ledger.json
  data/official/player_game_logs_<date>.json
  data/official/injury_<newest>.json

Every table row carries the official URL it came from.  A value the official
page did not print is rendered as an em dash, never as zero.
"""
from __future__ import annotations

import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, "site", "pages")


def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return json.load(fh)


def esc(x):
    if x is None or x == "":
        return '<span class="blank" title="not printed on the official page">—</span>'
    return html.escape(str(x))


def link(url, text=None):
    if not url:
        return esc(None)
    return '<a href="%s" rel="noopener">%s</a>' % (html.escape(url), html.escape(text or url))


HEAD = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>%s</title><link rel=\"stylesheet\" href=\"../assets/site.css\"></head><body>"
        "<div class=\"wrap\">%s<main>%s</main></div></body></html>")


def nav(active):
    groups = [
        ("Horizon", [("roll.html", "Rolling slate"), ("picks.html", "Lines &amp; picks"),
                     ("props.html", "Player props"), ("injuries.html", "Injuries"),
                     ("gameflow.html", "Game flow")]),
        ("Results &amp; settlement", [("results.html", "Official results &amp; settlement"),
                                      ("player-logs.html", "Player game logs")]),
        ("Evidence", [("strategies.html", "Strategies"), ("validation.html", "Gates"),
                      ("correlations.html", "Correlations"), ("luck.html", "Luck"),
                      ("backtest.html", "Backtest"), ("model.html", "Model")]),
        ("Decision", [("requirements.html", "Brief traceability"),
                      ("questions.html", "Open questions"), ("suggestions.html", "Suggestions"),
                      ("decisions.html", "Decisions"), ("flagged.html", "Flagged for review"),
                      ("sources.html", "Sources")]),
    ]
    out = ['<header class="top"><a class="brand" href="../../index.html">NBA1</a><nav>']
    for label, items in groups:
        out.append('<span class="grp"><b>%s</b>' % label)
        for href, text in items:
            out.append('<a href="%s"%s>%s</a>' % (href, ' class="on"' if href == active else "", text))
        out.append("</span>")
    out.append("</nav></header>")
    return "".join(out)


def table(headers, rows, cls=""):
    out = ['<table class="data %s"><thead><tr>' % cls]
    out += ['<th>%s</th>' % h for h in headers]
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def verdict_box(kind, title, body):
    return '<div class="banner %s"><b>%s</b> %s</div>' % (kind, html.escape(title), body)


# ---------------------------------------------------------------------------
def results_page():
    # Defect fixed by arena/23b323a3-nba1 (COORDINATION §50, finding F112):
    # a second capture of the same game day may be committed under a
    # session-namespaced name (`results_2026-11-15_dfef26dc.json`). The old code
    # took the date from the whole file stem, so that file produced its own
    # section under the heading "2026-11-15_dfef26dc", matched zero rows and
    # printed "0 of 0 final — NOT settleable" DIRECTLY BENEATH the settled
    # 2026-11-15 section. That is a false negative on the one page whose job is
    # to say whether a game day is settleable. The date is now read from the
    # first ten characters of the stem, and when a canonical `results_<date>.json`
    # exists it is authoritative — the extra captures are listed as superseded
    # rather than rendered as empty game days.
    _feeds_all = sorted(glob.glob(os.path.join(ROOT, "data", "official", "results_*.json")))
    _by_date = {}
    for _p in _feeds_all:
        _stem = os.path.basename(_p)[len("results_"):-5]
        # Only files named for a calendar date are game-day captures. The season-wide
        # running feed (`results_feed_2026_27.json`) is not a game day: before this guard
        # it rendered a phantom "feed_2026_ ... 0 of 0 final" section (2026-11-17, b454a53d).
        if not re.match(r"^\d{4}-\d{2}-\d{2}", _stem):
            continue
        _by_date.setdefault(_stem[:10], []).append(_p)
    feeds, superseded_captures = [], {}
    for _d in sorted(_by_date):
        _paths = _by_date[_d]
        _canon = [p for p in _paths
                  if os.path.basename(p) == "results_%s.json" % _d]
        feeds.append(_canon[0] if _canon else _paths[0])
        _extra = [p for p in _paths if p != ( _canon[0] if _canon else _paths[0])]
        if _extra:
            superseded_captures[_d] = [os.path.basename(p) for p in _extra]
    settlements = {os.path.basename(p)[:-5]: p
                   for p in glob.glob(os.path.join(ROOT, "data", "settlement", "settlement_*.json"))}
    ledger = load("data", "ledger", "ledger.json")

    body = ['<h1>Official results &amp; settlement</h1>']
    body.append('<p class="lead">One row per game for every date this repository holds an official '
                'result feed for. A game is <b>FINAL</b> only when the NBA game page printed Final '
                'and its quarter scores sum to the printed final &mdash; that check is asserted in '
                'the data file by the writer, and re-asserted by '
                '<code>scripts/settle_slate.py</code> before anything is settled. A live score is '
                'never stored as a final.</p>')

    total_games = total_final = 0
    for path in feeds:
        feed = json.load(open(path, encoding="utf-8"))
        date = os.path.basename(path)[len("results_"):-5][:10]
        rows = [r for r in feed.get("rows", []) if r.get("date") == date]
        # Two capture styles exist in this repo: the 11/15 feed adds an explicit
        # `status` field, the 11/14 feed records the same fact as `final_label`.
        # Both are read; neither is inferred.
        def is_final(r):
            return (r.get("status") == "FINAL"
                    or (r.get("final_label") or "").startswith("Final"))

        finals = [r for r in rows if is_final(r)]
        total_games += len(rows)
        total_final += len(finals)
        day_state = ("ALL FINAL &mdash; settleable" if rows and len(finals) == len(rows)
                     else "%d of %d final &mdash; NOT settleable" % (len(finals), len(rows)))
        body.append('<h2>%s</h2>' % html.escape(date))
        body.append('<p class="fine">Retrieved: %s &middot; %s</p>'
                    % (esc(feed.get("retrieved_utc")), day_state))
        tbl = []
        for r in sorted(rows, key=lambda x: x.get("game_id") or ""):
            aq = r.get("away_quarters")
            hq = r.get("home_quarters")
            q = ("%s / %s" % ("-".join(str(x) for x in aq), "-".join(str(x) for x in hq))
                 if aq and hq else None)
            score = ("%s &ndash; %s" % (esc(r.get("away_pts")), esc(r.get("home_pts")))
                     if r.get("away_pts") is not None else esc(None))
            tbl.append([
                esc(r.get("away")), esc(r.get("home")),
                esc(r.get("status") or r.get("final_label")),
                score,
                esc(q),
                esc(r.get("ot_periods") or 0),
                esc(r.get("tip_et")),
                esc(r.get("venue")),
                link(r.get("source_url"), "game page"),
            ])
        body.append(table(["Away", "Home", "Official status", "Final score",
                           "Quarters (away / home)", "OT", "Tip (ET)", "Venue", "Source"], tbl))

        srel = "settlement_" + date
        if srel in settlements:
            s = json.load(open(settlements[srel], encoding="utf-8"))
            sm = s["summary"]
            body.append(verdict_box("ok", "SETTLED",
                "This game day is settled. Stamp <b>%s</b>, by <code>%s</code>. "
                "Singles <b>%s</b> (%s units at paper &minus;110), parlays %s units, "
                "settled total <b>%s units</b>. Record file: %s."
                % (esc(s.get("settled_at_utc")), esc(s.get("settled_by")),
                   esc(sm.get("record")), esc(sm.get("singles_units_at_minus110")),
                   esc(sm.get("parlay_units")),
                   esc(sm.get("total_units_settled", sm.get("total_units"))),
                   link("../../" + os.path.relpath(settlements[srel], ROOT), "settlement JSON"))))
            # SGP tickets: scripts/settle_slate.py cannot read box scores and leaves them
            # UNSETTLED. A separate grading record (sgp_grades_<date>.json, hash-chained in
            # the ledger) carries the box-score grades when someone has read them.
            _sgp_p = os.path.join(ROOT, "data", "settlement", "sgp_grades_%s_amendment1.json" % date)
            if not os.path.exists(_sgp_p):
                _sgp_p = os.path.join(ROOT, "data", "settlement", "sgp_grades_%s.json" % date)
            if os.path.exists(_sgp_p):
                _g = json.load(open(_sgp_p, encoding="utf-8"))["summary"]
                _combined = round((sm.get("total_units_settled") or 0) + (_g.get("units") or 0), 2)
                _sgp_txt = ("SGP tickets: %s published, graded from official box scores: "
                            "%s won, %s lost, %s units (grading record: %s). "
                            "Combined with singles and parlays: <b>%s units</b>."
                            % (esc(sm.get("sgp_published")), esc(_g.get("won")), esc(_g.get("lost")),
                               esc(_g.get("units")), link("../../" + os.path.relpath(_sgp_p, ROOT),
                                                          "sgp_grades JSON"), esc(_combined)))
            else:
                _sgp_txt = ("SGP tickets: %s published, %s settled, not graded (player legs need the "
                            "official box score)." % (esc(sm.get("sgp_published")), esc(sm.get("sgp_settled"))))
            body.append('<p class="fine">%s Papers are graded by the price convention printed on each '
                        'row, and no market price exists anywhere on this site.</p>' % _sgp_txt)
        else:
            body.append(verdict_box("warn", "NOT SETTLED YET",
                "No settlement file exists for this game day. %s"
                % ("Every game is final, so the next scheduled refresh will settle it "
                   "automatically (<code>scripts/settle_slate.py</code> runs in "
                   "<code>refresh-data.yml</code>)." if rows and len(finals) == len(rows)
                   else "Games that are not final cannot be graded; settling now would be a "
                        "guess, so nothing is written.")))

        if date in superseded_captures:
            body.append('<p class="fine">Additional captures of this same game day are held in the '
                        'repository but are <b>not</b> rendered as separate game days, because they '
                        'describe the same slate at an earlier retrieval time and the canonical file '
                        'above supersedes them: <code>%s</code>. They are kept on disk as evidence of '
                        'what was observed then, which is why an earlier capture can still say a game '
                        'was not final.</p>'
                        % html.escape(", ".join(superseded_captures[date])))

    body.append('<h2>How a game day gets settled</h2>')
    body.append('<ol class="steps">'
                '<li>The scheduled job runs <code>scripts/settle_slate.py</code> for every archived '
                'pre-tip slate.</li>'
                '<li>It refuses any date where even one game is not verified final (exit 3).</li>'
                '<li>It grades only the <b>archived pre-tip picks</b>, and asserts their SHA-256 '
                'against the ledger entry that committed to them before the first tip.</li>'
                '<li>It appends two ledger entries: a settlement-verification entry and the '
                'settlement record, then re-verifies the whole chain.</li>'
                '<li>The settlement stamp above is read from that record, so the page cannot show a '
                'stamp the ledger does not hold.</li></ol>')
    body.append('<p class="fine">Ledger head at build time: <code>%s</code> (%d entries). %s</p>'
                % (esc(ledger.get("head")), len(ledger.get("entries", [])),
                   "Verify with <code>python3 scripts/verify_ledger.py</code>."))
    sub = ('<p class="fine">%d game rows across %d dates; %d are final. '
           'Every row links its own NBA.com game page.</p>'
           % (total_games, len(feeds), total_final))
    body.insert(2, sub)
    return HEAD % ("Official results and settlement · NBA1", nav("results.html"), "".join(body))


def player_logs_page():
    cands = sorted(glob.glob(os.path.join(ROOT, "data", "official", "player_game_logs_*.json")))
    body = ['<h1>Player game logs</h1>']
    if not cands:
        body.append(verdict_box("warn", "NOT CAPTURED",
                                "No <code>data/official/player_game_logs_*.json</code> exists. "
                                "Run <code>python3 scripts/capture_player_logs.py</code>."))
        return HEAD % ("Player game logs · NBA1", nav("player-logs.html"), "".join(body))

    doc = json.load(open(cands[-1], encoding="utf-8"))
    cov = doc["coverage"]
    # The 2026-11-15 capture predates a naming change; read whichever key the
    # capture carries rather than inventing a count.
    inj_count = (cov.get("players_on_2026_11_16_0130PM_report")
                 if cov.get("players_on_2026_11_16_0130PM_report") is not None
                 else cov.get("players_on_2026_11_15_0615PM_report"))
    body.append('<p class="lead">Minutes, points, rebounds and assists for <b>every player in the '
                'official gamebook</b> of each finished game &mdash; not just the players on the '
                'injury report, because a rotation question needs the players who actually played. '
                'The source is the league\'s own gamebook PDF; the text of every page used is '
                'committed under <code>data/official/gamebooks/</code> so each cell can be checked '
                'by eye.</p>')

    body.append(verdict_box("ok", "SOURCE",
        "%s. Retrieved %s. %d games, %d player rows (%d appeared), of which %d are players named "
        "on the %s injury report."
        % (html.escape(doc["source_name"]), html.escape(doc["retrieved_utc"]),
           cov["games"], cov["player_rows"], cov["players_who_played"],
           inj_count, html.escape(cov["injury_report_edition"]))))

    mc = doc.get("minutes_check") or {}
    body.append('<h2>The checks the parser must pass</h2>')
    body.append('<p>Every team\'s parsed player points must equal the official final score. '
                'Minutes are compared with the gamebook\'s own printed team total. '
                'Result: <b>%d of %d</b> team totals match exactly; the largest difference is '
                '<b>%s second(s)</b>. Those differences are the official document\'s own '
                '(its printed total against the sum of its per-player MM:SS cells) and are '
                'published, not smoothed away.</p>'
                % (mc.get("exact_matches", 0), mc.get("teams_checked", 0),
                   esc(mc.get("max_abs_delta_seconds"))))
    checks = []
    for g in doc["games"]:
        pts = [c for c in g["checks"] if "sum_of_player_points" in c]
        checks.append([esc(g["matchup"]), esc(g["game_id"]),
                       " / ".join("%s %s" % (esc(c["team"]), esc(c["official_final"])) for c in pts),
                       '<span class="ok">points reconcile</span>' if all(c["match"] for c in pts)
                       else '<span class="bad">MISMATCH</span>',
                       esc(g["played"]), link(g["source_pdf"], "gamebook PDF")])
    body.append(table(["Game", "Game id", "Official final", "Points check", "Players who appeared",
                       "Source"], checks))

    body.append('<h2>Players named on the injury report, and whether they played</h2>')
    body.append('<p class="fine">The value of this table is the negative case: a player listed '
                'Out who does not appear is exactly what the rotation model needs to know.</p>')
    rows = []
    for r in sorted([x for x in doc["rows"] if x["on_official_injury_report"]],
                    key=lambda x: (x["game_id"], x["team"], x["player"])):
        rows.append([esc(r["date"]), esc("%s@%s" % (r["team"], r["opponent"])),
                     esc(r["player"]), "yes" if r["played"] else '<span class="bad">no</span>',
                     esc(r["min"]), esc(r["pts"]), esc(r["reb"]), esc(r["ast"]),
                     esc(r.get("dnp_note")),
                     link(r["source_pdf"], "gamebook")])
    body.append(table(["Date", "Team@Opp", "Player", "Appeared", "MIN", "PTS", "REB", "AST",
                       "DNP / DND note", "Source"], rows))

    body.append('<h2>Every player row</h2>')
    body.append('<p class="fine">%d rows. Sorted by game, then team, then minutes descending. '
                'A dash means the official page printed nothing in that cell.</p>' % cov["player_rows"])
    rows = []
    for r in sorted(doc["rows"], key=lambda x: (x["game_id"], x["team"],
                                                -(x["minutes_seconds"] or -1))):
        rows.append([esc(r["game_id"]), esc(r["team"]), esc(r["opponent"]),
                     esc(r["player"]), "yes" if r["played"] else "no",
                     esc(r["min"]), esc(r["pts"]), esc(r["reb"]), esc(r["ast"]),
                     esc(r.get("stl")), esc(r.get("blk")), esc(r.get("tov")),
                     esc(r.get("fgm")), esc(r.get("fga")),
                     esc(r.get("fg3m")), esc(r.get("fg3a")), esc(r.get("ftm")), esc(r.get("fta")),
                     esc(r.get("plus_minus")),
                     link(r["source_pdf"], "PDF")])
    body.append(table(["Game", "Team", "Opp", "Player", "Played", "MIN", "PTS", "REB", "AST",
                       "STL", "BLK", "TOV", "FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "+/-",
                       "Source"], rows))

    nf = cov.get("names_on_report_not_found_in_any_gamebook") or []
    later = cov.get("names_on_report_later_games_only") or []
    unexpl = cov.get("names_on_report_11_15_unexplained") or []
    inact_n = cov.get("rows_recovered_from_gamebook_inactive_lines", 0)
    flagged = cov.get("report_players_unexplained_by_gamebooks") or []
    body.append('<h2>Coverage, stated</h2>')
    body.append('<p>The %d rows are the player rows parsed from the %d finished 11/15 gamebooks, '
                'plus <b>%d</b> injury-report players who have no row in the box-score table but are named on '
                'the gamebook\'s own <code>Inactive:</code> line for their team. Each is kept with that line\'s '
                'official reason, so a player who did not play is recorded, not dropped.</p>'
                % (cov["player_rows"], cov["games"], inact_n))
    body.append('<p>Of the %d names on the %s injury report, <b>%d</b> have no row in any of the %d gamebooks. '
                '<b>%d</b> of them have only games after 11/15, which have no gamebook yet. '
                '<b>%d</b> have a row for a finished 11/15 game and are <b>not explained</b> by the gamebooks '
                '(listed below and in <code>flagged.json</code>).</p>'
                % (cov["report_names_unique"], html.escape(cov["injury_report_edition"]),
                   len(nf), cov["games"], len(later), len(unexpl)))
    if flagged:
        # Every row carries the official gamebook PDF it came from (verify_all requires a link).
        rows_f = []
        for x in flagged:
            key = x.split(":", 1)[0]                      # e.g. 2026-11-15_DALBOS
            pdf = "https://statsdmz.nba.com/pdfs/20261115/20261115_%s_book.pdf" % key[len("2026-11-15_"):]
            rows_f.append([esc(x), link(pdf, "gamebook PDF")])
        body.append('<h3>Not explained by the gamebooks (flagged for review)</h3>')
        body.append(table(["Gamebook / report entry", "Official source"], rows_f))
    if nf:
        body.append('<details><summary>the %d report names with no gamebook row</summary><p class="fine">%s</p></details>'
                    % (len(nf), html.escape(", ".join(nf))))
    body.append('<p class="fine">Reproduce: <code>python3 scripts/capture_player_logs.py</code>. '
                'Source text: <code>data/official/gamebooks/*.md</code>.</p>')
    return HEAD % ("Player game logs · NBA1", nav("player-logs.html"), "".join(body))


def main():
    os.makedirs(PAGES, exist_ok=True)
    for name, html_text in (("results.html", results_page()),
                            ("player-logs.html", player_logs_page())):
        with open(os.path.join(PAGES, name), "w", encoding="utf-8") as fh:
            fh.write(html_text)
        print("wrote site/pages/%s (%d bytes)" % (name, len(html_text)))


if __name__ == "__main__":
    main()
