"""ALLEY HOP art: Sushi the calico cat, the kittens, traffic, canal floaters, laundry, boxes and lane backdrops.
All original designs for MOCHI ARCADE. Mirrored in ios/MochiArcade/Games/AlleyHopArt.swift."""
import math

import pygame

from mochi_arcade import sprites
from mochi_arcade.gfx import col, draw_text, sprite

TOP, CELL = 12, 16

# Sushi: white calico with an orange left ear / patch, a dark right ear / patch, mint eyes and a red neckerchief
_FRONT = [
    "................",
    "..kk........kk..",
    ".kook......khhk.",
    ".kopok....khphk.",
    ".kookkkkkkkkhhk.",
    "koooowwwwwwhhhhk",
    "kooowwwwwwwwhhhk",
    "koowmkwwwwmkwhhk",
    "kowwkkwwwwkkwwhk",
    "kpwwwwwppwwwwwpk",
    ".kwwwwwkkwwwwwk.",
    "..kkrrrrrrrrkk..",
    ".kwwkrrryrrkhhk.",
    ".kwwwkrrrkwhhhk.",
    ".kwwwwwkwwwhhhk.",
    "..kkkkk..kkkkk..",
]


def _eyes(rows, r7, r8):
    out = rows[:]
    out[7], out[8] = r7, r8
    return out


_BLINK = _eyes(_FRONT, "koowwwwwwwwwwhhk", "kowwkkwwwwkkwwhk")
_HAPPY = _eyes(_FRONT, "koowkwwwwwwkwhhk", "kowkwkwwwwkwkwhk")
_HURT = _eyes(_FRONT, "koowkwkwwwkwkhhk", "kowwwkwwwwwkwwhk")
_HURT[10] = ".kwwwwwkkwwwwwk."
_BACK = [
    "................",
    "..kk........kk..",
    ".kook......khhk.",
    ".koook....khhhk.",
    ".kookkkkkkkkhhk.",
    "koooowwwwwwhhhhk",
    "kooooowwwwwhhhhk",
    "koooowwwwwwwhhhk",
    "kooowwwwwwwwwhhk",
    ".kowwwwwwwwwwwk.",
    "..krrrrrrrrrrk..",
    ".kwwwwrrwwwwwhk.",
    ".kwwwwwwwwwhhhk.",
    ".kooowwwwwwhhhk.",
    "..kkooowwhhhkk..",
    "....kkkkkkkk....",
]
_SIDE = [
    "................",
    "..........k.k...",
    ".........kokhk..",
    ".........koohhk.",
    "........kooohhhk",
    "........kowwwkmk",
    "........kwwwwwpk",
    "..kkkkkkkwwwwwk.",
    ".kwwwwwhhkrrrkk.",
    ".kwwwwhhhhkryk..",
    ".kowwwwhhwwwwk..",
    ".koowwwwwwwwwk..",
    "..kkkkkkkkkkk...",
    "..kwk..kwk.kwk..",
    "..kwk..kwk.kwk..",
    "..kk...kk..kk...",
]
_STEP = _SIDE[:13] + [".kwk...kwk..kwk.", ".kwk...kwk..kwk.", ".kk....kk...kk.."]

# kittens (10x9): 'o' is the coat colour, remapped per kitten
_KIT = [
    ".k......k.",
    "kok....kok",
    "koookkoook",
    "kooooooook",
    "kokooookok",
    "kowwppwwok",
    ".kwwwwwwk.",
    ".koowwook.",
    ".kkkkkkkk.",
]
_KIT_BLINK = _KIT[:4] + ["kokkookkok"] + _KIT[5:]
_KIT_WOW = _KIT[:3] + ["kokooookok"] + _KIT[4:]
COATS = ["o", "g", "d", "c", "w", "e"]

