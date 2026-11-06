"""CLOUD POUNCE data: physics constants, sky themes, curated cloud chunks, the 200-stage campaign generator and
validator, boss arenas, SORA's pixel art and the game's own chiptune songs (all original).

Every stage is built here, deterministically (random.Random(seed)), from hand-made chunks of clouds, stars and
critters plus seeded variation, then validated (a reachable path of clouds from the rooftop to the moon gate).
The finished tables are EXPORTed so the iOS port (ios/MochiArcade/Games/CloudPounce*.swift) plays the same stages.
"""
import math
import random

from mochi_arcade import music, sprites

# ----------------------------------------------------------------------------- physics (shared with the game)
FW = 224                 # play field width (the field wraps around left <-> right)
CELL, ROW = 8, 12        # chunk grid: 28 columns of 8 px, rows of 12 px of altitude
COLS = FW // CELL
G = 480.0                # gravity (px/s^2)
JUMP_V = 270.0           # a normal cloud bounce (peak ~76 px)
RAIN_V = 215.0           # soggy rain cloud bounce (~48 px)
SPRING_V = 430.0         # rainbow spring cloud (~190 px)
POUNCE_V = 380.0         # pounce dive speed
POWER_V = 335.0          # bounce after landing a pounce (~117 px)
BALLOON_V = 430.0        # validation: a balloon lifts SORA about as high as a spring
BALLOON_LIFT, BALLOON_T = 150.0, 1.2   # balloon ride: rise speed and time
VX_MAX = 125.0           # air steering top speed

# cloud kinds (index = code in the exported tables)
CLOUDS = "FTMRSZGW"      # fluffy, thin (pops), moving, rain (soggy), spring (rainbow), thunder, ghost, wind
FLOOR = 8                # the rooftop at the start of a climb
K_F, K_T, K_M, K_R, K_S, K_Z, K_G, K_W = range(8)
# items: star, balloon, rocket, bell shield, parasol, magnet, milk (+1 life), golden fish
ITEMS = ("star", "balloon", "rocket", "bell", "parasol", "magnet", "milk", "goldfish")
I_STAR, I_BALLOON, I_ROCKET, I_BELL, I_PARASOL, I_MAGNET, I_MILK, I_GOLD = range(8)
# foes: puff finch (bird), paper kite, laser dot, spark
FOES = ("bird", "kite", "dot", "spark")
E_BIRD, E_KITE, E_DOT, E_SPARK = range(4)

# fish constellations: star offsets (x, altitude) and the lines between them
FISH = [
    {"pts": [(-14, 0), (-4, 7), (-4, -7), (8, 0), (15, 7), (15, -7)],
     "lines": [(0, 1), (1, 3), (3, 2), (2, 0), (3, 4), (3, 5)]},
    {"pts": [(-18, 0), (-8, 6), (5, 6), (5, -6), (-8, -6), (11, 0), (18, 8), (18, -8)],
     "lines": [(0, 1), (1, 2), (2, 5), (5, 3), (3, 4), (4, 0), (5, 6), (5, 7)]},
    {"pts": [(-9, 0), (-5, 8), (4, 8), (8, 0), (4, -8), (-5, -8), (16, 6), (16, -6)],
     "lines": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0), (3, 6), (3, 7)]},
]


def jump_peak(v):
    return v * v / (2 * G)


def reach_x(v, dy):
    """Horizontal distance SORA can safely cover while bouncing (speed v) onto a cloud dy higher (-1: too high)."""
    if dy > jump_peak(v) * 0.8:
        return -1.0
    t = (v + math.sqrt(max(0.0, v * v - 2 * G * dy))) / G
    return 0.7 * VX_MAX * t - 8


def wrapd(dx):
    """Signed horizontal distance on the wrapping field, in -FW/2 .. FW/2."""
    return (dx + FW / 2) % FW - FW / 2


# ----------------------------------------------------------------------------- sky themes (one per tier)
# name, sky at the rooftop, sky halfway, sky at the moon, panel accent, far-cloud colour
THEMES = [
    ("SUNNY ROOFTOPS", "sky", "blue", "deep", "sky", "white"),
    ("BREEZY BLUE", "mint", "sky", "blue", "mint", "white"),
    ("KITE HILLS", "teal", "sky", "purple", "lime", "white"),
    ("PINK DAWN", "peach", "pink", "purple", "pink", "cream"),
    ("THUNDER HEIGHTS", "gray", "darkgray", "ink", "yellow", "gray"),
    ("PHANTOM MIST", "lavender", "purple", "deep", "lavender", "white"),
    ("GUSTY GORGE", "teal", "blue", "ink", "mint", "sky"),
    ("LASER LOFT", "pink", "lavender", "deep", "red", "white"),
    ("FOGGY CLIMB", "cream", "gray", "ink", "cream", "white"),
    ("SPARKLE SKY", "sky", "lavender", "night", "yellow", "white"),
    ("HAIL HIGHWAY", "blue", "darkgray", "night", "sky", "gray"),
    ("SUNSET SPIRES", "orange", "hotpink", "purple", "orange", "peach"),
    ("COTTON CANDY", "pink", "lavender", "blue", "hotpink", "white"),
    ("AURORA ARC", "mint", "teal", "night", "lime", "mint"),
    ("STORM CROWN", "darkgray", "ink", "black", "yellow", "gray"),
    ("GOLDEN HOUR", "yellow", "orange", "deep", "yellow", "cream"),
    ("STARDUST TRAIL", "purple", "deep", "night", "lavender", "lavender"),
    ("COMET COAST", "blue", "deep", "black", "sky", "sky"),
    ("MILKY WAY", "deep", "night", "black", "white", "lavender"),
    ("MOON'S DOORSTEP", "ink", "night", "black", "yellow", "lavender"),
]

