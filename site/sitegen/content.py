# SPDX-FileCopyrightText: 2026 Matteo Beretta
# SPDX-License-Identifier: GPL-3.0-or-later
"""The English source, and how each translatable string is found in it.

Sources (all YAML, all English):

    content/site.yaml               the project name, the contents and its groups
    content/ui.yaml                 the fixed words around the texts (Next, Step %d...)
    content/pages/<id>.yaml         one page each
    content/features/<id>.yaml      the features of a test's scoring sheet: they
                                    feed both the guide's "how to read it" steps
                                    and the printable scorecard
    languages.yaml                  which languages are built

Every translatable string is identified in the PO files by a **context**
(where it is: `temperature-tower/open-project`) plus the **English text
itself** (msgid), as gettext does. So inserting a point does not disturb
the others' translations, and changing an English sentence turns only that
translation fuzzy. Step and feature ids are stable slugs, never positions.

A step (and a feature, and a page intro) has an essential part, always
shown, and an optional `more:` part, collapsed under "More":

    - id: check
      title: "..."
      callouts: [...]          # warnings: always here, never in `more:`
      points: [...]            # 1-3 short, action-first points + `warn` points
      photos: [...]            # the main photo
      more:                    # intro, callouts (info only), table, points,
        points: [...]          # photos, after: the why, beginner/expert notes,
        photos: [...]          # misreadings, long tables, extra photos

A string in `more:` has the same context as the step it belongs to, so
moving a sentence in or out of "More" keeps its translation. `validate()`
refuses a `warn` point or a warning callout inside `more:`.

`walk()` is the one place that knows which fields are translatable; it is
used both to extract (POT) and to translate (build). Strings with no letter
in them ("230 → 190", "0.2") are not extracted.
"""
import copy
import os
import re

import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # site/
CONTENT = os.path.join(HERE, "content")
LOCALES = os.path.join(HERE, "locales")
IMG = os.path.join(HERE, "img")
BUILD = os.path.join(HERE, "_build")

LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load():
    """Everything the build needs, in English."""
    site = _load(os.path.join(CONTENT, "site.yaml"))
    ui = _load(os.path.join(CONTENT, "ui.yaml"))
    langs = _load(os.path.join(HERE, "languages.yaml"))["languages"]
    pages = {}
    for name in sorted(os.listdir(os.path.join(CONTENT, "pages"))):
        if name.endswith(".yaml"):
            p = _load(os.path.join(CONTENT, "pages", name))
            if p["id"] + ".yaml" != name:
                raise SystemExit("content/pages/%s: id is %r, must match the file name"
                                 % (name, p["id"]))
            pages[p["id"]] = p
    features = {}
    fdir = os.path.join(CONTENT, "features")
    if os.path.isdir(fdir):
        for name in sorted(os.listdir(fdir)):
            if name.endswith(".yaml"):
                features[name[:-5]] = _load(os.path.join(fdir, name))
    src = {"site": site, "ui": ui, "languages": langs, "pages": pages,
           "features": features}
    validate(src)
    return src


# What a `more:` block (the collapsed "More" part of a step, a feature or a
# page intro) may hold. Warnings never go there: a reader who skips "More"
# must still see every warning, so `validate` refuses a `warn` point or a
# warning callout inside it.
MORE_KEYS = ("intro", "callouts", "table", "points", "photos", "after")


