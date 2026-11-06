"""JELLY STACK - a falling-block puzzle with wobbly jelly cubes (original design for MOCHI ARCADE).

Modes: STAGES - a 200-stage campaign (row / score / dig / star / survive / puzzle / speed goals, a jelly
monster boss every 10th stage, bonus stages on every x5, upgrades between) - and the classic MARATHON,
SPRINT 40 and ENDLESS. Rules: jelly_stack_core.py. Stage tables: jelly_stack_stages.py (exported to iOS).
The iOS port (ios/MochiArcade/Games/JellyStack*.swift) mirrors this file.
"""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, is_bonus, is_boss, rainbow, tier
from mochi_arcade.games import jelly_stack_stages as JS
from mochi_arcade.games.base import GameScene
from mochi_arcade.games.jelly_stack_core import (BH, BW, COLORS, KICKS, KICKS_I, LINE_PTS, ROT, SHAPES,  # noqa: F401
                                                 gravity_interval, rotations)
from mochi_arcade.gfx import H, W, col, draw_text, lerp_col, panel, sprite, text_width

CELL = 9
BX, BY = (W - BW * CELL) // 2, 16
WELL_W, WELL_H = BW * CELL, BH * CELL
BOSS_DMG = {1: 10, 2: 25, 3: 45, 4: 80}
LIFE_STEP = 100000            # extra lives at 100k, 300k, 600k, 1M ... (100k x 1, 3, 6, 10 ...)
GOLD_CHANCE = 0.012
BOMB_CHANCE = 0.02
KIND_TITLE = {"rows": "POP ROWS", "score": "SCORE!", "dig": "DIG OUT!", "stars": "STAR HUNT", "survive": "HANG ON!",
              "puzzle": "PUZZLE", "speed": "SPEED!", "mix": "POP ROWS", "rain": "CANDY RAIN", "well": "JACKPOT WELL",
              "boss": "BOSS!"}

EXPORT = {"stages": JS.STAGE_LIST, "themes": JS.THEMES, "bosses": JS.BOSSES, "upgrades": JS.UPGRADES,
          "attackNames": JS.ATTACK_NAMES, "mods": JS.MODS}

ICON_GLYPH = {"peek": ">", "slow": "`", "sticky": "#", "bomb": "*", "zap": "!", "shield": "=", "party": "+",
              "pocket": "&", "lucky": "$", "heart": "@"}


def upgrade_icon(uid, color):
    def draw(s, cx, cy, t):
        cute.jelly_cell(s, cx - 6, cy - 6, 13, color, t, face=False)
        draw_text(s, ICON_GLYPH[uid], cx, cy - 4, "black", align="center", shadow=None)
    return draw


UPGRADE_POOL = [Upgrade(uid, name, desc, c, upgrade_icon(uid, c), mx) for uid, name, desc, c, mx in JS.UPGRADES]


