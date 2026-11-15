#!/usr/bin/env python3
"""build_injury_archive.py — materialise the injury-report archive.

Every edition that has been read from the official NBA injury-report index is
stored under data/injury_reports/<edition_id>/ with:

  edition.json      the edition's own metadata (revision stamp, publication
                    time, retrieval time, official URLs, row hash, row counts)
  rows.json         the verbatim row transcription of that edition
  diff_vs_<prev>.json   the row-by-row diff against the previous edition

The index (data/injury_reports/README.md) lists every edition with its
official URL so a reviewer can open the source document for any row.

Binary PDF storage: NOT AVAILABLE in this sandbox. The only network route to
ak-static.cms.nba.com is the text-extraction fetch channel, and the shell
egress allowlist has no route to that host, so the PDF bytes cannot be
written to disk here. The archive therefore stores the extracted rows plus
the SHA-256 of the transcribed row text, and every row carries the official
PDF URL. This is stated in the index and in every edition.json - the archive
is not represented as a binary archive.

Run: python3 verify/2026-11-15-49f70042/build_injury_archive.py
"""
import datetime
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OFF = os.path.join(ROOT, "data", "official")
ARCH = os.path.join(ROOT, "data", "injury_reports")
INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

# edition_id -> (edition json, [diff file basenames])
# Each diff file is stored with the edition it produced (the "to" edition).
EDITIONS = [
    ("2026-11-14_0130PM", "injury_2026-11-14_0130PM.json", []),
    ("2026-11-15_0615AM", "injury_2026-11-15_0615AM.json",
     ["injury_diff_2026-11-14_0130PM_to_2026-11-15_0615AM.json"]),
    ("2026-11-15_0615PM", "injury_2026-11-15_0615PM.json",
     ["injury_diff_2026-11-15_0615AM_to_2026-11-15_0615PM.json"]),
]

