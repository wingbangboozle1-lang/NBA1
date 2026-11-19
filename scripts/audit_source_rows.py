#!/usr/bin/env python3
"""Write a line-numbered, no-inference audit of HTML table-row source links.

Usage:
  python3 scripts/audit_source_rows.py
  python3 scripts/audit_source_rows.py --root /path/to/repo --json-out /tmp/rows.json --md-out /tmp/rows.md

The command reports missing direct HTTPS NBA links but does not change site data,
fill links, fetch official pages, or claim that existing links verify values.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

try:  # Direct script execution (the CI and documented usage)
    from source_row_audit import audit_repository, write_report
except ImportError:  # Import as scripts.audit_source_rows in tests/tools
    from scripts.source_row_audit import audit_repository, write_report

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root to scan")
    parser.add_argument("--json-out", type=Path,
                        default=ROOT / "audit/source_row_audit_2026-11-19_d2a412c8.json")
    parser.add_argument("--md-out", type=Path,
                        default=ROOT / "audit/source_row_audit_2026-11-19_d2a412c8.md")
    args = parser.parse_args()

    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = audit_repository(args.root, generated_at_utc=generated)
    write_report(report, args.json_out, args.md_out)
    counts = report["counts"]
    unverified = counts["unverified_non_nba_or_insecure_link_only"] + counts["unverified_no_external_source_link"]
    print(f"HTML files scanned: {counts['html_files']}")
    print(f"Static table rows: {counts['static_rows']}")
    print(f"Direct HTTPS NBA links present (link presence only): {counts['official_link_present_not_value_verified']}")
    print(f"Unverified static rows: {unverified} "
          f"({counts['unverified_non_nba_or_insecure_link_only']} non-NBA/insecure-only; "
          f"{counts['unverified_no_external_source_link']} no external link)")
    print(f"Dynamic row templates not rendered/audited: {counts['dynamic_template_rows_not_rendered']}")
    print(f"JSON report: {args.json_out}")
    print(f"Markdown report: {args.md_out}")
    print("No network requests were made; link presence is not value verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
