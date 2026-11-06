"""CLOUD POUNCE sky bosses (every 10th stage): HOOTSTORM the storm owl, BILLOWHALE the cloud whale, RIBBON DRAKE
the paper dragon kite, the BLINKER SAUCER full of laser-pointer aliens and NOCTURNE, the guardian of the moon gate.

SORA hurts a boss by landing on its head (a pounce hits harder). Every attack is telegraphed first; at half health
a boss gets angry (faster, more often) and later bosses borrow attacks from the others.
Coordinates: x on the 224 px wrapping field, h = altitude (screen y = 200 - h, the arena camera never moves).
Mirrored by ios/MochiArcade/Games/CloudPounceBoss.swift.
"""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.arcade import rainbow
from mochi_arcade.gfx import col, sprite

FW = 224
BASE_H = {"owl": 150, "whale": 152, "kite": 148, "ufo": 160, "eclipse": 146}
SIZE = {"owl": (14, 14), "whale": (26, 10), "kite": (9, 9), "ufo": (22, 8), "eclipse": (15, 15)}  # half w, half h
ATTACKS = {
    "owl": ["feathers", "bolt", "gust"],
    "whale": ["spout", "geyser", "dive"],
    "kite": ["lanterns", "swoop", "ring"],
    "ufo": ["dots", "beam", "drones"],
    "eclipse": ["crescents", "starfall", "eclipse"],
}
TELE = {"feathers": 0.7, "bolt": 0.9, "gust": 0.8, "spout": 0.6, "geyser": 1.0, "dive": 1.0, "lanterns": 0.6,
        "swoop": 0.9, "ring": 0.7, "dots": 0.5, "beam": 0.8, "drones": 0.5, "crescents": 0.6, "starfall": 0.9,
        "eclipse": 0.6}


def wrapd(dx):
    return (dx + FW / 2) % FW - FW / 2


class Proj:
    def __init__(self, kind, x, h, vx, vh, life=6.0, grav=0.0, r=3):
        self.kind, self.x, self.h, self.vx, self.vh = kind, x, h, vx, vh
        self.life, self.grav, self.r = life, grav, r
        self.age = 0.0
        self.alive = True
        self.ox = self.oh = 0.0          # crescents: where they were thrown from


