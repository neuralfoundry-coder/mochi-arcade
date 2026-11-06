"""PAW PINBALL tables and the 200-stage mission campaign (generated here, exported to iOS as JSON).

Every table shares the same lower shell (walls, slingshots, inlanes, outlanes, Kiki's paw flippers and the
plunger lane on the right); the upper playfield comes from one of six layout templates, optionally mirrored,
with a theme per tier. Geometry is fully built in Python and exported, so both platforms collide against
exactly the same segments and circles.
"""
import math
import random

from mochi_arcade.arcade import STAGES, is_boss, is_bonus

# ----------------------------------------------------------------------------- shared shell
BALL_R = 3.0
TX0, TX1 = 68, 252            # table frame (the side panels sit outside)
LW, RW = 72.0, 238.0          # playfield walls; RW is also the plunger lane's inner wall
LANE_X = 243.0                # ball centre in the plunger lane
LANE_OUT = 248.0              # plunger lane outer wall
CX = 155.0                    # flipper centre line
MIRROR = 2 * CX               # x' = MIRROR - x
ARCH = (160.0, 62.0, 88.0, 56.0)   # top arch ellipse: cx, cy, rx, ry
PLUNGE_Y = 189.0              # plunger tip (ball rests at PLUNGE_Y - BALL_R)
GATE_Y = 74.0                 # top of the plunger lane's inner wall
FLIP_Y = 169.0
FLIP_X = (128.0, 182.0)       # left / right pivot
LANE_XS = (125.0, 143.0, 161.0, 179.0)   # M E O W rollover lanes
LANE_Y = 33.0

# inlane guide: tangent to the paw's pivot so the ball rolls smoothly onto the paw (and cradles when it's up)
_GA = math.atan(0.494)
GUIDE_END = (round(FLIP_X[0] + 3.6 * math.sin(_GA), 2), round(FLIP_Y - 3.6 * math.cos(_GA), 2))
GUIDE = ((84.0, round(GUIDE_END[1] - (GUIDE_END[0] - 84.0) * math.tan(_GA), 2)), GUIDE_END)
SLING_PTS = ((98.0, 117.0), (98.0, 137.0), (117.0, 148.0))   # back top, back bottom, kicker bottom

# wall kinds
METAL, RUBBER, SLING, GATE = 0, 1, 2, 3


def arch_y(x):
    cx, cy, rx, ry = ARCH
    u = max(-1.0, min(1.0, (x - cx) / rx))
    return cy - ry * math.sqrt(1 - u * u)


def _r(v):
    return round(v, 2)


# cat-tower block corners (top-left): wall foot, lower ledge, mouth bottom, mouth top, top (past the arch)
TOWER = ((72.0, 108.0), (88.0, 104.0), (95.0, 100.0), (99.0, 62.0), (99.0, 19.0))


