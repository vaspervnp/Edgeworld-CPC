#!/usr/bin/env python3
"""Convert an indexed PNG (160 Mode 0 pixels wide) into CRTC screen layout.

The output holds the 8 pixel-line blocks one after the other: block L has
line L of every character row, rows*80 bytes, ready to copy to
page + L*#800. Also writes the palette (16 hardware colour bytes).

Usage: png2scr.py in.png out_prefix   -> out_prefix.scr, out_prefix.pal
"""
import sys
from PIL import Image

from cpcpal import mode0_byte, nearest_hw


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, out = sys.argv[1:]
    img = Image.open(src)
    if img.mode != "P":
        raise SystemExit(f"{src}: needs an indexed (P mode) image")
    w, h = img.size
    if w != 160 or h % 8:
        raise SystemExit(f"{src}: must be 160 pixels wide and a multiple of 8 high, got {w}x{h}")
    px = img.load()
    data = bytearray()
    for line in range(8):
        for row in range(h // 8):
            y = row * 8 + line
            for x in range(0, w, 2):
                a, b = px[x, y], px[x + 1, y]
                if a > 15 or b > 15:
                    raise SystemExit(f"{src}: pen above 15 at ({x},{y})")
                data.append(mode0_byte(a, b))
    raw = img.getpalette()[:48]
    raw += [0] * (48 - len(raw))
    pal = bytes(nearest_hw(tuple(raw[i * 3:i * 3 + 3])) for i in range(16))
    open(out + ".scr", "wb").write(data)
    open(out + ".pal", "wb").write(pal)
    print(f"{src}: {h // 8} rows, {len(data)} bytes")


if __name__ == "__main__":
    main()
