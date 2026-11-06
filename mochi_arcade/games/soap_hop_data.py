"""SOAP HOP stage data: curated platform templates, tier themes, the seeded 200-stage generator and a
reachability validator. Pure Python (no pygame) so tests and ios/tools/gen_data.py can use it.

The finished campaign is exported to the iOS port as soap_hop.EXPORT, so both platforms play exactly the
same 200 stages. Map cells: '#' solid block, '=' one-way platform (jump up through it), '.' air.
"""
import random

COLS, ROWS = 40, 23          # full map: 2-tile side walls, ceiling row 0, floor rows 21-22
IN_W = 36                    # inner width (map columns 2..37)
JUMP_UP = 6                  # rows Momo can rise with a full jump (52 px)
STAGES = 200

# ----------------------------------------------------------------------------- the original eight stages
# 20 inner rows (36 wide, right-padded with '.'); rows 0 and 21-22 are the ceiling and floor.
# g = grump, f = flutter, P = Momo's start. Kept verbatim: they are stages 1-9 of the campaign.
LEVELS = [
    {"name": "HELLO SUDS", "rows": {
        5: "......g................g", 6: "....==========........==========", 10: "...............f",
        11: "..........================", 15: "......g................g",
        16: "....==========........==========", 20: "................P"}},
    {"name": "BUBBLE STAIRS", "rows": {
        3: "..f......................f", 5: "......................g", 6: "....................==========",
        9: "..............g", 10: "............=========", 13: "....g", 14: "..=========",
        17: "=====.........................=====", 20: "..........P"}},
    {"name": "FOAMY HEART", "rows": {
        4: "..........g........g", 5: "........======....======", 7: "......f...............f",
        8: "......======..........======", 10: "..........g", 11: "........======......======",
        13: "...............g", 14: "...........=====..=====", 17: ".............==========", 20: ".................P"}},
    {"name": "PILLAR PARK", "gap": (15, 20), "rows": {
        4: "....g.............g...........g", 5: "..========....==========....======",
        8: "........##................##", 9: "........##.......f........##", 10: "........##....========....##",
        11: "........##................##", 12: "........##................##", 13: "...g....##................##...g",
        14: "========##................##======", 15: "........##........g.......##",
        16: "........##...==========...##", 17: "........##................##", 18: "........##................##",
        19: "........##................##", 20: "...P....##................##"}},
    {"name": "ZIGZAG ZOOM", "rows": {
        4: "..g.................f", 5: "========================", 8: "...........................g",
        9: "............========================", 12: "..g...........f", 13: "========================",
        16: "..........................g", 17: "............========================", 20: "..P"}},
    {"name": "POLKA PUFFS", "rows": {
        4: "....g.......f.......g.......f", 5: "...====....====....====....====",
        8: "........f.......g", 9: ".......====....====....====", 12: "....g..............f",
        13: "...====....====....====....====", 16: "........g.......g", 17: ".......====....====....====",
        20: ".................P"}},
    {"name": "BUBBLE BATH", "rows": {
        4: "...g.......................g", 5: "..=======..............=======", 8: "...........f.........f",
        9: "..........==============", 11: "......##................##", 12: "......##.......g........##",
        13: "......##................##", 14: "......####################", 17: "=====.....................=====",
        20: ".................P"}},
    {"name": "MOCHI SMILE", "rows": {
        2: "..........g............g", 3: "........=======.......=======", 6: "....f..........................f",
        7: "...=====...................=====", 9: "................g", 10: "..............========",
        12: "......g..................g", 13: ".....=====..............=====", 15: ".................f",
        16: ".........==================", 20: ".................P"}},
]

# Legacy themes of the original eight stages (block, block shadow, platform, platform shadow, sky top, sky bottom).
THEMES = [("pink", "hotpink", "cream", "peach", "deep", "night"), ("mint", "teal", "cream", "lime", "deep", "night"),
          ("hotpink", "purple", "pink", "hotpink", "ink", "night"), ("sky", "blue", "white", "sky", "deep", "night"),
          ("yellow", "orange", "cream", "yellow", "ink", "night"), ("lavender", "purple", "white", "lavender", "deep", "night"),
          ("teal", "blue", "mint", "teal", "ink", "night"), ("peach", "orange", "yellow", "orange", "deep", "night")]