def shell(tower_mouth=False):
    """walls [x1, y1, x2, y2, kind], posts [x, y, r] shared by every table. The cat tower always stands in the
    top-left corner (it stops long plunges from looping into the left outlane); with a tower ramp its face has
    the ramp mouth instead of a rubber."""
    walls, posts = [], []

    def w(x1, y1, x2, y2, k=METAL):
        walls.append([_r(x1), _r(y1), _r(x2), _r(y2), k])

    # top arch from the left wall over to the plunger lane's outer wall
    cx, cy, rx, ry = ARCH
    n = 30
    pts = [(cx + rx * math.cos(math.pi + math.pi * i / n), cy + ry * math.sin(math.pi + math.pi * i / n))
           for i in range(n + 1)]
    for a, b in zip(pts, pts[1:]):
        w(a[0], a[1], b[0], b[1])
    # the cat tower block (its right face is the tower ramp's mouth when the table has one)
    (b0x, b0y), (b1x, b1y), (b2x, b2y), (b3x, b3y), (b4x, b4y) = TOWER
    w(b0x, b0y, b1x, b1y)
    w(b1x, b1y, b2x, b2y, RUBBER)
    if not tower_mouth:
        w(b2x, b2y, b3x, b3y, RUBBER)
    w(b3x, b3y, b4x, b4y, RUBBER)
    posts.append([b1x, b1y, 2.0])
    posts.append([b2x, b2y, 2.5])
    posts.append([b3x, b3y, 2.5])
    # outer walls
    w(LW, cy, LW, 204)
    w(LANE_OUT, cy, LANE_OUT, 204)
    # plunger lane inner wall (= right playfield wall), plunger tip, one-way gate over the lane
    w(RW, GATE_Y, RW, 204)
    w(RW, PLUNGE_Y, LANE_OUT, PLUNGE_Y)
    w(LANE_OUT, GATE_Y - 9, RW, GATE_Y, GATE)
    posts.append([RW, GATE_Y, 1.5])
    for side in (1, -1):
        def X(x):
            return x if side == 1 else MIRROR - x
        # outlane / inlane separator + inlane guide down to the flipper pivot, apron wall below
        w(X(84), 124, X(84), 204)
        (gx1, gy1), (gx2, gy2) = GUIDE
        w(X(gx1), gy1, X(gx2), gy2)
        posts.append([_r(X(84)), 124, 2.5])
        # slingshot: rubber back, kicker face towards the middle
        (ax, ay), (bx, by), (qx, qy) = SLING_PTS
        ax, bx, qx = X(ax), X(bx), X(qx)
        w(ax, ay, bx, by, RUBBER)
        w(bx, by, qx, qy, RUBBER)
        w(ax, ay, qx, qy, SLING)
        for px, py in ((ax, ay), (bx, by), (qx, qy)):
            posts.append([_r(px), py, 2.5])
    # rollover lane separators (short walls with round tops)
    for x in (116, 134, 152, 170, 188):
        w(x, 26, x, 38)
        posts.append([x, 26, 2.0])
    return walls, posts


# ----------------------------------------------------------------------------- upper playfield parts
def fish_bank(cx, y, n, vertical=False, face=1):
    """Drop targets: [x1, y1, x2, y2] capsules (radius 2). Horizontal banks face down; vertical banks face
    right (face=1) or left (face=-1)."""
    out = []
    for i in range(n):
        o = (i - (n - 1) / 2) * 12
        if vertical:
            out.append([cx, _r(y + o - 4), cx, _r(y + o + 4), face])
        else:
            out.append([_r(cx + o - 4), y, _r(cx + o + 4), y, 0])
    return out


def tower_ramp():
    """Left cat-tower ramp: a cross shot from the right paw enters the tower's face, climbs it and drops the ball
    into the M lane."""
    (b2x, b2y), (b3x, b3y) = TOWER[2], TOWER[3]
    gate = [b2x, b2y, b3x, b3y]
    d = (-0.993, -0.106)
    path = [[95, 78], [89, 70], [85, 58], [86, 46], [90, 36], [98, 28], [108, 22], [119, 19]]
    return {"kind": "tower", "gate": gate, "dir": list(d), "path": path, "out": [40.0, 30.0]}


def slide_ramp():
    """Right fish slide: a cross shot from the left paw, loops over the right side, returns to the right inlane."""
    gate = [204.3, 77.2, 221.7, 90.8]
    d = (0.62, -0.79)
    path = [[214, 82], [219, 73], [225, 64], [231, 62], [234, 70], [234, 84], [232, 98], [228, 110], [223, 118],
            [219, 123]]
    return {"kind": "slide", "gate": gate, "dir": list(d), "path": path, "out": [0.0, 90.0]}


def ramp_walls(r):
    """Little guide posts either side of a ramp mouth (the tower's are part of the shell)."""
    if r["kind"] == "tower":
        return []
    x1, y1, x2, y2 = r["gate"]
    return [[x1, y1, 2.5], [x2, y2, 2.5]]


def mirror_ramp(r):
    x1, y1, x2, y2 = r["gate"]
    return {"kind": r["kind"], "gate": [_r(MIRROR - x2), y2, _r(MIRROR - x1), y1], "dir": [-r["dir"][0], r["dir"][1]],
            "path": [[_r(MIRROR - x), y] for x, y in r["path"]], "out": [-r["out"][0], r["out"][1]]}


# Wall banks: on the tower's face (left) or against the right wall, facing the middle.
WALL_BANKS = {"L": (102.0, 66.0, 1), "R": (233.0, 96.0, -1)}

