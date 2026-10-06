#!/usr/bin/env python3
"""Generate the sprite sheet.

The Runner (4 running frames and a standing one), its rider on foot
(standing, 2 walking frames, aiming up), the two together while mounted (4
frames: one sprite is cheaper than two), all facing right and mirrored to
face left; the enemies (drifter, tracker, crawler, rock thrower, breach
carrier, 2 frames each), their bombs and rocks, an explosion, an energy
cell; and the rider's bolts (horizontal, vertical, diagonal both ways).

Sprites share the playfield palette and use only its fixed pens (tools/pens.py);
pen 0 is transparent. Writes the sheet
(one frame after another, left to right) and a JSON list of frames, in the
order the game numbers them.

Usage: gen_sprites.py sheet.png frames.json
"""
import json
import sys
from PIL import Image

from cpcpal import COLOURS
import pens

# ASCII pens: . transparent, then the fixed playfield pens (tools/pens.py)
# by letter; some letters share a pen.
KEY = {".": 0, "w": pens.WHITE, "Y": pens.YELLOW, "y": pens.ORANGE, "o": pens.ORANGE,
       "R": pens.RED, "r": pens.RED, "e": pens.GREY, "G": pens.GREEN, "g": pens.DGREEN,
       "m": pens.MAGENTA, "u": pens.MAGENTA, "p": pens.PBLUE, "s": pens.PBLUE,
       "c": pens.PBLUE}

RUNNER_BODY = [
    "............GG..",
    "...........GGwG.",
    "...........GGGGr",
    "............GGy.",
    "............Gg..",
    "...........GGg..",
    "...........Gg...",
    "..........GGg...",
    "......gGGGGGg...",
    "....gGGGGGGGGg..",
    "gggGGGGGGGGGGg..",
    ".ggggGGGGGGGgy..",
    "......gyyyyGg...",
    ".......gGGGg....",
    "......gg..gg....",
]
RUNNER_H = 24
RIDER_DX, RIDER_DY = 4, -2     # rider position on the Runner when mounted

RIDER_BODY = [
    "..eee...",
    ".eeeee..",
    ".eerrr..",
    "..eee...",
    ".pppp...",
    "ppppwwww",
    ".pppp...",
    ".pspp...",
    ".pppp...",
]
RIDER_UP_BODY = [
    "....w...",
    "..eew...",
    ".eerw...",
    "..eep...",
    ".pppp...",
    "pppp....",
    ".pppp...",
    ".pspp...",
    ".pppp...",
]
RIDER_LEGS = {
    "stand": ["..ee....", ".eeee...", ".e..e..."],
    "walk0": ["..ee....", ".ee.e...", "ee...e.."],
    "walk1": ["..ee....", "..eee...", "..ee...."],
}
RIDER = RIDER_BODY + RIDER_LEGS["stand"]

TRACKER = [[
    "..wwww..",
    ".ewwwwe.",
    "eeeeeeee",
    "crcrcrcr",
    ".eeeeee.",
    "..e..e..",
    "..r..r..",
    "........",
]]
TRACKER.append([r.replace("crcrcrcr", "rcrcrcrc") for r in TRACKER[0]])

CRAWLER = [[
    "..oooo..",
    ".ooYYoo.",
    "oorrrroo",
    "orrrrrro",
    ".oooooo.",
    "o.o..o.o",
    "o.o..o.o",
    "o..o.o.o",
], [
    "..oooo..",
    ".ooYYoo.",
    "oorrrroo",
    "orrrrrro",
    ".oooooo.",
    ".o.oo.o.",
    ".o.oo.o.",
    "o.o..o.o",
]]

THROWER_LEGS = ["..uuu...", "..u.u...", ".uu.uu..", ".uu.uu.."]
THROWER = [[
    "..uuu...",
    ".uwuwu..",
    ".uuuuu..",
    "..uuu...",
    ".uuuuu..",
    "uuuuuuu.",
    "u.uuu.u.",
    "u.uuu.u.",
] + THROWER_LEGS, [
    "..uuu.ey",
    ".uwuwuey",
    ".uuuuuu.",
    "..uuuu..",
    ".uuuuu..",
    "uuuuuu..",
    "u.uuu...",
    "u.uuu...",
] + THROWER_LEGS]

CARRIER = [[
    "......eeee......",
    "....eewwwwee....",
    "...emmmmmmmme...",
    "..emmmmmmmmmme..",
    ".emmmrrmmrrmmme.",
    "emmmmrrmmrrmmmme",
    "eeeeeeeeeeeeeeee",
    "eYeYeYeYeYeYeYeY",
    "eeeeeeeeeeeeeeee",
    ".emmmmmmmmmmmme.",
    "..emmmmmmmmmme..",
    "...eemmmmmmee...",
    ".....ee..ee.....",
    "....rr....rr....",
    "....YY....YY....",
    ".....r....r.....",
]]
CARRIER.append([r.replace("eYeYeYeYeYeYeYeY", "YeYeYeYeYeYeYeYe")
                .replace("....YY....YY....", "....rr....rr....") for r in CARRIER[0]])

