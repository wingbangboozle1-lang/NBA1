"""Fail-closed freshness/provenance gate for scheduled refresh builds.

The fetcher deliberately stores observations as capture-only artifacts. This
module permits builders to run only when every required official source was
successfully checked in this run, the check is recent, and no capture changed
since its last verified promotion. A changed capture is never treated as an
approved model input merely because it came from an official URL.
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


def parse_utc(value: str) -> dt.datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def evaluate(record: dict, now: dt.datetime, max_age_hours: float = 10) -> list[str]:
    errors: list[str] = []
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
    elif failures:
        errors.append(f"fetcher reported {len(failures)} failed source/parse checks")

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
            errors.append(f"missing/invalid structured capture: {rel}")
            continue
        if check_key == "S1_season" and (payload.get("row_count") != 30 or len(payload.get("rows", [])) != 30):
            errors.append("advanced team capture is not a complete 30-team table")
        if check_key == "S4_schedule" and not payload.get("games"):
            errors.append("official schedule capture has no parsed game IDs")

    # Advanced rows are parseable now, so compare every official row against
    # the season-to-date model snapshot rather than trusting a change list.
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
    for key, relative_path in promoted_paths.items():
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

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", default="data/raw/_last_refresh.json")
    parser.add_argument("--max-age-hours", type=float, default=10)
    parser.add_argument("--now", help="ISO-8601 UTC test clock")
    args = parser.parse_args()
    root = os.environ.get("NBA1_REPO_ROOT", os.getcwd())
    path = args.record if os.path.isabs(args.record) else os.path.join(root, args.record)
    try:
        record = read_json(path)
    except (OSError, ValueError) as exc:
        errors = [f"cannot read refresh record: {exc}"]
    else:
        now = parse_utc(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
        errors = evaluate(record, now, args.max_age_hours)
    allowed = not errors
    for error in errors:
        print(f"BLOCK: {error}")
    if not errors:
        print("PASS: all freshness, provenance, integrity, and promotion gates passed")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"ok={'true' if allowed else 'false'}\n")
    return 0 if allowed else 1


if __name__ == "__main__":
    sys.exit(main())
