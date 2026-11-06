"""WHISKER MAZE - a midnight snack raid! (original maze-chase game for MOCHI ARCADE)

NORI, a sleek black cat with yellow eyes and a tiny bell, sneaks through 200 house mazes eating fish crumbs
while dust bots with very different habits patrol: Sniffy follows her scent, Zigzag alternates turns, Fridgy
guards a spot, Snoozy naps until a crumb near it is eaten, Mopsy leaves slippery trails, Spritz sprays down
long halls and Ruff the roomba-dog barks and dashes. Catnip makes Nori zoomy: she bats dizzy bots, which
slide down the corridor like pucks and knock over every bot in their way.

Campaign data: whisker_maze_maze.py (exported to iOS), art + songs: whisker_maze_art.py, bosses:
whisker_maze_boss.py. The iOS port lives in ios/MochiArcade/Games/WhiskerMaze*.swift.
"""
import math
import random
from collections import deque

import pygame

from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow
from mochi_arcade.games import DIFF
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.games.whisker_maze_art import (RIM, draw_boss, draw_bot, draw_crumb, draw_led, draw_nori,
                                                draw_paws, draw_reboot, draw_secret)
from mochi_arcade.games.whisker_maze_boss import Boss
from mochi_arcade.games.whisker_maze_maze import BONUS_THEMES, CAMPAIGN, COLS, DOCK, EXIT, ROWS, THEMES
from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

HOWTO = ["ARROWS      MOVE (PRESS A TURN EARLY:",
         "            NORI TAKES THE NEXT GAP)",
         "Z / SPACE   PURR DASH (SHORT BURST)",
         "",
         "EAT EVERY FISH CRUMB TO CLEAR A ROOM.",
         "CATNIP = ZOOMIES: BAT THE DIZZY BOTS -",
         "THEY SLIDE AND KNOCK OVER THE OTHERS!",
         "TUNA, BELLS AND SECRET PAW PATHS TOO.",
         "BOSS EVERY 10TH STAGE, BONUS ON X5.",
         "ENTER / ESC  PAUSE"]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["left", "right", "up", "down", "a"]

TS = 10                      # tile size in pixels
OX, OY = 5, 25               # maze origin (31x17 tiles -> 310x170)
NORI_SPEED = 5.4             # tiles per second
BUFFER = 0.6                 # a tapped turn stays wanted this long (pre-turn)
ASSIST = 0.34                # turn when this close to a junction centre (early or a little late)
DIRS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
D4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
LIFE_AT = [20000, 50000, 100000, 160000]      # then every 80000
KIND_SPEED = {"sniffy": 0.95, "zig": 1.0, "fridgy": 0.9, "snoozy": 1.0, "mopsy": 0.9, "spritz": 0.85,
              "ruff": 0.8, "bunny": 0.8, "mouse": 0.72}
DOCK_X = (13, 14, 16, 17, 15, 15)
EXPORT = {"stages": [dict(st, rows=[r[:16] for r in st["rows"]]) for st in CAMPAIGN],
          "themes": [list(t) for t in THEMES], "bonus_themes": {k: list(v) for k, v in BONUS_THEMES.items()}}


def rnd(v):
    return int(math.floor(v + 0.5))


def tpx(x):
    return OX + x * TS + TS // 2


def tpy(y):
    return OY + y * TS + TS // 2


# ----------------------------------------------------------------------------- upgrade cards
def _icon_paws(s, cx, cy, t):
    for i, (dx, dy) in enumerate(((-5, 3), (-1, -1), (3, 3), (6, -2))):
        if int(t * 6) % 4 >= i:
            s.fill(col("white"), (cx + dx, cy + dy, 2, 2))


def _icon_nip(s, cx, cy, t):
    s.blit(sprite("wm_nip"), (cx - 4, cy - 4 + int(math.sin(t * 5))))


def _icon_dash(s, cx, cy, t):
    for i in range(3):
        s.fill(col("sky"), (cx - 7 + i * 2 - int(t * 20) % 3, cy - 3 + i * 3, 6, 1))
    s.blit(sprite("wm_side", int(t * 9) % 2), (cx - 2, cy - 6))


def _icon_collar(s, cx, cy, t):
    pygame.draw.circle(s, col("red"), (cx, cy), 6, 2)
    s.blit(sprite("wm_bell"), (cx - 4, cy + 1))


def _icon_whisker(s, cx, cy, t):
    for dy in (-2, 0, 2):
        w = 6 + int(math.sin(t * 6 + dy) * 2)
        s.fill(col("white"), (cx - w - 2, cy + dy, w, 1))
        s.fill(col("white"), (cx + 3, cy + dy, w, 1))
    s.fill(col("pink"), (cx - 1, cy - 1, 3, 2))


def _icon_bell(s, cx, cy, t):
    s.blit(sprite("wm_bell"), (cx - 4, cy - 4))
    pygame.draw.line(s, col("red"), (cx - 7, cy - 6), (cx + 7, cy + 6))


def _icon_power(s, cx, cy, t):
    r = 4 + int(abs(math.sin(t * 4)) * 2)
    pygame.draw.circle(s, col("hotpink"), (cx, cy + 1), r)
    for dx in (-4, -1, 2, 5):
        s.fill(col("pink"), (cx + dx - 1, cy - 6, 2, 2))


def _icon_tuna(s, cx, cy, t):
    s.blit(sprite("wm_tuna"), (cx - 5, cy - 4))


def _icon_fever(s, cx, cy, t):
    for i in range(3):
        pygame.draw.circle(s, col(rainbow(i, t)), (cx - 4 + i * 4, cy + 1 - (i % 2) * 3), 2)


def _icon_luck(s, cx, cy, t):
    s.blit(sprite("wm_gold"), (cx - 5, cy - 3 + int(math.sin(t * 4))))


UPGRADES = [
    Upgrade("speed", "QUICK PAWS", "NORI RUNS|FASTER", "lime", _icon_paws, 3),
    Upgrade("nip", "LONG ZOOMIES", "CATNIP|LASTS LONGER", "mint", _icon_nip, 3),
    Upgrade("dash", "ZOOM DASH", "DASH MORE|OFTEN AND|LONGER", "sky", _icon_dash, 3),
    Upgrade("collar", "LUCKY COLLAR", "SHRUGS OFF|ONE HIT|EVERY STAGE", "red", _icon_collar, 2),
    Upgrade("whisker", "LONG WHISKERS", "EAT CRUMBS|BESIDE YOU|TOO", "white", _icon_whisker, 2),
    Upgrade("bell", "SILENT BELL", "BOTS SNIFF,|SEE AND HEAR|YOU LESS", "yellow", _icon_bell, 3),
    Upgrade("power", "POWER POUNCE", "BOSSES TAKE|MORE DAMAGE", "hotpink", _icon_power, 3),
    Upgrade("tuna", "TUNA LOVER", "TUNA IS|WORTH MORE,|STAYS LONGER", "sky", _icon_tuna, 3),
    Upgrade("life", "EXTRA LIFE", "+1 LIFE|RIGHT NOW", "pink", "heart", 5),
    Upgrade("fever", "FEVER PURR", "FEVER FILLS|FASTER AND|LASTS LONGER", "orange", _icon_fever, 3),
    Upgrade("luck", "LUCKY PAW", "MORE GOLD|FISH, BELLS|AND MILK", "yellow", _icon_luck, 3),
]


# ----------------------------------------------------------------------------- movers
class Mover:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.dir = (0, 0)
        self.face = (0, 1)

    def tile(self):
        return rnd(self.x) % COLS, rnd(self.y)


class Bot(Mover):
    def __init__(self, kind, x, y, post=None):
        super().__init__(x, y)
        self.kind = kind
        self.post = post
        self.state = "dock"      # dock | leave | roam | sleep | puck | reboot
        self.mode = ""           # per-kind: patrol/chase/return, alert/chase/drowsy, aim, bark/dash/tired
        self.timer = 0.0         # dock release / reboot / mode timer
        self.cd = 0.0
        self.dizzy = False
        self.frozen = 0.0
        self.spin = 0.0
        self.last_turn = 1
        self.hits = 0
        self.life = 0.0          # minions / mice
        self.prev = None
        self.post_dist = None

    def harmful(self):
        return self.state in ("roam", "leave") and not self.dizzy and self.frozen <= 0 and self.kind != "mouse"


