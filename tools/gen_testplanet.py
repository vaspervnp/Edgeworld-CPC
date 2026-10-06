#!/usr/bin/env python3
"""Generate the test planet strip used by the scroll engine milestones.

A 1024x136 Mode 0 image (256 x 17 tiles) that wraps seamlessly: starfield,
a mountain range, ground, four shield generators and column markers on the
bottom row (a block at column 0, a tick every 8 columns) so scrolling and
wrap-around can be checked by eye.

The sky is a single pen (1); raster interrupts recolour it in bands.
Crystal spires stand in the foreground: the second image marks their
pixels (1 = foreground), and sprites pass behind them.

Usage: gen_testplanet.py out.png fg_mask.png
"""
import math
import random
import sys
from PIL import Image

from cpcpal import COLOURS

W, H = 1024, 136
COLS = W // 4

PENS = ["black", "black", "sky_blue", "mauve", "bright_white", "red", "orange",
        "bright_yellow", "yellow", "white", "pastel_blue", "green",
        "bright_green", "bright_red", "cyan", "magenta"]
BLACK, SKY, STAR2, MAUVE, WHITE, RED, ORANGE, BYELLOW, YELLOW, GREY, \
    PBLUE, GREEN, BGREEN, BRED, CYAN, MAGENTA = range(16)

GROUND = 96               # first ground line (tile row 12)
GENERATOR_COLS = (32, 96, 160, 224)
SPIRE_COLS = (12, 52, 75, 118, 141, 190, 236)


def mountain_heights():
    """Height above GROUND at each column boundary, multiples of 8, |slope| <= 8."""
    def target(c):
        t = 2 * math.pi * c / COLS
        v = 32 + 14 * math.sin(t * 3 + 0.5) + 9 * math.sin(t * 7 + 1.3) + 5 * math.sin(t * 13)
        return max(8, min(56, int(round(v / 8)) * 8))
    h = [target(0)]
    for c in range(1, COLS + 1):
        h.append(h[-1] + max(-8, min(8, target(c) - h[-1])))
    assert h[COLS] == h[0], "mountain profile does not wrap"
    return h


def main(out, fg_out):
    rnd = random.Random(1988)
    img = Image.new("P", (W, H), SKY)
    pal = []
    for name in PENS:
        pal += COLOURS[name][1]
    img.putpalette(pal + [0] * (768 - len(pal)))
    px = img.load()

    def rect(x0, y0, x1, y1, pen):
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[x % W, y] = pen

    # Stars: at most one per tile, from a few fixed spots, so tiles repeat.
    spots = [(1, 2), (3, 5), (0, 6), (2, 1)]
    for c in range(COLS):
        for row in range(9):
            if rnd.random() < 0.18 - row * 0.015:
                sx, sy = rnd.choice(spots)
                px[c * 4 + sx, row * 8 + sy] = WHITE if rnd.random() < 0.7 else STAR2

    # Mountains: slopes of 2 lines per pixel, breakpoints on tile corners.
    h = mountain_heights()
    for c in range(COLS):
        for i in range(4):
            top = GROUND - (h[c] + (h[c + 1] - h[c]) * (2 * i + 1) // 8)
            rect(c * 4 + i, top, c * 4 + i + 1, GROUND, MAUVE)

    # Ground: an orange crust, red soil with a few pebble tiles, dark bedrock.
    rect(0, GROUND, W, H, RED)
    rect(0, GROUND, W, GROUND + 2, ORANGE)
    pebbles = [[(1, 3)], [(0, 5), (2, 2)], [(3, 6)], [(2, 4), (1, 7)]]
    for c in range(COLS):
        for row in range(13, 16):
            if rnd.random() < 0.3:
                for (dx, dy) in rnd.choice(pebbles):
                    px[c * 4 + dx, row * 8 + dy] = YELLOW
    rect(0, 128, W, H, BLACK)

    # Boulders on the crust.
    for c in range(4, COLS, 23):
        rect(c * 4 + 1, GROUND - 6, c * 4 + 7, GROUND, GREY)
        rect(c * 4 + 2, GROUND - 8, c * 4 + 6, GROUND - 6, GREY)
        rect(c * 4 + 2, GROUND - 6, c * 4 + 4, GROUND - 3, PBLUE)

    # Shield generators: platform, shaft with a glowing core, domed cap.
    for gc in GENERATOR_COLS:
        x = gc * 4
        rect(x, 80, x + 12, GROUND, GREY)             # platform rows 10-11
        rect(x, 80, x + 12, 82, PBLUE)
        rect(x + 4, 48, x + 8, 80, GREY)              # shaft rows 6-9
        rect(x + 5, 52, x + 7, 76, BGREEN)
        rect(x, 40, x + 12, 48, GREEN)                # cap row 5
        rect(x + 2, 40, x + 10, 42, BGREEN)
        rect(x + 5, 40, x + 7, 41, WHITE)

    # Foreground crystal spires: 12 pixels wide, 44 lines tall, on the crust.
    fg_img = Image.new("P", (W, H), 0)
    fg_img.putpalette([0, 0, 0, 255, 255, 255] + [0] * 762)
    fg = fg_img.load()
    for sc in SPIRE_COLS:
        x0 = sc * 4
        for i in range(44):
            y = GROUND + 4 - 44 + i
            half = 1 + i * 5 // 43          # 1..6 pixels each side of the centre
            for x in range(x0 + 6 - half, x0 + 6 + half):
                pen = CYAN if x < x0 + 6 else PBLUE
                if x == x0 + 6 - half or (i < 3):
                    pen = WHITE
                px[x, y] = pen
                fg[x, y] = 1
    fg_img.save(fg_out)

    # Column markers on the bottom row.
    for c in range(0, COLS, 8):
        rect(c * 4, 130, c * 4 + 2, 135, BRED)
    rect(0, 128, 8, 136, BYELLOW)

    # Every pen but the sky on the last line, so a HUD palette switch that
    # comes too early shows (tests/test_screen.py).
    for x in range(8, W):
        px[x, H - 1] = [p for p in range(16) if p != SKY][x % 15]

    img.save(out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
