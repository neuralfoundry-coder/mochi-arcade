"""NOODLE SLURP - a snake-style game: a hungry noodle slurps up dumplings (original game)."""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.games.base import GameScene
from mochi_arcade.gfx import H, W, col, draw_text, panel

GW, GH, C = 32, 20, 8
OX, OY = (W - GW * C) // 2, 26
DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
STEP = {"slow": 0.16, "normal": 0.115, "fast": 0.08}


def maze(n):
    walls = set()
    def hline(y, x0, x1):
        walls.update((x, y) for x in range(x0, x1 + 1))
    def vline(x, y0, y1):
        walls.update((x, y) for y in range(y0, y1 + 1))
    k = n % 4
    if k == 1:
        hline(6, 6, 25); hline(13, 6, 25)
    elif k == 2:
        for (x, y, dx, dy) in ((4, 3, 1, 1), (27, 3, -1, 1), (4, 16, 1, -1), (27, 16, -1, -1)):
            hline(y, min(x, x + dx * 6), max(x, x + dx * 6)); vline(x, min(y, y + dy * 4), max(y, y + dy * 4))
        hline(9, 13, 18); hline(10, 13, 18)
    elif k == 3:
        vline(15, 2, 7); vline(16, 2, 7); vline(15, 12, 17); vline(16, 12, 17)
        hline(9, 3, 11); hline(10, 3, 11); hline(9, 20, 28); hline(10, 20, 28)
    else:
        for x in (8, 23):
            vline(x, 4, 15)
        hline(4, 12, 19); hline(15, 12, 19)
    return walls


