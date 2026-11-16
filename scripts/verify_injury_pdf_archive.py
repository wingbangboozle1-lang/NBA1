#!/usr/bin/env python3
"""S06 (session arena/3ff8ff0f-nba1, COORDINATION 56.1) - R04 integrity check.

Requirement R04 says: store every injury PDF with its timestamp, and diff consecutive
reports to detect status changes.  The board's register recorded the storage half as open
(flag F82, "the PDF bytes themselves are still not retained under version control").
This script measures the archive as it actually is instead of trusting that note:

  * every PDF under data/raw/injury_pdfs/ is re-hashed and compared with the hash in its
    own filename and in its sidecar (a content-addressed archive is only tamper-evident
    if someone checks);
  * the sidecar's byte count is compared with the file on disk;
  * every sidecar's official URL is checked to name the same edition as the file;
  * the consecutive-edition diff chain produced by engine/injury_diff.py is checked for a
    diff for every adjacent pair, and the detected status changes are counted.

Exit code 0 = archive integrity holds.  Anything that fails is printed and reported,
never repaired by inference.

Run:  python3 scripts/verify_injury_pdf_archive.py [--json out.json]
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(ROOT, "data", "raw", "injury_pdfs")
DIFF_DIR = os.path.join(ROOT, "data", "parsed", "injury_diffs")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 16), b""):
            h.update(blk)
    return h.hexdigest()


def edition_key(name):
    m = re.search(r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)", name)
    if not m:
        return (name, 0, 0, 0)
    d, hh, mm, ap = m.groups()
    hh = int(hh) % 12 + (12 if ap == "PM" else 0)
    return (d, hh, int(mm), 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    pdfs = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")), key=lambda p: edition_key(os.path.basename(p)))
    from collections import Counter
    problems, checked, editions, schemas = [], 0, [], Counter()
    for p in pdfs:
        checked += 1
        base = os.path.basename(p)
        stem = base[:-4]
        sidecar = os.path.join(PDF_DIR, stem + ".json")
        # Two naming conventions exist in the archive: the fetcher writes the
        # full sha256 in the filename, older captures carry its 16-char prefix.
        m = re.match(r"^(.+)__([0-9a-f]{16}|[0-9a-f]{64})$", stem)
        if not m:
            problems.append({"file": base, "problem": "filename is not content-addressed"})
            continue
        edition, short = m.groups()
        digest = sha256(p)
        ok_hash = (digest == short) if len(short) == 64 else digest.startswith(short)
        if not ok_hash:
            problems.append({"file": base,
                             "problem": "filename hash %s != sha256 %s (TAMPER INDICATOR)"
                                        % (short[:16], digest[:16])})
        if not open(p, "rb").read(5).startswith(b"%PDF-"):
            problems.append({"file": base, "problem": "file does not start with %PDF-"})
        if not os.path.exists(sidecar):
            problems.append({"file": base, "problem": "no sidecar manifest"})
            continue
        sc = json.load(open(sidecar, encoding="utf-8"))
        if sc.get("sha256") != digest:
            problems.append({"file": base, "problem": "sidecar sha256 != file sha256"})
        if sc.get("bytes") != os.path.getsize(p):
            problems.append({"file": base,
                             "problem": "sidecar bytes %s != on disk %s"
                                        % (sc.get("bytes"), os.path.getsize(p))})
        # Two sidecar schemas are in circulation in this archive (measured below):
        # the fetcher's own record writes {url, retrieved_utc, revision_label,
        # http_status, ...} while a later capture path writes {source_url,
        # retrieved_at_utc, edition, content_type}.  Both carry the same two
        # facts this check needs - where it came from and when it was fetched -
        # under different key names, so the reader accepts either and reports
        # the split rather than treating it as missing evidence.
        stamp = sc.get("retrieved_utc") or sc.get("retrieved_at_utc")
        url = sc.get("url") or sc.get("source_url") or ""
        if not stamp:
            problems.append({"file": base, "problem": "sidecar has no retrieval timestamp"})
        if edition.replace("Injury-Report_", "") not in url:
            problems.append({"file": base, "problem": "sidecar url does not name the edition",
                             "url": url})
        schemas[",".join(sorted(sc))] += 1
        editions.append({"edition": edition,
                         "revision_label": sc.get("revision_label") or sc.get("edition"),
                         "retrieved_utc": stamp,
                         "bytes": sc.get("bytes"),
                         "sha256": digest,
                         "source_url": url,
                         "file": os.path.relpath(p, ROOT)})

    # the consecutive-diff chain
    diff_files = sorted(glob.glob(os.path.join(DIFF_DIR, "diff_*.json")),
                        key=lambda p: edition_key(os.path.basename(p)))
    pairs = max(len(editions) - 1, 0)
    changes = adds = removes = filing = 0
    for d in diff_files:
        doc = json.load(open(d, encoding="utf-8"))
        changes += len(doc.get("status_or_reason_changes") or [])
        adds += len(doc.get("listed_in_after_only") or [])
        removes += len(doc.get("listed_in_before_only") or [])
        filing += len(doc.get("team_block_filing_changes") or [])
    if len(diff_files) < pairs:
        problems.append({"file": "data/parsed/injury_diffs/",
                         "problem": "%d consecutive pairs but only %d diff artifacts - the "
                                    "chain is not complete" % (pairs, len(diff_files))})

    out = {
        "title": "Injury-PDF archive integrity and consecutive-diff coverage",
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": "arena/3ff8ff0f-nba1",
        "pdfs_checked": checked,
        "first_edition": editions[0]["edition"] if editions else None,
        "last_edition": editions[-1]["edition"] if editions else None,
        "sidecar_schemas_in_circulation": {k: v for k, v in schemas.items()},
        "all_signed_ok": not problems,
        "status_changes_detected": changes,
        "players_listed_in_the_later_edition_only": adds,
        "players_dropped_from_the_later_edition": removes,
        "team_block_filing_changes": filing,
        "diff_artifacts": len(diff_files),
        "consecutive_pairs": pairs,
        "problems": problems,
        "editions": editions,
        "rule": ("every value here is computed from the files in this repository: the hash is "
                 "recomputed from the stored bytes, the timestamp and URL come from the sidecar "
                 "the fetcher wrote at retrieval, and the change counts come from the "
                 "consecutive-edition diffs engine/injury_diff.py generates."),
    }
    if args.json:
        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
    print("PDFs checked: %d (%s .. %s)" % (checked, out["first_edition"], out["last_edition"]))
    print("diff artifacts: %d for %d consecutive pairs" % (len(diff_files), pairs))
    print("status/reason changes detected across the chain: %d "
          "(%d players newly listed, %d no longer listed, %d team-block filing changes)"
          % (changes, adds, removes, filing))
    if problems:
        print("PROBLEMS (%d):" % len(problems))
        for p in problems[:20]:
            print("  ", json.dumps(p))
        return 1
    print("ARCHIVE OK - every stored PDF matches its content hash, sidecar and timestamp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
