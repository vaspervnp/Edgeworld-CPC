#!/usr/bin/env python3
"""Game flow test, on CRTC type 1: the title screen and its music, the high
score page, starting, the countdown and score in the HUD, sound effects,
clearing the planet (bonus, message), entering initials, a second game that
starts afresh, and losing the shield.

HUD text is checked in the displayed picture, against the font of
tools/font.py.
"""
import os
import sys

from harness import Game, ROOT, ST_TITLE, ST_PLAY, ST_ENTRY
from test_screen import Screen
import cpc

sys.path.insert(0, os.path.join(ROOT, "tools"))
import font  # noqa: E402

PLAY_H = 136
PLANET_TIME = 180
GAME_OVER_CLEAR, GAME_OVER_SHIELD = 3, 2
PEN_DIGITS, PEN_LABEL, PEN_GOOD, PEN_BAD = 4, 6, 5, 7
NUM_GENS = 4
E_BOOM, E_HOSTILE = 6, 6
EN_SIZE, MAX_ENEMIES = 8, 6
PAGE_FRAMES = 400
R_PERIOD_C, R_NOISE, R_MIXER, R_VOL_A, R_VOL_C = 4, 6, 7, 8, 10


class Flow:
    def __init__(self):
        self.g = Game(start=False)
        self.c = self.g.c
        self.screen = None

    def frames(self, n):
        self.c.run_frames(n)

    def state(self):
        return self.g.byte("GAME_STATE")

    def hud_shows(self, line, text, pen, x=None):
        """Is text drawn on HUD line `line` (centred, or at pixel x) in the
        picture just displayed?"""
        if self.screen is None:
            self.screen = Screen(self.g)
        self.g.next_frame()
        lines = self.g.frame_lines()
        pal = self.screen.exp.hud_pal
        if x is None:
            x = 80 - 2 * len(text)
        for row, pens in enumerate(font.rows(text, pen)):
            shown = Game.pixels(lines[self.screen.top + PLAY_H + line + row])
            if shown[x:x + len(pens)] != bytes(pal[p] for p in pens):
                return False
        return True

    def wait_text(self, line, text, pen, frames=60, x=None):
        for _ in range(frames):
            if self.hud_shows(line, text, pen, x):
                return
        raise AssertionError(f"HUD line {line} never showed {text!r}")

    def press(self, key, frames=6):
        self.c.key_down(key)
        self.frames(frames)
        self.c.key_up(key)
        self.frames(frames)


