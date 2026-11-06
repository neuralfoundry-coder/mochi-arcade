"""WHISKER MAZE campaign: 200 seeded, mirror-symmetric house mazes (20 rooms x 10 stages).

Mazes are carved on a 15x8 cell lattice (31x17 tiles, corridors one tile wide): curated "furniture" motifs
(tables, islands, shelves ...) block cells, a seeded spanning tree joins the rest, dead ends are opened up into
loops, then the room's features are stamped in: cupboard doors, wet floor, paw-print secret passages and
mouse-hole tunnels. Everything here is deterministic (random.Random(seed)) and exported to iOS as JSON.

Tile chars:  # wall   . crumb   (space) floor   o catnip   P start   = bot dock   - pet flap (bots only)
             D / d cupboard door (phase A / B, with a crumb)   ~ wet floor (crumb)   % paw passage (secret crumb)
"""
import random
from collections import deque

COLS, ROWS = 31, 17
CW, CH = 15, 8
DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
DOCK_CELLS = ((6, 3), (7, 3), (8, 3))
RING = [(x, 2) for x in range(5, 10)] + [(x, 4) for x in range(5, 10)] + [(5, 3), (9, 3)]
START_CELL = (7, 5)
BOSS_START_CELL = (7, 7)
PLAZA = (4, 2, 7, 4)            # boss stages: cells x 4..10, y 2..5 form an open hall
FLAP = (15, 6)
EXIT = (15, 5)
DOCK = (15, 7)
STAGES = 200

# name, floor a, floor b, wall, wall top, wall side, floor pattern (0 checker 1 planks 2 dots 3 grout 4 stars)
THEMES = [
    ("MIDNIGHT KITCHEN", "ink", "deep", "peach", "cream", "brown", 0),
    ("THE PANTRY", "choco", "brown", "yellow", "cream", "orange", 1),
    ("LAUNDRY ROOM", "night", "darkgray", "sky", "white", "blue", 3),
    ("BUBBLE BATHROOM", "deep", "purple", "mint", "white", "teal", 3),
    ("COZY LIVING ROOM", "purple", "deep", "orange", "peach", "brown", 1),
    ("GARDEN SHED", "choco", "night", "lime", "white", "teal", 1),
    ("GREENHOUSE", "night", "ink", "mint", "lime", "teal", 2),
    ("DUSTY ATTIC", "choco", "brown", "peach", "cream", "choco", 1),
    ("BASEMENT", "night", "darkgray", "gray", "white", "darkgray", 3),
    ("MOONLIT ROOF", "night", "ink", "lavender", "white", "purple", 4),
    ("NIGHT BAKERY", "brown", "choco", "pink", "white", "hotpink", 0),
    ("FISH MARKET", "blue", "deep", "sky", "white", "teal", 3),
    ("TOY STORE", "purple", "ink", "yellow", "white", "orange", 2),
    ("OLD LIBRARY", "choco", "night", "red", "peach", "choco", 1),
    ("MUSIC ROOM", "ink", "night", "lavender", "white", "purple", 0),
    ("TEA HOUSE", "night", "teal", "lime", "cream", "teal", 1),
    ("SNOWY CABIN", "deep", "ink", "white", "white", "sky", 2),
    ("LIGHTHOUSE", "night", "blue", "orange", "yellow", "red", 3),
    ("NIGHT TRAIN", "darkgray", "night", "hotpink", "pink", "purple", 1),
    ("THE CAT CASTLE", "purple", "night", "yellow", "white", "orange", 4),
]

BONUS_THEMES = {
    "mice": ("PARTY TIME", "purple", "deep", "pink", "white", "hotpink", 2),
    "fish": ("FISH FRENZY", "blue", "night", "sky", "white", "teal", 3),
}

