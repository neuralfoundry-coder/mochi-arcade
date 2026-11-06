"""WINDOW WATCH art: sprites (exported to iOS through sprites.ART) and the procedural drawings of Maru,
the treasures on the windowsill, the sky backgrounds and every falling/flying thing.
Mirrored in ios/MochiArcade/Games/WindowWatchArt.swift.
Characters: k=black i=ink w=white c=cream p=pink P=hotpink e=peach o=orange y=yellow l=lime m=mint t=teal
s=sky b=blue v=lavender u=purple n=brown h=choco g=gray d=darkgray r=red .=clear
"""
import math

import pygame

from mochi_arcade import cute, sprites
from mochi_arcade.gfx import H, W, bubble, col, draw_text, lerp_col, sprite

SILL = 172

ART = {
    "ww_drop": [[
        "...k...",
        "..kwk..",
        "..ksk..",
        ".kssbk.",
        "kswsbbk",
        "kbkbkbk",
        "kbbbbbk",
        ".kbbbk.",
        "..kkk..",
    ]],
    "ww_leaf": [[
        "......kkk",
        "....kkoyk",
        "...kooyok",
        "..kooyook",
        ".koyookk.",
        ".kyokk...",
        "k.kk.....",
    ], [
        "......kkk",
        "....kkeyk",
        "...keeyek",
        "..keeyeek",
        ".keyeekk.",
        ".kyekk...",
        "k.kk.....",
    ]],
    "ww_bug": [[
        "ss.....ss",
        "sws...sws",
        ".sskkkss.",
        ".klwklwk.",
        "kllkllllk",
        ".kllllk..",
        "..kkkk...",
    ], [
        ".........",
        ".........",
        "..kkkkk..",
        "sklwklwks",
        "swlkllllw",
        "skllllk.s",
        "..kkkk...",
    ]],
    "ww_dart": [[
        "yy.......kk.",
        ".yykkkkkkrrk",
        ".ywwwwwwwrrk",
        ".yykkkkkkrrk",
        "yy.......kk.",
    ]],
    "ww_crow": [[
        "...kk...........",
        "..kddk..........",
        "..kdddk....kkk..",
        "...kdddk..kddwk.",
        "....kdddkkddkwk.",
        "..kkkddddddddkoo",
        ".kddddddddddkoo.",
        "kddgggddddddk...",
        ".kkdddddddkk....",
        "...kkkkkkk......",
        "....k..k........",
    ], [
        "................",
        "................",
        "...........kkk..",
        "..........kddwk.",
        "....kkkkkkddkwk.",
        "..kkddddddddkkoo",
        ".kddddddddddkoo.",
        "kddgggdddddk....",
        ".kkdddddddk.....",
        "..kdddkkkk......",
        "..kddk..k.......",
    ]],
    "ww_dive": [[
        "....kkk.....",
        "..kkdddkk...",
        ".kdddddddk..",
        "kddkwddkwdk.",
        "kddkkddkkdk.",
        ".kdddddddk..",
        "..kkdoodkk..",
        "....kook....",
        ".....kk.....",
    ]],
    "ww_hail": [[
        "..kkk..",
        ".kwwsk.",
        "kwwssvk",
        "kwsssvk",
        "ksssvvk",
        ".kvvvk.",
        "..kkk..",
    ]],
    "ww_acorn": [[
        "...k...",
        ".kkhkk.",
        "khhhhhk",
        "kkkkkkk",
        "knnnenk",
        ".knnnk.",
        "..knk..",
        "...k...",
    ]],
    "ww_moth": [[
        "kk.......kk",
        "kvk.k.k.kvk",
        "kvvkkckkvvk",
        "kvwvkcckvwv",
        ".kvvkcckvvk",
        "..kkkcck.k.",
        "....kkk....",
    ], [
        "...........",
        "....k.k....",
        "kkkkkckkkkk",
        "kvvvkcckvvk",
        "kvwvkcckwvk",
        ".kkkkcckkk.",
        "....kkk....",
    ]],
    "ww_rocket": [[
        "..k..",
        ".kyk.",
        ".kyk.",
        "krrrk",
        "kwwwk",
        "krrrk",
        "krrrk",
        "kwwwk",
        ".kyk.",
        "..y..",
    ]],
    "ww_snow": [[
        "..kkkkk..",
        ".kwwwwwk.",
        "kwwwwwwsk",
        "kwkwwkwsk",
        "kwwwwwwsk",
        "kwwkkwssk",
        "kswwwssbk",
        ".ksssssk.",
        "..kkkkk..",
    ]],
    "ww_feather": [[
        ".....dk",
        "...ddgk",
        ".ddggk.",
        "kddkk..",
        "kk.....",
    ]],
    "ww_treat": [[
        "..kkkk..k.",
        ".koooyk.kk",
        "kooookkkok",
        "kokooooook",
        "kooookkkok",
        ".koooyk.kk",
        "..kkkk..k.",
    ]],
    "ww_gold": [[
        "...kkkkk...k.",
        "..kyyyywk.kk.",
        ".kyyyyyyykyk.",
        "kykyyyyyyyyyk",
        "kyyyyoyyykyk.",
        ".kyyyyyyk.kk.",
        "..kkkkkk...k.",
    ]],
    "ww_fish": [[
        ".oo.o",
        "ooooo",
        "kooo.",
        ".oo.o",
    ]],
    "ww_chick": [[
        ".kkk.",
        "kyyyk",
        "kykyo",
        "kyyyk",
        ".kkk.",
    ]],
    "ww_paw": [[
        "..kk.kk..",
        ".kwwkwwk.",
        ".kwwkwwk.",
        "kkkk.kkkk",
        "kwwkkkwwk",
        "kwkwwwkwk",
        ".kwwwwwk.",
        ".kwwwwwk.",
        "..kkkkk..",
    ]],
    "ww_pawicon": [[
        ".k.k.k.",
        "kwkwkwk",
        ".kkkkk.",
        "kwwwwwk",
        "kwwwwwk",
        ".kkkkk.",
    ]],
    "ww_heart": [[
        "pp.pp",
        "ppppp",
        ".ppp.",
        "..p..",
    ]],
}
sprites.ART.update(ART)

