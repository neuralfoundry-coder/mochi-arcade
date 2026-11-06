"""COMET KITTY - a fixed-screen space shooter starring Tama the teacup kitty (original game).

A 200-stage campaign (stage tables: comet_kitty_data.py). Squads of space critters swirl in along entry paths,
settle into formation and dive at Tama. Every x5 stage is a BONUS PARADE, every 10th stage a boss.
Bosses and good parades award upgrade cards; capsules, medal chains, FEVER hyper shots and the rare golden
comet JACKPOT keep things lively. The iOS port (ios/MochiArcade/Games/CometKitty*.swift) mirrors this file.
"""
import math
import random

import pygame

from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, ease_out, rainbow, tier
from mochi_arcade.games import comet_kitty_art as art
from mochi_arcade.games import comet_kitty_data as D
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.games.comet_kitty_data import (BLOB, COMET, DART, GOLD, JELLY, KINDS, METEOR, MINE, MINI, MOTH,
                                                 PUFF, SHELL, SPORE, URCHIN, WISP)
from mochi_arcade.gfx import H, W, Stars, bubble, col, draw_text, panel, sprite, text_width

EXPORT = D.EXPORT
PY = 166                        # Tama's resting height (top of her 16x16 sprite)
PY_MIN, PY_MAX = 128, 172       # she can drift up and down inside this band
EXTRA_LIVES = (30000, 80000, 150000, 250000)
EXTRA_EVERY = 150000
MEDALS = (100, 200, 300, 500, 800, 1000, 1500, 2000, 3000, 5000)
SIZES = art.SIZES
SPREAD = ((), (8,), (8, 18), (8, 18, 30), (8, 18, 30, 42))
PAL_SLOTS = ((-16, 6), (16, 6), (0, -14))
KIT_ORDER = ("rapid", "spread", "shield", "zoom", "bombs", "lance", "pals", "seeker", "focus", "magnet")
DIVING = ("dive", "dash", "kami")
HARMFUL = ("enter", "home", "dive", "dash", "kami", "free")

POOL = [
    Upgrade("spread", "STAR SPREAD", "MORE STREAMS|OF STARS THAT|FAN OUT WIDE", "yellow", art.icon("spread"), 3),
    Upgrade("rapid", "RAPID PAWS", "SHOOT STARS|FASTER", "orange", art.icon("rapid"), 5),
    Upgrade("lance", "COMET LANCE", "CENTRE SHOT|PIERCES FOES|AND HITS HARD", "sky", art.icon("lance"), 3),
    Upgrade("seeker", "SEEKER STARS", "HOMING STARS|CHASE FOES", "lime", art.icon("seeker"), 3),
    Upgrade("pals", "STAR PALS", "A STAR FRIEND|FLIES BESIDE|YOU, SHOOTING", "pink", art.icon("pals"), 2),
    Upgrade("shield", "BUBBLE GUARD", "+1 BUBBLE|EVERY STAGE|BLOCKS A HIT", "mint", art.icon("shield"), 3),
    Upgrade("zoom", "ZOOMIES", "FLY|FASTER", "peach", art.icon("zoom"), 3),
    Upgrade("focus", "FOCUS CORE", "TINIER HITBOX|LV2: GRAZING|BULLETS SCORES", "lavender", art.icon("focus"), 2),
    Upgrade("bombs", "BOMB POUCH", "+1 COMET BURST|BIGGER BLASTS", "red", art.icon("bombs"), 3),
    Upgrade("magnet", "MAGNET MITTS", "PULLS IN|MEDALS AND|CAPSULES", "lavender", art.icon("magnet"), 2),
]


def bezier(p, u):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p
    a, b, c, d = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3
    return a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3


def path_pos(path, dist, mirror):
    f = dist / D.STEP
    i = min(len(path) - 2, int(f))
    f -= i
    x = path[i][0] + (path[i + 1][0] - path[i][0]) * f
    y = path[i][1] + (path[i + 1][1] - path[i][1]) * f
    return (W - x if mirror else x), y


class Enemy:
    def __init__(self, uid, kind, hp):
        self.uid, self.kind = uid, kind
        self.hp = self.maxhp = float(hp)
        self.x, self.y = -60.0, -60.0
        self.col = self.row = 0
        self.state = "wait"
        self.t = 0.0
        self.delay = 0.0
        self.path = None
        self.mirror = 0
        self.dist = 0.0
        self.speed = 120.0
        self.group = -1
        self.cap = -1
        self.flash = 0.0
        self.alive = True
        self.extra = False      # mines, meteors, minis, golden comets: not needed to clear the stage
        self.parade = False
        self.entered = False
        self.bez = None
        self.dur = 1.0
        self.shots = []
        self.vx = self.vy = 0.0
        self.aux = 0.0
        self.fire_at = -1.0     # entry-path distance at which it fires once (-1: never)
        self.amb_at = -1.0      # entry-path distance at which it dives out of the entry (-1: never)
        self.tele = 0.0         # formation volley wind-up
        self.seed = random.uniform(0, 6.28)


class Boss:
    def __init__(self, st):
        spec = D.BOSSES[st["boss"]]
        self.kind, self.lv, self.final, self.name = st["boss"], st["lv"], st["final"], st["name"]
        self.hp = self.maxhp = float(st["hp"])
        self.bw, self.bh = spec["box"]
        self.weak = spec["weak"]
        self.phases, self.nphase = st["phases"], st["nphase"]
        self.parts = [[p[0], p[1], p[2], self.maxhp * p[3], 0.0, True] for p in spec["parts"]]  # dx dy r hp flash alive
        self.x, self.y = W / 2, -40.0
        self.cx, self.hy = W / 2, 50.0
        self.t = self.mt = 0.0
        self.state = "enter"
        self.phase = 0
        self.atk = None
        self.at = 0.0
        self.ai = self.an = 0
        self.rest = 1.0
        self.flash = 0.0
        self.face = 1
        self.alpha = 1.0
        self.lx, self.rx = [], []
        self.gap = self.tx = W / 2
        self.dir = 1
        self.ang = 0.0

    def weak_pos(self):
        f = self.face if self.kind == 2 else 1
        return self.x + self.weak[0] * f, self.y + self.weak[1], self.weak[2]


