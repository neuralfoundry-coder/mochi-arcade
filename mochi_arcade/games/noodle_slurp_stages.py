"""NOODLE SLURP campaign data: 200 seeded stages (arenas, goals, hazards, bonus feasts and boss fights) plus the
validator used by the tests. Everything is generated deterministically here and exported to the iOS port through
noodle_slurp.EXPORT, so both platforms play exactly the same stages.

Map characters (32 x 20, row-major, one string per stage):
  .  floor            #  wall             G  gate (a wall until enough dumplings are eaten)
  ~  ice (no turning) <>^v conveyor arrow  1-4 portal pairs     *  chili star (goal item)
  d  feast dumpling (bonus stages)
"""
import math
import random
from collections import deque

from mochi_arcade.arcade import STAGES, is_boss, is_bonus

GW, GH = 32, 20
N = GW * GH
D4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
ARROWS = {">": (1, 0), "<": (-1, 0), "v": (0, 1), "^": (0, -1)}
PORTALS = "1234"

# tier -> what the campaign introduces there (shown as "NEW!" on the stage card)
UNLOCK = {"portals": 2, "rollers": 3, "gates": 4, "ice": 5, "vents": 6, "arrows": 7, "squeeze": 11}
NEW_TEXT = {
    "stars": "CHILI STARS - GRAB THEM ALL!",
    "length": "GROW YOUR NOODLE LONG!",
    "survive": "HANG ON UNTIL THE CLOCK RUNS OUT!",
    "portals": "PORTALS - SLIP THROUGH THE SWIRLS!",
    "rollers": "ROLLING MEATBALLS - BLOCK THEM!",
    "gates": "DOORS OPEN AFTER SOME DUMPLINGS!",
    "ice": "ICE - NO TURNING WHILE SLIDING!",
    "vents": "STEAM VENTS - WAIT FOR THE PUFF!",
    "arrows": "CONVEYORS PUSH YOUR NOODLE!",
    "squeeze": "THE WALLS ARE CLOSING IN!",
}

# 20 kitchen themes, one per tier: name, background, decoration, floor a/b, wall, wall shade, accent
THEMES = [
    ["BAMBOO STEAMER", "choco", "brown", "cream", "peach", "brown", "choco", "lime"],
    ["TEA GARDEN", "teal", "mint", "white", "mint", "teal", "darkgray", "lime"],
    ["NOODLE ALLEY", "orange", "peach", "cream", "peach", "red", "choco", "yellow"],
    ["NIGHT MARKET", "night", "purple", "ink", "deep", "hotpink", "purple", "yellow"],
    ["RAMEN SHOP", "red", "hotpink", "white", "cream", "red", "choco", "orange"],
    ["SUSHI BAR", "blue", "sky", "white", "sky", "blue", "ink", "red"],
    ["MOCHI MILL", "lavender", "pink", "white", "pink", "purple", "ink", "hotpink"],
    ["SPICE CELLAR", "black", "choco", "brown", "choco", "orange", "red", "yellow"],
    ["SNOW KITCHEN", "sky", "white", "white", "sky", "blue", "teal", "mint"],
    ["DUMPLING PALACE", "hotpink", "pink", "peach", "pink", "yellow", "orange", "red"],
    ["RICE TERRACE", "teal", "lime", "lime", "mint", "brown", "choco", "yellow"],
    ["LANTERN PIER", "ink", "blue", "deep", "night", "orange", "red", "yellow"],
    ["HOT POT VOLCANO", "red", "orange", "choco", "brown", "orange", "red", "yellow"],
    ["BENTO FACTORY", "darkgray", "gray", "gray", "lavender", "ink", "black", "mint"],
    ["MOON BAKERY", "night", "lavender", "lavender", "purple", "cream", "yellow", "white"],
    ["STEAM ENGINE", "black", "darkgray", "darkgray", "ink", "brown", "choco", "orange"],
    ["CANDY CLOUDS", "pink", "white", "white", "pink", "hotpink", "purple", "sky"],
    ["STORM GALLEY", "ink", "blue", "sky", "blue", "ink", "night", "yellow"],
    ["SPACE KITCHEN", "black", "darkgray", "night", "ink", "gray", "darkgray", "mint"],
    ["STAR BANQUET", "purple", "lavender", "ink", "deep", "yellow", "orange", "hotpink"],
]

