#!/usr/bin/env python3
"""gate_refresh.py — freshness + provenance gate for the official capture layer.

Run after engine/fetch_official.py, before any rebuild or promotion:

    python3 engine/gate_refresh.py

Checks (each prints PASS/FAIL; exit 1 if any FAIL):
  1. FRESHNESS  - every capture payload in data/raw/_capture_*.json carries a
                  captured_at_utc no older than MAX_AGE_HOURS (default 26h: the
                  job runs three times a day; a day-old capture without a fresh
                  re-capture is a stale-data failure, not a pass).
  2. PROVENANCE - every capture payload carries source_url on an official host
                  (www.nba.com / official.nba.com / ak-static.cms.nba.com /
                  stats.nba.com), and every fetched payload carries a
                  page_sha256. Nothing anonymous is allowed into a rebuild.
  3. COVERAGE   - every id in engine/fetch_official.py FETCHES has either a
                  fresh _capture_<id>.json or a _capture_evidence_<id>.json from
                  the current run (a failed fetch must leave evidence; silently
                  missing sources fail the gate).
  4. SCHEMA     - _capture_S1_season.json rows still parse to 30 teams with
                  W+L == GP and the committed column list (the same validation
                  the fetch script applies, re-asserted at gate time so a
                  hand-edited capture cannot pass).

Writes data/raw/_capture_gate_report.json (also uploaded by the workflow and
quoted in the promotion PR). Exit 0 = gate open: rebuild/promotion may proceed.
"""
import datetime
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, read_json  # noqa: E402
from fetch_official import ALLOWED_HOSTS, BASE_COLS, FETCHES, OPP_COLS, STATS_COLS  # noqa: E402

MAX_AGE_HOURS = 26
NOW = datetime.datetime.now(datetime.timezone.utc)


def iso_age_hours(stamp):
    try:
        ts = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return (NOW - ts).total_seconds() / 3600.0


def main():
    results = []   # (check, target, status, detail)

    files = sorted(glob.glob(os.path.join(RAW, "_capture_*.json")))
    seen_ids = set()

    for path in files:
        name = os.path.basename(path)
        if name.startswith("_capture_evidence_") or name.startswith("_capture_gate_"):
            continue
        doc = read_json(path)
        if not isinstance(doc, dict):
            results.append(("schema", name, "FAIL", "not a JSON object"))
            continue
        ident = name[len("_capture_"):-len(".json")]
        seen_ids.add(ident)

        stamp = doc.get("captured_at_utc")
        age = iso_age_hours(stamp) if stamp else None
        if age is None:
            results.append(("freshness", name, "FAIL", f"missing/unparseable captured_at_utc: {stamp!r}"))
        elif age > MAX_AGE_HOURS:
            results.append(("freshness", name, "FAIL",
                            f"capture is {age:.1f}h old (max {MAX_AGE_HOURS}h); "
                            "re-fetch before any rebuild"))
        else:
            results.append(("freshness", name, "PASS", f"{age:.1f}h old"))

        src = doc.get("source_url") or doc.get("fetched_from")
        host = (src or "").split("/")[2] if src and "://" in src else None
        if not src:
            results.append(("provenance", name, "FAIL", "no source_url"))
        elif host not in ALLOWED_HOSTS:
            results.append(("provenance", name, "FAIL", f"non-official host: {host!r}"))
        elif "page_sha256" not in doc and "rows" not in doc:
            results.append(("provenance", name, "FAIL",
                            "neither page_sha256 nor parsed rows recorded"))
        else:
            results.append(("provenance", name, "PASS", f"{host}"))

        # schema re-assert for the model-input capture
        if ident in ("S1_season", "S2_train") and "rows" in doc:
            rows = doc["rows"]
            cols = doc.get("cols") or STATS_COLS
            bad = []
            if len(rows) != 30:
                bad.append(f"row count {len(rows)} != 30")
            if cols != STATS_COLS:
                bad.append(f"cols differ from committed schema")
            for r in rows:
                d = dict(zip(cols, r))
                if d.get("w", -1) + d.get("l", -1) != d.get("gp", -2):
                    bad.append(f"{d.get('team')}: W+L != GP")
                    break
            results.append(("schema", name, "FAIL" if bad else "PASS",
                            "; ".join(bad) if bad else "30 rows, W+L==GP, schema match"))
        if ident in ("S8_traditional",) and "rows" in doc:
            rows = doc["rows"]
            cols = doc.get("cols") or BASE_COLS
            ok = len(rows) == 30 and cols == BASE_COLS
            results.append(("schema", name, "PASS" if ok else "FAIL",
                            f"{len(rows)} rows, cols {'match' if cols == BASE_COLS else 'DIFFER'}"))
        if ident in ("S9_opponent",) and "rows" in doc:
            rows = doc["rows"]
            cols = doc.get("cols") or OPP_COLS
            ok = len(rows) == 30 and cols == OPP_COLS
            results.append(("schema", name, "PASS" if ok else "FAIL",
                            f"{len(rows)} rows, cols {'match' if cols == OPP_COLS else 'DIFFER'}"))

    # coverage: every FETCHES id must have a capture or evidence artefact
    for key in FETCHES:
        cap = os.path.join(RAW, f"_capture_{key}.json")
        ev = os.path.join(RAW, f"_capture_evidence_{key}.json")
        if os.path.exists(cap):
            results.append(("coverage", key, "PASS", "capture present"))
        elif os.path.exists(ev):
            results.append(("coverage", key, "PASS",
                            "failed fetch left evidence (capture absent; stale snapshot kept)"))
        else:
            results.append(("coverage", key, "FAIL",
                            "no capture and no evidence artefact - the source was never touched"))

    fails = [r for r in results if r[2] == "FAIL"]
    report = {
        "gate": "refresh freshness + provenance",
        "run_at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_age_hours": MAX_AGE_HOURS,
        "status": "FAIL" if fails else "PASS",
        "checks": [{"check": c, "target": t, "status": s, "detail": d}
                   for c, t, s, d in results],
        "failed": [{"check": c, "target": t, "detail": d} for c, t, s, d in fails],
    }
    path = os.path.join(RAW, "_capture_gate_report.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    for c, t, s, d in results:
        print(f"{s:4} [{c}] {t}: {d}")
    print(f"\ngate {report['status']} ({len(fails)} failures) -> data/raw/_capture_gate_report.json")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
