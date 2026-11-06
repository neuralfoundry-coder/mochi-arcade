"""ALLEY HOP bosses: one generic attack engine (charge / ring / strike / rows / cols / rest) wearing six original
costumes - BRUNO the guard dog, SWEEPO the street sweeper, the GULL GANG, BANDIT COON, KING CLAW, HOOTSWORTH the
night owl - plus BIG BOSS BRUNO on stage 200. Every attack is telegraphed; after some of them the boss is
dizzy / busy ('rest') and Sushi can hop onto it. Mirrored in ios/MochiArcade/Games/AlleyHopBoss.swift."""
import math

import pygame

from mochi_arcade import cute
from mochi_arcade.games import alley_hop_art as art
from mochi_arcade.gfx import W, col, draw_text

TOP, CELL = 12, 16
SIZE = {"bruno": (28, 22), "sweepo": (40, 24), "gulls": (14, 12), "coon": (24, 20), "claw": (44, 20),
        "owl": (26, 24), "king": (32, 26)}
EDGE = ("bruno", "sweepo", "owl", "king")           # live on the left / right edge and charge across rows
DIZZY_AFTER_CHARGE = ("bruno", "owl", "king")
SOLID = ("idle", "move", "tell", "act")
SHOT_SPEED = {"ball": 75, "bone": 80, "suds": 55, "jet": 210, "feather": 90, "egg": 105, "lid": 85, "can": 62,
              "bubble": 50, "dart": 130}
UP_SHOTS = ("jet", "bubble")


def row_cy(r):
    return TOP + r * CELL + 8


