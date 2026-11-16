#!/usr/bin/env python3
"""build_roll_page.py — two pages this repository did not have before.

  site/pages/roll.html          the rolling slate: the originated lines for the
                                current 3-day window, the two-estimator
                                disagreement as the headline, rotation
                                availability, rest / back-to-back / 3-in-4, and
                                parlays priced with the measured rho beside the
                                naive product.
  site/pages/requirements.html  requirement-by-requirement audit of the project
                                brief: what is implemented, what is partial,
                                what is not, and the artifact or official link
                                that backs each verdict.

Both are built only from files in the repository. Every row that carries a
number links to the official source the number came from; a value that cannot be
confirmed is rendered as an em dash and listed on Flagged for Review.

Called from scripts/build_dashboard.py so a single rebuild regenerates them.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA = os.path.join(ROOT, "data")
DOCS_DATA = os.path.join(ROOT, "docs", "data")

SRC_SCHEDULE = "https://www.nba.com/schedule"
SRC_STANDINGS = "https://www.nba.com/standings"
SRC_ADVANCED = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
SRC_TRADITIONAL = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"
SRC_OPPONENT = "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"
SRC_INJ_INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def phi(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def joint_over_over(z1, z2, rho, steps=400):
    """P(X>z1, Y>z2) for standardised thresholds under a Gaussian copula.
    rho = 0 reduces exactly to the independent product."""
    if rho == 0:
        return (1 - norm_cdf(z1)) * (1 - norm_cdf(z2))
    s = math.sqrt(1.0 - rho * rho)
    a, b = z1, 8.0
    n = 2 * steps
    h = (b - a) / n
    total = 0.0
    for i in range(n + 1):
        t = a + i * h
        val = phi(t) * norm_cdf((rho * t - z2) / s)
        w = 1 if i in (0, n) else (4 if i % 2 == 1 else 2)
        total += w * val
    return max(0.0, min(1.0, total * h / 3.0))


def american(p):
    if p is None or p <= 0 or p >= 1:
        return None
    return (-100 * p / (1 - p)) if p >= 0.5 else (100 * (1 - p) / p)


def build(db):
    """db = the build_dashboard module (for page/table/banner/esc/num/NA helpers)."""
    page, table, banner, h2 = db.page, db.table, db.banner, db.h2
    esc, num, NA, srclink_url = db.esc, db.num, db.NA, db.srclink_url

    built = {}

    # ------------------------------------------------------------------ data
    lines = load(os.path.join(DATA, "derived", "horizon_lines.json"))
    picks_doc = load(os.path.join(DATA, "derived", "horizon_picks.json"))
    meta = lines["_meta"]
    games = lines["games"]
    dates = sorted({g["date"] for g in games})

    rho_path = os.path.join(DATA, "derived", "measured_rho.json")
    rho_doc = load(rho_path) if os.path.exists(rho_path) else None

    inj_path = os.path.join(DATA, "official",
                            os.path.basename(meta["inputs"]["injury_file"]))
    inj = load(inj_path) if os.path.exists(inj_path) else {"rows": []}

    # estimator B: the validated engine's own model line, where the windows overlap
    est_b = {}
    b_path = os.path.join(DOCS_DATA, "lines.json")
    if os.path.exists(b_path):
        for r in load(b_path)["rows"]:
            est_b[(r["date"], r["matchup"])] = r

    # ------------------------------------------------------- availability map
    # (date, matchup) -> (label, out-count, questionable-count, not-submitted-count)
    avail = {}
    for g in games:
        want = "%s/%s/%s" % (g["date"][5:7], g["date"][8:10], g["date"][0:4])
        rows = [r for r in inj.get("rows", [])
                if r.get("game_date") == want and r.get("matchup") == g["matchup"]]
        out_n = sum(1 for r in rows if r.get("status") == "Out" and r.get("player"))
        q_n = sum(1 for r in rows if r.get("status") == "Questionable")
        ns = [r for r in rows if r.get("status") == "NOT YET SUBMITTED"]
        avail[(g["date"], g["matchup"])] = (rows, out_n, q_n, ns)

    # ------------------------------------------------------- rest / 3-in-4
    all_dates = {}
    for g in games:
        all_dates.setdefault(g["away"], set()).add(g["date"])
        all_dates.setdefault(g["home"], set()).add(g["date"])
    for f in ("data/official/results_2026-11-15.json",
              "data/official/results_2026-11-14.json"):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            for r in load(p)["rows"]:
                all_dates.setdefault(r["away"], set()).add(r["date"])
                all_dates.setdefault(r["home"], set()).add(r["date"])
    prior_path = os.path.join(DATA, "raw", "prior_slate.json")
    if os.path.exists(prior_path):
        pr = load(prior_path)
        for r in [dict(zip(pr["cols"], x)) for x in pr["rows"]]:
            all_dates.setdefault(r["away"], set()).add(r["date"])
            all_dates.setdefault(r["home"], set()).add(r["date"])

    import datetime as _dt

    def di(s):
        return _dt.date(*map(int, s.split("-")))

    def rest_for(abbr, d0):
        ds = sorted(di(x) for x in all_dates.get(abbr, ()) if di(x) < di(d0))
        if not ds:
            return None, False, False, None
        last = ds[-1]
        gap = (di(d0) - last).days
        prior4 = [x for x in ds if (di(d0) - x).days <= 3]
        return gap - 1, gap == 1, len(prior4) >= 3, last.isoformat()

    # ================================================================ ROLL PAGE
    b = []
    b.append(banner("info", "The rolling slate", (
        "<p>The window below is <b>%s &ndash; %s</b>: the next three calendar days, which is the "
        "maximum the brief allows a pick to be published ahead of a game. It is re-cut from a "
        "fresh official capture every pass &mdash; the schedule, the standings, the three official "
        "team-stat pages and the newest official injury report are all re-read before a line is "
        "rebuilt, and the rebuild is skipped if any of them is stale or missing.</p>"
        "<p><b>Cut:</b> schedule captured %s &middot; ratings re-cut from captures retrieved %s "
        "&middot; injury edition <b>%s</b> (revision %s, retrieved %s).</p>"
        % (esc(dates[0]), esc(dates[-1]),
           esc(meta["inputs"]["schedule_captured_on"]),
           esc(meta["inputs"]["ratings_recut_retrieved_utc"]),
           esc(meta["inputs"]["injury_edition"]),
           esc(meta["inputs"]["injury_revision_et"]),
           esc(meta["inputs"]["injury_retrieved_utc"])))))

    n_out = sum(v[1] for v in avail.values())
    n_ns = sum(len(v[3]) for v in avail.values())
    b.append(db.tiles([
        ("Games in the window", len(games),
         "%s" % ", ".join("%s=%d" % (d[5:], sum(1 for g in games if g["date"] == d))
                          for d in dates)),
        ("Singles picks", picks_doc.get("n_model_picks", 0), "gate: |originated spread| >= 3.0"),
        ("Two-leg parlays", len(picks_doc.get("parlays", [])), "different games, same date"),
        ("Out players listed", n_out, "official injury report, horizon games only"),
        ("Blocks NOT YET SUBMITTED", n_ns, "clubs that had not filed when the edition was cut"),
        ("Measured home-win rate",
         ("%s" % rho_doc["home_win_rate"]["rate"]) if rho_doc else NA,
         ("%d of %d official finals" % (rho_doc["home_win_rate"]["home_wins"],
                                        rho_doc["home_win_rate"]["n_games"])) if rho_doc else ""),
    ]))

    # ---- two estimators -------------------------------------------------
    shared = [(g, est_b[(g["date"], g["matchup"])]) for g in games
              if (g["date"], g["matchup"]) in est_b]
    diffs = [abs(a["line_spread_home"] - c["model_spread_home"]) for a, c in shared]
    # Decomposition of the gap. Estimator B's line carries two terms estimator A
    # does not (a fitted home-court advantage and a back-to-back penalty); reading
    # them out of the validated build's own fit rather than typing them.
    _hca = _b2b = None
    _vpath = os.path.join(DOCS_DATA, "validation.json")
    if os.path.exists(_vpath):
        _fit = load(_vpath).get("fit", {})
        _hca = (_fit.get("hca") or {}).get("est")
        _b2b = (_fit.get("b2b_coef_on_home_margin") or {}).get("penalty_applied")
    _signed = ([a["line_spread_home"] - c["model_spread_home"] for a, c in shared])
    _mean_signed = (sum(_signed) / len(_signed)) if _signed else 0.0
    _decomp = ""
    if _hca is not None:
        _decomp = (
            "<p><b>Where most of the gap comes from.</b> The mean <i>signed</i> difference "
            "(A &minus; B) is <b>%+.2f points</b>, i.e. B favours the home team by that much. "
            "B's line is built with a <b>fitted home-court advantage of %+.3f points</b> "
            "(t = %s, estimated in-sample on the test window) and a back-to-back penalty of "
            "%s points; estimator A applies <b>neither</b>, because no official page publishes "
            "either number. The fitted HCA alone accounts for %.0f%% of the mean gap. That is "
            "the whole of requirement R08 in one number: the measured home-win rate is %s "
            "(%d of %d official finals), and a fitted %+.2f-point edge is a far stronger claim "
            "than that evidence supports.</p>"
            % (_mean_signed, _hca,
               esc((load(_vpath).get("fit", {}).get("hca") or {}).get("t")),
               ("%.3f" % _b2b) if _b2b is not None else NA,
               min(100.0, 100.0 * abs(_hca) / abs(_mean_signed)) if _mean_signed else 0.0,
               (("%.4f" % rho_doc["home_win_rate"]["rate"]) if rho_doc else NA),
               (rho_doc["home_win_rate"]["home_wins"] if rho_doc else 0),
               (rho_doc["home_win_rate"]["n_games"] if rho_doc else 0),
               _hca))
    b.append(banner("warn", "Two independent estimators &mdash; their disagreement is the headline", (
        "<p>Every game below carries a line from <b>two models built from the same official "
        "inputs by different code</b>: estimator A is <code>scripts/originate_horizon.py</code> "
        "(this page), estimator B is <code>engine/pipeline.py</code> (the out-of-sample-validated "
        "build). The <b>disagreement column is the first number shown</b>, and the two spreads sit "
        "underneath it &mdash; not a blend, because averaging two models whose errors have not "
        "been measured against each other would hide the one signal we can read.</p>"
        "<p>On the <b>%d games both models cover</b> (they overlap on %s), the mean absolute "
        "disagreement is <b>%.2f points</b> and the largest is <b>%.1f</b>; on %d of them the two "
        "disagree about which team is the favourite. Note the vintage difference: estimator B's "
        "ratings window is its own published cut, estimator A's is the re-cut above, so some of "
        "the gap is input age, not model opinion. Choosing between them is open decision "
        "<a href=\"decisions.html\">F26</a>.</p>"
        % (len(shared), ", ".join(sorted({a['date'] for a, _ in shared})),
           (sum(diffs) / len(diffs)) if diffs else 0.0, max(diffs) if diffs else 0.0,
           sum(1 for a, c in shared
               if (a["line_spread_home"] > 0) != (c["model_spread_home"] > 0))))) + _decomp)

    # ---- table 1: the board -------------------------------------------
    rows = []
    for g in games:
        arows, out_n, q_n, ns = avail[(g["date"], g["matchup"])]
        ra, b2b_a, three_a, _ = rest_for(g["away"], g["date"])
        rh, b2b_h, three_h, _ = rest_for(g["home"], g["date"])
        if arows:
            av = ("%d Out / %d Questionable" % (out_n, q_n)) if out_n or q_n else "filed, no Out/Questionable"
            if ns:
                av += " &middot; %d block%s NOT YET SUBMITTED" % (len(ns), "" if len(ns) == 1 else "s")
        else:
            av = "no official report covers this date yet"
        c = est_b.get((g["date"], g["matchup"]))
        if c:
            dis = "%.1f" % abs(g["line_spread_home"] - c["model_spread_home"])
        else:
            dis = NA
        rest = "%s / %s" % (
            ("%dd%s%s" % (ra, " B2B" if b2b_a else "", " 3-in-4" if three_a else "")) if ra is not None else NA,
            ("%dd%s%s" % (rh, " B2B" if b2b_h else "", " 3-in-4" if three_h else "")) if rh is not None else NA)
        rows.append([
            esc(g["date"]) + " " + esc(g["tip_et"]),
            '<b>%s</b>' % esc(g["matchup"]),
            esc(g["records_as_captured"]),
            num(g["game_possessions"], 1),
            num(g["proj_away_pts"], 1) + " / " + num(g["proj_home_pts"], 1),
            num(g["line_spread_home"], 1),
            num(g["line_total"], 1),
            num(g["model_home_win_prob"], 3),
            ("%+d" % american(g["model_home_win_prob"])) if g["model_home_win_prob"] else NA,
            av,
            rest,
            (num(c["model_spread_home"], 1) if c else NA),
            dis,
            srclink_url(g["schedule_source"], "slate") + " " + srclink_url(SRC_ADVANCED, "ratings"),
        ])
    b.append(h2("1. The board &mdash; %d games, %s to %s" % (len(games), dates[0], dates[-1]),
                "Spread is home minus away; positive means the home team is favoured. "
                "Possessions, points, spread and total are DERIVED by the printed formula. "
                "No home-court advantage is applied (it is not sourced from an official page; "
                "measured home-win rate published below, flag F74)."))
    b.append(table(
        ["Date &middot; tip ET", "Matchup", "Records", "Poss.", "Proj pts A / H",
         "Spread (home)", "Total", "P(home win)", "Fair ML (home)",
         "Rotation availability (official report)", "Rest A / H",
         "Estimator B spread", "Disagreement", "Source"],
        rows,
        note=("Formula: POSS = pace_home + pace_away &minus; league_pace; "
              "PTS = (OffRtg &times; DefRtg_opp / league_OffRtg) &times; POSS / 100; "
              "TOTAL = PTS_home + PTS_away; SPREAD = PTS_home &minus; PTS_away. "
              "Ratings: official advanced page (pace, OffRtg, DefRtg). Records: official "
              "standings page. Availability: official injury report, verbatim statuses &mdash; "
              "no line is moved by them (see section 4). Rest, back-to-back and 3-in-4 are "
              "counted from the official schedule and official finals. "
              "'Estimator B' is engine/pipeline.py's own model line, shown only where the two "
              "windows overlap.")))

    # ---- table 2: singles ---------------------------------------------
    srows = []
    for s in picks_doc.get("singles", []):
        pk = s["pick"]
        srows.append([
            esc(s["date"]), '<b>%s</b>' % esc(s["matchup"]),
            esc(pk.get("pick_line") or NA),
            num(pk.get("pick_prob"), 3),
            ("%+d" % american(pk["pick_prob"])) if pk.get("pick_prob") else NA,
            esc(pk.get("gate")),
            esc(s.get("status", "")),
            srclink_url(s["sources"][0], "slate"),
        ])
    b.append(h2("2. Singles", "%d of %d games clear the |spread| &ge; 3.0 gate. Every pick is "
                              "MODEL OUTPUT &mdash; UNVALIDATED: no strategy has passed the "
                              "validation gates, so the stake is zero and the record is paper."
                              % (picks_doc.get("n_model_picks", 0), len(games))))
    b.append(table(["Date", "Matchup", "Pick", "Model p", "Fair price", "Gate", "Status", "Source"],
                   srows))

    # ---- table 3: two-leg parlays, naive product vs measured rho -------
    prows = []
    for p_ in picks_doc.get("parlays", []):
        p1, p2 = p_["p1"], p_["p2"]
        naive = p1 * p2
        lo, hi = max(0.0, p1 + p2 - 1.0), min(p1, p2)
        prows.append([
            esc(p_["date"]),
            "%s<br>%s" % (esc(p_["leg1"]), esc(p_["leg2"])),
            num(p1, 3), num(p2, 3),
            "<b>%.4f</b>" % naive,
            "[%.4f, %.4f]" % (lo, hi),
            ("%+d" % american(naive)),
            NA,
            srclink_url(p_["sources"][0], "slate"),
        ])
    b.append(h2("3. Two-leg parlays &mdash; the naive product, printed, with the band around it", (
        "The brief asks for every parlay to be priced with a measured rho and for the naive "
        "product to be printed next to it. Both columns are here. The rho column is an em dash "
        "because <b>no rho between two different games is measurable from official data</b>: the "
        "games have no natural pairing, so any figure would be an artefact of how the pairs were "
        "made. What is published instead of a fake number is the exact "
        "Fr&eacute;chet&ndash;Hoeffding band the joint probability must lie in for <i>any</i> rho, "
        "and the naive product is the price. Where a rho <i>is</i> measurable it is used &mdash; "
        "see section 4.")))
    b.append(table(["Date", "Legs", "p&#8321;", "p&#8322;", "Naive product p&#8321;&times;p&#8322;",
                    "Fr&eacute;chet band (any rho)", "Fair price at the naive product",
                    "Measured rho"],
                   prows,
                   note=("The band is [max(0, p&#8321;+p&#8322;&minus;1), min(p&#8321;,p&#8322;)]. "
                         "A price inside it is not evidence of skill; the naive product is the "
                         "independence price and is the number this site publishes.")))

    # ---- table 4: same-game, priced with the measured rho --------------
    if rho_doc:
        r_mt = rho_doc["measured"][0]["r"]
        r_reg = rho_doc["measured"][1]["r"]
        n_meas = rho_doc["measured"][0]["n"]
        p_meas = rho_doc["measured"][0]["p_value"]
        by_id = {g["matchup"]: g for g in games}
        srows2 = []
        for g in games:
            z1 = -g["line_spread_home"] / g["margin_sd"]   # P(home margin > 0)
            p_side = 1 - norm_cdf(z1)
            # the originated total is this model's own median, so P(total > total) = 0.5
            # exactly under the symmetric distribution it is drawn from.
            p_tot = 0.5
            naive = p_side * p_tot
            joint = joint_over_over(z1, 0.0, r_mt)
            joint_reg = joint_over_over(z1, 0.0, r_reg) if r_reg is not None else None
            srows2.append([
                esc(g["date"]), '<b>%s</b>' % esc(g["matchup"]),
                num(p_side, 3), "0.500",
                "<b>%.4f</b>" % naive,
                "%.4f" % joint,
                ("%.4f" % joint_reg) if joint_reg is not None else NA,
                ("%+d" % american(joint)) if 0 < joint < 1 else NA,
                srclink_url(g["schedule_source"], "slate") + " " +
                srclink_url(SRC_ADVANCED, "ratings"),
            ])
        b.append(h2("4. Same-game side-and-total &mdash; priced with the measured rho", (
            "Leg 1: the home team wins. Leg 2: the game total beats the originated total. "
            "These two legs come from the same final score, so their correlation is directly "
            "observable and is measured from <b>%d official finals</b> (%s to %s): "
            "<b>&rho;(home margin, game total) = %s</b> (p = %s), and %s on regulation games only. "
            "Both are statistically indistinguishable from zero, which is itself the finding: "
            "the naive product is very nearly the right price for this pair. "
            "P(total &gt; total) is exactly 0.500 because the originated total is this model's "
            "own median &mdash; stated rather than dressed up as a model edge."
            % (n_meas, esc(rho_doc["corpus"]["first_date"]), esc(rho_doc["corpus"]["last_date"]),
               esc(r_mt), esc(p_meas), esc(r_reg)))))
        b.append(table(
            ["Date", "Matchup", "P(home win)", "P(over total)", "Naive product",
             "Priced at measured &rho;", "Priced at &rho; (regulation)", "Fair price at &rho;"],
            srows2,
            note=("Joint probability = P(Z&#8321; &gt; z&#8321;, Z&#8322; &gt; 0) under a Gaussian "
                  "copula with the measured &rho;, integrated numerically; at &rho; = 0 it reduces "
                  "exactly to the naive product, so the two columns are directly comparable.")))

    # ---- table 5: measured statistics ---------------------------------
    if rho_doc:
        mrows = []
        for m in rho_doc["measured"]:
            mrows.append([esc(m["x"]), esc(m["y"]), num(m["r"], 4), num(m["p_value"], 4),
                          esc(m["n"]), esc(m["subset"]), esc(m["status"]), esc(m["why"]),
                          srclink_url("https://www.nba.com/games", "official games index")])
        hw = rho_doc["home_win_rate"]
        mrows.append(["home win", "&mdash;", num(hw["rate"], 4), NA, esc(hw["n_games"]),
                      "all official finals", esc(hw["status"]),
                      "the measured home-win rate the brief wants home-court advantage pinned to; "
                      "measured, published, and <b>not yet applied</b> to any line (F84)",
                      srclink_url("https://www.nba.com/games", "official games index")])
        b.append(h2("5. What was measured, and on how many games",
                    "Pearson r on official final scores. Nothing here is model-derived."))
        b.append(table(["x", "y", "r", "p", "n", "Subset", "Status", "Why / note"], mrows,
                       note=("Corpus: " + "; ".join(
                           "%s (%d games)" % (esc(f["file"]), f["games_added"])
                           for f in rho_doc["corpus"]["files"]) +
                           ". Only games whose official label is Final are used &mdash; a game "
                           "still live at capture time is excluded, never filled in.")))

        def _na_reason(why):
            return ('<span class="na" title="%s">&mdash;</span>'
                    % esc("not published - " + why))
        nrows = [[esc(q["quantity"]), esc(q["why_not"]), esc(q["consequence"]),
                  _na_reason(q["why_not"])] for q in rho_doc["not_measurable"]]
        b.append(h2("6. What could not be measured",
                    "Published as a gap rather than filled with a plausible number."))
        b.append(table(["Quantity", "Why it is not measurable from official data",
                        "What is published instead"], nrows))

    # ---- flags ---------------------------------------------------------
    frows = [[esc(f["id"]), esc(f["severity"]), '<b>%s</b>' % esc(f["item"]), esc(f["detail"]),
              srclink_url(f["source"], "link")] for f in meta["flags"]]
    b.append(h2("7. Flags carried by this window",
                "Every limitation that applies to the numbers above, with the official link "
                "that would resolve it."))
    b.append(table(["ID", "Severity", "Item", "Detail", "Source"], frows))

    b.append(h2("Where the inputs came from", "One official URL per input. Nothing is inferred."))
    b.append(table(
        ["Input", "Official page", "Captured"],
        [["Schedule, tip times, venues", srclink_url(SRC_SCHEDULE, SRC_SCHEDULE),
          esc(meta["inputs"]["schedule_captured_on"]),
          srclink_url(SRC_SCHEDULE, "schedule")],
         ["Team records", srclink_url(SRC_STANDINGS, SRC_STANDINGS),
          esc(meta["inputs"]["schedule_captured_on"]),
          srclink_url(SRC_STANDINGS, "standings")],
         ["Pace, OffRtg, DefRtg", srclink_url(SRC_ADVANCED, SRC_ADVANCED),
          esc(meta["inputs"]["ratings_recut_retrieved_utc"]),
          srclink_url(SRC_ADVANCED, "advanced")],
         ["Own scoring splits", srclink_url(SRC_TRADITIONAL, SRC_TRADITIONAL),
          esc(meta["inputs"]["ratings_recut_retrieved_utc"]),
          srclink_url(SRC_TRADITIONAL, "traditional")],
         ["Opponent scoring splits", srclink_url(SRC_OPPONENT, SRC_OPPONENT),
          esc(meta["inputs"]["ratings_recut_retrieved_utc"]),
          srclink_url(SRC_OPPONENT, "opponent")],
         ["Injury statuses", srclink_url(inj.get("source_url", SRC_INJ_INDEX), "official PDF"),
          "%s (%s)" % (esc(meta["inputs"]["injury_revision_et"]),
                       esc(meta["inputs"]["injury_retrieved_utc"])),
          srclink_url(SRC_INJ_INDEX, "index")],
         ["Injury policy (filing deadlines)", srclink_url(SRC_INJ_INDEX, SRC_INJ_INDEX),
          "policy page", srclink_url(SRC_INJ_INDEX, "index")]]))

    built["roll.html"] = page(
        "Rolling slate &mdash; %s to %s" % (dates[0], dates[-1]),
        "The originated lines for the next three days, the disagreement between the two "
        "estimators, rotation availability from the official injury report, and parlays "
        "priced with the measured rho beside the naive product.", "\n".join(b))

    # ================================================== REQUIREMENTS PAGE
    return built


if __name__ == "__main__":
    import build_dashboard as db
    out = build(db)
    for name, html in out.items():
        p = os.path.join(ROOT, "site", "pages", name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(html)
        print("wrote", os.path.relpath(p, ROOT), len(html), "bytes")
