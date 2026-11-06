"""KITTEN PILE - tuck sleepy kitten pairs into the cat bed; 4 of a colour curl up and fall asleep.
(original falling-pairs puzzle for MOCHI ARCADE)

Poppy, the lilac night-shift nanny cat, lowers kitten pairs (ginger, tabby, sooty, snowy and calico) into a
wicker bed. Four or more touching kittens of one colour curl up and nap; the kittens above tumble down and can
chain. Chains fill the PURR meter (FEVER) and send naps at rival cats who throw pillows, grandpa cats and grumpy
kittens back. 200 stages over 20 bedrooms: nap goals, chains, star rescues, pillow forts, stormy nights,
pillow duels, a boss cat every 10th stage and a bonus stage on every x5, with upgrades between.

Rules: kitten_pile_core.py. Stages: kitten_pile_stages.py. Art + songs: kitten_pile_art.py.
The iOS port (ios/MochiArcade/Games/KittenPile*.swift) mirrors these files.
"""
import math
import random

import pygame

from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, is_bonus, is_boss, rainbow, tier
from mochi_arcade.games import DIFF
from mochi_arcade.games import kitten_pile_art as A
from mochi_arcade.games import kitten_pile_core as K
from mochi_arcade.games import kitten_pile_stages as S
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.gfx import H, W, col, draw_text, lerp_col, panel, sprite, text_width

HOWTO = ["LEFT/RIGHT  MOVE         DOWN  FASTER", "Z / SPACE   TURN RIGHT   X  TURN LEFT", "UP / V      DROP",
         "", "TOUCH 4 KITTENS OF ONE COLOUR: THEY NAP!", "KITTENS THAT TUMBLE INTO NEW GROUPS CHAIN",
         "CHAINS FILL THE PURR METER AND SEND", "NAPS AT RIVAL CATS. YARN BALLS PUT A",
         "COLOUR TO SLEEP, TOY MICE SHOO PILLOWS.", "200 STAGES: BOSS EVERY 10TH, BONUS ON X5.",
         "ENTER / ESC  PAUSE"]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1),
           ("guide", "DROP GUIDE", [(True, "ON"), (False, "OFF")], True)]
SMOKE_KEYS = ["left", "right", "down", "a", "b", "up"]

CELL = A.CELL
COLS, ROWS = K.COLS, K.ROWS
BX, BY = 124, 44
BW, BH = COLS * CELL, ROWS * CELL
FALL = 520.0                 # px/s for tumbling kittens
POP_TIME = 0.5
LOCK_DELAY = 0.4
LIFE_STEP = 30000            # extra lives at 30k, 90k, 180k, 300k ...
GOLD_CHANCE = 0.012
FOE_X, FOE_Y = 261, 146
CHAIN_WORDS = ["", "", "CATNAP!", "SNOOZE!", "SLUMBER!", "DREAMLAND!", "MOONBEAM!", "STARDUST!", "PURRFECT!"]
UPGRADE_POOL = []


def _icon(uid, color):
    def draw(s, cx, cy, t):
        if uid == "peek":
            A.kitten(s, cx - 6, cy - 6, 4, 4)
        elif uid == "cozy":
            s.blit(sprite("kp_pillow"), (cx - 6, cy - 6))
        elif uid == "yarn":
            s.blit(sprite("kp_yarn"), (cx - 6, cy - 6))
        elif uid == "mouse":
            s.blit(sprite("kp_mouse"), (cx - 6, cy - 6))
        elif uid == "fort":
            s.blit(sprite("kp_pillow"), (cx - 8, cy - 4))
            s.blit(sprite("kp_pillow"), (cx - 4, cy - 8))
        elif uid == "purr":
            A.kitten(s, cx - 6, cy - 6, 1, 3)
        elif uid == "catnip":
            pygame.draw.polygon(s, col("lime"), [(cx, cy - 7), (cx + 5, cy), (cx, cy + 7), (cx - 5, cy)])
            pygame.draw.line(s, col("mint"), (cx, cy - 6), (cx, cy + 6))
        elif uid == "lullaby":
            draw_text(s, "~", cx - 2, cy - 4, "mint", shadow=None)
        elif uid == "guard":
            A.lantern(s, cx - 2, cy + 1, t)
        elif uid == "bell":
            A.kitten(s, cx - 6, cy - 6, 1 | K.GOLD, 3, t)
        else:
            draw_text(s, "@", cx - 2, cy - 4, "pink", shadow=None)
    return draw


for _u in S.UPGRADES:
    UPGRADE_POOL.append(Upgrade(_u[0], _u[1], _u[2], _u[3], _icon(_u[0], _u[3]), _u[4]))


def __getattr__(name):
    """EXPORT (stage tables for iOS) is built on demand: importing this module stays instant for the carousel."""
    if name == "EXPORT":
        return {"stages": S.stages(), "themes": S.THEMES, "bosses": S.BOSSES, "rivals": S.RIVALS,
                "upgrades": S.UPGRADES, "attackNames": S.ATTACK_NAMES, "mods": S.MODS, "kindTitle": S.KIND_TITLE,
                "talk": S.TALK, "cheers": S.CHEERS}
    raise AttributeError(name)