MISSILES = {
    "bomb": ["rr", "YY", "YY", "rr"],
    "rock": [".ee.", "eyye", "eeye", ".ee."],
    "boom0": ["...Y....", ".Y.oY.Y.", "..oroo..", "YoRwwroY", ".orwwRo.", "..ooro..", ".Y.Yo.Y.", "....Y..."],
    "boom1": ["Y..o..Y.", "..R..o..", ".o....R.", "o..r...o", "...o..o.", ".R....o.", "..o..R..", "Y..R...Y"],
    "cell": [".GG.", "GwwG", "GGGG", "GwwG", "GGGG", ".GG."],
}

SHOTS = {
    "shot_h": ["YwwY", "YwwY"],
    "shot_v": ["ww", "YY", "YY", "ww"],
    "shot_d": ["...w", "..Y.", ".Y..", "w..."],
}

DRIFTER = [
    [
        "..mmmm..",
        ".mrrrrm.",
        "mrYYYYrm",
        "mrYwwYrm",
        "mrYwwYrm",
        "mrYYYYrm",
        ".mrrrrm.",
        "..mmmm..",
        ".m.mm.m.",
        "m..m..m.",
    ],
    [
        "..mmmm..",
        ".mrrrrm.",
        "mroooorm",
        "mrowwerm",
        "mrewworm",
        "mroooorm",
        ".mrrrrm.",
        "..mmmm..",
        "m..mm..m",
        ".m.m.m..",
    ],
]


def grid(rows):
    return [[KEY[ch] for ch in row] for row in rows]


def line(g, x0, y0, x1, y1, pen):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        x = round(x0 + (x1 - x0) * i / n)
        y = round(y0 + (y1 - y0) * i / n)
        if 0 <= x < 16 and 0 <= y < RUNNER_H:
            g[y][x] = pen


def runner(phase):
    """Running frame 0-3, or phase None for standing."""
    g = grid(RUNNER_BODY) + [[0] * 16 for _ in range(RUNNER_H - len(RUNNER_BODY))]
    # Two legs half a cycle apart; the leg swinging forward is lifted.
    stride = [3, 1, -1, -3]
    for hip, offset, thigh, shin in ((7, 2, KEY["g"], KEY["g"]), (10, 0, KEY["G"], KEY["g"])):
        if phase is None:
            dx, lift = 0, 0
        else:
            p = (phase + offset) % 4
            dx = stride[p]
            lift = 2 if p == 3 else 0
        foot_y = RUNNER_H - 1 - lift
        knee = (hip + dx // 2 + 1, 18 - lift // 2)
        line(g, hip, 14, knee[0], knee[1], thigh)
        line(g, knee[0], knee[1], hip + dx, foot_y, shin)
        for fx in (hip + dx, hip + dx + 1):
            if 0 <= fx < 16:
                g[foot_y][fx] = KEY["y"]
    return g


def mounted(phase):
    """The Runner with its rider drawn over it, rider top at RIDER_DY."""
    top = -RIDER_DY
    g = [[0] * 16 for _ in range(RUNNER_H + top)]
    for y, row in enumerate(runner(phase)):
        g[y + top] = list(row)
    for y, row in enumerate(grid(RIDER)):
        for x, pen in enumerate(row):
            if pen:
                g[y][x + RIDER_DX] = pen
    return g


def mirror(g):
    return [list(reversed(row)) for row in g]


def main(sheet_path, json_path):
    right = [(f"mounted{i}", mounted(i)) for i in range(4)]
    right += [(f"runner{i}", runner(i)) for i in range(4)]
    right.append(("runner_stand", runner(None)))
    right += [(f"rider_{k}", grid(RIDER_BODY + RIDER_LEGS[k])) for k in ("stand", "walk0", "walk1")]
    right.append(("rider_up", grid(RIDER_UP_BODY + RIDER_LEGS["stand"])))
    # Facing right, then the same frames facing left: frame + FACING_LEFT.
    frames = [(name + "_r", g) for name, g in right] + [(name + "_l", mirror(g)) for name, g in right]
    frames += [(f"drifter{i}", grid(d)) for i, d in enumerate(DRIFTER)]
    for name, art in (("tracker", TRACKER), ("crawler", CRAWLER), ("thrower", THROWER),
                      ("carrier", CARRIER)):
        frames += [(f"{name}{i}", grid(a)) for i, a in enumerate(art)]
    frames += [(name, grid(a)) for name, a in MISSILES.items()]
    frames += [(name, grid(g)) for name, g in SHOTS.items()]
    frames.append(("shot_dl", mirror(grid(SHOTS["shot_d"]))))

    width = sum(len(f[0]) for _, f in frames)
    height = max(len(f) for _, f in frames)
    img = Image.new("P", (width, height), 0)
    pal = []
    for name in pens.palette(["black"] * 4):
        pal += COLOURS[name][1]
    img.putpalette(pal + [0] * (768 - len(pal)))
    px = img.load()
    meta, x0 = [], 0
    for name, g in frames:
        w, h = len(g[0]), len(g)
        assert w % 2 == 0, name
        for y, row in enumerate(g):
            assert len(row) == w, name
            for x, pen in enumerate(row):
                px[x0 + x, y] = pen
        meta.append({"name": name, "x": x0, "y": 0, "w": w, "h": h})
        x0 += w
    img.save(sheet_path)
    with open(json_path, "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
