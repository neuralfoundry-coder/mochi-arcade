"""WINDOW WATCH campaign: 200 stages built deterministically from curated wave patterns + seeded variation.

Every stage is plain JSON (exported to iOS through EXPORT in window_watch.py):
  n, kind (normal|bonus|boss), tier, name, new, speed, wind, treasures, events, time, bonus, boss
An event is [t, kind, x, y, target, speed, p, q]: spawn time (s), thing kind, spawn point, target treasure (0-2),
speed (px/s, already scaled for the stage) and two kind-specific numbers (sway, split height, dive x, phase ...).
validate() checks a stage is well-formed and can be defended with the paw energy a player has by then.
"""
import math
import random

STAGES = 200
SLOTS = (64, 160, 256)        # treasure centres on the windowsill
SILL = 172                    # top of the windowsill
TOPY = 14                     # things enter just under the HUD band

# kind: catch radius, points, armour (hits), base speed (px/s), harmful (splashes a treasure)
KINDS = {
    "drop": [3, 50, 1, 30, True],       # raindrop - falls straight at a bowl
    "leaf": [4, 60, 1, 22, True],       # falling leaf - sways
    "bug": [3, 80, 1, 30, True],        # buzzy gnat - zig-zags
    "dart": [3, 100, 1, 72, True],      # toy suction dart - fast, from the sides
    "bubble": [6, 70, 1, 15, True],     # soap bubble - splits into minis if left alone
    "mini": [3, 40, 1, 38, True],
    "crow": [5, 150, 1, 52, True],      # sneaky crow - cruises, caws, dives
    "hail": [3, 90, 2, 42, True],       # hailstone / acorn - takes two swats
    "moth": [4, 110, 1, 30, True],      # moth - drawn to the paw, then dives
    "rocket": [3, 150, 1, 70, True],    # festival rocket - bursts into sparks
    "spark": [2, 30, 1, 0, True],
    "snow": [5, 100, 2, 18, True],      # snowball - speeds up, two swats
    "plane": [4, 120, 1, 40, True],     # paper plane - loops, then dives
    "puff": [5, 80, 1, 13, True],       # dandelion puff - splits into seeds
    "seed": [2, 30, 1, 20, True],
    "star": [3, 200, 1, 88, True],      # shooting star - very fast
    "food": [3, 0, 1, 18, False],       # fish food - DON'T swat, it feeds the fish
    "cap": [7, 50, 1, 16, False],       # gift bubble (power-up)
    "orb": [4, 250, 1, 58, True],       # boss: thunder seed
    "feather": [2, 40, 1, 48, True],    # boss: crow captain feather
    "treat": [4, 100, 1, 40, False],    # bonus: fish cracker
    "gold": [5, 0, 1, 70, False],       # golden fish (jackpot)
    "fly": [3, 80, 1, 0, False],        # bonus: firefly
    "rise": [5, 60, 1, 30, False],      # bonus: rising bubble
}
HARMFUL = [k for k, v in KINDS.items() if v[4]]
SIDE_KINDS = ("dart", "crow", "plane", "gold")

# treasure: half width, top y, water (hp)
TREASURES = {"bowl": [11, 150, 3], "pond": [22, 158, 4], "feeder": [10, 144, 3]}
LAYOUTS = [["bowl", "bowl", "bowl"], ["bowl", "pond", "bowl"], ["feeder", "bowl", "feeder"],
           ["bowl", "feeder", "pond"], ["pond", "bowl", "feeder"]]