class KittenPile(GameScene):
    @property
    def music(self):
        return self.song

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        self.hype.COMBO_TIME = 4.0
        self.hype.combo_y = 14
        diff = opt.get("difficulty", "normal")
        self.lives = LIVES.get(diff, 3)
        self.speed = SPEED.get(diff, 1.0)
        self.foe_mult = {"easy": 0.75, "normal": 1.0, "hard": 1.3}.get(diff, 1.0)
        self.guide = bool(opt.get("guide", True))
        self.stages = S.stages()
        self.ups = {}
        self.life_k = 1
        self.song = "kp_nap"
        self.fever_was = False
        self.attempt = 0
        self.shots = []              # [x, y, progress, power]: naps flying at the rival (power -1: a pillow back)
        self.coin_fx = []            # [x, y, vx, vy, life]: fish coins hopping out of the bed (bonus stages)
        self.squish = {}             # (x, y) -> landing squash timer
        self.bed_kick = 0.0          # the bed shakes when a row of pillows pushes up
        self.foe_keep = 0            # rival / boss awake points kept for a retry
        self.talk = None             # Poppy's speech bubble [text, time]
        self.poppy_mood = ["idle", 0.0]
        n = int(opt.get("stage") or opt.get("start", 1))
        self.begin_stage(max(1, min(STAGES, n)))

    # ================================================================ helpers
    def up(self, uid):
        return self.ups.get(uid, 0)

    def kind(self):
        return self.st["k"]

    def bonus(self):
        return self.st["k"] in ("snack", "domino")

    def lv(self):
        return self.tier + 1

    def mood(self, m, dur=1.2):
        self.poppy_mood = [m, dur]

    def say(self, text, dur=2.2):
        self.talk = [text, dur]

    def gravity(self):
        g = self.st["g"] / self.speed * (1 + 0.12 * self.up("cozy"))
        if self.zoom_t > 0:
            g /= 3
        return max(0.03, g)

    def pending_total(self):
        return self.pend[0] + self.pend[1] * 3 + self.pend[2]

    # ================================================================ stage flow
    def begin_stage(self, n, retry=False):
        st = self.stages[n - 1]
        self.st = st
        self.stage_n = n
        self.tier = tier(n)
        self.theme = S.THEMES[self.tier]
        self.attempt = self.attempt + 1 if retry else 0
        self.rng = K.KRand(K.stage_seed(n, self.attempt))
        self.frng = K.KRand(K.stage_seed(n, self.attempt, 1))
        self.su_i = 0
        self.load_rows(st["rows"])
        self.piece = None
        self.piece_id = 0
        self.queue = []
        self.phase = "wait"
        self.phase_t = 0.0
        self.chain = 0
        self.popping = []
        self.pop_t = 0.0
        self.landed = []
        self.pend = [0, 0, 0]        # pillows, grandpas, grumpy kittens
        self.pend_rise = 0
        self.fog_t = self.zoom_t = self.dizzy_t = 0.0
        self.rain_t = self.rise_t = 0.0
        self.stime = 0.0
        self.kits = self.coins = self.best_chain = self.all_clears = 0
        self.rescued = 0
        self.missed = retry
        self.guard = self.up("guard")
        self.sscore0 = self.score
        self.fall_t = self.lock_t = 0.0
        self.lock_resets = 0
        self.das_dir, self.das_t = 0, 0.0
        self.foe = None
        if st["rival"] or st["boss"]:
            d = st["boss"] or st["rival"]
            keep = d["hp"]
            if retry and self.foe_keep:
                keep = min(d["hp"], self.foe_keep + d["hp"] * 15 // 100)
            self.foe = {"boss": bool(st["boss"]), "id": d["id"], "hp": keep, "max": d["hp"], "every": d["every"],
                        "pow": d["pow"], "atk": d["atk"], "t": d["every"] * 0.9, "tele": None, "hit": 0.0,
                        "phase": 1 if keep > d["hp"] // 2 else 2, "sleep": False}
        self.foe_keep = 0
        self.dropped = False
        while len(self.queue) < 4:
            self.queue.append(self.gen_piece())
        self.reached(n)
        boss = st["k"] == "boss"
        self.state = "warning" if boss and not retry else "intro"
        self.state_t = 0.0
        self.song = "boss" if boss else "bonus" if self.bonus() else "kp_duel" if st["k"] == "duel" else "kp_nap"
        self.app.audio.music(self.song)
        self.app.audio.play("warning" if self.state == "warning" else "stage")
        self.fever_was = False
        lines = S.TALK[st["k"]]
        self.quip = lines[(n + self.attempt) % len(lines)].replace("@", self.foe_name())
        self.talk = None

    def foe_name(self):
        if not self.foe:
            return ""
        return (S.BOSSES if self.foe["boss"] else S.RIVALS)[self.foe["id"]][0]

    def load_rows(self, rows):
        self.grid = K.parse_rows(rows) if rows else K.empty_grid()
        self.off = [[0.0] * COLS for _ in range(ROWS)]
        self.mood_t = [[0.0] * COLS for _ in range(ROWS)]
        self.stars0 = K.count_cells(self.grid, lambda c: K.is_kitten(c) and c & K.STAR)

    def gen_piece(self):
        st = self.st
        if st["twins"]:
            c = 1 + self.rng.below(st["ncol"])
            return (c, c)
        if st["k"] in ("domino", "trigger"):            # the pair that sets the prebuilt chain off
            su = st["setups"][min(self.su_i, len(st["setups"]) - 1)]
            return (su["c"], su["c"])
        r = self.rng.below(1000)
        yp = int(st["yarn"] * (1 + 0.6 * self.up("yarn")) * 1000)
        mp = int(st["mouse"] * (1 + 0.6 * self.up("mouse")) * 1000)
        a = 1 + self.rng.below(st["ncol"])
        b = 1 + self.rng.below(st["ncol"])
        gold = self.rng.below(100000) < int(GOLD_CHANCE * (1 + self.up("bell")) * 100000)
        if r < yp:
            return (K.YARN, 0)
        if r < yp + mp:
            return (K.MOUSE, 0)
        return (a | (K.GOLD if gold else 0), b)

    def start_play(self):
        self.state = "play"
        self.state_t = 0.0
        self.phase = "wait"
        self.phase_t = 0.2
        if self.bonus():
            self.hype.banner("GO GO GO!", rainbow=True, dur=1.0)
            if self.st["k"] == "snack":
                self.hype.start_fever(self.st["lim"])
        else:
            self.hype.banner("GOOD NIGHT!", color="lime", dur=0.9, scale=1)
        self.say(self.quip, 2.6)

    def goal_done(self):
        st, k = self.st, self.st["k"]
        if k == "clear":
            return self.kits >= st["goal"]
        if k in ("chain", "trigger"):
            return self.best_chain >= st["goal"]
        if k == "rescue":
            return self.stars_left() == 0
        if k == "pillow":
            return K.count_cells(self.grid, K.is_junk) == 0
        if k in ("storm", "snack", "domino"):
            return self.stime >= st["lim"]
        return False

    def stars_left(self):
        return K.count_cells(self.grid, lambda c: K.is_kitten(c) and c & K.STAR)

    def progress(self):
        """(short goal text, progress text, fraction) for the goal panel."""
        st, k, g = self.st, self.st["k"], self.st["goal"]
        if k == "clear":
            return f"NAP {g} KITTENS", f"{min(self.kits, g)}/{g}", self.kits / g
        if k == "chain":
            return f"MAKE A {g} CHAIN", f"BEST {self.best_chain}", self.best_chain / g
        if k == "trigger":
            return f"SET OFF A {g} CHAIN", f"BEST {self.best_chain}", self.best_chain / g
        if k == "rescue":
            got = self.stars0 - self.stars_left()
            return f"TUCK IN {self.stars0} STARS", f"{got}/{self.stars0}", got / max(1, self.stars0)
        if k == "pillow":
            left = K.count_cells(self.grid, K.is_junk)
            return "CLEAR THE PILLOWS", f"LEFT {left}", 1 - left / max(1, g)
        if k == "storm":
            return f"SURVIVE {st['lim']} SEC", f"{max(0, int(st['lim'] - self.stime + 0.99))} SEC", self.stime / st["lim"]
        if k in ("duel", "boss"):
            f = self.foe
            goal = "SNOOZE THE BOSS!" if f["boss"] else f"SNOOZE {self.foe_name()}"
            return goal, f"AWAKE {max(0, f['hp'])}", 1 - f["hp"] / f["max"]
        if k == "snack":
            return "FISH COIN RUSH", f"COINS {self.coins}", self.stime / st["lim"]
        return f"DOMINO {min(self.su_i + 1, len(st['setups']))}/{len(st['setups'])}", f"COINS {self.coins}", \
            self.stime / st["lim"]

    def fail_stage(self, why):
        if self.state != "play":
            return
        if self.bonus():
            self.stage_clear()
            self.hype.banner("BED FULL!", "BONUS OVER", color="peach", dur=1.2)
            return
        self.state = "fail"
        self.state_t = 0.0
        self.lives -= 1
        self.piece = None
        self.hype.break_combo()
        self.app.audio.play("die")
        self.app.shake(4, 0.4)
        self.hype.banner("OH NO!", why, color="red", dur=1.6)
        self.mood("hurt", 2.0)
        self.say("THE BED IS TOO FULL!")
        if self.foe:
            self.foe["tele"] = None
            self.foe_keep = self.foe["hp"]

    def stage_clear(self):
        if self.state not in ("play", "bossdown", "foedown"):
            return
        k, L = self.st["k"], self.lv()
        self.state = "clear"
        self.state_t = 0.0
        self.piece = None
        self.app.audio.play("win")
        self.mood("cheer", 3.0)
        if k != "boss":
            self.hype.banners = []
        if self.bonus():
            self.hype.banner("BONUS END!", f"{self.coins} FISH COINS", color="yellow", dur=1.4)
            lines = [("FISH COINS", self.coins * 50 * L)]
            if self.all_clears:
                lines.append(("ALL TUCKED IN", self.all_clears * 3000 * L))
            self.say("YUM! WHAT A FEAST!")
        else:
            if k != "boss":
                self.hype.banner("STAGE CLEAR!", rainbow=True, dur=1.4)
            self.hype.shower(40, "confetti")
            lines = [("BOSS BONUS" if k == "boss" else "CLEAR", (5000 if k == "boss" else 1000) * L)]
            if k == "storm":
                lines.append(("SURVIVED", 1500 * L))
            elif self.st["par"]:
                lines.append(("TIME", int(max(0, self.st["par"] - self.stime)) * 20 * L))
            lines.append((f"BEST CHAIN X{self.best_chain}", self.best_chain * self.best_chain * 100 * L))
            lines.append(("NO MISS", 0 if self.missed else 2000 * L))
            cells = K.count_cells(self.grid, lambda c: c != 0)
            if cells == 0:
                lines.append(("EMPTY BED", 5000 * L))
            elif cells <= 8:
                lines.append(("TIDY BED", 1500 * L))
            self.say(S.CHEERS[(self.stage_n + self.score // 10) % len(S.CHEERS)])
        self.tally = [[label, v, 0] for label, v in lines]
        self.tally_i = 0
        self.tally_t = 0.0

    def next_stage(self):
        n = self.stage_n
        if n >= STAGES:
            self.hype.jackpot(1000000, "ALL 200 BEDS!")
            self.end_game(True, "ALL 200 STAGES!", delay=3.5)
            return
        if is_boss(n) or is_bonus(n):
            self.state = "upgrade"
            self.pick_upgrade(UPGRADE_POOL, self.ups, self.took_upgrade,
                              title="BOSS REWARD!" if is_boss(n) else "POWER UP!")
        else:
            self.begin_stage(n + 1)

    def took_upgrade(self, uid):
        if uid is None:
            self.lives += 1
            self.hype.banner("1UP!", "EVERYTHING IS MAXED", color="pink", dur=1.4, sound="extra")
        else:
            self.ups[uid] = self.ups.get(uid, 0) + 1
            if uid == "milk":
                self.lives += 1
                self.app.audio.play("extra")
        self.begin_stage(self.stage_n + 1)

    def check_life(self):
        while self.score >= LIFE_STEP * self.life_k * (self.life_k + 1) // 2:
            self.life_k += 1
            self.lives += 1
            self.hype.banner("1UP!", "EXTRA LIFE", color="pink", dur=1.4, sound="extra")
            self.hype.shower(20, "hearts")

    # ================================================================ the piece
    def cells(self, p=None, x=None, y=None, rot=None):
        p = p or self.piece
        return K.piece_cells(p["x"] if x is None else x, p["y"] if y is None else y,
                             p["rot"] if rot is None else rot, p["b"] == 0)

    def spawn(self):
        if K.topped(self.grid):
            if self.guard > 0:
                self.guard_save()
                return
            self.fail_stage("THE BED IS FULL!")
            return
        a, b = self.queue.pop(0)
        self.queue.append(self.gen_piece())
        self.piece = {"x": K.SPAWN_X, "y": 0, "rot": 0, "a": a, "b": b}
        self.piece_id += 1
        self.fall_t = self.lock_t = 0.0
        self.lock_resets = 0
        self.phase = "piece"

    def guard_save(self):
        """NIGHT LIGHT upgrade: Poppy shoos the top four rows away instead of losing the stage."""
        self.guard -= 1
        for y in range(4):
            for x in range(COLS):
                if self.grid[y][x]:
                    self.parts.burst(BX + x * CELL + 6, BY + y * CELL + 6, 4, ("yellow", "white"), 60, 0.5)
                    self.grid[y][x] = 0
        self.hype.banner("NIGHT LIGHT!", "POPPY SAVES THE BED", color="orange", dur=1.4, sound="powerup")
        self.hype.flash("yellow", 0.25)
        self.mood("cheer")
        self.phase = "wait"
        self.phase_t = 0.4

    def try_move(self, dx, dy):
        p = self.piece
        if K.fits(self.grid, self.cells(x=p["x"] + dx, y=p["y"] + dy)):
            p["x"] += dx
            p["y"] += dy
            return True
        return False

    def grounded(self):
        p = self.piece
        return not K.fits(self.grid, self.cells(y=p["y"] + 1))

    def bump_lock(self):
        if self.lock_resets < 12:
            self.lock_t = 0.0
            self.lock_resets += 1

    def rotate(self, d):
        p = self.piece
        if p["b"] == 0:
            return
        for nr in ((p["rot"] + d) % 4, (p["rot"] + 2) % 4):      # quick turn when boxed in
            sx, sy = K.DIRS[nr]
            for kx, ky in ((0, 0), (-sx, -sy if sy > 0 else 0)):
                if K.fits(self.grid, self.cells(x=p["x"] + kx, y=p["y"] + ky, rot=nr)):
                    p["x"] += kx
                    p["y"] += ky
                    p["rot"] = nr
                    self.app.audio.play("rotate")
                    self.bump_lock()
                    return

    def hard_drop(self):
        p = self.piece
        d = K.drop_y(self.grid, p["x"], p["y"], p["rot"], p["b"] == 0) - p["y"]
        p["y"] += d
        self.add(d * 2)
        self.fall_t = 0.0
        self.lock()

    def lock(self):
        p = self.piece
        codes = [p["a"]] if p["b"] == 0 else [p["a"], p["b"]]
        cc = [(x, y, codes[i]) for i, (x, y) in enumerate(self.cells())]
        order = sorted(cc, key=lambda c: -c[1])          # K.place lands the lower kitten first
        landed = K.place(self.grid, cc)
        self.piece = None
        self.dropped = True
        self.app.audio.play("lock")
        self.landed = []
        for (x, y, code), (_, sy, _) in zip(landed, order):
            if y < 0:                                     # no room left in that column: it hops back out
                self.parts.burst(BX + x * CELL + 6, BY - 4, 8, ("white", "lavender"), 60, 0.5)
                self.floats.add(BX + x * CELL + 6, BY - 12, "HOP!", "lavender")
                continue
            self.off[y][x] = min(0.0, float((sy - y) * CELL))
            if code in (K.YARN, K.MOUSE):
                self.landed.append((x, y, code))
        self.phase = "settle"

    # ================================================================ resolution
    def move_cells(self, moves, extra=0.0):
        for x, fy, ty in moves:
            self.off[ty][x] = (fy - ty) * CELL - extra
            self.mood_t[ty][x] = self.mood_t[fy][x]
            self.mood_t[fy][x] = 0.0
            self.off[fy][x] = 0.0

    def falling(self):
        return any(self.off[y][x] < 0 for y in range(ROWS) for x in range(COLS))

    def after_settle(self):
        # specials that just landed act first
        while self.landed:
            x, y, code = self.landed.pop(0)
            if self.grid[y][x] != code:
                continue
            if code == K.YARN:
                k = K.yarn_color(self.grid, x, y)
                self.grid[y][x] = 0
                self.parts.burst(BX + x * CELL + 6, BY + y * CELL + 6, 14, ("pink", "hotpink", "white"), 80, 0.6)
                if k:
                    cells = [(xx, yy) for yy in range(ROWS) for xx in range(COLS) if K.kcolor(self.grid[yy][xx]) == k]
                    self.hype.banner("YARN BALL!", f"{A.KIT_NAMES[k]} KITTENS NAP", color="pink", dur=1.2, scale=1)
                    self.start_pop([cells])
                    return
                self.app.audio.play("pop")
            else:
                gone = K.mouse_cells(self.grid, x, y, 1 + (1 if self.up("mouse") >= 2 else 0))
                self.grid[y][x] = 0
                self.app.audio.play("tin")
                self.floats.add(BX + x * CELL + 6, BY + y * CELL - 4, "SQUEAK!", "yellow")
                for jx, jy in gone:
                    self.grid[jy][jx] = 0
                    self.parts.burst(BX + jx * CELL + 6, BY + jy * CELL + 6, 6, ("white", "cream", "lavender"), 70, 0.5)
                    self.add(30 * self.lv())
                if gone:
                    self.hype.hit(1)
            self.move_cells(K.apply_gravity(self.grid))
            if self.falling():
                return
        groups = K.find_groups(self.grid)
        if groups:
            self.start_pop(groups)
            return
        self.end_chain()

    def start_pop(self, groups):
        self.chain += 1
        ch = self.chain
        cells = [p for gr in groups for p in gr]
        self.popping = [(x, y, self.grid[y][x]) for x, y in cells]
        self.pop_t = 0.0
        self.phase = "pop"
        n = len(cells)
        L = self.lv()
        pts = int(K.step_points(groups, ch, self.grid) * (1 + 0.25 * self.up("lullaby")) * (1 + 0.1 * self.tier))
        cx = sum(x for x, _ in cells) / n
        cy = sum(y for _, y in cells) / n
        px, py = BX + cx * CELL + 6, BY + cy * CELL
        got = self.add(pts, px, py, "white" if ch < 2 else "yellow")
        self.kits += n
        self.best_chain = max(self.best_chain, ch)
        stars = sum(1 for _, _, c in self.popping if c & K.STAR)
        golds = sum(1 for _, _, c in self.popping if c & K.GOLD)
        if stars:
            self.rescued += stars
            self.hype.banner("STAR TUCKED IN!" if stars == 1 else f"{stars} STARS TUCKED IN!", color="yellow",
                             dur=1.0, scale=1, sound="bonus")
            self.add(1000 * L * stars)
        if golds:
            self.hype.jackpot(5000 * L, "GOLDEN KITTEN!")
            self.mood("cheer", 2.0)
        if self.st["k"] == "snack" or self.st["k"] == "domino":
            gain = n * (ch if self.st["k"] == "domino" else 1)
            self.coins += gain
            for x, y in cells[:8]:
                self.coin_fx.append([BX + x * CELL + 2, BY + y * CELL + 3, random.uniform(-30, 30), -70.0, 1.0])
            self.app.audio.play("coin")
        self.hype.hit(len(groups), fever=0.045 * (1 + 0.35 * self.up("purr")) * min(3, ch))
        # naps at the rival
        if self.foe and not self.foe["sleep"]:
            power = int(K.step_power(groups, ch) * (1 + 0.25 * self.up("catnip") + 0.05 * self.tier) *
                        (2 if self.hype.fever_on else 1))
            self.send_naps(power, px, py)
        # feedback
        self.app.audio.play("pop" if ch == 1 else "line" if ch < 4 else "quad")
        if ch >= 2:
            word = CHAIN_WORDS[min(ch, len(CHAIN_WORDS) - 1)]
            self.hype.banner(f"{ch} CHAIN!", word, color="peach" if ch < 4 else "hotpink", dur=1.0,
                             rainbow=ch >= 5, scale=2 if ch >= 3 else 1)
            self.mood("happy", 1.4)
            if ch >= 4:
                self.hype.flash("white", 0.12)
                self.app.shake(2 + min(4, ch - 3), 0.3)
            if ch >= 6:
                self.hype.slowmo(0.4, 0.6)
                self.hype.shower(30 + ch * 6, "stars")
                self.say("WHAT A TUMBLE!!")
            if ch >= 8:
                self.hype.jackpot(20000 * L, f"{ch} CHAIN!!")
        else:
            self.mood("happy", 0.7)
        del got

    def finish_pop(self):
        cells = [(x, y) for x, y, _ in self.popping]
        for jx, jy in K.junk_hits(self.grid, cells):
            c = self.grid[jy][jx]
            gone = K.hit_junk(self.grid, jx, jy)
            self.parts.burst(BX + jx * CELL + 6, BY + jy * CELL + 6, 6 if gone else 3,
                             ("white", "cream") if c == K.PILLOW else ("gray", "white"), 60, 0.5)
            if gone:
                self.add(20 * self.lv())
        for x, y, code in self.popping:
            self.grid[y][x] = 0
            self.mood_t[y][x] = 0.0
            self.parts.burst(BX + x * CELL + 6, BY + y * CELL + 6, 5, (A.KIT_COAT[code & 7], "white", "lavender"), 55, 0.6)
        self.popping = []
        self.move_cells(K.apply_gravity(self.grid))
        self.phase = "settle"

    def end_chain(self):
        st = self.st
        if self.chain:
            empty = K.count_cells(self.grid, lambda c: c != 0) == 0
            if empty:
                self.all_clears += 1
                self.hype.banner("ALL TUCKED IN!", f"+{5000 * self.lv() * self.hype.mult}", rainbow=True, dur=1.8,
                                 sound="extra")
                self.add(5000 * self.lv())
                self.hype.shower(50, "hearts")
                self.hype.flash("pink", 0.25)
                if self.foe and not self.foe["sleep"]:
                    self.send_naps(30, BX + BW // 2, BY + BH // 2)
            if st["k"] == "domino" and (self.chain >= 2 or empty):
                self.su_i += 1
                if self.su_i < len(st["setups"]):
                    self.hype.banner("NEXT DOMINO!", color="mint", dur=0.9, scale=1)
                    su = st["setups"][self.su_i]
                    self.queue = [(su["c"], su["c"]) for _ in range(4)]
                    self.chain = 0
                    self.drop_in(su["rows"])
                    return
                self.chain = 0
                self.stage_clear()
                return
        self.chain = 0
        if self.state != "play":
            return
        if self.goal_done() and st["k"] not in ("storm", "snack", "domino"):
            self.stage_clear()
            return
        if st["k"] == "trigger" and self.dropped:        # missed the spot: Poppy makes the domino bed again
            self.dropped = False
            self.missed = True
            self.hype.banner("MISSED!", "POPPY REMAKES THE BED", color="peach", dur=1.2, scale=1)
            self.say("ALMOST! TRY ANOTHER SPOT")
            self.drop_in(st["setups"][0]["rows"])
            return
        if self.pend_rise and self.raise_bed():
            return
        if self.pending_total() > 0:
            self.drop_garbage()
            return
        self.phase = "wait"
        self.phase_t = 0.05

    def drop_in(self, rows):
        """A fresh prebuilt bed tumbles in from above."""
        self.load_rows(rows)
        for y in range(ROWS):
            for x in range(COLS):
                if self.grid[y][x]:
                    self.off[y][x] = -(BH + 20 + (ROWS - y) * 4)
        self.phase = "settle"

    def settle_visual(self, dt):
        """Outside play (clear, tally, a rival dozing off) kittens still finish falling."""
        for y in range(ROWS):
            for x in range(COLS):
                if self.off[y][x] < 0:
                    self.off[y][x] = min(0.0, self.off[y][x] + FALL * dt)

    # ================================================================ pillows, grandpas, grumpy kittens
    def drop_garbage(self):
        items = []
        n = min(30, self.pend[0])
        self.pend[0] -= n
        items += [K.PILLOW] * n
        g = min(3, self.pend[1])
        self.pend[1] -= g
        items += [K.GRANDPA] * g
        k = min(12, self.pend[2])
        self.pend[2] -= k
        items += [1 + self.frng.below(self.st["ncol"]) for _ in range(k)]
        # full rows across the bed, then the rest in random columns
        rows = []
        while len(items) >= COLS:
            rows.append(items[:COLS])
            items = items[COLS:]
        if items:
            cols = list(range(COLS))
            row = [0] * COLS
            for code in items:
                i = self.frng.below(len(cols))
                row[cols.pop(i)] = code
            rows.append(row)
        for r_i, row in enumerate(rows):
            for x, code in enumerate(row):
                if not code:
                    continue
                h = K.col_height(self.grid, x)
                ty = ROWS - 1 - h
                if ty < 0:
                    continue
                self.grid[ty][x] = code
                self.off[ty][x] = -((ty + 2 + r_i) * CELL + 8)
                if K.is_kitten(code):
                    self.mood_t[ty][x] = 2.5
        self.app.audio.play("boom" if len(rows) > 1 else "hurt")
        self.app.shake(2 + min(3, len(rows)), 0.25)
        self.mood("hurt", 1.2)
        self.phase = "settle"

    def raise_bed(self):
        """BED QUAKE / RISING BED: a row of pillows pushes up from below (one gap)."""
        self.pend_rise = max(0, self.pend_rise - 1)
        if any(self.grid[0]):
            self.fail_stage("PUSHED OUT OF BED!")
            return True
        gap = self.frng.below(COLS)
        self.grid = self.grid[1:] + [[0 if x == gap else K.PILLOW for x in range(COLS)]]
        self.off = self.off[1:] + [[0.0] * COLS]
        self.mood_t = self.mood_t[1:] + [[0.0] * COLS]
        for x in range(COLS):
            if x != gap:
                self.off[ROWS - 1][x] = 0.0
        if self.piece:
            if not K.fits(self.grid, self.cells()):
                self.piece["y"] -= 1
        self.bed_kick = 0.25
        self.app.audio.play("hurt")
        self.app.shake(3, 0.3)
        self.mood("hurt")
        # the new row may complete nothing (pillows), but the stack may have been pushed into a group: settle
        if not self.piece:
            self.phase = "settle"
        return not self.piece

    # ================================================================ rivals and bosses
    def send_naps(self, power, x, y):
        f = self.foe
        if power <= 0:
            return
        blocked = 0
        for i, cost in ((0, 1), (2, 1), (1, 3)):          # cancel pillows, grumpies, then grandpas first
            while power >= cost and self.pend[i] > 0:
                self.pend[i] -= 1
                power -= cost
                blocked += 1
        if blocked:
            self.floats.add(BX + BW // 2, BY - 18, f"BLOCK {blocked}", "mint")
        if power <= 0:
            return
        self.shots.append([x, y, 0.0, power])

    def hit_foe(self, dmg):
        f = self.foe
        if not f or f["sleep"] or self.state != "play":
            return
        f["hp"] = max(0, f["hp"] - dmg)
        f["hit"] = 0.3
        self.floats.add(FOE_X + random.randint(-12, 12), FOE_Y - 30, f"-{dmg}", "red")
        self.parts.burst(FOE_X, FOE_Y, 6 + min(20, dmg // 4), ("white", "lavender", "yellow"), 80, 0.6)
        self.hype.hitstop(0.03 + min(0.08, dmg / 600))
        if dmg >= 40:
            self.hype.flash("white", 0.12)
            self.app.shake(3, 0.25)
        if f["hp"] <= 0:
            self.foe_down()
            return
        frac = f["hp"] / f["max"]
        if f["phase"] == 1 and frac <= 0.5:
            f["phase"] = 2
            self.hype.banner("GRRR!", f"{self.foe_name()} IS WIDE AWAKE", color="red", dur=1.2, scale=1)
        if f["phase"] == 2 and frac <= 0.2 and f["boss"] and self.tier >= 3:
            f["phase"] = 3
            self.hype.banner("LAST YAWN!", color="red", dur=1.2)

    def foe_down(self):
        f = self.foe
        f["sleep"] = True
        f["tele"] = None
        self.pend = [0, 0, 0]
        if self.popping:
            self.finish_pop()
        self.state = "bossdown" if f["boss"] else "foedown"
        self.state_t = 0.0
        self.piece = None
        if f["boss"]:
            self.app.audio.stop_music()
            self.app.audio.play("bossdown")
            self.hype.slowmo(0.3, 1.4)
            self.hype.flash("white", 0.4)
            self.hype.shower(120, "stars")
            self.app.shake(6, 0.8)
            self.hype.banners = []
            self.hype.banner("BOSS ASLEEP!", self.foe_name(), rainbow=True, dur=2.4)
            self.add(10000 * self.lv())
            self.say("SWEET DREAMS, GRUMPY!")
        else:
            self.app.audio.play("win")
            self.hype.banner("SNOOZED!", f"{self.foe_name()} IS ASLEEP", color="lime", dur=1.4)
            self.hype.shower(40, "stars")
        self.mood("cheer", 3.0)

    def tick_foe(self, dt):
        f = self.foe
        f["hit"] = max(0.0, f["hit"] - dt)
        if f["sleep"]:
            return
        if f["tele"] is not None:
            f["tele"][1] -= dt
            if f["tele"][1] <= 0:
                atk = f["tele"][0]
                f["tele"] = None
                self.foe_attack(atk)
                if f["phase"] >= 3 and self.frng.below(2) == 0:
                    f["t"] = 1.2
            return
        f["t"] -= dt
        if f["t"] <= 0:
            f["t"] = f["every"] * (0.75 if f["phase"] >= 2 else 1.0)
            atk = f["atk"][0] if self.frng.below(100) < 45 else f["atk"][self.frng.below(len(f["atk"]))]
            f["tele"] = [atk, max(1.0, 1.8 - self.tier * 0.04)]
            self.app.audio.play("trap")

    def foe_attack(self, atk):
        f = self.foe
        p = f["pow"] + (2 if f["phase"] >= 3 else 0)
        fort = max(0.25, 1 - 0.25 * self.up("fort")) * self.foe_mult
        self.hype.banner(S.ATTACK_NAMES[atk] + "!", color="red", dur=0.9, scale=1)
        self.shots.append([FOE_X, FOE_Y - 10, 0.0, -1])          # a pillow flying back at the bed (visual)
        if atk == "toss":
            self.pend[0] += max(1, int(p * fort))
        elif atk == "grandpa":
            self.pend[1] += max(1, int((1 + p // 6) * min(1.0, fort + 0.25)))
        elif atk == "grumpy":
            self.pend[2] += max(2, int((4 + p // 2) * fort))
        elif atk == "fog":
            self.fog_t = 5.0 + p * 0.3
            self.app.audio.play("bubble")
        elif atk == "zoom":
            self.zoom_t = 4.0 + p * 0.2
            self.app.audio.play("powerup")
        elif atk == "dizzy":
            self.dizzy_t = 4.0 + p * 0.2
            self.app.audio.play("powerup")
        elif atk == "rise":
            self.pend_rise += 1 + (1 if p >= 10 else 0)

    # ================================================================ update
    def tick(self, dt):
        if self.poppy_mood[1] > 0:
            self.poppy_mood[1] -= dt
            if self.poppy_mood[1] <= 0:
                self.poppy_mood[0] = "idle"
        if self.talk:
            self.talk[1] -= dt
            if self.talk[1] <= 0:
                self.talk = None
        self.bed_kick = max(0.0, self.bed_kick - dt)
        for key in list(self.squish):
            self.squish[key] -= dt
            if self.squish[key] <= 0:
                del self.squish[key]
        for y in range(ROWS):
            for x in range(COLS):
                if self.mood_t[y][x] > 0:
                    self.mood_t[y][x] -= dt
        self.tick_shots(dt)
        self.tick_coins(dt)
        if self.state != "play":
            self.settle_visual(dt)
        if self.hype.fever_on != self.fever_was and self.state == "play" and not self.bonus():
            self.fever_was = self.hype.fever_on
            self.song = "fever" if self.fever_was else ("boss" if self.st["k"] == "boss" else
                                                         "kp_duel" if self.st["k"] == "duel" else "kp_nap")
            self.app.audio.music(self.song)
        if self.ending is not None:
            return
        self.state_t += dt
        s = self.state
        inp = self.app.input
        if s == "warning":
            if self.state_t > 2.6:
                self.state = "intro"
                self.state_t = 0.0
            return
        if s == "intro":
            if self.state_t > 3.2 or (self.state_t > 0.5 and inp.hit("a", "b", "up", "y")):
                self.start_play()
            return
        if s == "fail":
            if self.state_t > 1.8:
                if self.lives <= 0:
                    self.end_game(False, f"STAGE {self.stage_n}")
                else:
                    self.begin_stage(self.stage_n, retry=True)
            return
        if s in ("bossdown", "foedown"):
            if self.foe["boss"] and self.state_t > 0.5 and int(self.state_t * 10) % 2 == 0:
                self.parts.burst(FOE_X + random.randint(-16, 16), FOE_Y + random.randint(-14, 14), 8,
                                 ("lavender", "white", "yellow"), 90, 0.7)
            if self.state_t > (2.4 if self.foe["boss"] else 1.3):
                self.stage_clear()
            return
        if s == "clear":
            if self.state_t > 1.3:
                self.state = "tally"
                self.state_t = 0.0
            return
        if s == "tally":
            self.tick_tally(dt)
            return
        if s != "play":
            return
        self.tick_play(dt)

    def tick_tally(self, dt):
        self.tally_t += dt
        if self.tally_i < len(self.tally):
            line = self.tally[self.tally_i]
            step = max(1, line[1] // 24)
            add = min(step, line[1] - line[2])
            line[2] += add
            self.score += add
            if self.tally_t > 0.06 and add:
                self.tally_t = 0.0
                self.app.audio.play("move")
            if line[2] >= line[1]:
                self.tally_i += 1
                self.tally_t = 0.0
                self.app.audio.play("coin" if line[1] else "move")
            self.check_life()
            return
        if (self.tally_t > 0.6 and self.app.input.hit("a", "b", "up", "y")) or self.tally_t > 3.0:
            self.next_stage()

    def tick_play(self, dt):
        st = self.st
        self.stime += dt
        self.fog_t = max(0.0, self.fog_t - dt)
        self.zoom_t = max(0.0, self.zoom_t - dt)
        self.dizzy_t = max(0.0, self.dizzy_t - dt)
        if self.phase in ("settle", "pop") or self.chain:
            self.hype.keep_combo()
        self.check_life()
        if st["k"] in ("storm", "snack", "domino") and self.stime >= st["lim"]:
            if self.phase in ("piece", "wait"):
                self.stage_clear()
                if st["k"] == "storm":
                    self.hype.banner("MORNING!", "THE STORM IS OVER", color="yellow", dur=1.4)
                return
        if st["rain"]:
            self.rain_t += dt
            if self.rain_t >= st["rain"]:
                self.rain_t = 0.0
                self.pend[0] += max(1, int(st["rainN"] * max(0.25, 1 - 0.25 * self.up("fort"))))
                if self.tier >= 6 and self.frng.below(4) == 0:
                    self.pend[1] += 1
                self.app.audio.play("trap")
        if st["rise"]:
            self.rise_t += dt
            if self.rise_t >= st["rise"]:
                self.rise_t = 0.0
                self.pend_rise += 1
        if self.foe:
            self.tick_foe(dt)
            if self.state != "play":
                return
        if self.phase == "wait":
            self.phase_t -= dt
            if self.phase_t <= 0:
                self.spawn()
            return
        if self.phase == "settle":
            moving = False
            for y in range(ROWS):
                for x in range(COLS):
                    o = self.off[y][x]
                    if o < 0:
                        o += FALL * dt
                        if o >= 0:
                            o = 0.0
                            self.squash(x, y)
                        else:
                            moving = True
                        self.off[y][x] = o
            if not moving:
                self.after_settle()
            return
        if self.phase == "pop":
            self.pop_t += dt
            if self.pop_t >= POP_TIME:
                self.finish_pop()
            return
        if self.phase == "piece":
            if self.pend_rise and self.raise_bed():
                return
            self.play_input(dt)

    def squash(self, x, y):
        self.squish[(x, y)] = 0.12

    def play_input(self, dt):
        inp = self.app.input
        p = self.piece
        if p is None:
            return
        if inp.hit("up", "y"):
            self.hard_drop()
            return
        if inp.hit("a"):
            self.rotate(1)
        elif inp.hit("b"):
            self.rotate(-1)
        d = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        if self.dizzy_t > 0:
            d = -d
        if d != self.das_dir:
            self.das_dir, self.das_t = d, 0.0
            if d and self.try_move(d, 0):
                self.app.audio.play("move")
                self.bump_lock()
        elif d:
            self.das_t += dt
            if self.das_t > 0.17:
                self.das_t -= 0.06
                if self.try_move(d, 0):
                    self.bump_lock()
        g = self.gravity()
        soft = inp.down("down")
        if soft:
            g = min(g, 0.035)
        self.fall_t += dt
        while self.fall_t >= g:
            self.fall_t -= g
            if self.try_move(0, 1):
                if soft:
                    self.add(1)
            else:
                self.fall_t = 0.0
                break
        if self.grounded():
            self.lock_t += dt
            if self.lock_t >= (0.08 if soft else LOCK_DELAY):
                self.lock()
        else:
            self.lock_t = 0.0

    def tick_shots(self, dt):
        for sh in self.shots:
            sh[2] += dt * 2.2
            if sh[3] > 0 and sh[2] >= 1.0:
                self.hit_foe(sh[3])
        self.shots = [sh for sh in self.shots if sh[2] < 1.0]

    def tick_coins(self, dt):
        for c in self.coin_fx:
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            c[3] += 160 * dt
            c[4] -= dt
        self.coin_fx = [c for c in self.coin_fx if c[4] > 0]

    # ================================================================ drawing
    def render(self, s):
        A.draw_bg(s, self.theme, self.t)
        self.draw_bed(s)
        self.draw_left(s)
        self.draw_right(s)
        self.draw_hud(s)
        self.parts.draw(s)
        self.floats.draw(s)
        for x, y, _, _, life in self.coin_fx:
            if life > 0.25 or int(life * 30) % 2:
                s.blit(sprite("kp_fish"), (int(x), int(y)))
        if self.state == "warning":
            self.draw_warning(s)
        elif self.state == "intro":
            self.draw_intro(s)
        elif self.state == "tally":
            self.draw_tally(s)

    def draw_bed(self, s):
        kick = int(math.sin(self.t * 60) * 2) if self.bed_kick > 0 else 0
        by = BY + kick
        A.bed(s, BX, by, BW, BH, self.theme)
        # danger mark over the spawn column
        hs = K.col_height(self.grid, K.SPAWN_X)
        if hs >= ROWS - 3 and int(self.t * 4) % 2:
            x0 = BX + K.SPAWN_X * CELL
            pygame.draw.line(s, col("red"), (x0 + 2, by + 2), (x0 + 9, by + 9), 2)
            pygame.draw.line(s, col("red"), (x0 + 9, by + 2), (x0 + 2, by + 9), 2)
        worried = max(K.col_height(self.grid, x) for x in range(COLS)) >= ROWS - 2
        popset = {(x, y) for x, y, _ in self.popping}
        fever = self.hype.fever_on
        sq = self.squish
        for y in range(ROWS):
            for x in range(COLS):
                c = self.grid[y][x]
                if not c or (x, y) in popset:
                    continue
                px, py = BX + x * CELL, by + y * CELL + int(self.off[y][x])
                if K.is_kitten(c):
                    m = 0
                    if self.mood_t[y][x] > 0:
                        m = 5
                    elif fever or self.state in ("clear", "tally"):
                        m = 3
                    elif worried:
                        m = 4
                    elif int(self.t * 2 + x * 7 + y * 13) % 23 == 0:
                        m = 1
                    if (x, y) in sq:
                        py += 1
                    A.kitten(s, px, py, c, m, self.t)
                else:
                    A.cell(s, px, py, c, 0, self.t)
        # paws holding between settled same-colour neighbours
        for y in range(ROWS):
            for x in range(COLS):
                k = K.kcolor(self.grid[y][x])
                if not k or self.off[y][x] < 0 or (x, y) in popset:
                    continue
                if x + 1 < COLS and K.kcolor(self.grid[y][x + 1]) == k and self.off[y][x + 1] >= 0 and \
                        (x + 1, y) not in popset:
                    A.link(s, BX + x * CELL, by + y * CELL, k, True)
                if y + 1 < ROWS and K.kcolor(self.grid[y + 1][x]) == k and self.off[y + 1][x] >= 0 and \
                        (x, y + 1) not in popset:
                    A.link(s, BX + x * CELL, by + y * CELL, k, False)
        if self.popping:
            f = min(1.0, self.pop_t / POP_TIME)
            for x, y, code in self.popping:
                A.curl(s, BX + x * CELL, by + y * CELL, code, f)
        p = self.piece
        if p is not None and self.state == "play":
            g = self.gravity()
            frac = 0.0 if self.grounded() else min(1.0, self.fall_t / g) * CELL
            codes = [p["a"]] if p["b"] == 0 else [p["a"], p["b"]]
            if self.guide or self.st["k"] in ("trigger", "domino"):
                self.draw_guide(s, by, codes)
            for i, (x, y) in enumerate(self.cells()):
                A.cell(s, BX + x * CELL, by + y * CELL + int(frac), codes[i], 0, self.t)
        if "dark" in self.st["mods"] and self.state == "play":
            self.draw_dark(s, by)
        if self.fog_t > 0:
            self.draw_fog(s, by)
        k = self.st["k"]
        if k in ("trigger", "domino") and self.state == "play" and self.piece is not None and \
                (k == "domino" or self.tier < 3 or self.missed):          # the glow: drop the pair here
            su = self.st["setups"][min(self.su_i, len(self.st["setups"]) - 1)]
            gx = BX + su["x"] * CELL
            hy = by + (ROWS - K.col_height(self.grid, su["x"])) * CELL
            if int(self.t * 5) % 2:
                pygame.draw.rect(s, col("yellow"), (gx, hy - 24, CELL, 24), 1)
            draw_text(s, "`", gx + 3, hy - 34 + int(math.sin(self.t * 6) * 2), "yellow", shadow="ink")
        self.draw_pending(s)

    def draw_guide(self, s, by, codes):
        p = self.piece
        g = [row[:] for row in self.grid]
        cc = [(x, y, codes[i]) for i, (x, y) in enumerate(self.cells())]
        for x, y, code in K.place(g, cc):
            if y < 0:
                continue
            c = col("white") if code & 8 else col(A.KIT_COAT[code & 7])
            px, py = BX + x * CELL, by + y * CELL
            s.fill(c, (px + 3, py + 3, 6, 1))
            s.fill(c, (px + 3, py + 8, 6, 1))
            s.fill(c, (px + 3, py + 3, 1, 6))
            s.fill(c, (px + 8, py + 3, 1, 6))
        del p

    def draw_dark(self, s, by):
        """LIGHTS OUT: only the lantern light around the falling pair shows the bed."""
        p = self.piece
        if p is not None:
            cx, cy = BX + p["x"] * CELL + 6, by + p["y"] * CELL + 6
        else:
            cx, cy = BX + BW // 2, by + BH // 2
        r = 34
        shade = col("black", 225)
        ov = pygame.Surface((BW, BH), pygame.SRCALPHA)
        for yy in range(BH):
            dy = yy + by - cy
            if abs(dy) >= r:
                ov.fill(shade, (0, yy, BW, 1))
                continue
            half = int(math.sqrt(r * r - dy * dy))
            x0, x1 = cx - half - BX, cx + half - BX
            if x0 > 0:
                ov.fill(shade, (0, yy, x0, 1))
            if x1 < BW:
                ov.fill(shade, (x1, yy, BW - x1, 1))
        s.blit(ov, (BX, by))

    def draw_fog(self, s, by):
        """FLUFF FOG: a lavender cloud over the top of the bed (thick at the top, puffy lower edge)."""
        fh = BH * 2 // 3
        ov = pygame.Surface((BW, fh + 12), pygame.SRCALPHA)
        for yy in range(0, fh, 3):
            ov.fill(col("lavender", 215 - yy * 100 // fh), (0, yy, BW, 3))
        for i in range(5):
            pygame.draw.circle(ov, col("lavender", 120), (i * 14 + 8 + int(math.sin(self.t * 2 + i) * 1), fh + 5), 5)
        s.blit(ov, (BX, by))

    def draw_pending(self, s):
        """Pillows, grandpas and grumpy kittens on their way (shown above the bed)."""
        if self.pending_total() <= 0 and not (self.foe and self.foe["tele"]):
            return
        x = BX
        y = BY - 14
        icons = []
        n = self.pend[0]
        icons += ["big"] * (n // 6) + ["small"] * (n % 6)
        icons += ["grandpa"] * self.pend[1]
        icons += ["grumpy"] * self.pend[2]
        for ic in icons[:12]:
            if ic == "big":
                s.blit(sprite("kp_pillow"), (x, y - 2))
                x += 12
            elif ic == "small":
                pygame.draw.rect(s, col("cream"), (x, y + 3, 6, 5), border_radius=2)
                s.fill(col("white"), (x + 1, y + 4, 4, 2))
                x += 7
            elif ic == "grandpa":
                s.blit(sprite("kp_grandpa"), (x, y - 2))
                x += 12
            else:
                pygame.draw.circle(s, col("red"), (x + 3, y + 5), 3)
                x += 7
        if len(icons) > 12:
            draw_text(s, f"+{len(icons) - 12}", x + 1, y + 2, "red", shadow="ink")

    def draw_hud(self, s):
        band = pygame.Surface((W, 11), pygame.SRCALPHA)
        band.fill((12, 8, 24, 170))
        s.blit(band, (0, 0))
        draw_text(s, f"SCORE {self.score:07d}", 4, 2, "yellow", shadow=None)
        draw_text(s, f"HI {max(self.best, self.score):07d}", 104, 2, "lavender", shadow=None)
        draw_text(s, f"STAGE {self.stage_n}", 196, 2, "white", shadow=None)
        self.hearts(s, 262, 2, self.lives, 6)

    def draw_left(self, s):
        k = self.st["k"]
        hue = self.theme[1]
        panel(s, (4, 14, 112, 50), fill="night", border=hue)
        draw_text(s, S.KIND_TITLE[k], 60, 18, self.theme[2], align="center")
        goal, prog, frac = self.progress()
        draw_text(s, goal, 60, 29, "white", align="center", shadow=None)
        s.fill(col("darkgray"), (10, 41, 100, 6))
        w = int(100 * max(0.0, min(1.0, frac)))
        s.fill(col("lime" if frac >= 1 else hue), (10, 41, w, 6))
        s.fill(col("white"), (10, 41, w, 1))
        draw_text(s, prog, 60, 51, "yellow" if frac >= 1 else "lavender", align="center", shadow=None)
        # purr meter
        panel(s, (4, 67, 112, 20), fill="night", border="pink" if not self.hype.fever_on else rainbow(0, self.t))
        draw_text(s, "PURR", 9, 74, "pink", shadow=None)
        fv = 1.0 if self.hype.fever_on else self.hype.fever
        if self.hype.fever_on:
            fv = self.hype.fever_t / self.hype.FEVER_TIME if self.st["k"] != "snack" else \
                max(0.0, 1 - self.stime / max(1, self.st["lim"]))
        s.fill(col("darkgray"), (36, 73, 74, 8))
        for i in range(int(74 * max(0.0, min(1.0, fv)))):
            s.fill(col(rainbow(i // 6, self.t) if self.hype.fever_on else "hotpink"), (36 + i, 73, 1, 8))
        for i in range(1, 4):
            s.fill(col("night"), (36 + i * 74 // 4, 73, 1, 8))
        # status chips
        y = 92
        chips = []
        if self.zoom_t > 0:
            chips.append(("ZOOMIES!", "orange"))
        if self.dizzy_t > 0:
            chips.append(("DIZZY!", "lime"))
        if self.fog_t > 0:
            chips.append(("FOGGY!", "lavender"))
        if self.guard:
            chips.append((f"NIGHT LIGHT X{self.guard}", "orange"))
        for m in self.st["mods"]:
            chips.append((S.MODS[m], "peach"))
        for text, c in chips[:2]:
            draw_text(s, text, 8, y, c if not text.endswith("!") or int(self.t * 6) % 2 else "white", shadow="ink")
            y += 9
        # Poppy on her rug
        pygame.draw.ellipse(s, col(self.theme[2]), (14, 186, 64, 10))
        pygame.draw.ellipse(s, col(lerp_col("black", self.theme[2], 0.6)), (20, 188, 52, 6), 1)
        look = 0
        if self.piece:
            look = max(-2, min(2, self.piece["x"] - 2))
        m = self.poppy_mood[0]
        if m == "idle":
            if self.state in ("clear", "tally"):
                m = "cheer"
            elif self.state == "fail":
                m = "hurt"
            elif self.piece and self.das_dir:
                m = "move"
            elif max(K.col_height(self.grid, x) for x in range(COLS)) >= ROWS - 2:
                m = "hurt"
        A.poppy(s, 46, 190, self.t, m, look)
        if self.talk:
            self.draw_talk(s, self.talk[0])

    def draw_talk(self, s, text):
        """Poppy's speech bubble above her head (at most 2 lines of 17)."""
        lines = A.wrap(text, 17)[:2]
        w = max(text_width(ln) for ln in lines) + 8
        h = len(lines) * 9 + 4
        x, y = max(5, 60 - w // 2), 136 - h
        panel(s, (x, y, w, h), fill="white", border="black", radius=3, shadow=False)
        pygame.draw.polygon(s, col("white"), [(50, y + h - 1), (56, y + h - 1), (48, y + h + 5)])
        pygame.draw.line(s, col("black"), (48, y + h + 5), (50, y + h - 1))
        pygame.draw.line(s, col("black"), (48, y + h + 5), (56, y + h - 1))
        for i, ln in enumerate(lines):
            draw_text(s, ln, x + 4, y + 3 + i * 9, "ink", shadow=None)

    def draw_right(self, s):
        hue = self.theme[1]
        panel(s, (206, 14, 54, 62), fill="night", border=hue)
        draw_text(s, "NEXT", 233, 17, "white", align="center", shadow=None)
        n = 2 + self.up("peek")
        if self.fog_t > 0:
            draw_text(s, "?", 233, 40, "lavender", 2, align="center")
        else:
            x0 = 233 - (n * 12 + (n - 1) * 3) // 2
            for i, (a, b) in enumerate(self.queue[:n]):
                x, y0 = x0 + i * 15, 30 + i * 6
                if b:
                    A.cell(s, x, y0, b, 0, self.t)
                    A.cell(s, x, y0 + 12, a, 0, self.t)
                else:
                    A.cell(s, x, y0 + 6, a, 0, self.t)
        # stage info: time, the kitten colours in play, best chain
        panel(s, (263, 14, 53, 62), fill="night", border=hue)
        draw_text(s, "TIME", 289, 17, "lavender", align="center", shadow=None)
        mm = int(self.stime) // 60
        draw_text(s, f"{mm}:{int(self.stime) % 60:02d}", 289, 26, "white", align="center", shadow=None)
        nc = self.st["ncol"]
        for i in range(nc):
            A.kitten(s, 289 - nc * 5 + i * 10 - 1, 37 + (i % 2) * 3, i + 1, 0)
        draw_text(s, f"CHAIN X{self.best_chain}", 289, 64, "peach", align="center", shadow=None)
        # rival / boss, else the upgrade shelf
        panel(s, (206, 80, 110, 116), fill="night", border="red" if self.foe and self.foe["boss"] else hue)
        if self.foe:
            f = self.foe
            data = (S.BOSSES if f["boss"] else S.RIVALS)[f["id"]]
            draw_text(s, data[0], 261, 84, "red" if f["boss"] else "white", align="center", shadow="ink")
            boss_bar(s, "AWAKE", f["hp"], f["max"], self.t, y=93, x=210, w=102)
            mood = "sleep" if f["sleep"] else "angry" if f["tele"] else "smug" if f["phase"] == 1 else "open"
            if f["hit"] > 0:
                mood = "hurt"
            A.foe(s, f["boss"], data, FOE_X, FOE_Y, self.t, mood, f["hit"] > 0)
            if f["sleep"]:
                A.draw_z(s, FOE_X + 18, FOE_Y - 28 - int(self.t * 8) % 8, "white")
            if f["tele"]:
                atk, left = f["tele"]
                if int(self.t * 8) % 2:
                    draw_text(s, "!", FOE_X - 34, FOE_Y - 20, "red", 2, outline="ink")
                draw_text(s, S.ATTACK_NAMES[atk], 261, 108, "red", align="center", shadow="ink")
                w = int(96 * max(0.0, left) / max(1.0, 1.8 - self.tier * 0.04))
                s.fill(col("red"), (213, 117, w, 2))
            elif not f["sleep"]:
                w = int(96 * max(0.0, 1 - f["t"] / max(0.1, f["every"])))
                s.fill(col("darkgray"), (213, 117, 96, 2))
                s.fill(col("peach"), (213, 117, w, 2))
            draw_text(s, data[6] if f["boss"] else "PILLOW FIGHT!", 261, 187, "lavender", align="center", shadow=None)
        else:
            self.draw_shelf(s)
        for x, y, prog, power in self.shots:
            if power > 0:
                tx, ty = FOE_X, FOE_Y
            else:
                x, y, tx, ty = FOE_X, FOE_Y - 10, BX + BW // 2, BY - 10
            px = x + (tx - x) * prog
            py = y + (ty - y) * prog - math.sin(prog * math.pi) * 30
            if power > 0:
                A.draw_z(s, int(px) - 1, int(py) - 1, "white")
                pygame.draw.circle(s, col("lavender"), (int(px) + 1, int(py) + 1), 3, 1)
            else:
                s.blit(sprite("kp_pillow"), (int(px) - 6, int(py) - 6))

    def draw_shelf(self, s):
        """No rival: a moonlit window and the upgrades Poppy has collected."""
        t = self.t
        pygame.draw.rect(s, col("black"), (220, 88, 82, 54), border_radius=3)
        s.fill(lerp_col("night", self.theme[1], 0.2), (222, 90, 78, 50))
        for i in range(9):
            sx, sy = 226 + (i * 29) % 72, 94 + (i * 17) % 40
            if int(t * 2 + i) % 4:
                s.fill(col("white"), (sx, sy, 1, 1))
        pygame.draw.circle(s, col("yellow"), (284, 104), 8)
        pygame.draw.circle(s, lerp_col("night", self.theme[1], 0.2), (288, 101), 7)
        s.fill(col("brown"), (260, 90, 2, 50))
        s.fill(col("brown"), (222, 114, 78, 2))
        draw_text(s, "UPGRADES", 261, 148, "white", align="center", shadow=None)
        x, y = 212, 158
        any_up = False
        for u in UPGRADE_POOL:
            lv = self.up(u.id)
            if not lv:
                continue
            any_up = True
            pygame.draw.circle(s, col(u.color), (x + 6, y + 6), 7)
            pygame.draw.circle(s, col("ink"), (x + 6, y + 6), 6)
            u.icon(s, x + 6, y + 6, t)
            draw_text(s, str(lv), x + 10, y + 9, "white", shadow="ink")
            x += 17
            if x > 300:
                x, y = 212, y + 17
        if not any_up:
            draw_text(s, "BEAT A BOSS", 261, 162, "darkgray", align="center", shadow=None)
            draw_text(s, "OR A BONUS!", 261, 172, "darkgray", align="center", shadow=None)

    def draw_warning(self, s):
        f = self.foe
        data = S.BOSSES[f["id"]]
        for i in range(2):
            y = 46 + i * 92
            s.fill(col("red"), (0, y, W, 12))
            off = int(self.t * 60) % 24
            for x in range(-24, W + 24, 24):
                pygame.draw.polygon(s, col("black"), [(x + off, y), (x + off + 10, y), (x + off + 4, y + 12),
                                                      (x + off - 6, y + 12)])
        ov = pygame.Surface((W, 80), pygame.SRCALPHA)
        ov.fill((12, 8, 24, 210))
        s.blit(ov, (0, 58))
        if int(self.t * 4) % 2:
            draw_text(s, "WARNING!", W // 2, 64, "red", 3, align="center", outline="ink")
        draw_text(s, f"A GRUMPY CAT APPROACHES: {data[0]}", W // 2, 92, "white", align="center")
        draw_text(s, f'"{data[6]}"', W // 2, 106, "peach", align="center")
        attacks = ", ".join(S.ATTACK_NAMES[a] for a in f["atk"][:3])
        draw_text(s, attacks, W // 2, 120, "lavender", align="center")

    def draw_intro(self, s):
        st = self.st
        k = st["k"]
        appear = min(1.0, self.state_t * 5)
        y = 40 + int((1 - appear) * 40)
        border = "red" if k == "boss" else "yellow" if self.bonus() else self.theme[1]
        tips = st["tip"]
        goals = self.goal_lines()
        h = 70 + 10 * len(goals) + 10 * len(tips) + (10 if st["mods"] else 0)
        panel(s, (34, y, 252, h), fill="night", border=border)
        draw_text(s, f"STAGE {self.stage_n}", W // 2, y + 7, "yellow", 2, align="center", outline="ink")
        draw_text(s, f"{self.theme[0]}  -  {S.KIND_TITLE[k]}", W // 2, y + 26, self.theme[2], align="center")
        yy = y + 39
        for line in goals:
            draw_text(s, line, W // 2, yy, "white", align="center")
            yy += 10
        if st["mods"]:
            draw_text(s, " + ".join(S.MODS[m] for m in st["mods"]), W // 2, yy, "pink", align="center")
            yy += 10
        for i, tip in enumerate(tips):
            draw_text(s, ("NEW! " if i == 0 else "") + tip, W // 2, yy, "lime" if int(self.t * 4) % 2 else "mint",
                      align="center")
            yy += 10
        # Poppy's line, with her face
        yy += 3
        s.fill(lerp_col("night", self.theme[1], 0.25), (40, yy - 2, 240, 13))
        s.blit(sprite("kp_kit", 3, remap=A.POPPY_REMAP), (43, yy - 1))
        draw_text(s, f'"{self.quip}"', 60, yy + 1, "cream", shadow=None)
        yy += 15
        if self.missed:
            draw_text(s, "TRY AGAIN!", W // 2, yy, "peach", align="center")
        elif self.state_t > 0.5:
            draw_text(s, "TURN: GO!", W // 2, yy, "lavender", align="center", shadow=None)

    def goal_lines(self):
        st, k, g = self.st, self.st["k"], self.st["goal"]
        if k == "clear":
            return [f"PUT {g} KITTENS TO SLEEP"]
        if k == "chain":
            return [f"MAKE A {g} CHAIN", "(KITTENS TUMBLING INTO NEW GROUPS)"]
        if k == "trigger":
            return [f"A {g} CHAIN IS WAITING IN THE BED", "DROP THE PAIR ON THE GLOW!" if self.tier < 3 or self.missed
                    else "FIND THE SPOT THAT SETS IT OFF!"]
        if k == "rescue":
            return [f"TUCK IN ALL {self.stars0} STAR KITTENS", "(MATCH THEM WITH THEIR COLOUR)"]
        if k == "pillow":
            return ["CLEAR EVERY PILLOW FROM THE BED", "(POP KITTENS NEXT TO THEM)"]
        if k == "storm":
            return [f"SURVIVE {st['lim']} SECONDS OF PILLOW RAIN"]
        if k == "duel":
            return [f"PILLOW FIGHT WITH {self.foe_name()}!", "CHAINS PUT THEM TO SLEEP"]
        if k == "boss":
            return [f"PUT {self.foe_name()} TO SLEEP!", "BIG CHAINS HIT HARDEST"]
        if k == "snack":
            return [f"{st['lim']} SEC: EVERY KITTEN = A FISH COIN", "TWIN PAIRS + PURR FEVER!"]
        return [f"{len(st['setups'])} DOMINO BEDS IN {st['lim']} SEC", "DROP THE PAIR ON THE GLOW!"]

    def draw_tally(self, s):
        appear = min(1.0, self.state_t * 6)
        y = 34 + int((1 - appear) * 30)
        k = self.st["k"]
        panel(s, (48, y, 224, 26 + 12 * len(self.tally) + 26), fill="night", border="yellow")
        title = "BOSS ASLEEP!" if k == "boss" else "BONUS RESULTS" if self.bonus() else f"STAGE {self.stage_n} CLEAR!"
        draw_text(s, title, W // 2, y + 8, "yellow", align="center")
        total = 0
        for i, (label, v, shown) in enumerate(self.tally):
            if i > self.tally_i:
                break
            yy = y + 24 + i * 12
            draw_text(s, label, 60, yy, "lavender" if v else "darkgray", shadow=None)
            draw_text(s, f"{shown}" if v else "-", 260, yy, "white" if v else "darkgray", align="right")
            total += shown
        yy = y + 28 + 12 * len(self.tally)
        s.fill(col("lavender"), (60, yy - 2, 200, 1))
        draw_text(s, "TOTAL", 60, yy + 2, "yellow")
        draw_text(s, f"{total}", 260, yy + 2, "yellow", align="right")
        if self.tally_i >= len(self.tally) and self.tally_t > 0.6:
            draw_text(s, "TURN: NEXT BED", W // 2, yy + 16, "white" if int(self.t * 3) % 2 else "lavender",
                      align="center", shadow=None)


# ==================================================================== carousel preview + GIF bot
_PV = ["..3.4.", ".1314.", "213442", "221142"]


def preview(s, t):
    w, h = s.get_width(), s.get_height()
    th = S.THEMES[int(t / 6) % len(S.THEMES)]
    s.fill(lerp_col("black", th[1], 0.18))
    for i in range(12):
        x, y = (i * 37 + 5) % w, (i * 23 + 3) % h
        if int(t * 2 + i) % 5:
            s.fill(lerp_col("black", th[1], 0.4), (x, y, 1, 1))
    bx, by = w - 6 * 12 - 6, h - 4 * 12 - 4
    pygame.draw.rect(s, col("brown"), (bx - 3, by - 2, 6 * 12 + 6, 4 * 12 + 6), border_radius=4)
    s.fill(lerp_col("night", th[1], 0.22), (bx, by, 72, 48))
    ph = t % 4.0                                # a pair falls, three tabbies + one curl up, the rest tumble
    for r, row in enumerate(_PV):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            code = int(ch)
            px, py = bx + x * 12, by + r * 12
            if code == 1 and ph > 2.0:
                f = min(1.0, (ph - 2.0) / 0.6)
                if f < 1:
                    A.curl(s, px, py, 1, f)
                continue
            if ph > 2.6 and code != 1 and r < 2 and x in (1, 2):
                py += min(12, int((ph - 2.6) * 60)) if _PV[r + 1][x] == "1" else 0
            A.kitten(s, px, py, code, 3 if ph > 2.0 else 0, t)
    if ph < 2.0:                                # the falling pair
        fy = by - 24 + int(min(1.0, ph / 1.6) * 24)
        A.kitten(s, bx + 2 * 12, fy - 12, 1, 0, t)
        A.kitten(s, bx + 2 * 12, fy, 1, 0, t)
    if 2.0 < ph < 3.4:
        draw_text(s, "2 CHAIN!", bx + 36, by - 10, rainbow(0, t), align="center", outline="ink", shadow=None)
    A.poppy(s, 20, h - 3, t, "cheer" if 2.0 < ph < 3.4 else "idle")


def gif_bot(scene, think=16):
    """Greedy bot: tries every column / turn for the current pair, keeps the best chain or the tidiest pile.
    think: frames it waits before dropping (16 = snappy GIF play, ~80 = roughly human pace)."""
    st = {"id": -1, "target": None, "frame": 0}

    def evaluate():
        p = scene.piece
        solo = p["b"] == 0
        codes = [p["a"]] if solo else [p["a"], p["b"]]
        best, best_v = None, -10 ** 9
        for x, rot in K.placements(scene.grid, solo):
            g = [row[:] for row in scene.grid]
            cc = [(cx, cy, codes[i]) for i, (cx, cy) in enumerate(K.piece_cells(x, 0, rot, solo))]
            landed = K.place(g, cc)
            v = 0
            if any(y < 0 for _, y, _ in landed):
                v -= 400
            chain, popped, pts = K.resolve(g, landed)
            v += pts * 2 + chain * 300 + popped * 15
            hs = [K.col_height(g, c) for c in range(COLS)]
            v -= max(hs) * 10 + hs[K.SPAWN_X] * 25 + sum(abs(hs[i] - hs[i + 1]) for i in range(COLS - 1)) * 3
            for yy in range(ROWS):
                for xx in range(COLS):
                    k = K.kcolor(g[yy][xx])
                    if not k:
                        continue
                    if xx + 1 < COLS and K.kcolor(g[yy][xx + 1]) == k:
                        v += 12
                    if yy + 1 < ROWS and K.kcolor(g[yy + 1][xx]) == k:
                        v += 12
            if K.topped(g):
                v -= 100000
            if v > best_v:
                best, best_v = (x, rot), v
        return best

    def f(frame):
        if scene.overlay is not None:
            return {"a"} if frame % 20 == 0 else set()
        if scene.state != "play":
            return {"a"} if frame % 25 == 0 else set()
        p = scene.piece
        if p is None:
            return set()
        if scene.piece_id != st["id"]:
            st["id"] = scene.piece_id
            st["target"] = evaluate()
            st["frame"] = frame
        tgt = st["target"]
        if tgt is None or frame % 2:
            return set()
        x, rot = tgt
        if p["b"] and p["rot"] != rot:
            return {"a"}
        if p["x"] < x:
            return {"right"}
        if p["x"] > x:
            return {"left"}
        if frame - st["frame"] > think:
            return {"up"}
        return set()
    return f
