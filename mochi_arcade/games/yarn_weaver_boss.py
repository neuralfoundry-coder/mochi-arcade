"""YARN WEAVER bosses: five original troublemakers that roam the open rug on every 10th stage.

You can't hit a boss - you take its rug away: every claim hurts it (claims close to it hurt double),
wrapping its minions hurts it too, and a boss squeezed into a tiny pocket is cornered at once.
Patterns: bolts (NIMBUS), pellets (TIN WHISKER), dash (DUST GULPER), bark (BIG SNOOT), dive (MADAME DUSTWING);
later bosses mix in each other's patterns. Mirrored in ios/MochiArcade/Games/YarnWeaverBoss.swift.
"""
import math
import random

import pygame

from mochi_arcade.cute import eyes, mouth
from mochi_arcade.gfx import col, draw_text

PATTERN = {"cloud": "bolts", "mouse": "pellets", "vacuum": "dash", "snoot": "bark", "moth": "dive"}
RADIUS = {"cloud": 15, "mouse": 12, "vacuum": 13, "snoot": 14, "moth": 13}


class Boss:
    def __init__(self, g, spec):
        self.g = g
        self.kind, self.name, self.tier = spec["kind"], spec["name"], spec["tier"]
        self.maxhp = self.hp = max(600, int(g.claimable * spec["hp"]))
        self.rate, self.speed = spec["rate"], spec["speed"] * g.hz_speed
        self.minions = spec["minions"]
        self.patterns = [PATTERN[self.kind]] + list(spec["extra"])
        self.pi = 0
        self.r = RADIUS[self.kind] + (3 if self.name == "GRAND FUZZ" else 0)
        self.x, self.y = 152.0, 60.0
        a = random.uniform(0.5, 2.6)
        self.vx, self.vy = math.cos(a) * self.speed, math.sin(a) * self.speed
        self.state = "intro"
        self.t = 0.0
        self.flash = 0.0
        self.cd = 2.0
        self.phase = 0
        self.tele = []            # [pattern, age, dur, tx, ty]
        self.shots = []           # pellets [x, y, vx, vy]
        self.rings = []           # bark waves [x, y, r, delay, max radius]
        self.bolts = []           # lightning [x, life]
        self.dash_t = 0.0
        self.mood = 0.0           # >0: showing an attack face
        self.dead_t = 0.0
        self.stuck = 0

    # ---------------------------------------------------------------- update
    def update(self, dt):
        g = self.g
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.mood = max(0.0, self.mood - dt)
        if self.state == "dead":
            self.dead_t += dt
            return
        if self.state != "fight":
            return
        frac = self.hp / self.maxhp
        ph = 0 if frac > 0.66 else 1 if frac > 0.33 else 2
        if ph > self.phase:
            self.phase = ph
            g.hype.banner("RAGE UP!", self.name, color="red", dur=1.0, scale=1, sound="warning")
            for _ in range(self.minions):
                g.spawn_minion(self.kind, self.x, self.y)
        frozen = g.freeze > 0
        if not frozen:
            mult = 3.2 if self.dash_t > 0 else (0.4 if self.tele else 1.0)
            self.dash_t = max(0.0, self.dash_t - dt)
            sp = math.hypot(self.vx, self.vy) or 1.0
            want = self.speed * (1 + 0.15 * self.phase) * mult
            self.vx, self.vy = self.vx / sp * want, self.vy / sp * want
            g.move_ball(self, dt)
            g.touch_check(self.x, self.y, self.r, "boss")
            # attacks
            self.cd -= dt
            if self.cd <= 0 and not self.tele and self.dash_t <= 0:
                self.cd = self.rate * (1 - 0.18 * self.phase) * random.uniform(0.8, 1.15)
                self.begin(self.patterns[self.pi % len(self.patterns)])
                self.pi += 1
        for tl in self.tele:
            tl[1] += dt
            if tl[1] >= tl[2]:
                self.fire(tl)
        self.tele = [tl for tl in self.tele if tl[1] < tl[2]]
        self.update_shots(dt)

    def begin(self, pat):
        g = self.g
        kx, ky = g.kumo_px()
        if pat == "bolts":
            n = 2 + self.phase + self.tier // 6
            xs = [kx + random.choice((-1, 1)) * random.uniform(14, 30)] if g.weaving else []
            while len(xs) < n:
                xs.append(random.uniform(8, 296))
            for x in xs:
                self.tele.append(["bolts", 0.0, 0.85, max(4.0, min(300.0, x)), 0.0])
            g.app.audio.play("warning" if self.phase >= 2 else "trap")
        elif pat in ("pellets", "dash", "dive"):
            tx, ty = kx, ky
            if pat == "dive" and g.trail:
                c = g.trail[len(g.trail) // 2]
                tx, ty = (c % g.GW) * 2 + 1, (c // g.GW) * 2 + 1
            self.tele.append([pat, 0.0, {"pellets": 0.55, "dash": 0.75, "dive": 0.65}[pat], tx, ty])
        elif pat == "bark":
            self.tele.append(["bark", 0.0, 0.7, self.x, self.y])
            g.app.audio.play("trap")
        self.mood = 1.0

    def fire(self, tl):
        g = self.g
        pat, tx, ty = tl[0], tl[3], tl[4]
        if pat == "bolts":
            self.bolts.append([tx, 0.3])
            g.app.audio.play("explode")
            g.app.shake(2, 0.15)
            g.strike_column(tx)
        elif pat == "pellets":
            base = math.atan2(ty - self.y, tx - self.x)
            n = 1 + 2 * self.phase
            for k in range(n):
                a = base + math.radians((k - (n - 1) / 2) * 14)
                sp = 85 + 4 * self.tier
                self.shots.append([self.x, self.y, math.cos(a) * sp, math.sin(a) * sp])
            g.app.audio.play("shoot")
        elif pat in ("dash", "dive"):
            a = math.atan2(ty - self.y, tx - self.x)
            self.vx, self.vy = math.cos(a), math.sin(a)
            self.dash_t = 0.9 if pat == "dash" else 0.75
            g.app.audio.play("jump")
            if pat == "dive" and self.phase >= 1:
                g.spawn_minion("moth", self.x, self.y)
            if pat == "dash" and self.phase >= 1:
                g.spawn_minion("vacuum", self.x, self.y)
        elif pat == "bark":
            reach = 70.0 + 14 * self.phase
            self.rings.append([self.x, self.y, float(self.r), 0.0, reach])
            if self.phase >= 2:
                self.rings.append([self.x, self.y, float(self.r), 0.45, reach])
            g.app.audio.play("boom")
            g.app.shake(2, 0.2)
            g.floats.add(g.FX + self.x, g.FY + self.y - 20, "WOOF!", "white")

    def update_shots(self, dt):
        g = self.g
        for b in self.bolts:
            b[1] -= dt
        self.bolts = [b for b in self.bolts if b[1] > 0]
        for p in self.shots:
            for _ in range(2):
                p[0] += p[2] * dt / 2
                p[1] += p[3] * dt / 2
                if g.trail_hit(p[0], p[1], 2):
                    g.hazard_hit("pellet", p[0], p[1])
                    p[1] = -99
                    break
                if g.blocked(p[0], p[1]):
                    p[1] = -99
                    break
                if g.kumo_hit(p[0], p[1], 3):
                    g.hazard_hit("pellet", p[0], p[1])
                    p[1] = -99
                    break
        self.shots = [p for p in self.shots if p[1] > -50]
        for rg in self.rings:
            if rg[3] > 0:
                rg[3] -= dt
                continue
            rg[2] += 105 * dt
            g.ring_check(rg[0], rg[1], rg[2])
        self.rings = [rg for rg in self.rings if rg[2] < rg[4]]

    def damage(self, n, near):
        if self.state != "fight":
            return 0
        dmg = n * (2 if near else 1)
        self.hp = max(0, self.hp - dmg)
        self.flash = 0.25
        return dmg

    # ---------------------------------------------------------------- drawing
    def draw(self, s, ox, oy, t):
        x, y = int(ox + self.x), int(oy + self.y)
        for tl in self.tele:
            self.draw_tele(s, ox, oy, tl, t)
        if self.state == "dead":
            return
        hit = self.flash > 0 and int(t * 20) % 2
        frozen = self.g.freeze > 0
        k = self.kind
        if self.name == "GRAND FUZZ":
            draw_cloud(s, x, y, self.r, t, hit, self.mood > 0, crown=True)
        elif k == "cloud":
            draw_cloud(s, x, y, self.r, t, hit, self.mood > 0)
        elif k == "mouse":
            draw_robomouse(s, x, y, t, hit, self.mood > 0, self.vx)
        elif k == "vacuum":
            draw_vacuum(s, x, y, t, hit, self.dash_t > 0 or self.mood > 0)
        elif k == "snoot":
            draw_snoot(s, x, y, t, hit, self.mood > 0)
        else:
            draw_dustwing(s, x, y, t, hit, self.mood > 0)
        if frozen:
            draw_text(s, "Z", x + self.r, y - self.r - 6, "sky", shadow="ink")
        for b in self.bolts:
            bx = int(ox + b[0])
            pts = [(bx + (3 if j % 2 else -3), oy + j * 11) for j in range(17)]
            for i in range(len(pts) - 1):
                pygame.draw.line(s, col("yellow"), pts[i], pts[i + 1], 3)
                pygame.draw.line(s, col("white"), pts[i], pts[i + 1], 1)
        for p in self.shots:
            pygame.draw.circle(s, col("black"), (int(ox + p[0]), int(oy + p[1])), 4)
            pygame.draw.circle(s, col("yellow"), (int(ox + p[0]), int(oy + p[1])), 3)
            s.fill(col("orange"), (int(ox + p[0]), int(oy + p[1]), 1, 1))
        for rg in self.rings:
            if rg[3] > 0:
                continue
            pygame.draw.circle(s, col("white" if int(t * 12) % 2 else "yellow"), (int(ox + rg[0]), int(oy + rg[1])),
                               int(rg[2]), 2)

    def draw_tele(self, s, ox, oy, tl, t):
        pat, age, dur, tx, ty = tl
        blink = int(t * 12) % 2
        if pat == "bolts":
            bx = int(ox + tx)
            off = int(age * 40) % 6
            for yy in range(oy + off, oy + 176, 6):
                s.fill(col("yellow" if blink else "orange"), (bx - 1, yy, 3, 3))
            draw_text(s, "!", bx - 2, oy + 2, "yellow" if blink else "red", shadow="ink")
        elif pat in ("pellets", "dash", "dive"):
            c = {"pellets": "red", "dash": "orange", "dive": "lavender"}[pat]
            x0, y0 = ox + self.x, oy + self.y
            a = math.atan2(ty - self.y, tx - self.x)
            n = 6 if pat == "pellets" else 9
            for i in range(1, n):
                d = i * 8 + (age * 30) % 8
                if blink or pat != "pellets":
                    s.fill(col(c), (int(x0 + math.cos(a) * d) - 1, int(y0 + math.sin(a) * d) - 1, 2, 2))
        elif pat == "bark":
            r = int(self.r + 4 + (1 - age / dur) * 10)
            if blink:
                pygame.draw.circle(s, col("white"), (int(ox + self.x), int(oy + self.y)), r, 1)
                pygame.draw.circle(s, col("red"), (int(ox + self.x), int(oy + self.y)), int(70 + 14 * self.phase), 1)


# ----------------------------------------------------------------------------- boss art (cute, original)
def draw_cloud(s, x, y, r, t, hit, angry, crown=False):
    k = r / 15
    puffs = [(-10, 3, 9), (10, 3, 9), (0, -5, 11), (-5, 7, 8), (6, 7, 8)]
    bob = int(math.sin(t * 3) * 2)
    for dx, dy, rr in puffs:
        pygame.draw.circle(s, col("black"), (x + int(dx * k), y + int(dy * k) + bob), int(rr * k) + 2)
    for dx, dy, rr in puffs:
        pygame.draw.circle(s, col("gray"), (x + int(dx * k), y + int(dy * k) + bob + 2), int(rr * k))
    for dx, dy, rr in puffs:
        pygame.draw.circle(s, col("white" if hit else "lavender"), (x + int(dx * k), y + int(dy * k) + bob), int(rr * k) - 1)
    s.fill(col("white"), (x - int(6 * k), y - int(10 * k) + bob, 4, 2))
    eyes(s, x, y + bob, 5, 0, "angry" if angry else "happy", blink=int(t * 2) % 6 == 0, size=2)
    mouth(s, x, y + 6 + bob, "angry" if angry else "happy")
    pygame.draw.ellipse(s, col("pink"), (x - 12, y + 4 + bob, 4, 2))
    pygame.draw.ellipse(s, col("pink"), (x + 9, y + 4 + bob, 4, 2))
    if int(t * 5) % 2:
        for dx in (-8, 6):
            bx, by = x + dx, y + int(14 * k) + bob
            pygame.draw.lines(s, col("yellow"), False, [(bx, by), (bx + 3, by + 3), (bx, by + 5), (bx + 3, by + 9)], 2)
    if crown:
        pts = [(x - 9, y - 15 + bob), (x - 9, y - 22 + bob), (x - 4, y - 18 + bob), (x, y - 24 + bob),
               (x + 4, y - 18 + bob), (x + 9, y - 22 + bob), (x + 9, y - 15 + bob)]
        pygame.draw.polygon(s, col("yellow"), pts)
        pygame.draw.lines(s, col("black"), True, pts, 1)
        s.fill(col("red"), (x - 1, y - 19 + bob, 2, 2))


def draw_robomouse(s, x, y, t, hit, aiming, vx):
    body = "white" if hit else "gray"
    for d in (-1, 1):                       # round ears
        pygame.draw.circle(s, col("black"), (x + d * 9, y - 9), 7)
        pygame.draw.circle(s, col(body), (x + d * 9, y - 9), 6)
        pygame.draw.circle(s, col("pink"), (x + d * 9, y - 9), 3)
    pygame.draw.ellipse(s, col("black"), (x - 14, y - 9, 28, 20))
    pygame.draw.ellipse(s, col(body), (x - 13, y - 8, 26, 18))
    s.fill(col("white"), (x - 8, y - 6, 6, 2))
    for i in range(3):                      # rivets
        s.fill(col("darkgray"), (x - 8 + i * 8, y + 5, 2, 2))
    ec = "red" if aiming and int(t * 10) % 2 else "sky"
    for d in (-1, 1):
        pygame.draw.circle(s, col("black"), (x + d * 5, y - 1), 3)
        pygame.draw.circle(s, col(ec), (x + d * 5, y - 1), 2)
    pygame.draw.circle(s, col("hotpink"), (x, y + 3), 2)
    for d in (-1, 1):
        for k in (0, 3):
            pygame.draw.line(s, col("black"), (x + d * 4, y + 3 + k), (x + d * 13, y + 1 + k * 2), 1)
    a = t * 6                               # the wind-up key spins
    kx, ky = x, y - 12
    pygame.draw.line(s, col("yellow"), (kx, ky + 3), (kx, ky - 3), 2)
    pygame.draw.circle(s, col("yellow"), (kx + int(math.cos(a) * 4), ky - 4), 2)
    pygame.draw.circle(s, col("yellow"), (kx - int(math.cos(a) * 4), ky - 4), 2)
    tail = -1 if vx > 0 else 1
    pts = [(x + tail * 13, y + 4), (x + tail * 18, y + 1 + int(math.sin(t * 8) * 2)), (x + tail * 22, y + 4)]
    pygame.draw.lines(s, col("pink"), False, pts, 1)
    for d in (-1, 1):                       # wheels
        pygame.draw.circle(s, col("black"), (x + d * 7, y + 11), 3)
        s.fill(col("gray"), (x + d * 7 + (1 if int(t * 12) % 2 else -1), y + 11, 1, 1))


def draw_vacuum(s, x, y, t, hit, mad):
    pygame.draw.circle(s, col("black"), (x, y), 15)
    pygame.draw.circle(s, col("white" if hit else "darkgray"), (x, y), 14)
    pygame.draw.circle(s, col("gray"), (x, y), 11)
    pygame.draw.circle(s, col("darkgray"), (x, y), 11, 1)
    pygame.draw.rect(s, col("ink"), (x - 8, y - 6, 16, 8), border_radius=3)
    if mad:
        for d in (-1, 1):
            pygame.draw.line(s, col("red"), (x + d * 6, y - 4), (x + d * 2, y - 2), 2)
    else:
        for d in (-1, 1):
            s.fill(col("mint"), (x + d * 4 - 1, y - 4, 3, 3))
    s.fill(col("black"), (x - 6, y + 6, 12, 3))   # the gulping mouth
    s.fill(col("red" if mad else "white"), (x - 4, y + 7, 8, 1))
    for d in (-1, 1):                       # spinning side brushes
        a = t * (20 if mad else 8) * d
        bx, by = x + d * 12, y + 10
        for k in range(3):
            aa = a + k * 2.1
            pygame.draw.line(s, col("yellow"), (bx, by), (bx + int(math.cos(aa) * 5), by + int(math.sin(aa) * 5)), 1)
    if int(t * 4) % 2:
        s.fill(col("lime"), (x + 9, y - 9, 2, 2))


def draw_snoot(s, x, y, t, hit, barking):
    bob = int(math.sin(t * 4) * 1)
    for d in (-1, 1):                       # floppy ears
        pygame.draw.ellipse(s, col("black"), (x + d * 14 - 6, y - 8 + bob, 12, 20))
        pygame.draw.ellipse(s, col("choco"), (x + d * 14 - 5, y - 7 + bob, 10, 18))
    pygame.draw.ellipse(s, col("black"), (x - 17, y - 12 + bob, 34, 26))
    pygame.draw.ellipse(s, col("white" if hit else "brown"), (x - 16, y - 11 + bob, 32, 24))
    pygame.draw.ellipse(s, col("peach"), (x - 9, y - 1 + bob, 18, 13))
    for d in (-1, 1):
        pygame.draw.circle(s, col("black"), (x + d * 7, y - 5 + bob), 3)
        s.fill(col("white"), (x + d * 7 - 1, y - 7 + bob, 1, 1))
    pygame.draw.ellipse(s, col("black"), (x - 6, y - 1 + bob, 12, 8))
    s.fill(col("white"), (x - 3, y + bob, 3, 2))
    if barking:
        pygame.draw.ellipse(s, col("black"), (x - 5, y + 7 + bob, 10, 7))
        pygame.draw.ellipse(s, col("red"), (x - 3, y + 9 + bob, 6, 4))
    else:
        mouth(s, x, y + 8 + bob, "happy")


def draw_dustwing(s, x, y, t, hit, mad):
    flap = math.sin(t * 14)
    wh = 11 + int(flap * 4)
    wing = "white" if hit else "lavender"
    for d in (-1, 1):
        pygame.draw.ellipse(s, col("black"), (x + (2 if d > 0 else -19), y - wh, 17, wh + 2))
        pygame.draw.ellipse(s, col(wing), (x + (3 if d > 0 else -18), y - wh + 1, 15, wh))
        pygame.draw.circle(s, col("purple"), (x + d * 10, y - wh // 2), 3)
        pygame.draw.circle(s, col("yellow"), (x + d * 10, y - wh // 2), 1)
        pygame.draw.ellipse(s, col("black"), (x + (1 if d > 0 else -12), y - 1, 11, 10))
        pygame.draw.ellipse(s, col("cream"), (x + (2 if d > 0 else -11), y, 9, 8))
    pygame.draw.ellipse(s, col("black"), (x - 5, y - 9, 10, 22))
    pygame.draw.ellipse(s, col("peach"), (x - 4, y - 8, 8, 20))
    for i in range(3):
        s.fill(col("brown"), (x - 3, y - 2 + i * 4, 6, 1))
    pygame.draw.circle(s, col("black"), (x, y - 10), 5)
    pygame.draw.circle(s, col("cream"), (x, y - 10), 4)
    eyes(s, x, y - 10, 2, 0, "angry" if mad else "happy")
    for d in (-1, 1):
        pygame.draw.line(s, col("black"), (x + d * 2, y - 14), (x + d * 6, y - 20), 1)
        s.fill(col("yellow"), (x + d * 6 - 1, y - 21, 2, 2))
    s.fill(col("yellow"), (x - 2, y - 15, 5, 1))
