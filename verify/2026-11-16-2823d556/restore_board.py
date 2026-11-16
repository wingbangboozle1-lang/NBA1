#!/usr/bin/env python3
"""Restore the shared task board after commit 813e7a9 truncated it.

    python3 verify/2026-11-16-2823d556/restore_board.py <good.md> <truncated.md> <out.md>

WHAT HAPPENED (measured, not inferred)
--------------------------------------
`git cat-file -s <commit>:COORDINATION.md` across recent `main` commits:

    3f86cba   491255 bytes   <- last good board (75 `## ` headings, 15 registry rows)
    813e7a9    30764 bytes   <- PR #128, session arena/dfef26dc-nba1, "E06: resolve merge
                                with the 754e9e54 full-cycle build"
    e30f541    28690 bytes

Commit `813e7a9` collapsed the board to 366 lines: **71 of 75 top-level headings and
13 of 15 session-registry rows disappeared.** Every delivery record from §1 to §45 —
the handoff log, the collision resolutions, the Pages deploy history, the 44-section
audit trail that eight sessions had been writing to since 2026-11-13 — was lost from
`main` in one merge.

This is not a criticism of that session: the same failure mode hit this session two
hours earlier, when a naive rebase-resolution slicing took the board from 4566 lines to
73. It was caught within minutes because the gates went red. It is the reason
`rebuild_board.py` in this directory exists.

WHAT THIS SCRIPT DOES
---------------------
It does **not** try to be clever. It takes the last known-good blob, finds exactly what
the truncated tip had that the good blob does not (registry rows and whole top-level
sections), and appends those. Then `rebuild_board.py` re-applies this session's three
blocks on top.

Two guards, both of which abort the write:
  * no heading present in EITHER input may be missing from the output;
  * the output may not be shorter than the good input.

Usage:
    git show 3f86cba:COORDINATION.md > /tmp/good.md
    git show 813e7a9:COORDINATION.md > /tmp/trunc.md
    python3 verify/2026-11-16-2823d556/restore_board.py /tmp/good.md /tmp/trunc.md COORDINATION.md
    python3 verify/2026-11-16-2823d556/rebuild_board.py COORDINATION.md COORDINATION.md
"""

from __future__ import annotations

import re
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    good = open(sys.argv[1], encoding="utf-8").read()
    trunc = open(sys.argv[2], encoding="utf-8").read()

    out = good

    # 1. Registry rows the good board does not have.
    missing_rows = [l for l in trunc.splitlines()
                    if l.startswith("| `arena/") and l not in out]
    if missing_rows:
        # append them right after the last existing registry row
        idx = out.rfind("\n| `arena/")
        end = out.find("\n", idx)
        out = out[:end + 1] + "\n".join(missing_rows) + "\n" + out[end + 1:]

    # 2. Whole top-level sections the good board does not have.
    missing_secs = []
    for part in re.split(r"(?m)^(?=## )", trunc):
        if not part.strip():
            continue
        if part.splitlines()[0] not in out:
            missing_secs.append(part.rstrip("\n"))
    if missing_secs:
        out = out.rstrip("\n") + "\n\n---\n\n" + "\n\n---\n\n".join(missing_secs) + "\n"

    # --- guards ---------------------------------------------------------
    all_headings = (set(re.findall(r"^## .*$", good, flags=re.M))
                    | set(re.findall(r"^## .*$", trunc, flags=re.M)))
    lost = sorted(h for h in all_headings if h not in out)
    if lost:
        print("REFUSING TO WRITE - these headings would be lost:")
        for h in lost[:25]:
            print("  -", h[:110])
        return 1
    if len(out.splitlines()) < len(good.splitlines()):
        print("REFUSING TO WRITE - output shorter than the good input")
        return 1

    open(sys.argv[3], "w", encoding="utf-8").write(out)
    print(f"restored: good {len(good.splitlines())} lines + truncated tip "
          f"{len(trunc.splitlines())} lines -> {len(out.splitlines())} lines")
    print(f"  registry rows recovered: {len(missing_rows)}")
    print(f"  sections recovered     : {len(missing_secs)}  "
          f"({[s.splitlines()[0][:60] for s in missing_secs]})")
    print(f"  headings in output     : {len(re.findall(r'^## .*$', out, flags=re.M))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
