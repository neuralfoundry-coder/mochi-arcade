"""ROOFTOP RUN - chase GULLY the fish thief across 200 stages of night-time rooftops (original game).

TORA, a tiger-striped street cat, auto-runs from roof to roof: jump (hold for higher), slide under billboards,
pounce on pigeons, wall-kick up chimneys, bounce on laundry lines and ride the tram wires. Fish fill the CHASE
meter - the closer she gets, the lower GULLY hovers at the finish line, where one good jump plucks his tail
feather. 20 districts (rooftop_run_course.py), a boss on every 10th stage (rooftop_run_boss.py), a bonus run on
every x5 and upgrade cards that last for the whole run.
The iOS port (ios/MochiArcade/Games/RooftopRun*.swift) mirrors these files and reads the courses from EXPORT.
"""
import bisect
import math
import random

import pygame

from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow
from mochi_arcade.games import DIFF
from mochi_arcade.games import rooftop_run_art  # noqa: F401  (registers the sprites and songs)
from mochi_arcade.games import rooftop_run_world as RW
from mochi_arcade.games.base import GameScene
from mochi_arcade.games.rooftop_run_boss import Boss, overlap
from mochi_arcade.games.rooftop_run_course import CAMPAIGN, CAP_NAMES, STAND_H, THEMES
from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

HOWTO = ["Z / SPACE   JUMP (HOLD = HIGHER)",
         "DOWN / X    SLIDE - IN THE AIR: POUNCE",
         "LEFT/RIGHT  EASE OFF / SPRINT (OPTIONAL)",
         "",
         "TORA CHASES GULLY THE FISH THIEF! JUMP ON",
         "A WALL TO KICK OFF IT, BOUNCE ON LAUNDRY,",
         "GRAB TRAM WIRES, STOMP PIGEONS. FISH FILL",
         "THE CHASE METER: GRAB GULLY'S FEATHER AT",
         "THE FINISH. BOSS EVERY 10TH, BONUS ON X5.",
         "ENTER / ESC  PAUSE"]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["a", "a", "down", "right"]
LIVES_RR = {"easy": 9, "normal": 7, "hard": 5}
SPEED_RR = {"easy": 0.9, "normal": 1.0, "hard": 1.1}
MAX_LIVES = 9
TORA_X = 80                    # Tora's spot on screen
LIFE_AT = [30000, 80000, 150000, 250000]      # then every 150000

EXPORT = {"stages": CAMPAIGN, "themes": [list(t) for t in THEMES]}


# ----------------------------------------------------------------------------- upgrade cards
def _icon_jump2(s, cx, cy, t):
    for i in range(2):
        y = cy + 3 - i * 6 - int(abs(math.sin(t * 4 + i)) * 2)
        pygame.draw.polygon(s, col("sky"), [(cx - 4, y + 2), (cx, y - 2), (cx + 4, y + 2)])


