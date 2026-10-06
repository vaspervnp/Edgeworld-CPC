#!/usr/bin/env python3
"""Build the game disc.

SHIELD.BAS (ASCII BASIC) lowers HIMEM below #4000 (BASIC only loads binary
files above it), pages each extra RAM bank in at #4000 (gate array RAM
configurations #C4 on) and loads its file there, then puts base RAM back and
runs GAME.BIN. The firmware leaves the extra banks alone, so the game finds
them filled.

The other files (the planets) go on the disc as they are: the game loads
them itself, with its own disc code, since the firmware is gone by then.

Usage: mkdisc.py out.dsk game.bin NAME=file ...
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

    lines = ["10 MEMORY &3FFF:MODE 0:BORDER 0:INK 0,0"]
    n = 20
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
        idsk(dsk, "-i", os.path.join(stage, name + ".BIN"), "-t", "1", "-c", "4000", "-e", "4000")
    idsk(dsk, "-i", os.path.join(stage, "GAME.BIN"), "-t", "1", "-c", "0200", "-e", "0200")
    print(f"{dsk}: SHIELD.BAS, {', '.join(n + '.BIN' for n in sorted(files))}, GAME.BIN")


if __name__ == "__main__":
    main()
