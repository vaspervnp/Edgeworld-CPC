"""Shared helpers: boot build/shield.dsk in the headless CPC emulator and look
at what it displays.

The emulator lives in CPCEMU_DIR (default ~/cpcemu). Its framebuffer is
1024 pixels per 64 us line (16 per us, 4 per Mode 0 pixel), one row per
scanline, and holds hardware colour numbers (0-31).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.environ.get("CPCEMU_DIR", os.path.expanduser("~/cpcemu")))

import cpc  # noqa: E402

DSK = os.path.join(ROOT, "build", "shield.dsk")
SYM = os.path.join(ROOT, "build", "shield.sym")

FB_W = cpc.FB_WIDTH
X0 = 64                 # framebuffer x of the first displayed pixel
PIX = 4                 # framebuffer pixels per Mode 0 pixel
VIEW_W = 160            # Mode 0 pixels per line


def symbols():
    out = {}
    for line in open(SYM):
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("#"):
            out[parts[0]] = int(parts[1][1:], 16)
    return out


class Game:
    def __init__(self, crtc_type=1):
        self.sym = symbols()
        self.c = cpc.CPC()
        self.c.crtc_type = crtc_type
        self.c.run_frames(150)
        self.c.insert_disc(DSK)
        self.c.type_text('RUN"SHIELD\n')
        isr = self.sym["ISR"]
        vector = bytes([0xC3, isr & 0xFF, isr >> 8])
        for _ in range(3000):
            self.c.run_frames(1)
            if self.c.read_ram(0x38, 3) == vector and self.word("FLIPS") > 2:
                return
        raise AssertionError("game did not start")

    def byte(self, name, offset=0):
        return self.c.read_ram(self.sym[name] + offset, 1)[0]

    def word(self, name):
        lo, hi = self.c.read_ram(self.sym[name], 2)
        return lo | hi << 8

    def bytes(self, name, n):
        return self.c.read_ram(self.sym[name], n)

    def next_frame(self):
        """Run to just after the next VSYNC, when a whole frame is in the framebuffer."""
        # Wait for exactly n+1: the counter's two bytes are written one at a
        # time, so a carry briefly shows a half-updated value.
        target = (self.word("FRAME_COUNT") + 1) & 0xFFFF
        for _ in range(400):
            self.c.run_us(64)
            if self.word("FRAME_COUNT") == target:
                return
        raise AssertionError("no VSYNC")

    def frame_lines(self):
        """The framebuffer as a list of scanlines (bytes of hardware colours)."""
        fb = self.c.framebuffer()
        return [fb[y * FB_W:(y + 1) * FB_W] for y in range(cpc.FB_HEIGHT)]

    @staticmethod
    def pixels(line):
        """The 160 displayed Mode 0 pixels of a scanline."""
        return bytes(line[X0 + 1 + x * PIX] for x in range(VIEW_W))
