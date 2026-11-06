"""Graphics helpers: palette, an original 5x7 pixel font, pixel-art sprites and small effects.

Everything here is drawn by hand for MOCHI ARCADE - no third-party art or fonts.
"""
import math
import random

import pygame

W, H = 320, 200  # logical resolution (16:10, scaled up by integer factors)

# ----------------------------------------------------------------------------- palette
PAL = {
    "night": (26, 16, 51),
    "ink": (43, 29, 74),
    "deep": (58, 40, 96),
    "white": (255, 247, 240),
    "cream": (255, 233, 199),
    "pink": (255, 143, 183),
    "hotpink": (255, 79, 139),
    "peach": (255, 179, 138),
    "orange": (255, 138, 61),
    "yellow": (255, 216, 77),
    "lime": (184, 240, 106),
    "mint": (110, 231, 183),
    "teal": (55, 200, 192),
    "sky": (124, 200, 255),
    "blue": (77, 124, 255),
    "lavender": (180, 156, 255),
    "purple": (138, 92, 246),
    "brown": (160, 98, 62),
    "choco": (110, 64, 44),
    "gray": (139, 134, 168),
    "darkgray": (74, 69, 102),
    "red": (255, 77, 90),
    "black": (12, 8, 24),
}

# sprite character -> palette key ('.' is transparent)
CHARS = {
    "k": "black", "i": "ink", "w": "white", "c": "cream", "p": "pink", "P": "hotpink", "e": "peach",
    "o": "orange", "y": "yellow", "l": "lime", "m": "mint", "t": "teal", "s": "sky", "b": "blue",
    "v": "lavender", "u": "purple", "n": "brown", "h": "choco", "g": "gray", "d": "darkgray", "r": "red",
}


def col(name, alpha=None):
    c = PAL[name] if isinstance(name, str) else name
    return c if alpha is None else (c[0], c[1], c[2], alpha)


def lerp_col(a, b, t):
    a, b = col(a), col(b)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ----------------------------------------------------------------------------- font
_F = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.", "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####", "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.####", "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.", "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.", "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#", "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.", "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.", "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.", "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####", "3": "####.|....#|....#|.###.|....#|....#|####.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.", "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.", "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.", "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    " ": ".....|.....|.....|.....|.....|.....|.....", ".": ".....|.....|.....|.....|.....|.##..|.##..",
    ",": ".....|.....|.....|.....|.##..|..#..|.#...", "!": "..#..|..#..|..#..|..#..|..#..|.....|..#..",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..", ":": ".....|.##..|.##..|.....|.##..|.##..|.....",
    "-": ".....|.....|.....|.###.|.....|.....|.....", "+": ".....|..#..|..#..|#####|..#..|..#..|.....",
    "/": "....#|....#|...#.|..#..|.#...|#....|#....", "%": "##..#|##.#.|...#.|..#..|.#...|.#.##|#..##",
    "(": "...#.|..#..|.#...|.#...|.#...|..#..|...#.", ")": ".#...|..#..|...#.|...#.|...#.|..#..|.#...",
    "'": "..#..|..#..|.#...|.....|.....|.....|.....", '"': ".#.#.|.#.#.|.....|.....|.....|.....|.....",
    "<": "...#.|..#..|.#...|#....|.#...|..#..|...#.", ">": ".#...|..#..|...#.|....#|...#.|..#..|.#...",
    "=": ".....|.....|#####|.....|#####|.....|.....", "*": ".....|#.#.#|.###.|#####|.###.|#.#.#|.....",
    "#": ".#.#.|.#.#.|#####|.#.#.|#####|.#.#.|.#.#.", "_": ".....|.....|.....|.....|.....|.....|#####",
    "^": "..#..|.#.#.|#...#|.....|.....|.....|.....", "&": ".##..|#..#.|#.#..|.#...|#.#.#|#..#.|.##.#",
    # icons on otherwise unused characters: @ heart, ~ note, $ star, { left arrow, } right arrow, | up, ` down
    "@": ".....|.#.#.|#####|#####|.###.|..#..|.....", "~": "..##.|..#.#|..#..|..#..|.##..|###..|.#...",
    "$": "..#..|..#..|#####|.###.|.###.|##.##|#...#", "{": "...#.|..##.|.###.|####.|.###.|..##.|...#.",
    "}": ".#...|.##..|.###.|.####|.###.|.##..|.#...", "|": "..#..|.###.|#####|..#..|..#..|..#..|.....",
    "`": ".....|..#..|..#..|..#..|#####|.###.|..#..",
}
FONT = {k: [r for r in v.split("|")] for k, v in _F.items()}
_text_cache = {}