def validate(src):
    """Structural rules the build relies on; exits with a message naming the
    file and the step. Run by load(), so by every command."""
    def more(m, where):
        if not isinstance(m, dict):
            raise SystemExit("%s: `more:` must be a mapping (%s)" % (where, ", ".join(MORE_KEYS)))
        extra = set(m) - set(MORE_KEYS)
        if extra:
            raise SystemExit("%s: `more:` cannot hold %s (allowed: %s)"
                             % (where, ", ".join(sorted(extra)), ", ".join(MORE_KEYS)))
        for pt in m.get("points", []):
            if isinstance(pt, dict) and "warn" in pt:
                raise SystemExit("%s: a `warn` point cannot go inside `more:` (it would be hidden); "
                                 "keep it in the step's own points" % where)
        for box in m.get("callouts", []):
            if box.get("kind", "info") != "info":
                raise SystemExit("%s: a callout of kind %r cannot go inside `more:` (it would be "
                                 "hidden); keep it in the step's own callouts" % (where, box.get("kind")))

    def photos(lst, where):
        for ph in lst:
            if "aspect" in ph and not re.fullmatch(r"\s*\d+(\.\d+)?\s*/\s*\d+(\.\d+)?\s*", str(ph["aspect"])):
                raise SystemExit("%s, photo %s: aspect %r must look like \"4/3\"" % (where, ph.get("id"), ph["aspect"]))
            if "focus" in ph and not re.fullmatch(r"[\w%. -]+", str(ph["focus"])):
                raise SystemExit("%s, photo %s: focus %r must look like \"50%% 30%%\"" % (where, ph.get("id"), ph["focus"]))

    for pid, p in src["pages"].items():
        for st in p.get("steps", []):
            photos(st.get("photos", []) + st.get("more", {}).get("photos", []), "content/pages/%s.yaml" % pid)
    for fid, f in src["features"].items():
        for x in f.get("features", []):
            photos(x.get("photos", []) + x.get("more", {}).get("photos", []), "content/features/%s.yaml" % fid)
    for pid, p in src["pages"].items():
        if "sketch" in p:
            sk = p["sketch"]
            if not (isinstance(sk, str) and sk.endswith(".svg") and ".." not in sk.split("/")):
                raise SystemExit("content/pages/%s.yaml: `sketch:` %r must be an .svg path under img/, "
                                 "e.g. sketches/%s.svg" % (pid, sk, pid))
            if not os.path.isfile(os.path.join(IMG, sk)):
                raise SystemExit("content/pages/%s.yaml: `sketch:` img/%s does not exist "
                                 "(hexcalibr-core: python3 -I calib.py sketch)" % (pid, sk))
        if "more" in p:
            more(p["more"], "content/pages/%s.yaml (page)" % pid)
        for st in p.get("steps", []):
            if "more" in st:
                more(st["more"], "content/pages/%s.yaml, step %s" % (pid, st.get("id")))
    for fid, f in src["features"].items():
        for x in f.get("features", []):
            if "more" in x:
                more(x["more"], "content/features/%s.yaml, feature %s" % (fid, x.get("id")))


# Point kinds: a plain string is an ordinary point; a one-key mapping gives
# the kind. The label each kind shows is a UI string (ui.yaml: kind_<k>).
KINDS = ("warn", "beginner", "expert", "misread", "tip", "note")


def walk(src, fn):
    """A deep copy of `src` (the result of load()) with every translatable
    string replaced by fn(context, text, note). `note` becomes the `#.`
    comment that tells a translator what kind of text it is."""
    src = copy.deepcopy(src)

    def t(ctxt, text, note):
        if not isinstance(text, str) or not LETTER.search(text):
            return text
        return fn(ctxt, text, note)

    # the fixed words
    for k in list(src["ui"]):
        src["ui"][k] = t("ui/" + k, src["ui"][k], "interface: " + k)

    # site: tagline and contents
    s = src["site"]
    for k in ("tagline", "description"):
        if k in s:
            s[k] = t("site", s[k], "site " + k)
    for g in s["contents"]:
        g["group"] = t("site/contents", g["group"], "contents group heading")
        for e in g["entries"]:
            for k in ("planned", "note"):
                if k in e:
                    e[k] = t("site/contents", e[k], "contents: " + k)

    # pages
    for pid, p in src["pages"].items():
        for k in ("title", "nav_title", "description", "intro", "breadcrumb"):
            if k in p:
                p[k] = t(pid, p[k], "page " + k)
        if "more" in p:
            _more(p["more"], pid, t)
        for c in p.get("callouts", []):
            _callout(c, pid, t)
        need = p.get("need")
        if need:
            need["title"] = t(pid, need.get("title", ""), "box title")
            for col in need["columns"]:
                col["title"] = t(pid, col["title"], "box column title")
                col["items"] = [t(pid, x, "box item") for x in col["items"]]
        for st in p.get("steps", []):
            if "part" in st:
                st["part"] = t(pid, st["part"], "part heading (groups steps)")
                continue
            if "features" in st:
                continue
            c = "%s/%s" % (pid, st["id"])
            _step(st, c, t)

    # features of the scoring sheets
    for fid, f in src["features"].items():
        base = "features/" + fid
        for k in ("title", "intro", "rule_title"):
            if k in f:
                f[k] = t(base, f[k], "scorecard " + k)
        f["rules"] = [t(base + "/rules", x, "scoring rule") for x in f.get("rules", [])]
        for x in f["features"]:
            c = "%s/%s" % (base, x["id"])
            for k in ("name", "short", "what", "pass", "fail", "fail_hot", "fail_cold", "fail_low", "fail_high",
                      "pattern", "cause", "action", "vc4"):
                if k in x:
                    x[k] = t(c, x[k], "feature " + k)
            _points(x, c, t)
            _photos(x, c, t)
            if "more" in x:
                _more(x["more"], c, t)
    return src


