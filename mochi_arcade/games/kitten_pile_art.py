"""KITTEN PILE art and music: kitten sprites, pillows, grandpa cats, yarn, toy mice, the big cats (Poppy the
night-shift nanny, rivals and bosses), bedroom backgrounds and two original chiptunes.

All original pixel art for MOCHI ARCADE. Mirrored in ios/MochiArcade/Games/KittenPileArt.swift.
"""
import math

import pygame

from mochi_arcade import music, sprites
from mochi_arcade.gfx import H, W, col, lerp_col, sprite

CELL = 12


# ---------------------------------------------------------------------------- sprites
# o coat  n markings  h second markings  c muzzle  p ears/nose  u eyes  k outline   (recoloured per kitten)
def _row(base, marks):
    r = list(base)
    for i, ch in marks.items():
        r[i] = ch
    return "".join(r)


_PLAIN = "k" + "o" * 10 + "k"
_EYES = {   # rows 5 and 6: (column -> char)
    "open": ({2: "w", 3: "u", 8: "w", 9: "u"}, {2: "u", 3: "u", 8: "u", 9: "u"}),
    "blink": ({}, {2: "k", 3: "k", 8: "k", 9: "k"}),
    "sleep": ({1: "k", 4: "k", 7: "k", 10: "k"}, {2: "k", 3: "k", 8: "k", 9: "k"}),
    "happy": ({2: "k", 3: "k", 8: "k", 9: "k"}, {1: "k", 4: "k", 7: "k", 10: "k"}),
    "wow": ({2: "u", 3: "u", 8: "u", 9: "u"}, {2: "u", 3: "u", 8: "u", 9: "u", 1: "w", 10: "w"}),
    "grumpy": ({1: "k", 2: "k", 9: "k", 10: "k"}, {2: "u", 3: "u", 8: "u", 9: "u"}),
}
MOODS = ["open", "blink", "sleep", "happy", "wow", "grumpy"]
_TOP = [".kk......kk.", "kpok....kopk", "kppokkkkoppk"]
_BOTTOM = ["kooocppcoook", "koockcckcook", ".koccccccok.", "..kkkkkkkk..", "............"]
_MARK = {"kp_kit": ["koooonnooook", "knoooooooonk"], "kp_cal": ["knnnnoohhhhk", "knnnnoohhhhk"]}
_TOPS = {"kp_kit": _TOP, "kp_cal": [".kk......kk.", "knnk....khhk", "knnnkkkkhhhk"]}
_BOTS = {"kp_kit": _BOTTOM, "kp_cal": ["knnocppcohhk", "knockcckcohk", ".kncccccchk.", "..kkkkkkkk..", "............"]}


def _kitten(name, mood):
    a, b = _EYES[mood]
    base5 = _row(_PLAIN, {1: "n"}) if name == "kp_kit" else _row(_PLAIN, {1: "n", 10: "h"})
    base6 = _PLAIN if name == "kp_kit" else _row(_PLAIN, {1: "n", 10: "h"})
    return _TOPS[name] + _MARK[name] + [_row(base5, a), _row(base6, b)] + _BOTS[name]


