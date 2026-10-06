#!/usr/bin/env python3
"""Generate a planet strip from its description (assets/planets/planetN.json):
a 1024x136 Mode 0 image (256 x 17 tiles) that wraps seamlessly, and the mask
of its foreground (1 = in front of sprites).

Every planet has a starfield, a skyline, ground with a crust at line 96 (the
game's physics rely on it), props on the crust, foreground objects the
sprites pass behind and the four shield generators at columns 32, 96, 160
and 224 (drawn alike everywhere). The description's "art" names the style
of the skyline, ground, props and foreground; its "colours" are pens 3-6
and its "sky" the three raster bands of pen 1 (tools/pens.py).

Skylines keep to the tile grid: heights at column edges are multiples of 8
lines and change by at most 8 per column, so slopes come in few tiles.

Usage: gen_planet.py planet.json out.png fg_mask.png
"""
import json
import math
import random
import sys

from PIL import Image

from cpcpal import COLOURS
from pens import (BLACK, SKY, CORE, P1, P2, P3, P4, WHITE, YELLOW, ORANGE, RED, GREY,
                  GREEN, DGREEN, PBLUE, palette)

W, H = 1024, 136
COLS = W // 4
GROUND = 96               # first ground line (tile row 12)
GENERATOR_COLS = (32, 96, 160, 224)


def near_generator(c, margin=5):
    return any(-margin <= c - g <= 2 + margin for g in GENERATOR_COLS)


def skyline(target):
    """Heights above GROUND at each column edge: target(c) rounded to
    multiples of 8, then lowered until no step is over 8 (round the planet)."""
    h = [max(8, int(round(target(c) / 8)) * 8) for c in range(COLS)]
    changed = True
    while changed:
        changed = False
        for c in range(COLS):
            lim = min(h[c - 1], h[(c + 1) % COLS]) + 8
            if h[c] > lim:
                h[c] = lim
                changed = True
    return h + [h[0]]


def waves(*terms, base=32, lo=8, hi=56):
    """A target from sines: (amplitude, cycles round the planet, phase)."""
    def target(c):
        t = 2 * math.pi * c / COLS
        v = base + sum(a * math.sin(t * f + p) for a, f, p in terms)
        return max(lo, min(hi, v))
    return target


