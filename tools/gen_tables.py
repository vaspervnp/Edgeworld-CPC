#!/usr/bin/env python3
"""Generate lookup tables.

out_prefix.mask: 256 bytes. For each Mode 0 screen byte, the AND mask that
keeps the screen where its pixels are pen 0 (transparent): #AA keeps the
left pixel, #55 the right one.

out_prefix.demo: the milestone 3 demo's enemy paths, 256 bytes each:
x (screen pixel + 12, so -12..164 fits in a byte) and y (top line, 8..90).

Usage: gen_tables.py out_prefix
"""
import math
import sys


def main(out):
    mask = bytearray()
    for b in range(256):
        left = b & 0xAA
        right = b & 0x55
        mask.append((0 if left else 0xAA) | (0 if right else 0x55))
    open(out + ".mask", "wb").write(mask)

    xs = bytes(round(12 + 76 + 88 * math.sin(2 * math.pi * i / 256)) for i in range(256))
    ys = bytes(round(49 + 41 * math.sin(2 * math.pi * i / 256)) for i in range(256))
    open(out + ".demo", "wb").write(xs + ys)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
