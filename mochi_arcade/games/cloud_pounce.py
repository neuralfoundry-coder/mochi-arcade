"""CLOUD POUNCE - SORA the star-patched cat bounces up through the clouds to the moon (original game).

A vertical climber in a wrapping sky column: SORA bounces on clouds by herself, you steer her in the air and
POUNCE - a dive that smashes puff clouds and critters and lands a power bounce. 200 stages (cloud_pounce_data.py):
climbs to a moon gate built from curated chunks, a sky boss on every 10th stage (cloud_pounce_boss.py), a bonus
stage on every x5 and upgrade cards after bosses and bonuses.
The iOS port (ios/MochiArcade/Games/CloudPounce*.swift) mirrors this file and reads the stages from EXPORT.
"""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow
from mochi_arcade.games import DIFF
from mochi_arcade.games import cloud_pounce_data as D
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.games.cloud_pounce_boss import Boss
from mochi_arcade.gfx import H, W, bubble, col, draw_text, lerp_col, panel, sprite, text_width

HOWTO = ["LEFT/RIGHT  STEER SORA IN THE AIR",
         "Z / SPACE   POUNCE (ALSO DOWN)",
         "",
         "SORA BOUNCES BY HERSELF - REACH THE MOON!",
         "POUNCE TO SMASH PUFFS AND FINCHES AND",
         "LAND A POWER BOUNCE. THE SKY WRAPS AROUND.",
         "STARS + FISH CONSTELLATIONS = BIG POINTS.",
         "A SKY BOSS EVERY 10TH STAGE: POUNCE ITS",
         "HEAD! BONUS ON X5, THEN PICK AN UPGRADE.",
         "ENTER / ESC  PAUSE"]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["left", "right", "a", "down"]

FX0 = 48                    # the play field: x 48 .. 272 on screen
FW = D.FW
LIFE_AT = [15000, 40000, 80000, 140000]          # then every 100000
CAP_NAMES = {D.I_ROCKET: "CATNIP ROCKET!", D.I_BELL: "LUCKY BELL!", D.I_PARASOL: "PARASOL!",
             D.I_MAGNET: "STAR MAGNET!", D.I_MILK: "MILK! +1 LIFE"}
BIRD_COLS = ["peach", "sky", "lime", "pink", "yellow", "mint", "lavender"]
BALLOON_COLS = ["red", "hotpink", "sky", "lime", "orange", "lavender"]

EXPORT = {"stages": D.CAMPAIGN, "themes": [list(t) for t in D.THEMES], "quips": D.QUIPS,
          "fish": [{"pts": [list(p) for p in f["pts"]], "lines": [list(p) for p in f["lines"]]} for f in D.FISH]}


# ----------------------------------------------------------------------------- upgrade cards
def _icon_spring(s, cx, cy, t):
    y = cy + 2 - abs(int(math.sin(t * 5) * 4))
    for i in range(3):
        s.fill(col("yellow"), (cx - 4, cy + 5 - i * 2, 9, 1))
    pygame.draw.circle(s, col("white"), (cx, y - 3), 3)


def _icon_steer(s, cx, cy, t):
    for i in range(3):
        x = cx - 6 + i * 5 + int(t * 12) % 5
        s.fill(col("sky"), (x, cy - 3 + i * 3, 4, 1))
    s.fill(col("white"), (cx + 5, cy - 1, 3, 3))


def _icon_heavy(s, cx, cy, t):
    y = cy - 6 + int(t * 14) % 8
    pygame.draw.circle(s, col("white"), (cx, y), 3)
    s.fill(col("orange"), (cx - 6, cy + 5, 13, 2))
    s.fill(col("yellow"), (cx - 4, cy + 3, 1, 2))
    s.fill(col("yellow"), (cx + 4, cy + 3, 1, 2))


