"""Procedurally drawn cute critters, food and blocks (original designs for MOCHI ARCADE)."""
import math

import pygame

from mochi_arcade.gfx import col


def eyes(dst, cx, cy, gap, look=0, mood="happy", blink=False, size=1):
    """Two eyes centred at (cx, cy). look: -1 left .. 1 right. mood: happy|angry|wow|sleepy."""
    k = col("black")
    for side in (-1, 1):
        ex = int(cx + side * gap + look)
        if blink or mood == "sleepy":
            dst.fill(k, (ex - size, cy, size * 2 + 1, 1))
            continue
        if mood == "wow":
            pygame.draw.circle(dst, col("white"), (ex, cy), size + 1)
            dst.fill(k, (ex, cy, 1, 1))
            continue
        dst.fill(k, (ex - (size - 1), cy - size, size + (size - 1), size * 2))
        dst.fill(col("white"), (ex, cy - size, 1, 1))
        if mood == "angry":  # slanted brows
            for i in range(3):
                bx = ex - 1 + i if side < 0 else ex + 1 - i
                dst.fill(k, (bx, cy - size - 2 + (i if side < 0 else i), 1, 1))


def mouth(dst, cx, cy, mood="happy"):
    k = col("black")
    if mood == "happy":
        dst.fill(k, (cx - 1, cy, 1, 1)); dst.fill(k, (cx, cy + 1, 1, 1)); dst.fill(k, (cx + 1, cy, 1, 1))
    elif mood == "angry":
        dst.fill(k, (cx - 1, cy + 1, 3, 1)); dst.fill(k, (cx - 2, cy + 2, 1, 1)); dst.fill(k, (cx + 2, cy + 2, 1, 1))
    elif mood == "wow":
        pygame.draw.circle(dst, k, (cx, cy + 1), 1)
    else:
        dst.fill(k, (cx - 1, cy, 3, 1))


def blush(dst, cx, cy, gap):
    p = col("pink")
    dst.fill(p, (cx - gap - 2, cy, 2, 1))
    dst.fill(p, (cx + gap + 1, cy, 2, 1))


def grump(dst, x, y, t, flip=False, angry=False, trapped=False):
    """Dust grump: a fluffy grey puff with tiny feet (Soap Hop enemy). (x, y) = top-left of 16x16."""
    body = col("red" if angry else "gray")
    dark = col("hotpink" if angry else "darkgray")
    cx, cy = x + 8, y + 9
    bob = int(math.sin(t * 10) * 1) if not trapped else 0
    # fluff
    for a in range(0, 360, 40):
        r = math.radians(a + t * 60)
        pygame.draw.circle(dst, dark, (int(cx + math.cos(r) * 6), int(cy + bob + math.sin(r) * 5)), 3)
    pygame.draw.circle(dst, body, (cx, cy + bob), 6)
    look = -1 if flip else 1
    eyes(dst, cx, cy - 1 + bob, 3, look, "angry", blink=int(t * 2) % 7 == 0)
    mouth(dst, cx + look, cy + 2 + bob, "angry")
    if not trapped:
        step = int(t * 8) % 2
        dst.fill(col("black"), (cx - 4 + step, y + 15, 3, 1))
        dst.fill(col("black"), (cx + 2 - step, y + 15, 3, 1))


def flutter(dst, x, y, t, flip=False, angry=False, trapped=False):
    """Puff-moth: round lavender bug with flapping wings (Soap Hop flying enemy)."""
    cx, cy = x + 8, y + 8
    flap = math.sin(t * 18)
    wing = col("hotpink" if angry else "sky")
    for side in (-1, 1):
        wx = cx + side * (5 + int(abs(flap) * 1))
        pygame.draw.ellipse(dst, wing, (wx - 3, cy - 6 + int(flap * 2), 6, 7))
        pygame.draw.ellipse(dst, col("white"), (wx - 2, cy - 5 + int(flap * 2), 2, 2))
    pygame.draw.circle(dst, col("red" if angry else "lavender"), (cx, cy), 5)
    pygame.draw.circle(dst, col("black"), (cx, cy), 5, 1)
    look = -1 if flip else 1
    eyes(dst, cx, cy - 1, 2, look, "angry" if angry else "wow" if trapped else "happy")
    dst.fill(col("black"), (cx - 3, cy - 7, 1, 2)); dst.fill(col("black"), (cx + 3, cy - 7, 1, 2))


