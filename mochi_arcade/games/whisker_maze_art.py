"""WHISKER MAZE art and music: Nori the black cat (pixel sprites), the dust bots, items and bosses
(drawn with primitives so they can look around, get dizzy and flash), plus two original chiptune songs.
Everything here is mirrored by ios/MochiArcade/Games/WhiskerMazeArt.swift (sprites/songs are exported).
"""
import math

import pygame

from mochi_arcade import cute, music, sprites
from mochi_arcade.gfx import col

# ----------------------------------------------------------------------------- Nori (13x12, facing right)
# k fur  d sheen  y eyes  w glint  p nose/ears  r collar  o/y bell
_SIDE = [
    ".....k...k...",
    "....kpk.kpk..",
    "....kkkkkkk..",
    "...kdkkkkkkk.",
    "...kkywkkywk.",
    ".k.kkyykkyyk.",
    ".dk.kkkkpkkk.",
    "..k.krrryrrk.",
    "..kkkkkkokk..",
    "..kdkkkkkkk..",
    "..kkkkkkkkk..",
    "..kk.k..kk.k.",
]
_SIDE2 = _SIDE[:11] + [".kk..kk.k.kk."]
_DOWN = [
    "..k.......k..",
    ".kpk.....kpk.",
    ".kkkkkkkkkkk.",
    ".kdkkkkkkkdk.",
    ".kywkkkkkywk.",
    ".kyykkkkkyyk.",
    "..kkkkpkkkk..",
    "...krrrrrk...",
    "..kkkkykkkk..",
    ".dkkkkokkkkk.",
    "..kkkkkkkkk..",
    "..kk.....kk..",
]
_DOWN2 = _DOWN[:11] + ["...kk...kk..."]
_UP = [
    "..k.......k..",
    ".kkk.....kkk.",
    ".kkkkkkkkkkk.",
    ".kkdkkkkkdkk.",
    ".kkkkkkkkkkk.",
    ".kkkkkkkkkkk.",
    "..kkkkkkkkk..",
    "...krrrrrk...",
    "..kkkkkkkkk..",
    ".kkkkdkkkkkk.",
    "..kkkkkkkkkd.",
    "..kk.....kkk.",
]
_UP2 = _UP[:11] + ["...kk...kkkd."]
_HAPPY = [
    "..k.......k..",
    ".kpk.....kpk.",
    ".kkkkkkkkkkk.",
    ".kdkkkkkkkdk.",
    ".kkykkkkkykk.",
    ".kykykkkykyk.",
    ".pkkkkpkkkkp.",
    "...krrrrrk...",
    "..kkkkykkkk..",
    ".dkkkkokkkkk.",
    "..kkkkkkkkk..",
    "..kk.....kk..",
]
_HURT = [
    "k.k.k...k.k.k",
    ".kkpk...kpkk.",
    "kkkkkkkkkkkkk",
    ".kkkkkkkkkkk.",
    "kkywykkkywykk",
    ".kkykkkkkykk.",
    "kkywykpkywykk",
    ".kkkrrrrrkkk.",
    "kkkkkkykkkkkk",
    ".kkkkkokkkkk.",
    "kkkkkkkkkkkkk",
    ".k.k.k.k.k.k.",
]
_SIT = [
    "..k.......k..",
    ".kpk.....kpk.",
    ".kkkkkkkkkkk.",
    ".kdkkkkkkkdk.",
    ".kywkkkkkywk.",
    ".kyykkkkkyyk.",
    "..kkkkpkkkk..",
    "...krrrrrk...",
    "..kkkkykkkk.k",
    "..kkkkokkkk.k",
    "..kkkkkkkkkkd",
    "..kkkkkkkkk..",
]
_SIT2 = _SIT[:8] + ["..kkkkykkkk..", "..kkkkokkkk..", "..kkkkkkkkkkk", "..kkkkkkkkkkd"]
_BLINK = _SIT[:4] + [".kkkkkkkkkkk.", ".kyykkkkkyyk."] + _SIT[6:]

