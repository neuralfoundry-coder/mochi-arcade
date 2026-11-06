"""KITTEN PILE campaign: 200 seeded stages over 20 themed bedrooms, rivals, bosses and upgrades.

Everything here is generated deterministically and exported to iOS (kitten_pile.EXPORT), so both platforms
play exactly the same stages. validate(stage) is used by tests/test_kitten_pile.py.
"""
import random

from mochi_arcade.arcade import STAGES, is_bonus, is_boss, tier
from mochi_arcade.games import kitten_pile_core as K

# name, hue, accent, wallpaper style (0 dots, 1 stripes, 2 stars, 3 checks, 4 hearts)
THEMES = [
    ["NURSERY NOOK", "lavender", "pink", 0], ["GARDEN SHED", "lime", "yellow", 1],
    ["LIBRARY LOFT", "brown", "peach", 3], ["SUNNY SILL", "yellow", "orange", 2],
    ["TEA HOUSE", "mint", "lime", 4], ["TOY BOX", "hotpink", "yellow", 0],
    ["SNOW CABIN", "sky", "white", 2], ["BEACH HUT", "teal", "peach", 1],
    ["LANTERN FAIR", "orange", "red", 4], ["MOON ROOF", "purple", "lavender", 2],
    ["CANDY DREAM", "pink", "mint", 0], ["AUTUMN PORCH", "red", "orange", 1],
    ["BUBBLE BATH", "sky", "lavender", 3], ["RAINY ATTIC", "gray", "sky", 1],
    ["CLOUD CASTLE", "white", "lavender", 4], ["AURORA POLE", "mint", "sky", 2],
    ["STAR HARBOR", "blue", "yellow", 0], ["COMET COAST", "teal", "orange", 3],
    ["DEEP DREAM", "purple", "hotpink", 4], ["MOON PALACE", "yellow", "lavender", 2],
]

# name, coat, markings, eye colour, accessory, attacks, taunt
BOSSES = [
    ["BISCUIT BARON", "black", "white", "yellow", "tophat", ["toss", "grandpa"], "TEA TIME IS OVER!"],
    ["MADAM FLOOF", "white", "cream", "sky", "bow", ["grumpy", "fog", "toss"], "DARLING, NO NAPS!"],
    ["SHADOW SOOT", "darkgray", "black", "lime", "mask", ["dizzy", "toss", "grandpa"], "NIN-NYA!"],
    ["DJ ZOOMIES", "orange", "brown", "yellow", "phones", ["zoom", "rise", "toss"], "DROP THE BEAT!"],
    ["GRUMBLEPAW", "gray", "darkgray", "orange", "crown", ["grandpa", "rise", "grumpy"], "GET OFF MY BED!"],
    ["NEBULA", "blue", "white", "yellow", "moon", ["toss", "fog", "zoom", "dizzy", "grumpy", "grandpa", "rise"],
     "I AM THE NIGHT!"],
]
# duel rivals: name, coat, markings, eye colour, collar
RIVALS = [
    ["PEPPER", "gray", "black", "lime", "red"], ["TOFFEE", "brown", "choco", "yellow", "mint"],
    ["MAPLE", "orange", "red", "lime", "sky"], ["CLOVER", "white", "gray", "lime", "lime"],
    ["BEANS", "black", "white", "yellow", "hotpink"], ["WAFFLE", "cream", "peach", "blue", "orange"],
    ["SPROUT", "peach", "orange", "teal", "yellow"], ["MOCHA", "choco", "brown", "orange", "lavender"],
]
ATTACK_NAMES = {"toss": "PILLOW TOSS", "grandpa": "GRANDPA DROP", "grumpy": "GRUMPY RAIN", "fog": "FLUFF FOG",
                "dizzy": "DIZZY SPIN", "zoom": "ZOOMIES", "rise": "BED QUAKE"}
MODS = {"rise": "RISING BED", "dark": "LIGHTS OUT", "fast": "ZOOMIES", "five": "5 COLOURS"}