# curated furniture motifs: blocked cells (x, y, w, h) on the left half (mirrored onto the right)
LAYOUTS = [
    ("CROSSROADS", [], 4),
    ("TWIN TABLES", [(1, 1, 2, 1), (1, 6, 2, 1)], 3),
    ("THE ISLAND", [(2, 2, 2, 2)], 3),
    ("PILLAR HALL", [(1, 1, 1, 1), (3, 1, 1, 1), (1, 5, 1, 1), (3, 6, 1, 1)], 2),
    ("SHELF ROW", [(1, 3, 3, 1)], 4),
    ("CORNER NOOK", [(0, 0, 2, 1), (0, 7, 2, 1)], 4),
    ("STOVE TOP", [(2, 1, 2, 1), (2, 5, 2, 2)], 3),
    ("LONG COUNTER", [(1, 2, 1, 4)], 3),
    ("L-BEND", [(1, 1, 2, 1), (1, 2, 1, 1), (3, 5, 1, 2)], 3),
    ("DINER BOOTHS", [(0, 2, 1, 1), (0, 5, 1, 1), (2, 0, 1, 1), (2, 7, 1, 1)], 4),
    ("BIG FRIDGE", [(0, 3, 2, 2)], 3),
    ("ZIGZAG HALL", [(1, 1, 1, 2), (3, 2, 1, 2), (1, 5, 1, 2)], 3),
    ("PANTRY SHELVES", [(1, 1, 3, 1), (1, 6, 3, 1)], 3),
    ("TEA PARTY", [(2, 3, 1, 2), (5, 6, 2, 1)], 3),
    ("SNACK LOOP", [(5, 0, 2, 1), (0, 4, 1, 2)], 4),
    ("CAT TOWER", [(3, 0, 1, 2), (3, 6, 1, 2), (0, 3, 1, 2)], 3),
]

BOT_KINDS = ("sniffy", "zig", "fridgy", "snoozy", "mopsy", "spritz", "ruff")
# tier at which each bot joins the roster
BOT_TIER = {"sniffy": 0, "zig": 0, "fridgy": 1, "snoozy": 2, "mopsy": 3, "spritz": 5, "ruff": 6}
INTRO = {
    (0, 0): "SNIFFY FOLLOWS YOUR PAW SCENT!",
    (0, 1): "ZIGZAG ALWAYS SWITCHES SIDES!",
    (0, 2): "TAP A TURN EARLY - NORI TAKES IT!",
    (1, 0): "FRIDGY GUARDS ITS SPOT - KEEP AWAY!",
    (1, 1): "CUPBOARD DOORS OPEN AND CLOSE!",
    (2, 0): "SNOOZY WAKES IF YOU EAT NEARBY!",
    (2, 1): "MOUSE HOLES WRAP AROUND!",
    (3, 0): "WET FLOOR: NO TURNING - YOU SLIDE!",
    (3, 1): "MOPSY MOPS A SLIPPERY TRAIL!",
    (4, 0): "PAW PRINTS: SECRET CAT-ONLY PATHS!",
    (4, 1): "JINGLE BELLS FREEZE THE BOTS!",
    (5, 0): "SPRITZ SPRAYS DOWN LONG HALLS!",
    (6, 0): "RUFF BARKS, THEN DASHES AT YOU!",
    (8, 2): "LIGHTS OUT! THE BOTS GLOW RED.",
}
QUIPS = ["MRRP! SNACK RAID TIME.", "SHH... THE BOTS ARE NEAR.", "THOSE CRUMBS SMELL FISHY!",
         "TIPTOE, TIPTOE... JINGLE!", "NOBODY SAW ME. PROBABLY.", "ONE MORE CRUMB. OK, TEN.",
         "THE FRIDGE HUMS A LULLABY.", "MY BELL SAYS HELLO.", "ZOOMIES INCOMING!",
         "I AM A SHADOW. A HUNGRY ONE.", "PURR... TUNA, WHERE ARE YOU?", "VACUUMS? NOT SCARED. MOSTLY."]

