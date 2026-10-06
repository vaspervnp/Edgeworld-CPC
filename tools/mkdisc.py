#!/usr/bin/env python3
"""Build the game disc.

SHIELD.BAS (ASCII BASIC) lowers HIMEM below #4000 (BASIC only loads binary
files above it), pages each extra RAM bank in at #4000 (gate array
RAM configurations #C4 on) and loads its file there, then puts base RAM
back and runs GAME.BIN. The firmware leaves the extra banks alone, so the
game finds them filled.

Usage: mkdisc.py out.dsk build_dir   (needs iDSK on the PATH)
"""
import glob
import os
import re
import shutil
import subprocess
import sys


def idsk(*args):
    subprocess.run(["iDSK", *args], check=True, stdout=subprocess.DEVNULL)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    dsk, build = sys.argv[1:]
    banks = sorted(glob.glob(os.path.join(build, "sprites.bank*.bin")))
    stage = os.path.join(build, "disc")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)

    lines = ["10 MEMORY &3FFF:MODE 0:BORDER 0:INK 0,0"]
    n = 20
    names = []
    for path in banks:
        bank = int(re.search(r"bank(\d)\.bin$", path).group(1))
        name = f"SPR{bank}.BIN"
        shutil.copy(path, os.path.join(stage, name))
        names.append(name)
        lines.append(f'{n} OUT &7F00,&{0xC0 + bank:X}:LOAD"{name}",&4000')
        n += 10
    lines.append(f'{n} OUT &7F00,&C0:RUN"GAME.BIN"')
    with open(os.path.join(stage, "SHIELD.BAS"), "wb") as f:
        f.write(("\r\n".join(lines) + "\r\n").encode("ascii") + b"\x1a")
    shutil.copy(os.path.join(build, "shield.bin"), os.path.join(stage, "GAME.BIN"))

    if os.path.exists(dsk):
        os.remove(dsk)
    idsk(dsk, "-n")
    idsk(dsk, "-i", os.path.join(stage, "SHIELD.BAS"), "-t", "0")
    for name in names:
        idsk(dsk, "-i", os.path.join(stage, name), "-t", "1", "-c", "4000", "-e", "4000")
    idsk(dsk, "-i", os.path.join(stage, "GAME.BIN"), "-t", "1", "-c", "0200", "-e", "0200")
    print(f"{dsk}: SHIELD.BAS, {', '.join(names)}, GAME.BIN")


if __name__ == "__main__":
    main()
