"""YARN WEAVER campaign: 200 stages in 20 rooms of KUMO's house, built from curated furniture layouts,
a per-room hazard recipe and seeded variation. Every stage hides an original cat picture (a picture *spec*,
painted by yarn_weaver_art.draw_picture). The whole table is exported to Swift (EXPORT in yarn_weaver.py),
so both platforms play exactly the same stages.
"""
import random

from mochi_arcade.arcade import STAGES, is_boss, is_bonus, tier

GW, GH = 152, 88            # playfield grid (2x2 pixel cells) -> 304 x 176 pixels

# (room name, rug colour, rug pattern colour, rug pattern, yarn colour A, yarn colour B, song)
THEMES = [
    ("LIVING ROOM", "brown", "choco", 2, "hotpink", "pink", "yw_purl"),
    ("KITCHEN", "teal", "mint", 7, "yellow", "orange", "yw_string"),
    ("BEDROOM", "purple", "deep", 1, "mint", "white", "yw_purl"),
    ("SUNROOM", "orange", "peach", 0, "sky", "white", "yw_string"),
    ("LIBRARY", "choco", "brown", 7, "yellow", "cream", "yw_purl"),
    ("BATHROOM", "sky", "blue", 2, "hotpink", "white", "yw_string"),
    ("ATTIC", "darkgray", "ink", 0, "orange", "yellow", "yw_purl"),
    ("GARDEN PATIO", "teal", "lime", 1, "pink", "white", "yw_string"),
    ("MUSIC ROOM", "red", "hotpink", 6, "white", "yellow", "yw_purl"),
    ("BASEMENT", "ink", "deep", 2, "lime", "mint", "yw_string"),
    ("GRANDMA'S HOUSE", "pink", "peach", 3, "purple", "lavender", "yw_purl"),
    ("CAT CAFE", "brown", "peach", 0, "mint", "white", "yw_string"),
    ("TOY SHOP", "blue", "sky", 1, "yellow", "white", "yw_purl"),
    ("BAKERY", "peach", "orange", 7, "hotpink", "red", "yw_string"),
    ("GREENHOUSE", "teal", "mint", 6, "orange", "yellow", "yw_purl"),
    ("TRAIN CAR", "red", "choco", 2, "yellow", "cream", "yw_string"),
    ("GRAND HOTEL", "purple", "lavender", 3, "yellow", "orange", "yw_purl"),
    ("MUSEUM", "gray", "darkgray", 7, "red", "pink", "yw_string"),
    ("OBSERVATORY", "night", "blue", 4, "yellow", "white", "yw_purl"),
    ("MOON PALACE", "deep", "lavender", 4, "mint", "white", "yw_string"),
]

NAMES = ["PICKLE", "BISCUIT", "TOFU", "NORI", "MISO", "SOBA", "PEACHES", "OLIVE", "PUDDING", "BEAN", "MAPLE",
         "SUSHI", "TURNIP", "WAFFLE", "BUTTONS", "PEPPER", "CLOVER", "GINGER", "MOCHA", "LATTE", "JUNIPER", "PIP",
         "ZIGGY", "LUNA", "SOOTY", "MITTENS", "SOCKS", "TAFFY", "PRETZEL", "BOBA", "YUZU", "KIWI", "MANGO", "FIG",
         "PLUM", "HAZEL", "COCOA", "MUFFIN", "CRUMPET", "SCONE", "TRUFFLE", "BINGO", "NUGGET", "POPCORN", "SPROUT",
         "PANCAKE", "MOOSE", "GIZMO", "TOAST", "CHAI", "MATCHA", "SESAME", "UDON", "RAMEN", "TEMPURA", "DAIFUKU",
         "BEANIE", "PIXEL", "COMET", "STARDUST", "NOODLE", "DUMPLING", "MARSHMALLOW", "CINNAMON", "NUTMEG",
         "PAPRIKA", "SAFFRON", "BASIL", "PARSLEY", "ROSEMARY", "THYME", "MINTY", "BRAMBLE", "THISTLE", "ACORN",
         "PINECONE", "BUTTERCUP", "DAISY", "TULIP", "POPPY", "WILLOW", "AVOCADO", "TATER", "BEANS", "CHEDDAR",
         "BRIE", "GOUDA", "PESTO", "RAVIOLI", "GNOCCHI", "MACARON", "ECLAIR", "SPRINKLES", "CUPCAKE", "BROWNIE",
         "JELLYBEAN", "GUMDROP", "LOLLIPOP", "TOFFEE", "FUDGE"]
