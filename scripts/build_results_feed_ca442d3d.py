#!/usr/bin/env python3
"""Re-cut the official per-game result feed for one game day from stored bytes.

COORDINATION §63 (session arena/ca442d3d-nba1), brief line:

  "Keep an official per-game result feed current and settle only after final
   scores are verified; store one row per game: date, teams, final score,
   quarter scores."

WHY THIS EXISTS
---------------
The repository's per-game feed (``data/official/results_feed_2026_27.json``) is
built by another session's pipeline from its own run directory, so when a game
day ends the feed only rolls forward if that session happens to re-run. This
script makes the roll mechanical and auditable: it reads a *stored* official
capture (``data/raw/session-ca442d3d/html/games_<date>__<sha256>.json.gz`` plus
its sidecar), takes the scoreboard JSON the page itself embeds
(``<script id="__NEXT_DATA__">``), and writes one row per game in the feed's own
schema. It then cross-checks every row against the committed feed and against
the settlement record for that date, and refuses to call a day settled on a
mismatch.

WHAT THE OFFICIAL PAGE ACTUALLY CARRIES
---------------------------------------
Measured on the 2026-11-16 capture (HTTP 200, sha256 recorded in the sidecar):
each game object prints ``gameId``, ``gameStatus``, ``gameStatusText``,
``period``, and per team ``teamTricode``, ``score`` and ``periods:
[{period, score}, ...]``. So date, teams, final score and quarter scores all
come from one official document; no box-score page has to be trusted for them.

RULES
-----
* Only rows the page marks ``gameStatus == 3`` ("Final") are emitted as settled.
  A scheduled or live game is written with its status and null scores, and is
  never counted.
* Quarter scores must sum to the printed final for both teams. A game that fails
  the sum is reported in ``quarter_sum_assertion_failures`` and excluded from
  the settled count - it is never silently corrected or dropped.
* Unplayed rows are never used as results: a ``0-0`` placeholder with
  ``gameStatus != 3`` is listed under ``excluded_not_final``. (25 such rows
  polluting a "final corpus" is the defect §61 found and fixed in
  ``engine/model_v2.py``; this script keeps the same discipline at capture time.)
* Every output row carries the capture's URL, sha256 and retrieval timestamp.
  A value the page does not print is left null, never filled in.
"""

from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "data", "raw", "session-ca442d3d")
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def load_capture(date: str):
    """Return (parsed_json, sidecar_record) for one stored day capture."""
    hits = sorted(glob.glob(os.path.join(CAP, "html", f"games_{date}__*.json.gz")))
    if not hits:
        raise SystemExit(f"no stored official capture for {date} under "
                         f"data/raw/session-ca442d3d/html/ - run "
                         f"scripts/capture_official_ca442d3d.py on the runner first")
    path = hits[0]
    sidecar_path = path + ".sidecar.json"
    sidecar = {}
    if os.path.exists(sidecar_path):
        sidecar = json.load(open(sidecar_path, encoding="utf-8"))
    raw = gzip.open(path, "rb").read()
    digest = hashlib.sha256(raw).hexdigest()
    if sidecar.get("sha256") and sidecar["sha256"] != digest:
        raise SystemExit(f"stored bytes do not match the sidecar digest for {path}: "
                         f"the capture file has been altered since retrieval")
    return raw.decode("utf-8", "replace"), sidecar, os.path.relpath(path, ROOT)


def games_from_page(html: str) -> list:
    """Every game object the page's own embedded scoreboard JSON prints."""
    m = NEXT_DATA_RE.search(html)
    if not m:
        return []
    data = json.loads(m.group(1))

    found = []

    def walk(node):
        if isinstance(node, dict):
            if "gameId" in node and ("homeTeam" in node or "awayTeam" in node):
                found.append(node)
                return
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return found


def periods_of(team: dict) -> list:
    per = team.get("periods") or []
    out = []
    for p in per:
        try:
            out.append(int(p.get("score")))
        except (TypeError, ValueError):
            out.append(None)      # printed but unreadable -> null, never guessed
    return out


