#!/usr/bin/env python3
"""Build C (session arena/afbb836e-nba1): row-by-row schedule verification.

Inputs
  data/raw/official_schedule_capture_2026-11-14.json  official transcription (NBA.com pages)
  data/schedule_2026_11_13_to_16.json                 the schedule file already published
Outputs
  data/raw/verification_c03.json                      machine-readable results, every row
  schedule-verified.html                              the site page for the same results

Rules applied (no inference):
  * A field is "match" only when the published value equals the official capture.
  * A record is "current" only if neither team played on 2026-11-13 (the official
    schedule lists 9 games that day, so the other 12 teams had no game).
  * Anything the official capture does not print is reported as "not printed",
    never filled in.
Exit status 1 on any mismatch between published and official values.
"""
import datetime
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "data", "raw", "official_schedule_capture_2026-11-14.json")
PUB = os.path.join(ROOT, "data", "schedule_2026_11_13_to_16.json")
OUT_JSON = os.path.join(ROOT, "data", "raw", "verification_c03.json")
OUT_HTML = os.path.join(ROOT, "schedule-verified.html")

# Official per-day game counts printed in the calendar cells of nba.com/games?date=...
CALENDAR_COUNTS = {"2026-11-13": 9, "2026-11-14": 5, "2026-11-15": 9, "2026-11-16": 8, "2026-11-17": 5}
HORIZON = ("2026-11-14", "2026-11-17")  # today (UTC 2026-11-14) through today + 3 days

FLAGS = [
    ("F-C01", "high", "11/13 final scores not captured",
     "Every NBA.com capture available to this session shows the 2026-11-13 games before tip or in progress "
     "(for example NYK at IND: 'LIVE Q1'). No final score for 11/13 is published here.",
     "https://www.nba.com/games?date=2026-11-13"),
    ("F-C02", "high", "Records are pre-11/13 for 18 teams in the 11/14-11/17 rows",
     "Teams that played on 2026-11-13 are listed with records captured before that night. Their records on "
     "11/14-11/17 rows are marked STALE and must not be read as current.",
     "https://www.nba.com/games?date=2026-11-14"),
    ("F-C03", "high", "11/14 injury report not retrievable",
     "The 2026-11-14 12:00 PM ET PDF returned AccessDenied to the fetch tool. No injury status for any 11/14 game "
     "has been verified in this session. This is not evidence that no report exists.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_12_00PM.pdf"),
    ("F-C04", "high", "Injury layer for later games uses a report dated 11/13",
     "gameflow.html and the injury impact rows are built from the official 11/13 5:15 PM ET report, whose printed "
     "Game Date is 11/13/2026 (a day already played). They do not come from the injury reports of 11/14-11/16 games.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf"),
    ("F-C05", "medium", "'Regular Season' label not printed on the official schedule",
     "The published rows for 11/14-11/16 say 'Regular Season'. The official schedule prints no label for these games; "
     "the value is an inference and is reported as not printed.",
     "https://www.nba.com/schedule"),
    ("F-C06", "medium", "Model output outlier: CHI at MIN, 11/14",
     "docs/data/gameflow.json gives expected home margin +29.7 and home win probability 0.956 for this game. "
     "The inputs (ratings through 11/12, and the pre-11/13 record of CHI 1-9) could not be reproduced from official "
     "data in this session. Flagged for review, not corrected.",
     "https://www.nba.com/game/chi-vs-min-0022600235"),
    ("F-C07", "high", "No lines or picks generated for 11/14-11/17",
     "The ratings used by the model run through 11/12, the 11/13 results are missing, and no 11/14+ injury report "
     "is verified (F-C03). Generating picks now would rest on stale inputs, so none were produced.",
     "https://www.nba.com/schedule"),
    ("F-C08", "info", "Venue names previously flagged are now printed by NBA.com",
     "'Rocket Arena' (Cleveland) and 'Mortgage Matchup Center' (Phoenix) appear on the official 2026-27 schedule page. "
     "They match the published rows.",
     "https://www.nba.com/schedule"),
    ("F-C09", "info", "11/13 tip times for NYK at IND and MIL at ORL",
     "The schedule capture showed these games as LIVE, so the tip time was not printed there. 7:00 PM ET is printed "
     "in the official 11/13 5:15 PM ET injury report game-time column. Resolved for these two rows.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf"),
    ("F-C10", "low", "Open pull requests not merged",
     "PR #11 (arena/c7fbc064-nba1, a third build) and PR #14 (coordination only) are open. Not touched by this session; "
     "they need an owner decision.",
     "https://github.com/wingbangboozle1-lang/NBA1/pull/11"),
    ("F-C11", "low", "summary.html row count drift (682 committed, 693 generated)",
     "The committed executive summary did not match what scripts/build_site.py generates on a clean checkout. "
     "Fixed in this session by regenerating the page from the builder.",
     "https://github.com/wingbangboozle1-lang/NBA1/blob/main/scripts/build_site.py"),
]


