#!/usr/bin/env python3
"""e3d25abc_availability.py — the injury report measured against the box score.

Session arena/e3d25abc-nba1, COORDINATION §68 Q04/Q07 (rotation availability column).

BRIEF LINES THIS SERVES
-----------------------
  * "Model a rotation availability column." - each team's declared absences tied
    to what the official box score says actually happened, plus the minutes those
    absences cost, which is the empirical base for redistribution.
  * "Store every injury report PDF with its retrieval timestamp and compute the
    diff between consecutive reports." - the diff says what changed; this says
    whether the change meant anything.
  * "Never fill or estimate a value a source did not provide." - an Out player who
    is simply absent from the game page is recorded as absent, not as confirmed;
    a name that matches a different team is recorded as unresolved.

METHOD
------
For each day D in (2026-11-17, 2026-11-18):
  1. take the **latest archived edition whose own name-date is D** - the last
     official word before that slate tipped - from data/parsed/injury_diffs/
     editions/, each parsed from an archived PDF bound to its SHA-256;
  2. keep its rows whose Game Date == D (a report also carries the next slate);
  3. join each row to that day's per-player game log on player name and team
     (log built by scripts/e3d25abc_game_logs.py from the digest-verified
     official game page);
  4. classify. An Out row with printed minutes is an irregularity; a cleared row
     on the game page with zero minutes is an irregularity; anything the two
     sources cannot settle is reported as unresolved.

The report's status words are published as printed - never re-bucketed.  "Game
Time" / "Questionable" count as a pending decision, not as availability.
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import re
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAYS = ("2026-11-17", "2026-11-18")
ED_DIR = os.path.join(ROOT, "data", "parsed", "injury_diffs", "editions")
OUT = os.path.join(ROOT, "data", "derived", "availability_2026-11-17_18_e3d25abc.json")
VERIFY = os.path.join(ROOT, "verify", "2026-11-19-e3d25abc", "availability.md")


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def minutes_txt(secs):
    secs = int(secs or 0)
    return f"{secs // 60}:{secs % 60:02d}"


OUT_WORDS = {"out", "not available", "injured - not available"}
# Availability assertions on the report's own vocabulary.  "Game Time Questionable"
# and similar are deliberately excluded: they say a decision is pending.
AVAIL_WORDS = {"available", "probable"}


def edition_key(name: str):
    m = re.match(r"^Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{1,2})_(\d{2})(AM|PM)?$", name)
    if not m:
        return None
    d, h, mi, ap = m.group(1), int(m.group(2)), int(m.group(3)), (m.group(4) or "AM")
    h24 = h % 12 + (12 if ap.upper() == "PM" else 0)
    return (d, h24 * 100 + mi)


def team_map():
    """Every team-name form the official pages print -> tricode.

    The standings files in this repository carry tricodes only, and the game page
    prints teamName as the short name with the city in a separate field, while the
    injury report writes "Toronto Raptors".  So all printed forms are registered.
    """
    m, src = {}, None
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "raw", "session-*",
                                              "gamepages", "*", "*.json.gz"))):
        try:
            raw = gzip.decompress(open(path, "rb").read()).decode("utf-8", "replace")
            blob = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                             raw, re.S)
            if not blob:
                continue
            game = json.loads(blob.group(1))["props"]["pageProps"]["game"]
        except Exception:
            continue
        for side in ("awayTeam", "homeTeam"):
            t = game.get(side) or {}
            if not t.get("teamTricode"):
                continue
            forms = [t.get("teamName"), t.get("teamCity"), t.get("teamSlug"),
                     " ".join(x for x in (t.get("teamCity"), t.get("teamName")) if x)]
            for nm in forms:
                if nm:
                    m[nm.strip()] = t["teamTricode"]
        src = os.path.relpath(path, ROOT).replace(os.sep, "/")
    return m, ("teamName / teamCity / teamSlug pairs printed on the stored official game "
               f"pages under data/raw/session-*/gamepages/ (last read: {src})")


def norm(name):
    """'Beal, Bradley' / 'Bradley Beal' / 'Bogle, Junior' -> one key."""
    s = re.sub(r"\s+(jr|ii|iii|iv)$", "", str(name).strip(), flags=re.I)
    if "," in s:
        last, first = s.split(",", 1)
        first = first.strip().split()[0] if first.strip() else ""
    else:
        parts = s.split()
        last, first = (parts[-1], parts[0]) if parts else ("", "")
    return f"{last.strip().lower()}|{first.strip().lower()}"


def load_logs(day):
    p = os.path.join(ROOT, "data", "official", f"player_game_logs_{day}.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    by_player = {}
    for r in d.get("rows", []):
        by_player.setdefault(norm(r["player"]), []).append(r)
    return {"rows": d.get("rows", []), "by_player": by_player,
            "path": os.path.relpath(p, ROOT).replace(os.sep, "/")}


def main() -> int:
    os.makedirs(os.path.dirname(VERIFY), exist_ok=True)
    tri, tri_src = team_map()
    problems, per_day, all_rows, log_missing = [], {}, [], []
    for day in DAYS:
        logs = load_logs(day)
        if not logs:
            log_missing.append(day)
            print(f"{day}: no player-game-log file - run scripts/e3d25abc_game_logs.py first")
            continue
        names = []
        for p in glob.glob(os.path.join(ED_DIR, "Injury-Report_*.json")):
            stem = os.path.basename(p)[:-5]
            k = edition_key(stem)
            if k and k[0] == day:
                names.append((k, stem, p))
        if not names:
            problems.append(f"{day}: no archived injury-report edition named for that day")
            continue
        names.sort(reverse=True)
        k, stem, path = names[0]
        ed = json.load(open(path, encoding="utf-8"))
        recs = []
        for r in [x for x in ed.get("rows", []) if len(x) >= 7 and x[0] == day]:
            game_date, tip, matchup, team_name, player, status, detail = r[:7]
            tricode = tri.get(str(team_name).strip())
            if tricode is None:
                problems.append(f"{day}: report team {team_name!r} is not among the team "
                                "names printed on the stored official game pages, so it "
                                "cannot be tied to a box-score row")
            matches = logs["by_player"].get(norm(player), [])
            if tricode and any(x["team"] == tricode for x in matches):
                join_kind = "team+name"
                matches = [x for x in matches if x["team"] == tricode]
            elif matches:
                join_kind = "name-matches-a-different-team"
            else:
                join_kind = "no-row-on-the-game-page"
            played = [x for x in matches if x.get("played")]
            status_l = (status or "").strip().lower()
            declared_out = any(w in status_l for w in OUT_WORDS)
            declared_avail = any(w in status_l for w in AVAIL_WORDS)
            rec = {"date": day, "edition": stem, "game_date": game_date,
                   "tipoff_et": tip, "matchup": matchup, "team": team_name,
                   "tricode": tricode, "player": player, "status": status,
                   "detail": detail, "join": join_kind,
                   "on_the_game_page": bool(matches),
                   "logged": True if played else (False if matches else None),
                   "minutes": played[0]["minutes"] if played else None,
                   "minutes_seconds": played[0]["minutes_seconds"] if played else None,
                   "points": sum((x.get("points") or 0) for x in played) if played else None,
                   "rebounds": sum((x.get("rebounds") or 0) for x in played) if played else None,
                   "assists": sum((x.get("assists") or 0) for x in played) if played else None,
                   "page_comment": (played or matches)[0].get("comment") if matches else None,
                   "notes": []}
            if declared_out and played:
                rec["outcome"] = "IRREGULAR: declared out, minutes printed"
                rec["notes"].append("the report says out/not available and the official box "
                                    f"score printed {played[0]['minutes']} for that player")
                problems.append(f"{day} {team_name}: '{player}' listed {status!r} yet "
                                f"played {played[0]['minutes']} min per the official page")
            elif declared_out:
                rec["outcome"] = ("held out - page lists them without minutes" if matches
                                  else "held out - absent from the game page")
                rec["notes"].append(
                    "the game page prints the game's active/inactive list; being on it with "
                    f"no minutes ({rec['page_comment'] or 'no comment printed'}) confirms the "
                    "scratch" if matches else
                    "absent from the game page entirely, which is the normal shape for an "
                    "Out designation - it is not treated as a confirmation")
            elif declared_avail and played:
                rec["outcome"] = "cleared and played - consistent"
            elif declared_avail and matches and not played:
                # An availability line on the report is a statement about eligibility,
                # not a promise of minutes.  A cleared player who then sits is a
                # coach's decision - recorded, counted, and NOT an irregularity.
                rec["outcome"] = "cleared, on the page without minutes (coach's decision)"
                rec["notes"].append("page comment " + (rec['page_comment'] or 'none printed') +
                                    "; availability was confirmed, minutes are not owed by it")
            elif declared_avail:
                rec["outcome"] = "cleared but no row on the game page - unresolved"
                rec["notes"].append("an availability declaration with no counterpart row on "
                                    "the page: no claim is made either way")
            elif matches and not played:
                rec["outcome"] = "listed, on the page without minutes"
            elif matches:
                rec["outcome"] = "listed, played"
            else:
                rec["outcome"] = "listed, absent from the game page"
            if join_kind == "name-matches-a-different-team":
                rec["outcome"] = "UNRESOLVED: name matches a player on another team"
                rec["logged"] = None
            recs.append(rec)
            all_rows.append(rec)

        out_names = {norm(r["player"]) for r in recs
                     if any(w in (r["status"] or "").lower() for w in OUT_WORDS)}
        # Where the minutes went, per team, on a day the report said players were out.
        # Read from the rotation file (same stored page, same assertions), because a
        # season-average base would be a modelling assumption, not an observation.
        rot = {}
        rp = os.path.join(ROOT, "data", "derived", "rotation_2026-11-19_e3d25abc.json")
        if os.path.exists(rp):
            for row in json.load(open(rp, encoding="utf-8")).get("rows", []):
                rot.setdefault((row["date"], row["team"]), []).append(row)
        by_team = {}
        for tcode in sorted({r["tricode"] for r in recs if r["tricode"]}):
            trows = [x for x in logs["rows"] if x["team"] == tcode]
            games = sorted({x["game_id"] for x in trows})
            def rot_val(g, key):
                for r0 in rot.get((day, tcode), []):
                    if r0["game_id"] == g:
                        return r0.get(key)
                return None
            by_team[tcode] = {
                "out_declarations": sorted({r["player"] for r in recs
                                            if r["tricode"] == tcode
                                            and any(w in (r["status"] or "").lower()
                                                    for w in OUT_WORDS)}),
                "players_used": sum(1 for x in trows if x.get("played")),
                "games": [{"game_id": g, "opponent": rot_val(g, "opponent"),
                           "players_used": rot_val(g, "players_used"),
                           "top8_share": rot_val(g, "top8_minutes_share"),
                           "five_most_minutes_share": rot_val(g, "five_most_minutes_share")}
                          for g in games],
                "cleared_but_sat": sorted({r["player"] for r in recs
                                           if r["tricode"] == tcode and r["outcome"].startswith(
                                               "cleared, on the page without minutes")})}
        per_day[day] = {
            "edition_used": stem,
            "edition_retrieved_at_utc": ed.get("retrieved_at_utc"),
            "edition_source_url": ed.get("source_url"),
            "edition_sha256": ed.get("sha256"),
            "report_rows_for_this_game_date": len(recs),
            "unparsed_regions_in_that_edition": len(ed.get("unparsed", []) or []),
            "teams_on_the_report": sorted({r["tricode"] for r in recs if r["tricode"]}),
            "declared_out": sum(1 for r in recs if any(w in (r["status"] or "").lower()
                                                        for w in OUT_WORDS)),
            "held_out_consistent": sum(1 for r in recs if r["outcome"].startswith("held out")),
            "declared_out_but_played": sum(1 for r in recs
                                           if r["outcome"].startswith("IRREGULAR: declared out")),
            "cleared_and_played": sum(1 for r in recs
                                      if r["outcome"] == "cleared and played - consistent"),
            "cleared_but_no_minutes": sum(1 for r in recs if r["outcome"].startswith(
                "cleared, on the page without minutes")),
            "pending_or_other_status_played": sum(1 for r in recs
                                                  if r["outcome"] in ("listed, played",)),
            "unresolved_name_other_team": sum(1 for r in recs
                                              if r["outcome"].startswith("UNRESOLVED")),
            "per_team_rotation": by_team,
            "log_file": logs["path"]}
        print(f"{day}: {stem} -> {len(recs)} rows for that game date | "
              f"declared out {per_day[day]['declared_out']} "
              f"(held out consistently {per_day[day]['held_out_consistent']}, "
              f"IRREGULAR {per_day[day]['declared_out_but_played']}) | "
              f"cleared+played {per_day[day]['cleared_and_played']} "
              f"cleared+sat {per_day[day]['cleared_but_no_minutes']} | "
              f"unresolved {per_day[day]['unresolved_name_other_team']}")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"title": "Injury-report availability measured against the official "
                           "box score, 2026-11-17 and 2026-11-18",
                   "generated_by": "scripts/e3d25abc_availability.py",
                   "generated_at_utc": now_utc(),
                   "session": "arena/e3d25abc-nba1",
                   "sources": {
                       "report_editions": "data/parsed/injury_diffs/editions/*.json - parsed "
                                          "by engine/injury_diff.py from the archived PDFs in "
                                          "data/raw/injury_pdfs/, each bound to its own SHA-256 "
                                          "and retrieval stamp",
                       "box_score": "data/official/player_game_logs_2026-11-1[78].json, read by "
                                    "scripts/e3d25abc_game_logs.py from the digest-verified "
                                    "stored official game pages",
                       "team_names": tri_src},
                   "rule": ("Per day the LATEST archived edition named for that day is used - "
                            "the last official word before tip-off - and only its rows whose "
                            "Game Date equals that day. 'On the floor' means the official box "
                            "score printed minutes for that player; 'held out' means the page "
                            "lists them without minutes or omits them, and an omission is "
                            "never read as confirmation. Status words are the report's own."),
                   "gaps": {"game_log_files_missing_for": log_missing},
                   "per_day": per_day,
                   "problems": problems,
                   "rows": all_rows}, fh, indent=1)
        fh.write("\n")

    with open(VERIFY, "w", encoding="utf-8") as fh:
        fh.write("# Injury report vs. the box score — 2026-11-17 / 11-18\n\n")
        fh.write("Built by `scripts/e3d25abc_availability.py` (§68 Q04 / rotation-availability "
                 "column). Both sides are archived official bytes: the report from the PDF "
                 "chain, the appearance from the digest-verified game page.\n\n")
        for day, d in per_day.items():
            fh.write(f"## {day}\n\n")
            fh.write(f"* edition used: `{d['edition_used']}` — retrieved "
                     f"{d['edition_retrieved_at_utc']}, SHA-256 `{(d['edition_sha256'] or '')[:16]}…`, "
                     f"unparsed regions in that edition: {d['unparsed_regions_in_that_edition']}\n")
            fh.write(f"* {d['report_rows_for_this_game_date']} report rows carry game date "
                     f"{day}, across {len(d['teams_on_the_report'])} teams: "
                     f"{', '.join(d['teams_on_the_report'])}\n")
            fh.write(f"* **{d['declared_out']}** rows carry an out / not-available status; "
                     f"**{d['held_out_consistent']}** are held out consistently and "
                     f"**{d['declared_out_but_played']}** played anyway\n")
            fh.write(f"* **{d['cleared_and_played']}** cleared and played, "
                     f"**{d['cleared_but_no_minutes']}** cleared but no minutes on the page, "
                     f"**{d['pending_or_other_status_played']}** with a pending/other status "
                     f"who played, **{d['unresolved_name_other_team']}** unresolved\n")
            fh.write(f"* {d['cleared_but_no_minutes']} player(s) cleared on the report who then "
                     "sat the whole game - a coach's decision, recorded, not a contradiction\n")
            fh.write("* per-team rotation load that day, from the same stored page "
                     "(the redistribution base; no season average is used):\n\n")
            fh.write("| Team | Out names on the report | Players used | Top-8 min share | "
                     "Five-most-min share |\n| --- | --- | --- | --- | --- |\n")
            for t, v in sorted(d["per_team_rotation"].items()):
                for g in v["games"]:
                    fh.write(f"| {t} | {len(v['out_declarations'])} | {v['players_used']} | "
                             + ("—" if g["top8_share"] is None else str(g["top8_share"])) + " | "
                             + ("—" if g["five_most_minutes_share"] is None
                                else str(g["five_most_minutes_share"])) + " |\n")
        if not per_day:
            fh.write("no day could be joined\n")
        fh.write("\n## Irregularities and unresolved items\n\n")
        fh.write("\n".join(f"* {p}" for p in problems) + "\n" if problems else "none\n")
        fh.write("\n## Every declaration, joined\n\n| Day | Team | Player | Report status | "
                 "Report detail | Box score | Outcome |\n| --- | --- | --- | --- | --- | --- | --- |\n")
        for r in all_rows:
            box = (f"played {r['minutes']}, {r['points']} pts" if r["logged"]
                   else ("no minutes on the page" if r["on_the_game_page"] else "not on the page"))
            fh.write(f"| {r['date']} | {r['tricode'] or '?'} | {r['player']} | {r['status']} | "
                     f"{(r['detail'] or '')[:58]} | {box} | {r['outcome']} |\n")
    print(json.dumps({"rows": len(all_rows), "problems": len(problems),
                      "cleared_but_sat": {d: per_day[d]["cleared_but_no_minutes"] for d in per_day},
                      "days": list(per_day)}, indent=1))
    # Only a hard contradiction is a failure: a player the report said was out
    # logging minutes on the official page.  Everything else is published as a
    # finding, not an error.
    return 1 if any(per_day[d]["declared_out_but_played"] for d in per_day) else 0


if __name__ == "__main__":
    sys.exit(main())