CAP_COLORS = {"N": "lime", "T": "orange", "S": "sky", "H": "pink", "$": "yellow"}
KIND_COLORS = {"drop": ("sky", "blue", "white"), "leaf": ("orange", "yellow", "peach"), "bug": ("lime", "mint", "sky"),
               "dart": ("yellow", "red", "white"), "bubble": ("sky", "white", "lavender"),
               "mini": ("sky", "white", "lavender"), "crow": ("darkgray", "gray", "black"),
               "hail": ("white", "sky", "lavender"), "moth": ("lavender", "cream", "white"),
               "rocket": ("red", "yellow", "white"), "spark": ("yellow", "orange", "white"),
               "snow": ("white", "sky", "white"), "plane": ("white", "sky", "cream"),
               "puff": ("white", "cream", "lime"), "seed": ("white", "cream"), "star": ("yellow", "white", "orange"),
               "food": ("orange", "yellow"), "cap": ("white", "pink", "yellow"), "orb": ("yellow", "white", "orange"),
               "feather": ("darkgray", "gray"), "treat": ("orange", "yellow", "peach"),
               "gold": ("yellow", "white", "orange"), "fly": ("yellow", "lime", "white"),
               "rise": ("sky", "white", "pink")}


# ----------------------------------------------------------------------------- small helpers
def disc_below(s, cx, cy, r, ytop, color):
    """Filled circle, only the rows at or below ytop (water in a bowl)."""
    c = col(color)
    for dy in range(-r, r + 1):
        y = cy + dy
        if y < ytop:
            continue
        dx = int(math.sqrt(r * r - dy * dy))
        s.fill(c, (cx - dx, y, dx * 2 + 1, 1))


def dither_band(s, y0, h, a, b):
    """Vertical gradient a -> b over h rows (7 steps, 2-pixel checker between steps)."""
    for i in range(h):
        f = i / max(1, h - 1)
        s.fill(lerp_col(a, b, f), (0, y0 + i, W, 1))


