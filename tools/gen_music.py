#!/usr/bin/env python3
"""Generate the music and sound effects for src/sound.asm.

Writes an assembler include with:

- snd_periods: AY tone periods (1 MHz clock) of the notes the tunes use;
- snd_instruments: per instrument, a volume envelope (a volume per 50 Hz
  tick, #FF = hold the last one);
- the songs: three channel streams each. A stream is note events (byte
  1-127: note number into snd_periods + 1, or 0 for a rest, then a duration
  in ticks), #80 + i (instrument i), #FE (loop to the start) or #FF (end);
- snd_songs: per song, its three stream addresses; SONG_* numbers;
- the sound effects: a step per tick (volume, period low, period high with
  #80 = noise on and #40 = tone off, noise period), ended by volume #FF;
  snd_sfx: per effect, its address and priority; SFX_* numbers.

Usage: gen_music.py out.inc
"""
import sys

CLOCK = 1_000_000
STEP = 6            # ticks per sixteenth note (125 bpm)
NAMES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7,
         "G#": 8, "A": 9, "A#": 10, "B": 11}

# Volume envelopes.
INSTRUMENTS = {
    "lead":  [13, 13, 12, 12, 11, 11, 10, 10, 10, 9, 9, 9, 8],
    "bass":  [15, 13, 11, 10, 9, 8, 7, 6, 5, 5, 4],
    "pad":   [4, 6, 7, 8, 8, 8, 7],
    "soft":  [11, 10, 9, 9, 8, 8, 7, 7, 6, 6, 5],
    "pluck": [12, 9, 7, 5, 4, 3, 2, 1, 0],
}
INST_ORDER = list(INSTRUMENTS)


def midi(note):
    name, octave = note[:-1], int(note[-1])
    return 12 * (octave + 1) + NAMES[name]


def period(m):
    f = 440.0 * 2 ** ((m - 69) / 12)
    return round(CLOCK / (16 * f))


def parse(text):
    """'@lead A4:4 r:2 ...' -> [('inst', name) | (midi or None, steps)]."""
    out = []
    for tok in text.split():
        if tok.startswith("@"):
            out.append(("inst", tok[1:]))
            continue
        note, steps = tok.split(":")
        out.append((None if note == "r" else midi(note), int(steps)))
    return out


def bass(roots, octave=2, pattern=(0, 12, 0, 12, 0, 12, 0, 12)):
    """Eighth-note bass: a bar per root."""
    s = "@bass"
    for root in roots.split():
        base = midi(root + str(octave))
        for off in pattern:
            s += f" {name_of(base + off)}:2"
    return s


def name_of(m):
    inv = {v: k for k, v in NAMES.items()}
    return f"{inv[m % 12]}{m // 12 - 1}"


SONGS = {
    "title": dict(loop=True, channels=[
        "@lead A4:4 C5:2 E5:2 D5:4 C5:2 B4:2 "
        "A4:6 E4:2 A4:4 B4:4 "
        "C5:4 D5:2 E5:2 G5:4 E5:4 "
        "D5:8 r:4 B4:4 "
        "C5:4 E5:2 A5:2 G5:4 E5:2 D5:2 "
        "E5:6 C5:2 A4:8 "
        "F5:4 E5:4 D5:4 C5:4 "
        "B4:4 G#4:4 A4:8",
        bass("A A C G F A D E"),
        "@pad E4:16 E4:16 G4:16 D4:16 A4:16 E4:16 F4:16 G#4:16",
    ]),
    "game": dict(loop=True, channels=[
        "@soft r:16 A4:2 r:2 A4:2 C5:2 r:4 E5:4 "
        "r:16 D5:2 r:2 D5:2 C5:2 r:4 B4:4 "
        "r:16 A4:2 r:2 A4:2 C5:2 r:4 G5:4 "
        "F5:4 E5:4 D5:4 B4:4 r:16",
        bass("A A G G F F E E", pattern=(0, 0, 12, 0, 0, 12, 0, 12)),
        "r:128",
    ]),
    "clear": dict(loop=False, channels=[
        "@lead C5:2 E5:2 G5:2 C6:6 G5:2 C6:8",
        "@bass C3:2 C3:2 C3:2 C3:6 G2:2 C3:8",
        "@pluck E4:2 G4:2 C5:2 E5:6 D5:2 E5:8",
    ]),
    "over": dict(loop=False, channels=[
        "@lead E5:4 D#5:4 D5:4 C#5:12",
        "@bass A2:4 G#2:4 G2:4 F#2:12",
        "r:24",
    ]),
}


