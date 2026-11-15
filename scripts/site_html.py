#!/usr/bin/env python3
"""site_html.py - the small HTML helpers the NBA1 site pages are built from.

These are the same helpers `scripts/build_dashboard.py` uses (page shell, table
renderer, source links, banners). They are duplicated here in a module of their
own so the 2026-11-15 rolling-slate builder can emit pages in exactly the same
style without either script importing the other (which would execute
`build_dashboard.py` twice when it is run as `__main__`).

Nothing here knows anything about the data. It only renders it.
"""

import re
from urllib.parse import urlparse

NA = '<span class="na" title="not published - no official source confirmed this value">&mdash;</span>'


def esc(v):
    if v is None:
        return NA
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return ("%.4g" % v)
    s = str(v)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def num(v, dp=1):
    if v is None or v == "":
        return NA
    try:
        return ("%." + str(dp) + "f") % float(v)
    except (TypeError, ValueError):
        return esc(v)


def signed(v, dp=2):
    if v is None or v == "":
        return NA
    try:
        return ("%+." + str(dp) + "f") % float(v)
    except (TypeError, ValueError):
        return esc(v)


def paths(depth):
    """Relative prefixes, so every generated link resolves from the page's own folder."""
    if depth == 0:
        return {"root": "", "css": "site/assets/site.css", "js": "site/assets/site.js",
                "home": "index.html", "navbase": "site/pages/", "repo": ""}
    return {"root": "../../", "css": "../assets/site.css", "js": "../assets/site.js",
            "home": "../../index.html", "navbase": "", "repo": "../../"}


def srclink_url(url, label):
    if not url:
        return '<span class="na" title="no official source">&mdash;</span>'
    return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(url), esc(label))


def is_official_url(url):
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return (host.endswith("nba.com") or host == "nba.com"
            or (host.endswith("github.com")
                and url.startswith("https://github.com/wingbangboozle1-lang/NBA1"))
            or host == "www2.census.gov")


def table(headers, rows, note=None, source_col="Source", cls="", table_id=None,
          src_header=None, anchor_pattern=None):
    out = ['<div class="tablewrap">', '<table class="tbl %s"' % cls]
    if table_id:
        out.append(' id="%s"' % table_id)
    out.append(">")
    out.append("<thead><tr>")
    hs = list(headers)
    if hs and hs[-1] == source_col:
        hs = hs[:-1]
    for h in hs:
        out.append("<th>%s</th>" % h)
    if source_col:
        out.append('<th class="src">%s</th>' % (src_header or source_col))
    out.append("</tr></thead><tbody>")
    for r in rows:
        _rid = ""
        if anchor_pattern and r:
            _first = re.sub(r"<[^>]+>", "", str(r[0])).strip()
            if re.match(anchor_pattern, _first):
                _rid = ' id="%s"' % _first
        out.append("<tr%s>" % _rid)
        cells = r[:-1] if source_col else r
        for c in cells:
            out.append("<td>%s</td>" % c)
        if source_col:
            out.append('<td class="src">%s</td>' % (r[-1] if r else ""))
        out.append("</tr>")
    out.append("</tbody></table></div>")
    if note:
        out.append('<p class="tnote">%s</p>' % note)
    return "\n".join(out)


def card(title, body, cls=""):
    return ('<section class="card %s"><h2>%s</h2>%s</section>' % (cls, title, body))


def tiles(items):
    out = ['<div class="tiles">']
    for label, value, sub in items:
        out.append('<div class="tile"><div class="tile-v">%s</div>'
                   '<div class="tile-l">%s</div><div class="tile-s">%s</div></div>'
                   % (value, label, sub))
    out.append("</div>")
    return "\n".join(out)


def banner(kind, title, body):
    return ('<div class="banner %s"><div class="b-t">%s</div><div class="b-b">%s</div></div>'
            % (kind, title, body))


def h2(title, sub=""):
    return '<h2 class="sec">%s</h2>%s' % (title, ('<p class="secsub">%s</p>' % sub) if sub else "")


def page(title, sub, body, depth=1, nav=""):
    pth = paths(depth)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s &middot; NBA1</title>
<link rel="stylesheet" href="%(css)s">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <div class="wrap topbar-in">
    <a class="brand" href="%(home)s">
      <span class="mark">NBA1</span>
      <span class="brand-txt">Originated lines &amp; strategy lab</span>
    </a>
    <nav class="topnav">
      <a href="%(navbase)spicks.html">Horizon</a>
      <a href="%(navbase)sprojection.html">Projection</a>
      <a href="%(navbase)sbet.html">Bet (gated)</a>
      <a href="%(navbase)sstrategies.html">Evidence</a>
      <a href="%(navbase)sdecisions.html">Decisions</a>
      <a href="%(navbase)sflagged.html">Flagged</a>
    </nav>
  </div>
</header>
<div class="wrap layout">
  <aside class="sidebar">
    <div class="side-h">Sections</div>
    %(nav)s
    <div class="side-note">
      <strong>Reading rule.</strong> Every table row either links to the official source
      it came from or carries an explicit no-source mark with a stated reason (the mark
      explains why no official source exists or could confirm the cell). A blank or
      dashed cell means the value could not be confirmed from an official source &mdash;
      it is never filled in by guesswork. See
      <a href="%(navbase)sflagged.html">Flagged for Review</a>.
    </div>
  </aside>
  <main id="main">
    <div class="page-head">
      <h1>%(title)s</h1>
      <p class="sub">%(sub)s</p>
    </div>
    %(body)s
    <footer class="foot">
      <p>NBA1 &mdash; a research workspace for originating NBA lines and testing whether the
      signal is skill or luck. Nothing on this site is a betting recommendation, and no
      market price is used anywhere: every "edge" is against a naive model that stands in
      for the market, because no official NBA-operated price feed exists.</p>
      <p class="foot-l">Generated by
      <code>scripts/build_rolling_slate_2026_11_15.py</code> from the official capture in
      <code>data/captures/2026-11-15/</code>. Sources:
      <a href="%(navbase)ssources.html">source register</a>.</p>
    </footer>
  </main>
</div>
</body>
</html>
""" % {"title": title, "sub": sub, "body": body, "nav": nav, "css": pth["css"],
       "home": pth["home"], "navbase": pth["navbase"], "repo": pth["repo"]}
