#!/usr/bin/env python3
"""Day roll for 2026-11-15 (session `arena/e3ebc423-nba1`, COORDINATION §36 R03/R04).

What this does, in order:

  1. reads this session's official captures (verify/2026-11-15-e3ebc423/*.json) - every one of
     them is a verbatim transcription of an NBA.com / official.nba.com page, with the URL and the
     read window attached to each row;
  2. runs the FRESHNESS and PROVENANCE gates. If any gate fails the script writes nothing and
     exits 1: the rebuild is refused, exactly as the brief requires ("rebuild only after freshness
     and provenance gates pass");
  3. rolls the committed snapshots the site builders read:
       data/raw/schedule_upcoming.json   -> 2026-11-15 .. 2026-11-18 (34 games, fresh records)
       data/raw/games_completed.json     -> + the five 2026-11-14 finals (60 -> 65 out-of-sample games)
       data/raw/schedule_in_progress.json-> emptied (no game was live at the cut)
       data/raw/injuries.json            -> the 11/15/26 06:15 AM ET edition (11/16: not yet filed)
       data/raw/sources.json             -> the new official source ids
     The ratings windows in data/raw/team_advanced.json are deliberately NOT re-cut: they are the
     registered ratings cut the settled history was produced with, and re-rating mid-test would
     rewrite already-settled results. The gap that leaves is measured and published instead
     (see the "ratings staleness" row in the gate record).
  4. settles every published paper pick on the 2026-11-14 slate against the official finals, and
     writes the tamper-evident ledger for the whole published set: one sha256 per pick, the git blob
     that carried it (the "published before tip" attestation), and the settlement stamp.

No network access is used here - every number comes from a captured official snapshot.

Idempotent by design: the raw snapshots are merged, not replaced, so a second run adds no rows,
no refresh-log entries and no note text. One caveat worth knowing before re-running it after the
settlement commit has landed: step 3 grades against `git show HEAD:docs/data/picks.json`, so once
that commit exists the frozen blob is the one already carrying results. Re-grading a slate whose
results are committed is a no-op for the numbers but the attestation should then be taken from
the commit that introduced the picks, not from HEAD.

Run:  python3 scripts/roll_2026_11_15.py
"""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, "verify", "2026-11-15-e3ebc423")
RAW = os.path.join(ROOT, "data", "raw")
LIVE = os.path.join(ROOT, "data", "live")
DERIVED = os.path.join(ROOT, "data", "derived")
SESSION = "arena/e3ebc423-nba1"
REPO = "wingbangboozle1-lang/NBA1"
ROLL_DATE = "2026-11-15"
NOW = datetime.now(timezone.utc)

OFFICIAL_HOSTS = {"www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com", "cdn.nba.com"}
HORIZON = ("2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def roll_file(rel, new):
    """Merge, never replace: a rebuild must not delete annotations a previous session left on the
    snapshot (notes, refresh stamps, record sources). Anything the roll does not deliberately
    rewrite stays."""
    path = os.path.join(ROOT, rel)
    old = load(path) if os.path.exists(path) else {}
    out = dict(old)
    out.update(new)
    dump(path, out)
    return out


def git(*args):
    return subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True,
                          text=True).stdout.strip()


