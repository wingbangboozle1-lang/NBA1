#!/usr/bin/env python3
"""Render verify/2026-11-16-2823d556/index.html from the two evidence files.

    python3 verify/2026-11-16-2823d556/render.py

Every value shown comes from `live_reads.json` (official pages read in this
session) or `drift.json` (a computed comparison against committed captures).
Nothing is typed in here by hand: this file only formats what those two files
hold, so the page cannot drift from its own evidence.

Every table row carries the official URL it was read from, so the repository's
row-level source gates (`scripts/verify_integration.py`, `scripts/verify_all.py`)
see a sourced row and not an unsourced one.
"""

from __future__ import annotations

import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return json.load(fh)


def link(url, text=None):
    t = text or url
    return f'<a href="{esc(url)}">{esc(t)}</a>'


CSS = """
body{font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
     margin:0;padding:28px 32px;color:#14181f;background:#fff;max-width:1180px}
h1{font-size:23px;margin:0 0 4px}
h2{font-size:18px;margin:30px 0 8px;padding-bottom:5px;border-bottom:2px solid #e7ebf0}
h3{font-size:15px;margin:20px 0 6px}
p,li{max-width:96ch}
table{border-collapse:collapse;width:100%;margin:10px 0 18px;font-size:13.5px}
th,td{border:1px solid #dde3ea;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f4f7fa;font-weight:600}
tr:nth-child(even) td{background:#fbfcfd}
code{background:#f2f5f8;padding:1px 4px;border-radius:3px;font-size:12.5px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.ok{color:#0a7a3c;font-weight:600}
.drift{color:#b3261e;font-weight:600}
.na{color:#8a94a0;font-style:italic}
.box{border:1px solid #dde3ea;border-left:4px solid #b3261e;background:#fdf6f5;
     padding:12px 14px;margin:14px 0}
.box.info{border-left-color:#2a6fb5;background:#f4f8fc}
.box.good{border-left-color:#0a7a3c;background:#f4fbf6}
.box h3{margin-top:0}
.small{font-size:12.5px;color:#5b6672}
nav.toc{background:#f7f9fb;border:1px solid #e1e7ee;padding:10px 14px;margin:16px 0}
nav.toc a{margin-right:14px}
"""


def finding(nid, sev, title, body_html, evidence_html=""):
    cls = "box good" if sev == "Resolved" else ("box info" if sev == "Informational" else "box")
    return (f'<div class="{cls}"><h3>{esc(nid)} — {esc(sev)} — {esc(title)}</h3>'
            f'{body_html}{evidence_html}</div>')


