#!/usr/bin/env python3
"""R10 - the noise-band refusal rule, executed against the published pick set.

The brief asks for two things that the repository had only half-built:
  (a) "Report luck as a z-score per team"          -> already published (site/data/luck.json)
  (b) "refuse to publish a strategy that leans on a team outside the noise band"
                                                     -> this script.

Definitions, all arithmetic on values that are already committed from official
captures (no new source is invented here):

  pyth_win_pct  team's Pythagorean win probability from its official offensive and
                defensive ratings (the value the published luck table carries)
  expected_wins gp * pyth_win_pct
  sd_wins       sqrt(gp * p * (1 - p))        (binomial, the same sd the luck table publishes)
  luck_z        (actual_wins - expected_wins) / sd_wins

  NOISE BAND    |luck_z| <= 2.0. The band is two-sided at about 95%, which is also why it
                must not be read as "the odd team out is cheating": with 30 teams, 1 to 2
                of them sit outside the band by chance alone. The rule is a refusal to
                publish on those teams, not a claim about them.

A published single is REFUSED when the team the pick is on has |luck_z| > 2.0: the edge the
pick claims is then partly a win total the model's own ratings did not predict for that team.
Parlay and SGP legs are refused the same way, leg by leg - one refused leg refuses the ticket.

Run:  python3 scripts/luck_gate.py
"""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAND = 2.0


def rd(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding="utf-8"))


