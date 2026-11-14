#!/usr/bin/env python3
"""build_verified.py — generate the `verified/` decision layer.

    python3 scripts/build_verified.py

Reads   verified/data/*.json
Writes  verified/index.html          landing / dashboard
        verified/summary.html        executive summary
        verified/verification.html   row-level verification against official sources
        verified/review.html         line-by-line repository review
        verified/questions.html      questions that block a decision, with the step that answers each
        verified/suggestions.html    options, with a review/choose workflow
        verified/flagged.html        everything unverified or contradicted, with official links
        verified/sources.html        source register for this section
        verified/assets/site.css     (already committed; regenerated only if missing)

Rules this builder enforces, matching the brief:
  * every table row links to an official source, or carries a visible NO-OFFICIAL-SOURCE marker;
  * no placeholder text is emitted ("TODO", "TBD", "lorem", "xxx", "???") - the checker fails on it;
  * a value that was not confirmed from an official source is rendered as an em dash, never filled in;
  * output is deterministic: rebuilding on an unchanged tree produces identical bytes.
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, "verified")
D = os.path.join(V, "data")

NA = ('<span class="tiny" title="not confirmed from an official source in this build">'
      '&mdash; <em>unverified</em></span>')

PAGES = [
    ("index.html", "Overview"),
    ("summary.html", "Executive summary"),
    ("verification.html", "Verification"),
    ("review.html", "Repo review"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged"),
    ("sources.html", "Sources"),
]

STATUS_CLASS = {
    "VERIFIED": "ok",
    "CONFIRMED": "ok",
    "RECONCILED": "ok",
    "INTERNALLY": "ok",
    "MISMATCH": "bad",
    "WRONG": "bad",
    "FAILED": "bad",
    "NOT REFLECTED": "bad",
    "STALE": "warn",
    "UNVERIFIED": "warn",
    "OVERSTATED": "warn",
    "PARTIALLY": "warn",
    "NOT COMPARABLE": "mut",
    "IRREGULARITY": "info",
    "NEW FINDING": "info",
    "OUTSTANDING": "info",
    "UNVERIFIABLE": "mut",
    "CONFIRMED WITH CAVEAT": "info",
}


def load(name):
    with open(os.path.join(D, name), encoding="utf-8") as fh:
        return json.load(fh)


def esc(v):
    if v is None or v == "":
        return NA
    return html.escape(str(v), quote=True)


def e(v):
    """Escape for body text (no 'unverified' marker)."""
    if v is None:
        return ""
    return html.escape(str(v), quote=True)


def pill(status):
    key = STATUS_CLASS.get(status)
    if key is None:
        for k, cls in STATUS_CLASS.items():
            if status.startswith(k):
                key = cls
                break
    key = key or "mut"
    return '<span class="pill %s">%s</span>' % (key, html.escape(status))


def link(url, label=None):
    """Render one official/repository link. Multiple URLs separated by ' ; ' are each linked."""
    if not url:
        return NA
    out = []
    for part in str(url).split(" ; "):
        part = part.strip()
        if not part:
            continue
        if not part.startswith("https://"):
            out.append(esc(part))
            continue
        host = part.split("/")[2] if "//" in part else ""
        if label:
            txt = label
        elif host in ("www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com"):
            tail = part.rstrip("/").split("/")[-1]
            txt = tail if tail and len(tail) <= 34 else host.replace("www.", "")
        elif host == "github.com":
            tail = part.rstrip("/").split("/")
            txt = "%s/%s" % (tail[-2], tail[-1]) if len(tail) > 1 else "repo"
            if len(txt) > 38:
                txt = tail[-1]
        else:
            txt = host.replace("www.", "")
        out.append('<a href="%s" rel="noopener">%s</a>' % (html.escape(part, quote=True), e(txt)))
    return '<span class="src">%s</span>' % " · ".join(out) if out else NA


def table(headers, rows, align=None, tid=""):
    align = align or {}
    th = []
    for i, h in enumerate(headers):
        cls = ' class="n"' if align.get(i) == "n" else ""
        th.append("<th%s>%s</th>" % (cls, h))
    body = []
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            cls = ' class="n"' if align.get(i) == "n" else ""
            cells.append("<td%s>%s</td>" % (cls, c))
        body.append("<tr>%s</tr>" % "".join(cells))
    return ('<div class="tablewrap"><table%s><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
            % (' id="%s"' % tid if tid else "", "".join(th), "".join(body)))


def kpi(value, key, sub="", cls=""):
    return ('<div class="kpi %s"><div class="v">%s</div><div class="k">%s</div>'
            '<div class="s">%s</div></div>' % (cls, e(value), e(key), e(sub)))


def page(title, slug, body, sub=""):
    nav = []
    for fn, label in PAGES:
        cur = ' aria-current="page"' if fn == slug else ""
        nav.append('<a href="%s"%s>%s</a>' % (fn, cur, e(label)))
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s &middot; NBA1 verified</title>
<meta name="description" content="Independent row-level verification and decision layer for the NBA1 line-origination project. No manual input, no inferred values.">
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="top-in">
    <a class="brand" href="index.html">
      <span class="tick">&#10003;</span>
      <span>NBA1 verified<small>independent check &middot; 14 Nov 2026</small></span>
    </a>
    <nav class="topnav" aria-label="Sections">%(nav)s</nav>
  </div>
</header>
<main id="main">
<div class="wrap">
%(body)s
</div>
</main>
</body>
</html>
""" % {"title": e(title), "nav": "".join(nav), "body": body}