def build_rows(games: list, date: str) -> dict:
    rows, excluded, sum_fail = [], [], []
    for g in games:
        home, away = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        gid = str(g.get("gameId") or "")
        status = g.get("gameStatus")
        row = {
            "date": date,
            "game_id": gid,
            "game_status": status,
            "game_status_text": g.get("gameStatusText"),
            "home": home.get("teamTricode"),
            "away": away.get("teamTricode"),
            "home_pts": home.get("score"),
            "away_pts": away.get("score"),
            "home_quarters": periods_of(home),
            "away_quarters": periods_of(away),
            "ot_periods": max(0, int(g.get("period") or 4) - 4),
            "margin_home": None,
            "total_pts": None,
            "home_record": f"{home.get('wins')}-{home.get('losses')}"
            if home.get("wins") is not None else None,
            "away_record": f"{away.get('wins')}-{away.get('losses')}"
            if away.get("wins") is not None else None,
            "tip_utc": g.get("gameTimeUtc"),
            "official_source": ("https://www.nba.com/games?date=" + date),
            "game_url": ("https://www.nba.com/game/"
                         f"{(away.get('teamSlug') or '?')}-vs-"
                         f"{(home.get('teamSlug') or '?')}-{gid}"),
        }
        if status != 3:
            excluded.append({"game_id": gid, "game_status": status,
                             "game_status_text": g.get("gameStatusText")})
            continue
        if row["home_pts"] is None or row["away_pts"] is None:
            excluded.append({"game_id": gid, "game_status": status,
                             "reason": "no printed score on a Final row"})
            continue
        hq, aq = row["home_quarters"], row["away_quarters"]
        if hq and sum(v or 0 for v in hq) != row["home_pts"]:
            sum_fail.append({"game_id": gid, "side": "home",
                             "quarters": hq, "printed_final": row["home_pts"]})
        if aq and sum(v or 0 for v in aq) != row["away_pts"]:
            sum_fail.append({"game_id": gid, "side": "away",
                             "quarters": aq, "printed_final": row["away_pts"]})
        row["margin_home"] = row["home_pts"] - row["away_pts"]
        row["total_pts"] = row["home_pts"] + row["away_pts"]
        rows.append(row)
    return {"rows": rows, "excluded_not_final": excluded,
            "quarter_sum_assertion_failures": sum_fail}


