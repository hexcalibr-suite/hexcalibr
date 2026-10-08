"""HexCalibr logo kit: a sword piercing a stack of hexagonal layers ordered like the
temperature tower (cold on top, hot at the bottom), with the "HexCalibr" wordmark in Sora.

    python3 -I brand/make_logo.py                 # icon, favicon (stdlib only)
    PYTHONPATH=<fonttools> python3 brand/make_logo.py --sora Sora[wght].ttf
                                                  # also the wordmark, text converted to paths

Writes the SVGs into icon/, wordmark/ and favicon/ next to this script. The PNGs (icon sizes,
word mark, social card, avatar) are rendered from them by render_png.sh (headless Chrome).
"""
import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))
AMBER, INK, PAPER, STEEL, SLOT = "#efa00b", "#16191d", "#f7f6f3", "#d3d8df", "#000"
COLD, WARM, HOT = ("#3a6fa8", "#24578f"), ("#efa00b", "#c98500"), ("#c4553b", "#a3361f")
LAYERS = [COLD, WARM, HOT]  # top -> bottom, like the temperature tower

# geometry (viewBox units)
W, H, T, GAP, TOP_Y = 23, 6, 4.5, 10.5, 30      # hexagon half-width, face half-height, thickness, pitch
BLADE, GRIP, RAISE = 7.5, 12.5, 3.0             # blade width, grip length, sword raised above the stack


def hexface(cx, cy, w, h):
    return [(cx - w, cy), (cx - w / 2, cy - h), (cx + w / 2, cy - h), (cx + w, cy), (cx + w / 2, cy + h), (cx - w / 2, cy + h)]


def pts(p):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in p)


def layer(cx, cy, top, side, w=W, h=H, t=T):
    f = hexface(cx, cy, w, h)
    skirt = [f[0], f[5], f[4], f[3], (f[3][0], f[3][1] + t), (f[4][0], f[4][1] + t), (f[5][0], f[5][1] + t), (f[0][0], f[0][1] + t)]
    return f'<polygon points="{pts(skirt)}" fill="{side}"/><polygon points="{pts(f)}" fill="{top}"/>'


def sword(cx, tip_y, top, hilt, edge):
    bw = BLADE / 2
    return "".join([
        f'<polygon points="{cx-bw},{top+5+GRIP} {cx+bw},{top+5+GRIP} {cx+bw},{tip_y-BLADE*1.6} {cx},{tip_y} {cx-bw},{tip_y-BLADE*1.6}" '
        f'fill="{STEEL}" stroke="{edge}" stroke-width="0.9" stroke-linejoin="round"/>',
        f'<line x1="{cx}" y1="{top+6+GRIP}" x2="{cx}" y2="{tip_y-BLADE*1.8}" stroke="#9aa3ad" stroke-width="0.8"/>',
        f'<rect x="{cx-12}" y="{top+2+GRIP}" width="24" height="4" rx="2" fill="{hilt}"/>',
        f'<rect x="{cx-2.2}" y="{top+2.5}" width="4.4" height="{GRIP}" rx="1" fill="{hilt}"/>',
        f'<polygon points="{pts(hexface(cx, top+1.8, 3.4, 2.9))}" fill="{AMBER}" stroke="{hilt}" stroke-width="0.8"/>',
    ])


def icon_parts(dark, prefix="hc"):
    """(defs, body, (x0, y0, w, h)) of the icon. Bottom-up: each layer, then the part of the
    sword between its face and the next face up (clipped); the next layer hides what is behind it."""
    hilt = PAPER if dark else INK
    edge = "#0b0d10" if dark else INK
    cx = 32
    ys = [TOP_Y + i * GAP for i in range(3)]
    tip_y = ys[-1] + H + T + 8
    top = 3 - RAISE
    sw = sword(cx, tip_y, top, hilt, edge)
    bands = [(-100, ys[0]), (ys[0], ys[1]), (ys[1], ys[2]), (ys[2], 200)]
    defs = "".join(f'<clipPath id="{prefix}{k}"><rect x="-50" y="{a}" width="200" height="{b-a}"/></clipPath>'
                   for k, (a, b) in enumerate(bands))
    body = [f'<g clip-path="url(#{prefix}3)">{sw}</g>']
    for i in (2, 1, 0):
        top_c, side_c = LAYERS[i]
        body.append(layer(cx, ys[i], top_c, side_c))
        body.append(f'<ellipse cx="{cx}" cy="{ys[i]}" rx="{BLADE/2+1.2}" ry="1.4" fill="{SLOT}" opacity="0.32"/>')
        body.append(f'<g clip-path="url(#{prefix}{i})">{sw}</g>')
    return defs, "".join(body), (8, top - 2.0, 48, tip_y + 1.5 - (top - 2.0))   # the hex pommel reaches top - 1.1 (+ stroke)


