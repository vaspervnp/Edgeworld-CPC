#!/usr/bin/env python3
"""Planets from disc, on CRTC type 1: the game's own disc code loads each
planet's bank image (build/planetN.bin) into extra RAM bank 7 and takes its
header (parameters, palette, sky) and foreground columns into base RAM.

Checks the first planet as booted, clearing it into the second (loaded
from disc meanwhile, score and spare Runners kept, every frame of the new
planet checked pixel for pixel in its own palette), a load with the disc
out (the border flashes and it keeps trying until the disc is back), the
title going back to the first planet, every planet in play (its frames
checked pixel for pixel) and the end of the last planet.
"""
import os

from harness import Game, ROOT, ST_TITLE, ST_PLAY, ST_ENTRY
from test_screen import Screen
from test_game import Flow, PEN_GOOD
import cpc

BANK7 = 7
HEADER, COL_FG, HEADER_SIZE = 0x1100, 0x1500, 52
GAME_OVER_CLEAR = 3
NUM_PLANETS = 4
BORDER_RED = 0x0C       # hardware colour of bright red, without bit 6


def planet_file(n):
    return open(os.path.join(ROOT, "build", f"planet{n}.bin"), "rb").read()


def check_loaded(g, n):
    data = planet_file(n)
    assert g.byte("CURRENT_PLANET") == n
    assert g.bank_bytes(BANK7, 0, len(data)) == data, f"bank 7 is not planet{n}.bin"
    header = data[HEADER:HEADER + HEADER_SIZE]
    assert g.bytes("PLANET", HEADER_SIZE) == header, "planet header not taken"
    assert g.bytes("COL_FG", 256) == data[COL_FG:COL_FG + 256], "col_fg not taken"
    assert g.bytes("SKY_SAVED", 3) == header[-3:]


def clear_planet(f):
    """Run the time out with the shield up; wait for the end message."""
    g = f.g
    g.c.write_ram(g.sym["SPAWN_ON"], b"\x00")
    g.c.write_ram(g.sym["ENEMIES"], bytes(8 * 6))
    g.c.write_ram(g.sym["TIME_SECS"], bytes([2, 0]))
    for _ in range(300):
        f.frames(1)
        if g.byte("GAME_OVER"):
            break
    assert g.byte("GAME_OVER") == GAME_OVER_CLEAR
    f.frames(2)                 # the bonus is added in the same game frame


def wait_planet(g, n, frames=1500):
    for _ in range(frames):
        g.c.run_frames(1)
        if (g.byte("PLANET_NUM"), g.byte("CURRENT_PLANET"), g.byte("GAME_STATE"),
                g.byte("GAME_OVER")) == (n, n, ST_PLAY, 0) and g.word("TIME_SECS"):
            g.c.run_frames(6)       # the picture comes back on
            return
    raise AssertionError(f"planet {n} did not start")


def test():
    f = Flow()
    g, c = f.g, f.c

    # Booted: planet 1 loaded by the game itself, the title on it.
    check_loaded(g, 1)
    assert g.byte("LOAD_TRIES") == 0
    print("first planet loaded at boot: ok")

    g.start()
    f.screen = None
    clear_planet(f)
    score = g.word("SCORE")
    spares = g.byte("PL_SPARES")
    wait_planet(g, 2)
    check_loaded(g, 2)
    header = planet_file(2)[HEADER:HEADER + HEADER_SIZE]
    assert g.word("TIME_SECS") in (header[0] | header[1] << 8, (header[0] | header[1] << 8) - 1)
    got = (g.word("SCORE"), g.byte("PL_SPARES"), g.byte("PL_ENERGY"))
    assert got == (score, spares, 100), (got, score, spares)
    assert g.bytes("PF_PALETTE", 16) != planet_file(1)[HEADER + 33:HEADER + 49]
    # every frame of the new planet, in its own palette and sky
    screen = Screen(g)
    pos = screen.check(g.word("SCROLL_POS"))
    c.key_down(" ")
    for _ in range(100):
        g.next_frame()
        pos = screen.check(pos)
    c.key_up(" ")
    print(f"planet 1 clear, planet 2 loaded: ok (score {score} kept)")

    # The disc out when the next load comes: it keeps trying, flashing the
    # border, and goes on when the disc is back.
    g.c.write_ram(g.sym["CURRENT_PLANET"], b"\x09")   # make the title reload
    c.write_ram(g.sym["SCORE"], bytes(2))            # no high score to enter
    c.write_ram(g.sym["GEN_CHARGE"], bytes(8))       # shield down: back to the title
    c.remove_disc()
    tries = 0
    for _ in range(1500):
        f.frames(1)
        tries = g.byte("LOAD_TRIES")
        if tries >= 3:
            break
    assert tries >= 3, "no retries without a disc"
    c.insert_disc(os.path.join(ROOT, "build", "shield.dsk"))
    g.wait_state(ST_TITLE, 1500)
    check_loaded(g, 1)
    assert g.byte("LOAD_TRIES") == 0
    print(f"disc out: retried {tries} times, loaded once it was back: ok")

    # Each planet in play: its own art, tiles, foreground and palette,
    # checked frame by frame while riding right, firing.
    for n in range(1, NUM_PLANETS + 1):
        c.write_ram(g.sym["FIRST_PLANET"], bytes([n]))
        g.start()
        c.write_ram(g.sym["GOD_MODE"], b"\x01")
        check_loaded(g, n)
        screen = Screen(g)
        pos = screen.check(g.word("SCROLL_POS"))
        c.key_down(cpc.KEY_RIGHT)
        c.key_down(" ")
        for _ in range(150):
            g.next_frame()
            pos = screen.check(pos)
        c.key_up(" ")
        c.key_up(cpc.KEY_RIGHT)
        c.write_ram(g.sym["GOD_MODE"], b"\x00")
        c.write_ram(g.sym["SCORE"], bytes(2))
        c.write_ram(g.sym["GEN_CHARGE"], bytes(8))   # shield down: back to the title
        g.wait_state(ST_TITLE, 1500)
        print(f"planet {n} in play: ok (scrolled to {pos})")

    # The last planet cleared: the end of the game.
    c.write_ram(g.sym["FIRST_PLANET"], bytes([NUM_PLANETS - 1]))
    g.start()
    f.screen = None
    clear_planet(f)
    wait_planet(g, NUM_PLANETS)
    f.screen = None
    clear_planet(f)
    f.wait_text(33, "EVERY PLANET IS SAFE!", PEN_GOOD)
    g.wait_state(ST_ENTRY, 600)
    assert g.word("LATE_FLIPS") == 0, "late flips"
    print("last planet clear, the end: ok")
    print("planets: ok, no late flips")


if __name__ == "__main__":
    test()
