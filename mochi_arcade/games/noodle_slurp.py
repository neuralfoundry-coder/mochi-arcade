"""NOODLE SLURP - a hungry noodle slurps dumplings through a 200-stage kitchen campaign (original game).

Modes: CAMPAIGN (200 stages: goals, hazards, bonus feasts on every x5, a boss on every 10th stage, upgrades),
CLASSIC and WRAP (endless). The stage tables are generated in noodle_slurp_stages.py and exported to the iOS
port (ios/MochiArcade/Games/NoodleSlurp.swift mirrors this file).
"""
import math
import random
from collections import deque

import pygame

from mochi_arcade import cute, sprites
from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow
from mochi_arcade.games import noodle_slurp_stages as NS
from mochi_arcade.games.base import GameScene
from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

GW, GH, C = NS.GW, NS.GH, 8
OX, OY = (W - GW * C) // 2, 22
DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
STEP = {"slow": 0.16, "normal": 0.115, "fast": 0.08}          # endless modes
SPEED_MULT = {"slow": 1.25, "normal": 1.0, "fast": 0.8}      # campaign
MILESTONES = (20, 30, 40, 50, 75, 100, 150, 200)
PORTAL_COLORS = {"1": ("lavender", "purple"), "2": ("mint", "teal"), "3": ("pink", "hotpink"), "4": ("yellow", "orange")}
WEAK_LOOK = {"crab": "chili", "teapot": "sugar", "golem": "bean", "bao": "bun", "sushi": "chili", "ghost": "chili"}
WEAK_ATTACK = {"crab": "toss", "teapot": "beam", "sushi": "plates", "golem": "drop", "bao": "toss"}


# ----------------------------------------------------------------------------- pixel art (registered at import)
def _x2(rows):
    """Double-size pixel art (upgrade card icons)."""
    return ["".join(ch * 2 for ch in r) for r in rows for _ in (0, 1)]


_ICONS = {
    "ns_tea": ["..w..w..", ".w..w...", "kkkkkk..", "kmwmmmkk", "kmmmmmk.", "kmmmmmkk", ".kmmmk..", "..kkk..."],
    "ns_chili": ["......l.", ".....lk.", "....rrk.", "...rwrk.", "..rrrk..", ".rrrk...", "rrkk....", "kk......"],
    "ns_magnet": [".kkkkkk.", "krrrrrrk", "krrkkrrk", "krk..krk", "krk..krk", "kwk..kwk", "kwk..kwk", ".k....k."],
    "ns_bolt": ["....kk..", "...kyk..", "..kyyk..", ".kyyyykk", "kkyyyyk.", "..kyyk..", "..kyk...", "..kk...."],
    "ns_ghost": ["..kkkk..", ".kvvvvk.", "kvkvvkvk", "kvvvvvvk", "kvvvvvvk", "kvvvvvvk", "kvkvvkvk", ".k.kk.k."],
    "ns_snip": ["kk....kk", "kgk..kgk", ".kgkkgk.", "..kggk..", "..kggk..", ".kpkkpk.", "kp.kk.pk", "kkk..kkk"],
    "ns_bowl": [".w..w...", "..w..w..", "kkkkkkkk", "koeoeoek", ".kcccck.", ".kcccck.", "..kkkk..", "..kkkk.."],
    "ns_gold": ["..o.o.o.", ".kyyyyyk", "kyyyyyyk", "kykyykyk", "kyyyyyyk", "kpyyyypk", ".kyyyyk.", "..kkkk.."],
    "ns_clock": ["..kkkk..", ".kwwwwk.", "kwwkwwwk", "kwwkwwwk", "kwwkkkwk", "kwwwwwwk", ".kwwwwk.", "..kkkk.."],
    "ns_loop": ["..mmmm..", ".m....m.", "m..mm..m", "m.m..m.m", "m.m.mm.m", "m..m...m", ".m....m.", "..mmmmm."],
}
NS_ART = {}
for _k, _rows in _ICONS.items():
    NS_ART[_k] = [_rows]
    NS_ART[_k + "2"] = [_x2(_rows)]
NS_ART["ns_heart2"] = [_x2([".kk.kk.", "kppkppk", "kpppppk", ".kpppk.", "..kpk..", "...k..."])]
sprites.ART.update(NS_ART)

UPGRADES = [
    ["calm", "CALM BROTH", "NOODLE MOVES|7% SLOWER", "sky", "ns_bowl2", 4],
    ["magnet", "MAGNET SPOON", "SLURP FOOD|1 MORE TILE|AWAY", "red", "ns_magnet2", 3],
    ["dash", "DASH SAUCE", "A: ZOOM AHEAD|+1 DASH|EVERY STAGE", "yellow", "ns_bolt2", 3],
    ["ghost", "GHOST TAIL", "PASS THROUGH|YOUR LAST|4 BITS/LEVEL", "lavender", "ns_ghost2", 3],
    ["snip", "SNIP SNIP", "BITE OFF YOUR|TAIL INSTEAD|OF CRASHING", "pink", "ns_snip2", 3],
    ["life", "SPARE BOWL", "+1 LIFE|RIGHT NOW", "hotpink", "ns_heart2", 5],
    ["gold", "GOLD RUSH", "MORE GOLDEN|DUMPLINGS", "yellow", "ns_gold2", 4],
    ["goldtime", "SLOW GOLD", "GOLDEN ONES|STAY 2 SEC|LONGER", "orange", "ns_clock2", 3],
    ["fever", "SPICE RACK", "FEVER FILLS|FASTER AND|LASTS LONGER", "orange", "ns_chili2", 3],
    ["combo", "LONG SLURP", "COMBO TIMER|LASTS LONGER", "mint", "ns_loop2", 3],
]
POOL = [Upgrade(u[0], u[1], u[2], u[3], u[4], u[5]) for u in UPGRADES]

STAGE_DATA = NS.build_all()
EXPORT = {"stages": STAGE_DATA, "themes": NS.THEMES, "bosses": NS.BOSSES, "upgrades": UPGRADES}


def cxy(c):
    return c % GW, c // GW


