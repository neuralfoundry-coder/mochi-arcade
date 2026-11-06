"""MEOW DECK pixel art, painted procedurally into sprite rows.

A tiny character-grid painter (ellipses, polygons, outlines) draws every cat portrait, the hero TOFU, the foes,
the bosses and the UI icons. The result is plain sprite rows registered in sprites.ART (prefix "md_"), so the iOS
port gets exactly the same pixels through ios/tools/gen_data.py - no drawing code to keep in step.

Cat portraits are 24x24: breed (coat + markings + ear shape), eye colour, expression (from the card role) and an
accessory are combined, so every card in the deck gets its own face. Frame 1 of each portrait is the blink.
"""

# ----------------------------------------------------------------------------- painter
class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [["."] * w for _ in range(h)]

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = c

    def get(self, x, y):
        return self.g[y][x] if 0 <= x < self.w and 0 <= y < self.h else "."

    def rect(self, x, y, w, h, c, only=None):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if only is None or self.get(xx, yy) in only:
                    self.put(xx, yy, c)

    def ell(self, cx, cy, rx, ry, c, only=None):
        """Filled ellipse through pixel centres (cx, cy may be fractional; cx=12 is symmetric in a 24 grid)."""
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                dx = (x + 0.5 - cx) / rx
                dy = (y + 0.5 - cy) / ry
                if dx * dx + dy * dy <= 1.0 and (only is None or self.get(x, y) in only):
                    self.put(x, y, c)

    def poly(self, pts, c, only=None):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            sy = y + 0.5
            xs = []
            for i in range(len(pts)):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % len(pts)]
                if (ay <= sy < by) or (by <= sy < ay):
                    xs.append(ax + (sy - ay) / (by - ay) * (bx - ax))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(round(xs[i])), int(round(xs[i + 1]))):
                    if only is None or self.get(x, y) in only:
                        self.put(x, y, c)

    def line(self, x0, y0, x1, y1, c):
        dx, sx = abs(x1 - x0), (1 if x0 < x1 else -1)
        dy, sy = -abs(y1 - y0), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.put(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def outline(self, c="k"):
        add = []
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != ".":
                    continue
                if any(self.get(x + dx, y + dy) not in (".", c) and self.get(x + dx, y + dy) != "#"
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    add.append((x, y))
        for x, y in add:
            self.g[y][x] = c

    def mirror(self):
        out = Grid(self.w, self.h)
        out.g = [row[::-1] for row in self.g]
        return out

    def rows(self):
        return ["".join(r) for r in self.g]


# ----------------------------------------------------------------------------- cat portraits
# coat: base, marking, muzzle, inner ear, pattern, ear shape
BREEDS = {
    "tabby":    ("n", "h", "c", "p", "stripes", "point"),
    "ginger":   ("o", "n", "c", "p", "stripes", "point"),
    "gray":     ("g", "d", "w", "p", "solid", "point"),
    "black":    ("i", "d", "i", "u", "solid", "point"),
    "white":    ("w", "c", "w", "p", "solid", "point"),
    "tuxedo":   ("i", "d", "w", "p", "tux", "point"),
    "calico":   ("w", "o", "w", "p", "calico", "point"),
    "tortie":   ("i", "o", "i", "p", "tortie", "point"),
    "siamese":  ("c", "h", "h", "e", "points", "point"),
    "bengal":   ("e", "h", "c", "p", "spots", "point"),
    "sphynx":   ("e", "p", "e", "P", "wrinkle", "big"),
    "longhair": ("v", "w", "w", "p", "fluff", "point"),
    "fold":     ("c", "e", "w", "p", "solid", "fold"),
    "munchkin": ("e", "o", "w", "p", "stripes", "point"),
    "coon":     ("n", "h", "c", "p", "mane", "tuft"),
}
BREED_LABEL = {"tabby": "TABBY", "ginger": "GINGER", "gray": "GRAY", "black": "BLACK", "white": "WHITE",
               "tuxedo": "TUXEDO", "calico": "CALICO", "tortie": "TORTIE", "siamese": "SIAMESE",
               "bengal": "BENGAL", "sphynx": "SPHYNX", "longhair": "FLUFFY", "fold": "FOLD",
               "munchkin": "MUNCHKIN", "coon": "COON", "gold": "GOLDEN", "bug": "PEST"}
ROLE_FACE = {"swipe": "fierce", "curl": "sleepy", "purr": "happy", "curious": "wide", "zoomies": "excited",
             "hiss": "hiss"}


def _ears(g, shape, base, inner):
    if shape == "fold":   # folded flaps lying on the head
        for side in (0, 1):
            pts = [(4, 8), (9, 5), (10, 8)] if side == 0 else [(20, 8), (15, 5), (14, 8)]
            g.poly(pts, base)
        return
    if shape == "big":
        L = [(1.5, 11), (3, 0.5), (11, 6)]
    else:
        L = [(3, 10), (5, 1.5), (11, 6)]
    for pts in (L, [(24 - x, y) for x, y in L]):
        g.poly(pts, base)
    # inner ear
    if shape == "big":
        IL = [(3.5, 9), (4, 3), (8.5, 6.5)]
    else:
        IL = [(4.5, 8), (5.5, 4), (8.8, 6.6)]
    for pts in (IL, [(24 - x, y) for x, y in IL]):
        g.poly(pts, inner)
    if shape == "tuft":   # lynx tips
        for x in (5, 18):
            g.put(x, 0, base)
            g.put(x, 1, base)


def _head(g, base, pattern):
    if pattern in ("fluff", "mane"):
        # fluffy cheeks: a wider head with jagged sides
        g.ell(12, 13.5, 9.5, 7.5, base)
        for y, dx in ((12, 11), (14, 11), (16, 10), (18, 9)):
            g.put(12 - dx - 1, y, base)
            g.put(12 + dx, y, base)
    else:
        g.ell(12, 13.5, 8.6, 7.6, base)


def _body(g, base, pattern, muzzle, munchkin):
    g.ell(12, 25.5, 9.5, 6.5, base)
    if pattern in ("tux", "fluff", "mane", "calico") or munchkin:
        g.ell(12, 25, 4.5, 4.5, muzzle if pattern != "mane" else "c")
    if munchkin:   # stubby little paws peeking at the bottom
        for x in (7, 14):
            g.rect(x, 21, 3, 3, "w")
            g.put(x + 1, 23, "p")


def _markings(g, spec):
    base, mark, muzzle, _, pattern, _ = BREEDS[spec["breed"]]
    head = (base,)
    if pattern == "stripes":
        for x0 in (10, 12, 14):      # forehead stripes
            g.rect(x0 - 1, 7, 1, 3 if x0 == 12 else 2, mark, head)
        for y in (12, 15):           # cheek stripes
            g.rect(3, y, 3, 1, mark, head)
            g.rect(18, y, 3, 1, mark, head)
    elif pattern == "spots":
        for x, y in ((6, 9), (9, 8), (14, 8), (17, 9), (5, 15), (18, 15), (12, 7)):
            g.rect(x, y, 2, 1, mark, head)
            g.put(x, y + 1, "o")
    elif pattern == "calico":
        g.ell(7, 9, 5, 4.2, "o", ("w",))
        g.ell(18, 10, 4, 3.2, "i", ("w",))
        g.ell(5.5, 4.5, 2.6, 4, "o", ("w",))   # ear patch
        g.ell(18.5, 4.5, 2.6, 4, "i", ("w",))
    elif pattern == "tortie":
        for x, y, rx, ry, c in ((7, 9, 3.5, 2.5, "o"), (17, 15, 3, 2.5, "o"), (15, 7, 2, 1.5, "n"),
                                (5, 15, 2, 2, "n"), (12, 9, 1.2, 2.5, "o")):
            g.ell(x, y, rx, ry, c, ("i",))
    elif pattern == "points":   # siamese: dark mask and ears
        g.ell(12, 16, 5, 4, mark, ("c",))
        g.ell(5.5, 5, 3, 4, mark, ("c",))
        g.ell(18.5, 5, 3, 4, mark, ("c",))
    elif pattern == "wrinkle":
        for y in (8, 10):
            g.rect(10, y, 4, 1, mark)
    elif pattern == "tux":
        g.poly([(12, 9), (8.5, 21), (15.5, 21)], "w", ("i",))
    elif pattern == "mane":
        g.ell(12, 21.5, 8.5, 3.5, "c", ("n",))
        for x0 in (10, 12, 14):
            g.rect(x0 - 1, 7, 1, 2, mark, head)
    elif pattern == "fluff":
        g.ell(12, 20.5, 7.5, 3, "w", ("v",))
    # muzzle
    g.ell(12, 16.6, 3.6, 2.6, muzzle, None if pattern != "points" else (mark,))


def _eyes(g, spec, blink):
    face = spec["face"]
    col_l = spec["eyes"]
    col_r = spec.get("eyes2", col_l)
    if face == "sleepy" or blink:
        for x0 in (6, 15):
            g.rect(x0, 13, 3, 1, "k")
            g.put(x0 + (0 if x0 < 12 else 2), 12, "k")
        return
    if face == "happy":
        for x0 in (6, 15):
            g.put(x0, 13, "k")
            g.put(x0 + 1, 12, "k")
            g.put(x0 + 2, 13, "k")
        return
    for x0, c in ((6, 15), (col_l, col_r)) if False else ((6, col_l), (15, col_r)):
        if face == "wide":
            g.rect(x0, 10, 3, 4, c)
            g.rect(x0 + 1, 11, 1, 3, "k")
            g.put(x0, 10, "w")
            g.put(x0, 11, "w")
        elif face == "fierce":
            g.rect(x0, 12, 3, 2, c)
            g.put(x0 + 1, 12, "k")
            g.put(x0 + 1, 13, "k")
            # angry brows slanting to the nose
            if x0 < 12:
                g.line(x0, 10, x0 + 2, 11, "k")
            else:
                g.line(x0, 11, x0 + 2, 10, "k")
        elif face == "hiss":
            g.rect(x0, 12, 3, 2, c)
            g.put(x0 + 1, 12, "k")
            g.put(x0 + 1, 13, "k")
            if x0 < 12:
                g.line(x0, 11, x0 + 2, 11, "k")
            else:
                g.line(x0, 11, x0 + 2, 11, "k")
        elif face == "excited":
            g.rect(x0, 11, 3, 3, c)
            g.put(x0 + 1, 12, "k")
            g.put(x0 + 1, 13, "k")
            g.put(x0, 11, "w")
        else:   # open
            g.rect(x0, 11, 3, 3, c)
            g.put(x0 + 1, 12, "k")
            g.put(x0 + 1, 13, "k")
            g.put(x0, 11, "w")


def _mouth(g, spec):
    face = spec["face"]
    nose = "P" if spec["breed"] in ("sphynx", "white", "calico") else "p"
    g.rect(11, 15, 2, 1, nose)
    if face == "hiss":
        g.rect(10, 17, 4, 2, "r")
        g.put(10, 17, "w")
        g.put(13, 17, "w")
        g.rect(10, 16, 1, 1, "k")
        g.rect(13, 16, 1, 1, "k")
        g.rect(11, 16, 2, 1, "k")
        return
    if face == "excited":
        g.put(10, 16, "k")
        g.put(13, 16, "k")
        g.rect(11, 17, 2, 1, "k")
        g.rect(11, 18, 2, 1, "P")
        return
    g.put(10, 17, "k")
    g.put(11, 16, "k")
    g.put(12, 16, "k")
    g.put(13, 17, "k")


def _whiskers(g, spec):
    wc = "w" if spec["breed"] in ("black", "tuxedo", "tortie") else "c" if spec["breed"] != "white" else "g"
    for y0, y1 in ((15, 14), (17, 18)):
        for x in range(0, 3):
            yy = y0 if x > 0 else y1
            if g.get(x, yy) == ".":
                g.put(x, yy, wc)
            if g.get(23 - x, yy) == ".":
                g.put(23 - x, yy, wc)


# accessories drawn before the outline (they change the silhouette) ...
def _acc_before(g, acc):
    if acc == "bow":
        g.poly([(15, 2), (19, 0), (19, 5)], "P")
        g.poly([(23, 2), (19, 0), (19, 5)], "P")
        g.rect(18, 1, 2, 3, "p")
    elif acc == "party":
        g.poly([(9, 6), (12, -3), (15, 6)], "s")
        for y, c in ((4, "y"), (1, "P")):
            g.rect(9, y, 7, 1, c, ("s",))
        g.put(12, 0, "y")
    elif acc == "captain":
        g.ell(12, 4.5, 8, 3.5, "w")
        g.rect(5, 5, 14, 2, "i")
        g.rect(4, 7, 16, 1, "k")
        g.rect(11, 3, 2, 2, "y")
    elif acc == "crown":
        g.poly([(6, 7), (6, 0.5), (9, 3.5), (12, 0), (15, 3.5), (18, 0.5), (18, 7)], "y")
        g.rect(11, 4, 2, 2, "r")
        g.rect(6, 6, 13, 1, "o")
    elif acc == "witch":
        g.rect(2, 6, 20, 2, "u")
        g.poly([(7, 6), (14, -2), (19, 1), (16, 6)], "u")
        g.rect(8, 5, 9, 1, "l", ("u",))
    elif acc == "beanie":
        g.ell(12, 6.5, 8, 4.5, "r")
        g.rect(4, 7, 16, 2, "w")
        g.ell(12, 1.5, 2, 1.6, "w")
    elif acc == "chef":
        g.ell(12, 3, 6.5, 3.6, "w")
        g.rect(7, 4, 10, 4, "w")
        g.rect(7, 7, 10, 1, "c")
    elif acc == "top":
        g.rect(7, -1, 10, 7, "k")
        g.rect(4, 6, 16, 1, "k")
        g.rect(7, 4, 10, 1, "r")
    elif acc == "headband":
        g.rect(3, 8, 18, 2, "r")
        g.poly([(20, 8), (24, 6), (24, 8)], "r")
        g.poly([(20, 9), (24, 11), (23, 12)], "r")
    elif acc == "nurse":
        g.poly([(7, 7), (8, 2), (16, 2), (17, 7)], "w")
        g.rect(11, 3, 2, 3, "r")
        g.rect(10, 4, 4, 1, "r")
    elif acc == "scarf":
        g.rect(4, 20, 16, 3, "r")
        g.rect(15, 20, 3, 4, "r")
        for x in range(5, 19, 3):
            g.put(x, 21, "y")
    elif acc == "scarf2":
        g.rect(4, 20, 16, 3, "t")
        g.rect(6, 20, 3, 4, "t")
        for x in range(5, 19, 3):
            g.put(x, 21, "w")
    elif acc == "bandana":
        g.poly([(5, 20), (19, 20), (12, 24)], "r")
        g.put(9, 21, "w")
        g.put(14, 21, "w")
    elif acc == "nightcap":
        g.poly([(4, 8), (11, 1), (20, 8)], "s")
        g.poly([(11, 1), (2, 3), (4, 6)], "s")
        g.ell(2, 4, 1.6, 1.6, "w")
        g.rect(4, 7, 16, 1, "w")
    elif acc == "beret":
        g.ell(10, 5, 8, 3, "P")
        g.put(10, 1, "P")
    elif acc == "halo":
        pass
    elif acc == "headphones":
        g.ell(12, 6, 9.5, 5.5, "d", None)
        g.ell(12, 6.5, 8.5, 4.5, ".", ("d",))
        for x in (1, 20):
            g.rect(x, 10, 3, 6, "P")
    elif acc == "sweat":
        g.rect(4, 8, 16, 2, "y")
        g.rect(4, 8, 16, 1, "o")
    elif acc == "flower":
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            g.put(18 + dx, 4 + dy, "P")
        g.put(18, 4, "y")
    elif acc == "leaf":
        g.poly([(12, 5), (9, 0), (15, 1)], "l")
        g.line(12, 5, 12, 2, "t")
    elif acc == "goggles":
        g.rect(3, 7, 18, 1, "n")
        for x0 in (6, 13):
            g.rect(x0, 6, 5, 3, "s")
            g.rect(x0 + 1, 7, 3, 1, "w")
    elif acc == "bell":
        g.rect(5, 20, 14, 2, "P")
        g.rect(11, 21, 2, 3, "y")
        g.put(11, 23, "o")
    elif acc == "tie":
        g.poly([(8, 20), (12, 22), (8, 24)], "r")
        g.poly([(16, 20), (12, 22), (16, 24)], "r")
        g.rect(11, 21, 2, 2, "P")
    elif acc == "cape":
        g.rect(3, 20, 18, 4, "u")
        g.rect(10, 20, 4, 1, "y")
    elif acc == "astro":
        g.ell(12, 13, 11.5, 11, "s", None)
    elif acc == "gold":
        g.poly([(7, 7), (7, 1), (10, 4), (12, 0), (14, 4), (17, 1), (17, 7)], "y")
        g.rect(11, 3, 2, 2, "P")


# ... and on top of the face
def _acc_after(g, acc):
    if acc == "glasses":
        for x0 in (5, 14):
            g.rect(x0, 10, 5, 1, "k")
            g.rect(x0, 14, 5, 1, "k")
            g.rect(x0, 11, 1, 3, "k")
            g.rect(x0 + 4, 11, 1, 3, "k")
        g.rect(10, 11, 4, 1, "k")
    elif acc == "shades":
        g.rect(4, 11, 16, 1, "k")
        for x0 in (5, 14):
            g.rect(x0, 11, 5, 3, "k")
            g.put(x0 + 1, 12, "s")
    elif acc == "eyepatch":
        g.rect(14, 10, 5, 4, "k")
        g.line(3, 8, 14, 11, "k")
        g.line(18, 11, 21, 13, "k")
    elif acc == "monocle":
        for (x, y) in ((14, 10), (15, 10), (16, 10), (17, 10), (18, 11), (18, 12), (18, 13), (17, 14), (16, 14),
                       (15, 14), (14, 13), (14, 12), (14, 11)):
            g.put(x, y, "y")
        g.line(18, 14, 20, 19, "y")
    elif acc == "mask":
        g.rect(4, 10, 16, 5, "k", ("i", "d", "w", "o", "n", "c", "e", "g", "v", "p", "h"))
        for x0 in (6, 15):
            g.rect(x0, 12, 3, 1, "w")
    elif acc == "halo":
        g.rect(7, 0, 10, 1, "y")
        g.put(6, 1, "y")
        g.put(17, 1, "y")
        g.rect(7, 2, 10, 1, "o")
    elif acc == "blush":
        g.rect(4, 15, 2, 1, "P")
        g.rect(18, 15, 2, 1, "P")
    elif acc == "astro":
        g.put(4, 5, "w")
        g.put(5, 4, "w")
        g.put(6, 4, "w")


def paint_cat(spec, blink=False):
    """spec: breed, eyes (+ eyes2), face, acc, munchkin flag. Returns 24 sprite rows."""
    g = Grid(24, 24)
    base, mark, muzzle, inner, pattern, ears = BREEDS[spec["breed"]]
    if spec.get("acc") == "astro":
        _acc_before(g, "astro")
    _ears(g, ears, base, inner)
    if pattern == "calico":
        pass
    _body(g, base, pattern, muzzle, spec["breed"] == "munchkin")
    _head(g, base, pattern)
    _markings(g, spec)
    if spec["face"] == "hiss" and ears == "point":   # ears pinned back a bit
        for x in (5, 18):
            g.put(x, 2, ".")
            g.put(x, 3, ".")
    acc = spec.get("acc")
    if acc and acc != "astro":
        _acc_before(g, acc)
    g.outline("k")
    if acc == "astro":   # see-through helmet glint
        g.ell(12, 13, 11.5, 11, "s", ("k",))
    _eyes(g, spec, blink)
    _mouth(g, spec)
    if acc != "astro":
        _whiskers(g, spec)
    if acc:
        _acc_after(g, acc)
    if spec["face"] in ("happy", "excited", "sleepy") and acc not in ("blush", "mask", "shades"):
        g.put(4, 15, "P")
        g.put(19, 15, "P")
    return g.rows()


def paint_gold(blink=False):
    """LUCKY GOLDIE: the golden JACKPOT kitten."""
    spec = {"breed": "white", "eyes": "o", "face": "excited", "acc": "gold"}
    rows = paint_cat(spec, blink)
    swap = {"w": "y", "c": "o", "g": "o"}
    out = []
    for y, r in enumerate(rows):
        out.append("".join(swap.get(ch, ch) if not (10 <= y <= 13 and 5 <= x <= 18 and ch in "wk") else ch
                           for x, ch in enumerate(r)))
    # sparkles
    out = [list(r) for r in out]
    for x, y in ((1, 2), (22, 20), (2, 21)):
        out[y][x] = "w"
    return ["".join(r) for r in out]


def paint_flea(blink=False):
    """The FLEAS junk card: a hopping bug."""
    g = Grid(24, 24)
    g.ell(12, 13, 6, 5, "n")
    g.ell(8, 10, 3, 3, "n")
    g.outline("k")
    g.put(7, 9, "w" if not blink else "k")
    g.put(7, 10, "k")
    for x0 in (9, 12, 15):
        g.line(x0, 17, x0 - 2, 21, "k")
    g.line(16, 15, 21, 19, "k")
    g.line(21, 19, 21, 22, "k")
    g.rect(11, 11, 4, 1, "h")
    g.rect(10, 14, 6, 1, "h")
    for x, y in ((3, 4), (19, 5), (20, 9)):
        g.put(x, y, "y")
    return g.rows()


# ----------------------------------------------------------------------------- the hero: TOFU
def paint_tofu(pose="idle", frame=0):
    """32x32 side view of TOFU the crew captain (white cat, orange eye patch, blue captain hat, red scarf)."""
    g = Grid(32, 32)
    bob = 1 if (pose == "idle" and frame == 1) else 0
    lean = 3 if pose == "attack" else (-2 if pose == "hurt" else 0)
    jump = -3 if pose == "happy" else 0
    if pose == "ko":
        g.ell(15, 27, 11, 4, "w")
        g.ell(23, 24, 6, 5, "w")
        g.ell(25, 23, 3, 2.5, "o")
        g.poly([(19, 21), (20, 16), (23, 20)], "w")
        g.poly([(5, 26), (1, 22), (3, 27)], "w")
        g.rect(12, 23, 8, 2, "r")
        g.outline("k")
        g.rect(23, 23, 3, 1, "k")
        g.put(28, 25, "p")
        for i, (x, y) in enumerate(((26, 13), (28, 11), (30, 9))):
            g.put(x, y, "s")
        return g.rows()
    by = 22 + bob + jump
    # tail
    tail_up = pose in ("happy", "attack")
    if tail_up:
        g.ell(5, by - 6, 2, 6, "w")
        g.ell(4, by - 12, 2.2, 2.2, "o")
    else:
        g.ell(5, by + 4, 5, 2, "w")
        g.ell(1.5, by + 3, 2, 2, "o")
    # body
    g.ell(14 + lean * 0.5, by + 1, 9, 7, "w")
    g.ell(17 + lean * 0.5, by + 3, 4, 4, "c")
    # legs
    for x in (9, 13):
        g.rect(int(x + lean * 0.3), by + 5, 3, 4 - (1 if jump else 0), "w")
    if pose == "attack":
        g.ell(28, by - 2, 3, 2.5, "w")            # paw strike
        g.rect(23, by - 3, 5, 3, "w")
    else:
        g.rect(19 + lean, by + 5, 3, 4 - (1 if jump else 0), "w")
    if pose == "happy":
        g.rect(20, by - 6, 3, 6, "w")
        g.ell(21.5, by - 7, 2, 2, "w")
    # head
    hx, hy = 19 + lean, by - 9
    g.poly([(hx - 7, hy - 2), (hx - 6, hy - 10), (hx - 1, hy - 6)], "w")     # back ear
    g.poly([(hx + 7, hy - 2), (hx + 5, hy - 10), (hx + 1, hy - 6)], "w")     # front ear
    g.poly([(hx + 6, hy - 3), (hx + 5, hy - 8), (hx + 2, hy - 5)], "p")
    g.ell(hx, hy, 8, 6.6, "w")
    g.ell(hx + 3.5, hy - 1.5, 3.4, 3, "o")                                   # orange eye patch
    g.ell(hx + 4, hy + 2.5, 3, 2, "c")                                       # muzzle
    # captain hat
    g.ell(hx - 1, hy - 7.5, 6.5, 3, "b")
    g.rect(hx - 7, hy - 7, 13, 2, "i")
    g.rect(hx - 2, hy - 6, 10, 1, "k")
    g.put(hx - 1, hy - 9, "y")
    g.put(hx, hy - 9, "y")
    # scarf
    g.rect(hx - 6, hy + 5, 11, 3, "r")
    g.rect(hx - 6, hy + 5, 3, 6, "r")
    g.outline("k")
    # face
    ex = hx + 3
    if pose == "hurt":
        g.line(ex - 1, hy - 2, ex + 1, hy, "k")
        g.line(ex - 1, hy, ex + 1, hy - 2, "k")
    elif pose == "happy":
        g.put(ex - 1, hy - 1, "k")
        g.put(ex, hy - 2, "k")
        g.put(ex + 1, hy - 1, "k")
    elif frame == 2:   # blink
        g.rect(ex - 1, hy - 1, 3, 1, "k")
    else:
        g.rect(ex - 1, hy - 2, 2, 3, "k")
        g.put(ex - 1, hy - 2, "w")
        g.put(ex + 1, hy - 1, "s")
    g.rect(hx + 7, hy + 1, 1, 1, "P")
    g.put(hx + 5, hy + 3, "k")
    g.put(hx + 6, hy + 4, "k")
    if pose in ("happy", "attack"):
        g.rect(hx + 5, hy + 4, 2, 1, "r")
    g.put(hx - 2, hy + 2, "P")
    return g.rows()


# ----------------------------------------------------------------------------- foes (face left)
def _face_left(g, x, y, mood="angry", c="k", eye="w"):
    g.rect(x, y, 2, 2, c)
    g.put(x, y, eye)
    if mood == "angry":
        g.line(x - 1, y - 2, x + 2, y - 1, "k")


def paint_pug(frame=0, mud=False):
    g = Grid(32, 30)
    b = "n" if mud else "e"
    dark = "h"
    yo = frame
    g.ell(20, 20 + yo * 0.5, 9, 6.5, b)                   # body
    for x in (13, 17, 23, 27):
        g.rect(x - 1, 24, 3, 5, b)
    g.ell(29, 15, 2.5, 2.5, b)                           # curly tail
    g.put(29, 15, dark)
    g.ell(11, 12 + yo, 8, 7, b)                          # head
    g.poly([(4, 8 + yo), (6, 2 + yo), (10, 6 + yo)], dark)   # ears
    g.poly([(14, 6 + yo), (17, 2 + yo), (18, 9 + yo)], dark)
    g.ell(8, 15 + yo, 5, 3.6, dark)                      # muzzle mask
    if mud:
        for x, y in ((18, 18), (23, 21), (21, 15), (26, 19)):
            g.ell(x, y, 2, 1.5, "h")
    else:
        g.rect(12, 18 + yo, 8, 2, "r")                   # collar
        g.put(15, 20 + yo, "y")
    g.outline("k")
    _face_left(g, 6, 10 + yo)
    _face_left(g, 11, 10 + yo)
    g.rect(5, 14 + yo, 3, 2, "k")                         # nose
    g.rect(6, 18 + yo, 4, 1, "w")                         # teeth
    g.put(4, 17 + yo, "p")
    return g.rows()


def paint_barker(frame=0):
    """BIG BARKER: chunky gray dog with a spiked collar."""
    g = Grid(36, 32)
    yo = frame
    g.ell(22, 21 + yo * 0.5, 11, 7.5, "g")
    for x in (14, 19, 26, 31):
        g.rect(x - 2, 25, 4, 6, "g")
    g.ell(12, 13 + yo, 9.5, 8, "g")
    g.ell(9, 17 + yo, 6, 4, "w")
    g.poly([(5, 9 + yo), (3, 3 + yo), (9, 6 + yo)], "d")
    g.poly([(17, 7 + yo), (21, 3 + yo), (20, 10 + yo)], "d")
    g.rect(14, 20 + yo, 10, 3, "k")
    for x in range(15, 24, 3):
        g.put(x, 19 + yo, "w")
    g.outline("k")
    _face_left(g, 6, 11 + yo)
    _face_left(g, 12, 11 + yo)
    g.rect(4, 15 + yo, 3, 2, "k")
    g.rect(5, 20 + yo, 6, 1, "k")
    g.put(6, 20 + yo, "w")
    g.put(9, 20 + yo, "w")
    return g.rows()


def paint_hound(frame=0):
    """SNIFF HOUND: long-eared beagle that cheers the pack on."""
    g = Grid(32, 30)
    yo = frame
    g.ell(20, 20 + yo * 0.5, 9, 6, "w")
    g.ell(22, 18, 6, 4, "n", ("w",))
    for x in (13, 17, 23, 27):
        g.rect(x - 1, 24, 3, 5, "w")
    g.line(28, 17, 31, 10 + yo, "w")
    g.ell(11, 12 + yo, 7, 6.5, "n")
    g.ell(8, 16 + yo, 5, 3.4, "w")
    g.ell(15, 15 + yo, 3, 6, "h")                        # floppy ear
    g.outline("k")
    _face_left(g, 7, 10 + yo, "happy")
    _face_left(g, 11, 10 + yo, "happy")
    g.rect(4, 15 + yo, 3, 2, "k")
    g.put(7, 19 + yo, "P")
    return g.rows()


def paint_crow(frame=0, shiny=False, gull=False):
    g = Grid(30, 28)
    body, wing = ("w", "g") if gull else ("i", "d")
    flap = frame
    g.ell(16, 16, 8, 6.5, body)
    g.ell(9, 10, 5.5, 5, body)
    if flap:
        g.poly([(14, 12), (26, 2), (22, 14)], wing)
    else:
        g.poly([(14, 14), (27, 18), (21, 21)], wing)
    g.poly([(23, 15), (29, 13), (29, 19)], wing)           # tail
    g.poly([(4, 9), (-1, 11), (4, 12)], "o" if gull else "y")   # beak
    for x in (14, 18):
        g.line(x, 22, x, 26, "o")
        g.line(x, 26, x - 2, 27, "o")
    g.outline("k")
    _face_left(g, 7, 8, "angry", eye="w" if not gull else "y")
    if shiny:
        g.ell(1.5, 13.5, 2, 2, "y")
        g.put(1, 13, "w")
    return g.rows()


def paint_bot(frame=0, kind="dust"):
    """Robot vacuums: dust = disc bot, mop = spinning mop arms, turbo = jet bot."""
    g = Grid(34, 26)
    shell = {"dust": "g", "mop": "t", "turbo": "r"}[kind]
    g.ell(17, 18, 15, 6, shell)
    g.ell(17, 16, 13, 4.5, "w" if kind != "turbo" else "o")
    g.rect(3, 20, 28, 2, "d")
    if kind == "mop":
        for side in (-1, 1):
            x = 17 + side * 14
            g.line(17 + side * 8, 14, x, 6 + frame * 2, "d")
            g.ell(x, 6 + frame * 2, 3, 2, "c")
    if kind == "turbo":
        g.poly([(30, 14), (34, 12), (34, 20), (30, 18)], "y")
    g.rect(9, 9, 16, 4, "d")
    g.rect(15, 5, 4, 4, "d")
    g.outline("k")
    g.rect(10, 10, 4, 2, "r" if frame == 0 else "P")       # visor eyes
    g.rect(20, 10, 4, 2, "r" if frame == 0 else "P")
    g.put(16 + frame, 6, "l")
    for x in range(5, 30, 4):                              # bristles
        g.put(x + frame, 24, "y")
    return g.rows()


def paint_mouse(frame=0, kind="thief"):
    """Mice: thief (mask + cheese), medic (red cross cap), squad (three little mice)."""
    if kind == "squad":
        g = Grid(34, 26)
        for i, (x, y) in enumerate(((7, 16), (17, 9), (27, 17))):
            yy = y + (frame if i % 2 else -frame)
            g.ell(x + 1, yy + 4, 5, 4, "g")
            g.ell(x, yy, 4, 3.5, "g")
            g.ell(x + 2, yy - 4, 2.2, 2.2, "p")
            g.line(x + 5, yy + 6, x + 8, yy + 3, "p")
        g.outline("k")
        for i, (x, y) in enumerate(((7, 16), (17, 9), (27, 17))):
            yy = y + (frame if i % 2 else -frame)
            g.put(x - 2, yy - 1, "k")
            g.put(x - 4, yy + 1, "P")
        return g.rows()
    g = Grid(30, 28)
    yo = frame
    fur = "w" if kind == "medic" else "g"
    g.ell(18, 19 + yo * 0.5, 8, 6.5, fur)
    g.ell(10, 13 + yo, 6.5, 5.5, fur)
    g.ell(12, 6 + yo, 3.5, 3.5, fur)
    g.ell(12, 6 + yo, 2, 2, "p")
    g.line(25, 21, 29, 15, "p")
    for x in (14, 21):
        g.rect(x, 24, 3, 3, fur)
    if kind == "medic":
        g.rect(7, 5 + yo, 7, 4, "w")
        g.rect(9, 6 + yo, 3, 1, "r")
        g.rect(10, 5 + yo, 1, 3, "r")
        g.rect(15, 14, 7, 6, "w")
        g.rect(17, 15, 3, 4, "r")
        g.rect(16, 16, 5, 2, "r")
    else:
        g.ell(23, 13, 4, 3, "y")                          # cheese sack
        g.rect(4, 11 + yo, 10, 3, "k")                     # bandit mask
    g.outline("k")
    g.put(7, 12 + yo, "w" if kind != "medic" else "k")
    g.put(10, 12 + yo, "w" if kind != "medic" else "k")
    g.rect(3, 15 + yo, 2, 2, "P")
    g.line(4, 17 + yo, 0, 18 + yo, "c")
    return g.rows()


def paint_spray(frame=0):
    g = Grid(24, 32)
    g.rect(6, 12, 13, 18, "t")
    g.rect(7, 13, 11, 6, "s")
    g.rect(8, 7, 9, 5, "w")
    g.rect(2, 7, 7, 3, "w")
    g.rect(14, 9, 3, 6, "w")
    g.outline("k")
    g.rect(9, 21, 2, 2, "k")
    g.rect(14, 21, 2, 2, "k")
    g.line(8, 19, 11, 20, "k")
    g.line(17, 19, 14, 20, "k")
    g.rect(10, 26, 5, 1, "k")
    if frame:
        for x, y in ((0, 6), (1, 11), (0, 3)):
            g.put(x, y, "s")
    return g.rows()


def paint_cuke(frame=0):
    """SPOOKY CUKE: the cucumber every cat fears."""
    g = Grid(20, 34)
    lean = frame
    g.ell(10 + lean * 0.5, 17, 7, 15, "l")
    g.ell(10 + lean * 0.5, 17, 5, 13, "l")
    for x, y in ((6, 8), (13, 12), (7, 20), (12, 26), (9, 4)):
        g.put(x + lean, y, "t")
    g.outline("k")
    for x in (6, 12):
        g.rect(x + lean, 12, 3, 3, "w")
        g.put(x + 1 + lean, 13, "k")
    for x in range(6, 15):
        g.put(x + lean, 19 + (x % 2), "k")
    return g.rows()


# ----------------------------------------------------------------------------- bosses (big, face left)
def paint_baron(frame=0):
    g = Grid(56, 48)
    yo = frame
    g.ell(32, 34 + yo * 0.5, 20, 12, "e")                 # body
    for x in (20, 28, 40, 48):
        g.rect(x - 3, 40, 6, 7, "e")
    g.ell(20, 23 + yo, 16, 13, "e")                       # head
    g.ell(14, 31 + yo, 10, 6, "c")                        # jowls
    g.poly([(7, 14 + yo), (4, 6 + yo), (13, 11 + yo)], "h")
    g.poly([(31, 13 + yo), (36, 7 + yo), (35, 17 + yo)], "h")
    g.rect(10, 0 + yo, 20, 11, "k")                        # top hat
    g.rect(5, 10 + yo, 30, 3, "k")
    g.rect(10, 7 + yo, 20, 2, "u")
    g.rect(22, 34 + yo, 16, 4, "u")                        # sash
    g.outline("k")
    _face_left(g, 10, 20 + yo)
    _face_left(g, 20, 20 + yo)
    for (x, y) in ((19, 18), (23, 18), (24, 19), (24, 22), (23, 23), (19, 23), (18, 22), (18, 19)):
        g.put(x, y + yo, "y")                              # monocle
    g.rect(6, 26 + yo, 5, 3, "k")
    g.rect(8, 33 + yo, 10, 1, "k")
    g.put(9, 32 + yo, "w")
    g.put(16, 32 + yo, "w")
    g.put(28, 36 + yo, "y")
    return g.rows()


def paint_cawline(frame=0):
    g = Grid(56, 48)
    flap = frame
    g.ell(30, 30, 15, 12, "i")
    g.ell(16, 18, 10, 9, "i")
    if flap:
        g.poly([(26, 22), (54, 4), (46, 28)], "d")
    else:
        g.poly([(26, 26), (55, 32), (44, 40)], "d")
    g.poly([(42, 28), (55, 24), (55, 36)], "d")
    g.poly([(7, 16), (-1, 21), (7, 22)], "y")
    g.poly([(10, 10), (10, 2), (14, 6), (17, 0), (20, 6), (24, 2), (24, 10)], "y")
    g.rect(16, 4, 2, 2, "r")
    for x in (26, 34):
        g.line(x, 41, x, 46, "o")
        g.line(x, 46, x - 3, 47, "o")
    g.ell(30, 33, 6, 5, "v", ("i",))
    g.outline("k")
    _face_left(g, 12, 15)
    g.put(4, 30, "y")
    return g.rows()


def paint_megabot(frame=0):
    g = Grid(60, 46)
    g.ell(30, 34, 28, 10, "g")
    g.ell(30, 31, 24, 7, "w")
    g.rect(4, 38, 52, 3, "d")
    g.rect(16, 8, 28, 18, "d")
    g.rect(18, 10, 24, 10, "k")
    for side in (-1, 1):
        x = 30 + side * 22
        g.line(30 + side * 14, 22, x, 12 - frame * 2, "g")
        g.ell(x, 12 - frame * 2, 4, 3, "y")
    g.rect(28, 2, 4, 6, "d")
    g.outline("k")
    g.rect(20, 12, 8, 4, "r" if frame == 0 else "P")
    g.rect(32, 12, 8, 4, "r" if frame == 0 else "P")
    g.rect(24, 17, 12, 1, "l")
    g.put(29, 2, "r")
    g.put(30, 2, "r")
    for x in range(6, 56, 5):
        g.put(x + frame, 44, "y")
    return g.rows()


def paint_bigcheese(frame=0):
    g = Grid(56, 48)
    yo = frame
    g.ell(28, 38, 24, 9, "y")                             # cheese wheel
    g.rect(4, 38, 48, 8, "y")
    for x, y in ((12, 40), (24, 42), (40, 39), (46, 43)):
        g.ell(x, y, 2.5, 2, "o")
    g.ell(30, 22 + yo, 13, 11, "g")                       # fat mouse king
    g.ell(19, 14 + yo, 9, 8, "g")
    g.ell(22, 4 + yo, 5, 5, "g")
    g.ell(22, 4 + yo, 3, 3, "p")
    g.poly([(13, 7 + yo), (13, 1 + yo), (16, 4 + yo), (19, 0 + yo), (22, 4 + yo), (25, 1 + yo), (25, 7 + yo)], "y")
    g.rect(20, 20 + yo, 22, 4, "r")
    g.line(42, 26, 52, 18, "p")
    g.outline("k")
    _face_left(g, 13, 12 + yo)
    _face_left(g, 19, 12 + yo)
    g.rect(10, 16 + yo, 3, 2, "P")
    g.line(11, 19 + yo, 5, 21 + yo, "c")
    return g.rows()


def paint_tub(frame=0):
    g = Grid(58, 48)
    g.rect(6, 22, 46, 18, "w")
    g.ell(29, 22, 23, 4, "w")
    g.ell(29, 22, 20, 2.5, "s")
    for x in (10, 46):
        g.rect(x, 40, 4, 6, "y")
    g.line(48, 22, 50, 6, "g")
    g.line(50, 6, 40, 4, "g")
    g.ell(38, 6, 4, 3, "g")
    for i in range(4):
        g.ell(10 + i * 10, 18 - (i + frame) % 2 * 2, 3, 3, "s")
    g.outline("k")
    _face_left(g, 18, 28)
    _face_left(g, 30, 28)
    g.rect(20, 34, 12, 2, "k")
    if frame:
        for x, y in ((34, 10), (31, 13), (36, 13)):
            g.put(x, y, "s")
    return g.rows()


def paint_cukeking(frame=0):
    g = Grid(40, 52)
    lean = frame
    g.ell(20 + lean, 28, 14, 23, "l")
    for x, y in ((10, 20), (26, 14), (14, 34), (28, 40), (20, 26)):
        g.put(x + lean, y, "t")
        g.put(x + lean + 1, y, "t")
    g.poly([(10 + lean, 8), (10 + lean, 0), (15 + lean, 4), (20 + lean, -1), (25 + lean, 4), (30 + lean, 0), (30 + lean, 8)], "y")
    g.rect(2, 24, 6, 20, "g")                             # shield
    g.outline("k")
    for x in (11, 23):
        g.rect(x + lean, 16, 5, 5, "w")
        g.rect(x + 2 + lean, 18, 2, 2, "k")
    for x in range(11, 29):
        g.put(x + lean, 29 + (x % 2), "k")
    g.rect(4, 30, 2, 8, "y")
    return g.rows()


def paint_mecha(frame=0):
    """MECHA MUTT: the final boss - a giant robot dog."""
    g = Grid(64, 52)
    yo = frame
    g.ell(38, 34 + yo * 0.5, 22, 12, "g")
    for x in (24, 32, 46, 54):
        g.rect(x - 3, 40, 7, 10, "d")
    g.ell(20, 22 + yo, 15, 13, "g")
    g.ell(14, 29 + yo, 9, 6, "d")
    g.poly([(8, 12 + yo), (4, 2 + yo), (14, 9 + yo)], "r")
    g.poly([(28, 10 + yo), (33, 1 + yo), (34, 14 + yo)], "r")
    g.rect(40, 26, 18, 6, "d")
    g.rect(56, 22, 6, 4, "y")
    g.rect(30, 32 + yo, 16, 3, "y")
    g.outline("k")
    g.rect(9, 18 + yo, 6, 3, "r" if frame == 0 else "y")
    g.rect(19, 18 + yo, 6, 3, "r" if frame == 0 else "y")
    g.rect(5, 26 + yo, 4, 3, "k")
    for x in range(8, 20, 2):
        g.put(x, 33 + yo, "w")
    for x in range(42, 58, 4):
        g.put(x, 28, "l")
    return g.rows()


# ----------------------------------------------------------------------------- icons (8x8 / 7x7)
ICONS = {
    "fish": ["........", ".kkkk...", "kyyyyk.k", "kyykyykk", "kyyyyykk", "kyyyyk.k", ".kkkk...", "........"],
    "fishoff": ["........", ".kkkk...", "kddddk.k", "kddkddkk", "kdddddkk", "kddddk.k", ".kkkk...", "........"],
    "claw": ["......ww", ".....wwg", "....wwg.", "y..wwg..", ".ywwg...", "..yy....", ".n.yy...", "n......."],
    "shield": [".kkkkk.", "kssssbk", "ksssbbk", "kssbbbk", ".kssbk.", "..kbk..", "...k...", "......."],
    "heart": [".......", ".PP.PP.", "PPPPPPP", "PPPPPPP", ".PPPPP.", "..PPP..", "...P...", "......."],
    "up": ["...o...", "..ooo..", ".ooooo.", "...o...", "...o...", "...o...", "...o...", "......."],
    "down": ["...u...", "...u...", "...u...", "...u...", ".uuuuu.", "..uuu..", "...u...", "......."],
    "zzz": ["kkkk...", "..k....", ".k.....", "kkkkkk.", "....k..", "...k...", "..kkkk.", "......."],
    "skull": [".wwwww.", "wwwwwww", "wkwwwkw", "wkwwwkw", "wwwkwww", ".wwwww.", ".w.w.w.", "......."],
    "plus": ["...l...", "...l...", "...l...", "lllllll", "...l...", "...l...", "...l...", "......."],
    "drop": ["...s...", "..sss..", "..sss..", ".sssss.", ".sswss.", "..sss..", "...s...", "......."],
    "flea": ["..n.n..", ".nnnnn.", "nnknnnn", "nnnnnnn", ".nnnnn.", "n.n.n.n", "n.n.n.n", "......."],
    "coin": ["..yyy..", ".yoooy.", "yoyyyoy", "yoyyyoy", "yoyyyoy", ".yoooy.", "..yyy..", "......."],
    "treat": [".......", "..ooo..", ".oyyyo.", "oyyhyyo", ".oyyyo.", "..ooo..", ".......", "......."],
    "spiky": ["...g...", "g..g..g", ".g.g.g.", "..ggg..", ".g.g.g.", "g..g..g", "...g...", "......."],
    "quest": [".yyyy..", "y....y.", ".....y.", "...yy..", "...y...", ".......", "...y...", "......."],
    "steal": ["...y...", "..yky..", ".yyyyy.", "..yyy..", "...k...", "..k.k..", ".k...k.", "......."],
    "boom": ["y..o..y", ".yoroy.", "oorrroo", ".yoroy.", "y..o..y", ".......", ".......", "......."],
}


def _icon_rows(rows):
    w = max(len(r) for r in rows)
    return [r.ljust(w, ".") for r in rows]


# ----------------------------------------------------------------------------- charm icons (16x16 painted)
def paint_charm(kind):
    g = Grid(16, 16)
    if kind == "bowl":
        g.ell(8, 10, 7, 4, "s")
        g.rect(1, 6, 15, 4, ".")
        g.ell(8, 8, 6, 1.5, "o")
        g.poly([(6, 7), (10, 3), (11, 7)], "y")
    elif kind == "nap":
        g.ell(8, 11, 7, 4, "v")
        g.ell(5, 9, 3, 3, "w")
        g.put(12, 2, "w")
        g.put(13, 4, "w")
    elif kind == "claws":
        for x in (4, 8, 12):
            g.line(x - 2, 13, x + 1, 2, "w")
    elif kind == "coat":
        g.ell(8, 9, 6, 6, "v")
        for x, y in ((3, 4), (12, 5), (2, 11), (13, 12)):
            g.put(x, y, "w")
    elif kind == "nose":
        g.poly([(4, 6), (12, 6), (8, 11)], "p")
        g.put(6, 7, "w")
    elif kind == "bell":
        g.ell(8, 9, 5, 5, "y")
        g.rect(3, 9, 11, 2, "o")
        g.rect(7, 2, 2, 2, "o")
        g.put(8, 12, "k")
    elif kind == "catnip":
        g.ell(6, 6, 3, 4, "l")
        g.ell(11, 9, 3, 4, "l")
        g.line(8, 15, 8, 6, "t")
    elif kind == "lives":
        g.ell(5.5, 6, 3.5, 3.5, "P")
        g.ell(10.5, 6, 3.5, 3.5, "P")
        g.poly([(2, 7), (14, 7), (8, 14)], "P")
        g.put(5, 5, "w")
    elif kind == "post":
        g.rect(6, 2, 4, 12, "n")
        for y in range(3, 13, 3):
            g.rect(6, y, 4, 1, "c")
        g.rect(2, 13, 12, 2, "h")
    elif kind == "blanket":
        g.rect(2, 4, 12, 9, "s")
        for x in range(2, 14, 4):
            g.rect(x, 4, 2, 9, "w")
    elif kind == "jar":
        g.rect(4, 4, 8, 10, "s")
        g.rect(4, 2, 8, 2, "n")
        g.ell(8, 10, 3, 2.5, "o")
    elif kind == "motor":
        g.ell(8, 8, 6, 6, "P")
        g.ell(8, 8, 3, 3, "w")
        g.put(8, 8, "P")
    g.outline("k")
    return g.rows()


CHARM_ICONS = ["bowl", "nap", "claws", "coat", "nose", "bell", "catnip", "lives", "post", "blanket", "jar", "motor"]


# ----------------------------------------------------------------------------- registration
def build_art(cats):
    """cats: the card table from meow_deck_data. Returns the sprite dict."""
    art = {}
    for c in cats:
        if c["breed"] == "gold":
            art[c["spr"]] = [paint_gold(), paint_gold(True)]
        elif c["breed"] == "bug":
            art[c["spr"]] = [paint_flea(), paint_flea(True)]
        else:
            art[c["spr"]] = [paint_cat(c["look"]), paint_cat(c["look"], True)]
    art["md_tofu"] = [paint_tofu("idle", 0), paint_tofu("idle", 1), paint_tofu("idle", 2)]
    art["md_tofu_act"] = [paint_tofu("attack"), paint_tofu("hurt"), paint_tofu("happy"), paint_tofu("ko")]
    foes = {
        "md_f_pug": [paint_pug(0), paint_pug(1)],
        "md_f_mud": [paint_pug(0, True), paint_pug(1, True)],
        "md_f_barker": [paint_barker(0), paint_barker(1)],
        "md_f_hound": [paint_hound(0), paint_hound(1)],
        "md_f_crow": [paint_crow(0), paint_crow(1)],
        "md_f_shiny": [paint_crow(0, True), paint_crow(1, True)],
        "md_f_gull": [paint_crow(0, gull=True), paint_crow(1, gull=True)],
        "md_f_dust": [paint_bot(0, "dust"), paint_bot(1, "dust")],
        "md_f_mop": [paint_bot(0, "mop"), paint_bot(1, "mop")],
        "md_f_turbo": [paint_bot(0, "turbo"), paint_bot(1, "turbo")],
        "md_f_thief": [paint_mouse(0, "thief"), paint_mouse(1, "thief")],
        "md_f_medic": [paint_mouse(0, "medic"), paint_mouse(1, "medic")],
        "md_f_squad": [paint_mouse(0, "squad"), paint_mouse(1, "squad")],
        "md_f_spray": [paint_spray(0), paint_spray(1)],
        "md_f_cuke": [paint_cuke(0), paint_cuke(1)],
        "md_b_baron": [paint_baron(0), paint_baron(1)],
        "md_b_cawline": [paint_cawline(0), paint_cawline(1)],
        "md_b_megabot": [paint_megabot(0), paint_megabot(1)],
        "md_b_cheese": [paint_bigcheese(0), paint_bigcheese(1)],
        "md_b_tub": [paint_tub(0), paint_tub(1)],
        "md_b_cuke": [paint_cukeking(0), paint_cukeking(1)],
        "md_b_mecha": [paint_mecha(0), paint_mecha(1)],
    }
    art.update(foes)
    for k, rows in ICONS.items():
        art["md_i_" + k] = [_icon_rows(rows)]
    for k in CHARM_ICONS:
        art["md_ch_" + k] = [paint_charm(k)]
    return art
