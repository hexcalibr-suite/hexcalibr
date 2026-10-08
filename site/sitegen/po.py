# SPDX-FileCopyrightText: 2026 Matteo Beretta
# SPDX-License-Identifier: GPL-3.0-or-later
"""gettext PO / POT files, read and written with the standard library only.

Why our own few lines and not polib or msgmerge: the site must build on a bare
Python with PyYAML, on a translator's laptop as on GitHub Actions, and the
subset of PO we need is small - msgctxt, msgid, msgstr, translator and
extracted comments, the `fuzzy` flag and the `#|` previous msgid. Plural forms
are not used: the guide has no counted nouns that depend on a run-time number.

The files written here are ordinary gettext files: Weblate, Poedit, Lokalize
and `msgfmt --check` read them, and Weblate's own msgmerge add-on can be used
instead of `update()` if preferred.
"""
import difflib
import re


class Entry:
    __slots__ = ("ctxt", "msgid", "msgstr", "fuzzy", "previous", "comments",
                 "extracted", "refs")

    def __init__(self, ctxt, msgid, msgstr="", fuzzy=False, previous=None,
                 comments=None, extracted=None, refs=None):
        self.ctxt, self.msgid, self.msgstr = ctxt, msgid, msgstr
        self.fuzzy, self.previous = fuzzy, previous
        self.comments = comments or []          # "# " lines, the translator's own
        self.extracted = extracted or []        # "#. " lines, from the source
        self.refs = refs or []                  # "#: " lines

    @property
    def key(self):
        return (self.ctxt, self.msgid)


def _unquote(s):
    s = s.strip()
    if not (s.startswith('"') and s.endswith('"')):
        raise ValueError("not a PO string: %r" % s)
    s = s[1:-1]
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _quote(s):
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t")
    lines = s.split("\n")
    if len(lines) == 1 and len(s) < 70:
        return '"%s"' % s
    # multi-line or long: the gettext convention, an empty first line and
    # one line per source line (and wrapped at spaces for long ones)
    out = ['""']
    for k, line in enumerate(lines):
        if k < len(lines) - 1:
            line += "\\n"
        elif line == "":
            continue
        while len(line) > 76:
            cut = line.rfind(" ", 0, 76)
            if cut <= 0:
                break
            out.append('"%s"' % line[:cut + 1])
            line = line[cut + 1:]
        out.append('"%s"' % line)
    return "\n".join(out)


def read(path):
    """(header text, [Entry]) of a PO/POT file. Obsolete (#~) entries are
    dropped: they are kept by git history, not by the file."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    entries, header = [], ""
    cur, field = None, None
    pend = {"comments": [], "extracted": [], "refs": [], "fuzzy": False, "previous": None}

    def flush():
        nonlocal cur, header
        if cur is None:
            return
        if cur["msgid"] == "" and cur["ctxt"] is None:
            header = cur["msgstr"]
        else:
            entries.append(Entry(cur["ctxt"], cur["msgid"], cur["msgstr"],
                                 cur["fuzzy"], cur["previous"], cur["comments"],
                                 cur["extracted"], cur["refs"]))
        cur = None

    for raw in lines + [""]:
        line = raw.rstrip()
        if line.startswith("#~"):
            continue
        if line == "":
            flush()
            field = None
            continue
        if line.startswith("#"):
            if cur is not None and field is not None:
                flush()
                field = None
            if line.startswith("#,"):
                pend["fuzzy"] = "fuzzy" in line
            elif line.startswith("#|"):
                m = re.match(r'#\|\s*msgid\s+(".*")$', line)
                if m:
                    pend["previous"] = _unquote(m.group(1))
            elif line.startswith("#."):
                pend["extracted"].append(line[2:].strip())
            elif line.startswith("#:"):
                pend["refs"].append(line[2:].strip())
            else:
                pend["comments"].append(line[1:].strip())
            continue
        m = re.match(r'(msgctxt|msgid|msgstr)\s+(".*")$', line)
        if m:
            kw, val = m.group(1), _unquote(m.group(2))
            if kw == "msgctxt" or (kw == "msgid" and (cur is None or field == "msgstr")):
                if cur is not None and field == "msgstr":
                    flush()
                if cur is None:
                    cur = {"ctxt": None, "msgid": "", "msgstr": ""}
                    cur.update({k: v for k, v in pend.items()})
                    pend = {"comments": [], "extracted": [], "refs": [],
                            "fuzzy": False, "previous": None}
            if kw == "msgctxt":
                cur["ctxt"] = val
            else:
                cur[kw] = val
            field = kw
            continue
        if line.startswith('"') and cur is not None and field:
            key = "ctxt" if field == "msgctxt" else field
            cur[key] = cur[key] + _unquote(line)
            continue
        raise ValueError("%s: cannot read line %r" % (path, raw))
    return header, entries


def write(path, header, entries, translations=True):
    out = []
    out.append('msgid ""')
    out.append("msgstr " + _quote(header))
    for e in entries:
        out.append("")
        for c in e.comments:
            out.append("# " + c if c else "#")
        for c in e.extracted:
            out.append("#. " + c)
        for r in e.refs:
            out.append("#: " + r)
        if e.fuzzy and translations:
            out.append("#, fuzzy")
        if e.previous is not None and translations:
            out.append("#| msgid " + _quote(e.previous).replace("\n", "\n#| "))
        if e.ctxt is not None:
            out.append("msgctxt " + _quote(e.ctxt))
        out.append("msgid " + _quote(e.msgid))
        out.append("msgstr " + _quote(e.msgstr if translations else ""))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def merge(template, existing):
    """A language's entries brought in line with the template (POT), as
    msgmerge does it:

      - same context and same English: the translation is kept as it is;
      - same context, English changed: the old translation is kept but marked
        fuzzy, with the old English in `#| msgid`, so the translator sees
        exactly what changed. The build does not use fuzzy strings - the
        reader gets the current English instead of an outdated translation;
      - nothing similar: empty.

    Returns (entries, counts)."""
    by_key = {e.key: e for e in existing}
    by_ctxt = {}
    for e in existing:
        by_ctxt.setdefault(e.ctxt, []).append(e)
    used, out = set(), []
    counts = {"kept": 0, "fuzzy": 0, "new": 0, "dropped": 0}
    for t in template:
        old = by_key.get(t.key)
        n = Entry(t.ctxt, t.msgid, extracted=list(t.extracted), refs=list(t.refs))
        if old is not None and old.msgstr:
            n.msgstr, n.fuzzy, n.previous = old.msgstr, old.fuzzy, old.previous
            n.comments = old.comments
            used.add(old.key)
            counts["fuzzy" if old.fuzzy else "kept"] += 1
        else:
            best, score = None, 0.0
            for cand in by_ctxt.get(t.ctxt, []):
                if cand.key in used or not cand.msgstr or cand.key in {x.key for x in template}:
                    continue
                r = difflib.SequenceMatcher(None, cand.msgid, t.msgid).ratio()
                if r > score:
                    best, score = cand, r
            if best is not None and score >= 0.55:
                n.msgstr, n.fuzzy, n.previous = best.msgstr, True, best.msgid
                n.comments = best.comments
                used.add(best.key)
                counts["fuzzy"] += 1
            else:
                counts["new"] += 1
        out.append(n)
    counts["dropped"] = sum(1 for e in existing if e.msgstr and e.key not in used
                            and e.key not in {x.key for x in template})
    return out, counts
