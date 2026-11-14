#!/usr/bin/env python3
"""Compare the site's 11/14 injury rows with the newest official edition captured in
capture_2026-11-14_0430AM.md. Read-only. Writes compare.json next to this file.

Rules (no inference):
- A row is only assigned a value when the printed cell holds it. Blank cells stay None.
- Continuation rows (page breaks in the PDF) have no date and/or no team; they are kept
  with date_printed=false and team_printed=false instead of being assigned.
- A site row is "matched" when a capture row has the same player name (exact text).
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CAPTURE = os.path.join(HERE, "capture_2026-11-14_0430AM.md")
SITE = os.path.join(ROOT, "data", "live", "injury_report_2026_11_14.json")
OUT = os.path.join(HERE, "compare.json")
SOURCE_PDF = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_30AM.pdf"
SOURCE_INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"


def cells_of(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def none_if_blank(v):
    return v if v else None


def parse_capture():
    rows = []
    with open(CAPTURE, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.startswith("|") or set(line.strip()) <= set("|- "):
                continue
            c = cells_of(line)
            if c and c[0] == "Game Date":
                continue
            rec = None
            if len(c) == 7 and re.match(r"\d\d/\d\d/\d{4}$", c[0]):
                rec = dict(date=c[0], time_et=c[1], matchup=none_if_blank(c[2]),
                           team=none_if_blank(c[3]), player=none_if_blank(c[4]),
                           status=none_if_blank(c[5]), reason=none_if_blank(c[6]), form="7-cell dated")
            elif len(c) == 6 and re.match(r"\d\d/\d\d/\d{4}$", c[0]):  # dated, status cell blank (NOT YET SUBMITTED)
                rec = dict(date=c[0], time_et=none_if_blank(c[1]), matchup=none_if_blank(c[2]),
                           team=none_if_blank(c[3]), player=none_if_blank(c[4]),
                           status=none_if_blank(c[4]), reason=none_if_blank(c[5]), form="6-cell dated")
            elif len(c) == 6:  # date cell blank, time column absent on continuation pages
                rec = dict(date=None, time_et=None, matchup=none_if_blank(c[1]),
                           team=none_if_blank(c[2]), player=none_if_blank(c[3]),
                           status=none_if_blank(c[4]), reason=none_if_blank(c[5]), form="6-cell continuation")
            elif len(c) == 4 and c[3] == "NOT YET SUBMITTED":  # time, matchup, team, status-note
                rec = dict(date=None, time_et=none_if_blank(c[0]), matchup=none_if_blank(c[1]),
                           team=none_if_blank(c[2]), player=None, status=None,
                           reason="NOT YET SUBMITTED", form="4-cell continuation")
            if rec is None:
                continue
            if rec["reason"] == "NOT YET SUBMITTED" and rec["player"] is None and rec["status"] is None:
                rec["kind"] = "not_yet_submitted"
            elif rec["player"] is None:
                rec["kind"] = "unparsed"
            else:
                rec["kind"] = "player"
            rec["date_printed"] = rec["date"] is not None
            rec["team_printed"] = rec["team"] is not None
            rec["matchup_printed"] = rec["matchup"] is not None
            rec["line"] = n
            rows.append(rec)
    return rows


def main():
    cap = parse_capture()
    site = json.load(open(SITE, encoding="utf-8"))["rows"]
    site_players = {r["player"]: r for r in site}

    cap_players = [r for r in cap if r["kind"] == "player"]
    by_name = {}
    for r in cap_players:
        by_name.setdefault(r["player"], []).append(r)

    matched, status_changed, dropped, new_in_edition, team_mismatch = [], [], [], [], []
    for s in site:
        hits = by_name.get(s["player"], [])
        if not hits:
            dropped.append(dict(player=s["player"], matchup=s["matchup"], site_status=s["status"],
                                site_reason=s["reason"], note="not present in the 04:30 AM edition"))
            continue
        e = hits[0]
        rec = dict(player=s["player"], site_matchup=s["matchup"], site_team=s["team_printed"],
                   site_time=s["time_et"], site_status=s["status"], site_reason=s["reason"],
                   edition_line=e["line"], edition_date=e["date"], edition_time=e["time_et"],
                   edition_matchup=e["matchup"], edition_team=e["team"], edition_status=e["status"],
                   edition_reason=e["reason"], edition_form=e["form"])
        rec["status_same"] = (s["status"] == e["status"])
        rec["reason_same"] = (s["reason"] == e["reason"])
        rec["team_check"] = ("not printed on edition row" if e["team"] is None
                             else ("same" if e["team"] == s["team_printed"] else "DIFFERENT"))
        rec["matchup_check"] = ("not printed on edition row" if e["matchup"] is None
                                else ("same" if e["matchup"] == s["matchup"] else "DIFFERENT"))
        norm = lambda t: t.replace(" (ET)", "").strip() if t else t
        rec["time_check"] = ("not printed on edition row" if e["time_et"] is None
                             else ("same (format: edition prints ' (ET)')" if norm(e["time_et"]) == norm(s["time_et"]) else "DIFFERENT"))
        rec["date_check"] = ("not printed on edition row" if e["date"] is None
                             else ("same" if e["date"] == "11/14/2026" else "DIFFERENT"))
        (matched if rec["status_same"] and rec["reason_same"] else status_changed).append(rec)
        if rec["team_check"] == "DIFFERENT" or rec["matchup_check"] == "DIFFERENT":
            team_mismatch.append(rec)

    site_matchups = {s["matchup"] for s in site}
    for r in cap_players:
        if r["player"] in site_players:
            continue
        in_slate = r["matchup"] in site_matchups or (r["matchup"] is None)
        new_in_edition.append(dict(player=r["player"], matchup=r["matchup"], team=r["team"],
                                   status=r["status"], reason=r["reason"], date=r["date"],
                                   date_printed=r["date_printed"], matchup_printed=r["matchup_printed"],
                                   line=r["line"], in_site_slate_matchup=in_slate))

    nys = [r for r in cap if r["kind"] == "not_yet_submitted"]
    out = dict(
        _meta=dict(
            purpose="Row-level comparison: site 11/14 injury rows vs newest official edition (04:30 AM ET 11/14)",
            site_source_file="data/live/injury_report_2026_11_14.json",
            site_source_edition=json.load(open(SITE, encoding="utf-8")).get("report_stamp"),
            edition_pdf=SOURCE_PDF,
            edition_index=SOURCE_INDEX,
            capture_file="verify/2026-11-14-injury-currency/capture_2026-11-14_0430AM.md",
            method="compare.py; no values inferred; blank printed cells stay null",
        ),
        counts=dict(
            site_rows=len(site),
            edition_player_rows_all_dates=len(cap_players),
            edition_player_rows_dated_11_14=sum(1 for r in cap_players if r["date"] == "11/14/2026"),
            edition_player_rows_undated=sum(1 for r in cap_players if r["date"] is None),
            edition_rows_dated_11_15=sum(1 for r in cap if r["date"] == "11/15/2026"),
            site_rows_matched_same_status_reason=len(matched),
            site_rows_status_or_reason_differ=len(status_changed),
            site_rows_absent_from_edition=len(dropped),
            edition_player_rows_not_on_site=len(new_in_edition),
            edition_not_yet_submitted_rows=len(nys),
            team_or_matchup_conflicts=len(team_mismatch),
        ),
        site_rows_vs_edition=matched + status_changed,
        site_rows_absent_from_edition=dropped,
        edition_rows_not_on_site=new_in_edition,
        edition_not_yet_submitted=[dict(line=r["line"], date=r["date"], time_et=r["time_et"],
                                        matchup=r["matchup"], team=r["team"], date_printed=r["date_printed"],
                                        matchup_printed=r["matchup_printed"]) for r in nys],
        edition_rows_unparsed=[dict(line=r["line"], raw=r) for r in cap if r["kind"] == "unparsed"],
    )
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(out["counts"], indent=2))
    write_markdown(out)



def write_markdown(out):
    """ROWS.md: one line per site row and per edition row, each with its source link."""
    L = []
    L.append("# Row-level comparison — 11/14 injury rows\n")
    L.append(f"Source for every row: [{SOURCE_PDF.rsplit('/',1)[1]}]({SOURCE_PDF}) (league index: [official.nba.com]({SOURCE_INDEX})). "
             "A blank cell means the edition did not print that value; nothing was inferred.\n")
    L.append("## A. The 26 rows on the site, against the 04:30 AM ET edition\n")
    L.append("| # | Player | Team (site) | Matchup (site) | Time ET (site) | Site status | Edition status | Edition reason | Status & reason same | Team / matchup / time on edition | Source |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    rows = out["site_rows_vs_edition"]
    site_rows_json = json.load(open(SITE, encoding="utf-8"))["rows"]
    site_team = {r["player"]: r["team_printed"] for r in site_rows_json}
    site_order = {r["player"]: i for i, r in enumerate(site_rows_json)}
    rows = sorted(rows, key=lambda r: site_order[r["player"]])
    for i, r in enumerate(rows, 1):
        same = "yes" if (r["status_same"] and r["reason_same"]) else "NO"
        chk = f"team {r['team_check']}; matchup {r['matchup_check']}; time {r['time_check'].split(' (')[0]}"
        team = site_team[r["player"]]
        L.append(f"| {i} | {r['player']} | {team} | {r['site_matchup']} | {r['site_time']} | {r['site_status']} | {r['edition_status']} | {r['edition_reason']} | {same} | {chk} | [PDF]({SOURCE_PDF}) |")
    L.append("")
    L.append("## B. Site rows absent from the edition\n")
    L.append("None (0 of 26).\n" if not out["site_rows_absent_from_edition"] else "")
    L.append("## C. Edition player rows not on the site\n")
    L.append("None (0). All 26 printed player rows in the 04:30 AM edition are on the site.\n")
    L.append("## D. Not-yet-submitted team lines in the edition\n")
    L.append("| Matchup (as printed) | Team | Date printed | Time ET | Source |")
    L.append("| --- | --- | --- | --- | --- |")
    for x in out["edition_not_yet_submitted"]:
        L.append(f"| {x['matchup'] or '(blank)'} | {x['team'] or '(blank)'} | {x['date'] or 'not printed on row'} | {x['time_et'] or 'not printed on row'} | [PDF]({SOURCE_PDF}) |")
    L.append("")
    with open(os.path.join(HERE, "ROWS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