# boss designs: footprint in cells, name, how-to-hurt hint
BOSSES = {
    "crab": {"name": "LADLE CRAB", "w": 6, "h": 3, "hint": "EAT THE CHILI DUMPLINGS IT FLINGS!"},
    "teapot": {"name": "KETTLE DRAKE", "w": 6, "h": 4, "hint": "SLURP THE SUGAR CUBES AFTER A PUFF!"},
    "sushi": {"name": "PLATE GOBBLER", "w": 8, "h": 3, "hint": "BITE THE GOLD PLATES, DODGE THE REST!"},
    "golem": {"name": "MOCHI GOLEM", "w": 6, "h": 4, "hint": "GRAB THE SWEET BEANS IT DROPS!"},
    "ghost": {"name": "FORTUNE SPOOK", "w": 2, "h": 2, "hint": "LOOP YOUR NOODLE AROUND IT!"},
    "bao": {"name": "BAO EMPEROR", "w": 8, "h": 4, "hint": "EAT THE GOLDEN BUNS IT TOSSES!"},
}
BOSS_ORDER = ("crab", "teapot", "sushi", "golem", "ghost")
BOSS_BASE = {"crab": ["sweep", "toss"], "teapot": ["beam", "vents"], "sushi": ["plates"], "golem": ["drop", "quake"],
             "ghost": ["dash"], "bao": ["sweep", "toss", "drop", "plates", "beam"]}
BOSS_EXTRA = ["csweep", "drop", "plates", "vents", "sweep", "toss"]


def tier_of(n):
    return (n - 1) // 10


def xy(c):
    return c % GW, c // GW


def inb(x, y):
    return 0 <= x < GW and 0 <= y < GH


# ----------------------------------------------------------------------------- map helpers
class Map:
    def __init__(self):
        self.g = ["."] * N

    def at(self, x, y):
        return self.g[y * GW + x] if inb(x, y) else "#"

    def put(self, x, y, ch):
        if inb(x, y):
            self.g[y * GW + x] = ch

    def sym(self, x, y, ch, mode):
        for px, py in mirror(x, y, mode):
            self.put(px, py, ch)


def mirror(x, y, mode):
    pts = [(x, y)]
    if mode in ("h", "hv"):
        pts.append((GW - 1 - x, y))
    if mode in ("v", "hv"):
        pts.append((x, GH - 1 - y))
    if mode == "hv":
        pts.append((GW - 1 - x, GH - 1 - y))
    if mode == "r":
        pts.append((GW - 1 - x, GH - 1 - y))
    return pts


def rect(m, x, y, w, h, ch="#", mode="n"):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            m.sym(xx, yy, ch, mode)


def free_around(m, cells, margin=1):
    """True if every cell (and its neighbourhood) is plain floor apart from the cells themselves."""
    own = set(cells)
    for (x, y) in cells:
        if not inb(x, y):
            return False
        for dy in range(-margin, margin + 1):
            for dx in range(-margin, margin + 1):
                px, py = x + dx, y + dy
                if (px, py) in own or not inb(px, py):
                    continue
                if m.at(px, py) != ".":
                    return False
    return True


def sym_cells(cells, mode):
    out = []
    for (x, y) in cells:
        for p in mirror(x, y, mode):
            if p not in out:
                out.append(p)
    return out


# ----------------------------------------------------------------------------- arena templates
def t_open(m, rnd, t):
    if rnd.random() < 0.7:
        rect(m, rnd.randint(3, 6), rnd.randint(2, 4), 2, 2, "#", "hv")


def t_bars(m, rnd, t):
    y, x0 = rnd.randint(4, 6), rnd.randint(4, 7)
    for x in range(x0, GW - x0):
        m.sym(x, y, "#", "v")
    if rnd.random() < 0.5:
        for x in range(14, 18):
            m.sym(x, y, ".", "v")
    if t >= 1 and rnd.random() < 0.5:
        rect(m, x0, y + 1, 1, 2, "#", "hv")


def t_corners(m, rnd, t):
    cx, cy = rnd.randint(3, 6), rnd.randint(2, 4)
    ax, ay = rnd.randint(4, 7), rnd.randint(2, 4)
    rect(m, cx, cy, ax, 1, "#", "hv")
    rect(m, cx, cy, 1, ay, "#", "hv")
    if rnd.random() < 0.7:
        rect(m, 14, 9, 4, 2)


def t_cross(m, rnd, t):
    a, b = rnd.randint(2, 3), rnd.randint(5, 7)
    rect(m, 15, a, 2, b - a + 1, "#", "v")
    c, d = rnd.randint(3, 5), rnd.randint(9, 11)
    rect(m, c, 9, d - c + 1, 2, "#", "h")


