"""COMET KITTY campaign tables: 200 stages built from curated templates plus seeded variation.

Everything here is deterministic (random.Random(seed) per stage) and is exported to the iOS port through
comet_kitty.EXPORT, so both platforms fly exactly the same 200 stages.

- 20 tiers of 10 stages, each tier with its own space backdrop (nebula colours, a planet).
- Normal stages: a formation template (ASCII art below) filled with the tier's enemy roster; enemies fly in
  along entry paths in squads, settle into formation and dive at Tama.
- Every x5 stage is a BONUS PARADE (no shooting back), every 10th stage a boss.
"""
import math
import random

from mochi_arcade.arcade import STAGES, is_boss, is_bonus, tier

W, H = 320, 200
STEP = 3.0          # path polylines are resampled to one point every STEP pixels
COL_DX, ROW_DY, ROW_Y0 = 18, 13, 26   # formation lattice: x = centre + col * COL_DX, y = ROW_Y0 + row * ROW_DY
PLAYER_TOP = 126    # entry paths never dip below this line (the player's flying band starts here)

# ----------------------------------------------------------------------------- enemies
# id: name, hp, (points in formation, points diving), tier it first appears, intro line
KINDS = [
    ("JELLY", 1, 50, 100, 0, "WOBBLY AND WEAK"),
    ("MOTH", 1, 80, 160, 0, "DIVES IN PAIRS"),
    ("PUFF", 2, 150, 400, 0, "LEADS A SQUAD - DROPS MEDALS"),
    ("DART SQUID", 1, 100, 250, 1, "AIMS, THEN DASHES STRAIGHT DOWN"),
    ("SPORE", 1, 120, 300, 2, "SHOOTS FROM THE FORMATION"),
    ("BLOB", 2, 150, 300, 3, "SPLITS IN TWO WHEN POPPED"),
    ("SHELL", 3, 200, 500, 4, "BUBBLE ARMOUR - KEEP SHOOTING"),
    ("COMET", 1, 120, 350, 5, "KAMIKAZE - HOMES IN ON YOU"),
    ("URCHIN", 2, 160, 400, 6, "LAYS FLOATING MINES"),
    ("WISP", 1, 200, 500, 7, "FADES OUT - SHOOT WHEN SOLID"),
    ("MINI", 1, 60, 120, 99, ""),          # blob halves and boss minions
    ("MINE", 1, 30, 30, 99, ""),
    ("METEOR", 3, 100, 100, 99, ""),
    ("GOLD COMET", 4, 0, 0, 99, ""),
]
JELLY, MOTH, PUFF, DART, SPORE, BLOB, SHELL, COMET, URCHIN, WISP, MINI, MINE, METEOR, GOLD = range(14)
ROLE_KINDS = {"L": (PUFF, SHELL, URCHIN), "A": (MOTH, SPORE, SHELL, URCHIN, WISP), "B": (JELLY, DART, BLOB, COMET)}

