"""BOUNCE BUN campaign: 200 stages built from a curated pattern library plus seeded variation.

Everything here is deterministic (random.Random(seed)), so the desktop game and the iOS port (which reads
the exported table, see EXPORT in bounce_bun.py) play exactly the same stages.

Brick codes (18 columns per row, up to 13 rows):
  c p m l b  snack bricks (cookie, candy, mint, lemon, berry)  - 1 hit
  h          chocolate - 2 hits          H  fudge - 3 hits
  t          tin - never breaks          $  golden brick - 3 hits, JACKPOT
  x          gumdrop bomb - blows up its neighbours
  ?          gift box - always drops a capsule
  r          jelly - grows back a few seconds after it pops
  k / L      key / lock - locks only break after the key is popped
  *          bumper - unbreakable, kicks the gumball
  o / O      portal pairs - the gumball warps to the twin portal
  C          coin (bonus stages)
"""
import random

COLS = 18
MAX_ROWS = 13
BASIC = "cpmlb"
BREAKABLE = set("cpmlbhH$x?rkLC")      # L counts: it breaks once its key is gone
SOLID = set("t*")                       # never break
NOT_BRICK = set(".oO")

# tiers: name, background a/b, background pattern (0 checker 1 stripes 2 dots 3 tiles 4 scallops), wall colour,
# and the "NEW!" line shown on the first stage that introduces something
THEMES = [
    ("COOKIE KITCHEN", "choco", "brown", 0, "peach", ""),
    ("CANDY COUNTER", "ink", "deep", 1, "pink", "NEW: GIFT BOXES ALWAYS DROP A CAPSULE"),
    ("GUMDROP GARDEN", "night", "ink", 2, "lime", "NEW: GUMDROP BOMBS POP THEIR NEIGHBOURS"),
    ("CONVEYOR BAKERY", "darkgray", "ink", 3, "yellow", "NEW: SLIDING SNACK ROWS"),
    ("JELLY LAB", "deep", "ink", 2, "mint", "NEW: JELLY GROWS BACK - BE QUICK!"),
    ("PASTRY VAULT", "choco", "night", 3, "orange", "NEW: POP THE KEY TO OPEN THE LOCKS"),
    ("PINBALL PARLOR", "night", "deep", 4, "hotpink", "NEW: BUMPERS KICK THE GUMBALL"),
    ("PORTAL PANTRY", "ink", "night", 1, "sky", "NEW: PORTALS WARP THE GUMBALL"),
    ("FUDGE FACTORY", "ink", "deep", 4, "cream", "NEW: FUDGE TAKES THREE HITS"),
    ("MIDNIGHT OVEN", "night", "black", 0, "lavender", "NEW: SOME SNACKS CREEP DOWNWARDS"),
    ("FROSTING FJORD", "deep", "ink", 4, "sky", "EVERYTHING MIXES FROM HERE ON!"),
    ("CARAMEL CAVES", "choco", "brown", 2, "orange", ""),
    ("SPRINKLE STORM", "deep", "night", 1, "yellow", ""),
    ("MARSHMALLOW MIST", "darkgray", "deep", 2, "white", ""),
    ("WAFFLE WORKS", "brown", "choco", 0, "yellow", ""),
    ("TOFFEE TOWER", "night", "choco", 3, "peach", ""),
    ("MOCHI MOON", "night", "ink", 2, "cream", ""),
    ("PRALINE PALACE", "deep", "purple", 3, "pink", ""),
    ("COMET CONFECTION", "black", "night", 1, "mint", ""),
    ("STAR BAKERY", "ink", "night", 4, "yellow", "THE LAST BAKERY - GOOD LUCK!"),
]

