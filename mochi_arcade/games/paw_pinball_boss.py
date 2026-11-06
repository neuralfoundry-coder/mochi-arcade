"""PAW PINBALL bosses: five troublemakers who barge into the cafe arena (every 10th stage).

BUSTER the bully dog tosses bones and charges; ROBO-VAC sucks balls in and spits dust bunnies; CAW the crow
throws pebbles, hides behind his wings and dives to steal the ball; CUKE the cucumber hops with shockwaves and
sends pickles at the paws; SPRITZ the spray bottle soaks a paw with a water jet and leaves a slowing mist.
Every attack is telegraphed (a wind-up pose plus a red marker). Things thrown at a paw stun it - unless the paw
is swinging up or held up when they arrive, which bats them back for a COUNTER hit.
Later rounds borrow attacks from the others; under half health they get ANGRY (faster, more often).
Ported in PawPinballBoss.swift.
"""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.gfx import col, draw_text
from mochi_arcade.games import paw_pinball_tables as T

MOVES = {"buster": ["toss", "charge"], "robovac": ["suck", "bunnies"], "caw": ["toss", "shield", "dive"],
         "cuke": ["hop", "pickles"], "spritz": ["squirt", "mist"]}
RADIUS = {"buster": 13.0, "robovac": 13.0, "caw": 11.0, "cuke": 12.0, "spritz": 12.0}
HOME_Y = {"buster": 52.0, "robovac": 54.0, "caw": 46.0, "cuke": 56.0, "spritz": 38.0}
TELL = {"toss": 0.75, "charge": 0.7, "suck": 0.9, "bunnies": 0.5, "shield": 0.45, "dive": 0.85, "hop": 0.9,
        "pickles": 0.55, "squirt": 0.85, "mist": 0.5}
X_MIN, X_MAX = 124.0, 212.0
TOSSED = {"buster": "bone", "caw": "pebble", "robovac": "bone", "cuke": "pebble", "spritz": "drop"}


