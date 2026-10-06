#!/usr/bin/env python3
"""Enemy test, on CRTC type 1: shooting enemies, being hit (mounted, on foot,
the Runner killed), jumping a crawler, bombs, rocks, energy cells, the
breach carrier, breach waves, the spawner and game over.

Enemies are placed straight into the game's enemy slots, with spawning off,
except where the spawner itself is tested. Every displayed frame is checked
pixel for pixel (test_screen.py), the ENERGY bar included.
"""
from test_player import Player, MODE_MOUNTED, MODE_FOOT, ABSENT
import cpc

DRIFTER, TRACKER, CRAWLER, THROWER, CARRIER, BOOM, CELL = range(1, 8)
EN_SIZE, MAX_ENEMIES = 8, 6
MS_SIZE, MAX_MISSILES = 7, 4
BOMB, ROCK = 1, 2
CRAWLER_Y, THROWER_Y, MOUNTED_Y = 90, 86, 73
INVULN = 40
AMBIENT_MAX = 4
POINTS = {DRIFTER: 1, TRACKER: 2, CRAWLER: 2, THROWER: 3, CARRIER: 20}


class Enemies(Player):
    def slots(self):
        raw = self.g.bytes("ENEMIES", EN_SIZE * MAX_ENEMIES)
        return [raw[i * EN_SIZE:(i + 1) * EN_SIZE] for i in range(MAX_ENEMIES)]

    def alive(self, *types):
        return [(s[0], s[1] | s[2] << 8, s[3]) for s in self.slots() if s[0] in types]

    def put(self, slot, kind, x, y, hp=1, timer=30, anim=0, drop=0):
        self.g.c.write_ram(self.g.sym["ENEMIES"] + slot * EN_SIZE,
                           bytes([kind, x & 255, (x >> 8) & 3, y, hp, timer, anim, drop]))

    def clear(self):
        self.g.c.write_ram(self.g.sym["ENEMIES"], bytes(EN_SIZE * MAX_ENEMIES + MS_SIZE * MAX_MISSILES))

    def missiles(self):
        raw = self.g.bytes("MISSILES", MS_SIZE * MAX_MISSILES)
        out = []
        for i in range(MAX_MISSILES):
            m = raw[i * MS_SIZE:(i + 1) * MS_SIZE]
            if m[0]:
                out.append((m[0], m[1] | m[2] << 8, (m[3] | m[4] << 8) / 4, (m[5] ^ 0x80) - 0x80,
                            (m[6] ^ 0x80) - 0x80))
        return out

    def poke(self, name, value):
        self.g.c.write_ram(self.g.sym[name], bytes([value]))

    def px(self):
        return int(self.x("PL_X"))

    def settle(self):
        """Wait out the invulnerability after a hit."""
        self.frames(2 * INVULN + 4)


