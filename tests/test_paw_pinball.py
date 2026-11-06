"""PAW PINBALL checks: all 200 missions generate and validate, every table's geometry is sane, balls never escape
the table, both ramps can be made from the paws on every table that has them, then headless bot runs of a normal
stage, both bonus kinds and every boss design.
usage: python tests/test_paw_pinball.py [shot_dir]"""
import json
import math
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-pp-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A  # noqa: E402
from mochi_arcade.arcade import STAGES, is_boss, is_bonus  # noqa: E402
from mochi_arcade.games import GAMES, paw_pinball as PP  # noqa: E402
from mochi_arcade.games import paw_pinball_phys as P  # noqa: E402
from mochi_arcade.games import paw_pinball_tables as T  # noqa: E402

# ---------------------------------------------------------------- campaign data
camp = T.build_campaign()
assert len(camp) == STAGES == 200
assert camp == T.CAMPAIGN, "generation must be deterministic"
exp = json.loads(json.dumps(PP.EXPORT))
assert exp["stages"] == camp and exp["tables"] == T.TABLES and exp["arena"] == T.ARENA, "EXPORT must be plain JSON"
kinds = {"normal": 0, "boss": 0, "bonus": 0}
boss_kinds, names, goal_types = set(), set(), set()
for st in camp:
    n = st["n"]
    errs = T.validate(st)
    assert not errs, (n, st["name"], errs)
    kinds[st["kind"]] += 1
    assert st["tier"] == (n - 1) // 10
    assert (st["kind"] == "boss") == is_boss(n) and (st["kind"] == "bonus") == is_bonus(n), n
    if st["kind"] == "boss":
        boss_kinds.add(st["boss"]["kind"])
    for g, c in st["goals"]:
        goal_types.add(g)
    names.add(st["name"])
assert kinds == {"normal": 160, "boss": 20, "bonus": 20}, kinds
assert len(boss_kinds) >= 5, boss_kinds
assert goal_types == set(T.GOALS), goal_types ^ set(T.GOALS)
assert len(names) >= 40, len(names)
assert {st["bonus"] for st in camp if st["kind"] == "bonus"} == set(T.BONUS_KINDS)
# difficulty goes up: tougher bosses, more goals, steeper tables, shorter ball saves
assert camp[199]["boss"]["hp"] > camp[9]["boss"]["hp"] and camp[199]["grav"] > camp[0]["grav"]
assert camp[190]["save"] < camp[0]["save"]
assert max(len(s["goals"]) for s in camp[:50]) == 1 and max(len(s["goals"]) for s in camp[150:]) == 3
assert len({t["name"] for t in T.TABLES}) == 20
print(f"campaign OK: {kinds}, {len(names)} stage names, bosses {sorted(boss_kinds)}, goals {sorted(goal_types)}")

# ---------------------------------------------------------------- geometry + physics


class Bench:
    """Just enough of a scene for the physics."""

    def __init__(self, tb):
        self.fish = [list(f[:6]) + [0.0] for f in tb["fish"]]
        self.dyn = []
        self.tail_on = False
        self.ramp_ease = 1.0
        self.flippers = [P.Flipper(T.FLIP_X[0], T.FLIP_Y, 1, 23), P.Flipper(T.FLIP_X[1], T.FLIP_Y, -1, 23)]
        self.balls = []


def ramp_reachable(tb, kind):
    """Feed a ball down the inlane of the paw that shoots this ramp and try every flip timing."""
    side = 1 if kind == "tower" else 0
    for flip_at in range(34, 56):
        sc = Bench(tb)
        ph = P.Physics(sc, tb)
        gx = 92 if side == 0 else T.MIRROR - 92
        b = P.Ball(gx, 136, 0.0, 60.0)
        b.launched = True
        sc.balls = [b]
        for fr in range(flip_at + 90):
            sc.flippers[side].pressed = fr >= flip_at
            ph.events = []
            ph.step(1 / 60)
            if any(e[0] == "ramp_in" and tb["ramps"][e[1]]["kind"] == kind for e in ph.events):
                return flip_at
            if b.state != "play":
                break
    return None