AH_ART = {
    "ah_sushi": [_FRONT, _BLINK, _BACK, _SIDE, _STEP, _HAPPY, _HURT],
    "ah_kit": [_KIT, _KIT_BLINK, _KIT_WOW],
    "ah_fish": [[
        "...kk.....",
        "..kssk..k.",
        ".kssssk.ks",
        "kswkssskss",
        "kssssssks.",
        ".kssssk.ks",
        "..kssk..k.",
        "...kk.....",
    ]],
    "ah_goldfish": [[
        "...kk.....",
        "..kyyk..k.",
        ".kyyyyk.ky",
        "kywkyyykyy",
        "kyyyyyyky.",
        ".kyyyyk.ky",
        "..kyyk..k.",
        "...kk.....",
    ]],
    "ah_yarn": [[
        "..kkkk..",
        ".kPpPpk.",
        "kpPpPpPk",
        "kPpPpPpk",
        "kpPpPpPk",
        ".kPpPpkk",
        "..kkkk.k",
    ]],
    "ah_clock": [[
        ".kk..kk.",
        "kyykkyyk",
        ".kwwwwk.",
        "kwwkwwwk",
        "kwwkkkwk",
        "kwwwwwwk",
        ".kwwwwk.",
        "..kkkk..",
    ]],
    "ah_nip": [[
        "....kk..",
        "...klk..",
        "..kllk..",
        ".kllmlk.",
        "kllmllk.",
        "klmllk..",
        ".kkkk...",
        "..k.....",
    ]],
    "ah_bell": [[
        "...kk...",
        "..kyyk..",
        ".kyyyyk.",
        ".kywyyk.",
        "kyyyyyyk",
        "kkkkkkkk",
        "...kk...",
    ]],
    "ah_boxitem": [[
        "k.kkkk.k",
        "kkhnnhkk",
        "knnnnnnk",
        "knnhhnnk",
        "knnnnnnk",
        "kkkkkkkk",
    ]],
}
sprites.ART.update(AH_ART)

KIT_SIZE = (10, 9)
SHEET_COLORS = ("white", "pink", "sky", "yellow", "mint", "lavender", "peach")


