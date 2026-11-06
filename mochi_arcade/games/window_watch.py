"""WINDOW WATCH - Maru, a very round cat on the windowsill, guards the fishbowls (original game).

Aim the paw cursor and swat: the PAW PUFF ring catches whatever falls or flies in through the window, and every
catch pops into a smaller ring that can chain-catch its neighbours. Swats use paw energy, which refills by itself;
the MEOW SHOUT clears the whole sky. 200 stages through 20 skies (window_watch_stages.py), a boss on every 10th
stage (window_watch_boss.py), a bonus stage on every x5 and upgrade cards after bosses and bonus stages.
The iOS port (ios/MochiArcade/Games/WindowWatch*.swift) mirrors this file and reads the campaign from EXPORT;
on touch screens the player taps right where to swat.
"""
import math
import random

import pygame

from mochi_arcade import music
from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, ease_out, rainbow
from mochi_arcade.games import DIFF
from mochi_arcade.games import window_watch_art as art
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.games.window_watch_boss import Boss
from mochi_arcade.games.window_watch_stages import CAMPAIGN, KINDS, SILL, SLOTS, THEMES, TOPY, TREASURES
from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

HOWTO = [
    "ARROWS      MOVE THE PAW",
    "Z / SPACE   SWAT! (THE PUFF RING CHAINS)",
    "X / CTRL    MEOW SHOUT - CLEARS THE SKY",
    "",
    "KEEP RAIN, BUGS, DARTS AND CROWS OFF",
    "MARU'S FISHBOWLS. EVERY CATCH POPS AND",
    "CAN CHAIN-CATCH ITS NEIGHBOURS! SWATS",
    "USE PAW ENERGY - IT REFILLS. DON'T SWAT",
    "FISH FOOD. BOSS EVERY 10TH STAGE.",
    "ENTER / ESC  PAUSE",
]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["left", "right", "up", "down", "a", "a", "b"]

# ----------------------------------------------------------------------------- original songs
music.SONGS.update({
    # "Windowsill Shuffle" - day skies (D major)
    "ww_sill": {"bpm": 138, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "D5:8 F#5:8 A5:8 F#5:8 B5:4 A5:4  G5:8 F#5:8 E5:8 D5:8 E5:4 A4:4 "
            "D5:8 F#5:8 A5:8 D6:8 C#6:4 B5:8 A5:8  B5:8 A5:8 G5:8 E5:8 F#5:2 "
            "G5:8 B5:8 D6:8 B5:8 A5:4 F#5:4  E5:8 G5:8 B5:8 G5:8 F#5:4 D5:4 "
            "E5:8 F#5:8 G5:8 A5:8 B5:8 C#6:8 D6:4  A5:8 F#5:8 E5:8 C#5:8 D5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": music._bass(["D", "E", "D", "B", "G", "E", "A", "D"])},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, music.BEAT)},
    ]},
    # "Moonlit Whiskers" - night skies (A minor, slower)
    "ww_moon": {"bpm": 116, "gain": 0.75, "channels": [
        {"wave": "square", "duty": 0.5, "vol": 0.2, "decay": 0.5, "notes":
            "A4:8 C5:8 E5:8 A5:8 G5:4 E5:4  F5:8 E5:8 D5:8 C5:8 D5:4 E5:4 "
            "C5:8 E5:8 G5:8 C6:8 B5:4 G5:4  A5:8 G5:8 E5:8 D5:8 E5:2 "
            "F5:8 A5:8 C6:8 A5:8 G5:4 E5:4  D5:8 F5:8 A5:8 F5:8 E5:4 C5:4 "
            "B4:8 D5:8 F5:8 G#5:8 A5:4 B5:4  C6:8 B5:8 G#5:8 E5:8 A5:2"},
        {"wave": "triangle", "vol": 0.4, "gate": 0.7, "notes": music._bass(["A", "F", "C", "E", "F", "D", "E", "A"], "4")},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, music.SOFT)},
    ]},
})

EXPORT = {"stages": CAMPAIGN, "themes": THEMES, "kinds": KINDS, "treasures": TREASURES, "slots": list(SLOTS)}

CUR_X0, CUR_X1, CUR_Y0, CUR_Y1 = 6, W - 6, 28, 168
LIFE_AT = [30000, 80000, 160000, 300000]          # then every 200000
LINEAR = ("drop", "mini", "dart", "hail", "star", "orb", "feather")
SWAY = ("leaf", "bug", "seed", "food", "bubble", "puff", "cap", "treat")
WIND_AFF = {"leaf": 1.0, "seed": 1.0, "food": 0.8, "cap": 0.6, "bubble": 0.7, "puff": 0.9, "drop": 0.45,
            "bug": 0.3, "snow": 0.3, "hail": 0.25, "mini": 0.5, "moth": 0.3, "feather": 0.6}
POWERS = {"N": ("lime", "CATNIP FRENZY!", "FREE BIG SWATS"), "T": ("orange", "FISH TREAT!", "+1 MEOW"),
          "S": ("sky", "SNOOZY SKY", "EVERYTHING SLOWS"), "H": ("pink", "FRESH WATER!", "BOWLS REFILLED"),
          "$": ("yellow", "LUCKY COIN!", None)}
MARU_LINES = ["MARU IS ON WATCH!", "MARU: NOT MY FISHIES!", "MARU WIGGLES... READY!", "MARU: MRRP!",
              "MARU STRETCHES HER PAWS", "MARU: THE SKY LOOKS SNEAKY", "MARU FLUFFS UP!", "MARU: PURR... FOCUS."]
BONUS_SUB = {"treats": "SWATS ARE FREE - CATCH THEM ALL!", "bubbles": "POP THE PARTY BUBBLES!",
             "fireflies": "CHAIN THE FIREFLIES!"}


# ----------------------------------------------------------------------------- upgrade cards
def _icon_paw(s, cx, cy, t):
    pygame.draw.circle(s, col("white"), (cx, cy), 6 + int(math.sin(t * 4) * 2), 1)
    s.blit(sprite("ww_paw"), (cx - 4, cy - 4))


def _icon_quick(s, cx, cy, t):
    for i in range(4):
        on = i <= int(t * 4) % 5
        s.blit(sprite("ww_pawicon", remap=None if on else {"w": "d"}), (cx - 10 + i * 5, cy - 2))


def _icon_stamina(s, cx, cy, t):
    for i in range(3):
        s.blit(sprite("ww_pawicon", remap={"w": "l"} if i == 2 and int(t * 3) % 2 else None), (cx - 2, cy - 7 + i * 5))


def _icon_chain(s, cx, cy, t):
    for i in range(3):
        pygame.draw.circle(s, col(("hotpink", "pink", "peach")[i]), (cx - 5 + i * 5, cy + (1 if i % 2 else -1) * 2),
                           3 + (1 if int(t * 4) % 3 == i else 0), 1)


def _icon_meow(s, cx, cy, t):
    for i in range(3):
        r = 3 + i * 3 + int(t * 6) % 3
        pygame.draw.circle(s, col("orange"), (cx, cy), r, 1)
    s.fill(col("white"), (cx - 1, cy - 1, 3, 3))


