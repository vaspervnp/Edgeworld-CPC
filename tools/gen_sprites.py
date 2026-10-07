#!/usr/bin/env python3
"""Generate the sprite sheet.

The Runner (4 running frames and a standing one), its rider on foot
(standing, 2 walking frames, aiming up), the two together while mounted (4
frames: one sprite is cheaper than two), all facing right and mirrored to
face left; the enemies (drifter, tracker, crawler, rock thrower, breach
carrier, 2 frames each), their bombs and rocks, an explosion, an energy
cell; and the rider's bolts (horizontal, vertical, diagonal both ways).

The look is chunky and shaded, with black outlines: the Runner, its rider
and the mounted frames are outlined all round (outline()), the enemies have
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

# The Runner: a big flightless running beast, crested, saddled, with a
# plumed tail; its legs are drawn by runner().
RUNNER_BODY = [
    "................",
    "................",
    "............rr..",
    "............GGGG",
    "...........gGwKG",
    "...........gGGyy",
    "............gGy.",
    "...........gG...",
    "g.........gGg...",
    "Gg..yrrrrgGGg...",
    ".GGgyyyyyGGGGg..",
    "..gGGGGGGGGGGGg.",
    "...ggGGGGGGGGgg.",
    "....gggggggggg..",
]
RUNNER_H = 24
HIP_Y = 13
RIDER_DX, RIDER_DY = 4, -2     # rider position on the Runner when mounted

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
# Mounted: sitting, the gun a little shorter to clear the Runner's head.
RIDER = RIDER_BODY[:5] + [".ppKeew."] + RIDER_BODY[6:] + RIDER_LEGS["sit"]

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
    "bomb": ["rr", "YY", "YY", "rr"],
    "rock": [".ee.", "eyyK", "eeyK", ".KK."],
    "boom0": ["...Y....", ".Y.oY.Y.", "..oroo..", "YoRwwroY", ".orwwRo.", "..ooro..", ".Y.Yo.Y.", "....Y..."],
    "boom1": ["Y..o..Y.", "..R..o..", ".o....R.", "o..r...o", "...o..o.", ".R....o.", "..o..R..", "Y..R...Y"],
    "cell": [".GG.", "GwwG", "GGGg", "GwwG", "GGGg", ".gg."],
}

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
            if 0 <= x + dx < 16 and 0 <= y < RUNNER_H:
                g[y][x + dx] = pen


def runner_raw(phase):
    """Running frame 0-3, or phase None for standing; not outlined."""
    g = grid(RUNNER_BODY) + [[0] * 16 for _ in range(RUNNER_H - len(RUNNER_BODY))]
    # Two bird legs half a cycle apart: a thick thigh, the joint bending
    # back, a thin shank down to a clawed foot. The far leg is darker and
    # drawn first; the leg swinging forward is lifted.
    stride = [3, 1, -1, -3]
    for hip, offset, thigh, shank in ((6, 2, KEY["g"], KEY["g"]), (9, 0, KEY["G"], KEY["g"])):
        if phase is None:
            dx, lift = 0, 0
        else:
            p = (phase + offset) % 4
            dx = stride[p]
            lift = 2 if p == 3 else 0
        foot = (hip + dx, RUNNER_H - 1 - lift)
        knee = (hip + dx // 2 + 1, 16 - lift // 2)
        joint = (hip + dx // 2 - 1, 20 - lift)
        line(g, hip, HIP_Y, knee[0], knee[1], thigh, 2)
        line(g, knee[0], knee[1], joint[0], joint[1], shank)
        line(g, joint[0], joint[1], foot[0], foot[1], shank)
        for fx in (foot[0], foot[0] + 1):
            if 0 <= fx < 16:
                g[foot[1]][fx] = KEY["y"]
    return g


def runner(phase):
    return outline(runner_raw(phase))


def mounted(phase):
    """The Runner with its rider sitting on it, rider top at RIDER_DY."""
    top = -RIDER_DY
    g = [[0] * 16 for _ in range(RUNNER_H + top)]
    for y, row in enumerate(runner_raw(phase)):
        g[y + top] = list(row)
    for y, row in enumerate(grid(RIDER)):
        for x, pen in enumerate(row):
            if pen:
                g[y][x + RIDER_DX] = pen
    return outline(g)


def mirror(g):
    return [list(reversed(row)) for row in g]


def main(sheet_path, json_path):
    right = [(f"mounted{i}", mounted(i)) for i in range(4)]
    right += [(f"runner{i}", runner(i)) for i in range(4)]
    right.append(("runner_stand", runner(None)))
    right += [(f"rider_{k}", outline(grid(RIDER_BODY + RIDER_LEGS[k])))
              for k in ("stand", "walk0", "walk1")]
    right.append(("rider_up", outline(grid(RIDER_UP_BODY + RIDER_LEGS["stand"]))))
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
    for name in pens.palette(["black"] * 4) + ["black"]:     # + OPAQUE_BLACK
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
