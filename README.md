# Shieldrunner (Edgeworld-CPC)

A horizontally scrolling "patrol and recharge" shooter for the Amstrad CPC 6128,
inspired by Palace Software's *Rimrunner* (C64, 1988). You ride a fast mount
around the rim of a dead planet, shoot intruders and dismount to recharge the
shield generators before they fail. The game keeps the original's loop and
adds what reviewers said it lacked: route decisions, risk when you dismount
and a different enemy mix on each planet.

This is an original game. The name, characters, art and music are new, and
nothing from Rimrunner or Palace is reused. The full design and technical plan
is in [plan.md](plan.md).

## Status

| # | Milestone | State |
|---|-----------|-------|
| 1 | Scroll engine: firmware off, Mode 0, double buffer, CRTC hardware scroll over a wrap-around map | **Done** |
| 2 | HUD split and rasters | Next |
| 3 | Sprite engine | |
| 4 | Player | |
| 5 | Generators and radar | |
| 6 | Enemies | |
| 7 | First planet complete | |
| 8 | Banking and loading | |
| 9 | Planets 2-4 | |
| 10 | Release | |

The current build is the milestone 1 scroll test: a 1024-pixel test planet
(starfield, mountains, ground, four generators and column markers) that
scrolls at 25 fps and wraps seamlessly.

## Building

You need:

- [RASM](https://github.com/EdouardBERGE/rasm) (tested with 3.2.5)
- [iDSK](https://github.com/cpcsdk/idsk)
- Python 3 with Pillow
- GNU make

```bash
make
```

This generates the test planet, converts it to tiles, assembles the game and
writes `build/shield.dsk`.

## Running

Load `build/shield.dsk` in a CPC 6128 emulator (Caprice32, WinAPE, ACE-DL) or
on a real machine and type:

```
RUN"SHIELD
```

Controls for the scroll test (joystick or cursor keys):

| Input | Action |
|-------|--------|
| Left / Right | Scroll left / right (the direction is kept after release) |
| Down | Stop |

It starts scrolling right on its own.

## Testing

```bash
make test
```

The test boots the disc in a headless CPC 6128 emulator (a Python wrapper
around the [floooh/chips](https://github.com/floooh/chips) CPC emulation,
looked up in `$CPCEMU_DIR`, default `~/cpcemu`). On CRTC types 0, 1 and 2 it
checks that:

- every displayed frame matches the map rendered at some scroll position, with
  no torn or stale columns;
- the view moves exactly one column every two frames (25 fps), with no late
  buffer flips;
- the view scrolls left, right, stops, and wraps past the end of the planet.

It also reports how much of the 2-frame budget the frame's work used.

## How it works

**Screen.** Mode 0, 160x200, 16 colours. The visible screen is 40 CRTC words
(80 bytes) by 25 character rows.

**Scrolling.** Each 2K line block of a 16K screen page is a ring of 1024 CRTC
words. Moving the start address (R12/R13) by one word scrolls the picture by
4 pixels, and only the newly exposed column needs drawing. A scroll position
is a 16-bit column count: its low 10 bits are the CRTC offset and its low 8
bits the map column, so the 256-column planet wraps for free.

**Double buffering.** Two screen pages at `&C000` and `&8000`. Each buffer
remembers the position it last showed and catches up (two columns per frame
at full speed) before it is displayed again.

**Frame timing.** The firmware is switched off and our own handler runs at
`&0038`. The gate array interrupts 300 times a second; the interrupt that
lands during VSYNC starts a frame. When the main loop has queued a buffer and
two frames have passed, the handler writes R12/R13, which every CRTC type
picks up at the next frame start. That locks the game to 25 fps.

**Tiles.** A tile is one CRTC character: 4 Mode 0 pixels by 8 lines, 16 bytes.
The map is stored column-major, one byte per cell. `tools/png2tiles.py`
converts any indexed PNG (pen = palette index, RGB matched to the nearest CPC
colour) into tiles, map and palette.

## Layout

| Path | Contents |
|------|----------|
| `src/main.asm` | Entry point, setup and main loop |
| `src/scroll.asm` | Column drawing, buffer catch-up and flips |
| `src/system.asm` | Interrupt handler, flip timing, keyboard and joystick, palette |
| `src/hw.asm` | Hardware ports and constants |
| `tools/gen_testplanet.py` | Generates the test planet image |
| `tools/png2tiles.py` | PNG to Mode 0 tiles, map and palette |
| `tools/cpcpal.py` | CPC colours and Mode 0 byte packing |
| `tests/test_scroll.py` | Headless scroll test on CRTC types 0, 1 and 2 |
| `assets/` | Source art |

### Memory map (current)

| Range | Use |
|-------|-----|
| `&0038` | Interrupt handler vector |
| `&0040-&01FF` | Stack |
| `&0200-` | Code, tiles, map, palette (about 8K) |
| `&8000-&BFFF` | Screen buffer 2 |
| `&C000-&FFFF` | Screen buffer 1 |

## Credits

Design inspiration: *Rimrunner* by Steve Brown, Binary Vision, Gary Carr and
Richard Joseph (Palace Software, 1988), and Pete Green's cancelled 1988 CPC
port.
