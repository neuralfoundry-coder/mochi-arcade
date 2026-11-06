"""COMET KITTY art: procedurally drawn space critters, bosses, backdrops, capsules and upgrade icons.
All original designs. Mirrored in ios/MochiArcade/Games/CometKittyArt.swift."""
import math

import pygame

from mochi_arcade import cute
from mochi_arcade.arcade import rainbow
from mochi_arcade.games.comet_kitty_data import (BLOB, COMET, DART, GOLD, JELLY, METEOR, MINE, MINI, MOTH, PUFF, SHELL,
                                                 SPORE, URCHIN, WISP)
from mochi_arcade.gfx import H, W, bubble, col, draw_text, sprite

SIZES = ((12, 12), (12, 12), (16, 14), (12, 14), (12, 12), (14, 12), (14, 14), (12, 12), (14, 14), (12, 12),
         (8, 8), (8, 8), (12, 12), (14, 10))
KIND_COLORS = (("sky", "white", "blue"), ("pink", "hotpink", "white"), ("purple", "yellow", "white"),
               ("orange", "peach", "red"), ("lime", "mint", "white"), ("mint", "teal", "white"),
               ("teal", "sky", "white"), ("yellow", "orange", "red"), ("purple", "lavender", "white"),
               ("lavender", "white", "sky"), ("pink", "white", "sky"), ("gray", "red", "yellow"),
               ("brown", "peach", "choco"), ("yellow", "orange", "white"))


def acircle(s, c, a, cx, cy, r):
    """Translucent filled circle (c: rgb tuple or palette name)."""
    if r < 1:
        return
    tmp = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
    pygame.draw.circle(tmp, col(c, a), (r, r), r)
    s.blit(tmp, (cx - r, cy - r))


def dark(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))


