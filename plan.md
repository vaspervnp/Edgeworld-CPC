# Rimrunner-style CPC 6128 game plan

Oct 6, 2026 · @Vassilis

Build a horizontally scrolling "patrol and recharge" shooter in the spirit of Palace Software's Rimrunner (C64, 1988), fixing its main criticism: too little variety. Working title: **Shieldrunner** (an original name, characters and art, since the Rimrunner name, Insectoid/Runner designs and Palace assets are not ours to reuse).

## The source game

The video is a C64 longplay of [Rimrunner](https://en.wikipedia.org/wiki/Rimrunner), designed by Steve Brown (Barbarian), coded by Binary Vision, graphics by Gary Carr, music by Richard Joseph, published by Palace in 1988.

**Premise.** Insectoid colonies on dead planets are protected by force-shield bubbles. Shield generators drain and must be recharged by an elite warrior riding a reptilian mount called a Runner ([MobyGames](https://www.mobygames.com/game/29262/)).

**Core loop** ([Zzap!64 #37 review](https://everygamegoing.com/larticle/Rimrunner-000/28765), [MobyGames](https://www.mobygames.com/game/29262/)):

- Three planets, each a horizontally scrolling perimeter, under a countdown timer.
- A radar strip at the top shows the whole planet, the player and every generator: green = stable, flashing = unstable, red = drained.
- Ride the Runner fast across the level, shooting in several directions at intruders.
- At a red generator, dismount and recharge it on foot. On foot you are slow and the screen stops scrolling.
- Hits drain the rider's energy and can knock him off the Runner. The Runner takes limited hits, then dies; a limited number of spares can be summoned by whistling.
- Game over when time or energy runs out.
- Most enemies drift toward the player; some track him and drop missiles; also flying rocks and fireballs.

**Reception.** Reviews praised the animation, parallax scrolling and sound, and averaged about 62% ([MobyGames](https://www.mobygames.com/game/29262/)). The common complaint: it plays like a rolling demo, with little variety and the fire button held down constantly ([Zzap!64](https://everygamegoing.com/larticle/Rimrunner-000/28765)). C&VG was kinder, calling it immediately playable ([C&VG #79](https://everygamegoing.com/larticle/Rim-Runner-000/42442)).

## The cancelled 1988 CPC port

A CPC version was nearly finished in 1988 and never shipped; memory was its stated problem ([Games That Weren't](https://www.gamesthatwerent.com/2025/09/rimrunner/)).

- Coder Pete Green; it was the cover story of Amstrad Computer User, July 1988, with a 2.5-page technical article.
- His starting point was a routine separating background layers so a foreground layer could hide sprites, plus fast software scrolling inspired by routines printed in ACU.
- Graphics and maps were transferred from a C64 to the CPC over RS232 with a null-modem cable.
- He could not fit all three levels in a 64K machine. The plan was two levels per tape side plus a CPC-exclusive bonus level; the disc version was to have different backgrounds.
- The Atari ST version was also cancelled; only a small ST demo survives.

**Lessons for us.** Target the 6128 and use the extra 64K banks, which fixes the exact problem that killed the 1988 port. Load one planet at a time from disc. Keep the foreground-occlusion layer: it is what made the original look rich, and it is affordable with masked sprites over tiles.

## Game design

Keep the original's loop (ride, shoot, dismount, recharge, beat the clock) and add the decisions it lacked: which generator to save first, when to leave the mount, and what to spend energy on.

**Kept from the original**

- Wrap-around planet perimeter, scrolling left/right, with a radar strip showing generators by state.
- Mounted vs on-foot modes: fast and exposed vs slow, precise and needed for recharging.
- Runner with limited hits; spares summoned with a whistle key.
- Countdown timer per planet; game over on time or energy.

**Added for variety**

| Addition | What it changes |
| --- | --- |
| Generators drain at different rates, and a fully drained one lets a breach wave in | Route planning: the radar becomes a decision, not decoration |
| Recharge is a short hold-fire minigame while enemies close in | Dismounting has risk; the fire button is not held all game |
| Enemy roster per planet (drifters, trackers that bomb, ground crawlers, rock throwers) | Each planet plays differently |
| A breach carrier mini-boss appears if two generators go red | Failure escalates instead of just ending |
| Energy cells dropped by enemies: spend on shots, rider health or a new Runner | Light resource choice |
| Runner jump over ground hazards | Uses the ground layer, not only shooting |

**Structure.** Four planets (three plus a bonus, echoing the 1988 CPC plan), each with its own tileset, palette and enemy mix. Difficulty rises with drain rates and timer, not just enemy count.

**Controls.** Joystick or keys. Left/right move, up = jump (mounted) or aim up, fire = shoot, fire + down = dismount/mount, a whistle key summons a spare Runner.

## Technical architecture (CPC 6128)

Mode 0, CRTC hardware scrolling, masked software sprites at 25 fps, firmware off, and one planet per load from the extra 64K.

**Screen.** Mode 0 (160x200, 16 of 27 colours) matches the C64's wide-pixel multicolour look. Playfield in the upper part of the screen; radar, timer and energy in a bottom strip.

**Scrolling.** Move the screen start address (CRTC R12/R13) one character per step, which is 4 Mode 0 pixels; draw the newly exposed tile column at the edge each step. Runner speed = 1 step per 25 Hz frame (100 px/s); on foot the screen stops scrolling, as in the original. A fixed HUD needs a mid-frame CRTC split; if that proves fragile across CRTC types, fall back to redrawing the HUD on the moving screen.

**Depth.** No hardware parallax on the CPC, so fake it: raster palette changes on the 300 Hz interrupt for a sky gradient and a separate HUD palette, plus animated distant-layer tiles. The foreground layer is drawn after sprites so they pass behind it, as Pete Green's 1988 routine did.

**Sprites.** Software, masked, two pre-shifted copies for 1-pixel positioning. Erase by restoring the tiles under each sprite (dirty rectangles), not by saving the background. Double-buffer two 16K screens.

**Memory map**

| Range | Use |
| --- | --- |
| &0000-&3FFF | Code, game state, tile map of current planet, interrupt handler (firmware disabled) |
| &4000-&7FFF | Bank window: pages C4-C7 swap in sprite sheets, tile graphics, music |
| &8000-&BFFF | Screen buffer 2 |
| &C000-&FFFF | Screen buffer 1 |
| Extra 64K | Current planet's tiles, sprites, enemy waves, music; reloaded from disc between planets |

**Frame budget.** A 50 Hz PAL frame is about 19,968 Z80 cycles in NOPs; at 25 fps the game gets about 40,000 per frame. Rough split: column draw 4K, sprite erase/draw (rider, Runner, 6-8 enemies, bullets) 22K, logic and collision 6K, music/SFX 3K, raster/HUD 3K, leaving margin.

**Sound.** AY-3-8912 with an Arkos Tracker 2 player for music and sound effects on a priority channel.

**Toolchain.** Your existing RASM + iDSK under WSL2, an emulator with a debugger (WinAPE or ACE-DL), Tiled for planet maps exported to binary, Arkos Tracker 2 for audio, and a Python converter for Mode 0 sprites, masks and pre-shifts.

## Milestones

Build the riskiest technical piece first (scroll + sprites at 25 fps), then the loop, then content. Each step ends in a bootable .dsk.

1. **Scroll engine.** Firmware off, Mode 0, double buffer, CRTC scroll over a wrap-around test map, new column per step. Done when it scrolls smoothly at 25 fps on CRTC types 0, 1 and 2 in the emulator.
2. **HUD split and rasters.** Fixed bottom HUD via CRTC split, sky gradient, separate HUD palette. Decide here between split and fallback.
3. **Sprite engine.** Masked, pre-shifted sprites with dirty-rectangle restore and foreground occlusion. Done when rider + Runner + 8 enemies hold 25 fps.
4. **Player.** Mounted and on-foot movement, multi-direction shooting, jump, dismount/mount, whistle for a spare Runner.
5. **Generators and radar.** Drain rates, colour states on the radar, recharge minigame, breach waves.
6. **Enemies.** Drifters, trackers that bomb, ground crawlers, rock throwers, breach-carrier mini-boss; collision and energy.
7. **First planet complete.** Timer, win/lose, title screen, high-score table, music and SFX. Playtest for the "rolling demo" problem before going further.
8. **Banking and loading.** Move planet data to the extra 64K; load planets from disc.
9. **Planets 2-4.** New tilesets, palettes and enemy mixes; tune difficulty curve.
10. **Release.** Final .dsk, test on real hardware if available, README and controls card.

## Risks and open questions

- **CRTC split portability.** Mid-frame splits behave differently across CRTC types; the fallback HUD costs frame time.
- **Scroll granularity.** 4-pixel steps can look jerky at slow speeds; on-foot mode avoids it by not scrolling.
- **Sprite count.** 25 fps with large masked sprites is tight; cap on-screen enemies per wave if needed.
- **Name and assets.** Rimrunner, its characters and Palace's art and music belong to their rights holders; a faithful remake under that name would need permission. This plan assumes an original game inspired by it.
- **Open:** 6128 only, or also a reduced 464 version? Disc only, or tape too?

## Sources

- [Rimrunner on Wikipedia](https://en.wikipedia.org/wiki/Rimrunner)
- [Rimrunner on MobyGames](https://www.mobygames.com/game/29262/)
- [Zzap!64 #37 review](https://everygamegoing.com/larticle/Rimrunner-000/28765)
- [C&VG #79 review](https://everygamegoing.com/larticle/Rim-Runner-000/42442)
- [Commodore User #55 review](https://everygamegoing.com/larticle/rimrunner-/53845)
- [Games That Weren't: the cancelled CPC and ST versions](https://www.gamesthatwerent.com/2025/09/rimrunner/)
- [The YouTube longplay (V.E.D.)](https://www.youtube.com/watch?v=0wYBhGsQFGQ)


I have rasm installed, idsk, and Caprice32 snap. Also a small headless cpc emu in the cpcemu directory