def build(level):
    """Original-format level -> 23 rows of 40 characters (with g/f/P markers)."""
    gap = level.get("gap")

    def edge():
        r = list("#" * COLS)
        if gap:
            for c in range(gap[0] + 2, gap[1] + 3):
                r[c] = "."
        return "".join(r)
    m = [edge()]
    for i in range(1, 21):
        inner = (level["rows"].get(i, "") + "." * 36)[:36]
        m.append("##" + inner + "##")
    m += [edge(), edge()]
    return m


# ----------------------------------------------------------------------------- tier themes (one per 10 stages)
# name, block, block shadow, platform, platform shadow, sky top, sky bottom, backdrop style, snack kind
TIER_THEMES = [
    ("BUBBLY BATHROOM", "pink", "hotpink", "cream", "peach", "deep", "night", "bubbles", 0),
    ("MINT SINK", "mint", "teal", "cream", "lime", "deep", "night", "tiles", 1),
    ("BERRY BATHTUB", "hotpink", "purple", "pink", "hotpink", "ink", "night", "dots", 2),
    ("SKY SHOWER", "sky", "blue", "white", "sky", "deep", "night", "rain", 3),
    ("LEMON LAUNDRY", "yellow", "orange", "cream", "yellow", "ink", "night", "stripes", 4),
    ("LAVENDER LOFT", "lavender", "purple", "white", "lavender", "deep", "night", "stars", 5),
    ("TEAL TILE HALL", "teal", "blue", "mint", "teal", "ink", "night", "tiles", 6),
    ("PEACH PANTRY", "peach", "orange", "yellow", "orange", "deep", "night", "dots", 7),
    ("COCOA CELLAR", "brown", "choco", "peach", "brown", "choco", "night", "bubbles", 4),
    ("GRIME GATE", "gray", "darkgray", "lavender", "gray", "darkgray", "night", "stars", 5),
    ("MIDNIGHT CLOSET", "blue", "purple", "sky", "blue", "night", "black", "stars", 3),
    ("CANDY CUPBOARD", "pink", "purple", "lime", "teal", "deep", "night", "stripes", 3),
    ("LIME LAGOON", "lime", "teal", "white", "lime", "ink", "night", "rain", 2),
    ("CREAM CLOUDS", "cream", "peach", "white", "cream", "deep", "night", "bubbles", 6),
    ("ORANGE ORCHARD", "orange", "brown", "yellow", "orange", "choco", "night", "dots", 0),
    ("STEAM SAUNA", "white", "gray", "peach", "orange", "deep", "night", "rain", 7),
    ("RAINBOW RINSE", "hotpink", "purple", "yellow", "orange", "ink", "night", "stripes", 1),
    ("SOOT CHIMNEY", "darkgray", "black", "gray", "darkgray", "night", "black", "stars", 5),
    ("GOLDEN GLEAM", "yellow", "brown", "white", "yellow", "deep", "night", "tiles", 4),
    ("THE GRAND DRAIN", "purple", "night", "pink", "hotpink", "ink", "black", "bubbles", 6),
]

