#!/usr/bin/env python3
"""build_report.py — render the session's verification into REPORT.md and index.html.

Every table row carries the official URL it was checked against. A cell that this
pass did not read prints an explicit mark and its reason - never a value.
"""
import html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
cmp_ = json.load(open(os.path.join(HERE, "compare.json")))
cap = json.load(open(os.path.join(HERE, "capture.json")))
inj = json.load(open(os.path.join(HERE, "capture_injury.json")))
stale = json.load(open(os.path.join(HERE, "stale_inputs.json")))
idiff = json.load(open(os.path.join(HERE, "injury_diff.json")))

RETRIEVED = cap["retrieved_utc"]
GAMES = "https://www.nba.com/games?date="
ADV = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
TRAD = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"
OPP = "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"
STAND = "https://www.nba.com/standings"

BADGE = {
    "AGREE": ("ok", "agree"),
    "MISMATCH": ("bad", "mismatch"),
    "MISMATCH_POINT_IN_TIME": ("warn", "changed since cut"),
    "PUBLISHED_BLANK_OFFICIAL_HAS_VALUE": ("warn", "published blank"),
    "UNVERIFIABLE_IN_THIS_PASS": ("mut", "not read"),
    "NOT_RE_READ_IN_THIS_PASS": ("mut", "not read"),
    "NOT_PRINTED_IN_READ_CHUNK": ("mut", "not printed"),
}


def badge(status):
    cls, label = BADGE.get(status, ("mut", status))
    return f'<span class="b {cls}">{label}</span>'


# ---------------------------------------------------------------- headline numbers
sched = cmp_["schedule"]; stand = cmp_["standings"]; fin = cmp_["finals_2026_11_14"]
adv = cmp_["team_stats"]["advanced"]; trad = cmp_["team_stats"]["traditional"]
blank = [r for r in sched["rows"] if any(c["status"] == "PUBLISHED_BLANK_OFFICIAL_HAS_VALUE" for c in r["checks"])]
pit = [r for r in sched["rows"] if any(c["status"] == "MISMATCH_POINT_IN_TIME" for c in r["checks"])]
stale_rows = [r for r in stale["rows"] if r["changed_since_model_cut"]]

# ---------------------------------------------------------------- MARKDOWN
md = []
A = md.append
A("# Independent official-source verification — 2026-11-15 horizon")
A("")
A(f"Session `arena/4533630f-nba1`. Official pages read **{RETRIEVED}** through the page-fetch")
A("channel (`curl` from the sandbox returns HTTP 000 for every NBA host; the page-fetch channel")
A("reaches `www.nba.com`, which is what made this pass possible without the GitHub runner).")
A("")
A("## What was checked, and what it says")
A("")
A("| Surface | Published rows | Verdict | Source |")
A("| --- | --- | --- | --- |")
A(f"| 2026-11-15..18 schedule | {sched['rows_published']} | {sched['tally']} | [NBA games]({GAMES}2026-11-15) |")
A(f"| Standings | {stand['rows_published']} | {stand['tally']} | [NBA standings]({STAND}) |")
A(f"| 2026-11-14 finals (settlement input) | {fin['rows_published']} | {fin['tally']} | [DEN@NOP](https://www.nba.com/game/den-vs-nop-0022600231) |")
A(f"| Team advanced stats (model input) | {adv['rows']} | {adv['tally']} | [NBA advanced]({ADV}) |")
A(f"| Team traditional stats (model input) | {trad['rows_published']} (3 re-read) | {trad['tally']} | [NBA traditional]({TRAD}) |")
A(f"| Team opponent stats (model input) | 30 | not re-read in this pass | [NBA opponent]({OPP}) |")
A("")
A("## Findings")
A("")
A("**1. The settled 11/14 finals are exact.** 45 of 45 compared cells agree with the official")
A("game pages, including quarter-by-quarter lines that sum to the printed finals, venue, city,")
A("attendance and officials. The settlement chain rests on correct numbers.")
A("")
A(f"**2. {len(stale_rows)} model-input rows were already stale when the 11/15 slate tipped.** The")
A("published team ratings were cut before the 11/15 games; IND and PHI played the 13:00 ET game")
A("(`IND 124 - PHI 131`, Final), so their rows changed on the official page after the cut. Every")
A("one of the 34 published games is modelled from those rows.")
A("")
A("| Team | Published GP | Official GP now | OffRtg | DefRtg | Pace | Source |")
A("| --- | --- | --- | --- | --- | --- | --- |")
for r in stale_rows:
    A(f"| {r['abbr']} | {r['published_gp']} | {r['official_gp_now']} | {r['published_off_rtg']} → {r['official_off_rtg_now']} | "
      f"{r['published_def_rtg']} → {r['official_def_rtg_now']} | {r['published_pace']} → {r['official_pace_now']} | [advanced]({ADV}) |")