KP_ART = {name: [_kitten(name, m) for m in MOODS] for name in ("kp_kit", "kp_cal")}
KP_ART.update({
    "kp_pillow": [[
        "............",
        ".cwwwwwwwwc.",
        "cwwwwwwwwwwc",
        "cwwvwwwwvwwc",
        "cwwwvvvvwwwc",
        "cwwwwwwwwwwc",
        "cwwwwwwwwwwc",
        "cwwvwwwwvwwc",
        "cwwwvvvvwwwc",
        "cwwwwwwwwwwc",
        ".cccccccccc.",
        "............",
    ]],
    # grandpa: sound asleep, then yawning with one eye open
    "kp_grandpa": [[
        ".kk......kk.",
        "kgdk....kdgk",
        "kggdkkkkdggk",
        "kgwwwggwwwgk",
        "kgggggggdggk",
        "kgkkggggkkgk",
        "kggggggggggk",
        "kwwwgppgwwwk",
        "wwwwwkkwwwww",
        ".kwwwwwwwwk.",
        "..kkkkkkkk..",
        "............",
    ], [
        ".kk......kk.",
        "kgdk....kdgk",
        "kggdkkkkdggk",
        "kgwwwggwwwgk",
        "kggggggkkkgk",
        "kgkkggkwkkgk",
        "kgggggkkkkgk",
        "kwwwgppgwwwk",
        "wwwwkrrkwwww",
        ".kwwkrrkwwk.",
        "..kkkkkkkk..",
        "............",
    ]],
    "kp_yarn": [[
        "............",
        "....kkkk....",
        "..kkpPpPkk..",
        ".kpPwpPpPpk.",
        ".kPwpPpPpPk.",
        "kpPpPpPpPpPk",
        "kPpPpPpPpPpk",
        ".kpPpPpPpPk.",
        ".kPpPpPpPpk.",
        "..kkpPpPkk.P",
        "....kkkk.PP.",
        "............",
    ]],
    "kp_mouse": [[
        "............",
        "..kk........",
        ".kpgk.......",
        ".kggkkkk....",
        "..kggggggk..",
        ".kkgggggggk.",
        "kpgggwgggggk",
        "kggggggggggk",
        ".kkkkkkkkkk.",
        "..........kk",
        "...........k",
        "............",
    ]],
    "kp_star": [[
        "..y..",
        ".yyy.",
        "yyyyy",
        ".yyy.",
        ".y.y.",
    ]],
    "kp_fish": [[
        "...........",
        "..yyyyy..y.",
        ".yyyyyyy.yy",
        "yykyyyyyyy.",
        ".yyyyyyy.yy",
        "..yyyyy..y.",
    ]],
})
for _name, _frames in KP_ART.items():
    for _f in _frames:
        assert all(len(r) == len(_f[0]) for r in _f), (_name, _f)
sprites.ART.update(KP_ART)

# kitten colours: (sprite, remap) - 1 ginger, 2 tabby, 3 sooty, 4 snowy, 5 calico
KITTENS = {
    1: ("kp_kit", {"o": "o", "n": "n", "c": "c", "p": "p", "u": "k"}),
    2: ("kp_kit", {"o": "g", "n": "d", "c": "w", "p": "p", "u": "k"}),
    3: ("kp_kit", {"o": "i", "n": "k", "c": "d", "p": "P", "u": "y", "k": "k"}),
    4: ("kp_kit", {"o": "w", "n": "c", "c": "w", "p": "p", "u": "b"}),
    5: ("kp_cal", {"o": "w", "n": "o", "h": "i", "c": "c", "p": "p", "u": "k"}),
}
POPPY_REMAP = {"o": "v", "n": "u", "c": "c", "p": "p", "u": "m"}     # Poppy's face as a kitten-size icon
KIT_NAMES = {1: "GINGER", 2: "TABBY", 3: "SOOTY", 4: "SNOWY", 5: "CALICO"}
KIT_COAT = {1: "orange", 2: "gray", 3: "ink", 4: "white", 5: "peach"}     # connectors / particles
KIT_DARK = {1: "brown", 2: "darkgray", 3: "black", 4: "cream", 5: "orange"}


# ---------------------------------------------------------------------------- the bed and its kittens
def kitten(s, x, y, code, mood=0, t=0.0):
    """One kitten sprite at the cell's top-left (code may carry the STAR / GOLD flags)."""
    name, remap = KITTENS[code & 7]
    s.blit(sprite(name, mood, remap=remap), (x, y))
    if code & 32:       # golden kitten: golden ear tips + a glint sweeping across
        s.fill(col("yellow"), (x + 1, y, 2, 2))
        s.fill(col("yellow"), (x + 9, y, 2, 2))
        ph = int(t * 10) % 14
        if ph < 10:
            s.fill(col("white"), (x + ph, y + 3, 2, 1))
            s.fill(col("yellow"), (x + ph + 1, y + 4, 1, 2))
    if code & 16:       # star kitten: a little star pinned to the forehead
        s.blit(sprite("kp_star"), (x + 4, y - 2 + int(math.sin(t * 5 + x) * 1)))