def _icon_spring(s, cx, cy, t):
    h = 3 + int(abs(math.sin(t * 5)) * 3)
    for i in range(4):
        s.fill(col("lime"), (cx - 4, cy + 4 - i * h // 2, 9, 1))
    s.fill(col("orange"), (cx - 3, cy - 4 - h, 7, 3))


def _icon_bell(s, cx, cy, t):
    RW.draw_cap_icon(s, 0, cx, cy, t)


def _icon_fur(s, cx, cy, t):
    pygame.draw.circle(s, col("peach"), (cx, cy), 6, 2)
    pygame.draw.circle(s, col("orange"), (cx, cy), 3)


def _icon_save(s, cx, cy, t):
    for i in range(-6, 7, 3):
        s.fill(col("lime"), (cx + i, cy + 4, 2, 1))
    s.blit(sprite("rr_head"), (cx - 4, cy - 6 - int(abs(math.sin(t * 5)) * 3)))


def _icon_glide(s, cx, cy, t):
    pygame.draw.polygon(s, col("lavender"), [(cx - 7, cy), (cx, cy - 5), (cx + 7, cy)])
    s.fill(col("white"), (cx, cy, 1, 5))


def _icon_pounce(s, cx, cy, t):
    s.fill(col("orange"), (cx - 1, cy - 6, 3, 7))
    pygame.draw.polygon(s, col("orange"), [(cx - 4, cy), (cx + 4, cy), (cx, cy + 4)])
    for dx in (-6, 6):
        s.fill(col("yellow"), (cx + dx, cy + 4 - int(t * 10) % 3, 1, 2))


def _icon_luck(s, cx, cy, t):
    RW.draw_cap_icon(s, 5, cx, cy, t)


def _icon_fever(s, cx, cy, t):
    for i in range(3):
        pygame.draw.circle(s, col(rainbow(i, t)), (cx - 4 + i * 4, cy + 1 - (i % 2) * 3), 2)


def _icon_chase(s, cx, cy, t):
    s.blit(sprite("rr_feather"), (cx - 4, cy - 4))


UPGRADES = [
    Upgrade("jump2", "TWIN LEAP", "JUMP AGAIN|IN MID-AIR", "sky", _icon_jump2, 2),
    Upgrade("spring", "SPRING PAWS", "JUMP|HIGHER", "lime", _icon_spring, 3),
    Upgrade("magnet", "FISH BELL", "PULLS FISH|TO YOU", "yellow", _icon_bell, 3),
    Upgrade("fur", "THICK FUR", "SHRUGS OFF|ONE HIT|EACH STAGE", "peach", _icon_fur, 2),
    Upgrade("save", "SAFETY TAIL", "BOUNCES YOU|OUT OF ONE|FALL A STAGE", "mint", _icon_save, 2),
    Upgrade("glide", "TAIL GLIDE", "HOLD JUMP|TO FLOAT|DOWN SLOWLY", "lavender", _icon_glide, 2),
    Upgrade("pounce", "POWER POUNCE", "POUNCES|SHAKE THE ROOF|+ BOSS DAMAGE", "orange", _icon_pounce, 2),
    Upgrade("life", "NINE LIVES", "+1 LIFE|RIGHT NOW", "hotpink", "heart", 5),
    Upgrade("luck", "LUCKY CHARM", "MORE|CAPSULES AND|JACKPOTS", "orange", _icon_luck, 3),
    Upgrade("fever", "PURR FEVER", "FEVER FILLS|FASTER AND|LASTS LONGER", "yellow", _icon_fever, 3),
    Upgrade("chase", "HOT PURSUIT", "START EVERY|STAGE CLOSER|TO GULLY", "pink", _icon_chase, 3),
]


# ----------------------------------------------------------------------------- the game
class RooftopRun(GameScene):
    @property
    def music(self):
        return self.song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES_RR.get(d, 7)
        self.speed_mul = SPEED_RR.get(d, 1.0)
        self.levels = {}
        self.life_i = 0
        self.fish_total = 0         # whole run: every 100 fish = +1 life
        self.feathers = 0
        self.picks_left = 0
        self.pick_title = "POWER UP!"
        self.next_n = None
        self.was_fever = False
        self.hype.combo_y = 26
        self.sky_cache = {}
        start = max(1, min(STAGES, int(opt.get("level", opt.get("start", 1)))))
        self.start_stage(start)
        if start > 10:          # starting from a checkpoint: catch up on some upgrades first
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

    def sfx(self, name):
        self.app.audio.play(name)

    def song(self):
        k = self.st["kind"]
        if k == "boss":
            return "boss"
        if k == "bonus":
            return "bonus"
        return "rr_run" if self.tier < 10 else "rr_chase"

    def fever_gain(self):
        return 0.022 * (1 + 0.35 * self.lv("fever"))

    def roof_y_at(self, x):
        """Top of the (intact) roof under world x, or None over a gap."""
        i = bisect.bisect_right(self.roof_x, x) - 1
        if i >= 0:
            r = self.course.roofs[i]
            if r.x <= x < r.x + r.w and not r.broken:
                return r.y
        return None

    def next_roof(self, x):
        i = bisect.bisect_right(self.roof_x, x)
        return self.course.roofs[i] if i < len(self.course.roofs) else None

    # ---------------------------------------------------------------- stages
    def start_stage(self, n):
        self.n = n
        st = self.st = CAMPAIGN[n - 1]
        self.tier = st["tier"]
        self.theme = THEMES[self.tier]
        self.reached(n)
        self.course = RW.Course(st)
        self.roof_x = [r.x for r in self.course.roofs]
        self.speed_base = st["speed"] * self.speed_mul
        self.speed = self.speed_base
        b = self.body = RW.Body(60, self.roof_y_at(60) or 150)
        b.ground = self.course.roofs[bisect.bisect_right(self.roof_x, 60) - 1]
        self.apply_upgrades()
        self.cam = b.x - TORA_X
        self.safe = (60.0, b.ground)
        self.stime = 0.0
        self.chase = min(100.0, 35.0 + 15 * self.lv("chase"))
        self.fish_got = self.gold_got = 0
        self.fish_n = len(self.course.fish)
        self.hits = 0
        self.falls = 0
        self.stage_combo = 0
        self.invuln = 0.0
        self.hurt_t = 0.0
        self.shield = self.lv("fur")
        self.saves = self.lv("save")
        self.timers = {"magnet": 0.0, "umbrella": 0.0, "catnip": 0.0}
        self.blocked_t = 0.0
        self.gully = {"state": "chase", "x": 0.0, "y": 0.0, "t": 0.0}
        self.feather = False
        self.flash_feather = None
        self.trail = []
        self.boss = Boss(self, st["boss"]) if st["kind"] == "boss" else None
        for hz in self.course.haz:          # flying pigeons well above the roof bob up and down
            if hz.k == "q":
                g = self.roof_y_at(hz.x)
                hz.b = 1 if g is None or g - hz.y > 20 else 0
        self.lucky = st["kind"] == "normal" and self.hype.lucky(0.03 + 0.01 * self.lv("luck"))
        if self.lucky and self.course.gold:        # one golden fish is a RAINBOW FISH today
            random.choice(self.course.gold)[3] = True
        for c in self.course.caps:                 # rare capsules: milk (+1 life) and the gold bell
            roll = random.random()
            if roll < 0.02 + 0.01 * self.lv("luck"):
                c[2] = 5
            elif roll < 0.07:
                c[2] = 4
        self.state = "intro"
        self.state_t = 0.0
        self.intro_len = 3.0 if self.boss else 2.4
        self.tally = []
        self.ctrl_prev = (False, False)
        self.sky = self.sky_cache.get(self.tier)
        if self.sky is None:
            self.sky = self.sky_cache[self.tier] = (RW.make_sky(self.tier), RW.make_skyline(self.tier, True),
                                                    RW.make_skyline(self.tier, False))
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.was_fever = False
        self.app.audio.music(self.song())
        self.sfx("warning" if self.boss else "stage")
        if self.boss:
            self.hype.flash("red", 0.3)

    def apply_upgrades(self):
        b = self.body
        b.air_max = self.lv("jump2")
        b.jv = 1 + 0.07 * self.lv("spring")
        b.glide = self.lv("glide")

    def on_pick(self, uid):
        if uid:
            self.levels[uid] = self.lv(uid) + 1
            u = next(x for x in UPGRADES if x.id == uid)
            self.hype.banner(u.name, f"LEVEL {self.levels[uid]}", color=u.color, dur=1.2, scale=1)
            if uid == "life":
                self.lives = min(MAX_LIVES, self.lives + 1)
                self.sfx("extra")
            elif uid == "fur":
                self.shield += 1
            elif uid == "save":
                self.saves += 1
            elif uid == "chase":
                self.chase = min(100.0, self.chase + 15)
            self.apply_upgrades()

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        s = self.state
        if s == "intro":
            if self.boss:
                self.boss.update(dt)
            if self.state_t > self.intro_len or (self.state_t > 0.5 and self.app.input.hit("a")):
                self.state = "play"
                self.state_t = 0.0
                inp = self.app.input
                self.ctrl_prev = (inp.down("a", "up"), inp.down("down", "b"))
                self.hype.banner("GO!", color="lime", dur=0.7, scale=2)
        elif s == "play":
            self.play(dt)
        elif s == "fall":
            self.body.vy += 900 * dt
            self.body.y += self.body.vy * dt
            if self.state_t > 1.0:
                self.after_fall()
        elif s == "finish":
            self.finish_run(dt)
        elif s == "clear":
            self.finish_run(dt)
            if self.state_t > 2.2:
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
        self.update_world(dt)

    def read_ctrl(self):
        inp = self.app.input
        jump = inp.down("a", "up")
        down = inp.down("down", "b")
        pj, pd = self.ctrl_prev
        self.ctrl_prev = (jump, down)
        lr = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        return RW.Ctrl(jump and not pj, jump, down and not pd, down, lr)

    def view(self, x0=None, x1=None):
        b = self.body
        return RW.View(self.course, b.x - 60 if x0 is None else x0, b.x + 280 if x1 is None else x1,
                       self.speed, self.stime)

    def play(self, dt):
        b = self.body
        st = self.st
        self.stime += dt
        for k in self.timers:
            self.timers[k] = max(0.0, self.timers[k] - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.hurt_t = max(0.0, self.hurt_t - dt)
        for m in self.course.lifts:
            m.y = m.at(self.stime)
        for ln in self.course.lines:
            ln.y = ln.at(self.stime)
        self.speed = self.speed_base * (self.boss.slow() if self.boss else 1.0)
        b.boost = 1.25 if self.timers["catnip"] > 0 else 1.0
        b.glide = max(self.lv("glide"), 1 if self.timers["umbrella"] > 0 else 0)
        c = self.read_ctrl()
        prev_y = b.y
        events = RW.step(b, c, dt, self.view())
        for ev, obj in events:
            self.on_event(ev, obj, c)
        self.cam = b.x - TORA_X
        if st["loop"] and b.x > st["loop"] + 120:
            self.wrap(st["loop"])
        # skylights crack under paws
        if b.ground is not None and getattr(b.ground, "glass", 0):
            g = b.ground
            if g.crack < 0:
                g.crack = 0.7
                self.sfx("tin")
        for r in self.course.roofs:
            if r.glass and r.crack >= 0 and not r.broken:
                r.crack -= dt
                if r.crack <= 0:
                    self.shatter(r)
        # blocked by a wall: Gully gets away a little
        if b.blocked is not None and b.ground is not None:
            self.blocked_t += dt
            self.chase_add(-6 * dt)
        else:
            self.blocked_t = 0.0
        self.collect(b)
        self.hazards(dt, b, prev_y)
        if self.boss:
            self.boss.update(dt)
            self.boss_contact(b)
        if self.state != "play":
            return
        # off the bottom of the screen
        if b.y > H + 10 and b.wire is None:
            if self.saves > 0 and st["kind"] != "bonus":
                self.saves -= 1
                b.y = H + 4
                b.vy = -470.0
                b.hold = False
                b.pounce = False
                self.floats.add(b.x, H - 30, "SAVED!", "lime")
                self.sfx("bubble")
                self.parts.burst(b.x, H - 4, 12, ("lime", "white"), 60, 0.5)
            else:
                self.fell()
                return
        if st["kind"] != "boss" and b.x >= self.course.finish:
            self.cross_finish()
        self.update_gully(dt)
        self.stage_combo = max(self.stage_combo, self.hype.combo)
        if self.hype.fever_on and not self.was_fever:
            self.hype.fever_t += 2 * self.lv("fever")
            self.app.audio.music("fever")
        elif self.was_fever and not self.hype.fever_on:
            self.app.audio.music(self.song())
        self.was_fever = self.hype.fever_on
        self.check_life()
        if self.timers["catnip"] > 0 or self.hype.fever_on:
            self.trail.append([b.x, b.y, 0.3])

    def update_world(self, dt):
        for tr in self.trail:
            tr[2] -= dt
        self.trail = [tr for tr in self.trail if tr[2] > 0]
        for p in self.course.pads:
            p[2] = max(0.0, p[2] - dt)
        for bx in self.course.boxes:
            bx.flash = max(0.0, bx.flash - dt)

    def wrap(self, L):
        """Boss arenas repeat: jump Tora (and everything that follows her) back one block."""
        b = self.body
        b.x -= L
        self.cam -= L
        self.safe = (self.safe[0] - L, None)
        if self.boss:
            self.boss.wx -= L
            for s in self.boss.shots:
                s.x -= L
        for p in self.parts.p:
            p[0] -= L
        for f in self.floats.items:
            f[0] -= L
        self.trail = []
        self.course.reset_consumables(self.cam - 20, self.cam + W + 20)
        if b.ground is not None and b.ground.solid == "R":
            b.ground = self.course.roofs[max(0, bisect.bisect_right(self.roof_x, b.x) - 1)]

    def chase_add(self, v):
        self.chase = max(0.0, min(100.0, self.chase + v))

    def on_event(self, ev, obj, c):
        b = self.body
        if ev == "jump":
            self.sfx("jump")
        elif ev == "airjump":
            self.sfx("jump")
            self.parts.burst(b.x, b.y, 6, ("white", "sky"), 40, 0.3)
        elif ev == "kick":
            self.sfx("tin")
            self.hype.hit(1, fever=self.fever_gain())
            self.chase_add(2)
            self.score_at(50)
            self.parts.burst(b.x + 5, b.y - 6, 6, ("white", "gray"), 40, 0.3)
            self.floats.add(b.x, b.y - 24, "KICK!", "mint")
        elif ev == "bounce":
            self.sfx("bubble")
            self.hype.hit(1, fever=self.fever_gain())
            self.chase_add(1)
            self.score_at(30)
            self.parts.burst(b.x, b.y, 5, ("cream", "white"), 30, 0.3)
        elif ev == "grab":
            self.sfx("hold")
            self.score_at(50)
            self.parts.burst(b.x, obj.y, 8, ("yellow", "white"), 40, 0.3)
        elif ev == "pad":
            obj[2] = 1.0
            self.sfx("powerup")
            self.hype.hit(1, fever=self.fever_gain())
            self.parts.burst(obj[0], obj[1] - 4, 20, ("red", "yellow", "white", "hotpink"), 90, 0.6)
            self.score_at(100)
        elif ev == "pounce":
            self.sfx("rotate")
        elif ev == "updraft":
            self.sfx("bubble")
        elif ev == "bonk":
            self.sfx("tin")
        elif ev == "land":
            solid, impact, pounced = obj
            if solid.solid == "R" and not solid.glass:
                self.safe = (max(solid.x + 16, min(b.x, solid.x + solid.w - 40)), solid)
            if pounced:
                self.sfx("lock")
                self.app.shake(2, 0.12)
                self.parts.burst(b.x, b.y, 10, ("white", "gray", "cream"), 60, 0.35)
                if self.lv("pounce"):
                    self.shockwave(b.x, b.y)
            elif impact > 260:
                self.parts.burst(b.x, b.y, 4, ("gray", "white"), 25, 0.25)
            if solid.solid == "S" and pounced and solid.k in ("X", "C"):
                self.smash(solid)
            elif getattr(solid, "glass", 0):
                if pounced:
                    self.shatter(solid)
                elif solid.crack < 0 or solid.crack > 0.2:
                    solid.crack = 0.2
                    self.sfx("tin")

    def smash(self, box):
        b = self.body
        box.alive = False
        self.sfx("brick")
        self.hype.hit(1, fever=self.fever_gain())
        self.score_at(100, box.x + box.w / 2, box.y - 6)
        self.parts.burst(box.x + box.w / 2, box.y + box.h / 2, 14, ("brown", "peach", "choco"), 70, 0.5)
        b.vy = -220.0
        b.ground = None
        if box.k == "C":
            n = 5
            self.fish_n += n
            for i in range(n):
                self.course.fish.append([box.x + box.w / 2 + (i - 2) * 9, box.y - 18 - (i % 2) * 8, False])
            self.course.fish.sort(key=lambda f: f[0])
            self.floats.add(box.x + box.w / 2, box.y - 30, "FISH CRATE!", "sky")

    def shatter(self, r):
        r.broken = True
        r.crack = -1.0
        self.sfx("brick")
        self.parts.burst(r.x + r.w / 2, r.y + 2, 16, ("sky", "white", "teal"), 70, 0.6)
        b = self.body
        if b.ground is r:
            b.ground = None
            b.vy = 0.0

    def shockwave(self, x, y):
        self.parts.burst(x, y - 2, 16, ("yellow", "orange", "white"), 90, 0.4)
        for hz in self.course.haz:
            if hz.alive and hz.k in ("p", "q") and abs(hz.x - x) < 34 + 10 * self.lv("pounce") and abs(hz.y - y) < 40:
                self.defeat(hz, pounce=True)
        for bx in self.course.boxes:
            if bx.alive and bx.k in ("X", "C") and abs(bx.x + bx.w / 2 - x) < 30 and abs(bx.y + bx.h - y) < 4:
                self.smash(bx)

    # ---------------------------------------------------------------- pickups
    def collect(self, b):
        bx, by, bw, bh = b.box()
        cx, cy = b.x, b.y - bh / 2
        mag = 22 * self.lv("magnet") + (60 if self.timers["magnet"] > 0 else 0) + (20 if self.hype.fever_on else 0)
        fish = self.course.fish
        i0 = bisect.bisect_left(fish, [b.x - 80 - mag])
        got = 0
        for i in range(i0, len(fish)):
            f = fish[i]
            if f[0] > b.x + 60 + mag:
                break
            if f[2]:
                continue
            if mag and abs(f[0] - cx) < mag and abs(f[1] - cy) < mag:
                d = math.hypot(cx - f[0], cy - f[1]) or 1
                stepv = min(d, 300 / 60)
                f[0] += (cx - f[0]) / d * stepv
                f[1] += (cy - f[1]) / d * stepv
            if bx - 4 <= f[0] <= bx + bw + 4 and by - 4 <= f[1] <= by + bh + 4:
                f[2] = True
                got += 1
                self.fish_got += 1
                self.fish_total += 1
                self.hype.hit(1, fever=self.fever_gain())
                self.chase_add(1.2)
                self.add(self.factor_pts(20) + self.hype.combo_bonus(1))
                self.parts.sparkle(f[0], f[1], "sky")
                if self.fish_total % 100 == 0:
                    self.extra_life(f"{self.fish_total} FISH!")
        if got:
            self.sfx("eat")
        if mag:
            fish.sort(key=lambda f: f[0])
        for g in self.course.gold:
            if not g[2] and bx - 5 <= g[0] <= bx + bw + 5 and by - 5 <= g[1] <= by + bh + 5:
                g[2] = True
                self.gold_got += 1
                self.chase_add(8)
                self.hype.hit(3, fever=self.fever_gain() * 3)
                self.sfx("coin")
                self.parts.burst(g[0], g[1], 14, ("yellow", "orange", "white"), 60, 0.5)
                if g[3]:
                    self.hype.jackpot(self.factor_pts(8000), "RAINBOW FISH!")
                else:
                    self.score_at(500, g[0], g[1] - 8)
        for c in self.course.caps:
            if not c[3] and bx - 6 <= c[0] <= bx + bw + 6 and by - 8 <= c[1] <= by + bh + 8:
                c[3] = True
                self.power(c[2], c[0], c[1])

    def power(self, k, x, y):
        self.sfx("powerup")
        self.chase_add(3)
        self.floats.add(x, y - 10, CAP_NAMES[k], ("yellow", "sky", "lime", "peach", "white", "orange")[k])
        if k == 0:
            self.timers["magnet"] = 10.0
        elif k == 1:
            self.timers["umbrella"] = 10.0
        elif k == 2:
            self.timers["catnip"] = 6.0
            self.hype.banner("CATNIP RUSH!", color="lime", dur=1.0, scale=1)
        elif k == 3:
            self.shield += 1
        elif k == 4:
            self.extra_life("MILK!")
        elif k == 5:
            self.hype.jackpot(self.factor_pts(5000), None)
        self.score_at(100)

    def extra_life(self, why):
        if self.lives < MAX_LIVES:
            self.lives += 1
            self.hype.banner("+1 LIFE!", why, color="pink", dur=1.3, sound="extra")
            self.hype.shower(14, "hearts")
        else:
            self.score_at(2000)
            self.hype.banner("NINE LIVES!", "+2000", color="pink", dur=1.0, scale=1, sound="coin")

    def check_life(self):
        i = self.life_i
        target = LIFE_AT[i] if i < len(LIFE_AT) else LIFE_AT[-1] + 150000 * (i - len(LIFE_AT) + 1)
        if self.score >= target:
            self.life_i += 1
            self.extra_life(f"{target} POINTS")

    # ---------------------------------------------------------------- hazards
    def hazards(self, dt, b, prev_y):
        box = b.box()
        cam = self.cam
        catnip = self.timers["catnip"] > 0
        for hz in self.course.haz:
            k = hz.k
            if hz.x < cam - 80 or hz.x > cam + W + 300:
                if not (k == "q" and hz.state == 1):
                    continue
            hz.t += dt
            if not hz.alive:
                if k in ("p", "q"):
                    hz.x += 60 * dt
                    hz.y -= 80 * dt
                continue
            if k == "p":
                hz.x += hz.dir * 18 * dt
                if hz.x < hz.a:
                    hz.x, hz.dir = float(hz.a), 1
                elif hz.x > hz.b:
                    hz.x, hz.dir = float(hz.b), -1
            elif k == "q":
                if hz.state == 0 and hz.x < cam + W + 30:
                    hz.state = 1
                if hz.state == 1:
                    hz.x -= 46 * dt
                    if hz.b:            # high flyers bob, low ones skim the roof at a steady height
                        hz.y = hz.y0 + math.sin(hz.t * 4) * 3
            elif k == "i":
                if hz.state == 0 and b.x > hz.x - 92:
                    hz.state = 3
                    hz.t = 0.0
                elif hz.state == 3 and hz.t > 0.3:
                    hz.state = 1
                    hz.y = float(hz.a + 10)
                    hz.vy = 0.0
                elif hz.state == 1:
                    hz.vy += 900 * dt
                    hz.y += hz.vy * dt
                    if hz.y >= hz.y0:
                        hz.y = hz.y0
                        hz.state = 2
                        hz.t = 0.0
                        self.sfx("tin")
                        self.parts.burst(hz.x, hz.y - 2, 6, ("sky", "white"), 40, 0.3)
                elif hz.state == 2 and hz.t > 1.4:
                    hz.alive = False
            elif k == "d":
                if hz.state == 0 and b.x > hz.x - 260:
                    hz.state = 1
                    hz.t = 0.0
                    self.sfx("warning")
                elif hz.state == 1 and hz.t > 0.75:
                    hz.state = 2
                    hz.x = cam + W + 12
                elif hz.state == 2:
                    hz.x += (self.speed - 230) * dt
                    if hz.x < cam - 30:
                        hz.alive = False
            elif k == "z":
                if hz.state == 0 and b.x > hz.x - 120:
                    hz.state = 1
                    hz.t = 0.0
                elif hz.state == 1 and hz.t > 0.55:
                    hz.state = 2
                    hz.t = 0.0
                    self.sfx("boom")
                    self.hype.flash("white", 0.1)
                    self.app.shake(2, 0.15)
                elif hz.state == 2 and hz.t > 0.5:
                    hz.state = 3
                    hz.alive = False
            r = hz.rect(self.stime)
            if r is None or not overlap(box, r):
                continue
            if k in ("p", "q"):
                if catnip or (b.vy > 0 and prev_y <= r[1] + 4) or (k == "p" and b.slide):
                    self.defeat(hz, pounce=b.pounce)
                    if not catnip and not b.slide:
                        b.vy = -260.0 if not self.app.input.down("a", "up") else -320.0
                        b.hold = True
                        b.pounce = False
                        b.jumps = b.air_max
                    continue
            if k == "s" and self.timers["umbrella"] > 0:
                continue
            if catnip and k != "s":
                continue
            self.hurt("SPLASH!" if k == "s" else "OUCH!")

    def defeat(self, hz, pounce=False):
        hz.alive = False
        hz.t = 0.0
        self.sfx("pop")
        self.hype.hit(1, fever=self.fever_gain() * 2)
        self.chase_add(4)
        pts = 200 * (2 if pounce else 1)
        self.score_at(pts, hz.x, hz.y - 16, "orange" if pounce else "yellow")
        self.parts.burst(hz.x, hz.y - 4, 10, ("gray", "white", "lavender"), 60, 0.4)
        if pounce:
            self.floats.add(hz.x, hz.y - 26, "POUNCE!", "orange")

    def hurt(self, word="OUCH!"):
        if self.invuln > 0 or self.state != "play":
            return
        b = self.body
        if self.shield > 0:
            self.shield -= 1
            self.invuln = 1.0
            self.sfx("tin")
            self.floats.add(b.x, b.y - 24, "FUR SHIELD!", "peach")
            self.parts.burst(b.x, b.y - 7, 14, ("peach", "orange", "white"), 60, 0.4)
            return
        self.hits += 1
        self.lives -= 1
        self.invuln = 1.6
        self.hurt_t = 0.45
        self.chase_add(-15)
        self.hype.break_combo()
        self.sfx("hurt")
        self.app.shake(3, 0.3)
        self.hype.hitstop(0.08)
        self.floats.add(b.x, b.y - 24, word, "red")
        self.parts.burst(b.x, b.y - 7, 10, ("red", "white", "orange"), 60, 0.4)
        if self.lives <= 0:
            self.game_over()

    def fell(self):
        if self.st["kind"] == "bonus":
            self.floats.add(self.body.x, H - 40, "BOING! AGAIN!", "lime")
            self.respawn()
            return
        self.state = "fall"
        self.state_t = 0.0
        self.body.vy = -260.0
        self.sfx("die")
        self.hype.break_combo()

    def after_fall(self):
        self.falls += 1
        self.lives -= 1
        self.chase_add(-20)
        if self.lives <= 0:
            self.game_over()
            return
        self.respawn()
        self.state = "play"
        self.state_t = 0.0
        self.hype.banner("MEOW!", f"{self.lives} LIVES LEFT", color="pink", dur=1.0, scale=1)

    def respawn(self):
        b = self.body
        x, roof = self.safe
        if roof is None or roof.broken:
            roof = self.course.roofs[max(0, bisect.bisect_right(self.roof_x, x) - 1)]
            while roof.glass or roof.broken:
                i = self.course.roofs.index(roof)
                roof = self.course.roofs[max(0, i - 1)]
                if i == 0:
                    break
            x = roof.x + 16
        b.x, b.y, b.vy = float(x), float(roof.y), 0.0
        b.ground, b.wire = roof, None
        b.pounce = b.pad = b.slide = b.cling = False
        b.jumps = b.air_max
        self.cam = b.x - TORA_X
        self.invuln = 2.0

    def game_over(self):
        self.lives = 0
        self.state = "over"
        self.hype.banner("GAME OVER", f"STAGE {self.n}", color="red", dur=3.0)
        self.sfx("gameover")
        self.end_game(False, f"STAGE {self.n}", delay=2.6)

    # ---------------------------------------------------------------- Gully and the finish
    def gully_hover(self):
        return 26 + (100 - self.chase) * 0.75

    def update_gully(self, dt):
        g = self.gully
        g["t"] += dt
        if self.st["kind"] != "normal":
            return
        b = self.body
        fin = self.course.finish
        gy = self.roof_y_at(fin - 24) or 150
        if g["state"] == "chase":
            g["x"] = self.cam + 330 - self.chase * 1.1
            g["y"] = 34 + math.sin(g["t"] * 3) * 4
            if b.x > fin - 330:
                g["state"] = "perch"
                g["t"] = 0.0
        elif g["state"] == "perch":
            tx, ty = fin - 24, gy - self.gully_hover() + math.sin(g["t"] * 4) * 3
            k = min(1.0, dt * 4)
            g["x"] += (tx - g["x"]) * k
            g["y"] += (ty - g["y"]) * k
            if overlap(b.box(), (g["x"] - 8, g["y"] - 6, 16, 12)) and not self.feather:
                self.grab_feather()
        elif g["state"] in ("flee", "plucked"):
            g["x"] += (self.speed + 160) * dt
            g["y"] -= 70 * dt

    def grab_feather(self):
        g = self.gully
        self.feather = True
        self.feathers += 1
        g["state"] = "plucked"
        self.flash_feather = [g["x"], g["y"], 0.0]
        self.sfx("bonus")
        self.hype.hit(5, fever=0.2)
        self.hype.slowmo(0.35, 0.6)
        self.hype.flash("white", 0.15)
        self.app.shake(3, 0.25)
        if self.chase >= 99.5:
            self.hype.jackpot(self.factor_pts(6000), "PERFECT CHASE!")
        else:
            self.hype.banner("TAIL FEATHER!", "SQUAAAWK!", color="yellow", dur=1.5)
        self.hype.shower(24, "stars")
        self.parts.burst(g["x"], g["y"], 18, ("white", "gray", "yellow"), 80, 0.7)

    def cross_finish(self):
        self.state = "finish"
        self.state_t = 0.0
        if self.st["kind"] == "normal" and not self.feather:
            self.gully["state"] = "flee"
            self.floats.add(self.course.finish, (self.roof_y_at(self.course.finish) or 150) - 70, "SQUAWK HA HA!",
                            "white")
        self.sfx("win")
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.app.audio.music(None)
        self.was_fever = False
        self.hype.banner("FINISH!" if self.st["kind"] == "normal" else "TIME UP!", color="mint", dur=1.3)
        self.hype.shower(30, "confetti")

    def finish_run(self, dt):
        """After the line (or a beaten boss): Tora skids to a stop and celebrates."""
        b = self.body
        k = max(0.0, 1 - self.state_t / 0.9)
        if self.state == "clear":
            k = max(0.0, 1 - self.state_t / 1.6)
        self.speed = self.speed_base * k
        if self.boss:
            self.boss.update(dt)
        RW.step(b, RW.Ctrl(), dt, self.view())
        if b.y > H + 10:     # never fall after the line
            self.respawn()
        self.cam = b.x - TORA_X
        if self.st["loop"] and b.x > self.st["loop"] + 120:
            self.wrap(self.st["loop"])
        self.update_gully(dt)
        if self.flash_feather:
            self.flash_feather[2] += dt
        if self.state == "finish" and self.state_t > 1.7:
            self.begin_tally()

    # ---------------------------------------------------------------- bosses
    def boss_landed(self):
        self.sfx("bubble")

    def boss_contact(self, b):
        bo = self.boss
        box = b.box()
        if bo.state != "dead" and bo.hurts(box) and self.timers["catnip"] <= 0:
            self.hurt()
        res = bo.check(b, box)
        if res in ("stomp", "hit"):
            dmg = 1 + (1 if (b.pounce and self.lv("pounce")) else 0)
            b.vy = -330.0
            b.hold = True
            b.pounce = False
            b.ground = None
            b.jumps = b.air_max
            self.sfx("boom")
            self.hype.hitstop(0.1)
            self.hype.flash("white", 0.12)
            self.app.shake(4, 0.25)
            self.hype.hit(2, fever=self.fever_gain() * 3)
            self.score_at(1000, bo.wx, bo.wy - 30, "orange")
            self.parts.burst(bo.wx, bo.wy - 10, 20, ("white", "yellow", "orange"), 90, 0.5)
            self.floats.add(bo.wx, bo.wy - 44, "STOMP!" if res == "stomp" else "BONK!", "yellow")
            if bo.take_hit(dmg):
                self.boss_defeated()
        elif res == "bump":
            b.vy = -180.0
            b.ground = None
            b.x -= 6
            self.sfx("tin")
            self.floats.add(b.x, b.y - 24, "FROM ABOVE!", "yellow")
        elif res == "hurt":
            self.hurt()

    def boss_defeated(self):
        g = self.hype
        self.sfx("bossdown")
        g.banner("BOSS DOWN!", self.boss.name, rainbow=True, dur=2.2, scale=2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(40, "coins")
        self.app.shake(6, 0.6)
        self.score_at(15000, self.body.x + 40, 80)
        self.state = "clear"
        self.state_t = 0.0
        self.hype.slowmo(0.3, 1.2)
        self.app.audio.music(None)
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.was_fever = False

    # ---------------------------------------------------------------- tally
    def begin_tally(self):
        st = self.st
        f = self.factor_pts
        rows = []
        if st["kind"] == "normal":
            rows.append(("COURSE CLEAR", f(1000)))
            rows.append((f"FISH {self.fish_got}/{self.fish_n}", f(self.fish_got * 20)))
            if self.fish_got >= self.fish_n:
                rows.append(("ALL FISH!", f(5000)))
            rows.append(("TAIL FEATHER", f(5000) if self.feather else 0))
            par = st["len"] / max(1.0, self.speed_base) * 1.15 + 3
            rows.append(("TIME BONUS", f(max(0, int(par - self.stime)) * 100)))
            rows.append(("NO HIT", f(3000) if self.hits + self.falls == 0 else 0))
        elif st["kind"] == "boss":
            rows.append(("BOSS BONUS", f(10000 + 2000 * self.tier)))
            rows.append(("NO HIT", f(8000) if self.hits + self.falls == 0 else 0))
        else:
            rows.append((f"FISH {self.fish_got}/{self.fish_n}", f(self.fish_got * 50)))
            rows.append((f"GOLDEN x{self.gold_got}", f(self.gold_got * 500)))
            rows.append(("ALL FISH!", f(10000) if self.fish_got >= self.fish_n else 0))
        rows.append((f"BEST COMBO {self.stage_combo}", f(self.stage_combo * 30)))
        self.tally = [[label, v, 0.0] for label, v in rows]
        self.tally_i = 0
        self.tally_wait = 0.0
        self.state = "tally"
        self.state_t = 0.0
        if st["kind"] == "normal" and self.feather and self.hits + self.falls == 0:
            self.hype.banner("PURRFECT!", "NO HITS + THE FEATHER", rainbow=True, dur=1.8, sound="fever")
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
                self.sfx("coin")
                return
            row = self.tally[self.tally_i]
            row[2] = min(row[1], row[2] + max(1.0, row[1] * dt / 0.4))
            if row[2] >= row[1]:
                if row[1] > 0:
                    self.add(row[1])
                    self.sfx("coin")
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
            self.hype.banner("ALL CLEAR!!", "TORA GOT HER FISH BACK!", rainbow=True, dur=5.0, sound="jackpot")
            self.hype.shower(120, "confetti")
            self.end_game(True, "ALL 200 STAGES!", delay=4.5)
            return
        self.next_n = self.n + 1
        if st["kind"] in ("boss", "bonus"):
            self.picks_left = 1
            self.pick_title = "BOSS BONUS!" if st["kind"] == "boss" else "FISHY TREAT!"
            self.state = "pick"
        else:
            self.start_stage(self.next_n)

    # ---------------------------------------------------------------- drawing
    def render(self, s):
        t = self.t
        th = self.theme
        cam = int(self.cam)
        sky, far, mid = self.sky
        s.blit(sky, (0, 0))
        self.draw_sky_fx(s, t)
        for layer, k in ((far, 0.12), (mid, 0.3)):
            off = int(self.cam * k) % W
            s.blit(layer, (-off, 0))
            s.blit(layer, (W - off, 0))
        c = self.course
        x0, x1 = self.cam - 40, self.cam + W + 40
        for z in c.winds:
            RW.draw_wind(s, z, self.cam, t)
        for wr in c.wires:
            if wr.x1 > x0 and wr.x0 < x1:
                RW.draw_wire(s, wr, self.cam, self.stime)
        for r in c.roofs:
            if r.x + r.w > x0 and r.x < x1:
                RW.draw_roof(s, r, cam, th, t)
        for v in c.vents:
            RW.draw_vent(s, v, self.cam, t)
        for p in c.pads:
            RW.draw_pad(s, p, self.cam, t)
        for bx in c.boxes:
            if bx.x + bx.w > x0 and bx.x < x1:
                RW.draw_box(s, bx, cam, th, t)
        for m in c.lifts:
            RW.draw_lift(s, m, self.cam, t)
        lantern = th[9] == "lanterns"
        for ln in c.lines:
            if ln.x1 > x0 and ln.x0 < x1:
                RW.draw_line(s, ln, self.cam, t, lantern)
        if self.st["kind"] == "normal":
            self.draw_finish(s, t)
        i0 = bisect.bisect_left(c.fish, [x0])
        for i in range(i0, len(c.fish)):
            f = c.fish[i]
            if f[0] > x1:
                break
            if not f[2]:
                RW.draw_fish(s, f, self.cam, t)
        for g in c.gold:
            if not g[2]:
                RW.draw_fish(s, g, self.cam, t, gold=True)
        for cp in c.caps:
            if not cp[3]:
                RW.draw_cap(s, cp, self.cam, t)
        for hz in c.haz:
            RW.draw_hazard(s, hz, self.cam, t, self.stime)
        if self.boss:
            self.boss.draw(s, t)
        self.draw_gully(s, t)
        self.draw_tora(s, t)
        self.parts.draw(s, -cam, 0)
        self.floats.draw(s, -cam, 0)
        RW.draw_weather(s, th[10], t, self.cam)
        self.draw_hud(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "tally":
            self.draw_tally(s, t)

    def draw_sky_fx(self, s, t):
        lm = self.theme[9]
        if lm == "fireworks":
            for i in range(3):
                p = (t * 0.5 + i / 3) % 1
                x, y = 50 + i * 100 + int(math.sin(i * 7) * 20), 30 + (i * 17) % 40
                if p < 0.25:
                    s.fill(col("white"), (x, y + int((0.25 - p) * 300), 1, 3))
                else:
                    r = int((p - 0.25) * 40)
                    c = col(("hotpink", "yellow", "mint")[i])
                    for a in range(0, 360, 30):
                        ra = math.radians(a)
                        s.fill(c, (x + int(math.cos(ra) * r), y + int(math.sin(ra) * r) + int(p * 6), 1, 1))
        elif lm == "lighthouse":
            bx = 286
            s.fill(col("white"), (bx - 4, 60, 8, 110))
            for yy in range(70, 170, 20):
                s.fill(col("red"), (bx - 4, yy, 8, 8))
            s.fill(col("yellow"), (bx - 5, 52, 10, 8))
            a = t * 1.2
            ex = bx + int(math.cos(a) * 160)
            ey = 56 + int(math.sin(a) * 20)
            pygame.draw.line(s, col("yellow"), (bx, 56), (ex, ey))
            pygame.draw.line(s, col("cream"), (bx, 57), (ex, ey + 6))
        elif lm == "clouds":
            for i in range(4):
                x = (i * 97 - int(t * (12 + i * 4))) % (W + 80) - 40
                y = 26 + i * 18
                for dx, r in ((0, 9), (10, 12), (22, 8)):
                    pygame.draw.circle(s, col("darkgray"), (x + dx, y), r)
        if self.theme[10] == "storm" and int(t * 7) % 23 == 0:
            s.fill(col("lavender"), (0, 0, W, 2))

    def draw_finish(self, s, t):
        fx = int(self.course.finish - self.cam)
        if fx < -30 or fx > W + 30:
            return
        gy = self.roof_y_at(self.course.finish) or 150
        for y in range(gy - 60, gy, 6):
            for i in range(2):
                s.fill(col("white" if ((y // 6) + i) % 2 else "black"), (fx + i * 3, y, 3, 6))
        s.fill(col("gray"), (fx + 6, gy - 66, 2, 66))
        draw_text(s, "FINISH", fx + 2, gy - 74, rainbow(0, t), align="center", outline="ink")

    def draw_gully(self, s, t):
        g = self.gully
        if self.st["kind"] != "normal":
            return
        x, y = int(g["x"] - self.cam), int(g["y"])
        if x > W + 20 or x < -30:
            return
        flip = g["state"] in ("flee", "plucked")
        sp = sprite("rr_gully" if g["state"] != "plucked" else "rr_gully_nofish", int(t * 8) % 2, flip=flip)
        s.blit(sp, (x - 11, y - 8))
        if g["state"] == "perch" and not self.feather:
            # the tail feather to grab sticks out behind him
            s.blit(sprite("rr_feather"), (x + 9, y - 2))
            if self.chase < 30 and int(t * 3) % 2:
                draw_text(s, "TOO HIGH? GET CLOSER!", x, y - 22, "white", align="center", outline="ink")
        if self.flash_feather:
            fx, fy, ft = self.flash_feather
            sp = sprite("rr_feather")
            s.blit(sp, (int(fx - self.cam) - 4, int(fy + ft * 20) - 4 + int(math.sin(ft * 6) * 3)))

    def draw_tora(self, s, t):
        b = self.body
        cam = self.cam
        if self.invuln > 0 and int(t * 16) % 2 and self.state == "play":
            return
        for tr in self.trail:
            s.fill(col(rainbow(int(tr[2] * 20), t)), (int(tr[0] - cam) - 6, int(tr[1]) - 9, 3, 3))
        x, y = int(b.x - cam), int(b.y)
        if self.state == "fall":
            name, fr = "rr_tora_hurt", 0
        elif self.state in ("finish", "clear", "tally") and self.speed < 5:
            name, fr = "rr_tora_happy", int(t * 4) % 2
        elif self.state in ("intro", "pick"):
            name, fr = "rr_tora_idle", 1 if int(t * 2) % 5 == 0 else 0
        elif self.hurt_t > 0:
            name, fr = "rr_tora_hurt", 0
        elif b.wire is not None:
            name, fr = "rr_tora_jump", 0
        elif b.ground is None:
            if b.cling:
                name, fr = "rr_tora_cling", 0
            elif b.pounce:
                name, fr = "rr_tora_pounce", 0
            else:
                name, fr = ("rr_tora_jump", 0) if b.vy < 60 else ("rr_tora_fall", 0)
        elif b.slide:
            name, fr = "rr_tora_slide", 0
        else:
            name, fr = "rr_tora_run", int(self.stime * self.speed / 9) % 4
        remap = None
        if self.timers["catnip"] > 0:
            remap = {"o": "l" if int(t * 10) % 2 else "m"}
        elif self.hype.fever_on and int(t * 8) % 2:
            remap = {"o": "y"}
        sp = sprite(name, fr, remap=remap)
        if b.wire is not None:          # hanging from the wire by the front paws
            s.blit(sp, (x - 10, y - 16))
            s.fill(col("black"), (x + 3, y - 16, 2, 3))
            if int(t * 20) % 2:
                s.fill(col("yellow"), (x + 4 + random.randint(-3, 3), y - 16, 1, 1))
        else:
            s.blit(sp, (x - 10, y - 16))
        if self.timers["umbrella"] > 0:
            pygame.draw.polygon(s, col("sky"), [(x - 10, y - 18), (x + 2, y - 28), (x + 14, y - 18)])
            s.fill(col("white"), (x + 2, y - 18, 1, 6))
        if self.shield > 0 and int(t * 4) % 4 == 0:
            pygame.draw.circle(s, col("peach"), (x, y - 7), 11, 1)

    def draw_hud(self, s, t):
        s.fill(col("black"), (0, 0, W, 21))
        s.fill(col("ink"), (0, 21, W, 1))
        draw_text(s, f"{self.score:07d}", 4, 3, "white", shadow=None)
        draw_text(s, f"HI {max(self.best, self.score):07d}", 4, 12, "gray", shadow=None)
        # lives: a cat-head icon and the count
        s.blit(sprite("rr_head"), (W - 30, 2))
        draw_text(s, f"x{self.lives}", W - 21, 3, "pink", shadow=None)
        # fish count
        s.blit(sprite("rr_fish"), (W - 72, 3))
        draw_text(s, f"{self.fish_got}", W - 62, 3, "sky", shadow=None)
        bo = self.boss
        if bo and bo.state != "dead":
            boss_bar(s, bo.name, bo.hp, bo.maxhp, t, y=0, x=92, w=136)
        else:
            if self.st["kind"] == "bonus":
                label = "BONUS RUN"
            elif self.st["kind"] == "boss":
                label = "BOSS STAGE"
            else:
                label = f"STAGE {self.n}"
            draw_text(s, label, W // 2, 3, "yellow", align="center", shadow=None)
        # course progress (normal + bonus) - a strip with Tora's head and the flag
        if self.st["kind"] != "boss" and self.course.finish:
            x0, w = 100, 120
            s.fill(col("darkgray"), (x0, 15, w, 2))
            p = max(0.0, min(1.0, self.body.x / self.course.finish))
            s.fill(col("mint"), (x0, 15, int(w * p), 2))
            s.fill(col("white"), (x0 + w, 11, 1, 6))
            s.fill(col("red"), (x0 + w + 1, 11, 3, 2))
            s.blit(sprite("rr_head"), (x0 + int(w * p) - 4, 11))
        # CHASE meter (fills with fish) and the FEVER gauge
        x0 = W - 72
        s.fill(col("darkgray"), (x0, 13, 46, 3))
        cw = int(46 * self.chase / 100)
        s.fill(col("yellow" if self.chase >= 99.5 and int(t * 8) % 2 else "orange"), (x0, 13, cw, 3))
        s.blit(sprite("rr_feather"), (x0 + 47, 10))
        s.fill(col("darkgray"), (x0, 17, 46, 1))
        if self.hype.fever_on:
            for i in range(46):
                s.fill(col(rainbow(i // 6, t)), (x0 + i, 17, 1, 1))
        else:
            s.fill(col("hotpink"), (x0, 17, int(46 * self.hype.fever), 1))
        # timers (bottom left)
        x = 4
        for k, ic in (("magnet", 0), ("umbrella", 1), ("catnip", 2)):
            v = self.timers[k]
            if v > 0 and (v > 2 or int(t * 8) % 2):
                pygame.draw.circle(s, col("black"), (x + 6, H - 8), 7)
                pygame.draw.circle(s, col(RW.CAP_COLORS[ic]), (x + 6, H - 8), 6)
                pygame.draw.circle(s, col("ink"), (x + 6, H - 8), 4)
                RW.draw_cap_icon(s, ic, x + 6, H - 8, t)
                x += 16
        if self.shield > 0:
            draw_text(s, f"FUR x{self.shield}", x + 2, H - 11, "peach", shadow="ink")

    def draw_intro(self, s, t):
        st = self.st
        k = st["kind"]
        if k == "boss":
            if int(t * 4) % 2:
                for x in range(-20, W + 20, 20):
                    pygame.draw.polygon(s, col("red"), [(x, 98), (x + 10, 98), (x + 20, 106), (x + 10, 106)])
                    pygame.draw.polygon(s, col("red"), [(x, 146), (x + 10, 146), (x + 20, 154), (x + 10, 154)])
            panel(s, (40, 108, 240, 34), fill="black", border="red")
            draw_text(s, "WARNING!!", W // 2, 112, "red" if int(t * 6) % 2 else "yellow", 2, align="center",
                      outline="ink")
            draw_text(s, f"{st['name']} IS ON THE ROOF", W // 2, 130, "white", align="center", shadow=None)
            return
        h = 64
        y0 = 40
        panel(s, (30, y0, 260, h), fill="ink", border="yellow" if k == "bonus" else "peach")
        if k == "bonus":
            title = "BONUS RUN"
            for i, ch in enumerate(title):
                draw_text(s, ch, W // 2 - text_width(title, 2) // 2 + i * 12, y0 + 6 + int(math.sin(t * 8 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            draw_text(s, st["name"], W // 2, y0 + 26, "yellow", align="center")
            draw_text(s, "NO HAZARDS - GRAB ALL THE FISH!", W // 2, y0 + 38, "white", align="center")
            draw_text(s, "FALLING IS FREE HERE", W // 2, y0 + 50, "mint", align="center")
            return
        draw_text(s, f"STAGE {self.n}", W // 2, y0 + 6, "yellow", 2, align="center", outline="ink", shadow=None)
        draw_text(s, f"{self.theme[0]} - {st['name']}", W // 2, y0 + 25, "lavender", align="center")
        if st["new"]:
            draw_text(s, st["new"], W // 2, y0 + 37, "mint" if int(t * 4) % 2 else "lime", align="center")
        draw_text(s, "TORA: " + self.theme[12], W // 2, y0 + 50, "peach", align="center")

    def draw_tally(self, s, t):
        rows = self.tally
        h = 34 + len(rows) * 11
        y0 = 40
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
            draw_text(s, "PRESS JUMP", W // 2, y0 + h - 11, "lavender", align="center", shadow=None)


# ----------------------------------------------------------------------------- autopilot (GIF bot + tests)
PLANS = [(), (("j", 3),), (("j", 9),), (("j", 16),), (("j", 30),), (("d", 40),),
         (("j", 30), ("w", 14), ("j", 20)), (("w", 10), ("j", 30)), (("w", 20), ("j", 30)), (("w", 30), ("j", 30))]


def _simulate(sc, plan, frames, v):
    """Run Tora's physics on a copy of her body with a planned input sequence. Returns (score, steps)."""
    b = sc.body.clone()
    seq = []
    for k, n in plan:
        seq += [k] * n
    held_prev = False
    score = 0.0
    dt = 1 / 60
    stime = sc.stime
    fish = [f for f in sc.course.fish if not f[2] and sc.body.x - 10 < f[0] < sc.body.x + 260]
    fish += [g for g in sc.course.gold if not g[2] and sc.body.x - 10 < g[0] < sc.body.x + 260]
    got = set()
    g = sc.gully
    gully = g["state"] == "perch" and not sc.feather
    for i in range(frames):
        k = seq[i] if i < len(seq) else ""
        jump = k == "j"
        down = k == "d"
        c = RW.Ctrl(jump and not held_prev, jump, False, down, 0)
        held_prev = jump
        RW.step(b, c, dt, v)
        stime += dt
        if b.y > H + 4:
            return -10000 + i, i
        box = b.box()
        for hz in sc.course.haz:
            if hz.alive and abs(hz.x - b.x) < 60:
                r = hz.rect(stime)
                if r is None and hz.k in ("i", "d", "z") and hz.state in (0, 1, 3):
                    r = (hz.x - 8, hz.y - 18, 16, 18) if hz.k != "d" else None
                if hz.k == "q" and hz.state == 1:
                    r = (hz.x - 46 * (stime - sc.stime) - 6, hz.y - 4, 12, 8)
                if r and overlap(box, r):
                    if hz.k in ("p", "q") and b.vy > 0:
                        score += 30
                        continue
                    return -5000 + i, i
        if sc.boss:
            hit = _boss_sim(sc, b, box, stime - sc.stime)
            if hit < 0:
                return -5000 + i, i
            score += hit
        for k, f in enumerate(fish):
            if k not in got and box[0] - 4 <= f[0] <= box[0] + box[2] + 4 and box[1] - 4 <= f[1] <= box[1] + box[3] + 4:
                got.add(k)
                score += 6 if len(f) == 3 else 30
        if gully and overlap(box, (g["x"] - 8, g["y"] - 6, 16, 12)):
            score += 400
            gully = False
        if b.blocked is not None:
            score -= 3
        if b.ground is not None and getattr(b.ground, "glass", 0):
            score -= 2
    score += b.x - sc.body.x
    if b.ground is None and b.wire is None:
        score -= 20          # prefer plans that end on something
    return score, frames


def _boss_sim(sc, b, box, tau):
    """Bot helper: does Tora's box at sim time tau meet a boss attack (-1), or a worn-out boss (+points)?"""
    bo = sc.boss
    for s in bo.shots:
        r = s.rect()
        if s.k == "bolt" and s.state == 0:
            t0 = max(0.5, 0.95 - 0.12 * bo.lv) - s.t
            r = (s.x - 8, s.gy - 16, 17, 16) if t0 - 0.05 <= tau <= t0 + 0.5 else None
        elif r is not None:
            r = (r[0] + s.vx * tau, r[1] + s.vy * tau * (0 if s.state else 1), r[2], r[3])
        if r and overlap(box, r):
            return -1
    if bo.state == "fight" and bo.act in ("dive", "charge"):
        tele = max(0.35, 0.8 - 0.1 * bo.lv) + (0.3 if bo.act == "charge" else 0)
        wait = max(0.0, (tele - bo.at) / bo.rate)
        if bo.act == "dive":
            sx = (bo.dive_x if bo.n_fired else 330.0) - 250 * bo.speed() * max(0.0, tau - wait)
            r = (b.x - TORA_X + sx - 10, bo.dive_y - 7, 20, 14)
        else:
            sx = bo.sx - 230 * bo.speed() * max(0.0, tau - wait)
            r = (b.x - TORA_X + sx - 14, bo.by - 21, 28, 21)
        if overlap(box, r):
            return -1
    if bo.state == "dazed":
        r = bo.body_rect()
        if r and overlap(box, r) and b.vy > 0:
            return 600
    return 0


def autopilot(sc):
    """Pick an input each frame by trying a few jump plans on a copy of Tora's physics."""
    keys = set()
    if sc.overlay is not None:
        k = sc.__dict__.get("_bot_pick", 0)
        sc._bot_pick = k + 1
        if k % 20 == 19:
            keys.add("a")
        return keys
    if sc.state in ("intro", "tally"):
        if int(sc.t * 60) % 30 == 0:
            keys.add("a")
        return keys
    if sc.state != "play":
        return keys
    bot = sc.__dict__.setdefault("_bot", {"plan": [], "i": 0, "cool": 0})
    bot["cool"] -= 1
    if bot["cool"] <= 0 or bot["i"] >= len(bot["plan"]):
        v = sc.view(sc.body.x - 40, sc.body.x + 300)
        best, best_plan = None, ()
        for plan in PLANS:
            score, _ = _simulate(sc, plan, 75, v)
            if best is None or score > best + 0.5:
                best, best_plan = score, plan
        seq = []
        for k, n in best_plan:
            seq += [k] * n
        bot["plan"] = seq
        bot["i"] = 0
        bot["cool"] = 5
    if bot["i"] < len(bot["plan"]):
        k = bot["plan"][bot["i"]]
        bot["i"] += 1
        if k == "j":
            keys.add("a")
        elif k == "d":
            keys.add("down")
    return keys


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys."""
    return lambda frame: autopilot(scene)


# ----------------------------------------------------------------------------- carousel preview
def preview(s, t):
    w, h = s.get_size()
    s.fill(col("night"))
    for i in range(8):
        s.fill(lerp(i), (0, i * h // 8, w, h // 8 + 1))
    pygame.draw.circle(s, col("cream"), (w - 18, 14), 8)
    pygame.draw.circle(s, col("white"), (w - 19, 13), 6)
    off = int(t * 50)
    for i in range(5):
        bx = i * 40 - off % 40 - 10
        top = h - 22 - (((i + off // 40) * 7) % 3) * 6
        s.fill(col("ink"), (bx, top - 14, 30, h))
    for i in range(4):
        rx = i * 48 - off % 48
        gap = 10
        ry = h - 16 + (((i + off // 48) * 5) % 2) * 4
        s.fill(col("brown"), (rx, ry, 48 - gap, h - ry))
        s.fill(col("peach"), (rx - 1, ry, 48 - gap + 2, 2))
        for wx in range(rx + 4, rx + 36, 9):
            s.fill(col("yellow"), (wx, ry + 6, 4, 4))
    for i in range(5):
        fx = (i * 23 - off) % (w + 20) - 10
        s.blit(sprite("rr_fish"), (fx, h - 34 - int(abs(math.sin(i + t)) * 10)))
    jy = int(abs(math.sin(t * 3)) * 16)
    s.blit(sprite("rr_tora_run" if jy < 3 else "rr_tora_jump", int(t * 12) % 4), (24, h - 32 - jy))
    s.blit(sprite("rr_gully", int(t * 8) % 2, flip=True), (w - 40 + int(math.sin(t * 2) * 6), 18 + int(math.sin(t * 3) * 3)))


def lerp(i):
    from mochi_arcade.gfx import lerp_col
    return lerp_col("night", "deep", i / 7)
