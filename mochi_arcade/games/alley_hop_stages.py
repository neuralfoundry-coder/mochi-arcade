"""ALLEY HOP campaign data: 200 stages built from curated lane layouts and lane traffic templates (seeded per
stage), plus the validator the tests run over every stage. Exported to the iOS port through alley_hop.EXPORT,
so both platforms play exactly the same stages.

The play field is 11 rows of 16 px: row 0 is the HOME row (cardboard boxes in a fence), row 10 the start sidewalk.
Every lane is a pure function of 'lane time' t, so both platforms - and the autopilot - can predict it:
  shift(t) = ph + v * t                    linear lanes (roads, canals, belts, pulley lines)
  shift(t) = sw * sin(om * t + ph)         swaying laundry lines over the rooftop gaps
  screen x of a pattern item = pmod(item_x + shift, P) - PAD,    PAD = (P - 320) / 2
Lane types: home start safe road water gap rail fence belt   (water / gap / belt carry whoever stands on them)
"""
import math
import random

from mochi_arcade.arcade import STAGES, is_boss, is_bonus

W = 320
CELL = 16
COLS = 20
ROWS = 11
START_COL = 9
CARRIERS = ("water", "gap", "belt")
HAZARDS = ("road", "water", "gap", "rail", "fence")
WIDTH = {"bike": 16, "can": 14, "scooter": 24, "van": 40, "pigeon": 12}
CODE = {".": "safe", "R": "road", "W": "water", "G": "gap", "T": "rail", "F": "fence", "B": "belt", "r": "road"}

# tier -> what the campaign introduces there (shown on the first stage card of the tier)
NEW_TEXT = {
    0: "HOP THE KITTENS HOME!",
    1: "NEW: SCOOTERS AND SLOW PUDDLES",
    2: "NEW: CANALS - RIDE CRATES + DUCKS",
    3: "NEW: ROOFTOPS - SWAYING LAUNDRY",
    4: "NEW: TRAINS AND CLOSING GATES",
    5: "NEW: MANHOLE SHORTCUTS + RAIN",
    6: "NEW: DIVING DUCKS + SLEEPY FISH",
    7: "NEW: FLICKERING STREETLIGHTS",
    8: "NEW: NOODLE VANS - FAST LANES",
    9: "NEW: BOX LIDS OPEN AND SHUT",
    10: "EVERYTHING GOT FASTER!",
    13: "NEW: PULLEY LINES ON THE ROOFS",
}

# 20 night-town themes, one per tier
# name, ground, ground2, road, paint, water, water2, void, wall, accent, focus lane code
THEMES = [
    ["MAPLE ALLEY", "darkgray", "gray", "ink", "gray", "blue", "sky", "night", "brown", "orange", "R"],
    ["NOODLE STREET", "deep", "lavender", "night", "yellow", "blue", "sky", "night", "red", "yellow", "R"],
    ["LANTERN CANAL", "brown", "peach", "ink", "gray", "blue", "sky", "night", "choco", "red", "W"],
    ["LAUNDRY ROOFS", "choco", "brown", "ink", "gray", "blue", "sky", "night", "darkgray", "pink", "G"],
    ["TRAIN TOWN", "darkgray", "gray", "night", "yellow", "blue", "sky", "night", "deep", "yellow", "T"],
    ["RAINY MARKET", "teal", "darkgray", "ink", "sky", "blue", "sky", "night", "deep", "sky", "R"],
    ["DUCK DOCKS", "brown", "choco", "ink", "gray", "teal", "mint", "night", "choco", "yellow", "W"],
    ["NEON NIGHTS", "deep", "purple", "night", "hotpink", "blue", "sky", "black", "purple", "hotpink", "R"],
    ["BRIDGE STREET", "gray", "darkgray", "ink", "white", "blue", "sky", "night", "darkgray", "orange", "R"],
    ["MOONLIT HARBOR", "choco", "brown", "ink", "gray", "ink", "blue", "night", "brown", "lavender", "W"],
    ["BLOSSOM LANE", "deep", "pink", "ink", "pink", "blue", "sky", "night", "purple", "pink", "R"],
    ["FIREWORK FAIR", "brown", "orange", "night", "yellow", "blue", "sky", "night", "red", "orange", "T"],
    ["FOGGY CANALS", "darkgray", "gray", "ink", "gray", "ink", "teal", "black", "deep", "mint", "W"],
    ["WINDY ROOFTOPS", "choco", "brown", "ink", "gray", "blue", "sky", "night", "darkgray", "sky", "G"],
    ["EXPRESS LINE", "darkgray", "gray", "night", "red", "blue", "sky", "night", "deep", "red", "T"],
    ["STORM STREET", "teal", "darkgray", "ink", "yellow", "ink", "blue", "black", "deep", "yellow", "R"],
    ["KOI GARDEN", "brown", "peach", "ink", "gray", "teal", "mint", "night", "choco", "orange", "W"],
    ["MIDNIGHT MARKET", "deep", "purple", "night", "lime", "blue", "sky", "black", "purple", "lime", "F"],
    ["HIGHWAY HILL", "gray", "darkgray", "ink", "white", "blue", "sky", "night", "darkgray", "red", "R"],
    ["STARLIGHT HOME", "deep", "lavender", "night", "yellow", "blue", "sky", "night", "purple", "yellow", "G"],
]
DARK_TIERS = (7, 12, 15, 17)
RAIN_TIERS = (5, 15)

