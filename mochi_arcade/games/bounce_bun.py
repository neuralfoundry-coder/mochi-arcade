"""BOUNCE BUN - a brick-breaking game with a bun paddle and snack bricks (original game).

A 200-stage campaign through 20 bakeries (bounce_bun_stages.py), a boss on every 10th stage
(bounce_bun_boss.py), bonus stages on every x5 stage and upgrade cards that last for the whole run.
The iOS port (ios/MochiArcade/Games/BounceBun*.swift) mirrors this file and reads the stage table from EXPORT.
"""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.games.bounce_bun_boss import Boss
from mochi_arcade.games.bounce_bun_stages import CAMPAIGN, COLS, PICTURES, THEMES
from mochi_arcade.gfx import H, W, col, draw_text, panel, render_text, sprite, text_width

LEFT, RIGHT, TOP = 8, W - 8, 20
BRW, BRH = 16, 8
BX0, BY0 = 16, 30
PADDLE_Y = 182
KIND = {"c": "cookie", "p": "candy", "m": "mint", "l": "lemon", "b": "berry", "h": "choco", "H": "fudge",
        "t": "tin", "$": "gold", "x": "bomb", "?": "gift", "r": "jelly", "k": "key", "L": "lock", "*": "bumper",
        "o": "portal", "O": "portal2", "C": "coin"}
HP = {"choco": 2, "fudge": 3, "gold": 3}
POINTS = {"cookie": 50, "candy": 60, "mint": 70, "lemon": 80, "berry": 90, "choco": 120, "fudge": 200, "gold": 1000,
          "bomb": 80, "gift": 100, "jelly": 60, "key": 300, "lock": 150, "coin": 150}
SOLID_ONLY = ("tin", "bumper")
PORTALS = ("portal", "portal2")
COLORS = {"cookie": ("peach", "brown"), "candy": ("pink", "white"), "mint": ("mint", "white"),
          "lemon": ("yellow", "white"), "berry": ("lavender", "purple"), "choco": ("brown", "choco"),
          "fudge": ("choco", "black"), "gold": ("yellow", "white", "orange"), "bomb": ("hotpink", "red", "yellow"),
          "gift": ("lavender", "yellow"), "jelly": ("mint", "teal"), "key": ("yellow", "orange"),
          "lock": ("gray", "pink"), "coin": ("yellow", "orange")}
CAPS = {"W": ("sky", "WIDE BUN!"), "M": ("pink", "MULTI BALL!"), "S": ("mint", "SLOW DOWN"),
        "G": ("yellow", "STICKY GLUE"), "F": ("orange", "FIREBALL!"), "L": ("lavender", "LASERS!"),
        "+": ("red", "EXTRA LIFE!"), "$": ("yellow", "GOLD!")}
TIMED = ("wide", "slow", "glue", "fire", "laser")
LIFE_AT = [20000, 60000, 120000, 200000]      # then every 150000

LEVELS = PICTURES   # the curated picture library (name, 18-column rows), also exported to Swift by gen_data
EXPORT = {"stages": CAMPAIGN, "themes": [list(t) for t in THEMES]}