def test():
    p = Enemies()
    c = p.g.c

    # A bolt kills a drifter coming at the Runner: points, an explosion.
    p.put(0, DRIFTER, p.px() + 60, MOUNTED_Y + 5)
    c.key_down(" ")
    for _ in range(30):
        p.frames(1)
        if not p.alive(DRIFTER):
            break
    c.key_up(" ")
    assert not p.alive(DRIFTER), "the drifter was not shot down"
    assert p.alive(BOOM) or p.alive(CELL)
    assert p.g.word("SCORE") == POINTS[DRIFTER]
    assert p.b("RN_HITS") == 0
    p.frames(30)
    p.clear()
    print("shoot a drifter: ok")

    # A drifter reaching the Runner: the Runner is hit, the drifter explodes;
    # then a moment when nothing hurts.
    p.put(0, DRIFTER, p.px() + 4, MOUNTED_Y + 5)
    p.frames(4)
    assert p.b("RN_HITS") == 1 and p.b("PL_ENERGY") == 96, (p.b("RN_HITS"), p.b("PL_ENERGY"))
    assert not p.alive(DRIFTER)
    p.put(1, CRAWLER, p.px() + 4, CRAWLER_Y, hp=2)
    p.frames(10)
    assert p.b("RN_HITS") == 1, "hurt while invulnerable"
    p.clear()
    p.settle()
    print("hit while mounted: ok")

    # Jump a crawler: ride at it and jump in time, and it passes underneath.
    c.key_down(cpc.KEY_RIGHT)
    p.frames(30)                        # up to speed
    p.put(0, CRAWLER, p.px() + 100, CRAWLER_Y, hp=2)
    while True:
        p.frames(1)
        crawler = p.alive(CRAWLER)[0]
        if (crawler[1] - (p.px() + 14)) % 1024 < 22:
            break
    p.press([cpc.KEY_UP], 4)
    p.frames(30)
    c.key_up(cpc.KEY_RIGHT)
    assert p.b("RN_HITS") == 1, "the jump did not clear the crawler"
    crawler = p.alive(CRAWLER)[0]
    assert (crawler[1] - p.px()) % 1024 > 512, "the crawler is not behind the Runner"
    p.clear()
    p.frames(60)
    print("jump a crawler: ok")

    # A crawler hits a Runner standing still.
    p.put(0, CRAWLER, p.px() + 30, CRAWLER_Y, hp=2)
    p.frames(60)
    assert p.b("RN_HITS") == 2
    p.clear()
    p.settle()
    print("crawler hit: ok")

    # Trackers sweep over the player and drop bombs straight down.
    p.put(0, TRACKER, p.px() + 40, 14, hp=2, timer=0, anim=56)   # about to swing over
    bombs = []
    for _ in range(300):
        p.frames(1)
        bombs += [m for m in p.missiles() if m[0] == BOMB]
        if p.b("RN_HITS") == 0:     # the third hit killed the Runner
            break
    assert bombs and all(m[3] == 0 and m[4] == 12 for m in bombs), bombs
    assert p.b("RN_STATE") == ABSENT and p.b("PL_MODE") == MODE_FOOT, "the Runner survived"
    energy = p.b("PL_ENERGY")
    assert energy == 100 - 3 * 4, energy
    p.clear()
    p.settle()
    print(f"tracker bombs, Runner killed, rider thrown off: ok (energy {energy})")

    # On foot: a bolt kills a crawler (a mounted one would fly over it).
    p.put(0, CRAWLER, p.px() + 60, CRAWLER_Y, hp=2)
    c.key_down(" ")
    for _ in range(80):
        p.frames(1)
        if not p.alive(CRAWLER):
            break
    c.key_up(" ")
    assert not p.alive(CRAWLER), "the crawler survived two bolts"
    p.frames(20)
    p.clear()
    print("shoot a crawler on foot: ok")

    # A thrower lobs a rock that comes down on the rider.
    energy = p.b("PL_ENERGY")
    p.put(0, THROWER, p.px() + 56, THROWER_Y, hp=3, timer=2)
    rocks = []
    for _ in range(80):
        p.frames(1)
        rocks += [m for m in p.missiles() if m[0] == ROCK]
        if p.b("PL_ENERGY") < energy:
            break
    assert rocks and rocks[0][3] == -2 and rocks[0][4] < 0, rocks[:3]
    assert min(r[2] for r in rocks) < THROWER_Y - 10, "the rock did not arc"
    assert p.b("PL_ENERGY") == energy - 10, "the rock missed"
    p.clear()
    p.settle()
    print("thrower's rock: ok")

    # An energy cell gives energy back.
    energy = p.b("PL_ENERGY")
    p.put(0, CELL, p.px() + 2, 80, timer=200)
    p.frames(20)
    assert p.b("PL_ENERGY") == min(100, energy + 25)
    assert not p.alive(CELL)
    print("energy cell: ok")

    # Two generators drained: the breach carrier comes; downing it leaves a
    # cell and rests the carriers for a while.
    for i in (1, 2):
        c.write_ram(p.g.sym["GEN_CHARGE"] + 2 * i, b"\x00\x00")
    p.poke("BREACH_NEW", 0)
    p.poke("SPAWN_ON", 1)
    p.frames(6)
    p.poke("SPAWN_ON", 0)
    carrier = p.alive(CARRIER)
    assert carrier and p.b("CARRIER_ALIVE") == 1, p.alive(*range(1, 8))
    p.clear()
    p.put(0, CARRIER, p.px() + 40, 82, hp=1, timer=60)
    p.poke("CARRIER_ALIVE", 1)
    score = p.g.word("SCORE")
    c.key_down(" ")
    for _ in range(40):
        p.frames(1)
        if not p.alive(CARRIER):
            break
    c.key_up(" ")
    assert not p.alive(CARRIER) and p.b("CARRIER_ALIVE") == 0 and p.b("CARRIER_COOL") > 200
    assert p.g.word("SCORE") == score + POINTS[CARRIER]
    p.frames(30)
    assert p.alive(CELL), "the carrier left no cell"
    p.clear()
    print("breach carrier: ok")

    # A breach sends a wave from the generator that drained.
    p.poke("BREACH_NEW", 0b0001)
    p.poke("SPAWN_ON", 1)
    p.frames(2)
    p.poke("SPAWN_ON", 0)
    wave = p.alive(DRIFTER, CRAWLER)
    gen_x = 32 * 4
    assert len(wave) == 3 and all(abs(x - gen_x) < 24 for _, x, _ in wave), wave
    assert p.b("BREACH_NEW") == 0
    p.clear()
    print("breach wave: ok")

    # The spawner keeps a few enemies coming, never more than AMBIENT_MAX.
    p.poke("SPAWN_ON", 1)
    p.poke("GOD_MODE", 1)
    most = 0
    kinds = set()
    for _ in range(1000):
        p.frames(1)
        hostile = p.alive(DRIFTER, TRACKER, CRAWLER, THROWER)
        most = max(most, len(hostile))
        kinds |= {k for k, _, _ in hostile}
    assert 3 <= most <= AMBIENT_MAX, most
    assert len(kinds) >= 3, kinds
    p.poke("SPAWN_ON", 0)
    p.poke("GOD_MODE", 0)
    p.clear()
    print(f"spawner: ok (up to {most} at once, kinds {sorted(kinds)})")

    # No energy left: game over, and the controls do nothing.
    p.settle()
    p.poke("PL_ENERGY", 5)
    p.put(0, DRIFTER, p.px(), 90)
    p.frames(6)
    assert p.b("PL_ENERGY") == 0 and p.b("GAME_OVER") == 1
    x = p.px()
    p.press([cpc.KEY_RIGHT], 20)
    assert p.px() == x, "moved after game over"
    assert p.g.word("LATE_FLIPS") == 0, "late flips"
    print("game over: ok")
    print("enemies: ok, no late flips")


if __name__ == "__main__":
    test()