# ----------------------------------------------------------------------------- curated symmetric templates
# Left 18 columns of the 36-wide interior, mirrored to the right. Row numbers 1..20 (floor is below row 20).
SYM_TEMPLATES = [
    ("TOWEL RACKS", {17: "...=======........", 13: "..........========", 9: "..=======.........",
                     5: ".........========="}),
    ("DRIP DROPS", {17: "..===.....===.....", 13: "......===.......==", 9: "..===.....===.....",
                    5: "......===.......=="}),
    ("SOAP DISH", {17: "=====.............", 13: "......#...........", 14: "......############",
                   9: "..=====...........", 5: ".........=========", 2: "...====..........."}),
    ("FAUCET FALLS", {2: "....==========....", 6: "..........=======#", 7: ".................#",
                      8: ".................#", 9: ".................#", 10: ".................#",
                      11: "..=======........#", 12: ".................#", 13: ".................#",
                      14: ".................#", 15: ".................#", 16: "..........=======#"}),
    ("TILE TOWER", {17: "......============", 13: "====......========", 9: "..............====",
                    5: "........=====.....", 10: "===..............."}),
    ("BATH MAT", {17: "..==============..", 13: "......======......", 9: ".........========.",
                  5: "..=====..........."}),
    ("BUBBLE WAND", {4: "..........========", 8: "......====........", 12: "....====..........",
                     16: "......====........", 13: ".............=====", 17: "==................"}),
    ("SHOWER CURTAIN", {16: "........==========", 12: "..=====...........", 8: "........#=========",
                        7: "........#.........", 6: "........#.........", 9: "........#.........",
                        4: "..=====...........", 3: "............======"}),
    ("LOOFAH LOOPS", {17: "...######.........", 13: ".........=====....", 9: "...######.........",
                      5: ".........=====....", 16: "...#.......=====.."}),
    ("DUCKY POND", {17: "=====........=====", 14: "........====......", 11: "..====............",
                    10: "...............===", 7: ".......=======....", 3: "..====............"}),
    ("TOOTHBRUSH TRACK", {16: "..================", 11: "================..", 6: "..================",
                          2: "......==.........."}),
    ("FOAM FORTRESS", {17: "...#=========.....", 16: "...#..............", 15: "...#..............",
                       13: "...#.....=========", 12: "...#..............", 11: "...#..............",
                       10: "...#..............", 9: "...=====..........", 5: "........======....",
                       14: "...#.............."}),
    ("SUDS STEPS", {17: "=====.............", 14: "....=====.........", 11: "........=====.....",
                    8: "............======", 4: "......======......"}),
    ("PLUNGER PEAKS", {17: "....====......====", 16: ".....##.......##..", 12: "========..........",
                       11: "..##..............", 8: ".........=========", 7: "..........##......",
                       4: "...=====.........."}),
    ("CLOUD NINE", {17: ".====.......====..", 14: "......=====.......", 11: "..====..........==",
                    8: ".......=====......", 5: "..====.......=====", 2: "........====......"}),
    ("MOCHI MAZE", {17: "..=====##=========", 13: "........##........", 12: "..========........",
                    14: "........##........", 15: "........##........", 16: "........##........",
                    9: "...........=======", 6: "..=======.........", 8: "...........#......",
                    7: "...........#......", 3: "........==========", 4: "...........#......"}),
    ("RINSE CYCLE", {16: "......======......", 12: "..====......====..", 8: "......======......",
                     4: "..====......====..", 18: "==................"}),
    ("HAPPY HOP", {17: "====..............", 14: "....====..........", 13: "..............====",
                   10: "........=====.....", 6: "...======.........", 3: ".............====="}),
    ("SPONGE STACK", {17: "....##############", 16: "....#.............", 12: "...........=======",
                      11: "..========........", 7: ".......=======....", 3: "..=====..........."}),
    ("DRAIN CLIMB", {17: "==========........", 13: "..............====", 12: "......#####.......",
                     9: "..====............", 6: "..........========", 2: "....======........"}),
    ("WASHBOARD", {17: "..===..===..===..=", 13: "....===..===..===.", 9: "..===..===..===..=",
                   5: "....===..===..===."}),
    ("BATH SALTS", {16: "...===.......===..", 12: "......=====.......", 13: "==................",
                    8: "..====........====", 4: ".......====.......", 9: ".............====="}),
]

