"""ROOFTOP RUN world: course objects, Tora's physics step and the rooftop drawing helpers.

The physics step only touches the body it is given (no side effects on the world) and reports events, so the
game and the autopilot (gif bot / tests) share exactly the same movement rules. Mirrored in
ios/MochiArcade/Games/RooftopRunWorld.swift.
"""
import math

import pygame

from mochi_arcade.games.rooftop_run_course import (AIR_V, BOUNCE_V, G_DOWN, G_UP, HANG, JUMP_V, KICK_V, PAD_V,
                                                   SLIDE_H, STAND_H, THEMES, decode, fish_points)
from mochi_arcade.gfx import H, W, col, draw_text, lerp_col, sprite

CLING_V = 40.0
MAX_FALL = 430.0
POUNCE_V = 380.0
GLIDE_V = (0.0, 70.0, 45.0)
SPRINT, BRAKE = 1.22, 0.7
BILLBOARD_ADS = ["FISH!", "MEOW", "TUNA", "PURR", "NAPS", "MILK", "YARN", "SALE"]


# ----------------------------------------------------------------------------- deterministic noise (same on iOS)
def lcg(s):
    return (s * 1103515245 + 12345) & 0x7FFFFFFF


def hash2(a, b):
    return lcg(lcg(a * 7919 + 13) ^ (b * 104729 + 7)) >> 7


# ----------------------------------------------------------------------------- course objects
class Roof:
    __slots__ = ("x", "y", "w", "h", "glass", "crack", "broken", "solid")

    def __init__(self, x0, x1, y, glass):
        self.x, self.y, self.w, self.h = x0, y, x1 - x0, 400
        self.glass = glass
        self.crack = -1.0      # seconds left before a touched skylight breaks (-1: untouched)
        self.broken = False
        self.solid = "R"


class Box:
    __slots__ = ("k", "x", "y", "w", "h", "alive", "solid", "flash")

    def __init__(self, k, x, y, w, h):
        self.k, self.x, self.y, self.w, self.h = k, x, y, w, h
        self.alive = True
        self.solid = "S"
        self.flash = 0.0


class Lift:
    __slots__ = ("x", "y0", "w", "amp", "ph", "y", "h", "solid")

    def __init__(self, x, y0, w, amp, ph):
        self.x, self.y0, self.w, self.amp, self.ph = x, y0, w, amp, ph / 100.0
        self.h = 6
        self.y = float(y0)
        self.solid = "M"

    def at(self, t):
        return self.y0 + self.amp * math.sin(t * 1.5 + self.ph)


class Line:
    __slots__ = ("x0", "x1", "base", "sway", "y")

    def __init__(self, x0, x1, y, sway):
        self.x0, self.x1, self.base, self.sway = x0, x1, y, sway
        self.y = float(y)

    def at(self, t):
        return self.base + self.sway * math.sin(t * 2.2 + self.x0 * 0.01)


class Wire:
    __slots__ = ("x0", "x1", "y", "spark")

    def __init__(self, x0, x1, y, spark):
        self.x0, self.x1, self.y, self.spark = x0, x1, y, spark

    def spark_x(self, t):
        """Zaps run from the far end towards Tora."""
        span = self.x1 - self.x0 + 80
        return self.x1 - (t * 70 + self.x0 * 0.37) % span


class Haz:
    __slots__ = ("k", "x", "y", "a", "b", "x0", "y0", "t", "state", "alive", "dir", "vy", "spin")

    def __init__(self, e):
        self.k = e[0]
        self.x, self.y = float(e[1]), float(e[2])
        self.x0, self.y0 = self.x, self.y
        self.a = e[3] if len(e) > 3 else 0
        self.b = e[4] if len(e) > 4 else 0
        self.t = 0.0
        self.state = 0          # kind specific: 0 idle / waiting, 1 active, 2 done
        self.alive = True
        self.dir = -1
        self.vy = 0.0
        self.spin = 0.0

    def rect(self, stime):
        """Hurt box (x, y, w, h) or None."""
        k, x, y = self.k, self.x, self.y
        if not self.alive:
            return None
        if k == "p":
            return (x - 5, y - 9, 10, 9)
        if k == "q":
            return (x - 5, y - 3, 10, 6)
        if k == "s":
            return (x - 5, y - 30, 10, 30) if sprinkler_phase(self, stime) == 2 else None
        if k == "a":
            return (x - 2, y - self.a, 5, self.a)
        if k == "i":
            if self.state == 2:
                return (x - 3, y - 6, 7, 6)
            return (x - 3, self.y - 9, 7, 9) if self.state == 1 else None
        if k == "d":
            return (x - 7, y - 4, 14, 8) if self.state == 2 else None
        if k == "z":
            return (x - 12, y - 8, 25, 8) if self.state == 2 else None
        return None


def sprinkler_phase(h, stime):
    """0 off, 1 dripping (about to spray), 2 spraying."""
    p = (stime + h.a / 100.0) % 2.4
    return 2 if p >= 1.4 else 1 if p >= 1.0 else 0


