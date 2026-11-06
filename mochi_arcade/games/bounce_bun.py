"""BOUNCE BUN - a brick-breaking game with a bun paddle and snack bricks (original game)."""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.gfx import H, W, col, draw_text, render_text

LEFT, RIGHT, TOP = 8, W - 8, 20
BRW, BRH = 16, 8
BX0, BY0 = 16, 30
PADDLE_Y = 182
KIND = {"c": "cookie", "p": "candy", "m": "mint", "l": "lemon", "b": "berry", "h": "choco", "t": "tin"}
POINTS = {"cookie": 50, "candy": 60, "mint": 70, "lemon": 80, "berry": 90, "choco": 120, "tin": 0}

LEVELS = [
    ("COOKIE JAR", ["..................", ".cccccccccccccccc.", ".pppppppppppppppp.", ".llllllllllllllll.",
                    ".mmmmmmmmmmmmmmmm.", ".bbbbbbbbbbbbbbbb."]),
    ("SWEETHEART", ["...ppp......ppp...", "..ppppp....ppppp..", ".pppppppp.ppppppp.", ".pppppppppppppppp.",
                    "..pppppppppppppp..", "...pppppppppppp...", "....pppppppppp....", ".....pppppppp.....",
                    "......pppppp......", ".......pppp......."]),
    ("KITTY CAKE", ["..h............h..", ".hhh..........hhh.", ".hhhhhhhhhhhhhhhh.", ".hcccccccccccccch.",
                    ".hccbbccccccbbcch.", ".hcccccccccccccch.", ".hccccccppcccccch.", ".hcccpccccccpccch.",
                    ".hhhhhhhhhhhhhhhh."]),
    ("TIN FORT", ["tttt..........tttt", "tllt..........tllt", "tllt.mmmmmmmm.tllt", "tttt.mbbbbbbm.tttt",
                  ".....mbhhhhbm.....", ".....mbbbbbbm.....", ".....mmmmmmmm.....", "..................",
                  "...tttt....tttt..."]),
    ("RAINBOW", ["p.................", "pl................", "plm...............", "plmb..............",
                 "plmbc.............", ".lmbcp............", "..mbcpl...........", "...bcplm..........",
                 "....cplmb.........", ".....plmbcplmbcplm"]),
    ("MOCHI FACE", [".....cccccccc.....", "...cccccccccccc...", "..cccccccccccccc..", ".cccbbcccccccbbccc",
                    ".cccbbcccccccbbccc", ".ccpccccccccccpccc", ".ccccccchhccccccc.", "..cccccccccccccc..",
                    "...cccccccccccc..."]),
    ("CHECKERS", ["h.h.h.h.h.h.h.h.h.", ".l.l.l.l.l.l.l.l.l", "m.m.m.m.m.m.m.m.m.", ".b.b.b.b.b.b.b.b.b",
                  "p.p.p.p.p.p.p.p.p.", ".h.h.h.h.h.h.h.h.h", "c.c.c.c.c.c.c.c.c."]),
    ("CANDY VAULT", ["tttttttttttttttttt", "t................t", "t.hhhhhhhhhhhhhh.t", "t.hpppppppppppph.t",
                     "t.hpllllllllllph.t", "t.hpppppppppppph.t", "t.hhhhhhhhhhhhhh.t", "t................t",
                     "tttttt......tttttt"]),
]


class Ball:
    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.stuck = None  # x offset from paddle centre while glued