# ----------------------------------------------------------------------------- backdrop
def _disc(s, x, y, r, c, stripe=None):
    """Planet disc lit from the upper left: the lower-right rim falls into shade (stripe: banded giant)."""
    for dy in range(-r, r + 1):
        hw = int(math.sqrt(max(0, r * r - dy * dy)))
        cc = c if stripe is None or ((dy + r) // 5) % 2 == 0 else stripe
        s.fill(cc, (x - hw, y + dy, hw * 2 + 1, 1))
        sx = x + int(hw * 0.35) - dy // 3
        if sx < x + hw:
            s.fill(dark(cc, 0.62), (sx, y + dy, x + hw - sx + 1, 1))


def _ring(s, x, y, a, b, c, front):
    for i in range(0, 180, 3):
        ang = math.radians(i if front else i + 180)
        s.fill(c, (x + int(math.cos(ang) * a), y + int(math.sin(ang) * b), 2, 1))


def make_backdrop(theme):
    s = pygame.Surface((W, H))
    top, bot = theme["top"], theme["bot"]
    for i in range(25):
        f = i / 24
        s.fill((int(top[0] + (bot[0] - top[0]) * f), int(top[1] + (bot[1] - top[1]) * f),
                int(top[2] + (bot[2] - top[2]) * f)), (0, i * 8, W, 8))
    for x, y, r, c, a in theme["neb"]:
        for i in range(5):     # soft glow: stacked faint discs
            acircle(s, tuple(c), a // 3, x, y, r * (5 - i) // 5)
    kind, x, y, r, c1, c2 = theme["planet"]
    c1, c2 = tuple(c1), tuple(c2)
    for rx, ry, rr in theme["rocks"]:
        pygame.draw.circle(s, dark(c1, 0.8), (rx, ry), rr)
        s.fill(c2, (rx - 1, ry - rr, 1, 1))
    if kind == 1:
        acircle(s, c1, 30, x, y, r + 5)
        _disc(s, x, y, r, c1)
        for dx, dy, rr in ((-r // 3, -r // 4, r // 4), (r // 4, r // 5, r // 5), (-r // 6, r // 2, r // 6), (r // 5, -r // 2, r // 7 + 1)):
            pygame.draw.circle(s, dark(c1, 0.8), (x + dx, y + dy), max(1, rr))
    elif kind == 2:
        _ring(s, x, y, r * 19 // 10, r * 9 // 20, c2, False)
        _disc(s, x, y, r, c1)
        _ring(s, x, y, r * 19 // 10, r * 9 // 20, c2, True)
    elif kind == 3:
        _disc(s, x, y, r, c1, c2)
    elif kind == 4:
        _disc(s, x, y, r, c1)
        _disc(s, x + r + 10, y + r // 2 + 6, r // 2, c2)
    elif kind == 5:
        acircle(s, c1, 26, x, y, r * 12 // 5)
        acircle(s, c1, 40, x, y, r * 8 // 5)
        pygame.draw.circle(s, c1, (x, y), r)
        pygame.draw.circle(s, c2, (x, y), r * 7 // 10)
    return s


# ----------------------------------------------------------------------------- enemies
def enemy(s, kind, x, y, t, hit=False, glow=False, faded=False, hp=1, d=1):
    """Draw an enemy centred at (x, y). glow: about to fire, faded: wisp out of phase, d: gold comet heading."""
    k = col("black")
    if kind in (JELLY, MOTH, PUFF):
        w, h = SIZES[kind]
        cute.space_jelly(s, x - w // 2, y - h // 2, t, kind, hit)
    elif kind == DART:
        body = col("white" if hit else "orange")
        pygame.draw.polygon(s, col("peach"), [(x - 6, y - 2), (x - 2, y - 7), (x - 2, y)])
        pygame.draw.polygon(s, col("peach"), [(x + 6, y - 2), (x + 2, y - 7), (x + 2, y)])
        pygame.draw.polygon(s, body, [(x - 3, y - 5), (x, y - 9), (x + 3, y - 5)])
        pygame.draw.ellipse(s, body, (x - 4, y - 7, 9, 11))
        pygame.draw.ellipse(s, k, (x - 4, y - 7, 9, 11), 1)
        for i in range(3):
            wig = int(math.sin(t * 12 + i) * 1)
            s.fill(col("red"), (x - 3 + i * 3 + wig, y + 3, 1, 4))
        cute.eyes(s, x, y - 2, 2, 0, "angry")
        if glow and int(t * 14) % 2:
            pygame.draw.circle(s, col("yellow"), (x, y), 9, 1)
    elif kind == SPORE:
        if glow:
            pygame.draw.circle(s, col("yellow" if int(t * 16) % 2 else "white"), (x, y), 8, 1)
        s.fill(col("mint"), (x, y - 7, 1, 2))
        s.fill(col("mint"), (x - 7, y, 2, 1))
        s.fill(col("mint"), (x + 6, y, 2, 1))
        pygame.draw.circle(s, col("white" if hit else "lime"), (x, y), 5)
        pygame.draw.circle(s, k, (x, y), 5, 1)
        s.fill(col("teal"), (x - 3, y - 3, 2, 1))
        s.fill(col("teal"), (x + 2, y - 3, 1, 2))
        cute.eyes(s, x, y, 2, 0, "wow" if glow else "happy")
    elif kind == BLOB:
        wob = int(math.sin(t * 6) * 1)
        r = (x - 7 - wob, y - 5 + wob, 14 + 2 * wob, 11 - wob)
        pygame.draw.ellipse(s, col("white" if hit else "mint"), r)
        pygame.draw.ellipse(s, k, r, 1)
        s.fill(col("white"), (x - 4, y - 3, 2, 1))
        cute.eyes(s, x, y, 3, 0, "happy")
        cute.blush(s, x, y + 2, 3)
    elif kind == SHELL:
        s.fill(col("mint"), (x - 5, y + 3, 2, 2))
        s.fill(col("mint"), (x + 4, y + 3, 2, 2))
        pygame.draw.circle(s, col("white" if hit else "teal"), (x, y), 4)
        pygame.draw.circle(s, k, (x, y), 4, 1)
        cute.eyes(s, x, y - 1, 2, 0, "angry" if hp <= 1 else "happy")
        if hp > 1:
            bubble(s, x, y, 7, t, "sky")
    elif kind == COMET:
        fl = int(t * 20) % 2
        pygame.draw.polygon(s, col("red"), [(x - 4, y), (x, y - 9 - fl * 2), (x + 4, y)])
        pygame.draw.polygon(s, col("orange"), [(x - 3, y), (x, y - 6 - fl), (x + 3, y)])
        pygame.draw.circle(s, col("white" if hit else "yellow"), (x, y + 1), 4)
        pygame.draw.circle(s, k, (x, y + 1), 4, 1)
        cute.eyes(s, x, y + 1, 2, 0, "angry")
    elif kind == URCHIN:
        for i in range(8):
            a = t * 2 + i * math.pi / 4
            pygame.draw.line(s, col("lavender"), (x, y), (x + int(math.cos(a) * 7), y + int(math.sin(a) * 7)))
        pygame.draw.circle(s, col("white" if hit else "purple"), (x, y), 5)
        pygame.draw.circle(s, k, (x, y), 5, 1)
        cute.eyes(s, x, y, 2, 0, "angry")
    elif kind == WISP:
        c = col("white" if hit else "lavender")
        if faded:
            pygame.draw.circle(s, c, (x, y - 1), 5, 1)
            for i in range(3):
                s.fill(c, (x - 5 + i * 4, y + 4, 2, 1))
            cute.eyes(s, x, y - 1, 2, 0, "sleepy")
        else:
            pygame.draw.circle(s, c, (x, y - 1), 5)
            s.fill(c, (x - 5, y - 1, 11, 5))
            for i in range(3):
                s.fill(c, (x - 5 + i * 4 + (int(t * 8) + i) % 2, y + 4, 3, 2))
            cute.eyes(s, x, y - 1, 2, 0, "happy")
            cute.mouth(s, x, y + 2, "wow")
    elif kind == MINI:
        pygame.draw.circle(s, col("white" if hit else "pink"), (x, y), 3)
        s.fill(k, (x - 2, y - 1, 1, 2))
        s.fill(k, (x + 1, y - 1, 1, 2))
    elif kind == MINE:
        s.fill(col("gray"), (x - 1, y - 5, 2, 10))
        s.fill(col("gray"), (x - 5, y - 1, 10, 2))
        pygame.draw.circle(s, col("darkgray"), (x, y), 3)
        s.fill(col("red" if glow else "yellow"), (x - 1, y - 1, 2, 2))
    elif kind == METEOR:
        pygame.draw.circle(s, col("white" if hit else "brown"), (x, y), 6)
        pygame.draw.circle(s, col("choco"), (x, y), 6, 1)
        pygame.draw.circle(s, col("choco"), (x - 2, y - 1), 2)
        pygame.draw.circle(s, col("choco"), (x + 2, y + 3), 1)
        s.fill(col("peach"), (x - 3, y - 4, 2, 1))
    elif kind == GOLD:
        for i in range(6):
            s.fill(col(rainbow(i, t)), (x - d * (6 + i * 3) - 1, y - 2 + i % 2, 3, 3))
        pygame.draw.circle(s, col("orange"), (x, y), 6)
        pygame.draw.circle(s, col("white" if hit else "yellow"), (x, y), 5)
        s.fill(col("white"), (x - 2, y - 3, 2, 2))
        cute.eyes(s, x, y, 2, 0, "happy")
        if int(t * 10) % 2:
            s.fill(col("white"), (x + d * 7, y - 6, 1, 3))
            s.fill(col("white"), (x + d * 7 - 1, y - 5, 3, 1))


def capsule(s, kind, x, y, t):
    """Power capsules (P F B S $), the lucky star (L) and score medals (M)."""
    if kind == "M":
        w = max(1, int(abs(math.cos(t * 6)) * 4))
        pygame.draw.rect(s, col("orange"), (x - w, y - 4, w * 2 + 1, 9))
        pygame.draw.rect(s, col("yellow"), (x - w + 1, y - 3, max(1, w * 2 - 1), 7))
        if w >= 3:
            s.fill(col("white"), (x, y - 2, 1, 5))
        return
    if kind == "L":
        for i in range(5):
            a = t * 4 + i * math.tau / 5
            s.fill(col(rainbow(i, t)), (x + int(math.cos(a) * 7), y + int(math.sin(a) * 7), 2, 2))
        s.blit(sprite("star"), (x - 3, y - 3))
        return
    c = {"P": "yellow", "F": "pink", "B": "red", "S": "mint", "$": "orange"}[kind]
    pygame.draw.rect(s, col("black"), (x - 6, y - 4, 13, 10), border_radius=3)
    pygame.draw.rect(s, col(c), (x - 6, y - 5, 13, 10), border_radius=3)
    pygame.draw.rect(s, col("white" if int(t * 6) % 2 else c), (x - 6, y - 5, 13, 10), 1, border_radius=3)
    draw_text(s, kind, x - 2, y - 3, "ink", shadow=None)


# ----------------------------------------------------------------------------- bosses
def _reticle(s, x, y, r, t):
    """Weak-spot marker: four blinking corner ticks."""
    c = col("yellow" if int(t * 4) % 2 else "white")
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = x + sx * r, y + sy * r
            s.fill(c, (px - (1 if sx > 0 else 0), py, 2, 1))
            s.fill(c, (px, py - (1 if sy > 0 else 0), 1, 2))


def boss(s, b, x, y, t, parts, look):
    """Draw boss b centred at (x, y). parts: [(x, y, r, alive, flash, front)], look: -2..2 eye direction."""
    k = col("black")
    hit = b.flash > 0 and int(t * 30) % 3 == 0
    angry = b.phase >= 1
    mood = "angry" if angry else "happy"
    blink = int(t * 1.3) % 6 == 0 and not angry
    attacking = b.atk is not None and b.atk != "teleport"
    if b.kind == 0:      # MOCHI MOON
        pygame.draw.circle(s, col("ink"), (x, y + 1), 24)
        pygame.draw.circle(s, col("peach"), (x, y + 1), 22)
        pygame.draw.circle(s, col("white" if hit else "cream"), (x, y), 21)
        for dx, dy, r in ((-12, -9, 4), (12, -6, 3), (7, -15, 2), (-15, 5, 2)):
            pygame.draw.circle(s, col("peach"), (x + dx, y + dy), r)
        pygame.draw.circle(s, col("white"), (x - 8, y - 13), 2)
        pygame.draw.polygon(s, col("lime"), [(x, y - 20), (x + 9, y - 28), (x + 3, y - 19)])
        s.fill(col("teal"), (x, y - 23, 1, 4))
        cute.eyes(s, x, y - 2, 8, look, mood, blink, 2)
        s.fill(col("pink"), (x - 17, y + 3, 4, 2))
        s.fill(col("pink"), (x + 14, y + 3, 4, 2))
        if attacking:
            pygame.draw.ellipse(s, k, (x - 6, y + 6, 12, 9))
            pygame.draw.ellipse(s, col("hotpink"), (x - 3, y + 10, 6, 4))
        else:
            cute.mouth(s, x, y + 8, mood)
    elif b.kind == 1:    # STAR SQUID
        for px, py, r, alive, fl, _ in parts:
            ex, ey = (px, py) if alive else (x + (px - x) // 2, y + 10)
            pygame.draw.line(s, col("purple"), (x + (px - x) // 3, y + 8), (ex, ey), 2)
            if alive:
                pygame.draw.circle(s, col("white" if fl > 0 else "lavender"), (px, py), r)
                pygame.draw.circle(s, k, (px, py), r, 1)
                s.fill(col("pink"), (px - 1, py + 1, 2, 2))
        pygame.draw.polygon(s, col("purple"), [(x - 11, y - 10), (x, y - 26), (x + 11, y - 10)])
        pygame.draw.ellipse(s, col("lavender"), (x - 24, y - 16, 10, 12))
        pygame.draw.ellipse(s, col("lavender"), (x + 14, y - 16, 10, 12))
        pygame.draw.ellipse(s, col("white" if hit else "purple"), (x - 16, y - 16, 32, 32))
        pygame.draw.ellipse(s, k, (x - 16, y - 16, 32, 32), 1)
        for dx, dy in ((-8, -8), (6, -11), (9, -2), (-11, 1), (0, -18)):
            s.fill(col("yellow"), (x + dx, y + dy, 1, 1))
        pygame.draw.circle(s, col("white"), (x, y + 6), 7)
        pygame.draw.circle(s, k, (x, y + 6), 7, 1)
        pygame.draw.circle(s, col("red" if angry else "black"), (x + look, y + 7), 3)
        s.fill(col("white"), (x + look - 1, y + 5, 1, 1))
        if angry:
            pygame.draw.line(s, k, (x - 7, y - 3), (x - 2, y - 1))
            pygame.draw.line(s, k, (x + 7, y - 3), (x + 2, y - 1))
    elif b.kind == 2:    # COMET WHALE
        f = b.face
        pygame.draw.polygon(s, col("blue"), [(x - f * 26, y - 2), (x - f * 40, y - 13), (x - f * 35, y),
                                             (x - f * 40, y + 10)])
        pygame.draw.ellipse(s, col("white" if hit else "blue"), (x - 30, y - 14, 60, 28))
        pygame.draw.ellipse(s, col("sky"), (x - 24, y - 1, 46, 14))
        pygame.draw.ellipse(s, k, (x - 30, y - 14, 60, 28), 1)
        for i in range(4):
            s.fill(col("white"), (x - 12 + i * 7, y + 3, 4, 1))
        s.fill(k, (x + f * 17 - 1, y - 5, 2, 3))
        s.fill(col("white"), (x + f * 17 - (1 if f > 0 else 0), y - 5, 1, 1))
        s.fill(col("pink"), (x + f * 20 - 1, y + 1, 3, 1))
        if angry:
            pygame.draw.line(s, k, (x + f * 14, y - 9), (x + f * 20, y - 7))
        sx = x + f * 4
        if b.atk == "rain" or int(t * 3) % 3 == 0:
            for i in range(5):
                a = -math.pi / 2 + (i - 2) * 0.35
                rr = 6 + int(t * 30 + i * 3) % 8
                s.fill(col("sky" if i % 2 else "white"), (sx + int(math.cos(a) * rr), y - 14 + int(math.sin(a) * rr), 2, 2))
        wx = x + b.weak[0] * f
        pygame.draw.polygon(s, col("yellow"), [(wx, y + 3), (wx + 2, y + 7), (wx + 6, y + 7), (wx + 3, y + 10),
                                               (wx + 4, y + 14), (wx, y + 11), (wx - 4, y + 14), (wx - 3, y + 10),
                                               (wx - 6, y + 7), (wx - 2, y + 7)])
    elif b.kind == 3:    # NEBULA CRAB
        for side in (-1, 1):
            for i in range(3):
                wig = int(math.sin(t * 8 + i + side) * 2)
                pygame.draw.line(s, col("red"), (x + side * (8 + i * 5), y + 8), (x + side * (14 + i * 6), y + 18 + wig), 2)
        for px, py, r, alive, fl, _ in parts:
            pygame.draw.line(s, col("red"), (x + (8 if px > x else -8), y), (px if alive else (x + px) // 2, py), 3)
            if alive:
                pygame.draw.circle(s, col("white" if fl > 0 else "red"), (px, py), r)
                pygame.draw.circle(s, k, (px, py), r, 1)
                pygame.draw.polygon(s, col("ink"), [(px - 3, py - r - 1), (px, py - 1), (px + 3, py - r - 1)])
                s.fill(col("peach"), (px - 5, py + 1, 2, 2))
        pygame.draw.line(s, k, (x - 6, y - 10), (x - 9, y - 19))
        pygame.draw.line(s, k, (x + 6, y - 10), (x + 9, y - 19))
        pygame.draw.ellipse(s, col("white" if hit else "red"), (x - 20, y - 12, 40, 26))
        pygame.draw.ellipse(s, k, (x - 20, y - 12, 40, 26), 1)
        for dx in (-10, 0, 10):
            s.fill(col("peach"), (x + dx - 1, y - 8, 3, 2))
        for side in (-1, 1):
            pygame.draw.circle(s, col("white"), (x + side * 9, y - 20), 3)
            s.fill(k, (x + side * 9 + look // 2, y - 21, 1, 2))
        cute.mouth(s, x, y + 6, "angry" if angry else "wow")
    elif b.kind == 4:    # RING GRUMP
        for px, py, r, alive, fl, front in parts:
            if alive and not front:
                pygame.draw.circle(s, col("gray"), (px, py), r - 1)
        _ring(s, x, y + 4, 36, 11, col("yellow"), False)
        _disc(s, x, y, 18, col("white") if hit else col("orange"), col("peach"))
        pygame.draw.circle(s, k, (x, y), 18, 1)
        cute.eyes(s, x, y - 1, 6, look, "angry", blink, 2)
        cute.mouth(s, x, y + 9, "angry")
        _ring(s, x, y + 4, 36, 11, col("yellow"), True)
        for px, py, r, alive, fl, front in parts:
            if alive and front:
                pygame.draw.circle(s, col("white" if fl > 0 else "lavender"), (px, py), r)
                pygame.draw.circle(s, k, (px, py), r, 1)
                cute.eyes(s, px, py, 2, 0, "sleepy")
    else:                # VOID PUFF / ABYSS PUFF
        body = col("white" if hit else ("ink" if not b.final else "night"))
        rim = col("red" if b.final else "purple")
        for i, (dx, dy, r) in enumerate(((0, -6, 18), (-17, 1, 12), (17, 1, 12), (-10, 10, 11), (10, 10, 11))):
            wob = int(math.sin(t * 3 + i) * 1)
            pygame.draw.circle(s, rim, (x + dx, y + dy + wob), r + 1)
        for i, (dx, dy, r) in enumerate(((0, -6, 18), (-17, 1, 12), (17, 1, 12), (-10, 10, 11), (10, 10, 11))):
            wob = int(math.sin(t * 3 + i) * 1)
            pygame.draw.circle(s, body, (x + dx, y + dy + wob), r)
        for i, (dx, dy) in enumerate(((-10, -12), (8, -14), (-20, 0), (18, -2), (-4, -2), (12, 6), (-14, 8))):
            if int(t * 2 + i * 1.7) % 5 != 0:
                s.fill(col("white"), (x + dx, y + dy, 3, 2))
                s.fill(k, (x + dx + 1 + (1 if look > 0 else 0) - (1 if look < 0 else 0), y + dy, 1, 2))
        pulse = int(math.sin(t * 6) * 1.5)
        pygame.draw.circle(s, col("black"), (x, y + 10), 8 + pulse)
        pygame.draw.circle(s, col("hotpink"), (x, y + 10), 6 + pulse)
        pygame.draw.circle(s, col("white"), (x, y + 10), 2)
        if b.final:
            pygame.draw.polygon(s, col("yellow"), [(x - 10, y - 22), (x - 7, y - 31), (x - 3, y - 24), (x, y - 33),
                                                   (x + 3, y - 24), (x + 7, y - 31), (x + 10, y - 22)])
            s.fill(col("red"), (x - 1, y - 28, 2, 2))
    if b.state == "fight":
        wx, wy, wr = b.weak_pos()
        _reticle(s, int(wx), int(wy), wr + 2, t)


# ----------------------------------------------------------------------------- upgrade card icons
def icon(uid):
    def f(s, cx, cy, t):
        if uid == "spread":
            for dx in (-6, 0, 6):
                pygame.draw.line(s, col("yellow"), (cx, cy + 6), (cx + dx, cy - 6), 2)
        elif uid == "rapid":
            for i in range(3):
                s.fill(col("yellow"), (cx - 1, cy - 8 + i * 6 + int(t * 12) % 6, 3, 4))
        elif uid == "lance":
            s.fill(col("sky"), (cx - 2, cy - 9, 5, 18))
            s.fill(col("white"), (cx - 1, cy - 9, 3, 18))
        elif uid == "seeker":
            pygame.draw.line(s, col("lime"), (cx - 7, cy + 7), (cx - 5, cy))
            pygame.draw.line(s, col("lime"), (cx - 5, cy), (cx - 1, cy - 4))
            pygame.draw.line(s, col("lime"), (cx - 1, cy - 4), (cx + 3, cy - 5))
            s.blit(sprite("star"), (cx + 1, cy - 9))
        elif uid == "pals":
            s.blit(sprite("star"), (cx - 9, cy - 3))
            s.blit(sprite("star"), (cx + 3, cy - 3))
            s.blit(sprite("heart"), (cx - 3, cy - 9))
        elif uid == "shield":
            bubble(s, cx, cy, 8, t, "mint")
        elif uid == "zoom":
            s.blit(sprite("kitty"), (cx - 8, cy - 8))
            for i in range(3):
                s.fill(col("white"), (cx - 11 + int(t * 20 + i * 4) % 6, cy - 4 + i * 4, 3, 1))
        elif uid == "focus":
            s.fill(col("lavender"), (cx - 9, cy, 18, 1))
            s.fill(col("lavender"), (cx, cy - 9, 1, 18))
            s.blit(sprite("heart"), (cx - 3, cy - 3))
        elif uid == "bombs":
            pygame.draw.circle(s, col("red"), (cx - 1, cy + 2), 6)
            s.fill(col("white"), (cx - 4, cy - 1, 2, 2))
            pygame.draw.line(s, col("peach"), (cx + 3, cy - 3), (cx + 6, cy - 7))
            if int(t * 8) % 2:
                s.fill(col("yellow"), (cx + 5, cy - 9, 3, 3))
        elif uid == "magnet":
            pygame.draw.circle(s, col("red"), (cx, cy - 1), 7, 3)
            s.fill(col("ink"), (cx - 8, cy, 17, 8))
            s.fill(col("red"), (cx - 7, cy - 1, 3, 6))
            s.fill(col("red"), (cx + 5, cy - 1, 3, 6))
            s.fill(col("white"), (cx - 7, cy + 4, 3, 2))
            s.fill(col("white"), (cx + 5, cy + 4, 3, 2))
    return f
