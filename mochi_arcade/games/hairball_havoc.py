"""HAIRBALL HAVOC - a single-screen arena shooter starring Biscuit, a cream cat with a ginger eye patch (original game).

Robo-toys have come to life! Biscuit defends the house room by room (20 rooms x 10 stages = 200 stages, tables in
hairball_havoc_data.py): waves of clockwork mice, zoom cars, sock puppets, vac-bots ... walk in through the doors.
Biscuit runs 8 ways and spits hairballs the way she faces; holding FIRE locks the facing so she can strafe.
Trapped kittens and hamsters raise the PURR multiplier, power-ups (yarn spread, laser pointer, catnip FEVER,
cardboard box shield, hairball bombs) drop from toys, every x5 stage is a bonus room and every 10th a boss.
The iOS port (ios/MochiArcade/Games/HairballHavoc*.swift) mirrors this file.
"""
import math
import random

import pygame

from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, ease_out, rainbow, tier
from mochi_arcade.games import DIFF
from mochi_arcade.games import hairball_havoc_art as art
from mochi_arcade.games import hairball_havoc_data as D
from mochi_arcade.games import hairball_havoc_sprites as S
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.games.hairball_havoc_data import (BALL, BLOCKLET, CAR, DRUM, GOLD, GOLEM, HELI, KINDS, MINIBALL,
                                                    MOUSE, PLANE, POPBOX, SOCK, TOP, VAC)
from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

EXPORT = D.EXPORT

HOWTO = [
    "ARROWS      RUN (8 WAYS)",
    "Z / SPACE   SPIT HAIRBALLS (HOLD = AIM LOCK)",
    "X / CTRL    HAIRBALL BOMB",
    "",
    "HOLD FIRE TO KEEP FACING ONE WAY AND",
    "STRAFE. SAVE KITTENS AND HAMSTERS FOR",
    "A BIGGER PURR MULTIPLIER - GRAB YARN,",
    "LASERS, CATNIP AND BOXES FROM THE TOYS.",
    "BONUS ROOM EVERY 5TH, BOSS EVERY 10TH!",
    "ENTER / ESC  PAUSE",
]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1),
           ("aim", "AIMING", [("lock", "HOLD TO LOCK"), ("auto", "AUTO AIM")], "lock")]
SMOKE_KEYS = ["left", "right", "up", "down", "a", "b"]

PSPEED = 82.0
HB = 3.0                    # Biscuit's hitbox (half size) against bullets and toys
BODY = 4.0                  # her half size against walls and furniture
SHOT_V = 220.0
EXTRA_LIVES = (20000, 60000, 120000, 200000)
EXTRA_EVERY = 150000
DIRS8 = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
KIT_ORDER = ("rapid", "big", "box", "zoom", "spread", "bomb", "tail", "purr", "pal", "bounce", "magnet", "nip")
DROPS = (("F", 7), ("Y", 5), ("X", 3), ("L", 3), ("H", 2), ("N", 2))
TOY_SPRITE = {MOUSE: "hh_mouse", CAR: "hh_car", SOCK: "hh_sock", VAC: "hh_vac", DRUM: "hh_drum", BALL: "hh_ball",
              PLANE: "hh_plane", POPBOX: "hh_popbox", GOLEM: "hh_golem", HELI: "hh_heli", TOP: "hh_top",
              MINIBALL: "hh_miniball", BLOCKLET: "hh_blocklet", GOLD: "hh_mouse"}
TOY_COLORS = {MOUSE: ("gray", "white", "pink"), CAR: ("red", "yellow", "sky"), SOCK: ("white", "red", "sky"),
              VAC: ("darkgray", "gray", "red"), DRUM: ("brown", "red", "yellow"), BALL: ("hotpink", "yellow", "sky"),
              PLANE: ("white", "lavender"), POPBOX: ("purple", "yellow", "lavender"), GOLEM: ("red", "sky", "lime"),
              HELI: ("blue", "sky", "gray"), TOP: ("orange", "yellow"), MINIBALL: ("hotpink", "yellow"),
              BLOCKLET: ("yellow", "sky"), GOLD: ("yellow", "orange", "white")}
CHASERS = (MOUSE, BLOCKLET, GOLEM, SOCK, DRUM, VAC)
BOSS_BULLET = (2, 3, 4, 0, 5, 7)
FEVER_TINT = ("P", "o", "y", "l", "m", "s", "v")
QUIPS_WIN = ("PURRFECT!", "NOT A SCRATCH!", "TOO EASY.", "I NEED A NAP...")

POOL = [
    Upgrade("rapid", "QUICK SPIT", "SPIT HAIRBALLS|FASTER", "orange", "hh_ic_rapid", 5),
    Upgrade("big", "BIG FLUFF", "BIGGER HAIR-|BALLS THAT|HIT HARDER", "peach", "hh_ic_big", 3),
    Upgrade("spread", "YARN TWIST", "+2 SIDE SHOTS|THAT FAN OUT", "pink", "hh_yarn", 2),
    Upgrade("tail", "TAIL SHOT", "ALSO SPIT|BEHIND YOU|LV2: SIDEWAYS", "yellow", "hh_ic_tail", 2),
    Upgrade("box", "BOX FORT", "+1 BOX SHIELD|EVERY STAGE", "peach", "hh_box", 3),
    Upgrade("zoom", "ZOOMIES", "RUN|FASTER", "sky", "hh_ic_zoom", 3),
    Upgrade("bomb", "BIG BELLY", "+1 HAIRBALL|BOMB, BIGGER|BLASTS", "red", "hh_bomb", 3),
    Upgrade("purr", "PURR POWER", "PURR STARTS|HIGHER,|+2 MAX PURR", "hotpink", "heart", 2),
    Upgrade("pal", "KITTEN PAL", "A KITTEN|FIGHTS AT|YOUR SIDE", "lime", "hh_kitten", 2),
    Upgrade("bounce", "RICOCHET", "HAIRBALLS|BOUNCE OFF|WALLS", "lavender", "hh_ic_bounce", 2),
    Upgrade("magnet", "WHISKER SENSE", "PULLS IN|TREATS, PETS|AND POWER-UPS", "mint", "hh_fish", 2),
    Upgrade("nip", "CATNIP NOSE", "POWER-UPS|AND FEVER|LAST LONGER", "lime", "hh_catnip", 3),
]


def dir8(dx, dy):
    return int(round(math.atan2(dy, dx) / (math.pi / 4))) % 8


def norm(dx, dy):
    d = math.hypot(dx, dy)
    return (dx / d, dy / d) if d > 1e-6 else (1.0, 0.0)


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    u = 0.0 if l2 < 1e-6 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + dx * u), py - (ay + dy * u))


class Toy:
    def __init__(self, uid, kind, x, y, elite=False, hpx=1.0):
        self.uid, self.kind = uid, kind
        self.x, self.y = float(x), float(y)
        hp = KINDS[kind][1] * (2 if elite else 1) * hpx
        self.hp = self.maxhp = float(hp)
        self.w, self.h = KINDS[kind][5], KINDS[kind][6]
        self.elite = elite
        self.vx = self.vy = 0.0
        self.t = 0.0
        self.flash = 0.0
        self.alive = True
        self.state = 0
        self.timer = random.uniform(0.6, 2.0)
        self.aux = 0.0
        self.side = 1
        self.stuck = 0.0
        self.face = 1
        self.ext = 0.0
        self.ax = self.ay = 0.0
        self.spawn_t = 0.4
        self.parade = False
        self.gold = False
        self.minion = False
        self.jit_t = 0.0        # chasers wobble off the straight line a little
        self.jit = 0.0
        self.seed = random.uniform(0, 6.28)


class Shot:
    def __init__(self, x, y, vx, vy, dmg, r, pierce, bounce, kind):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.dmg, self.r, self.pierce, self.bounce, self.kind = dmg, r, pierce, bounce, kind
        self.life = 2.0
        self.hits = []


class Bullet:
    def __init__(self, x, y, vx, vy, kind, fuse=0.0):
        self.x, self.y, self.vx, self.vy, self.kind, self.fuse = x, y, vx, vy, kind, fuse
        self.t = 0.0


class Item:
    def __init__(self, x, y, kind, vx=0.0, vy=0.0):
        self.x, self.y, self.kind, self.vx, self.vy = x, y, kind, vx, vy
        self.t = 0.0
        self.life = 9.0


class Pet:
    def __init__(self, kind, x, y, coat):
        self.kind, self.x, self.y, self.coat = kind, float(x), float(y), coat   # kind 0 kitten, 1 hamster, 2 gold
        self.vx = self.vy = 0.0
        self.t = random.uniform(0, 3)
        self.timer = random.uniform(0.5, 2.0)
        self.state = "idle"      # idle | saved | lost
        self.fade = 0.0


class Boss:
    def __init__(self, st):
        spec = D.BOSSES[st["boss"]]
        self.kind, self.lv, self.final, self.name = st["boss"], st["lv"], st["final"], st["name"]
        self.hp = self.maxhp = float(st["hp"])
        self.bw, self.bh = spec[2]
        self.minion = spec[1]
        self.phases, self.nphase = st["phases"], st["nphase"]
        if self.kind == 4:
            self.parts = [[0, 0, 8, self.maxhp * 0.08, 0.0, True] for _ in range(st["cars"])]
        else:
            self.parts = [[p[0], p[1], p[2], self.maxhp * p[3], 0.0, True] for p in spec[3]]
        self.x, self.y = W / 2, float(D.IY0 - 30)
        self.hy = 74.0
        self.t = 0.0
        self.state = "enter"
        self.phase = 0
        self.atk = None
        self.at = 0.0
        self.ai = self.an = 0
        self.rest = 1.2
        self.flash = 0.0
        self.face = 1
        self.moving = False
        self.tx, self.ty = W / 2, 80.0
        self.sx, self.sy = 0.0, 0.0
        self.wx, self.wy, self.wt = W / 2, 90.0, 0.0
        self.ang = 0.0
        self.dir = 1
        self.lanes = []
        self.spots = []
        self.ext = 0.0
        self.z = 0.0
        self.aux = 0.0
        self.heading = math.pi / 2
        self.trail = [(self.x, self.y - i * 2.0) for i in range(80)]
        self.head = (self.x, self.y - 20)


