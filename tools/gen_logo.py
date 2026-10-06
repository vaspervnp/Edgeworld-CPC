#!/usr/bin/env python3
"""Generate the title logo: SHIELDRUNNER in big letters, a shadow, and a
line of small text under it, in the fixed pens of the playfield (tools/pens.py);
pen 0 is transparent.

Writes the image, and the raw Mode 0 bytes (LOGO_W bytes a line, LOGO_H lines)
that src/logo.asm draws over the title's sky.

Usage: gen_logo.py out.png out.bin
"""
import sys
from PIL import Image

from cpcpal import COLOURS, mode0_byte
import font
import pens
from pens import WHITE, YELLOW as BYELLOW, ORANGE, RED as BRED, MAGENTA as MAUVE, PBLUE

W, H = 144, 32
CELL_W, CELL_H = 2, 3
GAP = 2
SUBTITLE = "AN ORIGINAL GAME FOR THE CPC 6128"
GLYPHS = {
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
}
# Line colours of the big letters, top to bottom (21 lines).
GRADIENT = [WHITE] * 3 + [BYELLOW] * 6 + [ORANGE] * 6 + [BRED] * 6


def main(out_png, out_bin):
    img = Image.new("P", (W, H), 0)
    pal = []
    for name in pens.palette(["black"] * 4):
        pal += COLOURS[name][1]
    img.putpalette(pal + [0] * (768 - len(pal)))
    px = img.load()

    word = "SHIELDRUNNER"
    width = len(word) * (5 * CELL_W + GAP) - GAP
    x0 = (W - width) // 2 // 2 * 2

    def letters(dx, dy, colour):
        x = x0
        for ch in word:
            for gy, row in enumerate(GLYPHS[ch]):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        for yy in range(CELL_H):
                            for xx in range(CELL_W):
                                y = gy * CELL_H + yy
                                px[x + gx * CELL_W + xx + dx, y + dy] = colour(y)
            x += 5 * CELL_W + GAP

    letters(1, 2, lambda y: MAUVE)
    letters(0, 0, lambda y: GRADIENT[y])
    sx = (W - len(SUBTITLE) * font.ADVANCE) // 2 // 2 * 2
    font.draw(px, sx, 26, SUBTITLE, PBLUE)
    img.save(out_png)

    data = bytearray()
    for y in range(H):
        for x in range(0, W, 2):
            data.append(mode0_byte(px[x, y], px[x + 1, y]))
    open(out_bin, "wb").write(data)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