def foot(extra=""):
    return ('<footer class="foot"><p><strong>How this section is made.</strong> '
            'Every number on these pages was read from an NBA-operated page during '
            '2026-11-14 18:38&ndash;19:45 UTC and compared with what the repository publishes. '
            'Where an official read was impossible the value is published as unverified and listed on '
            '<a href="flagged.html">Flagged for review</a> &mdash; it is never filled in. '
            'Generated by <code>scripts/build_verified.py</code> from '
            '<code>verified/data/*.json</code>; rebuilt and checked by '
            '<code>scripts/verify_verified.py</code>.</p>%s</footer>' % extra)


# --------------------------------------------------------------------------- pages
def build_index(summary, ver, rev, fl, sug, qs):
    c = ver["counts"]
    rc = rev["counts"]
    kp = "".join([
        kpi(c["verified"], "checks confirmed", "of %d verification rows" % c["rows"], "ok"),
        kpi(c["failed"], "checks failed", "official read contradicts the repo", "bad"),
        kpi(c["unverified"], "could not be verified", "left blank, never guessed", "warn"),
        kpi("{:,}".format(c["values_or_rows_compared"]), "values compared", "row-by-row, official source per row"),
        kpi(len(fl["rows"]), "flagged for review", "each with its official link"),
        kpi(len(qs["rows"]), "open questions", "each with the step that answers it"),
    ])
    top = summary["headline"]
    changed = "".join('<li><strong>%s</strong> &mdash; %s</li>' % (e(x["change"]), e(x["consequence"]))
                      for x in summary["what_changed_today"])
    falsy = "".join(
        '<div class="card false"><h3>%s</h3><p class="small">%s</p>'
        '<div class="meta">Instead: %s &middot; %s</div></div>'
        % (e(x["claim_as_published"]), e(x["why_not"]), e(x["instead"]), link("https://github.com/wingbangboozle1-lang/NBA1/blob/main/verified/data/flagged.json", x["flag"]))
        for x in summary["what_is_not_true"][:3])
    decisions = "".join(
        '<div class="card open"><h3>%s</h3><p class="small">%s</p>'
        '<div class="meta">%s &middot; <a href="questions.html#%s">%s</a></div></div>'
        % (e(x["decision"]), e(x["options"]), e(x["why_now"]), e(x["question"].lower()), e(x["question"]))
        for x in summary["what_to_decide"])

    body = """
<div class="banner"><b>Read this first.</b> These pages are an independent check of the NBA1
repository, not a new build of it. They re-read official NBA pages, compare them with what the
repository publishes, and record every disagreement. Nothing was corrected in another session's
files; every defect is published here with a proposed fix and an owner.</div>

<h1>What is actually true about this project</h1>
<p class="lede">%(headline)s</p>
<div class="kpis">%(kp)s</div>

<h2>The state in one paragraph</h2>
<p class="sub">%(state)s %(conf)s</p>

<h2>What changed today</h2>
<ul class="clean">%(changed)s</ul>

<h2>Where the site overstates itself</h2>
<p class="sub">Three of the repository's load-bearing statements do not survive an official read.
Each one is developed in full on <a href="review.html">Repo review</a> and listed with its fix on
<a href="flagged.html">Flagged</a>.</p>
<div class="grid2">%(falsy)s</div>
<p class="small"><a href="summary.html">All findings, including the ones the repository gets right &rarr;</a></p>

<h2>What needs your decision</h2>
<p class="sub">Four decisions are blocking everything else. Each links to the question that has to be
settled first and to the options on <a href="suggestions.html">Suggestions</a>.</p>
<div class="grid2">%(decisions)s</div>

<h2>Where to go</h2>
%(nav_cards)s
%(foot)s
""" % {
        "headline": e(top["one_sentence"]),
        "kp": kp,
        "state": e(top["state"]),
        "conf": e(top["confidence"]),
        "changed": changed,
        "falsy": falsy,
        "decisions": decisions,
        "nav_cards": nav_cards(),
        "foot": foot(),
    }
    return page("Overview", "index.html", body)