# boss arenas (symmetric, open in the middle) and bonus fields
ARENAS = [
    ("DUST DEN", {16: "====..............", 11: "......============", 6: "======............"}),
    ("MOP DOJO", {15: "=====.............", 10: "..=====...........", 5: "=====............."}),
    ("CLOUD COURT", {16: "....========......", 11: "==................", 7: "......======......"}),
    ("SOCK DRAWER", {16: "======............", 12: ".........=========", 8: "======............",
                     4: "..........========"}),
    ("SOOT STOVE", {16: "...=======........", 11: "===...............", 7: "...=======........"}),
    ("GRAND DRAIN", {16: "=====.....=====...", 11: "........==========", 6: "=====.....====...."}),
]
BONUS_FIELDS = [
    ("BUBBLE PARTY", {17: "....======........", 12: "..........========", 7: "....======........"}),
    ("SNACK RAIN", {17: "...======.........", 13: "............======", 9: "...======.........",
                    5: "..........====...."}),
]

# ----------------------------------------------------------------------------- enemies, bosses, modifiers
# kind: (name, intro tier, flies, blurb for the NEW card)
ENEMIES = {
    "g": ("GRUMP", 0, False, "WALKS AND HOPS"),
    "f": ("FLUTTER", 0, True, "FLIES CORNER TO CORNER"),
    "b": ("BOING", 1, False, "BOUNCES HIGH"),
    "z": ("ZOOMY", 2, False, "DASHES AT YOU"),
    "s": ("LIDDY", 4, False, "LID SHIELD: 2 BUBBLES"),
    "p": ("SNEEZY", 6, False, "SNEEZES DUST"),
    "w": ("WISP", 9, True, "DRIFTS THROUGH WALLS"),
}
ORDER = "gfbzspw"
BOSSES = {
    # kind: (name, base hp, own patterns by appearance level)
    "king": ("KING FLUFF", 26, ["hop", "spit", "hop", "minions"]),
    "mop": ("MOP TITAN", 30, ["walk", "slam", "walk", "splash"]),
    "vac": ("WHIRL CLOUD", 28, ["drift", "inhale", "puff", "drift", "minions"]),
    "sock": ("SOCK SERPENT", 24, ["slither", "lunge", "slither", "spit"]),
    "soot": ("SOOT STORM", 30, ["drift", "rain", "bolt", "minions"]),
    "grime": ("THE BIG GRIME", 48, ["hop", "spit", "slam", "rain", "minions"]),
}
BOSS_CYCLE = ["king", "mop", "vac", "sock", "soot"]
GUEST = ["spit", "rain", "bolt", "minions"]
MODS = {   # name: (label on the stage card, first tier)
    "wrap": ("WRAP-AROUND FLOOR", 1),
    "wind": ("BREEZY BUBBLES", 3),
    "slick": ("SLIPPERY SOAP", 5),
    "floaty": ("FLOATY JUMPS", 7),
    "dark": ("LIGHTS OUT", 8),
}


def boss_kind(tier):
    if tier in (9, 19):
        return "grime"
    k = tier - (1 if tier > 9 else 0)
    return BOSS_CYCLE[k % len(BOSS_CYCLE)]


# ----------------------------------------------------------------------------- map helpers
def sym_rows(rows):
    """{row: left-half string} -> full 23x40 map (walls, ceiling, floor)."""
    m = ["#" * COLS]
    for r in range(1, 21):
        half = (rows.get(r, "") + "." * 18)[:18]
        m.append("##" + half + half[::-1] + "##")
    m += ["#" * COLS, "#" * COLS]
    return m


def strip_markers(m):
    """Original map with g/f/P -> (plain map, start, [(kind, col, row)])."""
    start, ens, out = None, [], []
    for r, row in enumerate(m):
        for c, ch in enumerate(row):
            if ch == "P":
                start = (c, r)
            elif ch in "gf":
                ens.append((ch, c, r))
        out.append(row.replace("P", ".").replace("g", ".").replace("f", "."))
    return out, start, ens


def solid(m, c, r):
    if r < 0 or r >= ROWS:
        return False
    if c < 0 or c >= COLS:
        return True
    return m[r][c] == "#"