ADJ = ["FLUFFY", "SLEEPY", "BREEZY", "WOBBLY", "STARRY", "SNEAKY", "COZY", "SWIRLY", "PUFFY", "TWINKLY",
       "MISTY", "ZIPPY", "DREAMY", "SILVER", "BOUNCY", "WHISKER", "SOFT", "LOFTY", "VELVET", "NAPPY", "CREAMY",
       "GIDDY", "HUSHED", "SUGAR"]
NOUN = ["STEPS", "LADDER", "LOOP", "STAIRS", "HIGHWAY", "GARDEN", "TOWER", "DRIFT", "HOP", "TRAIL", "PARADE",
        "SPIRAL", "MEADOW", "ALLEY", "BRIDGE", "CASCADE", "ORCHARD", "CANYON", "RIBBON", "PILLOW", "PLUME", "NEST"]

# ----------------------------------------------------------------------------- curated chunks
# 28 columns x n rows (top row first; each row is 12 px of altitude). Runs of a cloud letter make one cloud:
#   F fluffy  T thin (pops)  M moving  R rain (soggy)  S spring  Z thunder  G ghost  W wind
#   * star  o balloon  r catnip rocket  ? capsule  $ golden fish  C fish constellation
#   b puff finch  k paper kite  l laser dot  x spark
# (name, first tier, weight, rows)
CHUNKS = [
    ("LAUNCH", 0, 0, [
        "..........FFFFFFF...........",
        "............................",
        "...*....................*...",
        "....FFFFF.........FFFFF.....",
        "............................",
        "...........FFFFFF...........",
    ]),
    ("STEPS", 0, 3, [
        "FFFFF.......................",
        "............................",
        "......*.....................",
        "........FFFF................",
        "............................",
        "..............*.............",
        "...............FFFF.........",
        "............................",
        ".....................*......",
        "......................FFFF..",
    ]),
    ("ZIGZAG", 0, 3, [
        "...FFFF.....................",
        "............................",
        "............*...............",
        "..................FFFF......",
        "............................",
        ".........*..................",
        "...FFFF.....................",
        "............................",
        "...............*............",
        "..................FFFF......",
    ]),
    ("STAR ARC", 0, 3, [
        "...........FFFFFF...........",
        ".........*........*.........",
        ".......*............*.......",
        "......*..............*......",
        "...FFFFF..........FFFFF.....",
        "............................",
        "............................",
        "..........FFFFFFFF..........",
    ]),
    ("WIDE REST", 0, 2, [
        "............*.*.*...........",
        "...........*.....*..........",
        "..FFFF................FFFF..",
        "............................",
        "............................",
        "........FFFFFFFFFFFF........",
        "............................",
        "...*......................*.",
    ]),
    ("TWIN TOWERS", 0, 3, [
        "...FFFF..............FFFF...",
        "............................",
        "....*................*......",
        "......FFFF........FFFF......",
        "............................",
        "...*..................*.....",
        "..FFFF..............FFFF....",
        "............................",
        "............................",
        "......FFFF........FFFF......",
    ]),
    ("CONSTELLATION", 0, 3, [
        ".................FFFFF......",
        "............................",
        "............................",
        "......C.....................",
        "..FFFF......................",
        "............................",
        "..............FFFFF.........",
        "............................",
        "............................",
        "...FFFFF....................",
    ]),
    ("WRAP AROUND", 0, 2, [
        "FFFF......................FF",
        "............................",
        "...*......................*.",
        "......................FFFF..",
        "............................",
        "..FFFF......................",
        "............................",
        "*..........................*",
        "FFF......................FFF",
    ]),
    ("BALLOON GAP", 0, 2, [
        "...........FFFFFF...........",
        "............................",
        "............................",
        "............................",
        "............................",
        "......o..............o......",
        "............................",
        "..........*.....*...........",
        "...FFFFF..........FFFFF.....",
    ]),
    ("PUFF LADDER", 0, 3, [
        "..........FFFFF.............",
        "............................",
        "....TTT.........*...........",
        "............................",
        "...............TTT..........",
        "........*...................",
        "......TTT...................",
        "............................",
        ".................TTT........",
        "............................",
        "..........FFFF..............",
    ]),
    ("RAINBOW HOP", 0, 3, [
        "...........FFFFFF...........",
        "............................",
        ".............*..............",
        "............................",
        ".............*..............",
        "............................",
        ".............*..............",
        "............................",
        ".............*..............",
        "............................",
        "..FFFF.......SS.......FFFF..",
        "............................",
        "........FFFF................",
    ]),
    ("STAR FIELD", 0, 2, [
        "..FFFF..........FFFF........",
        "............................",
        ".......*..*..*..............",
        "..........TTT.........*.....",
        "....*.....................*.",
        ".....................FFFF...",
        "...FFFF.....................",
        "............................",
        "...........FFFF.............",
    ]),
    ("SLIDERS", 1, 3, [
        "..........MMMM..............",
        "............................",
        "...*....................*...",
        "...............MMMM.........",
        "............................",
        "......MMMM..................",
        "............................",
        "..........*.......*.........",
        "..............FFFF..........",
    ]),
    ("BIRD LANE", 1, 3, [
        "...FFFF..............FFFF...",
        "............................",
        "............b...............",
        "...........FFFF.............",
        "............................",
        "...*................*.......",
        "...FFFF.......b.......FFFF..",
        "............................",
        "............................",
        "..........FFFFFF............",
    ]),
    ("FERRY", 1, 2, [
        "......................FFFF..",
        "............................",
        "...........*....*...........",
        "............................",
        "............MMMMM...........",
        "............................",
        "............................",
        "..FFFF......................",
    ]),
    ("FINCH FLOCK", 1, 2, [
        "..........FFFFFF............",
        "....b.......................",
        "............................",
        "..FFFF..............FFFF....",
        "..................b.........",
        ".........*..*..*............",
        "........FFFFFFFF............",
    ]),
    ("KITE GARDEN", 2, 3, [
        ".........FFFFFFF............",
        "............................",
        "..k.....................k...",
        "............................",
        "...........FFFF.............",
        "............................",
        "....*................*......",
        "...FFFF.............FFFF....",
        "............................",
        "............................",
        "...........FFFF.............",
    ]),
    ("ROCKET PAD", 2, 2, [
        "...........FFFFFF...........",
        "............................",
        "............*...............",
        "..FFFF..............FFFF....",
        "............................",
        "..........*..*..............",
        "...........FFFF.............",
        "............r...............",
        "............................",
        "......FFFF..........FFFF....",
    ]),
    ("GIFT CLOUD", 2, 2, [
        "...FFFF..............FFFF...",
        "............................",
        "............?...............",
        "...........FFFF.............",
        "............................",
        "....*.................*.....",
        "....FFFF.........FFFF.......",
    ]),
    ("DRIZZLE", 3, 3, [
        "..........FFFFFF............",
        "............................",
        "..RRRR..............RRRR....",
        "............................",
        "........*......*............",
        "..........RRRRR.............",
        "............................",
        "...*................*.......",
        "....FFFF..........FFFF......",
    ]),
    ("PUDDLE STEPS", 3, 2, [
        "...................FFFF.....",
        "............................",
        "..............RRR...........",
        "............................",
        ".........RRR................",
        "............................",
        "....RRR.........*...........",
        "............................",
        "........FFFFF...............",
    ]),
    ("THUNDER ALLEY", 4, 3, [
        ".........FFFFFF.............",
        "............................",
        "..ZZZZ.........*.....ZZZZ...",
        "............................",
        "...........FFFF.............",
        "............................",
        "....*..............*........",
        "...FFFF............FFFF.....",
        "............................",
        "..........ZZZZ..............",
    ]),
    ("STORM FRONT", 4, 2, [
        "....FFFF............FFFF....",
        "............................",
        "...........ZZZZZ............",
        "............................",
        "..*...................*.....",
        "..FFFF.......*......FFFF....",
        "............................",
        "..........FFFFFF............",
    ]),
    ("PHANTOM STEPS", 5, 3, [
        "..........FFFFF.............",
        "............................",
        "....GGGG..........GGGG......",
        "............................",
        "........*.....*.............",
        "..........GGGGG.............",
        "............................",
        "...FFFF.............FFFF....",
        "............................",
        "...........GGGG.............",
        "............................",
        "...........FFFF.............",
    ]),
    ("GUSTY", 6, 3, [
        "................FFFFF.......",
        "............................",
        ".....*......................",
        "....WWWW...........WWWW.....",
        "............................",
        "...........FFFF.............",
        "............................",
        "..*.................*.......",
        "..FFFF.............FFFF.....",
    ]),
    ("WINDMILL", 6, 2, [
        "...FFFF...........FFFF......",
        "............................",
        "..........WWWWW.............",
        "............................",
        "...*..................*.....",
        "....FFFF.........FFFF.......",
        "............................",
        "...........WWWW.............",
    ]),
    ("LASER LOBBY", 7, 3, [
        "..........FFFFFF............",
        "............................",
        "....*.......l.........*.....",
        "...FFFF.............FFFF....",
        "............................",
        "............................",
        "...........FFFF.............",
        "............................",
        "....l.......................",
        "..FFFF..............FFFF....",
    ]),
    ("SPARK RING", 9, 3, [
        "...FFFF..............FFFF...",
        "............................",
        "............................",
        "...........FFFFF............",
        ".............x..............",
        "............................",
        "..*......................*..",
        "..FFFF..............FFFF....",
        "............................",
        "...........FFFF.............",
    ]),
    ("TOWER", 2, 2, [
        "...........FFFF.............",
        "............................",
        "..b.........................",
        "...........TTTT.............",
        "...........*................",
        ".......................b....",
        "...........TTTT.............",
        "............*...............",
        "............................",
        "...........FFFF.............",
    ]),
    ("SPRING CHAIN", 3, 2, [
        "..........FFFFFF............",
        "............................",
        "....*...........*...........",
        "............................",
        "....*...........*...........",
        "............................",
        "....*...........SS..........",
        "............................",
        "...SS.......................",
        "............................",
        "...........FFFF.............",
    ]),
    ("MIXED SKY", 4, 3, [
        "...FFFF.............MMMM....",
        "............................",
        "..........*....b............",
        "...........TTTT.............",
        "............................",
        "..RRRR..............ZZZZ....",
        "............................",
        "........*.......*...........",
        "...........FFFF.............",
    ]),
    ("CONSTELLATION CLIMB", 2, 2, [
        "...........FFFF.............",
        "............................",
        "...................C........",
        "....FFFF....................",
        "............................",
        "......C.............FFFF....",
        "............................",
        "..........FFFF..............",
    ]),
]

