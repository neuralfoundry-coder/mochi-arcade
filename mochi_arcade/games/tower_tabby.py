"""TOWER TABBY - a single-screen climbing platformer starring Mikan, a chubby orange tabby (original game).

Mikan climbs a giant cat tree (scratching posts, sisal ropes, hammocks, springy beds, flimsy boxes, conveyor
belts and box tunnels) to win back the comfy cushion on the top perch. KAW, a cheeky crow in a red scarf,
throws yarn balls, pinecones, cushions and toys down the tree. JUMP over trouble or POUNCE to catch it.
200 stages from curated templates (tower_tabby_data.py): a boss every 10th (tower_tabby_boss.py), a bonus
stage on every x5, upgrades after bosses and bonus stages.
The iOS port (ios/MochiArcade/Games/TowerTabby*.swift) mirrors this file and plays the same exported stages.
"""
import math
import random

import pygame

from mochi_arcade import music
from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, rainbow, tier
from mochi_arcade.games import DIFF
from mochi_arcade.games import tower_tabby_art as art
from mochi_arcade.games import tower_tabby_data as data
from mochi_arcade.games.base import LIVES, SPEED, GameScene
from mochi_arcade.games.tower_tabby_boss import Boss
from mochi_arcade.gfx import H, W, col, draw_text, lerp_col, panel, sprite

HOWTO = [
    "LEFT/RIGHT  WALK      UP/DOWN  CLIMB",
    "Z / SPACE   JUMP (HOLD = HIGHER)",
    "X / CTRL    POUNCE! (CATCHES YARN & CONES)",
    "DOWN AT A BOX TUNNEL: DIVE IN",
    "",
    "CLIMB THE CAT TREE TO THE COMFY CUSHION.",
    "KAW THE CROW THROWS YARN - JUMP OR POUNCE!",
    "SAVE KITTENS, GRAB FISH, SWAT WITH WANDS.",
    "200 STAGES: BOSS EVERY 10TH, BONUS ON X5.",
    "ENTER / ESC  PAUSE",
]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["left", "right", "up", "down", "a", "b", "right", "up"]

HUD_H = 11
FLOOR = data.LEVEL_Y[0]
GRAV = 700.0
JUMP_V = 165.0
RUN = 72.0
CLIMB = 46.0
POUNCE_VX = 165.0
POUNCE_VY = 125.0
BED_V = 252.0
MAX_FALL = 260.0
PW, PH = 10, 11
BOPPABLE = ("yarn", "cone", "mouse", "spider", "ball", "marble", "moth", "dust")
ROLLERS = ("yarn", "marble", "dust", "mouse", "ball", "bot")
YARN_COLORS = ("pink", "sky", "lime", "lavender", "yellow", "mint", "peach")

music.SONGS.update({
    # "Tabby Climb" - stage theme (G major, bouncy)
    "tower": {"bpm": 138, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.26, "notes":
            "G5:8 B5:8 D6:8 B5:8 C6:8 A5:8 F#5:4  G5:8 A5:8 B5:8 G5:8 E5:4 D5:4 "
            "C5:8 E5:8 G5:8 C6:8 B5:8 G5:8 E5:4  D5:8 F#5:8 A5:8 D6:8 C6:4 A5:4 "
            "B5:8 D6:8 G6:8 D6:8 E6:8 D6:8 B5:4  C6:8 B5:8 A5:8 G5:8 A5:4 B5:4 "
            "C6:8 E6:8 D6:8 B5:8 A5:8 F#5:8 D5:4  G5:8 D5:8 B4:8 D5:8 G5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": music._bass(["G", "E", "C", "D", "G", "A", "D", "G"])},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, music.BEAT)},
    ]},
    # "Sky Perch" - stages 101-200 (E minor, driving)
    "tower_high": {"bpm": 150, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "E5:8 G5:8 B5:8 E6:8 D6:8 B5:8 G5:4  A5:8 C6:8 E6:8 C6:8 B5:4 G5:4 "
            "F#5:8 A5:8 D6:8 A5:8 G5:8 F#5:8 E5:4  D#5:8 F#5:8 B5:8 F#5:8 A5:4 B5:4 "
            "E6:8 D6:8 B5:8 G5:8 C6:8 B5:8 A5:4  D6:8 C6:8 A5:8 F#5:8 B5:4 A5:4 "
            "G5:8 A5:8 B5:8 C6:8 D6:8 C6:8 B5:4  A5:8 F#5:8 D#5:8 F#5:8 E5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": music._bass(["E", "A", "D", "B", "C", "D", "G", "B"])},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, music.ROCK)},
    ]},
})

def _icon(name):
    """Upgrade card icon: the 9x9 sprite drawn at 2x."""
    def draw(s, cx, cy, t):
        s.blit(sprite(name, 0, False, None, 2), (cx - 9, cy - 9))
    return draw


UPGRADES = [
    Upgrade("speed", "QUICK PAWS", "RUN FASTER", "lime", _icon("tt_i_speed"), 3),
    Upgrade("climb", "CLIMB CLAWS", "CLIMB 35%|FASTER", "mint", _icon("tt_i_climb"), 3),
    Upgrade("pounce", "POUNCE PRO", "LONGER POUNCE|QUICKER|RECOVERY", "orange", _icon("tt_i_pounce"), 3),
    Upgrade("heart", "NINE LIVES", "+1 LIFE|RIGHT NOW", "pink", _icon("tt_i_heart"), 3),
    Upgrade("bell", "BELL COLLAR", "BLOCKS 1 HIT|EVERY STAGE|LV2: REFILLS", "yellow", _icon("tt_i_bell"), 2),
    Upgrade("magnet", "FISH MAGNET", "PULLS FISH|AND ITEMS|TO YOU", "red", _icon("tt_i_magnet"), 3),
    Upgrade("wand", "LONG WAND", "WAND LASTS|LONGER, WIDER|SWATS", "lavender", _icon("tt_i_wand"), 3),
    Upgrade("lucky", "LUCKY TAIL", "MORE DROPS|AND GOLDEN|FISH", "hotpink", _icon("tt_i_lucky"), 3),
    Upgrade("nap", "CATNAP AURA", "HAZARDS MOVE|8% SLOWER", "teal", _icon("tt_i_nap"), 3),
    Upgrade("kitty", "KITTEN CALL", "KITTENS RUN|TO YOU +50%|KITTEN BONUS", "peach", _icon("tt_i_kitty"), 2),
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


# ----------------------------------------------------------------------------- the cat tree
class Seg:
    """A run of shelf cells of one kind: plank | bed | box | belt (dir -1/1)."""

    def __init__(self, x0, x1, k, slope, kind, belt=0):
        self.x0, self.x1, self.k, self.slope, self.kind, self.belt = x0, x1, k, slope, kind, belt
        self.stand = 0.0
        self.gone = 0.0
        self.boing = 0.0

    def y(self, x):
        return data.LEVEL_Y[self.k] + self.slope * data.TILT * (x - 160) / 160.0


class Post:
    def __init__(self, x, k, rope, slopes):
        self.x, self.k, self.rope = x, k, rope
        self.top = data.y_at(k + 1, slopes[k + 1], x)
        bot = data.y_at(k, slopes[k], x)
        self.bot = bot - 15 if rope else bot


class Ham:
    """A hammock riding back and forth over a run of '~' cells (32 px wide)."""

    def __init__(self, xa, xb, k, phase):
        self.xa, self.xb, self.k = xa, xb, k
        self.period = max(2.0, 2.0 * (xb - xa) / 34.0)
        self.phase = phase
        self.x = self.pos(0.0)
        self.dx = 0.0
        self.y = float(data.LEVEL_Y[k])
        self.x0, self.x1 = self.x, self.x + 32

    def pos(self, t):
        return self.xa + (self.xb - self.xa) * (0.5 - 0.5 * math.cos(math.tau * (t / self.period + self.phase)))

    def update(self, t):
        nx = self.pos(t)
        self.dx = nx - self.x
        self.x = nx
        self.x0, self.x1 = self.x, self.x + 32


class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)       # centre x, feet y
        self.vx = self.vy = 0.0
        self.ground = None
        self.face = 1
        self.climb = None
        self.pounce = False
        self.pounce_t = 0.0
        self.boost = False        # bounced by a bed or cushion: the jump-height cut does not apply
        self.pcd = 0.0
        self.air_pounce = True
        self.coyote = self.jbuf = 0.0
        self.inv = 2.0
        self.warp_t = 0.0
        self.warp_to = None
        self.anim = 0.0
        self.swipe = 0.0
        self.trail = []


class Haz:
    def __init__(self, kind, x, y, r):
        self.kind, self.x, self.y, self.r = kind, float(x), float(y), float(r)
        self.vx = self.vy = 0.0
        self.ground = None
        self.dir = random.choice((-1, 1))
        self.age = 0.0
        self.life = 16.0
        self.dead = False
        self.jumped = False
        self.batted = False
        self.spin = 0.0
        self.color = random.choice(YARN_COLORS)
        self.t = random.uniform(0, 6.28)
        self.cool = random.uniform(1.0, 2.5)
        self.mode = ""
        self.k = 0
        self.ay = self.y          # anchor y: spider thread top, moth cruise height, cushion landing
        self.stun = 0.0
        self.post = None
        self.cdir = 0
        self.harmless = False
        self.gold = False
        self.path = []


class Shot:
    def __init__(self, kind, x, y, vx, vy, r=2.0, warn=0.0, life=6.0):
        self.kind, self.x, self.y, self.vx, self.vy, self.r = kind, x, y, vx, vy, r
        self.warn, self.life = warn, life
        self.age = 0.0
        self.dead = False
        self.batted = False
        self.k = -1


class Pickup:
    def __init__(self, kind, x, y, value=0):
        self.kind, self.x, self.y, self.value = kind, float(x), float(y), value
        self.vx = self.vy = 0.0
        self.falling = False
        self.life = -1.0          # < 0: stays until picked up
        self.t = random.uniform(0, 6.28)
        self.ground = None


class Kitten:
    def __init__(self, x, y, color):
        self.x, self.y, self.color = float(x), float(y), color
        self.follow = False
        self.t = random.uniform(0, 6.28)


class Kaw:
    """The crow on the top branch: flies about and throws things down the tree."""

    def __init__(self, rate):
        self.x, self.y = 250.0, 22.0
        self.tx = 160.0
        self.face = -1
        self.mode = "fly"
        self.mode_t = 0.0
        self.throw_t = 2.6
        self.rate = rate
        self.aim = 0.0
        self.next_kind = None
        self.stun = 0.0
        self.taunt = 0.0
        self.party = False


