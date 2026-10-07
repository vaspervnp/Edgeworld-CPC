# SHIELDRUNNER

### Player's manual — Amstrad CPC 6128

![The loading screen](img/loading.png)

Shieldrunner is an original action game for the Amstrad CPC 6128. You ride
the Runner, a great long-legged beast, around the rim of four frontier
planets, keeping their shield generators charged while the enemy pours in.

<div class="pagebreak"></div>

## Contents

1. The job
2. What you need and loading
3. The title screen
4. The screen
5. Controls
6. Riding the Runner
7. On foot: recharging the generators
8. The generators and the shield
9. The enemies
10. Your Runner, spares and energy
11. The planets
12. Pausing and giving up
13. Clearing a planet, scoring and high scores
14. Tips

## 1. The job

Each planet is protected by a shield, kept up by **four shield generators**
spread around its rim. The generators drain all the time, each at its own
rate. Your job is to keep them charged until the planet's clock runs out.

- If **three** generators are drained at once, the shield fails and the
  game is over.
- If your **energy** runs out, you fall and the game is over.
- Hold out until the time runs out and the planet is safe: on to the next.

Save all four planets and you have won.

## 2. What you need and loading

You need an **Amstrad CPC 6128**, a **6128 Plus**, or any CPC with 64K of
extra memory, or an emulator such as Caprice32, WinAPE or ACE-DL. On a CPC
with only 64K the loader says so and stops.

Put the disc in and type:

```
RUN"SHIELD
```

First the **Revive8bit** screen appears. It stays for 10 seconds; press
**Space** to go on at once.

![The Revive8bit screen](img/splash.png)

Then the **loading screen** appears and stays while the game loads.

![The loading screen while the game loads](img/loading.png)

**Leave the disc in the drive.** Each planet is loaded from it when you
reach it.

## 3. The title screen

The title screen shows the first planet with the title over its sky. Below
it, two pages take turns every few seconds: a reminder of how to play, and
the **high-score table**.

![The title: how to play](img/title.png)

![The title: the high scores](img/hiscores.png)

Press **fire** to start. **M** turns the music off or on, here and in the
game.

## 4. The screen

The top of the screen is the **playfield**: the planet's surface, scrolling
as you ride. Below it is the **panel**:

![The panel](img/hud.png)

- **Radar** (the long strip): the whole planet, all the way round. The four
  squares are the generators: **green** holding, **flashing** unstable (see
  to it soon), **red** drained. The white mark is you.
- **TIME:** how long you still have to hold the shield.
- **RUNNERS:** your spare Runners (green squares).
- **PLANET:** which planet you are on (1 to 4).
- **SCORE:** your score.
- **ENERGY:** your own energy. Green, then yellow below half, red below a
  quarter.
- **SHIELD:** the charge of the generator nearest you, in the colour of its
  state.

## 5. Controls

Use a **joystick**, or the **cursor keys** with **Space** to fire.

| Input | Riding | On foot |
|-------|--------|---------|
| Left / Right | Ride: the Runner speeds up, skids round to turn, coasts to a stop | Walk (the screen does not scroll) |
| Up | Jump | Aim up |
| Fire | Shoot forward | Shoot forward |
| Fire + Up | Shoot diagonally up | Shoot straight up, or diagonally with Left / Right |
| Fire + Down | Get off | Get on (standing at the Runner) |
| Down (held) | | Recharge, standing at a generator |
| W | | Whistle for the Runner, or for a spare |

| Key | |
|-----|--|
| P | Pause. P again goes on; Esc gives up the game |
| M | Music off or on (the sound effects stay) |

## 6. Riding the Runner

On the Runner you are fast: it speeds up to the speed of the scrolling
screen, and the view keeps it in the middle. To turn round, push the other
way: it skids, slows and turns. Let go and it coasts to a stop.

![Riding, firing at a drifter](img/riding.png)

Press **up** to **jump**. Jumping is the way over **crawlers**, which walk
along the ground.

![Jumping](img/jump.png)

Riding, you shoot forward, or diagonally up with fire and up together.

## 7. On foot: recharging the generators

The generators can only be recharged on foot. Ride to the generator, press
**fire and down** to get off (the Runner waits where it stands), walk to
the generator's base and **hold down**. The rider plugs in and the
generator charges slowly.

![Recharging: the core flashes white](img/charging.png)

While you hold down, the generator's **core pulses**. Press **fire while it
flashes white** to pump in a big boost of charge. Press fire at the wrong
time and charging **stalls** for a second. Let go of down to unplug.

