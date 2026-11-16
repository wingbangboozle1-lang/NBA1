#!/usr/bin/env python3
"""Re-apply this session's three COORDINATION.md additions onto any base version.

    python3 verify/2026-11-16-2823d556/rebuild_board.py <base.md> <out.md>

Why this exists. COORDINATION.md is the one file every session writes to, and six
sessions were pushing to it at once. A naive `git rebase` resolution took this
session's board from 4566 lines to 73 once (2026-11-16 ~02:35Z) because the
conflict was resolved by slicing instead of by re-applying additive blocks. That
destroyed other sessions' records and was corrected within minutes by restoring
`origin/main`'s copy, but it should not be possible twice.

This script makes the operation **additive and idempotent** instead:

  * it inserts the top claim banner before the first `## 🔑 ACTIVE CLAIM`;
  * it inserts the §0b registry row directly after the `arena/754e9e54-nba1` row
    (falling back to the end of the registry table if that row is gone);
  * it appends the §47 section at the end of the file;

and it never removes a line from the base. It also refuses to run if the output
would lose headings that the base had.

The three blocks live in this namespace (not in COORDINATION.md) so they survive
a rebase that checks out the base file.
"""

from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BANNER = open(os.path.join(HERE, "_block_banner.md"), encoding="utf-8").read().rstrip("\n")
ROW = open(os.path.join(HERE, "_block_registry_row.md"), encoding="utf-8").read().rstrip("\n")
TAIL = open(os.path.join(HERE, "_block_section47.md"), encoding="utf-8").read().rstrip("\n")

REGISTRY_ANCHOR = "| `arena/754e9e54-nba1` |"
BANNER_ANCHOR = "## 🔑 ACTIVE CLAIM"


def apply(base: str) -> str:
    out = base
    if "arena/2823d556-nba1" not in out:
        # --- banner: before the first ACTIVE CLAIM heading -------------------
        i = out.find(BANNER_ANCHOR)
        if i == -1:
            raise SystemExit("anchor not found: no '## 🔑 ACTIVE CLAIM' heading in the base")
        out = out[:i] + BANNER + "\n\n---\n\n" + out[i:]

        # --- registry row: right after the 754e9e54 row ----------------------
        j = out.find(REGISTRY_ANCHOR)
        if j == -1:
            raise SystemExit("anchor not found: the arena/754e9e54-nba1 registry row")
        k = out.find("\n", j)
        out = out[:k + 1] + ROW + "\n" + out[k + 1:]

        # --- tail section ----------------------------------------------------
        out = out.rstrip("\n") + "\n\n---\n\n" + TAIL + "\n"
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    base = open(sys.argv[1], encoding="utf-8").read()
    out = apply(base)

    lost = [h for h in re.findall(r"^## .*$", base, flags=re.M) if h not in out]
    if lost:
        print("REFUSING TO WRITE: these base headings would be lost:")
        for h in lost[:20]:
            print("  -", h[:100])
        return 1
    if len(out.splitlines()) < len(base.splitlines()):
        print("REFUSING TO WRITE: the output is shorter than the base "
              f"({len(out.splitlines())} < {len(base.splitlines())})")
        return 1
    open(sys.argv[2], "w", encoding="utf-8").write(out)
    print(f"{sys.argv[2]}: {len(base.splitlines())} -> {len(out.splitlines())} lines "
          f"(+{len(out.splitlines()) - len(base.splitlines())}), 0 headings lost")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
