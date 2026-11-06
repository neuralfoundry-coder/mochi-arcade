"""BOUNCE BUN bosses (every 10th stage): CAKE CASTLE, JELLY DONUT, COOKIE JAR, GINGER-BOT, CANDY WHALE.

Each boss has telegraphed attacks (a warning first, then the shot), phases at 66% / 33% health and borrows
attacks from the other bosses on later tiers. Mirrored by ios/MochiArcade/Games/BounceBunBoss.swift.
"""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.gfx import H, W, col, draw_text

LEFT, RIGHT, TOP = 8, W - 8, 20
PADDLE_Y = 182
STYLE = {"cake": "flame", "donut": "jam", "jar": "crumb", "robot": "gear", "whale": "candy"}


class Body:
    """A damageable boss body; (x, y) is its centre."""

    def __init__(self, x, y, w, h, hp, size=0):
        self.x, self.y, self.w, self.h = float(x), float(y), w, h
        self.vx = self.vy = 0.0
        self.hp = hp
        self.size = size
        self.flash = 0.0
        self.shake = 0.0
        self.alive = True

    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)


class Part:
    """Candles (cake) and shield arms (robot): own health, block the ball, may shoot."""

    def __init__(self, kind, dx, dy, w, h, hp):
        self.kind, self.dx, self.dy, self.w, self.h = kind, dx, dy, w, h
        self.hp = self.maxhp = hp
        self.x = self.y = 0.0
        self.alive = True
        self.flash = 0.0
        self.regrow = 0.0
        self.glow = 0.0

    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)


class Tele:
    """A telegraphed attack: shown for t seconds, then it fires."""

    def __init__(self, kind, x, y, t, xs=None):
        self.kind, self.x, self.y, self.t, self.full = kind, x, y, t, t
        self.xs = xs or []


class Proj:
    def __init__(self, x, y, vx, vy, style, g=0.0):
        self.x, self.y, self.vx, self.vy, self.style, self.g = x, y, vx, vy, style, g
        self.alive = True