# ----------------------------------------------------------------------------- the sky
def make_sky(theme, seed):
    """Static part of a theme's background (gradient, sun/moon, rooftops)."""
    name, top, bottom, curtain, deco = theme[0], theme[1], theme[2], theme[3], theme[4]
    s = pygame.Surface((W, H))
    dither_band(s, 0, SILL, top, bottom)
    night = top in ("black", "night", "darkgray", "purple")
    if "rainbow" in deco:
        for i, c in enumerate(("red", "orange", "yellow", "lime", "sky", "lavender")):
            pygame.draw.circle(s, col(c), (160, 190), 120 - i * 4, 4)
        dither_band(s, 160, SILL - 160, bottom, bottom)
    if "sun" in deco:
        pygame.draw.circle(s, col("yellow"), (272, 52), 14)
        pygame.draw.circle(s, col("white"), (268, 48), 5)
        for a in range(0, 360, 30):
            r = math.radians(a)
            x0, y0 = 272 + math.cos(r) * 18, 52 + math.sin(r) * 18
            s.fill(col("yellow"), (int(x0), int(y0), 2, 2))
    if "sunset" in deco:
        pygame.draw.circle(s, col("orange"), (200, 160), 30)
        pygame.draw.circle(s, col("yellow"), (200, 160), 24)
        for i in range(4):
            s.fill(col("peach"), (150, 132 + i * 8, 100, 1))
    if "moon" in deco:
        pygame.draw.circle(s, col("cream"), (58, 50), 11)
        pygame.draw.circle(s, col(top), (64, 46), 10)
    if "bigmoon" in deco:
        pygame.draw.circle(s, col("orange"), (240, 70), 22)
        pygame.draw.circle(s, col("peach"), (234, 64), 6)
        pygame.draw.circle(s, col("peach"), (250, 80), 3)
    if "aurora" in deco:
        for band, c in ((40, "mint"), (52, "teal"), (64, "lavender")):
            for x in range(0, W, 2):
                y = band + int(math.sin(x * 0.03 + band) * 8)
                s.fill(col(c), (x, y, 2, 2 + (x // 2) % 3))
    if "stars" in deco:
        rnd = seed * 7 + 3
        for i in range(46):
            rnd = (rnd * 1103515245 + 12345) & 0x7FFFFFFF
            x = rnd % W
            rnd = (rnd * 1103515245 + 12345) & 0x7FFFFFFF
            y = 20 + rnd % 120
            s.fill(col("white" if i % 5 == 0 else "lavender"), (x, y, 1, 1))
    # distant rooftops
    roof = lerp_col(bottom, "black" if not night else "night", 0.45 if not night else 0.6)
    x = 0
    i = 0
    while x < W:
        w = 26 + (i * 37 % 23)
        h = 10 + (i * 53 % 17)
        s.fill(roof, (x, SILL - h, w - 2, h))
        if i % 3 == 0:
            pygame.draw.polygon(s, roof, [(x - 2, SILL - h), (x + w // 2 - 1, SILL - h - 8), (x + w, SILL - h)])
        if night:
            for wy in range(SILL - h + 3, SILL - 3, 5):
                for wx in range(x + 3, x + w - 5, 6):
                    if (wx * 7 + wy * 3 + i) % 5 == 0:
                        s.fill(col("yellow"), (wx, wy, 2, 2))
        x += w
        i += 1
    return s


def draw_sky_fx(s, theme, t, flash=0.0):
    """Animated background layers (clouds, rain, snow, petals, fireworks ...)."""
    deco = theme[4]
    if "clouds" in deco:
        for i in range(4):
            x = (i * 97 + t * (5 + i * 2)) % (W + 80) - 40
            y = 34 + (i * 29) % 70
            c = col("white")
            pygame.draw.ellipse(s, c, (int(x) - 16, y - 4, 32, 9))
            pygame.draw.ellipse(s, c, (int(x) - 8, y - 9, 18, 11))
    if "bubbles" in deco:
        for i in range(6):
            y = SILL - ((t * 10 + i * 31) % 150)
            x = 20 + (i * 53) % 280 + math.sin(t + i) * 6
            pygame.draw.circle(s, col("white"), (int(x), int(y)), 3 + i % 3, 1)
    if "storm" in deco:
        for i in range(5):
            x = (i * 71 + t * 6) % (W + 60) - 30
            pygame.draw.ellipse(s, col("darkgray"), (int(x) - 30, 14, 60, 18))
            pygame.draw.ellipse(s, col("ink"), (int(x) - 20, 22, 44, 12))
    if "rain" in deco:
        c = col("lavender")
        for i in range(40):
            x = (i * 41 + int(t * 40)) % W
            y = (i * 67 + int(t * 220)) % (SILL - 20) + 20
            s.fill(c, (x, y, 1, 4))
    if "leaves" in deco:
        for i in range(10):
            y = (i * 37 + t * 18) % (SILL - 20) + 20
            x = (i * 61 + t * 30 + math.sin(t * 2 + i) * 10) % W
            s.fill(col("orange" if i % 2 else "brown"), (int(x), int(y), 2, 1))
    if "petals" in deco:
        for i in range(14):
            y = (i * 29 + t * 16) % (SILL - 20) + 20
            x = (i * 47 + t * 12 + math.sin(t * 2 + i) * 8) % W
            s.fill(col("pink" if i % 3 else "white"), (int(x), int(y), 2, 1))
    if "snow" in deco:
        for i in range(36):
            y = (i * 23 + t * (14 + i % 4 * 4)) % (SILL - 20) + 20
            x = (i * 53 + math.sin(t + i) * 6) % W
            s.fill(col("white"), (int(x), int(y), 1 + i % 2, 1 + i % 2))
    if "stars" in deco:
        for i in range(6):
            if int(t * 3 + i * 1.7) % 4 == 0:
                x, y = (i * 131 + 17) % W, 24 + (i * 47) % 100
                s.fill(col("white"), (x - 1, y, 3, 1))
                s.fill(col("white"), (x, y - 1, 1, 3))
    if "lanterns" in deco:
        for x in range(10, W, 28):
            y = 28 + int(math.sin(x * 0.05) * 4)
            s.fill(col("darkgray"), (x, y - 3, 1, 3))
            pygame.draw.ellipse(s, col("red" if (x // 28) % 2 else "orange"), (x - 3, y, 7, 8))
            s.fill(col("yellow"), (x - 1, y + 3, 3, 2))
    if "fireworks" in deco:
        for i in range(2):
            cyc = (t + i * 1.7) % 3.4
            if cyc < 1.2:
                cx, cy = 60 + ((int((t + i * 1.7) / 3.4) * 97 + i * 120) % 200), 50 + i * 24
                rr = int(cyc * 22)
                c = col(("hotpink", "yellow", "mint", "sky")[(int((t + i) / 3.4) + i) % 4])
                for a in range(0, 360, 30):
                    r = math.radians(a)
                    s.fill(c, (int(cx + math.cos(r) * rr), int(cy + math.sin(r) * rr), 1, 1))
    if "kites" in deco:
        for i in range(2):
            x = 70 + i * 170 + math.sin(t * 0.8 + i) * 12
            y = 50 + i * 16 + math.sin(t * 1.3 + i) * 6
            pygame.draw.polygon(s, col("red" if i else "yellow"), [(x, y - 6), (x + 5, y), (x, y + 7), (x - 5, y)])
            for j in range(1, 6):
                s.fill(col("white" if j % 2 else "pink"), (int(x + math.sin(t * 4 + j) * 2), int(y + 7 + j * 4), 2, 1))
    if flash > 0:
        ov = pygame.Surface((W, SILL), pygame.SRCALPHA)
        ov.fill((255, 247, 240, int(120 * min(1.0, flash * 4))))
        s.blit(ov, (0, 0))


def draw_frame(s, theme, t):
    """Window frame: tied-back curtains on the sides and a scalloped valance under the HUD band."""
    cur = theme[3]
    dark = "darkgray" if cur == "white" else "ink"
    for i in range(9):
        yb = 150 - i * 7 + int(math.sin(t * 1.2 + i * 0.5))
        c = col(dark if i % 3 == 2 else cur)
        s.fill(c, (i, 17, 1, yb - 17))
        s.fill(c, (W - 1 - i, 17, 1, yb - 17))
    s.fill(col("yellow"), (0, 98, 6, 2))
    s.fill(col("yellow"), (W - 6, 98, 6, 2))
    for x in range(0, W, 12):
        pygame.draw.circle(s, col(cur), (x + 6, 21), 5)
        s.fill(col(dark), (x + 6, 25, 1, 1))
    s.fill(col(cur), (0, 17, W, 4))
    s.fill(col("brown"), (0, 16, W, 2))


def draw_sill(s, t):
    s.fill(col("brown"), (0, SILL, W, 5))
    s.fill(col("peach"), (0, SILL, W, 1))
    s.fill(col("choco"), (0, SILL + 5, W, H - SILL - 5))
    s.fill(col("black"), (0, SILL + 5, W, 1))
    for y in (SILL + 11, SILL + 19):
        for x in range(4 + (y % 3) * 9, W, 47):
            s.fill(col("brown"), (x, y, 18, 1))


# ----------------------------------------------------------------------------- treasures
def draw_treasure(s, tr, t):
    kind, x, hp, mx = tr.kind, int(tr.x), tr.hp, tr.maxhp
    wob = int(math.sin(tr.wobble * 30) * 2) if tr.wobble > 0 else 0
    x += wob
    if kind == "bowl":
        cx, cy, r = x, 161, 11
        s.fill(col("choco"), (cx - 6, SILL - 2, 13, 2))
        level = cy + r - int((2 * r - 4) * hp / mx) if hp > 0 else cy + r + 1
        pygame.draw.circle(s, col("black"), (cx, cy), r + 1)
        pygame.draw.circle(s, col("sky" if hp > 0 else "darkgray"), (cx, cy), r)
        inner = col("ink")
        pygame.draw.circle(s, inner, (cx, cy), r - 1)
        if hp > 0:
            disc_below(s, cx, cy, r - 1, level, "blue")
            s.fill(col("sky"), (cx - int(math.sqrt(max(0, (r - 1) ** 2 - (level - cy) ** 2))), level, 1, 1))
            fx = cx - 4 + int(math.sin(t * 1.3 + tr.x) * 4)
            fy = max(level + 2, cy + 1) + int(math.sin(t * 3 + tr.x) * 1)
            s.blit(sprite("ww_fish", flip=math.cos(t * 1.3 + tr.x) < 0), (fx, fy))
        else:
            s.blit(sprite("ww_fish"), (cx - 2, cy + 6))
            s.fill(col("black"), (cx - 1, cy + 7, 1, 1))
        s.fill(col("white"), (cx - 7, cy - 6, 2, 3))
        s.fill(col("white"), (cx - 8, cy - 2, 1, 2))
        pygame.draw.ellipse(s, col("black"), (cx - 7, cy - r - 2, 15, 5))
        pygame.draw.ellipse(s, col("sky"), (cx - 6, cy - r - 1, 13, 3))
    elif kind == "pond":
        x0, y0, w = x - 22, 158, 45
        pygame.draw.rect(s, col("black"), (x0 - 1, y0 - 1, w + 2, SILL - y0 + 1), border_radius=3)
        pygame.draw.rect(s, col("gray" if hp > 0 else "darkgray"), (x0, y0, w, SILL - y0), border_radius=3)
        s.fill(col("ink"), (x0 + 2, y0 + 2, w - 4, SILL - y0 - 3))
        if hp > 0:
            lv = int((SILL - y0 - 4) * hp / mx)
            s.fill(col("teal"), (x0 + 2, SILL - 1 - lv, w - 4, lv))
            s.fill(col("mint"), (x0 + 2, SILL - 1 - lv, w - 4, 1))
            for i in range(2):
                fx = x0 + 8 + i * 18 + int(math.sin(t * (1.1 + i * 0.4) + i) * 6)
                s.blit(sprite("ww_fish", flip=math.cos(t * (1.1 + i * 0.4) + i) < 0), (fx, SILL - 7))
            pygame.draw.ellipse(s, col("lime"), (x0 + 28, SILL - 2 - lv, 9, 3))
        s.fill(col("white"), (x0 + 3, y0 + 3, 4, 1))
    else:   # bird feeder: a little house on a post with two chicks
        s.fill(col("brown"), (x - 1, 160, 3, SILL - 160))
        s.fill(col("choco"), (x - 9, 158, 19, 3))
        pygame.draw.polygon(s, col("red" if hp > 0 else "darkgray"), [(x - 11, 150), (x, 143), (x + 11, 150)])
        s.fill(col("black"), (x - 11, 150, 23, 1))
        s.fill(col("cream"), (x - 8, 151, 17, 7))
        if hp > 0:
            for i in range(min(2, hp)):
                bob = int(abs(math.sin(t * 4 + i * 1.3)) * 1)
                s.blit(sprite("ww_chick", flip=i == 1), (x - 7 + i * 9, 152 - bob))
            for i in range(hp):
                s.fill(col("yellow"), (x - 6 + i * 4, 157, 2, 1))
        else:
            s.fill(col("darkgray"), (x - 6, 155, 13, 1))
    if tr.shield > 0:
        cx = x
        cy = 158 if kind != "pond" else 164
        rr = 15 if kind != "pond" else 26
        c = col("mint" if int(t * 6) % 2 else "sky")
        pygame.draw.circle(s, c, (cx, cy), rr, 1)
    if tr.flash > 0 and int(t * 20) % 2:
        pygame.draw.circle(s, col("white"), (x, 160), 14, 1)


# ----------------------------------------------------------------------------- Maru
def draw_maru(s, m, t):
    """Maru, the very round silver tabby. m: the scene (mx, face, mood timers, swat side, cursor)."""
    cx = int(m.mx)
    base = SILL + 2
    walk = m.walking
    breath = math.sin(t * 2.6) * 1.0
    hop = int(abs(math.sin(t * 10)) * 2) if walk else 0
    if m.happy_t > 0:
        hop = int(abs(math.sin(m.happy_t * 14)) * 3)
    bw = 30 + int(breath)
    bh = 24 - int(breath)
    if m.meow_t > 0:
        bh += 2
        bw -= 1
    top = base - bh - hop
    lx = max(-2, min(2, int((m.cx - m.mx) / 40)))
    ly = max(-1, min(1, int((m.cy - 120) / 30)))
    # tail (behind the body)
    sway = math.sin(t * 3.2 + (2 if m.hurt_t > 0 else 0)) * (4 if m.hurt_t <= 0 else 7)
    for i in range(7):
        a = i / 6
        tx = cx + 13 + int(a * 6)
        ty = base - 4 - int(a * 14) - hop
        tx += int(sway * a * a)
        pygame.draw.circle(s, col("black"), (tx, ty), 3)
    for i in range(7):
        a = i / 6
        tx = cx + 13 + int(a * 6) + int(sway * a * a)
        ty = base - 4 - int(a * 14) - hop
        pygame.draw.circle(s, col("gray" if i % 2 == 0 else "darkgray"), (tx, ty), 2)
    # ears
    for side in (-1, 1):
        ex = cx + side * 9
        pygame.draw.polygon(s, col("black"), [(ex - 5, top + 6), (ex + side * 2, top - 6), (ex + 6, top + 6)])
        pygame.draw.polygon(s, col("gray"), [(ex - 3, top + 5), (ex + side * 2, top - 3), (ex + 4, top + 5)])
        pygame.draw.polygon(s, col("pink"), [(ex - 1, top + 4), (ex + side * 1, top), (ex + 2, top + 4)])
    # body
    pygame.draw.ellipse(s, col("black"), (cx - bw // 2 - 1, top - 1, bw + 2, bh + 2))
    pygame.draw.ellipse(s, col("gray"), (cx - bw // 2, top, bw, bh))
    s.fill(col("lavender"), (cx - bw // 2 + 5, top + 3, 4, 1))
    # tabby stripes: forehead M and the sides
    for dx in (-3, 0, 3):
        s.fill(col("darkgray"), (cx + dx, top + 2, 1, 3 if dx else 4))
    for side in (-1, 1):
        for k in range(2):
            s.fill(col("darkgray"), (cx + side * (bw // 2 - 4) - (2 if side > 0 else 0), top + 12 + k * 4, 3, 1))
    # white muzzle + bib
    pygame.draw.ellipse(s, col("white"), (cx - 8, top + 11, 17, 9))
    pygame.draw.ellipse(s, col("white"), (cx - 6, top + 17, 13, bh - 17))
    # face
    ey = top + 8 + ly
    mood = "happy"
    if m.hurt_t > 0:
        mood = "wow"
    elif m.tired_t > 0:
        mood = "sleepy"
    if m.happy_t > 0 or m.meow_t > 0:
        for side in (-1, 1):       # ^ ^ eyes
            ex = cx + side * 6 + lx
            s.fill(col("black"), (ex - 2, ey + 1, 1, 1))
            s.fill(col("black"), (ex - 1, ey, 1, 1))
            s.fill(col("black"), (ex, ey - 1, 1, 1))
            s.fill(col("black"), (ex + 1, ey, 1, 1))
            s.fill(col("black"), (ex + 2, ey + 1, 1, 1))
    else:
        blink = int(t * 1.3) % 6 == 0 and (t * 1.3) % 1 < 0.15
        cute.eyes(s, cx + lx, ey, 6, 0, mood, blink=blink, size=2)
    cute.blush(s, cx + lx, ey + 4, 7)
    s.fill(col("pink"), (cx - 1 + lx, top + 13, 3, 2))
    if m.meow_t > 0:
        pygame.draw.ellipse(s, col("black"), (cx - 3 + lx, top + 15, 7, 6))
        s.fill(col("pink"), (cx - 1 + lx, top + 18, 3, 2))
    elif m.hurt_t > 0:
        cute.mouth(s, cx + lx, top + 16, "wow")
        s.fill(col("sky"), (cx + 12, top + 3 + int((m.hurt_t * 10) % 3), 2, 3))
    else:
        cute.mouth(s, cx + lx, top + 15, "happy")
    # whiskers
    for side in (-1, 1):
        for k in (0, 2):
            x0 = cx + side * 9
            s.fill(col("white"), (x0 if side > 0 else x0 - 5, top + 13 + k, 5, 1))
    # paws: one goes up to swat
    for side in (-1, 1):
        px = cx + side * 6
        if m.swat_t > 0 and side == m.swat_side:
            f = m.swat_t / 0.25
            ax = px + side * int(4 * f)
            ay = top + 8 - int(10 * f)
            pygame.draw.circle(s, col("black"), (ax, ay), 4)
            pygame.draw.circle(s, col("white"), (ax, ay), 3)
            s.fill(col("pink"), (ax - 1, ay, 2, 1))
        elif m.meow_t > 0:
            pygame.draw.circle(s, col("black"), (px + side * 10, top + 10), 4)
            pygame.draw.circle(s, col("white"), (px + side * 10, top + 10), 3)
        else:
            step = int(math.sin(t * 10 + side) * 1) if walk else 0
            pygame.draw.ellipse(s, col("black"), (px - 4, base - 5 - step, 9, 6))
            pygame.draw.ellipse(s, col("white"), (px - 3, base - 4 - step, 7, 4))
    if m.tired_t > 0 and int(t * 4) % 2:
        draw_text(s, "Z", cx + 14, top - 4, "lavender", shadow=None)


# ----------------------------------------------------------------------------- things
def draw_thing(s, th, t, theme_deco=()):
    k = th.k
    x, y = int(th.x), int(th.y)
    if th.flash > 0 and int(t * 30) % 2:
        pygame.draw.circle(s, col("white"), (x, y), th.r + 1)
        return
    if k == "drop":
        s.blit(sprite("ww_drop"), (x - 3, y - 5))
    elif k == "leaf":
        s.blit(sprite("ww_leaf", int(th.age * 3) % 2, flip=math.sin(th.age * 2.2 + th.q) > 0), (x - 4, y - 3))
    elif k == "bug":
        s.blit(sprite("ww_bug", int(t * 16) % 2, flip=th.vx < 0), (x - 4, y - 3))
    elif k == "dart":
        s.blit(sprite("ww_dart", flip=th.vx < 0), (x - 6, y - 2))
    elif k == "bubble":
        pygame.draw.circle(s, col("blue"), (x, y), 7, 1)
        bubble(s, x, y, 6, t + th.q, "sky")
    elif k == "mini":
        pygame.draw.circle(s, col("purple"), (x, y), 4, 1)
        bubble(s, x, y, 3, t, "lavender")
    elif k == "crow":
        if th.mode == 2:
            s.blit(sprite("ww_dive"), (x - 6, y - 4))
        else:
            s.blit(sprite("ww_crow", int(t * 8) % 2 if th.mode == 0 else 0, flip=th.side < 0), (x - 8, y - 5))
            if th.mode == 1:
                draw_text(s, "!", x - 2, y - 15, "red" if int(t * 10) % 2 else "yellow", shadow="black")
    elif k == "hail":
        if "leaves" in theme_deco:
            s.blit(sprite("ww_acorn", remap={"n": "d"} if th.hp < 2 else None), (x - 3, y - 4))
        else:
            s.blit(sprite("ww_hail", remap={"w": "s"} if th.hp < 2 else None), (x - 3, y - 3))
    elif k == "moth":
        s.blit(sprite("ww_moth", int(t * 12) % 2), (x - 5, y - 3))
    elif k == "rocket":
        s.blit(sprite("ww_rocket"), (x - 2, y - 5))
        for i in range(3):
            s.fill(col(("yellow", "orange", "red")[i]), (x - 1 + (i % 2), y + 5 + i * 2 + int(t * 30) % 2, 1, 2))
    elif k == "spark":
        c = ("yellow", "white", "orange", "hotpink")[(th.id + int(t * 12)) % 4]
        s.fill(col(c), (x - 1, y - 1, 3, 3))
        s.fill(col("white"), (x, y, 1, 1))
    elif k == "snow":
        s.blit(sprite("ww_snow"), (x - 4, y - 4))
        if th.hp < 2:
            s.fill(col("sky"), (x - 1, y - 3, 1, 5))
    elif k == "plane":
        a = math.atan2(th.vy, th.vx)
        ca, sa = math.cos(a), math.sin(a)
        nose = (x + ca * 6, y + sa * 6)
        back_l = (x - ca * 5 - sa * 4, y - sa * 5 + ca * 4)
        back_r = (x - ca * 5 + sa * 4, y - sa * 5 - ca * 4)
        mid = (x - ca * 3, y - sa * 3)
        pygame.draw.polygon(s, col("black"), [(x + ca * 8, y + sa * 8), (x - ca * 7 - sa * 6, y - sa * 7 + ca * 6),
                                              (x - ca * 4, y - sa * 4), (x - ca * 7 + sa * 6, y - sa * 7 - ca * 6)])
        pygame.draw.polygon(s, col("white"), [nose, back_l, mid])
        pygame.draw.polygon(s, col("sky"), [nose, mid, back_r])
    elif k == "puff":
        pygame.draw.line(s, col("lime"), (x, y + 2), (x, y + 7))
        for i in range(10):
            a = i * 0.628 + t * 0.6
            s.fill(col("white"), (x + int(math.cos(a) * 5), y + int(math.sin(a) * 5), 1, 1))
            s.fill(col("cream"), (x + int(math.cos(a) * 3), y + int(math.sin(a) * 3), 1, 1))
        s.fill(col("yellow"), (x - 1, y - 1, 2, 2))
    elif k == "seed":
        s.fill(col("darkgray"), (x - 2, y - 1, 5, 1))
        s.fill(col("white"), (x - 2, y - 2, 5, 1))
        s.fill(col("white"), (x, y - 3, 1, 3))
        s.fill(col("brown"), (x, y, 1, 2))
    elif k == "star":
        for i in range(1, 5):
            s.fill(col(("white", "yellow", "orange", "pink")[i - 1]),
                   (int(th.x - th.vx * 0.018 * i), int(th.y - th.vy * 0.018 * i), 2, 2))
        s.blit(sprite("star"), (x - 3, y - 3))
    elif k == "food":
        for i, (dx, dy) in enumerate(((-2, 0), (1, -1), (0, 2), (2, 1))):
            s.fill(col("orange" if i % 2 else "yellow"), (x + dx, y + dy, 2, 1))
        if int(t * 4) % 2:
            draw_text(s, "FOOD", x, y - 11, "lime", align="center", shadow="black")
    elif k == "cap":
        pygame.draw.circle(s, col("ink"), (x, y), 8, 1)
        bubble(s, x, y, 7, t, CAP_COLORS.get(th.letter, "pink"))
        draw_text(s, th.letter, x - 2, y - 3, CAP_COLORS.get(th.letter, "pink"), shadow="black")
    elif k == "orb":
        r = 4 + int(t * 12) % 2
        pygame.draw.circle(s, col("orange"), (x, y), r + 1)
        pygame.draw.circle(s, col("yellow"), (x, y), r)
        pygame.draw.circle(s, col("white"), (x - 1, y - 1), 2)
        for i in range(1, 4):
            s.fill(col("yellow"), (int(th.x - th.vx * 0.03 * i), int(th.y - th.vy * 0.03 * i), 2, 2))
    elif k == "feather":
        s.blit(sprite("ww_feather", flip=th.vx < 0), (x - 3, y - 2))
    elif k == "treat":
        s.blit(sprite("ww_treat", flip=th.id % 2 == 0), (x - 5, y - 3))
    elif k == "gold":
        s.blit(sprite("ww_gold", flip=th.side < 0), (x - 6, y - 3))
        if int(t * 8) % 2:
            s.fill(col("white"), (x + 3 * th.side, y - 5, 1, 1))
    elif k == "fly":
        glow = int(t * 6 + th.id) % 3
        if glow:
            s.fill(col("lime"), (x - 3, y, 7, 1))
            s.fill(col("lime"), (x, y - 3, 1, 7))
            s.fill(col("yellow"), (x - 1, y - 1, 3, 3))
        s.fill(col("lime" if glow else "yellow"), (x, y, 1, 1))
        s.fill(col("ink"), (x, y - 2, 1, 1))
    elif k == "rise":
        pygame.draw.circle(s, col("blue" if th.id % 3 else "hotpink"), (x, y), 6, 1)
        bubble(s, x, y, 5, t + th.q, "pink" if th.id % 3 == 0 else "sky")


def draw_paw_cursor(s, x, y, t, ready, color="white"):
    x, y = int(x), int(y)
    remap = None if ready else {"w": "g"}
    if color != "white" and ready:
        remap = {"w": {"lime": "l", "yellow": "y", "pink": "p", "sky": "s"}.get(color, "w")}
    s.blit(sprite("ww_paw", remap=remap), (x - 4, y - 4))
    if ready:
        for dx, dy in ((-9, 0), (8, 0), (0, -9), (0, 8)):
            if int(t * 4) % 2:
                s.fill(col("white"), (x + dx, y + dy, 1, 1))


# ----------------------------------------------------------------------------- preview (game carousel)
def preview(s, t):
    w, h = s.get_size()
    for i in range(h):
        s.fill(lerp_col("sky", "cream", i / h), (0, i, w, 1))
    pygame.draw.circle(s, col("yellow"), (w - 16, 14), 7)
    # falling things
    for i in range(5):
        x = 10 + (i * 23) % (w - 20)
        y = int((t * 22 + i * 17) % (h - 20))
        name = ("ww_drop", "ww_leaf", "ww_bug", "ww_drop", "ww_leaf")[i]
        s.blit(sprite(name, int(t * 4) % 2), (x, y))
    # a swat ring
    cyc = (t * 1.2) % 1.0
    rx, ry = w // 2 + int(math.sin(t * 0.7) * 26), 26
    pygame.draw.circle(s, col("white"), (rx, ry), 2 + int(cyc * 12), 1)
    s.blit(sprite("ww_paw"), (rx - 4, ry - 4))
    # windowsill, bowls, Maru
    s.fill(col("brown"), (0, h - 12, w, 12))
    s.fill(col("peach"), (0, h - 12, w, 1))
    for bx in (18, w - 18):
        pygame.draw.circle(s, col("black"), (bx, h - 20), 8)
        pygame.draw.circle(s, col("sky"), (bx, h - 20), 7)
        disc_below(s, bx, h - 20, 6, h - 21, "blue")
        s.blit(sprite("ww_fish"), (bx - 2, h - 18))
    cx = w // 2
    top = h - 12 - 20 + int(abs(math.sin(t * 3)) * 1)
    for side in (-1, 1):
        ex = cx + side * 7
        pygame.draw.polygon(s, col("black"), [(ex - 4, top + 5), (ex + side * 2, top - 5), (ex + 5, top + 5)])
        pygame.draw.polygon(s, col("pink"), [(ex - 2, top + 4), (ex + side * 2, top - 1), (ex + 3, top + 4)])
    pygame.draw.ellipse(s, col("black"), (cx - 13, top - 1, 26, 22))
    pygame.draw.ellipse(s, col("gray"), (cx - 12, top, 24, 20))
    pygame.draw.ellipse(s, col("white"), (cx - 6, top + 9, 13, 8))
    for dx in (-2, 0, 2):
        s.fill(col("darkgray"), (cx + dx, top + 2, 1, 3))
    cute.eyes(s, cx, top + 7, 5, int(math.sin(t * 0.7) * 1.5), "happy", size=2)
    s.fill(col("pink"), (cx - 1, top + 10, 3, 1))