# curated lane layouts: min tier, rows 9 (just above the start sidewalk) .. 1 (just below home)
LAYOUTS = [
    (0, "RR.RR.RR."), (0, "R.RRR.RR."), (0, ".RR.RR.RR"), (0, "RRR..RR.R"), (0, "RR.R.RRR."),
    (0, ".RRR.RR.."), (0, "RR..RR.RR"), (0, "R.RR.R.RR"),
    (1, "RRRR.RRR."), (1, "RRR.RRRR."), (1, ".RRRR.RRR"),
    (2, "RR.WW.RR."), (2, ".WWW.RR.."), (2, "RR.WWW.R."), (2, "R.WW.WW.."), (2, "WW.RRR.WW"),
    (2, "RRR.WWW.."), (3, ".RR.WWWW."), (3, "WWW.RR.WW"),
    (3, "RR.GG.RR."), (3, ".GG.WW.RR"), (3, "R.GGG.RR."), (3, "GG.RR.GG."), (3, ".GG.GG.WW"),
    (4, "RR.GGG.WW"), (4, "RT.RR.FWW"), (4, "T.RR.T.RR"), (4, ".RRF.WWT."), (4, "TR.WW.FR."),
    (4, "RR.T.RR.F"), (4, ".F.RRT.GG"), (5, "TRR.WW.RR"), (5, "RR.F.WWW."),
    (8, "RRT.WWW.R"), (8, "GG.RRR.WW"), (8, "WWW.RRR.T"), (8, "TRR.GGG.F"), (9, "RRF.WWWW."),
    (12, "RRRR.WWWW"), (12, "WWWW.RRRT"), (12, "GGG.TRRR."), (14, "TTR.WWW.R"), (14, "RRRRR.WWW"),
]
# lane codes the first stage of a tier must contain (its card announces them), and forced lane flavours
REQUIRE = {2: "W", 3: "G", 4: "TF", 6: "W", 8: "R", 13: "G", 14: "T"}
FORCE = {6: {"water": "dive"}, 8: {"road": "NOODLE VANS"}, 13: {"gap": "line"}}
MAX_RUN = [3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]

# traffic templates: name, min tier, kinds (cycled), gap px (lo, hi), speed px/s (lo, hi)
ROAD_T = [
    ("BIKES", 0, ["bike"], (56, 110), (30, 40)),
    ("TRASH ROLL", 0, ["can", "can"], (40, 90), (16, 24)),
    ("BIKE PACK", 0, ["bike", "bike", "can"], (40, 96), (26, 36)),
    ("SCOOTERS", 1, ["scooter"], (64, 120), (44, 56)),
    ("DELIVERY RUSH", 1, ["scooter", "bike"], (52, 104), (36, 48)),
    ("NOODLE VANS", 8, ["van"], (72, 130), (34, 46)),
    ("BIG CITY", 8, ["van", "scooter", "bike"], (56, 110), (36, 50)),
    ("ZOOM LANE", 10, ["scooter", "scooter"], (84, 140), (60, 72)),
]
WATER_T = [
    ("CRATES", 2, ["crate3", "crate2"], (24, 56), (16, 24)),
    ("DUCK FAMILY", 2, ["duck2", "crate3"], (24, 52), (18, 26)),
    ("LONG CRATES", 2, ["crate4"], (32, 64), (14, 20)),
    ("SLEEPY FISH", 6, ["fish", "crate2"], (28, 56), (14, 22)),
    ("DUCK PARADE", 6, ["duck3", "duck2"], (24, 48), (20, 28)),
]
GAP_T = [
    ("LAUNDRY", 3, "sway"),
    ("PULLEY LINE", 13, "line"),
]
NAMES = {
    "R": ["BUSY CORNER", "BIKE ROW", "SCOOTER STREET", "CROSSWALK", "NOODLE RUN", "BIN DAY", "RUSH HOUR",
          "LAMPLIGHT WAY", "BELL LANE", "ZOOM ZONE", "SIDE STREET", "SNACK ROAD"],
    "W": ["CRATE CROSSING", "DUCK POND", "LANTERN BRIDGE", "SPLASHY STEPS", "FISHY FERRY", "QUACK CANAL",
          "DRIFTWOOD", "BOAT LANE"],
    "G": ["SHEET JUMP", "SOCK LINE", "CHIMNEY HOP", "TOWEL SWING", "ROOF GAP", "BREEZY TOPS"],
    "T": ["CROSSING BELL", "LAST TRAIN", "SIGNAL BOX", "RAIL YARD", "NIGHT EXPRESS"],
    "F": ["GATE KEEPER", "GARDEN GATES", "PICKET PATH", "LATCH LANE"],
}
BONUS_NAMES = {"feast": ["FISH FEAST", "MARKET SNACKS", "SUSHI BELT", "MIDNIGHT BUFFET"],
               "parade": ["KITTEN PARADE", "BIG FAMILY DAY", "CONGA CATS", "MEW MARCH"]}
SUSHI_LINES = [
    "STAY CLOSE, LITTLE ONES!", "ONE HOP AT A TIME!", "MAMA SUSHI IS HERE!", "PAWS UP - LET'S GO!",
    "MIND THE BIKES, KITTENS!", "NOBODY GETS LEFT BEHIND!", "HOME IS JUST UP THERE!", "TAILS UP, EVERYONE!",
    "QUIET PAWS... NOW HOP!", "WHO WANTS A WARM BOX?",
]

