"""MEOW DECK - a deck-building card battler where every card is a cat (original game for MOCHI ARCADE).

TOFU the crew captain leads a crew of cats up 200 floors of mischief: dog gangs, crows, robot vacuums and
mouse crews. Every card is a cat with its own pixel portrait (meow_deck_art.py), a breed and a role. Fish are
the energy: draw 5, play cats, end turn, and the foes act on the plans they show. Chain cats of the same breed
or role for bonus power, fill FEVER (cats cost 1 less) and hope for a GOLDEN kitten (JACKPOT!).
Boss every 10th floor, the CAT CAFE (KITTY SLOTS + shop + nap + grooming) on every x5 floor, a new cat after every
fight and collar charms after bosses.

The battle rules live in meow_deck_rules.py, the data in meow_deck_data.py. The iOS port
(ios/MochiArcade/Games/MeowDeck*.swift) mirrors these files and reads the campaign from EXPORT.
"""
import math
import random

import pygame

from mochi_arcade import music, sprites
from mochi_arcade.arcade import STAGES, Upgrade, boss_bar, ease_out, rainbow
from mochi_arcade.games import meow_deck_data as D
from mochi_arcade.games.base import LIVES, GameScene
from mochi_arcade.games.meow_deck_art import BREED_LABEL, build_art, paint_cat
from mochi_arcade.games.meow_deck_rules import (BASE_HP, CHARM_PLAN, HERO, Battle, Card, bot_choice, reference_kit,
                                                 reward_card)
from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

HOWTO = [
    "LEFT/RIGHT  PICK A CAT CARD",
    "UP/DOWN     PICK A TARGET FOE",
    "Z / SPACE   PLAY IT (COSTS FISH)",
    "X / CTRL    END YOUR TURN",
    "C / SHIFT   VIEW YOUR CREW",
    "",
    "CHAIN CATS OF THE SAME BREED OR ROLE",
    "FOR BONUS POWER. FOES SHOW THEIR PLANS!",
    "BOSS EVERY 10TH FLOOR, CAT CAFE ON X5.",
    "ENTER / ESC  PAUSE",
]
OPTIONS = [("difficulty", "DIFFICULTY", [("easy", "EASY"), ("normal", "NORMAL"), ("hard", "HARD")], "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["left", "right", "up", "down", "a", "a", "b", "x"]

DIFF_POW = {"easy": 0.85, "normal": 1.0, "hard": 1.15}
LIFE_AT = [25000, 70000, 150000, 300000]      # then every 200000
HUD_H = 12
GROUND = 98
PANEL_Y = 112
BIG_W, BIG_H = 104, 88
MINI_W, MINI_H = 30, 40
HAND_X0, HAND_X1 = 110, 318
FOE_X = {1: [236], 2: [196, 268], 3: [156, 214, 274]}
BOSS_X = [146, 190, 256]
SLOT_STRIP = ["rio", "sue", "niko", "goldie", "pearl", "rio", "sue", "niko", "pearl", "fleas"]

# ----------------------------------------------------------------------------- art + music registration
ART = build_art(D.CATS)
ART["md_barista"] = [paint_cat({"breed": "longhair", "eyes": "y", "face": "happy", "acc": "chef"}),
                     paint_cat({"breed": "longhair", "eyes": "y", "face": "happy", "acc": "chef"}, True)]
sprites.ART.update(ART)

music.SONGS.update({
    # "Whisker Waltz Swing" - MEOW DECK battles, floors 1-100 (D minor, swing)
    "md_duel": {"bpm": 126, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "D5:8 F5:8 A5:8 F5:8 G5:4 E5:4  F5:8 A5:8 C6:8 A5:8 A#5:4 A5:8 G5:8 "
            "A5:8 F5:8 D5:8 F5:8 E5:4 C5:4  D5:8 E5:8 F5:8 G5:8 A5:2 "
            "A#5:8 A5:8 G5:8 F5:8 G5:4 A5:4  F5:8 E5:8 D5:8 C5:8 D5:4 F5:4 "
            "G5:8 A5:8 A#5:8 C6:8 D6:4 C6:8 A5:8  A#5:8 A5:8 G5:8 E5:8 D5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.65, "notes":
            "D3:4 A2:4 D3:4 A2:4  F2:4 C3:4 F2:4 C3:4  A#2:4 F3:4 A#2:4 F3:4  A2:4 E3:4 A2:4 C#3:4 "
            "G2:4 D3:4 G2:4 D3:4  D3:4 A2:4 D3:4 A2:4  C3:4 G3:4 C3:4 G3:4  A2:4 E3:4 A2:4 E3:4"},
        {"wave": "drums", "vol": 1, "notes": " ".join(["K:8 H:8 S:8 H:8 K:8 K:8 S:8 H:8"] * 8)},
    ]},
    # "Moonlight Prowl" - MEOW DECK battles, floors 101-200 (E minor, quicker)
    "md_night": {"bpm": 138, "channels": [
        {"wave": "square", "duty": 0.125, "vol": 0.24, "notes":
            "E5:8 G5:8 B5:8 G5:8 A5:8 G5:8 E5:4  C5:8 E5:8 G5:8 E5:8 F#5:4 D5:4 "
            "E5:8 B4:8 E5:8 G5:8 B5:4 A5:8 G5:8  F#5:8 G5:8 A5:8 B5:8 D6:4 B5:4 "
            "C6:8 B5:8 A5:8 G5:8 A5:4 E5:4  B5:8 A5:8 G5:8 F#5:8 G5:4 B4:4 "
            "C5:8 E5:8 G5:8 C6:8 B5:4 A5:4  G5:8 F#5:8 D5:8 F#5:8 E5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes":
            "E2:8 E3:8 E2:8 E3:8 E2:8 E3:8 E2:8 E3:8  C3:8 C2:8 C3:8 C2:8 D3:8 D2:8 D3:8 D2:8 "
            "E2:8 E3:8 E2:8 E3:8 E2:8 E3:8 E2:8 E3:8  B2:8 B1:8 B2:8 B1:8 B2:8 B1:8 B2:8 B1:8 "
            "A2:8 A1:8 A2:8 A1:8 A2:8 A1:8 A2:8 A1:8  G2:8 G1:8 G2:8 G1:8 G2:8 G1:8 G2:8 G1:8 "
            "C3:8 C2:8 C3:8 C2:8 D3:8 D2:8 D3:8 D2:8  B2:8 B1:8 B2:8 B1:8 E2:8 E3:8 E2:8 E3:8"},
        {"wave": "drums", "vol": 1, "notes": " ".join(["K:8 H:8 S:8 H:8 K:8 H:8 S:8 S:8"] * 8)},
    ]},
})

EXPORT = {
    "cats": [{k: c[k] for k in ("id", "name", "breed", "role", "rar", "cost", "fx", "up", "upcost", "text",
                                 "uptext", "spr")} for c in D.CATS],
    "foes": D.FOES, "bosses": D.BOSSES, "stages": D.CAMPAIGN, "themes": [list(t) for t in D.THEMES],
    "charms": [list(c) for c in D.CHARMS], "mods": D.MODS, "starter": D.STARTER, "pool": D.POOL,
    "breeds": BREED_LABEL, "roles": {k: list(v) for k, v in D.ROLE_INFO.items()},
    "glossary": D.GLOSSARY, "plan": CHARM_PLAN, "rarity": [list(r) for r in D.RARITY], "price": D.PRICE,
    "lines": D.TOFU_LINES, "targeted": list(D.TARGETED), "roleorder": D.ROLES + ["gold", "junk"],
}

CHARMS = [Upgrade(cid, name, desc, color, icon, mx) for cid, name, desc, color, icon, mx in D.CHARMS]

INTENT_TEXT = {"atk": "ATTACK", "blk": "BLOCK", "atkblk": "ATTACK + BLOCK", "buff": "POWER UP", "rally": "RALLY THE GANG",
               "scare": "STARTLE YOU", "soak": "SOAK YOU", "fleas": "THROW FLEAS", "heal": "HEAL A PAL",
               "summon": "CALL FOR HELP", "steal": "STEAL A FISH", "charge": "CHARGING UP!", "nap": "NAPPING",
               "shield": "SHIELD THE GANG"}
INTENT_ICON = {"atk": "md_i_claw", "blk": "md_i_shield", "atkblk": "md_i_claw", "buff": "md_i_up", "rally": "md_i_up",
               "scare": "md_i_down", "soak": "md_i_drop", "fleas": "md_i_flea", "heal": "md_i_plus",
               "summon": "md_i_plus", "steal": "md_i_fishoff", "charge": "md_i_boom", "nap": "md_i_zzz",
               "shield": "md_i_shield"}


# ----------------------------------------------------------------------------- card drawing
def chip(card, battle=None):
    """(icon sprite, text) for the bottom strip of a card in hand."""
    pv = battle.preview(card) if battle else None
    fx = [f for f in card.fx if f[0] not in ("once", "wild", "gold")]
    if not fx:
        return "md_i_up", "WILD"
    op, n = fx[0][0], fx[0][1]
    hits = fx[0][2] if len(fx[0]) > 2 else 1
    if card.gold and op in ("all", "dmg", "block", "heal"):
        n *= 2
    if pv:
        kind, v, h = pv
        icon = {"dmg": "md_i_claw", "block": "md_i_shield", "heal": "md_i_heart"}[kind]
        if op == "all":
            icon = "md_i_boom"
        return icon, f"{v}" + (f"X{h}" if h > 1 else "")
    hx = f"X{hits}" if hits > 1 else ""
    table = {"dmg": ("md_i_claw", f"{n}{hx}"), "all": ("md_i_boom", f"{n}"), "rnd": ("md_i_claw", f"{n}{hx}"),
             "slam": ("md_i_claw", "BLK"), "block": ("md_i_shield", f"{n}"), "heal": ("md_i_heart", f"{n}"),
             "draw": ("md_i_quest", f"+{n}"), "fish": ("md_i_fish", f"+{n}"), "zoom": ("md_i_up", f"+{n}"),
             "fluff": ("md_i_shield", f"+{n}"), "purr": ("md_i_heart", f"+{n}"), "spiky": ("md_i_spiky", f"{n}"),
             "scare": ("md_i_down", f"{n}"), "scareall": ("md_i_down", f"{n}"), "daze": ("md_i_down", f"{n}"),
             "dazeall": ("md_i_down", f"{n}"), "itchy": ("md_i_flea", f"{n}"), "itchyall": ("md_i_flea", f"{n}"),
             "sleep": ("md_i_zzz", ""), "echo": ("md_i_up", "X2"), "fever": ("md_i_up", f"{n}%"),
             "scratch": ("md_i_flea", "!"), "cleanse": ("md_i_plus", "")}
    return table.get(op, ("md_i_quest", ""))


def card_frame_color(card, t):
    if card.gold or card.d["rar"] == 4:
        return rainbow(0, t * 0.5)
    return D.RARITY[card.d["rar"]][1] if card.d["rar"] > 0 else "lavender"