# Templates: bumpers [x, y], fish banks (cx, y, n, vertical, face) or "L"/"R" wall banks of 3, saucer, ramps,
# spinner (centre x, y, half width), extra posts.
TEMPLATES = {
    "cafe": {"bumpers": [[138, 58], [172, 58], [155, 80]], "fish": [(155, 108, 3, False, 0)], "saucer": [212, 98],
             "ramps": ["tower"], "spinner": None, "posts": []},
    "yarn": {"bumpers": [[130, 62], [180, 62]], "fish": ["L"], "saucer": [155, 104],
             "ramps": ["slide"], "spinner": [155, 64, 9], "posts": [[155, 84, 2.5]]},
    "window": {"bumpers": [[126, 58], [155, 72], [184, 58]], "fish": [(155, 106, 4, False, 0)], "saucer": None,
               "ramps": ["tower", "slide"], "spinner": None, "posts": []},
    "market": {"bumpers": [[155, 52], [134, 70], [176, 70], [155, 88]], "fish": ["L"],
               "saucer": [155, 116], "ramps": ["slide"], "spinner": [186, 96, 8], "posts": []},
    "fort": {"bumpers": [[124, 64], [186, 64]], "fish": [(155, 92, 3, False, 0), "R"],
             "saucer": [155, 64], "ramps": ["tower"], "spinner": [116, 110, 9], "posts": [[186, 96, 2.5]]},
    "roof": {"bumpers": [[140, 58], [170, 58], [126, 88], [184, 88]], "fish": [(155, 112, 3, False, 0)],
             "saucer": [155, 84], "ramps": ["tower", "slide"], "spinner": None, "posts": []},
    # boss arena: the boss owns the top middle; two side bumpers, one fish bank, both ramps
    "arena": {"bumpers": [[126, 96], [184, 96]], "fish": [(155, 114, 3, False, 0)], "saucer": None,
              "ramps": ["tower", "slide"], "spinner": None, "posts": []},
}

# 20 tables, one per tier: (name, template, mirrored, theme)
# theme: playfield a/b, pattern 0-4, wall colour, accent, bumper colour, deco 0-5
THEMES = [
    ("KIKI'S CAFE", "cafe", False, ("choco", "brown", 0, "cream", "peach", "orange", 0)),
    ("YARN BASKET", "yarn", False, ("deep", "purple", 1, "pink", "hotpink", "pink", 1)),
    ("SUNNY WINDOW", "window", False, ("blue", "sky", 2, "white", "yellow", "yellow", 2)),
    ("FISH MARKET", "market", False, ("teal", "blue", 3, "mint", "sky", "mint", 3)),
    ("CARDBOARD FORT", "fort", False, ("brown", "choco", 4, "peach", "yellow", "peach", 4)),
    ("MOONLIT ROOF", "roof", False, ("night", "ink", 2, "lavender", "yellow", "lavender", 5)),
    ("CATNIP GARDEN", "cafe", True, ("teal", "mint", 1, "lime", "lime", "lime", 1)),
    ("BUBBLE BATH", "yarn", True, ("blue", "sky", 2, "white", "sky", "sky", 2)),
    ("TOY BOX", "window", True, ("purple", "deep", 0, "yellow", "orange", "orange", 4)),
    ("BOOK NOOK", "market", True, ("choco", "brown", 3, "peach", "cream", "peach", 0)),
    ("SUSHI BAR", "fort", True, ("ink", "deep", 4, "red", "pink", "red", 3)),
    ("CAT SHOW", "roof", True, ("purple", "hotpink", 1, "yellow", "yellow", "pink", 5)),
    ("SNOW DAY", "window", False, ("sky", "white", 2, "blue", "lavender", "sky", 2)),
    ("CANDY SHOP", "cafe", False, ("hotpink", "pink", 0, "white", "yellow", "mint", 1)),
    ("CIRCUS TENT", "roof", False, ("red", "hotpink", 1, "yellow", "yellow", "yellow", 4)),
    ("SPACE STATION", "market", False, ("night", "deep", 3, "sky", "mint", "sky", 5)),
    ("DESERT TEMPLE", "fort", False, ("orange", "peach", 4, "brown", "yellow", "orange", 0)),
    ("HAUNTED ATTIC", "yarn", False, ("ink", "night", 3, "gray", "lime", "lavender", 5)),
    ("CLOUD PALACE", "window", True, ("lavender", "sky", 2, "white", "pink", "pink", 2)),
    ("KIKI'S DREAM", "roof", False, ("night", "purple", 1, "pink", "yellow", "hotpink", 1)),
]


