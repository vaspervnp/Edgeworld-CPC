#!/usr/bin/env python3
"""Generate the HUD strip: 160x64 Mode 0 pixels (8 character rows).

Its first 8 lines are pen 0 only: the HUD palette is switched in while
they are displayed, so they must look the same under either palette.

Usage: gen_hud.py out.png
"""
import sys
from PIL import Image

from cpcpal import COLOURS
import font

W, H = 160, 64
TOP = 8                   # blank lines on top; the art below is 56 lines
PENS = ["black", "blue", "white", "pastel_blue", "bright_white", "bright_green",
        "bright_yellow", "bright_red", "orange", "sky_blue", "green",
        "black", "black", "black", "black", "black"]
BLACK, RADAR_BG, GREY, PBLUE, WHITE, BGREEN, BYELLOW, BRED, ORANGE, SKY, GREEN = range(11)

# Radar interior (also used by the game, see src/hud.asm).
RADAR_X0, RADAR_X1 = 16, 144      # 128 pixels for 256 map columns
RADAR_Y0, RADAR_Y1 = TOP + 8, TOP + 20
GENERATOR_COLS = (32, 96, 160, 224)
GAUGE_X0, GAUGE_X1 = 104, 152     # 24 bytes
ROW_A, ROW_B, ROW_C = TOP + 25, TOP + 33, TOP + 41
SCORE_X = 100                     # 5 digits drawn by the game, then a fixed 0
BWHITE_DIGITS = 4

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
        font.draw(px, x, y, s, pen)

    rect(0, TOP, W, TOP + 1, GREY)
    rect(0, TOP + 1, W, TOP + 2, PBLUE)

    # Radar: frame, interior, planet surface, generators.
    rect(RADAR_X0 - 2, RADAR_Y0 - 2, RADAR_X1 + 2, RADAR_Y1 + 2, GREY)
    rect(RADAR_X0 - 1, RADAR_Y0 - 1, RADAR_X1 + 1, RADAR_Y1 + 1, PBLUE)
    rect(RADAR_X0, RADAR_Y0, RADAR_X1, RADAR_Y1, RADAR_BG)
    rect(RADAR_X0, TOP + 15, RADAR_X1, TOP + 16, SKY)
    for gc in GENERATOR_COLS:
        x = RADAR_X0 + (gc + 1) // 2
        rect(x, TOP + 10, x + 2, TOP + 14, BGREEN)

    # Three text rows (lines 33, 41 and 49); the game draws the time, the
    # score, the Runner icons and the bars (see src/game.asm, player.asm,
    # enemies.asm and generators.asm).
    text(8, ROW_A, "TIME 0:00", BYELLOW)
    text(76, ROW_A, "SCORE", BYELLOW)
    text(SCORE_X, ROW_A, "000000", BWHITE_DIGITS)
    text(8, ROW_B, "RUNNERS", BYELLOW)
    text(76, ROW_B, "ENERGY", BYELLOW)
    rect(102, ROW_B, 152, ROW_B + 5, RADAR_BG)
    text(8, ROW_C, "PLANET 1", BYELLOW)
    text(76, ROW_C, "SHIELD", BYELLOW)
    rect(GAUGE_X0, ROW_C, GAUGE_X1, ROW_C + 5, RADAR_BG)

    rect(0, TOP + 48, W, TOP + 49, PBLUE)
    rect(0, TOP + 49, W, TOP + 50, GREY)
    img.save(out)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