class Course:
    """A stage's objects, sorted along x, with fast windows for physics and drawing."""

    def __init__(self, st):
        ents = decode(st["c"])
        self.roofs = sorted([Roof(e[1], e[2], e[3], e[4]) for e in ents if e[0] == "R"], key=lambda r: r.x)
        self.boxes = sorted([Box(*e[1:6]) for e in ents if e[0] == "S"], key=lambda b: b.x)
        self.lifts = [Lift(*e[1:6]) for e in ents if e[0] == "M"]
        self.lines = [Line(*e[1:5]) for e in ents if e[0] == "L"]
        self.wires = [Wire(*e[1:5]) for e in ents if e[0] == "W"]
        self.winds = [e[1:4] for e in ents if e[0] == "N"]
        self.vents = [e[1:3] for e in ents if e[0] == "V"]
        self.pads = [[e[1], e[2], 0.0] for e in ents if e[0] == "J"]
        self.fish = []
        for e in ents:
            if e[0] in "FA":
                for fx, fy in fish_points(e):
                    self.fish.append([float(fx), float(fy), False])
        self.fish.sort(key=lambda f: f[0])
        self.gold = [[float(e[1]), float(e[2]), False, False] for e in ents if e[0] == "G"]   # x, y, got, rainbow
        self.caps = [[float(e[1]), float(e[2]), e[3], False] for e in ents if e[0] == "P"]
        self.haz = [Haz(e) for e in ents if e[0] in "pqsaidz"]
        fin = [e[1] for e in ents if e[0] == "E"]
        self.finish = fin[0] if fin else 0

    def reset_consumables(self, keep_x0, keep_x1):
        """Boss arenas loop: everything outside [keep_x0, keep_x1] comes back fresh."""
        for f in self.fish:
            if not keep_x0 <= f[0] <= keep_x1:
                f[2] = False
        for r in self.roofs:
            if not keep_x0 <= r.x <= keep_x1:
                r.crack, r.broken = -1.0, False
        for b in self.boxes:
            if not keep_x0 <= b.x <= keep_x1:
                b.alive = True


class View:
    """What the physics needs around Tora: solids (roofs, boxes, lifts), lines, wires, winds, vents, pads."""

    def __init__(self, course, x0, x1, speed, t):
        self.speed, self.t = speed, t
        self.solids = [r for r in course.roofs if r.x < x1 and r.x + r.w > x0 and not r.broken]
        self.solids += [b for b in course.boxes if b.alive and b.x < x1 and b.x + b.w > x0]
        self.solids += [m for m in course.lifts if m.x < x1 and m.x + m.w > x0]
        self.lines = [ln for ln in course.lines if ln.x0 < x1 and ln.x1 > x0]
        self.wires = [w for w in course.wires if w.x0 < x1 and w.x1 > x0]
        self.winds = [z for z in course.winds if z[0] < x1 and z[1] > x0]
        self.vents = [v for v in course.vents if x0 - 20 < v[0] < x1 + 20]
        self.pads = [p for p in course.pads if x0 - 20 < p[0] < x1 + 20]


# ----------------------------------------------------------------------------- Tora's body + physics
class Body:
    def __init__(self, x, y):
        self.x, self.y, self.vy = float(x), float(y), 0.0
        self.ground = None        # the solid under the paws
        self.wire = None          # the tram wire she hangs on
        self.slide = self.pounce = self.pad = self.hold = self.cling = False
        self.blocked = None
        self.jumps = 0            # mid-air jumps left
        self.air_max = 0
        self.jv = 1.0             # jump power (SPRING PAWS)
        self.glide = 0            # TAIL GLIDE level (or 1 while the umbrella is open)
        self.boost = 1.0          # speed factor from catnip
        self.coyote = self.buffer = self.wire_cd = 0.0
        self.air_t = 0.0

    def clone(self):
        b = Body(self.x, self.y)
        for k, v in self.__dict__.items():
            setattr(b, k, v)
        return b

    def height(self):
        return SLIDE_H if self.slide else STAND_H

    def half(self):
        return 7 if self.slide else 5

    def box(self):
        h, hw = self.height(), self.half()
        return (self.x - hw, self.y - h, hw * 2, h)


class Ctrl:
    __slots__ = ("jump_hit", "jump", "down_hit", "down", "lr")

    def __init__(self, jump_hit=False, jump=False, down_hit=False, down=False, lr=0):
        self.jump_hit, self.jump, self.down_hit, self.down, self.lr = jump_hit, jump, down_hit, down, lr


def run_speed(b, c, v):
    spd = v.speed * b.boost * (SPRINT if c.lr > 0 else BRAKE if c.lr < 0 else 1.0)
    for z in v.winds:
        if z[0] <= b.x <= z[1]:
            spd *= 0.6 if z[2] == 0 else 1.35
    return spd