def nav_cards():
    items = [
        ("summary.html", "Executive summary",
         "The whole picture in ten minutes: what is true, what is not, what changed, what the numbers say, what to decide."),
        ("verification.html", "Verification",
         "28 checks, 3,873 compared values, one official link per row. Includes the 11/13 settlement re-graded from the official finals."),
        ("review.html", "Repo review",
         "20 load-bearing statements from the README and the pages, each tested against an official source or the repository's own code."),
        ("questions.html", "Questions",
         "12 questions that block a decision, sorted by priority. Each states what is known, what is missing, and the cheapest step that answers it."),
        ("suggestions.html", "Suggestions",
         "12 options with effort, risk and what each unlocks, plus the review workflow so one path can be chosen before anything is built."),
        ("flagged.html", "Flagged for review",
         "15 items this session could not confirm or that contradict an official source, each with the URL to check by hand."),
        ("sources.html", "Sources",
         "26 sources: 19 official NBA URLs read in this session and 7 repository files used for claims about the code."),
    ]
    out = []
    for href, title, blurb in items:
        out.append('<div class="card"><h3><a href="%s">%s</a></h3><p class="small">%s</p></div>'
                   % (href, e(title), e(blurb)))
    return '<div class="grid2">%s</div>' % "".join(out)


def build_summary(summary):
    def cards(items, cls, title_key, body_key, extra_keys=()):
        out = []
        for x in items:
            extra = "".join('<div class="meta"><strong>%s:</strong> %s</div>'
                            % (e(k), e(x.get(k, ""))) for k in extra_keys)
            out.append('<div class="card %s"><h3>%s</h3><p class="small">%s</p>%s</div>'
                       % (cls, e(x[title_key]), e(x[body_key]), extra))
        return '<div class="grid2">%s</div>' % "".join(out)

    true_cards = cards(summary["what_is_true"], "true", "claim", "evidence", ("strength",))
    false_cards = cards(summary["what_is_not_true"], "false", "claim_as_published", "why_not",
                        ("instead", "flag"))
    change_rows = [[e(x["change"]), e(x["detail"]), e(x["consequence"]), link(x.get("source", ""))]
                   for x in summary["what_changed_today"]]
    num_rows = [[e(x["number"]), e(x["reading"]), e(x["caveat"]), link(x.get("source", ""))]
                for x in summary["what_the_numbers_say"]]
    dec_cards = cards(summary["what_to_decide"], "open", "decision", "options",
                      ("why_now",))
    unknown = "".join("<li>%s</li>" % e(x) for x in summary["what_is_still_unknown"])
    did = "".join("<li>%s</li>" % e(x) for x in summary["what_this_build_did"])

    body = """
<h1>Executive summary</h1>
<p class="lede">%(headline)s</p>

<h2>1. What this session did</h2>
<ol class="steps">%(did)s</ol>

<h2>2. What is true</h2>
<p class="sub">These survive an official read. They are the parts of the project that can be defended
without a caveat.</p>
%(true_cards)s

<h2>3. What is not true as published</h2>
<p class="sub">Each of these is a statement the repository makes. The official read does not support it
in the form it is published. The full reasoning and the fix are on
<a href="review.html">Repo review</a> and <a href="flagged.html">Flagged</a>.</p>
%(false_cards)s

<h2>4. What changed today (14 Nov 2026)</h2>
%(change_table)s

<h2>5. What the numbers say</h2>
<p class="sub">The eight numbers a decision should actually rest on, with the caveat that belongs next
to each one.</p>
%(num_table)s

<h2>6. What to decide</h2>
<p class="sub">Options are laid out on <a href="suggestions.html">Suggestions</a> with effort, risk and a
definition of done, so one path can be chosen before anything is built.</p>
%(dec_cards)s

<h2>7. What is still unknown</h2>
<ul class="clean">%(unknown)s</ul>

<h2>Reading rule</h2>
<p class="sub">An em dash on these pages means <em>not confirmed from an official source in this
build</em>. It never means zero and it is never filled in by inference. Every table row carries the URL
it was checked against.</p>
%(foot)s
""" % {
        "headline": e(summary["headline"]["one_sentence"]),
        "did": did,
        "true_cards": true_cards,
        "false_cards": false_cards,
        "change_table": table(["Change", "Detail (official read)", "What it means", "Source"], change_rows),
        "num_table": table(["Number", "Reading", "Caveat that belongs next to it", "Source"], num_rows),
        "dec_cards": dec_cards,
        "unknown": unknown,
        "foot": foot(),
    }
    return page("Executive summary", "summary.html", body)


