"""SOAP HOP - a single-screen bubble platformer starring Momo the mochi bunny (original game).

A 200-stage campaign: stages are remixed from curated templates (soap_hop_data.py), every 10th stage is a
boss (soap_hop_boss.py), every x5 a bonus stage, and upgrades are picked after bosses and bonus stages.
The iOS port (ios/MochiArcade/Games/SoapHop*.swift) mirrors this file and plays the same exported stages.
"""
import math
import random

import pygame

from mochi_arcade import cute, music
from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow, tier
from mochi_arcade.games import soap_hop_art as art
from mochi_arcade.games import soap_hop_data as data
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.games.soap_hop_boss import Boss
from mochi_arcade.games.soap_hop_data import LEVELS, THEMES, build  # noqa: F401  (gen_data / smoke test)
from mochi_arcade.gfx import H, W, bubble, col, draw_text, lerp_col, panel, sprite

T = 8
COLS, ROWS = 40, 23
TOP = 12
FIELD_H = ROWS * T
FLOOR_Y = TOP + 21 * T
GRAV = 620.0
JUMP = 255.0
RUN = 74.0
FAST_PHASE = 0.32
LETTERS = "MOCHI"
POWERS = ("soda", "clock", "gem", "shield")

# "Grand Drain Gallop" - an extra (original) song for the final tier, stages 191-200
music.SONGS.update({
    "soap_final": {"bpm": 150, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "D5:8 A5:8 F5:8 A5:8 D6:4 C6:8 A5:8  A#4:8 F5:8 D5:8 F5:8 A#5:4 A5:4 "
            "G4:8 D5:8 A#4:8 D5:8 G5:8 A5:8 A#5:4  A4:8 C#5:8 E5:8 A5:8 G5:4 E5:4 "
            "F5:8 E5:8 D5:8 E5:8 F5:4 A5:4  G5:8 F5:8 E5:8 F5:8 G5:4 A#5:4 "
            "A5:8 G5:8 F5:8 E5:8 D5:4 F5:4  E5:8 C#5:8 A4:8 C#5:8 D5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": music._bass(["D", "A#", "G", "A"] * 2)},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, music.ROCK)},
    ]},
})

UPGRADES = [
    Upgrade("range", "BIG BLOW", "BUBBLES FLY|FARTHER", "sky", art.icon_range, 3),
    Upgrade("rate", "RAPID PUFF", "BLOW FASTER|+2 BUBBLES|AT ONCE", "mint", art.icon_rate, 3),
    Upgrade("trap", "STICKY SOAP", "BIGGER BUBBLES|HOLD GRUMPS|LONGER", "lavender", art.icon_trap, 3),
    Upgrade("speed", "QUICK FEET", "RUN FASTER", "lime", art.icon_speed, 3),
    Upgrade("jump", "SPRING EARS", "HIGHER JUMP|LV2: DOUBLE|JUMP IN AIR", "yellow", art.icon_jump, 3),
    Upgrade("heart", "EXTRA HEART", "+1 LIFE|RIGHT NOW", "pink", art.icon_heart, 3),
    Upgrade("chain", "CHAIN CHARM", "WIDER CHAINS|+50% CHAIN|POINTS", "orange", art.icon_chain, 3),
    Upgrade("magnet", "SNACK MAGNET", "PULLS SNACKS|AND ITEMS|TO YOU", "red", art.icon_magnet, 3),
    Upgrade("shield", "BUBBLE SHIELD", "BLOCKS 1 HIT|EVERY STAGE|LV2: REFILLS", "teal", art.icon_shield, 2),
    Upgrade("twin", "TWIN BLOW", "A 2ND BUBBLE|FLIES UPWARD", "hotpink", art.icon_twin, 1),
]

_export = None


def __getattr__(name):
    """EXPORT is built lazily (generating 200 stages takes a moment): gen_data reads it, Swift plays it."""
    if name == "EXPORT":
        return export()
    raise AttributeError(name)


def export():
    global _export
    if _export is None:
        _export = data.export()
    return _export


class Body:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = float(x), float(y), w, h
        self.vx = self.vy = 0.0
        self.on_ground = False

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)


class Enemy(Body):
    def __init__(self, kind, x, y, speed, angry=False):
        super().__init__(x, y, 12, 13)
        self.kind, self.base = kind, speed
        self.face = random.choice((-1, 1))
        self.vdir = random.choice((-1, 1))
        self.angry = angry
        self.think = random.uniform(0.5, 1.5)
        self.golden = False
        self.lid = kind == "s"
        self.mode, self.mode_t = "walk", 0.0
        self.cool = random.uniform(1.5, 3.0)
        self.swell = 0.0
        self.stun = 0.0
        self.minion = False


class Bubble:
    def __init__(self, x, y, vx, vy, life, kind="normal"):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.age = 0.0
        self.life = life
        self.enemy = None
        self.seed = random.uniform(0, 6.28)
        self.pop_in = None
        self.dead = False
        self.kind = kind          # normal | letter | party
        self.sub = 0              # letter index / snack kind
        self.value = 0


class Item(Body):
    def __init__(self, x, y, kind, sub=0, value=0):
        super().__init__(x, y, 8, 8)
        self.kind, self.sub, self.value = kind, sub, value
        self.vx = random.uniform(-40, 40)
        self.vy = -140
        self.life = 9.0
        self.rain = False


class Shot:
    def __init__(self, kind, x, y, vx, vy):
        self.kind, self.x, self.y, self.vx, self.vy = kind, x, y, vx, vy
        self.age = 0.0
        self.dead = False
        self.r = {"dust": 3, "drop": 3, "water": 2}.get(kind, 0)
        self.grav = {"drop": 260, "water": 420}.get(kind, 0)
        self.warn = {"bolt": 0.75, "mark": 0.85}.get(kind, 0.0)


