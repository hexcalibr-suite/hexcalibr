# SPDX-FileCopyrightText: 2026 Matteo Beretta
# SPDX-License-Identifier: GPL-3.0-or-later
"""The documentation site of the calibration suite.

Run from the site/ folder:

    python3 -m sitegen build          build every language into _build/
    python3 -m sitegen extract        write locales/messages.pot from the English
    python3 -m sitegen update [xx]    bring locales/xx.po (all if omitted) in line
                                      with the POT: changed English -> fuzzy
    python3 -m sitegen init xx        start a new language: locales/xx.po
    python3 -m sitegen check [xx]     verify translations keep placeholders,
                                      code, links and TBD marks; exit 1 on errors
    python3 -m sitegen stats          how complete each language is
    python3 -m sitegen shotlist       rewrite PHOTO-SHOTLIST.md from the sources

`build` also runs `extract` and `shotlist`, so the POT and the shot list never
drift from the English. Requires Python 3.8+ and PyYAML.

Preview:  python3 -m http.server -d _build 8000   ->  http://localhost:8000/
"""
import datetime
import os
import re
import shutil
import sys
import urllib.parse

from . import content, markup, po, render
from .style import STYLE


def _pot_entries(src):
    return [po.Entry(c, t, extracted=[note]) for c, t, note in content.strings(src)]


def extract(src=None, quiet=False):
    src = src or content.load()
    entries = _pot_entries(src)
    header = ("Project-Id-Version: %s docs\n"
              "Report-Msgid-Bugs-To: \n"
              "POT-Creation-Date: %s\n"
              "Language: \n"
              "MIME-Version: 1.0\n"
              "Content-Type: text/plain; charset=UTF-8\n"
              "Content-Transfer-Encoding: 8bit\n"
              % (src["site"]["suite_name"], datetime.date.today().isoformat()))
    os.makedirs(content.LOCALES, exist_ok=True)
    path = os.path.join(content.LOCALES, "messages.pot")
    # keep the file byte-stable when nothing changed (no date-only diffs)
    if os.path.exists(path):
        _, old = po.read(path)
        if [(e.ctxt, e.msgid, e.extracted) for e in old] == \
           [(e.ctxt, e.msgid, e.extracted) for e in entries]:
            if not quiet:
                print("extract: messages.pot unchanged (%d strings)" % len(entries))
            return entries
    po.write(path, header, entries, translations=False)
    if not quiet:
        print("extract: %d strings -> %s" % (len(entries), path))
    return entries


def _header(code, name):
    return ("Project-Id-Version: docs\n"
            "PO-Revision-Date: %s\n"
            "Last-Translator: \n"
            "Language: %s\n"
            "Language-Team: %s\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/plain; charset=UTF-8\n"
            "Content-Transfer-Encoding: 8bit\n"
            "Plural-Forms: nplurals=2; plural=(n != 1);\n"
            % (datetime.date.today().isoformat(), code, name))


def update(codes=None):
    src = content.load()
    template = extract(src, quiet=True)
    codes = codes or [c for c in src["languages"] if c != "en"]
    for code in codes:
        path = os.path.join(content.LOCALES, code + ".po")
        if os.path.exists(path):
            header, old = po.read(path)
        else:
            header, old = _header(code, src["languages"].get(code, {}).get("name", code)), []
        merged, counts = po.merge(template, old)
        po.write(path, header, merged)
        print("update %s: %d kept, %d fuzzy, %d new, %d dropped" %
              (code, counts["kept"], counts["fuzzy"], counts["new"], counts["dropped"]))


def init(code):
    if not re.fullmatch(r"[a-z]{2,3}(_[A-Z]{2})?", code):
        raise SystemExit("init: %r is not a language code like 'de' or 'pt_BR'" % code)
    path = os.path.join(content.LOCALES, code + ".po")
    if os.path.exists(path):
        raise SystemExit("init: %s exists already" % path)
    update([code])
    print("now add `%s` to languages.yaml (enabled: false until it is ready)" % code)


def translations(code):
    path = os.path.join(content.LOCALES, code + ".po")
    if not os.path.exists(path):
        return {}
    _, entries = po.read(path)
    return {e.key: e.msgstr for e in entries if e.msgstr and not e.fuzzy}