def build_verification(ver):
    rows = []
    for r in ver["rows"]:
        rows.append([
            '<span class="id">%s</span>' % e(r["id"]),
            "<strong>%s</strong><br><span class=\"tiny\">%s</span>" % (e(r["category"]), e(r["check"])),
            '%s<div class="tiny" style="margin-top:4px">%s</div>' % (e(r["result"]), e(r["detail"])),
            pill(r["status"]),
            "<span class=\"mono\">%s</span>" % e(r["rows_checked"]),
            e(r["official_value"] if len(str(r["official_value"])) <= 90 else str(r["official_value"])[:88] + "…"),
            link(r["evidence_url"]),
        ])
    tot = sum(r["rows_checked"] for r in ver["rows"])
    mism = sum(r["mismatches"] for r in ver["rows"])
    body = """
<h1>Row-level verification</h1>
<p class="lede">%(n)d checks, %(tot)s compared values, one official link per row. A check is
<strong>VERIFIED</strong> only when this session read the value on an NBA-operated page and it matched
what the repository publishes.</p>

<div class="kpis">%(kp)s</div>

<div class="banner"><b>What was not verified.</b> 45 of the 60 final scores in the out-of-sample window
were not re-read (the 11/07 page returned every score unrendered and 11/08&ndash;11/12 were not read).
Those rows are published as unverified rather than assumed correct &mdash;
see <a href="flagged.html#f-06">F-06</a>.</div>

<h2>Every check</h2>
%(tbl)s

<h2>The captures behind these rows</h2>
<p class="sub">The URLs, retrieval times and what was read from each page are listed in
<a href="https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/2026-11-14-session-428e/captures/NOTES.md">verify/2026-11-14-session-428e/captures/NOTES.md</a>.
That file records the two reads that came back unusable, so the list is the full set of attempts, not
only the successes.</p>

<h2>Method</h2>
<ul class="clean">
<li><strong>Official only.</strong> Values are confirmed against www.nba.com, official.nba.com or
ak-static.cms.nba.com. No sportsbook, aggregator or news site was used for any value.</li>
<li><strong>Exact match.</strong> A value is verified only if it agrees to the published precision.
Where a page rounds (e.g. PPG to one decimal) the comparison is made at that precision.</li>
<li><strong>Editions are part of the claim.</strong> An injury designation is recorded with the edition
stamp, because designations move during a game day.</li>
<li><strong>Two reads that disagree make a value unverified.</strong> Cooper Flagg's average returned
21.0 and 24.6 on two reads of the same official page, so it is published as unverified (V-09), not
averaged.</li>
<li><strong>Recomputation is not verification.</strong> Where a row says VERIFIED for a statistic it
means the arithmetic reproduces exactly from the data the repository stores &mdash; it does not mean the
underlying scores were re-read. The column on the right is the honest per-row distinction.</li>
</ul>
%(foot)s
""" % {
        "n": ver["counts"]["rows"],
        "tot": "{:,}".format(tot),
        "mism": mism,
        "kp": "".join([
            kpi(ver["counts"]["verified"], "verified", "official read matches", "ok"),
            kpi(ver["counts"]["failed"], "failed", "official read contradicts", "bad"),
            kpi(ver["counts"]["unverified"], "unverified", "left blank", "warn"),
            kpi("{:,}".format(tot), "values compared", "row by row"),
            kpi(mism, "cells mismatched", "all in props + injury"),
        ]),
        "tbl": table(["#", "Check", "Result", "Status", "Rows", "Official value", "Source"],
                     rows, align={4: "n"}),
        "foot": foot(),
    }
    return page("Verification", "verification.html", body)


