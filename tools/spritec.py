#!/usr/bin/env python3
"""Compile a sprite sheet into code and data for the 6128's extra RAM banks.

Each frame (listed in the JSON, in order) gets, for each of its two pixel
alignments (as drawn, W bytes per line; shifted one pixel right, W + 1):

- raw pixel data, line after line, for the engine's generic masked drawing
  (used when the sprite is clipped at the view's edge), opaque black as
  pen 1 (which sprites never use otherwise: it is the sky);
- a compiled drawing routine: straight-line Z80 that writes each byte of the
  sprite at HL. Fully opaque bytes are a single LD (HL),n, bytes with pen 0
  pixels are masked with immediates (LD A,(HL) : AND m : OR p : LD (HL),A),
  fully transparent bytes cost nothing. Lines are walked in whichever
  direction is closer, so there is no rewind; moving along a line is INC HL
  / DEC HL (or ADD HL,BC for longer hops), so a line may cross a 256-byte
  page; moving down a line is
  LD A,H : ADD A,8 : LD H,A : AND #38 : CALL Z,row_cross, where row_cross
  (at the start of every bank) moves to the next character row of the
  screen ring.

The routines expect HL = the screen address of the sprite's top-left byte,
no clipping, and no line running past the end of the 2K screen ring (the
engine checks); they change A, BC and HL.

Frames are packed into 16K banks (paged in at #4000 with gate array RAM
configurations #C4-#C7), in order. Writes out_prefix.bank4.bin onwards,
out_prefix.inc (SPR_<NAME> frame numbers, sizes) and out_prefix.frames (the
frame table spr_frames, FRAME_SIZE bytes per frame: W, height, raw data
unshifted and shifted, routines unshifted and shifted, RAM configuration,
spare).

Sheet pens 0-15 are the playfield's, pen 0 transparent; pen OPAQUE_BLACK
(16) is black drawn opaque, for outlines and dark shading.

Usage: spritec.py sheet.png frames.json out_prefix
"""
import json
import sys
from PIL import Image

from cpcpal import mode0_byte

BANK_BASE = 0x4000
BANK_SIZE = 0x4000
FIRST_CONFIG = 0xC4         # banks 4-7
MAX_BANKS = 4
OPAQUE_BLACK = 16
RAW_BLACK = 1               # opaque black in raw data (gen_tables.py)

# row_cross: H holds page + #40 | ring block (the line bits wrapped past 7).
# Back to line 0 and on 80 bytes, carrying into the ring block, wrapping it.
ROW_CROSS = bytes([
    0x7C,             # ld a,h
    0xD6, 0x40,       # sub #40
    0x67,             # ld h,a
    0x7D,             # ld a,l
    0xC6, 80,         # add a,80
    0x6F,             # ld l,a
    0xD0,             # ret nc
    0x7C,             # ld a,h
    0x3C,             # inc a
    0xAC,             # xor h
    0xE6, 0x07,       # and 7
    0xAC,             # xor h
    0x67,             # ld h,a
    0xC9,             # ret
])


def masked_bytes(rows, black=0):
    """Rows of pens -> rows of (pixel byte, mask byte), opaque black as
    pen black."""
    out = []
    for row in rows:
        line = []
        for x in range(0, len(row), 2):
            a, b = row[x], row[x + 1]
            if a == 1 or b == 1:
                raise SystemExit("pen 1 (the sky) in a sprite")
            mask = (0xAA if a == 0 else 0) | (0x55 if b == 0 else 0)
            a, b = (black if p == OPAQUE_BLACK else p for p in (a, b))
            line.append((mode0_byte(a, b), mask))
        out.append(line)
    return out