BINARY_NOTE = (
    "The binary PDF is NOT archived in this sandbox: the shell egress allowlist has no "
    "route to ak-static.cms.nba.com, and the only available route to it is the "
    "text-extraction fetch channel, which returns extracted text rather than bytes. "
    "What is stored is the verbatim row transcription, the SHA-256 of the transcribed "
    "row text, the official PDF URL on every row, the edition revision stamp and the "
    "retrieval time. This archive is therefore a text archive and is not represented "
    "as a binary one."
)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    os.makedirs(ARCH, exist_ok=True)
    built = []
    for ed_id, ed_file, diffs in EDITIONS:
        src = os.path.join(OFF, ed_file)
        doc = json.load(open(src, encoding="utf-8"))
        d = os.path.join(ARCH, ed_id)
        os.makedirs(d, exist_ok=True)

        rows = doc.get("rows", [])
        revision = (doc.get("revision") or doc.get("revision_time_et")
                    or doc.get("edition"))
        retrieved = (doc.get("retrieved_utc") or doc.get("captured_at_utc"))
        counts = doc.get("row_counts") or {}
        if not counts:
            counts = {"rows_total": doc.get("row_count", len(rows))}
            counts.setdefault("player_rows", len([r for r in rows if r.get("player")]))
            counts.setdefault("not_yet_submitted_blocks",
                              len([r for r in rows
                                   if r.get("status") == "NOT YET SUBMITTED"]))
            counts.setdefault("rows_with_inherited_team",
                              len([r for r in rows if r.get("team_inherited")]))
        edition = {
            "edition_id": ed_id,
            "revision": revision,
            "edition_published_utc": doc.get("edition_published_utc"),
            "retrieved_utc": retrieved,
            "retrieval_window_utc": doc.get("retrieval_window_utc"),
            "source_url": doc.get("source_url"),
            "edition_index_url": doc.get("edition_index_url") or doc.get("index_url", INDEX_URL),
            "captured_by": doc.get("captured_by"),
            "capture_method": doc.get("capture_method") or doc.get("rows_note") or doc.get("note"),
            "binary_pdf_stored": False,
            "binary_pdf_note": doc.get("binary_pdf_note", BINARY_NOTE),
            "rows_sha256": doc.get("rows_sha256"),
            "row_counts": counts,
            "game_dates_in_edition": doc.get("game_dates_in_edition")
                or sorted({r.get("game_date") for r in rows if r.get("game_date")}),
            "extraction_artefacts": doc.get("extraction_artefacts", []),
            "rows_file": "rows.json",
            "diffs": [],
        }
        for df in diffs:
            dsrc = os.path.join(OFF, df)
            if not os.path.exists(dsrc):
                continue
            dd = json.load(open(dsrc, encoding="utf-8"))
            name = "diff_vs_" + df.split("_to_")[0].replace("injury_diff_", "").replace("injury_", "") + ".json"
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                json.dump(dd, fh, indent=1, ensure_ascii=False)
            edition["diffs"].append({
                "file": name,
                "from_edition": dd.get("from_edition", {}).get("edition_id"),
                "to_edition": dd.get("to_edition", {}).get("edition_id"),
                "counts": dd.get("counts"),
                "sha256": sha256_file(os.path.join(d, name)),
            })

        with open(os.path.join(d, "edition.json"), "w", encoding="utf-8") as fh:
            json.dump(edition, fh, indent=1, ensure_ascii=False)
        with open(os.path.join(d, "rows.json"), "w", encoding="utf-8") as fh:
            json.dump({"edition_id": ed_id,
                       "revision": revision,
                       "retrieved_utc": retrieved,
                       "source_url": doc.get("source_url"),
                       "rows": doc.get("rows", [])},
                      fh, indent=1, ensure_ascii=False)
        built.append({
            "edition_id": ed_id,
            "revision": revision,
            "source_url": doc.get("source_url"),
            "retrieved_utc": retrieved,
            "row_counts": counts,
            "diffs": [x["file"] for x in edition["diffs"]],
            "status_change_counts": [x["counts"]["status_changes"] for x in edition["diffs"]],
        })
        print("archived", ed_id, counts)

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Injury-report archive",
        "",
        "Every edition of the official NBA injury report that has been read from the",
        "official index <%s> is archived here, one directory per edition." % INDEX_URL,
        "",
        "Each edition directory holds:",
        "",
        "| File | What it is |",
        "| --- | --- |",
        "| `edition.json` | the edition's metadata: revision stamp, publication time, retrieval time, official URL, row hash, row counts, extraction artefacts |",
        "| `rows.json` | the verbatim row transcription of that edition |",
        "| `diff_vs_*.json` | the row-by-row diff against the previous edition |",
        "",
        "**Binary PDFs are not archived here.** " + BINARY_NOTE,
        "",
        "## Editions",
        "",
        "| Edition (UTC id) | Revision stamp | Rows | Player rows | Team blocks | Status changes vs previous | Official source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for b in built:
        rc = b["row_counts"] or {}
        ch = b["status_change_counts"][0] if b["status_change_counts"] else "-"
        lines.append("| `%s` | %s | %s | %s | %s | %s | [PDF](%s) |" % (
            b["edition_id"], b["revision"], rc.get("rows_total"), rc.get("player_rows"),
            rc.get("not_yet_submitted_blocks"), ch, b["source_url"]))
    lines += [
        "",
        "## Files",
        "",
    ]
    for b in built:
        lines.append("### %s" % b["edition_id"])
        lines.append("")
        lines.append("- `data/injury_reports/%s/edition.json`" % b["edition_id"])
        lines.append("- `data/injury_reports/%s/rows.json`" % b["edition_id"])
        for f in b["diffs"]:
            lines.append("- `data/injury_reports/%s/%s`" % (b["edition_id"], f))
        lines.append("- official source: %s" % b["source_url"])
        lines.append("")
    lines.append("_Archive index rebuilt %s by verify/2026-11-15-49f70042/build_injury_archive.py._" % now)
    lines.append("")
    with open(os.path.join(ARCH, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("wrote", os.path.join(ARCH, "README.md"))


if __name__ == "__main__":
    main()