class Boss:
    def __init__(self, sc, spec):
        self.sc = sc
        self.kind = spec["kind"]
        self.name = spec["name"]
        self.title = spec["title"]
        self.hp = self.maxhp = spec["hp"]
        self.spd = spec["speed"]
        self.rate = spec["rate"]
        self.round = spec["round"]
        self.moves = list(MOVES[self.kind]) + [MOVES[e][0] for e in spec["extra"] if MOVES[e][0] not in MOVES[self.kind]]
        self.r = RADIUS[self.kind]
        self.home_y = HOME_Y[self.kind]
        self.x, self.y = 168.0, -24.0
        self.state = "enter"        # enter | idle | fight | dead
        self.t = 0.0
        self.cool = 2.2
        self.act = ""
        self.act_t = 0.0
        self.phase = 0              # 0 wind-up, 1 doing it
        self.flash = 0.0
        self.shield = 0.0
        self.iframes = 0.0          # brief invulnerability after a hit
        self.angry = False
        self.dir = 1
        self.ang = 0.0
        self.side = 0               # targeted paw (0 left, 1 right)
        self.tx = self.ty = 0.0     # dive / hop target
        self.sx = self.sy = 0.0     # where an act started
        self.vx = 0.0
        self.suck = 0.0
        self.jet = 0.0
        self.mists = []             # [x, y, time]
        self.bunnies = []           # [x, y, time]
        self.pickles = []           # [x, y, vy, side]
        self.projs = []             # [x, y, vx, vy, kind, side, back]
        self.held = None
        self.held_t = 0.0
        self.dead_t = 0.0
        self.hits = 0

    # ---------------------------------------------------------------- scene hooks
    def solid(self):
        return self.state == "fight" and not (self.act == "dive" and self.phase == 1)

    def dyn(self):
        out = []
        if self.state == "fight":
            if self.act == "dive" and self.phase == 1:
                out.append([self.x, self.y, self.r, "grab", False, 0])
            elif self.act == "suck" and self.phase == 1:
                out.append([self.x, self.y, self.r, "eat", False, 0])
            else:
                out.append([self.x, self.y, self.r, "boss", True, 0])
        for i, b in enumerate(self.bunnies):
            out.append([b[0], b[1], 4.0, "bunny", True, i])
        for i, p in enumerate(self.pickles):
            out.append([p[0], p[1], 4.0, "pickle", True, i])
        return out

    def hit(self, dmg, x=None, y=None):
        """A ball (or a counter / fish missile) hits the boss. Returns True if it hurt."""
        sc = self.sc
        if self.state != "fight":
            return False
        if self.shield > 0:
            sc.app.audio.play("tin")
            sc.floats.add(self.x, self.y - 16, "TINK!", "sky")
            return False
        if self.iframes > 0:
            return False
        self.iframes = 0.3
        self.hp = max(0, self.hp - dmg)
        self.hits += 1
        self.flash = 0.15
        sc.hype.hitstop(0.05)
        sc.app.audio.play("explode" if dmg >= 3 else "brick")
        sc.parts.burst(x if x is not None else self.x, y if y is not None else self.y, 10,
                       ("white", "yellow", "orange"), 70, 0.4)
        sc.app.shake(2, 0.12)
        if self.hp <= 0:
            self.state = "dead"
            self.dead_t = 0.0
            self.release_ball()
            self.projs = [p for p in self.projs if p[4] == "missile"]
            self.bunnies, self.pickles, self.mists = [], [], []
            sc.boss_defeated()
        elif not self.angry and self.hp <= self.maxhp // 2:
            self.angry = True
            sc.hype.banner(f"{self.name} IS ANGRY!", "WATCH OUT", color="red", dur=1.4, scale=1, sound="warning")
            sc.hype.flash("red", 0.2)
        return True

    def release_ball(self):
        if self.held is not None:
            b = self.held
            b.state = "play"
            b.x, b.y = self.x, self.y + self.r + 4
            b.vx, b.vy = random.uniform(-70, 70), 200.0
            self.held = None

    # ---------------------------------------------------------------- update
    def update(self, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.shield = max(0.0, self.shield - dt)
        self.iframes = max(0.0, self.iframes - dt)
        if self.state == "enter":
            self.y += (self.home_y - self.y) * min(1.0, dt * 3)
            if abs(self.y - self.home_y) < 0.5:
                self.y = self.home_y
                self.state = "idle"
            return
        if self.state == "dead":
            self.dead_t += dt
            self.y += 30 * dt
            self.update_projs(dt)
            return
        self.update_projs(dt)
        self.update_minions(dt)
        if self.held is not None:
            self.held_t -= dt
            self.held.x, self.held.y = self.x, self.y
            if self.held_t <= 0:
                self.release_ball()
        if self.state != "fight":
            return
        spd = self.spd * (1.3 if self.angry else 1.0)
        if self.act:
            self.act_t += dt
            self.do_act(dt, spd)
        else:
            self.move(dt, spd)
            self.cool -= dt * (1.35 if self.angry else 1.0)
            if self.cool <= 0:
                self.start(random.choice(self.moves))

    def move(self, dt, spd):
        k = self.kind
        if k == "buster":
            self.x += self.dir * 34 * spd * dt
            if self.x > X_MAX or self.x < X_MIN:
                self.dir = -self.dir
                self.x = max(X_MIN, min(X_MAX, self.x))
            self.y = self.home_y - abs(math.sin(self.t * 7)) * 2
        elif k == "robovac":
            self.ang += 0.8 * spd * dt
            self.x = 168 + math.cos(self.ang) * 40
            self.y = self.home_y + math.sin(self.ang) * 12
        elif k == "caw":
            self.ang += 1.0 * spd * dt
            self.x = 168 + math.sin(self.ang) * 42
            self.y = self.home_y + math.sin(self.ang * 2) * 10
        elif k == "cuke":
            self.y = self.home_y + math.sin(self.t * 3) * 1.5
        else:
            self.ang += 0.7 * spd * dt
            self.x = 168 + math.sin(self.ang) * 44
            self.y = self.home_y

    def start(self, act):
        sc = self.sc
        self.act, self.act_t, self.phase = act, 0.0, 0
        self.sx, self.sy = self.x, self.y
        self.side = random.randint(0, 1)
        if act == "charge":
            self.dir = 1 if self.x < 168 else -1
        elif act == "dive":
            self.tx, self.ty = random.uniform(120, 200), random.uniform(112, 128)
        elif act == "hop":
            self.tx, self.ty = random.uniform(X_MIN, X_MAX), random.uniform(44, 66)
        elif act == "mist":
            self.tx, self.ty = random.uniform(122, 196), random.uniform(96, 120)
        sc.app.audio.play("warning" if act in ("charge", "dive", "squirt", "suck") else "hold")

    def end_act(self):
        self.act = ""
        self.cool = self.rate * random.uniform(0.8, 1.2)
        self.ang = math.asin(max(-1.0, min(1.0, (self.x - 168) / 44))) if self.kind in ("caw", "spritz") else self.ang

    def paw_target(self):
        f = self.sc.flippers[self.side]
        tx, ty = f.tip()
        return (f.px + tx) / 2, f.py + 2

    def do_act(self, dt, spd):
        sc = self.sc
        a, k = self.act, self.kind
        tell = TELL[a] / min(1.6, spd)
        if self.phase == 0:
            if a in ("charge", "hop"):
                self.x = self.sx + random.uniform(-1, 1)
            if self.act_t >= tell:
                self.phase, self.act_t = 1, 0.0
                self.fire(a)
            return
        if a == "charge":
            self.x += self.dir * 230 * spd * dt
            if self.x > X_MAX + 6 or self.x < X_MIN - 6:
                self.x = max(X_MIN, min(X_MAX, self.x))
                self.dir = -self.dir
                self.end_act()
        elif a == "suck":
            for b in sc.balls:
                if b.state != "play":
                    continue
                dx, dy = self.x - b.x, self.y - b.y
                d = math.hypot(dx, dy)
                if 1 < d < 85:
                    f = 420 * (1 - d / 95) * dt
                    b.vx += dx / d * f
                    b.vy += dy / d * f
            if self.act_t > 2.0:
                self.end_act()
        elif a == "dive":
            if self.act_t < 0.45:
                u = self.act_t / 0.45
                self.x = self.sx + (self.tx - self.sx) * u
                self.y = self.sy + (self.ty - self.sy) * u * u
            elif self.act_t < 1.1:
                u = (self.act_t - 0.45) / 0.65
                self.x = self.tx + (self.sx - self.tx) * u
                self.y = self.ty + (self.sy - self.ty) * (1 - (1 - u) * (1 - u))
            else:
                self.x, self.y = self.sx, self.sy
                if self.held is not None:          # drop the stolen ball at the top
                    self.held_t = 0.0
                    self.release_ball()
                self.end_act()
        elif a == "hop":
            u = min(1.0, self.act_t / 0.55)
            self.x = self.sx + (self.tx - self.sx) * u
            self.y = self.sy + (self.ty - self.sy) * u - math.sin(u * math.pi) * 26
            if u >= 1:
                self.land()
                self.end_act()
        elif a == "squirt":
            self.jet = self.act_t
            fx, fy = self.paw_target()
            for b in sc.balls:              # balls in the jet get pushed along it
                if b.state != "play":
                    continue
                if seg_dist(b.x, b.y, self.x, self.y + 8, fx, fy) < 6:
                    dx, dy = fx - self.x, fy - self.y
                    d = math.hypot(dx, dy) or 1
                    b.vx += dx / d * 700 * dt
                    b.vy += dy / d * 700 * dt
            if self.act_t > 0.7:
                f = sc.flippers[self.side]
                if f.is_up() or f.w < 0:
                    sc.floats.add(fx, fy - 12, "BLOCKED!", "mint")
                    sc.app.audio.play("tin")
                else:
                    sc.stun_paw(self.side, 1.2, "SOAKED!")
                self.jet = 0.0
                self.end_act()
        else:
            self.end_act()

    def fire(self, a):
        sc = self.sc
        if a == "toss":
            fx, fy = self.paw_target()
            tt = 1.05
            vx = (fx - self.x) / tt
            vy = (fy - self.y - 0.5 * 240 * tt * tt) / tt
            self.projs.append([self.x, self.y, vx, vy, TOSSED[self.kind], self.side, False])
            sc.app.audio.play("shoot")
            self.end_act()
        elif a == "bunnies":
            spots = list(sc.tb["spots"])
            random.shuffle(spots)
            for x, y in spots[:2 + min(2, self.round)]:
                self.bunnies.append([float(x), float(y), 9.0])
                sc.parts.burst(x, y, 8, ("gray", "white"), 40, 0.4)
            sc.app.audio.play("pop")
            self.end_act()
        elif a == "shield":
            self.shield = 2.2
            self.end_act()
        elif a == "pickles":
            for i in range(2 + min(1, self.round)):
                self.pickles.append([self.x + (i - 0.5) * 14, self.y + 8, 26.0 + 6 * i, i % 2])
            sc.app.audio.play("pop")
            self.end_act()
        elif a == "mist":
            self.mists.append([self.tx, self.ty, 5.5])
            sc.app.audio.play("bubble")
            self.end_act()
        elif a == "suck":
            sc.app.audio.play("trap")
        elif a == "squirt":
            sc.app.audio.play("bubble")

    def land(self):
        sc = self.sc
        sc.app.shake(3, 0.25)
        sc.app.audio.play("boom")
        sc.parts.burst(self.x, self.y + 10, 16, ("lime", "mint", "white"), 70, 0.5)
        for b in sc.balls:
            if b.state != "play":
                continue
            dx, dy = b.x - self.x, b.y - self.y
            d = math.hypot(dx, dy)
            if d < 60:
                k = 260 * (1 - d / 70)
                b.vx += dx / (d or 1) * k
                b.vy += dy / (d or 1) * k

    def on_ball(self, kind, ref, b):
        """Physics reported a ball touching one of our colliders."""
        sc = self.sc
        if kind == "boss":
            if b.boss_cd <= 0:
                b.boss_cd = 0.25
                if self.hit(sc.ball_dmg(), b.x, b.y):
                    sc.boss_hit_fx(b)
        elif kind in ("grab", "eat") and self.held is None and b.state == "play":
            b.state = "held"
            self.held = b
            self.held_t = 1.0 if kind == "eat" else 99.0
            sc.app.audio.play("trap")
            sc.hype.banner("STOLEN!" if kind == "grab" else "GULP!", color="red", dur=0.9, scale=1)
        elif kind == "bunny" and ref < len(self.bunnies):
            bx, by, _ = self.bunnies.pop(ref)
            sc.score_at(300, bx, by - 6)
            sc.parts.burst(bx, by, 10, ("gray", "white"), 50, 0.4)
            sc.app.audio.play("pop")
            sc.switch_hit()
        elif kind == "pickle" and ref < len(self.pickles):
            px, py, _, _ = self.pickles.pop(ref)
            sc.score_at(400, px, py - 6)
            sc.parts.burst(px, py, 10, ("lime", "mint"), 50, 0.4)
            sc.app.audio.play("pop")
            sc.switch_hit()

    def update_minions(self, dt):
        sc = self.sc
        for b in self.bunnies:
            b[2] -= dt
        self.bunnies = [b for b in self.bunnies if b[2] > 0]
        for m in self.mists:
            m[2] -= dt
            for b in sc.balls:
                if b.state == "play" and (b.x - m[0]) ** 2 + (b.y - m[1]) ** 2 < 26 * 26:
                    b.vx *= 1 - 2.2 * dt
                    b.vy *= 1 - 1.2 * dt
        self.mists = [m for m in self.mists if m[2] > 0]
        keep = []
        for p in self.pickles:
            p[1] += p[2] * dt
            f = sc.flippers[p[3]]
            fx = (f.px + f.tip()[0]) / 2
            p[0] += (fx - p[0]) * min(1.0, dt * 0.6)
            if p[1] > T.FLIP_Y - 8:
                sc.stun_paw(p[3], 1.4, "PICKLED!")
                sc.parts.burst(p[0], p[1], 8, ("lime",), 40, 0.4)
                continue
            keep.append(p)
        self.pickles = keep

    def update_projs(self, dt):
        sc = self.sc
        keep = []
        for p in self.projs:
            x, y, vx, vy, kind, side, back = p
            if kind == "missile":
                dx, dy = self.x - x, self.y - y
                d = math.hypot(dx, dy) or 1
                p[2] += (dx / d * 300 - vx) * min(1.0, dt * 6)
                p[3] += (dy / d * 300 - vy) * min(1.0, dt * 6)
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                sc.parts.sparkle(p[0], p[1], "orange")
                if d < self.r + 3 or self.state == "dead":
                    if self.state == "fight":
                        self.hit(side, p[0], p[1])
                        sc.floats.add(p[0], p[1] - 10, "FISH HIT!", "orange")
                    continue
                keep.append(p)
                continue
            if back:
                p[0] += vx * dt
                p[1] += vy * dt
                if self.state == "fight" and math.hypot(p[0] - self.x, p[1] - self.y) < self.r + 4:
                    if self.hit(2 + sc.lv("power"), p[0], p[1]):
                        sc.hype.banner("COUNTER!", color="mint", dur=0.9, scale=1)
                        sc.score_at(1500, p[0], p[1] - 10)
                    continue
                if p[1] < 4:
                    continue
                keep.append(p)
                continue
            p[3] += 240 * dt
            p[0] += vx * dt
            p[1] += p[3] * dt
            hit_ball = False
            for b in sc.balls:
                if b.state == "play" and (b.x - p[0]) ** 2 + (b.y - p[1]) ** 2 < 36:
                    b.vy += 70
                    hit_ball = True
            if hit_ball:
                sc.parts.burst(p[0], p[1], 6, ("white", "gray"), 40, 0.3)
                continue
            f = sc.flippers[side]
            fx, fy = (f.px + f.tip()[0]) / 2, f.py
            if p[1] >= fy - 9 and abs(p[0] - fx) < 16:
                if f.w < 0 or f.is_up():
                    p[6] = True
                    p[2] = (self.x - p[0]) * 1.25
                    p[3] = -330.0
                    sc.app.audio.play("paddle")
                    sc.floats.add(p[0], p[1] - 10, "BAT!", "mint")
                    keep.append(p)
                else:
                    sc.stun_paw(side, 1.3, "BONK!")
                    sc.parts.burst(p[0], p[1], 8, ("white", "yellow"), 50, 0.3)
                continue
            if p[1] > 206:
                continue
            keep.append(p)
        self.projs = keep

    # ---------------------------------------------------------------- drawing
    def draw(self, s, t):
        for m in self.mists:
            for i in range(7):
                a = t * 0.8 + i * 0.9
                x = int(m[0] + math.cos(a) * 16)
                y = int(m[1] + math.sin(a * 1.3) * 10)
                pygame.draw.circle(s, col("sky" if i % 2 else "white"), (x, y), 5 if m[2] > 1 or int(t * 8) % 2 else 3, 1)
        for x, y, life in self.bunnies:
            if life < 1.5 and int(t * 8) % 2:
                continue
            draw_bunny(s, x, y, t)
        for x, y, _, _ in self.pickles:
            draw_pickle(s, x, y, t)
        if self.state == "fight" and self.act and self.phase == 0:
            self.draw_tell(s, t)
        if self.act == "squirt" and self.phase == 1:
            fx, fy = self.paw_target()
            for i in range(-1, 2):
                pygame.draw.line(s, col("sky" if i else "white"), (int(self.x) + i, int(self.y) + 8), (int(fx) + i, int(fy)))
        if self.act == "suck" and self.phase == 1:
            for i in range(3):
                rr = int(40 - ((t * 60 + i * 13) % 40))
                pygame.draw.circle(s, col("lavender" if i % 2 else "white"), (int(self.x), int(self.y)), max(2, rr), 1)
        dead = self.state == "dead"
        if dead and int(t * 12) % 2:
            pass
        else:
            draw_boss(s, self.kind, self.x, self.y, t, self.flash > 0, self.angry, self.shield > 0,
                      self.act if self.phase == 0 else "", dead)
        for x, y, vx, vy, kind, side, back in self.projs:
            draw_proj(s, kind, x, y, t, back)

    def draw_tell(self, s, t):
        a = self.act
        blink = int(t * 10) % 2
        if a in ("toss", "squirt"):
            fx, fy = self.paw_target()
            if blink:
                draw_text(s, "!", int(fx) - 2, int(fy) - 20, "red", 2, outline="black", shadow=None)
            if a == "squirt":
                for i in range(0, 100, 8):
                    u = i / 100
                    x = self.x + (fx - self.x) * u
                    y = self.y + 8 + (fy - self.y - 8) * u
                    s.fill(col("sky"), (int(x), int(y), 2, 2))
        elif a == "dive":
            for i in range(0, 100, 10):
                u = i / 100
                x = self.x + (self.tx - self.x) * u
                y = self.y + (self.ty - self.y) * u
                s.fill(col("red" if blink else "orange"), (int(x), int(y), 2, 2))
        elif a == "hop":
            pygame.draw.ellipse(s, col("black"), (int(self.tx) - 12, int(self.ty) + 8, 24, 6))
            pygame.draw.ellipse(s, col("red" if blink else "darkgray"), (int(self.tx) - 12, int(self.ty) + 8, 24, 6), 1)
        elif a == "suck":
            rr = int(30 + math.sin(t * 20) * 4)
            pygame.draw.circle(s, col("red" if blink else "lavender"), (int(self.x), int(self.y)), rr, 1)
        elif a == "charge":
            for i in range(3):
                s.fill(col("peach"), (int(self.x) - self.dir * (14 + i * 5), int(self.y) + 10 - i, 2, 2))
        elif a == "mist":
            pygame.draw.circle(s, col("sky"), (int(self.tx), int(self.ty)), 26 if blink else 22, 1)


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy or 1
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return math.hypot(px - (x1 + dx * t), py - (y1 + dy * t))


def draw_bunny(s, x, y, t):
    x, y = int(x), int(y)
    for a in range(0, 360, 60):
        r = math.radians(a + t * 90)
        pygame.draw.circle(s, col("darkgray"), (x + int(math.cos(r) * 3), y + int(math.sin(r) * 3)), 2)
    pygame.draw.circle(s, col("gray"), (x, y), 3)
    s.fill(col("black"), (x - 1, y - 1, 1, 1))
    s.fill(col("black"), (x + 1, y - 1, 1, 1))


def draw_pickle(s, x, y, t):
    x, y = int(x), int(y)
    pygame.draw.ellipse(s, col("black"), (x - 4, y - 6, 9, 13))
    pygame.draw.ellipse(s, col("lime"), (x - 3, y - 5, 7, 11))
    s.fill(col("teal"), (x - 1, y - 3, 1, 1))
    s.fill(col("teal"), (x + 1, y + 2, 1, 1))
    s.fill(col("black"), (x - 2, y - 1, 1, 2))
    s.fill(col("black"), (x + 2, y - 1, 1, 2))


def draw_proj(s, kind, x, y, t, back=False):
    x, y = int(x), int(y)
    if kind == "missile":
        sp_x = x - 5
        pygame.draw.ellipse(s, col("orange"), (sp_x, y - 2, 10, 5))
        s.fill(col("black"), (x + 2, y - 1, 1, 1))
        pygame.draw.polygon(s, col("yellow"), [(x - 5, y), (x - 8, y - 3), (x - 8, y + 3)])
        return
    if kind == "bone":
        a = t * 14
        dx, dy = int(math.cos(a) * 4), int(math.sin(a) * 4)
        pygame.draw.line(s, col("cream"), (x - dx, y - dy), (x + dx, y + dy), 2)
        for sx, sy in ((x - dx, y - dy), (x + dx, y + dy)):
            pygame.draw.circle(s, col("white"), (sx, sy), 2)
    elif kind == "pebble":
        pygame.draw.circle(s, col("black"), (x, y), 3)
        pygame.draw.circle(s, col("gray"), (x, y), 2)
        s.fill(col("white"), (x - 1, y - 1, 1, 1))
    else:
        pygame.draw.polygon(s, col("sky"), [(x, y - 4), (x + 3, y + 1), (x - 3, y + 1)])
        pygame.draw.circle(s, col("sky"), (x, y + 1), 3)
        s.fill(col("white"), (x - 1, y, 1, 1))
    if back and int(t * 10) % 2:
        pygame.draw.circle(s, col("mint"), (x, y), 6, 1)


def draw_boss(s, kind, x, y, t, flash, angry, shield, tell, dead):
    x, y = int(x), int(y)
    k = col("black")
    hot = flash
    if kind == "buster":           # scruffy bully dog with a spiked collar
        body = col("white" if hot else ("red" if angry and int(t * 6) % 2 else "brown"))
        pygame.draw.ellipse(s, k, (x - 15, y - 11, 30, 25))
        pygame.draw.ellipse(s, body, (x - 14, y - 10, 28, 23))
        for side in (-1, 1):          # floppy ears
            pygame.draw.ellipse(s, k, (x + side * 13 - 5, y - 10, 10, 14))
            pygame.draw.ellipse(s, col("choco"), (x + side * 13 - 4, y - 9, 8, 12))
        pygame.draw.ellipse(s, col("cream"), (x - 9, y - 1, 18, 11))      # muzzle
        pygame.draw.ellipse(s, k, (x - 3, y - 1, 6, 4))                  # nose
        cute.eyes(s, x, y - 5, 5, 0, "angry")
        s.fill(k, (x - 5, y + 6, 11, 1))
        s.fill(col("white"), (x - 4, y + 4, 2, 2))                       # underbite teeth
        s.fill(col("white"), (x + 3, y + 4, 2, 2))
        s.fill(col("red"), (x - 11, y + 11, 22, 3))                      # collar
        for i in range(-9, 10, 6):
            s.fill(col("gray"), (x + i, y + 10, 2, 2))
        if tell == "toss":
            pygame.draw.line(s, col("cream"), (x + 12, y - 16), (x + 20, y - 22), 2)
            pygame.draw.circle(s, col("white"), (x + 12, y - 16), 2)
            pygame.draw.circle(s, col("white"), (x + 20, y - 22), 2)
    elif kind == "robovac":        # round robot vacuum with a red visor
        body = col("white" if hot else ("red" if angry and int(t * 6) % 2 else "gray"))
        pygame.draw.ellipse(s, k, (x - 15, y - 9, 30, 20))
        pygame.draw.ellipse(s, body, (x - 14, y - 8, 28, 17))
        pygame.draw.ellipse(s, col("white"), (x - 10, y - 7, 20, 8))
        s.fill(col("darkgray"), (x - 9, y - 4, 18, 4))
        sweep = int((t * 30) % 14)
        s.fill(col("red"), (x - 8 + sweep, y - 4, 3, 3))                 # scanner eye
        for side in (-1, 1):                                             # spinning brushes
            a = t * 20 * side
            for i in range(3):
                bx = x + side * 12 + int(math.cos(a + i * 2.1) * 4)
                by = y + 9 + int(math.sin(a + i * 2.1) * 2)
                s.fill(col("yellow"), (bx, by, 1, 1))
        if angry:
            s.fill(col("red"), (x - 2, y + 3, 4, 2))
    elif kind == "caw":            # glossy crow
        flap = math.sin(t * 14) * 5 if not shield else 0
        body = col("white" if hot else "black")
        if shield:
            pygame.draw.ellipse(s, col("purple"), (x - 13, y - 13, 26, 26))
            pygame.draw.ellipse(s, col("deep"), (x - 11, y - 11, 22, 22))
            s.fill(col("lavender"), (x - 6, y - 8, 4, 1))
        else:
            for side in (-1, 1):
                pygame.draw.polygon(s, col("deep"), [(x + side * 4, y - 2), (x + side * 18, y - 6 - int(flap)),
                                                     (x + side * 14, y + 4)])
            pygame.draw.ellipse(s, body, (x - 8, y - 9, 16, 19))
            pygame.draw.circle(s, body, (x, y - 8), 6)
            pygame.draw.polygon(s, col("yellow"), [(x - 2, y - 6), (x + 2, y - 6), (x, y - 1)])
            for side in (-1, 1):
                s.fill(col("white"), (x + side * 3 - (1 if side < 0 else 0), y - 10, 2, 2))
                s.fill(col("red" if angry else "black"), (x + side * 3 - (1 if side < 0 else 0) + (1 if side < 0 else 0), y - 9, 1, 1))
            s.fill(col("purple"), (x - 3, y + 2, 6, 1))
        if tell == "dive":
            draw_text(s, "!", x + 10, y - 20, "red", outline="black", shadow=None)
    elif kind == "cuke":           # spooky cucumber (cats hate those)
        body = col("white" if hot else ("red" if angry and int(t * 6) % 2 else "lime"))
        squash = 2 if tell == "hop" else 0
        pygame.draw.ellipse(s, k, (x - 9 - squash, y - 15 + squash, 18 + 2 * squash, 31 - squash))
        pygame.draw.ellipse(s, body, (x - 8 - squash, y - 14 + squash, 16 + 2 * squash, 29 - squash))
        for dx, dy in ((-4, -8), (3, -4), (-3, 4), (4, 8), (0, -11), (-5, 10)):
            s.fill(col("teal"), (x + dx, y + dy, 2, 1))
        s.fill(col("mint"), (x - 5, y - 10, 1, 8))
        pygame.draw.polygon(s, col("teal"), [(x, y - 15), (x + 6, y - 20), (x + 2, y - 13)])
        cute.eyes(s, x, y - 3, 3, 0, "angry")
        cute.mouth(s, x, y + 3, "angry")
        if tell == "hop":
            for side in (-1, 1):
                s.fill(k, (x + side * 5, y + 15, 2, 3))
    else:                          # spray bottle
        body = col("white" if hot else ("red" if angry and int(t * 6) % 2 else "sky"))
        pygame.draw.rect(s, k, (x - 9, y - 6, 18, 22), border_radius=3)
        pygame.draw.rect(s, body, (x - 8, y - 5, 16, 20), border_radius=3)
        lvl = int(6 + math.sin(t * 2) * 1)
        s.fill(col("blue"), (x - 7, y + 14 - lvl, 14, lvl))
        s.fill(col("white"), (x - 6, y - 3, 2, 10))
        pygame.draw.rect(s, k, (x - 6, y - 15, 12, 10), border_radius=2)  # trigger head
        pygame.draw.rect(s, col("red"), (x - 5, y - 14, 10, 8), border_radius=2)
        s.fill(col("red"), (x - 4, y - 7, 3, 5))                           # trigger
        s.fill(col("white"), (x + 5, y - 12, 4, 2))                        # nozzle
        cute.eyes(s, x, y + 3, 3, 0, "angry")
        cute.mouth(s, x, y + 8, "angry")
    if dead:
        for i in range(4):
            a = t * 9 + i * 1.6
            s.fill(col("yellow"), (x + int(math.cos(a) * 16), y - 14 + int(math.sin(a) * 4), 2, 2))