def _icon_glass(s, cx, cy, t):
    pygame.draw.circle(s, col("sky"), (cx, cy + 1), 5)
    art.disc_below(s, cx, cy + 1, 4, cy + 1, "blue")
    pygame.draw.circle(s, col("mint" if int(t * 4) % 2 else "white"), (cx, cy), 9, 1)


def _icon_whisker(s, cx, cy, t):
    for side in (-1, 1):
        for k in (-2, 0, 2):
            s.fill(col("white"), (cx + (2 if side > 0 else -8), cy + k + (k // 2) * side, 6, 1))
    s.fill(col("pink"), (cx - 1, cy - 1, 3, 2))


def _icon_calm(s, cx, cy, t):
    s.blit(sprite("ww_drop"), (cx - 3, cy - 6 + int(t * 3) % 4))
    for i in range(3):
        s.fill(col("teal"), (cx - 6 + i * 6, cy + 6, 3, 1))


def _icon_luck(s, cx, cy, t):
    w = max(1, int(abs(math.cos(t * 3)) * 5))
    pygame.draw.ellipse(s, col("orange"), (cx - w, cy - 5, w * 2 + 1, 11))
    pygame.draw.ellipse(s, col("yellow"), (cx - w + 1, cy - 4, max(1, w * 2 - 1), 9))


def _icon_fever(s, cx, cy, t):
    for i in range(3):
        pygame.draw.circle(s, col(rainbow(i, t)), (cx - 4 + i * 4, cy + 1 - (i % 2) * 3), 2)


UPGRADES = [
    Upgrade("paw", "BIG PAW", "A WIDER|SWAT RING", "white", _icon_paw, 4),
    Upgrade("quick", "QUICK PAWS", "PAW ENERGY|REFILLS|FASTER", "mint", _icon_quick, 3),
    Upgrade("stamina", "MORE PAWS", "+1 MAX|PAW ENERGY", "lime", _icon_stamina, 3),
    Upgrade("chain", "CHAIN PURR", "BIGGER|CHAIN RINGS", "hotpink", _icon_chain, 3),
    Upgrade("meow", "LOUD MEOW", "+1 MEOW NOW|+1 MEOW|STOCK", "orange", _icon_meow, 3),
    Upgrade("glass", "BUBBLE GUARD", "A SHIELD ON|EVERY BOWL|EACH STAGE", "sky", _icon_glass, 2),
    Upgrade("whisker", "WHISKER SENSE", "SWATS SNAP|TO THINGS|NEARBY", "lavender", _icon_whisker, 3),
    Upgrade("calm", "CALM SKY", "THINGS FALL|A BIT|SLOWER", "teal", _icon_calm, 3),
    Upgrade("luck", "LUCKY CAT", "MORE GIFTS|AND|JACKPOTS", "yellow", _icon_luck, 3),
    Upgrade("fever", "FEVER PURR", "FEVER FILLS|FASTER AND|LASTS LONGER", "pink", _icon_fever, 3),
    Upgrade("life", "EXTRA LIFE", "+1 LIFE|RIGHT NOW", "hotpink", "heart", 5),
]


# ----------------------------------------------------------------------------- objects
class Thing:
    """Anything that falls or flies in (threats, gifts, fish food, bonus treats)."""

    def __init__(self, uid, k, x, y, tg, v, p, q):
        r, pts, hp, _, harm = KINDS[k]
        self.id, self.k = uid, k
        self.x, self.y = float(x), float(y)
        self.bx, self.by = float(x), float(y)      # path point the sway is added to
        self.vx = self.vy = 0.0
        self.v, self.p, self.q = v, p, q
        self.tg = tg
        self.r, self.pts, self.hp, self.harm = r, pts, hp, harm
        self.age = 0.0
        self.mode = 0
        self.mt = 0.0
        self.flash = 0.0
        self.dead = False
        self.side = 1
        self.letter = ""


class Treasure:
    def __init__(self, kind, x, shield):
        hw, top, hp = TREASURES[kind]
        self.kind, self.x, self.hw, self.top = kind, float(x), hw, top
        self.hp = self.maxhp = hp
        self.shield = shield
        self.flash = 0.0
        self.wobble = 0.0


class Group:
    """One swat and every chain it set off."""

    def __init__(self):
        self.count = 0


class Ring:
    def __init__(self, x, y, rmax, depth, g, kind, dur, hold):
        self.x, self.y, self.rmax, self.depth, self.g, self.kind = x, y, rmax, depth, g, kind
        self.dur, self.hold = dur, hold
        self.age = 0.0
        self.r = 0.0
        self.hits = set()
        self.boss_hit = False
        self.fever = False


def tri(x):
    return 2 * abs(2 * (x - math.floor(x + 0.5))) - 1


def pick_weighted(opts, weights):
    total = sum(weights)
    r = random.uniform(0, total)
    for o, w in zip(opts, weights):
        r -= w
        if r <= 0 and w > 0:
            return o
    return opts[-1]


# ----------------------------------------------------------------------------- the game
class WindowWatch(GameScene):
    @property
    def music(self):
        return self.song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.diff_speed = SPEED.get(d, 1.0)
        self.lives = LIVES.get(d, 3)
        self.levels = {}
        self.hype.COMBO_TIME = 2.6
        self.hype.combo_y = 30
        self.cx, self.cy = W / 2, 110.0
        self.chold = 0.0
        self.mx = W / 2
        self.walking = False
        self.happy_t = self.hurt_t = self.meow_t = self.tired_t = self.swat_t = 0.0
        self.swat_side = 1
        self.meows = 2
        self.energy = 4.0
        self.swat_cd = 0.0
        self.life_i = 0
        self.uid = 0
        self.picks_left = 0
        self.pick_title = "POWER UP!"
        self.next_n = None
        self.was_fever = False
        self.lightning = 0.0
        self.gust_t = 0.0
        self.gust_dir = 1
        self.tapped = self.tapped_now = False
        start = max(1, min(STAGES, int(opt.get("stage", opt.get("start", 1)))))
        self.start_stage(start)
        if start > 10:         # starting from a checkpoint: catch up on some upgrades first
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

    def emax(self):
        return 4 + self.lv("stamina")

    def meow_max(self):
        return 3 + self.lv("meow")

    def regen(self):
        return 0.6 * 0.82 ** self.lv("quick")

    def free_swats(self):
        return self.frenzy_t > 0 or self.hype.fever_on or self.st["kind"] == "bonus"

    def swat_r(self):
        r = 13 + 3 * self.lv("paw")
        if self.frenzy_t > 0:
            r = r * 1.4
        if self.hype.fever_on:
            r = r * 1.25
        return r

    def chain_r(self):
        return 9 + 2 * self.lv("chain") + (2 if self.hype.fever_on else 0)

    def fever_gain(self):
        return 0.03 * (1 + 0.35 * self.lv("fever"))

    def speed_mul(self):
        return self.diff_speed * (1 - 0.07 * self.lv("calm"))

    def song(self):
        k = self.st["kind"]
        return "boss" if k == "boss" else "bonus" if k == "bonus" else self.theme[5]

    def nearest_slot(self, x):
        best, bd = 0, 1e9
        for i in range(3):
            d = abs(SLOTS[i] - x)
            if d < bd:
                best, bd = i, d
        return best

    def alive_target(self, tg):
        """tg, or the nearest treasure that still has water."""
        if self.treasures[tg].hp > 0:
            return tg
        best, bd = tg, 1e9
        for i, tr in enumerate(self.treasures):
            if tr.hp > 0 and abs(tr.x - self.treasures[tg].x) < bd:
                best, bd = i, abs(tr.x - self.treasures[tg].x)
        return best

    def aim(self, th, speed, ax=None):
        tr = self.treasures[th.tg]
        tx = tr.x if ax is None else ax
        ty = tr.top + 4
        dx, dy = tx - th.bx, ty - th.by
        d = math.hypot(dx, dy) or 1.0
        th.vx, th.vy = dx / d * speed, dy / d * speed

    # ---------------------------------------------------------------- stages
    def start_stage(self, n):
        self.n = n
        st = self.st = CAMPAIGN[n - 1]
        self.tier = st["tier"]
        self.theme = THEMES[st["theme"]]
        self.reached(n)
        self.sky = art.make_sky(self.theme, st["theme"])
        self.treasures = [Treasure(k, SLOTS[i], self.lv("glass")) for i, k in enumerate(st["treasures"])]
        self.events = st["events"]
        self.ei = 0
        self.things, self.rings, self.stamps = [], [], []
        self.boss = Boss(self, st["boss"]) if st["kind"] == "boss" else None
        self.stime = 0.0
        self.wind_now = 0.0
        self.frenzy_t = self.snooze_t = 0.0
        self.gust_t = 0.0
        self.lightning = 0.0
        self.splashed = False
        self.wasted = 0
        self.caught = 0
        self.best_chain = 0
        harm = [e for e in self.events if KINDS[e[1]][4]]
        self.total = len(harm) if st["kind"] != "bonus" else len(self.events)
        self.bonus_left = float(st["time"])
        self.energy = float(self.emax())
        last = self.events[-1][0] if self.events else 10.0
        self.gold_at = -1.0
        if st["kind"] == "normal" and self.hype.lucky(0.025 + 0.012 * self.lv("luck")):
            self.gold_at = random.uniform(0.3, 0.75) * last
        self.state = "intro"
        self.state_t = 0.0
        self.intro_len = 3.0 if self.boss else 2.4
        self.tally = []
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.was_fever = False
        self.app.audio.music(self.song())
        self.app.audio.play("warning" if self.boss else "stage")
        if self.boss:
            self.hype.flash("red", 0.3)

    # ---------------------------------------------------------------- spawning
    def spawn(self, k, x, y, tg, v, p=0.0, q=0.0, ax=None):
        self.uid += 1
        th = Thing(self.uid, k, x, y, tg, v * self.speed_mul(), p, q)
        th.tg = self.alive_target(tg)
        th.side = 1 if x < W / 2 else -1
        if k in LINEAR or k in ("snow", "leaf", "bug", "seed", "food", "bubble", "puff"):
            self.aim(th, th.v, ax)
        elif k in ("cap", "treat"):
            th.vy = th.v
        elif k == "rocket":
            th.vy = -th.v
        elif k == "gold":
            th.side = 1 if p >= 0 else -1
        if k == "cap":
            th.letter = self.roll_power()
        self.things.append(th)
        return th

    def spawn_event(self, e):
        t, k, x, y, tg, v, p, q = e
        self.spawn(k, x, y, tg, v, p, q)

    def spark(self, x, y, tg, off):
        """A firework spark on a falling arc that lands on treasure tg (off = miss by that many pixels)."""
        g = 70 * self.st["speed"] * self.speed_mul()
        tr = self.treasures[tg]
        tx, ty = tr.x + off, tr.top + 4
        vy0 = -random.uniform(20, 50)
        dy = max(4.0, ty - y)
        tt = (-vy0 + math.sqrt(vy0 * vy0 + 2 * g * dy)) / g
        th = self.spawn("spark", x, y, tg, 1.0)
        th.vx, th.vy = (tx - x) / tt, vy0
        th.p = g
        return th

    def roll_power(self):
        hurt = any(tr.hp < tr.maxhp for tr in self.treasures)
        return pick_weighted(["N", "T", "S", "H", "$"], [3, 2, 2, 3 if hurt else 1, 2 + self.lv("luck")])

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        self.tapped_now = self.tapped
        self.tapped = False
        self.move_cursor(dt)
        self.update_maru(dt)
        for tr in self.treasures:
            tr.flash = max(0.0, tr.flash - dt)
            tr.wobble = max(0.0, tr.wobble - dt)
        self.lightning = max(0.0, self.lightning - dt)
        s = self.state
        if s == "intro":
            if self.boss:
                self.boss.update(dt)
            if self.state_t > self.intro_len or (self.state_t > 0.5 and (self.app.input.hit("a") or self.tapped_now)):
                self.state = "play"
                self.state_t = 0.0
                if self.boss:
                    self.boss.state = "fight"
        elif s == "play":
            self.play(dt)
        elif s == "clear":
            self.update_rings(dt)
            self.update_stamps(dt)
            if self.boss:
                self.boss.update(dt)
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
        elif s == "oops":
            self.update_stamps(dt)
            if self.state_t > 2.4:
                self.start_stage(self.n)

    def on_pick(self, uid):
        if uid:
            self.levels[uid] = self.lv(uid) + 1
            u = next(x for x in UPGRADES if x.id == uid)
            self.hype.banner(u.name, f"LEVEL {self.levels[uid]}", color=u.color, dur=1.2, scale=1)
            if uid == "life":
                self.lives += 1
                self.app.audio.play("extra")
            elif uid == "meow":
                self.meows = min(self.meow_max(), self.meows + 1)
            elif uid == "glass":
                for tr in self.treasures:
                    tr.shield = self.lv("glass")
            elif uid == "stamina":
                self.energy = float(self.emax())

    def tap(self, x, y):
        """Touch (the iOS port's onTap): swat right where the finger lands. Used by tests on desktop."""
        self.cx = max(CUR_X0, min(CUR_X1, x))
        self.cy = max(CUR_Y0, min(CUR_Y1, y))
        self.tapped = True
        if self.state == "play":
            self.swat()

    def move_cursor(self, dt):
        inp = self.app.input
        dx = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        dy = (1 if inp.down("down") else 0) - (1 if inp.down("up") else 0)
        if dx or dy:
            self.chold += dt
        else:
            self.chold = 0.0
        v = 120 + min(1.0, self.chold / 0.25) * 120
        if dx and dy:
            v *= 0.75
        self.cx = max(CUR_X0, min(CUR_X1, self.cx + dx * v * dt))
        self.cy = max(CUR_Y0, min(CUR_Y1, self.cy + dy * v * dt))

    def update_maru(self, dt):
        for k in ("happy_t", "hurt_t", "meow_t", "tired_t", "swat_t"):
            setattr(self, k, max(0.0, getattr(self, k) - dt))
        tx = max(20.0, min(W - 20.0, self.cx))
        d = tx - self.mx
        self.walking = abs(d) > 3 and self.meow_t <= 0
        if self.walking:
            self.mx += max(-70 * dt, min(70 * dt, d))

    def play(self, dt):
        inp, st = self.app.input, self.st
        self.stime += dt
        self.swat_cd = max(0.0, self.swat_cd - dt)
        self.frenzy_t = max(0.0, self.frenzy_t - dt)
        self.snooze_t = max(0.0, self.snooze_t - dt)
        self.gust_t = max(0.0, self.gust_t - dt)
        if self.energy < self.emax():
            self.energy = min(float(self.emax()), self.energy + dt / self.regen())
        self.wind_now = st["wind"] * (0.6 + 0.4 * math.sin(self.stime * 0.5))
        if self.gust_t > 0:
            self.wind_now += self.gust_dir * 55
        if inp.hit("a"):
            self.swat()
        if inp.hit("b"):
            self.meow()
        while self.ei < len(self.events) and self.events[self.ei][0] <= self.stime:
            self.spawn_event(self.events[self.ei])
            self.ei += 1
        if 0 < self.gold_at <= self.stime:
            self.gold_at = -1.0
            side = random.choice((-1, 1))
            self.spawn("gold", -10.0 if side > 0 else 330.0, random.uniform(40, 90), 0, 78.0, float(side), 0.0)
            self.hype.banner("GOLDEN FISH!", "SWAT IT!", color="yellow", dur=1.2, scale=1, sound="coin")
        if self.boss:
            self.boss.update(dt)
            if self.boss.state == "dead" and self.state == "play":
                self.boss_defeated()
        tdt = dt * (0.5 if self.snooze_t > 0 else 1.0)
        for th in list(self.things):
            if self.state != "play":
                break
            if not th.dead:
                self.move_thing(th, tdt)
        self.update_rings(dt)
        self.things = [th for th in self.things if not th.dead]
        self.update_stamps(dt)
        self.check_life()
        if self.hype.fever_on and not self.was_fever:
            self.hype.fever_t += 1.5 * self.lv("fever")
            self.app.audio.music("fever")
        elif self.was_fever and not self.hype.fever_on:
            self.app.audio.music(self.song())
        self.was_fever = self.hype.fever_on
        if self.state != "play":
            return
        k = st["kind"]
        if k == "bonus":
            self.bonus_left -= dt
            if self.bonus_left <= 0 or (self.ei >= len(self.events) and not self.things):
                if self.bonus_left <= 0:
                    self.hype.banner("TIME UP!", color="yellow", dur=1.2)
                self.stage_clear()
        elif k == "normal" and self.ei >= len(self.events) and not any(th.harm for th in self.things):
            self.stage_clear()

    # ---------------------------------------------------------------- things
    def move_thing(self, th, dt):
        th.age += dt
        th.flash = max(0.0, th.flash - dt)
        k = th.k
        w = self.wind_now * WIND_AFF.get(k, 0.15)
        if k in LINEAR:
            th.x += (th.vx + w) * dt
            th.y += th.vy * dt
        elif k == "snow":
            f = min(2.2, 1 + th.age * 0.45)
            th.x += (th.vx * f + w) * dt
            th.y += th.vy * f * dt
        elif k in SWAY:
            th.bx += (th.vx + w) * dt
            th.by += th.vy * dt
            if k == "leaf":
                off = th.p * math.sin(th.age * 2.2 + th.q)
            elif k == "bug":
                off = th.p * tri(th.age * 1.3 + th.q)
            elif k in ("bubble", "puff"):
                off = 5 * math.sin(th.age * 1.2 + th.q)
            elif k == "treat":
                off = 0.0
            else:
                off = th.p * math.sin(th.age * 1.6 + th.q)
            sp = math.hypot(th.vx, th.vy) or 1.0
            th.x = th.bx - th.vy / sp * off
            th.y = th.by + th.vx / sp * off
            if k in ("bubble", "puff") and th.y >= th.p:
                self.split(th)
                return
        elif k == "crow":
            if th.mode == 0:
                th.x += th.side * th.v * dt
                th.y += math.sin(th.age * 5) * 8 * dt
                th.vx = th.side * th.v
                if (th.side > 0 and th.x >= th.p) or (th.side < 0 and th.x <= th.p):
                    th.mode, th.mt = 1, 0.0
                    self.app.audio.play("back")
            elif th.mode == 1:
                th.mt += dt
                th.y -= 8 * dt
                if th.mt >= 0.5:
                    th.mode = 2
                    th.bx, th.by = th.x, th.y
                    th.tg = self.alive_target(th.tg)
                    self.aim(th, th.v * 1.9)
            else:
                th.x += th.vx * dt
                th.y += th.vy * dt
        elif k == "plane":
            if th.mode == 0:
                th.x += th.side * th.v * dt
                th.y += (math.sin(th.age * 3) * 10 + 6) * dt
                th.vx, th.vy = th.side * th.v, math.cos(th.age * 3) * 30
                if (th.side > 0 and th.x >= th.p) or (th.side < 0 and th.x <= th.p):
                    th.mode, th.mt = 1, 0.0
                    th.bx, th.by = th.x, th.y - 14
            elif th.mode == 1:
                th.mt += dt
                a = th.mt * 6.0
                th.x = th.bx + math.sin(a) * 14 * th.side
                th.y = th.by + math.cos(a) * 14
                th.vx, th.vy = math.cos(a) * 84 * th.side, -math.sin(a) * 84
                if a >= math.tau:
                    th.mode = 2
                    th.bx, th.by = th.x, th.y
                    th.tg = self.alive_target(th.tg)
                    self.aim(th, th.v * 1.5)
            else:
                th.x += th.vx * dt
                th.y += th.vy * dt
        elif k == "moth":
            if th.mode == 0:
                th.mt += dt
                dx, dy = self.cx - th.x, min(self.cy, 140.0) - th.y
                d = math.hypot(dx, dy) or 1.0
                sp = th.v * 0.8
                f = min(1.0, dt * 2)
                th.vx += (dx / d * sp - th.vx) * f
                th.vy += (dy / d * sp - th.vy) * f
                th.x += th.vx * dt + math.cos(th.age * 7) * 20 * dt
                th.y += th.vy * dt + math.sin(th.age * 11) * 14 * dt
                if th.mt >= th.p:
                    th.mode = 1
                    th.bx, th.by = th.x, th.y
                    th.tg = self.alive_target(th.tg)
                    self.aim(th, th.v * 1.5)
            else:
                th.x += th.vx * dt
                th.y += th.vy * dt
        elif k == "rocket":
            th.y += th.vy * dt
            if th.y <= th.p:
                self.burst(th)
                return
        elif k == "spark":
            th.vy += th.p * dt
            th.x += th.vx * dt
            th.y += th.vy * dt
        elif k == "gold":
            th.x += th.side * th.v * dt
            th.y = th.by + math.sin(th.age * 5) * 14
        elif k == "fly":
            a = th.q + th.age * th.v
            if th.age > 6:
                th.by -= 50 * dt
            else:
                th.bx += math.sin(th.age * 0.7 + th.q) * 10 * dt
            th.x = th.bx + math.cos(a) * th.p
            th.y = th.by + math.sin(a) * th.p * 0.7
        elif k == "rise":
            th.y -= th.v * dt
            th.x = th.bx + math.sin(th.age * 2 + th.q) * th.p
        # landing / leaving
        if th.harm and k != "rocket":
            for i, tr in enumerate(self.treasures):
                if tr.hp > 0 and th.y >= tr.top - 2 and abs(th.x - tr.x) <= tr.hw + th.r:
                    th.dead = True
                    self.hit_treasure(i, th.x, th.y)
                    return
        elif k == "food":
            for tr in self.treasures:
                if th.y >= tr.top - 2 and abs(th.x - tr.x) <= tr.hw + th.r:
                    th.dead = True
                    self.feed(tr, th)
                    return
        if th.y > SILL + 2 and k not in ("rocket", "rise", "fly"):
            th.dead = True
            if th.harm:
                self.parts.burst(th.x, SILL, 4, art.KIND_COLORS[k], 25, 0.3)
        elif th.x < -40 or th.x > W + 40 or th.y < -40 or (k == "rise" and th.y < 26):
            th.dead = True
            if k == "rise":
                self.parts.burst(th.x, th.y, 4, ("white", "sky"), 20, 0.3)

    def split(self, th):
        th.dead = True
        self.app.audio.play("bubble")
        self.parts.burst(th.x, th.y, 8, ("white", "sky"), 40, 0.4)
        sp = self.st["speed"]
        if th.k == "bubble":
            for i in range(3):
                self.spawn("mini", th.x + (i - 1) * 4, th.y, self.alive_target(i), KINDS["mini"][3] * sp)
        else:
            for i in range(5):
                self.spawn("seed", th.x + (i - 2) * 3, th.y, self.alive_target(random.randrange(3)),
                           KINDS["seed"][3] * sp, random.uniform(4, 9), random.uniform(0, 6))

    def burst(self, th):
        th.dead = True
        self.app.audio.play("explode")
        self.parts.burst(th.x, th.y, 16, ("yellow", "hotpink", "white", "mint"), 70, 0.6)
        for i in range(5):
            tg = self.alive_target((th.tg + i) % 3)
            self.spark(th.x, th.y, tg, random.uniform(-28, 28) if i >= 3 else random.uniform(-6, 6))

    def hit_treasure(self, i, x, y):
        tr = self.treasures[i]
        tr.flash = 0.4
        tr.wobble = 0.3
        if tr.shield > 0:
            tr.shield -= 1
            self.floats.add(tr.x, tr.top - 10, "BLOCK!", "mint")
            self.app.audio.play("tin")
            self.parts.burst(x, y, 8, ("mint", "white"), 40, 0.4)
            return
        tr.hp -= 1
        self.splashed = True
        self.hype.break_combo()
        self.hurt_t = 0.8
        self.app.audio.play("hurt")
        self.app.shake(3, 0.3)
        self.parts.burst(tr.x, tr.top + 4, 14, ("sky", "blue", "white"), 70, 0.6)
        self.floats.add(tr.x, tr.top - 10, "SPLASH!", "sky")
        if tr.hp <= 0:
            self.hype.banner("OH NO!", "A BOWL RAN DRY", color="pink", dur=1.0, scale=1)
            if all(t.hp <= 0 for t in self.treasures):
                self.lose_life()

    def boss_hits_treasure(self, i):
        tr = self.treasures[i]
        if tr.hp > 0 or tr.shield > 0:
            self.hit_treasure(i, tr.x, tr.top)

    def feed(self, tr, th):
        if tr.hp <= 0:
            return
        if tr.hp < tr.maxhp:
            tr.hp += 1
            self.floats.add(tr.x, tr.top - 10, "YUM! +WATER", "lime")
        else:
            self.score_at(300, tr.x, tr.top - 10, "lime")
            self.floats.add(tr.x, tr.top - 18, "YUM!", "lime")
        self.app.audio.play("eat")
        self.happy_t = max(self.happy_t, 0.6)
        self.parts.burst(tr.x, tr.top, 8, ("orange", "yellow", "lime"), 30, 0.5)

    # ---------------------------------------------------------------- swats
    def swat(self):
        if self.state != "play" or self.swat_cd > 0:
            return
        x, y = self.cx, self.cy
        if not self.free_swats():
            if self.energy < 1:
                self.swat_cd = 0.2
                self.tired_t = 0.6
                self.app.audio.play("move")
                self.stamps.append([x, y, 0.0, 1])
                return
            self.energy -= 1
        snap = 6 + 5 * self.lv("whisker") if self.lv("whisker") else 0
        if snap:
            best, bd = None, 1e9
            for th in self.things:
                if th.dead or th.k == "food":
                    continue
                d = math.hypot(th.x - x, th.y - y)
                if d < bd:
                    best, bd = th, d
            if best is not None and bd <= self.swat_r() + snap:
                f = min(1.0, snap / max(1.0, bd))
                x += (best.x - x) * f
                y += (best.y - y) * f
        rg = Ring(x, y, self.swat_r(), 0, Group(), "swat", 0.15, 0.08)
        rg.fever = self.hype.fever_on
        self.rings.append(rg)
        self.stamps.append([x, y, 0.0, 0])
        self.swat_cd = 0.1
        self.swat_t = 0.25
        self.swat_side = -1 if x < self.mx else 1
        self.app.audio.play("paddle")

    def meow(self):
        if self.state != "play" or self.meow_t > 0:
            return
        if self.meows <= 0:
            self.floats.add(self.mx, SILL - 30, "NO MEOW LEFT", "gray")
            self.app.audio.play("back")
            return
        self.meows -= 1
        self.meow_t = 1.0
        self.rings.append(Ring(self.mx, SILL - 14, 360, 0, Group(), "meow", 0.8, 0.0))
        self.hype.banner("MEOW!!", color="pink", dur=0.9)
        self.hype.flash("white", 0.25)
        self.app.shake(5, 0.5)
        self.app.audio.play("boom")

    def update_rings(self, dt):
        i = 0
        while i < len(self.rings):
            rg = self.rings[i]
            i += 1
            rg.age += dt
            rg.r = rg.rmax * ease_out(min(1.0, rg.age / rg.dur))
            if rg.age > rg.dur + rg.hold:
                continue
            for th in self.things:
                if th.dead or th.id in rg.hits or (rg.kind == "meow" and th.k == "food"):
                    continue
                dx, dy = th.x - rg.x, th.y - rg.y
                rr = rg.r + th.r
                if dx * dx + dy * dy <= rr * rr:
                    rg.hits.add(th.id)
                    self.catch(th, rg)
            b = self.boss
            if b is not None and not rg.boss_hit and b.hittable():
                dx, dy = b.x - rg.x, b.y - rg.y
                rr = rg.r + b.r
                if dx * dx + dy * dy <= rr * rr:
                    rg.boss_hit = True
                    self.hit_boss(rg)
        self.rings = [rg for rg in self.rings if rg.age < rg.dur + rg.hold + 0.18]

    def update_stamps(self, dt):
        for sp in self.stamps:
            sp[2] += dt
        self.stamps = [sp for sp in self.stamps if sp[2] < 0.35]

    def catch(self, th, rg):
        k = th.k
        if k == "food":
            th.dead = True
            self.wasted += 1
            self.floats.add(th.x, th.y - 8, "OOPS! FOOD", "red")
            self.parts.burst(th.x, th.y, 6, ("orange", "yellow"), 30, 0.4)
            self.app.audio.play("back")
            self.hype.break_combo()
            self.hurt_t = 0.5
            return
        if k == "cap":
            th.dead = True
            self.power(th.letter, th.x, th.y)
            return
        th.hp -= 1
        if th.hp > 0:
            th.flash = 0.12
            th.y -= 4
            th.by -= 4
            self.app.audio.play("tin")
            self.parts.burst(th.x, th.y, 5, ("white", "sky"), 30, 0.3)
            self.floats.add(th.x, th.y - 8, "CRACK!", "white")
            return
        th.dead = True
        g = rg.g
        g.count += 1
        mult = min(8, 1 + rg.depth) if rg.kind != "meow" else 1
        pts = KINDS[k][1] * mult + self.hype.combo_bonus(2)
        if k == "rocket":
            pts += 150
            self.floats.add(th.x, th.y - 16, "DUD!", "orange")
        if pts > 0:
            self.score_at(pts, th.x, th.y - 6, "yellow" if rg.depth == 0 else "peach")
        self.hype.hit(1, fever=self.fever_gain())
        self.caught += 1
        self.parts.burst(th.x, th.y, 8, art.KIND_COLORS[k], 50, 0.5)
        self.app.audio.play("pop")
        if rg.kind != "meow" and rg.depth < 14:
            ch = Ring(th.x, th.y, self.chain_r(), rg.depth + 1, g, "chain", 0.13, 0.05)
            ch.fever = self.hype.fever_on
            self.rings.append(ch)
        if k == "gold":
            self.hype.jackpot(self.factor(5000), "GOLDEN FISH!")
            self.happy_t = 1.5
        if rg.kind != "meow":
            self.chain_news(g, th.x, th.y)

    def chain_news(self, g, x, y):
        c = g.count
        self.best_chain = max(self.best_chain, c)
        h = self.hype
        if c >= 3:
            self.happy_t = max(self.happy_t, 0.5)
        if c == 3:
            self.floats.add(x, y - 16, "CHAIN!", "pink")
        elif c == 5:
            h.banner("5 CHAIN!", color="peach", dur=0.9, scale=1)
        elif c == 8:
            h.banner("8 CHAIN!!", "+1000", color="hotpink", dur=1.2, sound="bonus")
            h.shower(24, "stars")
            h.hitstop(0.06)
            self.score_at(1000)
        elif c == 12:
            h.banner("PURRFECT CHAIN!", "+3000", rainbow=True, dur=1.8, sound="fever")
            h.slowmo(0.4, 0.8)
            h.flash("white", 0.2)
            h.shower(40, "confetti")
            self.score_at(3000)
            self.happy_t = 1.5
        elif c == 16:
            h.jackpot(self.factor(6000), "16 CHAIN!!")

    def hit_boss(self, rg):
        b = self.boss
        dmg = 3 if rg.kind == "meow" else 1
        if b.mode in ("swoop", "dash", "slam"):
            dmg += 1
        died = b.damage(dmg)
        self.hype.hitstop(0.04)
        self.hype.hit(1, fever=self.fever_gain())
        self.app.shake(2, 0.15)
        self.app.audio.play("brick")
        self.parts.burst(b.x, b.y, 10, ("white", "yellow", "pink"), 60, 0.5)
        self.score_at(40 * dmg, b.x, b.y - b.r - 6, "orange")
        if died:
            self.boss_defeated()

    def power(self, letter, x, y):
        c, name, sub = POWERS[letter]
        self.app.audio.play("powerup")
        self.parts.burst(x, y, 14, (c, "white"), 60, 0.6)
        if letter == "N":
            self.frenzy_t = 7.0
        elif letter == "T":
            self.meows = min(self.meow_max(), self.meows + 1)
        elif letter == "S":
            self.snooze_t = 6.0
        elif letter == "H":
            for tr in self.treasures:
                tr.hp = min(tr.maxhp, tr.hp + 1)
                tr.flash = 0.4
        else:
            self.score_at(2000, x, y - 8, "yellow")
            self.hype.shower(20, "coins")
            self.app.audio.play("coin")
        self.hype.banner(name, sub, color=c, dur=1.2, scale=1)
        self.happy_t = 0.8

    def check_life(self):
        i = self.life_i
        target = LIFE_AT[i] if i < len(LIFE_AT) else LIFE_AT[-1] + 200000 * (i - len(LIFE_AT) + 1)
        if self.score >= target:
            self.life_i += 1
            self.lives += 1
            self.hype.banner("BONUS LIFE!", f"{target} POINTS", color="pink", dur=1.4, sound="extra")
            self.hype.shower(16, "hearts")

    def lose_life(self):
        if self.state != "play":
            return
        self.lives -= 1
        self.hype.break_combo()
        self.app.audio.play("die")
        self.app.shake(5, 0.5)
        self.things = []
        self.rings = []
        self.state_t = 0.0
        if self.lives <= 0:
            self.state = "over"
            self.hype.banner("GAME OVER", f"STAGE {self.n}", color="red", dur=3.0)
            self.end_game(False, f"STAGE {self.n}", delay=3.0)
        else:
            self.state = "oops"
            self.hype.banner("ALL DRY!", f"TRY AGAIN - {self.lives} LEFT", color="pink", dur=2.0)

    # ---------------------------------------------------------------- clear / tally
    def stage_clear(self):
        if self.state != "play":
            return
        self.state = "clear"
        self.state_t = 0.0
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        # whatever is still in the sky pops for free
        for th in self.things:
            if not th.dead and th.k not in ("food", "cap"):
                self.parts.burst(th.x, th.y, 6, art.KIND_COLORS[th.k], 40, 0.4)
        self.things = []
        self.hype.slowmo(0.3, 0.8)
        self.app.audio.play("win")
        self.happy_t = 2.0
        if self.st["kind"] == "normal":
            self.hype.banner("STAGE CLEAR!", color="mint", dur=1.4)
            self.hype.shower(30, "confetti")
        self.app.audio.music(None)
        self.was_fever = False

    def boss_defeated(self):
        if self.state != "play":
            return
        g = self.hype
        self.app.audio.play("bossdown")
        g.banner("BOSS DOWN!", self.boss.name, rainbow=True, dur=2.2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(40, "coins")
        self.app.shake(6, 0.6)
        self.score_at(15000, W / 2, 80)
        for th in self.things:
            if th.harm:
                self.score_at(th.pts, th.x, th.y, "peach")
        self.stage_clear()
        self.hype.slowmo(0.3, 1.2)

    def begin_tally(self):
        st, f = self.st, self.factor
        water = sum(max(0, tr.hp) for tr in self.treasures)
        rows = []
        if st["kind"] == "normal":
            rows.append(("STAGE CLEAR", f(1000)))
            rows.append((f"CAUGHT {self.caught}", f(self.caught * 20)))
            rows.append(("WATER LEFT", f(water * 150)))
            rows.append((f"BEST CHAIN {self.best_chain}", f(self.best_chain * 100)))
            rows.append(("NO SPLASH", f(5000) if not self.splashed else 0))
        elif st["kind"] == "boss":
            rows.append(("BOSS BONUS", f(10000 + 2000 * self.tier)))
            rows.append(("WATER LEFT", f(water * 300)))
            rows.append((f"BEST CHAIN {self.best_chain}", f(self.best_chain * 100)))
            rows.append(("NO SPLASH", f(8000) if not self.splashed else 0))
        else:
            rows.append((f"CAUGHT {self.caught}/{self.total}", f(self.caught * 50)))
            rows.append((f"BEST CHAIN {self.best_chain}", f(self.best_chain * 150)))
            rows.append(("ALL CAUGHT!", f(10000) if self.caught >= self.total else 0))
        self.tally = [[label, v, 0.0] for label, v in rows]
        self.tally_i = 0
        self.tally_wait = 0.0
        self.state = "tally"
        self.state_t = 0.0
        if st["kind"] != "bonus" and not self.splashed:
            self.hype.banner("PURRFECT!", "NOT A SINGLE SPLASH", rainbow=True, dur=1.8, sound="fever")
            self.hype.shower(40, "stars")
        elif st["kind"] == "bonus" and self.caught >= self.total:
            self.hype.banner("ALL CAUGHT!", rainbow=True, dur=1.8, sound="fever")

    def update_tally(self, dt):
        skip = self.state_t > 0.3 and (self.app.input.hit("a") or self.tapped_now)
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
            self.hype.banner("ALL CLEAR!!", "MARU SAVED EVERY FISH", rainbow=True, dur=5.0, sound="jackpot")
            self.hype.shower(120, "confetti")
            self.end_game(True, "ALL 200 STAGES!", delay=4.5)
            return
        self.next_n = self.n + 1
        if st["kind"] in ("boss", "bonus"):
            self.meows = min(self.meow_max(), self.meows + 1)
            self.picks_left = 1
            self.pick_title = "BOSS BONUS!" if st["kind"] == "boss" else "SWEET TREAT!"
            self.state = "pick"
        else:
            self.start_stage(self.next_n)

    # ---------------------------------------------------------------- drawing
    def render(self, s):
        t = self.t
        s.blit(self.sky, (0, 0))
        art.draw_sky_fx(s, self.theme, t, self.lightning)
        if self.boss:
            self.boss.draw(s, t)
        art.draw_sill(s, t)
        art.draw_maru(s, self, t)
        for tr in self.treasures:
            art.draw_treasure(s, tr, t)
        deco = self.theme[4]
        for th in self.things:
            art.draw_thing(s, th, t, deco)
        self.draw_rings(s, t)
        self.parts.draw(s)
        self.floats.draw(s)
        art.draw_frame(s, self.theme, t)
        if self.state in ("play", "intro"):
            ready = self.free_swats() or self.energy >= 1
            c = "lime" if self.frenzy_t > 0 else ("yellow" if self.hype.fever_on else "white")
            art.draw_paw_cursor(s, self.cx, self.cy, t, ready, c)
        self.draw_hud(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "tally":
            self.draw_tally(s, t)

    def draw_rings(self, s, t):
        for rg in self.rings:
            r = int(rg.r)
            if r < 1:
                continue
            x, y = int(rg.x), int(rg.y)
            if rg.kind == "meow":
                for i in range(3):
                    if r - i * 5 > 0:
                        pygame.draw.circle(s, col(rainbow(i, t)), (x, y), r - i * 5, 1)
                continue
            faded = rg.age > rg.dur + rg.hold
            if rg.fever:
                c = rainbow(rg.depth, t)
            elif rg.kind == "swat":
                c = "white"
            else:
                c = ("pink", "peach", "hotpink")[rg.depth % 3]
            if faded and int(t * 30) % 2:
                continue
            pygame.draw.circle(s, col(c), (x, y), r, 1)
            if rg.kind == "swat" and not faded and r > 4:
                pygame.draw.circle(s, col("lavender"), (x, y), r - 3, 1)
        for x, y, age, tired in self.stamps:
            if tired:
                if int(age * 20) % 2 == 0:
                    draw_text(s, "PUFF", int(x), int(y) - 14, "gray", align="center", shadow=None)
                continue
            if age < 0.12:
                sp = sprite("ww_paw", scale=2)
                s.blit(sp, (int(x) - 9, int(y) - 9))

    def draw_hud(self, s, t):
        s.fill(col("black"), (0, 0, W, 16))
        draw_text(s, f"{self.score:07d}", 4, 1, "white", shadow=None)
        b = self.boss
        if b is not None and b.state != "dead":
            boss_bar(s, b.name, b.hp, b.maxhp, t, y=2, x=64, w=192)
        else:
            draw_text(s, f"HI {max(self.best, self.score):07d}", 4, 9, "gray", shadow=None)
            if self.st["kind"] == "bonus" and self.state in ("play", "intro"):
                secs = max(0, int(math.ceil(self.bonus_left)))
                draw_text(s, f"TIME {secs:02d}", W // 2, 2, "yellow" if secs > 5 or int(t * 6) % 2 else "red",
                          align="center", shadow=None)
            else:
                draw_text(s, f"STAGE {self.n}", W // 2, 2, "yellow", align="center", shadow=None)
            if self.events and self.st["kind"] != "boss":
                frac = self.ei / len(self.events)
                s.fill(col("darkgray"), (W // 2 - 30, 11, 60, 2))
                s.fill(col("mint"), (W // 2 - 30, 11, int(60 * frac), 2))
        self.hearts(s, W - 54, 1, self.lives)
        x0, y0 = W - 54, 11
        s.fill(col("darkgray"), (x0, y0, 48, 3))
        if self.hype.fever_on:
            for i in range(48):
                s.fill(col(rainbow(i // 6, t)), (x0 + i, y0, 1, 3))
        else:
            s.fill(col("orange"), (x0, y0, int(48 * self.hype.fever), 3))
        # paw energy and meows on the windowsill
        y = SILL + 9
        free = self.free_swats()
        for i in range(self.emax()):
            x = 8 + i * 8
            full = free or i < int(self.energy)
            s.blit(sprite("ww_pawicon", remap=None if full else {"w": "d"}), (x, y))
            if not full and i == int(self.energy):
                s.fill(col("peach"), (x + 1, y + 7, int(5 * (self.energy - int(self.energy))), 1))
        if free and self.st["kind"] != "bonus" and int(t * 4) % 2:
            draw_text(s, "FREE!", 10 + self.emax() * 8, y - 1, "lime", shadow="black")
        draw_text(s, "MEOW", W - 10 - self.meow_max() * 7, y - 1, "orange", align="right", shadow="black")
        for i in range(self.meow_max()):
            c = "orange" if i < self.meows else "brown"
            pygame.draw.circle(s, col("black"), (W - 10 - i * 7, y + 3), 3)
            pygame.draw.circle(s, col(c), (W - 10 - i * 7, y + 3), 2)
        x = W // 2
        items = []
        if self.frenzy_t > 0:
            items.append((f"CATNIP {int(math.ceil(self.frenzy_t))}", "lime", self.frenzy_t))
        if self.snooze_t > 0:
            items.append((f"SNOOZE {int(math.ceil(self.snooze_t))}", "sky", self.snooze_t))
        if abs(self.wind_now) > 8 and self.state == "play":
            items.append(("WIND >>" if self.wind_now > 0 else "<< WIND", "white", 9.0))
        for i, (txt, c, left) in enumerate(items):
            if left > 2 or int(t * 8) % 2:
                draw_text(s, txt, x + i * 64 - (len(items) - 1) * 32, y - 1, c, align="center", shadow="black")

    def draw_intro(self, s, t):
        st = self.st
        k = st["kind"]
        if k == "boss":
            if int(t * 4) % 2:
                for x in range(-20, W + 20, 20):
                    pygame.draw.polygon(s, col("red"), [(x, 96), (x + 10, 96), (x + 20, 104), (x + 10, 104)])
                    pygame.draw.polygon(s, col("red"), [(x, 138), (x + 10, 138), (x + 20, 146), (x + 10, 146)])
            panel(s, (40, 106, 240, 30), fill="black", border="red")
            draw_text(s, "WARNING!!", W // 2, 110, "red" if int(t * 6) % 2 else "yellow", 2, align="center",
                      outline="ink")
            draw_text(s, f"{st['name']} APPROACHES", W // 2, 126, "white", align="center", shadow=None)
            if st["new"]:
                draw_text(s, st["new"], W // 2, 152, "mint", align="center", shadow="black")
            return
        if k == "bonus":
            panel(s, (30, 86, 260, 52), fill="ink", border="yellow")
            title = "BONUS STAGE"
            for i, ch in enumerate(title):
                draw_text(s, ch, W // 2 - text_width(title, 2) // 2 + i * 12, 92 + int(math.sin(t * 8 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            draw_text(s, st["name"], W // 2, 112, "yellow", align="center")
            draw_text(s, BONUS_SUB[st["bonus"]], W // 2, 124, "white", align="center")
            return
        y0 = 86
        h = 72 if st["new"] else 60
        panel(s, (30, y0, 260, h), fill="ink", border="pink")
        draw_text(s, f"STAGE {self.n}", W // 2, y0 + 6, "yellow", 2, align="center", outline="ink", shadow=None)
        draw_text(s, self.theme[0], W // 2, y0 + 25, "lavender", align="center")
        draw_text(s, st["name"], W // 2, y0 + 36, "white", align="center")
        if st["new"]:
            draw_text(s, st["new"], W // 2, y0 + 48, "mint" if int(t * 4) % 2 else "lime", align="center")
        draw_text(s, MARU_LINES[self.n % len(MARU_LINES)], W // 2, y0 + h - 12, "cream", align="center", shadow=None)

    def draw_tally(self, s, t):
        rows = self.tally
        h = 44 + len(rows) * 11
        y0 = 84
        panel(s, (64, y0, 192, h), fill="ink", border="mint")
        head = {"boss": "BOSS CLEAR!", "bonus": "BONUS OVER!"}.get(self.st["kind"], f"STAGE {self.n} CLEAR!")
        draw_text(s, head, W // 2, y0 + 6, "mint", align="center")
        for i, (label, v, shown) in enumerate(rows):
            if i > self.tally_i:
                break
            y = y0 + 20 + i * 11
            draw_text(s, label, 72, y, "white" if v else "gray", shadow=None)
            draw_text(s, f"{int(shown)}", 248, y, "yellow" if v else "darkgray", align="right", shadow=None)
        if self.tally_i >= len(rows):
            line = "MARU PURRS LOUDLY" if not self.splashed else (
                "MARU: THAT WAS CLOSE..." if any(tr.hp < tr.maxhp for tr in self.treasures) else "MARU: PHEW!")
            if self.st["kind"] == "bonus":
                line = "MARU: YUM YUM!"
            draw_text(s, line, W // 2, y0 + h - 22, "cream", align="center", shadow=None)
            if int(t * 3) % 2:
                draw_text(s, "PRESS Z", W // 2, y0 + h - 11, "lavender", align="center", shadow=None)


# ----------------------------------------------------------------------------- bots + carousel
def autopilot(sc, frame):
    """A decent player: chase the most urgent thing, swat when the paw is on it, MEOW in emergencies."""
    keys = set()
    if sc.overlay is not None:
        if frame % 20 == 0:
            keys.add("right" if frame % 40 else "a")
        return keys
    if sc.state != "play":
        if sc.state in ("tally", "intro") and frame % 30 == 0:
            keys.add("a")
        return keys
    best, score = None, -1e9
    for th in sc.things:
        if th.dead or th.k == "food":
            continue
        if th.k == "rocket" and th.y > 168:
            continue
        urgency = th.y + (40 if th.harm else 0) + (60 if th.k in ("cap", "gold") else 0)
        if th.harm:
            tr = sc.treasures[th.tg]
            urgency += 80 - min(80, abs(th.x - tr.x) / 3)
        d = math.hypot(th.x - sc.cx, th.y - sc.cy)
        urgency -= d * 0.35
        if urgency > score:
            best, score = th, urgency
    tx, ty = W / 2, 100.0
    if best is not None:
        tx, ty = best.x + best.vx * 0.12, best.y + best.vy * 0.12
    elif sc.boss is not None and sc.boss.hittable():
        tx, ty = sc.boss.x, sc.boss.y
    dx, dy = tx - sc.cx, ty - sc.cy
    if dx > 3:
        keys.add("right")
    elif dx < -3:
        keys.add("left")
    if dy > 3:
        keys.add("down")
    elif dy < -3:
        keys.add("up")
    near = math.hypot(dx, dy) < sc.swat_r() * 0.7
    if near and (sc.free_swats() or sc.energy >= 1) and frame % 2 == 0:
        if best is None or best.k != "food":
            keys.add("a")
    low = sum(1 for th in sc.things if th.harm and th.y > 120)
    if sc.meows > 0 and low >= 5 and frame % 2 == 0:
        keys.add("b")
    return keys


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys."""
    return lambda frame: autopilot(scene, frame)


def preview(s, t):
    art.preview(s, t)