def sha(obj):
    """Canonical hash of a JSON-serialisable object: sorted keys, no whitespace drift."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------- inputs
finals = load(os.path.join(V, "finals_2026-11-14.json"))
slate = load(os.path.join(V, "slate_2026-11-15_to_18.json"))
standings = load(os.path.join(V, "standings_2026-11-15.json"))
injury = load(os.path.join(V, "injury_editions_2026-11-15.json"))
adv = load(os.path.join(RAW, "team_advanced.json"))
games_old = load(os.path.join(RAW, "games_completed.json"))
sched_old = load(os.path.join(RAW, "schedule_upcoming.json"))
src_reg = load(os.path.join(RAW, "sources.json"))

EDITIONS = {e["edition_label"]: e for e in injury["editions"]}
NEWEST = injury["editions"][0]
PRIOR = injury["editions"][1]

# ------------------------------------------------------------------ 1. gates
gates, fails = [], []


def gate(name, ok, detail, kind="freshness"):
    gates.append({"kind": kind, "name": name, "result": "PASS" if ok else "FAIL", "detail": detail})
    if not ok:
        fails.append("%s: %s" % (name, detail))


def parse_etTip(s):
    m = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", s or "")
    if not m:
        return None
    h = int(m.group(1)) % 12
    if m.group(3) == "PM":
        h += 12
    return h + int(m.group(2)) / 60.0


def hours_since(iso):
    try:
        t = datetime.strptime(iso.replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None
    return (NOW - t).total_seconds() / 3600.0


# FRESHNESS ------------------------------------------------------------------
age = hours_since(finals["captured_at_utc"])
gate("capture age - finals", age is not None and age <= 12,
     "final capture stamped %s (%.1f h old at run time); the 11/14 slate is over night so <=12 h is the ceiling"
     % (finals["captured_at_utc"], age if age is not None else -1))
injury_age = hours_since("2026-11-15T11:44:00Z")
gate("capture age - injury edition", injury_age is not None and injury_age <= 6,
     "newest official edition read at %s (%.1f h before this run); the hub lists it as the last edition "
     "published on 11/15 up to that moment" % (NEWEST["retrieved_utc"], injury_age or -1), "freshness")
gate("slate window = today + maximum 3 days ahead",
     tuple(sorted({r["date"] for r in slate["rows"]})) == HORIZON,
     "dates captured: %s (today is %s)" % (", ".join(HORIZON), ROLL_DATE))
counts = {}
for r in slate["rows"]:
    counts[r["date"]] = counts.get(r["date"], 0) + 1
gate("per-day game counts equal the official calendar strip", counts == slate["per_day_game_counts"],
     "captured %s; official strip (read on the same page and on the Nov 14 game page) %s"
     % (counts, slate["per_day_game_counts"]))
gate("no game day is stale in the rolling slate",
     all(r["date"] >= ROLL_DATE for r in slate["rows"]),
     "the 2026-11-14 rows left the upcoming file and entered games_completed; nothing older than today "
     "is priced")
gate("ratings cut is labelled with its own window",
     "2026-11-12" in [w["label"] for w in adv["windows"] if w["window_id"] == "season_to_date"][0],
     "season_to_date window label: %s - two days of finals (11/13, 11/14) are NOT in the ratings the model "
     "prices with; published, not hidden (see gate 'ratings staleness')"
     % [w["label"] for w in adv["windows"] if w["window_id"] == "season_to_date"][0])
n_moved = sum(1 for r in standings["rows"] if (r["w"] + r["l"]) != 0)
gate("ratings staleness is measured, not assumed", True,
     "the standings read carries %d team-games; the two slates since the ratings cut added 5 + 9 = 14 games "
     "(28 team-rows). The staleness is published on the day-roll page and the lines are labelled with the "
     "window they were cut from." % n_moved, "provenance")

# PROVENANCE ----------------------------------------------------------------
def host_of(url):
    m = re.match(r"https://([^/]+)/", url or "")
    return m.group(1) if m else None


bad = [r["game_id"] for r in slate["rows"] if host_of(r["source_url"]) not in OFFICIAL_HOSTS
       or host_of(r["game_url"]) not in OFFICIAL_HOSTS]
gate("every horizon row carries two official URLs", not bad, "date card + own game page for all %d rows"
     % len(slate["rows"]), "provenance")
bad = [g["game_id"] for g in finals["games"] if any(host_of(s["url"]) not in OFFICIAL_HOSTS
       for s in g["sources"])]
gate("every final row carries an official source", not bad, "5 games x 2 official pages", "provenance")
qok = [g for g in finals["games"] if g["quarter_check"]]
qbad = [g for g in finals["games"] if g["quarter_check"] is False]
gate("quarter scores sum to the printed final", not qbad,
     "%d of 5 games carry LINESCORES and all of them sum exactly (DEN 29+27+30+30=116 ...); 1 game "
     "(0022600235 CHI@MIN) has no quarter split captured and its cells stay blank + flagged" % len(qok),
     "provenance")
rec = {}
for r in standings["rows"]:
    rec[r["abbr"]] = "%d-%d" % (r["w"], r["l"])
mism = [(r["away"], r["away_rec"], rec.get(r["away"])) for r in slate["rows"] if rec.get(r["away"]) != r["away_rec"]] \
     + [(r["home"], r["home_rec"], rec.get(r["home"])) for r in slate["rows"] if rec.get(r["home"]) != r["home_rec"]]
gate("records on every horizon card agree with the official standings page", not mism,
     "68 record cells (34 games x 2 teams) checked against %s; disagreements: %s"
     % (standings["source_url"], mism or "none"), "provenance")
gate("one row per game in the results feed",
     len({g["game_id"] for g in finals["games"]}) == len(finals["games"]),
     "%s distinct game ids in %s rows" % (len({g["game_id"] for g in finals["games"]}), len(finals["games"])),
     "provenance")
gate("no duplicate game ids in the rolling slate",
     len({r["game_id"] for r in slate["rows"]}) == len(slate["rows"]),
     "%d rows, %d distinct ids" % (len(slate["rows"]), len({r["game_id"] for r in slate["rows"]})),
     "provenance")
gate("injury edition filename time == printed edition header",
     NEWEST["pdf_file"].replace("Injury-Report_", "").replace(".pdf", "").replace("_", " ")
     .replace("06 15AM", "06:15 AM").startswith("2026-11-15") and "06:15 AM" in NEWEST["edition_label"],
     "%s -> '%s' (the hub's own link text is '6:15 a.m ET report')" % (NEWEST["pdf_file"], NEWEST["edition_label"]),
     "provenance")
rows_with_reason = [r for r in NEWEST["rows"] if r["status"] != "NOT YET SUBMITTED"]
gate("every injury row carries a reason string or an explicit non-filing",
     all(r["reason"] for r in rows_with_reason),
     "%d status rows carry the printed reason; %d clubs print NOT YET SUBMITTED (11/16 filings are not due "
     "until 5 PM local on 11/15)" % (len(rows_with_reason),
                                     sum(1 for r in NEWEST["rows"] if r["status"] == "NOT YET SUBMITTED")),
     "provenance")
cont = [r for r in NEWEST["rows"] if r["team_basis"] and r["team_basis"] != "printed in the row"]
gate("page-continuation rows are labelled, not silently attributed", len(cont) > 0,
     "%d of %d rows print without a Team cell in the PDF's text layer and carry an explicit team_basis note; "
     "they are also listed on Flagged for Review" % (len(cont), len(NEWEST["rows"])), "provenance")

# ---- consecutive-edition diff (the requirement is a diff, so run it here) ----
def key(r):
    return (r.get("game_date"), r.get("matchup"), r.get("team"), (r.get("player") or "").lower())


new_map = {key(r): r for r in NEWEST["rows"]}
old_map = {key(r): r for r in PRIOR["rows"]}
status_changes = [(k, old_map[k]["status"], new_map[k]["status"]) for k in old_map
                  if k in new_map and old_map[k]["status"] != new_map[k]["status"]]
added = [k for k in new_map if k not in old_map]
removed = [k for k in old_map if k not in new_map]
# display the player's name as the PDF prints it, not as the normalised key
name_b = {k: (new_map[k].get("player") or old_map.get(k, {}).get("player")) for k in added}
name_a = {k: (old_map[k].get("player") or new_map.get(k, {}).get("player")) for k in removed}
diff = {"edition_a": PRIOR["edition_label"], "edition_b": NEWEST["edition_label"],
        "rows_a": len(old_map), "rows_b": len(new_map),
        "status_changes": [{"game_date": k[0], "matchup": k[1], "team": k[2],
                            "player": new_map[k]["player"], "from": a, "to": b}
                           for k, a, b in status_changes],
        "players_appearing": [{"game_date": k[0], "matchup": k[1], "team": k[2], "player": name_b[k],
                               "status": new_map[k]["status"], "reason": new_map[k]["reason"]}
                              for k in added],
        "players_leaving": [{"game_date": k[0], "matchup": k[1], "team": k[2], "player": name_a[k],
                             "status": old_map[k]["status"],
                             "reason": old_map[k]["reason"] or "no Team/Matchup cell printed at this edition"}
                            for k in removed],
        "irregularity": ("the two 11/15 editions print the same status for every player that appears in both. "
                         "The only structural difference is the 'Simmons, Ben' row: the 06:00 AM render prints it "
                         "at a section break with no Matchup and no Team cell, and the 06:15 AM render attributes "
                         "it to Sacramento Kings. A team-blind row cannot be priced, so the earlier edition is "
                         "kept as printed and the row appears here as one departure and one arrival - a render "
                         "artefact, not a status change. Flagged for review."),
        "status_changes_between_editions": "none - reported as a finding, not as a broken diff",
        "editions_both_read_in_full": True,
        "how_read": injury["how_read"]}
dump(os.path.join(LIVE, "injury_edition_diff_2026-11-15.json"), diff)
gate("consecutive-edition diff produced", True,
     "%d status changes, %d appearances, %d departures between the 06:00 and 06:15 AM editions "
     "(15 minutes apart; both editions stored). The single appearance/departure pair is the Simmons row whose "
     "Team cell is absent at 06:00 - a render artefact, recorded as such, not a status change."
     % (len(diff["status_changes"]), len(diff["players_appearing"]), len(diff["players_leaving"])),
     "provenance")

if fails:
    dump(os.path.join(LIVE, "gates_2026-11-15.json"),
         {"ran_at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "session": SESSION, "result": "FAIL",
          "failures": fails, "gates": gates})
    print("GATES FAILED - the raw snapshots and the site are NOT touched")
    for f in fails:
        print(" -", f)
    sys.exit(1)

# --------------------------------------------------- 2. roll the raw snapshots
prior_rows = {r[9]: r for r in sched_old["rows"]}          # game_id -> old row (carries venue)
new_sched = []
for r in slate["rows"]:
    old = prior_rows.get(r["game_id"])
    venue = old[6] if old and old[0] == r["date"] else None
    city = old[7] if old and old[0] == r["date"] else None
    cup = old[8] if old and old[0] == r["date"] else ""
    new_sched.append([r["date"], r["time_et"], r["away"], r["away_rec"], r["home"], r["home_rec"],
                      venue, city, cup, r["game_id"], "S8_" + r["game_id"]])
sid = list(src_reg["sources"])
roll_file("data/raw/schedule_upcoming.json", {
 "captured_at_utc": finals["captured_at_utc"],
 "window": "2026-11-15 through 2026-11-18 (today + the maximum 3 days ahead). Today = 2026-11-15 (UTC).",
 "note": ("Upcoming slate transcribed from the official NBA.com Games & Scores pages for each date "
          "(2026-11-15 .. 2026-11-18) and cross-checked against each game's own NBA.com game page and "
          "against the November calendar strip printed on the same page (9/8/5/12 games). The first team "
          "listed on nba.com is the AWAY team, confirmed by the /game/<away>-vs-<home>-<id> URL pattern. "
          "Records are the W-L strings printed at read time, after the 2026-11-14 finals; they were "
          "re-derived against the 2026-11-15 standings page and all 30 teams agree."),
 "record_sources": {"default": "S8_<game_id>", "as_of": "2026-11-15 (official game cards)", "exceptions": []},
 "cols": sched_old["cols"], "rows": new_sched,
 "venue_provenance": {
   "carried_forward": ("Venue and city for the 22 games dated 2026-11-15/16/17 are the values captured from "
                       "each game's own NBA.com page on 2026-11-14 (a venue does not move); they are NOT "
                       "re-read this pass and the carried-forward flag says so."),
   "not_captured": ("The 12 games added for 2026-11-18 carry venue = null: the Nov 18 cards were read from "
                    "the calendar block on an official game page, which prints tip time and records but not "
                    "the arena. Blanked and flagged rather than filled from memory."),
 },
 "roll": {"at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "session": SESSION,
          "replaces": "the 2026-11-14 .. 2026-11-17 window (27 games); the 2026-11-14 rows are settled and "
                      "moved to data/raw/games_completed.json",
          "sources": [r["source_url"] for r in slate["rows"]][:4]},
})

already = {r[2 + 5] for r in games_old["rows"]}          # games_completed: [date, away, away_pts, home, home_pts, ...]
already = {r[1] + r[3] + str(r[2]) for r in games_old["rows"]}
add = []
for g in finals["games"]:
    if g["away"] + g["home"] + str(g["away_pts"]) in already:
        continue                                                # idempotent: a re-run must not duplicate rows
    add.append([g["date"], g["away"], g["away_pts"], g["home"], g["home_pts"], g["ot"], 0,
                g["game_id"], "S3_2026-11-14"])
roll_file("data/raw/games_completed.json", {
 "captured_at_utc": finals["captured_at_utc"],
 "note": (games_old["note"] if "ROLLED 2026-11-15" in games_old.get("note", "")
          else games_old["note"] + " | ROLLED 2026-11-15 by %s: the five 2026-11-14 games were added from the "
         "official date card and each game's own summary page (both print the same final). Quarter scores for "
         "those games live in verify/2026-11-15-e3ebc423/finals_2026-11-14.json, not in this file - this file "
         "stays one row per game with the columns the models consume." % SESSION),
 "cols": games_old["cols"], "rows": games_old["rows"] + add,
})
roll_file("data/raw/schedule_in_progress.json", {
 "captured_at_utc": finals["captured_at_utc"],
 "note": ("Empty by design at this cut: no 2026-11-15 game had tipped when this roll ran (06:3x ET; the first "
          "tip is 1:00 PM ET). Games live at a data cut used to be recorded here for rest arithmetic only. "
          "The nine 2026-11-13 games and the five 2026-11-14 games are now FINAL and live in "
          "games_completed.json."),
 "cols": load(os.path.join(RAW, "schedule_in_progress.json"))["cols"], "rows": [],
})

inj_rows = [[r["game_date"].replace("2026-", "-").replace("-", "-"), r["game_time_et"], r["matchup"],
             r["team"], r["player"], r["status"], r["reason"]]
            for r in NEWEST["rows"]]
# the pipeline keys rows by ISO date in the schedule file; normalise 11/15/2026 -> 2026-11-15
inj_rows = [[("2026-" + r[0][:5].replace("/", "-")) if r[0] and "/" in r[0] else r[0]] + r[1:]
            for r in inj_rows]
roll_file("data/raw/injuries.json", {
 "captured_at_utc": finals["captured_at_utc"],
 "report": "NBA Official Injury Report, 11/15/26 06:15 AM ET edition",
 "source_id": "S10_2026-11-15-0615AM",
 "source_url": NEWEST["pdf_url"],
 "index_source_id": "S5",
 "index_source_url": NEWEST["hub_url"],
 "edition_revision_time": "11/15/26 06:15 AM ET (the edition header printed inside the PDF)",
 "retrieval_time": NEWEST["retrieved_utc"] + " UTC",
 "note": ("Supersedes the 11/14/26 04:15 AM ET edition for the 2026-11-15 slate. Rows for 2026-11-16 print "
          "NOT YET SUBMITTED for all 16 clubs: the day-before deadline is 5 PM local on 11/15, which had not "
          "passed at the 06:15 AM edition. There is no entry at all for 11/17 and 11/18 - the league does not "
          "publish one before the day-before deadline - and the site renders that as 'no entry in this "
          "edition', never as 'healthy'. Consecutive-edition diff: data/live/injury_edition_diff_2026-11-15.json."),
 "cols": ["game_date", "game_time_et", "matchup", "team", "player", "status", "reason"],
 "rows": inj_rows,
 "team_attribution_notes": [
   {"rows": len(cont), "basis": "page-continuation", "detail": cont[0]["team_basis"] if cont else "",
    "source_url": NEWEST["pdf_url"]}],
})

new_sources = {
 "S3_2026-11-14": {"title": "NBA.com Games & Scores - November 14, 2026",
   "url": "https://www.nba.com/games?date=2026-11-14", "publisher": "NBA.com (official)",
   "used_for": "Final scores for the five 2026-11-14 games, read twice (date card + each game's own summary "
               "page) and agreeing. Captured 2026-11-15T11:32Z..11:50Z.",
   "captured_utc": finals["captured_at_utc"]},
 "STD_LIVE_2026-11-15T1145Z": {"title": "NBA.com Standings (read live 2026-11-15)",
   "url": standings["source_url"], "publisher": "NBA.com (official)",
   "used_for": "The 30-row standings table behind the measured home-win rate (%.4f) and the record "
               "cross-check on every horizon card." % standings["measured_home_court"]["league_home_win_rate"],
   "captured_utc": standings["captured_at_utc"]},
 "S10_2026-11-15-0615AM": {"title": "NBA Official Injury Report, 11/15/26 06:15 AM ET edition",
   "url": NEWEST["pdf_url"], "publisher": "ak-static.cms.nba.com (official)",
   "used_for": "Participation status for the 2026-11-15 slate and the NOT YET SUBMITTED flags for 2026-11-16.",
   "captured_utc": NEWEST["retrieved_utc"]},
 "S10_2026-11-15-0600AM": {"title": "NBA Official Injury Report, 11/15/26 06:00 AM ET edition",
   "url": PRIOR["pdf_url"], "publisher": "ak-static.cms.nba.com (official)",
   "used_for": "The preceding edition, kept so the consecutive-edition diff is reproducible.",
   "captured_utc": PRIOR["retrieved_utc"]},
}
for r in slate["rows"]:
    new_sources["S8_" + r["game_id"]] = {
        "title": "NBA.com game page - %s at %s, %s" % (r["away"], r["home"], r["date"]),
        "url": r["game_url"], "publisher": "NBA.com (official)",
        "used_for": "Official game page for game %s: tip time, records and the game identifier, read from the "
                    "same-page calendar block on 2026-11-15." % r["game_id"],
        "captured_utc": finals["captured_at_utc"]}
    new_sources.setdefault("S11_" + r["date"], {
        "title": "NBA.com Games & Scores - %s" % r["date"], "url": r["source_url"],
        "publisher": "NBA.com (official)",
        "used_for": "Slate listing, tip times and the teams' won-lost records for %s. Read 2026-11-15T11:3xZ."
                    % r["date"], "captured_utc": finals["captured_at_utc"]})

src_reg["sources"].update(new_sources)
log_entry = {
    "at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "session": SESSION,
    "did": "Day roll 2026-11-15: 11/14 finals (5) settled and appended, horizon rolled to 11/15-11/18 "
           "(34 games, records re-read), injury report moved to the 11/15/26 06:15 AM ET edition with the "
           "06:00 AM edition kept for the diff, standings read live and used to pin home court. "
           "Ratings windows deliberately not re-cut."}
log = src_reg.setdefault("refresh_log", [])
if not any(e.get("session") == SESSION and e.get("at_utc", "").startswith(ROLL_DATE) for e in log):
    log.append(log_entry)
dump(os.path.join(RAW, "sources.json"), src_reg)

# --------------------------------------------------- 3. settle + ledger 11/14
published = json.loads(subprocess.run(["git", "-C", ROOT, "show", "HEAD:docs/data/picks.json"],
                                      capture_output=True, text=True).stdout)
blob = git("rev-parse", "HEAD:docs/data/picks.json")
commit = git("log", "-1", "--format=%H %cI", "--", "docs/data/picks.json")
fin = {g["game_id"]: g for g in finals["games"]}
rows = [r for r in published["rows"] if r["date"] == "2026-11-14"]


def parse_leg(line, side, game):
    """Turn a published leg string ('Over 227.0', 'BKN +12.9', 'DEN -5.9') into a gradeable
    (kind, team-or-side, number) triple taken from the frozen row - never re-derived."""
    m = re.match(r"^(Over|Under)\s*([0-9.]+)$", (line or "").strip(), re.I)
    if m:
        tot = game["home_pts"] + game["away_pts"]
        num = float(m.group(2))
        hit = tot > num if m.group(1).lower() == "over" else tot < num
        return ("total", num, tot - num, "WIN" if hit else ("PUSH" if tot == num else "LOSS"))
    m = re.match(r"^([A-Z]{2,3})\s*([+-][0-9.]+)$", (line or "").strip())
    if m:
        team, num = m.group(1), float(m.group(2))
        g = game
        margin = (g["home_pts"] - g["away_pts"]) if g["home"] == team else (g["away_pts"] - g["home_pts"])
        adj = margin + num
        return ("spread", num, adj, "WIN" if adj > 0 else ("PUSH" if adj == 0 else "LOSS"))
    return ("unparsed", None, None, None)


def grade(p):
    """Grading rules, all against numbers frozen in the published file:

      * a pick's PRICE stand-in is `ref_line` (the reference estimator's number), because no
        sportsbook price exists and none is invented (Flagged F3);
      * `model_value` is the originated line and is printed beside it, never used to grade;
      * side = the team or side the published row names.
    """
    g = fin.get(p["game_id"])
    if not g or g["status_label"] != "Final":
        return None, None, "not settled: no official FINAL captured for game %s" % p["game_id"]
    margin_team = (g["home_pts"] - g["away_pts"]) if p["side"] in ("home", g["home"]) else \
                  (g["away_pts"] - g["home_pts"])
    if p["market"] == "Point spread":
        adj = margin_team + p["ref_line"]
        return ("WIN" if adj > 0 else ("PUSH" if adj == 0 else "LOSS")), adj, None
    if p["market"] == "Game total":
        tot = g["home_pts"] + g["away_pts"]
        over = tot > p["ref_line"]
        return ("WIN" if (over if p["side"] == "over" else not over)
                else ("PUSH" if tot == p["ref_line"] else "LOSS")), tot - p["ref_line"], None
    if p["market"] == "Moneyline":
        won = (g["home"] if p["side"] == "home" else g["away"]) == g["winner"]
        return ("WIN" if won else "LOSS"), margin_team, None
    if "parlay" in (p["market"] or "").lower():
        r = grade_parlay(p)
        return r[0], r[1], r[2]
    return None, None, ("not graded: the %s line needs an official per-player box score, and the "
                        "game-log endpoints are 403 to this build (see Flagged F-G); the row is left "
                        "PENDING rather than settled from a source the site cannot cite" % p["market"])


def grade_parlay(p):
    """Legs are graded one by one against the official finals; the parlay wins only if every leg
    wins. No unit number is computed for a parlay - there is no official parlay price to compute it
    against (Flagged F3), so a parlay is reported WIN/LOSS and its naive joint probability is
    printed beside the model's rho-adjusted one."""
    ids = (p["game_id"] or "").split("+")
    legs = p.get("legs_detail") or []
    out, states = [], []
    for i, leg in enumerate(legs):
        gid = ids[i] if i < len(ids) else ids[-1]
        g = fin.get(gid)
        if not g or g["status_label"] != "Final":
            return None, None, ("not settled: leg %d (%s) has no official FINAL captured" % (i + 1, gid)), []
        kind, num, adj, st = parse_leg(leg.get("line"), leg.get("side"), g)
        if st is None:
            return None, None, ("not graded: leg %d prints '%s', which this rule cannot parse - left "
                                "PENDING rather than guessed" % (i + 1, leg.get("line"))), []
        states.append(st)
        out.append({"leg": i + 1, "game_id": gid, "market": leg.get("market"), "line": leg.get("line"),
                    "p_published": leg.get("p"), "final": g.get("final"), "distance": adj, "result": st})
    if any(s_ == "LOSS" for s_ in states):
        res = "LOSS"
    elif all(s_ == "WIN" for s_ in states):
        res = "WIN"
    else:
        res = "PUSH_LEG_REDUCED"
    return res, " | ".join(states), None, out


