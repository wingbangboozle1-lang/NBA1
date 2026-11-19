#!/usr/bin/env python3
"""e3d25abc_verify_archive.py — audit every byte of the injury-report archive.

Session arena/e3d25abc-nba1, COORDINATION §68 Q06.

The brief's line this serves: *"Store every injury PDF with its timestamp and diff
consecutive reports to detect status changes"*, and *"every table row must have a
source link to an official site; if a value can't be confirmed, leave it blank and
flag it"*.  An archive claim is only worth as much as the check behind it, so this
re-reads **every** archived PDF and re-derives, from the bytes:

  * the SHA-256 — compared against the digest carried in the filename (full or
    16-hex-char prefix, both conventions exist in this archive) and against the
    sidecar's `sha256`;
  * the `%PDF-` signature in the first KiB;
  * the sidecar byte count vs the real length;
  * a retrieval timestamp under either key this repository has used
    (`retrieved_at_utc` from engine/fetch_official.py, `retrieved_utc` from the
    11/15 session captures) — a PDF with no stamp cannot satisfy "with its
    timestamp", so it is reported, not excused;
  * the source URL's host must be the official `ak-static.cms.nba.com`;
  * whether the edition is parsed by the repo's two-reader parser and whether the
    consecutive-diff records line up with the sorted edition order.

Output: verify/2026-11-19-e3d25abc/archive-audit.json (machine-readable) and
archive-audit.md (the human table).  Nothing outside verify/ is written here.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "data", "raw", "injury_pdfs")
DIFFS = os.path.join(ROOT, "data", "parsed", "injury_diffs")
OUT_DIR = os.path.join(ROOT, "verify", "2026-11-19-e3d25abc")

NAME_RE = re.compile(r"^(Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}(?:AM|PM))"
                     r"__([0-9a-f]{16,64})\.pdf$")
OFFICIAL_HOST = "https://ak-static.cms.nba.com/referee/injury/"


def edition_key(name: str):
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", name)
    if not m:
        return (name, 0)
    y, mo, d, hh, mm, ampm = m.groups()
    return (f"{y}-{mo}-{d}",
            (int(hh) % 12 + (12 if ampm == "PM" else 0)) * 100 + int(mm))


def audit_file(path: str) -> dict:
    base = os.path.basename(path)
    raw = open(path, "rb").read()
    digest = hashlib.sha256(raw).hexdigest()
    rec = {"file": base, "sha256_recomputed": digest, "bytes": len(raw),
           "pdf_signature": b"%PDF-" in raw[:1024]}
    m = NAME_RE.match(base)
    if not m:
        rec["filename_forms"] = False
        rec["problems"] = ["filename does not match <edition>__<hex digest>.pdf"]
        return rec
    rec["filename_forms"] = True
    edition, named = m.groups()
    rec["edition"] = edition
    rec["digest_length_in_filename"] = len(named)
    rec["filename_digest_is_full_sha256"] = len(named) == 64
    rec["filename_digest_matches_bytes"] = (
        digest == named if len(named) == 64 else digest.startswith(named))
    sc = path[:-4] + ".json"
    side = {}
    if os.path.exists(sc):
        try:
            side = json.load(open(sc, encoding="utf-8"))
        except json.JSONDecodeError:
            side = {"_unparseable": True}
    rec["sidecar_present"] = os.path.exists(sc)
    rec["sidecar_sha256_matches"] = side.get("sha256") == digest
    rec["sidecar_bytes_matches"] = side.get("bytes") in (None, len(raw))
    rec["retrieval_stamp"] = (side.get("retrieved_at_utc")
                              or side.get("retrieved_utc"))
    rec["retrieval_stamp_key"] = ("retrieved_at_utc" if side.get("retrieved_at_utc")
                                  else "retrieved_utc" if side.get("retrieved_utc")
                                  else None)
    url = side.get("source_url") or side.get("url") or ""
    rec["source_url"] = url or None
    rec["source_url_is_official_host"] = url.startswith(OFFICIAL_HOST)
    rec["edition_named_in_sidecar"] = (side.get("edition")
                                       or side.get("id", "").replace("pdf:", "")
                                       or None)   # an empty string means "absent"
    problems = []
    if not rec["filename_digest_matches_bytes"]:
        problems.append("filename digest does not match the recomputed SHA-256")
    if not rec["pdf_signature"]:
        problems.append("no %PDF- signature in the first KiB")
    if rec["sidecar_present"] and not rec["sidecar_sha256_matches"]:
        problems.append("sidecar sha256 disagrees with the bytes")
    if not rec["sidecar_bytes_matches"]:
        problems.append("sidecar byte count disagrees with the file")
    if not rec["retrieval_stamp"]:
        problems.append("no retrieval timestamp in any sidecar key")
    if not rec["source_url_is_official_host"]:
        problems.append(f"source URL is not on {OFFICIAL_HOST}: {url!r}")
    if rec["sidecar_present"] and rec["edition_named_in_sidecar"] not in (
            None, edition + ".pdf"):
        problems.append(f"sidecar names edition {rec['edition_named_in_sidecar']!r}, "
                        f"filename names {edition}.pdf")
    rec["problems"] = problems
    return rec


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(ARCHIVE, "*.pdf")),
                   key=lambda p: (edition_key(os.path.basename(p)),
                                  os.path.basename(p)))
    recs = [audit_file(p) for p in paths]

    by_day = {}
    for r in recs:
        day = edition_key(r["file"])[0]
        d = by_day.setdefault(day, {"files": 0, "editions": set(), "clean": 0,
                                    "truncated_digest_names": 0,
                                    "missing_retrieval_stamp": 0})
        d["files"] += 1
        d["editions"].add(r.get("edition"))
        d["clean"] += 0 if r["problems"] else 1
        if r.get("digest_length_in_filename") not in (None, 64):
            d["truncated_digest_names"] += 1
        if not r.get("retrieval_stamp"):
            d["missing_retrieval_stamp"] += 1
    for d in by_day.values():
        d["editions"] = len(d["editions"])

    # editions that exist under more than one filename
    seen = {}
    for r in recs:
        seen.setdefault(r.get("edition"), []).append(r["file"])
    dupes = {k: v for k, v in seen.items() if k and len(v) > 1}
    dupe_bytes_agree = {}
    for k, files in dupes.items():
        digests = {next(r["sha256_recomputed"] for r in recs
                        if r["file"] == f) for f in files}
        dupe_bytes_agree[k] = {"files": files, "identical_bytes": len(digests) == 1,
                               "digests": sorted(digests)}

    # the consecutive-diff chain: every diff must pair adjacent sorted editions
    order = sorted({r.get("edition") for r in recs if r.get("edition")},
                   key=edition_key)
    diff_files = sorted(glob.glob(os.path.join(DIFFS, "diff_*.json")))
    pair_ok, pair_bad, self_pairs = 0, [], []
    for p in diff_files:
        base = os.path.basename(p)[:-5]
        m = re.match(r"diff_(Injury-Report_[\d\-_]+(?:AM|PM))_to_(.+)$", base)
        if not m:
            pair_bad.append({"file": os.path.basename(p), "why": "unparsable name"})
            continue
        a, b = m.group(1), m.group(2)
        if a == b:
            self_pairs.append(os.path.basename(p))
            continue
        if b in order and a in order and order.index(b) == order.index(a) + 1:
            pair_ok += 1
        else:
            pair_bad.append({"file": os.path.basename(p),
                             "why": f"{a} -> {b} are not adjacent in the sorted "
                                    f"edition order"})
    edition_records = sorted(glob.glob(os.path.join(DIFFS, "editions", "*.json")))
    missing_parse_record = [e for e in order
                            if not os.path.exists(os.path.join(
                                DIFFS, "editions", e + ".json"))]

    out = {
        "title": "Injury-report PDF archive audit — byte-level, every file",
        "audited_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audited_by": "arena/e3d25abc-nba1 (scripts/e3d25abc_verify_archive.py)",
        "official_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "method": ("Every .pdf under data/raw/injury_pdfs/ is read, its SHA-256 "
                   "recomputed from the bytes, and compared with the digest in its "
                   "filename and in its sidecar. Nothing is sampled."),
        "totals": {
            "files": len(recs),
            "distinct_editions": len(order),
            "files_fully_clean": sum(1 for r in recs if not r["problems"]),
            "files_with_problems": sum(1 for r in recs if r["problems"]),
            "digest_in_filename_is_full_sha256": sum(
                1 for r in recs if r.get("filename_digest_is_full_sha256")),
            "digest_in_filename_truncated_to_16": sum(
                1 for r in recs if r.get("digest_length_in_filename") == 16),
            "edition_parse_records_published": len(edition_records),
            "diff_records_published": len(diff_files),
            "diff_pairs_adjacent": pair_ok,
            "diff_pairs_not_adjacent": len(pair_bad),
            "diff_pairs_self_to_self": len(self_pairs),
        },
        "per_day": {k: v for k, v in sorted(by_day.items())},
        "duplicate_edition_files": dupe_bytes_agree,
        "editions_without_parse_record": missing_parse_record,
        "non_adjacent_diffs": pair_bad[:12],
        "self_diffs": self_pairs,
        "problems": [{"file": r["file"], "problems": r["problems"]}
                     for r in recs if r["problems"]][:40],
        "problem_count_by_kind": {},
    }
    kinds = {}
    for r in recs:
        for pr in r["problems"]:
            kinds.setdefault(re.sub(r"https\S*|'[^']*'", "<value>", pr), 0)
            kinds[re.sub(r"https\S*|'[^']*'", "<value>", pr)] += 1
    out["problem_count_by_kind"] = kinds

    with open(os.path.join(OUT_DIR, "archive-audit.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")

    md = ["# Injury-report archive audit — 2026-11-19, session `arena/e3d25abc-nba1`",
          "",
          f"Audited {out['totals']['files']} archived PDFs "
          f"({out['totals']['distinct_editions']} distinct official editions) by "
          "recomputing every SHA-256 from the bytes. "
          f"Machine-readable: `verify/2026-11-19-e3d25abc/archive-audit.json`.",
          "",
          "| Day | Files | Editions | Fully clean | 16-hex truncated names | No retrieval stamp |",
          "| --- | --- | --- | --- | --- | --- |"]
    for k, v in sorted(by_day.items()):
        md.append(f"| {k} | {v['files']} | {v['editions']} | {v['clean']} | "
                  f"{v['truncated_digest_names']} | {v['missing_retrieval_stamp']} |")
    md += ["", "## Findings", ""]
    for kind, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
        md.append(f"* **{n}** file(s): {kind}")
    if dupe_editions := out["duplicate_edition_files"]:
        md += ["", "### Same official edition stored twice", ""]
        for k, v in dupe_editions.items():
            md.append(f"* `{k}`: {len(v['files'])} files, bytes identical: "
                      f"**{v['identical_bytes']}** — {', '.join('`'+f+'`' for f in v['files'])}")
    md += ["", "### Diff-chain shape", "",
           f"* {out['totals']['diff_pairs_adjacent']} published diff(s) pair two "
           f"adjacent editions in the sorted order;",
           f"* {out['totals']['diff_pairs_not_adjacent']} do not (listed in the JSON);",
           f"* {out['totals']['diff_pairs_self_to_self']} compare an edition with "
           "itself, which is only possible because the same edition is stored under "
           "two filenames;",
           f"* {len(missing_parse_record)} edition(s) have no parse record under "
           "`data/parsed/injury_diffs/editions/`."]
    with open(os.path.join(OUT_DIR, "archive-audit.md"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    t = out["totals"]
    print(f"files {t['files']} | editions {t['distinct_editions']} | clean "
          f"{t['files_fully_clean']} | problems {t['files_with_problems']} | "
          f"truncated-name files {t['digest_in_filename_truncated_to_16']} | "
          f"self-diffs {t['diff_pairs_self_to_self']} | editions w/o parse record "
          f"{len(missing_parse_record)}")
    for kind, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>4}  {kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
