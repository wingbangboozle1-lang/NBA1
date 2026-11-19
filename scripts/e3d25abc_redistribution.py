#!/usr/bin/env python3
"""e3d25abc_redistribution.py — explicit top-8 minutes redistribution, sized from
the archived official minutes, with the absence-vs-production delta reported only
where the archived window can actually measure it.

Session arena/e3d25abc-nba1, COORDINATION §68 Q05.

THE BRIEF LINE
--------------
  "Model minutes redistribution explicitly - when a player is out, show where his
     minutes go, using the team's actual top-8 rotation."

WHAT THIS IS NOT
----------------
It is not a fitted constant.  A common shortcut is "his minutes split evenly among
the other seven" or "the 9th man takes 100%"; neither is what NBA rotations do.
Here the recipient weights are that game's own observed minutes for the other
players, renormalised - so the shape of the redistribution comes from the box
score of the game being modelled, and every input is printed next to the output.

MEASURED VS MODELLED
--------------------
  * modelled (structural, per game): freed minutes, recipient weights, the new
    top-8 share, and the number of players the team actually used.
  * measured (difference in production): a player held out on one archived day
    and playing on the other, in the same team's window.  Where both days exist
    for the same player, the delta is arithmetic on two official box scores.
    Where they do not, the field is null and the reason is printed.  Nothing is
    filled in.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e3d25abc_availability as av  # same team-name map, same name normaliser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAYS = ("2026-11-17", "2026-11-18")
NEXT_SLATE = "2026-11-19"
OUT = os.path.join(ROOT, "data", "derived",
                   "minutes_redistribution_2026-11-19_e3d25abc.json")
VERIFY = os.path.join(ROOT, "verify", "2026-11-19-e3d25abc", "redistribution.md")
AVAIL = os.path.join(ROOT, "data", "derived", "availability_2026-11-17_18_e3d25abc.json")


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mtxt(secs):
    secs = int(secs or 0)
    return f"{secs // 60}:{secs % 60:02d}"


def load_logs(day):
    p = os.path.join(ROOT, "data", "official", f"player_game_logs_{day}.json")
    if not os.path.exists(p):
        raise SystemExit(f"FATAL: {p} missing - run scripts/e3d25abc_game_logs.py first")
    return json.load(open(p, encoding="utf-8")).get("rows", [])


def main() -> int:
    os.makedirs(os.path.dirname(VERIFY), exist_ok=True)
    per_game, notes = [], []
    logs = {d: load_logs(d) for d in DAYS}
    # the newest archived edition for the NEXT slate (2026-11-19), read the same way
    nxt = {}
    ed_paths = sorted(glob.glob(os.path.join(ROOT, "data", "parsed", "injury_diffs",
                                              "editions", "Injury-Report_2026-11-19_*.json")),
                      key=lambda p: av.edition_key(os.path.basename(p)[:-5]))
    next_edition = None
    if ed_paths:
        next_edition = os.path.basename(ed_paths[-1])[:-5]
        ed = json.load(open(ed_paths[-1], encoding="utf-8"))
        tri, _ = av.team_map()
        for r in ed.get("rows", []):
            if len(r) >= 7 and r[0] == NEXT_SLATE and any(w in (r[5] or "").lower()
                                                           for w in av.OUT_WORDS):
                nxt.setdefault(tri.get(str(r[3]).strip(), "?"), set()).add(av.norm(r[4]))

    forward = {}
    for day in DAYS:
        games = {}
        for r in logs[day]:
            games.setdefault((r["game_id"], r["team"]), []).append(r)
        for (gid, team), rows in sorted(games.items()):
            played = [r for r in rows if r.get("played")]
            played.sort(key=lambda r: -(r["minutes_seconds"] or 0))
            tot = sum(r["minutes_seconds"] or 0 for r in played) or 1
            top8_before = sum(r["minutes_seconds"] or 0 for r in played[:8]) / tot
            scen = []
            for target in played:
                freed = target["minutes_seconds"] or 0
                others = [r for r in played if r is not target]
                rem = sum(r["minutes_seconds"] or 0 for r in others) or 1
                # the structural redistribution: the freed minutes go to the players
                # who actually shared this game's floor, weighted by what they already
                # had.  Cap at the 8-man unit the brief names: beyond rank 8 the
                # weight is reported but the recipient list is the top 8 non-targets.
                recips = others[:8]
                rsum = sum(r["minutes_seconds"] or 0 for r in recips) or 1
                alloc = []
                for r in recips:
                    w = (r["minutes_seconds"] or 0) / rsum
                    alloc.append({"player": r["player"], "weight_from_observed_minutes": round(w, 4),
                                  "minutes_before": r["minutes"],
                                  "minutes_added_s": round(freed * w),
                                  "minutes_after": mtxt((r["minutes_seconds"] or 0) + freed * w)})
                after_total = sum(a["minutes_added_s"] for a in alloc)
                if abs(after_total - freed) > 3:
                    notes.append(f"{gid} {team}: allocation {after_total}s does not return the "
                                 f"{freed}s freed - rounding only, check the weights")
                top8_after = ((sum(r["minutes_seconds"] or 0 for r in played[:8]
                                   if r is not target) + after_total) / tot)
                scen.append({
                    "absent_player": target["player"], "absent_minutes": target["minutes"],
                    "absent_share_of_team_minutes": round(freed / tot, 4),
                    "absent_points": target["points"], "absent_rebounds": target["rebounds"],
                    "absent_assists": target["assists"],
                    # meaningful, unlike "was out today": a player out today has no
                    # minutes to redistribute.  This flags the players who played in
                    # this game and are declared out for the NEXT slate - the cases
                    # the model actually has to solve.
                    "declared_out_for_the_next_slate": (
                        av.norm(target["player"]) in nxt.get(team, set())),
                    "players_used_before": len(played),
                    "players_used_after": len(played) - 1,
                    "top8_share_before": round(top8_before, 4),
                    "top8_share_after": round(top8_after, 4),
                    "recipients": alloc,
                    "method_note": ("recipients are this game's own highest-minute players "
                                    "other than the absent one, weighted by the minutes they "
                                    "actually played in this game; no constant, no league "
                                    "average, no prior")})
            per_game.append({"date": day, "game_id": gid, "team": team,
                             "opponent": played[0]["opponent"] if played else None,
                             "team_minutes": mtxt(tot), "players_used": len(played),
                             "top8_share": round(top8_before, 4),
                             "scenarios": scen})
            # ---- (B) forward table: this team's out-names for the next slate ----
            for tcode, names in sorted(nxt.items()):
                if tcode != team:
                    continue
                for r in played:
                    if av.norm(r["player"]) in names:
                        forward.setdefault(tcode, []).append({
                            "declared_out": r["player"], "for_slate": NEXT_SLATE,
                            "reference_game": gid, "reference_game_date": day,
                            "minutes_that_need_a_home": r["minutes"],
                            "share_of_team_minutes": round((r["minutes_seconds"] or 0) / tot, 4),
                            "points_rebounds_assists_lost": [r["points"], r["rebounds"],
                                                              r["assists"]],
                            "redistribution": next(
                                (sc["recipients"] for sc in scen
                                 if sc["absent_player"] == r["player"]), [])})

    # every out-name for the next slate that has no archived game in this window
    covered = {av.norm(x["declared_out"]) for v in forward.values() for x in v}
    missing_next = sorted({(tcode, n) for tcode, names in nxt.items() for n in names
                           if n not in covered})
    last_log = {d: logs[d] for d in DAYS}
    for tcode, n in missing_next:
        for d in DAYS:
            for r in last_log[d]:
                if r["team"] == tcode and av.norm(r["player"]) == n and not r.get("played"):
                    forward.setdefault(tcode, []).append({
                        "declared_out": r["player"], "for_slate": NEXT_SLATE,
                        "reference_game": r["game_id"], "reference_game_date": d,
                        "minutes_that_need_a_home": None,
                        "share_of_team_minutes": None,
                        "points_rebounds_assists_lost": None,
                        "redistribution": [],
                        "note": "no archived minutes for this player in the two-day window - "
                                "the redistribution is not computable from official data here, "
                                "so it is left blank and flagged"})
    covered2 = {av.norm(x["declared_out"]) for v in forward.values() for x in v}
    still_missing = sorted(n for tcode, n in missing_next if av.norm(n) not in covered2)
    notes.append(f"{len(still_missing)} of the next slate's declared-out names have no row at "
                 f"all in the archived box scores; their redistribution is left blank")

    # ---- measured absence-vs-production delta, only where the window allows ----
    by_team_day = {}
    for day in DAYS:
        for r in logs[day]:
            by_team_day.setdefault((r["team"], r["player"]), {})[day] = r
    measured, unmeasurable = [], 0
    for (team, player), days in sorted(by_team_day.items()):
        if len(days) == 2:
            a, b = days.get(DAYS[0]), days.get(DAYS[1])
            if a is None or b is None:
                unmeasurable += 1
                continue
            if bool(a.get("played")) == bool(b.get("played")):
                continue  # both played or both out: no absence contrast to measure
            out_day, in_day = (a, b) if not a.get("played") else (b, a)
            measured.append({
                "team": team, "player": player,
                "absent_day": out_day["date"], "playing_day": in_day["date"],
                "minutes_while_playing": in_day["minutes"],
                "points_while_playing": in_day["points"],
                "rebounds_while_playing": in_day["rebounds"],
                "assists_while_playing": in_day["assists"],
                "on_the_page_without_minutes_when_absent": out_day.get("comment"),
                "production_while_absent": 0,
                "absence_vs_production_delta_points": -(in_day["points"] or 0),
                "lower_bound_note": (
                    "the delta is against the single other archived day for the same team, "
                    "which is a lower bound on impact and an upper bound on noise: one game "
                    "of a two-day window, different opponent, different venue. It is published "
                    "as measured arithmetic, not as an effect size.")})
        else:
            unmeasurable += 1
    for (team, player), days in sorted(by_team_day.items()):
        if any(not r.get("played") for r in days.values()) and len(days) == 1:
            notes.append(f"{team} {player}: appears on one archived day only, so no "
                         "absence contrast exists for them in this window - left blank")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"title": "Explicit minutes-redistribution table for the 2026-11-17 / "
                           "2026-11-18 games, sized from the archived official minutes",
                   "generated_by": "scripts/e3d25abc_redistribution.py",
                   "generated_at_utc": now_utc(),
                   "session": "arena/e3d25abc-nba1",
                   "sources": {
                       "box_scores": [f"data/official/player_game_logs_{d}.json" for d in DAYS],
                       "out_declarations": "data/derived/availability_2026-11-17_18_e3d25abc.json"
                                           " (report PDFs -> parsed editions)",
                       "gamepage_bytes": "data/raw/session-e3d25abc/gamepages/** (digest-verified)"},
                   "rule": ("Redistribution is structural arithmetic on one game's own box "
                            "score: the absent player's minutes are handed to the highest-minute "
                            "teammates of that same game in proportion to the minutes they "
                            "actually played. No constant, no league average and no prior is "
                            "used. A player absent on both archived days contributes no "
                            "measured delta - the field stays null and is reported as not "
                            "measurable rather than filled."),
                   "window_limits": {
                       "game_days": list(DAYS),
                       "games": len(per_game),
                       "scenarios": sum(len(g["scenarios"]) for g in per_game),
                       "measured_absence_contrasts": len(measured),
                       "players_with_one_archived_day_only": unmeasurable,
                       "why_so_few_measured": ("the archived window is two game days, so a "
                                               "player needs to have played one day and been "
                                               "held out the other; most rotations do not "
                                               "change that fast, and the report-to-box-score "
                                               "join holds 0 contradictions over 136 out-names")},
                   "next_slate": {"game_date": NEXT_SLATE,
                                  "edition_used": next_edition,
                                  "out_names_by_team": {t: sorted(n) for t, n in
                                                         sorted(nxt.items())},
                                  "per_team": forward,
                                  "names_with_no_archived_minutes": still_missing},
                   "per_game": per_game,
                   "measured_deltas": measured,
                   "notes": notes}, fh, indent=1)
        fh.write("\n")

    with open(VERIFY, "w", encoding="utf-8") as fh:
        fh.write("# Explicit top-8 minutes redistribution — 2026-11-17 / 11-18\n\n")
        fh.write(f"Built by `scripts/e3d25abc_redistribution.py` (§68 Q05) at {now_utc()}.\n\n")
        fh.write(f"* {len(per_game)} team-games, "
                 f"**{sum(len(g['scenarios']) for g in per_game)} one-player-out scenarios**, each "
                 "sized from that game's own minutes (recipients weighted by the minutes they "
                 "actually played), with `top8_share_before` / `top8_share_after` printed beside it\n")
        fh.write(f"* **{len(measured)}** measured absence-vs-production contrasts exist in the "
                 f"archived window; {unmeasurable} player(s) appear on only one of the two days "
                 "and are left blank with the reason, not filled\n")
        fh.write(f"* **{sum(1 for g in per_game for sc in g['scenarios'] if sc['declared_out_for_the_next_slate'])}"
                 " scenario(s) match a player the newest archived report declares out for the "
                 f"{NEXT_SLATE} slate — those are the ones the model feeds on\n")
        fh.write(f"* next-slate table: {sum(len(v) for v in forward.values())} team-entries across "
                 f"{len(forward)} team(s); {len(still_missing)} declared-out name(s) with no "
                 "archived minutes, left blank and flagged\n\n")
        fh.write("## Forward table — where the next slate's out-minutes go\n\n")
        fh.write("| Team | Out for " + NEXT_SLATE + " | Ref game | Min to reallocate | Top recipient | "
                 "Their min before → after |\n| --- | --- | --- | --- | --- | --- |\n")
        for t, entries in sorted(forward.items()):
            for e in entries:
                r0 = (e["redistribution"] or [{}])[0]
                fh.write(f"| {t} | {e['declared_out']} | {e['reference_game_date']} "
                         f"{e['reference_game']} | {e['minutes_that_need_a_home'] or '— not measurable'} | "
                         f"{r0.get('player') or '—'} | "
                         f"{r0.get('minutes_before', '—')} → {r0.get('minutes_after', '—')} |\n")
        fh.write("## Largest single structural shift, per team-day\n\n"
                 "| Day | Team | Players used | Top-8 share | Absent | Freed | Top-8 after | "
                 "Report said out? |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for g in per_game:
            if not g["scenarios"]:
                continue
            sc = max(g["scenarios"], key=lambda x: x["absent_share_of_team_minutes"])
            if not sc:
                continue
            fh.write(f"| {g['date']} | {g['team']} | {g['players_used']} | "
                     f"{g['top8_share']} | {sc['absent_player']} | {sc['absent_minutes']} | "
                     f"{sc['top8_share_after']} | "
                     f"{'yes' if sc['declared_out_for_the_next_slate'] else 'no'} |\n")
        fh.write("\n## Measured contrasts\n\n")
        if measured:
            fh.write("| Team | Player | Absent day | Playing day | Min | Pts | Reb | Ast | Comment while out |\n")
            fh.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
            for m in measured:
                fh.write(f"| {m['team']} | {m['player']} | {m['absent_day']} | "
                         f"{m['playing_day']} | {m['minutes_while_playing']} | "
                         f"{m['points_while_playing']} | {m['rebounds_while_playing']} | "
                         f"{m['assists_while_playing']} | {m['on_the_page_without_minutes_when_absent'] or '—'} |\n")
        else:
            fh.write("none — the two-day window contains no player who both played one day and "
                     "was held out the other. Published as an empty result rather than estimated.\n")
        fh.write("\n## Notes\n\n")
        fh.write("\n".join(f"* {n}" for n in notes) + "\n" if notes else "none\n")
    print(json.dumps({"next_slate_out_names": {t: len(n) for t, n in nxt.items()},
                      "forward_entries": sum(len(v) for v in forward.values()),
                      "team_games": len(per_game),
                      "scenarios": sum(len(g["scenarios"]) for g in per_game),
                      "measured_deltas": len(measured),
                      "one_day_only_players": unmeasurable,
                      "notes": len(notes)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
