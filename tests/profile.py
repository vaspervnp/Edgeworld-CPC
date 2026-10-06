#!/usr/bin/env python3
"""Sampling profiler: where the game's time goes.

Runs the game in the headless emulator, samples the program counter every
few microseconds and charges each sample to the routine (global label) it
falls in. Prints the share of time and NOPs per 2-frame (25 fps) game frame.

Both ride right at full speed, firing (the busiest case).

With --work, instead measures each game frame's work: the time from a flip
to the main loop queueing the next buffer (interrupts included), against
the 39,936 us of two frames.

Usage: profile.py [frames] [step_us]
       profile.py --work [frames]
"""
import bisect
import sys

from harness import Game

FRAME_PAIR_US = 2 * 19968


def main(frames=100, step=3):
    g = Game(1)
    import cpc
    g.c.key_down(cpc.KEY_RIGHT)
    g.c.key_down(" ")
    g.c.run_frames(30)
    labels = sorted((addr, name) for name, addr in g.sym.items()
                    if "." not in name and addr < 0x4000)
    addrs = [a for a, _ in labels]
    counts = {}
    total = 0
    for _ in range(frames * 19968 // step):
        g.c.run_us(step)
        pc = g.c.pc
        i = bisect.bisect_right(addrs, pc) - 1
        name = labels[i][1] if i >= 0 and pc < 0x4000 else f"#{pc:04X}"
        counts[name] = counts.get(name, 0) + 1
        total += 1
    print(f"{total} samples over {frames} frames; NOPs per 25 fps frame:")
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        share = n / total
        if share < 0.003:
            continue
        print(f"  {name:24s} {share * 100:5.1f}%  {share * FRAME_PAIR_US:7.0f}")


def work(frames=300):
    g = Game(1)
    import cpc
    g.c.key_down(cpc.KEY_RIGHT)         # ride at full speed (the busiest case)
    g.c.key_down(" ")                   # and keep firing
    g.c.run_frames(30)
    flips = g.sym["FLIPS"]
    pending = g.sym["FLIP_PENDING"]
    t, start, times = 0, None, []
    last_flips = g.word("FLIPS")
    was_pending = g.c.read_ram(pending, 1)[0]
    while t < frames * 19968:
        g.c.run_us(8)
        t += 8
        f = g.word("FLIPS")
        if f != last_flips:
            last_flips, start = f, t
        p = g.c.read_ram(pending, 1)[0]
        if p and not was_pending and start is not None:
            times.append(t - start)
        was_pending = p
    times.sort()
    n = len(times)
    print(f"{n} game frames: work min {times[0]}, median {times[n // 2]}, "
          f"90% {times[n * 9 // 10]}, max {times[-1]} us of {FRAME_PAIR_US}")
    print(f"over budget: {sum(1 for x in times if x > FRAME_PAIR_US)}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--work"]:
        work(*(int(a) for a in sys.argv[2:]))
    else:
        main(*(int(a) for a in sys.argv[1:]))