# bonus STAR SHOWER chunks: springs, puffs and piles of stars, no critters
BONUS_CHUNKS = [
    ("SHOWER A", [
        "...FFFF.......*.......FFFF..",
        "........*...*...*...........",
        "......*.............*.......",
        "..........FFFFFF............",
        "..*......................*..",
        "...*....................*...",
        "..SS..........C.........SS..",
        "............................",
        "........FFFF....FFFF........",
    ]),
    ("SHOWER B", [
        "..........FFFFFF............",
        ".....*..*.......*..*........",
        "...*...................*....",
        "...TTT....o.......o...TTT...",
        "............................",
        "..........*.*..*.*..........",
        ".........SSS......SSS.......",
        "............................",
        "...FFFF..............FFFF...",
    ]),
    ("SHOWER C", [
        ".....FFFF.........FFFF......",
        "............................",
        "..*.*.*.*.......*.*.*.*.....",
        "............C...............",
        "...FFFF..............FFFF...",
        "............................",
        ".......*.*..SS..*.*.........",
        "............................",
        "..........FFFFFFF...........",
    ]),
]

# boss arenas: (kind letter, x, altitude, width); screen y = 200 - altitude
ARENA_BASE = [("F", 8, 24, 48), ("F", 88, 24, 48), ("F", 168, 24, 48),
              ("F", 40, 66, 40), ("F", 144, 66, 40),
              ("F", 0, 108, 32), ("F", 96, 108, 32), ("F", 192, 108, 32)]