def check(codes=None):
    src = content.load()
    codes = codes or [c for c in src["languages"] if c != "en"]
    bad = 0
    for code in codes:
        path = os.path.join(content.LOCALES, code + ".po")
        if not os.path.exists(path):
            print("check %s: no %s" % (code, path))
            bad += 1
            continue
        _, entries = po.read(path)
        for e in entries:
            if not e.msgstr or e.fuzzy:
                continue
            a, b = markup.tokens(e.msgid), markup.tokens(e.msgstr)
            for k in a:
                if a[k] != b[k]:
                    bad += 1
                    print("check %s: [%s] %s differ\n    en: %s\n    %s: %s"
                          % (code, e.ctxt, k, e.msgid[:120], code, e.msgstr[:120]))
            if e.ctxt.startswith("ui/") and e.msgid.count("%") != e.msgstr.count("%"):
                bad += 1
                print("check %s: [%s] %%-fields differ" % (code, e.ctxt))
    print("check: %s" % ("OK" if not bad else "%d problem(s)" % bad))
    return bad


def stats(src=None):
    src = src or content.load()
    total = content.strings(src)
    for code in src["languages"]:
        if code == "en":
            continue
        tr = translations(code)
        done = sum(1 for c, t, _ in total if (c, t) in tr)
        print("%s: %d/%d translated (%.0f%%)" % (code, done, len(total), 100.0 * done / max(1, len(total))))


SHOTLIST_HEAD = """<!-- Generated by `python3 -m sitegen shotlist` (and by every build) from the
     `photos:` entries in content/. Edit the shot briefs there, not here. -->

# Photo shot list

Photos for the {suite} guides, to be taken by the owner. Every photo has a
fixed file name: save it as `site/img/<id>.jpg` and the next build replaces
the placeholder with the photo, in every language (photos are shared, so they
must not contain words; anything to say goes in the caption).

## Protocol (applies to every shot)

- **Background:** matte black or matte mid-grey card, no texture, no clutter.
- **Lighting:** one hard light raking at 10–20° from the side opposite the
  camera (it shows layer lines, droop and strings), plus a soft fill so
  shadows are not pure black. No on-camera flash.
- **Filament:** the reference set is **PETG** (it strings and sags more than
  PLA, so the fail examples read clearly), in a light, opaque colour (white,
  light grey, yellow). Avoid silk, matte, glitter and transparent filament: they
  change gloss and hide the defects being shown.
- **Framing:** the same framing, distance and light for every variant of the
  same shot (fail-hot / optimal / fail-cold), so the reader compares the part,
  not the photo. Tripod; camera square to the face being shown unless noted.
- **Scale:** a ruler or caliper in the overview shot of each test.
- **Size:** at least 2000 px on the long side, JPEG quality ~85, 4:3 landscape
  unless noted; the site scales them down.
- **Strings:** shoot stringing BEFORE brushing or touching the print. On the
  temperature tower, backlight the string ladder (lamp or window behind it,
  camera looking through its window); elsewhere, a dark background with the
  raking light from behind-side, or strings are invisible.
- **Labels:** the engraved temperature is on the front face only. Keep it
  readable in every block close-up of the front, front-left or front-right
  face; for shots of the other faces put a small paper tag with the
  temperature next to the tower, so the reader can match photo and tower.
- **Faces (hex tower):** each brief starts with the face or corner to shoot.
  Hold the tower with the engraved numbers facing you and turn it clockwise
  (seen from above): front (label), front-right (smooth face), back-right
  (ramp 55-80°), back (plain), back corner (string ladder), back-left (flag
  at the shelf edge), front-left (the 22 mm bridge beam on two long ribs).
  Tower v2.2. Reference renders: `docs/previews/hex-block-*.png`.
- **Faces (pressure advance tower):** hold it with the engraved band numbers
  facing you. Front-right face: 15 mm straight into the right 90° tip; back
  face: the seam bump, then the back-left 90° tip; front-left face: 18 mm
  straight into the 45° tip; inside corners where each blade folds back.
  Only the front face carries band numbers: for shots of the tips put a
  small paper tag with the band number beside the tower. Reference renders:
  `docs/previews/pa-band-*.png`.
- **IDEX alignment (F7):** one layer, read on the bed. PETG in **two contrasting
  colours** (T0 orange, T1 blue, or black and white), top-down with the **front
  of the printer at the bottom** of the frame, so left/right and front/back are
  the printer's. Raking light along the ticks for the macro shots; even light
  for the whole-bed shot. Reference renders: `docs/previews/idex-*.png`.
- **Naming:** `<testID>_<state>_<material>_<printer>`, already set in the ids
  below (test F1 = temperature tower, F2 = pressure advance, F7 = IDEX alignment).

## Shots

"""


