#!/usr/bin/env python3
"""Unit tests for the strict, no-fetch row-source audit."""
import tempfile
import unittest
from pathlib import Path

try:
    from source_row_audit import audit_repository, is_official_nba_https, render_markdown, scan_html, write_report
except ImportError:
    from scripts.source_row_audit import audit_repository, is_official_nba_https, render_markdown, scan_html, write_report


class OfficialHostTests(unittest.TestCase):
    def test_accepts_nba_domain_and_subdomains_over_https(self):
        for url in (
            "https://nba.com/games",
            "https://www.nba.com/game/example",
            "https://official.nba.com/injury-report/",
            "https://ak-static.cms.nba.com/report.pdf",
            "https://statsdmz.nba.com/pdfs/boxscore.pdf",
        ):
            with self.subTest(url=url):
                self.assertTrue(is_official_nba_https(url))

    def test_rejects_http_lookalikes_and_suffix_attacks(self):
        for url in (
            "http://www.nba.com/games",
            "https://nba.com.example.org/games",
            "https://notnba.com/games",
            "//www.nba.com/games",
            "https://github.com/wingbangboozle1-lang/NBA1",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_official_nba_https(url))


class StaticRowScanTests(unittest.TestCase):
    def setUp(self):
        self.html = """<!doctype html>
<table>
<thead><tr><th>Metric</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Verified-link row</td><td><a href="https://www.nba.com/games?date=2026-11-19">NBA</a></td></tr>
<tr><td>Repository-only row</td><td><a href="https://github.com/example/project">repo</a></td></tr>
<tr><td>Missing-source row</td><td>unverified</td></tr>
</tbody>
</table>
<script>
const row = `<tr><td>Runtime row</td><td><a href="https://www.nba.com/games">NBA</a></td></tr>`;
</script>
"""

    def test_line_numbers_and_link_status_are_preserved(self):
        result = scan_html(self.html, "fixture.html")
        rows = result["static_rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["line"] for row in rows], [5, 6, 7])
        self.assertEqual(rows[0]["status"], "official_link_present_not_value_verified")
        self.assertEqual(rows[0]["official_nba_links"], ["https://www.nba.com/games?date=2026-11-19"])
        self.assertEqual(rows[1]["status"], "unverified_non_nba_or_insecure_link_only")
        self.assertEqual(rows[1]["external_links"], ["https://github.com/example/project"])
        self.assertEqual(rows[2]["status"], "unverified_no_external_source_link")
        self.assertIn("Missing-source row", rows[2]["row_text"])

    def test_script_template_is_separate_not_counted_as_static_or_verified(self):
        result = scan_html(self.html, "fixture.html")
        self.assertEqual(result["counts"]["static_rows"], 3)
        self.assertEqual(result["counts"]["dynamic_template_rows_not_rendered"], 1)
        dynamic = result["dynamic_template_rows"][0]
        self.assertTrue(dynamic["dynamic_template"])
        self.assertEqual(dynamic["line"], 11)
        self.assertEqual(dynamic["status"], "not_evaluated_dynamic_template")
        self.assertEqual(dynamic["official_nba_links"], [])
        self.assertEqual(dynamic["literal_official_nba_link_candidates"], ["https://www.nba.com/games"])

    def test_header_rows_are_not_data_rows(self):
        result = scan_html(self.html, "fixture.html")
        self.assertEqual(result["counts"]["static_rows"], 3)

    def test_json_script_payload_is_not_misclassified_as_a_row_template(self):
        payload = '<script type="application/json">{"html":"<tr><td>data</td></tr>"}</script>'
        result = scan_html(payload, "fixture.html")
        self.assertEqual(result["counts"]["static_rows"], 0)
        self.assertEqual(result["counts"]["dynamic_template_rows_not_rendered"], 0)


class RepositoryReportTests(unittest.TestCase):
    def test_report_writes_hashes_and_explicit_unverified_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                "<table><tbody><tr><td>unknown</td></tr></tbody></table>\n",
                encoding="utf-8",
            )
            report = audit_repository(root, generated_at_utc="2026-11-19T07:00:00Z")
            self.assertEqual(report["counts"]["html_files"], 1)
            self.assertEqual(report["counts"]["static_rows"], 1)
            self.assertEqual(report["counts"]["unverified_no_external_source_link"], 1)
            self.assertEqual(report["unverified_rows"][0]["file"], "index.html")
            self.assertEqual(len(report["files"][0]["sha256"]), 64)
            self.assertIn("No outbound requests", report["method"]["network_access"])

            json_path = root / "out/report.json"
            markdown_path = root / "out/report.md"
            write_report(report, json_path, markdown_path)
            self.assertTrue(json_path.is_file())
            md = markdown_path.read_text(encoding="utf-8")
            self.assertIn("Unverified static table rows", md)
            self.assertIn("index.html:1", md)
            self.assertIn("no external source link", md)

    def test_existing_non_nba_href_remains_clickable_for_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<table><tbody><tr><td>review</td><td><a href="https://github.com/example/project">repo</a></td></tr></tbody></table>',
                encoding="utf-8",
            )
            report = audit_repository(root, generated_at_utc="2026-11-19T07:00:00Z")
            markdown = render_markdown(report)
            self.assertIn('href="https://github.com/example/project"', markdown)
            self.assertIn("unverified_non_nba_or_insecure_link_only", markdown)

    def test_nested_dependency_directories_are_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "node_modules/package").mkdir(parents=True)
            (root / "node_modules/package/noise.html").write_text("<tr><td>noise</td></tr>")
            (root / "live.html").write_text("<tr><td>live</td></tr>")
            report = audit_repository(root, generated_at_utc="2026-11-19T07:00:00Z")
            self.assertEqual(report["counts"]["html_files"], 1)
            self.assertEqual(report["files"][0]["file"], "live.html")


if __name__ == "__main__":
    unittest.main(verbosity=2)