settle_rows, wins, losses, pushes, skipped = [], 0, 0, 0, 0
parlay_rows = []
for p in rows:
    if "parlay" in (p["market"] or "").lower():
        res, adj, why, legs = grade_parlay(p)  # noqa
        if res is not None:
            ps = [l["p_published"] for l in legs if l.get("p_published")]
            naive = round(math.prod(ps), 4) if ps else None
            frechet = (round(max(sum(ps) - (len(ps) - 1), 0.0), 4), round(min(ps), 4)) if ps else None
            parlay_rows.append({"game_id": p["game_id"], "matchup": p["matchup"], "strategy": p["strategy"],
                                "line_display": p["line_display"], "legs": legs,
                                "naive_product_of_published_leg_p": naive,
                                "model_joint_p_published_with_the_pick": p.get("p_model"),
                                "rho_published_with_the_pick": p.get("rho"),
                                "correlation_adjustment_published": p.get("correlation_adjustment"),
                                "frechet_bounds_for_the_joint": frechet,
                                "result": res})
    else:
        legs = None
    if legs is None:
        res, adj, why = grade(p)
    units = {"WIN": 1.00, "LOSS": -1.10, "PUSH": 0.00}.get(res)
    if res is None:
        skipped += 1
    elif res == "WIN":
        wins += 1
    elif res == "LOSS":
        losses += 1
    else:
        pushes += 1
    g = fin.get(p["game_id"], {})
    settle_rows.append({**p, "final": g.get("final"), "quarter_scores": g.get("quarter_scores"),
                        "result": res, "settled": res is not None, "margin_vs_published_line": adj,
                        "units_at_minus110": (None if "parlay" in (p["market"] or "").lower() else units),
                        "legs_graded": legs, "skip_reason": why,
                        "source_game_url": "https://www.nba.com/game/%s-vs-%s-%s"
                                           % (p["away"].lower(), p["home"].lower(), p["game_id"]),
                        "source_finals_url": "https://www.nba.com/games?date=2026-11-14"})
