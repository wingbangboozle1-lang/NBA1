#!/usr/bin/env python3
"""Independent re-hash of the pick ledger chain.

Deliberately a second implementation of the same rule stated in
data/ledger/ledger.json ("each entry stores the SHA-256 of the previous entry's
canonical JSON (sorted keys); genesis = entry 1"), so a bug in
scripts/verify_ledger.py cannot hide a break here.

Run: python3 verify/2026-11-16-23b323a3/ledger_chain_check.py
"""
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
led = json.load(open(os.path.join(ROOT, "data/ledger/ledger.json"), encoding="utf-8"))
canon = lambda d: json.dumps(d, sort_keys=True).encode()
sha = lambda b: hashlib.sha256(b).hexdigest()

fails, prev = [], None
for e in led["entries"]:
    if prev is None:
        if e.get("prev") != "GENESIS":
            fails.append("entry %s does not start at GENESIS" % e.get("entry"))
    elif e.get("prev") != prev:
        fails.append("entry %s prev does not match the previous entry's hash" % e.get("entry"))
    prev = sha(canon(e))

if prev != led.get("head"):
    fails.append("recorded head %s != recomputed %s" % (led.get("head"), prev))

print("entries             :", len(led["entries"]))
print("recomputed head     :", prev)
print("recorded head       :", led.get("head"))
print("RESULT              :", "CHAIN OK" if not fails else "CHAIN BROKEN")
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
