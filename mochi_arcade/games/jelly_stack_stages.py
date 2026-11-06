"""JELLY STACK campaign: 200 stages built from curated templates plus seeded variation.

Plain data (no pygame). jelly_stack.EXPORT ships these tables to the iOS port, so both platforms play exactly
the same stages; tests/test_jelly_stack.py builds all 200 and checks every one with validate().

Stage dict keys:
  n      stage number 1..200          k     kind (see KINDS)
  goal   rows / points / stars / garbage rows / seconds, depending on the kind
  lim    time limit (speed), piece budget (puzzle), length in seconds (survive, bonus); 0 = none
  g      speed level (gravity, see jelly_stack_core.gravity_interval)
  rise   seconds between rising garbage rows (0 = none)
  rows   pre-filled jelly, top-down, bottom-aligned: . empty  g dusty  * star  i ice  b pop-bomb  c candy
  seq    puzzle: the exact pieces you get        mods  stage modifiers (see MODS)
  boss   boss index, hp, atk (attack names), every (seconds between attacks), pow (attack strength)
  par    seconds for the full time bonus        new   "NEW!" hint shown on the intro card (or "")
"""
import random

from mochi_arcade.games.jelly_stack_core import BH, BW, ROT, clear_full, drop_place

STAGES = 200
SEED = 0x7E11


def tier(n):
    return (n - 1) // 10


def is_boss(n):
    return n % 10 == 0


def is_bonus(n):
    return n % 10 == 5


# ------------------------------------------------------------------ 20 tiers: name, hue, accent, background style
THEMES = [
    ("STRAWBERRY HILL", "pink", "yellow", 0),
    ("MINT LAGOON", "mint", "sky", 1),
    ("LEMON GROVE", "yellow", "lime", 2),
    ("BLUEBERRY BAY", "blue", "sky", 3),
    ("CARAMEL CAVE", "orange", "peach", 4),
    ("GRAPE GARDEN", "purple", "lavender", 0),
    ("PEACH PARK", "peach", "pink", 1),
    ("MATCHA MEADOW", "lime", "mint", 2),
    ("COCOA CANYON", "brown", "cream", 3),
    ("SODA SKY", "sky", "white", 4),
    ("MARSHMALLOW MOON", "lavender", "white", 2),
    ("TAFFY TOWN", "hotpink", "cream", 0),
    ("SORBET SEA", "teal", "peach", 1),
    ("LICORICE LAB", "gray", "red", 3),
    ("HONEY HIVE", "orange", "yellow", 4),
    ("PUDDING PEAKS", "cream", "orange", 0),
    ("CANDY COMET", "red", "yellow", 2),
    ("SUGAR STORM", "white", "sky", 1),
    ("STARFRUIT STATION", "lime", "yellow", 3),
    ("JELLY CASTLE", "hotpink", "lavender", 4),
]

# ------------------------------------------------------------------ bosses: name, signature attack, body, trim
BOSSES = [
    ("GUMMY KING", "garbage", "lime", "yellow"),
    ("FROSTY FLAN", "freeze", "cream", "sky"),
    ("INKY PUDDING", "ink", "purple", "lavender"),
    ("TOFU TITAN", "heavy", "white", "gray"),
    ("TRICKY TART", "flip", "peach", "hotpink"),
    ("FIZZY FLOAT", "rush", "sky", "mint"),
    ("JELLY EMPEROR", "garbage", "hotpink", "yellow"),
]
ATTACKS = ["garbage", "freeze", "ink", "heavy", "flip", "rush"]
ATTACK_NAMES = {"garbage": "JELLY WAVE", "freeze": "DEEP FREEZE", "ink": "INK SPLAT", "heavy": "TOFU DROP",
                "flip": "SHUFFLE", "rush": "SUGAR RUSH"}