def standable(m, c, r):
    """Momo (12x14) can stand with her feet on top of row r+1 in column c."""
    if r < 1 or r + 1 >= ROWS or c < 2 or c >= COLS - 2:
        return False
    return m[r][c] != "#" and m[r - 1][c] != "#" and m[r + 1][c] in "#="


def fall_from(m, c, r, wrapped=False):
    """Falling down column c from row r: the standable row it lands on (or None)."""
    rr = r
    for _ in range(ROWS * 2):
        if solid(m, c, rr):
            return None
        if standable(m, c, rr):
            return rr
        rr += 1
        if rr >= ROWS:          # fell through a floor gap: wrap to the top once
            if wrapped:
                return None
            wrapped = True
            rr = 1
    return None


def reachable(m, start, bounce=False):
    """Tile-level flood fill of every place Momo can stand, using a conservative jump arc:
    up to JUMP_UP rows up and 4 columns across (no solid block in the way), 6 across on the same level,
    walking and dropping off ledges. bounce=True also allows a bubble-bounce boost (4 more rows), which the
    hand-made original stages rely on; generated stages must work without it."""
    rise = JUMP_UP + (4 if bounce else 0)
    seen = {start}
    todo = [start]
    while todo:
        c, r = todo.pop()
        nxt = []
        for dc in (-1, 1):                       # walk / walk off a ledge
            if standable(m, c + dc, r):
                nxt.append((c + dc, r))
            elif not solid(m, c + dc, r) and not solid(m, c + dc, r - 1):
                land = fall_from(m, c + dc, r + 1)
                if land is not None:
                    nxt.append((c + dc, land))
        # jumps: rise in column c to the target height, then drift across
        for r2 in range(r - rise, r + 1):
            if r2 < 1:
                continue
            if any(solid(m, c, rr) for rr in range(r2 - 1, r)):
                continue
            span = 7 if r2 == r else 5 if r - r2 <= 4 else 4
            for dc in range(-span, span + 1):
                c2 = c + dc
                if not standable(m, c2, r2) or (c2, r2) in seen:
                    continue
                lo, hi = min(c, c2), max(c, c2)
                if any(solid(m, cc, r2) or solid(m, cc, r2 - 1) for cc in range(lo, hi + 1)):
                    continue
                nxt.append((c2, r2))
        # jump off to a lower level (falls further across)
        for dc in range(-6, 7):
            c2 = c + dc
            if dc == 0 or solid(m, c2, r) or solid(m, c2, r - 1):
                continue
            lo, hi = min(c, c2), max(c, c2)
            if any(solid(m, cc, r) or solid(m, cc, r - 1) or solid(m, cc, r - 2) for cc in range(lo, hi + 1)):
                continue
            land = fall_from(m, c2, r)
            if land is not None and land > r:
                nxt.append((c2, land))
        for q in nxt:
            if q not in seen:
                seen.add(q)
                todo.append(q)
    return seen


def segments(m):
    """Maximal horizontal runs of standable cells: [(row, c0, c1)]."""
    segs = []
    for r in range(1, ROWS - 2):
        c = 2
        while c < COLS - 2:
            if standable(m, c, r):
                c0 = c
                while c < COLS - 2 and standable(m, c, r):
                    c += 1
                segs.append((r, c0, c - 1))
            else:
                c += 1
    return segs


def open_air(m, c, r):
    return all(not solid(m, cc, rr) and m[rr][cc] != "=" for cc in (c, c + 1) for rr in (r - 1, r))


def validate(m, start, enemies, strict=True):
    """Checks a stage is winnable without bubble-bouncing tricks:
    - strict: every platform segment is reachable from Momo's start;
    - every walker either starts somewhere Momo can reach or can walk/hop its own way down to her;
    - flyers start in open air."""
    if len(m) != ROWS or any(len(row) != COLS for row in m):
        return "bad size"
    if not standable(m, *start):
        return "bad start"
    seen = reachable(m, start, bounce=not strict)
    if strict:
        for r, c0, c1 in segments(m):
            if c1 - c0 >= 1 and not any((c, r) in seen for c in range(c0, c1 + 1)):
                return f"unreachable platform row {r} cols {c0}-{c1}"
    for kind, c, r in enemies:
        if ENEMIES[kind][2]:
            if not open_air(m, c, r) and not standable(m, c, r):
                return f"flyer {kind} stuck at {c},{r}"
        else:
            land = fall_from(m, c, r)
            if land is None:
                return f"walker {kind} falls forever from {c},{r}"
            if (c, land) not in seen and not reachable(m, (c, land)) & seen:
                return f"walker {kind} cannot meet Momo from {c},{r}"
    return None