def sweep(p0, p1, vols, noise=None, tone=True):
    """A step per volume; period from p0 to p1; noise period constant or a list."""
    n = len(vols)
    steps = []
    for i, v in enumerate(vols):
        p = round(p0 + (p1 - p0) * i / max(1, n - 1))
        nz = noise[i] if isinstance(noise, list) else noise
        steps.append((v, p, nz, tone))
    return steps


def notes(seq, vol=12, each=3):
    out = []
    for n in seq:
        out += [(vol, period(midi(n)), None, True)] * each
    return out


SFX = {  # name: (priority, steps)
    "shot":    (1, sweep(70, 160, [12, 11, 9, 7, 5])),
    "jump":    (1, sweep(320, 140, [10, 10, 9, 8, 7, 6])),
    "tick":    (1, sweep(60, 60, [11, 8])),
    "pump":    (2, sweep(220, 50, [14, 14, 13, 12, 11, 9, 7])),
    "stall":   (2, sweep(1400, 1600, [13, 12, 11, 10, 9, 8, 6, 4], noise=20)),
    "cell":    (2, notes(["C6", "E6", "G6", "C7"])),
    "whistle": (2, sweep(100, 100, [12] * 6) + sweep(75, 70, [12, 12, 12, 11, 10, 9, 8, 6, 4])),
    "boom":    (3, sweep(0, 0, [15, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2],
                         noise=[6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 31, 31], tone=False)),
    "hit":     (4, sweep(500, 1100, [15, 14, 13, 12, 11, 10, 8, 6, 4], noise=12)),
    "alarm":   (5, sweep(300, 120, [13] * 12) + sweep(300, 120, [13] * 12) + sweep(300, 120, [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1])),
}


def main(out):
    used = set()
    streams = {}
    for name, song in SONGS.items():
        lengths = []
        chans = []
        for ch in song["channels"]:
            events = parse(ch)
            lengths.append(sum(s for n, s in events if n != "inst"))
            used |= {n for n, s in events if n not in ("inst", None)}
            chans.append(events)
        assert len(set(lengths)) == 1, (name, lengths)
        streams[name] = chans
    notes_sorted = sorted(used)
    index = {m: i + 1 for i, m in enumerate(notes_sorted)}
    assert len(index) < 127

    lines = ["; Generated by tools/gen_music.py: music and sound effects for sound.asm.", ""]
    lines.append("snd_periods:")
    for m in notes_sorted:
        lines.append(f"    dw {period(m)}    ; {name_of(m)}")
    lines.append("snd_instruments:")
    for name in INST_ORDER:
        lines.append(f"    dw snd_inst_{name}")
    for name in INST_ORDER:
        vols = INSTRUMENTS[name]
        lines.append(f"snd_inst_{name}: db {', '.join(map(str, vols))}, #FF")

    size = 0
    for sname, chans in streams.items():
        for c, events in enumerate(chans):
            data = []
            for n, s in events:
                if n == "inst":
                    data.append(0x80 + INST_ORDER.index(s))
                    continue
                ticks = s * STEP
                code = 0 if n is None else index[n]
                while ticks > 0:
                    t = min(ticks, 240)
                    data += [code, t]
                    ticks -= t
            data.append(0xFE if SONGS[sname]["loop"] else 0xFF)
            size += len(data)
            lines.append(f"snd_{sname}_{c}:")
            for i in range(0, len(data), 16):
                lines.append("    db " + ", ".join(f"#{b:02X}" for b in data[i:i + 16]))
    lines.append("snd_songs:")
    for i, sname in enumerate(streams):
        lines.append(f"    dw snd_{sname}_0, snd_{sname}_1, snd_{sname}_2")
    for i, sname in enumerate(streams):
        lines.append(f"SONG_{sname.upper()} equ {i + 1}")

    lines.append("snd_sfx:")
    for name, (prio, steps) in SFX.items():
        lines.append(f"    dw snd_fx_{name} : db {prio}")
    for i, name in enumerate(SFX):
        lines.append(f"SFX_{name.upper()} equ {i + 1}")
    for name, (prio, steps) in SFX.items():
        data = []
        for v, p, nz, tone in steps:
            hi = (p >> 8) & 0x0F
            if nz is not None:
                hi |= 0x80
            if not tone:
                hi |= 0x40
            data += [v, p & 0xFF, hi, nz or 0]
        data.append(0xFF)
        size += len(data)
        lines.append(f"snd_fx_{name}:")
        for i in range(0, len(data), 16):
            lines.append("    db " + ", ".join(f"#{b:02X}" for b in data[i:i + 16]))
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"{out}: {len(notes_sorted)} notes, {len(streams)} songs, {len(SFX)} effects, {size} bytes of streams")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