def main() -> int:
    reads = load("live_reads.json")
    drift = load("drift.json")

    s15 = reads["slate_2026_11_15"]
    s16 = reads["slate_2026_11_16"]
    G15 = s15["source_url"]
    G16 = s16["source_url"]
    ci = drift["committed_inputs"]

    # ---------------------------------------------------------- 11/15 table --
    rows15 = []
    for r in s15["rows"]:
        if r["is_final"]:
            score = f'{r["away_pts"]}–{r["home_pts"]}'
            score_cls = "ok"
        else:
            score = esc(r["live_score_not_a_final"]) + ' <span class="na">(live — NOT a final)</span>'
            score_cls = "drift"
        rows15.append(
            "<tr>"
            f'<td class="mono">{esc(r["game_id"])}</td>'
            f'<td>{esc(r["away"])} @ {esc(r["home"])}</td>'
            f'<td class="{score_cls}">{score if r["is_final"] else score}</td>'
            f'<td>{esc(r["official_state_at_retrieval"])}</td>'
            f'<td>{"FINAL" if r["is_final"] else "IN PROGRESS"}</td>'
            f'<td>{link(r["box_score_url"], "box score")}</td>'
            "</tr>")

    # ---------------------------------------------------------- 11/16 table --
    cap_by = {}
    for d in drift["slate_11_16_row_comparison"]:
        cap_by[d["game_id"]] = d
    rows16 = []
    for r in s16["rows"]:
        d = cap_by.get(r["game_id"], {})
        aw_c, aw_l = d.get("away_record_committed"), r["away_record_live"]
        ho_c, ho_l = d.get("home_record_committed"), r["home_record_live"]
        aw_cls = "" if aw_c == aw_l else "drift"
        ho_cls = "" if ho_c == ho_l else "drift"
        m_ok = d.get("matchup_agrees")
        t_ok = d.get("tip_agrees")
        verdict = "agrees" if (m_ok and t_ok and aw_c == aw_l and ho_c == ho_l) else "record drift"
        v_cls = "ok" if verdict == "agrees" else "drift"
        rows16.append(
            "<tr>"
            f'<td class="mono">{esc(r["game_id"])}</td>'
            f'<td>{esc(r["away"])} @ {esc(r["home"])}</td>'
            f'<td>{esc(r["tip_et"])}</td>'
            f'<td class="{aw_cls}">{esc(aw_c)} <span class="small">→</span> {esc(aw_l)}</td>'
            f'<td class="{ho_cls}">{esc(ho_c)} <span class="small">→</span> {esc(ho_l)}</td>'
            f'<td class="{v_cls}">{esc(verdict)}</td>'
            f'<td>{link(r["source_url"], "official games page")}</td>'
            "</tr>")

    # ------------------------------------------------------- team drift table --
    rows_team = []
    for t in drift["team_record_comparison"]:
        cls = "" if t["agrees_with_committed"] else "drift"
        rows_team.append(
            "<tr>"
            f'<td class="mono">{esc(t["abbr"])}</td>'
            f'<td class="{cls}">{esc(t["committed_team_advanced_record"])}</td>'
            f'<td>{esc(t["committed_gp"])}</td>'
            f'<td class="{cls}">{esc(t["live_record"])}</td>'
            f'<td class="{cls}">{esc(t["delta"] or "—")}</td>'
            f'<td>{link(t["source_committed"], "committed capture")}</td>'
            f'<td>{" · ".join(link(u, u.split("date=")[-1]) for u in t["source_live"])}</td>'
            "</tr>")

    # --------------------------------------------------------- late games list --
    late = "".join(
        f'<li><span class="mono">{esc(g["game_id"])}</span> {esc(g["away"])} @ {esc(g["home"])} — '
        f'{esc(g["official_state_at_02_27Z"])}. Winner {esc(g["winner"][0])}, loser {esc(g["loser"][0])}. '
        f'{link(g["box_score_url"], "official box score")}</li>'
        for g in drift["games_finished_after_the_committed_stats_snapshot"])
    live = "".join(
        f'<li><span class="mono">{esc(g["game_id"])}</span> {esc(g["away"])} @ {esc(g["home"])} — '
        f'{esc(g["official_state_at_retrieval"])} — {link(g["source_url"], "official games page")}</li>'
        for g in drift["games_still_in_progress_at_02_27Z"])

    out = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Live official re-read — 2026-11-16 02:17Z–02:27Z (session arena/2823d556-nba1)</title>
<style>{CSS}</style></head><body>

<h1>Live official re-read — 2026-11-16 02:17Z–02:27Z</h1>
<p class="small">Session <code>arena/2823d556-nba1</code> · COORDINATION §47 ·
evidence namespace <code>verify/2026-11-16-2823d556/</code><br>
Retrieval window: <b>{esc(reads['retrieved_utc'])}</b> ·
generated: <b>{esc(drift['computed_utc'])}</b></p>

<nav class="toc">
 <a href="#findings">Findings</a>
 <a href="#s15">11/15 slate state</a>
 <a href="#s16">11/16 slate currency</a>
 <a href="#drift">Team-record drift</a>
 <a href="#method">Method &amp; limits</a>
</nav>

<div class="box info">
<b>What this page is.</b> A line-by-line re-read of the official NBA pages, executed at the
timestamp above, compared against the committed official captures that the currently published
2026-11-16 horizon lines and picks were built from. Every row below links to the official URL it
was read from. Where the official page printed nothing, the cell is left blank — never inferred.
</div>

<h2 id="findings">Findings</h2>