TITLES = ["", "", "", "LITTLE ", "SIR ", "LADY ", "CAPTAIN ", "DR. ", "BABY ", "BIG ", "AUNTIE ", "PRINCE ",
          "PRINCESS ", "PROFESSOR "]

# (fur, marking colour, marking) - marking: 0 solid 1 tabby 2 tuxedo 3 calico 4 colour points 5 spots
COATS = [("orange", "peach", 1), ("gray", "darkgray", 1), ("darkgray", "white", 2), ("white", "orange", 3),
         ("cream", "brown", 4), ("brown", "choco", 1), ("peach", "orange", 5), ("white", "gray", 0),
         ("cream", "peach", 1), ("choco", "brown", 0), ("gray", "white", 2), ("orange", "white", 2),
         ("lavender", "purple", 0), ("sky", "blue", 1), ("pink", "hotpink", 5), ("white", "sky", 4),
         ("mint", "teal", 5), ("yellow", "orange", 1)]
EYES = ["lime", "sky", "yellow", "mint", "orange", "blue", "teal"]
WALLS = [("cream", "peach"), ("sky", "white"), ("mint", "lime"), ("lavender", "pink"), ("peach", "yellow"),
         ("pink", "cream"), ("teal", "mint"), ("yellow", "cream"), ("lime", "mint"), ("deep", "purple"),
         ("night", "ink"), ("blue", "sky"), ("purple", "lavender"), ("orange", "peach")]
ACC_COLS = ["red", "hotpink", "sky", "lime", "purple", "orange", "teal", "yellow", "blue"]
CUSHIONS = ["red", "blue", "teal", "purple", "orange", "hotpink", "lime", "sky", "yellow"]

QUIPS = ["WHO'S UNDER THE RUG?", "MY WHISKERS ARE TINGLING!", "TIME TO KNIT A FRIEND!", "PURR-FECT DAY TO WEAVE!",
         "I SMELL A NEW FRIEND...", "KEEP YOUR YARN TIGHT!", "STAY AWAY FROM THE FLUFF!", "ONE STITCH AT A TIME!",
         "SOMEONE CUTE IS HIDING!", "PAWS READY... WEAVE!", "BIG LOOPS, BIG POINTS!", "MEOW-VELOUS RUG!"]

# hazards and twists, introduced one room at a time (shown as "NEW!" on the stage card)
INTRO = {0: "WEAVE INTO THE RUG TO CLAIM IT!", 1: "NEW: CUSHIONS - WEAVE TO THEM!", 2: "NEW: TWIN FLUFFS!",
         3: "NEW: MOTHS NIBBLE LOOSE YARN!", 4: "NEW: FUZZLETS - TINY AND FAST!", 5: "NEW: SNIFFY NOSE UNDER THE RUG!",
         6: "NEW: RED ZIPS HUNT YOU!", 7: "NEW: STATIC STORMS - FLUFF ZAPS!", 8: "NEW: KNOTS - WEAVE AROUND THEM!",
         9: "NEW: MOTH SWARMS!", 10: "REMIX: GRANDMA'S EVERYTHING!", 12: "NEW: TRIPLE FLUFF!",
         14: "FASTER ZIPS!", 16: "STORMIER FLUFF!", 18: "THE FINAL ROOMS!"}

# boss designs (yarn_weaver_boss.py): kind -> name
BOSSES = {"cloud": "NIMBUS", "mouse": "TIN WHISKER", "vacuum": "DUST GULPER", "snoot": "BIG SNOOT", "moth": "MADAME DUSTWING"}
BOSS_ORDER = ["cloud", "mouse", "vacuum", "snoot", "moth"]
BOSS_PATTERNS = {"cloud": "bolts", "mouse": "pellets", "vacuum": "dash", "snoot": "bark", "moth": "dive"}