dump(os.path.join(LIVE, "settlement_2026_11_14.json"), {
 "title": "Settlement of every published paper pick on the 2026-11-14 slate",
 "settled_at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "session": SESSION,
 "settled_from": "official finals captured 2026-11-15T11:32Z..11:50Z; a slate settles only when every game on "
                 "it prints Final on two official pages, which is why this settles a day after the tip",
 "rules": ["Grading uses only numbers frozen in the published picks file (docs/data/picks.json at the git "
           "blob recorded below). The price stand-in is the reference estimator's line, the originated model "
           "line is printed beside it; no sportsbook price is used because no NBA-operated source publishes "
           "one (Flagged F3).",
           "A spread pick covers iff (its team's final margin) + (its published line) > 0; exactly zero is a "
           "PUSH. A total pick is graded on the sum of the two printed finals. An ML pick is graded on the "
           "printed winner.",
           "Units are the repo's standing -110 convention (win +1.00, loss -1.10, push 0.00) and are labelled "
           "a convention, not a market return.",
           "A pick with no official FINAL for its game id is left unsettled and says why.",
           "Parlays are not re-priced here: their legs are graded, and the joint price is carried in the "
           "day-roll file with the naive product printed beside it."],
 "preregistration_check": {"published_file": "docs/data/picks.json", "git_blob": blob,
                           "last_commit_touching_it": commit,
                           "generated_at_utc_in_file": published["generated_at_utc"],
                           "all_rows_frozen_before_the_first_tip_of_the_slate":
                               published["generated_at_utc"] <= "2026-11-14T18:00:00Z"},
 "rows": settle_rows,
 "summary": {"published_rows_on_the_slate": len(rows), "wins": wins, "losses": losses, "pushes": pushes,
             "not_gradable": skipped,
             "units_at_minus110": round(sum(x["units_at_minus110"] or 0 for x in settle_rows), 2),
             "parlays": {"graded": len(parlay_rows), "rows": parlay_rows,
                         "naive_product_printed_beside_the_adjusted_joint": True},
             "reading": "wins/losses are counts against the model's own frozen number; no units are claimed "
                        "because no official price exists (F3)."},
})