# the hand-made stages of BOUNCE BUN 0.1 (kept as the opening stages)
ORIGINALS = [
    ("COOKIE JAR", ["..................", ".cccccccccccccccc.", ".pppppppppppppppp.", ".llllllllllllllll.",
                    ".mmmmmmmmmmmmmmmm.", ".bbbbbbbbbbbbbbbb."]),
    ("SWEETHEART", ["...ppp......ppp...", "..ppppp....ppppp..", ".pppppppp.ppppppp.", ".pppppppppppppppp.",
                    "..pppppppppppppp..", "...pppppppppppp...", "....pppppppppp....", ".....pppppppp.....",
                    "......pppppp......", ".......pppp......."]),
    ("KITTY CAKE", ["..h............h..", ".hhh..........hhh.", ".hhhhhhhhhhhhhhhh.", ".hcccccccccccccch.",
                    ".hccbbccccccbbcch.", ".hcccccccccccccch.", ".hccccccppcccccch.", ".hcccpccccccpccch.",
                    ".hhhhhhhhhhhhhhhh."]),
    ("TIN FORT", ["tttt..........tttt", "tllt..........tllt", "tllt.mmmmmmmm.tllt", "t..t.mbbbbbbm.t..t",
                  ".....mbhhhhbm.....", ".....mbbbbbbm.....", ".....mmmmmmmm.....", "..................",
                  "...tttt....tttt..."]),
    ("RAINBOW", ["p.................", "pl................", "plm...............", "plmb..............",
                 "plmbc.............", ".lmbcp............", "..mbcpl...........", "...bcplm..........",
                 "....cplmb.........", ".....plmbcplmbcplm"]),
    ("MOCHI FACE", [".....cccccccc.....", "...cccccccccccc...", "..cccccccccccccc..", ".cccbbcccccccbbccc",
                    ".cccbbcccccccbbccc", ".ccpccccccccccpccc", ".ccccccchhccccccc.", "..cccccccccccccc..",
                    "...cccccccccccc..."]),
    ("CHECKERS", ["h.h.h.h.h.h.h.h.h.", ".l.l.l.l.l.l.l.l.l", "m.m.m.m.m.m.m.m.m.", ".b.b.b.b.b.b.b.b.b",
                  "p.p.p.p.p.p.p.p.p.", ".h.h.h.h.h.h.h.h.h", "c.c.c.c.c.c.c.c.c."]),
    ("CANDY VAULT", ["tttttttttttttttttt", "t................t", "t.hhhhhhhhhhhhhh.t", "t.hpppppppppppph.t",
                     "t.hpllllllllllph.t", "t.hpppppppppppph.t", "t.hhhhhhhhhhhhhh.t", "t................t",
                     "tttttt......tttttt"]),
]