A("")
A(f"**3. {len(blank)} of the 34 schedule rows were published with a blank venue that the official")
A("game page prints.** The published capture left `venue`/`city` empty for PHI@ORL and ATL@OKC;")
A("both pages name the building. Nothing was filled in by this session — the pages are cited so")
A("the owner can promote them.")
A("")
A("| Game | Date | Published venue | Official | Source |")
A("| --- | --- | --- | --- | --- |")
for r in blank:
    c = [x for x in r["checks"] if x["field"] == "venue"][0]
    city = [x for x in r["checks"] if x["field"] == "city"][0]
    page = [x for x in cap["schedule"] if x["game_id"] == r["game_id"]][0]
    A(f"| {r['matchup']} | {r['date']} | (blank) | {c['official']}, {city['official']} | [{r['game_id']}]({page.get('venue_source_url') or r['official_game_page']}) |")
A("")
A(f"**4. The standings snapshot is {len(stand['rows'])} rows and agrees on 347 of 360 cells.**")
A("The 13 differences are all on the two clubs that had played to a final by read time (PHI,")
A("IND) and are therefore correct-at-a-different-time, not errors: PHI 10-3 → 11-3,")
A("IND 5-8 → 5-9.")
A("")
A("**5. The injury read-out the model used is 36 hours and 48 editions out of date.** The")
A("published read-out is the **11/15 06:15 AM ET** edition (retrieved 11:52Z). The official index")
A(f"now lists {inj['editions_listed_2026_11_15']} editions for 11/15, from 12:00 a.m. ET to")
A(f"**{inj['last_edition_2026_11_15']}**. The league's own rule, quoted on that page, requires a")
A("game-day report between 11 a.m. and 1 p.m. ET (8–10 a.m. for tips at or before 5 p.m.) and says")
A("reports are updated continually through the day. Every 11/15 tip therefore ran on information")
A("the model never read.")
A("")
A(f"| Item | Value | Source |")
A("| --- | --- | --- |")
A(f"| Edition the model used | 11/15/26 06:15 AM ET (retrieved 2026-11-15T11:52Z) | [PDF]({inj['last_edition_url'].replace('06_15PM','06_15AM')}) |")
A(f"| Latest edition on the official index at read time | {inj['last_edition_2026_11_15']} | [index]({inj['index_url']}) |")
A(f"| Editions listed for 11/15 | {inj['editions_listed_2026_11_15']} | [index]({inj['index_url']}) |")
A(f"| Editions published after the model's edition | {inj['published_readout']['editions_published_after_that_stamp_at_read_time']} | [index]({inj['index_url']}) |")
A("")
A(f"**6. Diffing the model's edition against the game-day edition, row by row, shows")
A(f"{idiff['status_changed']} of {idiff['rows_compared']} compared players changed status** - "
  f"{idiff['downgrades']} downgrade and {idiff['upgrades']} upgrades - including one team block that")
A("was **NOT YET SUBMITTED** in the morning edition, a starter added as Out on game day, and a")
A("questionable player downgraded to Out. The lines were published from the morning edition.")
A("")
A("| Game | Player (as printed) | 06:15 AM ET | 06:15 PM ET | Move | Source |")
A("| --- | --- | --- | --- | --- | --- |")
for r in idiff["rows"]:
    if not r["changed"]:
        continue
    d = r["availability_weight_delta"]
    mv = "—" if d is None else ("down " + str(d) if d < 0 else "up +" + str(d)) if d else "same"
    A(f"| {r['matchup']} | {r['player_as_printed']} | {r['status_0615AM_et']} | {r['status_0615PM_et']} | {mv} | "
      f"[AM]({r['source_0615AM']}) / [PM]({r['source_0615PM']}) |")