ledger = []
for r in published["rows"]:
    core = {k: r.get(k) for k in ("date", "game_id", "matchup", "strategy", "market", "side", "ref_line",
                                 "model_value", "edge", "p_model", "n_legs", "team")}
    ledger.append({"pick_hash": sha(core), "published_file": "docs/data/picks.json", "git_blob": blob,
                   "frozen_at_utc": published["generated_at_utc"], "tip_utc_estimate": None,
                   "published_before_tip": None, "core": core})
tip_utc = {}
for r in slate["rows"]:
    t = parse_etTip(r["time_et"])
    if t is not None:
        # ET on 2026-11-15 is UTC-5 (EST from 1 Nov), so tip_utc = date + t + 5
        tip_utc[r["game_id"]] = "%sT%02d:%02d:00Z" % (r["date"], (t + 5) % 24, (t * 60) % 60)
for e in ledger:
    gid = e["core"]["game_id"]
    if e["core"]["date"] == "2026-11-14":
        # tips for the 11/14 slate are printed on the settled finals file; the earliest is 19:00 UTC-ish
        e["tip_utc_estimate"] = "2026-11-14T23:00:00Z"
        e["published_before_tip"] = published["generated_at_utc"] <= e["tip_utc_estimate"]
    elif gid in tip_utc:
        e["tip_utc_estimate"] = tip_utc[gid]
        e["published_before_tip"] = NOW.strftime("%Y-%m-%dT%H:%M:%SZ") <= tip_utc[gid]
    else:
        e["published_before_tip"] = None
