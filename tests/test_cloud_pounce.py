"""CLOUD POUNCE campaign checks: all 200 stages generate deterministically and validate (a reachable cloud path from
the rooftop to the moon gate, everything inside the field), mechanics arrive tier by tier, then headless autopilot
runs of normal stages, all three bonus kinds and every boss design.
usage: MOCHI_FAST=1 python tests/test_cloud_pounce.py [shot_dir]"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-cp-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A  # noqa: E402
from mochi_arcade.arcade import STAGES, is_boss, is_bonus  # noqa: E402
from mochi_arcade.games import GAMES  # noqa: E402
from mochi_arcade.games import cloud_pounce as CP  # noqa: E402
from mochi_arcade.games import cloud_pounce_data as D  # noqa: E402

# ---------------------------------------------------------------- data
for name, tier, wgt, rows in D.CHUNKS:
    assert all(len(r) == D.COLS for r in rows), (name, [len(r) for r in rows])
for name, rows in D.BONUS_CHUNKS:
    assert all(len(r) == D.COLS for r in rows), name
assert all(len(line) <= 46 for line in CP.HOWTO) and CP.HOWTO[-1] == "ENTER / ESC  PAUSE"
assert len(CP.UPGRADES) >= 6
camp = D.build_campaign()
assert len(camp) == STAGES == 200
assert camp == D.CAMPAIGN, "generation must be deterministic"
assert json.loads(json.dumps(CP.EXPORT))["stages"] == camp, "EXPORT must be plain JSON"
kinds = {"normal": 0, "boss": 0, "bonus": 0}
boss_kinds, bonus_kinds, names = set(), set(), set()
first = {}
for st in camp:
    n = st["n"]
    unflat = {"c": D.unflat(st["c"], 4), "i": D.unflat(st["i"], 3), "f": D.unflat(st["f"], 5),
              "e": D.unflat(st["e"], 5)}
    errs = D.validate(dict(st, **unflat))
    assert not errs, (n, st["name"], errs)
    kinds[st["kind"]] += 1
    assert st["tier"] == (n - 1) // 10
    assert (st["kind"] == "boss") == is_boss(n) and (st["kind"] == "bonus") == is_bonus(n), n
    names.add(st["name"])
    if st["kind"] == "boss":
        b = st["boss"]
        boss_kinds.add(b["kind"])
        assert b["hp"] > 0 and b["rate"] > 0 and len(unflat["c"]) == 8
    elif st["kind"] == "bonus":
        bonus_kinds.add(st["bonus"])
        assert st["time"] > 0
    else:
        assert st["goal"] > 600 and st["par"] > 0
        for c in unflat["c"]:
            first.setdefault("cloud" + D.CLOUDS[c[0]] if c[0] < 8 else "floor", st["tier"])
        for e in unflat["e"]:
            first.setdefault(D.FOES[e[0]], st["tier"])
        for k, v in zip(("wind", "fog", "hail"), st["mods"]):
            if v:
                first.setdefault(k, st["tier"])
assert kinds == {"normal": 160, "boss": 20, "bonus": 20}, kinds
assert boss_kinds == set(D.BOSS_ORDER) and len(boss_kinds) >= 5, boss_kinds
assert bonus_kinds == set(D.BONUS_KINDS), bonus_kinds
assert len(names) >= 30, len(names)
assert first["cloudF"] == 0 and first["cloudT"] == 0 and first["cloudS"] == 0, first
assert first["cloudM"] == 1 and first["bird"] == 1 and first["kite"] == 2 and first["cloudR"] == 3, first
assert first["cloudZ"] == 4 and first["cloudG"] == 5 and first["cloudW"] == 6 and first["wind"] == 6, first
assert first["dot"] == 7 and first["fog"] == 8 and first["spark"] == 9 and first["hail"] == 10, first
# the climb gets longer and busier, bosses tougher
assert camp[190]["goal"] > camp[0]["goal"] * 2
foes = lambda sts: sum(len(s["e"]) for s in sts)  # noqa: E731
assert foes(camp[150:160]) > foes(camp[10:20])
assert camp[199]["boss"]["hp"] > camp[9]["boss"]["hp"] and camp[199]["boss"]["rate"] < camp[9]["boss"]["rate"]
assert len(camp[199]["boss"]["extra"]) == 3
size = len(json.dumps(CP.EXPORT, separators=(",", ":")))
print(f"campaign OK: {kinds}, {len(names)} names, bosses {sorted(boss_kinds)}, export {size // 1024} KB")

# ---------------------------------------------------------------- headless play
info = next(g for g in GAMES if g.id == "cloud_pounce")


def play(stage, frames, levels=None, name=None, hook=None):
    """Run the game headless with the autopilot (fixed 1/60 s steps), drawing every few frames."""
    ref = [None]
    stats = {"stages": set(), "boss_hp": None, "stars": 0, "pops": 0, "max_h": 0}
    app = A.App(windowed=True, mute=True, test_frames=frames, script=lambda f: CP.autopilot(ref[0]))
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    sc = info.load()(app, info, {"difficulty": "normal", "start": 1})
    sc.levels.update(levels or {})
    if stage != 1:
        sc.start_stage(stage)
    ref[0] = sc
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
        if hook:
            hook(sc, f)
        if f % 3 == 0:
            sc.draw(app.canvas)
        stats["stages"].add(sc.n)
        if sc.n == stage:
            stats["stars"] = max(stats["stars"], sc.got_stars)
            stats["pops"] = max(stats["pops"], sc.popped)
            stats["max_h"] = max(stats["max_h"], sc.h)
            if sc.boss:
                stats["boss_hp"] = sc.boss.hp
    sc.draw(app.canvas)
    app.screenshot(os.path.join(SHOTS, (name or f"cp-stage{stage}") + ".png"))
    pygame.quit()
    return sc, stats


sc, stats = play(1, 2400)
assert 2 in stats["stages"], f"the autopilot should clear stage 1 ({stats})"
print(f"stage 1: cleared, now stage {sc.n}, score {sc.score}")
sc, stats = play(5, 2400, name="cp-bonus-stars")
assert stats["stars"] > 5 and 6 in stats["stages"], stats
print(f"bonus STAR SHOWER: {stats['stars']} stars, then stage {sc.n}")
sc, stats = play(15, 1500, name="cp-bonus-rocket")
assert stats["stars"] > 10 and 16 in stats["stages"], stats
print(f"bonus ROCKET RIDE: {stats['stars']} stars, then stage {sc.n}")
sc, stats = play(25, 1800, name="cp-bonus-balloons")
assert 26 in stats["stages"], stats
print(f"bonus BALLOON BASH: {stats['pops']} balloons, then stage {sc.n}")


def immortal(sc, f):
    sc.lives = max(sc.lives, 3)


for n in (10, 20, 30, 40, 50, 120, 200):
    sc, stats = play(n, 2400, {"heavy": 2}, name=f"cp-boss{n}", hook=immortal)
    hp0 = camp[n - 1]["boss"]["hp"]
    print(f"boss stage {n} ({camp[n - 1]['boss']['name']}): hp {stats['boss_hp']}/{hp0} -> stage {sc.n} {sc.state}")
    assert stats["boss_hp"] is not None and stats["boss_hp"] < hp0, "the boss should take damage"
# later stages with every mechanic around (the autopilot does not dodge, so it just has to survive a while)
for n in (31, 47, 63, 88, 104, 137, 176, 199):
    sc, stats = play(n, 1200, {"spring": 2, "steer": 2}, hook=immortal)
    print(f"stage {n} ({camp[n - 1]['name']}): climbed {int(stats['max_h'])} of {camp[n - 1]['goal']} -> "
          f"stage {sc.n} {sc.state}")
    assert stats["max_h"] > 300, stats
print("shots in", SHOTS)
print("CLOUD POUNCE OK")