On foot the screen does not scroll, and you walk slowly. Fire with up
shoots straight up, or diagonally with left or right. To get back on, stand
at the Runner and press **fire and down**.

## 8. The generators and the shield

The radar shows every generator's state. A **flashing** generator is
running low: go to it. A **red** generator is drained: a **breach** opens
and a wave of enemies pours out of it.

With **two** generators drained, the **breach carrier** comes: a great
saucer that takes **twelve bolts** to bring down and bombs you from above.
With **three** drained, the shield fails and the game is over.

![Two generators drained: the breach carrier](img/breach.png)

A drained generator can still be recharged: it comes back as you charge it.

## 9. The enemies

| | Enemy | What it does | How to beat it |
|-|-------|--------------|----------------|
| ![Drifter](img/g_drifter.png) | **Drifter** | Floats towards you and explodes against you | Shoot it before it reaches you |
| ![Tracker](img/g_tracker.png) | **Tracker** | Sweeps overhead dropping bombs | It hangs still for a moment after each bomb: shoot straight up then |
| ![Crawler](img/g_crawler.png) | **Crawler** | Walks the ground at you | Jump it when riding; shoot it on foot |
| ![Thrower](img/g_thrower.png) | **Thrower** | Walks into view and lobs rocks that land where you stand | Keep moving, walk at it and shoot |
| ![Breach carrier](img/g_carrier.png) | **Breach carrier** | Comes with two generators drained; bombs from above | Twelve bolts |
| ![Energy cell](img/g_cell.png) | **Energy cell** | Sometimes left by a shot enemy; falls to the ground | Touch it for a quarter of your energy back |

## 10. Your Runner, spares and energy

![The Runner, ridden](img/g_runner.png) ![The rider on foot](img/g_rider.png)

**Riding**, hits fall on the **Runner**. Each costs you a little energy, but
after **three hits** the Runner dies and throws you off. After any hit you
flash for a moment and cannot be hit again.

**On foot**, every hit costs you a lot more energy, and knocks you off a
generator you are charging.

Press **W** to **whistle**: your Runner runs over to you and waits. If it
is dead, a **spare** comes in from the edge of the screen (you start with
three, shown under RUNNERS). With no spares left, no Runner comes.

Your **energy** is full at the start of each planet. Energy cells give
some back.

## 11. The planets

![The four planets](../planets.png)

| # | Planet | Its enemies | Time |
|---|--------|-------------|------|
| 1 | **Ferros**, the rust moon | a bit of everything | 3:00 |
| 2 | **Glacis**, the ice world | trackers swarm | 3:15 |
| 3 | **Mesa Ra**, the desert | crawlers and throwers | 3:30 |
| 4 | **Pyre**, the volcanic world | everything, faster | 3:45 |

Each planet's generators drain faster and start lower than the last.

## 12. Pausing and giving up

Press **P** to pause: the picture stops and the sound goes quiet. **P**
again goes on; **Esc** gives up the game.

![Paused](img/pause.png)

## 13. Clearing a planet, scoring and high scores

When the time runs out with the shield still up, the planet is clear. The
energy you have left and the charge in the generators make a **bonus**.
Then the next planet loads, and you go on with your score and spare
Runners and a full energy bar.

![Planet clear, with the bonus](img/clear.png)

| Shot down | Points |
|-----------|--------|
| Drifter | 10 |
| Tracker | 20 |
| Crawler | 20 |
| Thrower | 30 |
| Breach carrier | 200 |

At the end of a game, a score good enough for the table asks for your
**initials**: **up** and **down** choose a letter, **fire** takes it.

![A new high score](img/entry.png)

The high-score table is kept until you switch off: it is not saved to
disc.

## 14. Tips

- Watch the radar. Go to a **flashing** generator before it turns red.
- Ride to a generator and get off right beside it: the Runner waits there
  for you.
- Pump with **fire on the white flash** only. A wrong press costs a second.
- **Crawlers:** jump them when riding. On foot, shoot them from afar.
- **Trackers** hang still just after they bomb: shoot straight up then.
- **Throwers** stop to lob their rocks: walk at them and shoot.
- Pick up **energy cells**. They fall where an enemy was shot.
- Don't let two generators drain: the breach carrier is hard work.

---

*Shieldrunner is an original game for the Amstrad CPC 6128, inspired by
Rimrunner (Palace Software, 1988).*