# ----------------------------------------------------------------------------- furniture layouts (grid cells)
def _layouts(rng):
    """Curated furniture layouts, nudged a little per stage. Shapes: ["r", x, y, w, h, c] / ["c", cx, cy, r, c]."""
    j = lambda a: a + rng.randint(-4, 4)  # noqa: E731
    c = lambda: rng.choice(CUSHIONS)  # noqa: E731
    return {
        "open": [],
        "cushions": [["r", j(30), j(24), 14, 14, c()], ["r", j(104), j(46), 16, 14, c()]],
        "table": [["r", j(56), j(32), 40, 22, c()]],
        "legs": [["r", j(44), j(22), 8, 8, c()], ["r", j(100), j(22), 8, 8, c()], ["r", j(44), j(58), 8, 8, c()],
                 ["r", j(100), j(58), 8, 8, c()]],
        "sofa": [["r", j(40), 1, 72, 12, c()]],
        "shelves": [["r", j(38), 1, 8, 36, c()], ["r", j(106), 51, 8, 36, c()]],
        "stones": [["r", j(22), j(18), 7, 7, c()], ["r", j(62), j(50), 7, 7, c()], ["r", j(100), j(20), 7, 7, c()],
                   ["r", j(124), j(60), 7, 7, c()], ["r", j(36), j(62), 7, 7, c()]],
        "nooks": [["r", 1, 1, 20, 14, c()], ["r", GW - 21, 1, 20, 14, c()], ["r", 1, GH - 15, 20, 14, c()],
                  ["r", GW - 21, GH - 15, 20, 14, c()]],
        "plus": [["r", j(68), j(22), 16, 44, c()], ["r", j(50), j(37), 52, 14, c()]],
        "ottomans": [["c", j(40), j(30), 8, c()], ["c", j(112), j(30), 8, c()], ["c", j(76), j(60), 9, c()]],
        "pillars": [["c", j(38), j(44), 6, c()], ["c", j(76), j(44), 6, c()], ["c", j(114), j(44), 6, c()]],
        "corner": [["r", 1, 1, 34, 24, c()], ["c", j(110), j(58), 10, c()]],
    }


LAYOUT_BY_TIER = [
    ["open"], ["cushions", "open", "table"], ["legs", "open", "sofa"], ["table", "shelves", "open"],
    ["stones", "cushions", "nooks"], ["ottomans", "open", "sofa"], ["plus", "legs", "pillars"],
    ["corner", "stones", "shelves"], ["open", "ottomans", "nooks"], ["pillars", "table", "cushions"],
]


def apply_shapes(grid, shapes, value=1):
    """Mark furniture cells in a flat GW*GH grid."""
    for sh in shapes:
        if sh[0] == "r":
            _, x, y, w, h, _c = sh
            for yy in range(max(0, y), min(GH, y + h)):
                for xx in range(max(0, x), min(GW, x + w)):
                    grid[yy * GW + xx] = value
        else:
            _, cx, cy, r, _c = sh
            for yy in range(max(0, cy - r), min(GH, cy + r + 1)):
                for xx in range(max(0, cx - r), min(GW, cx + r + 1)):
                    if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                        grid[yy * GW + xx] = value


def base_grid(shapes):
    """0 = open rug, 1 = claimed (the border ring and the furniture)."""
    g = bytearray(GW * GH)
    for x in range(GW):
        g[x] = g[(GH - 1) * GW + x] = 1
    for y in range(GH):
        g[y * GW] = g[y * GW + GW - 1] = 1
    apply_shapes(g, shapes)
    return g


def open_regions(g):
    """4-connected regions of open cells: list of lists of cell indices."""
    seen = bytearray(len(g))
    out = []
    for i in range(len(g)):
        if g[i] or seen[i]:
            continue
        reg = [i]
        seen[i] = 1
        k = 0
        while k < len(reg):
            c = reg[k]
            k += 1
            x = c % GW
            for n in (c - 1 if x > 0 else -1, c + 1 if x < GW - 1 else -1, c - GW, c + GW):
                if 0 <= n < len(g) and not g[n] and not seen[n]:
                    seen[n] = 1
                    reg.append(n)
        out.append(reg)
    return out