ARENA_MODS = {   # per boss: replace clouds by index with another kind
    "owl": {6: "S"},
    "whale": {3: "M", 4: "M"},
    "kite": {5: "T", 7: "T", 6: "S"},
    "ufo": {1: "S", 3: "M", 4: "M"},
    "eclipse": {5: "G", 7: "G", 6: "S"},
}
BOSSES = {"owl": "HOOTSTORM", "whale": "BILLOWHALE", "kite": "RIBBON DRAKE", "ufo": "BLINKER SAUCER",
          "eclipse": "NOCTURNE"}
BOSS_ORDER = ["owl", "whale", "kite", "ufo", "eclipse"]
BOSS_ATTACKS = {
    "owl": ["feathers", "bolt", "gust"],
    "whale": ["spout", "geyser", "dive"],
    "kite": ["lanterns", "swoop", "ring"],
    "ufo": ["dots", "beam", "drones"],
    "eclipse": ["crescents", "starfall", "eclipse"],
}
BORROW = ["feathers", "bolt", "spout", "lanterns", "ring", "dots", "drones", "crescents", "starfall", "geyser"]

BONUS_KINDS = ["stars", "rocket", "balloons"]
BONUS_NAMES = {"stars": "STAR SHOWER", "rocket": "ROCKET RIDE", "balloons": "BALLOON BASH"}
BONUS_TIME = {"stars": 30, "rocket": 16, "balloons": 22}
ROCKET_SPEED = 210.0

# what each tier brings (shown on the first stage card of the tier)
NEW = {1: "NEW: PAWS ON THE CLOUDS!", 2: "NEW: PUFF CLOUDS POP!", 3: "NEW: RAINBOW CLOUDS BOING!",
       11: "NEW: SLIDING CLOUDS + FINCHES", 21: "NEW: KITES AND CATNIP ROCKETS!", 31: "NEW: SOGGY RAIN CLOUDS",
       41: "NEW: THUNDER CLOUDS ZAP!", 51: "NEW: GHOST CLOUDS BLINK", 61: "NEW: WIND CLOUDS + GUSTS",
       71: "NEW: LASER DOTS - DON'T CHASE!", 81: "NEW: THE FOG IS RISING!", 91: "NEW: SPARKS ORBIT CLOUDS",
       101: "NEW: HAIL STORMS - WATCH UP!", 111: "REMIX: FASTER FINCHES", 121: "REMIX: NARROW CLOUDS",
       131: "REMIX: DOUBLE WEATHER", 141: "REMIX: STORM CROWN", 151: "REMIX: GOLDEN WINDS",
       161: "REMIX: STARDUST FOG", 171: "REMIX: COMET RUSH", 181: "REMIX: EVERYTHING!",
       191: "THE MOON IS CLOSE!"}
QUIPS = ["SORA: TO THE MOON!", "SORA STRETCHES... READY!", "WHISKERS UP!", "PAWS ON THE CLOUDS!",
         "SORA: MEW! LET'S GO!", "THE MOON IS CALLING...", "TAIL HIGH, SORA!", "ONE MORE LEAP!",
         "SORA PURRS AT THE SKY", "STAR PATCH, SHINE ON!"]


# ----------------------------------------------------------------------------- generation
def tier_of(n):
    return (n - 1) // 10


def parse_chunk(rows):
    """Chunk rows -> (clouds, items, fish, foes) with x in px and altitude above the chunk base."""
    clouds, items, fish, foes = [], [], [], []
    nr = len(rows)
    for i, row in enumerate(rows):
        r = nr - 1 - i
        c = 0
        while c < len(row):
            ch = row[c]
            if ch in CLOUDS:
                c1 = c
                while c1 < len(row) and row[c1] == ch:
                    c1 += 1
                clouds.append([CLOUDS.index(ch), c * CELL, r * ROW, (c1 - c) * CELL])
                c = c1
                continue
            px, ph = c * CELL + CELL // 2, r * ROW + ROW // 2
            if ch == "*":
                items.append([I_STAR, px, ph])
            elif ch == "o":
                items.append([I_BALLOON, px, ph])
            elif ch == "r":
                items.append([I_ROCKET, px, ph])
            elif ch == "?":
                items.append([-1, px, ph])           # resolved per stage
            elif ch == "$":
                items.append([I_GOLD, px, ph])
            elif ch == "C":
                fish.append([px, ph])
            elif ch == "b":
                foes.append([E_BIRD, px, ph])
            elif ch == "k":
                foes.append([E_KITE, px, ph])
            elif ch == "l":
                foes.append([E_DOT, px, ph])
            elif ch == "x":
                foes.append([E_SPARK, px, ph])
            c += 1
    return clouds, items, fish, foes


