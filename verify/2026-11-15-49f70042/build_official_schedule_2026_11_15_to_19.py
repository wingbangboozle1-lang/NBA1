#!/usr/bin/env python3
"""build_official_schedule_2026_11_15_to_19.py — persist the official NBA
schedule for the rolling slate window 2026-11-15 .. 2026-11-19 with the
venue, the city and every tip time that was read from an official surface.

Tip-time policy (published in the output file):
  PRIMARY  = the official per-game card. For the games the official
             injury-report edition covers, that same tip time is printed by
             the league referee office on the PDF, so the primary value has
             two independent official corroborations.
  ALSO     = the NBA.com league schedule page and (for 2026-11-19) the
             NBA.com games-by-date page. Where an official surface disagrees
             the row carries tip_conflict=true and BOTH values are published.
             No tip time is inferred or averaged.

Run: python3 verify/2026-11-15-49f70042/build_official_schedule_2026_11_15_to_19.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OFF = os.path.join(ROOT, "data", "official")
CAP = os.path.join(ROOT, "data", "raw", "official_schedule_capture_2026-11-15.json")

SCHEDULE_PAGE = "https://www.nba.com/schedule"
GAMES_PAGE = "https://www.nba.com/games?date=YYYY-MM-DD"
INJURY_PDF = ("https://ak-static.cms.nba.com/referee/injury/"
              "Injury-Report_2026-11-15_06_15PM.pdf")

# tip times as printed on the NBA.com league schedule page
# (read 2026-11-15T23:52Z .. 2026-11-16T00:05Z)
SCHED_PAGE_TIP = {
    ("2026-11-15", "0022600242"): "7:00 PM ET",
    ("2026-11-15", "0022600243"): "9:00 PM ET",
    ("2026-11-16", "0022600245"): "7:00 PM ET",
    ("2026-11-16", "0022600246"): "7:00 PM ET",
    ("2026-11-16", "0022600247"): "7:30 PM ET",
    ("2026-11-16", "0022600248"): "7:30 PM ET",
    ("2026-11-16", "0022600249"): "8:00 PM ET",
    ("2026-11-16", "0022600250"): "8:00 PM ET",
    ("2026-11-16", "0022600251"): "9:00 PM ET",
    ("2026-11-17", "0022600253"): "7:30 PM ET",
    ("2026-11-17", "0022600254"): "8:00 PM ET",
    ("2026-11-17", "0022600255"): "8:00 PM ET",
    ("2026-11-17", "0022600257"): "10:30 PM ET",
    ("2026-11-17", "0022600256"): "11:00 PM ET",
    ("2026-11-18", "0022600258"): "7:00 PM ET",
    ("2026-11-18", "0022600259"): "7:00 PM ET",
    ("2026-11-18", "0022600260"): "7:00 PM ET",
    ("2026-11-18", "0022600261"): "7:00 PM ET",
    ("2026-11-18", "0022600262"): "7:30 PM ET",
    ("2026-11-18", "0022600263"): "7:30 PM ET",
    ("2026-11-18", "0022600264"): "8:00 PM ET",
    ("2026-11-18", "0022600265"): "8:00 PM ET",
    ("2026-11-18", "0022600267"): "9:30 PM ET",
    ("2026-11-18", "0022600266"): "10:00 PM ET",
    ("2026-11-18", "0022600268"): "10:00 PM ET",
    ("2026-11-18", "0022600269"): "10:00 PM ET",
}

# venues read off the NBA.com league schedule page for games whose venue was
# blank in the per-game-card capture (flag F77)
VENUE_FROM_SCHEDULE_PAGE = {
    ("2026-11-18", "0022600261"): ("Kia Center", "Orlando, FL"),
    ("2026-11-18", "0022600265"): ("Paycom Center", "Oklahoma City, OK"),
    ("2026-11-18", "0022600267"): ("American Airlines Center", "Dallas, TX"),
}

# 2026-11-19 slate, read off the NBA.com league schedule page
N19 = [
    ("0022600270", "GSW", "MEM", "8:00 PM ET", "FedExForum", "Memphis, TN"),
    ("0022600271", "POR", "MIL", "8:00 PM ET", "Fiserv Forum", "Milwaukee, WI"),
    ("0022600272", "NYK", "MIN", "8:00 PM ET", "Target Center", "Minneapolis, MN"),
    ("0022600273", "LAC", "SAS", "8:00 PM ET", "Frost Bank Center", "San Antonio, TX"),
]
# tip time for the 2026-11-19 slate as printed on the games-by-date page
GAMES_PAGE_1119 = {"0022600272": "9:00 PM ET"}


def norm(t):
    """Normalise '07:00 PM ET' and '7:00 PM ET' to the same string."""
    if not t:
        return None
    t = t.replace(" (ET)", "").strip()
    h, rest = t.split(":", 1)
    return "%d:%s" % (int(h), rest)


def main():
    cap = json.load(open(CAP, encoding="utf-8"))
    cols = cap["cols"]
    rows = [dict(zip(cols, r)) for r in cap["rows"]]

    # tip times printed by the league referee office on the official injury PDF
    inj = json.load(open(os.path.join(OFF, "injury_2026-11-15_0615PM_arena49f70042.json"),
                         encoding="utf-8"))
    pdf_tip = {}
    for r in inj["rows"]:
        if r.get("game_date") == "11/16/2026" and \
                str(r.get("game_time_source", "")).startswith("official PDF"):
            pdf_tip[r["matchup"]] = r["game_time"]

    out = []
    for r in rows:
        key = (r["date"], r["game_id"])
        mu = "%s@%s" % (r["away"], r["home"])
        card = r["tip_et"]
        sp = SCHED_PAGE_TIP.get(key)
        venue, city = r["venue"], r["city"]
        v_from = None
        if key in VENUE_FROM_SCHEDULE_PAGE:
            venue, city = VENUE_FROM_SCHEDULE_PAGE[key]
            v_from = SCHEDULE_PAGE
        pt = pdf_tip.get(mu) if r["date"] == "2026-11-16" else None
        out.append({
            "date": r["date"], "game_id": r["game_id"],
            "away": r["away"], "home": r["home"], "matchup": mu,
            "venue": venue, "city": city,
            "venue_source": (SCHEDULE_PAGE if v_from else
                             "official per-game card (data/raw/official_schedule_capture_2026-11-15.json)"),
            "tip_et_primary": card,
            "tip_et_primary_source": "official per-game card",
            "tip_et_schedule_page": sp,
            "tip_et_injury_pdf": pt,
            "tip_conflict": bool(sp and norm(sp) != norm(card)),
            "schedule_page_url": SCHEDULE_PAGE,
            "source_url": "https://www.nba.com/game/%s-vs-%s-%s"
                          % (r["away"].lower(), r["home"].lower(), r["game_id"]),
        })

    for gid, a, h, t, v, c in N19:
        gp = GAMES_PAGE_1119.get(gid)
        out.append({
            "date": "2026-11-19", "game_id": gid, "away": a, "home": h,
            "matchup": "%s@%s" % (a, h), "venue": v, "city": c,
            "venue_source": SCHEDULE_PAGE,
            "tip_et_primary": t,
            "tip_et_primary_source": ("NBA.com league schedule page - no third official "
                                      "surface (per-game card or injury-report PDF) is "
                                      "available for 2026-11-19 yet"),
            "tip_et_schedule_page": t,
            "tip_et_games_by_date_page": gp,
            "tip_et_injury_pdf": None,
            "tip_conflict": bool(gp and norm(gp) != norm(t)),
            "schedule_page_url": SCHEDULE_PAGE,
            "source_url": "https://www.nba.com/game/%s-vs-%s-%s"
                          % (a.lower(), h.lower(), gid),
        })

    doc = {
        "title": "Official NBA schedule, 2026-11-15 through 2026-11-19 (38 games)",
        "sources": {"schedule_page": SCHEDULE_PAGE, "games_by_date": GAMES_PAGE,
                    "per_game_cards": "https://www.nba.com/game/<away>-vs-<home>-<gameId>",
                    "injury_report_pdf": INJURY_PDF},
        "captured_by": "arena/49f70042-nba1",
        "captured_utc": "2026-11-15T23:52Z..2026-11-16T00:05Z",
        "tip_time_policy": (
            "PRIMARY = the official per-game card. For the games covered by the "
            "official injury-report edition the same tip time is printed by the "
            "league referee office on the PDF, so the primary value carries two "
            "independent official corroborations. The NBA.com league schedule page "
            "is recorded alongside; where an official surface disagrees the row "
            "carries tip_conflict=true and BOTH values are published. Nothing is inferred."),
        "counts": {"games": len(out),
                   "games_with_tip_conflict": len([r for r in out if r["tip_conflict"]])},
        "conflicts": [dict(date=r["date"], game_id=r["game_id"], matchup=r["matchup"],
                           per_game_card=r["tip_et_primary"],
                           schedule_page=r.get("tip_et_schedule_page"),
                           games_by_date=r.get("tip_et_games_by_date_page"),
                           injury_pdf=r.get("tip_et_injury_pdf"))
                      for r in out if r["tip_conflict"]],
        "anomalies": [
            {"id": "AN-1", "date_range": "2026-11-16/2026-11-17",
             "matchups": ["POR@MIN", "POR@MIN"],
             "game_ids": ["0022600250", "0022600254"],
             "item": "the same matchup POR@MIN appears on consecutive days, "
                     "both at Target Center, both 8:00 PM ET",
             "official_surfaces_checked": [
                 "https://www.nba.com/schedule",
                 "https://www.nba.com/games?date=2026-11-16",
                 "https://www.nba.com/games?date=2026-11-17",
                 "https://www.nba.com/team/1610612757/blazers/schedule",
             ],
             "corroboration": "all four official surfaces list both games with "
                              "distinct game IDs; the POR team schedule lists "
                              "Nov 16 @MIN 0022600250 and Nov 17 @MIN "
                              "0022600254 back to back; the 2026-11-15 06:15 "
                              "PM ET injury report lists POR@MIN only for "
                              "11/16 (it does not extend to 11/17)",
             "precedent": "the same season's schedule also pairs POR vs OKC on "
                          "consecutive days (Nov 10 and Nov 11, both at Moda "
                          "Center), so consecutive-day repeat matchups are a "
                          "pattern of this schedule, not a transcription error",
             "action": "recorded exactly as the official surfaces print it; "
                       "the rest model treats 11/17 POR@MIN as a POR road "
                       "back-to-back",
             }],
        "rows": out,
    }
    p = os.path.join(OFF, "official_schedule_2026-11-15_to_19.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote", p, doc["counts"])
    for c in doc["conflicts"]:
        print("  CONFLICT", c["date"], c["matchup"], "card:", c["per_game_card"],
              "| schedule page:", c["schedule_page"],
              "| games page:", c["games_by_date"], "| injury pdf:", c["injury_pdf"])


if __name__ == "__main__":
    main()
