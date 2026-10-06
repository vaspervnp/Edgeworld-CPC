#!/usr/bin/env python3
"""Screen test on CRTC types 0, 1 and 2: scroll, CRTC split and rasters.

Boots build/shield.dsk in the headless emulator and checks, frame by frame,
that the whole 200-line picture is exactly what it should be:

- lines 0-143: the map at some scroll position, in the playfield palette,
  with the sky pen in its raster colour for each band (so a raster change
  that lands inside the picture fails the test);
- lines 144-199: the HUD in its own palette, with the radar's view marker
  where the scroll position says;
- the position advances one column every 2 frames (25 fps) with no late
  flips, the frame's work fits the budget, and the frame stays 312 lines;
- it scrolls right on its own, left while left is held, and stops on down.
"""
import os

from PIL import Image

from harness import Game, ROOT, X0, PIX, VIEW_W
import cpc

PLANET = os.path.join(ROOT, "assets", "testplanet.png")
HUD = os.path.join(ROOT, "assets", "hud.png")

PLAY_H = 144
HUD_H = 56
MAP_W = 1024            # planet width in pixels
SKY_PEN = 1
SKY_BAND_LINES = (0, 36, 88)        # first line of each sky colour
INTS_BUDGET = 12        # 2 frames of 6 interrupts
MARKER_LINES = range(20, 23)        # HUD lines with the radar view marker
RADAR_X0, RADAR_X1 = 16, 144
VIEW_CENTRE = 20


def indexed_rows(path):
    img = Image.open(path)
    w, h = img.size
    data = img.tobytes()
    return [data[y * w:(y + 1) * w] for y in range(h)]


class Expected:
    def __init__(self, game):
        pf_pal = [v & 31 for v in game.bytes("PF_PALETTE", 16)]
        hud_pal = [v & 31 for v in game.bytes("HUD_PALETTE", 16)]
        sky = [v & 31 for v in game.bytes("SKY_COLOURS", 3)]
        self.planet = []
        for y, row in enumerate(indexed_rows(PLANET)):
            band = sum(1 for first in SKY_BAND_LINES if y >= first) - 1
            pal = list(pf_pal)
            pal[SKY_PEN] = sky[band]
            self.planet.append(bytes(pal[p] for p in row) * 2)
        self.hud = [bytes(hud_pal[p] for p in row) for row in indexed_rows(HUD)]
        self.marker = hud_pal[4]
        self.radar_bg = hud_pal[1]

    def playfield(self, pos):
        x = (pos * 4) % MAP_W
        return [r[x:x + VIEW_W] for r in self.planet]

    def hud_line(self, y, pos):
        line = self.hud[y]
        if y in MARKER_LINES:
            mx = RADAR_X0 + (((pos + VIEW_CENTRE) & 255) >> 2) * 2
            line = bytearray(line)
            line[RADAR_X0:RADAR_X1] = bytes([self.radar_bg]) * (RADAR_X1 - RADAR_X0)
            line[mx:mx + 2] = bytes([self.marker]) * 2
        return bytes(line)


class Screen:
    def __init__(self, game):
        self.game = game
        self.exp = Expected(game)
        game.next_frame()
        self.top = self.find_top()

    def find_top(self):
        lines = self.game.frame_lines()
        for y in range(10, 80):
            if Game.pixels(lines[y + PLAY_H + 4]) == self.exp.hud[4]:
                return y
        raise AssertionError("cannot find the HUD in the framebuffer")

    def check(self, guess):
        """Check the current frame; return the scroll position it shows."""
        lines = self.game.frame_lines()
        shown = [Game.pixels(lines[self.top + y]) for y in range(PLAY_H + HUD_H)]
        pos = None
        for p in (guess, guess + 1, guess - 1, guess + 2, guess - 2):
            if shown[:PLAY_H] == self.exp.playfield(p):
                pos = p
                break
        if pos is None:
            diffs = {}
            for p in range(guess - 2, guess + 3):
                ref = self.exp.playfield(p)
                diffs[p] = [y for y in range(PLAY_H) if shown[y] != ref[y]]
            best = min(diffs, key=lambda p: len(diffs[p]))
            raise AssertionError(f"playfield matches no scroll position near {guess}; "
                                 f"closest is {best}, lines {diffs[best][:10]} differ")
        # The marker is drawn after the flip, so it may lag the picture by a column.
        for y in range(HUD_H):
            options = {self.exp.hud_line(y, p) for p in (pos, pos - 1, pos + 1)}
            if shown[PLAY_H + y] not in options:
                raise AssertionError(f"HUD line {y} is wrong at position {pos}")
        # Nothing but border colour left and right of the picture.
        border = lines[self.top][0]
        for y in range(PLAY_H + HUD_H):
            line = lines[self.top + y]
            if set(line[X0 - 32:X0]) != {border} or set(line[X0 + VIEW_W * PIX:X0 + VIEW_W * PIX + 32]) != {border}:
                raise AssertionError(f"border disturbed on line {y}")
        return pos


def run_phase(screen, pos, frames, expect_dir):
    """Watch `frames` frames; check each picture and the 1-column-per-2-frames rhythm."""
    seen = []
    for _ in range(frames):
        screen.game.next_frame()
        pos = screen.check(pos)
        seen.append(pos)
    steps = [b - a for a, b in zip(seen, seen[1:])]
    if expect_dir == 0:
        assert set(steps) == {0}, f"expected no scrolling, got steps {steps}"
    else:
        tail = steps[4:]        # a direction change takes a few frames
        assert set(tail) <= {0, expect_dir}, f"bad steps {tail}"
        moves = [i for i, s in enumerate(tail) if s]
        gaps = [b - a for a, b in zip(moves, moves[1:])]
        assert set(gaps) == {2}, f"scroll is not 1 column per 2 frames: gaps {gaps}"
    return pos


def test_crtc(crtc_type):
    game = Game(crtc_type)
    screen = Screen(game)
    pos = screen.check(game.word("SCROLL_POS"))

    pos = run_phase(screen, pos, 120, +1)               # auto-scroll right
    game.c.key_down(cpc.KEY_LEFT)
    pos = run_phase(screen, pos, 60, -1)
    game.c.key_up(cpc.KEY_LEFT)
    pos = run_phase(screen, pos, 30, -1)                # direction persists
    game.c.key_down(cpc.KEY_DOWN)
    game.c.run_frames(4)
    game.c.key_up(cpc.KEY_DOWN)
    pos = run_phase(screen, pos, 20, 0)
    game.c.key_down(cpc.KEY_RIGHT)
    pos = run_phase(screen, pos, 560, +1)               # more than a full lap
    game.c.key_up(cpc.KEY_RIGHT)

    # 312-line frames: 250 VSYNCs in 5 seconds.
    n = game.word("FRAME_COUNT")
    game.c.run_us(5_000_000)
    frames = (game.word("FRAME_COUNT") - n) & 0xFFFF
    assert abs(frames - 250) <= 1, f"{frames} frames in 5 s, expected 250"

    late = game.word("LATE_FLIPS")
    work = game.byte("WORK_INTS_MAX")
    assert late == 0, f"{late} late flips"
    assert work < INTS_BUDGET, f"frame work took {work}/{INTS_BUDGET} interrupts"
    print(f"CRTC {crtc_type}: ok, {game.word('FLIPS')} flips, 0 late, {frames} frames in 5 s, "
          f"max work {work}/{INTS_BUDGET} ints")


def main():
    for t in (0, 1, 2):
        test_crtc(t)


if __name__ == "__main__":
    main()
