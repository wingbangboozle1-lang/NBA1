#!/usr/bin/env python3
"""e3d25abc_injury_chain.py — recover, verify and publish the official
injury-report edition chain for the game days the archive is missing
(session arena/e3d25abc-nba1, COORDINATION §68 Q03).

THE GAP THIS CLOSES
-------------------
The brief asks: *"Store every injury PDF with its timestamp and diff consecutive
reports to detect status changes."*  Two things were measured before writing
this file (`git rev-parse`/`ls`, not assumed):

* `data/raw/injury_pdfs/` newest archived edition on `main` is
  `Injury-Report_2026-11-17_11_30AM`; there is **no** 2026-11-18 or 2026-11-19
  edition in the archive at all;
* `data/parsed/injury_diffs/index.json` publishes a chain of **100** editions
  ending at `2026-11-16_01_15PM` — so even the ten 11/17 PDFs that a runner
  already committed were never parsed or diffed.

The official index page (https://official.nba.com/nba-injury-report-2026-27-season/)
lists only the **current** game day's editions — measured at 2026-11-19T05:49:13Z:
4 editions listed, all `2026-11-19`, newest 12:45 a.m. ET.  So the 11/17 and
11/18 editions cannot be re-fetched from the index, and this script does not
pretend otherwise.  What it does is recover them from the places they already
exist as **official bytes with a retrieval stamp**: the scheduled job's own
runner captures, which were committed to `auto/refresh-*` branches and never
promoted.

WHAT IT DOES
-------------
1. **Recover.** For each source (the four un-promoted `auto/refresh-*` capture
   branches, plus this seat's runner capture dir when it lands), take every
   `data/raw/injury_pdfs/<edition>__<sha>.pdf` + its sidecar whose edition name is
   not already in the local archive.
2. **Verify, then copy.** Before a single byte is written: the SHA-256 is
   recomputed from the bytes and must equal the digest in the filename *and* the
   one in the sidecar; the first KiB must carry `%PDF-`; the sidecar must carry a
   `retrieved_at_utc` and an `ak-static.cms.nba.com` source URL.  Anything that
   fails any check is reported and skipped — never "repaired".
   The copy keeps the same content-addressed name and gains two chain-of-custody
   fields: `recovered_from_git_ref` and `recovered_at_utc`.
3. **Publish the chain.** Runs `engine/injury_diff.py` (the repo's own two-reader
   parser: clipped-cell reader + word-band line reader, cross-checked) over the
   *whole* enlarged archive into a scratch dir, then copies into
   `data/parsed/injury_diffs/` only the edition and consecutive-diff records that
   do not exist yet.  A published record is never overwritten.
4. **Report.** Writes `verify/2026-11-19-e3d25abc/injury-chain.md` and
   `data/official/injury_editions_2026-11-19_e3d25abc.json`: per-day counts, the
   15-minute gap list (which official revisions no source in this repository has
   bytes for), every status/filing change between consecutive editions, and the
   promoted-pointer proposal (newest verified edition, with its revision label,
   its retrieval UTC and its digest) for whoever owns `data/raw/injuries.json`.

Nothing here infers a status.  A row the readers cannot assemble is recorded
under `unparsed` by the engine and stays blank.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "data", "raw", "injury_pdfs")
DIFFS = os.path.join(ROOT, "data", "parsed", "injury_diffs")
SESSION_CAPTURE = os.path.join(ROOT, "data", "raw", "session-e3d25abc",
                               "injury_pdfs")
VERIFY_DIR = os.path.join(ROOT, "verify", "2026-11-19-e3d25abc")
OUT_INDEX = os.path.join(ROOT, "data", "official",
                         "injury_editions_2026-11-19_e3d25abc.json")

# (git ref, why the run that produced it never reached promotion)
AUTO_REFS = [
    ("origin/auto/refresh-20261117-230319",
     "scheduled run 2026-11-17T23:03Z: captured the 11/17 afternoon editions; "
     "the branch was never merged, so the archive on `main` kept only the "
     "09:00 AM-11:30 AM set"),
    ("origin/auto/refresh-20261118-120903",
     "scheduled run 2026-11-18T12:09Z (the 11:15Z cron): captured the 11/18 "
     "early-morning editions"),
    ("origin/auto/refresh-20261118-160934",
     "scheduled run 2026-11-18T16:09Z (the 15:15Z cron): captured the 11/18 "
     "mid-morning editions"),
    ("origin/auto/refresh-20261118-230153",
     "scheduled run 2026-11-18T23:01Z (the 22:15Z cron): captured the 11/18 "
     "game-day editions (03:30-05:45 PM ET)"),
]

NAME_RE = re.compile(r"^(Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}(?:AM|PM))"
                     r"__([0-9a-f]{64})\.pdf$")
EDITION_ONLY_RE = re.compile(r"^(Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}(?:AM|PM))")


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def edition_key(name: str):
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", name)
    if not m:
        return (name, 0)
    y, mo, d, hh, mm, ampm = m.groups()
    return (f"{y}-{mo}-{d}", (int(hh) % 12 + (12 if ampm == "PM" else 0)) * 100 + int(mm))


def revision_label_et(edition: str) -> str:
    """'Injury-Report_2026-11-18_03_30PM' -> '2026-11-18 03:30 p.m. ET'."""
    m = re.search(r"_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)", edition)
    if not m:
        return None
    d, hh, mm, ap = m.groups()
    return f"{d} {hh}:{mm} {ap.lower().replace('am', 'a.m.').replace('pm', 'p.m.')} ET"


def git_show(ref: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT,
                          capture_output=True).stdout


def existing_editions() -> dict:
    """edition name -> filename, for what the local archive already holds."""
    out = {}
    for fn in os.listdir(ARCHIVE):
        if not fn.endswith(".pdf"):
            continue
        m = EDITION_ONLY_RE.match(fn)
        if m:
            out[m.group(1)] = fn
    return out


def verify_bytes(raw: bytes, fname: str, sidecar: dict) -> list:
    """Every claim this archive makes about a PDF, checked against the bytes."""
    problems = []
    m = NAME_RE.match(fname)
    if not m:
        problems.append("filename is not of the content-addressed form "
                        "<edition>__<sha256>.pdf")
        return problems
    name_edition, name_digest = m.groups()
    if hashlib.sha256(raw).hexdigest() != name_digest:
        problems.append(f"recomputed SHA-256 != digest in the filename "
                        f"({name_digest[:12]}...): the bytes are not what was filed")
    if sidecar is None:
        problems.append("no sidecar: no retrieval timestamp, no source URL")
    else:
        if sidecar.get("sha256") != name_digest:
            problems.append("sidecar sha256 disagrees with the filename digest")
        # `source_url` is the engine's field name, `url` the one this seat's
        # capture script wrote.  Either is accepted; the bytes still have to
        # match the digest and the host still has to be the official one.
        side_edition = sidecar.get("edition") or (
            (os.path.basename(sidecar.get("name") or "") + ".pdf")
            if sidecar.get("name") else None)
        if side_edition != name_edition + ".pdf":
            problems.append(f"sidecar edition {sidecar.get('edition')!r} != "
                            f"filename edition {name_edition}.pdf")
        if not sidecar.get("retrieved_at_utc"):
            problems.append("sidecar carries no retrieved_at_utc (the brief's "
                            "'with its timestamp')")
        src = sidecar.get("source_url") or sidecar.get("url") or ""
        if not src.startswith("https://ak-static.cms.nba.com/referee/injury/"):
            problems.append(f"source_url is not the official injury host: {src!r}")
        if sidecar.get("bytes") not in (None, len(raw)):  # as-is
            problems.append(f"sidecar says {sidecar.get('bytes')} bytes, the "
                            f"object is {len(raw)}")
    if b"%PDF-" not in raw[:1024]:
        problems.append("no %PDF- signature in the first KiB")
    return problems


def collect_from_ref(ref: str, have: dict, log) -> list:
    """New candidate editions held on `ref`, verified before acceptance."""
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, "--",
         "data/raw/injury_pdfs/"], cwd=ROOT, capture_output=True,
        text=True).stdout.split()
    fresh = []
    for path in listing:
        base = os.path.basename(path)
        if not path.endswith(".pdf"):
            continue
        m = EDITION_ONLY_RE.match(base)
        if not m or m.group(1) in have:
            continue
        raw = git_show(ref, path)
        side_path = path[:-4] + ".json"
        side_txt = git_show(ref, side_path)
        sidecar = None
        if side_txt:
            try:
                sidecar = json.loads(side_txt.decode("utf-8"))
            except json.JSONDecodeError:
                sidecar = None
        problems = verify_bytes(raw, base, sidecar or {})
        fresh.append({"ref": ref, "path": path, "name": base, "edition": m.group(1),
                      "raw": raw, "sidecar": sidecar, "problems": problems})
        log(f"  {ref.split('/')[-1]}: {m.group(1)} -> "
            + ("OK" if not problems else f"REJECTED ({problems[0]})"))
    return fresh


def collect_from_dir(d: str, log) -> list:
    """Same checks for this seat's own runner capture dir (sidecars are
    written as <file>.sidecar.json by scripts/capture_official_e3d25abc.py)."""
    fresh = []
    if not os.path.isdir(d):
        return fresh
    have = existing_editions()
    for path in sorted(glob.glob(os.path.join(d, "*.pdf"))):
        base = os.path.basename(path)
        m = EDITION_ONLY_RE.match(base)
        if not m:
            continue
        raw = open(path, "rb").read()
        side_path = path + ".sidecar.json"
        sidecar = None
        if os.path.exists(side_path):
            try:
                sidecar = json.load(open(side_path, encoding="utf-8"))
            except json.JSONDecodeError:
                sidecar = None
        else:
            alt = path[:-4] + ".json"
            if os.path.exists(alt):
                sidecar = json.load(open(alt, encoding="utf-8"))
        problems = verify_bytes(raw, base, sidecar or {})
        if m.group(1) in have:
            continue
        fresh.append({"ref": "data/raw/session-e3d25abc (this seat's runner "
                             "capture, commit-local)", "path": path,
                      "name": base, "edition": m.group(1), "raw": raw,
                      "sidecar": sidecar, "problems": problems})
        log(f"  session capture: {m.group(1)} -> "
            + ("OK" if not problems else f"REJECTED ({problems[0]})"))
    return fresh


def write_recovered(items, log) -> list:
    """Append-only: a file whose name already exists is never touched."""
    written = []
    for it in items:
        if it["problems"]:
            continue
        dst = os.path.join(ARCHIVE, it["name"])
        if os.path.exists(dst):
            log(f"  skip (already archived): {it['name']}")
            continue
        with open(dst, "wb") as fh:
            fh.write(it["raw"])
        side = dict(it["sidecar"] or {})
        side.update({"edition": it["edition"] + ".pdf",
                     "source_url": (it["sidecar"] or {}).get("source_url")
                                   or (it["sidecar"] or {}).get("url"),
                     "recovered_from_git_ref": it["ref"],
                     "recovered_at_utc": now_utc(),
                     "recovered_by": "arena/e3d25abc-nba1 (scripts/e3d25abc_injury_chain.py)",
                     "sha256_recomputed_from_bytes": True,
                     "pdf_signature": "%PDF-" if b"%PDF-" in it["raw"][:1024] else None,
                     "revision_label_et": revision_label_et(it["edition"])})
        with open(dst[:-4] + ".json", "w", encoding="utf-8") as fh:
            json.dump(side, fh, indent=2)
            fh.write("\n")
        written.append({"file": os.path.relpath(dst, ROOT).replace(os.sep, "/"),
                        "edition": it["edition"], "bytes": len(it["raw"]),
                        "sha256": it["sidecar"]["sha256"],
                        "retrieved_at_utc": it["sidecar"].get("retrieved_at_utc"),
                        "source_url": (it["sidecar"].get("source_url")
                                       or it["sidecar"].get("url")),
                        "recovered_from": it["ref"]})
    return written


def chain_gap_report() -> dict:
    """Which official 15-minute slots have no bytes in the archive.

    The league files on a 15-minute cadence through the reporting window, so an
    absent slot is a real hole in the audit trail and is published as one rather
    than being smoothed over.  Only days that have at least one archived edition
    are examined - a day with no editions at all is reported as absent, not as a
    chain of 96 gaps.
    """
    have = sorted(existing_editions())
    by_day = {}
    for fn in have:
        m = EDITION_ONLY_RE.match(fn)
        if m:
            e = m.group(1)
            day = re.search(r"_(\d{4}-\d{2}-\d{2})_", e).group(1)
            hh, mm = int(re.search(r"_(\d{2})_\d{2}(?:AM|PM)", e).group(1)), \
                int(re.search(r"_\d{2}_(\d{2})(?:AM|PM)", e).group(1))
            ap = re.search(r"_(\d{2})_(\d{2})(AM|PM)", e).group(3)
            h24 = hh % 12 + (12 if ap == "PM" else 0)
            by_day.setdefault(day, set()).add(h24 * 60 + mm)
    out = {}
    for day, slots in sorted(by_day.items()):
        lo, hi = min(slots), max(slots)
        expect = list(range(lo // 15 * 15, hi + 1, 15))
        missing = [f"{s // 60:02d}:{s % 60:02d}" for s in expect if s not in slots]
        out[day] = {"archived_editions": len(slots),
                   "first_slot_et": f"{lo // 60:02d}:{lo % 60:02d}",
                   "last_slot_et": f"{hi // 60:02d}:{hi % 60:02d}",
                   "missing_slots_inside_the_span": missing,
                   "missing_count": len(missing)}
    return out


def main() -> int:
    os.makedirs(VERIFY_DIR, exist_ok=True)
    lines, report = [], {"run_at_utc": now_utc(),
                         "session": "arena/e3d25abc-nba1", "coordination": "§68 Q03"}

    def log(msg):
        print(msg, flush=True)
        lines.append(msg)

    have = existing_editions()
    report["archive_before"] = {"pdfs": sum(1 for f in os.listdir(ARCHIVE)
                                             if f.endswith(".pdf")),
                                "editions": len(have)}
    log(f"archive before: {report['archive_before']['pdfs']} PDF(s), "
        f"{len(have)} distinct edition(s), newest "
        f"{max(have, key=edition_key) if have else 'none'}")

    candidates, per_source = [], {}
    for ref, why in AUTO_REFS:
        try:
            present = subprocess.run(["git", "rev-parse", "--verify", "-q", ref],
                                     cwd=ROOT, capture_output=True).returncode == 0
        except Exception:                                     # noqa: BLE001
            present = False
        if not present:
            per_source[ref] = {"status": "ref not available in this clone",
                               "note": why}
            log(f"  {ref}: ref not available - skipped, recorded")
            continue
        got = collect_from_ref(ref, have, log)
        per_source[ref] = {"status": "read", "candidates": len(got),
                           "accepted": sum(1 for g in got if not g["problems"]),
                           "rejected": sum(1 for g in got if g["problems"]),
                           "note": why}
        candidates += got
        for g in got:
            have.setdefault(g["edition"], g["name"])
    got = collect_from_dir(SESSION_CAPTURE, log)
    per_source["session-e3d25abc"] = {
        "status": "read", "candidates": len(got),
        "accepted": sum(1 for g in got if not g["problems"]),
        "rejected": sum(1 for g in got if g["problems"])}
    candidates += got
    for g in got:
        have.setdefault(g["edition"], g["name"])
    report["sources"] = per_source

    written = write_recovered(candidates, log)
    report["recovered"] = written
    report["recovered_count"] = len(written)
    report["rejected_count"] = sum(1 for c in candidates if c["problems"])
    report["rejections"] = [{"edition": c["edition"], "ref": c["ref"],
                             "problems": c["problems"]} for c in candidates
                            if c["problems"]]
    log(f"recovered {len(written)} official edition(s) into the archive "
        f"({report['rejected_count']} rejected)")

    # ---- publish the chain with the repo's own two-reader parser ----------
    scratch = tempfile.mkdtemp(prefix="injury-chain-")
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "engine", "injury_diff.py"),
                           "--pdf-dir", ARCHIVE, "--out-dir", scratch],
                          cwd=ROOT, capture_output=True, text=True)
    chain_stdout = (proc.stdout or "") + (proc.stderr or "")
    report["engine_exit"] = proc.returncode
    report["engine_summary"] = [l for l in chain_stdout.splitlines()
                                if "edition(s) parsed" in l or "::error::" in l
                                or "row disagreement" in l]
    log("engine/injury_diff.py: " + (report["engine_summary"][0]
                                     if report["engine_summary"] else
                                     f"exit {proc.returncode} (see run log)"))

    copied = {"editions": [], "diffs": []}
    for kind, sub, prefix in (("editions", "editions", ""), ("diffs", "", "diff_")):
        src_dir = os.path.join(scratch, sub) if sub else scratch
        pat = os.path.join(src_dir, "*.json")
        for path in sorted(glob.glob(pat)):
            base = os.path.basename(path)
            if kind == "diffs" and not base.startswith("diff_"):
                continue
            dst_dir = os.path.join(DIFFS, "editions") if kind == "editions" else DIFFS
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, base)
            if os.path.exists(dst):
                continue                      # published records are never overwritten
            shutil.copyfile(path, dst)
            copied[kind].append(os.path.relpath(dst, ROOT).replace(os.sep, "/"))
    report["published_new_records"] = copied
    log(f"new chain records published: {len(copied['editions'])} edition parse(s), "
        f"{len(copied['diffs'])} consecutive diff(s)")

    # scratch index -> merged chain index for the new tail
    idx_path = os.path.join(scratch, "index.json")
    if os.path.exists(idx_path):
        shutil.copyfile(idx_path, os.path.join(DIFFS, "index_e3d25abc.json"))
    shutil.rmtree(scratch, ignore_errors=True)

    report["chain_gaps"] = chain_gap_report()
    for day, g in report["chain_gaps"].items():
        log(f"  {day}: {g['archived_editions']} edition(s) "
            f"{g['first_slot_et']}-{g['last_slot_et']} ET, "
            f"{g['missing_count']} missing slot(s) inside that span")

    # ---- what the injuries pointer should become -------------------------
    editions = sorted(existing_editions(), key=edition_key)
    newest = editions[-1] if editions else None
    side = {}
    if newest:
        cand = sorted(glob.glob(os.path.join(ARCHIVE, newest + "__*.json")))
        if cand:
            side = json.load(open(cand[-1], encoding="utf-8"))
    report["newest_verified_edition"] = {
        "edition": newest + ".pdf" if newest else None,
        "revision_label_et": revision_label_et(newest) if newest else None,
        "retrieved_at_utc": side.get("retrieved_at_utc"),
        "sha256": side.get("sha256"),
        "source_url": side.get("source_url"),
        "note": ("proposed value for data/raw/injuries.json, which this seat "
                 "does not write (owned by PR #173 / the refresh owner)"),
    }
    log(f"newest verified edition: {newest} "
        f"({report['newest_verified_edition']['revision_label_et']}) "
        f"retrieved {report['newest_verified_edition']['retrieved_at_utc']}")

    with open(OUT_INDEX, "w", encoding="utf-8") as fh:
        json.dump({"title": "Official injury-report editions archived and "
                           "byte-verified for the 2026-11-17 .. 2026-11-19 window",
                   "generated_by": "scripts/e3d25abc_injury_chain.py",
                   "generated_at_utc": now_utc(),
                   "rule": ("Every entry is a PDF whose bytes were fetched from "
                            "https://ak-static.cms.nba.com/referee/injury/ and whose "
                            "SHA-256 was recomputed from the stored bytes in this run. "
                            "A slot with no such file is listed as a gap; no edition is "
                            "reconstructed, and no status is inferred."),
                   "per_day": report["chain_gaps"],
                   "recovered": report["recovered"],
                   "sources": report["sources"],
                   "newest_verified_edition": report["newest_verified_edition"]},
                  fh, indent=1)
        fh.write("\n")
    with open(os.path.join(VERIFY_DIR, "injury-chain.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# Injury-archive recovery and consecutive-diff chain — "
                 "2026-11-19 (session arena/e3d25abc-nba1, §68 Q03)\n\n")
        fh.write(f"Run at {report['run_at_utc']}. Machine-readable copy: "
                 f"`{os.path.relpath(OUT_INDEX, ROOT).replace(os.sep, '/')}`.\n\n```\n")
        fh.write("\n".join(lines))
        fh.write("\n```\n\n## Full report JSON\n\n```json\n")
        fh.write(json.dumps(report, indent=1))
        fh.write("\n```\n")
    log(f"wrote {os.path.relpath(OUT_INDEX, ROOT)} and "
        f"{os.path.relpath(os.path.join(VERIFY_DIR, 'injury-chain.md'), ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
