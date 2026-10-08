<p><img src="brand/wordmark/wordmark.svg" alt="HexCalibr — 3D print calibration suite" width="420"></p>

# HexCalibr — 3D print calibration suite

Hexagon-based calibration tests for **PrusaSlicer**, each with a step-by-step guide that helps you
print it, read it and apply the result. Klipper, Marlin, Prusa and RepRapFirmware printers,
single-tool and IDEX.

- **Guides:** https://hexcalibr.ui4.eu (English, Italian; more languages welcome)
- **Download the tests:** only from the official HexCalibr pages on **Printables**; each guide links to
  its page. The files change often: please link to Printables rather than re-uploading them.

| Test | Guide |
|---|---|
| Temperature tower | [EN](https://hexcalibr.ui4.eu/temperature-tower.html) · [IT](https://hexcalibr.ui4.eu/it/temperature-tower.html) |
| Pressure advance | [EN](https://hexcalibr.ui4.eu/pressure-advance.html) · [IT](https://hexcalibr.ui4.eu/it/pressure-advance.html) |
| Maximum volumetric flow | [EN](https://hexcalibr.ui4.eu/max-flow.html) · [IT](https://hexcalibr.ui4.eu/it/max-flow.html) |
| IDEX / multi-tool alignment (Lite and Vernier, with an interactive card) | [EN](https://hexcalibr.ui4.eu/idex-alignment.html) · [IT](https://hexcalibr.ui4.eu/it/idex-alignment.html) |

Coming next: first layer and Z offset, flow (extrusion multiplier), retraction, dimensions and fit.

## What is in this repository

The source of the guide site: texts (`site/content/`), translations (`site/locales/`), photos and
clips (`site/img/`), the brand kit (`brand/`) and the small generator that builds the site
(`site/sitegen/`). The test files themselves are published only on Printables.

```sh
pip install -r site/requirements.txt
cd site && python3 -m sitegen build && python3 -m http.server -d _build 8000
```

## Translate HexCalibr

Translations are very welcome: see [site/CONTRIBUTING-TRANSLATIONS.md](site/CONTRIBUTING-TRANSLATIONS.md).
Contributions are accepted with a DCO sign-off (`git commit -s`).

## Licenses

- **Guides, texts, photos, videos and translations** (`site/content/`, `site/img/`, `site/locales/`):
  [CC BY-SA 4.0](LICENSES/CC-BY-SA-4.0.txt). Attribution: "HexCalibr by Matteo Beretta", with a link
  to https://hexcalibr.ui4.eu.
- **Site generator** (`site/sitegen/`, `site/tools/`, `brand/make_logo.py`, `brand/render_png.sh`):
  [GPL-3.0-or-later](LICENSES/GPL-3.0-or-later.txt).
- The **HexCalibr** name and logo (`brand/`) are not covered by these licenses: please use a different
  name and logo for modified versions.

Not affiliated with Prusa Research, Bambu Lab, Rat Rig or OrcaSlicer. Product names are used only to
describe compatibility.
