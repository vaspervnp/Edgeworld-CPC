"""The CPC's 27 colours: hardware colour byte (as sent to the gate array,
with bit 6 set) and the RGB the monitor shows."""

# name: (hw byte, (r, g, b))
COLOURS = {
    "black":          (0x54, (0, 0, 0)),
    "blue":           (0x44, (0, 0, 128)),
    "bright_blue":    (0x55, (0, 0, 255)),
    "red":            (0x5C, (128, 0, 0)),
    "magenta":        (0x58, (128, 0, 128)),
    "mauve":          (0x5D, (128, 0, 255)),
    "bright_red":     (0x4C, (255, 0, 0)),
    "purple":         (0x45, (255, 0, 128)),
    "bright_magenta": (0x4D, (255, 0, 255)),
    "green":          (0x56, (0, 128, 0)),
    "cyan":           (0x46, (0, 128, 128)),
    "sky_blue":       (0x57, (0, 128, 255)),
    "yellow":         (0x5E, (128, 128, 0)),
    "white":          (0x40, (128, 128, 128)),
    "pastel_blue":    (0x5F, (128, 128, 255)),
    "orange":         (0x4E, (255, 128, 0)),
    "pink":           (0x47, (255, 128, 128)),
    "pastel_magenta": (0x4F, (255, 128, 255)),
    "bright_green":   (0x52, (0, 255, 0)),
    "sea_green":      (0x42, (0, 255, 128)),
    "bright_cyan":    (0x53, (0, 255, 255)),
    "lime":           (0x5A, (128, 255, 0)),
    "pastel_green":   (0x59, (128, 255, 128)),
    "pastel_cyan":    (0x5B, (128, 255, 255)),
    "bright_yellow":  (0x4A, (255, 255, 0)),
    "pastel_yellow":  (0x43, (255, 255, 128)),
    "bright_white":   (0x4B, (255, 255, 255)),
}


def nearest_hw(rgb):
    """Hardware byte of the CPC colour closest to rgb."""
    r, g, b = rgb
    best = min(COLOURS.values(),
               key=lambda c: (c[1][0] - r) ** 2 + (c[1][1] - g) ** 2 + (c[1][2] - b) ** 2)
    return best[0]


def mode0_byte(left, right):
    """Pack two Mode 0 pens (0-15) into a screen byte."""
    def spread(p, shift):
        return (((p >> 0) & 1) << (7 - shift) | ((p >> 1) & 1) << (3 - shift) |
                ((p >> 2) & 1) << (5 - shift) | ((p >> 3) & 1) << (1 - shift))
    return spread(left, 0) | spread(right, 1)