def shotlist(src=None):
    src = src or content.load()
    rows = content.all_photos(src)
    out = [SHOTLIST_HEAD.replace("{suite}", src["site"]["suite_name"])]

    def stand_in(ph):
        return bool(ph.get("stand_in")) and os.path.exists(os.path.join(content.IMG, ph["id"] + ".standin.jpg"))
    redo = [(pid, where, ph) for pid, where, ph in rows if stand_in(ph) and not any(
        os.path.exists(os.path.join(content.IMG, ph["id"] + ext)) for ext in (".jpg", ".jpeg", ".png", ".webp", ".svg"))]
    if redo:
        # before the protocol's "## Shots" heading: the first thing the owner reads
        out[0] = out[0].replace("## Protocol", "## Stand-ins: to redo\n\n"
            "These slots show an existing photo for now (`site/img/<id>.standin.jpg`), labelled\n"
            "\"Provisional photo\" on the site. It does not show what the caption needs, so the shot\n"
            "must still be taken. Save the real photo as `site/img/<id>.jpg`: it replaces the stand-in,\n"
            "then delete the `.standin.jpg` and the `stand_in:` entry in content/.\n\n"
            "| File id | Page / feature | Stand-in now | Why it must be redone |\n|---|---|---|---|\n"
            + "".join("| `%s` | %s / %s | %s | %s |\n" % (ph["id"], src["pages"][pid]["title"], where.replace("|", "/"),
                                                       ph["stand_in"].get("source", "").replace("|", "/"),
                                                       ph["stand_in"].get("redo", "").replace("|", "/"))
                      for pid, where, ph in redo)
            + "\n## Protocol", 1)
    current = None
    for pid, where, ph in rows:
        if pid != current:
            current = pid
            out.append("### %s\n" % src["pages"][pid]["title"])
            out.append("| # | File id | Step / feature | What it must show (shot brief) | Caption on the site |")
            out.append("|---|---|---|---|---|")
            k = 0
        k += 1
        video = ph.get("kind") == "video"
        exts = (".webm", ".mp4") if video else (".jpg", ".jpeg", ".png", ".webp", ".svg")
        have = bool(ph.get("youtube")) or any(os.path.exists(os.path.join(content.IMG, ph["id"] + ext))
                                              for ext in exts)
        redo_now = not have and stand_in(ph)
        out.append("| %d | `%s`%s%s | %s | %s%s | %s |"
                   % (k, ph["id"], " VIDEO" if video else "",
                      " (done)" if have else " **STAND-IN, TO REDO**" if redo_now else "", where.replace("|", "/"),
                      "**TO REDO:** %s **Brief:** " % ph["stand_in"].get("redo", "").replace("|", "/") if redo_now else "",
                      ph.get("shot", "").replace("|", "/").replace("\n", " "),
                      ph.get("caption", "").replace("|", "/")))
    out.append("")
    out.append("Total: %d shots (%d videos)." % (len(rows), sum(1 for _, _, ph in rows if ph.get("kind") == "video")))
    path = os.path.join(content.HERE, "PHOTO-SHOTLIST.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return len(rows)


def build():
    src = content.load()
    extract(src, quiet=True)
    n_photos = shotlist(src)
    out = content.BUILD
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    langs = {c: v for c, v in src["languages"].items() if v.get("enabled", True)}
    if list(langs)[0] != "en":
        raise SystemExit("languages.yaml: English must be first (it is the source)")
    english = content.strings(src)
    for code in langs:
        if code == "en":
            tsrc = src
            missing = 0
        else:
            tr = translations(code)
            miss = []

            def fn(ctxt, text, note, tr=tr, miss=miss):
                if (ctxt, text) in tr:
                    return tr[(ctxt, text)]
                miss.append((ctxt, text))
                return text
            tsrc = content.walk(src, fn)
            missing = len(set(miss))
        values = {"suite": src["site"]["suite_name"],
                  "author": src["site"]["author"],
                  "guide_url": src["site"].get("base_url") or ""}
        site = render.Site(tsrc, code, langs, content.IMG, values)
        folder = out if code == "en" else os.path.join(out, code)
        os.makedirs(folder, exist_ok=True)
        for pid in site.order:
            with open(os.path.join(folder, render.page_file(pid)), "w", encoding="utf-8") as f:
                f.write(site.page(pid))
        print("build %s: %d pages%s" % (code, len(site.order),
                                         "" if code == "en" else ", %d strings untranslated (shown in English)" % missing))
    with open(os.path.join(out, "guide.css"), "w", encoding="utf-8") as f:
        f.write(STYLE)
    # the brand kit (../brand): favicon, logo for the header, PNG icon, link-preview card
    brand = os.path.join(content.HERE, "..", "brand")
    for b_src, dst in (("favicon/favicon.svg", "favicon.svg"), ("icon/icon.svg", "logo.svg"),
                       ("icon/icon-dark.svg", "logo-dark.svg"), ("icon/icon-256.png", "icon-256.png"),
                       ("social/og-image.png", "og-image.png")):
        if os.path.exists(os.path.join(brand, b_src)):
            shutil.copyfile(os.path.join(brand, b_src), os.path.join(out, dst))
        elif dst == "favicon.svg":
            with open(os.path.join(out, dst), "w", encoding="utf-8") as f:
                f.write(render.FAVICON_FALLBACK)
    open(os.path.join(out, ".nojekyll"), "w").close()
    base = (src["site"].get("base_url") or "").rstrip("/")
    write_extras(out, src, langs, base)
    # GitHub Pages custom domain, taken from base_url.
    host = urllib.parse.urlparse(src["site"].get("base_url") or "").hostname
    if host and not host.endswith("github.io"):
        with open(os.path.join(out, "CNAME"), "w", encoding="utf-8") as f:
            f.write(host + "\n")
    if os.path.isdir(content.IMG):
        imgs = [n for n in os.listdir(content.IMG) if n.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".svg", ".webm", ".mp4"))]
        if imgs:
            os.makedirs(os.path.join(out, "img"))
            for n in imgs:
                shutil.copyfile(os.path.join(content.IMG, n), os.path.join(out, "img", n))
    tbd = sorted({m for _, t, _ in english for m in markup.TBD.findall(t)})
    print("build: %d photo slots (see PHOTO-SHOTLIST.md); %d distinct TBD marks:" % (n_photos, len(tbd)))
    for t in tbd:
        print("   TBD: " + t)
    print("build: done -> %s" % out)