# ----------------------------------------------------------------------------- the game
class WhiskerMaze(GameScene):
    @property
    def music(self):
        return self.song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES[d]
        self.dspeed = SPEED[d]
        self.levels = {}
        self.life_i = 0
        self.picks_left = 0
        self.pick_title = "POWER UP!"
        self.next_n = None
        self.hype.combo_y = 13
        start = max(1, min(STAGES, int(opt.get("stage", opt.get("start", 1)))))
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

    def song(self):
        k = self.st["kind"]
        return "boss" if k == "boss" else "bonus" if k == "bonus" else ("wm_prowl", "wm_moon")[self.tier % 2]

    def zoomy(self):
        return self.zoom_t > 0

    def scent_life(self):
        return (6.0 + 0.2 * self.tier) * (1 - 0.2 * self.lv("bell"))

    # ---------------------------------------------------------------- stage setup
    def start_stage(self, n):
        self.n = n
        st = self.st = CAMPAIGN[n - 1]
        self.tier = st["tier"]
        self.theme = THEMES[self.tier] if st["kind"] != "bonus" else BONUS_THEMES[st["bonus"]]
        self.reached(n)
        self.walls = []
        self.food = {}
        for y, row in enumerate(st["rows"]):
            wr = []
            for x, ch in enumerate(row):
                if ch in ".oP ":
                    wr.append(" ")
                elif ch == "~":
                    wr.append("~")
                else:
                    wr.append(ch)
                if ch in ".~Dd":
                    self.food[(x, y)] = "c"
                elif ch == "o":
                    self.food[(x, y)] = "o"
                elif ch == "%":
                    self.food[(x, y)] = "s"
                if ch == "P":
                    self.start = (x, y)
            self.walls.append(wr)
        self.total = sum(1 for v in self.food.values() if v == "c")
        if st["kind"] == "bonus" and st["bonus"] == "fish":
            for k in list(self.food):
                if self.food[k] == "c":
                    self.food[k] = "f"
        self.crumbs_left = self.total
        self.eaten = 0
        self.secrets = self.batted = 0
        self.door_phase = 0
        self.door_t = st["door_t"]
        self.door_ver = 0
        self.wet = {}            # (x, y) -> seconds left (Mopsy trails, boss floods)
        self.scent = {}
        self.items = []
        self.shots = []          # [x, y, vx, vy, style, life] (tiles, tiles/s)
        self.mists = []          # Spritz spray: [x, y, dx, dy]
        self.hazards = []        # boss telegraphs: {"tiles", "warn", "active", "style", "t"}
        self.zoom_t = 0.0
        self.chain = 0
        self.dash_t = 0.0
        self.dash_cd = 0.0
        self.invuln = 0.0
        self.collar = self.lv("collar")
        self.stime = 0.0
        self.missed = False
        self.stage_combo = 0
        self.streak = 0          # crumbs eaten without a pause (quiet counter, the combo is for big moments)
        self.streak_t = 0.0
        self.best_streak = 0
        self.mice_caught = self.mice_total = 0
        self.golds = 0
        self.bonus_left = float(st.get("time", 0))
        self.spawned = set()
        self.lucky_gold = st["kind"] == "normal" and self.hype.lucky(0.025 + 0.015 * self.lv("luck"))
        self.lucky_milk = st["kind"] == "normal" and self.hype.lucky(0.015 + 0.01 * self.lv("luck"))
        self.nip_spawn = 6.0
        self.nip_count = 0
        self.ndist = {}
        self.ndist_key = None
        self.boss = Boss(self, st["boss"]) if st["kind"] == "boss" else None
        self.bots = []
        self.reset_positions()
        if st["kind"] == "bonus" and st["bonus"] == "mice":
            sp = list(st["spots"])
            self.mice_total = min(len(sp), 10 + self.tier // 4)
            for x, y in sp[:self.mice_total]:
                m = Bot("mouse", x, y)
                m.state = "roam"
                self.bots.append(m)
        if st["kind"] == "bonus" and st["bonus"] == "fish":
            for x, y in st["spots"][:3]:
                self.items.append({"kind": "gold", "x": x, "y": y, "life": 99.0})
        self.state = "intro"
        self.state_t = 0.0
        self.intro_len = 3.0 if self.boss else 2.6
        self.tally = []
        self.bg = self.make_bg()
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.hype.FEVER_TIME = 8.0 + 1.5 * self.lv("fever")
        self.app.audio.music(self.song())
        self.app.audio.play("warning" if self.boss else "stage")
        if self.boss:
            self.hype.flash("red", 0.3)

    def reset_positions(self):
        """(Re)place Nori and the bots: start of a stage and after a miss."""
        sx, sy = self.start
        self.nori = Mover(sx, sy)
        self.nori.face = (0, 1)
        self.want = None
        self.want_t = 0.0
        self.last_key = None
        self.zoom_t = 0.0
        self.mists = []
        self.shots = []
        self.hazards = []
        self.dash_t = 0.0
        keep_mice = [b for b in self.bots if b.kind == "mouse"]
        self.bots = []
        if self.st["kind"] == "normal":
            gap = self.st["release"]
            for j, (k, px, py) in enumerate(self.st["bots"]):
                if k in ("fridgy", "snoozy"):
                    b = Bot(k, px, py, (px, py))
                    b.state = "sleep" if k == "snoozy" else "roam"
                    b.mode = "patrol" if k == "fridgy" else ""
                    b.post_dist = bfs_tiles(self, (px, py), "bot", doors=True)
                else:
                    b = Bot(k, DOCK_X[j % len(DOCK_X)], DOCK[1])
                    b.timer = 0.6 + j * gap
                self.bots.append(b)
        self.bots += keep_mice
        if self.boss and self.boss.state not in ("dead", "enter"):
            self.boss.x, self.boss.y = 15.0, 8.0
            self.boss.state = "idle"
            self.boss.cd = 2.0

    # ---------------------------------------------------------------- map queries
    def door_open(self, ch):
        return (ch == "D") == (self.door_phase == 1)

    def walk(self, x, y, who):
        """who: cat (Nori) | bot (maze only) | dock (bots leaving / entering the dock)."""
        if y < 0 or y >= ROWS:
            return False
        ch = self.walls[y][x % COLS]
        if ch == "#":
            return False
        if ch in "Dd":
            return self.door_open(ch)
        if ch == "%":
            return who == "cat"
        if ch in "=-":
            return who == "dock"
        return True

    def see(self, x, y):
        ch = self.walls[y][x % COLS] if 0 <= y < ROWS else "#"
        return ch not in "#%" and (ch not in "Dd" or self.door_open(ch))

    def is_wet(self, x, y):
        return self.walls[y][x % COLS] == "~" or (x % COLS, y) in self.wet

    def open_only(self, tiles):
        return [(x, y) for x, y in tiles if 0 <= x < COLS and 0 <= y < ROWS and self.walls[y][x] not in "#=-"]

    def row_tiles(self, y):
        return self.open_only([(x, y) for x in range(COLS)])

    def col_tiles(self, x):
        return self.open_only([(x, y) for y in range(ROWS)])

    def area_tiles(self, x, y, r):
        return self.open_only([(x + dx, y + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)])

    def nori_dist(self):
        """BFS distances (bot-walkable tiles) from Nori's tile, cached per tile + door state."""
        key = (self.nori.tile(), self.door_phase)
        if key != self.ndist_key:
            self.ndist_key = key
            self.ndist = bfs_tiles(self, key[0], "bot")
        return self.ndist

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
                if self.boss and self.boss.state == "enter":
                    self.boss.y = 8.0
                    self.boss.state = "idle"
        elif s == "play":
            self.play(dt)
        elif s == "dying":
            if self.state_t > 1.5:
                self.after_death()
        elif s == "ready":
            if self.state_t > 1.0:
                self.state = "play"
                self.state_t = 0.0
        elif s == "clear":
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

    def on_pick(self, uid):
        if uid:
            self.levels[uid] = self.lv(uid) + 1
            u = next(x for x in UPGRADES if x.id == uid)
            self.hype.banner(u.name, f"LEVEL {self.levels[uid]}", color=u.color, dur=1.2, scale=1)
            if uid == "life":
                self.lives += 1
                self.app.audio.play("extra")
            elif uid == "collar":
                self.collar += 1
            elif uid == "fever":
                self.hype.FEVER_TIME = 8.0 + 1.5 * self.lv("fever")

    def play(self, dt):
        st = self.st
        self.stime += dt
        self.invuln = max(0.0, self.invuln - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.dash_t = max(0.0, self.dash_t - dt)
        if self.zoom_t > 0:
            self.zoom_t -= dt
            if self.zoom_t <= 0:
                self.end_zoomy()
        self.stage_combo = max(self.stage_combo, self.hype.combo)
        if self.streak_t > 0:
            self.streak_t -= dt
            if self.streak_t <= 0:
                self.streak = 0
        self.read_input(dt)
        self.move_nori(dt)
        if self.state != "play":
            return
        self.update_doors(dt)
        for k in list(self.wet):
            self.wet[k] -= dt
            if self.wet[k] <= 0:
                del self.wet[k]
        self.update_bots(dt)
        if self.state != "play":
            return
        self.update_items(dt)
        self.update_shots(dt)
        self.update_hazards(dt)
        if self.boss and self.state == "play":
            self.update_boss(dt)
        if st["kind"] == "bonus" and self.state == "play":
            self.bonus_left -= dt
            if self.bonus_left <= 0:
                self.bonus_left = 0.0
                self.stage_clear()
        self.check_life()

    # ---------------------------------------------------------------- Nori
    def read_input(self, dt):
        inp = self.app.input
        for name in ("left", "right", "up", "down"):
            if inp.hit(name):
                self.last_key = name
                self.want = DIRS[name]
                self.want_t = BUFFER + 0.1 * self.lv("speed")
        held = [n for n in ("left", "right", "up", "down") if inp.down(n)]
        if held:
            name = self.last_key if self.last_key in held else held[0]
            self.want = DIRS[name]
            self.want_t = BUFFER
        else:
            self.want_t -= dt
            if self.want_t <= 0:
                self.want = None
        if inp.hit("a") and self.dash_cd <= 0 and (self.nori.dir != (0, 0) or self.want):
            self.dash_t = 0.45 + 0.1 * self.lv("dash")
            self.dash_cd = 5.0 - 0.9 * self.lv("dash")
            self.app.audio.play("jump")
            self.parts.burst(tpx(self.nori.x), tpy(self.nori.y), 8, ("white", "sky", "lavender"), 50, 0.4)

    def nori_speed(self):
        v = NORI_SPEED * (1 + 0.06 * self.lv("speed"))
        if self.zoomy():
            v *= 1.22
        if self.dash_t > 0:
            v *= 1.7
        if self.st["kind"] == "bonus":
            v *= 1.15
        tx, ty = self.nori.tile()
        if self.is_wet(tx, ty):
            v *= 1.25
        return v

    def nori_choose(self, m, tx, ty):
        w = self.want
        if self.is_wet(tx, ty) and m.dir != (0, 0) and self.walk(tx + m.dir[0], ty + m.dir[1], "cat"):
            return m.dir                         # sliding on a wet floor: no turning
        if w and self.walk(tx + w[0], ty + w[1], "cat"):
            return w
        if m.dir != (0, 0) and self.walk(tx + m.dir[0], ty + m.dir[1], "cat"):
            return m.dir
        return None

    def move_nori(self, dt):
        n = self.nori
        w = self.want
        tx, ty = n.tile()
        wet = self.is_wet(tx, ty)
        if w and n.dir != (0, 0) and not wet:
            if w == (-n.dir[0], -n.dir[1]):
                n.dir = w                        # reverse at once
                n.face = w
            elif w != n.dir:                    # corner assist: snap onto a nearby junction and turn
                cx, cy = rnd(n.x), rnd(n.y)
                if abs(n.x - cx) + abs(n.y - cy) <= ASSIST and self.walk(cx + w[0], cy + w[1], "cat"):
                    n.x, n.y = float(cx), float(cy)
                    n.dir = w
                    n.face = w
        self.advance(n, self.nori_speed() * dt, "cat", self.nori_choose)
        if n.dir != (0, 0):
            n.face = n.dir
        tx, ty = n.tile()
        self.scent[(tx, ty)] = self.stime
        if (tx, ty) in self.food:
            self.eat(tx, ty)
        wl = self.lv("whisker")
        if wl and abs(n.x - rnd(n.x)) + abs(n.y - rnd(n.y)) < 0.2:
            reach = [(tx + dx, ty + dy) for dx, dy in D4]
            if wl >= 2 and n.dir != (0, 0):
                reach.append((tx + 2 * n.dir[0], ty + 2 * n.dir[1]))
            for x, y in reach:
                k = (x % COLS, y)
                if k in self.food and self.food[k] in "cf" and self.walk(x, y, "cat"):
                    self.eat(k[0], k[1], whisker=True)
                    if self.state != "play":
                        return

    def advance(self, m, dist, who, choose):
        """Move m along the tile grid by dist tiles, calling choose(m, tx, ty) -> dir at every tile centre."""
        for _ in range(8):
            if dist <= 1e-6:
                return
            tx, ty = rnd(m.x), rnd(m.y)
            if abs(m.x - tx) < 1e-6 and abs(m.y - ty) < 1e-6:
                m.x, m.y = float(tx), float(ty)
                d = choose(m, tx % COLS, ty)
                if d is None or d == (0, 0) or not self.walk(tx + d[0], ty + d[1], who):
                    m.dir = (0, 0)
                    return
                m.dir = d
            dx, dy = m.dir
            if dx == 0 and dy == 0:
                return
            if dx:
                target = math.floor(m.x + 1e-9) + 1 if dx > 0 else math.ceil(m.x - 1e-9) - 1
                step = min(dist, abs(target - m.x))
                m.x += dx * step
                if abs(m.x - target) < 1e-6:
                    m.x = float(target)
            else:
                target = math.floor(m.y + 1e-9) + 1 if dy > 0 else math.ceil(m.y - 1e-9) - 1
                step = min(dist, abs(target - m.y))
                m.y += dy * step
                if abs(m.y - target) < 1e-6:
                    m.y = float(target)
            dist -= step
            if m.x < -0.5:
                m.x += COLS
            elif m.x > COLS - 0.5:
                m.x -= COLS

    # ---------------------------------------------------------------- eating
    def eat(self, x, y, whisker=False):
        kind = self.food.pop((x, y))
        au = self.app.audio
        if kind in "cf":
            self.crumbs_left -= 1
            self.eaten += 1
            self.streak += 1
            self.streak_t = 0.8
            self.best_streak = max(self.best_streak, self.streak)
            if kind == "f":
                combo = self.hype.hit(1, fever=0.01)
                if combo % 5 == 0:
                    self.score_at(50 + 5 * min(combo, 40), tpx(x), tpy(y) - 4, "peach")
                else:
                    self.score_at(50 + 5 * min(combo, 40))
                self.parts.burst(tpx(x), tpy(y), 4, ("cream", "peach", "white"), 30, 0.3)
            else:
                self.hype.fever_add(0.0045 * (1 + 0.35 * self.lv("fever")))
                self.score_at(10 + 5 * min(self.streak // 20, 4))
                if self.streak in (50, 100, 150, 200):
                    self.floats.add(tpx(x), tpy(y) - 10, f"STREAK {self.streak}!", "cream")
                    self.app.audio.play("combo")
            if whisker:
                self.parts.sparkle(tpx(x), tpy(y), "white")
            if self.eaten % 2 == 0:
                au.play("eat")
            self.wake_snoozers(x, y)
            self.check_spawns()
            if self.crumbs_left <= 0:
                if self.boss:
                    self.refill()
                else:
                    self.stage_clear()
        elif kind == "s":
            self.secrets += 1
            self.score_at(300, tpx(x), tpy(y) - 6, "yellow")
            self.hype.hit(1, fever=0.04)
            au.play("fruit")
            self.parts.burst(tpx(x), tpy(y), 10, ("yellow", "white"), 40, 0.5)
        elif kind == "o":
            self.score_at(50)
            self.start_zoomy(self.st["nip"] + 1.5 * self.lv("nip"))

    def refill(self):
        """Boss stages: the crumbs come back so the fight never runs dry."""
        for y, row in enumerate(self.st["rows"]):
            for x, ch in enumerate(row):
                if ch in ".~":
                    self.food[(x, y)] = "c"
        self.crumbs_left = self.total = sum(1 for v in self.food.values() if v == "c")
        self.hype.banner("FRESH CRUMBS!", color="cream", dur=1.2, scale=1, sound="bonus")

    def check_spawns(self):
        st = self.st
        if st["kind"] != "normal" or not st["spots"]:
            return
        f = self.eaten / max(1, self.total)
        for key, at, kind in (("tuna1", 0.33, "tuna"), ("tuna2", 0.72, "tuna"), ("gold", 0.2, "gold"),
                              ("bell", 0.5, "bell"), ("milk", 0.6, "milk")):
            if key in self.spawned or f < at:
                continue
            self.spawned.add(key)
            if kind == "gold" and not self.lucky_gold:
                continue
            if kind == "milk" and not self.lucky_milk:
                continue
            if kind == "bell" and not (st["bell"] and random.random() < 0.6 + 0.1 * self.lv("luck")):
                continue
            nt = self.nori.tile()
            sp = [p for p in st["spots"] if abs(p[0] - nt[0]) + abs(p[1] - nt[1]) >= 6 and (p[0], p[1]) not in self.food]
            if not sp:
                continue
            x, y = random.choice(sp)
            life = {"tuna": 9.0 + 2 * self.lv("tuna"), "gold": 8.0, "bell": 10.0, "milk": 10.0}[kind]
            self.items.append({"kind": kind, "x": x, "y": y, "life": life})
            self.parts.burst(tpx(x), tpy(y), 10, ("white", "yellow"), 40, 0.5)
            if kind == "gold":
                self.hype.banner("GOLDEN FISH!", "GRAB IT FAST!", color="yellow", dur=1.4, scale=1, sound="coin")

    def wake_snoozers(self, x, y):
        r = 3 - (1 if self.lv("bell") >= 2 else 0)
        for b in self.bots:
            if b.kind == "snoozy" and b.state == "sleep" and not self.zoomy():
                bx, by = b.tile()
                if abs(bx - x) + abs(by - y) <= r:
                    self.wake(b)

    def wake(self, b):
        b.state = "roam"
        b.mode = "alert"
        b.timer = 0.6
        self.floats.add(tpx(b.x), tpy(b.y) - 12, "!", "red")
        self.app.audio.play("hold")

    # ---------------------------------------------------------------- zoomies
    def start_zoomy(self, dur):
        self.zoom_t = dur
        self.chain = 0
        for b in self.bots:
            if b.state in ("roam", "leave", "sleep") and b.kind not in ("mouse",):
                b.dizzy = True
                b.spin = 0.35
        self.app.audio.play("powerup")
        self.hype.banner("ZOOMIES!", color="mint", dur=0.9, scale=1)
        self.parts.burst(tpx(self.nori.x), tpy(self.nori.y), 16, ("lime", "mint", "white"), 70, 0.6)

    def end_zoomy(self):
        self.zoom_t = 0.0
        for b in self.bots:
            b.dizzy = False

    # ---------------------------------------------------------------- doors
    def update_doors(self, dt):
        if "doors" not in self.st["feats"]:
            return
        self.door_t -= dt
        if self.door_t > 0:
            return
        closing = "d" if self.door_phase == 0 else "D"     # the group that is open now closes
        busy = set()
        for m in [self.nori] + [b for b in self.bots if b.state in ("roam", "leave", "puck")]:
            tx, ty = m.tile()
            busy.add((tx, ty))
            busy.add(((tx + m.dir[0]) % COLS, ty + m.dir[1]))
        for y in range(ROWS):
            for x in range(COLS):
                if self.walls[y][x] == closing and (x, y) in busy:
                    return                                   # wait until nobody stands in the doorway
        self.door_phase = 1 - self.door_phase
        self.door_t = self.st["door_t"]
        self.app.audio.play("lock")

    # ---------------------------------------------------------------- bots
    def bot_speed(self, b):
        base = NORI_SPEED * self.st["speed"] * self.dspeed * KIND_SPEED[b.kind]
        if b.kind == "mouse":
            return NORI_SPEED * 0.74
        if b.state == "leave":
            return base * 0.6
        if b.dizzy:
            return base * 0.55
        k = b.kind
        if k == "sniffy":
            tx, ty = b.tile()
            if self.stime - self.scent.get((tx, ty), -99) < 1.5:
                base *= 1.08
        elif k == "fridgy" and b.mode == "chase":
            base *= 1.22
        elif k == "snoozy" and b.mode == "chase":
            base *= 1.12
        elif k == "snoozy" and b.mode == "drowsy":
            base *= 0.6
        elif k == "ruff" and b.mode == "dash":
            base *= 1.45
        return base

    def update_bots(self, dt):
        nd = self.nori_dist()
        for b in list(self.bots):
            b.frozen = max(0.0, b.frozen - dt)
            b.cd = max(0.0, b.cd - dt)
            if b.state == "dock":
                b.timer -= dt
                if b.timer <= 0:
                    b.state = "leave"
                    b.dizzy = False
                continue
            if b.state == "reboot":
                dx, dy = DOCK[0] - b.x, DOCK[1] - b.y
                d = math.hypot(dx, dy)
                step = 12 * dt
                if d <= step:
                    b.x, b.y = float(DOCK[0]), float(DOCK[1])
                    b.state = "dock"
                    b.timer = 2.0
                    b.dir = (0, 0)
                    b.mode = ""
                else:
                    b.x += dx / d * step
                    b.y += dy / d * step
                continue
            if b.state == "puck":
                self.update_puck(b, dt)
                continue
            if b.life > 0:
                b.life -= dt
                if b.life <= 0:
                    self.parts.burst(tpx(b.x), tpy(b.y), 10, ("gray", "white"), 40, 0.4)
                    self.bots.remove(b)
                    continue
            if b.state == "sleep" or b.frozen > 0:
                continue
            if b.spin > 0:
                b.spin -= dt
                continue
            # timed modes that stand still
            if b.mode in ("alert", "aim", "bark", "tired"):
                b.timer -= dt
                if b.timer > 0:
                    continue
                if b.mode == "alert":
                    b.mode, b.timer = "chase", 6.0
                elif b.mode == "aim":
                    b.mode = ""
                    b.cd = 2.6
                    d = b.face
                    self.mists.append([b.x + d[0] * 0.5, b.y + d[1] * 0.5, d[0], d[1]])
                    self.app.audio.play("shoot")
                elif b.mode == "bark":
                    b.mode, b.timer = "dash", 1.8
                else:
                    b.mode = ""
                    b.cd = 2.5
            elif b.mode in ("chase", "drowsy", "dash") and b.kind in ("snoozy", "ruff"):
                b.timer -= dt
                if b.timer <= 0:
                    if b.kind == "ruff":
                        if b.mode == "dash":
                            b.mode, b.timer = "tired", 1.6
                    elif b.mode == "chase":
                        b.mode, b.timer = "drowsy", 1.6
                    else:
                        self.snooze(b)
                        continue
            who = "dock" if b.state == "leave" else "bot"
            self.advance(b, self.bot_speed(b) * dt, who, self.bot_choose)
            if b.dir != (0, 0):
                b.face = b.dir
        self.bots = [b for b in self.bots if b.state != "gone"]
        self.bot_touch()

    def snooze(self, b):
        b.mode = ""
        cx, cy = rnd(b.x), rnd(b.y)
        if self.walk(cx, cy, "bot"):
            b.x, b.y = float(cx), float(cy)
            b.state = "sleep"
            b.dir = (0, 0)

    def bot_choose(self, b, tx, ty):
        if b.prev != (tx, ty):
            if b.kind == "mopsy" and b.prev and self.walls[b.prev[1]][b.prev[0]] == " ":
                self.wet[b.prev] = 5.0
            b.prev = (tx, ty)
        if b.state == "leave":
            if ty == DOCK[1] and tx != DOCK[0]:
                return (1 if tx < DOCK[0] else -1, 0)
            if (tx, ty) == EXIT:
                b.state = "roam"
                if b.kind == "snoozy":
                    b.mode, b.timer = "chase", 4.0
                elif b.kind == "fridgy":
                    b.mode = "return"
                return random.choice(((1, 0), (-1, 0)))
            return (0, -1)
        opts = [d for d in D4 if self.walk(tx + d[0], ty + d[1], "bot")]
        if not opts:
            return None
        back = (-b.dir[0], -b.dir[1])
        if len(opts) > 1 and back in opts:
            opts.remove(back)
        nd = self.nori_dist()

        def toward():
            return min(opts, key=lambda d: (nd.get(((tx + d[0]) % COLS, ty + d[1]), 999), random.random()))

        def wander(straight=0.55):
            if b.dir in opts and random.random() < straight:
                return b.dir
            return random.choice(opts)

        if b.kind == "mouse" or b.dizzy:
            if random.random() < 0.25:
                return random.choice(opts)
            return max(opts, key=lambda d: (nd.get(((tx + d[0]) % COLS, ty + d[1]), 0), random.random()))
        k = b.kind
        nt = self.nori.tile()
        if k == "sniffy":
            life = self.scent_life()
            best, bt = None, self.stime - life
            for d in opts:
                v = self.scent.get(((tx + d[0]) % COLS, ty + d[1]), -99)
                if v > bt:
                    best, bt = d, v
            if best:
                return best
            return toward() if random.random() < 0.25 else wander()
        if k == "zig":
            if len(opts) == 1:
                return opts[0]
            if random.random() < 0.3 + 0.015 * self.tier:
                return toward()
            left = (b.dir[1], -b.dir[0])
            right = (-b.dir[1], b.dir[0])
            first, second = (left, right) if b.last_turn > 0 else (right, left)
            for d in (first, second):
                if d in opts and d != (0, 0):
                    b.last_turn = -b.last_turn
                    return d
            return b.dir if b.dir in opts else random.choice(opts)
        if k == "fridgy":
            r = max(3, 6 - self.lv("bell"))
            pd = b.post_dist
            npd = pd.get(nt, 99)
            if b.mode == "patrol" and npd <= r:
                b.mode = "chase"
                self.floats.add(tpx(b.x), tpy(b.y) - 12, "!", "red")
            elif b.mode == "chase" and npd > r + 3:
                b.mode = "return"
            elif b.mode == "return" and pd.get((tx, ty), 99) <= 1:
                b.mode = "patrol"
            if b.mode == "chase":
                return toward()
            if b.mode == "return" or not b.mode:
                return min(opts, key=lambda d: (pd.get(((tx + d[0]) % COLS, ty + d[1]), 99), random.random()))
            near = [d for d in opts if pd.get(((tx + d[0]) % COLS, ty + d[1]), 99) <= 4]
            return random.choice(near) if near else min(opts, key=lambda d: pd.get(((tx + d[0]) % COLS, ty + d[1]), 99))
        if k == "snoozy":
            if b.mode == "chase":
                return toward()
            return wander(0.4)
        if k == "spritz":
            if b.cd <= 0 and b.mode == "" and self.line_of_sight((tx, ty), nt):
                b.mode = "aim"
                b.timer = 0.55
                b.face = (sign(nt[0] - tx), sign(nt[1] - ty))
                self.floats.add(tpx(b.x), tpy(b.y) - 12, "!", "red")
                return None
            return toward() if random.random() < 0.3 else wander(0.5)
        if k == "ruff":
            if b.mode == "dash":
                return toward()
            det = 7 - self.lv("bell")
            if b.mode == "" and b.cd <= 0 and nd.get((tx, ty), 99) <= det:
                b.mode = "bark"
                b.timer = 0.45
                self.floats.add(tpx(b.x), tpy(b.y) - 12, "WOOF!", "orange")
                self.app.audio.play("pop")
                return None
            return wander(0.6)
        if k == "bunny":
            return toward() if random.random() < 0.8 else wander()
        return wander(0.6)   # mopsy

    def line_of_sight(self, a, b):
        if a == b:
            return False
        if a[1] == b[1] and abs(a[0] - b[0]) <= 9:
            s = sign(b[0] - a[0])
            return all(self.see(x, a[1]) for x in range(a[0] + s, b[0], s))
        if a[0] == b[0] and abs(a[1] - b[1]) <= 9:
            s = sign(b[1] - a[1])
            return all(self.see(a[0], y) for y in range(a[1] + s, b[1], s))
        return False

    def bot_touch(self):
        n = self.nori
        for b in list(self.bots):
            if b.state in ("dock", "reboot", "puck", "gone"):
                continue
            if dist_wrap(n.x, n.y, b.x, b.y) > 0.72:
                continue
            if b.kind == "mouse":
                self.catch_mouse(b)
                continue
            if b.dizzy and self.zoomy():
                self.bat(b)
            elif b.state == "sleep":
                if not self.zoomy():
                    self.wake(b)
            elif b.harmful():
                self.nori_hit(b)
                if self.state != "play":
                    return

    def bat(self, b):
        n = self.nori
        d = n.dir if n.dir != (0, 0) else n.face
        self.chain += 1
        self.batted += 1
        pts = 200 * 2 ** min(self.chain - 1, 5)
        got = self.score_at(pts, tpx(b.x), tpy(b.y) - 8, "white")
        b.state = "puck"
        b.dizzy = False
        b.x, b.y = float(rnd(b.x)), float(rnd(b.y))     # snap onto the grid: it slides from a tile centre
        b.dir = d
        b.timer = 2.5
        b.hits = 0
        b.spin = 0.0
        b.mode = ""
        self.hype.hit(1, fever=0.08 * (1 + 0.35 * self.lv("fever")))
        self.hype.hitstop(0.07)
        self.app.shake(2, 0.15)
        self.app.audio.play("pop")
        self.parts.burst(tpx(b.x), tpy(b.y), 12, ("white", "yellow", "sky"), 70, 0.5)
        if got >= 3200:
            self.hype.banner("WHAM!", f"+{got}", color="yellow", dur=1.0, scale=2)

    def update_puck(self, b, dt):
        def straight(m, tx, ty):
            return m.dir if self.walk(tx + m.dir[0], ty + m.dir[1], "bot") else None
        self.advance(b, 16 * dt, "bot", straight)
        if int(self.t * 60) % 2 == 0:
            self.parts.sparkle(tpx(b.x), tpy(b.y), "white")
        for o in self.bots:
            if o is b or o.state in ("dock", "reboot", "puck") or o.kind == "mouse":
                continue
            if dist_wrap(b.x, b.y, o.x, o.y) < 0.85:
                b.hits += 1
                self.chain += 1
                self.batted += 1
                pts = 200 * 2 ** min(self.chain - 1, 5)
                self.score_at(pts, tpx(o.x), tpy(o.y) - 8, "white")
                o.state = "gone" if o.kind == "bunny" else "reboot"
                o.dizzy = False
                o.mode = ""
                self.hype.hit(1, fever=0.08)
                self.hype.hitstop(0.09)
                self.app.audio.play("explode")
                self.parts.burst(tpx(o.x), tpy(o.y), 18, ("yellow", "white", "orange"), 80, 0.6)
                if b.hits == 2:
                    self.hype.banner("STRIKE!", "DOUBLE KNOCK", color="orange", dur=1.2, sound="combo")
                    self.app.shake(3, 0.25)
                elif b.hits == 3:
                    self.hype.banner("SUPER STRIKE!!", f"{b.hits} BOTS IN A ROW", rainbow=True, dur=1.8,
                                     sound="fever")
                    self.hype.slowmo(0.35, 0.8)
                    self.hype.shower(40, "stars")
                    self.app.shake(5, 0.4)
                    self.score_at(5000, W // 2, 90)
        b.timer -= dt
        if b.dir == (0, 0) or b.timer <= 0:          # hit a wall: clonk, then fly home to reboot
            b.state = "gone" if b.kind == "bunny" else "reboot"
            self.app.audio.play("tin")
            self.parts.burst(tpx(b.x), tpy(b.y), 8, ("gray", "white"), 40, 0.4)

    def catch_mouse(self, b):
        self.bots.remove(b)
        self.mice_caught += 1
        combo = self.hype.hit(1, fever=0.12)
        self.score_at(300 + 50 * min(combo, 20), tpx(b.x), tpy(b.y) - 8, "pink")
        self.app.audio.play("pop")
        self.parts.burst(tpx(b.x), tpy(b.y), 14, ("gray", "pink", "white"), 60, 0.5)
        if self.mice_caught >= self.mice_total:
            self.hype.banner("ALL CAUGHT!", "PURR-FECT PARTY", rainbow=True, dur=1.8, sound="jackpot")
            self.hype.shower(50, "confetti")
            self.stage_clear()

    def spawn_bunny(self):
        bx, by = self.boss.tile()
        cand = self.open_only([(bx + dx, by + dy) for dx in range(-2, 3) for dy in range(-2, 3)])
        cand = [p for p in cand if self.walk(p[0], p[1], "bot")]
        if not cand or sum(1 for b in self.bots if b.kind == "bunny") >= 5:
            return
        x, y = random.choice(cand)
        b = Bot("bunny", x, y)
        b.state = "roam"
        b.life = 8.0
        if self.zoomy():
            b.dizzy = True
        self.bots.append(b)
        self.parts.burst(tpx(x), tpy(y), 8, ("gray", "white"), 40, 0.4)

    # ---------------------------------------------------------------- items, shots, hazards
    def update_items(self, dt):
        n = self.nori
        for it in list(self.items):
            it["life"] -= dt
            if it["life"] <= 0:
                self.items.remove(it)
                continue
            if dist_wrap(n.x, n.y, it["x"], it["y"]) < 0.7:
                self.items.remove(it)
                self.take(it)
        if self.boss and self.state == "play":
            has_nip = any(v == "o" for v in self.food.values())
            if not has_nip and not self.zoomy():
                self.nip_spawn -= dt
                if self.nip_spawn <= 0:
                    nips = self.st["nips"]
                    nt = n.tile()
                    far = sorted(nips, key=lambda p: -(abs(p[0] - nt[0]) + abs(p[1] - nt[1])))
                    x, y = far[1 + self.nip_count % 2] if len(far) > 2 else far[0]
                    self.nip_count += 1
                    self.food[(x, y)] = "o"
                    self.nip_spawn = 7.0
                    self.parts.burst(tpx(x), tpy(y), 14, ("lime", "mint", "white"), 50, 0.6)
                    self.app.audio.play("bubble")

    def take(self, it):
        k, x, y = it["kind"], it["x"], it["y"]
        g = self.hype
        if k == "tuna":
            pts = int((500 + 250 * self.tier) * (1 + 0.5 * self.lv("tuna")))
            self.add(pts, tpx(x), tpy(y) - 8, "sky")
            g.hit(1, fever=0.15)
            self.app.audio.play("fruit")
            self.parts.burst(tpx(x), tpy(y), 16, ("sky", "white", "blue"), 60, 0.6)
            self.floats.add(tpx(x), tpy(y) - 18, "TUNA!", "white")
        elif k == "bell":
            for b in self.bots:
                if b.state in ("roam", "leave"):
                    b.frozen = 3.0
            g.banner("JINGLE!", "THE BOTS FREEZE", color="yellow", dur=1.2, scale=1, sound="bonus")
            g.flash("yellow", 0.15)
        elif k == "gold":
            self.golds += 1
            if self.st["kind"] == "bonus":
                self.score_at(2000, tpx(x), tpy(y) - 8, "yellow")
                g.hit(1, fever=0.2)
                self.app.audio.play("coin")
                self.parts.burst(tpx(x), tpy(y), 16, ("yellow", "white"), 60, 0.6)
            else:
                g.jackpot(self.factor_pts(5000), "GOLDEN FISH!")
        elif k == "milk":
            self.lives += 1
            g.banner("MILK!", "+1 LIFE", color="white", dur=1.4, scale=2, sound="extra")
            g.shower(16, "hearts")

    def update_shots(self, dt):
        n = self.nori
        for m in list(self.mists):
            m[0] += m[2] * 11 * dt
            m[1] += m[3] * 11 * dt
            tx, ty = rnd(m[0]), rnd(m[1])
            if not (0 <= ty < ROWS) or not self.see(tx, ty):
                self.mists.remove(m)
                self.parts.burst(tpx(m[0]), tpy(m[1]), 6, ("sky", "white"), 30, 0.3)
                continue
            if dist_wrap(n.x, n.y, m[0], m[1]) < 0.6 and not self.zoomy():
                self.mists.remove(m)
                self.nori_hit(None)
                if self.state != "play":
                    return
        for sh in list(self.shots):
            sh[0] += sh[2] * dt
            sh[1] += sh[3] * dt
            sh[5] -= dt
            if sh[5] <= 0 or not (-1 < sh[0] < COLS and -1 < sh[1] < ROWS):
                self.shots.remove(sh)
                continue
            if dist_wrap(n.x, n.y, sh[0], sh[1]) < 0.65:
                self.shots.remove(sh)
                self.nori_hit(None)
                if self.state != "play":
                    return

    def add_hazard(self, tiles, warn, active, style):
        self.hazards.append({"tiles": list(tiles), "warn": warn, "active": active, "style": style, "t": 0.0})

    def add_traps(self, k):
        nt = self.nori.tile()
        cand = [(x, y) for y in range(ROWS) for x in range(COLS) if self.walls[y][x] in " ~"
                and 2 <= abs(x - nt[0]) + abs(y - nt[1]) <= 6]
        random.shuffle(cand)
        for p in cand[:k]:
            self.add_hazard([p], 0.8, 9.0, "trap")

    def update_hazards(self, dt):
        n = self.nori
        nt = n.tile()
        for h in list(self.hazards):
            h["t"] += dt
            if h["t"] > h["warn"] + h["active"]:
                self.hazards.remove(h)
                continue
            if h["t"] < h["warn"]:
                continue
            if h["style"] == "wet":
                for p in h["tiles"]:
                    self.wet[tuple(p)] = max(self.wet.get(tuple(p), 0.0), h["warn"] + h["active"] - h["t"])
                continue
            if h["t"] - dt < h["warn"] and h["style"] in ("stomp", "pop", "splash"):
                self.app.shake(3, 0.2)
            if nt in [tuple(p) for p in h["tiles"]] and self.invuln <= 0:
                if h["style"] == "trap":
                    self.hazards.remove(h)
                    self.app.audio.play("brick")
                self.nori_hit(None)
                if self.state != "play":
                    return

    def update_boss(self, dt):
        bo = self.boss
        bo.update(dt)
        n = self.nori
        if bo.state in ("dead", "air", "enter"):
            return
        if math.hypot(n.x - bo.x, n.y - bo.y) < 1.45:
            if self.zoomy() and bo.state != "stun":
                dmg = 1 + self.lv("power")
                self.hype.hitstop(0.12)
                self.hype.flash("white", 0.15)
                self.app.shake(4, 0.3)
                self.app.audio.play("explode")
                self.parts.burst(tpx(bo.x), tpy(bo.y), 24, ("white", "yellow", "pink"), 90, 0.7)
                self.score_at(1000, tpx(bo.x), tpy(bo.y) - 16, "white")
                self.hype.hit(1, fever=0.12)
                n.dir = (-n.dir[0], -n.dir[1]) if n.dir != (0, 0) else (0, 1)
                if bo.hurt(dmg):
                    self.boss_defeated()
                else:
                    self.hype.banner("POUNCE!", f"{bo.hp} TO GO", color="hotpink", dur=0.9, scale=1)
                    if bo.phase >= 2 and bo.hp + dmg > bo.maxhp * (0.67 if bo.phase == 2 else 0.34):
                        self.hype.banner("BOSS ANGRY!", color="red", dur=1.0, scale=1, sound="warning")
            elif bo.state != "stun":
                self.nori_hit(None)

    # ---------------------------------------------------------------- getting caught
    def nori_hit(self, bot):
        if self.invuln > 0 or self.state != "play":
            return
        if self.collar > 0:
            self.collar -= 1
            self.invuln = 2.0
            self.hype.banner("JINGLE SAVE!", f"COLLAR x{self.collar}", color="red", dur=1.2, scale=1, sound="tin")
            self.app.shake(3, 0.2)
            if bot:
                bot.frozen = 1.5
            return
        self.missed = True
        self.hype.break_combo()
        self.state = "dying"
        self.state_t = 0.0
        self.app.audio.play("hurt")
        self.app.shake(4, 0.35)
        self.app.audio.music(None)

    def after_death(self):
        au = self.app.audio
        self.lives -= 1
        if self.lives <= 0:
            self.state = "over"
            self.hype.banner("GAME OVER", f"STAGE {self.n}", color="red", dur=3.0)
            au.play("gameover")
            self.end_game(False, f"STAGE {self.n}", delay=2.5)
            return
        au.play("die")
        self.reset_positions()
        self.invuln = 1.2
        self.state = "ready"
        self.state_t = 0.0
        au.music(self.song())

    def check_life(self):
        k = self.life_i
        target = LIFE_AT[k] if k < len(LIFE_AT) else LIFE_AT[-1] + 80000 * (k - len(LIFE_AT) + 1)
        if self.score >= target:
            self.life_i += 1
            self.lives += 1
            self.hype.banner("BONUS LIFE!", f"{target} POINTS", color="pink", dur=1.4, sound="extra")
            self.hype.shower(16, "hearts")

    # ---------------------------------------------------------------- clear / tally
    def stage_clear(self):
        if self.state != "play":
            return
        self.state = "clear"
        self.state_t = 0.0
        self.end_zoomy()
        self.mists = []
        self.shots = []
        self.hazards = []
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
        self.hype.slowmo(0.3, 0.9)
        self.app.audio.play("win")
        self.app.audio.music(None)
        for b in self.bots:
            if b.state not in ("dock",):
                self.parts.burst(tpx(b.x), tpy(b.y), 10, ("white", "lavender", "yellow"), 50, 0.6)
        if self.st["kind"] == "normal":
            self.bots = []
            self.hype.banner("ROOM CLEAR!", "MRRRP!", color="mint", dur=1.6)
            self.hype.shower(30, "confetti")
        if self.st["kind"] != "bonus" and not self.missed:
            self.hype.banner("PURR-FECT!", "NOT A WHISKER TOUCHED", rainbow=True, dur=1.7, sound="fever")
            self.hype.shower(40, "stars")
        elif self.st["kind"] == "bonus":
            self.hype.banner("TIME UP!" if self.bonus_left <= 0 else "BONUS CLEAR!", color="yellow", dur=1.4)

    def boss_defeated(self):
        g = self.hype
        self.app.audio.play("bossdown")
        g.banner("BOSS DOWN!", self.boss.name, rainbow=True, dur=2.2, scale=2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(40, "coins")
        self.app.shake(6, 0.6)
        self.score_at(15000, W // 2, 80)
        bx, by = tpx(self.boss.x), tpy(self.boss.y)
        for i in range(4):
            self.parts.burst(bx, by, 20, ("white", "yellow", "orange", "pink"), 120, 1.0)
        self.bots = []
        self.stage_clear()
        g.slowmo(0.3, 1.2)

    def begin_tally(self):
        st = self.st
        f = self.factor_pts
        rows = []
        if st["kind"] == "normal":
            rows.append(("ROOM CLEAR", f(1000)))
            par = 30 + 0.32 * self.total
            rows.append(("TIME BONUS", f(max(0, int(par - self.stime)) * 25)))
            rows.append((f"BOTS BATTED x{self.batted}", f(self.batted * 150)))
            if self.secrets or "paw" in st["feats"]:
                rows.append((f"SECRET TREATS x{self.secrets}", f(self.secrets * 250)))
        elif st["kind"] == "boss":
            rows.append(("BOSS BONUS", f(10000 + 2000 * self.tier)))
            rows.append(("TIME BONUS", f(max(0, int(120 - self.stime)) * 50)))
        elif st["bonus"] == "mice":
            rows.append((f"MICE x{self.mice_caught}/{self.mice_total}", f(self.mice_caught * 200)))
            rows.append(("ALL CAUGHT", f(10000) if self.mice_caught >= self.mice_total else 0))
        else:
            rows.append((f"FISH TREATS x{self.eaten}", f(self.eaten * 20)))
            rows.append((f"GOLDEN FISH x{self.golds}", f(self.golds * 500)))
            rows.append(("ALL EATEN", f(10000) if self.crumbs_left <= 0 else 0))
        if st["kind"] == "bonus":
            rows.append((f"BEST COMBO {self.stage_combo}", f(self.stage_combo * 50)))
        else:
            rows.append((f"BEST STREAK {self.best_streak}", f(self.best_streak * 10)))
        if st["kind"] != "bonus":
            rows.append(("NO MISS", f(5000) if not self.missed else 0))
        self.tally = [[label, v, 0.0] for label, v in rows]
        self.tally_i = 0
        self.tally_wait = 0.0
        self.state = "tally"
        self.state_t = 0.0

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
            self.hype.banner("ALL CLEAR!!", "THE CAT CASTLE IS YOURS", rainbow=True, dur=5.0, sound="jackpot")
            self.hype.shower(120, "confetti")
            self.end_game(True, "ALL 200 STAGES!", delay=4.5)
            return
        self.next_n = self.n + 1
        if st["kind"] in ("boss", "bonus"):
            self.picks_left = 1
            self.pick_title = "BOSS BONUS!" if st["kind"] == "boss" else "SNACK BREAK!"
            self.state = "pick"
        else:
            self.start_stage(self.next_n)

    # ---------------------------------------------------------------- drawing
    def make_bg(self):
        name, fa, fb, wall, top, side, pat = self.theme
        s = pygame.Surface((W, H))
        s.fill(col("black"))
        ca, cb = col(fa), col(fb)
        rng = random.Random(self.n)
        for y in range(ROWS):
            for x in range(COLS):
                px, py = OX + x * TS, OY + y * TS
                ch = self.walls[y][x]
                if ch in "#%":
                    continue
                if ch in "=-":
                    s.fill(col("night"), (px, py, TS, TS))
                    if ch == "=" and x % 2:
                        s.fill(col("darkgray"), (px + 2, py + 8, 6, 1))
                    continue
                if pat == 0:
                    s.fill(ca if (x + y) % 2 else cb, (px, py, TS, TS))
                elif pat == 1:
                    s.fill(ca, (px, py, TS, TS))
                    s.fill(cb, (px, py + 4, TS, 1))
                    s.fill(cb, (px, py + 9, TS, 1))
                    if (x + y * 3) % 4 == 0:
                        s.fill(cb, (px + 4, py, 1, 4))
                elif pat == 2:
                    s.fill(ca, (px, py, TS, TS))
                    if (x + y) % 2 == 0:
                        s.fill(cb, (px + 4, py + 4, 2, 2))
                elif pat == 3:
                    s.fill(ca, (px, py, TS, TS))
                    s.fill(cb, (px, py, TS, 1))
                    s.fill(cb, (px, py, 1, TS))
                else:
                    s.fill(ca, (px, py, TS, TS))
                    if rng.random() < 0.25:
                        s.fill(col("lavender" if rng.random() < 0.5 else "white"),
                               (px + rng.randrange(1, 9), py + rng.randrange(1, 9), 1, 1))
        cw, ct, cs, k = col(wall), col(top), col(side), col("black")
        for y in range(ROWS):
            for x in range(COLS):
                ch = self.walls[y][x]
                if ch not in "#%":
                    continue
                px, py = OX + x * TS, OY + y * TS
                up = y > 0 and self.walls[y - 1][x] not in "#%"
                down = y < ROWS - 1 and self.walls[y + 1][x] not in "#%"
                left = x > 0 and self.walls[y][x - 1] not in "#%"
                right = x < COLS - 1 and self.walls[y][x + 1] not in "#%"
                s.fill(cw, (px, py, TS, TS))
                if down:                      # the cupboard front under the counter top
                    s.fill(cs, (px, py + 6, TS, 4))
                    s.fill(k, (px, py + TS - 1, TS, 1))
                    if (x * 7 + y) % 3 == 0:
                        s.fill(ct, (px + 4, py + 7, 2, 1))
                if up:
                    s.fill(ct, (px, py, TS, 1))
                if left:
                    s.fill(k, (px, py, 1, TS))
                if right:
                    s.fill(k, (px + TS - 1, py, 1, TS))
                if ch == "%":
                    s.fill(cs, (px + 1, py + 1, TS - 2, TS - 2 if not down else 5))
        return s

    def render(self, s):
        t = self.t
        s.blit(self.bg, (0, 0))
        self.draw_tiles(s, t)
        self.draw_hazards(s, t)
        for it in self.items:
            if it["life"] > 2 or int(t * 8) % 2:
                k = it["kind"]
                sp = sprite("wm_" + k)
                bob = int(math.sin(t * 5 + it["x"]) * 1)
                s.blit(sp, (tpx(it["x"]) - sp.get_width() // 2, tpy(it["y"]) - sp.get_height() // 2 + bob))
                if k == "gold" and int(t * 6) % 2:
                    s.fill(col("white"), (tpx(it["x"]) + 4, tpy(it["y"]) - 5, 1, 1))
        for b in self.bots:
            self.draw_bot(s, b, t)
        if self.boss and self.boss.state != "dead":
            self.draw_boss(s, t)
        if self.state != "clear" or not self.boss:
            self.draw_nori(s, t)
        for m in self.mists:
            x, y = tpx(m[0]), tpy(m[1])
            for i in range(3):
                s.fill(col("sky" if i else "white"), (x - int(m[2] * i * 3) - 1, y - int(m[3] * i * 3) - 1, 3 - i, 3 - i))
        for sh in self.shots:
            x, y = int(OX + sh[0] * TS + TS / 2), int(OY + sh[1] * TS + TS / 2)
            if sh[4] == "toast":
                pygame.draw.rect(s, col("black"), (x - 4, y - 4, 9, 9), border_radius=2)
                pygame.draw.rect(s, col("peach"), (x - 3, y - 3, 7, 7), border_radius=2)
                s.fill(col("brown"), (x - 3, y - 3, 7, 1))
            else:
                pygame.draw.circle(s, col("blue"), (x, y), 3)
                pygame.draw.circle(s, col("sky"), (x, y - 1), 2)
                s.fill(col("white"), (x - 1, y - 2, 1, 1))
        if self.st["dark"] and self.state not in ("clear", "tally"):
            self.draw_dark(s, t)
        self.parts.draw(s)
        self.floats.draw(s)
        self.draw_hud(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "tally":
            self.draw_tally(s, t)
        elif self.state == "ready":
            draw_text(s, "GO, NORI!", W // 2, tpy(self.start[1]) - 22, "yellow", 2, align="center", outline="ink",
                      shadow=None)

    def draw_tiles(self, s, t):
        fever = self.hype.fever_on
        wall, side = col(self.theme[3]), col(self.theme[5])
        near = self.nori.tile()
        for y in range(ROWS):
            for x in range(COLS):
                ch = self.walls[y][x]
                px, py = OX + x * TS, OY + y * TS
                if ch in "Dd":
                    if self.door_open(ch):
                        s.fill(side, (px, py, 2, TS))
                        s.fill(side, (px + TS - 2, py, 2, TS))
                    else:
                        warn = self.door_t < 0.8 and int(t * 10) % 2
                        pygame.draw.rect(s, col("black"), (px, py, TS, TS))
                        pygame.draw.rect(s, col("white") if warn else wall, (px + 1, py + 1, TS - 2, TS - 2),
                                         border_radius=1)
                        s.fill(side, (px + 2, py + 2, TS - 4, TS - 4))
                        s.fill(col("yellow"), (px + TS - 4, py + 4, 1, 2))
                    if self.door_t < 0.8 and self.door_open(ch) and int(t * 10) % 2:
                        s.fill(col("red"), (px + 4, py + 4, 2, 2))
                elif ch == "%":
                    glow = abs(x - near[0]) + abs(y - near[1]) <= 3
                    draw_paws(s, px, py, glow, t)
                elif ch == "-":
                    s.fill(col("hotpink"), (px, py + 4, TS, 2))
                if ch == "~" or (x, y) in self.wet:
                    fresh = ch == "~" or self.wet.get((x, y), 0) > 1.0 or int(t * 8) % 2
                    if fresh:
                        sh = (int(t * 3) + x + y) % 4
                        s.fill(col("sky"), (px + 1, py + 2 + sh, 3, 1))
                        s.fill(col("sky"), (px + 5, py + 6 - sh // 2, 4, 1))
                        s.fill(col("white"), (px + 2 + sh, py + 4, 1, 1))
                v = self.food.get((x, y))
                if v is None:
                    continue
                cx, cy = px + TS // 2, py + TS // 2
                if v == "c":
                    draw_crumb(s, cx, cy, t, fever, x + y)
                elif v == "f":
                    s.fill(col("orange"), (cx - 3, cy - 1, 4, 3))
                    s.fill(col("peach"), (cx - 2, cy - 1, 2, 1))
                    s.fill(col("orange"), (cx + 1, cy - 2, 1, 1))
                    s.fill(col("orange"), (cx + 1, cy + 1, 1, 1))
                    s.fill(col("black"), (cx - 2, cy, 1, 1))
                elif v == "s":
                    draw_secret(s, cx, cy, t)
                elif v == "o":
                    sp = sprite("wm_nip")
                    bob = int(math.sin(t * 4 + x) * 1)
                    s.blit(sp, (cx - 4, cy - 4 + bob))
                    if int(t * 5 + x) % 4 == 0:
                        s.fill(col("white"), (cx + 3, cy - 4, 1, 1))
        if self.st["kind"] == "normal" and any(b.kind == "sniffy" for b in self.bots):
            life = self.scent_life()
            c = col(self.theme[2] if self.theme[2] != self.theme[1] else "darkgray")
            pc = col("lavender")
            for (x, y), when in self.scent.items():
                age = self.stime - when
                if 0.3 < age < life and (x + y) % 2 == 0 and (x, y) not in self.food:
                    px, py = OX + x * TS + 3, OY + y * TS + 3
                    s.fill(pc if age < life * 0.4 else c, (px, py + 2, 2, 2))
                    s.fill(pc if age < life * 0.4 else c, (px + 3, py, 1, 1))

    def draw_hazards(self, s, t):
        for h in self.hazards:
            st = h["style"]
            on = h["t"] >= h["warn"]
            if st == "wet":
                if not on and int(t * 10) % 2:
                    for x, y in h["tiles"]:
                        s.fill(col("sky"), (OX + x * TS + 4, OY + y * TS + 4, 2, 2))
                continue
            for x, y in h["tiles"]:
                px, py = OX + x * TS, OY + y * TS
                if st == "trap":
                    if on:
                        s.blit(sprite("wm_trap"), (px + 1, py + 2))
                    elif int(t * 12) % 2:
                        s.fill(col("yellow"), (px + 3, py + 3, 4, 4))
                    continue
                if not on:
                    if int(t * 10) % 2:
                        c = {"suck": "sky", "snap": "yellow", "burn": "orange", "quake": "yellow"}.get(st, "red")
                        pygame.draw.rect(s, col(c), (px + 1, py + 1, TS - 2, TS - 2), 1)
                    if st in ("stomp", "pop", "splash"):
                        k = h["t"] / h["warn"]
                        r = 1 + int(k * 4)
                        pygame.draw.ellipse(s, col("black"), (px + 5 - r, py + 5 - r // 2, r * 2, r))
                    continue
                if st == "suck":
                    s.fill(col("sky"), (px, py + 3, TS, 4))
                    s.fill(col("white"), (px + (int(t * 40) + x * 3) % TS, py + 4, 2, 2))
                elif st == "snap":
                    for i in range(0, TS, 3):
                        s.fill(col("white"), (px + i, py + 2 + (i // 3) % 2 * 4, 2, 2))
                    s.fill(col("brown"), (px, py + 4, TS, 2))
                elif st == "burn":
                    s.fill(col("orange"), (px, py + 2, TS, 6))
                    s.fill(col("yellow"), (px + (int(t * 30) + x) % 8, py + 3, 2, 3))
                elif st == "quake":
                    s.fill(col("brown"), (px, py + 4 + int(math.sin(t * 40 + x) * 2), TS, 2))
                elif st == "splash":
                    pygame.draw.circle(s, col("sky"), (px + 5, py + 5), 5)
                    s.fill(col("white"), (px + 3, py + 3, 2, 2))
                else:   # stomp / pop impact
                    pygame.draw.circle(s, col("white"), (px + 5, py + 5), 5, 1)
                    s.fill(col("peach" if st == "pop" else "pink"), (px + 2, py + 2, 6, 6))

    def draw_bot(self, s, b, t):
        x, y = tpx(b.x), tpy(b.y)
        if b.state == "reboot":
            draw_reboot(s, x, y, t)
            return
        if b.kind == "mouse":
            sp = sprite("wm_mouse", int(t * 10) % 2, b.face[0] < 0)
            s.blit(sp, (x - 5, y - 3))
            return
        state = ""
        if b.state == "sleep":
            state = "sleep"
        elif b.dizzy:
            state = "dizzy"
        elif b.frozen > 0:
            state = "frozen"
        elif b.mode in ("alert", "aim", "bark", "chase", "dash") and b.kind != "zig":
            state = "alert" if b.mode != "chase" or b.kind in ("fridgy", "snoozy") else ""
        elif b.mode in ("tired", "drowsy"):
            state = "tired"
        flash = b.dizzy and self.zoom_t < 1.6 and int(t * 8) % 2 == 0
        if b.state == "puck":
            state, flash = "dizzy", True
        dx, dy = b.face
        draw_bot(s, b.kind, x, y, t, (dx, dy), state, flash)
        if b.state == "sleep":
            k = int(t * 2) % 3
            draw_text(s, "Z", x + 4 + k * 2, y - 10 - k * 3, "white", shadow=None)
        elif b.frozen > 0 and int(t * 6) % 2:
            s.fill(col("white"), (x - 6, y - 8, 1, 1))
            s.fill(col("white"), (x + 6, y - 6, 1, 1))
        if b.mode == "aim" and b.timer > 0:
            dx, dy = b.face
            for i in range(1, 4):
                if int(t * 12 + i) % 2:
                    s.fill(col("sky"), (x + dx * i * 6, y + dy * i * 6, 2, 2))

    def draw_boss(self, s, t):
        bo = self.boss
        x, y = tpx(bo.x), tpy(bo.y)
        if bo.airborne():
            pygame.draw.ellipse(s, col("black"), (x - 12, y + 6, 24, 6))
            y -= 10 + int(abs(math.sin(min(1.0, bo.timer / max(0.01, bo.air[4])) * math.pi)) * 14)
        mood = "stun" if bo.state == "stun" else "angry" if bo.phase >= 3 or bo.state == "wind" else ""
        flash = bo.flash > 0 and int(t * 20) % 2 == 0
        draw_boss(s, bo.kind, x, y, t, mood, flash, bo.wind_frac())
        if bo.state == "wind":
            draw_text(s, "!", x, y - 26, "red" if int(t * 10) % 2 else "yellow", 2, align="center", outline="ink",
                      shadow=None)

    def draw_nori(self, s, t):
        n = self.nori
        x, y = tpx(n.x), tpy(n.y)
        if self.state == "dying":
            k = self.state_t
            if k < 0.8:
                draw_nori(s, x + int(math.sin(t * 50) * 1), y, n.face, t, False, "hurt")
            elif int(k * 10) % 2 == 0 and k < 1.4:
                pygame.draw.circle(s, col("black"), (x, y), max(1, int((1.4 - k) * 9)))
                pygame.draw.circle(s, col("lavender"), (x, y), max(1, int((1.4 - k) * 9)), 1)
            if 0.79 < k < 0.82:
                self.parts.burst(x, y, 20, ("black", "darkgray", "lavender", "yellow"), 70, 0.8)
            return
        if self.invuln > 0 and int(t * 12) % 2:
            return
        moving = n.dir != (0, 0) and self.state == "play"
        mood = "happy" if self.state in ("clear", "tally") else ""
        if self.zoomy() or self.dash_t > 0:     # rainbow afterimages
            for i in range(1, 4):
                c = rainbow(i, t) if self.zoomy() else "sky"
                ax, ay = x - n.face[0] * i * 4, y - n.face[1] * i * 4
                s.fill(col(c), (ax - 3, ay - 1, 6, 3))
        hop = -int(abs(math.sin(t * 9)) * 4) if mood == "happy" else 0
        draw_nori(s, x, y + hop, n.face, t, moving, mood, flash=self.zoomy() and int(t * 10) % 3 == 0)
        if self.collar > 0 and int(t * 2) % 4 == 0:
            s.fill(col("yellow"), (x + 1, y + 2, 1, 1))
        w = self.want
        if w and self.state == "play" and w != n.dir and int(t * 8) % 2:
            ax, ay = x + w[0] * 9, y + w[1] * 9
            if w[0]:
                pygame.draw.polygon(s, col("yellow"), [(ax + w[0] * 2, ay), (ax - w[0], ay - 2), (ax - w[0], ay + 2)])
            else:
                pygame.draw.polygon(s, col("yellow"), [(ax, ay + w[1] * 2), (ax - 2, ay - w[1]), (ax + 2, ay - w[1])])

    def draw_dark(self, s, t):
        n = self.nori
        r = 4.2 + (1.5 if self.zoomy() else 0.0)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(ROWS):
            for x in range(COLS):
                d = math.hypot(x - n.x, y - n.y)
                a = max(0.0, min(1.0, (d - r) / 2.5))
                if a > 0:
                    ov.fill((12, 8, 24, int(a * 235)), (OX + x * TS, OY + y * TS, TS, TS))
        s.blit(ov, (0, 0))
        for b in self.bots:
            if b.state in ("roam", "leave", "sleep") and math.hypot(b.x - n.x, b.y - n.y) > r:
                draw_led(s, tpx(b.x), tpy(b.y) - 1, t)
        for it in self.items:
            if int(t * 4) % 2:
                s.fill(col("yellow"), (tpx(it["x"]), tpy(it["y"]), 1, 1))

    def draw_hud(self, s, t):
        s.fill(col("black"), (0, 0, W, OY - 2))
        draw_text(s, f"{self.score:07d}", 4, 3, "white", shadow=None)
        if self.streak >= 20 and self.st["kind"] != "bonus":
            c = ("cream", "peach", "orange", "yellow", "yellow")[min(4, self.streak // 20)]
            draw_text(s, f"STREAK {self.streak}", 4, 13, c if self.streak < 80 else rainbow(0, t), shadow=None)
        else:
            draw_text(s, f"HI {max(self.best, self.score):07d}", 4, 13, "gray", shadow=None)
        if self.boss and self.boss.state != "dead" and self.state != "intro":
            boss_bar(s, self.boss.name, self.boss.hp, self.boss.maxhp, t, x=58, w=200, y=1)
        elif self.st["kind"] == "bonus" and self.state in ("play", "intro"):
            secs = int(math.ceil(self.bonus_left))
            draw_text(s, f"TIME {secs:02d}", W // 2, 3, "yellow" if secs > 5 or int(t * 6) % 2 else "red",
                      align="center", shadow=None)
        else:
            draw_text(s, f"STAGE {self.n}", W // 2, 3, "yellow", align="center", shadow=None)
        if self.st["kind"] == "normal" and self.hype.combo < 3:
            draw_text(s, f"FISH {self.crumbs_left}", W // 2, 13, "cream", align="center", shadow=None)
        elif self.st["kind"] == "bonus" and self.st["bonus"] == "mice" and self.hype.combo < 3:
            draw_text(s, f"MICE {self.mice_caught}/{self.mice_total}", W // 2, 13, "pink", align="center",
                      shadow=None)
        self.hearts(s, W - 54, 3, self.lives)
        # FEVER gauge + DASH meter
        x0, y0 = W - 54, 14
        s.fill(col("darkgray"), (x0, y0, 48, 3))
        if self.hype.fever_on:
            for i in range(48):
                s.fill(col(rainbow(i // 6, t)), (x0 + i, y0, 1, 3))
        else:
            s.fill(col("orange"), (x0, y0, int(48 * self.hype.fever), 3))
        dmax = 5.0 - 0.9 * self.lv("dash")
        ready = self.dash_cd <= 0
        draw_text(s, "DASH", W - 102, 12, "sky" if ready and int(t * 3) % 2 else "gray" if not ready else "white",
                  shadow=None)
        s.fill(col("darkgray"), (W - 75, 14, 16, 3))
        s.fill(col("sky"), (W - 75, 14, int(16 * (1 - self.dash_cd / dmax)), 3))
        if self.zoom_t > 0:        # zoomies timer along the top of the maze
            full = self.st["nip"] + 1.5 * self.lv("nip")
            w = int((W - 10) * min(1.0, self.zoom_t / full))
            for i in range(0, w, 4):
                s.fill(col(rainbow(i // 4, t)), (5 + i, OY - 3, 3, 2))
        if self.collar > 0:
            for i in range(self.collar):
                s.blit(sprite("wm_bell"), (W - 54 + 8 * min(self.lives, 6) + 2 + i * 8, 2))

    def draw_card_nori(self, s, x, y, mood, t):
        name = "wm_happy" if mood == "happy" else "wm_sit"
        f = 0 if mood == "happy" else int(t * 2) % 2
        rim = sprite(name, f, False, RIM, 2)
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            s.blit(rim, (x + ox, y + oy))
        s.blit(sprite(name, f, False, None, 2), (x, y))

    def draw_intro(self, s, t):
        st = self.st
        k = st["kind"]
        if k == "boss":
            if int(t * 4) % 2:
                for x in range(-20, W + 20, 20):
                    pygame.draw.polygon(s, col("red"), [(x, 128), (x + 10, 128), (x + 20, 136), (x + 10, 136)])
                    pygame.draw.polygon(s, col("red"), [(x, 170), (x + 10, 170), (x + 20, 178), (x + 10, 178)])
            panel(s, (40, 138, 240, 30), fill="black", border="red")
            draw_text(s, "WARNING!!", W // 2, 142, "red" if int(t * 6) % 2 else "yellow", 2, align="center",
                      outline="ink")
            draw_text(s, f"{st['name']} APPROACHES", W // 2, 158, "white", align="center", shadow=None)
            return
        h = 66 if st["new"] else 56
        y0 = 70
        panel(s, (24, y0, 272, h), fill="ink", border="yellow" if k == "bonus" else "lavender")
        self.draw_card_nori(s, 32, y0 + 10, "happy" if k == "bonus" else "", t)
        cx = 172
        if k == "bonus":
            title = "BONUS STAGE"
            for i, ch in enumerate(title):
                draw_text(s, ch, cx - text_width(title, 2) // 2 + i * 12, y0 + 6 + int(math.sin(t * 8 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            sub = "CATCH THE WIND-UP MICE!" if st["bonus"] == "mice" else "EAT ALL THE FISH TREATS!"
            draw_text(s, st["name"], cx, y0 + 26, "yellow", align="center")
            draw_text(s, sub, cx, y0 + 38, "white", align="center")
            return
        draw_text(s, f"STAGE {self.n}", cx, y0 + 6, "yellow", 2, align="center", outline="ink", shadow=None)
        draw_text(s, self.theme[0], cx, y0 + 24, "lavender", align="center")
        draw_text(s, st["name"], cx, y0 + 34, "white", align="center")
        draw_text(s, f'"{st["quip"]}"', cx, y0 + 45, "gray", align="center", shadow=None)
        if st["new"]:
            draw_text(s, st["new"], W // 2, y0 + 56, "mint" if int(t * 4) % 2 else "lime", align="center")

    def draw_tally(self, s, t):
        rows = self.tally
        h = 34 + len(rows) * 11
        y0 = 60
        panel(s, (40, y0, 240, h), fill="ink", border="mint")
        head = {"boss": "BOSS CLEAR!", "bonus": "BONUS OVER!"}.get(self.st["kind"], f"STAGE {self.n} CLEAR!")
        draw_text(s, head, W // 2 + 14, y0 + 6, "mint", align="center")
        for i, (label, v, shown) in enumerate(rows):
            if i > self.tally_i:
                break
            y = y0 + 20 + i * 11
            draw_text(s, label, 52, y, "white" if v else "gray", shadow=None)
            draw_text(s, f"{int(shown)}", 268, y, "yellow" if v else "darkgray", align="right", shadow=None)
        if self.tally_i >= len(rows) and int(t * 3) % 2:
            draw_text(s, "PRESS Z", W // 2, y0 + h - 11, "lavender", align="center", shadow=None)


def sign(v):
    return (v > 0) - (v < 0)


def dist_wrap(ax, ay, bx, by):
    dx = abs(ax - bx)
    dx = min(dx, COLS - dx)
    return math.hypot(dx, ay - by)


def bfs_tiles(sc, start, who, doors=False):
    """Distances over walkable tiles from start (doors=True treats every door as open)."""
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        d = dist[(x, y)] + 1
        for dx, dy in D4:
            nx, ny = (x + dx) % COLS, y + dy
            if (nx, ny) in dist or not 0 <= ny < ROWS:
                continue
            ch = sc.walls[ny][nx]
            if doors and ch in "Dd":
                ok = True
            else:
                ok = sc.walk(nx, ny, who)
            if ok:
                dist[(nx, ny)] = d
                q.append((nx, ny))
    return dist


# ----------------------------------------------------------------------------- autopilot (GIF bot + tests)
def autopilot(sc, frame=0):
    keys = set()
    if sc.overlay is not None:
        if frame % 20 == 0 and sc.overlay.t > 1.2:
            keys.add("a")
        return keys
    if sc.state in ("intro", "tally"):
        if frame % 30 == 0 and sc.state_t > 1.2:
            keys.add("a")
        return keys
    if sc.state != "play":
        return keys
    n = sc.nori
    start = n.tile()
    zoomy = sc.zoomy()
    danger = set()
    for b in sc.bots:
        if b.harmful() or (b.state == "puck"):
            bx, by = b.tile()
            r = 2 if b.state != "puck" else 0
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if abs(dx) + abs(dy) <= r:
                        danger.add(((bx + dx) % COLS, by + dy))
    for h in sc.hazards:
        if h["style"] != "wet":
            for p in h["tiles"]:
                danger.add(tuple(p))
    for m in sc.mists + [[s[0], s[1]] for s in sc.shots]:
        danger.add((rnd(m[0]) % COLS, rnd(m[1])))
    bo = sc.boss
    if bo and bo.state not in ("dead",) and not (zoomy and bo.state != "stun"):
        bx, by = bo.tile()
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                danger.add((bx + dx, by + dy))
    targets = set()
    if zoomy:
        targets = {b.tile() for b in sc.bots if b.dizzy and b.state in ("roam", "leave", "sleep")}
        if bo and bo.state not in ("dead", "stun", "air"):
            targets.add(bo.tile())
    if not targets:
        targets = {k for k, v in sc.food.items() if v in "cfo s"}
        targets |= {(it["x"], it["y"]) for it in sc.items}
        mice = {b.tile() for b in sc.bots if b.kind == "mouse"}
        if mice:
            targets = mice
        if bo:
            nips = {k for k, v in sc.food.items() if v == "o"}
            if nips:
                targets = nips
    prev = {start: None}
    q = deque([start])
    found = None
    while q:
        cur = q.popleft()
        if cur in targets and cur != start:
            found = cur
            break
        x, y = cur
        for dx, dy in D4:
            nx, ny = (x + dx) % COLS, y + dy
            if (nx, ny) in prev or not sc.walk(x + dx, ny, "cat"):
                continue
            if (nx, ny) in danger and (nx, ny) not in targets:
                continue
            prev[(nx, ny)] = cur
            q.append((nx, ny))
    if found is None:
        # nothing reachable safely: step away from the closest threat
        best, bd = None, -1
        for name, (dx, dy) in DIRS.items():
            if sc.walk(start[0] + dx, start[1] + dy, "cat"):
                p = ((start[0] + dx) % COLS, start[1] + dy)
                d = min([abs(p[0] - b.tile()[0]) + abs(p[1] - b.tile()[1]) for b in sc.bots if b.harmful()] or [9])
                if d > bd:
                    best, bd = name, d
        if best:
            keys.add(best)
        return keys
    step = found
    while prev[step] != start:
        step = prev[step]
    dx, dy = step[0] - start[0], step[1] - start[1]
    if abs(dx) > 1:
        dx = -sign(dx)
    for name, d in DIRS.items():
        if d == (sign(dx), sign(dy)):
            keys.add(name)
    if zoomy and frame % 90 == 0:
        keys.add("a")
    return keys


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys."""
    return lambda frame: autopilot(scene, frame)


# ----------------------------------------------------------------------------- carousel preview
def preview(s, t):
    """Nori trots along eating crumbs with bots on her tail - then catnip turns the chase around."""
    w, h = s.get_size()
    s.fill(col("ink"))
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            if (x // 8 + y // 8) % 2:
                s.fill(col("deep"), (x, y, 8, 8))
    for ry in (6, h - 14):
        s.fill(col("peach"), (0, ry, w, 8))
        s.fill(col("cream"), (0, ry, w, 1))
        s.fill(col("brown"), (0, ry + 5, w, 3))
        for x in range(6, w, 18):
            s.fill(col("cream"), (x, ry + 6, 3, 1))
    lane = h // 2 + 2
    cyc = t % 8.0
    zoom = cyc >= 4.0
    if not zoom:
        px = -10 + (w + 20) * cyc / 4.0
        for x in range(4, w, 9):
            if x > px + 4:
                s.fill(col("cream"), (x, lane, 2, 2))
        if px < w - 10:
            s.blit(sprite("wm_nip"), (w - 12, lane - 4))
        for j, kind in enumerate(("sniffy", "zig", "snoozy")):
            draw_bot(s, kind, px - 24 - j * 16, lane, t, (1, 0), "", False)
        draw_nori(s, px, lane, (1, 0), t, True)
    else:
        px = w + 10 - (w + 40) * (cyc - 4.0) / 4.0
        for j, kind in enumerate(("sniffy", "zig", "snoozy")):
            draw_bot(s, kind, px - 22 - j * 16, lane, t, (-1, 0), "dizzy", int(t * 8) % 2 == 0)
        for i in range(1, 4):
            s.fill(col(rainbow(i, t)), (int(px) + i * 4 - 3, lane - 1, 6, 3))
        draw_nori(s, px, lane, (-1, 0), t, True)
        draw_text(s, "ZOOMIES!", w // 2, 16, rainbow(0, t), align="center", shadow="ink")
    s.blit(sprite("wm_tuna"), (4, h - 26))