def icon_svg(dark):
    defs, body, (x, y, w, h) = icon_parts(dark)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y:.2f} {w} {h:.2f}">'
            f'<title>HexCalibr</title><defs>{defs}</defs>{body}</svg>\n')


def favicon_svg():
    """The layer stack alone: the sword disappears at 16-32 px."""
    out = []
    for i, (top_c, side_c) in reversed(list(enumerate(LAYERS))):
        out.append(layer(16, 9.5 + i * 7.2, top_c, side_c, w=14.5, h=4.2, t=3.6))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">{"".join(out)}</svg>\n'


def text_path(font_path, text, wght, size, x0, baseline):
    """SVG path data of `text` in the variable font at weight `wght` (no kerning)."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    font = instancer.instantiateVariableFont(TTFont(font_path), {"wght": wght})
    gs, cmap, upm = font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm
    k = size / upm
    d, x = [], x0
    for ch in text:
        g = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        gs[g].draw(TransformPen(pen, (k, 0, 0, -k, x, baseline)))
        d.append(pen.getCommands())
        x += gs[g].width * k
    return " ".join(d), x


def text_bounds(font_path, text, wght, size):
    """(yMin, yMax) in font-up units scaled to `size`: real ink extent, including the overshoot
    of round letters (C) and ascenders above the cap height."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    from fontTools.pens.boundsPen import BoundsPen
    font = instancer.instantiateVariableFont(TTFont(font_path), {"wght": wght})
    gs, cmap, upm = font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm
    lo, hi = 0.0, 0.0
    for ch in text:
        pen = BoundsPen(gs)
        gs[cmap[ord(ch)]].draw(pen)
        if pen.bounds:
            lo, hi = min(lo, pen.bounds[1]), max(hi, pen.bounds[3])
    return lo * size / upm, hi * size / upm


def wordmark_svg(font_path, dark, tagline="3D print calibration suite"):
    from fontTools.ttLib import TTFont
    ink = PAPER if dark else INK
    sub = "#a8adb3" if dark else "#555b62"
    defs, body, (ix, iy, iw, ih) = icon_parts(dark, prefix="wm")
    s = 100 / ih                                  # icon 100 units tall
    hex_d, x1 = text_path(font_path, "Hex", 700, 64, 0, 0)
    cal_d, x2 = text_path(font_path, "Calibr", 400, 64, x1, 0)
    tag_d, x3 = text_path(font_path, tagline, 400, 20.5, 2, 0)
    font = TTFont(font_path)
    cap = font["OS/2"].sCapHeight * 64 / font["head"].unitsPerEm
    # layout: the top of the cross-guard lines up with the cap height of "HexCalibr"
    # (the pommel and grip rise above the word)
    guard_top = (3 - RAISE) + 2 + GRIP           # icon units (see sword())
    oy = 0.0                                     # icon placed at y = oy .. oy + 100
    base = oy + (guard_top - iy) * s + cap       # text baseline
    _, ink_hi = text_bounds(font_path, "HexCalibr", 700, 64)
    _, ink_lo_tag = text_bounds(font_path, tagline, 400, 20.5)
    tag_base = base + 28
    tag_lo, _ = text_bounds(font_path, tagline, 400, 20.5)
    top = min(oy, base - ink_hi) - 2             # never clip the C's overshoot or the ascenders
    bottom = max(oy + 100, tag_base - tag_lo) + 2
    tx = iw * s + 22
    width = tx + max(x2, x3) + 6
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {top:.2f} {width:.1f} {bottom - top:.2f}">'
            f'<title>HexCalibr: 3D print calibration suite</title><defs>{defs}</defs>'
            f'<g transform="translate({-ix*s:.2f} {oy - iy*s:.2f}) scale({s:.4f})">{body}</g>'
            f'<g fill="{ink}" transform="translate({tx:.2f} {base:.2f})"><path d="{hex_d}"/><path d="{cal_d}"/></g>'
            f'<g fill="{sub}" transform="translate({tx:.2f} {tag_base:.2f})"><path d="{tag_d}"/></g></svg>\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sora", help="Sora variable font (OFL) to outline the wordmark; needs fontTools")
    a = ap.parse_args()
    files = {"icon/icon.svg": icon_svg(False), "icon/icon-dark.svg": icon_svg(True),
             "favicon/favicon.svg": favicon_svg()}
    if a.sora:
        files["wordmark/wordmark.svg"] = wordmark_svg(a.sora, False)
        files["wordmark/wordmark-dark.svg"] = wordmark_svg(a.sora, True)
    for name, svg in files.items():
        path = os.path.join(HERE, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", name)


if __name__ == "__main__":
    main()