NOT_FOUND = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="robots" content="noindex">
<title>Page not found — {suite}</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="/guide.css">
</head>
<body>
<main id="contenuto" style="max-width: 40rem; margin: 4rem auto; padding: 0 1rem;">
<p><a href="/"><img src="/logo.svg" alt="" width="48" height="64"></a></p>
<h1>Page not found</h1>
<p>This page does not exist, or it has moved. Start again from the <a href="/">{suite} home page</a>.</p>
<p lang="it" hreflang="it">Pagina non trovata. Riparti dalla <a href="/it/">pagina iniziale in italiano</a>.</p>
</main>
</body>
</html>
"""


def write_extras(out, src, langs, base):
    """404.html (GitHub Pages serves it for any missing path, so its links are
    root-relative), robots.txt, and sitemap.xml with hreflang alternates."""
    suite = src["site"]["suite_name"]
    with open(os.path.join(out, "404.html"), "w", encoding="utf-8") as f:
        f.write(NOT_FOUND.replace("{suite}", suite))
    robots = "User-agent: *\nAllow: /\n"
    if base:
        robots += "Sitemap: %s/sitemap.xml\n" % base
    with open(os.path.join(out, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots)
    if not base:
        return

    def url(pid, code):
        f = render.page_file(pid)
        rel = f if code == "en" else "%s/%s" % (code, f)
        return base + "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)

    pids = [e["page"] for g in src["site"]["contents"] for e in g["entries"] if "page" in e]
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for pid in pids:
        for code in langs:
            rows.append("  <url><loc>%s</loc>" % url(pid, code))
            for other in langs:
                rows.append('    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (other, url(pid, other)))
            rows.append('    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>' % url(pid, "en"))
            rows.append("  </url>")
    rows.append("</urlset>")
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == "build":
        build()
    elif cmd == "extract":
        extract()
    elif cmd == "update":
        update(args or None)
    elif cmd == "init":
        if len(args) != 1:
            raise SystemExit("usage: python3 -m sitegen init <code>")
        init(args[0])
    elif cmd == "check":
        return 1 if check(args or None) else 0
    elif cmd == "stats":
        stats()
    elif cmd == "shotlist":
        print("shotlist: %d photos" % shotlist())
    else:
        raise SystemExit("unknown command %r; see python3 -m sitegen --help" % cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
