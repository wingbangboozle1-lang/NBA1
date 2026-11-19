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

# Measured defect in the shared template (this session, 2026-11-19T06:0xZ, on
# the captured 11/17 scoreboard bytes): the official cards print the status as
# uppercase "FINAL" and base.FINAL_RE ("\bFinal(?:/OT\d*)?\b") is case-
# sensitive, so parse_scoreboard reported 0 of 5 (11/17) and 0 of 12 (11/18)
# games as Final while the same cards print "Knicks - FINAL Raptors -".
# The template script is left unchanged (it is the closed claim's record);
# this session's capture matches case-insensitively. Logged as F-4F19-01.
import re as _re  # noqa: E402
base.FINAL_RE = _re.compile(r"\bFinal(?:/OT\d*)?\b", _re.I)

import fetch_official as fo  # noqa: E402  (index-driven injury capture, engine)


INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
INJURY_DATES = ("2026-11-17", "2026-11-18", "2026-11-19")
MAX_INJURY_PASSES = 12   # 10 new editions per pass (engine cap), 12 passes bound


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def _load_day(d):
    """Reuse the captured scoreboard day when the bytes are already stored."""
    path = os.path.join(SESSION_DIR, f"games_{d}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def capture_gamebooks(dates, manifest):
    for d in dates:
        url = f"https://www.nba.com/games?date={d}"
        day = _load_day(d)   # re-arm fast path: the day's bytes are already stored
        if day is not None:
            log(f"games?date={d}: reused captured day "
                f"({len(day['games'])} game cards, {day['final_count']} marked Final)")
        else:
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
            log(f"games?date={d}: {len(day['games'])} game cards, "
                f"{day['final_count']} marked Final")
        manifest["days"].append({"date": d, "games": len(day["games"]),
                                 "marked_final": day["final_count"],
                                 "http_status": day.get("http_status"),
                                 "page_stored": day.get("page_stored")})

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
            # Idempotence: a re-armed run must not re-fetch what the content-
            # addressed store already holds (the runner is reclaimed every few
            # minutes; batches resume from disk).
            prior_rec = None
            gb_dir = os.path.join(SESSION_DIR, "gamebooks", d)
            if os.path.isdir(gb_dir):
                for fn in sorted(os.listdir(gb_dir)):
                    if fn.startswith(f"{d}_{code}__") and fn.endswith(".sidecar.json"):
                        try:
                            with open(os.path.join(gb_dir, fn), encoding="utf-8") as fh:
                                prior_rec = json.load(fh)
                        except ValueError:
                            prior_rec = None
                        break
            if prior_rec and prior_rec.get("sha256") and prior_rec.get("stored"):
                # the sidecar IS the fetch record (same fields), verbatim
                grec = dict(prior_rec)
                grec["reused_from_store"] = True
            else:
                grec = base.fetch_recorded(gb_url, f"gamebooks/{d}", f"{d}_{code}",
                                           expect="pdf")
                grec.pop("_raw", None)
            grec["date"] = d
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
                f"{grec.get('http_status')} {grec.get('bytes', 0)} bytes"
                + (" (reused from store)" if grec.get("reused_from_store") else ""))
            if not grec.get("reused_from_store"):
                time.sleep(1.2)


GRID_WINDOW = None   # (lo, hi) datetime batch filter; set by --grid-from/--grid-to


def _edition_dt(edition):
    m = _re.search(r"_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf$", edition)
    if not m:
        return None
    from datetime import datetime as _dt
    d, hh, mm, ampm = m.groups()
    return _dt.strptime("%s %s:%s%s" % (d, hh, mm, ampm), "%Y-%m-%d %I:%M%p")