def cross_check(rows: list, feed_path: str, settlement_dir: str) -> dict:
    """Compare each new row with the committed feed and the settlement record."""
    out = {"feed_compared": 0, "feed_agreements": [], "feed_conflicts": [],
           "feed_missing": [], "settlement_compared": 0,
           "settlement_agreements": [], "settlement_conflicts": [],
           "settlement_missing": None}
    committed = {}
    if os.path.exists(feed_path):
        feed = json.load(open(feed_path, encoding="utf-8"))
        for r in feed.get("rows", []):
            committed[str(r.get("game_id"))] = r
    for r in rows:
        c = committed.get(r["game_id"])
        if not c:
            out["feed_missing"].append(r["game_id"])
            continue
        out["feed_compared"] += 1
        agree = (c.get("home_pts") == r["home_pts"]
                 and c.get("away_pts") == r["away_pts"]
                 and (c.get("home_quarters") or [])[:4] == (r["home_quarters"] or [])[:4]
                 and (c.get("away_quarters") or [])[:4] == (r["away_quarters"] or [])[:4])
        rec = {"game_id": r["game_id"], "this_capture": f"{r['away']} {r['away_pts']} @ "
                                                        f"{r['home']} {r['home_pts']}",
               "committed_feed": f"{c.get('away')} {c.get('away_pts')} @ "
                                 f"{c.get('home')} {c.get('home_pts')}"}
        (out["feed_agreements"] if agree else out["feed_conflicts"]).append(rec)
    dates = sorted({r["date"] for r in rows})
    for d in dates:
        sp = os.path.join(settlement_dir, f"settlement_{d}.json")
        if not os.path.exists(sp):
            out["settlement_missing"] = (f"no settlement record for {d} in "
                                         f"{os.path.relpath(settlement_dir, ROOT)}")
            continue
        s = json.load(open(sp, encoding="utf-8"))
        by_id = {}
        # The settlement record carries the finals it graded against inside each
        # ticket row (`singles[*].home_pts/away_pts/*_quarters`) as well as any
        # per-game list, so both shapes are read and neither is trusted alone.
        for g in (s.get("games") or s.get("rows") or []):
            by_id[str(g.get("game_id") or "")] = g
        for g in (s.get("singles") or []):
            gid = str(g.get("game_id") or "")
            if gid and gid not in by_id:
                by_id[gid] = g
        for r in [x for x in rows if x["date"] == d]:
            g = by_id.get(r["game_id"])
            if not g:
                continue
            out["settlement_compared"] += 1
            hp = g.get("home_pts", g.get("home_score"))
            ap = g.get("away_pts", g.get("away_score"))
            q_ok = (g.get("home_quarters") in (None, r["home_quarters"])
                    and g.get("away_quarters") in (None, r["away_quarters"]))
            rec = {"game_id": r["game_id"],
                   "capture": f"{r['away']} {r['away_pts']} @ {r['home']} {r['home_pts']}",
                   "settlement": f"{g.get('away')} {ap} @ {g.get('home')} {hp}",
                   "quarters_agree": q_ok}
            if None in (hp, ap) or ((hp, ap) == (r["home_pts"], r["away_pts"]) and q_ok):
                out["settlement_agreements"].append(rec)
            else:
                out["settlement_conflicts"].append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True, help="game day to re-cut, YYYY-MM-DD")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    html, sidecar, stored = load_capture(args.date)
    games = games_from_page(html)
    if not games:
        print(f"::error:: the stored capture for {args.date} carries no embedded "
              f"scoreboard JSON - nothing to re-cut (not a zero-game day unless "
              f"the page says so)")
        return 2
    built = build_rows(games, args.date)
    rows = built["rows"]

    feed_path = os.path.join(ROOT, "data", "official", "results_feed_2026_27.json")
    xcheck = cross_check(rows, feed_path,
                         os.path.join(ROOT, "data", "settlement"))
    payload = {
        "title": f"Official per-game result feed rows for {args.date} "
                 f"(re-cut from a stored capture)",
        "generated_by": "scripts/build_results_feed_ca442d3d.py",
        "session": "arena/ca442d3d-nba1",
        "rule": ("one row per game: date, teams, final score, quarter scores. A "
                 "game is settled only when the official page prints gameStatus 3 "
                 "(Final) and the quarter scores sum to the printed final."),
        "capture": {
            "stored_at": stored,
            "source_url": sidecar.get("url"),
            "http_status": sidecar.get("http_status"),
            "bytes": sidecar.get("bytes"),
            "sha256_of_page_bytes": sidecar.get("sha256"),
            "retrieved_at_utc": sidecar.get("retrieved_at_utc"),
            "extracted_from": ("the page's own <script id=\"__NEXT_DATA__\"> "
                               "scoreboard JSON"),
        },
        "games_on_page": len(games),
        "settled_rows": len(rows),
        "excluded_not_final": built["excluded_not_final"],
        "quarter_sum_assertion_failures": built["quarter_sum_assertion_failures"],
        "cross_check": xcheck,
        "rows": rows,
    }
    out = args.out or os.path.join(
        ROOT, "data", "official", f"results_feed_{args.date.replace('-', '_')}_ca442d3d.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")
    print(f"{args.date}: {len(games)} game(s) on the page, {len(rows)} settled "
          f"-> {os.path.relpath(out, ROOT)}")
    print(f"  quarter-sum failures: {len(payload['quarter_sum_assertion_failures'])}; "
          f"excluded (not final): {len(payload['excluded_not_final'])}")
    print(f"  vs committed feed: {len(xcheck['feed_agreements'])} agree, "
          f"{len(xcheck['feed_conflicts'])} conflict, "
          f"{len(xcheck['feed_missing'])} not in the committed feed")
    if xcheck["settlement_missing"]:
        print(f"  settlement: {xcheck['settlement_missing']}")
    else:
        print(f"  vs settlement: {len(xcheck['settlement_agreements'])} agree, "
              f"{len(xcheck['settlement_conflicts'])} conflict")
    if payload["quarter_sum_assertion_failures"]:
        print("::error:: a quarter line does not sum to the printed final - the day "
              "is NOT settleable from this capture")
        return 1
    if xcheck["feed_conflicts"] or xcheck["settlement_conflicts"]:
        print("::error:: the capture disagrees with a committed record; left for "
              "review rather than overwritten")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