class SoapHop(GameScene):
    music = "soap"

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES.get(d, 3)
        self.spd = SPEED.get(d, 1.0)
        self.trap_base = {"easy": 9.0, "normal": 7.0, "hard": 5.0}.get(d, 7.0)
        self.stage = max(1, min(STAGES, int(opt.get("start", opt.get("stage", 1)))))
        self.ups = {u.id: 0 for u in UPGRADES}
        self.letters = [False] * 5
        self.next_extra = 50000
        self.picks, self.after_picks, self.pick_title = 0, "", "POWER UP!"
        self.was_fever = False
        self.tally, self.tally_i, self.tally_t, self.tally_total = [], 0, 0.0, 0
        self.load_stage()
        head = min(5, tier(self.stage))
        if head:          # starting from a checkpoint: catch up on the upgrades a full run would have
            self.picks, self.after_picks, self.pick_title = head, "intro", "HEAD START!"
            self.state = "picks"

    @property
    def fruits(self):
        """Old name of the item list (used by the GIF autoplay bot in packaging/record_gifs.py)."""
        return self.items

    # ---------------------------------------------------------------- stage setup
    def load_stage(self):
        sd = export()["stages"][self.stage - 1]
        self.sd = sd
        self.kind = sd["k"]
        self.tier = tier(self.stage)
        self.theme = data.TIER_THEMES[sd["th"]]
        self.map = [data.unrle(row) for row in sd["map"]]
        self.level_name = sd["nm"]
        self.mods = list(sd["mods"])
        self.wind = sd.get("wind", 0)
        self.enemies, self.bubbles, self.items, self.shots = [], [], [], []
        self.espeed = self.spd * (1 + 0.025 * self.tier)
        for kind, c, r, angry in sd["en"]:
            self.enemies.append(Enemy(kind, c * T - 2, TOP + r * T + T - 13, self.espeed, angry == 1))
        if self.kind == "normal" and self.hype.lucky(0.03):      # rare golden grump -> treasure chest
            walkers = [e for e in self.enemies if e.kind in "gbzp"]
            if walkers:
                random.choice(walkers).golden = True
        c, r = sd["p"]
        self.start = (c * T, TOP + r * T + T - 14)
        self.player = Body(*self.start, 12, 14)
        self.face = 1
        self.inv = 2.0
        self.shoot_cd = 0.0
        self.coyote = self.jump_buf = 0.0
        self.air_jumps = 0
        self.bounces = 0
        self.shield = self.ups["shield"] > 0
        self.shield_t = 0.0
        self.level_t = 0.0
        self.hurry = False
        self.chain, self.chain_t, self.best_chain = 0, 0.0, 0
        self.missed = False
        self.snacks_out = self.snacks_got = 0
        self.freeze_t = 0.0
        self.boss = Boss(sd) if self.kind == "boss" else None
        self.letter_t = -1.0
        if self.kind == "normal" and not all(self.letters) and self.hype.lucky(0.55):
            self.letter_t = random.uniform(5, 15)
        self.bonus_n = self.bonus_got = 0
        self.spawn_t = 0.0
        self.time_left = float(sd.get("time", 20))
        self.field = self.render_field()
        self.reached(self.stage)
        if self.kind == "boss":
            self.state = "warning"
            self.music = "boss"
            self.app.audio.play("warning")
        else:
            self.state = "intro"
            self.music = "bonus" if self.kind == "bonus" else ("soap_final" if self.tier >= 19 else "soap")
            self.app.audio.play("stage")
            if self.kind == "bonus":
                self.hype.banner("BONUS STAGE!", "POP EVERY BUBBLE!" if sd["bt"] == "party" else "CATCH THE SNACK RAIN!",
                                 rainbow=True, dur=2.0)
        self.intro_state = self.state
        self.state_t = 0.0
        self.was_fever = False          # a FEVER still running picks its song again on the next tick
        self.app.audio.music(self.music)

    def render_field(self):
        _, blk, blk_d, plat, plat_d = self.theme[:5]
        f = pygame.Surface((W, FIELD_H), pygame.SRCALPHA)
        for r, row in enumerate(self.map):
            for c, ch in enumerate(row):
                x, y = c * T, r * T
                if ch == "#":
                    f.fill(col(blk_d), (x, y, T, T))
                    f.fill(col(blk), (x, y, T - 1, T - 1))
                    if (r + c) % 2 == 0:
                        f.fill(col("white"), (x + 2, y + 2, 1, 1))
                elif ch == "=":
                    f.fill(col(plat_d), (x, y + 1, T, T - 3))
                    f.fill(col(plat), (x, y, T, 3))
                    f.fill(col("white"), (x + 1, y, 3, 1))
        return f

    def cell(self, px, py):
        c, r = int(px // T), math.floor((py - TOP) / T)
        if r < 0 or r >= ROWS:
            return "."
        if c < 0 or c >= COLS:
            return "#"
        return self.map[r][c]

    # ---------------------------------------------------------------- upgrades
    def run_speed(self):
        return RUN * (1 + 0.12 * self.ups["speed"])

    def jump_v(self):
        lv = self.ups["jump"]
        v = JUMP * (1.06 if lv >= 1 else 1.0) * (1.05 if lv >= 3 else 1.0)
        return v * (0.82 if "floaty" in self.mods else 1.0)

    def trap_time(self):
        return max(3.5, self.trap_base - 0.08 * self.tier) + 1.5 * self.ups["trap"]

    def took(self, uid):
        if uid is None:
            self.add(10000)
            self.hype.banner("ALL MAXED!", "+10000", color="yellow", dur=1.4)
            return
        self.ups[uid] += 1
        if uid == "heart":
            self.lives += 1
        if uid == "shield":
            self.shield = True
        name = next(u.name for u in UPGRADES if u.id == uid)
        self.hype.banner(name, f"LEVEL {self.ups[uid]}", color="mint", dur=1.1, scale=1)

    # ---------------------------------------------------------------- scene API used by the boss
    def shoot(self, kind, x, y, vx, vy):
        self.shots.append(Shot(kind, x, y, vx, vy))

    def minion_count(self):
        return sum(1 for e in self.enemies if e.minion) + sum(1 for b in self.bubbles if b.enemy is not None)

    def spawn_minion(self, kind, x, y):
        e = Enemy(kind, x - 6, y - 6, self.espeed)
        e.minion = True
        self.enemies.append(e)
        self.parts.burst(x, y, 10, ("gray", "white"), 50, 0.4)

    def boss_defeated(self):
        self.state, self.state_t = "bossdown", 0.0
        h = self.hype
        h.banners = []
        h.slowmo(0.3, 1.6)
        h.flash("white", 0.4)
        h.banner("BOSS DOWN!!", f"{self.boss.name} IS CLEAN!", rainbow=True, dur=2.6, sound="bossdown")
        self.app.shake(6, 0.8)
        self.add(10000 + 5000 * self.tier, self.boss.x, self.boss.y - 24, "yellow")
        for s in self.shots:
            s.dead = True
        for e in self.enemies:
            self.parts.burst(e.cx, e.cy, 10, ("white", "gray"), 60, 0.5)
            self.drop_snack(e.cx - 4, e.cy - 4)
        self.enemies = []
        for b in self.bubbles:
            if b.enemy is not None:
                b.dead = True
                self.drop_snack(b.x - 4, b.y - 4)

    def boss_burst(self):
        b = self.boss
        h = self.hype
        h.shower(70, "confetti")
        h.shower(40, "coins")
        h.flash("yellow", 0.3)
        self.app.audio.play("explode")
        self.app.shake(5, 0.5)
        self.parts.burst(b.x, b.y, 50, ("white", "yellow", "pink", "sky", "lavender"), 140, 1.1, size=2)
        for i in range(12):
            it = Item(b.x - 4, b.y - 4, "snack", (self.theme[8] + i) % 8, 300 + 50 * self.tier)
            it.vx = math.cos(i * math.tau / 12) * 90
            it.vy = -180 - (i % 3) * 40
            self.items.append(it)
            self.snacks_out += 1

    # ---------------------------------------------------------------- physics
    def move(self, b, dt, grav=GRAV):
        if grav:
            b.vy = min(b.vy + grav * dt, 270)
        hit_wall = False
        b.x += b.vx * dt
        for yy in (b.y + 1, b.y + b.h / 2, b.y + b.h - 1):
            if b.vx > 0 and self.cell(b.x + b.w, yy) == "#":
                b.x = (int((b.x + b.w) // T)) * T - b.w - 0.01
                hit_wall = True
            elif b.vx < 0 and self.cell(b.x, yy) == "#":
                b.x = (int(b.x // T) + 1) * T + 0.01
                hit_wall = True
        prev_bottom = b.y + b.h
        b.y += b.vy * dt
        b.on_ground = False
        xs = (b.x + 1, b.x + b.w / 2, b.x + b.w - 1)
        if b.vy >= 0:
            bottom = b.y + b.h
            for xx in xs:
                ch = self.cell(xx, bottom)
                row_top = TOP + math.floor((bottom - TOP) / T) * T
                if ch == "#" or (ch == "=" and prev_bottom <= row_top + 1):
                    b.y = row_top - b.h
                    b.vy = 0
                    b.on_ground = True
                    break
        else:
            for xx in xs:
                if self.cell(xx, b.y) == "#":
                    b.y = TOP + (math.floor((b.y - TOP) / T) + 1) * T
                    b.vy = 0
                    break
        if b.y > TOP + FIELD_H:
            b.y -= FIELD_H
        elif b.y + b.h < TOP:
            b.y += FIELD_H
        return hit_wall

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        st = self.state
        au = self.app.audio
        if st == "picks":
            if self.picks > 0:
                self.picks -= 1
                self.pick_upgrade(UPGRADES, self.ups, self.took, self.pick_title)
            elif self.after_picks == "next":
                self.next_stage()
            else:
                self.state, self.state_t = self.intro_state, 0.0
            return
        if st == "tally":
            self.update_tally(dt)
            return
        if st == "won":
            return
        if st == "intro" and self.state_t > 1.9:
            self.state, self.state_t = "play", 0.0
        elif st == "warning" and self.state_t > 2.8:
            self.state, self.state_t = "play", 0.0
            self.inv = max(self.inv, 1.0)
        st = self.state
        if st in ("intro", "warning", "play", "clear", "bossdown", "timeup"):
            self.update_player(dt)
        if st == "dead" and self.state_t > 1.3:
            if self.lives <= 0:
                self.state = "over"
                self.end_game(False, f"STAGE {self.stage}")
                return
            self.player = Body(*self.start, 12, 14)
            self.inv = 2.5
            self.state, self.state_t = "play", 0.0
        if st == "play":
            self.level_t += dt
            if self.kind == "normal" and self.level_t > self.sd["par"] and not self.hurry:
                self.hurry = True
                self.hype.banner("HURRY UP!", "THE GRUMPS ARE FURIOUS", color="red", dur=1.3, sound="warning")
                for e in self.enemies:
                    e.angry = True
            if 0 <= self.letter_t <= self.level_t:
                self.letter_t = -1.0
                self.spawn_letter()
        if st not in ("intro", "warning"):
            self.update_enemies(dt)
        self.update_bubbles(dt)
        self.update_items(dt)
        self.update_shots(dt)
        if self.boss is not None:
            self.boss.update(self, dt)
        self.chain_t -= dt
        self.freeze_t -= dt
        if self.shield_t > 0:
            self.shield_t -= dt
            if self.shield_t <= 0 and self.ups["shield"] >= 2:
                self.shield = True
                au.play("powerup")
        if self.kind == "bonus":
            self.update_bonus(dt)
        if st == "play" and self.kind == "normal" and not self.enemies and not any(b.enemy for b in self.bubbles):
            self.stage_clear()
        if st == "bossdown" and self.state_t > 3.8:
            self.state, self.state_t = "clear", 0.0
        if st == "timeup" and self.state_t > 1.6:
            self.start_tally()
        if st == "clear" and self.state_t > 2.6:
            self.start_tally()
        self.check_extra()
        fever = self.hype.fever_on
        if fever != self.was_fever and self.kind == "normal":
            au.music("fever" if fever else self.music)
        self.was_fever = fever

    def check_extra(self):
        while self.score >= self.next_extra:
            self.lives += 1
            self.next_extra = 150000 if self.next_extra < 150000 else self.next_extra + 200000
            self.hype.banner("1UP!", "EXTRA LIFE", color="pink", dur=1.4, sound="extra")
            self.hype.shower(16, "hearts")

    def stage_clear(self):
        self.state, self.state_t = "clear", 0.0
        h = self.hype
        if self.chain_t > 0 and self.chain >= 3:
            h.banner("CLEAN SWEEP!!", "+5000", rainbow=True, dur=1.8, sound="win")
            h.shower(50, "confetti")
            self.add(5000)
        else:
            h.banner("SPARKLING CLEAN!", "STAGE CLEAR", color="mint", dur=1.6, sound="levelup")

    def next_stage(self):
        if self.stage >= STAGES:
            self.state = "won"
            self.hype.banner("ALL CLEAN!!", "200 STAGES SPARKLING", rainbow=True, dur=3.0, sound="win")
            self.hype.shower(120, "confetti")
            self.end_game(True, "ALL 200 STAGES CLEAN!", delay=3.5)
            return
        self.stage += 1
        self.load_stage()

    def update_player(self, dt):
        p = self.player
        inp, au = self.app.input, self.app.audio
        self.inv = max(0.0, self.inv - dt)
        self.shoot_cd -= dt
        move = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        target = move * self.run_speed()
        if "slick" in self.mods:
            p.vx += (target - p.vx) * min(1.0, dt * 3.5)
        else:
            p.vx = target
        if move:
            self.face = move
        if p.on_ground:
            self.coyote = 0.09
            self.air_jumps = 1 if self.ups["jump"] >= 2 else 0
            self.bounces = 0
        else:
            self.coyote -= dt
        self.jump_buf = 0.12 if inp.hit("a") else self.jump_buf - dt
        if self.jump_buf > 0 and self.coyote > 0:
            p.vy = -self.jump_v()
            self.jump_buf = self.coyote = 0
            au.play("jump")
        elif inp.hit("a") and self.coyote <= 0 and self.air_jumps > 0:
            self.air_jumps -= 1
            self.jump_buf = 0
            p.vy = -self.jump_v() * (0.85 if self.ups["jump"] < 3 else 0.95)
            au.play("jump")
            self.parts.burst(p.cx, p.y + p.h, 8, ("white", "sky"), 40, 0.3)
        if p.vy < 0 and not inp.down("a"):
            p.vy *= 0.85 ** (dt * 60)
        self.move(p, dt, GRAV * (0.62 if "floaty" in self.mods else 1.0))
        mine = sum(1 for b in self.bubbles if b.kind == "normal" and b.enemy is None)
        if inp.hit("b") and self.shoot_cd <= 0 and mine < 7 + 2 * self.ups["rate"]:
            self.blow()

    def blow(self):
        p = self.player
        self.shoot_cd = max(0.12, 0.28 - 0.055 * self.ups["rate"])
        sp = 230 * (1 + 0.22 * self.ups["range"])
        self.bubbles.append(Bubble(p.cx + self.face * 6, p.cy - 1, self.face * sp, 0.0, 6.5))
        if self.ups["twin"]:
            self.bubbles.append(Bubble(p.cx + self.face * 4, p.cy - 4, self.face * sp * 0.7, -sp * 0.6, 6.5))
        self.app.audio.play("bubble")

    def spawn_letter(self):
        left = [i for i in range(5) if not self.letters[i]]
        if not left:
            return
        b = Bubble(random.uniform(T * 4, W - T * 4), FLOOR_Y - 10, 0.0, 0.0, 16.0, "letter")
        b.age = FAST_PHASE
        b.sub = random.choice(left)
        self.bubbles.append(b)
        self.app.audio.play("bonus")

    # ---------------------------------------------------------------- enemies
    def update_enemies(self, dt):
        p = self.player
        for e in list(self.enemies):
            sp = e.base * (1.6 if e.angry else 1.0)
            if self.freeze_t > 0:
                if e.kind not in "fw":
                    e.vx = 0
                    self.move(e, dt)
                if self.state == "play" and e.rect().inflate(-2, -2).colliderect(p.rect()):
                    self.defeat_frozen(e)
                continue
            if e.stun > 0:
                e.stun -= dt
                e.vx = 0
                self.move(e, dt)
                continue
            k = e.kind
            if k in "gs":
                self.walker(e, dt, sp * (0.8 if k == "s" else 1.0))
            elif k == "b":
                self.boing(e, dt, sp)
            elif k == "z":
                self.zoomy(e, dt, sp)
            elif k == "p":
                self.sneezy(e, dt, sp)
            elif k == "w":
                d = max(1.0, math.hypot(p.cx - e.cx, p.cy - e.cy))
                e.x += (p.cx - e.cx) / d * 18 * sp * dt
                e.y += (p.cy - e.cy) / d * 18 * sp * dt + math.sin(self.t * 3 + e.think) * 10 * dt
                e.face = 1 if p.cx > e.cx else -1
                e.x = max(T * 2, min(W - T * 2 - e.w, e.x))
                e.y = max(TOP + 2, min(FLOOR_Y - e.h, e.y))
            else:
                e.vx = e.face * 30 * sp
                e.vy = e.vdir * 22 * sp
                nx, ny = e.x + e.vx * dt, e.y + e.vy * dt
                if self.cell(nx + (e.w if e.vx > 0 else 0), e.cy) == "#":
                    e.face *= -1
                else:
                    e.x = nx
                if self.cell(e.cx, ny + (e.h if e.vy > 0 else 0)) == "#" or ny < TOP + 2 or ny + e.h > TOP + FIELD_H - 2:
                    e.vdir *= -1
                else:
                    e.y = ny
            if self.state == "play" and self.inv <= 0 and e.rect().inflate(-3, -3).colliderect(p.rect()):
                self.hurt()

    def walker(self, e, dt, sp):
        p = self.player
        e.vx = e.face * 32 * sp
        if self.move(e, dt):
            e.face *= -1
        if e.on_ground:
            ahead = self.cell(e.cx + e.face * 8, e.y + e.h + 2)
            e.think -= dt
            if ahead == "." and random.random() < 0.5 * dt * 10:
                e.face *= -1
            if e.think <= 0:
                e.think = random.uniform(0.8, 2.0)
                if p.y + p.h < e.y - 4 and random.random() < 0.55:
                    e.vy = -JUMP * 0.95
                elif random.random() < 0.25:
                    e.face = 1 if p.cx > e.cx else -1

    def boing(self, e, dt, sp):
        e.vx = e.face * (10 if e.on_ground else 30) * sp
        if self.move(e, dt):
            e.face *= -1
        if e.on_ground:
            if e.mode != "land":
                e.mode, e.mode_t = "land", random.uniform(0.15, 0.45)
            e.mode_t -= dt
            if e.mode_t <= 0:
                e.mode = "air"
                e.vy = -JUMP * random.uniform(0.75, 1.0)
                if random.random() < 0.5:
                    e.face = 1 if self.player.cx > e.cx else -1

    def zoomy(self, e, dt, sp):
        p = self.player
        e.cool -= dt
        if e.mode == "rev":
            e.vx = 0
            self.move(e, dt)
            e.mode_t -= dt
            if int(e.mode_t * 20) % 3 == 0:
                self.parts.sparkle(e.cx - e.face * 6, e.y + e.h, "white")
            if e.mode_t <= 0:
                e.mode, e.mode_t = "dash", 0.9
                self.app.audio.play("shoot")
            return
        if e.mode == "dash":
            e.vx = e.face * 130 * sp
            hit = self.move(e, dt)
            e.mode_t -= dt
            if hit or e.mode_t <= 0:
                e.mode, e.cool = "walk", 1.4
                if hit:
                    e.face *= -1
            return
        self.walker(e, dt, sp * 1.1)
        if (e.on_ground and e.cool <= 0 and abs(p.cy - e.cy) < 10 and abs(p.cx - e.cx) < 150
                and (1 if p.cx > e.cx else -1) == e.face and self.state == "play"):
            e.mode, e.mode_t = "rev", 0.45

    def sneezy(self, e, dt, sp):
        p = self.player
        if e.mode == "inhale":
            e.vx = 0
            self.move(e, dt)
            e.mode_t -= dt
            e.swell = min(1.0, e.swell + dt * 1.4)
            if e.mode_t <= 0:
                e.mode, e.swell = "walk", 0.0
                e.cool = random.uniform(2.4, 4.0) / sp
                self.shoot("dust", e.cx + e.face * 8, e.cy, e.face * 80 * (1.25 if e.angry else 1.0), 0.0)
                self.app.audio.play("shoot")
                self.parts.burst(e.cx + e.face * 8, e.cy, 6, ("gray", "white"), 40, 0.3)
            return
        e.cool -= dt
        self.walker(e, dt, sp * 0.65)
        if e.on_ground and e.cool <= 0 and self.state == "play":
            e.mode, e.mode_t = "inhale", 0.8
            e.face = 1 if p.cx > e.cx else -1

    def defeat_frozen(self, e):
        self.enemies.remove(e)
        self.add(500, e.cx, e.y - 6, "sky")
        self.hype.hit(1, fever=0.05)
        self.app.audio.play("pop")
        self.parts.burst(e.cx, e.cy, 12, ("sky", "white"), 60, 0.5)
        self.drop(e.cx - 4, e.cy - 4, e)

    def hurt(self):
        if self.inv > 0 or self.state != "play":
            return
        if self.shield:
            self.shield = False
            self.shield_t = 20.0
            self.inv = 1.5
            self.app.audio.play("pop")
            self.app.shake(2, 0.2)
            self.parts.burst(self.player.cx, self.player.cy, 16, ("mint", "white"), 70, 0.5)
            self.floats.add(self.player.cx, self.player.y - 6, "SHIELD!", "mint")
            return
        self.lives -= 1
        self.missed = True
        self.hype.break_combo()
        self.state, self.state_t = "dead", 0.0
        self.app.audio.play("hurt")
        self.app.shake(3, 0.3)
        self.hype.flash("red", 0.15)
        self.parts.burst(self.player.cx, self.player.cy, 20, ("white", "pink", "hotpink"), 80, 0.8)

    # ---------------------------------------------------------------- bubbles
    def update_bubbles(self, dt):
        p, au = self.player, self.app.audio
        catch = 11 + 2 * self.ups["trap"]
        damp = 0.92 ** (dt * 60)
        for b in self.bubbles:
            if b.dead:
                continue
            b.age += dt
            b.life -= dt
            if b.pop_in is not None:
                b.pop_in -= dt
                if b.pop_in <= 0:
                    self.pop(b)
                continue
            if b.age < FAST_PHASE:
                b.x += b.vx * dt
                b.y += b.vy * dt
                b.vx *= damp
                b.vy *= damp
                if self.cell(b.x + (7 if b.vx > 0 else -7), b.y) == "#" or (b.vy < 0 and self.cell(b.x, b.y - 7) == "#"):
                    b.age = FAST_PHASE
                if b.enemy is None and b.kind == "normal":
                    self.bubble_hits(b, catch, au)
            else:
                rise = 18 if b.enemy else (34 if b.kind == "party" else (14 if b.kind == "letter" else 22))
                b.y -= rise * dt
                b.x += math.sin(self.t * 2 + b.seed) * 8 * dt + self.wind * 16 * dt
                if b.kind != "party" and self.cell(b.x, b.y - 8) == "#":
                    b.y += rise * dt
                if b.y < TOP - 8:
                    b.y += FIELD_H
                b.x = max(T * 2 + 8, min(W - T * 2 - 8, b.x))
                if b.kind == "party" and b.y < TOP + 10:
                    b.dead = True
                    self.parts.burst(b.x, b.y, 4, ("white", "sky"), 30, 0.3)
                    continue
                if self.boss is not None and b.kind == "normal" and self.boss.hits(b.x, b.y, 8):
                    b.dead = True
                    self.parts.burst(b.x, b.y, 6, ("white", "sky"), 40, 0.3)
                    self.boss.hurt(self, 4 if b.enemy is not None else 1, "SPLASH!" if b.enemy is not None else None)
                    continue
                if self.state not in ("dead", "tally") and math.hypot(p.cx - b.x, p.cy - b.y) < 12:
                    if b.kind == "letter":
                        self.collect_letter(b)
                    elif p.vy > 0 and p.y + p.h < b.y and self.app.input.down("a"):
                        p.vy = -JUMP * 0.95
                        self.air_jumps = 1 if self.ups["jump"] >= 2 else 0
                        au.play("jump")
                        if b.kind == "party":
                            self.bounces += 1
                            self.pop(b)
                    else:
                        self.pop(b)
            if b.life <= 0 and not b.dead:
                if b.enemy:
                    e = b.enemy
                    e.x, e.y = b.x - e.w / 2, b.y - e.h / 2
                    e.angry = True
                    self.enemies.append(e)
                    b.enemy = None
                self.pop(b, quiet=True)
        # keep bubbles from overlapping completely
        alive = [b for b in self.bubbles if not b.dead and b.age > FAST_PHASE]
        for i, a in enumerate(alive):
            for b2 in alive[i + 1:]:
                dx, dy = b2.x - a.x, b2.y - a.y
                d = math.hypot(dx, dy)
                if 0 < d < 13:
                    push = (13 - d) * 0.5
                    a.x -= dx / d * push
                    a.y -= dy / d * push
                    b2.x += dx / d * push
                    b2.y += dy / d * push
        self.bubbles = [b for b in self.bubbles if not b.dead]

    def bubble_hits(self, b, catch, au):
        """A freshly blown bubble: trap an enemy, knock off a lid, cancel dust, hit the boss or a party bubble."""
        for e in self.enemies:
            if abs(e.cx - b.x) < catch and abs(e.cy - b.y) < catch:
                if e.lid:
                    e.lid = False
                    e.stun = 0.7
                    e.angry = True
                    b.dead = True
                    self.add(30, e.cx, e.y - 6, "white")
                    au.play("tin")
                    self.parts.burst(e.cx, e.y, 10, ("gray", "white"), 70, 0.4)
                    return
                b.enemy = e
                b.life = self.trap_time()
                self.enemies.remove(e)
                self.add(50)
                au.play("trap")
                return
        for s in self.shots:
            if s.r and not s.dead and math.hypot(s.x - b.x, s.y - b.y) < s.r + 7:
                s.dead = True
                b.dead = True
                self.add(30, s.x, s.y - 6, "white")
                self.parts.burst(s.x, s.y, 6, ("gray", "white"), 40, 0.3)
                au.play("pop")
                return
        if self.boss is not None:
            if self.boss.hits(b.x, b.y, 7):
                b.dead = True
                self.parts.burst(b.x, b.y, 6, ("white", "sky"), 50, 0.3)
                self.boss.hurt(self, 1)
                return
            if self.boss.touches(b.x, b.y, 7):
                b.dead = True
                au.play("tin")
                self.parts.burst(b.x, b.y, 4, ("white",), 30, 0.2)
                return
        for o in self.bubbles:
            if o.kind == "party" and not o.dead and math.hypot(o.x - b.x, o.y - b.y) < 14:
                b.dead = True
                self.pop(o)
                return

    def pop(self, b, quiet=False):
        if b.dead:
            return
        b.dead = True
        au = self.app.audio
        self.parts.burst(b.x, b.y, 8, ("white", "sky", "lavender"), 50, 0.4)
        if b.enemy:
            e = b.enemy
            self.chain = self.chain + 1 if self.chain_t > 0 else 1
            self.chain_t = 0.5
            self.best_chain = max(self.best_chain, self.chain)
            pts = int(min(8000, 500 * 2 ** (self.chain - 1)) * (1 + 0.5 * self.ups["chain"]))
            self.add(pts, b.x, b.y - 10 - 7 * min(4, self.chain - 1), "yellow" if self.chain < 2 else "mint")
            self.hype.hit(1, fever=0.06)
            self.drop(b.x - 4, b.y - 4, e)
            au.play("pop")
            self.app.shake(1.5, 0.12)
            if self.boss is not None and math.hypot(b.x - self.boss.x, b.y - self.boss.y) < 56:
                self.boss.hurt(self, 4, "SPLASH!")
            reach = 24 + 10 * self.ups["chain"]
            for o in self.bubbles:
                if o.enemy and o.pop_in is None and not o.dead and math.hypot(o.x - b.x, o.y - b.y) < reach:
                    o.pop_in = 0.09
            self.chain_hype()
        elif b.kind == "party":
            mult = max(1, min(5, self.bounces))
            pts = b.value * mult
            self.add(pts, b.x, b.y - 10, "yellow" if b.value < 1000 else "orange")
            self.bonus_got += 1
            self.hype.hit(1, fever=0.03)
            au.play("coin" if b.value >= 1000 else "pop")
            if mult > 1:
                self.floats.add(b.x, b.y - 20, f"BOUNCE X{mult}", "lime")
        elif b.kind == "letter":
            pass
        elif not quiet:
            self.add(10)
            au.play("pop")

    def chain_hype(self):
        n, h = self.chain, self.hype
        if n < 3:
            return
        h.banners = [bn for bn in h.banners if not bn[0].endswith("CHAIN!")]
        if n == 5:
            h.banner("SUPER CHAIN!", "+5000", rainbow=True, dur=1.4, sound="combo")
            h.slowmo(0.4, 0.6)
            h.flash("white", 0.15)
            h.shower(40, "stars")
            self.add(5000)
        elif n == 8:
            h.jackpot(10000, "MEGA SUDS! +10000")
        elif n < 5:
            h.banner(f"{n} CHAIN!", color="peach", dur=0.9, scale=1, sound="combo")
        elif n > 8:
            h.banner(f"{n} CHAIN!", color="hotpink", dur=0.9, scale=2)

    def collect_letter(self, b):
        b.dead = True
        self.letters[b.sub] = True
        self.app.audio.play("coin")
        self.add(500, b.x, b.y - 10, "yellow")
        self.parts.burst(b.x, b.y, 14, ("yellow", "white", "orange"), 60, 0.5)
        if all(self.letters):
            self.letters = [False] * 5
            self.lives += 1
            self.hype.banner("M-O-C-H-I!", "EXTRA LIFE +10000", rainbow=True, dur=2.2, sound="extra")
            self.hype.shower(40, "hearts")
            self.hype.shower(40, "confetti")
            self.hype.flash("pink", 0.25)
            self.add(10000)
        else:
            self.hype.banner(LETTERS[b.sub], "LETTER BUBBLE!", color="yellow", dur=0.9)

    # ---------------------------------------------------------------- items
    def drop_snack(self, x, y):
        kind = self.theme[8] if random.random() < 0.75 else random.randrange(8)
        self.items.append(Item(x, y, "snack", kind, 100 * (kind + 1) + 20 * self.tier))
        self.snacks_out += 1

    def drop(self, x, y, e):
        if e.golden:
            self.items.append(Item(x, y, "chest"))
            self.app.audio.play("bonus")
            return
        self.drop_snack(x, y)
        if self.kind != "normal" or any(it.kind in POWERS + ("heart", "cake") for it in self.items):
            return
        roll = random.random()
        if roll < 0.012 and self.lives < 9:
            self.items.append(Item(x, y, "heart"))
        elif roll < 0.03:
            self.items.append(Item(x, y, "cake"))
        elif roll < 0.075:
            self.items.append(Item(x, y, random.choice(POWERS)))

    def update_items(self, dt):
        p = self.player
        mag = (0, 40, 64, 96)[self.ups["magnet"]]
        for f in self.items:
            f.life -= dt
            d = math.hypot(p.cx - f.cx, p.cy - f.cy)
            if mag and d < mag and self.state not in ("dead", "tally") and f.life < 8.6:
                f.x += (p.cx - f.cx) / max(1.0, d) * 150 * dt
                f.y += (p.cy - f.cy) / max(1.0, d) * 150 * dt
                f.vy = 0
                if int(self.t * 20) % 4 == 0:
                    self.parts.sparkle(f.cx, f.cy, "red")
            elif f.rain and not f.on_ground:
                f.vx = 0
                f.vy = min(f.vy + 200 * dt, 70)
                self.move(f, dt, 0)
            else:
                f.vx *= 0.98 ** (dt * 60)
                self.move(f, dt)
                if f.on_ground:
                    f.vx = 0
            if self.state not in ("dead", "tally") and f.rect().colliderect(p.rect()):
                f.life = -1
                self.collect(f)
        self.items = [f for f in self.items if f.life > 0]

    def collect(self, f):
        au, h, k = self.app.audio, self.hype, f.kind
        self.parts.burst(f.cx, f.cy, 6, ("yellow", "white"), 40, 0.4)
        if k == "snack":
            self.add(f.value, f.cx, f.y - 6, "peach")
            h.hit(1, fever=0.02)
            au.play("fruit")
            self.snacks_got += 1
            if self.kind == "bonus":
                self.bonus_got += 1
        elif k == "chest":
            h.jackpot(5000 + 1000 * self.tier, "TREASURE CHEST!")
        elif k == "cake":
            self.add(3000 if self.kind != "bonus" else f.value, f.cx, f.y - 8, "orange")
            h.banner("SUPER SNACK!", color="orange", dur=1.0, sound="bonus")
            h.shower(24, "coins")
            if self.kind == "bonus":
                self.bonus_got += 1
        elif k == "gem":
            self.add(2000, f.cx, f.y - 8, "sky")
            au.play("coin")
        elif k == "heart":
            self.lives += 1
            h.banner("1UP!", color="pink", dur=1.0, sound="extra")
        elif k == "shield":
            self.shield = True
            h.banner("BUBBLE SHIELD!", color="mint", dur=1.0, scale=1, sound="powerup")
        elif k == "clock":
            self.freeze_t = 5.0
            h.banner("FREEZE!", "TOUCH THEM TO POP!", color="sky", dur=1.2, sound="powerup")
            h.flash("sky", 0.2)
        elif k == "soda":
            h.banner("FIZZ BURST!", color="hotpink", dur=1.0, sound="powerup")
            p = self.player
            for i in range(10):
                a = i * math.tau / 10
                self.bubbles.append(Bubble(p.cx, p.cy, math.cos(a) * 200, math.sin(a) * 200, 6.5))

    # ---------------------------------------------------------------- shots
    def update_shots(self, dt):
        p = self.player
        for s in self.shots:
            if s.dead:
                continue
            s.age += dt
            if s.kind in ("bolt", "mark"):
                if s.age >= s.warn:
                    if s.kind == "mark":
                        s.dead = True
                        self.shoot("drop", s.x, TOP + 10, 0.0, 40.0)
                    elif s.age < s.warn + 0.3:
                        if s.age - dt < s.warn:
                            self.app.audio.play("explode")
                            self.app.shake(2, 0.2)
                        if self.state == "play" and abs(p.cx - s.x) < 7:
                            self.hurt()
                    else:
                        s.dead = True
                continue
            s.vy += s.grav * dt
            s.x += s.vx * dt
            s.y += s.vy * dt
            if s.kind == "wave":
                if s.x < T * 2 or s.x > W - T * 2:
                    s.dead = True
                elif self.state == "play" and abs(p.cx - s.x) < 6 and p.y + p.h > FLOOR_Y - 9:
                    self.hurt()
                continue
            if (s.age > 6 or self.cell(s.x, s.y) == "#" or s.x < T * 2 or s.x > W - T * 2
                    or (s.grav and self.cell(s.x, s.y + s.r) == "=" and s.vy > 0)):
                s.dead = True
                self.parts.burst(s.x, s.y, 5, ("gray", "white"), 30, 0.3)
                continue
            if self.state == "play" and math.hypot(p.cx - s.x, p.cy - s.y) < s.r + 5:
                s.dead = True
                self.hurt()
        self.shots = [s for s in self.shots if not s.dead]

    # ---------------------------------------------------------------- bonus stages
    def update_bonus(self, dt):
        if self.state != "play":
            return
        self.time_left -= dt
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            if self.sd["bt"] == "party":
                self.spawn_t = 0.3
                b = Bubble(random.uniform(T * 3 + 8, W - T * 3 - 8), FLOOR_Y + 4, 0.0, 0.0, 30.0, "party")
                b.age = FAST_PHASE
                gold = random.random() < 0.06
                b.sub = random.randrange(8)
                b.value = 1000 if gold else 200 + 20 * self.tier
                self.bubbles.append(b)
            else:
                self.spawn_t = 0.22
                cake = random.random() < 0.04
                it = Item(random.uniform(T * 3, W - T * 4), TOP + 6, "cake" if cake else "snack", random.randrange(8),
                          2000 if cake else 200 + 20 * self.tier)
                it.vx, it.vy, it.rain, it.life = 0.0, 10.0, True, 6.0
                self.items.append(it)
            self.bonus_n += 1
        if self.time_left <= 0:
            self.time_left = 0
            self.state, self.state_t = "timeup", 0.0
            self.hype.banner("TIME UP!", color="yellow", dur=1.4, sound="levelup")
            for b in self.bubbles:
                if b.kind == "party":
                    b.dead = True
                    self.parts.burst(b.x, b.y, 4, ("white", "sky"), 30, 0.3)
            for it in self.items:
                if it.rain:
                    it.life = 0

    # ---------------------------------------------------------------- tally
    def start_tally(self):
        rows = []
        tr = self.tier
        if self.kind == "normal":
            rows.append(["STAGE CLEAR", 1000 + 200 * tr])
            tb = max(0, int((self.sd["par"] - self.level_t) * 50))
            if tb:
                rows.append(["TIME BONUS", tb])
            if not self.missed:
                rows.append(["NO MISS", 3000])
            if self.snacks_out and self.snacks_got >= self.snacks_out:
                rows.append(["ALL SNACKS", 2000])
            if self.best_chain >= 2:
                rows.append([f"BEST CHAIN X{self.best_chain}", 400 * self.best_chain])
        elif self.kind == "boss":
            rows.append(["BOSS CLEAR", 5000 + 1000 * tr])
            tb = max(0, int((90 - self.level_t) * 100))
            if tb:
                rows.append(["SPEED BONUS", tb])
            if not self.missed:
                rows.append(["NO MISS", 10000])
        else:
            word = "POPPED" if self.sd["bt"] == "party" else "CAUGHT"
            rows.append([f"{word} {self.bonus_got}/{self.bonus_n}", 50 * self.bonus_got])
            if self.bonus_got >= self.bonus_n * 0.85:
                rows.append(["PERFECT!!", 10000])
                self.hype.banner("PERFECT!!", rainbow=True, dur=1.8, sound="win")
                self.hype.shower(60, "coins")
            elif self.bonus_got >= self.bonus_n * 0.55:
                rows.append(["GREAT!", 3000])
        self.tally = [[label, val, 0.0] for label, val in rows]
        self.tally_i, self.tally_t, self.tally_total = 0, 0.0, 0
        self.state, self.state_t = "tally", 0.0

    def update_tally(self, dt):
        self.tally_t += dt
        inp = self.app.input
        if self.tally_i < len(self.tally):
            row = self.tally[self.tally_i]
            row[2] = min(row[1], row[2] + max(row[1], 300) * dt * 2.4)
            if int(self.tally_t * 14) != int((self.tally_t - dt) * 14) and row[2] < row[1]:
                self.app.audio.play("move")
            skip = self.state_t > 0.3 and inp.hit("a", "b")
            if row[2] >= row[1] or skip:
                for r in self.tally[self.tally_i:] if skip else [row]:
                    r[2] = r[1]
                    self.tally_total += self.add(r[1])
                self.tally_i = len(self.tally) if skip else self.tally_i + 1
                self.tally_t = 0.0
                self.app.audio.play("coin")
                self.check_extra()
            return
        if self.tally_t > 1.5 or (self.tally_t > 0.3 and inp.hit("a", "b")):
            if self.kind in ("boss", "bonus"):
                self.picks, self.after_picks, self.pick_title = 1, "next", "POWER UP!"
                self.state, self.state_t = "picks", 0.0
            else:
                self.next_stage()

    # ---------------------------------------------------------------- draw
    def render(self, s):
        name, blk, blk_d, plat, plat_d, sky_a, sky_b, style, _ = self.theme
        for y in range(0, H, 4):
            s.fill(lerp_col(sky_a, sky_b, y / H), (0, y, W, 4))
        self.backdrop(s, style, sky_a)
        s.blit(self.field, (0, TOP))
        for sh in self.shots:
            self.draw_shot(s, sh)
        for f in self.items:
            if f.life > 2 or int(f.life * 10) % 2:
                art.item(s, f.kind, f.sub, int(f.x), int(f.y), self.t)
        for e in self.enemies:
            art.critter(s, e.kind, int(e.x) - 2, int(e.y) - 2, self.t, e.face < 0, e.angry, False, e)
            if self.freeze_t > 0:
                bubble(s, e.cx, e.cy, 9, self.t, "sky")
        if self.boss is not None:
            self.boss.draw(s, self.t)
        for b in self.bubbles:
            if b.enemy:
                e = b.enemy
                art.critter(s, e.kind, int(b.x) - 8, int(b.y) - 8, self.t, False, b.life < 2, True, e)
                tint = "red" if b.life < 2 and int(b.life * 8) % 2 else ("yellow" if e.golden else "lavender")
                bubble(s, b.x, b.y, 10 + self.ups["trap"], self.t, tint)
            elif b.kind == "letter":
                art.letter_bubble(s, b.x, b.y, LETTERS[b.sub], self.t)
            elif b.kind == "party":
                if b.value >= 1000:
                    bubble(s, b.x, b.y, 9, self.t, "yellow")
                    s.blit(sprite("star"), (int(b.x) - 3, int(b.y) - 3))
                else:
                    cute.fruit(s, b.sub, int(b.x) - 4, int(b.y) - 4)
                    bubble(s, b.x, b.y, 8, self.t, "sky")
            else:
                bubble(s, b.x, b.y, 7 if b.age < FAST_PHASE else 8, self.t)
        p = self.player
        if self.state not in ("dead", "over") and (self.inv <= 0 or int(self.inv * 12) % 2 == 0):
            if not p.on_ground:
                img = sprite("momo_jump", 0, flip=self.face < 0)
            elif abs(p.vx) > 1:
                img = sprite("momo_walk", int(self.t * 10), flip=self.face < 0)
            else:
                img = sprite("momo_idle", int(self.t * 2), flip=self.face < 0)
            s.blit(img, (int(p.x) - 2, int(p.y) - 1))
            if self.shield:
                bubble(s, p.cx, p.cy, 11, self.t, "mint")
        self.parts.draw(s)
        self.floats.draw(s)
        if "dark" in self.mods and self.state not in ("intro", "tally"):
            self.darkness(s)
        self.hud(s)
        self.overlays(s)

    def backdrop(self, s, style, base):
        t = self.t
        shade = lerp_col(base, "black", 0.35)
        if style == "bubbles":
            for i in range(12):
                x = (i * 53 + t * (4 + i % 3)) % W
                y = TOP + (i * 37) % FIELD_H
                pygame.draw.circle(s, shade, (int(x), int(y)), 2 + i % 3)
        elif style == "tiles":
            for x in range(0, W, 16):
                s.fill(shade, (x, TOP, 1, FIELD_H))
            for y in range(TOP, H, 16):
                s.fill(shade, (0, y, W, 1))
        elif style == "dots":
            for i in range(40):
                x = (i * 41) % W
                y = TOP + (i * 23 + int(t * 3)) % FIELD_H
                s.fill(shade, (x, y, 2, 2))
        elif style == "rain":
            for i in range(24):
                x = (i * 29 + int(t * 6)) % W
                y = TOP + (i * 47 + int(t * 60)) % FIELD_H
                s.fill(shade, (x, y, 1, 5))
        elif style == "stripes":
            for i in range(-12, 24):
                x0 = i * 16 + int(t * 4) % 16
                pygame.draw.line(s, shade, (x0, H), (x0 + 60, TOP), 3)
        else:
            for i in range(30):
                x, y = (i * 67) % W, TOP + (i * 31) % FIELD_H
                c = "lavender" if int(t * 2 + i) % 5 == 0 else None
                s.fill(col(c) if c else shade, (x, y, 1, 1))
        if self.wind:
            for i in range(8):
                x = (i * 47 + int(t * 50 * self.wind)) % W
                y = TOP + 10 + (i * 23) % (FIELD_H - 30)
                s.fill(shade, (x, y, 6, 1))

    def darkness(self, s):
        p = self.player
        R = 64
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        c = (12, 8, 24, 200)
        cx, cy = int(p.cx), int(p.cy)
        for y in range(TOP, H):
            dy = y - cy
            if abs(dy) < R:
                half = int(math.sqrt(R * R - dy * dy))
                ov.fill(c, (0, y, max(0, cx - half), 1))
                ov.fill(c, (cx + half, y, W - (cx + half), 1))
            else:
                ov.fill(c, (0, y, W, 1))
        s.blit(ov, (0, 0))

    def draw_shot(self, s, sh):
        x, y = int(sh.x), int(sh.y)
        if sh.kind == "dust":
            pygame.draw.circle(s, col("darkgray"), (x, y), 3)
            pygame.draw.circle(s, col("gray"), (x - 1, y - 1), 1)
        elif sh.kind == "drop":
            pygame.draw.circle(s, col("black"), (x, y), 3)
            s.fill(col("darkgray"), (x - 1, y - 6, 2, 4))
        elif sh.kind == "water":
            pygame.draw.circle(s, col("sky"), (x, y), 2)
            s.fill(col("white"), (x - 1, y - 1, 1, 1))
        elif sh.kind == "wave":
            for i in range(3):
                h = 8 - i * 2
                s.fill(col(("white", "sky", "blue")[i]), (x - 3 + i * (-2 if sh.vx > 0 else 2), FLOOR_Y - h, 3, h))
        elif sh.kind == "mark":
            if int(sh.age * 12) % 2 == 0:
                pygame.draw.ellipse(s, col("black"), (x - 6, FLOOR_Y - 3, 12, 4))
                draw_text(s, "!", x, FLOOR_Y - 14, "red", align="center", shadow=None)
        elif sh.kind == "bolt":
            if sh.age < sh.warn:
                if int(sh.age * 16) % 2 == 0:
                    for yy in range(TOP + 8, FLOOR_Y, 6):
                        s.fill(col("yellow"), (x, yy, 1, 3))
            else:
                s.fill(col("yellow"), (x - 4, TOP + 8, 9, FLOOR_Y - TOP - 8))
                s.fill(col("white"), (x - 1, TOP + 8, 3, FLOOR_Y - TOP - 8))

    def hud(self, s):
        s.fill(col("black"), (0, 0, W, TOP))
        draw_text(s, f"{self.score:07d}", 4, 3, "white", shadow=None)
        self.hearts(s, 48, 3, self.lives, max_show=5)
        draw_text(s, f"HI {max(self.best, self.score):07d}", 150, 3, "lavender", align="center", shadow=None)
        for i, ch in enumerate(LETTERS):
            draw_text(s, ch, 190 + i * 7, 3, "yellow" if self.letters[i] else "darkgray", shadow=None)
        draw_text(s, f"STAGE {self.stage}", W - 4, 3, "yellow", align="right", shadow=None)
        h = self.hype
        if h.fever_on:
            s.fill(col(rainbow(0, self.t)), (0, TOP - 1, int(W * h.fever_t / h.FEVER_TIME), 1))
        else:
            s.fill(col("hotpink"), (0, TOP - 1, int(W * h.fever), 1))
        if self.boss is not None and not self.boss.dead and self.state not in ("warning", "tally"):
            boss_bar(s, self.boss.name, self.boss.hp, self.boss.maxhp, self.t, y=FLOOR_Y + 4)
        if self.kind == "bonus" and self.state in ("play", "intro"):
            frac = self.time_left / float(self.sd["time"])
            panel(s, (60, FLOOR_Y + 4, 200, 12), fill="black", border="yellow", radius=3, shadow=False)
            draw_text(s, f"TIME {int(math.ceil(self.time_left)):2d}", 64, FLOOR_Y + 7, "white", shadow=None)
            s.fill(col("darkgray"), (112, FLOOR_Y + 8, 140, 4))
            s.fill(col("yellow" if frac > 0.25 or int(self.t * 8) % 2 else "red"), (112, FLOOR_Y + 8, int(140 * frac), 4))

    def overlays(self, s):
        st = self.state
        if st == "intro" and self.kind == "normal":
            self.stage_card(s)
        elif st == "warning":
            self.warning_card(s)
        elif st == "tally":
            self.tally_card(s)
        elif self.hurry and self.state == "play" and self.level_t < self.sd["par"] + 2.5 and int(self.t * 6) % 2:
            draw_text(s, "HURRY!", W // 2, 100, "red", 2, align="center", outline="black")

    def stage_card(self, s):
        k = min(1.0, self.state_t * 5)
        y = int(54 - (1 - k) * 80)
        info = self.sd
        lines = [data.MODS[m][0] for m in self.mods]
        new = info.get("new") or ""
        hh = 56 + 10 * len(lines) + (20 if new else 0)
        panel(s, (56, y, 208, hh), fill="ink", border=self.theme[1])
        draw_text(s, f"STAGE {self.stage}", W // 2, y + 7, "yellow", 2, align="center", outline="black")
        draw_text(s, self.theme[0], W // 2, y + 26, self.theme[1], align="center", shadow=None)
        draw_text(s, f'"{self.level_name}"', W // 2, y + 37, "white", align="center", shadow=None)
        yy = y + 49
        for ln in lines:
            draw_text(s, "* " + ln + " *", W // 2, yy, "lime", align="center", shadow=None)
            yy += 10
        if new:
            nm, _, _, blurb = data.ENEMIES[new]
            art.critter(s, new, 70, yy - 1, self.t, False, False, False, None)
            draw_text(s, f"NEW! {nm}", 92, yy, "hotpink", shadow=None)
            draw_text(s, blurb, 92, yy + 9, "white", shadow=None)

    def warning_card(self, s):
        t = self.state_t
        for band_y in (46, 132):
            s.fill(col("black"), (0, band_y, W, 12))
            off = int(t * 40) % 16
            for x in range(-16, W + 16, 16):
                pygame.draw.polygon(s, col("red"), [(x + off, band_y), (x + off + 8, band_y), (x + off + 2, band_y + 12),
                                                    (x + off - 6, band_y + 12)])
        if int(t * 4) % 2 == 0:
            draw_text(s, "WARNING", W // 2, 66, "red", 3, align="center", outline="black")
        draw_text(s, "A HUGE DUST BOSS APPROACHES", W // 2, 96, "white", align="center", outline="black")
        draw_text(s, self.boss.name, W // 2, 110, "yellow", 2, align="center", outline="black")

    def tally_card(self, s):
        n = len(self.tally)
        hh = 46 + n * 11
        y0 = 100 - hh // 2
        panel(s, (64, y0, 192, hh), fill="ink", border="mint")
        title = {"normal": "STAGE CLEAR!", "boss": "BOSS DEFEATED!", "bonus": "BONUS RESULT"}[self.kind]
        draw_text(s, title, W // 2, y0 + 7, "mint", 2, align="center", outline="black")
        for i, (label, val, shown) in enumerate(self.tally):
            if i > self.tally_i:
                break
            yy = y0 + 28 + i * 11
            draw_text(s, label, 74, yy, "white", shadow=None)
            draw_text(s, f"{int(shown)}", 246, yy, "yellow", align="right", shadow=None)
        if self.tally_i >= n:
            draw_text(s, f"TOTAL {self.tally_total}", W // 2, y0 + hh - 13, rainbow(0, self.t), align="center",
                      shadow=None)


def preview(s, t):
    s.fill(col("deep"))
    w, h = s.get_size()
    for x in range(0, w, 8):
        s.fill(col("pink"), (x, h - 8, 7, 7))
    s.fill(col("cream"), (10, h - 30, 40, 3))
    s.blit(sprite("momo_walk", int(t * 8)), (16 + int(math.sin(t) * 10), h - 24))
    bubble(s, w - 30 + math.sin(t * 2) * 3, h - 36 - (t * 6) % 10, 9, t)
    cute.grump(s, w - 38, h - 44 - int((t * 6) % 10), t, trapped=True)
    cute.grump(s, w - 26, h - 24, t, flip=True)