def fruit(dst, kind, x, y):
    """8x8-ish snacks. kind: 0 cherry 1 strawberry 2 melon 3 candy 4 cake 5 donut 6 icecream 7 onigiri"""
    k = col("black")
    if kind == 0:
        pygame.draw.line(dst, col("lime"), (x + 4, y), (x + 2, y + 4))
        pygame.draw.line(dst, col("lime"), (x + 4, y), (x + 6, y + 4))
        for cx in (x + 2, x + 6):
            pygame.draw.circle(dst, col("red"), (cx, y + 5), 2)
            dst.fill(col("white"), (cx - 1, y + 4, 1, 1))
    elif kind == 1:
        pygame.draw.polygon(dst, col("red"), [(x, y + 2), (x + 8, y + 2), (x + 4, y + 8)])
        pygame.draw.circle(dst, col("red"), (x + 4, y + 3), 3)
        dst.fill(col("lime"), (x + 2, y, 5, 2))
        for px, py in ((x + 2, y + 3), (x + 5, y + 3), (x + 4, y + 5)):
            dst.fill(col("yellow"), (px, py, 1, 1))
    elif kind == 2:
        pygame.draw.polygon(dst, col("lime"), [(x, y + 2), (x + 8, y + 2), (x + 4, y + 8)])
        pygame.draw.polygon(dst, col("pink"), [(x + 1, y + 2), (x + 7, y + 2), (x + 4, y + 6)])
        dst.fill(k, (x + 3, y + 3, 1, 1)); dst.fill(k, (x + 5, y + 3, 1, 1))
    elif kind == 3:
        pygame.draw.circle(dst, col("hotpink"), (x + 4, y + 4), 3)
        pygame.draw.polygon(dst, col("yellow"), [(x, y + 2), (x + 2, y + 4), (x, y + 6)])
        pygame.draw.polygon(dst, col("yellow"), [(x + 8, y + 2), (x + 6, y + 4), (x + 8, y + 6)])
        dst.fill(col("white"), (x + 3, y + 3, 1, 1))
    elif kind == 4:
        dst.fill(col("cream"), (x, y + 3, 9, 5)); dst.fill(col("pink"), (x, y + 2, 9, 2))
        dst.fill(col("red"), (x + 4, y, 2, 2)); dst.fill(col("choco"), (x, y + 6, 9, 1))
    elif kind == 5:
        pygame.draw.circle(dst, col("peach"), (x + 4, y + 4), 4)
        pygame.draw.circle(dst, col("hotpink"), (x + 4, y + 4), 4, 2)
        pygame.draw.circle(dst, col("night"), (x + 4, y + 4), 1)
    elif kind == 6:
        pygame.draw.polygon(dst, col("orange"), [(x + 1, y + 4), (x + 7, y + 4), (x + 4, y + 9)])
        pygame.draw.circle(dst, col("mint"), (x + 4, y + 3), 3)
        dst.fill(col("white"), (x + 3, y + 1, 1, 1))
    else:
        pygame.draw.polygon(dst, col("white"), [(x + 4, y), (x + 8, y + 7), (x, y + 7)])
        dst.fill(col("black"), (x + 2, y + 5, 5, 3))


def jelly_cell(dst, x, y, size, color, t=0.0, face=True, wobble=0.0, ghost=False):
    """A jelly cube with a little face. Used by Jelly Stack."""
    c = col(color)
    if ghost:
        pygame.draw.rect(dst, c, (x, y, size, size), 1, border_radius=2)
        return
    dark = tuple(max(0, v - 70) for v in c)
    light = tuple(min(255, v + 60) for v in c)
    pygame.draw.rect(dst, dark, (x, y, size, size), border_radius=2)
    pygame.draw.rect(dst, c, (x, y, size, size - 1), border_radius=2)
    dst.fill(light, (x + 1, y + 1, size - 3, 1))
    dst.fill(light, (x + 1, y + 1, 1, 2))
    if face and size >= 8:
        cx, cy = x + size // 2, y + size // 2 + int(wobble)
        blink = (int(t * 1.7 + x * 0.13 + y * 0.07) % 9) == 0
        k = col("black")
        if blink:
            dst.fill(k, (cx - 3, cy, 2, 1)); dst.fill(k, (cx + 1, cy, 2, 1))
        else:
            dst.fill(k, (cx - 2, cy - 1, 1, 2)); dst.fill(k, (cx + 1, cy - 1, 1, 2))
        dst.fill(k, (cx - 1, cy + 2, 2, 1))