def build_review(rev):
    rows = []
    for r in rev["rows"]:
        rows.append([
            '<span class="id">%s</span>' % e(r["id"]),
            '<span class="tiny">%s</span>' % e(r["area"]),
            "<strong>%s</strong>" % e(r["claim"]),
            e(r["result"]),
            pill(r["status"]),
            '<span class="tiny">%s</span>' % e(r["note"]),
            link(r["source"]),
        ])
    body = """
<h1>Repository review, statement by statement</h1>
<p class="lede">%(n)d load-bearing statements, each quoted from the repository and then tested. The test
is named so it can be repeated: an official page read, a recomputation from stored data, or a read of
the code that produced the number.</p>

<div class="kpis">%(kp)s</div>

<div class="banner"><b>Coverage, stated honestly.</b> The repository holds 1,500+ files and six
implementations of the same brief. This review covers the statements a decision would rest on, not every
line of every page. Nothing here is a claim that the unaudited pages are correct.</div>

%(tbl)s

<h2>What the repository gets right</h2>
<p class="sub">It is worth stating plainly, because the criticism is easier to write: this project's
build is idempotent, its gate genuinely runs, its official-data lineage checks out row by row, its only
graded result is correct, and it publishes its own failures instead of hiding them. Most projects that
claim to originate lines do none of those things.</p>

<h2>The three findings that change a decision</h2>
<div class="grid2">
<div class="card false"><h3>The headline is stronger than the statistics</h3>
<p class="small">S1's p = 0.020 is a raw, uncorrected p-value from one of six tests. Corrected, q = 0.120.
Its win rate barely responds to edge size (r = 0.051). The site's most confident sentence is the least
defensible one.</p><div class="meta"><a href="flagged.html#f-05">F-05</a> &middot; question Q-03</div></div>
<div class="card false"><h3>The injury layer is a day behind on a game day</h3>
<p class="small">All ten teams filed between 04:15 and 13:30 ET. Twenty-two designations moved. The
published layer still shows the morning snapshot and does not say it is a snapshot.</p>
<div class="meta"><a href="flagged.html#f-03">F-03</a>, <a href="flagged.html#f-04">F-04</a> &middot; Q-04</div></div>
<div class="card false"><h3>Rest is computed wrongly and two pages disagree</h3>
<p class="small">26 of 27 horizon rows store a negative rest value because the "previous game" is taken
from a fixture list that includes future dates. Game flow and picks then contradict each other.</p>
<div class="meta"><a href="flagged.html#f-12">F-12</a> &middot; Q-09</div></div>
</div>
%(foot)s
""" % {
        "n": len(rev["rows"]),
        "kp": "".join(kpi(v, k.replace("_", " "), "", "ok" if k == "CONFIRMED" else ("bad" if k == "WRONG" else ""))
                      for k, v in rev["counts"]["by_status"].items()),
        "tbl": table(["#", "Area", "Statement as published", "Result of the test", "Status",
                      "Note", "Evidence"], rows),
        "foot": foot(),
    }
    return page("Repo review", "review.html", body)


