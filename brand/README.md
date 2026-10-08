# HexCalibr brand kit

The approved logo is a sword piercing a stack of hexagonal layers, ordered like the temperature
tower (cold blue on top, amber, hot red at the bottom). Beside it is the word mark **Hex**Calibr in Sora,
with the claim "3D print calibration suite". In the word mark the cross-guard sits level with the cap
height and the pommel rises above the word.

## Files

| Folder | File | Use |
|---|---|---|
| `icon/` | `icon.svg`, `icon-dark.svg` | The logo alone, for light and for dark backgrounds |
| | `icon-{64,256,512}.png`, `icon-dark-{64,256,512}.png` | Raster versions with a transparent background |
| `wordmark/` | `wordmark.svg`, `wordmark-dark.svg` | Logo, name and claim. The text is converted to paths, so no font is needed |
| | `wordmark-1200.png`, `wordmark-dark-1200.png` | Raster versions, 1200 px wide, transparent background |
| `favicon/` | `favicon.svg` | The layer stack alone: below 32 px the sword can't be read |
| `social/` | `og-image.png` | 1200×630 card for link previews (site, Printables, forums, chats) |
| | `avatar-github.png` | 512 px avatar for the GitHub organisation, with margin for round crops |

The guide site copies `favicon/favicon.svg`, `icon/icon.svg` (as `logo.svg`), `icon/icon-dark.svg`
(as `logo-dark.svg`), `icon/icon-256.png` and `social/og-image.png` at build time.

## Colours

| Name | Top / side |
|---|---|
| Cold (blue) | `#3a6fa8` / `#24578f` |
| Warm (amber) | `#efa00b` / `#c98500` |
| Hot (red) | `#c4553b` / `#a3361f` |
| Ink | `#16191d` |
| Paper | `#f7f6f3` |

## Regenerate

```sh
# SVGs; the word mark needs fontTools and the Sora font (SIL Open Font License)
PYTHONPATH=<fonttools> python3 brand/make_logo.py --sora Sora[wght].ttf
# PNGs (headless Chrome)
brand/render_png.sh
```

Sora is available at https://github.com/google/fonts/tree/main/ofl/sora.

## Usage

- Keep the proportions: don't stretch the logo, recolour it or put it on busy backgrounds.
- Use the `-dark` files on dark backgrounds.
- **The HexCalibr name and logo are not covered by the project's CC BY-SA / GPL licenses.** They
  identify the official project: please do not use them for modified versions or re-uploads.
  `make_logo.py` and `render_png.sh` are GPL-3.0-or-later like the rest of the code.

The early concepts (A–F) were dropped.