# ----------------------------------------------------------------------------- formations
# 15 columns (centre = column 7) x up to 7 rows. L leader, A middle, B basic.
TEMPLATES = {
    "BLOCK": (0, ["......LLL......",
                  "....AAAAAAA....",
                  "....AAAAAAA....",
                  "...BBBBBBBBB...",
                  "...BBBBBBBBB..."]),
    "VEE": (0, ["LL...........LL",
                ".AA.........AA.",
                "..BB.......BB..",
                "...BB.....BB...",
                "....AA...AA....",
                ".....BB.BB.....",
                "......LLL......"]),
    "DIAMOND": (0, [".......L.......",
                    "......LAL......",
                    ".....AABAA.....",
                    "....BBBBBBB....",
                    ".....AABAA.....",
                    "......BAB......",
                    ".......B......."]),
    "ARC": (0, ["L.............L",
                "AA...........AA",
                ".AA.........AA.",
                "..BBB.....BBB..",
                "....BBBBBBB....",
                "......AAA......"]),
    "PYRAMID": (1, [".......L.......",
                    "......LLL......",
                    ".....AAAAA.....",
                    "....AAAAAAA....",
                    "...BBBBBBBBB...",
                    "..BBBBBBBBBBB.."]),
    "TWIN": (1, [".LLL.......LLL.",
                 ".AAA.......AAA.",
                 "BBBBB.....BBBBB",
                 "BBBBB.....BBBBB",
                 ".AAA.......AAA."]),
    "RING": (2, [".....LLLLL.....",
                 "...AA.....AA...",
                 "..B.........B..",
                 "..B...LLL...B..",
                 "..B.........B..",
                 "...AA.....AA...",
                 ".....BBBBB....."]),
    "CHEVRON": (2, ["L.............L",
                    "AA...........AA",
                    "BBB.........BBB",
                    ".BBB.......BBB.",
                    "..AAA.....AAA..",
                    "...BBB...BBB...",
                    "....LLLLLLL...."]),
    "WAVE": (3, ["LL....LLL....LL",
                 "AAA..AAAAA..AAA",
                 ".BBBBB...BBBBB.",
                 "..BBB.....BBB.."]),
    "CROSS": (3, ["LL...........LL",
                  "..AA.......AA..",
                  "....BB...BB....",
                  "......LLL......",
                  "....BB...BB....",
                  "..AA.......AA..",
                  "BB...........BB"]),
    "COLUMNS": (4, ["LL....LLL....LL",
                    "AA....AAA....AA",
                    "BB....BBB....BB",
                    "BB....BBB....BB",
                    "AA....AAA....AA",
                    "BB....BBB....BB"]),
    "HEART": (4, ["..LLL.....LLL..",
                  ".AAAAA...AAAAA.",
                  ".BBBBBBBBBBBBB.",
                  "..BBBBBBBBBBB..",
                  "....AAAAAAA....",
                  "......BBB......",
                  ".......L......."]),
    "STAR": (5, [".......L.......",
                 "......AAA......",
                 "LAAABBBBBBBAAAL",
                 "...BBBBBBBBB...",
                 "....BBB.BBB....",
                 "...AA.....AA...",
                 "..L.........L.."]),
    "BOWTIE": (5, ["LA...........AL",
                   "BBA.........ABB",
                   "BBBA.......ABBB",
                   "BBBBA.LLL.ABBBB",
                   "BBBA.......ABBB",
                   "BBA.........ABB",
                   "LA...........AL"]),
}


def template_cells(name):
    cells = []
    for r, row in enumerate(TEMPLATES[name][1]):
        assert len(row) == 15, (name, r, len(row))
        for c, ch in enumerate(row):
            if ch != ".":
                cells.append((c - 7, r, ch))
    return cells


