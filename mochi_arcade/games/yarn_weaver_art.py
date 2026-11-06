"""YARN WEAVER art: KUMO the kitten (sprites), items, songs, the hidden cat pictures, rugs and hazards.

Everything is an original design for MOCHI ARCADE. The iOS port mirrors this file in
ios/MochiArcade/Games/YarnWeaverArt.swift (same drawing calls, same numbers).
"""
import math

import pygame

from mochi_arcade import music, sprites
from mochi_arcade.cute import eyes
from mochi_arcade.gfx import col, sprite

# ----------------------------------------------------------------------------- KUMO, the fluffy gray kitten
# 15x13, front view: gray fluff, darker forehead stripes, white muzzle / chest / paws, pink ears,
# and a white-tipped tail curling up on the right.
_KUMO = [
    ".k.........k...",
    "kgk.......kgk..",
    "kpgk.....kgpk..",
    "kpggkkkkkggpk..",
    "kgggdgdgdgggk..",
    "kgggggggggggk..",
    "kggkwgggkwggk..",
    "kggkkgggkkggkk.",
    "kpgggwpwgggpkwk",
    ".kgggkwkgggkkgk",
    "..kgwwwwwgk.kgk",
    "..kgwwwwwgkkgk.",
    "..kwwkkkwwkkk..",
]


def _rows(base, **rep):
    r = base[:]
    for k, v in rep.items():
        r[int(k[1:])] = v
    return r


KUMO_IDLE = _KUMO
KUMO_BLINK = _rows(_KUMO, r6="kgggggggggggk..", r7="kggkkgggkkggkk.",
                   r8="kpgggwpwgggpkkw", r9=".kgggkwkgggkkwk")
KUMO_WALK1 = _rows(_KUMO, r12="..kwwk..kkkkk..", r11="..kgwwwwwgkkgk.")
KUMO_WALK2 = _rows(_KUMO, r12="..kkkk..kwwkk..")
KUMO_HAPPY = _rows(_KUMO, r6="kgggkgggkgggk..", r7="kggkgkgkgkgkkk.", r9=".kgggkpkgggkkgk",
                   r10="kkkgwwwwwgkkkgk", r11="kwkgwwwwwgkwkk.", r12="..kkkk.kkkkk...")
KUMO_HURT = _rows(_KUMO, r0="k..k.....k..k..", r5="kggkgggggkggk..", r6="kgggkgggkgggk..",
                  r7="kggkgggggkggkk.", r9=".kgggkkkgggkkgk")
KUMO_WEAVE = _rows(_KUMO, r9=".kgggkPkgggkkgk", r10="..kgwwPwwgk.kgk", r11="..kgwwwPwgkkgk.")

# items lying on the rug (claim the spot or brush past them while weaving)
_FISH = [
    "..kkkkk...",
    ".koooookkk",
    "kowkoooook",
    "koooooookk",
    ".kyyyyyk.k",
    "..kkkkk...",
]
_NIP = [
    "....kk.",
    "..kkllk",
    ".klllmk",
    "klmllk.",
    "kmlllk.",
    ".kkkk..",
    "k......",
]
_BELL = [
    "...k...",
    "..kyk..",
    ".kyyyk.",
    "kywyyyk",
    "kyyyyyk",
    "kkkkkkk",
    "..kok..",
]
_GOLD = [
    "..kkkk..",
    ".kyoyyk.",
    "kyyoyyok",
    "kyoyyoyk",
    "koyyoyyk",
    "kyyoyyok",
    ".kyyoyk.",
    "..kkkk.k",
]
_RAINBOW = [
    "..kkkk..",
    ".krrook.",
    "kProoyyk",
    "kPPyyllk",
    "kuPPllsk",
    "kuubssbk",
    ".kubbsk.",
    "..kkkk.k",
]
_MOTH = [
    [
        "k.....k",
        ".k...k.",
        "ccvkvcc",
        "cwcvcwc",
        ".cckcc.",
        "..ckc..",
    ],
    [
        "k.....k",
        ".k...k.",
        "..vkv..",
        ".ccvcc.",
        "cwckcwc",
        ".cc.cc.",
    ],
]

YW_ART = {
    "yw_kumo": [KUMO_IDLE, KUMO_BLINK, KUMO_WALK1, KUMO_WALK2, KUMO_HAPPY, KUMO_HURT, KUMO_WEAVE],
    "yw_fish": [_FISH],
    "yw_nip": [_NIP],
    "yw_bell": [_BELL],
    "yw_gold": [_GOLD],
    "yw_rainbow": [_RAINBOW],
    "yw_moth": _MOTH,
}
sprites.ART.update(YW_ART)
K_IDLE, K_BLINK, K_WALK1, K_WALK2, K_HAPPY, K_HURT, K_WEAVE = range(7)

# ----------------------------------------------------------------------------- songs (original)
_GROOVE = "K:8 H:8 S:8 H:8 K:8 K:8 S:8 H:8"
_LILT = "K:4 H:8 H:8 S:4 H:8 K:8"