def mix(tier):
    """Per-tier chances that a fluffy cloud becomes another kind (makes old chunks harder later).
    Ghost clouds only replace a cloud that has a partner on the same row (never the only way up)."""
    return {
        K_T: min(0.3, 0.04 + 0.016 * tier),
        K_M: 0.0 if tier < 1 else min(0.24, 0.06 + 0.012 * tier),
        K_Z: 0.0 if tier < 4 else min(0.1, 0.03 + 0.005 * tier),
        K_G: 0.0 if tier < 5 else min(0.2, 0.08 + 0.01 * tier),
        K_W: 0.0 if tier < 6 else min(0.08, 0.03 + 0.003 * tier),
    }


def cloud_ab(k, x, h, w, tier):
    """(a, b) parameters of a cloud, derived from its position (integer maths, identical on iOS):
    moving: amplitude px, speed 1/100 rad/s; thunder / ghost: phase 1/100 of a cycle; wind: push direction."""
    if k == K_M:
        amp = min((20, 28, 36, 44)[(x // 8 + h // 12) % 4], 40 + tier)
        return amp, 70 + (x * 3 + h) % (41 + 3 * tier)
    if k in (K_Z, K_G):
        return (h * 7 + x * 3) % 100, 0
    if k == K_W:
        return (1 if x * 2 + w < FW else -1), 0
    return 0, 0


def place_chunk(rows, base, rnd, tier, st, mirror, allow):
    clouds, items, fish, foes = parse_chunk(rows)
    span = max(c[1] + c[3] for c in clouds) if clouds else FW
    lo = min(c[1] for c in clouds) if clouds else 0
    shift = rnd.randint(-lo // CELL, (FW - span) // CELL) * CELL if clouds else 0
    mx = mix(tier)

    def fx(x, w=0):
        x = x + shift
        return FW - x - w if mirror else x

    rows_n = {}
    for c in clouds:
        rows_n[c[2]] = rows_n.get(c[2], 0) + 1
    for k, x, h, w in clouds:
        if k == K_F and allow:
            roll = rnd.random()
            for kk in (K_T, K_M, K_Z, K_G, K_W):
                if roll < mx[kk]:
                    if kk != K_G or rows_n[h] >= 2:
                        k = kk
                        rows_n[h] -= 1 if kk == K_G else 0
                    break
                roll -= mx[kk]
        if tier >= 6 and w >= 32 and rnd.random() < min(0.45, 0.1 + 0.03 * (tier - 6)):
            w -= 8                                         # narrower clouds later on
        st["c"].append([k, fx(x, w), base + h, w])
    for k, x, h in items:
        if k == -1:
            k = rnd.choice((I_ROCKET, I_BELL, I_BELL, I_PARASOL, I_PARASOL, I_MAGNET, I_MAGNET, I_MILK))
        if k == I_STAR and rnd.random() < 0.004 * (1 + tier // 5):
            k = I_GOLD
        st["i"].append([k, int(fx(x)) % FW, base + h])
    for x, h in fish:
        shape = rnd.randrange(len(FISH))
        st["f"].append([int(fx(x)) % FW, base + h, shape, 1 if (mirror ^ (rnd.random() < 0.5)) else 0,
                        1 if rnd.random() < 0.06 else 0])
    for k, x, h in foes:
        st["e"].append(foe(rnd, k, int(fx(x)) % FW, base + h, tier))


def foe(rnd, k, x, h, tier):
    if k == E_BIRD:
        sp = 30 + 2 * tier + rnd.randint(0, 12) + (8 if tier >= 11 else 0)
        return [k, x, h, rnd.choice((-1, 1)), sp]
    if k == E_KITE:
        return [k, x, h, rnd.choice((26, 32, 38)), rnd.randint(90, 130 + 3 * tier)]
    if k == E_DOT:
        return [k, x, h, rnd.choice((40, 50, 60)), rnd.randint(80, 120 + 2 * tier)]
    return [k, x, h, rnd.choice((22, 26)), rnd.choice((-1, 1)) * rnd.randint(150, 200 + 4 * tier)]


def pick_chunks(rnd, tier, count, first):
    pool = [c for c in CHUNKS if c[2] > 0 and c[1] <= tier]
    weights = []
    for c in pool:
        wgt = c[2]
        if c[1] == tier:
            wgt *= 3                                       # show off what's new in this tier
        elif tier - c[1] >= 6 and c[1] == 0:
            wgt *= 0.6
        weights.append(wgt)
    out = []
    if first:      # the tier's newest chunk always appears on its first stage
        newest = [c for c in pool if c[1] == tier]
        if newest:
            out.append(newest[0])
    while len(out) < count:
        c = rnd.choices(pool, weights)[0]
        if out and c[0] == out[-1][0]:
            continue
        out.append(c)
    rnd.shuffle(out)
    return out


def add_extras(rnd, st, tier, n):
    """Extra critters and weather by tier (they never land on the cloud path - validation checks)."""
    goal = st["goal"]
    lo, hi = 260, goal - 160
    if hi <= lo:
        return
    nb = 0 if tier < 1 else min(7, int(goal / 700 * (0.6 + 0.2 * tier)))
    nk = 0 if tier < 2 else min(5, int(goal / 1200 * (0.5 + 0.12 * tier)))
    nd = 0 if tier < 7 else min(3, 1 + (tier - 7) // 4)
    ns = 0 if tier < 9 else min(4, 1 + (tier - 9) // 3)
    for _ in range(nb):
        st["e"].append(foe(rnd, E_BIRD, rnd.randrange(FW), rnd.randint(lo, hi), tier))
    for k, cnt, m in ((E_KITE, nk, 30), (E_DOT, nd, 40)):
        for _ in range(cnt):
            for _try in range(12):
                x, h = rnd.randint(m, FW - m), rnd.randint(lo, hi)
                if not any(abs(h - c[2]) < 16 and abs(wrapd(x - (c[1] + c[3] / 2))) < c[3] / 2 + 10 for c in st["c"]):
                    st["e"].append(foe(rnd, k, x, h, tier))
                    break
    solid = [c for c in st["c"] if c[0] in (K_F, K_R, K_W) and lo < c[2] < hi]
    for _ in range(ns):
        if solid:
            c = rnd.choice(solid)
            e = foe(rnd, E_SPARK, c[1] + c[3] // 2, c[2] + 4, tier)
            st["e"].append(e)
    # weather
    wind = fog = hail = 0
    if tier >= 6 and (n == 61 or rnd.random() < 0.3 + 0.01 * tier):
        wind = 60 + 4 * tier
    if tier >= 8 and (n == 81 or rnd.random() < 0.28 + 0.01 * tier):
        fog = 12 + tier
    if tier >= 10 and (n == 101 or rnd.random() < 0.25 + 0.01 * tier):
        hail = 40 + 5 * tier            # hailstones per 100 s
    if tier == 13 and n % 2:            # DOUBLE WEATHER
        wind = wind or 60 + 4 * tier
        hail = hail or 40 + 5 * tier
    st["mods"] = [wind, fog, hail]


def stage_name(rnd, n):
    return f"{ADJ[rnd.randrange(len(ADJ))]} {NOUN[(n * 7 + rnd.randrange(5)) % len(NOUN)]}"


def build_normal(n, seed):
    tier = tier_of(n)
    idx = (n - 1) % 10
    rnd = random.Random(seed)
    target = min(2300, 760 + tier * 72 + idx * 24)
    st = {"n": n, "kind": "normal", "tier": tier, "c": [], "i": [], "f": [], "e": [], "mods": [0, 0, 0]}
    st["c"].append([FLOOR, 0, 0, FW])                # the rooftop
    base = 24
    place_chunk(CHUNKS[0][3], base, rnd, 0, st, rnd.random() < 0.5, False)
    base += len(CHUNKS[0][3]) * ROW
    count = 0
    plan = pick_chunks(rnd, tier, 40, idx == 0)
    allow_mix = n >= 3
    while base < target - 60:
        rows = plan[count % len(plan)][3]
        name = plan[count % len(plan)][0]
        if n < 3 and name in ("PUFF LADDER", "RAINBOW HOP"):
            count += 1
            continue
        place_chunk(rows, base, rnd, tier if allow_mix else 0, st, rnd.random() < 0.5, allow_mix)
        base += len(rows) * ROW
        count += 1
    # the summit cloud and the moon gate right above it
    st["c"].append([K_F, FW // 2 - 32, base + 12, 64])
    st["goal"] = base + 12 + 40
    for i in range(5):
        st["i"].append([I_STAR, FW // 2 - 32 + i * 16, base + 30 + (8 if i % 2 else 0)])
    add_extras(rnd, st, tier, n)
    if n == 2:      # introduce puffs
        for c in st["c"][1:]:
            if c[0] == K_F and c[3] <= 40 and rnd.random() < 0.3:
                c[0] = K_T
    if n == 3:      # introduce springs
        st["c"].append([K_S, 8, 140, 16])
    st["name"] = stage_name(rnd, n)
    st["par"] = int(st["goal"] / 42 + 10)
    return st


def build_bonus(n, seed):
    tier = tier_of(n)
    rnd = random.Random(seed)
    kind = BONUS_KINDS[((n - 5) // 10) % 3]
    st = {"n": n, "kind": "bonus", "tier": tier, "bonus": kind, "time": BONUS_TIME[kind], "c": [], "i": [],
          "f": [], "e": [], "mods": [0, 0, 0], "name": BONUS_NAMES[kind], "riv": []}
    if kind == "stars":
        st["c"].append([FLOOR, 0, 0, FW])
        base = 24
        place_chunk(CHUNKS[0][3], base, rnd, 0, st, False, False)
        base += len(CHUNKS[0][3]) * ROW
        k = 0
        while base < 1500:
            rows = BONUS_CHUNKS[(k + n) % len(BONUS_CHUNKS)][1]
            place_chunk(rows, base, rnd, 0, st, rnd.random() < 0.5, False)
            base += len(rows) * ROW
            k += 1
        st["c"].append([K_F, FW // 2 - 32, base + 12, 64])
        st["goal"] = base + 12 + 40
        for f in st["f"]:
            f[4] = 1 if rnd.random() < 0.25 else 0
    elif kind == "rocket":
        h = 160
        total = int(ROCKET_SPEED * BONUS_TIME[kind]) + 200
        while h < total:
            count = rnd.randint(10, 18)
            dh = rnd.choice((12, 14, 16))
            amp = rnd.choice((0, 30, 50, 70))
            st["riv"].append([h, count, dh, rnd.randint(50, FW - 50), amp, rnd.randint(20, 45), rnd.randint(0, 628)])
            h += count * dh + rnd.randint(40, 90)
            if rnd.random() < 0.7:
                st["i"].append([I_BALLOON, rnd.randint(20, FW - 20), h - 30])
            if rnd.random() < 0.14:
                st["i"].append([I_GOLD, rnd.randint(30, FW - 30), h - 10])
            if rnd.random() < 0.5:
                st["c"].append([K_T, rnd.randint(0, FW - 32), h - 50, 32])
        st["goal"] = total
    else:
        st["c"].append([FLOOR, 0, 0, FW])
        for x in (12, 92, 172):
            st["c"].append([K_S if x == 92 else K_F, x, 60, 40])
        for x in (52, 132):
            st["c"].append([K_F, x, 106, 40])
        st["goal"] = 99999
    st["par"] = st["time"]
    return st


def build_boss(n):
    tier = tier_of(n)
    i = n // 10 - 1                   # 0..19
    kind = BOSS_ORDER[i % 5]
    rnd = random.Random(n * 31 + 5)
    extra = []
    pool = [a for a in BORROW if a not in BOSS_ATTACKS[kind]]
    for _ in range(min(3, i // 5)):
        a = rnd.choice(pool)
        pool.remove(a)
        extra.append(a)
    st = {"n": n, "kind": "boss", "tier": tier, "c": [], "i": [], "f": [], "e": [], "mods": [0, 0, 0],
          "name": BOSSES[kind], "goal": 99999, "par": 60,
          "boss": {"kind": kind, "name": BOSSES[kind], "hp": 8 + int(i * 1.6), "rate": round(max(1.5, 3.0 - 0.075 * i), 3),
                   "speed": round(1.0 + 0.035 * i, 3), "extra": extra, "tier": tier}}
    mods = ARENA_MODS[kind]
    for j, (k, x, h, w) in enumerate(ARENA_BASE):
        k = mods.get(j, k)
        if tier >= 12 and j >= 5 and k == "F":
            w -= 8
            x += 4
        st["c"].append([CLOUDS.index(k), x, h, w])
    return st


def validate(st):
    """Errors that would make a stage unfair or unwinnable ([] = fine)."""
    errs = []
    for c in st["c"]:
        k, x, h, w = c[0], c[1], c[2], c[3]
        if not (0 <= x and x + w <= FW and w >= 8):
            errs.append(f"cloud out of field {c}")
    for it in st["i"]:
        if not (0 <= it[1] < FW):
            errs.append(f"item out of field {it}")
    if st["kind"] != "normal" and not (st["kind"] == "bonus" and st["bonus"] == "stars"):
        return errs
    # reachable path of dependable clouds (and balloons, which lift SORA ~200 px) from the rooftop to the summit
    nodes = [(c[2], c[0], c[1], c[3], cloud_ab(c[0], c[1], c[2], c[3], st["tier"])[0] if c[0] == K_M else 0)
             for c in st["c"] if c[0] in (FLOOR, K_F, K_T, K_M, K_R, K_S, K_W, K_Z)]
    nodes += [(it[2] - 6, -1, it[1] - 6, 12, 0) for it in st["i"] if it[0] == I_BALLOON]
    nodes.sort()
    ok = [False] * len(nodes)
    best = 0
    for j, (hb, kb, xb, wb, mb) in enumerate(nodes):
        if kb == FLOOR:
            ok[j] = True
            continue
        for i in range(j - 1, -1, -1):
            ha, ka, xa, wa, ma = nodes[i]
            dy = hb - ha
            if dy > 240:
                break
            if not ok[i] or dy <= 0:
                continue
            v = RAIN_V if ka == K_R else SPRING_V if ka == K_S else BALLOON_V if ka == -1 else JUMP_V
            r = reach_x(v, dy)
            if r < 0:
                continue
            d = 0.0 if ka == FLOOR else abs(wrapd((xa + wa / 2) - (xb + wb / 2)))
            if ka == FLOOR or max(0.0, d - wa / 2 - wb / 2 - ma - mb) <= r:
                ok[j] = True
                break
        if ok[j] and kb != -1:
            best = max(best, hb)
    if best < st["goal"] - 40:
        errs.append(f"summit unreachable: best {best} of {st['goal']}")
    solid = [c for c in st["c"] if c[0] in (FLOOR, K_F, K_T, K_M, K_R, K_S, K_W, K_Z)]
    # no critter parked right on top of a path cloud
    for e in st["e"]:
        if e[0] == E_SPARK:
            continue
        for c in solid:
            if abs(e[2] - c[2]) < 10 and abs(wrapd(e[1] - (c[1] + c[3] / 2))) < c[3] / 2 + 6 and e[0] != E_BIRD:
                errs.append(f"foe on a cloud {e}")
                break
    return errs


def build_stage(n):
    if n % 10 == 0:
        return build_boss(n)
    if n % 10 == 5:
        st = build_bonus(n, n * 977 + 13)
        assert not validate(st), (n, validate(st))
        return st
    for attempt in range(60):
        st = build_normal(n, n * 7919 + attempt * 104729)
        if not validate(st):
            st["seed_try"] = attempt
            return st
    raise RuntimeError(f"stage {n}: no valid layout")


def build_campaign():
    camp = []
    for n in range(1, 201):
        st = build_stage(n)
        st["new"] = NEW.get(n, "")
        # flatten the object lists for a compact export
        st["c"] = [int(v) for c in st["c"] for v in c]
        st["i"] = [int(v) for c in st["i"] for v in c]
        st["f"] = [int(v) for c in st["f"] for v in c]
        st["e"] = [int(v) for c in st["e"] for v in c]
        st["riv"] = [int(v) for c in st.get("riv", []) for v in c]
        st.pop("seed_try", None)
        camp.append(st)
    return camp


def unflat(a, k):
    return [a[i:i + k] for i in range(0, len(a), k)]


CAMPAIGN = build_campaign()

# ----------------------------------------------------------------------------- SORA's pixel art (16x16)
_HEAD = [
    "................",
    ".kk..........kk.",
    ".kpk........kpk.",
    ".kppkkkkkkkkppk.",
    ".kwwwwwwwwwwwwk.",
    "kwwwwwwwwwwvwwwk",
    "kwwwwwwwwwvvvwwk",
    "kwwwwwwwwvvvvvwk",
    "kwwwwwwwwwvvvwwk",
    "kwpwwwwppwvwvpwk",
    ".kwwwwkwwkwwwwk.",
    "..kkwwwkkwwwkk..",
]


def _put(rows, pts, ch):
    rows = [list(r) for r in rows]
    for x, y in pts:
        rows[y][x] = ch
    return ["".join(r) for r in rows]


def _eyes(rows, kind):
    if kind == "open":
        return _put(rows, [(4, 7), (4, 8), (11, 7), (11, 8)], "k")
    if kind == "wide":
        rows = _put(rows, [(3, 7), (4, 7), (3, 8), (4, 8), (11, 7), (12, 7), (11, 8), (12, 8)], "k")
        return _put(rows, [(4, 7), (12, 7)], "s")
    if kind == "happy":
        return _put(rows, [(4, 7), (3, 8), (5, 8), (11, 7), (10, 8), (12, 8)], "k")
    if kind == "shut":
        return _put(rows, [(3, 8), (4, 8), (5, 8), (10, 8), (11, 8), (12, 8)], "k")
    if kind == "dizzy":
        return _put(rows, [(3, 6), (5, 6), (4, 7), (3, 8), (5, 8), (10, 6), (12, 6), (11, 7), (10, 8), (12, 8)], "k")
    return rows


_BODY = {
    "idle": ["...kwwwwwwwwk...", "..kwwwwwwwwwwk..", "..kwwkwwwwkwwk..", "...kk......kk..."],
    "up": ["....kwwwwwwk....", "....kwwwwwwk....", "....kwkwwkwk....", ".....kk..kk....."],
    "fall": ["..kwwwwwwwwwwk..", ".kwwkwwwwwwkwwk.", ".kk..kwwwwk..kk.", "......kkkk......"],
    "star": ["kwwkwwwwwwwwkwwk", ".kkkwwwwwwwwkkk.", "...kwwkkkkwwk...", "..kwk......kwk.."],
    "ball": [".kwwwwwwwwwwwwk.", ".kwwwwwwwwwwwwk.", "..kwwwwwwwwwwk..", "...kkkkkkkkkk..."],
}


def _cat(eyes, body):
    return _eyes(_HEAD, eyes) + _BODY[body]


def _squash():
    head = _eyes(_HEAD, "happy")
    return ["................"] * 2 + head[1:4] + head[5:12] + [
        "..kwwwwwwwwwwk..", ".kwwwwwwwwwwwwk.", "kwwkwwwwwwwwkwwk", ".kk..........kk."]


ART = {
    "cp_up": [_cat("open", "up")],
    "cp_star": [_cat("happy", "star")],
    "cp_fall": [_cat("wide", "fall")],
    "cp_land": [_squash()],
    "cp_ball": [_cat("shut", "ball")],
    "cp_hurt": [_cat("dizzy", "fall")],
    "cp_happy": [_cat("happy", "idle")],
    "cp_idle": [_cat("open", "idle"), _cat("shut", "idle")],
}
sprites.ART.update(ART)

# ----------------------------------------------------------------------------- songs (original)
music.SONGS.update({
    # "Sky Purr" - the daytime climb (D major, skipping arpeggios)
    "cp_sky": {"bpm": 148, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "D5:8 F#5:8 A5:8 D6:8 C#6:8 A5:8 F#5:4  G5:8 B5:8 D6:8 B5:8 A5:4 F#5:4 "
            "E5:8 G5:8 B5:8 E6:8 D6:8 B5:8 G5:4  A5:8 G5:8 F#5:8 E5:8 A5:2 "
            "D6:8 C#6:8 B5:8 A5:8 B5:8 A5:8 F#5:4  G5:8 F#5:8 E5:8 D5:8 E5:4 A5:4 "
            "B5:8 A5:8 G5:8 B5:8 A5:8 F#5:8 D5:4  E5:8 F#5:8 G5:8 A5:8 D5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": music._bass(["D", "G", "E", "A", "B", "E", "G", "A"])},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, music.BEAT)},
    ]},
    # "Moonward" - the night climb (A minor, dreamy)
    "cp_moon": {"bpm": 140, "channels": [
        {"wave": "square", "duty": 0.125, "vol": 0.24, "decay": 0.45, "notes":
            "E5:8 A5:8 B5:8 C6:8 B5:8 A5:8 E5:4  F5:8 A5:8 C6:8 A5:8 G5:4 E5:4 "
            "D5:8 G5:8 B5:8 D6:8 C6:8 B5:8 G5:4  E5:8 G5:8 C6:8 E6:8 D6:2 "
            "C6:8 B5:8 A5:8 B5:8 C6:8 E6:8 A5:4  F5:8 A5:8 D6:8 C6:8 B5:4 A5:4 "
            "G5:8 F5:8 E5:8 D5:8 E5:8 F5:8 G5:4  B5:8 A5:8 G#5:8 B5:8 A5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": music._bass(["A", "F", "G", "C", "A", "D", "G", "E"])},
        {"wave": "drums", "vol": 1, "notes": music._drums(8, music.SPACE)},
    ]},
})