def build_questions(qs):
    groups = {"P1": [], "P2": [], "P3": []}
    for r in qs["rows"]:
        groups.setdefault(r["priority"], []).append(r)
    blocks = []
    labels = {"P1": "P1 &mdash; blocks a decision being made now",
              "P2": "P2 &mdash; blocks a decision in the next build",
              "P3": "P3 &mdash; worth knowing, no decision depends on it yet"}
    for key in ("P1", "P2", "P3"):
        rows = groups.get(key, [])
        if not rows:
            continue
        cards = []
        for r in rows:
            cards.append("""
<div class="card qa %(cls)s" id="%(id)s">
  <h3>%(id)s &middot; %(q)s <span class="pill mut">%(pri)s</span></h3>
  <dl class="kv">
    <dt>What we know</dt><dd>%(known)s</dd>
    <dt>What is missing</dt><dd>%(missing)s</dd>
    <dt>Why it decides</dt><dd>%(why)s</dd>
    <dt>How to find out</dt><dd>%(how)s</dd>
    <dt>Owner</dt><dd>%(owner)s</dd>
    <dt>Blocks</dt><dd>%(blocks)s</dd>
  </dl>
</div>""" % {"cls": key.lower(), "id": r["id"].lower(), "q": e(r["question"]), "pri": key,
             "known": e(r["known"]), "missing": e(r["missing"]), "why": e(r["why_it_decides"]),
             "how": e(r["how_to_discover"]), "owner": e(r["owner"]), "blocks": e(r["blocks"])})
        blocks.append("<h2>%s</h2>%s" % (labels[key], "".join(cards)))

    rows = [[e(r["id"]), "<span class=\"%s\">%s</span>" % (r["priority"].lower(), r["priority"]),
             e(r["question"]), e(r["missing"]), e(r["how_to_discover"]), link(r.get("source", ""))]
            for r in qs["rows"]]
    body = """
<h1>Questions that block a decision</h1>
<p class="lede">The brief asked for a clear list of what still needs to be answered before a reasonable
decision can be made, and for a way to discover what is missing. This is that list. Every question names
the cheapest concrete step that would answer it &mdash; in most cases that step costs nothing.</p>

<div class="kpis">%(kp)s</div>

<h2>Summary table</h2>
%(tbl)s

<p class="sub" style="margin-top:22px">The same questions in full, with what is known, what is missing
and why the answer changes a decision.</p>

%(blocks)s
%(foot)s
""" % {
        "kp": "".join([
            kpi(sum(1 for r in qs["rows"] if r["priority"] == "P1"), "P1 questions", "blocking now", "bad"),
            kpi(sum(1 for r in qs["rows"] if r["priority"] == "P2"), "P2 questions", "block the next build", "warn"),
            kpi(sum(1 for r in qs["rows"] if r["priority"] == "P3"), "P3 questions", "no decision depends yet"),
            kpi(len(qs["rows"]), "total", "each with a discovery step"),
        ]),
        "tbl": table(["#", "Priority", "Question", "What is missing", "How to find out", "Evidence"], rows),
        "blocks": "".join(blocks),
        "foot": foot(),
    }
    return page("Questions", "questions.html", body)


