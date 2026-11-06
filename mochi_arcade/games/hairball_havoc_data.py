"""HAIRBALL HAVOC campaign tables: 20 rooms of Biscuit's house x 10 stages = 200 stages (original design).

Everything here is generated deterministically (random.Random(seed) per stage) from curated rooms, furniture
pieces and enemy rosters, then exported to iOS (hairball_havoc.EXPORT -> GeneratedData.swift), so both
platforms play exactly the same rooms, doors, waves, pets and bosses.

Room grid: the floor is COLS x ROWS tiles of 8 px starting at (IX0, IY0). Doors sit in the top, left and
right walls; waves of robo-toys walk in through them.
"""
import random
from collections import deque

from mochi_arcade.arcade import STAGES, is_boss, is_bonus, tier

TILE = 8
IX0, IY0, IX1, IY1 = 8, 24, 312, 192          # floor rectangle in screen pixels
COLS, ROWS = 38, 21
ZONE = (14, 7, 10, 7)                          # tiles kept clear around Biscuit's start (x, y, w, h)

# ---------------------------------------------------------------- robo-toys
MOUSE, CAR, SOCK, VAC, DRUM, BALL, PLANE, POPBOX, GOLEM, HELI, TOP, MINIBALL, BLOCKLET, GOLD = range(14)
# name, hp, speed, points, first stage, width, height, flies, intro line
KINDS = [
    ("ROBO-MOUSE", 1, 44, 100, 1, 11, 8, 0, "WIND-UP CHASERS"),
    ("ZOOM CAR", 2, 92, 150, 3, 12, 9, 0, "ZIGZAG OFF THE WALLS"),
    ("SOCK PUPPET", 2, 26, 200, 11, 10, 12, 0, "SPITS BUTTONS AT YOU"),
    ("VAC-BOT", 4, 28, 300, 21, 12, 10, 0, "SUCKS UP PETS - HURRY!"),
    ("DRUM BEAR", 3, 22, 250, 31, 12, 12, 0, "BOOM! RINGS OF NOTES"),
    ("BOUNCY BALL", 2, 64, 150, 41, 10, 10, 0, "POP IT: IT SPLITS!"),
    ("PAPER PLANE", 1, 74, 200, 51, 10, 8, 1, "FLIES OVER FURNITURE"),
    ("POP BOX", 3, 30, 300, 61, 10, 10, 0, "SPRING PUNCH - KEEP CLEAR"),
    ("BLOCK GOLEM", 8, 18, 500, 71, 14, 14, 0, "CRUMBLES INTO BLOCKS"),
    ("RC HELI", 3, 46, 350, 91, 12, 9, 1, "DROPS TOY BOMBS"),
    ("SPIN TOP", 4, 64, 400, 111, 10, 10, 0, "SPINS FASTER AND FASTER"),
    ("MINI BALL", 1, 76, 50, 999, 6, 6, 0, ""),
    ("BLOCKLET", 1, 42, 50, 999, 6, 6, 0, ""),
    ("GOLD MOUSE", 3, 88, 0, 999, 11, 8, 0, ""),
]
WEIGHT = {MOUSE: 10, CAR: 5, SOCK: 5, VAC: 3, DRUM: 3, BALL: 4, PLANE: 4, POPBOX: 3, GOLEM: 2, HELI: 3, TOP: 3}
FIELD = [k for k in WEIGHT]                    # kinds that walk in through doors

MODS = ["SWARM", "PET PANIC", "CROWDED", "RUSH", "LIGHTS OUT", "SLIPPERY", "ELITE"]
MOD_UNLOCK = {"SWARM": 1, "PET PANIC": 2, "CROWDED": 3, "RUSH": 4, "LIGHTS OUT": 6, "SLIPPERY": 8, "ELITE": 10}
MOD_TEXT = {"SWARM": "MICE EVERYWHERE!", "PET PANIC": "LOTS OF PETS TO SAVE", "CROWDED": "SO MUCH FURNITURE",
            "RUSH": "THE TOYS ARE FAST!", "LIGHTS OUT": "STAY IN THE LIGHT",
            "SLIPPERY": "WET FLOOR - SLIDEY PAWS", "ELITE": "PURPLE TOYS ARE TOUGH"}