def probe_clock_grid():
    """Archive editions the index no longer lists, by probing the league's own
    publication clock.

    MEASURED (2026-11-19): the official index page lists only the *current*
    day's editions — on 2026-11-17T16:36Z the engine's capture recorded 47
    listed editions, all of them 2026-11-17 (12:00 AM -> 11:30 AM ET), and the
    2026-11-19T06:00Z fetch listed 4, all 2026-11-19 (12:00 AM -> 12:45 AM).
    The 11/17-afternoon and 11/18 series are therefore not discoverable from
    the index any more. What IS known from the archive itself (114 archived
    editions across 2026-11-15..17 and 2026-11-19): the league files at
    15-minute intervals around the clock on game days. Each candidate label on
    that grid is probed exactly once and the outcome recorded — HTTP 200 bytes
    are stored content-addressed (identical re-downloads write nothing);
    anything else is recorded as "unavailable at capture time", which is never
    proof of absence. Discovery provenance is recorded in the probe record
    (``listed_on_official_index`` stays false for grid probes), not guessed.
    """
    import hashlib
    import urllib.error

    def labels_for(day, start_h, start_m, end_h, end_m):
        out = []
        h, m = start_h, start_m
        while (h, m) <= (end_h, end_m):
            ampm = "AM" if h < 12 else "PM"
            hh = h % 12 or 12
            out.append("Injury-Report_%s_%02d_%02d%s.pdf" % (day, hh, m, ampm))
            m += 15
            if m == 60:
                h, m = (h + 1) % 24, 0
        return out

    # Grid windows: 11/17 from the 11:45 AM ET point the archive stops at,
    # through 11:45 PM; 11/18 the full day; 11/19 12:00 AM -> 2:00 AM (the
    # run happens in the small hours ET; anything later is the scheduled job's).
    candidates = []
    candidates += labels_for("2026-11-17", 11, 45, 23, 45)
    candidates += labels_for("2026-11-18", 0, 0, 23, 45)
    candidates += labels_for("2026-11-19", 0, 0, 2, 0)

    archived = set()
    if os.path.isdir(fo.INJURY_PDF_DIR):
        for fn in os.listdir(fo.INJURY_PDF_DIR):
            if fn.endswith(".pdf"):
                archived.add(fn[:-4].split("__")[0] + ".pdf")

    results = []
    def _in_window(edition):
        if GRID_WINDOW is None:
            return True
        dt = _edition_dt(edition)
        if dt is None:
            return False
        lo, hi = GRID_WINDOW
        if lo is not None and dt < lo:
            return False
        if hi is not None and dt > hi:
            return False
        return True

    todo = [e for e in candidates if e not in archived and _in_window(e)]
    log("injury clock-grid probe: %d candidates (%d already archived), %d to probe"
        % (len(candidates), len(archived & set(candidates)), len(todo)))
    def _probe_edition(edition):
        # one clock-grid candidate: fetch, verify the PDF signature, store
        # content-addressed with a sidecar, and record the outcome exactly
        url = fo.INJURY_HOST + edition
        rec = {"edition": edition, "url": url, "http_status": None,
               "bytes": 0, "sha256": None, "attempts": 0,
               "listed_on_official_index": False,
               "discovered_via": ("clock-grid probe (league files at 15-minute "
                                  "intervals; see manifest clock_grid note)")}
        for attempt in (1, 2, 3):
            rec["attempts"] = attempt
            try:
                raw = fo.get(url, timeout=10)
                rec["http_status"] = 200
                rec["bytes"] = len(raw)
                rec["sha256"] = hashlib.sha256(raw).hexdigest()
                rec["pdf_valid"] = b"%PDF-" in raw[:1024]
                if not rec["pdf_valid"]:
                    rec["error"] = "HTTP 200 response did not contain a PDF signature"
                    log("  %s: invalid PDF response; not stored" % edition)
                    break
                os.makedirs(fo.INJURY_PDF_DIR, exist_ok=True)
                stem = "%s__%s" % (edition[:-4], rec["sha256"])
                pdf_path = os.path.join(fo.INJURY_PDF_DIR, stem + ".pdf")
                meta_path = os.path.join(fo.INJURY_PDF_DIR, stem + ".json")
                if not os.path.exists(pdf_path):
                    with open(pdf_path, "wb") as fh:
                        fh.write(raw)
                if not os.path.exists(meta_path):
                    with open(meta_path, "w", encoding="utf-8") as fh:
                        json.dump({"edition": edition, "source_url": url,
                                   "retrieved_at_utc": now_utc(),
                                   "bytes": len(raw),
                                   "sha256": rec["sha256"],
                                   "content_type": "application/pdf"},
                                  fh, indent=2)
                rec["artifact_path"] = os.path.relpath(pdf_path, ROOT).replace(os.sep, "/")
                log("  %s: 200, %d PDF bytes" % (edition, len(raw)))
                break
            except urllib.error.HTTPError as exc:
                rec["http_status"] = exc.code
                log("  %s: HTTP %s (attempt %d)" % (edition, exc.code, attempt))
                if exc.code in (403, 429) and attempt < 3:
                    time.sleep(4)
                    continue
                break
            except Exception as exc:  # noqa: BLE001
                # transient network failure (timeout, reset): retry cheaply, then
                # record the failure as-is - never as proof of absence
                rec["error"] = "%s: %s" % (type(exc).__name__, exc)
                log("  %s: %s (attempt %d)" % (edition, rec["error"], attempt))
                if attempt < 3:
                    time.sleep(2)
                    continue
                break
        time.sleep(0.4)
        return rec

    # light parallelism: each probe is an independent static-file GET with its
    # own recorded outcome; 5 workers keep wall time bounded when the CDN is
    # slow (measured 2026-11-19T06:48Z on this repo's runner: sequential probes
    # averaged ~50 s each) while staying far below any page-level request rate.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as pool:
        for rec in pool.map(_probe_edition, todo):
            results.append(rec)
    return results