def step(b, c, dt, v):
    """Advance Tora by dt. Returns a list of (event, obj) - jump airjump kick bounce grab land bonk pad pounce
    updraft leave."""
    ev = []
    b.wire_cd -= dt
    b.coyote -= dt
    b.buffer -= dt
    if c.jump_hit:
        b.buffer = 0.12
    if not c.jump:
        b.hold = False
    spd = run_speed(b, c, v)
    # ---- hanging on a tram wire
    if b.wire is not None:
        wr = b.wire
        b.x += spd * 1.3 * dt
        b.y = wr.y + HANG
        b.slide = False
        if b.buffer > 0:
            b.buffer = 0.0
            b.wire = None
            b.vy = -JUMP_V * 0.92 * b.jv
            b.hold = True
            b.wire_cd = 0.25
            b.jumps = b.air_max
            ev.append(("jump", wr))
        elif c.down_hit or b.x > wr.x1:
            hop = b.x > wr.x1
            b.wire = None
            b.vy = -90.0 if hop else 0.0
            b.wire_cd = 0.12 if hop else 0.3
            b.jumps = b.air_max
            ev.append(("leave", wr))
        return ev
    # ---- run (horizontal)
    h, hw = b.height(), b.half()
    nx = b.x + spd * dt
    b.blocked = None
    for r in v.solids:
        if r.y < b.y - 0.5 and r.y + r.h > b.y - h and b.x + hw <= r.x + 0.01 and nx + hw > r.x:
            nx = r.x - hw
            b.blocked = r
    b.x = nx
    # ---- on the ground
    if b.ground is not None:
        g = b.ground
        gone = getattr(g, "broken", False) or (g.solid == "S" and not g.alive)
        if gone or b.x + hw <= g.x or b.x - hw >= g.x + g.w:
            b.ground = None
            b.coyote = 0.09
            b.vy = 0.0
            ev.append(("leave", g))
        else:
            b.y = g.y
            # a solid overhead keeps her sliding (billboards)
            if c.down:
                b.slide = True
            elif b.slide:
                if not any(r.y + r.h > b.y - STAND_H and r.y + r.h <= b.y - SLIDE_H + 0.5 and
                           r.x < b.x + 5 and r.x + r.w > b.x - 5 for r in v.solids):
                    b.slide = False
            for p in v.pads:
                if abs(p[0] - b.x) < 8 and abs(p[1] - b.y) < 1 and p[2] <= 0:
                    b.ground = None
                    b.vy = -PAD_V
                    b.pad = True
                    b.slide = False
                    ev.append(("pad", p))
                    return ev
            if b.buffer > 0 and b.ground is not None:
                b.buffer = 0.0
                b.ground = None
                b.slide = False
                b.vy = -JUMP_V * b.jv
                b.hold = True
                b.jumps = b.air_max
                ev.append(("jump", None))
            elif b.ground is not None:
                for vx, vy0 in v.vents:
                    if abs(vx - b.x) < 12 and abs(vy0 - b.y) < 1:
                        b.ground = None
                        b.slide = False
                        b.vy = -120.0
                        ev.append(("updraft", None))
                        break
            if b.ground is not None:
                return ev
    # ---- in the air
    b.slide = False
    b.air_t += dt
    if b.buffer > 0:
        if b.blocked is not None or b.cling:
            b.buffer = 0.0
            b.vy = -KICK_V * b.jv
            b.hold = True
            b.pounce = b.pad = False
            ev.append(("kick", b.blocked))
        elif b.coyote > 0:
            b.buffer = 0.0
            b.vy = -JUMP_V * b.jv
            b.hold = True
            b.jumps = b.air_max
            ev.append(("jump", None))
        elif b.jumps > 0 and c.jump_hit:
            b.buffer = 0.0
            b.jumps -= 1
            b.vy = -AIR_V * b.jv
            b.hold = True
            b.pounce = b.pad = False
            ev.append(("airjump", None))
    if c.down_hit and not b.pounce:
        b.pounce = True
        b.pad = False
        b.vy = max(b.vy, POUNCE_V)
        ev.append(("pounce", None))
    g = G_UP if (b.vy < 0 and b.hold and not b.pad) else G_DOWN
    b.vy += g * dt
    for vx, vy0 in v.vents:
        if abs(vx - b.x) < 12 and vy0 - 130 < b.y <= vy0 + 1 and not b.pounce:
            b.vy = max(b.vy - 2600 * dt, -300.0)
    if b.glide and c.jump and b.vy > 0 and not b.pounce:
        b.vy = min(b.vy, GLIDE_V[min(2, b.glide)])
    b.cling = b.blocked is not None and not b.pounce
    if b.cling and b.vy > CLING_V:
        b.vy = CLING_V
    b.vy = min(b.vy, MAX_FALL)
    ny = b.y + b.vy * dt
    if b.vy >= 0:
        best = None
        for r in v.solids:
            if b.x + hw > r.x and b.x - hw < r.x + r.w and b.y <= r.y + 0.5 and ny >= r.y:
                if best is None or r.y < best.y:
                    best = r
        line = None
        for ln in v.lines:
            if ln.x0 <= b.x <= ln.x1 and b.y <= ln.y + 0.5 and ny >= ln.y:
                if (best is None or ln.y < best.y) and (line is None or ln.y < line.y):
                    line = ln
        if line is not None:
            b.y = line.y
            b.vy = -BOUNCE_V * (1.15 if c.jump else 1.0)
            b.hold = c.jump
            b.pounce = b.pad = False
            b.jumps = b.air_max
            ev.append(("bounce", line))
            return ev
        if best is not None:
            ev.append(("land", (best, b.vy, b.pounce)))
            b.y = best.y
            b.vy = 0.0
            b.ground = best
            b.pounce = b.pad = b.cling = False
            b.jumps = b.air_max
            b.air_t = 0.0
            if b.buffer > 0:        # a jump pressed just before touching down
                b.buffer = 0.0
                b.ground = None
                b.vy = -JUMP_V * b.jv
                b.hold = True
                ev.append(("jump", None))
            return ev
    else:
        for r in v.solids:
            if b.x + hw > r.x and b.x - hw < r.x + r.w and b.y - h >= r.y + r.h - 0.5 and ny - h < r.y + r.h:
                ny = r.y + r.h + h
                b.vy = 0.0
                ev.append(("bonk", r))
                break
    b.y = ny
    if b.wire_cd <= 0:
        for wr in v.wires:
            if wr.x0 + 2 <= b.x <= wr.x1 - 8 and abs(b.y - STAND_H - wr.y) <= 7:
                b.wire = wr
                b.y = wr.y + HANG
                b.vy = 0.0
                b.pounce = b.pad = b.cling = False
                ev.append(("grab", wr))
                break
    return ev


