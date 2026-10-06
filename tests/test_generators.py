#!/usr/bin/env python3
"""Generator test, on CRTC type 1: drain, unstable and drained states on the
radar and the core, breaches, and the recharge minigame.

Checks the game's state while checking every displayed frame pixel for
pixel (test_screen.py), which covers the radar dots, the SHIELD gauge and
the generator core's colour.
"""
from harness import Game
from test_player import Player, MODE_FOOT
import cpc

NUM_GENS, GEN_ENTRY = 4, 5
UNSTABLE = 0x6000
STABLE, UNSTABLE_STATE, DRAINED = 0, 1, 2
DOT_STABLE, DOT_UNSTABLE, DOT_DRAINED, DOT_OFF = 0xF0, 0x3C, 0xFC, 0xC0
CORE_STABLE, CORE_FLASH, CORE_DRAINED, CORE_PULSE, CORE_STALL = 0x52, (0x4A, 0x4E), 0x5C, 0x4B, 0x4C
MODE_CHARGING = 3
CHARGE_SLOW, PUMP, STALL_FRAMES, PULSE_WINDOW = 120, 6000, 25, 24


class Gens(Player):
    def table(self):
        t = self.g.bytes("GEN_TABLE", NUM_GENS * GEN_ENTRY)
        return [(t[i * 5], t[i * 5 + 1] | t[i * 5 + 2] << 8) for i in range(NUM_GENS)]

    def charges(self):
        c = self.g.bytes("GEN_CHARGE", 2 * NUM_GENS)
        return [c[2 * i] | c[2 * i + 1] << 8 for i in range(NUM_GENS)]

    def set_charge(self, i, value):
        self.g.c.write_ram(self.g.sym["GEN_CHARGE"] + 2 * i, bytes([value & 255, value >> 8]))

    def states(self):
        return list(self.g.bytes("GEN_STATE", NUM_GENS))

    def dots(self):
        return list(self.g.bytes("DOT_SHOWN", NUM_GENS))

    def game_frames(self, n):
        """Run n game frames (flips), checking every picture; return them."""
        f0 = self.g.word("FLIPS")
        while (self.g.word("FLIPS") - f0) & 0xFFFF < n:
            self.frames(1)
        return (self.g.word("FLIPS") - f0) & 0xFFFF


def test():
    p = Gens()
    table = p.table()

    # Drain: each generator loses its rate every game frame.
    c0 = p.charges()
    n = p.game_frames(50)
    c1 = p.charges()
    for i, (col, rate) in enumerate(table):
        lost = c0[i] - c1[i]
        assert abs(lost - rate * n) <= rate, f"generator {i}: lost {lost}, expected {rate * n}"
    assert p.states() == [STABLE] * 4 and p.dots() == [DOT_STABLE] * 4
    print(f"drain: ok ({n} frames, rates {[r for _, r in table]})")

    # Unstable: the radar dot flashes; the core too when it is in view.
    p.set_charge(0, UNSTABLE - 200)     # generator 0 is the one in view
    p.frames(4)
    seen_dots, seen_cores = set(), set()
    for _ in range(40):
        p.frames(1)
        seen_dots.add(p.dots()[0])
        seen_cores.add(p.b("CORE_NOW"))
    assert p.states()[0] == UNSTABLE_STATE
    assert seen_dots == {DOT_UNSTABLE, DOT_OFF}, seen_dots
    assert seen_cores == set(CORE_FLASH), [hex(c) for c in seen_cores]
    print("unstable: ok")

    # Drained: a breach, a red dot, a red core.
    p.set_charge(0, 300)
    p.set_charge(2, 100)
    p.game_frames(40)
    assert p.charges()[0] == 0 and p.charges()[2] == 0
    assert p.states()[0] == DRAINED and p.states()[2] == DRAINED
    assert p.dots()[0] == DOT_DRAINED and p.dots()[2] == DOT_DRAINED
    assert p.b("BREACHES") == 2 and p.b("BREACH_NEW") == 0b101
    assert p.b("CORE_NOW") == CORE_DRAINED
    print("breach: ok")

    # Recharge: get off, walk to generator 0, hold down.
    col0 = table[0][0]
    middle = col0 * 4 + 6
    p.press([cpc.KEY_DOWN, " "])
    p.frames(4)
    assert p.b("PL_MODE") == MODE_FOOT
    p.g.c.key_down(cpc.KEY_RIGHT)
    while p.x("PL_X") + 4 < middle - 2:
        p.frames(1)
    p.g.c.key_up(cpc.KEY_RIGHT)
    p.frames(4)
    p.g.c.key_down(cpc.KEY_DOWN)
    p.frames(4)
    assert p.b("PL_MODE") == MODE_CHARGING and p.b("PL_GEN") == 0, "did not plug in"
    assert p.shown_frames("rider_up_r", "rider_up_l")
    # slow charge, and a drained generator comes back
    c0 = p.charges()[0]
    n = p.game_frames(20)
    gained = p.charges()[0] - c0
    assert abs(gained - CHARGE_SLOW * n) <= CHARGE_SLOW, f"gained {gained} in {n} frames"
    assert p.states()[0] == UNSTABLE_STATE
    print(f"charging: ok (+{gained} in {n} frames)")

    # Pump in time: fire while the core flashes white.
    while p.b("PL_PULSE") < PULSE_WINDOW + 1 or p.b("PL_PULSE") > PULSE_WINDOW + 3:
        p.frames(1)
    assert p.b("CORE_NOW") == CORE_PULSE
    c0 = p.charges()[0]
    p.press([" "], 3)
    gained = p.charges()[0] - c0
    assert PUMP <= gained <= PUMP + 3 * CHARGE_SLOW, f"pump gave {gained}"
    assert p.b("PL_STALL") == 0
    print(f"pump in time: ok (+{gained})")

    # Pump out of time: a stall, no charge for a second.
    while not 2 <= p.b("PL_PULSE") <= 12:
        p.frames(1)
    p.press([" "], 3)
    assert p.b("PL_STALL") > 0 and p.b("CORE_NOW") == CORE_STALL
    c0 = p.charges()[0]
    p.game_frames(STALL_FRAMES - 6)
    assert p.charges()[0] == c0, "charged while stalled"
    p.game_frames(10)
    assert p.charges()[0] > c0, "did not charge again after the stall"
    print("pump out of time: ok (stalled)")

    # Let go: back on foot, and the generator drains again.
    p.g.c.key_up(cpc.KEY_DOWN)
    p.frames(6)
    assert p.b("PL_MODE") == MODE_FOOT
    c0 = p.charges()[0]
    p.game_frames(10)
    assert p.charges()[0] < c0
    print("let go: ok")
    assert p.g.word("LATE_FLIPS") == 0, "late flips"
    print("generators: ok, no late flips")


if __name__ == "__main__":
    test()
