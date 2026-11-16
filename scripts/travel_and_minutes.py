#!/usr/bin/env python3
"""R11 travel distance + R12 minutes redistribution, both computed from committed
official captures only.

R11  The brief: "Compute rest, back-to-back and 3-in-4 from the official schedule
     (already possible) and add travel distance from a sourced arena-coordinate table."
     The table exists (data/official/arena_coordinates_2026-11-15.json, 30 arenas, each
     row citing the official schedule page for the venue name and the coordinate source
     for the numbers). What was missing was the distance itself. It is now computed as the
     great-circle miles between the arena of the team's previous game and the arena of the
     game in question. A team whose previous arena is not in a committed official capture
     gets miles=null and a reason - never a guess.

R12  The brief: "for each team, the top-8 minutes shares and the replacement shares when a
     player is out". Season-length per-player minutes for all 30 teams were never captured
     (the only committed minutes table is the league top-50), so the shares are measured
     from the official game books of the 2026-11-15 slate: for each of the 12 teams that
     played, every player's minutes as the book prints them, the top-8 share of the team's
     minutes, the 9th-and-below share (the pool a replacement must come from), and the list
     of players the book marks out with an injury reason. Coverage and its limit are stated
     in the output rather than hidden.

Run:  python3 scripts/travel_and_minutes.py
"""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EARTH_MI = 3958.8


def rd(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding="utf-8"))


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return round(2 * EARTH_MI * math.asin(math.sqrt(h)), 1)


def mmss_to_min(t):
    if not t or ":" not in str(t):
        return None
    m, s = str(t).split(":")
    return int(m) + int(s) / 60.0


