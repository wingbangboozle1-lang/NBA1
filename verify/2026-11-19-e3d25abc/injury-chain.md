# Injury-archive recovery and consecutive-diff chain — 2026-11-19 (session arena/e3d25abc-nba1, §68 Q03)

Run at 2026-11-19T05:56:11Z. Machine-readable copy: `data/official/injury_editions_2026-11-19_e3d25abc.json`.

```
archive before: 150 PDF(s), 148 distinct edition(s), newest Injury-Report_2026-11-18_05_45PM
  session capture: Injury-Report_2026-11-19_12_00AM -> OK
  session capture: Injury-Report_2026-11-19_12_15AM -> OK
  session capture: Injury-Report_2026-11-19_12_30AM -> OK
  session capture: Injury-Report_2026-11-19_12_45AM -> OK
recovered 4 official edition(s) into the archive (0 rejected)
engine/injury_diff.py: 154 edition(s) parsed with no row disagreement between the two readers
new chain records published: 4 edition parse(s), 4 consecutive diff(s)
  2026-11-15: 81 edition(s) 00:00-23:00 ET, 12 missing slot(s) inside that span
  2026-11-16: 17 edition(s) 09:15-13:15 ET, 0 missing slot(s) inside that span
  2026-11-17: 20 edition(s) 09:15-18:00 ET, 16 missing slot(s) inside that span
  2026-11-18: 30 edition(s) 04:45-17:45 ET, 23 missing slot(s) inside that span
  2026-11-19: 4 edition(s) 00:00-00:45 ET, 0 missing slot(s) inside that span
newest verified edition: Injury-Report_2026-11-19_12_45AM (2026-11-19 12:45 a.m. ET) retrieved 2026-11-19T05:53:50Z
```

## Full report JSON