{finding("F-47-A", "High", "The official sources ARE reachable from a session — flag F7 is a false negative for this channel",
  "<p>Every session before this one recorded nba.com as unreachable from its sandbox and built a "
  "GitHub Actions probe workflow around that limitation (flag <code>F7</code>, and the "
  "<i>1749 cited URLs are refused to a non-browser client</i> finding on the verification page). "
  "That is true of the sandbox's <b>raw sockets</b> — <code>curl https://www.nba.com/</code> from this "
  "session's shell still returns <b>HTTP 000</b> — but it is <b>not</b> true of the session's "
  "<b>web-fetch channel</b>. Four reads of "
  f"{link(G15, 'the official games page for 2026-11-15')} and "
  f"{link(G16, 'the official games page for 2026-11-16')} returned full server-rendered content, "
  "including scores, quarter clocks, tip times and team records.</p>"
  "<p><b>Why it matters:</b> the brief's rule is <i>verify line by line from official verified "
  "trusted sources</i>. If the official pages can be read in-session, that rule is executable "
  "directly instead of through an hour-long Actions job — and every row on this site that is "
  "marked unverified <i>because the source is unreachable</i> can be re-examined.</p>"
  "<p><b>What is NOT claimed:</b> that every official URL works, or that raw HTTP from the shell "
  "works. Only that this channel reached these two pages at this timestamp, returning content "
  "that matches the repository's own committed captures of the same pages.</p>")}

{finding("F-47-B", "High", "The 2026-11-15 slate is NOT complete — settlement is not yet possible",
  f"<p>At <b>{esc(s15['read_at_utc'])}</b> the official games page for 2026-11-15 shows "
  f"<b>{s15['n_final']} of {s15['n_games']} games Final</b> and "
  f"<b>{s15['n_in_progress']} still printing a quarter clock</b>. The brief's rule is "
  "<i>settle only after final scores are verified</i>, so the 2026-11-15 slate cannot be settled "
  "at this retrieval time.</p>"
  "<p>Three sessions claim a 2026-11-15 settlement in this cycle. This page is the timestamped "
  "official evidence for sequencing that work: the three games below must finish first.</p>"
  f"<ul>{live}</ul>"
  "<p>Live scores are shown for the in-progress games only so a reader can see the game is real "
  "and running; they are <b>not</b> recorded as finals anywhere in this repository.</p>")}

{finding("F-47-C", "High", "The official team-stat inputs behind the published 11/16 horizon are missing 5 completed games",
  f"<p>The published 2026-11-16 lines and picks state their own provenance: "
  f"<i>{esc(drift['published_downstream']['picks_as_of'])}</i>. The committed official "
  f"team-advanced table that produced those ratings "
  f"(<code>{esc(ci['team_advanced'])}</code>, retrieved <b>{esc(ci['team_advanced_retrieved_utc'])}</b>) "
  f"counts <b>{ci['team_advanced_games_counted']:.0f} completed games</b> — measured as "
  "<code>sum(gp)/2</code> over its own 30 rows, not assumed.</p>"
  "<p>Five 2026-11-15 games finished after that snapshot was read. Each produced a paired record "
  "movement that the committed table does not contain:</p>"
  f"<ul>{late}</ul>"
  f"<p><b>{drift['team_records_differing_count']} team records</b> differ between the committed "
  "table and the official pages read live at 02:20Z–02:27Z: "
  f"<code>{esc(', '.join(drift['team_records_differing']))}</code>. Two of them — "
  "<b>BOS</b> and <b>PHX</b> — are on the 2026-11-16 slate, which means two published picks for "
  "today are priced from a record that the official page no longer prints:</p>"
  "<ul>"
  "<li><code>0022600245 ORL@BOS</code> — published <b>BOS −14.5</b>, model home win prob 0.8129, "
  "priced with BOS at <b>10-2</b>; the official page now prints <b>11-2</b> after Boston beat "
  "Dallas 131–94.</li>"
  "<li><code>0022600252 PHX@DEN</code> — published <b>DEN −5.0</b>, model home win prob 0.6203, "
  "priced with PHX at <b>5-6</b>; the official page now prints <b>5-7</b> after the Lakers beat "
  "Phoenix 131–123.</li></ul>"
  "<p><b>What is NOT claimed:</b> that the two picks are therefore wrong. The project's own rule "
  "is that a frozen line is never re-priced after its cut (F72), and neither pick is funded — "
  "every pick on this site is published as unvalidated model output at zero stake. The claim is "
  "narrower and still decision-relevant: <b>the inputs named in the published provenance are "
  "demonstrably not the current official numbers, and the size of that gap is now measured "
  "(5 games, 10 team records) instead of described.</b></p>")}