# ---------------------------------------------------------------- furniture: name, sizes (tiles), style, top, front
# "A" / "B" = the room's accent colours
FURN = [
    ("SOFA", [[6, 3], [5, 3]], "cushion", "A", "B"),
    ("ARMCHAIR", [[3, 3]], "cushion", "A", "B"),
    ("TABLE", [[4, 3], [3, 3], [6, 3]], "wood", "peach", "brown"),
    ("PLANT", [[2, 2]], "plant", "orange", "brown"),
    ("SHELF", [[5, 2], [2, 5]], "shelf", "brown", "choco"),
    ("BED", [[5, 6], [4, 5]], "bed", "A", "B"),
    ("BOX", [[2, 2], [3, 2]], "box", "peach", "brown"),
    ("COUNTER", [[8, 2], [6, 2]], "counter", "white", "A"),
    ("FRIDGE", [[3, 3]], "fridge", "white", "gray"),
    ("TUB", [[6, 3]], "tub", "white", "gray"),
    ("PIANO", [[6, 3]], "piano", "darkgray", "black"),
    ("CRATE", [[3, 3], [2, 2]], "crate", "brown", "choco"),
    ("LAMP", [[2, 2]], "lamp", "yellow", "orange"),
    ("TV", [[5, 2]], "tv", "darkgray", "black"),
    ("CHEST", [[4, 2]], "chest", "orange", "brown"),
    ("BARREL", [[2, 2]], "barrel", "brown", "choco"),
    ("BLOCKS", [[2, 2]], "blocks", "red", "choco"),
    ("ARCADE", [[3, 3]], "arcade", "purple", "ink"),
    ("WASHER", [[3, 3]], "washer", "white", "gray"),
    ("BENCH", [[6, 3]], "bench", "orange", "brown"),
    ("GEAR", [[3, 3]], "gear", "yellow", "orange"),
    ("POOL TABLE", [[7, 4]], "pool", "teal", "choco"),
]
SOFA, ARMCHAIR, TABLE, PLANT, SHELF, BED, BOX, COUNTER, FRIDGE, TUB, PIANO, CRATE, LAMP, TV, CHEST, BARREL, \
    BLOCKS, ARCADE, WASHER, BENCH, GEAR, POOL = range(len(FURN))

