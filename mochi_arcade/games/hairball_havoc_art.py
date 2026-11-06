"""HAIRBALL HAVOC drawing: rooms (floor, walls, doors, furniture), hairballs, toy bullets, pick-ups and the
five boss designs (+ the final WIND-UP KING). Original art. Mirrored by ios/MochiArcade/Games/HairballHavocArt.swift.
"""
import math

import pygame

from mochi_arcade import music
from mochi_arcade.arcade import rainbow
from mochi_arcade.games import hairball_havoc_data as D
from mochi_arcade.games import hairball_havoc_sprites  # noqa: F401  (registers the hh_ sprites)
from mochi_arcade.gfx import H, W, col, sprite

BOOKS = ("red", "sky", "yellow", "lime", "lavender", "orange")

# ---------------------------------------------------------------- music (original chiptunes)
_K = "K:8 H:8 S:8 H:8 K:8 H:8 S:8 K:8"


def _bass(roots):
    return " ".join(" ".join(f"{n}:8" for n in (r + "2", r + "3") * 4) for r in roots)


music.SONGS.update({
    # "Hairball Hustle" - the house, rooms 1-10 (G major, bouncy)
    "hh_house": {"bpm": 152, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "G5:8 B5:8 D6:8 B5:8 C6:8 A5:8 F#5:4  G5:8 A5:8 B5:8 G5:8 E5:4 D5:4 "
            "C5:8 E5:8 G5:8 C6:8 B5:8 G5:8 E5:4  D5:8 F#5:8 A5:8 D6:8 C6:4 A5:4 "
            "B5:8 D6:8 G6:8 D6:8 E6:8 D6:8 B5:4  C6:8 B5:8 A5:8 G5:8 A5:4 B5:4 "
            "C6:8 E6:8 D6:8 B5:8 A5:8 F#5:8 D5:4  G5:8 F#5:8 G5:8 A5:8 G5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": _bass(["G", "E", "C", "D", "G", "A", "D", "G"])},
        {"wave": "drums", "vol": 1, "notes": " ".join([_K] * 8)},
    ]},
    # "Clockwork Creep" - deeper in the house, rooms 11-20 (D minor, driving)
    "hh_deep": {"bpm": 158, "channels": [
        {"wave": "square", "duty": 0.125, "vol": 0.24, "notes":
            "D5:8 F5:8 A5:8 D6:8 C6:8 A5:8 F5:4  E5:8 G5:8 A#5:8 E6:8 D6:4 A#5:4 "
            "F5:8 A5:8 C6:8 F6:8 E6:8 C6:8 A5:4  C#6:8 A5:8 E5:8 A5:8 C#6:4 E6:4 "
            "D6:8 C6:8 A#5:8 A5:8 G5:8 A5:8 A#5:4  C6:8 A#5:8 A5:8 G5:8 F5:4 G5:4 "
            "A5:8 F5:8 D5:8 F5:8 A5:8 D6:8 C#6:4  D6:8 A5:8 F5:8 E5:8 D5:2"},
        {"wave": "triangle", "vol": 0.44, "gate": 0.6, "notes": _bass(["D", "A#", "F", "A", "A#", "C", "A", "D"])},
        {"wave": "drums", "vol": 1, "notes": " ".join(["K:8 H:8 S:8 H:8 K:8 K:8 S:8 H:8"] * 8)},
    ]},
})


def room_colors(room):
    r = D.ROOMS[room]
    return r[6], r[7]


def tint(name, room):
    a, b = room_colors(room)
    return a if name == "A" else (b if name == "B" else name)


