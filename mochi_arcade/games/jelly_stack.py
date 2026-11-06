"""JELLY STACK - a falling-block puzzle with wobbly jelly cubes (original presentation for MOCHI ARCADE)."""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.games.base import GameScene
from mochi_arcade.gfx import H, W, col, draw_text, panel

BW, BH = 10, 20
CELL = 9
BX, BY = (W - BW * CELL) // 2, 12

# piece shapes in their spawn orientation (rotation states are generated)
SHAPES = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(1, 0), (2, 0), (1, 1), (2, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}
COLORS = {"I": "mint", "O": "peach", "T": "pink", "S": "lavender", "Z": "sky", "J": "lime", "L": "yellow"}

# wall-kick offsets for rotation from state a to state b (x right, y down)
KICKS = {
    (0, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)], (1, 0): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (1, 2): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)], (2, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (2, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)], (3, 2): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (3, 0): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)], (0, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
}
KICKS_I = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)], (1, 0): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)], (2, 1): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)], (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)], (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
}


def rotations(kind):
    size = 4 if kind == "I" else 3 if kind != "O" else 4
    cells = SHAPES[kind]
    out = [cells]
    for _ in range(3):
        if kind == "O":
            out.append(cells)
            continue
        cells = [(size - 1 - y, x) for x, y in cells]
        out.append(cells)
    return out


ROT = {k: rotations(k) for k in SHAPES}
LINE_PTS = {1: 100, 2: 300, 3: 500, 4: 800}


