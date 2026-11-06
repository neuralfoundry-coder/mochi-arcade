"""KITTEN PILE rules: the cat bed grid, groups, gravity, chains and the shared random generator.

Pure logic (no pygame) used by the game scene, the stage generator/validator and the bots.
The iOS port mirrors it in ios/MochiArcade/Games/KittenPileCore.swift - keep the two in step.

Cells are small ints:   0 empty
                        1..5 kittens (ginger, tabby, sooty, snowy, calico)  (+16 star kitten, +32 golden kitten)
                        8 pillow, 9 grandpa (sound asleep), 10 grandpa (yawning), 11 yarn ball, 12 toy mouse
"""

COLS, ROWS = 6, 12
SPAWN_X = 2
STAR, GOLD = 16, 32
PILLOW, GRANDPA, GRANDPA1, YARN, MOUSE = 8, 9, 10, 11, 12
NEED = 4                                   # kittens of one colour that curl up together
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))  # satellite offsets for rot 0..3 (up, right, down, left)
CHAIN_MULT = (1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144, 169, 196, 225, 256, 289, 324)
CHAIN_POWER = (1, 2, 4, 6, 9, 12, 16, 20, 25, 30, 36, 42, 49, 56, 64, 72, 81, 90)
CODE_OF = {".": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "a": 17, "b": 18, "c": 19, "d": 20, "e": 21,
           "P": PILLOW, "G": GRANDPA, "g": GRANDPA1}
CHAR_OF = {v: k for k, v in CODE_OF.items()}


class KRand:
    """xorshift32 - identical sequences in Python and Swift (piece queues, rival moves, pillow columns)."""

    def __init__(self, seed):
        self.s = (seed & 0xFFFFFFFF) or 0x9E3779B9

    def next(self):
        x = self.s
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        self.s = x
        return x

    def below(self, n):
        return self.next() % n if n > 0 else 0

    def chance(self, p):
        return self.next() % 100000 < int(p * 100000)


def stage_seed(n, attempt, salt=0):
    return (n * 2654435761 + attempt * 40503 + salt * 97 + 12345) & 0xFFFFFFFF


def is_kitten(c):
    return c > 0 and not (c & 8)


def kcolor(c):
    return c & 7 if is_kitten(c) else 0


def is_junk(c):
    return c in (PILLOW, GRANDPA, GRANDPA1)


def empty_grid():
    return [[0] * COLS for _ in range(ROWS)]


def parse_rows(rows):
    g = empty_grid()
    for i, r in enumerate(rows):
        y = ROWS - len(rows) + i
        for x, ch in enumerate(r):
            g[y][x] = CODE_OF[ch]
    return g


def grid_rows(g):
    return ["".join(CHAR_OF.get(c, "?") for c in row) for row in g]


def col_height(g, x):
    for y in range(ROWS):
        if g[y][x]:
            return ROWS - y
    return 0


def count_cells(g, fn):
    return sum(1 for row in g for c in row if fn(c))


def apply_gravity(g):
    """Let everything fall. Returns [(x, from_y, to_y)] for the animation."""
    moves = []
    for x in range(COLS):
        dst = ROWS - 1
        for y in range(ROWS - 1, -1, -1):
            c = g[y][x]
            if c:
                if y != dst:
                    g[dst][x] = c
                    g[y][x] = 0
                    moves.append((x, y, dst))
                dst -= 1
    return moves


def find_groups(g, need=NEED):
    """Connected same-colour kittens of size >= need: list of cell lists (sorted, deterministic)."""
    seen = [[False] * COLS for _ in range(ROWS)]
    out = []
    for y in range(ROWS):
        for x in range(COLS):
            k = kcolor(g[y][x])
            if not k or seen[y][x]:
                continue
            comp, stack = [], [(x, y)]
            seen[y][x] = True
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dx, dy in DIRS:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < COLS and 0 <= ny < ROWS and not seen[ny][nx] and kcolor(g[ny][nx]) == k:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if len(comp) >= need:
                out.append(sorted(comp, key=lambda p: (p[1], p[0])))
    return out


def comp_size(g, x, y):
    k = kcolor(g[y][x])
    if not k:
        return 0
    seen = {(x, y)}
    stack = [(x, y)]
    while stack:
        cx, cy = stack.pop()
        for dx, dy in DIRS:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and (nx, ny) not in seen and kcolor(g[ny][nx]) == k:
                seen.add((nx, ny))
                stack.append((nx, ny))
    return len(seen)


def junk_hits(g, cells):
    """Pillows / grandpas next to the popping kittens (each hit once per pop)."""
    hit = set(cells)
    out = []
    for x, y in cells:
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and (nx, ny) not in hit and is_junk(g[ny][nx]):
                hit.add((nx, ny))
                out.append((nx, ny))
    return sorted(out, key=lambda p: (p[1], p[0]))


def hit_junk(g, x, y):
    """One nap's worth of damage: pillows vanish, sound-asleep grandpas start yawning, yawning ones leave."""
    c = g[y][x]
    if c == GRANDPA:
        g[y][x] = GRANDPA1
        return False
    g[y][x] = 0
    return True


