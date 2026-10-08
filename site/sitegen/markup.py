# SPDX-FileCopyrightText: 2026 Matteo Beretta
# SPDX-License-Identifier: GPL-3.0-or-later
"""The little Markdown the guide texts use, and nothing more.

    **bold**            menu paths, setting names a reader must find, key words
    `code`              G-code, setting keys, file names - never translated
    [text](url)         a link; `page:<id>` or `page:<id>#anchor` for a page of
                        this site (resolved per language); `link:<name>` for
                        an address kept in site.yaml `links:` (download pages)
    {suite}             the project name, from content/site.yaml
    {{TBD: what}}       a number or fact that is not final yet; listed by the
                        build, shown highlighted only in drafts (site.yaml
                        `show_tbd`, or HEXCALIBR_TBD=1), dropped on the public
                        site: write the sentence so it reads without it

Kept deliberately small: every construct here is one a translator must keep
intact, and `check` verifies exactly these. A richer Markdown would mean more
ways to break a translation without noticing.
"""
import html
import re

TBD = re.compile(r"\{\{\s*TBD:\s*(.*?)\s*\}\}")
PLACEHOLDER = re.compile(r"(?<!\{)\{([a-z_]+)\}(?!\})")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
CODE = re.compile(r"`([^`]+)`")


def tokens(text):
    """What a translation must carry over unchanged: placeholders, TBD
    markers, code spans and link targets. Used by `check`."""
    return {
        "placeholders": sorted(PLACEHOLDER.findall(text)),
        "tbd": len(TBD.findall(text)),
        "code": sorted(CODE.findall(text)),
        "links": sorted(u for _, u in LINK.findall(text)),
        "bold": text.count("**") // 2,
    }


def plain(text, values):
    """The text without markup: for <title>, meta description, the filter."""
    text = TBD.sub(lambda m: "TBD: " + m.group(1) if values.get("_tbd") else "", text)
    text = PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), text)
    text = LINK.sub(lambda m: m.group(1), text)
    return text.replace("**", "").replace("`", "")


def inline(text, values, resolve):
    """One paragraph of guide text to HTML. `values` fills {placeholders};
    `resolve(target)` turns a `page:` link into a relative URL."""
    out = []
    for i, part in enumerate(text.split("`")):
        if i % 2 == 1:
            # a code span with line breaks (a printer.cfg snippet) shows as a block, line by line
            cls = " class=\"blk\"" if "\n" in part else ""
            out.append("<code%s>%s</code>" % (cls, html.escape(part.strip("\n"), quote=False)))
            continue
        out.append(_prose(part, values, resolve))
    return "".join(out)


def _prose(text, values, resolve):
    # the links first, on the raw text, so their URLs are escaped once
    pieces, last = [], 0
    for m in LINK.finditer(text):
        pieces.append(_words(text[last:m.start()], values))
        url = m.group(2)
        internal = url.startswith(("page:", "#"))
        href = resolve(url) if url.startswith(("page:", "link:")) else url
        if not href:
            # a site.yaml address not known yet (a Printables page before upload):
            # the words, greyed, with a short "coming soon" - never a dead link
            pieces.append("<span class=\"in-arrivo\" aria-disabled=\"true\">%s</span>"
                          " <small class=\"in-arrivo-nota\">(%s)</small>"
                          % (_words(m.group(1), values), html.escape(values.get("_pending", ""), quote=False)))
            last = m.end()
            continue
        # affiliate links (Amazon "tag=") are marked sponsored, as search engines require
        if internal or href == "#":
            rel = ""
        else:
            rel = " rel=\"sponsored noopener\"" if "tag=" in href else " rel=\"noopener\""
        pieces.append("<a href=\"%s\"%s>%s</a>"
                      % (html.escape(href, quote=True),
                         rel,
                         _words(m.group(1), values)))
        last = m.end()
    pieces.append(_words(text[last:], values))
    return "".join(pieces)


def _words(text, values):
    t = html.escape(text, quote=False)
    t = TBD.sub(lambda m: "<mark class=\"tbd\" title=\"To be decided\">TBD: %s</mark>"
                % m.group(1) if values.get("_tbd") else "", t)
    t = PLACEHOLDER.sub(lambda m: "<span class=\"ph-%s\">%s</span>"
                        % (m.group(1), html.escape(values[m.group(1)], quote=False))
                        if m.group(1) in values else m.group(0), t)
    parts = t.split("**")
    return "".join(p if k % 2 == 0 else "<b>%s</b>" % p for k, p in enumerate(parts))


def paragraphs(text, values, resolve):
    """A field that may hold several paragraphs, separated by a blank line."""
    return "".join("<p>%s</p>" % inline(p.strip(), values, resolve)
                   for p in re.split(r"\n\s*\n", text.strip()) if p.strip())
