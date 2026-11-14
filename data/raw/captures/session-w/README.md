# Session W raw captures (`arena/f80dcc4a-nba1`, 2026-11-14 UTC)

Verbatim captures of official pages read by this session through the platform fetch tool.
These files are the provenance record for every structured row in:

- `data/raw/official_results_2026-11-13.json` — state of the 11/13 slate at capture time
- `data/raw/records_2026-11-14.json` — team W-L records as officially displayed at capture time
- `data/raw/injury_report_2026-11-13_08_00PM.json` — rows of the latest published official injury report at capture time

`scripts/verify_session_w.py` re-parses these captures and fails if any structured row does not
match the captured official text.

Capture conventions:

- Injury-report captures are the complete PDF text as returned by the fetch tool, chunk by chunk.
- Games-page captures keep the date strip, every game card (teams, records, tip time, game id link)
  and every Season Leaders table; the navigation chrome (identical on every NBA.com page) is elided
  and marked `[nav elided]`. Elision never removes a data row.
- Every capture records the URL, the UTC time it was read, and the fetch tool's chunking.