# id, name, description ("|" = line break), colour, max level
UPGRADES = [
    ["peek", "PEEK", "SEE ONE MORE|NEXT PAIR", "lavender", 2],
    ["cozy", "COZY BED", "KITTENS FALL|12% SLOWER", "sky", 3],
    ["yarn", "YARN STASH", "MORE YARN|BALLS DROP", "pink", 3],
    ["mouse", "SQUEAKY TOY", "MORE TOY MICE|BIGGER SQUEAK", "yellow", 3],
    ["fort", "PILLOW FORT", "INCOMING|PILLOWS -25%", "cream", 3],
    ["purr", "PURR POWER", "PURR METER|FILLS FASTER", "hotpink", 3],
    ["catnip", "CATNIP", "NAPS HIT|RIVALS HARDER", "lime", 4],
    ["lullaby", "LULLABY", "CHAIN POINTS|+25%", "mint", 4],
    ["guard", "NIGHT LIGHT", "SAVES A FULL|BED ONCE", "orange", 2],
    ["bell", "LUCKY BELL", "MORE GOLDEN|KITTENS", "yellow", 2],
    ["milk", "WARM MILK", "+1 LIFE", "peach", 3],
]

# Poppy's lines on the intro card ("@" = the rival's name) and after a clear
TALK = {
    "clear": ["SHH... BEDTIME, LITTLE ONES!", "FOUR IN A ROW, OFF YOU GO!", "WHO IS SLEEPY? EVERYONE!"],
    "chain": ["LET THEM TUMBLE INTO DREAMS!", "STACK THEM UP... THEN DOWN!"],
    "trigger": ["ONE LITTLE NUDGE...", "I BUILT YOU A DOMINO BED!"],
    "rescue": ["THE STAR KITTENS ARE SO TIRED!", "FIND THE STARS FOR ME!"],
    "pillow": ["WHO BUILT THIS PILLOW FORT?!", "SO MANY PILLOWS..."],
    "storm": ["HOLD ON TO YOUR NIGHTCAP!", "THUNDER? NAPS ANYWAY!"],
    "duel": ["@ WANTS A PILLOW FIGHT!", "@ WON'T GO TO BED!"],
    "boss": ["THAT IS ONE GRUMPY CAT...", "@! BEDTIME FOR YOU TOO!"],
    "snack": ["SNACK TIME! QUICK, QUICK!", "FISH FOR EVERYONE!"],
    "domino": ["WATCH THEM TUMBLE!", "NUDGE, TUMBLE, SNORE!"],
}
CHEERS = ["GOOD NIGHT, KITTENS!", "PURRFECT!", "YAWN... NEXT BED!", "SWEET DREAMS!", "ALL SNUG!"]

KIND_TITLE = {"clear": "NAP TIME", "chain": "CHAIN NAP", "trigger": "DOMINO NAP", "rescue": "STAR RESCUE",
              "pillow": "PILLOW FORT", "storm": "STORMY NIGHT", "duel": "PILLOW DUEL", "boss": "BOSS!",
              "snack": "SNACK SHOWER", "domino": "DOMINO DREAM"}

# shown on the intro card the first time something new turns up (see add_tips)
TIPS = {
    "clear": "MATCH 4 KITTENS OF ONE COLOUR!",
    "chain": "KITTENS THAT TUMBLE INTO A NEW 4 = CHAIN",
    "rescue": "STAR KITTENS: MATCH THEM TO TUCK IN",
    "snack": "BONUS! EVERY KITTEN DROPS A FISH COIN",
    "pillow": "PILLOWS GO WHEN KITTENS POP NEXT TO THEM",
    "trigger": "A CHAIN IS READY - DROP THE PAIR ON IT",
    "duel": "CHAINS FILL YOUR PURR AND HIT RIVALS",
    "boss": "POP KITTENS TO PUT THE BOSS TO SLEEP",
    "yarn": "YARN BALL: A WHOLE COLOUR FALLS ASLEEP",
    "mouse": "TOY MOUSE: SQUEAKS NEARBY PILLOWS AWAY",
    "domino": "DROP THE PAIR ON THE GLOW - TUMBLE!",
    "grandpa": "GRANDPA CAT NEEDS TWO POPS NEXT TO HIM",
    "storm": "STORMY NIGHT: OUTLAST THE PILLOW RAIN",
    "rise": "RISING BED: PILLOWS PUSH UP FROM BELOW",
    "dark": "LIGHTS OUT: ONLY THE LANTERN GLOWS",
    "five": "NEW KITTEN: CALICO! NOW 5 COLOURS",
    "fast": "ZOOMIES: THE KITTENS FALL FASTER",
}
TIP_ORDER = ["boss", "snack", "domino", "clear", "chain", "trigger", "rescue", "pillow", "duel", "storm", "five",
             "yarn", "mouse", "grandpa", "rise", "dark", "fast"]


