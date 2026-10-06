#!/usr/bin/env python3
"""Pack a planet into one 16K bank image for extra RAM bank 7, loaded from
disc by the game (src/disc.asm) and paged in at #4000:

  #4000  map: 256 columns of 17 cells, column-major, a tile number each
  #5100  header: the planet's parameters (see src/planet.asm), copied to
         base RAM when the planet is loaded
  #5200  tile_lo, #5300 tile_hi: the address of each tile
  #5400  tile_attr: per tile, 0 or its foreground overlay number + 1
  #5500  col_fg: per map column, non-zero if it has foreground tiles (also
         copied to base RAM: the sprite code reads it with a sprite bank in)
  #5600  tiles, 16 bytes each (up to 256)
  #6600  foreground overlays, 32 bytes each (256-aligned)

The art comes from png2tiles.py (out_prefix.map/.tiles/.attr/.colfg/.fg/.pal),
the parameters from a JSON file:

  time          seconds to hold the shield
  shield_fails  drained generators that bring the shield down
  spawn_every   game frames between enemies, ambient_max: at most this many
  mix           8 enemy types the spawner picks from
  generators    4 x [map column, drain per frame, starting charge]; the
                columns are fixed (the HUD radar and the core pen rely on them)
  sky           3 colours of the raster sky bands
  colours       pens 3-6 (tools/pens.py); the art's palette must agree

Usage: mkplanet.py planet.json art_prefix out.bin
"""
import json
import sys

from cpcpal import COLOURS
import pens

BASE = 0x4000
HEADER, TILE_LO, TILE_HI, TILE_ATTR, COL_FG, TILES, FG = (
    0x5100, 0x5200, 0x5300, 0x5400, 0x5500, 0x5600, 0x6600)
MAP_COLS, MAP_ROWS = 256, 17
GEN_COLS = [32, 96, 160, 224]
TYPES = {"drifter": 1, "tracker": 2, "crawler": 3, "thrower": 4}
HEADER_SIZE = 52


def header(p, art_palette):
    out = bytearray()
    out += p["time"].to_bytes(2, "little")
    out += bytes([p["shield_fails"], p["spawn_every"], p["ambient_max"]])
    assert len(p["mix"]) == 8
    out += bytes(TYPES[t] for t in p["mix"])
    gens = p["generators"]
    assert [g[0] for g in gens] == GEN_COLS, "generator columns are fixed"
    for col, rate, charge in gens:
        out += bytes([col]) + rate.to_bytes(2, "little") + charge.to_bytes(2, "little")
    fixed = pens.palette(p["colours"])
    expect = bytes(COLOURS[n][0] for n in fixed)
    for pen in range(16):
        if pen != pens.SKY:
            assert art_palette[pen] == expect[pen], f"pen {pen} of the art is not {fixed[pen]}"
    out += art_palette
    out += bytes(COLOURS[n][0] for n in p["sky"])
    assert len(out) == HEADER_SIZE, len(out)
    return out


def main(params_path, art, out_path):
    p = json.load(open(params_path))
    read = lambda ext: open(art + ext, "rb").read()
    tmap, tiles, attr, colfg, fg, pal = (read(e) for e in
                                         (".map", ".tiles", ".attr", ".colfg", ".fg", ".pal"))
    assert len(tmap) == MAP_COLS * MAP_ROWS
    assert len(tiles) <= FG - TILES and len(tiles) % 16 == 0
    assert len(fg) <= 0x8000 - FG
    bank = bytearray(0x8000 - BASE)

    def put(addr, data):
        bank[addr - BASE:addr - BASE + len(data)] = data

    put(BASE, tmap)
    put(HEADER, header(p, pal[:16]))
    assert len(colfg) == MAP_COLS
    put(COL_FG, colfg)
    put(TILE_LO, bytes((TILES + t * 16) & 0xFF for t in range(256)))
    put(TILE_HI, bytes((TILES + t * 16) >> 8 for t in range(256)))
    put(TILE_ATTR, attr[:256])
    put(TILES, tiles)
    put(FG, fg)
    end = FG + len(fg) - BASE
    open(out_path, "wb").write(bank[:end])
    print(f"{out_path}: {len(tiles) // 16} tiles, {len(fg) // 32} overlays, {end} bytes")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