# ------------------------------------------------------------------ upgrades: id, name, desc (2 lines), color, max
UPGRADES = [
    ("peek", "PEEK", "SEE ONE MORE|NEXT JELLY", "mint", 2),
    ("slow", "SLOW-MO", "JELLIES FALL|15% SLOWER", "sky", 3),
    ("sticky", "STICKY", "MORE TIME|BEFORE LOCKING", "lime", 3),
    ("bomb", "BOMB JELLY", "BOMB JELLIES|BLAST 3X3", "orange", 3),
    ("zap", "ZAPPER", "ROW POPS|CHARGE A ZAP", "yellow", 3),
    ("shield", "SHIELD", "BLOCKS 2|GARBAGE ROWS", "lavender", 3),
    ("party", "PARTY+", "+25% FOR|MULTI-ROW POPS", "pink", 4),
    ("pocket", "POCKET", "A SECOND|HOLD SLOT", "peach", 1),
    ("lucky", "LUCKY", "MORE GOLDEN|JELLIES", "orange", 3),
    ("heart", "1UP", "+1 LIFE|RIGHT NOW", "hotpink", 5),
]

KINDS = ["rows", "score", "dig", "stars", "survive", "puzzle", "speed", "mix", "rain", "well", "boss"]
MODS = {"nohold": "NO HOLD", "fog": "FOG", "noghost": "NO GHOST", "drizzle": "DRIZZLE", "vanish": "VANISH"}
MOD_TIER = {"nohold": 4, "fog": 6, "noghost": 7, "drizzle": 8, "vanish": 9}
NEW_TEXT = {
    "rows": "FILL A ROW TO POP IT!", "score": "SCORE GOAL: BIG POPS PAY MORE",
    "dig": "DUSTY JELLY: DIG IT ALL OUT!", "stars": "STAR JELLY: POP EVERY STAR!",
    "puzzle": "PUZZLE: ONLY THESE PIECES!", "survive": "RISING JELLY: HANG ON!",
    "speed": "SPEED: BEAT THE CLOCK!", "mix": "RISING ROWS WHILE YOU POP!",
    "rain": "BONUS: CANDY RAIN!", "well": "BONUS: JACKPOT WELL!", "boss": "BOSS: POP ROWS TO HIT IT!",
    "ice": "ICE JELLY NEEDS TWO POPS", "bombs": "POP-BOMBS BLAST 3X3",
    "nohold": "NO HOLD THIS STAGE", "fog": "FOG HIDES THE BOTTOM", "noghost": "NO GHOST PIECE",
    "drizzle": "DRIZZLE: SLOW RISING ROWS", "vanish": "VANISH: JELLIES GO INVISIBLE",
}
# stage plan inside a tier (the 8 regular slots; slot 4 is the bonus stage, slot 9 the boss)
PLAN_T0 = ["rows", "rows", "dig", "stars", "score", "puzzle", "dig", "stars"]
PLAN_T1 = ["survive", "rows", "dig", "stars", "puzzle", "score", "mix", "dig"]
PLAN = ["rows", "dig", "stars", "puzzle", "survive", "speed", "mix", "score"]
INTRO = {2: "speed", 3: "dig", 5: "dig"}          # first stage of a tier shows off what is new


# ------------------------------------------------------------------ pre-filled jelly
def garbage_rows(rnd, n, t, ice=0.0, bombs=0, pattern=None):
    """n dusty rows (top-down), every row with at least one hole, holes laid out by a template."""
    if pattern is None:
        pats = ["well", "steps", "zigzag", "random"] + (["double", "pairs"] if t >= 2 else []) + \
               (["random", "double"] if t >= 8 else [])
        pattern = rnd.choice(pats)
    rows = []
    c0 = rnd.randrange(BW)
    d = rnd.choice((-1, 1))
    for i in range(n):
        if pattern == "well":
            holes = {c0}
        elif pattern == "steps":
            holes = {(c0 + i * d) % BW}
        elif pattern == "zigzag":
            holes = {c0 if i % 2 == 0 else (c0 + 3) % BW}
        elif pattern == "double":
            holes = set(rnd.sample(range(BW), 2))
        elif pattern == "pairs":
            c = rnd.randrange(BW - 1)
            holes = {c, c + 1}
        else:
            holes = {rnd.randrange(BW)}
        rows.append(["." if x in holes else "g" for x in range(BW)])
    for y, row in enumerate(rows):
        for x in range(BW):
            if row[x] == "g" and rnd.random() < ice:
                row[x] = "i"
    spots = [(x, y) for y in range(1, n) for x in range(BW) if rows[y][x] == "g"]
    rnd.shuffle(spots)
    for x, y in spots[:bombs]:
        rows[y][x] = "b"
    return rows


