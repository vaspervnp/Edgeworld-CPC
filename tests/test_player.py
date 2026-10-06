#!/usr/bin/env python3
"""Player test: riding, jumping, shooting, dismounting, walking, whistling
and mounting, on CRTC type 1.

Drives the game with the keys and checks its state after each action, while
checking every displayed frame pixel for pixel as test_screen.py does
(sprites, foreground, HUD with the spare Runner icons).
"""
import os
import re

from harness import Game, ROOT
import cpc
from test_screen import Screen

FRAMES = {}
for line in open(os.path.join(ROOT, "build", "sprites.inc")):
    m = re.match(r"SPR_(\w+) equ (\d+)", line)
    if m:
        FRAMES[m.group(1).lower()] = int(m.group(2))

MODE_MOUNTED, MODE_FOOT, MODE_MOUNTING = 0, 1, 2
RIDDEN, IDLE, COMING, ABSENT = 0, 1, 2, 3
MOUNTED_Y, JUMP_PEAK = 73, 24
VIEW_CX = 72
SHOT_SIZE, MAX_SHOTS = 6, 4


class Player:
    """The game on CRTC 1 with no enemies (spawning off), unless enemies."""
    def __init__(self, enemies=False):
        self.g = Game(1)
        if not enemies:
            self.g.c.write_ram(self.g.sym["SPAWN_ON"], b"\x00")
        self.screen = Screen(self.g)
        self.pos = self.screen.check(self.g.word("SCROLL_POS"))

    def frames(self, n):
        """Run n frames, checking each picture."""
        for _ in range(n):
            self.g.next_frame()
            self.pos = self.screen.check(self.pos)

    def press(self, keys, n=6):
        for k in keys:
            self.g.c.key_down(k)
        self.frames(n)
        for k in keys:
            self.g.c.key_up(k)

    def b(self, name):
        return self.g.byte(name)

    def x(self, name):
        return self.g.word(name) / 8

    def shown(self):
        """Records of the displayed buffer: (frame, x, y)."""
        return self.screen.buffers()[0][1]

    def shown_frames(self, *names):
        ids = {FRAMES[n] for n in names}
        return [r for r in self.shown() if r[0] in ids]

    def shots(self):
        raw = self.g.bytes("SHOTS", SHOT_SIZE * MAX_SHOTS)
        out = []
        for i in range(MAX_SHOTS):
            s = raw[i * SHOT_SIZE:(i + 1) * SHOT_SIZE]
            if s[0]:
                out.append((s[0], s[1] | s[2] << 8, s[3], (s[4] ^ 0x80) - 0x80, (s[5] ^ 0x80) - 0x80))
        return out

    def centred(self):
        return ((int(self.x("PL_X")) - VIEW_CX) >> 2) & 255 == self.g.word("SCROLL_POS") & 255