BOSSES = {
    "queen": ("QUEEN VACUUMA", ["suck_row", "suck_col", "bunnies"], "suck_cross"),
    "slipper": ("GRANNY'S SLIPPER", ["stomp", "hop", "quake"], "stomp3"),
    "snap": ("SNAPTRAP 3000", ["traps", "snap_row", "snap_col"], "traps_big"),
    "toaster": ("TOASTY TYRANT", ["toast", "pop"], "burn_row"),
    "bucket": ("BUCKET BARON", ["flood", "splash", "drip"], "drip8"),
    "empress": ("VACUUMA EMPRESS", ["suck_row", "suck_col", "bunnies", "stomp", "traps", "toast", "flood"],
                "suck_cross"),
}
BOSS_ORDER = ["queen", "slipper", "snap", "toaster", "bucket"]


def tier_of(n):
    return (n - 1) // 10


# ----------------------------------------------------------------------------- generator
def _mirror(c):
    return (CW - 1 - c[0], c[1])


def _link(a, b):
    return (a, b) if a <= b else (b, a)


def _cells_of(rects):
    out = set()
    for x, y, w, h in rects:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                out.add((xx, yy))
    return out


def carve(rng, rects, loops, mode="normal"):
    """Return (rows, links) or None when the motif set leaves the maze disconnected."""
    blocked = set()
    for c in _cells_of(rects):
        blocked.add(c)
        blocked.add(_mirror(c))
    forced = set()
    if mode == "normal":
        blocked |= set(DOCK_CELLS)
        ring = set(RING)
        assert not (ring & blocked)
        for x in range(5, 9):
            forced.add(_link((x, 2), (x + 1, 2)))
            forced.add(_link((x, 4), (x + 1, 4)))
        for x in (5, 9):
            forced.add(_link((x, 2), (x, 3)))
            forced.add(_link((x, 3), (x, 4)))
    elif mode == "boss":
        px, py, pw, ph = PLAZA
        hall = {(x, y) for x in range(px, px + pw) for y in range(py, py + ph)}
        blocked -= hall
        for (x, y) in hall:
            for dx, dy in ((1, 0), (0, 1)):
                if (x + dx, y + dy) in hall:
                    forced.add(_link((x, y), (x + dx, y + dy)))
    start = BOSS_START_CELL if mode == "boss" else START_CELL
    if start in blocked:
        return None
    # prune pockets: an open cell with <= 1 open neighbour can only be a dead end
    changed = True
    while changed:
        changed = False
        for x in range(CW):
            for y in range(CH):
                c = (x, y)
                if c in blocked or c == start or (mode == "normal" and c in RING):
                    continue
                nb = [(x + dx, y + dy) for dx, dy in DIRS4 if 0 <= x + dx < CW and 0 <= y + dy < CH
                      and (x + dx, y + dy) not in blocked]
                if len(nb) <= 1:
                    blocked.add(c)
                    blocked.add(_mirror(c))
                    changed = True
    open_cells = [(x, y) for x in range(CW) for y in range(CH) if (x, y) not in blocked]
    open_set = set(open_cells)

    def nbrs(c):
        return [(c[0] + dx, c[1] + dy) for dx, dy in DIRS4 if (c[0] + dx, c[1] + dy) in open_set]

    links = set(forced)
    # spanning tree over the left half (x <= 7), randomized Prim from the start cell
    half = {c for c in open_cells if c[0] <= 7}
    seen = {start}
    frontier = [(start, n) for n in nbrs(start) if n in half]
    while frontier:
        i = rng.randrange(len(frontier))
        a, b = frontier.pop(i)
        if b in seen:
            continue
        seen.add(b)
        links.add(_link(a, b))
        frontier.extend((b, n) for n in nbrs(b) if n in half and n not in seen)
    if seen != half:
        return None
    for a, b in list(links):
        links.add(_link(_mirror(a), _mirror(b)))

    def degree(c):
        return sum(1 for n in nbrs(c) if _link(c, n) in links)

    # open every dead end into a loop (mirrored)
    for _ in range(200):
        dead = [c for c in open_cells if c[0] <= 7 and degree(c) <= 1]
        if not dead:
            break
        c = dead[rng.randrange(len(dead))]
        cand = [n for n in nbrs(c) if _link(c, n) not in links]
        if not cand:
            return None
        cand.sort(key=lambda n: (degree(n), rng.random()))
        n = cand[0]
        links.add(_link(c, n))
        links.add(_link(_mirror(c), _mirror(n)))
    # extra loops
    pairs = sorted({_link(c, n) for c in open_cells if c[0] <= 7 for n in nbrs(c)} - links)
    rng.shuffle(pairs)
    for a, b in pairs[:loops]:
        links.add((a, b))
        links.add(_link(_mirror(a), _mirror(b)))
    # rasterize
    g = [["#"] * COLS for _ in range(ROWS)]
    for (x, y) in open_cells:
        g[2 * y + 1][2 * x + 1] = "."
    for a, b in links:
        g[a[1] + b[1] + 1][a[0] + b[0] + 1] = "."
    if mode == "normal":
        for x in range(13, 18):
            g[7][x] = "="
        g[FLAP[1]][FLAP[0]] = "-"
    elif mode == "boss":          # the boss hall is one open floor (no pillars)
        px, py, pw, ph = PLAZA
        for y in range(2 * py + 1, 2 * (py + ph)):
            for x in range(2 * px + 1, 2 * (px + pw)):
                g[y][x] = "."
    sx, sy = 2 * start[0] + 1, 2 * start[1] + 1
    g[sy][sx] = "P"
    return g, links


