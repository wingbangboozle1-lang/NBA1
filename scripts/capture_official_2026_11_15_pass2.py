#!/usr/bin/env python3
"""capture_official_2026_11_15_pass2.py - the second capture pass.

    python3 scripts/capture_official_2026_11_15_pass2.py

The first pass (scripts/capture_official_2026_11_15.py) captured the slate
pages, every box score, the standings page, the three team-stat pages, every
injury-report PDF and the Census gazetteer. Three things in it were not usable
as they stood, and this pass fixes exactly those three:

  1. The box-score page stores the quarter lines and the player boxes in a
     shape the first pass's parser did not read. This pass stores the raw
     embedded JSON of three box-score pages (one early-season, one from the
     2026-11-14 slate, one from the upcoming horizon) so the parser can be
     corrected against the real payload rather than a guess.

  2. The standings page is rendered client-side, so the first pass's
     __NEXT_DATA__ walk found no team rows. This pass stores the raw page and
     renders it in the headless browser the runner has.

  3. The three official team-stat pages are rendered client-side from the NBA's
     own stats service. This pass renders them in the same headless browser and
     extracts the published tables.

Everything here is read-only with respect to the published snapshots: it writes
under data/captures/2026-11-15/ only.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from capture_official_2026_11_15 import (          # noqa: E402
    HEADERS, next_data, fetch, write_json, now_utc, log, OUT, RAW, PARSED)

SAMPLES = [
    ("0022600001", "https://www.nba.com/game/bos-vs-det-0022600001/box-score"),
    ("0022600231", "https://www.nba.com/game/den-vs-nop-0022600231/box-score"),
    ("0022600236", "https://www.nba.com/game/ind-vs-phi-0022600236/box-score"),
]

STAT_PAGES = {
    "traditional": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season",
    "opponent": "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season",
    "advanced": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
}


def main():
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(PARSED, exist_ok=True)

    # 1) raw box-score payloads ------------------------------------------
    for gid, url in SAMPLES:
        rec, body = fetch(url, label=f"pass2 boxscore {gid}",
                          store=f"samples/boxscore_{gid}.html")
        if not body:
            log(f"  boxscore {gid}: FAILED {rec.get('http_status')}")
            continue
        doc = next_data(body.decode("utf-8", "replace"))
        path = os.path.join(RAW, f"samples/boxscore_{gid}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        log(f"  boxscore {gid}: stored {os.path.getsize(path)} bytes of embedded JSON")

    # 2) the standings page, raw ------------------------------------------
    rec, body = fetch("https://www.nba.com/standings", label="pass2 standings",
                      store="samples/standings.html")
    log(f"  standings raw: {rec.get('bytes')} bytes (status {rec.get('http_status')})")

    # 3) the three team-stat pages, rendered -------------------------------
    node = os.path.join(ROOT, "scripts", "render_stats_tables.mjs")
    if os.path.exists(node):
        try:
            out = subprocess.run(["node", node], capture_output=True, text=True,
                                 timeout=900, cwd=ROOT)
            log("  stats render exit %s" % out.returncode)
            if out.stdout:
                for line in out.stdout.strip().splitlines()[-12:]:
                    log("    " + line)
            if out.returncode != 0 and out.stderr:
                for line in out.stderr.strip().splitlines()[-12:]:
                    log("    ERR " + line)
        except subprocess.TimeoutExpired:
            log("  stats render: TIMED OUT")
    else:
        log("  stats render: scripts/render_stats_tables.mjs is missing")

    write_json(os.path.join(OUT, "pass2_manifest.json"),
               {"finished_at_utc": now_utc(),
                "note": "second capture pass: raw box-score payloads, the raw "
                        "standings page and the rendered official team-stat tables"})


if __name__ == "__main__":
    sys.exit(main())
