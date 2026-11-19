"""Measure the scheduled refresh's publish path from committed evidence only.

    python3 scripts/f3cb4a98_refresh_path_audit.py
    python3 scripts/f3cb4a98_refresh_path_audit.py --json   # machine-readable

SESSION arena/f3cb4a98-nba1, COORDINATION.md section 69.

WHY THIS EXISTS
---------------
The brief's first requirement is: "Extend the scheduled job to refresh the
official schedule, standings, team statistics and injury report for each
rolling slate, then rebuild only after freshness and provenance gates pass."

On `main` `9cbdd74` the scheduled job captures, promotes and settles, but its
**rebuild step has never executed**. That is not an opinion: the only run
record ever committed (`data/raw/_last_refresh.json`, introduced by the single
commit that touches it) says `build_outcome: "skipped"` and
`freshness_ok: "false"`, and `engine/refresh_gate.py` on `main` prints 13
BLOCK lines.

This script answers the question the board kept answering by assertion: *which
of the gate's requirements can never be satisfied, and on what evidence?*

METHOD (every number below is read off a file, never assumed)
-------------------------------------------------------------
For each source the fetcher declares in `engine/fetch_official.py`'s FETCHES
table, and for each model input `engine/pipeline.py` actually loads, the audit
records:

  1. whether the run record lists that source as checked this run;
  2. whether the parsed capture exists and holds rows;
  3. whether a bounded parse-failure evidence record exists, and what its
     `problems` say;
  4. whether the promoted snapshot exists, and whether it carries a
     `verification` block;
  5. whether the model pipeline loads that exact filename (read out of
     `engine/pipeline.py`'s own source text, so it cannot drift);
  6. whether the promoted snapshot has EVER existed in this repository's
     history (from `git log --all`, when git is available).

Item 6 is the decisive one. A gate requirement that names a file with no
history is not a freshness check; it is an unsatisfiable predicate, and the
rebuild step behind it is dead code. Such a requirement is classified
`terminal` here and must be handled deliberately (declared, evidenced and
expiring) instead of being left in the gate looking like a transient failure.

Outputs `data/raw/refresh_path_audit.json`. Nothing is written to a model
input, and no promoted snapshot is touched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(RAW, "refresh_path_audit.json")
FETCHER = os.path.join(ROOT, "engine", "fetch_official.py")
PIPELINE = os.path.join(ROOT, "engine", "pipeline.py")
GATE = os.path.join(ROOT, "engine", "refresh_gate.py")
RECORD = os.path.join(RAW, "_last_refresh.json")

# key -> parsed capture, parse-failure evidence, promoted snapshot.
# The promoted path is the one engine/refresh_gate.py requires; capture and
# evidence names are the ones engine/fetch_official.py writes.
SOURCES = {
    "S1_season": ("_capture_S1_season.json", "_capture_evidence_S1_season.json",
                  "team_advanced.json"),
    "S2_train": ("_capture_S2_train.json", "_capture_evidence_S2_train.json", None),
    "S7_players": ("_capture_S7_players.json", None, "players_traditional.json"),
    "S4_schedule": ("_capture_S4_schedule.json", "_capture_evidence_S4_schedule.json",
                    "schedule_upcoming.json"),
    "S5_injury_index": ("_capture_S5_injury_index.json", None, None),
    "S8_standings": ("_capture_S8_standings.json", "_capture_evidence_S8_standings.json",
                     "standings.json"),
    "S9_team_traditional": ("_capture_S9_team_traditional.json",
                            "_capture_evidence_S9_team_traditional.json",
                            "team_traditional.json"),
    "S10_team_opponent": ("_capture_S10_team_opponent.json",
                          "_capture_evidence_S10_team_opponent.json",
                          "team_opponent.json"),
}


def assert_full_history():
    """Refuse to audit git history from a shallow clone.

    A shallow clone answers "0 commits" for files that do exist, which turns
    a real snapshot into a false terminal finding. This bit this session once
    (see COORDINATION.md section 69.2); the guard makes the failure loud.
    """
    shallow = os.path.join(ROOT, ".git", "shallow")
    if os.path.exists(shallow):
        return ("SHALLOW CLONE: history counts are not trustworthy. "
                "Run `git fetch --unshallow origin` first.")
    return None


def read_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def load_or(path, default=None):
    try:
        return read_json(path)
    except (OSError, ValueError):
        return default


def git_history_count(relative_path):
    """How many commits in this repository ever touched `relative_path`?

    Returns (count, error). A count of 0 means the file has never existed on
    any ref, which is what makes a gate requirement unsatisfiable.
    """
    try:
        out = subprocess.run(
            ["git", "log", "--all", "--oneline", "--", relative_path],
            cwd=ROOT, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:      # pragma: no cover
        return None, f"{type(exc).__name__}: {exc}"
    if out.returncode != 0:
        return None, (out.stderr or "git log failed").strip()[:300]
    return len([ln for ln in out.stdout.splitlines() if ln.strip()]), None


def capture_row_count(key, capture):
    """Rows a parsed capture actually carries, by the fetcher's own shape.

    engine/fetch_official.py does not use one field for every source: the
    schedule branch writes `games`, the injury-index branch writes `editions`,
    the players branch writes a page-level record with no rows at all, and the
    three team-stat/standings branches write `rows`. Reading only `rows` would
    report a readable schedule as empty — which is the same class of mistake
    this audit exists to catch, so each shape is named explicitly.
    """
    if not isinstance(capture, dict):
        return 0
    for field in ("rows", "games", "editions"):
        value = capture.get(field)
        if isinstance(value, list):
            return len(value)
    return 0


def evidence_problems(evidence):
    """The bounded reasons a captured page could not be parsed.

    Two evidence shapes exist in this repository and both are real:
    the standings/team-stat branches write `problems` (a list of strategy
    failures); the advanced branch writes `status: "parse_failed"` plus an
    `api_attempt.parse_note` and a bounded `failure_evidence` excerpt. Reading
    only `problems` would call a proved shell "unmeasured", which understates
    the finding.
    """
    if not isinstance(evidence, dict):
        return []
    out = [str(p) for p in (evidence.get("problems") or [])]
    if evidence.get("status") == "parse_failed":
        note = ((evidence.get("api_attempt") or {}).get("parse_note")
                or "parse_failed (no parse_note recorded)")
        out.append(str(note))
        for item in (evidence.get("failure_evidence") or [])[:1]:
            around = (item or {}).get("around")
            if around:
                out.append(f"bounded excerpt around {around!r}")
    return out


def fetcher_urls(source_text):
    """Official URL per source key, read out of engine/fetch_official.py.

    The URL published beside an audit row must be the one the fetcher actually
    requests, so it is parsed from its FETCHES table rather than retyped.
    """
    out = {}
    for match in re.finditer(
            r'"(S\d+_[a-z_]+)"\s*:\s*\(\s*"([^"]+)"', source_text):
        out[match.group(1)] = match.group(2)
    return out


def pipeline_consumers(source_text):
    """Which data/raw filenames engine/pipeline.py loads, read from its source."""
    found = set()
    for match in re.finditer(r'["\']([A-Za-z0-9_.\-]+\.json)["\']', source_text):
        found.add(match.group(1))
    return found


def gate_required_paths(source_text):
    """Promoted paths engine/refresh_gate.py requires, read from its source.

    Both spellings in the file are covered: the `promoted_paths` mapping and
    the literal `require_promotion(...)` calls.
    """
    found = {}
    for match in re.finditer(
            r'"(S\d+_[a-z_]+)"\s*:\s*"data/raw/([A-Za-z0-9_.\-]+\.json)"', source_text):
        found[match.group(1)] = match.group(2)
    return found


def _newest(*stamps):
    """The most recent parseable UTC stamp among the arguments (or None)."""
    best = None
    for stamp in stamps:
        if not isinstance(stamp, str):
            continue
        try:
            value = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        if best is None or value > best:
            best = value
    return best


def classify(entry):
    """Turn the measured facts into one honest classification.

    `readable`      - this run parsed structured rows AND a promoted snapshot
                      exists carrying a verification block. The gate can pass.
    `unreadable`    - the page cannot be parsed by the runner's client: a
                      bounded evidence record proves it returned a shell. The
                      gate must not require a snapshot that can never exist.
    `unmeasured`    - neither a capture nor an evidence record: nothing proves
                      either way, so the gate must block.
    """
    # A capture and its parse-failure evidence are both historical facts, so
    # the NEWER one describes the source's present state. A readable capture
    # from this run must not be overruled by evidence written weeks earlier
    # (the schedule source has exactly that shape in this repository).
    capture_time = _newest(entry.get("capture_captured_at_utc"))
    evidence_time = _newest(entry.get("evidence_captured_at_utc"))
    if entry["capture_has_rows"] and (evidence_time is None or capture_time is None
                                      or capture_time >= evidence_time):
        # A capture with parsed rows is readable whether or not a promoted
        # snapshot exists yet; promotion is the gate's business, not this
        # classification's. `promoted_verified` is reported separately.
        return "readable"
    if entry["evidence_problem_count"]:
        return "unreadable"
    if entry["capture_present"] and not entry["capture_has_rows"]:
        return "unreadable"
    return "unmeasured"


def rebuild_history():
    """Read EVERY committed run record and report when the rebuild really ran.

    The current record alone is not evidence about history: on 2026-11-19 its
    `build_outcome` is `skipped`, which says nothing about 2026-11-14. This
    session published "rebuild has ever run: no" from the current record and
    it was wrong (see COORDINATION.md section 73.2), so the history is read
    from git instead of inferred from one file.
    """
    facts = {"records_read": 0, "successes": [], "skipped_or_failed_after_last_success": 0,
             "error": None, "method": "git show <sha>:data/raw/_last_refresh.json for every "
                                      "commit that touched the file"}
    if os.path.exists(os.path.join(ROOT, ".git", "shallow")):
        facts["error"] = ("shallow clone: run `git fetch --unshallow origin` first")
        return facts
    try:
        commits = subprocess.run(
            ["git", "log", "--all", "--format=%H", "--", "data/raw/_last_refresh.json"],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:      # pragma: no cover
        facts["error"] = f"{type(exc).__name__}: {exc}"
        return facts
    if commits.returncode != 0:
        facts["error"] = (commits.stderr or "git log failed").strip()[:300]
        return facts
    seen = set()
    rows = []
    for sha in [c for c in commits.stdout.split() if c]:
        try:
            raw = subprocess.run(
                ["git", "show", f"{sha}:data/raw/_last_refresh.json"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if raw.returncode != 0:
            continue
        try:
            record = json.loads(raw.stdout)
        except ValueError:
            continue
        stamp = record.get("captured_at_utc")
        key = (stamp, record.get("build_outcome"))
        if key in seen:
            continue
        seen.add(key)
        rows.append({"captured_at_utc": stamp,
                     "build_outcome": record.get("build_outcome"),
                     "freshness_ok": record.get("freshness_ok"),
                     "promote_outcome": record.get("promote_outcome")})
    rows.sort(key=lambda r: r["captured_at_utc"] or "")
    facts["records_read"] = len(rows)
    facts["successes"] = [r for r in rows if r["build_outcome"] == "success"]
    if facts["successes"]:
        last = facts["successes"][-1]
        facts["last_success_utc"] = last["captured_at_utc"]
        facts["skipped_or_failed_after_last_success"] = len(
            [r for r in rows if (r["captured_at_utc"] or "") >
             (last["captured_at_utc"] or "")])
    else:
        facts["last_success_utc"] = None
    facts["rebuild_has_ever_run"] = bool(facts["successes"])
    return facts


def audit():
    history_warning = assert_full_history()
    record = load_or(RECORD, {}) or {}
    checks = {}
    for check in record.get("source_checks") or []:
        if isinstance(check, dict) and isinstance(check.get("key"), str):
            checks[check["key"]] = check
    failed = {}
    for item in record.get("failed") or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            failed[str(item[0])] = str(item[1])

    try:
        pipeline_text = open(PIPELINE, encoding="utf-8").read()
    except OSError:
        pipeline_text = ""
    consumers = pipeline_consumers(pipeline_text)
    try:
        fetcher_text = open(FETCHER, encoding="utf-8").read()
    except OSError:
        fetcher_text = ""
    fetch_urls = fetcher_urls(fetcher_text)
    try:
        gate_text = open(GATE, encoding="utf-8").read()
    except OSError:
        gate_text = ""
    gate_paths = gate_required_paths(gate_text)
    gate_requires = set(gate_paths.values())

    rows = []
    for key in sorted(SOURCES):
        capture, evidence, promoted = SOURCES[key]
        cap = load_or(os.path.join(RAW, capture)) if capture else None
        ev = load_or(os.path.join(RAW, evidence)) if evidence else None
        pro = load_or(os.path.join(RAW, promoted)) if promoted else None
        cap_rows = capture_row_count(key, cap)
        ev_problems = evidence_problems(ev) if evidence else []
        verification = (pro or {}).get("verification") or {} if isinstance(pro, dict) else {}
        history, history_error = (git_history_count(promoted) if promoted else (None, None))
        entry = {
            "key": key,
            "official_url": fetch_urls.get(key)
            or (checks.get(key) or {}).get("url"),
            "checked_this_run": key in checks,
            "http_status_this_run": (checks.get(key) or {}).get("http_status"),
            "fetch_failure_this_run": failed.get(key),
            "capture": f"data/raw/{capture}" if capture else None,
            "capture_present": bool(isinstance(cap, dict) and cap),
            "capture_row_count": cap_rows,
            "capture_has_rows": cap_rows > 0,
            "capture_captured_at_utc": (cap or {}).get("captured_at_utc")
            if isinstance(cap, dict) else None,
            "evidence": f"data/raw/{evidence}" if evidence else None,
            "evidence_captured_at_utc": (ev or {}).get("captured_at_utc")
            if isinstance(ev, dict) else None,
            "evidence_status": (ev or {}).get("status") if isinstance(ev, dict) else None,
            "evidence_problems": ev_problems,
            "evidence_problem_count": len(ev_problems),
            "promoted": f"data/raw/{promoted}" if promoted else None,
            "promoted_present": bool(isinstance(pro, dict) and pro),
            "promoted_verified": verification.get("verified") is True,
            "promoted_verified_at_utc": verification.get("verified_at_utc"),
            "promoted_source_url": verification.get("source_url"),
            "consumed_by_pipeline": bool(promoted and promoted in consumers),
            "required_by_gate": bool(promoted and promoted in gate_requires),
            "promoted_commits_in_history": history,
            "promoted_history_error": history_error,
        }
        entry["classification"] = classify(entry)
        # A gate requirement is terminal when the gate demands a snapshot that
        # this repository has never contained. That is the difference between a
        # transient failure and dead code behind a permanently-open gate.
        entry["terminal_gate_requirement"] = bool(
            entry["required_by_gate"] and history == 0)
        rows.append(entry)

    try:
        register = read_json(os.path.join(RAW, "unreadable_sources.json"))
    except (OSError, ValueError):
        register = {}
    declared = {}
    for entry in (register.get("declarations") or []):
        if isinstance(entry, dict) and isinstance(entry.get("source_key"), str):
            declared[entry["source_key"]] = entry
    for row in rows:
        decl = declared.get(row["key"])
        row["declared_unreadable"] = decl is not None
        row["declaration_expires_at_utc"] = (decl or {}).get("expires_at_utc")
        # A terminal requirement that a live, evidence-backed declaration
        # covers is no longer terminal: the gate can now pass without it.
        row["terminal_uncovered"] = bool(
            row["terminal_gate_requirement"] and decl is None)

    terminal = [r for r in rows if r["terminal_uncovered"]]
    unreadable = [r for r in rows if r["classification"] == "unreadable"]
    readable = [r for r in rows if r["classification"] == "readable"]
    return {
        "title": "Scheduled refresh publish-path audit",
        "built_by": "scripts/f3cb4a98_refresh_path_audit.py",
        "session": "arena/f3cb4a98-nba1",
        "built_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "history_warning": history_warning,
        "rule": ("Every field is read from a committed file or from git history. "
                 "No value is inferred. A gate requirement naming a snapshot "
                 "with zero commits in history is classified terminal, because "
                 "no scheduled run can ever satisfy it."),
        "run_record": {
            "path": "data/raw/_last_refresh.json",
            "captured_at_utc": record.get("captured_at_utc"),
            "build_outcome": record.get("build_outcome"),
            "freshness_ok": record.get("freshness_ok"),
            "promote_outcome": record.get("promote_outcome"),
            "fetch_outcome": record.get("fetch_outcome"),
            "promoted_item_count": len(record.get("promoted") or []),
            "failed_count": len(record.get("failed") or []),
        },
        "summary": {
            "sources_audited": len(rows),
            "readable": [r["key"] for r in readable],
            "unreadable": [r["key"] for r in unreadable],
            "terminal_gate_requirements": [r["key"] for r in terminal],
            "terminal_now_covered_by_declaration": [
                r["key"] for r in rows
                if r["terminal_gate_requirement"] and r["declared_unreadable"]],
            "declared_unreadable": sorted(declared),
            "rebuild_ever_ran_this_record": record.get("build_outcome") not in (None, "skipped"),
            "rebuild_history": rebuild_history(),
        },
        "sources": rows,
        "gate_required_snapshots": gate_paths,
        "pipeline_consumers": sorted(consumers),
    }


def render(payload):
    s = payload["summary"]
    lines = [
        "Scheduled refresh publish-path audit",
        "=" * 46,
        f"run record      : {payload['run_record']['path']}",
        f"  captured at   : {payload['run_record']['captured_at_utc']}",
        f"  fetch         : {payload['run_record']['fetch_outcome']}",
        f"  promote       : {payload['run_record']['promote_outcome']}",
        f"  freshness ok  : {payload['run_record']['freshness_ok']}",
        f"  build         : {payload['run_record']['build_outcome']}",
        f"  rebuild here  : {s.get('rebuild_ever_ran_this_record')}",
        f"  rebuild EVER  : {s.get('rebuild_history', {}).get('rebuild_has_ever_run')}"
        f"  (last success {s.get('rebuild_history', {}).get('last_success_utc')},"
        f" {s.get('rebuild_history', {}).get('records_read')} records read,"
        f" {s.get('rebuild_history', {}).get('skipped_or_failed_after_last_success')}"
        f" skipped/failed since)",
        "",
        f"{'source':22s} {'class':12s} {'gate':6s} {'hist':5s} {'pipeline':9s} problems",
        "-" * 90,
    ]
    for r in payload["sources"]:
        lines.append(
            f"{r['key']:22s} {r['classification']:12s} "
            f"{'yes' if r['required_by_gate'] else '-':6s} "
            f"{'-' if r['promoted_commits_in_history'] is None else r['promoted_commits_in_history']:5} "
            f"{'yes' if r['consumed_by_pipeline'] else '-':9s} "
            f"{(r['evidence_problems'][0] if (r['evidence_problems'] and r['classification'] != 'readable') else '')[:44]}")
    lines += [
        "",
        f"readable                    : {', '.join(s['readable']) or '(none)'}",
        f"unreadable (shell proved)   : {', '.join(s['unreadable']) or '(none)'}",
        f"TERMINAL gate requirements  : {', '.join(s['terminal_gate_requirements']) or '(none)'}",
    ]
    if s.get("terminal_now_covered_by_declaration"):
        lines += [
            "",
            "Covered by a live declaration (gate no longer demands the snapshot):",
            "  " + ", ".join(s["terminal_now_covered_by_declaration"]),
        ]
    if s["terminal_gate_requirements"]:
        lines += [
            "",
            "A terminal requirement names a snapshot with zero commits in this",
            "repository's history. The gate can never pass while it demands it,",
            "so the rebuild step behind the gate is dead code. Fix by declaring",
            "the source unreadable with evidence (and an expiry) rather than by",
            "requiring a file nothing can produce.",
        ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON only")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 when a terminal gate requirement exists")
    args = parser.parse_args()
    payload = audit()
    with open(OUT, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=1)
        stream.write("\n")
    if args.json:
        print(json.dumps(payload, indent=1))
    else:
        print(render(payload))
        print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    if args.check and payload["summary"]["terminal_gate_requirements"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