def add_stars(rnd, rows, count, deep):
    """Hide star jellies in dusty cells; deep=True prefers the lower half."""
    spots = [(x, y) for y in range(len(rows)) for x in range(BW) if rows[y][x] == "g"]
    if deep:
        spots.sort(key=lambda p: -p[1])
        spots = spots[:max(count, len(spots) // 2)]
    rnd.shuffle(spots)
    for x, y in spots[:count]:
        rows[y][x] = "*"


def make_puzzle(rnd, k, m):
    """A band of k rows at the bottom with holes that m pieces can exactly fill.

    Built backwards: start from a full band and lift out m pieces from the top, each one resting on what is
    left (so dropping them back in reverse order lands every piece exactly). Then the whole solution is
    replayed with the real spawn / rotate / slide / hard-drop rules (drop_place) to make sure it works."""
    for _ in range(400):
        band = [[1] * BW for _ in range(k)]
        removed = []
        for _ in range(m):
            cands = []
            for kind in "IOTSZJL":
                for rot in range(1 if kind == "O" else 4):
                    shape = ROT[kind][rot]
                    xs = [c[0] for c in shape]
                    ys = [c[1] for c in shape]
                    for ox in range(-min(xs), BW - max(xs)):
                        for oy in range(-min(ys), k - max(ys)):
                            pc = [(ox + cx, oy + cy) for cx, cy in shape]
                            if not all(band[y][x] for x, y in pc):
                                continue
                            own = set(pc)
                            if any(band[yy][x] for x, y in pc for yy in range(y) if (x, yy) not in own):
                                continue      # something still sits above: can't lift it out
                            if not any(y == k - 1 or ((x, y + 1) not in own and band[y + 1][x]) for x, y in pc):
                                continue      # would not rest here when dropped back in
                            cands.append((kind, rot, ox, oy, pc))
            if not cands:
                break
            kind, rot, ox, oy, pc = rnd.choice(cands)
            for x, y in pc:
                band[y][x] = 0
            removed.append((kind, rot, ox))
        if len(removed) < m:
            continue
        if any(all(r) for r in band) or any(sum(r) < 2 for r in band):
            continue
        rows = ["".join("g" if v else "." for v in r) for r in band]
        sol = list(reversed(removed))
        if solve_check(rows, sol):
            return rows, sol
    raise RuntimeError("no puzzle found")


def grid_from_rows(rows):
    grid = [[None] * BW for _ in range(BH)]
    for i, r in enumerate(rows):
        y = BH - len(rows) + i
        for x, ch in enumerate(r):
            if ch != ".":
                grid[y][x] = ch
    return grid


def solve_check(rows, sol):
    """Replay a puzzle solution with the real movement rules: every dusty jelly must be gone at the end."""
    grid = grid_from_rows(rows)
    for kind, rot, x in sol:
        cells = drop_place(grid, kind, rot, x)
        if cells is None or any(y < 0 for _, y in cells):
            return False
        for cx, cy in cells:
            grid[cy][cx] = kind
        clear_full(grid)
    return not any(c == "g" for row in grid for c in row)


# ------------------------------------------------------------------ the 200 stages
def build_all():
    stages = []
    seen = set()
    for t in range(STAGES // 10):
        rnd = random.Random(SEED + t * 101)
        if t == 0:
            plan = list(PLAN_T0)
        elif t == 1:
            plan = [PLAN_T1[0]] + rnd.sample(PLAN_T1[1:], 7)
        else:
            first = INTRO.get(t, "rows")
            rest = list(PLAN)
            rest.remove(first)
            plan = [first] + rnd.sample(rest, 7)
        slots = plan[:4] + ["bonus"] + plan[4:] + ["boss"]
        for i, kind in enumerate(slots):
            n = t * 10 + i + 1
            st = build_stage(n, kind, random.Random(SEED * 7 + n * 7919))
            notes = [st["k"]] + st["mods"] + (["ice"] if "i" in "".join(st["rows"]) else []) + \
                (["bombs"] if "b" in "".join(st["rows"]) else [])
            fresh = [x for x in notes if x not in seen]
            st["new"] = NEW_TEXT.get(fresh[-1], "") if fresh else ""
            seen.update(notes)
            stages.append(st)
    return stages


def build_stage(n, kind, rnd):
    t = tier(n)
    i = (n - 1) % 10
    lv = t + 1
    g = round(min(11.0, 1 + t * 0.45 + i * 0.04), 2)
    st = {"n": n, "k": kind, "goal": 0, "lim": 0, "g": g, "rise": 0, "rows": [], "seq": "", "mods": [],
          "par": 0, "boss": None}
    ice = 0.0 if t < 3 else min(0.28, 0.08 + (t - 3) * 0.015)
    bombs = 0 if t < 5 else min(3, 1 + (t - 5) // 5)
    if kind == "bonus":
        if t % 2 == 0:
            st["k"] = "rain"
            rows = garbage_rows(rnd, 4, t, pattern="double")
            for r in rows:
                for x in rnd.sample(range(BW), 3):
                    if r[x] == "g":
                        r[x] = "c"
        else:
            st["k"] = "well"
            rows = well_blocks(rnd, 3)
        st.update(goal=0, lim=30, g=round(1 + t * 0.15, 2), rows=["".join(r) for r in rows], par=0)
        return st
    if kind == "boss":
        k = n // 10
        b = 6 if n == STAGES else (k - 1) % 6
        prim = BOSSES[b][1]
        others = [a for a in ATTACKS if a != prim]
        rnd.shuffle(others)
        extra = 5 if b == 6 else (0 if k < 7 else 1 if k < 13 else 2)
        atk = [prim] + others[:extra]
        hp = 800 if b == 6 else 120 + 30 * (k - 1)
        rows = garbage_rows(rnd, min(6, k // 3), t) if k >= 3 else []
        st.update(goal=hp, rows=["".join(r) for r in rows], par=int(hp / 3.5),
                  boss={"id": b, "hp": hp, "atk": atk, "every": round(max(6.0, 13 - 0.35 * k), 1),
                        "pow": 1 + k // 5})
        return st
    if kind == "rows":
        st["goal"] = 6 if n == 1 else int(8 + t * 0.8 + i * 0.3)
        rows = garbage_rows(rnd, min(4, t // 3), t, ice) if t >= 2 else []
        st["par"] = st["goal"] * 6
    elif kind == "score":
        st["goal"] = int(lv * (1500 + 50 * t) // 100 * 100)
        rows = garbage_rows(rnd, min(3, t // 4), t, ice) if t >= 4 else []
        st["par"] = 70
    elif kind == "dig":
        nr = min(10, 3 + int(t * 0.4) + (1 if i > 5 else 0))
        rows = garbage_rows(rnd, nr, t, ice, bombs, pattern="well" if t == 0 else None)
        st["goal"] = nr
        st["par"] = nr * 9
    elif kind == "stars":
        nr = min(10, 3 + int(t * 0.35))
        rows = garbage_rows(rnd, nr, t, ice * 0.6, bombs)
        st["goal"] = min(nr, 2 + t // 3)
        add_stars(rnd, rows, st["goal"], deep=t >= 4)
        st["par"] = nr * 9
    elif kind == "survive":
        st["goal"] = int(40 + t * 2.5)
        st["rise"] = round(max(3.5, 9 - t * 0.28), 1)
        rows = garbage_rows(rnd, 2 + t // 6, t, ice * 0.5)
        st["lim"] = st["goal"]
    elif kind == "puzzle":
        kk = 2 if t < 3 else 3 if t < 9 else 4
        m = (2 + t // 2) if kk == 2 else (3 + (t - 3) // 2) if kk == 3 else min(7, 4 + (t - 9) // 3)
        m = min(m, {2: 3, 3: 5, 4: 7}[kk])
        prow, sol = make_puzzle(rnd, kk, m)
        slack = 2 if t < 3 else 1 if t < 8 else 0
        seq = "".join(s[0] for s in sol) + "".join(rnd.choice("IOTSZJL") for _ in range(slack))
        rows = [list(r) for r in prow]
        st.update(goal=kk, lim=len(seq), seq=seq, g=1.0, par=len(seq) * 7, sol=[list(s) for s in sol])
    elif kind == "speed":
        st["goal"] = int(6 + t * 0.5)
        st["lim"] = int(st["goal"] * max(4.0, 6.5 - t * 0.12))
        st["g"] = round(min(11.0, g + 2.0), 2)
        rows = []
    else:  # mix: pop rows while dusty rows creep up from below
        st["goal"] = int(8 + t * 0.6)
        st["rise"] = round(max(5.0, 12 - t * 0.35), 1)
        rows = garbage_rows(rnd, min(8, 3 + t // 4), t, ice, bombs)
        st["par"] = st["goal"] * 7
    st["rows"] = ["".join(r) for r in rows]
    st["mods"] = pick_mods(rnd, n, kind)
    if "drizzle" in st["mods"] and not st["rise"]:
        st["rise"] = round(max(7.0, 16 - t * 0.4), 1)
    return st


def well_blocks(rnd, blocks):
    """Jackpot well: blocks of 4 dusty rows, each block with a one-wide shaft (a long jelly pops 4 rows)."""
    rows = []
    last = -1
    for _ in range(blocks):
        c = rnd.choice([x for x in range(BW) if x != last])
        last = c
        rows += [["." if x == c else "g" for x in range(BW)] for _ in range(4)]
    return rows


def pick_mods(rnd, n, kind):
    t = tier(n)
    if kind == "puzzle":
        return []
    have = [m for m, mt in MOD_TIER.items() if t >= mt]
    if kind in ("dig", "stars", "survive", "mix"):
        have = [m for m in have if m not in ("drizzle", "vanish")]
    if kind == "speed":
        have = [m for m in have if m != "vanish"]
    mods = []
    fresh = [m for m, mt in MOD_TIER.items() if mt == t and m in have]
    if fresh and (n - 1) % 10 == 0:
        mods.append(fresh[0])                       # the first stage of a tier shows its new modifier
    elif have and rnd.random() < 0.2 + 0.025 * t:
        mods.append(rnd.choice(have))
        if t >= 12 and rnd.random() < 0.3:
            other = [m for m in have if m not in mods]
            if other:
                mods.append(rnd.choice(other))
    return mods


STAGE_LIST = build_all()


# ------------------------------------------------------------------ checks (used by the tests)
def validate(st):
    """Return a list of problems with one stage (empty when it is fine and winnable in principle)."""
    bad = []
    n, k, rows = st["n"], st["k"], st["rows"]
    if is_boss(n) != (k == "boss") or is_bonus(n) != (k in ("rain", "well")):
        bad.append("boss/bonus slot mismatch")
    if len(rows) > 12:
        bad.append("pre-fill too tall")
    for r in rows:
        if len(r) != BW or any(c not in ".g*ibc" for c in r):
            bad.append(f"bad row {r!r}")
        elif "." not in r:
            bad.append("full row in the pre-fill")
    if not 1.0 <= st["g"] <= 11.0:
        bad.append("speed level out of range")
    junk = sum(1 for r in rows if any(c in "gib*" for c in r))
    if k in ("rows", "mix", "speed") and st["goal"] < 1:
        bad.append("no row goal")
    if k == "dig" and (st["goal"] != junk or junk < 1):
        bad.append("dig goal does not match the dusty rows")
    if k == "stars":
        stars = sum(r.count("*") for r in rows)
        if stars != st["goal"] or stars < 1:
            bad.append("star count does not match the goal")
    if k == "speed" and st["lim"] < st["goal"] * 3.5:
        bad.append("speed stage too tight")
    if k == "survive" and (st["rise"] < 2.5 or st["goal"] / st["rise"] > 30):
        bad.append("survive stage too harsh")
    if k == "puzzle":
        if len(st["seq"]) != st["lim"] or st["goal"] != len(rows):
            bad.append("puzzle budget mismatch")
        sol = [tuple(s) for s in st.get("sol", [])]
        if not sol or "".join(s[0] for s in sol) != st["seq"][:len(sol)] or not solve_check(rows, sol):
            bad.append("puzzle has no working solution")
    if k in ("rain", "well") and not 20 <= st["lim"] <= 45:
        bad.append("bonus length")
    if k == "boss":
        b = st["boss"]
        if not b or b["hp"] < 50 or b["hp"] > 900 or not b["atk"] or any(a not in ATTACKS for a in b["atk"]):
            bad.append("boss table")
    if k in ("rows", "score", "speed") and junk > 6:
        bad.append("too much pre-fill for a plain stage")
    return bad