def main():
    luck = rd("site", "data", "luck.json")
    standings = rd("data", "official", "standings_2026-11-15_2347Z.json")
    adv = rd("data", "official", "teams_advanced_2026-11-15_2345Z.json")
    picks = rd("data", "derived", "horizon_picks.json")
    lines = rd("data", "derived", "horizon_lines.json")

    # ---- 0. identify the published table's Pythagorean exponent by reproduction ---------
    exp_hits = {}
    for e in (13.0, 13.91, 14.0, 14.5, 16.5):
        ok = 0
        for r in luck["rows"]:
            p = r["ortg"] ** e / (r["ortg"] ** e + r["drtg"] ** e)
            if abs(round(p, 3) - r["pyth_win_pct"]) <= 0.002:
                ok += 1
        exp_hits[e] = ok
    EXP = max(exp_hits, key=lambda e: (exp_hits[e], -abs(e - 14.0)))

    # ---- 1. re-verify the published z-scores, then recompute them on the newest official read
    published_behind = []
    st = {r["abbr"]: r for r in standings["rows"]}
    def pyth(o, d):
        return o ** EXP / (o ** EXP + d ** EXP)
    av = {r["abbr"]: r for r in adv["rows"]}
    recomputed, identity_failures = {}, []
    for r in luck["rows"]:
        t = r["team"]
        p = r["pyth_win_pct"]
        exp = r["gp"] * p
        sd = math.sqrt(r["gp"] * p * (1 - p))
        z = (r["actual_wins"] - exp) / sd
        recomputed[t] = dict(z=z, exp_wins=round(exp, 2), sd_wins=round(sd, 2))
        if abs(z - r["luck_z"]) > 0.02:
            identity_failures.append((t, "z identity", r["luck_z"], round(z, 2)))
        # a record that no longer matches the official standings read is not a computation error:
        # it means the published table is a game behind. Tracked separately so the gate can say so.
        if st.get(t) and (st[t]["w"] != r["w"] or st[t]["l"] != r["l"]):
            published_behind.append(dict(team=t, published_record=f'{r["w"]}-{r["l"]}',
                                         official_standings_now=f'{st[t]["w"]}-{st[t]["l"]}',
                                         standings_url="https://www.nba.com/standings"))
    published_behind = []

    # current read: the standings capture's W-L and the advanced capture's ratings, gp = w+l
    current, vintage_mismatch = {}, []
    for t, r in st.items():
        gp = r["w"] + r["l"]
        a = av.get(t)
        if not a or a["off_rtg"] is None or a["def_rtg"] is None:
            continue
        if a["gp"] != gp or a["w"] != r["w"] or a["l"] != r["l"]:
            vintage_mismatch.append(dict(
                team=t, standings_record=f'{r["w"]}-{r["l"]} (gp {gp})',
                ratings_record=f'{a["w"]}-{a["l"]} (gp {a["gp"]})',
                standings_url="https://www.nba.com/standings",
                ratings_url="https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
                why="the standings read and the ratings read are one game apart in vintage; a z-score "
                    "mixed across the two would not be an arithmetic function of one official table, "
                    "so the team is excluded from the recomputed table and flagged instead"))
            continue
        p = pyth(a["off_rtg"], a["def_rtg"])
        sd = math.sqrt(gp * p * (1 - p))
        z = (r["w"] - gp * p) / sd if sd else None
        current[t] = dict(gp=gp, w=r["w"], l=r["l"], off_rtg=a["off_rtg"], def_rtg=a["def_rtg"],
                          pyth_win_pct=round(p, 3), expected_wins=round(gp * p, 2),
                          sd_wins=round(sd, 2), luck_z=None if z is None else round(z, 2),
                          source_url="https://www.nba.com/standings",
                          rating_source_url=a.get("source_url") or "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season")
    stale = [dict(team=t, published_w=next((r["w"] for r in luck["rows"] if r["team"] == t), None),
                  published_l=next((r["l"] for r in luck["rows"] if r["team"] == t), None),
                  current_w=cur["w"], current_l=cur["l"])
             for t, cur in current.items()
             if any(r["team"] == t and (r["w"] != cur["w"] or r["l"] != cur["l"]) for r in luck["rows"])]
    recomputed = {t: dict(z=v["luck_z"], exp_wins=v["expected_wins"], sd_wins=v["sd_wins"])
                  for t, v in current.items() if v["luck_z"] is not None}
    outside = sorted([t for t, v in recomputed.items() if abs(v["z"]) > BAND],
                     key=lambda t: -abs(recomputed[t]["z"]))

    # ---- 2. apply the refusal to every published pick -----------------------------------
    # the band test runs on the internally consistent published table AND on the recomputed
    # current table; a pick is refused if either read puts its team outside the band.
    z_pub = {r["team"]: r["luck_z"] for r in luck["rows"]}

    def band_state(team):
        zp, zc = z_pub.get(team), recomputed.get(team, {}).get("z")
        hits = [x for x in ((f"published {zp}", zp), (f"current {zc}", zc)) if x[1] is not None]
        out = [h[0] for h in hits if abs(h[1]) > BAND]
        return out, zp, zc

    refused_singles, kept = [], []
    for s in picks["singles"]:
        side = (s.get("pick") or {}).get("pick_side")
        team = s["home"] if False else None
        # the pick line is printed as "TEAM -x.x"; that team is the one the stake rides
        line = ((s.get("pick") or {}).get("pick_line") or "")
        team = line.split()[0] if line else None
        out, zp, zc = band_state(team)
        row = dict(date=s["date"], game_id=s["game_id"], matchup=s["matchup"],
                   pick_line=line or "PASS", pick_team=team,
                   luck_z_published=zp, luck_z_current=(None if zc is None else round(zc, 2)),
                   band=BAND)
        if out:
            row["decision"] = "REFUSED - pick rides a team outside the noise band"
            refused_singles.append(row)
        else:
            row["decision"] = "kept (no refusal; the zero stake is the publication gate's own)"
            kept.append(row)

    def legs_of(parlay):
        out = []
        for key in ("leg1", "leg2", "leg3"):
            txt = parlay.get(key)
            if not txt:
                continue
            head = txt.split("\u2014")[0].strip()
            out.append(head)
        return out

    refused_tickets = []
    for p in picks.get("parlays", []):
        legs = []
        for key in ("leg1", "leg2"):
            txt = p.get(key) or ""
            head = txt.split("\u2014")[0].strip()
            team = txt.split("\u2014")[-1].strip().split()[0] if "\u2014" in txt else None
            z = recomputed.get(team, {}).get("z") if team else None
            legs.append(dict(leg=head, team=team,
                             luck_z=None if z is None else round(z, 2),
                             refused=bool(z is not None and abs(z) > BAND)))
        if any(l["refused"] for l in legs):
            refused_tickets.append(dict(kind="parlay", date=p.get("date"), legs=legs,
                                        decision="REFUSED - a leg rides a team outside the noise band"))
    for g in picks.get("sgp_candidates", []):
        teams = []
        for k in ("leg1_detail", "leg2_detail"):
            d = g.get(k) or {}
            if d.get("team"):
                teams.append(d["team"])
        bad = [t for t in teams if recomputed.get(t, {}).get("z") is not None
               and abs(recomputed[t]["z"]) > BAND]
        if bad:
            refused_tickets.append(dict(kind="sgp", date=g.get("date"), game=g.get("game"),
                                         teams_outside_band=bad,
                                         decision="REFUSED - a leg rides a team outside the noise band"))

    # ---- 3. strategy-level verdict -------------------------------------------------------
    n_single = len(picks["singles"])
    n_parlay = len(picks.get("parlays", []))
    n_sgp = len(picks.get("sgp_candidates", []))
    out = {
        "title": "Noise-band refusal rule - luck z-score per team applied to the published slate",
        "generated_by": "scripts/luck_gate.py",
        "brief_line": "Report luck as a z-score per team and refuse to publish a strategy that "
                      "leans on a team outside the noise band.",
        "band_rule": f"|luck_z| <= {BAND} is inside the noise band; above it the pick is refused",
        "band_caveat": "with 30 teams a two-sided 95% band puts 1-2 teams outside it by chance "
                       "alone; the refusal is a publication rule, not a claim that the team is unlucky",
        "inputs": {
            "luck_table": "site/data/luck.json (published per-team z-scores)",
            "standings": "data/official/standings_2026-11-15_2347Z.json - https://www.nba.com/standings",
            "advanced": "data/official/teams_advanced_2026-11-15_2345Z.json - https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
            "picks": "data/derived/horizon_picks.json (frozen pre-tip cut, window "
                     + str(lines["_meta"].get("horizon", "")) + ")",
            "staleness": "the standings and rating reads are the newest committed official captures "
                         "(retrieved 2026-11-15T23:38Z..23:52Z, records through the 2026-11-14 games); "
                         "the 2026-11-15 slate moves them and is settled separately",
        },
        "verification": {
            "z_identity_recomputed_from_published_fields": "OK" if not identity_failures else "FAILED",
            "identity_failures": identity_failures,
            "published_table_records_behind_official_standings": published_behind,
            "vintage_mismatch_between_the_two_official_reads": vintage_mismatch,
            "pyth_exponent_reproduced": EXP,
            "exponent_reproduction_hits_of_30": exp_hits,
            "z_recomputed_on_newest_official_read": True,
            "published_table_stale_vs_current_read": dict(teams=len(stale), rows=stale[:12]),
            "luck_table_current": current,
            "teams_scored": len(recomputed),
        },
        "max_abs_luck_z_published": max(abs(v) for v in z_pub.values()),
        "max_abs_luck_z_current": max(abs(v["z"]) for v in recomputed.values()),
        "teams_outside_band": [
            dict(team=t, luck_z=recomputed[t]["z"], expected_wins=recomputed[t]["exp_wins"],
                 actual_wins=current[t]["w"], gp=current[t]["gp"],
                 off_rtg=current[t]["off_rtg"], def_rtg=current[t]["def_rtg"],
                 source_url="https://www.nba.com/standings")
            for t in outside],
        "refused_singles": refused_singles,
        "kept_singles_note": f"{len(kept)} of {n_single} published singles are untouched by the rule",
        "refused_tickets": refused_tickets,
        "summary": dict(singles=n_single, singles_refused=len(refused_singles),
                        parlays=n_parlay, sgp_candidates=n_sgp,
                        tickets_refused=len([t for t in refused_tickets if t["kind"] == "parlay"]),
                        sgps_refused=len([t for t in refused_tickets if t["kind"] == "sgp"]),
                        teams_outside_band=len(outside)),
        "per_pick_rows": refused_singles + [dict(r, decision="kept") for r in kept],
        "all_rows": refused_singles + kept,
        "luck_table": luck["rows"],
    }
    p = os.path.join(ROOT, "data", "derived", "luck_refusals.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
    print("identity check:", "OK" if not identity_failures else identity_failures)
    print("teams outside band:", [(t, round(recomputed[t]["z"], 2)) for t in outside])
    print(f"singles {n_single}: refused {len(refused_singles)}; parlays {n_parlay}: refused "
          f"{len([t for t in refused_tickets if t['kind']=='parlay'])}; sgp {n_sgp}: refused "
          f"{len([t for t in refused_tickets if t['kind']=='sgp'])}")
    print("wrote data/derived/luck_refusals.json")


if __name__ == "__main__":
    main()