def draw_mini(s, card, x, y, t, battle=None, dim=False, sel=False, cost=None):
    """A 30x40 cat card in the hand."""
    d = card.d
    role_c = D.ROLE_INFO[d["role"]][1]
    frame = card_frame_color(card, t)
    pygame.draw.rect(s, col("black"), (x + 1, y + 1, MINI_W, MINI_H), border_radius=3)
    pygame.draw.rect(s, col("ink"), (x, y, MINI_W, MINI_H), border_radius=3)
    s.fill(col(role_c), (x + 2, y + 2, MINI_W - 4, 6))
    s.fill(col("night"), (x + 2, y + 8, MINI_W - 4, 24))
    s.blit(sprite(d["spr"], 1 if (int(t * 0.7 + card.uid * 0.37) % 9 == 0) else 0), (x + 3, y + 8))
    pygame.draw.rect(s, col(frame), (x, y, MINI_W, MINI_H), 1, border_radius=3)
    if d["rar"] >= 2 or card.gold:
        pygame.draw.rect(s, col(frame), (x + 1, y + 1, MINI_W - 2, MINI_H - 2), 1, border_radius=3)
    c = card.base_cost if cost is None else cost
    pygame.draw.rect(s, col("black"), (x + 1, y + 1, 9, 9), border_radius=2)
    draw_text(s, str(c), x + 3, y + 2, "lime" if c < card.base_cost else "sky", shadow=None)
    if card.up:
        draw_text(s, "+", x + MINI_W - 7, y + 1, "lime", shadow="black")
    icon, txt = chip(card, battle)
    s.fill(col("black"), (x + 2, y + 32, MINI_W - 4, 7))
    s.blit(sprite(icon), (x + 3, y + 32))
    draw_text(s, txt, x + 11, y + 32, "white", shadow=None)
    if card.gold:
        for i in range(3):
            a = t * 3 + i * 2.1
            s.fill(col("white"), (x + 15 + int(math.cos(a) * 13), y + 20 + int(math.sin(a) * 17), 1, 1))
    if dim:
        ov = pygame.Surface((MINI_W, MINI_H), pygame.SRCALPHA)
        ov.fill((12, 8, 24, 130))
        s.blit(ov, (x, y))
    if sel:
        pygame.draw.rect(s, col("white" if int(t * 6) % 2 else "yellow"), (x - 1, y - 1, MINI_W + 2, MINI_H + 2), 1,
                         border_radius=4)


