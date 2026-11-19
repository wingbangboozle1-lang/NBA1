#!/usr/bin/env python3
"""Pure helpers for auditing row-level source links in published HTML.

This module checks the presence of a direct, HTTPS NBA link in each static
(non-script) table row. It deliberately does not fetch URLs or claim that a
linked page confirms the row's value. Rows without an NBA source stay marked as
unverified; no link or value is inferred.
"""
from __future__ import annotations

import bisect
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
HREF_RE = re.compile(r"<a\b[^>]*\bhref\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def is_official_nba_https(url: str) -> bool:
    """Return whether *url* is an HTTPS URL on nba.com or a subdomain.

    Host suffix matching is boundary-aware: ``nba.com.example.org`` is not an
    official NBA host. Protocol-relative URLs and plain HTTP are not accepted
    as explicit HTTPS provenance.
    """
    parsed = urlparse(html.unescape(str(url)).strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme.lower() == "https" and (host == "nba.com" or host.endswith(".nba.com"))


def _line_starts(text: str) -> list[int]:
    return [0] + [index + 1 for index, char in enumerate(text) if char == "\n"]


def _line_at(offset: int, starts: list[int]) -> int:
    return bisect.bisect_right(starts, offset)


def _mask_scripts(match: re.Match[str]) -> str:
    """Hide script markup while retaining offsets and source line numbers."""
    return "".join("\n" if char == "\n" else " " for char in match.group(0))


def _external_links(row: str) -> list[str]:
    links: list[str] = []
    for match in HREF_RE.finditer(row):
        href = html.unescape(match.group(2)).strip()
        parsed = urlparse(href)
        if parsed.scheme.lower() in {"http", "https"} or href.startswith("//"):
            if href not in links:
                links.append(href)
    return links


def _row_record(row_html: str, file: str, line: int, *, dynamic: bool = False) -> dict:
    links = _external_links(row_html)
    nba_links = [url for url in links if is_official_nba_https(url)]
    if dynamic:
        status = "not_evaluated_dynamic_template"
        review_status = "rendered_dom_audit_required"
        reason = "The row is inside a script; its final source link depends on runtime data and was not evaluated."
        official_links = []
        literal_nba_candidates = nba_links
    elif nba_links:
        status = "official_link_present_not_value_verified"
        review_status = "value_not_verified"
        reason = "A direct HTTPS NBA link is present; the linked page/value was not fetched or compared."
        official_links = nba_links
        literal_nba_candidates = []
    elif links:
        status = "unverified_non_nba_or_insecure_link_only"
        review_status = "official_source_review_required"
        reason = "The row has external link(s), but none is a direct HTTPS NBA source."
        official_links = []
        literal_nba_candidates = []
    else:
        status = "unverified_no_external_source_link"
        review_status = "official_source_review_required"
        reason = "The row has no external source link."
        official_links = []
        literal_nba_candidates = []

    text = html.unescape(TAG_RE.sub(" ", row_html))
    text = " ".join(text.split())
    return {
        "file": file,
        "line": line,
        "status": status,
        "review_status": review_status,
        "reason": reason,
        "row_text": text[:800],
        "external_links": links,
        "official_nba_links": official_links,
        "literal_official_nba_link_candidates": literal_nba_candidates,
        "dynamic_template": dynamic,
    }


def scan_html(text: str, file: str = "<memory>") -> dict:
    """Classify static table rows and separately count rows inside scripts.

    HTML strings inside JavaScript templates are not present in the static DOM;
    they are recorded as ``dynamic_template_rows`` and never treated as either
    sourced or unsourced. A rendered-DOM check is required to verify their final
    links.
    """
    original = text
    starts = _line_starts(original)
    script_matches = list(SCRIPT_RE.finditer(original))
    dynamic_rows: list[dict] = []

    for script in script_matches:
        body = script.group(0)
        if re.search(r"<script\b[^>]*\btype\s*=\s*[\"']application/json[\"']", body, re.IGNORECASE):
            continue
        for match in ROW_RE.finditer(body):
            row_html = match.group(0)
            if re.search(r"<th\b", row_html, re.IGNORECASE):
                continue
            dynamic_rows.append(_row_record(
                row_html, file, _line_at(script.start() + match.start(), starts), dynamic=True
            ))

    static_html = SCRIPT_RE.sub(_mask_scripts, original)
    static_rows: list[dict] = []
    for match in ROW_RE.finditer(static_html):
        row_html = match.group(0)
        if re.search(r"<th\b", row_html, re.IGNORECASE):
            continue
        static_rows.append(_row_record(row_html, file, _line_at(match.start(), starts)))

    official = sum(r["status"] == "official_link_present_not_value_verified" for r in static_rows)
    non_nba = sum(r["status"] == "unverified_non_nba_or_insecure_link_only" for r in static_rows)
    no_link = sum(r["status"] == "unverified_no_external_source_link" for r in static_rows)
    return {
        "file": file,
        "static_rows": static_rows,
        "dynamic_template_rows": dynamic_rows,
        "counts": {
            "static_rows": len(static_rows),
            "official_link_present_not_value_verified": official,
            "unverified_non_nba_or_insecure_link_only": non_nba,
            "unverified_no_external_source_link": no_link,
            "dynamic_template_rows_not_rendered": len(dynamic_rows),
        },
    }


def _ignored_path(path: Path) -> bool:
    ignored = {".git", "node_modules", ".venv", "venv", "dist", "build", "coverage"}
    return any(part in ignored for part in path.parts)


def audit_repository(root: str | Path, generated_at_utc: str | None = None) -> dict:
    """Audit every HTML file under *root* and return a JSON-serializable report."""
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise NotADirectoryError(str(root_path))
    if generated_at_utc is None:
        generated_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    file_rows: list[dict] = []
    unverified_rows: list[dict] = []
    dynamic_rows: list[dict] = []
    totals = {
        "html_files": 0,
        "static_rows": 0,
        "official_link_present_not_value_verified": 0,
        "unverified_non_nba_or_insecure_link_only": 0,
        "unverified_no_external_source_link": 0,
        "dynamic_template_rows_not_rendered": 0,
    }

    for path in sorted(root_path.rglob("*.html")):
        if _ignored_path(path):
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        rel = path.relative_to(root_path).as_posix()
        result = scan_html(text, rel)
        counts = result["counts"]
        totals["html_files"] += 1
        for key in totals:
            if key != "html_files":
                totals[key] += counts.get(key, 0)
        file_rows.append({
            "file": rel,
            "sha256": hashlib.sha256(raw).hexdigest(),
            **counts,
        })
        for row in result["static_rows"]:
            if row["status"] != "official_link_present_not_value_verified":
                unverified_rows.append(row)
        dynamic_rows.extend(result["dynamic_template_rows"])

    return {
        "title": "Static HTML table-row source-link audit",
        "generated_at_utc": generated_at_utc,
        "scope": "Every .html file under the repository root, excluding Git and dependency/build directories.",
        "method": {
            "official_link_rule": "A static data row is link-present only if it contains an anchor to an HTTPS host equal to nba.com or ending in .nba.com.",
            "value_verification": "Not performed. Presence of a source URL does not prove the URL was reachable or that its current value matches the row.",
            "unverified_rule": "Rows without a qualifying official NBA link are listed with the existing external links (if any); no missing link or value is inferred.",
            "dynamic_content": "Rows inside script blocks are listed separately and are not classified until a rendered-DOM source audit evaluates their output.",
            "network_access": "No outbound requests were made by this audit.",
        },
        "counts": totals,
        "files": file_rows,
        "unverified_rows": unverified_rows,
        "dynamic_template_rows": dynamic_rows,
    }


def write_report(report: dict, json_path: str | Path, markdown_path: str | Path) -> None:
    json_target = Path(json_path)
    md_target = Path(markdown_path)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_target.write_text(render_markdown(report), encoding="utf-8")


def _md_cell(value: object) -> str:
    escaped = html.escape(str(value), quote=False)
    return escaped.replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


def _md_existing_link(url: str) -> str:
    """Render an already-present external href as a review link, without changing it."""
    href = html.escape(url, quote=True)
    label = html.escape(url, quote=False).replace("|", "&#124;")
    return f'<a href="{href}" rel="noopener noreferrer">{label}</a>'


def render_markdown(report: dict) -> str:
    counts = report["counts"]
    out = [
        "# Static HTML table-row source-link audit",
        "",
        f"**Generated (UTC):** `{report['generated_at_utc']}`",
        "",
        "## Result",
        "",
        "| Measure | Count |",
        "|---|---:|",
        f"| HTML files scanned | {counts['html_files']} |",
        f"| Static data rows scanned | {counts['static_rows']} |",
        f"| Rows with a direct HTTPS NBA link (link presence only) | {counts['official_link_present_not_value_verified']} |",
        f"| Unverified: non-NBA or insecure link only | {counts['unverified_non_nba_or_insecure_link_only']} |",
        f"| Unverified: no external source link | {counts['unverified_no_external_source_link']} |",
        f"| Dynamic table-row templates not rendered/audited | {counts['dynamic_template_rows_not_rendered']} |",
        "",
        "> **Important:** an NBA link is not proof the underlying value was re-fetched or verified. This audit made no network requests. Rows without a direct official NBA link are listed below and remain unverified; no source was guessed.",
        "",
        "## Per-file coverage and content hashes",
        "",
        "| File | Static rows | NBA-link-present | Non-NBA/insecure only | No external link | Dynamic templates | SHA-256 of HTML |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in report["files"]:
        out.append(
            f"| `{_md_cell(item['file'])}` | {item['static_rows']} | "
            f"{item['official_link_present_not_value_verified']} | "
            f"{item['unverified_non_nba_or_insecure_link_only']} | "
            f"{item['unverified_no_external_source_link']} | "
            f"{item['dynamic_template_rows_not_rendered']} | `{item['sha256']}` |"
        )

    out += ["", "## Unverified static table rows", ""]
    if not report["unverified_rows"]:
        out.append("No static table rows lacked a direct HTTPS NBA link in this snapshot.")
    else:
        out += [
            "Each row below is unresolved for official NBA provenance. Existing non-NBA links are shown but are not treated as NBA evidence.",
            "",
            "| File:line | Link classification | Review status | Rendered row text | Existing external links |",
            "|---|---|---|---|---|",
        ]
        for row in report["unverified_rows"]:
            links = "<br>".join(_md_existing_link(url) for url in row["external_links"]) or "—"
            out.append(
                f"| `{_md_cell(row['file'])}:{row['line']}` | `{row['status']}` | "
                f"`{row['review_status']}` | {_md_cell(row['row_text'])} | {links} |"
            )

    out += ["", "## Dynamic row templates requiring rendered-DOM review", ""]
    if not report["dynamic_template_rows"]:
        out.append("No table-row markup was found inside script blocks in this snapshot.")
    else:
        out += [
            "These are source-code templates, not rendered rows. Final links are data-dependent; any literal NBA URL below is only a candidate, not evidence that the runtime row uses it.",
            "",
            "| File:line | Link classification | Review status | Template text | Literal HTTPS NBA link candidates |",
            "|---|---|---|---|---|",
        ]
        for row in report["dynamic_template_rows"]:
            candidates = "<br>".join(
                _md_existing_link(url) for url in row["literal_official_nba_link_candidates"]
            ) or "—"
            out.append(
                f"| `{_md_cell(row['file'])}:{row['line']}` | `{row['status']}` | "
                f"`{row['review_status']}` | {_md_cell(row['row_text'])} | {candidates} |"
            )
    return "\n".join(out) + "\n"