# ----------------------------------------------------------------------------- the game
class TowerTabby(GameScene):
    music = "tower"

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        d = opt.get("difficulty", "normal")
        self.lives = LIVES.get(d, 3)
        self.spd = SPEED.get(d, 1.0)
        self.stage = max(1, min(STAGES, int(opt.get("stage", opt.get("start", 1)))))
        self.ups = {u.id: 0 for u in UPGRADES}
        self.next_extra = 30000
        self.picks, self.after_picks, self.pick_title = 0, "", "POWER UP!"
        self.was_fever = False
        self.kittens_saved = 0
        self.tally, self.tally_i, self.tally_t, self.tally_total = [], 0, 0.0, 0
        self.hype.combo_y = 14
        self.load_stage()
        head = min(5, tier(self.stage))
        if head:          # starting from a checkpoint: catch up on the upgrades a full run would have
            self.picks, self.after_picks, self.pick_title = head, "intro", "HEAD START!"
            self.state = "picks"

    # ---------------------------------------------------------------- stage setup
    def load_stage(self):
        sd = export()["stages"][self.stage - 1]
        self.sd = sd
        self.kind = sd["k"]
        self.tier = tier(self.stage)
        self.theme = data.THEMES[sd["th"]]
        self.lv = list(sd["lv"])
        self.sl = list(sd["sl"])
        self.mods = list(sd["mods"])
        self.build_tree()
        self.hz, self.shots, self.items, self.kits = [], [], [], []
        self.hs = sd["hs"] * self.spd * (1 - 0.08 * self.ups["nap"])
        self.wind = (1 if self.stage % 2 else -1) if "wind" in self.mods else 0
        self.spawn_placed()
        for c, k in sd["fish"]:
            x = c * data.CW + 8
            gold = self.hype.lucky(0.015 + 0.01 * self.ups["lucky"])
            self.items.append(Pickup("gfish" if gold else "fish", x, self.surface(k, x) - 5, 100 + 20 * self.tier))
        for c, k, kind in sd["it"]:
            x = c * data.CW + 8
            self.items.append(Pickup(kind, x, self.surface(k, x) - 6))
        for i, (c, k) in enumerate(sd["kit"]):
            x = c * data.CW + 8
            self.kits.append(Kitten(x, self.surface(k, x), (self.stage + i) % len(art.KITTEN_COLORS)))
        self.fish_total = len(sd["fish"])
        self.fish_got = 0
        sx = self.lv[0].index("P") * data.CW + 8
        self.start = (sx, float(FLOOR))
        self.p = Player(*self.start)
        self.shield = self.ups["bell"] > 0
        self.shield_t = 0.0
        self.wand_t = self.nip_t = self.milk_t = 0.0
        self.level_t = 0.0
        self.hurry = False
        self.missed = False
        self.chain, self.chain_t, self.best_chain = 0, 0.0, 0
        self.bops = 0
        self.got_kits = 0
        self.kaw = Kaw(sd["rate"]) if self.kind == "normal" or (self.kind == "bonus") else None
        if self.kaw and self.kind == "bonus":
            self.kaw.party = True
            self.kaw.rate = 0.24 if sd["bt"] == "fish" else 0.42
            self.kaw.throw_t = 1.2
        self.moth_t = sd["moth"] or 0.0
        self.moth_left = self.moth_t * 0.6
        self.boss = Boss(sd, self) if self.kind == "boss" else None
        self.wand_spawn = 6.0
        self.bonus_n = self.bonus_got = 0
        self.time_left = float(sd.get("time", 20))
        self.field = self.render_field()
        self.reached(self.stage)
        if self.kind == "boss":
            self.state = "warning"
            self.music = "boss"
            self.app.audio.play("warning")
        else:
            self.state = "intro"
            self.music = "bonus" if self.kind == "bonus" else ("tower_high" if self.tier >= 10 else "tower")
            self.app.audio.play("stage")
            if self.kind == "bonus":
                sub = "CATCH THE FISH RAIN!" if sd["bt"] == "fish" else "POUNCE THE RAINBOW YARN!"
                self.hype.banner("BONUS STAGE!", sub, rainbow=True, dur=2.0)
        self.intro_state = self.state
        self.state_t = 0.0
        self.was_fever = False
        self.app.audio.music(self.music)

    def build_tree(self):
        lv, sl = self.lv, self.sl
        cls = {"S": "bed", "X": "box", "<": "belt", ">": "belt"}
        self.segs, self.posts, self.hams, self.warps = [], [], [], []
        for k in range(6):
            c = 0
            row = lv[k]
            while c < data.NC:
                ch = row[c]
                if ch in data.SOLID:
                    kind = cls.get(ch, "plank")
                    c0 = c
                    while c < data.NC and row[c] in data.SOLID and cls.get(row[c], "plank") == kind and \
                            (kind != "belt" or row[c] == ch):
                        c += 1
                    self.segs.append(Seg(c0 * data.CW, c * data.CW, k, sl[k], kind,
                                         (-1 if ch == "<" else 1) if kind == "belt" else 0))
                elif ch == "~":
                    c0 = c
                    while c < data.NC and row[c] == "~":
                        c += 1
                    self.hams.append(Ham(c0 * data.CW, c * data.CW - 32, k, 0.5 * (len(self.hams) % 2)))
                else:
                    c += 1
            for c, ch in enumerate(row):
                if ch in "HR":
                    self.posts.append(Post(c * data.CW + 8, k, ch == "R", sl))
        for (k1, c1), (k2, c2) in data.warp_pairs(lv):
            self.warps.append(((c1 * data.CW + 8, k1), (c2 * data.CW + 8, k2)))
        g = data.find(lv, "G")
        self.goal = (g[1] * data.CW + 8, data.y_at(5, sl[5], g[1] * data.CW + 8)) if g else None

    def surface(self, k, x):
        return data.y_at(k, self.sl[k], x)

    def spawn_placed(self):
        for kind, c, k in self.sd["en"]:
            x = c * data.CW + 8
            if kind == "spider":
                h = Haz("spider", x, self.surface(k + 1, x) + 8, 4)
                h.ay = self.surface(k + 1, x) + 7
                h.k = k
            elif kind == "spritz":
                h = Haz("spritz", 5 if c == 0 else W - 5, self.surface(k, x) - 9, 5)
                h.k = k
                h.dir = 1 if c == 0 else -1
                h.cool = random.uniform(1.0, 2.6)
            else:
                r = 5 if kind == "mouse" else 5
                h = Haz(kind, x, self.surface(k, x) - r, r)
                h.k = k
            h.life = 1e9
            self.hz.append(h)

    def render_field(self):
        """The static part of the tree (posts, ropes, planks, the cushion, box tunnels) drawn once per stage."""
        th = self.theme
        f = pygame.Surface((W, H), pygame.SRCALPHA)
        for po in self.posts:
            draw_post(f, po, th, self.t)
        for sg in self.segs:
            if sg.kind == "plank":
                draw_plank(f, sg, th, self.lv)
        for (x1, k1), (x2, k2) in self.warps:
            for x, k in ((x1, k1), (x2, k2)):
                draw_tunnel(f, x, self.surface(k, x))
        if self.goal:
            draw_cushion(f, self.goal[0], self.goal[1])
        return f

    # ---------------------------------------------------------------- upgrades
    def run_speed(self):
        return RUN * (1 + 0.12 * self.ups["speed"]) * (1.45 if self.nip_t > 0 else 1.0)

    def climb_speed(self):
        return CLIMB * (1 + 0.35 * self.ups["climb"]) * (1.3 if self.nip_t > 0 else 1.0)

    def wand_reach(self):
        return 16 + 4 * self.ups["wand"]

    def took(self, uid):
        if uid is None:
            self.add(10000)
            self.hype.banner("ALL MAXED!", "+10000", color="yellow", dur=1.4)
            return
        self.ups[uid] += 1
        if uid == "heart":
            self.lives += 1
        if uid == "bell":
            self.shield = True
        if uid == "nap":
            self.hs = self.sd["hs"] * self.spd * (1 - 0.08 * self.ups["nap"])
        name = next(u.name for u in UPGRADES if u.id == uid)
        self.hype.banner(name, f"LEVEL {self.ups[uid]}", color="mint", dur=1.1, scale=1)

    # ---------------------------------------------------------------- physics
    def support(self, x, top, bottom):
        """Highest shelf / hammock surface under x between top and bottom: (y, thing) or (None, None)."""
        best, what = None, None
        for sg in self.segs:
            if sg.gone > 0 or x < sg.x0 or x >= sg.x1:
                continue
            y = sg.y(x)
            if top <= y <= bottom and (best is None or y < best):
                best, what = y, sg
        for hm in self.hams:
            if hm.x0 <= x < hm.x1 and top <= hm.y <= bottom and (best is None or hm.y < best):
                best, what = hm.y, hm
        return best, what

    def support_w(self, x, top, bottom, feet):
        """support() over a body's feet: the centre and +-feet pixels (ledge forgiveness for Mikan)."""
        y, g = self.support(x, top, bottom)
        if feet and g is None:
            for fx in (x - feet, x + feet):
                y2, g2 = self.support(fx, top, bottom)
                if g2 is not None and (y is None or y2 < y):
                    y, g = y2, g2
        return y, g

    def move_body(self, b, dt, half, grav=GRAV, walls=True, feet=0):
        """Walk / fall a body whose position is (centre x, feet y). Returns 'wall', 'land' or ''."""
        ev = ""
        g = b.ground
        if isinstance(g, Ham):
            b.x += g.dx
        if isinstance(g, Seg) and g.kind == "belt":
            b.x += g.belt * 32 * dt
        b.x += (b.vx + self.wind * 14) * dt
        if walls:
            if b.x < half:
                b.x, ev = half, "wall"
            elif b.x > W - half:
                b.x, ev = W - half, "wall"
        if g is not None:
            y, ng = self.support_w(b.x, b.y - 4, b.y + 5, feet)
            if ng is None:
                b.ground = None
                b.vy = 0.0
            else:
                b.y, b.ground, b.vy = y, ng, 0.0
                return ev
        b.vy = min(b.vy + grav * dt, MAX_FALL)
        prev = b.y
        b.y += b.vy * dt
        if b.vy >= 0:
            y, ng = self.support_w(b.x, prev - 1, b.y, feet)
            if ng is not None:
                b.y, b.ground, b.vy = y, ng, 0.0
                ev = "land"
        return ev

    def move_haz(self, h, dt, grav=GRAV):
        """Hazards keep their centre in (x, y); reuse the body mover with feet = y + r."""
        h.y += h.r
        ev = self.move_body(h, dt, h.r, grav)
        h.y -= h.r
        return ev

    # ---------------------------------------------------------------- update
    def tick(self, dt):
        self.state_t += dt
        st = self.state
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
            self.p.inv = max(self.p.inv, 1.0)
        st = self.state
        for hm in self.hams:
            hm.update(self.t)
        for sg in self.segs:
            sg.boing = max(0.0, sg.boing - dt)
            if sg.gone > 0:
                sg.gone -= dt
                if sg.gone <= 0:
                    sg.stand = 0.0
                    self.parts.burst((sg.x0 + sg.x1) / 2, sg.y((sg.x0 + sg.x1) / 2), 6, ("peach", "brown"), 30, 0.3)
        if st in ("intro", "warning", "play", "bossdown", "timeup") or (st == "clear" and self.kind != "normal"):
            self.update_player(dt)
        elif st == "dead":
            self.update_dead(dt)
        elif st == "clear":
            self.p.anim += dt
        if st == "play":
            self.level_t += dt
            if self.kind == "normal" and self.level_t > self.sd["par"] and not self.hurry:
                self.hurry = True
                self.hype.banner("HURRY UP!", "KAW IS GETTING CRANKY", color="red", dur=1.3, sound="warning")
        self.wand_t = max(0.0, self.wand_t - dt)
        self.nip_t = max(0.0, self.nip_t - dt)
        self.milk_t = max(0.0, self.milk_t - dt)
        if self.shield_t > 0:
            self.shield_t -= dt
            if self.shield_t <= 0 and self.ups["bell"] >= 2:
                self.shield = True
                self.app.audio.play("powerup")
        self.chain_t -= dt
        if self.chain_t <= 0:
            self.chain = 0
        if self.kaw is not None:
            self.update_kaw(dt)
        if st not in ("intro", "warning"):
            self.update_hazards(dt)
        self.update_shots(dt)
        self.update_items(dt)
        self.update_kittens(dt)
        if self.boss is not None:
            self.boss.update(self, dt)
            if st == "play":
                self.wand_spawn -= dt
                if self.wand_spawn <= 0:
                    self.wand_spawn = 11.0
                    if self.wand_t <= 0 and not any(i.kind == "wand" for i in self.items):
                        self.spawn_wand()
        if self.kind == "bonus":
            self.update_bonus(dt)
        if self.moth_t and st == "play":
            self.update_moths(dt)
        if st == "bossdown" and self.state_t > 3.8:
            self.state, self.state_t = "clear", 0.0
        if st == "timeup" and self.state_t > 1.6:
            self.start_tally()
        if st == "clear" and self.state_t > 2.4:
            self.start_tally()
        self.check_extra()
        fever = self.hype.fever_on
        if fever != self.was_fever and self.kind == "normal":
            self.app.audio.music("fever" if fever else self.music)
        self.was_fever = fever

    def check_extra(self):
        while self.score >= self.next_extra:
            self.lives += 1
            self.next_extra = 80000 if self.next_extra < 80000 else self.next_extra + 100000
            self.hype.banner("1UP!", "EXTRA LIFE", color="pink", dur=1.4, sound="extra")
            self.hype.shower(16, "hearts")

    def next_stage(self):
        if self.stage >= STAGES:
            self.state = "won"
            self.hype.banner("TOP CAT!!", "ALL 200 PERCHES WON", rainbow=True, dur=3.0, sound="win")
            self.hype.shower(120, "confetti")
            self.end_game(True, "ALL 200 STAGES CLIMBED!", delay=3.5)
            return
        self.stage += 1
        self.load_stage()

    # ---------------------------------------------------------------- the player
    def update_player(self, dt):
        p = self.p
        inp, au = self.app.input, self.app.audio
        p.inv = max(0.0, p.inv - dt)
        p.pcd -= dt
        p.anim += dt
        p.swipe = max(0.0, p.swipe - dt)
        p.trail.append((p.x, p.y))
        if len(p.trail) > 60:
            del p.trail[0]
        if p.warp_t > 0:
            p.warp_t -= dt
            if p.warp_t <= 0:
                x, k = p.warp_to
                p.x, p.y = float(x), self.surface(k, x)
                p.ground = self.support(p.x, p.y - 2, p.y + 2)[1]
                p.inv = max(p.inv, 0.6)
                au.play("pop")
                self.parts.burst(p.x, p.y - 6, 10, ("peach", "brown", "white"), 50, 0.4)
            return
        if p.climb is not None:
            self.update_climb(dt)
            return
        mx = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
        if not p.pounce:
            target = mx * self.run_speed()
            if "slick" in self.mods and p.ground is not None:
                p.vx += (target - p.vx) * min(1.0, dt * 3.5)
            else:
                p.vx = target
            if mx:
                p.face = mx
        if p.ground is not None and not (isinstance(p.ground, Seg) and p.ground.kind == "bed"):
            p.coyote = 0.08
            p.air_pounce = True
        else:
            p.coyote -= dt
        p.jbuf = 0.12 if inp.hit("a") else p.jbuf - dt
        if p.jbuf > 0 and p.coyote > 0 and not p.pounce:
            p.vy = -JUMP_V
            p.ground = None
            p.jbuf = p.coyote = 0.0
            au.play("jump")
        if p.vy < 0 and not inp.down("a") and not p.pounce and not p.boost:
            p.vy *= 0.86 ** (dt * 60)
        if inp.hit("b") and p.pcd <= 0 and (p.ground is not None or p.air_pounce):
            self.start_pounce()
        if inp.down("up") and not p.pounce:
            po = self.post_here(p, True)
            if po is not None:
                self.grab(po)
                return
        if inp.hit("down") and p.ground is not None:
            w = self.tunnel_here(p)
            if w is not None:
                p.warp_t, p.warp_to = 0.45, w
                p.vx = 0.0
                au.play("trap")
                self.parts.burst(p.x, p.y - 6, 8, ("peach", "brown"), 40, 0.3)
                return
            po = self.post_here(p, False)
            if po is not None:
                self.grab(po)
                p.y += 1.0
                return
        was_air = p.ground is None
        ev = self.move_body(p, dt, 6, feet=3)
        if p.ground is not None:
            g = p.ground
            if was_air:
                p.pounce = False
                p.boost = False
                if ev == "land":
                    self.parts.burst(p.x, p.y, 3, ("white",), 20, 0.2)
            if isinstance(g, Seg):
                if g.kind == "bed":
                    self.boing(p, g)
                elif g.kind == "box" and self.state in ("play", "intro"):
                    g.stand += dt
                    if g.stand > 0.45:
                        self.collapse(g)
        if p.pounce:
            p.pounce_t += dt
        if self.state == "play":
            self.check_goal()

    def start_pounce(self):
        p = self.p
        lv = self.ups["pounce"]
        p.pounce = True
        p.pounce_t = 0.0
        p.vx = p.face * POUNCE_VX * (1 + 0.1 * lv)
        p.vy = -POUNCE_VY if p.ground is not None else -70.0
        if p.ground is None:
            p.air_pounce = False
        p.ground = None
        p.pcd = 0.5 - 0.08 * lv
        self.app.audio.play("shoot")
        self.parts.burst(p.x, p.y - 2, 5, ("white", "peach"), 40, 0.3)

    def boing(self, b, sg):
        b.vy = -BED_V
        b.ground = None
        sg.boing = 0.25
        if b is self.p:
            self.p.pounce = False
            self.p.boost = True
            self.p.coyote = self.p.jbuf = 0.0
            self.app.audio.play("jump")
            self.parts.burst(b.x, b.y, 6, ("pink", "white"), 40, 0.3)

    def collapse(self, sg):
        sg.gone = 3.2
        self.app.audio.play("brick")
        for i in range(int((sg.x1 - sg.x0) / 4)):
            self.parts.burst(sg.x0 + i * 4 + 2, sg.y(sg.x0 + i * 4), 1, ("peach", "brown"), 60, 0.6)
        if self.p.ground is sg:
            self.p.ground = None

    def post_here(self, p, up):
        for po in self.posts:
            if abs(p.x - po.x) > 6:
                continue
            if up:
                if p.y - PH <= po.bot and p.y > po.top + 1.5 and p.y <= po.bot + 2 + (0 if po.rope else 0):
                    return po
                if po.rope and p.ground is None and p.y > po.top + 1.5 and p.y - PH <= po.bot:
                    return po
            elif p.ground is not None and abs(p.y - po.top) < 3:
                return po
        return None

    def tunnel_here(self, p):
        for a, b in self.warps:
            for here, there in ((a, b), (b, a)):
                x, k = here
                if abs(p.x - x) < 8 and abs(p.y - self.surface(k, x)) < 3:
                    return there
        return None

    def grab(self, po):
        p = self.p
        p.climb = po
        p.x = float(po.x)
        p.vx = p.vy = 0.0
        p.ground = None
        p.pounce = False

    def update_climb(self, dt):
        p, inp = self.p, self.app.input
        po = p.climb
        dy = (1 if inp.down("down") else 0) - (1 if inp.down("up") else 0)
        sp = self.climb_speed()
        p.y += dy * sp * dt
        if dy:
            p.anim += dt * 2
        if p.y <= po.top:
            p.y = po.top
            p.climb = None
            p.ground = self.support(p.x, p.y - 3, p.y + 3)[1]
            return
        if po.rope:
            if p.y - PH > po.bot:
                p.climb = None
        elif p.y >= po.bot:
            p.y = po.bot
            p.climb = None
            p.ground = self.support(p.x, p.y - 3, p.y + 3)[1]
            return
        if inp.hit("a") and p.climb is not None:
            mx = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0)
            p.climb = None
            p.vy = -JUMP_V * 0.6
            p.vx = mx * self.run_speed()
            if mx:
                p.face = mx
            self.app.audio.play("jump")

    def check_goal(self):
        p = self.p
        if self.goal is None or p.ground is None:
            return
        gx, gy = self.goal
        if abs(p.x - gx) < 11 and abs(p.y - gy) < 4:
            self.reach_goal()

    def reach_goal(self):
        self.state, self.state_t = "clear", 0.0
        p = self.p
        p.x, p.y = self.goal[0], self.goal[1] - 6
        p.vx = p.vy = 0.0
        h = self.hype
        if self.kaw:
            self.kaw.mode, self.kaw.mode_t = "flee", 0.0
        for hz in self.hz:
            if hz.kind not in ("spritz",):
                hz.dead = True
                self.parts.burst(hz.x, hz.y, 6, ("white", hz.color), 40, 0.4)
        self.hz = [hz for hz in self.hz if not hz.dead]
        self.shots = []
        if self.level_t < self.sd["par"] * 0.5:
            h.banner("SPEED CLIMB!!", "+5000", rainbow=True, dur=1.8, sound="win")
            h.shower(50, "confetti")
            self.add(5000)
        else:
            h.banner("TOP CAT!", "THE CUSHION IS MINE", color="yellow", dur=1.6, sound="levelup")
        h.shower(14, "hearts")
        self.add(1000, self.goal[0], self.goal[1] - 24, "yellow")

    def hurt(self, src=None):
        p = self.p
        if p.inv > 0 or self.state != "play" or p.warp_t > 0 or self.nip_t > 0:
            return
        if self.shield:
            self.shield = False
            self.shield_t = 18.0
            p.inv = 1.5
            self.app.audio.play("tin")
            self.app.shake(2, 0.2)
            self.parts.burst(p.x, p.y - 6, 16, ("yellow", "white"), 70, 0.5)
            self.floats.add(p.x, p.y - 18, "DING!", "yellow")
            return
        self.lives -= 1
        self.missed = True
        self.hype.break_combo()
        self.state, self.state_t = "dead", 0.0
        p.climb = None
        p.ground = None
        p.vy = -200.0
        p.vx = -p.face * 30.0
        self.app.audio.play("hurt")
        self.app.shake(3, 0.3)
        self.hype.flash("red", 0.15)
        self.parts.burst(p.x, p.y - 6, 18, ("orange", "white", "peach"), 80, 0.7)

    def update_dead(self, dt):
        p = self.p
        p.vy += GRAV * dt
        p.x += p.vx * dt
        p.y += p.vy * dt
        if self.state_t > 1.4:
            if self.lives <= 0:
                self.state = "over"
                self.end_game(False, f"STAGE {self.stage} - {self.kittens_saved} KITTENS SAVED")
                return
            self.respawn()

    def respawn(self):
        x, y = self.start
        if self.boss is not None and abs(self.boss.x - x) < 90:      # boss fights: come back on the far side
            x = 24.0 if self.boss.x > W / 2 else W - 24.0
        self.p = Player(x, y)
        self.p.inv = 2.2
        self.state, self.state_t = "play", 0.0
        self.shots = []
        keep = []
        for h in self.hz:
            if h.life > 1e8:
                keep.append(h)
        self.hz = keep
        if self.kaw:
            self.kaw.throw_t = 2.2
            self.kaw.mode = "fly"
        self.wand_t = 0.0

    # ---------------------------------------------------------------- KAW
    def update_kaw(self, dt):
        k = self.kaw
        k.mode_t += dt
        k.taunt -= dt
        if k.mode == "flee":
            k.y -= 70 * dt
            k.x += k.face * -40 * dt
            return
        if k.stun > 0:
            k.stun -= dt
            k.y = min(34.0, k.y + 30 * dt)
            return
        k.y += (22 + math.sin(self.t * 3) * 3 - k.y) * min(1.0, dt * 3)
        if k.mode == "perch":
            if k.mode_t > 1.0:
                k.mode, k.mode_t = "fly", 0.0
                k.tx = random.uniform(24, W - 24)
        else:
            d = k.tx - k.x
            sp = (52 if not self.hurry else 80) * (1.3 if k.party else 1.0)
            if abs(d) < 3:
                if random.random() < 0.35:
                    k.mode, k.mode_t = "perch", 0.0
                else:
                    k.tx = random.uniform(24, W - 24)
            else:
                k.x += max(-sp * dt, min(sp * dt, d))
                k.face = 1 if d > 0 else -1
        if self.state not in ("play",) or self.milk_t > 0:
            return
        if k.aim > 0:
            k.aim -= dt
            if k.aim <= 0:
                self.kaw_throw(k)
            return
        k.throw_t -= dt * (1.6 if self.hurry else 1.0)
        if k.throw_t <= 0:
            k.throw_t = k.rate * random.uniform(0.8, 1.2)
            if k.party:
                self.kaw_throw(k)
            else:
                k.aim = 0.42
                k.next_kind = random.choice(self.sd["mix"])
        if k.taunt <= 0 and not k.party:
            k.taunt = random.uniform(6, 11)

    def kaw_throw(self, k):
        x, y = max(14.0, min(W - 14.0, k.x)), k.y + 8
        if k.party:
            if self.sd["bt"] == "fish":
                gold = random.random() < 0.05
                it = Pickup("gfish" if gold else "fish", random.uniform(12, W - 12), 14.0, 150 + 15 * self.tier)
                it.falling, it.life = True, 5.0
                it.vy = 20.0
                self.items.append(it)
            else:
                h = Haz("yarn", x, y, 5)
                h.harmless = True
                h.gold = random.random() < 0.06
                h.life = 9.0
                h.color = "yellow" if h.gold else random.choice(YARN_COLORS)
                self.hz.append(h)
            self.bonus_n += 1
            return
        if self.hype.lucky(0.012 + 0.006 * self.ups["lucky"]):
            it = Pickup("coin", x, y)
            it.falling = True
            self.items.append(it)
            self.hype.banner("KAW DROPPED HIS SHINY!", color="yellow", dur=1.2, scale=1, sound="bonus")
            return
        self.spawn_drop(k.next_kind or "yarn", x, y)
        self.app.audio.play("move")

    def spawn_drop(self, kind, x, y):
        heavy = "heavy" in self.mods
        if kind == "cone":
            h = Haz("cone", x, y, 4)
            h.vy = 40.0
        elif kind == "cushion":
            h = Haz("cushion", x, y, 7)
            h.mode = "fall"
            h.ay = self.support(x, y + 7, H)[0] or FLOOR
        elif kind == "ball":
            h = Haz("ball", x, y, 4)
            h.life = 11.0
        elif kind == "marble":
            h = Haz("marble", x, y, 3)
            h.life = 13.0
        else:
            h = Haz("yarn", x, y, 6 if heavy else 5)
        self.hz.append(h)
        return h

    # ---------------------------------------------------------------- hazards
    def update_hazards(self, dt):
        p = self.p
        frozen = self.milk_t > 0
        for h in self.hz:
            if h.dead:
                continue
            h.age += dt
            h.t += dt
            if h.batted:
                self.update_batted(h, dt)
                continue
            if not frozen:
                h.life -= dt
                self.haz_step(h, dt)
            if h.life <= 0 or h.y > H + 20:
                h.dead = True
                if h.kind == "yarn" and h.life <= 0:
                    self.parts.burst(h.x, h.y, 5, (h.color, "white"), 30, 0.3)
                continue
            if self.state != "play" or p.warp_t > 0 or h.kind == "spritz":
                continue
            self.haz_vs_player(h, frozen)
        self.hz = [h for h in self.hz if not h.dead]

    def haz_step(self, h, dt):
        k = h.kind
        sp = self.hs
        if k in ("yarn", "marble", "dust"):
            base = {"yarn": 50.0, "marble": 88.0, "dust": 58.0}[k] * sp * (1.2 if "heavy" in self.mods and k == "yarn" else 1)
            if k == "yarn" and not h.harmless:
                h.r = max(2.5, h.r - dt * 0.18)
            h.vx = h.dir * base if h.ground is not None else h.vx * 0.98
            was = h.ground
            ev = self.move_haz(h, dt)
            if ev == "wall":
                h.dir = -h.dir
                if h.ground is not None and h.ground.k == 0 and k != "dust":
                    h.dead = True            # rolls out under the sofa
            if h.ground is not None and was is None:
                self.haz_landed(h)
            h.spin += h.vx * dt / max(2.0, h.r)
            if k == "yarn":
                h.path.append((h.x, h.y + h.r - 1))
                if len(h.path) > 14:
                    del h.path[0]
        elif k == "cone":
            h.vy = min(h.vy + 220 * dt, 95 + 25 * sp)
            h.y += h.vy * dt
            h.x += self.wind * 10 * dt
            h.spin += dt * 6
            if h.y >= FLOOR - h.r:
                h.dead = True
                self.parts.burst(h.x, FLOOR - 2, 8, ("brown", "choco", "peach"), 50, 0.4)
                self.app.audio.play("brick")
        elif k == "cushion":
            if h.mode == "fall":
                h.vy = min(h.vy + 400 * dt, 200)
                h.y += h.vy * dt
                if h.y + h.r >= h.ay:
                    h.y = h.ay - h.r
                    h.mode, h.cool = "sit", 3.2
                    self.app.audio.play("lock")
                    self.app.shake(1.5, 0.12)
                    self.parts.burst(h.x, h.ay, 8, ("lavender", "white"), 50, 0.4)
            else:
                h.cool -= dt
                if h.cool <= 0:
                    h.dead = True
                    self.parts.burst(h.x, h.y, 10, ("lavender", "white", "pink"), 50, 0.4)
        elif k == "ball":
            h.vx = h.dir * 46 * sp
            ev = self.move_haz(h, dt, 520)
            if ev == "wall":
                h.dir = -h.dir
            if h.ground is not None:
                if isinstance(h.ground, Seg) and h.ground.k == 0 and (h.x < 8 or h.x > W - 8):
                    h.dead = True
                h.vy = -175.0
                h.ground = None
                h.spin = 0.3
        elif k in ("mouse", "bot"):
            self.patrol(h, dt, sp)
        elif k == "spider":
            top = h.ay
            bot = self.surface(h.k, h.x) - 9
            ph = h.t * (1.1 + 0.05 * self.tier) * sp
            h.y = top + (bot - top) * (0.5 - 0.5 * math.cos(ph))
        elif k == "spritz":
            h.cool -= dt
            if h.cool <= 0 and self.state == "play":
                h.mode = "squirt"
                h.cool = max(1.6, 3.0 - 0.06 * self.tier) / sp
                s = Shot("drop", h.x + h.dir * 8, self.surface(h.k, h.x + h.dir * 8) - 7, h.dir * 100 * sp, 0.0, 2.5, 0.0, 4.0)
                s.k = h.k
                self.shots.append(s)
                self.app.audio.play("bubble")
        elif k == "moth":
            h.x += h.vx * dt
            h.y = h.ay + math.sin(h.t * 4) * 9
            if h.x < -12 or h.x > W + 12:
                h.dead = True

    def haz_landed(self, h):
        g = h.ground
        if isinstance(g, Seg) and g.kind == "bed":
            h.vy = -200.0
            h.ground = None
            g.boing = 0.25
            return
        if isinstance(g, Seg) and g.slope:
            h.dir = g.slope
        if h.kind == "yarn" and h.age > 0.2:
            self.parts.burst(h.x, h.y + h.r, 2, (h.color,), 20, 0.2)

    def patrol(self, h, dt, sp):
        """Toy mice and mini vacs walk their shelf and turn at the ends; mice hop, vacs ride the posts."""
        if h.stun > 0:
            h.stun -= dt
            return
        if h.mode == "climb":
            po = h.post
            h.y += h.cdir * 24 * sp * dt
            h.x = po.x
            if (h.cdir < 0 and h.y + h.r <= po.top) or (h.cdir > 0 and h.y + h.r >= po.bot):
                h.y = (po.top if h.cdir < 0 else po.bot) - h.r
                h.mode = ""
                h.vy = 0.0
                h.ground = self.support(h.x, h.y + h.r - 3, h.y + h.r + 3)[1]
                h.cool = 2.0
            return
        speed = (30 if h.kind == "mouse" else 26) * sp
        if h.ground is not None:
            ahead = self.support(h.x + h.dir * 8, h.y + h.r - 6, h.y + h.r + 6)[1]
            if ahead is None or h.x + h.dir * 8 < 4 or h.x + h.dir * 8 > W - 4:
                h.dir = -h.dir
            po = self.p.climb            # keep clear of the top of the post Mikan is climbing
            if po is not None and abs(h.x + h.dir * 10 - po.x) < 14 and abs(h.y + h.r - po.top) < 6:
                h.dir = 1 if h.x > po.x else -1
            h.vx = h.dir * speed
            h.cool -= dt
            if h.kind == "mouse" and h.cool <= 0:
                h.cool = random.uniform(1.2, 2.4)
                h.vy = -120.0
                h.ground = None
            elif h.kind == "bot" and h.cool <= 0:
                for po in self.posts:
                    if po.rope or abs(po.x - h.x) > 2 or self.p.climb is po:
                        continue
                    feet = h.y + h.r
                    h.cool = 1.5
                    if abs(feet - po.bot) < 3 and random.random() < 0.6:
                        h.mode, h.post, h.cdir, h.ground = "climb", po, -1, None
                        return
                    if abs(feet - po.top) < 3 and random.random() < 0.6:
                        h.mode, h.post, h.cdir, h.ground = "climb", po, 1, None
                        h.y += 2
                        return
                    break
        ev = self.move_haz(h, dt)
        if ev == "wall":
            h.dir = -h.dir

    def haz_vs_player(self, h, frozen):
        p = self.p
        if h.kind == "cushion" and h.mode == "sit":
            if p.ground is None and p.vy > 0 and abs(p.x - h.x) < 10 and h.y - h.r - 3 <= p.y <= h.y:
                p.vy = -205.0
                p.pounce = False
                p.boost = True
                p.air_pounce = True
                self.app.audio.play("jump")
                self.parts.burst(p.x, p.y, 5, ("lavender", "white"), 30, 0.3)
            return
        if self.wand_t > 0 and not h.harmless and h.kind in BOPPABLE + ("bot",) \
                and math.hypot(h.x - p.x, h.y - (p.y - 6)) < self.wand_reach():
            self.bat(h)                      # the feather wand swats anything in reach
            return
        if not self.touch(h):
            if h.kind in ROLLERS and not h.jumped and p.ground is None and p.climb is None \
                    and abs(h.x - p.x) < 5 and h.y - h.r - 34 < p.y < h.y - h.r - 1:
                h.jumped = True
                pts = self.add(100 + 10 * self.tier, h.x, h.y - 12, "white")
                self.hype.hit(1, fever=0.04)
                self.app.audio.play("coin" if pts >= 200 else "fruit")
            return
        if h.harmless:
            if p.pounce or p.ground is None:
                self.bonus_catch(h)
            return
        if p.climb is not None and h.kind in ("mouse", "bot") and not frozen and self.nip_t <= 0:
            h.dir = 1 if h.x > p.x else -1          # patrollers bump into a climbing cat and turn around
            if h.mode == "climb":
                h.cdir = -h.cdir
            return
        if frozen or self.nip_t > 0 or (p.pounce and h.kind in BOPPABLE):
            self.bop(h)
            return
        if p.pounce and h.kind == "bot":
            h.stun = 2.0
            p.vy = -150.0
            p.vx = -p.vx * 0.5
            self.app.audio.play("tin")
            self.floats.add(h.x, h.y - 10, "BONK", "white")
            return
        if h.kind == "bot" and h.stun > 0:
            return
        self.hurt(h)

    def touch(self, h):
        p = self.p
        cx = max(p.x - PW / 2, min(h.x, p.x + PW / 2))
        cy = max(p.y - PH, min(h.y, p.y))
        return (cx - h.x) ** 2 + (cy - h.y) ** 2 < (h.r - 0.5) ** 2

    def bop(self, h):
        """Pounced! The hazard is caught for points (chains within 1.2 s multiply)."""
        h.dead = True
        p = self.p
        self.chain = self.chain + 1 if self.chain_t > 0 else 1
        self.chain_t = 1.2
        self.best_chain = max(self.best_chain, self.chain)
        self.bops += 1
        pts = self.add((200 + 20 * self.tier) * min(8, self.chain), h.x, h.y - 10, "yellow")
        self.hype.hit(1, fever=0.07)
        self.hype.hitstop(0.04)
        self.app.audio.play("pop")
        self.parts.burst(h.x, h.y, 12, (h.color if h.kind == "yarn" else "white", "white", "yellow"), 70, 0.5)
        if p.pounce and p.ground is None:
            p.vy = min(p.vy, -110.0)
        if self.chain == 2:
            self.floats.add(h.x, h.y - 22, "DOUBLE!", "mint")
        elif self.chain == 4:
            self.hype.banner("PURR-FECT CHAIN!", f"+{pts}", rainbow=True, dur=1.3, sound="combo")
            self.hype.slowmo(0.45, 0.5)
            self.hype.shower(30, "stars")
        elif self.chain == 6:
            self.hype.jackpot(10000 + 1000 * self.tier, "POUNCE MASTER!")
        self.maybe_drop(h.x, h.y)

    def bat(self, h):
        """The feather wand swats a hazard back up the tree."""
        if h.batted:
            return
        h.batted = True
        h.harmless = True
        h.ground = None
        h.vy = -260.0
        h.vx = self.p.face * 50.0
        self.p.swipe = 0.18
        self.chain = self.chain + 1 if self.chain_t > 0 else 1
        self.chain_t = 1.2
        self.best_chain = max(self.best_chain, self.chain)
        self.add((150 + 15 * self.tier) * min(8, self.chain), h.x, h.y - 10, "lavender")
        self.hype.hit(1, fever=0.05)
        self.app.audio.play("paddle")
        self.parts.burst(h.x, h.y, 8, ("lavender", "white", "pink"), 60, 0.4)

    def update_batted(self, h, dt):
        if self.boss is not None and not self.boss.dead:
            b = self.boss
            d = max(1.0, math.hypot(b.x - h.x, b.y - h.y))
            h.vx += ((b.x - h.x) / d * 300 - h.vx) * min(1.0, dt * 6)
            h.vy += ((b.y - h.y) / d * 300 - h.vy) * min(1.0, dt * 6)
            if b.hits(h.x, h.y, h.r):
                h.dead = True
                b.hurt(self, 1, "SWAT!")
                self.parts.burst(h.x, h.y, 10, ("lavender", "white"), 60, 0.4)
        else:
            h.vy += 120 * dt
        h.x += h.vx * dt
        h.y += h.vy * dt
        h.spin += dt * 14
        k = self.kaw
        if k is not None and k.mode != "flee" and k.stun <= 0 and abs(h.x - k.x) < 12 and abs(h.y - k.y) < 10:
            h.dead = True
            self.stun_kaw()
        if h.y < -20 or h.y > H + 20 or h.x < -20 or h.x > W + 20:
            h.dead = True

    def stun_kaw(self):
        k = self.kaw
        k.stun = 1.6
        k.aim = 0.0
        k.throw_t = max(k.throw_t, 2.5)
        self.add(1000 + 100 * self.tier, k.x, k.y + 14, "orange")
        self.hype.banner("BULLSEYE!", "KAW IS SEEING STARS", color="orange", dur=1.2, scale=1, sound="boom")
        self.hype.hitstop(0.08)
        self.app.shake(3, 0.25)
        for i in range(3):
            it = Pickup("fish", k.x, k.y + 6, 200 + 20 * self.tier)
            it.falling, it.life = True, 8.0
            it.vx, it.vy = (i - 1) * 40.0, -90.0
            self.items.append(it)

    def maybe_drop(self, x, y):
        luck = self.ups["lucky"]
        r = random.random()
        if r < 0.01 + 0.006 * luck:
            kind = "gfish"
        elif r < 0.04 + 0.015 * luck:
            kind = random.choice(("wand", "bell", "milk", "nip"))
        elif r < 0.2:
            kind = "fish"
        else:
            return
        it = Pickup(kind, x, y, 100 + 20 * self.tier)
        it.falling, it.life = True, 8.0
        it.vy = -110.0
        it.vx = random.uniform(-30, 30)
        self.items.append(it)

    def update_moths(self, dt):
        self.moth_left -= dt
        if self.moth_left <= 0:
            self.moth_left = self.moth_t * random.uniform(0.8, 1.2)
            k = random.randint(1, 4)
            side = random.choice((-1, 1))
            h = Haz("moth", -8 if side > 0 else W + 8, 0, 4)
            h.ay = data.LEVEL_Y[k] - 17
            h.y = h.ay
            h.vx = side * 38 * self.hs
            h.life = 20.0
            self.hz.append(h)

    def wand_spot(self):
        cells = [(k, c) for k in range(1, 4) for c in range(data.NC) if self.lv[k][c] in "=<>"]
        if not cells:
            cells = [(0, c) for c in range(2, data.NC - 2)]
        k, c = random.choice(cells)
        return c * data.CW + 8, k

    def spawn_wand(self):
        x, k = self.wand_spot()
        it = Pickup("wand", x, self.surface(k, x) - 6)
        it.life = 9.0
        self.items.append(it)
        self.parts.burst(x, it.y, 12, ("lavender", "pink", "white"), 50, 0.5)
        self.app.audio.play("bonus")

    # ---------------------------------------------------------------- shots (spritzers and bosses)
    def update_shots(self, dt):
        p = self.p
        for s in self.shots:
            if s.dead:
                continue
            s.age += dt
            if s.kind in ("beam", "jet"):
                if s.age >= s.warn + s.life:
                    s.dead = True
                elif s.age >= s.warn and self.state == "play" and p.warp_t <= 0:
                    if s.age - dt < s.warn:
                        self.app.audio.play("explode" if s.kind == "beam" else "bubble")
                        self.app.shake(2, 0.15)
                    if s.kind == "beam" and abs(p.x - s.x) < 6 + s.r:
                        self.hurt()
                    elif s.kind == "jet" and abs(p.y - 6 - s.y) < 5:
                        self.hurt()
                continue
            if s.batted:
                if self.boss is not None and not self.boss.dead:
                    b = self.boss
                    d = max(1.0, math.hypot(b.x - s.x, b.y - s.y))
                    s.vx, s.vy = (b.x - s.x) / d * 280, (b.y - s.y) / d * 280
                    if b.hits(s.x, s.y, s.r):
                        s.dead = True
                        b.hurt(self, 1, "SWAT!")
                s.x += s.vx * dt
                s.y += s.vy * dt
                if s.y < -10 or s.x < -10 or s.x > W + 10:
                    s.dead = True
                continue
            if s.kind == "spray":
                s.vy += 260 * dt
            elif s.kind == "wave":
                s.y = FLOOR - 4
            s.x += s.vx * dt
            s.y += s.vy * dt
            if s.kind == "drop" and s.k >= 0:
                s.y = self.surface(s.k, s.x) - 7
            s.life -= dt
            if s.life <= 0 or s.x < -10 or s.x > W + 10 or s.y > H + 10 or s.y < -20:
                s.dead = True
                continue
            if s.kind == "spray" and s.vy > 0 and self.support(s.x, s.y - 4, s.y + 1)[1] is not None:
                s.dead = True
                self.parts.burst(s.x, s.y, 4, ("sky", "white"), 30, 0.3)
                continue
            if self.state != "play" or p.warp_t > 0:
                continue
            near = abs(s.x - p.x) < PW / 2 + s.r and p.y - PH - s.r < s.y < p.y + s.r
            if self.wand_t > 0 and s.kind != "wave" and math.hypot(s.x - p.x, s.y - p.y + 6) < self.wand_reach():
                s.batted = True
                p.swipe = 0.18
                self.add(100 + 10 * self.tier, s.x, s.y - 8, "lavender")
                self.app.audio.play("paddle")
                if self.boss is None:
                    s.vy, s.vx = -240.0, 0.0
                continue
            if near:
                s.dead = True
                self.hurt()
        self.shots = [s for s in self.shots if not s.dead]

    # ---------------------------------------------------------------- items and kittens
    def update_items(self, dt):
        p = self.p
        mag = (0, 36, 56, 84)[self.ups["magnet"]]
        for it in self.items:
            it.t += dt
            if it.life > 0:
                it.life -= dt
                if it.life <= 0:
                    it.life = -2.0
                    continue
            d = math.hypot(p.x - it.x, p.y - 6 - it.y)
            if mag and d < mag and self.state == "play" and it.kind not in ("coin",):
                it.x += (p.x - it.x) / max(1.0, d) * 140 * dt
                it.y += (p.y - 6 - it.y) / max(1.0, d) * 140 * dt
                it.falling = False
                if int(self.t * 20) % 4 == 0:
                    self.parts.sparkle(it.x, it.y, "red")
            elif it.falling:
                if it.kind == "coin":
                    it.vy = min(it.vy + 300 * dt, 90)
                    it.y += it.vy * dt
                    if it.y > FLOOR - 4:
                        it.life = -2.0
                        self.parts.burst(it.x, FLOOR - 2, 6, ("yellow", "white"), 40, 0.3)
                        continue
                else:
                    it.vy = min(it.vy + 380 * dt, 160)
                    prev = it.y + 4
                    it.x = max(6.0, min(W - 6.0, it.x + it.vx * dt))
                    it.vx *= 0.98
                    it.y += it.vy * dt
                    if it.vy > 0:
                        y, g = self.support(it.x, prev - 1, it.y + 4)
                        if g is not None:
                            it.y, it.falling, it.vy = y - 4, False, 0.0
            if self.state in ("play", "timeup", "bossdown") and p.warp_t <= 0 \
                    and abs(it.x - p.x) < 9 and p.y - PH - 5 < it.y < p.y + 4:
                it.life = -2.0
                self.collect(it)
        self.items = [i for i in self.items if i.life > 0 or i.life == -1.0]

    def collect(self, it):
        h, au, k = self.hype, self.app.audio, it.kind
        p = self.p
        self.parts.burst(it.x, it.y, 6, ("yellow", "white"), 40, 0.4)
        if k == "fish":
            self.add(it.value, it.x, it.y - 8, "peach")
            h.hit(1, fever=0.03)
            au.play("fruit")
            self.fish_got += 1
            if self.kind == "bonus":
                self.bonus_got += 1
        elif k == "gfish":
            if self.kind == "bonus":
                self.bonus_got += 1
                self.add(2000, it.x, it.y - 8, "yellow")
                au.play("coin")
                h.shower(20, "coins")
            else:
                self.fish_got += 1
                h.jackpot(5000 + 1000 * self.tier, "GOLDEN FISH!")
        elif k == "coin":
            h.jackpot(8000 + 1000 * self.tier, "KAW'S TREASURE!")
        elif k == "wand":
            self.wand_t = 8.0 + 3.0 * self.ups["wand"]
            h.banner("FEATHER WAND!", "SWAT EVERYTHING!", color="lavender", dur=1.2, scale=1, sound="powerup")
        elif k == "bell":
            self.shield = True
            h.banner("JINGLE BELL!", "BLOCKS ONE HIT", color="yellow", dur=1.2, scale=1, sound="powerup")
        elif k == "milk":
            self.milk_t = 5.0
            h.banner("WARM MILK!", "EVERYTHING NAPS - POUNCE!", color="sky", dur=1.4, scale=1, sound="powerup")
            h.flash("white", 0.2)
        elif k == "nip":
            self.nip_t = 6.0
            h.banner("CATNIP ZOOMIES!!", "UNSTOPPABLE!", rainbow=True, dur=1.4, sound="fever")
            h.flash("lime", 0.2)
        elif k == "heart":
            self.lives += 1
            h.banner("1UP!", color="pink", dur=1.0, sound="extra")

    def update_kittens(self, dt):
        p = self.p
        call = self.ups["kitty"]
        for i, kt in enumerate(self.kits):
            kt.t += dt
            if kt.follow:
                n = len([k for k in self.kits[:i] if k.follow])
                idx = max(0, len(p.trail) - 1 - (n + 1) * 9)
                if p.trail:
                    tx, ty = p.trail[idx]
                    kt.x += (tx - kt.x) * min(1.0, dt * 10)
                    kt.y += (ty - kt.y) * min(1.0, dt * 10)
                continue
            if call and self.state == "play" and abs(p.y - kt.y) < 4 and abs(p.x - kt.x) < 40 + 30 * call:
                kt.x += (1 if p.x > kt.x else -1) * 30 * dt
            if self.state in ("play",) and abs(kt.x - p.x) < 10 and p.y - PH - 4 < kt.y < p.y + 4:
                kt.follow = True
                self.got_kits += 1
                self.kittens_saved += 1
                self.add(500, kt.x, kt.y - 12, "pink")
                self.app.audio.play("bonus")
                self.hype.hit(1, fever=0.05)
                self.parts.burst(kt.x, kt.y - 4, 10, ("pink", "white"), 50, 0.5)
                if self.got_kits == len(self.kits) and len(self.kits) >= 2:
                    self.hype.banner("FAMILY REUNION!", "ALL KITTENS SAFE", color="pink", dur=1.6, sound="extra")
                    self.hype.shower(30, "hearts")
                else:
                    self.floats.add(kt.x, kt.y - 20, "MEW!", "pink")

    # ---------------------------------------------------------------- boss stages (API used by the boss)
    def shoot(self, kind, x, y, vx, vy, r=2.0, warn=0.0, life=6.0):
        s = Shot(kind, x, y, vx, vy, r, warn, life)
        self.shots.append(s)
        return s

    def spawn_haz(self, kind, x, y, vx=0.0, vy=0.0):
        r = {"dust": 4, "mouse": 5, "yarn": 5, "cone": 4}.get(kind, 4)
        h = Haz(kind, x, y, r)
        h.vx, h.vy = vx, vy
        h.dir = 1 if vx > 0 else -1
        h.life = 12.0 if kind != "mouse" else 14.0
        self.hz.append(h)
        return h

    def boss_defeated(self):
        self.state, self.state_t = "bossdown", 0.0
        h = self.hype
        h.banners = []
        h.slowmo(0.3, 1.6)
        h.flash("white", 0.4)
        h.banner("BOSS DOWN!!", f"{self.boss.name} GIVES UP!", rainbow=True, dur=2.6, sound="bossdown")
        self.app.shake(6, 0.8)
        self.add(10000 + 5000 * self.tier, self.boss.x, self.boss.y - 24, "yellow")
        for s in self.shots:
            s.dead = True
        for hz in self.hz:
            hz.dead = True
            self.parts.burst(hz.x, hz.y, 8, ("white", "gray"), 60, 0.5)
        self.hz = []
        self.shots = []

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
            it = Pickup("gfish" if i % 6 == 0 else "fish", b.x, b.y, 300 + 50 * self.tier)
            it.falling, it.life = True, 9.0
            it.vx = math.cos(i * math.tau / 12) * 80
            it.vy = -200 - (i % 3) * 40
            self.items.append(it)

    # ---------------------------------------------------------------- bonus stages
    def update_bonus(self, dt):
        if self.state != "play":
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0
            self.state, self.state_t = "timeup", 0.0
            self.hype.banner("TIME UP!", color="yellow", dur=1.4, sound="levelup")
            for it in self.items:
                if it.life > 0:
                    it.life = -2.0
            for h in self.hz:
                h.dead = True
                self.parts.burst(h.x, h.y, 4, (h.color, "white"), 30, 0.3)
            self.hz = []
            if self.kaw:
                self.kaw.mode = "flee"

    def bonus_catch(self, h):
        h.dead = True
        self.bonus_got += 1
        pts = 1000 if h.gold else 200 + 20 * self.tier
        self.add(pts, h.x, h.y - 10, "yellow" if h.gold else "white")
        self.hype.hit(1, fever=0.04)
        self.app.audio.play("coin" if h.gold else "pop")
        self.parts.burst(h.x, h.y, 8, (h.color, "white"), 50, 0.4)

    # ---------------------------------------------------------------- tally
    def start_tally(self):
        rows = []
        tr = self.tier
        if self.kind == "normal":
            rows.append(["CLIMBED!", 1000 + 200 * tr])
            tb = max(0, int((self.sd["par"] - self.level_t) * 60))
            if tb:
                rows.append(["TIME BONUS", tb])
            if not self.missed:
                rows.append(["NO MISS", 3000])
            if self.kits:
                kb = int(1000 * self.got_kits * (1 + 0.5 * self.ups["kitty"]))
                rows.append([f"KITTENS {self.got_kits}/{len(self.kits)}", kb])
                if self.got_kits == len(self.kits):
                    rows.append(["ALL KITTENS!", 3000])
            if self.fish_total and self.fish_got >= self.fish_total:
                rows.append(["ALL FISH", 2000])
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
            word = "FISH" if self.sd["bt"] == "fish" else "YARN"
            rows.append([f"{word} {self.bonus_got}/{self.bonus_n}", 50 * self.bonus_got])
            if self.bonus_n and self.bonus_got >= self.bonus_n * 0.8:
                rows.append(["PURR-FECT!!", 10000])
                self.hype.banner("PURR-FECT!!", rainbow=True, dur=1.8, sound="win")
                self.hype.shower(60, "coins")
            elif self.bonus_n and self.bonus_got >= self.bonus_n * 0.5:
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
        th = self.theme
        backdrop(s, th, self.t, self.tier)
        s.blit(self.field, (0, 0))
        for hm in self.hams:
            draw_hammock(s, hm, th)
        for sg in self.segs:
            if sg.kind != "plank":
                draw_special(s, sg, th, self.t)
        for it in self.items:
            if it.life < 0 or it.life > 2 or int(it.life * 10) % 2:
                draw_item(s, it, self.t)
        for kt in self.kits:
            if not kt.follow:
                draw_kitten(s, kt, self.t)
        for h in self.hz:
            draw_haz(s, h, self.t, self.milk_t > 0)
        if self.kaw is not None:
            self.draw_kaw(s)
        if self.boss is not None:
            self.boss.draw(s, self.t)
        for kt in self.kits:
            if kt.follow:
                draw_kitten(s, kt, self.t)
        self.draw_player(s)
        for sh in self.shots:
            draw_shot(s, sh, self.t)
        self.parts.draw(s)
        self.floats.draw(s)
        if "dark" in self.mods and self.state not in ("intro", "tally"):
            self.darkness(s)
        self.hud(s)
        self.overlays(s)

    def draw_player(self, s):
        p = self.p
        st = self.state
        if st == "over" or p.warp_t > 0:
            return
        if self.kind == "normal" and st in ("clear", "tally"):
            img = sprite("tt_mikan_nap")
            s.blit(img, (int(p.x) - 8, int(p.y) - 1))
            if int(self.t * 2) % 2:
                draw_text(s, "Z", int(p.x) + 8, int(p.y) - 10 - int(self.t * 8) % 6, "sky", shadow=None)
            return
        if p.inv > 0 and st != "dead" and int(p.inv * 12) % 2:
            return
        flip = p.face < 0
        if st == "dead":
            img = sprite("tt_mikan_hurt", 0, flip)
        elif p.climb is not None:
            img = sprite("tt_mikan_climb", int(p.anim * 6))
            s.blit(img, (int(p.x) - 7, int(p.y) - 13))
            img = None
        elif p.pounce:
            img = sprite("tt_mikan_pounce", 0, flip)
        elif p.ground is None:
            img = sprite("tt_mikan_jump", 0, flip)
        elif abs(p.vx) > 1:
            img = sprite("tt_mikan_walk", int(p.anim * 10), flip)
        else:
            img = sprite("tt_mikan_idle", 1 if int(self.t * 10) % 31 == 0 else 0, flip)
        if img is not None:
            s.blit(img, (int(p.x) - 8, int(p.y) - 13))
        if self.nip_t > 0:
            for i in range(3):
                a = self.t * 9 + i * 2.1
                s.fill(col(rainbow(i, self.t)), (int(p.x + math.cos(a) * 9), int(p.y - 6 + math.sin(a) * 7), 2, 2))
        if self.shield and st != "dead":
            s.blit(sprite("tt_bell"), (int(p.x) - 3 + (3 if p.face > 0 else -3), int(p.y) - 5))
        if self.wand_t > 0 and st != "dead":
            wx = int(p.x) + (5 if p.face > 0 else -13)
            s.blit(sprite("tt_wand", 0, p.face < 0), (wx, int(p.y) - 16))
            if p.swipe > 0:
                rr = self.wand_reach()
                a0 = -1.6 + (1 - p.swipe / 0.18) * 3.0
                for i in range(6):
                    a = a0 + i * 0.12
                    s.fill(col("white" if i % 2 else "lavender"),
                           (int(p.x + p.face * math.cos(a) * rr), int(p.y - 6 + math.sin(a) * rr), 2, 2))
            if self.wand_t < 2 and int(self.t * 8) % 2:
                pass
            else:
                s.fill(col("lavender"), (int(p.x) - 6, int(p.y) - 17, int(12 * self.wand_t / (8 + 3 * self.ups["wand"])), 1))

    def draw_kaw(self, s):
        k = self.kaw
        if k.y < -20:
            return
        x, y = int(k.x) - 8, int(k.y) - 6
        flip = k.face > 0
        if k.stun > 0:
            s.blit(sprite("tt_kaw_dazed", 0, flip), (x, y))
            for i in range(3):
                a = self.t * 6 + i * 2.1
                s.fill(col("yellow"), (int(k.x + math.cos(a) * 9), int(k.y - 8 + math.sin(a) * 3), 2, 2))
            return
        if k.mode == "perch" and k.aim <= 0:
            s.blit(sprite("tt_kaw_perch", 0, flip), (x, y))
        else:
            fr = int(self.t * (14 if k.aim > 0 else 8)) % 3
            s.blit(sprite("tt_kaw_fly", fr, flip), (x, y))
        if k.party:
            pygame.draw.polygon(s, col(rainbow(0, self.t)), [(x + 4, y + 1), (x + 8, y + 1), (x + 6, y - 6)])
            s.fill(col("yellow"), (x + 5, y - 7, 2, 2))
        if k.aim > 0:
            draw_text(s, "!", int(k.x), int(k.y) - 18, "red" if int(self.t * 12) % 2 else "yellow", align="center",
                      shadow=None)
            kind = k.next_kind
            if kind in ("cone", "cushion"):        # show where it will land
                yy = self.support(k.x, k.y + 8, H)[0] or FLOOR
                if kind == "cone":
                    yy = FLOOR
                if int(self.t * 12) % 2:
                    pygame.draw.ellipse(s, col("black"), (int(k.x) - 6, int(yy) - 2, 12, 3))
        elif k.taunt > 0 and k.taunt < 1.0 and self.state == "play":
            panel(s, (int(k.x) - 14, int(k.y) - 22, 28, 11), fill="white", border="black", radius=3, shadow=False)
            draw_text(s, "KAW!", int(k.x), int(k.y) - 20, "black", align="center", shadow=None)

    def darkness(self, s):
        p = self.p
        R = 60
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        c = (12, 8, 24, 205)
        cx, cy = int(p.x), int(p.y - 6)
        for y in range(HUD_H, H):
            dy = y - cy
            if abs(dy) < R:
                half = int(math.sqrt(R * R - dy * dy))
                ov.fill(c, (0, y, max(0, cx - half), 1))
                ov.fill(c, (cx + half, y, W - (cx + half), 1))
            else:
                ov.fill(c, (0, y, W, 1))
        s.blit(ov, (0, 0))

    def hud(self, s):
        s.fill(col("black"), (0, 0, W, HUD_H))
        draw_text(s, f"{self.score:07d}", 3, 2, "white", shadow=None)
        self.hearts(s, 48, 2, self.lives, max_show=5)
        if self.kind == "bonus" and self.state in ("play", "intro"):
            draw_text(s, f"TIME {int(math.ceil(self.time_left)):2d}", 140, 2,
                      "yellow" if self.time_left > 5 or int(self.t * 8) % 2 else "red", align="center", shadow=None)
        else:
            draw_text(s, f"HI {max(self.best, self.score):07d}", 140, 2, "lavender", align="center", shadow=None)
        s.blit(sprite("tt_kitten", 0, remap=art.KITTEN_COLORS[3]), (186, 2))
        draw_text(s, f"{self.kittens_saved}", 196, 2, "pink", shadow=None)
        draw_text(s, f"STAGE {self.stage}", W - 3, 2, "yellow", align="right", shadow=None)
        h = self.hype
        if self.kind == "bonus" and self.state in ("play", "intro"):
            s.fill(col("yellow"), (0, HUD_H - 1, int(W * self.time_left / float(self.sd["time"])), 1))
        elif h.fever_on:
            s.fill(col(rainbow(0, self.t)), (0, HUD_H - 1, int(W * h.fever_t / h.FEVER_TIME), 1))
        else:
            s.fill(col("hotpink"), (0, HUD_H - 1, int(W * h.fever), 1))
        if self.boss is not None and not self.boss.dead and self.state not in ("warning", "tally"):
            boss_bar(s, self.boss.name, self.boss.hp, self.boss.maxhp, self.t, y=HUD_H + 1)
        if self.kind == "normal" and self.state == "play":
            left = max(0, int(self.sd["par"] - self.level_t))
            if not self.hurry:
                draw_text(s, f"{left}", W - 3, HUD_H + 2, "white" if left > 10 else "red", align="right", shadow="ink")

    def overlays(self, s):
        st = self.state
        if st == "intro" and self.kind == "normal":
            self.stage_card(s)
        elif st == "warning":
            self.warning_card(s)
        elif st == "tally":
            self.tally_card(s)
        elif self.hurry and st == "play" and self.level_t < self.sd["par"] + 2.5 and int(self.t * 6) % 2:
            draw_text(s, "HURRY!", W // 2, 100, "red", 2, align="center", outline="black")

    def stage_card(self, s):
        k = min(1.0, self.state_t * 5)
        y = int(46 - (1 - k) * 80)
        sd = self.sd
        th = self.theme
        lines = [data.MODS[m][0] for m in self.mods]
        news = []
        if sd["new"]:
            news.append(("haz", sd["new"]) + tuple(data.HAZARDS[sd["new"]][::2]))
        if sd["nst"]:
            news.append(("st", sd["nst"]) + (data.STRUCTS[sd["nst"]][0], data.STRUCTS[sd["nst"]][2]))
        hh = 64 + 10 * len(lines) + 20 * len(news)
        panel(s, (52, y, 216, hh), fill="ink", border=th[3])
        draw_text(s, f"STAGE {self.stage}", W // 2, y + 7, "yellow", 2, align="center", outline="black")
        draw_text(s, th[0], W // 2, y + 26, th[3], align="center", shadow=None)
        draw_text(s, f'"{sd["nm"]}"', W // 2, y + 37, "white", align="center", shadow=None)
        s.blit(sprite("tt_mikan_idle", 0), (62, y + 46))
        draw_text(s, sd.get("quip", ""), 82, y + 50, "peach", shadow=None)
        yy = y + 62
        for ln in lines:
            draw_text(s, "* " + ln + " *", W // 2, yy, "lime", align="center", shadow=None)
            yy += 10
        for kind, key, nm, blurb in news:
            if kind == "haz":
                h = Haz(key, 74, yy + 5, 5)
                h.ay = yy - 2
                h.k = 0
                draw_haz(s, h, self.t, False, icon=True)
            else:
                draw_struct_icon(s, key, 66, yy, self.theme, self.t)
            draw_text(s, f"NEW! {nm}", 92, yy, "hotpink", shadow=None)
            draw_text(s, blurb, 92, yy + 9, "white", shadow=None)
            yy += 20

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
        draw_text(s, "SOMETHING BIG IS CLIMBING THE TREE", W // 2, 96, "white", align="center", outline="black")
        draw_text(s, self.boss.name, W // 2, 110, "yellow", 2, align="center", outline="black")

    def tally_card(self, s):
        n = len(self.tally)
        hh = 46 + n * 11
        y0 = 100 - hh // 2
        panel(s, (64, y0, 192, hh), fill="ink", border="mint")
        title = {"normal": "PERCH WON!", "boss": "BOSS DEFEATED!", "bonus": "BONUS RESULT"}[self.kind]
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


# ----------------------------------------------------------------------------- drawing helpers (shared with iOS)
def backdrop(s, th, t, tr=0):
    name, wa, wb, carpet, carpet_d, post, stripe, style, accent = th
    for y in range(HUD_H, H, 4):
        s.fill(lerp_col(wa, wb, (y - HUD_H) / (H - HUD_H)), (0, y, W, 4))
    shade = lerp_col(wa, "black", 0.3)
    light = lerp_col(wa, "white", 0.18)
    if style == "window":
        pygame.draw.rect(s, shade, (196, 26, 96, 70))
        pygame.draw.rect(s, col("sky" if tr != 6 else "night"), (200, 30, 88, 62))
        pygame.draw.circle(s, col("yellow"), (268, 48), 9)
        for i in range(3):
            cx = int((i * 41 + t * 4) % 110) + 190
            pygame.draw.ellipse(s, col("white"), (cx, 62 + i * 9, 18, 6))
        s.fill(shade, (242, 30, 4, 62))
        s.fill(shade, (200, 59, 88, 3))
        s.fill(col(accent), (192, 22, 104, 4))
    elif style == "tiles":
        for x in range(0, W, 20):
            s.fill(shade, (x, HUD_H, 1, H))
        for y in range(HUD_H, H, 20):
            s.fill(shade, (0, y, W, 1))
    elif style == "books":
        for row in range(4):
            y = 30 + row * 40
            s.fill(shade, (0, y + 22, W, 3))
            for i in range(24):
                h = 12 + (i * 7 + row * 3) % 9
                c = ("red", "blue", "lime", "yellow", "lavender", "teal")[(i + row) % 6]
                s.fill(lerp_col(c, wb, 0.55), (i * 13 + row * 5, y + 22 - h, 10, h))
    elif style == "bubbles":
        for i in range(14):
            x = (i * 53 + t * (3 + i % 3)) % W
            y = HUD_H + (i * 37 - t * 6) % (H - HUD_H)
            pygame.draw.circle(s, light, (int(x), int(y)), 3 + i % 4, 1)
    elif style == "leaves":
        for i in range(18):
            x = (i * 47 + int(t * 5)) % W
            y = HUD_H + (i * 29 + int(t * 9)) % (H - HUD_H)
            pygame.draw.ellipse(s, shade, (x, y, 6, 3))
    elif style == "stars":
        for i in range(36):
            x, y = (i * 67) % W, HUD_H + (i * 31) % (H - HUD_H)
            c = col("white") if int(t * 2 + i) % 7 == 0 else light
            s.fill(c, (x, y, 1, 1))
        pygame.draw.circle(s, col("cream"), (60, 40), 10)
        pygame.draw.circle(s, col(wa), (64, 37), 9)
    elif style == "beams":
        for x in range(10, W, 70):
            s.fill(shade, (x, HUD_H, 8, H))
        pygame.draw.polygon(s, shade, [(0, HUD_H), (W // 2, HUD_H + 30), (W, HUD_H), (W, HUD_H + 6), (W // 2, HUD_H + 36),
                                       (0, HUD_H + 6)])
    elif style == "rain":
        pygame.draw.rect(s, shade, (30, 30, 70, 60))
        for i in range(30):
            x = (i * 29 + int(t * 8)) % W
            y = HUD_H + (i * 47 + int(t * 90)) % (H - HUD_H)
            s.fill(light, (x, y, 1, 5))
    elif style == "stripes":
        for x in range(0, W, 16):
            s.fill(shade, (x, HUD_H, 6, H))
    elif style == "snow":
        for i in range(40):
            x = (i * 37 + int(math.sin(t + i) * 4)) % W
            y = HUD_H + (i * 53 + int(t * 14)) % (H - HUD_H)
            s.fill(col("white"), (x, y, 1 + i % 2, 1 + i % 2))
    elif style == "polka":
        for i in range(30):
            x, y = (i * 61) % W, HUD_H + (i * 43) % (H - HUD_H)
            pygame.draw.circle(s, light, (x, y), 4)
    elif style == "notes":
        for i in range(10):
            x = (i * 71 + int(t * 6)) % W
            y = HUD_H + 10 + (i * 37) % 150 + int(math.sin(t * 2 + i) * 3)
            s.fill(light, (x, y, 1, 7))
            pygame.draw.circle(s, light, (x - 2, y + 7), 2)
    elif style == "clouds":
        for i in range(7):
            x = int((i * 59 + t * (4 + i)) % (W + 60)) - 30
            y = HUD_H + 14 + (i * 27) % 150
            pygame.draw.ellipse(s, light, (x, y, 34, 10))
            pygame.draw.ellipse(s, light, (x + 8, y - 5, 18, 10))
    # the rug under the tree
    s.fill(col(carpet_d), (0, FLOOR, W, H - FLOOR))
    for x in range(0, W, 8):
        s.fill(col(accent), (x + 2, FLOOR + 4, 4, 1))


def draw_plank(f, sg, th, lv):
    carpet, carpet_d = th[3], th[4]
    k = sg.k
    c0, c1 = sg.x0 // data.CW, sg.x1 // data.CW - 1
    open_l = c0 == 0 or not data.solid(lv, k, c0 - 1)
    open_r = c1 == data.NC - 1 or not data.solid(lv, k, c1 + 1)
    for x in range(sg.x0, sg.x1):
        if (x == sg.x0 and open_l) or (x == sg.x1 - 1 and open_r):
            inset = 1
        else:
            inset = 0
        y = int(sg.y(x + 0.5))
        th_ = 5 if k > 0 else 3
        f.fill(col("black"), (x, y + inset, 1, th_ + 1 - inset))
        f.fill(col(carpet_d), (x, y + 1 + inset, 1, th_ - 1 - inset))
        f.fill(col(carpet), (x, y + inset, 1, 2 - inset))
        if (x * 7 + k * 3) % 11 == 0:
            f.fill(col("white"), (x, y + 1, 1, 1))


def draw_post(f, po, th, t):
    post, stripe = th[5], th[6]
    top, bot = int(po.top), int(po.bot)
    if po.rope:
        for y in range(top, bot):
            dx = 0
            f.fill(col(stripe if (y // 2) % 2 else post), (po.x - 1 + dx, y, 2, 1))
        pygame.draw.circle(f, col(stripe), (po.x, bot), 2)
        f.fill(col(post), (po.x - 1, bot + 1, 2, 3))
        return
    f.fill(col("black"), (po.x - 4, top, 8, bot - top))
    for y in range(top, bot):
        for x in range(po.x - 3, po.x + 3):
            c = stripe if ((y + x) // 2) % 3 == 0 else post
            f.fill(col(c), (x, y, 1, 1))


def draw_tunnel(f, x, y):
    x, y = int(x), int(y)
    f.fill(col("black"), (x - 8, y - 11, 16, 11))
    f.fill(col("peach"), (x - 7, y - 10, 14, 10))
    f.fill(col("brown"), (x - 7, y - 10, 14, 2))
    pygame.draw.ellipse(f, col("black"), (x - 4, y - 7, 8, 7))
    f.fill(col("brown"), (x - 1, y - 10, 2, 2))


def draw_cushion(f, x, y):
    x, y = int(x), int(y)
    pygame.draw.ellipse(f, col("black"), (x - 12, y - 9, 24, 10))
    pygame.draw.ellipse(f, col("purple"), (x - 11, y - 8, 22, 8))
    pygame.draw.ellipse(f, col("lavender"), (x - 10, y - 8, 20, 5))
    f.fill(col("yellow"), (x - 1, y - 6, 2, 2))
    for dx in (-12, 11):
        f.fill(col("yellow"), (x + dx, y - 3, 1, 3))


def draw_hammock(s, hm, th):
    x, y = int(hm.x), int(hm.y)
    for dx in (1, 30):
        s.fill(col(th[6]), (x + dx, y - 14, 1, 14))
    pygame.draw.polygon(s, col("black"), [(x, y - 1), (x + 32, y - 1), (x + 28, y + 5), (x + 4, y + 5)])
    pygame.draw.polygon(s, col(th[8]), [(x + 1, y), (x + 31, y), (x + 27, y + 4), (x + 5, y + 4)])
    for i in range(4, 28, 6):
        s.fill(col("white"), (x + i, y + 1, 2, 1))


def draw_special(s, sg, th, t, oy=0):
    if sg.kind == "bed":
        for c in range(sg.x0, sg.x1, data.CW):
            x = c + 8
            y = int(sg.y(x) + oy)
            sq = 2 if sg.boing > 0 else 0
            pygame.draw.ellipse(s, col("black"), (x - 8, y - 4 + sq, 16, 9 - sq))
            pygame.draw.ellipse(s, col("hotpink"), (x - 7, y - 3 + sq, 14, 7 - sq))
            pygame.draw.ellipse(s, col("pink"), (x - 5, y - 2 + sq, 10, 3))
            s.fill(col("white"), (x - 3, y - 2 + sq, 2, 1))
    elif sg.kind == "box":
        if sg.gone > 0:
            if sg.gone < 0.6 and int(t * 12) % 2:
                for c in range(sg.x0, sg.x1, 4):
                    s.fill(col("peach"), (c, int(sg.y(c) + oy), 2, 1))
            return
        shake = int(math.sin(t * 60) * 1.5) if sg.stand > 0.05 else 0
        for c in range(sg.x0, sg.x1, data.CW):
            y = int(sg.y(c + 8) + oy)
            s.fill(col("black"), (c + shake, y - 1, 16, 8))
            s.fill(col("peach"), (c + 1 + shake, y, 14, 6))
            s.fill(col("brown"), (c + 1 + shake, y, 14, 1))
            s.fill(col("orange"), (c + 7 + shake, y, 2, 6))
            if sg.stand > 0.2:
                pygame.draw.line(s, col("black"), (c + 3 + shake, y + 1), (c + 6 + shake, y + 4))
    elif sg.kind == "belt":
        for x in range(sg.x0, sg.x1):
            y = int(sg.y(x + 0.5) + oy)
            s.fill(col("black"), (x, y, 1, 6))
            s.fill(col("darkgray"), (x, y + 1, 1, 4))
            ph = int(x - sg.belt * t * 32) % 8
            if ph < 2:
                s.fill(col("yellow"), (x, y + 2, 1, 2))
        for x in (sg.x0, sg.x1 - 1):
            pygame.draw.circle(s, col("gray"), (x, int(sg.y(x) + oy) + 3), 3)


def draw_struct_icon(s, ch, x, y, th, t):
    """Small picture of a tree part for the NEW! line of the stage card (y = top of the line)."""
    floor = data.LEVEL_Y[0]
    if ch == "R":
        for yy in range(y - 2, y + 14):
            s.fill(col(th[6] if (yy // 2) % 2 else th[5]), (x + 8, yy, 2, 1))
    elif ch == "~":
        hm = Ham(x - 6, x - 6, 0, 0.0)
        hm.x, hm.y = float(x - 6), float(y + 12)
        draw_hammock(s, hm, th)
    elif ch == "S":
        draw_special(s, Seg(x, x + 16, 0, 0, "bed"), th, t, y + 10 - floor)
    elif ch == "X":
        draw_special(s, Seg(x, x + 16, 0, 0, "box"), th, t, y + 8 - floor)
    elif ch in "<>":
        draw_special(s, Seg(x - 2, x + 20, 0, 0, "belt", 1), th, t, y + 6 - floor)
    elif ch == "W":
        draw_tunnel(s, x + 8, y + 14)


def draw_item(s, it, t):
    x, y = int(it.x), int(it.y)
    bob = int(math.sin(it.t * 4) * 1.5) if not it.falling else 0
    k = it.kind
    if k == "fish":
        s.blit(sprite("tt_fish"), (x - 5, y - 3 + bob))
    elif k == "gfish":
        s.blit(sprite("tt_fish", 0, remap=art.GOLD_FISH), (x - 5, y - 3 + bob))
        if int(t * 8) % 2:
            s.fill(col("white"), (x + 2, y - 4 + bob, 1, 1))
    elif k == "coin":
        s.blit(sprite("tt_coin"), (x - 3, y - 3))
        if int(t * 10) % 2:
            s.fill(col("white"), (x - 5, y - 5, 1, 1))
    elif k == "heart":
        s.blit(sprite("heart"), (x - 3, y - 3 + bob))
    else:
        name = {"wand": "tt_wand", "bell": "tt_bell", "milk": "tt_milk", "nip": "tt_nip"}[k]
        img = sprite(name)
        pygame.draw.circle(s, col("white" if int(t * 6) % 2 else "lavender"), (x, y + bob), 7, 1)
        s.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2 + bob))


def draw_kitten(s, kt, t):
    x, y = int(kt.x), int(kt.y)
    fr = int(kt.t * (6 if kt.follow else 2)) % 2
    hop = -int(abs(math.sin(kt.t * 8)) * 2) if kt.follow else 0
    s.blit(sprite("tt_kitten", fr, remap=art.KITTEN_COLORS[kt.color]), (x - 4, y - 7 + hop))
    if not kt.follow and int(kt.t * 1.5) % 3 == 0:
        draw_text(s, "MEW", x, y - 16, "pink", align="center", shadow="ink")


def draw_haz(s, h, t, frozen, icon=False):
    x, y, r = int(h.x), int(h.y), int(round(h.r))
    k = h.kind
    if k == "yarn":
        c = h.color
        for i in range(1, len(h.path)):
            if i % 2:
                s.fill(col(c), (int(h.path[i][0]), int(h.path[i][1]), 1, 1))
        pygame.draw.circle(s, col("black"), (x, y), r + 1)
        pygame.draw.circle(s, col(c), (x, y), r)
        for j in range(2):
            a = h.spin + j * 1.6
            dx, dy = math.cos(a) * r, math.sin(a) * r
            pygame.draw.line(s, lerp_col(c, "black", 0.35), (int(x - dx * 0.8), int(y - dy * 0.8)),
                             (int(x + dx * 0.8), int(y + dy * 0.8)))
        s.fill(col("white"), (x - 2, y - 2, 1, 1))
        if h.gold and int(t * 10) % 2:
            s.fill(col("white"), (x + 2, y - 4, 1, 1))
    elif k == "marble":
        pygame.draw.circle(s, col("black"), (x, y), r + 1)
        pygame.draw.circle(s, col("sky"), (x, y), r)
        s.fill(col("white"), (x - 1, y - 1, 1, 1))
    elif k == "dust":
        for a in range(0, 360, 60):
            rr = math.radians(a + h.spin * 40)
            pygame.draw.circle(s, col("darkgray"), (int(x + math.cos(rr) * 3), int(y + math.sin(rr) * 3)), 2)
        pygame.draw.circle(s, col("gray"), (x, y), 3)
        s.fill(col("black"), (x - 2, y - 1, 1, 1))
        s.fill(col("black"), (x + 1, y - 1, 1, 1))
    elif k == "cone":
        pygame.draw.ellipse(s, col("black"), (x - 4, y - 5, 9, 11))
        pygame.draw.ellipse(s, col("brown"), (x - 3, y - 4, 7, 9))
        for j in range(3):
            s.fill(col("choco"), (x - 2 + (j % 2) * 2, y - 2 + j * 2, 2, 1))
        s.fill(col("lime"), (x - 1, y - 6, 2, 2))
    elif k == "cushion":
        pygame.draw.rect(s, col("black"), (x - 9, y - 6, 18, 12), border_radius=4)
        pygame.draw.rect(s, col("lavender"), (x - 8, y - 5, 16, 10), border_radius=4)
        pygame.draw.rect(s, col("purple"), (x - 8, y + 2, 16, 3), border_radius=2)
        s.fill(col("yellow"), (x - 1, y - 1, 2, 2))
    elif k == "ball":
        sq = 1 if h.spin > 0.2 else 0
        h.spin = max(0.0, h.spin - 0.02)
        pygame.draw.ellipse(s, col("black"), (x - r - 1, y - r - 1 + sq, 2 * r + 3, 2 * r + 3 - sq))
        pygame.draw.ellipse(s, col("red"), (x - r, y - r + sq, 2 * r + 1, 2 * r + 1 - sq))
        s.fill(col("yellow"), (x - r, y, 2 * r + 1, 1))
        s.fill(col("white"), (x - 2, y - 2, 1, 1))
    elif k == "mouse":
        flip = h.dir < 0
        d = -1 if flip else 1
        pygame.draw.ellipse(s, col("black"), (x - 7, y - 4, 14, 9))
        pygame.draw.ellipse(s, col("gray"), (x - 6, y - 3, 12, 7))
        pygame.draw.circle(s, col("pink"), (x + d * 3, y - 4), 2)
        s.fill(col("black"), (x + d * 4, y - 1, 1, 1))
        s.fill(col("pink"), (x + d * 7, y, 1, 1))
        pygame.draw.line(s, col("pink"), (x - d * 6, y + 1), (x - d * 10, y - 2))
        kw = 1 + int(abs(math.sin(t * 8)) * 2)
        s.fill(col("yellow"), (x - kw, y - 7, kw * 2 + 1, 1))
        s.fill(col("yellow"), (x, y - 6, 1, 2))
    elif k == "spider":
        if not icon:
            s.fill(col("white"), (x, int(h.ay) - 2, 1, max(0, y - int(h.ay) + 2)))
        else:
            s.fill(col("white"), (x, y - 8, 1, 6))
        pygame.draw.circle(s, col("black"), (x, y), 4)
        for side in (-1, 1):
            for j in range(3):
                leg = int(math.sin(t * 10 + j) * 1)
                s.fill(col("black"), (x + side * (4 + j % 2), y - 2 + j * 2 + leg, 3 * side if side > 0 else 3, 1))
        s.fill(col("red"), (x - 2, y - 1, 1, 1))
        s.fill(col("red"), (x + 1, y - 1, 1, 1))
    elif k == "spritz":
        d = h.dir
        bx = x - 4
        pygame.draw.rect(s, col("black"), (bx - 1, y - 6, 10, 16), border_radius=2)
        pygame.draw.rect(s, col("sky"), (bx, y - 5, 8, 14), border_radius=2)
        s.fill(col("white"), (bx + 1, y - 2, 6, 4))
        s.fill(col("blue"), (bx + 2, y - 9, 4, 4))
        s.fill(col("blue"), (x + d * 4 - (0 if d > 0 else 2), y - 9, 3, 2))
        if h.cool < 0.6 and int(t * 16) % 2:
            s.fill(col("white"), (x + d * 7, y - 9, 1, 1))
    elif k == "bot":
        w = 7
        pygame.draw.ellipse(s, col("black"), (x - w - 1, y - 4, 2 * w + 3, 9))
        pygame.draw.ellipse(s, col("darkgray"), (x - w, y - 3, 2 * w + 1, 7))
        s.fill(col("gray"), (x - 4, y - 3, 9, 2))
        s.fill(col("red" if int(t * 4) % 2 else "lime") if h.stun <= 0 else col("yellow"), (x - 1, y - 2, 3, 1))
        if h.stun > 0:
            for i in range(2):
                a = t * 8 + i * 3.1
                s.fill(col("yellow"), (int(x + math.cos(a) * 6), int(y - 7 + math.sin(a) * 2), 1, 1))
    elif k == "moth":
        fl = int(abs(math.sin(t * 16)) * 3)
        pygame.draw.ellipse(s, col("lavender"), (x - 6, y - 2 - fl, 5, 4 + fl))
        pygame.draw.ellipse(s, col("lavender"), (x + 2, y - 2 - fl, 5, 4 + fl))
        s.fill(col("black"), (x - 1, y - 2, 3, 5))
        s.fill(col("white"), (x - 4, y - 1, 1, 1))
    if frozen and k not in ("spritz",) and not icon:
        draw_text(s, "Z", x + 4, y - 10 - int(t * 6) % 4, "sky", shadow=None)


def draw_shot(s, sh, t):
    x, y = int(sh.x), int(sh.y)
    k = sh.kind
    if k in ("drop", "spray"):
        pygame.draw.circle(s, col("blue"), (x, y), int(sh.r) + 1)
        pygame.draw.circle(s, col("sky"), (x, y), int(sh.r))
        s.fill(col("white"), (x - 1, y - 1, 1, 1))
    elif k == "feather":
        a = math.atan2(sh.vy, sh.vx)
        dx, dy = math.cos(a) * 4, math.sin(a) * 4
        pygame.draw.line(s, col("black"), (int(x - dx), int(y - dy)), (int(x + dx), int(y + dy)), 3)
        pygame.draw.line(s, col("darkgray"), (int(x - dx), int(y - dy)), (int(x + dx), int(y + dy)))
        s.fill(col("white"), (int(x + dx), int(y + dy), 1, 1))
    elif k == "spark":
        c = "red" if int(t * 16) % 2 else "hotpink"
        pygame.draw.circle(s, col(c), (x, y), 3)
        s.fill(col("white"), (x - 1, y - 1, 2, 2))
    elif k == "wave":
        for i in range(3):
            hh = 9 - i * 2
            s.fill(col(("white", "lavender", "purple")[i]), (x - 2 + i * (-2 if sh.vx > 0 else 2), FLOOR - hh, 3, hh))
    elif k == "beam":
        if sh.age < sh.warn:
            if int(sh.age * 16) % 2 == 0:
                for yy in range(HUD_H + 4, FLOOR, 6):
                    s.fill(col("red"), (x, yy, 1, 3))
        else:
            w = int(sh.r) * 2 + 4
            s.fill(col("red"), (x - w // 2, HUD_H, w, FLOOR - HUD_H))
            s.fill(col("white"), (x - 1, HUD_H, 3, FLOOR - HUD_H))
    elif k == "jet":
        if sh.age < sh.warn:
            if int(sh.age * 16) % 2 == 0:
                for xx in range(0, W, 8):
                    s.fill(col("sky"), (xx, y, 4, 1))
        else:
            s.fill(col("blue"), (0, y - 3, W, 7))
            s.fill(col("sky"), (0, y - 2, W, 5))
            for xx in range(int(t * 200) % 12, W, 12):
                s.fill(col("white"), (xx, y - 1, 5, 1))
    if sh.batted:
        s.fill(col("lavender"), (x - 1, y - 4, 2, 1))


def preview(s, t):
    """Carousel thumbnail (~112 x 74): Mikan climbing toward KAW on the top perch."""
    w, h = s.get_size()
    th = data.THEMES[0]
    for y in range(0, h, 2):
        s.fill(lerp_col("deep", "ink", y / h), (0, y, w, 2))
    pygame.draw.rect(s, col("sky"), (70, 8, 30, 22))
    pygame.draw.circle(s, col("yellow"), (90, 15), 4)
    s.fill(col("hotpink"), (0, h - 6, w, 6))
    ys = (h - 6, h - 26, h - 46)
    for i, y in enumerate(ys[1:]):
        x0 = 6 if i % 2 == 0 else 34
        for x in range(x0, x0 + 72):
            yy = y + (x - x0) * (1 if i % 2 == 0 else -1) // 24
            s.fill(col("black"), (x, yy, 1, 5))
            s.fill(col(th[4]), (x, yy + 1, 1, 3))
            s.fill(col(th[3]), (x, yy, 1, 2))
    for px, y0, y1 in ((60, h - 26, h - 6), (44, h - 46, h - 26)):
        for y in range(y0, y1):
            s.fill(col(th[6] if (y // 2) % 3 == 0 else th[5]), (px - 3, y, 6, 1))
    draw_cushion(s, 50, h - 46)
    phase = (t * 0.4) % 1.0
    mx = int(14 + phase * 60)
    s.blit(sprite("tt_mikan_walk", int(t * 8)), (mx - 8, h - 6 - 13))
    kx = int(80 + math.sin(t * 1.3) * 22)
    s.blit(sprite("tt_kaw_fly", int(t * 8) % 3, math.cos(t * 1.3) > 0), (kx - 8, 4))
    yx = 74 - (t * 30) % 64
    yy = h - 26 + int((yx - 6) / 24) - 5
    pygame.draw.circle(s, col("black"), (int(yx), yy), 5)
    pygame.draw.circle(s, col("pink"), (int(yx), yy), 4)
    s.fill(col("hotpink"), (int(yx) - 2, yy - 1, 4, 1))
    s.blit(sprite("tt_kitten", int(t * 2), remap=art.KITTEN_COLORS[1]), (88, h - 46 - 7))
    s.blit(sprite("tt_fish"), (20, h - 30))


def gif_bot(scene):
    """Autoplay for README clips / tests: path-finds up the tree, jumps or pounces at incoming hazards."""
    from mochi_arcade.games.tower_tabby_bot import make_bot
    return make_bot(scene)