def link(s, x, y, k, right):
    """Paws holding: bridge two touching kittens of one colour (right: to the east, else to the south)."""
    c = col(KIT_COAT[k])
    if right:
        s.fill(c, (x + 10, y + 5, 4, 3))
        s.fill(col("black"), (x + 10, y + 4, 4, 1))
    else:
        s.fill(c, (x + 4, y + 9, 4, 5))
        s.fill(col(KIT_DARK[k]), (x + 5, y + 10, 2, 1))


def junk(s, x, y, code, t=0.0):
    if code == 8:
        s.blit(sprite("kp_pillow"), (x, y))
    else:
        s.blit(sprite("kp_grandpa", 0 if code == 9 else 1), (x, y))
        if code == 9 and int(t * 2 + x) % 4 == 0:
            draw_z(s, x + 9, y - 3, "white")


def special(s, x, y, code, t=0.0):
    if code == 11:
        s.blit(sprite("kp_yarn"), (x, y))
        a = t * 6
        s.fill(col("white"), (x + 5 + int(math.cos(a) * 3), y + 5 + int(math.sin(a) * 3), 1, 1))
    else:
        s.blit(sprite("kp_mouse", flip=int(t * 4) % 2 == 0), (x, y + int(t * 12) % 2))


def cell(s, x, y, code, mood=0, t=0.0):
    if not code:
        return
    if code & 8:
        if code <= 10:
            junk(s, x, y, code, t)
        else:
            special(s, x, y, code, t)
    else:
        kitten(s, x, y, code, mood, t)


def curl(s, x, y, code, f):
    """A kitten curling up to sleep (f: 0 -> 1): eyes close, it shrinks into a ball, then a puff."""
    if f < 0.45:
        kitten(s, x, y, code, 2 if f > 0.12 else 1)
        if f > 0.2:
            draw_z(s, x + 9, y - 2 - int((f - 0.2) * 20), "white")
    else:
        r = max(1, int(6 * (1 - (f - 0.45) / 0.55)))
        pygame.draw.circle(s, col("black"), (x + 6, y + 7), r + 1)
        pygame.draw.circle(s, col(KIT_COAT[code & 7]), (x + 6, y + 7), r)
        draw_z(s, x + 8, y - 6 - int(f * 10), "lavender")


def draw_z(s, x, y, c="white"):
    s.fill(col(c), (x, y, 3, 1))
    s.fill(col(c), (x + 1, y + 1, 1, 1))
    s.fill(col(c), (x, y + 2, 3, 1))


