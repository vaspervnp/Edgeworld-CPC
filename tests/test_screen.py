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
  The generator core pen takes the colour the game showed that frame;
- lines 136-199: the HUD in its own palette, with the radar's view marker
  where the scroll position says, the spare Runner icons, the generators'
  radar dots, the SHIELD gauge and the ENERGY bar as the game's state says;
- the position advances one column every 2 frames (25 fps) with no late
  flips, the frame's work fits the budget, and the frame stays 312 lines;
- the camera follows the Runner: standing still, riding right (once up to
  speed), skidding round to ride left, coasting to a stop, a lap of the
  planet; enemies come and go meanwhile (the player cannot be hurt here).
"""
import json
import os
import sys

from PIL import Image

from harness import Game, ROOT, X0, PIX, VIEW_W
import cpc

sys.path.insert(0, os.path.join(ROOT, "tools"))
import font  # noqa: E402

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
SPARES_LINES = range(41, 46)        # HUD lines with the spare Runner icons
SPARES_X, SPARES_STEP, MAX_SPARES = 40, 6, 5
CORE_PEN = 2
DOT_LINES = range(18, 22)           # radar dots of the generators
GAUGE_LINES, GAUGE_X, GAUGE_BYTES = range(49, 54), 104, 24
NUM_GENS, GEN_ENTRY = 4, 5
ENERGY_LINES, ENERGY_X, ENERGY_BYTES = range(41, 46), 102, 25
TEXT_LINE, TIME_X, SCORE_X, DIGIT_PEN = 33, 28, 100, 4   # time "M:SS", score digits
PLANET_LINE, PLANET_X, LABEL_PEN = 49, 36, 6                # "PLANET n"
END_MESSAGE_LINES = range(31, 56)   # HUD lines the end of a game writes over
HUD_PEN_OF = {0xF0: 5, 0x3C: 6, 0xFC: 7, 0xC0: 1}  # HUD bytes the game writes


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
        self.icon_full = hud_pal[5]
        self.icon_empty = hud_pal[2]
        self.hud_pal = hud_pal
        table = game.bytes("GEN_TABLE", NUM_GENS * GEN_ENTRY)
        self.gen_cols = [table[i * GEN_ENTRY] for i in range(NUM_GENS)]
        self.core = self.pf_pal[CORE_PEN]

    def colour(self, y, pen):
        if pen == SKY_PEN:
            return self.sky[sum(1 for first in SKY_BAND_LINES if y >= first) - 1]
        if pen == CORE_PEN:
            return self.core
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

    def hud_line(self, y, pos, spares, gens, secs=0, score=0, planet=1):
        """HUD line y; gens = (radar dot bytes, gauge byte, energy byte) as
        the game shows them; secs and score as the time and score shown."""
        line = bytearray(self.hud[y])
        if y - PLANET_LINE in range(5):
            pens = font.rows(str(planet), LABEL_PEN)[y - PLANET_LINE]
            line[PLANET_X:PLANET_X + len(pens)] = bytes(self.hud_pal[p] for p in pens)
        if y - TEXT_LINE in range(5):
            row = y - TEXT_LINE
            for x, text in ((TIME_X, f"{secs // 60}:{secs % 60:02}"), (SCORE_X, f"{score:05}")):
                pens = font.rows(text, DIGIT_PEN)[row]
                line[x:x + len(pens)] = bytes(self.hud_pal[p] for p in pens)
        dots, gauge, energy = gens
        if y in ENERGY_LINES:
            n, colour = energy & 31, (5, 6, 7)[energy >> 5]
            line[ENERGY_X:ENERGY_X + 2 * ENERGY_BYTES] = (
                bytes([self.hud_pal[colour]]) * (2 * n)
                + bytes([self.hud_pal[1]]) * (2 * (ENERGY_BYTES - n)))
        if y in DOT_LINES:
            for col, byte in zip(self.gen_cols, dots):
                x = 2 * (8 + ((col + 1) >> 2))
                line[x:x + 2] = bytes([self.hud_pal[HUD_PEN_OF[byte]]]) * 2
        if y in GAUGE_LINES:
            n = gauge & 0x3F
            fill = self.hud_pal[5 if gauge & 0xC0 else 6]
            line[GAUGE_X:GAUGE_X + 2 * GAUGE_BYTES] = (
                bytes([fill]) * (2 * n) + bytes([self.hud_pal[1]]) * (2 * (GAUGE_BYTES - n)))
        if y in MARKER_LINES:
            mx = RADAR_X0 + (((pos + VIEW_CENTRE) & 255) >> 2) * 2
            line[RADAR_X0:RADAR_X1] = bytes([self.radar_bg]) * (RADAR_X1 - RADAR_X0)
            line[mx:mx + 2] = bytes([self.marker]) * 2
        if y in SPARES_LINES:
            for i in range(MAX_SPARES):
                x = SPARES_X + i * SPARES_STEP
                line[x:x + 4] = bytes([self.icon_full if i < spares else self.icon_empty]) * 4
        return bytes(line)


class Screen:
    def __init__(self, game):
        self.game = game
        self.exp = Expected(game)
        self.last_gens = None
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
        self.exp.core = self.game.byte("CORE_PREV") & 31
        expected = self.exp.playfield(pos, records)
        if shown[:PLAY_H] != expected:
            bad = [y for y in range(PLAY_H) if shown[y] != expected[y]]
            y = bad[0]
            xs = [x for x in range(VIEW_W) if shown[y][x] != expected[y][x]]
            raise AssertionError(f"playfield wrong at position {pos} with sprites {records}: "
                                 f"lines {bad[:10]} differ, line {y} at x {xs[:10]}")
        # The HUD is not double buffered: the marker is drawn after the flip,
        # so it may lag the picture by a column, and the spare Runners may be
        # caught as they change.
        spares = self.game.byte("PL_SPARES")
        gens = (tuple(self.game.bytes("DOT_SHOWN", NUM_GENS)), self.game.byte("GAUGE_SHOWN"),
                self.game.byte("ENERGY_SHOWN"))
        gen_options = {gens, self.last_gens or gens}
        self.last_gens = gens
        # the time and score are redrawn as they change: shown, or about to be
        secs = self.game.word("TIME_SECS")
        score = self.game.word("SCORE_SHOWN")
        texts = {(secs, score), (secs + 1, score), (secs, self.game.word("SCORE"))}
        ending = self.game.byte("END_TIMER") != 0
        planet = self.game.byte("PLANET_NUM")
        for y in range(HUD_H):
            if ending and y in END_MESSAGE_LINES:
                continue        # the end message (tests/test_game.py)
            options = {self.exp.hud_line(y, p, n, g, t, sc, planet) for p in (pos, pos - 1, pos + 1)
                       for n in (spares, spares + 1) for g in gen_options for t, sc in texts}
            if shown[PLAY_H + y] not in options:
                raise AssertionError(f"HUD line {y} is wrong at position {pos}")
        # Nothing but border colour left and right of the picture.
        border = lines[self.top][0]
        for y in range(PLAY_H + HUD_H):
            line = lines[self.top + y]
            if set(line[X0 - 32:X0]) != {border} or set(line[X0 + VIEW_W * PIX:X0 + VIEW_W * PIX + 32]) != {border}:
                raise AssertionError(f"border disturbed on line {y}")
        return pos


def run_phase(screen, pos, frames, expect_dir, settle=0, rhythm=True):
    """Watch `frames` frames; check each picture, and that after `settle`
    frames the view only scrolls in expect_dir (or stands still if it is 0),
    one column every 2 frames unless rhythm is False."""
    seen = []
    for _ in range(frames):
        screen.game.next_frame()
        pos = screen.check(pos)
        seen.append(pos)
    steps = [b - a for a, b in zip(seen, seen[1:])][settle:]
    if expect_dir == 0:
        assert set(steps) <= {0}, f"expected no scrolling, got steps {steps}"
    else:
        assert set(steps) <= {0, expect_dir}, f"bad steps {steps}"
        if not rhythm:
            return pos
        moves = [i for i, s in enumerate(steps) if s]
        gaps = [b - a for a, b in zip(moves, moves[1:])]
        assert set(gaps) == {2}, f"scroll is not 1 column per 2 frames: gaps {gaps}"
    return pos


def test_crtc(crtc_type):
    game = Game(crtc_type)
    game.c.write_ram(game.sym["GOD_MODE"], b"\x01")
    screen = Screen(game)
    pos = screen.check(game.word("SCROLL_POS"))
    game.c.write_ram(game.sym["IDLE_MIN"], b"\xff\xff")   # ignore start-up
    c = game.c

    pos = run_phase(screen, pos, 20, 0)                 # standing
    c.key_down(cpc.KEY_RIGHT)
    pos = run_phase(screen, pos, 120, +1, settle=30)    # up to speed, then 25 fps
    c.key_up(cpc.KEY_RIGHT)
    c.key_down(cpc.KEY_LEFT)
    pos = run_phase(screen, pos, 120, -1, settle=60)    # skid, turn, ride left
    c.key_up(cpc.KEY_LEFT)
    pos = run_phase(screen, pos, 70, -1, rhythm=False)  # coasting...
    pos = run_phase(screen, pos, 20, 0)                 # ...to a stop
    c.key_down(cpc.KEY_RIGHT)
    pos = run_phase(screen, pos, 560, +1, settle=40)    # more than a full lap
    c.key_up(cpc.KEY_RIGHT)

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