def yarn_color(g, x, y):
    """The colour a landed yarn ball puts to sleep: the kitten under it, else the most common one."""
    if y + 1 < ROWS and is_kitten(g[y + 1][x]):
        return kcolor(g[y + 1][x])
    counts = [0] * 6
    for row in g:
        for c in row:
            counts[kcolor(c)] += 1
    best = bestn = 0
    for k in range(1, 6):
        if counts[k] > bestn:
            best, bestn = k, counts[k]
    return best


def mouse_cells(g, x, y, radius):
    """Junk a landed toy mouse squeaks awake (Chebyshev radius)."""
    out = []
    for yy in range(max(0, y - radius), min(ROWS, y + radius + 1)):
        for xx in range(max(0, x - radius), min(COLS, x + radius + 1)):
            if is_junk(g[yy][xx]):
                out.append((xx, yy))
    return out


def step_points(groups, chain, g):
    """Score for one chain step (before upgrades / FEVER)."""
    n = sum(len(gr) for gr in groups)
    colours = {kcolor(g[y][x]) for gr in groups for x, y in gr}
    mult = CHAIN_MULT[min(chain, len(CHAIN_MULT)) - 1] + sum(len(gr) - NEED for gr in groups) + 3 * (len(colours) - 1)
    return 10 * n * max(1, mult)


def step_power(groups, chain):
    """Naps sent at a rival for one chain step."""
    n = sum(len(gr) for gr in groups)
    return n * CHAIN_POWER[min(chain, len(CHAIN_POWER)) - 1] + (3 if chain >= 2 else 0)


def piece_cells(x, y, rot, solo=False):
    """Pivot first, then the satellite."""
    if solo:
        return [(x, y)]
    dx, dy = DIRS[rot]
    return [(x, y), (x + dx, y + dy)]


def fits(g, cells):
    for x, y in cells:
        if x < 0 or x >= COLS or y >= ROWS:
            return False
        if y >= 0 and g[y][x]:
            return False
    return True


def drop_y(g, x, y, rot, solo=False):
    while fits(g, piece_cells(x, y + 1, rot, solo)):
        y += 1
    return y


def place(g, cells_codes):
    """Put a locked piece into the bed: every kitten falls on its own. Returns [(x, y, code)] where each landed
    (y < 0: it bounced out of a full column)."""
    out = []
    for x, y, code in sorted(cells_codes, key=lambda c: -c[1]):     # lowest first
        h = col_height(g, x)
        ty = ROWS - 1 - h
        if ty >= 0:
            g[ty][x] = code
        out.append((x, ty, code))
    return out


def resolve(g, landed=(), mouse_r=1, max_chain=40):
    """Instant resolution (bots, validators, chain generator): specials, then pops until stable.
    Returns (chain, kittens popped, points)."""
    chain = popped = pts = 0
    for x, y, code in landed:
        if y < 0 or g[y][x] != code:
            continue
        if code == YARN:
            k = yarn_color(g, x, y)
            g[y][x] = 0
            if k:
                cells = [(xx, yy) for yy in range(ROWS) for xx in range(COLS) if kcolor(g[yy][xx]) == k]
                chain += 1
                popped += len(cells)
                pts += 10 * len(cells)
                for jx, jy in junk_hits(g, cells):
                    hit_junk(g, jx, jy)
                for cx, cy in cells:
                    g[cy][cx] = 0
        elif code == MOUSE:
            g[y][x] = 0
            for jx, jy in mouse_cells(g, x, y, mouse_r):
                g[jy][jx] = 0
    apply_gravity(g)
    while chain < max_chain:
        groups = find_groups(g)
        if not groups:
            break
        chain += 1
        cells = [p for gr in groups for p in gr]
        pts += step_points(groups, chain, g)
        popped += len(cells)
        for jx, jy in junk_hits(g, cells):
            hit_junk(g, jx, jy)
        for cx, cy in cells:
            g[cy][cx] = 0
        apply_gravity(g)
    return chain, popped, pts


def topped(g):
    return g[0][SPAWN_X] != 0


def placements(g, solo=False):
    """Every reachable (x, rot) landing for a pair spawned at the top (ignores the path, like most bots)."""
    out = []
    for rot in ((0,) if solo else (0, 1, 2, 3)):
        for x in range(COLS):
            cells = piece_cells(x, 0, rot, solo)
            if any(cx < 0 or cx >= COLS for cx, _ in cells):
                continue
            # the pair has to travel along row 0/-1 from the spawn column: every column in between must be open
            lo, hi = min(SPAWN_X, x), max(SPAWN_X, x)
            if any(g[0][cx] for cx in range(lo, hi + 1)) or (not solo and rot in (1, 3) and g[0][x + DIRS[rot][0]]):
                continue
            out.append((x, rot))
    return out