music.SONGS.update({
    # "Purl Polka" - bouncy G major, the main weaving tune
    "yw_purl": {"bpm": 138, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "G5:8 B5:8 D6:8 B5:8 C6:8 A5:8 F#5:4  G5:8 E5:8 C5:8 E5:8 D5:4 R:4 "
            "A5:8 C6:8 E6:8 C6:8 B5:8 G5:8 D5:4  F#5:8 A5:8 D6:8 C6:8 B5:4 A5:4 "
            "B5:8 B5:8 A5:8 G5:8 E5:4 G5:4  C6:8 B5:8 A5:8 G5:8 F#5:4 D5:4 "
            "E5:8 G5:8 B5:8 E6:8 D6:8 C6:8 A5:4  D6:8 C6:8 A5:8 F#5:8 G5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": music._bass(["G", "C", "A", "D", "E", "C", "A", "D"])},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, _GROOVE)},
    ]},
    # "Ball of String" - a mellow D minor stroll for the even rooms
    "yw_string": {"bpm": 124, "gain": 0.78, "channels": [
        {"wave": "square", "duty": 0.5, "vol": 0.21, "decay": 0.45, "notes":
            "D5:8 F5:8 A5:8 D6:8 C6:4 A5:4  A#5:8 A5:8 G5:8 F5:8 G5:4 E5:4 "
            "F5:8 A5:8 C6:8 F6:8 E6:4 C6:4  D6:8 C6:8 A#5:8 A5:8 G5:2 "
            "A5:8 A#5:8 C6:8 D6:8 C6:8 A#5:8 A5:4  G5:8 A5:8 A#5:8 C6:8 A#5:8 A5:8 G5:4 "
            "F5:8 G5:8 A5:8 C6:8 D6:4 F6:4  E6:8 D6:8 C#6:8 E6:8 D6:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.7, "notes": music._bass(["D", "A#", "F", "C", "A#", "G", "F", "A"], "4")},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, _LILT)},
    ]},
})

# ----------------------------------------------------------------------------- the hidden cat pictures
PW, PH = 304, 176          # picture / playfield size in pixels
SIT, LOAF, CURL, PEEK = range(4)
DARK_FUR = ("darkgray", "choco", "brown", "purple", "blue", "ink", "black", "deep")


def oval(s, c, x, y, w, h, o=2):
    """Ellipse with a black outline o pixels thick."""
    if o:
        pygame.draw.ellipse(s, col("black"), (x - o, y - o, w + 2 * o, h + 2 * o))
    pygame.draw.ellipse(s, col(c), (x, y, w, h))


def ocircle(s, c, x, y, r, o=2):
    if o:
        pygame.draw.circle(s, col("black"), (x, y), r + o)
    pygame.draw.circle(s, col(c), (x, y), r)


def opoly(s, c, pts, o=2):
    pygame.draw.polygon(s, col(c), pts)
    if o:
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            pygame.draw.line(s, col("black"), a, b, o)


def thick(s, c, pts, w=3):
    for i in range(len(pts) - 1):
        pygame.draw.line(s, col(c), pts[i], pts[i + 1], w)


