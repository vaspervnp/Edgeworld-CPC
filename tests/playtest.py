#!/usr/bin/env python3
"""Playtest bots for the "rolling demo" problem: the game must not play
itself. Each bot plays a whole game on the first planet in the headless
emulator, reading the game's state from RAM and pressing keys:

  idle     touches nothing                        -> must lose
  gunner   rides back and forth firing, never     -> must lose (shield down)
           recharges (cannot be hurt)
  keeper   recharges the weakest generator, over  -> must clear the planet
           and over (cannot be hurt)
  player   the keeper firing as it goes and at     -> reported
           trackers overhead; enemies can hurt it
  skilled  the player, also jumping crawlers and   -> reported
           turning to shoot what comes near

So holding the shield takes recharging, and recharging is enough when
nothing else interferes; how the real thing (enemies, Runner losses) goes
is reported for tuning.

Usage: playtest.py [--seed=N] [--planet=N] [bot ...]
  (default: all bots, planet 1; the seed changes the enemies)
"""
import sys

from harness import Game, ST_PLAY
import cpc

FPS = 25
NUM_GENS = 4
GEN_ENTRY = 5
MODE_MOUNTED, MODE_FOOT, MODE_MOUNTING, MODE_CHARGING = range(4)
RUNNER_IDLE, RUNNER_COMING = 1, 2
TRACKER, CRAWLER, THROWER, BOOM = 2, 3, 4, 6
PULSE_WINDOW = 24
FULL = 0xF000
MAP_W = 1024
END_NAMES = {1: "energy gone", 2: "shield down", 3: "planet clear"}