# name, sky top, sky bottom, curtain, deco layers, song, focus kinds
THEMES = [
    ["SUNNY MORNING", "sky", "cream", "pink", ["sun", "clouds"], "ww_sill", ["drop"]],
    ["BREEZY NOON", "blue", "sky", "mint", ["clouds"], "ww_sill", ["bug", "leaf"]],
    ["PLAYROOM AFTERNOON", "sky", "peach", "yellow", ["sun", "clouds"], "ww_sill", ["dart"]],
    ["BUBBLE BATH DAY", "lavender", "pink", "sky", ["clouds", "bubbles"], "ww_sill", ["bubble"]],
    ["CROW HOUR", "purple", "orange", "red", ["sunset"], "ww_sill", ["crow"]],
    ["NIGHT STORM", "black", "ink", "lavender", ["stars", "storm", "rain"], "ww_moon", ["drop", "hail"]],
    ["AUTUMN WIND", "lavender", "peach", "orange", ["leaves"], "ww_sill", ["leaf", "hail"]],
    ["MOONLIT NIGHT", "night", "deep", "sky", ["stars", "moon"], "ww_moon", ["moth", "bug"]],
    ["FIRST SNOW", "darkgray", "lavender", "white", ["snow"], "ww_moon", ["snow", "hail"]],
    ["SUMMER FESTIVAL", "night", "purple", "red", ["stars", "lanterns", "fireworks"], "ww_sill", ["rocket"]],
    ["CHERRY SPRING", "sky", "pink", "pink", ["clouds", "petals"], "ww_sill", ["puff", "leaf"]],
    ["RAINY SEASON", "darkgray", "gray", "teal", ["rain"], "ww_moon", ["drop", "food"]],
    ["KITE DAY", "blue", "mint", "yellow", ["clouds", "kites"], "ww_sill", ["plane"]],
    ["STARRY NIGHT", "black", "night", "lavender", ["stars", "moon"], "ww_moon", ["star", "moth"]],
    ["THUNDER NIGHT", "black", "deep", "purple", ["storm", "rain"], "ww_moon", ["hail", "drop", "star"]],
    ["HARVEST MOON", "night", "choco", "orange", ["stars", "bigmoon"], "ww_moon", ["crow", "moth"]],
    ["BLIZZARD", "darkgray", "gray", "white", ["snow", "storm"], "ww_moon", ["snow", "hail"]],
    ["FIREWORK GALA", "black", "purple", "hotpink", ["stars", "lanterns", "fireworks"], "ww_sill", ["rocket", "star"]],
    ["RAINBOW SKY", "sky", "mint", "lavender", ["rainbow", "clouds"], "ww_sill", []],
    ["MOON GATE", "black", "ink", "yellow", ["stars", "aurora", "moon"], "ww_moon", []],
    ["FIREFLY NIGHT", "night", "deep", "mint", ["stars", "moon"], "ww_moon", []],      # firefly bonus stages
]
FIREFLY_THEME = 20

# eight names per theme (the normal stages of each tier)
NAMES = [
    ["PITTER PATTER", "DEWDROP DASH", "LAZY DRIZZLE", "LEAF ON THE WIND", "SUNNY SPRINKLE", "PUDDLE PATROL",
     "MORNING YAWN", "DRIP DROP"],
    ["BUZZ OFF!", "NOON NAP", "GNAT ATTACK", "BREEZE BLOCK", "SHOO FLY", "WHIRLY LEAVES", "HUM HUM HUM",
     "SNACK TIME"],
    ["DART PARTY", "TOY TROUBLE", "SUCTION CUP", "BULLSEYE", "PLAYTIME PANIC", "FOAM FLURRY", "POP GUN POP",
     "RECESS"],
    ["SUDS UP", "SPLIT SPLAT", "BUBBLE TROUBLE", "FOAM PARTY", "RUBBER DUCK DAY", "FIZZY SKY", "SOAP OPERA",
     "SQUEAKY CLEAN"],
    ["CAW CAW CAW", "SNEAKY BEAKS", "SHINY THIEVES", "DUSK DIVERS", "ORANGE SKY", "BLACK FEATHERS",
     "CROWDED", "LAST LIGHT"],
    ["THUNDER PURR", "HAIL HAIL", "WILD WET NIGHT", "STORM WATCH", "FLASH FLASH", "BIG DROPS", "RUMBLE",
     "SOAKED"],
    ["ACORN ALERT", "GUSTY GUST", "CRUNCHY LEAVES", "MAPLE RAIN", "WINDY WINDOW", "PUMPKIN SKY",
     "FALLING FAST", "SWEATER WEATHER"],
    ["MOTH TO A PAW", "MOON BEAMS", "NIGHT FLUTTER", "OWL O'CLOCK", "SILVER SKY", "SLEEPY SHIFT",
     "LAMP LIGHT", "MIDNIGHT SNACK"],
    ["FIRST FLAKES", "SNOWBALL FIGHT", "FROSTY PAWS", "ICY WIND", "COLD NOSE", "WINTER WATCH", "HOT COCOA",
     "MITTEN WEATHER"],
    ["FESTIVAL EVE", "SPARKLER SKY", "BOOM BOOM", "LANTERN LANE", "RED ROCKETS", "TAIYAKI TIME",
     "SUMMER NIGHT", "GRAND FINALE"],
    ["PETAL STORM", "DANDELION DAY", "MAKE A WISH", "PINK BREEZE", "SEED SPREAD", "SPRING FEVER",
     "BLOSSOM BLITZ", "POLLEN PANIC"],
    ["DON'T SWAT SNACKS", "DRIZZLE DAYS", "WET WHISKERS", "FOOD DROP", "UMBRELLA WEATHER", "GRAY GRAY GRAY",
     "PUDDLE JUMP", "YUM AND SPLASH"],
    ["PAPER PLANES", "LOOP THE LOOP", "KITE STRINGS", "AIR MAIL", "SKY SCRIBBLES", "FOLD AND FLY",
     "HIGH FLYERS", "TAIL WIND"],
    ["WISHING STARS", "COMET CATCH", "SPACE DUST", "STARGAZER", "SHOOTING GALLERY", "TWINKLE TWINKLE",
     "NIGHT LIGHTS", "COSMIC CATNAP"],
    ["KA-BOOM", "ICE PELLETS", "STORM SURGE", "RATTLE THE GLASS", "ELECTRIC PURR", "NO SLEEP TONIGHT",
     "THUNDERCLAP", "DOWNPOUR"],
    ["HARVEST HUSTLE", "ORANGE MOON", "SCARECROWS", "MOONLIGHT MOTHS", "CROW CROWD", "GOLDEN FIELDS",
     "LONG NIGHT", "MOON PIE"],
    ["WHITEOUT", "BLIZZARD BLITZ", "SNOW DAY", "ICICLE SKY", "FROZEN WHISKERS", "DEEP FREEZE",
     "SNOWSTORM", "BRRRR!"],
    ["GALA OPENING", "CHAIN OF LIGHTS", "SKY FLOWERS", "STARBURST", "BIG BANG", "CONFETTI CLOUDS",
     "ROCKET RUSH", "ENCORE!"],
    ["RAINBOW ROAD", "EVERYTHING!", "COLOR STORM", "PRISM PANIC", "SEVEN COLORS", "BRIGHT SIDE",
     "SKY PARADE", "OVER THE RAINBOW"],
    ["MOON GATE", "AURORA", "LAST WATCH", "STARLIGHT STORM", "ROUND AND ROUND", "MARU'S MOMENT",
     "ONE MORE NIGHT", "DAWN IS NEAR"],
]