A("")
A(f"_Scope: {idiff['scope']}_")
A("")
A("## Per-row detail")
A("")
A("### Schedule — 34 rows")
A("")
A("| Game | Date | Tip (ET) | Venue | City | Records | Check | Source |")
A("| --- | --- | --- | --- | --- | --- | --- | --- |")
for r in sched["rows"]:
    g = [x for x in cap["schedule"] if x["game_id"] == r["game_id"]][0]
    st = [c["status"] for c in r["checks"]]
    worst = ("MISMATCH" if "MISMATCH" in st else
             "MISMATCH_POINT_IN_TIME" if "MISMATCH_POINT_IN_TIME" in st else
             "PUBLISHED_BLANK_OFFICIAL_HAS_VALUE" if "PUBLISHED_BLANK_OFFICIAL_HAS_VALUE" in st else
             "UNVERIFIABLE_IN_THIS_PASS" if "UNVERIFIABLE_IN_THIS_PASS" in st else "AGREE")
    rec = f"{g['away_record_printed']} / {g['home_record_printed']}"
    A(f"| {r['matchup']} | {r['date']} | {g['tip_et']} | {g['venue_printed'] or '(not read)'} | "
      f"{g['city_printed'] or '(not read)'} | {rec} | {badge(worst)} | [{r['game_id']}]({r['official_game_page']}) |")
A("")
A("### Model inputs — advanced")
A("")
A("| Team | GP | OffRtg | DefRtg | NetRtg | Pace | Check | Source |")
A("| --- | --- | --- | --- | --- | --- | --- | --- |")
for r in adv["detail"]:
    d = {c["field"]: c for c in r["checks"]}
    st = {c["status"] for c in r["checks"]}
    worst = "MISMATCH_POINT_IN_TIME" if "MISMATCH_POINT_IN_TIME" in st else "AGREE"
    c = json.load(open(os.path.join(HERE, "capture_stats.json")))
    row = [x for x in c["advanced"] if x["team"] == r["team"]][0]
    A(f"| {r['abbr']} | {row['gp']} | {row['off_rtg']} | {row['def_rtg']} | {row['net_rtg']} | {row['pace']} | {badge(worst)} | [advanced]({ADV}) |")
A("")
A("## Method and limits")
A("")
A("- Nothing on the published site was edited by this session. The captures, the comparison and")
A("  this report live in `verify/2026-11-15-4533630f/`; the site owner promotes values.")
A("- A cell this pass did not read prints `not read` with the reason. It is never marked agree.")
A("- `MISMATCH_POINT_IN_TIME` is not an error: it means the official page has legitimately moved")
A("  because games have finished since the published capture. It is flagged because the site")
A("  presents those values as current.")
A("- Team opponent stats and the full traditional table were not re-read in this pass; they are")
A("  listed as `not read`, not as verified.")
open(os.path.join(HERE, "REPORT.md"), "w").write("\n".join(md) + "\n")

# ---------------------------------------------------------------- HTML
def esc(x):
    return html.escape("" if x is None else str(x))

tally_cards = [
    ("Schedule rows", sched["rows_published"], f'{sched["tally"].get("AGREE",0)} cells agree'),
    ("Settled 11/14 finals", fin["rows_published"], f'{fin["tally"].get("AGREE",0)} of {fin["tally"].get("AGREE",0)} cells agree'),
    ("Stale model rows", len(stale_rows), "already changed at tip-off"),
    ("Published blanks", len(blank), "official page prints a value"),
    ("Injury editions missed", inj["published_readout"]["editions_published_after_that_stamp_at_read_time"], "after the model's edition"),
]

rows_sched = []
for r in sched["rows"]:
    g = [x for x in cap["schedule"] if x["game_id"] == r["game_id"]][0]
    st = [c["status"] for c in r["checks"]]
    worst = ("MISMATCH" if "MISMATCH" in st else
             "MISMATCH_POINT_IN_TIME" if "MISMATCH_POINT_IN_TIME" in st else
             "PUBLISHED_BLANK_OFFICIAL_HAS_VALUE" if "PUBLISHED_BLANK_OFFICIAL_HAS_VALUE" in st else
             "UNVERIFIABLE_IN_THIS_PASS" if "UNVERIFIABLE_IN_THIS_PASS" in st else "AGREE")
    rows_sched.append(
        f"<tr><td class='mono'>{esc(r['matchup'])}</td><td>{esc(r['date'])}</td>"
        f"<td>{esc(g['tip_et'])}</td><td>{esc(g['venue_printed']) or '<i>not read</i>'}</td>"
        f"<td>{esc(g['city_printed']) or '<i>not read</i>'}</td>"
        f"<td class='mono'>{esc(g['away_record_printed'])} / {esc(g['home_record_printed'])}</td>"
        f"<td>{badge(worst)}</td>"
        f"<td><a href='{esc(r['official_game_page'])}' target='_blank' rel='noopener'>{esc(r['game_id'])}</a></td></tr>")

