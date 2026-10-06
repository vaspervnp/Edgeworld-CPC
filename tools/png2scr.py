#!/usr/bin/env python3
"""Convert an indexed PNG (160 Mode 0 pixels wide) into CRTC screen layout.

The output holds the 8 pixel-line blocks one after the other: block L has
line L of every character row, rows*80 bytes, for page + L*#800. Each block
is run-length encoded (see rle()) and ends with a 0. Also writes the
palette (16 hardware colour bytes).

Usage: png2scr.py in.png out_prefix   -> out_prefix.rle, out_prefix.pal
"""
import sys
from PIL import Image

from cpcpal import mode0_byte, nearest_hw


def rle(data):
    """Control byte n: 1-127 = n literal bytes follow; 128+n = the next byte
    repeated n times (n 1-127); 0 = end."""
    out, lit, i = bytearray(), bytearray(), 0

    def flush():
        while lit:
            chunk = lit[:127]
            out.append(len(chunk))
            out.extend(chunk)
            del lit[:127]

    while i < len(data):
        run = 1
        while i + run < len(data) and data[i + run] == data[i] and run < 127:
            run += 1
        if run >= 3:
            flush()
            out += bytes([128 + run, data[i]])
            i += run
        else:
            lit.append(data[i])
            i += 1
    flush()
    out.append(0)
    return out


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
    packed = bytearray()
    for line in range(8):
        data = bytearray()
        for row in range(h // 8):
            y = row * 8 + line
            for x in range(0, w, 2):
                a, b = px[x, y], px[x + 1, y]
                if a > 15 or b > 15:
                    raise SystemExit(f"{src}: pen above 15 at ({x},{y})")
                data.append(mode0_byte(a, b))
        packed += rle(data)
    raw = img.getpalette()[:48]
    raw += [0] * (48 - len(raw))
    pal = bytes(nearest_hw(tuple(raw[i * 3:i * 3 + 3])) for i in range(16))
    open(out + ".rle", "wb").write(packed)
    open(out + ".pal", "wb").write(pal)
    print(f"{src}: {h // 8} rows, {len(packed)} bytes packed from {h * 80}")


if __name__ == "__main__":
    main()