def text_width(s, scale=1):
    return len(s) * 6 * scale - scale if s else 0


def render_text(s, color="white", scale=1):
    key = (s, color if isinstance(color, str) else tuple(color), scale)
    surf = _text_cache.get(key)
    if surf is None:
        s2 = s.upper()
        surf = pygame.Surface((max(1, text_width(s2, scale)), 7 * scale), pygame.SRCALPHA)
        c = col(color)
        for i, ch in enumerate(s2):
            g = FONT.get(ch, FONT["?"])
            for y, row in enumerate(g):
                for x, px in enumerate(row):
                    if px == "#":
                        surf.fill(c, ((i * 6 + x) * scale, y * scale, scale, scale))
        if len(_text_cache) > 600:
            _text_cache.clear()
        _text_cache[key] = surf
    return surf


def draw_text(dst, s, x, y, color="white", scale=1, align="left", shadow="ink", outline=None):
    """align: left | center | right. shadow: palette name or None. outline: palette name or None."""
    w = text_width(s.upper(), scale)
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    if outline:
        o = render_text(s, outline, scale)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            dst.blit(o, (x + dx * scale, y + dy * scale))
    elif shadow:
        dst.blit(render_text(s, shadow, scale), (x + scale, y + scale))
    dst.blit(render_text(s, color, scale), (x, y))
    return w


def draw_wavy(dst, s, x, y, t, color="white", scale=2, outline="ink", amp=2.0, align="center"):
    """Title text where each letter bobs on a sine wave."""
    s = s.upper()
    w = text_width(s, scale)
    if align == "center":
        x -= w // 2
    for i, ch in enumerate(s):
        dy = int(math.sin(t * 4 + i * 0.6) * amp)
        c = color(i) if callable(color) else color
        draw_text(dst, ch, x + i * 6 * scale, y + dy, c, scale, outline=outline, shadow=None)


# ----------------------------------------------------------------------------- sprites
_sprite_cache = {}


def make_sprite(rows, remap=None):
    """rows: list of equal-length strings using CHARS; remap: {char: char} for recolored variants."""
    h, w = len(rows), max(len(r) for r in rows)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if remap and ch in remap:
                ch = remap[ch]
            if ch != "." and ch in CHARS:
                surf.set_at((x, y), PAL[CHARS[ch]])
    return surf


def sprite(name, frame=0, flip=False, remap=None, scale=1):
    from mochi_arcade import sprites as S  # local import: art lives in its own module

    key = (name, frame, flip, tuple(sorted(remap.items())) if remap else None, scale)
    s = _sprite_cache.get(key)
    if s is None:
        data = S.ART[name]
        rows = data[frame % len(data)] if isinstance(data[0], list) else data
        s = make_sprite(rows, remap)
        if flip:
            s = pygame.transform.flip(s, True, False)
        if scale != 1:
            s = pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))
        _sprite_cache[key] = s
    return s