# first stage each kind appears in (normal stages)
UNLOCK = {"drop": 1, "leaf": 3, "bug": 11, "dart": 21, "bubble": 31, "crow": 41, "hail": 51, "moth": 71,
          "snow": 81, "rocket": 91, "puff": 101, "food": 111, "plane": 121, "star": 131}
NEW_TEXT = {
    "leaf": "NEW: FALLING LEAVES SWAY!",
    "bug": "NEW: BUZZY BUGS ZIG-ZAG!",
    "dart": "NEW: TOY DARTS FLY IN FAST!",
    "bubble": "NEW: BUBBLES SPLIT - POP THEM EARLY!",
    "crow": "NEW: CROWS CAW, THEN DIVE!",
    "hail": "NEW: HAIL NEEDS TWO SWATS!",
    "wind": "NEW: WIND PUSHES THINGS SIDEWAYS!",
    "moth": "NEW: MOTHS FOLLOW YOUR PAW!",
    "snow": "NEW: SNOWBALLS SPEED UP!",
    "rocket": "NEW: ROCKETS BURST INTO SPARKS!",
    "puff": "NEW: DANDELIONS SCATTER SEEDS!",
    "food": "NEW: DON'T SWAT FISH FOOD!",
    "plane": "NEW: PAPER PLANES LOOP AND DIVE!",
    "star": "NEW: SHOOTING STARS - SO FAST!",
}
WIND_TIERS = (6, 10, 12, 16)

BOSS_KINDS = {
    "cloud": ["GRUMBLE CLOUD", ["drizzle", "seed", "curtain"]],
    "crow": ["CAPTAIN CAW", ["feathers", "swoop", "squad"]],
    "jelly": ["WOBBLE JELLY", ["bubbles", "spray", "slam"]],
    "twister": ["GUSTY TWISTER", ["leafstorm", "acorns", "gust"]],
    "kite": ["SKY CARP KITE", ["sparks", "dash", "rockets"]],
    "moth": ["MOONLIGHT MOTH", ["dust", "mothlings", "chase"]],
    "king": ["STORM KING", ["drizzle", "seed", "curtain", "downpour"]],
}
BOSS_ORDER = ["cloud", "crow", "jelly", "twister", "kite", "moth"]
BONUS_KINDS = ["treats", "bubbles", "fireflies"]
BONUS_NAMES = {"treats": "FISH CRACKER RAIN", "bubbles": "BUBBLE PARTY", "fireflies": "FIREFLY DANCE"}


