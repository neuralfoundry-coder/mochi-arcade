"""TOWER TABBY stage data: curated cat-tree templates, tier themes, the seeded 200-stage generator and a
reachability validator. Pure Python (no pygame) so tests and ios/tools/gen_data.py can use it.

A stage is six "level lines" (L0 = the floor ... L5 = the top perch), 20 cells of 16 px each. Cells:
  .  air                 =  carpeted shelf           H  shelf + scratching post up to the next level
  R  shelf + sisal rope hanging from the level above (jump + UP to grab it)
  ~  a hammock rides back and forth over this run    S  springy cat bed (bounces you up a level)
  X  cardboard box shelf that collapses under you    < >  conveyor belt (moves you left / right)
  W  box tunnel: dive in with DOWN, pop out of its partner box (pairs in reading order)
  G  the comfy cushion (goal, top level)             P  Mikan's start (floor)
Each level may tilt (slope -1 / 0 / +1, 4 px from the centre to the ends): yarn rolls downhill.
The finished campaign is exported to iOS (tower_tabby.EXPORT) so both platforms play the same stages.
"""
import random

STAGES = 200
NC = 20                      # cells per level line
CW = 16                      # cell width in pixels
LEVEL_Y = [192, 162, 132, 102, 72, 42]   # shelf surface of each level at the screen centre
TILT = 4
SOLID = set("=HRSX<>WGP")
GAP_JUMP = 2                 # air cells a normal jump clears

