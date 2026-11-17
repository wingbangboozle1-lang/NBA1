#!/usr/bin/env python3
"""F-CA-07 + F-CA-04 amendment + R04 evidence (additive register update)."""
import json

S = "session arena/ca442d3d-nba1 (COORDINATION \u00a765)"

R04 = ("Measured on the runner 2026-11-17 16:36Z, " + S + ": the index-driven capture ran on a "
       "scheduled refresh armed from this branch and archived **10 new editions for 2026-11-17** "
       "(09:00 AM through 11:30 AM ET, content-addressed with sidecars) where the archive had "
       "stopped at 2026-11-16 01:15 PM - the four-fixed-clock-times limitation is gone. The dual "
       "reader was re-run over the whole archive afterwards: **110 editions, no row disagreement** "
       "between the clipped-cell reader and the word-band parser, so F-X01 stays closed on fresh "
       "bytes. The promotion-time chain was then executed over the committed archive: "
       "Injury-Report_2026-11-17_11_15AM -> 11_30AM, 59 rows / 33 player rows, 0 status or filing "
       "changes -> data/parsed/injury_diffs/promote_diff_Injury-Report_2026-11-17_11_15AM_to_"
       "Injury-Report_2026-11-17_11_30AM.json. The row stays partial on one measured point, now "
       "flagged as F-CA-07: in that refresh run promotion did not execute at all "
       "(`_last_refresh.json` records an empty promotion and a `changed` list holding only the three "
       "failed evidence sources), so the 11/17 editions were captured but not diffed or promoted "
       "until this seat ran the chain by hand. Capture, diff and promote are each correct; the "
       "wiring that makes the scheduled run reach the promote step is the remaining gap.")

F07 = ("Opened 2026-11-17 by " + S + ". The 16:36Z refresh on this branch captured 10 official "
       "injury editions for 2026-11-17 (bytes + sidecars committed by the runner in 68caa0e) and "
       "then stopped: `data/raw/_last_refresh.json` for that run records `promotion` as an empty "
       "record with `promoted: []` and `blocked: null`, while `changed` lists only "
       "'evidence S1_season', 'evidence S2_train', 'evidence S8_standings' - the three sources whose "
       "parse failed with 'expected 30 team rows, parsed 0' (F-CA-02). So the injury capture is not "
       "part of the `changed` vocabulary that the promote step consumes, and an edition-only change "
       "cannot wake promotion. Consequence, and it is the same shape as arena/b454a53d-nba1's F140 from the other direction: the ten newest official editions sit in the archive with no revision-to-revision diff and were never promoted, so the model input data/raw/injuries.json is still `Injury-Report_2026-11-16_09_45AM.pdf` (verification.verified_at_utc 2026-11-16T15:25:57Z) - a day and roughly twenty-five editions behind the newest archived PDF (2026-11-17 11:30 AM) - while the roll page's cut banner names the newer edition because the horizon build read it separately as a text render. This seat verified the chain by hand over the committed archive (11/17 11:15 AM -> 11:30 AM, "
       "59 rows / 33 player rows, 0 status and 0 filing changes, written to "
       "data/parsed/injury_diffs/promote_diff_Injury-Report_2026-11-17_11_15AM_to_"
       "Injury-Report_2026-11-17_11_30AM.json), which proves the code and isolates the gap to the "
       "trigger. Proposed, not applied here because `.github/workflows/refresh-data.yml` and the "
       "changed-list semantics belong to the refresh owner: treat 'new editions archived' as a "
       "promotion-relevant change, and gate the *model rebuild* (not the injury promotion) on the "
       "structured sources. Until then, R04's automation is only as current as the last session that "
       "ran the diff by hand.")

F04_APPEND = (" UPDATE 2026-11-17 16:41Z: one run armed from this branch was NOT cancelled and it "
              "completed usefully - the refresh committed 10 new 2026-11-17 injury editions plus the "
              "11/16-11/17 results captures (68caa0e), which is the evidence that the index-driven "
              "capture works end to end on a runner. The cancellation finding above still stands for "
              "the 3 runs it was measured on, and the promotion gap that run left is now its own "
              "flag, F-CA-07.")


def main():
    fp = "data/content/flagged.json"
    fl = json.load(open(fp, encoding="utf-8"))
    by_id = {i["id"]: i for i in fl["items"]}
    if "F-CA-04" in by_id and F04_APPEND.strip() not in by_id["F-CA-04"]["detail"]:
        by_id["F-CA-04"]["detail"] = by_id["F-CA-04"]["detail"].rstrip() + " " + F04_APPEND.strip()
        by_id["F-CA-04"]["status"] = "open (partly overtaken by events - see the update)"
    if "F-CA-07" not in by_id:
        fl["items"].append({
            "id": "F-CA-07", "severity": "High", "status": "open",
            "title": ("The scheduled refresh captures the newest injury editions but never reaches "
                      "promotion, so an edition-only change is archived without its diff or a "
                      "promoted injuries.json (the trigger half of R04)"),
            "detail": F07,
            "affected": ("engine/fetch_official.py (changed-list), engine/promote_official.py, "
                         ".github/workflows/refresh-data.yml, data/raw/injuries.json, R04, R18, R26"),
            "links": [
                {"label": "That run's refresh record (repo)",
                 "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/raw/_last_refresh.json"},
                {"label": "Hand-verified 11/17 diff chain (repo)",
                 "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/parsed/injury_diffs/promote_diff_Injury-Report_2026-11-17_11_15AM_to_Injury-Report_2026-11-17_11_30AM.json"},
                {"label": "Official injury-report index (the source that listed the 10 editions)",
                 "url": "https://official.nba.com/nba-injury-report-2026-27-season/"}]})
    json.dump(fl, open(fp, "w", encoding="utf-8"), indent=1)

    rp = "data/content/requirements.json"
    rq = json.load(open(rp, encoding="utf-8"))
    for r in rq["rows"]:
        if r["id"] == "R04" and "F-CA-07" not in (r.get("evidence") or ""):
            r["evidence"] = f"{(r.get('evidence') or '').rstrip()} {R04}".strip()
    json.dump(rq, open(rp, "w", encoding="utf-8"), indent=1)
    print("flagged items:", len(fl["items"]), "| R04 appended")


if __name__ == "__main__":
    main()