def dumpling(dst, x, y, golden=False, t=0.0):
    """8x8 dumpling snack (Noodle Slurp)."""
    body = col("yellow" if golden else "cream")
    pygame.draw.ellipse(dst, body, (x, y + 2, 8, 6))
    pygame.draw.ellipse(dst, col("black"), (x, y + 2, 8, 6), 1)
    for i in range(3):
        dst.fill(col("orange" if golden else "peach"), (x + 2 + i * 2, y + 2 - (i % 2), 1, 2))
    dst.fill(col("black"), (x + 2, y + 5, 1, 1)); dst.fill(col("black"), (x + 5, y + 5, 1, 1))
    dst.fill(col("pink"), (x + 1, y + 6, 1, 1)); dst.fill(col("pink"), (x + 6, y + 6, 1, 1))
    if golden and int(t * 8) % 2:
        dst.fill(col("white"), (x + 6, y + 1, 1, 1))


def space_jelly(dst, x, y, t, kind=0, hit=False):
    """Comet Kitty enemies, 12x12. kind 0 blue jelly, 1 pink moth, 2 big boss puff (16x14)."""
    k = col("black")
    if kind == 2:
        cx, cy = x + 8, y + 7
        body = col("white" if hit else "purple")
        pygame.draw.circle(dst, body, (cx, cy), 7)
        pygame.draw.circle(dst, k, (cx, cy), 7, 1)
        crown = col("yellow")
        pygame.draw.polygon(dst, crown, [(cx - 4, cy - 6), (cx - 2, cy - 9), (cx, cy - 6), (cx + 2, cy - 9), (cx + 4, cy - 6)])
        eyes(dst, cx, cy, 3, 0, "angry" if hit else "happy")
        mouth(dst, cx, cy + 3, "angry" if hit else "happy")
        return
    if kind == 0:
        cx, cy = x + 6, y + 5
        body = col("white" if hit else "sky")
        pygame.draw.ellipse(dst, body, (x + 1, y, 10, 9))
        pygame.draw.ellipse(dst, k, (x + 1, y, 10, 9), 1)
        for i in range(4):
            wig = int(math.sin(t * 10 + i) * 1)
            dst.fill(col("blue"), (x + 2 + i * 2 + wig, y + 9, 1, 3))
        eyes(dst, cx, cy - 1, 2, 0, "happy")
        blush(dst, cx, cy + 1, 2)
        return
    cx, cy = x + 6, y + 6
    flap = int(math.sin(t * 16) * 2)
    for side in (-1, 1):
        pygame.draw.ellipse(dst, col("pink"), (cx + side * 4 - 2, cy - 4 + flap, 5, 6))
    pygame.draw.circle(dst, col("white" if hit else "hotpink"), (cx, cy), 4)
    pygame.draw.circle(dst, k, (cx, cy), 4, 1)
    eyes(dst, cx, cy - 1, 2, 0, "wow")


def brick(dst, rect, kind, hp=1, t=0.0):
    """Bounce Bun bricks: cookies, candy bars, macarons, chocolate (2 hits), steel tins (unbreakable)."""
    r = pygame.Rect(rect)
    palette = {"cookie": ("peach", "brown"), "candy": ("pink", "hotpink"), "mint": ("mint", "teal"),
               "lemon": ("yellow", "orange"), "berry": ("lavender", "purple"), "choco": ("brown", "choco"),
               "tin": ("gray", "darkgray")}
    light, dark = palette.get(kind, ("white", "gray"))
    pygame.draw.rect(dst, col(dark), r, border_radius=2)
    pygame.draw.rect(dst, col(light), r.inflate(-2, -2), border_radius=2)
    if kind == "cookie":
        for i, (dx, dy) in enumerate(((3, 2), (8, 4), (12, 2))):
            dst.fill(col("choco"), (r.x + dx, r.y + dy, 2, 1))
    elif kind == "candy":
        for i in range(3, r.w - 2, 4):
            dst.fill(col("white"), (r.x + i, r.y + 2, 2, r.h - 4))
    elif kind == "choco":
        dst.fill(col(dark), (r.centerx, r.y + 1, 1, r.h - 2))
        if hp < 2:
            pygame.draw.line(dst, col("black"), (r.x + 3, r.y + 2), (r.x + 7, r.bottom - 3))
    elif kind == "tin":
        dst.fill(col("white"), (r.x + 2, r.y + 2, r.w - 4, 1))
    else:
        dst.fill(col("white"), (r.x + 2, r.y + 2, 3, 1))