# ----------------------------------------------------------------------------- curated templates
# (name, first tier, rows top -> bottom (L5 .. L0), slopes top -> bottom (L5 .. L1))
TEMPLATES = [
    ("FIRST PERCH", 0, [
        ".......===G===......",
        "...=======H=====....",
        "....H===========....",
        "..============H===..",
        "....H=============..",
        "==P===========H====="], [0, 0, 0, 0, 0]),
    ("ZIGZAG SHELVES", 0, [
        "......===G===.......",
        "..=====H============",
        "=====H==========H=..",
        "..===H=====H========",
        "=========H========..",
        "==P=============H==="], [0, -1, 1, -1, 1]),
    ("THE TRUNK", 0, [
        ".........=G=........",
        "....======H======...",
        "..=====H....H=====..",
        "...=H==========H==..",
        "......===H==H===....",
        "=P======H====H======"], [0, 0, -1, 1, 0]),
    ("STAIRCASE", 0, [
        "..............=G==..",
        "...........=====H...",
        ".......=====H.......",
        "...=====H...........",
        "=====H==............",
        "==H=P==============="], [0, -1, -1, -1, -1]),
    ("SPIRAL STEPS", 0, [
        ".........==G==......",
        "......======H===....",
        "...======H=====H==..",
        "====H===========H===",
        "..=====H====H=====..",
        "=======P====H======="], [0, 1, -1, 0, 1]),
    ("ROPE SWINGS", 1, [
        "..........==G==.....",
        ".....=====R=====....",
        "..====R======R===...",
        "=====H=====R======..",
        "..R=============H==.",
        "==P=======R========="], [0, 1, -1, 1, -1]),
    ("SCRATCH PILLARS", 1, [
        "....==G==...........",
        "..==H===...=======..",
        "===H...====H...=H===",
        ".=H===..=H===.===H=.",
        "====....===H===H====",
        "===P=========H======"], [0, -1, 0, 0, 1]),
    ("CRISSCROSS", 1, [
        ".........==G==......",
        "=========..==H======",
        "..H=========H===....",
        "======H=...===H=====",
        "..===H=======H====..",
        "P========H=========="], [0, 1, -1, 1, -1]),
    ("SIDE STEP", 1, [
        "........==G=........",
        "....====H=======....",
        "=====H=......=H=====",
        "..=H===========H==..",
        "=====H======H=====..",
        "=========P=====H===="], [0, 0, 0, -1, 1]),
    ("SWING SET", 1, [
        "...====G====........",
        "..=R==....=R==......",
        "....=R==...==R==....",
        "....==R=.....=R=....",
        "=====R==...==R=====.",
        "=P=====H=======H===="], [0, 0, 0, 0, 1]),
    ("HAMMOCK HOP", 2, [
        "........===G==......",
        "====~~~~~~===H=====.",
        "..H======~~~~~~=====",
        "=====~~~~~~=====H===",
        ".H====~~~~~~=======.",
        "=============H==P==="], [0, 0, 0, 0, 0]),
    ("TWIN TOWERS", 2, [
        "....=====G=====.....",
        "..==H=~~~~~~=H====..",
        ".====.........==H==.",
        ".=H=~~~~~~~~~~=H==..",
        "===H===.....=======.",
        "==P==H=======H======"], [0, 0, -1, 0, 1]),
    ("BALCONY", 2, [
        "..===G===...........",
        "..=H======~~~~~=====",
        "======~~~~~=====H===",
        "=H==========~~~~~===",
        "=========H=========.",
        "===P===========H===="], [0, 0, 0, 0, 1]),
    ("PYRAMID", 2, [
        ".........=G=........",
        ".......===H===......",
        ".....===H===H===....",
        "...===H========H===.",
        ".==H=============H==",
        "=H=======P========H="], [0, 0, -1, 1, -1]),
    ("WATERFALL", 2, [
        "..............==G==.",
        "..=============H===.",
        "===========H======..",
        "..=====H============",
        "=============H====..",
        "===H==============P="], [0, -1, 1, -1, 1]),
    ("BIRDHOUSE", 2, [
        "......====G====.....",
        "......=R=..=R=......",
        "..====R==~~~~R====..",
        "=====H=......=H=====",
        "...R==========R.....",
        "=P=======H=========="], [0, 0, 0, 1, 0]),
    ("BOUNCE HOUSE", 3, [
        "...........====G===.",
        "....========S==.....",
        "..=====S====..======",
        "..====......===S===.",
        "===S=========H=====.",
        "==H====P=====S======"], [0, 0, -1, 0, 1]),
    ("DROP ZONE", 3, [
        ".....===G===........",
        "..==..===H==..==..==",
        "==..==H===..==..==..",
        "..==..==..===H==..==",
        "==..==..==H=..==..==",
        "=P========H========="], [0, 0, 0, 0, 0]),
    ("LONG WAY ROUND", 4, [
        "..............==G==.",
        "...===============H=",
        "...H======..======..",
        "..===============H==",
        "==H======..=======..",
        "P================H=="], [0, -1, 1, -1, 1]),
    ("CAT CONDO", 4, [
        "........==G==.......",
        "..====XXX===H===....",
        "=====H====XXX====...",
        "...===XXX====H=====.",
        "====H==XXX======....",
        "============H==P===="], [0, 1, -1, 1, -1]),
    ("TREEHOUSE", 5, [
        "....==G==...........",
        "...=H===S.....=====.",
        "===H=~~~~~====R===..",
        "..H=====XX=====S===.",
        "====>>>>====H=====..",
        "=H=========P========"], [0, 0, 0, -1, 0]),
    ("CONVEYOR CAFE", 5, [
        "...........==G==....",
        "....>>>>>>=====H=...",
        "...==H=<<<<<<<===...",
        "..===>>>>>>>===H==..",
        "===H==<<<<<<<======.",
        "=====P=========H===="], [0, 0, 0, 0, 0]),
    ("BOX TUNNELS", 6, [
        ".......===G===......",
        "..====W...==H====...",
        "=====H===......HW==.",
        "...=W==H=.....===H=.",
        "=====H===......=W==.",
        "P================H=="], [0, 0, 1, -1, 0]),
    ("THE GAUNTLET", 7, [
        "................==G=",
        "====~~~~~====~~~~H==",
        "=R====..=====..====.",
        "==~~~~~=====~~~~~H==",
        "R=====..=======..===",
        "=================P=H"], [0, 0, 1, 0, -1]),
]

# Boss arenas use levels 0-3 (the open sky above is the boss's) and bonus stages their own fields.
ARENAS = [
    ("PERCH ARENA", [
        "....................",
        "....................",
        "====............====",
        "..H===........===H..",
        "====H..........H====",
        "=H==P============H=="]),
    ("HIGH NEST", [
        "....................",
        "....................",
        "......========......",
        "======H......H======",
        "..H===........===H..",
        "=P==H==========H===="]),
    ("ROPE RING", [
        "....................",
        "....................",
        "===......==......===",
        "=R=.....=H==.....=R=",
        "..H=====H..H=====H..",
        "=====H====P===H====="]),
]
BONUS_FIELDS = [
    ("FISH FRENZY", [
        "....................",
        "....................",
        "..======....======..",
        "=====H........H=====",
        "...=H======S====H...",
        "====H====P=====H===="], [0, 0, 0, 0, 0]),
    ("YARN ROUNDUP", [
        "....................",
        "......========......",
        "..====H......H====..",
        "======H......H======",
        "...==H===SS===H==...",
        "====H===P======H===="], [0, 0, 0, 1, -1]),
]