def capture_injury_editions(manifest):
    """Archive every unarchived edition of 2026-11-17..19 the official index
    lists (engine path), then probe the league's clock grid for the editions
    the index no longer lists (see probe_clock_grid).

    engine/fetch_official.capture_injury is called for the index-driven part so
    the canonical archive naming, sidecar schema and probe record stay exactly
    the ones the scheduled refresh writes (PR #170's promotion path reads
    those). The engine caps 10 new editions per call; this driver loops until
    the index is exhausted or the pass bound is hit. Both sources are then
    merged into ONE probe record sorted newest-edition-first, so
    promote_injuries sees the true newest archived edition rather than the last
    pass's.
    """
    # Keep the index page bytes as evidence of what the league lists today.
    irec = base.fetch_recorded(INJURY_INDEX_URL, "html", "injury_index",
                               compress=True)
    irec.pop("_raw", None)
    text = fo.as_text(fo.get(INJURY_INDEX_URL, timeout=45))
    editions = fo.parse_injury_index(text)
    wanted = [e for e in editions
              if any(("Injury-Report_%s_" % d) in e for d in INJURY_DATES)]
    log("injury index: %d editions listed, %d for %s"
        % (len(editions), len(wanted), ", ".join(INJURY_DATES)))
    manifest["injury_index"] = {
        "url": INJURY_INDEX_URL,
        "page_stored": irec.get("stored"),
        "page_sha256": irec.get("sha256"),
        "editions_listed": len(editions),
        "editions_wanted_dates": len(wanted),
        "newest_listed": editions[0] if editions else None,
        "note": ("MEASURED: the index lists only the current day's editions "
                 "(47 listed on 2026-11-17T16:36Z, all 2026-11-17; 4 listed on "
                 "2026-11-19T06:00Z, all 2026-11-19). Earlier series are "
                 "probed from the league's 15-minute clock grid - see the "
                 "manifest's clock_grid block."),
    }

    all_results = []
    changed, failed = [], []
    if GRID_WINDOW is not None:
        log("grid batch window set: skipping the index-driven passes "
            "(index editions were captured in earlier runs)")
    for p in range(1, MAX_INJURY_PASSES + 1):
        if GRID_WINDOW is not None:
            break
        results = fo.capture_injury(now_utc(), changed, failed, editions)
        fresh = [r for r in results if r.get("artifact_path")]
        all_results.extend(results)
        log("injury index pass %d: %d attempted, %d stored (cap 10 new per pass)"
            % (p, len(results), len(fresh)))
        if len(results) < 10:
            break
        time.sleep(2.0)

    grid = probe_clock_grid()
    all_results.extend(grid)

    # Merge so the probe record's results[0] is the newest edition actually
    # stored (promote_injuries takes results[0]).
    def ed_key(name):
        m = _re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", name)
        if not m:
            return (name, 0)
        y, mo, d, hh, mm, ampm = m.groups()
        return ("%s-%s-%s" % (y, mo, d),
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
        "method": ("index-driven (engine/fetch_official.capture_injury, looped "
                   "past the per-pass cap) plus a 15-minute clock-grid probe for "
                   "the earlier series the index no longer lists; records merged "
                   "newest-edition-first; session driver arena/4f19ecf1-nba1"),
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
        "non_200_count": sum(1 for r in merged if r.get("http_status") != 200),
        "non_200_sample": [{"edition": r["edition"], "http_status": r.get("http_status")}
                           for r in merged if r.get("http_status") != 200][:20],
        "newest_stored": stored[0]["edition"] if stored else None,
        "changed": changed,
        "failed": failed,
    }
    manifest["clock_grid"] = {
        "rule": ("quarter-hourly labels, measured from 114 archived editions "
                 "across 2026-11-15..17 and 2026-11-19 and from the 47-edition "
                 "index listing on 2026-11-17"),
        "probe_results": {
            "200": sum(1 for r in grid if r.get("http_status") == 200),
            "other": sum(1 for r in grid if r.get("http_status") != 200),
        },
    }
    log("injury archive: %d editions stored OK across both sources, newest %s"
        % (len(stored), stored[0]["edition"] if stored else None))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dates", default="2026-11-17,2026-11-18")
    ap.add_argument("--skip-gamebooks", action="store_true")
    ap.add_argument("--skip-injury", action="store_true")
    ap.add_argument("--only", choices=("gamebooks", "injury"), default=None,
                    help="run one stage only (the workflow commits each stage "
                         "separately so a reclaimed runner loses no completed work)")
    ap.add_argument("--grid-from", dest="grid_from", default=None,
                    help="clock-grid batch window start, e.g. 2026-11-17_11:45AM")
    ap.add_argument("--grid-to", dest="grid_to", default=None,
                    help="clock-grid batch window end, e.g. 2026-11-17_03:30PM")
    args = ap.parse_args()
    global GRID_WINDOW
    GRID_WINDOW = None
    if args.grid_from or args.grid_to:
        from datetime import datetime as _dt
        fmt = "%Y-%m-%d_%I:%M%p"
        GRID_WINDOW = (_dt.strptime(args.grid_from, fmt) if args.grid_from else None,
                       _dt.strptime(args.grid_to, fmt) if args.grid_to else None)
    run_stamp = {"at_utc": now_utc(), "argv": " ".join(sys.argv[1:]) or "(all stages)"}
    if args.only == "gamebooks":
        args.skip_injury = True
    elif args.only == "injury":
        args.skip_gamebooks = True

    os.makedirs(SESSION_DIR, exist_ok=True)
    # Stage runs commit separately; merge into an existing manifest so one
    # stage never erases the other's records.
    manifest_path = os.path.join(SESSION_DIR, "capture_manifest.json")
    prior = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, encoding="utf-8") as fh:
                prior = json.load(fh)
        except ValueError:
            prior = {}
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

    if prior:
        for k in ("days", "gamebooks", "gamebooks_skipped_not_final", "failures"):
            seen = {(x.get("url"), x.get("game_id"), x.get("error")) for x in manifest.get(k, [])}
            for x in prior.get(k, []) or []:
                if (x.get("url"), x.get("game_id"), x.get("error")) not in seen:
                    manifest.setdefault(k, []).append(x)
        for k in ("injury_index", "injury_editions", "clock_grid", "injury_probe"):
            if prior.get(k) and not manifest.get(k):
                manifest[k] = prior[k]
        manifest["runs"] = (prior.get("runs") or []) + [run_stamp]
    else:
        manifest["runs"] = [run_stamp]
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    log(f"done: {len(manifest['gamebooks'])} gamebook fetches, "
        f"{len(manifest['failures'])} failure(s) recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