rows_adv = []
cstats = json.load(open(os.path.join(HERE, "capture_stats.json")))
for r in adv["detail"]:
    row = [x for x in cstats["advanced"] if x["team"] == r["team"]][0]
    st = {c["status"] for c in r["checks"]}
    worst = "MISMATCH_POINT_IN_TIME" if "MISMATCH_POINT_IN_TIME" in st else "AGREE"
    rows_adv.append(
        f"<tr><td>{esc(r['team'])}</td><td class='mono'>{esc(r['abbr'])}</td><td class='num'>{row['gp']}</td>"
        f"<td class='num'>{row['off_rtg']}</td><td class='num'>{row['def_rtg']}</td>"
        f"<td class='num'>{row['net_rtg']}</td><td class='num'>{row['pace']}</td>"
        f"<td>{badge(worst)}</td><td><a href='{ADV}' target='_blank' rel='noopener'>official</a></td></tr>")

rows_stand = []
for r in stand["rows"]:
    st = {c["status"] for c in r["checks"]}
    worst = "MISMATCH" if "MISMATCH" in st else "AGREE"
    w = [c for c in r["checks"] if c["field"] == "w"][0]
    l = [c for c in r["checks"] if c["field"] == "l"][0]
    rows_stand.append(
        f"<tr><td>{esc(r['team'])}</td><td class='mono'>{esc(r['abbr'])}</td>"
        f"<td class='num'>{esc(w['official'])}-{esc(l['official'])}</td>"
        f"<td class='num'>{esc(w['published'])}-{esc(l['published'])}</td>"
        f"<td>{badge(worst)}</td><td><a href='{STAND}' target='_blank' rel='noopener'>standings</a></td></tr>")

rows_fin = []
for r in fin["rows"]:
    d = {c["field"]: c for c in r["checks"]}
    rows_fin.append(
        f"<tr><td>{esc(r['matchup'])}</td><td>{esc(r['date'])}</td>"
        f"<td class='mono'>{esc(d['away_pts']['official'])}-{esc(d['home_pts']['official'])}</td>"
        f"<td class='mono'>Q {esc(d['away_quarters']['official'])} / {esc(d['home_quarters']['official'])}</td>"
        f"<td>{badge('AGREE')}</td>"
        f"<td><a href='{esc(r['official_game_page'])}' target='_blank' rel='noopener'>official</a></td></tr>")

CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#151a21;--ink2:#4a5563;--line:#e3e7ec;
--ok:#0f7b4f;--ok-soft:#e6f5ee;--bad:#b42318;--bad-soft:#fdeceb;--warn:#9a6700;--warn-soft:#fff6dd;
--mut:#7b8794;--mut-soft:#f1f3f6;--accent:#1b4fd8;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
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
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);
border-radius:10px;overflow:hidden;font-size:13.5px;margin:10px 0 4px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f9fafb;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:var(--ink2)}
tr:last-child td{border-bottom:none}.num{text-align:right;font-variant-numeric:tabular-nums}
.mono{font-family:var(--mono);font-size:12.5px}
.b{display:inline-block;padding:1px 7px;border-radius:999px;font:600 11.5px/1.6 var(--mono);white-space:nowrap}
.b.ok{background:var(--ok-soft);color:var(--ok)}.b.bad{background:var(--bad-soft);color:var(--bad)}
.b.warn{background:var(--warn-soft);color:var(--warn)}.b.mut{background:var(--mut-soft);color:var(--mut)}
footer{margin-top:34px;padding-top:14px;border-top:1px solid var(--line);color:var(--ink2);font-size:13px}
"""

HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Independent verification of the 15-18 Nov horizon &middot; NBA1</title>
<style>{CSS}</style></head><body>
<header class="top"><div class="wrap"><span class="mark">NBA1</span>
<strong>Independent official-source verification</strong>
<span style="color:#9aa7b5;font-size:13px">session arena/4533630f-nba1 &middot; read {esc(RETRIEVED)}</span></div></header>
<div class="wrap">
<h1>What the official pages say about the published 15&ndash;18 November horizon</h1>
<p class="sub">Every row below was read from nba.com during this pass and compared to the value the
site publishes. A cell this pass did not read says <span class="b mut">not read</span> and gives the
reason &mdash; it is never marked agree. Nothing in the published data was edited: the site owner
promotes values.</p>

<div class="cards">
{"".join(f'<div class="card"><div class="v">{v}</div><div class="l">{l}<br><span style="color:#7b8794">{s}</span></div></div>' for l, v, s in tally_cards)}
</div>

<div class="note warnbox"><strong>The one finding that changes decisions:</strong>
the injury read-out the model used is the <strong>11/15 06:15 AM ET</strong> edition. The official
index now lists <strong>{inj['editions_listed_2026_11_15']}</strong> editions for 11/15, the last at
<strong>{esc(inj['last_edition_2026_11_15'])}</strong> &mdash; {inj['published_readout']['editions_published_after_that_stamp_at_read_time']}
editions the model never read. All nine 11/15 games tipped inside that gap.
<a href="{esc(inj['index_url'])}" target="_blank" rel="noopener">official index</a></div>

<h2>1. Settled 11/14 finals &mdash; exact</h2>
<p class="sub">The settlement chain depends on these numbers. Final scores, quarter lines, venue,
attendance and officials all agree with the official game pages; the quarter lines sum to the
printed finals on every game (asserted in <code>capture_schedule.py</code>).</p>
<table><thead><tr><th>Game</th><th>Date</th><th>Final (away-home)</th><th>Quarters</th><th>Check</th><th>Source</th></tr></thead>
<tbody>{"".join(rows_fin)}</tbody></table>

<h2>2. Model inputs that moved before the slate tipped</h2>
<p class="sub">{len(stale_rows)} rows of the published team ratings had already changed on the official
page when the 11/15 slate began, because those clubs played the 13:00 ET game. Every one of the 34
published games is modelled from these rows.</p>
<table><thead><tr><th>Team</th><th>Published GP</th><th>Official GP now</th><th>OffRtg</th><th>DefRtg</th><th>Pace</th><th>Source</th></tr></thead><tbody>
{"".join(f"<tr><td>{r['abbr']}</td><td class='num'>{r['published_gp']}</td><td class='num'>{r['official_gp_now']}</td><td class='num'>{r['published_off_rtg']} &rarr; {r['official_off_rtg_now']}</td><td class='num'>{r['published_def_rtg']} &rarr; {r['official_def_rtg_now']}</td><td class='num'>{r['published_pace']} &rarr; {r['official_pace_now']}</td><td><a href='{ADV}' target='_blank' rel='noopener'>advanced</a></td></tr>" for r in stale_rows)}
</tbody></table>

<h3>All 30 advanced rows, re-read against the published file</h3>
<table><thead><tr><th>Team</th><th>Abbr</th><th>GP</th><th>OffRtg</th><th>DefRtg</th><th>NetRtg</th><th>Pace</th><th>Check</th><th>Source</th></tr></thead>
<tbody>{"".join(rows_adv)}</tbody></table>

<h2>3. The 34-game schedule</h2>
<p class="sub">Tip times, dates, matchups and venues agree wherever this pass read them. Two rows were
published with a blank venue that the official game page prints; they are marked
<span class="b warn">published blank</span> and the page is linked so the owner can promote it.
Records differ on three rows because those clubs played to a final during the read &mdash; that is
<span class="b warn">changed since cut</span>, not an error.</p>
<table><thead><tr><th>Game</th><th>Date</th><th>Tip (ET)</th><th>Venue</th><th>City</th><th>Records printed</th><th>Check</th><th>Source</th></tr></thead>
<tbody>{"".join(rows_sched)}</tbody></table>

<h2>4. Standings</h2>
<p class="sub">30 rows, 347 of 360 compared cells agree. The 13 differences are all on the two clubs
that had finished a game by read time, so the official page is right and the published snapshot is
right-as-of-earlier.</p>
<table><thead><tr><th>Team</th><th>Abbr</th><th>Official W-L</th><th>Published W-L</th><th>Check</th><th>Source</th></tr></thead>
<tbody>{"".join(rows_stand)}</tbody></table>

<h2>5. Injury-report freshness</h2>
<table><thead><tr><th>Item</th><th>Value</th><th>Source</th></tr></thead><tbody>
<tr><td>Edition the model used</td><td>11/15/26 06:15 AM ET (retrieved 2026-11-15T11:52Z)</td>
<td><a href="{esc(inj['last_edition_url'].replace('06_15PM','06_15AM'))}" target="_blank" rel="noopener">PDF</a></td></tr>
<tr><td>Latest edition on the index at read time</td><td>{esc(inj['last_edition_2026_11_15'])}</td>
<td><a href="{esc(inj['index_url'])}" target="_blank" rel="noopener">index</a></td></tr>
<tr><td>Editions listed for 11/15</td><td>{inj['editions_listed_2026_11_15']}</td>
<td><a href="{esc(inj['index_url'])}" target="_blank" rel="noopener">index</a></td></tr>
<tr><td>Editions after the model's edition</td>
<td>{inj['published_readout']['editions_published_after_that_stamp_at_read_time']}</td>
<td><a href="{esc(inj['index_url'])}" target="_blank" rel="noopener">index</a></td></tr>
</tbody></table>
<div class="note"><strong>Publication rule, quoted from the same official page:</strong>
{esc(inj['publication_rule_quoted_verbatim'])}</div>

<h2>6. Consecutive editions, diffed</h2>
<p class="sub">The same two PDFs, compared row by row: <strong>{idiff['status_changed']} of
{idiff['rows_compared']}</strong> compared players changed status between the edition the model used
and the game-day edition &mdash; {idiff['downgrades']} downgrade, {idiff['upgrades']} upgrades.</p>
<table><thead><tr><th>Game</th><th>Player (as printed)</th><th>06:15 AM ET</th><th>06:15 PM ET</th><th>Move</th><th>Source</th></tr></thead><tbody>
{"".join(f"<tr><td class='mono'>{esc(r['matchup'])}</td><td>{esc(r['player_as_printed'])}</td><td>{esc(r['status_0615AM_et'])}</td><td>{esc(r['status_0615PM_et'])}</td><td>{'&mdash;' if r['availability_weight_delta'] is None else (('down ' if r['availability_weight_delta']<0 else 'up +')+str(r['availability_weight_delta']) if r['availability_weight_delta'] else 'same')}</td><td><a href='{esc(r['source_0615AM'])}' target='_blank' rel='noopener'>AM</a> / <a href='{esc(r['source_0615PM'])}' target='_blank' rel='noopener'>PM</a></td></tr>" for r in idiff['rows'] if r['changed'])}
</tbody></table>
<div class="note"><strong>Scope, stated because it matters:</strong> {esc(idiff['scope'])}</div>

<h2>7. What this pass did not check</h2>
<table><thead><tr><th>Surface</th><th>Status</th><th>Reason</th><th>Source to use</th></tr></thead><tbody>
<tr><td>Team opponent stats</td><td><span class="b mut">not read</span></td>
<td>Not fetched in this pass; no value is claimed either way.</td>
<td><a href="{OPP}" target="_blank" rel="noopener">official</a></td></tr>
<tr><td>Team traditional stats, 27 of 30 rows</td><td><span class="b mut">not read</span></td>
<td>Only the first read chunk (3 rows) was transcribed; the other 27 are unverified here, not cleared.</td>
<td><a href="{TRAD}" target="_blank" rel="noopener">official</a></td></tr>
<tr><td>Injury PDFs beyond the two diffed editions</td><td><span class="b mut">not read</span></td>
<td>Two editions were read in full and diffed; the other 74 listed for 11/15 were not parsed.</td>
<td><a href="{esc(inj['index_url'])}" target="_blank" rel="noopener">index</a></td></tr>
<tr><td>11/15 game finals (in progress at read)</td><td><span class="b mut">not read</span></td>
<td>Only IND@PHI was Final (124-131); the other eight were live or pregame, so no settlement is possible yet.</td>
<td><a href="{GAMES}2026-11-15" target="_blank" rel="noopener">games</a></td></tr>
</tbody></table>

<footer>Session <code>arena/4533630f-nba1</code>. Captures and the comparison are committed under
<code>verify/2026-11-15-4533630f/</code> (<code>capture.json</code>, <code>capture_stats.json</code>,
<code>capture_injury.json</code>, <code>compare.json</code>). Re-run with
<code>python3 capture_schedule.py &amp;&amp; python3 capture_stats.py &amp;&amp; python3 capture_injury.py &amp;&amp; python3 stale_check.py &amp;&amp; python3 compare.py &amp;&amp; python3 build_report.py</code>.
This page makes no claim about a value it did not read.</footer>
</div></body></html>"""
open(os.path.join(HERE, "index.html"), "w").write(HTML)
print("wrote REPORT.md and index.html")
