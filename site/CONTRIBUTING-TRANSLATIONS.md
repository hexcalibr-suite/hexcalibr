<!-- SPDX-FileCopyrightText: 2026 Matteo Beretta
     SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Translating the HexCalibr guides

Thank you for helping! The guides are written in English. Italian is
maintained by the author. Every other language comes from contributors like
you.

You can translate in two ways:

- **A. On Weblate**, in the browser, with no git. This is the easiest way.
- **B. Manually, with a pull request.** Use it if you prefer Poedit or a text editor.

Both end up in the same files: `site/locales/<language>.po`.

## How the translation files work (read this once)

- The English text lives in `site/content/` (YAML). **Do not translate those files.**
- `site/locales/messages.pot` is the template. The build regenerates it from the
  English, so never edit it by hand.
- Each language is one gettext file, `site/locales/<code>.po`, for example
  `de.po` or `pt_BR.po`. Each entry has:
  - `msgctxt`: where the text is (`temperature-tower/check` = the "check" step of
    the temperature tower guide);
  - `msgid`: the English text;
  - `msgstr`: your translation.
- When the English changes, your old translation is kept but marked **fuzzy**,
  and the old English is shown next to it (`#| msgid`). The site shows the
  **English** for fuzzy or empty entries until someone reviews them. A
  half-finished language therefore never shows outdated text.

### Why PO files, and not translated Markdown

- Weblate's gettext support is mature. Its Markdown support is still marked
  "under development".
- PO gives you translation memory, fuzzy matching and per-sentence review.
- When one English sentence changes, only that sentence needs work, not a whole page.
- You never touch the page layout, so a translation cannot break the HTML.

## What to keep exactly as it is

`python3 -m sitegen check` verifies these, and a pull request that fails the
check cannot be merged:

| In the English | Keep it… |
|---|---|
| `{suite}`, `{author}` | exactly as written. They are filled in automatically (the project name, the author). |
| `{{TBD: …}}` | exactly as written, if one appears. It marks a fact that is not final yet; the public site does not show it. |
| `` `code` `` | unchanged and untranslated: G-code (`M104`), setting keys (`first_layer_temperature`), file names. |
| `[text](target)` | Translate the *text*. Keep the *target* (`page:…`, `link:…`, URLs) unchanged. |
| `**bold**` | Keep the same **number** of bold parts. They mark menu paths and key words. |
| `%s`, `%d` (interface strings) | Keep the same placeholders in the same order. |

Style guidelines:

- **PrusaSlicer menu and setting names:** use the name PrusaSlicer itself shows
  in your language, if PrusaSlicer is translated into it. Otherwise keep the
  English name. Readers must find the words on their screen.
- **Units:** keep °C and mm. Use your language's decimal separator in prose
  (0,4 mm in Italian), but never inside `` `code` ``.
- **Tone:** short sentences, second person ("you"), the same level of detail as
  the English. Do not add or drop safety warnings.
- **Photos have no words in them**, so you never need to edit images. Translate
  the `alt` and `caption` texts in the PO file.
- Shot briefs for the photographer (`shot:` in the YAML) are not translated.

## A. Translate on Weblate (planned)

Weblate is not set up yet: until it is, use **B** below. Once it is:

1. Open the HexCalibr project on Weblate (the link will be added here).
2. Sign in (GitHub login works) and pick your language. If your language is
   missing, click **Start new translation**.
3. Translate, or review suggestions. Weblate shows the context (`msgctxt`) and
   the note under each string. Its checks flag missing placeholders.
4. Weblate commits to its own copy of the repository and opens or updates a
   pull request on GitHub. The maintainer reviews and merges it.
5. **DCO sign-off:** by contributing through Weblate you agree to the Developer
   Certificate of Origin (below). Weblate adds a `Signed-off-by:` line with
   your name and e-mail to its commits (the maintainer enables this in the Weblate component settings).

For the maintainer, the Weblate component settings are:

- **File format:** gettext PO
- **File mask:** `site/locales/*.po`
- **Template for new translations:** `site/locales/messages.pot`
- **Language filter:** exclude `en`
- **Add-ons:** "Update PO files to match POT (msgmerge)". This is optional:
  `python3 -m sitegen update` does the same merge without needing gettext
  installed.

## B. Translate manually and open a pull request

You need Python 3.8+ and PyYAML (`pip install -r site/requirements.txt`).
Poedit (free) or any text editor works for the `.po` file.

1. Fork the repository and clone your fork.
2. Start your language (skip this step if the `.po` already exists):

   ```sh
   cd site
   python3 -m sitegen init de          # creates locales/de.po from the template
   ```

3. Add it to `site/languages.yaml` **disabled** for now:

   ```yaml
     de:
       name: Deutsch
       enabled: false
       translators: ["Your Name"]
   ```

4. Translate `locales/de.po` in Poedit or an editor. Fill in `msgstr` only.
   Never change `msgctxt` or `msgid`. Put your name in the header's
   `Last-Translator`.
5. If the English changed while you worked, run `python3 -m sitegen update de`.
   It merges the new strings and marks changed ones fuzzy. Review the fuzzy
   ones and remove the `#, fuzzy` line when your translation is correct again.
6. Check and preview your work:

   ```sh
   python3 -m sitegen check de         # must say: check: OK
   python3 -m sitegen stats            # how complete each language is
   # set enabled: true locally to see it, then:
   python3 -m sitegen build
   python3 -m http.server -d _build 8000    # open http://localhost:8000/de/
   ```

7. Commit **with a sign-off** and push:

   ```sh
   git add site/locales/de.po site/languages.yaml
   git commit -s -m "Add German translation (start pages)"
   git push
   ```

8. Open a pull request. You can submit a partial translation: untranslated
   strings simply show in English.

### When a language goes live

The maintainer switches `enabled: true` once these pages are **100% translated
and reviewed**: the overview, *Before you start*, *License and credits*, the
interface strings, and at least one complete test guide with its scorecard.
Until then the language is kept in the repository but is not published.
Translators are credited on the *License and credits* page, from the
`translators` list in `languages.yaml`.

## Developer Certificate of Origin (DCO)

All contributions, translations included, must be signed off. A sign-off is a
line at the end of the commit message:

```
Signed-off-by: Your Name <you@example.com>
```

`git commit -s` adds it for you. Use your real name, or a name you are
publicly known by, and an e-mail you can be reached at.

By signing off you certify the
[Developer Certificate of Origin 1.1](https://developercertificate.org/):
that you wrote the contribution or have the right to submit it under the
project's license. For translations, that license is **CC BY-SA 4.0**, the
same as the English guides. Do not paste text from other guides, manuals or
machine-translation services whose terms do not allow it. Machine translation
as a first draft is fine, as long as you review every sentence yourself.

Forgot the sign-off? Run `git commit --amend -s` for the last commit, or
`git rebase --signoff main` for several commits, then force-push your branch.

## Questions

Open an issue in the repository: https://github.com/hexcalibr-suite/hexcalibr/issues
