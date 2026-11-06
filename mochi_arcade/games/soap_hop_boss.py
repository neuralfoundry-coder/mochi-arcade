"""SOAP HOP bosses (every 10th stage). Mirrored in ios/MochiArcade/Games/SoapHopBoss.swift.

Six original bosses, each with telegraphed patterns (crouch / swell / raise / swirl / shadow marks before
anything dangerous happens). Stage data (soap_hop_data.py) decides HP and the pattern list: later
appearances add patterns, and from tier 10 on bosses borrow 'guest' patterns from the others.
Damage: a bubble hit = 1, a bubble swallowed by WHIRL CLOUD = 2, popping a trapped minion close by = 4.
"""
import math
import random

from mochi_arcade.games import soap_hop_art as art
from mochi_arcade.gfx import W, draw_text

T = 8
TOP = 12
FLOOR_Y = TOP + 21 * T
LEFT, RIGHT = 2 * T, W - 2 * T
RADIUS = {"king": 15, "mop": 15, "vac": 16, "sock": 8, "soot": 16, "grime": 20}
MINION = {"king": "g", "mop": "g", "vac": "f", "sock": "f", "soot": "w", "grime": "b"}
FLYING = ("vac", "soot")


class Boss:
    def __init__(self, sd):
        self.kind = sd["boss"]
        self.name = sd["nm"]
        self.hp = self.maxhp = sd["hp"]
        self.pats = list(sd["pat"])
        self.spd = sd["spd"]
        self.r = RADIUS[self.kind]
        self.x = W / 2 + 56
        self.home_y = TOP + 40 if self.kind in FLYING else (TOP + 60 if self.kind == "sock" else FLOOR_Y - self.r)
        self.y = -40.0
        self.vx = self.vy = 0.0
        self.face = -1
        self.mode, self.mode_t, self.step = "enter", 0.0, 0
        self.pat_i = 0
        self.count = 0
        self.flash = 0.0
        self.phase = 1
        self.squash = self.lift = self.inhale = self.charge = 0.0
        self.walk = 0.0
        self.t = 0.0
        self.trail = []
        self.tx = W / 2
        self.dead = False

    # ------------------------------------------------------------------ helpers
    def segs(self):
        """Sock Serpent body segments (x, y), head first excluded."""
        if self.kind != "sock":
            return []
        n = 4 + int(math.ceil(8 * self.hp / self.maxhp))
        out = []
        for i in range(1, n + 1):
            k = len(self.trail) - 1 - i * 4
            if k < 0:
                break
            out.append(self.trail[k])
        return out

    def ground(self):
        return self.kind in ("king", "grime", "mop")

    def speed(self):
        return self.spd * (1 + 0.15 * (self.phase - 1))

    def hurt(self, sc, n, label=None):
        if self.mode in ("enter", "dying") or self.dead:
            return
        self.hp -= n
        self.flash = 0.12
        sc.add(20 * n)
        sc.hype.hit(1, fever=0.012)
        sc.app.audio.play("brick")
        if label:
            sc.floats.add(self.x, self.y - self.r - 8, label, "orange")
            sc.hype.hitstop(0.05)
            sc.app.shake(2, 0.15)
        new = 1 + (self.hp <= self.maxhp * 0.66) + (self.hp <= self.maxhp * 0.33)
        if self.hp <= 0:
            self.hp = 0
            self.mode, self.mode_t = "dying", 0.0
            sc.boss_defeated()
        elif new > self.phase:
            self.phase = new
            sc.hype.banner("GRRR!!", "IT'S GETTING ANGRY", color="red", dur=1.0, scale=2, sound="boom")
            sc.app.shake(4, 0.4)
            self.mode, self.mode_t = "rest", 0.6

    def hits(self, x, y, rad):
        """Does a circle (x, y, rad) touch the weak point?"""
        return math.hypot(x - self.x, y - self.y) < self.r + rad

    def touches(self, x, y, rad):
        """Does a circle touch any harmful part (body or sock segments)?"""
        if self.hits(x, y, rad):
            return True
        return any(math.hypot(x - sx, y - sy) < 5 + rad for sx, sy in self.segs())

    # ------------------------------------------------------------------ frame
    def update(self, sc, dt):
        self.t += dt
        self.flash -= dt
        p = sc.player
        if self.kind == "sock":
            self.trail.append((int(self.x), int(self.y)))
            if len(self.trail) > 80:
                del self.trail[0]
        if self.mode == "enter":
            self.y += (self.home_y - self.y) * min(1.0, dt * 2.2)
            if sc.state == "play":
                self.mode, self.mode_t = "rest", 1.0
            return
        if self.mode == "dying":
            self.mode_t += dt
            self.x += random.uniform(-1.5, 1.5)
            if self.mode_t > 1.8 and not self.dead:
                self.dead = True
                sc.boss_burst()
            return
        sp = self.speed()
        self.squash *= 0.85 ** (dt * 60)
        if self.mode == "rest":
            self.idle(sc, dt, sp)
            self.mode_t -= dt
            if self.mode_t <= 0:
                self.next_pattern(sc)
        else:
            getattr(self, "p_" + self.mode)(sc, dt, sp, p)
        airborne = self.mode == "hop" or (self.mode == "slam" and self.kind != "mop")
        if self.ground() and not airborne:
            self.vy = min(self.vy + 620 * dt, 300)
            self.y += self.vy * dt
            if self.y >= FLOOR_Y - self.r:
                self.y, self.vy = FLOOR_Y - self.r, 0.0
        self.x = max(LEFT + self.r, min(RIGHT - self.r, self.x))
        if sc.state == "play" and self.touches(p.cx, p.cy, 5):
            sc.hurt()

    def idle(self, sc, dt, sp):
        if self.kind in FLYING:
            self.x += (self.tx - self.x) * min(1.0, dt * 0.8)
            self.y = self.home_y + math.sin(self.t * 2) * 6
        elif self.kind == "sock":
            self.slither(dt, 38 * sp)
        self.inhale = max(0.0, self.inhale - dt * 2)
        self.charge = max(0.0, self.charge - dt * 2)
        if self.lift > 0:
            self.lift = max(0.0, self.lift - dt * 2)
        elif self.lift < 0:
            self.lift = min(0.0, self.lift + dt * 2)

    def next_pattern(self, sc):
        name = self.pats[self.pat_i % len(self.pats)]
        self.pat_i += 1
        if name == "minions" and sc.minion_count() >= 3:
            name = "spit"
        self.mode, self.mode_t, self.step = name, 0.0, 0
        p = sc.player
        self.face = 1 if p.cx > self.x else -1
        if name == "hop":
            self.count = 2 + self.phase
        elif name == "drift":
            self.tx = random.uniform(LEFT + 40, RIGHT - 40)
        elif name == "slither":
            a = random.uniform(0.4, 1.1) * random.choice((-1, 1))
            self.vx, self.vy = math.cos(a) * self.face, math.sin(a)

    def rest(self, sc, base=1.1):
        self.mode = "rest"
        self.mode_t = max(0.35, (base - 0.12 * (self.phase - 1)) / self.spd)
        self.step = 0

    # ------------------------------------------------------------------ patterns
    def p_hop(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:                         # crouch (telegraph)
            self.squash = 0.6
            if self.mode_t > 0.38 / sp:
                self.step, self.mode_t = 1, 0.0
                self.face = 1 if p.cx > self.x else -1
                self.vy = -(250 + 25 * self.phase)
                self.vx = self.face * (70 + 15 * self.phase) * sp
                sc.app.audio.play("jump")
        else:
            self.vy += 620 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.x < LEFT + self.r or self.x > RIGHT - self.r:
                self.vx = -self.vx
            if self.y >= FLOOR_Y - self.r and self.vy > 0:
                self.y, self.vy = FLOOR_Y - self.r, 0.0
                self.squash = 0.5
                sc.app.shake(2, 0.15)
                sc.parts.burst(self.x, FLOOR_Y - 2, 8, ("gray", "white"), 50, 0.4)
                if self.phase >= 2 or self.kind == "grime":
                    sc.shoot("wave", self.x - self.r, FLOOR_Y, -90 * sp, 0)
                    sc.shoot("wave", self.x + self.r, FLOOR_Y, 90 * sp, 0)
                self.count -= 1
                if self.count > 0:
                    self.step, self.mode_t = 0, 0.0
                else:
                    self.rest(sc)

    def p_slam(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.kind != "mop":                     # big bounce that ends in shockwaves
            if self.step == 0:
                self.squash = 0.8
                if self.mode_t > 0.55 / sp:
                    self.step = 1
                    self.vy = -340
                    self.vx = (p.cx - self.x) * 0.9
                    sc.app.audio.play("jump")
            else:
                self.vy += 620 * dt
                self.x += self.vx * dt
                self.y += self.vy * dt
                if self.y >= FLOOR_Y - self.r and self.vy > 0:
                    self.y, self.vy = FLOOR_Y - self.r, 0.0
                    self.squash = 0.8
                    self.quake(sc, sp)
                    self.rest(sc)
            return
        if self.step in (0, 2):                    # raise the mop (telegraph)
            self.lift = min(1.0, self.mode_t / (0.7 / sp))
            if self.mode_t > 0.7 / sp:
                self.step += 1
                self.mode_t = 0.0
                self.lift = -1.0
                self.quake(sc, sp)
        elif self.step == 1:
            if self.phase >= 2 and self.mode_t > 0.45:
                self.step, self.mode_t = 2, 0.0
            elif self.phase < 2 and self.mode_t > 0.4:
                self.rest(sc)
        else:
            if self.mode_t > 0.4:
                self.rest(sc)

    def quake(self, sc, sp):
        sc.app.shake(4, 0.35)
        sc.app.audio.play("boom")
        v = (100 + 20 * self.phase) * sp
        sc.shoot("wave", self.x - self.r, FLOOR_Y, -v, 0)
        sc.shoot("wave", self.x + self.r, FLOOR_Y, v, 0)
        sc.parts.burst(self.x, FLOOR_Y - 2, 14, ("white", "sky", "gray"), 70, 0.5)

    def p_walk(self, sc, dt, sp, p):
        self.mode_t += dt
        self.face = 1 if p.cx > self.x else -1
        self.x += self.face * 38 * sp * dt
        self.walk += dt
        if self.mode_t > 1.6:
            self.rest(sc, 0.6)

    def p_splash(self, sc, dt, sp, p):
        self.mode_t += dt
        self.lift = 0.5
        if self.step == 0 and self.mode_t > 0.45 / sp:
            self.step = 1
            sc.app.audio.play("bubble")
            for _ in range(3 + self.phase):
                sc.shoot("water", self.x + self.face * 10, self.y - 18, random.uniform(-110, 110), random.uniform(-270, -200))
        if self.mode_t > 0.9:
            self.rest(sc)

    def p_spit(self, sc, dt, sp, p):
        self.mode_t += dt
        self.squash = -0.25 if self.step == 0 else self.squash
        self.charge = 1.0
        if self.step == 0 and self.mode_t > 0.6 / sp:
            self.step = 1
            sc.app.audio.play("shoot")
            n = 3 if self.phase == 1 else 5
            ox, oy = self.x, self.y + (self.r * 0.3 if self.kind in FLYING else 0)
            base = math.atan2(p.cy - oy, p.cx - ox)
            for i in range(n):
                a = base + (i - (n - 1) / 2) * 0.28
                sc.shoot("dust", ox + math.cos(a) * self.r, oy + math.sin(a) * self.r, math.cos(a) * 85 * sp, math.sin(a) * 85 * sp)
        if self.mode_t > 0.95 / sp:
            self.rest(sc)

    def p_minions(self, sc, dt, sp, p):
        self.mode_t += dt
        self.squash = 0.2 * math.sin(self.mode_t * 30)
        if self.step == 0 and self.mode_t > 0.6:
            self.step = 1
            sc.app.audio.play("trap")
            for side in (-1, 1):
                if sc.minion_count() < 3:
                    sc.spawn_minion(MINION[self.kind], self.x + side * (self.r + 8), self.y - 4)
        if self.mode_t > 1.0:
            self.rest(sc)

    def p_drift(self, sc, dt, sp, p):
        self.mode_t += dt
        self.x += max(-50 * sp * dt, min(50 * sp * dt, self.tx - self.x))
        self.y = self.home_y + math.sin(self.t * 2) * 6
        if self.mode_t > 1.6:
            self.tx = max(LEFT + 40, min(RIGHT - 40, p.cx + random.uniform(-60, 60)))
            self.rest(sc, 0.5)

    def p_inhale(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:                         # swirl telegraph
            self.inhale = min(0.5, self.mode_t)
            if self.mode_t > 0.55:
                self.step, self.mode_t = 1, 0.0
                sc.app.audio.play("trap")
            return
        self.inhale = 1.0
        mx, my = self.x, self.y + 6
        if sc.state == "play" and abs(p.cx - mx) < 150:
            p.x += (1 if mx > p.cx else -1) * 45 * dt
        for b in sc.bubbles:
            if b.dead or b.kind != "normal":
                continue
            d = math.hypot(mx - b.x, my - b.y)
            if d < 10:
                b.dead = True
                sc.parts.burst(b.x, b.y, 6, ("white", "sky"), 40, 0.3)
                if b.enemy is not None:
                    self.hurt(sc, 4, "GULP!!")
                else:
                    self.hurt(sc, 2, "GULP!")
            elif d < 140:
                b.x += (mx - b.x) / d * 100 * dt
                b.y += (my - b.y) / d * 100 * dt
        if self.mode_t > 2.0 + 0.3 * self.phase:
            self.rest(sc)

    def p_puff(self, sc, dt, sp, p):
        self.mode_t += dt
        self.inhale = 0.6
        if self.step == 0 and self.mode_t > 0.5 / sp:
            self.step = 1
            sc.app.audio.play("shoot")
            n = 4 + self.phase
            for i in range(n):
                a = math.radians(50 + 80 * i / (n - 1))
                sc.shoot("dust", self.x, self.y + 8, math.cos(a) * 70 * sp, math.sin(a) * 70 * sp)
        if self.mode_t > 0.9:
            self.rest(sc)

    def p_rain(self, sc, dt, sp, p):
        self.mode_t += dt
        self.charge = 1.0
        if self.step == 0:
            self.step = 1
            sc.app.audio.play("warning" if self.kind == "soot" else "move")
            xs = [p.cx]
            for _ in range(2 + self.phase):
                xs.append(random.uniform(LEFT + 8, RIGHT - 8))
            for x in xs:
                sc.shoot("mark", x, FLOOR_Y, 0, 0)
        if self.mode_t > 1.4:
            self.rest(sc)

    def p_bolt(self, sc, dt, sp, p):
        self.mode_t += dt
        self.charge = 1.0
        if self.step == 0 and self.mode_t > 0.3:
            self.step = 1
            sc.shoot("bolt", p.cx, TOP, 0, 0)
            if self.phase >= 3:
                sc.shoot("bolt", p.cx - 56, TOP, 0, 0)
                sc.shoot("bolt", p.cx + 56, TOP, 0, 0)
        if self.mode_t > 1.4:
            self.rest(sc)

    def slither(self, dt, v):
        self.x += self.vx * v * dt
        self.y += self.vy * v * dt + math.sin(self.t * 6) * 20 * dt
        if self.x < LEFT + 10 or self.x > RIGHT - 10:
            self.vx = -self.vx
            self.x = max(LEFT + 10, min(RIGHT - 10, self.x))
        if self.y < TOP + 18 or self.y > FLOOR_Y - 10:
            self.vy = -self.vy
            self.y = max(TOP + 18, min(FLOOR_Y - 10, self.y))
        self.face = 1 if self.vx > 0 else -1

    def p_slither(self, sc, dt, sp, p):
        self.mode_t += dt
        self.slither(dt, 75 * sp)
        if self.mode_t > 2.6:
            self.rest(sc, 0.5)

    def p_lunge(self, sc, dt, sp, p):
        self.mode_t += dt
        if self.step == 0:                         # rear back and shake (telegraph)
            self.charge = 1.0
            self.x += math.sin(self.t * 50) * 0.6
            if self.mode_t > 0.55 / sp:
                self.step, self.mode_t = 1, 0.0
                d = max(1.0, math.hypot(p.cx - self.x, p.cy - self.y))
                self.vx, self.vy = (p.cx - self.x) / d, (p.cy - self.y) / d
                sc.app.audio.play("jump")
        else:
            self.charge = 0.0
            self.slither(dt, 200 * sp)
            if self.mode_t > 0.65:
                self.rest(sc)

    # ------------------------------------------------------------------ draw
    def draw(self, s, t):
        fl = self.flash > 0 and int(self.flash * 40) % 2 == 0
        x, y = int(self.x), int(self.y)
        if self.dead:
            return
        if self.kind == "king":
            art.king(s, x, y, t, self.squash, fl, self.phase)
        elif self.kind == "grime":
            art.grime(s, x, y, t, self.squash, fl, self.phase)
        elif self.kind == "mop":
            art.mop(s, x, y, t, self.lift, fl, self.walk, self.phase)
        elif self.kind == "vac":
            art.vac(s, x, y, t, self.inhale, fl, self.phase)
        elif self.kind == "soot":
            art.soot(s, x, y, t, self.charge, fl, self.phase)
        else:
            segs = self.segs()
            for i in range(len(segs) - 1, -1, -1):
                art.sock_seg(s, segs[i][0], segs[i][1], i, fl)
            art.sock_head(s, x, y, t, self.face, self.mode == "lunge" and self.step == 1, fl)
        if self.mode in ("spit", "lunge", "slam", "minions", "puff", "splash") and self.step == 0 and int(t * 10) % 2:
            draw_text(s, "!", x, y - self.r - 22, "red", 2, align="center", outline="black")