def _overlaps(x, y, things, d):
    return any((x - a) ** 2 + (y - b) ** 2 < d * d for a, b in things)


def build_table(tier, arena=False):
    name, tpl_name, mirrored, theme = THEMES[tier]
    tpl = TEMPLATES["arena" if arena else tpl_name]
    walls, posts = shell("tower" in tpl["ramps"])

    def X(x):
        return _r(MIRROR - x) if mirrored else x

    bumpers = [[X(x), y] for x, y in tpl["bumpers"]]
    fish = []
    for bank, spec in enumerate(tpl["fish"]):
        if isinstance(spec, str):       # wall bank: mirroring moves it to the other wall
            side = spec if not mirrored else ("R" if spec == "L" else "L")
            cx, cy, face = WALL_BANKS[side]
            fish += [f[:5] + [bank] for f in fish_bank(cx, cy, 3, True, face)]
            continue
        cx, y, n, vertical, face = spec
        for f in fish_bank(cx, y, n, vertical, face):
            x1, y1, x2, y2, fc = f
            if mirrored:
                x1, x2 = MIRROR - x2, MIRROR - x1
                fc = -fc
            fish.append([_r(x1), y1, _r(x2), y2, fc, bank])
    saucer = [X(tpl["saucer"][0]), tpl["saucer"][1]] if tpl["saucer"] else []
    # ramps stay put when a table is mirrored: the tower lives in the corner, the slide beside the plunger
    ramps = [tower_ramp() if k == "tower" else slide_ramp() for k in tpl["ramps"]]
    for r in ramps:
        posts.extend(ramp_walls(r))
    spinner = []
    if tpl["spinner"]:
        sx, sy, hw = tpl["spinner"]
        spinner = [_r(X(sx) - hw), sy, _r(X(sx) + hw), sy]
    for x, y, r in tpl["posts"]:
        posts.append([X(x), y, r])
    # kitten rescue spots: open places spread over the playfield (deterministic)
    things = [(b[0], b[1]) for b in bumpers] + [((f[0] + f[2]) / 2, (f[1] + f[3]) / 2) for f in fish]
    things += [(p[0], p[1]) for p in posts]
    if saucer:
        things.append(tuple(saucer))
    for r in ramps:
        things += [(r["gate"][0], r["gate"][1]), (r["gate"][2], r["gate"][3])]
    if spinner:
        things.append(((spinner[0] + spinner[2]) / 2, spinner[1]))
    rnd = random.Random(1000 + tier * 7 + (500 if arena else 0))
    spots = []
    cands = [(x, y) for y in range(46, 128, 6) for x in range(96, 216, 6)]
    rnd.shuffle(cands)
    lo = 70 if arena else 44
    for x, y in cands:
        if y < lo or _overlaps(x, y, things, 17) or _overlaps(x, y, spots, 26):
            continue
        if 116 < y and (x < 106 or x > 204):      # keep clear of the slingshots
            continue
        if x < 110 and y < 112:                    # the cat tower
            continue
        spots.append((x, y))
        if len(spots) >= 6:
            break
    a, b, pat, wall, accent, bump, deco = theme
    return {"name": "BOSS ARENA" if arena else name, "tier": tier, "arena": arena, "mirror": mirrored,
            "theme": {"a": a, "b": b, "pat": pat, "wall": wall, "accent": accent, "bump": bump, "deco": deco},
            "walls": walls, "posts": posts, "bumpers": bumpers, "fish": fish, "saucer": saucer, "ramps": ramps,
            "spinner": spinner, "spots": [[x, y] for x, y in spots], "lanes": [[x, LANE_Y] for x in LANE_XS]}


TABLES = [build_table(t) for t in range(20)]
ARENA = build_table(0, arena=True)      # boss stages: one arena, painted in the tier's colours