# ---------------------------------------------------------------- the 20 rooms of the house (one per tier)
# name, floor style, floor a, floor b, wall, wall stripe, accent A, accent B, furniture kinds, landmark, Biscuit's quip
ROOMS = [
    ("LIVING ROOM", "planks", "brown", "choco", "peach", "orange", "pink", "hotpink",
     [SOFA, ARMCHAIR, TABLE, PLANT, LAMP, SHELF], TV, "NOT ON MY SOFA!"),
    ("KITCHEN", "checker", "teal", "darkgray", "mint", "white", "sky", "blue",
     [FRIDGE, TABLE, PLANT, BOX, COUNTER], COUNTER, "PAWS OFF MY TUNA!"),
    ("BEDROOM", "carpet", "purple", "deep", "lavender", "pink", "sky", "blue",
     [BED, CHEST, LAMP, BOX, SHELF, PLANT], BED, "WHO WOKE ME UP?!"),
    ("BATHROOM", "tiles", "blue", "darkgray", "sky", "white", "mint", "teal",
     [TUB, BARREL, PLANT, BOX, COUNTER], TUB, "NO BATHS. EVER."),
    ("NURSERY", "carpet", "deep", "purple", "pink", "yellow", "yellow", "orange",
     [BED, BLOCKS, CHEST, ARMCHAIR, LAMP], CHEST, "SHH... KITTENS NAPPING!"),
    ("LIBRARY", "planks", "choco", "ink", "brown", "orange", "red", "choco",
     [SHELF, ARMCHAIR, TABLE, LAMP, PLANT], SHELF, "QUIET IN THE LIBRARY!"),
    ("MUSIC ROOM", "carpet", "ink", "deep", "red", "hotpink", "lavender", "purple",
     [PIANO, BARREL, ARMCHAIR, SHELF, LAMP], PIANO, "THIS IS MY CONCERT!"),
    ("LAUNDRY", "tiles", "darkgray", "gray", "sky", "blue", "peach", "orange",
     [WASHER, BARREL, BOX, COUNTER], WASHER, "MY WARM TOWEL PILE!"),
    ("ATTIC", "planks", "brown", "choco", "choco", "brown", "peach", "orange",
     [CRATE, BOX, CHEST, BARREL, LAMP], CHEST, "DUSTY... I LOVE IT."),
    ("BASEMENT", "stone", "darkgray", "ink", "gray", "darkgray", "gray", "darkgray",
     [CRATE, BARREL, BOX, SHELF, WASHER], WASHER, "SPOOKY. I'M BRAVE."),
    ("GARAGE", "stone", "gray", "darkgray", "darkgray", "yellow", "yellow", "orange",
     [BENCH, CRATE, BARREL, BOX], BENCH, "SMELLS LIKE TIRES."),
    ("GREENHOUSE", "tiles", "teal", "deep", "mint", "lime", "lime", "teal",
     [PLANT, PLANT, TABLE, BARREL, ARMCHAIR], PLANT, "ZOOMIES IN THE FERNS!"),
    ("GAME ROOM", "carpet", "night", "purple", "purple", "hotpink", "hotpink", "purple",
     [ARCADE, POOL, ARMCHAIR, LAMP], ARCADE, "HIGH SCORE TIME!"),
    ("DINING HALL", "checker", "choco", "brown", "red", "orange", "orange", "brown",
     [TABLE, ARMCHAIR, PLANT, SHELF, LAMP], SHELF, "IS THAT SALMON?!"),
    ("STUDY", "planks", "choco", "brown", "teal", "mint", "teal", "blue",
     [TABLE, SHELF, ARMCHAIR, LAMP, CHEST], SHELF, "I SIT ON KEYBOARDS."),
    ("PLAYROOM", "carpet", "blue", "deep", "yellow", "orange", "hotpink", "red",
     [BLOCKS, CHEST, CRATE, BOX, ARMCHAIR], CHEST, "THE TOYS STARTED IT!"),
    ("SUNROOM", "tiles", "orange", "brown", "yellow", "white", "lime", "teal",
     [PLANT, ARMCHAIR, TABLE, LAMP], PLANT, "MY SUNBEAM. MINE."),
    ("WORKSHOP", "planks", "darkgray", "ink", "brown", "choco", "orange", "red",
     [BENCH, CRATE, BARREL, BLOCKS, SHELF], BENCH, "SO THIS IS WHERE...!"),
    ("TOY FACTORY", "stone", "ink", "night", "darkgray", "red", "red", "hotpink",
     [BENCH, CRATE, BARREL, BOX, BLOCKS, GEAR], BENCH, "SHUT IT ALL DOWN!"),
    ("CLOCKWORK CORE", "tiles", "night", "purple", "purple", "yellow", "yellow", "orange",
     [GEAR, CRATE, BARREL, BLOCKS], GEAR, "TIME TO UNWIND THEM!"),
]

# ---------------------------------------------------------------- bosses
# name, minion kind, box (w, h) for hits/contact, parts [dx, dy, r, share of hp], attack family, intro line
BOSSES = [
    ("MECHA SQUEAK", MOUSE, [40, 30], [], ["fan", "charge", "summon", "rain", "spiral", "lane"],
     "A GIANT CLOCKWORK MOUSE!"),
    ("DUST FORT", VAC, [52, 30], [[-19, -9, 6, 0.12], [19, -9, 6, 0.12]],
     ["suck", "ring", "turret", "charge", "summon", "spiral"], "THE ROBOT VACUUM FORTRESS!"),
    ("KING BOING", POPBOX, [32, 28], [], ["lane", "hop", "fan", "spiral", "summon", "ring"],
     "THE JACK-IN-THE-BOX KING!"),
    ("SOCKTOPUS", SOCK, [34, 26], [[-30, 10, 5, 0.08], [-15, 24, 5, 0.08], [15, 24, 5, 0.08], [30, 10, 5, 0.08]],
     ["lane", "fan", "turret", "rain", "ring", "summon"], "EIGHT SOCKS... WELL, FOUR."),
    ("CHOO-CHOO CHIEF", CAR, [24, 18], [], ["turret", "fan", "charge", "rain", "ring", "summon"],
     "ALL ABOARD THE TOY TRAIN!"),
    ("WIND-UP KING", MOUSE, [44, 32], [], ["fan", "charge", "suck", "lane", "rain", "spiral", "ring", "summon", "hop"],
     "THE TOYMAKER'S MASTERPIECE!"),
]
EXTRA_ATTACKS = ["ring", "spiral", "rain", "fan"]
ATTACKS = ["fan", "ring", "spiral", "charge", "hop", "summon", "suck", "lane", "rain", "turret"]