# ----------------------------------------------------------------------------- pictures
def picture(rng, n, kind, used):
    coat = rng.choice(COATS if n > 30 else COATS[:12])
    wall = rng.choice(WALLS)
    name = None
    for _ in range(200):
        nm = rng.choice(TITLES) + rng.choice(NAMES)
        if nm not in used:
            name = nm
            break
    name = name or f"KITTY {n}"
    used.add(name)
    acc = rng.choice([0, 1, 1, 2, 2, 3, 5, 7]) if kind == "normal" else (4 if kind == "bonus" else 6)
    prop = rng.choice([0, 1, 1, 2, 3, 4, 5, 6, 7]) if kind == "normal" else (6 if kind == "bonus" else 1)
    return {"name": name, "bg": wall[0], "bg2": wall[1], "pat": rng.randrange(8), "pose": rng.randrange(4),
            "fur": coat[0], "fur2": coat[1], "mark": coat[2], "eye": rng.choice(EYES),
            "mood": rng.choice([0, 0, 1, 2, 3]), "acc": acc, "accc": rng.choice(ACC_COLS), "prop": prop,
            "propc": rng.choice(ACC_COLS), "cush": rng.choice(CUSHIONS), "x": rng.randint(-34, 34)}


# ----------------------------------------------------------------------------- the campaign
def _knots(rng, shapes, k):
    g = base_grid(shapes)
    out = []
    for _ in range(200):
        if len(out) >= k:
            break
        x, y = rng.randint(14, GW - 15), rng.randint(12, GH - 22)
        if any(g[yy * GW + xx] for yy in range(y - 6, y + 7) for xx in range(x - 6, x + 7)):
            continue
        if any(abs(x - a) + abs(y - b) < 24 for a, b in out):
            continue
        out.append([x, y])
    return out


FEATS = ["", "", "twin", "moths", "minis", "nose", "hunters", "storm", "knots", "swarm"]   # by room (tier % 10)


