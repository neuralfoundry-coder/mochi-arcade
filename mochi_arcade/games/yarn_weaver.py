"""YARN WEAVER - KUMO the fluffy gray kitten unspools yarn across the rug to fence it off and claim it,
revealing a hidden cat picture underneath (an original area-capture game for MOCHI ARCADE's CAT CORNER).

Rules: walk along the yarn edges; push into the open rug to weave a loose line; reach yarn again to close it.
The rug always keeps its biggest piece - every smaller pocket is claimed, together with anything inside it
(wrap hazards for big points). Static fluff snaps loose yarn, zips run along the edges, moths nibble yarn,
a dog's nose sniffs under the rug. Hold A for a CAREFUL weave: half speed, double points.

200 stages in 20 rooms (yarn_weaver_stages.py), a boss on every 10th (yarn_weaver_boss.py), a bonus stage on
every x5, upgrade cards after bosses and bonuses. The iOS port mirrors this file (Games/YarnWeaver*.swift).
"""
import math
import random

import pygame

from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow
from mochi_arcade.games import DIFF
from mochi_arcade.games import yarn_weaver_art as A
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.games.yarn_weaver_boss import Boss
from mochi_arcade.games.yarn_weaver_stages import CAMPAIGN, GH, GW, THEMES, apply_shapes, base_grid, open_regions
from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

HOWTO = ["ARROWS      WALK THE YARN / WEAVE INTO RUG",
         "Z / SPACE   HOLD: CAREFUL WEAVE (X2 POINTS)",
         "",
         "CLOSE A LOOP TO CLAIM THE RUG AND REVEAL",
         "THE HIDDEN CAT. CLAIM THE TARGET % TO WIN!",
         "FLUFF SNAPS LOOSE YARN, ZIPS RUN THE EDGES.",
         "WRAP HAZARDS INSIDE SMALL POCKETS = BONUS!",
         "BOSS EVERY 10TH, BONUS ON X5, UPGRADES.",
         "ENTER / ESC  PAUSE"]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["left", "right", "up", "down", "a"]
EXPORT = {"stages": CAMPAIGN, "themes": [list(t) for t in THEMES]}

FX, FY = 8, 20
PW, PH = A.PW, A.PH
OPEN, CLAIMED, TRAIL = 0, 1, 2
DIRS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
DIR_ORDER = ("left", "right", "up", "down")
LIFE_AT = [30000, 80000, 160000, 300000]      # then every 200000
POM_COLS = ("pink", "mint", "sky", "yellow", "lavender", "peach", "lime")
SNAP_TEXT = {"fluff": "SNAP!", "zip": "ZAPPED!", "moth": "NIBBLED!", "fray": "UNRAVELLED!", "knot": "TANGLED!",
             "nose": "SNIFFED!", "storm": "STATIC!", "pellet": "PELLET!", "bolt": "ZAP!", "bark": "WOOF!",
             "boss": "BONK!", "pom": "BOING!"}
ITEM_TEXT = {"fish": "FISH TREAT!", "nip": "CATNIP RUSH!", "bell": "JINGLE! FREEZE!", "heart": "EXTRA LIFE!",
             "gold": "GOLDEN YARN!", "rainbow": "RAINBOW YARN!"}


# ----------------------------------------------------------------------------- upgrade cards
def _icon_paws(s, cx, cy, t):
    for i, dx in enumerate((-5, 3)):
        y = cy - 2 + (int(t * 8) + i) % 2 * 3
        pygame.draw.circle(s, col("pink"), (cx + dx, y), 3)
        s.fill(col("white"), (cx + dx - 1, y - 4, 1, 1))
        s.fill(col("white"), (cx + dx + 1, y - 4, 1, 1))