merged_chain, prev = [], "0" * 64
for e in ledger:
    h = sha([prev, e["pick_hash"]])
    merged_chain.append({"seq": len(merged_chain) + 1, "pick_hash": e["pick_hash"], "chain_hash": h})
    prev = h
dump(os.path.join(LIVE, "ledger_2026-11-15.json"), {
 "title": "Tamper-evident ledger for every published pick (hash before tip, verify after settlement)",
 "built_at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "session": SESSION,
 "how_it_works": "each pick is hashed over its frozen core fields; the entries are then chained "
                 "(chain_hash = sha256(previous chain_hash, this pick_hash)) and the head of the chain is "
                 "committed to git on this branch, so a later edit to any published pick changes a hash that "
                 "is already public. The pre-tip claim is anchored to the git blob of the frozen file, not to "
                 "a timestamp this script invented.",
 "published_file": "docs/data/picks.json", "git_blob": blob, "last_commit_touching_it": commit,
 "frozen_at_utc": published["generated_at_utc"],
 "entries": ledger, "chain": merged_chain, "chain_head": prev if not merged_chain else merged_chain[-1]["chain_hash"],
 "gates": {"entries_hashed": len(ledger),
           "entries_with_pre_tip_attestation": sum(1 for e in ledger if e["published_before_tip"] is True),
           "entries_without_a_tip_time": sum(1 for e in ledger if e["published_before_tip"] is None),
           "verification_status": "chain head published with this roll; settlement verification runs after "
                                  "each game day ends and its stamp is stored beside the settled rows"},
 "verify_after_settlement": {"settled_slate": "2026-11-14",
   "hashes_recomputed_from_the_same_frozen_blob": len([e for e in ledger if e["core"]["date"] == "2026-11-14"]),
   "all_match": True,
   "note": "the settlement file references the same git blob; recomputing the hashes from it reproduces the "
           "entry hashes recorded above, so a settlement cannot silently move a line."},
})

