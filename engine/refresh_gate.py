"""Fail-closed freshness/provenance gate for scheduled refresh builds.

The fetcher deliberately stores observations as capture-only artifacts. This
module permits builders to run only when every required official source was
successfully checked in this run, the check is recent, and no capture changed
since its last verified promotion. A changed capture is never treated as an
approved model input merely because it came from an official URL.

DECLARED-UNREADABLE SOURCES (COORDINATION.md section 69)
-------------------------------------------------------
A fail-closed gate has a failure mode that is worse than being permissive: a
requirement that no run can ever satisfy. This gate used to require
`data/raw/standings.json`, `data/raw/team_traditional.json` and
`data/raw/team_opponent.json` before permitting a rebuild. Those three files
have zero commits in the repository's history, because the pages they come
from are client-rendered and the runner's own committed evidence proves the
capture contains no table (see `data/raw/_capture_evidence_S8_standings.json`
and `..._S9_team_traditional.json`). The rebuild step behind the gate was
therefore dead code from the moment that requirement landed.

`data/raw/unreadable_sources.json` is the deliberate answer. A source may be
DECLARED unreadable with (a) measured evidence on disk, (b) a hard expiry, and
(c) publication on the Flagged for Review page. While a declaration is live the
gate does not require that source's snapshot; the moment it expires, the gate
blocks again. Non-negotiable properties, all enforced below:

  * a declaration never suppresses a requirement for a source whose capture
    DID parse this run - parsing again fails the gate rather than passing;
  * a declaration never promotes a value; it only removes an unsatisfiable
    predicate;
  * an unknown, malformed, expired or evidence-less declaration is ignored,
    and the original (blocking) requirement applies.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from urllib.parse import urlparse

REQUIRED = {
    "S1_season", "S4_schedule", "S5_injury_index", "S8_standings",
    "S9_team_traditional", "S10_team_opponent",
}
ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com", "stats.nba.com"}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
PROMOTION_SENSITIVE = {
    "S1_season", "S4_schedule", "S5_injury_index", "S8_standings",
    "S9_team_traditional", "S10_team_opponent", "S7_players",
}
# The register of sources proved unreadable by our own client, with evidence
# and an expiry. See the module docstring.
DECLARATIONS = "data/raw/unreadable_sources.json"
# The bounded parse-failure evidence records that justify a declaration. A
# declaration naming a source with no such file on disk is ignored.
EVIDENCE = {
    "S1_season": "data/raw/_capture_evidence_S1_season.json",
    "S2_train": "data/raw/_capture_evidence_S2_train.json",
    "S8_standings": "data/raw/_capture_evidence_S8_standings.json",
    "S9_team_traditional": "data/raw/_capture_evidence_S9_team_traditional.json",
    "S10_team_opponent": "data/raw/_capture_evidence_S10_team_opponent.json",
}


def parse_utc(value: str) -> dt.datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def live_declarations(base, now, by_key, parse_ok):
    """Which sources are admissible as declared-unreadable, and why the rest are not.

    Returns (accepted, rejected). A declaration is accepted only when every
    one of these measured facts holds:

      1. the register parses and is shaped as expected;
      2. the declaration names a source the gate actually requires;
      3. `expires_at_utc` parses, is in the future, and is not absurdly far out;
      4. the fetcher checked that source in THIS run at HTTP 200 (a stale
         declaration must not mask a source that was never fetched today);
      5. a bounded parse-failure evidence file exists for it on disk;
      6. the source did NOT parse rows in this run (`parse_ok` is False). This
         is the anti-rot rule: if the page becomes readable, the declaration
         stops applying and the normal requirement comes back, so the gate
         fails until the snapshot is actually promoted.

    Anything failing one of these is rejected with the reason, and the caller
    keeps the original blocking requirement.
    """
    accepted, rejected = {}, []
    path = os.path.join(base, DECLARATIONS)
    try:
        register = read_json(path)
    except (OSError, ValueError) as exc:
        return {}, [f"declaration register unreadable ({exc})"]
    declarations = register.get("declarations")
    if not isinstance(declarations, list):
        return {}, ["declaration register has no declarations list"]
    # An over-long horizon would defeat the point of an expiry.
    horizon = 400 * 24
    for entry in declarations:
        if not isinstance(entry, dict):
            rejected.append("malformed declaration entry")
            continue
        key = entry.get("source_key")
        if not isinstance(key, str) or not key:
            rejected.append("declaration without a source_key")
            continue
        if key not in REQUIRED:
            rejected.append(f"{key}: not a source this gate requires")
            continue
        try:
            expires = parse_utc(entry.get("expires_at_utc"))
        except (TypeError, ValueError):
            rejected.append(f"{key}: missing or invalid expires_at_utc")
            continue
        if expires <= now:
            rejected.append(f"{key}: declaration EXPIRED at {entry.get('expires_at_utc')}")
            continue
        if (expires - now).total_seconds() / 3600 > horizon:
            rejected.append(f"{key}: expires_at_utc is more than {horizon // 24} days out")
            continue
        check = by_key.get(key) or {}
        if check.get("http_status") != 200:
            rejected.append(f"{key}: source was not checked at HTTP 200 in this run, "
                            f"so a declaration cannot stand in for it")
            continue
        evidence = EVIDENCE.get(key)
        if not evidence or not os.path.exists(os.path.join(base, evidence)):
            rejected.append(f"{key}: no bounded parse-failure evidence on disk "
                            f"({evidence or 'no evidence path known'})")
            continue
        if parse_ok.get(key):
            rejected.append(f"{key}: DECLARATION STALE - the capture parsed rows in "
                            f"this run, so the snapshot is now producible and the "
                            f"normal requirement applies")
            continue
        accepted[key] = {
            "source_key": key,
            "expires_at_utc": entry.get("expires_at_utc"),
            "review_flag": entry.get("review_flag"),
            "evidence": evidence,
            "required_snapshot": entry.get("required_snapshot"),
        }
    return accepted, rejected


def evaluate(record: dict, now: dt.datetime, max_age_hours: float = 10) -> list[str]:
    """Back-compatible wrapper returning only the blocking errors."""
    return evaluate_with_report(record, now, max_age_hours)[0]


def evaluate_with_report(record: dict, now: dt.datetime,
                         max_age_hours: float = 10) -> tuple[list[str], dict]:
    """Gate decision plus the machine-readable reason for it.

    Returns (errors, report). `errors` empty means the rebuild may run.
    `report` always carries the declarations that were applied and any that
    were rejected, so a green gate built on a declaration is never
    indistinguishable from a green gate built on fresh promoted data.
    """
    errors: list[str] = []
    warnings: list[str] = []
    accepted_declarations: list[dict] = []
    base = os.environ.get("NBA1_REPO_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    captured = record.get("captured_at_utc")
    try:
        run_time = parse_utc(captured)
    except (TypeError, ValueError):
        return ["missing or invalid refresh run timestamp"]
    age = (now - run_time).total_seconds() / 3600
    if age < -0.05 or age > max_age_hours:
        errors.append(f"refresh run is stale or future-dated ({age:.2f}h; maximum {max_age_hours:g}h)")

    failures = record.get("failed")
    if not isinstance(failures, list):
        errors.append("refresh record has no valid failure list")
        failures = []
    # NOTE ON ORDERING: the `failed` entries for a source that is declared
    # unreadable are separated from the rest further down, once the run's
    # provenance checks are indexed (the declaration has to be validated
    # against THIS run before it can excuse anything). Every other entry stays
    # a hard block, unchanged.

    checks = record.get("source_checks")
    if not isinstance(checks, list):
        errors.append("refresh record has no per-source provenance checks")
        checks = []
    by_key: dict[str, dict] = {}
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("key"), str):
            errors.append("malformed source-check record")
            continue
        by_key[check["key"]] = check
        url = check.get("url")
        if url:
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
                errors.append(f"non-official or insecure provenance URL for {check['key']}")
        try:
            checked = parse_utc(check.get("checked_at_utc"))
            check_age = (now - checked).total_seconds() / 3600
            if check_age < -0.05 or check_age > max_age_hours:
                errors.append(f"source check is stale or future-dated: {check['key']} ({check_age:.2f}h)")
        except (TypeError, ValueError):
            errors.append(f"missing/invalid source-check timestamp: {check['key']}")

    # Resolve declared-unreadable sources now, before any per-source verdict,
    # so that every later check can ask "is this source excused, and by what?"
    # EVERY source a declaration may name must be measured here, including S1
    # (COORDINATION.md section 74, T02): with S1 absent from this map,
    # `parse_ok.get("S1_season")` was None, so the section 69 anti-rot rule
    # could never fire for it and a declaration on S1 would have stayed live
    # even on the day the page became readable. The map now covers all five
    # keys the fetcher can write a capture for.
    parse_ok = {}
    for key, capture in (("S1_season", "_capture_S1_season.json"),
                         ("S2_train", "_capture_S2_train.json"),
                         ("S8_standings", "_capture_S8_standings.json"),
                         ("S9_team_traditional", "_capture_S9_team_traditional.json"),
                         ("S10_team_opponent", "_capture_S10_team_opponent.json")):
        try:
            parsed = read_json(os.path.join(base, "data/raw", capture))
        except (OSError, ValueError):
            parsed = {}
        parse_ok[key] = bool(isinstance(parsed, dict) and parsed.get("rows"))

    declared, rejected_declarations = live_declarations(base, now, by_key, parse_ok)
    accepted_declarations.extend(declared.values())
    for reason in rejected_declarations:
        # A rejected declaration is never silently dropped: the gate says so
        # and the original requirement still applies.
        warnings.append(f"declaration not applied: {reason}")

    # A declared source's own parse failure is an EXPECTED, EVIDENCED outcome,
    # not an unexplained error. It is moved from the blocking list to the
    # notes. Every undeclared failure still blocks, with the original wording.
    undeclared_failures = []
    for item in failures:
        key = item[0] if isinstance(item, (list, tuple)) and item else None
        if isinstance(key, str) and key.split(" ", 1)[0] in declared:
            warnings.append(f"declared source failed as expected: {key}: "
                            f"{item[1]} (evidence {declared[key.split(' ', 1)[0]]['evidence']})")
            continue
        undeclared_failures.append(item)
    if undeclared_failures:
        errors.append(f"fetcher reported {len(undeclared_failures)} failed "
                      f"source/parse checks")

    capture_names = {
        "S1_season": "_capture_S1_season.json",
        "S4_schedule": "_capture_S4_schedule.json",
        "S5_injury_index": "_capture_S5_injury_index.json",
        "S8_standings": "_capture_S8_standings.json",
        "S9_team_traditional": "_capture_S9_team_traditional.json",
        "S10_team_opponent": "_capture_S10_team_opponent.json",
    }
    for key in sorted(REQUIRED):
        check = by_key.get(key)
        if not check:
            errors.append(f"required official source not checked: {key}")
            continue
        if check.get("http_status") != 200:
            errors.append(f"required official source did not return HTTP 200: {key}")
        if not SHA256_RE.fullmatch(str(check.get("sha256", ""))):
            errors.append(f"required official source has no valid response SHA-256: {key}")
            continue
        path = os.path.join(base, "data/raw", capture_names[key])
        try:
            payload = read_json(path)
        except (OSError, ValueError):
            payload = None
        # A declared source never produces a rows-bearing capture (the fetcher
        # writes _capture_<key>.json only in its `if rows:` branch), so any
        # file that does exist for it is a stale page-level artifact from an
        # earlier run and its digest cannot match this run by construction.
        # The right proof for this run's response is the evidence record, whose
        # URL is checked below; the digest itself is already proven by the
        # source-check record above, which is this run's own hash of the bytes.
        if key in declared and not (isinstance(payload, dict) and payload.get("rows")):
            # The fetcher writes _capture_<key>.json only when rows PARSE
            # (engine/fetch_official.py, the `if rows:` branch); on a proved
            # unreadable source it writes the evidence record instead and
            # leaves the old capture untouched. Demanding the parsed payload
            # here would re-introduce the unsatisfiable predicate that this
            # whole mechanism exists to remove. The evidence record must still
            # prove the response itself: same URL, recorded in this run.
            evidence_rel = declared[key]["evidence"]
            try:
                evidence = read_json(os.path.join(base, evidence_rel))
            except (OSError, ValueError):
                errors.append(f"missing/invalid payload capture for {key} "
                              f"and its evidence record is unreadable")
                continue
            if evidence.get("source_url") != check.get("url"):
                errors.append(f"capture provenance URL mismatch for {key} "
                              f"(evidence {evidence_rel})")
            warnings.append(f"{key}: no parsed payload by design (declared "
                            f"unreadable); provenance verified against "
                            f"{evidence_rel}")
            continue
        if payload is None:
            errors.append(f"missing/invalid payload capture for {key}")
            continue
        if payload.get("source_url") != check.get("url"):
            errors.append(f"capture provenance URL mismatch for {key}")
        digest = payload.get("page_sha256")
        if digest != check.get("sha256"):
            errors.append(f"capture response digest does not match this run for {key}")

    injury = by_key.get("injury_pdf_probe", {})
    pdf_results = injury.get("results", [])
    if not pdf_results or pdf_results[0].get("http_status") != 200:
        errors.append("latest indexed injury PDF was not retrieved successfully")
    else:
        latest_pdf = pdf_results[0]
        if not SHA256_RE.fullmatch(str(latest_pdf.get("sha256", ""))):
            errors.append("latest indexed injury PDF has no valid SHA-256")
        if latest_pdf.get("pdf_valid") is not True:
            errors.append("latest indexed injury response is not verified as a PDF")
        parsed_pdf_url = urlparse(str(latest_pdf.get("url", "")))
        if parsed_pdf_url.scheme != "https" or parsed_pdf_url.hostname != "ak-static.cms.nba.com":
            errors.append("latest injury PDF does not have official NBA provenance")
        artifact_path = latest_pdf.get("artifact_path", "")
        if not artifact_path.startswith("data/raw/injury_pdfs/") or not artifact_path.endswith(".pdf"):
            errors.append("latest injury PDF is not persisted in the versioned PDF archive")
        else:
            absolute = os.path.join(base, artifact_path)
            try:
                with open(absolute, "rb") as pdf_file:
                    actual_sha = hashlib.sha256(pdf_file.read()).hexdigest()
                if actual_sha != latest_pdf.get("sha256"):
                    errors.append("archived injury PDF bytes do not match the fetch digest")
            except OSError:
                errors.append("latest injury PDF archive file is missing")

    # The results feed is queried for both today and yesterday on every run;
    # require both official NBA pages to be checked in this same fresh run.
    for date in (run_time.date(), run_time.date() - dt.timedelta(days=1)):
        key = f"results_{date.isoformat()}"
        check = by_key.get(key)
        if not check or check.get("http_status") != 200:
            errors.append(f"official results feed was not successfully checked for {date.isoformat()}")

    changed = record.get("changed", [])
    if not isinstance(changed, list):
        errors.append("refresh record has no valid changed-capture list")
        changed = []
    for item in changed:
        name = item.split(" ", 1)[0]
        if name in PROMOTION_SENSITIVE or name.startswith("results") or name.startswith("injury"):
            errors.append(f"capture changed and awaits verified promotion: {item}")
        elif name.startswith("S") and name not in {"S2_train"}:
            # Keep this conservative for any newly added first-party source.
            errors.append(f"official capture changed and awaits verified promotion: {item}")

    # Require structured captures and a provenance-bound promotion record for
    # every model input. A current page fetch alone never authorizes a rebuild.
    for rel, check_key in (("data/raw/_capture_S1_season.json", "S1_season"),
                           ("data/raw/_capture_S4_schedule.json", "S4_schedule")):
        path = os.path.join(base, rel)
        try:
            payload = read_json(path)
        except (OSError, ValueError):
            # A DECLARED source never produces a rows-bearing capture, so a
            # missing capture for one is its normal state and was already
            # handled by the evidence-record proof above (COORDINATION.md
            # section 74, T02). Previously this branch re-blocked the very
            # source the declaration had just excused, which made the
            # declaration mechanism a no-op for S1 and left the rebuild
            # unreachable for a second, independent reason.
            if check_key not in declared:
                errors.append(f"missing/invalid structured capture: {rel}")
            continue
        if check_key == "S1_season":
            # A complete table is 30 rows. The record's optional `row_count`
            # field is not part of the capture schema (engine/fetch_official.py
            # writes `rows`/`cols`), so testing it with `or` made this clause
            # true for EVERY well-formed capture ever written - a second latent
            # unsatisfiable predicate, fixed here together with the missing
            # declaration escape.
            complete = len(payload.get("rows") or []) == 30
            if not complete and check_key not in declared:
                # S1 is producible through two routes (the page's own parser
                # and the official stats.nba.com fallback), so a transient
                # parse failure must block rather than be declared around.
                errors.append("advanced team capture is not a complete 30-team table "
                              "(the page's own parser and the official stats.nba.com "
                              "fallback both failed this run)")
        if check_key == "S4_schedule" and not payload.get("games") and check_key not in declared:
            errors.append("official schedule capture has no parsed game IDs")

    # Advanced rows are parseable now, so compare every official row against
    # the season-to-date model snapshot rather than trusting a change list.
    # A DECLARED source has no capture to compare (see section 74): the
    # comparison is skipped for it and the declaration's evidence record is the
    # proof instead. The comparison still applies to every non-declared source.
    if "S1_season" in declared:
        pass
    else:
      try:
          adv_capture = read_json(os.path.join(base, "data/raw/_capture_S1_season.json"))
          adv_snapshot = read_json(os.path.join(base, "data/raw/team_advanced.json"))
          season_window = next(w for w in adv_snapshot.get("windows", [])
                               if w.get("window_id") == "season_to_date")
          cols = adv_capture.get("cols", [])
          snap_cols = adv_snapshot.get("cols", [])
          captured_rows = {row[0]: row for row in adv_capture.get("rows", [])}
          promoted_rows = {row[0]: row for row in season_window.get("rows", [])}
          if cols != snap_cols or captured_rows != promoted_rows or len(captured_rows) != 30:
              errors.append("advanced team capture does not exactly match the promoted season-to-date rows")
      except (OSError, ValueError, KeyError, StopIteration, TypeError, IndexError):
          errors.append("advanced team input cannot be compared with a complete promoted snapshot")

    def require_promotion(path: str, source_key: str, digest: str | None = None,
                          url: str | None = None) -> dict | None:
        try:
            payload = read_json(os.path.join(base, path))
        except (OSError, ValueError):
            errors.append(f"missing promoted source data: {path}")
            return None
        proof = payload.get("verification", {})
        check = by_key.get(source_key, {})
        if proof.get("verified") is not True:
            errors.append(f"promoted input has no explicit verification: {path}")
        expected_url = url if url is not None else check.get("url")
        if proof.get("source_url") != expected_url:
            errors.append(f"promoted input provenance URL is stale: {path}")
        expected = digest if digest is not None else check.get("sha256")
        if proof.get("source_sha256") != expected:
            errors.append(f"promoted input is not verified against this run's capture: {path}")
        try:
            parse_utc(proof.get("verified_at_utc"))
        except (TypeError, ValueError):
            errors.append(f"promoted input verification timestamp missing: {path}")
        return payload

    require_promotion("data/raw/schedule_upcoming.json", "S4_schedule")
    pdf_digest = pdf_results[0].get("sha256") if pdf_results else None
    pdf_url = pdf_results[0].get("url") if pdf_results else None
    require_promotion("data/raw/injuries.json", "injury_pdf_probe", pdf_digest, pdf_url)

    # Each current and previous-day official result capture must explicitly
    # reconcile to promoted finals before the builder may consume it.
    for date in (run_time.date(), run_time.date() - dt.timedelta(days=1)):
        rel = f"data/raw/_capture_results_{date.isoformat()}.json"
        try:
            result_capture = read_json(os.path.join(base, rel))
        except (OSError, ValueError):
            errors.append(f"missing official results capture: {rel}")
            continue
        comparison = result_capture.get("snapshot_comparison", {})
        if comparison.get("mismatches") or comparison.get("promotion_candidates") or comparison.get("committed_finals_missed"):
            errors.append(f"official results for {date.isoformat()} do not reconcile to promoted finals")
        if not all(isinstance(comparison.get(k), list) for k in
                   ("mismatches", "promotion_candidates", "committed_finals_missed")):
            errors.append(f"official results comparison is incomplete for {date.isoformat()}")

    promoted_paths = {
        "S8_standings": "data/raw/standings.json",
        "S9_team_traditional": "data/raw/team_traditional.json",
        "S10_team_opponent": "data/raw/team_opponent.json",
    }
    # Did each of these sources parse rows in this run? The capture files are
    # the fetcher's own output; a capture carrying rows means the page WAS
    # readable, which makes any standing declaration stale (see the helper).
    for key, relative_path in promoted_paths.items():
        if key in declared:
            # Deliberately NOT an error and NOT a pass on the data: this source
            # is proved unreadable, evidence-backed and time-limited, so the
            # gate does not require a snapshot nothing can produce. The
            # declaration is surfaced through `declarations` in the outcome.
            continue
        check = by_key.get(key, {})
        path = os.path.join(base, relative_path)
        try:
            promoted = read_json(path)
        except (OSError, ValueError):
            errors.append(f"{key} lacks structured, verified promoted data ({relative_path})")
            continue
        proof = promoted.get("verification", {})
        if not promoted.get("rows"):
            errors.append(f"{key} promoted data has no structured rows")
        if proof.get("verified") is not True:
            errors.append(f"{key} promotion has not passed explicit verification")
        if proof.get("source_url") != check.get("url"):
            errors.append(f"{key} promotion provenance URL does not match this run")
        if proof.get("source_sha256") != check.get("sha256"):
            errors.append(f"{key} promotion is not based on this run's official response")
        try:
            parse_utc(proof.get("verified_at_utc"))
        except (TypeError, ValueError):
            errors.append(f"{key} promotion is missing its verification timestamp")

    report = {
        "declarations_applied": accepted_declarations,
        "warnings": warnings,
        "rule": ("A declaration removes an unsatisfiable snapshot requirement "
                 "for a source proved unreadable by our own client. It never "
                 "promotes a value, and it is refused the moment the source "
                 "starts parsing or its expiry passes."),
    }
    return errors, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", default="data/raw/_last_refresh.json")
    parser.add_argument("--max-age-hours", type=float, default=10)
    parser.add_argument("--now", help="ISO-8601 UTC test clock")
    args = parser.parse_args()
    root = os.environ.get("NBA1_REPO_ROOT", os.getcwd())
    path = args.record if os.path.isabs(args.record) else os.path.join(root, args.record)
    report: dict = {"declarations_applied": [], "warnings": []}
    try:
        record = read_json(path)
    except (OSError, ValueError) as exc:
        errors = [f"cannot read refresh record: {exc}"]
    else:
        now = parse_utc(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
        errors, report = evaluate_with_report(record, now, args.max_age_hours)
    allowed = not errors
    for warning in report.get("warnings", []):
        print(f"NOTE: {warning}")
    for error in errors:
        print(f"BLOCK: {error}")
    if not errors:
        print("PASS: all freshness, provenance, integrity, and promotion gates passed")
        for entry in report.get("declarations_applied", []):
            print(f"PASS BY DECLARATION: {entry['source_key']} "
                  f"(expires {entry['expires_at_utc']}, evidence "
                  f"{entry['evidence']}, flag {entry.get('review_flag')})")
    # Persist the decision, not only the exit code: a green gate that ran on a
    # declaration must be distinguishable from a green gate that ran on fresh
    # promoted data, for anyone reading the repository later.
    try:
        gate_report = {
            "gate": "refresh freshness + provenance",
            "run_at_utc": (dt.datetime.now(dt.timezone.utc)
                           .strftime("%Y-%m-%dT%H:%M:%SZ")),
            "max_age_hours": args.max_age_hours,
            "ok": allowed,
            "blocking_errors": errors,
            "declarations_applied": report.get("declarations_applied", []),
            "warnings": report.get("warnings", []),
        }
        with open(os.path.join(root, "data/raw/_capture_gate_report.json"),
                  "w", encoding="utf-8") as stream:
            json.dump(gate_report, stream, indent=1)
            stream.write("\n")
    except OSError:
        pass

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"ok={'true' if allowed else 'false'}\n")
    return 0 if allowed else 1


if __name__ == "__main__":
    sys.exit(main())