def walk_ok(ch, cat=True, doors_open=False):
    """Can an entity stand on this tile? cat: Nori (paw passages yes, dock no) / bots (dock + flap yes)."""
    if ch == "#":
        return False
    if ch in "Dd":
        return doors_open
    if ch == "%":
        return cat
    if ch in "=-":
        return not cat
    return True


def bfs(rows, start, cat=True, doors_open=False):
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in DIRS4:
            nx, ny = (x + dx) % COLS, y + dy
            if not 0 <= ny < ROWS or (nx, ny) in dist:
                continue
            if abs(dx) and not (0 <= x + dx < COLS) and rows[y][x] == "#":
                continue
            if walk_ok(rows[ny][nx], cat, doors_open):
                dist[(nx, ny)] = dist[(x, y)] + 1
                q.append((nx, ny))
    return dist


def _find(rows, ch):
    for y, r in enumerate(rows):
        x = r.find(ch)
        if x >= 0:
            return (x, y)
    return None


def _set(g, x, y, ch):
    g[y][x] = ch
    g[y][COLS - 1 - x] = ch


def add_features(rng, g, links, t, i, mode):
    """Stamp catnip, tunnels, doors, wet floor and paw passages (all mirrored)."""
    feats = []
    rows = lambda: ["".join(r) for r in g]  # noqa: E731
    # catnip leaves near the four corners
    if mode == "normal":
        for band in ((0, 1), (6, 7)):
            cand = [(x, y) for x in (0, 1, 2) for y in band if g[2 * y + 1][2 * x + 1] == "."]
            if cand:
                x, y = cand[rng.randrange(len(cand))]
                _set(g, 2 * x + 1, 2 * y + 1, "o")
    # mouse-hole tunnels
    if t >= 2 and mode == "normal" and rng.random() < 0.6 or (t, i) == (2, 1):
        cand = [y for y in (1, 2, 5, 6) if g[2 * y + 1][1] in ".o"]
        if cand:
            y = 2 * cand[rng.randrange(len(cand))] + 1
            g[y][0] = " "
            g[y][COLS - 1] = " "
            feats.append("tunnel")
    start = _find(rows(), "P")
    # cupboard doors on loop links whose cells both keep >= 3 exits
    if t >= 1 and mode == "normal" and (t > 1 or i >= 1):
        want = 1 + (t >= 4) + (t >= 9) + (rng.random() < 0.4)

        def deg(c):
            return sum(1 for dx, dy in DIRS4 if _link(c, (c[0] + dx, c[1] + dy)) in links)
        cand = []
        for a, b in sorted(links):
            if a[0] > 7 or b[0] > 7 or (a[0] == 7 and b[0] == 7):
                continue
            if a in RING or b in RING or START_CELL in (a, b):
                continue
            if deg(a) >= 3 and deg(b) >= 3:
                cand.append((a, b))
        rng.shuffle(cand)
        placed = 0
        for a, b in cand:
            if placed >= want:
                break
            x, y = a[0] + b[0] + 1, a[1] + b[1] + 1
            if g[y][x] != ".":
                continue
            old = g[y][x]
            _set(g, x, y, "D" if placed % 2 == 0 else "d")
            r = rows()
            reach = bfs(r, start, cat=True, doors_open=False)
            need = [(xx, yy) for yy in range(ROWS) for xx in range(COLS) if r[yy][xx] in ".o~"]
            if all(p in reach for p in need):
                placed += 1
            else:
                _set(g, x, y, old)
        if placed:
            feats.append("doors")
    # wet floor runs on straight corridors
    if t >= 3 and mode == "normal":
        runs = 1 + (t >= 5) + (t >= 10) + (rng.random() < 0.5)
        cand = []
        for y in range(1, ROWS - 1):
            for x in range(1, 15):
                if g[y][x] != ".":
                    continue
                h = g[y][x - 1] != "#" and g[y][x + 1] != "#" and g[y - 1][x] == "#" and g[y + 1][x] == "#"
                v = g[y - 1][x] != "#" and g[y + 1][x] != "#" and g[y][x - 1] == "#" and g[y][x + 1] == "#"
                if h or v:
                    cand.append((x, y, 1 if h else 0))
        rng.shuffle(cand)
        for x, y, horiz in cand[:runs]:
            for k in range(-1, 2):
                xx, yy = (x + k, y) if horiz else (x, y + k)
                if 0 < xx < 15 and g[yy][xx] == ".":
                    _set(g, xx, yy, "~")
        feats.append("wet")
    # paw-print passages: closed links that would save the most steps
    if t >= 4 and mode == "normal":
        want = 1 + (t >= 7) + (rng.random() < 0.4)
        r = rows()
        best = []
        for y in range(1, ROWS - 1):
            for x in range(1, 16):
                if g[y][x] != "#" or (x % 2) == (y % 2):
                    continue      # only the wall tiles between two cells
                a, b = ((x - 1, y), (x + 1, y)) if x % 2 == 0 else ((x, y - 1), (x, y + 1))
                if r[a[1]][a[0]] not in ".o~" or r[b[1]][b[0]] not in ".o~" or x == 15:
                    continue
                d = bfs(r, a, cat=True, doors_open=True).get(b, 99)
                if d >= 8:
                    best.append((d + rng.random(), x, y))
        best.sort(reverse=True)
        for _, x, y in best[:want]:
            _set(g, x, y, "%")
        if best:
            feats.append("paw")
    return feats


