#!/usr/bin/env python3
"""Generate the sprite sheet.

The Runner, 24x36, in two parts: its body (ridden, with the rider sitting
on it, or not) and its legs (4 running poses and a standing one); the rider
on foot (standing, 2 walking frames, aiming up); all facing right and
mirrored to face left; the enemies (drifter, tracker, crawler, rock thrower, breach
carrier, 2 frames each), their bombs and rocks, an explosion, an energy
cell; and the rider's bolts (horizontal, vertical, diagonal both ways).
The look is chunky and shaded, with black outlines: the Runner and the rider
are outlined all round (outline()), the enemies have
their black drawn in by hand.

Sprites share the playfield palette and use only its fixed pens (tools/pens.py);
pen 0 is transparent, and the sheet's pen 16 (OPAQUE_BLACK) is black drawn
opaque (tools/spritec.py). Writes the sheet
(one frame after another, left to right) and a JSON list of frames, in the
order the game numbers them.

Usage: gen_sprites.py sheet.png frames.json
"""
import json
import sys
from PIL import Image

from cpcpal import COLOURS
import pens

OPAQUE_BLACK = 16

# ASCII pens: . transparent, K opaque black, then the fixed playfield pens
# (tools/pens.py) by letter; some letters share a pen.
KEY = {".": 0, "K": OPAQUE_BLACK, "w": pens.WHITE, "Y": pens.YELLOW, "y": pens.ORANGE,
       "o": pens.ORANGE, "R": pens.RED, "r": pens.RED, "e": pens.GREY, "G": pens.GREEN,
       "g": pens.DGREEN, "m": pens.MAGENTA, "u": pens.MAGENTA, "p": pens.PBLUE,
       "s": pens.PBLUE, "c": pens.PBLUE}

# The Runner: a big flightless running beast on long bird legs, crested
# head held low and forward (below the rider's gun), saddled in the middle
# so the rider sits RIDER_DX in whichever way it faces, plumed tail; its
# legs are drawn by runner().
RUNNER_BODY = [
    "g.......................",
    "Gg......................",
    "gGg.....................",
    ".gGg...............rr...",
    "..GGg.............rGGGG.",
    "...GGg...........rGGwKGG",
    "...gGGgyrrrrrry..gGGGGyy",
    "....gGGyyyyyyyyg.ggGGGy.",
    "....gGGGGGGGGGGGgGGGg...",
    "...gGGGGGGGGGGGGGGGg....",
    "..gGGGGGGGGGGGGGGGGg....",
    "..gGGGGGGGGGGGGGGGg.....",
    "...ggGGGGGGGGGGGGgg.....",
    "....ggggGGGGGGGgg.......",
    ".....gggggggggg.........",
    ".......gggggg...........",
]
RUNNER_W, RUNNER_H = 24, 36
HIP_Y = 14
LEGS_Y = 14                 # the legs' frames start this far down (player.asm)
RIDER_DX = 8                # rider's x on the Runner (player.asm RIDER_ON_RUNNER)
RIDER_UP = 3                # rows of the rider above the Runner (player.asm)

# The rider: helmet with a dark visor, suit, belt, boots, gun forward.
RIDER_BODY = [
    "..eee...",
    ".eeeee..",
    ".eeKKw..",
    "..eee...",
    ".ppppp..",
    ".ppKeeew",
    ".ppp....",
    ".KKK....",
    ".ppp....",
]
RIDER_UP_BODY = [
    "..eee.w.",
    ".eeeeKe.",
    ".eeKK.e.",
    "..eee.p.",
    ".ppppp..",
    ".ppp....",
    ".ppp....",
    ".KKK....",
    ".ppp....",
]
RIDER_LEGS = {
    "stand": [".p.p....", ".p.p....", "ee.ee..."],
    "walk0": [".pp.p...", "pp...p..", "ee...ee."],
    "walk1": ["..pp....", "..pp....", "..eee..."],
    "sit": [".ppppp..", "....p...", "....ee.."],
}
RIDER_SIT = RIDER_BODY + RIDER_LEGS["sit"]       # on the Runner

TRACKER = [[
    "..KwwK..",
    ".KewweK.",
    "KeeeeeeK",
    "crcrcrcr",
    "KeeeeeeK",
    ".KKeeKK.",
    "..r..r..",
    "..Y..Y..",
]]
TRACKER.append([r.replace("crcrcrcr", "rcrcrcrc").replace("..Y..Y..", "..r..r..")
                for r in TRACKER[0]])

CRAWLER = [[
    "..KooK..",
    ".KoYwoK.",
    "KorrrroK",
    "orRrrRro",
    "KooooooK",
    ".KoKKoK.",
    "oK.o.Ko.",
    "o..o..o.",
], [
    "..KooK..",
    ".KoYwoK.",
    "KorrrroK",
    "orRrrRro",
    "KooooooK",
    ".KoKKoK.",
    ".oKo.oK.",
    ".o.o.o.o",
]]