# ----------------------------------------------------------------------------- paths
def _catmull(pts, step=STEP):
    """Smooth curve through the waypoints, resampled to one point every `step` pixels."""
    if len(pts) < 2:
        return [list(p) for p in pts]
    ext = [pts[0]] + list(pts) + [pts[-1]]
    dense = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        n = max(4, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / 2))
        for k in range(n):
            u = k / n
            u2, u3 = u * u, u * u * u
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * u + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * u2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * u3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * u + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * u2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * u3)
            dense.append((x, y))
    dense.append(pts[-1])
    out = [dense[0]]
    acc = 0.0
    for a, b in zip(dense, dense[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        while acc + seg >= step and seg > 0:
            f = (step - acc) / seg
            a = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            out.append(a)
            acc = 0.0
        acc += seg
    out.append(dense[-1])
    return [[int(round(x)), int(round(y))] for x, y in out]


def _arc(cx, cy, rx, ry, a0, a1, n):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _entry_paths():
    p = {}
    p["swoop"] = [(-20, 24), (40, 40), (100, 90), (160, 112), (220, 96), (240, 60), (200, 40)]
    p["loop"] = [(-20, 110), (40, 104)] + _arc(90, 72, 32, 32, 90, -270, 16) + [(150, 96), (190, 70)]
    p["sweep"] = [(-20, 112), (60, 118), (160, 114), (250, 100), (290, 70), (250, 44), (190, 50)]
    p["drop"] = [(110, -20), (115, 30), (125, 80), (150, 106), (185, 94), (190, 60)]
    p["zigzag"] = [(30, -20), (70, 20), (20, 50), (90, 75), (40, 100), (120, 112), (170, 80)]
    p["hook"] = [(16, -20), (16, 60), (30, 100), (70, 114), (120, 102), (140, 70)]
    p["spiral"] = [(-20, 60)] + [(160 + (140 - 115 * i / 36) * math.cos(math.radians(180 + 15 * i)),
                                  70 + (140 - 115 * i / 36) * 0.38 * math.sin(math.radians(180 + 15 * i)))
                                 for i in range(37)]
    p["snake"] = [(-20 + 20 * i, 64 + 36 * math.sin(i * 0.62)) for i in range(17)] + [(260, 40)]
    p["figure8"] = [(-20, 40)] + [(160 + 100 * math.sin(math.radians(a)), 72 + 34 * math.sin(math.radians(2 * a)))
                                  for a in range(-90, 271, 15)]
    p["corkscrew"] = [(-20 + 270 * u - 26 * math.sin(6 * math.pi * u), 72 - 30 * math.cos(6 * math.pi * u))
                      for u in [i / 48 for i in range(49)]]
    p["dive8"] = [(60, -20), (80, 50), (120, 112), (160, 116), (200, 112), (240, 50), (220, 20), (180, 30)]
    p["wide"] = [(-20, 64)] + _arc(160, 64, 130, 52, 180, 540, 32)
    return p


ENTRY_UNLOCK = {"swoop": 0, "loop": 0, "sweep": 0, "drop": 0, "zigzag": 1, "hook": 1, "spiral": 2, "snake": 2,
                "figure8": 3, "corkscrew": 4, "dive8": 5, "wide": 5}


def _parade_paths():
    p = {}
    p["arch"] = [(-20, 170), (60, 80), (160, 30), (260, 80), (340, 170)]
    p["dip"] = [(-20, 30), (80, 120), (160, 160), (240, 120), (340, 30)]
    p["loopthru"] = [(-20, 70), (100, 80)] + _arc(160, 90, 44, 44, 180, -180, 16) + [(220, 80), (340, 70)]
    p["zig"] = [(-20, 40), (60, 140), (120, 40), (180, 140), (240, 40), (340, 140)]
    p["spiralout"] = [(160 + (8 + 160 * i / 40) * math.cos(math.radians(90 + 18 * i)),
                       96 + (8 + 160 * i / 40) * 0.6 * math.sin(math.radians(90 + 18 * i))) for i in range(41)]
    p["rain"] = [(80, -20), (96, 50), (60, 100), (100, 150), (76, 224)]
    p["wave"] = [(-20 + 20 * i, 100 + 50 * math.sin(i * 0.5)) for i in range(19)]
    p["eight"] = [(-20, 96)] + [(160 + 120 * math.sin(math.radians(a)), 96 + 50 * math.sin(math.radians(2 * a)))
                                for a in range(-90, 271, 12)] + [(340, 96)]
    p["bounce"] = [(-20, 40), (50, 160), (110, 60), (170, 160), (230, 60), (290, 160), (340, 100)]
    p["orbit"] = [(-20, 96)] + _arc(160, 96, 110, 70, 180, 630, 40) + [(250, 10), (340, -20)]
    return p


ENTRY = _entry_paths()
PARADE = _parade_paths()
PATH_NAMES = list(ENTRY) + list(PARADE)
PATHS = [_catmull(ENTRY[k]) for k in ENTRY] + [_catmull(PARADE[k]) for k in PARADE]


def path_index(name):
    return PATH_NAMES.index(name)


# ----------------------------------------------------------------------------- themes (one per tier)
def _theme(name, top, bot, neb, planet, seed):
    rnd = random.Random(seed)
    blobs = []
    for i in range(7):
        c = neb[i % len(neb)]
        blobs.append([rnd.randint(10, 310), rnd.randint(20, 180), rnd.randint(22, 54), list(c), rnd.randint(18, 34)])
    kind, pc1, pc2 = planet
    px = rnd.choice((rnd.randint(40, 90), rnd.randint(230, 280)))
    rocks = []
    if kind == 6:   # asteroid belt: a diagonal band of little rocks
        for i in range(34):
            u = i / 33
            rocks.append([int(-10 + 340 * u + rnd.randint(-8, 8)), int(150 - 110 * u + rnd.randint(-12, 12)),
                          rnd.choice((1, 1, 2, 2, 3))])
    return {"name": name, "top": list(top), "bot": list(bot), "neb": blobs, "rocks": rocks,
            "planet": [kind, px, rnd.randint(40, 120), rnd.randint(14, 26), list(pc1), list(pc2)]}


# planet kinds: 0 none, 1 cratered moon, 2 ringed, 3 striped giant, 4 twin moons, 5 glowing sun, 6 asteroid belt
THEMES = [
    _theme("MILKY BAY", (22, 14, 46), (44, 28, 78), [(180, 156, 255), (124, 200, 255)], (1, (255, 233, 199), (200, 180, 160)), 1),
    _theme("CANDY NEBULA", (34, 12, 42), (78, 24, 70), [(255, 79, 139), (255, 179, 138)], (3, (255, 143, 183), (255, 247, 240)), 2),
    _theme("MINT DRIFT", (8, 30, 40), (18, 60, 66), [(110, 231, 183), (55, 200, 192)], (2, (55, 200, 192), (184, 240, 106)), 3),
    _theme("PEACH BELT", (40, 18, 28), (88, 40, 42), [(255, 138, 61), (255, 179, 138)], (6, (160, 98, 62), (255, 179, 138)), 4),
    _theme("LEMON GLOW", (34, 26, 18), (70, 52, 30), [(255, 216, 77), (255, 138, 61)], (5, (255, 216, 77), (255, 247, 240)), 5),
    _theme("BERRY VOID", (18, 8, 38), (48, 20, 72), [(138, 92, 246), (77, 124, 255)], (4, (180, 156, 255), (138, 92, 246)), 6),
    _theme("SODA SKY", (8, 22, 54), (20, 58, 108), [(124, 200, 255), (255, 247, 240)], (2, (124, 200, 255), (255, 247, 240)), 7),
    _theme("COCOA COMETS", (28, 14, 10), (60, 34, 26), [(160, 98, 62), (255, 179, 138)], (1, (160, 98, 62), (110, 64, 44)), 8),
    _theme("AURORA ROAD", (6, 20, 28), (10, 42, 50), [(184, 240, 106), (55, 200, 192), (138, 92, 246)], (0, (0, 0, 0), (0, 0, 0)), 9),
    _theme("SAKURA ORBIT", (38, 16, 38), (70, 30, 60), [(255, 143, 183), (255, 247, 240)], (2, (255, 143, 183), (255, 233, 199)), 10),
    _theme("TWILIGHT TEA", (22, 18, 46), (62, 40, 80), [(180, 156, 255), (255, 138, 61)], (3, (255, 138, 61), (180, 156, 255)), 11),
    _theme("MELON MOONS", (8, 28, 18), (24, 58, 36), [(184, 240, 106), (110, 231, 183)], (4, (184, 240, 106), (255, 233, 199)), 12),
    _theme("PLUM STORM", (28, 6, 28), (60, 14, 50), [(255, 79, 139), (138, 92, 246)], (6, (139, 134, 168), (255, 79, 139)), 13),
    _theme("GLACIER GLOW", (10, 24, 46), (38, 66, 98), [(255, 247, 240), (124, 200, 255)], (1, (255, 247, 240), (124, 200, 255)), 14),
    _theme("EMBER RINGS", (38, 8, 8), (78, 20, 16), [(255, 77, 90), (255, 138, 61)], (2, (255, 77, 90), (255, 216, 77)), 15),
    _theme("HONEY HALO", (38, 28, 8), (78, 58, 20), [(255, 216, 77), (255, 233, 199)], (5, (255, 138, 61), (255, 216, 77)), 16),
    _theme("NEON NOODLE", (8, 8, 30), (30, 10, 60), [(255, 79, 139), (184, 240, 106), (124, 200, 255)], (3, (110, 231, 183), (255, 79, 139)), 17),
    _theme("DREAM DUST", (28, 22, 40), (58, 48, 78), [(255, 233, 199), (180, 156, 255)], (4, (255, 233, 199), (255, 143, 183)), 18),
    _theme("STARLIGHT SEA", (6, 10, 30), (14, 30, 70), [(77, 124, 255), (124, 200, 255), (255, 247, 240)], (2, (77, 124, 255), (255, 247, 240)), 19),
    _theme("THE LAST LIGHT", (8, 4, 16), (30, 10, 40), [(255, 216, 77), (255, 247, 240), (138, 92, 246)], (5, (255, 247, 240), (255, 216, 77)), 20),
]

# ----------------------------------------------------------------------------- bosses
# Attacks: fan aim ring spiral laser rain summon mines charge wall teleport
ATTACKS = ("fan", "aim", "ring", "spiral", "laser", "rain", "summon", "mines", "charge", "wall", "teleport")
# box: body hit box (w, h) around the centre. weak: (dx, dy, r) weak spot on the lower edge (double damage).
# parts: (dx, dy, r, share of the boss hp) - breakable tentacles / claws / moons.
BOSSES = [
    {"name": "MOCHI MOON", "hp": 230, "box": [44, 34],
     "phases": [["fan", "summon", "aim"], ["ring", "fan", "summon", "aim"], ["ring", "spiral", "fan", "summon"]],
     "mix": ["rain", "wall", "laser"], "parts": [], "weak": [0, 12, 8],
     "intro": "A GIANT RICE-CAKE MOON"},
    {"name": "STAR SQUID", "hp": 210, "box": [32, 28],
     "phases": [["aim", "fan", "laser"], ["spiral", "aim", "laser"], ["spiral", "laser", "aim", "ring"]],
     "mix": ["summon", "rain", "wall"], "parts": [[-24, 18, 6, 0.1], [-9, 23, 6, 0.1], [9, 23, 6, 0.1], [24, 18, 6, 0.1]],
     "weak": [0, 8, 8], "intro": "BREAK ITS TENTACLES!"},
    {"name": "COMET WHALE", "hp": 260, "box": [60, 24],
     "phases": [["rain", "charge", "fan"], ["wall", "rain", "charge", "aim"], ["rain", "wall", "charge", "spiral"]],
     "mix": ["ring", "summon", "laser"], "parts": [], "weak": [-14, 8, 7], "intro": "WATCH OUT FOR ITS DASH!"},
    {"name": "NEBULA CRAB", "hp": 240, "box": [40, 24],
     "phases": [["laser", "fan", "mines"], ["laser", "mines", "aim", "fan"], ["laser", "wall", "mines", "ring"]],
     "mix": ["spiral", "summon", "rain"], "parts": [[-32, 8, 9, 0.14], [32, 8, 9, 0.14]], "weak": [0, 9, 7],
     "intro": "ITS CLAWS FIRE LASERS"},
    {"name": "RING GRUMP", "hp": 250, "box": [34, 34],
     "phases": [["ring", "wall", "aim"], ["ring", "spiral", "wall"], ["spiral", "ring", "wall", "fan"]],
     "mix": ["mines", "laser", "summon"], "parts": [[0, 0, 7, 0.07], [0, 0, 7, 0.07], [0, 0, 7, 0.07]],
     "weak": [0, 12, 8], "intro": "ITS MOONS BLOCK YOUR STARS"},
    {"name": "VOID PUFF", "hp": 240, "box": [44, 32],
     "phases": [["teleport", "summon", "fan", "ring"], ["teleport", "spiral", "laser", "summon"],
                ["teleport", "spiral", "rain", "laser", "ring"]],
     "mix": ["mines", "wall", "aim", "charge"], "parts": [], "weak": [0, 11, 9], "intro": "NOW YOU SEE IT..."},
]
# RING GRUMP's moons orbit the planet: their position is computed at runtime from the orbit angle.


def boss_phases(b, lv, final):
    """Attack rotation per phase: later visits mix in other bosses' attacks (one more per level)."""
    spec = BOSSES[b]
    out = []
    for i, ph in enumerate(spec["phases"]):
        names = list(ph)
        for m in spec["mix"][:lv]:
            if i >= 1 or lv >= 2:
                names.append(m)
        if final:
            names = list(ph) + [a for a in ("laser", "wall", "rain", "mines", "summon", "spiral", "ring") if a not in ph]
        out.append(names)
    return out


def boss_entry(n):
    """Which boss (and how fierce) guards stage n (n % 10 == 0)."""
    k = n // 10 - 1                     # 0..19
    if n >= STAGES:
        return 5, 3, True               # the finale: VOID PUFF with everything
    return k % 6, k // 6, False


# ----------------------------------------------------------------------------- stage builder
MODS = ("SPEEDY", "TRIGGER HAPPY", "ARMORED", "SWARM", "METEORS")
MOD_UNLOCK = {"SPEEDY": 2, "TRIGGER HAPPY": 3, "SWARM": 4, "ARMORED": 5, "METEORS": 6}
CAPSULES = ("P", "F", "B", "S", "$")


def _new_kind(t):
    for k, row in enumerate(KINDS):
        if row[4] == t:
            return k
    return -1


def _normal(n, rnd, recent):
    t = tier(n)
    k = (n - 1) % 10
    mods = []
    if t >= 2:
        avail = [m for m in MODS if MOD_UNLOCK[m] <= t]
        nm = 0 if rnd.random() < max(0.2, 0.6 - 0.03 * t) else (1 if rnd.random() < 0.7 or t < 8 else 2)
        rnd.shuffle(avail)
        mods = sorted(avail[:nm], key=MODS.index)
    target = 22 + t + (k % 3) + (6 if "SWARM" in mods else 0)
    # templates of a fitting size, not one of the last few stages' shapes
    names = [nm for nm, (u, _) in TEMPLATES.items() if u <= t]
    sized = [nm for nm in names if target - 2 <= len(template_cells(nm)) <= target + 14] or names
    fresh = [nm for nm in sized if nm not in recent[-3:]] or [nm for nm in sized if nm not in recent[-1:]] or sized
    # prefer a shape introduced in this tier for its first stage
    newest = [nm for nm in fresh if TEMPLATES[nm][0] == t]
    tpl = newest[0] if newest and k == 0 else fresh[rnd.randrange(len(fresh))]
    recent.append(tpl)
    cells = template_cells(tpl)
    # thin out symmetric pairs (basic ones first) down to the target count
    while len(cells) > target:
        pool = [c for c in cells if c[2] == "B"] or [c for c in cells if c[2] == "A"] or cells
        c, r, _ = rnd.choice(pool)
        cells = [x for x in cells if not (x[1] == r and abs(x[0]) == abs(c))]
    # roster: one kind per (row, role); a newly unlocked kind gets the spotlight in its first stage
    new = _new_kind(t) if k == 0 and t >= 1 else -1
    choice = {}
    rows = sorted({(r, role) for _, r, role in cells})
    for r, role in rows:
        cands = [kd for kd in ROLE_KINDS[role] if KINDS[kd][4] <= t]
        weights = [1.0 + (2.5 if KINDS[kd][4] == t else 0.0) + (0.6 if KINDS[kd][4] >= t - 2 else 0.0) for kd in cands]
        choice[(r, role)] = rnd.choices(cands, weights)[0]
    if new >= 0:
        fits = [(r, role) for r, role in rows if new in ROLE_KINDS[role]]
        for key in rnd.sample(fits, min(2, len(fits))):
            choice[key] = new
    checker = t >= 3 and rnd.random() < 0.3
    slots = []
    for c, r, role in sorted(cells, key=lambda x: (x[1], x[0])):
        kd = choice[(r, role)]
        if checker and abs(c) % 2 == 1:
            alts = [x for x in ROLE_KINDS[role] if KINDS[x][4] <= t and x != kd]
            if alts:
                kd = alts[(r + n) % len(alts)]
        slots.append([c, r, kd])
    # squads: slots are grouped bottom rows last; each squad flies one entry path
    paths = [p for p in ENTRY if ENTRY_UNLOCK[p] <= t]
    order = sorted(range(len(slots)), key=lambda i: (slots[i][1], abs(slots[i][0]), slots[i][0]))
    size = 8 if len(slots) > 30 else 6
    groups = [order[i:i + size] for i in range(0, len(order), size)]
    speed = min(190, 108 + 4 * t) * (1.2 if "SPEEDY" in mods else 1.0)
    gap = max(0.9, 1.9 - 0.045 * t)
    member_gap = round(max(0.1, 18.0 / speed), 3)
    out_slots = [None] * len(slots)
    last_path = None
    for g, members in enumerate(groups):
        choices = [p for p in paths if p != last_path]
        pname = choices[rnd.randrange(len(choices))]
        last_path = pname
        style = rnd.random()
        for j, si in enumerate(sorted(members, key=lambda i: (slots[i][0], slots[i][1]))):
            if style < 0.3 and t >= 1:      # pincer: the squad splits and enters from both sides
                mirror = j % 2
                delay = 0.9 + g * gap + (j // 2) * member_gap
            else:
                mirror = g % 2
                delay = 0.9 + g * gap + j * member_gap
            c, r, kd = slots[si]
            out_slots[si] = [c, r, kd, path_index(pname), mirror, round(delay, 3), g, -1]
    # capsule carriers
    ncap = 1 + (1 if t >= 2 else 0) + (1 if t >= 8 else 0)
    for si in rnd.sample(range(len(out_slots)), min(ncap, len(out_slots))):
        out_slots[si][7] = CAPSULES.index(rnd.choices(CAPSULES, (3, 2, 2, 2, 1))[0])
    return {
        "n": n, "type": "normal", "theme": t, "tpl": tpl, "slots": out_slots, "groups": len(groups), "mods": mods,
        "new": new, "speed": round(speed, 1), "dive_gap": round(max(0.55, 2.5 - 0.09 * t - 0.03 * k), 3),
        "dive_max": min(6, 2 + t // 3 + (1 if k >= 6 else 0)), "shots": 1 + (1 if t >= 6 else 0) + (1 if t >= 13 else 0),
        "efire": round(min(0.6, 0.08 + 0.03 * t + 0.01 * k) * (1.4 if "TRIGGER HAPPY" in mods else 1.0), 3),
        "burst": 1 + (1 if t >= 10 else 0) + (1 if t >= 15 else 0),
        "amb": round(min(0.5, 0.035 * t), 3), "volley": round(max(2.2, 6.5 - 0.22 * t), 2) if t >= 4 else 0,
        "bv": round(min(140, 72 + 3.2 * t) * (1.1 if "TRIGGER HAPPY" in mods else 1.0), 1),
        "fire_gap": round(max(1.3, 3.6 - 0.11 * t) * (0.7 if "TRIGGER HAPPY" in mods else 1.0), 2),
        "hpb": t // 4 + (1 if "ARMORED" in mods else 0), "hpj": t // 6, "par": round(30 + len(slots) * 0.6 + len(groups) * gap),
    }


def _bonus(n, rnd):
    t = tier(n)
    names = list(PARADE)
    rnd.shuffle(names)
    waves = []
    nw = 5 + min(3, t // 5)
    gold_wave = rnd.randrange(nw)
    kinds = [kd for kd in (JELLY, MOTH, PUFF, DART, SPORE, BLOB, SHELL, COMET, URCHIN, WISP) if KINDS[kd][4] <= t]
    gap = max(1.7, 2.7 - 0.05 * t)
    for i in range(nw):
        kd = kinds[(i + n) % len(kinds)]
        gold = rnd.randrange(8) if i == gold_wave else -1
        waves.append([path_index(names[i % len(names)]), i % 2, round(1.8 + i * gap, 3), 8, gold, kd])
    return {"n": n, "type": "bonus", "theme": t, "waves": waves, "speed": round(min(200, 120 + 4 * t), 1),
            "par": round(4 + nw * gap + 4)}


def _boss(n):
    t = tier(n)
    b, lv, final = boss_entry(n)
    base = BOSSES[b]["hp"]
    name = "ABYSS PUFF" if final else BOSSES[b]["name"]
    return {"n": n, "type": "boss", "theme": t, "boss": b, "lv": lv, "final": final, "name": name,
            "phases": boss_phases(b, lv, final), "nphase": 2 if lv == 0 else 3,
            "hp": int(base * (1 + 0.45 * t) * (1.35 if final else 1.0)), "bv": round(min(118, 62 + 2.6 * t), 1),
            "rest": round(max(0.45, 1.3 - 0.045 * t), 3), "par": 60 + 4 * lv}


def build_stage(n, recent):
    rnd = random.Random(7919 * n + 13)
    if is_boss(n):
        return _boss(n)
    if is_bonus(n):
        return _bonus(n, rnd)
    return _normal(n, rnd, recent)


def build_all():
    recent = []
    return [build_stage(n, recent) for n in range(1, STAGES + 1)]


STAGE_TABLE = build_all()


def stage(n):
    return STAGE_TABLE[max(1, min(STAGES, n)) - 1]


EXPORT = {
    "stages": STAGE_TABLE,
    "paths": PATHS,
    "path_names": PATH_NAMES,
    "themes": THEMES,
    "bosses": BOSSES,
    "kinds": [[k[0], k[1], k[2], k[3], k[4], k[5]] for k in KINDS],
    "mods": list(MODS),
    "capsules": list(CAPSULES),
    "consts": {"step": STEP, "col_dx": COL_DX, "row_dy": ROW_DY, "row_y0": ROW_Y0},
}
