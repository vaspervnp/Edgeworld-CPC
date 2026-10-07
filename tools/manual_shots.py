#!/usr/bin/env python3
"""Screenshots for the manuals (docs/manual/), taken from build/shield.dsk in
the headless emulator (tests/harness.py), each scene set up by driving the
game and, where that would take long, by writing its RAM. Also draws the
gallery of the Runner, the rider and the enemies from the sprite sheet.

Usage: manual_shots.py out_dir
"""
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import harness  # noqa: E402
from harness import Game, DSK, SPLASH, ST_TITLE, ST_PLAY, ST_ENTRY  # noqa: E402
cpc = harness.cpc

CROP = (32, 20, 736, 524)       # the picture, with a little border round it
NUM_GENS, EN_SIZE = 4, 8
DRIFTER, TRACKER, CRAWLER, THROWER, CARRIER = 1, 2, 3, 4, 5


def save(c, out, name):
    c.image(aspect=True).convert("RGB").crop(CROP).save(os.path.join(out, name + ".png"))
    print(name)


def put(g, slot, kind, dx, y, hp=50, timer=30):
    """An enemy dx pixels right of the player."""
    x = (g.word("PL_X") // 8 + dx) & 1023
    g.c.write_ram(g.sym["ENEMIES"] + slot * EN_SIZE, bytes([kind, x & 255, x >> 8, y, hp, timer, 0, 0]))


def loading_screens(out):
    """The splash screen, then the loading screen, as the disc boots."""
    c = cpc.CPC()
    c.crtc_type = 1
    c.run_frames(150)
    c.insert_disc(DSK)
    c.type_text('RUN"SHIELD\n')
    splash = open(SPLASH, "rb").read()
    loading = open(os.path.join(ROOT, "build", "loading.bin"), "rb").read()
    for _ in range(400):
        c.run_frames(5)
        if bytes(c.read_ram(0xC000, len(splash))) == splash:
            break
    c.run_frames(10)
    save(c, out, "splash")
    c.key_down(" ")
    c.run_frames(6)
    c.key_up(" ")
    for _ in range(400):
        c.run_frames(5)
        if bytes(c.read_ram(0xC000, len(loading))) == loading:
            break
    c.run_frames(10)
    save(c, out, "loading")


def title_pages(out):
    g = Game(start=False)
    g.c.run_frames(40)
    save(g.c, out, "title")
    for _ in range(700):            # the page turns to the high scores
        g.c.run_frames(1)
        if g.byte("TITLE_PAGE"):
            break
    g.c.run_frames(20)
    save(g.c, out, "hiscores")


def riding(out):
    g = Game()
    c = g.c
    c.write_ram(g.sym["SPAWN_ON"], b"\x00")
    c.write_ram(g.sym["GOD_MODE"], b"\x01")
    c.key_down(cpc.KEY_RIGHT)
    c.run_frames(80)
    put(g, 0, DRIFTER, 70, 40)
    put(g, 1, TRACKER, 30, 14)
    put(g, 2, CRAWLER, 110, 90)
    c.key_down(" ")
    c.run_frames(14)
    save(c, out, "riding")
    # a jump over a crawler
    c.key_up(" ")
    put(g, 2, CRAWLER, 40, 90)
    c.key_down(cpc.KEY_UP)
    c.run_frames(16)
    c.key_up(cpc.KEY_UP)
    save(c, out, "jump")
    # the HUD close up
    c.image(aspect=True).convert("RGB").crop((64, 360, 704, 496)).save(os.path.join(out, "hud.png"))
    print("hud")


def charging(out):
    g = Game()
    c = g.c
    c.write_ram(g.sym["SPAWN_ON"], b"\x00")
    table = g.bytes("GEN_TABLE", NUM_GENS * 5)
    middle = table[0] * 4 + 6
    c.key_down(cpc.KEY_DOWN); c.key_down(" ")
    c.run_frames(6)
    c.key_up(cpc.KEY_DOWN); c.key_up(" ")
    c.run_frames(6)
    c.key_down(cpc.KEY_RIGHT)
    while g.word("PL_X") // 8 + 4 < middle - 2:
        c.run_frames(1)
    c.key_up(cpc.KEY_RIGHT)
    c.run_frames(4)
    c.key_down(cpc.KEY_DOWN)
    for _ in range(200):            # the core flashing white: the time to pump
        c.run_frames(1)
        if g.byte("PL_PULSE") >= 26:
            break
    save(c, out, "charging")
    c.key_up(cpc.KEY_DOWN)


def breach(out):
    g = Game()
    c = g.c
    c.write_ram(g.sym["SPAWN_ON"], b"\x00")
    c.write_ram(g.sym["GOD_MODE"], b"\x01")
    c.run_frames(20)
    # two generators drained: the alarm, and the breach carrier comes
    charge = bytearray(g.bytes("GEN_CHARGE", 2 * NUM_GENS))
    charge[4:8] = bytes(4)
    c.write_ram(g.sym["GEN_CHARGE"], bytes(charge))
    c.run_frames(30)
    put(g, 0, CARRIER, 30, 10, hp=12)
    put(g, 1, THROWER, 85, 86)
    put(g, 2, DRIFTER, -20, 50)
    c.key_down(" ")
    c.run_frames(20)
    c.key_up(" ")
    save(c, out, "breach")


def pause_clear_entry(out):
    g = Game()
    c = g.c
    c.write_ram(g.sym["SPAWN_ON"], b"\x00")
    c.run_frames(30)
    c.key_down("p"); c.run_frames(6); c.key_up("p")
    c.run_frames(20)
    save(c, out, "pause")
    c.key_down("p"); c.run_frames(6); c.key_up("p")
    c.run_frames(20)
    # the time runs out with the shield up: planet clear
    c.write_ram(g.sym["TIME_SECS"], bytes([2, 0]))
    for _ in range(600):
        c.run_frames(1)
        if g.byte("GAME_OVER"):
            break
    c.run_frames(60)
    save(c, out, "clear")
    # the next planet; its shield lost with a score: initials
    for _ in range(2000):
        c.run_frames(1)
        if g.byte("PLANET_NUM") == 2 and g.byte("GAME_STATE") == ST_PLAY:
            break
    c.run_frames(40)
    c.write_ram(g.sym["SCORE"], bytes([0x2C, 0x01]))     # 300: 3000 shown
    c.write_ram(g.sym["GEN_CHARGE"], bytes(2 * NUM_GENS))
    g.wait_state(ST_ENTRY, 900)
    c.run_frames(30)
    c.key_down(cpc.KEY_UP); c.run_frames(6); c.key_up(cpc.KEY_UP)
    c.run_frames(10)
    save(c, out, "entry")


def gallery(out):
    """The Runner (ridden), the rider and the enemies, from the sprite sheet,
    4 times as large, with Mode 0's wide pixels."""
    sheet = Image.open(os.path.join(ROOT, "assets", "sprites.png"))
    frames = {f["name"]: f for f in json.load(open(os.path.join(ROOT, "assets", "sprites.json")))}
    pal = sheet.getpalette()

    def frame(name):
        f = frames[name]
        img = Image.new("RGB", (f["w"], f["h"]), (30, 30, 46))
        px = img.load()
        for y in range(f["h"]):
            for x in range(f["w"]):
                p = sheet.getpixel((f["x"] + x, f["y"] + y))
                if p:
                    px[x, y] = tuple(pal[p * 3:p * 3 + 3])
        return img.resize((f["w"] * 8, f["h"] * 4), Image.NEAREST)

    def runner():
        body, legs = frames["mounted_r"], frames["legs0_r"]
        img = Image.new("RGB", (24, 39), (30, 30, 46))
        for part, dy in ((body, 0), (legs, 3 + 14)):
            pimg = frame(part["name"]).resize((part["w"], part["h"]), Image.NEAREST)
            mask = Image.new("L", (part["w"], part["h"]))
            mask.putdata([255 if sheet.getpixel((part["x"] + x, y)) else 0
                          for y in range(part["h"]) for x in range(part["w"])])
            img.paste(pimg, (part.get("dx", 0), dy), mask)
        return img.resize((24 * 8, 39 * 4), Image.NEAREST)

    items = [runner(), frame("rider_stand_r")] + [frame(n) for n in (
        "drifter0", "tracker0", "crawler0", "thrower0", "carrier0", "cell")]
    for name, img in zip(("g_runner", "g_rider", "g_drifter", "g_tracker", "g_crawler",
                          "g_thrower", "g_carrier", "g_cell"), items):
        img.save(os.path.join(out, name + ".png"))
        print(name)


def main(out):
    os.makedirs(out, exist_ok=True)
    gallery(out)
    loading_screens(out)
    title_pages(out)
    riding(out)
    charging(out)
    breach(out)
    pause_clear_entry(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