def test():
    f = Flow()
    g, c = f.g, f.c

    # Title: the how-to-play page, PRESS FIRE flashing, the title music.
    assert f.state() == ST_TITLE
    f.wait_text(12, "KEEP THE FOUR SHIELD GENERATORS", PEN_LABEL)
    f.wait_text(50, "PRESS FIRE TO START", PEN_LABEL)
    volumes = set()
    for _ in range(50):
        f.frames(1)
        regs = c.psg_regs()
        assert regs[R_MIXER] & 0x3F == 0x38, hex(regs[R_MIXER])    # tones, no noise
        volumes.add(regs[R_VOL_A])
    assert max(volumes) > 8 and len(volumes) > 2, volumes
    print("title and music: ok")

    # After a while the page turns to the high scores.
    f.frames(PAGE_FRAMES)
    f.wait_text(12, "HIGH SCORES", PEN_LABEL, frames=200)
    f.wait_text(19, "1. SHD  003000", PEN_DIGITS)
    f.wait_text(43, "5. ZAP  001000", PEN_DIGITS)
    print("high score page: ok")

    # Start: time, score, a bolt with its sound.
    g.start()
    f.screen = None
    assert g.word("TIME_SECS") == PLANET_TIME and g.word("SCORE") == 0
    f.wait_text(33, "3:00", PEN_DIGITS, x=28)
    f.wait_text(33, "00000", PEN_DIGITS, x=100)
    secs = g.word("TIME_SECS")
    f.frames(500)
    assert secs - g.word("TIME_SECS") in (9, 10, 11), (secs, g.word("TIME_SECS"))
    c.key_down(" ")
    shot = False
    for _ in range(8):
        f.frames(1)
        regs = c.psg_regs()
        period = regs[R_PERIOD_C] | (regs[R_PERIOD_C + 1] & 15) << 8
        shot |= regs[R_VOL_C] > 0 and 70 <= period <= 160
    c.key_up(" ")
    assert shot, "no shot sound on channel C"
    print("countdown, score and shot sound: ok")

    # The time runs out with the shield up: planet clear, the enemies blow
    # up, a bonus of the energy plus a quarter of the charge.
    g.c.write_ram(g.sym["SPAWN_ON"], b"\x00")
    g.c.write_ram(g.sym["GOD_MODE"], b"\x01")
    g.c.write_ram(g.sym["ENEMIES"], bytes([1, 80, 0, 60, 1, 30, 0, 0]))
    g.c.write_ram(g.sym["TIME_SECS"], bytes([2, 0]))
    g.c.write_ram(g.sym["SCORE"], bytes([0, 0]))
    for _ in range(300):
        f.frames(1)
        if g.byte("GAME_OVER"):
            break
    assert g.byte("GAME_OVER") == GAME_OVER_CLEAR
    charge = g.bytes("GEN_CHARGE", 2 * NUM_GENS)
    bonus = g.byte("PL_ENERGY") + sum(charge[1::2]) // 4
    assert abs(g.word("BONUS") - bonus) <= 1, (g.word("BONUS"), bonus)
    assert g.word("SCORE") == g.word("BONUS")
    kinds = [g.byte("ENEMIES", i * EN_SIZE) for i in range(MAX_ENEMIES)]
    assert not [k for k in kinds if 0 < k < E_HOSTILE], kinds
    f.wait_text(33, "PLANET CLEAR!", PEN_GOOD)
    score = g.word("SCORE")
    f.wait_text(41, f"BONUS {score:05}0", PEN_DIGITS)
    f.wait_text(49, f"SCORE {score:05}0", PEN_DIGITS)
    print(f"planet clear: ok (bonus {score})")

    # On to the second planet (tests/test_planets.py); losing its shield
    # ends the game with the score so far, which makes the table: initials,
    # chosen with up/down and fire.
    for _ in range(1500):
        f.frames(1)
        if g.byte("PLANET_NUM") == 2 and g.byte("GAME_STATE") == ST_PLAY:
            break
    assert g.byte("PLANET_NUM") == 2 and g.word("SCORE") == score
    g.c.write_ram(g.sym["GEN_CHARGE"], bytes(2 * NUM_GENS))
    g.wait_state(ST_ENTRY, 600)
    f.screen = None
    rank = g.byte("HS_NEW")
    assert rank == 1, rank      # between 3000 and 2500
    f.wait_text(14, "A NEW HIGH SCORE!", PEN_GOOD)
    f.frames(10)
    f.press(cpc.KEY_DOWN)       # A -> .
    f.press(" ")
    f.press(cpc.KEY_UP)         # A -> B
    f.press(" ")
    f.press(cpc.KEY_UP)
    f.press(cpc.KEY_UP)         # A -> C
    f.press(" ")
    g.wait_state(ST_TITLE, 300)
    table = g.bytes("HS_TABLE", 25)
    entries = [(table[i * 5] | table[i * 5 + 1] << 8, table[i * 5 + 2:i * 5 + 5].decode())
               for i in range(5)]
    assert entries == [(300, "SHD"), (score, ".BC"), (250, "RUN"), (200, "CPC"), (150, "AMS")], entries
    f.wait_text(25, f"2. .BC  {score:05}0", PEN_GOOD)
    print("initials and table: ok")

    # A second game starts afresh; losing every generator ends it, and a
    # score of 0 goes straight back to the title.
    g.start()
    f.screen = None
    assert (g.word("SCORE"), g.byte("PL_ENERGY"), g.word("TIME_SECS"), g.byte("PL_SPARES"),
            g.byte("GAME_OVER")) == (0, 100, PLANET_TIME, 3, 0)
    g.c.write_ram(g.sym["SPAWN_ON"], b"\x00")
    g.c.write_ram(g.sym["ENEMIES"], bytes(EN_SIZE * MAX_ENEMIES))
    g.c.write_ram(g.sym["GEN_CHARGE"], bytes(2 * NUM_GENS))
    for _ in range(20):
        f.frames(1)
        if g.byte("GAME_OVER"):
            break
    assert g.byte("GAME_OVER") == GAME_OVER_SHIELD
    f.wait_text(33, "GAME OVER", PEN_BAD)
    f.wait_text(41, "THE SHIELD HAS FAILED", PEN_LABEL)
    x = g.word("PL_X")
    c.key_down(cpc.KEY_RIGHT)
    f.frames(20)
    c.key_up(cpc.KEY_RIGHT)
    assert g.word("PL_X") == x, "moved after the game ended"
    g.wait_state(ST_TITLE, 400)
    assert g.byte("HS_NEW") == 0xFF
    assert g.word("LATE_FLIPS") == 0, "late flips"
    print("shield down, back to the title: ok")
    print("game: ok, no late flips")


if __name__ == "__main__":
    test()
