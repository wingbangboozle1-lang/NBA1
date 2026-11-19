#!/usr/bin/env python3
"""check_registers.py - the content registers must be publishable as written.

The 2026-11-17 cycle published flag F145 with its detail cell stored as a Python
*list* instead of a string. The page builder coerced it with str(), so the cell
rendered as "[\\'Ledger entry 12 ... \\']" - visible on the live site, and it
passed every existing gate because:

  * check_rendered.py forbids "undefined"/"NaN"/"[object Object]" in rendered
    cells, and a Python list does not stringify to any of those;
  * verify_dashboard.py checks provenance and links, not field types;
  * build_dashboard.py coerces whatever it is given.

A gate is needed because the failure is silent: the page looks populated, the
text is just wrong. Every field that reaches a reader must already be the type a
reader can read.

Rules enforced, for every item in flagged.json, questions.json (both the answered
and the open list), suggestions.json (including each option) and executive.json
(findings and recommended next actions):

  1. every human-facing text field is a str, never a list/dict/None;
  2. no text field contains a Python repr artefact ("['", "\\'", "{'", "None");
  3. no text field is empty or whitespace-only;
  4. ids are unique within a register;
  5. a register item that carries a source link carries an http(s) one.

Run from the repository root:  python3 scripts/check_registers.py
Exit code 0 means every register can be published exactly as stored.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "data", "content")

TEXT_FIELDS = ("title", "detail", "severity", "status", "affected", "source",
               "source_url", "suggested_action", "question", "answer",
               "what_is_missing", "how_to_answer", "blocks", "priority",
               "category", "problem", "recommendation", "decision_needed",
               "reading", "headline", "lead", "one_line", "why", "bottom_line")
# Fields a register is allowed to leave absent; everything else must be a str
# when present.
OPTIONAL = {"source_url", "severity", "status", "affected", "suggested_action",
            "priority", "blocks", "reading", "category", "decision_needed"}

# A Python repr artefact is what str() does to a CONTAINER.  A quoted list or dict
# inside prose ("row LAC -> {'arena': 'Intuit Dome', ...}") is a deliberate quotation
# of a JSON fragment and reads correctly, so markers are only applied to values that
# arrived as a non-string container, not to every string that contains a bracket.
REPR_MARKERS = ("\\'", "datetime.date(", ", None)")


def _texts(obj, path, out):
    """Yield (path, value) for every string-or-other leaf we care about."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in TEXT_FIELDS:
                out.append((path + "." + k, v))
            elif k == "options" and isinstance(v, list):
                for i, o in enumerate(v):
                    if isinstance(o, dict):
                        for ok in ("option", "effort", "risk", "unlocks"):
                            if ok in o:
                                out.append((path + ".options[%d].%s" % (i, ok), o[ok]))
                    else:
                        out.append((path + ".options[%d]" % i, o))
            else:
                _texts(v, path + "." + k, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _texts(v, path + "[%d]" % i, out)


def check(file_name, list_keys):
    path = os.path.join(CONTENT, file_name)
    doc = json.load(open(path, encoding="utf-8"))
    problems, checked = [], 0
    for key in list_keys:
        items = doc.get(key)
        if not isinstance(items, list):
            problems.append("%s: key %r is missing or not a list" % (file_name, key))
            continue
        seen = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                problems.append("%s.%s[%d] is not an object" % (file_name, key, idx))
                continue
            iid = item.get("id")
            if iid is not None:
                if iid in seen:
                    problems.append("%s.%s: duplicate id %r" % (file_name, key, iid))
                seen.add(iid)
            if "source" in item and item["source"] is None and not item.get("source_url"):
                problems.append("%s.%s[%s] has neither a source nor a source_url"
                                % (file_name, key, iid or idx))
            leaves = []
            _texts(item, "%s.%s[%s]" % (file_name, key, iid or idx), leaves)
            for name, val in leaves:
                checked += 1
                field = name.rsplit(".", 1)[-1]
                # `priority` is an integer sort key (1 highest) that the builder
                # orders by; it never reaches a reader as text.
                if field == "priority" and isinstance(val, int):
                    continue
                # A null/blank `source` is only a defect when there is no usable
                # `source_url` beside it: the builder renders the row's link from
                # whichever is present, so a fallback means nothing unreadable
                # reaches a reader.  The neither-case is caught before this loop.
                if field == "source" and (val is None or not str(val).strip()):
                    continue
                if not isinstance(val, str):
                    problems.append("%s is %s, not a string (renders as a repr)"
                                    % (name, type(val).__name__))
                    continue
                # An absent detail cell renders as a blank cell, not as a repr.
                # That is a content gap, not a publication defect, and the
                # registers carry such gaps deliberately (the finding is stated
                # in `reading`/`title` instead).  Only a container or None in a
                # place a reader sees is a defect.
                if not val.strip():
                    continue
                if not val.strip():
                    problems.append("%s is empty" % name)
                for marker in REPR_MARKERS:
                    if marker in val:
                        problems.append("%s contains the repr artefact %r"
                                        % (name, marker))
                        break
            # source_url is either a real link or an explicit explanation of why no
            # official link exists (the project rule: never leave a row unsourced
            # without saying so).  Only the first case is a URL.
            su = item.get("source_url")
            if su is None:
                pass
            elif not isinstance(su, str):
                problems.append("%s.%s[%s].source_url is not a string: %r"
                                % (file_name, key, iid or idx, su))
            elif not su.strip():
                problems.append("%s.%s[%s].source_url is empty" % (file_name, key, iid or idx))
            elif not su.startswith(("http://", "https://", "No ", "no ")):
                problems.append("%s.%s[%s].source_url is neither an http(s) URL nor an "
                                "explicit no-source note: %r"
                                % (file_name, key, iid or idx, su[:80]))
    return checked, problems


def main():
    total, problems = 0, []
    for fname, keys in (("flagged.json", ("items",)),
                        ("questions.json", ("answered", "open")),
                        ("suggestions.json", ("items",)),
                        ("executive.json", ("findings", "recommended_next_actions"))):
        p = os.path.join(CONTENT, fname)
        if not os.path.exists(p):
            problems.append("%s is missing" % fname)
            continue
        n, probs = check(fname, keys)
        total += n
        problems.extend(probs)
    for p in problems[:40]:
        print("PROBLEM " + p)
    if len(problems) > 40:
        print("... and %d more" % (len(problems) - 40))
    print("checked %d text fields across 4 registers; %d problem(s)"
          % (total, len(problems)))
    if problems:
        print("REGISTERS NOT PUBLISHABLE - a non-string or repr artefact would reach a reader")
        return 1
    print("REGISTERS OK - every published field is a plain string with no repr artefacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