# items
_NIP = [
    "...l....",
    "..lml...",
    ".lmlml..",
    ".lmllml.",
    "lmllmlml",
    ".lmlmll.",
    "..lml...",
    "...t....",
]
_TUNA = [
    ".kkkkkkkk.",
    "kggggggggk",
    "kbbbbbbbbk",
    "kbsswssbbk",
    "kbswwwsbbk",
    "kbbsssbbbk",
    "kggggggggk",
    ".kkkkkkkk.",
]
_BELL = [
    "...k....",
    "..kyk...",
    ".kyyyk..",
    ".kywyk..",
    "kyyyyyk.",
    "kkkkkkk.",
    "...o....",
]
_GOLD = [
    ".......kk.",
    "..kkkkkyk.",
    ".kyyywyyk.",
    "kyykyyyyyk",
    ".kyyyyyyk.",
    "..kkkkkyk.",
    ".......kk.",
]
_MILK = [
    "..wwwwww..",
    ".wcwwwwww.",
    "kwwwwwwwwk",
    ".kssssssk.",
    "..kkkkkk..",
]
_MOUSE = [
    "....pp....",
    "...pcpp...",
    ".kcccccc..",
    "kcccccccp.",
    ".cccccccc.",
    "..k...k.yy",
]
_MOUSE2 = [
    "....pp....",
    "...pcpp...",
    ".kcccccc..",
    "kcccccccp.",
    ".cccccccc.",
    "...k.k..yy",
]
_TRAP = [
    "..yyyy..",
    ".kggggk.",
    "knnnnnnk",
    "knyhhynk",
    "knnnnnnk",
    ".kkkkkk.",
]
_TRAP_SHUT = [
    "........",
    "........",
    "kggggggk",
    "knnnnnnk",
    "knnnnnnk",
    ".kkkkkk.",
]

ART = {
    "wm_side": [_SIDE, _SIDE2],
    "wm_down": [_DOWN, _DOWN2],
    "wm_up": [_UP, _UP2],
    "wm_happy": [_HAPPY],
    "wm_hurt": [_HURT],
    "wm_sit": [_SIT, _SIT2, _BLINK],
    "wm_nip": [_NIP],
    "wm_tuna": [_TUNA],
    "wm_bell": [_BELL],
    "wm_gold": [_GOLD],
    "wm_milk": [_MILK],
    "wm_mouse": [_MOUSE, _MOUSE2],
    "wm_trap": [_TRAP, _TRAP_SHUT],
}
sprites.ART.update(ART)

# ----------------------------------------------------------------------------- songs (original)
SONGS = {
    # "Tiptoe Tango" - normal stages
    "wm_prowl": {"bpm": 128, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.24, "notes":
            "D5:8 R:8 F5:8 R:8 A5:8 G#5:8 A5:4  D6:8 C6:8 A5:8 F5:8 G5:4 R:4 "
            "A#4:8 R:8 D5:8 R:8 F5:8 E5:8 F5:4  A5:8 G5:8 F5:8 D5:8 E5:4 R:4 "
            "D5:8 F5:8 A5:8 D6:8 C#6:4 A5:4  A#5:8 A5:8 G5:8 F5:8 G5:4 A5:4 "
            "F5:8 E5:8 D5:8 E5:8 F5:8 G5:8 A5:4  G#5:8 A5:8 R:8 E5:8 D5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.55, "notes": music._bass(["D", "D", "A#", "C", "D", "G", "A", "A"])},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, "K:8 H:8 H:8 K:8 S:8 H:8 K:8 H:8")},
    ]},
    # "Moon Over the Fridge" - every other room
    "wm_moon": {"bpm": 118, "channels": [
        {"wave": "square", "duty": 0.5, "vol": 0.2, "decay": 0.5, "notes":
            "E5:8 G5:8 B5:8 E6:8 D6:4 B5:4  C6:8 B5:8 A5:8 G5:8 A5:2 "
            "A5:8 C6:8 E6:8 C6:8 B5:4 G5:4  F#5:8 G5:8 A5:8 B5:8 F#5:2 "
            "G5:8 B5:8 D6:8 G6:8 F#6:4 D6:4  E6:8 D6:8 C6:8 B5:8 C6:4 E6:4 "
            "D6:8 C6:8 B5:8 A5:8 G5:8 A5:8 B5:4  D#5:8 F#5:8 A5:8 B5:8 E5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.7, "notes": music._bass(["E", "C", "A", "B", "G", "C", "D", "B"], "4")},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, "K:4 H:8 H:8 S:4 H:8 H:8")},
    ]},
}
music.SONGS.update(SONGS)


