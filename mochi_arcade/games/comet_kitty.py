"""COMET KITTY - a fixed-screen space shooter starring Tama the teacup kitty (original game)."""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.gfx import H, W, Stars, col, draw_text, sprite

PY = 178            # player y (top of sprite)
POINTS = {0: (50, 100), 1: (80, 160), 2: (150, 400)}  # (in formation, diving)


def bezier(p, u):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p
    a, b, c, d = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3
    return a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3


class Enemy:
    def __init__(self, kind, col_, row, delay, side):
        self.kind, self.col, self.row = kind, col_, row
        self.hp = 2 if kind == 2 else 1
        self.state = "enter"
        self.t = 0.0
        self.delay = delay
        self.side = side
        self.x, self.y = (-20 if side < 0 else W + 20), 70
        self.path = None
        self.dur = 1.8
        self.shots = []
        self.hit_flash = 0.0
        self.alive = True

    def size(self):
        return (16, 14) if self.kind == 2 else (12, 12)

    def rect(self):
        w, h = self.size()
        return pygame.Rect(int(self.x) - w // 2, int(self.y) - h // 2, w, h)


class CometKitty(GameScene):
    music = "comet"

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES[d]
        self.spd = SPEED[d]
        self.wave = int(opt.get("wave", 1))
        self.stars = Stars(80, seed=7)
        self.px = W / 2
        self.shots, self.bullets, self.items = [], [], []
        self.inv = 2.0
        self.dead_t = None
        self.wingman = 0.0
        self.next_extra = 20000
        self.start_wave()

    # ---------------------------------------------------------------- waves
    def slot(self, e):
        sway = math.sin(self.t * 0.9) * 14
        breathe = 1 + math.sin(self.t * 1.7) * 0.06
        cx = W / 2 + ((e.col - 3.5) * 26) * breathe + sway
        return cx, 30 + e.row * 16

    def start_wave(self):
        self.enemies = []
        self.bonus = self.wave % 4 == 0
        self.wave_t = 0.0
        self.banner_t = 1.8
        self.dive_t = 3.0
        self.bonus_hits = 0
        layout = [(2, 0, c) for c in range(2, 6)] + [(1, r, c) for r in (1, 2) for c in range(1, 7)] + \
                 [(0, r, c) for r in (3, 4) for c in range(8)]
        if self.bonus:
            for g in range(5):
                side = -1 if g % 2 == 0 else 1
                for i in range(8):
                    e = Enemy(i % 2, 0, 0, g * 2.2 + i * 0.16, side)
                    e.state = "parade"
                    y0 = 30 + g * 22
                    e.path = [(-24, y0), (W * 0.35, 190), (W * 0.65, -10), (W + 24, y0 + 60)]
                    if side > 0:  # mirror for parades coming from the right
                        e.path = [(W - x, y) for x, y in e.path]
                    e.dur = 3.2
                    self.enemies.append(e)
            return
        for n, (kind, row, c) in enumerate(layout):
            group = n // 8
            side = -1 if group % 2 == 0 else 1
            self.enemies.append(Enemy(kind, c, row, 0.6 + group * 1.5 + (n % 8) * 0.13, side))

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        inp, au = self.app.input, self.app.audio
        self.stars.update(dt, 22)
        self.wave_t += dt
        self.banner_t -= dt
        self.inv = max(0.0, self.inv - dt)
        self.wingman = max(0.0, self.wingman - dt)
        diff = self.spd * (1 + 0.06 * (self.wave - 1))
        # player
        if self.dead_t is None:
            d = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
            self.px = max(10, min(W - 10, self.px + d * 130 * dt))
            limit = 3 if self.wingman > 0 else 2
            if inp.hit("a") and len(self.shots) < limit:
                self.shots.append([self.px, PY])
                if self.wingman > 0:
                    self.shots.append([self.px + 14, PY + 4])
                au.play("shoot")
        else:
            self.dead_t -= dt
            if self.dead_t <= 0:
                if self.lives <= 0:
                    self.end_game(False, f"WAVE {self.wave}")
                    return
                self.dead_t = None
                self.inv = 2.5
                self.px = W / 2
        for sh in self.shots:
            sh[1] -= 270 * dt
        self.shots = [s for s in self.shots if s[1] > -8]
        # enemies
        for e in self.enemies:
            self.update_enemy(e, dt, diff)
        # dives
        if not self.bonus and self.wave_t > 6:
            self.dive_t -= dt
            if self.dive_t <= 0:
                self.dive_t = max(0.5, (2.4 - self.wave * 0.12)) / self.spd * random.uniform(0.7, 1.3)
                self.launch_dive()
        # bullets
        for b in self.bullets:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
        self.bullets = [b for b in self.bullets if -10 < b[1] < H + 10]
        for it in self.items:
            it[1] += 45 * dt
        self.collide(au)
        self.items = [i for i in self.items if i[1] < H + 10 and not i[2]]
        self.enemies = [e for e in self.enemies if e.alive]
        if self.score >= self.next_extra:
            self.lives += 1
            self.next_extra += 50000
            au.play("extra")
            self.floats.add(self.px, PY - 14, "1UP!", "mint")
        if not self.enemies and self.ending is None:
            if self.bonus:
                pts = 10000 if self.bonus_hits >= 40 else self.bonus_hits * 100
                self.add(pts, W // 2, 100, "mint")
                self.floats.add(W // 2, 86, f"BONUS {self.bonus_hits} HITS", "yellow")
                au.play("win" if self.bonus_hits >= 40 else "levelup")
            else:
                au.play("levelup")
            self.wave += 1
            self.start_wave()

    def update_enemy(self, e, dt, diff):
        e.t += dt
        e.hit_flash = max(0.0, e.hit_flash - dt)
        if e.state == "enter":
            if e.t < e.delay:
                return
            if e.path is None:
                sx = -20 if e.side < 0 else W + 20
                e.path = [(sx, 60), (W / 2 - e.side * 70, 190), (W / 2 + e.side * 90, 40), None]
            u = min(1.0, (e.t - e.delay) / e.dur)
            p = e.path[:3] + [self.slot(e)]
            e.x, e.y = bezier(p, u)
            if u >= 1:
                e.state = "form"
        elif e.state == "form":
            e.x, e.y = self.slot(e)
        elif e.state == "parade":
            if e.t < e.delay:
                e.x = -50
                return
            u = (e.t - e.delay) / e.dur
            if u >= 1:
                e.alive = False
                return
            e.x, e.y = bezier(e.path, u)
        elif e.state == "dive":
            u = (e.t) / e.dur
            if u >= 1:
                e.state, e.t = "return", 0.0
                e.path = [(e.x, -16), (e.x, 20), None, None]
                return
            e.x, e.y = bezier(e.path, u)
            for st in e.shots:
                if not st[1] and u >= st[0]:
                    st[1] = True
                    ang = math.atan2(PY - e.y, self.px - e.x)
                    sp = 105 * diff
                    self.bullets.append([e.x, e.y + 6, math.cos(ang) * sp * 0.45, abs(math.sin(ang)) * sp + 30])
        elif e.state == "return":
            u = min(1.0, e.t / 1.2)
            sx, sy = self.slot(e)
            e.x, e.y = bezier([e.path[0], e.path[1], (sx, sy - 20), (sx, sy)], u)
            if u >= 1:
                e.state = "form"

    def launch_dive(self):
        ready = [e for e in self.enemies if e.state == "form"]
        if not ready:
            return
        e = random.choice(ready)
        group = [e]
        if e.kind == 2:
            group += [o for o in ready if o.kind == 1 and o.row == 1 and abs(o.col - e.col) <= 1][:2]
        side = 1 if e.x < W / 2 else -1
        for i, g in enumerate(group):
            g.state, g.t = "dive", 0.0
            g.dur = random.uniform(2.3, 2.9) / max(0.7, self.spd)
            off = (i - (len(group) - 1) / 2) * 16
            g.path = [(g.x, g.y), (g.x + side * 70, g.y - 20), (self.px + off - side * 40, 150),
                      (self.px + off + side * 30, H + 24)]
            n = 1 + (random.random() < 0.3 + self.wave * 0.04)
            g.shots = [[random.uniform(0.15, 0.55), False] for _ in range(n)]
        self.app.audio.play("move")

    def collide(self, au):
        for sh in self.shots[:]:
            r = pygame.Rect(int(sh[0]) - 2, int(sh[1]) - 3, 5, 7)
            for e in self.enemies:
                if e.alive and e.state != "enter" or (e.alive and e.state == "enter" and e.t > e.delay):
                    if e.rect().colliderect(r):
                        if sh in self.shots:
                            self.shots.remove(sh)
                        self.hit_enemy(e, au)
                        break
        if self.dead_t is not None:
            return
        pr = pygame.Rect(int(self.px) - 6, PY + 3, 12, 11)
        if self.inv <= 0:
            for b in self.bullets:
                if pr.collidepoint(b[0], b[1]):
                    self.kill_player(au)
                    b[1] = H + 99
                    return
            for e in self.enemies:
                if e.alive and e.state in ("dive", "parade") and e.rect().inflate(-2, -2).colliderect(pr):
                    if e.state == "dive":
                        e.alive = False
                        self.parts.burst(e.x, e.y, 14, ("sky", "white", "pink"), 70, 0.6)
                    self.kill_player(au)
                    return
        for it in self.items:
            if pr.collidepoint(it[0], it[1]):
                it[2] = True
                self.wingman = 20.0
                self.add(1000, self.px, PY - 10, "mint")
                au.play("powerup")

    def hit_enemy(self, e, au):
        e.hp -= 1
        if e.hp > 0:
            e.hit_flash = 0.3
            au.play("tin")
            return
        e.alive = False
        diving = e.state in ("dive", "return")
        pts = POINTS[e.kind][1 if diving else 0]
        if e.state == "parade":
            self.bonus_hits += 1
            pts = 100
        self.add(pts, e.x, e.y - 8, "yellow" if not diving else "mint")
        colors = {0: ("sky", "white", "blue"), 1: ("pink", "hotpink", "white"), 2: ("purple", "yellow", "white")}[e.kind]
        self.parts.burst(e.x, e.y, 16, colors, 80, 0.6)
        au.play("explode")
        if e.kind == 2 and diving and random.random() < 0.35 and self.wingman <= 0:
            self.items.append([e.x, e.y, False])

    def kill_player(self, au):
        self.lives -= 1
        self.dead_t = 1.6
        self.wingman = 0.0
        self.shots.clear()
        au.play("boom")
        self.app.shake(4, 0.4)
        self.parts.burst(self.px, PY + 8, 30, ("orange", "yellow", "white", "pink"), 110, 1.0)

    # ---------------------------------------------------------------- draw
    def render(self, s):
        s.fill(col("night"))
        self.stars.draw(s, self.t)
        for it in self.items:
            img = sprite("star")
            s.blit(img, (int(it[0]) - 3, int(it[1]) - 3))
            if int(self.t * 10) % 2:
                s.fill(col("white"), (int(it[0]), int(it[1]) - 6, 1, 2))
        for e in self.enemies:
            if e.state == "enter" and e.t < e.delay:
                continue
            w, h = e.size()
            cute.space_jelly(s, int(e.x) - w // 2, int(e.y) - h // 2, self.t + e.col, e.kind, hit=e.hit_flash > 0 or e.hp < 2 and e.kind == 2 and int(self.t * 6) % 2 == 0)
        for sh in self.shots:
            x, y = int(sh[0]), int(sh[1])
            s.fill(col("yellow"), (x - 1, y - 3, 3, 6))
            s.fill(col("white"), (x, y - 3, 1, 3))
        for b in self.bullets:
            pygame.draw.circle(s, col("pink"), (int(b[0]), int(b[1])), 2)
            s.fill(col("white"), (int(b[0]) - 1, int(b[1]) - 1, 1, 1))
        if self.dead_t is None and (self.inv <= 0 or int(self.inv * 12) % 2 == 0):
            bob = int(math.sin(self.t * 5) * 1)
            s.blit(sprite("kitty"), (int(self.px) - 8, PY + bob))
            flame = int(self.t * 20) % 2
            s.fill(col("orange" if flame else "yellow"), (int(self.px) - 2, PY + 16 + bob, 4, 2 + flame))
            if self.wingman > 0 and (self.wingman > 3 or int(self.t * 8) % 2):
                img = sprite("star")
                s.blit(img, (int(self.px) + 11, PY + 6 + int(math.sin(self.t * 6) * 2)))
        self.parts.draw(s)
        self.floats.draw(s)
        draw_text(s, f"{self.score:07d}", 4, 2, "white", shadow=None)
        draw_text(s, f"HI {max(self.best, self.score):07d}", W // 2, 2, "lavender", align="center", shadow=None)
        draw_text(s, f"WAVE {self.wave}", W - 4, 2, "yellow", align="right", shadow=None)
        for i in range(min(self.lives, 6)):
            s.blit(sprite("heart"), (4 + i * 8, H - 8))
        if self.banner_t > 0:
            if self.bonus:
                self.banner(s, "BONUS PARADE!", "SHOOT THEM ALL", "mint")
            else:
                self.banner(s, f"WAVE {self.wave}", "GET READY!")


def preview(s, t):
    s.fill(col("night"))
    w, h = s.get_size()
    st = Stars(25, seed=2)
    st.update(t, 15)
    st.draw(s, t)
    for i in range(5):
        cute.space_jelly(s, 6 + i * 18 + int(math.sin(t + i) * 3), 6 + (i % 2) * 12, t, i % 2)
    cute.space_jelly(s, w // 2 - 8, 30 + int(math.sin(t * 2) * 6), t, 2)
    s.blit(sprite("kitty"), (w // 2 - 8 + int(math.sin(t * 1.5) * 20), h - 18))
    s.fill(col("yellow"), (w // 2 + int(math.sin(t * 1.5) * 20), h - 30 - int(t * 60) % 20, 2, 4))