def bg_pattern(s, a, b, pat, x0=0, y0=0, w=PW, h=PH):
    """Wallpaper behind the cat (also used by the rugs)."""
    s.fill(col(a), (x0, y0, w, h))
    cb = col(b)
    if pat == 0:                     # diagonal stripes
        for k in range(-h, w, 18):
            for i in range(6):
                pygame.draw.line(s, cb, (x0 + k + i, y0 + h - 1), (x0 + k + i + h - 1, y0))
    elif pat == 1:                   # polka dots
        for y in range(6, h, 16):
            for x in range(6 + (8 if (y // 16) % 2 else 0), w, 16):
                pygame.draw.circle(s, cb, (x0 + x, y0 + y), 3)
    elif pat == 2:                   # checks
        for y in range(0, h, 16):
            for x in range(0, w, 16):
                if (x // 16 + y // 16) % 2:
                    s.fill(cb, (x0 + x, y0 + y, 16, 16))
    elif pat == 3:                   # little hearts
        for y in range(8, h, 20):
            for x in range(8 + (10 if (y // 20) % 2 else 0), w, 20):
                pygame.draw.circle(s, cb, (x0 + x - 2, y0 + y), 2)
                pygame.draw.circle(s, cb, (x0 + x + 2, y0 + y), 2)
                pygame.draw.polygon(s, cb, [(x0 + x - 4, y0 + y + 1), (x0 + x + 4, y0 + y + 1), (x0 + x, y0 + y + 5)])
    elif pat == 4:                   # twinkle stars
        for y in range(8, h, 22):
            for x in range(10 + (11 if (y // 22) % 2 else 0), w, 22):
                s.fill(cb, (x0 + x - 3, y0 + y, 7, 1))
                s.fill(cb, (x0 + x, y0 + y - 3, 1, 7))
                s.fill(cb, (x0 + x - 1, y0 + y - 1, 3, 3))
    elif pat == 5:                   # tiny fish
        for y in range(10, h, 22):
            for x in range(8 + (14 if (y // 22) % 2 else 0), w, 28):
                pygame.draw.ellipse(s, cb, (x0 + x, y0 + y - 3, 10, 6))
                pygame.draw.polygon(s, cb, [(x0 + x + 9, y0 + y), (x0 + x + 14, y0 + y - 3), (x0 + x + 14, y0 + y + 3)])
    elif pat == 6:                   # waves
        for y in range(6, h, 12):
            for x in range(0, w, 2):
                yy = y + int(math.sin((x + y) * 0.25) * 2)
                s.fill(cb, (x0 + x, y0 + yy, 2, 2))
    else:                            # plaid
        for y in range(4, h, 24):
            s.fill(cb, (x0, y0 + y, w, 4))
        for x in range(4, w, 24):
            s.fill(cb, (x0 + x, y0, 4, h))


def _eye(s, x, y, c, mood):
    if mood == 2:            # closed, happy
        thick(s, "black", [(x - 7, y + 3), (x, y - 3), (x + 7, y + 3)])
        return
    if mood == 4:            # sleeping
        thick(s, "black", [(x - 7, y - 1), (x, y + 3), (x + 7, y - 1)])
        return
    oval(s, c, x - 8, y - 9, 16, 18, 2)
    if mood == 3:            # wow: huge sparkly pupils
        pygame.draw.ellipse(s, col("black"), (x - 6, y - 7, 12, 15))
        pygame.draw.circle(s, col("white"), (x - 2, y - 3), 3)
        pygame.draw.circle(s, col("white"), (x + 3, y + 3), 2)
        return
    pygame.draw.ellipse(s, col("black"), (x - 4, y - 7, 8, 14))
    pygame.draw.circle(s, col("white"), (x - 3, y - 4), 3)
    s.fill(col("white"), (x + 2, y + 4, 2, 2))


def _face(s, sp, hx, hy, eye_dy=2, nose_dy=14, gap=17, mood=None):
    """Eyes, nose, mouth, whiskers and blush around the head centre."""
    mood = sp["mood"] if mood is None else mood
    ey = hy + eye_dy
    if mood == 1:            # wink
        _eye(s, hx - gap, ey, sp["eye"], 0)
        _eye(s, hx + gap, ey, sp["eye"], 2)
    else:
        _eye(s, hx - gap, ey, sp["eye"], mood)
        _eye(s, hx + gap, ey, sp["eye"], mood)
    ny = hy + nose_dy
    pygame.draw.ellipse(s, col("pink"), (hx - gap - 15, ny - 1, 10, 5))
    pygame.draw.ellipse(s, col("pink"), (hx + gap + 5, ny - 1, 10, 5))
    wc = "white" if sp["fur"] in DARK_FUR else "black"
    for k in range(3):
        pygame.draw.line(s, col(wc), (hx - 14, ny + 2 + k * 3), (hx - 44, ny - 4 + k * 6), 1)
        pygame.draw.line(s, col(wc), (hx + 14, ny + 2 + k * 3), (hx + 44, ny - 4 + k * 6), 1)
    opoly(s, "pink", [(hx - 5, ny - 2), (hx + 5, ny - 2), (hx, ny + 3)], 1)
    thick(s, "black", [(hx, ny + 3), (hx, ny + 6)], 2)
    thick(s, "black", [(hx - 8, ny + 7), (hx - 4, ny + 9), (hx, ny + 6), (hx + 4, ny + 9), (hx + 8, ny + 7)], 2)
    if mood == 3:
        pygame.draw.ellipse(s, col("black"), (hx - 3, ny + 8, 7, 6))
        pygame.draw.ellipse(s, col("hotpink"), (hx - 2, ny + 10, 5, 3))


def _ears(s, sp, hx, top, spread=34, inner="pink"):
    ec = sp["fur2"] if sp["mark"] == 4 else sp["fur"]
    for d in (-1, 1):
        opoly(s, ec, [(hx + d * (spread + 6), top + 20), (hx + d * spread, top - 18), (hx + d * 10, top + 6)])
        pygame.draw.polygon(s, col(inner), [(hx + d * (spread + 1), top + 13), (hx + d * (spread - 2), top - 8),
                                            (hx + d * 16, top + 6)])


def _head_marks(s, sp, hx, hy, hw, hh):
    m, f2 = sp["mark"], sp["fur2"]
    if m == 1:               # tabby
        for dx in (-9, 0, 9):
            thick(s, f2, [(hx + dx - (dx // 9), hy - hh + 6), (hx + dx, hy - hh + 18)], 4)
        for d in (-1, 1):
            for k in range(2):
                thick(s, f2, [(hx + d * (hw - 2), hy + 2 + k * 7), (hx + d * (hw - 12), hy + 4 + k * 7)], 3)
    elif m == 2:             # tuxedo muzzle
        pygame.draw.ellipse(s, col("white"), (hx - 17, hy + 6, 34, hh - 4))
    elif m == 3:             # calico patches
        pygame.draw.circle(s, col(f2), (hx - hw + 20, hy - hh + 20), 11)
        pygame.draw.circle(s, col("darkgray"), (hx + hw - 18, hy - hh + 18), 9)
    elif m == 4:             # colour points: darker mask
        pygame.draw.ellipse(s, col(f2), (hx - 19, hy - 2, 38, 30))
    elif m == 5:             # spots
        pygame.draw.circle(s, col(f2), (hx + 20, hy - hh + 16), 5)
        pygame.draw.circle(s, col(f2), (hx - 24, hy - hh + 22), 4)


def _body_marks(s, sp, bx, by, brx, bry):
    m, f2 = sp["mark"], sp["fur2"]
    if m == 1:
        for k in (-1, 0, 1):
            y = by + k * 12
            for d in (-1, 1):
                thick(s, f2, [(bx + d * (brx - 3), y), (bx + d * (brx - 15), y + 3)], 4)
    elif m == 2:
        pygame.draw.ellipse(s, col("white"), (bx - brx // 2, by - bry + 8, brx, bry + 8))
    elif m == 3:
        r = min(brx, bry) * 35 // 100
        pygame.draw.circle(s, col(f2), (bx + brx * 35 // 100, by + bry * 15 // 100), r)
        pygame.draw.circle(s, col("darkgray"), (bx - brx * 40 // 100, by - bry * 25 // 100), r * 3 // 4)
    elif m == 5:
        for fx, fy, r in ((-40, -30, 6), (45, 10, 5), (-10, 45, 5), (20, -40, 4)):
            pygame.draw.circle(s, col(f2), (bx + brx * fx // 100, by + bry * fy // 100), r)


def _paw_col(sp):
    return "white" if sp["mark"] == 2 else (sp["fur2"] if sp["mark"] == 4 else sp["fur"])


def _tail(s, sp, pts0, r=7):
    c = sp["fur2"] if sp["mark"] in (1, 4) else sp["fur"]
    pts = [pts0[0]]
    for i in range(1, len(pts0)):           # a smooth tube: circles every couple of pixels
        (ax, ay), (bx, by) = pts0[i - 1], pts0[i]
        k = max(1, int(math.hypot(bx - ax, by - ay) / 2))
        for j in range(1, k + 1):
            pts.append((ax + (bx - ax) * j // k, ay + (by - ay) * j // k))
    for x, y in pts:
        pygame.draw.circle(s, col("black"), (x, y), r + 2)
    for x, y in pts:
        pygame.draw.circle(s, col(c), (x, y), r)
    if sp["mark"] in (0, 2, 5):      # a pale tip
        x, y = pts[-1]
        pygame.draw.circle(s, col("white" if sp["fur"] != "white" else "cream"), (x, y), r - 1)


def _accessory(s, sp, hx, hy, hw, hh, neck):
    a, c = sp["acc"], sp["accc"]
    top = hy - hh
    if a == 1:               # bow
        bx, by = hx + hw - 16, top + 8
        opoly(s, c, [(bx - 13, by - 7), (bx - 13, by + 7), (bx, by)], 2)
        opoly(s, c, [(bx + 13, by - 7), (bx + 13, by + 7), (bx, by)], 2)
        ocircle(s, c, bx, by, 4, 2)
    elif a == 2 and neck:    # bell collar
        thick(s, c, [(hx - 26, neck), (hx + 26, neck)], 6)
        ocircle(s, "yellow", hx, neck + 6, 6, 2)
        s.fill(col("black"), (hx - 3, neck + 7, 7, 1))
        s.fill(col("white"), (hx - 3, neck + 3, 2, 2))
    elif a == 3:             # flower
        fx, fy = hx - hw + 18, top + 10
        for k in range(5):
            ang = k * math.tau / 5
            ocircle(s, c, fx + int(math.cos(ang) * 6), fy + int(math.sin(ang) * 6), 4, 1)
        ocircle(s, "yellow", fx, fy, 4, 1)
    elif a == 4:             # party hat
        pts = [(hx - 15, top + 6), (hx + 15, top + 6), (hx + 4, top - 30)]
        opoly(s, c, pts, 2)
        for k in range(1, 3):
            y = top + 6 - k * 11
            w = 15 - k * 5
            thick(s, "white", [(hx - w + k * 4 - 2, y), (hx + w + k * 2 - 2, y)], 2)
        ocircle(s, "yellow", hx + 4, top - 32, 5, 2)
    elif a == 5 and neck:    # scarf
        pygame.draw.rect(s, col("black"), (hx - 32, neck - 7, 64, 14), border_radius=5)
        pygame.draw.rect(s, col(c), (hx - 30, neck - 5, 60, 10), border_radius=4)
        pygame.draw.rect(s, col("black"), (hx + 6, neck - 2, 16, 30), border_radius=4)
        pygame.draw.rect(s, col(c), (hx + 8, neck, 12, 26), border_radius=3)
        for k in range(3):
            s.fill(col("white"), (hx + 8, neck + 6 + k * 7, 12, 2))
    elif a == 6:             # crown
        pts = [(hx - 18, top + 8), (hx - 18, top - 8), (hx - 9, top), (hx, top - 13), (hx + 9, top),
               (hx + 18, top - 8), (hx + 18, top + 8)]
        opoly(s, "yellow", pts, 2)
        for dx, c2 in ((-9, "red"), (0, "sky"), (9, "lime")):
            pygame.draw.circle(s, col(c2), (hx + dx, top + 3), 2)
    elif a == 7:             # round glasses
        for d in (-1, 1):
            pygame.draw.circle(s, col("black"), (hx + d * 17, hy + 2), 12, 2)
        thick(s, "black", [(hx - 6, hy), (hx + 6, hy)], 2)


def _prop(s, sp, px, py):
    p, c = sp["prop"], sp["propc"]
    if p == 1:               # yarn ball with a loose strand
        thick(s, c, [(px + 10, py + 10), (px + 26, py + 18), (px + 40, py + 14)], 2)
        ocircle(s, c, px, py, 14, 2)
        for k in range(-2, 3):
            pygame.draw.line(s, col("white"), (px - 10, py + k * 5 - 3), (px + 9, py + k * 5 + 3), 1)
        pygame.draw.line(s, col("black"), (px - 6, py - 11), (px + 8, py + 10), 1)
    elif p == 2:             # fish
        opoly(s, c, [(px + 12, py), (px + 22, py - 8), (px + 22, py + 8)], 2)
        oval(s, c, px - 16, py - 7, 30, 14, 2)
        pygame.draw.circle(s, col("white"), (px - 8, py - 2), 3)
        s.fill(col("black"), (px - 8, py - 2, 2, 2))
        thick(s, "white", [(px - 2, py + 3), (px + 8, py + 3)], 1)
    elif p == 3:             # warm mug
        pygame.draw.circle(s, col("black"), (px + 12, py + 2), 8, 4)
        pygame.draw.circle(s, col(c), (px + 12, py + 2), 7, 2)
        pygame.draw.rect(s, col("black"), (px - 13, py - 13, 26, 28), border_radius=4)
        pygame.draw.rect(s, col(c), (px - 11, py - 11, 22, 24), border_radius=3)
        s.fill(col("white"), (px - 8, py - 8, 3, 14))
        for k in (-5, 3):
            thick(s, "white", [(px + k, py - 16), (px + k + 3, py - 21), (px + k, py - 26), (px + k + 3, py - 31)], 2)
    elif p == 4:             # moon and stars (top corner)
        pygame.draw.circle(s, col("black"), (34, 32), 19)
        pygame.draw.circle(s, col("yellow"), (34, 32), 17)
        pygame.draw.circle(s, col(sp["bg"]), (42, 26), 15)
        for x, y in ((70, 20), (90, 46), (58, 58), (PW - 40, 26), (PW - 70, 50)):
            s.fill(col("yellow"), (x - 4, y, 9, 1))
            s.fill(col("yellow"), (x, y - 4, 1, 9))
            s.fill(col("white"), (x - 1, y - 1, 3, 3))
    elif p == 5:             # potted flower
        thick(s, "lime", [(px, py - 6), (px - 2, py - 30)], 3)
        thick(s, "lime", [(px, py - 14), (px + 10, py - 22)], 3)
        for k in range(6):
            ang = k * math.tau / 6
            ocircle(s, c, px - 2 + int(math.cos(ang) * 7), py - 32 + int(math.sin(ang) * 7), 5, 1)
        ocircle(s, "yellow", px - 2, py - 32, 5, 1)
        opoly(s, "orange", [(px - 14, py - 8), (px + 14, py - 8), (px + 10, py + 14), (px - 10, py + 14)], 2)
        s.fill(col("brown"), (px - 13, py - 7, 26, 4))
    elif p == 6:             # cupcake
        opoly(s, "sky", [(px - 13, py - 2), (px + 13, py - 2), (px + 9, py + 16), (px - 9, py + 16)], 2)
        for k in (-6, 0, 6):
            pygame.draw.line(s, col("blue"), (px + k, py), (px + k * 3 // 4, py + 15), 1)
        for dx, dy in ((-8, -4), (8, -4), (0, -8), (-4, -12), (4, -12)):
            pygame.draw.circle(s, col("black"), (px + dx, py + dy), 8)
        for dx, dy in ((-8, -4), (8, -4), (0, -8), (-4, -12), (4, -12)):
            pygame.draw.circle(s, col(c), (px + dx, py + dy), 6)
        ocircle(s, "red", px, py - 21, 4, 2)
        s.fill(col("white"), (px - 2, py - 23, 2, 2))
    elif p == 7:             # stack of books
        for k, bc in enumerate((c, "teal", "orange")):
            y = py + 10 - k * 11
            x = px - 18 + (k % 2) * 4
            pygame.draw.rect(s, col("black"), (x - 2, y - 2, 36, 13), border_radius=2)
            pygame.draw.rect(s, col(bc), (x, y, 32, 9), border_radius=2)
            s.fill(col("cream"), (x + 3, y + 3, 26, 3))


def draw_picture(s, sp, golden=False):
    """Paint the hidden picture described by the stage's picture spec onto s (PW x PH)."""
    sp = dict(sp)
    if golden:
        sp.update(fur="yellow", fur2="orange", mark=5, eye="sky", acc=6)
    bg_pattern(s, sp["bg"], sp["bg2"], sp["pat"])
    cx = PW // 2 + sp["x"]
    pose = sp["pose"]
    if sp["prop"] == 4:
        _prop(s, sp, 0, 0)
    side_x = cx - 96 if sp["x"] >= 0 else cx + 96
    if pose != PEEK:         # a comfy cushion
        oval(s, sp["cush"], cx - 74, 146, 148, 28, 2)
        s.fill(col("white"), (cx - 50, 152, 30, 2))
    fur, paw = sp["fur"], _paw_col(sp)
    if pose == SIT:
        hx, hy, hw, hh = cx, 66, 44, 33
        _tail(s, sp, [(cx + 38, 152), (cx + 50, 146), (cx + 58, 136), (cx + 62, 124), (cx + 62, 112), (cx + 58, 101)])
        oval(s, fur, cx - 44, 126, 26, 34)
        oval(s, fur, cx + 18, 126, 26, 34)
        oval(s, fur, cx - 34, 82, 68, 80)
        _body_marks(s, sp, cx, 122, 34, 40)
        oval(s, paw, cx - 22, 152, 18, 12)
        oval(s, paw, cx + 4, 152, 18, 12)
        _ears(s, sp, hx, hy - hh)
        oval(s, fur, hx - hw, hy - hh, hw * 2, hh * 2)
        _head_marks(s, sp, hx, hy, hw, hh)
        _face(s, sp, hx, hy)
        _accessory(s, sp, hx, hy, hw, hh, hy + hh - 2)
    elif pose == LOAF:
        hx, hy, hw, hh = cx, 92, 40, 30
        _tail(s, sp, [(cx + 62, 140), (cx + 60, 152), (cx + 50, 160), (cx + 38, 164), (cx + 26, 165)], 6)
        oval(s, fur, cx - 62, 106, 124, 58)
        _body_marks(s, sp, cx, 135, 62, 29)
        oval(s, paw, cx - 26, 158, 18, 9)
        oval(s, paw, cx + 8, 158, 18, 9)
        _ears(s, sp, hx, hy - hh, 30)
        oval(s, fur, hx - hw, hy - hh, hw * 2, hh * 2)
        _head_marks(s, sp, hx, hy, hw, hh)
        _face(s, sp, hx, hy)
        _accessory(s, sp, hx, hy, hw, hh, hy + hh - 2)
    elif pose == CURL:
        bx, by, br = cx + 10, 112, 50
        ocircle(s, fur, bx, by, br, 2)
        if sp["mark"] != 2:
            _body_marks(s, sp, bx, by, br, br)
        _tail(s, sp, [(bx + int(math.cos(math.radians(a)) * 46), by + int(math.sin(math.radians(a)) * 46))
                      for a in range(-30, 110, 16)], 7)
        hx, hy, hw, hh = cx - 22, 122, 36, 28
        _ears(s, sp, hx, hy - hh, 28)
        oval(s, fur, hx - hw, hy - hh, hw * 2, hh * 2)
        _head_marks(s, sp, hx, hy, hw, hh)
        _face(s, sp, hx, hy, 2, 13, 15, 4)
        oval(s, paw, hx + 18, hy + 18, 18, 10)
        _accessory(s, sp, hx, hy, hw, hh, 0)
        for k, (zx, zy) in enumerate(((hx + 34, hy - 46), (hx + 46, hy - 60), (hx + 60, hy - 72))):
            thick(s, "white", [(zx, zy), (zx + 4 + k, zy), (zx, zy + 4 + k), (zx + 4 + k, zy + 4 + k)], 2)
    else:                    # PEEK: popping out of a cardboard box
        hx, hy, hw, hh = cx, 86, 42, 31
        _tail(s, sp, [(cx + 64, 150), (cx + 70, 138), (cx + 74, 126), (cx + 76, 114)], 6)
        _ears(s, sp, hx, hy - hh)
        oval(s, fur, hx - hw, hy - hh, hw * 2, hh * 2)
        _head_marks(s, sp, hx, hy, hw, hh)
        _face(s, sp, hx, hy)
        _accessory(s, sp, hx, hy, hw, hh, 0)
        opoly(s, "peach", [(cx - 62, 112), (cx - 84, 98), (cx - 70, 92), (cx - 46, 112)], 2)
        opoly(s, "peach", [(cx + 62, 112), (cx + 84, 98), (cx + 70, 92), (cx + 46, 112)], 2)
        pygame.draw.rect(s, col("black"), (cx - 64, 110, 128, 70))
        pygame.draw.rect(s, col("orange"), (cx - 62, 112, 124, 70))
        s.fill(col("brown"), (cx - 62, 112, 124, 3))
        s.fill(col("peach"), (cx - 8, 122, 16, 30))
        oval(s, paw, cx - 36, 104, 20, 12)
        oval(s, paw, cx + 16, 104, 20, 12)
    if sp["prop"] not in (0, 4):
        _prop(s, sp, max(22, min(PW - 30, side_x)), 140)
    if golden:
        for x, y in ((40, 40), (PW - 40, 60), (70, 140), (PW - 60, 150), (PW // 2 + 70, 30)):
            s.fill(col("white"), (x - 5, y, 11, 1))
            s.fill(col("white"), (x, y - 5, 1, 11))
            s.fill(col("yellow"), (x - 1, y - 1, 3, 3))


# ----------------------------------------------------------------------------- rugs and furniture
def make_rug(s, theme):
    """The unclaimed rug: a woven pattern in the room's colours with a soft knit texture."""
    bg_pattern(s, theme[1], theme[2], theme[3])
    dark = col("black")
    for y in range(1, PH, 4):        # knit rows
        for x in range((y // 4) % 2 * 2, PW, 4):
            s.fill(dark, (x, y, 1, 1))


def draw_furniture(s, sh):
    """Pre-claimed furniture on the rug: ["r", x, y, w, h, colour] or ["c", cx, cy, r, colour] (cells)."""
    c = sh[-1]
    if sh[0] == "r":
        x, y, w, h = sh[1] * 2, sh[2] * 2, sh[3] * 2, sh[4] * 2
        pygame.draw.rect(s, col("black"), (x, y, w, h), border_radius=5)
        pygame.draw.rect(s, col(c), (x + 2, y + 2, w - 4, h - 4), border_radius=4)
        s.fill(col("white"), (x + 5, y + 4, max(2, w // 3), 2))
        if w >= 16 and h >= 16:          # tufted buttons
            for bx in range(x + 8, x + w - 6, 12):
                for by in range(y + 8, y + h - 6, 12):
                    s.fill(col("black"), (bx, by, 2, 2))
    else:                                # a round pouf: stitched ring, button, piping
        x, y, r = sh[1] * 2 + 1, sh[2] * 2 + 1, sh[3] * 2
        pygame.draw.circle(s, col("black"), (x, y), r + 1)
        pygame.draw.circle(s, col(c), (x, y), r - 1)
        pygame.draw.circle(s, col("black"), (x, y), r - 5, 1)
        for k in range(8):
            a = k * math.tau / 8
            s.fill(col("black"), (x + int(math.cos(a) * (r - 3)), y + int(math.sin(a) * (r - 3)), 1, 1))
            pygame.draw.line(s, col("black"), (x, y), (x + int(math.cos(a) * (r - 6)), y + int(math.sin(a) * (r - 6))), 1)
        pygame.draw.circle(s, col("black"), (x, y), 3)
        pygame.draw.circle(s, col("cream"), (x, y), 2)
        s.fill(col("white"), (x - r // 2, y - r // 2 - 2, 4, 2))


# ----------------------------------------------------------------------------- hazards and friends
def draw_fluff(s, x, y, r, t, angry=True, zap=0.0, color="gray"):
    """The crackly static-fluff ball: a spiky puff with sparks."""
    x, y = int(x), int(y)
    spin = t * 3
    n = 10 if r >= 6 else 7
    for k in range(n):
        a = spin + k * math.tau / n
        rr = r + 2 + (k % 2)
        pygame.draw.circle(s, col("black"), (x + int(math.cos(a) * rr * 0.75), y + int(math.sin(a) * rr * 0.75)), r // 2 + 2)
    for k in range(n):
        a = spin + k * math.tau / n
        rr = r + 2 + (k % 2)
        c = "yellow" if zap > 0 and int(t * 20) % 2 else ("white" if k % 3 == 0 else color)
        pygame.draw.circle(s, col(c), (x + int(math.cos(a) * rr * 0.75), y + int(math.sin(a) * rr * 0.75)), r // 2 + 1)
    pygame.draw.circle(s, col("lavender" if color == "gray" else color), (x, y), r)
    if r >= 5:
        eyes(s, x, y - 1, max(2, r // 3), 0, "angry" if angry else "happy", blink=int(t * 3) % 9 == 0)
    else:
        s.fill(col("black"), (x - 2, y - 1, 1, 2))
        s.fill(col("black"), (x + 1, y - 1, 1, 2))
    for k in range(2):                       # crackles
        a = t * 7 + k * 3.1 + x * 0.1
        if int(t * 12 + k) % 3 == 0:
            ax, ay = x + int(math.cos(a) * (r + 4)), y + int(math.sin(a) * (r + 4))
            pygame.draw.line(s, col("yellow"), (ax, ay), (ax + int(math.cos(a + 1.3) * 4), ay + int(math.sin(a + 1.3) * 4)), 1)


def draw_zip(s, x, y, t, hunter=False):
    """A zip: a tiny static spark that runs along the yarn edges."""
    x, y = int(x), int(y)
    c1, c2 = ("red", "orange") if hunter else ("yellow", "white")
    ph = int(t * 16) % 2
    pygame.draw.circle(s, col("black"), (x, y), 4)
    for k in range(4):
        a = k * math.pi / 2 + (math.pi / 4 if ph else 0)
        pygame.draw.line(s, col(c1), (x, y), (x + int(math.cos(a) * 5), y + int(math.sin(a) * 5)), 1)
    pygame.draw.circle(s, col(c1), (x, y), 3)
    s.fill(col(c2), (x - 1, y - 1, 2, 2))
    s.fill(col("black"), (x - 2, y, 1, 1))
    s.fill(col("black"), (x + 1, y, 1, 1))


def draw_moth(s, x, y, t):
    s.blit(sprite("yw_moth", int(t * 10) % 2), (int(x) - 3, int(y) - 3))


def draw_nose(s, x, y, t, up):
    """The dog's nose poking up through the rug. up: 0..1 how far it is out."""
    x, y = int(x), int(y)
    r = max(2, int(11 * up))
    pygame.draw.ellipse(s, col("black"), (x - r - 6, y - r // 2 - 3, (r + 6) * 2, r + 8))
    pygame.draw.ellipse(s, col("brown"), (x - r - 4, y - r // 2 - 1, (r + 4) * 2, r + 4))
    pygame.draw.ellipse(s, col("black"), (x - r, y - r, r * 2, r * 16 // 10))
    pygame.draw.ellipse(s, col("choco"), (x - r + 2, y - r + 2, r * 2 - 4, r * 16 // 10 - 4))
    if r > 5:
        s.fill(col("white"), (x - r // 2, y - r + 4, 3, 2))
        pygame.draw.ellipse(s, col("black"), (x - r // 2 - 1, y - 1, 4, 4))
        pygame.draw.ellipse(s, col("black"), (x + r // 2 - 3, y - 1, 4, 4))
    if up > 0.9 and int(t * 6) % 2:
        for d in (-1, 1):
            s.fill(col("white"), (x + d * (r + 6), y - r, 1, 3))


def draw_pom(s, x, y, r, t, c):
    """Bonus pom-pom: a harmless fuzzy ball with a smile."""
    x, y = int(x), int(y)
    for k in range(12):
        a = t * 2 + k * math.tau / 12
        pygame.draw.circle(s, col("black"), (x + int(math.cos(a) * (r - 1)), y + int(math.sin(a) * (r - 1))), 3)
    for k in range(12):
        a = t * 2 + k * math.tau / 12
        pygame.draw.circle(s, col(c), (x + int(math.cos(a) * (r - 1)), y + int(math.sin(a) * (r - 1))), 2)
    pygame.draw.circle(s, col(c), (x, y), r)
    s.fill(col("white"), (x - r // 2, y - r // 2, 2, 2))
    eyes(s, x, y - 1, 2, 0, "happy", blink=int(t * 2 + x) % 7 == 0)
    s.fill(col("pink"), (x - 4, y + 1, 1, 1))
    s.fill(col("pink"), (x + 4, y + 1, 1, 1))


def draw_knot(s, x, y, t):
    """A prickly tangle of old yarn: weaving through it snaps the line."""
    x, y = int(x), int(y)
    pygame.draw.circle(s, col("white"), (x, y), 8)
    pygame.draw.circle(s, col("black"), (x, y), 7)
    for k in range(6):
        a = k * 1.05 + t * 0.6
        pygame.draw.line(s, col("hotpink" if k % 2 else "yellow"), (x + int(math.cos(a) * 6), y + int(math.sin(a) * 6)),
                         (x - int(math.cos(a) * 6), y - int(math.sin(a) * 4)), 2)
    pygame.draw.line(s, col("black"), (x - 2, y - 2), (x + 2, y + 2), 1)
    pygame.draw.line(s, col("black"), (x + 2, y - 2), (x - 2, y + 2), 1)


ITEM_SPRITE = {"fish": "yw_fish", "nip": "yw_nip", "bell": "yw_bell", "heart": "heart", "gold": "yw_gold",
               "rainbow": "yw_rainbow"}


def draw_item(s, kind, x, y, t, life=9.0):
    """Treats lying on the rug. kind: fish | nip | bell | heart | gold | rainbow"""
    if life < 2.5 and int(t * 10) % 2:
        return
    img = sprite(ITEM_SPRITE[kind])
    bob = int(math.sin(t * 4 + x) * 1.5)
    s.fill(col("black"), (int(x) - 3, int(y) + 4, 7, 1))
    s.blit(img, (int(x) - img.get_width() // 2, int(y) - img.get_height() // 2 - 1 + bob))
    if kind in ("gold", "rainbow") and int(t * 8) % 3 == 0:
        s.fill(col("white"), (int(x) + 4, int(y) - 6, 1, 1))
