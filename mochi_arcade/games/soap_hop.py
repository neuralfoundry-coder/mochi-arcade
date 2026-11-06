"""SOAP HOP - a single-screen bubble platformer starring Momo the mochi bunny (original game)."""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.gfx import H, W, bubble, col, draw_text, lerp_col, sprite

T = 8
COLS, ROWS = 40, 23
TOP = 12
FIELD_H = ROWS * T
GRAV = 620.0
JUMP = 255.0
RUN = 74.0
FAST_PHASE = 0.32

# themes: block, block shadow, platform, platform shadow, sky top, sky bottom
THEMES = [("pink", "hotpink", "cream", "peach", "deep", "night"), ("mint", "teal", "cream", "lime", "deep", "night"),
          ("hotpink", "purple", "pink", "hotpink", "ink", "night"), ("sky", "blue", "white", "sky", "deep", "night"),
          ("yellow", "orange", "cream", "yellow", "ink", "night"), ("lavender", "purple", "white", "lavender", "deep", "night"),
          ("teal", "blue", "mint", "teal", "ink", "night"), ("peach", "orange", "yellow", "orange", "deep", "night")]

# 20 inner rows (36 wide, right-padded with '.'); rows 0 and 21-22 are the ceiling and floor.
LEVELS = [
    {"name": "HELLO SUDS", "rows": {
        5: "......g................g", 6: "....==========........==========", 10: "...............f",
        11: "..........================", 15: "......g................g",
        16: "....==========........==========", 20: "................P"}},
    {"name": "BUBBLE STAIRS", "rows": {
        3: "..f......................f", 5: "......................g", 6: "....................==========",
        9: "..............g", 10: "............=========", 13: "....g", 14: "..=========",
        17: "=====.........................=====", 20: "..........P"}},
    {"name": "FOAMY HEART", "rows": {
        4: "..........g........g", 5: "........======....======", 7: "......f...............f",
        8: "......======..........======", 10: "..........g", 11: "........======......======",
        13: "...............g", 14: "...........=====..=====", 17: ".............==========", 20: ".................P"}},
    {"name": "PILLAR PARK", "gap": (15, 20), "rows": {
        4: "....g.............g...........g", 5: "..========....==========....======",
        8: "........##................##", 9: "........##.......f........##", 10: "........##....========....##",
        11: "........##................##", 12: "........##................##", 13: "...g....##................##...g",
        14: "========##................##======", 15: "........##........g.......##",
        16: "........##...==========...##", 17: "........##................##", 18: "........##................##",
        19: "........##................##", 20: "...P....##................##"}},
    {"name": "ZIGZAG ZOOM", "rows": {
        4: "..g.................f", 5: "========================", 8: "...........................g",
        9: "............========================", 12: "..g...........f", 13: "========================",
        16: "..........................g", 17: "............========================", 20: "..P"}},
    {"name": "POLKA PUFFS", "rows": {
        4: "....g.......f.......g.......f", 5: "...====....====....====....====",
        8: "........f.......g", 9: ".......====....====....====", 12: "....g..............f",
        13: "...====....====....====....====", 16: "........g.......g", 17: ".......====....====....====",
        20: ".................P"}},
    {"name": "BUBBLE BATH", "rows": {
        4: "...g.......................g", 5: "..=======..............=======", 8: "...........f.........f",
        9: "..........==============", 11: "......##................##", 12: "......##.......g........##",
        13: "......##................##", 14: "......####################", 17: "=====.....................=====",
        20: ".................P"}},
    {"name": "MOCHI SMILE", "rows": {
        2: "..........g............g", 3: "........=======.......=======", 6: "....f..........................f",
        7: "...=====...................=====", 9: "................g", 10: "..............========",
        12: "......g..................g", 13: ".....=====..............=====", 15: ".................f",
        16: ".........==================", 20: ".................P"}},
]


def build(level):
    gap = level.get("gap")
    def edge():
        r = list("#" * COLS)
        if gap:
            for c in range(gap[0] + 2, gap[1] + 3):
                r[c] = "."
        return "".join(r)
    m = [edge()]
    for i in range(1, 21):
        inner = (level["rows"].get(i, "") + "." * 36)[:36]
        m.append("##" + inner + "##")
    m += [edge(), edge()]
    return m


