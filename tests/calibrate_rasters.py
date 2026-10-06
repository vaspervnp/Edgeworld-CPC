#!/usr/bin/env python3
"""Report where each raster colour change lands: scanline and position in
the line, in us from the start of the first displayed pixel (0-40 is the
visible picture, 40-64 the horizontal blank). Used to tune SKY1_DELAY
and SKY2_DELAY in src/system.asm; a change that lands in the
blank shows as "clean" and its exact position cannot be seen. Run it with
the delay under test set to 0 to see where the code lands unpadded.
"""
import sys

from harness import Game, X0, PIX

GREY, BLACK, BLUE, MAGENTA = 0x40 & 31, 0x54 & 31, 0x44 & 31, 0x58 & 31


def find_top(lines):
    """The HUD's grey rule is its line 8, i.e. line 144 from the top."""
    for y, line in enumerate(lines):
        if all(line[X0 + 1 + x * PIX] == GREY for x in range(160)):
            return y - 144
    raise SystemExit("HUD not found")


def change(lines, top, first, last, new, old):
    """First line in [first, last] with colour `new`; where it starts."""
    for y in range(top + first, top + last + 1):
        px = [lines[y][X0 + 1 + x * PIX] for x in range(160)]
        if new in px:
            xs = px.index(new)
            olds = [x for x in range(xs) if px[x] == old]
            if not olds:
                return y - top, "clean"
            return y - top, f"torn between {olds[-1] * 0.25:.2f} and {xs * 0.25:.2f} us"
    return None, "not visible in this view"


def main(crtc_type):
    g = Game(crtc_type)
    g.next_frame()
    lines = g.frame_lines()
    top = find_top(lines)
    print(f"CRTC {crtc_type}: playfield starts on framebuffer line {top}")
    print("  sky band 1:", *change(lines, top, 20, 60, BLUE, BLACK))
    print("  sky band 2:", *change(lines, top, 70, 110, MAGENTA, BLUE))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