# ----------------------------------------------------------------------------- Nori
RIM = {c: "v" for c in "kdywpro"}      # moonlit outline: every colour -> lavender


def nori_pose(d, t, moving, mood):
    """(sprite name, frame, flip, bob) for Nori's current pose."""
    if mood == "hurt":
        return "wm_hurt", 0, False, 0
    if mood == "happy":
        return "wm_happy", 0, False, 0
    if not moving:
        return "wm_sit", 2 if int(t * 1.3) % 6 == 0 else int(t * 2) % 2, False, 0
    f = int(t * 9) % 2
    bob = -1 if f else 0
    if d[0]:
        return "wm_side", f, d[0] < 0, bob
    if d[1] < 0:
        return "wm_up", f, False, bob
    return "wm_down", f, False, bob


def draw_nori(s, cx, cy, d, t, moving, mood="", flash=False):
    """Nori centred at (cx, cy) with her lavender rim. d: facing (dx, dy). mood: '' | happy | hurt."""
    name, f, flip, bob = nori_pose(d, t, moving, mood)
    x, y = int(cx) - 6, int(cy) - 6 + bob
    rim = sprite_at(name, f, flip, RIM)
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        s.blit(rim, (x + ox, y + oy))
    s.blit(sprite_at(name, f, flip, {"k": "w", "d": "w"} if flash else None), (x, y))


def sprite_at(name, frame, flip, remap):
    from mochi_arcade.gfx import sprite
    return sprite(name, frame, flip, remap)


# ----------------------------------------------------------------------------- dust bots
BOT_COLORS = {      # body, dark, accent
    "sniffy": ("peach", "brown", "pink"),
    "zig": ("lime", "teal", "yellow"),
    "fridgy": ("sky", "blue", "white"),
    "snoozy": ("lavender", "purple", "yellow"),
    "mopsy": ("mint", "teal", "white"),
    "spritz": ("pink", "hotpink", "sky"),
    "ruff": ("orange", "brown", "choco"),
    "bunny": ("gray", "darkgray", "white"),
}


def draw_bot(s, kind, cx, cy, t, look=(0, 0), state="", flash=False):
    """A dust bot centred at (cx, cy). state: '' | dizzy | sleep | alert | frozen | tired | aim.
    Dizzy bots wobble with swirly eyes under a ring of cartoon stars (the stars blink when flash is set)."""
    if state == "dizzy":
        wob = int(math.sin(t * 18 + cx) * 1.5)
        _bot_body(s, kind, cx + wob, cy, t, (0, 0), "dizzy")
        if not flash:
            for i in range(3):
                a = t * 6 + i * 2.09
                sx, sy = int(cx + math.cos(a) * 6), int(cy - 10 + math.sin(a) * 2)
                s.fill(col("yellow"), (sx - 1, sy, 3, 1))
                s.fill(col("yellow"), (sx, sy - 1, 1, 3))
        return
    _bot_body(s, kind, cx, cy, t, look, state)