# pixel pictures drawn in snack bricks. Symmetric ones are written as the left half (9 columns, mirrored).
HALF_PICS = [
    ("CUPCAKE", ["........p", ".......pp", ".....pmpp", "...pppppp", "..ppppmpp", "..ppppppp", "...hchchc",
                 "...hchchc", "....hchch", "....hchch"]),
    ("ICE CREAM", ["....mmmmm", "...mmmmmm", "..mmbmmmm", "..mmmmmmm", "...pppppp", "....ppppp", ".....lclc",
                   "......lcl", ".......lc", "........l"]),
    ("DONUT", ["....ccccc", "..ccppppp", ".cppppbpp", ".cpppp...", ".cppp....", ".cpppp...", ".ccppppbp",
               "..ccccccc", "....ccccc"]),
    ("BUNNY", ["....cc...", "...cpc...", "...cpc...", "..ccccccc", ".cccccccc", ".ccbccccc", ".ccbccccc",
               ".pccccccp", "..ccccccc", "...cccccc"]),
    ("FROG", ["..mmm....", ".mbbmm...", ".mbbmmmmm", ".mmmmmmmm", "mmmmmmmmm", "mmhmmmmmm", "mmmhhhhhh",
              ".mmmmmmmm", "..mm..mmm"]),
    ("BEAR", [".hh......", "hhhh.....", "hhhhhhhhh", ".hhhhhhhh", ".hhbhhhhh", ".hhhhhhhh", ".hhhhhccc",
              "..hhhhcbc", "...hhhccc", "....hhhhh"]),
    ("MUSHROOM", [".....pppp", "...pppppp", "..ppcpppp", ".pppppppc", ".pcppppcc", ".pppppppp", "....ccccc",
                  "....ccbcc", "....ccccc", ".....cccc"]),
    ("CHERRIES", ["........l", ".......l.", "......l..", ".....l...", "....l....", "..pp.....", ".pppp....",
                  ".ppcp....", ".pppp....", "..pp....."]),
    ("STRAWBERRY", ["......mmm", "....mmmmm", "...pppppp", "..pplpppp", "..ppppppp", "..ppppplp", "...pppppp",
                    "....pplpp", ".....pppp", ".......pp"]),
    ("ONIGIRI", ["........c", ".......cc", "......ccc", ".....cccc", "....ccccc", "...cccccc", "..ccccccc",
                 "..ccchhhh", ".cccchhhh", ".cccchhhh"]),
    ("STAR", ["........l", ".......ll", ".......ll", "lllllllll", ".llllllll", "...llllll", "...llllll",
              "..lllllll", "..lll..ll", ".ll......"]),
    ("FLOWER", ["......pp.", ".....pppp", "..pp.pppp", ".pppppppp", ".ppppplll", "..pppplll", ".pppppppp",
                "..pp.pppp", ".....pppp", "......pp."]),
    ("GHOST", [".....llll", "...llllll", "..lllllll", "..llbblll", "..llbblll", "..lllllll", "..lllllpl",
               "..lllllll", "..lllllll", "..l.ll.ll"]),
    ("OCTOPUS", [".....pppp", "...pppppp", "..ppppppp", "..ppbbppp", "..ppbbppp", "..ppppppp", "...pppppp",
                 "..pp.pp.p", ".pp.pp..p", ".p..p...p"]),
    ("CROWN", [".l.......", ".ll...l..", ".lll.lll.", ".llllllll", ".llbllllp", ".llllllll", ".hhhhhhhh"]),
    ("PUDDING", ["......hhh", ".....hhhh", "....lllll", "...llllll", "...llllll", "..lllllll", "..lllllll",
                 ".cccccccc"]),
    ("GINGER HOUSE", ["........h", ".......hh", "......hhh", ".....hhhh", "....hhhhh", "...cccccc", "...cpcccc",
                      "...cpccll", "...ccccll", "...ccccll"]),
    ("BUTTERFLY", ["mm.......", "mmm......", "mmbm....h", "mmmmm...h", ".mmmmm..h", "..mmmm..h", ".pppp...h",
                   "ppppp...h", "pppp.....", ".pp......"]),
]
FULL_PICS = [
    ("WHALE", ["..............b...", ".............bbb..", "....bbbbbbb...b...", "..bbbbbbbbbbb.....",
               ".bbbcbbbbbbbbb..bb", ".bbbbbbbbbbbbbbbb.", ".bbbbbbbbbbbbbbb..", "..mmmmmmmmmmmmb...",
               "...mmmmmmmmmm....."]),
    ("FISH", ["......pppp........", "....pppppppp....pp", "..ppcpppppppp..ppp", ".pppppppppppppppp.",
              ".ppppppppppppppp..", "..pppppppppppp.ppp", "....pppppppp....pp", "......pppp........"]),
    ("BIRDIE", [".....mmmm.........", "...mmmmmmmm.......", "..mmmbmmmmmm......", ".lmmmmmmmmmmm.....",
                "lllmmmmmmmmmmmm...", ".lmmmmmmmmmmmmmmm.", "...mmmmmmmmmmmmm..", ".....mmmmmmmm.....",
                "......l...l......."]),
    ("SNAIL", ["..........b.....b.", "..........b.....b.", "...hhhh...bb...bb.", "..hllllh..bbbbbbb.",
               ".hlhhhllh.bcbbbcb.", ".hlhllhlh.bbbbbbb.", ".hlhhlhlhbbbbbbbb.", ".hllllllhbbbbbbb..",
               "bbbbbbbbbbbbbbb..."]),
    ("TEAPOT", [".......ll.........", "......llll........", "....pppppppp......", "...pppppppppp...p.",
                ".pppcpppppppppp.p.", "p..ppppppppcpppp..", "p..pppppppppppp...", ".p.pppppppppppp...",
                "..ppppppppppppp...", "....pppppppppp...."]),
]

PICTURES = list(ORIGINALS)
for _n, _half in HALF_PICS:
    PICTURES.append((_n, [(r + r[::-1])[:COLS].ljust(COLS, ".") for r in _half]))
PICTURES.extend(FULL_PICS)

# ----------------------------------------------------------------------------- bosses
BOSSES = ["cake", "donut", "jar", "robot", "whale"]
BOSS_NAMES = {"cake": "CAKE CASTLE", "donut": "JELLY DONUT", "jar": "COOKIE JAR", "robot": "GINGER-BOT",
              "whale": "CANDY WHALE"}
BOSS_ATTACKS = {"cake": "aimed", "donut": "drop", "jar": "spread", "robot": "beam", "whale": "arc"}
RANKS = ["", " II", " III", " IV"]


# ----------------------------------------------------------------------------- helpers
def _grid(nrows):
    return [["."] * COLS for _ in range(nrows)]


def _rows(g):
    return ["".join(r) for r in g]


