#!/usr/bin/env python3
"""Screen test on CRTC types 0, 1 and 2: scroll, CRTC split, rasters and
sprites.

Boots build/shield.dsk in the headless emulator and checks, frame by frame,
that the whole 200-line picture is exactly what it should be:

- lines 0-135: the map at the displayed buffer's scroll position, with the
  buffer's sprites drawn over it in list order (pen 0 transparent, clipped
  to the view) and the foreground over them, in the playfield palette, with
  the sky pen in its raster colour for each band (so a raster change that
  lands inside the picture fails the test);
- lines 136-199: the HUD in its own palette, with the radar's view marker
  where the scroll position says;
- the position advances one column every 2 frames (25 fps) with no late
  flips, the frame's work fits the budget, and the frame stays 312 lines;
- it scrolls right on its own, left while left is held, and stops on down.
"""
import json
import os

from PIL import Image

from harness import Game, ROOT, X0, PIX, VIEW_W
import cpc

PLANET = os.path.join(ROOT, "assets", "testplanet.png")
PLANET_FG = os.path.join(ROOT, "assets", "testplanet_fg.png")
SPRITES = os.path.join(ROOT, "assets", "sprites.png")
SPRITES_JSON = os.path.join(ROOT, "assets", "sprites.json")
HUD = os.path.join(ROOT, "assets", "hud.png")

PLAY_H = 136
HUD_H = 64
MAP_W = 1024            # planet width in pixels
SKY_PEN = 1
SKY_BAND_LINES = (0, 36, 88)        # first line of each sky colour
IDLE_LOOP = 10          # NOPs per turn of the wait loop in flip_and_wait
MARKER_LINES = range(24, 27)        # HUD lines with the radar view marker
REC_SIZE = 4
RADAR_X0, RADAR_X1 = 16, 144
VIEW_CENTRE = 20


def indexed_rows(path):
    img = Image.open(path)
    w, h = img.size
    data = img.tobytes()
    return [data[y * w:(y + 1) * w] for y in range(h)]


def sprite_frames():
    sheet = Image.open(SPRITES)
    px = sheet.load()
    return [[[px[f["x"] + x, f["y"] + y] for x in range(f["w"])] for y in range(f["h"])]
            for f in json.load(open(SPRITES_JSON))]


class Expected:
    def __init__(self, game):
        self.pf_pal = [v & 31 for v in game.bytes("PF_PALETTE", 16)]
        hud_pal = [v & 31 for v in game.bytes("HUD_PALETTE", 16)]
        self.sky = [v & 31 for v in game.bytes("SKY_COLOURS", 3)]
        self.planet = [bytes(row) * 2 for row in indexed_rows(PLANET)]
        self.fg = [bytes(row) * 2 for row in indexed_rows(PLANET_FG)]
        self.frames = sprite_frames()
        self.hud = [bytes(hud_pal[p] for p in row) for row in indexed_rows(HUD)]
        self.marker = hud_pal[4]
        self.radar_bg = hud_pal[1]

    def colour(self, y, pen):
        if pen == SKY_PEN:
            return self.sky[sum(1 for first in SKY_BAND_LINES if y >= first) - 1]
        return self.pf_pal[pen]

    def playfield(self, pos, records=()):
        """Hardware colours of the playfield at scroll position pos, with
        sprite records (frame, world x, y) drawn over it."""
        x0 = (pos * 4) % MAP_W
        pens = [bytearray(r[x0:x0 + VIEW_W]) for r in self.planet]
        for frame, wx, wy in records:
            sx = (wx - pos * 4) % MAP_W
            if sx >= 512:
                sx -= MAP_W
            for dy, row in enumerate(self.frames[frame]):
                for dx, pen in enumerate(row):
                    x = sx + dx
                    if pen and 0 <= x < VIEW_W:
                        pens[wy + dy][x] = pen
        for y in range(PLAY_H):
            fg = self.fg[y]
            for x in range(VIEW_W):
                if fg[x0 + x]:
                    pens[y][x] = self.planet[y][x0 + x]
        return [bytes(self.colour(y, p) for p in row) for y, row in enumerate(pens)]

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
            if Game.pixels(lines[y + PLAY_H + 8]) == self.exp.hud[8]:
                return y
        raise AssertionError("cannot find the HUD in the framebuffer")

    def buffers(self):
        """(scroll position, sprite records) of each screen buffer."""
        g = self.game
        out = []
        for side in ("FRONT", "BACK"):
            pos = g.word(side + "_POS")
            lst = g.c.read_ram(g.word(side + "_LIST"), 1 + 12 * REC_SIZE)
            recs = []
            for i in range(lst[0]):
                r = lst[1 + i * REC_SIZE:1 + (i + 1) * REC_SIZE]
                recs.append((r[0], r[1] | r[2] << 8, r[3]))
            out.append((pos, recs))
        return out

    def check(self, guess):
        """Check the current frame; return the scroll position it shows.

        The displayed buffer is the front one: frames are sampled just after
        VSYNC, before the main loop can swap or redraw anything."""
        lines = self.game.frame_lines()
        shown = [Game.pixels(lines[self.top + y]) for y in range(PLAY_H + HUD_H)]
        pos, records = self.buffers()[0]
        expected = self.exp.playfield(pos, records)
        if shown[:PLAY_H] != expected:
            bad = [y for y in range(PLAY_H) if shown[y] != expected[y]]
            y = bad[0]
            xs = [x for x in range(VIEW_W) if shown[y][x] != expected[y][x]]
            raise AssertionError(f"playfield wrong at position {pos} with sprites {records}: "
                                 f"lines {bad[:10]} differ, line {y} at x {xs[:10]}")
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
    game.c.write_ram(game.sym["IDLE_MIN"], b"\xff\xff")   # ignore start-up

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
    pos = run_phase(screen, pos, 540, +1)               # more than a full lap
    game.c.key_up(cpc.KEY_RIGHT)

    # 312-line frames: 250 VSYNCs in 5 seconds.
    n = game.word("FRAME_COUNT")
    game.c.run_us(5_000_000)
    frames = (game.word("FRAME_COUNT") - n) & 0xFFFF
    assert abs(frames - 250) <= 1, f"{frames} frames in 5 s, expected 250"

    late = game.word("LATE_FLIPS")
    spare = game.word("IDLE_MIN") * IDLE_LOOP
    assert late == 0, f"{late} late flips"
    print(f"CRTC {crtc_type}: ok, {game.word('FLIPS')} flips, 0 late, {frames} frames in 5 s, "
          f"least spare time {spare} us per 25 fps frame")


def main():
    for t in (0, 1, 2):
        test_crtc(t)


if __name__ == "__main__":
    main()
