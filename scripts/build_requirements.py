#!/usr/bin/env python3
"""Render the brief-traceability register from data/content/requirements.json.

Called by scripts/build_dashboard.py (builder-cannot-drop: a rebuild of the site
always regenerates this page). Session arena/513516f6-nba1, COORDINATION section 41.

Rule: a status is set only by repository evidence or an official source; rows
that cannot be sourced stay visible as partial, missing or blocked.
"""
import html
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, "data", "content", "requirements.json")

STATUS_LABEL = {"done": "Done", "partial": "Partial", "missing": "Missing", "blocked": "Blocked"}
STATUS_CLASS = {"done": "ok", "partial": "warn", "missing": "bad", "blocked": "bad"}


def _esc(v):
    return html.escape(str(v), quote=True)


def render(page, table):
    """page and table are the shared helpers from scripts/build_dashboard.py."""
    with open(REGISTER, encoding="utf-8") as fh:
        reg = json.load(fh)
    rows = reg["rows"]
    counts = Counter(r["status"] for r in rows)

    tiles = []
    for key in ["done", "partial", "missing", "blocked"]:
        tiles.append(
            '<div class="tile"><div class="tile-n">%d</div><div class="tile-l">%s</div></div>'
            % (counts.get(key, 0), STATUS_LABEL[key])
        )
    key_html = "".join(
        "<li><b>%s</b> &mdash; %s</li>" % (STATUS_LABEL[k], _esc(v)) for k, v in reg["status_key"].items()
    )

    body_rows = []
    for r in rows:
        status = (
            '<span class="pill %s">%s</span>'
            % (STATUS_CLASS.get(r["status"], "warn"), STATUS_LABEL.get(r["status"], r["status"]))
        )
        links = " &middot; ".join(
            '<a href="%s" target="_blank" rel="noopener">%s</a>' % (_esc(l["url"]), _esc(l["label"]))
            for l in r["links"]
        )
        body_rows.append([
            "<b>%s</b>" % _esc(r["id"]),
            _esc(r["requirement"]),
            status,
            _esc(r["evidence"]),
            _esc(r["gap"]),
            links,
        ])

    body = (
        '<section class="card"><p><b>Status counts</b></p>'
        '<div class="tiles">%s</div>'
        '<ul class="tnote">%s</ul>'
        '<p class="tnote">Repository links are code and data evidence in this repository. '
        'NBA.com links are the official pages the data was read from. No row fills a value '
        'that the repository does not contain. Full register: '
        '<a href="../../data/content/requirements.json">requirements.json</a>.</p></section>'
        % ("".join(tiles), key_html)
    )
    body += table(
        ["ID", "Brief requirement", "Status", "What the repository contains", "Gap / next step", "Source links"],
        body_rows,
        note="%d requirements traced to repository evidence, %s."
        % (len(rows), ", ".join("%d %s" % (counts.get(k, 0), k) for k in ["done", "partial", "missing", "blocked"])),
        source_col="Source links",
        table_id="requirements",
    )
    return page(
        "Brief traceability",
        "Every requirement in the brief, checked against the repository. Done, partial, missing or blocked, "
        "with the gap stated and a link to the evidence.",
        body,
        depth=1,
    )