class Body:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = float(x), float(y), w, h
        self.vx = self.vy = 0.0
        self.on_ground = False

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)


class Enemy(Body):
    def __init__(self, kind, x, y, speed):
        super().__init__(x, y, 12, 13)
        self.kind, self.base = kind, speed
        self.face = random.choice((-1, 1))
        self.vdir = random.choice((-1, 1))
        self.angry = False
        self.think = random.uniform(0.5, 1.5)


class Bubble:
    def __init__(self, x, y, face, life):
        self.x, self.y = x, y
        self.vx = face * 230.0
        self.age = 0.0
        self.life = life
        self.enemy = None
        self.seed = random.uniform(0, 6.28)
        self.pop_in = None


class Fruit(Body):
    def __init__(self, x, y, kind, value):
        super().__init__(x, y, 8, 8)
        self.kind, self.value = kind, value
        self.vx = random.uniform(-40, 40)
        self.vy = -140
        self.life = 9.0


class SoapHop(GameScene):
    music = "soap"

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES[d]
        self.spd = SPEED[d]
        self.trap_time = {"easy": 9.0, "normal": 7.0, "hard": 5.0}[d]
        self.stage = int(opt.get("stage", 1))
        self.load_stage()

    # ---------------------------------------------------------------- level
    def load_stage(self):
        lv = LEVELS[(self.stage - 1) % len(LEVELS)]
        self.loop = (self.stage - 1) // len(LEVELS)
        self.map = build(lv)
        self.level_name = lv["name"]
        self.theme = THEMES[(self.stage - 1) % len(THEMES)]
        self.enemies, self.bubbles, self.fruits = [], [], []
        speed = self.spd * (1 + 0.15 * self.loop)
        for r, row in enumerate(self.map):
            for c, ch in enumerate(row):
                x, y = c * T, TOP + r * T
                if ch == "P":
                    self.start = (x, y + T - 14)
                elif ch in "gf":
                    self.enemies.append(Enemy(ch, x - 2, y + T - 13, speed))
        self.map = [row.replace("P", ".").replace("g", ".").replace("f", ".") for row in self.map]
        self.player = Body(*self.start, 12, 14)
        self.face = 1
        self.inv = 2.0
        self.shoot_cd = 0.0
        self.coyote = self.jump_buf = 0.0
        self.state, self.state_t = "intro", 0.0
        self.level_t = 0.0
        self.hurry = False
        self.chain, self.chain_t = 0, 0.0
        self.field = self.render_field()

    def render_field(self):
        blk, blk_d, plat, plat_d, sky_a, sky_b = self.theme
        f = pygame.Surface((W, FIELD_H), pygame.SRCALPHA)
        for r, row in enumerate(self.map):
            for c, ch in enumerate(row):
                x, y = c * T, r * T
                if ch == "#":
                    f.fill(col(blk_d), (x, y, T, T))
                    f.fill(col(blk), (x, y, T - 1, T - 1))
                    if (r + c) % 2 == 0:
                        f.fill(col("white"), (x + 2, y + 2, 1, 1))
                elif ch == "=":
                    f.fill(col(plat_d), (x, y + 1, T, T - 3))
                    f.fill(col(plat), (x, y, T, 3))
                    f.fill(col("white"), (x + 1, y, 3, 1))
        return f

    def cell(self, px, py):
        c, r = int(px // T), math.floor((py - TOP) / T)
        if r < 0 or r >= ROWS:
            return "."
        if c < 0 or c >= COLS:
            return "#"
        return self.map[r][c]

    # ---------------------------------------------------------------- physics
    def move(self, b, dt, gravity=True):
        if gravity:
            b.vy = min(b.vy + GRAV * dt, 270)
        hit_wall = False
        b.x += b.vx * dt
        for yy in (b.y + 1, b.y + b.h / 2, b.y + b.h - 1):
            if b.vx > 0 and self.cell(b.x + b.w, yy) == "#":
                b.x = (int((b.x + b.w) // T)) * T - b.w - 0.01
                hit_wall = True
            elif b.vx < 0 and self.cell(b.x, yy) == "#":
                b.x = (int(b.x // T) + 1) * T + 0.01
                hit_wall = True
        prev_bottom = b.y + b.h
        b.y += b.vy * dt
        b.on_ground = False
        xs = (b.x + 1, b.x + b.w / 2, b.x + b.w - 1)
        if b.vy >= 0:
            bottom = b.y + b.h
            for xx in xs:
                ch = self.cell(xx, bottom)
                row_top = TOP + math.floor((bottom - TOP) / T) * T
                if ch == "#" or (ch == "=" and prev_bottom <= row_top + 1):
                    b.y = row_top - b.h
                    b.vy = 0
                    b.on_ground = True
                    break
        else:
            for xx in xs:
                if self.cell(xx, b.y) == "#":
                    b.y = TOP + (math.floor((b.y - TOP) / T) + 1) * T
                    b.vy = 0
                    break
        if b.y > TOP + FIELD_H:
            b.y -= FIELD_H
        elif b.y + b.h < TOP:
            b.y += FIELD_H
        return hit_wall

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        inp, au = self.app.input, self.app.audio
        if self.state == "intro" and self.state_t > 1.4:
            self.state, self.state_t = "play", 0.0
        p = self.player
        alive = self.state in ("intro", "play", "clear")
        if alive:
            self.update_player(dt, inp, au)
        if self.state == "dead" and self.state_t > 1.2:
            if self.lives <= 0:
                self.end_game(False, f"STAGE {self.stage}")
                return
            self.player = Body(*self.start, 12, 14)
            self.inv = 2.5
            self.state, self.state_t = "play", 0.0
        if self.state == "play":
            self.level_t += dt
            if self.level_t > 50 and not self.hurry:
                self.hurry = True
                au.play("hurt")
                for e in self.enemies:
                    e.angry = True
        self.update_enemies(dt, p)
        self.update_bubbles(dt, p, au)
        self.update_fruits(dt, p, au)
        self.chain_t -= dt
        if self.state == "play" and not self.enemies and not any(b.enemy for b in self.bubbles):
            self.state, self.state_t = "clear", 0.0
            au.play("levelup")
            bonus = 1000 + max(0, int((60 - self.level_t) * 50))
            self.add(bonus, W // 2, TOP + 70, "mint")
        if self.state == "clear" and self.state_t > 3.0:
            self.stage += 1
            self.load_stage()

    def update_player(self, dt, inp, au):
        p = self.player
        self.inv = max(0.0, self.inv - dt)
        self.shoot_cd -= dt
        move = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        p.vx = move * RUN
        if move:
            self.face = move
        self.coyote = 0.09 if p.on_ground else self.coyote - dt
        self.jump_buf = 0.12 if inp.hit("a") else self.jump_buf - dt
        if self.jump_buf > 0 and self.coyote > 0:
            p.vy = -JUMP
            self.jump_buf = self.coyote = 0
            au.play("jump")
        if p.vy < 0 and not inp.down("a"):
            p.vy *= 0.85
        self.move(p, dt)
        if inp.hit("b") and self.shoot_cd <= 0 and len(self.bubbles) < 7:
            self.shoot_cd = 0.28
            bx = p.cx + self.face * 6
            self.bubbles.append(Bubble(bx, p.cy - 1, self.face, 6.5))
            au.play("bubble")

    def update_enemies(self, dt, p):
        for e in self.enemies:
            sp = e.base * (1.7 if e.angry else 1.0)
            if e.kind == "g":
                e.vx = e.face * 32 * sp
                if self.move(e, dt):
                    e.face *= -1
                if e.on_ground:
                    ahead = self.cell(e.cx + e.face * 8, e.y + e.h + 2)
                    e.think -= dt
                    if ahead == "." and random.random() < 0.5 * dt * 10:
                        e.face *= -1
                    if e.think <= 0:
                        e.think = random.uniform(0.8, 2.0)
                        if p.y + p.h < e.y - 4 and random.random() < 0.55:
                            e.vy = -JUMP * 0.95
                        elif random.random() < 0.25:
                            e.face = 1 if p.cx > e.cx else -1
            else:
                e.vx = e.face * 30 * sp
                e.vy = e.vdir * 22 * sp
                nx, ny = e.x + e.vx * dt, e.y + e.vy * dt
                if self.cell(nx + (e.w if e.vx > 0 else 0), e.cy) == "#":
                    e.face *= -1
                else:
                    e.x = nx
                if self.cell(e.cx, ny + (e.h if e.vy > 0 else 0)) == "#" or ny < TOP + 2 or ny + e.h > TOP + FIELD_H - 2:
                    e.vdir *= -1
                else:
                    e.y = ny
            if self.state == "play" and self.inv <= 0 and e.rect().inflate(-3, -3).colliderect(p.rect()):
                self.hurt()

    def hurt(self):
        self.lives -= 1
        self.state, self.state_t = "dead", 0.0
        self.app.audio.play("hurt")
        self.app.shake(3, 0.3)
        self.parts.burst(self.player.cx, self.player.cy, 20, ("white", "pink", "hotpink"), 80, 0.8)

    def update_bubbles(self, dt, p, au):
        for b in self.bubbles:
            b.age += dt
            b.life -= dt
            if b.pop_in is not None:
                b.pop_in -= dt
                if b.pop_in <= 0:
                    self.pop(b, au)
                continue
            if b.age < FAST_PHASE:
                b.x += b.vx * dt
                b.vx *= 0.92
                if self.cell(b.x + (7 if b.vx > 0 else -7), b.y) == "#":
                    b.age = FAST_PHASE
                if b.enemy is None:
                    for e in self.enemies:
                        if abs(e.cx - b.x) < 11 and abs(e.cy - b.y) < 11:
                            b.enemy = e
                            b.life = self.trap_time
                            self.enemies.remove(e)
                            self.add(50)
                            au.play("trap")
                            break
            else:
                b.y -= (18 if b.enemy else 22) * dt
                b.x += math.sin(self.t * 2 + b.seed) * 8 * dt
                if self.cell(b.x, b.y - 8) == "#":
                    b.y += (18 if b.enemy else 22) * dt
                if b.y < TOP - 8:
                    b.y += FIELD_H
                b.x = max(T * 2 + 8, min(W - T * 2 - 8, b.x))
                if self.state != "dead" and math.hypot(p.cx - b.x, p.cy - b.y) < 12:
                    if p.vy > 0 and p.y + p.h < b.y and self.app.input.down("a"):
                        p.vy = -JUMP * 0.95
                        au.play("jump")
                    else:
                        self.pop(b, au)
            if b.life <= 0 and b in self.bubbles:
                if b.enemy:
                    e = b.enemy
                    e.x, e.y = b.x - e.w / 2, b.y - e.h / 2
                    e.angry = True
                    self.enemies.append(e)
                    b.enemy = None
                self.pop(b, au, quiet=True)
        # keep bubbles from overlapping completely
        for i, a in enumerate(self.bubbles):
            for b2 in self.bubbles[i + 1:]:
                dx, dy = b2.x - a.x, b2.y - a.y
                d = math.hypot(dx, dy)
                if 0 < d < 13 and a.age > FAST_PHASE and b2.age > FAST_PHASE:
                    push = (13 - d) * 0.5
                    a.x -= dx / d * push
                    a.y -= dy / d * push
                    b2.x += dx / d * push
                    b2.y += dy / d * push
        self.bubbles = [b for b in self.bubbles if not getattr(b, "dead", False)]

    def pop(self, b, au, quiet=False):
        if getattr(b, "dead", False):
            return
        b.dead = True
        self.parts.burst(b.x, b.y, 8, ("white", "sky", "lavender"), 50, 0.4)
        if b.enemy:
            self.chain = self.chain + 1 if self.chain_t > 0 else 1
            self.chain_t = 0.5
            pts = min(8000, 500 * 2 ** (self.chain - 1))
            self.add(pts, b.x, b.y - 10, "yellow" if self.chain < 2 else "mint")
            kind = (self.stage - 1) % 8
            self.fruits.append(Fruit(b.x - 4, b.y - 4, kind, 100 * (kind + 1)))
            au.play("pop")
            self.app.shake(1.5, 0.12)
            for o in self.bubbles:
                if o.enemy and o.pop_in is None and not getattr(o, "dead", False) and math.hypot(o.x - b.x, o.y - b.y) < 24:
                    o.pop_in = 0.09
        elif not quiet:
            self.add(10)
            au.play("pop")

    def update_fruits(self, dt, p, au):
        for f in self.fruits:
            f.life -= dt
            f.vx *= 0.98
            self.move(f, dt)
            if f.on_ground:
                f.vx = 0
            if self.state != "dead" and f.rect().colliderect(p.rect()):
                f.life = -1
                self.add(f.value, f.cx, f.y - 6, "peach")
                au.play("fruit")
                self.parts.burst(f.cx, f.cy, 6, ("yellow", "white"), 40, 0.4)
        self.fruits = [f for f in self.fruits if f.life > 0]

    # ---------------------------------------------------------------- draw
    def render(self, s):
        blk, blk_d, plat, plat_d, sky_a, sky_b = self.theme
        for y in range(0, H, 4):
            s.fill(lerp_col(sky_a, sky_b, y / H), (0, y, W, 4))
        for i in range(12):
            x = (i * 53 + self.t * (4 + i % 3)) % W
            y = TOP + (i * 37) % FIELD_H
            pygame.draw.circle(s, col("ink"), (int(x), int(y)), 2 + i % 3)
        s.blit(self.field, (0, TOP))
        for f in self.fruits:
            if f.life > 2 or int(f.life * 10) % 2:
                cute.fruit(s, f.kind, int(f.x), int(f.y))
        for e in self.enemies:
            draw = cute.grump if e.kind == "g" else cute.flutter
            draw(s, int(e.x) - 2, int(e.y) - 2, self.t, flip=e.face < 0, angry=e.angry)
        for b in self.bubbles:
            if b.enemy:
                draw = cute.grump if b.enemy.kind == "g" else cute.flutter
                draw(s, int(b.x) - 8, int(b.y) - 8, self.t, trapped=True, angry=b.life < 2)
                tint = "red" if b.life < 2 and int(b.life * 8) % 2 else "lavender"
                bubble(s, b.x, b.y, 10, self.t, tint)
            else:
                bubble(s, b.x, b.y, 7 if b.age < FAST_PHASE else 8, self.t)
        p = self.player
        if self.state != "dead" and (self.inv <= 0 or int(self.inv * 12) % 2 == 0):
            if not p.on_ground:
                img = sprite("momo_jump", 0, flip=self.face < 0)
            elif abs(p.vx) > 1:
                img = sprite("momo_walk", int(self.t * 10), flip=self.face < 0)
            else:
                img = sprite("momo_idle", int(self.t * 2), flip=self.face < 0)
            s.blit(img, (int(p.x) - 2, int(p.y) - 1))
        self.parts.draw(s)
        self.floats.draw(s)
        # HUD
        s.fill(col("black"), (0, 0, W, TOP))
        draw_text(s, f"{self.score:07d}", 4, 3, "white", shadow=None)
        draw_text(s, f"HI {max(self.best, self.score):07d}", W // 2, 3, "lavender", align="center", shadow=None)
        draw_text(s, f"STAGE {self.stage}", W - 4, 3, "yellow", align="right", shadow=None)
        self.hearts(s, 54, 3, self.lives)
        if self.state == "intro":
            self.banner(s, f"STAGE {self.stage}", self.level_name)
        elif self.state == "clear":
            self.banner(s, "SPARKLING CLEAN!", "STAGE CLEAR", "mint")
        elif self.hurry and self.level_t < 52.5 and int(self.t * 6) % 2:
            draw_text(s, "HURRY!", W // 2, 90, "red", 2, align="center", outline="black")


def preview(s, t):
    s.fill(col("deep"))
    w, h = s.get_size()
    for x in range(0, w, 8):
        s.fill(col("pink"), (x, h - 8, 7, 7))
    s.fill(col("cream"), (10, h - 30, 40, 3))
    s.blit(sprite("momo_walk", int(t * 8)), (16 + int(math.sin(t) * 10), h - 24))
    bubble(s, w - 30 + math.sin(t * 2) * 3, h - 36 - (t * 6) % 10, 9, t)
    cute.grump(s, w - 38, h - 44 - int((t * 6) % 10), t, trapped=True)
    cute.grump(s, w - 26, h - 24, t, flip=True)