# ----------------------------------------------------------------------------- drawing: background
class Rng:
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def n(self, k):
        self.s = lcg(self.s)
        return (self.s >> 8) % k


def make_sky(tier):
    """Static sky: gradient, stars, moon and the district's landmark."""
    th = THEMES[tier]
    s = pygame.Surface((W, H))
    for i in range(16):
        s.fill(lerp_col(th[1], th[2], i / 15), (0, i * 10, W, 10 if i < 15 else H - 150))
    rnd = Rng(tier * 31 + 5)
    if th[10] not in ("rain", "storm", "fog"):
        for _ in range(46):
            x, y = rnd.n(W), rnd.n(120)
            c = ("white", "lavender", "yellow")[rnd.n(3)]
            s.fill(col(c), (x, y, 1, 1))
    lm = th[9]
    if lm in ("moon", "sea", "domes", "hills", "lanterns", "fireworks", "lighthouse"):
        mx, my, mr = (248, 46, 16) if lm != "moon" else (236, 50, 24)
        pygame.draw.circle(s, col("cream"), (mx, my), mr)
        pygame.draw.circle(s, col("white"), (mx - 2, my - 2), mr - 4)
        for dx, dy, r in ((-5, 3, 3), (4, -4, 2), (6, 6, 2)):
            pygame.draw.circle(s, col("cream"), (mx + dx, my + dy), r)
    if lm == "sea":
        s.fill(col("ink"), (0, 150, W, H - 150))
        for y in range(152, H, 5):
            for x in range(rnd.n(20), W, 26 + rnd.n(20)):
                s.fill(col("deep" if y > 170 else "lavender"), (x, y, 6 + rnd.n(8), 1))
        for x in range(242, 256, 2):
            s.fill(col("yellow"), (x, 158 + (x % 6), 1, 2))
    elif lm == "clock":
        pygame.draw.rect(s, col("ink"), (52, 34, 34, 130))
        pygame.draw.polygon(s, col("ink"), [(48, 36), (69, 10), (90, 36)])
        pygame.draw.circle(s, col("cream"), (69, 56), 12)
        pygame.draw.circle(s, col("ink"), (69, 56), 12, 1)
        pygame.draw.line(s, col("ink"), (69, 56), (69, 47))
        pygame.draw.line(s, col("ink"), (69, 56), (75, 59))
    elif lm == "tram":
        for k in range(3):
            pygame.draw.line(s, col("darkgray"), (0, 60 + k * 6), (W, 46 + k * 6))
    elif lm == "towers":
        for k, (x, w, h) in enumerate(((30, 26, 140), (84, 18, 170), (190, 30, 150), (268, 22, 176))):
            s.fill(col("ink"), (x, H - h, w, h))
            s.fill(col("red"), (x + w // 2, H - h - 3, 1, 3))
    elif lm == "lanterns":
        for k in range(3):
            y0 = 40 + k * 22
            for x in range(0, W, 6):
                y = y0 + int(8 * math.sin(x / W * math.pi + k))
                s.fill(col("darkgray"), (x, y, 6, 1))
                if x % 24 == 0:
                    pygame.draw.circle(s, col(("red", "orange", "yellow")[(x // 24 + k) % 3]), (x + 3, y + 4), 3)
    elif lm == "cranes":
        for x0, h in ((40, 120), (210, 140)):
            s.fill(col("ink"), (x0, H - h, 4, h))
            s.fill(col("ink"), (x0 - 30, H - h, 90, 3))
            pygame.draw.line(s, col("ink"), (x0 + 50, H - h + 3), (x0 + 50, H - h + 50))
            s.fill(col("orange"), (x0 + 1, H - h - 2, 2, 2))
    return s


def make_skyline(tier, far):
    """A 320 px wide band of rooftops (alpha) that tiles horizontally."""
    th = THEMES[tier]
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    c = col(th[3] if far else th[4])
    win = col("darkgray" if far else th[8])
    rnd = Rng(tier * 97 + (1 if far else 2))
    x = 0
    lm = th[9]
    while x < W:
        w = 18 + rnd.n(26)
        top = (88 if far else 112) + rnd.n(40 if far else 46)
        if x + w > W:
            w = W - x
        style = rnd.n(5)
        if style == 1 and lm == "domes" and w > 14:      # a glass dome, drawn before the walls cover its base
            pygame.draw.circle(s, col("teal" if far else "mint"), (x + w // 2, top), w // 2 - 1)
            pygame.draw.circle(s, c, (x + w // 2, top), w // 2 - 2)
            s.fill(col("teal"), (x + w // 2 - 1, top - w // 2 + 3, 1, w // 2 - 3))
        s.fill(c, (x, top, w, H - top))
        if style == 0 and w > 12:
            pygame.draw.polygon(s, c, [(x, top), (x + w // 2, top - 10), (x + w - 1, top)])
        elif style == 2:
            s.fill(c, (x + w // 3, top - 9, 2, 9))
            if lm == "antennas" or not far:
                s.fill(c, (x + w // 3 - 3, top - 7, 8, 1))
        elif style == 3 and not far:
            pygame.draw.rect(s, c, (x + 3, top - 12, 9, 8), border_radius=2)
            s.fill(c, (x + 4, top - 4, 1, 4))
            s.fill(c, (x + 10, top - 4, 1, 4))
        if lm == "neon" and not far and w > 16 and rnd.n(2):
            pygame.draw.rect(s, col(("hotpink", "sky", "lime")[rnd.n(3)]), (x + 3, top + 6, w - 6, 7), 1)
        for wy in range(top + 6, H, 9 if far else 10):
            for wx in range(x + 3, x + w - 3, 6 if far else 7):
                if rnd.n(5 if far else 3) == 0:
                    s.fill(win, (wx, wy, 2, 3 if far else 4))
        x += w + rnd.n(4)
    return s


def draw_weather(s, kind, t, cam):
    if kind in ("rain", "storm"):
        c = col("sky")
        for i in range(70):
            x = (i * 53 + int(t * 60) - int(cam * 0.6)) % (W + 40) - 20
            y = (i * 37 + int(t * 260)) % (H + 20) - 10
            pygame.draw.line(s, c, (x, y), (x - 3, y + 6))
    elif kind == "snow":
        for i in range(60):
            x = (i * 61 + int(math.sin(t + i) * 8) - int(cam * 0.5)) % W
            y = (i * 29 + int(t * (24 + i % 5 * 6))) % H
            s.fill(col("white"), (x, y, 1 + (i % 3 == 0), 1 + (i % 3 == 0)))
    elif kind == "wind":
        for i in range(14):
            x = W - (i * 83 + int(t * 300)) % (W + 60)
            y = 30 + (i * 47) % 150
            s.fill(col("lavender"), (x, y, 10 + i % 3 * 6, 1))
    elif kind == "fog":
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(6):
            y = 70 + i * 22 + int(math.sin(t * 0.7 + i) * 4)
            ov.fill((139, 134, 168, 34), (0, y, W, 14))
        for x in range(170, W, 10):        # thick fog ahead
            ov.fill((139, 134, 168, min(150, (x - 170) * 1)), (x, 24, 10, H - 24))
        s.blit(ov, (0, 0))


# ----------------------------------------------------------------------------- drawing: rooftops
def draw_roof(s, r, cam, th, t):
    x = int(r.x - cam)
    w = r.w
    if x > W or x + w < 0:
        return
    y = r.y
    if r.glass:
        draw_skylight(s, r, x, t)
        return
    face, trim, ledge, win = col(th[5]), col(th[6]), col(th[7]), col(th[8])
    s.fill(face, (x, y, w, H - y))
    s.fill(trim, (x, y + 3, 2, H - y))
    s.fill(trim, (x + w - 2, y + 3, 2, H - y))
    s.fill(ledge, (x - 1, y, w + 2, 3))
    s.fill(col("black"), (x - 1, y + 3, w + 2, 1))
    # windows: a grid anchored to the world so they scroll with the building
    gx0 = r.x + 8
    for wy in range(y + 12, H, 16):
        for wx in range(gx0, r.x + w - 10, 14):
            sx = wx - cam
            if sx < -8 or sx > W:
                continue
            hv = hash2(wx, wy)
            if hv % 3 == 0:
                s.fill(trim, (sx, wy, 6, 8))
            else:
                s.fill(col("black"), (sx - 1, wy - 1, 8, 10))
                s.fill(win if hv % 5 else col("orange"), (sx, wy, 6, 8))
                s.fill(face, (sx + 3, wy, 1, 8))
                if hv % 7 == 0:          # a cat silhouette in the window, now and then
                    s.fill(col("black"), (sx + 1, wy + 4, 4, 4))
                    s.fill(col("black"), (sx + 1, wy + 3, 1, 1))
                    s.fill(col("black"), (sx + 4, wy + 3, 1, 1))


def draw_skylight(s, r, x, t):
    y, w = r.y, r.w
    if r.broken:
        s.fill(col("black"), (x, y, w, H - y))
        s.fill(col("ink"), (x, y, w, 2))
        for i in range(0, w, 5):
            s.fill(col("sky"), (x + i, y + 1 + (i // 5) % 2 * 2, 2, 1))
        return
    s.fill(col("darkgray"), (x, y + 4, w, H - y - 4))
    s.fill(col("gray"), (x, y, w, 4))
    s.fill(col("teal"), (x + 1, y + 1, w - 2, 2))
    shine = int(t * 30 + r.x) % (w + 20) - 10
    if 0 <= shine < w - 2:
        s.fill(col("white"), (x + 1 + shine, y + 1, 2, 2))
    s.fill(col("black"), (x, y, 1, 4))
    s.fill(col("black"), (x + w - 1, y, 1, 4))
    if r.crack >= 0:
        k = 1 + int((0.7 - min(0.7, r.crack)) * 8)
        for i in range(min(k, 5)):
            cx = x + 3 + (i * 7) % max(4, w - 6)
            pygame.draw.line(s, col("white"), (cx, y + 1), (cx + 3, y + 3))


def draw_box(s, b, cam, th, t):
    x, y, w, h = int(b.x - cam), int(b.y), b.w, b.h
    if x > W + 4 or x + w < -4 or not b.alive:
        return
    k = b.k
    k_ = col("black")
    if k in ("X", "C"):
        pygame.draw.rect(s, k_, (x - 1, y - 1, w + 2, h + 2))
        s.fill(col("brown"), (x, y, w, h))
        s.fill(col("peach"), (x, y, w, 1))
        pygame.draw.line(s, col("choco"), (x + 1, y + 1), (x + w - 2, y + h - 2))
        pygame.draw.line(s, col("choco"), (x + w - 2, y + 1), (x + 1, y + h - 2))
        s.fill(col("choco"), (x, y + h // 2, w, 1))
        if k == "C":
            s.fill(col("ink"), (x + 2, y + 4, w - 4, 6))
            s.blit(sprite("rr_fish"), (x + w // 2 - 4, y + 4))
    elif k == "U":
        pygame.draw.rect(s, k_, (x - 1, y - 1, w + 2, h + 1))
        s.fill(col("gray"), (x, y, w, h))
        s.fill(col("white"), (x, y, w, 1))
        s.fill(col("darkgray"), (x, y + h - 2, w, 2))
        cx, cy = x + w // 2, y + h // 2
        r = min(w, h) // 2 - 2
        pygame.draw.circle(s, col("darkgray"), (cx, cy), r)
        a = t * 12
        for i in range(3):
            pygame.draw.line(s, col("white"), (cx, cy),
                             (cx + int(math.cos(a + i * 2.1) * (r - 1)), cy + int(math.sin(a + i * 2.1) * (r - 1))))
    elif k == "K":
        pygame.draw.rect(s, k_, (x - 1, y + 3, w + 2, h - 3))
        s.fill(col("choco"), (x, y + 4, w, h - 4))
        for by in range(y + 6, y + h, 5):
            off = 0 if (by // 5) % 2 else 4
            for bx in range(x + off, x + w, 8):
                s.fill(col("brown"), (bx, by, min(6, x + w - bx), 3))
        pygame.draw.rect(s, k_, (x - 3, y - 1, w + 6, 6))
        s.fill(col("darkgray"), (x - 2, y, w + 4, 4))
        s.fill(col("gray"), (x - 2, y, w + 4, 1))
        for i in range(3):          # smoke puffs drifting up-left
            p = (t * 0.6 + i / 3 + b.x * 0.01) % 1
            pygame.draw.circle(s, col("darkgray" if p > 0.5 else "gray"),
                               (x + w // 2 - int(p * 14), y - 4 - int(p * 26)), 2 + int(p * 3))
    elif k == "B":
        for lx in (x + 4, x + w - 6):
            s.fill(col("darkgray"), (lx, y + h, 2, b.y + h + 12 - (y + h) + 0))
        pygame.draw.rect(s, k_, (x - 1, y - 1, w + 2, h + 2))
        hue = ("hotpink", "sky", "lime", "yellow", "orange")[hash2(b.x, 3) % 5]
        s.fill(col("ink"), (x, y, w, h))
        glow = int(t * 3 + b.x) % 7 != 0
        pygame.draw.rect(s, col(hue if glow else "darkgray"), (x + 1, y + 1, w - 2, h - 2), 1)
        ad = BILLBOARD_ADS[hash2(b.x, 7) % len(BILLBOARD_ADS)]
        draw_text(s, ad, x + w // 2, y + h // 2 - 3, hue if glow else "gray", align="center", shadow=None)
    elif k == "T":
        s.fill(col("brown"), (x, y, w, h))


def draw_lift(s, m, cam, t):
    x, y = int(m.x - cam), int(m.y)
    if x > W or x + m.w < 0:
        return
    s.fill(col("darkgray"), (x + 4, 0, 1, y))
    s.fill(col("darkgray"), (x + m.w - 5, 0, 1, y))
    pygame.draw.rect(s, col("black"), (x - 1, y - 1, m.w + 2, m.h + 2))
    s.fill(col("gray"), (x, y, m.w, m.h))
    for i in range(0, m.w, 6):
        s.fill(col("yellow"), (x + i, y + m.h - 2, 3, 2))
    s.fill(col("white"), (x, y, m.w, 1))


def draw_line(s, ln, cam, t, lantern=False):
    x0, x1 = int(ln.x0 - cam), int(ln.x1 - cam)
    if x0 > W or x1 < 0:
        return
    y = int(ln.y)
    for px in (x0, x1):
        s.fill(col("choco"), (px - 1, y - 6, 3, H - y + 6))
        s.fill(col("brown"), (px, y - 6, 1, H - y + 6))
    span = max(1, x1 - x0)
    prev = None
    for i in range(0, span + 1, 4):
        sag = int(3 * math.sin(math.pi * i / span))
        p = (x0 + i, y + sag)
        if prev:
            pygame.draw.line(s, col("cream"), prev, p)
        prev = p
    k = 0
    for i in range(8, span - 6, 14):
        sag = int(3 * math.sin(math.pi * i / span))
        cx = x0 + i
        cy = y + sag
        sw = int(math.sin(t * 3 + i) * 1.5)
        if lantern:
            c = ("red", "orange", "yellow", "hotpink")[(k + int(ln.x0)) % 4]
            pygame.draw.circle(s, col("black"), (cx + sw, cy + 5), 4)
            pygame.draw.circle(s, col(c), (cx + sw, cy + 5), 3)
            s.fill(col("white"), (cx + sw - 1, cy + 3, 1, 1))
        else:
            c = ("pink", "sky", "lime", "yellow", "white", "lavender")[(k + int(ln.x0)) % 6]
            kind = (k + int(ln.x0) // 7) % 3
            if kind == 0:           # a little shirt
                s.fill(col(c), (cx - 3 + sw, cy + 1, 7, 6))
                s.fill(col(c), (cx - 5 + sw, cy + 1, 2, 3))
                s.fill(col(c), (cx + 4 + sw, cy + 1, 2, 3))
            elif kind == 1:         # a sock
                s.fill(col(c), (cx - 1 + sw, cy + 1, 3, 7))
                s.fill(col(c), (cx - 1 + sw, cy + 6, 5, 2))
            else:                   # a towel
                s.fill(col(c), (cx - 3 + sw, cy + 1, 6, 9))
                s.fill(col("white"), (cx - 3 + sw, cy + 7, 6, 1))
            s.fill(col("black"), (cx + sw, cy, 1, 2))
        k += 1


def draw_wire(s, wr, cam, t):
    x0, x1 = int(wr.x0 - cam), int(wr.x1 - cam)
    if x0 > W or x1 < 0:
        return
    for px in (x0, x1):
        s.fill(col("darkgray"), (px - 1, wr.y - 8, 3, H - wr.y + 8))
        s.fill(col("gray"), (px - 4, wr.y - 8, 9, 2))
    pygame.draw.line(s, col("black"), (x0, wr.y + 1), (x1, wr.y + 1))
    pygame.draw.line(s, col("gray"), (x0, wr.y), (x1, wr.y))
    if wr.spark:
        sx = int(wr.spark_x(t) - cam)
        if x0 <= sx <= x1:
            for i in range(4):
                a = t * 30 + i * 1.6
                s.fill(col("yellow" if i % 2 else "white"), (sx + int(math.cos(a) * 3), wr.y + int(math.sin(a) * 3), 2, 2))


def draw_fish(s, f, cam, t, gold=False):
    x, y = int(f[0] - cam), int(f[1])
    if x < -10 or x > W + 10:
        return
    bob = int(math.sin(t * 5 + f[0] * 0.05) * 1.5)
    if gold:
        if f[3]:
            sp = sprite("rr_goldfish", remap={"y": "p", "o": "u"} if int(t * 8) % 2 else {"y": "m", "o": "b"})
        else:
            sp = sprite("rr_goldfish")
        s.blit(sp, (x - 5, y - 3 + bob))
        if int(t * 6 + f[0]) % 4 == 0:
            s.fill(col("white"), (x + 4, y - 4 + bob, 1, 1))
    else:
        s.blit(sprite("rr_fish"), (x - 4, y - 2 + bob))


CAP_COLORS = ("yellow", "sky", "lime", "peach", "white", "orange")


def draw_cap(s, c, cam, t):
    x, y = int(c[0] - cam), int(c[1] + math.sin(t * 4 + c[0]) * 2)
    if x < -12 or x > W + 12:
        return
    k = c[2]
    pygame.draw.circle(s, col("black"), (x, y), 8)
    pygame.draw.circle(s, col(CAP_COLORS[k]), (x, y), 7)
    pygame.draw.circle(s, col("ink"), (x, y), 5)
    draw_cap_icon(s, k, x, y, t)
    s.fill(col("white"), (x - 4, y - 5, 2, 1))


def draw_cap_icon(s, k, x, y, t):
    if k in (0, 5):        # bell
        c = "yellow" if k == 0 else ("yellow" if int(t * 10) % 2 else "orange")
        pygame.draw.circle(s, col(c), (x, y), 3)
        s.fill(col(c), (x - 4, y + 1, 9, 2))
        s.fill(col("black"), (x, y + 3, 1, 1))
    elif k == 1:           # umbrella
        pygame.draw.polygon(s, col("sky"), [(x - 4, y), (x, y - 4), (x + 4, y)])
        s.fill(col("white"), (x, y, 1, 4))
        s.fill(col("white"), (x - 1, y + 3, 1, 1))
    elif k == 2:           # catnip leaf
        pygame.draw.ellipse(s, col("lime"), (x - 3, y - 3, 6, 7))
        s.fill(col("mint"), (x, y - 3, 1, 7))
    elif k == 3:           # yarn shield
        pygame.draw.circle(s, col("peach"), (x, y), 3)
        pygame.draw.line(s, col("hotpink"), (x - 2, y - 2), (x + 2, y + 2))
    elif k == 4:           # milk carton
        s.fill(col("white"), (x - 2, y - 2, 5, 6))
        s.fill(col("sky"), (x - 2, y, 5, 2))
        s.fill(col("white"), (x - 1, y - 4, 3, 2))


def draw_hazard(s, hz, cam, t, stime):
    if not hz.alive and hz.k not in ("p", "q"):
        return
    x, y = int(hz.x - cam), int(hz.y)
    if x < -30 or x > W + 30:
        return
    k = hz.k
    if k in ("p", "q"):
        if not hz.alive:        # knocked away: tumbles off
            if hz.t < 1.2:
                sp = sprite("rr_pigeon_fly", int(t * 10), flip=True)
                s.blit(sp, (x - 6, y - 10))
            return
        if k == "p":
            sp = sprite("rr_pigeon", int(t * 6) % 2, flip=hz.dir > 0)
            s.blit(sp, (x - 6, y - 10 + (int(t * 6) % 2 == 0)))
        else:
            sp = sprite("rr_pigeon_fly", int(t * 10) % 2)
            s.blit(sp, (x - 6, y - 6))
    elif k == "s":
        ph = sprinkler_phase(hz, stime)
        s.fill(col("darkgray"), (x - 3, y - 4, 7, 4))
        s.fill(col("gray"), (x - 1, y - 7, 3, 3))
        if ph == 1 and int(t * 10) % 2:
            s.fill(col("sky"), (x, y - 10, 1, 2))
        elif ph == 2:
            for i in range(14):
                yy = y - 8 - (i * 2 + int(t * 60)) % 24
                dx = int(math.sin(i * 1.7 + t * 9) * 3)
                s.fill(col("sky" if i % 3 else "white"), (x + dx, yy, 1 + i % 2, 2))
            pygame.draw.ellipse(s, col("sky"), (x - 7, y - 33, 15, 6))
    elif k == "a":
        h = hz.a
        s.fill(col("gray"), (x - 1, y - h, 2, h))
        for i in range(2):
            yy = y - h + 2 + i * 5
            w = 9 - i * 3
            s.fill(col("white"), (x - w // 2, yy, w, 1))
            s.fill(col("red"), (x - w // 2, yy - 1, 1, 2))
            s.fill(col("red"), (x + w // 2, yy - 1, 1, 2))
        s.fill(col("red" if int(t * 4) % 2 else "orange"), (x - 1, y - h - 2, 2, 2))
    elif k == "i":
        top = int(hz.a)
        s.fill(col("white"), (int(hz.x0 - cam) - 8, top - 3, 17, 3))
        s.fill(col("gray"), (int(hz.x0 - cam) - 8, top, 17, 1))
        if hz.state == 0 or hz.state == 3:
            shake = int(math.sin(t * 60) * 1) if hz.state == 3 else 0
            pygame.draw.polygon(s, col("sky"), [(x - 3 + shake, top + 1), (x + 3 + shake, top + 1), (x + shake, top + 11)])
            s.fill(col("white"), (x - 1 + shake, top + 2, 1, 4))
        elif hz.state == 1:
            yy = int(hz.y)
            pygame.draw.polygon(s, col("sky"), [(x - 3, yy - 10), (x + 3, yy - 10), (x, yy)])
            s.fill(col("white"), (x - 1, yy - 9, 1, 4))
        elif hz.state == 2:
            for i in range(-3, 4, 2):
                s.fill(col("sky"), (x + i, y - 4 - abs(i), 2, 4 + abs(i) // 2))
    elif k == "d":
        if hz.state == 1:       # warning
            if int(t * 8) % 2:
                draw_text(s, "!", W - 10, y - 4, "red", 2, outline="ink")
            for xx in range(80, W - 20, 10):
                s.fill(col("red"), (xx, y, 5, 1))
        elif hz.state == 2:
            sp = sprite("rr_gully_nofish", int(t * 10) % 2, remap={"w": "c", "g": "d"})
            s.blit(sp, (x - 9, y - 9))
    elif k == "z":
        s.fill(col("gray"), (x, y - 26, 1, 26))
        pygame.draw.circle(s, col("yellow" if hz.state == 1 and int(t * 12) % 2 else "gray"), (x, y - 27), 2)
        if hz.state == 1:
            for xx in range(x - 12, x + 13, 4):
                s.fill(col("yellow"), (xx, y - 1, 2, 1))
        elif hz.state == 2:
            px = x
            for yy in range(0, y - 27, 6):
                nx = x + (hash2(yy, int(t * 30)) % 9) - 4
                pygame.draw.line(s, col("white"), (px, yy), (nx, yy + 6), 2)
                px = nx
            for i in range(8):
                xx = x - 12 + hash2(i, int(t * 40)) % 25
                s.fill(col("yellow" if i % 2 else "white"), (xx, y - 2 - hash2(i, int(t * 30)) % 7, 2, 2))


def draw_pad(s, p, cam, t):
    x, y = int(p[0] - cam), int(p[1])
    if x < -10 or x > W + 10:
        return
    pygame.draw.rect(s, col("black"), (x - 7, y - 6, 15, 7))
    s.fill(col("red"), (x - 6, y - 5, 13, 5))
    s.fill(col("yellow"), (x - 6, y - 5, 13, 1))
    for i in range(3):
        s.fill(col("white"), (x - 4 + i * 4, y - 3, 1, 2))
    if int(t * 6) % 2:
        s.fill(col("yellow"), (x, y - 9, 1, 2))


def draw_vent(s, v, cam, t):
    x, y = int(v[0] - cam), int(v[1])
    if x < -20 or x > W + 20:
        return
    pygame.draw.rect(s, col("black"), (x - 10, y - 6, 21, 7))
    s.fill(col("gray"), (x - 9, y - 5, 19, 5))
    for i in range(-8, 9, 3):
        s.fill(col("darkgray"), (x + i, y - 5, 1, 5))
    for i in range(6):
        yy = y - 10 - (int(t * 90) + i * 22) % 120
        s.fill(col("lavender" if i % 2 else "white"), (x - 8 + (i * 7) % 16, yy, 1, 5))


def draw_wind(s, z, cam, t):
    x0, x1 = int(z[0] - cam), int(z[1] - cam)
    if x0 > W or x1 < 0:
        return
    head = z[2] == 0
    for i in range(10):
        span = max(1, x1 - x0)
        p = (t * (160 if head else 200) + i * 37) % span
        x = x1 - int(p) if head else x0 + int(p)
        y = 40 + (i * 29) % 120
        s.fill(col("lavender" if head else "mint"), (x, y, 8, 1))
        s.fill(col("white"), (x + (0 if head else 6), y, 2, 1))
