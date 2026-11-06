"""TOWER TABBY bosses (every 10th stage). Mirrored in ios/MochiArcade/Games/TowerTabbyBoss.swift.

Seven original bosses with telegraphed patterns (a glow, a shake or a dotted warning line comes first).
Many attacks end with the boss DAZED (stars circle it): POUNCE into a dazed boss for 3 damage or land on it
for 2. While Mikan holds a feather wand, swatted projectiles home back onto the boss (1 damage each).
Stage data (tower_tabby_data.py) sets HP and the pattern list; later fights add a guest pattern.
"""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.games import tower_tabby_data as data
from mochi_arcade.gfx import W, col, draw_text, lerp_col, sprite

FLOOR = data.LEVEL_Y[0]
TOPY = 14
RADIUS = {"kaw": 13, "storm": 15, "vac": 14, "mouse": 14, "spritz": 12, "dot": 8, "golem": 15}
HITBOX = {"kaw": (12, 9), "storm": (14, 10), "vac": (16, 7), "mouse": (15, 9), "spritz": (10, 12), "dot": (8, 8),
          "golem": (14, 14)}     # half width, half height: ground bosses stand on the floor at FLOOR - hh
FLYERS = ("kaw", "storm", "dot")
STORM_REMAP = {"d": "u", "r": "y", "w": "y"}