class Boss:
    def __init__(self, game, spec):
        self.g = game
        self.kind = spec["kind"]
        self.name = spec["name"]
        self.tier = spec["tier"]
        self.maxhp = spec["hp"]
        self.rate = spec["rate"]
        self.spd = spec["speed"]
        self.extra = list(spec["extra"])
        self.style = STYLE[self.kind]
        self.t = 0.0
        self.phase = 1
        self.atk = 2.0
        self.n_atk = 0
        self.state = "enter"
        self.die_t = 0.0
        self.boom_t = 0.0
        self.teles = []
        self.projs = []
        self.parts = []
        self.beams = []          # active beams: [x, time left]
        self.open = False        # cookie jar lid
        self.open_t = 3.0
        self.lid_hits = 0
        self.dir = 1             # whale heading
        self.dive = 0            # whale: 0 swimming, 1 diving up, 2 hidden, 3 coming back
        self.dive_t = 8.0
        self.target_y = 60.0
        k = self.kind
        if k == "cake":
            self.bodies = [Body(W / 2, -40, 96, 40, self.maxhp)]
            self.target_y = 62
            spots = [(0, -34), (-28, -24), (28, -24), (-41, -12), (41, -12)]
            for dx, dy in spots[:3 + (self.tier >= 6) + (self.tier >= 11)]:
                self.parts.append(Part("candle", dx, dy, 6, 9, 2 + self.tier // 5))
        elif k == "donut":
            b = Body(W / 2, -40, 44, 36, self.maxhp)
            b.vx, b.vy = 55 * self.spd, 30 * self.spd
            self.bodies = [b]
            self.target_y = 58
        elif k == "jar":
            self.bodies = [Body(W / 2, -40, 52, 54, self.maxhp)]
            self.target_y = 62
        elif k == "robot":
            self.bodies = [Body(W / 2, -40, 40, 44, self.maxhp)]
            self.target_y = 52
            for side in (-1, 1):
                self.parts.append(Part("arm", side, 0, 30, 8, 4 + self.tier // 3))
        else:
            self.bodies = [Body(W / 2, -40, 76, 30, self.maxhp)]
            self.target_y = 52

    # ------------------------------------------------------------------ state
    @property
    def hp(self):
        return sum(max(0, b.hp) for b in self.bodies if b.alive)

    def vulnerable(self, b):
        if self.state != "fight":
            return False
        if self.kind == "jar":
            return self.open
        if self.kind == "whale":
            return self.dive == 0
        return True

    def colliders(self):
        """[(rect, body or part)] the gumball and the lasers bounce off."""
        out = []
        if self.state not in ("fight", "enter"):
            return out
        for b in self.bodies:
            if not b.alive or b.y + b.h / 2 < TOP:
                continue
            if self.kind == "cake":
                cx, cy = int(b.x), int(b.y)
                out.append((pygame.Rect(cx - 48, cy + 2, 96, 18), b))
                out.append((pygame.Rect(cx - 34, cy - 10, 68, 12), b))
                out.append((pygame.Rect(cx - 22, cy - 20, 44, 10), b))
            else:
                out.append((b.rect(), b))
        for p in self.parts:
            if p.alive:
                out.append((p.rect(), p))
        return out

    # ------------------------------------------------------------------ damage
    def hit(self, target, dmg):
        """The gumball or a laser hit a body or part. Returns True when it did damage."""
        g = self.g
        if isinstance(target, Part):
            if not target.alive or self.state != "fight":
                return False
            target.hp -= dmg
            target.flash = 0.12
            if target.hp <= 0:
                target.alive = False
                target.regrow = 10.0
                g.parts.burst(target.x, target.y, 14, ("yellow", "orange", "white"), 70, 0.6)
                g.app.audio.play("explode")
                g.score_at(500, target.x, target.y)
                self.damage(self.bodies[0] if self.bodies[0].alive else None,
                            max(1, int(self.maxhp * (0.04 if self.kind == "cake" else 0.06))))
            else:
                g.app.audio.play("brick")
            return True
        b = target
        if not self.vulnerable(b):
            b.flash = 0.05
            g.app.audio.play("tin")
            if self.kind == "jar" and self.state == "fight" and not self.open:
                self.lid_hits += 1
                b.shake = 0.25
                if self.lid_hits >= 2:      # knock the lid off early
                    self.open_lid()
            return False
        self.damage(b, dmg)
        return True

    def damage(self, b, dmg):
        if b is None or not b.alive:
            return
        g = self.g
        b.hp -= dmg
        b.flash = 0.1
        g.hype.hitstop(0.035)
        g.app.audio.play("brick")
        g.parts.burst(b.x, b.y + b.h / 2, 5, ("white", "pink", "yellow"), 50, 0.4)
        g.score_at(30 * dmg)
        if self.kind == "donut":
            self.split(b)
        if b.hp <= 0:
            b.alive = False
            g.parts.burst(b.x, b.y, 24, ("pink", "hotpink", "peach", "yellow"), 90, 0.8)
            g.app.audio.play("explode")
        old = self.phase
        f = self.hp / max(1, self.maxhp)
        self.phase = 1 if f > 0.66 else 2 if f > 0.33 else 3
        if self.phase > old and self.hp > 0:
            g.hype.banner("GRRR!!", f"{self.name} IS FURIOUS", color="red", dur=1.2, scale=2, sound="boom")
            g.hype.flash("red", 0.2)
            g.app.shake(3, 0.3)
            if self.kind == "cake" and self.phase == 3 and self.tier >= 4:
                for p in self.parts:       # the candles light up again
                    p.alive, p.hp = True, p.maxhp
        if self.hp <= 0:
            self.start_dying()

    def split(self, b):
        """Jelly donut: big -> 2 medium (at half health) -> 2 small each (tier 3+)."""
        if b.hp <= 0:
            return
        if (b.size == 0 and b.hp <= self.maxhp * 0.5) or (b.size == 1 and self.tier >= 3 and b.hp <= self.maxhp * 0.14):
            b.alive = False
            dims = [(30, 24), (20, 16)][b.size]
            h1 = b.hp // 2
            for i, hp in enumerate((h1, b.hp - h1)):
                if hp <= 0:
                    continue
                nb = Body(b.x + (i * 2 - 1) * 10, b.y, dims[0], dims[1], hp, b.size + 1)
                sp = math.hypot(b.vx, b.vy) * 1.2 + 10
                nb.vx = (i * 2 - 1) * sp * 0.8
                nb.vy = -sp * 0.6
                nb.flash = 0.2
                self.bodies.append(nb)
            self.bodies = [x for x in self.bodies if x.alive]
            self.g.app.audio.play("pop")
            self.g.hype.banner("SPLIT!", color="pink", dur=0.8, scale=1)

    def open_lid(self):
        self.open = True
        self.open_t = 4.0
        self.lid_hits = 0
        self.g.app.audio.play("pop")
        b = self.bodies[0]
        self.g.parts.burst(b.x, b.y - 28, 10, ("hotpink", "red", "white"), 60, 0.5)
        self.attack("spread", b.x, b.y - 4)
        if self.phase >= 2:
            self.g.spawn_minions(1 + self.phase // 2 + self.tier // 6)

    def start_dying(self):
        self.state = "dying"
        self.die_t = 2.0
        self.teles = []
        self.projs = []
        self.beams = []
        g = self.g
        g.hype.slowmo(0.35, 1.6)
        g.hype.flash("white", 0.3)
        g.app.audio.play("boom")

    # ------------------------------------------------------------------ attacks
    def attack(self, kind, sx, sy):
        tr = self.tier
        if kind == "aimed":
            self.teles.append(Tele("aimed", sx, sy, 0.75))
        elif kind == "drop":
            self.teles.append(Tele("drop", sx, sy, 0.6))
        elif kind == "spread":
            self.teles.append(Tele("spread", sx, sy, 0.7))
        elif kind == "rain":
            n = min(7, 3 + tr // 4)
            xs = [random.uniform(LEFT + 10, RIGHT - 10) for _ in range(n)]
            self.teles.append(Tele("rain", sx, TOP, 1.0, xs))
        elif kind == "beam":
            xs = [self.g.px]
            if self.phase >= 3 or tr >= 12:
                xs.append(max(LEFT + 12, min(RIGHT - 12, self.g.px + random.choice((-70, 70)))))
            self.teles.append(Tele("beam", sx, sy, 1.0, xs))
        elif kind == "arc":
            self.teles.append(Tele("arc", sx, sy, 0.8))

    def fire(self, te):
        tr = self.tier
        st = self.style
        g = self.g
        if te.kind == "aimed":
            dx, dy = g.px - te.x, PADDLE_Y - te.y
            d = math.hypot(dx, dy) or 1
            v = 85 + 4 * tr
            self.projs.append(Proj(te.x, te.y, dx / d * v, dy / d * v, st))
            g.app.audio.play("shoot")
        elif te.kind == "drop":
            vx = max(-40.0, min(40.0, (g.px - te.x) * 0.3))
            self.projs.append(Proj(te.x, te.y, vx, 90 + 4 * tr, st))
            g.app.audio.play("shoot")
        elif te.kind == "spread":
            n = 5 if (tr >= 8 or self.phase >= 3) else 3
            for i in range(n):
                a = math.radians((i - (n - 1) / 2) * 18)
                v = 80 + 3 * tr
                self.projs.append(Proj(te.x, te.y, math.sin(a) * v, math.cos(a) * v, st))
            g.app.audio.play("shoot")
        elif te.kind == "rain":
            for x in te.xs:
                self.projs.append(Proj(x, TOP + 2, 0.0, 100 + 3 * tr, "drop"))
            g.app.audio.play("shoot")
        elif te.kind == "beam":
            for x in te.xs:
                self.beams.append([x, 0.5])
            g.app.audio.play("explode")
            g.app.shake(2, 0.3)
        elif te.kind == "arc":
            for _ in range(min(8, 4 + tr // 5)):
                self.projs.append(Proj(te.x, te.y, random.uniform(-80, 80), random.uniform(-120, -70), "candy", 150))
            g.app.audio.play("bubble")

    def pick_attack(self):
        """Choose and launch the next attack for the current phase."""
        self.n_atk += 1
        k = self.kind
        alive = [b for b in self.bodies if b.alive]
        if not alive:
            return
        b = random.choice(alive)
        if self.extra and self.n_atk % 3 == 0:
            self.attack(self.extra[(self.n_atk // 3) % len(self.extra)], b.x, b.y + b.h / 2)
            return
        if k == "cake":
            candles = [p for p in self.parts if p.alive]
            if self.phase >= 2 and self.n_atk % 2 == 0:
                self.attack("rain", b.x, b.y)
            elif candles:
                for p in random.sample(candles, min(len(candles), 1 + (self.phase >= 3))):
                    p.glow = 0.75
                    self.attack("spread" if self.phase >= 3 else "aimed", p.x, p.y - 4)
            else:
                self.attack("spread", b.x, b.y + 20)
        elif k == "donut":
            b.shake = 0.6
            self.attack("spread" if (self.phase >= 3 and self.n_atk % 2) else "drop", b.x, b.y + b.h / 2)
        elif k == "jar":
            if not self.open:
                self.attack("aimed" if self.phase >= 3 else "drop", b.x, b.y + 26)
        elif k == "robot":
            if self.phase >= 2 and self.n_atk % 2 == 0:
                for p in self.parts:
                    if p.alive:
                        self.attack("spread", p.x, p.y)
                        break
                else:
                    self.attack("beam", b.x, b.y - 8)
            else:
                self.attack("beam", b.x, b.y - 8)
        else:
            if self.dive == 0:
                self.attack("arc", b.x + self.dir * 20, b.y - 14)
                if self.phase >= 3:
                    self.attack("aimed", b.x - self.dir * 30, b.y)

    # ------------------------------------------------------------------ frame
    def update(self, dt):
        self.t += dt
        g = self.g
        for b in self.bodies:
            b.flash = max(0.0, b.flash - dt)
            b.shake = max(0.0, b.shake - dt)
        for p in self.parts:
            p.flash = max(0.0, p.flash - dt)
            p.glow = max(0.0, p.glow - dt)
        if self.state == "enter":
            for b in self.bodies:
                b.y += (self.target_y - b.y) * min(1.0, dt * 2.5)
            self.place_parts()
            return
        if self.state == "dying":
            self.die_t -= dt
            self.boom_t -= dt
            if self.boom_t <= 0:
                self.boom_t = 0.12
                b = self.bodies[0]
                x = b.x + random.uniform(-b.w / 2, b.w / 2)
                y = b.y + random.uniform(-b.h / 2, b.h / 2)
                g.parts.burst(x, y, 10, ("yellow", "orange", "white", "pink"), 80, 0.6)
                g.app.audio.play("explode")
                g.app.shake(2, 0.15)
            if self.die_t <= 0:
                self.state = "dead"
                g.boss_defeated()
            return
        if self.state != "fight":
            return
        self.move(dt)
        self.place_parts()
        # attacks
        self.atk -= dt
        if self.atk <= 0:
            self.atk = self.rate * (1.0, 0.85, 0.7)[self.phase - 1]
            self.pick_attack()
        if self.kind == "jar":
            self.open_t -= dt
            if self.open and self.open_t <= 0:
                self.open = False
                self.open_t = self.rate * 1.0
                g.app.audio.play("lock")
            elif not self.open:
                if self.open_t <= 0.8:
                    self.bodies[0].shake = 0.1       # the lid rattles: about to open
                if self.open_t <= 0:
                    self.open_lid()
        if self.kind == "robot" and self.phase >= 3:     # shield arms grow back
            for p in self.parts:
                if not p.alive:
                    p.regrow -= dt
                    if p.regrow <= 0:
                        p.alive, p.hp, p.flash = True, p.maxhp, 0.3
        for te in self.teles:
            te.t -= dt
            if te.t <= 0:
                self.fire(te)
        self.teles = [te for te in self.teles if te.t > 0]
        # projectiles and beams vs the paddle
        for pr in self.projs:
            pr.vy += pr.g * dt
            pr.x += pr.vx * dt
            pr.y += pr.vy * dt
            if pr.y > H + 6 or pr.x < -6 or pr.x > W + 6:
                pr.alive = False
            elif g.paddle_hit(pr.x, pr.y, 3):
                pr.alive = False
        self.projs = [pr for pr in self.projs if pr.alive]
        for bm in self.beams:
            bm[1] -= dt
            if abs(bm[0] - g.px) < g.pw() / 2 + 4:
                g.paddle_hit(g.px, PADDLE_Y, 0, beam=True)
        self.beams = [bm for bm in self.beams if bm[1] > 0]

    def move(self, dt):
        t, s = self.t, self.spd
        k = self.kind
        if k == "cake":
            b = self.bodies[0]
            amp = 16 if self.phase == 1 else 70
            b.x = W / 2 + math.sin(t * (0.5 if self.phase == 1 else 0.7) * s) * amp
        elif k == "donut":
            for b in self.bodies:
                if not b.alive:
                    continue
                b.x += b.vx * dt
                b.y += b.vy * dt
                if b.x < LEFT + b.w / 2:
                    b.x, b.vx = LEFT + b.w / 2, abs(b.vx)
                elif b.x > RIGHT - b.w / 2:
                    b.x, b.vx = RIGHT - b.w / 2, -abs(b.vx)
                if b.y < TOP + 12 + b.h / 2:        # leave room for the gumball under the ceiling
                    b.y, b.vy = TOP + 12 + b.h / 2, abs(b.vy)
                elif b.y > 98 - b.h / 2:            # and stay above the snack rows
                    b.y, b.vy = 98 - b.h / 2, -abs(b.vy)
        elif k == "jar":
            b = self.bodies[0]
            b.x = W / 2 + math.sin(t * 0.6 * s) * 60
        elif k == "robot":
            b = self.bodies[0]
            b.x = W / 2 + math.sin(t * 0.45 * s) * 80
        else:
            b = self.bodies[0]
            if self.dive == 0:
                b.x += self.dir * 38 * s * (1.4 if self.phase >= 3 else 1.0) * dt
                if b.x > RIGHT - 46:
                    self.dir = -1
                elif b.x < LEFT + 46:
                    self.dir = 1
                b.y = self.target_y + math.sin(t * 1.5) * 5
                if self.phase >= 2:
                    self.dive_t -= dt
                    if self.dive_t <= 0:
                        self.dive = 1
                        self.g.app.audio.play("bubble")
            elif self.dive == 1:
                b.y -= 110 * dt
                if b.y < -30:
                    self.dive, self.dive_t = 2, 1.4
                    self.attack("rain", b.x, TOP)
            elif self.dive == 2:
                self.dive_t -= dt
                if self.dive_t <= 0:
                    self.dive = 3
                    b.x = max(LEFT + 46, min(RIGHT - 46, self.g.px + random.uniform(-60, 60)))
            else:
                b.y += 90 * dt
                if b.y >= self.target_y:
                    b.y = self.target_y
                    self.dive, self.dive_t = 0, 9.0

    def place_parts(self):
        b = self.bodies[0]
        if self.kind == "cake":
            for p in self.parts:
                p.x, p.y = b.x + p.dx, b.y + p.dy
        elif self.kind == "robot":
            sw = math.sin(self.t * 1.4 * self.spd) * 44
            for p in self.parts:
                p.x, p.y = b.x + p.dx * sw, b.y + 36

    # ------------------------------------------------------------------ draw
    def draw(self, s, t):
        for bm in self.beams:
            x = int(bm[0])
            w = 10 if int(t * 30) % 2 else 8
            s.fill(col("hotpink"), (x - w // 2, TOP, w, H - TOP))
            s.fill(col("white"), (x - 2, TOP, 4, H - TOP))
        if self.state == "dead":
            return
        k = self.kind
        for b in self.bodies:
            if not b.alive:
                continue
            ox = int(math.sin(t * 60) * 2) if b.shake > 0 else 0
            x, y = int(b.x) + ox, int(b.y)
            hit = b.flash > 0 and int(t * 40) % 2 == 0
            if self.state == "dying" and int(t * 20) % 2:
                hit = True
            if k == "cake":
                self.draw_cake(s, x, y, t, hit)
            elif k == "donut":
                self.draw_donut(s, b, x, y, t, hit)
            elif k == "jar":
                self.draw_jar(s, x, y, t, hit)
            elif k == "robot":
                self.draw_robot(s, x, y, t, hit)
            else:
                self.draw_whale(s, x, y, t, hit)
        for p in self.parts:
            if p.alive:
                self.draw_part(s, p, t)
        for te in self.teles:
            self.draw_tele(s, te, t)
        for pr in self.projs:
            if pr.y > TOP + 2:
                draw_proj(s, pr, t)

    def mood(self):
        return "angry" if self.phase >= 2 else "happy"

    def draw_cake(self, s, x, y, t, hit):
        tiers = [(x - 48, y + 2, 96, 18), (x - 34, y - 10, 68, 12), (x - 22, y - 20, 44, 10)]
        for i, r in enumerate(tiers):
            body = "white" if hit else ("cream", "peach", "cream")[i]
            pygame.draw.rect(s, col("black"), pygame.Rect(r).inflate(2, 2), border_radius=3)
            pygame.draw.rect(s, col(body), r, border_radius=3)
            s.fill(col("pink" if not hit else "white"), (r[0], r[1], r[2], 4))
            for dx in range(4, r[2] - 3, 9):       # frosting drips
                s.fill(col("pink"), (r[0] + dx, r[1] + 4, 3, 2 + (dx // 9) % 3))
            s.fill(col("choco"), (r[0] + 2, r[1] + r[3] - 3, r[2] - 4, 1))
        cute.eyes(s, x, y + 9, 10, 0, self.mood(), blink=int(t * 1.3) % 6 == 0, size=2)
        cute.mouth(s, x, y + 14, "angry" if self.phase >= 3 else "happy")
        cute.blush(s, x, y + 12, 14)
        pygame.draw.circle(s, col("red"), (x, y - 23), 3)
        s.fill(col("white"), (x - 1, y - 25, 1, 1))

    def draw_donut(self, s, b, x, y, t, hit):
        w, h = b.w, b.h
        r = pygame.Rect(x - w // 2, y - h // 2, w, h)
        pygame.draw.ellipse(s, col("black"), r.inflate(2, 2))
        pygame.draw.ellipse(s, col("white" if hit else "peach"), r)
        pygame.draw.ellipse(s, col("white" if hit else "hotpink"), r.inflate(-4, -6).move(0, -2))
        hole = pygame.Rect(0, 0, max(4, w // 4), max(3, h // 5))
        hole.center = (x, y + h // 8)
        pygame.draw.ellipse(s, col("ink"), hole)
        for i in range(7):
            a = i * 0.9 + b.size
            sx = x + int(math.cos(a) * w * 0.32)
            sy = y - 2 + int(math.sin(a) * h * 0.25)
            s.fill(col(("yellow", "mint", "sky", "white")[i % 4]), (sx, sy, 2, 1))
        if b.size < 2:
            cute.eyes(s, x, y - h // 5, max(3, w // 6), 0, self.mood(), blink=int(t * 1.5) % 5 == 0)
        else:
            cute.eyes(s, x, y - 3, 3, 0, "angry")

    def draw_jar(self, s, x, y, t, hit):
        r = pygame.Rect(x - 26, y - 22, 52, 50)
        pygame.draw.rect(s, col("black"), r.inflate(2, 2), border_radius=8)
        pygame.draw.rect(s, col("white" if hit else "sky"), r, border_radius=8)
        pygame.draw.rect(s, col("ink"), r.inflate(-6, -6), border_radius=6)
        for i, (cx, cy) in enumerate(((-12, 14), (4, 16), (14, 8), (-6, 4), (8, -2))):
            pygame.draw.circle(s, col("peach"), (x + cx, y + cy), 6)
            s.fill(col("choco"), (x + cx - 2, y + cy - 1, 2, 1))
            s.fill(col("choco"), (x + cx + 1, y + cy + 2, 2, 1))
        s.fill(col("white"), (r.x + 4, r.y + 6, 2, 30))
        if self.open:
            # the lid pops up and an eye peeks out
            pygame.draw.circle(s, col("white"), (x, y - 20), 9)
            px = max(-4, min(4, int((self.g.ball_x() - x) / 20)))
            pygame.draw.circle(s, col("black"), (x + px, y - 19), 4)
            s.fill(col("white"), (x + px - 2, y - 21, 1, 1))
            lid = pygame.Rect(x - 28, y - 44 - int(abs(math.sin(t * 8)) * 3), 56, 9)
        else:
            lid = pygame.Rect(x - 28 + (int(math.sin(t * 50) * 2) if self.open_t < 0.8 else 0), y - 30, 56, 9)
            cute.eyes(s, x, y - 14, 9, 0, "angry" if self.phase >= 2 else "sleepy")
        pygame.draw.rect(s, col("black"), lid.inflate(2, 2), border_radius=3)
        pygame.draw.rect(s, col("red" if not hit else "white"), lid, border_radius=3)
        s.fill(col("pink"), (lid.x + 3, lid.y + 2, lid.w - 6, 1))
        s.fill(col("red"), (lid.centerx - 4, lid.y - 3, 8, 3))

    def draw_robot(self, s, x, y, t, hit):
        body = col("white" if hit else "brown")
        r = pygame.Rect(x - 20, y - 6, 40, 28)
        pygame.draw.rect(s, col("black"), r.inflate(2, 2), border_radius=5)
        pygame.draw.rect(s, body, r, border_radius=5)
        pygame.draw.circle(s, col("black"), (x, y - 12), 13)
        pygame.draw.circle(s, body, (x, y - 12), 12)
        # icing details
        for i in range(-16, 17, 4):
            s.fill(col("white"), (x + i, y - 4, 2, 1))
        for i, c in enumerate(("red", "mint", "yellow")):
            pygame.draw.circle(s, col(c), (x, y + 3 + i * 6), 2)
        charging = any(te.kind == "beam" for te in self.teles)
        eye = "red" if charging and int(t * 16) % 2 else "white"
        for side in (-1, 1):
            pygame.draw.circle(s, col(eye), (x + side * 5, y - 14), 3)
            s.fill(col("black"), (x + side * 5 - (side < 0), y - 14, 1, 2))
        s.fill(col("white"), (x - 4, y - 7, 8, 1))
        s.fill(col("white"), (x - 5, y - 8, 1, 1))
        s.fill(col("white"), (x + 4, y - 8, 1, 1))
        # antenna
        s.fill(col("gray"), (x, y - 29, 1, 5))
        pygame.draw.circle(s, col("red" if int(t * 3) % 2 else "yellow"), (x, y - 30), 2)

    def draw_whale(self, s, x, y, t, hit):
        d = self.dir
        body = col("white" if hit else "sky")
        r = pygame.Rect(x - 38, y - 15, 76, 30)
        tx = x - d * 38
        pygame.draw.polygon(s, col("black"), [(tx, y), (tx - d * 16, y - 12), (tx - d * 16, y + 8)])
        pygame.draw.polygon(s, body, [(tx + d, y), (tx - d * 14, y - 10), (tx - d * 14, y + 6)])
        pygame.draw.ellipse(s, col("black"), r.inflate(2, 2))
        pygame.draw.ellipse(s, body, r)
        pygame.draw.ellipse(s, col("mint"), (x - 30, y + 2, 60, 12))
        for i in range(5):
            s.fill(col("teal"), (x - 20 + i * 9, y + 6, 1, 6))
        ex = x + d * 22
        pygame.draw.circle(s, col("white"), (ex, y - 3), 4)
        pygame.draw.circle(s, col("black"), (ex + d, y - 3), 2)
        if self.phase >= 2:
            s.fill(col("black"), (ex - 3, y - 8 - (d > 0), 6, 1))
        cute.blush(s, ex, y + 3, 3)
        s.fill(col("blue"), (x + d * 6, y - 15, 4, 2))
        if any(te.kind == "arc" for te in self.teles):       # the spout builds up
            hh = 4 + int(abs(math.sin(t * 20)) * 6)
            s.fill(col("white"), (x + d * 6 + 1, y - 15 - hh, 2, hh))
            pygame.draw.circle(s, col("pink"), (x + d * 6 + 2, y - 16 - hh), 3)

    def draw_part(self, s, p, t):
        hit = p.flash > 0 and int(t * 40) % 2 == 0
        r = p.rect()
        if p.kind == "candle":
            pygame.draw.rect(s, col("black"), r.inflate(2, 2))
            s.fill(col("white" if hit else "cream"), r)
            for yy in range(r.y + 1, r.bottom, 3):
                s.fill(col("pink"), (r.x, yy, r.w, 1))
            big = p.glow > 0
            fh = 5 + (3 if big else 0) + int(math.sin(t * 20 + p.dx) * 1)
            fc = "white" if big and int(t * 20) % 2 else "yellow"
            pygame.draw.ellipse(s, col("orange"), (r.centerx - 3, r.y - fh, 6, fh + 1))
            pygame.draw.ellipse(s, col(fc), (r.centerx - 1, r.y - fh + 2, 3, fh - 2))
        else:
            pygame.draw.rect(s, col("black"), r.inflate(2, 2), border_radius=3)
            pygame.draw.rect(s, col("white"), r, border_radius=3)
            if not hit:
                for i in range(0, r.w, 6):
                    s.fill(col("red"), (r.x + i, r.y + 1, 3, r.h - 2))
            s.fill(col("white"), (r.x + 2, r.y + 1, r.w - 4, 1))
            for i in range(p.maxhp):
                s.fill(col("lime" if i < p.hp else "darkgray"), (r.x + 2 + i * 3, r.bottom + 2, 2, 1))

    def draw_tele(self, s, te, t):
        blink = int(t * 12) % 2 == 0
        if te.kind in ("aimed", "drop", "spread", "arc"):
            if blink:
                draw_text(s, "!", int(te.x) - 2, int(te.y) - 14, "yellow", outline="red")
            if te.kind == "aimed":
                x = int(self.g.px)
                pygame.draw.circle(s, col("red"), (x, PADDLE_Y + 3), 7 if blink else 6, 1)
        elif te.kind == "rain":
            for x in te.xs:
                if blink:
                    pygame.draw.polygon(s, col("red"), [(x - 4, 190), (x + 4, 190), (x, 195)])
                s.fill(col("red"), (int(x), TOP + 2, 1, 3))
        elif te.kind == "beam":
            for x in te.xs:
                xi = int(x)
                for yy in range(TOP, H, 6):
                    if (yy // 6 + int(t * 20)) % 2:
                        s.fill(col("red"), (xi, yy, 1, 3))
                if blink:
                    pygame.draw.rect(s, col("red"), (xi - 6, PADDLE_Y - 4, 12, 14), 1)


def draw_proj(s, pr, t):
    x, y = int(pr.x), int(pr.y)
    st = pr.style
    if st == "flame":
        pygame.draw.circle(s, col("red"), (x, y), 4)
        pygame.draw.circle(s, col("orange"), (x, y), 3)
        pygame.draw.circle(s, col("yellow"), (x, y - 1), 1)
    elif st == "jam":
        pygame.draw.circle(s, col("black"), (x, y), 4)
        pygame.draw.circle(s, col("red"), (x, y), 3)
        s.fill(col("pink"), (x - 1, y - 2, 1, 1))
    elif st == "crumb":
        s.fill(col("black"), (x - 3, y - 3, 7, 7))
        s.fill(col("peach"), (x - 2, y - 2, 5, 5))
        s.fill(col("choco"), (x, y, 1, 1))
    elif st == "gear":
        pygame.draw.circle(s, col("black"), (x, y), 4)
        pygame.draw.circle(s, col("yellow" if int(t * 10) % 2 else "orange"), (x, y), 3)
        s.fill(col("black"), (x, y, 1, 1))
    elif st == "candy":
        pygame.draw.circle(s, col("black"), (x, y), 4)
        pygame.draw.circle(s, col("hotpink"), (x, y), 3)
        s.fill(col("white"), (x - 1, y - 1, 1, 1))
    else:
        pygame.draw.circle(s, col("black"), (x, y), 3)
        pygame.draw.circle(s, col("white"), (x, y), 2)
        s.fill(col("pink"), (x, y + 1, 1, 1))