class CometKitty(GameScene):
    @property
    def music(self):
        return self.stage_music

    def __init__(self, app, info, opt):
        self.stage_music = "comet"
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES[d]
        self.spd = SPEED[d]
        self.autofire = str(opt.get("autofire", "off")).lower() in ("on", "true")
        self.stage_n = max(1, min(STAGES, int(opt.get("start", 1))))
        self.stars = Stars(70, seed=7)
        self.px, self.py = W / 2, float(PY)
        self.vx = self.vy = 0.0
        self.shots, self.bullets, self.items, self.enemies, self.spawned = [], [], [], [], []
        self.boss = None
        self.levels = {}
        self.inv = 1.5
        self.dead_t = None
        self.fire_t = self.seek_t = 0.0
        self.shot_n = 0
        self.bomb_t = self.bomb_x = self.bomb_y = 0.0
        self.friend_t = self.power_t = 0.0
        self.pals = [[self.px, self.py] for _ in range(3)]
        self.medal_i = 0
        self.extra_i = 0
        self.next_extra = EXTRA_LIVES[0]
        self.uid = 0
        self.fever_was = False
        self.tin_t = 0.0
        self.warp = 0.0
        self.bg, self.bg_theme = None, -1
        self.tally = None
        self.vic_t = 0.0
        # starting from a checkpoint: hand out the power a player would roughly have by then
        kit = given = (self.stage_n - 1) // 10
        i = 0
        while kit > 0 and i < 200:
            u = next(x for x in POOL if x.id == KIT_ORDER[i % len(KIT_ORDER)])
            if self.lv(u.id) < u.max:
                self.levels[u.id] = self.lv(u.id) + 1
                kit -= 1
            i += 1
        self.bombs = 2 + self.lv("bombs")
        self.shield = 0
        self.start_stage()
        if given:
            self.hype.banner("CHECKPOINT!", f"+{given} POWER LEVELS", color="lime", dur=2.0)

    # ---------------------------------------------------------------- helpers
    def lv(self, uid):
        return self.levels.get(uid, 0)

    def npals(self):
        return min(3, self.lv("pals") + (1 if self.friend_t > 0 else 0))

    def hitbox(self):
        return 2.5 if self.lv("focus") >= 1 else 4.0

    def centre(self):
        return self.px, self.py + 9

    def say(self, x, y, text, color):
        """Floating text kept fully on screen."""
        hw = text_width(text) // 2 + 2
        self.floats.add(max(hw, min(W - hw, x)), y, text, color)

    def spawn(self, kind, hp):
        self.uid += 1
        return Enemy(self.uid, kind, hp)

    def solid(self, e):
        return e.kind != WISP or math.sin(self.stage_t * 2.4 + e.seed) > -0.35

    def hittable(self, e):
        return e.alive and e.state != "wait" and e.y > -6 and self.solid(e)

    def slot(self, e):
        ft = self.stage_t
        sway = math.sin(ft * 0.8) * 12
        breathe = 1 + math.sin(ft * 1.6) * 0.05
        return (W / 2 + e.col * D.COL_DX * breathe + sway,
                D.ROW_Y0 + e.row * D.ROW_DY + math.sin(ft * 2 + e.col * 0.5) * 1.5)

    # ---------------------------------------------------------------- stages
    def start_stage(self):
        n = self.stage_n
        self.st = D.stage(n)
        self.mode = self.st["type"]
        self.tier = tier(n)
        self.theme = D.THEMES[self.st["theme"]]
        if self.bg_theme != self.st["theme"]:
            self.bg, self.bg_theme = art.make_backdrop(self.theme), self.st["theme"]
        self.reached(n)
        self.enemies, self.bullets, self.spawned = [], [], []
        self.boss = None
        self.stage_t = self.intro_t = self.clear_t = 0.0
        self.deaths = self.squad_wipes = self.hits = self.total = self.broken = 0
        self.squads = {}
        self.dive_t = 1.0
        self.meteor_t = 3.0
        self.volley_t = 3.0
        self.gold_t = random.uniform(8, 16) if self.mode == "normal" and self.hype.lucky(0.03) else -1.0
        self.shield = max(self.shield, self.lv("shield"))
        self.tally = None
        self.dive_start = 0.0
        au = self.app.audio
        if self.mode == "boss":
            self.phase = "warning"
            self.boss = Boss(self.st)
            self.stage_music = "boss"
            au.play("warning")
        else:
            self.phase = "intro"
            self.stage_music = "bonus" if self.mode == "bonus" else "comet"
            au.play("stage")
        if not self.hype.fever_on or self.mode == "boss":
            au.music(self.stage_music)
        if self.mode == "normal":
            st = self.st
            last = 0.0
            for c, r, kd, pi, mirror, delay, g, cap in st["slots"]:
                hp = KINDS[kd][1] + (st["hpb"] if kd not in (JELLY, MOTH) else st["hpj"] + (1 if "ARMORED" in st["mods"] else 0))
                e = self.spawn(kd, hp)
                e.col, e.row, e.delay, e.path, e.mirror, e.group, e.cap = c, r, delay, D.PATHS[pi], mirror, g, cap
                e.speed = st["speed"] * (0.85 + 0.15 * self.spd)
                e.aux = random.uniform(2.0, st["fire_gap"] + 2.0)
                plen = (len(e.path) - 1) * D.STEP
                if random.random() < st["efire"]:     # takes a pot shot at Tama while flying in
                    e.fire_at = random.uniform(0.3, 0.8) * plen
                if random.random() < st["amb"]:       # breaks off the entry path to attack straight away
                    e.amb_at = random.uniform(0.45, 0.8) * plen
                self.enemies.append(e)
                self.squads.setdefault(g, [0, 0])[0] += 1
                last = max(last, delay)
            self.dive_start = min(3.0, last)
        elif self.mode == "bonus":
            for g, (pi, mirror, delay, count, gold, kd) in enumerate(self.st["waves"]):
                for i in range(count):
                    e = self.spawn(GOLD if i == gold else kd, 1)
                    e.parade = True
                    e.delay, e.path, e.mirror, e.group = delay + i * 20.0 / self.st["speed"], D.PATHS[pi], mirror, g
                    e.speed = self.st["speed"]
                    self.enemies.append(e)
                    self.total += 1
                self.squads[g] = [count, 0]

    def next_stage(self):
        self.stage_n += 1
        self.start_stage()

    def check_clear(self):
        if self.phase != "play":
            return
        if self.mode == "boss":
            done = self.boss is None
        elif self.mode == "bonus":
            done = not self.enemies
        else:
            done = not any(not e.extra for e in self.enemies)
        if not done:
            return
        self.phase = "clear"
        self.clear_t = 0.0
        self.cancel_bullets()
        for e in self.enemies:
            if e.alive and e.state != "wait":
                self.parts.burst(e.x, e.y, 8, art.KIND_COLORS[e.kind], 60, 0.5)
        self.enemies = []
        if self.mode != "boss":
            self.app.audio.play("levelup")

    def start_tally(self):
        t = self.tier
        lines = []
        if self.mode == "normal":
            lines.append(["CLEAR BONUS", 1000 + 250 * t])
            lines.append(["TIME BONUS", max(0, int(self.st["par"] - self.stage_t)) * 50])
            lines.append(["NO MISS", (3000 + 750 * t) if self.deaths == 0 else 0])
            sq = self.st["groups"]
            lines.append([f"SQUADS {self.squad_wipes}/{sq}", self.squad_wipes * (300 + 60 * t)])
            if self.squad_wipes >= sq:
                lines.append(["PERFECT!!", 5000 + 1000 * t])
            title = f"STAGE {self.stage_n} CLEAR!"
        elif self.mode == "bonus":
            lines.append([f"HITS {self.hits}/{self.total}", self.hits * 100])
            if self.hits >= self.total:
                lines.append(["PERFECT!!", 10000 + 2500 * t])
            title = "BONUS PARADE OVER"
        else:
            lines.append(["BOSS BONUS", 10000 + 5000 * t])
            lines.append(["TIME BONUS", max(0, int(self.st["par"] - self.stage_t)) * 100])
            lines.append(["NO MISS", (5000 + 1000 * t) if self.deaths == 0 else 0])
            if D.BOSSES[self.st["boss"]]["parts"]:
                lines.append([f"PARTS BROKEN {self.broken}", self.broken * 2000])
            title = f"{self.st['name']} DEFEATED!"
        self.tally = {"title": title, "lines": lines, "t": 0.0, "shown": 0, "total": sum(v for _, v in lines)}
        self.phase = "tally"

    def update_tally(self, dt):
        tl = self.tally
        tl["t"] += dt
        n = len(tl["lines"])
        while tl["shown"] < n and tl["t"] >= 0.35 + tl["shown"] * 0.4:
            label, v = tl["lines"][tl["shown"]]
            tl["shown"] += 1
            if label.startswith("PERFECT"):
                self.app.audio.play("win")
                self.hype.shower(50, "coins")
                self.hype.flash("yellow", 0.2)
            else:
                self.app.audio.play("coin" if v > 0 else "move")
        end = 0.35 + n * 0.4 + 0.4
        if tl["t"] >= end + 1.4 or (tl["t"] >= end and self.app.input.hit("a", "b")):
            self.finish_tally()

    def finish_tally(self):
        tl = self.tally
        self.tally = None
        if tl["total"]:
            self.add(tl["total"], W // 2, 110, "yellow")
        self.phase = "between"
        if self.mode == "boss":
            if self.st["final"] or self.stage_n >= STAGES:
                self.phase = "victory"
                self.vic_t = 0.0
                self.hype.banner("GALAXY SAVED!!", "ALL 200 STAGES CLEAR", rainbow=True, dur=4.0, sound="win")
                self.hype.shower(120, "confetti")
                self.app.audio.music("fever")
                return
            self.pick_upgrade(POOL, self.levels, self.on_pick, "POWER UP!")
        elif self.mode == "bonus" and self.hits * 2 >= self.total:
            self.pick_upgrade(POOL, self.levels, self.on_pick, "BONUS PICK!")
        else:
            self.next_stage()

    def on_pick(self, uid):
        if uid is None:
            self.add(25000, W // 2, 100, "lime")
            self.hype.banner("MAX POWER!", "+25000", color="lime", dur=1.4)
        else:
            self.levels[uid] = self.lv(uid) + 1
            if uid == "bombs":
                self.bombs += 1
            elif uid == "shield":
                self.shield += 1
        self.next_stage()

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        au = self.app.audio
        self.stage_t += dt
        self.intro_t += dt
        self.tin_t = max(0.0, self.tin_t - dt)
        warp_goal = 1.0 if self.phase in ("clear", "tally", "between") else 0.0
        self.warp += (warp_goal - self.warp) * min(1.0, dt * 2)
        self.stars.update(dt, 22 + self.warp * 160 + (12 if self.mode == "boss" else 0))
        self.inv = max(0.0, self.inv - dt)
        self.friend_t = max(0.0, self.friend_t - dt)
        self.power_t = max(0.0, self.power_t - dt)
        self.bomb_t = max(0.0, self.bomb_t - dt)
        self.update_player(dt)
        if self.ending is not None:
            return
        self.update_shots(dt)
        for e in self.enemies:
            if e.alive:
                self.update_enemy(e, dt)
        if self.boss is not None:
            self.update_boss(dt)
        if self.phase == "play" and self.mode == "normal":
            self.spawn_events(dt)
        for b in self.bullets:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
        self.bullets = [b for b in self.bullets if -12 < b[1] < H + 12 and -12 < b[0] < W + 12]
        self.update_items(dt)
        self.collide()
        self.enemies = [e for e in self.enemies if e.alive] + self.spawned
        self.spawned = []
        self.check_extra()
        if self.hype.fever_on != self.fever_was:
            self.fever_was = self.hype.fever_on
            if self.mode != "boss" and self.phase != "victory":
                au.music("fever" if self.fever_was else self.stage_music)
        # flow
        if self.phase == "intro" and self.intro_t >= 2.4:
            self.phase = "play"
        elif self.phase == "warning" and self.boss is not None and self.boss.state == "fight":
            self.phase = "play"
        elif self.phase == "clear":
            self.clear_t += dt
            if self.clear_t >= 1.0:
                self.start_tally()
        elif self.phase == "tally":
            self.update_tally(dt)
        elif self.phase == "victory":
            self.vic_t += dt
            if int(self.vic_t * 4) != int((self.vic_t - dt) * 4):
                self.parts.burst(random.uniform(40, W - 40), random.uniform(30, 120), 30,
                                 (rainbow(random.randrange(7)), "white", "yellow"), 110, 1.0)
                au.play("explode")
            if self.vic_t >= 5.0:
                self.end_game(True, "ALL 200 STAGES!")
        self.check_clear()

    def check_extra(self):
        while self.score >= self.next_extra:
            self.lives += 1
            self.extra_i += 1
            self.next_extra = EXTRA_LIVES[self.extra_i] if self.extra_i < len(EXTRA_LIVES) else self.next_extra + EXTRA_EVERY
            if self.hype.banners:
                self.say(self.px, self.py - 14, "1UP!", "mint")
                self.app.audio.play("extra")
            else:
                self.hype.banner("1UP!", "EXTRA KITTY", color="mint", dur=1.3, sound="extra")
            self.hype.shower(16, "hearts")

    def update_player(self, dt):
        inp = self.app.input
        if self.dead_t is not None:
            self.dead_t -= dt
            if self.dead_t <= 0:
                if self.lives <= 0:
                    self.end_game(False, f"STAGE {self.stage_n}")
                    return
                self.dead_t = None
                self.inv = 2.5
                self.px, self.py = W / 2, float(PY)
                self.vx = self.vy = 0.0
                self.bombs = max(self.bombs, 2)
                self.cancel_bullets()
            return
        dx = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        dy = (1 if inp.down("down") else 0) - (1 if inp.down("up") else 0)
        sp = 125 * (1 + 0.16 * self.lv("zoom"))
        if dx and dy:
            sp *= 0.7071
        k = min(1.0, dt * 18)     # quick ease in/out: smooth like a stick, still snappy
        self.vx += (dx * sp - self.vx) * k
        self.vy += (dy * sp - self.vy) * k
        self.px = max(10.0, min(W - 10.0, self.px + self.vx * dt))
        self.py = max(float(PY_MIN), min(float(PY_MAX), self.py + self.vy * dt))
        for i, p in enumerate(self.pals):
            kk = min(1.0, dt * (10 - i * 2))
            p[0] += (self.px + PAL_SLOTS[i][0] - p[0]) * kk
            p[1] += (self.py + PAL_SLOTS[i][1] - p[1]) * kk
        firing = inp.down("a") or self.autofire
        self.fire_t -= dt
        if firing and self.fire_t <= 0 and self.phase != "victory":
            self.fire()
            self.fire_t = 0.19 * 0.85 ** self.lv("rapid") * (0.6 if self.hype.fever_on else 1.0)
        sl = self.lv("seeker")
        if sl:
            self.seek_t -= dt
            if firing and self.seek_t <= 0:
                self.seek_t = (0.75, 0.55, 0.4)[sl - 1]
                for sd in ((-1, 1) if sl >= 3 else (-1 if self.shot_n % 2 else 1,)):
                    self.shots.append([self.px + sd * 6, self.py + 4, sd * 80.0, -120.0, 0.8, 0, 3, [], 2.0])
        if inp.hit("b"):
            self.bomb()

    def fire(self):
        x, y = self.px, self.py
        lance = self.lv("lance")
        if lance:
            self.shots.append([x, y - 2, 0.0, -340.0, 1 + 0.5 * lance, lance, 1, [], 1.2])
        else:
            self.shots.append([x, y - 2, 0.0, -300.0, 1.0, 0, 0, [], 1.2])
        for a in SPREAD[min(4, self.lv("spread") + (1 if self.power_t > 0 else 0))]:
            r = math.radians(a)
            for sd in (-1, 1):
                self.shots.append([x + sd * 3, y, math.sin(r) * 300 * sd, -math.cos(r) * 300, 0.7, 0, 0, [], 1.2])
        if self.hype.fever_on:     # hyper shot: a fan of rainbow stars
            for a in (-55, -40, -25, 25, 40, 55):
                r = math.radians(a)
                self.shots.append([x, y, math.sin(r) * 280, -math.cos(r) * 280, 1.0, 0, 4, [], 1.2])
        for i in range(self.npals()):
            p = self.pals[i]
            self.shots.append([p[0], p[1] - 2, 0.0, -300.0, 0.8, 0, 2, [], 1.2])
        self.shot_n += 1
        if self.shot_n % 2:
            self.app.audio.play("shoot")

    def seek_target(self, x, y):
        best, bd = None, 1e9
        for e in self.enemies:
            if self.hittable(e) and e.y < H - 10:
                d = (e.x - x) ** 2 + (e.y - y) ** 2
                if d < bd:
                    best, bd = (e.x, e.y), d
        b = self.boss
        if b is not None and b.state == "fight":
            wx, wy, _ = b.weak_pos()
            d = (wx - x) ** 2 + (wy - y) ** 2
            if d < bd:
                best = (wx, wy)
        return best

    def update_shots(self, dt):
        for sh in self.shots:
            sh[8] -= dt
            if sh[6] == 3:
                tgt = self.seek_target(sh[0], sh[1])
                if tgt is not None:
                    dx, dy = tgt[0] - sh[0], tgt[1] - sh[1]
                    d = max(1.0, math.hypot(dx, dy))
                    k = min(1.0, dt * 7)
                    sh[2] += (dx / d * 260 - sh[2]) * k
                    sh[3] += (dy / d * 260 - sh[3]) * k
                else:
                    sh[3] = max(-300.0, sh[3] - 400 * dt)
            sh[0] += sh[2] * dt
            sh[1] += sh[3] * dt
        self.shots = [sh for sh in self.shots if sh[8] > 0 and -10 < sh[1] < H + 10 and -10 < sh[0] < W + 10]

    # ---------------------------------------------------------------- enemies
    def update_enemy(self, e, dt):
        e.t += dt
        e.flash = max(0.0, e.flash - dt)
        s = e.state
        if s == "wait":
            if e.t >= e.delay:
                e.state, e.t, e.dist = ("parade" if e.parade else "enter"), 0.0, 0.0
                e.x, e.y = path_pos(e.path, 0.0, e.mirror)
        elif s in ("enter", "parade"):
            if 0 < e.fire_at <= e.dist and self.phase in ("intro", "play"):
                e.fire_at = -1.0
                n = self.st["burst"]
                for i in range(n):
                    self.enemy_shot(e, (i - (n - 1) / 2) * 12)
            if 0 < e.amb_at <= e.dist and self.phase == "play" and self.dead_t is None and e.y < PY_MIN - 20:
                e.amb_at = -1.0
                self.ambush(e)
                return
            e.dist += e.speed * dt
            if e.dist >= (len(e.path) - 1) * D.STEP:
                if s == "parade":
                    e.alive = False
                else:
                    e.state = "home"
            else:
                e.x, e.y = path_pos(e.path, e.dist, e.mirror)
        elif s == "home":
            sx, sy = self.slot(e)
            dx, dy = sx - e.x, sy - e.y
            d = math.hypot(dx, dy)
            step = e.speed * dt
            if d <= step + 0.5:
                e.x, e.y = sx, sy
                e.state, e.t = "form", 0.0
                e.entered = True
            else:
                e.x += dx / d * step
                e.y += dy / d * step
        elif s == "form":
            e.x, e.y = self.slot(e)
            if e.tele > 0:      # formation volley: glow, then fire
                e.tele -= dt
                if e.tele <= 0:
                    self.enemy_shot(e, 0)
            if e.kind == SPORE and self.phase == "play" and self.dead_t is None:
                e.aux -= dt
                if e.aux <= 0:
                    e.aux = self.st["fire_gap"] * random.uniform(0.8, 1.5) / self.spd
                    for a in ((-14, 0, 14) if self.tier >= 8 else (0,)):
                        self.enemy_shot(e, a)
        elif s == "dive":
            u = e.t / e.dur
            if u >= 1:
                if e.extra:
                    e.alive = False
                elif e.kind == URCHIN:     # finished its mine-laying pass: fly straight back
                    e.state = "home"
                else:
                    e.state = "home"
                    e.x, e.y = self.slot(e)[0], -16.0
                return
            e.x, e.y = bezier(e.bez, u)
            for sh in e.shots:
                if not sh[1] and u >= sh[0]:
                    sh[1] = True
                    self.enemy_shot(e, 0)
            if e.kind == URCHIN and 0.2 < u < 0.85:
                e.aux -= dt
                if e.aux <= 0:
                    e.aux = 0.4
                    self.add_mine(e.x, e.y + 4, 0.0, 22.0, 4.0)
        elif s == "dash":
            if e.t < 0.5:          # wind-up: shiver in place, then shoot down at Tama
                sx, sy = self.slot(e)
                e.x, e.y = sx + math.sin(e.t * 60) * 1.5, sy
            else:
                if e.vx == 0 and e.vy == 0:
                    cx, cy = self.centre()
                    a = math.atan2(cy - e.y, cx - e.x)
                    v = 200 * (0.85 + 0.15 * self.spd)
                    e.vx, e.vy = math.cos(a) * v, max(60.0, math.sin(a) * v)
                    self.app.audio.play("move")
                e.x += e.vx * dt
                e.y += e.vy * dt
                if e.y > H + 16 or e.x < -20 or e.x > W + 20:
                    e.state, e.vx, e.vy = "home", 0.0, 0.0
                    e.x, e.y = self.slot(e)[0], -16.0
        elif s == "kami":
            sp = min(230.0, 80 + e.t * 110)
            ang = math.atan2(e.vy, e.vx)
            cx, cy = self.centre()
            if e.y < cy - 12:
                want = math.atan2(cy - e.y, cx - e.x)
                diff = (want - ang + math.pi) % math.tau - math.pi
                ang += max(-2.2 * dt, min(2.2 * dt, diff))
            e.vx, e.vy = math.cos(ang) * sp, math.sin(ang) * sp
            e.x += e.vx * dt
            e.y += e.vy * dt
            if int(e.t * 20) != int((e.t - dt) * 20):
                self.parts.sparkle(e.x, e.y - 4, "orange")
            if e.y > H + 16 or e.x < -24 or e.x > W + 24 or e.y < -40:
                e.state, e.vx, e.vy = "home", 0.0, 0.0
                e.x, e.y = self.slot(e)[0], -16.0
        elif s == "free":
            if e.kind == MINE:
                k = min(1.0, dt * 1.5)
                e.vy += (16 - e.vy) * k
                e.vx -= e.vx * k
                e.aux -= dt
                if e.aux <= 0:
                    e.alive = False
                    n = 6 if self.tier >= 10 or self.mode == "boss" else 4
                    for i in range(n):
                        self.bshot(e.x, e.y, math.tau * i / n + 0.3, self.bullet_speed() * 0.55, 3)
                    self.parts.burst(e.x, e.y, 10, ("red", "orange", "yellow"), 60, 0.4)
            elif e.kind == GOLD:
                e.y = 24 + math.sin(e.t * 3) * 6
                if int(e.t * 15) != int((e.t - dt) * 15):
                    self.parts.sparkle(e.x - (8 if e.vx > 0 else -8), e.y, rainbow(int(e.t * 15)))
            e.x += e.vx * dt
            e.y += e.vy * dt
            if e.y > H + 14 or e.x < -30 or e.x > W + 30:
                e.alive = False

    def bullet_speed(self):
        return self.st.get("bv", 80) * self.spd

    def enemy_shot(self, e, spread):
        if self.dead_t is not None or e.y > PY_MIN - 10:
            return
        cx, cy = self.centre()
        sp = self.bullet_speed()
        a = math.atan2(cy - e.y, cx - e.x) + math.radians(spread)
        vx, vy = math.cos(a) * sp, max(math.sin(a) * sp, sp * 0.35)
        vx = max(-sp * 0.7, min(sp * 0.7, vx))
        self.bullets.append([e.x, e.y + 5, vx, vy, 0, False])

    def bshot(self, x, y, ang, sp, kind):
        if len(self.bullets) < 240:
            self.bullets.append([x, y, math.cos(ang) * sp, math.sin(ang) * sp, kind, False])

    def add_mine(self, x, y, vx, vy, fuse):
        m = self.spawn(MINE, 1)
        m.state, m.extra, m.x, m.y, m.vx, m.vy, m.aux = "free", True, x, y, vx, vy, fuse
        self.spawned.append(m)

    def spawn_events(self, dt):
        st = self.st
        # dives
        if self.stage_t >= self.dive_start and self.dead_t is None:
            self.dive_t -= dt
            if self.dive_t <= 0:
                left = sum(1 for e in self.enemies if not e.extra)
                rush = left <= 5
                self.dive_t = st["dive_gap"] / self.spd * random.uniform(0.75, 1.25) * (0.5 if rush else 1.0)
                self.launch_dive(st["dive_max"] + (1 if rush else 0))
        # formation volleys: one row glows, then fires together
        if st["volley"] > 0 and self.stage_t >= self.dive_start and self.dead_t is None:
            self.volley_t -= dt
            if self.volley_t <= 0:
                self.volley_t = st["volley"] * random.uniform(0.8, 1.2) / self.spd
                rows = sorted({e.row for e in self.enemies if e.state == "form" and not e.extra})
                if rows:
                    r = random.choice(rows)
                    for e in self.enemies:
                        if e.state == "form" and e.row == r and not e.extra:
                            e.tele = 0.5
        # meteor showers
        if "METEORS" in st["mods"]:
            self.meteor_t -= dt
            if self.meteor_t <= 0:
                self.meteor_t = random.uniform(2.5, 4.5)
                m = self.spawn(METEOR, 3)
                m.state, m.extra = "free", True
                m.x, m.y, m.vx, m.vy = random.uniform(20, W - 20), -10.0, random.uniform(-15, 15), random.uniform(45, 70)
                self.spawned.append(m)
        # the rare golden comet
        if 0 < self.gold_t <= self.stage_t:
            self.gold_t = -1.0
            g = self.spawn(GOLD, 4)
            side = random.choice((-1, 1))
            g.state, g.extra = "free", True
            g.x, g.y, g.vx = (-16.0 if side > 0 else W + 16.0), 24.0, side * 85.0
            self.spawned.append(g)
            self.hype.banner("GOLDEN COMET!", "SHOOT IT!", color="yellow", dur=1.2, scale=1, sound="coin")

    def ambush(self, e):
        side = 1 if e.x < W / 2 else -1
        if e.kind == DART:
            e.state, e.t, e.vx, e.vy = "dash", 0.5, 0.0, 0.0      # skip the wind-up: it is already moving
        elif e.kind == COMET:
            e.state, e.t, e.vx, e.vy = "kami", 0.0, side * 30.0, 60.0
        else:
            self.start_dive(e, side, 0)
            e.bez = [(e.x, e.y), (e.x + side * 40, e.y + 30), (self.px - side * 30, 150), (self.px + side * 20, H + 24)]
        self.app.audio.play("move")

    def launch_dive(self, maxd):
        ready = [e for e in self.enemies if e.state == "form" and not e.extra]
        divers = sum(1 for e in self.enemies if e.state in DIVING)
        if not ready or divers >= maxd:
            return
        e = random.choice(ready)
        if e.kind == SPORE and random.random() < 0.6:
            e = random.choice(ready)
        side = 1 if e.x < W / 2 else -1
        if e.kind == DART:
            e.state, e.t, e.vx, e.vy = "dash", 0.0, 0.0, 0.0
            return
        if e.kind == COMET:
            e.state, e.t, e.vx, e.vy = "kami", 0.0, side * 30.0, 40.0
            self.app.audio.play("move")
            return
        group = [e]
        if e.kind == PUFF:
            group += [o for o in ready if o is not e and o.kind in (MOTH, JELLY) and abs(o.col - e.col) <= 2
                      and o.row > e.row][:2]
        elif e.kind == MOTH:
            group += [o for o in ready if o is not e and o.kind == MOTH and abs(o.col - e.col) == 1 and o.row == e.row][:1]
        for i, g in enumerate(group):
            self.start_dive(g, side, (i - (len(group) - 1) / 2) * 16)
        self.app.audio.play("move")

    def start_dive(self, g, side, off):
        g.state, g.t = "dive", 0.0
        base = 2.5 * 130 / max(60.0, self.st.get("speed", 140))
        g.dur = max(1.4, random.uniform(0.9, 1.1) * base / max(0.7, self.spd))
        cx = self.px
        if g.kind == URCHIN:
            y2 = random.uniform(104, 118)
            g.bez = [(g.x, g.y), (g.x, y2 + 30), (W - g.x, y2 + 30), (W - g.x, g.y)]
            g.aux = 0.2
        else:
            g.bez = [(g.x, g.y), (g.x + side * 70, g.y - 20), (cx + off - side * 40, 150), (cx + off + side * 30, H + 24)]
        n = 0 if g.extra and self.mode != "boss" else self.st.get("shots", 1)
        if g.kind == MINI:
            n = 1 if self.mode == "boss" and self.boss is not None and self.boss.lv >= 2 else 0
        g.shots = [[random.uniform(0.15, 0.55), False] for _ in range(n)]

    # ---------------------------------------------------------------- boss
    def part_pos(self, b, i):
        p = b.parts[i]
        if b.kind == 4:     # RING GRUMP: moons orbit the planet, blocking shots while in front
            a = b.t * 1.5 + i * math.tau / 3
            return b.x + math.cos(a) * 36, b.y + 4 + math.sin(a) * 14, math.sin(a) > -0.2
        return b.x + p[0] + math.sin(b.t * 3 + i) * 2, b.y + p[1] + math.cos(b.t * 2.5 + i) * 1.5, True

    def update_boss(self, dt):
        b = self.boss
        b.t += dt
        b.flash = max(0.0, b.flash - dt)
        for p in b.parts:
            p[4] = max(0.0, p[4] - dt)
        if b.state == "enter":
            u = min(1.0, b.t / 2.8)
            b.y = -40 + (b.hy + 40) * ease_out(u)
            if u >= 1:
                b.state, b.rest = "fight", 1.0
            return
        if b.state == "dying":
            b.at += dt
            if int(b.at * 10) != int((b.at - dt) * 10):
                self.parts.burst(b.x + random.uniform(-b.bw / 2, b.bw / 2), b.y + random.uniform(-b.bh / 2, b.bh / 2), 14,
                                 ("white", "yellow", "orange", "pink"), 90, 0.6)
                self.app.audio.play("explode")
                self.app.shake(3, 0.15)
            if b.at >= 2.2:
                self.parts.burst(b.x, b.y, 70, ("white", "yellow", "orange", "pink", "sky"), 160, 1.2)
                self.hype.shower(80, "stars")
                self.hype.shower(50, "confetti")
                self.hype.flash("white", 0.4)
                self.app.shake(6, 0.6)
                self.app.audio.play("win")
                self.boss = None
            return
        # fight
        if b.atk is None:
            b.mt += dt
            b.rest -= dt
            if b.rest <= 0:
                self.begin_attack(b)
        else:
            if b.atk not in ("laser", "charge", "teleport"):
                b.mt += dt * 0.4
            b.at += dt
            if self.run_attack(b, dt):
                b.atk = None
                b.rest = self.st["rest"] * (1 - 0.12 * b.phase) * (1.25 if b.lv == 0 else 1.0)
        if b.atk not in ("charge", "teleport"):
            amp = 96 if b.kind == 2 else (34 if b.kind == 5 else 70)
            tx = b.cx + math.sin(b.mt * 0.7) * amp
            old = b.x
            b.x += (tx - b.x) * min(1.0, dt * 3)
            b.y += (b.hy + math.sin(b.mt * 1.4) * 5 - b.y) * min(1.0, dt * 3)
            if abs(b.x - old) > 0.05:
                b.face = 1 if b.x > old else -1
        # phases
        if b.phase < b.nphase - 1 and b.hp <= b.maxhp * (1 - (b.phase + 1) / b.nphase):
            b.phase += 1
            b.atk, b.rest = None, 1.2
            self.cancel_bullets()
            self.hype.banner("ANGRY!!", f"PHASE {b.phase + 1}", color="red", dur=1.2, sound="warning")
            self.hype.flash("red", 0.25)
            self.hype.hitstop(0.12)
            self.app.shake(4, 0.4)

    def begin_attack(self, b):
        names = b.phases[b.phase]
        b.atk = names[b.ai % len(names)]
        b.ai += 1
        b.at, b.an = 0.0, 0
        a, lv, ph = b.atk, b.lv, b.phase
        if a == "summon" and sum(1 for e in self.enemies if e.kind == MINI) >= 8:
            b.atk = "fan"
        if a == "laser":
            xs = [self.px]
            if lv >= 1 or ph >= 1:
                xs += [self.px - 70, self.px + 70]
            if lv >= 3:
                xs += [self.px - 140, self.px + 140]
            if b.kind == 3 and not any(p[5] for p in b.parts):
                xs = [self.px]
            b.lx = [max(8.0, min(W - 8.0, x)) for x in xs]
        elif a == "rain":
            n = min(18, 6 + 2 * lv + ph)
            cols = random.sample(range(20), n)
            b.rx = [8 + c * 16 + random.uniform(-3, 3) for c in cols]
        elif a == "wall":
            b.gap = random.uniform(50, W - 50)
        elif a == "charge":
            b.tx = max(40.0, min(W - 40.0, self.px))
        elif a == "teleport":
            choices = [x for x in (70.0, 115.0, 160.0, 205.0, 250.0) if abs(x - b.cx) > 50]
            b.tx = random.choice(choices)
        elif a == "spiral":
            b.dir = 1 if b.ai % 2 else -1
            b.ang = random.uniform(0, math.tau)

    def muzzle(self, b):
        wx, wy, _ = b.weak_pos()
        return wx, wy

    def run_attack(self, b, dt):
        """Advance the current attack; True when it is over. Every attack starts with a readable telegraph."""
        a, at, lv, ph = b.atk, b.at, b.lv, b.phase
        bv = self.bullet_speed()
        mx, my = self.muzzle(b)
        cx, cy = self.centre()
        au = self.app.audio
        if a == "fan":
            tele, vol, per = 0.55, min(3, 1 + (lv + ph) // 2), 0.5
            te = at - tele
            while te >= 0 and b.an < vol and te >= b.an * per:
                n = 5 + lv + ph
                n += 1 - n % 2
                base = math.atan2(cy - my, cx - mx) if b.an % 2 == 0 else math.pi / 2
                for i in range(n):
                    self.bshot(mx, my, base + math.radians(-30 + 60 * i / (n - 1)), bv, 0)
                b.an += 1
                au.play("pop")
            return te >= vol * per
        if a == "aim":
            tele, n, per = 0.45, 3 + lv + ph, 0.16
            te = at - tele
            while te >= 0 and b.an < n and te >= b.an * per:
                srcs = [self.part_pos(b, i) for i, p in enumerate(b.parts) if p[5]] if b.kind == 1 else []
                sx, sy = (srcs[b.an % len(srcs)][0], srcs[b.an % len(srcs)][1]) if srcs else (mx, my)
                self.bshot(sx, sy, math.atan2(cy - sy, cx - sx), bv * 1.45, 2)
                b.an += 1
                au.play("tin")
            return te >= n * per + 0.2
        if a == "ring":
            tele, rings, per = 0.6, 1 + (1 if lv >= 2 else 0) + (1 if ph >= 2 else 0), 0.55
            te = at - tele
            while te >= 0 and b.an < rings and te >= b.an * per:
                n = 14 + 3 * lv + 2 * ph
                for i in range(n):
                    self.bshot(b.x, b.y + 4, math.tau * i / n + b.an * math.pi / n, bv * 0.75, 1)
                b.an += 1
                au.play("pop")
            return te >= rings * per + 0.2
        if a == "spiral":
            tele, dur = 0.5, 2.0 + 0.3 * lv
            per = max(0.07, 0.11 - 0.01 * lv)
            arms = 2 + lv // 2 + (1 if ph >= 2 else 0)
            te = at - tele
            while te >= 0 and te < dur and b.an * per <= te:
                for k in range(arms):
                    self.bshot(b.x, b.y + 4, b.ang + math.tau * k / arms + b.dir * 2.2 * b.an * per, bv * 0.7, 0)
                b.an += 1
            return te >= dur
        if a == "laser":
            tele, fire = 0.95, 0.55
            if b.an == 0 and at >= tele:
                b.an = 1
                au.play("explode")
                self.app.shake(2, 0.3)
            return at >= tele + fire
        if a == "rain":
            tele = 0.7
            te = at - tele
            while te >= 0 and b.an < len(b.rx) and te >= b.an * 0.07:
                self.bshot(b.rx[b.an], -4.0, math.pi / 2, bv * 1.05, 1)
                b.an += 1
            return te >= len(b.rx) * 0.07 + 0.3
        if a == "summon":
            tele, n, per = 0.5, 3 + lv, 0.22
            te = at - tele
            while te >= 0 and b.an < n and te >= b.an * per:
                m = self.spawn(MINI, 1 + self.tier // 8)
                m.extra = True
                m.x, m.y = b.x + random.uniform(-b.bw / 3, b.bw / 3), b.y + 6
                self.start_dive(m, random.choice((-1, 1)), random.uniform(-30, 30))
                self.spawned.append(m)
                b.an += 1
                au.play("bubble")
            return te >= n * per + 0.2
        if a == "mines":
            tele, n, per = 0.4, 3 + lv, 0.18
            te = at - tele
            while te >= 0 and b.an < n and te >= b.an * per:
                self.add_mine(b.x, b.y + 10, random.uniform(-70, 70), random.uniform(20, 50), 3.0)
                b.an += 1
                au.play("pop")
            return te >= n * per + 0.2
        if a == "charge":
            tele = 0.8
            if at < tele:
                b.x += (b.tx - b.x) * min(1.0, dt * 5)
                return False
            te = at - tele
            b.x = b.tx
            if te < 0.45:
                b.y = b.hy + (150 - b.hy) * ease_out(te / 0.45)
            elif te < 0.6:
                b.y = 150.0
            elif te < 1.4:
                b.y = 150 - (150 - b.hy) * (te - 0.6) / 0.8
            if b.an == 0 and te >= 0.45:
                b.an = 1
                self.app.shake(3, 0.3)
                au.play("boom")
                if lv >= 1:
                    for i in range(10):
                        self.bshot(b.x, b.y, math.pi + math.pi * i / 9, bv * 0.7, 0)
            if te >= 1.4:
                b.cx = W / 2
                return True
            return False
        if a == "wall":
            tele, rows, per = 0.6, 1 + lv // 2 + (1 if ph >= 2 else 0), 1.0
            te = at - tele
            while te >= 0 and b.an < rows and te >= b.an * per:
                if b.an > 0:
                    b.gap = max(40.0, min(W - 40.0, b.gap + random.choice((-60, 60))))
                x = 8
                while x < W - 4:
                    if abs(x - b.gap) > 24:
                        self.bshot(x, b.y + 16, math.pi / 2, bv * 0.55, 0)
                    x += 13
                b.an += 1
                au.play("pop")
            return te >= rows * per
        if a == "teleport":
            if at < 0.45:
                b.alpha = 1 - at / 0.45
            elif b.an == 0:
                b.an = 1
                b.cx = b.x = b.tx
                b.mt = 0.0
                au.play("bubble")
            else:
                b.alpha = min(1.0, (at - 0.45) / 0.4)
                if b.an == 1 and b.alpha >= 1 and (lv >= 1 or ph >= 1):
                    b.an = 2
                    n = 10 + 2 * lv
                    for i in range(n):
                        self.bshot(b.x, b.y + 4, math.tau * i / n, bv * 0.7, 1)
            if at >= 1.0:
                b.alpha = 1.0
                return True
            return False
        return True

    def hurt_boss(self, dmg, crit=False, x=0.0, y=0.0):
        b = self.boss
        b.hp -= dmg
        self.score += (10 if crit else 2) * self.hype.mult
        if crit:
            b.flash = 0.05
            self.parts.sparkle(x, y, "yellow")
            if self.tin_t <= 0:
                self.tin_t = 0.09
                self.app.audio.play("tin")
        if b.hp <= 0:
            self.boss_die()

    def break_part(self, b, i):
        p = b.parts[i]
        p[5] = False
        x, y, _ = self.part_pos(b, i)
        self.parts.burst(x, y, 24, ("white", "yellow", "pink", "lavender"), 100, 0.7)
        self.add(3000 + 300 * self.tier, x, y - 8, "lime")
        self.say(x, y - 18, "BREAK!", "white")
        self.broken += 1
        self.hype.hitstop(0.06)
        self.hype.hit()
        self.app.shake(3, 0.2)
        self.app.audio.play("explode")
        self.hurt_boss(b.maxhp * D.BOSSES[b.kind]["parts"][i][3] * 0.5)

    def boss_die(self):
        b = self.boss
        if b.state == "dying":
            return
        b.state, b.at, b.atk = "dying", 0.0, None
        b.hp = 0
        self.cancel_bullets()
        for e in self.enemies:
            if e.extra and e.alive:
                e.alive = False
                self.parts.burst(e.x, e.y, 8, art.KIND_COLORS[e.kind], 60, 0.5)
        self.hype.hitstop(0.25)
        self.hype.slowmo(0.3, 1.6)
        self.hype.flash("white", 0.35)
        self.hype.banner(f"{b.name} DOWN!", rainbow=True, dur=2.2, sound="bossdown")
        self.app.shake(6, 0.8)
        self.app.audio.stop_music()

    def shot_boss(self, sh):
        b = self.boss
        if b.state == "dying":
            return
        for i, p in enumerate(b.parts):
            if not p[5]:
                continue
            x, y, front = self.part_pos(b, i)
            if front and (sh[0] - x) ** 2 + (sh[1] - y) ** 2 <= (p[2] + 2) ** 2:
                sh[8] = 0
                if b.state == "fight":
                    p[3] -= sh[4]
                    p[4] = 0.06
                    self.score += 2 * self.hype.mult
                    if p[3] <= 0:
                        self.break_part(b, i)
                return
        if abs(sh[0] - b.x) > b.bw / 2 or abs(sh[1] - b.y) > b.bh / 2:
            return
        sh[8] = 0
        if b.state != "fight" or b.alpha < 0.5:
            self.parts.sparkle(sh[0], sh[1], "gray")
            return
        wx, wy, wr = b.weak_pos()
        if (sh[0] - wx) ** 2 + (sh[1] - wy) ** 2 <= (wr + 2) ** 2:
            self.hurt_boss(sh[4] * 2, True, sh[0], sh[1])
        else:
            self.hurt_boss(sh[4])

    # ---------------------------------------------------------------- items
    def drop(self, x, y, kind):
        if kind == "M":
            self.items.append([x, y, random.uniform(-20, 20), -50.0, "M", 0.0])
        else:
            self.items.append([x, y, 0.0, 34.0, kind, 0.0])

    def cancel_bullets(self, near=None):
        cx, cy = self.centre()
        keep = []
        bits = sum(1 for it in self.items if it[4] == "c")
        for b in self.bullets:
            if near is not None and (b[0] - cx) ** 2 + (b[1] - cy) ** 2 > near * near:
                keep.append(b)
                continue
            if bits < 140:
                self.items.append([b[0], b[1], random.uniform(-30, 30), random.uniform(-40, -10), "c", 0.0])
                bits += 1
        self.bullets = keep

    def update_items(self, dt):
        cx, cy = self.centre()
        alive = self.dead_t is None
        mag = (0, 60, 130)[self.lv("magnet")]
        keep = []
        for it in self.items:
            it[5] += dt
            if it[4] == "c":
                if it[5] < 0.3 or not alive:
                    it[0] += it[2] * dt
                    it[1] += it[3] * dt
                    if it[5] > 1.5:
                        continue
                else:
                    dx, dy = cx - it[0], cy - it[1]
                    d = max(1.0, math.hypot(dx, dy))
                    v = 160 + it[5] * 200
                    it[0] += dx / d * v * dt
                    it[1] += dy / d * v * dt
            else:
                dx, dy = cx - it[0], cy - it[1]
                d = math.hypot(dx, dy)
                if alive and d < mag:
                    it[0] += dx / max(1.0, d) * 170 * dt
                    it[1] += dy / max(1.0, d) * 170 * dt
                else:
                    if it[4] == "M":
                        it[3] = min(70.0, it[3] + 120 * dt)
                        it[2] *= max(0.0, 1 - dt)
                    else:
                        it[2] = math.sin(it[5] * 3) * 14
                    it[0] += it[2] * dt
                    it[1] += it[3] * dt
                if it[1] > H + 6:
                    if it[4] == "M" and self.medal_i > 0:
                        self.medal_i = 0
                        self.say(it[0], H - 18, "CHAIN LOST", "gray")
                    continue
            keep.append(it)
        self.items = keep

    def collect(self, it):
        k, au = it[4], self.app.audio
        x, y = it[0], it[1]
        t = self.tier
        if k == "c":
            self.score += 10 * self.hype.mult
            return
        if k == "M":
            v = MEDALS[min(self.medal_i, len(MEDALS) - 1)]
            self.medal_i += 1
            self.add(v, x, y - 8, "orange")
            au.play("coin")
            if self.medal_i == len(MEDALS):
                self.hype.banner("MAX MEDAL!", "5000 EACH", color="orange", dur=1.2, scale=1)
            return
        au.play("powerup")
        if k == "P":
            self.power_t = 20.0
            self.say(x, y - 10, "POWER UP!", "yellow")
        elif k == "F":
            self.friend_t = 25.0
            self.say(x, y - 10, "FRIEND STAR!", "pink")
        elif k == "B":
            if self.bombs < 3 + self.lv("bombs"):
                self.bombs += 1
                self.say(x, y - 10, "BOMB +1", "red")
            else:
                self.add(2000, x, y - 10, "red")
        elif k == "S":
            self.shield = min(self.lv("shield") + 2, self.shield + 1)
            self.say(x, y - 10, "BUBBLE!", "mint")
        elif k == "$":
            self.add(3000 * (1 + t // 4), x, y - 10, "orange")
            self.hype.shower(20, "coins")
            au.play("coin")
        elif k == "L":
            self.hype.jackpot(15000 + 1500 * t, "LUCKY STAR!")

    # ---------------------------------------------------------------- collisions
    def collide(self):
        for sh in self.shots:
            for e in self.enemies:
                if sh[8] <= 0:
                    break
                if e.uid in sh[7] or not self.hittable(e):
                    continue
                w, h = SIZES[e.kind]
                if abs(sh[0] - e.x) <= w / 2 + 1.5 and abs(sh[1] - e.y) <= h / 2 + 2:
                    self.damage(e, sh[4])
                    if sh[5] > 0:
                        sh[5] -= 1
                        sh[7].append(e.uid)
                    else:
                        sh[8] = 0
            if sh[8] > 0 and self.boss is not None:
                self.shot_boss(sh)
        self.shots = [sh for sh in self.shots if sh[8] > 0]
        if self.dead_t is not None or self.phase == "victory":
            return
        cx, cy = self.centre()
        hb = self.hitbox()
        keep = []
        for it in self.items:
            if (it[0] - cx) ** 2 + (it[1] - cy) ** 2 < (8 if it[4] == "c" else 12) ** 2:
                self.collect(it)
            else:
                keep.append(it)
        self.items = keep
        if self.inv > 0:
            return
        graze = self.lv("focus") >= 2
        for b in self.bullets:
            r = 2 if b[4] == 1 else 1
            if abs(b[0] - cx) <= hb + r and abs(b[1] - cy) <= hb + r:
                b[1] = H + 99
                self.hurt()
                return
            if graze and not b[5] and abs(b[0] - cx) < 12 and abs(b[1] - cy) < 12:
                b[5] = True
                self.score += 20 * self.hype.mult
                self.hype.fever_add(0.006)
                self.parts.sparkle(b[0], b[1], "white")
        b = self.boss
        if b is not None and b.state == "fight":
            if b.atk == "laser" and 0.95 <= b.at < 1.5:
                for x in b.lx:
                    if abs(cx - x) <= 5 + hb - 1:
                        self.hurt()
                        return
            if abs(b.x - cx) <= b.bw / 2 + hb - 2 and abs(b.y - cy) <= b.bh / 2 + hb - 2 and b.alpha >= 0.5:
                self.hurt()
                return
        for e in self.enemies:
            if not e.alive or e.parade or e.kind == GOLD or e.state not in HARMFUL or not self.solid(e):
                continue
            w, h = SIZES[e.kind]
            if abs(e.x - cx) <= w / 2 + hb - 1 and abs(e.y - cy) <= h / 2 + hb - 1:
                self.kill_enemy(e)
                self.hurt()
                return

    def damage(self, e, dmg):
        e.hp -= dmg
        if e.hp > 0:
            if e.flash <= 0:
                self.app.audio.play("tin")
            e.flash = 0.12
            return
        self.kill_enemy(e)

    def kill_enemy(self, e):
        if not e.alive:
            return
        e.alive = False
        t = self.tier
        au = self.app.audio
        diving = e.state in DIVING
        self.parts.burst(e.x, e.y, 16, art.KIND_COLORS[e.kind], 80, 0.6)
        au.play("explode")
        if e.kind == GOLD and not e.parade:
            self.parts.burst(e.x, e.y, 40, ("yellow", "orange", "white"), 140, 1.0)
            self.hype.jackpot(20000 + 2000 * t, f"GOLDEN COMET +{(20000 + 2000 * t) * self.hype.mult}")
            self.hype.hit()
            return
        if e.parade:
            self.hits += 1
            sq = self.squads[e.group]
            sq[1] += 1
            if e.kind == GOLD:
                self.add(5000 + 500 * t, e.x, e.y - 8, "yellow")
                self.hype.shower(24, "coins")
                au.play("coin")
            else:
                self.add(100 + 20 * t, e.x, e.y - 8, "yellow")
            if sq[1] == sq[0]:
                self.add(1000 + 200 * t, e.x, e.y - 18, "lime")
                self.say(e.x, e.y - 28, "WAVE PERFECT!", "lime")
                au.play("bonus")
            self.hype.hit(fever=0.02)
            return
        base = KINDS[e.kind][3 if diving else 2]
        pts = int(base * (1 + 0.1 * t)) // 10 * 10 + self.hype.combo_bonus(5)
        self.add(pts, e.x, e.y - 8, "mint" if diving else "yellow")
        self.hype.hit(fever=0.028)
        if not e.extra and not e.entered and e.group >= 0:
            sq = self.squads[e.group]
            sq[1] += 1
            if sq[1] == sq[0]:
                self.squad_wipes += 1
                self.say(e.x, e.y - 18, "SQUAD!", "lime")
                au.play("bonus")
        if e.cap >= 0:
            self.drop(e.x, e.y, "L" if self.hype.lucky(0.015) else D.CAPSULES[e.cap])
        if e.kind in (PUFF, SHELL) or (diving and random.random() < 0.3):
            self.drop(e.x, e.y, "M")
        if e.kind == PUFF and diving and self.friend_t <= 0 and random.random() < 0.35:
            self.drop(e.x + 6, e.y, "F")
        if e.kind == BLOB:
            for sd in (-1, 1):
                m = self.spawn(MINI, 1)
                m.extra = True
                m.x, m.y = e.x + sd * 5, e.y
                self.start_dive(m, sd, sd * 12)
                self.spawned.append(m)

    def hurt(self):
        au = self.app.audio
        cx, cy = self.centre()
        if self.shield > 0:
            self.shield -= 1
            self.inv = 1.2
            self.cancel_bullets(48)
            self.parts.burst(cx, cy, 20, ("mint", "white", "sky"), 90, 0.5)
            au.play("pop")
            self.say(cx, cy - 18, "POP!", "mint")
            self.app.shake(2, 0.2)
            return
        self.lives -= 1
        self.deaths += 1
        self.dead_t = 1.6
        self.friend_t = self.power_t = 0.0
        self.medal_i = 0
        self.hype.break_combo()
        au.play("boom")
        self.app.shake(4, 0.4)
        self.hype.flash("red", 0.2)
        self.parts.burst(cx, cy, 30, ("orange", "yellow", "white", "pink"), 110, 1.0)

    def bomb(self):
        if self.bombs <= 0 or self.dead_t is not None or self.phase not in ("intro", "play", "warning"):
            return
        self.bombs -= 1
        self.bomb_t = 0.9
        self.bomb_x, self.bomb_y = self.centre()
        self.inv = max(self.inv, 1.6)
        self.cancel_bullets()
        pouch = self.lv("bombs")
        for e in list(self.enemies):
            if e.alive and e.state != "wait" and e.kind != GOLD and -10 < e.y < H + 10 and not e.parade:
                self.damage(e, 5 + 2 * pouch)
        b = self.boss
        if b is not None and b.state == "fight":
            if b.atk == "laser":
                b.atk = None
                b.rest = 1.0
            self.hurt_boss(b.maxhp * (0.035 + 0.01 * pouch))
        self.hype.flash("white", 0.3)
        self.hype.hitstop(0.08)
        self.app.shake(5, 0.5)
        self.app.audio.play("boom")
        self.say(self.bomb_x, self.bomb_y - 20, "COMET BURST!", "orange")

    # ---------------------------------------------------------------- draw
    def render(self, s):
        t = self.t
        s.blit(self.bg, (0, 0))
        if self.warp > 0.05:
            ln = int(self.warp * 14)
            for x, y, z in self.stars.s:
                s.fill(col(("darkgray", "lavender", "white")[z - 1]), (int(x), int(y) - ln * z // 2, 1, 1 + ln * z // 2))
        else:
            self.stars.draw(s, t)
        b = self.boss
        if b is not None and b.state == "fight":
            self.draw_tells(s, b)
        for it in self.items:
            if it[4] == "c":
                s.fill(col("sky" if int(t * 12 + it[0]) % 2 else "white"), (int(it[0]) - 1, int(it[1]) - 1, 2, 2))
            else:
                art.capsule(s, it[4], int(it[0]), int(it[1]), t + it[5])
        for e in self.enemies:
            if e.state == "wait":
                continue
            if e.kind == MINE:
                glow = int(t * (16 if e.aux < 1.0 else 3)) % 2 == 1
            else:
                glow = (e.kind == SPORE and e.state == "form" and e.aux < 0.45 and self.phase == "play") or \
                       (e.kind == DART and e.state == "dash" and e.t < 0.5) or e.tele > 0
            art.enemy(s, e.kind, int(e.x), int(e.y), t + e.seed, e.flash > 0, glow, not self.solid(e), int(math.ceil(e.hp)),
                      1 if e.vx >= 0 else -1)
            if e.cap >= 0 and e.state != "free" and int(t * 6) % 2:
                pygame.draw.circle(s, col("yellow"), (int(e.x), int(e.y)), 9, 1)
        if b is not None:
            self.draw_boss(s, b)
        for sh in self.shots:
            x, y, kd = int(sh[0]), int(sh[1]), sh[6]
            if kd == 1:
                s.fill(col("sky"), (x - 1, y - 5, 3, 9))
                s.fill(col("white"), (x, y - 5, 1, 7))
            elif kd == 2:
                s.fill(col("pink"), (x - 1, y - 3, 2, 5))
            elif kd == 3:
                s.fill(col("lime"), (x - 1, y, 3, 1))
                s.fill(col("lime"), (x, y - 1, 1, 3))
            elif kd == 4:
                c = col(rainbow(x // 8, t))
                s.fill(c, (x - 1, y, 3, 1))
                s.fill(c, (x, y - 1, 1, 3))
            else:
                s.fill(col("yellow"), (x - 1, y - 3, 3, 6))
                s.fill(col("white"), (x, y - 3, 1, 3))
        self.draw_player(s)
        for bl in self.bullets:
            x, y, kd = int(bl[0]), int(bl[1]), bl[4]
            if kd == 1:
                pygame.draw.circle(s, col("black"), (x, y), 4)
                pygame.draw.circle(s, col("hotpink"), (x, y), 3)
                s.fill(col("white"), (x - 1, y - 1, 2, 2))
            elif kd == 2:
                s.fill(col("black"), (x - 2, y - 3, 4, 7))
                s.fill(col("red"), (x - 1, y - 2, 2, 5))
                s.fill(col("white"), (x - 1, y - 2, 1, 1))
            else:
                pygame.draw.circle(s, col("black"), (x, y), 3)
                pygame.draw.circle(s, col("orange" if kd == 3 else "pink"), (x, y), 2)
                s.fill(col("white"), (x - 1, y - 1, 1, 1))
        if b is not None and b.state == "fight" and b.atk == "laser" and b.at >= 0.95:
            for x in b.lx:
                xi = int(x)
                fl = int(t * 30) % 2
                s.fill(col("hotpink"), (xi - 5, int(b.y) + 8, 10, H))
                s.fill(col("white"), (xi - 2 - fl, int(b.y) + 8, 4 + fl * 2, H))
        if self.bomb_t > 0:
            r = int((0.9 - self.bomb_t) / 0.9 * 330)
            pygame.draw.circle(s, col("white"), (int(self.bomb_x), int(self.bomb_y)), r, 3)
            if r > 6:
                pygame.draw.circle(s, col("yellow"), (int(self.bomb_x), int(self.bomb_y)), r - 5, 2)
        self.parts.draw(s)
        self.floats.draw(s)
        self.draw_hud(s)
        if self.phase == "intro":
            self.draw_intro(s)
        elif self.phase == "warning":
            self.draw_warning(s)
        elif self.phase == "tally" and self.tally is not None:
            self.draw_tally(s)

    def draw(self, s):
        super().draw(s)
        if self.paused:
            self.draw_power(s, 160)

    def draw_power(self, s, y):
        """Pause screen: the upgrades collected so far."""
        owned = [u for u in POOL if self.lv(u.id) > 0]
        if not owned:
            return
        x0 = W // 2 - len(owned) * 13 + 13
        for i, u in enumerate(owned):
            cx = x0 + i * 26
            pygame.draw.circle(s, col(u.color), (cx, y), 12)
            pygame.draw.circle(s, col("ink"), (cx, y), 10)
            u.icon(s, cx, y, self.t)
            for p in range(u.max):
                s.fill(col("yellow" if p < self.lv(u.id) else "darkgray"), (cx - u.max * 2 + p * 4, y + 14, 3, 3))

    def draw_player(self, s):
        t = self.t
        if self.dead_t is not None:
            return
        for i in range(self.npals()):
            p = self.pals[i]
            temp = i >= self.lv("pals")
            if not temp or self.friend_t > 3 or int(t * 8) % 2:
                s.blit(sprite("star"), (int(p[0]) - 3, int(p[1]) - 3 + int(math.sin(t * 6 + i) * 2)))
        if self.inv > 0 and int(self.inv * 12) % 2:
            return
        x, y = int(self.px), int(self.py)
        bob = int(math.sin(t * 5) * 1)
        flame = int(t * 20) % 2
        s.fill(col("orange" if flame else "yellow"), (x - 2, y + 16 + bob, 4, 2 + flame + (2 if self.vy < -20 else 0)))
        s.blit(sprite("kitty"), (x - 8, y + bob))
        if self.lv("focus") >= 1:
            cx, cy = self.centre()
            s.fill(col("hotpink" if int(t * 6) % 2 else "white"), (int(cx) - 1, int(cy) - 1, 2, 2))
        if self.shield > 0:
            bubble(s, x, y + 8, 12, t, "mint")
            if self.shield > 1:
                pygame.draw.circle(s, col("white"), (x, y + 8), 14, 1)

    def draw_boss(self, s, b):
        t = self.t
        if b.alpha < 1 and int(t * 30) % 3 >= int(b.alpha * 3):
            return
        parts = []
        for i, p in enumerate(b.parts):
            x, y, front = self.part_pos(b, i)
            parts.append((int(x), int(y), p[2], p[5], p[4], front))
        look = max(-2, min(2, int((self.px - b.x) / 30)))
        ox = int(math.sin(t * 50) * 2) if b.atk == "charge" and b.at < 0.8 else 0
        art.boss(s, b, int(b.x) + ox, int(b.y), t, parts, look)
        if b.atk is not None and b.at < 0.6 and b.atk in ("fan", "aim", "ring", "spiral", "summon", "mines"):
            mx, my = self.muzzle(b)
            r = int(14 * (1 - b.at / 0.6)) + 2
            pygame.draw.circle(s, col("white" if int(t * 20) % 2 else "yellow"), (int(mx), int(my)), r, 1)

    def draw_tells(self, s, b):
        """Telegraphs drawn under everything: laser warning lines, rain markers, wall preview, charge lane."""
        t = self.t
        blink = int(t * 12) % 2
        if b.atk == "laser" and b.at < 0.95:
            for x in b.lx:
                c = col("red" if blink else "white")
                yy = int(b.y) + 10
                while yy < H:
                    s.fill(c, (int(x), yy, 1, 4))
                    yy += 7
                draw_text(s, "!", int(x) - 2, PY_MIN - 12, "red" if blink else "yellow", shadow=None)
        elif b.atk == "rain" and b.at < 0.9:
            for x in b.rx:
                xi = int(x)
                pygame.draw.polygon(s, col("yellow" if blink else "orange"), [(xi - 3, 14), (xi + 3, 14), (xi, 18)])
        elif b.atk == "wall" and b.at < 0.6:
            yy = int(b.y) + 16
            x = 8
            while x < W - 4:
                if abs(x - b.gap) > 24:
                    s.fill(col("pink" if blink else "white"), (x - 1, yy, 3, 2))
                x += 13
            draw_text(s, "{}", int(b.gap) - 6, yy - 3, "lime", shadow=None)
        elif b.atk == "charge" and b.at < 0.8:
            for sx in (-1, 1):
                x = int(b.tx + sx * b.bw / 2)
                yy = int(b.y) + 10
                while yy < H:
                    s.fill(col("red" if blink else "orange"), (x, yy, 1, 3))
                    yy += 6
        elif b.atk == "teleport" and b.an == 0:
            r = int(4 + (0.45 - min(0.45, b.at)) * 40)
            pygame.draw.circle(s, col("hotpink"), (int(b.tx), int(b.hy)), r, 1)

    def draw_hud(self, s):
        draw_text(s, f"{self.score:07d}", 4, 2, "white")
        draw_text(s, f"@{max(0, self.lives)}", 49, 2, "pink")
        b = self.boss
        if b is not None and self.phase != "warning":
            boss_bar(s, b.name, b.hp, b.maxhp, self.t)
        else:
            draw_text(s, f"HI {max(self.best, self.score):07d}", W // 2, 2, "lavender", align="center")
        c = "red" if self.mode == "boss" else ("mint" if self.mode == "bonus" else "yellow")
        draw_text(s, f"STAGE {self.stage_n}", W - 4, 2, c, align="right")
        y = H - 8
        for i in range(min(self.bombs, 6)):
            x = 6 + i * 8
            pygame.draw.circle(s, col("black"), (x, y + 3), 4)
            pygame.draw.circle(s, col("red"), (x, y + 3), 3)
            s.fill(col("white"), (x - 1, y + 1, 1, 1))
        x0 = 8 + min(self.bombs, 6) * 8
        for i in range(min(self.shield, 4)):
            pygame.draw.circle(s, col("mint"), (x0 + i * 8, y + 3), 3, 1)
        if self.medal_i > 0:
            v = MEDALS[min(self.medal_i, len(MEDALS) - 1)]
            draw_text(s, f"MEDAL {v}", W // 2, y, "orange", align="center")
        if not self.hype.fever_on:
            x = W - 44
            s.fill(col("black"), (x - 1, y + 1, 42, 5))
            s.fill(col("darkgray"), (x, y + 2, 40, 3))
            w = int(40 * self.hype.fever)
            s.fill(col(rainbow(0, self.t) if self.hype.fever > 0.8 else "peach"), (x, y + 2, w, 3))
            draw_text(s, "FEVER", x - 32, y, "gray", shadow=None)

    def draw_intro(self, s):
        a = self.intro_t
        drop = int((1 - ease_out(min(1.0, a / 0.25))) * -60) + int(ease_out(max(0.0, (a - 2.1) / 0.3)) * -80)
        st = self.st
        new = st.get("new", -1)
        tall = 44 if new < 0 else 62
        y0 = 100 + drop
        if self.mode == "bonus":
            panel(s, (40, y0, 240, 40), fill="ink", border="mint")
            draw_text(s, "BONUS PARADE!", W // 2, y0 + 6, "mint", 2, align="center", outline="ink")
            draw_text(s, "SHOOT THEM ALL - THEY CAN'T SHOOT", W // 2, y0 + 26, "white", align="center")
            return
        panel(s, (60, y0, 200, tall), fill="ink", border="yellow")
        draw_text(s, f"STAGE {self.stage_n}", W // 2, y0 + 6, "yellow", 2, align="center", outline="ink")
        mods = st.get("mods", [])
        sub = self.theme["name"] if not mods else " + ".join(mods) + "!"
        draw_text(s, sub, W // 2, y0 + 26, "orange" if mods else "lavender", align="center")
        if self.stage_n == 1:
            draw_text(s, "Z: SHOOT (HOLD)   X: COMET BURST", W // 2, y0 + 48, "mint", align="center", outline="ink")
        if new >= 0:
            name, _, _, _, _, desc = KINDS[new]
            art.enemy(s, new, 76, y0 + 47, self.t, hp=3)
            draw_text(s, f"NEW: {name}", 90, y0 + 38, "lime", shadow=None)
            draw_text(s, desc, 90, y0 + 48, "white", shadow=None)

    def draw_warning(self, s):
        t = self.t
        for by in (50, 116):
            s.fill(col("yellow"), (0, by, W, 8))
            off = int(t * 40) % 12
            for i in range(-1, 29):
                x = i * 12 + off
                pygame.draw.polygon(s, col("black"), [(x, by), (x + 5, by), (x + 1, by + 7), (x - 4, by + 7)])
        if int(t * 4) % 2 == 0:
            draw_text(s, "WARNING", W // 2, 66, "red", 3, align="center", outline="ink")
        else:
            draw_text(s, "WARNING", W // 2, 66, "white", 3, align="center", outline="red")
        b = self.boss
        if b is not None:
            draw_text(s, f"{b.name} APPROACHING", W // 2, 92, "white", align="center", outline="ink")
            sub = "THE FINAL GUARDIAN!" if b.final else D.BOSSES[b.kind]["intro"]
            draw_text(s, sub, W // 2, 103, "peach", align="center", outline="ink")

    def draw_tally(self, s):
        tl = self.tally
        n = len(tl["lines"])
        h = 34 + n * 11 + 14
        y0 = 92 - h // 2
        panel(s, (50, y0, 220, h), fill="ink", border="yellow")
        draw_text(s, tl["title"], W // 2, y0 + 6, rainbow(0, self.t) if self.mode == "boss" else "yellow", align="center")
        for i in range(tl["shown"]):
            label, v = tl["lines"][i]
            age = tl["t"] - (0.35 + i * 0.4)
            shown = int(v * min(1.0, age / 0.3))
            y = y0 + 20 + i * 11
            perfect = label.startswith("PERFECT")
            draw_text(s, label, 60, y, rainbow(i, self.t) if perfect else "white", shadow=None)
            draw_text(s, str(shown) if v > 0 else "-", 260, y, "lime" if v > 0 else "gray", align="right", shadow=None)
        if tl["shown"] >= n:
            y = y0 + 22 + n * 11
            s.fill(col("lavender"), (60, y - 2, 200, 1))
            draw_text(s, "TOTAL", 60, y + 2, "yellow", shadow=None)
            draw_text(s, str(tl["total"] * self.hype.mult), 260, y + 2, "yellow", align="right", shadow=None)


def preview(s, t):
    w, h = s.get_size()
    s.fill(col("night"))
    st = Stars(25, seed=2)
    st.update(t, 15)
    st.draw(s, t)
    kinds = (JELLY, MOTH, DART, SPORE, BLOB, COMET)
    for i in range(6):
        art.enemy(s, kinds[i], 10 + i * (w - 20) // 5, 10 + (i % 2) * 10 + int(math.sin(t * 2 + i) * 2), t)
    art.enemy(s, PUFF, w // 2 + int(math.sin(t) * 20), 34 + int(math.sin(t * 2) * 5), t)
    kx = w // 2 + int(math.sin(t * 1.5) * 24)
    s.blit(sprite("kitty"), (kx - 8, h - 18))
    for i in range(3):
        y = h - 24 - (int(t * 90) + i * 14) % 42
        s.fill(col("yellow"), (kx - 1, y, 3, 5))
