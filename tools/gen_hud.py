#!/usr/bin/env python3
"""Generate the HUD strip: 160x56 Mode 0 pixels (7 character rows).

Its first 4 lines are pen 0 only: the HUD palette is switched in while
they are displayed, so they must look the same under either palette.

Usage: gen_hud.py out.png
"""
import sys
from PIL import Image

from cpcpal import COLOURS

W, H = 160, 56
PENS = ["black", "blue", "white", "pastel_blue", "bright_white", "bright_green",
        "bright_yellow", "bright_red", "orange", "sky_blue", "green",
        "black", "black", "black", "black", "black"]
BLACK, RADAR_BG, GREY, PBLUE, WHITE, BGREEN, BYELLOW, BRED, ORANGE, SKY, GREEN = range(11)

# Radar interior (also used by the game, see src/hud.asm).
RADAR_X0, RADAR_X1 = 16, 144      # 128 pixels for 256 map columns
RADAR_Y0, RADAR_Y1 = 12, 24
GENERATOR_COLS = (32, 96, 160, 224)

FONT = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "011", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
    ":": ["000", "010", "000", "010", "000"], " ": ["000"] * 5,
    "D": ["110", "101", "101", "101", "110"], "E": ["111", "100", "110", "100", "111"],
    "G": ["111", "100", "101", "101", "111"], "H": ["101", "101", "111", "101", "101"],
    "I": ["111", "010", "010", "010", "111"], "L": ["100", "100", "100", "100", "111"],
    "M": ["101", "111", "111", "101", "101"], "N": ["111", "101", "101", "101", "101"],
    "R": ["110", "101", "110", "101", "101"], "S": ["111", "100", "111", "001", "111"],
    "T": ["111", "010", "010", "010", "010"], "U": ["101", "101", "101", "101", "111"],
    "Y": ["101", "101", "010", "010", "010"],
}


def main(out):
    img = Image.new("P", (W, H), BLACK)
    pal = []
    for name in PENS:
        pal += COLOURS[name][1]
    img.putpalette(pal + [0] * (768 - len(pal)))
    px = img.load()

    def rect(x0, y0, x1, y1, pen):
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[x, y] = pen

    def text(x, y, s, pen):
        for ch in s:
            for gy, row in enumerate(FONT[ch]):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        px[x + gx, y + gy] = pen
            x += 4

    rect(0, 4, W, 5, GREY)
    rect(0, 5, W, 6, PBLUE)

    # Radar: frame, interior, planet surface, generators.
    rect(RADAR_X0 - 2, RADAR_Y0 - 2, RADAR_X1 + 2, RADAR_Y1 + 2, GREY)
    rect(RADAR_X0 - 1, RADAR_Y0 - 1, RADAR_X1 + 1, RADAR_Y1 + 1, PBLUE)
    rect(RADAR_X0, RADAR_Y0, RADAR_X1, RADAR_Y1, RADAR_BG)
    rect(RADAR_X0, 19, RADAR_X1, 20, SKY)
    for gc in GENERATOR_COLS:
        x = RADAR_X0 + (gc + 1) // 2
        rect(x, 14, x + 2, 18, BGREEN)

    text(8, 31, "TIME 9:59", BYELLOW)
    text(76, 31, "ENERGY", BYELLOW)
    rect(102, 31, 152, 36, GREEN)
    rect(102, 31, 152, 32, BGREEN)
    text(56, 43, "SHIELDRUNNER", PBLUE)

    rect(0, 52, W, 53, PBLUE)
    rect(0, 53, W, 54, GREY)
    img.save(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