class Planet:
    def __init__(self, desc):
        self.desc = desc
        self.rnd = random.Random(desc.get("seed", 1988))
        self.img = Image.new("P", (W, H), SKY)
        pal = []
        for name in palette(desc["colours"]):
            pal += COLOURS[name][1]
        self.img.putpalette(pal + [0] * (768 - len(pal)))
        self.px = self.img.load()
        self.fg_img = Image.new("P", (W, H), 0)
        self.fg_img.putpalette([0, 0, 0, 255, 255, 255] + [0] * 762)
        self.fg = self.fg_img.load()

    def rect(self, x0, y0, x1, y1, pen):
        for y in range(max(0, y0), min(H, y1)):
            for x in range(x0, x1):
                self.px[x % W, y] = pen

    def dot(self, x, y, pen, fg=False):
        if 0 <= y < H:
            self.px[x % W, y] = pen
            if fg:
                self.fg[x % W, y] = 1

    def stars(self, rows=9):
        # at most one per tile, from a few fixed spots, so tiles repeat
        spots = [(1, 2), (3, 5), (0, 6), (2, 1)]
        for c in range(COLS):
            for row in range(rows):
                if self.rnd.random() < 0.18 - row * 0.015:
                    sx, sy = self.rnd.choice(spots)
                    self.px[c * 4 + sx, row * 8 + sy] = WHITE if self.rnd.random() < 0.7 else PBLUE

    def mountains(self, h, pen, cap=None, cap_lines=3):
        """The skyline h in pen, the top cap_lines of it in cap."""
        self.tops = []
        for c in range(COLS):
            for i in range(4):
                top = GROUND - (h[c] + (h[c + 1] - h[c]) * (2 * i + 1) // 8)
                self.tops.append(top)
                self.rect(c * 4 + i, top, c * 4 + i + 1, GROUND, pen)
                if cap is not None:
                    self.rect(c * 4 + i, top, c * 4 + i + 1, min(GROUND, top + cap_lines), cap)

    def ground(self, soil, crust, texture, marks):
        """Soil with a 2-line crust; marks(x, y) puts the texture on tile (c, row)."""
        self.rect(0, GROUND, W, H, soil)
        self.rect(0, GROUND, W, GROUND + 2, crust)
        for c in range(COLS):
            for row in range(13, 16):
                if self.rnd.random() < 0.3:
                    for (dx, dy) in self.rnd.choice(marks):
                        self.px[c * 4 + dx, row * 8 + dy] = texture
        self.rect(0, 128, W, H, BLACK)

    def seam(self, pens_):
        # several pens on the last line, so a HUD palette switch that comes
        # too early shows (tests/test_screen.py)
        for x in range(W):
            self.px[x, H - 1] = pens_[x % len(pens_)]
            if x % 12 in (3, 4):
                self.px[x, H - 2] = pens_[1]

    def generators(self):
        for gc in GENERATOR_COLS:
            x = gc * 4
            self.rect(x, 80, x + 12, GROUND, GREY)            # platform rows 10-11
            self.rect(x, 80, x + 12, 82, PBLUE)
            self.rect(x + 4, 48, x + 8, 80, GREY)             # shaft rows 6-9
            self.rect(x + 5, 52, x + 7, 76, CORE)
            self.rect(x, 40, x + 12, 48, DGREEN)              # cap row 5
            self.rect(x + 2, 40, x + 10, 42, GREEN)
            self.rect(x + 5, 40, x + 7, 41, WHITE)

    def columns(self, every, start, skip=5):
        cols, c = [], start
        while c < COLS - 3:
            if not near_generator(c, skip) and not near_generator(c + 3, skip):
                cols.append(c)
            c += every
        return cols

    def save(self, out, fg_out):
        self.img.save(out)
        self.fg_img.save(fg_out)


# ---------------------------------------------------------------------------
# Styles: skyline, ground, props and foreground of each kind of planet.

def rust(p):
    """A dead moon of rust: rolling mauve hills, red soil with pebbles,
    boulders, crystal spires in front."""
    p.stars()
    p.mountains(skyline(waves((14, 3, 0.5), (9, 7, 1.3), (5, 13, 0))), P1)
    p.ground(P2, ORANGE, P3, [[(1, 3)], [(0, 5), (2, 2)], [(3, 6)], [(2, 4), (1, 7)]])
    for c in range(4, COLS, 23):                      # boulders on the crust
        p.rect(c * 4 + 1, GROUND - 6, c * 4 + 7, GROUND, GREY)
        p.rect(c * 4 + 2, GROUND - 8, c * 4 + 6, GROUND - 6, GREY)
        p.rect(c * 4 + 2, GROUND - 6, c * 4 + 4, GROUND - 3, PBLUE)
    p.generators()
    for sc in (12, 52, 75, 118, 141, 190, 236):      # crystal spires, 12 x 44
        x0 = sc * 4
        for i in range(44):
            y = GROUND + 4 - 44 + i
            half = 1 + i * 5 // 43
            for x in range(x0 + 6 - half, x0 + 6 + half):
                pen = P4 if x < x0 + 6 else PBLUE
                if x == x0 + 6 - half or i < 3:
                    pen = WHITE
                p.dot(x, y, pen, fg=True)
    p.seam([P2, P1, P2, P3, P2, GREY])


def ice(p):
    """A frozen world: jagged snow-capped peaks, a blue ice sheet with
    cracks, ice blocks, shards of ice in front."""
    p.stars(rows=8)
    p.mountains(skyline(waves((16, 5, 0.2), (12, 11, 2.0), (8, 23, 1.0), base=36, hi=64)),
                P2, cap=WHITE, cap_lines=3)
    p.ground(P1, P3, P4, [[(0, 1), (1, 2), (2, 3)], [(3, 2), (2, 3)], [(1, 6), (2, 6)]])
    for c in range(9, COLS, 19):                      # ice blocks
        if near_generator(c, 2):
            continue
        p.rect(c * 4, GROUND - 8, c * 4 + 8, GROUND, P4)
        p.rect(c * 4, GROUND - 8, c * 4 + 8, GROUND - 7, WHITE)
        p.rect(c * 4 + 5, GROUND - 6, c * 4 + 7, GROUND - 1, P3)
    p.generators()
    for sc in p.columns(29, 14):                      # leaning shards, 8 wide
        x0 = sc * 4
        height = 36 + (sc * 7) % 12
        for i in range(height):
            y = GROUND + 2 - height + i
            lean = (height - i) // 8
            w = 1 + i * 3 // height
            for x in range(x0 + 4 + lean - w, x0 + 4 + lean + w):
                pen = WHITE if x == x0 + 4 + lean - w else (P3 if x < x0 + 4 + lean else P4)
                p.dot(x, y, pen, fg=True)
    p.seam([P1, P3, P1, P4, P1, WHITE])


def desert(p):
    """A desert of mesas: flat-topped buttes, sand with ripples, standing
    stones, rock hoodoos in front."""
    p.stars(rows=7)

    def mesas(c):
        t = 2 * math.pi * c / COLS
        v = math.sin(t * 4 + 0.7) + 0.6 * math.sin(t * 9 + 2.1)
        return 48 if v > 0.55 else 24 if v > -0.2 else 8
    h = skyline(mesas)
    p.mountains(h, P4, cap=P3, cap_lines=2)
    p.ground(P2, ORANGE, P1, [[(0, 3), (1, 3), (2, 3)], [(1, 6), (2, 6)], [(2, 1), (3, 1)]])
    for c in range(6, COLS, 17):                      # standing stones
        if near_generator(c, 2):
            continue
        p.rect(c * 4 + 1, GROUND - 12, c * 4 + 5, GROUND, GREY)
        p.rect(c * 4 + 1, GROUND - 12, c * 4 + 3, GROUND, PBLUE)
    p.generators()
    for sc in p.columns(31, 18):                      # hoodoos: a column with a cap
        x0 = sc * 4
        height = 30 + (sc * 5) % 14
        top = GROUND + 2 - height
        for y in range(top + 6, GROUND + 2):
            for x in range(x0 + 3, x0 + 9):
                p.dot(x, y, P3 if x < x0 + 6 else P1, fg=True)
        for y in range(top, top + 6):
            for x in range(x0, x0 + 12):
                p.dot(x, y, P4 if y > top + 1 else P3, fg=True)
    p.seam([P2, P1, P2, P3, P2, ORANGE])


def volcano(p):
    """A volcanic world: smoking cones with lava running down, ash with
    glowing cracks, vents, basalt columns in front."""
    p.stars(rows=6)
    cones = (20, 84, 148, 200)

    def target(c):
        v = 16
        for k in cones:
            d = min(abs(c - k), COLS - abs(c - k))
            v = max(v, 64 - d * 5)
        return v
    h = skyline(target)
    p.mountains(h, P1)
    for k in cones:                                   # craters and lava streams
        x = k * 4
        top = GROUND - h[k]
        p.rect(x - 2, top, x + 4, top + 2, ORANGE)
        p.rect(x, top, x + 2, top + 1, YELLOW)
        for side in (-1, 1):
            for i in range(1, 22):
                lx = x + side * (i // 2) + (1 if side > 0 else 0)
                ly = top + 2 + i
                if ly < GROUND and p.px[lx % W, ly] == P1:
                    p.px[lx % W, ly] = ORANGE if i % 5 else RED
    p.ground(P2, P3, ORANGE, [[(0, 2), (1, 3), (2, 3)], [(2, 5), (3, 6)], [(1, 1)]])
    for c in range(11, COLS, 21):                     # vents
        if near_generator(c, 2):
            continue
        p.rect(c * 4, GROUND - 4, c * 4 + 8, GROUND, GREY)
        p.rect(c * 4 + 2, GROUND - 6, c * 4 + 6, GROUND - 4, GREY)
        p.rect(c * 4 + 3, GROUND - 6, c * 4 + 5, GROUND - 5, ORANGE)
    p.generators()
    for sc in p.columns(27, 9):                       # basalt columns, 3 of them
        x0 = sc * 4
        for j, height in enumerate((34, 42, 28)):
            for y in range(GROUND + 2 - height, GROUND + 2):
                for x in range(x0 + j * 4, x0 + j * 4 + 4):
                    edge = x == x0 + j * 4
                    pen = P4 if y < GROUND + 4 - height else (GREY if edge else P3)
                    p.dot(x, y, pen, fg=True)
    p.seam([P2, P3, P2, P1, P2, ORANGE])


STYLES = {"rust": rust, "ice": ice, "desert": desert, "volcano": volcano}


def main(desc_path, out, fg_out):
    desc = json.load(open(desc_path))
    p = Planet(desc)
    STYLES[desc["art"]](p)
    p.save(out, fg_out)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