def t_pillars(m, rnd, t):
    sx, sy = rnd.choice((6, 7, 8)), rnd.choice((5, 6))
    pw, ph = rnd.choice((1, 2)), rnd.choice((1, 2))
    x0, y0 = rnd.randint(3, 5), rnd.randint(2, 4)
    for y in range(y0, GH // 2 - 1, sy):
        for x in range(x0, GW // 2 - 1, sx):
            rect(m, x, y, pw, ph, "#", "hv")


def t_bowls(m, rnd, t):
    bw, bh = rnd.randint(4, 6), rnd.randint(2, 3)
    xs = (rnd.randint(2, 4), rnd.randint(9, 10)) if rnd.random() < 0.6 else (rnd.randint(4, 7),)
    y = rnd.randint(2, 4)
    for x in xs:
        if x + bw > GW // 2 - 1:
            continue
        rect(m, x, y + bh, bw, 1, "#", "hv")
        rect(m, x, y, 1, bh, "#", "hv")
        rect(m, x + bw - 1, y, 1, bh, "#", "hv")


def t_islands(m, rnd, t):
    mode = rnd.choice(("hv", "h", "r"))
    want = min(7, 3 + t // 4)
    for _ in range(want * 8):
        if want <= 0:
            break
        w, h = rnd.randint(2, 4), rnd.randint(1, 3)
        x, y = rnd.randint(1, GW // 2 - w), rnd.randint(1, GH - h - 1)
        cells = sym_cells([(xx, yy) for yy in range(y, y + h) for xx in range(x, x + w)], mode)
        if free_around(m, cells, 2):
            for (px, py) in cells:
                m.put(px, py, "#")
            want -= 1


def t_lattice(m, rnd, t):
    mode = rnd.choice(("hv", "h", "r"))
    want = min(10, 4 + t // 3)
    for _ in range(want * 10):
        if want <= 0:
            break
        ln = rnd.randint(3, 7)
        if rnd.random() < 0.5:
            x, y = rnd.randint(1, GW // 2 - 2), rnd.randint(1, GH - 2)
            seg = [(x + i, y) for i in range(ln)]
        else:
            x, y = rnd.randint(1, GW // 2 - 2), rnd.randint(1, GH - ln - 1)
            seg = [(x, y + i) for i in range(ln)]
        cells = sym_cells(seg, mode)
        if free_around(m, cells, 2 if t < 8 else 1):
            for (px, py) in cells:
                m.put(px, py, "#")
            want -= 1


def t_zigzag(m, rnd, t):
    gap = rnd.randint(4, 6)
    flip = rnd.random() < 0.5
    for i, y in enumerate((5, 10, 14)):
        left = (i % 2 == 0) != flip
        for x in range(GW):
            if (left and x < GW - gap) or (not left and x >= gap):
                m.put(x, y, "#")


def t_rooms(m, rnd, t):
    variant = rnd.choice(("four", "four", "split"))
    rect(m, 15, 0, 2, GH)
    doors = [(15, rnd.randint(2, 5), 2, 2), (15, rnd.randint(12, 15), 2, 2)]
    if variant == "four":
        rect(m, 0, 9, GW, 2)
        doors += [(rnd.randint(3, 10), 9, 2, 2), (rnd.randint(19, 26), 9, 2, 2)]
    for (x, y, w, h) in doors:
        rect(m, x, y, w, h, "G")
    # one door starts open so the first area is roomy
    x, y, w, h = rnd.choice(doors)
    rect(m, x, y, w, h, ".")


def t_ring(m, rnd, t):
    x0, y0 = rnd.randint(7, 9), rnd.randint(4, 5)
    x1, y1 = GW - 1 - x0, GH - 1 - y0
    for x in range(x0, x1 + 1):
        m.put(x, y0, "#")
        m.put(x, y1, "#")
    for y in range(y0, y1 + 1):
        m.put(x0, y, "#")
        m.put(x1, y, "#")
    rect(m, 15, y0, 2, 1, "G")
    rect(m, 15, y1, 2, 1, "G")
    rect(m, x0, 9, 1, 2, "G")
    rect(m, x1, 9, 1, 2, "G")
    if rnd.random() < 0.5:
        rect(m, 15, 9, 2, 2)


TEMPLATES = {"open": t_open, "bars": t_bars, "corners": t_corners, "cross": t_cross, "pillars": t_pillars,
             "bowls": t_bowls, "islands": t_islands, "lattice": t_lattice, "zigzag": t_zigzag,
             "rooms": t_rooms, "ring": t_ring}
TEMPLATE_TIER = {"open": 0, "bars": 0, "corners": 0, "pillars": 0, "bowls": 0, "cross": 1, "islands": 1,
                 "lattice": 2, "zigzag": 6}


# ----------------------------------------------------------------------------- graph helpers
def solid(ch, gates_open=False):
    return ch == "#" or (ch == "G" and not gates_open)


def portal_map(g):
    pos = {}
    for c, ch in enumerate(g):
        if ch in PORTALS:
            pos.setdefault(ch, []).append(c)
    link = {}
    for cells in pos.values():
        if len(cells) == 2:
            link[cells[0]], link[cells[1]] = cells[1], cells[0]
    return link


def reach(g, start, gates_open=False):
    """Cells reachable from start (4-way moves, portals followed)."""
    link = portal_map(g)
    seen = {start}
    q = deque([start])
    while q:
        c = q.popleft()
        x, y = xy(c)
        for dx, dy in D4:
            nx, ny = x + dx, y + dy
            if not inb(nx, ny):
                continue
            n = ny * GW + nx
            if solid(g[n], gates_open):
                continue
            if g[n] in PORTALS and n in link:
                for k in (n, link[n]):
                    if k not in seen:
                        seen.add(k)
                        q.append(k)
                continue
            if n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def open_neighbours(g, c, gates_open=True):
    x, y = xy(c)
    k = 0
    for dx, dy in D4:
        nx, ny = x + dx, y + dy
        if inb(nx, ny) and not solid(g[ny * GW + nx], gates_open):
            k += 1
    return k


def tidy(m):
    """Fill 1-wide dead ends (a noodle can never turn around in them) and sealed pockets."""
    g = m.g
    changed = True
    while changed:
        changed = False
        for c in range(N):
            if g[c] == "." and open_neighbours(g, c) <= 1:
                g[c] = "#"
                changed = True
    best = None
    seen = set()
    for c in range(N):
        if g[c] != "#" and c not in seen:
            comp = reach(g, c, True) if g[c] != "G" else {c}
            seen |= comp
            if best is None or len(comp) > len(best):
                best = comp
    for c in range(N):
        if g[c] == "." and c not in best:
            g[c] = "#"


def ring_of(c):
    x, y = xy(c)
    return min(x, y, GW - 1 - x, GH - 1 - y)


# ----------------------------------------------------------------------------- feature placement
def find_spawn(m, rnd, length, margin=0, rows=None):
    best = None
    for y in (rows or range(margin, GH - margin)):
        for hx in range(length - 1 + margin, GW - 6 - margin):
            if all(m.at(x, y) == "." for x in range(hx - length + 1, hx + 6)):
                score = abs(y - 11) * 1.2 + abs(hx - 9) * 0.6 + rnd.random() * 2
                if best is None or score < best[0]:
                    best = (score, hx, y)
    return None if best is None else (best[1], best[2])


def spawn_zone(hx, hy, length):
    z = set()
    for x in range(hx - length, hx + 7):
        for y in (hy - 1, hy, hy + 1):
            if inb(x, y) and (y == hy or hx - 1 <= x <= hx + 4):
                z.add(y * GW + x)
    return z


def place_stars(m, rnd, k, spawn, reserved):
    g = m.g
    s = spawn[1] * GW + spawn[0]
    r1, r0 = reach(g, s, True), reach(g, s, False)
    cand = [c for c in sorted(r1) if g[c] == "." and c not in reserved
            and abs(xy(c)[0] - spawn[0]) + abs(xy(c)[1] - spawn[1]) >= 5]
    behind = [c for c in cand if c not in r0]
    rnd.shuffle(cand)
    rnd.shuffle(behind)
    chosen = []

    def ok(c):
        x, y = xy(c)
        return all(abs(x - xy(o)[0]) + abs(y - xy(o)[1]) >= 4 for o in chosen)
    want_behind = (k + 1) // 2 if behind else 0
    for c in behind:
        if len(chosen) >= want_behind:
            break
        if ok(c):
            chosen.append(c)
    for c in cand:
        if len(chosen) >= k:
            break
        if c not in chosen and ok(c):
            chosen.append(c)
    for c in chosen:
        g[c] = "*"
    return len(chosen) == k


def place_portals(m, rnd, pairs, reserved):
    g = m.g
    good = [c for c in range(N) if g[c] == "." and c not in reserved
            and all(m.at(xy(c)[0] + dx, xy(c)[1] + dy) == "." for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
    made = 0
    for pid in range(pairs):
        for _ in range(60):
            if not good:
                break
            a = rnd.choice(good)
            ax, ay = xy(a)
            bx, by = (GW - 1 - ax, ay) if rnd.random() < 0.5 else (GW - 1 - ax, GH - 1 - ay)
            b = by * GW + bx
            if b not in good or abs(ax - bx) + abs(ay - by) < 12:
                continue
            g[a] = g[b] = PORTALS[pid]
            for c in (a, b):
                cx, cy = xy(c)
                for dx in (-2, -1, 0, 1, 2):
                    for dy in (-2, -1, 0, 1, 2):
                        k = (cy + dy) * GW + cx + dx
                        if k in good:
                            good.remove(k)
            made += 1
            break
    return made


def place_ice(m, rnd, patches, reserved):
    g = m.g
    for _ in range(patches):
        w, h = rnd.randint(3, 7), rnd.randint(2, 4)
        x, y = rnd.randint(1, GW - w - 1), rnd.randint(1, GH - h - 1)
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                c = yy * GW + xx
                if g[c] == "." and c not in reserved:
                    g[c] = "~"
    # sliding must never end in a wall: ice may not touch anything solid
    for c in range(N):
        if g[c] == "~":
            x, y = xy(c)
            if any(not inb(x + dx, y + dy) or solid(g[(y + dy) * GW + x + dx]) for dx, dy in D4):
                g[c] = "."


def place_arrows(m, rnd, strips, reserved):
    g = m.g
    made = 0
    for _ in range(strips):
        for _try in range(50):
            ch = rnd.choice("<>^v")
            dx, dy = ARROWS[ch]
            ln = rnd.randint(2, 4)
            x, y = rnd.randint(1, GW - 2), rnd.randint(1, GH - 2)
            cells = [(x + dx * i, y + dy * i) for i in range(ln + 2)]
            if not all(inb(px, py) and m.at(px, py) == "." and (py * GW + px) not in reserved for px, py in cells):
                continue
            # keep the sides of the strip clear too, so arrows never point the noodle along a wall
            if not free_around(m, cells[:ln], 1):
                continue
            for px, py in cells[:ln]:
                g[py * GW + px] = ch
            made += 1
            break
    return made


def run_cells(g, c, dx, dy):
    """Straight run of non-solid cells through c along (dx, dy) in both directions."""
    x, y = xy(c)
    out = [c]
    for s in (1, -1):
        px, py = x + dx * s, y + dy * s
        while inb(px, py) and not solid(g[py * GW + px]):
            out.append(py * GW + px)
            px, py = px + dx * s, py + dy * s
    return out


def place_rollers(m, rnd, k, period, reserved):
    g = m.g
    out = []
    used = set()
    for _ in range(k):
        for _try in range(80):
            c = rnd.randrange(N)
            if g[c] != "." or c in reserved or c in used:
                continue
            dx, dy = rnd.choice(((1, 0), (0, 1)))
            run = run_cells(g, c, dx, dy)
            if len(run) < 5 or any(r in reserved for r in run):
                continue
            if rnd.random() < 0.5:
                dx, dy = -dx, -dy
            x, y = xy(c)
            out.append([x, y, dx, dy, round(period * rnd.uniform(0.9, 1.1), 3)])
            used.update(run)
            break
    return out


def place_vents(m, rnd, k, period, reserved):
    g = m.g
    out = []
    used = set()
    for _ in range(k):
        for _try in range(80):
            c = rnd.randrange(N)
            if g[c] != "." or c in reserved or c in used:
                continue
            x, y = xy(c)
            dirs = list(D4)
            rnd.shuffle(dirs)
            for dx, dy in dirs:
                ln = rnd.randint(2, 4)
                beam = [c]
                px, py = x + dx, y + dy
                while len(beam) <= ln and inb(px, py) and not solid(g[py * GW + px]):
                    beam.append(py * GW + px)
                    px, py = px + dx, py + dy
                if len(beam) >= 3 and not any(b in reserved or b in used for b in beam):
                    out.append([x, y, dx, dy, len(beam) - 1, round(period * rnd.uniform(0.9, 1.15), 3),
                                round(rnd.uniform(0, period), 3)])
                    used.update(beam)
                    break
            else:
                continue
            break
    return out


def vent_beam(v):
    x, y, dx, dy, ln = v[:5]
    return [(y + dy * i) * GW + x + dx * i for i in range(ln + 1)]


# ----------------------------------------------------------------------------- stage builders
def regular(n, rnd, attempt):
    t, slot = tier_of(n), (n - 1) % 10 + 1
    unlocked = [f for f, t0 in UNLOCK.items() if t >= t0 and f != "squeeze"]
    focus = [f for f, t0 in UNLOCK.items() if t0 == t and f != "squeeze"]
    feats = set()
    if focus and (slot == 1 or rnd.random() < 0.85):
        feats.add(focus[0])
    extra = min(len(unlocked), 0 if t < 3 else 1 if t < 9 else 2 if t < 15 else 3)
    others = [f for f in unlocked if f not in feats]
    rnd.shuffle(others)
    for f in others[:extra]:
        if f != "gates" or rnd.random() < 0.35:     # door rooms stay a treat, not every stage
            feats.add(f)
    if attempt > 30:   # fall back to calmer stages if a layout keeps failing validation
        feats = set(sorted(feats)[:1])

    late = {3: "length", 4: "survive", 8: "length" if t % 2 == 0 else "survive"}
    goal = {1: "eat", 2: "stars", 3: "length", 4: "survive", 6: "eat", 7: "stars", 8: late[8], 9: "stars"}[slot]
    if goal == "length" and t < 1:
        goal = "eat"
    if goal == "survive" and t < 3:
        goal = "stars" if slot == 4 else ("length" if t >= 1 else "eat")
    if "gates" in feats and goal in ("length", "survive"):
        goal = "stars"
    squeeze = goal == "survive" and t >= UNLOCK["squeeze"]

    if "gates" in feats:
        tname = rnd.choice(("rooms", "ring"))
    else:
        pool = [k for k, t0 in TEMPLATE_TIER.items() if t >= t0]
        if t == 0:
            tname = ("open", "bars", "corners", "pillars", "bowls", "cross", "bars", "corners", "pillars", "bowls")[slot - 1]
        else:
            tname = rnd.choice(pool)
        if squeeze and tname in ("zigzag",):
            tname = "pillars"
    m = Map()
    TEMPLATES[tname](m, rnd, t)
    tidy(m)

    length = 4
    margin = 3 if squeeze else 0
    sp = find_spawn(m, rnd, length, margin)
    if sp is None:
        return None
    reserved = spawn_zone(sp[0], sp[1], length)
    if squeeze:
        reserved |= {c for c in range(N) if ring_of(c) <= 2}

    if goal == "stars":
        k = min(11, 4 + t // 3 + rnd.randint(0, 1))
        if not place_stars(m, rnd, k, sp, reserved):
            return None
        target = k
    elif goal == "eat":
        target = 6 + t // 2 + rnd.randint(0, 2)
    elif goal == "length":
        target = min(34, 12 + t + rnd.randint(0, 3))
    else:
        target = min(40, 20 + t)
    stars = {c for c in range(N) if m.g[c] == "*"}
    reserved |= stars

    if "portals" in feats:
        place_portals(m, rnd, 2 if (t >= 9 and rnd.random() < 0.5) else 1, reserved)
    if "ice" in feats:
        place_ice(m, rnd, rnd.randint(1, 3), reserved)
    if "arrows" in feats:
        place_arrows(m, rnd, rnd.randint(1, 3), reserved)
    rollers, vents = [], []
    if "rollers" in feats:
        k = min(5, 1 + max(0, t - 3) // 4 + rnd.randint(0, 1))
        rollers = place_rollers(m, rnd, k, max(0.18, 0.42 - 0.012 * (t - 3)), reserved)
    if "vents" in feats:
        k = min(5, 1 + max(0, t - 6) // 4 + rnd.randint(0, 1))
        vents = place_vents(m, rnd, k, max(2.6, 3.6 - 0.05 * (t - 6)), reserved | stars)

    step = round(max(0.08, 0.145 - 0.003 * t - 0.0008 * slot), 4)
    par = {"eat": target * 4.5 + 6, "stars": target * 5 + 8, "length": (target - length) / 2 * 4.5 + 6,
           "survive": 0}[goal]
    new = ""
    if focus and slot == 1:
        new = NEW_TEXT[focus[0]]
    elif n == 2:
        new = NEW_TEXT["stars"]
    elif FIRST_GOAL.get(goal) == n:
        new = NEW_TEXT[goal]
    if squeeze and t == UNLOCK["squeeze"]:
        new = NEW_TEXT["squeeze"]
    gate = 0
    if "G" in m.g:
        gate = min(8, 3 + t // 4)
    st = {"n": n, "kind": "stage", "theme": t, "map": "".join(m.g), "sp": list(sp), "len": length,
          "goal": goal, "target": target, "foods": 2 if t < 6 else 3, "step": step, "par": round(par, 1),
          "gate": gate, "rollers": rollers, "vents": vents,
          "squeeze": [8.0, round((target - 12) / 3.0, 2)] if squeeze else [], "new": new, "tpl": tname}
    return st


FIRST_GOAL = {"length": 13, "survive": 34}   # where each goal type first shows up (tier 1 / tier 3)

FEAST_SHAPES = ("rings", "diamond", "grid", "waves", "heart", "stripes")


def feast_cells(shape):
    """Dumpling patterns for the DUMPLING FEAST bonus stages (about 45-75 dumplings each)."""
    out = set()
    for y in range(1, GH - 1):
        for x in range(1, GW - 1):
            dx, dy = (x - 15.5) / 1.7, y - 9.5
            sx = x if x >= GW // 2 else GW - 1 - x      # mirrored column, keeps patterns symmetric
            if shape == "rings":
                d = math.hypot(dx, dy)
                hit = any(abs(d - r) < 0.55 for r in (3.5, 7.5)) and (x + y) % 2 == 0
            elif shape == "diamond":
                hit = any(abs(abs(x - 15.5) / 2 + abs(dy) - r) < 0.3 for r in (3, 6, 9)) and sx % 2 == 0
            elif shape == "grid":
                hit = x % 3 == 2 and y % 3 == 1
            elif shape == "waves":
                hit = x % 2 == 0 and any(y == int(round(b + math.sin(x * 0.5) * 1.6)) for b in (4, 10, 15))
            elif shape == "heart":
                u, v = (x - 15.5) / 8.0, (12.0 - y) / 8.5
                hit = (u * u + v * v - 1) ** 3 - u * u * v * v * v <= 0 and sx % 2 == 0 and y % 2 == 0
            else:
                hit = (x - y) % 6 == 0 and 2 <= x <= GW - 3 and 2 <= y <= GH - 3
            if hit:
                out.add((x, y))
    return out


def bonus(n, rnd):
    t = tier_of(n)
    kind = "feast" if t % 2 == 0 else "rush"
    m = Map()
    if kind == "rush":
        t_pillars(m, rnd, 0)
    tidy(m)
    sp = find_spawn(m, rnd, 4, 0, rows=range(16, 17)) or find_spawn(m, rnd, 4)
    reserved = spawn_zone(sp[0], sp[1], 4)
    if kind == "feast":
        shape = FEAST_SHAPES[(t // 2) % len(FEAST_SHAPES)]
        for (x, y) in sorted(feast_cells(shape)):
            c = y * GW + x
            if inb(x, y) and m.g[c] == "." and c not in reserved:
                m.g[c] = "d"
    return {"n": n, "kind": "bonus", "theme": t, "map": "".join(m.g), "sp": list(sp), "len": 4,
            "goal": kind, "target": 20, "foods": 0, "step": round(max(0.075, 0.12 - 0.002 * t), 4), "par": 0,
            "gate": 0, "rollers": [], "vents": [], "squeeze": [], "new": "", "tpl": "bonus"}


def boss_kind(n):
    if n in (100, 200):
        return "bao"
    k = n // 10
    return BOSS_ORDER[(k - 1 - (1 if k > 10 else 0)) % len(BOSS_ORDER)]


def boss(n, rnd):
    t = tier_of(n)
    kind = boss_kind(n)
    lvl = t // 5                      # 0..3: how many extra attack types it mixes in
    m = Map()
    if lvl >= 2 and kind != "ghost":
        for (x, y) in ((6, 12), (24, 12)):
            rect(m, x, y, 2, 2)
    sp = (9, 16)
    length = 10 if kind == "ghost" else 6
    pool = list(BOSS_BASE[kind])
    extra = [a for a in BOSS_EXTRA if a not in pool]
    if kind == "ghost":
        extra = ["slips", "drop", "vents"]
    for a in extra[:lvl]:
        pool.append(a)
    base_hp = {"crab": 6, "teapot": 5, "sushi": 5, "golem": 5, "ghost": 3, "bao": 12}[kind]
    hp = base_hp + (lvl * 2 if kind != "ghost" else lvl) + (6 if n == 200 else 0)
    bd = {"kind": kind, "hp": hp, "lvl": lvl, "pool": pool,
          "cool": round(max(1.2, 2.7 - 0.08 * t), 3), "tele": round(max(0.75, 1.25 - 0.025 * t), 3),
          "move": round(max(0.22, 0.55 - 0.016 * t), 3)}
    return {"n": n, "kind": "boss", "theme": t, "map": "".join(m.g), "sp": list(sp), "len": length,
            "goal": "boss", "target": hp, "foods": 2 if kind != "ghost" else 3,
            "step": round(max(0.085, 0.14 - 0.0028 * t), 4), "par": 60 + 4 * hp, "gate": 0, "rollers": [],
            "vents": [], "squeeze": [], "new": "", "boss": bd, "tpl": "boss"}


def build(n):
    if is_boss(n):
        return boss(n, random.Random(n * 7919))
    if is_bonus(n):
        return bonus(n, random.Random(n * 7919))
    for attempt in range(80):
        rnd = random.Random(n * 7919 + attempt * 104729)
        st = regular(n, rnd, attempt)
        if st is not None and not validate(st):
            return st
    raise RuntimeError(f"noodle slurp: no valid layout for stage {n}")


def build_all():
    return [build(n) for n in range(1, STAGES + 1)]


# ----------------------------------------------------------------------------- validation
def validate(st):
    """Return a list of problems (empty when the stage is playable and winnable)."""
    errs = []
    g = list(st["map"])
    if len(g) != N:
        return ["map size"]
    if any(ch not in ".#G~<>^v1234*d" for ch in g):
        errs.append("bad map char")
    hx, hy = st["sp"]
    ln = st["len"]
    body = [hy * GW + hx - i for i in range(ln)]
    ahead = [hy * GW + hx + i for i in range(1, 6)]
    if hx - ln + 1 < 0 or hx + 5 >= GW:
        return ["spawn off board"]
    if any(g[c] != "." for c in body):
        errs.append("spawn body not on floor")
    if any(g[c] not in ".*d" for c in ahead):
        errs.append("spawn runway blocked")
    head = body[0]
    r0, r1 = reach(g, head, False), reach(g, head, True)
    if len(r0) < 60:
        errs.append(f"start area too small ({len(r0)})")
    open_cells = [c for c in range(N) if not solid(g[c], True)]
    if any(c not in r1 for c in open_cells):
        errs.append("unreachable pocket")
    for c in open_cells:
        if g[c] not in "G" and open_neighbours(g, c) < 2:
            errs.append(f"dead end at {xy(c)}")
            break
    stars = [c for c in range(N) if g[c] == "*"]
    if st["goal"] == "stars" and len(stars) != st["target"]:
        errs.append("star count")
    if any(c not in r1 for c in stars):
        errs.append("star unreachable")
    if "G" in g and st["gate"] <= 0:
        errs.append("gates without a key count")
    # ice: sliding never ends in a wall
    for c in range(N):
        if g[c] == "~":
            x, y = xy(c)
            for dx, dy in D4:
                px, py = x + dx, y + dy
                if not inb(px, py) or solid(g[py * GW + px]):
                    errs.append(f"ice touches wall at {(x, y)}")
                    break
    # conveyors push onto open floor
    for c in range(N):
        if g[c] in ARROWS:
            x, y = xy(c)
            dx, dy = ARROWS[g[c]]
            px, py = x + dx, y + dy
            if not inb(px, py) or solid(g[py * GW + px]):
                errs.append(f"arrow into wall at {(x, y)}")
    # portals come in pairs and every way in has a way out
    link = portal_map(g)
    for ch in PORTALS:
        k = g.count(ch)
        if k not in (0, 2):
            errs.append(f"portal {ch} x{k}")
    for a, b in link.items():
        ax, ay = xy(a)
        bx, by = xy(b)
        for dx, dy in D4:
            if inb(ax - dx, ay - dy) and not solid(g[(ay - dy) * GW + ax - dx], True):
                if not inb(bx + dx, by + dy) or solid(g[(by + dy) * GW + bx + dx], True):
                    errs.append(f"portal exit blocked at {(bx, by)}")
    zone = spawn_zone(hx, hy, ln)
    for r in st["rollers"]:
        c = r[1] * GW + r[0]
        if solid(g[c], True):
            errs.append("roller in wall")
        if any(k in zone for k in run_cells(g, c, abs(r[2]), abs(r[3]))):
            errs.append("roller track crosses spawn")
    for v in st["vents"]:
        beam = vent_beam(v)
        if any(not inb(*xy(b)) or solid(g[b], True) for b in beam):
            errs.append("vent beam in wall")
        if any(b in zone for b in beam):
            errs.append("vent near spawn")
    if st["squeeze"]:
        if any(ring_of(c) <= 2 for c in stars + body + ahead):
            errs.append("squeeze covers spawn or stars")
        for r in st["rollers"]:
            if ring_of(r[1] * GW + r[0]) <= 2:
                errs.append("roller in squeeze ring")
    if st["goal"] == "length" and st["target"] > len(r0) // 3:
        errs.append("length goal too long for the room")
    if st["kind"] == "bonus" and st["goal"] == "feast" and g.count("d") < 20:
        errs.append("feast too small")
    return errs