def _bot_body(s, kind, cx, cy, t, look, state):
    body, dark, acc = BOT_COLORS[kind]
    if state == "frozen":
        body, dark, acc = "sky", "blue", "white"
    k = col("black")
    cx, cy = int(cx), int(cy)
    bob = int(math.sin(t * 12 + cx) * 1) if state not in ("sleep", "frozen", "puck") else 0
    lx, ly = look
    y = cy + bob
    if kind == "fridgy":
        r = pygame.Rect(cx - 5, y - 7, 11, 13)
        pygame.draw.rect(s, k, r.inflate(2, 2), border_radius=3)
        pygame.draw.rect(s, col(body), r, border_radius=3)
        s.fill(col(dark), (r.x, y - 1, r.w, 1))
        s.fill(col(acc), (r.right - 3, y - 5, 1, 3))
        s.fill(col(acc), (r.right - 3, y + 1, 1, 3))
        _bot_eyes(s, cx - 1 + lx, y - 4 + ly, state, t)
        s.fill(k, (cx - 4, y + 6, 3, 1))
        s.fill(k, (cx + 2, y + 6, 3, 1))
        return
    if kind == "spritz":
        pygame.draw.polygon(s, k, [(cx - 5, y + 6), (cx + 5, y + 6), (cx + 4, y - 3), (cx - 4, y - 3)])
        pygame.draw.polygon(s, col(body), [(cx - 4, y + 5), (cx + 4, y + 5), (cx + 3, y - 2), (cx - 3, y - 2)])
        s.fill(k, (cx - 3, y - 7, 7, 5))
        s.fill(col(dark), (cx - 2, y - 6, 5, 3))
        nx = cx + 4 if lx >= 0 else cx - 6
        s.fill(col(acc), (nx, y - 6, 3, 2))
        s.fill(col("white"), (cx - 3, y + 1, 1, 3))
        _bot_eyes(s, cx + lx, y + ly, state, t, gap=2)
        return
    if kind == "ruff":
        pygame.draw.circle(s, k, (cx, y + 1), 7)
        pygame.draw.circle(s, col(body), (cx, y + 1), 6)
        pygame.draw.circle(s, col(acc), (cx, y + 1), 6, 1)
        flop = int(math.sin(t * 10) * 1)
        for side in (-1, 1):
            pygame.draw.ellipse(s, col(dark), (cx + side * 6 - 2, y - 4 + flop, 4, 7))
        wag = int(math.sin(t * 18) * 2)
        s.fill(col(dark), (cx - lx * 7 + wag - 1, y - 6, 2, 3))
        _bot_eyes(s, cx + lx, y + ly, state, t)
        s.fill(k, (cx - 1 + lx, y + 3, 3, 2))
        return
    # round bots: sniffy, zig, snoozy, mopsy, bunny
    if kind == "bunny":
        for a in range(0, 360, 60):
            rr = math.radians(a + t * 90)
            pygame.draw.circle(s, col(dark), (cx + int(math.cos(rr) * 4), y + int(math.sin(rr) * 3)), 2)
        pygame.draw.circle(s, col(body), (cx, y), 4)
        _bot_eyes(s, cx + lx, y - 1 + ly, state, t, gap=1)
        return
    pygame.draw.ellipse(s, k, (cx - 7, y - 6, 15, 13))
    pygame.draw.ellipse(s, col(body), (cx - 6, y - 5, 13, 11))
    s.fill(col(dark), (cx - 5, y + 3, 11, 1))
    if kind == "sniffy":
        s.fill(col(acc), (cx - 1 + lx * 3, y + 1 + ly, 3, 2))
        s.fill(k, (cx + lx * 3, y + 1 + ly, 1, 1))
        s.fill(col(dark), (cx, y - 9, 1, 3))
        s.fill(col(acc), (cx - 1, y - 10, 3, 2))
    elif kind == "zig":
        pts = [(cx - 4, y - 5), (cx - 1, y - 2), (cx + 1, y - 4), (cx + 4, y - 1)]
        for a, b in zip(pts, pts[1:]):
            pygame.draw.line(s, col(acc), a, b)
    elif kind == "snoozy":
        pygame.draw.polygon(s, col(acc), [(cx - 5, y - 4), (cx + 4, y - 5), (cx + 8, y - 9)])
        s.fill(col("white"), (cx + 7, y - 10, 2, 2))
    elif kind == "mopsy":
        for i in range(-6, 7, 2):
            s.fill(col(acc), (cx + i, y + 5 + (i // 2) % 2, 1, 3))
    eye_state = "sleep" if state == "sleep" else state
    _bot_eyes(s, cx + lx, y - 1 + ly, eye_state, t)


def _bot_eyes(s, x, y, state, t, gap=3):
    k = col("black")
    if state == "sleep":
        s.fill(k, (x - gap - 1, y, 3, 1))
        s.fill(k, (x + gap - 1, y, 3, 1))
        return
    if state == "dizzy":
        for side in (-1, 1):
            a = t * 14 * side
            ex = x + side * gap
            s.fill(col("white"), (ex - 1, y - 1, 3, 3))
            s.fill(k, (ex + int(math.cos(a) * 1.5), y + int(math.sin(a) * 1.5), 1, 1))
        return
    if state in ("tired", "frozen"):
        for side in (-1, 1):
            s.fill(k, (x + side * gap - 1, y, 3, 1))
            s.fill(k, (x + side * gap, y + 1, 1, 1))
        return
    red = state in ("alert", "aim")
    for side in (-1, 1):
        ex = x + side * gap
        s.fill(col("white"), (ex - 1, y - 1, 3, 3))
        s.fill(col("red") if red else k, (ex, y, 1, 1) if not red else (ex - 1, y - 1, 3, 3))
        if red:
            s.fill(col("white"), (ex - 1, y - 1, 1, 1))


def draw_led(s, cx, cy, t):
    """Lights-out stages: bots' red eyes glow in the dark."""
    c = col("red" if int(t * 4) % 2 else "hotpink")
    s.fill(c, (int(cx) - 4, int(cy) - 1, 2, 2))
    s.fill(c, (int(cx) + 2, int(cy) - 1, 2, 2))


def draw_reboot(s, cx, cy, t):
    """A batted bot flying home to its dock: a spinning shell with sparks."""
    cx, cy = int(cx), int(cy)
    pygame.draw.circle(s, col("darkgray"), (cx, cy), 4)
    pygame.draw.circle(s, col("gray"), (cx, cy), 4, 1)
    a = t * 20
    s.fill(col("yellow"), (cx + int(math.cos(a) * 6), cy + int(math.sin(a) * 6), 1, 1))
    s.fill(col("sky"), (cx - int(math.cos(a) * 6), cy - int(math.sin(a) * 6), 1, 1))


# ----------------------------------------------------------------------------- floor items
def draw_crumb(s, x, y, t, fever=False, i=0):
    if fever:
        from mochi_arcade.arcade import rainbow
        s.fill(col(rainbow(i, t)), (x - 1, y - 1, 2, 2))
        return
    s.fill(col("cream"), (x - 1, y - 1, 2, 2))
    s.fill(col("peach"), (x, y, 1, 1))


def draw_secret(s, x, y, t):
    """A fish-bone treat on a paw-print passage."""
    c = col("white")
    s.fill(c, (x - 3, y, 6, 1))
    s.fill(c, (x - 2, y - 1, 1, 3))
    s.fill(c, (x, y - 1, 1, 3))
    s.fill(col("yellow" if int(t * 4) % 2 else "white"), (x + 3, y - 1, 1, 3))


def draw_paws(s, x, y, glow, t):
    """Paw prints on a cat-only wall tile."""
    c = col("yellow" if glow and int(t * 6) % 2 else "lavender" if glow else "gray")
    for px, py in ((x + 2, y + 5), (x + 6, y + 2)):
        s.fill(c, (px, py, 2, 2))
        s.fill(c, (px - 1, py - 2, 1, 1))
        s.fill(c, (px + 1, py - 2, 1, 1))
        s.fill(c, (px + 2, py - 1, 1, 1))


# ----------------------------------------------------------------------------- bosses
BOSS_LOOK = {   # body, dark, accent
    "queen": ("pink", "hotpink", "yellow"),
    "slipper": ("pink", "peach", "white"),
    "snap": ("brown", "choco", "yellow"),
    "toaster": ("gray", "darkgray", "orange"),
    "bucket": ("sky", "blue", "white"),
    "empress": ("yellow", "orange", "white"),
}


def draw_boss(s, kind, cx, cy, t, mood="", flash=False, wind=0.0):
    """Big boss centred at (cx, cy) (about 32x26). mood: '' | angry | stun | dead. wind: 0..1 attack wind-up."""
    body, dark, acc = BOSS_LOOK[kind]
    if flash:
        body = dark = "white"
    k = col("black")
    cx, cy = int(cx + (math.sin(t * 50) * 2 if wind > 0.5 else 0)), int(cy)
    em = "angry" if mood == "angry" or wind > 0 else "wow" if mood == "stun" else "happy"
    if kind in ("queen", "empress"):
        pygame.draw.ellipse(s, k, (cx - 17, cy - 8, 35, 20))
        pygame.draw.ellipse(s, col(dark), (cx - 16, cy - 6, 33, 17))
        pygame.draw.ellipse(s, col(body), (cx - 16, cy - 8, 33, 15))
        pygame.draw.ellipse(s, col("white"), (cx - 10, cy - 6, 8, 3))
        for i in range(-12, 13, 4):      # side brushes
            a = t * 16 + i
            s.fill(col("gray"), (cx + i + int(math.cos(a) * 1), cy + 10, 1, 2))
        # crown
        ccol = col("yellow" if kind == "queen" else "white")
        pygame.draw.polygon(s, ccol, [(cx - 7, cy - 8), (cx - 7, cy - 14), (cx - 4, cy - 10), (cx, cy - 16),
                                      (cx + 4, cy - 10), (cx + 7, cy - 14), (cx + 7, cy - 8)])
        s.fill(col("red"), (cx - 1, cy - 12, 2, 2))
        if kind == "empress":
            s.fill(col("sky"), (cx - 6, cy - 11, 1, 1))
            s.fill(col("sky"), (cx + 6, cy - 11, 1, 1))
        cute.eyes(s, cx, cy - 2, 5, 0, em, size=2)
        cute.mouth(s, cx, cy + 3, "angry" if em == "angry" else "happy")
    elif kind == "slipper":
        pygame.draw.ellipse(s, k, (cx - 17, cy - 8, 35, 20))
        pygame.draw.ellipse(s, col(body), (cx - 16, cy - 7, 33, 18))
        pygame.draw.ellipse(s, col(dark), (cx - 16, cy + 4, 33, 7))
        pygame.draw.ellipse(s, col("hotpink"), (cx + 2, cy - 7, 14, 12))     # the toe cap
        for a in range(0, 360, 45):                                          # pompom
            rr = math.radians(a + t * 40)
            pygame.draw.circle(s, col(acc), (cx + 9 + int(math.cos(rr) * 3), cy - 9 + int(math.sin(rr) * 3)), 2)
        pygame.draw.circle(s, col(acc), (cx + 9, cy - 9), 3)
        cute.eyes(s, cx - 6, cy - 1, 4, 0, em, size=2)
        cute.mouth(s, cx - 6, cy + 4, "angry" if em != "happy" else "flat")
        for i in range(3):
            s.fill(col("white"), (cx - 14 + i * 3, cy + 7, 1, 1))
    elif kind == "snap":
        r = pygame.Rect(cx - 16, cy - 4, 32, 14)
        pygame.draw.rect(s, k, r.inflate(2, 2), border_radius=2)
        pygame.draw.rect(s, col(body), r, border_radius=2)
        for i in range(r.x + 2, r.right - 2, 5):
            s.fill(col(dark), (i, r.y + 2, 3, 1))
        open_a = 0.5 + 0.5 * math.sin(t * 4) if wind == 0 else 1.0 - wind
        bar_y = cy - 4 - int(10 * open_a)
        pygame.draw.line(s, col("gray"), (cx - 14, cy - 4), (cx - 14, bar_y), 2)
        pygame.draw.line(s, col("gray"), (cx + 14, cy - 4), (cx + 14, bar_y), 2)
        pygame.draw.line(s, col("white"), (cx - 14, bar_y), (cx + 14, bar_y), 2)
        pygame.draw.polygon(s, col(acc), [(cx + 6, cy - 4), (cx + 13, cy - 4), (cx + 13, cy - 9)])
        s.fill(col("orange"), (cx + 10, cy - 6, 1, 1))
        for i in range(-14, 15, 4):     # treads
            s.fill(col("darkgray"), (cx + i + int(t * 20) % 4, cy + 11, 2, 2))
        cute.eyes(s, cx - 3, cy + 3, 4, 0, em, size=2)
    elif kind == "toaster":
        r = pygame.Rect(cx - 15, cy - 8, 30, 20)
        pygame.draw.rect(s, k, r.inflate(2, 2), border_radius=5)
        pygame.draw.rect(s, col(body), r, border_radius=5)
        s.fill(col("white"), (r.x + 3, r.y + 2, 3, 12))
        for sx in (cx - 8, cx + 2):     # toast slices peeking out
            pop = int(abs(math.sin(t * 3 + sx)) * 3) + int(wind * 4)
            pygame.draw.rect(s, col("peach"), (sx, cy - 13 - pop, 7, 7), border_radius=2)
            s.fill(col("brown"), (sx, cy - 13 - pop, 7, 1))
        s.fill(col(dark), (r.x, r.bottom - 4, r.w, 2))
        s.fill(col(acc), (r.right - 4, cy - 2, 2, 5))
        cute.eyes(s, cx - 2, cy + 1, 5, 0, em, size=2)
        cute.mouth(s, cx - 2, cy + 6, "angry" if em != "happy" else "happy")
    else:   # bucket
        pygame.draw.polygon(s, k, [(cx - 15, cy - 7), (cx + 15, cy - 7), (cx + 12, cy + 13), (cx - 12, cy + 13)])
        pygame.draw.polygon(s, col(body), [(cx - 14, cy - 6), (cx + 14, cy - 6), (cx + 11, cy + 12), (cx - 11, cy + 12)])
        s.fill(col(dark), (cx - 13, cy - 3, 26, 2))
        pygame.draw.line(s, col("gray"), (cx - 13, cy - 7), (cx - 8, cy - 14))
        pygame.draw.line(s, col("gray"), (cx - 8, cy - 14), (cx + 8, cy - 14))
        pygame.draw.line(s, col("gray"), (cx + 8, cy - 14), (cx + 13, cy - 7))
        for i in range(-8, 9, 3):       # mop hair
            sway = int(math.sin(t * 6 + i) * 2)
            pygame.draw.line(s, col(acc), (cx + i, cy - 7), (cx + i + sway, cy - 14), 1)
        cute.eyes(s, cx, cy + 3, 5, 0, em, size=2)
        cute.mouth(s, cx, cy + 8, "angry" if em != "happy" else "happy")
    if mood == "stun":
        for i in range(3):
            a = t * 6 + i * 2.1
            s.fill(col("yellow"), (cx + int(math.cos(a) * 14), cy - 16 + int(math.sin(a) * 3), 2, 2))
