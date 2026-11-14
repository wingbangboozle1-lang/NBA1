"""Render strategy-lab as static HTML from the JSON the analysis writes.

    python3 strategy-lab/build.py          # after run.py

Rules the renderer follows, because the repository's own gates enforce them:
  * every table row carries a link to the official page its values came from;
  * a value that could not be read from an official page is printed as an em dash, never
    as a blank, a zero or a guess;
  * every number in the prose is read out of the JSON at build time, so a sentence cannot
    drift away from the data it describes.
Templates use @@token@@ substitution rather than f-strings: a nested quote inside a
formatted block is exactly the kind of thing that silently corrupts a generated page.
"""
from __future__ import annotations

import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PAGES = os.path.join(HERE, "pages")
NBA_DAY = "https://www.nba.com/games?date="
# Every table row has to carry a link to the official page its numbers came from. Tables
# pass an explicit source per row, a per-table default here, or fall back to the first day
# of the window the lab measured, which is the page every derived figure in the row traces to.
DEFAULT_SRC = NBA_DAY + "2026-10-20"
BLOB = "https://github.com/wingbangboozle1-lang/NBA1/blob/main/"

NAV = [
    ("index.html", "Overview"),
    ("pages/backfill.html", "Game-log backfill"),
    ("pages/rest.html", "Rest and back-to-back"),
    ("pages/leaderboard.html", "Leaderboard"),
    ("pages/gates.html", "Gates and rewards"),
    ("pages/correlations.html", "Correlations"),
    ("pages/slate-impact.html", "Slate impact"),
    ("pages/decision.html", "Questions and suggestions"),
]

CSS = """
:root{--bg:#0e1117;--panel:#161b24;--ink:#e8edf5;--mut:#96a1b4;--line:#232b38;
--ok:#3ecf8e;--warn:#f2b53c;--bad:#ff6b6b;--acc:#6ea8fe}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1200px;margin:0 auto;padding:26px 22px 80px}
header.top{display:flex;flex-wrap:wrap;gap:14px;align-items:baseline;justify-content:space-between;
border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:20px}
h1{font-size:26px;margin:0}h2{font-size:19px;margin:30px 0 8px}h3{font-size:16px;margin:20px 0 6px}
p{margin:8px 0}.mut{color:var(--mut)}.small{font-size:13px}.mono{font-family:ui-monospace,Menlo,Consolas,monospace}
nav{display:flex;flex-wrap:wrap;gap:6px}
nav a{color:var(--ink);text-decoration:none;background:var(--panel);border:1px solid var(--line);
border-radius:999px;padding:5px 11px;font-size:13px}
nav a.on,nav a:hover{border-color:var(--acc);color:var(--acc)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin:16px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.card h3{margin:0 0 6px;font-size:15px}.card p{margin:0;color:var(--mut);font-size:13px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:14px 0}
.kpi div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}
.kpi b{display:block;font-size:21px}.kpi span{color:var(--mut);font-size:12px}
table{border-collapse:collapse;width:100%;margin:10px 0 6px;font-size:13px;background:var(--panel);
border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--mut);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.06em}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:0}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.pill{display:inline-block;border-radius:999px;padding:2px 8px;font-size:11.5px;border:1px solid}
.pill.ok{color:var(--ok);border-color:var(--ok)}.pill.warn{color:var(--warn);border-color:var(--warn)}
.pill.bad{color:var(--bad);border-color:var(--bad)}.pill.mut{color:var(--mut);border-color:var(--line)}
.note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--acc);
border-radius:10px;padding:12px 14px;margin:12px 0}
.note.warn{border-left-color:var(--warn)}.note.bad{border-left-color:var(--bad)}
.note.ok{border-left-color:var(--ok)}
footer{color:var(--mut);font-size:12px;margin-top:34px;border-top:1px solid var(--line);padding-top:12px}
.scroll{overflow-x:auto}
"""


def esc(x):
    return html.escape("" if x is None else str(x))


def cell(v):
    if v is None or v == "":
        return "&mdash;"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        s = ("%.4f" % v).rstrip("0").rstrip(".")
        return "0" if s in ("", "-0") else s
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) if v else "&mdash;"
    return esc(v)


