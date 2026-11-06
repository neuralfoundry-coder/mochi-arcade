"""JELLY STACK rules shared by the game scene, the stage generator and the tests (no pygame here).

The iOS port gets the shapes, rotations and kicks through ios/tools/gen_data.py (GData.jelly*).
"""
BW, BH = 10, 20

# piece shapes in their spawn orientation (rotation states are generated)
SHAPES = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(1, 0), (2, 0), (1, 1), (2, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}
COLORS = {"I": "mint", "O": "peach", "T": "pink", "S": "lavender", "Z": "sky", "J": "lime", "L": "yellow"}

# wall-kick offsets for rotation from state a to state b (x right, y up)
KICKS = {
    (0, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)], (1, 0): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (1, 2): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)], (2, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (2, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)], (3, 2): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (3, 0): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)], (0, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
}
KICKS_I = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)], (1, 0): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)], (2, 1): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)], (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)], (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
}


def rotations(kind):
    size = 4 if kind == "I" else 3 if kind != "O" else 4
    cells = SHAPES[kind]
    out = [cells]
    for _ in range(3):
        if kind == "O":
            out.append(cells)
            continue
        cells = [(size - 1 - y, x) for x, y in cells]
        out.append(cells)
    return out


ROT = {k: rotations(k) for k in SHAPES}
LINE_PTS = {1: 100, 2: 300, 3: 500, 4: 800}
SPAWN_X = 3


def spawn_y(kind):
    return -2 if kind == "I" else -1


def gravity_interval(lv):
    """Seconds per row for a (possibly fractional) speed level 1..20."""
    lv = max(1.0, min(20.0, lv))
    return max(0.016, (0.8 - (lv - 1) * 0.007) ** (lv - 1))


def piece_cells(kind, x, y, rot):
    return [(x + cx, y + cy) for cx, cy in ROT[kind][rot]]


def fits(grid, cells):
    for x, y in cells:
        if x < 0 or x >= BW or y >= BH:
            return False
        if y >= 0 and grid[y][x]:
            return False
    return True


def kick_rotate(grid, kind, x, y, rot, d):
    """Rotate by d (+1 right, -1 left) with wall kicks. Returns the new (x, y, rot) or None."""
    b = (rot + d) % 4
    table = KICKS_I if kind == "I" else KICKS
    for kx, ky in table[(rot, b)]:
        if fits(grid, piece_cells(kind, x + kx, y - ky, b)):
            return x + kx, y - ky, b
    return None


def drop_place(grid, kind, rot, tx):
    """Play a placement like a player: spawn, turn right until `rot`, slide to column `tx`, hard drop.
    Returns the landed cells, or None when that placement can't be reached this way."""
    x, y, r = SPAWN_X, spawn_y(kind), 0
    if not fits(grid, piece_cells(kind, x, y, r)):
        return None
    while r != rot:
        nxt = kick_rotate(grid, kind, x, y, r, 1)
        if nxt is None:
            return None
        x, y, r = nxt
    while x != tx:
        step = 1 if tx > x else -1
        if not fits(grid, piece_cells(kind, x + step, y, r)):
            return None
        x += step
    while fits(grid, piece_cells(kind, x, y + 1, r)):
        y += 1
    return piece_cells(kind, x, y, r)


def clear_full(grid):
    """Remove full rows (plain rules, no ice). Returns how many were removed."""
    full = [y for y in range(BH) if all(grid[y])]
    for y in full:
        del grid[y]
        grid.insert(0, [None] * BW)
    return len(full)