def compile_frame(lines, row_cross):
    """Z80 code drawing the lines of (pixel, mask) bytes at HL."""
    code = bytearray()
    cursor = 0
    for y, line in enumerate(lines):
        targets = [x for x, (p, m) in enumerate(line) if m != 0xFF]
        if targets:
            if abs(cursor - targets[0]) > abs(cursor - targets[-1]):
                targets.reverse()
            for x in targets:
                d = x - cursor
                if abs(d) <= 3:
                    code += bytes([0x23 if d > 0 else 0x2B]) * abs(d)   # inc hl / dec hl
                else:
                    code += bytes([0x01, d & 0xFF, (d >> 8) & 0xFF, 0x09])  # ld bc,d : add hl,bc
                cursor = x
                p, m = line[x]
                if m == 0:
                    code += bytes([0x36, p])                        # ld (hl),p
                else:
                    code += bytes([0x7E, 0xE6, m, 0xF6, p, 0x77])   # ld a,(hl) : and m : or p : ld (hl),a
        if y < len(lines) - 1:
            code += bytes([0x7C, 0xC6, 0x08, 0x67, 0xE6, 0x38,      # ld a,h : add a,8 : ld h,a : and #38
                           0xCC, row_cross & 0xFF, row_cross >> 8])  # call z,row_cross
    code.append(0xC9)
    return code


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    sheet, frames_json, out = sys.argv[1:]
    px = Image.open(sheet).load()
    frames = json.load(open(frames_json))

    banks = [bytearray(ROW_CROSS)]
    table = []
    for f in frames:
        w, h = f["w"], f["h"]
        if w % 2:
            raise SystemExit(f"{f['name']}: width {w} is odd")
        rows = [[px[f["x"] + x, f["y"] + y] for x in range(w)] for y in range(h)]
        shifted = [[0] + r + [0] for r in rows]
        versions = [masked_bytes(rows), masked_bytes(shifted)]
        raws = [masked_bytes(rows, RAW_BLACK), masked_bytes(shifted, RAW_BLACK)]
        # place raw data first, then code (which needs its own address only
        # for row_cross, at the bank start)
        blob, raw_offsets, code_offsets = bytearray(), [], []
        for v in raws:
            raw_offsets.append(len(blob))
            for line in v:
                blob += bytes(p for p, m in line)
        for v in versions:
            code_offsets.append(len(blob))
            blob += compile_frame(v, BANK_BASE)
        if len(blob) > BANK_SIZE - len(ROW_CROSS):
            raise SystemExit(f"{f['name']}: {len(blob)} bytes does not fit a bank")
        if len(banks[-1]) + len(blob) > BANK_SIZE:
            if len(banks) == MAX_BANKS:
                raise SystemExit("sprites do not fit in the extra 64K")
            banks.append(bytearray(ROW_CROSS))
        base = BANK_BASE + len(banks[-1])
        banks[-1] += blob
        table.append((f["name"], w // 2, h, [base + o for o in raw_offsets],
                      [base + o for o in code_offsets], FIRST_CONFIG + len(banks) - 1))

    for i, data in enumerate(banks):
        open(f"{out}.bank{4 + i}.bin", "wb").write(data)
    with open(out + ".inc", "w") as fh:
        fh.write(f"; generated by spritec.py from {sheet}\n")
        for i, (name, *_) in enumerate(table):
            fh.write(f"SPR_{name.upper()} equ {i}\n")
        fh.write(f"NUM_SPRITE_FRAMES equ {len(table)}\n")
        fh.write(f"SPR_MAX_W equ {max(t[1] for t in table) + 1}\n")
        fh.write(f"SPRITE_BANKS equ {len(banks)}\n")
    with open(out + ".frames", "w") as fh:
        fh.write(f"; generated by spritec.py from {sheet}\n")
        fh.write("spr_frames:\n")
        for name, w, h, raw, code, config in table:
            fh.write(f"    db {w},{h} : dw #{raw[0]:04X},#{raw[1]:04X},#{code[0]:04X},#{code[1]:04X}"
                     f" : db #{config:02X},0  ; {name}\n")
    sizes = ", ".join(f"bank {4 + i} {len(b)} bytes" for i, b in enumerate(banks))
    print(f"{sheet}: {len(table)} frames; {sizes}")


if __name__ == "__main__":
    main()