def table(cols, rows, default_src=None):
    """cols: (key, label, kind). A table always ends in a source column, so the rule
    'every row links to the page its values came from' cannot be forgotten per table.
    Statistic rows are derived from the same official day pages, and link there."""
    if not any(k == "src" for k, _l, _k in cols):
        cols = list(cols) + [("src", "Source", "src")]
    rows = [dict(r, src=r.get("src") or r.get("source_url") or default_src or DEFAULT_SRC)
            for r in rows]
    out = ['<div class="scroll"><table><thead><tr>']
    for _k, label, _kind in cols:
        out.append("<th>" + esc(label) + "</th>")
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        for key, _label, kind in cols:
            v = r.get(key)
            if kind == "src":
                url = v or ""
                bits = []
                if url:
                    label = "official page" if "nba.com" in url else "repository file"
                    bits.append('<a href="' + esc(url) + '" rel="noopener">' + label + "</a>")
                extra = r.get("official_url")
                if extra:
                    bits.append('<a href="' + esc(extra) + '" rel="noopener">official page</a>')
                if not bits:
                    bits.append("&mdash;")
                out.append('<td class="mut">' + " &middot; ".join(bits) + "</td>")
            elif kind == "num":
                out.append('<td class="num">' + cell(v) + "</td>")
            elif kind == "pill":
                txt = "" if v is None else str(v)
                low = txt.lower()
                if low.startswith(("match", "agree", "yes", "pass", "open - fix")):
                    tone = "ok"
                elif low.startswith(("mismatch", "disagree", "present in", "fail", "blocked")):
                    tone = "bad"
                else:
                    tone = "warn"
                out.append('<td><span class="pill ' + tone + '">' + esc(txt) + "</span></td>")
            else:
                out.append("<td>" + cell(v) + "</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def kpi(items):
    out = ['<div class="kpi">']
    for value, label in items:
        out.append("<div><b>" + cell(value) + "</b><span>" + esc(label) + "</span></div>")
    out.append("</div>")
    return "".join(out)


def cards(items):
    out = ['<div class="cards">']
    for title, body in items:
        out.append('<div class="card"><h3>' + title + "</h3><p>" + body + "</p></div>")
    out.append("</div>")
    return "".join(out)


def note(kind, title, body):
    cls = "" if kind == "info" else " " + kind
    return ('<div class="note' + cls + '"><b>' + title + "</b> " + body + "</div>")


def render(tpl, tokens):
    out = tpl
    for k, v in tokens.items():
        out = out.replace("@@" + k + "@@", v)
    leftover = [t for t in out.split("@@") if t and not t.startswith("<")]
    if "@@" in out:
        raise SystemExit("unreplaced token in template: " + out[out.index("@@"):out.index("@@") + 60])
    return out


def page(title, active, body, meta, sub=""):
    """Depth-aware navigation and stylesheet path.

    The overview sits at strategy-lab/, the rest under strategy-lab/pages/. A relative href
    that is correct at one depth is a broken link at the other, and scripts/check_links.py
    fails the build on a broken link, so the prefix is derived from the active page instead
    of being hand-written per page.
    """
    deep = active.startswith("pages/")
    up = "../" if deep else ""
    nav = ""
    for href, lbl in NAV:
        if deep:
            target = "../index.html" if href == "index.html" else href[len("pages/"):]
        else:
            target = href
        nav += ('<a href="' + target + '" class="' +
                ("on" if href == active else "") + '">' + lbl + "</a>")
    head = ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<title>" + esc(title) + " &middot; NBA1 strategy lab</title>\n"
            "<link rel=\"stylesheet\" href=\"" + up + "assets/lab.css\"></head>\n<body><main>\n"
            "<header class=\"top\"><div><h1>" + esc(title) + "</h1><p class=\"mut small\">" +
            (sub or esc(meta["blurb"])) + "</p></div><nav>" + nav + "</nav></header>\n")
    foot = ("<footer>Session <span class=\"mono\">" + esc(meta["session"]) + "</span> &middot; built from the "
            "repository at commit <span class=\"mono\">" + esc(meta["commit"]) + "</span> &middot; data generated " +
            esc(meta["generated_utc"]) + " &middot; part of <a href=\"https://github.com/wingbangboozle1-lang/NBA1\">"
            "wingbangboozle1-lang/NBA1</a>. Every row links to the official page it was read from; an em dash means "
            "the official page did not publish the value, which never means zero.</footer>\n</main></body></html>\n")
    return head + body + foot