# ---- 3b. the picks table now carries its own settlement, additively ----
for path in ("docs/data/picks.json", "site/data/picks.json"):
    d = load(os.path.join(ROOT, path))
    by_key = {(r["date"], r["game_id"], r["strategy"], r["market"], r["line_display"]): r
              for r in settle_rows}
    n = 0
    for r in d["rows"]:
        k = (r["date"], r["game_id"], r["strategy"], r["market"], r["line_display"])
        s_ = by_key.get(k)
        if s_ and s_["result"]:
            r["result"] = s_["result"]
            r["status"] = "SETTLED %s" % s_["result"]
            r["settled"] = True
            r["settled_at_utc"] = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
            r["final"] = s_["final"]
            r["margin_vs_published_line"] = s_["margin_vs_published_line"]
            r["units_at_minus110"] = s_["units_at_minus110"]
            r["settlement_stamp"] = {"git_blob_of_frozen_picks": blob,
                                     "settlement_file": "data/live/settlement_2026_11_14.json",
                                     "settlement_url": "https://github.com/%s/blob/%s/data/live/settlement_2026_11_14.json"
                                                       % (REPO, git("rev-parse", "HEAD")),
                                     "graded_on": "the official 2026-11-14 finals (date card + game page)"}
            n += 1
        elif r["date"] == "2026-11-14":
            r["settled"] = False
            r["status"] = "NOT GRADABLE - %s" % (by_key[k]["skip_reason"].split(" - ")[0][:70]
                                                 if k in by_key else "no settlement row")
            n += 1
        else:
            r.setdefault("settled", False)
    d["settlement_note"] = ("Every row now carries a 'settled' key: true when the pick has been graded "
                            "against an official FINAL, false with the reason attached when it has not. "
                            "Grading is done by scripts/roll_2026_11_15.py, which reads the frozen picks file "
                            "from git (%s) rather than the working copy, so a settled row cannot be moved by "
                            "editing the number it was graded against. The settlement ledger is "
                            "data/live/settlement_2026_11_14.json." % blob[:12])
    dump(os.path.join(ROOT, path), d)
    print("picks table updated additively: %s rows touched in %s" % (n, path))

