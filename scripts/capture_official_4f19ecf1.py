#!/usr/bin/env python3
"""capture_official_4f19ecf1.py — runner-side byte capture for session
``arena/4f19ecf1-nba1`` (COORDINATION.md §68, tasks G02/G03).

What this script captures, and why it is this narrow
----------------------------------------------------
Two currency gaps left by the 2026-11-19 day-roll (PR #172) and unclaimed by any
open session at claim time (2026-11-19 05:5x UTC):

1. **Official gamebook PDFs for the 17 finished games of 2026-11-17 (5) and
   2026-11-18 (12)** — ``https://statsdmz.nba.com/pdfs/<yyyymmdd>/<yyyymmdd>_<AWAY><HOME>_book.pdf``.
   These are the only official source that carries minutes, points, rebounds and
   assists for every player in a game plus the score-by-period line (register
   R21), and they are the evidence the SGP prop tickets left ``UNSETTLED`` by
   ``scripts/settle_slate.py`` are graded from.

2. **Every official injury-report edition for 2026-11-17 (after the 11:30 AM ET
   archive point) through 2026-11-19**, byte-exact and content-addressed into
   the canonical ``data/raw/injury_pdfs/`` archive, so the consecutive-edition
   diff chain (R04) can be continued and the newest edition promoted. This is
   the first capture through the index-driven ``engine/fetch_official.py``
   path since PR #170 closed the F-CA-07 trigger gap.

Design rules (same as ``scripts/capture_official_ca442d3d.py``, which this
script reuses by import and which the board reviewed):

  * only the four official NBA hosts are contacted (``www.nba.com``,
    ``official.nba.com``, ``ak-static.cms.nba.com``, ``statsdmz.nba.com``);
    any other host raises;
  * every artifact is stored content-addressed with a provenance sidecar
    (bytes, sha256, retrieval time, source URL). Nothing parsed is published
    here: parsing happens locally on the stored bytes so it can be re-run;
  * a failed fetch is recorded as a failure, never as a missing source;
  * the bot commit that lands these bytes carries ``[skip ci]``.

Outputs
-------
  data/raw/session-4f19ecf1/gamebooks/<date>/<date>_<CODE>__<sha>.bin (+ sidecar)
  data/raw/session-4f19ecf1/games_<date>.json          (official scoreboard cards)
  data/raw/session-4f19ecf1/capture_manifest.json
  data/raw/injury_pdfs/<edition>__<sha>.pdf (+ .json)  (canonical archive, append-only)
  data/raw/_capture_injury_probe.json                  (canonical probe run record,
                                                       merged across capture passes)

Usage
-----
  python3 scripts/capture_official_4f19ecf1.py
  python3 scripts/capture_official_4f19ecf1.py --dates 2026-11-17,2026-11-18
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_DIR = os.path.join(ROOT, "data", "raw", "session-4f19ecf1")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "engine"))

import capture_official_ca442d3d as base  # noqa: E402  (host allowlist + store)

# The session store replaces ca442d3d's; every store()/fetch_recorded() call
# below therefore writes under data/raw/session-4f19ecf1/ and nothing else.
base.OUT_ROOT = SESSION_DIR

import fetch_official as fo  # noqa: E402  (index-driven injury capture, engine)


INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
INJURY_DATES = ("2026-11-17", "2026-11-18", "2026-11-19")
MAX_INJURY_PASSES = 12   # 10 new editions per pass (engine cap), 12 passes bound


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def capture_gamebooks(dates, manifest):
    for d in dates:
        url = f"https://www.nba.com/games?date={d}"
        rec = base.fetch_recorded(url, "html", f"games_{d}", compress=True)
        html = (rec.pop("_raw", b"") or b"").decode("utf-8", "replace")
        day = base.parse_scoreboard(html, d)
        day["source_url"] = url
        day["page_sha256"] = rec.get("sha256")
        day["page_retrieved_at_utc"] = rec.get("retrieved_at_utc")
        day["http_status"] = rec.get("http_status")
        if rec.get("error"):
            manifest["failures"].append({"url": url, "error": rec["error"]})
        with open(os.path.join(SESSION_DIR, f"games_{d}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(day, fh, indent=1)
            fh.write("\n")
        manifest["days"].append({"date": d, "games": len(day["games"]),
                                 "marked_final": day["final_count"],
                                 "http_status": rec.get("http_status"),
                                 "page_stored": rec.get("stored")})
        log(f"games?date={d}: {len(day['games'])} game cards, "
            f"{day['final_count']} marked Final")

        ymd = d.replace("-", "")
        for g in day["games"]:
            if not g["marked_final_on_page"]:
                manifest["gamebooks_skipped_not_final"].append(
                    {"date": d, "game_id": g["game_id"],
                     "matchup": f"{g['away']}@{g['home']}"})
                continue
            code = f"{g['away']}{g['home']}"
            gb_url = (f"https://statsdmz.nba.com/pdfs/{ymd}/"
                      f"{ymd}_{code}_book.pdf")
            grec = base.fetch_recorded(gb_url, f"gamebooks/{d}", f"{d}_{code}",
                                       expect="pdf")
            grec.pop("_raw", None)
            grec["game_id"] = g["game_id"]
            grec["away"] = g["away"]
            grec["home"] = g["home"]
            grec["matchup"] = f"{g['away']}@{g['home']}"
            grec["source_page"] = g["url"]
            manifest["gamebooks"].append(grec)
            if grec.get("error"):
                manifest["failures"].append({"url": gb_url,
                                             "error": grec["error"],
                                             "game_id": g["game_id"]})
            log(f"  gamebook {d} {code}: "
                f"{grec.get('http_status')} {grec.get('bytes', 0)} bytes")
            time.sleep(1.2)


def capture_injury_editions(manifest):
    """Archive every unarchived edition of 2026-11-17..19 listed on the index.

    engine/fetch_official.capture_injury is called directly so the canonical
    archive naming, sidecar schema and probe record stay exactly the ones the
    scheduled refresh writes (PR #170's promotion path reads those). The
    engine caps 10 new editions per call; this driver loops until the index is
    exhausted for the three dates or the pass bound is hit, then writes one
    MERGED probe record (newest edition first) so promote_injuries sees the
    true newest archived edition rather than the last pass's.
    """
    raw = fo.get(INJURY_INDEX_URL, timeout=45)
    text = fo.as_text(raw)
    editions = fo.parse_injury_index(text)
    # Edition filenames keep hyphens in the date part:
    # Injury-Report_2026-11-17_11_30AM.pdf (pinned by engine/fetch_official's
    # name_re and by every archived file in data/raw/injury_pdfs/).
    wanted = [e for e in editions
              if any(f"Injury-Report_{d}_" in e for d in INJURY_DATES)]
    log(f"injury index: {len(editions)} editions listed, "
        f"{len(wanted)} for {', '.join(INJURY_DATES)}")
    manifest["injury_index"] = {
        "url": INJURY_INDEX_URL,
        "editions_listed": len(editions),
        "editions_wanted_dates": len(wanted),
        "newest_listed": editions[0] if editions else None,
    }

    all_results = []
    changed, failed = [], []
    for p in range(1, MAX_INJURY_PASSES + 1):
        results = fo.capture_injury(now_utc(), changed, failed, editions)
        fresh = [r for r in results if r.get("artifact_path")]
        all_results.extend(results)
        log(f"injury pass {p}: {len(results)} attempted, "
            f"{len(fresh)} stored (cap 10 new per pass)")
        if len(results) < 10:
            break
        time.sleep(2.0)

    # Merge with the archive so the probe record's results[0] is the newest
    # edition actually stored (promote_injuries takes results[0]).
    def ed_key(name):
        import re
        m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", name)
        if not m:
            return (name, 0)
        y, mo, d, hh, mm, ampm = m.groups()
        return (f"{y}-{mo}-{d}",
                (int(hh) % 12 + (12 if ampm == "PM" else 0)) * 100 + int(mm))

    seen, merged = set(), []
    for r in sorted(all_results, key=lambda r: ed_key(r["edition"]), reverse=True):
        if r["edition"] in seen:
            continue
        seen.add(r["edition"])
        merged.append(r)

    archived = 0
    if os.path.isdir(fo.INJURY_PDF_DIR):
        archived = sum(1 for fn in os.listdir(fo.INJURY_PDF_DIR) if fn.endswith(".pdf"))
    probe = {
        "captured_at_utc": now_utc(),
        "results": merged,
        "editions_listed_on_index": len(editions),
        "newest_listed": editions[0] if editions else None,
        "editions_already_archived": archived,
        "method": ("index-driven (engine/fetch_official.capture_injury), "
                   "looped past the per-pass cap by session driver "
                   "arena/4f19ecf1-nba1 so the 2026-11-17..19 series is "
                   "archived in full; records merged newest-edition-first"),
        "note": ("HTTP status only. 403 from ak-static.cms.nba.com is recorded "
                 "as unavailable at capture time, never as proof of absence."),
    }
    with open(os.path.join(fo.RAW, "_capture_injury_probe.json"), "w",
              encoding="utf-8") as fh:
        json.dump(probe, fh, indent=1)
        fh.write("\n")

    stored = [r for r in merged if r.get("artifact_path") and r.get("http_status") == 200]
    manifest["injury_editions"] = {
        "attempted": len(merged),
        "stored_ok": len(stored),
        "non_200": [{"edition": r["edition"], "http_status": r.get("http_status")}
                    for r in merged if r.get("http_status") != 200],
        "newest_stored": stored[0]["edition"] if stored else None,
        "changed": changed,
        "failed": failed,
    }
    log(f"injury archive: {len(stored)} editions stored OK, "
        f"newest {stored[0]['edition'] if stored else None}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dates", default="2026-11-17,2026-11-18")
    ap.add_argument("--skip-gamebooks", action="store_true")
    ap.add_argument("--skip-injury", action="store_true")
    args = ap.parse_args()

    os.makedirs(SESSION_DIR, exist_ok=True)
    manifest = {
        "session": "arena/4f19ecf1-nba1",
        "coordination": "COORDINATION.md §68 (G02/G03)",
        "run_at_utc": now_utc(),
        "hosts_allowed": sorted(base.ALLOWED_HOSTS),
        "rule": ("Bytes as received, content-addressed with provenance sidecars. "
                 "This script publishes no parsed value: parsing happens locally "
                 "on the stored bytes so it can be re-run and audited."),
        "dates": [d.strip() for d in args.dates.split(",") if d.strip()],
        "days": [], "gamebooks": [], "gamebooks_skipped_not_final": [],
        "injury_index": None, "injury_editions": None,
        "failures": [],
    }

    if not args.skip_gamebooks:
        capture_gamebooks(manifest["dates"], manifest)
    if not args.skip_injury:
        try:
            capture_injury_editions(manifest)
        except Exception as exc:  # noqa: BLE001 — record, never mask
            manifest["failures"].append({"stage": "injury",
                                         "error": f"{type(exc).__name__}: {exc}"})
            log(f"injury stage FAILED: {type(exc).__name__}: {exc}")

    with open(os.path.join(SESSION_DIR, "capture_manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    log(f"done: {len(manifest['gamebooks'])} gamebook fetches, "
        f"{len(manifest['failures'])} failure(s) recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
