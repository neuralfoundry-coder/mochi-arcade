"""ALLEY HOP - a lane-crossing game (original design for MOCHI ARCADE).

SUSHI, a calico cat, guides lost kittens home across a night town: busy alleys, canals with floating crates and
ducks, rooftops with swaying laundry, train crossings and closing gates. Picked-up kittens follow her in a little
line - hopping exactly where she hopped, a beat later - so a big family needs bigger gaps in the traffic. Bring
them all to the cozy cardboard boxes at the top.

200 stages (alley_hop_stages.py): a boss on every 10th stage (alley_hop_boss.py), a bonus stage on every x5,
upgrade cards after bosses / bonus stages. The iOS port (ios/MochiArcade/Games/AlleyHop*.swift) mirrors this file
and reads the stage table from EXPORT.
"""
import math
import random

import pygame

from mochi_arcade import music
from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow
from mochi_arcade.games import DIFF
from mochi_arcade.games import alley_hop_art as art
from mochi_arcade.games.alley_hop_boss import Boss
from mochi_arcade.games.alley_hop_stages import CAMPAIGN, CARRIERS, START_COL, THEMES, pmod
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

HOWTO = [
    "ARROWS      HOP (ONE HOP PER PRESS)",
    "Z / SPACE   HOP FORWARD",
    "X / CTRL    POUNCE OVER A LANE (UPGRADE)",
    "",
    "GUIDE THE LOST KITTENS HOME! THEY FOLLOW",
    "SUSHI IN A LINE - BIG FAMILIES SCORE MORE.",
    "A BOSS EVERY 10TH STAGE: HOP ON IT WHEN",
    "IT'S DIZZY. BONUS STAGES ON EVERY X5.",
    "",
    "ENTER / ESC  PAUSE",
]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["up", "up", "up", "left", "right", "down", "a", "b"]

TOP, CELL, ROWS, COLS = 12, 16, 11, 20
HOP, KHOP, KDELAY, POUNCE_T = 0.14, 0.13, 0.15, 0.27
LIFE_AT = [30000, 80000, 150000, 250000]     # then every 150000
DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
HURTS = ("hit", "train")

EXPORT = {"stages": CAMPAIGN, "themes": THEMES}

music.SONGS.update({
    # "Whisker Walk" - the streets (F major, a strolling swing)
    "ah_alley": {"bpm": 132, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "F5:8 A5:8 C6:4 A5:8 F5:8 G5:4  A5:8 G5:8 F5:8 D5:8 C5:4 R:4 "
            "D5:8 F5:8 A#5:4 A5:8 G5:8 F5:4  E5:8 G5:8 C6:4 A#5:8 A5:8 G5:4 "
            "F5:8 A5:8 C6:8 D6:8 C6:4 A5:4  A#5:8 A5:8 G5:8 F5:8 G5:4 A5:4 "
            "D6:8 C6:8 A#5:8 A5:8 G5:8 E5:8 C5:4  F5:8 R:8 C5:8 R:8 F5:4 R:4"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.7, "notes": music._bass(["F", "D", "A#", "C", "F", "A#", "C", "F"], "4")},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, "K:4 H:8 H:8 S:4 H:8 K:8")},
    ]},
    # "Lantern Lullaby" - canals and rooftops (D minor, gentle)
    "ah_canal": {"bpm": 116, "gain": 0.8, "channels": [
        {"wave": "square", "duty": 0.5, "vol": 0.2, "decay": 0.45, "notes":
            "D5:4 F5:8 A5:8 D6:4 C6:8 A5:8  A#5:4 A5:8 G5:8 F5:4 E5:4 "
            "F5:4 A5:8 C6:8 F6:4 E6:8 C6:8  D6:8 C6:8 A#5:8 A5:8 G5:2 "
            "G5:4 A#5:8 D6:8 G6:4 F6:8 D6:8  E6:8 D6:8 C6:8 A5:8 F5:4 A5:4 "
            "A#5:8 A5:8 G5:8 F5:8 E5:8 G5:8 A#5:8 C#6:8  D6:4 A5:4 D5:2"},
        {"wave": "triangle", "vol": 0.4, "gate": 0.8, "notes": music._bass(["D", "A#", "F", "C", "G", "C", "A", "D"], "4")},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, "K:4 H:4 S:4 H:4")},
    ]},
})


# ----------------------------------------------------------------------------- lane maths (pure functions of time)
def lane_shift(ln, lt):
    if ln["sw"]:
        return ln["sw"] * math.sin(ln["om"] * lt + ln["ph"])
    return ln["ph"] + ln["v"] * lt


def pad_of(ln):
    return (ln["p"] - W) // 2


def item_sx(ln, ix, sh):
    """Screen x of a pattern item's left edge."""
    return pmod(ix + sh, ln["p"]) - pad_of(ln)


def dive_state(ln, i, lt):
    """0 afloat, 1 about to dive (telegraph), 2 under water."""
    if not ln["dv"]:
        return 0
    cyc, down, stag = ln["dv"]
    c = pmod(lt + i * stag, cyc)
    if c < cyc - down - 0.9:
        return 0
    return 1 if c < cyc - down else 2


def train_span(ln, lt):
    """(warning, x0, x1): x0/x1 = the train's extent on screen (None when no train is passing)."""
    cyc, warn, length, speed, ph, d = ln["tr"]
    c = pmod(lt + ph, cyc)
    if c < warn:
        return True, None, None
    dist = (c - warn) * speed
    if dist > W + length + 80:
        return False, None, None
    if d > 0:
        front = -40 + dist
        return True, front - length, front
    front = W + 40 - dist
    return True, front, front + length


def gate_open(ln, lt):
    cyc, opn, ph = ln["gt"]
    return pmod(lt + ph, cyc) < opn


def gate_warn(ln, lt):
    cyc, opn, ph = ln["gt"]
    c = pmod(lt + ph, cyc)
    return opn - 0.8 < c < opn


def cy(r):
    return TOP + r * CELL + 8


# ----------------------------------------------------------------------------- upgrade cards
def _icon_quick(s, cx, cy_, t):
    for i in range(3):
        x = cx - 6 + i * 5 + int(t * 20) % 5
        s.fill(col("mint"), (x, cy_ - 3 + i, 3, 1))
    s.blit(sprite("ah_kit", 0), (cx - 5, cy_ - 4))


def _icon_pounce(s, cx, cy_, t):
    h = int(abs(math.sin(t * 4)) * 6)
    pygame.draw.line(s, col("orange"), (cx - 8, cy_ + 5), (cx, cy_ - 4 - h))
    pygame.draw.line(s, col("orange"), (cx, cy_ - 4 - h), (cx + 8, cy_ + 5))
    s.fill(col("white"), (cx - 2, cy_ - 6 - h, 5, 4))


def _icon_nap(s, cx, cy_, t):
    s.blit(sprite("ah_clock"), (cx - 4, cy_ - 3))
    draw_text(s, "Z", cx + 3, cy_ - 9 - int(t * 3) % 3, "sky", shadow=None)


def _icon_magnet(s, cx, cy_, t):
    pygame.draw.rect(s, col("red"), (cx - 6, cy_ - 6, 4, 10))
    pygame.draw.rect(s, col("red"), (cx + 3, cy_ - 6, 4, 10))
    pygame.draw.rect(s, col("red"), (cx - 6, cy_ + 1, 13, 4))
    s.fill(col("white"), (cx - 6, cy_ - 6, 4, 2))
    s.fill(col("white"), (cx + 3, cy_ - 6, 4, 2))


def _icon_bell(s, cx, cy_, t):
    s.blit(sprite("ah_bell"), (cx - 4 + int(math.sin(t * 9) * 1.5), cy_ - 4))


def _icon_swim(s, cx, cy_, t):
    for i in range(3):
        y = cy_ + 2 + i * 2
        x = cx - 7 + int(math.sin(t * 4 + i) * 2)
        s.fill(col("sky"), (x, y, 14, 1))
    s.blit(sprite("ah_kit", 1), (cx - 5, cy_ - 7))


def _icon_box(s, cx, cy_, t):
    art.draw_box(s, cx - 8, cy_ - 8, 1, t)


def _icon_luck(s, cx, cy_, t):
    pygame.draw.circle(s, col("white"), (cx, cy_), 6)
    s.fill(col("black"), (cx - 3, cy_ - 2, 1, 1))
    s.fill(col("black"), (cx + 2, cy_ - 2, 1, 1))
    s.fill(col("red"), (cx - 4, cy_ + 3, 9, 2))
    s.fill(col("yellow"), (cx - 1, cy_ + 4, 2, 2))
    wave = int(abs(math.sin(t * 5)) * 3)
    s.fill(col("white"), (cx + 6, cy_ - 4 - wave, 2, 4))


def _icon_fever(s, cx, cy_, t):
    for i in range(3):
        pygame.draw.circle(s, col(rainbow(i, t)), (cx - 4 + i * 4, cy_ + 1 - (i % 2) * 3), 2)


def _icon_family(s, cx, cy_, t):
    for i in range(3):
        art.draw_kitten(s, cx - 8 + i * 8, cy_ + 6 - (i % 2) * 2, i, t, "happy", seed=i)


UPGRADES = [
    Upgrade("quick", "QUICK PAWS", "FASTER|HOPS", "mint", _icon_quick, 3),
    Upgrade("pounce", "POUNCE", "X: LEAP OVER|A WHOLE LANE|FASTER EACH LV", "orange", _icon_pounce, 3),
    Upgrade("life", "NINE LIVES", "+1 LIFE|RIGHT NOW", "hotpink", "heart", 5),
    Upgrade("nap", "CAT NAP", "+8 SECONDS|ON EVERY|STAGE CLOCK", "sky", _icon_nap, 3),
    Upgrade("magnet", "FISH MAGNET", "GRAB TREATS|NEXT TO YOU", "lavender", _icon_magnet, 2),
    Upgrade("bell", "GUARDIAN BELL", "SAVES A|LOST KITTEN|EVERY STAGE", "yellow", _icon_bell, 2),
    Upgrade("swim", "SWIM PAWS", "SURVIVE A|SPLASH OR FALL|EVERY STAGE", "teal", _icon_swim, 2),
    Upgrade("box", "BOX ARMOR", "BLOCKS ONE|HIT EVERY|STAGE", "peach", _icon_box, 2),
    Upgrade("luck", "LUCKY CHARM", "MORE TREATS|AND JACKPOTS", "red", _icon_luck, 3),
    Upgrade("fever", "FEVER PURR", "FEVER FILLS|FASTER, LASTS|LONGER", "pink", _icon_fever, 3),
    Upgrade("family", "BIG FAMILY", "+50% FAMILY|BONUS PER|LEVEL", "lime", _icon_family, 3),
]


# ----------------------------------------------------------------------------- objects
class Hopper:
    """Sushi or a kitten: stands on a lane (row, lane-local x) or hops between two lanes."""

    def __init__(self, row, lx):
        self.row = row
        self.lx = float(lx)
        self.hopping = False
        self.ht = 0.0
        self.hd = HOP
        self.fr = row             # row the hop started on
        self.fx = 0.0             # world x at the start of the hop
        self.tr = row             # target row
        self.tx = 0.0             # target: world x (Sushi) / lane-local x (kittens: it rides with the lane)
        self.track = False
        self.kind = "hop"         # hop | pounce
        self.face = "up"

    def p(self):
        return min(1.0, self.ht / self.hd) if self.hopping else 0.0