class Bot:
    def __init__(self, god, shoot=False, planet=1):
        self.g = Game(1, start=False)
        self.c = self.g.c
        self.c.write_ram(self.g.sym["FIRST_PLANET"], bytes([planet]))
        self.g.start()
        self.planet_time = self.g.word("PLANET_TIME")
        if god:
            self.c.write_ram(self.g.sym["GOD_MODE"], b"\x01")
        table = self.g.bytes("GEN_TABLE", NUM_GENS * GEN_ENTRY)
        self.gen_mid = [table[i * GEN_ENTRY] * 4 + 6 for i in range(NUM_GENS)]
        self.held = set()
        self.fire = (" ",) if shoot else ()
        self.target = None
        self.charged = False
        self.log = []

    def keys(self, *want):
        want = set(want)
        for k in self.held - want:
            self.c.key_up(k)
        for k in want - self.held:
            self.c.key_down(k)
        self.held = want

    def word(self, name):
        return self.g.word(name)

    def trackers_over(self, px, reach=24):
        """Trackers within reach pixels either side of x px."""
        raw = self.g.bytes("ENEMIES", 8 * 6)
        return [i for i in range(6) if raw[8 * i] == TRACKER
                and abs(self.towards((raw[8 * i + 1] | raw[8 * i + 2] << 8) - px)) < reach]

    def nearest_hostile(self, px):
        """(signed dx, y, type) of the nearest enemy that fights, or None."""
        raw = self.g.bytes("ENEMIES", 8 * 6)
        best = None
        for i in range(6):
            kind = raw[8 * i]
            if 0 < kind < BOOM:
                dx = self.towards((raw[8 * i + 1] | raw[8 * i + 2] << 8) + 4 - px)
                if best is None or abs(dx) < abs(best[0]):
                    best = (dx, raw[8 * i + 3], kind)
        return best

    def skilled(self, frame):
        """The keeper, defending itself: jumps crawlers when riding, and on
        foot turns to the nearest enemy and shoots it (up or diagonally at
        flying ones) before going on with the job."""
        g = self.g
        mode = g.byte("PL_MODE")
        px = self.word("PL_X") // 8
        if mode == MODE_MOUNTED:
            near = self.nearest_hostile(px + 8)
            face = -1 if g.byte("PL_FACE") else 1
            if near and near[2] == CRAWLER and 8 < near[0] * face < 30:
                self.keys(cpc.KEY_RIGHT if face > 0 else cpc.KEY_LEFT, cpc.KEY_UP)
                return
        elif mode in (MODE_FOOT, MODE_CHARGING):
            near = self.nearest_hostile(px + 4)
            # walkers on the ground are shot from afar, fliers when close
            reach = {CRAWLER: (50, 70), THROWER: (84, 90)}.get(near[2] if near else 0, (14, 28))
            if near and abs(near[0]) < reach[mode == MODE_FOOT]:
                if mode == MODE_CHARGING:
                    self.keys()                      # let go and fight
                    return
                dx, y, kind = near
                way = cpc.KEY_RIGHT if dx > 0 else cpc.KEY_LEFT
                tap = (" ",) if frame % 2 else ()
                if abs(dx) < 6:
                    self.keys(cpc.KEY_UP, *tap)      # straight up
                elif y < 66:
                    self.keys(cpc.KEY_UP, way, *tap)  # diagonally up
                else:
                    self.keys(way, *tap)
                return
        self.keeper(frame)

    def charges(self):
        raw = self.g.bytes("GEN_CHARGE", 2 * NUM_GENS)
        return [raw[2 * i] | raw[2 * i + 1] << 8 for i in range(NUM_GENS)]

    @staticmethod
    def towards(d):
        """Signed shortest distance round the planet."""
        return (d + MAP_W // 2) % MAP_W - MAP_W // 2

    def play(self, step):
        """Run the game to its end, calling step() every game frame."""
        frame = 0
        while self.g.byte("GAME_OVER") == 0:
            self.c.run_frames(2)
            frame += 1
            step(frame)
            if frame > 260 * FPS:
                raise AssertionError("the game did not end")
        self.keys()
        over = self.g.byte("GAME_OVER")
        left = self.word("TIME_SECS")
        return over, left, self.word("SCORE")

    # -- the bots --------------------------------------------------------

    def idle(self, frame):
        pass

    def gunner(self, frame):
        # ride a lap one way, then the other, firing
        lap = (frame // 300) % 2
        self.keys(cpc.KEY_RIGHT if lap == 0 else cpc.KEY_LEFT, " ")

    def keeper(self, frame):
        g = self.g
        mode = g.byte("PL_MODE")
        px = self.word("PL_X") // 8
        charge = self.charges()
        if self.target is None:
            self.target = min(range(NUM_GENS), key=lambda i: charge[i])
            self.charged = False
            self.log.append((frame, self.target, charge[self.target] >> 8))
        mid = self.gen_mid[self.target]
        if mode == MODE_MOUNTED:
            d = self.towards(mid - (px + 8))
            speed = g.byte("PL_SPEED")
            if abs(d) > 40:
                self.keys(cpc.KEY_RIGHT if d > 0 else cpc.KEY_LEFT, *self.fire)
            elif speed:
                self.keys()
            else:
                self.keys(cpc.KEY_DOWN, " ")        # get off
        elif mode == MODE_FOOT:
            if self.fire and self.trackers_over(px):
                # shoot the trackers overhead first (tapping: fire repeats on release)
                self.keys(cpc.KEY_UP, *(self.fire if frame % 2 else ()))
                return
            if not self.charged:
                d = self.towards(mid - (px + 4))
                if abs(d) > 2:
                    self.keys(cpc.KEY_RIGHT if d > 0 else cpc.KEY_LEFT, *self.fire)
                else:
                    self.keys(cpc.KEY_DOWN)
                return
            # charged: call the Runner and get on
            rn = g.byte("RN_STATE")
            if rn == RUNNER_IDLE and abs(self.towards(self.word("RN_X") // 8 + 4 - px)) <= 6:
                self.keys(cpc.KEY_DOWN, " ")
                self.target = None
            elif rn != RUNNER_COMING and frame % 8 == 0:
                self.keys("w")
            else:
                self.keys(*self.fire if frame % 2 else ())   # tap fire while waiting
        elif mode == MODE_CHARGING:
            if self.fire and self.trackers_over(px, 12):
                self.keys()                          # let go and deal with it
                return
            if charge[self.target] >= FULL:
                self.charged = True
                self.keys()                          # let go
                return
            pump = g.byte("PL_PULSE") >= PULSE_WINDOW and " " not in self.held
            self.keys(cpc.KEY_DOWN, " ") if pump else self.keys(cpc.KEY_DOWN)
        else:
            self.keys()


BOTS = {          # name: (god mode, shoots, must end with)
    "idle": (False, False, (1, 2)),
    "gunner": (True, True, (2,)),
    "keeper": (True, False, (3,)),
    "player": (False, True, None),
    "skilled": (False, True, None),
}


def main(names, seed=None, planet=1):
    failed = False
    for name in names:
        god, shoot, must = BOTS[name]
        bot = Bot(god, shoot, planet)
        play = {"player": bot.keeper}.get(name) or getattr(bot, name)
        if seed is not None:
            bot.c.write_ram(bot.g.sym["RAND_SEED"], bytes([seed & 255, seed >> 8 | 1]))
        over, left, score = bot.play(play)
        played = bot.planet_time - left
        verdict = "ok" if must is None or over in must else "WRONG"
        failed |= verdict == "WRONG"
        print(f"{name:7} {END_NAMES[over]:12} after {played // 60}:{played % 60:02}, "
              f"score {score * 10}, {verdict}")
        if name in ("keeper", "player", "skilled"):
            print(f"        recharges: {len(bot.log)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    opts = {"seed": None, "planet": 1}
    while args and args[0].startswith("--"):
        key, value = args.pop(0)[2:].split("=")
        opts[key] = int(value)
    main(args or list(BOTS), **opts)