class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.rot = 0
        self.x = 3
        self.y = -1 if kind != "I" else -2

    def cells(self, x=None, y=None, rot=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        r = self.rot if rot is None else rot
        return [(x + cx, y + cy) for cx, cy in ROT[self.kind][r]]


class JellyStack(GameScene):
    music = "jelly"

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        self.mode = opt.get("mode", "marathon")
        self.level = int(opt.get("level", 1))
        self.ghost = bool(opt.get("ghost", True))
        self.grid = [[None] * BW for _ in range(BH)]
        self.wob = [[0.0] * BW for _ in range(BH)]
        self.bag = []
        self.queue = [self.next_kind() for _ in range(4)]
        self.hold, self.hold_used = None, False
        self.lines = 0
        self.combo = -1
        self.b2b = False
        self.clearing = None  # (rows, timer)
        self.das_dir, self.das_t, self.arr_t = 0, 0.0, 0.0
        self.time = 0.0
        self.message, self.message_t = "", 0.0
        self.spawn()

    def next_kind(self):
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    def gravity(self):
        lv = min(self.level, 20)
        return max(0.016, (0.8 - (lv - 1) * 0.007) ** (lv - 1))

    def spawn(self, kind=None):
        if kind is None:
            kind = self.queue.pop(0)
            self.queue.append(self.next_kind())
        self.cur = Piece(kind)
        self.fall_t = 0.0
        self.lock_t = 0.0
        self.lock_resets = 0
        if not self.fits(self.cur.cells()):
            self.app.audio.play("die")
            self.end_game(False, f"{self.lines} LINES")

    def fits(self, cells):
        for x, y in cells:
            if x < 0 or x >= BW or y >= BH:
                return False
            if y >= 0 and self.grid[y][x]:
                return False
        return True

    def grounded(self):
        return not self.fits(self.cur.cells(y=self.cur.y + 1))

    def try_move(self, dx, dy):
        if self.fits(self.cur.cells(self.cur.x + dx, self.cur.y + dy)):
            self.cur.x += dx
            self.cur.y += dy
            if dx and self.grounded() and self.lock_resets < 15:
                self.lock_t = 0.0
                self.lock_resets += 1
            return True
        return False

    def rotate(self, d):
        p = self.cur
        a, b = p.rot, (p.rot + d) % 4
        table = KICKS_I if p.kind == "I" else KICKS
        for kx, ky in table[(a, b)]:
            if self.fits(p.cells(p.x + kx, p.y - ky, b)):
                p.x += kx
                p.y -= ky
                p.rot = b
                if self.grounded() and self.lock_resets < 15:
                    self.lock_t = 0.0
                    self.lock_resets += 1
                self.app.audio.play("rotate")
                return True
        return False

    def lock(self):
        p = self.cur
        for x, y in p.cells():
            if y < 0:
                self.app.audio.play("die")
                self.end_game(False, f"{self.lines} LINES")
                return
            self.grid[y][x] = COLORS[p.kind]
            self.wob[y][x] = 1.0
        self.app.audio.play("lock")
        full = [y for y in range(BH) if all(self.grid[y])]
        if full:
            self.clearing = [full, 0.32]
            n = len(full)
            pts = LINE_PTS[n] * self.level
            if n == 4:
                if self.b2b:
                    pts = int(pts * 1.5)
                self.b2b = True
                self.app.audio.play("quad")
                self.app.shake(3, 0.3)
                self.say("JELLY PARTY!")
            else:
                self.b2b = False
                self.app.audio.play("line")
                if n == 3:
                    self.say("TRIPLE!")
            self.combo += 1
            if self.combo > 0:
                pts += 50 * self.combo * self.level
                self.say(f"COMBO x{self.combo + 1}")
            self.add(pts, BX + BW * CELL // 2, BY + full[0] * CELL, "mint")
            for y in full:
                for x in range(BW):
                    self.parts.burst(BX + x * CELL + 4, BY + y * CELL + 4, 3,
                                     (self.grid[y][x], "white"), 60, 0.6)
        else:
            self.combo = -1
            self.spawn()
        self.hold_used = False

    def say(self, msg):
        self.message, self.message_t = msg, 1.2

    def finish_clear(self):
        rows, _ = self.clearing
        for y in rows:
            del self.grid[y]
            del self.wob[y]
            self.grid.insert(0, [None] * BW)
            self.wob.insert(0, [0.0] * BW)
        for y in range(BH):
            for x in range(BW):
                if self.grid[y][x]:
                    self.wob[y][x] = max(self.wob[y][x], 0.6)
        self.lines += len(rows)
        self.clearing = None
        new_level = max(self.level, int(self.opt.get("level", 1)) + self.lines // 10)
        if new_level > self.level and self.mode != "sprint":
            self.level = new_level
            self.app.audio.play("levelup")
            self.say(f"LEVEL {self.level}")
        if self.mode == "sprint" and self.lines >= 40:
            self.score = max(1, int(100000 - self.time * 300))
            self.end_game(True, f"{self.time:.1f} SEC")
            return
        if self.mode == "marathon" and self.lines >= 150:
            self.end_game(True, "150 LINES!")
            return
        self.spawn()

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        inp = self.app.input
        self.time += dt
        self.message_t -= dt
        for row in self.wob:
            for x in range(BW):
                if row[x] > 0:
                    row[x] = max(0.0, row[x] - dt * 2.5)
        if self.clearing:
            self.clearing[1] -= dt
            if self.clearing[1] <= 0:
                self.finish_clear()
            return
        if self.ending is not None:
            return
        raw = inp.raw
        if inp.hit("x") and not self.hold_used:
            self.app.audio.play("hold")
            k = self.cur.kind
            if self.hold:
                self.spawn(self.hold)
            else:
                self.spawn()
            self.hold, self.hold_used = k, True
            return
        if pygame.K_SPACE in raw or inp.hit("y"):
            n = 0
            while self.try_move(0, 1):
                n += 1
            self.add(n * 2)
            self.parts.burst(BX + (self.cur.x + 1.5) * CELL, BY + (self.cur.y + 2) * CELL, 6, ("white", "lavender"), 40, 0.3)
            self.lock()
            return
        if inp.hit("up", "b"):
            self.rotate(1)
        elif inp.hit("a"):
            self.rotate(-1)
        # horizontal with DAS
        d = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        if d != self.das_dir:
            self.das_dir, self.das_t, self.arr_t = d, 0.0, 0.0
            if d and self.try_move(d, 0):
                self.app.audio.play("move")
        elif d:
            self.das_t += dt
            if self.das_t > 0.167:          # delayed auto shift, then auto repeat every 33 ms
                self.arr_t += dt
                while self.arr_t >= 0.033:
                    self.arr_t -= 0.033
                    if not self.try_move(d, 0):
                        break
        # gravity / soft drop
        g = self.gravity()
        if inp.down("down"):
            g = min(g, 0.03)
        self.fall_t += dt
        while self.fall_t >= g:
            self.fall_t -= g
            if self.try_move(0, 1):
                if inp.down("down"):
                    self.add(1)
            else:
                self.fall_t = 0
                break
        if self.grounded():
            self.lock_t += dt
            if self.lock_t >= 0.5:
                self.lock()
        else:
            self.lock_t = 0.0

    # ---------------------------------------------------------------- draw
    def draw_piece_cells(self, s, kind, cells, ox, oy, size, ghost=False):
        for x, y in cells:
            cute.jelly_cell(s, ox + x * size, oy + y * size, size, COLORS[kind], self.t, face=size >= 8, ghost=ghost)

    def mini(self, s, kind, cx, cy):
        cells = ROT[kind][0]
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        w = (max(xs) - min(xs) + 1) * 7
        h = (max(ys) - min(ys) + 1) * 7
        for x, y in cells:
            cute.jelly_cell(s, cx - w // 2 + (x - min(xs)) * 7, cy - h // 2 + (y - min(ys)) * 7, 7, COLORS[kind], face=False)

    def render(self, s):
        s.fill(col("ink"))
        for i in range(14):
            x = (i * 47) % W
            y = (H - (self.t * (8 + i % 4) * 2 + i * 31) % (H + 20))
            pygame.draw.circle(s, col("deep"), (int(x), int(y)), 3 + i % 4)
        bw, bh = BW * CELL, BH * CELL
        panel(s, (BX - 3, BY - 3, bw + 6, bh + 6), fill="black", border="lavender", radius=3)
        for y in range(BH):
            for x in range(BW):
                if (x + y) % 2 == 0:
                    s.fill(col("night"), (BX + x * CELL, BY + y * CELL, CELL, CELL))
        clearing = set(self.clearing[0]) if self.clearing else set()
        for y in range(BH):
            for x in range(BW):
                c = self.grid[y][x]
                if not c:
                    continue
                if y in clearing:
                    if int(self.clearing[1] * 20) % 2:
                        s.fill(col("white"), (BX + x * CELL, BY + y * CELL, CELL, CELL))
                    continue
                wob = math.sin(self.t * 30 + x) * self.wob[y][x] * 1.5
                cute.jelly_cell(s, BX + x * CELL, BY + y * CELL, CELL, c, self.t, wobble=wob)
        if not self.clearing and self.ending is None:
            if self.ghost:
                gy = self.cur.y
                while self.fits(self.cur.cells(y=gy + 1)):
                    gy += 1
                cells = [(x, y) for x, y in self.cur.cells(y=gy) if y >= 0]
                self.draw_piece_cells(s, self.cur.kind, cells, BX, BY, CELL, ghost=True)
            cells = [(x, y) for x, y in self.cur.cells() if y >= 0]
            self.draw_piece_cells(s, self.cur.kind, cells, BX, BY, CELL)
        # side panels
        panel(s, (14, 14, 76, 40), fill="ink", border="pink")
        draw_text(s, "HOLD", 52, 18, "pink", align="center", shadow=None)
        if self.hold:
            self.mini(s, self.hold, 52, 40)
        panel(s, (14, 62, 76, 112), fill="ink", border="lavender")
        rows = [("SCORE", f"{self.score}"), ("LEVEL", f"{self.level}"), ("LINES", f"{self.lines}")]
        if self.mode == "sprint":
            rows.append(("TIME", f"{self.time:.1f}"))
        else:
            rows.append(("BEST", f"{max(self.best, self.score)}"))
        for n, (k, v) in enumerate(rows):
            draw_text(s, k, 20, 68 + n * 26, "lavender", shadow=None)
            draw_text(s, v, 84, 78 + n * 26, "white", align="right")
        panel(s, (230, 14, 76, 100), fill="ink", border="mint")
        draw_text(s, "NEXT", 268, 18, "mint", align="center", shadow=None)
        for n, k in enumerate(self.queue[:3]):
            self.mini(s, k, 268, 40 + n * 26)
        mode = {"marathon": "MARATHON", "sprint": "SPRINT 40", "endless": "ENDLESS"}[self.mode]
        draw_text(s, mode, 268, 124, "yellow", align="center")
        if self.mode == "sprint":
            draw_text(s, f"{max(0, 40 - self.lines)} TO GO", 268, 136, "white", align="center")
        self.parts.draw(s)
        self.floats.draw(s)
        if self.message_t > 0:
            draw_text(s, self.message, BX + bw // 2, BY + 60, "yellow", 1, align="center", outline="black")


def preview(s, t):
    s.fill(col("ink"))
    w, h = s.get_size()
    kinds = ["mint", "pink", "yellow", "sky", "lavender", "lime", "peach"]
    for y in range(4):
        for x in range(10):
            if (x * 7 + y * 3) % 5:
                cute.jelly_cell(s, 2 + x * 9, h - 9 - y * 9, 9, kinds[(x + y) % 7], t, wobble=math.sin(t * 6 + x))
    py = int((t * 20) % 30)
    for cx, cy in ((4, 0), (5, 0), (6, 0), (5, 1)):
        cute.jelly_cell(s, 2 + cx * 9, py + cy * 9, 9, "pink", t)