def main():
    slate = rd("data", "raw", "official_schedule_capture_2026-11-16.json")
    cols = slate["cols"]
    arenas = rd("data", "official", "arena_coordinates_2026-11-15.json")["rows"]
    coord = {r["abbr"]: r for r in arenas}
    by_arena = {r["arena"]: r for r in arenas}

    # previous-game venue, from the committed official result feeds only
    venue_by_game = {}          # (date, team) -> arena
    for path, key in (("data/official/results_2026-11-14.json", "venue"),
                      ("data/official/results_2026-11-15.json", "venue"),
                      ("data/official/results_2026-11-15_settled_6e1aadc1.json", "arena")):
        f = os.path.join(ROOT, path)
        if not os.path.exists(f):
            continue
        for r in rd(*path.split("/"))["rows"]:
            v = r.get(key) or ""
            # the 11/14 feed stores "Arena, City" in one field
            v = v.split(",")[0].strip()
            for side in ("away", "home"):
                if v:
                    venue_by_game[(r["date"], r[side])] = v
    # in-window games (11/16-11/18) carry their arena in the schedule capture itself
    idx = {c: i for i, c in enumerate(cols)}
    slate_rows = []
    for raw in slate["rows"]:
        row = {c: raw[i] for i, c in enumerate(cols)} if isinstance(raw, list) else dict(raw)
        slate_rows.append(row)
        for side in ("away", "home"):
            venue_by_game[(row["date"], row[side])] = row["venue"]

    lines = {g["game_id"]: g for g in rd("data", "derived", "horizon_lines.json")["games"]}
    travel_rows = []
    for row in slate_rows:
        gid = row["game_id"]
        lg = lines.get(gid, {})
        for side in ("away", "home"):
            team = row[side]
            cur_arena = row["venue"]
            rest = lg.get(f"rest_{side}") or {}
            prev_date = rest.get("last_date")
            prev_arena = venue_by_game.get((prev_date, team)) if prev_date else None
            cur = by_arena.get(cur_arena)
            out = dict(date=row["date"], game_id=gid, team=team, side=side,
                       rest_days=rest.get("rest_days"), back_to_back=rest.get("b2b"),
                       prev_game_date=prev_date, prev_arena=prev_arena, arena=cur_arena,
                       miles=None)
            if prev_arena and cur and prev_arena in by_arena:
                out["miles"] = hav(by_arena[prev_arena], cur)
                out["source_url"] = "https://www.nba.com/schedule"
                out["coordinate_source"] = coord[team]["coordinate_source_url"] if team in coord else arenas[0]["coordinate_source_url"]
            else:
                out["not_computed_reason"] = (
                    "previous-game arena not in a committed official capture "
                    f"({team} on {prev_date}); the 2026-11-13 result feeds store score and "
                    "date but no venue, so the distance is left null rather than assumed")
            # 3-in-4 from the official schedule: count games in the trailing 4-day window
            travel_rows.append(out)

    def in4(d1, d2):
        from datetime import date
        a = date(*map(int, d1.split("-")))
        b = date(*map(int, d2.split("-")))
        return 0 <= (b - a).days <= 4
    games_by_team_date = {}
    for row in slate_rows:
        for side in ("away", "home"):
            games_by_team_date.setdefault(row[side], set()).add(row["date"])
    for r in travel_rows:
        if r["prev_game_date"]:
            # games of this team inside the trailing 4-day window, from the official schedule
            cnt = 1 + sum(1 for d in games_by_team_date.get(r["team"], ()) if in4(d, r["date"]))
            r["games_in_4_days_from_official_schedule"] = cnt

    # ---- R12: minutes shares measured from the official game books ----------------------
    logs = rd("data", "official", "player_game_logs_2026-11-15_6e1aadc1.json")["rows"]
    feed = {r["game_id"]: r for r in rd("data", "official",
                                       "results_2026-11-15_settled_6e1aadc1.json")["rows"]}
    per_team = {}
    for r in logs:
        if not r["appears_in_box"]:
            continue
        per_team.setdefault((r["game_id"], r["team"]), []).append(r)
    minutes_rows = []
    for (gid, team), rows in sorted(per_team.items()):
        for r in rows:
            r["min_dec"] = mmss_to_min(r["minutes"])
        rows.sort(key=lambda r: -(r["min_dec"] or 0))
        total = round(sum(r["min_dec"] for r in rows), 1)
        top8 = rows[:8]
        bench = rows[8:]
        top8_min = round(sum(r["min_dec"] for r in top8), 1)
        bench_min = round(sum(r["min_dec"] for r in bench), 1)
        g = feed.get(gid, {})
        inact_key = "inactives_away" if g.get("away") == team else "inactives_home"
        outs = [o for o in g.get(inact_key, [])
                if "Injury/Illness" in (o.get("reason") or "")]
        minutes_rows.append(dict(
            date="2026-11-15", game_id=gid, team=team, opponent=rows[0]["opponent"],
            players_used=len(rows), team_total_minutes=total,
            top8_players=[f"{r['player']} {r['minutes']}" for r in top8],
            top8_minutes=top8_min,
            top8_share=round(top8_min / total, 4) if total else None,
            replacement_pool_players=len(bench), replacement_pool_minutes=bench_min,
            replacement_pool_share=round(bench_min / total, 4) if total else None,
            players_out_with_injury_reason=[o["player"] for o in outs],
            out_reasons={o["player"]: o["reason"] for o in outs},
            dnp_dnd_injury=[r["player"] for r in rows if "Injury" in str(r.get("did_not_play"))],
            source_gamebook_pdf=rows[0]["source_gamebook_pdf"]))
    out = {
        "title": "Travel distance (R11) and minutes-share table (R12) for the rolling slate",
        "generated_by": "scripts/travel_and_minutes.py",
        "travel_method": "great-circle (haversine) miles between the arena of the team's previous "
                         "game and the arena of the game in question; earth radius 3958.8 miles. "
                         "Venue names come from the official schedule page and the official result "
                         "feeds; coordinates come from the sourced arena-coordinate table, which "
                         "states its own provenance and caveat.",
        "rest_method": "rest_days and back_to_back are carried from data/derived/horizon_lines.json, "
                       "which derives them from the official schedule capture and the official finals.",
        "travel_rows": travel_rows,
        "travel_coverage": dict(rows=len(travel_rows),
                                computed=sum(1 for r in travel_rows if r["miles"] is not None),
                                left_null=len([r for r in travel_rows if r["miles"] is None]),
                                reason="previous arena for the 2026-11-13 game day is not in any "
                                       "committed official capture"),
        "minutes_method": "measured from the official game book of each 2026-11-15 game: every player "
                           "with playing time, minutes as printed (MM:SS). top-8 share = the eight "
                           "largest minute lines over the team's total minutes (5 x 48, or 5 x 53 in OT); "
                           "the replacement pool is the 9th player and below - the minutes that a "
                           "fill-in actually comes from in that game.",
        "minutes_rows": minutes_rows,
        "coverage_limit": "12 teams from one game day. Season-length top-8 minutes shares for all 30 "
                           "teams need the full official minutes table (only the league top-50 is "
                           "committed), which is published here as an open item, not filled in.",
    }
    p = os.path.join(ROOT, "data", "derived", "travel_2026-11-16.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
    print("travel rows:", out["travel_coverage"])
    print("minutes rows:", len(minutes_rows))
    for r in minutes_rows[:4]:
        print("  ", r["team"], r["top8_share"], "pool", r["replacement_pool_share"],
              "out:", r["players_out_with_injury_reason"])
    print("wrote data/derived/travel_2026-11-16.json")


if __name__ == "__main__":
    main()