# ----------------------------------------------------------------------------- themes (one per tier)
# name, wall top, wall bottom, carpet, carpet shade, post, post stripe, backdrop style, accent
THEMES = [
    ("COZY LIVING ROOM", "deep", "ink", "pink", "hotpink", "peach", "brown", "window", "yellow"),
    ("SUNNY WINDOWSILL", "sky", "blue", "cream", "peach", "peach", "orange", "window", "yellow"),
    ("KITCHEN CLIMB", "teal", "ink", "mint", "teal", "cream", "peach", "tiles", "orange"),
    ("BOOKSHELF HEIGHTS", "brown", "choco", "lavender", "purple", "peach", "brown", "books", "lime"),
    ("LAUNDRY LOFT", "lavender", "deep", "white", "gray", "sky", "blue", "bubbles", "pink"),
    ("GREENHOUSE GROVE", "teal", "night", "lime", "teal", "brown", "choco", "leaves", "pink"),
    ("MOONLIT HALL", "ink", "night", "sky", "blue", "lavender", "purple", "stars", "yellow"),
    ("ATTIC ADVENTURE", "choco", "night", "orange", "brown", "cream", "brown", "beams", "yellow"),
    ("RAINY PORCH", "darkgray", "night", "teal", "blue", "gray", "darkgray", "rain", "sky"),
    ("KAW'S NEST", "purple", "night", "yellow", "orange", "brown", "choco", "stars", "red"),
    ("CANDY PARLOR", "hotpink", "deep", "mint", "teal", "pink", "white", "stripes", "yellow"),
    ("SNOWY CABIN", "blue", "ink", "white", "sky", "brown", "choco", "snow", "red"),
    ("TOY BOX TOWER", "orange", "choco", "sky", "blue", "yellow", "orange", "polka", "lime"),
    ("MUSIC ROOM", "deep", "night", "red", "hotpink", "cream", "peach", "notes", "yellow"),
    ("AUTUMN GARDEN", "orange", "brown", "peach", "orange", "choco", "brown", "leaves", "red"),
    ("STARLIGHT DECK", "night", "black", "lavender", "purple", "sky", "blue", "stars", "yellow"),
    ("BUBBLE BATH", "sky", "deep", "pink", "hotpink", "white", "sky", "bubbles", "mint"),
    ("STORMY TOWER", "darkgray", "black", "gray", "darkgray", "lavender", "purple", "rain", "yellow"),
    ("GOLDEN PALACE", "yellow", "brown", "white", "yellow", "orange", "yellow", "stripes", "hotpink"),
    ("SKY PERCH", "sky", "lavender", "hotpink", "purple", "yellow", "orange", "clouds", "white"),
]

# ----------------------------------------------------------------------------- hazards, bosses, modifiers
# kind: (name, intro tier, blurb for the NEW card)
HAZARDS = {
    "yarn": ("YARN BALL", 0, "ROLLS DOWNHILL"),
    "cone": ("PINECONE", 0, "DROPS STRAIGHT DOWN"),
    "mouse": ("TOY MOUSE", 1, "HOPS ALONG SHELVES"),
    "cushion": ("CUSHION", 2, "FALLS AND SITS THERE"),
    "spider": ("DANGLER", 3, "BOBS ON A THREAD"),
    "spritz": ("SPRITZER", 4, "SQUIRTS WATER - JUMP!"),
    "ball": ("SQUEAKY BALL", 5, "BOUNCES HIGH"),
    "bot": ("MINI VAC", 6, "CLIMBS POSTS TOO"),
    "moth": ("MOTH", 7, "FLUTTERS ACROSS"),
    "marble": ("MARBLE", 8, "ZOOMS FAST"),
}
DROPS = {"yarn": 4, "cone": 2, "cushion": 1, "ball": 1, "marble": 1}      # what KAW throws, with weights
PLACED = ("mouse", "spider", "spritz", "bot")
# structure: (name, intro tier, blurb)
STRUCTS = {
    "R": ("SISAL ROPE", 1, "JUMP + UP TO GRAB"),
    "~": ("HAMMOCK", 2, "RIDE IT ACROSS"),
    "S": ("SPRING BED", 3, "BOING! UP A LEVEL"),
    "X": ("FLIMSY BOX", 4, "COLLAPSES - HURRY!"),
    ">": ("CONVEYOR", 5, "CARRIES EVERYTHING"),
    "W": ("BOX TUNNEL", 6, "DOWN TO DIVE IN"),
}
MODS = {   # name: (label on the stage card, first tier)
    "wind": ("WINDY WINDOW", 3),
    "slick": ("POLISHED WOOD", 5),
    "frenzy": ("KAW FRENZY", 6),
    "dark": ("LIGHTS OUT", 8),
    "heavy": ("HEAVY YARN", 10),
}
BOSSES = {
    # kind: (name, base hp, own patterns)
    "kaw": ("KAW THE CROW", 14, ["swoop", "drop", "swoop", "feathers"]),
    "vac": ("MEGA VAC", 16, ["dash", "spit", "suck", "dash"]),
    "mouse": ("WIND-UP KING", 16, ["slam", "mice", "dash", "slam"]),
    "spritz": ("SPRITZ KING", 16, ["spray", "jet", "hop", "spray"]),
    "dot": ("DOT PHANTOM", 15, ["trace", "sparks", "beam", "trace"]),
    "golem": ("TANGLE TITAN", 18, ["roll", "toss", "slam", "roll"]),
    "storm": ("STORM KAW", 24, ["swoop", "drop", "beam", "feathers", "swoop", "mice"]),
}
BOSS_CYCLE = ["kaw", "vac", "mouse", "spritz", "dot", "golem", "kaw", "vac", "mouse", "storm",
              "spritz", "dot", "golem", "kaw", "vac", "mouse", "spritz", "dot", "golem", "storm"]