def _icon_knit(s, cx, cy, t):
    for i in range(-6, 7, 3):
        s.fill(col("white" if (i // 3) % 2 else "mint"), (cx + i, cy, 2, 2))
    pygame.draw.line(s, col("gray"), (cx - 6, cy - 6), (cx + 6, cy + 6), 1)


def _icon_guard(s, cx, cy, t):
    pygame.draw.polygon(s, col("sky"), [(cx - 6, cy - 6), (cx + 6, cy - 6), (cx + 6, cy), (cx, cy + 7), (cx - 6, cy)])
    s.fill(col("hotpink"), (cx - 6, cy - 1, 13, 2))


def _icon_claws(s, cx, cy, t):
    for i in range(3):
        pygame.draw.line(s, col("white"), (cx - 5 + i * 4, cy - 6), (cx - 7 + i * 4, cy + 5), 1)
    pygame.draw.circle(s, col("yellow"), (cx + 5, cy + 4), 2)


def _icon_luck(s, cx, cy, t):
    s.blit(sprite("yw_bell"), (cx - 3, cy - 4 + int(math.sin(t * 6))))


def _icon_fever(s, cx, cy, t):
    for i in range(3):
        pygame.draw.circle(s, col(rainbow(i, t)), (cx - 4 + i * 4, cy + 1 - (i % 2) * 3), 2)


def _icon_cozy(s, cx, cy, t):
    s.fill(col("hotpink"), (cx - 7, cy - 7, 5, 5))
    s.fill(col("hotpink"), (cx + 3, cy - 7, 5, 5))
    s.fill(col("hotpink"), (cx - 7, cy + 3, 5, 5))
    s.fill(col("hotpink"), (cx + 3, cy + 3, 5, 5))


def _icon_calm(s, cx, cy, t):
    A.draw_fluff(s, cx, cy, 4, t * 0.3, angry=False)


def _icon_strong(s, cx, cy, t):
    for i in range(3):
        pygame.draw.line(s, col("orange" if i == 1 else "yellow"), (cx - 6, cy - 3 + i * 3), (cx + 6, cy - 3 + i * 3), 1)
    if int(t * 6) % 2:
        s.fill(col("red"), (cx + 5, cy - 1, 2, 2))


UPGRADES = [
    Upgrade("quick", "QUICK PAWS", "KUMO MOVES|10% FASTER", "pink", _icon_paws, 3),
    Upgrade("knit", "TIGHT KNIT", "CAREFUL WEAVE|IS FASTER AND|SCORES MORE", "mint", _icon_knit, 2),
    Upgrade("guard", "STURDY YARN", "BLOCKS ONE|SNAP EVERY|STAGE PER LV", "sky", _icon_guard, 3),
    Upgrade("claws", "SHARP CLAWS", "POUNCE ON A|ZIP INSTEAD|OF GETTING HIT", "yellow", _icon_claws, 2),
    Upgrade("life", "NINE LIVES", "+1 LIFE|RIGHT NOW", "hotpink", "heart", 5),
    Upgrade("luck", "LUCKY BELL", "MORE TREATS|AND JACKPOTS", "orange", _icon_luck, 3),
    Upgrade("fever", "PURR POWER", "FEVER FILLS|FASTER AND|LASTS LONGER", "yellow", _icon_fever, 3),
    Upgrade("cozy", "COZY CORNERS", "STAGES START|WITH CLAIMED|CORNERS", "hotpink", _icon_cozy, 3),
    Upgrade("calm", "CALM ROOM", "HAZARDS|MOVE 8%|SLOWER", "lavender", _icon_calm, 3),
    Upgrade("strong", "STRONG YARN", "LOOSE YARN|FRAYS LATER|AND SLOWER", "orange", _icon_strong, 2),
]


# ----------------------------------------------------------------------------- objects
class Ball:
    """Fluff (static ball), fuzzlet (mini), pom-pom (bonus) or a boss minion: bounces around the open rug."""

    def __init__(self, x, y, r, speed, kind, color="gray"):
        a = random.uniform(0, math.tau)
        self.x, self.y, self.r, self.kind, self.color = x, y, r, kind, color
        self.speed = speed
        self.vx, self.vy = math.cos(a) * speed, math.sin(a) * speed
        self.turn = random.uniform(0.8, 2.5)
        self.zap = 0.0          # STATIC STORM charge-up
        self.born = 0.0         # harmless while popping in (respawns)
        self.stuck = 0
        self.alive = True


class Zip:
    def __init__(self, c, hunter):
        self.c, self.hunter = c, hunter
        self.dx, self.dy = (1, 0) if random.random() < 0.5 else (-1, 0)
        self.acc = 0.0
        self.born = 0.6
        self.alive = True


class Moth:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.hx, self.hy = random.uniform(60, 244), random.uniform(40, 136)
        self.t = random.uniform(0, 10)
        self.alive = True


class Item:
    def __init__(self, x, y, kind, life=12.0):
        self.x, self.y, self.kind, self.life = x, y, kind, life


# ----------------------------------------------------------------------------- the game
class YarnWeaver(GameScene):
    GW, FX, FY = GW, FX, FY

    @property
    def music(self):
        return self.song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES.get(d, 3)
        self.dspeed = SPEED.get(d, 1.0)
        self.levels = {}
        self.life_i = 0
        self.picks_left = 0
        self.pick_title = "POWER UP!"
        self.next_n = None
        self.was_fever = False
        self.last_dir = None
        self.friends = 0
        self.hype.COMBO_TIME = 5.0          # claims take a while: a longer window to chain them
        self.hype.combo_y = 23
        self._rugs = {}
        start = max(1, min(STAGES, int(opt.get("level", opt.get("start", 1)))))
        self.start_stage(start)
        if start > 10:                      # starting from a checkpoint: catch up on some upgrades first
            self.picks_left = min(8, (start - 1) // 10)
            self.pick_title = "HEAD START!"
            self.state = "pick"

    # ---------------------------------------------------------------- helpers
    def lv(self, uid):
        return self.levels.get(uid, 0)

    def factor_pts(self, pts):
        return pts * (10 + self.tier) // 10

    def score_at(self, pts, x=None, y=None, color="yellow"):
        return self.add(self.factor_pts(pts), x, y, color)

    def song(self):
        k = self.st["kind"]
        return "boss" if k == "boss" else "bonus" if k == "bonus" else self.theme[6]

    def careful_mult(self):
        return 2.0 + 0.5 * self.lv("knit")

    def kumo_speed(self, careful):
        sp = 38.0 * (1 + 0.1 * self.lv("quick"))
        if careful:
            sp *= 0.5 + 0.1 * self.lv("knit")
        if self.nip > 0:
            sp *= 1.4
        if self.hype.fever_on:
            sp *= 1.2
        return sp

    def fever_gain(self, x):
        return x * (1 + 0.35 * self.lv("fever"))

    def kumo_px(self):
        return self.kx * 2 + 1.0, self.ky * 2 + 1.0

    def percent(self):
        return 100 * self.claimed // max(1, self.claimable)

    @property
    def claimed(self):
        return self.claimable - self.open_n

    # ---------------------------------------------------------------- stages
    def start_stage(self, n):
        self.state = "setup"
        self.n = n
        st = self.st = CAMPAIGN[n - 1]
        self.tier = st["tier"]
        self.theme = THEMES[self.tier]
        self.reached(n)
        self.grid = base_grid(st["shapes"])
        self.furn = bytearray(GW * GH)
        apply_shapes(self.furn, st["shapes"])
        self.claimable = self.open_n = sum(1 for v in self.grid if v == OPEN)
        cz = self.lv("cozy")
        if cz and st["kind"] != "bonus":
            k = 3 + 4 * cz
            for x0, y0 in ((1, 1), (GW - 1 - k, 1), (1, GH - 1 - k), (GW - 1 - k, GH - 1 - k)):
                for y in range(y0, y0 + k):
                    for x in range(x0, x0 + k):
                        if self.grid[y * GW + x] == OPEN:
                            self.grid[y * GW + x] = CLAIMED
                            self.open_n -= 1
        self.trail, self.trail_slow = [], []
        self.weaving = False
        self.careful = False
        self.anchor = (GW // 2, GH - 1)
        self.kx, self.ky = GW // 2, GH - 1
        self.kacc = 0.0
        self.kprev = None
        self.kface = 1
        self.kmove_t = 0.0
        self.fray = -1.0
        self.idle = 0.0
        self.inv = self.hurt_t = self.happy_t = self.stun = 0.0
        self.freeze = self.nip = self.trail_safe = 0.0
        self.recoil = []
        self.balls, self.zips, self.moths, self.items, self.wraps, self.respawns, self.storms = [], [], [], [], [], [], []
        self.knots = [[k[0], k[1], True] for k in st["knots"]]
        self.nose = {"st": "wait", "t": st["nose"] * random.uniform(0.6, 1.0), "x": 0.0, "y": 0.0}
        self.guard = self.lv("guard")
        self.claws = self.lv("claws")
        self.hz_speed = self.dspeed * (1 - 0.08 * self.lv("calm"))
        self.item_t = st["items"] * random.uniform(0.4, 0.8)
        self.storm_t = st["storm"] * random.uniform(0.7, 1.0)
        self.stime = 0.0
        self.missed = False
        self.wrapped_n = self.stage_combo = self.claims = 0
        self.poms_total = self.poms_wrapped = self.fish_total = self.fish_got = 0
        self.bonus_left = float(st["time"])
        self.golden = st["kind"] == "normal" and self.hype.lucky(0.02 + 0.01 * self.lv("luck"))
        self.boss = None
        # hazards
        for _ in range(st["fluffs"]):
            self.spawn_ball("fluff")
        for _ in range(st["minis"]):
            self.spawn_ball("mini")
        for i in range(st["zips"]):
            self.zips.append(Zip(GW * (i + 1) // (st["zips"] + 1), i >= st["zips"] - st["hunters"]))
        for _ in range(st["moths"]):
            self.moths.append(Moth(random.choice((-6.0, PW + 6.0)), random.uniform(10, 80)))
        if st["kind"] == "bonus":
            if st["bonus"] == "poms":
                for _ in range(st["poms"]):
                    self.spawn_ball("pom")
                self.poms_total = st["poms"]
            else:
                for _ in range(st["fish"]):
                    x, y = self.find_spot(6, 40)
                    self.items.append(Item(x, y, "fish", 999.0))
                self.fish_total = st["fish"]
                self.spawn_ball("pom")
        if st["kind"] == "boss":
            self.boss = Boss(self, st["boss"])
        # pictures
        self.pic = pygame.Surface((PW, PH))
        A.draw_picture(self.pic, st["pic"], self.golden)
        rug = self._rugs.get(self.tier)
        if rug is None:
            rug = pygame.Surface((PW, PH))
            A.make_rug(rug, self.theme)
            self._rugs = {self.tier: rug}
        self.rug = rug
        self.furn_s = rug.copy()
        for sh in st["shapes"]:
            A.draw_furniture(self.furn_s, sh)
        self.field = rug.copy()
        for i in range(GW * GH):
            if self.grid[i] == CLAIMED:
                self.paint(i)
        self.reveal_list = []
        self.reveal_i = 0
        self.state = "intro"
        self.state_t = 0.0
        self.intro_len = 3.2 if self.boss else 2.6
        self.tally = []
        self.hype.combo_y = 23
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.was_fever = False
        self.app.audio.music(self.song())
        self.app.audio.play("warning" if self.boss else "stage")
        if self.boss:
            self.hype.flash("red", 0.3)

    # ---------------------------------------------------------------- the grid
    def cell_at(self, x, y):
        cx, cy = int(x) // 2, int(y) // 2
        if 0 <= cx < GW and 0 <= cy < GH:
            return cy * GW + cx
        return -1

    def blocked(self, x, y):
        c = self.cell_at(x, y)
        return c < 0 or self.grid[c] != OPEN

    def is_edge(self, i):
        g = self.grid
        if g[i] != CLAIMED:
            return False
        x, y = i % GW, i // GW
        for yy in (y - 1, y, y + 1):
            if 0 <= yy < GH:
                for xx in (x - 1, x, x + 1):
                    if 0 <= xx < GW and g[yy * GW + xx] != CLAIMED:
                        return True
        return False

    def yarn_col(self, x, y):
        return self.theme[4] if ((x + y) // 2) % 2 == 0 else self.theme[5]

    def paint(self, i):
        x, y = i % GW, i // GW
        r = (x * 2, y * 2, 2, 2)
        if self.grid[i] != CLAIMED:
            self.field.blit(self.rug, r[:2], r)
        elif self.is_edge(i):
            self.field.fill(col(self.yarn_col(x, y)), r)
        elif self.furn[i]:
            self.field.blit(self.furn_s, r[:2], r)
        else:
            self.field.blit(self.pic, r[:2], r)

    def find_spot(self, r, far, avoid=None):
        """A random open spot with r pixels of clear rug around it, at least `far` px from KUMO (or avoid)."""
        ax, ay = avoid if avoid else self.kumo_px()
        best = None
        for k in range(300):
            x, y = random.uniform(r + 3, PW - r - 3), random.uniform(r + 3, PH - r - 3)
            if self.clear_at(x, y, r):
                if math.hypot(x - ax, y - ay) >= far or k > 200:
                    return x, y
                best = best or (x, y)
        if best:
            return best
        for i in range(GW * GH):
            if self.grid[i] == OPEN:
                return (i % GW) * 2 + 1.0, (i // GW) * 2 + 1.0
        return PW / 2, PH / 2

    def clear_at(self, x, y, r):
        for yy in range(int(y - r), int(y + r) + 1, 2):
            for xx in range(int(x - r), int(x + r) + 1, 2):
                if self.blocked(xx, yy):
                    return False
        return True

    def trail_hit(self, x, y, rad):
        """Does a circle at (x, y) touch the loose yarn?"""
        if not self.trail or self.trail_safe > 0:
            return False
        g = self.grid
        x0, x1 = max(0, int(x - rad) // 2), min(GW - 1, int(x + rad) // 2)
        y0, y1 = max(0, int(y - rad) // 2), min(GH - 1, int(y + rad) // 2)
        rr = (rad + 1) * (rad + 1)
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                if g[cy * GW + cx] == TRAIL and (cx * 2 + 1 - x) ** 2 + (cy * 2 + 1 - y) ** 2 <= rr:
                    return True
        return False

    def kumo_hit(self, x, y, rad):
        if not self.weaving:
            return False
        kx, ky = self.kumo_px()
        return math.hypot(kx - x, ky - y) < rad + 3

    def touch_check(self, x, y, r, kind):
        if self.trail_hit(x, y, r) or self.kumo_hit(x, y, r):
            self.hazard_hit(kind, x, y)
            return True
        return False

    def ring_check(self, x, y, r):
        """A bark / static wave of radius r: it snaps loose yarn it passes over."""
        if not self.weaving:
            return
        for c in self.trail:
            d = math.hypot((c % GW) * 2 + 1 - x, (c // GW) * 2 + 1 - y)
            if abs(d - r) <= 3:
                self.hazard_hit("bark", x, y)
                return
        kx, ky = self.kumo_px()
        if abs(math.hypot(kx - x, ky - y) - r) <= 4:
            self.hazard_hit("bark", x, y)

    def strike_column(self, x):
        if not self.weaving:
            return
        kx, _ = self.kumo_px()
        if abs(kx - x) <= 4 or any(abs((c % GW) * 2 + 1 - x) <= 3 for c in self.trail):
            self.hazard_hit("bolt", x, 0)

    # ---------------------------------------------------------------- spawning
    def spawn_ball(self, kind, x=None, y=None, color=None):
        sp = self.st["fspeed"] * self.hz_speed
        if kind == "fluff":
            r, speed, c = 7, sp, "gray"
        elif kind == "mini":
            r, speed, c = 4, sp * 1.35, color or "gray"
        else:
            r, speed, c = 6, 34.0 + 2 * self.tier, color or random.choice(POM_COLS)
        if x is None:
            x, y = self.find_spot(r + 2, 60)
        b = Ball(x, y, r, speed, kind, c)
        if self.state == "play":
            b.born = 0.4 if kind == "mini" else 0.8
        self.balls.append(b)
        return b

    def spawn_minion(self, kind, x, y):
        if kind == "moth":
            if len(self.moths) < 6:
                self.moths.append(Moth(x, y))
        else:
            n = sum(1 for b in self.balls if b.kind == "mini")
            if n < 8:
                self.spawn_ball("mini", x, y, "lavender" if kind == "cloud" else "gray")

    def respawn(self, kind, delay):
        self.respawns.append([delay, kind])

    def zip_home(self):
        """An edge cell far from KUMO for a (re)spawning zip."""
        kx, ky = self.kx, self.ky
        best, bd = None, -1
        for _ in range(400):
            i = random.randrange(GW * GH)
            if self.is_edge(i):
                d = abs(i % GW - kx) + abs(i // GW - ky)
                if d > bd:
                    best, bd = i, d
                if bd > 70:
                    break
        return best

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        s = self.state
        inp = self.app.input
        if s == "intro":
            if self.boss:
                self.boss.update(dt)
            if self.state_t > self.intro_len or (self.state_t > 0.6 and inp.hit("a")):
                self.state = "play"
                self.state_t = 0.0
                if self.boss:
                    self.boss.state = "fight"
        elif s == "play":
            self.play(dt)
        elif s == "clear":
            if self.boss:
                self.boss.update(dt)
            if self.state_t > 1.1:
                self.begin_reveal()
        elif s == "reveal":
            self.update_reveal(dt)
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
        for w in self.wraps:
            w[2] += dt
        self.wraps = [w for w in self.wraps if w[2] < 1.0]
        for r in self.recoil:
            r[1] -= dt
        self.recoil = [r for r in self.recoil if r[1] > 0]
        self.happy_t = max(0.0, self.happy_t - dt)
        self.hurt_t = max(0.0, self.hurt_t - dt)

    def on_pick(self, uid):
        if uid:
            self.levels[uid] = self.lv(uid) + 1
            u = next(x for x in UPGRADES if x.id == uid)
            self.hype.banner(u.name, f"LEVEL {self.levels[uid]}", color=u.color, dur=1.2, scale=1)
            if uid == "life":
                self.lives += 1
                self.app.audio.play("extra")
            elif uid == "guard":
                self.guard += 1
            elif uid == "claws":
                self.claws += 1

    def play(self, dt):
        st = self.st
        self.stime += dt
        self.inv = max(0.0, self.inv - dt)
        self.stun = max(0.0, self.stun - dt)
        self.freeze = max(0.0, self.freeze - dt)
        self.nip = max(0.0, self.nip - dt)
        self.trail_safe = max(0.0, self.trail_safe - dt)
        self.kmove_t = max(0.0, self.kmove_t - dt)
        self.move_kumo(dt)
        if self.state != "play":
            return
        self.update_fray(dt)
        if self.state != "play":
            return
        self.update_balls(dt)
        self.update_zips(dt)
        self.update_moths(dt)
        self.update_nose(dt)
        self.update_storms(dt)
        self.update_items(dt)
        if self.boss:
            self.boss.update(dt)
        if self.state != "play":
            return
        for r in self.respawns:
            r[0] -= dt
            if r[0] <= 0:
                if r[1] == "zip":
                    c = self.zip_home()
                    if c is not None:
                        self.zips.append(Zip(c, False))
                elif r[1] == "moth":
                    self.moths.append(Moth(random.choice((-6.0, PW + 6.0)), random.uniform(10, PH - 10)))
                else:
                    self.spawn_ball(r[1])
        self.respawns = [r for r in self.respawns if r[0] > 0]
        if st["kind"] == "bonus":
            self.bonus_left -= dt
            if self.bonus_left <= 0:
                self.bonus_left = 0.0
                self.hype.banner("TIME UP!", color="yellow", dur=1.2)
                self.stage_clear()
                return
        self.stage_combo = max(self.stage_combo, self.hype.combo)
        if self.hype.fever_on and not self.was_fever:
            self.hype.fever_t += 2 * self.lv("fever")
            self.app.audio.music("fever")
            kx, ky = self.kumo_px()
            self.floats.add(FX + kx, FY + ky - 16, "RAINBOW YARN!", "yellow")
        elif self.was_fever and not self.hype.fever_on:
            self.app.audio.music(self.song())
        self.was_fever = self.hype.fever_on
        self.check_life()

    def check_life(self):
        i = self.life_i
        target = LIFE_AT[i] if i < len(LIFE_AT) else LIFE_AT[-1] + 200000 * (i - len(LIFE_AT) + 1)
        if self.score >= target:
            self.life_i += 1
            self.lives += 1
            self.hype.banner("BONUS LIFE!", f"{target} POINTS", color="pink", dur=1.4, sound="extra")
            self.hype.shower(16, "hearts")

    # ---------------------------------------------------------------- KUMO
    def held_dir(self):
        inp = self.app.input
        for name in DIR_ORDER:
            if inp.hit(name):
                self.last_dir = name
        if self.last_dir and inp.down(self.last_dir):
            return self.last_dir
        for name in DIR_ORDER:
            if inp.down(name):
                return name
        return None

    def move_kumo(self, dt):
        d = self.held_dir()
        self.careful = self.app.input.down("a")      # careful: slow and precise, x2 stitches
        if d is None or self.stun > 0:
            self.kacc = 0.0
            if self.weaving:
                self.idle += dt
            return
        self.kacc += self.kumo_speed(self.careful) * dt
        moved = False
        while self.kacc >= 1:
            self.kacc -= 1
            if not self.step(d):
                self.kacc = 0.0
                break
            moved = True
            if self.state != "play" or self.stun > 0:
                break
        if moved:
            self.idle = 0.0
            self.kmove_t = 0.15
            if DIRS[d][0]:
                self.kface = DIRS[d][0]
        elif self.weaving:
            self.idle += dt

    def step(self, d):
        dx, dy = DIRS[d]
        nx, ny = self.kx + dx, self.ky + dy
        if not (0 <= nx < GW and 0 <= ny < GH):
            return False if self.weaving else self.slide(dx, dy)
        i = ny * GW + nx
        v = self.grid[i]
        if not self.weaving:
            if v == OPEN:
                self.weaving = True
                self.anchor = (self.kx, self.ky)
                self.trail, self.trail_slow = [i], [self.careful]
                self.grid[i] = TRAIL
                self.kprev = (self.kx, self.ky)
                self.kx, self.ky = nx, ny
                self.fray = 0.0
                self.idle = 0.0
                self.app.audio.play("hold")
                self.after_step()
                return True
            if v == CLAIMED and self.is_edge(i):
                self.kprev = (self.kx, self.ky)
                self.kx, self.ky = nx, ny
                self.after_step()
                return True
            return self.slide(dx, dy)
        if v == OPEN:
            self.grid[i] = TRAIL
            self.trail.append(i)
            self.trail_slow.append(self.careful)
            self.kprev = (self.kx, self.ky)
            self.kx, self.ky = nx, ny
            self.after_step()
            return True
        if v == CLAIMED:
            self.kprev = (self.kx, self.ky)
            self.kx, self.ky = nx, ny
            self.finish_weave()
            return True
        return False                      # can't cross your own loose yarn

    def slide(self, dx, dy):
        """Walking along the yarn: if the way ahead is blocked, follow the edge round the corner."""
        opts = []
        for sx, sy in ((dy, dx), (-dy, -dx)):
            nx, ny = self.kx + sx, self.ky + sy
            if 0 <= nx < GW and 0 <= ny < GH and (nx, ny) != self.kprev and self.is_edge(ny * GW + nx):
                opts.append((nx, ny))
        if len(opts) != 1:
            return False
        self.kprev = (self.kx, self.ky)
        self.kx, self.ky = opts[0]
        self.after_step()
        return True

    def after_step(self):
        x, y = self.kumo_px()
        for it in self.items:
            if it.life > 0 and abs(it.x - x) < 7 and abs(it.y - y) < 7:
                self.collect(it)
        if self.weaving:
            for k in self.knots:
                if k[2] and abs(k[0] * 2 + 1 - x) < 6 and abs(k[1] * 2 + 1 - y) < 6:
                    self.hazard_hit("knot", x, y)
                    return

    def update_fray(self, dt):
        """Stand still while weaving and the loose yarn starts to fray from where you began."""
        if not self.weaving:
            return
        delay = 0.9 + 0.5 * self.lv("strong")
        if self.idle > delay:
            self.fray += (26 - 6 * self.lv("strong")) * dt
            if int(self.fray * 4) % 6 == 0:
                c = self.trail[min(len(self.trail) - 1, int(self.fray))]
                self.parts.sparkle(FX + (c % GW) * 2 + 1, FY + (c // GW) * 2 + 1, "orange")
            if self.fray >= len(self.trail):
                self.hazard_hit("fray", *self.kumo_px())

    # ---------------------------------------------------------------- claiming
    def finish_weave(self):
        self.weaving = False
        for c in self.trail:
            self.grid[c] = CLAIMED
        self.claim()

    def claim(self):
        trail, slow = self.trail, sum(1 for s in self.trail_slow if s)
        self.trail, self.trail_slow = [], []
        self.fray = -1.0
        g = self.grid
        regs = open_regions(g)
        keep = None
        if regs:
            keep = max(regs, key=len)
            if self.boss and self.boss.state == "fight":
                bc = self.cell_at(self.boss.x, self.boss.y)
                for r in regs:
                    if bc in r:
                        keep = r
                        break
        newly = list(trail)
        for r in regs:
            if r is not keep:
                for c in r:
                    g[c] = CLAIMED
                newly.extend(r)
        self.open_n = len(keep) if keep else 0
        mark = bytearray(GW * GH)
        for c in newly:
            mark[c] = 1
        # repaint the newly claimed cells and their neighbours (old edges may now be inside)
        dirty = bytearray(GW * GH)
        for c in newly:
            x, y = c % GW, c // GW
            for yy in (y - 1, y, y + 1):
                if 0 <= yy < GH:
                    for xx in (x - 1, x, x + 1):
                        if 0 <= xx < GW:
                            dirty[yy * GW + xx] = 1
        for c in range(GW * GH):
            if dirty[c] and g[c] == CLAIMED:
                self.paint(c)
        # score: bigger single claims are worth more, careful stitches multiply
        cells = len(newly)
        frac = cells / max(1, self.claimable)
        stitch = 1 + (slow / max(1, len(trail))) * (self.careful_mult() - 1)
        sx = sum(c % GW for c in newly) * 2 // max(1, cells) + FX
        sy = sum(c // GW for c in newly) * 2 // max(1, cells) + FY
        mult = 2 if self.st["kind"] == "bonus" else 1
        pts = int(cells * (1 + 3 * frac) * stitch) * mult
        self.score_at(pts, sx, sy)
        self.claims += 1
        self.hype.hit(1, fever=self.fever_gain(0.05 + frac * 1.4))
        if self.hype.combo > 1:
            self.add(self.factor_pts(self.hype.combo_bonus(20)))
        if stitch > 1.05:
            self.floats.add(sx, sy - 10, f"STITCH X{stitch:.1f}", "mint")
        self.happy_t = 0.7
        for k in range(0, len(trail), 3):
            c = trail[k]
            self.parts.burst(FX + (c % GW) * 2 + 1, FY + (c // GW) * 2 + 1, 2, (self.theme[4], self.theme[5], "white"),
                             30, 0.5)
        au = self.app.audio
        self.headline(frac, self.wrap_caught(mark), cells)
        if frac >= 0.05 and self.hype.lucky(0.015 + 0.005 * self.lv("luck")):
            self.hype.jackpot(self.factor_pts(3000), "LUCKY STITCH!")
        # the boss loses rug
        b = self.boss
        if b and b.state == "fight":
            r2 = (b.r + 22) ** 2
            near = any(((c % GW) * 2 + 1 - b.x) ** 2 + ((c // GW) * 2 + 1 - b.y) ** 2 <= r2 for c in newly)
            dmg = b.damage(cells, near)
            if dmg:
                self.hype.hitstop(0.08)
                self.floats.add(FX + b.x, FY + b.y - b.r - 8, "CLOSE WEAVE! X2" if near else f"-{dmg}",
                                "hotpink" if near else "white")
                self.parts.burst(FX + b.x, FY + b.y, 14, ("white", "yellow", "pink"), 70, 0.5)
                au.play("explode")
            if b.hp > 0 and self.open_n < self.claimable * 0.06:
                b.hp = 0
                self.hype.banner("CORNERED!", color="yellow", dur=1.2)
            if b.hp <= 0:
                self.boss_defeated()
                return
        # KUMO must stand on yarn
        if not self.is_edge(self.ky * GW + self.kx):
            self.relocate_kumo()
        if self.st["kind"] == "normal" and self.percent() >= self.st["target"]:
            self.stage_clear()
        elif self.st["kind"] == "bonus":
            if self.st["bonus"] == "poms" and self.poms_wrapped >= self.poms_total:
                self.hype.banner("ALL ROUNDED UP!", rainbow=True, dur=1.4, sound="bonus")
                self.stage_clear()
            elif self.percent() >= 95:
                self.stage_clear()

    def headline(self, frac, n, cells):
        """One headline per claim: the biggest news wins (weave size or wrapped hazards)."""
        g = self.hype
        pct = int(frac * 100)
        if frac >= 0.33:
            g.banner("MEGA WEAVE!!!", f"{pct}% IN ONE GO", rainbow=True, dur=1.8, sound="jackpot")
            g.shower(70, "confetti")
            g.flash("white", 0.3)
            g.slowmo(0.4, 0.6)
            self.app.shake(4, 0.4)
        elif n >= 3:
            g.banner("MEGA WRAP!!", f"{n} AT ONCE", rainbow=True, dur=1.6, sound="fever")
            g.shower(50, "confetti")
        elif frac >= 0.2:
            g.banner("HUGE WEAVE!!", f"{pct}%", color="hotpink", dur=1.4, sound="quad")
            g.shower(40, "stars")
            self.app.shake(3, 0.25)
        elif n == 2:
            g.banner("DOUBLE WRAP!", color="lime", dur=1.2, sound="combo")
            g.shower(20, "stars")
        elif frac >= 0.1:
            g.banner("BIG WEAVE!", color="yellow", dur=1.1, scale=1, sound="line")
        elif n == 1:
            g.banner("WRAPPED!", color="lime", dur=1.0, scale=1, sound="trap")
        else:
            self.app.audio.play("line" if cells > 60 else "lock")

    def wrap_caught(self, mark):
        """Hazards, treats and knots inside the claimed pocket get wrapped up. Returns how many hazards."""
        caught = []
        for b in self.balls:
            c = self.cell_at(b.x, b.y)
            if c >= 0 and mark[c]:
                b.alive = False
                caught.append((b.kind, b.x, b.y, b.color))
        self.balls = [b for b in self.balls if b.alive]
        for z in self.zips:
            if not self.is_edge(z.c):
                z.alive = False
                caught.append(("zip", (z.c % GW) * 2 + 1.0, (z.c // GW) * 2 + 1.0, "yellow"))
        self.zips = [z for z in self.zips if z.alive]
        for m in self.moths:
            c = self.cell_at(m.x, m.y)
            if c >= 0 and mark[c]:
                m.alive = False
                caught.append(("moth", m.x, m.y, "cream"))
        self.moths = [m for m in self.moths if m.alive]
        for it in self.items:
            c = self.cell_at(it.x, it.y)
            if c >= 0 and mark[c]:
                self.collect(it)
        for k in self.knots:
            if k[2] and mark[k[1] * GW + k[0]]:
                k[2] = False
                self.score_at(800, FX + k[0] * 2, FY + k[1] * 2 - 6, "lavender")
                self.floats.add(FX + k[0] * 2, FY + k[1] * 2 + 4, "UNTANGLED!", "lavender")
        nz = self.nose
        if nz["st"] in ("warn", "up"):
            c = self.cell_at(nz["x"], nz["y"])
            if c >= 0 and mark[c]:
                nz["st"], nz["t"] = "wait", self.st["nose"]
                self.score_at(1500, FX + nz["x"], FY + nz["y"] - 8, "pink")
                self.hype.banner("BOOP!", "THE NOSE GOT BOOPED", color="pink", dur=1.0, scale=1, sound="pop")
        if not caught:
            return 0
        boss_hit = 0
        for k, (kind, x, y, c) in enumerate(caught):
            self.wraps.append([x, y, 0.0, c])
            self.wrapped_n += 1
            if kind == "pom":
                self.poms_wrapped += 1
                pts = 600 * self.poms_wrapped
            else:
                pts = {"fluff": 1500, "mini": 800, "zip": 700, "moth": 700}.get(kind, 500)
            self.score_at(pts * (k + 1), FX + x, FY + y - 6, "lime")
            self.hype.hit(1, fever=self.fever_gain(0.06))
            self.parts.burst(FX + x, FY + y, 12, (self.theme[4], self.theme[5], "white", c), 60, 0.6)
            if self.st["kind"] == "normal":
                if kind == "fluff":
                    self.respawn("fluff", 6.0)
                elif kind == "zip":
                    self.respawn("zip", 4.0)
                elif kind == "moth":
                    self.respawn("moth", 6.0)
            elif self.st["kind"] == "boss":
                if kind == "zip":
                    self.respawn("zip", 5.0)
                if kind in ("mini", "moth"):
                    boss_hit += 1
        self.app.audio.play("bubble")
        if boss_hit and self.boss and self.boss.state == "fight":
            self.boss.hp = max(0, self.boss.hp - boss_hit * self.boss.maxhp * 4 // 100)
            self.boss.flash = 0.25
        return len(caught)

    def relocate_kumo(self):
        """After a claim KUMO might stand inside the claimed area: hop to the nearest yarn edge."""
        start = self.ky * GW + self.kx
        seen = {start}
        q = [start]
        k = 0
        while k < len(q):
            c = q[k]
            k += 1
            if self.is_edge(c):
                self.kx, self.ky = c % GW, c // GW
                self.kprev = None
                return
            x = c % GW
            for n in (c - 1 if x > 0 else -1, c + 1 if x < GW - 1 else -1, c - GW, c + GW):
                if 0 <= n < GW * GH and n not in seen:
                    seen.add(n)
                    q.append(n)

    # ---------------------------------------------------------------- getting hurt
    def hazard_hit(self, kind, x, y):
        """Something touched the loose yarn (or KUMO while weaving / a zip touched KUMO)."""
        if self.state != "play" or self.inv > 0:
            return
        if kind != "zip" and kind != "fray" and not self.weaving:
            return
        if kind not in ("zip", "fray", "knot") and self.hype.fever_on:
            return                              # RAINBOW YARN: nothing snaps it during FEVER
        if kind not in ("zip", "fray", "knot", "pom") and self.guard > 0:
            self.guard -= 1
            self.trail_safe = 1.0
            self.hype.banner("STURDY YARN!", f"{self.guard} LEFT" if self.guard else None, color="sky", dur=1.0,
                             scale=1, sound="tin")
            self.parts.burst(FX + x, FY + y, 10, ("sky", "white"), 50, 0.4)
            return
        self.lose_life(kind)

    def zip_touch(self, z):
        if self.inv > 0 or z.born > 0 or self.state != "play":
            return
        if self.claws > 0:
            self.claws -= 1
            z.alive = False
            x, y = (z.c % GW) * 2 + 1.0, (z.c // GW) * 2 + 1.0
            self.wraps.append([x, y, 0.0, "yellow"])
            self.score_at(800, FX + x, FY + y - 8, "yellow")
            self.hype.banner("POUNCE!", color="yellow", dur=0.9, scale=1, sound="pop")
            self.respawn("zip", 4.0)
            return
        self.hazard_hit("zip", 0, 0)

    def lose_life(self, kind):
        au = self.app.audio
        self.hype.break_combo()
        au.play("hurt")
        self.app.shake(3, 0.3)
        kx, ky = self.kumo_px()
        self.parts.burst(FX + kx, FY + ky, 14, ("white", "gray", "pink"), 60, 0.6)
        if self.weaving:
            self.recoil = [[c, 0.45] for c in self.trail]
            for c in self.trail:
                self.grid[c] = OPEN
            self.trail, self.trail_slow = [], []
            self.weaving = False
            self.kx, self.ky = self.anchor
            self.kprev = None
        self.fray = -1.0
        self.idle = 0.0
        self.hurt_t = 0.9
        self.stun = 0.5
        if self.st["kind"] == "bonus":       # no lives lost in a bonus stage
            self.inv = 1.0
            self.floats.add(FX + kx, FY + ky - 12, "BOING!", "pink")
            return
        self.missed = True
        self.lives -= 1
        self.inv = 2.2
        if self.lives <= 0:
            self.state = "over"
            self.hype.banner("GAME OVER", f"STAGE {self.n}", color="red", dur=3.0)
            au.play("gameover")
            self.end_game(False, f"STAGE {self.n}", delay=2.5)
            return
        self.hype.banner(SNAP_TEXT.get(kind, "OUCH!"), f"{self.lives} LEFT", color="pink", dur=1.1, scale=1)

    # ---------------------------------------------------------------- hazards
    def move_ball(self, o, dt):
        """Bounce a round thing around the open rug (claimed rug and loose yarn are walls)."""
        sp = math.hypot(o.vx, o.vy)
        steps = max(1, int(sp * dt / 1.5) + 1)
        h = dt / steps
        r = o.r
        jam = 0
        for _ in range(steps):
            nx = o.x + o.vx * h
            ex = nx + (r if o.vx > 0 else -r)
            if self.blocked(ex, o.y) or self.blocked(ex, o.y - r * 0.7) or self.blocked(ex, o.y + r * 0.7):
                o.vx = -o.vx
                jam += 1
            else:
                o.x = nx
            ny = o.y + o.vy * h
            ey = ny + (r if o.vy > 0 else -r)
            if self.blocked(o.x, ey) or self.blocked(o.x - r * 0.7, ey) or self.blocked(o.x + r * 0.7, ey):
                o.vy = -o.vy
                jam += 1
            else:
                o.y = ny
        o.stuck = o.stuck + 1 if jam >= 2 * steps else 0
        if o.stuck > 20:                    # wedged in a tight spot: pop out somewhere roomier
            o.stuck = 0
            o.x, o.y = self.find_spot(r + 1, 0, (o.x, o.y))

    def update_balls(self, dt):
        frozen = self.freeze > 0
        for b in self.balls:
            b.born = max(0.0, b.born - dt)
            if frozen and b.kind != "pom":
                continue
            b.turn -= dt
            if b.turn <= 0:                  # crackly static: erratic little swerves
                b.turn = random.uniform(0.6, 2.2)
                a = math.atan2(b.vy, b.vx) + random.uniform(-0.7, 0.7)
                b.vx, b.vy = math.cos(a), math.sin(a)
            sp = math.hypot(b.vx, b.vy) or 1.0
            want = b.speed * (0.3 if b.zap > 0 else 1.0)
            b.vx, b.vy = b.vx / sp * want, b.vy / sp * want
            self.move_ball(b, dt)
            if b.zap > 0:
                b.zap -= dt
                if b.zap <= 0:
                    self.storms.append([b.x, b.y, float(b.r)])
                    self.app.audio.play("explode")
            if b.born <= 0:
                self.touch_check(b.x, b.y, b.r, "pom" if b.kind == "pom" else "fluff")
                if self.state != "play":
                    return

    def update_storms(self, dt):
        st = self.st
        if st["storm"] > 0 and self.freeze <= 0:
            self.storm_t -= dt
            if self.storm_t <= 0:
                self.storm_t = st["storm"] * random.uniform(0.8, 1.2)
                fl = [b for b in self.balls if b.kind == "fluff" and b.born <= 0]
                if fl:
                    random.choice(fl).zap = 0.9
                    self.app.audio.play("trap")
        for sw in self.storms:
            sw[2] += 120 * dt
            self.ring_check(sw[0], sw[1], sw[2])
        self.storms = [sw for sw in self.storms if sw[2] < 36]

    def update_zips(self, dt):
        if self.freeze > 0:
            return
        kx, ky = self.kumo_px()
        sp = self.st["zspeed"] * self.hz_speed
        for z in self.zips:
            z.born = max(0.0, z.born - dt)
            if not self.is_edge(z.c):       # the edge vanished under it
                c = self.zip_home()
                if c is None:
                    continue
                z.c = c
            z.acc += sp * dt
            while z.acc >= 1:
                z.acc -= 1
                self.zip_step(z)
            if abs((z.c % GW) * 2 + 1 - kx) < 5 and abs((z.c // GW) * 2 + 1 - ky) < 5:
                self.zip_touch(z)
                if self.state != "play":
                    return
        self.zips = [z for z in self.zips if z.alive]

    def zip_step(self, z):
        x, y = z.c % GW, z.c // GW
        opts = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (dx, dy) == (-z.dx, -z.dy):
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < GW and 0 <= ny < GH and self.is_edge(ny * GW + nx):
                opts.append((dx, dy))
        if not opts:
            z.dx, z.dy = -z.dx, -z.dy
            nx, ny = x + z.dx, y + z.dy
            if 0 <= nx < GW and 0 <= ny < GH and self.is_edge(ny * GW + nx):
                z.c = ny * GW + nx
            return
        if len(opts) == 1:
            d = opts[0]
        elif z.hunter and random.random() < 0.75:
            d = min(opts, key=lambda o: abs(x + o[0] - self.kx) + abs(y + o[1] - self.ky))
        elif (z.dx, z.dy) in opts and random.random() < 0.6:
            d = (z.dx, z.dy)
        else:
            d = random.choice(opts)
        z.dx, z.dy = d
        z.c = (y + d[1]) * GW + x + d[0]

    def update_moths(self, dt):
        frozen = self.freeze > 0
        msp = (18 + 0.8 * self.tier) * self.hz_speed
        for m in self.moths:
            m.t += dt
            if frozen:
                continue
            if self.weaving and len(self.trail) > 4:
                c = self.trail[len(self.trail) // 2]
                tx, ty, sp = (c % GW) * 2 + 1.0, (c // GW) * 2 + 1.0, msp * 1.25
            else:
                tx, ty, sp = m.hx + math.sin(m.t * 0.7) * 60, m.hy + math.sin(m.t * 1.1) * 30, msp * 0.7
            a = math.atan2(ty - m.y, tx - m.x)
            k = min(1.0, dt * 2)
            m.vx += (math.cos(a) * sp - m.vx) * k
            m.vy += (math.sin(a) * sp - m.vy) * k
            m.x = max(-8.0, min(PW + 8.0, m.x + m.vx * dt))
            m.y = max(-8.0, min(PH + 8.0, m.y + m.vy * dt + math.sin(m.t * 9) * 0.3))
            if self.weaving and self.trail_hit(m.x, m.y, 3):
                self.hazard_hit("moth", m.x, m.y)
                if self.state != "play":
                    return

    def update_nose(self, dt):
        nz, every = self.nose, self.st["nose"]
        if every <= 0 or self.freeze > 0:
            return
        nz["t"] -= dt
        if nz["st"] == "wait" and nz["t"] <= 0:
            near = None
            if self.weaving and self.trail:
                c = self.trail[-1]
                near = ((c % GW) * 2 + 1.0 + random.uniform(-20, 20), (c // GW) * 2 + 1.0 + random.uniform(-20, 20))
            x, y = self.find_spot(10, 0 if near else 30)
            if near and self.clear_at(near[0], near[1], 10):
                x, y = near
            nz.update(st="warn", t=1.1, x=x, y=y)
            self.floats.add(FX + x, FY + y - 16, "SNIFF SNIFF", "peach")
        elif nz["st"] == "warn" and nz["t"] <= 0:
            nz["st"], nz["t"] = "up", 1.3
            self.app.audio.play("pop")
            self.app.shake(2, 0.15)
        elif nz["st"] == "up":
            self.touch_check(nz["x"], nz["y"], 11, "nose")
            if nz["t"] <= 0:
                nz["st"], nz["t"] = "down", 0.35
        elif nz["st"] == "down" and nz["t"] <= 0:
            nz["st"], nz["t"] = "wait", every * random.uniform(0.8, 1.2)

    def update_items(self, dt):
        st = self.st
        if st["kind"] != "bonus":
            self.item_t -= dt
            if self.item_t <= 0:
                self.item_t = st["items"] * (1 - 0.12 * self.lv("luck")) * random.uniform(0.8, 1.2)
                if len(self.items) < 3:
                    luck = self.lv("luck")
                    pool = ["fish"] * 10 + ["nip"] * 3 + ["bell"] * 3 + ["rainbow"] * 1
                    if self.lives < 5:
                        pool += ["heart"]
                    if random.random() < 0.02 + 0.01 * luck:
                        pool = ["gold"]
                    x, y = self.find_spot(7, 30)
                    self.items.append(Item(x, y, random.choice(pool)))
        for it in self.items:
            it.life -= dt
        self.items = [it for it in self.items if it.life > 0]

    def collect(self, it):
        if it.life <= 0:
            return
        it.life = 0.0
        au = self.app.audio
        x, y = FX + it.x, FY + it.y
        k = it.kind
        self.parts.burst(x, y, 10, ("yellow", "white", "pink"), 50, 0.5)
        if k == "fish":
            self.fish_got += 1
            self.hype.hit(1, fever=self.fever_gain(0.04))
            self.score_at(300 + self.hype.combo_bonus(10), x, y - 6)
            au.play("eat")
            if self.st["kind"] == "bonus" and self.fish_got >= self.fish_total and self.state == "play":
                self.hype.banner("ALL TREATS!", rainbow=True, dur=1.4, sound="bonus")
                self.stage_clear()
            return
        self.floats.add(x, y - 12, ITEM_TEXT[k], "mint")
        au.play("powerup")
        if k == "nip":
            self.nip = 8.0
        elif k == "bell":
            self.freeze = 4.0 + self.lv("luck")
            self.hype.flash("sky", 0.2)
        elif k == "heart":
            self.lives += 1
            au.play("extra")
        elif k == "gold":
            self.hype.jackpot(self.factor_pts(5000), "GOLDEN YARN!")
        elif k == "rainbow":
            self.hype.start_fever()

    # ---------------------------------------------------------------- clear / reveal / tally
    def stage_clear(self):
        if self.state != "play":
            return
        self.state = "clear"
        self.state_t = 0.0
        if self.weaving:
            for c in self.trail:
                self.grid[c] = OPEN
            self.trail, self.trail_slow = [], []
            self.weaving = False
            self.kx, self.ky = self.anchor
        left = [(b.x, b.y, b.color) for b in self.balls] + [(m.x, m.y, "cream") for m in self.moths] + \
               [((z.c % GW) * 2 + 1.0, (z.c // GW) * 2 + 1.0, "yellow") for z in self.zips]
        for x, y, c in left:              # everything left gets wrapped up for a few points
            self.wraps.append([x, y, -random.uniform(0, 0.5), c])
            self.score_at(300, FX + x, FY + y - 6, "lime")
        self.balls, self.moths, self.zips, self.storms, self.items = [], [], [], [], []
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.hype.slowmo(0.3, 0.8)
        self.hype.flash("white", 0.2)
        self.app.audio.play("win")
        if self.st["kind"] == "normal":
            self.hype.banner("RUG CLAIMED!", f"{self.percent()}%", color="mint", dur=1.4)
            self.hype.shower(30, "confetti")
        self.app.audio.music(None)
        self.was_fever = False
        self.happy_t = 3.0
        self.hype.combo_y = -20             # keep the picture caption clear

    def boss_defeated(self):
        g = self.hype
        b = self.boss
        b.state = "dead"
        b.hp = 0
        self.app.audio.play("bossdown")
        g.banner("WRAPPED UP!", b.name, rainbow=True, dur=2.2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(40, "coins")
        self.app.shake(6, 0.6)
        self.score_at(20000, FX + b.x, FY + b.y - 10)
        self.wraps.append([b.x, b.y, -0.3, "white"])
        self.stage_clear()
        g.slowmo(0.3, 1.2)

    def begin_reveal(self):
        self.state = "reveal"
        self.state_t = 0.0
        kx, ky = self.kx, self.ky
        rest = [i for i in range(GW * GH) if self.grid[i] != CLAIMED]
        rest.sort(key=lambda i: (i % GW - kx) ** 2 + (i // GW - ky) ** 2)
        self.reveal_list = rest
        self.reveal_i = 0
        self.friends += 1
        self.app.audio.play("bonus")

    def update_reveal(self, dt):
        n = len(self.reveal_list)
        if self.reveal_i < n:
            k = max(1, int(n * dt / 0.9) + 1)
            for i in self.reveal_list[self.reveal_i:self.reveal_i + k]:
                x, y = i % GW, i // GW
                self.field.blit(self.pic, (x * 2, y * 2), (x * 2, y * 2, 2, 2))
                if random.random() < 0.02:
                    self.parts.sparkle(FX + x * 2, FY + y * 2, random.choice(("yellow", "white", "pink")))
            self.reveal_i += k
            if self.reveal_i >= n:
                self.field.blit(self.pic, (0, 0))      # the whole picture, yarn and furniture gone
                self.hype.shower(30, "hearts")
                if self.golden:
                    self.hype.jackpot(self.factor_pts(20000), "A GOLDEN CAT!")
                self.app.audio.play("levelup")
        elif self.state_t > 2.8 or (self.state_t > 1.2 and self.app.input.hit("a")):
            self.begin_tally()

    def begin_tally(self):
        st = self.st
        f = self.factor_pts
        pct = self.percent()
        rows = []
        if st["kind"] == "normal":
            rows.append((f"CLAIMED {pct}%", f(pct * 100)))
            extra = max(0, pct - st["target"])
            rows.append((f"OVER TARGET +{extra}%", f(extra * 400)))
            par = 75 + 3 * self.tier
            rows.append(("TIME BONUS", f(max(0, int(par - self.stime)) * 25)))
            rows.append((f"WRAPPED X{self.wrapped_n}", f(self.wrapped_n * 500)))
        elif st["kind"] == "boss":
            rows.append(("BOSS BONUS", f(15000 + 2500 * self.tier)))
            rows.append((f"WRAPPED X{self.wrapped_n}", f(self.wrapped_n * 500)))
        elif st["bonus"] == "poms":
            rows.append((f"POM-POMS X{self.poms_wrapped}", f(self.poms_wrapped * 800)))
            rows.append(("ALL ROUNDED UP", f(10000) if self.poms_wrapped >= self.poms_total else 0))
            rows.append((f"CLAIMED {pct}%", f(pct * 50)))
        else:
            rows.append((f"TREATS X{self.fish_got}", f(self.fish_got * 300)))
            rows.append(("ALL TREATS", f(8000) if self.fish_got >= self.fish_total else 0))
            rows.append((f"CLAIMED {pct}%", f(pct * 50)))
        rows.append((f"BEST COMBO {self.stage_combo}", f(self.stage_combo * 150)))
        if st["kind"] != "bonus":
            rows.append(("NO MISS", f(5000) if not self.missed else 0))
        self.tally = [[label, v, 0.0] for label, v in rows]
        self.tally_i = 0
        self.tally_wait = 0.0
        self.state = "tally"
        self.state_t = 0.0
        if st["kind"] != "bonus" and not self.missed:
            self.hype.banner("PURRFECT!", "NO YARN SNAPPED", rainbow=True, dur=1.8, sound="fever")
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

    def finish_stage(self):
        st = self.st
        self.check_life()
        if self.n >= STAGES:
            self.state = "over"
            self.hype.banner("ALL CLEAR!!", "EVERY RUG IN THE HOUSE!", rainbow=True, dur=5.0, sound="jackpot")
            self.hype.shower(120, "confetti")
            self.end_game(True, "ALL 200 STAGES!", delay=4.5)
            return
        self.next_n = self.n + 1
        if st["kind"] in ("boss", "bonus"):
            self.picks_left = 1
            self.pick_title = "BOSS BONUS!" if st["kind"] == "boss" else "SWEET TREAT!"
            self.state = "pick"
        else:
            self.start_stage(self.next_n)

    # ---------------------------------------------------------------- drawing
    def render(self, s):
        t = self.t
        th = self.theme
        s.fill(col("night"))
        for y in range(FY, FY + PH, 4):          # rug fringe
            s.fill(col("cream"), (2, y + 1, 5, 1))
            s.fill(col("cream"), (W - 7, y + 1, 5, 1))
        pygame.draw.rect(s, col("black"), (FX - 1, FY - 1, PW + 2, PH + 2), 1)
        s.blit(self.field, (FX, FY))
        # loose yarn
        fever = self.hype.fever_on
        for k, c in enumerate(self.trail):
            x, y = FX + (c % GW) * 2, FY + (c // GW) * 2
            if fever:
                cc = rainbow(k // 3, t)
            elif self.trail_slow[k]:
                cc = "white" if k % 2 else th[4]
            else:
                cc = th[4] if (k // 3) % 2 else "white"
            s.fill(col(cc), (x, y, 2, 2))
        for c, life in self.recoil:
            if int(life * 20) % 2:
                s.fill(col("red"), (FX + (c % GW) * 2, FY + (c // GW) * 2, 2, 2))
        if self.weaving and self.fray >= 0 and self.idle > 0.3 and self.trail:
            c = self.trail[min(len(self.trail) - 1, int(self.fray))]
            x, y = FX + (c % GW) * 2 + 1, FY + (c // GW) * 2 + 1
            pygame.draw.circle(s, col("black"), (x, y), 3)
            pygame.draw.circle(s, col("orange" if int(t * 16) % 2 else "red"), (x, y), 2)
        for k in self.knots:
            if k[2]:
                A.draw_knot(s, FX + k[0] * 2 + 1, FY + k[1] * 2 + 1, t)
        for it in self.items:
            A.draw_item(s, it.kind, FX + it.x, FY + it.y, t, it.life)
        nz = self.nose
        if nz["st"] == "warn":
            r = 6 + int(nz["t"] * 12)
            if int(t * 10) % 2:
                pygame.draw.circle(s, col("peach"), (int(FX + nz["x"]), int(FY + nz["y"])), r, 1)
            A.draw_nose(s, FX + nz["x"], FY + nz["y"], t, 0.25)
        elif nz["st"] in ("up", "down"):
            up = 1.0 if nz["st"] == "up" else max(0.0, nz["t"] / 0.35)
            A.draw_nose(s, FX + nz["x"], FY + nz["y"], t, up)
        for b in self.balls:
            if b.born > 0 and int(t * 20) % 2:
                continue
            if b.kind == "pom":
                A.draw_pom(s, FX + b.x, FY + b.y, b.r, t, b.color)
            else:
                A.draw_fluff(s, FX + b.x, FY + b.y, b.r, t * (0.2 if self.freeze > 0 else 1.0), True, b.zap,
                             "gray" if b.kind == "fluff" else b.color)
        for sw in self.storms:
            pygame.draw.circle(s, col("yellow" if int(t * 20) % 2 else "white"), (int(FX + sw[0]), int(FY + sw[1])),
                               int(sw[2]), 1)
        for z in self.zips:
            if z.born > 0 and int(t * 20) % 2:
                continue
            A.draw_zip(s, FX + (z.c % GW) * 2 + 1, FY + (z.c // GW) * 2 + 1, t, z.hunter)
        for m in self.moths:
            A.draw_moth(s, FX + m.x, FY + m.y, t if self.freeze <= 0 else 0.0)
        if self.boss:
            self.boss.draw(s, FX, FY, t)
        for x, y, age, c in self.wraps:
            if age < 0:
                continue
            self.draw_wrap(s, FX + x, FY + y, age, c, t)
        self.draw_kumo(s, t)
        self.parts.draw(s)
        self.floats.draw(s)
        self.draw_hud(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "reveal" and self.reveal_i >= len(self.reveal_list):
            self.draw_caption(s, t)
        elif self.state == "tally":
            self.draw_caption(s, t)
            self.draw_tally(s, t)

    def draw_wrap(self, s, x, y, age, c, t):
        """A hazard being wrapped up: yarn spirals round it into a little ball, then pops."""
        x, y = int(x), int(y)
        if age < 0.6:
            r = 9 - int(age * 6)
            pygame.draw.circle(s, col("black"), (x, y), r + 1)
            pygame.draw.circle(s, col(self.theme[4]), (x, y), r)
            for k in range(3):
                a = age * 14 + k * 2.1
                pygame.draw.line(s, col("white"), (x + int(math.cos(a) * r), y + int(math.sin(a) * r)),
                                 (x - int(math.cos(a) * r), y - int(math.sin(a) * r * 0.5)), 1)
        else:
            k = (age - 0.6) / 0.4
            for i in range(6):
                a = i * math.tau / 6 + age
                d = int(4 + k * 14)
                s.fill(col(rainbow(i, t)), (x + int(math.cos(a) * d), y + int(math.sin(a) * d), 2, 2))

    def draw_kumo(self, s, t):
        if self.state == "over":
            return
        if self.inv > 0 and self.hurt_t <= 0 and int(t * 16) % 2:
            return
        x, y = FX + self.kx * 2 + 1, FY + self.ky * 2 + 1
        if self.hurt_t > 0:
            fr = A.K_HURT
        elif self.happy_t > 0:
            fr = A.K_HAPPY
            y -= int(abs(math.sin(t * 10)) * 3)
        elif self.kmove_t > 0:
            fr = A.K_WALK1 if int(t * 10) % 2 else A.K_WALK2
        elif self.weaving:
            fr = A.K_WEAVE
        else:
            fr = A.K_BLINK if int(t * 1.3) % 6 == 0 else A.K_IDLE
        s.blit(sprite("yw_kumo", fr, flip=self.kface < 0), (x - 7, y - 10))
        if self.careful and self.weaving:
            for k in range(2):
                a = t * 6 + k * math.pi
                s.fill(col("mint"), (x + int(math.cos(a) * 9), y - 12 + int(math.sin(a) * 2), 2, 2))
        if self.nip > 0 and int(t * 8) % 2:
            s.fill(col("lime"), (x - 8, y - 2, 1, 1))
            s.fill(col("lime"), (x + 8, y - 4, 1, 1))

    def draw_hud(self, s, t):
        draw_text(s, f"{self.score:07d}", 4, 3, "white", shadow=None)
        b = self.boss
        if b and b.state != "dead" and self.state != "intro":
            boss_bar(s, b.name, b.hp, b.maxhp, t, y=0)
        else:
            draw_text(s, f"HI {max(self.best, self.score):07d}", 4, 11, "gray", shadow=None)
            if self.st["kind"] == "bonus" and self.state in ("play", "intro"):
                secs = int(math.ceil(self.bonus_left))
                draw_text(s, f"TIME {secs:02d}", W // 2, 3, "yellow" if secs > 5 or int(t * 6) % 2 else "red",
                          align="center", shadow=None)
            else:
                draw_text(s, f"STAGE {self.n}", W // 2, 3, "yellow", align="center", shadow=None)
            # claim meter with the target tick
            x0, w = 116, 88
            pct = self.percent()
            tgt = self.st["target"] if self.st["kind"] == "normal" else 95
            s.fill(col("darkgray"), (x0, 12, w, 4))
            s.fill(col(self.theme[4] if pct < tgt else "lime"), (x0, 12, w * min(100, pct) // 100, 4))
            tx = x0 + w * tgt // 100
            s.fill(col("white"), (tx, 10, 1, 8))
            draw_text(s, f"{pct}%", x0 + w + 4, 11, "lime" if pct >= tgt else "white", shadow=None)
        self.hearts(s, W - 54, 3, self.lives)
        x0, y0 = W - 54, 13
        s.fill(col("darkgray"), (x0, y0, 48, 3))
        if self.hype.fever_on:
            for i in range(48):
                s.fill(col(rainbow(i // 6, t)), (x0 + i, y0, 1, 3))
        else:
            s.fill(col("orange"), (x0, y0, int(48 * self.hype.fever), 3))
        # charges and timed effects along the bottom of the rug
        x = FX + 3
        for label, n, c in (("Y", self.guard, "sky"), ("C", self.claws, "yellow")):
            for _ in range(n):
                pygame.draw.rect(s, col(c), (x, FY + PH - 9, 9, 7), border_radius=2)
                draw_text(s, label, x + 2, FY + PH - 9, "black", shadow=None)
                x += 11
        for label, v, c in (("NIP", self.nip, "lime"), ("FREEZE", self.freeze, "sky")):
            if v > 0 and (v > 2 or int(t * 8) % 2):
                draw_text(s, label, x, FY + PH - 9, c, shadow="ink")
                x += text_width(label) + 6

    def draw_intro(self, s, t):
        st = self.st
        k = st["kind"]
        if k == "boss":
            if int(t * 4) % 2:
                for x in range(-20, W + 20, 20):
                    pygame.draw.polygon(s, col("red"), [(x, 108), (x + 10, 108), (x + 20, 116), (x + 10, 116)])
                    pygame.draw.polygon(s, col("red"), [(x, 158), (x + 10, 158), (x + 20, 166), (x + 10, 166)])
            panel(s, (40, 120, 240, 34), fill="black", border="red")
            draw_text(s, "WARNING!!", W // 2, 124, "red" if int(t * 6) % 2 else "yellow", 2, align="center",
                      outline="ink")
            draw_text(s, f"{st['boss']['name']} WANTS THE RUG!", W // 2, 142, "white", align="center", shadow=None)
            return
        if k == "bonus":
            panel(s, (40, 78, 240, 62), fill="ink", border="yellow")
            title = "BONUS STAGE"
            for i, ch in enumerate(title):
                draw_text(s, ch, W // 2 - text_width(title, 2) // 2 + i * 12, 84 + int(math.sin(t * 8 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            poms = st["bonus"] == "poms"
            draw_text(s, "POM-POM ROUND-UP!" if poms else "FISH FEAST!", W // 2, 104, "yellow", align="center")
            draw_text(s, "WRAP UP THE POM-POMS!" if poms else "SCOOP UP ALL THE TREATS!", W // 2, 115, "white",
                      align="center", shadow=None)
            draw_text(s, "NOTHING CAN HURT YOU HERE", W // 2, 126, "mint", align="center", shadow=None)
            return
        h = 70 if st["new"] else 60
        panel(s, (34, 74, 252, h), fill="ink", border=self.theme[4])
        draw_text(s, f"STAGE {self.n}", W // 2, 80, "yellow", 2, align="center", outline="ink", shadow=None)
        draw_text(s, self.theme[0], W // 2, 98, "lavender", align="center", shadow=None)
        draw_text(s, f"CLAIM {st['target']}% OF THE RUG", W // 2, 109, "white", align="center", shadow=None)
        s.blit(sprite("yw_kumo", A.K_BLINK if int(t * 2) % 5 == 0 else A.K_IDLE), (44, 112))
        draw_text(s, f'"{st["quip"]}"', W // 2 + 8, 121, "mint", align="center", shadow=None)
        if st["new"]:
            draw_text(s, st["new"], W // 2, 132, "lime" if int(t * 4) % 2 else "yellow", align="center", shadow=None)

    def draw_caption(self, s, t):
        name = self.st["pic"]["name"]
        txt = f"IT'S {name}!" if self.st["kind"] != "boss" else f"{name} IS SAFE!"
        if self.golden:
            txt = f"GOLDEN {name}!"
        w = text_width(txt) + 16
        panel(s, (W // 2 - w // 2, FY + 4, w, 14), fill="cream", border="choco", radius=3)
        draw_text(s, txt, W // 2, FY + 8, "choco", align="center", shadow=None)
        draw_text(s, f"KUMO'S FRIEND #{self.friends}", W // 2, FY + 21, "white", align="center", shadow="ink")

    def draw_tally(self, s, t):
        rows = self.tally
        h = 22 + len(rows) * 9
        y0 = H - 4 - h
        panel(s, (60, y0, 200, h), fill="ink", border="mint")
        head = {"boss": "BOSS CLEAR!", "bonus": "BONUS OVER!"}.get(self.st["kind"], f"STAGE {self.n} CLEAR!")
        draw_text(s, head, W // 2, y0 + 4, "mint", align="center", shadow=None)
        for i, (label, v, shown) in enumerate(rows):
            if i > self.tally_i:
                break
            y = y0 + 15 + i * 9
            draw_text(s, label, 68, y, "white" if v else "gray", shadow=None)
            draw_text(s, f"{int(shown)}", 252, y, "yellow" if v else "darkgray", align="right", shadow=None)
        if self.tally_i >= len(rows) and int(t * 3) % 2:
            s.blit(sprite("yw_kumo", A.K_HAPPY), (W // 2 - 7, y0 - 14))


# ----------------------------------------------------------------------------- carousel preview + GIF bot
_PREVIEW = {}
PREVIEW_PIC = {"name": "KUMO", "bg": "sky", "bg2": "white", "pat": 1, "pose": 0, "fur": "orange", "fur2": "peach",
               "mark": 1, "eye": "lime", "mood": 0, "acc": 1, "accc": "hotpink", "prop": 0, "propc": "red",
               "cush": "purple", "x": 0}


def preview(s, t):
    w, h = s.get_size()
    pic = _PREVIEW.get("pic")
    if pic is None:
        big = pygame.Surface((PW, PH))
        A.draw_picture(big, PREVIEW_PIC)
        pic = _PREVIEW["pic"] = big.subsurface((PW // 2 - 56, 22, 112, 74)).copy()
        rug = _PREVIEW["rug"] = pygame.Surface((112, 74))
        A.bg_pattern(rug, "brown", "choco", 2, 0, 0, 112, 74)
    s.blit(_PREVIEW["rug"], (0, 0))
    cyc = t % 6.0
    rx = 14 + int(cyc / 1.2) * 18                # claimed so far: columns left of rx
    s.blit(pic, (0, 0), (0, 0, rx, h))
    for y in range(0, h, 2):
        s.fill(col("hotpink" if (y // 2) % 2 else "pink"), (rx, y, 2, 2))
    ph = (cyc % 1.2) / 1.2                       # weaving the next strip
    ky = int(ph * (h - 4)) + 2
    lx = rx + 16
    for y in range(0, ky, 2):
        s.fill(col("white" if (y // 4) % 2 else "hotpink"), (lx, y, 2, 2))
    s.fill(col("hotpink"), (rx, 0, 18, 2))
    s.blit(sprite("yw_kumo", A.K_WALK1 if int(t * 10) % 2 else A.K_WALK2), (lx - 7, ky - 10))
    fx = w - 18 + math.sin(t * 2.3) * 10
    fy = h / 2 + math.sin(t * 3.1) * 22
    A.draw_fluff(s, fx, fy, 6, t)


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys. Takes rectangular bites out of the rug."""
    mem = {"plan": [], "seg": 0, "moved": 0, "pos": None, "still": 0, "mode": "", "wove": False}
    opposite = {"left": "right", "right": "left", "up": "down", "down": "up"}

    def inward(sc):
        opts = []
        for name, (dx, dy) in DIRS.items():
            nx, ny = sc.kx + dx, sc.ky + dy
            if 0 <= nx < GW and 0 <= ny < GH and sc.grid[ny * GW + nx] == OPEN:
                opts.append(name)
        return opts

    def replan(sc):
        ins = inward(sc)
        mem["seg"] = mem["moved"] = mem["still"] = 0
        mem["wove"] = False
        if ins:
            d = random.choice(ins)
            side = random.choice([k for k in DIRS if k not in (d, opposite[d])])
            mem["plan"] = [(d, random.randint(8, 22)), (side, random.randint(10, 34)), (opposite[d], 999)]
            mem["mode"] = "bite"
        else:
            mem["plan"] = [(random.choice(DIR_ORDER), random.randint(6, 30))]
            mem["mode"] = "walk"

    def f(frame):
        sc = scene
        keys = set()
        if sc.overlay is not None:
            if frame % 20 == 0:
                keys.add("right" if frame % 40 else "a")
            return keys
        if sc.state != "play":
            mem["plan"] = []
            if sc.state in ("intro", "reveal", "tally") and frame % 30 == 0:
                keys.add("a")
            return keys
        pos = (sc.kx, sc.ky)
        if pos != mem["pos"]:
            mem["pos"] = pos
            mem["moved"] += 1
            mem["still"] = 0
        else:
            mem["still"] += 1
        if sc.weaving:
            mem["wove"] = True
        elif (not mem["plan"] or mem["wove"] or (mem["mode"] == "walk" and mem["moved"] >= mem["plan"][0][1])
              or mem["still"] > 12):
            replan(sc)
        d, n = mem["plan"][mem["seg"]]
        if sc.weaving and mem["moved"] >= n and mem["seg"] < len(mem["plan"]) - 1:
            mem["seg"] += 1
            mem["moved"] = 0
            d, n = mem["plan"][mem["seg"]]
        if mem["still"] > 20 and sc.weaving:           # blocked: try turning
            d = random.choice([k for k in DIR_ORDER if k != d])
            mem["plan"][mem["seg"]] = (d, 999)
            mem["still"] = 0
        keys.add(d)
        if sc.weaving and (frame // 120) % 3 == 0:
            keys.add("a")
        return keys
    return f