# ----------------------------------------------------------------------------- drawing helpers
def panel(dst, rect, fill="ink", border="lavender", radius=4, shadow=True):
    r = pygame.Rect(rect)
    if shadow:
        pygame.draw.rect(dst, col("black"), r.move(2, 2), border_radius=radius)
    pygame.draw.rect(dst, col(fill), r, border_radius=radius)
    pygame.draw.rect(dst, col(border), r, 1, border_radius=radius)


def bubble(dst, cx, cy, r, t=0.0, tint="sky"):
    """Soap bubble with a rim and a moving highlight."""
    s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(s, col(tint, 60), (r + 1, r + 1), r)
    pygame.draw.circle(s, col(tint, 230), (r + 1, r + 1), r, 1)
    hx = r + 1 - int(r * 0.45) + int(math.sin(t * 3) * 1)
    hy = r + 1 - int(r * 0.45)
    pygame.draw.circle(s, col("white", 230), (hx, hy), max(1, r // 4))
    pygame.draw.circle(s, col("white", 140), (r + 1 + r // 3, r + 1 + r // 3), max(1, r // 7))
    dst.blit(s, (int(cx) - r - 1, int(cy) - r - 1))


def checker_bg(dst, t, a="night", b="ink", size=16, speed=8):
    dst.fill(col(a))
    off = int(t * speed) % (size * 2)
    cb = col(b)
    for y in range(-size * 2, H + size * 2, size):
        for x in range(-size * 2, W + size * 2, size):
            if ((x + y) // size) % 2 == 0:
                dst.fill(cb, (x + off, y + off // 2, size, size))


class Stars:
    """Parallax starfield."""

    def __init__(self, n=70, seed=3):
        rnd = random.Random(seed)
        self.s = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.choice((1, 1, 1, 2, 3))] for _ in range(n)]

    def update(self, dt, speed=20):
        for st in self.s:
            st[1] += speed * st[2] * dt
            if st[1] > H:
                st[1] -= H
                st[0] = random.uniform(0, W)

    def draw(self, dst, t=0):
        for x, y, z in self.s:
            c = ("darkgray", "lavender", "white")[z - 1]
            if z == 3 and int(t * 6 + x) % 7 == 0:
                c = "yellow"
            dst.fill(col(c), (int(x), int(y), 1, 1 if z < 3 else 2))


class Particles:
    def __init__(self):
        self.p = []

    def burst(self, x, y, n=10, colors=("white", "pink", "yellow"), speed=60, life=0.6, grav=80, size=1):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(speed * 0.4, speed)
            self.p.append([x, y, math.cos(a) * v, math.sin(a) * v - speed * 0.3, life, life,
                           random.choice(colors), grav, size])

    def sparkle(self, x, y, color="yellow"):
        self.p.append([x, y, random.uniform(-10, 10), random.uniform(-30, -10), 0.5, 0.5, color, 0, 1])

    def update(self, dt):
        for q in self.p:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[3] += q[7] * dt
            q[4] -= dt
        self.p = [q for q in self.p if q[4] > 0]

    def draw(self, dst, ox=0, oy=0):
        for x, y, _, _, life, full, c, _, size in self.p:
            if life < full * 0.3 and int(life * 30) % 2:
                continue
            dst.fill(col(c), (int(x) + ox, int(y) + oy, size, size))


class FloatText:
    """'+100' style popups."""

    def __init__(self):
        self.items = []

    def add(self, x, y, s, color="yellow"):
        self.items.append([x, y, s, color, 0.9])

    def update(self, dt):
        for it in self.items:
            it[1] -= 18 * dt
            it[4] -= dt
        self.items = [i for i in self.items if i[4] > 0]

    def draw(self, dst, ox=0, oy=0):
        for x, y, s, c, _ in self.items:
            draw_text(dst, s, int(x) + ox, int(y) + oy, c, align="center")


def scanlines(dst, strength=40):
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    c = (0, 0, 0, strength)
    for y in range(0, H, 2):
        ov.fill(c, (0, y, W, 1))
    dst.blit(ov, (0, 0))