# ----------------------------------------------------------------------------- missions
# goal type -> (HUD word, intro text with {n}, seconds a decent player needs per unit)
GOALS = {
    "bump": ("BUMPS", "BOP THE CAT BUMPERS {n} TIMES", 1.2),
    "fish": ("FISH", "KNOCK DOWN {n} FISH TARGETS", 3.5),
    "meow": ("MEOW", "SPELL M-E-O-W {n} TIMES", 22.0),
    "ramp": ("RAMPS", "MAKE {n} RAMP SHOTS", 9.0),
    "nap": ("NAPS", "SINK {n} BALLS IN THE NAP BED", 12.0),
    "rescue": ("KITTENS", "RESCUE {n} KITTENS", 7.0),
    "spin": ("SPINS", "SPIN THE YARN {n} TIMES", 0.6),
    "combo": ("COMBOS", "CHAIN {n} RAMP COMBOS", 18.0),
    "multi": ("PARTY", "START A KITTEN MULTIBALL", 60.0),
    "score": ("POINTS", "SCORE {n} POINTS", 0.0025),
    "hits": ("HITS", "HIT {n} SWITCHES", 0.45),
}

# what each tier brings in (new goal types) - shown on the stage card the first time
INTRO = {0: ["bump", "meow", "fish", "score"], 1: ["ramp", "nap"], 2: ["rescue"], 3: ["spin", "hits"], 4: ["combo"],
         5: ["multi"]}
NEW_TEXT = {"ramp": "NEW: RAMP SHOTS!", "nap": "NEW: THE NAP BED!", "rescue": "NEW: KITTEN RESCUE!",
            "spin": "NEW: YARN SPINNER!", "hits": "NEW: TIMED FRENZY!", "combo": "NEW: RAMP COMBOS!",
            "multi": "NEW: KITTEN MULTIBALL!"}

NAMES = {
    "bump": ["BOP BOP BOP", "WHISKER WAKE-UP", "HEADBUTT PARTY", "BUMPER PURRS", "BOOP THE SNOOTS", "CAT NAP RIOT"],
    "fish": ["FISH FRY", "CATCH OF THE DAY", "TUNA TUMBLE", "SARDINE SWEEP", "FISHY BUSINESS", "SALMON SLAM"],
    "meow": ["SAY MEOW", "MEOW MIX", "LOUD AND PROUD", "CHATTY CAT", "MEOW MEOW MEOW", "THE BIG YOWL"],
    "ramp": ["CLIMB THE TOWER", "UP UP UP", "SLIDE TIME", "HIGH PERCH", "TOWER RUN", "SKY SCRATCHER"],
    "nap": ["NAP TIME", "SLEEPY HEAD", "CUSHION CRASH", "DOZE OFF", "SNOOZE BUTTON", "CAT BED CATCH"],
    "rescue": ["KITTEN RESCUE", "LOST KITTENS", "WHERE'S MITTENS", "HOME SAFE", "TINY PAWS", "LITTER ROUNDUP"],
    "spin": ["YARN SPIN", "TANGLE TWIST", "SPOOL RUSH", "DIZZY KITTY", "WOOL WHIRL", "KNIT PICKER"],
    "combo": ["COMBO CAT", "ZOOMIES", "PARKOUR", "CHAIN CHASE", "ACROBAT", "TOP SPEED"],
    "multi": ["KITTEN PARTY", "PILE OF KITTENS", "FURBALL FIESTA", "LITTER PARTY", "KITTEN STAMPEDE"],
    "score": ["WARM UP", "HIGH SCORE HUNT", "CAFE RUSH", "BIG SPENDER", "TIP JAR", "GOLDEN BOWL"],
    "hits": ["FRENZY", "FLURRY", "PAW STORM", "SCRAMBLE", "WILD HOUR", "CRAZY HOUR"],
}

BONUS_KINDS = ("party", "fountain")
BONUS_NAMES = {"party": ["KITTEN PARTY", "CATNIP RAVE", "BALL BONANZA", "PURR PARTY"],
               "fountain": ["FISH FOUNTAIN", "GOLD RUSH", "TREAT RAIN", "COIN CASCADE"]}

BOSSES = ["buster", "robovac", "caw", "cuke", "spritz"]
BOSS_NAMES = {"buster": "BUSTER", "robovac": "ROBO-VAC", "caw": "CAW", "cuke": "CUKE", "spritz": "SPRITZ"}
BOSS_TITLES = {"buster": "THE BULLY DOG", "robovac": "THE DUST DEVOURER", "caw": "THE SHINY THIEF",
               "cuke": "THE SPOOKY CUCUMBER", "spritz": "THE SPRAY BOTTLE"}