def stage_feats(rng, t, sub):
    """Which hazards a stage uses: the room's newest one (most stages) plus a few learned earlier."""
    tt = t % 10
    learned = [f for f in FEATS[:tt + 1 if t < 10 else 10] if f]
    newest = FEATS[tt] if t < 10 else ""
    pool = [f for f in learned if f != newest]
    out = []
    if newest and (sub < 6 or rng.random() < 0.6):
        out.append(newest)
    k = min(len(pool), (1 + sub // 4) if t < 10 else (2 + sub // 4 + (t >= 15)))
    if t < 10 and sub < 2:
        k = min(k, 1)
    out += rng.sample(pool, k)
    return out


def build_stage(n, used):
    rng = random.Random(9000 + n * 7919)
    t = tier(n)
    room = THEMES[t]
    sub = (n - 1) % 10            # 0..9 inside the room
    kind = "boss" if is_boss(n) else "bonus" if is_bonus(n) else "normal"
    late = t >= 10
    tt = t - 10 if late else t     # the recipe repeats in the second half, faster and mixed
    lay_names = LAYOUT_BY_TIER[tt]
    layout = lay_names[sub % len(lay_names)] if kind == "normal" else ("open" if kind == "boss" else lay_names[0])
    if kind == "bonus":
        layout = "open"
    if n <= 2:
        layout = "open"
    shapes = _layouts(rng)[layout]
    speed = 1.0 + 0.035 * t + 0.01 * sub
    st = {"n": n, "tier": t, "kind": kind, "room": room[0], "layout": layout, "shapes": shapes,
          "target": min(90, 75 + (t * 3) // 4 + (sub % 3)), "speed": round(speed, 3),
          "pic": picture(rng, n, kind, used), "quip": rng.choice(QUIPS), "new": "",
          "fluffs": 1, "minis": 0, "zips": 0, "hunters": 0, "moths": 0, "nose": 0.0, "storm": 0.0,
          "knots": [], "items": round(max(7.0, 13.0 - 0.25 * t), 2), "time": 0, "bonus": "", "boss": None}
    # hazard recipe: the room's newest trick, plus a seeded handful of the ones learned before
    feats = set(stage_feats(rng, t, sub))
    st["feats"] = sorted(feats)
    st["zips"] = 0 if n <= 2 else 1 if t == 0 else 2 if t < 6 else 3 if t < 14 else 4
    st["fluffs"] = (2 if "twin" in feats else 1) + (1 if t >= 12 and sub >= 6 else 0)
    st["moths"] = (1 if "moths" in feats else 0) + (2 if "swarm" in feats else 0)
    st["minis"] = (1 + (t >= 15) + (sub % 4 == 3)) if "minis" in feats else 0
    st["nose"] = round(max(5.0, 11.0 - 0.3 * t), 2) if "nose" in feats else 0.0
    st["hunters"] = (1 + (t >= 16)) if "hunters" in feats else 0
    st["storm"] = round(max(4.0, 9.0 - 0.2 * t), 2) if "storm" in feats else 0.0
    st["knots"] = _knots(rng, shapes, 2 + sub % 3 + (t >= 18)) if "knots" in feats else []
    if sub == 0 and kind == "normal":
        st["new"] = INTRO.get(t, "")
    if n == 3:
        st["new"] = "NEW: ZIPS RUN ALONG THE EDGES!"
    if kind == "bonus":
        st.update(fluffs=0, minis=0, zips=0, hunters=0, moths=0, nose=0.0, storm=0.0, knots=[], target=95,
                  time=30, bonus="poms" if t % 2 == 0 else "fish")
        st["poms"] = 6 + min(6, t // 3)
        st["fish"] = 24 + min(16, t)
    if kind == "boss":
        bk = BOSS_ORDER[t % 5] if n < STAGES else "cloud"
        extra = []
        if late:
            extra.append(BOSS_PATTERNS[BOSS_ORDER[(t + 2) % 5]])
        if t >= 15:
            extra.append(BOSS_PATTERNS[BOSS_ORDER[(t + 3) % 5]])
        if n == STAGES:
            extra = [p for p in BOSS_PATTERNS.values() if p != "bolts"]
        st["boss"] = {"kind": bk, "name": "GRAND FUZZ" if n == STAGES else BOSSES[bk], "tier": t,
                      "hp": round(min(0.68, 0.46 + 0.012 * t), 3), "rate": round(max(1.1, 2.6 - 0.07 * t), 2),
                      "speed": round(36 + 2.2 * t, 1), "extra": extra, "minions": 1 + t // 4}
        st.update(fluffs=0, minis=0, moths=0, nose=0.0, storm=0.0, knots=[], zips=1 + (t >= 8), hunters=int(t >= 12),
                  target=100)
    st["fspeed"] = round(52 * speed, 1)
    st["zspeed"] = round(min(46.0, 24 + 1.1 * t + (2 if t >= 14 else 0)), 1)
    return st


def build_campaign():
    used = set()
    return [build_stage(n, used) for n in range(1, STAGES + 1)]


def validate(st):
    """Return a list of problems with a stage (empty = playable)."""
    errs = []
    g = base_grid(st["shapes"])
    regs = open_regions(g)
    if len(regs) != 1:
        errs.append(f"open rug must be one region, got {len(regs)}")
    total = GW * GH
    opened = sum(len(r) for r in regs)
    if opened < total * 0.6:
        errs.append(f"too much furniture: {opened}/{total} open")
    sx, sy = GW // 2, GH - 1
    if not g[sy * GW + sx] or g[(sy - 1) * GW + sx]:
        errs.append("KUMO must start on the bottom edge next to open rug")
    for x, y in st["knots"]:
        if g[y * GW + x]:
            errs.append(f"knot on furniture at {x},{y}")
        if abs(x - sx) + abs(y - sy) < 16:
            errs.append("knot too close to the start")
    if st["kind"] == "normal" and not (75 <= st["target"] <= 90):
        errs.append(f"target {st['target']} out of range")
    if st["kind"] == "normal" and st["fluffs"] < 1:
        errs.append("a normal stage needs a fluff")
    if st["kind"] == "boss" and not st["boss"]:
        errs.append("boss spec missing")
    return errs


CAMPAIGN = build_campaign()
