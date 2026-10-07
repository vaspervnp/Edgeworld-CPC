#!/usr/bin/env python3
"""Smoke test in Caprice32, a second emulator (with its own CRTC, gate
array and floppy controller emulation, the latter with real timing), as
far as possible from the headless one the tests use.

Boots the disc, takes screenshots of the splash screen, of the loading
screen, of the title, presses fire, takes one of the game a while later,
and quits. Needs the Caprice32 snap (the
`caprice32` snap's cap32 binary is run inside its confinement, so the disc
and the typed commands go through its home directory) and a display.

Usage: cap32_smoke.py disc.dsk out_dir [model [ram_kb]]
  model: 0 = CPC 464, 2 = CPC 6128 (default), 3 = CPC 6128 Plus;
  ram_kb: 128 (default), or 64 (the game should refuse to run)
"""
import glob
import os
import shutil
import subprocess
import sys

HOME = os.path.expanduser("~/snap/caprice32/current")
RUNNER = """#!/bin/bash
exec $SNAP/usr/bin/cap32 --cfg_file=$SNAP_USER_DATA/etc/cap32.cfg -O system.model=$1 \\
    -O system.ram_size=$2 -a "$(cat $SNAP_USER_DATA/autocmd.txt)" "$SNAP_USER_DATA/disk/smoke.dsk"
"""
WAIT = "x"          # a key the game ignores: typing it passes the time


def main(dsk, out, model="2", ram="128"):
    shots = os.path.join(HOME, "screenshots")
    for f in glob.glob(os.path.join(shots, "*.png")):
        os.remove(f)
    shutil.copy(dsk, os.path.join(HOME, "disk", "smoke.dsk"))
    with open(os.path.join(HOME, "smoke.sh"), "w") as f:
        f.write(RUNNER)
    os.chmod(os.path.join(HOME, "smoke.sh"), 0o755)
    shot = "\\(CAP32_SCRNSHOT)"
    boot = "\\(CPC_F1)" + "\n" * 40 if model == "3" else ""    # the Plus menu: BASIC
    cmd = (boot + 'RUN"SHIELD\n' + WAIT * 100 + shot + WAIT * 250 + shot + WAIT * 500 + shot
           + " " + WAIT * 300 + shot
           + "\\(CAP32_EXIT)")
    with open(os.path.join(HOME, "autocmd.txt"), "w") as f:
        f.write(cmd)
    subprocess.run(["snap", "run", "--shell", "caprice32.launcher", "-c",
                    f"$SNAP_USER_DATA/smoke.sh {model} {ram}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    os.makedirs(out, exist_ok=True)
    taken = sorted(glob.glob(os.path.join(shots, "*.png")))
    for name, path in zip(("splash", "loading", "title", "game"), taken):
        shutil.copy(path, os.path.join(out, f"model{model}_ram{ram}_{name}.png"))
    print(f"model {model}, {ram}K: {len(taken)} screenshots in {out}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