# ---------------------------------------------------------------- geometry helpers (mirrored in Swift)
def door_rect(side, pos):
    """Screen rectangle of a doorway. side 0 = top wall, 1 = left wall, 2 = right wall."""
    if side == 0:
        return IX0 + pos * TILE, IY0 - 14, TILE * 3, 14
    if side == 1:
        return 0, IY0 + pos * TILE, IX0, TILE * 3
    return IX1, IY0 + pos * TILE, W_SCREEN - IX1, TILE * 3


W_SCREEN = 320


def door_spawn(side, pos):
    """Where a toy appears when it walks in, and the inward direction."""
    if side == 0:
        return IX0 + pos * TILE + 12, IY0 + 6, 0, 1
    if side == 1:
        return IX0 + 6, IY0 + pos * TILE + 12, 1, 0
    return IX1 - 6, IY0 + pos * TILE + 12, -1, 0


def door_zone(side, pos):
    """Tiles in front of a door that must stay free of furniture."""
    if side == 0:
        return pos - 1, 0, 5, 4
    if side == 1:
        return 0, pos - 1, 4, 5
    return COLS - 4, pos - 1, 4, 5


def _overlap(a, b, gap=0):
    return a[0] - gap < b[0] + b[2] and b[0] - gap < a[0] + a[2] and a[1] - gap < b[1] + b[3] and b[1] - gap < a[1] + a[3]


# ---------------------------------------------------------------- generation
def make_doors(rng, k, sides=None):
    order = sides or [0, 1, 2, 0, 2, 1]
    doors = []
    for side in order[:k]:
        hi = COLS - 5 if side == 0 else ROWS - 6
        for _ in range(60):
            pos = rng.randint(3, hi)
            if all(d[0] != side or abs(d[1] - pos) >= 7 for d in doors):
                doors.append([side, pos])
                break
    return doors


def _fits(rect, pieces, zones):
    x, y, w, h = rect
    if x < 0 or y < 0 or x + w > COLS or y + h > ROWS:
        return False
    for d in (x, y, COLS - x - w, ROWS - y - h):     # flush against a wall, or a 2-tile corridor
        if d == 1:
            return False
    if any(_overlap(rect, z) for z in zones):
        return False
    return not any(_overlap(rect, p[1:], 2) for p in pieces)


def place_furniture(rng, room, count, doors, sym, landmark=True, kinds=None):
    zones = [ZONE] + [door_zone(*d) for d in doors]
    pieces = []
    kinds = kinds or ROOMS[room][8]
    if landmark:
        k = ROOMS[room][9]
        w, h = rng.choice(FURN[k][1])
        for _ in range(40):
            x = rng.randint(0, COLS - w)
            if _fits((x, 0, w, h), pieces, zones):
                pieces.append([k, x, 0, w, h])
                if sym and x + w <= COLS // 2 - 1 and _fits((COLS - x - w, 0, w, h), pieces, zones):
                    pieces.append([k, COLS - x - w, 0, w, h])
                break
    tries = 0
    while len(pieces) < count and tries < 300:
        tries += 1
        k = rng.choice(kinds)
        w, h = rng.choice(FURN[k][1])
        flush = rng.random() < 0.3
        if flush:
            side = rng.randrange(3)
            x = 0 if side == 0 else (COLS - w if side == 1 else rng.randint(2, COLS - w - 2))
            y = rng.randint(2, ROWS - h - 2) if side < 2 else ROWS - h
        else:
            x = rng.randint(2, COLS - w - 2)
            y = rng.randint(2, ROWS - h - 2)
        if not _fits((x, y, w, h), pieces, zones):
            continue
        pieces.append([k, x, y, w, h])
        mx = COLS - x - w
        if sym and len(pieces) < count and mx >= x + w + 2 and _fits((mx, y, w, h), pieces, zones):
            pieces.append([k, mx, y, w, h])
    return pieces