class Boss:
    def __init__(self, game, spec):
        self.g = game
        self.kind = spec["kind"]
        self.name = spec["name"]
        self.tier = spec["tier"]
        self.maxhp = self.hp = spec["hp"]
        self.rate = spec["rate"]
        self.spd = spec["speed"] * (0.85 + 0.15 * game.fspeed)
        self.attacks = ATTACKS[self.kind] + list(spec["extra"])
        self.state = "enter"
        self.x = FW / 2
        self.h = 270.0
        self.base_h = BASE_H[self.kind]
        self.t = 0.0
        self.atk_t = 2.2
        self.atk_i = 0
        self.flash = 0.0
        self.inv = 0.0
        self.phase = 1
        self.die_t = 0.0
        self.tele = None             # [attack, time left, full, x, h]
        self.projs = []
        self.cols = []               # active columns [kind, x, half width, h low, h high, time left]
        self.push = 0.0
        self.push_t = 0.0
        self.dark = 0.0
        self.dark_t = 0.0
        self.dotl = []               # laser dots [x, h, life, phase]
        self.drones = []             # stompable mini saucers [x, h, vx, life]
        self.dir = 1                 # whale heading
        self.mode = ""               # dive / swoop in progress
        self.mode_t = 0.0
        self.mx = self.mh = 0.0      # dive / swoop target
        self.tx = self.th = 0.0      # where the last telegraphed attack aims
        self.trail = []              # kite tail history [(x, h)]
        self.trail_t = 0.0
        self.angry_t = 0.0
        self.boom_t = 0.0
        self.knock_t = 0.0           # reeling away after a stomp
        self.knock_dx = 1

    # ------------------------------------------------------------------ queries for the game
    def stomp_zone(self):
        """(x, altitude of the head top, half width) or None."""
        if self.state != "fight" or self.mode == "dive":
            return None
        hw, hh = SIZE[self.kind]
        return self.x, self.h + hh, hw

    def blocked(self, x):
        """NOCTURNE's star shields block a stomp while one sits on top of its head."""
        if self.kind != "eclipse":
            return False
        for a in self.shield_angles():
            if math.sin(a) > 0.82:
                return True
        return False

    def shield_angles(self):
        n = 3 + (1 if self.tier >= 10 else 0)
        sp = 1.5 * self.spd * (2.0 if self.dark > 0.5 else 1.0)
        return [self.t * sp + i * math.tau / n for i in range(n)]

    def body_box(self):
        hw, hh = SIZE[self.kind]
        return self.x, self.h, hw, hh

    def bump(self, cx, cy, rx, ry):
        """SORA touches the resting boss body: a harmless bonk (only its charges hurt)."""
        if self.state != "fight" or self.mode:
            return False
        bx, bh, hw, hh = self.body_box()
        return abs(wrapd(cx - bx)) < hw + rx - 2 and abs(cy - bh) < hh + ry - 2

    def touch(self, cx, cy, rx, ry):
        """Does SORA's box (centre cx, cy, half sizes rx, ry) touch anything harmful?"""
        if self.state != "fight":
            return False
        bx, bh, hw, hh = self.body_box()
        if self.mode and abs(wrapd(cx - bx)) < hw + rx - 3 and abs(cy - bh) < hh + ry - 3:
            return True                  # the dive / swoop charge itself hurts
        if self.kind == "kite":
            for i, (sx, sh) in enumerate(self.segments()):
                if abs(wrapd(cx - sx)) < rx + 2 and abs(cy - sh) < ry + 2:
                    return True
        if self.kind == "eclipse":
            for a in self.shield_angles():
                sx, sh = self.x + math.cos(a) * 24, self.h + math.sin(a) * 24
                if abs(wrapd(cx - sx)) < rx + 2 and abs(cy - sh) < ry + 2 and math.sin(a) < 0.82:
                    return True
        for p in self.projs:
            if abs(wrapd(cx - p.x)) < rx + p.r - 1 and abs(cy - p.h) < ry + p.r - 1:
                p.alive = False
                return True
        for c in self.cols:
            if abs(wrapd(cx - c[1])) < c[2] + rx - 2 and c[3] < cy < c[4]:
                return True
        for d in self.drones:
            if abs(wrapd(cx - d[0])) < rx + 5 and abs(cy - d[1]) < ry + 3:
                return True
        return False

    def stomp_minions(self, x, h, vh):
        """Drones squashed by SORA's feet (falling onto them). Returns how many."""
        n = 0
        if vh >= 0:
            return 0
        for d in self.drones:
            if d[3] > 0 and abs(wrapd(x - d[0])) < 9 and d[1] - 2 <= h <= d[1] + 7:
                d[3] = 0.0
                n += 1
                self.g.parts.burst(d[0], self.g.sy(d[1]), 10, ("lime", "white", "gray"), 60, 0.4)
        self.drones = [d for d in self.drones if d[3] > 0]
        return n

    def dots(self):
        return [(d[0], d[1]) for d in self.dotl]

    def segments(self):
        """RIBBON DRAKE's tail: points along its recent path."""
        out = []
        for i in range(1, 6):
            k = i * 3
            if k < len(self.trail):
                out.append(self.trail[k])
        return out

    def hit(self, dmg):
        if self.state != "fight":
            return False
        g = self.g
        self.flash = 0.25
        if self.inv > 0:
            return False
        self.inv = 1.3
        self.knock_t = 0.8
        self.knock_dx = 1 if wrapd(self.x - g.x) >= 0 else -1
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.state = "dead"
            self.die_t = 0.0
            self.projs, self.cols, self.dotl, self.drones = [], [], [], []
            self.tele = None
            self.push = 0.0
            self.dark = 0.0
            return True
        if self.phase == 1 and self.hp <= self.maxhp // 2:
            self.phase = 2
            self.spd *= 1.2
            self.rate *= 0.8
            self.angry_t = 1.2
            g.hype.banner(f"{self.name} IS ANGRY!", color="red", dur=1.2, scale=1, sound="warning")
            for a in ATTACKS[self.kind]:
                if a not in self.attacks:
                    self.attacks.append(a)
        return True

    # ------------------------------------------------------------------ update
    def update(self, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.inv = max(0.0, self.inv - dt)
        self.angry_t = max(0.0, self.angry_t - dt)
        if self.state == "dead":
            self.die_t += dt
            self.boom_t -= dt
            if self.boom_t <= 0:
                self.boom_t = 0.12
                g = self.g
                g.parts.burst(self.x + random.uniform(-16, 16), g.sy(self.h + random.uniform(-10, 10)), 10,
                              ("white", "yellow", "orange", "hotpink"), 80, 0.5)
                g.app.audio.play("explode")
            if self.die_t > 0.9:
                self.h -= 90 * dt
            return
        self.move(dt)
        if self.state == "enter":
            self.h = max(self.base_h, self.h - 90 * dt)
            return
        self.update_attacks(dt)
        self.update_shots(dt)

    def move(self, dt):
        k = self.kind
        t = self.t
        sp = self.spd
        g = self.g
        if self.knock_t > 0:          # reel away from SORA, then carry on
            self.knock_t -= dt
            self.x = (self.x + self.knock_dx * 130 * dt) % FW
            self.h = min(self.base_h + 24, self.h + 40 * dt)
            if k == "kite":
                self.record_trail(dt)
            return
        if self.mode == "dive":
            self.mode_t += dt
            if self.mode_t < 1.4:
                self.h -= 230 * dt
                self.x = self.mx
            else:
                self.mode = ""
                self.h = 260.0
                self.state = "fight"
            return
        if self.mode == "swoop":
            self.mode_t += dt
            self.x = (self.mx + self.dir * 250 * sp * self.mode_t) % FW
            self.h += (self.mh - self.h) * min(1.0, dt * 6)
            self.record_trail(dt)
            if self.mode_t > 1.1:
                self.mode = ""
            return
        if k == "owl":
            tx = FW / 2 + math.sin(t * 0.7 * sp) * 70
            th = self.base_h + math.sin(t * 1.6) * 8
        elif k == "whale":
            self.x = (self.x + self.dir * 38 * sp * dt) % FW
            tx = self.x
            th = self.base_h + math.sin(t * 1.2) * 6
        elif k == "kite":
            tx = FW / 2 + math.sin(t * 0.9 * sp) * 80
            th = self.base_h + math.sin(t * 1.8 * sp) * 16
        elif k == "ufo":
            dx = wrapd(g.x - self.x)
            if not (self.tele and self.tele[0] == "beam") and not any(c[0] == "beam" for c in self.cols):
                self.x = (self.x + max(-1.0, min(1.0, dx / 30)) * 34 * sp * dt) % FW
            tx = self.x
            th = self.base_h + math.sin(t * 2) * 5
        else:
            tx = FW / 2 + math.cos(t * 0.5 * sp) * 52
            th = self.base_h + math.sin(t * 0.5 * sp) * 12
        if k in ("owl", "kite", "eclipse"):
            self.x += wrapd(tx - self.x) * min(1.0, dt * 3)
            self.x %= FW
        if self.state == "fight" or self.h <= self.base_h + 1:
            self.h += (th - self.h) * min(1.0, dt * 3)
        if k == "kite":
            self.record_trail(dt)

    def record_trail(self, dt):
        self.trail_t -= dt
        if self.trail_t <= 0:
            self.trail_t = 0.03
            self.trail.insert(0, (self.x, self.h))
            del self.trail[40:]

    def update_attacks(self, dt):
        g = self.g
        if self.tele:
            self.tele[1] -= dt
            if self.tele[0] in ("bolt", "dive") and self.tele[1] > 0.35:
                self.tele[3] = g.x               # keeps aiming until just before it strikes
            if self.tele[1] <= 0:
                a = self.tele[0]
                self.tx, self.th = self.tele[3], self.tele[4]
                self.tele = None
                self.fire(a)
            return
        if self.mode:
            return
        self.atk_t -= dt
        if self.atk_t <= 0:
            self.atk_t = self.rate * random.uniform(0.85, 1.15)
            a = self.attacks[self.atk_i % len(self.attacks)]
            self.atk_i += 1
            if random.random() < 0.3:
                a = random.choice(self.attacks)
            if a == "eclipse" and self.dark_t > 0:
                a = "starfall"
            tx, th = g.x, g.h + 7
            if a == "geyser":
                alive = [c for c in g.clouds if c.alive]
                if alive:
                    c = min(alive, key=lambda c: abs(wrapd(c.cx() - g.x)) + abs(c.h - g.h) * 0.5)
                    tx, th = c.cx(), c.h
            if a == "swoop":
                th = max(40.0, min(170.0, g.h + 10))
            self.tele = [a, TELE[a], TELE[a], tx, th]
            g.app.audio.play("warning" if a in ("dive", "swoop", "eclipse") else "select")

    def fire(self, a):
        g = self.g
        sp = self.spd
        au = g.app.audio
        px, ph = g.x, g.h + 7
        bx, bh = self.x, self.h
        if a == "feathers":
            n = min(7, 3 + self.tier // 4 + (1 if self.phase == 2 else 0))
            base = math.atan2(ph - bh, wrapd(px - bx))
            for i in range(n):
                ang = base + (i - (n - 1) / 2) * 0.28
                self.projs.append(Proj("feather", bx, bh, math.cos(ang) * 75 * sp, math.sin(ang) * 75 * sp, 5.0))
            au.play("shoot")
        elif a == "bolt":
            xs = [self.tx]
            if self.phase == 2:
                xs += [(self.tx + 60) % FW, (self.tx - 60) % FW]
            for x in xs:
                self.cols.append(["bolt", x, 6, -20, 240, 0.35])
            au.play("explode")
            g.app.shake(2, 0.15)
        elif a == "gust":
            self.push = (1 if random.random() < 0.5 else -1) * 170 * sp
            self.push_t = 2.0
            au.play("bubble")
        elif a == "spout":
            for i in range(5 + (1 if self.phase == 2 else 0)):
                self.projs.append(Proj("drop", bx, bh + 8, random.uniform(-70, 70), random.uniform(150, 210),
                                       5.0, grav=230, r=3))
            au.play("bubble")
        elif a == "geyser":
            self.cols.append(["geyser", self.tx, 7, self.th, 240, 0.8])
            au.play("bubble")
        elif a == "dive":
            self.mode = "dive"
            self.mode_t = 0.0
            self.mx = self.tx
            self.h = 240.0
            au.play("boom")
        elif a == "lanterns":
            for i in range(3 + (1 if self.phase == 2 else 0)):
                p = Proj("lantern", bx + (i - 1) * 14, bh - 6, (i - 1) * 12, -30 - i * 4, 7.0, r=4)
                self.projs.append(p)
            au.play("shoot")
        elif a == "swoop":
            self.mode = "swoop"
            self.mode_t = 0.0
            self.dir = 1 if wrapd(px - bx) > 0 else -1
            self.mx = bx
            self.mh = self.th
            au.play("boom")
        elif a == "ring":
            n = 8 + (4 if self.phase == 2 else 0)
            for i in range(n):
                ang = math.tau * i / n + self.t
                self.projs.append(Proj("confetti", bx, bh, math.cos(ang) * 70 * sp, math.sin(ang) * 70 * sp, 4.0))
            au.play("pop")
        elif a == "dots":
            for i in range(2 + (1 if self.phase == 2 else 0)):
                self.dotl.append([random.uniform(10, FW - 10), random.uniform(30, 130), 4.5, random.uniform(0, 6)])
            au.play("type")
        elif a == "beam":
            self.cols.append(["beam", bx, 6, -20, bh - 6, 0.7])
            au.play("shoot")
        elif a == "drones":
            for i in range(2):
                self.drones.append([bx + (i * 2 - 1) * 14, bh - 8, (i * 2 - 1) * 20.0, 9.0])
            au.play("powerup")
        elif a == "crescents":
            for side in (-1, 1):
                p = Proj("crescent", bx, bh, side, 0, 2.4, r=4)
                p.ox, p.oh = bx, bh
                p.vh = math.atan2(ph - bh, wrapd(px - bx) + side * 40)
                self.projs.append(p)
            au.play("shoot")
        elif a == "starfall":
            n = 4 + (1 if self.phase == 2 else 0)
            for i in range(n):
                x = (self.tx + (i - n // 2) * 40) % FW
                self.projs.append(Proj("star", x, 210 + i * 12, 0, -150 * sp, 3.0, r=4))
            au.play("coin")
        elif a == "eclipse":
            self.dark_t = 3.5
            au.play("boom")

    def update_shots(self, dt):
        g = self.g
        for p in self.projs:
            p.age += dt
            if p.kind == "crescent":       # out and back like a boomerang
                u = p.age / p.life
                reach = 100 * math.sin(u * math.pi)
                p.x = (p.ox + math.cos(p.vh) * reach + p.vx * math.sin(u * math.pi * 2) * 20) % FW
                p.h = p.oh + math.sin(p.vh) * reach
            else:
                p.vh -= p.grav * dt
                if p.kind == "lantern":
                    p.vx = math.sin(p.age * 3 + p.ox) * 18
                p.x = (p.x + p.vx * dt) % FW
                p.h += p.vh * dt
            if p.age > p.life or p.h < -20 or p.h > 260:
                p.alive = False
        self.projs = [p for p in self.projs if p.alive]
        for c in self.cols:
            c[5] -= dt
        self.cols = [c for c in self.cols if c[5] > 0]
        if self.push_t > 0:
            self.push_t -= dt
            if self.push_t <= 0:
                self.push = 0.0
        if self.dark_t > 0:
            self.dark_t -= dt
            self.dark = min(1.0, self.dark + dt * 2)
        else:
            self.dark = max(0.0, self.dark - dt * 2)
        for d in self.dotl:
            d[2] -= dt
            d[3] += dt
            dx = wrapd(g.x - d[0])
            d[0] = (d[0] + (max(-1.0, min(1.0, dx / 40)) * 36 + math.sin(d[3] * 3) * 50) * dt) % FW
            d[1] += ((g.h + 7 - d[1]) * 0.6 + math.cos(d[3] * 2.3) * 40) * dt
        self.dotl = [d for d in self.dotl if d[2] > 0]
        for d in self.drones:
            d[3] -= dt
            dx = wrapd(g.x - d[0])
            d[2] += max(-1.0, min(1.0, dx / 30)) * 40 * dt
            d[2] = max(-30.0, min(30.0, d[2]))
            d[0] = (d[0] + d[2] * dt) % FW
            d[1] = max(30.0, d[1] - 22 * dt)
        self.drones = [d for d in self.drones if d[3] > 0]

    # ------------------------------------------------------------------ drawing
    def draw(self, s, t):
        g = self.g
        if self.tele:
            self.draw_tele(s, t)
        for c in self.cols:
            self.draw_col(s, c, t)
        if not (self.state == "dead" and self.die_t > 1.4 and int(t * 20) % 2):
            for xd in (0, -FW, FW):
                x = int(self.x) + xd
                if -40 < x < FW + 40:
                    self.draw_body(s, x, int(g.sy(self.h)), t)
        for p in self.projs:
            draw_proj(s, p, int(p.x), int(g.sy(p.h)), t)
        for d in self.dotl:
            x, y = int(d[0]), int(g.sy(d[1]))
            r = 3 + int(t * 10) % 2
            pygame.draw.circle(s, col("hotpink"), (x, y), r + 2, 1)
            pygame.draw.circle(s, col("red"), (x, y), r)
            s.fill(col("white"), (x - 1, y - 1, 1, 1))
        for d in self.drones:
            x, y = int(d[0]), int(g.sy(d[1]))
            if d[3] < 1.5 and int(t * 10) % 2:
                continue
            pygame.draw.ellipse(s, col("black"), (x - 7, y - 2, 15, 6))
            pygame.draw.ellipse(s, col("gray"), (x - 6, y - 1, 13, 4))
            pygame.draw.circle(s, col("lime"), (x, y - 2), 3)
            s.fill(col("black"), (x - 1, y - 3, 1, 1))
            s.fill(col("black"), (x + 1, y - 3, 1, 1))
            s.fill(col(rainbow(int(t * 8), 0)), (x - 5, y + 1, 1, 1))
            s.fill(col(rainbow(int(t * 8) + 3, 0)), (x + 5, y + 1, 1, 1))

    def draw_tele(self, s, t):
        g = self.g
        a, left, full, x, h = self.tele
        blink = int(t * 12) % 2
        x = int(x)
        if a in ("bolt", "beam"):
            if blink:
                y1 = 200 if a == "bolt" else int(g.sy(self.h)) + 6
                for y in range(0, y1, 6):
                    s.fill(col("yellow" if a == "bolt" else "red"), (x, y, 1, 3))
        elif a == "geyser":
            y = int(g.sy(h))
            for i in range(4):
                by = y - 2 - int((t * 40 + i * 9) % 30)
                pygame.draw.circle(s, col("sky"), (x - 6 + i * 4, by), 2, 1)
        elif a == "dive":
            if blink:
                for i in range(3):
                    pygame.draw.polygon(s, col("red"), [(x - 6, 8 + i * 8), (x + 6, 8 + i * 8), (x, 14 + i * 8)])
        elif a == "swoop":
            if blink:
                y = int(g.sy(h))
                for xx in range(0, FW, 8):
                    s.fill(col("red"), (xx, y, 4, 1))
        elif a == "starfall":
            n = 4 + (1 if self.phase == 2 else 0)
            for i in range(n):
                xx = int((x + (i - n // 2) * 40) % FW)
                if blink:
                    s.blit(sprite("star"), (xx - 3, 2))
        elif a == "gust":
            for i in range(4):
                yy = 40 + i * 36
                s.fill(col("white" if blink else "sky"), (int((t * 120 + i * 50) % FW), yy, 10, 1))
        else:
            # the boss winds up: glowing sparkle at its body
            r = 4 + int((1 - left / full) * 8)
            bx, by = int(self.x), int(g.sy(self.h))
            pygame.draw.circle(s, col("yellow" if blink else "white"), (bx, by), r + 14, 1)

    def draw_col(self, s, c, t):
        g = self.g
        kind, x, hw, lo, hi, left = c
        x = int(x)
        y0 = max(0, int(g.sy(hi)))
        y1 = min(200, int(g.sy(lo)))
        if kind == "bolt":
            xx = x
            for y in range(y0, y1, 10):
                nx = x + (3 if (y // 10 + int(t * 30)) % 2 else -3)
                pygame.draw.line(s, col("yellow"), (xx, y), (nx, y + 10), 3)
                pygame.draw.line(s, col("white"), (xx, y), (nx, y + 10), 1)
                xx = nx
        elif kind == "geyser":
            for y in range(y0, y1, 2):
                w = hw + int(math.sin(t * 20 + y * 0.3) * 2)
                s.fill(col("sky"), (x - w, y, w * 2, 2))
                s.fill(col("white"), (x - 2 + int(math.sin(y * 0.5 + t * 9) * 2), y, 2, 1))
        else:
            w = hw - (int(t * 30) % 2)
            s.fill(col("hotpink"), (x - w, y0, w * 2, y1 - y0))
            s.fill(col("white"), (x - 1, y0, 2, y1 - y0))

    def draw_body(self, s, x, y, t):
        k = self.kind
        hit = self.flash > 0 and int(t * 30) % 2
        angry = self.phase == 2
        g = self.g
        look = 1 if wrapd(g.x - self.x) > 0 else -1
        if k == "owl":
            # storm cloud perch
            for i in range(4):
                pygame.draw.circle(s, col("darkgray"), (x - 15 + i * 10, y + 13), 6)
            body = "white" if hit else ("purple" if angry else "lavender")
            flap = int(math.sin(t * 8) * 3)
            for side in (-1, 1):
                pygame.draw.ellipse(s, col("black"), (x + side * 13 - 6, y - 6 + flap * side, 12, 16))
                pygame.draw.ellipse(s, col("gray"), (x + side * 13 - 5, y - 5 + flap * side, 10, 14))
            pygame.draw.circle(s, col("black"), (x, y), 16)
            pygame.draw.circle(s, col(body), (x, y), 15)
            pygame.draw.polygon(s, col(body), [(x - 13, y - 8), (x - 9, y - 20), (x - 4, y - 12)])
            pygame.draw.polygon(s, col(body), [(x + 13, y - 8), (x + 9, y - 20), (x + 4, y - 12)])
            pygame.draw.ellipse(s, col("cream"), (x - 9, y + 1, 18, 12))
            for i in range(3):
                s.fill(col("peach"), (x - 5 + i * 4, y + 5 + (i % 2) * 2, 2, 1))
            for side in (-1, 1):
                pygame.draw.circle(s, col("white"), (x + side * 6, y - 5), 5)
                pygame.draw.circle(s, col("black"), (x + side * 6 + look * 2, y - 5), 2)
                if angry:
                    pygame.draw.line(s, col("black"), (x + side * 2, y - 10), (x + side * 10, y - 12))
            pygame.draw.polygon(s, col("orange"), [(x - 2, y - 2), (x + 2, y - 2), (x, y + 2)])
            if angry and int(t * 8) % 2:
                pygame.draw.lines(s, col("yellow"), False, [(x + 18, y - 14), (x + 21, y - 9), (x + 18, y - 7), (x + 22, y - 2)])
        elif k == "whale":
            d = self.dir
            body = "white" if hit else ("pink" if angry else "white")
            for i in range(5):
                pygame.draw.circle(s, col("sky"), (x - 20 + i * 10, y - 7), 6)
            pygame.draw.ellipse(s, col("sky"), (x - 29, y - 11, 58, 24))
            pygame.draw.ellipse(s, col(body), (x - 27, y - 9, 54, 20))
            for i in range(5):
                pygame.draw.circle(s, col(body), (x - 20 + i * 10, y - 7), 5)
            pygame.draw.ellipse(s, col("cream"), (x - 18, y + 2, 36, 7))
            tx = x - d * 30
            flip = int(math.sin(t * 5) * 3)
            pygame.draw.polygon(s, col("sky"), [(tx, y), (tx - d * 10, y - 8 + flip), (tx - d * 10, y + 6 + flip)])
            ex = x + d * 15
            s.fill(col("black"), (ex, y - 3, 2, 3 if not angry else 2))
            s.fill(col("pink"), (ex - d * 2, y + 2, 3, 1))
            pygame.draw.line(s, col("black"), (x + d * 18, y + 4), (x + d * 23, y + 3))
            s.fill(col("sky"), (x + d * 4, y - 14, 3, 2))
        elif k == "kite":
            segs = self.segments()
            for i in range(len(segs) - 1, -1, -1):
                sx, sh = segs[i]
                sy = int(g.sy(sh))
                for xd in (0, -FW, FW):
                    xx = int(sx) + xd
                    r = 5 - i // 2
                    c = rainbow(i, 0)
                    pygame.draw.polygon(s, col("black"), [(xx, sy - r - 1), (xx + r + 1, sy), (xx, sy + r + 1), (xx - r - 1, sy)])
                    pygame.draw.polygon(s, col(c), [(xx, sy - r), (xx + r, sy), (xx, sy + r), (xx - r, sy)])
            body = "white" if hit else ("hotpink" if angry else "red")
            pygame.draw.polygon(s, col("black"), [(x, y - 12), (x + 12, y), (x, y + 12), (x - 12, y)])
            pygame.draw.polygon(s, col(body), [(x, y - 11), (x + 11, y), (x, y + 11), (x - 11, y)])
            pygame.draw.polygon(s, col("yellow"), [(x, y - 11), (x + 11, y), (x, y)])
            for side in (-1, 1):
                pygame.draw.line(s, col("yellow"), (x + side * 4, y - 9), (x + side * 8, y - 15))
                pygame.draw.line(s, col("white"), (x + side * 6, y + 3), (x + side * 16, y + 6 + int(math.sin(t * 6) * 2)))
            cute.eyes(s, x, y - 2, 4, look, "angry" if angry else "happy")
            cute.mouth(s, x, y + 3, "angry" if angry else "happy")
        elif k == "ufo":
            dome = "white" if hit else "sky"
            pygame.draw.circle(s, col("black"), (x, y - 3), 11)
            pygame.draw.circle(s, col(dome), (x, y - 3), 10)
            for i in range(3):       # the laser-pointer aliens inside
                ax = x - 6 + i * 6
                ay = y - 4 + (1 if (i + int(t * 4)) % 2 else 0)
                pygame.draw.circle(s, col("lime"), (ax, ay), 2)
                s.fill(col("black"), (ax, ay - 1, 1, 1))
                s.fill(col("lime"), (ax, ay - 4, 1, 2))
                s.fill(col("red"), (ax + 1, ay + 1, 2, 1))
            s.fill(col("white"), (x - 6, y - 10, 3, 2))
            pygame.draw.ellipse(s, col("black"), (x - 24, y - 2, 48, 13))
            pygame.draw.ellipse(s, col("purple" if angry else "gray"), (x - 23, y - 1, 46, 11))
            pygame.draw.ellipse(s, col("lavender"), (x - 20, y - 1, 40, 4))
            for i in range(6):
                c = rainbow(i + int(t * 10), 0)
                s.fill(col(c), (x - 17 + i * 7, y + 5, 2, 2))
        else:
            for a in self.shield_angles():
                sx = x + int(math.cos(a) * 24)
                sy = y - int(math.sin(a) * 24)
                s.blit(sprite("star"), (sx - 3, sy - 3))
            body = "white" if hit else ("purple" if angry else "night")
            pygame.draw.circle(s, col("lavender"), (x, y), 17)
            pygame.draw.circle(s, col(body), (x, y), 15)
            pygame.draw.circle(s, col("ink"), (x + 5, y - 4), 12)
            for side in (-1, 1):
                ex = x + side * 6
                pygame.draw.circle(s, col("yellow"), (ex, y - 2), 3)
                pygame.draw.circle(s, col("ink"), (ex + 1, y - 3), 3)
            pygame.draw.line(s, col("yellow"), (x - 3, y + 7), (x + 3, y + 7))
            for i in range(3):
                s.fill(col("white"), (x - 10 + (i * 9 + int(t * 6)) % 20, y + 10 - i * 3, 1, 1))


def draw_proj(s, p, x, y, t):
    k = p.kind
    if k == "feather":
        pygame.draw.line(s, col("white"), (x - 3, y - 1), (x + 3, y + 1), 2)
        s.fill(col("gray"), (x - 3, y - 1, 2, 1))
    elif k == "drop":
        pygame.draw.circle(s, col("blue"), (x, y), 3)
        pygame.draw.circle(s, col("sky"), (x, y), 2)
        s.fill(col("white"), (x - 1, y - 1, 1, 1))
    elif k == "lantern":
        pygame.draw.rect(s, col("black"), (x - 4, y - 5, 9, 11), border_radius=3)
        pygame.draw.rect(s, col("red"), (x - 3, y - 4, 7, 9), border_radius=3)
        s.fill(col("yellow"), (x - 1, y - 2, 3, 5))
        s.fill(col("black"), (x - 2, y - 6, 5, 1))
    elif k == "confetti":
        s.fill(col(rainbow(int(p.age * 10 + p.ox), 0)), (x - 1, y - 1, 3, 3))
    elif k == "crescent":
        for i in range(7):
            a = -1.2 + i * 0.4 + t * 8
            s.fill(col("yellow"), (x + int(math.cos(a) * 4), y + int(math.sin(a) * 4), 2, 2))
    else:
        s.blit(sprite("star"), (x - 3, y - 3))
        if int(t * 12) % 2:
            s.fill(col("white"), (x, y - 5, 1, 2))
