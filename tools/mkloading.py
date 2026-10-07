#!/usr/bin/env python3
"""Make the loading screen: a Mode 0 picture (160x200, 16 inks out of the
CPC's 27 colours) from a render (assets/loading_render.png, rendered in
Blender from assets/loading_scene.blend), with the title logo over the top.

Colours are compared in CIE Lab, as the eye sees them. The logo's colours,
and black, are inks from the start; the other nine are chosen from the 27,
one at a time, each the one that brings the picture closest, then swapped
for others while that brings it closer still. The picture is then dithered
into the 16 inks: ordered (a 4x4 Bayer matrix: each pixel takes the nearer
of the two inks its colour lies between, by the threshold), which keeps
flat areas calm, the way CPC pictures were drawn; or, with --diffuse,
Floyd-Steinberg error diffusion. The logo gets a black outline.

Writes the screen as the 16K of screen memory at &C000 (line y at
(y % 8) * &800 + (y / 8) * 80), the inks as firmware colour numbers, one
line of 16 (for SHIELD.BAS's INK commands), and a preview PNG at the
proportions a monitor shows.

Usage: mkloading.py [--diffuse] render.png logo.png out.bin out.inks preview.png
"""
import sys
from PIL import Image, ImageEnhance

from cpcpal import COLOURS, mode0_byte
import pens

W, H = 160, 200
LOGO_X, LOGO_Y = 8, 4           # Mode 0 pixels
SATURATION, CONTRAST, BRIGHTNESS = 1.7, 1.25, 1.0
NAMES = list(COLOURS)           # in firmware order: INK numbers
RGB = [COLOURS[n][1] for n in NAMES]
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def lab(rgb):
    """CIE Lab of an sRGB colour (0-255)."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.9505
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.089

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return (116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z)))


LAB = [lab(c) for c in RGB]


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def choose_inks(pixels, fixed, count=16):
    """Firmware numbers of the inks: fixed ones, then the best others."""
    sample = [lab(p) for p in pixels[::5]]
    dists = [[dist(p, LAB[c]) for c in range(len(RGB))] for p in sample]

    def error(inks):
        return sum(min(d[i] for i in inks) for d in dists)
    inks = list(fixed)
    while len(inks) < count:
        inks.append(min((c for c in range(len(RGB)) if c not in inks),
                        key=lambda c: error(inks + [c])))
    better = True
    while better:                   # swap while it helps
        better = False
        for k in range(len(fixed), count):
            for c in range(len(RGB)):
                if c in inks:
                    continue
                trial = inks[:k] + [c] + inks[k + 1:]
                if error(trial) < error(inks):
                    inks, better = trial, True
    return inks


def ordered(img, inks):
    """Pens of a W x H picture, ordered-dithered into the inks: each pixel
    takes one of the two inks nearest its colour, the one on the line
    between them its colour lies along, against the Bayer threshold."""
    pal = [LAB[i] for i in inks]
    out = [[0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            p = lab(img.getpixel((x, y)))
            order = sorted(range(len(pal)), key=lambda i: dist(p, pal[i]))
            a, b = order[0], order[1]
            ab = [v - u for u, v in zip(pal[a], pal[b])]
            n2 = sum(v * v for v in ab) or 1
            t = sum((q - u) * v for q, u, v in zip(p, pal[a], ab)) / n2    # 0 at a, 1 at b
            out[y][x] = b if t > (BAYER[y % 4][x % 4] + 0.5) / 16 else a
    return out


def dither(img, inks):
    """Pens (0-15) of a W x H picture, error-diffused into the inks."""
    pal = [RGB[i] for i in inks]
    px = [[list(img.getpixel((x, y))) for x in range(W)] for y in range(H)]
    out = [[0] * W for _ in range(H)]
    for y in range(H):
        xs = range(W) if y % 2 == 0 else range(W - 1, -1, -1)
        step = 1 if y % 2 == 0 else -1
        for x in xs:
            old = [min(255, max(0, v)) for v in px[y][x]]
            ol = lab(old)
            pen = min(range(len(pal)), key=lambda i: dist(ol, LAB[inks[i]]))
            out[y][x] = pen
            err = [o - n for o, n in zip(old, pal[pen])]
            for dx, dy, f in ((step, 0, 7), (-step, 1, 3), (0, 1, 5), (step, 1, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and ny < H:
                    p = px[ny][nx]
                    for k in range(3):
                        p[k] += err[k] * f * 0.85 / 16      # a little less: calmer
    return out


def main(render, logo, out_bin, out_inks, preview, diffuse=False):
    src = Image.open(render).convert("RGB")
    # the picture: 2:1 pixels, so squeeze the width twice as much
    img = src.resize((W, H), Image.LANCZOS)
    # towards the CPC's strong colours: hand-drawn CPC pictures sit on them
    img = ImageEnhance.Color(img).enhance(SATURATION)
    img = ImageEnhance.Contrast(img).enhance(CONTRAST)
    img = ImageEnhance.Brightness(img).enhance(BRIGHTNESS)
    logo_img = Image.open(logo)
    lpx = logo_img.load()
    logo_names = sorted({pens.FIXED[lpx[x, y]] for x in range(logo_img.width)
                         for y in range(logo_img.height) if lpx[x, y]})
    fixed = [NAMES.index("black")] + [NAMES.index(n) for n in logo_names]
    pixels = [img.getpixel((x, y)) for y in range(H) for x in range(W)]
    inks = choose_inks(pixels, fixed)
    pen_rows = dither(img, inks) if diffuse else ordered(img, inks)
    # the logo over the top, in its own colours, outlined in black
    black = inks.index(NAMES.index("black"))
    for y in range(-1, logo_img.height + 1):
        for x in range(-1, logo_img.width + 1):
            near = [(x + dx, y + dy) for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))]
            if any(0 <= u < logo_img.width and 0 <= v < logo_img.height and lpx[u, v] for u, v in near):
                pen_rows[LOGO_Y + y][LOGO_X + x] = black
    for y in range(logo_img.height):
        for x in range(logo_img.width):
            if lpx[x, y]:
                pen_rows[LOGO_Y + y][LOGO_X + x] = inks.index(NAMES.index(pens.FIXED[lpx[x, y]]))
    # screen memory
    scr = bytearray(16384)
    for y in range(H):
        base = (y % 8) * 0x800 + (y // 8) * 80
        for xb in range(W // 2):
            scr[base + xb] = mode0_byte(pen_rows[y][2 * xb], pen_rows[y][2 * xb + 1])
    open(out_bin, "wb").write(scr)
    open(out_inks, "w").write(",".join(str(i) for i in inks) + "\n")
    # preview: 4x2.4 per pixel, about as a monitor shows it
    pv = Image.new("RGB", (W, H))
    pv.putdata([RGB[inks[p]] for row in pen_rows for p in row])
    pv.resize((W * 4, int(H * 2.4)), Image.NEAREST).save(preview)
    print(f"{out_bin}: inks {', '.join(NAMES[i] for i in inks)}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--diffuse"]
    if len(args) != 5:
        raise SystemExit(__doc__)
    main(*args, diffuse="--diffuse" in sys.argv)