def features(st):
    f = {st["k"]} | set(st["mods"])
    if st["yarn"]:
        f.add("yarn")
    if st["mouse"]:
        f.add("mouse")
    if any("G" in r for r in st["rows"]) or (st["rival"] and "grandpa" in st["rival"]["atk"]) or \
            (st["boss"] and "grandpa" in st["boss"]["atk"]):
        f.add("grandpa")
    return f


def add_tips(stages):
    seen = set()
    for st in stages:
        new = [k for k in TIP_ORDER if k in features(st) and k not in seen]
        st["tip"] = [TIPS[k] for k in new[:2]]
        seen |= set(new[:2])


# tier 0 is a hand-made tutorial run; later tiers shuffle these templates
TIER0 = ["clear", "chain", "clear", "rescue", "snack", "pillow", "trigger", "duel", "clear", "boss"]
POOL = ["clear", "chain", "rescue", "pillow", "duel", "storm", "trigger"]


def tier_plan(t):
    """The 8 regular stages of a tier: always a nap, a duel, a dig and a chain, then seeded extras."""
    trng = random.Random(500 + t)
    kinds = ["clear", "duel", "rescue" if t % 2 else "pillow", "trigger" if t % 3 == 1 else "chain"]
    if t >= 2 and (t % 2 == 0 or t >= 10):
        kinds.append("storm")
    while len(kinds) < 8:
        k = trng.choice(POOL if t >= 2 else POOL[:5] + POOL[6:])
        if kinds.count(k) < 2:
            kinds.append(k)
    trng.shuffle(kinds)
    return kinds


def gravity_for(t):
    return round(0.62 * 0.925 ** t, 4)


