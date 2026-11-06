"""SOAP HOP art: the new dust critters, the six bosses, item sprites and upgrade-card icons.
All original designs for MOCHI ARCADE. Mirrored in ios/MochiArcade/Games/SoapHopArt.swift."""
import math

import pygame

from mochi_arcade import cute, sprites
from mochi_arcade.gfx import bubble, col, draw_text, sprite

# item sprites (same character palette as sprites.py) - registered for gen_data at import time
SH_ART = {
    "sh_chest": [[
        "..kkkkkkkk..",
        ".kooooooook.",
        "kooyyyyyyook",
        "kkkkkkkkkkkk",
        "konnnyynnnok",
        "konnykkynnok",
        "konnnyynnnok",
        "konnnnnnnnok",
        "kooooooooook",
        ".kkkkkkkkkk.",
    ]],
    "sh_soda": [[
        "..kkk..",
        ".kgggk.",
        "ksssssk",
        "kswwssk",
        "ksPPPsk",
        "ksPwPsk",
        "ksPPPsk",
        "ksssssk",
        ".kgggk.",
        "..kkk..",
    ]],
    "sh_clock": [[
        ".kk...kk.",
        "kyykkkyyk",
        ".kwwwwwk.",
        "kwwwkwwwk",
        "kwwwkwwwk",
        "kwwwkkkwk",
        "kwwwwwwwk",
        ".kwwwwwk.",
        "..kkkkk..",
    ]],
    "sh_gem": [[
        "..kkkkk..",
        ".kwssssk.",
        "kwsssssbk",
        "kkkkkkkkk",
        ".ksssbbk.",
        "..ksbbk..",
        "...kbk...",
        "....k....",
    ]],
    "sh_cake": [[
        ".....kk.....",
        ".....rr.....",
        "..kkkkkkkk..",
        ".kwwwwwwwwk.",
        "kppwppwppwpk",
        "kcccccccccck",
        "kcPcccPcccPk",
        "kcccccccccck",
        "kppppppppppk",
        "kcccccccccck",
        ".kkkkkkkkkk.",
    ]],
    "sh_shoe": [[
        "...kkk...",
        "..kmmmk..",
        "..kmwmk..",
        ".kmmmmkk.",
        "kmmmmmmmk",
        "kwwwwwwwk",
        ".kkkkkkk.",
    ]],
}
sprites.ART.update(SH_ART)


# ----------------------------------------------------------------------------- critters (16x16 boxes)
def fluff(dst, x, y, t, body, dark, flip=False, mood="angry", trapped=False, feet=True):
    """A dust puff in any colours (cute.grump with a palette)."""
    cx, cy = x + 8, y + 9
    bob = 0 if trapped else int(math.sin(t * 10))
    for a in range(0, 360, 40):
        r = math.radians(a + t * 60)
        pygame.draw.circle(dst, col(dark), (int(cx + math.cos(r) * 6), int(cy + bob + math.sin(r) * 5)), 3)
    pygame.draw.circle(dst, col(body), (cx, cy + bob), 6)
    look = -1 if flip else 1
    cute.eyes(dst, cx, cy - 1 + bob, 3, look, mood, blink=int(t * 2) % 7 == 0)
    cute.mouth(dst, cx + look, cy + 2 + bob, mood)
    if feet and not trapped:
        step = int(t * 8) % 2
        dst.fill(col("black"), (cx - 4 + step, y + 15, 3, 1))
        dst.fill(col("black"), (cx + 2 - step, y + 15, 3, 1))


def golden(dst, x, y, t, flip=False, trapped=False):
    fluff(dst, x, y, t, "yellow", "orange", flip, "happy", trapped)
    if int(t * 6) % 3 == 0:
        dst.fill(col("white"), (x + 3 + int(t * 7) % 10, y + 3, 1, 1))