# ---------------------------------------------------------------- room background (built once per stage)
def floor(s, style, a, b):
    x0, y0, x1, y1 = D.IX0, D.IY0, D.IX1, D.IY1
    s.fill(col(a), (x0, y0, x1 - x0, y1 - y0))
    cb = col(b)
    if style == "planks":
        for y in range(y0, y1, 8):
            s.fill(cb, (x0, y, x1 - x0, 1))
            off = ((y - y0) // 8 % 3) * 21
            for x in range(x0 + off, x1, 64):
                s.fill(cb, (x, y, 1, 8))
    elif style == "checker":
        for y in range(y0, y1, 12):
            for x in range(x0, x1, 12):
                if ((x - x0) // 12 + (y - y0) // 12) % 2:
                    s.fill(cb, (x, y, 12, 12))
    elif style == "carpet":
        for y in range(y0 + 2, y1, 6):
            for x in range(x0 + 2 + (3 if (y - y0) // 6 % 2 else 0), x1, 6):
                s.fill(cb, (x, y, 1, 1))
    elif style == "tiles":
        for y in range(y0, y1, 12):
            s.fill(cb, (x0, y, x1 - x0, 1))
        for x in range(x0, x1, 12):
            s.fill(cb, (x, y0, 1, y1 - y0))
    else:   # stone
        for y in range(y0, y1, 8):
            s.fill(cb, (x0, y, x1 - x0, 1))
            for x in range(x0 + (8 if (y - y0) // 8 % 2 else 0), x1, 16):
                s.fill(cb, (x, y, 1, 8))
    s.fill(col("black"), (x0, y0, x1 - x0, 2))   # shadow under the top wall


def rug(s, r, room):
    tx, ty, tw, th, pat = r
    a, b = room_colors(room)
    x, y, w, h = D.IX0 + tx * 8, D.IY0 + ty * 8, tw * 8, th * 8
    pygame.draw.rect(s, col(b), (x, y, w, h), border_radius=4)
    pygame.draw.rect(s, col(a), (x + 2, y + 2, w - 4, h - 4), border_radius=3)
    if pat == 0:
        for yy in range(y + 5, y + h - 4, 4):
            s.fill(col(b), (x + 4, yy, w - 8, 1))
    elif pat == 1:
        pygame.draw.ellipse(s, col(b), (x + 6, y + 5, w - 12, h - 10), 1)
        pygame.draw.ellipse(s, col("white"), (x + w // 2 - 4, y + h // 2 - 2, 8, 4))
    else:
        for xx in range(x + 4, x + w - 3, 6):
            for yy in range(y + 4, y + h - 3, 6):
                s.fill(col(b), (xx, yy, 2, 2))
    for xx in range(x + 1, x + w - 1, 3):     # tassels
        s.fill(col("white"), (xx, y - 1, 1, 1))
        s.fill(col("white"), (xx, y + h, 1, 1))


def walls(s, room, doors):
    r = D.ROOMS[room]
    wall, stripe = r[4], r[5]
    s.fill(col("black"), (0, 0, W, 10))
    s.fill(col(wall), (0, 10, W, 14))
    for x in range(4, W, 10):
        s.fill(col(stripe), (x, 12, 2, 8))
    s.fill(col("black"), (0, 10, W, 1))
    s.fill(col("brown"), (0, 20, W, 4))
    s.fill(col("peach"), (0, 20, W, 1))
    # pictures and windows between the doors
    for i, x in enumerate((44, 120, 200, 276)):
        if any(d[0] == 0 and abs(D.IX0 + d[1] * 8 + 12 - x) < 26 for d in doors):
            continue
        if i % 2 == 0:
            s.fill(col("choco"), (x - 9, 11, 18, 9))
            s.fill(col("sky"), (x - 8, 12, 16, 7))
            s.fill(col("white"), (x - 8, 15, 16, 1))
            s.fill(col("white"), (x, 12, 1, 7))
        else:
            s.fill(col("yellow"), (x - 6, 12, 12, 8))
            s.fill(col("ink"), (x - 5, 13, 10, 6))
            s.blit(sprite("heart"), (x - 3, 13))
    for x in (0, D.IX1):
        s.fill(col("ink"), (x, 10, 8, H - 10))
        s.fill(col("deep"), (x + (7 if x == 0 else 0), 24, 1, D.IY1 - 24))
    s.fill(col("black"), (0, D.IY1, W, H - D.IY1))
    s.fill(col("deep"), (0, D.IY1, W, 1))


def door(s, side, pos):
    x, y, w, h = D.door_rect(side, pos)
    if side == 0:
        s.fill(col("choco"), (x - 2, y, w + 4, h))
        s.fill(col("black"), (x, y + 2, w, h - 2))
        s.fill(col("brown"), (x - 2, y, w + 4, 1))
    else:
        s.fill(col("choco"), (x, y - 2, w, h + 4))
        s.fill(col("black"), (x + (2 if side == 1 else 0), y, w - 2, h))


def furniture(s, k, x, y, w, h, room):
    _, _, style, top, front = D.FURN[k]
    ct, cf, kk = col(tint(top, room)), col(tint(front, room)), col("black")
    cx = x + w // 2
    if style in ("plant", "lamp", "barrel", "gear"):
        pygame.draw.ellipse(s, kk, (x + 1, y + h - 5, w - 2, 6))
        cy = y + h // 2 - 1
        r = min(w, h) // 2 - 1
        if style == "plant":
            pygame.draw.polygon(s, cf, [(cx - 5, cy + 1), (cx + 5, cy + 1), (cx + 4, y + h - 2), (cx - 4, y + h - 2)])
            s.fill(ct, (cx - 6, cy, 12, 2))
            for i, (dx, dy) in enumerate(((-4, -3), (4, -3), (0, -6), (-6, 1), (6, 1), (0, -1))):
                pygame.draw.circle(s, col("teal" if i % 2 else "lime"), (cx + dx, cy + dy), 3)
            s.fill(col("white"), (cx - 1, cy - 7, 1, 1))
        elif style == "lamp":
            s.fill(col("brown"), (cx - 1, cy, 2, h // 2))
            pygame.draw.circle(s, cf, (cx, cy - 1), r)
            pygame.draw.circle(s, ct, (cx, cy - 2), r - 2)
            s.fill(col("white"), (cx - 2, cy - 4, 2, 1))
        elif style == "barrel":
            pygame.draw.circle(s, kk, (cx, cy), r + 1)
            pygame.draw.circle(s, ct, (cx, cy), r)
            pygame.draw.circle(s, cf, (cx, cy), r - 2, 1)
            pygame.draw.circle(s, cf, (cx, cy), 2)
        else:   # gear
            for i in range(8):
                a = i * math.tau / 8
                s.fill(cf, (int(cx + math.cos(a) * (r - 1)) - 2, int(cy + math.sin(a) * (r - 1)) - 2, 4, 4))
            pygame.draw.circle(s, ct, (cx, cy), r - 2)
            pygame.draw.circle(s, cf, (cx, cy), r - 5, 1)
            pygame.draw.circle(s, kk, (cx, cy), 2)
        return
    # a block in 3/4 view: shadow, front face, top surface, outline
    s.fill(kk, (x + 2, y + 2, w, h))
    pygame.draw.rect(s, cf, (x, y, w, h), border_radius=2)
    pygame.draw.rect(s, ct, (x, y, w, h - 4), border_radius=2)
    pygame.draw.rect(s, kk, (x, y, w, h), 1, border_radius=2)
    s.fill(kk, (x + 1, y + h - 4, w - 2, 1))
    ty, th = y + 1, h - 5          # top surface
    if style == "cushion":
        s.fill(cf, (x + 1, ty, w - 2, 4))
        s.fill(cf, (x + 1, ty, 3, th))
        s.fill(cf, (x + w - 4, ty, 3, th))
        n = max(1, (w - 8) // 12)
        cw = (w - 8) // n
        for i in range(n):
            pygame.draw.rect(s, cf, (x + 4 + i * cw, ty + 5, cw - 1, th - 6), 1, border_radius=2)
    elif style == "wood":
        for yy in range(ty + 3, ty + th - 1, 4):
            s.fill(cf, (x + 2, yy, w - 4, 1))
        pygame.draw.circle(s, col("white"), (cx, ty + th // 2), 3)
        pygame.draw.circle(s, col("sky"), (cx, ty + th // 2), 1)
    elif style == "shelf":
        if w >= h:
            for i, xx in enumerate(range(x + 2, x + w - 3, 3)):
                s.fill(col(BOOKS[i % 6]), (xx, ty + 1 + i % 2, 2, th - 2 - i % 2))
        else:
            for i, yy in enumerate(range(ty + 1, ty + th - 2, 3)):
                s.fill(col(BOOKS[i % 6]), (x + 2 + i % 2, yy, w - 4 - i % 2, 2))
    elif style == "bed":
        s.fill(col("brown"), (x + 1, ty, w - 2, 3))
        pygame.draw.rect(s, col("white"), (x + 4, ty + 4, w - 8, 7), border_radius=3)
        s.fill(cf, (x + 1, ty + 13, w - 2, 2))
        for xx in range(x + 4, x + w - 3, 6):
            s.fill(cf, (xx, ty + 17, 2, 2))
    elif style == "box":
        s.fill(col("yellow"), (cx - 1, ty, 3, th))
        s.fill(cf, (x + 1, ty + th // 2, w - 2, 1))
    elif style == "counter":
        for xx in range(x + 6, x + w - 4, 12):
            s.fill(col("gray"), (xx, ty, 1, th))
        pygame.draw.circle(s, col("darkgray"), (x + w - 7, ty + th // 2), 3)
        pygame.draw.circle(s, col("darkgray"), (x + w - 15, ty + th // 2), 3)
        s.fill(col("peach"), (x + 4, ty + 3, 7, 5))
    elif style in ("fridge", "washer"):
        if style == "fridge":
            s.fill(col("gray"), (x + w - 5, ty + 2, 2, th - 4))
            s.fill(cf, (x + 1, ty + th // 2 - 2, w - 2, 1))
            s.fill(col("red"), (x + 4, ty + 3, 2, 2))
            s.fill(col("yellow"), (x + 7, ty + 5, 2, 2))
        else:
            pygame.draw.circle(s, col("gray"), (cx, ty + th // 2 + 1), 7)
            pygame.draw.circle(s, col("sky"), (cx, ty + th // 2 + 1), 5)
            s.fill(col("white"), (cx - 2, ty + th // 2 - 2, 2, 1))
            s.fill(col("lime"), (x + 3, ty + 1, 3, 1))
    elif style == "tub":
        pygame.draw.rect(s, col("sky"), (x + 3, ty + 2, w - 6, th - 3), border_radius=4)
        for i, (dx, dy) in enumerate(((6, 4), (14, 7), (22, 3), (30, 6))):
            if x + dx < x + w - 4:
                pygame.draw.circle(s, col("white"), (x + dx, ty + dy), 2 if i % 2 else 1)
    elif style == "piano":
        s.fill(col("white"), (x + 2, ty + th - 5, w - 4, 4))
        for xx in range(x + 3, x + w - 3, 3):
            s.fill(kk, (xx, ty + th - 5, 1, 2))
        s.fill(col("white"), (cx - 5, ty + 2, 10, 5))
        s.fill(kk, (cx - 3, ty + 4, 6, 1))
    elif style == "crate":
        pygame.draw.rect(s, cf, (x + 1, ty, w - 2, th), 1)
        pygame.draw.line(s, cf, (x + 2, ty + 1), (x + w - 3, ty + th - 2))
        pygame.draw.line(s, cf, (x + w - 3, ty + 1), (x + 2, ty + th - 2))
    elif style == "tv":
        s.fill(col("night"), (x + 3, ty + 1, w - 6, th - 2))
        s.fill(col("sky"), (x + 4, ty + 2, 4, 1))
        s.fill(col("lavender"), (x + 4, ty + 4, 2, 1))
    elif style == "chest":
        s.fill(cf, (x + 1, ty + th // 2, w - 2, 1))
        s.fill(col("yellow"), (cx - 2, ty + th // 2 - 1, 4, 3))
        s.fill(cf, (x + 4, ty, 1, th))
        s.fill(cf, (x + w - 5, ty, 1, th))
    elif style == "blocks":
        for i, c in enumerate(("red", "sky", "yellow", "lime")):
            bx, by = x + 1 + (i % 2) * 7, ty + (i // 2) * 6
            s.fill(col(c), (bx, by, 6, 5))
            s.fill(kk, (bx, by + 5, 6, 1))
            s.fill(col("white"), (bx + 1, by + 1, 1, 1))
    elif style == "arcade":
        s.fill(col("night"), (x + 3, ty + 1, w - 6, th - 6))
        for i in range(3):
            s.fill(col(BOOKS[i]), (x + 5 + i * 5, ty + 3 + i % 2 * 3, 2, 2))
        pygame.draw.circle(s, col("red"), (x + 6, ty + th - 2), 2)
        s.fill(col("yellow"), (x + w - 8, ty + th - 3, 2, 2))
    elif style == "bench":
        for yy in range(ty + 3, ty + th - 1, 4):
            s.fill(cf, (x + 2, yy, w - 4, 1))
        s.fill(col("gray"), (x + 6, ty + 3, 8, 3))
        s.fill(col("brown"), (x + 14, ty + 4, 7, 1))
        s.fill(col("darkgray"), (x + w - 12, ty + 6, 6, 4))
    elif style == "pool":
        s.fill(col("choco"), (x + 1, ty, w - 2, th))
        s.fill(ct, (x + 4, ty + 3, w - 8, th - 6))
        for i, c in enumerate(("white", "red", "yellow", "blue", "hotpink")):
            pygame.draw.circle(s, col(c), (x + 10 + i * 7, ty + 6 + (i % 2) * 8), 1)


def build_room(st):
    """The static background of a stage: HUD band, walls, floor, rug, doors and furniture."""
    room = st["room"]
    r = D.ROOMS[room]
    s = pygame.Surface((W, H))
    floor(s, r[1], r[2], r[3])
    if st.get("rug"):
        rug(s, st["rug"], room)
    walls(s, room, st["doors"])
    for d in st["doors"]:
        door(s, d[0], d[1])
    for k, tx, ty, tw, th in sorted(st["furn"], key=lambda f: f[2] + f[4]):
        furniture(s, k, D.IX0 + tx * 8, D.IY0 + ty * 8, tw * 8, th * 8, room)
    return s


# ---------------------------------------------------------------- shots, bullets, pick-ups
def hairball(s, x, y, r, kind, t):
    if kind == 2:
        c1, c2 = rainbow(x // 6, t), "white"
    elif kind == 1:
        c1, c2 = "pink", "white"
    else:
        c1, c2 = "peach", "cream"
    pygame.draw.circle(s, col("choco"), (x, y), r + 1)
    pygame.draw.circle(s, col(c1), (x, y), r)
    s.fill(col(c2), (x - 1, y - 1, 1, 1))
    if r >= 3:
        s.fill(col("brown"), (x + 1, y, 1, 1))


BULLET_R = (2, 2, 2, 3, 2, 3, 0, 2)


def bullet(s, kind, x, y, t, fuse=0.0):
    k = col("black")
    if kind == 0:       # button
        pygame.draw.circle(s, k, (x, y), 3)
        pygame.draw.circle(s, col("sky" if (x + y) % 2 else "hotpink"), (x, y), 2)
        s.fill(k, (x - 1, y, 1, 1))
        s.fill(k, (x + 1, y, 1, 1))
    elif kind == 1:     # music note
        s.fill(k, (x - 2, y, 4, 3))
        s.fill(col("lavender"), (x - 1, y + 1, 2, 1))
        s.fill(k, (x + 1, y - 4, 1, 4))
        s.fill(col("hotpink"), (x + 2, y - 4, 1, 2))
    elif kind == 2:     # cheese
        pygame.draw.polygon(s, k, [(x - 3, y + 2), (x + 3, y + 2), (x, y - 3)])
        pygame.draw.polygon(s, col("yellow"), [(x - 2, y + 1), (x + 2, y + 1), (x, y - 2)])
        s.fill(col("orange"), (x, y, 1, 1))
    elif kind == 3:     # dust bunny
        pygame.draw.circle(s, col("darkgray"), (x, y), 3)
        pygame.draw.circle(s, col("gray"), (x, y), 2)
        s.fill(col("white"), (x - 1, y - 1, 1, 1))
    elif kind == 4:     # confetti
        s.fill(k, (x - 2, y - 2, 4, 4))
        s.fill(col(rainbow((x + y) // 3, t)), (x - 1, y - 1, 2, 2))
    elif kind == 5:     # steam puff
        pygame.draw.circle(s, col("gray"), (x, y), 4)
        pygame.draw.circle(s, col("white"), (x, y), 3)
    elif kind == 6:     # toy bomb (harmless until it bursts)
        pygame.draw.circle(s, k, (x, y), 3)
        s.fill(col("red" if int(t * (14 if fuse < 0.5 else 5)) % 2 else "gray"), (x - 1, y - 1, 2, 2))
        s.fill(col("yellow"), (x + 2, y - 4, 1, 1))
    else:               # spark
        pygame.draw.circle(s, k, (x, y), 3)
        pygame.draw.circle(s, col("orange"), (x, y), 2)
        s.fill(col("yellow"), (x, y - 1, 1, 1))


ITEM_SPRITE = {"Y": "hh_yarn", "L": "hh_laser", "N": "hh_catnip", "X": "hh_box", "H": "hh_bomb", "F": "hh_fish",
               "G": "hh_tuna"}
ITEM_RING = {"Y": "pink", "L": "red", "N": "lime", "X": "peach", "H": "orange", "F": "sky", "G": "yellow"}


def item(s, kind, x, y, t, life):
    if kind == "c":
        s.fill(col("sky" if int(t * 12 + x) % 2 else "white"), (x - 1, y - 1, 2, 2))
        return
    if life < 2.5 and int(t * 10) % 2:
        return
    bob = int(math.sin(t * 5) * 1.5)
    if kind != "F":
        pygame.draw.circle(s, col(ITEM_RING[kind] if int(t * 6) % 2 else "white"), (x, y + bob), 7, 1)
    sp = sprite(ITEM_SPRITE[kind])
    s.blit(sp, (x - sp.get_width() // 2, y - sp.get_height() // 2 + bob))
    if kind == "G" and int(t * 8) % 2:
        s.fill(col("white"), (x + 3, y - 5 + bob, 1, 1))


def spring(s, x0, y0, x1, y1, t):
    """A zig-zag spring between two points (pop boxes, King Boing)."""
    dx, dy = x1 - x0, y1 - y0
    d = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / d, dx / d
    n = max(2, int(d / 4))
    px, py = x0, y0
    for i in range(1, n + 1):
        u = i / n
        side = 0 if i == n else (3 if i % 2 else -3)
        qx, qy = x0 + dx * u + nx * side, y0 + dy * u + ny * side
        pygame.draw.line(s, col("gray"), (int(px), int(py)), (int(qx), int(qy)))
        px, py = qx, qy


def clown(s, x, y, r, t, crown=False, flash=False):
    """A jack-in-the-box head."""
    pygame.draw.circle(s, col("black"), (x, y), r + 1)
    pygame.draw.circle(s, col("white" if flash else "peach"), (x, y), r)
    e = max(1, r // 3)
    s.fill(col("black"), (x - e - 1, y - e, 2, 2))
    s.fill(col("black"), (x + e, y - e, 2, 2))
    pygame.draw.circle(s, col("red"), (x, y + 1), max(1, r // 4))
    s.fill(col("black"), (x - e, y + e + 1, e * 2 + 1, 1))
    if crown:
        pygame.draw.polygon(s, col("yellow"), [(x - r + 1, y - r + 2), (x - r + 2, y - r - 4), (x - 2, y - r),
                                                (x, y - r - 5), (x + 2, y - r), (x + r - 2, y - r - 4),
                                                (x + r - 1, y - r + 2)])
        s.fill(col("hotpink"), (x, y - r - 2, 1, 1))
    else:
        pygame.draw.polygon(s, col(rainbow(1, t)), [(x - r + 1, y - r + 2), (x, y - r - 5), (x + r - 1, y - r + 2)])


# ---------------------------------------------------------------- bosses
def boss(s, b, x, y, t, look, parts, flash):
    """Draw boss b centred at (x, y). parts: [(x, y, r, alive, flash)] already positioned."""
    k = b.kind
    pygame.draw.ellipse(s, col("black"), (x - b.bw // 2, y + b.bh // 2 - 3 + int(b.z), b.bw, 7))
    if k in (0, 5):
        mech(s, b, x, y, t, look, flash, k == 5)
    elif k == 1:
        fort(s, b, x, y, t, look, parts, flash)
    elif k == 2:
        king(s, b, x, y, t, look, flash)
    elif k == 3:
        socktopus(s, b, x, y, t, look, parts, flash)
    else:
        train(s, b, x, y, t, look, parts, flash)


def mech(s, b, x, y, t, look, flash, gold):
    body = "white" if flash else ("yellow" if gold else "gray")
    dark = "orange" if gold else "darkgray"
    k = col("black")
    step = int(math.sin(t * 8) * 2) if b.moving else 0
    for sd in (-1, 1):                                   # legs
        lx = x + sd * 11
        s.fill(k, (lx - 5, y + 8 + (step * sd if sd > 0 else -step), 10, 9))
        s.fill(col(dark), (lx - 4, y + 9 + (step * sd if sd > 0 else -step), 8, 7))
    tail = [(x + 18 + int(math.sin(t * 3 + i * 0.7) * 3) + i * 3, y + 6 - i * 3) for i in range(6)]
    pygame.draw.lines(s, col("pink"), False, tail, 2)
    for sd in (-1, 1):                                   # big round ears
        pygame.draw.circle(s, k, (x + sd * 16, y - 13), 10)
        pygame.draw.circle(s, col(body), (x + sd * 16, y - 13), 9)
        pygame.draw.circle(s, col("pink"), (x + sd * 16, y - 13), 5)
    pygame.draw.ellipse(s, k, (x - 21, y - 14, 42, 28))
    pygame.draw.ellipse(s, col(body), (x - 20, y - 13, 40, 26))
    s.fill(col(dark), (x - 20, y + 4, 40, 2))            # armour seam
    hatch = b.atk == "summon" and b.at > 0.3
    s.fill(k, (x - 7, y + 3, 14, 7))
    s.fill(col("black" if hatch else dark), (x - 6, y + 4, 12, 5))
    # visor eyes look at Biscuit
    s.fill(k, (x - 13, y - 9, 26, 8))
    glow = "red" if not (b.atk in ("lane", "fan") and b.at < 0.6 and int(t * 16) % 2) else "white"
    for sd in (-1, 1):
        s.fill(col(glow), (x + sd * 6 - 2 + look, y - 7, 5, 4))
        s.fill(col("white"), (x + sd * 6 - 1 + look, y - 7, 1, 1))
    pygame.draw.circle(s, col("hotpink"), (x, y - 1), 2)     # nose
    for sd in (-1, 1):
        for i in (-1, 1):
            pygame.draw.line(s, k, (x + sd * 4, y - 1 + i), (x + sd * 14, y - 2 + i * 3))
    # wind-up key turning on its back
    kw = int(abs(math.cos(t * 4)) * 6) + 1
    s.fill(col("orange" if gold else "yellow"), (x - 1, y - 22, 3, 8))
    s.fill(col("orange" if gold else "yellow"), (x - kw, y - 25, kw * 2 + 1, 4))
    s.fill(k, (x - kw, y - 25, kw * 2 + 1, 1))
    # cheese launchers on the shoulders (glow before a volley)
    hot = b.atk in ("fan", "rain") and b.at < 0.6 and int(t * 14) % 2
    for sd in (-1, 1):
        pygame.draw.polygon(s, col("white" if hot else "yellow"),
                            [(x + sd * 20, y - 4), (x + sd * 27, y - 9), (x + sd * 27, y)])
        pygame.draw.polygon(s, k, [(x + sd * 20, y - 4), (x + sd * 27, y - 9), (x + sd * 27, y)], 1)
    if gold:
        pygame.draw.polygon(s, col("yellow"), [(x - 9, y - 13), (x - 9, y - 21), (x - 4, y - 16), (x, y - 23),
                                               (x + 4, y - 16), (x + 9, y - 21), (x + 9, y - 13)])
        s.fill(col("hotpink"), (x - 1, y - 18, 3, 3))


def fort(s, b, x, y, t, look, parts, flash):
    k = col("black")
    body = "white" if flash else "darkgray"
    for sd in (-1, 1):                                   # side brushes
        a = t * (14 if b.atk in ("suck", "charge") else 5) * sd
        bx, by = x + sd * 22, y + 10
        for i in range(3):
            aa = a + i * math.tau / 3
            pygame.draw.line(s, col("yellow"), (bx, by), (int(bx + math.cos(aa) * 7), int(by + math.sin(aa) * 4)))
    pygame.draw.ellipse(s, k, (x - 28, y - 17, 56, 36))
    pygame.draw.ellipse(s, col("sky"), (x - 27, y - 16, 54, 34))     # bumper
    pygame.draw.ellipse(s, col(body), (x - 25, y - 17, 50, 30))
    pygame.draw.ellipse(s, col("gray" if not flash else "white"), (x - 21, y - 15, 42, 22))
    for i in range(8):                                   # light ring
        a = i * math.tau / 8 + t
        on = (i + int(t * 6)) % 4 == 0
        s.fill(col("red" if on else "black"), (int(x + math.cos(a) * 18) - 1, int(y - 4 + math.sin(a) * 9) - 1, 2, 2))
    s.fill(k, (x - 10, y - 9, 20, 9))                    # face screen
    s.fill(col("night"), (x - 9, y - 8, 18, 7))
    angry = b.phase > 0
    for sd in (-1, 1):
        s.fill(col("sky"), (x + sd * 5 - 1 + look, y - 6, 3, 3))
        if angry:
            s.fill(col("red"), (x + sd * 5 - 2, y - 8 + (0 if sd < 0 else 0), 5, 1))
    sucking = b.atk == "suck" and b.at > 0.8
    s.fill(k, (x - 14, y + 7, 28, 5))                    # intake
    s.fill(col("hotpink" if sucking and int(t * 20) % 2 else "black"), (x - 13, y + 8, 26, 3))
    for px, py, r, alive, pf in parts:                   # turrets
        if not alive:
            pygame.draw.circle(s, col("black"), (px, py), r)
            s.fill(col("darkgray"), (px - 1, py - 1, 2, 2))
            continue
        pygame.draw.circle(s, k, (px, py), r + 1)
        pygame.draw.circle(s, col("white" if pf else "lavender"), (px, py), r)
        s.fill(col("purple"), (px - 2, py - 2, 4, 2))


def king(s, b, x, y, t, look, flash):
    k = col("black")
    z = int(b.z)
    y -= z
    box = "white" if flash else "purple"
    s.fill(k, (x - 17, y - 13, 34, 30))
    s.fill(col(box), (x - 16, y - 12, 32, 28))
    s.fill(col("lavender"), (x - 16, y - 12, 32, 5))     # box top
    s.fill(k, (x - 16, y - 7, 32, 1))
    pygame.draw.polygon(s, col("yellow"), [(x, y - 3), (x + 3, y + 3), (x + 8, y + 3), (x + 4, y + 7), (x + 6, y + 12),
                                           (x, y + 9), (x - 6, y + 12), (x - 4, y + 7), (x - 8, y + 3), (x - 3, y + 3)])
    a = t * 6                                            # crank
    s.fill(col("gray"), (x + 16, y + 1, 4, 2))
    pygame.draw.line(s, col("gray"), (x + 19, y + 2), (int(x + 19 + math.cos(a) * 5), int(y + 2 + math.sin(a) * 5)), 2)
    hx, hy = b.head
    spring(s, x, y - 12, hx, hy + 6 - z, t)
    clown(s, int(hx), int(hy) - z, 9, t, crown=True, flash=flash)


def socktopus(s, b, x, y, t, look, parts, flash):
    k = col("black")
    for px, py, r, alive, pf in parts:                   # sock tentacles
        if not alive:
            pygame.draw.circle(s, col("darkgray"), (px, py), 3)
            continue
        n = 5
        for i in range(n + 1):
            u = i / n
            qx, qy = int(x + (px - x) * u), int(y + 4 + (py - y - 4) * u)
            pygame.draw.circle(s, k, (qx, qy), 4)
            pygame.draw.circle(s, col("white" if pf else ("red" if i % 2 else "white")), (qx, qy), 3)
        pygame.draw.circle(s, col("sky" if not pf else "white"), (px, py), r)
    body = "white" if flash else "lavender"
    pygame.draw.ellipse(s, k, (x - 18, y - 16, 36, 30))
    pygame.draw.ellipse(s, col(body), (x - 17, y - 15, 34, 28))
    for i in range(3):                                   # stripes
        s.fill(col("purple" if not flash else "white"), (x - 15 + i, y - 6 + i * 6, 30 - i * 2, 2))
    for sd in (-1, 1):                                   # button eyes
        ex = x + sd * 7 + look
        pygame.draw.circle(s, k, (ex, y - 8), 4)
        pygame.draw.circle(s, col("hotpink" if b.phase else "sky"), (ex, y - 8), 3)
        s.fill(k, (ex - 1, y - 8, 1, 1))
        s.fill(k, (ex + 1, y - 8, 1, 1))
    open_ = b.atk in ("fan", "ring") and b.at > 0.3
    pygame.draw.ellipse(s, k, (x - 7, y + 1, 14, 6 if open_ else 3))
    if open_:
        s.fill(col("hotpink"), (x - 4, y + 3, 8, 2))
    for xx in range(x - 12, x + 13, 4):                  # stitches
        s.fill(k, (xx, y - 15, 2, 1))


def train(s, b, x, y, t, look, parts, flash):
    k = col("black")
    for i in range(len(parts) - 1, -1, -1):              # carriages, last one first
        px, py, r, alive, pf = parts[i]
        if not alive:
            s.fill(col("darkgray"), (px - 6, py - 4, 12, 8))
            continue
        c = "white" if pf else ("blue" if i % 2 else "lime")
        s.fill(k, (px - 9, py - 7, 18, 14))
        s.fill(col(c), (px - 8, py - 6, 16, 10))
        s.fill(col("yellow"), (px - 5, py - 9, 10, 4))
        s.fill(k, (px - 5, py - 9, 10, 1))
        for sd in (-1, 1):
            pygame.draw.circle(s, k, (px + sd * 5, py + 5), 3)
            s.fill(col("gray"), (px + sd * 5, py + 5, 1, 1))
    f = b.face
    body = "white" if flash else "red"
    s.fill(k, (x - 13, y - 9, 26, 18))
    s.fill(col(body), (x - 12, y - 8, 24, 14))
    s.fill(col("choco"), (x - 12, y - 8, 24, 3))
    s.fill(col("blue"), (x - f * 6 - 4, y - 14, 9, 8))  # cab
    s.fill(k, (x - f * 6 - 4, y - 14, 9, 1))
    s.fill(col("sky"), (x - f * 6 - 2, y - 12, 5, 3))
    s.fill(k, (x + f * 6 - 2, y - 15, 5, 7))             # chimney
    s.fill(col("darkgray"), (x + f * 6 - 1, y - 14, 3, 6))
    pygame.draw.circle(s, col("yellow"), (x + f * 12, y - 1), 2)   # lamp
    for sd in (-1, 0, 1):
        wy = y + 7
        pygame.draw.circle(s, k, (x + sd * 8, wy), 4)
        pygame.draw.circle(s, col("gray"), (x + sd * 8, wy), 3)
        a = t * 10
        s.fill(k, (int(x + sd * 8 + math.cos(a) * 2), int(wy + math.sin(a) * 2), 1, 1))
    for sd in (-1, 1):                                   # angry little face
        s.fill(k, (x + f * 3 + sd * 3, y - 3, 2, 2))
    s.fill(k, (x + f * 3 - 2, y + 2, 5, 1))