rnd = random.Random(7)
tables = T.TABLES + [T.ARENA]
for tb in tables:
    errs = T.validate_table(tb)
    assert not errs, (tb["name"], errs)
    for r in tb["ramps"]:
        assert ramp_reachable(tb, r["kind"]) is not None, (tb["name"], r["kind"], "ramp can't be made")
    # random balls with random flipping: nobody escapes the table or goes NaN
    sc = Bench(tb)
    ph = P.Physics(sc, tb)
    for k in range(12):
        b = P.Ball(rnd.uniform(110, 210), rnd.uniform(40, 120), rnd.uniform(-300, 300), rnd.uniform(-300, 200))
        b.launched = True
        sc.balls = [b]
        for fr in range(600):
            for f in sc.flippers:
                f.pressed = rnd.random() < 0.3 if fr % 8 == 0 else f.pressed
            ph.step(1 / 60)
            assert not (math.isnan(b.x) or math.isnan(b.y)), tb["name"]
            if b.state == "ramp":
                break
            if b.state == "play":
                assert T.LW - 1 <= b.x <= T.LANE_OUT + 1 and b.y > -1, (tb["name"], b.x, b.y)
                if b.x > T.RW + 1:          # the one-way gate keeps playfield balls out of the plunger lane
                    gate_y = T.GATE_Y - 9 + (T.LANE_OUT - b.x) * 0.9
                    assert b.y < gate_y + 4, (tb["name"], "fell into the plunger lane", b.x, b.y)
            if b.state != "play":
                break
print(f"geometry OK: {len(tables)} tables, every ramp reachable, no escapes")

# plunger: a weak pull falls back, a full pull makes it round the arch into the playfield
for power, ok in ((0.0, False), (1.0, True)):
    tb = T.TABLES[0]
    sc = Bench(tb)
    ph = P.Physics(sc, tb)
    b = P.Ball(*P.LANE_START)
    sc.balls = [b]
    b.vy = -(240 + 380 * power)
    out = False
    for fr in range(240):
        ph.events = []
        ph.step(1 / 60)
        out = out or any(e[0] == "launched" for e in ph.events)
    assert out == ok, (power, out)

# ---------------------------------------------------------------- headless play
info = next(g for g in GAMES if g.id == "paw_pinball")


def play(stage, frames, levels=None, name=None):
    ref = [None]
    stats = {"boss_hp": None, "stages": set(), "events": {}, "max_balls": 0}
    app = A.App(windowed=True, mute=True, test_frames=frames, script=lambda f: PP.autopilot(ref[0], f))
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    sc = info.load()(app, info, {"difficulty": "normal", "start": 1})
    sc.levels.update(levels or {})
    if stage != 1:
        sc.start_stage(stage)
    ref[0] = sc
    orig = sc.on_event

    def spy(kind, a, x, y):
        stats["events"][kind] = stats["events"].get(kind, 0) + 1
        orig(kind, a, x, y)

    sc.on_event = spy
    app.apply_settings()
    app.scenes = [sc]
    sc.enter()
    for f in range(frames):
        app.input.begin()
        app.input.end(f)
        if app.scene is not sc:
            break
        sc.t += 1 / 60
        sc.update(1 / 60)
        if f % 3 == 0:
            sc.draw(app.canvas)
        stats["stages"].add(sc.n)
        stats["max_balls"] = max(stats["max_balls"], len(sc.balls))
        if sc.boss and sc.n == stage:
            stats["boss_hp"] = sc.boss.hp
    sc.draw(app.canvas)
    app.screenshot(os.path.join(SHOTS, (name or f"pp-stage{stage}") + ".png"))
    pygame.quit()
    return sc, stats


sc, stats = play(1, 5400)
assert sc.score > 0 and stats["events"].get("bumper", 0) > 0, "the bot should score on stage 1"
assert 2 in stats["stages"], "the bot should clear the first mission"
print(f"stage 1: reached stage {sc.n}, score {sc.score}, events {stats['events']}")
sc, stats = play(5, 2700, name="pp-bonus-party")
assert stats["max_balls"] >= 3 and 6 in stats["stages"], stats
print(f"bonus party: up to {stats['max_balls']} balls, then stage {sc.n}")
sc, stats = play(15, 2700, name="pp-bonus-fountain")
assert stats["events"].get("coin", 0) > 0 and 16 in stats["stages"], stats
print(f"bonus fountain: coins {sc.stats['coins']}, then stage {sc.n}")
for n in (10, 20, 30, 40, 50, 120, 200):
    sc, stats = play(n, 3600, {"power": 2, "paws": 2}, name=f"pp-boss{n}")
    hp = camp[n - 1]["boss"]["hp"]
    print(f"boss stage {n} ({camp[n - 1]['boss']['name']}): hp {stats['boss_hp']}/{hp} -> stage {sc.n} {sc.state}")
    assert stats["boss_hp"] is None or stats["boss_hp"] < hp, "the boss should take damage"
for n in (11, 21, 31, 51, 64, 97, 143, 188):
    sc, stats = play(n, 2400, {"paws": 1})
    print(f"stage {n} ({camp[n - 1]['name']} {camp[n - 1]['goals']}): score {sc.score} -> stage {sc.n} {sc.state}")
print("shots in", SHOTS)
print("PAW PINBALL OK")
