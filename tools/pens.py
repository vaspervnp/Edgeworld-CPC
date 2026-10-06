"""The playfield's pens, shared by the planets, the sprites and the logo.

Sprites share the playfield palette, so their pens keep the same colours on
every planet; each planet has four pens of its own (3-6) and its sky.

  0       black (space, and transparent in sprites)
  1       the sky: the raster interrupts give it three colours a frame
  2       the generator core: the game sets it to show the state
  3-6     the planet's own colours (assets/planets/planetN.json)
  7-15    fixed, used by sprites, generators and anything shared
"""
BLACK, SKY, CORE = 0, 1, 2
P1, P2, P3, P4 = 3, 4, 5, 6
WHITE, YELLOW, ORANGE, RED, GREY, GREEN, DGREEN, MAGENTA, PBLUE = range(7, 16)

FIXED = {
    BLACK: "black", CORE: "bright_green",
    WHITE: "bright_white", YELLOW: "bright_yellow", ORANGE: "orange", RED: "bright_red",
    GREY: "white", GREEN: "bright_green", DGREEN: "green", MAGENTA: "magenta",
    PBLUE: "pastel_blue",
}


def palette(planet_colours, sky="black"):
    """The 16 colour names of a planet with its 4 colours (pens 3-6)."""
    assert len(planet_colours) == 4
    names = [FIXED.get(p) for p in range(16)]
    names[SKY] = sky
    names[P1:P4 + 1] = planet_colours
    return names