def make_pile(rng, heights, ncol, stars=0, pillows=0, grandpas=0):
    """Random settled pile with no group of 3+ of one colour (so nothing is free), junk and star kittens."""
    g = K.empty_grid()
    spots = [(x, K.ROWS - 1 - h) for x in range(K.COLS) for h in range(heights[x])]
    junk = rng.sample(spots, min(len(spots), pillows + grandpas))
    jset = {p: (K.GRANDPA if i < grandpas else K.PILLOW) for i, p in enumerate(junk)}
    for y in range(K.ROWS - 1, -1, -1):
        for x in range(K.COLS):
            if (x, y) not in spots:
                continue
            if (x, y) in jset:
                g[y][x] = jset[(x, y)]
                continue
            cols = list(range(1, ncol + 1))
            rng.shuffle(cols)
            for c in cols:
                g[y][x] = c
                if K.comp_size(g, x, y) <= 2:
                    break
            else:
                g[y][x] = K.PILLOW
    kits = [(x, y) for x, y in spots if K.is_kitten(g[y][x])]
    kits.sort(key=lambda p: -p[1])          # lowest first: stars hide deep in the pile
    deep = kits[:max(stars, len(kits) * 2 // 3)]
    for x, y in rng.sample(deep, min(stars, len(deep))):
        g[y][x] |= K.STAR
    return [r for r in K.grid_rows(g)]


def trim(rows):
    while rows and set(rows[0]) == {"."}:
        rows = rows[1:]
    return rows


def heights_for(rng, lo, hi, spawn_max=7):
    hs = [rng.randint(lo, hi) for _ in range(K.COLS)]
    hs[K.SPAWN_X] = min(hs[K.SPAWN_X], spawn_max)
    return hs


def chain_setup(rng, length, ncol):
    for _ in range(400):
        r = K.build_chain(K.KRand(rng.randrange(1, 2 ** 31)), length, ncol)
        if r:
            rows, c, x = r
            return {"rows": trim(rows), "c": c, "x": x, "len": length}
    raise RuntimeError(f"no chain of {length}")


def make_stage(n):
    t = tier(n)
    slot = (n - 1) % 10
    rng = random.Random(9000 + n * 131)
    if is_boss(n):
        kind = "boss"
    elif is_bonus(n):
        kind = "snack" if t % 2 == 0 else "domino"
    elif t == 0:
        kind = TIER0[slot]
    else:
        kind = tier_plan(t)[slot if slot < 4 else slot - 1]
    st = {"n": n, "k": kind, "goal": 0, "ncol": 4, "g": gravity_for(t), "rows": [], "mods": [], "lim": 0,
          "par": 0, "yarn": 0.0, "mouse": 0.0, "rival": None, "boss": None, "setups": [], "tip": [],
          "rain": 0.0, "rainN": 0, "rise": 0.0, "twins": False}
    # colours: 3 for the first lessons, calico (5) joins from tier 5
    five = {5: 30, 6: 30, 7: 35, 8: 40, 9: 40}.get(t, 0 if t < 5 else 50 if t < 15 else 70)
    if n in (1, 2):
        st["ncol"] = 3
    elif kind not in ("snack", "domino") and (n == 51 or rng.randrange(100) < five):
        st["ncol"] = 5
        st["mods"].append("five")
    # specials: yarn from stage 11, toy mice from 13
    if n >= 11:
        st["yarn"] = 0.03 + 0.002 * t
    if n >= 13:
        st["mouse"] = 0.025 + 0.002 * t
    if n == 11:
        st["yarn"] = 0.12
    if n == 13:
        st["mouse"] = 0.12
    # modifiers on the regular stages
    if kind in ("clear", "chain", "rescue", "pillow"):
        if (t >= 3 and rng.randrange(100) < 25) or n == 31:
            st["mods"].append("rise")
            st["rise"] = round(max(7.0, 15 - t * 0.35), 2)
        if (t >= 4 and rng.randrange(100) < 22) or n == 41:
            st["mods"].append("dark")
        if (t >= 6 and rng.randrange(100) < 25) or n == 61:
            st["mods"].append("fast")
            st["g"] = round(st["g"] * 0.7, 4)
    nc = st["ncol"]
    if kind == "clear":
        st["goal"] = {1: 16, 3: 24, 9: 30}.get(n, min(80, 22 + t * 3 + rng.randrange(9)))
        st["par"] = st["goal"] * 2 + 10
        if t >= 2 and rng.randrange(100) < 40:
            st["rows"] = trim(make_pile(rng, heights_for(rng, 0, 2 + t // 6), nc, 0, rng.randrange(3), 0))
    elif kind == "chain":
        st["goal"] = 2 + (t >= 3) + (t >= 9) + (t >= 15)
        st["par"] = 50 + st["goal"] * 15
    elif kind == "trigger":
        ln = min(9, 3 + t // 3)
        su = chain_setup(rng, ln, nc)
        st["rows"], st["setups"] = su["rows"], [su]
        st["goal"] = ln
        st["par"] = 25
    elif kind == "rescue":
        stars = min(6, 2 + t // 4)
        st["goal"] = stars
        hs = heights_for(rng, 2 + min(4, t // 4), 4 + min(4, t // 3))
        junk = 0 if t < 1 else rng.randrange(1 + t // 3)
        st["rows"] = trim(make_pile(rng, hs, nc, stars, junk, 1 if t >= 2 and rng.randrange(2) else 0))
        st["par"] = 30 + stars * 15
    elif kind == "pillow":
        p = min(30, 6 + t * 2)
        gp = 0 if t < 2 else min(6, t // 2)
        hs = heights_for(rng, 2 + min(4, t // 4), 4 + min(4, t // 3))
        while sum(hs) < p + gp + 4:
            i = rng.randrange(K.COLS)
            if hs[i] < (7 if i == K.SPAWN_X else 8):
                hs[i] += 1
        st["rows"] = trim(make_pile(rng, hs, nc, 0, p, gp))
        st["goal"] = sum(r.count("P") + r.count("G") for r in st["rows"])
        st["par"] = 30 + st["goal"] * 3
    elif kind == "storm":
        st["lim"] = min(70, 35 + t * 2)
        st["goal"] = st["lim"]
        st["rain"] = round(max(4.5, 9 - t * 0.25), 2)
        st["rainN"] = min(10, 3 + t // 3)
    elif kind == "duel":
        r = (n * 7 + t) % len(RIVALS)
        atk = ["toss"] + (["grumpy"] if t >= 4 else []) + (["grandpa"] if t >= 8 else [])
        st["rival"] = {"id": r, "hp": 36 + t * 16, "every": round(max(4.0, 9.5 - t * 0.28), 2),
                       "pow": 2 + t // 2, "atk": atk}
        st["par"] = 40 + t * 3
    elif kind == "boss":
        bid = 5 if n in (100, 200) else t % 5
        atk = list(BOSSES[bid][5])
        if t >= 10 and bid != 5:
            extra = BOSSES[(bid + 2) % 5][5][0]
            if extra not in atk:
                atk.append(extra)
        hp = 60 + t * 24 + (60 if n >= 100 else 0) + (60 if n == 200 else 0)
        st["boss"] = {"id": bid, "hp": hp, "every": round(max(3.2, 7.5 - t * 0.22), 2),
                      "pow": 3 + t // 2, "atk": atk}
        st["ncol"] = 5 if t >= 15 else 4
        st["mods"] = ["five"] if t >= 15 else []
        st["par"] = 60 + t * 4
    elif kind == "snack":
        st["ncol"] = 3
        st["lim"] = 30
        st["g"] = 0.3
        st["twins"] = True
    elif kind == "domino":
        base = 3 + t // 4
        st["setups"] = [chain_setup(rng, min(10, base + i), 4) for i in range(4)]
        st["rows"] = st["setups"][0]["rows"]
        st["lim"] = 45
        st["g"] = 0.4
    return st


def validate(st):
    """Problems with a generated stage (empty list = fine)."""
    out = []
    k = st["k"]
    g = K.parse_rows(st["rows"]) if st["rows"] else K.empty_grid()
    if len(st["rows"]) > K.ROWS or any(len(r) != K.COLS for r in st["rows"]):
        out.append("bad rows")
        return out
    if K.find_groups(g):
        out.append("starts with a group")
    after = [row[:] for row in g]
    if K.apply_gravity(after):
        out.append("floating cells")
    if K.col_height(g, K.SPAWN_X) > 9:
        out.append("spawn column too tall")
    if any(K.kcolor(c) > st["ncol"] for row in g for c in row):
        out.append("colour outside the stage palette")
    if not 0.05 < st["g"] < 1.0:
        out.append("gravity")
    if k == "rescue":
        stars = K.count_cells(g, lambda c: K.is_kitten(c) and c & K.STAR)
        if stars != st["goal"] or stars < 1:
            out.append("star count")
    if k == "pillow":
        junk = K.count_cells(g, K.is_junk)
        if junk != st["goal"] or junk < 3:
            out.append("pillow count")
    if k in ("trigger", "domino"):
        if not st["setups"]:
            out.append("no setups")
        for su in st["setups"]:
            if K.chain_of(su["rows"], su["c"], su["x"]) < su["len"]:
                out.append(f"setup does not chain {su['len']}")
        if k == "trigger" and st["setups"][0]["len"] < st["goal"]:
            out.append("trigger shorter than the goal")
    if k in ("clear", "chain") and st["goal"] < 2:
        out.append("goal")
    if k == "duel" and not st["rival"]:
        out.append("no rival")
    if k == "boss" and not st["boss"]:
        out.append("no boss")
    if k in ("storm", "snack", "domino") and st["lim"] <= 0:
        out.append("no time limit")
    return out


_CACHE = []


def stages():
    """All 200 stages (generated on first use: importing the module stays instant for the game carousel)."""
    if not _CACHE:
        _CACHE.extend(make_stage(n) for n in range(1, STAGES + 1))
        add_tips(_CACHE)
    return _CACHE