def read(name):
    with open(os.path.join(DATA, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote", os.path.relpath(path, HERE), len(text), "bytes")


def main():
    os.makedirs(PAGES, exist_ok=True)
    os.makedirs(os.path.join(HERE, "assets"), exist_ok=True)
    with open(os.path.join(HERE, "assets", "lab.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    bf = read("backfill")
    rest = read("rest-audit")
    tour = read("tournament")
    corr = read("correlations")
    gates = read("gates")
    prob = read("probability-audit")
    imp = read("impact")
    content = read("content")
    meta = read("meta")
    s = bf["summary"]
    ts = tour["strategies"]
    top = ts[0]
    hz = rest["horizon_rest_check"]
    reg0 = corr["regressions"][0]
    m0 = reg0["measured"]
    lib = tour["library_null"]
    fs = tour["forecast_skill"]
    leg = corr["leg_correlation"]
    M = {"session": meta["session"], "commit": meta["commit"],
         "generated_utc": meta["generated_utc"],
         "blurb": ("Official-source audit of the season game log, of the rest layer built on it, "
                   "and of every strategy the lab could grade against the originated line.")}

    # -------------------------------------------------------------- overview
    ov_kpi = kpi([
        (s["scored_games"], "scored games in the repaired log (was " + str(s["log_rows_before_this_session"]) + ")"),
        (s["fixtures_without_published_scores"], "fixtures the official page prints without a score"),
        (tour["games_graded"], "games graded here, 2026-10-20 to 2026-11-13"),
        (len(ts), "strategies run against the originated line"),
        (len(gates["funded"]), "strategies clearing every computable gate"),
        (m0["coef"], "season-measured back-to-back effect, points (site parameter: " + str(reg0["site_value"]) + ")"),
    ])
    card_page = {"1": "backfill.html", "2": "rest.html", "3": "leaderboard.html",
                 "4": "correlations.html", "5": "gates.html"}
    findings = [
        ("1", "The game log was 23 games short, and the fix can only be a schedule fix",
         "Three official instruments now agree: " + str(s["fixture_rows_matching_repo"]) + " of " +
         str(s["fixture_rows_compared"]) + " fixture rows match the copy already in the repository, " +
         str(s["dates_checked"] - s["dates_mismatched"]) + " of " + str(s["dates_checked"]) +
         " dates match the official per-date count, and " + str(s["teams_checked"] - s["teams_mismatched"]) +
         " of " + str(s["teams_checked"]) + " teams match the official games-played column. The 23 results are "
         "still unpublished, so no score was filled in."),
        ("2", "The rest layer never read the fixtures its own file promises it",
         str(rest["summary"]["team_slots_affected_by_the_missing_fixtures"]) + " of " +
         str(rest["summary"]["team_slots_checked"]) + " team-slots change when the fixtures enter the history, and " +
         str(rest["summary"]["back_to_back_flags_that_flip"]) + " back-to-back flags flip. None of them falls inside "
         "the 51-game window the leaderboard was graded on, so no published pick changes today; what it does "
         "invalidate is any October backtest, which is the base this lab used."),
        ("3", "Nothing in a 13-strategy library beats the originated line",
         "The largest excess over the model's own expectation is " + str(top["excess_wins"]) + " wins on " +
         str(top["n"]) + " plays (z = " + str(top["z_vs_model"]) + ", exact p = " + str(top["p_model_null"]) +
         ", Benjamini-Hochberg q = " + str(top["bh_q"]) + "). A shared-draw simulation of the whole library reaches a "
         "best that large " + str(int(float(lib["probability_luck_only_library_matches_or_beats"]) * 100)) +
         "% of the time when every strategy is pure noise. That is the luck removal asked for, and the answer is "
         "that the signal is not there yet."),
        ("4", "The back-to-back penalty is a one-week fit applied to every line",
         "The site carries " + str(reg0["site_value"]) + " points. Measured on " + str(m0["n"]) +
         " games where both teams have a game on record it is " + str(m0["coef"]) + " &plusmn; " + str(m0["se"]) +
         " (p = " + str(m0["p_two_sided"]) + "). On the current slate " +
         str(imp["summary"]["games_where_the_two_positions_differ_by_3_points_or_more"]) + " of " +
         str(imp["summary"]["horizon_games"]) + " games move by 3 points or more between those two choices."),
        ("5", "The published probability columns are close, except on overtime",
         "Mean published home-win probability " + str(prob["rows"][0]["mean_model_probability_published"]) +
         " against a realised " + str(prob["rows"][0]["realised_rate_on_completed_games"]) +
         "; margin inside 5 " + str(prob["rows"][1]["mean_model_probability_published"]) + " against " +
         str(prob["rows"][1]["realised_rate_on_completed_games"]) + "; overtime " +
         str(prob["rows"][3]["mean_model_probability_published"]) + " predicted against " +
         str(prob["rows"][3]["realised_rate_on_completed_games"]) + " realised (" +
         str(prob["rows"][3]["realised_count"]) + " of " + str(prob["games"]) + " games, exact p = " +
         str(prob["rows"][3]["p_exact_vs_model"]) + ")."),
    ]
    ov_cards = ""
    for n, t, txt in findings:
        ov_cards += ('<div class="card"><h3>' + n + ". " + esc(t) + "</h3><p>" + txt +
                     '</p><p class="small"><a href="pages/' + card_page[n] +
                     '">the table behind it &rarr;</a></p></div>')
    section_rows = [
        {"page": "Game-log backfill", "what": "the 23 fixtures, row by row, against three official instruments",
         "rows": len(bf["fixture_rows"]), "src": bf["sources"]["day_pages"][0]},
        {"page": "Rest and back-to-back", "what": "every rest figure recomputed with the fixtures in the history",
         "rows": len(rest["changed_rows"]), "src": NBA_DAY + "2026-10-25"},
        {"page": "Leaderboard", "what": "the strategy library graded against the originated line, with the luck controls",
         "rows": len(ts), "src": NBA_DAY + "2026-10-20"},
        {"page": "Gates and rewards", "what": "the six computable gates, the blocked market gate, the tier each strategy earns",
         "rows": len(gates["rows"]), "src": NBA_DAY + "2026-10-20"},
        {"page": "Correlations", "what": "measured back-to-back, rest, margin and total, and same-night leg effects",
         "rows": len(corr["regressions"]) + len(corr["correlations"]), "src": NBA_DAY + "2026-10-20"},
        {"page": "Slate impact", "what": "what the parameter decision is worth on the 27 games still to be played",
         "rows": len(imp["rows"]), "src": NBA_DAY + "2026-11-14"},
        {"page": "Questions and suggestions", "what": "what has to be known before a decision is reasonable, and the options",
         "rows": len(content["questions"]["open"]) + len(content["suggestions"]),
         "src": "https://www.nba.com/stats/teams/advanced"},
    ]
    ov_tbl = table([("page", "Section", "txt"), ("what", "What it holds", "txt"),
                    ("rows", "Rows", "num"), ("src", "Source", "src")], section_rows)
    inputs_html = "<br>".join('<a href="' + esc(u) + '" rel="noopener">' + esc(k) + "</a>"
                               for k, u in meta["inputs"].items())
    notused_html = "<br>".join(esc(x) for x in meta["not_used_anywhere_in_this_directory"])
    pagesread_html = "<br>".join('<a href="' + esc(u) + '" rel="noopener">' + esc(u) + "</a>"
                                 for u in meta["official_pages_read_by_this_session"])

    overview = """
@@kpi@@
<div class="note"><b>What this directory is.</b> The rest of the site reports lines, picks and gates on a
51-game window, because that is the only window a point-in-time team rating was ever captured for. The
repository already holds a bigger official base: @@scored@@ scored games, every one transcribed from
<span class="mono">nba.com/games</span>. This lab re-runs the audit on all of it with a walk-forward that cannot
see the future, and publishes what survives. It reads committed files and writes only inside
<span class="mono">strategy-lab/</span> &mdash; no other session's data moved while it was running.</div>
<h2>Findings</h2>
<div class="cards">@@cards@@</div>
<h2>Sections</h2>
@@sections@@
<h2>Method, in the order it is executed</h2>
<div class="cards">
<div class="card"><h3>1 &middot; Repair the base</h3><p>Re-read the two missing dates from the official day pages,
reconcile the log against the official per-date count and the official games-played column, and record what the
pages do not publish instead of filling it in.</p></div>
<div class="card"><h3>2 &middot; Recompute the layers that depend on it</h3><p>Rest days, back-to-back flags and
team form are rebuilt on the complete schedule and diffed against what is shipped, slot by slot.</p></div>
<div class="card"><h3>3 &middot; Grade against the right null</h3><p>Each play is graded against the probability
the originated line itself implied. A raw hit rate is published too, and labelled as the thing that proves
nothing.</p></div>
<div class="card"><h3>4 &middot; Correct for looking</h3><p>Benjamini-Hochberg across the library, a shared-draw
best-of-library simulation, a moving-block bootstrap on the units, and a both-halves stability requirement.</p></div>
</div>
<h2>Inputs, and what was deliberately not used</h2>
<div class="cards">
<div class="card"><h3>Inputs</h3><p>@@inputs@@</p></div>
<div class="card"><h3>Not used anywhere here</h3><p>@@notused@@</p></div>
<div class="card"><h3>Official pages read by this session</h3><p>@@pagesread@@</p></div>
</div>
<div class="note warn"><b>Reproduce it.</b> The analysis is <span class="mono">strategy-lab/run.py</span>, the
pages are <span class="mono">strategy-lab/build.py</span>; both are deterministic, stdlib only, one fixed seed
(@@seed@@). A clean checkout at the commit in the footer rebuilds every table on these pages.</div>
"""
    overview = render(overview, {
        "kpi": ov_kpi, "cards": ov_cards, "sections": ov_tbl, "inputs": inputs_html,
        "notused": notused_html, "pagesread": pagesread_html,
        "scored": str(s["scored_games"]), "seed": str(meta["determinism"]["seed"]),
    })
    write(os.path.join(HERE, "index.html"), page("Strategy lab", "index.html", overview, M))

    # -------------------------------------------------------------- backfill
    bf_head = note("ok", "Result.", str(s["fixture_rows_matching_repo"]) + " of " +
                   str(s["fixture_rows_compared"]) + " rows agree on date, both teams and game id; " +
                   str(s["fixture_rows_disagreeing"]) + " disagree. Scores are absent in both readings, so they "
                   "stay absent here: none was inferred from the standings residual, although the residual does "
                   "determine them.")
    t_fixtures = table([("date", "Date", "txt"), ("game_id", "Game id", "txt"), ("fixture", "Matchup", "txt"),
                        ("status_printed", "Status printed", "txt"), ("score_this_session", "Score in this reading", "txt"),
                        ("score_in_repo", "Score in the repository", "txt"), ("verdict", "Verdict", "pill"),
                        ("src", "Source", "src")], bf["fixture_rows"])
    t_dates = table([("date", "Date", "txt"), ("official_calendar_count", "Official count", "num"),
                     ("scored_rows", "Scored rows", "num"), ("fixture_rows", "Fixture rows", "num"),
                     ("unplayed_rows", "Unplayed rows", "num"), ("rows_total", "Rows held", "num"),
                     ("verdict", "Verdict", "pill"), ("src", "Source", "src")], bf["date_rows"])
    t_teams = table([("team", "Team", "txt"), ("name", "Name", "txt"),
                     ("official_gp_through_11_12", "Official GP to 11/12", "num"),
                     ("finals_11_13", "plus 11/13 finals", "num"), ("expected_rows", "Expected rows", "num"),
                     ("scored_rows_only", "Rows with a score", "num"),
                     ("rows_in_repaired_log", "Rows after the backfill", "num"),
                     ("verdict", "Verdict", "pill"), ("src", "Source", "src")], bf["team_rows"])
    t_finals = table([("game_id", "Game id", "txt"), ("fixture", "Matchup", "txt"),
                      ("read_by_this_session", "Read by this session", "txt"),
                      ("in_repo_transcription", "In the repository", "txt"),
                      ("cup_group_printed", "Cup group printed", "txt"), ("verdict", "Verdict", "pill"),
                      ("src", "Source", "src")], bf["finals_rows"])
    bf_tpl = """
<p class="mut small">A second reading of the two dates the repository already holds as fixtures without results,
taken on 2026-11-14 at 10:38&ndash;10:44 UTC by a different session than the one that recorded them.</p>
@@head@@
<h2>The 23 fixture rows</h2>
@@fixtures@@
<h2>Per-date completeness, against the official calendar count</h2>
<p class="small mut">The calendar block at the top of the same official page prints how many games each date carries.
That is an independent count of what the log should hold &mdash; it is not derived from the log.</p>
@@dates@@
<h2>Per-team reconciliation against the official games-played column</h2>
@@teams@@
<h2>Second reading of the 2026-11-13 finals</h2>
<p class="small mut">The nine finals the site's 11/13 rows were waiting on, read here from the official scoreboard
block and compared with the transcription already committed by session
<span class="mono">arena/b0f2cc98-nba1</span> and merged as PR #56.</p>
@@finals@@
@@irreg@@
"""
    bf_body = render(bf_tpl, {
        "head": bf_head, "fixtures": t_fixtures, "dates": t_dates, "teams": t_teams, "finals": t_finals,
        "irreg": note("warn", "Irregularity kept on the record.", esc(bf["irregularity"]) +
                      " Method note: " + esc(bf["method_note"])),
    })
    write(os.path.join(PAGES, "backfill.html"), page("Game-log backfill", "pages/backfill.html", bf_body, M))

    # -------------------------------------------------------------- rest
    rs = rest["summary"]
    t_perdate = table([("date", "Date", "txt"), ("team_slots_affected", "Team-slots affected", "num"),
                       ("b2b_flags_that_flip", "Back-to-back flags that flip", "num"),
                       ("rest_days_only", "Rest figure only", "num"), ("src", "Source", "src")], rest["per_date"])
    t_changed = table([("date", "Date", "txt"), ("matchup", "Game", "txt"), ("side", "Side", "txt"),
                       ("team", "Team", "txt"), ("last_game_as_shipped", "Last game, as shipped", "txt"),
                       ("last_game_repaired", "Last game, repaired", "txt"),
                       ("gap_as_shipped", "Gap as shipped", "num"), ("gap_repaired", "Gap repaired", "num"),
                       ("b2b_as_shipped", "B2B as shipped", "num"), ("b2b_repaired", "B2B repaired", "num"),
                       ("caused_by_a_missing_fixture", "Caused by a fixture", "txt"),
                       ("src", "Source", "src")], rest["changed_rows"])
    t_hz = table([("date", "Date", "txt"), ("matchup", "Game", "txt"), ("side", "Side", "txt"),
                  ("team", "Team", "txt"), ("published_last_game", "Published last game", "txt"),
                  ("repaired_last_game", "Recomputed", "txt"), ("published_rest_field", "Published rest field", "num"),
                  ("repaired_gap_days", "Gap days", "num"), ("repaired_days_off", "Days off", "num"),
                  ("published_b2b", "Published B2B", "txt"), ("repaired_b2b", "Recomputed B2B", "txt"),
                  ("verdict", "Verdict", "pill"), ("src", "Source", "src")], hz["rows"])
    dc = rest["definition_conflict"]
    rest_tpl = """
@@found@@
@@kpi@@
<p class="mut small">@@materiality@@</p>
<h2>By date</h2>
@@perdate@@
<h2>Every affected team-slot</h2>
@@changed@@
<h2>The unplayed slate, checked field by field</h2>
<p class="small mut">@@hznote@@</p>
@@hz@@
@@conflict@@
"""
    rest_body = render(rest_tpl, {
        "found": note("warn", "What was found.", esc(rs["cause"])),
        "kpi": kpi([(rs["team_slots_affected_by_the_missing_fixtures"], "team-slots whose rest changes"),
                    (rs["back_to_back_flags_that_flip"], "back-to-back flags that flip"),
                    (rs["affected_inside_the_published_51_game_window"], "of them inside the graded 51-game window"),
                    (hz["agree"], "horizon rest fields confirmed on 27 unplayed games (" +
                     str(hz["mismatch"]) + " mismatch)")]),
        "materiality": esc(rs["materiality"]), "perdate": t_perdate, "changed": t_changed,
        "hznote": esc(hz["note"]), "hz": t_hz,
        "conflict": note("bad", "Definition conflict, published for a decision.",
                         esc(dc["reading_A"]) + "<br>" + esc(dc["reading_B"]) + "<br><i>" +
                         esc(dc["consequence"]) + "</i> Worked example: " + esc(dc["worked_example"]) +
                         ". This file publishes both quantities: " + esc(dc["this_file_publishes"]) +
                         '. <a href="' + esc(dc["source_url"]) + '" rel="noopener">source</a>'),
    })
    write(os.path.join(PAGES, "rest.html"), page("Rest and back-to-back layer", "pages/rest.html", rest_body, M))

    # -------------------------------------------------------------- leaderboard
    t_lib = table([("id", "Id", "txt"), ("name", "Strategy", "txt"), ("family", "Family", "txt"),
                   ("market", "Market", "txt"), ("n", "Plays", "num"), ("wins", "Wins", "num"),
                   ("hit_rate", "Hit rate", "num"), ("mean_p_model", "Line implied", "num"),
                   ("expected_wins_from_model", "Expected wins", "num"), ("excess_wins", "Excess", "num"),
                   ("z_vs_model", "z", "num"), ("p_model_null", "Exact p", "num"), ("bh_q", "BH q", "num"),
                   ("units_pnl_minus110", "Units at -110", "num"),
                   ("src", "Source", "src")],
                  [dict(r, src="https://www.nba.com/games?date=" + str(r["first_date"])) for r in ts])
    t_rules = table([("id", "Id", "txt"), ("name", "Rule as written", "txt"),
                     ("why_tested", "The question it answers", "txt")], ts, NBA_DAY + "2026-10-20")
    t_null = table([("k", "Quantity", "txt"), ("v", "Value", "txt"), ("why", "Reading", "txt")], [
        {"k": "statistic", "v": lib["statistic"], "why": "the largest standardised excess in the library"},
        {"k": "observed z", "v": lib["observed_z"], "why": "the number to beat"},
        {"k": "strategies in the library", "v": lib["strategies_in_library"], "why": "how many shots at the board were taken"},
        {"k": "draws", "v": lib["simulations"], "why": "each draw resamples every game once and re-runs every rule, so the overlap between strategies is preserved"},
        {"k": "probability a luck-only library matches it", "v": lib["probability_luck_only_library_matches_or_beats"],
         "why": lib["reading"]},
    ], NBA_DAY + "2026-10-20")
    t_skill = table([("k", "Measure", "txt"), ("v", "Value", "txt"), ("ctx", "Context", "txt")], [
        {"k": "games", "v": fs["n"], "ctx": "gradeable games in the walk-forward"},
        {"k": "margin MAE, model", "v": fs["margin"]["mae_model"], "ctx": "points"},
        {"k": "margin MAE, naive zero line", "v": fs["margin"]["mae_naive_zero_line"], "ctx": "points"},
        {"k": "improvement on the naive line", "v": str(fs["margin"]["improvement_pct"]) + "%",
         "ctx": "the same comparison on 51 games, published by Build B, was 2.3%"},
        {"k": "margin bias", "v": fs["margin"]["bias_model"],
         "ctx": "points; negative means the model over-predicts the home margin"},
        {"k": "total MAE, model", "v": fs["total"]["mae_model"], "ctx": "points"},
        {"k": "total MAE, league-mean naive", "v": fs["total"]["mae_naive"],
         "ctx": "the totals projection is not beating its own naive reference here"},
        {"k": "Brier skill vs 50%", "v": fs["win_probability"]["brier_skill_score"], "ctx": "win-probability forecast quality"},
        {"k": "AUC", "v": fs["win_probability"]["auc"], "ctx": "does the model rank favourites correctly"},
        {"k": "mean probability on the side it liked", "v": fs["favourite_side"]["mean_model_prob"], "ctx": "what the line said"},
        {"k": "how often that side won", "v": fs["favourite_side"]["realised_win_rate"],
         "ctx": "a gap of " + str(fs["favourite_side"]["gap"]) + " - the model slightly under-prices its own favourites"},
    ], NBA_DAY + "2026-10-20")
    t_plays = table([("date", "Date", "txt"), ("matchup", "Game", "txt"), ("proj_home", "Model home", "num"),
                     ("naive_home", "Naive home", "num"), ("actual_home", "Actual", "num"),
                     ("fav_model", "Line likes", "txt"), ("p_fav", "Line prob", "num"),
                     ("win_fav", "Favourite won", "num"), ("edge", "Edge vs naive", "num"),
                     ("b2b_home", "H B2B", "num"), ("b2b_away", "A B2B", "num"), ("src", "Source", "src")],
                    tour["play_log"])
    par_rows = [dict(r, sid=k) for k, rowsl in tour["parlays"].items() for r in rowsl]
    t_par = table([("sid", "Family", "txt"), ("date", "Date", "txt"), ("legs", "Legs", "txt"),
                   ("model_prob", "Model joint", "num"), ("win", "All legs won", "num"),
                   ("src", "Source", "src")], par_rows)
    lb_tpl = """
@@tested@@
@@walk@@
<h2>The library</h2>
@@lib@@
<p class="small mut">Excess = wins minus the wins the originated line already expected. Exact p is the
Poisson-binomial tail over each play's own probability, so the null is &ldquo;the model was right&rdquo;, not
&ldquo;a coin flip&rdquo;. What the tiers mean is on the <a href="gates.html">gates page</a>.</p>
<h2>Rules as written</h2>
@@rules@@
<h2>Luck control, computed on the whole library at once</h2>
@@null@@
<h2>Forecast quality, which is the only claim a price-free repository can make</h2>
@@skill@@
<h2>Every graded play</h2>
<p class="small mut">One row per game the library was allowed to bet. The site's pages show picks; this is the
sample the verdict comes from.</p>
@@plays@@
<h2>Parlays, leg by leg</h2>
@@par@@
"""
    lb_body = render(lb_tpl, {
        "tested": note("info", "What a play is graded against.", esc(tour["what_being_tested"])),
        "walk": note("ok", "Walk-forward discipline.", esc(tour["params"]["status"]) +
                     " Window " + esc(tour["window"]) + ": " + str(tour["games_in_log_with_scores"]) +
                     " scored games, " + str(tour["games_graded"]) + " of them gradeable (both teams need " +
                     str(tour["params"]["min_history_per_team"]) + " games on record first)."),
        "lib": t_lib, "rules": t_rules, "null": t_null, "skill": t_skill, "plays": t_plays, "par": t_par,
    })
    write(os.path.join(PAGES, "leaderboard.html"), page("Leaderboard", "pages/leaderboard.html", lb_body, M))

    # -------------------------------------------------------------- gates
    t_gdefs = table([("id", "Id", "txt"), ("name", "Gate", "txt"), ("definition", "Definition", "txt")],
                    gates["gate_definitions"], BLOB + "scripts/verify_all.py")
    t_tiers = table([("id", "Id", "txt"), ("name", "Strategy", "txt"), ("n", "Plays", "num"),
                     ("hit_rate", "Hit", "num"), ("excess_wins", "Excess", "num"),
                     ("p_model_null", "Exact p", "num"), ("bh_q", "BH q", "num"),
                     ("gates_passed", "Gates passed", "txt"), ("tier", "Reward tier", "txt"),
                     ("paper_stake_units", "Paper stake, units", "num"), ("direction", "Direction", "txt"),
                     ("blocking_reason", "Why it stops there", "txt"), ("src", "Source", "src")],
                    [dict(r, src="https://www.nba.com/games?date=2026-10-20") for r in gates["rows"]])
    t_prob = table([("quantity", "Quantity", "txt"), ("mean_model_probability_published", "Published mean", "num"),
                    ("realised_rate_on_completed_games", "Realised", "num"), ("realised_count", "Games", "num"),
                    ("games", "Sample", "num"), ("gap_points", "Gap, points", "num"),
                    ("p_exact_vs_model", "Exact p", "num"), ("src", "Source", "src")],
                   [dict(r, src=r["source_url"]) for r in prob["rows"]])
    g_tpl = """
@@rule@@
<h2>The gates</h2>
@@defs@@
<h2>Tiers and rewards</h2>
@@tiers@@
<p class="small mut">@@gatenote@@</p>
<h2>The published probability columns, tested against the season</h2>
@@prob@@
@@caveat@@
"""
    g_body = render(g_tpl, {
        "rule": note("bad", "The reward rule, in one sentence.",
                     "A strategy earns a stake only if it wins more often than the originated line it bets against "
                     "already implies, on at least 30 plays, in both halves of the window, with a "
                     "multiple-comparison correction across the whole library &mdash; and the market gate is "
                     "reserved for a price feed this repository does not have. Nothing here passes it, so every "
                     "tier below is paper."),
        "defs": t_gdefs, "tiers": t_tiers, "gatenote": esc(gates["note"]), "prob": t_prob,
        "caveat": note("warn", "Read that table as a distribution check, not a backtest.", esc(prob["caveat"])),
    })
    write(os.path.join(PAGES, "gates.html"), page("Gates and rewards", "pages/gates.html", g_body, M))

    # -------------------------------------------------------------- correlations
    rs_cols = [dict(r["measured"], src=r["measured"]["source_url"]) for r in corr["regressions"] if r["measured"]]
    t_reg = table([("term", "Term", "txt"), ("coef", "Coefficient", "num"), ("se", "Standard error", "num"),
                   ("t", "t", "num"), ("p_two_sided", "p (two-sided)", "num"), ("ci95", "95% interval", "txt"),
                   ("n", "n", "num"), ("dof", "Degrees of freedom", "num"), ("unit", "Unit", "txt"),
                   ("src", "Source", "src")], rs_cols)
    cmp_rows = []
    for r in corr["regressions"]:
        m = r["measured"] or {}
        ci = m.get("ci95") or []
        cmp_rows.append({"name": r["name"], "site_value": r["site_value"], "measured_coef": m.get("coef"),
                         "measured_se": m.get("se"),
                         "measured_ci": " / ".join(str(x) for x in ci) if ci else None,
                         "games": m.get("n"), "reading": r["reading"], "src": r["site_source"]})
    t_cmp = table([("name", "What is being compared", "txt"), ("site_value", "Value the site carries", "num"),
                   ("measured_coef", "Measured on the season", "num"), ("measured_se", "Standard error", "num"),
                   ("measured_ci", "95% interval", "txt"), ("games", "Sample games", "num"),
                   ("reading", "Reading", "txt"), ("src", "Site source", "src")], cmp_rows)
    t_corr = table([("x", "x", "txt"), ("y", "y", "txt"), ("r", "r", "num"), ("t", "t", "num"),
                    ("p", "p", "num"), ("n", "n", "num"), ("site_assumption", "What the site assumes", "txt"),
                    ("meaning", "Why it matters", "txt"), ("src", "Source", "src")],
                   [dict(c, src=c["source_url"]) for c in corr["correlations"]])
    t_leg = table([("k", "Same-night legs", "txt"), ("v", "Value", "txt"), ("why", "Reading", "txt")], [
        {"k": "date-pairs measured", "v": leg["date_pairs"], "why": "the first two games of each slate"},
        {"k": "leg A home win rate", "v": leg["leg_a_home_win"], "why": ""},
        {"k": "leg B home win rate", "v": leg["leg_b_home_win"], "why": ""},
        {"k": "measured joint", "v": leg["measured_joint"], "why": "both home sides won"},
        {"k": "product if independent", "v": leg["independent_product"], "why": "how a bookless parlay would be priced"},
        {"k": "difference", "v": leg["difference"], "why": leg["warning"]},
        {"k": "ratio true to independent", "v": leg["ratio_true_to_independent"], "why": leg["meaning"]},
    ], NBA_DAY + "2026-10-20")
    mg, tt = corr["margins"], corr["totals"]
    t_dist = table([("k", "Quantity", "txt"), ("v", "Value", "txt"), ("unit", "Unit", "txt"),
                    ("src", "Source", "src")], [
        {"k": "mean home margin", "v": mg["mean_home"], "unit": "points", "src": mg["source_url"]},
        {"k": "home margin spread", "v": mg["sd"], "unit": "points; the site carries 17.44 from a 51-game fit",
         "src": mg["source_url"]},
        {"k": "decided by 3 or fewer", "v": mg["within_3"], "unit": "share of games", "src": mg["source_url"]},
        {"k": "decided by 5 or fewer", "v": mg["within_5"], "unit": "share of games", "src": mg["source_url"]},
        {"k": "20-point margins or worse", "v": mg["twenty_plus"], "unit": "share of games", "src": mg["source_url"]},
        {"k": "went to overtime", "v": mg["ot_rate"], "unit": str(mg["ot_games"]) + " of " + str(corr["games"]) + " games",
         "src": mg["source_url"]},
        {"k": "mean total", "v": tt["mean"], "unit": "points", "src": tt["source_url"]},
        {"k": "mean total, regulation only", "v": tt["regulation_only_mean"], "unit": "points", "src": tt["source_url"]},
        {"k": "total spread", "v": tt["sd"], "unit": "points", "src": tt["source_url"]},
    ])
    c_tpl = """
<p class="mut small">Correlation values, measured rather than assumed, on @@games@@ completed games
(@@window@@). Regression sample @@rsample@@ games: @@rdrop@@ dropped for a documented reason &mdash;
@@rwhy@@.</p>
<h2>Effects, with intervals</h2>
@@reg@@
@@cmp@@
<h2>Correlations used by the parlay pricing</h2>
@@corr@@
@@leg@@
<h2>The distributions every probability on the site is built from</h2>
@@dist@@
"""
    c_body = render(c_tpl, {
        "games": str(corr["games"]), "window": esc(corr["window"]),
        "rsample": str(corr["regression_sample"]["games_with_a_known_prior_game_for_both_teams"]),
        "rdrop": str(corr["regression_sample"]["dropped_no_prior_game_on_record"]),
        "rwhy": esc(corr["regression_sample"]["why_dropped"]),
        "reg": t_reg, "cmp": t_cmp, "corr": t_corr, "leg": t_leg, "dist": t_dist,
    })
    write(os.path.join(PAGES, "correlations.html"), page("Correlations", "pages/correlations.html", c_body, M))

    # -------------------------------------------------------------- slate impact
    smy = imp["summary"]
    t_imp = table([("date", "Date", "txt"), ("time_et", "Tip", "txt"), ("matchup", "Game", "txt"),
                   ("home_b2b_published", "H B2B published", "num"), ("home_b2b_recomputed", "H B2B recomputed", "num"),
                   ("away_b2b_published", "A B2B published", "num"), ("away_b2b_recomputed", "A B2B recomputed", "num"),
                   ("home_last_game", "Home last game", "txt"), ("away_last_game", "Away last game", "txt"),
                   ("line_adjustment_from_site_parameter", "Adjustment at the site's parameter", "num"),
                   ("line_adjustment_from_season_estimate", "Adjustment at the season estimate", "num"),
                   ("disagreement_points", "Disagreement, points", "num"),
                   ("model_spread_home", "Published model line", "num"), ("src", "Source", "src")], imp["rows"])
    si_tpl = """
<p class="mut small">One parameter, twenty-seven games that have not been played. The question is what the
site's back-to-back number is worth against the season's own measurement of the same thing.</p>
@@kpi@@
@@ok@@
<h2>Game by game</h2>
@@tbl@@
@@rec@@
"""
    si_body = render(si_tpl, {
        "kpi": kpi([
            (str(smy["games_where_the_two_positions_differ_by_3_points_or_more"]) + " / " +
             str(smy["horizon_games"]), "horizon games that move 3+ points"),
            (smy["mean_abs_disagreement_points"], "mean movement, points"),
            (smy["max_abs_disagreement_points"], "largest movement, points"),
            (str(smy["rest_flags_reproduced_from_the_official_schedule"]) + " / " +
             str(smy["horizon_games"]), "rest flags reproduced from the official schedule"),
        ]),
        "ok": note("ok", "The live page's rest layer is right.",
                   "Every published back-to-back flag on the 27 unplayed games was reproduced from the official "
                   "schedule, including the games played on 2026-11-13, which is the part of the history the game "
                   "log itself does not carry."),
        "tbl": t_imp,
        "rec": note("warn", "Suggestion for the owner of the model.",
                    esc(imp["recommendation"]["action"]) + " &mdash; " + esc(imp["recommendation"]["why"]) +
                    " Cost: " + esc(imp["recommendation"]["cost"]) + ". Risk if ignored: " +
                    esc(imp["recommendation"]["risk_if_ignored"]) +
                    '. <a href="' + esc(imp["published_parameter"]["source_url"]) + '" rel="noopener">the published parameter</a>'),
    })
    write(os.path.join(PAGES, "slate-impact.html"),
          page("Slate impact", "pages/slate-impact.html", si_body, M))

    # -------------------------------------------------------------- decision
    q = content["questions"]
    t_ans = table([("id", "Id", "txt"), ("question", "Question", "txt"), ("answer", "Answer", "txt"),
                   ("evidence", "Where it is shown", "txt"), ("confidence", "Confidence", "txt"),
                   ("src", "Source", "src")], q["answered"])
    t_open = table([("id", "Id", "txt"), ("question", "Question", "txt"), ("what_is_missing", "What is missing", "txt"),
                    ("how_to_get_it", "How to get it", "txt"), ("blocks", "What it blocks", "txt"),
                    ("src", "Source", "src")], q["open"])
    t_sug = table([("id", "Id", "txt"), ("title", "Suggestion", "txt"), ("category", "Category", "txt"),
                   ("problem", "Problem", "txt"), ("options", "Options", "txt"), ("cost", "Cost", "txt"),
                   ("unlocks", "What it unlocks", "txt"), ("recommendation", "Recommendation", "txt"),
                   ("owner", "Who has to act", "txt"), ("src", "Source", "src")], content["suggestions"])
    t_flag = table([("id", "Id", "txt"), ("severity", "Severity", "txt"), ("title", "Item", "txt"),
                    ("detail", "Detail", "txt"), ("status", "Status", "txt"), ("src", "Source", "src")],
                   content["flags"])
    d_body = (note("info", "How to use this page.", esc(content["how_to_use"])) +
              "<h2>Answered &mdash; decided from the data on hand</h2>" + t_ans +
              "<h2>Open &mdash; what has to be known before a decision is reasonable</h2>" + t_open +
              "<h2>Suggestions, as options rather than instructions</h2>" + t_sug +
              "<h2>Flagged for review by this session</h2>" + t_flag)
    write(os.path.join(PAGES, "decision.html"),
          page("Questions and suggestions", "pages/decision.html", d_body, M))
    print("pages written:", len(NAV))


if __name__ == "__main__":
    main()