class Kitten(Hopper):
    def __init__(self, r, x, coat, idx):
        super().__init__(r, x)
        self.home_r, self.home_x = r, float(x)
        self.coat = coat
        self.idx = idx
        self.state = "wait"       # wait | line | home | lost
        self.queue = []           # [start time, row, local x, kind]
        self.lost_t = 0.0
        self.lost_x = self.lost_y = 0.0
        self.flash = 0.0
        self.carrier = False


class Item:
    def __init__(self, kind, r, x, carrier):
        self.kind, self.row, self.x, self.carrier = kind, r, float(x), carrier
        self.alive = True
        self.life = -1.0          # bonus snacks fade away


# ----------------------------------------------------------------------------- the game
class AlleyHop(GameScene):
    @property
    def music(self):
        return self.song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES[d]
        self.tmul = SPEED[d]
        self.levels = {}
        self.life_i = 0
        self.picks_left = 0
        self.pick_title = "POWER UP!"
        self.next_n = None
        self.hype.COMBO_TIME = 3.0
        self.hype.combo_y = 14
        start = max(1, min(STAGES, int(opt.get("stage", opt.get("start", 1)))))
        self.start_stage(start)
        if start > 10:          # starting from a checkpoint: catch up on some upgrades first
            self.picks_left = min(8, (start - 1) // 10)
            self.pick_title = "HEAD START!"
            self.state = "pick"

    # ---------------------------------------------------------------- helpers
    def lv(self, uid):
        return self.levels.get(uid, 0)

    def factor(self, pts):
        return pts * (10 + self.tier) // 10

    def score_at(self, pts, x=None, y=None, color="yellow"):
        return self.add(self.factor(pts), x, y, color)

    def song(self):
        k = self.st["kind"]
        if k == "boss":
            return "boss"
        if k == "bonus":
            return "bonus"
        return "ah_canal" if THEMES[self.tier][10] in ("W", "G") else "ah_alley"

    def fever_gain(self, x):
        return x * (1 + 0.35 * self.lv("fever"))

    def hop_time(self, kind="hop"):
        t = HOP * (1 - 0.1 * self.lv("quick"))
        if self.zoom_t > 0:
            t *= 0.7
        if self.hype.fever_on:
            t *= 0.85
        if kind == "pounce":
            t = POUNCE_T * (1 - 0.06 * self.lv("quick"))
        return t

    # ---------------------------------------------------------------- stages
    def start_stage(self, n):
        self.n = n
        st = self.st = CAMPAIGN[n - 1]
        self.tier = st["tier"]
        self.theme = THEMES[self.tier]
        self.reached(n)
        self.lanes = st["lanes"]
        self.lt = 0.0                # lane time (traffic clock)
        self.pt = 0.0                # play time
        self.boxes = list(st["boxes"])
        self.box_n = [0] * len(self.boxes)
        self.kittens = [Kitten(r, x, coat, i) for i, (r, x, coat) in enumerate(st["kittens"])]
        for k in self.kittens:
            k.carrier = self.lanes[k.home_r]["t"] in CARRIERS
        self.line = []
        self.need = len(self.kittens)
        self.home_count = 0
        self.items = []
        for kind, r, x in st["items"]:
            self.items.append(Item(kind, r, x, self.lanes[r]["t"] in CARRIERS))
        self.boss = Boss(self, st["boss"]) if st["kind"] == "boss" else None
        if self.boss:
            self.need = self.boss.hp
        self.mh = [list(m) for m in st["manholes"]]
        self.wet_cells = {}          # (row, col) -> seconds (puddles a sweeper leaves behind)
        self.freed = []              # boss-freed kittens flying home: [x, y, tx, ty, t, coat, box]
        self.ghosts = []             # lost kittens floating back: [x, y, t, coat]
        nap = 8 * self.lv("nap") if st["kind"] == "normal" else 3 * self.lv("nap")
        self.clock = float(st["clock"] + nap)
        self.clock_full = self.clock
        self.shield = self.lv("box")
        self.bells = self.lv("bell")
        self.swims = self.lv("swim")
        self.zoom_t = self.slow_t = 0.0
        self.pounce_cd = 0.0
        self.inv = 0.0
        self.stun = 0.0
        self.missed = False
        self.lost_any = False
        self.hurt_boss = False
        self.stage_combo = 0
        self.fish_n = self.gold_n = 0
        self.trip_n = 0
        self.best_family = 0
        self.spawn_t = 0.0
        self.bump_cd = 0.0
        self.home_wait = 0.0
        self.dead_t = 0.0
        self.death = ""
        self.tally = []
        self.buf = None
        self.buf_t = 0.0
        self.wet = False
        self.new_sushi()
        if st["kind"] == "normal":
            luck = 0.03 + 0.02 * self.lv("luck")
            if self.hype.lucky(luck):
                self.spawn_item("gold")
            if self.hype.lucky(0.05 + 0.05 * self.lv("luck")):
                self.spawn_item(random.choice(["nip", "bell", "box", "clock"]))
            if self.hype.lucky(0.01 + 0.01 * self.lv("luck")):
                self.spawn_item("heart")
        self.state = "intro"
        self.state_t = 0.0
        self.intro_len = 3.2 if self.boss else 2.6
        self.bg = self.make_bg()
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.app.audio.music(self.song())
        self.app.audio.play("warning" if self.boss else "stage")
        if self.boss:
            self.hype.flash("red", 0.3)

    def new_sushi(self):
        self.sushi = Hopper(10, START_COL * CELL + 8)
        self.sushi.face = "up"
        self.trip_best = 10
        self.safe_r, self.safe_x = 10, float(START_COL * CELL + 8)
        self.wet = False
        self.buf = None
        self.home_box = -1

    def spawn_item(self, kind):
        cells = []
        for r in range(1, 10):
            ln = self.lanes[r]
            if ln["t"] == "safe":
                for c in range(COLS):
                    if c not in ln["bl"] and not self.item_at(r, c * CELL + 8) and not self.kitten_at(r, c * CELL + 8):
                        cells.append((r, c))
        if cells:
            r, c = random.choice(cells)
            self.items.append(Item(kind, r, c * CELL + 8, False))

    def item_at(self, r, x):
        return any(it.alive and it.row == r and not it.carrier and abs(it.x - x) < 4 for it in self.items)

    def kitten_at(self, r, x):
        return any(k.state == "wait" and k.home_r == r and abs(k.home_x - x) < 4 for k in self.kittens)

    # ---------------------------------------------------------------- lanes
    def shift(self, r):
        ln = self.lanes[r]
        if ln["t"] not in CARRIERS:
            return 0.0
        return lane_shift(ln, self.lt)

    def on_platform(self, r, x):
        ln = self.lanes[r]
        if ln["t"] == "belt":
            return True
        sh = lane_shift(ln, self.lt)
        u = pmod(x + pad_of(ln) - sh, ln["p"])
        for i, (kind, ix, w) in enumerate(ln["it"]):
            if ix + 2 <= u <= ix + w - 2 and dive_state(ln, i, self.lt) < 2:
                return True
        return False

    def pattern_wx(self, r, px):
        """World x of something sitting on a carrier pattern at pattern x px."""
        ln = self.lanes[r]
        return pmod(px + lane_shift(ln, self.lt), ln["p"]) - pad_of(ln)

    def hx(self, h):
        if h.hopping:
            end = h.tx + self.shift(h.tr) if h.track else h.tx
            return h.fx + (end - h.fx) * h.p()
        return h.lx + self.shift(h.row)

    def hy(self, h):
        if h.hopping:
            return cy(h.fr) + (cy(h.tr) - cy(h.fr)) * h.p()
        return float(cy(h.row))

    def hrow(self, h):
        if h.hopping:
            return h.tr if h.p() >= 0.5 else h.fr
        return h.row

    def sushi_x(self):
        return self.hx(self.sushi)

    def kitten_wx(self, k):
        if k.state == "wait" and k.carrier:
            return self.pattern_wx(k.home_r, k.home_x)
        if k.state == "wait":
            return k.home_x
        return self.hx(k)

    def lid_open(self, i):
        if not self.st["lids"]:
            return True
        cyc, opn = self.st["lids"]
        return pmod(self.lt + i * 1.3, cyc) < opn

    def lid_warn(self, i):
        if not self.st["lids"]:
            return False
        cyc, opn = self.st["lids"]
        c = pmod(self.lt + i * 1.3, cyc)
        return opn - 0.9 < c < opn

    def puddle(self, r, x):
        c = int(x // CELL)
        return c in self.lanes[r]["pd"] or (r, c) in self.wet_cells

    def wet_cell(self, y, x):
        """A sweeper leaves wet floor behind it."""
        r = int((y - TOP) // CELL)
        c = int(x // CELL)
        if 1 <= r <= 9 and 0 <= c < COLS and self.lanes[r]["t"] in ("safe", "road"):
            self.wet_cells[(r, c)] = 5.0

    def vehicles(self, r):
        """[(kind, screen x, w, i)] of the traffic in a road lane."""
        ln = self.lanes[r]
        sh = lane_shift(ln, self.lt)
        return [(kind, item_sx(ln, ix, sh), w, i) for i, (kind, ix, w) in enumerate(ln["it"])]

    def danger(self, r, x, rad=5, airborne=False):
        """What would hurt an entity at (row r, world x) right now? None / hit / soft / train / squish."""
        ln = self.lanes[r]
        t = ln["t"]
        if not airborne:
            if t == "road":
                for kind, X, w, _ in self.vehicles(r):
                    if X + 2 < x + rad and X + w - 2 > x - rad:
                        return "soft" if ln["soft"] else "hit"
            elif t == "rail":
                _, x0, x1 = train_span(ln, self.lt)
                if x0 is not None and x0 < x + rad and x1 > x - rad:
                    return "train"
            elif t == "fence":
                if not gate_open(ln, self.lt):
                    return "squish"
        if self.boss and self.boss.hurts(x, cy(r), rad):
            return "hit"
        return None

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        s = self.state
        if s == "intro":
            self.lt += dt * self.tmul * 0.5
            if self.boss:
                self.boss.update(dt)
            if self.state_t > self.intro_len or (self.state_t > 0.5 and self.app.input.hit("a")):
                self.state = "play"
                self.state_t = 0.0
        elif s == "play":
            self.play(dt)
        elif s == "dead":
            self.lt += dt * self.tmul
            self.update_world(dt)
            if self.state_t > 1.3:
                if self.lives <= 0:
                    self.state = "over"
                    self.hype.banner("GAME OVER", f"STAGE {self.n}", color="red", dur=3.0)
                    self.app.audio.play("gameover")
                    self.end_game(False, f"STAGE {self.n}", delay=2.5)
                else:
                    self.new_sushi()
                    self.inv = 1.2
                    self.state = "play"
                    self.state_t = 0.0
        elif s == "bossdown":
            self.boss.update(dt)
            self.update_world(dt)
            if self.state_t > 2.6:
                self.stage_clear()
        elif s == "clear":
            self.update_world(dt)
            if self.state_t > 1.6:
                self.begin_tally()
        elif s == "tally":
            self.update_tally(dt)
        elif s == "pick":
            if self.picks_left > 0:
                self.picks_left -= 1
                self.pick_upgrade(UPGRADES, self.levels, self.on_pick, self.pick_title)
            elif self.next_n is None:
                self.state = "intro"
                self.state_t = 0.0
            else:
                self.start_stage(self.next_n)

    def on_pick(self, uid):
        if not uid:
            return
        self.levels[uid] = self.lv(uid) + 1
        u = next(x for x in UPGRADES if x.id == uid)
        self.hype.banner(u.name, f"LEVEL {self.levels[uid]}", color=u.color, dur=1.2, scale=1)
        if uid == "life":
            self.lives += 1
            self.app.audio.play("extra")
        elif uid == "box":
            self.shield += 1
        elif uid == "bell":
            self.bells += 1
        elif uid == "swim":
            self.swims += 1
        elif uid == "fever":
            self.hype.FEVER_TIME = 8.0 + 1.5 * self.levels[uid]

    def play(self, dt):
        inp = self.app.input
        st = self.st
        self.pt += dt
        slow = 0.35 if self.slow_t > 0 else 1.0
        self.lt += dt * self.tmul * slow
        self.zoom_t = max(0.0, self.zoom_t - dt)
        self.slow_t = max(0.0, self.slow_t - dt)
        self.pounce_cd = max(0.0, self.pounce_cd - dt)
        self.inv = max(0.0, self.inv - dt)
        self.stun = max(0.0, self.stun - dt)
        self.bump_cd = max(0.0, self.bump_cd - dt)
        self.buf_t = max(0.0, self.buf_t - dt)
        if self.buf_t <= 0:
            self.buf = None
        if not self.boss:
            self.clock -= dt
            if self.clock <= 0:
                if st["kind"] == "bonus":
                    self.clock = 0.0
                    self.stage_clear()
                    return
                self.clock = max(20.0, self.clock_full * 0.5)
                self.die("time")
                return
        # input: one hop per press, the latest press during a hop is buffered
        want = None
        pounce = False
        for d in ("up", "down", "left", "right"):
            if inp.hit(d):
                want = d
        if inp.hit("a"):
            want = "up"
        if inp.hit("b") and self.lv("pounce") > 0:
            pounce = True
            want = want or self.sushi.face
        if want:
            self.buf = (want, pounce)
            self.buf_t = 0.3
        s = self.sushi
        if self.home_box < 0:
            if s.hopping:
                s.ht += dt
                if s.ht >= s.hd:
                    self.sushi_land()
                    if self.state != "play":
                        return
            if not s.hopping and self.home_box < 0 and self.buf and self.stun <= 0:
                d, pc = self.buf
                self.buf = None
                self.try_hop(d, pc)
        else:
            self.home_wait += dt
            if not self.line or self.home_wait > 8:
                for k in list(self.line):
                    self.lose_kitten(k, "")
                self.trip_done()
                if self.state != "play":
                    return
        self.update_world(dt)
        if self.state != "play":
            return
        # Sushi's own dangers
        if self.home_box < 0 and self.inv <= 0:
            r = self.hrow(s)
            x = self.hx(s)
            air = s.hopping and s.kind == "pounce" and 0.12 < s.p() < 0.88
            cause = self.danger(r, x, 5, air)
            if cause:
                self.die(cause)
                if self.state != "play":
                    return
            if not s.hopping and self.lanes[s.row]["t"] in ("water", "gap"):
                if not self.on_platform(s.row, x) or x < 2 or x > W - 2:
                    self.die("splash" if self.lanes[s.row]["t"] == "water" else "fall")
                    if self.state != "play":
                        return
            if not s.hopping and self.lanes[s.row]["t"] == "belt":
                s.lx = max(8.0, min(W - 8.0, x)) - self.shift(s.row)
        if self.boss:
            self.update_boss(dt)
        elif st["kind"] == "bonus" and st["bonus"] == "feast":
            self.update_feast(dt)
        self.check_life()

    def update_world(self, dt):
        """Kittens, items, effects - also while Sushi is down or the stage is being cleared."""
        for key in list(self.wet_cells):
            self.wet_cells[key] -= dt
            if self.wet_cells[key] <= 0:
                del self.wet_cells[key]
        for k in self.kittens:
            k.flash = max(0.0, k.flash - dt)
            if k.state == "lost":
                k.lost_t -= dt
                if k.lost_t <= 0:
                    k.state = "wait"
                    k.row, k.lx = k.home_r, k.home_x
                    k.hopping = False
                    self.parts.burst(self.kitten_wx(k), cy(k.home_r), 6, ("white", "pink"), 30, 0.4)
        for k in list(self.line):
            self.update_kitten(k, dt)
        for g in self.ghosts:
            g[2] += dt
            g[1] -= 22 * dt
        self.ghosts = [g for g in self.ghosts if g[2] < 1.2]
        for f in self.freed:
            f[4] += dt
            if f[4] >= 1.0 and f[6] >= 0:
                self.box_n[f[6]] += 1
                self.parts.burst(f[2], f[3], 10, ("pink", "white", "yellow"), 40, 0.5)
                self.app.audio.play("fruit")
                f[6] = -1
        self.freed = [f for f in self.freed if f[4] < 1.0]
        for it in self.items:
            if it.life > 0:
                it.life -= dt
                if it.life <= 0:
                    it.alive = False
        self.items = [it for it in self.items if it.alive]

    def update_kitten(self, k, dt):
        if k.hopping:
            k.ht += dt
            if k.ht >= k.hd:
                self.land(k)
                self.kitten_landed(k)
                if k.state != "line":
                    return
        while not k.hopping and k.queue and self.pt >= k.queue[0][0]:
            t0, r, lx, kind = k.queue.pop(0)
            if kind == "warp":
                self.parts.burst(self.hx(k), cy(k.row), 6, ("gray", "lime"), 30, 0.3)
                k.row, k.lx = r, lx
                continue
            k.face = "up" if r < k.row else "down" if r > k.row else ("right" if lx > k.lx else "left")
            self.start_hop(k, r, lx, True, kind, KHOP * (1 - 0.1 * self.lv("quick")) if kind == "hop" else POUNCE_T)
        if self.zoom_t > 0 or k.flash > 0 or self.state != "play":
            return
        r = self.hrow(k)
        x = self.hx(k)
        air = k.hopping and k.kind == "pounce" and 0.12 < k.p() < 0.88
        cause = self.danger(r, x, 4, air)
        if not cause and not k.hopping and self.lanes[k.row]["t"] in ("water", "gap"):
            if not self.on_platform(k.row, x) or x < 2 or x > W - 2:
                cause = "splash"
        if cause:
            self.lose_kitten(k, cause)

    def start_hop(self, h, tr, tx, track, kind, dur):
        h.fx = self.hx(h)
        h.fr = h.row
        h.tr = tr
        h.tx = tx
        h.track = track
        h.kind = kind
        h.hd = dur
        h.ht = 0.0
        h.hopping = True

    def land(self, h):
        end = h.tx + self.shift(h.tr) if h.track else h.tx
        h.hopping = False
        h.row = h.tr
        h.lx = h.tx if h.track else end - self.shift(h.tr)

    # ---------------------------------------------------------------- Sushi
    def can_enter(self, tr, tx):
        """(ok, snapped x) for a hop into row tr at world x tx."""
        if tr < 0 or tr >= ROWS or tx < 4 or tx > W - 4:
            return False, tx
        ln = self.lanes[tr]
        if tr == 0:
            if self.boss:
                return False, tx
            for i, c in enumerate(self.boxes):
                bx = c * CELL + 8
                if abs(bx - tx) <= 9 and self.lid_open(i):
                    return True, float(bx)
            return False, tx
        if ln["t"] not in CARRIERS:
            c = max(0, min(COLS - 1, int(tx // CELL)))
            tx = float(c * CELL + 8)
            if c in ln["bl"]:
                return False, tx
            if ln["t"] == "fence" and (c not in ln["gc"] or not gate_open(ln, self.lt)):
                return False, tx
        return True, tx

    def try_hop(self, d, pounce):
        s = self.sushi
        dr, dc = DIRS[d]
        s.face = d
        x = self.hx(s)
        tries = [(2, "pounce"), (1, "hop")] if pounce and self.pounce_cd <= 0 else [(1, "hop")]
        for dist, kind in tries:
            tr = s.row + dr * dist
            ok, tx = self.can_enter(tr, x + dc * dist * CELL)
            if ok:
                if kind == "pounce":
                    self.pounce_cd = (4.0, 4.0, 3.0, 2.0)[min(3, self.lv("pounce"))]
                    self.app.audio.play("powerup")
                else:
                    self.app.audio.play("jump" if not self.wet else "move")
                dur = self.hop_time(kind) * (1.8 if self.wet and kind == "hop" else 1.0)
                self.wet = False
                self.start_hop(s, tr, tx, False, kind, dur)
                return True
        self.app.audio.play("tin")
        return False

    def sushi_land(self):
        s = self.sushi
        self.land(s)
        r = s.row
        x = self.hx(s)
        for k_i, k in enumerate(self.line):
            k.queue.append([self.pt + k_i * KDELAY, r, s.lx, s.kind])
        ln = self.lanes[r]
        if r == 0:
            self.reach_home(x)
            return
        if ln["t"] in ("water", "gap") and (not self.on_platform(r, x) or x < 2 or x > W - 2):
            self.die("splash" if ln["t"] == "water" else "fall")
            return
        if ln["t"] not in CARRIERS:
            self.safe_r, self.safe_x = r, x
        self.wet = ln["t"] in ("safe", "road", "start") and self.puddle(r, x)
        if self.wet:
            self.app.audio.play("bubble")
            self.parts.burst(x, cy(r) + 4, 6, ("sky", "white"), 30, 0.3)
        g = self.hype
        if r < self.trip_best:
            steps = self.trip_best - r
            self.trip_best = r
            self.score_at(10 * steps)
            self.stage_combo = max(self.stage_combo, g.hit(1, fever=self.fever_gain(0.012)))
        self.pickups(r, x)
        # manhole shortcut: the lower lid pops you out of the upper one
        for m in self.mh:
            if m[0] == r and abs(m[1] * CELL + 8 - x) < 4:
                self.warp(m)
                break
        if self.boss:
            br = self.boss.bop_rect()
            if br and br[0] <= x <= br[0] + br[2] and br[1] <= cy(r) <= br[1] + br[3]:
                self.bop_boss()
        if ln["t"] == "road" and not ln["soft"]:
            for kind, X, w, _ in self.vehicles(r):
                gap = min(abs(X - (x + 5)), abs(x - 5 - (X + w)))
                if gap < 5:
                    self.score_at(50, x, cy(r) - 12, "mint")
                    self.floats.add(x, cy(r) - 20, "CLOSE!", "mint")
                    g.hit(1, fever=self.fever_gain(0.02))
                    break

    def warp(self, m):
        s = self.sushi
        r1, c1, r2, c2 = m
        x1 = c1 * CELL + 8
        self.parts.burst(x1, cy(r1), 10, ("gray", "lime", "white"), 50, 0.4)
        s.row, s.lx = r2, float(c2 * CELL + 8)
        for k_i, k in enumerate(self.line):
            k.queue.append([self.pt + k_i * KDELAY + 0.01, r2, float(c2 * CELL + 8), "warp"])
        self.parts.burst(c2 * CELL + 8, cy(r2), 12, ("gray", "lime", "white"), 60, 0.5)
        self.app.audio.play("pop")
        self.floats.add(c2 * CELL + 8, cy(r2) - 14, "SHORTCUT!", "lime")
        if r2 < self.trip_best:
            self.score_at(10 * (self.trip_best - r2))
            self.trip_best = r2
        self.safe_r, self.safe_x = r2, float(c2 * CELL + 8)
        self.pickups(r2, c2 * CELL + 8)

    def pickups(self, r, x):
        mag = self.lv("magnet")
        for it in self.items:
            if not it.alive:
                continue
            ix = self.pattern_wx(it.row, it.x) if it.carrier else it.x
            dr = abs(it.row - r)
            dx = abs(ix - x)
            near = (dr == 0 and dx < 10) or (mag >= 1 and dr == 0 and dx < 26) or \
                   (mag >= 1 and dr == 1 and dx < 10) or (mag >= 2 and dr == 1 and dx < 26)
            if near:
                it.alive = False
                self.collect(it, ix, cy(it.row))
        for k in self.kittens:
            if k.state == "wait" and k.home_r == r and abs(self.kitten_wx(k) - x) < 11:
                self.pick_kitten(k)

    def collect(self, it, x, y):
        g = self.hype
        au = self.app.audio
        k = it.kind
        if k == "fish":
            self.fish_n += 1
            self.score_at(100 + g.combo_bonus(5), x, y - 8)
            g.hit(1, fever=self.fever_gain(0.03))
            au.play("eat")
        elif k == "yarn":
            self.fish_n += 1
            self.score_at(50 + g.combo_bonus(5), x, y - 8, "pink")
            g.hit(2, fever=self.fever_gain(0.03))
            au.play("fruit")
        elif k == "gold":
            self.gold_n += 1
            if self.st["kind"] == "bonus":
                self.score_at(1500, x, y - 8, "orange")
                g.hit(3, fever=self.fever_gain(0.05))
                au.play("coin")
                self.parts.burst(x, y, 14, ("yellow", "orange", "white"), 60, 0.6)
            else:
                g.jackpot(self.factor(5000), "GOLDEN FISH!")
        elif k == "clock":
            self.clock += 15
            self.hype.banner("+15 SECONDS", color="sky", dur=1.0, scale=1, sound="powerup")
        elif k == "nip":
            self.zoom_t = 6.0
            self.hype.banner("ZOOMIES!", "CATNIP POWER", rainbow=True, dur=1.4, sound="powerup")
            self.hype.flash("lime", 0.2)
        elif k == "bell":
            self.slow_t = 5.0
            self.hype.banner("TIME PAWS", "TRAFFIC SLOWS DOWN", color="yellow", dur=1.4, sound="powerup")
        elif k == "box":
            self.shield = min(3, self.shield + 1)
            self.hype.banner("BOX ARMOR!", color="peach", dur=1.0, scale=1, sound="powerup")
        elif k == "heart":
            self.lives += 1
            self.hype.banner("1 UP!", color="pink", dur=1.2, sound="extra")
            self.hype.shower(12, "hearts")
        self.parts.burst(x, y, 8, ("yellow", "white", "pink"), 40, 0.4)

    def pick_kitten(self, k):
        s = self.sushi
        k.state = "line"
        k.row = s.row
        k.lx = s.lx
        k.hopping = False
        k.queue = []
        k.flash = 0.0
        self.line.append(k)
        self.score_at(200, self.sushi_x(), cy(s.row) - 10, "pink")
        self.stage_combo = max(self.stage_combo, self.hype.hit(2, fever=self.fever_gain(0.04)))
        self.app.audio.play("bonus")
        self.floats.add(self.sushi_x(), cy(s.row) - 20, "MEW!", "white")
        self.parts.burst(self.sushi_x(), cy(s.row), 8, ("pink", "white"), 40, 0.4)

    def kitten_landed(self, k):
        r = k.row
        x = self.hx(k)
        if r == 0:
            self.deliver(k, x)
            return
        ln = self.lanes[r]
        if ln["t"] in ("water", "gap") and not self.on_platform(r, x):
            self.lose_kitten(k, "splash")

    def deliver(self, k, x):
        k.state = "home"
        if k in self.line:
            self.line.remove(k)
        i = min(range(len(self.boxes)), key=lambda j: abs(self.boxes[j] * CELL + 8 - x))
        self.box_n[i] += 1
        self.home_count += 1
        self.trip_n += 1
        self.score_at(500, x, TOP - 2 + 10, "pink")
        self.stage_combo = max(self.stage_combo, self.hype.hit(2, fever=self.fever_gain(0.05)))
        self.app.audio.play("coin" if self.trip_n < 3 else "levelup")
        self.parts.burst(x, cy(0), 12, ("pink", "hotpink", "white", "yellow"), 50, 0.6)

    def lose_kitten(self, k, cause):
        if k.state != "line":
            return
        if cause and self.bells > 0:          # GUARDIAN BELL: the kitten is saved once
            self.bells -= 1
            k.flash = 1.5
            self.hype.banner("BELL SAVE!", color="yellow", dur=1.0, scale=1, sound="hold")
            self.parts.burst(self.hx(k), self.hy(k), 10, ("yellow", "white"), 40, 0.5)
            return
        x, y = self.hx(k), self.hy(k)
        if k in self.line:
            self.line.remove(k)
        k.state = "lost"
        k.lost_t = 1.6
        k.queue = []
        k.hopping = False
        if cause:
            self.lost_any = True
            self.hype.break_combo()
            self.app.audio.play("hurt" if cause != "splash" else "bubble")
            self.floats.add(x, y - 12, "MEW..." if cause != "splash" else "SPLASH!", "pink")
            self.parts.burst(x, y, 10, ("white", "pink", "sky") if cause == "splash" else ("white", "pink"), 50, 0.5)
            self.ghosts.append([x, y, 0.0, k.coat])

    def reach_home(self, x):
        i = min(range(len(self.boxes)), key=lambda j: abs(self.boxes[j] * CELL + 8 - x))
        self.home_box = i
        self.home_wait = 0.0
        self.trip_n = 0
        self.app.audio.play("select")
        self.score_at(100, x, TOP + 4, "white")
        self.parts.burst(x, cy(0), 8, ("yellow", "white"), 40, 0.4)
        if not self.line:
            self.trip_done()

    def trip_done(self):
        """Sushi waited in a box until her line was home (or lost). Pay the family bonus, go again."""
        n = self.trip_n
        g = self.hype
        if n >= 2:
            pts = self.factor(250 * n * (n - 1)) * (2 + self.lv("family")) // 2
            self.best_family = max(self.best_family, n)
            x = self.boxes[self.home_box] * CELL + 8
            if n >= 5:
                g.banner("MEGA FAMILY!", f"{n} KITTENS AT ONCE  +{pts * g.mult}", rainbow=True, dur=2.0, sound="fever")
                g.shower(30, "hearts")
                g.slowmo(0.4, 0.6)
                self.app.shake(3, 0.3)
            elif n >= 3:
                g.banner(f"FAMILY X{n}!", f"+{pts * g.mult}", rainbow=True, dur=1.6, sound="combo")
                g.shower(14, "hearts")
            else:
                g.banner("FAMILY X2", f"+{pts * g.mult}", color="pink", dur=1.2, scale=1, sound="combo")
            self.add(pts)
            g.hit(n, fever=self.fever_gain(0.06))
            self.parts.burst(x, cy(0), 20, ("pink", "hotpink", "yellow", "white"), 70, 0.8)
        if n >= 1:
            self.best_family = max(self.best_family, n)
        self.trip_n = 0
        if self.home_count >= self.need and self.need > 0:
            self.stage_clear()
            return
        self.new_sushi()
        self.parts.burst(START_COL * CELL + 8, cy(10), 8, ("white", "yellow"), 30, 0.3)

    def die(self, cause):
        g = self.hype
        au = self.app.audio
        s = self.sushi
        x, y = self.hx(s), self.hy(s)
        if cause == "squish":          # a closing gate shoves Sushi back where she came from
            r = self.hrow(s)
            back = s.fr if s.hopping and s.fr != r else min(ROWS - 1, r + 1)
            s.hopping = False
            s.row = back
            s.lx = float(max(0, min(COLS - 1, int(x // CELL))) * CELL + 8) - self.shift(back)
            self.stun = 0.35
            self.inv = 0.5
            g.break_combo()
            au.play("tin")
            self.app.shake(2, 0.2)
            self.floats.add(x, y - 12, "BONK!", "orange")
            for k_i, k in enumerate(self.line):
                k.queue.append([self.pt + 0.1 + k_i * KDELAY, s.row, s.lx, "hop"])
            return
        if cause in HURTS and self.zoom_t > 0:
            if self.bump_cd <= 0:
                self.bump_cd = 0.4
                self.score_at(100, x, y - 10, "lime")
                self.floats.add(x, y - 18, "BONK!", "lime")
                au.play("brick")
                g.hit(1)
            return
        if cause in ("splash", "fall") and self.swims > 0:
            self.swims -= 1
            au.play("bubble")
            g.banner("SWIM PAWS!", color="teal", dur=1.0, scale=1)
            self.parts.burst(x, y, 12, ("sky", "white"), 50, 0.5)
            s.hopping = False
            s.row, s.lx = self.safe_r, self.safe_x - self.shift(self.safe_r)
            for k in self.line:
                k.hopping = False
                k.queue = []
                k.row, k.lx = s.row, s.lx
            self.inv = 0.8
            return
        if cause in HURTS and self.shield > 0:
            self.shield -= 1
            self.inv = 1.2
            au.play("pop")
            g.banner("BOX ARMOR!", "SAVED YOU", color="peach", dur=1.0, scale=1)
            self.parts.burst(x, y, 14, ("brown", "peach", "cream"), 60, 0.6)
            self.app.shake(2, 0.2)
            return
        if cause == "soft":
            self.stun = 0.8
            self.inv = 1.4
            g.break_combo()
            au.play("hurt")
            self.floats.add(x, y - 12, "BUMP!", "pink")
            for k in list(self.line):
                self.lose_kitten(k, "")
            return
        # a real miss
        self.lives -= 1
        self.missed = True
        if self.boss:
            self.hurt_boss = True
        g.break_combo()
        self.death = cause
        self.dead_x, self.dead_y = x, y
        self.state = "dead"
        self.state_t = 0.0
        for k in list(self.line):
            self.lose_kitten(k, "")
        if cause in ("splash", "fall"):
            au.play("bubble")
            self.parts.burst(x, y, 16, ("sky", "white", "blue") if cause == "splash" else ("gray", "white"), 60, 0.6)
        else:
            au.play("hurt")
            self.parts.burst(x, y, 16, ("white", "orange", "choco"), 70, 0.6)
        self.app.shake(4 if cause in ("train", "hit") else 2, 0.35)
        msg = {"hit": "BONK!", "splash": "SPLASH!", "fall": "WHOOPS!", "train": "TOOT TOOT!",
               "time": "SUNRISE!"}.get(cause, "OUCH!")
        if self.lives > 0:
            g.banner(msg, f"{self.lives} LEFT", color="pink", dur=1.2, scale=1)
        else:
            au.play("die")

    def check_life(self):
        i = self.life_i
        target = LIFE_AT[i] if i < len(LIFE_AT) else LIFE_AT[-1] + 150000 * (i - len(LIFE_AT) + 1)
        if self.score >= target:
            self.life_i += 1
            self.lives += 1
            self.hype.banner("BONUS LIFE!", f"{target} POINTS", color="pink", dur=1.4, sound="extra")
            self.hype.shower(16, "hearts")

    # ---------------------------------------------------------------- boss / bonus
    def update_boss(self, dt):
        b = self.boss
        b.update(dt * (0.5 if self.slow_t > 0 else 1.0))

    def bop_boss(self):
        b = self.boss
        g = self.hype
        x, y = b.hx, b.hy
        b.hit()
        g.hitstop(0.08)
        g.flash("white", 0.15)
        self.app.shake(4, 0.3)
        self.app.audio.play("explode")
        self.score_at(2000, x, y - 16, "orange")
        self.stage_combo = max(self.stage_combo, g.hit(3, fever=self.fever_gain(0.08)))
        self.parts.burst(x, y, 20, ("yellow", "white", "orange"), 80, 0.6)
        # a kitten pops free and runs to a box
        i = len(self.freed) + self.home_count
        box = i % len(self.boxes)
        self.freed.append([x, y, self.boxes[box] * CELL + 8, float(cy(0)), 0.0, i % 6, box])
        self.home_count += 1
        self.floats.add(x, y - 24, "FREE!", "pink")
        if b.hp <= 0:
            self.boss_defeated()

    def boss_defeated(self):
        g = self.hype
        self.app.audio.play("bossdown")
        g.banner("BOSS DOWN!", self.boss.name, rainbow=True, dur=2.4, scale=2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(30, "hearts")
        g.slowmo(0.3, 1.4)
        self.app.shake(6, 0.6)
        self.score_at(15000, W / 2, 80)
        self.state = "bossdown"
        self.state_t = 0.0
        self.app.audio.music(None)

    def update_feast(self, dt):
        """FISH FEAST: snacks keep appearing on the belts and sidewalks."""
        self.spawn_t -= dt
        alive = sum(1 for it in self.items if it.alive)
        if self.spawn_t <= 0 and alive < 16:
            self.spawn_t = 0.3
            r = random.randint(1, 10)
            ln = self.lanes[r]
            kind = "gold" if self.hype.lucky(0.05 + 0.02 * self.lv("luck")) else random.choice(["fish", "fish", "yarn"])
            if ln["t"] == "belt":
                ix = random.randint(pad_of(ln), pad_of(ln) + W - 16)
                it = Item(kind, r, pmod(ix - lane_shift(ln, self.lt) + 0.0, ln["p"]), True)
            elif ln["t"] in ("safe", "start"):
                it = Item(kind, r, random.randint(0, COLS - 1) * CELL + 8, False)
            else:
                return
            it.life = 7.0
            self.items.append(it)

    # ---------------------------------------------------------------- clear / tally
    def stage_clear(self):
        if self.state in ("clear", "tally"):
            return
        self.state = "clear"
        self.state_t = 0.0
        g = self.hype
        if g.fever_on:
            g.fever_t = 0.0
        g.slowmo(0.4, 0.8)
        self.app.audio.play("win")
        self.app.audio.music(None)
        k = self.st["kind"]
        if k == "normal":
            g.banner("ALL HOME!", "EVERY KITTEN IS SAFE", color="mint", dur=1.5)
            g.shower(30, "confetti")
        elif k == "bonus":
            g.banner("TIME UP!" if self.clock <= 0 else "ALL DONE!", color="yellow", dur=1.4)

    def begin_tally(self):
        st = self.st
        f = self.factor
        rows = []
        k = st["kind"]
        if k == "normal":
            rows.append(("STAGE CLEAR", f(1000)))
            rows.append((f"TIME LEFT {int(self.clock)}", f(int(self.clock) * 40)))
            rows.append(("NO KITTEN LOST", f(2000) if not self.lost_any else 0))
        elif k == "boss":
            rows.append(("BOSS BONUS", f(10000 + 2000 * self.tier)))
            rows.append(("NO DAMAGE", f(8000) if not self.hurt_boss else 0))
        elif st["bonus"] == "feast":
            rows.append((f"TREATS X{self.fish_n}", f(self.fish_n * 60)))
            rows.append((f"GOLDEN X{self.gold_n}", f(self.gold_n * 600)))
        else:
            rows.append((f"KITTENS HOME X{self.home_count}", f(self.home_count * 300)))
            rows.append((f"BIGGEST FAMILY {self.best_family}", f(self.best_family * 800)))
            rows.append(("EVERYONE HOME", f(5000) if self.home_count >= self.need else 0))
        rows.append((f"BEST COMBO {self.stage_combo}", f(self.stage_combo * 30)))
        if k != "bonus":
            rows.append(("NO MISS", f(3000) if not self.missed else 0))
        self.tally = [[label, v, 0.0] for label, v in rows]
        self.tally_i = 0
        self.tally_wait = 0.0
        self.state = "tally"
        self.state_t = 0.0
        if k == "normal" and not self.missed and not self.lost_any:
            self.hype.banner("PURRFECT!", "NOBODY GOT HURT", rainbow=True, dur=1.8, sound="fever")
            self.hype.shower(40, "stars")

    def update_tally(self, dt):
        skip = self.state_t > 0.3 and self.app.input.hit("a")
        if self.tally_i < len(self.tally):
            if skip:
                for row in self.tally[self.tally_i:]:
                    row[2] = row[1]
                    if row[1] > 0:
                        self.add(row[1])
                self.tally_i = len(self.tally)
                self.app.audio.play("coin")
                return
            row = self.tally[self.tally_i]
            row[2] = min(row[1], row[2] + max(1.0, row[1] * dt / 0.4))
            if row[2] >= row[1]:
                if row[1] > 0:
                    self.add(row[1])
                    self.app.audio.play("coin")
                self.tally_i += 1
        else:
            self.tally_wait += dt
            if self.tally_wait > 1.6 or skip:
                self.finish_stage()
        self.check_life()

    def finish_stage(self):
        st = self.st
        if self.n >= STAGES:
            self.state = "over"
            self.hype.banner("ALL CLEAR!!", "EVERY KITTEN IN TOWN IS HOME", rainbow=True, dur=5.0, sound="jackpot")
            self.hype.shower(120, "confetti")
            self.hype.shower(40, "hearts")
            self.end_game(True, "ALL 200 STAGES!", delay=4.5)
            return
        self.next_n = self.n + 1
        if st["kind"] in ("boss", "bonus"):
            self.picks_left = 1
            self.pick_title = "BOSS BONUS!" if st["kind"] == "boss" else "TREAT TIME!"
            self.state = "pick"
        else:
            self.start_stage(self.next_n)

    # ---------------------------------------------------------------- drawing
    def make_bg(self):
        th = self.theme
        s = pygame.Surface((W, H))
        s.fill(col("black"))
        focus = th[10]
        for r in range(ROWS):
            ln = self.lanes[r]
            y0 = TOP + r * CELL
            t = ln["t"]
            if t == "home":
                s.fill(col(th[8]), (0, y0, W, CELL))
                for yy in range(0, CELL, 4):
                    off = 0 if (yy // 4) % 2 == 0 else 8
                    s.fill(col("black"), (0, y0 + yy, W, 1))
                    for xx in range(off, W, 16):
                        s.fill(col("black"), (xx, y0 + yy, 1, 4))
                s.fill(col(th[9]), (0, y0 + CELL - 2, W, 2))
            elif t in ("safe", "start"):
                self.draw_ground(s, y0, th, focus, r)
            elif t == "road":
                s.fill(col(th[3]), (0, y0, W, CELL))
                above = self.lanes[r - 1]["t"]
                if above == "road":
                    for xx in range(0, W, 16):
                        s.fill(col(th[4]), (xx + 2, y0, 8, 1))
                else:
                    s.fill(col("gray"), (0, y0, W, 1))
                if self.lanes[r + 1]["t"] != "road":
                    s.fill(col("gray"), (0, y0 + CELL - 1, W, 1))
                for xx in range(r * 7 % 13, W, 23):
                    s.fill(col("black"), (xx, y0 + 5 + (xx // 23) % 7, 1, 1))
            elif t == "water":
                s.fill(col(th[5]), (0, y0, W, CELL))
                if self.lanes[r - 1]["t"] != "water":
                    s.fill(col("choco"), (0, y0, W, 2))
                if self.lanes[r + 1]["t"] != "water":
                    s.fill(col("choco"), (0, y0 + CELL - 1, W, 1))
            elif t == "gap":
                s.fill(col(th[7]), (0, y0, W, CELL))
                for i in range(12):
                    lx = (i * 53 + r * 29) % W
                    ly = y0 + 4 + (i * 7 + r) % 10
                    s.fill(col("yellow" if i % 3 else "lavender"), (lx, ly, 1, 1))
                s.fill(col("black"), (0, y0, W, 1))
                s.fill(col("gray"), (0, y0 + 2, W, 1))      # the washing line
            elif t == "rail":
                s.fill(col("darkgray"), (0, y0, W, CELL))
                for xx in range(0, W, 7):
                    s.fill(col("brown"), (xx, y0 + 2, 3, 12))
                s.fill(col("gray"), (0, y0 + 4, W, 1))
                s.fill(col("gray"), (0, y0 + 11, W, 1))
            elif t == "fence":
                self.draw_ground(s, y0, th, focus, r)
                for c in range(COLS):
                    if c in ln["gc"]:
                        continue
                    x = c * CELL
                    s.fill(col("black"), (x, y0 + 2, CELL, 13))
                    s.fill(col("choco"), (x, y0 + 4, CELL, 2))
                    s.fill(col("choco"), (x, y0 + 10, CELL, 2))
                    for px in (x + 1, x + 6, x + 11):
                        s.fill(col("brown"), (px, y0 + 2, 4, 13))
                        s.fill(col("peach"), (px, y0 + 2, 4, 1))
            elif t == "belt":
                s.fill(col("darkgray"), (0, y0, W, CELL))
                s.fill(col("gray"), (0, y0 + 1, W, 1))
                s.fill(col("gray"), (0, y0 + CELL - 2, W, 1))
            # sidewalk props
            for c in ln["bl"]:
                art.draw_block(s, c * CELL, y0, (c + r + self.n) % 4 if focus != "G" else (0 if c % 2 else 2), 0.0)
        for m in self.mh:
            art.draw_manhole(s, m[1] * CELL, TOP + m[0] * CELL, 0.0)
            x, y0 = m[3] * CELL, TOP + m[2] * CELL
            pygame.draw.ellipse(s, col("black"), (x + 1, y0 + 4, 14, 10))
            pygame.draw.ellipse(s, col("lime"), (x + 3, y0 + 6, 10, 6), 1)
        if self.st["dark"]:
            for lx, ly, rad, ph in self.st["lamps"]:
                s.fill(col("black"), (lx - 1, ly - 2, 3, 12))
                s.fill(col("gray"), (lx, ly - 1, 1, 10))
        return s

    def draw_ground(self, s, y0, th, focus, r):
        s.fill(col(th[1]), (0, y0, W, CELL))
        c2 = col(th[2])
        if focus == "G":          # roof tiles
            for yy in (y0 + 5, y0 + 11):
                s.fill(c2, (0, yy, W, 1))
                for xx in range((yy // 6) % 2 * 4, W, 8):
                    s.fill(c2, (xx, yy - 4, 1, 4))
        elif focus == "W":        # dock planks
            for yy in (y0 + 4, y0 + 9, y0 + 14):
                s.fill(c2, (0, yy, W, 1))
            for xx in range((r * 11) % 40, W, 40):
                s.fill(c2, (xx, y0 + 4, 1, 10))
        elif focus in ("T", "F"):   # cobbles
            for yy in range(y0 + 2, y0 + CELL, 5):
                for xx in range((yy // 5) % 2 * 3, W, 6):
                    s.fill(c2, (xx, yy, 2, 1))
        else:                     # sidewalk slabs
            for xx in range(0, W, 16):
                s.fill(c2, (xx, y0, 1, CELL))
            s.fill(c2, (0, y0 + 8, W, 1))
        acc = col(th[9])
        for i in range(3):
            xx = (r * 37 + i * 101 + self.n * 13) % W
            s.fill(acc, (xx, y0 + 3 + i * 4, 2, 1))

    def render(self, s):
        t = self.t
        lt = self.lt
        s.blit(self.bg, (0, 0))
        th = self.theme
        # animated lane bits + traffic / floaters
        for r in range(ROWS):
            ln = self.lanes[r]
            y0 = TOP + r * CELL
            typ = ln["t"]
            if typ == "water":
                for i in range(10):
                    wx = int(pmod(i * 37 + r * 11 + lane_shift(ln, lt) * 0.5, W + 20)) - 10
                    s.fill(col(th[6]), (wx, y0 + 5 + (i * 5) % 8, 5, 1))
            elif typ == "belt":
                off = int(pmod(lane_shift(ln, lt), 16))
                for xx in range(-16, W + 16, 16):
                    x = xx + off
                    d = 1 if ln["v"] > 0 else -1
                    pygame.draw.polygon(s, col("gray"), [(x, y0 + 5), (x + 3 * d, y0 + 8), (x, y0 + 11)])
            elif typ == "gap" and not ln["sw"]:
                off = int(pmod(lane_shift(ln, lt), 12))
                for xx in range(-12, W + 12, 12):
                    s.fill(col("white"), (xx + off, y0 + 2, 1, 1))
            for c in ln["pd"]:
                art.draw_puddle(s, c * CELL, y0, t)
            if typ in ("road", "water", "gap", "belt"):
                sh = lane_shift(ln, lt)
                d = 1 if ln["v"] >= 0 else -1
                if ln["sw"]:
                    d = 1 if math.cos(ln["om"] * lt + ln["ph"]) >= 0 else -1
                for i, (kind, ix, w) in enumerate(ln["it"]):
                    X = item_sx(ln, ix, sh)
                    if X > W + 2 or X + w < -2:
                        continue
                    Xi = int(X)
                    if kind in art.TRAFFIC:
                        art.draw_traffic(s, kind, Xi, y0, d, t, i + r)
                    elif kind == "crate":
                        art.draw_crate(s, Xi, y0, w, t)
                    elif kind == "duck":
                        art.draw_ducks(s, Xi, y0, w, d, t, ("up", "tell", "down")[dive_state(ln, i, lt)])
                    elif kind == "fish":
                        art.draw_fish(s, Xi, y0, w, d, t, ("up", "tell", "down")[dive_state(ln, i, lt)])
                    elif kind == "sheet":
                        art.draw_sheet(s, Xi, y0, w, t, i + r)
                    elif kind == "tray":
                        art.draw_tray(s, Xi, y0, t, i)
            elif typ == "fence":
                opn = gate_open(ln, lt)
                warn = gate_warn(ln, lt)
                for c in ln["gc"]:
                    art.draw_gate(s, c * CELL, y0, t, opn, warn)
            elif typ == "rail":
                warn, x0, x1 = train_span(ln, lt)
                art.draw_signal(s, 2, y0, t, warn)
                art.draw_signal(s, W - 8, y0, t, warn)
        for (r, c), v in self.wet_cells.items():
            art.draw_puddle(s, c * CELL, TOP + r * CELL, t)
        # boxes
        for i, c in enumerate(self.boxes):
            closed = not self.lid_open(i) or bool(self.boss)
            glow = bool(self.line) and not closed and int(t * 3) % 2 == 0
            art.draw_box(s, c * CELL, TOP, self.box_n[i], t, closed, self.lid_warn(i), glow)
        # treats
        for it in self.items:
            if not it.alive or (0 < it.life < 1.5 and int(t * 10) % 2):
                continue
            x = self.pattern_wx(it.row, it.x) if it.carrier else it.x
            if -8 < x < W + 8:
                art.draw_item(s, it.kind, x, cy(it.row), t)
        # waiting kittens
        for k in self.kittens:
            if k.state == "wait":
                x = self.kitten_wx(k)
                if -8 < x < W + 8:
                    mood = "wow" if self.line and abs(k.home_r - self.sushi.row) <= 1 else ""
                    art.draw_kitten(s, x, cy(k.home_r) + 6, k.coat, t, mood, seed=k.idx)
                    if int(t * 2 + k.idx) % 4 == 0:
                        draw_text(s, "?", int(x) + 4, cy(k.home_r) - 12, "white", shadow="black")
        if self.boss:
            self.boss.draw_tells(s, t)
        # the line of kittens, then Sushi
        s_rest = not self.sushi.hopping
        for i in range(len(self.line) - 1, -1, -1):
            k = self.line[i]
            x, y = self.hx(k), self.hy(k)
            if not k.hopping and s_rest and k.row == self.sushi.row and abs(x - self.sushi_x()) < 3:
                x += (-7, 7, -11, 11, -4, 4, -9, 9)[i % 8]          # huddle around mama
                y += 1
            art.draw_kitten(s, x, y + 6, k.coat, t, "happy" if self.home_box >= 0 else "", k.p(), k.idx,
                            flash=k.flash > 0)
        if self.state not in ("dead",) or self.state_t < 0.05:
            self.draw_sushi(s, t)
        else:
            self.draw_death(s, t)
        # trains go over everything on the ground
        for r in range(ROWS):
            ln = self.lanes[r]
            if ln["t"] == "rail":
                warn, x0, x1 = train_span(ln, lt)
                if x0 is not None and x1 > -4 and x0 < W + 4:
                    d = ln["tr"][5]
                    art.draw_train(s, x1 if d > 0 else x0, TOP + r * CELL, ln["tr"][2], d, t)
        if self.boss:
            self.boss.draw(s, t)
            self.boss.draw_shots(s, t)
        for f in self.freed:
            p = min(1.0, f[4])
            x = f[0] + (f[2] - f[0]) * p
            y = f[1] + (f[3] - f[1]) * p - math.sin(math.pi * p) * 40
            art.draw_kitten(s, x, y + 6, f[5], t, "happy", 0.0, f[5])
        for g in self.ghosts:
            if int(g[2] * 12) % 2 == 0:
                art.draw_kitten(s, g[0], g[1] + 6, g[3], t, "wow")
        self.parts.draw(s)
        if self.st["dark"]:
            self.draw_dark(s, t)
        if self.st["rain"]:
            for i in range(40):
                rx = int(pmod(i * 37 + t * 60, W + 20)) - 10
                ry = int(pmod(i * 53 + t * 220, H + 20)) - 10
                s.fill(col("sky"), (rx, ry, 1, 3))
        self.floats.draw(s)
        self.draw_hud(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "tally":
            self.draw_tally(s, t)

    def draw_sushi(self, s, t):
        sh = self.sushi
        if self.home_box >= 0:
            x = self.boxes[self.home_box] * CELL
            bob = int(abs(math.sin(t * 6)) * 2)
            s.blit(sprite("ah_sushi", 5), (x, TOP - 2 - bob))
            return
        x, y = self.hx(sh), self.hy(sh)
        mood = "hurt" if self.stun > 0 else ""
        if self.state == "clear":
            mood = "happy"
        if self.zoom_t > 0:
            for i in range(1, 4):
                s.fill(col(rainbow(i, t)), (int(x) - 6 + i * 3, int(y) + 4 + (i % 2), 2, 2))
        if self.shield > 0 and int(t * 3) % 3 == 0:
            pygame.draw.rect(s, col("peach"), (int(x) - 9, int(y) - 10, 18, 19), 1, border_radius=3)
        art.draw_sushi(s, int(x) - 8, int(y) - 9, t, sh.face, mood, sh.p(), flash=self.inv > 0)
        if self.wet and int(t * 6) % 2:
            s.fill(col("sky"), (int(x) - 6, int(y) - 10, 1, 2))
            s.fill(col("sky"), (int(x) + 6, int(y) - 8, 1, 2))
        if self.stun > 0:
            for i in range(3):
                a = t * 8 + i * 2.1
                s.fill(col("yellow"), (int(x) + int(math.cos(a) * 7), int(y) - 12 + int(math.sin(a) * 2), 1, 1))

    def draw_death(self, s, t):
        x, y = int(self.dead_x), int(self.dead_y)
        p = min(1.0, self.state_t / 1.0)
        if self.death in ("splash", "fall"):
            if self.death == "splash":
                for i in range(3):
                    rr = int(4 + p * 14 + i * 4)
                    pygame.draw.ellipse(s, col("white" if i == 0 else "sky"), (x - rr, y + 2 - rr // 4, rr * 2, rr // 2 + 2), 1)
                if p < 0.4:
                    art.draw_sushi(s, x - 8, y - 9 + int(p * 20), t, "down", "hurt")
            else:
                if p < 0.8:
                    sp = sprite("ah_sushi", 6)
                    k = max(1, int(16 * (1 - p)))
                    small = pygame.transform.scale(sp, (k, k))
                    s.blit(small, (x - k // 2, y - k // 2 + int(p * 10)))
            return
        jump = int(math.sin(math.pi * min(1.0, p * 1.4)) * 18)
        art.draw_sushi(s, x - 8, y - 9 - jump, t, "down", "hurt")
        for i in range(4):
            a = t * 9 + i * 1.6
            s.fill(col("yellow"), (x + int(math.cos(a) * 10), y - 16 - jump + int(math.sin(a) * 3), 2, 2))

    def draw_dark(self, s, t):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((8, 6, 20, 175))
        lights = []
        for lx, ly, rad, ph in self.st["lamps"]:
            if not (pmod(t * 0.9 + ph, 4.0) > 3.3 and int(t * 15) % 2 == 0):
                lights.append((lx, ly + 6, rad))
        if self.home_box < 0:
            lights.append((int(self.sushi_x()), int(self.hy(self.sushi)), 30))
        for k in self.line:
            lights.append((int(self.hx(k)), int(self.hy(k)), 12))
        heads = []
        for r in range(ROWS):
            ln = self.lanes[r]
            if ln["t"] == "road":
                d = 1 if ln["v"] >= 0 else -1
                for kind, X, w, _ in self.vehicles(r):
                    if -50 < X < W + 50:
                        hx = art.headlight(kind, X, d)
                        lights.append((int(hx), cy(r), 14))
                        heads.append((int(X + w - 1 if d > 0 else X), cy(r)))
            elif ln["t"] == "rail":
                warn, x0, x1 = train_span(ln, self.lt)
                if x0 is not None:
                    fx = x1 + 10 if ln["tr"][5] > 0 else x0 - 10
                    lights.append((int(fx), cy(r), 26))
        if self.boss and self.boss.state != "dead":
            lights.append((int(self.boss.x), int(self.boss.y), 24))
        for x, y, rad in lights:
            ov.blit(light_sprite(rad), (x - rad, y - rad), special_flags=pygame.BLEND_RGBA_SUB)
        s.blit(ov, (0, 0))
        for x, y in heads:
            s.fill(col("yellow"), (x, y - 1, 1, 2))
        for lx, ly, rad, ph in self.st["lamps"]:
            if not (pmod(t * 0.9 + ph, 4.0) > 3.3 and int(t * 15) % 2 == 0):
                s.fill(col("yellow"), (lx - 1, ly - 3, 3, 2))

    def draw_hud(self, s, t):
        s.fill(col("black"), (0, 0, W, TOP))
        draw_text(s, f"{self.score:07d}", 3, 3, "white", shadow=None)
        if self.boss and self.boss.state != "dead":
            boss_bar(s, self.boss.name, self.boss.hp, self.boss.maxhp, t, y=0, x=50, w=200)
        else:
            draw_text(s, f"HI {max(self.best, self.score):07d}", 52, 3, "gray", shadow=None)
            draw_text(s, f"STAGE {self.n}", 196, 3, "yellow", align="center", shadow=None)
        self.hearts(s, W - 50, 2, self.lives)
        # bottom bar: kittens, clock, power-ups, fever
        y = H - 12
        s.fill(col("black"), (0, y, W, 12))
        n = self.need
        x = 3
        if self.st["kind"] == "bonus" and self.st["bonus"] == "feast":
            s.blit(sprite("ah_fish"), (x, y + 2))
            draw_text(s, f"X{self.fish_n}", x + 12, y + 3, "sky", shadow=None)
            x += 40
        else:
            show = min(n, 12)
            for i in range(show):
                kx = x + i * 9
                if i < self.home_count:
                    c = ("orange", "gray", "darkgray", "cream", "white", "peach")[i % 6]
                    s.fill(col(c), (kx, y + 4, 7, 5))
                    s.fill(col(c), (kx, y + 2, 2, 2))
                    s.fill(col(c), (kx + 5, y + 2, 2, 2))
                    s.fill(col("black"), (kx + 2, y + 5, 1, 1))
                    s.fill(col("black"), (kx + 4, y + 5, 1, 1))
                else:
                    in_line = i < self.home_count + len(self.line)
                    c = "pink" if in_line and int(t * 6) % 2 else "darkgray"
                    pygame.draw.rect(s, col(c), (kx, y + 2, 7, 7), 1)
            if n > show:
                draw_text(s, f"+{n - show}", x + show * 9 + 1, y + 3, "pink", shadow=None)
            x += min(n, 12) * 9 + (14 if n > 12 else 4)
        if not self.boss:
            secs = max(0, int(math.ceil(self.clock)))
            low = secs <= 10
            draw_text(s, f"{secs:02d}", x + 2, y + 3, ("red" if int(t * 6) % 2 else "yellow") if low else "white",
                      shadow=None)
            bw = 50
            s.fill(col("darkgray"), (x + 18, y + 5, bw, 3))
            s.fill(col("red" if low else "sky"), (x + 18, y + 5, int(bw * max(0.0, min(1.0, self.clock / max(1.0, self.clock_full)))), 3))
            x += 74
        # power-ups
        icons = []
        if self.zoom_t > 0:
            icons.append(("ah_nip", self.zoom_t))
        if self.slow_t > 0:
            icons.append(("ah_bell", self.slow_t))
        for name, v in icons:
            if v > 1.5 or int(t * 8) % 2:
                s.blit(sprite(name), (x, y + 2))
            x += 11
        for i in range(self.shield):
            s.blit(sprite("ah_boxitem"), (x, y + 3))
            x += 10
        for i in range(self.bells):
            s.fill(col("yellow"), (x + 1, y + 4, 3, 4))
            x += 6
        for i in range(self.swims):
            s.fill(col("teal"), (x, y + 6, 5, 2))
            x += 7
        if self.lv("pounce"):
            ready = self.pounce_cd <= 0
            c = col("orange" if ready else "darkgray")      # a little leap arc
            pygame.draw.line(s, c, (x, y + 9), (x + 3, y + 3))
            pygame.draw.line(s, c, (x + 3, y + 3), (x + 6, y + 9))
            if not ready:
                full = (4.0, 4.0, 3.0, 2.0)[min(3, self.lv("pounce"))]
                s.fill(col("orange"), (x, y + 10, int(7 * (1 - self.pounce_cd / full)), 1))
            x += 9
        if not self.hype.fever_on:          # (during FEVER the kit shows its own label here)
            x0, y0 = W - 52, y + 4
            s.fill(col("darkgray"), (x0, y0, 48, 3))
            s.fill(col("orange"), (x0, y0, int(48 * self.hype.fever), 3))

    def draw_intro(self, s, t):
        st = self.st
        k = st["kind"]
        if k == "boss":
            b = st["boss"]
            if int(t * 4) % 2:
                for x in range(-20, W + 20, 20):
                    pygame.draw.polygon(s, col("red"), [(x, 96), (x + 10, 96), (x + 20, 104), (x + 10, 104)])
                    pygame.draw.polygon(s, col("red"), [(x, 152), (x + 10, 152), (x + 20, 160), (x + 10, 160)])
            panel(s, (30, 108, 260, 40), fill="black", border="red")
            draw_text(s, "WARNING!!", W // 2, 112, "red" if int(t * 6) % 2 else "yellow", 2, align="center",
                      outline="ink")
            draw_text(s, f"{b['name']} - {b['title']}", W // 2, 129, "white", align="center", shadow=None)
            draw_text(s, b["hint"], W // 2, 138, "lime", align="center", shadow=None)
            return
        h = 64 if st["new"] else 54
        y0 = 92
        panel(s, (24, y0, 272, h), fill="ink", border="yellow" if k == "bonus" else th_border(self.theme))
        bob = int(abs(math.sin(t * 5)) * 2)
        s.blit(sprite("ah_sushi", 5, scale=2), (32, y0 + 10 - bob))
        cx = 176
        if k == "bonus":
            title = "BONUS STAGE"
            for i, ch in enumerate(title):
                draw_text(s, ch, cx - text_width(title, 2) // 2 + i * 12, y0 + 6 + int(math.sin(t * 8 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            sub = "GRAB ALL THE TREATS YOU CAN!" if st["bonus"] == "feast" else "HUGE FAMILIES = HUGE POINTS!"
            draw_text(s, st["name"], cx, y0 + 26, "yellow", align="center")
            draw_text(s, sub, cx, y0 + 37, "white", align="center", shadow=None)
            return
        draw_text(s, f"STAGE {self.n}", cx, y0 + 6, "yellow", 2, align="center", outline="ink", shadow=None)
        draw_text(s, f"{self.theme[0]} - {st['name']}", cx, y0 + 24, "lavender", align="center", shadow=None)
        draw_text(s, f"BRING {self.need} KITTENS HOME!", cx, y0 + 34, "white", align="center", shadow=None)
        draw_text(s, f"\"{st['line']}\"", cx, y0 + 44, "peach", align="center", shadow=None)
        if st["new"]:
            draw_text(s, st["new"], cx, y0 + 54, "mint" if int(t * 4) % 2 else "lime", align="center", shadow=None)

    def draw_tally(self, s, t):
        rows = self.tally
        h = 40 + len(rows) * 11
        y0 = 70
        panel(s, (48, y0, 224, h), fill="ink", border="mint")
        head = {"boss": "BOSS CLEAR!", "bonus": "BONUS OVER!"}.get(self.st["kind"], f"STAGE {self.n} CLEAR!")
        draw_text(s, head, W // 2, y0 + 6, "mint", align="center")
        for i, (label, v, shown) in enumerate(rows):
            if i > self.tally_i:
                break
            y = y0 + 20 + i * 11
            draw_text(s, label, 58, y, "white" if v else "gray", shadow=None)
            draw_text(s, f"{int(shown)}", 262, y, "yellow" if v else "darkgray", align="right", shadow=None)
        quip = "PURRFECT! EVERYONE IS HOME!" if not self.missed and not self.lost_any else \
            "PHEW... HOME SWEET HOME!" if self.missed else "WE MADE IT, LITTLE ONES!"
        if self.st["kind"] == "boss":
            quip = "AND STAY OUT OF MY ALLEY!"
        elif self.st["kind"] == "bonus":
            quip = "YUM! WHAT A NIGHT!"
        draw_text(s, quip, W // 2, y0 + h - 22, "peach", align="center", shadow=None)
        if self.tally_i >= len(rows) and int(t * 3) % 2:
            draw_text(s, "PRESS Z", W // 2, y0 + h - 11, "lavender", align="center", shadow=None)


def th_border(th):
    return th[9]


_light_cache = {}


def light_sprite(rad):
    """Banded light pool: alpha to subtract from the darkness (same formula on iOS)."""
    s = _light_cache.get(rad)
    if s is None:
        s = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        r2 = rad * rad
        for yy in range(rad * 2):
            for xx in range(rad * 2):
                d2 = (xx - rad) ** 2 + (yy - rad) ** 2
                a = light_alpha(d2, r2)
                if a:
                    s.set_at((xx, yy), (0, 0, 0, a))
        _light_cache[rad] = s
    return s


def light_alpha(d2, r2):
    if d2 < r2 * 0.3:
        return 175
    if d2 < r2 * 0.6:
        return 120
    if d2 < r2:
        return 60
    return 0


# ----------------------------------------------------------------------------- autopilot (GIF recorder + tests)
def autopilot(sc):
    """A careful crosser for the GIF recorder and the tests: a two-hop search over the predicted lanes (every lane
    is a pure function of time), scored by grid distance to the next kitten / box."""
    keys = set()
    if sc.overlay is not None:
        if int(sc.t * 60) % 20 < 2:
            keys.add("a")
        return keys
    if sc.state in ("intro", "tally"):
        if int(sc.t * 60) % 30 < 2:
            keys.add("a")
        return keys
    if sc.state != "play" or sc.home_box >= 0:
        return keys
    s = sc.sushi
    if s.hopping or sc.stun > 0:
        return keys
    m = sc.tmul * (0.35 if sc.slow_t > 0 else 1.0)
    hop = (sc.hop_time() + 0.03) * m
    tail = (0.12 + KDELAY * len(sc.line)) * m
    goal = bot_goal(sc)

    def drift(r, x, t0, t1):
        ln = sc.lanes[r]
        if ln["t"] not in CARRIERS:
            return x
        return x + lane_shift(ln, t1) - lane_shift(ln, t0)

    def span_safe(r, x, t0, t1):
        """(r, x at t0) stays safe from t0 to t1, riding the lane if it is a carrier."""
        tt = t0
        while True:
            if not cell_ok(sc, r, drift(r, x, t0, tt), tt):
                return False
            if tt >= t1:
                return True
            tt = min(t1, tt + 0.05)

    def options(r, x, t):
        out = []
        wait = 0.25 * m
        if span_safe(r, x, t, t + wait + tail):
            out.append((None, r, drift(r, x, t, t + wait), t + wait))
        if not span_safe(r, x, t, t + hop * 0.5 + tail):
            return out
        for d in ("up", "left", "right", "down"):
            dr, dc = DIRS[d]
            ok, tx = bot_can_enter(sc, r + dr, x + dc * CELL, t + hop * 0.5)
            if not ok:
                continue
            r2 = r + dr
            if r2 == 0:
                out.append((d, r2, tx, t + hop))
                continue
            if span_safe(r2, tx, t + hop * 0.4, t + hop + 0.05):
                out.append((d, r2, tx, t + hop))
        return out

    t0 = sc.lt
    r0, x0 = s.row, sc.sushi_x()
    # no progress towards the goal for a while: try another kitten / box
    here = bot_dist(sc, goal[0], max(0, min(COLS - 1, int(goal[1] // CELL)))).get((r0, int(x0 // CELL)), 99)
    memo = sc.__dict__.setdefault("_bot_prog", [99, sc.pt])
    if here < memo[0]:
        memo[0], memo[1] = here, sc.pt
    elif sc.pt - memo[1] > 5.0:
        memo[0], memo[1] = 99, sc.pt
        sc._bot_rot = sc.__dict__.get("_bot_rot", 0) + 1
        sc._bot_box = None
    best = None
    for d1, r1, x1, t1 in options(r0, x0, t0):
        val = None
        first = bot_score(sc, r1, x1, goal)
        if r1 == 0:
            val = first * 1.5 + 5
        else:
            for d2, r2, x2, t2 in options(r1, x1, t1):
                if r2 != 0 and not span_safe(r2, x2, t2, t2 + 0.3 * m + tail) and not options(r2, x2, t2):
                    continue
                v = bot_score(sc, r2, x2, goal) - 2 * (t2 - t0)
                if val is None or v > val:
                    val = v
            if val is None and span_safe(r1, x1, t1, t1 + 0.6 * m + tail):
                val = first - 8
            if val is not None:
                val += 0.5 * first
        if val is None:
            continue
        if best is None or val > best[0]:
            best = (val, d1)
    if best is None:
        # nothing is safe: pick the least scary hop
        for d in ("up", "left", "right", "down"):
            dr, dc = DIRS[d]
            ok, tx = sc.can_enter(r0 + dr, x0 + dc * CELL)
            if ok and cell_ok(sc, r0 + dr, tx, t0 + hop):
                keys.add(d)
                break
        return keys
    if best[1]:
        keys.add(best[1])
    return keys


def bot_can_enter(sc, tr, tx, lt):
    """can_enter for a future lane time (gates and lids move)."""
    if tr < 0 or tr >= ROWS or tx < 4 or tx > W - 4:
        return False, tx
    ln = sc.lanes[tr]
    if tr == 0:
        if sc.boss:
            return False, tx
        for i, c in enumerate(sc.boxes):
            bx = c * CELL + 8
            if abs(bx - tx) <= 9:
                if not sc.st["lids"]:
                    return True, float(bx)
                cyc, opn = sc.st["lids"]
                if pmod(lt + i * 1.3, cyc) < opn - 0.2:
                    return True, float(bx)
        return False, tx
    if ln["t"] not in CARRIERS:
        c = max(0, min(COLS - 1, int(tx // CELL)))
        tx = float(c * CELL + 8)
        if c in ln["bl"]:
            return False, tx
        if ln["t"] == "fence" and (c not in ln["gc"] or not gate_open(ln, lt)):
            return False, tx
    return True, tx


def cell_ok(sc, r, x, lt):
    ln = sc.lanes[r]
    t = ln["t"]
    if t == "road":
        sh = lane_shift(ln, lt)
        for i, (kind, ix, w) in enumerate(ln["it"]):
            X = item_sx(ln, ix, sh)
            if X - 1 < x + 6 and X + w + 1 > x - 6:
                return False
    elif t == "rail":
        warn, x0, x1 = train_span(ln, lt)
        if warn and (x0 is None or (x0 - 30 < x + 8 and x1 + 30 > x - 8)):
            return False
    elif t == "fence":
        cyc, opn, ph = ln["gt"]
        if pmod(lt + ph, cyc) > opn - 0.3:
            return False
    elif t in ("water", "gap"):
        if x < 5 or x > W - 5:
            return False
        sh = lane_shift(ln, lt)
        u = pmod(x + pad_of(ln) - sh, ln["p"])
        if not any(ix + 3 <= u <= ix + w - 3 and dive_state(ln, i, lt) == 0 for i, (_, ix, w) in enumerate(ln["it"])):
            return False
    if sc.boss and sc.boss.hurts(x, cy(r), 9):
        return False
    return True


def bot_goal(sc):
    """(row, x) the bot wants to reach. When it makes no progress for a while it rotates to another target."""
    s = sc.sushi
    rot = sc.__dict__.get("_bot_rot", 0)
    if sc.boss:
        b = sc.boss
        if b.vulnerable():
            return int((b.hy - TOP) // CELL), b.hx
        return (6 + rot % 3), 160.0
    waiting = [k for k in sc.kittens if k.state == "wait"]
    if waiting and (len(sc.line) < 2 or sc.st["kind"] == "bonus" and len(sc.line) < 8):
        waiting.sort(key=lambda k: abs(k.home_r - s.row) * 20 + abs(sc.kitten_wx(k) - sc.sushi_x()))
        k = waiting[rot % len(waiting)]
        gx = sc.kitten_wx(k)
        if k.carrier and (s.row != k.home_r + 1 or abs(gx - sc.sushi_x()) > 8) and k.home_r < 10:
            return k.home_r + 1, gx           # riding kittens are reached from the lane below
        return k.home_r, gx
    if sc.st["kind"] == "bonus" and sc.st["bonus"] == "feast":
        its = [it for it in sc.items if it.alive]
        if its:
            it = min(its, key=lambda it: abs(it.row - s.row) * 20 + abs((sc.pattern_wx(it.row, it.x) if it.carrier else it.x) - sc.sushi_x()))
            return it.row, sc.pattern_wx(it.row, it.x) if it.carrier else it.x
    # pick a box once per trip (so the bot does not dither between two of them)
    memo = sc.__dict__.get("_bot_box")
    if memo and memo[0] is s:
        return 0, sc.boxes[memo[1]] * CELL + 8.0
    here = (s.row, max(0, min(COLS - 1, int(sc.sushi_x() // CELL))))
    order = sorted(range(len(sc.boxes)),
                   key=lambda i: bot_dist(sc, 0, sc.boxes[i]).get(here, 99) * 16 + abs(sc.boxes[i] * CELL + 8 - sc.sushi_x()))
    i = order[rot % len(order)]
    sc._bot_box = (s, i)
    return 0, sc.boxes[i] * CELL + 8.0


def bot_dist(sc, gr, gc):
    """Hop distances to the goal cell over the static grid (blocks, fences and the box row stop you)."""
    key = (sc.n, gr, gc)
    cache = sc.__dict__.setdefault("_bot_cache", {})
    if key in cache:
        return cache[key]
    lanes = sc.lanes

    def passable(r, c):
        if r == 0:
            return c in sc.boxes and gr == 0
        ln = lanes[r]
        if c in ln["bl"]:
            return False
        if ln["t"] in ("water", "gap") and (c == 0 or c == COLS - 1):
            return False            # riding along the very edge ends in a splash
        return ln["t"] != "fence" or c in ln["gc"]
    dist = {(gr, gc): 0}
    todo = [(gr, gc)]
    while todo:
        nxt = []
        for r, c in todo:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < ROWS and 0 <= cc < COLS and (rr, cc) not in dist and passable(rr, cc):
                    dist[(rr, cc)] = dist[(r, c)] + 1
                    nxt.append((rr, cc))
        todo = nxt
    if len(cache) > 200:
        cache.clear()
    cache[key] = dist
    return dist


def bot_score(sc, r, x, goal):
    gr, gx = goal
    gc = max(0, min(COLS - 1, int(gx // CELL)))
    dist = bot_dist(sc, gr, gc)
    c = max(0, min(COLS - 1, int(x // CELL)))
    lane_t = sc.lanes[r]["t"]
    risk = 4 if lane_t in ("road", "rail", "fence") else 2 if lane_t in ("water", "gap") else 0
    return -dist.get((r, c), 60) * 30 - abs(x - gx) * 0.05 - risk


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys."""
    return lambda frame: autopilot(scene) if frame % 2 == 0 else set()


# ----------------------------------------------------------------------------- carousel preview
def preview(s, t):
    """Carousel thumbnail: Sushi hops a little family across a road, a canal and another road into a box."""
    w, h = s.get_size()
    s.fill(col("night"))
    n = max(2, min(4, (h - 10) // 16))
    kinds = ["safe", "road", "water", "road"][:n]
    base = h - 16 * n
    for i, kind in enumerate(kinds):
        y0 = h - 16 * (i + 1)
        if kind == "safe":
            s.fill(col("darkgray"), (0, y0, w, 16))
            for xx in range(0, w, 16):
                s.fill(col("gray"), (xx, y0, 1, 16))
            s.fill(col("gray"), (0, y0 + 8, w, 1))
        elif kind == "road":
            s.fill(col("ink"), (0, y0, w, 16))
            d = 1 if i == 1 else -1
            for k in range(3):
                X = int(pmod(k * 46 + d * t * 30 + i * 20, w + 40)) - 30
                if k % 2:
                    art.draw_bike(s, X, y0, d, t)
                else:
                    art.draw_scooter(s, X, y0, d, t)
        else:
            s.fill(col("blue"), (0, y0, w, 16))
            X = int(pmod(t * 16, w + 60)) - 52
            art.draw_crate(s, X, y0, 48, t)
            art.draw_crate(s, X - 80, y0, 32, t)
    s.fill(col("brown"), (0, 0, w, base))
    s.fill(col("orange"), (0, base - 2, w, 2))
    for bx in range(w // 2 - 40, w, 40):
        art.draw_box(s, bx - 8, base - 15, 1 if bx < w // 2 else 0, t)
    # hop, hop, hop... into the box
    T = 0.55
    steps = n + 3
    k = int(t / T) % steps
    p = (t / T) % 1.0
    hop = min(1.0, p / 0.35)

    def spot(idx):
        idx = max(0, min(n, idx))
        return h - 16 * idx - 8 if idx < n else base - 6
    cx = w // 2
    for j in (2, 1):
        kk = k - j
        if kk < 0 or kk > n:
            continue
        y = spot(kk) + (spot(kk + 1) - spot(kk)) * hop if kk < n else spot(n)
        art.draw_kitten(s, cx + (j * 2 - 3) * 3, y + 6, j, t, "happy" if kk >= n else "", hop if kk < n else 0.0, j)
    if k <= n:
        y = spot(k) + (spot(k + 1) - spot(k)) * hop if k < n else spot(n)
        art.draw_sushi(s, cx - 8, int(y) - 9, t, "up", "happy" if k >= n else "", hop if k < n else 0.0)