# ----------------------------------------------------------------------------- heroes
def draw_tail(s, x, y, t, face, wag=1.0):
    """Sushi's ringed tail (white with an orange band and a dark tip), drawn behind the body."""
    sway = math.sin(t * 5) * 2 * wag
    if face in ("left", "right"):
        d = -1 if face == "right" else 1
        bx, by = x + 8 + d * 7, y + 9
        for i in range(5):
            px = bx + d * (i // 2)
            py = by - i - int(sway * i / 4)
            c = "white" if i < 2 else "orange" if i < 4 else "choco"
            s.fill(col("black"), (px - 1, py, 3, 2))
            s.fill(col(c), (px, py, 1, 1))
    else:
        bx, by = x + 12, y + 13
        for i in range(5):
            px = bx + i // 2 + int(sway * i / 5)
            py = by - i
            c = "white" if i < 2 else "orange" if i < 4 else "choco"
            s.fill(col("black"), (px - 1, py - 1, 3, 3))
            s.fill(col(c), (px, py, 1, 1))


def draw_sushi(s, x, y, t, face="up", mood="", hop=0.0, flash=False):
    """Sushi with her top-left at (x, y). face: up/down/left/right. mood: '' | happy | hurt."""
    if flash and int(t * 20) % 2:
        return
    lift = int(math.sin(math.pi * hop) * 5) if hop > 0 else 0
    if hop > 0:
        pygame.draw.ellipse(s, col("black"), (x + 3, y + 13, 10, 3))
    y -= lift
    if mood == "happy":
        fr = 5
    elif mood == "hurt":
        fr = 6
    elif face == "up":
        fr = 2
    elif face in ("left", "right"):
        fr = 4 if 0 < hop < 0.6 else 3
    else:
        fr = 1 if int(t * 1.3) % 6 == 0 else 0
    if mood == "" and face != "down":
        draw_tail(s, x, y, t, face, 2.0 if hop > 0 else 1.0)
    s.blit(sprite("ah_sushi", fr, flip=face == "left"), (x, y))


def draw_kitten(s, cx, by, coat, t, mood="", hop=0.0, seed=0, flash=False):
    """A kitten centred at cx with its feet on by. mood: '' | wow | happy | sleepy"""
    if flash and int(t * 20) % 2:
        return
    lift = int(math.sin(math.pi * hop) * 4) if hop > 0 else 0
    if mood == "happy":
        lift = max(lift, int(abs(math.sin(t * 8 + seed)) * 2))
    x, y = int(cx) - 5, int(by) - 9 - lift
    if hop > 0:
        s.fill(col("black"), (int(cx) - 3, int(by) - 1, 7, 1))
    fr = 2 if mood == "wow" else 1 if mood == "sleepy" or (int(t * 1.1 + seed * 0.37) % 5 == 0) else 0
    s.blit(sprite("ah_kit", fr, remap={"o": COATS[coat % 6]}), (x, y))


# ----------------------------------------------------------------------------- traffic
def draw_bike(s, X, y0, d, t, tint="sky"):
    for wx in (X + 3, X + 12):
        pygame.draw.circle(s, col("black"), (wx, y0 + 12), 3)
        pygame.draw.circle(s, col("gray"), (wx, y0 + 12), 2, 1)
    pygame.draw.line(s, col(tint), (X + 3, y0 + 12), (X + 7, y0 + 8))
    pygame.draw.line(s, col(tint), (X + 7, y0 + 8), (X + 12, y0 + 12))
    pygame.draw.line(s, col(tint), (X + 7, y0 + 8), (X + 9, y0 + 12))
    hx = X + 13 if d > 0 else X + 2
    s.fill(col("gray"), (hx - 1, y0 + 6, 3, 1))
    # the rider: a pup in a helmet, leaning forward
    s.fill(col("orange"), (X + 6, y0 + 5, 4, 4))
    pygame.draw.circle(s, col("peach"), (X + 8 + d * 2, y0 + 3), 2)
    s.fill(col(tint), (X + 6 + d * 2, y0, 5, 2))
    s.fill(col("black"), (X + 8 + d * 3, y0 + 3, 1, 1))
    s.fill(col("yellow"), (X + 15 if d > 0 else X, y0 + 9, 1, 2))


def draw_scooter(s, X, y0, d, t, tint="red"):
    for wx in (X + 4, X + 19):
        pygame.draw.circle(s, col("black"), (wx, y0 + 12), 3)
        s.fill(col("gray"), (wx, y0 + 12, 1, 1))
    pygame.draw.ellipse(s, col(tint), (X + 2, y0 + 6, 20, 7))
    s.fill(col("white"), (X + 6, y0 + 7, 10, 1))
    bx = X + 1 if d > 0 else X + 15          # delivery box at the back
    s.fill(col("black"), (bx - 1, y0 + 1, 10, 7))
    s.fill(col("yellow"), (bx, y0 + 2, 8, 5))
    s.fill(col("red"), (bx + 2, y0 + 4, 4, 1))
    rx = X + 12 + d * 2
    s.fill(col("blue"), (rx - 2, y0 + 3, 5, 4))
    pygame.draw.circle(s, col("peach"), (rx + d, y0 + 2), 2)
    s.fill(col("white"), (rx - 1 + d, y0, 4, 2))
    fx = X + 23 if d > 0 else X
    s.fill(col("yellow"), (fx, y0 + 7, 1, 3))


def draw_can(s, X, y0, d, t, tint="gray"):
    bob = int(abs(math.sin(t * 9 + X * 0.1)) * 2)
    y = y0 + 3 - bob
    pygame.draw.rect(s, col("black"), (X, y, 14, 11), border_radius=3)
    pygame.draw.rect(s, col(tint), (X + 1, y + 1, 12, 9), border_radius=2)
    roll = int(t * 14 * d) % 4
    for i in range(3):
        rx = X + 2 + (i * 4 + roll) % 11
        s.fill(col("darkgray"), (rx, y + 1, 1, 9))
    s.fill(col("white"), (X + 3, y + 2, 6, 1))
    lx = X + 13 if d > 0 else X
    s.fill(col("darkgray"), (lx, y - 1, 1, 13))
    if int(t * 6) % 2:
        s.fill(col("lime"), (X + 6, y - 2, 1, 1))      # a stinky little fly


def draw_van(s, X, y0, d, t, tint="cream"):
    pygame.draw.rect(s, col("black"), (X, y0 + 1, 40, 12), border_radius=3)
    pygame.draw.rect(s, col(tint), (X + 1, y0 + 2, 38, 10), border_radius=2)
    s.fill(col("orange"), (X + 1, y0 + 9, 38, 2))
    wx = X + 30 if d > 0 else X + 3
    s.fill(col("sky"), (wx, y0 + 3, 7, 4))
    s.fill(col("white"), (wx + 1, y0 + 3, 2, 1))
    # a steaming noodle bowl painted on the side
    bx = X + 12 if d > 0 else X + 20
    pygame.draw.ellipse(s, col("red"), (bx, y0 + 5, 9, 4))
    s.fill(col("yellow"), (bx + 2, y0 + 4, 5, 1))
    if int(t * 4) % 2:
        s.fill(col("white"), (bx + 4, y0 + 2, 1, 2))
    for wx2 in (X + 8, X + 31):
        pygame.draw.circle(s, col("black"), (wx2, y0 + 13), 3)
        s.fill(col("gray"), (wx2, y0 + 13, 1, 1))
    fx = X + 39 if d > 0 else X
    s.fill(col("yellow"), (fx, y0 + 4, 1, 3))


def draw_pigeon(s, X, y0, d, t, tint="gray"):
    bob = int(t * 8) % 2
    pygame.draw.ellipse(s, col("black"), (X, y0 + 5, 12, 8))
    pygame.draw.ellipse(s, col(tint), (X + 1, y0 + 6, 10, 6))
    hx = X + 9 if d > 0 else X + 2
    pygame.draw.circle(s, col("lavender"), (hx, y0 + 5 + bob), 2)
    s.fill(col("black"), (hx, y0 + 4 + bob, 1, 1))
    s.fill(col("orange"), (hx + d * 2, y0 + 5 + bob, 1, 1))
    s.fill(col("orange"), (X + 4 + bob, y0 + 13, 1, 2))
    s.fill(col("orange"), (X + 7 - bob, y0 + 13, 1, 2))


TRAFFIC = {"bike": draw_bike, "scooter": draw_scooter, "can": draw_can, "van": draw_van, "pigeon": draw_pigeon}
TINTS = {"bike": ("sky", "lime", "pink", "mint"), "scooter": ("red", "teal", "purple", "orange"),
         "can": ("gray", "teal", "lavender", "gray"), "van": ("cream", "white", "peach", "pink"),
         "pigeon": ("gray", "gray", "lavender", "gray")}


def draw_traffic(s, kind, X, y0, d, t, i=0):
    TRAFFIC[kind](s, int(X), y0, d, t, TINTS[kind][i % 4])


def headlight(kind, X, d):
    """x of the headlight (for the dark stages) of a vehicle at screen x X moving in d."""
    w = {"bike": 16, "scooter": 24, "can": 14, "van": 40, "pigeon": 12}[kind]
    return X + w + 6 if d > 0 else X - 6


# ----------------------------------------------------------------------------- floaters
def draw_crate(s, X, y0, w, t):
    bob = 1 if int(t * 2 + X * 0.05) % 2 else 0
    for i in range(w // 16):
        x = X + i * 16
        s.fill(col("choco"), (x + 1, y0 + 2 + bob, 14, 12))
        s.fill(col("brown"), (x + 2, y0 + 3 + bob, 12, 10))
        pygame.draw.line(s, col("choco"), (x + 2, y0 + 3 + bob), (x + 13, y0 + 12 + bob))
        pygame.draw.line(s, col("choco"), (x + 13, y0 + 3 + bob), (x + 2, y0 + 12 + bob))
        s.fill(col("peach"), (x + 2, y0 + 3 + bob, 12, 1))
    s.fill(col("sky"), (X, y0 + 14, w, 1))


def draw_ducks(s, X, y0, w, d, t, state="up"):
    """A mother duck leading her ducklings; state up | tell | down (diving)."""
    n = (w - 16) // 12
    if state == "down":
        for i in range(n + 1):
            cx = X + 8 + i * 12
            s.fill(col("sky"), (cx - 4, y0 + 11, 8, 1))
            if int(t * 6 + i) % 2:
                s.fill(col("white"), (cx, y0 + 9, 1, 1))
        return
    shake = int(math.sin(t * 30) * 1) if state == "tell" else 0
    mx = X + w - 8 if d > 0 else X + 8          # the mother swims in front
    order = [(mx, True)] + [((X + w - 22 - 12 * i) if d > 0 else (X + 22 + 12 * i), False) for i in range(n)]
    for cx, big in order:
        cx += shake
        if big:
            pygame.draw.ellipse(s, col("black"), (cx - 7, y0 + 5, 14, 9))
            pygame.draw.ellipse(s, col("white"), (cx - 6, y0 + 6, 12, 7))
            hx = cx + d * 4
            pygame.draw.circle(s, col("black"), (hx, y0 + 4), 3)
            pygame.draw.circle(s, col("white"), (hx, y0 + 4), 2)
            s.fill(col("orange"), (hx + d * 2 - (1 if d < 0 else 0), y0 + 4, 2, 1))
            s.fill(col("black"), (hx + d, y0 + 3, 1, 1))
        else:
            pygame.draw.ellipse(s, col("black"), (cx - 5, y0 + 7, 10, 7))
            pygame.draw.ellipse(s, col("yellow"), (cx - 4, y0 + 8, 8, 5))
            pygame.draw.circle(s, col("yellow"), (cx + d * 3, y0 + 7), 2)
            s.fill(col("orange"), (cx + d * 5 - (1 if d < 0 else 0), y0 + 7, 1, 1))
        s.fill(col("sky"), (cx - 6, y0 + 14, 12, 1))
    if state == "tell" and int(t * 8) % 2:
        draw_text(s, "!", mx - 2, y0 - 6, "yellow", shadow="black")


def draw_fish(s, X, y0, w, d, t, state="up"):
    """A big sleepy koi floating along (kittens nap on it). Dives when it wakes up."""
    if state == "down":
        s.fill(col("orange"), (X + w // 2 - 2, y0 + 10, 5, 2))
        s.fill(col("sky"), (X + 4, y0 + 12, w - 8, 1))
        return
    shake = int(math.sin(t * 30) * 1) if state == "tell" else 0
    x = X + shake
    pygame.draw.ellipse(s, col("black"), (x + 3, y0 + 4, w - 8, 10))
    pygame.draw.ellipse(s, col("white"), (x + 4, y0 + 5, w - 10, 8))
    for i in range(3):
        s.fill(col("orange"), (x + 8 + i * 9, y0 + 6 + (i % 2), 5, 3))
    tx = x + 1 if d > 0 else x + w - 6        # tail at the back
    pygame.draw.polygon(s, col("orange"), [(tx, y0 + 4), (tx + 5, y0 + 9), (tx, y0 + 13)] if d > 0 else
                        [(tx + 5, y0 + 4), (tx, y0 + 9), (tx + 5, y0 + 13)])
    ex = x + w - 12 if d > 0 else x + 9
    s.fill(col("black"), (ex, y0 + 7, 3, 1))        # a sleepy closed eye
    s.fill(col("sky"), (X + 2, y0 + 14, w - 4, 1))
    if state == "tell":
        if int(t * 8) % 2:
            draw_text(s, "!", ex - 1, y0 - 6, "yellow", shadow="black")
    elif int(t * 1.5 + X * 0.01) % 3 == 0:
        draw_text(s, "Z", ex + d * 4, y0 - 4 - int(t * 4) % 3, "lavender", shadow=None)


def draw_sheet(s, X, y0, w, t, i):
    c = SHEET_COLORS[i % len(SHEET_COLORS)]
    flap = int(math.sin(t * 3 + i) * 1.5)
    s.fill(col("black"), (X - 1, y0 + 2, w + 2, 13 + flap))
    s.fill(col(c), (X, y0 + 3, w, 11 + flap))
    for k in range(4, w, 8):
        s.fill(col("white" if c != "white" else "sky"), (X + k, y0 + 5 + (k // 8) % 2 * 3, 2, 1))
    s.fill(col("brown"), (X + 2, y0 + 1, 2, 3))
    s.fill(col("brown"), (X + w - 4, y0 + 1, 2, 3))


def draw_tray(s, X, y0, t, i):
    s.fill(col("black"), (X, y0 + 4, 16, 9))
    s.fill(col("cream"), (X + 1, y0 + 5, 14, 7))
    s.fill(col("orange" if i % 2 else "pink"), (X + 3, y0 + 7, 10, 3))


# ----------------------------------------------------------------------------- props
def draw_block(s, x, y0, kind, t):
    """Static obstacles on sidewalks: 0 chimney, 1 trash bin, 2 flower pot, 3 hydrant."""
    if kind == 0:
        s.fill(col("black"), (x + 2, y0, 12, 15))
        s.fill(col("red"), (x + 3, y0 + 3, 10, 11))
        for yy in (y0 + 6, y0 + 10):
            s.fill(col("choco"), (x + 3, yy, 10, 1))
        s.fill(col("darkgray"), (x + 1, y0, 14, 3))
        if int(t * 2 + x) % 4 == 0:
            s.fill(col("gray"), (x + 7, y0 - 3, 2, 2))
    elif kind == 1:
        pygame.draw.rect(s, col("black"), (x + 2, y0 + 2, 12, 13), border_radius=2)
        s.fill(col("teal"), (x + 3, y0 + 4, 10, 10))
        s.fill(col("gray"), (x + 2, y0 + 2, 12, 2))
        s.fill(col("mint"), (x + 5, y0 + 6, 1, 6))
    elif kind == 2:
        s.fill(col("black"), (x + 3, y0 + 8, 10, 7))
        s.fill(col("orange"), (x + 4, y0 + 9, 8, 5))
        pygame.draw.circle(s, col("lime"), (x + 8, y0 + 6), 4)
        for fx, fy, c in ((x + 6, y0 + 4, "pink"), (x + 10, y0 + 6, "yellow"), (x + 7, y0 + 7, "hotpink")):
            s.fill(col(c), (fx, fy, 2, 2))
    else:
        s.fill(col("black"), (x + 4, y0 + 3, 8, 12))
        s.fill(col("red"), (x + 5, y0 + 4, 6, 10))
        s.fill(col("black"), (x + 2, y0 + 7, 12, 3))
        s.fill(col("red"), (x + 3, y0 + 8, 10, 1))
        s.fill(col("pink"), (x + 6, y0 + 5, 1, 4))


def draw_box(s, x, y0, n_in, t, closed=False, warn=False, glow=False):
    """A cozy cardboard box in the home row (x = cell left). n_in kittens peek out."""
    if glow:
        pygame.draw.rect(s, col("yellow"), (x - 1, y0 + 1, 18, 15), 1)
    s.fill(col("black"), (x + 1, y0 + 5, 14, 11))
    s.fill(col("brown"), (x + 2, y0 + 6, 12, 9))
    s.fill(col("choco"), (x + 2, y0 + 12, 12, 1))
    if closed:
        s.fill(col("black"), (x, y0 + 3, 16, 3))
        s.fill(col("peach"), (x + 1, y0 + 4, 14, 1))
        s.fill(col("yellow"), (x + 7, y0 + 3, 2, 4))
        if warn and int(t * 8) % 2:
            s.fill(col("red"), (x + 6, y0, 4, 2))
        return
    flap = int(math.sin(t * 3 + x) * 1)
    s.fill(col("peach"), (x - 1, y0 + 4 + flap, 4, 2))
    s.fill(col("peach"), (x + 13, y0 + 4 - flap, 4, 2))
    for i in range(min(n_in, 3)):
        hx = x + 4 + i * 4
        pygame.draw.circle(s, col(("orange", "gray", "cream")[i]), (hx, y0 + 5), 2)
        s.fill(col("black"), (hx - 1, y0 + 4, 1, 1))
        s.fill(col("black"), (hx + 1, y0 + 4, 1, 1))
    if n_in > 3:
        draw_text(s, f"{n_in}", x + 8, y0 + 7, "yellow", align="center", shadow="black")
    if warn and int(t * 8) % 2:
        s.fill(col("red"), (x + 6, y0, 4, 2))


def draw_puddle(s, x, y0, t):
    pygame.draw.ellipse(s, col("blue"), (x + 1, y0 + 5, 14, 8))
    pygame.draw.ellipse(s, col("sky"), (x + 3, y0 + 7, 9, 4), 1)
    k = int(t * 3 + x) % 5
    if k < 2:
        s.fill(col("white"), (x + 5 + k * 3, y0 + 8, 1, 1))


def draw_manhole(s, x, y0, t, open_=0.0):
    pygame.draw.ellipse(s, col("black"), (x + 1, y0 + 4, 14, 10))
    pygame.draw.ellipse(s, col("gray"), (x + 2, y0 + 5, 12, 8))
    pygame.draw.ellipse(s, col("darkgray"), (x + 4, y0 + 7, 8, 4), 1)
    if int(t * 2 + x) % 3 == 0:
        s.fill(col("lime"), (x + 7, y0 + 2, 2, 1))       # it whispers 'shortcut'


def draw_item(s, kind, cx, cy, t):
    bob = int(math.sin(t * 4 + cx * 0.3) * 1.5)
    name = {"fish": "ah_fish", "gold": "ah_goldfish", "yarn": "ah_yarn", "clock": "ah_clock", "nip": "ah_nip",
            "bell": "ah_bell", "box": "ah_boxitem", "heart": "heart"}[kind]
    sp = sprite(name)
    if kind in ("gold", "nip", "bell", "box", "heart") and int(t * 6) % 2:
        s.fill(col("white"), (int(cx) + 5, int(cy) - 7 + bob, 1, 1))
    s.blit(sp, (int(cx) - sp.get_width() // 2, int(cy) - sp.get_height() // 2 + bob))


def draw_train(s, front, y0, length, d, t):
    """A night express: engine + lit carriages. front = x of the leading edge."""
    x0 = front - length if d > 0 else front
    ncar = (length - 40) // 48
    for i in range(ncar + 1):
        if i == 0:
            cx = front - 40 if d > 0 else front
            cw = 40
        else:
            cx = (front - 40 - 48 * i) if d > 0 else (front + 40 + 48 * (i - 1))
            cw = 46
        s.fill(col("black"), (int(cx), y0, cw, 16))
        s.fill(col("red" if i == 0 else "teal"), (int(cx) + 1, y0 + 1, cw - 2, 13))
        s.fill(col("white"), (int(cx) + 1, y0 + 10, cw - 2, 1))
        if i == 0:
            wx = int(cx) + (26 if d > 0 else 6)
            s.fill(col("sky"), (wx, y0 + 3, 8, 5))
            s.fill(col("yellow"), (int(cx) + (38 if d > 0 else 1), y0 + 6, 1, 3))
        else:
            for k in range(4):
                s.fill(col("yellow" if (k + i) % 3 else "cream"), (int(cx) + 4 + k * 11, y0 + 3, 7, 5))
    return x0


def draw_signal(s, x, y0, t, on):
    s.fill(col("black"), (x, y0 + 2, 6, 13))
    s.fill(col("darkgray"), (x + 1, y0 + 3, 4, 11))
    a = on and int(t * 6) % 2 == 0
    b = on and int(t * 6) % 2 == 1
    s.fill(col("red" if a else "choco"), (x + 1, y0 + 4, 2, 2))
    s.fill(col("red" if b else "choco"), (x + 3, y0 + 4, 2, 2))
    s.fill(col("white"), (x + 2, y0 + 8, 2, 1))


def draw_gate(s, x, y0, t, opn, warn):
    if opn:
        s.fill(col("brown"), (x, y0 + 2, 2, 13))
        s.fill(col("brown"), (x + 14, y0 + 2, 2, 13))
        if warn and int(t * 8) % 2:
            s.fill(col("red"), (x + 6, y0 + 1, 4, 2))
        return
    s.fill(col("black"), (x, y0 + 1, 16, 15))
    s.fill(col("orange"), (x + 1, y0 + 2, 14, 13))
    for k in range(3, 15, 4):
        s.fill(col("brown"), (x + k, y0 + 2, 1, 13))
    s.fill(col("yellow"), (x + 7, y0 + 7, 2, 2))