# bosses: one per tier (stage 10, 20 ... 200); later appearances borrow attacks from the others
BOSS_ORDER = ["bruno", "sweepo", "gulls", "coon", "claw", "owl"] * 3 + ["coon", "king"]
BOSS_NAMES = {"bruno": "BRUNO", "sweepo": "SWEEPO", "gulls": "GULL GANG", "coon": "BANDIT COON",
              "claw": "KING CLAW", "owl": "HOOTSWORTH", "king": "BIG BOSS BRUNO"}
BOSS_TITLE = {"bruno": "THE GUARD DOG", "sweepo": "THE STREET SWEEPER", "gulls": "THE SEAGULL GANG",
              "coon": "THE TRASH BANDIT", "claw": "THE DOCK CRAB", "owl": "THE NIGHT OWL",
              "king": "THE TOP DOG"}
BOSS_HINT = {"bruno": "HOP ON HIM WHILE HE'S DIZZY!", "sweepo": "HOP ON IT WHILE IT REFILLS!",
             "gulls": "HOP ON A GULL WHILE IT EATS!", "coon": "HOP ON HIM WHILE HE DIGS!",
             "claw": "HOP ON A STUCK CLAW!", "owl": "HOP ON HIM WHILE HE PERCHES!",
             "king": "DODGE EVERYTHING - HOP WHEN DIZZY!"}
BOSS_BASE = {"bruno": ["charge", "ring", "charge"], "sweepo": ["charge", "cols", "charge", "rest"],
             "gulls": ["strike", "cols", "strike"], "coon": ["rows", "cols", "rest"],
             "claw": ["strike", "rows", "strike"], "owl": ["cols", "charge", "ring"],
             "king": ["charge", "ring", "rows", "strike", "cols", "charge"]}
BOSS_EXTRA = {"bruno": ["rows", "strike"], "sweepo": ["ring", "rows"], "gulls": ["rows", "strike"],
              "coon": ["strike", "ring"], "claw": ["cols", "ring"], "owl": ["rows", "strike"], "king": []}
SHOT_KIND = {"bruno": ("ball", "bone"), "sweepo": ("suds", "jet"), "gulls": ("feather", "egg"),
             "coon": ("lid", "can"), "claw": ("bubble", "bubble"), "owl": ("feather", "dart"),
             "king": ("ball", "can")}
ARENAS = {"bruno": ".R.....R.", "sweepo": "RR..R..RR", "gulls": ".WW..WW..", "coon": ".R.....R.",
          "claw": "..WW.WW..", "owl": ".G..G..G.", "king": ".R..W..R."}


def tier_of(n):
    return (n - 1) // 10


def pmod(a, b):
    return a - b * math.floor(a / b)


def r2(x):
    return round(x, 2)


# ----------------------------------------------------------------------------- lanes
def lane(t, **kw):
    d = {"t": t, "v": 0.0, "p": 384, "ph": 0.0, "it": [], "sw": 0.0, "om": 0.0, "dv": [], "tr": [], "gt": [],
         "gc": [], "bl": [], "pd": [], "soft": 0, "nm": ""}
    d.update(kw)
    return d


def fill_items(rng, kinds, P, gmin, gmax, hard_max=None):
    """Lay items out along the pattern: [kind, x, w], all inside [0, P - w]. Every gap (the wrap-around one
    too) lands in [gmin, hard_max]: a random density is picked first, then the slack is shared out."""
    hard_max = hard_max or gmax * 2
    for _ in range(30):
        avg = rng.uniform(gmin, gmax)
        seq = []
        while True:
            kind, w = item_size(kinds[len(seq) % len(kinds)])
            if seq and sum(x[1] for x in seq) + w + (len(seq) + 1) * avg > P:
                break
            seq.append((kind, w))
        total = P - sum(w for _, w in seq)
        raw = [rng.uniform(0.75, 1.25) for _ in seq]
        gaps = [int(total * r / sum(raw)) for r in raw]
        gaps[-1] += total - sum(gaps)
        for i in range(len(gaps)):          # lift short gaps to gmin, paid for by the longest
            while gaps[i] < gmin:
                j = gaps.index(max(gaps))
                if gaps[j] <= gmin:
                    break
                d = min(gmin - gaps[i], gaps[j] - gmin)
                gaps[i] += d
                gaps[j] -= d
        if min(gaps) >= gmin and max(gaps) <= hard_max:
            break
    x = rng.randint(0, gaps[-1])
    items = []
    for (kind, w), g in zip(seq, gaps):
        items.append([kind, x, w])
        x += w + g
    return items


def item_size(k):
    if k.startswith("crate"):
        return "crate", 16 * int(k[5:])
    if k.startswith("duck"):
        return "duck", 16 + 12 * int(k[4:])
    if k == "fish":
        return "fish", 40
    if k.startswith("sheet"):
        return "sheet", int(k[5:])
    return k, WIDTH[k]


def make_road(rng, tier, soft=False, sparse=1.0, force=None):
    pool = [t for t in ROAD_T if t[1] <= tier]
    if tier >= 8:
        late = [t for t in pool if t[1] >= 1]
        pool = late or pool
    if force:
        pool = [t for t in ROAD_T if t[0] == force]
    name, _, kinds, (glo, ghi), (slo, shi) = rng.choice(pool)
    if tier < 3 and sparse <= 1:
        sparse = 1.6 - 0.15 * tier      # gentle first streets
    mul = min(1.7, 1 + 0.035 * tier)
    speed = rng.uniform(slo, shi) * mul
    maxw = max(item_size(k)[1] for k in kinds)
    P = 384 if maxw <= 32 else 416
    gmin = max(glo, 27 + int(speed * 0.6))
    gmax = max(gmin + 8, ghi)
    if sparse > 1:
        gmin, gmax = int(gmin * sparse), int(gmax * sparse)
    items = fill_items(rng, kinds, P, gmin, gmax)
    if not items:
        items = [[item_size(kinds[0])[0], 0, item_size(kinds[0])[1]]]
    return lane("road", v=r2(speed * rng.choice((-1, 1))), p=P, ph=r2(rng.uniform(0, P)), it=items, soft=1 if soft else 0,
                nm=name)