class Boss:
    def __init__(self, sd, sc):
        self.kind = sd["boss"]
        self.name = sd["nm"]
        self.hp = self.maxhp = sd["hp"]
        self.pats = list(sd["pat"])
        self.spd = sd["spd"]
        self.r = RADIUS[self.kind]
        self.hw, self.hh = HITBOX[self.kind]
        self.flyer = self.kind in FLYERS
        self.x = W / 2 + 60.0
        self.y = -30.0
        self.home_y = 58.0 if self.flyer else float(FLOOR - self.hh)
        self.vx = self.vy = 0.0
        self.face = -1
        self.mode, self.mode_t, self.step = "enter", 0.0, 0
        self.pat_i = 0
        self.count = 0
        self.flash = 0.0
        self.phase = 1
        self.daze = 0.0
        self.inv = 0.0
        self.air = False
        self.tx, self.ty = W / 2, 58.0
        self.t = 0.0
        self.dead = False
        self.squash = 0.0
        self.glow = 0.0
        self.way = []
        self.timer = 0.0

    # ------------------------------------------------------------------ helpers
    def speed(self):
        return self.spd * (1 + 0.15 * (self.phase - 1))

    def hits(self, x, y, rad):
        return abs(x - self.x) < self.hw + rad and abs(y - self.y) < self.hh + rad

    def touches(self, p):
        return abs(p.x - self.x) < self.hw + 4 and p.y - 10 < self.y + self.hh - 1 and p.y > self.y - self.hh + 3

    def hurt(self, sc, n, label=None):
        if self.mode in ("enter", "dying") or self.dead:
            return
        self.hp -= n
        self.flash = 0.15
        sc.add(50 * n)
        sc.hype.hit(1, fever=0.02)
        sc.app.audio.play("brick")
        if label:
            sc.floats.add(self.x, self.y - self.r - 8, label, "orange")
            sc.hype.hitstop(0.06 if n >= 2 else 0.03)
            sc.app.shake(2 + n * 0.5, 0.15)
        new = 1 + (self.hp <= self.maxhp * 0.66) + (self.hp <= self.maxhp * 0.33)
        if self.hp <= 0:
            self.hp = 0
            self.mode, self.mode_t, self.daze = "dying", 0.0, 0.0
            sc.boss_defeated()
        elif new > self.phase:
            self.phase = new
            sc.hype.banner("GRRR!!", "IT'S GETTING ANGRY", color="red", dur=1.0, scale=2, sound="boom")
            sc.app.shake(4, 0.4)
            self.daze = 0.0
            self.air = False
            self.rest(0.6)

    def rest(self, base=1.1):
        self.mode = "rest"
        self.mode_t = max(0.35, (base - 0.12 * (self.phase - 1)) / self.spd)
        self.step = 0

    def dazed(self, dur, sc, word="DIZZY!"):
        self.daze = max(0.6, dur - 0.12 * (self.phase - 1))
        self.mode = "dazed"
        self.vx = 0.0
        self.air = False
        sc.floats.add(self.x, self.y - self.r - 10, word, "yellow")

    # ------------------------------------------------------------------ frame
    def update(self, sc, dt):
        self.t += dt
        self.flash -= dt
        self.inv -= dt
        self.glow = max(0.0, self.glow - dt * 2)
        self.squash *= 0.85 ** (dt * 60)
        p = sc.p
        if self.mode == "enter":
            self.y += (self.home_y - self.y) * min(1.0, dt * 2.2)
            if sc.state == "play":
                self.rest(1.0)
            return
        if self.mode == "dying":
            self.mode_t += dt
            self.x += random.uniform(-1.5, 1.5)
            if self.mode_t > 1.8 and not self.dead:
                self.dead = True
                sc.boss_burst()
            return
        sp = self.speed()
        if self.mode == "dazed":
            self.daze -= dt
            if self.daze <= 0:
                self.daze = 0.0
                if self.flyer:
                    self.mode, self.step = "rise", 0
                else:
                    self.rest(0.8)
        elif self.mode == "rest":
            self.idle(sc, dt, sp)
            self.mode_t -= dt
            if self.mode_t <= 0:
                self.next_pattern(sc)
        elif self.mode == "rise":
            self.y += max(-90 * dt, min(90 * dt, self.home_y - self.y))
            if abs(self.y - self.home_y) < 2:
                self.rest(0.9)
        else:
            getattr(self, "p_" + self.mode)(sc, dt, sp, p)
        if not self.flyer and not self.air:
            self.vy = min(self.vy + 620 * dt, 300)
            self.y += self.vy * dt
            if self.y >= FLOOR - self.hh:
                self.y, self.vy = FLOOR - self.hh, 0.0
        self.x = max(self.hw + 2.0, min(W - self.hw - 2.0, self.x))
        if sc.state != "play" or self.dead or self.mode == "dying" or p.warp_t > 0:
            return
        if self.touches(p):
            if self.daze > 0:
                if self.inv <= 0 and (p.pounce or (p.vy > 0 and p.y < self.y)):
                    self.hurt(sc, 3 if p.pounce else 2, "POUNCE!" if p.pounce else "STOMP!")
                    p.vy = -190.0
                    p.vx = (-1 if p.x < self.x else 1) * 90.0
                    p.pounce = False
                    p.ground = None
                    p.inv = max(p.inv, 0.8)
                    self.inv = 0.6
                    self.daze = min(self.daze, 0.35)
            else:
                sc.hurt()

    def idle(self, sc, dt, sp):
        p = sc.p
        if self.flyer:
            self.x += (self.tx - self.x) * min(1.0, dt * 0.9)
            self.y = self.home_y + math.sin(self.t * 2.2) * 6
            if abs(self.tx - self.x) < 4:
                self.tx = random.uniform(40, W - 40)
        else:
            self.face = 1 if p.x > self.x else -1
            if abs(p.x - self.x) > self.hw + 30:          # creeps closer, but never walks into Mikan
                self.x += self.face * 18 * sp * dt

    def next_pattern(self, sc):
        name = self.pats[self.pat_i % len(self.pats)]
        self.pat_i += 1
        if name == "mice" and sum(1 for h in sc.hz if h.kind == "mouse") >= 3:
            name = "sparks" if self.flyer else "spit"
        self.mode, self.mode_t, self.step, self.timer = name, 0.0, 0, 0.0
        p = sc.p
        self.face = 1 if p.x > self.x else -1
        if name in ("drop", "spit", "toss", "spray"):
            self.count = 3 + self.phase
        elif name == "roll":
            self.count = 2 + (self.phase >= 3)

    def telegraph(self, sc, dur):
        """Glow + shake for dur seconds; returns True once it is over."""
        self.glow = 1.0
        self.x += math.sin(self.t * 60) * 0.6
        if self.mode_t >= dur:
            self.mode_t = 0.0
            return True
        return False

    # ------------------------------------------------------------------ patterns
    def p_swoop(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:                                   # line up above Mikan
            self.x += max(-130 * sp * dt, min(130 * sp * dt, p.x - self.x))
            self.y += (40 - self.y) * min(1.0, dt * 3)
            if self.mode_t > 0.8 or (abs(p.x - self.x) < 6 and self.mode_t > 0.4):
                self.step, self.mode_t = 1, 0.0
        elif self.step == 1:                                 # telegraph
            if self.telegraph(sc, 0.55 / sp):
                tx, ty = p.x, p.y - 6
                d = max(1.0, math.hypot(tx - self.x, ty - self.y))
                self.vx, self.vy = (tx - self.x) / d * 250 * sp, (ty - self.y) / d * 250 * sp
                self.step = 2
                sc.app.audio.play("shoot")
        else:
            prev = self.y + self.hh
            self.x += self.vx * dt
            self.y += self.vy * dt
            hit_y = None
            if self.vy > 0:
                hit_y = sc.support(self.x, prev - 1, self.y + self.hh)[0]
            if self.y + self.hh >= FLOOR:
                hit_y = FLOOR
            if hit_y is not None or self.x <= self.hw + 2 or self.x >= W - self.hw - 2 or self.mode_t > 1.6:
                if hit_y is not None:
                    self.y = hit_y - self.hh
                sc.app.audio.play("boom")
                sc.app.shake(3, 0.25)
                sc.parts.burst(self.x, self.y + self.r, 14, ("white", "gray", "brown"), 70, 0.5)
                if self.phase >= 2 and hit_y == FLOOR:
                    sc.shoot("wave", self.x - self.hw, FLOOR - 4, -100 * sp, 0.0, 4.0, 0.0, 3.0)
                    sc.shoot("wave", self.x + self.hw, FLOOR - 4, 100 * sp, 0.0, 4.0, 0.0, 3.0)
                self.dazed(1.8, sc, "BONK!")

    def p_drop(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.flyer:
            self.y += (34 - self.y) * min(1.0, dt * 3)
            self.x += max(-110 * sp * dt, min(110 * sp * dt, self.tx - self.x))
        else:
            self.squash = 0.3 * abs(math.sin(self.t * 12))
        if self.mode_t > 0.45 / sp:
            self.mode_t = 0.0
            if self.count <= 0:
                self.rest(1.0)
                return
            self.count -= 1
            x = self.x if self.flyer else random.uniform(16, W - 16)
            if not self.flyer:
                x = max(12.0, min(W - 12.0, p.x + random.uniform(-70, 70)))
            h = sc.spawn_haz("cone", x, TOPY + 4 if not self.flyer else self.y + 6)
            h.vy = 40.0
            self.tx = max(30.0, min(W - 30.0, p.x + random.uniform(-60, 60)))
            sc.app.audio.play("move")

    def p_feathers(self, sc, dt, sp, p, kind="feather"):
        self.mode_t += dt
        if self.step == 0:
            if self.telegraph(sc, 0.5 / sp):
                n = (3 if kind == "feather" else 5) + self.phase
                base = math.atan2(p.y - 6 - self.y, p.x - self.x)
                v = (85 if kind == "feather" else 100) * sp
                for i in range(n):
                    a = base + (i - (n - 1) / 2) * 0.22
                    sc.shoot(kind, self.x, self.y, math.cos(a) * v, math.sin(a) * v, 3.0, 0.0, 5.0)
                sc.app.audio.play("shoot")
                self.step = 1
        elif self.mode_t > 0.4:
            self.rest(1.1)

    def p_sparks(self, sc, dt, sp, p):
        self.p_feathers(sc, dt, sp, p, "spark")

    def p_beam(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            xs = [p.x]
            if self.phase >= 2:
                xs += [p.x - 72, p.x + 72]
            for x in xs:
                if 4 < x < W - 4:
                    sc.shoot("beam", x, 0.0, 0.0, 0.0, 3.0, 0.8 / sp, 0.35)
            self.glow = 1.0
            sc.app.audio.play("warning")
            self.step = 1
        elif self.mode_t > 1.3:
            self.rest(1.0)

    def p_mice(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            if self.telegraph(sc, 0.4):
                for i in range(1 + (self.phase + 1) // 2):
                    d = 1 if i % 2 == 0 else -1
                    h = sc.spawn_haz("mouse", self.x + d * 6, self.y - 4, d * 60.0, -150.0)
                    h.dir = d
                sc.app.audio.play("pop")
                self.step = 1
        elif self.mode_t > 0.5:
            self.rest(1.2)

    def p_spit(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            if self.telegraph(sc, 0.4 / sp):
                self.step = 1
            return
        if self.mode_t > 0.35 / sp:
            self.mode_t = 0.0
            if self.count <= 0 or self.count > 6:
                self.rest(1.0)
                return
            self.count -= 1
            self.face = 1 if p.x > self.x else -1
            sc.spawn_haz("dust", self.x + self.face * self.r, self.y - 2, self.face * 70.0, -80.0)
            sc.app.audio.play("shoot")

    def p_dash(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            if int(self.t * 20) % 2:
                sc.parts.sparkle(self.x - self.face * self.r, self.y + self.r - 2, "white")
            if self.telegraph(sc, 0.55 / sp):
                self.step = 1
                sc.app.audio.play("shoot")
        else:
            self.x += self.face * 165 * sp * dt
            if self.x <= self.hw + 2 or self.x >= W - self.hw - 2:
                sc.app.audio.play("boom")
                sc.app.shake(4, 0.3)
                sc.parts.burst(self.x + self.face * self.r, self.y, 14, ("white", "gray"), 70, 0.5)
                if self.phase >= 2:
                    for _ in range(2):
                        h = sc.spawn_haz("cone", random.uniform(20, W - 20), TOPY + 4)
                        h.vy = 30.0
                self.dazed(1.7, sc, "BONK!")

    def p_suck(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            if self.telegraph(sc, 0.6 / sp):
                self.step = 1
                sc.app.audio.play("bubble")
        elif self.step == 1:
            self.glow = 1.0
            if p.climb is None and abs(p.y - self.y) < 46:
                p.x += (1 if self.x > p.x else -1) * 44 * sp * dt
            if int(self.t * 30) % 2:
                a = random.uniform(-0.6, 0.6) + (0 if self.face > 0 else math.pi)
                sc.parts.p.append([self.x + math.cos(a) * 40, self.y + math.sin(a) * 30, -math.cos(a) * 80,
                                   -math.sin(a) * 60, 0.45, 0.45, "white", 0, 1])
            if self.mode_t > 2.2:
                self.step = 2
                sc.app.audio.play("explode")
                self.dazed(1.9, sc, "OVERHEAT!")

    def p_slam(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            self.squash = 0.6
            if self.mode_t > 0.4 / sp:
                self.step, self.mode_t = 1, 0.0
                self.air = True
                self.vy = -330.0
                self.vx = max(-150 * sp, min(150 * sp, (p.x - self.x) / 0.95))
                sc.app.audio.play("jump")
        else:
            self.vy += 700 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.y >= FLOOR - self.hh and self.vy > 0:
                self.y, self.vy = FLOOR - self.hh, 0.0
                self.air = False
                self.squash = 0.6
                sc.app.shake(3, 0.25)
                sc.app.audio.play("boom")
                sc.parts.burst(self.x, FLOOR - 2, 12, ("white", "gray"), 60, 0.5)
                sc.shoot("wave", self.x - self.hw, FLOOR - 4, -100 * sp, 0.0, 4.0, 0.0, 3.0)
                sc.shoot("wave", self.x + self.hw, FLOOR - 4, 100 * sp, 0.0, 4.0, 0.0, 3.0)
                self.dazed(1.25, sc)

    def p_hop(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            self.squash = 0.5
            if self.mode_t > 0.35 / sp:
                self.step, self.mode_t = 1, 0.0
                self.air = True
                self.vy = -300.0
                tx = W - self.x if abs(W - 2 * self.x) > 60 else (40 if self.x > W / 2 else W - 40)
                self.vx = (tx - self.x) / 0.86
                sc.app.audio.play("jump")
        else:
            self.vy += 700 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.y >= FLOOR - self.hh and self.vy > 0:
                self.y, self.vy = FLOOR - self.hh, 0.0
                self.air = False
                sc.app.shake(2, 0.15)
                sc.parts.burst(self.x, FLOOR - 2, 8, ("sky", "white"), 50, 0.4)
                self.dazed(0.9, sc, "SPLOSH!")

    def p_spray(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            if self.telegraph(sc, 0.4 / sp):
                self.step = 1
            return
        if self.mode_t > 0.16 / sp:
            self.mode_t = 0.0
            if self.count <= 0 or self.count > 8:
                self.rest(1.1)
                return
            self.count -= 1
            vx = (p.x - self.x) / 1.1 * random.uniform(0.7, 1.3)
            sc.shoot("spray", self.x + self.face * 6, self.y - self.r, vx, -170 - random.uniform(0, 80), 2.5, 0.0, 4.0)
            sc.app.audio.play("bubble")

    def p_jet(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            ys = [p.y - 6]
            if self.phase >= 3:
                other = [y for y in (data.LEVEL_Y[1] - 6, data.LEVEL_Y[2] - 6, data.LEVEL_Y[0] - 6)
                         if abs(y - ys[0]) > 20]
                if other:
                    ys.append(random.choice(other))
            for y in ys:
                sc.shoot("jet", 0.0, y, 0.0, 0.0, 3.0, 0.85 / sp, 0.6)
            self.glow = 1.0
            sc.app.audio.play("warning")
            self.step = 1
        elif self.mode_t > 0.85 / sp + 0.7:
            self.dazed(1.8, sc, "GURGLE!")

    def p_trace(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:
            self.way = [(random.uniform(30, W - 30), random.uniform(40, 120)),
                        (random.uniform(30, W - 30), random.uniform(40, 140)),
                        (p.x, p.y - self.hh)]
            self.step = 1
            self.mode_t = 0.0
            sc.app.audio.play("warning")
        elif self.step == 1:
            self.glow = 1.0
            if self.mode_t > 0.85 / sp:
                self.step, self.mode_t = 2, 0.0
        elif self.step == 2:
            if not self.way:
                sc.app.shake(2, 0.15)
                sc.parts.burst(self.x, self.y, 14, ("red", "hotpink", "white"), 60, 0.5)
                g = sc.support(self.x, self.y, FLOOR + 1)[0]
                self.y = (g if g is not None else FLOOR) - self.hh
                self.dazed(1.7, sc, "FIZZLE!")
                return
            tx, ty = self.way[0]
            d = math.hypot(tx - self.x, ty - self.y)
            step = 280 * sp * dt
            if d <= step:
                self.x, self.y = tx, ty
                self.way.pop(0)
            else:
                self.x += (tx - self.x) / d * step
                self.y += (ty - self.y) / d * step
            self.timer -= dt
            if self.phase >= 2 and self.timer <= 0:
                self.timer = 0.05
                sc.shoot("spark", self.x, self.y, 0.0, 0.0, 2.0, 0.0, 0.5)

    def p_roll(self, sc, dt, sp, p):
        """Bounces across the room in big hops (run underneath!), dizzy after the last wall."""
        self.mode_t += dt
        if self.step == 0:
            if self.telegraph(sc, 0.6 / sp):
                self.step = 1
                self.air = True
                self.vy = -260.0
                sc.app.audio.play("jump")
        else:
            self.vy += 640 * dt
            self.x += self.face * 120 * sp * dt
            self.y += self.vy * dt
            if self.y >= FLOOR - self.hh and self.vy > 0:
                self.y = FLOOR - self.hh
                self.vy = -260.0
                self.squash = 0.5
                sc.app.audio.play("lock")
                sc.parts.burst(self.x, FLOOR - 2, 6, ("pink", "white"), 40, 0.3)
            if self.x <= self.hw + 2 or self.x >= W - self.hw - 2:
                self.face = -self.face
                self.x = max(self.hw + 3.0, min(W - self.hw - 3.0, self.x))
                self.count -= 1
                sc.app.audio.play("boom")
                sc.app.shake(3, 0.2)
                if self.phase >= 2:
                    sc.spawn_haz("yarn", random.uniform(30, W - 30), TOPY + 4)
                if self.count <= 0:
                    self.air = False
                    self.dazed(1.7, sc)

    def p_toss(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.mode_t > 0.32 / sp:
            self.mode_t = 0.0
            if self.count <= 0 or self.count > 6:
                self.rest(1.1)
                return
            self.count -= 1
            vx = (p.x - self.x) * 0.9 + random.uniform(-25, 25)
            sc.spawn_haz("yarn", self.x, self.y - self.r, vx, -230.0)
            self.squash = 0.4
            sc.app.audio.play("jump")

    # ------------------------------------------------------------------ draw
    def draw(self, s, t):
        if self.dead:
            return
        x, y, r = int(self.x), int(self.y), self.r
        hit = self.flash > 0 and int(self.flash * 30) % 2
        k = self.kind
        if self.mode == "trace" and self.step == 1:
            pts = [(self.x, self.y)] + self.way
            for i in range(len(pts) - 1):
                (ax, ay), (bx, by) = pts[i], pts[i + 1]
                n = int(math.hypot(bx - ax, by - ay) / 6)
                for j in range(n):
                    if (j + int(t * 20)) % 2:
                        s.fill(col("red"), (int(ax + (bx - ax) * j / max(1, n)), int(ay + (by - ay) * j / max(1, n)), 2, 2))
        if self.glow > 0 and int(t * 16) % 2:
            pygame.draw.circle(s, col("yellow" if k != "dot" else "hotpink"), (x, y), r + 4, 1)
        if k in ("kaw", "storm"):
            remap = STORM_REMAP if k == "storm" else None
            if hit:
                remap = {"k": "w", "d": "w", "i": "w", "u": "w"}
            name = "tt_kaw_dazed" if self.daze > 0 else "tt_kaw_fly"
            fr = 0 if self.daze > 0 else int(t * 10) % 3
            img = sprite(name, fr, self.face > 0, remap, 2)
            s.blit(img, (x - 16, y - 12))
            if k == "storm" and int(t * 10) % 3 == 0:
                for i in range(3):
                    a = t * 5 + i * 2.1
                    s.fill(col("yellow"), (int(x + math.cos(a) * 20), int(y + math.sin(a) * 14), 2, 2))
        elif k == "vac":
            body = col("white") if hit else col("red" if self.daze > 0 else "darkgray")
            pygame.draw.ellipse(s, col("black"), (x - 17, y - 8, 34, 16))
            pygame.draw.ellipse(s, body, (x - 16, y - 7, 32, 14))
            pygame.draw.ellipse(s, col("gray"), (x - 13, y - 7, 26, 6))
            s.fill(col("black"), (x - 7, y - 4, 14, 5))
            eye = "yellow" if self.daze > 0 else ("red" if self.glow > 0 else "lime")
            s.fill(col(eye), (x - 5 + self.face, y - 3, 3, 2))
            s.fill(col(eye), (x + 2 + self.face, y - 3, 3, 2))
            nx = x + self.face * 16
            s.fill(col("black"), (min(nx, nx + self.face * 7), y, 8, 5))
            s.fill(col("gray"), (min(nx, nx + self.face * 7) + 1, y + 1, 6, 3))
            for i in range(-12, 13, 4):
                s.fill(col("yellow"), (x + i, y + 5, 2, 1))
            if self.daze > 0:
                for i in range(3):
                    s.fill(col("white"), (x - 4 + i * 4, y - 12 - int((t * 20 + i * 5) % 10), 2, 2))
        elif k == "mouse":
            sq = int(self.squash * 5)
            body = col("white") if hit else col("gray")
            pygame.draw.ellipse(s, col("black"), (x - 18, y - 10 + sq, 36, 20 - sq))
            pygame.draw.ellipse(s, body, (x - 17, y - 9 + sq, 34, 18 - sq))
            ex = x + self.face * 9
            for dx in (-5, 5):
                pygame.draw.circle(s, col("black"), (ex + dx - self.face * 4, y - 10 + sq), 5)
                pygame.draw.circle(s, col("pink"), (ex + dx - self.face * 4, y - 10 + sq), 3)
            cute.eyes(s, ex - self.face * 2, y - 3 + sq, 3, self.face, "sleepy" if self.daze > 0 else "angry")
            pygame.draw.circle(s, col("pink"), (x + self.face * 17, y + sq), 2)
            pygame.draw.polygon(s, col("yellow"), [(x - 6, y - 9 + sq), (x - 6, y - 15 + sq), (x - 3, y - 12 + sq),
                                                   (x, y - 16 + sq), (x + 3, y - 12 + sq), (x + 6, y - 15 + sq),
                                                   (x + 6, y - 9 + sq)])
            kw = 2 + int(abs(math.sin(t * (2 if self.daze > 0 else 9))) * 4)
            kx = x - self.face * 18
            s.fill(col("yellow"), (kx - 1, y - 4 + sq, 3, 3))
            s.fill(col("orange"), (kx - kw, y - 7 + sq, 2 * kw + 1, 2))
            pygame.draw.line(s, col("pink"), (x - self.face * 15, y + 5), (x - self.face * 24, y + 1))
        elif k == "spritz":
            sq = int(self.squash * 4)
            body = col("white") if hit else col("sky")
            pygame.draw.rect(s, col("black"), (x - 10, y - 12 + sq, 20, 25 - sq), border_radius=4)
            pygame.draw.rect(s, body, (x - 9, y - 11 + sq, 18, 23 - sq), border_radius=4)
            s.fill(col("blue"), (x - 9, y + 4, 18, 8))
            s.fill(col("white"), (x - 6, y - 6 + sq, 12, 8))
            cute_mood = "sleepy" if self.daze > 0 else "angry"
            cute.eyes(s, x, y - 3 + sq, 3, self.face, cute_mood)
            s.fill(col("black"), (x - 4, y - 16 + sq, 8, 5))
            s.fill(col("blue"), (x - 3, y - 15 + sq, 6, 3))
            nx = x + self.face * 4
            s.fill(col("blue"), (min(nx, nx + self.face * 6), y - 15 + sq, 7, 2))
            s.fill(col("black"), (x + self.face * 3 - 1, y - 11 + sq, 2, 4))
        elif k == "dot":
            pulse = 1 + int(abs(math.sin(t * 6)) * 2)
            rr = r + (4 if self.daze > 0 else 0)
            for i in range(3, 0, -1):
                pygame.draw.circle(s, lerp_col("red", "deep", i * 0.25), (x, y), rr + i * 2 + pulse)
            pygame.draw.circle(s, col("white" if hit else "red"), (x, y), rr)
            pygame.draw.circle(s, col("hotpink"), (x - 2, y - 2), rr // 2)
            s.fill(col("white"), (x - 3, y - 3, 2, 2))
            if self.daze > 0:
                    cute.eyes(s, x, y + 1, 3, 0, "sleepy")
            else:
                for i in range(4):
                    s.fill(col("hotpink"), (int(x - self.vx * 0.02 * i) - 1, int(y - self.vy * 0.02 * i) - 1, 2, 2))
        elif k == "golem":
            sq = int(self.squash * 4)
            base = "white" if hit else "hotpink"
            pygame.draw.circle(s, col("black"), (x, y + sq // 2), r + 1)
            pygame.draw.circle(s, col(base), (x, y + sq // 2), r)
            for j in range(4):
                a = (x * 0.08 if self.mode == "roll" else 0) + j * 0.8
                dx, dy = math.cos(a) * r, math.sin(a) * r
                pygame.draw.line(s, col("purple"), (int(x - dx * 0.9), int(y - dy * 0.9)), (int(x + dx * 0.9), int(y + dy * 0.9)))
            cute.eyes(s, x + self.face * 2, y - 3, 4, self.face, "sleepy" if self.daze > 0 else "angry", size=2)
            for side in (-1, 1):
                wob = int(math.sin(t * 6 + side) * 3)
                pygame.draw.line(s, col("hotpink"), (x + side * r, y), (x + side * (r + 6), y - 6 + wob))
        if self.daze > 0:
            for i in range(3):
                a = t * 6 + i * 2.1
                s.fill(col("yellow"), (int(x + math.cos(a) * (r + 2)), int(y - r - 4 + math.sin(a) * 3), 2, 2))
        elif self.glow > 0 and self.mode not in ("rest", "rise"):
            draw_text(s, "!", x, y - r - 14, "red" if int(t * 12) % 2 else "yellow", align="center", shadow=None)