THROWER_LEGS = [".uK.u...", ".u..u...", "uu.uu...", "KK.KK..."]
THROWER = [[
    "..KuuK..",
    ".Kuwuw..",
    ".uuKKu..",
    "..Kuu...",
    ".uuuuu..",
    "uuKuuuu.",
    "u.uuu.u.",
    "K.uKu.K.",
] + THROWER_LEGS, [
    "..KuuKey",
    ".KuwuwKe",
    ".uuKKuu.",
    "..Kuuu..",
    ".uuuuu..",
    "uuKuuu..",
    "u.uuu...",
    "K.uKu...",
] + THROWER_LEGS]

CARRIER = [[
    "......KeeK......",
    "....KewwwweK....",
    "...KmmmmmmmmK...",
    "..KmmmmmmmmmmK..",
    ".KmmmrrmmrrmmmK.",
    "KmmmmrKmmrKmmmmK",
    "eeeeeeeeeeeeeeee",
    "eYeYeYeYeYeYeYeY",
    "KeeeeeeeeeeeeeeK",
    ".KmmmmmmmmmmmmK.",
    "..KmmmmmmmmmmK..",
    "...KKmmmmmmKK...",
    ".....eK..Ke.....",
    "....rr....rr....",
    "....YY....YY....",
    ".....r....r.....",
]]
CARRIER.append([r.replace("eYeYeYeYeYeYeYeY", "YeYeYeYeYeYeYeYe")
                .replace("....YY....YY....", "....rr....rr....") for r in CARRIER[0]])

MISSILES = {
    "boom0": ["...Y....", ".Y.oY.Y.", "..oroo..", "YoRwwroY", ".orwwRo.", "..ooro..", ".Y.Yo.Y.", "....Y..."],
    "boom1": ["Y..o..Y.", "..R..o..", ".o....R.", "o..r...o", "...o..o.", ".R....o.", "..o..R..", "Y..R...Y"],
    "cell": [".GG.", "GwwG", "GGGg", "GwwG", "GGGg", ".gg."],
    "bomb": ["rr", "YY", "YY", "rr"],
    "rock": [".ee.", "eyyK", "eeyK", ".KK."],
}
# Small, fast and many: drawn at even x straight over everything, saving
# what they cover (src/tiny.asm), not as sprites; numbered last.
TINY = ("bomb", "rock", "shot_h", "shot_v", "shot_d", "shot_dl")

SHOTS = {
    "shot_h": ["YwwY", "YwwY"],
    "shot_v": ["ww", "YY", "YY", "ww"],
    "shot_d": ["...w", "..Y.", ".Y..", "w..."],
}

DRIFTER = [
    [
        "..KmmK..",
        ".KmrrmK.",
        "KmrYYrmK",
        "mrYwKYrm",
        "mrYKKYrm",
        "KmrYYrmK",
        ".KmrrmK.",
        "..KmmK..",
        ".m.mm.m.",
        "m..K..m.",
    ],
    [
        "..KmmK..",
        ".KmrrmK.",
        "KmroorrK",
        "mroKwerm",
        "mroKKorm",
        "KmroorrK",
        ".KmrrmK.",
        "..KmmK..",
        "m..mm..m",
        ".m.K.m..",
    ],
]


def grid(rows):
    return [[KEY[ch] for ch in row] for row in rows]


def outline(g):
    """Black round everything: each transparent pixel next to (left, right,
    above or below) a coloured one."""
    h, w = len(g), len(g[0])
    out = [list(row) for row in g]
    for y in range(h):
        for x in range(w):
            if g[y][x]:
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and g[ny][nx] not in (0, OPAQUE_BLACK):
                    out[y][x] = OPAQUE_BLACK
                    break
    return out


def line(g, x0, y0, x1, y1, pen, width=1):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        x = round(x0 + (x1 - x0) * i / n)
        y = round(y0 + (y1 - y0) * i / n)
        for dx in range(width):
            if 0 <= x + dx < RUNNER_W and 0 <= y < RUNNER_H:
                g[y][x + dx] = pen