def make_water(rng, tier, prev_v=None, sparse=1.0, allow_dive=True, force=None):
    pool = [t for t in WATER_T if t[1] <= tier]
    if force == "dive":
        pool = [t for t in WATER_T if t[0] in ("SLEEPY FISH", "DUCK PARADE")]
    name, _, kinds, (glo, ghi), (slo, shi) = rng.choice(pool)
    mul = min(1.6, 1 + 0.03 * tier)
    speed = rng.uniform(slo, shi) * mul
    P = 448
    gmax = min(ghi, int(speed * 2.2) + 24)
    gmin = min(glo, gmax)
    hard = int(speed * 2.5) + 26
    if sparse > 1:
        gmax = min(int(gmax * sparse), hard - 8)
    items = fill_items(rng, kinds, P, gmin, min(gmax, int(hard / 1.3)), hard)
    d = 1 if prev_v is None else (-1 if prev_v > 0 else 1)
    if prev_v is None:
        d = rng.choice((-1, 1))
    ln = lane("water", v=r2(speed * d), p=P, ph=r2(rng.uniform(0, P)), it=items, nm=name)
    if allow_dive and tier >= 6 and name in ("SLEEPY FISH", "DUCK PARADE") and (rng.random() < 0.55 or force):
        cyc = r2(rng.uniform(4.5, 6.5))
        ln["dv"] = [cyc, r2(min(1.6, 0.9 + 0.03 * tier)), r2(rng.uniform(1.1, 1.8))]
    return ln


def make_gap(rng, tier, prev_v=None, force=None):
    pool = [t for t in GAP_T if t[1] <= tier]
    if force:
        pool = [t for t in GAP_T if t[2] == force]
    name, _, how = rng.choice(pool)
    P = 512 if how == "sway" else 448
    PAD = (P - W) // 2
    if how == "sway":
        items = []
        x = PAD - 8 + rng.randint(0, 8)
        while True:
            w = rng.choice((24, 32, 32, 40))
            items.append(["sheet", x, w])
            if x + w >= PAD + W + 8:
                break
            x += w + rng.randint(14, 30)
        gap = max([items[i + 1][1] - (items[i][1] + items[i][2]) for i in range(len(items) - 1)] or [16])
        amp = max(gap / 2 + 8, rng.uniform(24, 36) + tier * 0.6)
        om = rng.uniform(0.9, 1.3) * (1 + 0.015 * tier)
        return lane("gap", p=P, ph=r2(rng.uniform(0, 6.28)), it=items, sw=r2(amp), om=r2(om), nm=name)
    speed = rng.uniform(18, 28) * (1 + 0.02 * tier)
    gmax = min(56, int(speed * 2.0) + 20)
    kinds = rng.sample(["sheet24", "sheet32", "sheet40"], 3)
    items = fill_items(rng, kinds, P, 20, gmax, int(speed * 2.5) + 26)
    d = rng.choice((-1, 1)) if prev_v is None else (-1 if prev_v > 0 else 1)
    return lane("gap", v=r2(speed * d), p=P, ph=r2(rng.uniform(0, P)), it=items, nm=name)


def make_rail(rng, tier):
    cars = rng.choice((2, 3, 3, 4))
    length = 40 + 48 * cars
    speed = rng.uniform(300, 380) * min(1.3, 1 + 0.015 * tier)
    passing = (W + length + 32) / speed
    cycle = max(passing + 1.4 + 2.0, rng.uniform(6.0, 8.5) - 0.08 * tier)
    return lane("rail", tr=[r2(cycle), 1.4, length, r2(speed), r2(rng.uniform(0, cycle)), rng.choice((-1, 1))],
                nm="EXPRESS")


def make_fence(rng, tier):
    n = rng.choice((2, 3, 3, 4))
    cols = sorted(rng.sample([c for c in range(1, COLS - 1) if c != START_COL], n))
    cycle = rng.uniform(3.6, 4.6)
    opn = max(1.8, rng.uniform(2.1, 2.7) - 0.02 * tier)
    return lane("fence", gc=cols, gt=[r2(cycle), r2(opn), r2(rng.uniform(0, cycle))], nm="GATES")


def make_safe(rng, tier, row, puddles=0, blocks=0):
    ln = lane("safe")
    free = [c for c in range(COLS)]
    bl = []
    for _ in range(blocks):
        c = rng.choice(free)
        if c in (START_COL,) or c in bl:
            continue
        bl.append(c)
    pd = []
    for _ in range(puddles):
        c = rng.choice(free)
        if c not in bl and c not in pd:
            pd.append(c)
    ln["bl"] = sorted(bl)
    ln["pd"] = sorted(pd)
    return ln


