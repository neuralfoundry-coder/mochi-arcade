"""PAW PINBALL - flip, bump and purr! (original game)

Kiki the tuxedo cat runs a cat-cafe pinball machine: the ball is a jingle bell and her white-socked paws are
the flippers. 200 missions over 20 tables (paw_pinball_tables.py): bop cat-face bumpers, knock down fish
targets, spell M-E-O-W in the top lanes, climb the cat tower, ride the fish slide, sink the nap bed, rescue
lost kittens and start KITTEN MULTIBALL. A troublemaker boss barges in every 10th stage
(paw_pinball_boss.py), every x5 stage is a bonus frenzy, and bosses / bonuses hand out upgrade cards.
The iOS port (ios/MochiArcade/Games/PawPinball*.swift) mirrors this file and reads the tables from EXPORT.
"""
import math
import random

import pygame

from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow
from mochi_arcade.games import DIFF
from mochi_arcade.games import paw_pinball_art as A
from mochi_arcade.games import paw_pinball_tables as T
from mochi_arcade.games.base import LIVES, GameScene
from mochi_arcade.games.paw_pinball_boss import Boss
from mochi_arcade.games.paw_pinball_phys import GRAV, LANE_START, Ball, Flipper, Physics, ramp_lengths, ramp_pos
from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

HOWTO = ["LEFT / RIGHT  LEFT / RIGHT PAW (FLIPPERS)", "DOWN (HOLD)   PULL THE PLUNGER, LET GO",
         "UP / C        NUDGE THE TABLE (DON'T TILT!)", "",
         "KIKI'S CAFE MACHINE: 200 MISSIONS -", "BOP CAT BUMPERS, DROP FISH, SPELL MEOW,",
         "CLIMB THE TOWER, RESCUE KITTENS. BOSS ON", "EVERY 10TH STAGE, BONUS FRENZY ON X5.",
         "ENTER / ESC  PAUSE"]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["left", "right", "down", "a", "up"]

EXPORT = {"tables": T.TABLES, "arena": T.ARENA, "stages": T.CAMPAIGN}

LIFE_AT = [50000, 150000, 300000, 500000]        # then every 300000
NAP_TIME = 1.1
LEFT_PANEL, RIGHT_PANEL = 33, 287                # panel centres


# ----------------------------------------------------------------------------- upgrade cards
def _icon_paws(s, cx, cy, t):
    w = 7 + int(math.sin(t * 4) * 2)
    for side in (-1, 1):
        pygame.draw.line(s, col("white"), (cx + side * 2, cy + 3), (cx + side * (2 + w), cy - 1), 3)
        s.fill(col("pink"), (cx + side * (1 + w), cy, 1, 1))


def _icon_save(s, cx, cy, t):
    sp = sprite("pp_bell")
    s.blit(sp, (cx - 3, cy - 3 - int(abs(math.sin(t * 4)) * 3)))
    s.fill(col("mint"), (cx - 6, cy + 5, 13, 1))


def _icon_kick(s, cx, cy, t):
    y = int(abs(math.sin(t * 5)) * 6)
    s.fill(col("orange"), (cx - 2, cy + 2, 5, 4))
    s.blit(sprite("pp_bell"), (cx - 3, cy - 4 - y))


def _icon_tail(s, cx, cy, t):
    for i in range(6):
        s.fill(col("black"), (cx - 3 + i + int(math.sin(t * 5 + i) * 1), cy + 4 - i * 2, 2, 2))
    s.fill(col("white"), (cx + 3, cy - 7, 2, 2))


def _icon_power(s, cx, cy, t):
    pygame.draw.circle(s, col("red"), (cx, cy), 5)
    for dx, dy in ((-4, -6), (-1, -8), (2, -8), (5, -6)):
        pygame.draw.circle(s, col("red"), (cx + dx, cy + dy + 2), 1)
    s.fill(col("white"), (cx - 1, cy - 1, 2, 2))


def _icon_bell(s, cx, cy, t):
    s.blit(sprite("pp_bell"), (cx - 3, cy - 3))
    if int(t * 6) % 2:
        s.fill(col("white"), (cx + 4, cy - 5, 1, 1))
        s.fill(col("white"), (cx - 5, cy + 3, 1, 1))


def _icon_catnip(s, cx, cy, t):
    for i in range(3):
        pygame.draw.circle(s, col(rainbow(i, t)), (cx - 4 + i * 4, cy + 1 - (i % 2) * 3), 2)
    s.fill(col("lime"), (cx, cy + 3, 1, 4))


def _icon_luck(s, cx, cy, t):
    w = max(1, int(abs(math.cos(t * 3)) * 5))
    pygame.draw.ellipse(s, col("orange"), (cx - w, cy - 5, w * 2 + 1, 11))
    pygame.draw.ellipse(s, col("yellow"), (cx - w + 1, cy - 4, max(1, w * 2 - 1), 9))


