#!/usr/bin/env python3
"""Build the game disc.

SHIELD.BAS (ASCII BASIC) lowers HIMEM below #4000 (BASIC only loads binary
files above it), pages each extra RAM bank in at #4000 (gate array RAM
configurations #C4 on) and loads its file there, then puts base RAM back and
runs GAME.BIN. The firmware leaves the extra banks alone, so the game finds
them filled.

The other files (the planets) go on the disc as they are: the game loads
them itself, with its own disc code, since the firmware is gone by then.

It stops with a message on a machine without the extra 64K; otherwise it
first shows a splash screen (SPLASH=: 16K of screen memory, its inks from
the file of the same name ending .txt, the pen/firmware table) for 10
seconds or until Space is pressed, then shows the loading screen (SCREEN=: 16K of screen memory, with its inks in
the same file name ending .inks, from tools/mkloading.py) in Mode 0 while
the rest loads: the inks first, so the picture comes in as it loads.

Usage: mkdisc.py out.dsk game.bin NAME=file ...
  SPLASH=...: shown before anything loads, loaded at &C000
  SCREEN=...: the loading screen, loaded at &C000
  BANK4=..., BANK5=..., BANK6=...: loaded into that extra bank by SHIELD.BAS
  any other NAME=file: written as NAME.BIN   (needs iDSK on the PATH)
"""
import os
import re
import shutil
import subprocess
import sys


def read_inks(screen):
    """The 16 firmware inks of a screen: from name.inks (one line, commas),
    or from name.txt (a table: pen, firmware number, ...)."""
    base = os.path.splitext(screen)[0]
    if os.path.exists(base + ".inks"):
        inks = open(base + ".inks").read().strip().split(",")
    else:
        inks = [m.group(2) for m in re.finditer(r"(?m)^\s*(\d+)\s+(\d+)\s+&", open(base + ".txt").read())]
    assert len(inks) == 16, screen
    return [int(i) for i in inks]


def show(n, name, inks):
    """BASIC lines from n: Mode 0 with the inks, then the picture loaded."""
    return [f"{n} MODE 0:BORDER 0:" + ":".join(f"INK {i},{c}" for i, c in enumerate(inks)),
            f'{n + 10} LOAD"{name}.BIN",&C000']


def idsk(*args):
    subprocess.run(["iDSK", *args], check=True, stdout=subprocess.DEVNULL)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    dsk, game = sys.argv[1:3]
    files = dict(arg.split("=", 1) for arg in sys.argv[3:])
    stage = os.path.join(os.path.dirname(dsk), "disc")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)

    lines = [
        "10 MODE 1:BORDER 0:INK 0,0:INK 1,24:INK 2,20:INK 3,6:PAPER 0:PEN 1",
        "20 MEMORY &3FFF",
        # the extra 64K: a byte written with bank 4 paged in must not land in
        # base RAM (on a 64K machine the paging does nothing)
        "30 OUT &7F00,&C0:POKE &4000,0:OUT &7F00,&C4:POKE &4000,170:OUT &7F00,&C0",
        '40 IF PEEK(&4000)=170 THEN LOCATE 5,10:PRINT "Shieldrunner needs a CPC 6128,":'
        'LOCATE 5,11:PRINT "or a CPC with 64K more memory.":END',
    ]
    n = 50
    if "SPLASH" in files:
        lines += show(n, "SPLASH", read_inks(files["SPLASH"]))
        # 10 seconds (TIME counts 300 a second), or until Space (key 47)
        lines.append(f"{n + 20} T=TIME:WHILE TIME-T<3000 AND INKEY(47)=-1:WEND")
        n += 30
    if "SCREEN" in files:
        lines += show(n, "SCREEN", read_inks(files["SCREEN"]))
        n += 20
    for name in sorted(files):
        m = re.fullmatch(r"BANK([4-7])", name)
        if m:
            lines.append(f'{n} OUT &7F00,&{0xC0 + int(m.group(1)):X}:LOAD"{name}.BIN",&4000')
            n += 10
    lines.append(f'{n} OUT &7F00,&C0:RUN"GAME.BIN"')
    with open(os.path.join(stage, "SHIELD.BAS"), "wb") as f:
        f.write(("\r\n".join(lines) + "\r\n").encode("ascii") + b"\x1a")
    shutil.copy(game, os.path.join(stage, "GAME.BIN"))

    if os.path.exists(dsk):
        os.remove(dsk)
    idsk(dsk, "-n")
    idsk(dsk, "-i", os.path.join(stage, "SHIELD.BAS"), "-t", "0")
    for name, path in sorted(files.items()):
        shutil.copy(path, os.path.join(stage, name + ".BIN"))
        load = "C000" if name in ("SCREEN", "SPLASH") else "4000"
        idsk(dsk, "-i", os.path.join(stage, name + ".BIN"), "-t", "1", "-c", load, "-e", load)
    idsk(dsk, "-i", os.path.join(stage, "GAME.BIN"), "-t", "1", "-c", "0200", "-e", "0200")
    print(f"{dsk}: SHIELD.BAS, {', '.join(n + '.BIN' for n in sorted(files))}, GAME.BIN")


if __name__ == "__main__":
    main()