# ----------------------------------------------------------------------------- stages
def pick_layout(rng, tier, focus, prev, need=""):
    pool = [lay for mt, lay in LAYOUTS if mt <= tier and lay != prev and all(ch in lay for ch in need)
            and (runs_ok(lay, MAX_RUN[tier]) or runs_ok(lay[::-1], MAX_RUN[tier]))]
    weights = []
    for lay in pool:
        w = 1.0
        if focus in lay:
            w += 3.0
        mt = next(m for m, l2 in LAYOUTS if l2 == lay)
        if mt >= tier - 2:
            w += 1.5          # freshly unlocked layouts show up more
        weights.append(w)
    lay = rng.choices(pool, weights)[0]
    flip = lay[::-1]
    if (rng.random() < 0.5 and runs_ok(flip, MAX_RUN[tier])) or not runs_ok(lay, MAX_RUN[tier]):
        lay = flip
    return lay


def runs_ok(lay, mx):
    """Hazard runs stay short, and every fence has a sidewalk (or the start) right below it to wait on."""
    run = 0
    for i, ch in enumerate(lay):
        run = run + 1 if ch != "." else 0
        if run > mx:
            return False
        if ch == "F" and i > 0 and lay[i - 1] != ".":
            return False
    return True


def harden(rng, lay, tier):
    """Later tiers turn some safe medians into extra traffic (if the hazard runs stay short enough)."""
    if tier < 10:
        return lay
    for _ in range(1 + (tier - 10) // 4):
        idx = [i for i, ch in enumerate(lay) if ch == "."]
        if not idx:
            break
        i = rng.choice(idx)
        cand = lay[:i] + "R" + lay[i + 1:]
        if runs_ok(cand, MAX_RUN[tier]) and cand.count(".") >= 2:
            lay = cand
    return lay


def build_lanes(rng, lay, tier, soft=False, sparse=1.0, boss=False, force=None):
    force = dict(force or {})
    lanes = [None] * ROWS
    lanes[0] = lane("home")
    lanes[10] = lane("start")
    prev_carrier_v = None
    for i, ch in enumerate(lay):
        row = 9 - i
        kind = CODE[ch]
        if kind == "safe":
            blocks = 0 if tier < 3 or boss else rng.choice((0, 1, 1, 2, 2, 3))
            puddles = 0 if tier < 1 else rng.choice((0, 0, 1, 1, 2)) + (1 if tier in RAIN_TIERS else 0)
            ln = make_safe(rng, tier, row, puddles, blocks)
            prev_carrier_v = None
        elif kind == "road":
            ln = make_road(rng, tier, soft=soft or ch == "r", sparse=sparse, force=force.pop("road", None))
            if tier >= 5 and not boss and rng.random() < 0.35:
                ln["pd"] = sorted(rng.sample(range(COLS), rng.choice((1, 2))))
            prev_carrier_v = None
        elif kind == "water":
            ln = make_water(rng, tier, prev_carrier_v, sparse=sparse, allow_dive=not boss, force=force.pop("water", None))
            prev_carrier_v = ln["v"]
        elif kind == "gap":
            ln = make_gap(rng, tier, prev_carrier_v, force=force.pop("gap", None))
            prev_carrier_v = ln["v"] if ln["v"] else None
        elif kind == "rail":
            ln = make_rail(rng, tier)
            prev_carrier_v = None
        elif kind == "fence":
            ln = make_fence(rng, tier)
            prev_carrier_v = None
        else:   # belt
            sp = rng.uniform(18, 30) * rng.choice((-1, 1))
            if prev_carrier_v is not None and (prev_carrier_v > 0) == (sp > 0):
                sp = -sp
            ln = lane("belt", v=r2(sp), p=384, ph=r2(rng.uniform(0, 384)), nm="BELT")
            ln["it"] = [["tray", x, 16] for x in range(8, 368, 48)]
            prev_carrier_v = sp
        lanes[row] = ln
    return lanes


def ground_spots(lanes, extra_block=()):
    """(row, col) cells a kitten / item may sit on: safe lanes and the start sidewalk (not blocked)."""
    out = []
    for r in range(1, ROWS):
        ln = lanes[r]
        if ln["t"] in ("safe", "start"):
            for c in range(COLS):
                if c in ln["bl"] or c in ln["pd"] or (r, c) in extra_block:
                    continue
                if r == 10 and abs(c - START_COL) <= 1:
                    continue
                out.append((r, c))
    return out


def platform_spots(lanes, kinds=("crate", "sheet", "fish")):
    """(row, pattern x) spots on carrier items that never sink (kittens may wait there)."""
    out = []
    for r in range(1, 10):
        ln = lanes[r]
        if ln["t"] not in ("water", "gap") or ln["dv"]:
            continue
        PAD = (ln["p"] - W) // 2
        for kind, x, w in ln["it"]:
            if kind in kinds:
                for j in range(w // 16):
                    u = x + 8 + 16 * j
                    if ln["sw"] and not (u - PAD - ln["sw"] >= 20 and u - PAD + ln["sw"] <= W - 20):
                        continue        # swaying laundry: only spots that never swing off the screen
                    out.append((r, u))
    return out


def place(rng, lanes, n_kittens, n_items, tier, kind, boxes, first=False):
    blocked = set()
    manholes = []
    safe_rows = [r for r in range(1, 10) if lanes[r]["t"] == "safe"]
    if kind == "normal" and tier >= 5 and (rng.random() < 0.55 or (first and tier == 5)):
        low = [r for r in safe_rows if r >= 6] + [10]
        high = [r for r in safe_rows if r <= 4]
        if high:
            r1 = rng.choice(low)
            r2_ = rng.choice(high)
            c1 = rng.choice([c for c in range(2, COLS - 2) if c not in lanes[r1]["bl"] and c not in lanes[r1]["pd"]
                             and not (r1 == 10 and abs(c - START_COL) <= 1)])
            c2 = rng.choice([c for c in range(2, COLS - 2) if c not in lanes[r2_]["bl"] and c not in lanes[r2_]["pd"]])
            manholes.append([r1, c1, r2_, c2])
            blocked |= {(r1, c1), (r2_, c2)}
    ground = ground_spots(lanes, blocked)
    plats = platform_spots(lanes)
    kittens = []
    used = set()
    row_count = {}
    plat_share = 0.0 if tier < 2 else min(0.45, 0.15 + 0.02 * tier)
    tries = 0
    while len(kittens) < n_kittens and tries < 400:
        tries += 1
        on_plat = plats and rng.random() < plat_share and kind == "normal"
        if on_plat:
            r, x = rng.choice(plats)
        else:
            if not ground:
                break
            r, c = rng.choice(ground)
            if kind == "normal" and r == 10 and tier >= 2 and rng.random() < 0.6:
                continue        # later on, kittens wait further up the town
            x = c * CELL + 8
        if (r, x) in used or row_count.get(r, 0) >= (2 if kind == "normal" else 4):
            continue
        if any(rr == r and abs(xx - x) < 32 for rr, xx, _ in kittens) and kind == "normal":
            continue
        used.add((r, x))
        row_count[r] = row_count.get(r, 0) + 1
        kittens.append([r, x, rng.randint(0, 5)])
    items = []
    tries = 0
    while len(items) < n_items and tries < 300:
        tries += 1
        if plats and rng.random() < 0.35:
            r, x = rng.choice(plats)
        else:
            r, c = rng.choice(ground)
            x = c * CELL + 8
        if (r, x) in used:
            continue
        used.add((r, x))
        items.append(["fish" if rng.random() < 0.55 else "yarn", r, x])
    # one power-up / clock now and then
    extra = []
    if tier >= 1 and rng.random() < 0.45:
        extra.append("clock")
    if tier >= 2 and rng.random() < 0.4:
        extra.append(rng.choice(["nip", "bell", "box", "nip", "bell"]))
    for k in extra:
        for _ in range(40):
            r, c = rng.choice(ground)
            x = c * CELL + 8
            if (r, x) not in used and r != 10:
                used.add((r, x))
                items.append([k, r, x])
                break
    return kittens, items, manholes


def pick_boxes(rng, tier):
    n = 5 if tier < 4 else 4 if tier < 12 else rng.choice((3, 4))
    for _ in range(200):
        cols = sorted(rng.sample(range(1, COLS - 1), n))
        if all(cols[i + 1] - cols[i] >= 3 for i in range(n - 1)):
            return cols
    return [2, 6, 10, 14, 17][:n]


def lamps_for(rng, lanes):
    out = []
    for r in range(0, ROWS):
        ln = lanes[r]
        if ln["t"] in ("safe", "start", "home"):
            for c in sorted(rng.sample(range(1, COLS - 1), 2 if r in (0, 10) else 1)):
                out.append([c * CELL + 8, 12 + r * CELL + 4, rng.choice((34, 38, 42)), r2(rng.uniform(0, 4))])
    return out


def build_stage(n, prev_layout=None, used_names=None):
    rng = random.Random(5150 + n * 7919)
    tier = tier_of(n)
    th = THEMES[tier]
    kind = "boss" if is_boss(n) else "bonus" if is_bonus(n) else "normal"
    st = {"n": n, "tier": tier, "kind": kind, "theme": tier, "name": "", "new": "", "line": "",
          "lanes": [], "kittens": [], "items": [], "boxes": [], "lids": [], "manholes": [], "lamps": [],
          "clock": 0, "dark": 0, "rain": 1 if tier in RAIN_TIERS else 0, "bonus": "", "boss": None, "layout": ""}
    if kind == "boss":
        bk = BOSS_ORDER[tier]
        lay = ARENAS[bk]
        st["layout"] = lay
        lanes = build_lanes(rng, lay, min(tier, 9), sparse=2.2, boss=True)
        if bk == "coon":   # the bandit's alley is full of bins to hide behind
            for r in (8, 6, 5, 4, 2):
                if lanes[r]["t"] == "safe":
                    lanes[r]["bl"] = sorted(rng.sample([c for c in range(1, COLS - 1) if c != START_COL], 2))
        if bk == "owl":
            st["dark"] = 1
        st["lanes"] = lanes
        st["boxes"] = [2, 6, 13, 17]
        cyc = tier // 6
        atk = list(BOSS_BASE[bk])
        for e in BOSS_EXTRA[bk][:min(cyc, 2)]:
            atk.insert(len(atk) - 1, e)
        hp = 3 + cyc + tier // 10 + (2 if bk == "king" else 0)
        if bk == "gulls":
            hp += 1
        st["boss"] = {"kind": bk, "name": BOSS_NAMES[bk], "title": BOSS_TITLE[bk], "hint": BOSS_HINT[bk], "hp": hp,
                      "sp": r2(min(2.0, 1 + 0.05 * tier)), "rest": r2(max(1.5, 2.7 - 0.06 * tier)),
                      "tell": r2(max(0.55, 1.05 - 0.025 * tier)), "atk": atk, "n": min(5, 2 + tier // 5),
                      "rk": SHOT_KIND[bk][0], "ck": SHOT_KIND[bk][1], "cyc": cyc}
        st["name"] = BOSS_NAMES[bk]
        st["line"] = "YOU WON'T SCARE MY KITTENS!"
        if st["dark"]:
            st["lamps"] = lamps_for(rng, lanes)
        return st
    if kind == "bonus":
        bk = "feast" if (n // 10) % 2 == 0 else "parade"
        st["bonus"] = bk
        lay = ".B.B.B.B." if bk == "feast" else ".r..r..r."
        if bk == "feast" and tier >= 4:
            lay = ".BrB.BrB."
        st["layout"] = lay
        lanes = build_lanes(rng, lay, min(tier, 9), soft=True, sparse=1.6, boss=True)
        st["lanes"] = lanes
        st["boxes"] = [2, 6, 10, 14, 18] if bk == "parade" else [3, 9, 16]
        st["clock"] = 20 if bk == "feast" else 30
        if bk == "parade":
            kittens, _, _ = place(rng, lanes, min(20, 12 + tier // 2), 0, tier, "bonus", st["boxes"])
            st["kittens"] = kittens
        names = BONUS_NAMES[bk]
        st["name"] = names[(n // 20) % len(names)]
        st["line"] = "SNACK TIME, EVERYONE!" if bk == "feast" else "LINE UP, KITTENS - PARADE!"
        return st
    # ---- normal stage
    focus = th[10]
    k = n - 1 - tier * 10        # 0..8 inside the tier
    need_codes = REQUIRE.get(tier, "") if k == 0 else ""
    for attempt in range(60):
        lay = harden(rng, pick_layout(rng, tier, focus, prev_layout, need_codes), tier)
        if runs_ok(lay, MAX_RUN[tier]) and all(ch in lay for ch in need_codes):
            break
    st["layout"] = lay
    lanes = build_lanes(rng, lay, tier, force=FORCE.get(tier) if k == 0 else None)
    st["lanes"] = lanes
    need = min(7, 2 + tier // 3 + (1 if k >= 5 else 0))
    n_items = 3 + tier // 4 + rng.randint(0, 2)
    st["boxes"] = pick_boxes(rng, tier)
    if lanes[1]["t"] == "fence":     # the gates right under the boxes line up with them
        lanes[1]["gc"] = sorted(rng.sample(st["boxes"], min(len(st["boxes"]), rng.choice((2, 3)))))
    kittens, items, manholes = place(rng, lanes, need, n_items, tier, "normal", st["boxes"], first=k == 0)
    st["kittens"], st["items"], st["manholes"] = kittens, items, manholes
    if tier >= 9 and (rng.random() < 0.6 or (tier == 9 and k == 0)):
        st["lids"] = [r2(rng.uniform(5.0, 7.0)), r2(rng.uniform(3.2, 4.2))]
    st["clock"] = int((34 + 13 * need) * (1 - 0.008 * tier))
    if tier in DARK_TIERS or (tier >= 8 and rng.random() < 0.18):
        st["dark"] = 1
        st["lamps"] = lamps_for(rng, lanes)
    if tier >= 6 and tier not in RAIN_TIERS and rng.random() < 0.15:
        st["rain"] = 1
    # a name from the most common hazard of the layout
    counts = {c: lay.count(c) for c in "RWGTF"}
    main = max("RWGTF", key=lambda c: (counts[c], c == focus))
    pool = [nm for nm in NAMES[main] if nm not in (used_names or ())] or NAMES[main]
    st["name"] = rng.choice(pool)
    if k == 0:
        st["new"] = NEW_TEXT.get(tier, "")
    st["line"] = SUSHI_LINES[(n * 7) % len(SUSHI_LINES)]
    return st


def build_campaign():
    out = []
    prev = None
    used = []
    for n in range(1, STAGES + 1):
        if n % 10 == 1:
            used = []
        st = build_stage(n, prev, used)
        if n == 1:
            st["name"] = "FIRST STEPS"
        if st["kind"] == "normal":
            prev = st["layout"]
            used.append(st["name"])
        out.append(st)
    return out


# ----------------------------------------------------------------------------- validation
def item_gaps(ln):
    it = ln["it"]
    P = ln["p"]
    gaps = []
    for i in range(len(it)):
        end = it[i][1] + it[i][2]
        nxt = it[(i + 1) % len(it)][1] + (P if i + 1 == len(it) else 0)
        gaps.append(nxt - end)
    return gaps


def validate(st):
    """Return a list of problems (empty = the stage is playable and winnable)."""
    errs = []
    lanes = st["lanes"]
    n, tier = st["n"], st["tier"]
    if len(lanes) != ROWS:
        return [f"{len(lanes)} lanes"]
    if lanes[0]["t"] != "home" or lanes[10]["t"] != "start":
        errs.append("home / start rows")
    for r, ln in enumerate(lanes):
        t = ln["t"]
        P = ln["p"]
        PAD = (P - W) // 2
        for kind, x, w in ln["it"]:
            if x < 0 or x + w > P:
                errs.append(f"row {r}: item outside the pattern")
        xs = [x for _, x, _ in ln["it"]]
        if xs != sorted(xs):
            errs.append(f"row {r}: items not sorted")
        if t in ("road", "water", "belt") or (t == "gap" and not ln["sw"]):
            if not ln["it"]:
                errs.append(f"row {r}: empty {t} lane")
                continue
            if max(w for _, _, w in ln["it"]) > PAD:
                errs.append(f"row {r}: an item is wider than the wrap margin")
            gaps = item_gaps(ln)
            if min(gaps) < 0:
                errs.append(f"row {r}: overlapping items")
            sp = abs(ln["v"])
            if t == "road" and min(gaps) < 26 + sp * 0.6:
                errs.append(f"row {r}: road gap {min(gaps)} too tight for speed {sp}")
            if t in ("water", "gap") and max(gaps) > sp * 2.6 + 28:
                errs.append(f"row {r}: water gap {max(gaps)} too wide for speed {sp}")
            if t in ("water", "gap") and min(w for _, _, w in ln["it"]) < 16:
                errs.append(f"row {r}: platform too small")
            if t in ("water", "gap") and sp < 6:
                errs.append(f"row {r}: carrier too slow")
        if t == "gap" and ln["sw"]:
            amp = ln["sw"]
            for c in range(COLS):
                x = c * CELL + 8
                ok = any(sx - PAD - amp + 4 <= x <= sx - PAD + w + amp - 4 for _, sx, w in ln["it"])
                if not ok:
                    errs.append(f"row {r}: column {c} never gets laundry")
                    break
        if t in ("water", "gap") and r > 1:
            below = lanes[r + 1]
            if below["t"] in ("water", "gap") and ln["v"] and below["v"]:
                if (ln["v"] > 0) == (below["v"] > 0) and abs(abs(ln["v"]) - abs(below["v"])) < 4:
                    errs.append(f"rows {r}/{r + 1}: carriers locked in step")
        if ln["dv"]:
            cyc, down, stag = ln["dv"]
            if down > cyc * 0.4:
                errs.append(f"row {r}: dives too long")
        if t == "rail":
            cyc, warn, length, speed, ph, d = ln["tr"]
            passing = (W + length + 32) / speed
            if cyc - warn - passing < 1.2:
                errs.append(f"row {r}: no time to cross the rails")
        if t == "fence":
            cyc, opn, ph = ln["gt"]
            if len(ln["gc"]) < 2 or opn < 1.3 or cyc - opn < 0.8:
                errs.append(f"row {r}: gates")
    # hazard runs
    lay = st["layout"]
    if st["kind"] == "normal" and not runs_ok(lay, MAX_RUN[tier]):
        errs.append(f"hazard run too long: {lay}")
    # connectivity over the cells (hazard lanes count as passable, blocks / fences do not)
    def passable(r, c):
        ln = lanes[r]
        if r == 0:
            return c in st["boxes"]
        if c in ln["bl"]:
            return False
        if ln["t"] == "fence" and c not in ln["gc"]:
            return False
        return True
    seen = {(10, START_COL)}
    todo = [(10, START_COL)]
    while todo:
        r, c = todo.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < ROWS and 0 <= cc < COLS and (rr, cc) not in seen and passable(rr, cc):
                seen.add((rr, cc))
                todo.append((rr, cc))
    for mh in st["manholes"]:
        r1, c1, r2_, c2 = mh
        if lanes[r1]["t"] not in ("safe", "start") or lanes[r2_]["t"] != "safe":
            errs.append("manhole not on a sidewalk")
        if c1 in lanes[r1]["bl"] or c2 in lanes[r2_]["bl"]:
            errs.append("manhole under a block")
    if not any((0, c) in seen for c in st["boxes"]):
        errs.append("no box can be reached")
    for r, x, coat in st["kittens"]:
        ln = lanes[r]
        if ln["t"] in ("safe", "start"):
            c = int(x // CELL)
            if x != c * CELL + 8 or (r, c) not in seen:
                errs.append(f"kitten at {r},{x} unreachable")
        elif ln["t"] in ("water", "gap"):
            if ln["dv"]:
                errs.append("kitten on a diving lane")
            if not any(sx <= x - 4 and x + 4 <= sx + w for _, sx, w in ln["it"]):
                errs.append(f"kitten at {r},{x} not on a platform")
            pad = (ln["p"] - W) // 2
            if ln["sw"] and not (x - pad - ln["sw"] >= 16 and x - pad + ln["sw"] <= W - 16):
                errs.append(f"kitten at {r},{x} swings off the screen")
            if not any((r + 1, c) in seen or (r - 1, c) in seen for c in range(COLS)):
                errs.append(f"kitten row {r} unreachable")
        else:
            errs.append(f"kitten on a {ln['t']} lane")
        if not 0 <= coat <= 5:
            errs.append("kitten coat")
    if st["kind"] == "normal":
        need = len(st["kittens"])
        if need < 2:
            errs.append("too few kittens")
        if st["clock"] < 22 + 9 * need:
            errs.append("clock too short")
        if len(st["boxes"]) < 3:
            errs.append("too few boxes")
        if st["lids"]:
            cyc, opn = st["lids"]
            if opn < 2.5 or opn > cyc:
                errs.append("lids")
    boxes = st["boxes"]
    if any(boxes[i + 1] - boxes[i] < 2 for i in range(len(boxes) - 1)) or min(boxes) < 0 or max(boxes) >= COLS:
        errs.append("box spacing")
    for k, r, x in st["items"]:
        if k not in ("fish", "yarn", "clock", "nip", "bell", "box"):
            errs.append(f"item {k}")
    if st["kind"] == "boss":
        b = st["boss"]
        if b["hp"] <= 0 or not b["atk"]:
            errs.append("boss spec")
        if not any(a in ("charge", "strike", "rest") for a in b["atk"]):
            errs.append("the boss is never vulnerable")
        if b["kind"] in ("sweepo", "coon") and "rest" not in b["atk"]:
            errs.append("rest missing")
    if st["kind"] == "bonus":
        if st["bonus"] == "parade" and len(st["kittens"]) < 10:
            errs.append("parade needs kittens")
        if st["bonus"] == "feast" and not any(ln["t"] == "belt" for ln in lanes):
            errs.append("feast needs belts")
    return errs


CAMPAIGN = build_campaign()