def draw_big(s, card, x, y, t, battle=None, cost=None, upgraded=False, note=None):
    """The enlarged 104x88 card: 2x portrait, cost, role, breed, rarity, name and text."""
    d = card.d
    up = card.up or upgraded
    role_label, role_c, _ = D.ROLE_INFO[d["role"]]
    rar_label, rar_c = D.RARITY[d["rar"]]
    frame = card_frame_color(card, t)
    panel(s, (x, y, BIG_W, BIG_H), fill="ink", border=frame, radius=4)
    if d["rar"] >= 2 or card.gold:
        pygame.draw.rect(s, col(frame), (x + 1, y + 1, BIG_W - 2, BIG_H - 2), 1, border_radius=4)
    pygame.draw.rect(s, col(role_c), (x + 3, y + 3, 50, 50))
    s.fill(col("night"), (x + 4, y + 4, 48, 48))
    s.blit(sprite(d["spr"], 1 if (int(t * 0.8 + card.uid) % 7 == 0) else 0, scale=2), (x + 4, y + 4))
    # right column: cost, role, breed, rarity
    c = card.base_cost if cost is None else cost
    if up and cost is None:
        c = d["upcost"]
    s.blit(sprite("md_i_fish"), (x + 56, y + 6))
    draw_text(s, str(c), x + 66, y + 4, "sky" if cost is None or cost >= card.base_cost else "lime", 2,
              outline="black", shadow=None)
    draw_text(s, role_label, x + 56, y + 22, role_c, shadow="black")
    draw_text(s, BREED_LABEL.get(d["breed"], ""), x + 56, y + 32, "white", shadow="black")
    draw_text(s, rar_label if not card.gold else "GOLDEN", x + 56, y + 42, rar_c if not card.gold else rainbow(0, t),
              shadow="black")
    name = d["name"] + ("+" if up else "")
    draw_text(s, name, x + BIG_W // 2, y + 56, "yellow" if not up else "lime", align="center", shadow="black")
    lines = d["uptext"] if up else d["text"]
    for i, ln in enumerate(lines[:3]):
        draw_text(s, ln, x + BIG_W // 2, y + 65 + i * 8, "white" if not upgraded else "lime", align="center",
                  shadow=None)
    if card.gold:
        draw_text(s, "X2!", x + 32, y + 42, rainbow(1, t), outline="black", shadow=None)
    if note:
        draw_text(s, note, x + 28, y + 6, "lime" if int(t * 6) % 2 else "yellow", align="center", outline="black",
                  shadow=None)


def blit_rows(s, sp, x, y, y0, y1):
    """Blit only the sprite rows that fall inside y0 <= y < y1 (a vertical clip)."""
    top = max(0, y0 - y)
    bot = min(sp.get_height(), y1 - y)
    if bot > top:
        s.blit(sp, (x, y + top), pygame.Rect(0, top, sp.get_width(), bot - top))


def draw_tofu(s, x, ground, t, pose="idle", flash=False):
    if pose == "idle":
        fr = 2 if int(t * 1.3) % 6 == 0 and (t * 1.3) % 1 < 0.2 else int(t * 2) % 2
        sp = sprite("md_tofu", fr)
    else:
        sp = sprite("md_tofu_act", {"attack": 0, "hurt": 1, "happy": 2, "ko": 3}[pose])
    if flash:
        sp = sprite("md_tofu_act", 1, remap={"w": "r", "c": "P"})
    s.blit(sp, (x - 16, ground - 32))


def make_bg(theme, t=0):
    name, sky, sky2, ground, ground2, deco = theme
    s = pygame.Surface((W, PANEL_Y - HUD_H))
    s.fill(col(sky))
    gy = GROUND - HUD_H - 6
    for i, y in enumerate((0, 8, 18)):
        s.fill(col(sky2), (0, y, W, 4 - i))
    if deco == 0:      # fence
        for x in range(0, W, 12):
            pygame.draw.rect(s, col(sky2), (x + 1, gy - 30, 10, 30))
            s.fill(col(ground2), (x + 1, gy - 30, 10, 1))
        s.fill(col(ground2), (0, gy - 22, W, 2))
        s.fill(col(ground2), (0, gy - 10, W, 2))
    elif deco == 1:    # windows
        for x in range(14, W, 64):
            pygame.draw.rect(s, col(sky2), (x, 14, 36, 34))
            for wx, wy in ((x + 3, 17), (x + 19, 17), (x + 3, 33), (x + 19, 33)):
                s.fill(col("yellow" if (wx // 7 + wy) % 3 else "cream"), (wx, wy, 14, 12))
    elif deco == 2:    # bushes and trees
        for x in range(10, W, 46):
            s.fill(col(ground2), (x + 8, gy - 26, 4, 26))
            pygame.draw.circle(s, col(sky2), (x + 10, gy - 30), 14)
            pygame.draw.circle(s, col(ground2), (x + 4, gy - 4), 8)
            pygame.draw.circle(s, col(ground2), (x + 18, gy - 3), 7)
    elif deco == 3:    # shelves with jars
        for y in (24, 52):
            s.fill(col(sky2), (0, y, W, 3))
            for x in range(8, W, 26):
                h = 8 + (x * 7 + y) % 9
                pygame.draw.rect(s, col(ground2 if (x // 26) % 2 else sky2), (x, y - h, 12, h), border_radius=2)
                s.fill(col("white"), (x + 2, y - h + 2, 2, h - 4))
    elif deco == 4:    # roofs and a moon
        pygame.draw.circle(s, col("cream"), (40, 26), 10)
        pygame.draw.circle(s, col(sky), (45, 23), 9)
        for x in range(-20, W, 70):
            pygame.draw.polygon(s, col(sky2), [(x, gy - 12), (x + 35, gy - 44), (x + 70, gy - 12)])
            s.fill(col(sky2), (x + 46, gy - 50, 8, 20))
            s.fill(col("yellow"), (x + 30, gy - 26, 8, 8))
    else:              # stars and a bridge
        for i in range(40):
            s.fill(col("white" if i % 3 else "yellow"), ((i * 73) % W, (i * 37) % (gy - 20), 1, 1))
        for x in range(0, W, 80):
            pygame.draw.circle(s, col(sky2), (x + 40, gy + 30), 44, 4)
    s.fill(col(ground), (0, gy, W, PANEL_Y - HUD_H - gy))
    for x in range(0, W, 16):
        s.fill(col(ground2), (x + (8 if (x // 16) % 2 else 0), gy + 4, 8, 2))
    s.fill(col("black"), (0, gy, W, 1))
    return s


# ----------------------------------------------------------------------------- the game
class MeowDeck(GameScene):
    @property
    def music(self):
        return self.song()

    def __init__(self, app, info, opt):
        super().__init__(app, info, opt)
        self.diff = opt.get("difficulty", "normal")
        self.lives = LIVES.get(self.diff, 3)
        self.hype.FEVER_TIME = 999.0      # FEVER lasts turns, not seconds (ended by end_turn)
        self.hype.COMBO_TIME = 999.0      # the chain is per turn
        self.hype.combo_y = -20           # we draw our own CHAIN counter
        self.rng = random.Random()
        self.charms = {}
        self.treats = 0
        self.life_i = 0
        self.fever_turns = 0
        self.state = "intro"
        self.state_t = 0.0
        self.battle = None
        self.view = None                  # deck viewer: {"mode", "i", "cards", "title", "back"}
        self.offers, self.prices = [], None
        self.pick_i = 0
        self.pick_mode = "reward"
        self.cafe_i = 0
        self.cafe_used = set()
        self.slots = None
        self.tally = []
        self.after = []                   # queued reward steps after a fight
        self.flying = None
        self.cameo = None
        self.foe_queue = []
        self.foe_t = 0.0
        self.fxs = {}
        self.hero_pose, self.hero_pose_t = "idle", 0.0
        self.hero_flash = 0.0
        self.deal_t = {}
        self.sel = 0
        self.tgt = 0
        self.msg = ""
        self.msg_t = 0.0
        self.tap_flag = self.tap_ok = False
        start = max(1, min(STAGES, int(opt.get("stage", opt.get("start", 1)))))
        tier = (start - 1) // 10
        if tier > 0:     # a checkpoint start brings a crew fit for the floor
            self.deck, self.charms, self.maxhp = reference_kit(tier, self.rng)
            self.treats = 30 * tier
        else:
            self.deck = [Card(c) for c in D.STARTER]
            self.maxhp = BASE_HP
        self.lives += self.charms.get("lives", 0)
        self.hp = self.maxhp
        self.start_floor(start)

    # ---------------------------------------------------------------- helpers
    def song(self):
        k = self.st["kind"] if hasattr(self, "st") else "normal"
        if k == "boss":
            return "boss"
        if k == "bonus":
            return "bonus"
        return "md_duel" if self.n <= 100 else "md_night"

    def tier(self):
        return self.st["tier"]

    def lv(self, cid):
        return self.charms.get(cid, 0)

    def say(self, text, dur=1.4):
        self.msg, self.msg_t = text, dur

    def set_state(self, s):
        self.state = s
        self.state_t = 0.0

    def check_life(self):
        need = LIFE_AT[self.life_i] if self.life_i < len(LIFE_AT) else LIFE_AT[-1] + 200000 * (self.life_i - len(LIFE_AT) + 1)
        if self.score >= need:
            self.life_i += 1
            self.lives += 1
            self.hype.banner("EXTRA LIFE!", "TOFU FEELS LUCKY", color="pink", dur=1.4, scale=1, sound="extra")
            self.hype.shower(20, "hearts")

    def score_at(self, pts, x=None, y=None, color="yellow"):
        got = self.add(pts, x, y, color)
        self.check_life()
        return got

    # ---------------------------------------------------------------- floors
    def start_floor(self, n):
        self.n = n
        self.st = D.CAMPAIGN[n - 1]
        self.theme = D.THEMES[self.st["theme"]]
        self.bg = make_bg(self.theme)
        self.reached(n)
        self.battle = None
        self.view = None
        self.slots = None
        self.tally = []
        self.after = []
        self.fxs = {}
        self.flying = None
        self.cameo = None
        self.hero_pose = "idle"
        self.end_fever(quiet=True)
        self.hype.break_combo()
        self.set_state("intro")
        self.intro_len = 3.0 if self.st["kind"] == "boss" else 2.4
        self.app.audio.music(self.song())
        self.app.audio.play("warning" if self.st["kind"] == "boss" else "stage")
        if self.st["kind"] == "boss":
            self.hype.flash("red", 0.3)
        if self.st["kind"] != "bonus":
            self.begin_fight()

    def begin_fight(self):
        for c in self.deck:
            c.gold = False
        pw = DIFF_POW.get(self.diff, 1.0)
        self.battle = Battle(self.st, self.deck, self.hp, self.maxhp, self.charms, self.rng, pw)
        self.fxs = {}
        self.sel = 0
        self.tgt = 0

    def go_fight(self):
        """Intro is over: deal the first hand."""
        if self.battle is None:
            self.begin_fight()
        ev = self.battle.start()
        self.on_events(ev)
        self.retarget()
        self.set_state("player")

    def retry_floor(self):
        self.hp = self.maxhp
        self.start_floor(self.n)

    # ---------------------------------------------------------------- update
    def a_hit(self):
        """Z pressed - or the screen tapped (touch) - to continue."""
        return self.app.input.hit("a") or self.tap_ok

    def tick(self, dt):
        self.tap_ok, self.tap_flag = self.tap_flag, False
        self.state_t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        self.hero_pose_t = max(0.0, self.hero_pose_t - dt)
        if self.hero_pose_t <= 0 and self.hero_pose not in ("ko",):
            self.hero_pose = "idle"
        self.hero_flash = max(0.0, self.hero_flash - dt)
        if self.cameo is not None:
            self.cameo["t"] += dt
            if self.cameo["t"] > 0.9:
                self.cameo = None
        for v in self.fxs.values():
            for k in ("flash", "shake", "lunge", "dead"):
                if v.get(k, 0) > 0:
                    v[k] = max(0.0, v[k] - dt)
        for uid in list(self.deal_t):
            self.deal_t[uid] += dt
            if self.deal_t[uid] > 1.0:
                del self.deal_t[uid]
        inp = self.app.input
        if self.view is not None:
            self.update_view(dt)
            return
        s = self.state
        if s == "intro":
            if self.state_t > self.intro_len or (self.state_t > 0.5 and self.a_hit()):
                if self.st["kind"] == "bonus":
                    self.open_slots()
                else:
                    self.go_fight()
        elif s == "player":
            self.update_player(dt)
        elif s == "anim":
            self.update_fly(dt)
        elif s == "foes":
            self.update_foes(dt)
        elif s == "win":
            if self.state_t > 1.6:
                self.begin_tally()
        elif s == "tally":
            self.update_tally(dt)
        elif s == "reward":
            self.update_picker(dt)
        elif s == "next":
            if self.after or self.state_t > 0.7:      # let the "NEW CREW!" banner breathe before the next floor
                self.next_step()
        elif s == "slots":
            self.update_slots(dt)
        elif s == "cafe":
            self.update_cafe(dt)
        elif s == "ko":
            if self.state_t > 2.4 or (self.state_t > 1.0 and self.a_hit()):
                if self.lives > 0:
                    self.retry_floor()
                else:
                    self.set_state("over")
                    self.end_game(False, f"FLOOR {self.n}", delay=0.5)

    # ---------------------------------------------------------------- player turn
    def retarget(self, step=0):
        b = self.battle
        al = [k for k, f in enumerate(b.foes) if f.alive]
        if not al:
            return
        if self.tgt not in al:
            self.tgt = min(al, key=lambda k: abs(k - self.tgt))
        if step:
            order = sorted(al, key=lambda k: self.foe_x(k))
            i = order.index(self.tgt)
            self.tgt = order[(i + step) % len(order)]

    def update_player(self, dt):
        b = self.battle
        inp = self.app.input
        b.fever = self.hype.fever_on
        n = len(b.hand)
        if n:
            self.sel = max(0, min(self.sel, n - 1))
            if inp.repeat("left", dt=dt):
                self.sel = (self.sel - 1) % n
                self.app.audio.play("move")
            if inp.repeat("right", dt=dt):
                self.sel = (self.sel + 1) % n
                self.app.audio.play("move")
        if inp.hit("up"):
            self.retarget(-1)
            self.app.audio.play("move")
        if inp.hit("down"):
            self.retarget(1)
            self.app.audio.play("move")
        if inp.hit("x"):
            self.open_view("look")
            return
        if inp.hit("a") and n:
            self.try_play(self.sel, self.tgt)
        elif inp.hit("b"):
            self.end_turn()

    def try_play(self, i, tgt):
        b = self.battle
        if not b.can_play(i):
            self.app.audio.play("back")
            self.say("NOT ENOUGH FISH!")
            self.floats.add(self.hand_pos(i)[0] + MINI_W // 2, PANEL_Y + 4, "NEED FISH", "red")
            return
        card = b.hand[i]
        x0, y0 = self.hand_pos(i)
        if card.targeted:
            tx, ty = self.foe_x(tgt), GROUND - 20
        else:
            tx, ty = 38, GROUND - 20
        self.flying = {"card": card, "i": i, "tgt": tgt, "x0": x0, "y0": y0, "x1": tx - MINI_W // 2,
                       "y1": ty - MINI_H // 2, "t": 0.0}
        self.app.audio.play("card")
        if card.d["role"] == "swipe" or card.targeted:
            self.hero_pose, self.hero_pose_t = "attack", 0.4
        self.set_state("anim")

    def update_fly(self, dt):
        f = self.flying
        f["t"] += dt
        if f["t"] < 0.2:
            return
        b = self.battle
        idx = b.hand.index(f["card"]) if f["card"] in b.hand else f["i"]

        ev = b.play(idx, f["tgt"])
        self.flying = None
        self.cameo = {"card": f["card"], "t": 0.0}
        self.after_play(ev)
        if b.won:
            self.fight_won()
        else:
            self.retarget()
            self.sel = min(self.sel, max(0, len(b.hand) - 1))
            self.set_state("player")

    def after_play(self, ev):
        b = self.battle
        link = ev[0][2] if ev and ev[0][0] == "play" else 0
        if link > 0:
            self.hype.hit(1, fever=0.0)
            self.hype.fever_add((0.05 + 0.05 * link) * (1 + 0.25 * self.lv("catnip")))
            self.score_at(50 * b.chain)
            label = "PURRFECT CHAIN!" if link >= 2 else f"CHAIN X{b.chain}!"
            self.floats.add(60, PANEL_Y - 18, label, "lime" if link >= 2 else "peach")
            if link >= 2:
                self.app.audio.play("combo")
            if b.chain in (4, 6, 8):
                self.hype.banner(f"CHAIN X{b.chain}!", "THE CREW IS IN SYNC", color="lime", dur=1.0, scale=1,
                                 sound="combo")
        else:
            self.hype.break_combo()
            self.hype.hit(1, fever=0.0)
            self.hype.fever_add(0.03 * (1 + 0.25 * self.lv("catnip")))
        self.on_events(ev)

    def end_turn(self):
        b = self.battle
        ev = b.end_turn()
        self.on_events(ev)
        self.hype.break_combo()
        if self.fever_turns > 0:
            self.fever_turns -= 1
            if self.fever_turns == 0:
                self.end_fever()
        self.app.audio.play("select")
        if b.lost:
            self.hero_ko()
            return
        self.foe_queue = [k for k, f in enumerate(b.foes) if f.alive]
        self.foe_t = 0.0
        self.set_state("foes")

    def update_foes(self, dt):
        b = self.battle
        self.foe_t += dt
        if self.foe_t < 0.35:
            return
        if not self.foe_queue:
            ev = []
            b.begin_turn(ev)
            self.on_events(ev)
            self.retarget()
            self.sel = 0
            self.set_state("player")
            return
        k = self.foe_queue.pop(0)
        self.foe_t = 0.0
        if k >= len(b.foes) or not b.foes[k].alive:
            self.foe_t = 0.3
            return
        self.fx(k)["lunge"] = 0.3
        ev = b.foe_act(k)
        self.on_events(ev)
        if b.lost:
            self.hero_ko()
        elif b.won:
            self.fight_won()

    def fx(self, k):
        v = self.fxs.get(k)
        if v is None:
            v = self.fxs[k] = {"flash": 0.0, "shake": 0.0, "lunge": 0.0, "dead": 0.0}
        return v

    # ---------------------------------------------------------------- events -> juice
    def on_events(self, ev):
        b = self.battle
        tier = self.tier()
        for kind, who, n, s in ev:
            if who == HERO:
                x, y = 38, GROUND - 40
            else:
                x, y = self.foe_x(who), GROUND - self.foe_h(who) - 6
            if kind == "hit":
                v = self.fx(who)
                v["flash"], v["shake"] = 0.15, 0.25
                if n > 0:
                    self.floats.add(x, y + 10, str(n), "white" if s != "ITCHY" else "lime")
                    self.parts.burst(x, GROUND - 14, 8, ("white", "yellow", "orange"), 50, 0.4)
                    self.score_at(10 * n)
                    self.app.audio.play("pop" if n < 12 else "explode")
                    self.hype.fever_add(0.004 * n * (1 + 0.25 * self.lv("catnip")))
                    if n >= 25:
                        self.app.shake(3, 0.2)
                        self.hype.hitstop(0.06)
                elif s not in ("0", ""):
                    self.floats.add(x, y + 10, "BLOCKED", "sky")
                    self.app.audio.play("tin")
            elif kind == "die":
                fo = b.foes[who]
                self.fx(who)["dead"] = 0.6
                self.parts.burst(x, GROUND - 14, 24, ("white", "pink", "yellow", "lavender"), 80, 0.7)
                self.app.audio.play("bossdown" if fo.boss else "explode")
                if fo.boss:
                    self.boss_defeated(fo)
                else:
                    self.score_at(150 * (tier + 1) * (2 if fo.elite else 1), x, y - 6, "lime")
                    self.hype.fever_add(0.08 * (1 + 0.25 * self.lv("catnip")))
                    self.app.shake(2, 0.15)
            elif kind == "hurt":
                if n > 0:
                    self.hero_pose, self.hero_pose_t = "hurt", 0.35
                    self.hero_flash = 0.15
                    self.floats.add(38, GROUND - 46, f"-{n}", "red")
                    self.app.audio.play("hurt")
                    self.app.shake(2 + min(4, n // 8), 0.2)
                    self.parts.burst(38, GROUND - 16, 10, ("red", "pink", "white"), 50, 0.4)
                elif s not in ("0", ""):
                    self.floats.add(38, GROUND - 46, "BLOCKED!", "sky")
                    self.app.audio.play("tin")
            elif kind == "block":
                self.floats.add(20, GROUND - 30, f"+{n}", "sky")
                self.app.audio.play("hold")
                self.score_at(5 * n)
            elif kind == "heal":
                if n > 0:
                    self.floats.add(38, GROUND - 46, f"+{n}", "lime")
                    self.parts.burst(38, GROUND - 20, 8, ("pink", "hotpink", "white"), 40, 0.5)
                    self.app.audio.play("fruit")
                    self.score_at(5 * n)
            elif kind == "buff":
                self.floats.add(38, GROUND - 52, f"+{n} {s}", "orange")
                self.app.audio.play("powerup")
            elif kind == "fish":
                self.floats.add(HAND_X0 + 20, PANEL_Y + 2, f"+{n} FISH", "sky")
                self.app.audio.play("coin")
            elif kind == "debuff":
                self.floats.add(x, y - 4, s, "lavender")
                self.app.audio.play("trap")
            elif kind == "fever":
                self.hype.fever_add(n / 100)
                self.floats.add(38, GROUND - 52, f"FEVER +{n}%", "yellow")
            elif kind == "text":
                self.floats.add(x, y - 4, s, "peach")
            elif kind == "golden":
                self.hype.banner("GOLDEN KITTEN!", "IT COSTS 0 AND HITS X2!", rainbow=True, dur=1.4, scale=1,
                                 sound="bonus")
                self.hype.shower(16, "stars")
            elif kind == "jackpot":
                self.hype.jackpot(3000 * (tier + 1), f"{s}!")
                self.treats += 25
                self.check_life()
            elif kind == "phase":
                self.hype.banner(f"PHASE {n}!", f"{s} GETS SERIOUS", color="red", dur=1.6, sound="warning")
                self.hype.flash("red", 0.3)
                self.app.shake(5, 0.4)
            elif kind == "summon":
                self.floats.add(x, y - 4, "HELP ARRIVES!", "orange")
                self.fx(who)["flash"] = 0.3
                self.fx(who)["dead"] = 0.0
                self.app.audio.play("warning")
            elif kind == "junk":
                self.floats.add(HAND_X0 + 60, PANEL_Y + 2, f"+{n} FLEAS IN DECK", "brown")
                self.app.audio.play("trap")
            elif kind == "fblock":
                self.floats.add(x, y, f"+{n}", "sky")
            elif kind == "fheal":
                self.floats.add(x, y, f"+{n}", "lime")
                self.app.audio.play("fruit")
            elif kind == "fbuff":
                self.floats.add(x, y - 4, s, "orange")
            elif kind == "draw":
                for k, c in enumerate(b.hand[-n:]):
                    self.deal_t[c.uid] = -0.05 * k
                self.app.audio.play("move")
            elif kind == "turn":
                if n > 1:
                    self.floats.add(W // 2, PANEL_Y - 18, f"TURN {n}", "white")
        if self.hype.fever_on and self.fever_turns == 0:
            self.fever_turns = 2          # FEVER: the rest of this turn and the next one
            self.say("FEVER! CATS COST 1 LESS")

    def end_fever(self, quiet=False):
        if self.hype.fever_on:
            self.hype.fever_t = 0.0
            if not quiet:
                self.hype.banner("FEVER END", color="lavender", dur=0.9, scale=1)
        self.fever_turns = 0

    def hero_ko(self):
        self.hero_pose, self.hero_pose_t = "ko", 99.0
        self.lives -= 1
        self.hp = 0
        self.end_fever(quiet=True)
        self.app.audio.play("die")
        self.app.audio.music(None)
        self.hype.slowmo(0.4, 0.8)
        if self.lives > 0:
            self.hype.banner("TOFU FAINTED!", f"{self.lives} LIVES LEFT - TRY AGAIN", color="red", dur=2.2)
        else:
            self.hype.banner("GAME OVER", "TOFU NEEDS A LONG NAP", color="red", dur=2.4)
        self.set_state("ko")

    # ---------------------------------------------------------------- winning
    def fight_won(self):
        b = self.battle
        self.hp = b.hero.hp
        self.end_fever(quiet=True)
        self.hype.break_combo()
        self.hero_pose, self.hero_pose_t = "happy", 99.0
        self.app.audio.play("win")
        if self.st["kind"] != "boss":
            self.hype.banner("VICTORY!", D.TOFU_LINES[(self.n + b.turn) % len(D.TOFU_LINES)], color="mint", dur=1.5)
            self.hype.shower(30, "confetti")
        self.hype.slowmo(0.4, 0.6)
        self.set_state("win")

    def boss_defeated(self, fo):
        g = self.hype
        g.banner("BOSS DOWN!", fo.name, rainbow=True, dur=2.2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(40, "coins")
        g.slowmo(0.3, 1.2)
        self.app.shake(6, 0.6)
        self.score_at(10000 + 3000 * self.tier(), W // 2, 60)

    def begin_tally(self):
        b = self.battle
        t1 = self.tier() + 1
        rows = []
        if self.st["kind"] == "boss":
            rows.append(("BOSS BONUS", 5000 * t1))
        else:
            rows.append(("VICTORY", 500 * t1 * (2 if self.st["elite"] else 1)))
        rows.append((f"TURNS {b.turn}", max(0, 7 - b.turn) * 150 * t1))
        rows.append((f"BEST CHAIN X{b.best_chain}", b.best_chain * 120 * t1))
        rows.append(("NO SCRATCH", 1500 * t1 if b.dmg_taken == 0 else 0))
        mult = (1 + 0.5 * self.lv("jar")) * (2 if self.st["mod"] == "treats" else 1)
        self.treats_won = int((self.st["treats"] + int(self.rng.random() * 5)) * mult) + 2 * self.lv("bell")
        self.tally = [[label, v, 0.0] for label, v in rows]
        self.tally_i = 0
        self.tally_wait = 0.0
        self.treats += self.treats_won
        heal = 4 * self.lv("motor")
        if self.st["kind"] == "boss":
            self.hp = self.maxhp
        elif heal:
            self.hp = min(self.maxhp, self.hp + heal)
        if b.dmg_taken == 0:
            self.hype.banner("PURRFECT!", "NOT A SCRATCH", rainbow=True, dur=1.6, sound="fever")
            self.hype.shower(30, "stars")
        self.set_state("tally")

    def update_tally(self, dt):
        skip = self.state_t > 0.3 and self.a_hit()
        if self.tally_i < len(self.tally):
            if skip:
                for row in self.tally[self.tally_i:]:
                    row[2] = row[1]
                    if row[1] > 0:
                        self.score_at(row[1])
                self.tally_i = len(self.tally)
                self.app.audio.play("coin")
                return
            row = self.tally[self.tally_i]
            row[2] = min(row[1], row[2] + max(1.0, row[1] * dt / 0.35))
            if row[2] >= row[1]:
                if row[1] > 0:
                    self.score_at(row[1])
                    self.app.audio.play("coin")
                self.tally_i += 1
        else:
            self.tally_wait += dt
            if self.tally_wait > 1.4 or skip:
                self.finish_fight()

    def finish_fight(self):
        if self.n >= STAGES:
            self.set_state("over")
            self.hype.banner("ALL CLEAR!!", "THE CREW RULES THE TOWER", rainbow=True, dur=5.0, sound="jackpot")
            self.hype.shower(120, "confetti")
            self.end_game(True, "ALL 200 FLOORS!", delay=4.5)
            return
        kind = self.st["kind"]
        self.after = []
        if kind == "boss":
            self.after = ["charm", "groom", "reward"]
        else:
            self.after = ["reward"]
        self.set_state("next")

    def next_step(self):
        if not self.after:
            self.start_floor(self.n + 1)
            return
        step = self.after.pop(0)
        if step == "charm":
            self.set_state("charm")
            self.pick_upgrade(CHARMS, self.charms, self.on_charm, "COLLAR CHARM!")
        elif step == "groom":
            self.open_view("groom", back=False)
        elif step == "reward":
            self.open_reward()

    def on_charm(self, uid):
        if uid:
            self.charms[uid] = self.lv(uid) + 1
            u = next(c for c in CHARMS if c.id == uid)
            self.hype.banner(u.name, f"LEVEL {self.charms[uid]}", color=u.color, dur=1.2, scale=1)
            if uid == "nap":
                self.maxhp += 12
                self.hp = min(self.maxhp, self.hp + 12)
            elif uid == "lives":
                self.lives += 1
                self.app.audio.play("extra")
        self.set_state("next")

    # ---------------------------------------------------------------- reward / shop picker
    def make_offers(self, n, boss=False, shop=False):
        tier = self.tier()
        out = []
        ids = []
        for k in range(n):
            cid = reward_card(self.rng, tier + (3 if boss or (shop and k == 0) else 0), ids)
            if (boss or (shop and k == 0) or self.st.get("elite")) and D.CAT[cid]["rar"] == 0:
                cid = reward_card(self.rng, tier + 4, ids)
            ids.append(cid)
            c = Card(cid, self.rng.random() < min(0.5, 0.03 * tier))
            out.append(c)
        if self.hype.lucky(0.01 + 0.006 * self.lv("bell")):
            out[int(self.rng.random() * n)] = Card("goldie")
        return out

    def open_reward(self):
        boss = self.st["kind"] == "boss"
        self.offers = self.make_offers(3, boss=boss)
        self.prices = None
        self.pick_mode = "reward"
        self.pick_i = 0
        if any(c.cid == "goldie" for c in self.offers):
            self.hype.banner("LUCKY!", "A GOLDEN KITTEN WANTS TO JOIN!", rainbow=True, dur=1.8, sound="bonus")
        self.app.audio.play("levelup")
        self.set_state("reward")

    def update_picker(self, dt):
        inp = self.app.input
        n = len(self.offers)
        if inp.hit("left"):
            self.pick_i = (self.pick_i - 1) % (n + 1)
            self.app.audio.play("move")
        if inp.hit("right"):
            self.pick_i = (self.pick_i + 1) % (n + 1)
            self.app.audio.play("move")
        if inp.hit("down"):
            self.pick_i = n
            self.app.audio.play("move")
        if inp.hit("up") and self.pick_i == n:
            self.pick_i = 0
            self.app.audio.play("move")
        if inp.hit("x"):
            self.open_view("look")
            return
        if self.state_t > 0.4 and inp.hit("a"):
            self.take_offer(self.pick_i)
        elif self.state_t > 0.4 and inp.hit("b") and self.pick_mode == "shop":
            self.take_offer(n)

    def take_offer(self, i):
        n = len(self.offers)
        if i >= n:          # skip / leave
            if self.pick_mode == "reward":
                self.treats += 10
                self.floats.add(W // 2, 150, "+10 TREATS", "orange")
                self.app.audio.play("coin")
                self.set_state("next")
            else:
                self.set_state("cafe")
            return
        c = self.offers[i]
        if c is None:
            return
        if self.prices is not None:
            p = self.prices[i]
            if self.treats < p:
                self.app.audio.play("back")
                self.say("NOT ENOUGH TREATS!")
                return
            self.treats -= p
        self.deck.append(c)
        self.app.audio.play("card")
        self.hype.banner("NEW CREW!", c.name, color=D.RARITY[c.d["rar"]][1], dur=1.2, scale=1)
        self.hype.shower(12 + 8 * c.d["rar"], "stars")
        if c.cid == "goldie":
            self.hype.jackpot(5000 * (self.tier() + 1), "LUCKY GOLDIE JOINS!")
        if self.prices is None:
            self.set_state("next")
        else:
            self.offers[i] = None
            self.pick_i = n

    # ---------------------------------------------------------------- deck viewer
    def crew(self):
        order = {r: i for i, r in enumerate(D.ROLES + ["gold", "junk"])}
        return sorted(self.deck, key=lambda c: (order.get(c.d["role"], 9), c.d["name"], not c.up))

    def open_view(self, mode, back=True, paid=0):
        cards = self.crew()
        if mode == "groom":
            cards = [c for c in cards if not c.up and c.cid != "fleas"]
            if not cards:
                self.set_state("next" if not back else self.state)
                return
        if mode == "rehome":
            cards = [c for c in cards if c.cid != "goldie"]
        titles = {"look": f"YOUR CREW: {len(self.deck)} CATS", "groom": "GROOMING: PICK A CAT TO UPGRADE",
                  "rehome": "REHOME: WHICH CAT FINDS A NEW HOME?"}
        self.view = {"mode": mode, "i": 0, "cards": cards, "title": titles[mode], "back": back, "t": 0.0,
                     "paid": paid, "done": False}
        self.app.audio.play("select")

    def update_view(self, dt):
        v = self.view
        v["t"] += dt
        inp = self.app.input
        n = len(v["cards"])
        cols = 6
        if n:
            if inp.repeat("left", dt=dt):
                v["i"] = (v["i"] - 1) % n
                self.app.audio.play("move")
            if inp.repeat("right", dt=dt):
                v["i"] = (v["i"] + 1) % n
                self.app.audio.play("move")
            if inp.repeat("up", dt=dt) and v["i"] >= cols:
                v["i"] -= cols
                self.app.audio.play("move")
            if inp.repeat("down", dt=dt) and v["i"] + cols < n:
                v["i"] += cols
                self.app.audio.play("move")
        if v["mode"] == "look":
            if v["t"] > 0.2 and inp.hit("x", "b", "a"):
                self.close_view()
            return
        if v["t"] > 0.3 and inp.hit("a") and n:
            self.view_pick(v["i"])
        elif v["back"] and inp.hit("b", "x"):
            self.close_view()

    def view_pick(self, i):
        v = self.view
        c = v["cards"][i]
        if v["mode"] == "groom":
            c.up = True
            self.hype.banner("GROOMED!", c.name, color="lime", dur=1.2, scale=1, sound="powerup")
            self.hype.shower(16, "stars")
        else:
            self.deck.remove(c)
            self.hype.banner("REHOMED", f"{c.d['name']} FOUND A COZY HOME", color="peach", dur=1.4, scale=1,
                             sound="select")
        v["done"] = True
        self.close_view()

    def close_view(self):
        v = self.view
        self.view = None
        self.app.audio.play("back")
        if v["mode"] == "groom" and not v["back"]:
            self.set_state("next")
        elif v["paid"] and not v["done"]:      # cancelled a cafe service: money back
            self.treats += v["paid"]
            self.cafe_used.discard(v["mode"])

    # ---------------------------------------------------------------- KITTY SLOTS + CAT CAFE (bonus floors)
    def open_slots(self):
        self.slots = {"spins": 3, "reels": [0.0, 3.0, 6.0], "stop": [False, False, False], "target": [0, 0, 0],
                      "k": 0, "wait": 0.0, "result": ""}
        self.set_state("slots")

    def update_slots(self, dt):
        sl = self.slots
        inp = self.app.input
        speed = 7.5 - 0.8 * self.lv("bell")
        n = len(SLOT_STRIP)
        for r in range(3):
            if not sl["stop"][r]:
                sl["reels"][r] = (sl["reels"][r] + speed * dt * (1 + 0.15 * r)) % n
            else:
                tgt = sl["target"][r]
                cur = sl["reels"][r]
                if abs(cur - tgt) > 0.01:
                    step = speed * dt
                    d = (tgt - cur) % n
                    sl["reels"][r] = tgt if d <= step else (cur + step) % n
        if sl["k"] < 3:
            if self.state_t > 0.4 and self.a_hit():
                r = sl["k"]
                sl["stop"][r] = True
                sl["target"][r] = int(math.floor(sl["reels"][r] + 1)) % n
                sl["k"] += 1
                self.app.audio.play("lock")
                if sl["k"] == 3:
                    sl["wait"] = 0.0
        else:
            sl["wait"] += dt
            if sl["wait"] > 0.45 and not sl["result"]:
                self.slot_payout()
            if sl["wait"] > 1.8 or (sl["wait"] > 0.8 and self.a_hit()):
                sl["spins"] -= 1
                if sl["spins"] <= 0:
                    self.open_cafe()
                else:
                    sl["k"] = 0
                    sl["stop"] = [False, False, False]
                    sl["result"] = ""
                    self.state_t = 0.0

    def slot_payout(self):
        sl = self.slots
        t1 = self.tier() + 1
        sym = [SLOT_STRIP[int(sl["target"][r]) % len(SLOT_STRIP)] for r in range(3)]
        if sym.count("goldie") == 3:
            sl["result"] = "JACKPOT!!"
            self.hype.jackpot(10000 * t1, "THREE GOLDEN KITTENS!")
            self.treats += 60
            self.deck.append(Card("goldie"))
            self.say("LUCKY GOLDIE JOINED THE CREW!", 2.0)
        elif sym[0] == sym[1] == sym[2] and sym[0] != "fleas":
            sl["result"] = "TRIPLE CATS!"
            self.score_at(2500 * t1, W // 2, 60)
            self.treats += 25
            self.hype.banner("TRIPLE CATS!", "+25 TREATS", color="yellow", dur=1.2, sound="bonus")
            self.hype.shower(40, "coins")
        elif sym[0] == sym[1] == sym[2]:
            sl["result"] = "ITCHY!"
            self.treats += 1
            self.app.audio.play("trap")
        elif len(set(sym)) == 2:
            sl["result"] = "PAIR! +8 TREATS"
            self.score_at(500 * t1, W // 2, 60)
            self.treats += 8
            self.app.audio.play("coin")
        elif "goldie" in sym:
            sl["result"] = "GOLDEN GLIMPSE +5"
            self.treats += 5
            self.app.audio.play("coin")
        else:
            sl["result"] = "NO LUCK"
            self.app.audio.play("move")

    def cafe_items(self):
        t = self.tier()
        return [("ADOPT A CAT", None), ("CATNAP: HEAL 40%", 0 if "nap" not in self.cafe_used else -1),
                ("GROOM A CAT", 35 + 5 * t if "groom" not in self.cafe_used else -1),
                ("REHOME A CAT", 25 + 5 * t if "rehome" not in self.cafe_used else -1), ("LEAVE THE CAFE", None)]

    def open_cafe(self):
        self.cafe_i = 0
        self.cafe_used = set()
        self.shop_offers = self.make_offers(3, shop=True)
        t = self.tier()
        self.shop_prices = [D.PRICE[c.d["rar"]] + 5 * t for c in self.shop_offers]
        self.set_state("cafe")
        self.say("BOBA: WELCOME TO THE CAT CAFE!", 2.0)

    def update_cafe(self, dt):
        inp = self.app.input
        items = self.cafe_items()
        if inp.repeat("up", dt=dt):
            self.cafe_i = (self.cafe_i - 1) % len(items)
            self.app.audio.play("move")
        if inp.repeat("down", dt=dt):
            self.cafe_i = (self.cafe_i + 1) % len(items)
            self.app.audio.play("move")
        if self.state_t > 0.3 and inp.hit("a"):
            self.cafe_pick(self.cafe_i)
        elif self.state_t > 0.3 and inp.hit("x"):
            self.open_view("look")

    def cafe_pick(self, i):
        label, price = self.cafe_items()[i]
        if price == -1:
            self.app.audio.play("back")
            self.say("ALREADY DONE TODAY!")
            return
        if i == 0:
            self.offers, self.prices = self.shop_offers, self.shop_prices
            self.pick_mode = "shop"
            self.pick_i = 0
            self.set_state("reward")
        elif i == 1:
            heal = min(self.maxhp - self.hp, self.maxhp * 2 // 5)
            self.hp += heal
            self.cafe_used.add("nap")
            self.floats.add(60, 120, f"+{heal} HP", "lime")
            self.hype.banner("CATNAP", "TOFU FEELS FRESH", color="lavender", dur=1.2, scale=1, sound="levelup")
        elif i in (2, 3):
            if self.treats < price:
                self.app.audio.play("back")
                self.say("NOT ENOUGH TREATS!")
                return
            if i == 2 and not any(not c.up and c.cid != "fleas" for c in self.deck):
                self.app.audio.play("back")
                self.say("EVERY CAT IS GROOMED!")
                return
            self.treats -= price
            self.cafe_used.add("groom" if i == 2 else "rehome")
            self.open_view("groom" if i == 2 else "rehome", paid=price)
        else:
            self.app.audio.play("select")
            self.start_floor(self.n + 1)

    # ---------------------------------------------------------------- layout
    def foe_x(self, k):
        b = self.battle
        if b is None or k >= len(b.foes):
            return 236
        fo = b.foes[k]
        if any(f.boss for f in b.foes):
            return BOSS_X[fo.slot]
        n = len(b.foes)
        return FOE_X[min(3, n)][min(k, 2)]

    def foe_h(self, k):
        return sprite(self.battle.foes[k].spr).get_height()

    def hand_layout(self, n):
        if n == 0:
            return []
        sp = min(32.0, (HAND_X1 - HAND_X0 - MINI_W) / max(1, n - 1))
        total = MINI_W + sp * (n - 1)
        x0 = HAND_X0 + (HAND_X1 - HAND_X0 - total) / 2
        out = []
        for i in range(n):
            off = i - (n - 1) / 2
            out.append((int(x0 + i * sp), int(140 + off * off * 0.7)))
        return out

    def hand_pos(self, i):
        lay = self.hand_layout(len(self.battle.hand))
        if not lay:
            return HAND_X0, 140
        x, y = lay[min(i, len(lay) - 1)]
        if i == self.sel and self.state == "player":
            y -= 10
        return x, y

    # ---------------------------------------------------------------- touch (iOS taps; also used by tests)
    def tap(self, x, y):
        if self.overlay is not None or self.paused:
            return
        if self.view is not None:
            self.tap_view(x, y)
            return
        s = self.state
        if s == "player":
            b = self.battle
            lay = self.hand_layout(len(b.hand))
            hit = None
            for i in range(len(lay) - 1, -1, -1):     # topmost card first
                cx, cy = self.hand_pos(i)
                if cx <= x < cx + MINI_W and cy <= y < cy + MINI_H + 12:
                    hit = i if hit is None or i == self.sel else hit
            if hit is not None and y >= PANEL_Y:
                if hit == self.sel:
                    self.try_play(hit, self.tgt)
                else:
                    self.sel = hit
                    self.app.audio.play("move")
                return
            for k, fo in enumerate(b.foes):
                if not fo.alive:
                    continue
                sp = sprite(fo.spr)
                fx = self.foe_x(k)
                if abs(x - fx) <= sp.get_width() // 2 + 4 and GROUND - sp.get_height() - 16 <= y <= GROUND + 8:
                    self.tgt = k
                    self.app.audio.play("move")
                    if b.hand and b.hand[self.sel].targeted:
                        self.try_play(self.sel, k)
                    return
            if x < 106 and y >= PANEL_Y and b.hand:
                self.try_play(self.sel, self.tgt)
        elif s in ("intro", "tally", "ko", "slots"):
            self.tap_flag = True
        elif s == "reward":
            for k in range(len(self.offers)):
                if 3 + k * 106 <= x < 3 + k * 106 + BIG_W and 22 <= y < 140:
                    if k == self.pick_i:
                        self.take_offer(k)
                    else:
                        self.pick_i = k
                        self.app.audio.play("move")
                    return
            if 100 <= x < 220 and 146 <= y < 168:
                self.take_offer(len(self.offers))
        elif s == "cafe":
            for i in range(len(self.cafe_items())):
                if 10 <= x < 170 and 46 + i * 18 <= y < 46 + i * 18 + 16:
                    if i == self.cafe_i:
                        self.cafe_pick(i)
                    else:
                        self.cafe_i = i
                        self.app.audio.play("move")

    def tap_view(self, x, y):
        v = self.view
        if v["mode"] == "look":
            self.close_view()
            return
        if x >= 210 and y >= 160:          # the hint corner cancels
            if v["back"]:
                self.close_view()
            return
        first = self.view_first()
        for j, c in enumerate(v["cards"][first:first + 24]):
            cx, cy = 6 + (j % 6) * 34, 16 + (j // 6) * 43
            if cx <= x < cx + MINI_W and cy <= y < cy + MINI_H:
                i = first + j
                if i == v["i"]:
                    self.view_pick(i)
                else:
                    v["i"] = i
                    self.app.audio.play("move")
                return
        if 212 <= x < 316 and 12 <= y < 100:
            self.view_pick(v["i"])

    def view_first(self):
        v = self.view
        row = v["i"] // 6
        top = max(0, min(row - 1, (len(v["cards"]) - 1) // 6 - 3))
        return top * 6

    # ---------------------------------------------------------------- drawing
    def render(self, s):
        t = self.t
        s.fill(col("black"))
        s.blit(self.bg, (0, HUD_H))
        b = self.battle
        st = self.st
        if st["kind"] == "bonus":
            self.draw_cafe_scene(s, t)
        if b is not None:
            self.draw_field(s, t)
            self.draw_panel(s, t)
        self.parts.draw(s)
        self.floats.draw(s)
        if self.state == "reward":
            self.draw_picker(s, t)
        elif self.state == "slots":
            self.draw_slots(s, t)
        elif self.state == "cafe":
            self.draw_cafe(s, t)
        self.draw_hud(s, t)
        if self.state == "intro":
            self.draw_intro(s, t)
        elif self.state == "tally":
            self.draw_tally(s, t)
        if self.view is not None:
            self.draw_view(s, t)
        if self.msg_t > 0:
            w = text_width(self.msg) + 10
            my = 84 if self.state in ("player", "anim", "foes") else HUD_H + 2
            panel(s, (W // 2 - w // 2, my, w, 13), fill="black", border="yellow", radius=3, shadow=False)
            draw_text(s, self.msg, W // 2, my + 3, "yellow", align="center", shadow=None)

    def draw_hud(self, s, t):
        s.fill(col("black"), (0, 0, W, HUD_H))
        draw_text(s, f"{self.score:07d}", 3, 3, "white", shadow=None)
        s.blit(sprite("md_i_treat"), (48, 2))
        draw_text(s, str(self.treats), 57, 3, "orange", shadow=None)
        b = self.battle
        boss = None
        if b is not None:
            boss = next((f for f in b.foes if f.boss and f.alive), None)
        if boss is not None:
            boss_bar(s, boss.name if len(boss.name) <= 14 else boss.name[:14], boss.hp, boss.maxhp, t, y=0, x=84, w=166)
        else:
            label = "CAT CAFE" if self.st["kind"] == "bonus" else f"FLOOR {self.n}"
            draw_text(s, label, 136, 3, "yellow", align="center", shadow=None)
            draw_text(s, f"HI {max(self.best, self.score)}", 252, 3, "gray", align="right", shadow=None)
        self.hearts(s, W - 62, 2, self.lives, max_show=5)
        x0, y0 = W - 62, 10
        s.fill(col("darkgray"), (x0, y0, 40, 2))
        if self.hype.fever_on:
            for i in range(40):
                s.fill(col(rainbow(i // 5, t)), (x0 + i, y0, 1, 2))
        else:
            s.fill(col("orange"), (x0, y0, int(40 * self.hype.fever), 2))
        s.fill(col("darkgray"), (0, HUD_H - 1, W, 1))

    def draw_field(self, s, t):
        b = self.battle
        # hero
        flash = self.hero_flash > 0 and int(t * 30) % 2
        draw_tofu(s, 38, GROUND, t, self.hero_pose, flash)
        h = b.hero
        self.hp_bar(s, 14, GROUND + 1, 50, h.hp, h.maxhp, h.block)
        sx = 6
        for val, icon, c in ((h.zoom, "md_i_up", "orange"), (h.fluff, "md_i_shield", "sky"), (h.purr, "md_i_heart", "pink"),
                             (h.spiky, "md_i_spiky", "gray"), (h.startled, "md_i_down", "lavender"),
                             (h.soaked, "md_i_drop", "sky")):
            if val:
                s.blit(sprite(icon), (sx, GROUND - 46))
                draw_text(s, str(val), sx + 8, GROUND - 46, c, shadow="black")
                sx += 8 + text_width(str(val)) + 3
        # the cat that was just played pops in next to TOFU
        cm = self.cameo
        if cm is not None and (cm["t"] < 0.7 or int(t * 20) % 2):
            c = cm["card"]
            y = 26 + int((1 - ease_out(min(1.0, cm["t"] / 0.15))) * 18)
            rc = D.ROLE_INFO[c.d["role"]][1]
            pygame.draw.rect(s, col("black"), (57, y + 1, 52, 52), border_radius=4)
            pygame.draw.rect(s, col(rc), (56, y, 52, 52), border_radius=4)
            s.blit(sprite(c.d["spr"], 0, scale=2), (58, y + 2))
            draw_text(s, c.name, 82, y - 9, "yellow", align="center", outline="black", shadow=None)
        # foes
        for k, fo in enumerate(b.foes):
            v = self.fx(k)
            if not fo.alive and v["dead"] <= 0:
                continue
            self.draw_foe(s, k, fo, v, t)
        # target info line
        if self.state in ("player", "anim") and 0 <= self.tgt < len(b.foes) and b.foes[self.tgt].alive:
            fo = b.foes[self.tgt]
            info = fo.name + ": " + ("SLEEPING" if fo.sleepy else
                                     "???" if self.st["mod"] == "foggy" else self.intent_label(fo))
            w = text_width(info) + 8
            s.fill(col("black"), (W - w - 2, HUD_H + 2, w, 10))
            draw_text(s, info, W - 6, HUD_H + 4, "white", align="right", shadow=None)
        # flying card
        f = self.flying
        if f is not None:
            a = ease_out(min(1.0, f["t"] / 0.2))
            x = f["x0"] + (f["x1"] - f["x0"]) * a
            y = f["y0"] + (f["y1"] - f["y0"]) * a - math.sin(a * math.pi) * 24
            draw_mini(s, f["card"], int(x), int(y), t, b)

    def intent_label(self, fo):
        mv = fo.intent
        txt = INTENT_TEXT.get(mv[0], mv[0].upper())
        if mv[0] in ("atk", "atkblk"):
            d, hits = self.battle.intent_damage(fo)
            txt += f" {d}" + (f"X{hits}" if hits > 1 else "")
        return txt

    def hp_bar(self, s, x, y, w, hp, maxhp, block=0):
        s.fill(col("black"), (x - 1, y - 1, w + 2, 6))
        s.fill(col("darkgray"), (x, y, w, 4))
        fw = int(w * max(0, hp) / max(1, maxhp))
        s.fill(col("red" if hp > maxhp * 0.3 or int(self.t * 6) % 2 else "yellow"), (x, y, fw, 4))
        s.fill(col("pink"), (x, y, fw, 1))
        draw_text(s, f"{max(0, hp)}/{maxhp}", x + w // 2, y + 5, "white", align="center", shadow="black")
        if block > 0:
            s.blit(sprite("md_i_shield"), (x - 9, y - 3))
            draw_text(s, str(block), x - 6, y + 5, "sky", align="center", shadow="black")

    def draw_foe(self, s, k, fo, v, t):
        sp = sprite(fo.spr, int(t * 2 + k) % 2)
        w, h = sp.get_width(), sp.get_height()
        x = self.foe_x(k)
        lunge = math.sin(min(1.0, v["lunge"] / 0.3) * math.pi) * 12 if v["lunge"] > 0 else 0
        shake = int(math.sin(t * 60) * 2) if v["shake"] > 0 else 0
        dx = int(x - w // 2 - lunge + shake)
        dy = GROUND - h
        if not fo.alive:
            if int(t * 20) % 2:
                return
            dy += int((0.6 - v["dead"]) * 20)
        if v["flash"] > 0 and int(t * 30) % 2:
            sp = sprite(fo.spr, 0, remap={c: "w" for c in "nhoegdiytsrPpbclmuv"})
        if fo.sleepy and fo.alive:
            draw_text(s, "Z", dx + w - 4, dy - 6 - int(t * 4) % 4, "white", shadow="black")
        s.blit(sp, (dx, dy))
        if not fo.alive:
            return
        bw = min(44, max(30, w))
        self.hp_bar(s, x - bw // 2, GROUND + 1, bw, fo.hp, fo.maxhp, fo.block)
        # intent bubble
        iy = dy - 12 + int(math.sin(t * 4 + k) * 1.5)
        if fo.sleepy:
            icon, txt, c = "md_i_zzz", "", "white"
        elif self.st["mod"] == "foggy":
            icon, txt, c = "md_i_quest", "?", "white"
        else:
            mv = fo.intent
            icon = INTENT_ICON.get(mv[0], "md_i_quest")
            txt, c = "", "white"
            if mv[0] in ("atk", "atkblk"):
                d, hits = self.battle.intent_damage(fo)
                txt = f"{d}" + (f"X{hits}" if hits > 1 else "")
                c = "red" if d * hits >= 15 else "white"
            elif mv[0] in ("blk", "shield", "heal"):
                txt = str(fo.val(mv[1]))
            elif mv[0] in ("steal",):
                txt = f"-{mv[1]}"
            elif mv[0] in ("buff", "rally", "fleas"):
                txt = f"+{mv[1]}"
            elif mv[0] in ("scare", "soak"):
                txt = str(mv[1])
            elif mv[0] == "charge":
                txt = "!!"
                c = "orange"
        tw = 9 + (text_width(txt) + 1 if txt else 0)
        s.fill(col("black"), (x - tw // 2 - 1, iy - 1, tw + 2, 9))
        s.blit(sprite(icon), (x - tw // 2, iy))
        if txt:
            draw_text(s, txt, x - tw // 2 + 9, iy + 1, c, shadow=None)
        # statuses
        sx = x - bw // 2
        for val, icon2, cc in ((fo.zoom, "md_i_up", "orange"), (fo.scared, "md_i_down", "lavender"),
                               (fo.dazed, "md_i_skull", "white"), (fo.itchy, "md_i_flea", "lime")):
            if val:
                s.blit(sprite(icon2), (sx, iy - 9))
                draw_text(s, str(val), sx + 8, iy - 9, cc, shadow="black")
                sx += 9 + text_width(str(val)) + 2
        if fo.elite:
            pygame.draw.polygon(s, col("yellow"), [(x - 5, iy - 2), (x - 5, iy - 7), (x - 2, iy - 4), (x, iy - 8),
                                                   (x + 2, iy - 4), (x + 5, iy - 7), (x + 5, iy - 2)])
        if self.state in ("player", "anim") and k == self.tgt:
            c = "yellow" if int(t * 5) % 2 else "white"
            x0, y0, x1, y1 = dx - 3, dy - 2, dx + w + 2, GROUND + 1
            for (cx, cy, ddx, ddy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
                s.fill(col(c), (min(cx, cx + ddx * 4), cy, 5, 1))
                s.fill(col(c), (cx, min(cy, cy + ddy * 4), 1, 5))

    def draw_panel(self, s, t):
        b = self.battle
        s.fill(col("night"), (0, PANEL_Y, W, H - PANEL_Y))
        s.fill(col("lavender"), (0, PANEL_Y, W, 1))
        # fish (energy)
        x = HAND_X0
        for i in range(max(b.max_fish, b.hero.fish)):
            s.blit(sprite("md_i_fish" if i < b.hero.fish else "md_i_fishoff"), (x + i * 9, PANEL_Y + 4))
        draw_text(s, f"{b.hero.fish}/{b.max_fish}", x + max(b.max_fish, b.hero.fish) * 9 + 3, PANEL_Y + 4, "sky",
                  shadow=None)
        # chain
        if b.chain >= 2:
            c = "lime" if int(t * 6) % 2 else "yellow"
            draw_text(s, f"CHAIN X{b.chain} +{min(b.power, b.chain_cap)}", 216, PANEL_Y + 4, c, shadow="black")
        elif b.echo:
            draw_text(s, "ECHO READY", 216, PANEL_Y + 4, "orange", shadow="black")
        if self.n <= 3 and self.state == "player":     # first floors: how to play, right above the hand
            draw_text(s, "{} PICK  Z PLAY  |` AIM  X END", 214, PANEL_Y + 13, "lavender", align="center", shadow=None)
        draw_text(s, f"DRAW {len(b.draw_pile)}", HAND_X0, H - 8, "gray", shadow=None)
        draw_text(s, f"DISC {len(b.discard)}", HAND_X0 + 52, H - 8, "gray", shadow=None)
        can = any(b.can_play(i) for i in range(len(b.hand)))
        hx = W - 3 - (36 if self.hype.fever_on else 0)
        if self.state == "player":
            c = "yellow" if (not can and int(t * 4) % 2) else "lavender"
            draw_text(s, "X: END TURN" if not self.hype.fever_on else "X: END", hx, H - 8, c, align="right",
                      shadow=None)
        elif self.state == "foes":
            draw_text(s, "FOES' TURN", hx, H - 8, "red", align="right", shadow=None)
        # hand
        lay = self.hand_layout(len(b.hand))
        order = [i for i in range(len(b.hand)) if i != self.sel] + ([self.sel] if self.sel < len(b.hand) else [])
        for i in order:
            c = b.hand[i]
            x, y = self.hand_pos(i)
            dt0 = self.deal_t.get(c.uid)
            if dt0 is not None and dt0 < 0.2:
                a = ease_out(max(0.0, dt0) / 0.2)
                x = int(W + (x - W) * a)
                y = int(H + (y - H) * a)
            if self.flying is not None and self.flying["card"] is c:
                continue
            sel = i == self.sel and self.state == "player"
            draw_mini(s, c, x, y, t, b, dim=not b.can_play(i), sel=sel, cost=b.cost(c))
        # big card
        busy = self.state in ("player", "anim", "foes")
        if b.hand and busy and self.sel < len(b.hand):
            c = b.hand[self.sel]
            m = b.link(c)
            note = ("+%d CHAIN" % m) if m > 0 and b.last is not None else None
            draw_big(s, c, 2, PANEL_Y, t, b, cost=b.cost(c), note=note)
        else:
            panel(s, (2, PANEL_Y, BIG_W, BIG_H), fill="ink", border="darkgray")
            if busy:
                draw_text(s, "NO CATS", 2 + BIG_W // 2, PANEL_Y + 30, "gray", align="center", shadow=None)
                draw_text(s, "IN HAND", 2 + BIG_W // 2, PANEL_Y + 40, "gray", align="center", shadow=None)
            else:
                draw_text(s, "TOFU'S CREW", 2 + BIG_W // 2, PANEL_Y + 8, "peach", align="center", shadow=None)
                draw_text(s, f"{len(self.deck)} CATS", 2 + BIG_W // 2, PANEL_Y + 20, "white", align="center",
                          shadow=None)
                for k in range(3):
                    c = self.deck[(int(t * 0.8) + k * 5) % len(self.deck)]
                    s.blit(sprite(c.d["spr"]), (10 + k * 30, PANEL_Y + 34))
                draw_text(s, f"HP {self.hp if self.battle is None else b.hero.hp}/{self.maxhp}", 2 + BIG_W // 2,
                          PANEL_Y + 66, "pink", align="center", shadow=None)

    def draw_intro(self, s, t):
        st = self.st
        k = st["kind"]
        if k == "boss":
            if int(t * 4) % 2:
                for x in range(-20, W + 20, 20):
                    pygame.draw.polygon(s, col("red"), [(x, 108), (x + 10, 108), (x + 20, 116), (x + 10, 116)])
                    pygame.draw.polygon(s, col("red"), [(x, 152), (x + 10, 152), (x + 20, 160), (x + 10, 160)])
            panel(s, (40, 118, 240, 32), fill="black", border="red")
            draw_text(s, "WARNING!!", W // 2, 122, "red" if int(t * 6) % 2 else "yellow", 2, align="center",
                      outline="ink")
            draw_text(s, f"{st['name']} APPROACHES", W // 2, 139, "white", align="center", shadow=None)
            return
        lines = 3 + (1 if st["new"] else 0) + (1 if st["mod"] else 0)
        h = 30 + lines * 10
        y0 = 120 - h // 2
        panel(s, (40, y0, 240, h), fill="ink", border="yellow" if k == "bonus" else "peach")
        if k == "bonus":
            title = "BONUS: CAT CAFE"
            for i, ch in enumerate(title):
                draw_text(s, ch, W // 2 - text_width(title, 2) // 2 + i * 12, y0 + 6 + int(math.sin(t * 8 + i) * 2),
                          rainbow(i, t), 2, outline="ink", shadow=None)
            draw_text(s, "3 FREE SPINS OF KITTY SLOTS,", W // 2, y0 + 26, "white", align="center")
            draw_text(s, "THEN SNACKS, NAPS AND NEW CATS!", W // 2, y0 + 36, "white", align="center")
            draw_text(s, f"TREATS: {self.treats}", W // 2, y0 + 48, "orange", align="center")
            return
        draw_text(s, f"FLOOR {self.n}", W // 2, y0 + 6, "yellow", 2, align="center", outline="ink", shadow=None)
        y = y0 + 24
        draw_text(s, self.theme[0], W // 2, y, "lavender", align="center")
        y += 10
        draw_text(s, st["name"], W // 2, y, "orange" if st["elite"] else "white", align="center")
        y += 10
        if st["mod"]:
            lab, line = D.MODS[st["mod"]]
            draw_text(s, f"{lab}: {line}", W // 2, y, "sky", align="center")
            y += 10
        if st["new"]:
            draw_text(s, st["new"], W // 2, y, "mint" if int(t * 4) % 2 else "lime", align="center")
            y += 10
        draw_text(s, "TOFU: " + st["line"], W // 2, y + 2, "peach", align="center", shadow=None)

    def draw_tally(self, s, t):
        rows = self.tally
        h = 46 + len(rows) * 11
        y0 = 104
        panel(s, (64, y0, 192, h), fill="ink", border="mint")
        head = "BOSS CLEAR!" if self.st["kind"] == "boss" else f"FLOOR {self.n} CLEAR!"
        draw_text(s, head, W // 2, y0 + 6, "mint", align="center")
        for i, (label, v, shown) in enumerate(rows):
            if i > self.tally_i:
                break
            y = y0 + 20 + i * 11
            draw_text(s, label, 72, y, "white" if v else "gray", shadow=None)
            draw_text(s, f"{int(shown)}", 248, y, "yellow" if v else "darkgray", align="right", shadow=None)
        y = y0 + 20 + len(rows) * 11
        s.blit(sprite("md_i_treat"), (72, y))
        draw_text(s, f"TREATS +{self.treats_won}", 82, y, "orange", shadow=None)
        if self.tally_i >= len(rows) and int(t * 3) % 2:
            draw_text(s, "PRESS Z", W // 2, y0 + h - 10, "lavender", align="center", shadow=None)

    def draw_picker(self, s, t):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((12, 8, 24, 200))
        s.blit(ov, (0, 0))
        shop = self.prices is not None
        title = "ADOPT A CAT!" if not shop else "CAFE ADOPTIONS"
        for i, ch in enumerate(title):
            draw_text(s, ch, W // 2 - text_width(title, 2) // 2 + i * 12, 16 + int(math.sin(t * 6 + i * 0.6) * 2),
                      rainbow(i, t), 2, outline="ink", shadow=None)
        for k, c in enumerate(self.offers):
            x = 3 + k * 106
            appear = ease_out(min(1.0, max(0.0, self.state_t * 4 - k * 0.4)))
            sel = k == self.pick_i
            y = 34 + int((1 - appear) * 120) - (4 if sel else 0)
            if c is None:
                panel(s, (x, y, BIG_W, BIG_H), fill="night", border="darkgray")
                draw_text(s, "ADOPTED!", x + BIG_W // 2, y + 40, "gray", align="center", shadow=None)
                continue
            draw_big(s, c, x, y, t)
            if sel and int(t * 6) % 2:
                pygame.draw.rect(s, col("white"), (x - 1, y - 1, BIG_W + 2, BIG_H + 2), 1, border_radius=5)
            have = sum(1 for d in self.deck if d.cid == c.cid)
            tag = "NEW!" if have == 0 else f"YOU HAVE {have}"
            draw_text(s, tag, x + BIG_W // 2, y + BIG_H + 4, "mint" if have == 0 else "gray", align="center",
                      shadow=None)
            if shop:
                p = self.prices[k]
                draw_text(s, f"{p} TREATS", x + BIG_W // 2, y + BIG_H + 13,
                          "orange" if self.treats >= p else "red", align="center", shadow=None)
        sel = self.pick_i == len(self.offers)
        label = "SKIP: +10 TREATS" if not shop else "BACK TO THE CAFE"
        panel(s, (100, 148, 120, 18), fill="ink" if sel else "night", border="yellow" if sel else "darkgray")
        draw_text(s, label, W // 2, 154, "yellow" if sel else "gray", align="center", shadow=None)
        s.blit(sprite("md_i_treat"), (4, 189))
        draw_text(s, str(self.treats), 14, 190, "orange", shadow=None)
        draw_text(s, "LEFT/RIGHT CHOOSE  Z TAKE  C CREW", W - 4, 190, "lavender", align="right", shadow=None)

    def draw_view(self, s, t):
        v = self.view
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((12, 8, 24, 230))
        s.blit(ov, (0, 0))
        draw_text(s, v["title"], 6, 4, "yellow", shadow=None)
        first = self.view_first()
        cards = v["cards"]
        for j, c in enumerate(cards[first:first + 24]):
            i = first + j
            x, y = 6 + (j % 6) * 34, 16 + (j // 6) * 43
            draw_mini(s, c, x, y, t, sel=i == v["i"])
        if len(cards) > first + 24:
            draw_text(s, "`", 104, 188, "white", shadow=None)
        if first > 0:
            draw_text(s, "|", 104, 9, "white", shadow=None)
        if not cards:
            draw_text(s, "NO CATS TO PICK", 104, 90, "gray", align="center", shadow=None)
            return
        c = cards[min(v["i"], len(cards) - 1)]
        groom = v["mode"] == "groom"
        draw_big(s, c, 212, 12, t, upgraded=groom)
        y = 104
        for f in c.fx:
            g = D.GLOSSARY.get(f[0])
            if g:
                draw_text(s, g, 212, y, "lavender", shadow=None)
                y += 9
                if y > 122:
                    break
        y = max(y, 124)
        if self.battle is not None and v["mode"] == "look":
            b = self.battle
            draw_text(s, f"DRAW {len(b.draw_pile)} DISC {len(b.discard)}", 212, y, "gray", shadow=None)
            y += 10
        # charms
        x0 = 212
        k = 0
        for ch in CHARMS:
            lv = self.lv(ch.id)
            if not lv:
                continue
            x, yy = x0 + (k % 5) * 21, y + (k // 5) * 20
            if yy > 172:
                break
            s.blit(sprite(ch.icon), (x, yy))
            draw_text(s, str(lv), x + 13, yy + 10, "yellow", shadow="black")
            k += 1
        hint = {"look": "X/C/Z CLOSE", "groom": "Z: GROOM THIS CAT", "rehome": "Z: REHOME  X: KEEP ALL"}[v["mode"]]
        if groom and v["back"]:
            hint = "Z: GROOM  X: CANCEL"
        draw_text(s, hint, W - 4, 190, "lavender" if int(t * 3) % 2 else "white", align="right", shadow=None)

    def draw_cafe_scene(self, s, t):
        s.fill(col("brown"), (0, HUD_H, W, PANEL_Y - HUD_H))
        for x in range(0, W, 20):
            s.fill(col("choco"), (x, HUD_H, 10, PANEL_Y - HUD_H))
        s.fill(col("peach"), (0, 92, W, 20))
        s.fill(col("choco"), (0, 92, W, 2))
        s.fill(col("cream"), (0, PANEL_Y, W, H - PANEL_Y))
        for x in range(0, W, 16):
            for y in range(PANEL_Y, H, 16):
                if (x // 16 + y // 16) % 2:
                    s.fill(col("peach"), (x, y, 16, 16))
        for i, x in enumerate((22, 62, 262, 300)):
            pygame.draw.rect(s, col("orange"), (x - 6, 36, 12, 16), border_radius=3)
            s.fill(col("white"), (x - 4, 38, 2, 10))
            if i != 0:
                s.blit(sprite(D.CATS[(i * 11 + int(t / 3)) % 60]["spr"]), (x - 12, 68))
        happy = self.slots is not None and "!" in self.slots["result"]
        draw_tofu(s, 30, 108, t, "happy" if happy else "idle")

    def draw_slots(self, s, t):
        sl = self.slots
        panel(s, (80, 30, 160, 112), fill="red", border="yellow", radius=8)
        s.fill(col("hotpink"), (84, 34, 152, 14))
        title = "KITTY SLOTS"
        for i, ch in enumerate(title):
            draw_text(s, ch, W // 2 - text_width(title) // 2 + i * 6, 38, rainbow(i, t), shadow="black")
        n = len(SLOT_STRIP)
        for r in range(3):
            x = 96 + r * 44
            pygame.draw.rect(s, col("white"), (x - 2, 52, 36, 64), border_radius=4)
            pos = sl["reels"][r]
            base = int(math.floor(pos))
            frac = pos - base
            for j in range(-1, 3):
                sym = SLOT_STRIP[(base + j) % n]
                yy = 72 + int((j - frac) * 26) - 12
                blit_rows(s, sprite("md_c_" + sym), x + 5, yy, 53, 115)
            pygame.draw.rect(s, col("yellow" if sl["stop"][r] else "black"), (x - 2, 52, 36, 64), 2, border_radius=4)
        s.fill(col("yellow"), (90, 83, 4, 2))
        s.fill(col("yellow"), (226, 83, 4, 2))
        pygame.draw.line(s, col("gray"), (244, 60), (244, 96), 3)
        pygame.draw.circle(s, col("red"), (244, 58 + (12 if sl["k"] < 3 and int(t * 3) % 2 else 0)), 5)
        draw_text(s, f"SPINS LEFT {sl['spins']}", W // 2, 122, "white", align="center", shadow="black")
        if sl["result"]:
            draw_text(s, sl["result"], W // 2, 131, rainbow(0, t) if "!" in sl["result"] else "white", align="center",
                      shadow="black")
        elif sl["k"] < 3 and int(t * 3) % 2:
            draw_text(s, f"Z: STOP REEL {sl['k'] + 1}", W // 2, 131, "yellow", align="center", shadow="black")
        draw_text(s, "LINE UP 3 GOLDEN KITTENS FOR THE JACKPOT!", W // 2, 186, "choco", align="center", shadow=None)

    def draw_cafe(self, s, t):
        panel(s, (6, 22, 172, 120), fill="ink", border="peach")
        draw_text(s, "CAT CAFE MENU", 92, 28, "peach", align="center", shadow=None)
        for i, (label, price) in enumerate(self.cafe_items()):
            y = 46 + i * 18
            sel = i == self.cafe_i
            if sel:
                pygame.draw.rect(s, col("deep"), (10, y - 3, 164, 15), border_radius=3)
                draw_text(s, "}", 12, y, "yellow", shadow=None)
            c = "gray" if price == -1 else ("yellow" if sel else "white")
            draw_text(s, label, 22, y, c, shadow=None)
            if price is not None and price > 0:
                draw_text(s, str(price), 168, y, "orange" if self.treats >= price else "red", align="right",
                          shadow=None)
            elif price == 0:
                draw_text(s, "FREE", 168, y, "lime", align="right", shadow=None)
            elif price == -1:
                draw_text(s, "DONE", 168, y, "gray", align="right", shadow=None)
        # barista
        s.blit(sprite("md_barista", 1 if int(t * 1.5) % 5 == 0 else 0, scale=2), (226, 44))
        s.fill(col("choco"), (200, 92, 110, 8))
        panel(s, (186, 22, 128, 18), fill="white", border="ink", radius=6, shadow=False)
        draw_text(s, "BOBA: HI TOFU!", 250, 28, "ink", align="center", shadow=None)
        s.blit(sprite("md_i_treat"), (196, 120))
        draw_text(s, f"TREATS {self.treats}", 206, 121, "orange", shadow="black")
        s.blit(sprite("md_i_heart"), (196, 131))
        draw_text(s, f"HP {self.hp}/{self.maxhp}", 206, 131, "pink", shadow="black")
        draw_text(s, "UP/DOWN CHOOSE  Z OK  C CREW", W // 2, 190, "choco", align="center", shadow=None)


# ----------------------------------------------------------------------------- carousel + GIF bot
def preview(s, t):
    w, h = s.get_width(), s.get_height()
    gy = h - 12
    s.fill(col("deep"))
    for y in range(0, gy, 8):
        s.fill(col("ink"), (0, y, w, 4))
    s.fill(col("darkgray"), (0, gy, w, h - gy))
    s.fill(col("black"), (0, gy, w, 1))
    s.blit(sprite("md_tofu", int(t * 2) % 2), (-4, gy - 30))
    pug = sprite("md_f_pug", int(t * 2) % 2)
    s.blit(pug, (w - pug.get_width() + 2, gy - pug.get_height() + 2))
    s.fill(col("black"), (w - 23, gy - 37, 18, 9))
    s.blit(sprite("md_i_claw"), (w - 22, gy - 36))
    draw_text(s, "6", w - 12, gy - 35, "white", shadow=None)
    k = int(t * 1.5)
    for i in (0, 2, 1):           # the middle card on top
        card = Card(D.CATS[(k + i * 7) % 66]["id"])
        card.uid = i
        x = w // 2 - 17 + (i - 1) * 15
        y = 6 + abs(i - 1) * 4 + int(math.sin(t * 3 + i) * 2)
        draw_mini(s, card, x, y, t, sel=i == 1)


def gif_bot(scene):
    """Drop-in for packaging/record_gifs.py: bot(scene) -> fn(frame) -> keys."""

    def f(frame):
        sc = scene
        keys = set()
        if frame % 2:
            return keys
        if sc.overlay is not None:
            if frame % 24 == 0:
                keys.add("a")
            return keys
        if sc.view is not None:
            if frame % 20 == 0:
                keys.add("a")
            return keys
        st = sc.state
        if st in ("intro", "tally", "ko", "slots", "win"):
            if frame % 20 == 0:
                keys.add("a")
            return keys
        if st == "reward":
            if frame % 16 == 0:
                keys.add("a")
            return keys
        if st == "cafe":
            if frame % 16 == 0:
                keys.add("down" if sc.cafe_i < 4 else "a")
            return keys
        if st != "player" or frame % 12:
            return keys
        ch = bot_choice(sc.battle)
        if ch is None:
            keys.add("b")
            return keys
        i, tgt = ch
        if sc.sel != i:
            keys.add("right" if (i - sc.sel) % len(sc.battle.hand) <= len(sc.battle.hand) // 2 else "left")
        elif sc.battle.hand[i].targeted and sc.tgt != tgt:
            sc.tgt = tgt
        else:
            keys.add("a")
        return keys
    return f