def bed(s, bx, by, w, h, th):
    """The wicker cat bed around the play field, with a dotted cushion inside."""
    hue, acc = th[1], th[2]
    pygame.draw.rect(s, col("black"), (bx - 7, by - 3, w + 14, h + 12), border_radius=6)
    pygame.draw.rect(s, col("brown"), (bx - 6, by - 2, w + 12, h + 10), border_radius=6)
    for yy in range(by, by + h + 6, 4):          # wicker weave
        for xx in (bx - 5, bx + w + 1):
            s.fill(col("choco"), (xx + (yy // 4) % 2 * 2, yy, 2, 2))
    s.fill(col("peach"), (bx - 5, by - 2, w + 10, 2))
    s.fill(lerp_col("night", hue, 0.22), (bx, by, w, h))
    dot = lerp_col("night", hue, 0.3)
    for yy in range(by + 6, by + h, 18):
        for xx in range(bx + 6 + (yy - by) // 18 % 2 * 9, bx + w, 18):
            s.fill(dot, (xx, yy, 2, 2))
    pygame.draw.rect(s, col("brown"), (bx - 6, by + h + 1, w + 12, 7), border_radius=3)
    s.fill(col("choco"), (bx - 4, by + h + 4, w + 8, 1))
    s.fill(col(acc), (bx + w // 2 - 6, by + h + 3, 12, 3))


def draw_bg(s, th, t):
    style = th[3]
    s.fill(lerp_col("black", th[1], 0.16))
    deco = lerp_col("black", th[1], 0.28)
    if style == 0:          # drifting dots
        for i in range(40):
            pygame.draw.circle(s, deco, ((i * 53 + 11) % W, (i * 29 + int(t * 4)) % (H + 8) - 4), 2 + i % 2)
    elif style == 1:        # wallpaper stripes
        off = int(t * 5) % 20
        for x in range(-20, W + 20, 20):
            s.fill(deco, (x + off, 0, 6, H))
    elif style == 2:        # twinkles
        for i in range(30):
            x, y = (i * 71 + 7) % W, (i * 37 + 11) % H
            if int(t * 2 + i) % 6:
                s.fill(deco, (x, y - 2, 1, 5))
                s.fill(deco, (x - 2, y, 5, 1))
    elif style == 3:        # slow checks
        off = int(t * 4) % 32
        for y in range(-32, H + 32, 16):
            for x in range(-32, W + 32, 16):
                if ((x + y) // 16) % 2 == 0:
                    s.fill(deco, (x + off, y + off // 2, 16, 16))
    else:                   # floating hearts
        for i in range(24):
            x, y = (i * 61 + 23) % W, (i * 43 + int(t * 6)) % (H + 10) - 5
            pygame.draw.circle(s, deco, (x - 2, y), 2)
            pygame.draw.circle(s, deco, (x + 2, y), 2)
            pygame.draw.polygon(s, deco, [(x - 4, y + 1), (x + 4, y + 1), (x, y + 5)])


# ---------------------------------------------------------------------------- big cats
def big_cat(s, cx, cy, r, coat, mark, eye, mood="open", t=0.0, look=0, pattern="tabby", ear=0, muzzle="cream"):
    """A round cat head (radius r) - Poppy, the rivals and the bosses all share it.
    mood: open | angry | smug | happy | sleep | wow | hurt"""
    k = col("black")
    if pattern == "fluff":          # scalloped fur edge behind the head
        for pass_ in range(2):
            for i in range(12):
                a = i * 0.5236 + 0.26
                fx, fy = cx + int(math.cos(a) * r), cy + int(math.sin(a) * r * 0.9) + 1
                pygame.draw.circle(s, k if pass_ == 0 else col(coat), (fx, fy), r // 4 + 2 - pass_)
    for side in (-1, 1):            # ears
        tw = ear if side < 0 else 0
        ax, ay = cx + side * r, cy - r // 3
        bx, by = cx + side * (r * 3 // 4), cy - r - r // 2 + tw
        qx, qy = cx + side * (r // 4), cy - r + 1
        pygame.draw.polygon(s, k, [(ax + side, ay + 1), (bx + side, by - 1), (qx - side, qy - 1)])
        pygame.draw.polygon(s, col(coat), [(ax, ay), (bx, by), (qx, qy)])
        pygame.draw.polygon(s, col("pink"), [(ax - side * 3, ay - 2), (bx, by + 4), (qx + side * 2, qy + 1)])
    if pattern != "fluff":
        pygame.draw.circle(s, k, (cx, cy), r + 1)
        pygame.draw.ellipse(s, k, (cx - r - 2, cy - r // 4 - 1, 2 * r + 4, r + 3))
    pygame.draw.circle(s, col(coat), (cx, cy), r)
    pygame.draw.ellipse(s, col(coat), (cx - r - 1, cy - r // 4, 2 * r + 2, r + 1))
    m = col(mark)
    if pattern == "tabby":
        s.fill(m, (cx - 1, cy - r + 1, 3, r // 3))
        s.fill(m, (cx - r // 3 - 2, cy - r + 3, 2, r // 4))
        s.fill(m, (cx + r // 3 + 1, cy - r + 3, 2, r // 4))
        for side in (-1, 1):
            for i in range(2):
                s.fill(m, (cx + side * (r - 1) - (3 if side > 0 else 0), cy + i * 3, 4, 1))
    elif pattern == "tux":
        pygame.draw.ellipse(s, m, (cx - r // 2 - 1, cy - 1, r + 2, r // 2 + 4))
        pygame.draw.polygon(s, m, [(cx - 2, cy - r // 2), (cx + 2, cy - r // 2), (cx + r // 3, cy + 2),
                                   (cx - r // 3, cy + 2)])
    elif pattern == "patch":
        pygame.draw.circle(s, m, (cx + r // 2, cy - r // 4), r // 2)
    elif pattern == "fluff":
        pygame.draw.ellipse(s, m, (cx - r // 2, cy + r // 6, r, r // 2 + 2))
    elif pattern == "cosmic":
        for i in range(7):
            s.fill(m, (cx + int(math.cos(i * 1.1 + t) * r * 0.6), cy - r // 2 + int(math.sin(i * 1.7) * r * 0.3), 1, 1))
    es = max(2, r // 5)
    ey = cy - r // 8
    if pattern == "mask":
        s.fill(m, (cx - r, ey - es - 2, 2 * r + 1, 2 * es + 5))
    for side in (-1, 1):
        ex = cx + side * (r * 2 // 5) + look
        if mood in ("open", "angry", "smug"):
            pygame.draw.ellipse(s, col(eye), (ex - es, ey - es - 1, 2 * es + 1, 2 * es + 3))
            pygame.draw.ellipse(s, k, (ex - es // 2, ey - es, es + 1, 2 * es + 1))
            s.fill(col("white"), (ex - es + 1, ey - es, 2, 2))
            if mood == "smug":
                s.fill(col(coat), (ex - es, ey - es - 1, 2 * es + 1, es + 1))
                s.fill(k, (ex - es, ey, 2 * es + 1, 1))
            if mood == "angry":
                pygame.draw.line(s, k, (ex - side * es * 2, ey - es - 3), (ex + side, ey - es), 2)
        elif mood == "happy":
            pygame.draw.lines(s, k, False, [(ex - es, ey + 1), (ex, ey - es + 1), (ex + es, ey + 1)], 2)
        elif mood == "sleep":
            pygame.draw.lines(s, k, False, [(ex - es, ey - 1), (ex, ey + es - 1), (ex + es, ey - 1)], 2)
        elif mood == "wow":
            pygame.draw.circle(s, col("white"), (ex, ey), es + 1)
            pygame.draw.circle(s, k, (ex, ey), es + 1, 1)
            s.fill(k, (ex - 1, ey - 1, 2, 2))
        else:               # hurt: > <
            pygame.draw.lines(s, k, False, [(ex - side * es, ey - es), (ex + side * es, ey), (ex - side * es, ey + es)], 2)
    mz = col(muzzle)
    my = cy + r // 3
    pygame.draw.circle(s, mz, (cx - es + 1, my), es)
    pygame.draw.circle(s, mz, (cx + es - 1, my), es)
    pygame.draw.polygon(s, col("hotpink"), [(cx - 2, my - es), (cx + 2, my - es), (cx, my - es + 2)])
    if mood in ("wow", "hurt"):
        pygame.draw.ellipse(s, k, (cx - 2, my + 1, 5, 5))
    elif mood == "happy":
        pygame.draw.ellipse(s, k, (cx - 3, my, 7, 5))
        s.fill(col("hotpink"), (cx - 1, my + 2, 3, 2))
    elif mood == "angry":
        s.fill(k, (cx - 2, my + 2, 5, 1))
    else:
        s.fill(k, (cx - 2, my + 1, 2, 1))
        s.fill(k, (cx + 1, my + 1, 2, 1))
        s.fill(k, (cx, my, 1, 1))
    for side in (-1, 1):
        x0 = cx + side * (es + 3)
        pygame.draw.line(s, col("white"), (x0, my - 1), (x0 + side * (r // 2 + 3), my - 3))
        pygame.draw.line(s, col("white"), (x0, my + 1), (x0 + side * (r // 2 + 3), my + 2))
        if mood != "angry":
            s.fill(col("pink"), (cx + side * (r // 2 + 2) - 2, my - es + 1, 4, 2))


def star(s, x, y, r, c):
    pygame.draw.polygon(s, col(c), [(x, y - r), (x + r // 2 + 1, y), (x, y + r), (x - r // 2 - 1, y)])
    pygame.draw.polygon(s, col(c), [(x - r, y), (x, y - r // 2 - 1), (x + r, y), (x, y + r // 2 + 1)])


def accessory(s, kind, cx, cy, r, t, c2="red"):
    k = col("black")
    if kind == "tophat":
        hx = cx - r // 2 - 1
        s.fill(k, (hx - 4, cy - r - 2, r + 10, 3))
        s.fill(k, (hx, cy - r - 16, r + 2, 14))
        s.fill(col("red"), (hx, cy - r - 6, r + 2, 3))
        pygame.draw.circle(s, col("yellow"), (cx + r * 2 // 5, cy - r // 8), max(3, r // 4), 1)
        pygame.draw.line(s, col("yellow"), (cx + r * 2 // 5 + 2, cy), (cx + r - 2, cy + r // 2))
    elif kind == "bow":
        bx, by = cx - r + 2, cy - r + 1
        pygame.draw.polygon(s, col("hotpink"), [(bx, by), (bx - 7, by - 5), (bx - 7, by + 5)])
        pygame.draw.polygon(s, col("hotpink"), [(bx, by), (bx + 7, by - 5), (bx + 7, by + 5)])
        pygame.draw.circle(s, col("pink"), (bx, by), 2)
    elif kind == "mask":
        tail = int(math.sin(t * 8) * 3)
        pygame.draw.polygon(s, col("red"), [(cx + r, cy - r // 3), (cx + r + 10, cy - r // 3 - 4 + tail),
                                            (cx + r + 9, cy - r // 3 + 3 + tail)])
        s.fill(col("red"), (cx - r + 1, cy - r // 2 - 2, 2 * r - 1, 2))
    elif kind == "phones":
        pygame.draw.circle(s, col("hotpink"), (cx, cy - 2), r + 3, 2)
        s.fill(col("sky"), (cx - r - 4, cy - 4, 5, 9))
        s.fill(col("sky"), (cx + r, cy - 4, 5, 9))
        if int(t * 4) % 2:
            s.fill(col("yellow"), (cx + r + 7, cy - 10, 2, 2))
            s.fill(col("yellow"), (cx - r - 9, cy - 12, 2, 2))
    elif kind == "crown":
        y0 = cy - r - 3
        pygame.draw.polygon(s, col("yellow"), [(cx - r // 2 - 2, y0 + 4), (cx - r // 2 - 2, y0 - 6), (cx - r // 4, y0 - 1),
                                                (cx, y0 - 8), (cx + r // 4, y0 - 1), (cx + r // 2 + 2, y0 - 6),
                                                (cx + r // 2 + 2, y0 + 4)])
        s.fill(col("red"), (cx - 1, y0 - 2, 3, 3))
        pygame.draw.ellipse(s, col("white"), (cx - r // 2, cy + r // 3 + 2, r, r // 2))
    elif kind == "moon":
        mx, my = cx - r - 2, cy - r - 4
        pygame.draw.circle(s, col("yellow"), (mx, my), 6)
        pygame.draw.circle(s, col("purple"), (mx + 3, my - 2), 5)
        for i in range(5):
            a = t * 1.5 + i * 1.26
            s.fill(col("white" if i % 2 else "yellow"), (cx + int(math.cos(a) * (r + 8)), cy + int(math.sin(a) * (r + 6)), 1, 1))
    elif kind == "nightcap":
        tip = int(math.sin(t * 2) * 2)
        y0 = cy - r + 1
        pts = [(cx - r + 1, y0), (cx - r // 2, y0 - 7), (cx + r // 3, y0 - 9),
               (cx + r + 7, y0 + 3 + tip), (cx + r - 1, y0 - 1)]
        pygame.draw.polygon(s, k, [(x, y - 1) for x, y in pts])
        pygame.draw.polygon(s, col("purple"), pts)
        for i in range(3):
            x = cx - r // 2 + i * (r // 2 + 1)
            pygame.draw.line(s, col("lavender"), (x, y0 - 7 + i), (x + 3, y0 - 2))
        s.fill(col("white"), (cx - r + 2, y0 - 1, 2 * r - 3, 3))
        star(s, cx + r + 7, y0 + 3 + tip, 3, "yellow")
    elif kind == "collar":
        s.fill(col(c2), (cx - r // 2, cy + r - 1, r, 3))
        pygame.draw.circle(s, col("yellow"), (cx, cy + r + 3), 2)


POPPY_FACE = {"idle": "open", "move": "open", "happy": "happy", "cheer": "happy", "hurt": "wow", "sleepy": "sleep"}


def poppy(s, cx, by, t, mood="idle", look=0):
    """Poppy, the night-shift nanny cat: lilac fur, a striped nightcap and a lantern. (cx, by) = feet.
    mood: idle | move | happy | cheer | hurt | sleepy"""
    bob = int(math.sin(t * 3) * 1)
    jump = -int(abs(math.sin(t * 9)) * 5) if mood in ("happy", "cheer") else 0
    if mood == "hurt":
        bob = int(math.sin(t * 40) * 1)
    y = by + jump
    for pass_ in range(2):          # tail: outline pass, then fur
        for i in range(8):
            a = i / 7
            tx = cx + 8 + int(a * 8)
            ty = y - 6 - int(a * 12) + int(math.sin(t * 4 + a * 3) * 2)
            if pass_ == 0:
                pygame.draw.circle(s, col("black"), (tx, ty), 3)
            else:
                pygame.draw.circle(s, col("lavender" if i < 6 else "purple"), (tx, ty), 2)
    pygame.draw.ellipse(s, col("black"), (cx - 10, y - 19 + bob, 20, 18))
    pygame.draw.ellipse(s, col("lavender"), (cx - 9, y - 18 + bob, 18, 16))
    pygame.draw.ellipse(s, col("cream"), (cx - 5, y - 14 + bob, 10, 10))
    for side in (-1, 1):
        step = int(math.sin(t * 10) * 2) * side if mood == "move" else 0
        pygame.draw.ellipse(s, col("black"), (cx + side * 6 - 4 + step, y - 4, 9, 5))
        pygame.draw.ellipse(s, col("white"), (cx + side * 6 - 3 + step, y - 3, 7, 3))
    lx, ly = cx - 13 + int(math.sin(t * 2.4) * 3), y - 9 + bob
    if mood in ("happy", "cheer"):
        lx, ly = cx - 14, y - 26 + bob
    pygame.draw.line(s, col("black"), (cx - 7, y - 14 + bob), (lx + 2, ly - 6), 3)
    pygame.draw.line(s, col("lavender"), (cx - 7, y - 14 + bob), (lx + 2, ly - 6), 1)
    lantern(s, lx, ly, t)
    face = POPPY_FACE[mood]
    if face == "open" and int(t * 10) % 37 == 0:
        face = "sleep"
    hy = y - 27 + bob
    big_cat(s, cx, hy, 10, "lavender", "purple", "mint", face, t, look, "tabby", ear=2 if math.sin(t * 7) > 0.95 else 0)
    accessory(s, "nightcap", cx, hy, 10, t)
    if mood == "hurt":
        s.fill(col("sky"), (cx + 11, hy - 6, 2, 4))
        s.fill(col("white"), (cx + 11, hy - 6, 1, 1))
    if mood == "sleepy":
        draw_z(s, cx + 12, hy - 14 - int(t * 6) % 6, "white")


def lantern(s, lx, ly, t):
    """Poppy's lantern (lx, ly = left / middle) with a soft warm glow."""
    glow = 7 + int(math.sin(t * 6) * 1)
    halo = pygame.Surface((glow * 2 + 2, glow * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(halo, col("yellow", 70), (glow + 1, glow + 1), glow)
    s.blit(halo, (lx + 2 - glow - 1, ly - glow - 1))
    s.fill(col("black"), (lx - 1, ly - 5, 7, 9))
    s.fill(col("yellow"), (lx, ly - 4, 5, 7))
    s.fill(col("white"), (lx + 1, ly - 3, 2, 3))
    s.fill(col("brown"), (lx - 1, ly - 6, 7, 2))


def wrap(text, n):
    """Greedy word wrap to lines of at most n characters."""
    lines, cur = [], ""
    for word in text.split(" "):
        if cur and len(cur) + 1 + len(word) > n:
            lines.append(cur)
            cur = word
        else:
            cur = word if not cur else cur + " " + word
    if cur:
        lines.append(cur)
    return lines


BOSS_PATTERN = {"tophat": "tux", "bow": "fluff", "mask": "mask", "phones": "tabby", "crown": "fluff", "moon": "cosmic"}


def foe(s, boss, data, cx, cy, t, mood="open", hit=False):
    """A boss (data: a BOSSES row) or a duel rival (data: a RIVALS row): head and shoulders."""
    name, coat, mark, eye = data[0], data[1], data[2], data[3]
    if boss:
        acc, r, pattern = data[4], 17, BOSS_PATTERN[data[4]]
    else:
        acc, r, pattern = "collar", 13, data[5]
    bob = int(math.sin(t * 2.5) * 1)
    if hit and int(t * 30) % 2:
        coat = "white"
    pygame.draw.ellipse(s, col("black"), (cx - r - 3, cy + r - 6 + bob, 2 * r + 6, r + 10))
    pygame.draw.ellipse(s, col(coat), (cx - r - 2, cy + r - 5 + bob, 2 * r + 4, r + 8))
    if pattern in ("tux", "fluff"):
        pygame.draw.ellipse(s, col(mark if pattern == "tux" else "white"), (cx - r // 2, cy + r - 2 + bob, r, r // 2 + 4))
    if acc == "moon":
        accessory(s, acc, cx, cy + bob, r, t)
    big_cat(s, cx, cy + bob, r, coat, mark, eye, mood, t, 0, pattern,
            muzzle="white" if coat in ("black", "darkgray", "ink", "choco") else "cream")
    if acc != "moon":
        accessory(s, acc, cx, cy + bob, r, t, "red" if boss else data[4])


# ---------------------------------------------------------------------------- music (original)
_NAP_BASS = (("D", "F#"), ("G", "B"), ("E", "G"), ("A", "C#"), ("D", "F#"), ("B", "D"), ("G", "B"), ("A", "C#"))
music.SONGS.update({
    # "Pillow Pile Polka" - the bedtime stages (D major, gentle swing)
    "kp_nap": {"bpm": 126, "gain": 0.78, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.24, "decay": 0.45, "notes":
            "D5:8 F#5:8 A5:8 F#5:8 B5:4 A5:4  G5:8 F#5:8 E5:8 F#5:8 D5:2 "
            "E5:8 G5:8 B5:8 G5:8 C#6:4 B5:4  A5:8 G5:8 F#5:8 E5:8 A4:2 "
            "D5:8 F#5:8 A5:8 D6:8 C#6:4 B5:4  B5:8 A5:8 G5:8 B5:8 A5:4 F#5:4 "
            "G5:8 F#5:8 E5:8 G5:8 F#5:8 E5:8 D5:8 C#5:8  E5:4 A4:4 D5:2"},
        {"wave": "triangle", "vol": 0.4, "gate": 0.75,
         "notes": " ".join(f"{a}2:4 {a}3:4 {b}3:4 {a}3:4" for a, b in _NAP_BASS)},
        {"wave": "drums", "vol": 1, "notes": " ".join(["K:4 H:4 S:4 H:4"] * 8)},
    ]},
    # "Pillow Fight Shuffle" - rival duels (E minor, bouncy)
    "kp_duel": {"bpm": 152, "channels": [
        {"wave": "square", "duty": 0.125, "vol": 0.24, "notes":
            "E5:8 G5:8 B5:8 E6:8 D6:8 B5:8 G5:4  A5:8 C6:8 E6:8 C6:8 B5:4 G5:4 "
            "F#5:8 A5:8 D6:8 A5:8 G5:8 F#5:8 E5:4  D#5:8 F#5:8 B5:8 F#5:8 D#6:4 B5:4 "
            "E6:8 D6:8 B5:8 G5:8 A5:8 B5:8 C6:4  D6:8 C6:8 A5:8 F#5:8 G5:4 A5:4 "
            "B5:8 G5:8 E5:8 G5:8 C6:8 A5:8 F#5:8 A5:8  B5:4 D#5:4 E5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": " ".join(
            " ".join(f"{n}:8" for n in (r + "2", r + "3") * 4) for r in ("E", "A", "D", "B", "E", "D", "C", "B"))},
        {"wave": "drums", "vol": 1, "notes": " ".join(["K:8 H:8 S:8 H:8 K:8 H:8 S:8 H:8"] * 8)},
    ]},
})