class Boss:
    def __init__(self, game, spec):
        self.g = game
        self.kind = spec["kind"]
        self.name = spec["name"]
        self.hp = self.maxhp = spec["hp"]
        self.sp = spec["sp"]
        self.rest_t = spec["rest"]
        self.tell_t = spec["tell"]
        self.atk = spec["atk"]
        self.nshots = spec["n"]
        self.rk, self.ck = spec["rk"], spec["ck"]
        self.w, self.h = SIZE[self.kind]
        self.state = "enter"
        self.st = 0.0
        self.t = 0.0
        self.ai = 0
        self.cur = ""
        self.face = -1
        self.x, self.y = float(W + 30), float(row_cy(5))
        if self.kind in ("coon", "claw"):
            self.x, self.y = float(W // 2), float(row_cy(1) - 40)
        elif self.kind == "gulls":
            self.x, self.y = float(W // 2), float(TOP - 30)
        self.hx, self.hy = self.x, self.y         # where the boss can be bopped while it rests
        self.sx = self.sy = 0.0                    # strike: start of the leap
        self.tx = self.ty = 0.0                    # strike target / charge row
        self.zone = None                           # [x, y, w, h] strike impact area
        self.zone_t = 0.0                          # > 0 while the impact hurts
        self.rows = []                             # telegraphed rows / columns for volleys
        self.cols = []
        self.side = 1                              # volleys from the left (1) or right (-1)
        self.ring = -1.0
        self.shots = []                            # [x, y, vx, vy, kind, spin]
        self.flash = 0.0
        self.home_x = float(W - self.w // 2 - 4)

    # ------------------------------------------------------------------ helpers
    def target_row(self):
        r = self.g.sushi.row
        return max(1, min(9, r))

    def target_col(self):
        return max(0, min(19, int(self.g.sushi_x() // CELL)))

    def home(self):
        """(x, y) the boss returns to after a rest / hurt."""
        if self.kind in EDGE:
            lx, rx = float(self.w // 2 + 4), float(W - self.w // 2 - 4)
            x = lx if self.x < W / 2 else rx
            return x, max(float(row_cy(1)), min(float(row_cy(9)), self.y))
        if self.kind == "gulls":
            return float(W // 2), float(TOP + 2)
        if self.kind == "claw":
            return float(W // 2), float(row_cy(1) - 2)
        return max(40.0, min(float(W - 40), self.x)), float(row_cy(1) - 2)

    def body(self):
        if self.kind == "gulls":
            if self.cur == "strike" and self.state in ("act", "rest", "hurt"):
                return (self.hx - 7, self.hy - 6, 14, 12)
            return None
        return (self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)

    def claw_pos(self):
        """The crab's striking claw (hx, hy) - at rest it hangs next to the body."""
        if self.cur == "strike" and self.state in ("act", "rest", "hurt", "tell"):
            return self.hx, self.hy
        return self.x + 30, self.y + 10

    def vulnerable(self):
        return self.state == "rest"

    def bop_rect(self):
        if not self.vulnerable():
            return None
        if self.kind == "claw":
            return (self.hx - 10, self.hy - 10, 20, 20)
        if self.kind == "gulls":
            return (self.hx - 10, self.hy - 10, 20, 20)
        return (self.hx - self.w / 2 - 3, self.hy - self.h / 2 - 3, self.w + 6, self.h + 6)

    def set_state(self, s):
        self.state = s
        self.st = 0.0

    # ------------------------------------------------------------------ damage tests
    def hurts(self, x, y, r=5):
        """Does anything of the boss hit an entity centred at (x, y)?"""
        ex0, ey0, ex1, ey1 = x - r, y - r, x + r, y + r

        def over(rx, ry, rw, rh, inset=3):
            return rx + inset < ex1 and rx + rw - inset > ex0 and ry + inset < ey1 and ry + rh - inset > ey0
        if self.state == "dead":
            return False
        b = self.body()
        solid = self.state in SOLID
        if self.kind == "gulls":
            solid = self.cur == "strike" and self.state == "act"
        if self.kind == "claw":
            solid = self.state not in ("hurt", "dead", "enter")
            cx, cy = self.claw_pos()
            if self.cur == "strike" and self.state == "act" and over(cx - 7, cy - 6, 14, 12, 1):
                return True
        if b and solid and over(*b):
            return True
        if self.zone_t > 0 and self.zone and over(*self.zone, 0):
            return True
        if self.ring >= 0:
            d = math.hypot(x - self.x, y - self.y)
            if abs(d - self.ring) < 7:
                return True
        for sh in self.shots:
            if abs(sh[0] - x) < 5 + r and abs(sh[1] - y) < 5 + r:
                return True
        return False

    def hit(self):
        """Sushi bopped the boss while it rested."""
        self.hp -= 1
        self.flash = 0.5
        self.zone_t = 0.0
        if self.hp <= 0:
            self.set_state("dead")
            self.shots = []
            self.ring = -1.0
        else:
            self.set_state("hurt")

    # ------------------------------------------------------------------ update
    def update(self, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.zone_t = max(0.0, self.zone_t - dt)
        sp = self.sp
        for sh in self.shots:
            sh[0] += sh[2] * dt
            sh[1] += sh[3] * dt
            sh[5] += dt
        self.shots = [sh for sh in self.shots if -20 < sh[0] < W + 20 and -10 < sh[1] < 210]
        if self.ring >= 0:
            self.ring += 120 * sp * dt
            if self.ring > 100:
                self.ring = -1.0
        self.st += dt
        s = self.state
        if s == "enter":
            hx, hy = self.home()
            if self.kind in EDGE:
                hx, hy = self.home_x, float(row_cy(5))
            self.approach(hx, hy, 90 * dt)
            if self.st > 1.6:
                self.set_state("idle")
        elif s == "idle":
            if self.kind == "coon":       # the bandit paces along the top alley
                self.x += math.sin(self.t * 1.3) * 40 * dt
                self.x = max(30.0, min(float(W - 30), self.x))
            if self.st > max(0.35, 0.9 - 0.12 * sp):
                self.next_attack()
        elif s == "move":       # charge: line up with Sushi's row along the edge
            self.approach(self.x, self.ty, 95 * sp * dt)
            if abs(self.y - self.ty) < 0.5 or self.st > 2.5:
                self.set_state("tell")
        elif s == "tell":
            if self.cur == "strike" and self.kind == "claw":
                self.hx, self.hy = self.x + 30, self.y + 10
            if self.st > self.tell_t:
                self.begin_act()
        elif s == "act":
            self.act(dt)
        elif s == "rest":
            if self.st > self.rest_t:
                self.set_state("ret")
        elif s == "hurt":
            if self.st > 0.7:
                self.set_state("ret")
        elif s == "ret":
            if self.kind == "claw" or self.kind == "gulls":
                self.hx, self.hy = self.x + 30, self.y + 10
                if self.kind == "gulls":
                    self.hx, self.hy = self.x, self.y
                self.cur = ""
                self.set_state("idle")
            else:
                hx, hy = self.home()
                self.approach(hx, hy, 220 * dt)
                self.hx, self.hy = self.x, self.y
                if (abs(self.x - hx) < 1 and abs(self.y - hy) < 1) or self.st > 1.2:
                    self.cur = ""
                    self.set_state("idle")
        elif s == "dead":
            self.y -= 70 * dt
            self.shots = []

    def approach(self, tx, ty, step):
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d <= step or d < 0.01:
            self.x, self.y = tx, ty
        else:
            self.x += dx / d * step
            self.y += dy / d * step

    def next_attack(self):
        a = self.atk[self.ai % len(self.atk)]
        self.ai += 1
        self.cur = a
        g = self.g
        if a == "charge" and self.kind not in EDGE:
            a = self.cur = "strike"
        if a == "charge":
            self.ty = float(row_cy(self.target_row()))
            self.set_state("move")
            return
        if a == "strike":
            r, c = self.target_row(), self.target_col()
            self.tx, self.ty = float(c * CELL + 8), float(row_cy(r))
            self.sx, self.sy = self.x, self.y
            if self.kind == "claw":
                self.sx, self.sy = self.x + 30, self.y + 10
            if self.kind == "gulls":
                self.sx, self.sy = self.x, self.y
            zw, zh = {"gulls": (1, 1), "coon": (3, 1), "claw": (2, 2), "owl": (1, 3)}.get(self.kind, (3, 3))
            zx = max(0, min(20 - zw, c - zw // 2))
            zy = max(1, min(10 - zh, r - zh // 2))
            self.zone = [zx * CELL, TOP + zy * CELL, zw * CELL, zh * CELL]
            if self.kind == "claw" and zw == 2:
                self.tx = float(zx * CELL + 16)
                self.ty = float(TOP + zy * CELL + 16)
            self.set_state("tell")
            g.app.audio.play("warning" if self.ai % 3 == 1 else "move")
            return
        if a == "rows":
            rr = self.target_row()
            rows = [rr]
            k = 0
            while len(rows) < min(self.nshots, 4) and k < 20:
                k += 1
                cand = 1 + (rr + 3 * k + self.ai) % 9
                if all(abs(cand - q) >= 2 for q in rows):
                    rows.append(cand)
            self.rows = rows
            if self.kind in EDGE:
                self.side = 1 if self.x < W / 2 else -1
            else:
                self.side = 1 if self.ai % 2 else -1
            self.set_state("tell")
            return
        if a == "cols":
            cc = self.target_col()
            cols = [cc]
            k = 0
            while len(cols) < self.nshots + 1 and k < 30:
                k += 1
                cand = (cc + 5 * k + self.ai * 3) % 20
                if all(abs(cand - q) >= 2 for q in cols):
                    cols.append(cand)
            self.cols = cols
            self.set_state("tell")
            return
        if a == "ring":
            self.set_state("tell")
            return
        # rest: busy refilling / digging - a free bop
        self.hx, self.hy = self.x, self.y
        self.set_state("rest")
        g.app.audio.play("hold")

    def begin_act(self):
        a = self.cur
        au = self.g.app.audio
        if a == "charge":
            self.face = 1 if self.x < W / 2 else -1
            au.play("boom" if self.kind == "sweepo" else "jump")
        elif a == "ring":
            self.ring = 4.0
            au.play("explode")
            self.g.app.shake(2, 0.2)
        elif a == "rows":
            for r in self.rows:
                x0 = -8.0 if self.side > 0 else float(W + 8)
                v = SHOT_SPEED.get(self.rk, 80) * self.sp * 0.85
                self.shots.append([x0, float(row_cy(r)), v * self.side, 0.0, self.rk, 0.0])
            au.play("shoot")
            self.set_state("idle")
            return
        elif a == "cols":
            up = self.ck in UP_SHOTS
            for c in self.cols:
                v = SHOT_SPEED.get(self.ck, 80) * self.sp * 0.85
                y0 = float(TOP + 11 * CELL + 6) if up else float(TOP + 4)
                self.shots.append([float(c * CELL + 8), y0, 0.0, -v if up else v, self.ck, 0.0])
            au.play("shoot")
            self.set_state("idle")
            return
        elif a == "strike":
            au.play("jump")
        self.set_state("act")

    def act(self, dt):
        a = self.cur
        if a == "charge":
            self.x += self.face * 215 * self.sp * dt
            lx, rx = float(self.w // 2 + 4), float(W - self.w // 2 - 4)
            if self.kind == "sweepo":
                self.g.wet_cell(self.ty, self.x)
            if self.x <= lx or self.x >= rx:
                self.x = max(lx, min(rx, self.x))
                self.g.app.shake(3, 0.25)
                self.g.app.audio.play("tin")
                if self.kind in DIZZY_AFTER_CHARGE:
                    self.hx, self.hy = self.x, self.y
                    self.set_state("rest")
                else:
                    self.cur = ""
                    self.set_state("idle")
        elif a == "ring":
            if self.ring < 0 or self.st > 1.2:
                self.ring = -1.0
                self.set_state("idle")
        elif a == "strike":
            dur = 0.36
            p = min(1.0, self.st / dur)
            hx = self.sx + (self.tx - self.sx) * p
            hy = self.sy + (self.ty - self.sy) * p - math.sin(math.pi * p) * 26
            self.hx, self.hy = hx, hy
            if self.kind not in ("claw", "gulls"):
                self.x, self.y = hx, hy
            if p >= 1:
                self.hx, self.hy = self.tx, self.ty
                if self.kind not in ("claw", "gulls"):
                    self.x, self.y = self.tx, self.ty
                self.zone_t = 0.14
                self.g.app.shake(3, 0.2)
                self.g.app.audio.play("boom" if self.kind in ("bruno", "king") else "pop")
                self.g.parts.burst(self.tx, self.ty + 4, 10, ("white", "gray", "cream"), 50, 0.4)
                self.set_state("rest")

    # ------------------------------------------------------------------ drawing
    def draw_tells(self, s, t):
        """Telegraphs (drawn above the lanes, under the HUD)."""
        blink = int(t * 8) % 2
        if self.state == "tell" and self.cur == "charge":
            r = int((self.ty - TOP) // CELL)
            y0 = TOP + r * CELL
            d = 1 if self.x < W / 2 else -1
            for k in range(8):
                cx = int(self.x) + d * (28 + k * 34 + int(t * 60) % 34)
                if 0 <= cx < W:
                    pts = [(cx - 4 * d, y0 + 3), (cx + 3 * d, y0 + 8), (cx - 4 * d, y0 + 13)]
                    pygame.draw.polygon(s, col("red" if blink else "orange"), pts)
        if self.state == "tell" and self.cur == "strike" and self.zone:
            zx, zy, zw, zh = self.zone
            p = min(1.0, self.st / max(0.1, self.tell_t))
            rw = int(4 + 10 * p)
            pygame.draw.ellipse(s, col("black"), (int(self.tx) - rw, int(self.ty) + 2, rw * 2, max(2, rw // 2 + 1)))
            if blink:
                pygame.draw.rect(s, col("red"), (zx, zy, zw, zh), 1)
        if self.state == "tell" and self.cur == "rows":
            for r in self.rows:
                y = row_cy(r)
                x = 4 if self.side > 0 else W - 12
                if blink:
                    draw_text(s, "}}" if self.side > 0 else "{{", x if self.side > 0 else x - 6, y - 3, "red",
                              shadow="black")
        if self.state == "tell" and self.cur == "cols":
            up = self.ck in UP_SHOTS
            for c in self.cols:
                x = c * CELL + 8
                if blink:
                    draw_text(s, "|" if up else "`", x - 2, TOP + 10 * CELL + 4 if up else TOP + 2, "red",
                              shadow="black")
                s.fill(col("red"), (x, TOP + 16, 1, 10 * CELL - 16))
        if self.state == "tell" and self.cur == "ring":
            if blink:
                pygame.draw.circle(s, col("red"), (int(self.x), int(self.y)), 22, 1)
        if self.ring >= 0:
            r = int(self.ring)
            pygame.draw.circle(s, col("yellow"), (int(self.x), int(self.y)), r, 2)
            if r > 8:
                pygame.draw.circle(s, col("white"), (int(self.x), int(self.y)), r - 5, 1)
        if self.zone_t > 0 and self.zone:
            zx, zy, zw, zh = self.zone
            pygame.draw.rect(s, col("white"), (zx, zy, zw, zh), 2)

    def draw_shots(self, s, t):
        for x, y, vx, vy, kind, spin in self.shots:
            xi, yi = int(x), int(y)
            if kind == "ball":
                pygame.draw.circle(s, col("black"), (xi, yi), 5)
                pygame.draw.circle(s, col("lime"), (xi, yi), 4)
                a = spin * 10
                s.fill(col("white"), (xi + int(math.cos(a) * 2), yi + int(math.sin(a) * 2), 1, 1))
            elif kind == "bone":
                s.fill(col("black"), (xi - 6, yi - 2, 12, 5))
                s.fill(col("white"), (xi - 5, yi - 1, 10, 3))
                for bx in (xi - 6, xi + 4):
                    pygame.draw.circle(s, col("white"), (bx + 1, yi - 2), 2)
                    pygame.draw.circle(s, col("white"), (bx + 1, yi + 2), 2)
            elif kind in ("suds", "bubble"):
                pygame.draw.circle(s, col("sky"), (xi, yi), 5, 1)
                pygame.draw.circle(s, col("white"), (xi - 2, yi - 2), 1)
                pygame.draw.circle(s, col("sky"), (xi + 4, yi + 3), 2, 1)
            elif kind == "jet":
                s.fill(col("sky"), (xi - 2, yi - 2, 5, 20))
                s.fill(col("white"), (xi - 1, yi - 4, 3, 22))
            elif kind in ("feather", "dart"):
                c = "lavender" if kind == "dart" else "white"
                if vy != 0:
                    s.fill(col("black"), (xi - 2, yi - 6, 5, 12))
                    s.fill(col(c), (xi - 1, yi - 5, 3, 10))
                    s.fill(col("purple" if kind == "dart" else "gray"), (xi, yi - 5, 1, 10))
                else:
                    s.fill(col("black"), (xi - 6, yi - 2, 12, 5))
                    s.fill(col(c), (xi - 5, yi - 1, 10, 3))
                    s.fill(col("gray"), (xi - 5, yi, 10, 1))
            elif kind == "egg":
                pygame.draw.ellipse(s, col("black"), (xi - 4, yi - 5, 9, 11))
                pygame.draw.ellipse(s, col("white"), (xi - 3, yi - 4, 7, 9))
                s.fill(col("sky"), (xi - 1, yi - 2, 1, 2))
            elif kind == "lid":
                w = max(1, int(abs(math.cos(spin * 8)) * 6))
                pygame.draw.ellipse(s, col("black"), (xi - w - 1, yi - 6, w * 2 + 3, 13))
                pygame.draw.ellipse(s, col("gray"), (xi - w, yi - 5, w * 2 + 1, 11))
                s.fill(col("white"), (xi, yi - 4, 1, 3))
            elif kind == "can":
                art.draw_can(s, xi - 7, yi - 8, 1, t, "teal")

    def draw(self, s, t):
        k = self.kind
        if self.state == "dead" and self.y < -40:
            return
        hurt = self.flash > 0 and int(t * 20) % 2
        dizzy = self.state == "rest"
        angry = self.state in ("tell", "act", "move")
        x, y = int(self.x), int(self.y)
        if self.state == "dead":
            hurt = int(t * 10) % 2
        if k in ("bruno", "king"):
            draw_dog(s, x, y, t, self.face, angry, dizzy, hurt, k == "king", self.state == "act")
        elif k == "sweepo":
            draw_sweeper(s, x, y, t, self.face if self.state == "act" else (1 if x < W / 2 else -1), angry, dizzy, hurt)
        elif k == "coon":
            draw_coon(s, x, y, t, angry, dizzy, hurt)
        elif k == "owl":
            draw_owl(s, x, y, t, angry, dizzy, hurt)
        elif k == "claw":
            cx, cy = self.claw_pos()
            draw_crab(s, x, y, t, angry, dizzy, hurt, int(cx), int(cy))
        elif k == "gulls":
            n = max(0, self.hp - (1 if self.cur == "strike" and self.state in ("act", "rest", "hurt") else 0))
            if self.state != "dead":
                for i in range(n):
                    a = t * 1.6 + i * math.tau / max(1, n)
                    gx = x + int(math.cos(a) * (40 + 10 * (i % 2)))
                    gy = y + int(math.sin(a) * 5)
                    draw_gull(s, gx, gy, t + i, i == n - 1 and self.hp <= 2, False, False, math.cos(a) > 0)
            if self.cur == "strike" and self.state in ("act", "rest", "hurt") or self.state == "dead":
                gx, gy = (x, y) if self.state == "dead" else (int(self.hx), int(self.hy))
                draw_gull(s, gx, gy, t, self.hp <= 1, dizzy, hurt, self.tx > self.sx, landed=dizzy)
        if dizzy and k != "gulls":
            hx, hy = (int(self.hx), int(self.hy)) if k == "claw" else (x, y)
            for i in range(3):
                a = t * 6 + i * 2.1
                s.fill(col("yellow"), (hx + int(math.cos(a) * 10), hy - self.h // 2 - 4 + int(math.sin(a) * 3), 2, 2))
        if dizzy and int(t * 3) % 2:
            hx, hy = int(self.hx), int(self.hy)
            draw_text(s, "HOP!", hx, hy - (self.h // 2 if k not in ("gulls", "claw") else 8) - 14, "lime",
                      align="center", shadow="black")


# ----------------------------------------------------------------------------- costumes
def draw_dog(s, x, y, t, face, angry, dizzy, hurt, king, running):
    """BRUNO: a big fluffy guard dog with a cap and a studded collar (centre x, y)."""
    body = col("white") if hurt else col("peach" if not king else "orange")
    dark = col("brown" if not king else "choco")
    sc = 1.15 if king else 1.0
    bw, bh = int(28 * sc), int(18 * sc)
    step = int(t * 12) % 2 if running else 0
    pygame.draw.ellipse(s, col("black"), (x - bw // 2 - 1, y - bh // 2 + 2, bw + 2, bh))
    pygame.draw.ellipse(s, body, (x - bw // 2, y - bh // 2 + 3, bw, bh - 2))
    for lx in (x - bw // 2 + 4, x + bw // 2 - 8):
        s.fill(col("black"), (lx, y + bh // 2 - 2 + step, 5, 4))
        s.fill(dark, (lx + 1, y + bh // 2 - 2 + step, 3, 3))
    hx = x + face * (bw // 2 - 5)
    hy = y - bh // 2 + 2
    pygame.draw.circle(s, col("black"), (hx, hy), 9)
    pygame.draw.circle(s, body, (hx, hy), 8)
    for side in (-1, 1):       # floppy ears
        pygame.draw.ellipse(s, dark, (hx + side * 7 - 3, hy - 4, 6, 10))
    pygame.draw.ellipse(s, col("cream"), (hx - 4 + face * 2, hy + 1, 9, 6))
    s.fill(col("black"), (hx + face * 3 - 1, hy + 1, 3, 2))
    if dizzy:
        for side in (-1, 1):
            pygame.draw.circle(s, col("black"), (hx + side * 3, hy - 2), 2, 1)
    else:
        cute.eyes(s, hx, hy - 2, 3, face, "angry" if angry else "happy")
    if king:
        pts = [(hx - 6, hy - 7), (hx - 6, hy - 13), (hx - 3, hy - 9), (hx, hy - 14), (hx + 3, hy - 9), (hx + 6, hy - 13),
               (hx + 6, hy - 7)]
        pygame.draw.polygon(s, col("yellow"), pts)
        s.fill(col("red"), (hx - 1, hy - 10, 2, 2))
    else:
        s.fill(col("blue"), (hx - 6, hy - 9, 12, 3))       # guard cap
        s.fill(col("blue"), (hx + face * 4 - 2, hy - 7, 6, 1))
        s.fill(col("yellow"), (hx - 1, hy - 9, 2, 2))
    s.fill(col("red"), (hx - 6, hy + 7, 12, 2))           # studded collar
    for i in range(3):
        s.fill(col("yellow"), (hx - 4 + i * 4, hy + 7, 1, 1))
    tx = x - face * (bw // 2)
    wag = int(math.sin(t * (20 if angry else 8)) * 3)
    pygame.draw.line(s, dark, (tx, y), (tx - face * 4, y - 5 + wag))


def draw_sweeper(s, x, y, t, face, angry, dizzy, hurt):
    """SWEEPO: a mint street-sweeper truck with headlight eyes and spinning brushes."""
    body = col("white") if hurt else col("mint")
    pygame.draw.rect(s, col("black"), (x - 21, y - 12, 42, 22), border_radius=4)
    pygame.draw.rect(s, body, (x - 20, y - 11, 40, 20), border_radius=3)
    s.fill(col("teal"), (x - 20, y + 3, 40, 3))
    tank_x = x - 18 if face > 0 else x - 2
    s.fill(col("sky"), (tank_x, y - 9, 20, 9))          # the water tank
    s.fill(col("white"), (tank_x + 2, y - 8, 6, 1))
    cab_x = x + 6 if face > 0 else x - 18
    s.fill(col("black"), (cab_x, y - 9, 12, 8))
    s.fill(col("yellow" if not dizzy else "darkgray"), (cab_x + 2, y - 7, 3, 3))
    s.fill(col("yellow" if not dizzy else "darkgray"), (cab_x + 7, y - 7, 3, 3))
    if angry:
        s.fill(col("red"), (cab_x + 1, y - 9, 10, 1))
    if dizzy:
        draw_text(s, "~", tank_x + 6, y - 18, "sky", shadow=None)
    bx = x + 20 if face > 0 else x - 20
    for k in range(2):
        cy = y + 6 + k * 4 - 2
        pygame.draw.circle(s, col("black"), (bx, cy), 4)
        pygame.draw.circle(s, col("yellow"), (bx, cy), 3)
        a = t * 25 + k
        s.fill(col("orange"), (bx + int(math.cos(a) * 3), cy + int(math.sin(a) * 3), 1, 1))
    for wx in (x - 12, x + 12):
        pygame.draw.circle(s, col("black"), (wx, y + 10), 3)
        s.fill(col("gray"), (wx, y + 10, 1, 1))
    lamp = col("orange") if int(t * 6) % 2 else col("yellow")
    s.fill(lamp, (x - 2, y - 14, 4, 2))


def draw_gull(s, x, y, t, captain, dizzy, hurt, right, landed=False):
    body = col("white") if not hurt else col("yellow")
    flap = 0 if landed else int(math.sin(t * 14) * 3)
    d = 1 if right else -1
    for side in (-1, 1):
        pygame.draw.line(s, col("black"), (x, y), (x + side * 8, y - 2 - flap))
        pygame.draw.line(s, col("gray"), (x, y - 1), (x + side * 7, y - 3 - flap))
    pygame.draw.ellipse(s, col("black"), (x - 6, y - 4, 12, 9))
    pygame.draw.ellipse(s, body, (x - 5, y - 3, 10, 7))
    hx = x + d * 5
    pygame.draw.circle(s, col("black"), (hx, y - 3), 3)
    pygame.draw.circle(s, body, (hx, y - 3), 2)
    s.fill(col("orange"), (hx + d * 2 - (1 if d < 0 else 0), y - 3, 3, 1))
    if dizzy:
        s.fill(col("black"), (hx - 1, y - 4, 2, 1))
        s.fill(col("orange"), (hx + d * 4, y - 2, 4, 3))         # munching a fish
        s.fill(col("sky"), (hx + d * 4, y - 2, 2, 2))
    else:
        s.fill(col("black"), (hx, y - 4, 1, 1))
    if captain:
        s.fill(col("blue"), (hx - 3, y - 7, 6, 2))
        s.fill(col("white"), (hx - 2, y - 8, 4, 1))
    if landed:
        s.fill(col("orange"), (x - 2, y + 4, 1, 2))
        s.fill(col("orange"), (x + 2, y + 4, 1, 2))


def draw_coon(s, x, y, t, angry, dizzy, hurt):
    """BANDIT COON: a masked raccoon with a ringed tail and a sack of stolen snacks."""
    body = col("white") if hurt else col("gray")
    tw = int(math.sin(t * 6) * 2)
    for i in range(4):
        c = "black" if i % 2 else "darkgray"
        pygame.draw.circle(s, col(c), (x + 12 + i * 2, y + 4 - i * 3 + tw), 3)
    pygame.draw.ellipse(s, col("black"), (x - 11, y - 4, 22, 15))
    pygame.draw.ellipse(s, body, (x - 10, y - 3, 20, 13))
    sack_y = y + (2 if dizzy else 0)
    pygame.draw.circle(s, col("black"), (x - 12, sack_y + 2), 7)
    pygame.draw.circle(s, col("brown"), (x - 12, sack_y + 2), 6)
    s.fill(col("choco"), (x - 14, sack_y - 4, 4, 2))
    if dizzy and int(t * 8) % 2:
        s.fill(col("yellow"), (x - 14, sack_y - 7, 2, 2))      # rummaging for loot
        s.fill(col("pink"), (x - 10, sack_y - 9, 2, 2))
    pygame.draw.circle(s, col("black"), (x, y - 7), 8)
    pygame.draw.circle(s, body, (x, y - 7), 7)
    for side in (-1, 1):
        pygame.draw.polygon(s, col("darkgray"), [(x + side * 3, y - 13), (x + side * 7, y - 16), (x + side * 7, y - 10)])
    s.fill(col("black"), (x - 6, y - 9, 12, 4))              # the mask
    if dizzy:
        s.fill(col("white"), (x - 4, y - 8, 2, 1))
        s.fill(col("white"), (x + 2, y - 8, 2, 1))
    else:
        s.fill(col("red" if angry else "white"), (x - 4, y - 8, 2, 2))
        s.fill(col("red" if angry else "white"), (x + 2, y - 8, 2, 2))
    s.fill(col("cream"), (x - 2, y - 4, 5, 3))
    s.fill(col("black"), (x, y - 4, 1, 1))


def draw_crab(s, x, y, t, angry, dizzy, hurt, cx, cy):
    """KING CLAW: a big dock crab; one claw strikes and gets stuck in the boards."""
    body = col("white") if hurt else col("red")
    pygame.draw.line(s, col("black"), (x + 18, y + 4), (cx, cy))
    pygame.draw.line(s, col("red"), (x + 18, y + 3), (cx, cy - 1))
    for i in range(3):
        for side in (-1, 1):
            lx = x + side * (12 + i * 4)
            s.fill(col("black"), (lx - 1, y + 6, 3, 6 - i))
            s.fill(col("orange"), (lx, y + 6, 1, 5 - i))
    pygame.draw.ellipse(s, col("black"), (x - 22, y - 9, 44, 19))
    pygame.draw.ellipse(s, body, (x - 21, y - 8, 42, 17))
    s.fill(col("orange"), (x - 14, y - 3, 28, 2))
    for side in (-1, 1):
        ex = x + side * 7
        s.fill(col("black"), (ex, y - 14, 1, 6))
        pygame.draw.circle(s, col("black"), (ex, y - 15), 3)
        pygame.draw.circle(s, col("white"), (ex, y - 15), 2)
        s.fill(col("black"), (ex + (1 if angry else 0), y - 15, 1, 1))
    s.fill(col("yellow"), (x - 6, y - 12, 12, 3))           # a little crown
    for i in range(3):
        s.fill(col("yellow"), (x - 5 + i * 5, y - 14, 2, 2))
    # the other (resting) claw on the left
    pygame.draw.circle(s, col("black"), (x - 26, y + 6), 6)
    pygame.draw.circle(s, body, (x - 26, y + 6), 5)
    # the striking claw
    pygame.draw.circle(s, col("black"), (cx, cy), 7)
    pygame.draw.circle(s, body if not dizzy else col("pink"), (cx, cy), 6)
    gap = 0 if dizzy else int(abs(math.sin(t * 10)) * 3)
    s.fill(col("black"), (cx - 1, cy - 6, 2, 5 + gap))
    if dizzy:
        s.fill(col("brown"), (cx - 7, cy + 5, 14, 2))         # stuck in the planks!


def draw_owl(s, x, y, t, angry, dizzy, hurt):
    """HOOTSWORTH: a round purple night owl with huge glasses and glowing eyes."""
    body = col("white") if hurt else col("purple")
    flap = 0 if dizzy else int(math.sin(t * 10) * 4)
    for side in (-1, 1):
        pygame.draw.polygon(s, col("lavender"), [(x + side * 9, y - 4), (x + side * (19 + abs(flap)), y + flap),
                                                 (x + side * 9, y + 8)])
    pygame.draw.ellipse(s, col("black"), (x - 13, y - 12, 26, 25))
    pygame.draw.ellipse(s, body, (x - 12, y - 11, 24, 23))
    pygame.draw.ellipse(s, col("lavender"), (x - 7, y + 1, 14, 9))
    for side in (-1, 1):
        pygame.draw.polygon(s, body, [(x + side * 5, y - 10), (x + side * 11, y - 16), (x + side * 10, y - 7)])
        ex = x + side * 5
        pygame.draw.circle(s, col("black"), (ex, y - 4), 5)
        pygame.draw.circle(s, col("yellow" if not dizzy else "gray"), (ex, y - 4), 4)
        if dizzy:
            pygame.draw.circle(s, col("black"), (ex, y - 4), 2, 1)
        else:
            s.fill(col("red" if angry else "black"), (ex - 1, y - 5, 2, 2))
    s.fill(col("black"), (x - 1, y - 4, 2, 1))              # glasses bridge
    pygame.draw.polygon(s, col("orange"), [(x - 2, y), (x + 2, y), (x, y + 3)])
    s.fill(col("orange"), (x - 5, y + 11, 3, 2))
    s.fill(col("orange"), (x + 3, y + 11, 3, 2))