def _icon_spring(s, cx, cy, t):
    k = int(abs(math.sin(t * 6)) * 3)
    for i in range(4):
        s.fill(col("sky"), (cx - 4, cy + 4 - i * (2 + k // 2), 9, 1))
    s.fill(col("white"), (cx - 1, cy - 6 - k, 3, 3))


def _icon_multi(s, cx, cy, t):
    for i, dx in enumerate((-5, 0, 5)):
        s.blit(sprite("pp_kball", remap=A.KITTEN_COATS[i]), (cx + dx - 3, cy - 3 + int(math.sin(t * 6 + i) * 2)))


UPGRADES = [
    Upgrade("paws", "BIG PAWS", "LONGER|FLIPPERS", "white", _icon_paws, 3),
    Upgrade("save", "NINE LIVES", "LONGER|BALL SAVE", "mint", _icon_save, 3),
    Upgrade("kick", "KICKBACK", "SAVES AN|OUTLANE BALL|LV2: BOTH SIDES", "orange", _icon_kick, 2),
    Upgrade("tail", "TAIL POST", "KIKI'S TAIL|GUARDS THE|MIDDLE A WHILE", "lavender", _icon_tail, 3),
    Upgrade("power", "POWER PAW", "+1 BOSS HIT|FISH WORTH|MORE", "red", _icon_power, 3),
    Upgrade("bell", "GOLDEN BELL", "+25% ALL|POINTS", "yellow", _icon_bell, 4),
    Upgrade("catnip", "CATNIP", "FEVER FILLS|FASTER AND|LASTS LONGER", "lime", _icon_catnip, 3),
    Upgrade("luck", "LUCKY CHARM", "BETTER NAP|PRIZES AND|JACKPOTS", "orange", _icon_luck, 3),
    Upgrade("spring", "SPRING PAWS", "STRONGER|FLIPS, EASIER|RAMPS", "sky", _icon_spring, 3),
    Upgrade("multi", "KITTEN PILE", "+1 KITTEN|IN MULTIBALL", "pink", _icon_multi, 2),
    Upgrade("life", "EXTRA BALL", "+1 BALL|RIGHT NOW", "hotpink", "heart", 5),
]


# ----------------------------------------------------------------------------- the game
class PawPinball(GameScene):
    @property
    def music(self):
        return self.song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES[d] + 1          # pinball eats balls: one spare on top
        self.levels = {}
        self.life_i = 0
        self.picks_left = 0
        self.pick_title = "POWER UP!"
        self.next_n = None
        self.hype.COMBO_TIME = 3.0
        self.hype.combo_y = 191
        self.mood, self.mood_t = "idle", 0.0
        start = max(1, min(STAGES, int(opt.get("stage", opt.get("start", 1)))))
        self.start_stage(start)
        if start > 10:          # starting from a checkpoint: catch up on some upgrades first
            self.picks_left = min(8, (start - 1) // 10)
            self.pick_title = "HEAD START!"
            self.state = "pick"

    # ---------------------------------------------------------------- helpers
    def lv(self, uid):
        return self.levels.get(uid, 0)

    def pts(self, base):
        return int(base * (10 + self.tier) / 10 * (1 + 0.25 * self.lv("bell")))

    def score_at(self, base, x=None, y=None, color="yellow"):
        return self.add(self.pts(base), x, y, color)

    def add(self, pts, x=None, y=None, color="yellow"):
        got = super().add(pts, x, y, color)
        self.stage_score += got
        if "score" in self.prog:
            self.prog["score"] += got
        self.check_life()
        return got

    def ball_dmg(self):
        return 1 + self.lv("power")

    def song(self):
        k = self.st["kind"]
        return "boss" if k == "boss" else "bonus" if k == "bonus" else ("pp_cafe" if self.tier % 2 == 0 else "pp_moon")

    def paw_len(self):
        return 23.0 + 2 * self.lv("paws")

    def save_len(self):
        return float(self.st["save"] + 4 * self.lv("save"))

    def locks_needed(self):
        return 2

    def set_mood(self, m, dur=1.2):
        self.mood, self.mood_t = m, dur

    def live_balls(self):
        return [b for b in self.balls if b.state != "gone"]

    # ---------------------------------------------------------------- stages
    def start_stage(self, n):
        self.n = n
        st = self.st = T.CAMPAIGN[n - 1]
        self.tier = st["tier"]
        self.tb = T.ARENA if st["kind"] == "boss" else T.TABLES[self.tier]
        self.theme = T.TABLES[self.tier]["theme"]
        self.reached(n)
        self.phys = Physics(self, self.tb)
        self.phys.grav = GRAV * st["grav"]
        self.flippers = [Flipper(T.FLIP_X[0], T.FLIP_Y, 1, self.paw_len()),
                         Flipper(T.FLIP_X[1], T.FLIP_Y, -1, self.paw_len())]
        for f in self.flippers:
            f.power = 1 + 0.07 * self.lv("spring")
        self.ramp_ease = 1 - 0.1 * self.lv("spring")
        self.fish = [list(f[:6]) + [0.0] for f in self.tb["fish"]]      # [x1, y1, x2, y2, face, bank, down]
        self.banks = sorted({f[5] for f in self.fish})
        self.bank_reset = {b: 0.0 for b in self.banks}
        self.bump_t = [0.0] * len(self.tb["bumpers"])
        self.ramp_lens = [ramp_lengths(r["path"]) for r in self.tb["ramps"]]
        self.ramp_flash = [0.0] * len(self.tb["ramps"])
        self.lanes = [False] * 4
        self.bonus_x = 1
        self.kittens = []           # [x, y, coat, spot, golden, life]
        self.kitten_cd = 2.0
        self.coins = []             # bonus fountain: [x, y, rainbow, life]
        self.coin_cd = 0.5
        self.dyn = []
        self.balls = []
        self.queue = []             # balls waiting for the plunger: kind
        self.goals = st["goals"]
        self.prog = {g: 0 for g, _ in self.goals}
        self.time_left = float(st["time"])
        self.timer_on = False
        self.save_t = 0.0
        self.save_ready = True
        self.kick = [self.lv("kick") >= 1, self.lv("kick") >= 2]
        self.tail_t = 0.0
        self.tail_on = False
        self.tilt = 0.0
        self.tilted = False
        self.locks = 0
        self.lock_lit = False
        self.multiball = False
        self.jackpot_lit = False
        self.jp_t = 0.0
        self.last_ramp = -99.0
        self.chain = 0
        self.skill = -1
        self.skill_t = 0.0
        self.pull = 0.0
        self.armed = False
        self.spin_a = 0.0
        self.spin_v = 0.0
        self.stage_score = 0
        self.stats = {"switch": 0, "jackpot": 0, "coins": 0, "rainbow": 0, "combo": 0}
        self.missed = False
        self.extra_given = False
        self.stime = 0.0
        self.sound_t = 0.0
        self.boss = Boss(self, st["boss"]) if st["kind"] == "boss" else None
        self.golden = st["kind"] == "normal" and self.hype.lucky(0.04 + 0.015 * self.lv("luck"))
        self.golden_t = random.uniform(8, 20)
        self.bg = A.make_bg(self.tb, self.theme)
        self.tally = []
        self.state = "intro"
        self.state_t = 0.0
        self.intro_len = 3.2 if self.boss else 2.6
        if st["kind"] == "bonus":
            self.queue = ["kitten"] * (3 if st["bonus"] == "party" else 2)
            self.jackpot_lit = st["bonus"] == "party"
        else:
            self.serve("bell", auto=False)
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.hype.FEVER_TIME = 8.0 + 2 * self.lv("catnip")
        self.app.audio.music(self.song())
        self.app.audio.play("warning" if self.boss else "stage")
        if self.boss:
            self.hype.flash("red", 0.3)
            self.set_mood("angry", 99)
        else:
            self.set_mood("happy", 1.5)

    def serve(self, kind="bell", auto=True):
        b = Ball(LANE_START[0], LANE_START[1], 0.0, 0.0, kind)
        b.coat = random.randint(0, 5)
        if auto:
            b.auto = 0.35
        else:
            self.skill = random.randint(0, 3)
            self.skill_t = 0.0
        self.balls.append(b)
        return b

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        self.mood_t -= dt
        if self.mood_t <= 0:
            self.mood = "angry" if self.boss and self.boss.state != "dead" else "idle"
        s = self.state
        if s == "intro":
            self.flip_input(dt)
            self.phys.events = []
            self.phys.step(dt)
            if self.boss:
                self.boss.update(dt)
            if self.state_t > self.intro_len or (self.state_t > 0.5 and self.app.input.hit("a")):
                self.state = "play"
                self.state_t = 0.0
                self.armed = not self.app.input.down("a", "down")
                if self.boss:
                    self.boss.state = "fight"
        elif s == "play":
            self.play(dt)
        elif s == "lost":
            self.flip_input(dt)
            if self.state_t > 1.6:
                self.state = "play"
                self.state_t = 0.0
                self.save_ready = True
                self.tilted = False
                self.tilt = 0.0
                self.serve("bell", auto=False)
                self.armed = not self.app.input.down("a", "down")
        elif s == "clear":
            self.flip_input(dt)
            for b in self.balls:
                if b.state == "play" and int(self.state_t * 30) % 3 == 0:
                    self.parts.sparkle(b.x, b.y, "yellow")
            if self.boss:
                self.boss.update(dt)
            if self.state_t > 1.8:
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
        self.update_fx(dt)

    def update_fx(self, dt):
        self.bump_t = [max(0.0, v - dt) for v in self.bump_t]
        self.ramp_flash = [max(0.0, v - dt) for v in self.ramp_flash]
        self.spin_a += self.spin_v * dt
        self.spin_v *= max(0.0, 1 - dt * 1.5)
        for b in self.balls:
            if b.state == "play":
                b.trail.append((b.x, b.y))
                if len(b.trail) > 6:
                    b.trail.pop(0)

    def on_pick(self, uid):
        if not uid:
            return
        self.levels[uid] = self.lv(uid) + 1
        u = next(x for x in UPGRADES if x.id == uid)
        self.hype.banner(u.name, f"LEVEL {self.levels[uid]}", color=u.color, dur=1.2, scale=1)
        if uid == "life":
            self.lives += 1
            self.app.audio.play("extra")
        elif uid == "paws":
            for f in self.flippers:
                f.len = self.paw_len()
        elif uid == "spring":
            for f in self.flippers:
                f.power = 1 + 0.07 * self.lv("spring")
            self.ramp_ease = 1 - 0.1 * self.lv("spring")
        elif uid == "kick":
            self.kick = [self.lv("kick") >= 1, self.lv("kick") >= 2]

    # ---------------------------------------------------------------- input
    def flip_input(self, dt):
        inp = self.app.input
        lp, rp = inp.down("left", "b"), inp.down("right", "a")
        for i, (f, p) in enumerate(zip(self.flippers, (lp, rp))):
            f.stun = max(0.0, f.stun - dt)
            if self.tilted or self.state not in ("play", "intro", "lost", "clear"):
                p = False
            if p and not f.pressed and f.stun <= 0:
                self.app.audio.play("lock")
                if not all(self.lanes):           # lane change: the lit letters slide with the paws
                    self.lanes = self.lanes[1:] + self.lanes[:1] if i == 0 else self.lanes[-1:] + self.lanes[:-1]
            f.pressed = p

    def plunger(self, dt):
        inp = self.app.input
        held = inp.down("a", "down")
        ball = None
        for b in self.balls:
            if b.state == "play" and b.on_plunger():
                ball = b
                break
        if ball is not None and ball.auto >= 0:
            ball.auto -= dt
            if ball.auto < 0:
                self.launch(ball, 0.62 + random.uniform(0.0, 0.3))
            return
        if not held:
            if self.pull > 0.04 and ball is not None:
                self.launch(ball, self.pull)
            self.pull = 0.0
            self.armed = True
        elif self.armed and ball is not None:
            self.pull = min(1.0, self.pull + dt / 0.9)

    def launch(self, b, power):
        b.vy = -(240 + 380 * power)
        b.vx = 0.0
        b.auto = -1.0
        self.app.audio.play("shoot")
        self.pull = 0.0

    def nudge(self):
        if self.tilted:
            return
        self.tilt += 0.4
        self.app.shake(2, 0.15)
        self.app.audio.play("hold")
        for b in self.balls:
            if b.state == "play" and not b.in_lane():
                b.vy -= 80
                b.vx += random.uniform(-30, 30)
        if self.tilt > 1.0:
            self.tilted = True
            self.save_t = 0.0
            self.hype.banner("TILT!", "PAWS OFF THE TABLE", color="red", dur=2.0, sound="boom")
            self.hype.flash("red", 0.3)
            self.set_mood("hurt", 2.0)
            self.hype.break_combo()
        elif self.tilt > 0.6:
            self.hype.banner("DANGER!", color="orange", dur=0.8, scale=1)

    # ---------------------------------------------------------------- play
    def play(self, dt):
        inp = self.app.input
        st = self.st
        self.stime += dt
        self.sound_t -= dt
        self.flip_input(dt)
        self.plunger(dt)
        if inp.hit("up", "x"):
            self.nudge()
        self.tilt = max(0.0, self.tilt - dt * 0.35)
        if self.save_t > 0:
            self.save_t -= dt
        if self.tail_t > 0:
            self.tail_t -= dt
        self.tail_on = self.tail_t > 0
        self.jp_t -= dt
        if self.multiball and not self.jackpot_lit and self.jp_t <= 0:
            self.jackpot_lit = True
            self.hype.banner("JACKPOT LIT!", "HIT A RAMP", color="yellow", dur=1.0, scale=1)
        if self.skill >= 0:
            self.skill_t += dt
        # serve waiting balls one at a time
        if self.queue and not any(b.state == "play" and b.in_lane() for b in self.balls):
            self.serve(self.queue.pop(0), auto=True)
        # timers
        if self.timer_on and (st["time"] > 0):
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_up()
                return
        self.update_kittens(dt)
        if st["kind"] == "bonus" and st["bonus"] == "fountain":
            self.update_coins(dt)
        if self.boss:
            self.boss.update(dt)
        for bank in self.banks:
            if self.bank_reset[bank] > 0:
                self.bank_reset[bank] -= dt
                if self.bank_reset[bank] <= 0:
                    for f in self.fish:
                        if f[5] == bank:
                            f[6] = 0.0
        # physics
        self.dyn = self.make_dyn()
        self.phys.events = []
        self.phys.step(dt)
        for ev in self.phys.events:
            self.on_event(*ev)
        self.update_balls(dt)
        self.update_drains()
        self.check_mission()

    def make_dyn(self):
        out = []
        for i, k in enumerate(self.kittens):
            out.append([k[0], k[1], 5.0, "kitten", True, i])
        for i, c in enumerate(self.coins):
            out.append([c[0], c[1], 5.0, "coin", False, i])
        if self.boss:
            out += self.boss.dyn()
        return out

    def update_balls(self, dt):
        for b in self.balls:
            b.boss_cd = max(0.0, b.boss_cd - dt)
            b.nap_cd = max(0.0, b.nap_cd - dt)
            if b.state == "ramp":
                r = self.tb["ramps"][b.ramp]
                lens = self.ramp_lens[b.ramp]
                b.rd += b.rv * dt
                b.x, b.y, _, _ = ramp_pos(r["path"], lens, b.rd)
                if b.rd >= lens[-1]:
                    b.state = "play"
                    b.vx, b.vy = float(r["out"][0]), float(r["out"][1])
                    b.trail = []
                    self.ramp_done(b, b.ramp)
            elif b.state == "nap":
                b.nap_t += dt
                if b.nap_t > NAP_TIME:
                    b.state = "play"
                    b.nap_cd = 0.6
                    sx = self.tb["saucer"][0]
                    d = -1 if sx > T.CX + 10 else (1 if sx < T.CX - 10 else random.choice((-1, 1)))
                    b.vx, b.vy = d * random.uniform(110, 160), random.uniform(120, 170)
                    self.app.audio.play("shoot")
                    self.parts.burst(b.x, b.y, 8, ("lavender", "white"), 50, 0.4)
            elif b.state == "play":
                # kickbacks in the outlanes
                if b.y > 172 and b.vy > 0:
                    side = 0 if b.x < 84 else (1 if 226 < b.x < T.RW else -1)
                    if side >= 0 and self.kick[side]:
                        self.kick[side] = False
                        b.vy, b.vx = -470.0, (25.0 if side == 0 else -25.0)
                        self.hype.banner("KICKBACK!", color="orange", dur=0.9, scale=1, sound="boom")
                        self.app.shake(3, 0.2)
                        self.parts.burst(b.x, b.y, 12, ("orange", "yellow"), 80, 0.5)
                # stuck rescue (cradling on a raised paw is fine)
                if math.hypot(b.x - b.ax, b.y - b.ay) > 5:
                    b.ax, b.ay, b.still_t = b.x, b.y, 0.0
                else:
                    b.still_t += dt
                    near_paws = b.y > 150 and abs(b.x - T.CX) < 40
                    if b.still_t > 2.5 and not near_paws and not b.in_lane():
                        b.vy, b.vx = -220.0, random.uniform(-90, 90)
                        b.still_t = 0.0
                        self.floats.add(b.x, b.y - 8, "NUDGE!", "white")
                    if b.still_t > 6 and b.in_lane() and b.auto < 0 and self.st["kind"] == "bonus":
                        b.auto = 0.1

    def update_drains(self):
        gone = [b for b in self.balls if b.state == "gone"]
        if not gone:
            return
        self.balls = [b for b in self.balls if b.state != "gone"]
        saved = False
        for b in gone:
            if self.st["kind"] == "bonus" or (self.save_t > 0 and not self.tilted):
                self.queue.append(b.kind)
                saved = True
        if saved and self.st["kind"] != "bonus":
            self.hype.banner("BALL SAVED!", "KIKI CAUGHT IT", color="mint", dur=1.2, scale=1, sound="powerup")
        alive = [b for b in self.balls if b.state != "gone"]
        if self.multiball and len(alive) + len(self.queue) <= 1:
            self.multiball = False
            self.jackpot_lit = False
            self.hype.banner("MULTIBALL OVER", color="lavender", dur=1.0, scale=1)
        if not alive and not self.queue:
            self.ball_lost()

    def ball_lost(self):
        self.lives -= 1
        self.missed = True
        self.multiball = False
        self.jackpot_lit = self.st["kind"] == "bonus" and self.st["bonus"] == "party"
        self.timer_on = False
        self.hype.break_combo()
        self.app.audio.play("die")
        self.set_mood("sad", 2.0)
        self.app.shake(3, 0.3)
        if self.boss:
            self.boss.release_ball()
        if self.lives <= 0:
            self.state = "over"
            self.hype.banner("GAME OVER", "KIKI NEEDS A NAP...", color="red", dur=3.0)
            self.end_game(False, f"STAGE {self.n}", delay=2.6)
            self.app.audio.play("gameover")
            return
        self.state = "lost"
        self.state_t = 0.0
        self.hype.banner("BALL LOST", f"{self.lives} LEFT", color="pink", dur=1.4, scale=1)

    def time_up(self):
        self.hype.banner("TIME UP!", "-1 BALL", color="red", dur=1.6, sound="hurt")
        self.time_left = float(self.st["time"])
        for b in self.balls:
            if b.state == "held" and self.boss:
                self.boss.release_ball()
            self.parts.burst(b.x, b.y, 8, ("white", "gray"), 40, 0.4)
        self.balls = []
        self.queue = []
        self.ball_lost()

    def check_life(self):
        target = LIFE_AT[self.life_i] if self.life_i < len(LIFE_AT) else LIFE_AT[-1] + 300000 * (self.life_i - len(LIFE_AT) + 1)
        if self.score >= target:
            self.life_i += 1
            self.lives += 1
            self.hype.banner("EXTRA BALL!", color="hotpink", dur=1.5, sound="extra")
            self.hype.shower(30, "hearts")

    # ---------------------------------------------------------------- events
    def switch_hit(self):
        self.stats["switch"] += 1
        if "hits" in self.prog:
            self.prog["hits"] += 1
        self.hype.hit(1, fever=0.016 * (1 + 0.4 * self.lv("catnip")))

    def on_event(self, kind, a, x, y):
        au = self.app.audio
        if kind == "bumper":
            if self.bump_t[a] > 0.05:
                return
            self.bump_t[a] = 0.15
            au.play("pop")
            self.score_at(100, x, y - 12)
            self.parts.burst(x, y, 6, ("white", self.theme["bump"], "yellow"), 50, 0.35)
            if "bump" in self.prog:
                self.prog["bump"] += 1
            self.switch_hit()
            if self.boss is None and random.random() < 0.15:
                self.floats.add(x, y - 18, random.choice(("MEW!", "MRRP!", "NYA!", "PURR!")), "pink")
        elif kind == "sling":
            if self.sound_t <= 0:
                au.play("brick")
                self.sound_t = 0.05
            self.score_at(30)
            self.switch_hit()
        elif kind == "wall":
            if self.sound_t <= 0 and a > 200:
                au.play("tin")
                self.sound_t = 0.08
        elif kind == "flip_hit":
            pass
        elif kind == "fish":
            self.fish_hit(a, x, y)
        elif kind == "lane":
            self.lane_hit(a, x, y)
        elif kind == "spin":
            spins = max(1, a // 70)
            self.spin_v = min(40.0, a / 8)
            au.play("type")
            self.score_at(40 * spins, x, y - 8, "pink")
            if "spin" in self.prog:
                self.prog["spin"] += spins
            self.switch_hit()
        elif kind == "nap":
            self.nap_hit(x, y)
        elif kind == "ramp_in":
            au.play("jump")
            self.ramp_flash[a] = 0.5
            self.set_mood("wow", 1.0)
        elif kind == "ramp_fail":
            self.floats.add(x, y - 8, "TOO SLOW!", "gray")
        elif kind == "launched":
            self.launched()
        elif kind == "kitten":
            self.kitten_hit(a, x, y)
        elif kind == "coin":
            if a < len(self.coins) and self.coins[a][3] > 0:
                c = self.coins[a]
                c[3] = 0.0
                if c[2]:
                    self.stats["rainbow"] += 1
                    self.score_at(2500, c[0], c[1] - 8, "hotpink")
                    au.play("bonus")
                    self.hype.shower(14, "stars")
                else:
                    self.stats["coins"] += 1
                    self.score_at(250, c[0], c[1] - 8)
                    au.play("coin")
                self.switch_hit()
        elif kind in ("boss", "grab", "eat", "bunny", "pickle"):
            if self.boss:
                b = self.ball_at(x, y)
                if b is not None or kind in ("bunny", "pickle"):
                    self.boss.on_ball(kind, a, b)
        elif kind == "drain":
            pass

    def ball_at(self, x, y):
        best, bd = None, 1e9
        for b in self.balls:
            if b.state == "play":
                d = (b.x - x) ** 2 + (b.y - y) ** 2
                if d < bd:
                    best, bd = b, d
        return best

    def launched(self):
        if self.save_ready and self.st["kind"] != "bonus":
            self.save_ready = False
            self.save_t = self.save_len()
            if self.lv("tail"):
                self.tail_t = 5.0 + 10 * self.lv("tail")
        self.timer_on = True

    def fish_hit(self, i, x, y):
        f = self.fish[i]
        self.app.audio.play("fruit")
        self.score_at(500 * (1 + 0.5 * self.lv("power")), x, y - 8, "sky")
        self.parts.burst(x, y, 8, ("sky", "white", "blue"), 50, 0.4)
        if "fish" in self.prog:
            self.prog["fish"] += 1
        self.switch_hit()
        bank = f[5]
        if all(g[6] > 0 for g in self.fish if g[5] == bank):
            self.bank_reset[bank] = 1.2
            self.score_at(2500, x, y - 18, "mint")
            self.app.audio.play("line")
            if self.boss:
                self.hype.banner("FISH BARRAGE!", color="orange", dur=1.0, scale=1)
                for k in range(3):
                    self.boss.projs.append([x + (k - 1) * 8, y, (k - 1) * 60.0, -160.0, "missile", self.ball_dmg(), False])
            elif self.tb["saucer"] and not self.multiball and not self.lock_lit and self.st["kind"] == "normal":
                self.lock_lit = True
                self.hype.banner("LOCK IS LIT!", "SHOOT THE NAP BED", color="lavender", dur=1.2, scale=1)
            else:
                self.hype.banner("FISH FRY!", color="sky", dur=0.9, scale=1)

    def lane_hit(self, i, x, y):
        au = self.app.audio
        if self.skill >= 0:
            if i == self.skill and self.skill_t < 6:
                self.hype.banner("SKILL SHOT!", f"+{self.pts(5000)}", rainbow=True, dur=1.4, sound="bonus")
                self.score_at(5000)
                self.set_mood("happy", 1.5)
            self.skill = -1
        if not self.lanes[i]:
            self.lanes[i] = True
            au.play("select")
            self.score_at(250, x, y - 10)
        else:
            self.score_at(100, x, y - 10)
        self.switch_hit()
        if all(self.lanes):
            self.lanes = [False] * 4
            self.bonus_x = min(6, self.bonus_x + 1)
            self.score_at(2000 + 500 * self.bonus_x)
            if "meow" in self.prog:
                self.prog["meow"] += 1
            self.hype.banner("MEOW!!", f"BONUS X{self.bonus_x}", rainbow=True, dur=1.4, sound="quad")
            self.hype.shower(20, "hearts")
            self.set_mood("happy", 1.6)
            if self.lv("kick"):
                self.kick = [self.lv("kick") >= 1 or self.kick[0], self.lv("kick") >= 2 or self.kick[1]]

    def nap_hit(self, x, y):
        au = self.app.audio
        au.play("trap")
        self.set_mood("sleepy", NAP_TIME + 0.4)
        self.score_at(1000, x, y - 12, "lavender")
        if "nap" in self.prog:
            self.prog["nap"] += 1
        self.switch_hit()
        if self.st["kind"] == "bonus":
            return
        if self.lock_lit and not self.multiball:
            self.lock_lit = False
            self.locks += 1
            if self.locks >= self.locks_needed():
                self.start_multiball()
            else:
                self.hype.banner("KITTEN LOCKED!", f"{self.locks}/{self.locks_needed()}", color="pink", dur=1.3,
                                 sound="levelup")
            return
        self.nap_prize(x, y)

    def nap_prize(self, x, y):
        r = random.random()
        luck = self.lv("luck")
        if r < 0.015 + 0.01 * luck:
            self.hype.jackpot(self.pts(20000), "NAP JACKPOT!")
            self.stats["jackpot"] += 1
            self.set_mood("wow", 2.0)
            return
        if r < 0.04 + 0.012 * luck and not self.extra_given:
            self.extra_given = True
            self.lives += 1
            self.hype.banner("EXTRA BALL!", "SWEET DREAMS", color="hotpink", dur=1.5, sound="extra")
            return
        prizes = ["points", "save", "lane", "catnip"]
        if self.tb["fish"] and not self.lock_lit and not self.multiball:
            prizes.append("lock")
        if not self.kick[0]:
            prizes.append("kick")
        p = random.choice(prizes)
        if p == "points":
            got = self.score_at(5000 + 2500 * luck)
            self.hype.banner("DREAM POINTS", f"+{got}", color="yellow", dur=1.1, scale=1)
        elif p == "save":
            self.save_t = max(self.save_t, 10.0)
            self.hype.banner("BALL SAVE 10S", color="mint", dur=1.1, scale=1)
        elif p == "lane":
            off = [i for i, v in enumerate(self.lanes) if not v]
            if off:
                self.lanes[random.choice(off)] = True
            self.hype.banner("FREE LETTER", color="yellow", dur=1.1, scale=1)
        elif p == "catnip":
            self.hype.fever_add(0.35)
            self.hype.banner("CATNIP!", "FEVER UP", color="lime", dur=1.1, scale=1)
        elif p == "lock":
            self.lock_lit = True
            self.hype.banner("LOCK IS LIT!", color="lavender", dur=1.1, scale=1)
        elif p == "kick":
            self.kick[0] = True
            self.hype.banner("KICKBACK LIT", color="orange", dur=1.1, scale=1)
        self.app.audio.play("powerup")

    def start_multiball(self):
        self.locks = 0
        self.multiball = True
        self.jackpot_lit = True
        self.save_t = max(self.save_t, 10.0)
        n = 2 + self.lv("multi")
        self.queue += ["kitten"] * n
        self.hype.banner("KITTEN MULTIBALL!", "HIT THE RAMPS FOR JACKPOTS", rainbow=True, dur=2.0, sound="fever")
        self.hype.shower(40, "confetti")
        self.hype.flash("pink", 0.25)
        self.set_mood("wow", 2.5)
        if "multi" in self.prog:
            self.prog["multi"] += 1

    def ramp_done(self, b, i):
        au = self.app.audio
        r = self.tb["ramps"][i]
        self.ramp_flash[i] = 0.6
        au.play("levelup")
        name = "TOWER CLIMB!" if r["kind"] == "tower" else "FISH SLIDE!"
        self.score_at(1000, b.x, b.y - 10, "mint")
        if "ramp" in self.prog:
            self.prog["ramp"] += 1
        self.switch_hit()
        if self.stime - self.last_ramp < 5.0 and self.st["kind"] != "bonus":
            self.chain += 1
            self.stats["combo"] += 1
            if "combo" in self.prog:
                self.prog["combo"] += 1
            bonus = self.score_at(500 * min(4, self.chain))
            self.hype.banner("RAMP COMBO!", f"+{bonus}", color="orange", dur=1.1, scale=1, sound="combo")
        else:
            self.chain = 0
            self.floats.add(b.x, b.y - 18, name, "white")
        self.last_ramp = self.stime
        self.set_mood("happy", 1.2)
        if self.boss:
            ex, ey = r["path"][-1]
            self.boss.projs.append([float(ex), float(ey), 0.0, -120.0, "missile", self.ball_dmg() + 1, False])
            self.hype.banner("POUNCE!", color="orange", dur=0.8, scale=1)
            return
        if self.jackpot_lit:
            if self.st["kind"] == "bonus":
                self.score_at(1000, b.x, b.y - 18, "hotpink")
                self.hype.banner("PARTY POINTS!", color="hotpink", dur=0.8, scale=1)
                self.stats["jackpot"] += 1
            else:
                self.jackpot_lit = False
                self.jp_t = 5.0
                self.stats["jackpot"] += 1
                self.hype.jackpot(self.pts(8000 + 1000 * self.tier), "KITTEN JACKPOT!")

    def kitten_hit(self, i, x, y):
        if i >= len(self.kittens):
            return
        k = self.kittens.pop(i)
        if k[4]:                       # the golden kitten
            self.hype.jackpot(self.pts(25000), "GOLDEN KITTEN!")
            self.stats["jackpot"] += 1
            self.set_mood("wow", 2.0)
        else:
            self.app.audio.play("eat")
            self.score_at(1500, x, y - 10, "pink")
            self.hype.banner("RESCUED!", color="pink", dur=0.7, scale=1)
            self.set_mood("happy", 1.0)
        if "rescue" in self.prog:
            self.prog["rescue"] += 1
        self.parts.burst(x, y, 12, ("pink", "white", "yellow"), 60, 0.5)
        self.switch_hit()

    def update_kittens(self, dt):
        for k in self.kittens:
            k[5] -= dt
        self.kittens = [k for k in self.kittens if k[5] > 0 or not k[4]]
        if self.golden and self.stime > self.golden_t and self.tb["spots"]:
            self.golden = False
            x, y = random.choice(self.tb["spots"])
            self.kittens.append([float(x), float(y), 0, -1, True, 12.0])
            self.hype.banner("GOLDEN KITTEN!", "QUICK - BEFORE IT RUNS", rainbow=True, dur=1.4, sound="bonus")
        if "rescue" not in self.prog or self.prog["rescue"] >= dict(self.goals)["rescue"]:
            return
        self.kitten_cd -= dt
        if self.kitten_cd <= 0 and sum(1 for k in self.kittens if not k[4]) < 2:
            used = {k[3] for k in self.kittens}
            free = [i for i in range(len(self.tb["spots"])) if i not in used]
            if free:
                i = random.choice(free)
                x, y = self.tb["spots"][i]
                self.kittens.append([float(x), float(y), random.randint(0, 5), i, False, 0.0])
                self.app.audio.play("bubble")
            self.kitten_cd = 2.5

    def update_coins(self, dt):
        for c in self.coins:
            c[3] -= dt if c[3] > 0 else 0
            c[1] += math.sin(self.stime * 2 + c[0]) * 4 * dt
        self.coins = [c for c in self.coins if c[3] > 0]
        self.coin_cd -= dt
        if self.coin_cd <= 0 and len(self.coins) < 8:
            self.coin_cd = 0.45
            x = random.uniform(104, 216)
            y = random.uniform(48, 132)
            if not (x < 110 and y < 112):
                self.coins.append([x, y, random.random() < 0.06, 7.0])

    def stun_paw(self, side, dur, text):
        f = self.flippers[side]
        f.stun = dur
        f.pressed = False
        tx, ty = f.tip()
        self.floats.add((f.px + tx) / 2, f.py - 14, text, "red")
        self.app.audio.play("hurt")
        self.set_mood("hurt", 1.0)

    def boss_hit_fx(self, b):
        self.score_at(500, b.x, b.y - 10, "orange")
        self.switch_hit()
        self.set_mood("happy", 0.6)

    def boss_defeated(self):
        g = self.hype
        self.app.audio.play("bossdown")
        g.banner("BOSS DOWN!", self.boss.name, rainbow=True, dur=2.4, scale=2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(40, "coins")
        g.slowmo(0.3, 1.4)
        self.app.shake(6, 0.6)
        self.score_at(15000, self.boss.x, self.boss.y)
        self.set_mood("happy", 3.0)
        self.stage_clear(quiet=True)

    # ---------------------------------------------------------------- mission
    def check_mission(self):
        st = self.st
        if self.state != "play":
            return
        if st["kind"] == "normal":
            if all(self.prog[g] >= c for g, c in self.goals):
                self.stage_clear()
        elif st["kind"] == "bonus":
            if self.timer_on and self.time_left <= 0.05:
                self.stage_clear()

    def stage_clear(self, quiet=False):
        if self.state != "play":
            return
        self.state = "clear"
        self.state_t = 0.0
        self.queue = []
        if not quiet:
            self.app.audio.play("win")
            title = "BONUS OVER!" if self.st["kind"] == "bonus" else "MISSION CLEAR!"
            self.hype.banner(title, color="mint", dur=1.6)
            self.hype.shower(30, "confetti")
            self.hype.slowmo(0.3, 0.8)
            self.set_mood("happy", 2.5)
        for b in self.balls:
            self.parts.burst(b.x, b.y, 10, ("yellow", "white"), 60, 0.5)
        self.balls = []
        self.kittens = [k for k in self.kittens if not k[4]]
        self.app.audio.music(None)

    def begin_tally(self):
        st = self.st
        p = self.pts
        rows = []
        if st["kind"] == "normal":
            rows.append(("MISSION BONUS", p(3000 + 300 * self.tier)))
            if st["time"]:
                rows.append((f"TIME LEFT {int(self.time_left)}S", p(int(self.time_left) * 100)))
            rows.append((f"MEOW BONUS X{self.bonus_x}", p(1000 * self.bonus_x)))
            rows.append(("NO MISS", p(5000) if not self.missed else 0))
        elif st["kind"] == "boss":
            rows.append(("BOSS BONUS", p(10000 + 1000 * self.tier)))
            rows.append(("NO MISS", p(8000) if not self.missed else 0))
        else:
            rows.append((f"SWITCHES x{self.stats['switch']}", p(self.stats["switch"] * 10)))
            if st["bonus"] == "party":
                rows.append((f"PARTY SHOTS x{self.stats['jackpot']}", p(self.stats["jackpot"] * 1000)))
            else:
                rows.append((f"FISH COINS x{self.stats['coins']}", p(self.stats["coins"] * 100)))
                rows.append((f"RAINBOW FISH x{self.stats['rainbow']}", p(self.stats["rainbow"] * 1000)))
        rows.append((f"BEST COMBO {self.hype.best_combo}", p(min(self.hype.best_combo, 200) * 20)))
        self.tally = [[label, v, 0.0] for label, v in rows]
        self.tally_i = 0
        self.tally_wait = 0.0
        self.state = "tally"
        self.state_t = 0.0
        self.hype.best_combo = 0
        if st["kind"] != "bonus" and not self.missed:
            self.hype.banner("PURRFECT!", "NO BALL LOST", rainbow=True, dur=1.8, sound="fever")
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
        if self.n >= STAGES:
            self.state = "over"
            self.hype.banner("ALL CLEAR!!", "KIKI'S CAFE IS SAVED", rainbow=True, dur=5.0, sound="jackpot")
            self.hype.shower(120, "confetti")
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
    def render(self, s):
        t = self.t
        s.blit(self.bg, (0, 0))
        tb = self.tb
        st = self.st
        for i, (lx, ly) in enumerate(tb["lanes"]):
            A.draw_lane_letter(s, i, lx, self.lanes[i], t, i == self.skill)
        if tb["spinner"]:
            A.draw_spinner(s, tb["spinner"], self.spin_a, t)
        if tb["saucer"]:
            busy = any(b.state == "nap" for b in self.balls)
            A.draw_saucer(s, tb["saucer"][0], tb["saucer"][1], t, busy, self.lock_lit)
        for f in self.fish:
            A.draw_fish(s, f, t)
        for i, (x, y) in enumerate(tb["bumpers"]):
            A.draw_bumper(s, x, y, self.theme["bump"], self.bump_t[i], t, i)
        for k in self.kittens:
            A.draw_kitten(s, k[0], k[1], k[2], t, k[4])
        for c in self.coins:
            A.draw_coin_fish(s, c[0], c[1], t, c[2])
        if self.tail_on:
            pygame.draw.line(s, col("black"), (155, 182), (155, 191), 4)
            s.fill(col("white"), (154, 182, 2, 2))
        if self.save_t > 0 and (self.save_t > 2 or int(t * 8) % 2):
            s.blit(sprite("pp_bell"), (152, 192))
        for side, on in enumerate(self.kick):
            if on:
                x = 78 if side == 0 else 232
                s.fill(col("orange" if int(t * 4) % 2 else "yellow"), (x - 2, 196, 5, 3))
        if self.boss:
            self.boss.draw(s, t)
        for b in self.balls:
            if b.state in ("play", "nap") and not (b.state == "nap" and int(t * 6) % 2):
                A.draw_ball(s, b, t, self.hype.fever_on)
        for f in self.flippers:
            A.draw_flipper(s, f, t, self.hype.fever_on)
        self.draw_plunger(s, t)
        for i, r in enumerate(tb["ramps"]):
            lit = self.jackpot_lit or (self.boss is not None)
            c = "mint" if r["kind"] == "tower" else "sky"
            if self.ramp_flash[i] > 0 and int(t * 12) % 2:
                c = "white"
            A.draw_ramp(s, r, self.ramp_lens[i], t, c, lit)
        for b in self.balls:
            if b.state == "ramp":
                A.draw_ball(s, b, t, self.hype.fever_on)
        self.parts.draw(s)
        self.floats.draw(s)
        self.draw_hud(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "tally":
            self.draw_tally(s, t)
        if self.tilted and int(t * 4) % 2:
            draw_text(s, "TILT", 155, 100, "red", 3, align="center", outline="black", shadow=None)

    def draw_plunger(self, s, t):
        y = int(T.PLUNGE_Y + self.pull * 8)
        x = int(T.LANE_X)
        s.fill(col("gray"), (x - 1, y, 3, H - y))
        s.fill(col("red"), (x - 4, y, 9, 2))
        waiting = any(b.state == "play" and b.on_plunger() and b.auto < 0 for b in self.balls)
        if waiting and self.state == "play" and int(t * 3) % 2:
            for i in range(3):
                s.fill(col("yellow"), (x - 1, 150 + i * 6 - int(t * 12) % 6, 3, 2))

    def draw_hud(self, s, t):
        st = self.st
        # ---- left panel: score, stage, mission, MEOW
        draw_text(s, f"{self.score:08d}", 4, 3, "white", shadow=None)
        draw_text(s, f"HI {max(self.best, self.score):07d}", 4, 12, "gray", shadow=None)
        draw_text(s, f"STAGE {self.n}", 4, 24, "yellow", shadow=None)
        y = 35
        if st["kind"] == "normal":
            draw_text(s, "MISSION", 4, y, "lavender", shadow=None)
            y += 10
            for g, c in self.goals:
                have = min(self.prog[g], c)
                word = T.GOALS[g][0]
                done = have >= c
                if g == "score":
                    txt = f"{word} {c // 1000}K"
                elif g == "multi":
                    txt = word
                else:
                    txt = f"{word} {have}/{c}"
                draw_text(s, txt, 4, y, "lime" if done else "white", shadow=None)
                s.fill(col("darkgray"), (4, y + 8, 58, 2))
                s.fill(col("lime" if done else "orange"), (4, y + 8, int(58 * have / max(1, c)), 2))
                y += 13
        elif st["kind"] == "boss":
            draw_text(s, "BOSS FIGHT", 4, y, "red", shadow=None)
            draw_text(s, self.boss.name if self.boss else "", 4, y + 10, "white", shadow=None)
            draw_text(s, "HIT IT WITH", 4, y + 24, "gray", shadow=None)
            draw_text(s, "THE BELL!", 4, y + 33, "gray", shadow=None)
            y += 46
        else:
            draw_text(s, "BONUS!", 4, y, rainbow(0, t), shadow=None)
            draw_text(s, "SCORE ALL" if st["bonus"] == "party" else "GRAB THE", 4, y + 10, "white", shadow=None)
            draw_text(s, "YOU CAN!" if st["bonus"] == "party" else "GOLD FISH!", 4, y + 19, "white", shadow=None)
            y += 32
        if st["time"]:
            secs = int(math.ceil(self.time_left))
            c = "yellow" if secs > 10 or int(t * 6) % 2 else "red"
            draw_text(s, f"TIME {secs}", 4, y + 2, c, shadow=None)
        # MEOW letters
        for i, ch in enumerate("MEOW"):
            lit = self.lanes[i]
            c = ("yellow" if int(t * 4 + i) % 3 else "white") if lit else "darkgray"
            draw_text(s, ch, 6 + i * 14, 112, c, 2, shadow="black")
        draw_text(s, f"BONUS X{self.bonus_x}", 4, 130, "peach", shadow=None)
        y = 142
        if self.multiball:
            draw_text(s, "MULTIBALL", 4, y, rainbow(1, t), shadow=None)
            y += 10
        elif self.lock_lit:
            draw_text(s, "LOCK LIT!", 4, y, "pink" if int(t * 4) % 2 else "lavender", shadow=None)
            y += 10
        elif self.locks:
            draw_text(s, f"LOCKED {self.locks}/{self.locks_needed()}", 4, y, "pink", shadow=None)
            y += 10
        if self.jackpot_lit and int(t * 4) % 2:
            draw_text(s, "JACKPOT!", 4, y, "yellow", shadow=None)
        # ---- right panel: Kiki, balls, fever, status
        panel(s, (256, 2, 62, 58), fill="night", border=self.theme["wall"], radius=3, shadow=False)
        lx, ly = 0.0, 0.0
        mood = self.mood
        tgt = None
        for b in self.balls:
            if b.state in ("play", "ramp") and (tgt is None or b.y > tgt.y):
                tgt = b
        if tgt is not None:
            lx = max(-1.0, min(1.0, (tgt.x - 160) / 70))
            ly = max(-1.0, min(1.0, (tgt.y - 90) / 70))
            if mood == "idle" and tgt.y > 160 and abs(tgt.x - T.CX) < 16 and tgt.vy > 60:
                mood = "worried"
        s.set_clip((257, 3, 60, 56))
        A.draw_kiki(s, RIGHT_PANEL, 28, mood, t, lx, ly, blink=int(t * 1.3) % 5 == 0 and mood == "idle")
        s.set_clip(None)
        draw_text(s, "KIKI", 260, 5, "white", shadow="black")
        draw_text(s, "BALLS", 258, 64, "lavender", shadow=None)
        for i in range(min(self.lives, 7)):
            s.blit(sprite("pp_bell"), (258 + i * 8, 73))
        if self.lives > 7:
            draw_text(s, f"+{self.lives - 7}", 300, 73, "yellow", shadow=None)
        draw_text(s, "FEVER", 258, 84, "orange", shadow=None)
        x0, y0 = 258, 93
        s.fill(col("darkgray"), (x0, y0, 58, 3))
        if self.hype.fever_on:
            for i in range(58):
                s.fill(col(rainbow(i // 6, t)), (x0 + i, y0, 1, 3))
        else:
            s.fill(col("orange"), (x0, y0, int(58 * self.hype.fever), 3))
        y = 101
        if self.save_t > 0 and (self.save_t > 2 or int(t * 8) % 2):
            draw_text(s, f"SAVE {int(math.ceil(self.save_t))}", 258, y, "mint", shadow=None)
            y += 10
        if self.kick[0] or self.kick[1]:
            draw_text(s, "KICKBACK", 258, y, "orange", shadow=None)
            y += 10
        if self.tail_on:
            draw_text(s, "TAIL POST", 258, y, "lavender", shadow=None)
            y += 10
        if self.tilt > 0.55 and not self.tilted:
            draw_text(s, "DANGER", 258, y, "red" if int(t * 8) % 2 else "orange", shadow=None)
            y += 10
        if self.tilted:
            draw_text(s, "TILT!", 258, y, "red", shadow=None)
        # plunger hint / power
        waiting = any(b.state == "play" and b.on_plunger() and b.auto < 0 for b in self.balls)
        if waiting and self.state == "play":
            s.fill(col("darkgray"), (306, 150, 6, 40))
            h = int(40 * self.pull)
            s.fill(col("red" if self.pull > 0.9 else "yellow"), (306, 190 - h, 6, h))
            if int(t * 2) % 2 or self.pull > 0:
                draw_text(s, "PULL", 258, 162, "yellow", shadow=None)
                draw_text(s, "AND", 258, 171, "yellow", shadow=None)
                draw_text(s, "LET GO", 258, 180, "yellow", shadow=None)
        # boss health
        if self.boss and self.boss.state in ("fight", "idle", "enter"):
            boss_bar(s, self.boss.name, self.boss.hp, self.boss.maxhp, t, x=T.TX0 + 2, w=T.TX1 - T.TX0 - 4, y=1)

    def draw_intro(self, s, t):
        st = self.st
        k = st["kind"]
        cx = 160
        if k == "boss":
            if int(t * 4) % 2:
                for x in range(T.TX0, T.TX1, 20):
                    pygame.draw.polygon(s, col("red"), [(x, 108), (x + 10, 108), (x + 20, 116), (x + 10, 116)])
                    pygame.draw.polygon(s, col("red"), [(x, 152), (x + 10, 152), (x + 20, 160), (x + 10, 160)])
            panel(s, (T.TX0 + 4, 118, T.TX1 - T.TX0 - 8, 32), fill="black", border="red")
            draw_text(s, "WARNING!!", cx, 122, "red" if int(t * 6) % 2 else "yellow", 2, align="center",
                      outline="ink")
            draw_text(s, f"{st['boss']['name']} - {st['boss']['title']}", cx, 139, "white", align="center", shadow=None)
            return
        goals = st["goals"]
        h = 44 + 9 * max(1, len(goals)) + (10 if st["new"] else 0) + (9 if st["time"] else 0)
        y0 = 70
        panel(s, (T.TX0 + 2, y0, T.TX1 - T.TX0 - 4, h), fill="ink", border="yellow" if k == "bonus" else "peach")
        if k == "bonus":
            title = "BONUS STAGE"
            for i, ch in enumerate(title):
                draw_text(s, ch, cx - text_width(title, 2) // 2 + i * 12, y0 + 6 + int(math.sin(t * 8 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            draw_text(s, st["name"], cx, y0 + 26, "yellow", align="center")
            sub = "KITTEN PARTY - EVERYTHING X2!" if st["bonus"] == "party" else "GRAB THE GOLD FISH COINS!"
            draw_text(s, sub, cx, y0 + 37, "white", align="center", shadow=None)
            draw_text(s, f"{st['time']} SECONDS, NO DRAINS!", cx, y0 + 47, "mint", align="center", shadow=None)
            return
        draw_text(s, f"STAGE {self.n}", cx, y0 + 6, "yellow", 2, align="center", outline="ink", shadow=None)
        draw_text(s, f"{self.tb['name']} - {st['name']}", cx, y0 + 24, "lavender", align="center", shadow=None)
        y = y0 + 36
        for g, c in goals:
            txt = T.GOALS[g][1].format(n=f"{c // 1000}K" if g == "score" else c)
            draw_text(s, txt, cx, y, "white", align="center", shadow=None)
            y += 9
        if st["time"]:
            draw_text(s, f"IN {st['time']} SECONDS!", cx, y, "orange", align="center", shadow=None)
            y += 9
        if st["new"]:
            draw_text(s, st["new"], cx, y + 2, "mint" if int(t * 4) % 2 else "lime", align="center", shadow=None)

    def draw_tally(self, s, t):
        rows = self.tally
        h = 34 + len(rows) * 11
        y0 = 76
        panel(s, (T.TX0 + 6, y0, T.TX1 - T.TX0 - 12, h), fill="ink", border="mint")
        head = {"boss": "BOSS CLEAR!", "bonus": "BONUS OVER!"}.get(self.st["kind"], f"STAGE {self.n} CLEAR!")
        draw_text(s, head, 160, y0 + 6, "mint", align="center")
        for i, (label, v, shown) in enumerate(rows):
            if i > self.tally_i:
                break
            y = y0 + 20 + i * 11
            draw_text(s, label, T.TX0 + 12, y, "white" if v else "gray", shadow=None)
            draw_text(s, f"{int(shown)}", T.TX1 - 12, y, "yellow" if v else "darkgray", align="right", shadow=None)
        if self.tally_i >= len(rows) and int(t * 3) % 2:
            draw_text(s, "PRESS A", 160, y0 + h - 11, "lavender", align="center", shadow=None)


# ----------------------------------------------------------------------------- bots and the carousel
def autopilot(sc, frame):
    """A decent flipper bot (smoke tests and README GIFs)."""
    keys = set()
    if sc.overlay is not None:
        if frame % 20 == 0:
            keys.add("right" if frame % 40 else "a")
        return keys
    if sc.state in ("intro", "tally"):
        if frame % 30 == 0:
            keys.add("a")
        return keys
    if sc.state != "play":
        return keys
    for b in sc.balls:
        if b.state == "play" and b.on_plunger() and b.auto < 0:
            if (frame // 50) % 2 == 0:
                keys.add("down")
    bot = sc.__dict__.setdefault("_bot", [0, 0, 0, 0])      # hold frames L, R, cooldown L, R
    for side, f in enumerate(sc.flippers):
        tx, _ = f.tip()
        x0, x1 = min(f.px, tx) - 4, max(f.px, tx) + 5
        if bot[side] > 0:
            bot[side] -= 1
            keys.add("left" if side == 0 else "right")
            if bot[side] == 0:
                bot[2 + side] = 10
            continue
        if bot[2 + side] > 0:
            bot[2 + side] -= 1
            continue
        for b in sc.balls:
            if b.state != "play" or b.in_lane():
                continue
            if x0 <= b.x <= x1 and f.py - 16 <= b.y <= f.py + 12 and b.vy > -40:
                # aim a little: wait for the ball to roll towards the tip before flipping
                along = (b.x - f.px) * f.side / f.len
                if along > 0.35 or b.vy > 160 or b.y > f.py + 4:
                    bot[side] = 9
                    keys.add("left" if side == 0 else "right")
    return keys


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys."""
    return lambda frame: autopilot(scene, frame)


def preview(s, t):
    w, h = s.get_size()
    s.fill(col("choco"))
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            if (x // 8 + y // 8) % 2:
                s.fill(col("brown"), (x, y, 8, 8))
    cx = w // 2
    # two cat bumpers and the paws
    A.draw_bumper(s, cx - 22, 24, "orange", 0.1 if int(t * 3) % 3 == 0 else 0, t, 0)
    A.draw_bumper(s, cx + 22, 24, "pink", 0.1 if int(t * 3) % 3 == 1 else 0, t, 1)
    for i in range(3):
        s.blit(sprite("pp_fish"), (cx - 17 + i * 12, 40))
    paws = []
    for side in (1, -1):
        f = Flipper(cx - side * 22, h - 14, side, 17)
        up = (int(t * 2) % 2 == 0) == (side == 1)
        f.a = -0.4 if up else 0.5
        paws.append(f)
        A.draw_flipper(s, f, t)
    bx = cx + math.sin(t * 2.3) * 26
    by = h - 22 - abs(math.sin(t * 3.1)) * 36
    s.blit(sprite("pp_bell"), (int(bx) - 3, int(by) - 3))
    A.draw_kiki(s, w - 13, 18, "happy" if int(t) % 3 == 0 else "idle", t, math.sin(t * 2.3), 0.5)
    draw_text(s, "MEOW", 4, 3, rainbow(0, t), shadow="black")