```json
{
 "run_at_utc": "2026-11-19T05:56:11Z",
 "session": "arena/e3d25abc-nba1",
 "coordination": "\u00a768 Q03",
 "archive_before": {
  "pdfs": 150,
  "editions": 148
 },
 "sources": {
  "origin/auto/refresh-20261117-230319": {
   "status": "read",
   "candidates": 0,
   "accepted": 0,
   "rejected": 0,
   "note": "scheduled run 2026-11-17T23:03Z: captured the 11/17 afternoon editions; the branch was never merged, so the archive on `main` kept only the 09:00 AM-11:30 AM set"
  },
  "origin/auto/refresh-20261118-120903": {
   "status": "read",
   "candidates": 0,
   "accepted": 0,
   "rejected": 0,
   "note": "scheduled run 2026-11-18T12:09Z (the 11:15Z cron): captured the 11/18 early-morning editions"
  },
  "origin/auto/refresh-20261118-160934": {
   "status": "read",
   "candidates": 0,
   "accepted": 0,
   "rejected": 0,
   "note": "scheduled run 2026-11-18T16:09Z (the 15:15Z cron): captured the 11/18 mid-morning editions"
  },
  "origin/auto/refresh-20261118-230153": {
   "status": "read",
   "candidates": 0,
   "accepted": 0,
   "rejected": 0,
   "note": "scheduled run 2026-11-18T23:01Z (the 22:15Z cron): captured the 11/18 game-day editions (03:30-05:45 PM ET)"
  },
  "session-e3d25abc": {
   "status": "read",
   "candidates": 4,
   "accepted": 4,
   "rejected": 0
  }
 },
 "recovered": [
  {
   "file": "data/raw/injury_pdfs/Injury-Report_2026-11-19_12_00AM__8b516e44bd666b4da7196b7b9e7eb250228f3c8f5e6c8ced043c5d58be1bb5ee.pdf",
   "edition": "Injury-Report_2026-11-19_12_00AM",
   "bytes": 87159,
   "sha256": "8b516e44bd666b4da7196b7b9e7eb250228f3c8f5e6c8ced043c5d58be1bb5ee",
   "retrieved_at_utc": "2026-11-19T05:53:53Z",
   "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_12_00AM.pdf",
   "recovered_from": "data/raw/session-e3d25abc (this seat's runner capture, commit-local)"
  },
  {
   "file": "data/raw/injury_pdfs/Injury-Report_2026-11-19_12_15AM__5571ebd0eeca2d5e16b70eaf123b845bf50a248c7020a19c0ea2363a692564a2.pdf",
   "edition": "Injury-Report_2026-11-19_12_15AM",
   "bytes": 87198,
   "sha256": "5571ebd0eeca2d5e16b70eaf123b845bf50a248c7020a19c0ea2363a692564a2",
   "retrieved_at_utc": "2026-11-19T05:53:52Z",
   "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_12_15AM.pdf",
   "recovered_from": "data/raw/session-e3d25abc (this seat's runner capture, commit-local)"
  },
  {
   "file": "data/raw/injury_pdfs/Injury-Report_2026-11-19_12_30AM__14a511bfabd6666c0c07b6248fda2fbca46a566dcab0c11e13268a6081fe4a15.pdf",
   "edition": "Injury-Report_2026-11-19_12_30AM",
   "bytes": 87322,
   "sha256": "14a511bfabd6666c0c07b6248fda2fbca46a566dcab0c11e13268a6081fe4a15",
   "retrieved_at_utc": "2026-11-19T05:53:51Z",
   "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_12_30AM.pdf",
   "recovered_from": "data/raw/session-e3d25abc (this seat's runner capture, commit-local)"
  },
  {
   "file": "data/raw/injury_pdfs/Injury-Report_2026-11-19_12_45AM__91002377f7653e4c96aaa7c3293c70f3a36ceaf000cbd2be2349205831ccea33.pdf",
   "edition": "Injury-Report_2026-11-19_12_45AM",
   "bytes": 87302,
   "sha256": "91002377f7653e4c96aaa7c3293c70f3a36ceaf000cbd2be2349205831ccea33",
   "retrieved_at_utc": "2026-11-19T05:53:50Z",
   "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_12_45AM.pdf",
   "recovered_from": "data/raw/session-e3d25abc (this seat's runner capture, commit-local)"
  }
 ],
 "recovered_count": 4,
 "rejected_count": 0,
 "rejections": [],
 "engine_exit": 0,
 "engine_summary": [
  "154 edition(s) parsed with no row disagreement between the two readers"
 ],
 "published_new_records": {
  "editions": [
   "data/parsed/injury_diffs/editions/Injury-Report_2026-11-19_12_00AM.json",
   "data/parsed/injury_diffs/editions/Injury-Report_2026-11-19_12_15AM.json",
   "data/parsed/injury_diffs/editions/Injury-Report_2026-11-19_12_30AM.json",
   "data/parsed/injury_diffs/editions/Injury-Report_2026-11-19_12_45AM.json"
  ],
  "diffs": [
   "data/parsed/injury_diffs/diff_Injury-Report_2026-11-18_05_45PM_to_Injury-Report_2026-11-19_12_00AM.json",
   "data/parsed/injury_diffs/diff_Injury-Report_2026-11-19_12_00AM_to_Injury-Report_2026-11-19_12_15AM.json",
   "data/parsed/injury_diffs/diff_Injury-Report_2026-11-19_12_15AM_to_Injury-Report_2026-11-19_12_30AM.json",
   "data/parsed/injury_diffs/diff_Injury-Report_2026-11-19_12_30AM_to_Injury-Report_2026-11-19_12_45AM.json"
  ]
 },
 "chain_gaps": {
  "2026-11-15": {
   "archived_editions": 81,
   "first_slot_et": "00:00",
   "last_slot_et": "23:00",
   "missing_slots_inside_the_span": [
    "19:00",
    "19:15",
    "19:30",
    "19:45",
    "20:00",
    "20:15",
    "20:30",
    "20:45",
    "21:45",
    "22:00",
    "22:15",
    "22:30"
   ],
   "missing_count": 12
  },
  "2026-11-16": {
   "archived_editions": 17,
   "first_slot_et": "09:15",
   "last_slot_et": "13:15",
   "missing_slots_inside_the_span": [],
   "missing_count": 0
  },
  "2026-11-17": {
   "archived_editions": 20,
   "first_slot_et": "09:15",
   "last_slot_et": "18:00",
   "missing_slots_inside_the_span": [
    "11:45",
    "12:00",
    "12:15",
    "12:30",
    "12:45",
    "13:00",
    "13:15",
    "13:30",
    "13:45",
    "14:00",
    "14:15",
    "14:30",
    "14:45",
    "15:00",
    "15:15",
    "15:30"
   ],
   "missing_count": 16
  },
  "2026-11-18": {
   "archived_editions": 30,
   "first_slot_et": "04:45",
   "last_slot_et": "17:45",
   "missing_slots_inside_the_span": [
    "07:15",
    "07:30",
    "07:45",
    "08:00",
    "08:15",
    "08:30",
    "11:15",
    "11:30",
    "11:45",
    "12:00",
    "12:15",
    "12:30",
    "12:45",
    "13:00",
    "13:15",
    "13:30",
    "13:45",
    "14:00",
    "14:15",
    "14:30",
    "14:45",
    "15:00",
    "15:15"
   ],
   "missing_count": 23
  },
  "2026-11-19": {
   "archived_editions": 4,
   "first_slot_et": "00:00",
   "last_slot_et": "00:45",
   "missing_slots_inside_the_span": [],
   "missing_count": 0
  }
 },
 "newest_verified_edition": {
  "edition": "Injury-Report_2026-11-19_12_45AM.pdf",
  "revision_label_et": "2026-11-19 12:45 a.m. ET",
  "retrieved_at_utc": "2026-11-19T05:53:50Z",
  "sha256": "91002377f7653e4c96aaa7c3293c70f3a36ceaf000cbd2be2349205831ccea33",
  "source_url": null,
  "note": "proposed value for data/raw/injuries.json, which this seat does not write (owned by PR #173 / the refresh owner)"
 }
}
```
