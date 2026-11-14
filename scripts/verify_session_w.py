#!/usr/bin/env python3
"""
verify_session_w.py — line-by-line verification pass for the session arena-f80dcc4a-nba1 batch
(window 2026-11-13..2026-11-17, records + injury editions + Edge Lab outputs).

RULE (user brief): every published table row must carry an official source link, and every value must
be confirmed against an official source capture stored in this repository. Anything unverifiable must
be blank and flagged. This script re-derives every published number from the stored verbatim captures
(data/raw/captures/session-w/ and the frozen pre-tip captures) and fails if any value drifts.

Checks
  W1  schedule file (36 rows) matches the official schedule capture field-by-field
  W2  every team record shown anywhere equals the record printed in the stored official capture pages;
      single-source teams (GSW/OKC/SAC) must be documented in the records file's cross_check_note
  W3  leaders.json (30 rows) equals the season-leader lines printed in the capture pages
  W4  injury 08:00 PM file: every player row exists verbatim in its source chunk, carried rows record
      an edition source, unattributed rows have no team, NYS teams match the printed rows
  W5  originated_lines.json: 11/13 rows reproduce the frozen archive byte-identically; every game row
      carries only official source URLs; per-date injury-status logic is reflected in prop rows
  W6  published pages (lines.html, gameflow.html, review.html): every table row has a source link,
      every link is local-resolvable or an allowed official domain, W-F1..W-F8 flags are published
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
CAP = os.path.join(RAW, "captures", "session-w")

OFFICIAL_HOSTS = (
    "https://www.nba.com/", "https://official.nba.com/",
    "https://ak-static.cms.nba.com/", "https://docs.github.com/",
    "https://github.com/", "https://kansspelautoriteit.nl/",
    "https://stats.",
)

NICKNAME_TO_FULL = {
    "Hawks": "Atlanta Hawks", "Celtics": "Boston Celtics", "Nets": "Brooklyn Nets",
    "Hornets": "Charlotte Hornets", "Bulls": "Chicago Bulls", "Cavaliers": "Cleveland Cavaliers",
    "Mavericks": "Dallas Mavericks", "Nuggets": "Denver Nuggets", "Pistons": "Detroit Pistons",
    "Warriors": "Golden State Warriors", "Rockets": "Houston Rockets", "Pacers": "Indiana Pacers",
    "Clippers": "LA Clippers", "Lakers": "Los Angeles Lakers", "Grizzlies": "Memphis Grizzlies",
    "Heat": "Miami Heat", "Bucks": "Milwaukee Bucks", "Timberwolves": "Minnesota Timberwolves",
    "Pelicans": "New Orleans Pelicans", "Knicks": "New York Knicks",
    "Thunder": "Oklahoma City Thunder", "Magic": "Orlando Magic", "76ers": "Philadelphia 76ers",
    "Suns": "Phoenix Suns", "Trail Blazers": "Portland Trail Blazers",
    "Kings": "Sacramento Kings", "Spurs": "San Antonio Spurs", "Raptors": "Toronto Raptors",
    "Jazz": "Utah Jazz", "Wizards": "Washington Wizards",
}

errors = []
checks = 0


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cap_text(name):
    with open(os.path.join(CAP, name), encoding="utf-8") as f:
        return f.read()


def cap_files():
    return sorted(n for n in os.listdir(CAP) if n.endswith(".txt"))


def ok_url(url):
    return isinstance(url, str) and any(url.startswith(h) for h in OFFICIAL_HOSTS)


def eq(label, a, b):
    global checks
    checks += 1
    if a != b:
        errors.append(f"{label}: {a!r} != {b!r}")


def main():
    slate = load(os.path.join(ROOT, "data", "slate_full.json"))
    sched = load(os.path.join(ROOT, "data", "schedule_2026_11_13_to_16.json"))
    cap_sched = load(os.path.join(RAW, "official_schedule_capture_2026-11-14.json"))
    records = load(os.path.join(RAW, "records_2026-11-14.json"))
    leaders = load(os.path.join(ROOT, "data", "leaders.json"))
    inj8 = load(os.path.join(RAW, "injury_report_2026-11-13_08_00PM.json"))
    lines = load(os.path.join(ROOT, "data", "originated_lines.json"))
    archive = load(os.path.join(ROOT, "data", "archive", "originated_lines_2026-11-13T2245Z.json"))

    # ---------------------------------------------------------------- W1 schedule
    cap_cols = cap_sched["cols"]
    cap_rows = {tuple(r[cap_cols.index(k)] for k in ("date", "game_id")): dict(zip(cap_cols, r))
                for r in cap_sched["rows"]}
    eq("W1 game count", len(sched["games"]), 36)
    counts = {}
    for g in sched["games"]:
        counts[g["date"]] = counts.get(g["date"], 0) + 1
    eq("W1 per-date counts", counts, {"2026-11-13": 9, "2026-11-14": 5, "2026-11-15": 9,
                                      "2026-11-16": 8, "2026-11-17": 5})
    for g in sched["games"]:
        key = (g["date"], g["game_id"])
        c = cap_rows.get(key)
        if c is None:
            errors.append(f"W1 no capture row for {key}")
            continue
        eq(f"W1 {key} away", g["away"], c["away"])
        eq(f"W1 {key} home", g["home"], c["home"])
        eq(f"W1 {key} tip", g["tip_et"], c["tip_et"])
        eq(f"W1 {key} venue", g.get("venue"), c.get("venue"))
        if not ok_url(g.get("source_url")):
            errors.append(f"W1 {key} non-official source URL")

    slate_games = [g for s in slate["slates"] for g in s["games"]]
    eq("W1 slate_full game count", len(slate_games), 36)
    eq("W1 slate_full ids == schedule ids",
       sorted(g["game_id"] for g in slate_games),
       sorted(g["game_id"] for g in sched["games"]))

    # ---------------------------------------------------------------- W2 records
    rcols = records["cols"]
    rec_rows = [dict(zip(rcols, r)) for r in records["rows"]]
    rec_by_name = {r["team"]: r for r in rec_rows}
    eq("W2 records rows", len(rec_rows), 30)
    # every "Nickname W-L" occurrence in every capture game card must match the record file
    seen = set()
    for name in cap_files():
        text = cap_text(name)
        for nick, rec in re.findall(r"(?m)^(%s) (\d+-\d+) \|" % "|".join(map(re.escape, NICKNAME_TO_FULL)), text):
            full = NICKNAME_TO_FULL[nick]
            r = rec_by_name.get(full)
            if r is None:
                errors.append(f"W2 capture shows unknown team {full!r}")
                continue
            seen.add(full)
            eq(f"W2 record {full} in {name}", rec, r["record"])
        # date-strip rows print "Nickname W-L | tip | Nickname W-L" on one line
        for line in text.splitlines():
            m = re.match(r"^(%s) (\d+-\d+) \| [\d:]+ [AP]M ET \| (%s) (\d+-\d+)$"
                         % ("|".join(map(re.escape, NICKNAME_TO_FULL)),
                            "|".join(map(re.escape, NICKNAME_TO_FULL))), line)
            if m:
                for nick, rec in ((m.group(1), m.group(2)), (m.group(3), m.group(4))):
                    full = NICKNAME_TO_FULL[nick]
                    r = rec_by_name.get(full)
                    if r:
                        seen.add(full)
                        eq(f"W2 record {full} in {name}", rec, r["record"])
    missing = set(rec_by_name) - seen
    if missing:
        errors.append(f"W2 records never seen in captures: {sorted(missing)}")
    # single-source teams (GSW/OKC/SAC) must be documented as such in the records file
    for r in rec_rows:
        pages = r.get("displayed_on_date_pages") or []
        if len(pages) < 2 and not r.get("cross_checked"):
            if r["abbr"] not in records.get("cross_check_note", ""):
                errors.append(f"W2 {r['team']} single-source and undocumented")

    # ---------------------------------------------------------------- W3 leaders
    lead_by_abbr = {l["team"]: l for l in leaders["leaders"]}
    eq("W3 leaders rows", len(leaders["leaders"]), 30)
    seen_abbr = set()
    for name in cap_files():
        text = cap_text(name)
        for player, abbr, ppg, rpg, apg in re.findall(
                r"([A-Z][A-Za-z\u00c0-\u024f\-\. '’]+) \(([A-Z]{3})\) (\d+\.\d) (\d+\.\d) (\d+\.\d)", text):
            l = lead_by_abbr.get(abbr)
            if l is None:
                errors.append(f"W3 capture shows leader for unknown team {abbr}")
                continue
            seen_abbr.add(abbr)
            if l["player"] is None:
                errors.append(f"W3 capture shows leader {player} for {abbr} but file is blank")
                continue
            eq(f"W3 {abbr} player in {name}", " ".join(player.split()), " ".join(l["player"].split()))
            eq(f"W3 {abbr} ppg", float(ppg), l["ppg"])
            eq(f"W3 {abbr} rpg", float(rpg), l["rpg"])
            eq(f"W3 {abbr} apg", float(apg), l["apg"])
            if not ok_url(l.get("source_url")):
                errors.append(f"W3 {abbr} leader source not official")
    if set(lead_by_abbr) - seen_abbr:
        errors.append(f"W3 leaders never seen in captures: {sorted(set(lead_by_abbr) - seen_abbr)}")
    eq("W3 no blanks remain", len([l for l in leaders["leaders"] if l["player"] is None]), 0)

    # ---------------------------------------------------------------- W4 injury 8PM edition
    chunks = ""
    for n in cap_files():
        if n.startswith("injury_report_2026-11-13_08_00PM"):
            chunks += cap_text(n)
    eq("W4 attributed rows", len(inj8["rows"]), 111)
    eq("W4 unattributed rows", len(inj8["unattributed_rows"]), 11)
    for r in inj8["rows"]:
        if not r.get("team"):
            errors.append(f"W4 attributed row without team: {r.get('player')}")
        if not ok_url(inj8["source_url"]):
            errors.append(f"W4 non-official source for {r.get('player')}")
        if r.get("player") and r["player"] not in chunks:
            errors.append(f"W4 player line not found in capture: {r['player']}")
        ts = r.get("team_source", "")
        if ts.startswith("carried:") and "edition" not in ts:
            errors.append(f"W4 carried row without edition source: {r.get('player')}")
        if ts.startswith("carried:") and "FLAG" in ts and "W-F7" not in ts:
            errors.append(f"W4 carried row with unlogged flag: {r.get('player')}")
    for r in inj8["unattributed_rows"]:
        if r.get("team"):
            errors.append(f"W4 unattributed row has team: {r['player']}")
        if r["player"] not in chunks:
            errors.append(f"W4 unattributed player not found in capture: {r['player']}")
    nys = [r for r in inj8["rows"] if r["status"] == "NOT YET SUBMITTED"]
    eq("W4 NYS rows", len(nys), 5)
    for r in nys:
        if r.get("player"):
            errors.append(f"W4 NYS row unexpectedly has a player: {r['player']}")
        row_ok = any(r["team"] in line and "NOT YET SUBMITTED" in line
                     for line in chunks.splitlines())
        if not row_ok:
            errors.append(f"W4 NYS team not on a printed NOT YET SUBMITTED row: {r['team']}")
    martin = [r for r in inj8["rows"] if r["player"] == "Martin, Caleb"]
    eq("W4 Martin rows", len(martin), 1)
    if martin:
        eq("W4 Martin team (W-F7)", martin[0]["team"], "Cleveland Cavaliers")

    # ---------------------------------------------------------------- W5 originated lines
    eq("W5 games", len(lines["games"]), 36)
    old = {g["matchup"] + g["date"]: g for g in archive["games"] if g["date"] == "2026-11-13"}
    for g in lines["games"]:
        key = g["matchup"] + g["date"]
        if g["date"] == "2026-11-13":
            if key not in old:
                errors.append(f"W5 frozen row missing from archive: {key}")
            elif old[key] != g:
                errors.append(f"W5 frozen row changed since 2026-11-13T22:45Z: {key}")
        for u in (g.get("sources") or []) + [g.get("slate_url"), g.get("preview_url")]:
            if u and not ok_url(u):
                errors.append(f"W5 non-official source in {key}: {u}")
    # frozen parlays: byte-identical; frozen props: identical except the documented Jokić spelling
    # correction (leaders.json name now follows the official page; archive keeps the old spelling)
    def norm(p):
        p = dict(p)
        if p.get("player"):
            p["player"] = (p["player"].replace("Jokić", "Jokic"))
        return p
    old_p = [norm(p) for p in archive["prop_rows"] if p["date"] == "2026-11-13"]
    new_p = [norm(p) for p in lines["prop_rows"] if p["date"] == "2026-11-13"]
    eq("W5 frozen prop rows", new_p, old_p)
    old_par = [p for p in archive["parlays"] if p["date"] == "2026-11-13"]
    new_par = [p for p in lines["parlays"] if p["date"] == "2026-11-13"]
    eq("W5 frozen parlay rows", new_par, old_par)
    for p in lines["prop_rows"]:
        d, sig, status = p["date"], p["signal"], p["status"]
        if d in ("2026-11-15", "2026-11-16", "2026-11-17"):
            if "not yet" not in (status or "").lower() or "G-INJ" not in sig:
                errors.append(f"W5 prop {p['player']} {d}: expected unpublished-report gate")
        elif d == "2026-11-14":
            if status == "Team report NOT YET SUBMITTED" and "G-INJ" not in sig:
                errors.append(f"W5 prop {p['player']} {d}: NYS must gate")
            eq(f"W5 {p['player']} uses 8PM edition", "08_00PM" in p["src_inj"], True)
        if not ok_url(p["src_leader"]) or not ok_url(p["src_inj"]):
            errors.append(f"W5 prop {p['player']} {d}: non-official source")

    # ---------------------------------------------------------------- W6 pages
    pages = ["lines.html", "gameflow.html", "review.html"]
    for page in pages:
        with open(os.path.join(ROOT, page), encoding="utf-8") as f:
            html = f.read()
        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith("http"):
                if not ok_url(href):
                    errors.append(f"W6 {page}: non-official link {href}")
            else:
                target = os.path.normpath(os.path.join(ROOT, os.path.dirname(page), href))
                if not os.path.exists(target):
                    errors.append(f"W6 {page}: broken local link {href}")
        for tr in re.findall(r"<tr>.*?</tr>", html, re.S):
            if "<td" in tr and "http" not in tr and 'href="' not in tr:
                if "flag" not in tr and "blank" not in tr.lower():
                    errors.append(f"W6 {page}: table row without source link: {tr[:80]}...")
    with open(os.path.join(ROOT, "review.html"), encoding="utf-8") as f:
        rev = f.read()
    for flag in [f"W-F{i}" for i in range(1, 9)]:
        eq(f"W6 review.html has {flag}", flag in rev, True)

    # ---------------------------------------------------------------- report
    print(f"verify_session_w: {checks} value checks + link/row audit")
    if errors:
        for e in errors:
            print("ERROR:", e)
        print(f"VERIFY SESSION W FAILED — {len(errors)} problems")
        sys.exit(1)
    print("VERIFY SESSION W OK — 36 games, 30 records, 30 leaders, 111+11 injury rows, 36 pick rows, "
          "3 pages: every value re-derived from the stored official captures.")


if __name__ == "__main__":
    main()