class Piece:
    def __init__(self, kind, gold=False, bomb=-1):
        self.kind = kind
        self.rot = 0
        self.x = 3
        self.y = -1 if kind != "I" else -2
        self.gold = gold
        self.bomb = bomb          # index of the bomb cell, -1 = none

    def cells(self, x=None, y=None, rot=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        r = self.rot if rot is None else rot
        return [(x + cx, y + cy) for cx, cy in ROT[self.kind][r]]


class JellyStack(GameScene):
    @property
    def music(self):
        return self.stage_song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        self.mode = opt.get("mode", "stages")
        self.campaign = self.mode == "stages"
        self.ghost_opt = bool(opt.get("ghost", True))
        self.grid = [[None] * BW for _ in range(BH)]
        self.wob = [[0.0] * BW for _ in range(BH)]
        self.bag = []
        self.queue = []
        self.holds = [None]
        self.hold_used = False
        self.lines = 0
        self.chain = -1
        self.b2b = False
        self.clearing = None            # [rows, timer]
        self.clear_gold = False
        self.das_dir, self.das_t, self.arr_t = 0, 0.0, 0.0
        self.time = 0.0
        self.fall_t = self.lock_t = 0.0
        self.lock_resets = 0
        self.last_rot = False
        self.pieces = 0
        self.fever_was = False
        self.zap_fx = None               # [row y, timer]
        # campaign state
        self.ups = {}
        self.lives = 3
        self.life_k = 1
        self.stage_n = int(opt.get("start", 1))
        self.st = None
        self.state = "play"
        self.state_t = 0.0
        self.boss = None
        self.tally = []
        self.shield = self.zap = self.coins = 0
        self.rise_t = self.ink_t = self.hide_t = self.rush_t = self.reveal_t = 0.0
        self.ink = []
        self.fail_why = ""
        self.theme = JS.THEMES[0]
        if self.campaign:
            self.level = 1
            self.begin_stage(self.stage_n)
        else:
            self.level = int(opt.get("level", 1))
            self.queue = [self.next_kind() for _ in range(6)]
            self.spawn()

    # ================================================================ helpers
    @property
    def kind(self):
        return self.st["k"] if self.st else self.mode

    def mod(self, m):
        return self.st is not None and m in self.st["mods"]

    def up(self, uid):
        return self.ups.get(uid, 0)

    def next_kind(self):
        if self.st and self.st["k"] == "well":
            return "I"
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    def n_next(self):
        return 3 + self.up("peek")

    def gravity(self):
        if not self.campaign:
            return gravity_interval(min(self.level, 20))
        g = gravity_interval(self.st["g"]) * (1 + 0.15 * self.up("slow"))
        if self.rush_t > 0:
            g = max(0.016, g / 4)
        return g

    def lock_delay(self):
        return 0.5 + 0.15 * self.up("sticky") if self.campaign else 0.5

    def fits(self, cells):
        for x, y in cells:
            if x < 0 or x >= BW or y >= BH:
                return False
            if y >= 0 and self.grid[y][x]:
                return False
        return True

    def grounded(self):
        return not self.fits(self.cur.cells(y=self.cur.y + 1))

    def count(self, code):
        return sum(1 for row in self.grid for c in row if c == code)

    def junk_rows(self):
        return sum(1 for row in self.grid if any(c in ("g", "i", "b") for c in row))

    def filled(self):
        return sum(1 for row in self.grid for c in row if c)

    def stack_top(self):
        for y in range(BH):
            if any(self.grid[y]):
                return y
        return BH

    def wow_on(self):
        return self.mode != "sprint"

    # ================================================================ pieces
    def spawn(self, kind=None):
        if kind is None:
            kind = self.queue.pop(0)
            if not (self.st and self.st["k"] == "puzzle"):
                self.queue.append(self.next_kind())
        self.pieces += 1
        gold = False
        if self.wow_on() and not (self.st and self.st["k"] == "puzzle"):
            gold = random.random() < GOLD_CHANCE + 0.012 * self.up("lucky") + (0.04 if self.kind == "rain" else 0)
        bomb = -1
        if self.up("bomb") and self.pieces % (15 - 3 * self.up("bomb")) == 0:
            bomb = 1
        elif self.st and self.st["k"] not in ("puzzle", "well") and not gold and random.random() < BOMB_CHANCE:
            bomb = 1                                   # a free bomb jelly now and then
        self.cur = Piece(kind, gold, bomb)
        self.fall_t = self.lock_t = 0.0
        self.lock_resets = 0
        self.last_rot = False
        if not self.fits(self.cur.cells()):
            self.top_out()

    def try_move(self, dx, dy):
        if self.fits(self.cur.cells(self.cur.x + dx, self.cur.y + dy)):
            self.cur.x += dx
            self.cur.y += dy
            self.last_rot = False
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
                self.last_rot = True
                if self.grounded() and self.lock_resets < 15:
                    self.lock_t = 0.0
                    self.lock_resets += 1
                self.app.audio.play("rotate")
                return True
        return False

    def do_hold(self):
        if self.hold_used or self.mod("nohold"):
            return
        puzzle = self.st and self.st["k"] == "puzzle"
        if None in self.holds and puzzle and not self.queue:
            return
        self.app.audio.play("hold")
        k = self.cur.kind
        if None in self.holds:
            self.holds[self.holds.index(None)] = k
            self.spawn()
        else:
            out = self.holds.pop(0)
            self.holds.append(k)
            self.spawn(out)
        self.hold_used = True

    def hard_drop(self):
        n = 0
        while self.try_move(0, 1):
            n += 1
        if n:
            self.add(n * 2)
        self.parts.burst(BX + (self.cur.x + 1.5) * CELL, BY + (self.cur.y + 2) * CELL, 6, ("white", "lavender"), 40, 0.3)
        self.lock()

    def immobile(self):
        p = self.cur
        return not (self.fits(p.cells(p.x - 1, p.y)) or self.fits(p.cells(p.x + 1, p.y)) or
                    self.fits(p.cells(p.x, p.y - 1)))

    # ================================================================ locking and clearing
    def lock(self):
        p = self.cur
        cells = p.cells()
        twist = self.last_rot and p.kind != "O" and self.immobile()
        if any(y < 0 for _, y in cells):
            self.top_out()
            return
        code = "$" if p.gold else COLORS[p.kind]
        for x, y in cells:
            self.grid[y][x] = code
            self.wob[y][x] = 1.0
        self.app.audio.play("lock")
        self.hold_used = False
        if self.st:
            self.used += 1
            self.reveal_t = max(self.reveal_t, 0.35)
            if self.st["k"] == "rain":                 # candy rain: every jelly that lands drops a coin
                self.coins += 1
                self.app.audio.play("coin")
        if p.bomb >= 0:
            bx, by = cells[p.bomb]
            n = self.explode(bx, by)
            self.app.audio.play("explode")
            self.app.shake(3, 0.3)
            self.hype.flash("orange", 0.15)
            self.floats.add(BX + bx * CELL + 4, BY + by * CELL, "BOMB!", "orange")
            if self.boss:
                self.hit_boss(10 + 2 * n)
        full = [y for y in range(BH) if all(self.grid[y])]
        if not full:
            if twist:
                self.add(100 * self.level, BX + p.x * CELL + 12, BY + p.y * CELL, "pink")
                self.floats.add(BX + p.x * CELL + 12, BY + p.y * CELL - 9, "TWIST", "pink")
            self.chain = -1
            self.hype.break_combo()
            self.after_piece()
            return
        self.clearing = [full, 0.32]
        self.clear_gold = any(self.grid[y][x] == "$" for y in full for x in range(BW))
        self.score_clear(len(full), twist, full)

    def score_clear(self, n, twist, full):
        L = self.level
        pts = LINE_PTS[n] * L
        big = n == 4 or twist
        b2b = big and self.b2b
        if twist:
            pts *= 2
        if b2b:
            pts = pts * 3 // 2
        self.b2b = big
        self.chain += 1
        if self.chain > 0:
            pts += 50 * self.chain * L
        if n >= 2 and self.up("party"):
            pts = int(pts * (1 + 0.25 * self.up("party")))
        cx = BX + WELL_W // 2
        self.add(pts, cx, BY + full[0] * CELL - 4, "mint")
        if self.wow_on():
            self.hype.hit(1, fever=0)
            self.hype.fever_add(0.035 * n + (0.12 if big else 0) + (0.08 if b2b else 0))
        if twist:
            self.hype.banner("JELLY TWIST!", ["", "SINGLE", "DOUBLE", "TRIPLE", "PARTY"][n] + (" B2B" if b2b else ""),
                             color="pink", dur=1.2)
        elif n == 4:
            self.hype.banner("JELLY PARTY!", "BACK-TO-BACK!" if b2b else None, rainbow=True, dur=1.4)
        elif n == 3:
            self.floats.add(cx, BY + full[0] * CELL - 12, "TRIPLE!", "yellow")
        if n == 4 or twist:
            self.app.audio.play("quad")
            self.app.shake(3, 0.3)
            self.hype.hitstop(0.05)
        else:
            self.app.audio.play("line")
        if self.chain > 0:
            self.floats.add(cx, BY + full[0] * CELL + 6, f"COMBO x{self.chain + 1}", "peach")
        for y in full:
            for x in range(BW):
                c = self.grid[y][x]
                self.parts.burst(BX + x * CELL + 4, BY + y * CELL + 4, 3, (self.cell_color(c), "white"), 60, 0.6)
        self.lines += n
        if self.st:
            self.srows += n
            self.zap += n
            k = self.st["k"]
            if k == "rain":
                candies = sum(1 for y in full for c in self.grid[y] if c == "c")
                self.coins += 3 * n + 3 * candies
                self.hype.shower(8 * n + 6 * candies, "coins")
                self.app.audio.play("coin")
            elif k == "well" and n == 4:
                self.coins += 5
                self.hype.shower(30, "coins")
            if self.boss:
                dmg = BOSS_DMG[n] * (2 if twist else 1)
                if b2b:
                    dmg = dmg * 3 // 2
                dmg += 5 * max(0, self.chain)
                if self.hype.fever_on:
                    dmg = dmg * 5 // 4
                self.hit_boss(dmg)

    def cell_color(self, c):
        if c in COLORS.values():
            return c
        return {"g": "gray", "*": "yellow", "i": "sky", "b": "red", "c": "yellow", "$": "yellow", "s": "cream"}.get(c, "white")

    def explode(self, cx, cy):
        """3x3 blast (bomb jelly). Returns how many jellies it popped."""
        n = 0
        for y in range(cy - 1, cy + 2):
            for x in range(cx - 1, cx + 2):
                if 0 <= x < BW and 0 <= y < BH and self.grid[y][x]:
                    c = self.grid[y][x]
                    if c == "$":
                        self.gold_jackpot()
                    if c == "*":
                        self.star_pop(x, y)
                    self.parts.burst(BX + x * CELL + 4, BY + y * CELL + 4, 4, (self.cell_color(c), "orange", "yellow"),
                                     80, 0.6)
                    self.grid[y][x] = None
                    n += 1
        return n

    def star_pop(self, x, y):
        self.parts.burst(BX + x * CELL + 4, BY + y * CELL + 4, 12, ("yellow", "white", "orange"), 90, 0.8)
        self.add(500 * self.level, BX + x * CELL + 4, BY + y * CELL - 4, "yellow")
        self.app.audio.play("bonus")

    def finish_clear(self):
        rows, _ = self.clearing
        for y in rows:                       # star jellies in the popped rows
            for x in range(BW):
                if self.grid[y][x] == "*":
                    self.star_pop(x, y)
        for y in rows:                       # pop-bombs blast the rows next to them
            for x in range(BW):
                if self.grid[y][x] == "b":
                    self.app.audio.play("explode")
                    self.app.shake(3, 0.25)
                    for yy in (y - 1, y + 1):
                        if 0 <= yy < BH and yy not in rows:
                            for xx in (x - 1, x, x + 1):
                                if 0 <= xx < BW and self.grid[yy][xx]:
                                    c = self.grid[yy][xx]
                                    if c == "*":
                                        self.star_pop(xx, yy)
                                    self.parts.burst(BX + xx * CELL + 4, BY + yy * CELL + 4, 4,
                                                     ("orange", "red", "yellow"), 80, 0.5)
                                    self.grid[yy][xx] = None
        for y in sorted(rows):
            if "i" in self.grid[y]:          # ice survives one pop and thaws into a dusty jelly
                self.grid[y] = ["g" if c == "i" else None for c in self.grid[y]]
                self.wob[y] = [1.0] * BW
                self.parts.burst(BX + WELL_W // 2, BY + y * CELL + 4, 10, ("sky", "white"), 70, 0.5)
                continue
            del self.grid[y]
            del self.wob[y]
            self.grid.insert(0, [None] * BW)
            self.wob.insert(0, [0.0] * BW)
        for y in range(BH):
            for x in range(BW):
                if self.grid[y][x]:
                    self.wob[y][x] = max(self.wob[y][x], 0.6)
        self.clearing = None
        if self.clear_gold:
            self.clear_gold = False
            self.gold_jackpot()
        if self.wow_on() and not any(any(r) for r in self.grid):
            self.perfect()
        if self.st:
            self.reveal_t = 1.2
            need = 12 - 2 * self.up("zap")
            if self.up("zap") and self.zap >= need and self.stack_top() < BH:
                self.zap -= need
                self.zap_row()
        if not self.campaign:
            self.classic_after_clear()
            return
        self.after_piece()

    def gold_jackpot(self):
        self.hype.jackpot(3000 * self.level, "GOLDEN JELLY!")

    def perfect(self):
        well = self.st is not None and self.st["k"] == "well"
        pts = self.add((1000 if well else 10000) * self.level)
        self.hype.banner("PERFECT!!", f"+{pts}", rainbow=True, dur=2.2, scale=3, sound="win")
        self.hype.flash("white", 0.3)
        self.hype.shower(120, "confetti")
        self.hype.fever_add(0.5)
        self.app.shake(5, 0.5)
        if self.st:
            self.perfects += 1
            if well:
                self.coins += 10
                if self.perfects % 3 == 0:          # every third empty well in the jackpot bonus
                    self.hype.jackpot(2000 * self.level)

    def zap_row(self):
        y = BH - 1
        while y >= 0 and not any(self.grid[y]):
            y -= 1
        if y < 0:
            return
        for x in range(BW):
            if self.grid[y][x] == "*":
                self.star_pop(x, y)
            if self.grid[y][x]:
                self.parts.burst(BX + x * CELL + 4, BY + y * CELL + 4, 3, ("yellow", "white"), 70, 0.5)
        del self.grid[y]
        del self.wob[y]
        self.grid.insert(0, [None] * BW)
        self.wob.insert(0, [0.0] * BW)
        self.zap_fx = [y, 0.45]
        self.srows += 1
        self.app.audio.play("shoot")
        self.floats.add(BX + WELL_W // 2, BY + y * CELL - 6, "ZAP!", "yellow")
        if self.boss:
            self.hit_boss(15)

    def classic_after_clear(self):
        new_level = max(self.level, int(self.opt.get("level", 1)) + self.lines // 10)
        if new_level > self.level and self.mode != "sprint":
            self.level = new_level
            self.app.audio.play("levelup")
            self.hype.banner(f"LEVEL {self.level}", color="mint", dur=1.0, scale=1)
        if self.mode == "sprint" and self.lines >= 40:
            self.score = max(1, int(100000 - self.time * 300))
            self.end_game(True, f"{self.time:.1f} SEC")
            return
        if self.mode == "marathon" and self.lines >= 150:
            self.end_game(True, "150 LINES!")
            return
        self.spawn()

    def after_piece(self):
        """A piece has settled (and its rows popped): check the stage goal, then bring the next piece."""
        if not self.campaign:
            self.spawn()
            return
        self.check_life()
        if self.state != "play":
            return
        if self.goal_done():
            self.stage_clear()
            return
        if self.st["k"] == "puzzle" and not self.queue:
            held = [h for h in self.holds if h]
            if held:
                self.holds[self.holds.index(held[0])] = None
                self.spawn(held[0])
                return
            self.fail_stage("OUT OF PIECES!")
            return
        if self.st["k"] == "well" and self.junk_rows() == 0:
            self.push_rows(12, well=True)
            if self.state != "play":
                return
        self.spawn()

    # ================================================================ garbage, attacks
    def push_rows(self, n, hole=None, well=False, shieldable=True):
        if shieldable and self.shield > 0 and not well:
            blocked = min(self.shield, n)
            self.shield -= blocked
            n -= blocked
            self.floats.add(BX + WELL_W // 2, BY + WELL_H - 20, "SHIELD!", "lavender")
            self.parts.burst(BX + WELL_W // 2, BY + WELL_H - 4, 14, ("lavender", "white"), 80, 0.5)
            self.app.audio.play("tin")
        if n <= 0:
            return
        over = False
        rows = JS.well_blocks(random, n // 4) if well else None
        for i in range(n):
            if any(self.grid[0]):
                over = True
            del self.grid[0]
            del self.wob[0]
            if well:
                row = ["g" if c == "g" else None for c in rows[i]]
            else:
                h = random.randrange(BW) if hole is None else hole
                row = ["g"] * BW
                row[h] = None
            self.grid.append(row)
            self.wob.append([0.8] * BW)
        self.app.audio.play("hurt" if not well else "bonus")
        if not self.fits(self.cur.cells()):
            for k in range(1, n + 1):
                if self.fits(self.cur.cells(y=self.cur.y - k)):
                    self.cur.y -= k
                    break
            else:
                over = True
        if over:
            self.top_out()

    def drop_heavy(self, c):
        if self.shield > 0:
            self.shield -= 1
            self.floats.add(BX + c * CELL + 9, BY + 30, "SHIELD!", "lavender")
            self.parts.burst(BX + c * CELL + 9, BY + 20, 14, ("cream", "white"), 80, 0.5)
            self.app.audio.play("tin")
            return
        y = -2
        while self.fits([(c, y + 1), (c + 1, y + 1), (c, y + 2), (c + 1, y + 2)]):
            y += 1
        if y < 0:
            self.top_out()
            return
        for yy in (y, y + 1):
            for xx in (c, c + 1):
                self.grid[yy][xx] = "s"
                self.wob[yy][xx] = 1.0
        self.app.audio.play("boom")
        self.app.shake(5, 0.35)
        self.parts.burst(BX + c * CELL + 9, BY + (y + 2) * CELL, 14, ("cream", "white", "gray"), 90, 0.6)
        if not self.fits(self.cur.cells()):
            for k in range(1, 5):
                if self.fits(self.cur.cells(y=self.cur.y - k)):
                    self.cur.y -= k
                    return
            self.top_out()

    def freeze(self, n):
        top = self.stack_top()
        spots = [(x, y) for y in range(top, min(BH, top + 5)) for x in range(BW)
                 if self.grid[y][x] and self.grid[y][x] not in ("i", "*", "$", "b")]
        random.shuffle(spots)
        for x, y in spots[:n]:
            self.grid[y][x] = "i"
            self.parts.burst(BX + x * CELL + 4, BY + y * CELL + 4, 5, ("sky", "white"), 50, 0.5)
        return len(spots[:n])

    def boss_attack(self, atk):
        b = self.boss
        p = b["pow"] + (1 if b["phase"] >= 3 else 0)
        name = JS.ATTACK_NAMES[atk]
        self.hype.banner(name + "!", color="red", dur=0.9, scale=1)
        if atk == "garbage":
            self.push_rows(min(4, 1 + p // 3), b["hole"])
            self.app.shake(4, 0.3)
        elif atk == "freeze":
            if self.freeze(2 + p) < 2:
                self.push_rows(1, b["hole"])
            self.app.audio.play("trap")
            self.hype.flash("sky", 0.2)
        elif atk == "ink":
            self.ink_t = 5.0 + p
            top = max(4, self.stack_top() - 2)
            self.ink = [(random.randint(top, BH - 1), random.randint(0, BW - 1), random.randint(9, 16))
                        for _ in range(4 + p * 2)]
            self.app.audio.play("pop")
        elif atk == "heavy":
            self.drop_heavy(b["col"])
            if p >= 4 and self.state == "play":
                self.drop_heavy((b["col"] + 4) % (BW - 1))
        elif atk == "flip":
            self.hide_t = 4.0 + p
            vis = self.queue[:self.n_next()]
            vis.reverse()
            self.queue[:len(vis)] = vis
            self.app.audio.play("powerup")
        elif atk == "rush":
            self.rush_t = 4.0 + p * 0.5
            self.app.audio.play("powerup")

    def hit_boss(self, dmg):
        b = self.boss
        if b is None or b["hp"] <= 0 or self.state != "play":
            return
        b["hp"] = max(0, b["hp"] - dmg)
        b["hit"] = 0.3
        self.floats.add(BOSS_CX + random.randint(-10, 10), BOSS_CY - 26, f"-{dmg}", "red")
        self.parts.burst(BOSS_CX, BOSS_CY, 6 + dmg // 8, ("white", JS.BOSSES[b["id"]][2], "yellow"), 90, 0.6)
        self.hype.hitstop(0.04 + min(0.1, dmg / 800))
        if dmg >= 60:
            self.hype.flash("white", 0.12)
            self.app.shake(3, 0.25)
        if b["hp"] <= 0:
            self.boss_down()
            return
        frac = b["hp"] / b["max"]
        if b["phase"] == 1 and frac <= 0.5:
            b["phase"] = 2
            self.hype.banner("GRRR!", "THE BOSS IS ANGRY", color="red", dur=1.2)
        if b["phase"] == 2 and frac <= 0.2 and self.stage_n >= 40:
            b["phase"] = 3
            self.hype.banner("LAST STAND!", color="red", dur=1.2)

    def boss_down(self):
        self.state = "bossdown"
        self.state_t = 0.0
        self.app.audio.stop_music()
        self.app.audio.play("bossdown")
        self.hype.slowmo(0.3, 1.4)
        self.hype.flash("white", 0.4)
        self.hype.shower(120, "stars")
        self.app.shake(6, 0.8)
        self.hype.banners = []
        self.hype.banner("BOSS DOWN!", JS.BOSSES[self.boss["id"]][0], rainbow=True, dur=2.4)
        self.boss["tele"] = None

    def top_out(self):
        if not self.campaign:
            self.app.audio.play("die")
            self.end_game(False, f"{self.lines} LINES")
            return
        if self.state != "play":
            return
        if self.st["k"] in ("rain", "well"):
            self.hype.banner("STACKED!", color="peach", dur=1.0)
            self.stage_clear()
            return
        self.fail_stage("STACKED UP!")

    # ================================================================ campaign flow
    def begin_stage(self, n, retry=False):
        st = JS.STAGE_LIST[n - 1]
        self.st = st
        self.stage_n = n
        self.tier = tier(n)
        self.theme = JS.THEMES[self.tier]
        self.level = self.tier + 1
        self.grid = [[None] * BW for _ in range(BH)]
        self.wob = [[0.0] * BW for _ in range(BH)]
        rows = st["rows"]
        for i, r in enumerate(rows):
            y = BH - len(rows) + i
            for x, ch in enumerate(r):
                if ch != ".":
                    self.grid[y][x] = ch
        self.bag = []
        self.queue = list(st["seq"]) if st["k"] == "puzzle" else [self.next_kind() for _ in range(6)]
        self.holds = [None, None] if self.up("pocket") else [None]
        self.hold_used = False
        self.clearing = None
        self.chain = -1
        self.b2b = False
        self.srows = self.used = self.coins = self.perfects = 0
        self.sscore0 = self.score
        self.stime = 0.0
        self.missed = retry
        self.shield = 2 * self.up("shield")
        self.rise_t = self.ink_t = self.hide_t = self.rush_t = 0.0
        self.reveal_t = 0.0
        self.ink = []
        self.zap_fx = None
        if st["k"] == "boss":
            bd = st["boss"]
            keep = self.boss["hp"] if (retry and self.boss) else bd["hp"]
            keep = min(bd["hp"], keep + bd["hp"] * 15 // 100) if retry else keep
            self.boss = {"id": bd["id"], "hp": keep, "max": bd["hp"], "atk": bd["atk"], "every": bd["every"],
                         "pow": bd["pow"], "t": bd["every"] * 0.8, "tele": None, "hit": 0.0, "phase": 1,
                         "col": 0, "hole": 0}
            if keep <= bd["hp"] // 2:
                self.boss["phase"] = 2
        else:
            self.boss = None
        self.spawn()
        self.reached(n)
        self.state = "warning" if (st["k"] == "boss" and not retry) else "intro"
        self.state_t = 0.0
        song = "boss" if st["k"] == "boss" else "bonus" if st["k"] in ("rain", "well") else "jelly"
        self.app.audio.music(song)
        if self.state == "warning":
            self.app.audio.play("warning")
        else:
            self.app.audio.play("stage")

    def start_play(self):
        self.state = "play"
        self.state_t = 0.0
        if self.st["k"] in ("rain", "well"):
            self.hype.banner("GO GO GO!", rainbow=True, dur=1.0)
        else:
            self.hype.banner("GO!", color="lime", dur=0.8)

    def goal_done(self):
        k, goal = self.st["k"], self.st["goal"]
        if k in ("rows", "mix", "speed"):
            return self.srows >= goal
        if k == "score":
            return self.score - self.sscore0 >= goal
        if k in ("dig", "puzzle"):
            return self.junk_rows() == 0
        if k == "stars":
            return self.count("*") == 0
        if k == "survive":
            return self.stime >= goal
        if k in ("rain", "well"):
            return self.stime >= self.st["lim"]
        if k == "boss":
            return self.boss["hp"] <= 0
        return False

    def progress(self):
        """(label, fraction done) for the goal bar."""
        k, goal, st = self.st["k"], self.st["goal"], self.st
        if k in ("rows", "mix", "speed"):
            return f"ROWS {min(self.srows, goal)}/{goal}", min(1.0, self.srows / goal)
        if k == "score":
            got = self.score - self.sscore0
            return f"SCORE {min(got, goal)}", min(1.0, got / goal)
        if k in ("dig", "puzzle"):
            left = self.junk_rows()
            tot = max(1, len(st["rows"]))
            return f"DUSTY ROWS {left}", 1 - min(1.0, left / tot)
        if k == "stars":
            left = self.count("*")
            return f"STARS {goal - left}/{goal}", (goal - left) / goal
        if k == "survive":
            return f"HANG ON {max(0, int(goal - self.stime + 0.99))}", min(1.0, self.stime / goal)
        if k in ("rain", "well"):
            return f"COINS {self.coins}", min(1.0, self.stime / st["lim"])
        return "", 0.0

    def fail_stage(self, why):
        if self.state != "play":
            return
        self.state = "fail"
        self.state_t = 0.0
        self.fail_why = why
        self.lives -= 1
        self.chain = -1
        self.hype.break_combo()
        self.app.audio.play("die")
        self.app.shake(4, 0.4)
        self.hype.banner("OOPS!", why, color="red", dur=1.6)
        if self.boss:
            self.boss["tele"] = None

    def stage_clear(self):
        if self.state not in ("play", "bossdown"):
            return
        k = self.st["k"]
        L = self.level
        self.state = "clear"
        self.state_t = 0.0
        self.app.audio.play("win")
        if k != "boss":
            self.hype.banners = []
        if k in ("rain", "well"):
            self.hype.banner("BONUS END!", f"{self.coins} COINS", color="yellow", dur=1.4)
            lines = [("COINS", self.coins * 100 * L)]
        else:
            if k != "boss":
                self.hype.banner("STAGE CLEAR!", rainbow=True, dur=1.4)
            self.hype.shower(40, "confetti")
            lines = [("BOSS BONUS" if k == "boss" else "CLEAR", (5000 if k == "boss" else 1000) * L)]
            if k == "speed":
                lines.append(("TIME", int(max(0, self.st["lim"] - self.stime)) * 50 * L))
            elif k == "survive":
                lines.append(("SURVIVED", 1500 * L))
            elif k == "puzzle":
                lines.append(("PIECES LEFT", max(0, self.st["lim"] - self.used) * 1000 * L))
            elif self.st["par"]:
                lines.append(("TIME", int(max(0, self.st["par"] - self.stime)) * 20 * L))
            lines.append(("NO MISS", 0 if self.missed else 2000 * L))
            cells = self.filled()
            if cells == 0:
                lines.append(("PERFECT WELL", 5000 * L))
            elif cells <= 12:
                lines.append(("CLEAN WELL", 1500 * L))
        self.tally = [[label, v, 0] for label, v in lines]
        self.tally_i = 0
        self.tally_t = 0.0

    def next_stage(self):
        n = self.stage_n
        if n >= STAGES:
            self.hype.jackpot(1000000, "ALL 200 STAGES!")
            self.end_game(True, "ALL 200 STAGES!", delay=3.5)
            return
        if is_boss(n) or is_bonus(n):
            self.state = "upgrade"
            self.pick_upgrade(UPGRADE_POOL, self.ups, self.took_upgrade,
                              title="BOSS REWARD!" if is_boss(n) else "POWER UP!")
        else:
            self.begin_stage(n + 1)

    def took_upgrade(self, uid):
        if uid is None:
            self.lives += 1
            self.hype.banner("1UP!", "EVERYTHING IS MAXED", color="pink", dur=1.4, sound="extra")
        else:
            self.ups[uid] = self.ups.get(uid, 0) + 1
            if uid == "heart":
                self.lives += 1
                self.app.audio.play("extra")
        self.begin_stage(self.stage_n + 1)

    def check_life(self):
        while self.score >= LIFE_STEP * self.life_k * (self.life_k + 1) // 2:
            self.life_k += 1
            self.lives += 1
            self.hype.banner("1UP!", "EXTRA LIFE", color="pink", dur=1.4, sound="extra")
            self.hype.shower(20, "hearts")

    # ================================================================ update
    def tick(self, dt):
        self.time += dt
        for row in self.wob:
            for x in range(BW):
                if row[x] > 0:
                    row[x] = max(0.0, row[x] - dt * 2.5)
        if self.zap_fx:
            self.zap_fx[1] -= dt
            if self.zap_fx[1] <= 0:
                self.zap_fx = None
        if self.wow_on() and self.hype.fever_on != self.fever_was:
            self.fever_was = self.hype.fever_on
            if self.state == "play" or not self.campaign:
                self.app.audio.music("fever" if self.fever_was else self.stage_song())
        if self.chain >= 0 and self.hype.combo > 0:
            self.hype.combo_t = self.hype.COMBO_TIME      # the chain lives until a piece pops nothing
        if self.campaign and self.state == "play" and self.ending is None:
            self.stime += dt                               # the stage clock also runs while rows pop
        if self.clearing:
            self.clearing[1] -= dt
            if self.clearing[1] <= 0:
                self.finish_clear()
            return
        if self.ending is not None:
            return
        if self.campaign and not self.tick_campaign(dt):
            return
        self.play_input(dt)

    def stage_song(self):
        if not self.st:
            return "jelly"
        return "boss" if self.st["k"] == "boss" else "bonus" if self.st["k"] in ("rain", "well") else "jelly"

    def tick_campaign(self, dt):
        """Stage flow. Returns True when the player controls the piece this frame."""
        inp = self.app.input
        self.state_t += dt
        s = self.state
        if s == "warning":
            if self.state_t > 2.4:
                self.state = "intro"
                self.state_t = 0.0
            return False
        if s == "intro":
            if self.state_t > 2.6 or (self.state_t > 0.5 and inp.hit("a", "b", "y")):
                self.start_play()
            return False
        if s == "fail":
            if self.state_t > 1.8:
                if self.lives <= 0:
                    self.end_game(False, f"STAGE {self.stage_n}")
                else:
                    self.begin_stage(self.stage_n, retry=True)
            return False
        if s == "bossdown":
            if self.state_t > 0.5 and int(self.state_t * 10) % 2 == 0:
                self.parts.burst(BOSS_CX + random.randint(-16, 16), BOSS_CY + random.randint(-14, 14), 10,
                                 (JS.BOSSES[self.boss["id"]][2], "white", "yellow"), 100, 0.7)
            if self.state_t > 2.2:
                self.stage_clear()
            return False
        if s == "clear":
            if self.state_t > 1.2:
                self.state = "tally"
                self.state_t = 0.0
            return False
        if s == "tally":
            self.tick_tally(dt)
            return False
        if s != "play":
            return False
        # ---- playing
        self.ink_t = max(0.0, self.ink_t - dt)
        self.hide_t = max(0.0, self.hide_t - dt)
        self.rush_t = max(0.0, self.rush_t - dt)
        self.reveal_t = max(0.0, self.reveal_t - dt)
        k = self.st["k"]
        if self.st["rise"]:
            self.rise_t += dt
            if self.rise_t >= self.st["rise"]:
                self.rise_t = 0.0
                self.push_rows(1)
                if self.state != "play":
                    return False
        if self.boss:
            self.tick_boss(dt)
            if self.state != "play":
                return False
        if k == "speed" and self.stime >= self.st["lim"]:
            self.fail_stage("TIME UP!")
            return False
        if k in ("survive", "rain", "well") and self.goal_done():
            self.stage_clear()
            return False
        if k == "score" and self.goal_done():
            self.stage_clear()
            return False
        return True

    def tick_tally(self, dt):
        self.tally_t += dt
        if self.tally_i < len(self.tally):
            line = self.tally[self.tally_i]
            step = max(1, line[1] // 24)
            add = min(step, line[1] - line[2])
            line[2] += add
            self.score += add
            if self.tally_t > 0.06 and add:
                self.tally_t = 0.0
                self.app.audio.play("move")
            if line[2] >= line[1]:
                self.tally_i += 1
                self.tally_t = 0.0
                self.app.audio.play("coin" if line[1] else "move")
            self.check_life()
            return
        if (self.tally_t > 0.6 and self.app.input.hit("a", "b", "y")) or self.tally_t > 3.0:
            self.next_stage()

    def tick_boss(self, dt):
        b = self.boss
        b["hit"] = max(0.0, b["hit"] - dt)
        if b["tele"] is not None:
            b["tele"][1] -= dt
            if b["tele"][1] <= 0:
                atk = b["tele"][0]
                b["tele"] = None
                self.boss_attack(atk)
                if b["phase"] >= 3 and self.state == "play" and random.random() < 0.5:
                    b["t"] = 1.2
            return
        b["t"] -= dt
        if b["t"] <= 0:
            b["t"] = b["every"] * (0.75 if b["phase"] >= 2 else 1.0)
            atk = b["atk"][0] if random.random() < 0.45 else random.choice(b["atk"])
            b["tele"] = [atk, max(1.2, 2.2 - self.tier * 0.05)]
            b["col"] = random.randrange(BW - 1)
            b["hole"] = random.randrange(BW)
            self.app.audio.play("trap")

    def play_input(self, dt):
        inp = self.app.input
        raw = inp.raw
        if inp.hit("x"):
            self.do_hold()
            return
        if pygame.K_SPACE in raw or inp.hit("y"):
            self.hard_drop()
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
            if self.lock_t >= self.lock_delay():
                self.lock()
        else:
            self.lock_t = 0.0

    # ================================================================ drawing
    def render(self, s):
        th = self.theme
        draw_bg(s, th, self.t)
        self.draw_well(s)
        self.draw_hud(s)
        self.parts.draw(s)
        self.floats.draw(s)
        if self.campaign:
            if self.state == "warning":
                self.draw_warning(s)
            elif self.state == "intro":
                self.draw_intro(s)
            elif self.state == "tally":
                self.draw_tally(s)

    def draw_cell(self, s, x, y, c, wob=0.0, size=CELL, rb=-1):
        px, py = BX + x * CELL, BY + y * CELL
        t = self.t
        if c in COLORS.values():
            color = rainbow(rb, t) if rb >= 0 else c
            cute.jelly_cell(s, px, py, size, color, t, wobble=wob)
        elif c == "g":
            cute.jelly_cell(s, px, py, size, "gray", face=False)
            k = col("darkgray")
            s.fill(k, (px + 2, py + 4, 2, 1))
            s.fill(k, (px + 5, py + 4, 2, 1))
        elif c == "*":
            tw = int(t * 4 + x + y) % 4 == 0
            cute.jelly_cell(s, px, py, size, "orange" if tw else "yellow", face=False)
            draw_text(s, "$", px + 2, py + 1, "white", shadow=None)
        elif c == "i":
            cute.jelly_cell(s, px, py, size, "sky", face=False)
            pygame.draw.rect(s, col("white"), (px, py, size, size), 1, border_radius=2)
            s.fill(col("white"), (px + 2, py + 5, 1, 1))
            s.fill(col("white"), (px + 3, py + 4, 1, 1))
            s.fill(col("white"), (px + 4, py + 3, 1, 1))
        elif c == "b":
            cute.jelly_cell(s, px, py, size, "red", face=False)
            pygame.draw.circle(s, col("black"), (px + 4, py + 5), 2)
            s.fill(col("yellow" if int(t * 8) % 2 else "orange"), (px + 5, py + 1, 2, 2))
        elif c == "c":
            cute.jelly_cell(s, px, py, size, "peach", face=False)
            pygame.draw.circle(s, col("yellow"), (px + 4, py + 4), 3)
            pygame.draw.circle(s, col("orange"), (px + 4, py + 4), 3, 1)
        elif c == "$":
            cute.jelly_cell(s, px, py, size, "yellow", t, wobble=wob)
            if int(t * 6 + x * 3 + y) % 5 == 0:
                s.fill(col("white"), (px + 6, py + 1, 2, 2))
        elif c == "s":
            pygame.draw.rect(s, col("gray"), (px, py, size, size), border_radius=1)
            pygame.draw.rect(s, col("cream"), (px, py, size, size - 1), border_radius=1)
            s.fill(col("white"), (px + 1, py + 1, size - 3, 1))

    def draw_well(self, s):
        th = self.theme
        hue = th[1]
        bwc = col(hue) if self.campaign else col("lavender")
        top = self.stack_top()
        danger = top < 5 and (self.state == "play" or not self.campaign)
        border = "red" if danger and int(self.t * 6) % 2 else None
        r = (BX - 3, BY - 3, WELL_W + 6, WELL_H + 6)
        pygame.draw.rect(s, col("black"), (r[0] + 2, r[1] + 2, r[2], r[3]), border_radius=3)
        pygame.draw.rect(s, lerp_col("black", hue, 0.06) if self.campaign else col("black"), r, border_radius=3)
        pygame.draw.rect(s, col(border) if border else bwc, r, 1, border_radius=3)
        chk = lerp_col("black", hue, 0.14) if self.campaign else col("night")
        for y in range(BH):
            for x in range(BW):
                if (x + y) % 2 == 0:
                    s.fill(chk, (BX + x * CELL, BY + y * CELL, CELL, CELL))
        clearing = set(self.clearing[0]) if self.clearing else set()
        fever = self.hype.fever_on
        vanish = self.mod("vanish") and self.state == "play" and self.reveal_t <= 0
        for y in range(BH):
            for x in range(BW):
                c = self.grid[y][x]
                if not c:
                    continue
                if y in clearing:
                    if int(self.clearing[1] * 20) % 2:
                        s.fill(col("white"), (BX + x * CELL, BY + y * CELL, CELL, CELL))
                    else:
                        self.draw_cell(s, x, y, c)
                    continue
                if vanish:
                    pygame.draw.rect(s, lerp_col("black", hue, 0.35), (BX + x * CELL, BY + y * CELL, CELL, CELL), 1)
                    continue
                wob = math.sin(self.t * 30 + x) * self.wob[y][x] * 1.5
                self.draw_cell(s, x, y, c, wob, rb=(x + y) if fever and c in COLORS.values() else -1)
        if self.mod("fog") and self.state == "play":
            fog = pygame.Surface((WELL_W, 8 * CELL), pygame.SRCALPHA)
            fog.fill(col("gray", 205))
            s.blit(fog, (BX, BY + 12 * CELL))
            for i in range(6):
                fx = BX + 4 + int((self.t * (6 + i) * 3 + i * 23) % (WELL_W - 8))
                pygame.draw.circle(s, col("white"), (fx, BY + 12 * CELL + 2), 4)
        if self.zap_fx:
            y = BY + self.zap_fx[0] * CELL + 4
            w = int(self.zap_fx[1] * 10)
            s.fill(col("yellow"), (BX, y - w // 2, WELL_W, max(1, w)))
            s.fill(col("white"), (BX, y, WELL_W, 1))
        playing = (not self.campaign) or self.state in ("play", "intro")
        if not self.clearing and self.ending is None and playing:
            if self.ghost_opt and not self.mod("noghost"):
                gy = self.cur.y
                while self.fits(self.cur.cells(y=gy + 1)):
                    gy += 1
                for x, y in self.cur.cells(y=gy):
                    if y >= 0:
                        cute.jelly_cell(s, BX + x * CELL, BY + y * CELL, CELL, self.piece_color(), ghost=True)
        if self.ink_t > 0:
            self.draw_ink(s)
        if not self.clearing and self.ending is None and playing:
            for i, (x, y) in enumerate(self.cur.cells()):
                if y < 0:
                    continue
                cute.jelly_cell(s, BX + x * CELL, BY + y * CELL, CELL, self.piece_color(), self.t)
                if i == self.cur.bomb:
                    px, py = BX + x * CELL, BY + y * CELL
                    pygame.draw.circle(s, col("black"), (px + 4, py + 5), 3)
                    s.fill(col("yellow" if int(self.t * 10) % 2 else "red"), (px + 6, py + 1, 2, 2))
        if self.boss and self.boss["tele"] and self.state == "play":
            self.draw_tele_well(s)
        if self.st and self.st["rise"] and self.state == "play":
            f = self.rise_t / self.st["rise"]
            c = "red" if f > 0.8 and int(self.t * 10) % 2 else "orange"
            s.fill(col(c), (BX, BY + WELL_H + 1, int(WELL_W * f), 2))
        if self.campaign and self.state == "fail":
            ov = pygame.Surface((WELL_W, WELL_H), pygame.SRCALPHA)
            ov.fill((12, 8, 24, min(170, int(self.state_t * 200))))
            s.blit(ov, (BX, BY))

    def piece_color(self):
        if self.cur.gold:
            return "yellow" if int(self.t * 8) % 2 else "orange"
        if self.hype.fever_on:
            return rainbow(0, self.t)
        return COLORS[self.cur.kind]

    def draw_ink(self, s):
        fade = min(1.0, self.ink_t / 0.6)
        for y, x, r in self.ink:          # ink blobs, clipped to the well
            rr = max(1, int(r * fade))
            cx = BX + x * CELL + 4
            cy = BY + y * CELL + 4
            for dy in range(-rr, rr + 1):
                yy = cy + dy
                if BY <= yy < BY + WELL_H:
                    half = int(math.sqrt(rr * rr - dy * dy))
                    a, b = max(BX, cx - half), min(BX + WELL_W, cx + half + 1)
                    if b > a:
                        s.fill(col("night"), (a, yy, b - a, 1))
            if rr > 4:
                pygame.draw.circle(s, col("purple"), (cx - rr // 3, cy - rr // 3), 2)

    def draw_tele_well(self, s):
        b = self.boss
        atk = b["tele"][0]
        blink = int(self.t * 8) % 2
        if atk == "heavy":
            x = BX + b["col"] * CELL
            ov = pygame.Surface((CELL * 2, WELL_H), pygame.SRCALPHA)
            ov.fill(col("red", 60 if blink else 30))
            s.blit(ov, (x, BY))
            draw_text(s, "`", x + 6, BY + 2, "red" if blink else "white", shadow=None)
        elif atk == "garbage":
            n = min(4, 1 + (b["pow"] + (1 if b["phase"] >= 3 else 0)) // 3)
            for x in range(BW):
                if x != b["hole"]:
                    s.fill(col("red" if blink else "orange"), (BX + x * CELL, BY + WELL_H + 1, CELL - 1, 2))
            draw_text(s, f"+{n}", BX - 6, BY + WELL_H - 8, "red", align="right")

    # ---------------------------------------------------------------- HUD
    def draw_hud(self, s):
        th = self.theme
        hue, acc = (th[1], th[2]) if self.campaign else ("lavender", "yellow")
        # header: score | goal or boss bar | lives
        draw_text(s, f"{self.score}", 4, 4, "yellow")
        if self.campaign:
            s.blit(sprite("heart"), (W - 30, 3))
            draw_text(s, f"x{self.lives}", W - 21, 4, "white")
            if self.boss:
                b = self.boss
                boss_bar(s, JS.BOSSES[b["id"]][0], b["hp"], b["max"], self.t, y=1)
            else:
                label, frac = self.progress()
                self.goal_bar(s, label, frac, hue)
        else:
            label = {"marathon": f"MARATHON  {self.lines}/150", "sprint": f"SPRINT  {self.lines}/40",
                     "endless": f"ENDLESS  {self.lines} LINES"}[self.mode]
            frac = self.lines / 150 if self.mode == "marathon" else self.lines / 40 if self.mode == "sprint" else 0
            self.goal_bar(s, label, min(1.0, frac), "lavender")
            draw_text(s, f"LV {self.level}", W - 4, 4, "mint", align="right")
        # left column: hold
        no_hold = self.mod("nohold")
        for i, h in enumerate(self.holds):
            x = 6 + i * 52
            panel(s, (x, 18, 48, 34), fill="ink", border="darkgray" if no_hold else "pink")
            draw_text(s, "HOLD" if i == 0 else "HOLD 2", x + 24, 21, "darkgray" if no_hold else "pink", align="center",
                      shadow=None)
            if no_hold:
                draw_text(s, "X", x + 24, 36, "darkgray", align="center")
            elif h:
                self.mini(s, h, x + 24, 39, 7)
        # stage / mode panel
        panel(s, (6, 56, 100, 44), fill="ink", border=hue)
        if self.campaign:
            n = self.stage_n
            title = f"STAGE {n}" + (" BOSS" if is_boss(n) else " BONUS" if is_bonus(n) else "")
            draw_text(s, title, 56, 60, "yellow" if not is_boss(n) else "red", align="center")
            draw_text(s, th[0], 56, 70, acc, align="center", shadow=None)
        else:
            draw_text(s, {"marathon": "MARATHON", "sprint": "SPRINT 40", "endless": "ENDLESS"}[self.mode], 56, 60,
                      "yellow", align="center")
            draw_text(s, f"TIME {self.time:.1f}" if self.mode == "sprint" else f"LINES {self.lines}", 56, 70, "white",
                      align="center", shadow=None)
        draw_text(s, f"HI {max(self.best, self.score)}", 56, 84, "lavender", align="center", shadow=None)
        # goal / info panel
        panel(s, (6, 104, 100, 56), fill="ink", border=hue)
        if self.campaign:
            self.draw_goal_panel(s, acc)
        else:
            draw_text(s, "COMBO", 12, 110, "lavender", shadow=None)
            draw_text(s, f"{max(0, self.chain + 1)}", 100, 110, "white", align="right")
            draw_text(s, "LEVEL", 12, 124, "lavender", shadow=None)
            draw_text(s, f"{self.level}", 100, 124, "white", align="right")
            draw_text(s, "B2B" if self.b2b else "", 56, 142, "pink", align="center")
        # upgrades
        if self.campaign:
            panel(s, (6, 164, 100, 32), fill="ink", border="darkgray")
            owned = [(u, self.ups[u.id]) for u in UPGRADE_POOL if self.ups.get(u.id)]
            if not owned:
                draw_text(s, "NO UPGRADES", 56, 169, "darkgray", align="center", shadow=None)
                draw_text(s, "BEAT BOSSES!", 56, 180, "darkgray", align="center", shadow=None)
            for i, (u, lv) in enumerate(owned[:10]):
                x, y = 10 + (i % 5) * 19, 167 + (i // 5) * 14
                cute.jelly_cell(s, x, y, 9, u.color, face=False)
                draw_text(s, ICON_GLYPH[u.id], x + 2, y + 1, "black", shadow=None)
                draw_text(s, str(lv), x + 10, y + 3, "white", shadow=None)
        # right column: next
        nn = self.n_next()
        ph = 26 + (nn - 1) * 18
        panel(s, (214, 18, 50, ph), fill="ink", border="mint")
        draw_text(s, "NEXT", 239, 21, "mint", align="center", shadow=None)
        hidden = self.hide_t > 0
        for i in range(nn):
            cy = 38 + i * 18 if i else 37
            if hidden:
                draw_text(s, "?", 239, cy - 3, "hotpink" if int(self.t * 6 + i) % 2 else "lavender", align="center")
            elif i < len(self.queue):
                self.mini(s, self.queue[i], 239, cy + (1 if i else 0), 7 if i == 0 else 5)
        if self.campaign and self.st["k"] == "puzzle":
            draw_text(s, f"{len(self.queue)} LEFT", 239, 20 + ph, "white", align="center", shadow=None)
        # meters: fever / zap / shield
        self.draw_meters(s, hue)
        # boss or buddy
        if self.campaign:
            panel(s, (214, 116, 100, 80), fill="ink", border="red" if self.boss else hue)
            if self.boss:
                self.draw_boss_area(s)
            else:
                self.draw_buddy(s, hue)

    def goal_bar(self, s, label, frac, hue):
        panel(s, (60, 1, 200, 12), fill="black", border=hue, radius=3, shadow=False)
        draw_text(s, label, 64, 4, "white", shadow=None)
        x0 = 68 + text_width(label)
        bw = 256 - x0
        if bw > 4:
            s.fill(col("darkgray"), (x0, 5, bw, 4))
            s.fill(col("lime" if frac >= 1 else hue), (x0, 5, int(bw * frac), 4))
            s.fill(col("white"), (x0, 5, int(bw * frac), 1))

    def draw_goal_panel(self, s, acc):
        st = self.st
        k = st["k"]
        draw_text(s, KIND_TITLE[k], 56, 108, acc, align="center")
        big, sub = "", ""
        if k in ("rows", "mix", "speed"):
            big = f"{max(0, st['goal'] - self.srows)}"
            sub = "ROWS TO GO"
        elif k == "score":
            big = f"{max(0, st['goal'] - (self.score - self.sscore0))}"
            sub = "POINTS TO GO"
        elif k in ("dig", "puzzle"):
            big = f"{self.junk_rows()}"
            sub = "DUSTY ROWS"
        elif k == "stars":
            big = f"{self.count('*')}"
            sub = "STARS LEFT"
        elif k == "survive":
            big = f"{max(0, int(st['goal'] - self.stime + 0.99))}"
            sub = "SECONDS"
        elif k in ("rain", "well"):
            big = f"{max(0, int(st['lim'] - self.stime + 0.99))}"
            sub = f"{self.coins} COINS"
        elif k == "boss":
            big = f"{int(math.ceil(100 * self.boss['hp'] / self.boss['max']))}%"
            sub = "BOSS HP"
        sc = 2 if text_width(big, 2) <= 92 else 1
        draw_text(s, big, 56, 119 if sc == 2 else 122, "white", sc, align="center")
        draw_text(s, sub, 56, 136, "lavender", align="center", shadow=None)
        extra = ""
        if k == "speed":
            left = max(0.0, st["lim"] - self.stime)
            extra = f"TIME {left:.0f}"
            if left < 10 and int(self.t * 4) % 2:
                extra = ""
        elif k == "puzzle":
            extra = f"PIECES {len(self.queue) + (1 if self.state == 'play' else 0)}"
        elif st["mods"]:
            extra = " ".join(JS.MODS[m] for m in st["mods"])
        if extra:
            draw_text(s, extra, 56, 148, "orange" if k in ("speed", "puzzle") else "pink", align="center", shadow=None)

    def draw_meters(self, s, hue):
        x = 270
        # fever gauge (vertical)
        draw_text(s, "FVR", x, 21, "hotpink", shadow=None)
        h = 60
        s.fill(col("black"), (x + 4, 31, 9, h + 2))
        f = 1.0 if self.hype.fever_on else self.hype.fever
        fh = int(h * f)
        c = rainbow(0, self.t) if self.hype.fever_on else "hotpink"
        s.fill(col(c), (x + 5, 32 + h - fh, 7, fh))
        pygame.draw.rect(s, col("pink"), (x + 4, 31, 9, h + 2), 1)
        if self.campaign:
            yy = 96
            if self.up("zap"):
                need = 12 - 2 * self.up("zap")
                draw_text(s, "ZAP", 292, 21, "yellow", shadow=None)
                s.fill(col("black"), (296, 31, 9, h + 2))
                zh = int(h * min(1.0, self.zap / need))
                s.fill(col("yellow"), (297, 32 + h - zh, 7, zh))
                pygame.draw.rect(s, col("yellow"), (296, 31, 9, h + 2), 1)
            if self.up("shield"):
                cute.jelly_cell(s, 270, yy + 4, 9, "lavender", face=False)
                draw_text(s, "=", 272, yy + 5, "black", shadow=None)
                draw_text(s, f"x{self.shield}", 281, yy + 6, "lavender", shadow=None)
            if self.st["rise"] and not self.boss:
                draw_text(s, "RISE", 312, yy + 6, "orange", align="right", shadow=None)

    def mini(self, s, kind, cx, cy, size):
        cells = ROT[kind][0]
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        w = (max(xs) - min(xs) + 1) * size
        h = (max(ys) - min(ys) + 1) * size
        for x, y in cells:
            cute.jelly_cell(s, cx - w // 2 + (x - min(xs)) * size, cy - h // 2 + (y - min(ys)) * size, size,
                            COLORS[kind], face=False)

    def draw_buddy(self, s, hue):
        """A big jelly pal beside the well that cheers you on."""
        cx, cy = 264, 160
        happy = self.chain > 0 or self.state in ("clear", "tally")
        worried = self.stack_top() < 7
        bob = int(math.sin(self.t * (8 if happy else 3)) * (3 if happy else 1))
        w = 40 + int(math.sin(self.t * 5) * 2)
        body = pygame.Rect(cx - w // 2, cy - 18 + bob, w, 36 - bob)
        dark = lerp_col("black", hue, 0.55)
        pygame.draw.rect(s, dark, body.move(0, 2), border_radius=10)
        pygame.draw.rect(s, col(hue), body, border_radius=10)
        s.fill(col("white"), (body.x + 6, body.y + 4, 8, 2))
        mood = "wow" if worried else "happy"
        cute.eyes(s, cx, cy - 4 + bob, 7, 0, mood, blink=int(self.t * 1.3) % 6 == 0, size=2)
        cute.mouth(s, cx, cy + 5 + bob, "wow" if worried else "happy")
        cute.blush(s, cx, cy + 2 + bob, 10)
        msg = "YAY!" if happy else "EEK!" if worried else ""
        if msg:
            draw_text(s, msg, cx, 124, "yellow" if happy else "red", align="center")

    def draw_boss_area(self, s):
        b = self.boss
        down = self.state in ("bossdown", "clear", "tally", "upgrade")
        if (self.state == "bossdown" and self.state_t > 1.0) or self.state in ("clear", "tally", "upgrade"):
            draw_text(s, "DEFEATED!", BOSS_CX, BOSS_CY - 4, "yellow", align="center")
            return
        shake = random.randint(-2, 2) if (b["hit"] > 0 or down) else 0
        draw_boss(s, b["id"], BOSS_CX + shake, BOSS_CY, self.t, hurt=b["hit"] > 0 and int(self.t * 20) % 2 == 0,
                  angry=b["phase"] >= 2)
        if b["tele"] and self.state == "play":
            atk, left = b["tele"]
            blink = int(self.t * 8) % 2
            draw_text(s, JS.ATTACK_NAMES[atk] + "!", BOSS_CX, 185, "red" if blink else "yellow", align="center",
                      shadow="black")
            pygame.draw.circle(s, col("white"), (BOSS_CX + 22, BOSS_CY - 24), 6)
            draw_text(s, "!", BOSS_CX + 20, BOSS_CY - 27, "red", shadow=None)
        elif self.state == "play":
            nxt = max(0.0, b["t"])
            w = int(80 * min(1.0, nxt / b["every"]))
            s.fill(col("darkgray"), (224, 190, 80, 2))
            s.fill(col("red"), (224, 190, w, 2))
        if self.ink_t > 0:
            draw_text(s, "INK!", 222, 124, "purple", shadow=None)
        if self.rush_t > 0:
            draw_text(s, "RUSH!", 306, 124, "orange", align="right", shadow=None)

    def draw_warning(self, s):
        t = self.state_t
        if int(t * 6) % 2 == 0:
            for i in range(0, W, 16):
                x = (i + int(t * 60)) % (W + 16) - 16
                pygame.draw.polygon(s, col("red"), [(x, 70), (x + 8, 70), (x + 16, 62), (x + 8, 62)])
                pygame.draw.polygon(s, col("red"), [(x, 138), (x + 8, 138), (x + 16, 130), (x + 8, 130)])
        ov = pygame.Surface((W, 56), pygame.SRCALPHA)
        ov.fill((12, 8, 24, 200))
        s.blit(ov, (0, 74))
        draw_text(s, "WARNING!!", W // 2, 82, "red" if int(t * 8) % 2 else "yellow", 3, align="center", outline="black")
        b = JS.BOSSES[self.st["boss"]["id"]]
        draw_text(s, f"{b[0]} APPROACHES", W // 2, 110, "white", align="center")

    def draw_intro(self, s):
        st = self.st
        k = st["k"]
        appear = min(1.0, self.state_t * 5)
        y = 46 + int((1 - appear) * 40)
        bonus = k in ("rain", "well")
        border = "red" if k == "boss" else "yellow" if bonus else self.theme[1]
        panel(s, (44, y, 232, 104), fill="night", border=border)
        n = self.stage_n
        draw_text(s, f"STAGE {n}", W // 2, y + 8, "yellow", 2, align="center", outline="ink")
        draw_text(s, self.theme[0], W // 2, y + 28, self.theme[2], align="center")
        draw_text(s, self.goal_text(), W // 2, y + 44, "white", align="center")
        if st["mods"]:
            draw_text(s, " + ".join(JS.MODS[m] for m in st["mods"]), W // 2, y + 58, "pink", align="center")
        if st["new"]:
            tag = "NEW! " + st["new"]
            draw_text(s, tag, W // 2, y + 72, "lime" if int(self.t * 4) % 2 else "mint", align="center")
        if self.missed:
            draw_text(s, "TRY AGAIN!", W // 2, y + 86, "peach", align="center")
        elif self.state_t > 0.5:
            draw_text(s, "DROP: GO!", W // 2, y + 88, "lavender", align="center", shadow=None)

    def goal_text(self):
        st = self.st
        k, g = st["k"], st["goal"]
        if k == "rows":
            return f"POP {g} ROWS"
        if k == "mix":
            return f"POP {g} ROWS - ROWS RISE!"
        if k == "score":
            return f"SCORE {g} POINTS"
        if k == "dig":
            return "CLEAR ALL THE DUSTY JELLY"
        if k == "stars":
            return f"POP ALL {g} STAR JELLIES"
        if k == "survive":
            return f"SURVIVE {g} SECONDS"
        if k == "puzzle":
            return f"CLEAR IT WITH {st['lim']} PIECES"
        if k == "speed":
            return f"POP {g} ROWS IN {st['lim']} SEC"
        if k == "rain":
            return "30 SEC: EVERY POP RAINS COINS"
        if k == "well":
            return "30 SEC: LONG JELLIES ONLY!"
        if k == "boss":
            return f"BEAT {JS.BOSSES[st['boss']['id']][0]}!"
        return ""

    def draw_tally(self, s):
        appear = min(1.0, self.state_t * 6)
        y = 40 + int((1 - appear) * 30)
        k = self.st["k"]
        panel(s, (52, y, 216, 26 + 12 * len(self.tally) + 26), fill="night", border="yellow")
        title = "BOSS DEFEATED!" if k == "boss" else "BONUS RESULTS" if k in ("rain", "well") else \
            f"STAGE {self.stage_n} CLEAR!"
        draw_text(s, title, W // 2, y + 8, "yellow", align="center")
        total = 0
        for i, (label, v, shown) in enumerate(self.tally):
            if i > self.tally_i:
                break
            yy = y + 24 + i * 12
            draw_text(s, label, 64, yy, "lavender" if v else "darkgray", shadow=None)
            draw_text(s, f"{shown}" if v else "-", 256, yy, "white" if v else "darkgray", align="right")
            total += shown
        yy = y + 28 + 12 * len(self.tally)
        s.fill(col("lavender"), (64, yy - 2, 192, 1))
        draw_text(s, "TOTAL", 64, yy + 2, "yellow")
        draw_text(s, f"{total}", 256, yy + 2, "yellow", align="right")
        if self.tally_i >= len(self.tally) and self.tally_t > 0.6:
            draw_text(s, "DROP: NEXT", W // 2, yy + 16, "white" if int(self.t * 3) % 2 else "lavender", align="center",
                      shadow=None)


BOSS_CX, BOSS_CY = 264, 160


# ==================================================================== backgrounds and boss art
def draw_bg(s, th, t):
    name, hue, acc, style = th
    bg = lerp_col("black", hue, 0.16)
    deco = lerp_col("black", hue, 0.3)
    s.fill(bg)
    if style == 0:          # bubbles drifting up
        for i in range(16):
            x = (i * 47 + 13) % W
            y = H - (t * (8 + i % 4) * 2 + i * 31) % (H + 20)
            pygame.draw.circle(s, deco, (int(x), int(y)), 3 + i % 4)
    elif style == 1:        # rolling waves
        for i in range(6):
            y0 = 20 + i * 34
            for x in range(0, W, 4):
                y = y0 + int(math.sin(x * 0.05 + t * 1.5 + i) * 4)
                s.fill(deco, (x, y, 4, 3))
    elif style == 2:        # twinkles
        for i in range(28):
            x = (i * 71 + 7) % W
            y = (i * 37 + 11) % H
            if int(t * 2 + i) % 5:
                s.fill(deco, (x, y - 2, 1, 5))
                s.fill(deco, (x - 2, y, 5, 1))
    elif style == 3:        # diagonal candy stripes
        off = int(t * 10) % 24
        for i in range(-H, W + H, 24):
            x = i + off
            pygame.draw.polygon(s, deco, [(x, 0), (x + 8, 0), (x + 8 - H, H), (x - H, H)])
    else:                   # slow checker
        off = int(t * 6) % 32
        for y in range(-32, H + 32, 16):
            for x in range(-32, W + 32, 16):
                if ((x + y) // 16) % 2 == 0:
                    s.fill(deco, (x + off, y + off // 2, 16, 16))


def draw_boss(s, bid, cx, cy, t, hurt=False, angry=False):
    """Seven original jelly monsters, about 48x44, drawn around (cx, cy)."""
    name, _, body, trim = JS.BOSSES[bid]
    bc = "white" if hurt else body
    mood = "angry" if angry else "happy"
    wob = math.sin(t * 4) * 2
    k = col("black")
    if bid == 0:      # GUMMY KING: green dome jelly with a crown
        w = int(44 + wob)
        pygame.draw.ellipse(s, k, (cx - w // 2 - 1, cy - 19, w + 2, 40))
        pygame.draw.ellipse(s, col(bc), (cx - w // 2, cy - 18, w, 38))
        s.fill(col("white"), (cx - 12, cy - 12, 6, 3))
        pygame.draw.polygon(s, col(trim), [(cx - 10, cy - 16), (cx - 12, cy - 26), (cx - 5, cy - 20), (cx, cy - 28),
                                           (cx + 5, cy - 20), (cx + 12, cy - 26), (cx + 10, cy - 16)])
        s.fill(col("red"), (cx - 1, cy - 22, 3, 3))
        cute.eyes(s, cx, cy - 2, 8, 0, mood, size=2)
        cute.mouth(s, cx, cy + 8, mood)
    elif bid == 1:    # FROSTY FLAN: pudding with caramel top and icicles
        pygame.draw.polygon(s, k, [(cx - 22, cy + 20), (cx + 22, cy + 20), (cx + 15, cy - 16), (cx - 15, cy - 16)])
        pygame.draw.polygon(s, col(bc), [(cx - 21, cy + 19), (cx + 21, cy + 19), (cx + 14, cy - 15), (cx - 14, cy - 15)])
        pygame.draw.ellipse(s, col("brown" if not hurt else "white"), (cx - 15, cy - 20, 30, 10))
        for i in range(5):
            x = cx - 12 + i * 6
            ln = 4 + (i * 3) % 5
            pygame.draw.polygon(s, col(trim), [(x, cy - 12), (x + 4, cy - 12), (x + 2, cy - 12 + ln)])
        cute.eyes(s, cx, cy + 2, 7, 0, "sleepy" if not angry else "angry", size=2)
        cute.mouth(s, cx, cy + 10, mood)
        if int(t * 3) % 2:
            s.fill(col("white"), (cx + 18, cy - 20, 1, 3))
            s.fill(col("white"), (cx + 17, cy - 19, 3, 1))
    elif bid == 2:    # INKY PUDDING: round purple blob with wiggly tentacles
        for i in range(4):
            x = cx - 15 + i * 10
            for j in range(4):
                dx = int(math.sin(t * 6 + i + j * 0.8) * 2)
                pygame.draw.circle(s, col(trim if not hurt else "white"), (x + dx, cy + 12 + j * 4), 3)
        pygame.draw.circle(s, k, (cx, cy - 2), 20)
        pygame.draw.circle(s, col(bc), (cx, cy - 2), 19)
        s.fill(col("white"), (cx - 10, cy - 14, 5, 2))
        cute.eyes(s, cx, cy - 4, 7, int(math.sin(t * 2) * 2), mood, size=2)
        cute.mouth(s, cx, cy + 6, "wow")
    elif bid == 3:    # TOFU TITAN: a big square block of tofu
        r = pygame.Rect(cx - 21, cy - 20 + int(abs(wob)), 42, 40 - int(abs(wob)))
        pygame.draw.rect(s, k, r.inflate(2, 2), border_radius=4)
        pygame.draw.rect(s, col(bc), r, border_radius=4)
        pygame.draw.rect(s, col(trim), (r.x, r.bottom - 6, r.w, 6), border_radius=3)
        s.fill(col("cream"), (r.x + 4, r.y + 3, 10, 2))
        cute.eyes(s, cx, r.y + 14, 9, 0, "angry", size=2)
        cute.mouth(s, cx, r.y + 24, "angry" if angry else "flat")
    elif bid == 4:    # TRICKY TART: round tart with a jester hat
        pygame.draw.circle(s, k, (cx, cy + 4), 19)
        pygame.draw.circle(s, col("orange" if not hurt else "white"), (cx, cy + 4), 18)
        pygame.draw.circle(s, col(bc), (cx, cy + 4), 14)
        for a in range(0, 360, 60):
            ra = math.radians(a + t * 40)
            s.fill(col("red"), (cx + int(math.cos(ra) * 10), cy + 4 + int(math.sin(ra) * 10), 2, 2))
        pygame.draw.polygon(s, col(trim), [(cx - 14, cy - 12), (cx - 22, cy - 26), (cx, cy - 16)])
        pygame.draw.polygon(s, col("yellow"), [(cx + 14, cy - 12), (cx + 22, cy - 26), (cx, cy - 16)])
        pygame.draw.circle(s, col("yellow"), (cx - 22, cy - 26), 2)
        pygame.draw.circle(s, col(trim), (cx + 22, cy - 26), 2)
        cute.eyes(s, cx, cy + 2, 6, int(math.sin(t * 5) * 2), mood, size=2)
        cute.mouth(s, cx, cy + 10, "happy" if not angry else "angry")
    elif bid == 5:    # FIZZY FLOAT: fizzy soda bubble with a straw
        pygame.draw.line(s, col("red"), (cx + 6, cy - 18), (cx + 14, cy - 30), 2)
        pygame.draw.circle(s, k, (cx, cy), 20)
        pygame.draw.circle(s, col(bc), (cx, cy), 19)
        pygame.draw.circle(s, col(trim), (cx, cy + 6), 13)
        for i in range(6):
            by = cy + 14 - int((t * 20 + i * 7) % 30)
            pygame.draw.circle(s, col("white"), (cx - 10 + i * 4, by), 1)
        cute.eyes(s, cx, cy - 4, 7, 0, mood, size=2)
        cute.mouth(s, cx, cy + 5, "wow" if angry else "happy")
    else:             # JELLY EMPEROR: layered rainbow jelly with crown and cape
        pygame.draw.polygon(s, col("red"), [(cx - 24, cy - 6), (cx + 24, cy - 6), (cx + 28, cy + 22), (cx - 28, cy + 22)])
        for i, c in enumerate(("hotpink", "orange", "yellow", "lime", "sky")):
            cc = "white" if hurt else c
            pygame.draw.rect(s, col(cc), (cx - 18 + i, cy - 16 + i * 7, 36 - i * 2, 8), border_radius=3)
        pygame.draw.rect(s, k, (cx - 19, cy - 17, 38, 37), 1, border_radius=4)
        pygame.draw.polygon(s, col(trim), [(cx - 12, cy - 16), (cx - 14, cy - 28), (cx - 6, cy - 20), (cx, cy - 30),
                                           (cx + 6, cy - 20), (cx + 14, cy - 28), (cx + 12, cy - 16)])
        s.fill(col("sky"), (cx - 1, cy - 25, 3, 3))
        cute.eyes(s, cx, cy - 3, 8, 0, "angry", size=2)
        cute.mouth(s, cx, cy + 7, mood)


def preview(s, t):
    s.fill(col("ink"))
    w, h = s.get_size()
    kinds = ["mint", "pink", "yellow", "sky", "lavender", "lime", "peach"]
    for y in range(4):
        for x in range(10):
            if (x * 7 + y * 3) % 5:
                c = kinds[(x + y) % 7]
                if (x + y * 3) % 11 == 0:
                    c = "gray"
                cute.jelly_cell(s, 2 + x * 9, h - 9 - y * 9, 9, c, t, wobble=math.sin(t * 6 + x))
    cute.jelly_cell(s, 2 + 3 * 9, h - 9 - 3 * 9, 9, "yellow", face=False)
    draw_text(s, "$", 2 + 3 * 9 + 2, h - 9 - 3 * 9 + 1, "white", shadow=None)
    py = int((t * 20) % 30)
    for cx, cy in ((4, 0), (5, 0), (6, 0), (5, 1)):
        cute.jelly_cell(s, 2 + cx * 9, py + cy * 9, 9, "pink", t)