class HairballHavoc(GameScene):
    @property
    def music(self):
        return self.stage_music

    def __init__(self, app, info, opt):
        self.stage_music = "hh_house"
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES.get(d, 3)
        self.spd = SPEED.get(d, 1.0)
        self.auto = str(opt.get("aim", "lock")).lower() == "auto"
        self.stage_n = max(1, min(STAGES, int(opt.get("start", 1))))
        self.hype.combo_y = 13          # the combo counter sits on a plate in the top wall
        self.px, self.py = W / 2, 108.0
        self.vx = self.vy = 0.0
        self.fx, self.fy = 0.0, 1.0
        self.face8 = 2
        self.locked = False
        self.levels = {}
        self.toys, self.shots, self.bullets, self.items, self.pets, self.spawned = [], [], [], [], [], []
        self.boss = None
        self.inv = 1.5
        self.dead_t = None
        self.fire_t = 0.0
        self.shot_n = 0
        self.walk_t = 0.0
        self.happy_t = 0.0
        self.blink_t = 2.0
        self.yarn_t = self.laser_t = 0.0
        self.laser_tick = 0.0
        self.laser_end = None
        self.bomb_t = 0.0
        self.bomb_x = self.bomb_y = 0.0
        self.bomb_hit = set()
        self.pull_x = self.pull_y = 0.0
        self.trail = []
        self.pals = [[self.px, self.py, 0.3] for _ in range(2)]
        self.extra_i = 0
        self.next_extra = EXTRA_LIVES[0]
        self.uid = 0
        self.fever_was = False
        self.bg, self.bg_n = None, -1
        self.tally = None
        self.vic_t = 0.0
        self.dark = None
        kit = given = (self.stage_n - 1) // 10       # a checkpoint start hands out the power you'd roughly have
        i = 0
        while kit > 0 and i < 200:
            u = next(x for x in POOL if x.id == KIT_ORDER[i % len(KIT_ORDER)])
            if self.lv(u.id) < u.max:
                self.levels[u.id] = self.lv(u.id) + 1
                kit -= 1
            i += 1
        self.bombs = 2 + self.lv("bomb")
        self.shield = 0
        self.hype.FEVER_TIME = 8.0 + 1.5 * self.lv("nip")
        self.start_stage()
        if given:
            self.hype.banner("CHECKPOINT!", f"+{given} POWER LEVELS", color="lime", dur=2.0)

    # ---------------------------------------------------------------- helpers
    def lv(self, uid):
        return self.levels.get(uid, 0)

    def say(self, x, y, text, color):
        hw = text_width(text) // 2 + 2
        self.floats.add(max(hw, min(W - hw, x)), max(30, y), text, color)

    def purr_base(self):
        return 1 + self.lv("purr")

    def purr_max(self):
        return 8 + 2 * self.lv("purr")

    def blocked(self, x, y, hw, hh, fly=False):
        """A box centred at (x, y) leaves the floor or (walkers only) touches furniture."""
        if x - hw < D.IX0 or x + hw > D.IX1 or y - hh < D.IY0 or y + hh > D.IY1:
            return True
        if fly:
            return False
        for fx, fy, fw, fh in self.furn:
            if x + hw > fx and x - hw < fx + fw and y + hh > fy and y - hh < fy + fh:
                return True
        return False

    def solid_pt(self, x, y):
        if x < D.IX0 or x >= D.IX1 or y < D.IY0 or y >= D.IY1:
            return True
        for fx, fy, fw, fh in self.furn:
            if fx <= x < fx + fw and fy <= y < fy + fh:
                return True
        return False

    def move(self, o, dx, dy, hw, hh, fly=False):
        """Axis-separated move (slides along walls); returns which axes were blocked."""
        inside = self.blocked(o.x, o.y, hw, hh, fly)
        hx = hy = False
        if dx:
            if not inside and self.blocked(o.x + dx, o.y, hw, hh, fly):
                hx = True
            else:
                o.x += dx
        if dy:
            if not inside and self.blocked(o.x, o.y + dy, hw, hh, fly):
                hy = True
            else:
                o.y += dy
        if inside:      # spawned or pushed into something: nudge back onto the floor
            o.x = max(D.IX0 + hw, min(D.IX1 - hw, o.x))
            o.y = max(D.IY0 + hh, min(D.IY1 - hh, o.y))
        return hx, hy

    def target_of(self, x, y):
        """Nearest thing to shoot at (auto aim, kitten pals)."""
        best, bd = None, 1e9
        for e in self.toys:
            if e.alive and e.spawn_t <= 0:
                d = (e.x - x) ** 2 + (e.y - y) ** 2
                if d < bd:
                    best, bd = (e.x, e.y), d
        b = self.boss
        if b is not None and b.state == "fight":
            d = (b.x - x) ** 2 + (b.y - y) ** 2
            if d < bd:
                best, bd = (b.x, b.y), d
        return best, bd

    # ---------------------------------------------------------------- stages
    def start_stage(self):
        n = self.stage_n
        self.st = D.stage(n)
        st = self.st
        self.mode = st["type"]
        self.tier = tier(n)
        self.reached(n)
        if self.bg_n != n:
            self.bg, self.bg_n = art.build_room(st), n
        self.furn = [(D.IX0 + f[1] * 8, D.IY0 + f[2] * 8, f[3] * 8, f[4] * 8) for f in st["furn"]]
        self.doors = st["doors"]
        self.toys, self.bullets, self.items, self.spawned = [], [], [], []
        self.boss = None
        self.px, self.py = W / 2, 108.0
        self.vx = self.vy = 0.0
        self.stage_t = self.intro_t = self.clear_t = self.wave_t = 0.0
        self.deaths = self.saved = self.lost = self.hits = self.total = self.broken = 0
        self.spawn_i = 0
        self.purr = self.purr_base()
        self.max_said = False
        self.shield = max(self.shield, self.lv("box"))
        self.tally = None
        self.trail = []
        self.mods = st.get("mods", [])
        self.lights = "LIGHTS OUT" in self.mods
        self.slip = "SLIPPERY" in self.mods
        self.pets = [Pet(p[0], D.IX0 + p[1] * 8 + 4, D.IY0 + p[2] * 8 + 4, p[3]) for p in st.get("pets", [])]
        self.total_pets = len(self.pets)
        self.gold_t = random.uniform(10, 25) if self.mode == "normal" and self.hype.lucky(0.04) else -1.0
        self.lanes = []
        au = self.app.audio
        song = "hh_house" if self.tier < 10 else "hh_deep"
        if self.mode == "boss":
            self.phase = "warning"
            self.boss = Boss(st)
            self.stage_music = "boss"
            au.play("warning")
        else:
            self.phase = "intro"
            self.stage_music = "bonus" if self.mode == "bonus" else song
            au.play("stage")
            if self.mode == "bonus":
                self.inv = max(self.inv, 0.5)
                if st["mode"] == "parade":
                    self.yarn_t = st["dur"] + 3
                    self.lanes = [[ln[0], ln[1], ln[2], ln[3], ln[4], 0] for ln in st["lanes"]]
                    self.total = sum(ln[3] for ln in st["lanes"])
                else:
                    self.total = self.total_pets
        if not self.hype.fever_on or self.mode == "boss":
            au.music(self.stage_music)

    def next_stage(self):
        self.stage_n += 1
        self.start_stage()

    def check_clear(self):
        if self.phase != "play":
            return
        if self.mode == "boss":
            done = self.boss is None
        elif self.mode == "bonus":
            if self.st["mode"] == "parade":
                done = self.stage_t >= self.st["dur"] or (all(ln[5] >= ln[3] for ln in self.lanes) and not self.toys)
            else:
                done = self.stage_t >= self.st["dur"] or not any(p.state == "idle" for p in self.pets)
        else:
            done = self.spawn_i >= len(self.st["spawns"]) and not any(e.kind != GOLD for e in self.toys)
        if not done:
            return
        self.phase = "clear"
        self.clear_t = 0.0
        self.cancel_bullets()
        for e in self.toys:
            if e.alive:
                self.parts.burst(e.x, e.y, 8, TOY_COLORS[e.kind], 60, 0.5)
        self.toys = []
        self.happy_t = 3.0
        if self.mode != "boss":
            self.app.audio.play("levelup")
        if self.mode == "normal" and self.total_pets and self.saved == self.total_pets:
            self.hype.banner("ALL PETS SAFE!", color="pink", dur=1.4, sound="bonus")
            self.hype.shower(30, "hearts")

    def start_tally(self):
        t = self.tier
        lines = []
        if self.mode == "normal":
            lines.append(["CLEAR BONUS", 1000 + 250 * t])
            lines.append(["TIME BONUS", max(0, int(self.st["par"] - self.stage_t)) * 50])
            if self.total_pets:
                lines.append([f"PETS SAVED {self.saved}/{self.total_pets}", self.saved * (1000 + 200 * t)])
            lines.append(["NO MISS", (3000 + 750 * t) if self.deaths == 0 else 0])
            if self.total_pets and self.saved == self.total_pets and self.deaths == 0:
                lines.append(["PERFECT!!", 5000 + 1000 * t])
            title = f"STAGE {self.stage_n} CLEAR!"
        elif self.mode == "bonus":
            if self.st["mode"] == "parade":
                lines.append([f"TOYS POPPED {self.hits}/{self.total}", self.hits * (100 + 10 * t)])
            else:
                lines.append([f"PETS SAVED {self.saved}/{self.total}", self.saved * (300 + 30 * t)])
                self.hits = self.saved
            if self.hits >= self.total:
                lines.append(["PERFECT!!", 10000 + 2500 * t])
            title = "BONUS ROOM OVER"
        else:
            lines.append(["BOSS BONUS", 10000 + 5000 * t])
            lines.append(["TIME BONUS", max(0, int(self.st["par"] - self.stage_t)) * 100])
            lines.append(["NO MISS", (5000 + 1000 * t) if self.deaths == 0 else 0])
            if self.boss_parts:
                lines.append([f"PARTS BROKEN {self.broken}", self.broken * 2000])
            title = f"{self.st['name']} DOWN!"
        perfect = any(lb.startswith("PERFECT") for lb, _ in lines)
        quip = QUIPS_WIN[0] if perfect else (QUIPS_WIN[1] if self.deaths == 0 else
                                            (QUIPS_WIN[3] if self.deaths >= 2 else QUIPS_WIN[2]))
        self.tally = {"title": title, "lines": lines, "t": 0.0, "shown": 0, "total": sum(v for _, v in lines),
                      "quip": quip}
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
                self.hype.banner("HOUSE SAVED!!", "ALL 200 STAGES CLEAR", rainbow=True, dur=4.0, sound="win")
                self.hype.shower(120, "confetti")
                self.hype.shower(40, "hearts")
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
            if uid == "bomb":
                self.bombs += 1
            elif uid == "box":
                self.shield += 1
            elif uid == "nip":
                self.hype.FEVER_TIME = 8.0 + 1.5 * self.lv("nip")
        self.next_stage()

    @property
    def boss_parts(self):
        return self.st.get("boss") in (1, 3, 4)

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        au = self.app.audio
        self.stage_t += dt if self.phase == "play" else 0.0
        self.intro_t += dt
        self.inv = max(0.0, self.inv - dt)
        self.happy_t = max(0.0, self.happy_t - dt)
        self.yarn_t = max(0.0, self.yarn_t - dt)
        self.laser_t = max(0.0, self.laser_t - dt)
        self.update_player(dt)
        if self.ending is not None:
            return
        self.pull_x = self.pull_y = 0.0
        self.update_shots(dt)
        for e in self.toys:
            if e.alive:
                self.update_toy(e, dt)
        self.separate()
        if self.boss is not None:
            self.update_boss(dt)
        self.update_pets(dt)
        if self.phase == "play":
            self.spawn_logic(dt)
        self.update_bullets(dt)
        self.update_items(dt)
        self.collide()
        if self.bomb_t > 0:
            self.update_bomb(dt)
        self.toys = [e for e in self.toys if e.alive] + self.spawned
        self.spawned = []
        self.check_extra()
        if self.hype.fever_on != self.fever_was:
            self.fever_was = self.hype.fever_on
            if self.mode != "boss" and self.phase != "victory":
                au.music("fever" if self.fever_was else self.stage_music)
        if self.phase == "intro" and self.intro_t >= 2.4:
            self.phase = "play"
        elif self.phase == "warning" and self.boss is not None and self.boss.state == "fight":
            self.phase = "play"
        elif self.phase == "clear":
            self.clear_t += dt
            if self.clear_t >= 1.2:
                self.start_tally()
        elif self.phase == "tally":
            self.update_tally(dt)
        elif self.phase == "victory":
            self.vic_t += dt
            if int(self.vic_t * 4) != int((self.vic_t - dt) * 4):
                self.parts.burst(random.uniform(40, W - 40), random.uniform(40, 150), 30,
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
                self.say(self.px, self.py - 16, "1UP!", "mint")
                self.app.audio.play("extra")
            else:
                self.hype.banner("1UP!", "AN EXTRA LIFE", color="mint", dur=1.3, sound="extra")
            self.hype.shower(16, "hearts")

    def set_face(self, dx, dy):
        self.fx, self.fy = norm(dx, dy)
        self.face8 = dir8(dx, dy)

    def update_player(self, dt):
        inp = self.app.input
        if self.dead_t is not None:
            self.dead_t -= dt
            if self.dead_t <= 0:
                if self.lives <= 0:
                    self.end_game(False, f"STAGE {self.stage_n}")
                    return
                self.respawn()
            return
        dx = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        dy = (1 if inp.down("down") else 0) - (1 if inp.down("up") else 0)
        firing = inp.down("a") and self.phase not in ("tally", "between", "victory")
        if self.auto:
            self.locked = False
            if firing:
                tgt, _ = self.target_of(self.px, self.py)
                if tgt is not None:
                    self.set_face(tgt[0] - self.px, tgt[1] - self.py)
                elif dx or dy:
                    self.set_face(dx, dy)
            elif dx or dy:
                self.set_face(dx, dy)
        else:
            if (dx or dy) and (inp.hit("a") or not inp.down("a")):
                self.set_face(dx, dy)     # a fresh press takes the stick's direction, then holds it
            self.locked = inp.down("a")
        fever = self.hype.fever_on
        sp = PSPEED * (1 + 0.12 * self.lv("zoom")) * (1.3 if fever else 1.0)
        if dx and dy:
            sp *= 0.7071
        k = min(1.0, dt * (3.0 if self.slip else 22.0))
        self.vx += (dx * sp - self.vx) * k
        self.vy += (dy * sp - self.vy) * k
        mx, my = (self.vx + self.pull_x) * dt, (self.vy + self.pull_y) * dt
        hx, hy = self.move(self, mx, my, BODY, BODY)
        if hx and not dy:
            self.nudge(mx, 0.0)
        if hy and not dx:
            self.nudge(0.0, my)
        if hx and self.slip:
            self.vx = -self.vx * 0.3
        if hy and self.slip:
            self.vy = -self.vy * 0.3
        moving = abs(self.vx) + abs(self.vy) > 12
        self.walk_t = self.walk_t + dt * (1.6 if fever else 1.0) if moving else 0.0
        self.blink_t -= dt
        if self.blink_t < -0.12:
            self.blink_t = random.uniform(1.5, 4.0)
        if moving and (not self.trail or abs(self.trail[-1][0] - self.px) + abs(self.trail[-1][1] - self.py) > 2):
            self.trail.append((self.px, self.py))
            if len(self.trail) > 60:
                self.trail.pop(0)
        self.update_pals(dt)
        self.fire_t -= dt
        self.laser_end = None
        if firing:
            if self.laser_t > 0:
                self.fire_laser(dt)
            if self.fire_t <= 0:
                self.fire()
                self.fire_t = 0.16 * 0.87 ** self.lv("rapid") * (0.5 if fever else 1.0)
        if inp.hit("b"):
            self.bomb()

    def nudge(self, mx, my):
        """Corner assist: running straight into the corner of a piece of furniture slides around it."""
        for k in (1, 2, 3, 4, 5):
            for sd in (-1, 1):
                if mx and not self.blocked(self.px + mx, self.py + sd * k, BODY, BODY):
                    self.move(self, 0.0, sd * min(k, abs(mx) + 0.5), BODY, BODY)
                    return
                if my and not self.blocked(self.px + sd * k, self.py + my, BODY, BODY):
                    self.move(self, sd * min(k, abs(my) + 0.5), 0.0, BODY, BODY)
                    return

    # x / y as properties so self can be moved like any other body
    @property
    def x(self):
        return self.px

    @x.setter
    def x(self, v):
        self.px = v

    @property
    def y(self):
        return self.py

    @y.setter
    def y(self, v):
        self.py = v

    def respawn(self):
        self.dead_t = None
        self.inv = 2.5
        self.px, self.py = W / 2, 108.0
        self.vx = self.vy = 0.0
        self.bombs = max(self.bombs, 2)
        self.cancel_bullets()
        for e in self.toys:          # shoo the toys away from the middle
            dx, dy = e.x - self.px, e.y - self.py
            d = math.hypot(dx, dy)
            if d < 60:
                ux, uy = norm(dx, dy) if d > 1 else (1.0, 0.0)
                self.move(e, ux * (60 - d), uy * (60 - d), e.w * 0.4, e.h * 0.4, KINDS[e.kind][7])

    def update_pals(self, dt):
        n = self.lv("pal")
        for i in range(n):
            p = self.pals[i]
            idx = len(self.trail) - 1 - 10 * (i + 1)
            tx, ty = self.trail[max(0, idx)] if self.trail else (self.px - 12, self.py)
            p[0] += (tx - p[0]) * min(1.0, dt * 6)
            p[1] += (ty - p[1]) * min(1.0, dt * 6)
            p[2] -= dt
            if p[2] <= 0 and self.dead_t is None and self.phase in ("play", "warning", "intro"):
                tgt, d2 = self.target_of(p[0], p[1])
                if tgt is not None and d2 < 150 * 150:
                    ux, uy = norm(tgt[0] - p[0], tgt[1] - p[1])
                    self.shots.append(Shot(p[0], p[1], ux * 200, uy * 200, 0.6, 1, 0, 0, 3))
                    p[2] = 0.55
                else:
                    p[2] = 0.2

    def fire(self):
        x, y = self.px + self.fx * 5, self.py + self.fy * 5 - 1
        base = math.atan2(self.fy, self.fx)
        fever = self.hype.fever_on
        big = self.lv("big")
        dmg, r = 1.0 + 0.5 * big, 2 + big // 2
        kind = 2 if fever else 0
        pierce = 1 if fever else 0
        bounce = self.lv("bounce")
        angs = [0.0]
        if self.laser_t > 0:
            angs = []
        for i in range(self.lv("spread")):
            angs += [0.18 * (i + 1), -0.18 * (i + 1)]
        tail = self.lv("tail")
        if tail:
            angs.append(math.pi)
        if tail >= 2:
            angs += [math.pi / 2, -math.pi / 2]
        for a in angs:                       # side and tail shots are a little weaker than the main one
            self.shots.append(Shot(x, y, math.cos(base + a) * SHOT_V, math.sin(base + a) * SHOT_V,
                                   dmg if a == 0 else dmg * 0.7, r, pierce, bounce, kind))
        if self.yarn_t > 0:
            for a in (0.3, -0.3, 0.6, -0.6):
                self.shots.append(Shot(x, y, math.cos(base + a) * SHOT_V, math.sin(base + a) * SHOT_V, 0.8, 2,
                                       pierce, bounce, 1 if not fever else 2))
        self.shot_n += 1
        if self.shot_n % 2 and angs:
            self.app.audio.play("shoot")

    def fire_laser(self, dt):
        x, y = self.px + self.fx * 5, self.py + self.fy * 5 - 1
        ex, ey = x, y
        for _ in range(170):
            nx, ny = ex + self.fx * 2, ey + self.fy * 2
            if self.solid_pt(nx, ny):
                break
            ex, ey = nx, ny
        self.laser_end = (ex, ey)
        self.laser_tick -= dt
        if self.laser_tick > 0:
            return
        self.laser_tick = 0.07
        dmg = 0.6 + 0.2 * self.lv("big")
        for e in self.toys:
            if e.alive and e.spawn_t <= 0 and seg_dist(e.x, e.y, x, y, ex, ey) < max(e.w, e.h) / 2:
                self.damage(e, dmg, self.fx, self.fy)
        b = self.boss
        if b is not None and b.state == "fight" and b.z < 8:
            for i in range(len(b.parts)):
                p = b.parts[i]
                if p[5]:
                    qx, qy = self.part_pos(b, i)
                    if seg_dist(qx, qy, x, y, ex, ey) < p[2] + 2:
                        self.hurt_part(b, i, dmg)
                        return
            if seg_dist(b.x, b.y, x, y, ex, ey) < min(b.bw, b.bh) / 2:
                self.hurt_boss(dmg)

    def update_shots(self, dt):
        for sh in self.shots:
            sh.life -= dt
            nx, ny = sh.x + sh.vx * dt, sh.y + sh.vy * dt
            if self.solid_pt(nx, ny):
                if sh.bounce > 0:
                    sh.bounce -= 1
                    if self.solid_pt(nx, sh.y):
                        sh.vx = -sh.vx
                    if self.solid_pt(sh.x, ny):
                        sh.vy = -sh.vy
                    if not self.solid_pt(nx, sh.y) and not self.solid_pt(sh.x, ny):
                        sh.vx, sh.vy = -sh.vx, -sh.vy
                else:
                    sh.life = 0
                    self.parts.burst(sh.x, sh.y, 3, ("peach", "cream"), 30, 0.25)
                continue
            sh.x, sh.y = nx, ny
        self.shots = [sh for sh in self.shots if sh.life > 0]

    # ---------------------------------------------------------------- toys
    def spawn_logic(self, dt):
        st = self.st
        if self.mode == "bonus":
            if st["mode"] == "parade":
                for ln in self.lanes:
                    kind, di, delay, count, gold, done = ln
                    while done < count and self.stage_t >= delay + done * 0.32:
                        side, pos = self.doors[di]
                        x, y, ix, iy = D.door_spawn(side, pos)
                        e = self.spawn_toy(kind, x, y, False)
                        e.parade, e.gold = True, done == gold
                        e.spawn_t = 0.15
                        v = 62 + 2 * self.tier
                        e.vx, e.vy = ix * v, iy * v
                        e.aux = random.uniform(0, 6.28)
                        done += 1
                    ln[5] = done
            return
        if self.mode != "normal":
            return
        sp = st["spawns"]
        alive = sum(1 for e in self.toys if e.alive and e.kind != GOLD)
        if alive < st["max_on"]:
            self.wave_t += dt
        if self.spawn_i < len(sp) and alive == 0 and sp[self.spawn_i][2] - self.wave_t > 1.0:
            self.wave_t = sp[self.spawn_i][2] - 1.0        # nobody left: hurry the next wave in
        while self.spawn_i < len(sp) and sp[self.spawn_i][2] <= self.wave_t:
            kind, di, _, elite = sp[self.spawn_i]
            side, pos = self.doors[di]
            x, y, ix, iy = D.door_spawn(side, pos)
            if abs(x - self.px) < 30 and abs(y - self.py) < 30 and self.dead_t is None:
                # Biscuit is camping in the doorway: use another door
                di = (di + 1) % len(self.doors)
                side, pos = self.doors[di]
                x, y, ix, iy = D.door_spawn(side, pos)
            hw, hh = KINDS[kind][5] / 2, KINDS[kind][6] / 2
            self.spawn_toy(kind, x + ix * (hw - 4), y + iy * (hh - 4), bool(elite), ix, iy)
            self.spawn_i += 1
        if 0 < self.gold_t <= self.stage_t:
            self.gold_t = -1.0
            side, pos = self.doors[random.randrange(len(self.doors))]
            x, y, ix, iy = D.door_spawn(side, pos)
            self.spawn_toy(GOLD, x, y, False)
            self.hype.banner("GOLDEN MOUSE!", "CATCH IT!", color="yellow", dur=1.4, scale=1, sound="coin")

    def spawn_toy(self, kind, x, y, elite, ix=0, iy=1):
        self.uid += 1
        e = Toy(self.uid, kind, x, y, elite, self.st.get("hpx", 1.0))
        if kind == CAR:
            dx, dy = DIRS8[dir8(self.px - x, self.py - y)]
            e.vx, e.vy = norm(dx, dy)
        elif kind in (TOP, BALL, MINIBALL):         # diagonal into the room
            e.vx, e.vy = norm(ix if ix else random.choice((-1, 1)), iy if iy else random.choice((-1, 1)))
        elif kind == PLANE:
            e.aux = math.atan2(iy, ix)
        e.face = 1 if self.px >= x else -1
        self.spawned.append(e)
        if kind != GOLD:
            self.parts.burst(x, y, 6, ("white", "gray"), 30, 0.3)
        return e

    def toy_speed(self, e):
        return KINDS[e.kind][2] * self.st.get("spd", 1.0) * self.spd * (1.15 if e.elite else 1.0)

    def update_toy(self, e, dt):
        e.t += dt
        e.flash = max(0.0, e.flash - dt)
        if e.spawn_t > 0:
            e.spawn_t -= dt
            return
        k = e.kind
        if e.parade:
            e.x += e.vx * dt
            e.y += e.vy * dt
            wig = math.sin(e.t * 6 + e.aux) * 18
            e.x += -e.vy / 70 * wig * dt
            e.y += e.vx / 70 * wig * dt
            if e.x < D.IX0 - 8 or e.x > D.IX1 + 8 or e.y > D.IY1 + 8 or e.y < D.IY0 - 16:
                e.alive = False
            e.face = 1 if e.vx >= 0 else -1
            return
        sp = self.toy_speed(e)
        hw, hh = e.w * 0.4, e.h * 0.4
        fly = KINDS[k][7]
        cx, cy = self.px, self.py
        if self.dead_t is not None:          # Biscuit is down: the toys mill about
            cx, cy = W / 2 + math.sin(e.seed) * 80, 108 + math.cos(e.seed) * 50
        tx, ty = cx, cy
        if k in (MOUSE, BLOCKLET, GOLEM, SOCK, DRUM, VAC, GOLD):
            if k in (MOUSE, BLOCKLET) and self.laser_end is not None:
                lx, ly = self.laser_end
                if (lx - e.x) ** 2 + (ly - e.y) ** 2 < 90 * 90:
                    tx, ty = lx, ly                    # can't resist the red dot!
            if k == VAC:
                prey = [p for p in self.pets if p.state == "idle"]
                if prey:
                    p = min(prey, key=lambda q: (q.x - e.x) ** 2 + (q.y - e.y) ** 2)
                    tx, ty = p.x, p.y
                if self.tier >= 4 and self.dead_t is None:
                    dx, dy = e.x - self.px, e.y - self.py
                    d = math.hypot(dx, dy)
                    if 6 < d < 48:
                        pull = 24 + 2 * self.tier
                        self.pull_x += dx / d * pull
                        self.pull_y += dy / d * pull
                        e.state = 1
                    else:
                        e.state = 0
            mult = 1.0
            if k == MOUSE:                       # wind up, then dash
                e.timer -= dt
                if e.timer <= 0:
                    e.aux = 0.0 if e.aux else 1.0
                    e.timer = 0.45 if e.aux else random.uniform(1.6, 2.8)
                mult = 0.0 if e.aux else (1.5 if e.timer < 0.5 else 1.0)
            if k == SOCK:                        # hop, hop, spit
                hop = (e.t * 1.4) % 1.0
                mult = 2.4 if hop < 0.35 else 0.0
                e.timer -= dt
                if e.timer <= 0:
                    self.toy_shot(e, 0, 3 if self.tier >= 8 else 1)
                    e.timer = self.st.get("fire", 2.4) * random.uniform(0.8, 1.3) / self.spd
            if k == DRUM:
                e.timer -= dt
                mult = 0.0 if e.timer < 0.6 else 1.0
                if e.timer <= 0:
                    n = min(12, 6 + self.tier // 3)
                    off = random.uniform(0, 1)
                    for i in range(n):
                        self.bshot(e.x, e.y - 2, (i + off) * math.tau / n, self.st.get("bv", 90) * 0.6 * self.spd, 1)
                    e.timer = self.st.get("fire", 2.4) * 1.3 * random.uniform(0.9, 1.3) / self.spd
                    self.app.audio.play("paddle")
            if k == GOLD:                        # runs away, leaves after a while
                if e.t < 9:
                    tx, ty = 2 * e.x - self.px, 2 * e.y - self.py
                else:
                    side, pos = self.doors[0]
                    tx, ty, _, _ = D.door_spawn(side, pos)
                    if abs(tx - e.x) + abs(ty - e.y) < 10:
                        e.alive = False
                        self.say(e.x, e.y - 10, "IT GOT AWAY!", "gray")
                        return
                if int(e.t * 15) != int((e.t - dt) * 15):
                    self.parts.sparkle(e.x, e.y, rainbow(int(e.t * 15)))
            e.jit_t -= dt
            if e.jit_t <= 0:
                e.jit_t = random.uniform(0.5, 1.0)
                e.jit = random.uniform(-0.6, 0.6)
            ang = math.atan2(ty - e.y, tx - e.x) + e.jit
            if e.stuck > 0:
                e.stuck -= dt
                ang += e.side * math.pi / 2
            vx, vy = math.cos(ang) * sp * mult, math.sin(ang) * sp * mult
            hx, hy = self.move(e, vx * dt, vy * dt, hw, hh)
            if (hx or hy) and e.stuck <= 0:
                e.stuck = random.uniform(0.3, 0.7)
                e.side = random.choice((-1, 1))
            if abs(vx) > 1:
                e.face = 1 if vx > 0 else -1
        elif k in (CAR, BALL, MINIBALL, TOP):
            if k == TOP:
                sp *= 1 + min(1.0, e.t / 8)
                a = math.atan2(e.vy, e.vx) + random.uniform(-3, 3) * dt
                e.vx, e.vy = math.cos(a), math.sin(a)
            hx, hy = self.move(e, e.vx * sp * dt, e.vy * sp * dt, hw, hh)
            if hx:
                e.vx = -e.vx
            if hy:
                e.vy = -e.vy
            if (hx or hy) and k in (CAR, TOP) and random.random() < 0.45:
                e.vx, e.vy = norm(*DIRS8[dir8(cx - e.x, cy - e.y)])
                if self.blocked(e.x + e.vx * 3, e.y + e.vy * 3, hw, hh):
                    if hx:
                        e.vx = -e.vx
                    if hy:
                        e.vy = -e.vy
            if hx or hy:
                self.parts.burst(e.x, e.y, 2, ("white",), 30, 0.2)
            e.face = 1 if e.vx >= 0 else -1
        elif k == PLANE:
            want = math.atan2(cy - e.y, cx - e.x)
            diff = (want - e.aux + math.pi) % math.tau - math.pi
            e.aux += max(-1.7 * dt, min(1.7 * dt, diff))
            e.x += math.cos(e.aux) * sp * dt
            e.y += math.sin(e.aux) * sp * dt
            if e.x < D.IX0 + 4 or e.x > D.IX1 - 4:
                e.aux = math.pi - e.aux
                e.x = max(D.IX0 + 4.0, min(D.IX1 - 4.0, e.x))
            if e.y < D.IY0 + 4 or e.y > D.IY1 - 4:
                e.aux = -e.aux
                e.y = max(D.IY0 + 4.0, min(D.IY1 - 4.0, e.y))
            e.face = 1 if math.cos(e.aux) >= 0 else -1
        elif k == HELI:
            gx = cx + math.sin(e.t * 0.9 + e.seed) * 50
            gy = cy - 34 + math.cos(e.t * 1.3) * 10
            ux, uy = norm(gx - e.x, gy - e.y)
            e.x = max(D.IX0 + 6.0, min(D.IX1 - 6.0, e.x + ux * sp * dt))
            e.y = max(D.IY0 + 5.0, min(D.IY1 - 5.0, e.y + uy * sp * dt))
            e.face = 1 if ux >= 0 else -1
            e.timer -= dt
            if e.timer <= 0 and self.dead_t is None:
                e.timer = self.st.get("fire", 2.4) * random.uniform(0.9, 1.4) / self.spd
                self.bullets.append(Bullet(e.x, e.y + 4, 0.0, 12.0, 6, 1.3))
        elif k == POPBOX:
            self.update_popbox(e, dt, sp, hw, hh)

    def update_popbox(self, e, dt, sp, hw, hh):
        e.timer -= dt
        if e.state == 0:                         # waiting
            if e.timer <= 0:
                d = math.hypot(self.px - e.x, self.py - e.y)
                if d < 72 and self.dead_t is None:
                    e.state, e.timer = 2, 0.55
                    e.ax, e.ay = norm(self.px - e.x, self.py - e.y)
                    self.app.audio.play("move")
                else:
                    e.state, e.timer = 1, 0.5
                    a = math.atan2(self.py - e.y, self.px - e.x) + random.uniform(-0.8, 0.8)
                    e.vx, e.vy = math.cos(a), math.sin(a)
        elif e.state == 1:                       # hop
            self.move(e, e.vx * sp * 2.2 * dt, e.vy * sp * 2.2 * dt, hw, hh)
            if e.timer <= 0:
                e.state, e.timer = 0, random.uniform(0.5, 1.1)
        elif e.state == 2:                       # wind-up (telegraph)
            if e.timer <= 0:
                e.state, e.timer = 3, 0.6
                self.app.audio.play("jump")
        elif e.state == 3:                       # punch out and hold
            e.ext = min(44.0, e.ext + 260 * dt)
            if e.timer <= 0:
                e.state, e.timer = 4, 0.4
        else:                                    # pull the spring back in
            e.ext = max(0.0, e.ext - 140 * dt)
            if e.timer <= 0 and e.ext <= 0:
                e.state, e.timer = 0, random.uniform(0.8, 1.6)
        e.face = 1 if self.px >= e.x else -1

    def separate(self):
        walkers = [e for e in self.toys if e.alive and e.kind in CHASERS and e.spawn_t <= 0]
        for i in range(len(walkers)):
            a = walkers[i]
            for j in range(i + 1, len(walkers)):
                b = walkers[j]
                dx, dy = b.x - a.x, b.y - a.y
                if abs(dx) < 8 and abs(dy) < 8:
                    ux, uy = norm(dx, dy) if abs(dx) + abs(dy) > 0.01 else (1.0, 0.0)
                    self.move(a, -ux * 0.6, -uy * 0.6, a.w * 0.4, a.h * 0.4)
                    self.move(b, ux * 0.6, uy * 0.6, b.w * 0.4, b.h * 0.4)

    def toy_shot(self, e, kind, n):
        if self.dead_t is not None:
            return
        a0 = math.atan2(self.py - e.y, self.px - e.x)
        for i in range(n):
            self.bshot(e.x, e.y, a0 + (i - (n - 1) / 2) * 0.3, self.st.get("bv", 90) * self.spd, kind)
        self.app.audio.play("pop")

    def bshot(self, x, y, ang, sp, kind):
        if len(self.bullets) < 220:
            self.bullets.append(Bullet(x, y, math.cos(ang) * sp, math.sin(ang) * sp, kind))

    def update_bullets(self, dt):
        keep = []
        for b in self.bullets:
            b.t += dt
            b.x += b.vx * dt
            b.y += b.vy * dt
            if b.kind == 6:                       # toy bomb: fall, then burst
                b.vy *= max(0.0, 1 - dt * 2)
                b.fuse -= dt
                if b.fuse <= 0:
                    n = 6 if self.tier < 14 else 8
                    for i in range(n):
                        self.bshot(b.x, b.y, i * math.tau / n + 0.2, self.st.get("bv", 80) * 0.6 * self.spd, 7)
                    self.parts.burst(b.x, b.y, 10, ("red", "orange", "yellow"), 60, 0.4)
                    self.app.audio.play("pop")
                    continue
            elif b.kind == 3 and b.fuse > 0:       # suction dust: dies at the vacuum
                b.fuse -= dt
                if b.fuse <= 0:
                    continue
            if self.solid_pt(b.x, b.y) and not (b.kind == 3 and b.fuse > 0):
                self.parts.burst(b.x, b.y, 3, ("white", "gray"), 25, 0.2)
                continue
            keep.append(b)
        self.bullets = keep

    def cancel_bullets(self, near=None):
        keep = []
        bits = sum(1 for it in self.items if it.kind == "c")
        for b in self.bullets:
            if near is not None and (b.x - self.px) ** 2 + (b.y - self.py) ** 2 > near * near:
                keep.append(b)
                continue
            if bits < 120:
                self.items.append(Item(b.x, b.y, "c", random.uniform(-30, 30), random.uniform(-40, -10)))
                bits += 1
        self.bullets = keep

    # ---------------------------------------------------------------- pets and pick-ups
    def update_pets(self, dt):
        roundup = self.mode == "bonus" and self.st.get("mode") == "roundup"
        keep = []
        mag = 40 * self.lv("magnet")
        for p in self.pets:
            p.t += dt
            if p.state != "idle":
                p.fade += dt
                if p.fade < 0.6:
                    keep.append(p)
                continue
            p.timer -= dt
            fast = p.kind == 2
            run = 0.0
            # flee from nearby toys (and in the roundup, from Biscuit - catch them!)
            threat = None
            for e in self.toys:
                if e.alive and not e.parade and abs(e.x - p.x) < 32 and abs(e.y - p.y) < 32:
                    threat = e
                    break
            if roundup and abs(self.px - p.x) < 34 and abs(self.py - p.y) < 34:
                threat = self
            if mag and not roundup and math.hypot(self.px - p.x, self.py - p.y) < mag + 20:
                ux, uy = norm(self.px - p.x, self.py - p.y)
                p.vx, p.vy = ux * 40, uy * 40
            elif threat is not None:
                ux, uy = norm(p.x - threat.x, p.y - threat.y)
                run = (58 if fast else 46) if roundup else 40
                p.vx, p.vy = ux * run, uy * run
            elif p.timer <= 0:
                p.timer = random.uniform(0.8, 2.0)
                if random.random() < 0.35:
                    p.vx = p.vy = 0.0
                else:
                    a = random.uniform(0, math.tau)
                    v = (30 if roundup else 14) * (1.6 if fast else 1.0)
                    p.vx, p.vy = math.cos(a) * v, math.sin(a) * v
            hx, hy = self.move(p, p.vx * dt, p.vy * dt, 3, 3)
            if hx:
                p.vx = -p.vx
            if hy:
                p.vy = -p.vy
            # caught by a vac-bot?
            for e in self.toys:
                if e.alive and e.kind == VAC and e.spawn_t <= 0 and abs(e.x - p.x) < 8 and abs(e.y - p.y) < 8:
                    p.state, p.fade = "lost", 0.0
                    self.lost += 1
                    self.say(p.x, p.y - 10, "OH NO!", "gray")
                    self.app.audio.play("trap")
                    break
            if p.state == "idle" and self.dead_t is None and abs(self.px - p.x) < 9 and abs(self.py - p.y) < 9:
                self.rescue(p)
            keep.append(p)
        self.pets = keep

    def rescue(self, p):
        p.state, p.fade = "saved", 0.0
        self.saved += 1
        self.happy_t = 0.8
        au = self.app.audio
        self.parts.burst(p.x, p.y, 12, ("pink", "white", "hotpink"), 50, 0.6)
        if self.mode == "bonus":
            if p.kind == 2:
                self.hype.jackpot(5000 + 500 * self.tier, "GOLDEN HAMSTER!")
            else:
                self.add((200 + 20 * self.tier) * min(self.purr, 8), p.x, p.y - 8, "pink")
                self.purr = min(self.purr_max(), self.purr + 1) if self.saved % 3 == 0 else self.purr
            au.play("fruit")
            self.hype.hit(fever=0.03)
            return
        before = self.purr
        self.purr = min(self.purr_max(), self.purr + 1)
        self.add(500 * self.purr, p.x, p.y - 8, "pink")
        self.say(p.x, p.y - 18, f"PURR X{self.purr}", "hotpink")
        self.hype.hit(fever=0.05)
        au.play("bonus")
        if self.purr == self.purr_max() and before < self.purr and not self.max_said:
            self.max_said = True
            self.hype.banner("MAX PURR!", f"X{self.purr} POINTS", color="hotpink", dur=1.3, sound="combo")
            self.hype.shower(24, "hearts")

    def drop(self, x, y):
        if self.hype.lucky(0.012):
            kind = "G"
        else:
            tot = sum(w for _, w in DROPS)
            r = random.uniform(0, tot)
            kind = DROPS[-1][0]
            for kd, w in DROPS:
                r -= w
                if r <= 0:
                    kind = kd
                    break
        self.items.append(Item(x, y, kind, random.uniform(-20, 20), random.uniform(-30, -10)))

    def update_items(self, dt):
        mag = (0, 50, 90)[self.lv("magnet")]
        alive = self.dead_t is None
        keep = []
        for it in self.items:
            it.t += dt
            if it.kind == "c":
                if it.t < 0.3 or not alive:
                    it.x += it.vx * dt
                    it.y += it.vy * dt
                    if it.t > 1.5:
                        continue
                else:
                    ux, uy = norm(self.px - it.x, self.py - it.y)
                    v = 160 + it.t * 200
                    it.x += ux * v * dt
                    it.y += uy * v * dt
                keep.append(it)
                continue
            it.life -= dt
            if it.life <= 0:
                continue
            d = math.hypot(self.px - it.x, self.py - it.y)
            if alive and d < mag:
                ux, uy = norm(self.px - it.x, self.py - it.y)
                it.x += ux * 150 * dt
                it.y += uy * 150 * dt
            else:
                k = min(1.0, dt * 5)
                it.vx -= it.vx * k
                it.vy -= it.vy * k
                if not self.solid_pt(it.x + it.vx * dt, it.y + it.vy * dt):
                    it.x += it.vx * dt
                    it.y += it.vy * dt
            keep.append(it)
        self.items = keep

    def collect(self, it):
        k, au = it.kind, self.app.audio
        x, y = it.x, it.y
        t = self.tier
        nip = 1 + 0.25 * self.lv("nip")
        if k == "c":
            self.score += 10 * self.hype.mult
            return
        if k == "F":
            self.add(300 + 50 * t, x, y - 8, "sky")
            au.play("eat")
            return
        au.play("powerup")
        if k == "Y":
            self.yarn_t = 12.0 * nip
            self.say(x, y - 12, "YARN SPREAD!", "pink")
        elif k == "L":
            self.laser_t = 8.0 * nip
            self.say(x, y - 12, "LASER POINTER!", "red")
        elif k == "N":
            self.say(x, y - 12, "CATNIP!", "lime")
            if not self.hype.fever_on:
                self.hype.start_fever()
            else:
                self.hype.fever_t += 4
        elif k == "X":
            if self.shield < 3 + self.lv("box"):
                self.shield += 1
                self.say(x, y - 12, "BOX SHIELD!", "peach")
            else:
                self.add(2000, x, y - 12, "peach")
        elif k == "H":
            if self.bombs < 3 + self.lv("bomb"):
                self.bombs += 1
                self.say(x, y - 12, "HAIRBALL BOMB +1", "orange")
            else:
                self.add(2000, x, y - 12, "orange")
        elif k == "G":
            self.hype.jackpot(10000 + 1000 * t, "GOLDEN TUNA!")

    # ---------------------------------------------------------------- collisions
    def collide(self):
        for sh in self.shots:
            for e in self.toys:
                if sh.life <= 0:
                    break
                if not e.alive or e.spawn_t > 0 or e.uid in sh.hits:
                    continue
                if abs(sh.x - e.x) <= e.w / 2 + sh.r and abs(sh.y - e.y) <= e.h / 2 + sh.r:
                    self.damage(e, sh.dmg, sh.vx / SHOT_V, sh.vy / SHOT_V)
                    if sh.pierce > 0:
                        sh.pierce -= 1
                        sh.hits.append(e.uid)
                    else:
                        sh.life = 0
            if sh.life > 0 and self.boss is not None:
                self.shot_boss(sh)
        self.shots = [sh for sh in self.shots if sh.life > 0]
        if self.dead_t is not None or self.phase in ("victory", "tally", "between"):
            return
        keep = []
        for it in self.items:
            if (it.x - self.px) ** 2 + (it.y - self.py) ** 2 < (7 if it.kind == "c" else 10) ** 2:
                self.collect(it)
            else:
                keep.append(it)
        self.items = keep
        if self.inv > 0 or self.phase == "clear":
            return
        for b in self.bullets:
            r = art.BULLET_R[b.kind]
            if r and abs(b.x - self.px) <= HB + r and abs(b.y - self.py) <= HB + r:
                self.bullets.remove(b)
                self.hurt()
                return
        for e in self.toys:
            if not e.alive or e.spawn_t > 0 or e.parade:
                continue
            if abs(e.x - self.px) <= e.w * 0.4 + HB and abs(e.y - self.py) <= e.h * 0.4 + HB:
                if e.kind == GOLD:
                    continue
                self.hurt()
                return
            if e.kind == POPBOX and e.ext > 6:
                hx, hy = e.x + e.ax * e.ext, e.y + e.ay * e.ext
                if abs(hx - self.px) <= 5 + HB and abs(hy - self.py) <= 5 + HB:
                    self.hurt()
                    return
        b = self.boss
        if b is not None and b.state == "fight":
            self.boss_hits_player(b)

    def damage(self, e, dmg, ux=0.0, uy=0.0):
        if not e.alive:
            return
        if e.parade:
            self.kill_toy(e)
            return
        e.hp -= dmg
        if e.hp > 0:
            if e.flash <= 0:
                self.app.audio.play("tin")
            e.flash = 0.1
            if e.kind not in (GOLEM, POPBOX):
                self.move(e, ux * 2, uy * 2, e.w * 0.4, e.h * 0.4, KINDS[e.kind][7])
            return
        self.kill_toy(e)

    def kill_toy(self, e):
        if not e.alive:
            return
        e.alive = False
        t = self.tier
        au = self.app.audio
        self.parts.burst(e.x, e.y, 14, TOY_COLORS[e.kind], 80, 0.6)
        au.play("explode" if e.kind in (GOLEM, VAC, DRUM) else "pop")
        if e.kind == GOLD:
            self.parts.burst(e.x, e.y, 40, ("yellow", "orange", "white"), 140, 1.0)
            self.hype.jackpot(15000 + 1500 * t, f"GOLDEN MOUSE +{(15000 + 1500 * t) * self.hype.mult}")
            self.hype.hit()
            return
        if e.parade:
            self.hits += 1
            if e.gold:
                self.add(3000 + 300 * t, e.x, e.y - 8, "yellow")
                self.hype.shower(16, "coins")
                au.play("coin")
            else:
                self.add(100 + 10 * t, e.x, e.y - 8, "yellow")
            self.hype.hit(fever=0.02)
            return
        base = int(KINDS[e.kind][3] * (1 + 0.1 * t)) // 10 * 10 * (2 if e.elite else 1)
        pts = base * self.purr + self.hype.combo_bonus(5)
        self.add(pts, e.x, e.y - 8, "hotpink" if self.purr > 1 else "yellow")
        self.hype.hit(fever=0.03)
        if e.kind in (GOLEM, VAC, DRUM):
            self.app.shake(2, 0.15)
        if e.kind == BALL:
            for sd in (-1, 1):
                m = self.spawn_toy(MINIBALL, e.x + sd * 3, e.y, False)
                m.spawn_t = 0.0
                qx, qy = -e.vy * sd, e.vx * sd            # the halves fly apart sideways
                if abs(qx) + abs(qy) < 0.1:
                    qx, qy = float(sd), 1.0
                m.vx, m.vy = norm(qx + e.vx * 0.5, qy + e.vy * 0.5)
        elif e.kind == GOLEM:
            for i in range(3):
                m = self.spawn_toy(BLOCKLET, e.x + (i - 1) * 5, e.y, False)
                m.spawn_t = 0.1
                m.seed = i
        if not e.minion and random.random() < 0.07 + 0.002 * t + (0.1 if e.elite else 0):
            self.drop(e.x, e.y)

    def hurt(self):
        if self.inv > 0 or self.dead_t is not None:
            return
        au = self.app.audio
        if self.shield > 0:
            self.shield -= 1
            self.inv = 1.2
            self.cancel_bullets(44)
            self.parts.burst(self.px, self.py, 20, ("peach", "brown", "yellow"), 90, 0.5)
            au.play("pop")
            self.say(self.px, self.py - 16, "BOX SAVED YOU!", "peach")
            self.app.shake(2, 0.2)
            return
        self.lives -= 1
        self.deaths += 1
        self.dead_t = 1.6
        self.yarn_t = self.laser_t = 0.0
        self.purr = self.purr_base()
        self.hype.break_combo()
        au.play("hurt")
        self.app.shake(4, 0.4)
        self.hype.flash("red", 0.2)
        self.parts.burst(self.px, self.py, 30, ("cream", "white", "orange", "peach"), 100, 1.0)

    def bomb(self):
        if self.bombs <= 0 or self.dead_t is not None or self.phase not in ("intro", "play", "warning"):
            return
        self.bombs -= 1
        self.bomb_t = 0.6
        self.bomb_x, self.bomb_y = self.px, self.py
        self.bomb_hit = set()
        self.inv = max(self.inv, 1.4)
        self.cancel_bullets()
        b = self.boss
        if b is not None and b.state == "fight":
            if b.atk in ("lane", "suck"):
                b.atk, b.rest = None, 1.0
                b.ext = 0.0
            self.hurt_boss(b.maxhp * (0.035 + 0.01 * self.lv("bomb")))
        self.hype.flash("white", 0.3)
        self.hype.hitstop(0.08)
        self.app.shake(5, 0.5)
        self.app.audio.play("boom")
        self.say(self.px, self.py - 20, "HAIRBALL BOMB!", "orange")

    def update_bomb(self, dt):
        self.bomb_t = max(0.0, self.bomb_t - dt)
        rad = (1 - self.bomb_t / 0.6) * (100 + 15 * self.lv("bomb"))
        for e in self.toys:
            if e.alive and e.uid not in self.bomb_hit and (e.x - self.bomb_x) ** 2 + (e.y - self.bomb_y) ** 2 < rad * rad:
                self.bomb_hit.add(e.uid)
                self.damage(e, 6 + 2 * self.lv("bomb"))

    # ---------------------------------------------------------------- boss
    def part_pos(self, b, i):
        p = b.parts[i]
        if b.kind == 4:
            idx = len(b.trail) - 1 - 11 * (i + 1)
            return b.trail[max(0, idx)]
        if b.kind == 3:
            return b.x + p[0] + math.sin(b.t * 3 + i) * 3, b.y + p[1] + math.cos(b.t * 2.4 + i * 1.3) * 2
        return b.x + p[0], b.y + p[1]

    def lane_origin(self, b):
        return (b.x, b.y - 14) if b.kind == 2 else self.muzzle(b)

    def muzzle(self, b):
        if b.kind == 1:
            return b.x, b.y + 9
        if b.kind == 2:
            return b.head
        if b.kind == 4:
            return b.x + b.face * 6, b.y - 12
        return b.x, b.y - 2

    def minions(self):
        return sum(1 for e in self.toys if e.alive and e.minion)

    def update_boss(self, dt):
        b = self.boss
        b.t += dt
        b.flash = max(0.0, b.flash - dt)
        for p in b.parts:
            p[4] = max(0.0, p[4] - dt)
        if b.kind == 4:
            if not b.trail or abs(b.trail[-1][0] - b.x) + abs(b.trail[-1][1] - b.y) >= 2:
                b.trail.append((b.x, b.y))
                if len(b.trail) > 90:
                    b.trail.pop(0)
        if b.kind == 2:                       # the king's head bobs on its spring (or punches along a lane)
            if b.atk == "lane" and b.ext > 0 and b.lanes:
                ax, ay = b.lanes[0]
                b.head = (b.x + ax * 120 * b.ext, b.y - 14 + ay * 120 * b.ext)
            else:
                b.head = (b.x + math.sin(b.t * 2) * 3, b.y - 22 + math.sin(b.t * 4) * 2)
        if b.state == "enter":
            u = min(1.0, b.t / 2.6)
            b.y = D.IY0 - 30 + (b.hy - D.IY0 + 30) * ease_out(u)
            b.moving = True
            if u >= 1:
                b.state, b.rest = "fight", 1.0
            return
        if b.state == "dying":
            b.at += dt
            if int(b.at * 10) != int((b.at - dt) * 10):
                self.parts.burst(b.x + random.uniform(-b.bw / 2, b.bw / 2), b.y + random.uniform(-b.bh / 2, b.bh / 2),
                                 14, ("white", "yellow", "orange", "pink"), 90, 0.6)
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
        if b.atk is None:
            b.rest -= dt
            if b.rest <= 0:
                self.begin_attack(b)
        else:
            b.at += dt
            if self.run_attack(b, dt):
                b.atk = None
                b.ext = 0.0
                b.z = 0.0
                b.rest = self.st["rest"] * (1 - 0.1 * b.phase)
        self.boss_move(b, dt)
        if b.phase < b.nphase - 1 and b.hp <= b.maxhp * (1 - (b.phase + 1) / b.nphase):
            b.phase += 1
            b.atk, b.rest, b.ext, b.z = None, 1.2, 0.0, 0.0
            self.cancel_bullets()
            self.hype.banner("ANGRY!!", f"PHASE {b.phase + 1}", color="red", dur=1.2, sound="warning")
            self.hype.flash("red", 0.25)
            self.hype.hitstop(0.12)
            self.app.shake(4, 0.4)

    def boss_move(self, b, dt):
        busy = b.atk in ("charge", "hop")
        old = b.x
        if b.kind == 4:                      # the train never stops: it steers around the room
            if not busy:
                b.wt -= dt
                if b.wt <= 0 or abs(b.wx - b.x) + abs(b.wy - b.y) < 20:
                    b.wt = random.uniform(2.0, 3.5)
                    b.wx, b.wy = random.uniform(60, 260), random.uniform(50, 160)
                want = math.atan2(b.wy - b.y, b.wx - b.x)
                diff = (want - b.heading + math.pi) % math.tau - math.pi
                b.heading += max(-2.2 * dt, min(2.2 * dt, diff))
                v = 52 + 8 * b.lv + (20 if not any(p[5] for p in b.parts) else 0) + 6 * b.phase
                b.x += math.cos(b.heading) * v * dt
                b.y += math.sin(b.heading) * v * dt
                b.x = max(D.IX0 + 14.0, min(D.IX1 - 14.0, b.x))
                b.y = max(D.IY0 + 12.0, min(D.IY1 - 12.0, b.y))
        elif not busy and b.atk != "suck":
            b.wt -= dt
            if b.wt <= 0:
                b.wt = random.uniform(2.0, 3.2)
                b.wx, b.wy = random.uniform(70, 250), random.uniform(56, 110 if b.kind != 3 else 96)
            dx, dy = b.wx - b.x, b.wy - b.y
            d = math.hypot(dx, dy)
            v = (26 + 6 * b.lv) * (0.4 if b.atk else 1.0)
            if d > 2:
                b.x += dx / d * min(d, v * dt)
                b.y += dy / d * min(d, v * dt)
        b.moving = abs(b.x - old) > 0.05 or busy
        if abs(b.x - old) > 0.05:
            b.face = 1 if b.x > old else -1

    def begin_attack(self, b):
        names = b.phases[b.phase]
        a = names[b.ai % len(names)]
        b.ai += 1
        if a == "summon" and self.minions() >= 6:
            a = "fan"
        if a == "turret" and not any(p[5] for p in b.parts):
            a = "fan"
        if a == "hop" and b.kind == 4:
            a = "charge"
        b.atk, b.at, b.an = a, 0.0, 0
        px = max(D.IX0 + 20.0, min(D.IX1 - 20.0, self.px))
        py = max(D.IY0 + 20.0, min(D.IY1 - 16.0, self.py))
        if a == "lane":
            mx, my = self.lane_origin(b)
            base = math.atan2(self.py - my, self.px - mx)
            b.lanes = [(math.cos(base), math.sin(base))]
            if b.kind != 2 and (b.lv >= 2 or b.phase >= 2):
                for off in (0.5, -0.5):
                    b.lanes.append((math.cos(base + off), math.sin(base + off)))
        elif a == "rain":
            n = min(12, 4 + 2 * b.lv + b.phase)
            b.spots = [(px, py)]
            for _ in range(n - 1):
                b.spots.append((random.uniform(D.IX0 + 16, D.IX1 - 16), random.uniform(D.IY0 + 16, D.IY1 - 12)))
        elif a in ("charge", "hop"):
            b.tx, b.ty = px, py
            b.sx, b.sy = b.x, b.y
        elif a == "spiral":
            b.dir = 1 if b.ai % 2 else -1
            b.ang = random.uniform(0, math.tau)

    def run_attack(self, b, dt):
        """Advance the current attack; True when it is over. Every attack starts with a readable telegraph."""
        a, at, lv, ph = b.atk, b.at, b.lv, b.phase
        bv = self.st["bv"] * self.spd
        mx, my = self.muzzle(b)
        kind = BOSS_BULLET[b.kind]
        au = self.app.audio
        if a == "fan":
            tele, per = 0.5, 0.45
            vol = min(3, 1 + (lv + ph) // 2)
            while at - tele >= b.an * per and b.an < vol:
                n = 5 + lv + ph
                n += 1 - n % 2
                base = math.atan2(self.py - my, self.px - mx)
                for i in range(n):
                    self.bshot(mx, my, base + (i - n // 2) * 0.2, bv, kind)
                b.an += 1
                au.play("shoot")
            return at >= tele + vol * per
        if a == "ring":
            tele, per = 0.6, 0.5
            vol = min(3, 1 + (lv + ph) // 2)
            while at - tele >= b.an * per and b.an < vol:
                n = min(28, 10 + 2 * lv + 2 * ph)
                off = (b.an % 2) * math.pi / n
                for i in range(n):
                    self.bshot(b.x, b.y, off + i * math.tau / n, bv * 0.8, kind)
                b.an += 1
                au.play("pop")
            return at >= tele + vol * per
        if a == "spiral":
            tele, dur, step = 0.4, 2.2, 0.075
            arms = min(4, 2 + lv // 2)
            while at - tele >= b.an * step and b.an * step < dur:
                for i in range(arms):
                    self.bshot(b.x, b.y, b.ang + i * math.tau / arms, bv * 0.75, kind)
                b.ang += b.dir * 0.3
                b.an += 1
            return at >= tele + dur
        if a == "charge":
            tele = 0.7
            if at < tele:
                return False
            if b.an == 0:
                dx, dy = b.tx - b.x, b.ty - b.y
                d = math.hypot(dx, dy)
                step = (230 + 20 * lv) * dt
                if d <= step or at > tele + 1.3:
                    b.an, b.aux = 1, at
                    if lv >= 1 or ph >= 1:
                        n = 8 + 2 * lv
                        for i in range(n):
                            self.bshot(b.x, b.y, i * math.tau / n, bv * 0.7, kind)
                    self.app.shake(4, 0.3)
                    au.play("boom")
                else:
                    b.x += dx / d * step
                    b.y += dy / d * step
                    if b.kind == 4:
                        b.heading = math.atan2(dy, dx)
                return False
            return at >= b.aux + 0.4
        if a == "hop":
            tele, air = 0.7, 0.6
            if at < tele:
                return False
            u = min(1.0, (at - tele) / air)
            b.x = b.sx + (b.tx - b.sx) * u
            b.y = b.sy + (b.ty - b.sy) * u
            b.z = math.sin(math.pi * u) * 40
            if u >= 1 and b.an == 0:
                b.an = 1
                b.z = 0.0
                n = 10 + 2 * lv
                for i in range(n):
                    self.bshot(b.x, b.y + 6, i * math.tau / n, bv * 0.7, kind)
                self.app.shake(5, 0.35)
                au.play("boom")
                self.parts.burst(b.x, b.y + 10, 20, ("white", "gray"), 70, 0.5)
            return at >= tele + air + 0.5
        if a == "summon":
            if at >= 0.6 and b.an == 0:
                b.an = 1
                for i in range(min(4, 2 + lv)):
                    e = self.spawn_toy(b.minion, b.x + (i - 1.5) * 12, b.y + 14, False)
                    e.minion = True
                au.play("bubble")
            return at >= 1.0
        if a == "suck":
            tele, dur = 0.8, 2.6
            if tele <= at < tele + dur and self.dead_t is None:
                dx, dy = b.x - self.px, b.y - self.py
                d = max(1.0, math.hypot(dx, dy))
                pull = 52 + 12 * lv
                self.pull_x += dx / d * pull
                self.pull_y += dy / d * pull
                while at - tele >= b.an * 0.16:
                    b.an += 1
                    side = random.randrange(3)
                    if side == 0:
                        sx, sy = random.uniform(D.IX0 + 4, D.IX1 - 4), D.IY1 - 4.0
                    else:
                        sx, sy = (D.IX0 + 4.0 if side == 1 else D.IX1 - 4.0), random.uniform(D.IY0 + 10, D.IY1 - 6)
                    ang = math.atan2(b.y - sy, b.x - sx)
                    v = bv * 0.75
                    bl = Bullet(sx, sy, math.cos(ang) * v, math.sin(ang) * v, 3, math.hypot(b.x - sx, b.y - sy) / v)
                    self.bullets.append(bl)
            return at >= tele + dur
        if a == "lane":
            tele = 0.7
            if at < tele:
                return False
            u = at - tele
            if u < 0.18:
                b.ext = u / 0.18
            elif u < 0.63:
                b.ext = 1.0
            else:
                b.ext = max(0.0, 1 - (u - 0.63) / 0.3)
            if b.an == 0:
                b.an = 1
                au.play("jump" if b.kind == 2 else "shoot")
            return u >= 0.93
        if a == "rain":
            tele = 0.9
            if at >= tele + 0.3 and b.an == 0:
                b.an = 1
                n = 6 if lv >= 1 else 4
                for sx, sy in b.spots:
                    for i in range(n):
                        self.bshot(sx, sy, i * math.tau / n + 0.4, bv * 0.6, kind)
                    self.parts.burst(sx, sy, 6, ("white", "yellow"), 50, 0.3)
                    if self.dead_t is None and self.inv <= 0 and math.hypot(self.px - sx, self.py - sy) < 10:
                        self.hurt()
                au.play("explode")
            return at >= tele + 0.8
        if a == "turret":
            dur = 2.2
            alive = [i for i in range(len(b.parts)) if b.parts[i][5]]
            while alive and b.an * 0.3 <= min(at, dur) - 0.2:
                i = alive[b.an % len(alive)]
                qx, qy = self.part_pos(b, i)
                base = math.atan2(self.py - qy, self.px - qx)
                for off in ((-0.12, 0.12) if lv >= 2 else (0.0,)):
                    self.bshot(qx, qy, base + off, bv, kind)
                b.parts[i][4] = 0.1
                b.an += 1
                au.play("shoot")
            return at >= dur or not alive
        return True

    def lane_len(self, b):
        return 120.0 if b.kind == 2 else 260.0

    def boss_hits_player(self, b):
        if b.z < 8:
            if abs(b.x - self.px) <= b.bw / 2 - 2 + HB and abs(b.y - self.py) <= b.bh / 2 - 2 + HB:
                self.hurt()
                return
        if b.atk == "lane" and b.ext >= 0.5:
            mx, my = self.lane_origin(b)
            L = self.lane_len(b) * b.ext
            for ax, ay in b.lanes:
                if seg_dist(self.px, self.py, mx, my, mx + ax * L, my + ay * L) < 4 + HB:
                    self.hurt()
                    return
        if b.kind == 2 and math.hypot(b.head[0] - self.px, b.head[1] - b.z - self.py) < 8 + HB:
            self.hurt()
            return
        for i in range(len(b.parts)):
            if b.parts[i][5] and b.kind in (3, 4):
                qx, qy = self.part_pos(b, i)
                if math.hypot(qx - self.px, qy - self.py) < b.parts[i][2] + HB:
                    self.hurt()
                    return

    def shot_boss(self, sh):
        b = self.boss
        if b.state != "fight" or b.z >= 8:
            return
        for i in range(len(b.parts)):
            p = b.parts[i]
            if p[5]:
                qx, qy = self.part_pos(b, i)
                if (sh.x - qx) ** 2 + (sh.y - qy) ** 2 <= (p[2] + sh.r) ** 2:
                    self.hurt_part(b, i, sh.dmg)
                    sh.life = 0
                    return
        if b.kind == 2 and b.atk == "lane" and b.ext > 0.3:
            hx, hy = b.head
            if (sh.x - hx) ** 2 + (sh.y - hy) ** 2 <= (9 + sh.r) ** 2:
                self.hurt_boss(sh.dmg * 2)
                self.parts.sparkle(hx, hy - 8, "yellow")
                sh.life = 0
                return
        if abs(sh.x - b.x) <= b.bw / 2 + sh.r and abs(sh.y - b.y) <= b.bh / 2 + sh.r:
            self.hurt_boss(sh.dmg)
            sh.life = 0

    def hurt_part(self, b, i, dmg):
        p = b.parts[i]
        p[3] -= dmg
        p[4] = 0.08
        if p[3] <= 0:
            p[5] = False
            self.broken += 1
            qx, qy = self.part_pos(b, i)
            self.parts.burst(qx, qy, 24, ("white", "yellow", "orange"), 100, 0.7)
            self.add(2000, qx, qy - 10, "orange")
            self.app.audio.play("explode")
            self.app.shake(3, 0.2)
            self.hurt_boss(b.maxhp * 0.06)

    def hurt_boss(self, dmg):
        b = self.boss
        if b is None or b.state != "fight":
            return
        b.hp -= dmg
        if b.flash <= 0:
            self.app.audio.play("tin")
        b.flash = 0.08
        if b.hp <= 0:
            b.hp = 0.0
            b.state, b.at, b.atk, b.ext, b.z = "dying", 0.0, None, 0.0, 0.0
            self.cancel_bullets()
            for e in self.toys:
                if e.alive:
                    e.alive = False
                    self.parts.burst(e.x, e.y, 10, TOY_COLORS[e.kind], 70, 0.5)
            self.add(5000 * (1 + self.tier // 5), b.x, b.y - 20, "yellow")
            self.app.audio.play("bossdown")
            self.hype.slowmo(0.3, 1.4)
            self.hype.hitstop(0.15)
            self.hype.flash("white", 0.3)
            self.hype.banner("KO!!", f"{b.name} IS UNWOUND", rainbow=True, dur=2.0)
            self.app.shake(5, 0.6)

    # ---------------------------------------------------------------- draw
    def render(self, s):
        t = self.t
        s.blit(self.bg, (0, 0))
        for it in self.items:
            art.item(s, it.kind, int(it.x), int(it.y), t + it.t, it.life)
        for p in self.pets:
            self.draw_pet(s, p)
        b = self.boss
        if b is not None and b.state == "fight":
            self.draw_tells(s, b)
        for e in sorted(self.toys, key=lambda q: q.y):
            self.draw_toy(s, e)
        if b is not None:
            self.draw_boss(s, b)
        if self.lights and self.phase in ("intro", "play"):
            self.draw_dark(s)
        self.draw_doors(s)
        for sh in self.shots:
            art.hairball(s, int(sh.x), int(sh.y), sh.r if sh.kind != 3 else 1, sh.kind if sh.kind != 3 else 0, t)
        self.draw_cat(s)
        if self.laser_end is not None:
            x0, y0 = int(self.px + self.fx * 5), int(self.py + self.fy * 5 - 1)
            ex, ey = int(self.laser_end[0]), int(self.laser_end[1])
            pygame.draw.line(s, col("red"), (x0, y0), (ex, ey), 3)
            pygame.draw.line(s, col("white" if int(t * 30) % 2 else "pink"), (x0, y0), (ex, ey), 1)
            pygame.draw.circle(s, col("red"), (ex, ey), 3)
            s.fill(col("white"), (ex - 1, ey - 1, 2, 2))
        for bl in self.bullets:
            art.bullet(s, bl.kind, int(bl.x), int(bl.y), t, bl.fuse)
        if b is not None and b.state == "fight" and b.atk == "lane" and b.ext > 0 and b.kind != 2:
            mx, my = self.muzzle(b)
            L = self.lane_len(b) * b.ext
            for ax, ay in b.lanes:
                ex, ey = int(mx + ax * L), int(my + ay * L)
                pygame.draw.line(s, col("hotpink" if b.kind != 3 else "lavender"), (int(mx), int(my)), (ex, ey), 7)
                pygame.draw.line(s, col("white"), (int(mx), int(my)), (ex, ey), 3)
        if self.bomb_t > 0:
            r = int((1 - self.bomb_t / 0.6) * (100 + 15 * self.lv("bomb")))
            pygame.draw.circle(s, col("orange"), (int(self.bomb_x), int(self.bomb_y)), r, 4)
            if r > 6:
                pygame.draw.circle(s, col("cream"), (int(self.bomb_x), int(self.bomb_y)), r - 5, 2)
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
        owned = [u for u in POOL if self.lv(u.id) > 0]
        if not owned:
            return
        x0 = W // 2 - len(owned) * 11 + 11
        for i, u in enumerate(owned):
            cx = x0 + i * 22
            pygame.draw.circle(s, col(u.color), (cx, y), 10)
            pygame.draw.circle(s, col("ink"), (cx, y), 8)
            sp = sprite(u.icon)
            s.blit(sp, (cx - sp.get_width() // 2, y - sp.get_height() // 2))
            for p in range(u.max):
                s.fill(col("yellow" if p < self.lv(u.id) else "darkgray"), (cx - u.max * 2 + p * 4, y + 12, 3, 3))

    def draw_doors(self, s):
        """Doors flash and show an arrow just before a toy walks in."""
        if self.mode != "normal" or self.phase != "play":
            return
        sp = self.st["spawns"]
        hot = set()
        i = self.spawn_i
        while i < len(sp) and sp[i][2] - self.wave_t < 0.9:
            hot.add(sp[i][1])
            i += 1
        blink = int(self.t * 10) % 2
        for di in hot:
            side, pos = self.doors[di]
            x, y, w, h = D.door_rect(side, pos)
            s.fill(col("red" if blink else "orange"), (x + (2 if side == 1 else 0), y + (2 if side == 0 else 0),
                                                      w - (2 if side else 0), h - (2 if side == 0 else 0)))
            sx, sy, ix, iy = D.door_spawn(side, pos)
            ax, ay = int(sx + ix * 8), int(sy + iy * 8)
            pygame.draw.polygon(s, col("yellow" if blink else "white"),
                                [(ax + ix * 4, ay + iy * 4), (ax - iy * 4, ay + ix * 4), (ax + iy * 4, ay - ix * 4)])

    def draw_pet(self, s, p):
        t = self.t
        x, y = int(p.x), int(p.y)
        name = "hh_kitten" if p.kind == 0 else "hh_hamster"
        remap = S.KITTEN_COATS[p.coat % 4] if p.kind == 0 else ({"o": "y", "w": "w"} if p.kind == 2 else None)
        if p.state == "saved":
            yy = y - int(p.fade * 40)
            s.blit(sprite(name, 0, remap=remap), (x - 4, yy - 4))
            s.blit(sprite("heart"), (x - 3, yy - 12))
            return
        if p.state == "lost":
            if int(p.fade * 20) % 2 == 0:
                s.blit(sprite(name, 0, remap=S.WHITE), (x - 4, y - 4 + int(p.fade * 6)))
            return
        moving = abs(p.vx) + abs(p.vy) > 1
        fr = int(t * 8) % 2 if moving else 0
        hop = -int(abs(math.sin(p.t * 9)) * 2) if moving else 0
        s.blit(sprite(name, fr, flip=p.vx < 0, remap=remap), (x - 4, y - 4 + hop))
        if p.kind == 2 and int(t * 8) % 2:
            s.fill(col("white"), (x + 3, y - 5 + hop, 1, 1))
        if self.mode == "normal" and int(t * 2 + p.t) % 3 == 0:     # "help!" bubble
            s.fill(col("white"), (x - 2, y - 13, 5, 6))
            draw_text(s, "!", x - 2, y - 13, "hotpink", shadow=None)

    def draw_toy(self, s, e):
        t = self.t
        x, y = int(e.x), int(e.y)
        if e.spawn_t > 0:
            r = int((0.4 - e.spawn_t) / 0.4 * 7) + 1
            pygame.draw.circle(s, col("white"), (x, y), r, 1)
            return
        name = TOY_SPRITE[e.kind]
        fr = int(t * 8 + e.seed) % 2
        if e.kind == SOCK:
            fr = 1 if e.timer < 0.45 else 0
        elif e.kind == DRUM:
            fr = 1 if e.timer < 0.6 and int(t * 16) % 2 else 0
        elif e.kind == POPBOX:
            fr = 1 if e.state == 2 and int(t * 20) % 2 else 0
        elif e.kind == MOUSE and e.aux:
            fr = int(t * 16) % 2
        remap = None
        if e.flash > 0:
            remap = S.WHITE
        elif e.kind == GOLD or e.gold:
            remap = S.GOLDEN
        elif e.elite:
            remap = S.ELITE
        elif e.kind == BLOCKLET:
            remap = S.BLOCK_COLOURS[int(e.seed * 7) % 4]
        sp = sprite(name, fr, flip=e.face < 0, remap=remap)
        hop = -int(abs(math.sin(e.t * 1.4 * math.pi)) * 3) if e.kind == SOCK else 0
        if e.kind == POPBOX and e.state == 1:
            hop = -int(math.sin(max(0.0, e.timer) / 0.5 * math.pi) * 5)
        s.fill(col("black"), (x - e.w // 2 + 1, y + e.h // 2 - 1, e.w - 2, 2))
        s.blit(sp, (x - sp.get_width() // 2, y - sp.get_height() // 2 + hop))
        if e.kind == POPBOX and e.ext > 0:
            hx, hy = e.x + e.ax * e.ext, e.y + e.ay * e.ext
            art.spring(s, x, y - 4, hx, hy, t)
            art.clown(s, int(hx), int(hy), 5, t)
        if e.kind == VAC and e.state == 1 and int(t * 12) % 2:
            for i in range(3):
                a = t * 3 + i * 2.1
                r = 30 - (t * 40 + i * 10) % 26
                s.fill(col("white"), (int(e.x + math.cos(a) * r), int(e.y + math.sin(a) * r), 1, 1))
        if e.kind == HELI and e.timer < 0.4:
            s.fill(col("red" if int(t * 16) % 2 else "yellow"), (x - 1, y + 4, 2, 2))

    def draw_boss(self, s, b):
        t = self.t
        parts = []
        for i, p in enumerate(b.parts):
            qx, qy = self.part_pos(b, i)
            parts.append((int(qx), int(qy), p[2], p[5], p[4] > 0))
        look = max(-2, min(2, int((self.px - b.x) / 30)))
        ox = int(math.sin(t * 50) * 2) if b.atk in ("charge", "hop") and b.at < 0.7 else 0
        art.boss(s, b, int(b.x) + ox, int(b.y), t, look, parts, b.flash > 0 and int(t * 30) % 2 == 0)
        if b.atk is not None and b.at < 0.5 and b.atk in ("fan", "ring", "spiral", "summon", "turret"):
            mx, my = self.muzzle(b) if b.atk == "fan" else (b.x, b.y)
            r = int(14 * (1 - b.at / 0.5)) + 2
            pygame.draw.circle(s, col("white" if int(t * 20) % 2 else "yellow"), (int(mx), int(my)), r, 1)

    def draw_tells(self, s, b):
        """Telegraphs under everything: lane lines, rain shadows, charge path, hop target, suction."""
        t = self.t
        blink = int(t * 12) % 2
        if b.atk == "lane" and b.at < 0.7:
            mx, my = self.lane_origin(b)
            L = self.lane_len(b)
            for ax, ay in b.lanes:
                for i in range(4, int(L), 7):
                    s.fill(col("red" if blink else "white"), (int(mx + ax * i), int(my + ay * i), 2, 2))
        elif b.atk == "rain" and b.at < 1.2:
            for sx, sy in b.spots:
                r = 3 + int(min(1.0, b.at / 0.9) * 7)
                pygame.draw.ellipse(s, col("black"), (int(sx) - r, int(sy) - r // 2, r * 2, r))
                if b.at < 0.9:
                    pygame.draw.circle(s, col("red" if blink else "yellow"), (int(sx), int(sy)), 10, 1)
                else:
                    fy = int(sy - (1.2 - b.at) / 0.3 * 60)
                    art.bullet(s, BOSS_BULLET[b.kind], int(sx), fy, t)
        elif b.atk == "charge" and b.at < 0.7:
            ux, uy = norm(b.tx - b.x, b.ty - b.y)
            d = int(math.hypot(b.tx - b.x, b.ty - b.y))
            for i in range(0, d, 8):
                s.fill(col("red" if blink else "orange"), (int(b.x + ux * i) - 1, int(b.y + uy * i) - 1, 3, 3))
            pygame.draw.circle(s, col("red"), (int(b.tx), int(b.ty)), 8, 1)
        elif b.atk == "hop" and b.an == 0:
            r = 6 + int(min(1.0, b.at / 0.7) * 12)
            pygame.draw.ellipse(s, col("black"), (int(b.tx) - r, int(b.ty) + 4 - r // 3, r * 2, r * 2 // 3))
            pygame.draw.circle(s, col("red" if blink else "yellow"), (int(b.tx), int(b.ty) + 4), r, 1)
        elif b.atk == "suck":
            for i in range(10):
                a = i * math.tau / 10 + t
                r = 80 - (t * 70 + i * 13) % 70
                s.fill(col("white" if b.at > 0.8 else "gray"), (int(b.x + math.cos(a) * r), int(b.y + math.sin(a) * r), 2, 1))

    def draw_dark(self, s):
        """LIGHTS OUT: only a pool of light around Biscuit (and the toys' glowing eyes)."""
        r1, r2 = 44, 58
        cx, cy = int(self.px), int(self.py)
        if self.dark is None:
            self.dark = pygame.Surface((W, H), pygame.SRCALPHA)
        ov = self.dark
        ov.fill((0, 0, 0, 0))
        far, mid = (8, 4, 20, 225), (8, 4, 20, 140)
        for y in range(D.IY0, D.IY1):
            dy = y - cy
            if abs(dy) >= r2:
                ov.fill(far, (D.IX0, y, D.IX1 - D.IX0, 1))
                continue
            h2 = int(math.sqrt(r2 * r2 - dy * dy))
            ov.fill(far, (D.IX0, y, max(0, cx - h2 - D.IX0), 1))
            ov.fill(far, (cx + h2, y, max(0, D.IX1 - cx - h2), 1))
            h1 = int(math.sqrt(r1 * r1 - dy * dy)) if abs(dy) < r1 else 0
            if h1:
                ov.fill(mid, (cx - h2, y, h2 - h1, 1))
                ov.fill(mid, (cx + h1, y, h2 - h1, 1))
            else:
                ov.fill(mid, (cx - h2, y, h2 * 2, 1))
        s.blit(ov, (0, 0))
        for e in self.toys:
            if e.alive and e.spawn_t <= 0:
                c = col("red" if int(self.t * 3 + e.seed) % 4 else "yellow")
                s.fill(c, (int(e.x) - 2, int(e.y) - 2, 1, 1))
                s.fill(c, (int(e.x) + 2, int(e.y) - 2, 1, 1))

    def cat_view(self):
        dx, dy = DIRS8[self.face8]
        if dx:
            return "hh_cat_side", dx < 0
        return ("hh_cat_back", False) if dy < 0 else ("hh_cat_front", False)

    def draw_cat(self, s):
        t = self.t
        x, y = int(self.px), int(self.py)
        n = self.lv("pal")
        for i in range(n):           # kitten pals
            p = self.pals[i]
            s.blit(sprite("hh_kitten", int(t * 8) % 2, remap=S.KITTEN_COATS[(i + 1) % 4]), (int(p[0]) - 4, int(p[1]) - 4))
        if self.dead_t is not None:
            spin = int(t * 12) % 2 == 0
            s.blit(sprite("hh_cat_front", 0, flip=spin), (x - 6, y - 7))
            for sd in (-1, 1):       # X eyes
                ex = x + sd * 3 - (1 if sd < 0 else 0)
                s.fill(col("cream"), (ex - 1, y - 3, 3, 2))
                s.fill(col("black"), (ex - 1, y - 3, 1, 1))
                s.fill(col("black"), (ex + 1, y - 3, 1, 1))
                s.fill(col("black"), (ex, y - 2, 1, 1))
            for i in range(3):
                a = t * 6 + i * math.tau / 3
                s.fill(col("yellow"), (int(x + math.cos(a) * 9), int(y - 10 + math.sin(a) * 3), 2, 2))
            return
        if self.inv > 0 and int(self.inv * 12) % 2 and self.phase in ("play", "intro", "warning"):
            return
        name, flip = self.cat_view()
        happy = self.happy_t > 0 or self.phase in ("clear", "tally", "victory")
        if happy and self.phase != "play":
            name, flip = "hh_cat_front", False
        fr = 1 + int(self.walk_t * 8) % 2 if self.walk_t > 0 else 0
        bob = -1 if fr == 1 else 0
        if happy and self.phase != "play":
            bob = -int(abs(math.sin(t * 6)) * 4)
        remap = None
        if self.hype.fever_on:
            remap = {"c": FEVER_TINT[int(t * 12) % 7]}
        s.blit(sprite(name, fr, flip=flip, remap=remap), (x - 6, y - 7 + bob))
        if name == "hh_cat_front":
            base = remap["c"] if remap else "c"
            body = col({"c": "cream", "P": "hotpink", "o": "orange", "y": "yellow", "l": "lime", "m": "mint",
                        "s": "sky", "v": "lavender"}[base])
            ey = y - 3 + bob
            if happy:                    # ^^ eyes
                for ex in (x - 3, x + 2):
                    s.fill(body, (ex - 1, ey, 3, 2))
                    s.fill(col("black"), (ex - 1, ey + 1, 1, 1))
                    s.fill(col("black"), (ex, ey, 1, 1))
                    s.fill(col("black"), (ex + 1, ey + 1, 1, 1))
            elif self.blink_t < 0:
                for ex in (x - 3, x + 2):
                    s.fill(body, (ex, ey, 1, 2))
                    s.fill(col("black"), (ex - 1, ey + 1, 3, 1))
        if self.shield > 0:              # if it fits, she sits: a cardboard box around her
            bx, by = x - 7, y + 1 + bob
            s.fill(col("black"), (bx, by, 14, 7))
            s.fill(col("peach"), (bx + 1, by + 1, 12, 5))
            s.fill(col("brown"), (bx + 1, by + 3, 12, 1))
            s.fill(col("yellow"), (x - 1, by + 1, 2, 5))
            pygame.draw.line(s, col("peach"), (bx, by), (bx - 3, by - 3))
            pygame.draw.line(s, col("peach"), (bx + 13, by), (bx + 16, by - 3))
            if self.shield > 1:
                draw_text(s, str(self.shield), bx + 16, by, "peach", shadow="black")
        if self.phase in ("play", "intro", "warning"):    # aim guide: where the hairballs go
            c = "yellow" if (self.locked or (self.auto and self.app.input.down("a"))) else "gray"
            for i, d in enumerate((10, 15, 20)):
                px, py = int(self.px + self.fx * d), int(self.py + self.fy * d)
                s.fill(col(c), (px - (1 if i == 2 else 0), py - (1 if i == 2 else 0), 2 if i == 2 else 1, 2 if i == 2 else 1))
        if self.happy_t > 0 and self.phase == "play" and int(t * 6) % 2:
            s.blit(sprite("heart"), (x + 5, y - 14))

    def draw_hud(self, s):
        if self.hype.combo >= 3:
            w = text_width(f"{self.hype.combo} COMBO") + 8
            panel(s, (W // 2 - w // 2, 11, w, 12), fill="black", border="peach", radius=3, shadow=False)
        draw_text(s, f"{self.score:07d}", 4, 2, "white")
        draw_text(s, f"@{max(0, self.lives)}", 50, 2, "pink")
        b = self.boss
        if b is not None and self.phase != "warning":
            boss_bar(s, b.name, b.hp, b.maxhp, self.t, y=0, x=74, w=172)
        else:
            draw_text(s, f"HI {max(self.best, self.score):07d}", W // 2, 2, "lavender", align="center")
        c = "red" if self.mode == "boss" else ("mint" if self.mode == "bonus" else "yellow")
        draw_text(s, f"STAGE {self.stage_n}", W - 4, 2, c, align="right")
        y = D.IY1 + 1
        for i in range(min(self.bombs, 6)):          # hairball bombs
            x = 6 + i * 8
            pygame.draw.circle(s, col("choco"), (x, y + 3), 3)
            pygame.draw.circle(s, col("peach"), (x, y + 3), 2)
        x0 = 8 + min(self.bombs, 6) * 8
        for i in range(min(self.shield, 4)):          # boxes
            s.fill(col("peach"), (x0 + i * 7, y + 1, 5, 5))
            s.fill(col("brown"), (x0 + i * 7, y + 3, 5, 1))
        x = 96
        if self.mode != "boss":
            pc = rainbow(0, self.t) if self.purr >= self.purr_max() else "hotpink"
            s.blit(sprite("heart"), (x, y))
            draw_text(s, f"PURR X{self.purr}", x + 9, y, pc, shadow=None)
        x = 168
        for name, left, full, c in (("hh_yarn", self.yarn_t, 12.0, "pink"), ("hh_laser", self.laser_t, 8.0, "red")):
            if left > 0 and not (left < 2 and int(self.t * 8) % 2):
                s.blit(sprite(name), (x, y - 1))
                s.fill(col("darkgray"), (x + 10, y + 3, 20, 2))
                s.fill(col(c), (x + 10, y + 3, int(20 * min(1.0, left / full)), 2))
                x += 34
        if not self.hype.fever_on:
            x = W - 44
            s.fill(col("darkgray"), (x, y + 2, 40, 3))
            s.fill(col(rainbow(0, self.t) if self.hype.fever > 0.8 else "lime"), (x, y + 2, int(40 * self.hype.fever), 3))
            draw_text(s, "NIP", x - 20, y, "gray", shadow=None)

    def stage_hint(self):
        return "HOLD Z = AIM LOCK + STRAFE"

    def draw_intro(self, s):
        a = self.intro_t
        drop = int((1 - ease_out(min(1.0, a / 0.25))) * -60) + int(ease_out(max(0.0, (a - 2.1) / 0.3)) * -90)
        st = self.st
        room = D.ROOMS[st["room"]]
        if self.mode == "bonus":
            y0 = 92 + drop
            panel(s, (40, y0, 240, 40), fill="ink", border="mint")
            if st["mode"] == "parade":
                draw_text(s, "TOY PARADE!", W // 2, y0 + 6, "mint", 2, align="center", outline="ink")
                draw_text(s, "POP THEM ALL - THEY CAN'T HURT YOU", W // 2, y0 + 26, "white", align="center")
            else:
                draw_text(s, "KITTEN ROUNDUP!", W // 2, y0 + 6, "pink", 2, align="center", outline="ink")
                draw_text(s, "CATCH EVERY RUNAWAY PET!", W // 2, y0 + 26, "white", align="center")
            return
        new = st.get("new", -1)
        mods = st.get("mods", [])
        tall = 46 + (16 if new >= 0 else 0) + 9 * len(mods) + (10 if self.stage_n == 1 else 0)
        y0 = 100 - tall // 2 + drop
        panel(s, (56, y0, 208, tall), fill="ink", border="yellow")
        draw_text(s, f"STAGE {self.stage_n}", W // 2, y0 + 5, "yellow", 2, align="center", outline="ink")
        sub = f"{room[0]} {(self.stage_n - 1) % 10 + 1}/10"
        draw_text(s, sub, W // 2, y0 + 23, "lavender", align="center")
        draw_text(s, f'"{room[10]}"', W // 2, y0 + 33, "cream", align="center", shadow=None)
        y = y0 + 44
        for m in mods:
            draw_text(s, f"{m}: {D.MOD_TEXT[m]}", W // 2, y, "orange", align="center", shadow=None)
            y += 9
        if new >= 0:
            sp = sprite(TOY_SPRITE[new], int(self.t * 6) % 2)
            s.blit(sp, (76 - sp.get_width() // 2, y + 6 - sp.get_height() // 2))
            draw_text(s, f"NEW: {KINDS[new][0]}", 90, y, "lime", shadow=None)
            draw_text(s, KINDS[new][8], 90, y + 8, "white", shadow=None)
            y += 16
        if self.stage_n == 1:
            draw_text(s, self.stage_hint(), W // 2, y, "mint", align="center", shadow=None)

    def draw_warning(self, s):
        t = self.t
        for by in (52, 118):
            s.fill(col("yellow"), (0, by, W, 8))
            off = int(t * 40) % 12
            for i in range(-1, 29):
                x = i * 12 + off
                pygame.draw.polygon(s, col("black"), [(x, by), (x + 5, by), (x + 1, by + 7), (x - 4, by + 7)])
        if int(t * 4) % 2 == 0:
            draw_text(s, "WARNING", W // 2, 68, "red", 3, align="center", outline="ink")
        else:
            draw_text(s, "WARNING", W // 2, 68, "white", 3, align="center", outline="red")
        b = self.boss
        if b is not None:
            draw_text(s, f"{b.name} IS COMING", W // 2, 94, "white", align="center", outline="ink")
            draw_text(s, D.BOSSES[b.kind][5], W // 2, 105, "peach", align="center", outline="ink")

    def draw_tally(self, s):
        tl = self.tally
        n = len(tl["lines"])
        h = 34 + n * 11 + 26
        y0 = 96 - h // 2
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
            bob = int(abs(math.sin(self.t * 5)) * 2)
            s.blit(sprite("hh_cat_front", 0), (62, y + 12 - bob))
            draw_text(s, f'BISCUIT: "{tl["quip"]}"', 80, y + 15, "cream", shadow=None)


# ---------------------------------------------------------------- GIF bot / test autopilot
def autopilot(scene, frame, mem):
    """One frame of a decent automatic player (GIF recorder, tests). mem keeps state between frames."""
    s = scene
    held = mem.get("held", False)
    if s.overlay is not None or s.phase in ("tally", "between"):
        mem["held"] = False
        return {"a"} if frame % 20 == 0 else set()
    if s.dead_t is not None:
        mem["held"] = False
        return set()
    px, py = s.px, s.py
    ax = ay = 0.0                          # danger pushes Biscuit away
    for bl in s.bullets:
        dx, dy = px - bl.x, py - bl.y
        d2 = dx * dx + dy * dy
        if d2 < 44 * 44 and (bl.vx * dx + bl.vy * dy) > 0 and art.BULLET_R[bl.kind]:
            ax += dx / (d2 + 1) * 50
            ay += dy / (d2 + 1) * 50
        elif bl.kind == 6 and d2 < 34 * 34:
            ax += dx / (d2 + 1) * 40
            ay += dy / (d2 + 1) * 40
    for e in s.toys:
        if e.alive and not e.parade:
            dx, dy = px - e.x, py - e.y
            d2 = dx * dx + dy * dy
            r = 44 if e.kind in (CAR, TOP, BALL, MINIBALL, POPBOX) else 36
            if d2 < r * r:
                ax += dx / (d2 + 1) * 70
                ay += dy / (d2 + 1) * 70
    b = s.boss
    if b is not None and b.state == "fight":
        dx, dy = px - b.x, py - b.y
        d = math.hypot(dx, dy) + 1
        if d < 70:
            ax += dx / d * 2
            ay += dy / d * 2
        if b.atk == "suck":
            ax += dx / d * 3
            ay += dy / d * 3
        if b.atk == "lane" and b.at < 1.6:
            mx, my = s.lane_origin(b)
            for lx, ly in b.lanes:
                cross = (px - mx) * ly - (py - my) * lx
                if abs(cross) < 16 and (px - mx) * lx + (py - my) * ly > 0:
                    sd = 1 if cross < 0 else -1
                    ax += -ly * sd * 3
                    ay += lx * sd * 3
        if b.atk in ("rain", "hop", "charge"):
            for sx, sy in (b.spots if b.atk == "rain" else [(b.tx, b.ty)]):
                dx, dy = px - sx, py - sy
                if dx * dx + dy * dy < 34 * 34:
                    ax += dx / (abs(dx) + abs(dy) + 1) * 3
                    ay += dy / (abs(dx) + abs(dy) + 1) * 3
    roundup = s.mode == "bonus" and s.st.get("mode") == "roundup"
    tgt, _ = s.target_of(px, py)
    goal = None
    pets = [p for p in s.pets if p.state == "idle"]
    if pets and (roundup or len([e for e in s.toys if e.alive]) < 3):
        p = min(pets, key=lambda q: (q.x - px) ** 2 + (q.y - py) ** 2)
        goal = (p.x, p.y)
    items = [it for it in s.items if it.kind != "c"]
    if items and goal is None:
        it = min(items, key=lambda q: (q.x - px) ** 2 + (q.y - py) ** 2)
        if (it.x - px) ** 2 + (it.y - py) ** 2 < 70 * 70:
            goal = (it.x, it.y)
    mvx = mvy = 0.0
    if abs(ax) + abs(ay) > 0.5:
        mvx, mvy = ax, ay
    elif goal is not None:
        mvx, mvy = goal[0] - px, goal[1] - py
    elif tgt is not None:
        dx, dy = tgt[0] - px, tgt[1] - py
        d = math.hypot(dx, dy)
        orbit = 1 if (frame // 150) % 2 else -1
        if d > 100:
            mvx, mvy = dx, dy
        elif d < 56:
            mvx, mvy = -dx, -dy
        else:
            mvx, mvy = -dy * orbit, dx * orbit
    else:
        mvx, mvy = W / 2 - px, 108 - py
    if px < 34:                              # keep off the walls
        mvx += 2
    if px > W - 34:
        mvx -= 2
    if py < 44:
        mvy += 2
    if py > 172:
        mvy -= 2
    mv = set()
    if abs(mvx) > 0.4 * (abs(mvy) + 0.01) and abs(mvx) > 0.05:
        mv.add("right" if mvx > 0 else "left")
    if abs(mvy) > 0.4 * (abs(mvx) + 0.01) and abs(mvy) > 0.05:
        mv.add("down" if mvy > 0 else "up")
    if roundup or tgt is None:
        mem["held"] = False
        return mv
    want = dir8(tgt[0] - px, tgt[1] - py)
    keys = set(mv)
    if s.auto or want == s.face8:
        keys.add("a")
    elif not held:                          # fresh press + stick direction = new facing, then it locks
        dx, dy = DIRS8[want]
        keys = {"a"}
        if dx:
            keys.add("right" if dx > 0 else "left")
        if dy:
            keys.add("down" if dy > 0 else "up")
    mem["held"] = "a" in keys
    near = sum(1 for e in s.toys if e.alive and not e.parade and (e.x - px) ** 2 + (e.y - py) ** 2 < 30 * 30)
    if s.bombs > 0 and (near >= 3 or (b is not None and b.state == "fight" and frame % 900 == 450)):
        keys.add("b")
    return keys


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys."""
    mem = {}
    return lambda frame: autopilot(scene, frame, mem)


# ---------------------------------------------------------------- carousel preview
def preview(s, t):
    w, h = s.get_size()
    s.fill(col("brown"))
    for y in range(0, h, 8):
        s.fill(col("choco"), (0, y, w, 1))
        for x in range(((y // 8) % 3) * 21, w, 64):
            s.fill(col("choco"), (x, y, 1, 8))
    s.fill(col("peach"), (0, 0, w, 9))
    for x in range(3, w, 8):
        s.fill(col("orange"), (x, 1, 2, 6))
    s.fill(col("brown"), (0, 7, w, 3))
    art.furniture(s, D.SOFA, 6, 16, 32, 20, 0)
    art.furniture(s, D.PLANT, w - 22, 14, 16, 16, 0)
    cx = w // 2 + int(math.sin(t * 1.3) * (w // 4))
    cy = h - 16
    s.blit(sprite("hh_cat_back", 1 + int(t * 8) % 2), (cx - 6, cy - 7))
    for i in range(3):
        yy = cy - 12 - (int(t * 120) + i * 16) % 46
        art.hairball(s, cx, yy, 2, 0, t)
    for i in range(3):
        mx = int((t * 30 + i * w / 3) % (w + 20)) - 10
        my = 30 + i * 8 + int(math.sin(t * 3 + i) * 3)
        if (mx - cx) ** 2 > 36 or i:
            s.blit(sprite("hh_mouse", int(t * 8 + i) % 2), (mx - 5, my - 4))
    s.blit(sprite("hh_kitten", int(t * 4) % 2), (w - 18, h - 14))
    if int(t * 2) % 2:
        s.blit(sprite("heart"), (w - 17, h - 22))
