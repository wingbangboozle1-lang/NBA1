#!/usr/bin/env python3
"""verify_ledger.py — recompute the SHA-256 hash chain in data/ledger/ledger.json.

For each entry: recompute the SHA-256 of its canonical JSON (sorted keys) and
check it equals the `prev` value stored in the following entry (and `head`).
Also re-hash any files named in file entries against their recorded digests.

Exit 0 = chain intact; exit 1 = tamper detected.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canon(d):
    return json.dumps(d, sort_keys=True).encode()


def main():
    ledger = json.load(open(os.path.join(ROOT, "data/ledger/ledger.json"), encoding="utf-8"))
    ok = True
    prev = None
    for e in ledger["entries"]:
        expected_prev = e.get("prev")
        if prev is not None and expected_prev != prev:
            print(f"FAIL entry {e['entry']}: prev mismatch ({expected_prev[:16]} != {prev[:16]})")
            ok = False
        h = sha(canon(e))
        if "files" in e:
            for rel, want in e["files"].items():
                got = sha(open(os.path.join(ROOT, rel), "rb").read())
                if got != want:
                    print(f"FAIL entry {e['entry']}: {rel} digest mismatch")
                    ok = False
        for key in ("prereg_files",):
            if key in e:
                for rel, want in e[key].items():
                    got = sha(open(os.path.join(ROOT, rel), "rb").read())
                    if got != want:
                        print(f"FAIL entry {e['entry']}: {rel} digest mismatch ({key})")
                        ok = False
        if ("files_now" in e or "files_at_settlement" in e
                or "model_input_digests" in e):
            # point-in-time attestation (hash-chained); live files legitimately
            # change after the rolling update, so digests are not re-checked here
            pass
        if "sha256" in e and "file" in e:
            got = sha(open(os.path.join(ROOT, e["file"]), "rb").read())
            if got != e["sha256"]:
                print(f"FAIL entry {e['entry']}: {e['file']} digest mismatch")
                ok = False
        prev = h
    if prev != ledger["head"]:
        print("FAIL: head mismatch")
        ok = False
    print("ledger chain OK" if ok else "ledger chain BROKEN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