def build_suggestions(sug):
    rows = []
    for r in sug["rows"]:
        rows.append([
            "<span class=\"mono\">%s</span>" % e(r["order"]),
            "<strong>%s</strong><div class=\"tiny\" style=\"margin-top:3px\">%s</div>" % (e(r["id"]), e(r["title"])),
            e(r["fixes"]),
            e(r["effort"]),
            e(r["risk"]),
            e(r["unlocks"]),
            '<span class="pill mut">%s</span><div class="tiny">%s</div>' % (e(r["status"]), e(r["owner"])),
            link(r.get("source", "")),
        ])
    cards = []
    for r in sug["rows"]:
        cards.append("""
<div class="card open" id="%(id)s">
  <h3>%(id)s &middot; %(title)s</h3>
  <dl class="kv">
    <dt>Fixes</dt><dd>%(fixes)s</dd>
    <dt>Evidence</dt><dd>%(evidence)s</dd>
    <dt>Effort</dt><dd>%(effort)s</dd>
    <dt>Risk</dt><dd>%(risk)s</dd>
    <dt>Unlocks</dt><dd>%(unlocks)s</dd>
    <dt>Cost</dt><dd>%(cost)s</dd>
    <dt>Done when</dt><dd>%(dod)s</dd>
    <dt>Status</dt><dd><span class="pill mut">%(status)s</span> &middot; owner: %(owner)s</dd>
  </dl>
</div>""" % {"id": r["id"], "title": e(r["title"]), "fixes": e(r["fixes"]), "evidence": e(r["evidence"]),
             "effort": e(r["effort"]), "risk": e(r["risk"]), "unlocks": e(r["unlocks"]),
             "cost": e(r.get("cost", "—")), "dod": e(r["definition_of_done"]),
             "status": e(r["status"]), "owner": e(r["owner"])})

    body = """
<h1>Suggestions — review, then choose</h1>
<p class="lede">%(n)d options for improving the project, ordered by what unblocks the most. This is a
decision board, not a backlog: nothing here has been implemented, and nothing should be implemented until
one path is chosen.</p>

<div class="banner"><b>How to use this page.</b> Read the summary table, pick the row that fixes the thing
that is actually costing you a decision, and set its status to <em>accepted</em> with an owner and a
definition of done. A suggestion without a definition of done is how a wishlist becomes a backlog.
Statuses are <em>proposed &rarr; accepted &rarr; done</em>, or <em>rejected</em> &mdash; and a rejected row
keeps its reason so it is not proposed again.</div>

<h2>Summary — pick one row at a time</h2>
%(tbl)s

<h2>The options in full</h2>
%(cards)s

<h2>If you only do three things</h2>
<ol class="steps">
<li><strong>S-03 &mdash; publish the corrected statistics next to the raw ones.</strong> It costs half a
day, it makes the headline worse, and it is the difference between a defensible project and one that
falls apart under the first competent question.</li>
<li><strong>S-02 + S-05 &mdash; put a timestamp on every number and automate the injury edition.</strong>
This is the fastest-moving input in the whole system and the only part of the brief that is currently
served by a stale snapshot.</li>
<li><strong>S-01 &mdash; make one build the product.</strong> Six live builds that disagree with each
other make every other fix five times more expensive and make the site impossible to read.</li>
</ol>

<h2>What this session did not do</h2>
<p class="sub">No suggestion here was implemented. The scope this session claimed on the coordination
board was deliberately limited to new files, so that six other sessions' work could not be disturbed.
Any of these options can be executed by whoever owns the target build, without re-reading this
analysis.</p>
%(foot)s
""" % {
        "n": len(sug["rows"]),
        "tbl": table(["Order", "Suggestion", "Fixes", "Effort", "Risk", "Unlocks", "Status", "Evidence"], rows,
                     align={0: "n"}),
        "cards": "".join(cards),
        "foot": foot(),
    }
    return page("Suggestions", "suggestions.html", body)