def table_supports(tb, goal):
    if goal in ("bump",):
        return len(tb["bumpers"]) > 0
    if goal == "fish":
        return len(tb["fish"]) > 0
    if goal in ("ramp", "combo"):
        return len(tb["ramps"]) > 0
    if goal == "nap":
        return bool(tb["saucer"])
    if goal == "multi":
        return bool(tb["saucer"]) and len(tb["fish"]) > 0
    if goal == "rescue":
        return len(tb["spots"]) >= 3
    if goal == "spin":
        return bool(tb["spinner"])
    return True


def goal_count(goal, tier, rnd):
    t = tier
    if goal == "bump":
        return 8 + 2 * t + rnd.randint(0, 4)
    if goal == "fish":
        return 3 + t // 2 + rnd.randint(0, 2)
    if goal == "meow":
        return 1 + t // 5
    if goal == "ramp":
        return 2 + t // 3 + rnd.randint(0, 1)
    if goal == "nap":
        return 2 + t // 4
    if goal == "rescue":
        return 3 + t // 3
    if goal == "spin":
        return 12 + 3 * t + rnd.randint(0, 6)
    if goal == "combo":
        return 1 + t // 5
    if goal == "multi":
        return 1
    if goal == "score":
        return (15 + 6 * t + rnd.randint(0, 5)) * 1000
    if goal == "hits":
        return 25 + 3 * t + rnd.randint(0, 6)
    return 1