def _callout(box, c, t, pre=""):
    """A boxed note: `kind` (warn / info), an optional `title`, a `text`
    and optional `items` (a short list)."""
    for k in ("title", "text"):
        if k in box:
            box[k] = t(c, box[k], pre + ("callout " + k if k == "title" else "callout"))
    if "items" in box:
        box["items"] = [t(c, x, pre + "callout item") for x in box["items"]]


def _step(st, c, t):
    for k in ("title", "intro", "after"):
        if k in st:
            st[k] = t(c, st[k], "step " + k)
    _body(st, c, t, "")
    if "more" in st:
        _more(st["more"], c, t)


def _more(m, c, t):
    """The collapsed part. Same context as the step it belongs to, so moving
    a sentence between the essentials and "More" keeps its translation."""
    for k in ("intro", "after"):
        if k in m:
            m[k] = t(c, m[k], "More: " + k)
    _body(m, c, t, "More: ")


def _body(st, c, t, pre):
    for box in st.get("callouts", []):
        _callout(box, c, t, pre)
    _points(st, c, t, pre)
    _photos(st, c, t, pre)
    tab = st.get("table")
    if tab:
        tab["head"] = [t(c, h, pre + "table header") for h in tab["head"]]
        tab["rows"] = [[t(c, cell, pre + "table cell") for cell in row] for row in tab["rows"]]


def _points(st, c, t, pre=""):
    out = []
    for pt in st.get("points", []):
        if isinstance(pt, str):
            out.append(t(c, pt, pre + "point"))
        else:
            (kind, text), = pt.items()
            if kind not in KINDS:
                raise SystemExit("%s: unknown point kind %r (use %s)" % (c, kind, KINDS))
            out.append({kind: t(c, text, pre + "point (%s)" % kind)})
    if "points" in st:
        st["points"] = out


def _photos(st, c, t, pre=""):
    for ph in st.get("photos", []):
        # `shot` is the brief for the photographer: English only, not shown
        # to readers in production, so it is not translated
        for k in ("alt", "caption"):
            if k in ph:
                ph[k] = t(c, ph[k], pre + "photo " + k)
        # a stand-in photo: alt and caption are shown, `redo` is for the owner
        for k in ("alt", "caption"):
            if k in ph.get("stand_in", {}):
                ph["stand_in"][k] = t(c, ph["stand_in"][k], pre + "stand-in photo " + k)


def strings(src):
    """[(context, English, note)] in source order, duplicates removed."""
    seen, out = set(), []

    def fn(ctxt, text, note):
        if (ctxt, text) not in seen:
            seen.add((ctxt, text))
            out.append((ctxt, text, note))
        return text
    walk(src, fn)
    return out


def all_photos(src):
    """[(page or feature set, step/feature title, photo)] in reading order."""
    out = []
    for pid, p in src["pages"].items():
        for st in p.get("steps", []):
            if "features" in st:
                for x in src["features"][st["features"]]["features"]:
                    for ph in x.get("photos", []) + x.get("more", {}).get("photos", []):
                        out.append((pid, x["name"], ph))
            for ph in st.get("photos", []) + st.get("more", {}).get("photos", []):
                out.append((pid, st.get("title", ""), ph))
    return out