def boing(dst, x, y, t, flip=False, angry=False, trapped=False, squash=0):
    """BOING: a lime puff on a coil spring - bounces all the time."""
    cx = x + 8
    by = y + 6 + squash
    if not trapped:
        for i in range(3):
            yy = y + 11 + squash + i * (2 - squash // 2)
            dst.fill(col("gray" if i % 2 else "white"), (cx - 3, yy, 7, 1))
        dst.fill(col("black"), (cx - 3, y + 15, 7, 1))
    pygame.draw.circle(dst, col("red" if angry else "lime"), (cx, by), 6)
    pygame.draw.circle(dst, col("hotpink" if angry else "teal"), (cx, by), 6, 1)
    dst.fill(col("hotpink" if angry else "teal"), (cx - 1, by - 8, 1, 2))
    dst.fill(col("hotpink" if angry else "teal"), (cx + 1, by - 9, 1, 3))
    look = -1 if flip else 1
    cute.eyes(dst, cx, by - 1, 2, look, "angry" if angry else ("wow" if trapped else "happy"))
    cute.mouth(dst, cx + look, by + 2, "wow" if squash == 0 and not trapped else "happy")


def zoomy(dst, x, y, t, flip=False, angry=False, trapped=False, dash=False, rev=False):
    """ZOOMY: an orange speed puff that revs up and dashes."""
    cx, cy = x + 8, y + 9
    look = -1 if flip else 1
    jit = (int(t * 30) % 2) if rev else 0
    if dash and not trapped:
        for i, yy in enumerate((cy - 3, cy, cy + 3)):
            ln = 4 + (i % 2) * 3
            dst.fill(col("white"), (cx - look * 8 - (ln if look > 0 else 0), yy, ln, 1))
    pygame.draw.polygon(dst, col("hotpink" if angry else "red"),
                        [(cx - look * 5, cy - 4), (cx - look * 10, cy - 7), (cx - look * 7, cy), (cx - look * 11, cy + 2),
                         (cx - look * 5, cy + 3)])
    pygame.draw.ellipse(dst, col("red" if angry else "orange"), (cx - 6 + jit, cy - 5, 13, 11))
    pygame.draw.ellipse(dst, col("brown"), (cx - 6 + jit, cy - 5, 13, 11), 1)
    cute.eyes(dst, cx + look + jit, cy - 1, 2, look, "angry")
    cute.mouth(dst, cx + look * 2 + jit, cy + 2, "angry" if not trapped else "wow")
    if not trapped:
        step = int(t * (16 if dash else 8)) % 2
        dst.fill(col("black"), (cx - 4 + step, y + 15, 3, 1))
        dst.fill(col("black"), (cx + 2 - step, y + 15, 3, 1))


def liddy(dst, x, y, t, flip=False, angry=False, trapped=False, lid=True):
    """LIDDY: a teal puff hiding under a pot lid. The first bubble knocks the lid off."""
    fluff(dst, x, y, t, "red" if angry else "sky", "hotpink" if angry else "blue", flip, "angry", trapped)
    if lid:
        bob = 0 if trapped else int(math.sin(t * 10))
        pygame.draw.ellipse(dst, col("gray"), (x, y + 1 + bob, 16, 6))
        pygame.draw.ellipse(dst, col("darkgray"), (x, y + 1 + bob, 16, 6), 1)
        dst.fill(col("white"), (x + 3, y + 2 + bob, 5, 1))
        dst.fill(col("darkgray"), (x + 7, y - 1 + bob, 3, 2))


def sneezy(dst, x, y, t, flip=False, angry=False, trapped=False, swell=0.0):
    """SNEEZY: a pink puff with a big nose that sneezes dust balls."""
    cx, cy = x + 8, y + 9
    look = -1 if flip else 1
    r = 6 + int(swell * 2)
    bob = 0 if trapped else int(math.sin(t * 8))
    pygame.draw.circle(dst, col("red" if angry else "pink"), (cx, cy + bob), r)
    pygame.draw.circle(dst, col("hotpink"), (cx, cy + bob), r, 1)
    cute.eyes(dst, cx - look, cy - 2 + bob, 2, look, "sleepy" if swell > 0.5 else ("angry" if angry else "happy"))
    pygame.draw.circle(dst, col("hotpink" if not angry else "orange"), (cx + look * (r - 1), cy + 1 + bob), 2)
    dst.fill(col("white"), (cx + look * (r - 1), cy + bob, 1, 1))
    if not trapped:
        step = int(t * 6) % 2
        dst.fill(col("black"), (cx - 4 + step, y + 15, 3, 1))
        dst.fill(col("black"), (cx + 2 - step, y + 15, 3, 1))


def wisp(dst, x, y, t, flip=False, angry=False, trapped=False):
    """WISP: a little soot ghost that drifts through walls towards Momo."""
    cx, cy = x + 8, y + 7
    sway = int(math.sin(t * 6) * 2)
    body = "purple" if angry else "darkgray"
    pygame.draw.polygon(dst, col(body), [(cx - 5, cy), (cx + 5, cy), (cx + 2 + sway, cy + 7), (cx + sway, cy + 9),
                                         (cx - 2 + sway, cy + 6)])
    pygame.draw.circle(dst, col(body), (cx, cy), 5)
    pygame.draw.circle(dst, col("black" if not angry else "hotpink"), (cx, cy), 5, 1)
    look = -1 if flip else 1
    dst.fill(col("white"), (cx - 3 + look, cy - 1, 2, 2))
    dst.fill(col("white"), (cx + 1 + look, cy - 1, 2, 2))
    if trapped:
        dst.fill(col("black"), (cx - 1, cy + 2, 2, 1))


def critter(dst, kind, x, y, t, flip=False, angry=False, trapped=False, e=None):
    """Draw any enemy kind at the 16x16 box (x, y). e: the Enemy (for per-kind state) or None."""
    if e is not None and e.golden:
        golden(dst, x, y, t, flip, trapped)
    elif kind == "g":
        cute.grump(dst, x, y, t, flip=flip, angry=angry, trapped=trapped)
    elif kind == "f":
        cute.flutter(dst, x, y, t, flip=flip, angry=angry, trapped=trapped)
    elif kind == "b":
        boing(dst, x, y, t, flip, angry, trapped, 2 if e is not None and e.on_ground and not trapped else 0)
    elif kind == "z":
        zoomy(dst, x, y, t, flip, angry, trapped, e is not None and e.mode == "dash", e is not None and e.mode == "rev")
    elif kind == "s":
        liddy(dst, x, y, t, flip, angry, trapped, e is None or e.lid)
    elif kind == "p":
        sneezy(dst, x, y, t, flip, angry, trapped, e.swell if e is not None and not trapped else 0.0)
    else:
        wisp(dst, x, y, t, flip, angry, trapped)


# ----------------------------------------------------------------------------- bosses (centre x, y)
def _c(name, flash):
    return col("white" if flash else name)


def king(dst, cx, cy, t, squash=0.0, flash=False, phase=1):
    """KING FLUFF: a giant crowned dust bunny."""
    rw, rh = int(14 + squash * 5), int(13 - squash * 5)
    for i in range(12):
        a = i * math.tau / 12 + t * 0.8
        pygame.draw.circle(dst, _c("darkgray" if phase < 3 else "hotpink", flash),
                           (int(cx + math.cos(a) * rw), int(cy + math.sin(a) * rh)), 5)
    pygame.draw.ellipse(dst, _c("gray" if phase < 3 else "red", flash), (cx - rw, cy - rh, rw * 2, rh * 2))
    for side in (-1, 1):   # bunny ears
        pygame.draw.ellipse(dst, _c("gray", flash), (cx + side * 7 - 3, cy - rh - 12, 6, 13))
        pygame.draw.ellipse(dst, _c("pink", flash), (cx + side * 7 - 1, cy - rh - 9, 2, 8))
    top = cy - rh - 2
    pygame.draw.polygon(dst, _c("yellow", flash), [(cx - 8, top + 4), (cx - 8, top - 4), (cx - 4, top), (cx, top - 6),
                                                   (cx + 4, top), (cx + 8, top - 4), (cx + 8, top + 4)])
    dst.fill(_c("red", flash), (cx - 1, top - 1, 3, 3))
    cute.eyes(dst, cx, cy - 2, 6, 0, "angry", size=2)
    cute.mouth(dst, cx, cy + 4, "angry")
    cute.blush(dst, cx, cy + 2, 8)


def mop(dst, cx, cy, t, lift=0.0, flash=False, walk=0.0, phase=1):
    """MOP TITAN: a bucket golem swinging a giant mop. lift 0 rest .. 1 raised high, -1 slammed down."""
    step = int(walk * 6) % 2
    dst.fill(_c("darkgray", flash), (cx - 9, cy + 13 - step, 6, 5))
    dst.fill(_c("darkgray", flash), (cx + 3, cy + 13 - (1 - step), 6, 5))
    pygame.draw.polygon(dst, _c("sky" if phase < 3 else "lavender", flash),
                        [(cx - 14, cy - 10), (cx + 14, cy - 10), (cx + 10, cy + 14), (cx - 10, cy + 14)])
    dst.fill(_c("blue", flash), (cx - 12, cy + 2, 24, 3))
    dst.fill(_c("white", flash), (cx - 15, cy - 12, 30, 3))
    dst.fill(_c("gray", flash), (cx - 15, cy - 9, 30, 1))
    cute.eyes(dst, cx, cy - 4, 5, 0, "angry", size=2)
    cute.mouth(dst, cx, cy + 6, "angry")
    # the mop
    hx, hy = cx + 15, cy - 2
    if lift >= 0:
        tx, ty = hx + int(8 - lift * 8), hy - 22 - int(lift * 8)
    else:
        tx, ty = hx + 22, hy + 14
    pygame.draw.line(dst, _c("brown", flash), (hx, hy), (tx, ty), 2)
    for i in range(-3, 4):
        ex = tx + i * 2 + (int(math.sin(t * 9 + i)) if lift < 0.5 else 0)
        ey = ty - 7 if lift >= 0 else ty + 6
        pygame.draw.line(dst, _c("cream", flash), (tx, ty), (ex, ey), 1)
    pygame.draw.circle(dst, _c("cream", flash), (tx, ty), 3)


def vac(dst, cx, cy, t, inhale=0.0, flash=False, phase=1):
    """WHIRL CLOUD: a grumpy storm puff with a vacuum-nozzle mouth."""
    shade = "gray" if phase < 3 else "purple"
    for dx, dy, r in ((-11, 3, 9), (11, 3, 9), (0, 5, 10)):
        pygame.draw.circle(dst, _c(shade, flash), (cx + dx, cy + dy), r)
    for dx, dy, r in ((-11, 0, 9), (11, 0, 9), (0, -6, 11), (0, 2, 10)):
        pygame.draw.circle(dst, _c("lavender", flash), (cx + dx, cy + dy), r)
    cute.eyes(dst, cx, cy - 4, 5, 0, "angry", size=2)
    mr = 3 + int(inhale * 3)
    pygame.draw.circle(dst, col("night"), (cx, cy + 6), mr)
    pygame.draw.circle(dst, _c("darkgray", flash), (cx, cy + 6), mr, 1)
    if inhale > 0:
        for i in range(6):
            a = i * math.tau / 6 - t * 7
            r1 = 14 + (t * 40 + i * 5) % 12
            x1, y1 = cx + math.cos(a) * r1, cy + 6 + math.sin(a) * r1
            pygame.draw.line(dst, col("white"), (int(x1), int(y1)), (int(x1 + math.cos(a + 1.2) * 3), int(y1 + math.sin(a + 1.2) * 3)))


def sock_seg(dst, x, y, i, flash=False):
    c = ("hotpink", "white")[i % 2]
    pygame.draw.circle(dst, _c(c, flash), (x, y), 6)
    pygame.draw.circle(dst, _c("purple", flash), (x, y), 6, 1)


def sock_head(dst, cx, cy, t, face=1, lunge=False, flash=False):
    """SOCK SERPENT's head: a striped sock cuff with a big face."""
    pygame.draw.circle(dst, _c("hotpink", flash), (cx, cy), 8)
    dst.fill(_c("white", flash), (cx - 7, cy - 3, 15, 2))
    pygame.draw.circle(dst, _c("purple", flash), (cx, cy), 8, 1)
    cute.eyes(dst, cx + face, cy - 2, 3, face, "angry" if not lunge else "wow", size=1)
    if lunge:
        pygame.draw.line(dst, col("red"), (cx + face * 4, cy + 4), (cx + face * 9, cy + 5 + int(math.sin(t * 30) * 2)))
    else:
        cute.mouth(dst, cx + face, cy + 3, "angry")


def soot(dst, cx, cy, t, charge=0.0, flash=False, phase=1):
    """SOOT STORM: a sulky black rain cloud with glowing eyes."""
    for dx, dy, r in ((-12, 2, 9), (12, 2, 9), (0, -5, 12), (-5, 4, 9), (6, 4, 9)):
        pygame.draw.circle(dst, _c("darkgray" if phase < 3 else "purple", flash), (cx + dx, cy + dy), r)
    for dx, dy, r in ((-12, 0, 7), (0, -7, 9), (12, 0, 7)):
        pygame.draw.circle(dst, _c("gray", flash), (cx + dx, cy + dy), r)
    for side in (-1, 1):
        dst.fill(col("yellow"), (cx + side * 5 - 1, cy - 3, 3, 3))
        dst.fill(col("black"), (cx + side * 5 - 2 + (1 if side < 0 else 0), cy - 5, 3, 1))
    dst.fill(col("black"), (cx - 3, cy + 4, 7, 1))
    if charge > 0 and int(t * 12) % 2:
        pygame.draw.polygon(dst, col("yellow"), [(cx - 2, cy - 18), (cx + 4, cy - 18), (cx, cy - 13), (cx + 3, cy - 13),
                                                 (cx - 4, cy - 6), (cx - 1, cy - 12), (cx - 4, cy - 12)])


def grime(dst, cx, cy, t, squash=0.0, flash=False, phase=1):
    """THE BIG GRIME: the boss of all dust, wearing a drain cover crown."""
    rw, rh = int(19 + squash * 6), int(17 - squash * 6)
    for i in range(14):
        a = i * math.tau / 14 - t * 0.6
        pygame.draw.circle(dst, _c("choco" if phase < 3 else "purple", flash),
                           (int(cx + math.cos(a) * rw), int(cy + math.sin(a) * rh)), 6)
    pygame.draw.ellipse(dst, _c("brown", flash), (cx - rw, cy - rh, rw * 2, rh * 2))
    for dx, dy in ((-10, 6), (9, 8), (-4, 11), (12, -2)):
        pygame.draw.circle(dst, _c("choco", flash), (cx + dx, cy + dy), 2)
    top = cy - rh - 3
    pygame.draw.ellipse(dst, _c("gray", flash), (cx - 11, top - 4, 22, 8))
    pygame.draw.ellipse(dst, _c("darkgray", flash), (cx - 11, top - 4, 22, 8), 1)
    for i in range(4):
        dst.fill(col("darkgray"), (cx - 6 + i * 4, top - 1, 2, 2))
    cute.eyes(dst, cx, cy - 3, 7, 0, "angry", size=2)
    dst.fill(col("black"), (cx - 6, cy + 5, 13, 3))
    for i in range(3):
        dst.fill(col("white"), (cx - 5 + i * 4, cy + 5, 2, 2))


# ----------------------------------------------------------------------------- items / letters
def item(dst, kind, sub, x, y, t):
    """x, y: top-left of the item's 8x8 body."""
    if kind == "snack":
        cute.fruit(dst, sub, x, y)
    elif kind == "heart":
        dst.blit(sprite("heart"), (x, y + 1))
    elif kind == "shield":
        bubble(dst, x + 4, y + 4, 5, t, "mint")
        dst.fill(col("white"), (x + 3, y + 3, 2, 2))
    else:
        sp = sprite("sh_" + kind)
        dst.blit(sp, (x + 4 - sp.get_width() // 2, y + 8 - sp.get_height()))


def letter_bubble(dst, x, y, ch, t):
    bubble(dst, x, y, 9, t, "yellow")
    draw_text(dst, ch, int(x) - 2, int(y) - 3, "yellow", outline="ink")


# ----------------------------------------------------------------------------- upgrade icons (cx, cy, t)
def icon_range(s, cx, cy, t):
    bubble(s, cx - 4, cy, 5, t)
    draw_text(s, "}", cx + 2, cy - 3, "white", shadow=None)


def icon_rate(s, cx, cy, t):
    for i in range(3):
        bubble(s, cx - 6 + i * 6, cy + (i % 2) * 2 - 1, 3, t)


def icon_trap(s, cx, cy, t):
    cute.grump(s, cx - 8, cy - 9, t, trapped=True)
    bubble(s, cx, cy, 9, t, "lavender")


def icon_speed(s, cx, cy, t):
    sp = sprite("sh_shoe")
    s.blit(sp, (cx - sp.get_width() // 2, cy - sp.get_height() // 2))
    s.fill(col("white"), (cx - 9, cy - 1, 3, 1))
    s.fill(col("white"), (cx - 10, cy + 2, 4, 1))


def icon_jump(s, cx, cy, t):
    draw_text(s, "|", cx - 6, cy - 3, "yellow", shadow=None)
    draw_text(s, "|", cx + 1, cy - 5 + int(math.sin(t * 6) * 1), "yellow", shadow=None)


def icon_heart(s, cx, cy, t):
    s.blit(sprite("heart"), (cx - 3, cy - 3))


def icon_chain(s, cx, cy, t):
    for dx, dy in ((-5, 3), (5, 3), (0, -5)):
        bubble(s, cx + dx, cy + dy, 4, t, "orange")


def icon_magnet(s, cx, cy, t):
    s.fill(col("red"), (cx - 6, cy - 5, 4, 9))
    s.fill(col("red"), (cx + 2, cy - 5, 4, 9))
    s.fill(col("red"), (cx - 6, cy + 2, 12, 4))
    s.fill(col("white"), (cx - 6, cy - 6, 4, 2))
    s.fill(col("white"), (cx + 2, cy - 6, 4, 2))


def icon_shield(s, cx, cy, t):
    s.blit(sprite("momo_idle", 0), (cx - 8, cy - 8))
    bubble(s, cx, cy, 10, t, "mint")


def icon_twin(s, cx, cy, t):
    bubble(s, cx - 3, cy + 3, 4, t)
    bubble(s, cx + 4, cy - 4, 4, t)
