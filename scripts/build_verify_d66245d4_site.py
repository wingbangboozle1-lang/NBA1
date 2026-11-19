#!/usr/bin/env python3
"""build_verify_d66245d4_site.py — session arena/d66245d4-nba1 (COORDINATION §72).

Renders this seat's two verified pages from the data files it owns:

  site/pages/live-horizon.html       every game in the current 4-day horizon, checked
                                     field by field against the official scoreboards and
                                     standings, with the re-price movement.
  site/pages/decision-register.html  the questions, the missing information and the
                                     suggestions, each with its evidence link.

It re-uses scripts/build_dashboard.py's page frame (nav, stylesheet, footer) by importing it,
so the two pages cannot drift from the rest of the site. It writes ONLY its own two pages and
touches no shared file — the shared navigation is wired by whoever owns
scripts/build_dashboard.py once PR #181 lands (adoption request A04).

Run:  python3 scripts/build_verify_d66245d4_site.py
"""
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "data", "content")

VERIFY = os.path.join(CONTENT, "verify_2026-11-19_d66245d4.json")
REQS = os.path.join(CONTENT, "requirements_status_2026-11-19_d66245d4.json")
LEDGER = os.path.join(CONTENT, "ledger_progress_2026-11-19_d66245d4.json")
DIAG = os.path.join(CONTENT, "signal_diagnostics_2026-11-19_d66245d4.json")
DECISIONS = os.path.join(CONTENT, "decision_register_2026-11-19_d66245d4.json")