# ----------------------------------------------------------------------------- variation
def _runs(row, ch):
    out, c = [], 0
    while c < len(row):
        if row[c] == ch:
            c0 = c
            while c < len(row) and row[c] == ch:
                c += 1
            out.append((c0, c - 1))
        else:
            c += 1
    return out


def vary(m, rng, tier, sym):
    """Seeded remix of a template: mirror, platform stretch/shrink, some ledges turned into solid blocks."""
    g = [list(row) for row in m]
    if not sym and rng.random() < 0.5:
        g = [row[::-1] for row in g]
    for r in range(1, 21):
        for c0, c1 in _runs(g[r], "="):
            if c1 < COLS // 2 or not sym:        # left half (mirrored below) or free templates
                roll = rng.random()
                if roll < 0.22 and c1 + 1 < COLS - 2 and g[r][c1 + 1] == "." and (not sym or c1 + 1 < COLS // 2):
                    g[r][c1 + 1] = "="
                elif roll < 0.44 and c0 - 1 > 1 and g[r][c0 - 1] == ".":
                    g[r][c0 - 1] = "="
                elif roll < 0.56 and c1 - c0 >= 4:
                    g[r][c0] = "."
                if tier >= 3 and c1 - c0 <= 4 and rng.random() < 0.12 + 0.01 * tier and r >= 3:
                    for c in range(c0, c1 + 1):
                        if g[r][c] == "=":
                            g[r][c] = "#"
        if sym:
            for c in range(COLS // 2, COLS):
                g[r][c] = g[r][COLS - 1 - c]
    return ["".join(row) for row in g]


def open_gap(m):
    """WRAP: holes in the floor and ceiling (falling out of the bottom drops you in from the top)."""
    out = list(m)
    for r in (0, 21, 22):
        row = list(out[r])
        for c in range(17, 23):
            row[c] = "."
        out[r] = "".join(row)
    return out


def pick_start(m, prefer=19):
    for d in range(0, 18):
        for c in (prefer - d, prefer + d):
            if standable(m, c, 20) and m[21][c] == "#" and m[21][c - 1] == "#" and m[21][c + 1] == "#":
                return (c, 20)
    return (4, 20)


def place_enemies(m, start, kinds, rng, sym):
    """Spread walkers over different platforms (mirrored pairs on symmetric maps), flyers in open air."""
    seen = reachable(m, start)
    segs = [s for s in segments(m) if s[0] < 19 and any((c, s[0]) in seen for c in range(s[1], s[2] + 1))]
    rng.shuffle(segs)
    segs.sort(key=lambda s: s[0])                 # higher platforms first (stable after shuffle)
    spots, used = [], set()
    walkers = [k for k in kinds if not ENEMIES[k][2]]
    flyers = [k for k in kinds if ENEMIES[k][2]]

    def free(c, r):
        return all(abs(c - c2) > 2 or abs(r - r2) > 1 for c2, r2 in used)

    i = 0
    rounds = 0
    while walkers and rounds < 6:
        for r, c0, c1 in segs:
            if not walkers:
                break
            cands = [c for c in range(c0, c1 + 1) if (c, r) in seen and free(c, r)]
            if not cands:
                continue
            c = cands[len(cands) // 2] if rounds == 0 else rng.choice(cands)
            k = walkers.pop(0)
            spots.append((k, c, r))
            used.add((c, r))
            if sym and walkers and (COLS - 1 - c, r) in seen and free(COLS - 1 - c, r) and c != COLS - 1 - c:
                k2 = walkers.pop(0)
                spots.append((k2, COLS - 1 - c, r))
                used.add((COLS - 1 - c, r))
        rounds += 1
        i += 1
    air = [(c, r) for r in range(2, 15) for c in range(4, COLS - 5) if open_air(m, c, r)]
    for k in flyers:
        cands = [q for q in air if free(*q)] or air
        c, r = rng.choice(cands)
        spots.append((k, c, r))
        used.add((c, r))
    return spots


def roster(tier, n, rng, new=None):
    unlocked = [k for k in ORDER if ENEMIES[k][1] <= tier]
    weights = []
    for k in unlocked:
        w = {"g": 5, "f": 3}.get(k, 3)
        if ENEMIES[k][1] == tier:
            w += 3
        weights.append(w)
    cap = {"w": 2, "p": 3, "s": 3, "z": 3, "f": 3}
    out = []
    if new:
        out += [new, new]
    while len(out) < n:
        k = rng.choices(unlocked, weights)[0]
        if out.count(k) < cap.get(k, 99):
            out.append(k)
    return sorted(out, key=ORDER.index)


# ----------------------------------------------------------------------------- the campaign
def _normal(n, rng, tier, library, used_names):
    if n < 10:          # stages 1-9: the original hand-made eight, as designed
        idx = n - 1 if n < 5 else n - 2
        lv = LEVELS[idx]
        m, start, ens = strip_markers(build(lv))
        kinds = [k for k, _, _ in ens]
        return {"name": lv["name"], "map": m, "start": start, "enemies": ens, "mods": [], "sym": False,
                "kinds": kinds}
    # later stages: remix a curated template
    fresh = [t for t in library if t[0] not in used_names] or library
    name, rows, sym = fresh[rng.randrange(len(fresh))]
    used_names.add(name)
    if len(used_names) >= len(library):
        used_names.clear()
    base = sym_rows(rows) if sym else rows
    start0 = None
    if not sym:
        base, start0, _ = strip_markers(base)
    mods = []
    chance = 0.0 if tier == 0 else 0.35 if tier < 5 else 0.5 if tier < 10 else 0.65
    avail = [k for k, (_, t0) in MODS.items() if t0 <= tier]
    if avail and rng.random() < chance:
        mods.append(rng.choice(avail))
        if tier >= 5 and rng.random() < (0.15 if tier < 10 else 0.3):
            other = [k for k in avail if k not in mods]
            if other:
                mods.append(rng.choice(other))
    count = min(10, 5 + tier // 3 + rng.randint(0, 1))
    new = next((k for k in ORDER if ENEMIES[k][1] == tier and tier > 0), None) if n % 10 == 1 else None
    kinds = roster(tier, count, rng, new)
    for attempt in range(12):
        m = vary(base, rng, tier, sym) if attempt < 10 else list(base)
        if "wrap" in mods:
            m = open_gap(m)
        start = pick_start(m, start0[0] if start0 and attempt < 10 else 19)
        ens = place_enemies(m, start, list(kinds), rng, sym)
        if len(ens) == len(kinds) and validate(m, start, ens, strict=sym) is None:
            return {"name": name, "map": m, "start": start, "enemies": ens, "mods": mods, "sym": sym,
                    "kinds": kinds, "new": new}
        if attempt == 10 and "wrap" in mods:
            mods.remove("wrap")
    raise ValueError(f"stage {n}: template {name} cannot be validated")


def _arena(rows, start_col=19):
    m = sym_rows(rows)
    return m, pick_start(m, start_col)


ROMAN = ["", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X"]


def generate():
    """The 200-stage campaign as a list of dicts (index 0 = stage 1). 'tpl' = template name (not exported)."""
    library = [(name, rows, True) for name, rows in SYM_TEMPLATES]
    library += [(lv["name"], build(lv), False) for lv in LEVELS]
    used = set()
    uses = {}
    stages = []
    for n in range(1, STAGES + 1):
        tier = (n - 1) // 10
        rng = random.Random(9173 * n + 17)
        if n % 10 == 0:
            kind = boss_kind(tier)
            name, base_hp, pats = BOSSES[kind]
            level = sum(1 for t in range(tier) if boss_kind(t) == kind)
            own = pats[:2 + min(level, len(pats) - 2)]
            guests = []
            if tier >= 10:
                pool = [g for g in GUEST if g not in own]
                rng.shuffle(pool)
                guests = pool[:1 + (tier >= 15)]
            hp = int(base_hp * (1 + 0.12 * tier))
            arena_i = {"king": 0, "mop": 1, "vac": 2, "sock": 3, "soot": 4, "grime": 5}[kind]
            aname, arows = ARENAS[arena_i]
            m, start = _arena(arows, 6)            # Momo starts on the left, the boss lands on the right
            stages.append({"k": "boss", "nm": name + ROMAN[min(level, 9)], "tpl": kind, "th": tier, "map": m, "p": list(start), "en": [], "mods": [],
                           "boss": kind, "lv": level, "hp": hp, "pat": own + guests, "spd": round(1 + 0.04 * tier, 3),
                           "par": 90, "new": ""})
        elif n % 10 == 5:
            bt = "party" if (n // 10) % 2 == 0 else "rain"
            fname, frows = BONUS_FIELDS[0 if bt == "party" else 1]
            m, start = _arena(frows)
            stages.append({"k": "bonus", "nm": fname, "tpl": fname, "th": tier, "map": m, "p": list(start), "en": [], "mods": [],
                           "bt": bt, "time": 20, "par": 20, "new": ""})
        else:
            st = _normal(n, rng, tier, library, used)
            wind = 0
            if "wind" in st["mods"]:
                wind = rng.choice((-1, 1))
            angry = 0.0 if tier < 12 else min(0.5, 0.08 * (tier - 11))   # late tiers: some start already angry
            ens = [[k, c, r, 1 if rng.random() < angry else 0] for k, c, r in st["enemies"]]
            k = uses.get(st["name"], 0)
            uses[st["name"]] = k + 1
            stages.append({"k": "normal", "nm": st["name"] + ROMAN[min(k, 9)], "tpl": st["name"], "th": tier, "map": st["map"], "p": list(st["start"]),
                           "en": ens, "mods": st["mods"], "wind": wind,
                           "par": 25 + 5 * len(st["enemies"]), "new": st.get("new") or ""})
    return stages


def rle(row):
    """'####....==' -> '4#4.2=' (map rows are exported run-length encoded to keep the iOS data small)."""
    out, c = [], 0
    while c < len(row):
        n = 1
        while c + n < len(row) and row[c + n] == row[c]:
            n += 1
        out.append(f"{n}{row[c]}")
        c += n
    return "".join(out)


def unrle(s):
    out, n = [], 0
    for ch in s:
        if ch.isdigit():
            n = n * 10 + int(ch)
        else:
            out.append(ch * n)
            n = 0
    return "".join(out)


def export():
    stages = generate()
    for st in stages:
        st["map"] = [rle(row) for row in st["map"]]
        del st["tpl"]
    return {
        "stages": stages,
        "themes": [list(t) for t in TIER_THEMES],
        "enemies": {k: [v[0], v[1], v[2], v[3]] for k, v in ENEMIES.items()},
        "bosses": {k: [v[0], v[1]] for k, v in BOSSES.items()},
        "mods": {k: v[0] for k, v in MODS.items()},
    }


def ascii(m, start=None, enemies=()):
    g = [list(r) for r in m]
    if start:
        g[start[1]][start[0]] = "P"
    for e in enemies:
        g[e[2]][e[1]] = e[0]
    return "\n".join("".join(r) for r in g)


if __name__ == "__main__":
    import sys
    sts = generate()
    want = [int(a) for a in sys.argv[1:]] or [11, 12]
    for n in want:
        s = sts[n - 1]
        print(n, s["k"], s["nm"], s["mods"], s.get("new"))
        print(ascii(s["map"], s["p"], s["en"]))
