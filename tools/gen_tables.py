#!/usr/bin/env python3
"""Generate lookup tables.

out_prefix.mask: 256 bytes. For each Mode 0 screen byte, the AND mask that
keeps the screen where its pixels are pen 0 (transparent): #AA keeps the
left pixel, #55 the right one.

out_prefix.pixels: 256 bytes. For each sprite byte, the pixels it draws:
itself, but with pen 1 (opaque black in sprites, see tools/spritec.py) as
pen 0.

Usage: gen_tables.py out_prefix
"""
import sys


def main(out):
    mask = bytearray()
    for b in range(256):
        left = b & 0xAA
        right = b & 0x55
        mask.append((0 if left else 0xAA) | (0 if right else 0x55))
    open(out + ".mask", "wb").write(mask)
    pixels = bytearray()
    for b in range(256):
        if b & 0xAA == 0x80:        # left pixel pen 1
            b &= ~0x80
        if b & 0x55 == 0x40:        # right pixel pen 1
            b &= ~0x40
        pixels.append(b)
    open(out + ".pixels", "wb").write(pixels)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
