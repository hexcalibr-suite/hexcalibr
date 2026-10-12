# SPDX-FileCopyrightText: 2026 Matteo Beretta
# SPDX-License-Identifier: GPL-3.0-or-later
"""Release consistency: when a test moves from `planned:` to a written page,
every place that lists the tests must follow. Run by `check` (and so by CI,
which then refuses to deploy).

Rules, on the English sources:
- the home's release list links every written test (page:<id>) and, once its
  Printables address is known, its files (link:printables-<id>);
- the release intro says how many tests there are, in words ("six tests");
- its "Coming next" point names every planned test, and nothing else;
- the full path in the "fast or full" table links every written test;
- in any table cell, a numbered item with no link must be a planned test
  (an unlinked "3. Flow" after the flow guide is out is an error).
"""
import re

NUMBERS = "zero one two three four five six seven eight nine ten eleven twelve".split()
LINK = re.compile(r"\]\((page|link):([\w-]+)(?:#[\w-]*)?\)")
ITEM = re.compile(r"^\s*\d+\.\s+(.*)$")


def _tests(site):
    """Written test pages and planned names, from the numbered groups."""
    pages, planned = [], []
    for g in site["contents"]:
        if not g.get("numbered"):
            continue
        for e in g["entries"]:
            if "page" in e:
                pages.append(e["page"])
            elif "planned" in e:
                planned.append(e["planned"])
    return pages, planned


def _first_word(s):
    return re.sub(r"[^\w\s]", " ", s).split()[0].lower()


def _texts(step):
    out = list(step.get("points", []))
    for k in ("intro", "after"):
        if k in step:
            out.append(step[k])
    return [p if isinstance(p, str) else next(iter(p.values())) for p in out]


def check(src):
    site, pages = src["site"], src["pages"]
    tests, planned = _tests(site)
    links = site.get("links", {})
    problems = []
    home = {st["id"]: st for st in pages["home"].get("steps", []) if "id" in st}

    # the release list
    rel = home.get("release-1")
    if not rel:
        problems.append("home: no `release-1` step")
    else:
        texts = _texts(rel)
        found = {(k, v) for t in texts for k, v in LINK.findall(t)}
        for pid in tests:
            if ("page", pid) not in found:
                problems.append("home/release-1: no [..](page:%s) for the written test %r"
                                % (pid, pages[pid]["nav_title"]))
            if links.get("printables-" + pid) and ("link", "printables-" + pid) not in found:
                problems.append("home/release-1: no [..](link:printables-%s), "
                                "although its Printables address is filled in" % pid)
        m = re.search(r"\b(\w+) tests\b", rel.get("intro", ""))
        want = NUMBERS[len(tests)] if len(tests) < len(NUMBERS) else str(len(tests))
        if not m or m.group(1).lower() != want:
            problems.append("home/release-1 intro: says %r tests, the contents have %s (%s)"
                            % (m.group(1) if m else None, want, ", ".join(tests)))
        coming = [t for t in texts if "Coming next" in t]
        if planned and not coming:
            problems.append("home/release-1: no \"Coming next\" point for %s" % planned)
        for t in coming:
            low = t.lower()
            for name in planned:
                if _first_word(name) not in low:
                    problems.append("home/release-1 Coming next: planned test %r missing" % name)
            for pid in tests:
                w = _first_word(pages[pid]["nav_title"])
                if re.search(r"\b%s\b" % re.escape(w), low):
                    problems.append("home/release-1 Coming next: names %r, which is written"
                                    % pages[pid]["nav_title"])

    # the fast or full table: the full path links every written test
    tab = home.get("fast-or-full", {}).get("table")
    if tab:
        row = next((r for r in tab["rows"] if r[0] == "Tests"), None)
        if row is None:
            problems.append("home/fast-or-full: no \"Tests\" row")
        else:
            full = {v for k, v in LINK.findall(row[-1]) if k == "page"}
            for pid in tests:
                if pid not in full:
                    problems.append("home/fast-or-full full path: no link to %r" % pid)

    # any table cell: an unlinked numbered item must be a planned test
    planned_words = {_first_word(n) for n in planned}
    for pid, p in pages.items():
        for st in p.get("steps", []):
            for holder in (st, st.get("more") or {}):
                tab = holder.get("table") if isinstance(holder, dict) else None
                for row in (tab or {}).get("rows", []):
                    for cell in row:
                        for line in str(cell).split("\n"):
                            m = ITEM.match(line)
                            if not m or "](" in m.group(1):
                                continue
                            if _first_word(m.group(1)) not in planned_words:
                                problems.append("%s/%s table: %r has no link and is not a "
                                                "planned test" % (pid, st.get("id"), line.strip()))
    return problems