# ----------------------------------------------------------------------------- upgrade cards
def _icon_wide(s, cx, cy, t):
    w = 14 + int(math.sin(t * 4) * 3)
    pygame.draw.rect(s, col("peach"), (cx - w // 2, cy - 2, w, 5), border_radius=2)
    s.fill(col("cream"), (cx - w // 2 + 2, cy - 1, w - 4, 1))


def _icon_ball(c):
    def f(s, cx, cy, t):
        pygame.draw.circle(s, col(c), (cx, cy), 4)
        s.fill(col("white"), (cx - 2, cy - 2, 1, 1))
    return f


def _icon_laser(s, cx, cy, t):
    for dx in (-4, 4):
        s.fill(col("sky"), (cx + dx, cy - 6 + int(t * 20) % 4, 1, 5))
    s.fill(col("peach"), (cx - 6, cy + 4, 13, 3))


def _icon_twin(s, cx, cy, t):
    for dx in (-3, 3):
        pygame.draw.circle(s, col("hotpink"), (cx + dx, cy + (dx // 3) * int(math.sin(t * 6) * 2)), 3)


def _icon_sticky(s, cx, cy, t):
    pygame.draw.circle(s, col("hotpink"), (cx, cy - 2), 3)
    s.fill(col("yellow"), (cx - 7, cy + 2, 15, 3))
    s.fill(col("yellow"), (cx - 1, cy + 1, 3, 1))


def _icon_magnet(s, cx, cy, t):
    pygame.draw.rect(s, col("red"), (cx - 6, cy - 6, 4, 10))
    pygame.draw.rect(s, col("red"), (cx + 3, cy - 6, 4, 10))
    pygame.draw.rect(s, col("red"), (cx - 6, cy + 1, 13, 4))
    s.fill(col("white"), (cx - 6, cy - 6, 4, 2))
    s.fill(col("white"), (cx + 3, cy - 6, 4, 2))


def _icon_calm(s, cx, cy, t):
    pygame.draw.circle(s, col("mint"), (cx, cy), 6, 1)
    a = t * 2
    s.fill(col("white"), (cx + int(math.cos(a) * 4), cy + int(math.sin(a) * 4), 1, 1))
    s.fill(col("mint"), (cx, cy - 4, 1, 4))


def _icon_net(s, cx, cy, t):
    for i in range(-6, 7, 3):
        s.fill(col("lime"), (cx + i, cy + 3, 2, 1))
    pygame.draw.circle(s, col("hotpink"), (cx, cy - 2 - abs(int(math.sin(t * 5) * 3))), 2)


def _icon_luck(s, cx, cy, t):
    w = max(1, int(abs(math.cos(t * 3)) * 5))
    pygame.draw.ellipse(s, col("orange"), (cx - w, cy - 5, w * 2 + 1, 11))
    pygame.draw.ellipse(s, col("yellow"), (cx - w + 1, cy - 4, max(1, w * 2 - 1), 9))


def _icon_fever(s, cx, cy, t):
    for i in range(3):
        c = rainbow(i, t)
        pygame.draw.circle(s, col(c), (cx - 4 + i * 4, cy + 1 - (i % 2) * 3), 2)


UPGRADES = [
    Upgrade("wide", "BIG BUN", "A WIDER|BUN PADDLE", "peach", _icon_wide, 4),
    Upgrade("power", "POWER BALL", "+1 DAMAGE|CRACKS CHOCO|AND BOSSES", "red", _icon_ball("red"), 3),
    Upgrade("laser", "SPRINKLE GUN", "HOLD X TO|FIRE LASERS|FASTER EACH LV", "sky", _icon_laser, 3),
    Upgrade("twin", "TWIN START", "+1 GUMBALL|AT EVERY|LAUNCH", "pink", _icon_twin, 2),
    Upgrade("sticky", "STICKY BUN", "HOLD Z TO|CATCH THE|GUMBALL", "yellow", _icon_sticky, 1),
    Upgrade("magnet", "MAGNET", "PULLS|CAPSULES|TO THE BUN", "lavender", _icon_magnet, 3),
    Upgrade("calm", "CALM DOWN", "A SLOWER|GUMBALL", "mint", _icon_calm, 3),
    Upgrade("net", "SAFETY NET", "SAVES ONE|DROPPED BALL|EVERY STAGE", "lime", _icon_net, 2),
    Upgrade("life", "EXTRA LIFE", "+1 LIFE|RIGHT NOW", "hotpink", "heart", 5),
    Upgrade("luck", "LUCKY DOUGH", "MORE|CAPSULES AND|JACKPOTS", "orange", _icon_luck, 3),
    Upgrade("fever", "FEVER OVEN", "FEVER FILLS|FASTER AND|LASTS LONGER", "yellow", _icon_fever, 3),
]


# ----------------------------------------------------------------------------- objects
class Ball:
    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.stuck = None      # x offset from the paddle centre while held
        self.hold = False      # caught by STICKY BUN: launches when the button is released
        self.held_t = 0.0
        self.volley = 0        # bricks broken since the last paddle touch
        self.pcd = 0.0         # portal cooldown
        self.boost = 0.0       # bumper kick
        self.idle = 0.0        # time since the last brick / paddle touch


class Brick:
    def __init__(self, r, c, ch):
        self.r, self.c = r, c
        self.kind = KIND[ch]
        self.hp = self.maxhp = HP.get(self.kind, 1)
        self.alive = True
        self.flash = 0.0
        self.regrow = 0.0
        self.locked = self.kind == "lock"
        self.bump = 0.0
        self.x = float(BX0 + c * BRW)
        self.y = float(BY0 + r * BRH)

    @property
    def breakable(self):
        return self.kind not in SOLID_ONLY and self.kind not in PORTALS

    def rect(self):
        if self.kind == "bumper":
            return pygame.Rect(int(self.x) + 3, int(self.y), BRW - 6, BRH)
        return pygame.Rect(int(self.x), int(self.y), BRW, BRH)


class Cap:
    def __init__(self, x, y, k):
        self.x, self.y, self.k = x, y, k
        self.got = False


class Sweet:
    """Bonus CANDY RAIN: kind 0-7 snacks, 8 golden star, 9 sour drop (ouch)."""

    def __init__(self, x, vy, kind):
        self.x, self.y, self.vy, self.kind = x, float(TOP), vy, kind
        self.got = False


# ----------------------------------------------------------------------------- the game
class BounceBun(GameScene):
    @property
    def music(self):
        return self.song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES[d]
        self.base_speed = 125 * SPEED[d]
        self.levels = {}
        self.px = W / 2
        self.pdir = 0
        self.phold = 0.0
        self.pvel = 0.0
        self.stun = 0.0
        self.next_life = 0
        self.life_i = 0
        self.picks_left = 0
        self.pick_title = "POWER UP!"
        self.next_n = None
        self.was_fever = False
        start = int(opt.get("start", opt.get("level", 1)))
        start = max(1, min(STAGES, start))
        self.start_stage(start)
        if start > 1:          # starting from a checkpoint: catch up on some upgrades first
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

    def pw(self):
        w = 32 + 4 * self.lv("wide")
        if self.timers["wide"] > 0:
            w += 16
        if self.st["kind"] == "bonus" and self.st["bonus"] == "rain":
            w += 16
        return w

    def fire_on(self):
        return self.timers["fire"] > 0 or self.hype.fever_on

    def laser_lv(self):
        lv = self.lv("laser")
        return max(1, lv) if self.timers["laser"] > 0 else lv

    def ball_dmg(self):
        return 1 + self.lv("power")

    def fever_gain(self):
        return 0.03 * (1 + 0.35 * self.lv("fever"))

    def ball_x(self):
        free = [b for b in self.balls if b.stuck is None]
        return free[0].x if free else self.px

    def song(self):
        k = self.st["kind"]
        return "boss" if k == "boss" else "bonus" if k == "bonus" else "bounce"

    # ---------------------------------------------------------------- stages
    def start_stage(self, n):
        self.n = n
        st = self.st = CAMPAIGN[n - 1]
        self.tier = st["tier"]
        self.theme = THEMES[self.tier]
        self.reached(n)
        self.bricks = []
        self.cell = {}
        for r, row in enumerate(st["rows"]):
            for c, ch in enumerate(row):
                if ch in KIND:
                    br = Brick(r, c, ch)
                    self.bricks.append(br)
                    self.cell[(r, c)] = br
        self.portals = [br for br in self.bricks if br.kind in PORTALS]
        self.moves = {m[0]: m for m in st["moves"]}
        self.creep = 0.0
        self.total = sum(1 for br in self.bricks if br.breakable)
        self.coins_total = sum(1 for br in self.bricks if br.kind == "coin")
        self.boss = Boss(self, st["boss"]) if st["kind"] == "boss" else None
        self.caps, self.shots, self.booms, self.sweets = [], [], [], []
        self.timers = {k: 0.0 for k in TIMED}
        self.net = self.lv("net")
        self.laser_cd = 0.0
        self.stime = 0.0
        self.missed = False
        self.hurt = False
        self.stage_combo = 0
        self.coins = self.caught = self.golds = 0
        self.sweet_t = 0.0
        self.speed = self.base_speed * st["speed"]
        self.speed_cap = self.base_speed * min(1.9, st["speed"] * 1.45)
        self.bonus_left = float(st.get("time", 0))
        self.fresh = True
        self.lucky = st["kind"] == "normal" and self.hype.lucky(0.03 + 0.01 * self.lv("luck"))
        self.balls = []
        if not (st["kind"] == "bonus" and st["bonus"] == "rain"):
            self.reset_ball()
        self.state = "intro"
        self.state_t = 0.0
        self.intro_len = 3.0 if self.boss else 2.2
        self.tally = []
        self.bg = self.make_bg()
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.was_fever = False
        self.app.audio.music(self.song())
        self.app.audio.play("warning" if self.boss else "stage")
        if self.boss:
            self.hype.flash("red", 0.3)

    def reset_ball(self):
        b = Ball(self.px, PADDLE_Y - 4, 0, 0)
        b.stuck = 4.0
        self.balls = [b]
        self.fresh = True
        for k in TIMED:
            self.timers[k] = 0.0

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        s = self.state
        if s == "intro":
            self.move_paddle(dt)
            self.follow_stuck()
            if self.boss:
                self.boss.update(dt)
            if self.state_t > self.intro_len or (self.state_t > 0.5 and self.app.input.hit("a")):
                self.state = "play"
                self.state_t = 0.0
                if self.boss:
                    self.boss.state = "fight"
        elif s == "play":
            self.play(dt)
        elif s == "clear":
            for b in self.balls:
                if b.stuck is None:
                    self.move_ball(b, dt, floor=True)
            if self.state_t > 1.4:
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
        self.update_floaters(dt)

    def update_floaters(self, dt):
        for br in self.bricks:
            br.flash = max(0.0, br.flash - dt)
            br.bump = max(0.0, br.bump - dt)

    def on_pick(self, uid):
        if uid:
            self.levels[uid] = self.lv(uid) + 1
            u = next(x for x in UPGRADES if x.id == uid)
            self.hype.banner(u.name, f"LEVEL {self.levels[uid]}", color=u.color, dur=1.2, scale=1)
            if uid == "life":
                self.lives += 1
                self.app.audio.play("extra")
            elif uid == "net":
                self.net += 1

    def move_paddle(self, dt):
        inp = self.app.input
        d = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        if self.stun > 0:
            d = 0
        if d != self.pdir:
            self.phold = 0.0
        self.pdir = d
        v = 0.0
        if d:
            self.phold += dt
            v = 100 + min(1.0, self.phold / 0.22) * 170     # fine control first, then fast
        half = self.pw() / 2
        self.px = max(LEFT + half, min(RIGHT - half, self.px + d * v * dt))
        self.pvel = d * v

    def follow_stuck(self):
        half = self.pw() / 2
        for b in self.balls:
            if b.stuck is not None:
                b.stuck = max(-half + 2, min(half - 2, b.stuck))
                b.x, b.y = self.px + b.stuck, PADDLE_Y - 4

    def play(self, dt):
        inp, au = self.app.input, self.app.audio
        st = self.st
        self.stime += dt
        self.stun = max(0.0, self.stun - dt)
        for k in TIMED:
            self.timers[k] = max(0.0, self.timers[k] - dt)
        self.move_paddle(dt)
        half = self.pw() / 2
        # lasers
        self.laser_cd -= dt
        if self.laser_lv() > 0 and inp.down("b") and self.laser_cd <= 0 and self.stun <= 0:
            self.laser_cd = (0.5, 0.5, 0.38, 0.28)[min(3, self.laser_lv())]
            for dx in (-half + 3, half - 3):
                self.shots.append([self.px + dx, PADDLE_Y - 2])
            au.play("shoot")
        # balls on the bun
        self.follow_stuck()
        for b in self.balls:
            if b.stuck is None:
                continue
            b.held_t += dt
            if b.hold:
                if not inp.down("a") or b.held_t > 3.0:
                    self.launch(b)
            elif inp.hit("a"):
                self.launch(b)
        for b in self.balls:
            if b.stuck is None:
                self.move_ball(b, dt, floor=st["kind"] == "bonus" or (self.boss is not None and self.boss.state != "fight"))
        self.balls = [b for b in self.balls if b.y <= H + 6]
        if not self.balls and not (st["kind"] == "bonus" and st["bonus"] == "rain"):
            self.lose_life()
            if self.state != "play":
                return
        self.update_caps(dt)
        self.update_shots(dt)
        self.update_bricks(dt)
        if self.boss:
            self.boss.update(dt)
        if st["kind"] == "bonus":
            self.update_bonus(dt)
        self.stage_combo = max(self.stage_combo, self.hype.combo)
        # FEVER: its own song and a longer FEVER with the oven upgrade
        if self.hype.fever_on and not self.was_fever:
            self.hype.fever_t += 2 * self.lv("fever")
            au.music("fever")
        elif self.was_fever and not self.hype.fever_on:
            au.music(self.song())
        self.was_fever = self.hype.fever_on
        self.check_life()
        if self.state == "play" and st["kind"] == "normal" and not any(br.alive and br.breakable for br in self.bricks):
            self.stage_clear()

    def launch(self, b):
        half = self.pw() / 2
        ang = math.radians(max(-1.0, min(1.0, b.stuck / half)) * 45)
        sp = self.cur_speed(b)
        b.vx, b.vy = math.sin(ang) * sp, -math.cos(ang) * sp
        b.stuck = None
        b.hold = False
        b.volley = 0
        self.app.audio.play("paddle")
        if self.fresh:
            self.fresh = False
            if self.lucky:          # a rare lucky stage: FEVER from the first bounce
                self.lucky = False
                self.hype.banner("LUCKY BAKE!", "FEVER START", rainbow=True, dur=1.4)
                self.hype.start_fever()
            extra = self.lv("twin")
            if self.st["kind"] == "bonus":
                extra += 2
            for i in range(extra):
                a = ang + math.radians((25 + 10 * (i // 2)) * (1 if i % 2 == 0 else -1))
                self.balls.append(Ball(b.x, b.y, math.sin(a) * sp, -abs(math.cos(a) * sp)))

    def cur_speed(self, b=None):
        sp = self.speed * (1 - 0.06 * self.lv("calm"))
        if self.timers["slow"] > 0:
            sp *= 0.7
        if b is not None and b.boost > 0:
            sp *= 1.3
        return sp

    def lose_life(self):
        au = self.app.audio
        self.hype.break_combo()
        self.missed = True
        self.lives -= 1
        au.play("hurt")
        self.app.shake(3, 0.3)
        if self.lives <= 0:
            self.state = "over"
            self.hype.banner("GAME OVER", f"STAGE {self.n}", color="red", dur=3.0)
            au.play("gameover")
            self.end_game(False, f"STAGE {self.n}", delay=2.5)
            return
        self.hype.banner("OOPS!", f"{self.lives} LEFT", color="pink", dur=1.0, scale=1)
        self.caps = []
        self.reset_ball()

    def check_life(self):
        target = LIFE_AT[self.life_i] if self.life_i < len(LIFE_AT) else LIFE_AT[-1] + 150000 * (self.life_i - len(LIFE_AT) + 1)
        if self.score >= target:
            self.life_i += 1
            self.lives += 1
            self.hype.banner("BONUS LIFE!", f"{target} POINTS", color="pink", dur=1.4, sound="extra")
            self.hype.shower(16, "hearts")

    # ---------------------------------------------------------------- the gumball
    def move_ball(self, b, dt, floor=False):
        au = self.app.audio
        b.pcd = max(0.0, b.pcd - dt)
        b.boost = max(0.0, b.boost - dt)
        b.idle += dt
        target = self.cur_speed(b)
        sp = math.hypot(b.vx, b.vy) or 1
        b.vx, b.vy = b.vx / sp * target, b.vy / sp * target
        if b.idle > 8:          # stuck in a boring loop: nudge it
            b.idle = 0.0
            a = math.atan2(b.vx, -b.vy) + math.radians(random.choice((-9, 9)))
            b.vx, b.vy = math.sin(a) * target, -math.cos(a) * target
        steps = max(1, int(target * dt / 3) + 1)
        for _ in range(steps):
            b.x += b.vx * dt / steps
            b.y += b.vy * dt / steps
            if b.x < LEFT + 2:
                b.x, b.vx = LEFT + 2, abs(b.vx)
                au.play("tin")
            elif b.x > RIGHT - 2:
                b.x, b.vx = RIGHT - 2, -abs(b.vx)
                au.play("tin")
            if b.y < TOP + 2:
                b.y, b.vy = TOP + 2, abs(b.vy)
                au.play("tin")
            if b.y > 194 and b.vy > 0 and (floor or self.net > 0):
                b.y, b.vy = 194, -abs(b.vy)
                if not floor:
                    self.net -= 1
                    self.floats.add(b.x, 180, "SAVED!", "lime")
                    au.play("bubble")
                    self.parts.burst(b.x, 196, 10, ("lime", "white"), 50, 0.5)
            half = self.pw() / 2
            if b.vy > 0 and PADDLE_Y - 2 <= b.y + 2 <= PADDLE_Y + 5 and abs(b.x - self.px) <= half + 2:
                self.paddle_bounce(b, half, target)
                if b.stuck is not None:
                    return
            if self.collide_bricks(b):
                self.min_vy(b)
            if self.boss and self.collide_boss(b):
                self.min_vy(b)
            for p in self.portals:
                if b.pcd <= 0 and abs(b.x - (p.x + 8)) < 5 and abs(b.y - (p.y + 4)) < 4:
                    twin = next((q for q in self.portals if q is not p and q.kind == p.kind), None)
                    if twin:
                        self.parts.burst(b.x, b.y, 8, ("lavender", "white"), 40, 0.4)
                        b.x, b.y = twin.x + 8, twin.y + 4
                        b.pcd = 0.5
                        au.play("bubble")
                        self.parts.burst(b.x, b.y, 8, ("mint", "white"), 40, 0.4)
                        break

    def min_vy(self, b):
        """Never let the gumball fly almost flat (endless side-to-side loops)."""
        sp = math.hypot(b.vx, b.vy) or 1
        if abs(b.vy) < sp * 0.28:
            b.vy = math.copysign(sp * 0.28, b.vy or -1.0)
            b.vx = math.copysign(math.sqrt(max(0.0, sp * sp - b.vy * b.vy)), b.vx or 1.0)

    def paddle_bounce(self, b, half, target):
        off = max(-1.0, min(1.0, (b.x - self.px) / half))
        ang = math.radians(max(-65.0, min(65.0, off * 60 + (6 if self.pvel > 0 else -6 if self.pvel < 0 else 0))))
        b.vx, b.vy = math.sin(ang) * target, -math.cos(ang) * target
        b.y = PADDLE_Y - 3
        b.volley = 0
        b.idle = 0.0
        self.app.audio.play("paddle")
        catch = self.timers["glue"] > 0 or (self.lv("sticky") and self.app.input.down("a"))
        if catch and self.stun <= 0:
            b.stuck = b.x - self.px
            b.hold = self.timers["glue"] <= 0
            b.held_t = 0.0

    def collide_bricks(self, b):
        ball = pygame.Rect(int(b.x) - 2, int(b.y) - 2, 5, 5)
        fire = self.fire_on()
        hit = False
        for br in self.bricks:
            if not br.alive or br.kind in PORTALS:
                continue
            r = br.rect()
            if not r.colliderect(ball):
                continue
            if fire and br.breakable and not br.locked:
                self.hit_brick(br, 99, b)       # FEVER / fireball: burn straight through
                continue
            ox = min(ball.right - r.left, r.right - ball.left)
            oy = min(ball.bottom - r.top, r.bottom - ball.top)
            if ox < oy:
                if b.x < r.centerx:
                    b.vx, b.x = -abs(b.vx), b.x - ox - 0.5
                else:
                    b.vx, b.x = abs(b.vx), b.x + ox + 0.5
            else:
                if b.y < r.centery:
                    b.vy, b.y = -abs(b.vy), b.y - oy - 0.5
                else:
                    b.vy, b.y = abs(b.vy), b.y + oy + 0.5
            b.idle = 0.0 if br.breakable else b.idle
            if br.kind == "bumper":
                br.bump = 0.25
                b.boost = 0.45
                self.app.audio.play("pop")
                self.score_at(10)
                self.parts.burst(r.centerx, r.centery, 4, ("hotpink", "white"), 40, 0.3)
            else:
                self.hit_brick(br, self.ball_dmg(), b)
            hit = True
            break
        return hit

    def collide_boss(self, b):
        ball = pygame.Rect(int(b.x) - 2, int(b.y) - 2, 5, 5)
        for r, target in self.boss.colliders():
            if not r.colliderect(ball):
                continue
            ox = min(ball.right - r.left, r.right - ball.left)
            oy = min(ball.bottom - r.top, r.bottom - ball.top)
            if ox < oy:
                if b.x < r.centerx:
                    b.vx, b.x = -abs(b.vx), b.x - ox - 0.5
                else:
                    b.vx, b.x = abs(b.vx), b.x + ox + 0.5
            else:
                if b.y < r.centery:
                    b.vy, b.y = -abs(b.vy), b.y - oy - 0.5
                else:
                    b.vy, b.y = abs(b.vy), b.y + oy + 0.5
            b.idle = 0.0
            if self.boss.hit(target, self.ball_dmg() + (2 if self.fire_on() else 0)):
                self.hype.hit(1, fever=self.fever_gain())
            return True
        return False

    # ---------------------------------------------------------------- bricks
    def hit_brick(self, br, dmg, ball):
        au = self.app.audio
        k = br.kind
        if k in SOLID_ONLY or (k == "lock" and br.locked):
            br.flash = 0.15
            au.play("tin")
            return
        br.hp -= dmg
        if br.hp > 0:
            br.flash = 0.2
            if k == "gold":
                au.play("coin")
                for _ in range(4):
                    self.parts.sparkle(br.x + random.uniform(0, BRW), br.y + 4)
            else:
                au.play("tin")
            return
        self.break_brick(br, ball)

    def break_brick(self, br, ball):
        au = self.app.audio
        k = br.kind
        br.alive = False
        if k == "jelly":
            br.regrow = 6.0
        cx, cy = br.x + BRW / 2, br.y + BRH / 2
        vol = ball.volley if ball else 0
        self.hype.hit(1, fever=self.fever_gain())
        pts = POINTS[k] * (100 + 10 * min(vol, 20)) // 100 + self.hype.combo_bonus(2)
        self.score_at(pts, cx if pts >= 150 else None, cy - 4, "yellow")
        if ball:
            ball.volley += 1
            if ball.volley % 8 == 0:
                bonus = self.score_at(300 * (ball.volley // 8))
                self.floats.add(cx, cy - 12, f"RALLY x{ball.volley} +{bonus}", "mint")
                au.play("combo")
        self.speed = min(self.speed_cap, self.speed + 1.2)
        self.parts.burst(cx, cy, 8, COLORS.get(k, ("white",)), 50, 0.5)
        au.play("coin" if k == "coin" else "brick")
        if k == "coin":
            self.coins += 1
        if k == "bomb":
            self.booms.append([br.r, br.c, 0.12])
        elif k == "key":
            for q in self.bricks:
                if q.kind == "lock" and q.locked:
                    q.locked = False
                    q.flash = 0.3
            self.hype.banner("UNLOCKED!", color="yellow", dur=1.0, scale=1, sound="bonus")
        elif k == "gold":
            self.hype.jackpot(self.factor_pts(5000), None)
        if k == "gift":
            self.drop_cap(cx, cy, force=True)
        elif k not in ("coin", "gold"):
            self.drop_cap(cx, cy)

    def drop_cap(self, x, y, force=False):
        luck = self.lv("luck")
        if len(self.caps) >= 6 or self.st["kind"] == "bonus":
            return
        if not force and random.random() >= 0.09 + 0.03 * luck:
            return
        if random.random() < 0.015 * (1 + luck):
            k = "$"
        else:
            pool = "WWWMMMSSGG" + ("FF" if self.tier >= 1 else "") + ("LL" if self.tier >= 2 else "")
            k = "+" if random.random() < 0.05 else random.choice(pool)
        self.caps.append(Cap(x, y, k))

    def update_bricks(self, dt):
        t = self.stime
        if self.st["creep"]:
            self.creep = min(24.0, float(int(t / 6) * 2))
        for br in self.bricks:
            m = self.moves.get(br.r)
            off = math.sin(t * m[2] + m[3]) * m[1] if m else 0.0
            br.x = BX0 + br.c * BRW + off
            br.y = BY0 + br.r * BRH + self.creep
            if br.kind == "jelly" and not br.alive and br.regrow > 0:
                br.regrow -= dt
                if br.regrow <= 0:
                    if any(pygame.Rect(int(b.x) - 2, int(b.y) - 2, 5, 5).colliderect(br.rect()) for b in self.balls):
                        br.regrow = 0.5        # a gumball is in the way: try again in a moment
                    else:
                        br.alive, br.hp, br.flash = True, 1, 0.25
                        self.parts.burst(br.x + 8, br.y + 4, 6, ("mint", "teal"), 30, 0.3)
        for bm in self.booms:
            bm[2] -= dt
            if bm[2] <= 0:
                r0, c0 = bm[0], bm[1]
                src = self.cell.get((r0, c0))
                x, y = (src.x + 8, src.y + 4) if src else (BX0 + c0 * BRW + 8, BY0 + r0 * BRH + 4)
                self.parts.burst(x, y, 18, ("hotpink", "orange", "yellow", "white"), 90, 0.5)
                self.app.audio.play("explode")
                self.app.shake(2, 0.15)
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        q = self.cell.get((r0 + dr, c0 + dc))
                        if q and q.alive and q.breakable and not q.locked:
                            self.hit_brick(q, 1 if q.kind == "gold" else 99, None)
        self.booms = [bm for bm in self.booms if bm[2] > 0]

    def spawn_minions(self, n):
        """COOKIE JAR spits cookies that land as bricks."""
        spots = [(r, c) for r in range(7, 11) for c in range(COLS)
                 if not (self.cell.get((r, c)) and self.cell[(r, c)].alive)]
        random.shuffle(spots)
        made = 0
        for r, c in spots:
            if made >= n:
                break
            br = Brick(r, c, random.choice("cpml"))
            if any(pygame.Rect(int(b.x) - 2, int(b.y) - 2, 5, 5).colliderect(br.rect().inflate(4, 4)) for b in self.balls):
                continue
            br.flash = 0.3
            self.bricks.append(br)
            self.cell[(r, c)] = br
            self.parts.burst(br.x + 8, br.y + 4, 6, ("peach", "brown"), 40, 0.4)
            made += 1

    # ---------------------------------------------------------------- capsules, lasers, bonus
    def update_caps(self, dt):
        mag = self.lv("magnet")
        half = self.pw() / 2
        for cap in self.caps:
            cap.y += 52 * dt
            if mag and cap.y > 90 and abs(cap.x - self.px) < 30 + 25 * mag:
                d = self.px - cap.x
                cap.x += math.copysign(min(abs(d), (40 + 30 * mag) * dt), d)
            if PADDLE_Y - 3 <= cap.y <= PADDLE_Y + 7 and abs(cap.x - self.px) < half + 5:
                cap.got = True
                self.power(cap.k)
        self.caps = [c for c in self.caps if not c.got and c.y < H + 8]

    def power(self, k):
        au = self.app.audio
        au.play("powerup")
        self.floats.add(self.px, PADDLE_Y - 12, CAPS[k][1], "mint")
        if k == "W":
            self.timers["wide"] = 15.0
        elif k == "S":
            self.timers["slow"] = 10.0
        elif k == "G":
            self.timers["glue"] = 12.0
        elif k == "F":
            self.timers["fire"] = 8.0
        elif k == "L":
            self.timers["laser"] = 10.0
        elif k == "+":
            self.lives += 1
            au.play("extra")
        elif k == "$":
            self.hype.jackpot(self.factor_pts(3000), None)
        elif k == "M":
            src = [b for b in self.balls if b.stuck is None][:3] or self.balls[:1]
            for b0 in src:
                for a in (-25, 25):
                    if len(self.balls) >= 12:
                        break
                    base = math.atan2(b0.vx, -b0.vy) if (b0.vx or b0.vy) else 0.0
                    ang = base + math.radians(a)
                    sp = self.cur_speed()
                    self.balls.append(Ball(b0.x, min(b0.y, PADDLE_Y - 6), math.sin(ang) * sp, -abs(math.cos(ang) * sp)))
        self.score_at(100)

    def update_shots(self, dt):
        for sh in self.shots:
            sh[1] -= 300 * dt
            if sh[1] < TOP:
                sh[1] = -99
                continue
            for br in self.bricks:
                if br.alive and br.kind not in PORTALS and br.rect().collidepoint(int(sh[0]), int(sh[1])):
                    self.hit_brick(br, 1, None)
                    sh[1] = -99
                    break
            if sh[1] > 0 and self.boss:
                for r, target in self.boss.colliders():
                    if r.collidepoint(int(sh[0]), int(sh[1])):
                        if self.boss.hit(target, 1):
                            self.hype.hit(1, fever=self.fever_gain())
                        sh[1] = -99
                        break
        self.shots = [sh for sh in self.shots if sh[1] > 0]

    def update_bonus(self, dt):
        st = self.st
        self.bonus_left -= dt
        if st["bonus"] == "coins":
            if self.coins >= self.coins_total:
                self.hype.banner("ALL COINS!", color="yellow", dur=1.4, rainbow=True, sound="bonus")
                self.stage_clear()
                return
        else:
            self.sweet_t -= dt
            if self.sweet_t <= 0 and self.bonus_left > 0.8:
                prog = 1 - self.bonus_left / st["time"]
                self.sweet_t = 0.36 - 0.18 * prog
                roll = random.random()
                kind = 8 if roll < 0.05 else 9 if roll < 0.12 else random.randrange(8)
                self.sweets.append(Sweet(random.uniform(LEFT + 8, RIGHT - 8), random.uniform(50, 90) + 2 * self.tier,
                                         kind))
            half = self.pw() / 2
            for sw in self.sweets:
                sw.y += sw.vy * dt
                if PADDLE_Y - 4 <= sw.y <= PADDLE_Y + 6 and abs(sw.x - self.px) < half + 4:
                    sw.got = True
                    if sw.kind == 9:
                        self.paddle_hit(sw.x, PADDLE_Y + 2, 6)
                    else:
                        gold = sw.kind == 8
                        self.hype.hit(1, fever=0.05)
                        self.score_at(500 if gold else 100, sw.x, PADDLE_Y - 10, "yellow" if gold else "pink")
                        self.app.audio.play("coin" if gold else "eat")
                        self.parts.burst(sw.x, PADDLE_Y, 6, ("yellow", "white") if gold else ("pink", "white"), 40, 0.4)
                        if gold:
                            self.golds += 1
                        else:
                            self.caught += 1
            self.sweets = [sw for sw in self.sweets if not sw.got and sw.y < H + 6]
        if self.bonus_left <= 0:
            self.bonus_left = 0.0
            self.hype.banner("TIME UP!", color="yellow", dur=1.2)
            self.stage_clear()

    def paddle_hit(self, x, y, r, beam=False):
        """A boss shot (or a sour drop) touches the bun: dizzy for a moment. Returns True on contact."""
        half = self.pw() / 2
        if not beam and not (abs(x - self.px) <= half + r and PADDLE_Y - r - 1 <= y <= PADDLE_Y + 7 + r):
            return False
        if self.stun <= 0:
            self.stun = 0.9
            self.hurt = True
            self.hype.break_combo()
            self.app.audio.play("hurt")
            self.app.shake(3, 0.25)
            self.floats.add(self.px, PADDLE_Y - 10, "OUCH!", "red")
            self.parts.burst(self.px, PADDLE_Y, 8, ("red", "white"), 50, 0.4)
        return True

    # ---------------------------------------------------------------- clear / tally / boss
    def stage_clear(self):
        if self.state != "play":
            return
        self.state = "clear"
        self.state_t = 0.0
        self.caps = []
        self.sweets = []
        self.shots = []
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.hype.slowmo(0.25, 1.0)
        self.hype.flash("white", 0.2)
        self.app.audio.play("win")
        if self.st["kind"] == "normal":
            self.hype.banner("STAGE CLEAR!", color="mint", dur=1.4)
            self.hype.shower(30, "confetti")
        self.app.audio.music(None)
        self.was_fever = False

    def boss_defeated(self):
        g = self.hype
        self.app.audio.play("bossdown")
        g.banner("BOSS DOWN!", self.boss.name, rainbow=True, dur=2.2, scale=2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(40, "coins")
        self.app.shake(6, 0.6)
        self.score_at(15000, W / 2, 70)
        self.stage_clear()
        self.hype.slowmo(0.3, 1.2)

    def begin_tally(self):
        st = self.st
        f = self.factor_pts
        rows = []
        if st["kind"] == "normal":
            rows.append(("STAGE CLEAR", f(1000)))
            par = 40 + 0.6 * self.total
            rows.append(("TIME BONUS", f(max(0, int(par - self.stime)) * 20)))
        elif st["kind"] == "boss":
            rows.append(("BOSS BONUS", f(10000 + 2000 * self.tier)))
            rows.append(("NO DAMAGE", f(8000) if not self.hurt else 0))
        elif st["bonus"] == "coins":
            rows.append((f"COINS {self.coins}/{self.coins_total}", f(self.coins * 50)))
            rows.append(("ALL COINS", f(10000) if self.coins >= self.coins_total else 0))
        else:
            rows.append((f"SWEETS x{self.caught}", f(self.caught * 50)))
            rows.append((f"GOLDEN x{self.golds}", f(self.golds * 500)))
            rows.append(("NO OUCH", f(3000) if not self.hurt else 0))
        rows.append((f"BEST COMBO {self.stage_combo}", f(self.stage_combo * 40)))
        if st["kind"] != "bonus":
            rows.append(("NO MISS", f(5000) if not self.missed else 0))
        self.tally = [[label, v, 0.0] for label, v in rows]    # label, value, counted so far
        self.tally_i = 0
        self.tally_wait = 0.0
        self.state = "tally"
        self.state_t = 0.0
        if st["kind"] != "bonus" and not self.missed:
            self.hype.banner("PERFECT!", "NO BALL LOST", rainbow=True, dur=1.8, sound="fever")
            self.hype.shower(40, "stars")

    def update_tally(self, dt):
        skip = self.state_t > 0.3 and self.app.input.hit("a")
        if self.tally_i < len(self.tally):
            if skip:            # fast-forward: count everything at once
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
        if self.n >= STAGES:
            self.state = "over"
            self.hype.banner("ALL CLEAR!!", "THE BAKERIES ARE SAVED", rainbow=True, dur=5.0, sound="jackpot")
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
    def make_bg(self):
        name, a, b, pat, wall, _ = self.theme
        s = pygame.Surface((W, H))
        s.fill(col(a))
        cb = col(b)
        if pat == 0:
            for y in range(TOP, H, 12):
                for x in range(0, W, 12):
                    if (x // 12 + y // 12) % 2:
                        s.fill(cb, (x, y, 12, 12))
        elif pat == 1:
            for k in range(-H, W + H, 16):
                for i in range(5):
                    pygame.draw.line(s, cb, (k + i, H), (k + i + H - TOP, TOP))
        elif pat == 2:
            for y in range(TOP + 6, H, 14):
                for x in range(4 + (7 if (y // 14) % 2 else 0), W, 14):
                    pygame.draw.circle(s, cb, (x, y), 2)
        elif pat == 3:
            for y in range(TOP, H, 12):
                s.fill(cb, (0, y, W, 1))
                for x in range((0 if (y // 12) % 2 else 12), W, 24):
                    s.fill(cb, (x, y, 1, 12))
        else:
            for y in range(TOP + 8, H + 8, 12):
                for x in range(0, W + 12, 12):
                    pygame.draw.circle(s, cb, (x + (6 if (y // 12) % 2 else 0), y), 6, 1)
        s.fill(col("black"), (0, 0, W, TOP))
        for x0, w in ((0, LEFT), (RIGHT, W - RIGHT)):
            s.fill(col(wall), (x0, TOP, w, H - TOP))
            for y in range(TOP + 2, H, 8):
                s.fill(col("white"), (x0 + 2, y, w - 4, 1))
            s.fill(col("black"), (x0 + (w - 1 if x0 == 0 else 0), TOP, 1, H - TOP))
        s.fill(col("cream"), (0, TOP - 1, W, 1))
        return s

    def render(self, s):
        t = self.t
        s.blit(self.bg, (0, 0))
        for br in self.bricks:
            if br.alive or (br.kind == "jelly" and br.regrow > 0):
                draw_brick(s, br, t)
        if self.net > 0 or self.st["kind"] == "bonus" and self.st["bonus"] == "coins":
            for x in range(LEFT, RIGHT, 6):
                s.fill(col("lime" if int(t * 4) % 2 else "mint"), (x, 196, 3, 1))
        if self.boss:
            self.boss.draw(s, t)
        for cap in self.caps:
            draw_cap(s, cap.x, cap.y, cap.k, t)
        for sw in self.sweets:
            draw_sweet(s, sw, t)
        for sh in self.shots:
            s.fill(col("white"), (int(sh[0]), int(sh[1]), 1, 5))
            s.fill(col(rainbow(int(sh[1]) // 6, t)), (int(sh[0]), int(sh[1]) + 2, 1, 3))
        self.draw_paddle(s, t)
        fire = self.fire_on()
        for b in self.balls:
            x, y = int(b.x), int(b.y)
            if fire:
                for i in range(1, 4):
                    pygame.draw.circle(s, col(rainbow(i, t)), (int(b.x - b.vx * 0.012 * i), int(b.y - b.vy * 0.012 * i)), 3 - i // 2)
            pygame.draw.circle(s, col("black"), (x, y), 3)
            pygame.draw.circle(s, col(rainbow(0, t) if fire else "hotpink"), (x, y), 2)
            s.fill(col("white"), (x - 1, y - 1, 1, 1))
        if self.state == "play" and self.st["kind"] == "normal" and int(t * 4) % 2:
            left = [br for br in self.bricks if br.alive and br.breakable]
            if len(left) <= 3:      # point at the last few snacks
                for br in left:
                    x, y = int(br.x) + 8, int(br.y) - 3 - int(abs(math.sin(t * 6)) * 2)
                    pygame.draw.polygon(s, col("yellow"), [(x - 3, y - 3), (x + 3, y - 3), (x, y)])
        self.parts.draw(s)
        self.floats.draw(s)
        self.draw_hud(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "tally":
            self.draw_tally(s, t)
        elif self.state == "play" and any(b.stuck is not None and not b.hold for b in self.balls) and int(t * 3) % 2:
            draw_text(s, "PRESS Z TO LAUNCH", W // 2, 160, "white", align="center")
        if self.lv("sticky") and self.state == "play":
            for b in self.balls:
                if b.stuck is not None and b.hold:
                    self.draw_aim(s, b)

    def draw_aim(self, s, b):
        half = self.pw() / 2
        ang = math.radians(max(-1.0, min(1.0, b.stuck / half)) * 45)
        for i in range(1, 8):
            s.fill(col("white"), (int(b.x + math.sin(ang) * i * 7), int(b.y - math.cos(ang) * i * 7), 1, 1))

    def draw_paddle(self, s, t):
        w = int(self.pw())
        r = pygame.Rect(int(self.px - w / 2), PADDLE_Y, w, 7)
        dizzy = self.stun > 0
        body = "gray" if dizzy else ("yellow" if self.timers["glue"] > 0 or self.lv("sticky") and self.app.input.down("a") else "peach")
        pygame.draw.rect(s, col("black"), r.inflate(2, 2), border_radius=4)
        pygame.draw.rect(s, col(body), r, border_radius=4)
        s.fill(col("cream"), (r.x + 3, r.y + 1, r.w - 6, 2))
        for i in range(3):
            s.fill(col("choco"), (r.x + 6 + i * (r.w - 12) // 2, r.y + 3, 2, 1))
        if self.laser_lv() > 0:
            for x in (r.x + 1, r.right - 3):
                s.fill(col("sky"), (x, r.y - 2, 2, 3))
        if dizzy:
            for side in (-1, 1):
                a = t * 12 * side
                s.fill(col("black"), (r.centerx + side * 3 + int(math.cos(a)), r.y + 3 + int(math.sin(a)), 1, 1))
        else:
            cute.eyes(s, r.centerx, r.y + 3, 3, int(max(-1, min(1, self.pvel / 100))), "happy",
                      blink=int(t * 1.2) % 5 == 0)

    def draw_hud(self, s, t):
        draw_text(s, f"{self.score:07d}", 4, 3, "white", shadow=None)
        if self.boss and self.boss.state != "dead":
            boss_bar(s, self.boss.name, self.boss.hp, self.boss.maxhp, t)
        else:
            draw_text(s, f"HI {max(self.best, self.score):07d}", 4, 11, "gray", shadow=None)
            if self.st["kind"] == "bonus" and self.state in ("play", "intro"):
                secs = int(math.ceil(self.bonus_left))
                draw_text(s, f"TIME {secs:02d}", W // 2, 3, "yellow" if secs > 5 or int(t * 6) % 2 else "red",
                          align="center", shadow=None)
            else:
                draw_text(s, f"STAGE {self.n}", W // 2, 3, "yellow", align="center", shadow=None)
        self.hearts(s, W - 54, 3, self.lives)
        # FEVER gauge
        x0, y0 = W - 54, 13
        s.fill(col("darkgray"), (x0, y0, 48, 3))
        if self.hype.fever_on:
            for i in range(48):
                s.fill(col(rainbow(i // 6, t)), (x0 + i, y0, 1, 3))
        else:
            s.fill(col("orange"), (x0, y0, int(48 * self.hype.fever), 3))
        # timed effects (bottom left)
        x = LEFT + 3
        for k, letter in (("wide", "W"), ("slow", "S"), ("glue", "G"), ("fire", "F"), ("laser", "L")):
            v = self.timers[k]
            if v > 0 and (v > 2 or int(t * 8) % 2):
                c = {"wide": "sky", "slow": "mint", "glue": "yellow", "fire": "orange", "laser": "lavender"}[k]
                pygame.draw.rect(s, col(c), (x, 188, 9, 7), border_radius=2)
                s.blit(render_text(letter, "black"), (x + 2, 188))
                x += 12
        if self.net > 0 and self.st["kind"] != "bonus":
            draw_text(s, f"NET x{self.net}", RIGHT - 3, 188, "lime", align="right", shadow="ink")

    def draw_intro(self, s, t):
        st = self.st
        k = st["kind"]
        if k == "boss":
            if int(t * 4) % 2:
                for x in range(-20, W + 20, 20):
                    pygame.draw.polygon(s, col("red"), [(x, 108), (x + 10, 108), (x + 20, 116), (x + 10, 116)])
                    pygame.draw.polygon(s, col("red"), [(x, 150), (x + 10, 150), (x + 20, 158), (x + 10, 158)])
            panel(s, (40, 118, 240, 30), fill="black", border="red")
            draw_text(s, "WARNING!!", W // 2, 122, "red" if int(t * 6) % 2 else "yellow", 2, align="center",
                      outline="ink")
            draw_text(s, f"{st['name']} APPROACHES", W // 2, 138, "white", align="center", shadow=None)
            return
        h = 62 if st["new"] else 50
        panel(s, (30, 96, 260, h), fill="ink", border="yellow" if k == "bonus" else "peach")
        if k == "bonus":
            title = "BONUS STAGE"
            for i, ch in enumerate(title):
                draw_text(s, ch, W // 2 - text_width(title, 2) // 2 + i * 12, 102 + int(math.sin(t * 8 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            sub = "BREAK ALL THE COINS!" if st["bonus"] == "coins" else "CATCH THE SWEETS!"
            draw_text(s, st["name"], W // 2, 122, "yellow", align="center")
            draw_text(s, sub, W // 2, 134, "white", align="center")
            return
        draw_text(s, f"STAGE {self.n}", W // 2, 102, "yellow", 2, align="center", outline="ink", shadow=None)
        draw_text(s, self.theme[0], W // 2, 121, "lavender", align="center")
        draw_text(s, st["name"], W // 2, 132, "white", align="center")
        if st["new"]:
            draw_text(s, st["new"], W // 2, 145, "mint" if int(t * 4) % 2 else "lime", align="center")

    def draw_tally(self, s, t):
        rows = self.tally
        h = 34 + len(rows) * 11
        y0 = 90
        panel(s, (64, y0, 192, h), fill="ink", border="mint")
        head = {"boss": "BOSS CLEAR!", "bonus": "BONUS OVER!"}.get(self.st["kind"], f"STAGE {self.n} CLEAR!")
        draw_text(s, head, W // 2, y0 + 6, "mint", align="center")
        for i, (label, v, shown) in enumerate(rows):
            if i > self.tally_i:
                break
            y = y0 + 20 + i * 11
            draw_text(s, label, 72, y, "white" if v else "gray", shadow=None)
            draw_text(s, f"{int(shown)}", 248, y, "yellow" if v else "darkgray", align="right", shadow=None)
        if self.tally_i >= len(rows) and int(t * 3) % 2:
            draw_text(s, "PRESS Z", W // 2, y0 + h - 11, "lavender", align="center", shadow=None)



def draw_brick(s, br, t):
    r = br.rect() if br.kind != "bumper" else pygame.Rect(int(br.x), int(br.y), BRW, BRH)
    k = br.kind
    if not br.alive:       # jelly seed, growing back
        g = int((6.0 - br.regrow) / 6.0 * 4) + 1
        pygame.draw.circle(s, col("teal"), r.center, g)
        return
    if br.flash > 0 and k not in PORTALS:
        pygame.draw.rect(s, col("white"), r, border_radius=2)
        return
    if k in ("cookie", "candy", "mint", "lemon", "berry", "choco", "tin"):
        cute.brick(s, r, k, br.hp, t)
    elif k == "fudge":
        pygame.draw.rect(s, col("black"), r, border_radius=2)
        pygame.draw.rect(s, col("choco"), r.inflate(-2, -2), border_radius=2)
        for i in range(2, r.w - 2, 2):      # a white icing zigzag on top
            s.fill(col("white" if br.hp >= 3 else "pink"), (r.x + i, r.y + 2 + (i // 2) % 2, 1, 1))
        s.fill(col("black"), (r.x + 5, r.y + 4, 1, r.h - 5))
        s.fill(col("black"), (r.x + 10, r.y + 4, 1, r.h - 5))
        if br.hp < 3:
            pygame.draw.line(s, col("peach"), (r.x + 2, r.y + 4), (r.x + 4, r.bottom - 2))
        if br.hp < 2:
            pygame.draw.line(s, col("peach"), (r.right - 3, r.y + 4), (r.right - 5, r.bottom - 2))
    elif k == "gold":
        pygame.draw.rect(s, col("orange"), r, border_radius=2)
        pygame.draw.rect(s, col("yellow"), r.inflate(-2, -2), border_radius=2)
        sx = r.x + int(t * 24 + br.c * 5) % 28 - 6
        for i in range(3):
            if r.x + 1 <= sx + i < r.right - 1:
                s.fill(col("white"), (sx + i, r.y + 1, 1, r.h - 2))
        draw_text(s, "$", r.centerx - 2, r.y, "orange", shadow=None)
        if br.hp < 3:
            s.fill(col("orange"), (r.x + 3, r.y + 5, 3, 1))
    elif k == "bomb":
        pygame.draw.rect(s, col("red"), r.inflate(-2, 0), border_radius=3)
        pygame.draw.rect(s, col("hotpink"), r.inflate(-4, -2), border_radius=3)
        for dx, dy in ((4, 3), (9, 2), (11, 5), (6, 5)):
            s.fill(col("white"), (r.x + dx, r.y + dy, 1, 1))
        s.fill(col("yellow" if int(t * 8 + br.c) % 2 else "orange"), (r.centerx, r.y - 1, 1, 2))
    elif k == "gift":
        pygame.draw.rect(s, col("purple"), r, border_radius=1)
        s.fill(col("lavender"), r.inflate(-2, -2))
        s.fill(col("yellow"), (r.centerx - 1, r.y, 2, r.h))
        s.fill(col("yellow"), (r.x, r.centery - 1, r.w, 1))
        s.fill(col("orange"), (r.centerx - 3, r.y, 2, 1))
        s.fill(col("orange"), (r.centerx + 1, r.y, 2, 1))
    elif k == "jelly":
        wob = int(math.sin(t * 6 + br.c) * 1)
        pygame.draw.rect(s, col("teal"), (r.x, r.y + max(0, wob), r.w, r.h - max(0, wob)), border_radius=3)
        pygame.draw.rect(s, col("mint"), (r.x + 1, r.y + 1 + max(0, wob), r.w - 2, r.h - 3 - max(0, wob)), border_radius=2)
        s.fill(col("white"), (r.x + 3, r.y + 2 + max(0, wob), 2, 1))
        s.fill(col("black"), (r.centerx - 2, r.centery, 1, 1))
        s.fill(col("black"), (r.centerx + 2, r.centery, 1, 1))
    elif k == "key":
        pygame.draw.rect(s, col("orange"), r, border_radius=2)
        pygame.draw.rect(s, col("yellow"), r.inflate(-2, -2), border_radius=2)
        pygame.draw.circle(s, col("brown"), (r.x + 5, r.centery), 2, 1)
        s.fill(col("brown"), (r.x + 7, r.centery, 6, 1))
        s.fill(col("brown"), (r.x + 11, r.centery, 1, 2))
    elif k == "lock":
        if br.locked:
            pygame.draw.rect(s, col("black"), r, border_radius=2)
            pygame.draw.rect(s, col("darkgray"), r.inflate(-2, -2), border_radius=2)
            s.fill(col("gray"), (r.x + 2, r.y + 1, r.w - 4, 1))
            s.fill(col("yellow"), (r.centerx - 1, r.y + 2, 2, 2))
            s.fill(col("yellow"), (r.centerx, r.y + 4, 1, 2))
        else:
            pygame.draw.rect(s, col("hotpink"), r, border_radius=2)
            pygame.draw.rect(s, col("pink"), r.inflate(-2, -2), border_radius=2)
            s.fill(col("white"), (r.x + 2, r.y + 2, 3, 1))
            pygame.draw.rect(s, col("yellow"), (r.centerx - 2, r.y + 2, 4, 4), 1)
    elif k == "bumper":
        rad = 4 + (1 if br.bump > 0 else 0)
        pygame.draw.circle(s, col("black"), r.center, rad + 1)
        pygame.draw.circle(s, col("white" if br.bump > 0 else "hotpink"), r.center, rad)
        pygame.draw.circle(s, col("yellow"), r.center, 2)
    elif k in PORTALS:
        c1, c2 = ("lavender", "purple") if k == "portal" else ("orange", "yellow")
        pygame.draw.ellipse(s, col(c2), r.inflate(-2, 0))
        pygame.draw.ellipse(s, col("night"), r.inflate(-5, -3))
        a = t * 6
        for i in range(3):
            s.fill(col(c1), (r.centerx + int(math.cos(a + i * 2.1) * 4), r.centery + int(math.sin(a + i * 2.1) * 2), 1, 1))
    elif k == "coin":
        w = max(1, int(abs(math.cos(t * 4 + br.c * 0.5)) * 4))
        pygame.draw.ellipse(s, col("orange"), (r.centerx - w, r.y, w * 2 + 1, 8))
        pygame.draw.ellipse(s, col("yellow"), (r.centerx - w + 1, r.y + 1, max(1, w * 2 - 1), 6))


def draw_cap(s, x, y, k, t):
    x, y = int(x), int(y)
    c = CAPS[k][0]
    if k == "$":
        c = "yellow" if int(t * 10) % 2 else "orange"
    pygame.draw.rect(s, col("black"), (x - 7, y - 4, 14, 8), border_radius=3)
    pygame.draw.rect(s, col(c), (x - 6, y - 3, 12, 6), border_radius=3)
    s.fill(col("white"), (x - 4, y - 2, 2, 1))
    s.blit(render_text(k, "black"), (x - 2, y - 3))


def draw_sweet(s, sw, t):
    x, y = int(sw.x), int(sw.y)
    if sw.kind == 8:
        sp = sprite("star")
        s.blit(sp, (x - sp.get_width() // 2, y - sp.get_height() // 2))
        if int(t * 10) % 2:
            s.fill(col("white"), (x + 4, y - 4, 1, 1))
    elif sw.kind == 9:
        pygame.draw.circle(s, col("black"), (x, y), 5)
        pygame.draw.circle(s, col("lime"), (x, y), 4)
        for a in range(0, 360, 60):
            r = math.radians(a + t * 90)
            s.fill(col("black"), (x + int(math.cos(r) * 5), y + int(math.sin(r) * 5), 1, 1))
        cute.eyes(s, x, y - 1, 2, 0, "angry")
    else:
        cute.fruit(s, sw.kind, x - 4, y - 4)


def preview(s, t):
    s.fill(col("choco"))
    w, h = s.get_size()
    kinds = ["cookie", "candy", "mint", "lemon", "berry"]
    for r in range(4):
        for c in range(w // 16):
            if (r + c + int(t)) % 7:
                cute.brick(s, (c * 16, 4 + r * 8, 16, 8), kinds[(r + c) % 5])
    bx = w / 2 + math.sin(t * 2) * 30
    by = h - 20 - abs(math.sin(t * 3)) * 26
    pygame.draw.circle(s, col("hotpink"), (int(bx), int(by)), 2)
    pygame.draw.rect(s, col("peach"), (int(w / 2 + math.sin(t * 2) * 25) - 14, h - 10, 28, 5), border_radius=3)