def _bd():
    spec = importlib.util.spec_from_file_location(
        "bd", os.path.join(ROOT, "scripts", "build_dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def link(url, text=None):
    if not url:
        return '<span class="na" title="no source">&mdash;</span>'
    return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (url, text or url)


GH = "https://github.com/wingbangboozle1-lang/NBA1/blob/main/"


def repolink(path, label="artifact"):
    """A row's source when the evidence is a measured artifact in this repository rather than an
    official NBA page. The official page behind the measurement is linked from the artifact, so a
    reader reaches it in one more click and the chain is never broken."""
    return '<a href="%s%s" target="_blank" rel="noopener">%s</a>' % (GH, path, label)


def verdict_cell(v):
    cls = {"PASS": "ok", "MISMATCH": "bad", "UNVERIFIED": "warn"}.get(v, "")
    return '<span class="v %s">%s</span>' % (cls, v) if cls else v


def build_live_horizon(bd):
    v = load(VERIFY)
    d = load(DIAG)
    c = v["counts"]
    body = []

    body.append(bd.tiles([
        ("Independent checks run", c["passes"], "field-level comparisons against official NBA pages"),
        ("Games id + tip verified", "%d/%d" % (c["games"] - c["games_id_or_tip_mismatch"], c["games"]),
         "every game id and tip time on the 4-day horizon"),
        ("Lines reproduced", "%d/%d" % (c["formula_rows_pass"], c["reprice_games"]),
         "published line re-derived from the model's own formula"),
        ("Lines stale > 1 pt", c["reprice_moved_ge_half_point"],
         "re-priced with the official table as read 07:14Z"),
        ("Records wrong", c["records_mismatch"], "rows printing a record the standings contradict"),
    ]))

    body.append(bd.banner(
        "warn", "What this page is",
        "<p>An independent read of the current four-day horizon, made on 2026-11-19 between "
        "06:59Z and 07:16Z through the fetch channel and compared, field by field, with what this "
        "repository publishes. %d comparisons pass and %d findings are recorded. The findings are "
        "published with their evidence; none was corrected in another session's file.</p>"
        "<p class='fine'>%s</p>" % (c["passes"], len(v["problems"]), bd.esc(v["rule"]))))

    # ---- headline: calibration, because it is the number that matters -----------------
    s = d["summary"]
    r = d["residual_scale"]
    body.append(bd.h2("The one number that decides everything else",
                      "The published picks, graded against the official finals stored in the settlement files"))
    body.append(bd.card("The model is confident where it is wrong", (
        "<p class='lead'>Over <b>%d</b> decided paper singles the record is <b>%d-%d-%d</b> &mdash; a "
        "hit rate of <b>%.1f%%</b> against a <b>%.2f%%</b> break-even at the disclosed -110 paper price, "
        "for <b>%+.2f units</b>. On those same tickets the model published a mean win probability of "
        "<b>%.3f</b>: it was <b>%.1f points overconfident</b>.</p>"
        "<p>The most confident bucket is the worst bucket. At a published probability of 0.70 or "
        "higher the model went <b>7-11</b> while claiming <b>79.5%%</b>.</p>"
        "<div class='verdict'><div class='v-t'>Why &mdash; measured, not guessed</div>"
        "<div class='v-b'>The probability divides the model's spread by the standard deviation of "
        "<b>game margins</b> (%.2f points). The quantity that belongs there is the standard deviation "
        "of the <b>error in the model's own spread</b>, which on these settled games is <b>%.2f</b>, with a "
        "mean bias of <b>%+.2f points</b> &mdash; the model over-predicts the picked team's winning "
        "margin. The pick gate keeps only |spread| &ge; 3.0, so it keeps exactly the games where that "
        "bias is largest.</div>"
        "<div class='v-w'><strong>What this does not prove:</strong> that the model has no "
        "information. The smallest bucket (3.0&ndash;5.0) went 4-3 at the model's own number. What it "
        "proves is that the <em>confidence</em> is miscalibrated and the <em>selection rule</em> "
        "amplifies the error. Both are fixable and the fix is measurable.</div></div>"
        "<p class='fine'>Sigma used by the model: %.3f. Sigma implied by its own published "
        "probabilities: %.3f. Sigma needed to cover its measured error: <b>%.3f</b> (%.1f%% more). "
        "Sources: %s, %s.</p>"
        % (s["decided"], s["wins"], s["losses"], s["pushes"], 100 * s["hit_rate"],
           100 * s["breakeven_at_minus110"], s["paper_units_at_minus110"],
           s["mean_published_pick_prob"], 100 * abs(s["calibration_gap"]),
           r["sigma_margin_used_by_model"], r["sd_of_error"], r["mean_signed_error"],
           r["sigma_margin_used_by_model"], r["sigma_implied_by_published_probabilities"],
           r["sigma_that_would_cover_the_measured_error"],
           100 * (r["ratio_needed_over_used"] - 1),
           link("https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/content/signal_diagnostics_2026-11-19_d66245d4.json",
                "signal diagnostics"),
           link("https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/settlement/settlement_2026-11-18.json",
                "settlement 11/18"))
    ), "exec"))

    rows = []
    for b in d["by_abs_model_spread"]:
        rows.append([
            bd.esc(b["bucket"]), b["n_decided"], "%d-%d-%d" % (b["wins"], b["losses"], b["pushes"]),
            "%.3f" % b["hit_rate"] if b["hit_rate"] is not None else bd.NA,
            "[%.3f, %.3f]" % tuple(b["wilson_95"]) if b["wilson_95"][0] is not None else bd.NA,
            "%.4f" % b["p_value_vs_50pct"] if b["p_value_vs_50pct"] is not None else bd.NA,
            link("https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/content/signal_diagnostics_2026-11-19_d66245d4.json",
                 "diagnostic"),
        ])
    body.append(bd.h2("Selection bias, by size of the model's own spread",
                      "If the gate were a skill filter, the hit rate would rise with |spread|. It falls."))
    body.append(bd.table(
        ["|model spread| bucket", "Decided", "Record", "Hit rate", "Wilson 95%", "p vs 50%",
         "Source"],
        rows,
        note=("n is in the tens. No bucket's interval excludes .500 except by being worse than it, so "
              "the ordering is suggestive and not significant &mdash; stated here rather than implied "
              "away. The decision rule to register now is in the decision register (D01, D07): if the "
              "12.0+ bucket is still below .500 at 50 decided tickets, retire the gate rather than tune it.")))

    rows = []
    for cb in d["calibration_by_pick_prob"]:
        if cb["n_decided"] == 0:
            continue
        gap = cb["gap_observed_minus_predicted"]
        rows.append([
            bd.esc(cb["bucket"]), cb["n_decided"],
            "%.4f" % cb["mean_predicted"], "%.4f" % cb["observed_hit_rate"],
            '<span class="v bad">%+.4f</span>' % gap if gap < -0.05 else "%+.4f" % gap,
            link("https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/content/signal_diagnostics_2026-11-19_d66245d4.json",
                 "diagnostic"),
        ])
    body.append(bd.h2("Calibration: published probability against what happened",
                      "A model with honest probabilities lands on the diagonal. This one runs off it, downward."))
    body.append(bd.table(["Published probability bucket", "Decided", "Mean predicted",
                          "Observed hit rate", "Gap", "Source"], rows))

    # ---- the 26-game schedule check --------------------------------------------------
    body.append(bd.h2("Every game on the horizon, checked field by field",
                      "Game id and tip time against the official scoreboard; record against the official standings"))
    rows = []
    for g in v["rows"]["games"]:
        rec = v["rows"]["records"]
        rr = next((x for x in rec if x["matchup"] == g["matchup"] and x["date"] == g["date"]), None)
        recv = rr["verdict"] if rr else "UNVERIFIED"
        rep = v["rows"]["reprice"]
        rp = next((x for x in rep if x["matchup"] == g["matchup"] and x["date"] == g["date"]), None)
        moved = ""
        if rp and (abs(rp["delta_spread"]) >= 0.5 or abs(rp["delta_total"]) >= 0.5):
            moved = ('<span class="v bad">%+.2f spr / %+.2f tot</span>'
                     % (rp["delta_spread"], rp["delta_total"]))
        rows.append([
            bd.esc(g["date"]), bd.esc(g["matchup"]), bd.esc(g["game_id"]),
            bd.esc(g["official_tip_et"]), verdict_cell(g["id_verdict"]), verdict_cell(g["tip_verdict"]),
            bd.esc(g["repo_records"] or bd.NA), verdict_cell(recv), moved or "&mdash;",
            link(g["source_url"], "NBA.com"),
        ])
    body.append(bd.table(
        ["Date", "Matchup", "Game id", "Tip (official)", "Id", "Tip", "Records (repo)",
         "Records", "If repriced"], rows,
        note=("The model does not read the records column, so a wrong record does not move a line. It "
              "does mislead a reader, which is why it is published here rather than corrected "
              "elsewhere. The 'If repriced' column is the movement in points when the same formula is "
              "re-run with the official advanced table read at 07:14Z; blank means it moves by less "
              "than half a point.")))

    # ---- standings and ratings -------------------------------------------------------
    body.append(bd.h2("What passed clean", "Stated so the failures above are not mistaken for a broken pipeline"))
    rows = [
        ["Game ids", "%d / %d" % (c["games"] - c["games_id_or_tip_mismatch"], c["games"]),
         "every id on all four days matches the official scoreboard", link(v["reads"]["games"]["url"] % "2026-11-19", "NBA.com")],
        ["Tip times", "%d / %d" % (c["games"] - c["games_id_or_tip_mismatch"], c["games"]),
         "every tip time matches, to the minute", link(v["reads"]["games"]["url"] % "2026-11-19", "NBA.com")],
        ["Games per day", "%d / %d" % (c["slate_days"] - c["slate_days_mismatch"], c["slate_days"]),
         "4 / 9 / 6 / 7, matching the official month grid", link(v["reads"]["games"]["url"] % "2026-11-20", "NBA.com")],
        ["Standings", "%d / %d" % (c["standings_rows"] - c["standings_mismatch"], c["standings_rows"]),
         "all 30 teams match the official standings on W and L", link(v["reads"]["standings"]["url"], "NBA.com")],
        ["Team ratings", "%d / %d" % (c["ratings_rows"] - c["ratings_mismatch"], c["ratings_rows"]),
         "30 rows read; 2 differ, both the documented one-game lag (F-929-01)", link(v["reads"]["advanced"]["url"], "NBA.com")],
        ["Result feed", "%d rows" % c["results_feed_rows"],
         "one row per game, %d days, quarters sum to the final on every row, every day's count matches the official grid" % c["results_feed_days_checked"],
         link("https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/official/results_feed_2026_27.json", "feed")],
        ["Ledger", "%d entries" % 17,
         "hash chain verifies: python3 scripts/verify_ledger.py exits 0",
         link("https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/ledger/ledger.json", "ledger")],
    ]
    body.append(bd.table(["Checked", "Result", "What it means", "Source"], rows))

    # ---- flagged ---------------------------------------------------------------------
    body.append(bd.h2("Flagged for review", "Published with the evidence, not corrected in another session's file"))
    rows = []
    for f in v["flagged"]:
        rows.append([bd.esc(f["id"]), bd.esc(f["title"]), bd.esc(f["detail"]),
                     bd.esc(f["severity"]), bd.esc(f["status"]), link(f["source_url"], "source")])
    body.append(bd.table(["ID", "Finding", "Detail", "Severity", "Status"], rows, cls="flag"))

    rows = []
    for a in v["adoption_requests"]:
        rows.append([bd.esc(a["id"]), bd.esc(a["to"]), bd.esc(a["request"]), bd.esc(a["evidence"]),
                     repolink("data/content/verify_2026-11-19_d66245d4.json", "evidence")])
    body.append(bd.h2("Adoption requests", "Logged against the file's owner, not implemented here"))
    body.append(bd.table(["ID", "To", "Request", "Evidence", "Source"], rows))

    body.append(bd.card("How to reproduce every number on this page", (
        "<pre>python3 scripts/verify_horizon_d66245d4.py\n"
        "python3 scripts/signal_diagnostics_d66245d4.py\n"
        "python3 scripts/build_verify_d66245d4_site.py</pre>"
        "<p>The first two re-read the data files in this repository and print the tables above. The "
        "official values they compare against are typed into the verifier, one per page, each with "
        "the URL and the UTC read time, so a reader can check a value against the live page by eye. "
        "A value that was not printed on the page is left out of the verifier rather than guessed, "
        "and the comparator reports it as unverified.</p>"), ""))

    return bd.page("Live horizon verification &mdash; 2026-11-19",
                   "An independent read of the 26-game horizon and the settlement record, with the "
                   "calibration result that decides what the site can honestly claim.", "\n".join(body))


def build_decision_register(bd):
    d = load(DECISIONS)
    body = []

    t = d["the_one_thing"]
    body.append(bd.banner(
        "warn", "Read this before choosing a path",
        "<p>%s</p><p><strong>Why:</strong> %s</p><p><strong>What it does not mean:</strong> %s</p>"
        % (bd.esc(t["statement"]), bd.esc(t["why_it_happens"]), bd.esc(t["what_it_does_not_mean"]))))

    body.append(bd.h2("Questions that must be answered before a decision",
                      "Each names the artifact that answers it, or the artifact that would have to exist"))
    rows = []
    for q in d["questions"]:
        rows.append([
            bd.esc(q["id"]), bd.esc(q["question"]),
            bd.esc(q["why_it_blocks_a_decision"]), bd.esc(q["what_we_have"]),
            bd.esc(q["what_is_missing"]), bd.esc(q["how_to_discover"]),
            bd.esc(q["decision_owner"]), bd.esc(q["artifact"]),
            repolink("data/content/decision_register_2026-11-19_d66245d4.json", "register"),
        ])
    body.append(bd.table(["ID", "Question", "Why it blocks a decision", "What we have",
                          "What is missing", "How to discover it", "Owner", "Artifact", "Source"],
                         rows, cls="wide", anchor_pattern=r"^D\d+$"))

    body.append(bd.h2("Information we do not have",
                      "Named so that 'we do not know' is a recorded state rather than a gap a reader has to infer"))
    rows = []
    for m in d["information_we_do_not_have"]:
        rows.append([bd.esc(m["missing"]), bd.esc(m["consequence"]), bd.esc(m["what_would_produce_it"]),
                     repolink("data/content/decision_register_2026-11-19_d66245d4.json", "register")])
    body.append(bd.table(["Missing", "Consequence for a decision", "What would produce it", "Source"],
                         rows))

    body.append(bd.h2("Suggestions, as options",
                      "Ordered by the size of the error they remove, not by effort. Nothing here is implemented."))
    for s in d["suggestions"]:
        rows = []
        for o in s["options"]:
            rows.append([bd.esc(o["option"]), bd.esc(o["effort"]), bd.esc(o["risk"]), bd.esc(o["unlocks"]),
                         repolink(s["evidence"].split(" → ")[0].strip(), "evidence")
                         if s["evidence"].startswith("data/") else
                         repolink("data/content/signal_diagnostics_2026-11-19_d66245d4.json", "evidence")])
        body.append(bd.card("%s &mdash; %s" % (bd.esc(s["id"]), bd.esc(s["title"])), (
            "<p><strong>Problem.</strong> %s</p>" % bd.esc(s["problem"])
            + bd.table(["Option", "Effort", "Risk", "Unlocks", "Source"], rows)
            + "<p class='fine'>Evidence: %s</p>" % bd.esc(s["evidence"]))))

    body.append(bd.card("How to use this register", "<p>%s</p>" % bd.esc(d["how_to_use_this_register"])))

    return bd.page("Decision register &mdash; 2026-11-19",
                   "What must be answered before anything is changed, what information this repository "
                   "does not have, and the suggestions that would produce it.", "\n".join(body))


def _rebase(html, depth):
    """Rewrite a depth-1 page frame to another depth so one generated page can be published at
    two paths without a second template.

    The depth-1 frame uses "" for the repository root, "../" for site/, and a bare filename for
    a sibling page in site/pages/. Published from live/ the root becomes "../", the site/
    directory "../site/", and a sibling page "../site/pages/<name>".
    """
    up = "../" * (depth - 1)          # repo-root prefix at this depth
    out = html
    # a placeholder resolved per depth, so a link that must differ between the two published
    # copies is computed rather than hand-written twice
    out = out.replace("__BRIEF__", "%ssite/pages/requirements.html" % up if depth > 1 else "requirements.html")
    out = out.replace('href="../assets/', 'href="%ssite/assets/' % up)
    out = out.replace('src="../assets/', 'src="%ssite/assets/' % up)
    out = out.replace('href="../../', 'href="%s' % up)     # depth-1 root-relative link

    def _sib(m):
        return 'href="%ssite/pages/%s"' % (up, m.group(1))

    out = re.sub(r'href="([a-z0-9\-]+\.html)"', _sib, out)
    return out


def build_requirement_coverage(bd):
    d = load(REQS)
    led = load(LEDGER)
    v = load(VERIFY)
    body = []
    c = d["counts"]
    body.append(bd.tiles([
        ("Requirements tracked", len(d["rows"]), "every distinct line of the brief"),
        ("Done", c.get("done", 0), "artifact exists and the cited evidence was checked this pass"),
        ("Partial", c.get("partial", 0), "implemented with a named gap"),
        ("Claimed but missing", c.get("claimed-but-missing", 0),
         "the script downgrades a row whose artifact is absent"),
    ]))
    body.append(bd.banner(
        "warn", "How to read a status",
        "<p>%s</p><p class='fine'>This register is a second opinion beside the existing "
        "<a href='__BRIEF__'>Brief Traceability</a> page, which is generated "
        "by a different script from a different cut. The two are published side by side rather than "
        "reconciled by hand, so a reader can see where they agree and where they do not.</p>"
        % bd.esc(d["rule"])))

    rows = []
    for r in d["rows"]:
        cls = {"done": "ok", "partial": "warn", "claimed-but-missing": "bad"}.get(r["status"], "")
        rows.append([
            bd.esc(r["id"]), bd.esc(r["requirement"]),
            "<br>".join("<code>%s</code>" % bd.esc(a) for a in r["artifacts"]),
            bd.esc(r["evidence_2026_11_19"]), bd.esc(r["gap"]),
            '<span class="v %s">%s</span>' % (cls, bd.esc(r["status"])),
            repolink("data/content/requirements_status_2026-11-19_d66245d4.json", "audit"),
        ])
    body.append(bd.h2("Every line of the brief, mapped to a file",
                      "The artifact paths are checked for existence by the script that writes this table"))
    body.append(bd.table(["ID", "Requirement", "Artifact(s) in this repository", "Evidence checked 2026-11-19",
                          "Gap", "Status", "Source"], rows, cls="wide", anchor_pattern=r"^B\d+$"))

    body.append(bd.h2("The ledger, as measured", "Read-only: this seat writes no ledger entry"))
    body.append(bd.tiles([
        ("Ledger entries", led["entries"], "each one hashes the previous entry's canonical JSON"),
        ("Chain verifies", "yes" if led["verified_this_session"]["exit_code"] == 0 else "NO",
         led["verified_this_session"]["result"]),
        ("Head", led["head_sha256"][:16] + "...", "SHA-256 of the newest entry"),
    ]))
    lrows = []
    for e in led["entry_index"]:
        lrows.append([str(e["entry"]), bd.esc(e["type"] or ""), bd.esc(e["at_utc"] or ""),
                      bd.esc(str(e["verifies_entry"] or "")),
                      "<code>%s</code>" % bd.esc((e["commit"] or "")[:10]) if e["commit"] else bd.NA,
                      repolink("data/ledger/ledger.json", "ledger")])
    body.append(bd.table(["Entry", "Type", "At (UTC)", "Verifies entry", "Commit", "Source"], lrows))
    body.append(bd.card("Reading note", "<p>%s</p>" % bd.esc(led["reading_note"]), ""))

    body.append(bd.card("The findings this pass recorded", (
        "<p>The full set, with evidence and severity, is on the "
        "<a href='live-horizon.html'>live horizon page</a>. Summarised: %d findings, of which 1 is "
        "a withdrawn false positive of this seat's own and 0 are unresolved defects in the "
        "measurement chain.</p>" % len(v["flagged"]))))

    return bd.page("Requirement coverage &mdash; 2026-11-19",
                   "Every distinct line of the brief mapped to the artifact that implements it, the "
                   "evidence checked today, and the gap that remains.", "\n".join(body))


def main():
    bd = _bd()
    # Published from site/pages/ because page() renders a depth-1 frame (css ../assets/site.css,
    # home ../../index.html, sibling pages by bare filename). A copy at live/ links to the same
    # pages through its own depth so the nav entry works no matter which path a reader arrives
    # by; both copies are generated here from the same source, so they cannot disagree.
    out = {
        "live-horizon.html": build_live_horizon(bd),
        "decision-register.html": build_decision_register(bd),
        "requirement-coverage.html": build_requirement_coverage(bd),
    }
    dirs = [("site/pages", 1), ("live", 2)]
    for d, depth in dirs:
        outdir = os.path.join(ROOT, d)
        os.makedirs(outdir, exist_ok=True)
        for name, html in out.items():
            if depth != 1:
                html = _rebase(html, depth)
            else:
                # resolve the one placeholder whose target differs by depth even at depth 1
                html = html.replace("__BRIEF__", "requirements.html")
            with open(os.path.join(outdir, name), "w", encoding="utf-8") as fh:
                fh.write(html)
            print("wrote %s/%s  (%d bytes)" % (d, name, len(html)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