def runner(phase):
    """The whole Runner, running frame 0-3 or phase None for standing,
    rider_top rows above it with the rider sitting on it if rider; outlined."""
    g = grid(RUNNER_BODY) + [[0] * RUNNER_W for _ in range(RUNNER_H - len(RUNNER_BODY))]
    # Two bird legs half a cycle apart: a thick thigh forward to the knee,
    # the shank back to the ankle joint, the long foot bone forward to a
    # clawed foot. The far leg is darker and drawn first; the leg swinging
    # forward is lifted.
    stride = [5, 2, -2, -5]
    for hip, offset, thigh, shank in ((9, 2, KEY["g"], KEY["g"]), (13, 0, KEY["G"], KEY["g"])):
        if phase is None:
            dx, lift = 0, 0
        else:
            p = (phase + offset) % 4
            dx = stride[p]
            lift = 4 if p == 3 else 0
        foot = (hip + dx, RUNNER_H - 1 - lift)
        knee = (hip + dx // 2 + 2, 20 - lift // 2)
        joint = (hip + dx // 2 - 2, 28 - lift)
        line(g, hip, HIP_Y, knee[0], knee[1], thigh, 3)
        line(g, knee[0], knee[1], joint[0], joint[1], shank, 2)
        line(g, joint[0], joint[1], foot[0], foot[1], shank)
        for fx in range(foot[0] - 1, foot[0] + 3):
            if 0 <= fx < RUNNER_W:
                g[foot[1]][fx] = KEY["y"]
    return g


def ridden(phase):
    """The Runner with the rider sitting on it, RIDER_UP rows above it."""
    g = [[0] * RUNNER_W for _ in range(RIDER_UP)] + runner(phase)
    for y, row in enumerate(grid(RIDER_SIT)):
        for x, pen in enumerate(row):
            if pen:
                g[y][x + RIDER_DX] = pen
    return g


def split_runner():
    """The Runner in parts: only its legs move, so its body (the rows above
    LEGS_Y, the same in every frame) is one frame, ridden or not, and each
    pose of the legs another, cropped to them: (name, grid, x offset)."""
    poses = [(f"legs{i}", i) for i in range(4)] + [("legs_stand", None)]
    whole = [outline(runner(p)) for _, p in poses]
    with_rider = [outline(ridden(p)) for _, p in poses]
    assert all(g[:LEGS_Y] == whole[0][:LEGS_Y] for g in whole), "the body moves"
    top = LEGS_Y + RIDER_UP
    assert all(g[:top] == with_rider[0][:top] for g in with_rider), "the body moves"
    parts = [("body", whole[0][:LEGS_Y], 0), ("mounted", with_rider[0][:top], 0)]
    for (name, _), g in zip(poses, whole):
        legs = g[LEGS_Y:]
        xs = [x for row in legs for x, pen in enumerate(row) if pen]
        x0, x1 = min(xs), max(xs) + 1
        if (x1 - x0) % 2:               # whole bytes
            if x1 < RUNNER_W:
                x1 += 1
            else:
                x0 -= 1
        parts.append((name, [row[x0:x1] for row in legs], x0))
    return parts


def mirror(g):
    return [list(reversed(row)) for row in g]


def main(sheet_path, json_path):
    right = split_runner()
    right += [(f"rider_{k}", outline(grid(RIDER_BODY + RIDER_LEGS[k])), None)
              for k in ("stand", "walk0", "walk1")]
    right.append(("rider_up", outline(grid(RIDER_UP_BODY + RIDER_LEGS["stand"])), None))
    # Facing right, then the same frames facing left: frame + FACING_LEFT.
    # Legs carry their x offset from the Runner's left edge.
    frames = [(name + "_r", g, dx) for name, g, dx in right]
    frames += [(name + "_l", mirror(g), None if dx is None else RUNNER_W - dx - len(g[0]))
               for name, g, dx in right]
    frames = [(name, g) if dx is None else (name, g, dx) for name, g, dx in frames]
    frames += [(f"drifter{i}", grid(d)) for i, d in enumerate(DRIFTER)]
    for name, art in (("tracker", TRACKER), ("crawler", CRAWLER), ("thrower", THROWER),
                      ("carrier", CARRIER)):
        frames += [(f"{name}{i}", grid(a)) for i, a in enumerate(art)]
    frames += [(name, grid(a)) for name, a in MISSILES.items()]
    frames += [(name, grid(g)) for name, g in SHOTS.items()]
    frames.append(("shot_dl", mirror(grid(SHOTS["shot_d"]))))

    width = sum(len(f[1][0]) for f in frames)
    height = max(len(f[1]) for f in frames)
    img = Image.new("P", (width, height), 0)
    pal = []
    for name in pens.palette(["black"] * 4) + ["black"]:     # + OPAQUE_BLACK
        pal += COLOURS[name][1]
    img.putpalette(pal + [0] * (768 - len(pal)))
    px = img.load()
    meta, x0 = [], 0
    for name, g, *dx in frames:
        w, h = len(g[0]), len(g)
        assert w % 2 == 0, name
        for y, row in enumerate(g):
            assert len(row) == w, name
            for x, pen in enumerate(row):
                px[x0 + x, y] = pen
        meta.append({"name": name, "x": x0, "y": 0, "w": w, "h": h})
        if name in TINY:
            meta[-1]["tiny"] = True
        if dx:
            meta[-1]["dx"] = dx[0]
        x0 += w
    tiny = [i for i, m in enumerate(meta) if m.get("tiny")]
    assert tiny == list(range(len(meta) - len(TINY), len(meta))), "tiny frames go last"
    img.save(sheet_path)
    with open(json_path, "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