def spots(rows, start, k=14, rng=None):
    """Cell-centre tiles away from the start: where tuna cans, bells and golden fish appear."""
    d = bfs(rows, start, cat=True, doors_open=True)
    out = [(x, y) for (x, y), v in d.items() if v >= 5 and x % 2 == 1 and y % 2 == 1 and rows[y][x] in ". "]
    out.sort()
    rng.shuffle(out)
    return [list(p) for p in out[:k]]


def corner_spots(rows):
    """Boss stages: the open cell centre nearest to each corner (catnip appears there)."""
    out = []
    for cx, cy in ((1, 1), (COLS - 2, 1), (1, ROWS - 2), (COLS - 2, ROWS - 2)):
        cand = [(abs(x - cx) + abs(y - cy), x, y) for y in range(1, ROWS, 2) for x in range(1, COLS, 2)
                if rows[y][x] == "."]
        _, x, y = min(cand)
        out.append([x, y])
    return out


def roster(t):
    return [k for k in BOT_KINDS if BOT_TIER[k] <= t]


def make_bots(rng, rows, t, i):
    """Bot list [kind, post x, post y]: Sniffy leads, the newest bot of the tier shows up on its intro stage."""
    n = min(5 + (t >= 12), 2 + t // 3 + (i >= 3) + (i >= 7))
    pool = roster(t)
    kinds = ["sniffy"]
    newest = [k for k in pool if BOT_TIER[k] == t and k != "sniffy"]
    if newest and i <= 3:
        kinds.append(newest[0])
    if t == 0 and i == 1:
        kinds.append("zig")
    while len(kinds) < n:
        k = pool[rng.randrange(len(pool))]
        if kinds.count(k) < 2 and (k != "snoozy" or kinds.count(k) < 1 or t >= 6):
            kinds.append(k)
    open_cells = [(x, y) for y in range(1, ROWS, 2) for x in range(1, COLS, 2) if rows[y][x] in ".o~"]
    out = []
    for j, k in enumerate(kinds):
        px = py = 0
        if k in ("fridgy", "snoozy"):
            # guard / nap spots in different quadrants, away from the start
            quad = [(x, y) for x, y in open_cells if (x < 15) == (j % 2 == 0) and (y < 8) == (j % 4 < 2)
                    and abs(x - 15) + abs(y - 11) >= 8]
            quad = quad or open_cells
            px, py = quad[rng.randrange(len(quad))]
        out.append([k, px, py])
    return out


def build_stage(n):
    t, i = tier_of(n), (n - 1) % 10
    rng = random.Random(7919 * n + 17)
    kind = "boss" if i == 9 else "bonus" if i == 4 else "normal"
    for attempt in range(60):
        if kind == "boss":
            li = (t * 3 + attempt) % len(LAYOUTS)
            name, rects, loops = LAYOUTS[li]
            rects = [r for r in rects if r[1] + r[3] <= 2 or r[1] >= 6 or r[0] + r[2] <= 4]
            res = carve(rng, rects, loops + 2, "boss")
        elif kind == "bonus":
            li = rng.randrange(len(LAYOUTS))
            name, rects, loops = LAYOUTS[li]
            res = carve(rng, rects, loops + 6, "bonus")
        else:
            li = (n * 7 + attempt * 5 + t) % len(LAYOUTS)
            name, rects, loops = LAYOUTS[li]
            res = carve(rng, rects, loops + (t >= 10), "normal")
        if res:
            break
    g, links = res
    feats = add_features(rng, g, links, t, i, kind)
    rows = ["".join(r) for r in g]
    start = _find(rows, "P")
    st = {"n": n, "kind": kind, "tier": t, "name": name, "rows": rows, "bots": [], "feats": feats,
          "speed": round(min(0.98, 0.76 + 0.012 * t + 0.003 * i), 3),
          "nip": round(max(3.0, 7.0 - 0.22 * t), 2),
          "release": round(max(1.4, 4.0 - 0.15 * t), 2),
          "door_t": round(max(3.0, 5.5 - 0.1 * t), 2),
          "dark": (t == 8 and i in (2, 6, 8)) or (t == 9 and i in (1, 3, 6, 8)) or (t >= 10 and kind == "normal"
                                                                                     and rng.random() < 0.2),
          "bell": t >= 4 or (t, i) == (4, 1),
          "new": INTRO.get((t, i), ""),
          "quip": QUIPS[(n * 5) % len(QUIPS)],
          "spots": spots(rows, start, rng=rng)}
    if kind == "normal":
        st["bots"] = make_bots(rng, rows, t, i)
    elif kind == "bonus":
        st["bonus"] = "mice" if (n // 10) % 2 == 0 else "fish"
        st["time"] = 30 if st["bonus"] == "mice" else 25
        st["name"] = "MOUSE PARTY" if st["bonus"] == "mice" else "FISH FRENZY"
        st["dark"] = False
    else:
        bk = "empress" if n == STAGES else BOSS_ORDER[t % len(BOSS_ORDER)]
        bname, pats, extra = BOSSES[bk]
        pats = list(pats)
        if t >= 5 and bk != "empress":      # later bosses borrow a move from the next boss in line
            guest = BOSSES[BOSS_ORDER[(t + 1) % len(BOSS_ORDER)]][1][0]
            pats.append(guest)
        if t >= 10 and bk != "empress":
            pats.append(BOSSES[BOSS_ORDER[(t + 2) % len(BOSS_ORDER)]][1][-1])
        suffix = ["", " II", " III", " IV"][min(3, t // 5)] if bk != "empress" else ""
        st["boss"] = {"kind": bk, "name": bname + suffix, "hp": 6 + t // 2 + (3 if bk == "empress" else 0),
                      "rate": round(max(1.5, 3.4 - 0.09 * t), 2), "speed": round(1.6 + 0.06 * t, 2),
                      "patterns": pats, "extra": extra, "tier": t}
        st["name"] = bname + suffix
        st["dark"] = False
        st["nips"] = corner_spots(rows)
    return st


def build_campaign():
    return [build_stage(n) for n in range(1, STAGES + 1)]


def validate(st):
    """Return a list of problems (empty when the stage is fine)."""
    errs = []
    rows = st["rows"]
    if len(rows) != ROWS or any(len(r) != COLS for r in rows):
        return ["bad size"]
    for r in rows:
        if r != r[::-1]:
            errs.append("not mirror-symmetric")
            break
    if sum(r.count("P") for r in rows) != 1:
        errs.append("needs exactly one P")
    start = _find(rows, "P")
    need = [(x, y) for y in range(ROWS) for x in range(COLS) if rows[y][x] in ".o~Dd"]
    if len(need) < 60:
        errs.append("too few crumbs")
    for doors_open in (False, True):
        reach = bfs(rows, start, cat=True, doors_open=doors_open)
        miss = [p for p in need if p not in reach and rows[p[1]][p[0]] not in "Dd"]
        if miss:
            errs.append(f"unreachable crumbs (doors open={doors_open}): {miss[:3]}")
    secret = [(x, y) for y in range(ROWS) for x in range(COLS) if rows[y][x] == "%"]
    reach = bfs(rows, start, cat=True, doors_open=False)
    if any(p not in reach for p in secret):
        errs.append("paw passage unreachable")
    # bots: no dead ends with doors open (outside the dock), and the dock must lead out
    for y in range(ROWS):
        for x in range(COLS):
            ch = rows[y][x]
            if not walk_ok(ch, cat=False, doors_open=True) or ch in "=-":
                continue
            exits = 0
            for dx, dy in DIRS4:
                nx, ny = (x + dx) % COLS, y + dy
                if 0 <= ny < ROWS and walk_ok(rows[ny][nx], cat=False, doors_open=True) and rows[ny][nx] != "-":
                    exits += 1
            if exits < 2:
                errs.append(f"dead end at {(x, y)}")
    if st["kind"] == "normal":
        if rows[FLAP[1]][FLAP[0]] != "-" or rows[DOCK[1]][DOCK[0]] != "=":
            errs.append("dock missing")
        d = bfs(rows, DOCK, cat=False, doors_open=False)
        if EXIT not in d or start not in d:
            errs.append("bots cannot leave the dock")
        if not st["bots"] or st["bots"][0][0] != "sniffy":
            errs.append("bots")
        for k, px, py in st["bots"]:
            if k in ("fridgy", "snoozy") and rows[py][px] not in ".o~":
                errs.append(f"bad post for {k}")
    if st["kind"] == "boss":
        px, py, pw, ph = PLAZA
        for y in range(2 * py + 1, 2 * (py + ph)):
            for x in range(2 * px + 1, 2 * (px + pw)):
                if rows[y][x] == "#" and not (x % 2 == 0 and y % 2 == 0):
                    errs.append("plaza blocked")
                    break
        for x, y in st["nips"]:
            if rows[y][x] == "#":
                errs.append("catnip spot in a wall")
    for x, y in st["spots"]:
        if rows[y][x] not in ". ":
            errs.append("bad spot")
    return errs


CAMPAIGN = build_campaign()