def _mirror(g):
    for r in g:
        for c in range(COLS // 2):
            r[COLS - 1 - c] = r[c]
    return g


def _kinds(rng, n):
    k = list(BASIC)
    rng.shuffle(k)
    return k[:n]


# ----------------------------------------------------------------------------- shape generators
def gen_stripes(rng, nrows, tier):
    ks = _kinds(rng, 5)
    gap = rng.choice([0, 0, 2, 3])
    g = _grid(nrows)
    for r in range(nrows):
        k = ks[r % len(ks)]
        for c in range(COLS):
            if gap and c % (gap + 3) == gap + 2:
                continue
            if c in (0, COLS - 1) and rng.random() < 0.5:
                continue
            g[r][c] = k
    return "SNACK STRIPES", _mirror(g)


def gen_pyramid(rng, nrows, tier):
    ks = _kinds(rng, 3)
    inv = rng.random() < 0.5
    g = _grid(nrows)
    for r in range(nrows):
        rr = nrows - 1 - r if inv else r
        half = min(9, 1 + rr * 9 // max(1, nrows - 1))
        for c in range(9 - half, 9):
            g[r][c] = ks[(rr // 2) % len(ks)]
    return ("UPSIDE CAKE" if inv else "LAYER CAKE"), _mirror(g)


def gen_diamond(rng, nrows, tier):
    ks = _kinds(rng, 3)
    g = _grid(nrows)
    mid = (nrows - 1) / 2
    for r in range(nrows):
        d = abs(r - mid) / max(1, mid)
        half = int(round(9 * (1 - d)))
        for c in range(9 - max(1, half), 9):
            ring = int(abs(r - mid) + (8 - c)) // 2
            g[r][c] = ks[ring % len(ks)]
    return "SUGAR GEM", _mirror(g)


def gen_rings(rng, nrows, tier):
    ks = _kinds(rng, 4)
    tin = tier >= 1 and rng.random() < 0.5
    g = _grid(nrows)
    for r in range(nrows):
        for c in range(1, 9):
            d = min(r, nrows - 1 - r, c - 1)
            g[r][c] = ks[d % len(ks)]
            if tin and d == 0 and not (r == nrows - 1 and c >= 6):
                g[r][c] = "t"
    return "SWEET RINGS", _mirror(g)


def gen_checker(rng, nrows, tier):
    ks = _kinds(rng, 2)
    g = _grid(nrows)
    w = rng.choice([1, 2])
    for r in range(nrows):
        for c in range(COLS):
            if ((r // 1) + (c // w)) % 2 == 0:
                g[r][c] = ks[(r // 2) % 2]
    return "CHECKERBOARD", g


def gen_columns(rng, nrows, tier):
    ks = _kinds(rng, 3)
    g = _grid(nrows)
    caps = tier >= 1 and rng.random() < 0.6
    for c in range(1, 9):
        if c % 3 == 0:
            continue
        top = rng.randint(0, 2)
        for r in range(top, nrows):
            g[r][c] = ks[c % len(ks)]
        if caps and c % 3 == 1:
            g[top][c] = "t"
    return "CANDY PILLARS", _mirror(g)


def gen_waves(rng, nrows, tier):
    import math
    ks = _kinds(rng, 4)
    g = _grid(nrows)
    thick = rng.choice([2, 3])
    for band in range(0, nrows, thick + 2):
        for c in range(COLS):
            y0 = band + int(round(math.sin(c * 0.7) * 1.2 + 1))
            for r in range(y0, min(nrows, y0 + thick)):
                g[r][c] = ks[(band // (thick + 2)) % len(ks)]
    return "CREAM WAVES", g


def gen_zigzag(rng, nrows, tier):
    ks = _kinds(rng, 3)
    g = _grid(nrows)
    for r in range(nrows):
        for c in range(COLS):
            if (c + r) % 6 < 3 if (r // 3) % 2 == 0 else (c - r) % 6 < 3:
                g[r][c] = ks[(r // 3) % len(ks)]
    return "ZIGZAG ROLL", g


def gen_blob(rng, nrows, tier):
    ks = _kinds(rng, 3)
    g = _grid(nrows)
    for r in range(nrows):
        for c in range(9):
            if rng.random() < 0.62:
                g[r][c] = ks[rng.randrange(len(ks))]
    # smooth: a cell keeps/gets a brick when most neighbours have one
    for _ in range(2):
        ng = [row[:] for row in g]
        for r in range(nrows):
            for c in range(9):
                n = sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                        if (dr or dc) and 0 <= r + dr < nrows and 0 <= c + dc < 9 and g[r + dr][c + dc] != ".")
                if n >= 5 and g[r][c] == ".":
                    ng[r][c] = ks[(r + c) % len(ks)]
                elif n <= 2:
                    ng[r][c] = "."
        g = ng
    return "SPRINKLE CLOUD", _mirror(g)


def gen_fort(rng, nrows, tier):
    """Tin chambers with doors, full of snacks."""
    ks = _kinds(rng, 3)
    g = _grid(nrows)
    w = rng.choice([4, 5])
    for r in range(nrows):
        for c in range(COLS):
            g[r][c] = ks[(c // w + r // 3) % len(ks)]
    for c in range(COLS):
        if c % w == 0:
            for r in range(nrows):
                if r % 4 != 3:
                    g[r][c] = "t"
    for c in range(COLS):
        if g[0][c] != "t" and rng.random() < 0.3:
            g[0][c] = "t"
    return "SNACK FORT", g


def gen_maze(rng, nrows, tier):
    """A tin maze (coarse cells 2x2) whose corridors are packed with snacks."""
    ks = _kinds(rng, 3)
    cw, ch = 8, max(2, (nrows - 1) // 2)
    g = [["t"] * COLS for _ in range(ch * 2 + 1)]
    seen = set()
    stack = [(rng.randrange(cw), ch - 1)]
    seen.add(stack[0])
    while stack:
        x, y = stack[-1]
        opts = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if 0 <= x + dx < cw and 0 <= y + dy < ch and (x + dx, y + dy) not in seen]
        if not opts:
            stack.pop()
            continue
        dx, dy = rng.choice(opts)
        nx, ny = x + dx, y + dy
        seen.add((nx, ny))
        g[1 + y * 2 + dy][1 + x * 2 + dx] = "."
        g[1 + ny * 2][1 + nx * 2] = "."
        g[1 + y * 2][1 + x * 2] = "."
        stack.append((nx, ny))
    for r in range(len(g)):
        for c in range(COLS):
            if g[r][c] == ".":
                g[r][c] = ks[(r // 2 + c // 3) % len(ks)]
    # open the bottom row and the outermost columns so the gumball can get in
    for c in range(COLS):
        if rng.random() < 0.45 or c in (0, COLS - 1):
            g[-1][c] = ks[0]
    for r in range(len(g)):
        g[r][COLS - 1] = ks[1] if r % 2 else "."
    return "TIN MAZE", g[:nrows]


def gen_islands(rng, nrows, tier):
    ks = _kinds(rng, 4)
    g = _grid(nrows)
    for i in range(rng.randint(4, 6)):
        cx, cy = rng.randrange(1, 8), rng.randrange(1, max(2, nrows - 2))
        k = ks[i % len(ks)]
        for r in range(cy - 1, cy + 2):
            for c in range(cx - 2, cx + 2):
                if 0 <= r < nrows and 0 <= c < 9:
                    g[r][c] = k
        if tier >= 1 and cy + 2 < nrows and rng.random() < 0.6:
            for c in range(cx - 2, cx + 2):
                if 0 <= c < 9:
                    g[cy + 2][c] = "t"
    return "CANDY ISLANDS", _mirror(g)


def gen_spiral(rng, nrows, tier):
    ks = _kinds(rng, 3)
    g = _grid(nrows)
    top, bot, lef, rig = 0, nrows - 1, 0, COLS - 1
    i = 0
    while top <= bot and lef <= rig:
        k = ks[i % len(ks)]
        for c in range(lef, rig + 1):
            g[top][c] = k
        for r in range(top, bot + 1):
            g[r][rig] = k
        if bot - top >= 2:
            for c in range(lef, rig + 1):
                g[bot][c] = k
        if rig - lef >= 2:
            for r in range(top + 2, bot + 1):
                g[r][lef] = k
        top, bot, lef, rig = top + 2, bot - 2, lef + 2, rig - 2
        i += 1
    return "SWIRL ROLL", g


def gen_arches(rng, nrows, tier):
    ks = _kinds(rng, 3)
    g = _grid(nrows)
    for a in range(3):
        x0 = a * 6
        for r in range(nrows):
            for c in range(x0, x0 + 6):
                inner = 1 <= c - x0 <= 4 and r >= 2
                if not inner or r == nrows - 1 and (c - x0) in (2, 3):
                    g[r][c] = ks[a % len(ks)]
        if tier >= 2 and rng.random() < 0.5:
            g[0][x0 + 2] = g[0][x0 + 3] = "h"
    return "BISCUIT ARCHES", g


GENERATORS = [gen_stripes, gen_pyramid, gen_diamond, gen_rings, gen_checker, gen_columns, gen_waves, gen_zigzag,
              gen_blob, gen_fort, gen_maze, gen_islands, gen_spiral, gen_arches]


# ----------------------------------------------------------------------------- decorations
def _cells(g, pred):
    return [(r, c) for r in range(len(g)) for c in range(COLS) if pred(g[r][c])]


def _sym_set(g, r, c, ch, sym):
    g[r][c] = ch
    if sym:
        g[r][COLS - 1 - c] = ch


def _is_sym(g):
    return all(r[c] == r[COLS - 1 - c] for r in g for c in range(COLS // 2))


def decorate(rng, g, tier, j):
    """Sprinkle the tier's mechanics over a shape. j = index of the stage inside its tier (0..7)."""
    sym = _is_sym(g)
    basic = lambda ch: ch in BASIC  # noqa: E731
    left = lambda pred: [(r, c) for r, c in _cells(g, pred) if not sym or c < COLS // 2]  # noqa: E731
    mix = tier >= 10
    lvl = min(1.0, (tier + j / 8) / 12)

    # armour: chocolate (2 hits) and fudge (3 hits, tier 8+)
    for r, c in left(basic):
        if rng.random() < 0.06 + 0.22 * lvl:
            _sym_set(g, r, c, "H" if tier >= 8 and rng.random() < 0.4 else "h", sym)
    # tins (tier 1+): a few in symmetric spots, never more than ~12% of the bricks
    if tier >= 1 and rng.random() < 0.55:
        for r, c in left(basic):
            if rng.random() < 0.03 + 0.04 * lvl:
                _sym_set(g, r, c, "t", sym)
    # gift boxes (tier 1+)
    if tier >= 1:
        for _ in range(rng.randint(1, 3)):
            cs = left(basic)
            if cs:
                r, c = rng.choice(cs)
                _sym_set(g, r, c, "?", sym)
    # gumdrop bombs (tier 2+)
    if tier >= 2 and (tier == 2 or mix or rng.random() < 0.5):
        for _ in range(rng.randint(1, 2 + tier // 6)):
            cs = left(basic)
            if cs:
                r, c = rng.choice(cs)
                _sym_set(g, r, c, "x", sym)
    # jelly that grows back (tier 4+)
    if tier >= 4 and (tier == 4 or rng.random() < 0.45):
        cs = left(basic)
        rng.shuffle(cs)
        for r, c in cs[:rng.randint(3, 8)]:
            _sym_set(g, r, c, "r", sym)
    # key & locks (tier 5+): lock a cluster of snacks, put the key somewhere else
    if tier >= 5 and (tier == 5 or rng.random() < 0.4):
        cs = left(basic)
        if len(cs) > 6:
            rng.shuffle(cs)
            for r, c in cs[:rng.randint(3, 7)]:
                _sym_set(g, r, c, "L", sym)
            ks = _cells(g, basic)
            if ks:
                r, c = rng.choice(ks)
                g[r][c] = "k"
    # bumpers (tier 6+) in empty cells, away from the bricks' bottom edge
    if tier >= 6 and (tier == 6 or rng.random() < 0.45):
        empties = [(r, c) for r, c in left(lambda ch: ch == ".") if r < len(g)]
        rng.shuffle(empties)
        for r, c in empties[:rng.randint(2, 4)]:
            _sym_set(g, r, c, "*", sym)
    # portals (tier 7+): a pair, left and right side
    if tier >= 7 and (tier == 7 or rng.random() < 0.4):
        for ch in ("o", "O") if tier >= 12 and rng.random() < 0.5 else ("o",):
            el = [(r, c) for r, c in _cells(g, lambda ch2: ch2 == ".") if c < 8]
            er = [(r, c) for r, c in _cells(g, lambda ch2: ch2 == ".") if c > 9]
            if el and er:
                r1, c1 = rng.choice(el)
                r2, c2 = rng.choice(er)
                g[r1][c1] = ch
                g[r2][c2] = ch
    return g


def _moving_rows(rng, g, tier, j):
    """Rows of snacks that slide left/right (tier 3+): [row, amplitude px, speed, phase]."""
    if tier < 3 or not (tier == 3 or rng.random() < 0.4):
        return []
    out = []
    cand = [r for r in range(len(g)) if all(ch in BREAKABLE or ch == "." for ch in g[r])
            and sum(ch != "." for ch in g[r]) >= 3 and "L" not in g[r]]
    rng.shuffle(cand)
    for r in cand[:1 + (tier >= 10) + (tier >= 15)]:
        cs = [c for c in range(COLS) if g[r][c] != "."]
        c0, c1 = min(cs), max(cs)
        room = min(8 + 16 * c0, 8 + 16 * (COLS - 1 - c1))
        if room >= 12:
            out.append([r, min(room, 24 + 3 * tier), round(0.8 + 0.06 * tier + rng.random() * 0.5, 2),
                        round(rng.random() * 6.28, 2)])
    return out


# ----------------------------------------------------------------------------- validation
def reachable(rows, locks_open):
    """Cells the gumball can reach. The ball enters from below the grid and also slips around its sides
    (the 8 px gaps at the walls and the 10 px gap under the ceiling). Breakable bricks are 'eaten' as they
    are reached; tins, bumpers and still-locked locks are walls."""
    n = len(rows)
    wall = set("t*") | (set() if locks_open else {"L"})
    seen = set()
    todo = [(n, c) for c in range(COLS)]          # the open row under the bricks
    todo += [(r, -1) for r in range(-1, n + 1)] + [(r, COLS) for r in range(-1, n + 1)]
    todo += [(-1, c) for c in range(COLS)]
    seen.update(todo)
    while todo:
        r, c = todo.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if (rr, cc) in seen or not (-1 <= rr <= n and -1 <= cc <= COLS):
                continue
            if 0 <= rr < n and 0 <= cc < COLS and rows[rr][cc] in wall:
                continue
            seen.add((rr, cc))
            todo.append((rr, cc))
    return seen


def validate(st):
    """Returns a list of problems (empty = playable and clearable)."""
    errs = []
    rows = st["rows"]
    if len(rows) > MAX_ROWS:
        errs.append("too many rows")
    if any(len(r) != COLS for r in rows):
        errs.append("bad row width")
    flat = "".join(rows)
    if st["kind"] == "normal":
        if sum(flat.count(k) for k in BASIC + "hH") < 12:
            errs.append("too few bricks")
    if st["kind"] == "bonus" and st["bonus"] == "coins" and flat.count("C") < 20:
        errs.append("too few coins")
    for p in "oO":
        if flat.count(p) not in (0, 2):
            errs.append("portals must come in pairs")
    if flat.count("$") > 1:
        errs.append("more than one golden brick")
    if "L" in flat:
        if flat.count("k") != 1:
            errs.append("locks need exactly one key")
        else:
            seen = reachable(rows, False)
            kr = next(r for r, row in enumerate(rows) if "k" in row)
            if (kr, rows[kr].index("k")) not in seen:
                errs.append("key sealed off")
    seen = reachable(rows, True)
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch in BREAKABLE and (r, c) not in seen:
                errs.append(f"brick {ch} at {r},{c} sealed off")
            if ch in "oO" and (r, c) not in seen:
                errs.append("portal sealed off")
    for r, amp, sp, ph in st.get("moves", []):
        cs = [c for c in range(COLS) if rows[r][c] != "."]
        if any(rows[r][c] not in BREAKABLE for c in cs) or "L" in rows[r]:
            errs.append("moving row holds fixed things")
        if 16 + 16 * min(cs) - amp < 8 or 16 + 16 * (max(cs) + 1) + amp > 312:
            errs.append("moving row leaves the field")
    return errs


# ----------------------------------------------------------------------------- the campaign
def _trim(g):
    rows = _rows(g)
    while rows and not rows[-1].strip("."):
        rows.pop()
    while rows and not rows[0].strip("."):
        rows.pop(0)
    return rows


def _remap(rows, rng):
    a = list(BASIC)
    b = a[:]
    rng.shuffle(b)
    m = dict(zip(a, b))
    return ["".join(m.get(ch, ch) for ch in r) for r in rows]


def normal_stage(n):
    t, j = (n - 1) // 10, (n - 1) % 10
    j = j if j < 4 else j - 1           # 0..7 among the tier's normal stages
    for attempt in range(40):
        rng = random.Random(n * 7919 + attempt * 104729)
        nrows = min(MAX_ROWS, 5 + min(6, t // 2) + j // 3 + rng.randint(0, 1))
        if n <= 9 and j < len(ORIGINALS) and attempt == 0:
            name, rows = ORIGINALS[j]
            g = [list(r) for r in rows]
        elif rng.random() < 0.38:
            name, rows = rng.choice(PICTURES)
            g = [list(r) for r in _remap(rows, rng)]
        else:
            gen = GENERATORS[(n * 5 + attempt + rng.randrange(len(GENERATORS))) % len(GENERATORS)]
            name, g = gen(rng, nrows, t)
        if t >= 1 or n > 9:
            g = decorate(rng, g, t, j)
        rows = _trim(g)
        top = 1 if t < 3 else 0
        rows = ["." * COLS] * top + rows
        st = {"n": n, "kind": "normal", "name": name, "rows": rows[:MAX_ROWS]}
        st["moves"] = _moving_rows(rng, [list(r) for r in st["rows"]], t, j)
        st["creep"] = t >= 9 and (t == 9 or rng.random() < 0.35) and len(st["rows"]) <= 11
        # a golden JACKPOT brick hides in some stages
        if rng.random() < 0.12 + 0.01 * t:
            cs = [(r, c) for r, row in enumerate(st["rows"]) for c, ch in enumerate(row) if ch in BASIC]
            if cs:
                r, c = rng.choice(cs)
                st["rows"][r] = st["rows"][r][:c] + "$" + st["rows"][r][c + 1:]
        if not validate(st):
            return st
    raise RuntimeError(f"stage {n}: no valid layout")


COIN_SHAPES = [
    ("COIN BAKE", ["..CCC..CCCC..CCC..", ".CCCCC.CCCC.CCCCC.", ".CC$CC.CCCC.CCCCC.", ".CCCCC.CCCC.CCCCC.",
                   "..CCC..CCCC..CCC..", "...C....CC....C...", "CCCCCCCCCCCCCCCCCC"]),
    ("PIGGY BANK", ["...CC.......CC....", "..CCCCCCCCCCCCC...", ".CCCCCCCCCCCCCCC..", ".CCC$CCCCCCCCCCCC.",
                    ".CCCCCCCCCCCCCCC..", "..CCCCCCCCCCCCC...", "...CC.CC..CC.CC..."]),
    ("GOLD RUSH", ["CCCCCCCCCCCCCCCCCC", "C................C", "C.CCCCCCCCCCCCCC.C", "C.C............C.C",
                   "C.C.CCCCCCCCCC.C.C", "C.C.C...$....C.C.C"]),
    ("TREASURE", ["......CCCCCC......", "....CCCCCCCCCC....", "..CCCCCC$$CCCCCC..", "CCCCCCCCCCCCCCCCCC",
                  "..CCCCCCCCCCCCCC..", "....CCCCCCCCCC...."]),
]


def bonus_stage(n):
    t = (n - 1) // 10
    if (n // 10) % 2 == 0:
        name, rows = COIN_SHAPES[(n // 20) % len(COIN_SHAPES)]
        # only one golden brick per stage
        flat = "\n".join(rows)
        i = flat.find("$")
        if i >= 0:
            flat = flat[:i + 1] + flat[i + 1:].replace("$", "C")
        rows = ["." * COLS] + flat.split("\n")
        for _ in range(t // 6):            # later coin bakes are bigger
            rows.append("".join("C" if c % 3 else "." for c in range(COLS)))
        return {"n": n, "kind": "bonus", "bonus": "coins", "name": name, "rows": rows, "moves": [], "creep": False,
                "time": 30}
    return {"n": n, "kind": "bonus", "bonus": "rain", "name": "CANDY RAIN", "rows": [], "moves": [], "creep": False,
            "time": 25}


def boss_stage(n):
    t = (n - 1) // 10
    kind = BOSSES[t % len(BOSSES)]
    rng = random.Random(n * 31337)
    extra = []
    if t >= 5:     # later bosses borrow attacks from the others
        others = [BOSS_ATTACKS[k] for k in BOSSES if k != kind]
        rng.shuffle(others)
        extra = others[:1 + (t >= 12) + (t >= 17)]
    rows = ["." * COLS] * 9
    ks = _kinds(rng, 2)
    rows.append("".join(ks[0] if c % 4 in (1, 2) else "." for c in range(COLS)))
    if t >= 3:
        rows.append("".join((ks[1] if c % 4 in (1, 2) else ("t" if t >= 8 and c % 8 == 0 else "."))
                            for c in range(COLS)))
    hp = (16 + 5 * t) * {"cake": 10, "donut": 10, "jar": 6, "robot": 9, "whale": 7}[kind] // 10
    boss = {"kind": kind, "name": BOSS_NAMES[kind] + RANKS[min(3, t // 5)], "hp": hp,
            "rate": round(max(0.9, 2.6 - 0.08 * t), 2), "speed": round(1 + 0.05 * t, 2),
            "extra": extra, "tier": t}
    return {"n": n, "kind": "boss", "name": boss["name"], "rows": rows, "moves": [], "creep": False, "boss": boss}


def build_campaign():
    out = []
    for n in range(1, 201):
        if n % 10 == 0:
            st = boss_stage(n)
        elif n % 10 == 5:
            st = bonus_stage(n)
        else:
            st = normal_stage(n)
        t = (n - 1) // 10
        st["tier"] = t
        st["speed"] = round(1 + 0.022 * t + 0.003 * (n % 10), 3)
        st["new"] = THEMES[t][5] if n % 10 == 1 else ""
        out.append(st)
    return out


CAMPAIGN = build_campaign()