def build_flagged(fl):
    rows = []
    for r in fl["rows"]:
        rows.append([
            '<span class="id" id="%s">%s</span>' % (r["id"].lower(), e(r["id"])),
            "<strong>%s</strong>" % e(r["topic"]),
            e(r["detail"]),
            e(r["why_it_matters"]),
            link(r["official_url"]),
            e(r["proposed_fix"]),
            '<span class="pill %s">%s</span>' % ("bad" if r["severity"] == "High" else ("warn" if r["severity"] == "Medium" else "mut"), e(r["severity"])),
        ])
    hi = sum(1 for r in fl["rows"] if r["severity"] == "High")
    body = """
<h1>Flagged for review</h1>
<p class="lede">%(n)d items this session could not confirm from an official source, or where the
official source and the repository disagree. Every item carries the URL to check it by hand and a
concrete proposal for closing it.</p>

<div class="banner"><b>Being on this page does not mean a value is wrong.</b> It means the value is not
proven. The six high-severity items do change decisions; the rest are housekeeping. Nothing on this page
was corrected in another session's files &mdash; each item names who should fix it.</div>

<div class="kpis">%(kp)s</div>

%(tbl)s

<h2>How to review these</h2>
<ol class="steps">
<li>Open the official link in the row and compare it with what the repository publishes. Every link here
was opened in this session, so it is known to resolve.</li>
<li>If the official value is right and the repository's is wrong, the fix is a re-capture &mdash; the
proposed fix in the row says which builder to change.</li>
<li>If the official value has moved since this capture, the item closes itself: record the new edition
stamp and delete the row.</li>
<li>If a value genuinely cannot be confirmed (e.g. two official reads disagree), keep the row and keep
publishing the value as unverified. Deleting the row would be the one wrong answer.</li>
</ol>
%(foot)s
""" % {
        "n": len(fl["rows"]),
        "kp": "".join([
            kpi(hi, "high severity", "change a decision", "bad"),
            kpi(sum(1 for r in fl["rows"] if r["severity"] == "Medium"), "medium", "fix in next build", "warn"),
            kpi(sum(1 for r in fl["rows"] if r["severity"] == "Low"), "low", "housekeeping"),
            kpi(len(fl["rows"]), "total", "all with an official link"),
        ]),
        "tbl": table(["#", "Topic", "What was found", "Why it matters", "Official source",
                      "Proposed fix", "Severity"], rows),
        "foot": foot(),
    }
    return page("Flagged for review", "flagged.html", body)


def build_sources(src):
    rows = []
    for r in src["rows"]:
        rows.append([
            '<span class="id">%s</span>' % e(r["id"]),
            e(r["source"]),
            link(r["url"]),
            '<span class="tiny">%s</span>' % e(r["host"]),
            '<span class="pill %s">%s</span>' % ("ok" if r["type"] == "official" else "mut", e(r["type"])),
            e(r["used_for"]),
            '<span class="tiny">%s</span>' % e(r["sections"]),
        ])
    off = sum(1 for r in src["rows"] if r["type"] == "official")
    body = """
<h1>Source register</h1>
<p class="lede">%(n)d sources. %(off)d are official NBA pages read in this session; the rest are
repository files, used only for statements about the repository's own code or data &mdash; never as
evidence about the world.</p>

<div class="banner"><b>The rule.</b> A value is confirmed only against an NBA-operated host:
www.nba.com, official.nba.com or ak-static.cms.nba.com. No sportsbook, aggregator, news outlet or
prediction service was used to confirm any value on this site.</div>

%(tbl)s

<h2>Why there is no odds source here</h2>
<p class="sub">No NBA-operated source publishes a sportsbook price, and no licensed price feed is
connected to this repository. That is not an oversight in this session's research &mdash; it is the
central open question of the project (<a href="questions.html#q-01">Q-01</a>) and the reason every "edge"
number on the main site is model-versus-model rather than model-versus-market. A sportsbook's price
would also not be an <em>official</em> source in the sense this site uses the word, which is why this
register contains none.</p>
%(foot)s
""" % {
        "n": len(src["rows"]),
        "off": off,
        "tbl": table(["#", "Source", "URL", "Host", "Type", "Used for", "Where it is cited"], rows),
        "foot": foot(),
    }
    return page("Sources", "sources.html", body)


def main():
    summary = load("summary.json")
    ver = load("verification.json")
    rev = load("repo_review.json")
    fl = load("flagged.json")
    sug = load("suggestions.json")
    qs = load("questions.json")
    src = load("sources.json")

    outputs = {
        "index.html": build_index(summary, ver, rev, fl, sug, qs),
        "summary.html": build_summary(summary),
        "verification.html": build_verification(ver),
        "review.html": build_review(rev),
        "questions.html": build_questions(qs),
        "suggestions.html": build_suggestions(sug),
        "flagged.html": build_flagged(fl),
        "sources.html": build_sources(src),
    }
    for name, text in outputs.items():
        path = os.path.join(V, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote verified/%s (%d bytes)" % (name, len(text.encode("utf-8"))))
    print("build_verified: %d pages" % len(outputs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