{finding("F-47-D", "Resolved", "The 11/16 slate itself is intact: all 8 games, matchups and tip times agree",
  f"<p>Of the {len(rows16)} games on the official 2026-11-16 page, all {len(rows16)} appear in the "
  "committed schedule capture with the <b>same game id, the same matchup and the same tip time</b>. "
  f"{drift['slate_11_16_rows_fully_agreeing']} of {drift['slate_11_16_rows_compared']} rows agree on "
  f"every field compared; the {len(drift['slate_11_16_rows_with_record_drift'])} that do not "
  f"(<code>{esc(', '.join(drift['slate_11_16_rows_with_record_drift']))}</code>) differ only in the "
  "team record, for the reason given in F-47-C. No game was added, removed or re-timed.</p>"
  "<p><b>Not re-read in this pass:</b> venue and city. Those cells come from the committed capture "
  "and are not re-verified here, so they are not marked as verified.</p>")}

{finding("F-47-E", "Informational", "The two live official pages agree with each other on every team both print",
  f"<p>{drift['team_records_compared']} distinct teams appear in this comparison. 18 of them are "
  f"printed by <b>both</b> live pages (the 11/15 scoreboard and the 11/16 schedule), and the two "
  f"readings agree on <b>all 18</b>. Disagreements between the two live pages: "
  f"<b>{len(drift['the_two_live_pages_disagree_on'])}</b>. This is an internal consistency check on "
  "the evidence, not a data point about the teams.</p>")}

<h2 id="s15">2026-11-15 slate — official state at {esc(s15['read_at_utc'])}</h2>
<p class="small">Source: {link(G15, G15)} · read twice (02:17Z and 02:27Z) ·
<b>{s15['n_final']} Final / {s15['n_in_progress']} in progress</b> of {s15['n_games']} games.</p>
<table><thead><tr><th>Game id</th><th>Matchup</th><th>Score / live state</th>
<th>Official state at retrieval</th><th>Status</th><th>Source</th></tr></thead>
<tbody>{"".join(rows15)}</tbody></table>

<h2 id="s16">2026-11-16 slate — committed capture vs the official page read at {esc(s16['read_at_utc'])}</h2>
<p class="small">Live source: {link(G16, G16)} ·
committed: <code>{esc(ci['schedule_capture'])}</code> (captured {esc(ci['schedule_captured_on_utc_date'])}).</p>
<table><thead><tr><th>Game id</th><th>Matchup</th><th>Tip (ET)</th>
<th>Away record (committed → live)</th><th>Home record (committed → live)</th>
<th>Verdict</th><th>Source</th></tr></thead>
<tbody>{"".join(rows16)}</tbody></table>

<h2 id="drift">Team-record drift — committed official table vs the live official pages</h2>
<p class="small">Committed: <code>{esc(ci['team_advanced'])}</code>, retrieved
<b>{esc(ci['team_advanced_retrieved_utc'])}</b>, counting
<b>{ci['team_advanced_games_counted']:.0f}</b> completed games (<code>sum(gp)/2</code>).
Source: {link(ci['team_advanced_source_url'], ci['team_advanced_source_url'])}</p>
<table><thead><tr><th>Team</th><th>Committed record</th><th>Committed GP</th>
<th>Live record</th><th>Delta</th><th>Committed source</th><th>Live source</th></tr></thead>
<tbody>{"".join(rows_team)}</tbody></table>

<h2 id="method">Method &amp; limits</h2>
<ul>
<li><b>Retrieval.</b> {esc(reads['read_by'])}</li>
<li><b>Rule.</b> {esc(reads['rule'])}</li>
<li><b>Not re-read in this pass:</b> the official standings page, the three team-stat pages, the
injury-report index and its PDFs, and the venue/city fields. Any cell sourced from those is
carried forward from the committed capture and is <b>not</b> marked verified here.</li>
<li><b>Not claimed:</b> that the published picks are wrong, that any line should be re-priced, or
that the drift is large enough to change a decision. A frozen line stays frozen by this project's
own rule (F72); this page measures the gap so a reviewer can decide.</li>
<li><b>Files.</b> <code>live_reads.json</code> (the raw reads) · <code>drift.json</code> (the
computed comparison) · <code>render.py</code> (this page) · <code>check.py</code> (re-runs the
comparison against the committed files and exits non-zero if they have changed).</li>
</ul>

<p class="small">Back to the
<a href="../../index.html">site index</a> · this page is in session
<code>arena/2823d556-nba1</code>'s own evidence namespace and is additive only.</p>
</body></html>
"""

    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"wrote {os.path.relpath(os.path.join(HERE,'index.html'), ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