def build_campaign():
    rnd = random.Random(20261106)
    camp = []
    unlocked = []
    bag = []
    recent = []
    for n in range(1, STAGES + 1):
        tier = (n - 1) // 10
        k = (n - 1) % 10
        grav = round(1.0 + 0.012 * tier, 3)
        save = max(5, 9 - tier // 4)
        for g in INTRO.get(tier, []):
            if g not in unlocked:
                unlocked.append(g)
        if is_boss(n):
            rnd_b = n // 10 - 1
            kind = BOSSES[rnd_b % len(BOSSES)]
            rd = rnd_b // len(BOSSES)                     # 0..3: the same boss returns stronger
            extra = []
            if rd >= 1:
                extra.append(BOSSES[(rnd_b + 2) % len(BOSSES)])
            if rd >= 3:
                extra.append(BOSSES[(rnd_b + 3) % len(BOSSES)])
            boss = {"kind": kind, "name": ("MEGA " if rd >= 2 else "") + BOSS_NAMES[kind], "title": BOSS_TITLES[kind],
                    "hp": 28 + 6 * tier + 4 * rd, "speed": round(1.0 + 0.05 * tier, 2),
                    "rate": round(max(1.6, 4.2 - 0.12 * tier), 2), "extra": extra, "round": rd}
            camp.append({"n": n, "kind": "boss", "tier": tier, "name": boss["name"], "goals": [], "time": 0,
                         "grav": grav, "save": save + 3, "boss": boss, "bonus": "", "new": ""})
            continue
        if is_bonus(n):
            bk = BONUS_KINDS[tier % 2]
            camp.append({"n": n, "kind": "bonus", "tier": tier, "name": BONUS_NAMES[bk][tier // 2 % 4], "goals": [],
                         "time": 30 + min(10, tier // 2), "grav": grav, "save": 0, "boss": None, "bonus": bk,
                         "new": ""})
            continue
        tb = TABLES[tier]
        avail = [g for g in unlocked if table_supports(tb, g)]
        new = ""
        fresh = [g for g in INTRO.get(tier, []) if table_supports(tb, g)]
        # the tier's new goal types come first so the card can introduce them
        if k < len(fresh):
            first = fresh[k]
            new = NEW_TEXT.get(first, "")
        else:
            if k == 0 or not bag:            # a shuffled bag per tier: every goal type comes round
                bag = [g for g in avail if g != "hits"] or list(avail)
                rnd.shuffle(bag)
            first = bag.pop()
        goals = [first]
        ngoals = 1 if tier < 6 else (2 if tier < 12 else 3)
        if tier >= 12 and k in (1, 4):
            ngoals = 2
        if first in ("multi", "hits"):
            ngoals = min(ngoals, 2)
        pool = [g for g in avail if g not in goals and g not in ("multi", "hits")]
        while len(goals) < ngoals and pool:
            g = rnd.choice(pool)
            pool.remove(g)
            goals.append(g)
        counts = [[g, goal_count(g, tier, rnd)] for g in goals]
        # extra goals are a bit smaller so multi-goal missions stay sane
        for c in counts[1:]:
            if c[0] not in ("multi", "meow", "combo"):
                c[1] = max(2, int(c[1] * 0.7))
        timed = first == "hits" or (tier >= 3 and k in (6, 8) and first not in ("multi",))
        time_ = 0
        if timed:
            counts = counts[:2]
            need = sum(GOALS[g][2] * c for g, c in counts)
            if need * 1.35 + 12 > 150:           # trim the goals so the clock stays fair
                f = (150 - 12) / 1.35 / need
                for c in counts:
                    if c[0] not in ("multi",):
                        c[1] = max(1, int(c[1] * f))
                need = sum(GOALS[g][2] * c for g, c in counts)
            time_ = int(max(30, min(150, need * 1.35 + 12)))
            time_ -= time_ % 5
        for c in counts:
            if c[0] == "score":
                c[1] = max(1000, int(round(c[1] / 1000.0)) * 1000)
        name = rnd.choice([x for x in NAMES[first] if x not in recent] or NAMES[first])
        recent = (recent + [name])[-4:]
        camp.append({"n": n, "kind": "normal", "tier": tier, "name": name, "goals": counts, "time": time_,
                     "grav": grav, "save": save, "boss": None, "bonus": "", "new": new})
    return camp


def validate(st):
    """Return a list of problems with a stage (empty = playable)."""
    errs = []
    tier = st["tier"]
    tb = ARENA if st["kind"] == "boss" else TABLES[tier]
    if st["kind"] == "normal":
        if not st["goals"]:
            errs.append("no goals")
        for g, c in st["goals"]:
            if g not in GOALS:
                errs.append(f"unknown goal {g}")
            elif not table_supports(tb, g):
                errs.append(f"table {tb['name']} can't do {g}")
            if c <= 0:
                errs.append(f"bad count {g} {c}")
        if st["time"]:
            need = sum(GOALS[g][2] * c for g, c in st["goals"])
            if st["time"] < need * 1.2:
                errs.append(f"too little time {st['time']} for {need:.0f}")
    elif st["kind"] == "boss":
        b = st["boss"]
        if b["kind"] not in BOSSES or b["hp"] <= 0:
            errs.append("bad boss")
        if not tb["ramps"] or not tb["fish"]:
            errs.append("arena needs ramps and fish")
    else:
        if st["bonus"] not in BONUS_KINDS or st["time"] <= 0:
            errs.append("bad bonus")
    errs += validate_table(tb)
    return errs


def validate_table(tb):
    """Geometry sanity: everything inside the playfield and nothing overlapping a flipper's sweep."""
    errs = []
    for x, y in tb["bumpers"]:
        if not (LW + 12 < x < RW - 12 and 40 < y < 120):
            errs.append(f"bumper out of place {x},{y}")
        if y < arch_y(x) + 14:
            errs.append(f"bumper under the arch {x},{y}")
    for f in tb["fish"]:
        if not (LW + 6 < f[0] < RW - 3 and 40 < f[1] < 130):
            errs.append(f"fish out of place {f}")
    items = [(b[0], b[1], 9) for b in tb["bumpers"]] + [(p[0], p[1], p[2]) for p in tb["posts"]]
    for i, (x, y, r) in enumerate(items):           # a ball must fit between any two round things
        for x2, y2, r2 in items[i + 1:]:
            gap = math.hypot(x - x2, y - y2) - r - r2
            if 0 < gap < 2 * BALL_R + 1 and (r > 3 or r2 > 3):
                errs.append(f"tight gap {x},{y} - {x2},{y2}")
    for x, y in tb["spots"]:
        if math.hypot(x - FLIP_X[0], y - FLIP_Y) < 40 or math.hypot(x - FLIP_X[1], y - FLIP_Y) < 40:
            errs.append("kitten spot too close to a flipper")
    for r in tb["ramps"]:
        if len(r["path"]) < 3:
            errs.append("short ramp")
    return errs


CAMPAIGN = build_campaign()