def target_point(tg, layout):
    hw, top, _ = TREASURES[layout[tg]]
    return SLOTS[tg], top + 4


def nearest_slot(x):
    return min(range(3), key=lambda i: abs(SLOTS[i] - x))


def speed_of(n):
    t, k = (n - 1) // 10, (n - 1) % 10
    return round(1.0 + 0.042 * t + 0.012 * k, 3)


def pool_for(n):
    return [k for k, s in UNLOCK.items() if s <= n]


def _r(x):
    return round(x, 1)


class Gen:
    """Builds one stage's event list."""

    def __init__(self, n, rnd, layout, sp):
        self.n, self.rnd, self.layout, self.sp = n, rnd, layout, sp
        self.tier = (n - 1) // 10
        self.ev = []

    def v(self, k):
        return _r(KINDS[k][3] * self.sp * self.rnd.uniform(0.92, 1.08))

    def add(self, t, k, tg, x=None, y=None, side=None):
        rnd = self.rnd
        if tg is None:
            tg = rnd.randrange(3)
        tx = SLOTS[tg]
        p = q = 0.0
        if k in ("dart", "crow", "plane"):
            side = side if side is not None else rnd.choice((-1, 1))
            x = -8.0 if side > 0 else 328.0
            y = y if y is not None else rnd.uniform(24, 78 if k != "dart" else 96)
            if k == "crow":
                p = min(290.0, max(30.0, tx + rnd.uniform(-50, 50)))
            elif k == "plane":
                p = min(270.0, max(50.0, tx + rnd.uniform(-60, 60)))
        elif k == "star":
            side = side if side is not None else rnd.choice((-1, 1))
            x = rnd.uniform(4, 70) if side > 0 else rnd.uniform(250, 316)
            y = float(TOPY)
        elif k == "rocket":
            x = x if x is not None else rnd.uniform(24, 296)
            y = 206.0
            p = rnd.uniform(44, 92)              # burst height
        else:
            if x is None:
                x = tx + rnd.uniform(-95, 95)
            x = min(308.0, max(12.0, x))
            y = y if y is not None else float(TOPY)
            if k in ("leaf", "seed", "food"):
                p, q = rnd.uniform(8, 18), rnd.uniform(0, 6.28)
            elif k == "bug":
                p, q = rnd.uniform(6, 11), rnd.uniform(0, 4)
            elif k == "bubble":
                p, q = rnd.uniform(84, 108), rnd.uniform(0, 6.28)
            elif k == "puff":
                p, q = rnd.uniform(74, 100), rnd.uniform(0, 6.28)
            elif k == "moth":
                p = rnd.uniform(2.4, 4.2)        # seconds spent following the paw
            elif k == "cap":
                p, q = rnd.uniform(10, 22), rnd.uniform(0, 6.28)
        self.ev.append([_r(t), k, _r(x), _r(y), tg, self.v(k), _r(p), _r(q)])

    # ---------------------------------------------------------------- wave patterns
    def wave(self, t0, k, pattern, n, gap):
        rnd = self.rnd
        if pattern == "scatter":
            t = t0
            for _ in range(n):
                self.add(t, k, None)
                t += gap * rnd.uniform(0.75, 1.3)
            return t
        if pattern == "cluster":            # same target, close together: they converge - one swat, big chain
            tg = rnd.randrange(3)
            bx = min(290, max(30, SLOTS[tg] + rnd.uniform(-70, 70)))
            for i in range(n):
                self.add(t0 + rnd.uniform(0, 0.3), k, tg, x=bx + rnd.uniform(-13, 13), y=TOPY + rnd.uniform(0, 8))
            return t0 + 0.6
        if pattern == "line":               # a curtain across the window
            for i in range(n):
                x = 24 + (272 * (i + 0.5) / n) + rnd.uniform(-6, 6)
                self.add(t0 + rnd.uniform(0, 0.15), k, nearest_slot(x), x=x)
            return t0 + 0.8
        if pattern == "sweep":              # left to right (or back)
            rev = rnd.random() < 0.5
            for i in range(n):
                f = (i + 0.5) / n
                x = 24 + 272 * (1 - f if rev else f)
                self.add(t0 + i * gap * 0.55, k, nearest_slot(x), x=x)
            return t0 + n * gap * 0.55
        if pattern == "focus":              # everything at one treasure
            tg = rnd.randrange(3)
            t = t0
            for _ in range(n):
                self.add(t, k, tg)
                t += gap * rnd.uniform(0.6, 1.0)
            return t
        if pattern == "volley":             # from one side
            side = rnd.choice((-1, 1))
            t = t0
            for _ in range(n):
                self.add(t, k, None, side=side)
                t += gap * rnd.uniform(0.8, 1.2)
            return t
        if pattern == "pincer":
            t = t0
            for i in range(n):
                self.add(t, k, None, side=1 if i % 2 == 0 else -1)
                if i % 2:
                    t += gap * 1.3
            return t + gap
        if pattern == "barrage":            # rockets across the bottom
            t = t0
            for i in range(n):
                self.add(t, k, None, x=30 + rnd.uniform(0, 260))
                t += gap * 1.4
            return t
        raise ValueError(pattern)


