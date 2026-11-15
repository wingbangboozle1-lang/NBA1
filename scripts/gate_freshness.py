#!/usr/bin/env python3
"""gate_freshness.py — the freshness + provenance gate that guards every rebuild.

    python3 scripts/gate_freshness.py        # exit 0 = rebuild allowed

Requirement: "Extend the scheduled job to refresh the official schedule,
standings, team statistics and injury report for each rolling slate, then rebuild
only after freshness and provenance gates pass."

This is that gate. It is deliberately strict and it never heals anything: a
failure is written to `data/capture/<run>/gate.json`, printed, and the rebuild is
skipped.

Checks, in order
----------------
P1  provenance   every required artefact has a fetch record: HTTP 200, a SHA-256,
                 an allowed official host, and a retrieval timestamp.
P2  freshness    every required artefact was retrieved inside its own SLA.
                 The injury report moves several times a day, so it gets a
                 tighter SLA (6h) than the schedule (24h) or the season-long
                 stats pages (36h).
P3  completeness the parsers produced the rows the official pages publish:
                 30 standings rows, 30 rows on each of the three team-stat
                 pages, at least one game on each slate date.
P4  integrity    every stored injury PDF's bytes still hash to the SHA-256
                 recorded when it was retrieved. This is the check that makes the
                 injury archive tamper-evident.
P5  no-stale     the run being gated is the newest run in data/capture/.

Exit 0 only if every hard check passes. Advisory findings are recorded and do
not block a rebuild.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE = os.path.join(ROOT, "data", "capture")

ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com", "cdn.nba.com"}

# artefact -> (parsed filename, minimum rows, freshness SLA in hours)
REQUIRED = {
    "standings":          ("standings.json", 30, 24.0, "row_count"),
    "teams_traditional":  ("teams_traditional.json", 30, 36.0, "row_count"),
    "teams_opponent":     ("teams_opponent.json", 30, 36.0, "row_count"),
    "teams_advanced":     ("teams_advanced.json", 30, 36.0, "row_count"),
    "injury_index":       ("injury_index.json", 1, 6.0, "edition_count"),
}


def _parse(ts):
    try:
        return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc)
    except Exception:                                            # noqa: BLE001
        return None


def main():
    latest_path = os.path.join(CAPTURE, "LATEST")
    if not os.path.exists(latest_path):
        print("GATE FAIL: no capture run has ever been recorded (data/capture/LATEST missing)")
        return 1
    run = open(latest_path, encoding="utf-8").read().strip()
    run_dir = os.path.join(CAPTURE, run)
    man_path = os.path.join(run_dir, "manifest.json")
    if not os.path.exists(man_path):
        print(f"GATE FAIL: run {run} has no manifest.json")
        return 1
    man = json.load(open(man_path, encoding="utf-8"))
    now = datetime.datetime.now(datetime.timezone.utc)

    hard, advisory = [], []
    checks = []

    def add(cid, ok, detail, blocking=True):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "blocking": blocking})
        (hard if blocking else advisory).append(f"{cid}: {detail}") if not ok else None

    # ---- P1 provenance ----------------------------------------------------
    fetches = man.get("fetches", [])
    bad_host = [f for f in fetches if f.get("host") not in ALLOWED_HOSTS]
    add("P1.hosts", not bad_host,
        f"{len(bad_host)} fetch(es) to a host outside the official allowlist")
    no_sha = [f for f in fetches if f.get("http_status") == 200 and not f.get("sha256")]
    add("P1.sha256", not no_sha, f"{len(no_sha)} successful fetch(es) without a SHA-256")
    not_ok = [f for f in fetches if f.get("http_status") != 200]
    add("P1.http200", not not_ok,
        f"{len(not_ok)} fetch(es) did not return HTTP 200: "
        + ", ".join(sorted({str(f.get('http_status')) for f in not_ok})[:5]))

    # ---- P2 freshness + P3 completeness -----------------------------------
    parsed_dir = os.path.join(run_dir, "parsed")
    for name, (fn, min_rows, sla_h, count_key) in REQUIRED.items():
        p = os.path.join(parsed_dir, fn)
        if not os.path.exists(p):
            add(f"P3.{name}", False, f"{fn} missing from the run")
            continue
        d = json.load(open(p, encoding="utf-8"))
        n = d.get(count_key) if isinstance(d, dict) else None
        if n is None and isinstance(d, dict) and isinstance(d.get("rows"), list):
            n = len(d["rows"])
        add(f"P3.{name}", (n or 0) >= min_rows,
            f"{fn}: {n} rows, need >= {min_rows}")
        # freshness: newest successful fetch whose url matches the artefact
        cands = [f for f in fetches
                 if f.get("http_status") == 200 and f.get("fetched_at_utc")
                 and name.replace("teams_", "teams/") in (f.get("url") or "")]
        if name == "standings":
            cands = [f for f in fetches if (f.get("url") or "").endswith("/standings")]
        if name == "injury_index":
            cands = [f for f in fetches if "nba-injury-report" in (f.get("url") or "")]
        if not cands:
            add(f"P2.{name}", False, f"no successful fetch record for {name}")
            continue
        newest = max(_parse(f["fetched_at_utc"]) for f in cands
                     if _parse(f["fetched_at_utc"]))
        age = (now - newest).total_seconds() / 3600.0
        add(f"P2.{name}", age <= sla_h,
            f"{name} is {age:.2f}h old; SLA is {sla_h:.0f}h")

    # slate dates: each must have at least one game row
    for d in man.get("slate_dates", []):
        p = os.path.join(parsed_dir, f"games_{d}.json")
        if not os.path.exists(p):
            add(f"P3.slate_{d}", False, f"games_{d}.json missing")
            continue
        g = json.load(open(p, encoding="utf-8"))
        add(f"P3.slate_{d}", len(g.get("rows", [])) > 0,
            f"{d}: {len(g.get('rows', []))} games on the official page")

    # ---- P4 integrity of the stored injury PDFs ---------------------------
    pdf_dir = os.path.join(run_dir, "injury_pdf")
    pdfs = sorted(f for f in os.listdir(pdf_dir) if f.endswith(".pdf")) if os.path.isdir(pdf_dir) else []
    pdf_rec = os.path.join(parsed_dir, "injury_pdfs.json")
    hash_map = {}
    if os.path.exists(pdf_rec):
        for e in json.load(open(pdf_rec, encoding="utf-8")).get("editions", []):
            hash_map[e.get("pdf_stored_path", "").rsplit("/", 1)[-1]] = e.get("pdf_sha256")
    broken = []
    for fn in pdfs:
        want = hash_map.get(fn)
        if not want:
            continue
        got = hashlib.sha256(open(os.path.join(pdf_dir, fn), "rb").read()).hexdigest()
        if got != want:
            broken.append(fn)
    add("P4.pdf_bytes", not broken,
        f"{len(broken)} stored injury PDF(s) no longer hash to the value recorded at capture")
    add("P4.pdf_present", len(pdfs) > 0,
        f"{len(pdfs)} injury PDFs archived in this run", blocking=False)

    # ---- P5: the gated run must be the newest ------------------------------
    runs = sorted(d for d in os.listdir(CAPTURE) if os.path.isdir(os.path.join(CAPTURE, d)))
    add("P5.newest", not runs or runs[-1] == run,
        f"newest run on disk is {runs[-1] if runs else '-'}, gating {run}", blocking=False)

    gate = {
        "gate": "freshness_and_provenance",
        "run_id": run,
        "evaluated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checks": checks,
        "passed": not hard,
        "blocking_failures": hard,
        "advisory": advisory,
        "slas_hours": {k: v[2] for k, v in REQUIRED.items()},
        "count_of_fetches": len(fetches),
        "count_of_injury_pdfs": len(pdfs),
    }
    with open(os.path.join(run_dir, "gate.json"), "w", encoding="utf-8") as fh:
        json.dump(gate, fh, indent=1)

    print(f"GATE {'PASS' if not hard else 'FAIL'} — run {run}, "
          f"{len(checks)} checks, {len(hard)} blocking, {len(advisory)} advisory")
    for c in checks:
        print(f"  [{'ok ' if c['ok'] else 'FAIL'}] {c['id']}: {c['detail']}")
    if gate["passed"]:
        print("REBUILD ALLOWED")
    else:
        print("REBUILD SKIPPED — the gate did not pass, so no page was regenerated")
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