GUEST = ["drop", "spit", "beam", "mice", "sparks"]
ROMAN = ["", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X"]
POWERS = {"wand": 4.0, "bell": 2.0, "milk": 2.0, "nip": 1.5, "heart": 0.4}
QUIPS = ["NAP TIME IS UP THERE!", "THAT CUSHION IS MINE!", "NO CROW KEEPS MY SPOT!",
         "PAWS READY... CLIMB!", "ONE MORE SHELF!", "SMELLS LIKE TUNA UP TOP!",
         "KAW KAW YOURSELF!", "I CAN CLIMB ANYTHING!", "WHO MOVED MY PERCH?", "PURR-SISTENCE!"]


# ----------------------------------------------------------------------------- geometry helpers
def y_at(level, slope, x):
    """Shelf surface y of a level at pixel x (slope +1: the right end is lower, things roll right)."""
    return LEVEL_Y[level] + slope * TILT * (x - 160) / 160.0


def solid(lv, k, c):
    return 0 <= k < 6 and 0 <= c < NC and lv[k][c] in SOLID


def walk(lv, k, c):
    return 0 <= k < 6 and 0 <= c < NC and (lv[k][c] in SOLID or lv[k][c] == "~")


def fall_from(lv, k, c):
    """Where something falling from level k down column c lands (highest solid level below)."""
    for j in range(k - 1, -1, -1):
        if solid(lv, j, c):
            return j
    return None


def warp_pairs(lv):
    cells = [(k, c) for k in range(6) for c in range(NC) if lv[k][c] == "W"]
    return [(cells[i], cells[i + 1]) for i in range(0, len(cells) - 1, 2)]


def find(lv, ch):
    for k in range(6):
        c = lv[k].find(ch)
        if c >= 0:
            return k, c
    return None


def neighbours(lv, k, c):
    """Moves Mikan can make from cell (k, c): yields ((k2, c2), cost)."""
    ch = lv[k][c]
    for d in (-1, 1):
        c2 = c + d
        if not 0 <= c2 < NC:
            continue
        if walk(lv, k, c2):
            yield (k, c2), 1
            continue
        j = fall_from(lv, k, c2)
        if j is not None:
            yield (j, c2), 1
        for g in range(2, GAP_JUMP + 2):          # jump over a gap of g-1 air cells
            c3 = c + d * g
            if 0 <= c3 < NC and walk(lv, k, c3):
                if all(not walk(lv, k, c + d * i) for i in range(1, g)):
                    yield (k, c3), 2
                break
    if ch in "HR" and k < 5 and solid(lv, k + 1, c):
        yield (k + 1, c), 2
    if k > 0 and lv[k - 1][c] in "HR":
        yield (k - 1, c), 2
    if ch == "S" and k < 5:
        for dc in (0, -1, 1):
            if solid(lv, k + 1, c + dc):
                yield (k + 1, c + dc), 1
    if ch == "W":
        for a, b in warp_pairs(lv):
            if a == (k, c):
                yield b, 1
            elif b == (k, c):
                yield a, 1


def distances(lv, start):
    """Cheapest cost from start to every reachable cell (Dijkstra over the small cell graph)."""
    import heapq
    dist = {start: 0}
    q = [(0, start)]
    while q:
        d, cur = heapq.heappop(q)
        if d > dist.get(cur, 1 << 30):
            continue
        for nxt, w in neighbours(lv, *cur):
            nd = d + w
            if nd < dist.get(nxt, 1 << 30):
                dist[nxt] = nd
                heapq.heappush(q, (nd, nxt))
    return dist


def structure_errors(lv, slopes):
    """Static sanity rules for a level set (bottom-to-top strings)."""
    if len(lv) != 6 or any(len(r) != NC for r in lv):
        return "bad size"
    if any(ch not in SOLID and ch not in ".~" for r in lv for ch in r):
        return "bad char"
    if lv[0].count("P") != 1:
        return "needs one P on the floor"
    for k in range(6):
        for c in range(NC):
            ch = lv[k][c]
            if ch in "HR":
                if k == 5 or not solid(lv, k + 1, c):
                    return f"post/rope at L{k} c{c} has no shelf above"
                if lv[k + 1][c] in "X~":
                    return f"post/rope at L{k} c{c} ends on a box"
                if ch == "H" and lv[k][c] == "X":
                    return "post on a box"
            if ch == "~" and slopes[k]:
                return f"hammock on a sloped level L{k}"
        for run_c0, run_c1 in _runs(lv[k], "~"):
            if run_c1 - run_c0 < 3:
                return f"hammock run too short at L{k}"
    if len([1 for k in range(6) for c in range(NC) if lv[k][c] == "W"]) % 2:
        return "unpaired box tunnel"
    return None


def _runs(row, ch):
    out, c = [], 0
    while c < len(row):
        if row[c] == ch:
            c0 = c
            while c < len(row) and row[c] == ch:
                c += 1
            out.append((c0, c))
        else:
            c += 1
    return out


def validate(st):
    """None if the stage is sound and winnable, else a message."""
    lv, slopes = st["lv"], st["sl"]
    err = structure_errors(lv, slopes)
    if err:
        return err
    start = find(lv, "P")
    dist = distances(lv, start)
    if st["k"] == "normal":
        goal = find(lv, "G")
        if goal is None or goal[0] != 5:
            return "goal must be on the top level"
        if goal not in dist:
            return "goal unreachable"
        for c, k in st["kit"] + st["fish"] + [i[:2] for i in st["it"]]:
            if (k, c) not in dist:
                return f"pickup at L{k} c{c} unreachable"
            if goal not in distances(lv, (k, c)):
                return f"stuck after the pickup at L{k} c{c}"
    else:
        for k in range(6):
            for c in range(NC):
                if solid(lv, k, c) and (k, c) not in dist:
                    return f"arena cell L{k} c{c} unreachable"
    for kind, c, k in st["en"]:
        if kind == "spider":
            if not solid(lv, k + 1, c) or lv[k][c] in "HR" or abs(c - start[1]) < 3 and k == 0:
                return f"bad spider at L{k} c{c}"
        elif kind == "spritz":
            if c not in (0, NC - 1) or not solid(lv, k, c):
                return f"bad spritzer at L{k} c{c}"
        elif not solid(lv, k, c):
            return f"{kind} floating at L{k} c{c}"
    return None


# ----------------------------------------------------------------------------- generator
def mirror(rows, slopes):
    flip = {"<": ">", ">": "<"}
    return ["".join(flip.get(ch, ch) for ch in reversed(r)) for r in rows], [-s for s in slopes]


def _set(lv, k, c, ch):
    r = lv[k]
    lv[k] = r[:c] + ch + r[c + 1:]


def _plain_runs(lv, k, minlen):
    """Runs of plain '=' cells on level k (candidates for specials)."""
    return [(a, b) for a, b in _runs(lv[k], "=") if b - a >= minlen]


def add_specials(lv, rng, tier, force):
    """Seeded extras by tier: beds, collapsing boxes, belts, a tunnel pair. force: struct chars to include."""
    added = []
    want = []
    if tier >= 3 and (force == "S" or rng.random() < 0.45):
        want += ["S"] * (1 + (tier >= 8 and rng.random() < 0.5))
    if tier >= 4 and (force == "X" or rng.random() < 0.4):
        want += ["X"] * (1 + (tier >= 9 and rng.random() < 0.5))
    if tier >= 5 and (force == ">" or rng.random() < 0.4):
        want += [">"] * (1 + (tier >= 10 and rng.random() < 0.5))
    if tier >= 6 and (force == "W" or rng.random() < 0.35):
        want.append("W")
    for sp in want:
        for _ in range(30):
            k = rng.randint(0, 4)
            runs = _plain_runs(lv, k, 3 if sp != "S" else 1)
            if not runs:
                continue
            a, b = rng.choice(runs)
            if sp == "S":
                c = rng.randrange(a, b)
                if not any(solid(lv, k + 1, c + dc) for dc in (-1, 0, 1)) or lv[k][c] != "=":
                    continue
                if k > 0 and lv[k - 1][c] in "HR":          # a post arrives here: keep its top plain
                    continue
                _set(lv, k, c, "S")
            elif sp == "X":
                if k == 0:
                    continue
                n = min(b - a, rng.randint(2, 3))
                c0 = rng.randint(a, b - n)
                if any(lv[k - 1][c] in "HR" for c in range(c0, c0 + n)):
                    continue
                for c in range(c0, c0 + n):
                    _set(lv, k, c, "X")
            elif sp == ">":
                if k == 0:
                    continue
                n = min(b - a, rng.randint(3, 5))
                c0 = rng.randint(a, b - n)
                ch = rng.choice("<>")
                for c in range(c0, c0 + n):
                    _set(lv, k, c, ch)
            else:
                # a tunnel pair: two plain cells on different levels, far apart
                cand = [(kk, c) for kk in range(5) for c in range(NC) if lv[kk][c] == "="
                        and not (kk > 0 and lv[kk - 1][c] in "HR")]
                rng.shuffle(cand)
                pair = None
                for i, (k1, c1) in enumerate(cand):
                    for k2, c2 in cand[i + 1:]:
                        if abs(k1 - k2) >= 1 and abs(c1 - c2) >= 6:
                            pair = ((k1, c1), (k2, c2))
                            break
                    if pair:
                        break
                if not pair or any(ch == "W" for r in lv for ch in r):
                    continue
                for kk, c in pair:
                    _set(lv, kk, c, "W")
            added.append(sp)
            break
    return added


def roster(tier, n_stage, rng, new):
    """Placed enemies for a stage: a list of kinds."""
    unlocked = [k for k in PLACED if HAZARDS[k][1] <= tier]
    if not unlocked:
        return []
    n = min(6, (1 if tier >= 1 else 0) + tier // 3 + (1 if n_stage % 10 >= 6 else 0))
    out = []
    if new in PLACED:
        out.append(new)
    while len(out) < n:
        k = rng.choice(unlocked)
        if k == "spritz" and out.count("spritz") >= (2 if tier >= 10 else 1):
            continue
        if k == "bot" and out.count("bot") >= (2 if tier >= 12 else 1):
            continue
        out.append(k)
    return out


def place(lv, kinds, rng, start):
    en = []
    used = set()
    for kind in kinds:
        for _ in range(60):
            if kind == "spritz":
                k = rng.randint(1, 4)
                c = rng.choice((0, NC - 1))
                if not solid(lv, k, c) or (k, c, "spritz") in used:
                    continue
            elif kind == "spider":
                k = rng.randint(0, 4)
                c = rng.randint(1, NC - 2)
                if not solid(lv, k + 1, c) or lv[k][c] in "HR" or lv[k + 1][c] in "~":
                    continue
                if k == 0 and abs(c - start[1]) < 3:
                    continue
            else:
                k = rng.randint(1, 4 if kind == "mouse" else 3)
                c = rng.randint(0, NC - 1)
                if lv[k][c] not in "=":
                    continue
                if kind == "mouse" and not any(b - a >= 4 and a <= c < b for a, b in _runs_solid(lv[k])):
                    continue
            if (k, c) in used:
                continue
            used.add((k, c))
            en.append([kind, c, k])
            break
    return en


def _runs_solid(row):
    out, c = [], 0
    while c < len(row):
        if row[c] in SOLID:
            c0 = c
            while c < len(row) and row[c] in SOLID:
                c += 1
            out.append((c0, c))
        else:
            c += 1
    return out


def to_goal(lv, goal):
    """Cost from every cell to the goal (Dijkstra on the reversed move graph)."""
    import heapq
    rev = {}
    for k in range(6):
        for c in range(NC):
            if walk(lv, k, c):
                for nxt, w in neighbours(lv, k, c):
                    rev.setdefault(nxt, []).append(((k, c), w))
    dist = {goal: 0}
    q = [(0, goal)]
    while q:
        d, cur = heapq.heappop(q)
        if d > dist.get(cur, 1 << 30):
            continue
        for prv, w in rev.get(cur, ()):
            nd = d + w
            if nd < dist.get(prv, 1 << 30):
                dist[prv] = nd
                heapq.heappush(q, (nd, prv))
    return dist


def pickups(lv, rng, tier, start):
    """Fish, kittens (off the main route: exploring pays) and power-ups."""
    goal = find(lv, "G")
    ds, dg = distances(lv, start), to_goal(lv, goal)
    best = ds[goal]
    cells = [(k, c) for k in range(6) for c in range(NC) if lv[k][c] in "=<>" and (k, c) != goal and k > 0
             and (k, c) in ds and (k, c) in dg]
    rng.shuffle(cells)
    nk = 1 if tier < 2 else (2 if tier < 8 else 3)
    nf = min(9, 5 + tier // 4)
    ni = 1 if tier < 10 else 2
    detour = sorted(cells, key=lambda kc: -(ds[kc] + dg[kc] - best) - kc[0] * 0.8 - rng.random() * 3)
    kit = []
    for k, c in detour:
        if len(kit) >= nk:
            break
        if k >= 2 and all(abs(c - c2) > 2 or k != k2 for c2, k2 in kit):
            kit.append([c, k])
    taken = {(k, c) for c, k in kit}
    fish = []
    for k, c in cells:
        if len(fish) >= nf:
            break
        if (k, c) not in taken:
            fish.append([c, k])
            taken.add((k, c))
    kinds = [p for p in POWERS if p != "milk" or tier >= 2]
    its = []
    for k, c in cells:
        if len(its) >= ni:
            break
        if (k, c) in taken or k > 4:
            continue
        r = rng.random() * sum(POWERS[p] for p in kinds)
        for p in kinds:
            r -= POWERS[p]
            if r <= 0:
                break
        its.append([c, k, p])
        taken.add((k, c))
    return fish, kit, its


def tier_of(n):
    return (n - 1) // 10


def _template_order():
    """Which template each normal stage uses: a seeded walk through the unlocked library."""
    rng = random.Random(2024)
    order = {}
    recent = []
    for n in range(1, STAGES + 1):
        if n % 5 == 0:
            continue
        t = tier_of(n)
        if t == 0:
            first = ["FIRST PERCH", "ZIGZAG SHELVES", "THE TRUNK", "STAIRCASE", "SPIRAL STEPS", "ZIGZAG SHELVES",
                     "THE TRUNK", "FIRST PERCH"]
            order[n] = first[[1, 2, 3, 4, 6, 7, 8, 9].index(n)]
        else:
            pool = [tp for tp in TEMPLATES if tp[1] <= t]
            intro = [tp for tp in pool if tp[1] == t]
            if n % 10 == 1 and intro:
                pick = intro[0][0]
            else:
                fresh = [tp[0] for tp in pool if tp[0] not in recent[-6:]]
                weights = [3 if next(x for x in TEMPLATES if x[0] == nm)[1] >= t - 3 else 1 for nm in fresh]
                pick = rng.choices(fresh, weights)[0]
            order[n] = pick
        recent.append(order[n])
    return order


def _new_things(n, t):
    """(new hazard kind, new structure char) shown on the stage card of the first stage of a tier."""
    if n == 3:
        return "cone", ""
    if n % 10 != 1 or n == 1:
        return "", ""
    haz = next((k for k, v in HAZARDS.items() if v[1] == t and k != "cone"), "")
    st = next((k for k, v in STRUCTS.items() if v[1] == t), "")
    return haz, st


def _normal(n, order, counts):
    t = tier_of(n)
    i = (n - 1) % 10
    name = order[n]
    tpl = next(tp for tp in TEMPLATES if tp[0] == name)
    new_h, new_s = _new_things(n, t)
    for attempt in range(40):
        rng = random.Random(n * 7919 + attempt * 104729 + 7)
        rows, slopes = list(tpl[2]), list(tpl[3])
        if n > 2 and rng.random() < 0.5:
            rows, slopes = mirror(rows, slopes)
        lv = list(reversed(rows))
        sl = [0] + list(reversed(slopes))
        force = new_s if new_s in "SX>W" and new_s else ""
        added = add_specials(lv, rng, t, force)
        if force and not any(ch in (force + ("<" if force == ">" else "")) for r in lv for ch in r):
            continue
        start = find(lv, "P")
        mix = []
        for kind, w in DROPS.items():
            if HAZARDS[kind][1] <= t and (kind != "cone" or n >= 3):
                mix += [kind] * w
        if new_h in DROPS:
            mix += [new_h] * 3
        en = place(lv, roster(t, n, rng, new_h), rng, start)
        fish, kit, its = pickups(lv, rng, t, start)
        mods = []
        unlocked = [m for m, (_, t0) in MODS.items() if t0 <= t]
        if unlocked and (i == 8 or rng.random() < min(0.5, 0.12 + 0.03 * t)):
            mods.append(rng.choice(unlocked))
            if t >= 10 and rng.random() < 0.25:
                m2 = rng.choice(unlocked)
                if m2 not in mods:
                    mods.append(m2)
        if new_h or new_s:
            mods = []               # keep intro stages readable
        rate = max(1.15, 3.3 - 0.1 * t - 0.03 * i)
        if "frenzy" in mods:
            rate = max(0.9, rate * 0.65)
        counts[name] = counts.get(name, 0) + 1
        nm = name + ROMAN[min(9, counts[name] - 1)] if t > 0 else name
        st = {"k": "normal", "nm": nm, "tpl": name, "th": t, "lv": lv, "sl": sl, "en": en, "fish": fish,
              "kit": kit, "it": its, "mix": mix, "rate": round(rate, 3), "hs": round(1 + 0.03 * t + 0.006 * i, 3),
              "moth": round(max(3.5, 9.0 - 0.25 * t), 2) if t >= 7 else 0, "mods": mods,
              "new": new_h, "nst": new_s, "quip": QUIPS[(n * 3 + n // 7) % len(QUIPS)]}
        err = validate(st)
        if err is None:
            goal = find(lv, "G")
            st["par"] = int(14 + distances(lv, start)[goal] * 0.55)
            return st
    raise RuntimeError(f"stage {n} ({name}) could not be generated")


def _boss(n, counts):
    t = tier_of(n)
    kind = BOSS_CYCLE[t]
    name, hp0, pats = BOSSES[kind]
    lv_n = counts.get("boss_" + kind, 0)
    counts["boss_" + kind] = lv_n + 1
    rng = random.Random(n * 31337)
    pat = list(pats)
    if lv_n >= 1 and kind != "storm":
        pat.append(pats[1])
    if t >= 10:
        g = [p for p in GUEST if p not in pat]
        pat.insert(2, rng.choice(g))
    arena = ARENAS[t % len(ARENAS)]
    lv = list(reversed(arena[1]))
    st = {"k": "boss", "nm": name + ROMAN[min(9, lv_n)], "tpl": arena[0], "th": t, "lv": lv, "sl": [0] * 6,
          "en": [], "fish": [], "kit": [], "it": [], "mix": [], "rate": 0, "hs": round(1 + 0.03 * t, 3), "moth": 0,
          "mods": [], "new": "", "nst": "", "boss": kind, "lv_n": lv_n,
          "hp": int(hp0 * (1 + 0.3 * lv_n) + t * 0.6), "pat": pat, "spd": round(1 + 0.05 * t, 3), "par": 90}
    err = validate(st)
    assert err is None, (n, err)
    return st


def _bonus(n):
    t = tier_of(n)
    field = BONUS_FIELDS[t % 2]
    lv = list(reversed(field[1]))
    st = {"k": "bonus", "nm": field[0], "tpl": field[0], "th": t, "lv": lv, "sl": [0] + list(reversed(field[2])),
          "en": [], "fish": [], "kit": [], "it": [], "mix": [], "rate": 0, "hs": 1.0, "moth": 0, "mods": [], "new": "",
          "nst": "", "bt": "fish" if t % 2 == 0 else "yarn", "time": 20, "par": 20}
    err = validate(st)
    assert err is None, (n, err)
    return st


_cache = []


def generate():
    if _cache:
        return [dict(s) for s in _cache[0]]
    order = _template_order()
    counts = {}
    out = []
    for n in range(1, STAGES + 1):
        if n % 10 == 0:
            out.append(_boss(n, counts))
        elif n % 10 == 5:
            out.append(_bonus(n))
        else:
            out.append(_normal(n, order, counts))
    _cache.append(out)
    return [dict(s) for s in out]


def export():
    keep = ("k", "nm", "th", "lv", "sl", "en", "fish", "kit", "it", "mix", "rate", "hs", "moth", "mods", "new", "nst",
            "par", "quip", "boss", "hp", "pat", "spd", "bt", "time", "lv_n")
    stages = [{k: v for k, v in s.items() if k in keep} for s in generate()]
    return {
        "stages": stages,
        "themes": [list(t) for t in THEMES],
        "hazards": {k: list(v) for k, v in HAZARDS.items()},
        "structs": {k: list(v) for k, v in STRUCTS.items()},
        "mods": {k: v[0] for k, v in MODS.items()},
    }


def ascii(st):
    """Debug view of a stage (top level first)."""
    lv = [list(r) for r in st["lv"]]
    for c, k in st.get("kit", []):
        lv[k][c] = "k"
    for c, k in st.get("fish", []):
        lv[k][c] = "f"
    for c, k, _ in st.get("it", []):
        lv[k][c] = "i"
    for kind, c, k in st.get("en", []):
        lv[k][c] = kind[0].upper() if kind != "spider" else "D"
    return "\n".join(f"L{k} {st['sl'][k]:+d} " + "".join(lv[k]) for k in range(5, -1, -1))