def test():
    p = Player()
    c = p.g.c
    mounted = [f"mounted{i}_{d}" for i in range(4) for d in "rl"]

    # Riding right: speeds up to 4 pixels a frame, the camera keeps up.
    x0 = p.x("PL_X")
    c.key_down(cpc.KEY_RIGHT)
    p.frames(60)
    assert p.b("PL_SPEED") == 32 and p.b("PL_FACE") == 0
    assert p.centred(), "camera not on the Runner"
    x1 = p.x("PL_X")
    p.frames(20)                # 10 game frames
    assert (p.x("PL_X") - x1) % 1024 == 40, "not riding at 4 pixels a frame"
    c.key_up(cpc.KEY_RIGHT)
    p.frames(60)
    assert p.b("PL_SPEED") == 0, "did not coast to a stop"
    print(f"ride: ok ({x0:.0f} -> {p.x('PL_X'):.0f})")

    # Jump: up and back down, highest JUMP_PEAK pixels up.
    ys = []
    c.key_down(cpc.KEY_UP)
    for i in range(40):
        p.frames(1)
        r = p.shown_frames(*mounted)
        assert len(r) == 1
        ys.append(r[0][2])
        if i == 4:              # the game reads the keys once a game frame
            c.key_up(cpc.KEY_UP)
    assert min(ys) == MOUNTED_Y - JUMP_PEAK and ys[-1] == MOUNTED_Y, f"jump: {ys}"
    assert p.b("PL_JUMP") == 0
    print(f"jump: ok (top {min(ys)})")

    # Fire: bolts fly forward 8 pixels a frame, 6 frames apart, leave the view.
    c.key_down(" ")
    p.frames(3)
    s = p.shots()
    assert len(s) == 1 and s[0][0] == FRAMES["shot_h"] and s[0][3:] == (8, 0), s
    x = s[0][1]
    p.frames(2)
    assert p.shots()[0][1] == (x + 8) % 1024
    p.frames(40)
    c.key_up(" ")
    assert 1 <= len(p.shots()) <= MAX_SHOTS
    p.frames(60)
    assert p.shots() == [], "bolts did not leave the view"
    # with up: diagonally up
    c.key_down(" ")
    c.key_down(cpc.KEY_UP)
    p.frames(3)
    c.key_up(" ")
    c.key_up(cpc.KEY_UP)
    s = p.shots()
    assert s and s[0][0] == FRAMES["shot_d"] and s[0][3:] == (6, -6), s
    assert p.b("PL_JUMP") == 0, "aiming up must not jump"
    p.frames(60)
    print("fire: ok")

    # Dismount: the Runner waits, the rider stands on the ground.
    rx = p.x("PL_X")
    scroll = p.g.word("SCROLL_POS")
    p.press([cpc.KEY_DOWN, " "])
    p.frames(4)
    assert p.b("PL_MODE") == MODE_FOOT and p.b("RN_STATE") == IDLE
    assert p.x("RN_X") == rx
    assert p.shown_frames("runner_stand_r") and p.shown_frames("rider_stand_r")
    assert p.shots() == [], "dismounting must not fire"
    # walk right: slowly, no scrolling, stopping at the edge of the view
    c.key_down(cpc.KEY_RIGHT)
    p.frames(20)
    assert abs(p.x("PL_X") - (rx + 4) - 10) <= 1, "not walking at 1 pixel a frame"
    p.frames(200)
    c.key_up(cpc.KEY_RIGHT)
    assert p.g.word("SCROLL_POS") == scroll, "the screen scrolled on foot"
    assert int(p.x("PL_X")) == (scroll * 4 + 150) % 1024, "rider left the view"
    # shoot straight up, and diagonally
    c.key_down(" ")
    c.key_down(cpc.KEY_UP)
    p.frames(6)                 # input shows up to 2 game frames later
    assert p.shown_frames("rider_up_r")
    s = p.shots()
    assert s and s[0][0] == FRAMES["shot_v"] and s[0][3:] == (0, -8), s
    c.key_down(cpc.KEY_LEFT)
    p.frames(14)
    c.key_up(cpc.KEY_LEFT)
    c.key_up(cpc.KEY_UP)
    c.key_up(" ")
    assert any(s[0] == FRAMES["shot_dl"] and s[3:] == (-6, -6) for s in p.shots()), p.shots()
    p.frames(40)
    print("on foot: ok")

    # Whistle: the waiting Runner runs over and waits by the rider.
    p.press(["w"], 4)
    assert p.b("RN_STATE") == COMING
    p.frames(80)
    assert p.b("RN_STATE") == IDLE
    assert abs(p.x("RN_X") + 4 - p.x("PL_X")) <= 3
    assert p.shown_frames("runner_stand_l", "runner_stand_r")
    # mount: the camera pans back to the Runner, then the controls return
    p.press([cpc.KEY_DOWN, " "], 4)
    assert p.b("PL_MODE") in (MODE_MOUNTING, MODE_MOUNTED) and p.b("RN_STATE") == RIDDEN
    p.frames(80)
    assert p.b("PL_MODE") == MODE_MOUNTED and p.centred()
    print("whistle and mount: ok")

    # No Runner: whistling brings a spare from the edge of the view.
    p.press([cpc.KEY_DOWN, " "])
    p.frames(4)
    c.write_ram(p.g.sym["RN_STATE"], bytes([ABSENT]))
    p.frames(4)
    assert not p.shown_frames("runner_stand_r", "runner_stand_l")
    spares = p.b("PL_SPARES")
    p.press(["w"], 4)
    assert p.b("PL_SPARES") == spares - 1 and p.b("RN_STATE") == COMING
    p.frames(120)
    assert p.b("RN_STATE") == IDLE
    # use the rest up, then none comes
    while p.b("PL_SPARES"):
        c.write_ram(p.g.sym["RN_STATE"], bytes([ABSENT]))
        p.frames(2)
        p.press(["w"], 4)
    c.write_ram(p.g.sym["RN_STATE"], bytes([ABSENT]))
    p.frames(4)
    p.press(["w"], 4)
    p.frames(10)
    assert p.b("RN_STATE") == ABSENT and p.b("PL_SPARES") == 0
    print("spare Runners: ok")
    assert p.g.word("LATE_FLIPS") == 0, "late flips"
    print("player: ok, no late flips")


if __name__ == "__main__":
    test()
