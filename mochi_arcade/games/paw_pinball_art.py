"""PAW PINBALL art: sprites, songs and the procedural drawing of Kiki, her paws, cat bumpers, fish targets,
the nap bed, the cat tower and the table backgrounds. Ported in PawPinballArt.swift."""
import math

import pygame

from mochi_arcade import cute, music, sprites
from mochi_arcade.arcade import rainbow
from mochi_arcade.games import paw_pinball_tables as T
from mochi_arcade.gfx import H, W, col, draw_text

# ----------------------------------------------------------------------------- sprites
BELL = ["..ooo..", ".oyyyo.", "oywyyyo", "oyyyyyo", "okkkkko", ".oyyyo.", "..ooo.."]
KBALL = [".k...k.", "kgk.kgk", "kgggggk", "kgkgkgk", "kggpggk", ".kgggk.", "..kkk.."]
KITTEN = [
    ".k.....k.",
    "kgk...kgk",
    "kgggggggk",
    "kgkgggkgk",
    "kggggpggk",
    ".kgggggk.",
    "..kgggk..",
    ".kgwgwgk.",
    ".kgwkwgk.",
    "..kk.kk..",
]
KITTEN_BLINK = KITTEN[:3] + ["kgggggggk"] + KITTEN[4:]
FISH = ["..kkkk..kk", ".ksssskksk", "kskssssssk", ".kswwskksk", "..kkkk..kk"]


def _transpose(rows):
    return ["".join(rows[len(rows) - 1 - y][x] for y in range(len(rows))) for x in range(len(rows[0]))]


FISH_V = _transpose(FISH)          # head at the top
for _rows in (BELL, KBALL, KITTEN, KITTEN_BLINK, FISH, FISH_V):
    assert len({len(r) for r in _rows}) == 1, _rows

sprites.ART.update({
    "pp_bell": [BELL],
    "pp_kball": [KBALL],
    "pp_kitten": [KITTEN, KITTEN_BLINK],
    "pp_fish": [FISH],
    "pp_fish_v": [FISH_V],
})
KITTEN_COATS = [{"g": "o"}, {"g": "g"}, {"g": "c"}, {"g": "e"}, {"g": "w"}, {"g": "n"}]

# ----------------------------------------------------------------------------- songs (original)
SWING = "K:8. H:16 S:8. H:16 K:8. H:16 S:8. H:16"
music.SONGS.update({
    # "Cat Cafe Shuffle" - even tiers
    "pp_cafe": {"bpm": 126, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "F5:8. A5:16 C6:8. A5:16 F5:4 E5:8 F5:8  D5:8. F5:16 A5:8. F5:16 D6:4 C6:4 "
            "A#4:8 D5:8 F5:8 A#5:8 A5:8. G5:16 F5:4  G5:8. E5:16 C5:8 E5:8 G5:4 R:4 "
            "C6:8. C6:16 A5:8 F5:8 G5:8. A5:16 C6:4  A#5:8 A5:8 G5:8 F5:8 D5:4 G5:4 "
            "E5:8. F5:16 G5:8 A#5:8 A5:8. G5:16 E5:8 C5:8  F5:4 A5:8 C6:8 F6:4 R:4"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.7, "notes":
            "F2:4 A2:4 C3:4 D3:4  D2:4 F2:4 A2:4 C3:4  A#2:4 A2:4 G2:4 F2:4  C2:4 E2:4 G2:4 A#2:4 "
            "F2:4 A2:4 C3:4 A2:4  G2:4 A#2:4 D3:4 A#2:4  C3:4 A#2:4 A2:4 G2:4  F2:4 C3:4 F2:2"},
        {"wave": "drums", "vol": 1, "notes": " ".join([SWING] * 8)},
    ]},
    # "Moonlit Paws" - odd tiers
    "pp_moon": {"bpm": 118, "channels": [
        {"wave": "square", "duty": 0.125, "vol": 0.24, "notes":
            "A4:8 C5:8 E5:8 A5:8 G5:8. E5:16 C5:4  F4:8 A4:8 C5:8 F5:8 E5:4 C5:4 "
            "D5:8. E5:16 G5:8 B5:8 A5:8 G5:8 E5:4  G#4:8 B4:8 E5:8 G#5:8 B5:2 "
            "C6:8 B5:8 A5:8 E5:8 A5:8. B5:16 C6:4  D6:8 C6:8 A5:8 F5:8 D5:4 F5:4 "
            "E5:8. F5:16 G#5:8 B5:8 D6:8 C6:8 B5:4  A5:4 E5:4 A4:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": music._bass(["A", "F", "G", "E", "A", "D", "E", "A"])},
        {"wave": "drums", "vol": 1, "notes": " ".join(["K:8 H:8 S:8 H:8 K:8 H:8 S:8 H:16 H:16"] * 8)},
    ]},
})