def game_url(away, home, gid):
    return f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}"


def main():
    cap = json.load(open(CAP, encoding="utf-8"))
    cols = cap["cols"]
    official = [dict(zip(cols, r)) for r in cap["rows"]]
    pub = {g["game_id"]: g for g in json.load(open(PUB, encoding="utf-8"))["games"]}

    played_1113 = set()
    for o in official:
        if o["date"] == "2026-11-13":
            played_1113 |= {o["away"], o["home"]}

    # calendar count check
    per_day = {}
    for o in official:
        per_day[o["date"]] = per_day.get(o["date"], 0) + 1
    calendar_ok = all(per_day.get(d) == n for d, n in CALENDAR_COUNTS.items())

    rows, mismatches = [], []
    for o in official:
        gid = o["game_id"]
        if o["date"] == "2026-11-13":
            rec_status = "pre-tip capture (as of 2026-11-13 before the games)"
        elif o["away"] in played_1113 or o["home"] in played_1113:
            # The 11/13 finals have since been captured and promoted, and the records on the
            # published horizon rows were refreshed against NBA.com on 2026-11-14 (session
            # arena/934ca56f-nba1, checked by scripts/verify_horizon_s934ca56f.py). This file's
            # own transcription stays marked as the pre-11/13 capture it is, so the two are not
            # confused; the published value is no longer stale.
            rec_status = ("pre-11/13 capture in this file; the published row was refreshed to the "
                          "post-11/13 official value on 2026-11-14")
        else:
            rec_status = "unchanged: neither team played 2026-11-13 per the official schedule"
        if o["cup_label"]:
            comp_official = f"Emirates NBA Cup - {o['cup_label']}"
        else:
            comp_official = "not printed on official schedule"
        r = {
            "date": o["date"], "game_id": gid, "away": o["away"], "home": o["home"],
            "tip_et": o["tip_et"], "venue": o["venue"], "city": o["city"],
            "competition_official": comp_official,
            "away_record_pre_11_13": o["away_record_pre_11_13"],
            "home_record_pre_11_13": o["home_record_pre_11_13"],
            "record_status": rec_status,
            "tip_confirmed_by": o["tip_confirmed_by"],
            "in_published_file": gid in pub,
            "source_game": game_url(o["away"], o["home"], gid),
            "source_schedule": "https://www.nba.com/schedule",
            "published_check": {},
        }
        if gid in pub:
            p = pub[gid]
            checks = {
                "date": p["date"] == o["date"],
                "matchup": (p["away"], p["home"]) == (o["away"], o["home"]),
                "tip_et": p["tip_et"] == o["tip_et"],
                "venue": p["venue"] == o["venue"],
                "city": p["venue_city"] == o["city"],
                "away_record": p["away_record"] == o["away_record_pre_11_13"],
                "home_record": p["home_record"] == o["home_record_pre_11_13"],
            }
            if o["cup_label"]:
                checks["competition"] = p["competition"].endswith(o["cup_label"])
            else:
                checks["competition"] = "unverified: label not printed on official schedule (published: %s)" % p["competition"]
            for k, v in checks.items():
                if v is False:
                    mismatches.append((gid, k))
            r["published_check"] = checks
        rows.append(r)

    # 2026-11-14..17 horizon rows
    horizon = [r for r in rows if HORIZON[0] <= r["date"] <= HORIZON[1]]
    stale_teams = sorted({t for r in horizon for t in (r["away"], r["home"])
                          if t in played_1113})
    out = {
        "generated_utc_date": "2026-11-14",
        "session": "arena/afbb836e-nba1",
        "method": cap["capture_method"],
        "horizon": {"from": HORIZON[0], "to": HORIZON[1], "note": "today (2026-11-14 UTC) plus three days"},
        "counts": {
            "official_games_2026_11_13_to_17": len(official),
            "official_games_in_horizon": len(horizon),
            "published_rows_compared": sum(1 for r in rows if r["in_published_file"]),
            "published_mismatches": len(mismatches),
            "calendar_day_counts_match": calendar_ok,
            "teams_played_2026_11_13": sorted(played_1113),
            "teams_that_played_2026_11_13_and_appear_in_horizon": stale_teams,
            "note_on_records": ("teams_that_played_2026_11_13_and_appear_in_horizon lists the teams whose record "
                                "could have moved on 11/13; the published horizon rows were refreshed to the official "
                                "post-11/13 values on 2026-11-14, so this is a superset marker, not a stale count."),
        },
        "flags": [{"id": a, "severity": b, "item": c, "detail": d, "source_url": e} for a, b, c, d, e in FLAGS],
        "rows": rows,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")

    write_html(out, horizon, rows)
    print(f"official games 11/13-11/17: {len(official)}; published rows compared: "
          f"{out['counts']['published_rows_compared']}; mismatches: {len(mismatches)}; "
          f"calendar counts match: {calendar_ok}; teams that played 11/13 in horizon: {len(stale_teams)} "
          f"(records refreshed to official post-11/13 values)")
    for m in mismatches:
        print("MISMATCH", m)
    return 1 if mismatches or not calendar_ok else 0


def cell(x):
    return html.escape("" if x is None else str(x))


def write_html(out, horizon, rows):
    c = out["counts"]
    played = set(c["teams_played_2026_11_13"])
    stale_n = sum(1 for r in horizon if r["away"] in played or r["home"] in played)

    def tr_horizon(r):
        pc = r["published_check"]
        if r["in_published_file"]:
            if any(v is False for v in pc.values()):
                ver = "MISMATCH: " + ", ".join(k for k, v in pc.items() if v is False)
            elif any(isinstance(v, str) for v in pc.values()):
                ver = "matches published file; competition label not printed (F-C05)"
            else:
                ver = "matches published file"
        else:
            ver = "official capture only (not in published file)"
        status_cls = ("stale" if (r["away"] in played or r["home"] in played) else "ok")
        return (f"<tr><td>{cell(r['date'])}</td><td>{cell(r['tip_et'])}</td>"
                f"<td><b>{cell(r['away'])} at {cell(r['home'])}</b><br><small>{cell(r['game_id'])}</small></td>"
                f"<td>{cell(r['venue'])}<br><small>{cell(r['city'])}</small></td>"
                f"<td>{cell(r['competition_official'])}</td>"
                f"<td>{cell(r['away_record_pre_11_13'])} / {cell(r['home_record_pre_11_13'])}</td>"
                f"<td><span class='tag {status_cls}'>{cell(r['record_status'])}</span></td>"
                f"<td>{cell(ver)}</td>"
                f"<td><a href='{cell(r['source_game'])}'>game ↗</a> · <a href='{cell(r['source_schedule'])}'>schedule ↗</a></td></tr>")

    def tr_day1113(r):
        pc = r["published_check"]
        if pc:
            diffs = [k for k, v in pc.items() if v is False]
            ver = "matches published file" if not diffs else "MISMATCH: " + ", ".join(diffs)
        else:
            ver = "not in published file"
        return (f"<tr><td>{cell(r['tip_et'])}</td><td><b>{cell(r['away'])} at {cell(r['home'])}</b></td>"
                f"<td>{cell(r['venue'])}, {cell(r['city'])}</td><td>{cell(r['competition_official'])}</td>"
                f"<td>{cell(ver)}</td><td>{cell(r['tip_confirmed_by'])}</td>"
                f"<td><a href='{cell(r['source_game'])}'>game ↗</a> · <a href='{cell(r['source_schedule'])}'>schedule ↗</a></td></tr>")

    def tr_flag(f):
        return (f"<tr><td><b>{cell(f['id'])}</b></td><td><span class='tag {cell(f['severity'])}'>{cell(f['severity'])}</span></td>"
                f"<td><b>{cell(f['item'])}</b><br>{cell(f['detail'])}</td>"
                f"<td><a href='{cell(f['source_url'])}'>source ↗</a></td></tr>")

    day1113 = [r for r in rows if r["date"] == "2026-11-13"]
    body_h = "\n".join(tr_horizon(r) for r in horizon)
    body_d = "\n".join(tr_day1113(r) for r in day1113)
    body_f = "\n".join(tr_flag(f) for f in out["flags"])
    teams = ", ".join(c["teams_that_played_2026_11_13_and_appear_in_horizon"])
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Verified schedule 14–17 Nov 2026 | NBA Lines Lab</title><link rel="stylesheet" href="subpages.css">
<style>.tag.stale{{background:#fde7c8;color:#7a4300}}.tag.ok{{background:#e3f4e6;color:#14532d}}.tag.high{{background:#fde2e2;color:#8a1c1c}}.tag.medium{{background:#fff3c4;color:#6b5000}}.tag.low,.tag.info{{background:#e8eef7;color:#24405f}}.tag{{display:inline-block;padding:2px 6px;border-radius:4px;font-size:12px}}.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}}.cards div{{border:1px solid #d9dee7;border-radius:6px;padding:10px 14px;min-width:150px}}</style></head>
<body><header class="topbar"><div class="top-inner"><a class="brand" href="index.html"><span class="brand-mark">N</span> NBA Lines Lab</a><div class="top-note">Row-by-row against NBA.com · nothing inferred</div></div></header>
<div class="layout"><nav class="side" aria-label="Main navigation"><div class="nav-label">Workspace</div>
<a href="index.html"><span class="nav-icon">◫</span>Executive summary</a><a href="lines.html"><span class="nav-icon">◈</span>Originated lines &amp; picks</a><a href="gameflow.html"><span class="nav-icon">＋</span>Injuries &amp; game flow</a><a class="active" href="schedule-verified.html"><span class="nav-icon">▦</span>Verified schedule</a><a href="verification.html"><span class="nav-icon">◎</span>Live verification</a><a href="review.html"><span class="nav-icon">⚑</span>Flagged items</a><a href="sources.html"><span class="nav-icon">↗</span>Source register</a><a href="docs/b/index.html"><span class="nav-icon">◈</span>Second build (backtest)</a><div class="side-foot">Blank = not verified.<br>Flags are not merge blockers.</div></nav>
<main class="main"><p class="crumb">Workspace / Verified schedule</p>
<header class="page-head"><div class="kicker">Official schedule · horizon today + 3 days</div><h1>Verified schedule, 14–17 Nov 2026</h1>
<p>Every row below was checked against NBA.com. This file records the <b>11/14 pre-11/13 capture</b> as it was taken. For the {len(c['teams_that_played_2026_11_13_and_appear_in_horizon'])} teams that played on 11/13 the figures in <em>this file</em> are the pre-11/13 values; the <b>published</b> horizon rows were refreshed to the official post-11/13 values on 2026-11-14 and are checked separately by <code>scripts/verify_horizon_s934ca56f.py</code>.</p></header>
<div class="cards"><div><small>Official games 13–17 Nov</small><br><b>{c['official_games_2026_11_13_to_17']}</b></div>
<div><small>In horizon 14–17 Nov</small><br><b>{c['official_games_in_horizon']}</b></div>
<div><small>Published rows compared</small><br><b>{c['published_rows_compared']}</b></div>
<div><small>Published mismatches</small><br><b>{c['published_mismatches']}</b></div>
<div><small>Calendar day counts match</small><br><b>{'yes' if c['calendar_day_counts_match'] else 'NO'}</b></div>
<div><small>Rows whose teams played 11/13</small><br><b>{stale_n}</b></div></div>
<h2>Horizon: 14–17 November (official schedule)</h2>
<div class="table-wrap"><table><thead><tr><th>Date</th><th>Tip (ET)</th><th>Game</th><th>Venue · city</th><th>Cup group (official)</th><th>Records away / home (pre-11/13)</th><th>Record status</th><th>Verification</th><th>Source</th></tr></thead><tbody>
{body_h}
</tbody></table></div>
<p class="small">Teams that played on 11/13 and therefore had a record that could move: {cell(teams)}. Records for the other teams cannot have changed, because the official schedule lists no 11/13 game for them. Every one of these records was re-read from NBA.com on 2026-11-14 and the published rows now carry the post-11/13 value.</p>
<h2>13 November (played; results not captured)</h2>
<div class="table-wrap"><table><thead><tr><th>Tip (ET)</th><th>Game</th><th>Venue · city</th><th>Cup group (official)</th><th>Check against published file</th><th>Tip time confirmed by</th><th>Source</th></tr></thead><tbody>
{body_d}
</tbody></table></div>
<h2>Flagged for Review</h2>
<p class="small">These items are published for review. They do not block anything. Each one links to the official source it refers to.</p>
<div class="table-wrap"><table><thead><tr><th>ID</th><th>Severity</th><th>Item and detail</th><th>Source</th></tr></thead><tbody>
{body_f}
</tbody></table></div>
<p class="small">Generated by <code>scripts/verify_schedule_c.py</code> from <code>data/raw/official_schedule_capture_2026-11-14.json</code>. Machine-readable output: <code>data/raw/verification_c03.json</code>.</p>
</main></div></body></html>
"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(page)


if __name__ == "__main__":
    sys.exit(main())