PATTERNS = {   # which patterns suit each kind
    "drop": ["scatter", "cluster", "line", "sweep", "focus"],
    "leaf": ["scatter", "cluster", "sweep", "line"],
    "bug": ["scatter", "cluster", "focus"],
    "dart": ["volley", "pincer"],
    "bubble": ["scatter", "line", "cluster"],
    "crow": ["volley", "pincer"],
    "hail": ["scatter", "focus", "cluster", "line"],
    "moth": ["scatter", "cluster"],
    "snow": ["scatter", "focus", "line"],
    "rocket": ["barrage"],
    "puff": ["scatter", "line"],
    "food": ["scatter"],
    "plane": ["volley", "pincer"],
    "star": ["volley", "pincer"],
}
BIG = ("bubble", "crow", "snow", "plane", "puff", "rocket", "moth", "star")


def wave_size(k, tier, rnd, pattern):
    n = 3 + tier // 4 + rnd.randint(0, 2)
    if pattern == "cluster":
        n = 3 + min(4, tier // 3) + rnd.randint(0, 1)
    if pattern == "line":
        n = 4 + min(4, tier // 4) + rnd.randint(0, 1)
    if k in BIG:
        n = max(2, (n + 1) // 2)
    return min(n, 8)


def build_normal(n, rnd, layout):
    T, k = (n - 1) // 10, (n - 1) % 10
    sp = speed_of(n)
    g = Gen(n, rnd, layout, sp)
    pool = [x for x in pool_for(n) if x != "food"]
    newest = [x for x, s in UNLOCK.items() if s == n]
    focus = [x for x in THEMES[T][6] if x in pool]
    nw = 5 + T // 4 + (1 if k >= 5 else 0)
    gap = max(0.24, 0.86 - 0.03 * T)
    rest = max(1.0, 2.6 - 0.08 * T)
    t = 1.0
    for w in range(nw):
        if newest and newest[0] != "food" and w < 2:
            kind = newest[0]
        else:
            weights = [(3 if x in focus else 1) * (2 if UNLOCK[x] > n - 30 else 1) for x in pool]
            kind = rnd.choices(pool, weights)[0]
        pat = rnd.choice(PATTERNS[kind])
        size = wave_size(kind, T, rnd, pat)
        end = g.wave(t, kind, pat, size, gap)
        if T >= 8 and rnd.random() < 0.18 + 0.01 * T and w < nw - 1:
            t = t + 0.6                     # a double wave: the next one comes right away
        else:
            t = end + rest * rnd.uniform(0.85, 1.2)
    last = max(e[0] for e in g.ev)
    # gift bubbles (power-ups) and fish food
    if n >= 2:
        for i in range(1 + (1 if T >= 3 else 0) + (1 if T >= 10 else 0)):
            g.add(_r(rnd.uniform(4, max(5, last - 3))), "cap", rnd.randrange(3), x=rnd.uniform(40, 280))
    if n >= UNLOCK["food"]:
        for i in range(2 + (1 if T >= 14 else 0)):
            g.add(_r(rnd.uniform(3, max(4, last - 2))), "food", rnd.randrange(3))
    g.ev.sort(key=lambda e: e[0])
    return g.ev, sp


def build_bonus(n, rnd):
    T = (n - 1) // 10
    kind = BONUS_KINDS[T % 3]
    ev = []
    t = 1.0
    if kind == "treats":
        while t < 17:
            m = rnd.randint(5, 8)
            bx = rnd.uniform(40, 280)
            for i in range(m):
                x = min(310, max(10, bx + rnd.uniform(-22, 22)))
                ev.append([_r(t + rnd.uniform(0, 0.4)), "treat", _r(x), float(TOPY), 0,
                           _r(40 * rnd.uniform(0.9, 1.1)), 0.0, 0.0])
            t += rnd.uniform(1.6, 2.4)
        for i in range(2):
            side = 1 if i == 0 else -1
            ev.append([_r(rnd.uniform(4, 15)), "gold", -10.0 if side > 0 else 330.0, _r(rnd.uniform(40, 90)), 0,
                       75.0, float(side), _r(rnd.uniform(0, 6))])
    elif kind == "bubbles":
        while t < 17:
            m = rnd.randint(5, 8)
            bx = rnd.uniform(40, 280)
            for i in range(m):
                x = min(310, max(10, bx + rnd.uniform(-20, 20)))
                ev.append([_r(t + rnd.uniform(0, 0.5)), "rise", _r(x), 196.0, 0, _r(34 * rnd.uniform(0.85, 1.15)),
                           _r(rnd.uniform(4, 10)), _r(rnd.uniform(0, 6.28))])
            t += rnd.uniform(1.5, 2.3)
    else:
        while t < 16:
            m = rnd.randint(6, 9)
            cx, cy = rnd.uniform(60, 260), rnd.uniform(50, 120)
            rad = rnd.uniform(12, 26)
            w = rnd.choice((-1, 1)) * rnd.uniform(1.6, 2.6)
            for i in range(m):
                ev.append([_r(t + i * 0.08), "fly", _r(cx), _r(cy), 0, _r(w), _r(rad), _r(i * 6.283 / m)])
            t += rnd.uniform(2.2, 3.0)
    ev.sort(key=lambda e: e[0])
    return ev, kind


def boss_spec(n):
    T = (n - 1) // 10
    if n == STAGES:
        kind = "king"
        name, attacks = BOSS_KINDS[kind]
        extra = ["feathers", "bubbles", "leafstorm", "sparks", "dust"]
        return {"kind": kind, "name": name, "hp": 120, "rate": 1.55, "attacks": attacks, "extra": extra,
                "tier": T, "phases": 3}
    kind = BOSS_ORDER[T % 6]
    cycle = T // 6
    name, attacks = BOSS_KINDS[kind]
    name = name + ("" if cycle == 0 else " II" if cycle == 1 else " III" if cycle == 2 else " IV")
    rnd = random.Random(n * 31 + 7)
    others = [a for b in BOSS_ORDER if b != kind for a in BOSS_KINDS[b][1] if a not in ("swoop", "dash", "slam", "chase",
                                                                                         "gust")]
    extra = rnd.sample(others, min(cycle, 2)) if cycle else []
    return {"kind": kind, "name": name, "hp": 28 + 4 * T, "rate": round(1.0 + 0.04 * T, 3), "attacks": attacks,
            "extra": extra, "tier": T, "phases": 2 if T < 6 else 3}


def build_campaign():
    out = []
    for n in range(1, STAGES + 1):
        T, k = (n - 1) // 10, (n - 1) % 10
        rnd = random.Random(n * 7919 + 13)
        lay = LAYOUTS[min(4, T // 4)]
        st = {"n": n, "tier": T, "theme": T, "treasures": lay, "speed": speed_of(n), "wind": 0.0, "new": "", "time": 0,
              "bonus": "", "boss": None, "events": []}
        if n % 10 == 0:
            st["kind"] = "boss"
            st["boss"] = boss_spec(n)
            st["name"] = st["boss"]["name"]
            if n == 10:
                st["new"] = "SWAT THE BOSS TO HURT IT!"
            # a couple of gift bubbles to help
            g = Gen(n, rnd, lay, st["speed"])
            for i in range(2 + T // 7):
                g.add(_r(8 + i * 14 + rnd.uniform(0, 6)), "cap", rnd.randrange(3), x=rnd.uniform(40, 280))
            st["events"] = g.ev
        elif n % 10 == 5:
            st["kind"] = "bonus"
            st["events"], st["bonus"] = build_bonus(n, rnd)
            st["name"] = BONUS_NAMES[st["bonus"]]
            if st["bonus"] == "fireflies":
                st["theme"] = FIREFLY_THEME
            st["time"] = 20
        else:
            st["kind"] = "normal"
            idx = k if k < 4 else k - 1
            st["name"] = NAMES[T][idx]
            for tries in range(12):
                ev, sp = build_normal(n, random.Random(n * 7919 + 13 + tries * 101), lay)
                st["events"] = ev
                if not validate(st, quick=True):
                    break
            newest = [x for x, s in UNLOCK.items() if s == n]
            if newest:
                st["new"] = NEW_TEXT.get(newest[0], "")
            if T in WIND_TIERS or (T >= 13 and rnd.random() < 0.3):
                st["wind"] = _r((10 + 0.8 * T) * (1 if n % 2 else -1))
                if n == 61:
                    st["new"] = NEW_TEXT["wind"]
            if n == 2:
                st["new"] = "SWAT GIFT BUBBLES FOR POWER-UPS!"
        out.append(st)
    return out


# ------------------------------------------------------------------------- validation
def travel_time(e, layout):
    """Rough time from spawn until a harmful thing reaches its treasure."""
    t, k, x, y, tg, v = e[:6]
    tx, ty = target_point(tg, layout)
    if k == "crow":
        return abs(e[6] - x) / v + 0.5 + math.hypot(tx - e[6], ty - y) / (v * 1.9)
    if k == "plane":
        return abs(e[6] - x) / v + 1.0 + math.hypot(tx - e[6], ty - y) / (v * 1.5)
    if k == "moth":
        return e[6] + 120 / (v * 1.5)
    if k == "rocket":
        return (y - e[6]) / v + 1.2
    if k == "snow":
        return math.hypot(tx - x, ty - y) / (v * 1.6)
    if k in ("bubble", "puff"):
        return (e[6] - y) / v + 1.5
    return math.hypot(tx - x, ty - y) / max(1.0, v)


def validate(st, quick=False):
    errs = []
    ev = st["events"]
    lay = st["treasures"]
    if len(lay) != 3 or any(x not in TREASURES for x in lay):
        errs.append("bad treasures")
    if not ev and st["kind"] != "boss":
        errs.append("no events")
    last = -1
    for e in ev:
        if len(e) != 8:
            errs.append(f"bad event {e}")
            continue
        t, k, x, y, tg, v, p, q = e
        if t < last:
            errs.append("events not sorted")
        last = t
        if k not in KINDS:
            errs.append(f"unknown kind {k}")
        if not (0 <= tg <= 2):
            errs.append(f"bad target {tg}")
        if not (-12 <= x <= 332 and -12 <= y <= 210):
            errs.append(f"spawn off screen {e}")
        if KINDS.get(k, [0, 0, 0, 0, False])[3] > 0 and v <= 0:
            errs.append(f"no speed {e}")
        if st["kind"] == "normal" and k in UNLOCK and UNLOCK[k] > st["n"]:
            errs.append(f"{k} before its stage")
    if st["kind"] == "normal":
        harm = [e for e in ev if KINDS[e[1]][4]]
        if len(harm) < 10:
            errs.append(f"too few threats ({len(harm)})")
        # defendable: the swats needed before each impact must fit the paw energy a player has by this tier
        T = st["tier"]
        emax = 4 + min(3, T // 5)
        regen = 0.6 * 0.82 ** min(3, T // 4)
        hits = sorted(e[0] + travel_time(e, lay) for e in harm)
        need = 0
        groups = []
        for e in sorted(harm, key=lambda e: e[0]):     # things spawned together at one treasure share a swat
            key = (e[4], e[1])
            if groups and groups[-1][0] == key and e[0] - groups[-1][1] < 0.35:
                groups[-1][2] += 1
                continue
            groups.append([key, e[0], 1])
            need += KINDS[e[1]][2]
        span = max(1.0, hits[-1] - 0.4) if hits else 1.0
        if need > emax + span / regen:
            errs.append(f"too many swats needed ({need} > {emax + span / regen:.0f})")
        # never more than a handful of impacts at once
        for i in range(len(hits)):
            j = i
            while j < len(hits) and hits[j] - hits[i] < 1.0:
                j += 1
            if j - i > emax + 4:
                errs.append(f"{j - i} impacts within 1s at {hits[i]:.1f}s")
                break
    return errs


CAMPAIGN = build_campaign()
