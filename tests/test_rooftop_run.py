"""ROOFTOP RUN campaign checks: all 200 courses generate and validate (every gap jumpable at easy speed, wires and
laundry lines span their drops, skylights never in landing zones, a finish on a long flat roof), then headless
autopilot runs of normal stages, both bonus kinds and every boss design (each boss must be beaten).
usage: MOCHI_FAST=1 python tests/test_rooftop_run.py [shot_dir]"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-rr-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A, music, sprites  # noqa: E402
from mochi_arcade.arcade import STAGES, is_boss, is_bonus  # noqa: E402
from mochi_arcade.games import GAMES, rooftop_run as RR  # noqa: E402
from mochi_arcade.games import rooftop_run_course as C  # noqa: E402
from mochi_arcade.games import rooftop_run_world as RW  # noqa: E402

# ---------------------------------------------------------------- campaign data
camp = [C.build_stage(n) for n in range(1, STAGES + 1)]
assert len(camp) == STAGES == 200
assert camp == C.CAMPAIGN, "generation must be deterministic"
assert json.loads(json.dumps(RR.EXPORT))["stages"] == camp, "EXPORT must be plain JSON and match the campaign"
kinds = {"normal": 0, "boss": 0, "bonus": 0}
boss_kinds, bonus_kinds, names = set(), set(), set()
for st in camp:
    n = st["n"]
    errs = C.validate(st)
    assert not errs, (n, st["name"], errs[:5])
    kinds[st["kind"]] += 1
    assert st["tier"] == (n - 1) // 10
    assert (st["kind"] == "boss") == is_boss(n) and (st["kind"] == "bonus") == is_bonus(n), n
    for e in C.decode(st["c"]):
        assert e[0] in "RSLWNVMFAGPpqsaidzJE", (n, e)
        assert all(isinstance(v, int) for v in e[2 if e[0] == "S" else 1:]), (n, e)
    if st["kind"] == "boss":
        b = st["boss"]
        boss_kinds.add(b["kind"])
        assert b["hp"] > 0 and st["loop"] > 0 and b["kind"] in C.BOSS_KINDS
    elif st["kind"] == "bonus":
        bonus_kinds.add(st["bonus"])
        assert st["fish"] >= 80, (n, st["fish"])
    else:
        assert st["fish"] >= 30 and st["len"] > 2000, (n, st["fish"], st["len"])
    names.add(st["name"])
assert kinds == {"normal": 160, "boss": 20, "bonus": 20}, kinds
assert boss_kinds == set(C.BOSS_KINDS) and len(boss_kinds) >= 5, boss_kinds
assert bonus_kinds == set(C.BONUS_KINDS), bonus_kinds
assert len(names) >= 40, len(names)
# the difficulty curve: faster runs, longer courses, tougher bosses later on
assert camp[190]["speed"] > camp[0]["speed"] + 30
assert camp[198]["len"] > camp[1]["len"] + 1500
assert camp[199]["boss"]["hp"] > camp[9]["boss"]["hp"]
# every mechanic shows up from its district on, and never before
first = {}
for st in camp:
    for e in C.decode(st["c"]):
        key = {"L": "laundry", "W": "wire", "p": "pigeon", "q": "pigeon", "s": "sprinkler", "a": "antenna",
               "i": "icicle", "d": "diver", "z": "zap", "J": "pad", "M": "lift", "V": "updraft", "N": "wind"}.get(e[0])
        if e[0] == "S":
            key = {"K": "chimney", "B": "billboard", "U": "ac"}.get(e[1])
        if e[0] == "R" and e[4]:
            key = "glass"
        if key and st["kind"] == "normal":
            first.setdefault(key, st["tier"])
for f, tier in first.items():
    assert tier == C.INTRO[f], (f, tier, C.INTRO[f])
assert set(first) >= {"laundry", "chimney", "pigeon", "glass", "sprinkler", "billboard", "wire", "wind", "antenna",
                      "lift", "icicle", "pad", "diver", "zap"}, sorted(first)
# art and music registered for iOS
assert all(k in sprites.ART for k in ("rr_tora_run", "rr_gully", "rr_pigeon", "rr_fish", "rr_goldfish"))
assert "rr_run" in music.SONGS and "rr_chase" in music.SONGS
for frames in RR.rooftop_run_art.MY_ART.values():
    for fr in frames:
        assert len({len(r) for r in fr}) == 1, "ragged sprite"
assert all(len(line) <= 46 for line in RR.HOWTO) and RR.HOWTO[-1] == "ENTER / ESC  PAUSE"
print(f"campaign OK: {kinds}, {len(names)} stage names, bosses {sorted(boss_kinds)}")

# ---------------------------------------------------------------- physics sanity: a plain jump clears max_gap
v = RW.View.__new__(RW.View)
v.speed, v.t = 88.0 * C.EASY, 0.0
v.solids = [RW.Roof(0, 100, 150, 0), RW.Roof(100 + C.max_gap(88.0, 0), 400, 150, 0)]
v.lines, v.wires, v.winds, v.vents, v.pads = [], [], [], [], []
b = RW.Body(90, 150)
b.ground = v.solids[0]
held = False
for i in range(120):
    jump = 88 <= b.x < 100 or (b.ground is None and b.vy < 0)
    RW.step(b, RW.Ctrl(jump and not held, jump), 1 / 60, v)
    held = jump
assert b.ground is v.solids[1], "a held jump from the edge must clear the widest generated gap at easy speed"
print("physics OK")


# ---------------------------------------------------------------- headless play
info = next(g for g in GAMES if g.id == "rooftop_run")


def play(stage, frames, name, god=False, levels=None):
    """Run the game headless with the autopilot (no frame clock)."""
    ref = [None]
    app = A.App(windowed=True, mute=True, test_frames=frames, script=lambda f: RR.autopilot(ref[0]))
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    sc = info.load()(app, info, {"difficulty": "normal", "start": 1})
    sc.levels.update(levels or {})
    if stage != 1:
        sc.start_stage(stage)
    sc.apply_upgrades()
    ref[0] = sc
    app.apply_settings()
    app.scenes = [sc]
    sc.enter()
    stats = {"stages": set(), "boss_down": False, "max_fish": 0}
    for f in range(frames):
        app.input.begin()
        app.input.end(f)
        if app.scene is not sc:
            break
        if god:
            sc.lives = 9
        sc.t += 1 / 60
        sc.update(1 / 60)
        if f % 4 == 0:
            sc.draw(app.canvas)
        stats["stages"].add(sc.n)
        stats["max_fish"] = max(stats["max_fish"], sc.fish_got)
        if sc.boss and sc.boss.state == "dead":
            stats["boss_down"] = True
    sc.draw(app.canvas)
    app.screenshot(os.path.join(SHOTS, name + ".png"))
    pygame.quit()
    return sc, stats


sc, stats = play(1, 2600, "rr-stage1")
assert 2 in stats["stages"], f"the bot should clear stage 1 (reached {sorted(stats['stages'])})"
assert sc.score > 0 and sc.feathers >= 1, (sc.score, sc.feathers)
print(f"stage 1: cleared, score {sc.score}, feathers {sc.feathers}, hits {sc.hits}")
for n in (23, 64, 118, 187):
    sc, stats = play(n, 3000, f"rr-stage{n}", god=True, levels={"jump2": 1})
    assert n + 1 in stats["stages"], f"the bot should finish stage {n} ({sc.state}, x {int(sc.body.x)})"
    print(f"stage {n}: cleared, fish {stats['max_fish']}, hits {sc.hits} falls {sc.falls}")
for n in (5, 15):
    sc, stats = play(n, 2400, f"rr-bonus{n}")
    assert stats["max_fish"] >= 30, (n, stats["max_fish"])
    assert sc.lives == RR.LIVES_RR["normal"] or sc.lives > RR.LIVES_RR["normal"], "falling is free in bonus runs"
    print(f"bonus {n} ({camp[n - 1]['bonus']}): fish {stats['max_fish']}")
for n in (10, 20, 30, 40, 50, 200):
    sc, stats = play(n, 9000 if n == 200 else 6000, f"rr-boss{n}", god=True)
    assert stats["boss_down"], f"boss {camp[n - 1]['boss']['kind']} at stage {n} was not beaten (hp {sc.boss.hp})"
    print(f"boss {n} ({camp[n - 1]['boss']['kind']}): beaten, hits taken {sc.hits}")
print("shots in", SHOTS)
print("ALL OK")
