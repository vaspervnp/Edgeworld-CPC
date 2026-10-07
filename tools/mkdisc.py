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
shows the loading screen (SCREEN=: 16K of screen memory, with its inks in
the same file name ending .inks, from tools/mkloading.py) in Mode 0 while
the rest loads: the inks first, so the picture comes in as it loads.

Usage: mkdisc.py out.dsk game.bin NAME=file ...
  SCREEN=...: the loading screen, loaded at &C000
  BANK4=..., BANK5=..., BANK6=...: loaded into that extra bank by SHIELD.BAS
  any other NAME=file: written as NAME.BIN   (needs iDSK on the PATH)
"""
import os
import re
import shutil
import subprocess
import sys


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
    if "SCREEN" in files:
        inks = open(os.path.splitext(files["SCREEN"])[0] + ".inks").read().strip().split(",")
        assert len(inks) == 16
        lines.append(f"{n} MODE 0:BORDER 0:" + ":".join(f"INK {i},{c}" for i, c in enumerate(inks)))
        lines.append(f'{n + 10} LOAD"SCREEN.BIN",&C000')
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
        load = "C000" if name == "SCREEN" else "4000"
        idsk(dsk, "-i", os.path.join(stage, name + ".BIN"), "-t", "1", "-c", load, "-e", load)
    idsk(dsk, "-i", os.path.join(stage, "GAME.BIN"), "-t", "1", "-c", "0200", "-e", "0200")
    print(f"{dsk}: SHIELD.BAS, {', '.join(n + '.BIN' for n in sorted(files))}, GAME.BIN")


if __name__ == "__main__":
    main()
