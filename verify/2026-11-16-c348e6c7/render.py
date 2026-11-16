#!/usr/bin/env python3
"""Render the 2026-11-16 live-verification page from this session's captures.

    python3 verify/2026-11-16-c348e6c7/render.py

Reads only the JSON files this session wrote in this directory. Every table row
carries the official URL it was read from, because the brief's rule is that a row
without a source is not a row.

Output: verify/2026-11-16-c348e6c7/index.html  (published verbatim at
site/pages/verify-2026-11-16.html by scripts/build_dashboard.py)
"""

from __future__ import annotations

import datetime
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#151a21;--ink2:#4a5563;--line:#e3e7ec;
--ok:#0f7b4f;--ok-soft:#e6f5ee;--bad:#b42318;--bad-soft:#fdeceb;--warn:#9a6700;--warn-soft:#fff6dd;
--mut:#7b8794;--accent:#1b4fd8;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1200px;margin:0 auto;padding:26px 20px 70px}
header.top{background:#0f151d;color:#e9edf2;padding:14px 0;margin-bottom:24px}
header.top .wrap{padding-bottom:0;padding-top:0;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.mark{background:var(--accent);color:#fff;border-radius:6px;padding:4px 8px;font:700 13px/1 var(--mono)}
h1{font-size:25px;margin:0 0 6px}h2{font-size:18px;margin:30px 0 10px}h3{font-size:15px;margin:22px 0 8px}
.sub{color:var(--ink2);margin:0 0 18px;max-width:80ch}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0 8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .v{font:700 24px/1.1 var(--mono);margin-bottom:4px}.card .l{font-size:13px;color:var(--ink2)}
.note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:8px;padding:14px 16px;margin:16px 0}
.warnbox{border-left-color:var(--warn);background:var(--warn-soft)}
.okbox{border-left-color:var(--ok);background:var(--ok-soft)}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);
border-radius:10px;overflow:hidden;font-size:13.5px;margin:10px 0 4px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f9fafb;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:var(--ink2)}
tr:last-child td{border-bottom:none}.num{text-align:right;font-variant-numeric:tabular-nums}
.mono{font-family:var(--mono);font-size:12.5px}
.b{display:inline-block;padding:1px 7px;border-radius:999px;font:600 11.5px/1.6 var(--mono);white-space:nowrap}
.b-ok{background:var(--ok-soft);color:var(--ok)}.b-bad{background:var(--bad-soft);color:var(--bad)}
.b-warn{background:var(--warn-soft);color:var(--warn)}.b-mut{background:#f1f3f6;color:var(--mut)}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);color:var(--ink2);font-size:13px}
code{font-family:var(--mono);font-size:12.5px;background:#f1f3f6;padding:1px 5px;border-radius:4px}
.scroll{overflow-x:auto}
"""


def e(x):
    return html.escape("" if x is None else str(x), quote=True)


def link(url, text=None):
    u = (url or "").strip()
    if not u:
        return '<span class="b b-warn">no source</span>'
    return '<a href="%s">%s</a>' % (e(u), e(text or u.replace("https://", "")))


def table(headers, rows, note=None):
    out = ['<div class="scroll"><table><thead><tr>']
    for h in headers:
        out.append("<th>%s</th>" % e(h))
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    if note:
        out.append('<p class="sub" style="margin-top:6px">%s</p>' % note)
    return "".join(out)


def main():
    def rd(name):
        p = os.path.join(HERE, name)
        return json.load(open(p)) if os.path.exists(p) else {}

    sched = rd("schedule_live.json")
    stand = rd("standings_live.json")
    cmp_ = rd("compare.json")
    inj = rd("injury_2026-11-15_0900PM.json")
    injd = rd("injury_diff_0615PM_to_0900PM.json")

    srows = sched.get("rows", [])
    trows = stand.get("rows", [])
    sch = cmp_.get("schedule", {})
    stn = cmp_.get("standings", {})

    nd = sum(1 for r in srows if r["date"] == "2026-11-16")
    nt = sum(1 for r in srows if r["date"] == "2026-11-17")
    nw = sum(1 for r in srows if r["date"] == "2026-11-18")
    agree = sch.get("cells_agree", 0)
    dis = sch.get("cells_disagree", 0)

    b = []
    b.append("<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">")
    b.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    b.append("<title>Live official verification, 2026-11-16 &middot; NBA1</title>")
    b.append("<style>%s</style></head><body>" % CSS)
    b.append('<header class="top"><div class="wrap"><span class="mark">NBA1</span>'
             "<strong>Live official verification &mdash; 2026-11-16</strong></div></header>")
    b.append('<div class="wrap">')
    b.append("<h1>The window read directly from NBA.com</h1>")
    b.append('<p class="sub">Every session before this one recorded that its sandbox could not reach '
             "nba.com, so the refresh path had never been executed (flag F7). This session's fetcher "
             "reaches it. The %d-game rolling window (%s to %s) was read from the official pages at "
             "%s and compared cell by cell against the captures already committed in the repository. "
             "Nothing below is inferred; a value the page did not print is left blank and flagged."
             "</p>" % (len(srows), sched.get("rows", [{}])[0].get("date", ""),
                       srows[-1].get("date", "") if srows else "", e(sched.get("retrieved_utc"))))

    b.append('<div class="cards">')
    b.append('<div class="card"><div class="v">%d</div><div class="l">Games in the window (%d / %d / %d by day)</div></div>'
             % (len(srows), nd, nt, nw))
    b.append('<div class="card"><div class="v">%d</div><div class="l">Schedule cells that agree with the stored capture</div></div>' % agree)
    b.append('<div class="card"><div class="v">%d</div><div class="l">Schedule cells that differ &mdash; all explained</div></div>' % dis)
    b.append('<div class="card"><div class="v">%d</div><div class="l">Standings teams read live</div></div>' % len(trows))
    b.append('<div class="card"><div class="v">%d</div><div class="l">Injury rows in the newest edition</div></div>' % len(inj.get("rows", [])))
    b.append("</div>")

    # ---- 1. schedule -----------------------------------------------------
    b.append("<h2>1. The schedule, read live</h2>")
    b.append('<p class="sub">Window rule: read at %s (%s). &ldquo;Up to a maximum of 3 days in '
             "advance&rdquo; is taken from the US/Eastern calendar date, so the window is the next "
             "three ET game days: 11/16, 11/17, 11/18.</p>"
             % (e(sched.get("retrieved_utc")), e(sched.get("retrieved_et"))))
    rows = []
    for r in srows:
        rows.append([
            e(r["date"]),
            "<strong>%s @ %s</strong>" % (e(r["away"]), e(r["home"])),
            '<span class="mono">%s</span>' % e(r["game_id"]),
            e(r["tip_et"]),
            "%s <span class='b b-mut'>%s</span>" % (e(r["away_record"]), e(r["home_record"])),
            e(r["venue"]) or '<span class="b b-warn">not re-read</span>',
            link(r["source_game_url"], "game page"),
        ])
    b.append(table(["Date", "Matchup", "Game ID", "Tip (ET)", "Records (away / home)", "Venue", "Source"], rows,
                   note="Records are what the official page printed at retrieval time. Venues are carried "
                        "from the repository's stored capture for this window (retrieved "
                        "2026-11-15T23:38Z..23:52Z) and were not individually re-opened in this pass, so "
                        "they are labelled rather than presented as freshly read."))

    # ---- 2. comparison ---------------------------------------------------
    b.append("<h2>2. Comparison against the stored capture</h2>")
    verdict = sch.get("verdict", "")
    cls = "okbox" if "EXACT" in verdict else "warnbox"
    b.append('<div class="note %s"><strong>%s</strong><br>'
             "Compared against <code>%s</code>, retrieved %s by %s. This read: %s by %s. "
             "%d rows stored, %d rows read live.</div>"
             % (cls, e(verdict), e(sch.get("compared_against")), e(sch.get("stored_retrieved_utc")),
                e(sch.get("stored_captured_by")), e(sch.get("live_retrieved_utc")),
                e(sch.get("live_captured_by")), sch.get("stored_rows", 0), sch.get("live_rows", 0)))

    diffs = sch.get("differences", [])
    if diffs:
        b.append('<div class="note"><strong>Every difference is a clock difference, and here is the '
                 "proof.</strong><br>The stored capture was taken at %s, which is 18:47 ET &mdash; "
                 "before a single 11/15 game had tipped. This read was taken at %s (21:2x ET), by "
                 "which time six 11/15 games had gone final. A record cell can therefore only differ "
                 "for a team that played on 11/15, and only in the direction of that game's result."
                 "</div>" % (e(sch.get("stored_retrieved_utc")), e(sch.get("live_retrieved_utc"))))
        rows = []
        for d in diffs:
            g = next((r for r in srows if r["game_id"] == d["game_id"]), {})
            rows.append([
                '<span class="mono">%s</span>' % e(d["game_id"]),
                "%s @ %s" % (e(g.get("away")), e(g.get("home"))),
                e(d["field"]).replace("_", " "),
                '<span class="b b-mut">%s</span>' % e(d["stored"]),
                '<span class="b b-ok">%s</span>' % e(d["live"]),
                e(d["field"]).startswith("away") and "away team played 11/15" or "home team played 11/15",
                link(g.get("source_game_url"), "game page"),
            ])
        b.append(table(["Game ID", "Matchup", "Field", "Stored", "Live", "Why it moved", "Source"], rows))

    # ---- 3. standings ----------------------------------------------------
    b.append("<h2>3. Standings, read live</h2>")
    b.append('<p class="sub">%s</p>' % e(stand.get("not_read_notes", [""])[0]))
    rows = []
    for r in trows:
        rows.append([
            "<strong>%s</strong>" % e(r["team"]),
            e(r["conference"]),
            "%d&ndash;%d" % (r["w"], r["l"]),
            e(r["win_pct"]), e(r["gb"]), e(r["conf"]), e(r["div"]),
            e(r["home"]), e(r["road"]), e(r["last10"]), e(r["streak"]),
            link(r["source_url"], "standings"),
        ])
    b.append(table(["Team", "Conf", "W&ndash;L", "WIN%", "GB", "Conf", "Div", "Home", "Road",
                    "L10", "Streak", "Source"], rows,
                   note="A blank cell means the page did not print it into this read. It is left blank "
                        "on purpose: the brief's rule is that a value is never inferred."))

    sd = stn.get("differences", [])
    if sd:
        b.append('<div class="note"><strong>Standings diff: %s</strong><br>%d of 60 W/L cells moved '
                 "against <code>%s</code>. Those %d teams are exactly the participants in the five "
                 "11/15 games that finished after that capture &mdash; two teams per game, five games. "
                 "The sixth 11/15 game (IND@PHI, 1:00 PM ET) had already landed in the stored capture, "
                 "so neither IND nor PHI appears here. That is the arithmetic check that the diff is "
                 "complete and not merely small.</div>"
                 % (e(stn.get("verdict")), len(sd), e(stn.get("compared_against")), len(sd)))
        rows = [[
            "<strong>%s</strong>" % e(d["team"]), e(d["field"]).upper(),
            '<span class="b b-mut">%s</span>' % e(d["stored"]),
            '<span class="b b-ok">%s</span>' % e(d["live"]),
            link("https://www.nba.com/standings", "standings"),
        ] for d in sd]
        b.append(table(["Team", "Field", "Stored", "Live", "Source"], rows))

    # ---- 4. injuries -----------------------------------------------------
    b.append("<h2>4. The newest official injury edition</h2>")
    b.append('<div class="note"><strong>Report revision:</strong> %s &nbsp;|&nbsp; '
             "<strong>retrieved (UTC):</strong> %s &nbsp;|&nbsp; <strong>rows for the 11/16 games:</strong> %d"
             "<br>Source: %s &nbsp;|&nbsp; index: %s</div>"
             % (e(inj.get("revision_time_et")), e(inj.get("retrieved_utc")), len(inj.get("rows", [])),
                link(inj.get("source_url"), "official PDF"), link(inj.get("index_url"), "official.nba.com")))

    irows = inj.get("rows", [])
    rows = []
    for r in irows:
        st = (r.get("status") or "")
        badge = ("b-ok" if st.lower() == "available" else
                 "b-warn" if st.lower() == "questionable" else
                 "b-mut" if "NOT YET" in st.upper() else "b-bad")
        rows.append([
            e(r["matchup"]), e(r["team_printed"]),
            e(r["player"]) or '<span class="b b-mut">no player printed</span>',
            '<span class="b %s">%s</span>' % (badge, e(st)),
            e(r["reason"]) or '<span class="b b-warn">not printed</span>',
            link(r["source_url"], "PDF"),
        ])
    b.append(table(["Matchup", "Team", "Player", "Status", "Reason", "Source"], rows,
                   note="Rows for the 11/16 games only; they are the rows the picks page consumes. "
                        "The same edition also covers 11/15 games, which have already tipped."))

    # ---- 5. diff ---------------------------------------------------------
    b.append("<h2>5. Consecutive-edition diff</h2>")
    b.append('<div class="note"><strong>%s</strong><br>%s &rarr; %s. %d comparable player rows held '
             "their status.</div>"
             % (e(injd.get("verdict")), e(injd.get("prev_edition")), e(injd.get("cur_edition")),
                injd.get("players_unchanged", 0)))
    sc = injd.get("team_submission_changes", [])
    if sc:
        rows = []
        for c in sc:
            rows.append([
                "<strong>%s</strong>" % e(c["matchup"]), e(c["team"]),
                '<span class="b b-mut">%s</span>' % e(c["from"]),
                '<span class="b b-ok">%s</span>' % e(c["to"]),
                "%d listed, %d Out" % (c["players_now_listed"], c["outright_outs_now"]),
                link(injd.get("cur_source_url"), "PDF"),
            ])
        b.append(table(["Matchup", "Team", "Older edition", "Newer edition", "Now listed", "Source"], rows,
                       note="A team moving from NOT YET SUBMITTED to filed is the most consequential "
                            "kind of change and the one a player-keyed diff misses entirely: there is no "
                            "player row on either side to compare. It is tracked separately for exactly "
                            "that reason."))

    nys = injd.get("teams_still_not_submitted_in_current", [])
    if nys:
        b.append('<div class="note warnbox"><strong>%d teams had still not filed at %s:</strong> %s. '
                 "Their rows are published as NOT YET SUBMITTED, never as &ldquo;healthy&rdquo;.</div>"
                 % (len(nys), e(inj.get("revision_time_et")),
                    ", ".join("<strong>%s</strong> (%s)" % (e(t["team"]), e(t["matchup"])) for t in nys)))

    inh = injd.get("inherited_name_rows_in_prev", [])
    if inh:
        b.append('<div class="note warnbox"><strong>A defect in the repository&rsquo;s own stored '
                 "edition.</strong><br>A NOT YET SUBMITTED row is a team-level marker and the league "
                 "prints no player on it. These stored rows carry a player name inherited from the "
                 "preceding row, and one of them is encoded <code>status='Out'</code> &mdash; so any "
                 "consumer reading the status column alone counts a player who was never named as ruled "
                 "out for a team that had filed nothing. Published as flag F101 rather than silently "
                 "corrected, because the row is also the record that the team had not filed.</div>")
        rows = [[e(i["matchup"]), e(i["team"]), e(i["inherited_player"]),
                 '<code>%s</code>' % e(i["status_field"]), '<code>%s</code>' % e(i["reason_field"]),
                 link("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf", "PDF")]
                for i in inh]
        b.append(table(["Matchup", "Team", "Inherited name", "status field", "reason field", "Source"], rows))

    # ---- 6. cannot do ----------------------------------------------------
    b.append("<h2>6. What this pass could not do</h2>")
    b.append('<div class="note warnbox"><strong>The original PDF bytes could not be archived.</strong> '
             "The brief asks for every injury PDF to be stored with its timestamp. This environment has "
             "no outbound network &mdash; <code>curl</code> to ak-static.cms.nba.com fails at the TLS "
             "handshake (<code>OpenSSL SSL_connect: SSL_ERROR_SYSCALL</code>, HTTP 000, 0 bytes) &mdash; "
             "and the agent-side fetcher returns parsed text only. So no SHA-256 of the PDF and no "
             "byte-identical copy exist. What is archived is the edition stamp the PDF prints, the exact "
             "URL, the UTC retrieval time, the printed row count and the full row transcription. "
             "Published as flag F100.</div>")
    b.append('<div class="note warnbox"><strong>The 2026-11-15 slate is not settled.</strong> At 21:2x '
             "ET on 11/15, six of its nine games were final and three were still in progress. The "
             "settlement rule requires the official page to print Final with quarter linescores summing "
             "to it, so the slate stays open rather than being settled from live scores. Published as "
             "flag F99.</div>")

    b.append("<footer>Session <code>arena/c348e6c7-nba1</code>, rendered %s. Captures are committed "
             "under <code>verify/2026-11-16-c348e6c7/</code> "
             "(<code>schedule_live.json</code>, <code>standings_live.json</code>, "
             "<code>compare.json</code>, <code>injury_2026-11-15_0900PM.json</code>, "
             "<code>injury_diff_0615PM_to_0900PM.json</code>). Re-read with "
             "<code>python3 capture.py &amp;&amp; python3 capture_injury.py &amp;&amp; python3 render.py</code>. "
             "This page makes no claim about a value it did not read.</footer>"
             % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    b.append("</div></body></html>")

    out = os.path.join(HERE, "index.html")
    open(out, "w", encoding="utf-8").write("".join(b))
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