def _icon_double(s, cx, cy, t):
    for dx in (-3, 3):
        pygame.draw.circle(s, col("hotpink"), (cx + dx, cy + (dx // 3) * int(math.sin(t * 6) * 2)), 3)
        s.fill(col("white"), (cx + dx - 1, cy - 1 + (dx // 3) * int(math.sin(t * 6) * 2), 1, 1))


def _icon_magnet(s, cx, cy, t):
    pygame.draw.rect(s, col("red"), (cx - 6, cy - 4, 4, 9))
    pygame.draw.rect(s, col("red"), (cx + 3, cy - 4, 4, 9))
    pygame.draw.rect(s, col("red"), (cx - 6, cy + 2, 13, 3))
    s.fill(col("white"), (cx - 6, cy - 4, 4, 2))
    s.fill(col("white"), (cx + 3, cy - 4, 4, 2))
    s.fill(col("yellow"), (cx, cy - 7 + int(t * 6) % 3, 1, 1))


def _icon_bell(s, cx, cy, t):
    pygame.draw.circle(s, col("yellow"), (cx, cy), 5)
    s.fill(col("yellow"), (cx - 6, cy + 2, 13, 3))
    s.fill(col("orange"), (cx - 1, cy + 5, 3, 2))
    s.fill(col("white"), (cx - 2, cy - 3, 1, 2))


def _icon_cushion(s, cx, cy, t):
    draw_cloud(s, cx - 9, cy - 1 + int(math.sin(t * 4) * 1), 18, D.K_F, t, 0.0, face=False)


def _icon_rocket(s, cx, cy, t):
    draw_rocket(s, cx, cy + 3, t)


def _icon_luck(s, cx, cy, t):
    w = max(1, int(abs(math.cos(t * 3)) * 5))
    pygame.draw.ellipse(s, col("orange"), (cx - w, cy - 5, w * 2 + 1, 11))
    pygame.draw.ellipse(s, col("yellow"), (cx - w + 1, cy - 4, max(1, w * 2 - 1), 9))


def _icon_fever(s, cx, cy, t):
    for i in range(3):
        pygame.draw.circle(s, col(rainbow(i, t)), (cx - 4 + i * 4, cy + 1 - (i % 2) * 3), 2)


UPGRADES = [
    Upgrade("spring", "SPRING PAWS", "HIGHER|BOUNCES", "yellow", _icon_spring, 3),
    Upgrade("steer", "SWIFT TAIL", "FASTER|AIR STEERING", "sky", _icon_steer, 3),
    Upgrade("heavy", "HEAVY POUNCE", "POUNCES HIT|BOSSES HARDER|+ BIGGER BOUNCE", "orange", _icon_heavy, 3),
    Upgrade("double", "DOUBLE POUNCE", "+1 POUNCE|PER JUMP", "hotpink", _icon_double, 2),
    Upgrade("magnet", "STAR MAGNET", "PULLS STARS|AND TREATS|TO SORA", "red", _icon_magnet, 3),
    Upgrade("bell", "LUCKY BELL", "A SHIELD BELL|AT EVERY|STAGE START", "yellow", _icon_bell, 1),
    Upgrade("cushion", "CLOUD CUSHION", "SAVES ONE|FALL EVERY|STAGE", "white", _icon_cushion, 2),
    Upgrade("rocket", "ROCKET FUEL", "LONGER|CATNIP|ROCKETS", "orange", _icon_rocket, 3),
    Upgrade("life", "NINE LIVES", "+1 LIFE|RIGHT NOW", "hotpink", "heart", 5),
    Upgrade("luck", "LUCKY WHISKERS", "MORE GOLD|BALLOONS AND|JACKPOTS", "orange", _icon_luck, 3),
    Upgrade("fever", "FEVER PURR", "FEVER FILLS|FASTER AND|LASTS LONGER", "lime", _icon_fever, 3),
]


# ----------------------------------------------------------------------------- objects
class Cloud:
    def __init__(self, k, x, h, w, tier):
        self.k, self.x0, self.h, self.w = k, x, h, w
        self.a, self.b = D.cloud_ab(k, x, h, w, tier)
        self.x = float(x)
        self.alive = True
        self.squash = 0.0
        self.regrow = 0.0
        self.temp = 0.0        # cushion / rescue clouds fade away
        self.phase = (x + h) * 0.05

    def cx(self):
        return self.x + self.w / 2


class Item:
    def __init__(self, k, x, h):
        self.k, self.x, self.h = k, float(x), float(h)
        self.got = False
        self.gold = False
        self.ph = (x * 13 + h) % 7


class Fish:
    def __init__(self, x, h, shape, mirror, gold):
        f = FISH_DATA[shape]
        self.x, self.h, self.shape, self.gold = x, h, shape, gold
        sx = -1 if mirror else 1
        self.stars = [[(x + sx * px) % FW, h + ph, False] for px, ph in f["pts"]]
        self.lines = f["lines"]
        self.done = False
        self.glow = 0.0


class Foe:
    def __init__(self, k, x, h, a, b, spd):
        self.k, self.ax, self.ah, self.a, self.b = k, float(x), float(h), a, b
        self.x, self.h = float(x), float(h)
        self.spd = spd
        self.alive = True
        self.dead_t = 0.0
        self.vh = 0.0
        self.ph = (x * 7 + h) % 13 * 0.5


class Hail:
    def __init__(self, x, h):
        self.x, self.h = x, h
        self.warn = 0.8
        self.alive = True


FISH_DATA = D.FISH


# ----------------------------------------------------------------------------- the game
class CloudPounce(GameScene):
    @property
    def music(self):
        return self.song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES[d]
        self.fspeed = SPEED[d]
        self.levels = {}
        self.life_i = 0
        self.picks_left = 0
        self.pick_title = "POWER UP!"
        self.next_n = None
        self.was_fever = False
        self.hype.COMBO_TIME = 2.6
        self.hype.combo_y = 16
        self.field = pygame.Surface((FW, H))
        # "stage" is only passed by the GIF recorder (packaging/record_gifs.py)
        start = max(1, min(STAGES, int(opt.get("stage", opt.get("start", 1)))))
        self.start_stage(start)
        if start > 10 and "stage" not in opt:        # from a checkpoint: catch up on some upgrades first
            self.picks_left = min(8, (start - 1) // 10)
            self.pick_title = "HEAD START!"
            self.state = "pick"

    # ---------------------------------------------------------------- helpers
    def lv(self, uid):
        return self.levels.get(uid, 0)

    def factor(self, pts):
        return pts * (10 + self.tier) // 10

    def score_at(self, pts, x=None, h=None, color="yellow"):
        return self.add(self.factor(pts), x, None if h is None else self.sy(h) - 10, color)

    def sy(self, h):
        """Screen (field) y of an altitude."""
        return int(H - (h - self.cam))

    def song(self):
        k = self.st["kind"]
        if k == "boss":
            return "boss"
        if k == "bonus":
            return "bonus"
        return "cp_sky" if self.tier % 2 == 0 else "cp_moon"

    def fever_gain(self, base):
        return base * (1 + 0.35 * self.lv("fever"))

    def vx_max(self):
        v = D.VX_MAX * (1 + 0.12 * self.lv("steer"))
        if self.rocket_t > 0:
            v *= 1.25
        return v

    def jump_v(self):
        return D.JUMP_V * (1 + 0.05 * self.lv("spring"))

    def is_arena(self):
        return self.st["kind"] == "boss" or (self.st["kind"] == "bonus" and self.st["bonus"] == "balloons")

    # ---------------------------------------------------------------- stages
    def start_stage(self, n):
        self.n = n
        st = self.st = D.CAMPAIGN[n - 1]
        self.tier = st["tier"]
        self.theme = D.THEMES[self.tier]
        self.reached(n)
        tier = self.tier
        self.clouds = [Cloud(c[0], c[1], c[2], c[3], tier) for c in D.unflat(st["c"], 4)]
        self.items = [Item(i[0], i[1], i[2]) for i in D.unflat(st["i"], 3)]
        for it in self.items:
            if it.k == D.I_BALLOON:
                it.gold = self.hype.lucky(0.025 + 0.012 * self.lv("luck"))
            elif it.k == D.I_STAR and self.lv("luck") and self.hype.lucky(0.004 * self.lv("luck")):
                it.k = D.I_GOLD
        self.fish = [Fish(*f) for f in D.unflat(st["f"], 5)]
        self.foes = [Foe(e[0], e[1], e[2], e[3], e[4], self.fspeed) for e in D.unflat(st["e"], 5)]
        for r in D.unflat(st["riv"], 7):         # rocket ride star rivers
            h0, count, dh, xc, amp, freq, ph = r
            for i in range(count):
                x = xc + amp * math.sin(i * freq / 100 + ph / 100)
                self.items.append(Item(D.I_STAR, int(x) % FW, h0 + i * dh))
        self.stars_total = sum(1 for it in self.items if it.k == D.I_STAR) + sum(len(f.stars) for f in self.fish)
        self.hail = []
        self.boss = Boss(self, st["boss"]) if st["kind"] == "boss" else None
        self.goal = st["goal"]
        self.wind, self.fog, self.hail_rate = st["mods"]
        self.wind_t = 0.0
        self.wind_dir = 1
        self.wind_on = 0.0
        self.hail_t = 2.0
        # SORA
        self.x = FW / 2
        self.h = 0.0
        self.vx = self.vh = 0.0
        self.face = 1
        self.pouncing = False
        self.pounces = 1 + self.lv("double")
        self.land_t = 0.0
        self.hurt_t = 0.0
        self.invuln = 0.0
        self.rocket_t = 0.0
        self.balloon_t = 0.0
        self.balloon_c = "red"
        self.parasol_t = 0.0
        self.magnet_t = 0.0
        self.shield = self.lv("bell") > 0
        self.cushion = self.lv("cushion")
        self.rescue_t = 0.0
        self.distract_t = 0.0
        self.distract_x = 0.0
        self.kick = 0.0
        self.chain = 0             # critters knocked out since SORA last touched a cloud
        self.bonk_t = 0.0
        self.milk_given = False
        self.cam = -60.0
        self.best_h = 0.0
        self.top_land = 0.0
        self.alt_pts = 10.0
        if self.is_arena():
            self.cam = -12.0 if st["kind"] == "bonus" else 0.0
            sc = self.clouds[1] if st["kind"] == "boss" else self.clouds[0]
            self.x, self.h = sc.cx(), float(sc.h)
        if st["kind"] == "bonus" and st["bonus"] == "rocket":
            self.h = 40.0
            self.cam = -60.0
        # stage stats
        self.stime = 0.0
        self.missed = False
        self.hurt = False
        self.stage_combo = 0
        self.got_stars = 0
        self.got_fish = 0
        self.stomps = 0
        self.popped = 0
        self.golds = 0
        self.moon = False
        self.bonus_left = float(st.get("time", 0))
        self.balloon_spawn = 0.0
        self.lucky = st["kind"] == "normal" and self.hype.lucky(0.03 + 0.01 * self.lv("luck"))
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

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        s = self.state
        if s == "intro":
            if self.boss:
                self.boss.update(dt)
            self.follow_cam(dt)
            if self.state_t > self.intro_len or (self.state_t > 0.5 and self.app.input.hit("a")):
                self.begin_play()
        elif s == "play":
            self.play(dt)
        elif s == "clear":
            self.update_clear(dt)
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
        for c in self.clouds:
            c.squash = max(0.0, c.squash - dt)

    def begin_play(self):
        self.state = "play"
        self.state_t = 0.0
        if self.boss:
            self.boss.state = "fight"
        if self.st["kind"] == "bonus" and self.st["bonus"] == "rocket":
            self.rocket_t = self.st["time"] + 0.5
            self.app.audio.play("powerup")
        else:
            self.vh = self.jump_v()
            self.app.audio.play("jump")
        if self.lucky:           # a rare lucky stage: a catnip rocket from the very first leap
            self.lucky = False
            self.hype.banner("SHOOTING STAR!", "LUCKY ROCKET START", rainbow=True, dur=1.6, sound="jackpot")
            self.rocket_t = 2.2
            self.hype.shower(30, "stars")

    def on_pick(self, uid):
        if uid:
            self.levels[uid] = self.lv(uid) + 1
            u = next(x for x in UPGRADES if x.id == uid)
            self.hype.banner(u.name, f"LEVEL {self.levels[uid]}", color=u.color, dur=1.2, scale=1)
            if uid == "life":
                self.lives += 1
                self.app.audio.play("extra")
            elif uid == "bell":
                self.shield = True
            elif uid == "cushion":
                self.cushion += 1
            elif uid == "double":
                self.pounces += 1

    def play(self, dt):
        st = self.st
        self.stime += dt
        for t in ("land_t", "hurt_t", "invuln", "parasol_t", "magnet_t", "distract_t", "bonk_t"):
            setattr(self, t, max(0.0, getattr(self, t) - dt))
        self.update_clouds(dt)
        self.move_cat(dt)
        if self.state != "play":
            return
        self.update_items(dt)
        self.update_foes(dt)
        self.update_weather(dt)
        if self.boss:
            self.update_boss(dt)
        if st["kind"] == "bonus":
            self.update_bonus(dt)
        self.follow_cam(dt)
        self.stage_combo = max(self.stage_combo, self.hype.combo)
        if self.hype.fever_on and not self.was_fever:
            self.hype.fever_t += 2 * self.lv("fever")
            self.app.audio.music("fever")
        elif self.was_fever and not self.hype.fever_on:
            self.app.audio.music(self.song())
        self.was_fever = self.hype.fever_on
        self.check_life()
        if self.state == "play" and not self.is_arena() and self.h >= self.goal and not (
                st["kind"] == "bonus" and st["bonus"] == "rocket"):
            self.moon = True
            self.stage_clear()

    # ---------------------------------------------------------------- SORA
    def steer_input(self):
        """-1..1: digital left/right, or the touch pad's analog x when present (iOS)."""
        inp = self.app.input
        d = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        a = getattr(inp, "analog", None)
        if a is not None and abs(a[0]) > 0.1:
            d = max(-1.0, min(1.0, (a[0] - math.copysign(0.1, a[0])) / 0.75))
        return d

    def move_cat(self, dt):
        inp = self.app.input
        d = self.steer_input()
        if self.distract_t > 0:       # chasing a laser dot!
            dd = D.wrapd(self.distract_x - self.x)
            d = 0 if abs(dd) < 3 else (1 if dd > 0 else -1)
        vmax = self.vx_max()
        acc = 760 * (1 + 0.12 * self.lv("steer"))
        if d:
            self.face = 1 if d > 0 else -1
            target = d * vmax
            if self.vx < target:
                self.vx = min(target, self.vx + acc * dt)
            else:
                self.vx = max(target, self.vx - acc * dt)
        else:
            dec = 520 * dt
            self.vx = self.vx - dec if self.vx > dec else self.vx + dec if self.vx < -dec else 0.0
        if self.kick:
            self.vx += self.kick * dt * 4
            self.kick *= max(0.0, 1 - dt * 3)
            if abs(self.kick) < 5:
                self.kick = 0.0
        if self.wind_on > 0:
            self.vx += self.wind_dir * self.wind * dt
        if self.boss and self.boss.push:
            self.vx += self.boss.push * dt
        lim = vmax + 70
        self.vx = max(-lim, min(lim, self.vx))
        self.x = (self.x + self.vx * dt) % FW
        # pounce
        if (inp.hit("a") or inp.hit("down")) and self.pounces > 0 and not self.pouncing and self.rocket_t <= 0 \
                and self.balloon_t <= 0 and self.rescue_t <= 0 and self.distract_t <= 0:
            self.pouncing = True
            self.pounces -= 1
            self.vh = -D.POUNCE_V
            self.vx *= 0.25
            self.app.audio.play("trap")
            self.parts.burst(self.x, self.sy(self.h) - 8, 6, ("white", "lavender"), 40, 0.3)
        prev = self.h
        if self.rescue_t > 0:
            self.rescue_t -= dt
            self.vh = 120.0
            self.h += self.vh * dt
            if self.rescue_t <= 0:
                c = Cloud(D.K_F, int(max(0, min(FW - 40, self.x - 20))), int(self.h - 14), 40, 0)
                c.temp = 3.0
                self.clouds.append(c)
                self.vh = 60.0
                self.app.audio.play("pop")
            return
        if self.rocket_t > 0:
            self.rocket_t -= dt
            self.vh = D.ROCKET_SPEED if self.st["kind"] == "bonus" else 300.0
            self.pouncing = False
            if int(self.state_t * 30) % 2 == 0:
                self.parts.burst(self.x, self.sy(self.h) + 2, 2, (rainbow(int(self.stime * 10), 0), "orange", "yellow"),
                                 40, 0.4, grav=-20)
            if self.rocket_t <= 0:
                self.vh = 220.0
                self.pounces = 1 + self.lv("double")
                self.hype.banner("FUEL OUT!", color="orange", dur=0.8, scale=1)
        elif self.balloon_t > 0:
            self.balloon_t -= dt
            self.vh = D.BALLOON_LIFT
            if self.balloon_t <= 0:
                self.app.audio.play("pop")
                self.parts.burst(self.x, self.sy(self.h) - 22, 10, (self.balloon_c, "white"), 50, 0.4)
                self.pounces = 1 + self.lv("double")
        else:
            self.vh -= D.G * dt
            if self.pouncing:
                self.vh = max(self.vh, -D.POUNCE_V - 40)
            else:
                cap = 80.0 if self.parasol_t > 0 else 330.0
                self.vh = max(self.vh, -cap)
        self.h += self.vh * dt
        if self.is_arena() and self.h > 186:
            self.h = 186.0
            self.vh = min(self.vh, 0.0)
        if self.vh < 0:
            self.check_land(prev)
            if self.state != "play":
                return
        # new heights give points
        if self.h > self.best_h:
            self.best_h = self.h
            while self.best_h >= self.alt_pts and not self.is_arena():
                self.add(self.factor(10))
                self.alt_pts += 10
        # falling off the bottom
        if self.h < self.cam - 20:
            self.fall_off()
        elif self.cushion > 0 and self.vh < -60 and self.h < self.cam + 10 and not self.is_arena():
            self.cushion -= 1
            c = Cloud(D.K_F, int(max(0, min(FW - 48, self.x - 24))), int(self.h - 4), 48, 0)
            c.temp = 2.5
            self.clouds.append(c)
            self.hype.banner("CUSHION!", color="white", dur=0.9, scale=1, sound="bubble")

    def overlaps(self, c, pad=3.0):
        return abs(D.wrapd(self.x - c.cx())) <= c.w / 2 + pad

    def solid(self, c):
        if not c.alive:
            return False
        if c.k == D.K_G:
            return self.ghost_u(c) < 0.7
        return True

    def check_land(self, prev):
        best = None
        for c in self.clouds:
            if self.solid(c) and prev >= c.h - 0.01 and self.h <= c.h and self.overlaps(c):
                if self.pouncing and c.k == D.K_T:
                    self.smash_puff(c)
                    continue
                if best is None or c.h > best.h:
                    best = c
        if best is not None:
            self.land(best)

    def smash_puff(self, c):
        c.alive = False
        if self.is_arena():
            c.regrow = 3.0
        self.app.audio.play("pop")
        self.parts.burst(c.cx(), self.sy(c.h) + 4, 14, ("white", "cream", "lavender"), 60, 0.5)
        self.hype.hit(1, fever=self.fever_gain(0.03))
        self.score_at(50, c.cx(), c.h)

    def land(self, c):
        au = self.app.audio
        g = self.hype
        self.h = float(c.h)
        k = c.k
        powered = self.pouncing
        v = self.jump_v()
        if k == D.K_R:
            v = D.RAIN_V * (1 + 0.05 * self.lv("spring"))
        elif k == D.K_S:
            v = D.SPRING_V
        if powered and k != D.K_S:
            v = max(v, D.POWER_V + 15 * self.lv("heavy"))
        if g.fever_on:
            v *= 1.1
        if k == D.K_Z and self.zap_u(c) >= 0.85:
            if powered:
                self.hype.banner("GROUNDED!", "+500", color="yellow", dur=0.9, scale=1)
                self.score_at(500, c.cx(), c.h + 20)
                g.hit(1, fever=self.fever_gain(0.06))
                c.phase += 1.7            # knocks its rhythm back to calm
            else:
                self.hurt_cat("ZAP!")
        self.vh = v
        self.pouncing = False
        self.pounces = 1 + self.lv("double")
        self.chain = 0
        self.land_t = 0.12
        c.squash = 0.2
        sy = self.sy(c.h)
        if k == D.K_S:
            au.play("bubble")
            self.parts.burst(self.x, sy, 12, ("hotpink", "yellow", "mint", "sky"), 70, 0.5)
            self.floats.add(self.x, sy - 14, "BOING!", rainbow(0, self.t))
        elif k == D.K_R:
            au.play("eat")
            self.parts.burst(self.x, sy + 2, 6, ("sky", "blue"), 40, 0.4)
        elif powered:
            au.play("explode")
            self.app.shake(2, 0.15)
            self.parts.burst(self.x, sy, 16, ("white", "yellow", "lavender"), 90, 0.45)
            self.shockwave(c)
        else:
            au.play("jump")
            self.parts.burst(self.x, sy, 4, ("white", "cream"), 30, 0.3)
        if k == D.K_T:
            c.alive = False
            if self.is_arena():
                c.regrow = 3.0
            au.play("pop")
            self.parts.burst(c.cx(), sy + 3, 12, ("white", "cream"), 50, 0.5)
        elif k == D.K_W:
            self.kick = c.a * 230.0
            self.parts.burst(self.x, sy, 8, ("mint", "white"), 60, 0.4)
            au.play("bubble")
        if c.h > self.top_land:       # climbing keeps the combo chain alive, bouncing in place doesn't
            self.top_land = c.h
            if g.combo:
                g.keep_combo()

    def shockwave(self, c):
        """A pounce landing knocks out critters right next to the landing spot."""
        for f in self.foes:
            if f.alive and f.k in (D.E_BIRD, D.E_KITE) and abs(f.h - c.h) < 26 and abs(D.wrapd(f.x - self.x)) < 34:
                self.defeat_foe(f, True)

    def zap_u(self, c):
        per = max(2.8, 4.2 - 0.06 * self.tier)
        return ((self.stime + c.a / 100 * per + c.phase) % per) / per

    def ghost_u(self, c):
        return ((self.stime + c.a / 100 * 3.2) % 3.2) / 3.2

    def update_clouds(self, dt):
        t = self.stime
        for c in self.clouds:
            if c.k == D.K_M:
                c.x = c.x0 + math.sin(t * c.b / 100 + c.phase) * c.a
            if not c.alive and c.regrow > 0:
                c.regrow -= dt
                if c.regrow <= 0:
                    c.alive = True
                    c.squash = 0.2
                    self.parts.burst(c.cx(), self.sy(c.h) + 4, 6, ("white", "cream"), 30, 0.3)
            if c.temp > 0:
                c.temp -= dt
                if c.temp <= 0:
                    c.alive = False
            if c.k == D.K_Z and c.alive and self.zap_u(c) >= 0.85 and self.invuln <= 0 and self.rocket_t <= 0:
                # the bolt under a zapping thunder cloud
                if 0 < c.h - (self.h + 12) < 70 and abs(D.wrapd(self.x - c.cx())) < 6:
                    self.hurt_cat("ZAP!")
        self.clouds = [c for c in self.clouds if c.alive or c.regrow > 0 or c.h > self.cam - 30]

    def follow_cam(self, dt):
        if self.is_arena():
            return
        cam = self.cam
        target = self.h - 112
        if self.rocket_t > 0:
            target = self.h - 90
        if target > cam:
            cam += (target - cam) * min(1.0, dt * 7)
        if self.state == "play" and self.fog and self.rescue_t <= 0 and self.stime > 1.5:
            cam += self.fog * dt
        self.move_cam(min(cam, self.goal - 150))

    def move_cam(self, cam):
        """Scroll; sparks and score pop-ups (drawn in screen space) scroll along with the sky."""
        dc = cam - self.cam
        self.cam = cam
        if dc:
            for q in self.parts.p:
                q[1] += dc
            for it in self.floats.items:
                it[1] += dc

    def hurt_cat(self, why="OUCH!"):
        if self.invuln > 0 or self.rocket_t > 0 or self.state != "play":
            return
        au = self.app.audio
        if self.shield:
            self.shield = False
            self.invuln = 1.5
            au.play("tin")
            self.hype.banner("BELL SAVE!", color="yellow", dur=0.9, scale=1)
            self.parts.burst(self.x, self.sy(self.h) - 8, 12, ("yellow", "white"), 60, 0.5)
            return
        self.hurt = True
        self.hype.break_combo()
        self.invuln = 2.0
        self.hurt_t = 0.6
        self.pouncing = False
        self.vh = min(self.vh, 80.0)
        au.play("hurt")
        self.app.shake(3, 0.3)
        self.floats.add(self.x, self.sy(self.h) - 20, why, "red")
        self.parts.burst(self.x, self.sy(self.h) - 8, 10, ("red", "white"), 60, 0.5)
        if self.st["kind"] != "bonus":
            self.lose_life()

    def lose_life(self):
        self.missed = True
        self.lives -= 1
        if self.lives <= 0:
            self.state = "over"
            self.hype.banner("GAME OVER", f"STAGE {self.n}", color="red", dur=3.0)
            self.app.audio.play("gameover")
            self.end_game(False, f"STAGE {self.n}", delay=2.5)
            return False
        self.hype.banner("MEW!", f"{self.lives} LEFT", color="pink", dur=1.0, scale=1)
        return True

    def fall_off(self):
        self.app.audio.play("hurt")
        self.hype.break_combo()
        self.pouncing = False
        self.rocket_t = self.balloon_t = 0.0
        if self.st["kind"] != "bonus":
            if not self.lose_life():
                return
        # a rescue balloon carries SORA back up
        self.rescue_t = 1.3
        self.invuln = 3.0
        self.h = self.cam - 16
        self.vh = 120.0
        self.app.audio.play("bubble")

    def check_life(self):
        target = LIFE_AT[self.life_i] if self.life_i < len(LIFE_AT) else LIFE_AT[-1] + 100000 * (self.life_i - len(LIFE_AT) + 1)
        if self.score >= target:
            self.life_i += 1
            self.lives += 1
            self.hype.banner("BONUS LIFE!", f"{target} POINTS", color="pink", dur=1.4, sound="extra")
            self.hype.shower(16, "hearts")

    # ---------------------------------------------------------------- stars, treats, constellations
    def update_items(self, dt):
        au = self.app.audio
        g = self.hype
        cy = self.h + 7
        mag = 0.0
        if self.lv("magnet"):
            mag = 18 + 12 * self.lv("magnet")
        if self.magnet_t > 0 or g.fever_on:
            mag = max(mag, 70.0)
        for it in self.items:
            if it.got or abs(it.h - cy) > 120:
                continue
            dx = D.wrapd(it.x - self.x)
            dh = it.h - cy
            if mag and it.k in (D.I_STAR, D.I_GOLD) and dx * dx + dh * dh < mag * mag:
                dist = max(1.0, math.hypot(dx, dh))
                step = min(dist, 190 * dt)
                it.x = (it.x - dx / dist * step) % FW
                it.h -= dh / dist * step
                dx = D.wrapd(it.x - self.x)
                dh = it.h - cy
            r = 10 if it.k != D.I_BALLOON else 9
            if abs(dx) < r and abs(dh) < r + 2:
                self.collect(it)
        for f in self.fish:
            f.glow = max(0.0, f.glow - dt)
            if f.done or abs(f.h - cy) > 60:
                continue
            for s in f.stars:
                if not s[2] and abs(D.wrapd(s[0] - self.x)) < 9 and abs(s[1] - cy) < 11:
                    s[2] = True
                    self.got_stars += 1
                    g.hit(1, fever=self.fever_gain(0.025))
                    self.score_at(30 + g.combo_bonus(2), s[0], s[1], "sky")
                    au.play("coin")
                    self.parts.burst(s[0], self.sy(s[1]), 5, ("white", "sky"), 30, 0.3)
            if all(s[2] for s in f.stars):
                f.done = True
                f.glow = 1.2
                self.got_fish += 1
                pts = self.score_at(1000, f.x, f.h + 14, "yellow")
                g.hit(2, fever=self.fever_gain(0.12))
                if f.gold:
                    g.jackpot(self.factor(5000), "GOLDEN FISH STARS!")
                else:
                    g.banner("FISH CONSTELLATION!", f"+{pts}", color="sky", dur=1.3, scale=1, sound="bonus")
                for a, b in f.lines:
                    for k in range(4):
                        px = f.stars[a][0] + D.wrapd(f.stars[b][0] - f.stars[a][0]) * k / 4
                        ph = f.stars[a][1] + (f.stars[b][1] - f.stars[a][1]) * k / 4
                        self.parts.sparkle(px, self.sy(ph), "yellow")
        self.items = [it for it in self.items if not it.got and it.h > self.cam - 40]

    def collect(self, it):
        au = self.app.audio
        g = self.hype
        k = it.k
        if k == D.I_STAR:
            it.got = True
            self.got_stars += 1
            g.hit(1, fever=self.fever_gain(0.02))
            self.score_at(50 + g.combo_bonus(2), it.x if g.combo % 5 == 0 else None, it.h)
            au.play("fruit")
            self.parts.burst(it.x, self.sy(it.h), 4, ("yellow", "white"), 30, 0.3)
        elif k == D.I_BALLOON:
            if self.rocket_t > 0 or self.rescue_t > 0 or self.is_arena():
                it.got = True
                self.popped += 1
                g.hit(1, fever=self.fever_gain(0.03))
                self.score_at(100, it.x, it.h, "pink")
                au.play("pop")
                self.parts.burst(it.x, self.sy(it.h), 10, ("red", "white"), 50, 0.4)
                if it.gold:
                    self.golds += 1
                    g.jackpot(self.factor(3000), "GOLDEN BALLOON!")
                return
            it.got = True
            self.popped += 1
            self.balloon_t = D.BALLOON_T
            self.balloon_c = "yellow" if it.gold else BALLOON_COLS[int(it.ph) % len(BALLOON_COLS)]
            self.pouncing = False
            g.hit(1, fever=self.fever_gain(0.03))
            self.score_at(100, it.x, it.h, "pink")
            au.play("bubble")
            if it.gold:
                self.golds += 1
                g.jackpot(self.factor(3000), "GOLDEN BALLOON!")
        elif k == D.I_GOLD:
            it.got = True
            self.golds += 1
            g.jackpot(self.factor(4000), "GOLDEN FISH!")
            self.parts.burst(it.x, self.sy(it.h), 16, ("yellow", "orange", "white"), 70, 0.6)
        else:
            it.got = True
            self.power(k)

    def power(self, k):
        au = self.app.audio
        au.play("powerup")
        self.floats.add(self.x, self.sy(self.h) - 22, CAP_NAMES[k], "mint")
        self.score_at(100)
        if k == D.I_ROCKET:
            self.rocket_t = 2.2 + 0.45 * self.lv("rocket")
            self.balloon_t = 0.0
            self.pouncing = False
            self.hype.flash("orange", 0.15)
        elif k == D.I_BELL:
            self.shield = True
        elif k == D.I_PARASOL:
            self.parasol_t = 10.0
        elif k == D.I_MAGNET:
            self.magnet_t = 12.0
        elif k == D.I_MILK:
            self.lives += 1
            au.play("extra")

    # ---------------------------------------------------------------- critters
    def update_foes(self, dt):
        t = self.stime
        cx, cy = self.x, self.h + 7
        for f in self.foes:
            if not f.alive:
                f.dead_t += dt
                f.vh -= 300 * dt
                f.h += f.vh * dt
                continue
            if f.ah < self.cam - 60 or f.ah > self.cam + 300:
                continue
            k = f.k
            if k == D.E_BIRD:
                f.x = (f.x + f.a * f.b * f.spd * dt) % FW
                f.h = f.ah + math.sin(t * 5 + f.ph) * 3
                hw, hh = 7, 5
            elif k == D.E_KITE:
                f.x = (f.ax + math.sin(t * f.b / 100 + f.ph) * f.a) % FW
                f.h = f.ah + math.cos(t * f.b / 50 + f.ph) * 4
                hw, hh = 6, 8
            elif k == D.E_DOT:
                f.x = (f.ax + math.sin(t * f.b / 100 * 1.3 + f.ph) * f.a) % FW
                f.h = f.ah + math.sin(t * f.b / 100 * 0.9) * f.a * 0.45
                hw, hh = 4, 4
            else:
                f.x = (f.ax + math.cos(t * f.b / 100 + f.ph) * f.a) % FW
                f.h = f.ah + math.sin(t * f.b / 100 + f.ph) * f.a * 0.6
                hw, hh = 4, 4
            dx = D.wrapd(f.x - cx)
            dh = f.h - cy
            if abs(dx) > hw + 5 or abs(dh) > hh + 7:
                continue
            if self.rescue_t > 0:
                continue
            if k == D.E_DOT:
                if self.distract_t <= 0 and self.rocket_t <= 0 and self.invuln <= 0:
                    self.distract_t = 1.0
                    self.distract_x = f.x
                    self.pouncing = False
                    self.floats.add(self.x, self.sy(self.h) - 22, "!?", "red")
                    self.app.audio.play("type")
                continue
            if self.rocket_t > 0 and k != D.E_SPARK:
                self.defeat_foe(f, True)
                continue
            if k != D.E_SPARK and (self.pouncing or (self.vh < 0 and self.h >= f.h - 3)):
                self.defeat_foe(f, self.pouncing)
                self.vh = (D.POWER_V + 15 * self.lv("heavy")) if self.pouncing else self.jump_v() * 1.05
                self.pouncing = False
                self.pounces = 1 + self.lv("double")
                continue
            self.hurt_cat()
        if self.distract_t > 0:
            for f in self.foes:
                if f.k == D.E_DOT and abs(D.wrapd(f.x - self.distract_x)) < 40:
                    self.distract_x = f.x
                    break
        self.foes = [f for f in self.foes if f.alive or f.dead_t < 1.5]

    def defeat_foe(self, f, power):
        g = self.hype
        f.alive = False
        f.vh = 120.0
        self.stomps += 1
        g.hit(1, fever=self.fever_gain(0.06))
        base = 300 if f.k == D.E_KITE else 200
        pts = self.score_at((base * (2 if power else 1)) + g.combo_bonus(10), f.x, f.h + 6, "orange")
        self.app.audio.play("pop" if f.k == D.E_KITE else "brick")
        g.hitstop(0.04)
        self.parts.burst(f.x, self.sy(f.h), 12, ("white", "yellow", BIRD_COLS[int(f.ph) % len(BIRD_COLS)]), 70, 0.5)
        if power:
            self.floats.add(f.x, self.sy(f.h) - 18, "POUNCE!", "yellow")
        self.chain += 1
        if self.chain >= 2:        # several critters in one leap: a sky chain
            bonus = self.score_at(250 * self.chain)
            if self.chain == 3:
                g.banner("SKY CHAIN!", f"+{bonus}", color="orange", dur=1.1, scale=1, sound="combo")
            else:
                self.floats.add(f.x, self.sy(f.h) - 28, f"CHAIN x{self.chain}", "orange")
        return pts

    # ---------------------------------------------------------------- weather
    def update_weather(self, dt):
        if self.wind:
            self.wind_t += dt
            if self.wind_on > 0:
                self.wind_on -= dt
                if self.wind_on <= 0:
                    self.wind_t = 0.0
                    self.wind_dir = -self.wind_dir
            elif self.wind_t > 4.5:
                self.wind_on = 2.6
                self.app.audio.play("bubble")
        if self.hail_rate:
            self.hail_t -= dt
            if self.hail_t <= 0:
                self.hail_t = 100.0 / self.hail_rate * random.uniform(0.6, 1.4)
                x = (self.x + random.uniform(-70, 70)) % FW
                self.hail.append(Hail(x, self.cam + H + 6))
            for hs in self.hail:
                if hs.warn > 0:
                    hs.warn -= dt
                    hs.h = self.cam + H + 6
                    continue
                hs.h -= 150 * dt
                if abs(D.wrapd(hs.x - self.x)) < 7 and abs(hs.h - (self.h + 7)) < 9:
                    hs.alive = False
                    self.parts.burst(hs.x, self.sy(hs.h), 8, ("white", "sky"), 50, 0.4)
                    self.hurt_cat("HAIL!")
            self.hail = [hs for hs in self.hail if hs.alive and hs.h > self.cam - 20]

    # ---------------------------------------------------------------- boss
    def update_boss(self, dt):
        b = self.boss
        b.update(dt)
        if b.state == "dead":
            if b.die_t > 1.6 and self.state == "play":
                self.stage_clear()
            return
        if b.state != "fight" or self.rescue_t > 0:
            return
        cy = self.h + 7
        z = b.stomp_zone()
        if z is not None and self.vh < 0:
            zx, zh, hw = z
            if abs(D.wrapd(self.x - zx)) < hw + 4 and zh - 8 <= self.h <= zh + 6:
                away = 1 if D.wrapd(self.x - zx) >= 0 else -1
                if b.blocked(self.x) or b.inv > 0:     # shields up / still reeling: SORA just bounces off
                    self.vh = self.jump_v()
                    self.kick = away * 160.0
                    self.pouncing = False
                    self.app.audio.play("tin")
                    self.floats.add(self.x, self.sy(self.h) - 16, "CLANG!" if b.inv <= 0 else "BOP!", "gray")
                    return
                dmg = (2 + self.lv("heavy")) if self.pouncing else 1
                b.hit(dmg)
                self.hype.hit(1, fever=self.fever_gain(0.08))
                self.score_at(250 * dmg, self.x, self.h + 8, "orange")
                self.hype.hitstop(0.08)
                self.hype.flash("white", 0.12)
                self.app.shake(3, 0.2)
                self.app.audio.play("explode" if self.pouncing else "brick")
                self.parts.burst(self.x, self.sy(self.h), 14, ("white", "yellow", "orange"), 80, 0.5)
                self.vh = (D.POWER_V + 15 * self.lv("heavy")) if self.pouncing else self.jump_v() * 1.1
                self.kick = away * 200.0
                self.pouncing = False
                self.pounces = 1 + self.lv("double")
                if b.state == "dead":
                    self.boss_defeated()
                elif b.phase == 2 and not self.milk_given:   # a milk bottle for the second half
                    self.milk_given = True
                    c = max(self.clouds, key=lambda c: c.h * 10 - abs(D.wrapd(c.cx() - self.x)))
                    self.items.append(Item(D.I_MILK, int(c.cx()), c.h + 12))
                    self.floats.add(c.cx(), self.sy(c.h) - 24, "MILK!", "white")
                return
        n = b.stomp_minions(self.x, self.h, self.vh)
        if n:
            self.vh = self.jump_v() * 1.05
            self.pounces = 1 + self.lv("double")
            self.stomps += n
            self.hype.hit(n, fever=self.fever_gain(0.05))
            self.score_at(300 * n, self.x, self.h + 8, "lime")
            self.app.audio.play("brick")
        if self.bonk_t <= 0 and b.bump(self.x, cy, 5, 7):
            self.bonk_t = 0.4
            self.vh = min(self.vh, -60.0)
            self.kick = (1 if D.wrapd(self.x - b.x) >= 0 else -1) * 180.0
            self.pouncing = False
            self.app.audio.play("tin")
            self.floats.add(self.x, self.sy(self.h) - 16, "BONK!", "gray")
        if self.invuln <= 0 and b.touch(self.x, cy, 5, 7):
            self.hurt_cat()
        for dx, dh in b.dots():
            if self.distract_t <= 0 and self.invuln <= 0 and abs(D.wrapd(dx - self.x)) < 7 and abs(dh - cy) < 8:
                self.distract_t = 0.8
                self.distract_x = dx
                self.floats.add(self.x, self.sy(self.h) - 22, "!?", "red")
                self.app.audio.play("type")

    def boss_defeated(self):
        g = self.hype
        self.app.audio.play("bossdown")
        g.banner("BOSS DOWN!", self.boss.name, rainbow=True, dur=2.2, scale=2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(40, "coins")
        g.slowmo(0.3, 1.4)
        self.app.shake(6, 0.6)
        self.score_at(15000, FW / 2, 140)
        self.app.audio.music(None)

    # ---------------------------------------------------------------- bonus stages
    def update_bonus(self, dt):
        st = self.st
        self.bonus_left -= dt
        if st["bonus"] == "balloons":
            self.balloon_spawn -= dt
            if self.balloon_spawn <= 0 and self.bonus_left > 1.0:
                prog = 1 - self.bonus_left / st["time"]
                self.balloon_spawn = 0.55 - 0.25 * prog
                it = Item(D.I_BALLOON, random.uniform(10, FW - 10), self.cam - 10)
                it.gold = self.hype.lucky(0.05 + 0.02 * self.lv("luck"))
                it.ph = random.randrange(6)
                self.items.append(it)
            for it in self.items:
                if it.k == D.I_BALLOON:
                    it.h += (34 + 4 * self.tier // 2 + it.ph * 3) * dt
                    it.x = (it.x + math.sin(self.stime * 2 + it.ph) * 10 * dt) % FW
            self.items = [it for it in self.items if it.h < 220]
        if self.bonus_left <= 0:
            self.bonus_left = 0.0
            self.hype.banner("TIME UP!", color="yellow", dur=1.2)
            self.stage_clear()

    # ---------------------------------------------------------------- clear / tally
    def stage_clear(self):
        if self.state != "play":
            return
        self.state = "clear"
        self.state_t = 0.0
        self.pouncing = False
        self.rocket_t = self.balloon_t = 0.0
        self.hail = []
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.was_fever = False
        self.app.audio.music(None)
        if self.boss:
            return
        self.app.audio.play("win")
        self.hype.slowmo(0.35, 0.9)
        if self.moon:
            self.hype.banner("MOON GATE!", "SORA MADE IT!", rainbow=True, dur=1.8)
            self.hype.flash("white", 0.25)
            self.hype.shower(50, "stars")

    def update_clear(self, dt):
        # SORA floats happily into the moon gate (or just hovers after a boss / bonus)
        self.vh = 0.0
        if self.moon:
            self.h += 50 * dt
            self.x += D.wrapd(FW / 2 - self.x) * min(1.0, dt * 3)
            self.move_cam(min(self.cam + 30 * dt, self.goal - 120))
        if int(self.state_t * 10) % 3 == 0:
            self.parts.sparkle(self.x + random.uniform(-10, 10), self.sy(self.h) - random.uniform(0, 16),
                               rainbow(int(self.state_t * 10), 0))
        if self.boss and self.state_t < 1.0:
            return
        if self.state_t > 1.8:
            self.begin_tally()

    def begin_tally(self):
        st = self.st
        f = self.factor
        rows = []
        if st["kind"] == "normal":
            rows.append(("MOON GATE", f(1000)))
            rows.append(("CLIMB TIME", f(max(0, int(st["par"] - self.stime)) * 40)))
            rows.append((f"STARS {self.got_stars}/{self.stars_total}", f(self.got_stars * 20)))
            if self.fish:
                rows.append((f"FISH STARS {self.got_fish}/{len(self.fish)}", f(self.got_fish * 500)))
        elif st["kind"] == "boss":
            rows.append(("BOSS BONUS", f(10000 + 2000 * self.tier)))
            rows.append(("NO DAMAGE", f(8000) if not self.hurt else 0))
        elif st["bonus"] == "balloons":
            rows.append((f"BALLOONS x{self.popped}", f(self.popped * 100)))
            rows.append((f"GOLDEN x{self.golds}", f(self.golds * 1000)))
        else:
            rows.append((f"STARS {self.got_stars}/{self.stars_total}", f(self.got_stars * 40)))
            rows.append((f"BALLOONS x{self.popped}", f(self.popped * 150)))
            if st["bonus"] == "stars":
                rows.append(("MOON REACHED", f(5000) if self.moon else 0))
        rows.append((f"BEST COMBO {self.stage_combo}", f(self.stage_combo * 40)))
        if st["kind"] != "bonus":
            rows.append(("NO MISS", f(5000) if not self.missed else 0))
        self.tally = [[label, v, 0.0] for label, v in rows]
        self.tally_i = 0
        self.tally_wait = 0.0
        self.state = "tally"
        self.state_t = 0.0
        if st["kind"] != "bonus" and not self.missed:
            self.hype.banner("PURRFECT!", "NO MISS", rainbow=True, dur=1.8, sound="fever")
            self.hype.shower(40, "stars")

    def tally_line(self):
        st = self.st
        if st["kind"] == "boss":
            return "SORA: THE SKY IS SAFE AGAIN!"
        if st["kind"] == "bonus":
            return "SORA: WHAT A TREAT!"
        if not self.missed and self.got_stars >= self.stars_total * 0.8:
            return "SORA PURRS: PURRFECT CLIMB!"
        if not self.missed:
            return "SORA: NOT A SINGLE SLIP!"
        return "SORA: MEW... THAT WAS CLOSE!"

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
            self.hype.banner("ALL CLEAR!!", "SORA REACHED THE MOON!", rainbow=True, dur=5.0, sound="jackpot")
            self.hype.shower(120, "confetti")
            self.end_game(True, "ALL 200 STAGES!", delay=4.5)
            return
        self.next_n = self.n + 1
        if st["kind"] in ("boss", "bonus"):
            self.picks_left = 1
            self.pick_title = "BOSS BONUS!" if st["kind"] == "boss" else "SWEET DREAMS!"
            self.state = "pick"
        else:
            self.start_stage(self.next_n)

    # ---------------------------------------------------------------- drawing
    def sky_col(self, p):
        th = self.theme
        p = max(0.0, min(1.0, p))
        if p < 0.5:
            return lerp_col(th[1], th[2], p * 2)
        return lerp_col(th[2], th[3], (p - 0.5) * 2)

    def progress_at(self, h):
        if self.st["kind"] == "boss":
            return 0.85
        if self.is_arena():
            return 0.3
        return h / max(1.0, self.goal)

    def render(self, s):
        t = self.t
        f = self.field
        self.draw_sky(f, t)
        for c in self.clouds:
            if c.alive:
                y = self.sy(c.h)
                if -12 < y < H + 12:
                    self.draw_cloud_obj(f, c, y, t)
        for fi in self.fish:
            self.draw_fish(f, fi, t)
        for it in self.items:
            y = self.sy(it.h)
            if -12 < y < H + 12:
                draw_item(f, it, int(it.x), int(y), t)
        for fo in self.foes:
            y = self.sy(fo.h)
            if -20 < y < H + 20:
                draw_foe(f, fo, int(fo.x), int(y), t, self.tier)
        if self.boss:
            self.boss.draw(f, t)
        self.draw_cat(f, t)
        self.draw_weather(f, t)
        self.parts.draw(f)
        self.floats.draw(f)
        s.blit(f, (FX0, 0))
        if self.boss and self.boss.dark > 0:
            self.draw_dark(s)
        self.draw_panels(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "tally":
            self.draw_tally(s, t)

    def draw_sky(self, f, t):
        cam = self.cam
        for y in range(0, H, 4):
            f.fill(self.sky_col(self.progress_at(cam + H - y - 2)), (0, y, FW, 4))
        p = self.progress_at(cam + H / 2)
        # twinkling stars come out as the sky darkens
        if p > 0.3:
            n = int(min(1.0, (p - 0.3) * 2) * 30)
            for i in range(n):
                x = (i * 71 + 13) % FW
                y = int((i * 37 + cam * 0.2) % 210) - 5
                c = ("white", "lavender", "yellow", "white", "sky")[(int(t * 3) + i) % 5]
                f.fill(col(c), (x, y, 1, 1 if i % 3 else 2))
        # soft far clouds (parallax)
        fc = self.theme[5]
        for i in range(5):
            x = (i * 97 + int(t * (3 + i))) % (FW + 80) - 40
            y = int((i * 61 + cam * 0.35) % 260) - 30
            c = lerp_col(self.sky_col(self.progress_at(cam + H - y)), fc, 0.28)
            for j in range(3):
                puff(f, c, x + j * 12, y + (1 if j == 1 else 0), 9 + (j % 2) * 3)
            pygame.draw.rect(f, c, (x - 6, y + 2, 36, 8), border_radius=4)
        # the town far below at the start
        if not self.is_arena() and cam < 140:
            self.draw_town(f, t)
        # the moon gate
        if not self.is_arena() and self.goal - cam < 300:
            self.draw_moon(f, t)

    def draw_town(self, f, t):
        y0 = self.sy(0)
        for i in range(8):
            x = i * 30 - 6
            hh = 10 + (i * 7) % 12
            c = ("choco", "brown", "purple", "deep")[i % 4]
            f.fill(col(c), (x, y0 + 4 + hh // 3, 30, H))
            pygame.draw.polygon(f, col("red" if i % 2 else "orange"), [(x - 2, y0 + 5 + hh // 3), (x + 15, y0 - 4 + hh // 3),
                                                                      (x + 32, y0 + 5 + hh // 3)])
            for wy in range(y0 + 12 + hh // 3, H, 10):
                for wx in (x + 6, x + 18):
                    lit = (i + wx + wy) % 3
                    f.fill(col("yellow" if lit else "ink"), (wx, wy, 4, 5))
        # SORA's own rooftop with a chimney
        f.fill(col("darkgray"), (FW // 2 + 30, y0 - 14, 10, 14))
        f.fill(col("gray"), (FW // 2 + 29, y0 - 16, 12, 3))
        f.fill(col("ink"), (0, y0, FW, 4))
        for x in range(0, FW, 8):
            f.fill(col("red"), (x, y0, 7, 2))

    def draw_moon(self, f, t):
        gy = self.sy(self.goal)
        cx = FW // 2
        my = gy - 40
        near = self.h > self.goal - 160
        pygame.draw.circle(f, col("yellow"), (cx, my), 25)
        pygame.draw.circle(f, col("cream"), (cx, my), 23)
        for dx, dy, r in ((-9, -8, 4), (8, 6, 3), (11, -10, 2), (-4, 11, 2)):
            pygame.draw.circle(f, col("peach"), (cx + dx, my + dy), r)
        # sleepy moon face, it wakes up when SORA comes near
        cute.eyes(f, cx, my + 1, 6, 0, "happy" if near else "sleepy")
        cute.mouth(f, cx, my + 6, "happy" if near else "flat")
        cute.blush(f, cx, my + 4, 9)
        # the gate: an arch of stars
        for i in range(13):
            a = math.pi * i / 12
            x = cx + int(math.cos(a) * 70)
            y = gy - int(math.sin(a) * 34)
            c = rainbow(i, t) if near else ("yellow" if (i + int(t * 4)) % 3 else "white")
            f.fill(col(c), (x - 1, y, 3, 1))
            f.fill(col(c), (x, y - 1, 1, 3))
        for x in range(cx - 70, cx + 71, 6):
            f.fill(col("yellow" if (x // 6 + int(t * 8)) % 2 else "white"), (x, gy, 3, 1))

    def draw_cloud_obj(self, f, c, y, t):
        x = int(c.x)
        k = c.k
        if k == D.FLOOR:
            if self.is_arena():       # BALLOON BASH: a bank of clouds to bounce on
                for i in range(7):
                    draw_cloud(f, i * 32, y, 32, D.K_F, t, c.squash, face=i % 2 == 0)
            return
        sq = c.squash
        if k == D.K_G:
            u = self.ghost_u(c) if self.state in ("play", "clear") else 0.0
            if u >= 0.7:
                for xx in range(x, x + c.w, 4):
                    for xd in (0, -FW, FW):
                        f.fill(col("lavender"), (xx + xd, y + 3, 2, 1))
                        f.fill(col("lavender"), (xx + xd, y + 9, 2, 1))
                return
            if u >= 0.6 and int(t * 16) % 2:
                return
        state = 0
        if k == D.K_Z and self.state in ("play", "clear"):
            u = self.zap_u(c)
            state = 2 if u >= 0.85 else 1 if u >= 0.62 else 0
        if c.temp > 0 and c.temp < 0.8 and int(t * 12) % 2:
            return
        for xd in (0, -FW, FW):
            if -c.w - 8 < x + xd < FW + 8:
                draw_cloud(f, x + xd, y, c.w, k, t, sq, state=state, wind=c.a)
        if k == D.K_Z and state == 2:
            bx = int(c.cx()) % FW
            yy = y + 10
            for i in range(7):
                nx = bx + (2 if (i + int(t * 20)) % 2 else -2)
                pygame.draw.line(f, col("yellow"), (bx, yy), (nx, yy + 10), 2)
                f.fill(col("white"), (nx, yy + 10, 1, 1))
                bx, yy = nx, yy + 10

    def draw_fish(self, f, fi, t):
        if abs(fi.h - (self.cam + H / 2)) > 140:
            return
        lit = fi.done
        lc = col("yellow" if fi.gold else "sky") if lit else col("darkgray")
        for a, b in fi.lines:
            x0, h0 = fi.stars[a][0], fi.stars[a][1]
            dx = D.wrapd(fi.stars[b][0] - x0)
            dh = fi.stars[b][1] - h0
            n = max(1, int(max(abs(dx), abs(dh)) / (1 if lit else 3)))
            for k in range(n + 1):
                px = int(x0 + dx * k / n) % FW
                py = int(self.sy(h0 + dh * k / n))
                f.fill(lc, (px, py, 1, 1))
        for x, h, got in fi.stars:
            y = int(self.sy(h))
            x = int(x)
            if got:
                c = "yellow" if fi.gold else "white"
                f.fill(col(c), (x - 1, y, 3, 1))
                f.fill(col(c), (x, y - 1, 1, 3))
            else:
                tw = int(t * 6 + x) % 4
                c = "yellow" if fi.gold else ("white" if tw else "sky")
                f.fill(col(c), (x - 2, y, 5, 1))
                f.fill(col(c), (x, y - 2, 1, 5))
                f.fill(col("white"), (x, y, 1, 1))
        if fi.glow > 0 and int(t * 10) % 2:
            draw_text(f, "FISH!", int(fi.x), int(self.sy(fi.h)) - 16, "yellow", align="center")

    def draw_cat(self, f, t):
        x = int(self.x)
        y = int(self.sy(self.h))
        if self.invuln > 0 and self.state == "play" and int(t * 14) % 2 and self.rescue_t <= 0:
            return
        if y > H + 20 or y < -30:
            return
        st = self.state
        # accessories behind SORA
        if self.balloon_t > 0 or self.rescue_t > 0:
            bc = "yellow" if self.rescue_t > 0 else self.balloon_c
            for xd in (0, -FW, FW):
                draw_balloon(f, x + xd + 3, y - 30, bc, t)
                pygame.draw.line(f, col("white"), (x + xd + 3, y - 22), (x + xd + 1, y - 12))
        if self.rocket_t > 0:
            for xd in (0, -FW, FW):
                draw_rocket(f, x + xd, y + 4, t, flame=True)
        if self.parasol_t > 0 and self.vh < 0:
            for xd in (0, -FW, FW):
                draw_parasol(f, x + xd, y - 22, t)
        if st == "intro" and self.st.get("bonus") == "rocket":
            for xd in (0, -FW, FW):
                draw_rocket(f, x + xd, y + 4, t)
        if st == "intro":
            name = "cp_idle"
            frame = 1 if int(t * 1.3) % 5 == 0 else 0
        elif st in ("clear", "tally"):
            name, frame = "cp_happy", 0
        elif self.hurt_t > 0:
            name, frame = "cp_hurt", 0
        elif self.pouncing:
            name, frame = "cp_ball", 0
        elif self.land_t > 0:
            name, frame = "cp_land", 0
        elif self.distract_t > 0:
            name, frame = "cp_fall", 0
        elif self.vh > 130 or self.balloon_t > 0 or self.rescue_t > 0 or self.rocket_t > 0:
            name, frame = "cp_up", 0
        elif self.vh > -110:
            name, frame = "cp_star", 0
        else:
            name, frame = "cp_fall", 0
        flip = self.pouncing and int(t * 14) % 2 == 1
        spr = sprite(name, frame, flip=flip)
        if self.hype.fever_on and st == "play":
            for i in range(1, 4):
                c = col(rainbow(i, t))
                ty = y - 8 + int(self.vh * 0.02 * i)
                pygame.draw.circle(f, c, (x - int(self.vx * 0.02 * i), ty), 3 - i // 2)
        for xd in (0, -FW, FW):
            if -20 < x + xd < FW + 20:
                if name != "cp_ball":
                    self.draw_tail(f, x + xd, y, t)
                f.blit(spr, (x + xd - 8, y - 16))
                if self.shield:
                    yy = y - 4 + (2 if name == "cp_land" else 0)
                    pygame.draw.circle(f, col("yellow"), (x + xd, yy), 2)
                    f.fill(col("orange"), (x + xd, yy + 1, 1, 1))
        if self.pouncing:
            for i in range(3):
                f.fill(col("white"), (x - 6 + i * 6, y - 22 - (int(t * 40) + i * 5) % 12, 1, 4))
        if self.distract_t > 0 and int(t * 6) % 2:
            draw_text(f, "!?", x, y - 26, "red", align="center")

    def draw_tail(self, f, x, y, t):
        side = -self.face
        sway = math.sin(t * 7) * 2
        pts = []
        for i in range(5):
            pts.append((x + side * (5 + i), y - 4 - i * 2 + int(sway * i / 4)))
        for px, py in pts:
            f.fill(col("black"), (px - 1, py - 1, 3, 3))
        for i, (px, py) in enumerate(pts):
            f.fill(col("lavender" if i == 4 else "white"), (px, py, 1, 1))

    def draw_weather(self, f, t):
        if self.wind and self.state == "play":
            if self.wind_on > 0 or (self.wind_t > 3.5 and int(t * 8) % 2):
                d = self.wind_dir
                for i in range(6):
                    y = 30 + i * 28 + int(math.sin(t * 3 + i) * 4)
                    x = int((i * 53 + t * 140 * d) % (FW + 40)) - 20
                    c = "white" if self.wind_on > 0 else "yellow"
                    f.fill(col(c), (x, y, 12, 1))
                    f.fill(col(c), (x + (12 if d > 0 else -2), y - 1, 2, 3))
        for hs in self.hail:
            if hs.warn > 0:
                if int(t * 10) % 2:
                    x = int(hs.x)
                    pygame.draw.polygon(f, col("red"), [(x - 4, 2), (x + 4, 2), (x, 7)])
                continue
            y = int(self.sy(hs.h))
            pygame.draw.circle(f, col("sky"), (int(hs.x), y), 4)
            pygame.draw.circle(f, col("white"), (int(hs.x) - 1, y - 1), 2)
        if self.fog:
            top = H - 14 + int(math.sin(t * 2) * 2)
            for x in range(0, FW, 6):
                yy = top + int(math.sin(t * 3 + x * 0.2) * 2)
                f.fill(col("lavender"), (x, yy, 6, H - yy))
            for x in range(0, FW, 2):
                f.fill(col("white"), (x, top + 4 + (x // 2) % 2 * 3, 1, 1))

    def draw_dark(self, s):
        """NOCTURNE's eclipse: darkness everywhere except a circle of light around SORA."""
        a = self.boss.dark
        cx = FX0 + int(self.x)
        cy = int(self.sy(self.h)) - 8
        r = 44
        dark = (12, 8, 24, int(220 * a))
        ov = pygame.Surface((FW, H), pygame.SRCALPHA)
        for y in range(0, H, 2):
            dy = y - cy
            if abs(dy) < r:
                half = int(math.sqrt(r * r - dy * dy))
                ov.fill(dark, (0, y, max(0, cx - FX0 - half), 2))
                ov.fill(dark, (cx - FX0 + half, y, FW, 2))
            else:
                ov.fill(dark, (0, y, FW, 2))
        s.blit(ov, (FX0, 0))

    def draw_panels(self, s, t):
        acc = self.theme[4]
        for x0 in (0, FX0 + FW):
            s.fill(col("night"), (x0, 0, FX0, H))
            for i in range(10):
                sx = x0 + (i * 17 + 5) % FX0
                sy = (i * 41 + 7) % H
                s.fill(col("deep" if (i + int(t * 2)) % 4 else "lavender"), (sx, sy, 1, 1))
        s.fill(col(acc), (FX0 - 1, 0, 1, H))
        s.fill(col(acc), (FX0 + FW, 0, 1, H))
        # left: score, hi, the altitude meter
        draw_text(s, "SCORE", 4, 3, "lavender", shadow=None)
        draw_text(s, f"{self.score:07d}", 4, 12, "white", shadow=None)
        draw_text(s, "HI", 4, 24, "lavender", shadow=None)
        draw_text(s, f"{max(self.best, self.score):07d}", 4, 33, "gray", shadow=None)
        k = self.st["kind"]
        if k == "bonus":
            secs = int(math.ceil(self.bonus_left))
            draw_text(s, "TIME", 24, 60, "lavender", align="center", shadow=None)
            draw_text(s, f"{secs:02d}", 24, 72, "yellow" if secs > 5 or int(t * 6) % 2 else "red", 2,
                      align="center", outline="ink", shadow=None)
            draw_text(s, "POPS" if self.st["bonus"] == "balloons" else "STARS", 24, 104, "lavender", align="center",
                      shadow=None)
            draw_text(s, f"{self.got_stars if self.st['bonus'] != 'balloons' else self.popped}", 24, 114, "white",
                      align="center", shadow=None)
        elif self.boss:
            draw_text(s, "BOSS", 24, 50, "red", align="center", shadow=None)
            hpf = max(0.0, self.boss.hp / max(1, self.boss.maxhp))
            pygame.draw.rect(s, col("ink"), (18, 62, 12, 124), border_radius=3)
            hh = int(120 * hpf)
            s.fill(col("red"), (20, 64 + 120 - hh, 8, hh))
            s.fill(col("pink"), (20, 64 + 120 - hh, 2, hh))
        else:
            top, bot = 58, 184
            pygame.draw.rect(s, col("ink"), (19, top, 10, bot - top), border_radius=4)
            p = max(0.0, min(1.0, self.h / max(1.0, self.goal)))
            fh = int((bot - top - 4) * p)
            s.fill(col(acc), (21, bot - 2 - fh, 6, fh))
            pygame.draw.circle(s, col("yellow"), (24, top - 7), 6)
            pygame.draw.circle(s, col("cream"), (24, top - 7), 5)
            s.fill(col("peach"), (22, top - 9, 2, 2))
            cy = bot - 2 - fh
            s.blit(sprite("cp_happy"), (16, cy - 10))
            draw_text(s, f"{int(max(0, self.h) / 10)}M", 24, 190, "white", align="center", shadow=None)
        # right: stage, lives, fever, power-ups, stars
        x0 = FX0 + FW + 3
        draw_text(s, "STAGE", x0, 3, "lavender", shadow=None)
        draw_text(s, f"{self.n}", x0 + 21, 12, "yellow", 2, align="center", outline="ink", shadow=None)
        self.hearts(s, x0, 30, self.lives, max_show=4)
        draw_text(s, "FEVER", x0, 42, "orange" if not self.hype.fever_on else rainbow(0, t), shadow=None)
        s.fill(col("darkgray"), (x0, 51, 40, 4))
        if self.hype.fever_on:
            for i in range(40):
                s.fill(col(rainbow(i // 5, t)), (x0 + i, 51, 1, 4))
        else:
            s.fill(col("orange"), (x0, 51, int(40 * self.hype.fever), 4))
        y = 61
        # pounces left this jump
        draw_text(s, "POUNCE", x0, y, "pink", shadow=None)
        for i in range(1 + self.lv("double")):
            c = "hotpink" if i < self.pounces else "darkgray"
            pygame.draw.circle(s, col(c), (x0 + 4 + i * 9, y + 13), 3)
            s.fill(col("white" if i < self.pounces else "gray"), (x0 + 3 + i * 9, y + 12, 1, 1))
        y += 22
        for name, v, full, c in (("ROCKET", self.rocket_t, 2.2 + 0.45 * self.lv("rocket"), "orange"),
                                 ("PARASOL", self.parasol_t, 10.0, "pink"), ("MAGNET", self.magnet_t, 12.0, "red")):
            if v > 0 and (v > 2 or int(t * 8) % 2):
                draw_text(s, name, x0, y, c, shadow=None)
                s.fill(col("darkgray"), (x0, y + 8, 40, 2))
                s.fill(col(c), (x0, y + 8, int(40 * min(1.0, v / full)), 2))
                y += 14
        if self.shield:
            _icon_bell(s, x0 + 6, y + 5, t)
            draw_text(s, "BELL", x0 + 15, y + 2, "yellow", shadow=None)
            y += 14
        if self.cushion:
            draw_cloud(s, x0, y + 2, 14, D.K_F, t, 0.0, face=False)
            draw_text(s, f"x{self.cushion}", x0 + 18, y + 3, "white", shadow=None)
            y += 14
        if k != "boss":
            s.blit(sprite("star"), (x0, 168))
            draw_text(s, f"{self.got_stars}", x0 + 10, 168, "yellow", shadow=None)
            if self.fish:
                draw_fish_icon(s, x0 + 4, 186, "sky")
                draw_text(s, f"{self.got_fish}/{len(self.fish)}", x0 + 15, 183, "sky", shadow=None)
        if self.boss and self.boss.state != "dead" and self.state in ("play", "intro"):
            boss_bar(s, self.boss.name, self.boss.hp, self.boss.maxhp, t, y=2, x=FX0 + 4, w=FW - 8)

    def draw_intro(self, s, t):
        st = self.st
        k = st["kind"]
        cx = FX0 + FW // 2
        if k == "boss":
            if int(t * 4) % 2:
                for x in range(FX0 - 20, FX0 + FW + 20, 20):
                    pygame.draw.polygon(s, col("red"), [(x, 108), (x + 10, 108), (x + 20, 116), (x + 10, 116)])
                    pygame.draw.polygon(s, col("red"), [(x, 158), (x + 10, 158), (x + 20, 166), (x + 10, 166)])
            panel(s, (cx - 100, 120, 200, 34), fill="black", border="red")
            draw_text(s, "WARNING!!", cx, 124, "red" if int(t * 6) % 2 else "yellow", 2, align="center", outline="ink")
            draw_text(s, f"{st['name']} APPROACHES", cx, 141, "white", align="center", shadow=None)
            return
        weather = self.weather_line()
        h = 56 + (10 if st["new"] else 0) + (10 if weather else 0)
        y0 = 34
        panel(s, (cx - 104, y0, 208, h), fill="ink", border="yellow" if k == "bonus" else self.theme[4])
        if k == "bonus":
            title = "BONUS STAGE"
            for i, ch in enumerate(title):
                draw_text(s, ch, cx - text_width(title, 2) // 2 + i * 12, y0 + 6 + int(math.sin(t * 8 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            sub = {"stars": "GRAB STARS - CLIMB TO THE MOON!", "rocket": "RIDE THE ROCKET, CATCH STARS!",
                   "balloons": "POP ALL THE BALLOONS!"}[st["bonus"]]
            draw_text(s, st["name"], cx, y0 + 26, "yellow", align="center")
            draw_text(s, sub, cx, y0 + 38, "white", align="center", shadow=None)
            return
        draw_text(s, f"STAGE {self.n}", cx, y0 + 6, "yellow", 2, align="center", outline="ink", shadow=None)
        draw_text(s, self.theme[0], cx, y0 + 25, "lavender", align="center", shadow=None)
        draw_text(s, st["name"], cx, y0 + 35, "white", align="center", shadow=None)
        y = y0 + 46
        if st["new"]:
            draw_text(s, st["new"], cx, y, "mint" if int(t * 4) % 2 else "lime", align="center", shadow=None)
            y += 10
        if weather:
            draw_text(s, weather, cx, y, "sky", align="center", shadow=None)
            y += 10
        draw_text(s, D.QUIPS[(self.n * 3) % len(D.QUIPS)], cx, y, "pink", align="center", shadow=None)

    def weather_line(self):
        w = []
        if self.wind:
            w.append("GUSTS")
        if self.fog:
            w.append("RISING FOG")
        if self.hail_rate:
            w.append("HAIL")
        return ("WEATHER: " + " + ".join(w)) if w else ""

    def draw_tally(self, s, t):
        rows = self.tally
        cx = FX0 + FW // 2
        h = 46 + len(rows) * 11
        y0 = 84
        panel(s, (cx - 98, y0, 196, h), fill="ink", border="mint")
        head = {"boss": "BOSS CLEAR!", "bonus": "BONUS OVER!"}.get(self.st["kind"], f"STAGE {self.n} CLEAR!")
        draw_text(s, head, cx, y0 + 6, "mint", align="center")
        for i, (label, v, shown) in enumerate(rows):
            if i > self.tally_i:
                break
            y = y0 + 20 + i * 11
            draw_text(s, label, cx - 90, y, "white" if v else "gray", shadow=None)
            draw_text(s, f"{int(shown)}", cx + 90, y, "yellow" if v else "darkgray", align="right", shadow=None)
        draw_text(s, self.tally_line(), cx, y0 + h - 22, "pink", align="center", shadow=None)
        if self.tally_i >= len(rows) and int(t * 3) % 2:
            draw_text(s, "PRESS Z", cx, y0 + h - 11, "lavender", align="center", shadow=None)


# ----------------------------------------------------------------------------- drawing helpers
CLOUD_COL = {D.K_F: ("white", "lavender", "cream"), D.K_T: ("cream", "gray", "peach"),
             D.K_M: ("white", "sky", "sky"), D.K_R: ("gray", "darkgray", "darkgray"),
             D.K_S: ("white", "hotpink", "pink"), D.K_Z: ("darkgray", "ink", "ink"),
             D.K_G: ("lavender", "purple", "purple"), D.K_W: ("mint", "teal", "teal")}


def puff(s, c, cx, cy, r):
    """A round cloud tuft (an ellipse in a (2r+1) box: smooth, and identical on iOS)."""
    pygame.draw.ellipse(s, col(c), (cx - r, cy - r, 2 * r + 1, 2 * r + 1))


def draw_cloud(s, x, y, w, k, t, sq=0.0, face=True, state=0, wind=0):
    """A puffy cloud whose walkable top is at y (x = left edge)."""
    y += int(sq * 10)
    body, rim, shade = CLOUD_COL[k]
    if k == D.K_Z:
        body = ("darkgray", "purple" if int(t * 12) % 2 else "yellow", "white")[state]
    if k == D.K_T:           # a puff cloud: little separate tufts that pop
        n = max(2, w // 8)
        for i in range(n):
            cx = x + 4 + (w - 8) * i // (n - 1)
            puff(s, "sky", cx, y + 5, 4)
        for i in range(n):
            cx = x + 4 + (w - 8) * i // (n - 1)
            puff(s, "white", cx, y + 5, 3)
            s.fill(col("cream"), (cx - 1, y + 7, 3, 1))
            s.fill(col("lavender"), (cx + 1, y + 3, 1, 1))
        return
    n = max(2, w // 10)
    top = y + 4
    pygame.draw.rect(s, col(rim), (x - 1, y + 2, w + 2, 9), border_radius=4)
    for i in range(n):
        puff(s, rim, x + 4 + (w - 8) * i // (n - 1), top, 5 + (i % 2))
    pygame.draw.rect(s, col(body), (x, y + 3, w, 7), border_radius=3)
    for i in range(n):
        puff(s, body, x + 4 + (w - 8) * i // (n - 1), top, 4 + (i % 2))
    if k == D.K_S:           # rainbow stripes
        for i, c in enumerate(("hotpink", "orange", "yellow", "lime", "sky")):
            s.fill(col(c), (x + 2, y + 3 + i, w - 4, 1))
    s.fill(col(shade), (x + 2, y + 9, w - 4, 1))
    s.fill(col("white"), (x + 3, top - 3, 2, 1))
    if k == D.K_M:
        for sx in (-1, 1):
            ax = x - 4 if sx < 0 else x + w + 2
            s.fill(col("sky"), (ax, y + 5, 2, 1))
            s.fill(col("sky"), (ax + (1 if sx < 0 else 0), y + 4, 1, 3))
    elif k == D.K_R:
        for i in range(max(1, w // 8)):
            dx = x + 3 + i * 8 + (i % 2) * 3
            dy = y + 11 + int(t * 30 + i * 5) % 9
            s.fill(col("sky"), (dx, dy, 1, 2))
    elif k == D.K_Z:
        bx = x + w // 2
        pygame.draw.lines(s, col("yellow" if state != 1 else "white"), False,
                          [(bx - 2, y + 2), (bx + 1, y + 5), (bx - 1, y + 6), (bx + 2, y + 9)])
    elif k == D.K_W:
        a = t * 6
        for i in range(3):
            s.fill(col("white"), (x + w // 2 + int(math.cos(a + i * 2.1) * 4), y + 5 + int(math.sin(a + i * 2.1) * 2), 1, 1))
        if wind > 0:
            pygame.draw.polygon(s, col("teal"), [(x + w + 2, y + 3), (x + w + 2, y + 9), (x + w + 5, y + 6)])
        else:
            pygame.draw.polygon(s, col("teal"), [(x - 2, y + 3), (x - 2, y + 9), (x - 5, y + 6)])
    if face and w >= 32 and k in (D.K_F, D.K_M, D.K_G, D.K_W, D.K_R):
        cx = x + w // 2
        if sq > 0:
            s.fill(col("black"), (cx - 4, y + 5, 2, 1))
            s.fill(col("black"), (cx + 3, y + 5, 2, 1))
            s.fill(col("black"), (cx - 1, y + 7, 3, 1))
        else:
            blink = int(t * 0.8 + x * 0.1) % 6 == 0
            s.fill(col("black"), (cx - 4, y + 5, 1, 1 if blink else 2))
            s.fill(col("black"), (cx + 4, y + 5, 1, 1 if blink else 2))
            s.fill(col("pink"), (cx - 6, y + 7, 2, 1))
            s.fill(col("pink"), (cx + 5, y + 7, 2, 1))
            if k == D.K_G:
                pygame.draw.circle(s, col("black"), (cx, y + 8), 1)
            else:
                s.fill(col("black"), (cx - 1, y + 7, 1, 1))
                s.fill(col("black"), (cx + 1, y + 7, 1, 1))
                s.fill(col("black"), (cx, y + 8, 1, 1))


def draw_balloon(s, x, y, c, t):
    y += int(math.sin(t * 3 + x) * 1)
    pygame.draw.ellipse(s, col("black"), (x - 5, y - 6, 11, 13))
    pygame.draw.ellipse(s, col(c), (x - 4, y - 5, 9, 11))
    s.fill(col("white"), (x - 2, y - 3, 2, 2))
    s.fill(col(c), (x - 1, y + 6, 3, 2))


def draw_rocket(s, x, y, t, flame=False):
    """A catnip rocket (x, y = its nose under SORA)."""
    pygame.draw.rect(s, col("black"), (x - 4, y - 1, 9, 12), border_radius=3)
    pygame.draw.rect(s, col("mint"), (x - 3, y, 7, 10), border_radius=3)
    s.fill(col("lime"), (x - 1, y + 2, 3, 3))
    s.fill(col("white"), (x - 2, y + 1, 1, 3))
    s.fill(col("red"), (x - 5, y + 7, 2, 4))
    s.fill(col("red"), (x + 4, y + 7, 2, 4))
    if flame:
        fl = 4 + int(t * 30) % 4
        pygame.draw.polygon(s, col("orange"), [(x - 3, y + 11), (x + 3, y + 11), (x, y + 11 + fl + 3)])
        pygame.draw.polygon(s, col("yellow"), [(x - 1, y + 11), (x + 1, y + 11), (x, y + 11 + fl)])


def draw_parasol(s, x, y, t):
    pygame.draw.polygon(s, col("black"), [(x - 11, y + 5), (x, y - 4), (x + 11, y + 5)])
    pygame.draw.polygon(s, col("pink"), [(x - 9, y + 4), (x, y - 2), (x + 9, y + 4)])
    s.fill(col("white"), (x - 3, y + 1, 2, 3))
    s.fill(col("white"), (x + 3, y + 1, 2, 3))
    s.fill(col("brown"), (x, y + 4, 1, 8))


def draw_fish_icon(s, x, y, c):
    pygame.draw.ellipse(s, col(c), (x - 4, y - 2, 8, 5))
    pygame.draw.polygon(s, col(c), [(x + 3, y), (x + 7, y - 3), (x + 7, y + 3)])
    s.fill(col("black"), (x - 2, y - 1, 1, 1))


def draw_item(s, it, x, y, t):
    k = it.k
    bob = int(math.sin(t * 4 + it.ph) * 1.5)
    if k == D.I_STAR:
        sp = sprite("star")
        s.blit(sp, (x - 3, y - 3 + bob))
        if int(t * 5 + it.ph) % 6 == 0:
            s.fill(col("white"), (x + 3, y - 4 + bob, 1, 1))
        return
    if k == D.I_BALLOON:
        c = "yellow" if it.gold else BALLOON_COLS[int(it.ph) % len(BALLOON_COLS)]
        draw_balloon(s, x, y + bob, c, t)
        pygame.draw.line(s, col("white"), (x, y + 8 + bob), (x + 1, y + 14 + bob))
        if it.gold and int(t * 8) % 2:
            s.fill(col("white"), (x + 4, y - 7 + bob, 1, 1))
        return
    if k == D.I_GOLD:
        y += bob
        pygame.draw.ellipse(s, col("orange"), (x - 6, y - 4, 11, 8))
        pygame.draw.ellipse(s, col("yellow"), (x - 5, y - 3, 9, 6))
        pygame.draw.polygon(s, col("orange"), [(x + 4, y), (x + 8, y - 4), (x + 8, y + 4)])
        s.fill(col("black"), (x - 3, y - 1, 1, 1))
        if int(t * 10) % 2:
            s.fill(col("white"), (x - 6, y - 6, 1, 1))
        return
    y += bob
    tint = {D.I_ROCKET: "orange", D.I_BELL: "yellow", D.I_PARASOL: "pink", D.I_MAGNET: "red",
            D.I_MILK: "white"}.get(k, "sky")
    bubble(s, x, y, 7, t, tint)
    if k == D.I_ROCKET:
        draw_rocket(s, x, y - 4, t)
    elif k == D.I_BELL:
        _icon_bell(s, x, y - 1, t)
    elif k == D.I_PARASOL:
        draw_parasol(s, x, y - 2, t)
    elif k == D.I_MAGNET:
        _icon_magnet(s, x, y, t)
    else:
        s.fill(col("white"), (x - 2, y - 3, 5, 7))
        s.fill(col("sky"), (x - 1, y - 5, 3, 2))
        s.fill(col("pink"), (x - 2, y, 5, 2))


def draw_foe(s, f, x, y, t, tier):
    k = f.k
    dead = not f.alive
    for xd in (0, -FW, FW):
        xx = x + xd
        if not (-16 < xx < FW + 16):
            continue
        if k == D.E_BIRD:
            c = BIRD_COLS[(tier + int(f.ph)) % len(BIRD_COLS)]
            flap = int(math.sin(t * 16 + f.ph) * 3)
            d = f.a
            pygame.draw.circle(s, col("black"), (xx, y), 6)
            pygame.draw.circle(s, col(c), (xx, y), 5)
            s.fill(col("white"), (xx - 2 * d - 1, y + 1, 3, 2))
            pygame.draw.polygon(s, col("orange"), [(xx + d * 5, y - 1), (xx + d * 9, y + 1), (xx + d * 5, y + 2)])
            pygame.draw.ellipse(s, col("black"), (xx - d * 3 - 3, y - 4 - flap, 7, 5))
            pygame.draw.ellipse(s, col("white"), (xx - d * 3 - 2, y - 3 - flap, 5, 3))
            if dead:
                s.fill(col("black"), (xx + d * 2 - 1, y - 3, 3, 1))
                s.fill(col("black"), (xx + d * 2, y - 4, 1, 3))
            else:
                s.fill(col("black"), (xx + d * 2, y - 2, 1, 2))
                s.fill(col("black"), (xx + d * 1, y - 4, 2, 1))
        elif k == D.E_KITE:
            if not dead:
                for i in range(0, 40, 3):
                    s.fill(col("white"), (xx + int(math.sin(i * 0.2 + t) * 2), y + 9 + i, 1, 1))
            c1, c2 = (("red", "yellow"), ("sky", "white"), ("hotpink", "lavender"), ("lime", "teal"))[int(f.ph) % 4]
            pts = [(xx, y - 9), (xx + 7, y), (xx, y + 9), (xx - 7, y)]
            pygame.draw.polygon(s, col("black"), [(xx, y - 10), (xx + 8, y), (xx, y + 10), (xx - 8, y)])
            pygame.draw.polygon(s, col(c1), pts)
            pygame.draw.polygon(s, col(c2), [(xx, y - 9), (xx + 7, y), (xx, y)])
            pygame.draw.polygon(s, col(c2), [(xx, y), (xx - 7, y), (xx, y + 9)])
            cute.eyes(s, xx, y - 1, 2, 0, "wow" if dead else "angry")
            for i in range(4):     # ribbon bows
                bx = xx + int(math.sin(t * 5 + i + f.ph) * 3) - 2
                by = y + 10 + i * 5
                s.fill(col(rainbow(i, 0)), (bx, by, 2, 2))
                s.fill(col(rainbow(i, 0)), (bx + 3, by, 2, 2))
        elif k == D.E_DOT:
            r = 4 + int(t * 8) % 3
            pygame.draw.circle(s, col("hotpink"), (xx, y), r, 1)
            pygame.draw.circle(s, col("red"), (xx, y), 2)
            s.fill(col("white"), (xx, y - 1, 1, 1))
        else:
            for i in range(4):
                a = t * 9 + i * 1.57
                ex = xx + int(math.cos(a) * 6)
                ey = y + int(math.sin(a) * 6)
                pygame.draw.line(s, col("yellow"), (xx, y), (ex, ey))
            pygame.draw.circle(s, col("orange"), (xx, y), 4)
            pygame.draw.circle(s, col("yellow"), (xx, y), 3)
            s.fill(col("white"), (xx - 1, y - 1, 2, 2))


# ----------------------------------------------------------------------------- autopilot (GIF bot + tests)
def autopilot(sc):
    """A simple player: aim for the best cloud this bounce can reach, pounce bosses from above."""
    keys = set()
    if sc.overlay is not None:
        if int(sc.t * 60) % 20 == 0:
            keys.add("a")
        return keys
    if sc.state in ("intro", "tally"):
        if int(sc.t * 60) % 30 == 0 and sc.state_t > 0.6:
            keys.add("a")
        return keys
    if sc.state != "play":
        return keys
    x, h, vh = sc.x, sc.h, sc.vh
    vmax = sc.vx_max()
    target = None
    if sc.boss and sc.boss.state == "fight":
        z = sc.boss.stomp_zone()
        if z is not None:
            zx, zh, hw = z
            apex = h + max(0.0, vh) ** 2 / (2 * D.G)
            if apex > zh + 6:
                target = zx
                if vh < 40 and abs(D.wrapd(zx - x)) < hw and h > zh + 4:
                    keys.add("a")
    if target is None and sc.st["kind"] == "bonus" and sc.st["bonus"] in ("balloons", "rocket"):
        cand = [it for it in sc.items if it.h > h - 20] or sc.items
        if cand:
            target = min(cand, key=lambda it: abs(it.h - h - 30) + abs(D.wrapd(it.x - x))).x
    if target is None:
        best = None
        for c in sc.clouds:
            if not sc.solid(c) or c.k == D.FLOOR or (c.k == D.K_Z and sc.zap_u(c) > 0.55):
                continue
            dy = c.h - h
            disc = vh * vh - 2 * D.G * dy
            if disc < 0:
                continue
            tl = (vh + math.sqrt(disc)) / D.G
            if tl <= 0.05:
                continue
            dx = abs(D.wrapd(c.cx() - x))
            if dx - c.w / 2 + 4 > vmax * tl * 0.85:
                continue
            score = c.h + (40 if c.k == D.K_S else 0) - (25 if c.k == D.K_R else 0) - dx * 0.05
            if best is None or score > best[0]:
                best = (score, c)
        if best:
            target = best[1].cx()
        else:
            items = [it for it in sc.items if abs(it.h - h) < 60]
            if items:
                target = items[0].x
    if target is not None:
        dx = D.wrapd(target - x)
        if abs(dx) > 3:
            keys.add("right" if dx > 0 else "left")
    return keys


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys."""
    return lambda frame: autopilot(scene)


def preview(s, t):
    w, h = s.get_size()
    for y in range(0, h, 3):
        s.fill(lerp_col("sky", "deep", 1 - y / h), (0, y, w, 3))
    for i in range(12):
        s.fill(col("white" if (i + int(t * 3)) % 3 else "yellow"), ((i * 37) % w, (i * 23) % (h // 2), 1, 1))
    pygame.draw.circle(s, col("yellow"), (w - 18, 14), 9)
    pygame.draw.circle(s, col("cream"), (w - 18, 14), 8)
    cute.eyes(s, w - 18, 14, 3, 0, "sleepy")
    off = (t * 24) % 30
    for i in range(4):
        cy = int(i * 30 - 20 + off)
        cx = (i * 47 + 20) % (w - 40) + 4
        draw_cloud(s, cx, cy, 32 if i % 2 else 24, D.K_S if i == 2 else D.K_F, t)
    by = h - 13 - abs(math.sin(t * 3)) * 30
    bx = w // 2 + int(math.sin(t * 1.3) * 26)
    draw_cloud(s, bx - 16, h - 14, 32, D.K_F, t, 0.15 if abs(math.sin(t * 3)) < 0.15 else 0.0)
    name = "cp_star" if abs(math.cos(t * 3)) < 0.4 else ("cp_up" if math.cos(t * 3) > 0 else "cp_fall")
    s.blit(sprite(name), (bx - 8, int(by) - 16))
    for i, (fx, fy) in enumerate(((10, 30), (16, 25), (16, 35), (24, 30), (29, 25), (29, 35))):
        c = "yellow" if (i + int(t * 4)) % 6 else "white"
        s.fill(col(c), (fx - 1, fy, 3, 1))
        s.fill(col(c), (fx, fy - 1, 1, 3))