class BounceBun(GameScene):
    music = "bounce"

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES[d]
        self.base_speed = 125 * SPEED[d]
        self.level = int(opt.get("level", 1))
        self.px = W / 2
        self.timers = {"wide": 0.0, "slow": 0.0, "glue": 0.0}
        self.load_level()

    def load_level(self):
        name, rows = LEVELS[(self.level - 1) % len(LEVELS)]
        self.level_name = name
        self.loop = (self.level - 1) // len(LEVELS)
        self.bricks = []
        for r, row in enumerate(rows):
            for c, ch in enumerate((row + "." * 18)[:18]):
                if ch in KIND:
                    kind = KIND[ch]
                    self.bricks.append({"rect": pygame.Rect(BX0 + c * BRW, BY0 + r * BRH, BRW, BRH), "kind": kind,
                                        "hp": 2 if kind == "choco" else 1, "flash": 0.0})
        self.caps = []
        self.speed = self.base_speed * (1 + 0.12 * self.loop)
        self.reset_ball()
        self.intro = 1.5

    def reset_ball(self):
        self.balls = [Ball(self.px, PADDLE_Y - 4, 0, 0)]
        self.balls[0].stuck = 0
        self.timers = {k: 0.0 for k in self.timers}

    def pw(self):
        return 48 if self.timers["wide"] > 0 else 32

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        inp, au = self.app.input, self.app.audio
        self.intro = max(0.0, self.intro - dt)
        for k in self.timers:
            self.timers[k] = max(0.0, self.timers[k] - dt)
        d = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        half = self.pw() / 2
        self.px = max(LEFT + half, min(RIGHT - half, self.px + d * 170 * dt))
        for b in self.balls:
            if b.stuck is not None:
                b.x, b.y = self.px + b.stuck, PADDLE_Y - 4
                if inp.hit("a") and self.intro <= 0:
                    ang = math.radians(-20 + (b.stuck / half) * 40 if half else 0)
                    sp = self.cur_speed()
                    b.vx, b.vy = math.sin(ang) * sp, -math.cos(ang) * sp
                    b.stuck = None
                    au.play("paddle")
        for b in self.balls:
            if b.stuck is None:
                self.move_ball(b, dt, au)
        lost = [b for b in self.balls if b.y > H + 6]
        if lost:
            self.balls = [b for b in self.balls if b.y <= H + 6]
            if not self.balls:
                self.lives -= 1
                au.play("hurt")
                self.app.shake(3, 0.3)
                if self.lives <= 0:
                    self.end_game(False, f"LEVEL {self.level}")
                    return
                self.reset_ball()
        for cap in self.caps:
            cap["y"] += 55 * dt
            if PADDLE_Y - 2 <= cap["y"] <= PADDLE_Y + 6 and abs(cap["x"] - self.px) < self.pw() / 2 + 6:
                cap["got"] = True
                self.power(cap["k"], au)
        self.caps = [c for c in self.caps if not c.get("got") and c["y"] < H + 8]
        for br in self.bricks:
            br["flash"] = max(0.0, br["flash"] - dt)
        if not any(br["kind"] != "tin" for br in self.bricks):
            au.play("levelup")
            self.add(2000, W // 2, 100, "mint")
            self.level += 1
            self.load_level()

    def cur_speed(self):
        return self.speed * (0.65 if self.timers["slow"] > 0 else 1.0)

    def move_ball(self, b, dt, au):
        sp = math.hypot(b.vx, b.vy) or 1
        target = self.cur_speed()
        b.vx, b.vy = b.vx / sp * target, b.vy / sp * target
        steps = max(1, int(target * dt / 3) + 1)
        for _ in range(steps):
            b.x += b.vx * dt / steps
            b.y += b.vy * dt / steps
            if b.x < LEFT + 2:
                b.x, b.vx = LEFT + 2, abs(b.vx)
                au.play("tin")
            elif b.x > RIGHT - 2:
                b.x, b.vx = RIGHT - 2, -abs(b.vx)
                au.play("tin")
            if b.y < TOP + 2:
                b.y, b.vy = TOP + 2, abs(b.vy)
                au.play("tin")
            half = self.pw() / 2
            if b.vy > 0 and PADDLE_Y - 2 <= b.y + 2 <= PADDLE_Y + 4 and abs(b.x - self.px) <= half + 2:
                off = max(-1.0, min(1.0, (b.x - self.px) / half))
                ang = math.radians(off * 60)
                b.vx, b.vy = math.sin(ang) * target, -math.cos(ang) * target
                b.y = PADDLE_Y - 3
                au.play("paddle")
                if self.timers["glue"] > 0:
                    b.stuck = b.x - self.px
                    return
            br_hit = None
            ball = pygame.Rect(int(b.x) - 2, int(b.y) - 2, 5, 5)
            for br in self.bricks:
                if br["rect"].colliderect(ball):
                    br_hit = br
                    break
            if br_hit:
                r = br_hit["rect"]
                ox = min(ball.right - r.left, r.right - ball.left)
                oy = min(ball.bottom - r.top, r.bottom - ball.top)
                if ox < oy:
                    b.vx = -b.vx
                    b.x += math.copysign(ox + 0.5, b.vx)
                else:
                    b.vy = -b.vy
                    b.y += math.copysign(oy + 0.5, b.vy)
                self.hit_brick(br_hit, au)

    def hit_brick(self, br, au):
        if br["kind"] == "tin":
            br["flash"] = 0.15
            au.play("tin")
            return
        br["hp"] -= 1
        if br["hp"] > 0:
            br["flash"] = 0.2
            au.play("tin")
            return
        self.bricks.remove(br)
        r = br["rect"]
        self.add(POINTS[br["kind"]] * (1 + self.loop))
        self.speed = min(self.base_speed * 1.8, self.speed + 1.5)
        au.play("brick")
        colors = {"cookie": ("peach", "brown"), "candy": ("pink", "white"), "mint": ("mint", "white"),
                  "lemon": ("yellow", "white"), "berry": ("lavender", "purple"), "choco": ("brown", "choco")}
        self.parts.burst(r.centerx, r.centery, 8, colors[br["kind"]], 50, 0.5)
        roll = random.random()
        if roll < 0.025:
            self.caps.append({"x": r.centerx, "y": r.centery, "k": "+"})
        elif roll < 0.14:
            self.caps.append({"x": r.centerx, "y": r.centery, "k": random.choice("WMSG")})

    def power(self, k, au):
        au.play("powerup")
        name = {"W": "WIDE BUN!", "M": "MULTI BALL!", "S": "SLOW DOWN", "G": "STICKY GLUE", "+": "EXTRA LIFE!"}[k]
        self.floats.add(self.px, PADDLE_Y - 12, name, "mint")
        if k == "W":
            self.timers["wide"] = 15
        elif k == "S":
            self.timers["slow"] = 10
        elif k == "G":
            self.timers["glue"] = 12
        elif k == "+":
            self.lives += 1
            au.play("extra")
        elif k == "M":
            src = [b for b in self.balls if b.stuck is None] or self.balls
            b0 = src[0]
            for a in (-25, 25):
                ang = math.atan2(b0.vx, -b0.vy) + math.radians(a) if (b0.vx or b0.vy) else math.radians(a)
                sp = self.cur_speed()
                self.balls.append(Ball(b0.x, b0.y, math.sin(ang) * sp, -abs(math.cos(ang) * sp)))
        self.add(100)

    # ---------------------------------------------------------------- draw
    def render(self, s):
        s.fill(col("choco"))
        for y in range(TOP, H, 12):
            for x in range(0, W, 12):
                if (x // 12 + y // 12) % 2:
                    s.fill(col("brown"), (x, y, 12, 12))
        s.fill(col("black"), (0, 0, W, TOP))
        s.fill(col("peach"), (0, TOP, LEFT, H))
        s.fill(col("peach"), (RIGHT, TOP, W - RIGHT, H))
        s.fill(col("cream"), (0, TOP - 2, W, 2))
        for br in self.bricks:
            r = br["rect"]
            if br["flash"] > 0:
                s.fill(col("white"), r)
            else:
                cute.brick(s, r, br["kind"], br["hp"], self.t)
        for cap in self.caps:
            x, y = int(cap["x"]), int(cap["y"])
            c = {"W": "sky", "M": "pink", "S": "mint", "G": "yellow", "+": "red"}[cap["k"]]
            pygame.draw.rect(s, col("black"), (x - 7, y - 4, 14, 8), border_radius=3)
            pygame.draw.rect(s, col(c), (x - 6, y - 3, 12, 6), border_radius=3)
            s.blit(render_text(cap["k"], "black"), (x - 2, y - 3))
        # the bun paddle
        w = self.pw()
        r = pygame.Rect(int(self.px - w / 2), PADDLE_Y, int(w), 7)
        pygame.draw.rect(s, col("black"), r.inflate(2, 2), border_radius=4)
        pygame.draw.rect(s, col("peach" if self.timers["glue"] <= 0 else "yellow"), r, border_radius=4)
        s.fill(col("cream"), (r.x + 3, r.y + 1, r.w - 6, 2))
        for i in range(3):
            s.fill(col("choco"), (r.x + 6 + i * (r.w - 12) // 2, r.y + 3, 2, 1))
        cute.eyes(s, r.centerx, r.y + 3, 3, 0, "happy", blink=int(self.t * 1.2) % 5 == 0)
        for b in self.balls:
            pygame.draw.circle(s, col("black"), (int(b.x), int(b.y)), 3)
            pygame.draw.circle(s, col("hotpink"), (int(b.x), int(b.y)), 2)
            s.fill(col("white"), (int(b.x) - 1, int(b.y) - 1, 1, 1))
        self.parts.draw(s)
        self.floats.draw(s)
        draw_text(s, f"{self.score:07d}", 4, 6, "white", shadow=None)
        draw_text(s, f"LEVEL {self.level}", W // 2, 6, "yellow", align="center", shadow=None)
        self.hearts(s, W - 54, 6, self.lives)
        if self.intro > 0:
            self.banner(s, f"LEVEL {self.level}", self.level_name, "peach")
        elif any(b.stuck is not None for b in self.balls) and int(self.t * 3) % 2:
            draw_text(s, "PRESS Z TO LAUNCH", W // 2, 160, "white", align="center")


def preview(s, t):
    s.fill(col("choco"))
    w, h = s.get_size()
    kinds = ["cookie", "candy", "mint", "lemon", "berry"]
    for r in range(4):
        for c in range(w // 16):
            if (r + c + int(t)) % 7:
                cute.brick(s, (c * 16, 4 + r * 8, 16, 8), kinds[(r + c) % 5])
    bx = w / 2 + math.sin(t * 2) * 30
    by = h - 20 - abs(math.sin(t * 3)) * 26
    pygame.draw.circle(s, col("hotpink"), (int(bx), int(by)), 2)
    pygame.draw.rect(s, col("peach"), (int(w / 2 + math.sin(t * 2) * 25) - 14, h - 10, 28, 5), border_radius=3)