# --------------------------------------------------------------------------- chain construction
# Fixed tetromino shapes as (dx, dh) offsets: dh counts up from the bottom.
TETROS = [
    [(0, 0), (0, 1), (0, 2), (0, 3)], [(0, 0), (1, 0), (2, 0), (3, 0)],
    [(0, 0), (1, 0), (0, 1), (1, 1)],
    [(0, 0), (1, 0), (2, 0), (0, 1)], [(0, 0), (1, 0), (2, 0), (2, 1)], [(0, 0), (1, 0), (2, 0), (1, 1)],
    [(0, 1), (1, 1), (2, 1), (0, 0)], [(0, 1), (1, 1), (2, 1), (2, 0)], [(0, 1), (1, 1), (2, 1), (1, 0)],
    [(0, 0), (0, 1), (0, 2), (1, 0)], [(0, 0), (0, 1), (0, 2), (1, 2)], [(0, 0), (0, 1), (0, 2), (1, 1)],
    [(1, 0), (1, 1), (1, 2), (0, 0)], [(1, 0), (1, 1), (1, 2), (0, 2)], [(1, 0), (1, 1), (1, 2), (0, 1)],
    [(0, 0), (1, 0), (1, 1), (2, 1)], [(0, 1), (1, 1), (1, 0), (2, 0)],
    [(0, 0), (0, 1), (1, 1), (1, 2)], [(1, 0), (1, 1), (0, 1), (0, 2)],
]


def _cols_to_grid(cols):
    g = empty_grid()
    for x, c in enumerate(cols):
        for h, code in enumerate(c):
            g[ROWS - 1 - h][x] = code
    return g


def build_chain(rng, length, ncol, max_h=10, tries=400):
    """Build a bed that tumbles into a `length` chain when a (c, c) pair is dropped upright into column tx.
    Works backwards: each new group is slid *under* part of the previous one so that the previous group only
    reconnects when the new one pops. Returns (rows, colour, column) or None."""
    cols = [[] for _ in range(COLS)]
    prev = None          # cells (x, h) of the newest group in column coordinates
    last_c = 0
    for step in range(length):
        ok = False
        for _ in range(tries):
            c = 1 + rng.below(ncol)
            if c == last_c:
                continue
            shape = TETROS[rng.below(len(TETROS))]
            w = max(dx for dx, _ in shape) + 1
            ax = rng.below(COLS - w + 1)
            if prev:
                # aim at the previous group: slide in under one of its cells
                px, ph = prev[rng.below(len(prev))]
                base = max(0, ph - rng.below(3))
            else:
                base = 0
            cells = [(ax + dx, base + dh) for dx, dh in shape]
            if prev and not any(x == px2 and h <= ph2 for x, h in cells for px2, ph2 in prev):
                continue
            # insert column by column (ascending heights), checking support
            new = [list(cc) for cc in cols]
            good = True
            for x in range(COLS):
                hs = sorted(h for cx, h in cells if cx == x)
                for j, h in enumerate(hs):
                    if h > len(new[x]):
                        good = False
                        break
                    new[x].insert(h, c)
                if not good:
                    break
            if not good or any(len(cc) > max_h for cc in new) or len(new[SPAWN_X]) > max_h - 2:
                continue
            g = _cols_to_grid(new)
            groups = find_groups(g)
            if len(groups) != 1 or len(groups[0]) != NEED:
                continue
            want = {(x, ROWS - 1 - h) for x, h in cells}
            if set(groups[0]) != want:
                continue
            # where did the previous group's cells end up? (shifted up by inserts below them)
            if prev:
                prev_shift = []
                for x, h in prev:
                    k = 0
                    for ch in sorted(ch for cx, ch in cells if cx == x):
                        if ch <= h + k:
                            k += 1
                    prev_shift.append((x, h + k))
                if any(comp_size(g, x, ROWS - 1 - h) >= NEED for x, h in prev_shift):
                    continue
            cols = new
            prev = cells
            last_c = c
            ok = True
            break
        if not ok:
            return None
    # trigger: take the newest group's top cell(s) off a column where they sit on top
    g = _cols_to_grid(cols)
    tops = [x for x in range(COLS) if cols[x] and (x, len(cols[x]) - 1) in prev]
    if not tops:
        return None
    tx = tops[rng.below(len(tops))]
    k = 0
    while cols[tx] and (tx, len(cols[tx]) - 1) in prev and k < 2:
        cols[tx].pop()
        prev = [p for p in prev if p != (tx, len(cols[tx]))]
        k += 1
    g = _cols_to_grid(cols)
    if find_groups(g) or col_height(g, tx) > ROWS - 3:
        return None
    # verify by playing it forward
    test = [row[:] for row in g]
    landed = place(test, [(tx, 0, last_c), (tx, -1, last_c)])
    chain, _, _ = resolve(test, landed)
    if chain != length:
        return None
    return grid_rows(g), last_c, tx


def chain_of(rows, colour, x):
    g = parse_rows(rows)
    landed = place(g, [(x, 0, colour), (x, -1, colour)])
    return resolve(g, landed)[0]