# ----------------------------------------------------------------------------- table background
def make_bg(tb, theme, t=0.0):
    """Pre-rendered table: panels, playfield pattern, walls, slingshots, tower, lanes, aprons."""
    s = pygame.Surface((W, H))
    s.fill(col("black"))
    a, b, pat, wall = theme["a"], theme["b"], theme["pat"], theme["wall"]
    # playfield
    s.fill(col(a), (T.TX0, 0, T.TX1 - T.TX0, H))
    cb = col(b)
    x0, x1 = int(T.LW), int(T.RW)
    if pat == 0:          # checks
        for y in range(0, H, 10):
            for x in range(x0, x1, 10):
                if (x // 10 + y // 10) % 2:
                    s.fill(cb, (x, y, 10, 10))
    elif pat == 1:        # diagonal stripes
        for k in range(-H, W, 14):
            for i in range(4):
                pygame.draw.line(s, cb, (k + i, H), (k + i + H, 0))
    elif pat == 2:        # polka dots
        for y in range(6, H, 12):
            for x in range(x0 + 4 + (6 if (y // 12) % 2 else 0), x1, 12):
                pygame.draw.circle(s, cb, (x, y), 2)
    elif pat == 3:        # waves
        for y in range(4, H, 10):
            for x in range(x0, x1, 2):
                s.fill(cb, (x, y + int(math.sin(x * 0.25) * 2), 2, 1))
    else:                 # little paw prints
        for y in range(8, H, 18):
            for x in range(x0 + 6 + (9 if (y // 18) % 2 else 0), x1, 18):
                pygame.draw.circle(s, cb, (x, y + 2), 2)
                for dx, dy in ((-3, -2), (-1, -4), (1, -4), (3, -2)):
                    s.fill(cb, (x + dx, y + dy, 1, 1))
    deco(s, theme["deco"], theme)
    # outside the arch and the outer walls: frame colour
    fr = col("black")
    for x in range(int(T.LW), int(T.LANE_OUT) + 1):
        s.fill(fr, (x, 0, 1, int(T.arch_y(x))))
    s.fill(fr, (T.TX0, 0, int(T.LW) - T.TX0, H))
    s.fill(fr, (int(T.LANE_OUT) + 1, 0, T.TX1 - int(T.LANE_OUT) - 1, H))
    # aprons below the inlane guides
    for side in (1, -1):
        def X(x):
            return x if side == 1 else T.MIRROR - x
        (gx1, gy1), (gx2, gy2) = T.GUIDE
        pts = [(X(gx1), gy1), (X(gx2), gy2), (X(gx2), H), (X(gx1), H)]
        pygame.draw.polygon(s, col("black"), pts)
        pygame.draw.polygon(s, col("ink"), [(X(gx1 + 3), gy1 + 6), (X(gx2 - 4), gy2 + 4), (X(gx2 - 4), H), (X(gx1 + 3), H)])
        # slingshot bodies
        (ax, ay), (bx, by), (qx, qy) = T.SLING_PTS
        pygame.draw.polygon(s, col(theme["accent"]), [(X(ax), ay), (X(bx), by), (X(qx), qy)])
        pygame.draw.polygon(s, col("white"), [(X(ax + 2), ay + 6), (X(bx + 2), by - 2), (X(qx - 6), qy - 7)])
    # the cat tower (top-left block)
    draw_tower(s, theme)
    # walls on top
    for x1_, y1, x2_, y2, k in tb["walls"]:
        if k == T.GATE:
            continue
        c = {T.METAL: wall, T.RUBBER: "white", T.SLING: "white"}[k]
        pygame.draw.line(s, col(c), (x1_, y1), (x2_, y2), 2)
    # plunger lane
    s.fill(col("black"), (int(T.RW) + 1, int(T.GATE_Y), int(T.LANE_OUT - T.RW) - 1, H - int(T.GATE_Y)))
    for y in range(int(T.GATE_Y) + 4, int(T.PLUNGE_Y) - 4, 8):
        s.fill(col("darkgray"), (int(T.LANE_X), y, 1, 3))
    for x, y, r in tb["posts"]:
        pygame.draw.circle(s, col("black"), (int(x), int(y)), int(r) + 1)
        pygame.draw.circle(s, col("white"), (int(x), int(y)), int(r))
    # lane letters sit under the lanes (drawn live); little lane guides
    # side panels' bevels
    s.fill(col("ink"), (0, 0, T.TX0 - 2, H))
    s.fill(col("ink"), (T.TX1 + 2, 0, W - T.TX1 - 2, H))
    s.fill(col(wall), (T.TX0 - 2, 0, 1, H))
    s.fill(col(wall), (T.TX1 + 1, 0, 1, H))
    return s


def draw_tower(s, theme):
    """Kiki's cat tower: a sisal scratching post with cushioned platforms in the top-left corner."""
    (b0x, b0y), (b1x, b1y), (b2x, b2y), (b3x, b3y), (b4x, b4y) = T.TOWER
    poly = [(T.LW, 30), (T.LW, b0y), (b1x, b1y), (b2x, b2y), (b3x, b3y), (b4x, b4y), (T.LW, b4y)]
    pygame.draw.polygon(s, col("choco"), poly)
    for y in range(22, int(b0y), 3):           # sisal rope wrap
        xr = 97 if y < 92 else (96 - (y - 92) * 0.75 if y < 100 else 90 - (y - 100) * 3)
        pygame.draw.line(s, col("peach" if y % 2 else "brown"), (int(T.LW) + 2, y), (int(xr) - 2, y + 1))
    for py in (34, 56):                        # platforms
        pygame.draw.rect(s, col(theme["accent"]), (int(T.LW) + 1, py, 24, 5), border_radius=2)
        s.fill(col("white"), (int(T.LW) + 3, py + 1, 18, 1))


def deco(s, kind, theme):
    """A faint motif per theme, under everything."""
    c = col(theme["b"])
    if kind == 1:        # big yarn ball
        pygame.draw.circle(s, c, (196, 140), 18, 2)
        for i in range(-12, 13, 6):
            pygame.draw.line(s, c, (196 + i, 124), (196 - i, 156))
    elif kind == 2:      # sun / window
        pygame.draw.rect(s, c, (128, 112, 54, 40), 2)
        s.fill(c, (154, 112, 2, 40))
        s.fill(c, (128, 131, 54, 2))
    elif kind == 3:      # fish bones
        for x0 in (120, 176):
            s.fill(c, (x0, 140, 20, 2))
            for i in range(4):
                pygame.draw.line(s, c, (x0 + 3 + i * 4, 136), (x0 + 3 + i * 4, 146))
            pygame.draw.polygon(s, c, [(x0 + 20, 141), (x0 + 26, 136), (x0 + 26, 146)])
    elif kind == 4:      # boxes
        pygame.draw.rect(s, c, (130, 124, 22, 18), 2)
        pygame.draw.rect(s, c, (160, 116, 26, 26), 2)
    elif kind == 5:      # moon and stars
        pygame.draw.circle(s, c, (200, 132), 12)
        pygame.draw.circle(s, col(theme["a"]), (205, 128), 10)
        for x, y in ((120, 120), (140, 150), (180, 158), (112, 100)):
            s.fill(c, (x, y - 1, 1, 3))
            s.fill(c, (x - 1, y, 3, 1))
    else:                # a big paw print
        pygame.draw.circle(s, c, (155, 140), 9)
        for dx, dy in ((-11, -9), (-4, -15), (4, -15), (11, -9)):
            pygame.draw.circle(s, c, (155 + dx, 140 + dy), 3)


# ----------------------------------------------------------------------------- live pieces
def draw_bumper(s, x, y, color, flash, t, i=0):
    """Cat-face pop bumper (radius 9)."""
    x, y = int(x), int(y)
    lit = flash > 0
    body = col("white" if lit else color)
    pygame.draw.circle(s, col("black"), (x, y + 1), 10)
    for side in (-1, 1):            # ears
        pygame.draw.polygon(s, col("black"), [(x + side * 9, y - 2), (x + side * 8, y - 13), (x + side * 1, y - 7)])
        pygame.draw.polygon(s, body, [(x + side * 7, y - 3), (x + side * 7, y - 10), (x + side * 2, y - 7)])
        pygame.draw.polygon(s, col("pink"), [(x + side * 6, y - 5), (x + side * 6, y - 8), (x + side * 4, y - 7)])
    pygame.draw.circle(s, body, (x, y), 9)
    pygame.draw.circle(s, col("cream" if not lit else "yellow"), (x, y + 3), 5)
    k = col("black")
    if lit:                         # squeezed eyes > <
        for side in (-1, 1):
            ex = x + side * 4
            s.fill(k, (ex + side, y - 3, 1, 1))
            s.fill(k, (ex, y - 2, 1, 1))
            s.fill(k, (ex + side, y - 1, 1, 1))
    else:
        blink = int(t * 1.3 + i * 1.7) % 6 == 0
        for side in (-1, 1):
            ex = x + side * 4
            if blink:
                s.fill(k, (ex - 1, y - 2, 3, 1))
            else:
                s.fill(k, (ex - 1, y - 3, 2, 3))
                s.fill(col("white"), (ex - 1, y - 3, 1, 1))
    s.fill(col("hotpink"), (x - 1, y + 1, 3, 1))
    s.fill(k, (x - 1, y + 3, 1, 1))
    s.fill(k, (x + 1, y + 3, 1, 1))
    s.fill(k, (x, y + 2, 1, 1))
    for side in (-1, 1):            # whiskers
        s.fill(k, (x + side * 6 - (2 if side < 0 else 0), y + 2, 3, 1))


def draw_fish(s, f, t, golden=False):
    """Drop target f = [x1, y1, x2, y2, face, bank, down]."""
    x1, y1, x2, y2, face, _, down = f
    remap = {"s": "y"} if golden else None
    if down > 0:                    # dropped: a slot
        if x1 == x2:
            s.fill(col("black"), (int(x1) - 1, int(y1), 3, int(y2 - y1) + 1))
        else:
            s.fill(col("black"), (int(x1), int(y1) - 1, int(x2 - x1) + 1, 3))
        return
    if x1 == x2:
        sp = sprites_get("pp_fish_v", remap)
        s.blit(sp, (int(x1) - 2, int((y1 + y2) / 2) - 5))
    else:
        sp = sprites_get("pp_fish", remap)
        s.blit(sp, (int((x1 + x2) / 2) - 5, int(y1) - 2))


def sprites_get(name, remap=None, frame=0):
    from mochi_arcade.gfx import sprite
    return sprite(name, frame, remap=remap)


def draw_saucer(s, x, y, t, busy=False, lit=False):
    """Kiki's nap bed: a round cushion."""
    x, y = int(x), int(y)
    pygame.draw.ellipse(s, col("black"), (x - 9, y - 5, 18, 11))
    pygame.draw.ellipse(s, col("hotpink" if lit and int(t * 6) % 2 else "lavender"), (x - 8, y - 4, 16, 9))
    pygame.draw.ellipse(s, col("purple"), (x - 5, y - 2, 10, 5))
    s.fill(col("white"), (x - 6, y - 3, 3, 1))
    if busy:
        for i in range(2):
            zz = (t * 0.8 + i * 0.5) % 1.0
            draw_text(s, "Z", x + 4 + int(zz * 6), y - 8 - int(zz * 10), "white" if i else "sky", shadow=None)


def draw_spinner(s, sp, angle, t):
    """Yarn spool across a lane: the wool rolls round while it spins."""
    x1, y, x2, _ = sp
    x1, x2, y = int(x1), int(x2), int(y)
    w = x2 - x1 + 1
    s.fill(col("black"), (x1 - 3, y - 5, w + 6, 11))
    for j in range(7):
        c = ("hotpink", "pink", "white")[(j + int(angle * 6)) % 3]
        s.fill(col(c), (x1, y - 3 + j, w, 1))
    for fx in (x1 - 2, x2 + 1):              # wooden flanges
        s.fill(col("brown"), (fx, y - 4, 2, 9))
        s.fill(col("peach"), (fx, y - 4, 1, 9))


def draw_lane_letter(s, i, x, lit, t, skill=False):
    ch = "MEOW"[i]
    c = "yellow" if lit else ("orange" if skill and int(t * 8) % 2 else "darkgray")
    if lit and int(t * 3 + i) % 4 == 0:
        c = "white"
    draw_text(s, ch, int(x) - 2, 29, c, shadow="black")


def draw_ball(s, b, t, fever=False):
    x, y = int(round(b.x)), int(round(b.y))
    if fever:
        for i, (tx, ty) in enumerate(b.trail[-4:]):
            pygame.draw.circle(s, col(rainbow(i, t)), (int(tx), int(ty)), 2)
    elif len(b.trail) > 2 and abs(b.vx) + abs(b.vy) > 330:
        for tx, ty in b.trail[-3:-1]:
            s.fill(col("gray"), (int(tx), int(ty), 1, 1))
    if b.kind == "kitten":
        sp = sprites_get("pp_kball", KITTEN_COATS[b.coat % len(KITTEN_COATS)])
    else:
        sp = sprites_get("pp_bell")
    s.blit(sp, (x - 3, y - 3))


def draw_ramp(s, r, lens, t, color="sky", lit=False):
    """Elevated ramp: two rails with ties along the path, a glowing mouth."""
    path = r["path"]
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L * 4, dx / L * 4
        for sgn in (-1, 1):
            pygame.draw.line(s, col("black"), (x1 + nx * sgn, y1 + ny * sgn + 1), (x2 + nx * sgn, y2 + ny * sgn + 1))
            pygame.draw.line(s, col(color), (x1 + nx * sgn, y1 + ny * sgn), (x2 + nx * sgn, y2 + ny * sgn))
    d = 0.0
    total = lens[-1]
    while d < total:                 # ties
        i = 0
        while i < len(lens) - 2 and lens[i + 1] < d:
            i += 1
        (x1, y1), (x2, y2) = path[i], path[i + 1]
        L = max(0.001, lens[i + 1] - lens[i])
        u = (d - lens[i]) / L
        x, y = x1 + (x2 - x1) * u, y1 + (y2 - y1) * u
        nx, ny = -(y2 - y1) / L * 3, (x2 - x1) / L * 3
        pygame.draw.line(s, col("white"), (x - nx, y - ny), (x + nx, y + ny))
        d += 7
    gx1, gy1, gx2, gy2 = r["gate"]
    c = "yellow" if lit and int(t * 6) % 2 else color
    pygame.draw.line(s, col(c), (gx1, gy1), (gx2, gy2), 2)
    if lit:                          # arrow pointing into the mouth
        mx, my = (gx1 + gx2) / 2, (gy1 + gy2) / 2
        dx, dy = r["dir"]
        k = 6 + int(abs(math.sin(t * 6)) * 3)
        tipx, tipy = mx - dx * k, my - dy * k
        pygame.draw.polygon(s, col("yellow"), [(tipx, tipy), (tipx - dx * 5 - dy * 3, tipy - dy * 5 + dx * 3),
                                               (tipx - dx * 5 + dy * 3, tipy - dy * 5 - dx * 3)])


def draw_flipper(s, f, t, fever=False):
    """Kiki's paw: a black furry arm with a white sock and pink toe beans at the tip."""
    tx, ty = f.tip()
    px, py = f.px, f.py
    stun = f.stun > 0
    arm = col("darkgray" if stun else "black")
    sock = col("gray" if stun else "white")
    # tapered body
    for i in range(7):
        u = i / 6
        x = px + (tx - px) * u
        y = py + (ty - py) * u
        r = 3.6 + (2.2 - 3.6) * u
        pygame.draw.circle(s, col("black"), (int(round(x)), int(round(y))), int(round(r)) + 1)
    for i in range(7):
        u = i / 6
        x = px + (tx - px) * u
        y = py + (ty - py) * u
        r = 3.6 + (2.2 - 3.6) * u
        c = arm if u < 0.45 else sock
        if fever and u >= 0.45:
            c = col(rainbow(i, t))
        pygame.draw.circle(s, c, (int(round(x)), int(round(y))), max(1, int(round(r))))
    # toe beans on the underside near the tip
    dx, dy = (tx - px) / f.len, (ty - py) / f.len
    nx, ny = -dy * f.side, dx * f.side          # points "down" from the paw
    for k in (0.72, 0.86):
        bx, by = px + (tx - px) * k + nx * 1.5, py + (ty - py) * k + ny * 1.5
        s.fill(col("pink"), (int(round(bx)), int(round(by)), 1, 1))
    s.fill(col("hotpink"), (int(round(tx - dx + nx)), int(round(ty - dy + ny)), 1, 1))
    pygame.draw.circle(s, col("darkgray"), (int(px), int(py)), 1)
    if stun:
        for i in range(3):
            a = t * 8 + i * 2.1
            s.fill(col("yellow"), (int((px + tx) / 2 + math.cos(a) * 6), int((py + ty) / 2 - 5 + math.sin(a) * 2), 1, 1))


def draw_kitten(s, x, y, coat, t, golden=False):
    """A lost kitten waiting to be rescued (centre x, y)."""
    remap = {"g": "y", "k": "o"} if golden else KITTEN_COATS[coat % len(KITTEN_COATS)]
    fr = 1 if int(t * 1.5 + coat) % 7 == 0 else 0
    bob = int(abs(math.sin(t * 3 + coat)) * 1.5)
    s.blit(sprites_get("pp_kitten", remap, fr), (int(x) - 4, int(y) - 5 - bob))
    if golden and int(t * 8) % 2:
        s.fill(col("white"), (int(x) + 4, int(y) - 6, 1, 1))


def draw_coin_fish(s, x, y, t, rainbow_fish=False):
    w = max(1, int(abs(math.cos(t * 4 + x * 0.1)) * 5))
    if rainbow_fish:
        pygame.draw.ellipse(s, col(rainbow(0, t)), (int(x) - w, int(y) - 3, w * 2 + 1, 7))
        pygame.draw.ellipse(s, col(rainbow(3, t)), (int(x) - max(1, w - 1), int(y) - 2, max(1, w * 2 - 1), 5))
        return
    pygame.draw.ellipse(s, col("orange"), (int(x) - w, int(y) - 3, w * 2 + 1, 7))
    pygame.draw.ellipse(s, col("yellow"), (int(x) - w + 1, int(y) - 2, max(1, w * 2 - 1), 5))
    if w > 2:
        s.fill(col("black"), (int(x) - w + 2, int(y) - 1, 1, 1))


# ----------------------------------------------------------------------------- Kiki
def draw_kiki(s, cx, cy, mood, t, lx=0.0, ly=0.0, blink=False):
    """Kiki the tuxedo cat, head and bib. mood: idle happy wow worried sad sleepy angry hurt.
    lx, ly in -1..1: where she looks."""
    k, w = col("black"), col("white")
    ear_drop = 3 if mood in ("sad", "hurt") else 0
    twitch = 1 if mood == "idle" and int(t * 2) % 9 == 0 else 0
    # bib + shoulders
    pygame.draw.ellipse(s, k, (cx - 17, cy + 8, 34, 18))
    pygame.draw.ellipse(s, w, (cx - 9, cy + 9, 18, 16))
    # ears
    for side in (-1, 1):
        tip = (cx + side * 13, cy - 19 + ear_drop + (twitch if side > 0 else 0))
        pygame.draw.polygon(s, col("darkgray"), [(cx + side * 16, cy - 4), tip, (cx + side * 4, cy - 13)])
        pygame.draw.polygon(s, k, [(cx + side * 15, cy - 5), (tip[0], tip[1] + 1), (cx + side * 5, cy - 12)])
        pygame.draw.polygon(s, col("pink"), [(cx + side * 13, cy - 8), (tip[0], tip[1] + 5), (cx + side * 7, cy - 11)])
    # head
    pygame.draw.ellipse(s, col("darkgray"), (cx - 17, cy - 15, 34, 28))
    pygame.draw.ellipse(s, k, (cx - 16, cy - 14, 32, 26))
    # tuxedo blaze + muzzle
    pygame.draw.polygon(s, w, [(cx - 1, cy - 12), (cx + 1, cy - 12), (cx + 4, cy), (cx - 4, cy)])
    pygame.draw.ellipse(s, w, (cx - 9, cy - 1, 18, 12))
    # eyes
    for side in (-1, 1):
        ex, ey = cx + side * 7, cy - 4
        if mood == "happy":
            for i in range(5):
                s.fill(w, (ex - 2 + i, ey - (1 if i in (1, 2, 3) else 0) + (1 if i == 2 else 0) - 1, 1, 1))
            continue
        if mood == "sleepy" or blink:
            s.fill(col("lime"), (ex - 3, ey, 7, 1))
            continue
        if mood == "hurt":
            for i in range(5):
                s.fill(w, (ex - 2 + i, ey - 2 + i, 1, 1))
                s.fill(w, (ex + 2 - i, ey - 2 + i, 1, 1))
            continue
        pygame.draw.ellipse(s, col("lime"), (ex - 3, ey - 3, 7, 7))
        pygame.draw.ellipse(s, col("yellow"), (ex - 2, ey - 1, 5, 4))
        px = ex + int(round(lx * 1.5))
        py = ey + int(round(ly * 1.5))
        if mood in ("wow", "worried"):
            pygame.draw.circle(s, k, (px, py), 2)
        else:
            s.fill(k, (px, py - 2, 1, 5))
            s.fill(k, (px - 1, py - 1, 3, 3))
        s.fill(w, (px + 1, py - 2, 1, 1))
        if mood == "sad":
            s.fill(k, (ex - 3, ey - 3, 7, 3))     # heavy lids
            s.fill(col("sky"), (ex + side, ey + 4 + int(t * 6) % 3, 1, 2))
        if mood == "angry":                   # determined brows: lids slant down to the middle
            inner = ex - side * 4
            outer = ex + side * 4
            pygame.draw.polygon(s, k, [(outer, ey - 4), (inner, ey - 4), (inner, ey - 1)])
            pygame.draw.line(s, w, (outer, ey - 4), (inner, ey - 1))
    # nose + mouth
    pygame.draw.polygon(s, col("hotpink"), [(cx - 2, cy + 2), (cx + 2, cy + 2), (cx, cy + 4)])
    if mood in ("happy", "wow"):
        pygame.draw.ellipse(s, col("hotpink"), (cx - 2, cy + 5, 5, 4))
        s.fill(k, (cx - 1, cy + 5, 3, 1))
    elif mood in ("worried", "hurt"):
        pygame.draw.circle(s, k, (cx, cy + 7), 1)
    else:
        s.fill(k, (cx - 3, cy + 6, 2, 1))
        s.fill(k, (cx, cy + 5, 1, 1))
        s.fill(k, (cx + 2, cy + 6, 2, 1))
    # whiskers
    for side in (-1, 1):
        for dy, dy2 in ((3, 1), (5, 6)):
            pygame.draw.line(s, col("white"), (cx + side * 9, cy + dy), (cx + side * 19, cy + dy2))
    if mood in ("happy", "wow"):
        cute.blush(s, cx, cy + 2, 8)
    if mood == "worried":
        s.fill(col("sky"), (cx + 15, cy - 9, 2, 3))
        s.fill(col("sky"), (cx + 16, cy - 10, 1, 1))
    if mood == "sleepy":
        for i in range(2):
            zz = (t * 0.7 + i * 0.5) % 1.0
            draw_text(s, "Z", cx + 12 + int(zz * 6), cy - 14 - int(zz * 10), "white", shadow=None)
