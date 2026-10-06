#!/usr/bin/env python3
"""Milestone 1 test: the scroll engine on CRTC types 0, 1 and 2.

Boots build/shield.dsk in the headless emulator (CPCEMU_DIR, default
~/cpcemu) and checks, frame by frame:

- every displayed frame is exactly the map rendered at some scroll position
  (no torn or stale columns);
- the position advances one column every 2 frames (25 fps), with no late
  flips and the frame's work inside the 2-frame budget;
- it scrolls right on its own, left while left is held, and stops on down.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.environ.get("CPCEMU_DIR", os.path.expanduser("~/cpcemu")))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from PIL import Image  # noqa: E402
import cpc  # noqa: E402

DSK = os.path.join(ROOT, "build", "shield.dsk")
SYM = os.path.join(ROOT, "build", "shield.sym")
PLANET = os.path.join(ROOT, "assets", "testplanet.png")
PAL = os.path.join(ROOT, "build", "testplanet.pal")

FB_W = cpc.FB_WIDTH
X0 = 64                 # left edge of the display area in the framebuffer
PIX = 4                 # framebuffer pixels per Mode 0 pixel
VIEW_W, VIEW_H = 160, 200
MAP_W = 1024            # planet width in pixels
INTS_BUDGET = 12        # 2 frames of 6 interrupts


def symbols():
    out = {}
    for line in open(SYM):
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("#"):
            out[parts[0]] = int(parts[1][1:], 16)
    return out


class Game:
    def __init__(self, crtc_type):
        self.sym = symbols()
        self.c = cpc.CPC()
        self.c.crtc_type = crtc_type
        self.c.run_frames(150)
        self.c.insert_disc(DSK)
        self.c.type_text('RUN"SHIELD\n')
        isr = self.sym["ISR"]
        vector = bytes([0xC3, isr & 0xFF, isr >> 8])
        for _ in range(3000):
            self.c.run_frames(1)
            if self.c.read_ram(0x38, 3) == vector and self.word("FLIPS") > 0:
                return
        raise AssertionError("game did not start")

    def byte(self, name):
        return self.c.read_ram(self.sym[name], 1)[0]

    def word(self, name):
        lo, hi = self.c.read_ram(self.sym[name], 2)
        return lo | hi << 8

    def next_frame(self):
        """Run to just after the next VSYNC, when a whole frame is in the framebuffer."""
        n = self.word("FRAME_COUNT")
        for _ in range(400):
            self.c.run_us(64)
            if self.word("FRAME_COUNT") != n:
                return
        raise AssertionError("no VSYNC")

    def pens(self, y0):
        """The displayed picture as rows of pens."""
        fb = self.c.framebuffer()
        hw_to_pen = {hw & 0x1F: pen for pen, hw in enumerate(open(PAL, "rb").read())}
        rows = []
        for y in range(VIEW_H):
            base = (y0 + y) * FB_W + X0 + 1
            rows.append(bytes(hw_to_pen.get(fb[base + x * PIX], 255) for x in range(VIEW_W)))
        return rows


class Reference:
    def __init__(self):
        img = Image.open(PLANET)
        w, h = img.size
        data = img.tobytes()
        self.rows = [data[y * w:(y + 1) * w] * 2 for y in range(h)]

    def view(self, pos):
        x = (pos * 4) % MAP_W
        return [r[x:x + VIEW_W] for r in self.rows]


def find_y0(game, ref, pos_guess):
    for y0 in range(20, 70):
        shown = game.pens(y0)
        for p in range(pos_guess - 3, pos_guess + 4):
            if shown == ref.view(p):
                return y0
    raise AssertionError("cannot find the display area in the framebuffer")


def shown_pos(game, ref, y0, guess):
    shown = game.pens(y0)
    for p in (guess, guess + 1, guess - 1, guess + 2, guess - 2):
        if shown == ref.view(p):
            return p
    bad = sum(1 for a, b in zip(shown, ref.view(guess)) if a != b)
    raise AssertionError(f"frame matches no scroll position near {guess} ({bad} lines differ)")


def run_phase(game, ref, y0, pos, frames, expect_dir):
    """Watch `frames` frames; check the picture and the 1-column-per-2-frames rhythm."""
    seen = []
    for _ in range(frames):
        game.next_frame()
        pos = shown_pos(game, ref, y0, pos)
        seen.append(pos)
    steps = [b - a for a, b in zip(seen, seen[1:])]
    if expect_dir == 0:
        assert set(steps) == {0}, f"expected no scrolling, got steps {steps}"
    else:
        # skip the first few frames while a direction change takes effect
        tail = steps[4:]
        assert set(tail) <= {0, expect_dir}, f"bad steps {tail}"
        moves = [i for i, s in enumerate(tail) if s]
        gaps = [b - a for a, b in zip(moves, moves[1:])]
        assert set(gaps) == {2}, f"scroll is not 1 column per 2 frames: gaps {gaps}"
    return pos


def test_crtc(crtc_type):
    ref = Reference()
    game = Game(crtc_type)
    game.next_frame()
    y0 = find_y0(game, ref, game.word("SCROLL_POS"))
    pos = shown_pos(game, ref, y0, game.word("SCROLL_POS"))

    pos = run_phase(game, ref, y0, pos, 120, +1)          # auto-scroll right, wraps past 256 later
    game.c.key_down(cpc.KEY_LEFT)
    pos = run_phase(game, ref, y0, pos, 60, -1)
    game.c.key_up(cpc.KEY_LEFT)
    pos = run_phase(game, ref, y0, pos, 30, -1)           # direction persists
    game.c.key_down(cpc.KEY_DOWN)
    game.c.run_frames(4)
    game.c.key_up(cpc.KEY_DOWN)
    pos = run_phase(game, ref, y0, pos, 20, 0)
    game.c.key_down(cpc.KEY_RIGHT)
    pos = run_phase(game, ref, y0, pos, 600, +1)          # more than a full lap of the planet
    game.c.key_up(cpc.KEY_RIGHT)

    late = game.word("LATE_FLIPS")
    work = game.byte("WORK_INTS_MAX")
    assert late == 0, f"{late} late flips"
    assert work < INTS_BUDGET, f"frame work took {work}/{INTS_BUDGET} interrupts"
    print(f"CRTC {crtc_type}: ok, {game.word('FLIPS')} flips, 0 late, "
          f"max work {work}/{INTS_BUDGET} ints ({work * 100 // INTS_BUDGET}% of the 25 fps frame)")


def main():
    for t in (0, 1, 2):
        test_crtc(t)


if __name__ == "__main__":
    main()