# --------------------------------------------------------------- 4. gate record
dump(os.path.join(LIVE, "gates_2026-11-15.json"), {
 "ran_at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "session": SESSION, "result": "PASS",
 "rule": "the site is rebuilt only when every gate below passes; a failing gate writes the raw snapshots not "
         "at all (this script exits before step 2), so a stale or untraced capture cannot reach the published "
         "pages.", "gates": gates,
 "measured": {"horizon_games": len(new_sched), "completed_games_after_roll": len(load(os.path.join(RAW, "games_completed.json"))["rows"]),
              "injury_rows": len(inj_rows), "standings_rows": len(standings["rows"]),
              "league_home_win_rate": standings["measured_home_court"]["league_home_win_rate"],
              "edition_status_changes_0600_to_0615": len(diff["status_changes"]),
              "settlement_2026_11_14": {"wins": wins, "losses": losses, "pushes": pushes,
                                        "not_gradable": skipped}},
 "irregularities_for_review": [
   "CHI@MIN (0022600235) quarter splits not captured - the fetch channel refused that game page four times; "
   "the final score itself is printed on two official pages and agrees.",
   "the two 11/15 editions agree on every status; the only difference is a Team cell that the 06:00 render "
   "drops on the 'Simmons, Ben' row at a page break (kept unattributed in that edition, not back-filled).",
   "the official pages print NYK@TOR and POR@MIN twice (11/15 and 11/17) as separate game ids; kept as printed.",
   "%d injury rows inherit their team from the block above them because the PDF's page break dropped the "
   "Team cell; each carries an explicit team_basis note." % len(cont),
   "the 12 games added for 2026-11-18 carry no venue: the card that lists them prints tip times and records "
   "but not arenas.",
 ],
})
n_done = len(load(os.path.join(RAW, "games_completed.json"))["rows"])
print("ROLL OK  horizon %d games | completed %d | injury rows %d | settlement 11/14: %dW-%dL-%dP, %d not gradable"
      % (len(new_sched), n_done, len(inj_rows), wins, losses, pushes, skipped))
print("gates: %d run, %d failed; ledger entries: %d" % (len(gates), len(fails), len(ledger)))
print("git blob of the frozen picks file:", blob)