class NoodleSlurp(GameScene):
    music = "noodle"

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        self.mode = opt.get("mode", "classic")
        self.base_step = STEP[opt.get("speed", "normal")]
        self.maze_n = 1
        self.reset_level()

    def reset_level(self):
        self.walls = maze(self.maze_n) if self.mode == "maze" else set()
        y = GH // 2 + (3 if self.mode == "maze" and self.maze_n % 4 == 1 else 0)
        y = min(GH - 2, y)
        self.body = [(8 - i, y) for i in range(4)]
        self.dir = (1, 0)
        self.queue = []
        self.grow = 0
        self.step_t = 0.0
        self.eaten = 0
        self.level_eaten = 0
        self.food = self.free_cell()
        self.gold = None
        self.gold_t = 0.0
        self.slurp = 0.0
        self.dead = False
        self.intro = 1.2

    def free_cell(self):
        occupied = set(self.body) | self.walls
        for _ in range(500):
            p = (random.randrange(GW), random.randrange(GH))
            if p not in occupied and (getattr(self, "food", None) != p):
                return p
        return (0, 0)

    def step_time(self):
        return max(0.05, self.base_step - self.eaten * 0.0015)

    def tick(self, dt):
        inp, au = self.app.input, self.app.audio
        self.slurp = max(0.0, self.slurp - dt)
        if self.intro > 0:
            self.intro -= dt
        for name, d in DIRS.items():
            if inp.hit(name) and len(self.queue) < 3:
                last = self.queue[-1] if self.queue else self.dir
                if d != last and d != (-last[0], -last[1]):
                    self.queue.append(d)
        if self.gold:
            self.gold_t -= dt
            if self.gold_t <= 0:
                self.gold = None
        if self.intro > 0 or self.dead:
            return
        self.step_t += dt
        while self.step_t >= self.step_time() and not self.dead:
            self.step_t -= self.step_time()
            self.advance(au)

    def advance(self, au):
        if self.queue:
            self.dir = self.queue.pop(0)
        hx, hy = self.body[0]
        nx, ny = hx + self.dir[0], hy + self.dir[1]
        if self.mode != "classic" and self.mode != "maze":
            nx %= GW
            ny %= GH
        elif self.mode == "maze":
            nx %= GW
            ny %= GH
        hit = not (0 <= nx < GW and 0 <= ny < GH) or (nx, ny) in self.walls or (nx, ny) in self.body[:-1]
        if hit:
            self.dead = True
            au.play("hurt")
            self.app.shake(3, 0.3)
            for (x, y) in self.body:
                self.parts.burst(OX + x * C + 4, OY + y * C + 4, 2, ("cream", "peach", "white"), 50, 0.8)
            self.end_game(False, f"LENGTH {len(self.body)}", delay=1.8)
            return
        self.body.insert(0, (nx, ny))
        if self.grow > 0:
            self.grow -= 1
        else:
            self.body.pop()
        if (nx, ny) == self.food:
            self.eaten += 1
            self.level_eaten += 1
            self.grow += 2
            self.slurp = 0.25
            self.add(10 + 5 * self.maze_n, OX + nx * C + 4, OY + ny * C - 4)
            au.play("eat")
            self.food = self.free_cell()
            if self.eaten % 5 == 0 and not self.gold:
                self.gold = self.free_cell()
                self.gold_t = 6.0
                au.play("bonus")
            if self.mode == "maze" and self.level_eaten >= 12:
                self.maze_n += 1
                au.play("levelup")
                self.add(1000, W // 2, 100, "mint")
                keep = self.eaten
                self.reset_level()
                self.eaten = keep
        elif self.gold and (nx, ny) == self.gold:
            self.gold = None
            self.grow += 4
            self.slurp = 0.4
            self.add(500, OX + nx * C + 4, OY + ny * C - 4, "mint")
            au.play("bonus")
            self.parts.burst(OX + nx * C + 4, OY + ny * C + 4, 14, ("yellow", "white", "orange"), 60, 0.7)

    # ---------------------------------------------------------------- draw
    def render(self, s):
        s.fill(col("choco"))
        panel(s, (OX - 3, OY - 3, GW * C + 6, GH * C + 6), fill="cream", border="brown", radius=3)
        for y in range(GH):
            for x in range(GW):
                if (x // 2 + y // 2) % 2 == 0:
                    s.fill(col("peach"), (OX + x * C, OY + y * C, C, C))
        for (x, y) in self.walls:
            r = (OX + x * C, OY + y * C, C, C)
            s.fill(col("brown"), r)
            s.fill(col("choco"), (r[0] + 1, r[1] + 1, C - 2, C - 2))
        fx, fy = self.food
        cute.dumpling(s, OX + fx * C, OY + fy * C - int(abs(math.sin(self.t * 5)) * 1), t=self.t)
        if self.gold and (self.gold_t > 1.5 or int(self.t * 10) % 2):
            gx, gy = self.gold
            cute.dumpling(s, OX + gx * C, OY + gy * C, golden=True, t=self.t)
        self.draw_noodle(s)
        self.parts.draw(s)
        self.floats.draw(s)
        draw_text(s, f"SCORE {self.score}", 6, 8, "white")
        draw_text(s, f"BEST {max(self.best, self.score)}", W // 2, 8, "cream", align="center")
        mode = {"classic": "CLASSIC", "wrap": "WRAP", "maze": f"MAZE {self.maze_n}"}[self.mode]
        draw_text(s, mode, W - 6, 8, "yellow", align="right")
        if self.mode == "maze":
            draw_text(s, f"{12 - self.level_eaten} TO NEXT", W // 2, H - 10, "cream", align="center")
        if self.intro > 0 and not self.dead:
            self.banner(s, "READY?", "SLURP!", "peach")

    def draw_noodle(self, s):
        body = self.body
        n = len(body)
        cream, peach, k = col("cream"), col("orange"), col("black")
        pts = [(OX + x * C + 4, OY + y * C + 4) for x, y in body]
        for i in range(n - 1, 0, -1):
            a, b = pts[i], pts[i - 1]
            if abs(a[0] - b[0]) > C or abs(a[1] - b[1]) > C:  # wrapped around the edge
                continue
            pygame.draw.line(s, k, a, b, 7)
        for i in range(n - 1, -1, -1):
            r = 3 if i < n - 2 else 2
            pygame.draw.circle(s, k, pts[i], r + 1)
        for i in range(n - 1, 0, -1):
            a, b = pts[i], pts[i - 1]
            if abs(a[0] - b[0]) > C or abs(a[1] - b[1]) > C:
                continue
            pygame.draw.line(s, cream, a, b, 5)
        for i in range(n - 1, -1, -1):
            r = 3 if i < n - 2 else 2
            pygame.draw.circle(s, cream, pts[i], r)
            if i % 3 == 1:
                s.fill(peach, (pts[i][0] - 1, pts[i][1] - 1, 2, 1))
        hx, hy = pts[0]
        dx, dy = self.dir
        head_r = 4 + (1 if self.slurp > 0 else 0)
        pygame.draw.circle(s, k, (hx, hy), head_r + 1)
        pygame.draw.circle(s, cream, (hx, hy), head_r)
        if self.dead:
            cute.eyes(s, hx, hy - 1, 2, 0, "sleepy")
        else:
            cute.eyes(s, hx + dx, hy - 1 + dy, 2, 0, "happy", blink=int(self.t * 1.3) % 6 == 0)
        cute.blush(s, hx, hy + 1, 2)
        if self.slurp > 0:
            pygame.draw.circle(s, col("hotpink"), (hx + dx * 3, hy + dy * 3 + 1), 1)


def preview(s, t):
    s.fill(col("peach"))
    w, h = s.get_size()
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            if (x // 8 + y // 8) % 2:
                s.fill(col("cream"), (x, y, 8, 8))
    pts = [(10 + i * 6, h // 2 + int(math.sin(t * 4 + i * 0.6) * 6)) for i in range(10)]
    for i in range(len(pts) - 1):
        pygame.draw.line(s, col("black"), pts[i], pts[i + 1], 7)
    for i in range(len(pts) - 1):
        pygame.draw.line(s, col("cream"), pts[i], pts[i + 1], 5)
    hx, hy = pts[-1]
    pygame.draw.circle(s, col("black"), (hx, hy), 5)
    pygame.draw.circle(s, col("cream"), (hx, hy), 4)
    cute.eyes(s, hx + 1, hy - 1, 2)
    cute.dumpling(s, w - 22, h // 2 - 4, t=t)
    cute.dumpling(s, w - 40, 10, golden=True, t=t)