def walkable(pieces):
    grid = [[True] * COLS for _ in range(ROWS)]
    for _, x, y, w, h in pieces:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                grid[yy][xx] = False
    return grid


def reach(grid, start=(19, 10)):
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and grid[ny][nx] and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def door_tile(side, pos):
    if side == 0:
        return pos + 1, 0
    if side == 1:
        return 0, pos + 1
    return COLS - 1, pos + 1


def place_pets(rng, count, pieces, doors, seen, golden=False):
    grid = walkable(pieces)
    out = []
    spots = [(x, y) for (x, y) in seen
             if all(0 <= x + dx < COLS and 0 <= y + dy < ROWS and grid[y + dy][x + dx]
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1))
             and not _overlap((x, y, 1, 1), ZONE)
             and all(abs(x - door_tile(*d)[0]) + abs(y - door_tile(*d)[1]) >= 6 for d in doors)]
    spots.sort()
    rng.shuffle(spots)
    for x, y in spots:
        if len(out) >= count:
            break
        if all(abs(x - p[1]) + abs(y - p[2]) >= 4 for p in out):
            out.append([rng.randrange(2) if not golden or out else 2, x, y, rng.randrange(4)])
    return out


def make_spawns(rng, n, t, doors, mods, new):
    total = int(12 + 2.3 * t + ((n - 1) % 10) * 0.8)
    if "SWARM" in mods:
        total = int(total * 1.4)
    kinds = [k for k in FIELD if KINDS[k][4] <= n]
    ws = [WEIGHT[k] * (0.6 if k == MOUSE and t >= 6 else 1) for k in kinds]
    out = []
    time = 0.6
    left = total
    gap = max(2.4, 5.6 - 0.16 * t)
    first = True
    heavy = 0
    while left > 0:
        size = min(left, rng.randint(3, 5 + t // 4))
        ds = rng.sample(range(len(doors)), min(len(doors), rng.choice((1, 1, 2, 2, 3))))
        theme = rng.choices(kinds, ws)[0] if rng.random() < 0.5 else -1
        for i in range(size):
            if new >= 0 and first and i < 3:
                k = new
            elif "SWARM" in mods and rng.random() < 0.5:
                k = MOUSE
            elif theme >= 0 and rng.random() < 0.6:
                k = theme
            else:
                k = rng.choices(kinds, ws)[0]
            if k == GOLEM:
                heavy += 1
                if heavy > 2 + t // 6:
                    k = MOUSE
            elite = 1 if "ELITE" in mods and k != MOUSE and rng.random() < 0.35 else 0
            out.append([k, ds[i % len(ds)], round(time + i * 0.45, 2), elite])
        left -= size
        time += gap * rng.uniform(0.8, 1.2) + size * 0.3
        first = False
    return out


def boss_phases(rng, kind, lv, final):
    fam = BOSSES[kind][4]
    nphase = 4 if final else (2 if lv == 0 else 3)
    out = []
    for p in range(nphase):
        k = min(len(fam), 2 + p + lv)
        pool = list(fam[:k])
        if lv >= 2 and not final:
            pool += [a for a in EXTRA_ATTACKS if a not in pool][:lv - 1]
        rng.shuffle(pool)
        out.append(pool)
    return out


def gen_stage(n):
    t = tier(n)
    rng = random.Random(n * 7919 + 17)
    room = t
    st = {"n": n, "room": room, "type": "normal", "mods": [], "new": -1, "rug": None, "pets": [], "spawns": []}
    if is_boss(n):
        final = n == STAGES
        kind = 5 if final else t % 5
        lv = t // 5
        st["type"] = "boss"
        st["doors"] = [[0, 6], [0, 29]]
        cover = [CRATE, BOX, BARREL, BLOCKS] if room >= 8 else [BOX, PLANT, BARREL]
        st["furn"] = place_furniture(rng, room, 4, st["doors"], True, landmark=False, kinds=cover)
        name = BOSSES[kind][0] + ("" if lv == 0 or final else f" MK{lv + 1}")
        st.update({"boss": kind, "lv": lv, "final": final, "name": name,
                   "hp": int(200 * (1 + 0.25 * t) ** 1.8 * (1.3 if final else 1.0)),
                   "phases": boss_phases(rng, kind, lv, final),
                   "rest": round(max(0.7, 1.5 - 0.12 * lv - 0.02 * t), 2),
                   "bv": min(150, 74 + 3 * t), "cars": min(6, 3 + lv), "par": 60 + 3 * t})
        st["nphase"] = len(st["phases"])
        return st
    if is_bonus(n):
        st["type"] = "bonus"
        if t % 2 == 0:              # TOY PARADE: harmless toys march across the room - pop them all
            st["mode"] = "parade"
            st["doors"] = [[0, 7], [0, 28], [1, 4], [1, 13], [2, 4], [2, 13]]
            st["furn"] = []
            kinds = [k for k in FIELD if KINDS[k][4] <= max(n, 3) and k not in (GOLEM, POPBOX)]
            lanes = []
            for i in range(12):
                count = 5 + rng.randint(0, 2 + t // 6)
                gold = rng.randrange(count) if rng.random() < 0.35 else -1
                lanes.append([rng.choice(kinds), i % 6 if i < 6 else rng.randrange(6), round(0.8 + i * 1.45, 2),
                              count, gold])
            st["lanes"] = lanes
            st["dur"] = 24.0
        else:                       # KITTEN ROUNDUP: scoop up a room full of runaway pets
            st["mode"] = "roundup"
            st["doors"] = [[0, 17]]
            st["furn"] = place_furniture(rng, room, 3, st["doors"], True)
            seen = reach(walkable(st["furn"]))
            st["pets"] = place_pets(rng, 20 + t // 3, st["furn"], st["doors"], seen, golden=True)
            st["dur"] = 20.0
        st["par"] = int(st["dur"])
        return st
    # ---- normal stage
    new = next((k for k in FIELD if KINDS[k][4] == n), -1)
    mods = []
    if t >= 1 and new < 0:
        pool = [m for m in MODS if MOD_UNLOCK[m] <= t]
        if rng.random() < min(0.85, 0.35 + 0.03 * t):
            mods.append(rng.choice(pool))
            if t >= 12 and rng.random() < 0.35:
                m2 = rng.choice(pool)
                if m2 not in mods:
                    mods.append(m2)
    ndoors = min(5, 2 + t // 4 + rng.randint(0, 1))
    for attempt in range(50):
        doors = make_doors(rng, ndoors)
        count = min(10, 4 + t // 4 + rng.randint(0, 2)) + (4 if "CROWDED" in mods else 0)
        furn = place_furniture(rng, room, count, doors, rng.random() < 0.55)
        seen = reach(walkable(furn))
        if all(door_tile(*d) in seen for d in doors):
            break
    npets = min(4, 1 + t // 4) + rng.randint(0, 1) + (3 if "PET PANIC" in mods else 0)
    pets = place_pets(rng, npets, furn, doors, seen)
    rug = None
    if rng.random() < 0.6:
        rw, rh = rng.randint(8, 14), rng.randint(5, 8)
        rug = [19 - rw // 2, 10 - rh // 2, rw, rh, rng.randrange(3)]
    spawns = make_spawns(rng, n, t, doors, mods, new)
    st.update({"doors": doors, "furn": furn, "pets": pets, "rug": rug, "mods": mods, "new": new, "spawns": spawns,
               "spd": round(min(1.6, 1 + 0.035 * t) * (1.2 if "RUSH" in mods else 1.0), 3),
               "hpx": round(1 + 0.08 * t, 2),
               "fire": round(max(1.2, 3.4 * 0.95 ** t), 2),
               "bv": min(140, 70 + int(3.5 * t)),
               "max_on": min(24, 7 + t // 2 + (4 if "SWARM" in mods else 0)),
               "par": int(25 + len(spawns) * 1.5)})
    return st


STAGE_TABLE = [gen_stage(n) for n in range(1, STAGES + 1)]


def stage(n):
    return STAGE_TABLE[max(1, min(STAGES, n)) - 1]


EXPORT = {
    "kinds": [list(k) for k in KINDS],
    "furn": [list(f) for f in FURN],
    "rooms": [list(r) for r in ROOMS],
    "bosses": [list(b) for b in BOSSES],
    "mod_text": MOD_TEXT,
    "stages": STAGE_TABLE,
}