def cpx(c):
    """Top-left pixel of a cell."""
    return OX + (c % GW) * C, OY + (c // GW) * C


def endless_stage(mode, speed):
    return {"n": 0, "kind": "endless", "theme": 0, "map": "." * (GW * GH), "sp": [8, 10], "len": 4,
            "goal": "endless", "target": 0, "foods": 1, "step": STEP[speed], "par": 0, "gate": 0, "rollers": [],
            "vents": [], "squeeze": [], "new": "", "tpl": mode}


# ----------------------------------------------------------------------------- moving parts
class Roller:
    """Rolling meatball (bounces), sushi plate / gold plate / fortune slip (fly straight, break on contact)."""

    def __init__(self, x, y, dx, dy, period, kind="ball"):
        self.x, self.y, self.dx, self.dy, self.period, self.kind = x, y, dx, dy, period, kind
        self.acc = 0.0
        self.alive = True
        self.spin = 0.0

    @property
    def cell(self):
        return self.y * GW + self.x


class Vent:
    WARN, ON = 0.7, 1.0

    def __init__(self, x, y, dx, dy, ln, period, phase, life=-1.0):
        self.x, self.y, self.dx, self.dy, self.period, self.phase, self.life = x, y, dx, dy, period, phase, life
        self.beam = [(y + dy * i) * GW + x + dx * i for i in range(ln + 1)]

    def state(self, t):
        u = (t + self.phase) % self.period
        if u >= self.period - self.ON:
            return 2
        if u >= self.period - self.ON - self.WARN:
            return 1
        return 0


class Item:
    def __init__(self, kind, cell, life=-1.0, look=""):
        self.kind, self.cell, self.life, self.look = kind, cell, life, look
        self.t = 0.0


class Attack:
    def __init__(self, kind, cells, tele, act=0.0, style="", dx=0, dy=0, gold=-1, src=None):
        self.kind, self.cells, self.tele, self.act, self.style = kind, cells, tele, act, style
        self.dx, self.dy, self.gold = dx, dy, gold
        self.src = src or (W // 2, OY)
        self.t = 0.0
        self.fired = False

    @property
    def live(self):
        return self.tele <= self.t < self.tele + self.act


class Boss:
    def __init__(self, d):
        info = NS.BOSSES[d["kind"]]
        self.kind, self.name, self.w, self.h = d["kind"], info["name"], info["w"], info["h"]
        self.hint = info["hint"]
        self.hp = self.maxhp = d["hp"]
        self.lvl, self.pool, self.cool, self.tele, self.move = d["lvl"], d["pool"], d["cool"], d["tele"], d["move"]
        self.x, self.y = (GW - self.w) // 2, 0
        if self.kind == "ghost":
            self.x, self.y = 15, 3
        self.cd = 2.2
        self.move_t = 0.0
        self.mdir = 1
        self.flash = self.stun = self.inv = self.anim = self.lid = 0.0
        self.angry = False
        self.last = ""
        self.dead = False
        self.dash = 0
        self.ddx = self.ddy = 0
        self.weak_wait = 0.0
        self.t = 0.0

    def cells(self):
        return [(self.y + j) * GW + self.x + i for j in range(self.h) for i in range(self.w)]

    def center(self):
        return OX + self.x * C + self.w * C // 2, OY + self.y * C + self.h * C // 2


# ----------------------------------------------------------------------------- the game
class NoodleSlurp(GameScene):
    music = "noodle"

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        self.mode = opt.get("mode", "campaign")
        if self.mode not in ("campaign", "classic", "wrap"):
            self.mode = "campaign"
        self.speed = opt.get("speed", "normal")
        if self.speed not in STEP:
            self.speed = "normal"
        self.campaign = self.mode == "campaign"
        self.lives = 3 if self.campaign else 1
        self.up = {}
        self.next_life = 30000
        self.stage_n = max(1, min(STAGES, int(opt.get("start", 1)))) if self.campaign else 0
        self.total_eaten = 0
        self.best_len = 0
        self.fever_boosted = False
        self.cache = None
        self.begin_stage()

    def lv(self, uid):
        return self.up.get(uid, 0)

    # ---------------------------------------------------------------- stage setup
    def begin_stage(self):
        if self.campaign:
            st = STAGE_DATA[self.stage_n - 1]
            self.reached(self.stage_n)
        else:
            st = endless_stage(self.mode, self.speed)
        self.st = st
        self.kind = st["kind"]
        self.goal, self.target = st["goal"], st["target"]
        self.tier = max(0, (self.stage_n - 1) // 10)
        self.theme = NS.THEMES[st["theme"]]
        self.tiles = list(st["map"])
        self.stars = [c for c, ch in enumerate(self.tiles) if ch == "*"]
        self.foods = [c for c, ch in enumerate(self.tiles) if ch == "d"]
        self.feast_total = len(self.foods)
        for c in self.stars + self.foods:
            self.tiles[c] = "."
        self.stars_total = len(self.stars)
        self.link = NS.portal_map(self.tiles)
        self.rollers = [Roller(r[0], r[1], r[2], r[3], r[4]) for r in st["rollers"]]
        self.vents = [Vent(*v) for v in st["vents"]]
        self.blocks = {}
        self.attacks = []
        self.items = []
        self.boss = Boss(st["boss"]) if self.kind == "boss" else None
        self.boss_set = set(self.boss.cells()) if self.boss and self.boss.kind != "ghost" else set()
        self.gates_open = "G" not in self.tiles
        self.eaten_stage = 0
        self.stage_time = 0.0
        self.deaths = 0
        self.gold_seen = self.gold_missed = self.gold_eaten = 0
        self.since_gold = 0
        self.dash_charges = self.lv("dash")
        self.snips = self.lv("snip")
        self.squeezed = 0
        self.pending = set()
        self.warn_ring = -1
        self.bonus_left = 20.0
        self.tally = []
        self.tally_i = 0
        self.tally_t = 0.0
        self.lucky = False
        self.victory_t = 0.0
        self.milestone = 0
        self.spawn_noodle()
        self.fill_foods()
        self.state = "intro"
        self.state_t = 0.0
        self.cache = None
        if self.kind == "boss":
            self.music = "boss"
            self.app.audio.music("boss")
            self.app.audio.play("warning")
        else:
            self.music = "bonus" if self.kind == "bonus" else "noodle"
            self.app.audio.music(self.music)
            self.app.audio.play("stage")

    def spawn_noodle(self):
        x, y = self.st["sp"]
        self.body = [y * GW + x - i for i in range(self.st["len"])]
        for c in self.body:
            self.blocks.pop(c, None)
        self.dir = (1, 0)
        self.queue = []
        self.grow = 0
        self.step_t = 0.0
        self.slurp = 0.0
        self.ghost_t = self.dash_t = self.magnet_t = 0.0
        self.invuln = 0.0
        self.dead = False

    # ---------------------------------------------------------------- queries
    def head(self):
        return self.body[0]

    def solid(self, c):
        ch = self.tiles[c]
        return ch == "#" or ch == "G" or c in self.blocks or c in self.boss_set

    def safe(self):
        return self.invuln > 0 or self.ghost_t > 0 or self.dash_t > 0 or self.state in ("bossdown", "victory")

    def roller_at(self, c):
        for r in self.rollers:
            if r.alive and r.cell == c:
                return r
        return None

    def deadly(self, c):
        """Something that hurts the head on this cell right now (besides walls and the body)."""
        r = self.roller_at(c)
        if r is not None and r.kind != "gold":
            return True
        for v in self.vents:
            if c in v.beam and v.state(self.stage_time) == 2:
                return True
        for a in self.attacks:
            if a.kind in ("row", "col") and a.live and c in a.cells:
                return True
        b = self.boss
        if b and b.kind == "ghost" and not b.dead and c in b.cells():
            return True
        return False

    def magnet_r(self):
        r = self.lv("magnet") + (2 if self.magnet_t > 0 else 0)
        if self.hype.fever_on:
            r += 2
        return r

    def step_time(self):
        if self.campaign:
            s = self.st["step"] * SPEED_MULT[self.speed] - min(0.012, self.eaten_stage * 0.0006)
        else:
            s = STEP[self.speed] - min(0.06, self.total_eaten * 0.0015)
        s *= 1 - 0.07 * self.lv("calm")
        if self.dash_t > 0:
            s /= 3
        return max(0.045, s)

    def reach_cells(self):
        """Cells the noodle can currently get to (for spawning food it can actually eat)."""
        seen = {self.head()}
        stack = [self.head()]
        wrap = self.mode == "wrap"
        while stack:
            c = stack.pop()
            x, y = cxy(c)
            for dx, dy in NS.D4:
                nx, ny = x + dx, y + dy
                if wrap:
                    nx, ny = nx % GW, ny % GH
                elif not (0 <= nx < GW and 0 <= ny < GH):
                    continue
                n = ny * GW + nx
                if n in seen or self.solid(n) or n in self.pending:
                    continue
                seen.add(n)
                stack.append(n)
                if n in self.link and self.link[n] not in seen:
                    seen.add(self.link[n])
                    stack.append(self.link[n])
        return seen

    def free_cell(self, near=None, far=3, region=None):
        region = region if region is not None else self.reach_cells()
        taken = set(self.body) | set(self.foods) | set(self.stars) | {i.cell for i in self.items}
        taken |= {r.cell for r in self.rollers}
        for v in self.vents:
            taken.update(v.beam)
        for a in self.attacks:
            if a.kind in ("drop", "toss"):
                taken.update(a.cells)
        hx, hy = cxy(self.head())
        cand = []
        for c in region:
            if c in taken or self.tiles[c] not in ".~" or c in self.pending or NS.ring_of(c) <= self.warn_ring:
                continue
            x, y = cxy(c)
            d = abs(x - hx) + abs(y - hy)
            if d < far:
                continue
            if near is not None and abs(x - near[0]) + abs(y - near[1]) > near[2]:
                continue
            cand.append(c)
        if not cand:
            return None
        cand.sort()
        return random.choice(cand)

    def fill_foods(self):
        if self.kind == "bonus":
            return
        want = self.st["foods"] + (2 if self.hype.fever_on else 0)
        region = None
        while len(self.foods) < want:
            region = region if region is not None else self.reach_cells()
            c = self.free_cell(region=region)
            if c is None:
                break
            self.foods.append(c)

    def add_item(self, kind, life=-1.0, look="", cell=None):
        c = cell if cell is not None else self.free_cell()
        if c is None:
            return None
        it = Item(kind, c, life, look)
        self.items.append(it)
        return it

    # ---------------------------------------------------------------- frame
    def tick(self, dt):
        inp = self.app.input
        self.state_t += dt
        self.slurp = max(0.0, self.slurp - dt)
        if self.state in ("intro", "ready", "play", "bossdown", "victory"):
            for name, d in DIRS.items():
                if inp.hit(name) and len(self.queue) < 3:
                    last = self.queue[-1] if self.queue else self.dir
                    if d != last and d != (-last[0], -last[1]):
                        self.queue.append(d)
        self.update_fever()
        if self.score >= self.next_life:
            self.lives += 1
            self.next_life = 80000 if self.next_life < 80000 else self.next_life + 100000
            self.hype.banner("BONUS LIFE!", "+1 NOODLE", color="pink", dur=1.6, sound="extra")
            self.hype.shower(24, "hearts")
        st = self.state
        if st == "intro":
            dur = 4.2 if self.kind == "boss" else 2.2
            if self.state_t >= dur or (self.state_t > 0.6 and inp.hit("a", "start")):
                self.go_play()
        elif st == "ready":
            if self.state_t >= 0.9:
                self.state = "play"
        elif st in ("play", "bossdown", "victory"):
            self.play(dt, inp)
        elif st == "dead":
            if self.state_t >= 1.5:
                if self.lives > 0:
                    self.spawn_noodle()
                    self.invuln = 2.2
                    self.state, self.state_t = "ready", 0.0
                else:
                    self.state = "over"
                    self.hype.banner("GAME OVER", "THANKS FOR SLURPING!", color="pink", dur=1.6)
                    if self.campaign:
                        self.end_game(False, f"STAGE {self.stage_n}", delay=1.4)
                    else:
                        self.end_game(False, f"LENGTH {self.best_len}", delay=1.4)
        elif st == "clear":
            if self.state_t >= 1.6:
                self.state, self.state_t = "tally", 0.0
        elif st == "tally":
            self.update_tally(dt, inp)

    def go_play(self):
        self.state, self.state_t = "play", 0.0
        if self.kind == "boss":
            self.hype.banner("FIGHT!", color="red", dur=0.9, scale=2)
        else:
            self.hype.banner("GO!", color="lime", dur=0.7, scale=2)

    def update_fever(self):
        h = self.hype
        if h.fever_on and not self.fever_boosted:
            self.fever_boosted = True
            h.fever_t += 2.0 * self.lv("fever")
            self.fill_foods()
        elif not h.fever_on:
            self.fever_boosted = False

    def play(self, dt, inp):
        self.stage_time += dt
        for k in ("ghost_t", "dash_t", "magnet_t", "invuln"):
            setattr(self, k, max(0.0, getattr(self, k) - dt))
        if inp.hit("a") and self.state == "play" and self.dash_charges > 0 and self.dash_t <= 0:
            self.dash_charges -= 1
            self.dash_t = 0.6
            self.app.audio.play("jump")
            self.hype.banner("DASH!", color="yellow", dur=0.5, scale=1)
        # timed things
        for it in self.items:
            it.t += dt
            if it.life > 0:
                it.life -= dt
                if it.life <= 0:
                    if it.kind in ("gold", "fortune"):
                        self.gold_missed += 1
                    x, y = cpx(it.cell)
                    self.parts.burst(x + 4, y + 4, 5, ("white", "gray"), 30, 0.4)
        self.items = [i for i in self.items if i.life == -1.0 or i.life > 0]
        for c in list(self.blocks):
            self.blocks[c] -= dt
            if self.blocks[c] <= 0:
                del self.blocks[c]
                x, y = cpx(c)
                self.parts.burst(x + 4, y + 4, 4, ("white", "cream"), 30, 0.4)
        for v in self.vents:
            if v.life > 0:
                v.life -= dt
        self.vents = [v for v in self.vents if v.life == -1.0 or v.life > 0]
        self.update_rollers(dt)
        self.update_attacks(dt)
        if self.boss:
            self.update_boss(dt)
        if self.st["squeeze"]:
            self.update_squeeze()
        if self.state == "victory":
            self.victory_t -= dt
            if self.victory_t <= 0:
                self.stage_clear()
                return
        if self.state == "bossdown":
            if self.state_t >= 1.6:
                self.boss_feast()
        if self.kind == "bonus" and self.state == "play":
            self.bonus_left -= dt
            if self.goal == "rush":
                golds = sum(1 for i in self.items if i.kind in ("gold", "fortune"))
                if golds < 3 and int(self.stage_time * 10) % 4 == 0:
                    kind = "fortune" if self.hype.lucky(0.06) else "gold"
                    self.add_item(kind, 3.2)
            if self.bonus_left <= 0:
                self.bonus_left = 0
                self.hype.banner("TIME UP!", color="yellow", dur=1.2)
                self.stage_clear()
                return
        self.step_t += dt
        guard = 0
        while self.step_t >= self.step_time() and self.state in ("play", "bossdown", "victory") and guard < 4 \
                and not self.dead:
            self.step_t -= self.step_time()
            guard += 1
            self.advance()
        if self.state in ("play", "bossdown", "victory") and not self.safe() and self.deadly(self.head()):
            self.crash()
        if self.state == "play":
            self.fill_foods()
            self.check_goal()

    # ---------------------------------------------------------------- movement
    def advance(self):
        au = self.app.audio
        h = self.head()
        on = self.tiles[h]
        if on in NS.ARROWS:
            d = NS.ARROWS[on]
            if d != (-self.dir[0], -self.dir[1]):
                self.dir = d
        elif on != "~" and self.queue:
            self.dir = self.queue.pop(0)
        hx, hy = cxy(h)
        nx, ny = hx + self.dir[0], hy + self.dir[1]
        if self.mode == "wrap":
            nx, ny = nx % GW, ny % GH
        if not (0 <= nx < GW and 0 <= ny < GH):
            self.crash()
            return
        c = ny * GW + nx
        if c in self.link:
            c = self.link[c]
            x, y = cpx(c)
            self.parts.burst(x + 4, y + 4, 8, PORTAL_COLORS[self.tiles[c]], 40, 0.4)
            au.play("bubble")
        if self.solid(c):
            self.crash()
            return
        tail_moves = self.grow == 0
        check = self.body[:-1] if tail_moves else self.body
        if c in check:
            i = self.body.index(c)
            ghost_n = 4 * self.lv("ghost")
            if self.ghost_t > 0 or (ghost_n > 0 and i >= len(self.body) - ghost_n):
                pass
            elif self.snips > 0 and i >= 2:
                self.snips -= 1
                cut = self.body[i:]
                self.body = self.body[:i]
                for k in cut:
                    x, y = cpx(k)
                    self.parts.burst(x + 4, y + 4, 2, ("cream", "white", "pink"), 40, 0.5)
                au.play("pop")
                self.hype.banner("SNIP!", color="pink", dur=0.6, scale=1)
            else:
                self.crash()
                return
        gold_plate = self.roller_at(c)
        if gold_plate is not None and gold_plate.kind == "gold":
            gold_plate.alive = False
            self.boss_hit(c)
        elif not self.safe() and self.deadly(c):
            self.crash()
            return
        self.body.insert(0, c)
        if self.grow > 0:
            self.grow -= 1
        else:
            self.body.pop()
        if len(self.body) > self.best_len:
            self.best_len = len(self.body)
        if self.dash_t > 0:
            x, y = cpx(c)
            self.parts.burst(x + 4, y + 4, 2, ("yellow", "white"), 20, 0.3, grav=0)
        self.eat_at(c, False)
        r = self.magnet_r()
        if r > 0:
            hx, hy = cxy(c)
            for k in list(self.foods) + [i.cell for i in self.items if i.kind in ("gold", "fortune", "weak")]:
                x, y = cxy(k)
                if 0 < abs(x - hx) + abs(y - hy) <= r:
                    self.eat_at(k, True)
        self.check_length()
        if self.boss and self.boss.kind == "ghost":
            self.check_trap()

    def eat_at(self, c, pulled):
        au = self.app.audio
        x, y = cpx(c)
        if pulled:
            hx, hy = cpx(self.head())
            for k in range(4):
                u = k / 4
                self.parts.sparkle(x + 4 + (hx - x) * u, y + 4 + (hy - y) * u, "pink")
        if c in self.foods:
            self.foods.remove(c)
            self.eat_dumpling(c)
        for it in [i for i in self.items if i.cell == c]:
            self.items.remove(it)
            if it.kind == "gold":
                self.gold_eaten += 1
                self.grow += 3
                self.slurp = 0.4
                combo = self.hype.hit(2, fever=0.15 * (1 + 0.35 * self.lv("fever")))
                self.hype.combo_t += 0.6 * self.lv("combo")
                base = 150 + self.hype.combo_bonus(5) if self.goal == "rush" else 200 + 30 * self.tier
                self.add(base, x + 4, y - 4, "mint")
                au.play("bonus")
                self.parts.burst(x + 4, y + 4, 14, ("yellow", "white", "orange"), 60, 0.7)
                if self.goal == "rush":
                    self.eaten_stage += 1
            elif it.kind == "fortune":
                self.gold_eaten += 1
                self.grow += 3
                self.hype.hit(3)
                self.hype.jackpot(1500 + 300 * self.tier, "FORTUNE DUMPLING!")
                if self.goal == "rush":
                    self.eaten_stage += 1
            elif it.kind == "tea":
                self.ghost_t = 5.0
                au.play("powerup")
                self.add(50, x + 4, y - 4, "lavender")
                self.hype.banner("GHOST TEA!", "PASS THROUGH ANYTHING", color="lavender", dur=1.1, scale=1)
            elif it.kind == "chili":
                au.play("powerup")
                self.add(50, x + 4, y - 4, "orange")
                self.hype.banner("HOT CHILI!", "FEVER UP", color="orange", dur=1.0, scale=1)
                self.hype.fever_add(0.5)
            elif it.kind == "magnet":
                self.magnet_t = 8.0
                au.play("powerup")
                self.add(50, x + 4, y - 4, "red")
                self.hype.banner("MAGNET!", color="red", dur=1.0, scale=1)
            elif it.kind == "weak":
                self.boss_hit(c)
        if c in self.stars:
            self.stars.remove(c)
            self.hype.hit(1, fever=0.08 * (1 + 0.35 * self.lv("fever")))
            self.hype.combo_t += 0.6 * self.lv("combo")
            self.add(100 + 20 * self.tier, x + 4, y - 4, "orange")
            au.play("fruit")
            self.parts.burst(x + 4, y + 4, 12, ("red", "orange", "yellow"), 60, 0.6)
            left = len(self.stars)
            if 0 < left <= 2:
                self.floats.add(W // 2, OY + 70, f"{left} MORE!", "orange")

    def eat_dumpling(self, c):
        au = self.app.audio
        x, y = cpx(c)
        self.eaten_stage += 1
        self.total_eaten += 1
        self.slurp = 0.25
        self.hype.hit(1, fever=0.06 * (1 + 0.35 * self.lv("fever")))
        self.hype.combo_t += 0.6 * self.lv("combo")
        if self.kind == "bonus":
            self.grow += 1 if self.eaten_stage % 2 == 0 else 0
            pts = 30 + self.hype.combo_bonus(3)
            if not self.foods:
                self.hype.jackpot(10000, "ALL SLURPED!")
                self.stage_clear()
        else:
            self.grow += 2
            pts = (10 + 5 * self.tier if self.campaign else 10 + self.total_eaten // 5) + self.hype.combo_bonus(2)
        self.add(pts, x + 4, y - 4)
        au.play("eat")
        self.parts.burst(x + 4, y + 4, 5, ("cream", "peach", "white"), 40, 0.4)
        if self.kind == "bonus":
            return
        # golden / fortune / power-up drops
        self.since_gold += 1
        has_gold = any(i.kind in ("gold", "fortune") for i in self.items)
        if not has_gold and (self.since_gold >= 6 - self.lv("gold") or random.random() < 0.10 + 0.06 * self.lv("gold")):
            self.since_gold = 0
            if self.hype.lucky(0.03):
                it = self.add_item("fortune", 5.0)
            else:
                it = self.add_item("gold", 6.0 + 2.0 * self.lv("goldtime"))
            if it:
                self.gold_seen += 1
                au.play("bonus")
        if not any(i.kind in ("tea", "chili", "magnet") for i in self.items) and random.random() < 0.07:
            self.add_item(random.choice(("tea", "chili", "magnet")), 8.0)
        if not self.gates_open and self.eaten_stage >= self.st["gate"]:
            self.open_gates()
        if not self.campaign and self.total_eaten % 25 == 0:
            self.pick_upgrade(POOL, self.up, self.on_pick, title="SNACK BREAK!")

    def check_length(self):
        n = len(self.body)
        for m in MILESTONES:
            if n >= m > self.milestone:
                self.milestone = m
                if m >= 30 or not self.campaign:
                    pts = self.add(50 * m)
                    self.hype.banner(f"LENGTH {m}!", f"+{pts}", color="mint", dur=1.3, sound="levelup")
                    self.hype.shower(10 + m // 3, "stars")

    def open_gates(self):
        self.gates_open = True
        for c, ch in enumerate(self.tiles):
            if ch == "G":
                self.tiles[c] = "."
                x, y = cpx(c)
                self.parts.burst(x + 4, y + 4, 4, ("brown", "yellow", "white"), 50, 0.6)
        self.cache = None
        self.hype.banner("DOORS OPEN!", color="yellow", dur=1.2, sound="levelup")
        self.app.shake(2, 0.2)

    def crash(self):
        if self.state not in ("play", "bossdown", "victory"):
            return
        au = self.app.audio
        if self.state in ("bossdown", "victory"):   # no life lost once the boss is down
            self.dead = True
            self.victory_t = min(self.victory_t, 0.8)
            au.play("hurt")
            return
        self.dead = True
        au.play("hurt")
        self.app.shake(3, 0.3)
        self.hype.break_combo()
        self.hype.flash("red", 0.15)
        for c in self.body:
            x, y = cpx(c)
            self.parts.burst(x + 4, y + 4, 2, ("cream", "peach", "white"), 50, 0.8)
        if self.kind == "bonus":
            self.hype.banner("OOPS!", "BONUS OVER", color="pink", dur=1.2)
            self.stage_clear()
            return
        self.deaths += 1
        self.lives -= 1
        self.state, self.state_t = "dead", 0.0
        self.attacks = [a for a in self.attacks if a.kind not in ("row", "col")]

    def check_goal(self):
        g = self.goal
        done = False
        if g == "eat":
            done = self.eaten_stage >= self.target
        elif g == "stars":
            done = not self.stars
        elif g == "length":
            done = len(self.body) >= self.target
        elif g == "survive":
            done = self.stage_time >= self.target
        if done:
            self.stage_clear()

    # ---------------------------------------------------------------- hazards
    def roller_blocked(self, c, me):
        if self.solid(c):
            return True
        for r in self.rollers:
            if r is not me and r.alive and r.cell == c:
                return True
        return False

    def update_rollers(self, dt):
        body_rest = set(self.body[1:])
        for r in self.rollers:
            if not r.alive:
                continue
            r.spin += dt * 10
            r.acc += dt
            if r.acc < r.period:
                continue
            r.acc -= r.period
            nx, ny = r.x + r.dx, r.y + r.dy
            ball = r.kind == "ball"
            if not (0 <= nx < GW and 0 <= ny < GH):
                if ball:
                    r.dx, r.dy = -r.dx, -r.dy
                else:
                    r.alive = False
                continue
            c = ny * GW + nx
            if c == self.head():
                if r.kind == "gold":
                    r.alive = False
                    self.boss_hit(c)
                    continue
                if not self.safe():
                    r.x, r.y = nx, ny
                    self.crash()
                    continue
            if self.roller_blocked(c, r) or c in body_rest or c == self.head():
                if ball:
                    r.dx, r.dy = -r.dx, -r.dy
                    bx, by = r.x + r.dx, r.y + r.dy
                    if 0 <= bx < GW and 0 <= by < GH and not self.roller_blocked(by * GW + bx, r) and \
                            by * GW + bx not in body_rest and by * GW + bx != self.head():
                        r.x, r.y = bx, by
                else:
                    r.alive = False
                    x, y = cpx(c)
                    self.parts.burst(x + 4, y + 4, 8, ("white", "red", "yellow") if r.kind != "slip" else ("white", "cream"),
                                     50, 0.5)
                    if c in body_rest:
                        self.add(50, x + 4, y - 4, "white")
                        self.app.audio.play("brick")
                continue
            r.x, r.y = nx, ny
        self.rollers = [r for r in self.rollers if r.alive]

    def update_squeeze(self):
        t0, iv = self.st["squeeze"]
        k = self.squeezed
        if k < 3:
            close = t0 + k * iv
            if self.stage_time >= close - 2.0:
                self.warn_ring = k
            if self.stage_time >= close:
                self.squeezed += 1
                self.pending |= {c for c in range(GW * GH) if NS.ring_of(c) == k and self.tiles[c] != "#"}
                self.hype.banner("SQUEEZE!", color="orange", dur=0.9, scale=1)
                self.app.audio.play("lock")
                self.app.shake(2, 0.2)
        if self.pending:
            body = set(self.body)
            done = [c for c in self.pending if c not in body]
            for c in done:
                self.pending.discard(c)
                self.tiles[c] = "#"
                if c in self.foods:
                    self.foods.remove(c)
            if done:
                self.items = [i for i in self.items if i.cell not in done]
                for r in self.rollers:
                    if r.cell in done:
                        r.alive = False
                self.cache = None

    # ---------------------------------------------------------------- boss
    def update_boss(self, dt):
        b = self.boss
        b.t += dt
        for k in ("flash", "stun", "inv", "anim", "lid"):
            setattr(b, k, max(0.0, getattr(b, k) - dt))
        if b.dead or self.state != "play":
            return
        if b.kind == "crab":
            b.move_t += dt
            if b.move_t >= b.move * 1.6:
                b.move_t = 0.0
                nx = b.x + b.mdir
                if nx < 1 or nx + b.w > GW - 1:
                    b.mdir = -b.mdir
                    nx = b.x + b.mdir
                b.x = nx
                self.boss_set = set(b.cells())
                if self.head() in self.boss_set and not self.safe():
                    self.crash()
        elif b.kind == "ghost":
            self.ghost_move(dt)
        weak = any(i.kind == "weak" for i in self.items) or any(a.gold >= 0 or a.kind == "toss" for a in self.attacks) \
            or any(r.kind == "gold" for r in self.rollers)
        b.weak_wait = 0.0 if weak else b.weak_wait + dt
        b.cd -= dt * (1.3 if b.angry else 1.0)
        if b.cd > 0 or b.stun > 0:
            return
        b.cd = b.cool * (0.75 if b.angry else 1.0)
        if b.kind != "ghost" and not weak and (b.weak_wait > 3.5 or random.random() < 0.5):
            name = WEAK_ATTACK[b.kind]
        else:
            opts = [p for p in b.pool if p != b.last] or b.pool
            name = random.choice(opts)
        b.last = name
        b.anim = 0.6
        self.boss_attack(name)

    def lines_near(self, n, rows, lo, hi):
        hx, hy = cxy(self.head())
        target = hy if rows else hx
        pool = [k for k in range(lo, hi) if k != target]
        random.shuffle(pool)
        out = []
        if lo <= target < hi and random.random() < 0.6:
            out.append(target)
        for k in pool:
            if len(out) >= n:
                break
            if all(abs(k - o) > 1 for o in out):
                out.append(k)
        return out

    def boss_attack(self, name):
        b = self.boss
        au = self.app.audio
        tele = b.tele
        top = b.y + b.h if b.kind != "ghost" else 0
        style = {"crab": "ladle", "teapot": "steam", "golem": "quake", "bao": "ladle"}.get(b.kind, "ladle")
        bx, by = b.center()
        if name in ("sweep", "quake"):
            n = 1 + (1 if b.angry else 0) + (1 if b.lvl >= 2 else 0)
            for y in self.lines_near(n, True, top + 1, GH):
                self.attacks.append(Attack("row", [y * GW + x for x in range(GW)], tele, 0.45,
                                           "quake" if name == "quake" else style))
        elif name == "csweep":
            n = 1 + (1 if b.angry else 0)
            for x in self.lines_near(n, False, 0, GW):
                self.attacks.append(Attack("col", [y * GW + x for y in range(top, GH)], tele, 0.45, style))
        elif name == "beam":
            hx, _ = cxy(self.head())
            x0 = max(0, min(GW - 2, hx - (1 if random.random() < 0.5 else 0)))
            cells = [y * GW + x for y in range(top, GH) for x in (x0, x0 + 1)]
            self.attacks.append(Attack("col", cells, tele, 1.0, "steam", gold=1 if b.kind == "teapot" else -1))
        elif name == "toss":
            k = 2 + (1 if b.angry else 0)
            for _ in range(k):
                c = self.free_cell(far=3)
                if c is not None:
                    self.attacks.append(Attack("toss", [c], 0.8, src=(bx, by)))
            au.play("jump")
        elif name == "drop":
            k = 4 + 2 * b.lvl + (2 if b.angry else 0)
            hx, hy = cxy(self.head())
            cells = []
            for i in range(k):
                c = self.free_cell(near=(hx, hy, 5) if i % 2 == 0 else None, far=2)
                if c is not None and c not in cells:
                    cells.append(c)
            if cells:
                gold = random.randrange(len(cells)) if b.kind == "golem" else -1
                self.attacks.append(Attack("drop", cells, tele + 0.25, gold=gold))
        elif name == "plates":
            k = 2 + b.lvl + (1 if b.angry else 0)
            rows = self.lines_near(k, True, top + 1, GH)
            golds = 1 if b.kind in ("sushi", "bao") else 0
            for i, y in enumerate(rows):
                if b.kind == "sushi" and b.lvl >= 1 and i % 2 == 1:
                    x = random.randrange(GW)
                    cell, dx, dy = (GH - 1) * GW + x, 0, -1
                else:
                    left = random.random() < 0.5
                    cell, dx, dy = y * GW + (0 if left else GW - 1), (1 if left else -1), 0
                g = 1 if i < golds else -1
                self.attacks.append(Attack("plate", [cell], 0.9 + i * 0.35, dx=dx, dy=dy, gold=g))
        elif name == "vents":
            k = 2 + (1 if b.angry else 0)
            for _ in range(k):
                c = self.free_cell(far=4)
                if c is None:
                    continue
                x, y = cxy(c)
                dx, dy = random.choice(NS.D4)
                ln = 0
                while ln < 3 and 0 <= x + dx * (ln + 1) < GW and 0 <= y + dy * (ln + 1) < GH and \
                        not self.solid((y + dy * (ln + 1)) * GW + x + dx * (ln + 1)):
                    ln += 1
                if ln >= 1:
                    self.vents.append(Vent(x, y, dx, dy, ln, 2.4, 0.4 - self.stage_time % 2.4, 7.5))
        elif name == "dash":
            hx, hy = cxy(self.head())
            dx = (1 if hx > b.x else -1) if abs(hx - b.x) >= abs(hy - b.y) else 0
            dy = 0 if dx else (1 if hy > b.y else -1)
            cells = []
            x, y = b.x, b.y
            for _ in range(6):
                x, y = x + dx, y + dy
                if not (0 <= x <= GW - b.w and 0 <= y <= GH - b.h):
                    break
                cells += [(y + j) * GW + x + i for j in range(b.h) for i in range(b.w)]
            self.attacks.append(Attack("dash", cells, 0.75, dx=dx, dy=dy))
        elif name == "slips":
            for dx, dy in NS.D4:
                x = b.x + (b.w if dx > 0 else -1 if dx < 0 else 0)
                y = b.y + (b.h if dy > 0 else -1 if dy < 0 else 0)
                if 0 <= x < GW and 0 <= y < GH:
                    self.attacks.append(Attack("plate", [y * GW + x], 0.5, dx=dx, dy=dy, gold=-2))

    def update_attacks(self, dt):
        au = self.app.audio
        keep = []
        for a in self.attacks:
            a.t += dt
            if a.kind in ("row", "col"):
                if a.t >= a.tele and not a.fired:
                    a.fired = True
                    au.play("shoot" if a.style == "ladle" else "explode" if a.style == "quake" else "bubble")
                    if a.style == "quake":
                        self.app.shake(2, 0.2)
                if a.t >= a.tele + a.act:
                    if a.gold >= 0 and self.boss and not self.boss.dead:
                        self.spawn_sugar()
                    continue
            elif a.kind == "toss" and a.t >= a.tele:
                c = a.cells[0]
                if c == self.head() and not self.safe():
                    self.crash()
                look = WEAK_LOOK.get(self.boss.kind if self.boss else "crab", "chili")
                self.items.append(Item("weak", c, 9.0, look))
                if c in self.foods:
                    self.foods.remove(c)
                continue
            elif a.kind == "drop" and a.t >= a.tele:
                body = set(self.body[1:])
                for i, c in enumerate(a.cells):
                    x, y = cpx(c)
                    if i == a.gold:
                        self.items.append(Item("weak", c, 7.0, "bean"))
                        continue
                    if c == self.head() and not self.safe():
                        self.crash()
                    if c in body or c == self.head():
                        self.parts.burst(x + 4, y + 4, 6, ("white", "cream"), 40, 0.4)
                        continue
                    self.blocks[c] = 6.0
                    if c in self.foods:
                        self.foods.remove(c)
                    self.items = [it for it in self.items if it.cell != c]
                    self.parts.burst(x + 4, y + 7, 4, ("white", "gray"), 30, 0.3)
                au.play("lock")
                self.app.shake(2, 0.15)
                continue
            elif a.kind == "plate" and a.t >= a.tele:
                x, y = cxy(a.cells[0])
                kind = "gold" if a.gold == 1 else "slip" if a.gold == -2 else "plate"
                r = Roller(x, y, a.dx, a.dy, max(0.07, 0.12 - 0.002 * self.tier) if kind != "slip" else 0.13, kind)
                if a.cells[0] == self.head():
                    if kind == "gold":
                        self.boss_hit(a.cells[0])
                        continue
                    if not self.safe():
                        self.crash()
                self.rollers.append(r)
                au.play("shoot")
                continue
            elif a.kind == "dash" and a.t >= a.tele:
                if self.boss:
                    self.boss.dash = 6
                    self.boss.ddx, self.boss.ddy = a.dx, a.dy
                    self.boss.move_t = 0.0
                continue
            keep.append(a)
        self.attacks = keep

    def spawn_sugar(self):
        b = self.boss
        cx = b.x + b.w // 2
        c = self.free_cell(near=(cx, b.y + b.h + 2, 4), far=2)
        if c is None:
            c = self.free_cell(far=2)
        if c is not None:
            self.items.append(Item("weak", c, 4.5 + b.lvl * 0.5, "sugar"))
            b.lid = 4.5
            x, y = cpx(c)
            self.parts.burst(x + 4, y + 4, 10, ("white", "sky"), 40, 0.5)
            self.app.audio.play("pop")

    def ghost_move(self, dt):
        b = self.boss
        if b.stun > 0:
            return
        b.move_t += dt
        period = 0.05 if b.dash > 0 else b.move * (0.75 if b.angry else 1.0)
        if b.move_t < period:
            return
        b.move_t = 0.0
        body = set(self.body[1:])
        hx, hy = cxy(self.head())

        def fits(x, y):
            if not (0 <= x <= GW - b.w and 0 <= y <= GH - b.h):
                return False
            return not any((y + j) * GW + x + i in body for j in range(b.h) for i in range(b.w))
        if b.dash > 0:
            b.dash -= 1
            nx, ny = b.x + b.ddx, b.y + b.ddy
            if not fits(nx, ny):
                b.dash = 0
                return
        else:
            opts = []
            for dx, dy in NS.D4:
                if fits(b.x + dx, b.y + dy):
                    cx, cy = b.x + dx + 0.5, b.y + dy + 0.5
                    opts.append((abs(cx - hx) + abs(cy - hy) + random.random() * 1.5, dx, dy))
            if not opts:
                return
            opts.sort()
            _, dx, dy = opts[0]
            nx, ny = b.x + dx, b.y + dy
        b.x, b.y = nx, ny
        if self.head() in b.cells() and not self.safe():
            self.crash()
            return
        self.check_trap()

    def check_trap(self):
        """FORTUNE SPOOK: hurt it by sealing it in with the noodle (board edges count as walls)."""
        b = self.boss
        if b.dead or b.inv > 0 or b.stun > 0:
            return
        body = set(self.body)
        start = [c for c in b.cells() if c not in body]
        seen = set(start)
        stack = list(start)
        while stack and len(seen) <= 70:
            c = stack.pop()
            x, y = cxy(c)
            for dx, dy in NS.D4:
                nx, ny = x + dx, y + dy
                if 0 <= nx < GW and 0 <= ny < GH:
                    n = ny * GW + nx
                    if n not in seen and n not in body:
                        seen.add(n)
                        stack.append(n)
        if len(seen) <= 70:
            b.stun = 1.2
            b.inv = 2.6
            self.boss_hit(b.y * GW + b.x)
            self.hype.banner("TRAPPED!", color="lavender", dur=0.9, scale=1)

    def ghost_warp(self):
        b = self.boss
        body = set(self.body)
        hx, hy = cxy(self.head())
        best = None
        for _ in range(40):
            x, y = random.randrange(GW - 1), random.randrange(GH - 1)
            if any((y + j) * GW + x + i in body for j in range(2) for i in range(2)):
                continue
            d = abs(x - hx) + abs(y - hy)
            if best is None or d > best[0]:
                best = (d, x, y)
        if best:
            px, py = b.center()
            self.parts.burst(px, py, 16, ("white", "lavender", "yellow"), 60, 0.6)
            b.x, b.y = best[1], best[2]

    def boss_hit(self, c):
        b = self.boss
        if b is None or b.dead:
            return
        b.hp -= 1
        b.flash = 0.25
        x, y = cpx(c)
        self.add(500, x + 4, y - 4, "red")
        self.hype.hit(2)
        self.hype.flash("white", 0.12)
        self.hype.hitstop(0.08)
        self.app.shake(3, 0.25)
        self.app.audio.play("explode")
        bx, by = b.center()
        self.parts.burst(bx, by, 18, ("white", "yellow", "red", "orange"), 80, 0.7)
        if b.kind == "ghost" and b.hp > 0:
            self.ghost_warp()
        if b.hp <= b.maxhp // 2 and not b.angry and b.hp > 0:
            b.angry = True
            self.hype.banner("IT'S ANGRY!", color="red", dur=1.0, scale=1)
        if b.hp <= 0:
            self.boss_defeat()

    def boss_defeat(self):
        b = self.boss
        b.dead = True
        b.hp = 0
        self.attacks = []
        self.rollers = []
        self.vents = []
        self.blocks = {}
        self.items = [i for i in self.items if i.kind != "weak"]
        self.app.audio.play("bossdown")
        self.hype.slowmo(0.3, 1.4)
        self.hype.flash("white", 0.4)
        self.hype.shower(70, "stars")
        self.hype.banner("BOSS DOWN!!", b.name, rainbow=True, dur=2.2)
        self.app.shake(6, 0.9)
        self.state, self.state_t = "bossdown", 0.0
        self.cache = None

    def boss_feast(self):
        """The defeated boss bursts into golden dumplings - slurp as many as you can!"""
        b = self.boss
        bx, by = b.center()
        self.parts.burst(bx, by, 40, ("yellow", "white", "orange", "pink"), 110, 1.0)
        self.boss_set = set()
        region = self.reach_cells()
        hx, hy = cxy(self.head())
        for _ in range(12):
            c = self.free_cell(near=(b.x + b.w // 2, b.y + b.h // 2, 8), far=2, region=region)
            if c is None:
                break
            self.items.append(Item("gold", c, 5.0))
        self.state, self.state_t = "victory", 0.0
        self.victory_t = 0.8 if self.dead else 5.0
        self.hype.banner("GOLDEN FEAST!", "SLURP THEM UP!", color="yellow", dur=1.4, scale=1)
        self.app.audio.play("coin")

    # ---------------------------------------------------------------- clear / tally
    def stage_clear(self):
        if self.state in ("clear", "tally", "pick", "over"):
            return
        self.state, self.state_t = "clear", 0.0
        t = self.tier
        lines = []
        if self.kind == "stage":
            lines.append(["CLEAR BONUS", 500 + 100 * t])
            if self.goal == "survive":
                lines.append(["DUMPLINGS", 50 * self.eaten_stage])
            else:
                lines.append(["TIME BONUS", max(0, int(self.st["par"] - self.stage_time)) * (20 + 5 * t)])
            lines.append(["NO MISS", 1000 + 200 * t if self.deaths == 0 else 0])
            perfect = self.deaths == 0 and self.gold_missed == 0 and self.gold_seen > 0
            lines.append(["PERFECT!", 3000 + 500 * t if perfect else 0])
            self.hype.banner("STAGE CLEAR!", rainbow=True, dur=1.5, sound="win")
            self.hype.shower(40, "confetti")
        elif self.kind == "boss":
            lines.append(["BOSS BONUS", 10000 * (1 + self.boss.lvl)])
            lines.append(["TIME BONUS", max(0, int(self.st["par"] - self.stage_time)) * 50])
            lines.append(["NO MISS", 5000 + 1000 * t if self.deaths == 0 else 0])
            lines.append(["GOLD SLURPED", 300 * self.gold_eaten])
            self.app.audio.play("win")
        elif self.kind == "bonus":
            if self.goal == "feast":
                got = self.feast_total - len(self.foods)
                lines.append([f"SLURPED {got}/{self.feast_total}", 100 * got])
                lines.append(["ALL SLURPED!", 10000 if not self.foods else 0])
            else:
                lines.append([f"GOLDEN X{self.eaten_stage}", 300 * self.eaten_stage])
            lines.append(["BEST COMBO", 50 * self.hype.best_combo])
            if not self.dead:
                self.app.audio.play("win")
        else:
            self.end_game(False, f"LENGTH {self.best_len}")
            return
        self.lucky = self.campaign and self.hype.lucky(0.03)
        if self.lucky:
            for ln in lines:
                ln[1] *= 3
        self.tally = [[a, b, 0] for a, b in lines]
        self.tally_i = 0
        self.tally_t = 0.0
        self.attacks = []

    def update_tally(self, dt, inp):
        fast = inp.hit("a", "start")
        if self.state_t < 0.3:
            return
        if self.lucky and self.tally_i == 0 and self.tally_t == 0:
            self.hype.jackpot(0, "LUCKY BOWL! X3")
        self.tally_t += dt
        if self.tally_i < len(self.tally):
            ln = self.tally[self.tally_i]
            step = max(1, ln[1] // 25)
            if fast:
                step = ln[1]
            if ln[2] < ln[1]:
                d = min(step, ln[1] - ln[2])
                ln[2] += d
                self.score += d
                if int(self.tally_t * 30) % 3 == 0:
                    self.app.audio.play("move")
            if ln[2] >= ln[1]:
                self.tally_i += 1
                self.tally_t = 0.0
                if ln[1] > 0:
                    self.app.audio.play("coin")
            return
        if self.tally_t > 1.2 or (fast and self.tally_t > 0.2):
            self.after_tally()

    def after_tally(self):
        if self.kind in ("boss", "bonus") and self.stage_n < STAGES:
            self.state = "pick"
            self.pick_upgrade(POOL, self.up, self.on_pick, title="POWER UP!" if self.kind == "boss" else "BONUS PRIZE!")
        else:
            self.next_stage()

    def on_pick(self, uid):
        if uid:
            self.up[uid] = self.up.get(uid, 0) + 1
            if uid == "life":
                self.lives += 1
            if uid == "dash":
                self.dash_charges += 1
            if uid == "snip":
                self.snips += 1
        if self.campaign and self.state == "pick":
            self.next_stage()

    def next_stage(self):
        if self.stage_n >= STAGES:
            self.state = "over"
            self.hype.jackpot(100000, "ALL 200 STAGES!")
            self.end_game(True, "ALL 200 STAGES CLEAR!", delay=4.0)
            return
        self.stage_n += 1
        self.begin_stage()

    # ---------------------------------------------------------------- drawing
    def render(self, s):
        if self.cache is None:
            self.cache = self.build_cache()
        s.blit(self.cache, (0, 0))
        t = self.t
        self.draw_tiles(s, t)
        self.draw_attacks(s, t, False)
        shade = col(self.theme[6])
        for c in self.foods:
            x, y = cpx(c)
            s.fill(shade, (x + 1, y + 7, 6, 1))
            cute.dumpling(s, x, y - int(abs(math.sin(t * 5 + c)) * 1), t=t)
        for c in self.stars:
            x, y = cpx(c)
            bob = int(math.sin(t * 4 + c * 0.7) * 1)
            s.fill(shade, (x + 1, y + 7, 6, 1))
            s.blit(sprite("star", remap={"y": "r" if int(t * 4 + c) % 4 else "o"}), (x, y + bob))
            if int(t * 3 + c) % 5 == 0:
                s.fill(col("white"), (x + 6, y + bob, 1, 1))
        for it in self.items:
            self.draw_item(s, it, t)
        for r in self.rollers:
            self.draw_roller(s, r, t)
        self.draw_noodle(s)
        if self.boss:
            self.draw_boss(s, t)
        self.draw_attacks(s, t, True)
        self.parts.draw(s)
        self.floats.draw(s)
        self.draw_hud(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "ready" and int(t * 6) % 2 == 0:
            draw_text(s, "READY?", W // 2, OY + 64, "yellow", 2, align="center", outline="ink")
        elif self.state in ("tally",):
            self.draw_tally(s, t)

    def build_cache(self):
        th = self.theme
        surf = pygame.Surface((W, H))
        surf.fill(col(th[1]))
        rnd = random.Random(self.stage_n * 31 + 7)
        deco = col(th[2])
        for i in range(70):
            x, y = rnd.randrange(W), rnd.randrange(H)
            if OX - 6 < x < OX + GW * C + 6 and OY - 6 < y < OY + GH * C + 6:
                continue
            k = i % 3
            if k == 0:
                surf.fill(deco, (x, y, 2, 2))
            elif k == 1:
                surf.fill(deco, (x, y, 1, 1))
            else:
                surf.fill(deco, (x - 1, y, 3, 1))
                surf.fill(deco, (x, y - 1, 1, 3))
        # dark HUD bands keep the score row and the goal row readable on every theme
        surf.fill(col("black"), (0, 0, W, 13))
        surf.fill(deco, (0, 13, W, 1))
        surf.fill(col("black"), (0, OY + GH * C + 4, W, H - (OY + GH * C + 4)))
        surf.fill(deco, (0, OY + GH * C + 4, W, 1))
        panel(surf, (OX - 3, OY - 3, GW * C + 6, GH * C + 6), fill=th[3], border=th[5], radius=3)
        fb = col(th[4])
        for y in range(GH):
            for x in range(GW):
                if (x // 2 + y // 2) % 2 == 0:
                    surf.fill(fb, (OX + x * C, OY + y * C, C, C))
        wall, shade, acc = col(th[5]), col(th[6]), col(th[7])
        for c, ch in enumerate(self.tiles):
            x, y = cpx(c)
            if ch == "#":
                surf.fill(wall, (x, y, C, C))
                gx, gy = cxy(c)
                if gy + 1 >= GH or self.tiles[c + GW] != "#":
                    surf.fill(shade, (x, y + C - 2, C, 2))
                if gy == 0 or self.tiles[c - GW] != "#":
                    surf.fill(acc, (x, y, C, 1))
                if (gx + gy) % 3 == 0:
                    surf.fill(shade, (x + 2, y + 3, 1, 1))
            elif ch == "G":
                surf.fill(col("brown"), (x, y, C, C))
                surf.fill(col("choco"), (x, y + 2, C, 1))
                surf.fill(col("choco"), (x, y + 5, C, 1))
                surf.fill(col("yellow"), (x + 3, y + 3, 2, 2))
            elif ch == "~":
                surf.fill(col("sky"), (x, y, C, C))
                gx, gy = cxy(c)
                for k in range(0, C, 4):
                    pygame.draw.line(surf, col("white"), (x + k, y + C - 1), (x + min(C - 1, k + 3), y + C - 4))
                ice = col("blue")
                if gx == 0 or self.tiles[c - 1] != "~":
                    surf.fill(ice, (x, y, 1, C))
                if gx == GW - 1 or self.tiles[c + 1] != "~":
                    surf.fill(ice, (x + C - 1, y, 1, C))
                if gy == 0 or self.tiles[c - GW] != "~":
                    surf.fill(ice, (x, y, C, 1))
                if gy == GH - 1 or self.tiles[c + GW] != "~":
                    surf.fill(ice, (x, y + C - 1, C, 1))
            elif ch in NS.ARROWS:
                surf.fill(col("darkgray"), (x, y, C, C))
                surf.fill(col("gray"), (x, y, C, 1))
        for v in self.vents:
            if v.life == -1.0:
                x, y = OX + v.x * C, OY + v.y * C
                surf.fill(col("darkgray"), (x, y, C, C))
                for k in range(1, 7, 2):
                    surf.fill(col("black"), (x + 1, y + k, C - 2, 1))
        return surf

    def draw_tiles(self, s, t):
        for c, ch in enumerate(self.tiles):
            if ch in NS.ARROWS:
                x, y = cpx(c)
                dx, dy = NS.ARROWS[ch]
                k = int(t * 8) % 4
                for i in range(2):
                    o = (k + i * 4) % 8 - 4
                    cx, cy = x + 4 + ((dx * o) >> 1), y + 4 + ((dy * o) >> 1)
                    c2 = col("yellow" if i == 0 else "orange")
                    pygame.draw.line(s, c2, (cx - dy * 2 - dx * 2, cy - dx * 2 - dy * 2), (cx, cy))
                    pygame.draw.line(s, c2, (cx + dy * 2 - dx * 2, cy + dx * 2 - dy * 2), (cx, cy))
            elif ch in NS.PORTALS:
                x, y = cpx(c)
                a, b = PORTAL_COLORS[ch]
                r = 4 + int(math.sin(t * 6 + c) * 1)
                pygame.draw.circle(s, col("black"), (x + 4, y + 4), r + 1)
                pygame.draw.circle(s, col(a), (x + 4, y + 4), r)
                pygame.draw.circle(s, col(b), (x + 4, y + 4), max(1, r - 2))
                ang = t * 8
                s.fill(col("white"), (x + 4 + int(math.cos(ang) * 2), y + 4 + int(math.sin(ang) * 2), 1, 1))
        for c in self.blocks:
            x, y = cpx(c)
            pygame.draw.rect(s, col("gray"), (x, y, C, C), border_radius=2)
            pygame.draw.rect(s, col("white"), (x, y, C, C - 1), border_radius=2)
            s.fill(col("pink"), (x + 2, y + 4, 1, 1))
            s.fill(col("pink"), (x + 5, y + 4, 1, 1))
            if self.blocks[c] < 1.2 and int(t * 10) % 2:
                pygame.draw.rect(s, col("gray"), (x, y, C, C), 1, border_radius=2)
        if self.warn_ring >= 0 and self.squeezed <= self.warn_ring and int(t * 8) % 2:
            for c in range(GW * GH):
                if NS.ring_of(c) == self.warn_ring and self.tiles[c] != "#":
                    x, y = cpx(c)
                    pygame.draw.rect(s, col("red"), (x, y, C, C), 1)
        for c in self.pending:
            x, y = cpx(c)
            pygame.draw.rect(s, col("orange"), (x + 1, y + 1, C - 2, C - 2), 1)
        for v in self.vents:
            st = v.state(self.stage_time)
            x, y = OX + v.x * C, OY + v.y * C
            if v.life != -1.0:
                s.fill(col("darkgray"), (x, y, C, C))
                for k in range(1, 7, 2):
                    s.fill(col("black"), (x + 1, y + k, C - 2, 1))
                if v.life < 1.0 and int(t * 10) % 2:
                    continue
            if st == 1:
                for i in range(3):
                    px = x + 2 + i * 2
                    py = y - int(((t * 12) + i * 3) % 5)
                    s.fill(col("white"), (px, py, 1, 1))
                pygame.draw.rect(s, col("orange" if int(t * 10) % 2 else "yellow"), (x, y, C, C), 1)
            elif st == 2:
                for i, b in enumerate(v.beam):
                    bx, by = cpx(b)
                    wob = int(math.sin(t * 20 + i) * 1)
                    pygame.draw.circle(s, col("gray"), (bx + 4 + wob, by + 4), 4)
                    pygame.draw.circle(s, col("white"), (bx + 4 + wob, by + 3), 3)
                    s.fill(col("cream"), (bx + 2 - wob, by + 2, 2, 1))

    def draw_item(self, s, it, t):
        x, y = cpx(it.cell)
        if 0 < it.life < 1.5 and int(t * 10) % 2:
            return
        bob = int(math.sin(t * 5 + it.cell) * 1)
        if it.kind == "gold":
            cute.dumpling(s, x, y + bob, golden=True, t=t)
        elif it.kind == "fortune":
            c = rainbow(0, t)
            pygame.draw.ellipse(s, col(c), (x, y + 2 + bob, 8, 6))
            pygame.draw.ellipse(s, col("black"), (x, y + 2 + bob, 8, 6), 1)
            s.fill(col("white"), (x + 2, y + 4 + bob, 1, 1))
            s.fill(col("white"), (x + 5, y + 4 + bob, 1, 1))
            if int(t * 8) % 2:
                s.fill(col("white"), (x + 7, y + bob, 1, 1))
                s.fill(col("yellow"), (x - 1, y + 2 + bob, 1, 1))
        elif it.kind in ("tea", "chili", "magnet"):
            pygame.draw.circle(s, col("white"), (x + 4, y + 4 + bob), 5)
            s.blit(sprite("ns_" + it.kind), (x, y + bob))
        elif it.kind == "weak":
            ring = 6 + int((t * 8) % 3)
            pygame.draw.circle(s, col("red" if int(t * 6) % 2 else "yellow"), (x + 4, y + 4), ring, 1)
            if it.look == "sugar":
                s.fill(col("gray"), (x + 1, y + 2 + bob, 7, 6))
                s.fill(col("white"), (x + 1, y + 1 + bob, 6, 6))
                s.fill(col("sky"), (x + 2, y + 2 + bob, 1, 1))
            elif it.look == "bean":
                pygame.draw.ellipse(s, col("black"), (x, y + 1 + bob, 9, 7))
                pygame.draw.ellipse(s, col("choco"), (x + 1, y + 2 + bob, 7, 5))
                s.fill(col("pink"), (x + 2, y + 3 + bob, 2, 1))
            elif it.look == "bun":
                cute.dumpling(s, x, y + bob, golden=True, t=t)
                s.fill(col("red"), (x + 3, y + 1 + bob, 2, 1))
            else:
                s.blit(sprite("ns_chili"), (x, y + bob))

    def draw_roller(self, s, r, t):
        x, y = OX + r.x * C, OY + r.y * C
        if r.kind == "ball":
            pygame.draw.circle(s, col("peach"), (x + 4, y + 4), 5, 1)
            pygame.draw.circle(s, col("black"), (x + 4, y + 4), 4)
            pygame.draw.circle(s, col("brown"), (x + 4, y + 4), 3)
            k = int(r.spin) % 4
            s.fill(col("orange"), (x + 2 + (k % 2) * 2, y + 2 + (k // 2) * 2, 2, 1))
            cute.eyes(s, x + 4 + r.dx, y + 4 + r.dy, 1, 0, "angry")
        elif r.kind == "slip":
            s.fill(col("black"), (x + 1, y + 2, 7, 5))
            s.fill(col("white"), (x + 1, y + 2, 6, 4))
            s.fill(col("red"), (x + 2, y + 4, 4, 1))
        else:
            gold = r.kind == "gold"
            pygame.draw.ellipse(s, col("black"), (x - 1, y + 3, 10, 5))
            pygame.draw.ellipse(s, col("yellow" if gold else "white"), (x - 1, y + 3, 10, 4))
            s.fill(col("white" if gold else "cream"), (x + 1, y + 1, 6, 3))
            s.fill(col("orange" if gold else "red"), (x + 1, y, 6, 2))
            if gold and int(t * 8) % 2:
                s.fill(col("white"), (x + 7, y - 1, 1, 1))
                pygame.draw.circle(s, col("yellow"), (x + 4, y + 3), 6, 1)

    def draw_attacks(self, s, t, top):
        for a in self.attacks:
            if a.kind in ("row", "col"):
                if a.t < a.tele and not top:
                    if int(t * 12) % 2:
                        c = col("red")
                        for k in a.cells:
                            x, y = cpx(k)
                            s.fill(c, (x + 3, y + 3, 2, 2))
                    if a.kind == "row":
                        x, y = cpx(a.cells[0])
                        draw_text(s, "!", OX - 8, y, "red", shadow=None)
                        draw_text(s, "!", OX + GW * C + 3, y, "red", shadow=None)
                    else:
                        x, y = cpx(a.cells[0])
                        draw_text(s, "!", x + 1, OY - 10 if a.cells[0] < GW else y - 9, "red", shadow=None)
                elif a.live and top:
                    for i, k in enumerate(a.cells):
                        x, y = cpx(k)
                        if a.style == "steam":
                            wob = int(math.sin(t * 25 + i) * 1)
                            pygame.draw.circle(s, col("gray"), (x + 4 + wob, y + 4), 5)
                            pygame.draw.circle(s, col("white"), (x + 4 + wob, y + 3), 4)
                        elif a.style == "quake":
                            s.fill(col("choco"), (x, y + 2, C, 4))
                            s.fill(col("brown"), (x + (i * 3) % 6, y + 1, 2, 6))
                        else:
                            s.fill(col("orange"), (x, y + 1, C, 6))
                            s.fill(col("yellow"), (x, y + 2, C, 2))
                    if a.style == "ladle":
                        u = (a.t - a.tele) / max(0.01, a.act)
                        x0, y0 = cpx(a.cells[0])
                        if a.kind == "row":
                            lx = OX + int(u * GW * C)
                            pygame.draw.circle(s, col("black"), (lx, y0 + 4), 7)
                            pygame.draw.circle(s, col("gray"), (lx, y0 + 4), 6)
                            pygame.draw.circle(s, col("white"), (lx - 2, y0 + 2), 2)
            elif a.kind == "drop" and not top:
                u = min(1.0, a.t / a.tele)
                for i, k in enumerate(a.cells):
                    x, y = cpx(k)
                    rr = 1 + int(u * 3)
                    if int(t * 10) % 2:
                        pygame.draw.rect(s, col("red"), (x, y, C, C), 1)
                    pygame.draw.ellipse(s, col("black"), (x + 4 - rr, y + 5, rr * 2, 3))
                    fy = y - int((1 - u) * 60)
                    if i == a.gold:
                        pygame.draw.ellipse(s, col("choco"), (x, fy + 1, 8, 6))
                        s.fill(col("pink"), (x + 2, fy + 2, 2, 1))
                    else:
                        s.fill(col("gray"), (x, fy + 1, C, C - 1))
                        s.fill(col("white"), (x, fy, C, C - 2))
            elif a.kind == "toss" and top:
                u = min(1.0, a.t / a.tele)
                tx, ty = cpx(a.cells[0])
                sx, sy = a.src
                x = sx + (tx + 4 - sx) * u
                y = sy + (ty + 4 - sy) * u - math.sin(u * math.pi) * 30
                look = WEAK_LOOK.get(self.boss.kind if self.boss else "crab", "chili")
                if look == "bun":
                    cute.dumpling(s, int(x) - 4, int(y) - 4, golden=True, t=t)
                else:
                    s.blit(sprite("ns_chili"), (int(x) - 4, int(y) - 4))
                if int(t * 10) % 2:
                    pygame.draw.circle(s, col("red"), (tx + 4, ty + 4), 4, 1)
            elif a.kind == "plate" and top and int(t * 10) % 2:
                x, y = cpx(a.cells[0])
                c = "yellow" if a.gold == 1 else "red"
                ch = {(1, 0): "}", (-1, 0): "{", (0, -1): "|", (0, 1): "`"}[(a.dx, a.dy)]
                draw_text(s, ch, x + 1, y, c, shadow=None, outline="black")
            elif a.kind == "dash" and not top and int(t * 12) % 2:
                for k in a.cells:
                    x, y = cpx(k)
                    pygame.draw.rect(s, col("lavender"), (x + 1, y + 1, C - 2, C - 2), 1)

    def draw_noodle(self, s):
        body = self.body
        n = len(body)
        if self.invuln > 0 and self.state == "play" and int(self.t * 12) % 2:
            return
        fever = self.hype.fever_on
        ghost = self.ghost_t > 0
        ghost_n = 4 * self.lv("ghost")
        k = col("black")
        base = col("lavender") if ghost else col("cream")
        pts = [(OX + (c % GW) * C + 4, OY + (c // GW) * C + 4) for c in body]

        def seg_col(i):
            if fever:
                return col(rainbow(i, self.t))
            if ghost_n and i >= n - ghost_n:
                return col("lavender")
            return base
        for i in range(n - 1, 0, -1):
            a, b = pts[i], pts[i - 1]
            if abs(a[0] - b[0]) > C or abs(a[1] - b[1]) > C:
                continue
            pygame.draw.line(s, k, a, b, 7)
        for i in range(n - 1, -1, -1):
            pygame.draw.circle(s, k, pts[i], (3 if i < n - 2 else 2) + 1)
        for i in range(n - 1, 0, -1):
            a, b = pts[i], pts[i - 1]
            if abs(a[0] - b[0]) > C or abs(a[1] - b[1]) > C:
                continue
            pygame.draw.line(s, seg_col(i), a, b, 5)
        peach = col("orange")
        for i in range(n - 1, -1, -1):
            pygame.draw.circle(s, seg_col(i), pts[i], 3 if i < n - 2 else 2)
            if i % 3 == 1 and not fever:
                s.fill(peach, (pts[i][0] - 1, pts[i][1] - 1, 2, 1))
        hx, hy = pts[0]
        dx, dy = self.dir
        head_r = 4 + (1 if self.slurp > 0 else 0)
        pygame.draw.circle(s, k, (hx, hy), head_r + 1)
        pygame.draw.circle(s, col(rainbow(0, self.t)) if fever else base, (hx, hy), head_r)
        if self.dead:
            cute.eyes(s, hx, hy - 1, 2, 0, "sleepy")
        else:
            cute.eyes(s, hx + dx, hy - 1 + dy, 2, 0, "happy", blink=int(self.t * 1.3) % 6 == 0)
        cute.blush(s, hx, hy + 1, 2)
        if self.slurp > 0:
            pygame.draw.circle(s, col("hotpink"), (hx + dx * 3, hy + dy * 3 + 1), 1)
        if self.dash_t > 0:
            for i in range(3):
                s.fill(col("yellow"), (hx - dx * (7 + i * 3) + dy * (i - 1) * 3, hy - dy * (7 + i * 3) + dx * (i - 1) * 3, 2, 1))

    # ---------------------------------------------------------------- bosses
    def draw_boss(self, s, t):
        b = self.boss
        if b.dead and self.state != "bossdown":
            return
        x, y = OX + b.x * C, OY + b.y * C
        w, h = b.w * C, b.h * C
        if b.dead:
            x += random.randint(-2, 2)
            y += random.randint(-2, 2)
            if int(t * 20) % 2:
                self.parts.burst(x + random.randrange(w), y + random.randrange(h), 3, ("yellow", "white", "red"), 50, 0.4)
        hit = b.flash > 0 and int(t * 30) % 2 == 0
        mood = "angry" if b.angry or b.anim > 0 else "happy"
        getattr(self, "draw_" + b.kind)(s, x, y, w, h, t, hit, mood, b)

    def body_col(self, name, hit):
        return col("white") if hit else col(name)

    def draw_crab(self, s, x, y, w, h, t, hit, mood, b):
        k = col("black")
        cx = x + w // 2
        bob = int(math.sin(t * 6) * 1)
        for side in (-1, 1):   # legs
            for i in range(3):
                lx = cx + side * (10 + i * 5)
                s.fill(k, (lx, y + h - 4 + (i + int(t * 8)) % 2, 2, 4))
        pygame.draw.ellipse(s, k, (x + 1, y + 5 + bob, w - 2, h - 6))
        pygame.draw.ellipse(s, self.body_col("red", hit), (x + 2, y + 6 + bob, w - 4, h - 8))
        pygame.draw.ellipse(s, self.body_col("hotpink", hit), (x + 8, y + 8 + bob, w - 16, 4))
        # chef hat
        pygame.draw.rect(s, k, (cx - 9, y - 3 + bob, 18, 9), border_radius=4)
        pygame.draw.rect(s, col("white"), (cx - 8, y - 2 + bob, 16, 7), border_radius=3)
        s.fill(col("gray"), (cx - 8, y + 4 + bob, 16, 1))
        cute.eyes(s, cx, y + 13 + bob, 5, 0, mood)
        cute.mouth(s, cx, y + 17 + bob, "angry" if mood == "angry" else "happy")
        for side in (-1, 1):   # claws, the right one waves the ladle
            ccx = x + (3 if side < 0 else w - 4)
            ccy = y + 12 + int(math.sin(t * 5 + side) * 2)
            pygame.draw.circle(s, k, (ccx, ccy), 5)
            pygame.draw.circle(s, self.body_col("red", hit), (ccx, ccy), 4)
            s.fill(k, (ccx - 1, ccy - 4, 2, 4))
            if side > 0:
                pygame.draw.line(s, col("gray"), (ccx, ccy), (ccx + 6, ccy - 8), 2)
                pygame.draw.circle(s, col("gray"), (ccx + 7, ccy - 9), 3)

    def draw_teapot(self, s, x, y, w, h, t, hit, mood, b):
        k = col("black")
        cx = x + w // 2
        body = self.body_col("teal", hit)
        pygame.draw.circle(s, k, (x + 4, y + 18), 6, 2)        # handle
        pygame.draw.polygon(s, k, [(x + w - 9, y + 16), (x + w + 5, y + 8), (x + w + 6, y + 12), (x + w - 7, y + 24)])
        pygame.draw.polygon(s, body, [(x + w - 9, y + 17), (x + w + 4, y + 9), (x + w + 4, y + 11), (x + w - 8, y + 22)])
        pygame.draw.ellipse(s, k, (x + 3, y + 7, w - 6, h - 7))
        pygame.draw.ellipse(s, body, (x + 4, y + 8, w - 8, h - 9))
        pygame.draw.ellipse(s, self.body_col("mint", hit), (x + 9, y + 11, w - 18, 5))
        lid_y = y + 3 - (4 + int(abs(math.sin(t * 12)) * 3) if b.lid > 0 else 0)
        pygame.draw.ellipse(s, k, (cx - 10, lid_y, 20, 8))
        pygame.draw.ellipse(s, self.body_col("white", hit), (cx - 9, lid_y + 1, 18, 6))
        pygame.draw.circle(s, col("yellow"), (cx, lid_y), 2)
        for side in (-1, 1):   # little dragon horns
            pygame.draw.polygon(s, col("yellow"), [(cx + side * 12, y + 10), (cx + side * 16, y + 3), (cx + side * 9, y + 9)])
        cute.eyes(s, cx, y + 18, 5, 0, mood)
        s.fill(k, (cx - 2, y + 22, 1, 1))
        s.fill(k, (cx + 2, y + 22, 1, 1))
        if b.anim > 0 or b.lid > 0:
            for i in range(3):
                py = y - 2 - int((t * 30 + i * 6) % 14)
                pygame.draw.circle(s, col("white"), (x + w + 4 + i * 2 - 2, py + 8), 2)

    def draw_sushi(self, s, x, y, w, h, t, hit, mood, b):
        k = col("black")
        cx = x + w // 2
        pygame.draw.rect(s, k, (x, y + h - 6, w, 6), border_radius=2)       # conveyor
        s.fill(col("gray"), (x + 1, y + h - 5, w - 2, 3))
        for i in range(8):
            s.fill(col("darkgray"), (x + 2 + (i * 8 + int(t * 20)) % (w - 4), y + h - 5, 2, 3))
        pygame.draw.rect(s, k, (x + 2, y + 1, w - 4, h - 6), border_radius=5)
        pygame.draw.rect(s, self.body_col("white", hit), (x + 3, y + 2, w - 6, h - 8), border_radius=4)
        pygame.draw.rect(s, self.body_col("orange", hit), (x + 3, y + 2, w - 6, 6), border_radius=3)
        for i in range(5):
            s.fill(col("peach"), (x + 8 + i * 10, y + 3, 4, 1))
        s.fill(k, (cx - 4, y + 7, 8, h - 13))                                  # nori band
        cute.eyes(s, cx - 14, y + 13, 3, 0, mood)
        cute.eyes(s, cx + 14, y + 13, 3, 0, mood)
        mo = 3 + int(abs(math.sin(t * 6)) * 3) if b.anim > 0 else 2
        pygame.draw.ellipse(s, col("red"), (cx - 6, y + 8 + 6 - mo // 2, 12, mo))

    def draw_golem(self, s, x, y, w, h, t, hit, mood, b):
        k = col("black")
        cx = x + w // 2
        sq = int(abs(math.sin(t * 3)) * 2)
        tiers = ((h - 12, w - 2), (h - 21, w - 10), (h - 28, w - 20))
        for i, (ty, tw) in enumerate(tiers):
            ry = y + ty + (sq if i else 0)
            pygame.draw.ellipse(s, k, (cx - tw // 2 - 1, ry - 1, tw + 2, 13))
            pygame.draw.ellipse(s, self.body_col("white" if i != 1 else "cream", hit), (cx - tw // 2, ry, tw, 11))
        pygame.draw.circle(s, k, (cx, y + 2), 5)
        pygame.draw.circle(s, col("orange"), (cx, y + 2), 4)
        s.fill(col("lime"), (cx, y - 3, 2, 2))
        cute.eyes(s, cx, y + h - 17 + sq, 5, 0, mood)
        cute.blush(s, cx, y + h - 14 + sq, 5)
        cute.mouth(s, cx, y + h - 12 + sq, "angry" if mood == "angry" else "happy")
        for side in (-1, 1):
            ax = cx + side * (w // 2 + 1)
            ay = y + h - 10 + (int(math.sin(t * 8) * 2) if b.anim > 0 else 0)
            pygame.draw.circle(s, k, (ax, ay), 4)
            pygame.draw.circle(s, self.body_col("white", hit), (ax, ay), 3)

    def draw_ghost(self, s, x, y, w, h, t, hit, mood, b):
        k = col("black")
        cx, cy = x + w // 2, y + h // 2 + int(math.sin(t * 4) * 2)
        if b.inv > 0 and int(t * 12) % 2:
            return
        body = self.body_col("white", hit)
        pygame.draw.circle(s, k, (cx, cy - 1), 9)
        pygame.draw.rect(s, k, (cx - 9, cy - 1, 19, 10))
        pygame.draw.circle(s, body, (cx, cy - 1), 8)
        pygame.draw.rect(s, body, (cx - 8, cy - 1, 17, 8))
        for i in range(5):   # wavy hem
            pygame.draw.circle(s, k if (i + int(t * 8)) % 2 else body, (cx - 8 + i * 4, cy + 8), 2)
            pygame.draw.circle(s, body, (cx - 8 + i * 4, cy + 7), 2)
        s.fill(col("lavender"), (cx + 4, cy - 4, 2, 9))
        pygame.draw.ellipse(s, k, (cx - 7, cy - 14, 14, 8))     # fortune cookie hat
        pygame.draw.ellipse(s, col("yellow"), (cx - 6, cy - 13, 12, 6))
        pygame.draw.line(s, col("orange"), (cx - 4, cy - 10), (cx + 4, cy - 10))
        s.fill(col("white"), (cx + 5, cy - 12, 6, 3))           # the fortune slip
        s.fill(col("red"), (cx + 7, cy - 11, 3, 1))
        stunned = b.stun > 0
        cute.eyes(s, cx, cy - 2, 3, 0, "wow" if stunned else mood)
        cute.mouth(s, cx, cy + 2, "wow" if stunned else ("angry" if mood == "angry" else "happy"))
        cute.blush(s, cx, cy + 1, 3)

    def draw_bao(self, s, x, y, w, h, t, hit, mood, b):
        k = col("black")
        cx = x + w // 2
        bob = int(math.sin(t * 3) * 1)
        pygame.draw.ellipse(s, k, (x, y + 4 + bob, w, h - 3))
        pygame.draw.ellipse(s, self.body_col("white", hit), (x + 1, y + 5 + bob, w - 2, h - 5))
        for i in range(-3, 4):   # pleats
            s.fill(col("cream"), (cx + i * 5, y + 6 + bob + abs(i), 1, 5))
        pygame.draw.polygon(s, col("black"), [(cx - 11, y + 4 + bob), (cx - 11, y - 5 + bob), (cx - 5, y + bob),
                                              (cx, y - 7 + bob), (cx + 5, y + bob), (cx + 11, y - 5 + bob), (cx + 11, y + 4 + bob)])
        pygame.draw.polygon(s, col("yellow"), [(cx - 10, y + 3 + bob), (cx - 10, y - 3 + bob), (cx - 5, y + 1 + bob),
                                               (cx, y - 5 + bob), (cx + 5, y + 1 + bob), (cx + 10, y - 3 + bob), (cx + 10, y + 3 + bob)])
        s.fill(col("red"), (cx - 1, y - 1 + bob, 3, 2))
        cute.eyes(s, cx, y + 17 + bob, 6, 0, mood)
        cute.blush(s, cx, y + 20 + bob, 6)
        pygame.draw.line(s, k, (cx - 6, y + 23 + bob), (cx - 1, y + 21 + bob), 2)   # mustache
        pygame.draw.line(s, k, (cx + 6, y + 23 + bob), (cx + 1, y + 21 + bob), 2)

    # ---------------------------------------------------------------- HUD & cards
    def draw_hud(self, s, t):
        draw_text(s, f"{self.score:07d}", 4, 4, "white")
        draw_text(s, f"HI {max(self.best, self.score):07d}", 52, 4, "lavender")
        if self.campaign:
            if self.kind == "bonus":
                label, c = "BONUS", rainbow(0, t)
            elif self.kind == "boss":
                label, c = f"BOSS {self.stage_n}", "red"
            else:
                label, c = f"STAGE {self.stage_n}", "yellow"
        else:
            label, c = ("CLASSIC" if self.mode == "classic" else "WRAP"), "yellow"
        hx = W - 4 - 8 * min(6, max(0, self.lives)) - (14 if self.lives > 6 else 0)
        draw_text(s, label, hx - 6, 4, c, align="right")
        self.hearts(s, hx, 3, self.lives)
        # left column: fever gauge
        gx, gy, gh = 12, 40, 130
        s.blit(sprite("ns_chili"), (gx - 1, gy - 12))
        panel(s, (gx - 2, gy - 2, 10, gh + 4), fill="black", border=self.theme[2], radius=2, shadow=False)
        if self.hype.fever_on:
            fh = int(gh * min(1.0, self.hype.fever_t / (self.hype.FEVER_TIME + 2.0 * self.lv("fever"))))
            for i in range(0, fh, 4):
                s.fill(col(rainbow(i // 4, t)), (gx, gy + gh - i - 4, 6, 4))
        else:
            fh = int(gh * self.hype.fever)
            s.fill(col("orange"), (gx, gy + gh - fh, 6, fh))
            s.fill(col("yellow"), (gx + 1, gy + gh - fh, 2, fh))
        # right column: abilities and timers
        rx, ry = W - 24, 30
        for i in range(self.dash_charges):
            s.blit(sprite("ns_bolt"), (rx + (i % 2) * 10, ry + (i // 2) * 10))
        ry += 10 * ((self.dash_charges + 1) // 2) + (4 if self.dash_charges else 0)
        for i in range(self.snips):
            s.blit(sprite("ns_snip"), (rx + (i % 2) * 10, ry + (i // 2) * 10))
        ry += 10 * ((self.snips + 1) // 2) + (4 if self.snips else 0)
        for name, v, full in (("ns_tea", self.ghost_t, 5.0), ("ns_magnet", self.magnet_t, 8.0)):
            if v > 0:
                s.blit(sprite(name), (rx + 4, ry))
                s.fill(col("white"), (rx, ry + 10, int(16 * v / full), 2))
                ry += 16
        # bottom row: goal progress
        by = OY + GH * C + 5
        if self.kind == "boss" and self.boss:
            boss_bar(s, self.boss.name, self.boss.hp, self.boss.maxhp, t, y=by - 1)
            return
        g = self.goal
        if g == "eat":
            txt = f"EAT {min(self.eaten_stage, self.target)}/{self.target}"
        elif g == "stars":
            txt = f"STARS {self.stars_total - len(self.stars)}/{self.stars_total}"
        elif g == "length":
            txt = f"LENGTH {len(self.body)}/{self.target}"
        elif g == "survive":
            txt = f"SURVIVE {max(0, int(math.ceil(self.target - self.stage_time)))}"
        elif g == "feast":
            txt = f"FEAST {self.feast_total - len(self.foods)}/{self.feast_total}"
        elif g == "rush":
            txt = f"GOLDEN {self.eaten_stage}"
        else:
            txt = f"LENGTH {len(self.body)}  EATEN {self.total_eaten}"
        draw_text(s, txt, OX, by, "white")
        if self.kind == "bonus":
            tl = max(0.0, self.bonus_left)
            draw_text(s, f"TIME {tl:04.1f}", OX + GW * C - (34 if self.hype.fever_on else 0), by, "yellow" if tl > 5 or int(t * 8) % 2 else "red",
                      align="right")
        elif not self.gates_open:
            need = max(0, self.st["gate"] - self.eaten_stage)
            draw_text(s, f"DOORS OPEN IN {need}", OX + GW * C, by, "yellow", align="right")
        elif self.campaign and not self.hype.fever_on:
            draw_text(s, self.theme[0], OX + GW * C, by, "cream", align="right")

    def goal_text(self):
        g, n = self.goal, self.target
        return {"eat": f"EAT {n} DUMPLINGS", "stars": f"GRAB ALL {n} CHILI STARS", "length": f"GROW TO LENGTH {n}",
                "survive": f"SURVIVE {n} SECONDS", "feast": "SLURP THE FEAST IN 20 SEC!",
                "rush": "GOLDEN RUSH! 20 SECONDS", "endless": "EAT, GROW, DON'T BUMP!"}.get(g, "")

    def draw_intro(self, s, t):
        if self.kind == "boss" and self.state_t < 2.2:
            on = int(t * 6) % 2 == 0
            band = pygame.Surface((W, 40), pygame.SRCALPHA)
            band.fill((120, 10, 30, 170))
            s.blit(band, (0, 70))
            for i in range(0, W, 16):
                o = int(t * 40) % 16
                pygame.draw.polygon(s, col("yellow"), [(i + o, 70), (i + o + 8, 70), (i + o, 74)])
                pygame.draw.polygon(s, col("yellow"), [(i - o + 8, 110), (i - o + 16, 110), (i - o + 16, 106)])
            if on:
                draw_text(s, "WARNING!!", W // 2, 80, "red", 3, align="center", outline="white")
            draw_text(s, "A HUNGRY BOSS APPROACHES", W // 2, 101, "white", align="center", shadow=None)
            return
        y0 = 54
        panel(s, (50, y0, 220, 84), fill="ink", border=self.theme[7] if self.kind == "stage" else "yellow")
        if self.kind == "boss":
            b = self.boss
            draw_text(s, b.name, W // 2, y0 + 10, "red", 2, align="center", outline="black")
            draw_text(s, f"STAGE {self.stage_n}", W // 2, y0 + 32, "yellow", align="center")
            draw_text(s, b.hint, W // 2, y0 + 48, "white", align="center", shadow=None)
            draw_text(s, f"HP {b.maxhp}", W // 2, y0 + 64, "pink", align="center", shadow=None)
            return
        if self.kind == "bonus":
            title = "BONUS STAGE"
            for i, ch in enumerate(title):
                draw_text(s, ch, W // 2 - text_width(title, 2) // 2 + i * 12, y0 + 10 + int(math.sin(t * 6 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            draw_text(s, "DUMPLING FEAST!" if self.goal == "feast" else "GOLDEN RUSH!", W // 2, y0 + 34, "yellow",
                      align="center")
            draw_text(s, self.goal_text(), W // 2, y0 + 50, "white", align="center", shadow=None)
            draw_text(s, "NO LIVES LOST HERE - GO WILD!", W // 2, y0 + 66, "mint", align="center", shadow=None)
            return
        if self.campaign:
            draw_text(s, f"STAGE {self.stage_n}", W // 2, y0 + 8, "yellow", 2, align="center", outline="black")
            draw_text(s, self.theme[0], W // 2, y0 + 28, self.theme[7], align="center")
        else:
            draw_text(s, "CLASSIC" if self.mode == "classic" else "WRAP AROUND", W // 2, y0 + 12, "yellow", 2,
                      align="center", outline="black")
        draw_text(s, self.goal_text(), W // 2, y0 + 44, "white", align="center", shadow=None)
        if self.st["new"]:
            draw_text(s, "NEW!", W // 2, y0 + 58, rainbow(0, t), align="center", shadow=None)
            draw_text(s, self.st["new"], W // 2, y0 + 68, "mint", align="center", shadow=None)
        else:
            draw_text(s, "READY... SLURP!", W // 2, y0 + 62, "peach", align="center", shadow=None)

    def draw_tally(self, s, t):
        y0 = 48
        hh = 30 + 14 * len(self.tally)
        panel(s, (60, y0, 200, hh + 14), fill="ink", border="yellow")
        title = "BOSS DEFEATED!" if self.kind == "boss" else "BONUS RESULT" if self.kind == "bonus" else \
            f"STAGE {self.stage_n} CLEAR!"
        draw_text(s, title, W // 2, y0 + 8, "yellow", align="center")
        for i, (label, v, shown) in enumerate(self.tally):
            if i > self.tally_i:
                break
            y = y0 + 24 + i * 14
            dim = v == 0 and i < self.tally_i
            draw_text(s, label, 72, y, "gray" if dim else "white", shadow=None)
            draw_text(s, f"{shown}" if not dim else "-", 248, y, "gray" if dim else "lime", align="right", shadow=None)
        if self.tally_i >= len(self.tally):
            total = sum(v for _, v, _ in self.tally)
            draw_text(s, f"TOTAL {total}", W // 2, y0 + hh - 2, rainbow(0, t) if self.lucky else "yellow",
                      align="center")


def autopilot(scene):
    """Demo / test pilot: breadth-first search toward the nearest snack, star or weak point, avoiding walls, the
    body and live hazards. Returns the keys to press this frame."""
    if scene.queue or scene.state not in ("play", "intro", "ready", "victory", "bossdown"):
        return set()
    body = set(scene.body[:-1])
    targets = set(scene.foods) | set(scene.stars) | {i.cell for i in scene.items}
    targets |= {r.cell for r in scene.rollers if r.kind == "gold"}
    if scene.boss and scene.boss.kind == "ghost":
        targets = set(scene.foods)
    wrap = scene.mode == "wrap"

    slide = {c for c, ch in enumerate(scene.tiles) if ch == "~" or ch in NS.ARROWS}

    def nxt(c, d, careful=False):
        x, y = c % GW + d[0], c // GW + d[1]
        if wrap:
            x, y = x % GW, y % GH
        if not (0 <= x < GW and 0 <= y < GH):
            return None
        n = y * GW + x
        if n in scene.link:
            n = scene.link[n]
        if scene.solid(n) or n in body or scene.deadly(n) or scene.roller_at(n) is not None and \
                scene.roller_at(n).kind != "gold":
            return None
        if careful and n in slide and n not in targets:   # it cannot steer on ice / conveyors: avoid them first
            return None
        return n
    h = scene.head()
    rev = (-scene.dir[0], -scene.dir[1])
    choice = None
    for careful in (True, False):
        first = {}
        q = deque()
        for name, d in DIRS.items():
            if d == rev:
                continue
            n = nxt(h, d, careful)
            if n is not None and n not in first:
                first[n] = name
                q.append(n)
        seen = set(first)
        while q:
            c = q.popleft()
            if c in targets:
                choice = first[c]
                break
            for d in DIRS.values():
                n = nxt(c, d, careful)
                if n is not None and n not in seen:
                    seen.add(n)
                    first[n] = first[c]
                    q.append(n)
        if choice:
            break
    if choice is None:   # no snack reachable: go where there is the most room
        best = None
        for name, d in DIRS.items():
            if d == rev:
                continue
            n = nxt(h, d)
            if n is None:
                continue
            room, st = {n}, [n]
            while st and len(room) < 200:
                c = st.pop()
                for e in DIRS.values():
                    m = nxt(c, e)
                    if m is not None and m not in room:
                        room.add(m)
                        st.append(m)
            if best is None or len(room) > best[0]:
                best = (len(room), name)
        choice = best[1] if best else None
    if choice and DIRS[choice] != scene.dir:
        return {choice}
    return set()


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys."""
    return lambda frame: autopilot(scene)


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
        c = col(rainbow(i, t)) if int(t) % 4 == 3 else col("cream")
        pygame.draw.line(s, c, pts[i], pts[i + 1], 5)
    hx, hy = pts[-1]
    pygame.draw.circle(s, col("black"), (hx, hy), 5)
    pygame.draw.circle(s, col("cream"), (hx, hy), 4)
    cute.eyes(s, hx + 1, hy - 1, 2)
    cute.dumpling(s, w - 22, h // 2 - 4, t=t)
    cute.dumpling(s, w - 40, 10, golden=True, t=t)
    s.blit(sprite("star", remap={"y": "r"}), (w - 30, h - 16))
