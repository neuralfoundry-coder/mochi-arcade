"""WINDOW WATCH bosses (every 10th stage): six original sky troublemakers plus the final STORM KING.

A boss drifts in the sky and attacks by throwing things at the treasures (telegraphed: it flashes and a
warning sign blinks first) - or by swooping at them itself. Swat it with the paw (chain rings count too,
a MEOW SHOUT hits hard). Later tiers add a third phase and borrow attacks from the other bosses.
Mirrored in ios/MochiArcade/Games/WindowWatchBoss.swift.
"""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.gfx import col, draw_text
from mochi_arcade.games.window_watch_stages import KINDS, SLOTS, TOPY

HOME_Y = {"cloud": 46, "crow": 52, "jelly": 58, "twister": 60, "kite": 54, "moth": 60, "king": 48}
RADIUS = {"cloud": 19, "crow": 14, "jelly": 17, "twister": 15, "kite": 15, "moth": 15, "king": 24}
SPECIAL = ("swoop", "dash", "slam", "chase")


class Boss:
    def __init__(self, scene, spec):
        self.sc = scene
        self.kind, self.name = spec["kind"], spec["name"]
        self.hp = self.maxhp = spec["hp"]
        self.rate = spec["rate"]
        self.attacks = list(spec["attacks"])
        self.extra = list(spec["extra"])
        self.tier = spec["tier"]
        self.phases = spec["phases"]
        self.phase = 1
        self.x, self.y = 160.0, -40.0
        self.hy = float(HOME_Y[self.kind])
        self.r = RADIUS[self.kind]
        self.t = 0.0
        self.state = "enter"
        self.mode = "idle"
        self.mt = 0.0
        self.cd = 2.2
        self.tele = 0.0
        self.next = ""
        self.queue = []
        self.flash = 0.0
        self.inv = 0.0            # invulnerable after a hit (so a boss can't be shredded in seconds)
        self.dead_t = 0.0
        self.tx = self.ty = 0.0
        self.tg = 0
        self.drop_cd = 0.0
        self.gx = 160.0           # jelly: wander goal
        self.dir = 1

    # ---------------------------------------------------------------- helpers
    def sp(self):
        return 1.0 + 0.04 * self.tier

    def pool(self):
        if self.kind == "king":
            return self.attacks + self.extra
        base = self.attacks[:2] if self.phase == 1 and not self.extra else self.attacks
        return base + self.extra

    def interval(self):
        return 3.0 / (self.rate * (1.0, 1.3, 1.6)[self.phase - 1])

    def hittable(self):
        return self.state == "fight" and self.inv <= 0

    def home(self):
        """Where the boss wants to be while idle."""
        t, k = self.t, self.kind
        if k in ("cloud", "king"):
            return 160 + math.sin(t * 0.55) * 100, self.hy + math.sin(t * 1.3) * 5
        if k == "crow":
            return 160 + math.sin(t * 0.7) * 112, self.hy + math.sin(t * 1.4) * 14
        if k == "jelly":
            if abs(self.gx - self.x) < 6:
                self.gx = random.uniform(60, 260)
            step = 46 if self.gx > self.x else -46
            return self.x + step * 0.4, self.hy - abs(math.sin(t * 2.2)) * 12
        if k == "twister":
            return 160 + math.sin(t * 0.9) * 118, self.hy + math.sin(t * 3) * 2
        if k == "kite":
            return 160 + math.sin(t * 0.8) * 118, self.hy + math.sin(t * 2.2) * 16
        cx = self.sc.cx
        return self.x + max(-40.0, min(40.0, cx - self.x)), self.hy + math.sin(t * 2.5) * 8

    # ---------------------------------------------------------------- update
    def update(self, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.inv = max(0.0, self.inv - dt)
        if self.state == "enter":
            self.y += (self.hy - self.y) * min(1.0, dt * 2.5)
            self.x += (160 - self.x) * min(1.0, dt * 2.5)
            return
        if self.state == "dead":
            self.dead_t += dt
            self.y += 26 * dt
            self.x += math.sin(self.dead_t * 40) * 30 * dt
            if random.random() < 0.5:
                self.sc.parts.burst(self.x + random.uniform(-self.r, self.r), self.y + random.uniform(-self.r, self.r),
                                    4, ("white", "yellow", "pink"), 60, 0.5)
            return
        self.move(dt)
        if self.mode != "idle":
            return
        if self.tele > 0:
            self.tele -= dt
            if self.tele <= 0:
                self.perform(self.next)
            return
        self.cd -= dt
        if self.cd <= 0:
            if self.queue:
                self.next = self.queue.pop(0)
                self.tele = 0.5
            else:
                pool = self.pool()
                self.next = random.choice(pool)
                self.tele = 0.8
                if self.phase >= 3 and random.random() < 0.5:
                    self.queue.append(random.choice(pool))
            self.cd = self.interval()
            if self.next in SPECIAL:
                self.tg = self.sc.alive_target(random.randrange(3))
            self.sc.app.audio.play("hold")

    def move(self, dt):
        m = self.mode
        sp = self.sp()
        if m == "idle":
            hx, hy = self.home()
            self.x += (hx - self.x) * min(1.0, dt * 3)
            self.y += (hy - self.y) * min(1.0, dt * 3)
            return
        self.mt += dt
        if m == "swoop":
            tr = self.sc.treasures[self.tg]
            if self.step_to(tr.x, tr.top - 4, 120 * sp, dt):
                self.sc.boss_hits_treasure(self.tg)
                self.mode, self.mt = "back", 0.0
        elif m == "back":
            hx, hy = self.home()
            if self.step_to(hx, hy, 110, dt) or self.mt > 3:
                self.mode, self.mt = "idle", 0.0
        elif m == "dash":
            if self.mt < 0.9:
                self.step_to(self.x, 112, 140 * sp, dt)
            else:
                self.x += self.dir * 150 * sp * dt
                self.drop_cd -= dt
                if self.drop_cd <= 0:
                    self.drop_cd = 0.32
                    self.sc.spark(self.x, self.y + 6, self.sc.alive_target(self.sc.nearest_slot(self.x)), 0.0)
                if (self.dir > 0 and self.x > 292) or (self.dir < 0 and self.x < 28):
                    self.mode, self.mt = "back", 0.0
        elif m == "slam":
            if self.step_to(self.x, 124, 170 * sp, dt):
                self.sc.app.shake(3, 0.3)
                self.sc.app.audio.play("bubble")
                for i in range(6):
                    tg = self.sc.alive_target(i % 3)
                    self.sc.spawn("mini", self.x + (i - 2.5) * 6, self.y - 6, tg, KINDS["mini"][3] * sp)
                self.mode, self.mt = "back", 0.0
        elif m == "chase":
            cx, cy = self.sc.cx, max(40.0, min(118.0, self.sc.cy))
            self.step_to(cx, cy, 64 * sp, dt)
            self.drop_cd -= dt
            if self.drop_cd <= 0:
                self.drop_cd = 0.45
                tg = self.sc.alive_target(self.sc.nearest_slot(self.x))
                self.sc.spawn("seed", self.x, self.y + 8, tg, KINDS["seed"][3] * sp * 1.2, 4.0, self.mt)
            if self.mt > 3.5:
                self.mode, self.mt = "back", 0.0

    def step_to(self, tx, ty, speed, dt):
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d <= speed * dt or d < 1:
            self.x, self.y = tx, ty
            return True
        self.x += dx / d * speed * dt
        self.y += dy / d * speed * dt
        return False

    # ---------------------------------------------------------------- attacks
    def perform(self, atk):
        sc, sp = self.sc, self.sp()
        x, y, r = self.x, self.y, self.r
        n = 1 + self.phase
        if atk == "drizzle":
            for i in range(3 + n):
                sc.spawn("drop", x + random.uniform(-r, r), y + 8 - i * 10, sc.alive_target(random.randrange(3)),
                         KINDS["drop"][3] * sp)
        elif atk == "seed":
            sc.spawn("orb", x, y + r, sc.alive_target(random.randrange(3)), KINDS["orb"][3] * sp)
            sc.lightning = 0.25
            sc.app.audio.play("explode")
        elif atk == "curtain":
            m = 6 + self.phase
            gap = random.randrange(m)
            for i in range(m):
                if i != gap:
                    xx = 24 + i * 272 / (m - 1)
                    sc.spawn("drop", xx, TOPY, sc.alive_target(sc.nearest_slot(xx)), KINDS["drop"][3] * sp * 0.9)
        elif atk == "downpour":
            for i in range(10):
                xx = random.uniform(20, 300)
                sc.spawn("drop", xx, TOPY - i * 9, sc.alive_target(sc.nearest_slot(xx)), KINDS["drop"][3] * sp * 1.1)
        elif atk == "feathers":
            for i in range(4 + n):
                tg = sc.alive_target(i % 3)
                sc.spawn("feather", x, y + 4, tg, KINDS["feather"][3] * sp, ax=SLOTS[tg] + random.uniform(-26, 26))
        elif atk == "squad":
            side = random.choice((-1, 1))
            for i in range(2 + self.phase // 2):
                tg = sc.alive_target(i % 3)
                c = sc.spawn("crow", -8.0 if side > 0 else 328.0, 30.0 + i * 14, tg, KINDS["crow"][3] * sp)
                c.p = max(30.0, min(290.0, SLOTS[tg] + random.uniform(-40, 40)))
        elif atk == "bubbles":
            for i in range(2 + self.phase):
                sc.spawn("bubble", x + (i - 1) * 14, y + r, sc.alive_target(i % 3), KINDS["bubble"][3] * sp * 1.3,
                         y + r + random.uniform(30, 50), random.uniform(0, 6))
        elif atk == "spray":
            for i in range(5 + n):
                tg = sc.alive_target(i % 3)
                sc.spawn("mini", x, y + r, tg, KINDS["mini"][3] * sp * 0.9, ax=SLOTS[tg] + random.uniform(-20, 20))
        elif atk == "leafstorm":
            for i in range(6 + n):
                a = i * math.tau / (6 + n)
                sc.spawn("leaf", x + math.cos(a) * 20, y + math.sin(a) * 10, sc.alive_target(i % 3),
                         KINDS["leaf"][3] * sp * 1.2, random.uniform(8, 16), a)
        elif atk == "acorns":
            for i in range(2 + self.phase):
                sc.spawn("hail", x + (i - 1) * 10, y + r, sc.alive_target(random.randrange(3)), KINDS["hail"][3] * sp)
        elif atk == "gust":
            sc.gust_t = 3.2
            sc.gust_dir = random.choice((-1, 1))
            sc.hype.banner("GUST!", ">>>" if sc.gust_dir > 0 else "<<<", color="sky", dur=1.0, scale=1)
            for i in range(4):
                xx = random.uniform(30, 290)
                sc.spawn("leaf", xx, TOPY, sc.alive_target(sc.nearest_slot(xx)), KINDS["leaf"][3] * sp,
                         random.uniform(8, 14), random.uniform(0, 6))
        elif atk == "sparks":
            for i in range(5 + n):
                sc.spark(x, y + 6, sc.alive_target(i % 3), random.uniform(-24, 24))
            sc.app.audio.play("explode")
        elif atk == "rockets":
            for i in range(2 + self.phase // 2):
                xx = random.uniform(30, 290)
                sc.spawn("rocket", xx, 206.0, sc.alive_target(sc.nearest_slot(xx)), KINDS["rocket"][3] * sp,
                         random.uniform(50, 86))
        elif atk == "dust":
            tg = sc.alive_target(random.randrange(3))
            for i in range(5 + self.phase):
                sc.spawn("seed", x + random.uniform(-10, 10), y + 6 + random.uniform(-4, 4), tg,
                         KINDS["seed"][3] * sp * 1.2, random.uniform(3, 7), random.uniform(0, 6))
        elif atk == "mothlings":
            for i in range(2 + self.phase // 2):
                sc.spawn("moth", x + (i - 1) * 12, y + 6, sc.alive_target(i % 3), KINDS["moth"][3] * sp,
                         random.uniform(1.8, 3.0))
        elif atk == "swoop":
            self.mode, self.mt = "swoop", 0.0
            sc.app.audio.play("jump")
        elif atk == "dash":
            self.mode, self.mt = "dash", 0.0
            self.dir = 1 if self.x < 160 else -1
            self.drop_cd = 0.0
        elif atk == "slam":
            self.mode, self.mt = "slam", 0.0
        elif atk == "chase":
            self.mode, self.mt = "chase", 0.0
            self.drop_cd = 0.3

    # ---------------------------------------------------------------- hits
    def damage(self, n):
        """Returns True when this hit defeated the boss."""
        if self.state != "fight":
            return False
        self.hp -= n
        self.flash = 0.15
        self.inv = 0.4
        if self.hp <= 0:
            self.hp = 0
            self.state = "dead"
            self.mode = "idle"
            self.dead_t = 0.0
            return True
        frac = self.hp / self.maxhp
        g = self.sc.hype
        if self.phase == 1 and frac <= 0.5 and self.phases >= 2:
            self.phase = 2
            g.banner("GRRRR!", self.name + " IS MAD", color="red", dur=1.3)
            g.flash("red", 0.2)
            self.cd = min(self.cd, 0.6)
        elif self.phase == 2 and frac <= 0.25 and self.phases >= 3:
            self.phase = 3
            g.banner("FURIOUS!", "LAST PHASE", color="red", dur=1.3)
            g.flash("red", 0.25)
            self.cd = min(self.cd, 0.4)
        if self.mode == "swoop":
            self.mode, self.mt = "back", 0.0
            self.sc.floats.add(self.x, self.y - 16, "BONK!", "yellow")
        return False

    # ---------------------------------------------------------------- drawing
    def draw(self, s, t):
        if self.state == "dead" and self.dead_t > 1.6:
            return
        x, y = int(self.x), int(self.y)
        hit = self.flash > 0 and int(t * 30) % 2 == 0
        angry = self.phase >= 2 or self.mode != "idle"
        k = self.kind
        if k in ("cloud", "king"):
            draw_cloud(s, x, y, t, hit, angry, k == "king")
        elif k == "crow":
            draw_crow(s, x, y, t, hit, angry, self.mode)
        elif k == "jelly":
            draw_jelly(s, x, y, t, hit, angry, self.phase)
        elif k == "twister":
            draw_twister(s, x, y, t, hit, angry)
        elif k == "kite":
            draw_kite(s, x, y, t, hit, angry)
        else:
            draw_moth(s, x, y, t, hit, angry)
        if self.tele > 0 and self.state == "fight" and int(t * 10) % 2:
            draw_text(s, "!", x - 2, y - self.r - 14, "red", 2 if self.next in SPECIAL else 1, shadow="black")
            if self.next in SPECIAL:
                tr = self.sc.treasures[self.tg]
                for i in range(0, 10):
                    f = i / 10
                    s.fill(col("red"), (int(x + (tr.x - x) * f), int(y + (tr.top - y) * f), 2, 2))


def draw_cloud(s, x, y, t, hit, angry, king):
    body = "white" if hit else ("darkgray" if angry else "gray")
    light = "white" if not angry else "gray"
    puffs = ((-15, 3, 9), (-6, -5, 11), (7, -4, 10), (16, 3, 8), (0, 5, 11))
    if king:
        puffs = ((-20, 3, 11), (-8, -6, 13), (8, -5, 12), (21, 3, 10), (0, 6, 13))
    for dx, dy, r in puffs:
        pygame.draw.circle(s, col("black"), (x + dx, y + dy), r + 1)
    for dx, dy, r in puffs:
        pygame.draw.circle(s, col(body), (x + dx, y + dy), r)
    for dx, dy, r in puffs[1:3]:
        s.fill(col(light), (x + dx - 3, y + dy - r + 3, 5, 2))
        s.fill(col(light), (x + dx - 5, y + dy - r + 5, 2, 2))
    cute.eyes(s, x, y + 2, 6, 0, "angry" if angry else "happy", size=2)
    cute.mouth(s, x, y + 7, "angry" if angry else "happy")
    cute.blush(s, x, y + 5, 8)
    for i in range(3):     # its own little rain
        dy = int((t * 40 + i * 7) % 12)
        s.fill(col("sky"), (x - 10 + i * 10, y + 14 + dy, 1, 3))
    if angry and int(t * 6) % 3 == 0:
        pygame.draw.polygon(s, col("yellow"), [(x + 4, y + 12), (x - 2, y + 20), (x + 2, y + 20), (x - 3, y + 28),
                                               (x + 6, y + 18), (x + 2, y + 18)])
    if king:
        pygame.draw.polygon(s, col("yellow"), [(x - 10, y - 16), (x - 10, y - 26), (x - 5, y - 20), (x, y - 28),
                                               (x + 5, y - 20), (x + 10, y - 26), (x + 10, y - 16)])
        s.fill(col("red"), (x - 1, y - 21, 3, 3))
        s.fill(col("orange"), (x - 10, y - 17, 21, 1))


def draw_crow(s, x, y, t, hit, angry, mode):
    flap = int(math.sin(t * (14 if mode != "idle" else 8)) * 6)
    body = "white" if hit else "darkgray"
    for side in (-1, 1):
        pygame.draw.polygon(s, col("black"), [(x + side * 6, y - 3), (x + side * 26, y - 8 + flap),
                                              (x + side * 20, y + 2 + flap // 2), (x + side * 8, y + 6)])
        pygame.draw.polygon(s, col("gray"), [(x + side * 8, y - 1), (x + side * 22, y - 5 + flap),
                                             (x + side * 18, y + 1 + flap // 2), (x + side * 9, y + 4)])
    pygame.draw.polygon(s, col("black"), [(x - 4, y + 8), (x - 9, y + 16), (x, y + 12), (x + 9, y + 16), (x + 4, y + 8)])
    pygame.draw.ellipse(s, col("black"), (x - 12, y - 9, 25, 21))
    pygame.draw.ellipse(s, col(body), (x - 11, y - 8, 23, 19))
    s.fill(col("gray"), (x - 6, y + 2, 12, 5))
    # face
    cute.eyes(s, x, y - 2, 5, 0, "angry" if angry else "happy", size=2)
    pygame.draw.polygon(s, col("orange"), [(x - 3, y + 1), (x + 3, y + 1), (x, y + 6)])
    s.fill(col("black"), (x - 3, y + 1, 7, 1))
    # captain's cap
    s.fill(col("black"), (x - 9, y - 15, 19, 6))
    s.fill(col("blue"), (x - 8, y - 14, 17, 4))
    s.fill(col("ink"), (x - 10, y - 10, 21, 2))
    s.fill(col("yellow"), (x - 1, y - 13, 3, 2))
    s.fill(col("white"), (x - 8, y - 14, 17, 1))


def draw_jelly(s, x, y, t, hit, angry, phase):
    r = 17 - (phase - 1) * 2
    wob = math.sin(t * 5) * 1.5
    for i in range(5):     # dangly bits
        for j in range(5):
            px = x - 10 + i * 5 + int(math.sin(t * 4 + i + j * 0.6) * 2)
            py = y + r - 4 + j * 3
            s.fill(col("lavender" if (i + j) % 2 else "pink"), (px, py, 2, 2))
    pygame.draw.ellipse(s, col("black"), (int(x - r - 1 - wob), int(y - r - 1 + wob), int(2 * r + 2 + 2 * wob),
                                          int(2 * r + 2 - 2 * wob)))
    pygame.draw.ellipse(s, col("white" if hit else "lavender"), (int(x - r - wob), int(y - r + wob),
                                                                 int(2 * r + 2 * wob), int(2 * r - 2 * wob)))
    pygame.draw.ellipse(s, col("pink"), (x - r + 4, y - 2, 2 * r - 8, r - 2))
    pygame.draw.circle(s, col("white"), (x - r // 2, y - r // 2), 3)
    s.fill(col("white"), (x + r // 2, y - r // 2 - 2, 2, 2))
    cute.eyes(s, x, y - 1, 6, 0, "angry" if angry else "happy", size=2)
    cute.mouth(s, x, y + 5, "angry" if angry else "wow")
    cute.blush(s, x, y + 3, 8)


def draw_twister(s, x, y, t, hit, angry):
    for i in range(7):
        w = 40 - i * 5
        yy = y - 16 + i * 5
        xx = x + int(math.sin(t * 6 + i * 0.8) * 3)
        pygame.draw.ellipse(s, col("black"), (xx - w // 2 - 1, yy - 1, w + 2, 8))
        pygame.draw.ellipse(s, col("white" if hit else ("lavender" if i % 2 else "sky")), (xx - w // 2, yy, w, 6))
    for j in range(6):
        a = t * 4 + j * 1.05
        lx = x + int(math.cos(a) * 24)
        ly = y - 8 + j * 4 + int(math.sin(a) * 4)
        s.fill(col("black"), (lx - 1, ly - 1, 4, 3))
        s.fill(col("orange" if j % 2 else "yellow"), (lx, ly, 2, 1))
    cute.eyes(s, x, y - 10, 6, 0, "angry" if angry else "happy", size=2)
    cute.mouth(s, x, y - 5, "angry" if angry else "happy")


def draw_kite(s, x, y, t, hit, angry):
    pygame.draw.line(s, col("white"), (x - 6, y + 6), (x + 30, 200))
    wave = int(math.sin(t * 7) * 4)
    tail = [(x - 14, y), (x - 30, y - 9 + wave), (x - 25, y), (x - 30, y + 9 + wave)]
    pygame.draw.polygon(s, col("black"), tail)
    pygame.draw.polygon(s, col("yellow" if not hit else "white"), [(x - 15, y), (x - 28, y - 7 + wave),
                                                                   (x - 24, y), (x - 28, y + 7 + wave)])
    pygame.draw.ellipse(s, col("black"), (x - 18, y - 10, 36, 20))
    pygame.draw.ellipse(s, col("white" if hit else ("red" if angry else "orange")), (x - 17, y - 9, 34, 18))
    pygame.draw.ellipse(s, col("cream"), (x - 12, y + 1, 24, 7))
    for i in range(3):          # scales
        for j in range(2):
            sx, sy = x - 10 + i * 6 + j * 3, y - 6 + j * 4
            s.fill(col("yellow"), (sx, sy, 3, 1))
            s.fill(col("yellow"), (sx - 1, sy + 1, 1, 1))
    pygame.draw.circle(s, col("black"), (x + 15, y), 5)
    pygame.draw.circle(s, col("ink"), (x + 15, y), 3)
    pygame.draw.circle(s, col("white"), (x + 8, y - 3), 3)
    s.fill(col("black"), (x + 8 + (1 if angry else 0), y - 3, 2, 2))
    if angry:
        s.fill(col("black"), (x + 5, y - 7, 6, 1))
    for side in (-1, 1):
        pygame.draw.polygon(s, col("orange"), [(x - 2, y + side * 8), (x - 8, y + side * 14), (x + 4, y + side * 9)])


def draw_moth(s, x, y, t, hit, angry):
    flap = int(abs(math.sin(t * 6)) * 7)
    for side in (-1, 1):
        wx = x + (2 if side > 0 else -26)
        pygame.draw.ellipse(s, col("black"), (wx - 1, y - 16 + flap // 2, 26, 20 - flap))
        pygame.draw.ellipse(s, col("white" if hit else "lavender"), (wx, y - 15 + flap // 2, 24, 18 - flap))
        ex = x + side * 13
        pygame.draw.circle(s, col("purple"), (ex, y - 6), 4 - flap // 4)
        pygame.draw.circle(s, col("yellow"), (ex, y - 6), 2 - flap // 6)
        lx = x + (2 if side > 0 else -18)
        pygame.draw.ellipse(s, col("black"), (lx - 1, y + 1, 18, 12))
        pygame.draw.ellipse(s, col("pink"), (lx, y + 2, 16, 10))
    for side in (-1, 1):
        pygame.draw.line(s, col("black"), (x + side * 2, y - 10), (x + side * 8, y - 20))
        pygame.draw.circle(s, col("yellow"), (x + side * 8, y - 20), 2)
    pygame.draw.ellipse(s, col("black"), (x - 6, y - 12, 12, 26))
    pygame.draw.ellipse(s, col("white" if hit else "cream"), (x - 5, y - 11, 10, 24))
    for i in range(3):
        s.fill(col("peach"), (x - 4, y + 2 + i * 4, 8, 1))
    pygame.draw.ellipse(s, col("white"), (x - 6, y - 6, 12, 4))
    cute.eyes(s, x, y - 7, 3, 0, "angry" if angry else "happy")
