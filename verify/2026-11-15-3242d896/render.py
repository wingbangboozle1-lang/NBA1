#!/usr/bin/env python3
"""Render verify/2026-11-15-3242d896/index.html from REPORT.md.

    python3 verify/2026-11-15-3242d896/render.py

Deliberately self-contained: it links only the repository's existing stylesheet
(site/assets/site.css) and nothing else, so the page cannot break when another
session rebuilds the site. No value is generated here - the numbers come from
REPORT.md, which is the audited document.
"""

import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = "../../site/assets/site.css"


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                  r'<a href="\2">\1</a>', text)
    return text


def render_table(rows):
    head, body = rows[0], rows[2:]
    out = ['<div class="tw"><table>', "<thead><tr>"]
    out += [f"<th>{inline(c.strip())}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>" + "".join(f"<td>{inline(c.strip())}</td>" for c in row) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def split_row(line):
    return [c for c in line.strip().strip("|").split("|")]


def to_html(markdown):
    lines = markdown.splitlines()
    out, i = [], 0
    open_list = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(split_row(lines[i]))
                i += 1
            out.append(render_table(block))
            continue
        if line.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            out.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
            i += 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2)
            anchor = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]
            out.append(f'<h{level} id="{anchor}">{inline(text)}</h{level}>')
            i += 1
            continue
        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append('<div class="banner info"><div class="b-b">'
                       + inline(" ".join(quote)) + "</div></div>")
            continue
        item = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if item:
            if not open_list:
                out.append("<ul>")
                open_list = True
            out.append(f"<li>{inline(item.group(2))}</li>")
            i += 1
            continue
        if open_list:
            out.append("</ul>")
            open_list = False
        if line.strip() == "---":
            out.append("<hr>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
        i += 1
    if open_list:
        out.append("</ul>")
    return "\n".join(out)


def main():
    markdown = open(os.path.join(HERE, "REPORT.md"), encoding="utf-8").read()
    body = to_html(markdown)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scheduled-refresh integrity audit — NBA1 session arena/3242d896-nba1</title>
<link rel="stylesheet" href="{CSS}">
</head>
<body>
<header class="topbar"><div class="wrap topbar-in">
  <a class="brand" href="../../site/pages/picks.html"><span class="mark">NBA1</span>
    <span class="brand-txt">Verification report</span></a>
  <nav class="topnav">
    <a href="../../site/pages/flagged.html">Flagged for review</a>
    <a href="../../site/pages/sources.html">Sources</a>
    <a href="REPORT.md">Raw report (markdown)</a>
    <a href="evidence.json">Evidence bundle</a>
  </nav>
</div></header>
<main class="wrap">
<div class="banner info">
  <div class="b-t">Scope note</div>
  <div class="b-b"><p>This report is written by session <code>arena/3242d896-nba1</code> and lives entirely
  inside its own directory (<code>verify/2026-11-15-3242d896/</code>). It edits no data, no page and no
  builder. Every number in it is reproduced by <code>reproduce.py</code> in this folder. Where a claim
  could not be established it says so; one such claim was withdrawn after checking the run that
  produced it, and the withdrawal is left visible rather than deleted.</p></div>
</div>
{body}
</main>
</body>
</html>
"""
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as handle:
        handle.write(page)
    print(f"wrote {os.path.join(HERE, 'index.html')} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
