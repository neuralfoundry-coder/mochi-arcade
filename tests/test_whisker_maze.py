"""WHISKER MAZE checks: all 200 stages generate deterministically and validate (mirror symmetry, every crumb
reachable with the cupboard doors shut, no dead ends for the bots, the dock leads out ...), the iOS export
round-trips, the pre-turn buffer and the bat/knock chain behave, then headless autopilot runs of a normal stage,
both bonus kinds, every boss design and some late stages.
usage: MOCHI_FAST=1 python tests/test_whisker_maze.py [shot_dir]"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-wm-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A  # noqa: E402
from mochi_arcade.arcade import STAGES, is_bonus, is_boss  # noqa: E402
from mochi_arcade.games import GAMES  # noqa: E402
from mochi_arcade.games import whisker_maze as WM  # noqa: E402
from mochi_arcade.games import whisker_maze_maze as M  # noqa: E402

# ---------------------------------------------------------------- campaign data
camp = M.build_campaign()
assert len(camp) == STAGES == 200
assert camp == M.CAMPAIGN, "generation must be deterministic"
exp = json.loads(json.dumps(WM.EXPORT))
for st, ex in zip(camp, exp["stages"]):
    full = [r + r[-2::-1] for r in ex["rows"]]          # iOS rebuilds the mirrored right half
    assert full == st["rows"], st["n"]
assert len(exp["themes"]) == 20 and set(exp["bonus_themes"]) == {"mice", "fish"}
kinds = {"normal": 0, "boss": 0, "bonus": 0}
boss_kinds, names, bot_first, feat_first = set(), set(), {}, {}
for st in camp:
    n = st["n"]
    errs = M.validate(st)
    assert not errs, (n, st["name"], errs)
    kinds[st["kind"]] += 1
    assert st["tier"] == (n - 1) // 10
    assert (st["kind"] == "boss") == is_boss(n) and (st["kind"] == "bonus") == is_bonus(n), n
    for row in st["rows"]:
        assert all(ch in "#.oP=-Dd~% " for ch in row), (n, row)
    names.add(st["name"])
    for k, _, _ in st["bots"]:
        bot_first.setdefault(k, st["tier"])
    for f in st["feats"]:
        feat_first.setdefault(f, st["tier"])
    if st["dark"]:
        feat_first.setdefault("dark", st["tier"])
    if st["kind"] == "boss":
        b = st["boss"]
        boss_kinds.add(b["kind"])
        assert b["hp"] > 0 and b["rate"] > 0 and b["patterns"]
        assert len(st["nips"]) == 4
    if st["kind"] == "bonus":
        assert st["bonus"] in ("mice", "fish") and st["time"] > 0 and len(st["spots"]) >= 10
assert kinds == {"normal": 160, "boss": 20, "bonus": 20}, kinds
assert len(boss_kinds) >= 5, boss_kinds
assert len(names) >= 30, len(names)
assert bot_first == {"sniffy": 0, "zig": 0, "fridgy": 1, "snoozy": 2, "mopsy": 3, "spritz": 5, "ruff": 6}, bot_first
assert feat_first["doors"] == 1 and feat_first["tunnel"] == 2 and feat_first["wet"] == 3, feat_first
assert feat_first["paw"] == 4 and feat_first["dark"] == 8, feat_first
# difficulty goes up: faster bots, more of them, shorter catnip, tougher bosses
assert camp[190]["speed"] > camp[0]["speed"] and camp[190]["nip"] < camp[0]["nip"]
assert len(camp[187]["bots"]) > len(camp[0]["bots"])
assert camp[199]["boss"]["hp"] > camp[9]["boss"]["hp"] and camp[199]["boss"]["kind"] == "empress"
print(f"campaign OK: {kinds}, {len(names)} stage names, bosses {sorted(boss_kinds)}")

info = next(g for g in GAMES if g.id == "whisker_maze")


def make(stage, frames=10, script=None):
    app = A.App(windowed=True, mute=True, test_frames=frames, script=script)
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    sc = info.load()(app, info, {"difficulty": "normal", "stage": stage})
    sc.picks_left = 0
    sc.state = "play"
    app.apply_settings()
    app.scenes = [sc]
    sc.enter()
    return app, sc


def step(app, sc, keys, n=1):
    for _ in range(n):
        app.input.held = set()
        app.input.script = lambda f: keys
        app.input.begin()
        app.input.end(app.frame)
        app.frame += 1
        sc.t += 1 / 60
        sc.update(1 / 60)


# ---------------------------------------------------------------- pre-turn buffer + corner assist
app, sc = make(1)
sc.bots = []
rows = sc.st["rows"]
# find a horizontal corridor tile with an opening upwards two tiles further right
spot = None
for y in range(1, M.ROWS - 1):
    for x in range(1, M.COLS - 4):
        if all(sc.walk(x + i, y, "cat") for i in range(3)) and sc.walk(x + 2, y - 1, "cat") and \
                not sc.walk(x + 1, y - 1, "cat") and not sc.walk(x, y - 1, "cat"):
            spot = (x, y)
            break
    if spot:
        break
assert spot, "test corridor"
sc.nori = WM.Mover(*spot)
sc.nori.dir = (1, 0)
step(app, sc, {"up"}, 1)            # one tap, well before the junction
step(app, sc, set(), 40)            # released: the buffer remembers the turn
assert sc.nori.dir == (0, -1) or sc.nori.y < spot[1] - 0.5, ("pre-turn", sc.nori.x, sc.nori.y, sc.nori.dir)
# late press: 0.25 tiles past a junction still turns (corner assist)
sc.nori = WM.Mover(spot[0] + 2.25, spot[1])
sc.nori.dir = (1, 0)
step(app, sc, {"up"}, 1)
assert sc.nori.dir == (0, -1) and sc.nori.x == spot[0] + 2, ("assist", sc.nori.x, sc.nori.dir)
print("pre-turn buffer + corner assist OK")
pygame.quit()

# ---------------------------------------------------------------- bat a dizzy bot into two others
app, sc = make(1)
sc.bots = []
y, x0 = None, None
for yy in range(1, M.ROWS - 1):
    for xx in range(1, M.COLS - 8):
        if all(sc.walk(xx + i, yy, "bot") for i in range(7)):
            y, x0 = yy, xx
            break
    if y:
        break
assert y is not None
sc.nori = WM.Mover(x0, y)
sc.nori.dir = (1, 0)
bots = []
for i, k in enumerate(("sniffy", "zig", "fridgy")):
    b = WM.Bot(k, x0 + 1 + i * 2, y, (x0, y))
    b.state = "roam"
    b.post_dist = WM.bfs_tiles(sc, (x0, y), "bot", doors=True)
    bots.append(b)
sc.bots = bots
sc.start_zoomy(6.0)
for b in bots[1:]:
    b.frozen = 2.0                   # hold still so the puck reaches them
step(app, sc, {"right"}, 30)
step(app, sc, set(), 120)
assert sc.chain >= 3 and sc.batted >= 3, ("knock chain", sc.chain, sc.batted, [b.state for b in bots])
assert all(b.state in ("reboot", "dock", "leave") for b in bots), [b.state for b in bots]
print(f"bat + knock chain OK: chain {sc.chain}, score {sc.score}")
pygame.quit()


# ---------------------------------------------------------------- headless autopilot runs
def play(stage, frames, levels=None, name=None):
    ref = [None]
    stats = {"boss_hp": None, "stages": set(), "mice": 0, "eaten": 0, "max_score": 0}
    app = A.App(windowed=True, mute=True, test_frames=frames, script=lambda f: WM.autopilot(ref[0], f))
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    sc = info.load()(app, info, {"difficulty": "easy", "stage": stage})
    sc.levels.update(levels or {})
    sc.picks_left = 0
    if sc.state == "pick":
        sc.state = "intro"
    ref[0] = sc
    app.apply_settings()
    app.scenes = [sc]
    sc.enter()
    shots = {30: "intro", frames // 3: "play"}
    for f in range(frames):
        app.input.begin()
        app.input.end(f)
        if app.scene is not sc:
            break
        sc.t += 1 / 60
        sc.update(1 / 60)
        if f % 3 == 0 or f in shots:
            sc.draw(app.canvas)
        if f in shots and sc.n == stage:
            app.screenshot(os.path.join(SHOTS, f"{name or 'wm-stage%d' % stage}-{shots[f]}.png"))
        if sc.state == "tally" and sc.tally_i >= len(sc.tally) and "tally" not in stats:
            stats["tally"] = True
            sc.draw(app.canvas)
            app.screenshot(os.path.join(SHOTS, f"{name or 'wm-stage%d' % stage}-tally.png"))
        if sc.overlay is not None and stats.get("pick_t", 0) < 55:
            stats["pick_t"] = stats.get("pick_t", 0) + 1
        if stats.get("pick_t") == 55 and "pick" not in stats:
            stats["pick"] = True
            sc.draw(app.canvas)
            app.screenshot(os.path.join(SHOTS, f"{name or 'wm-stage%d' % stage}-pick.png"))
        stats["stages"].add(sc.n)
        if sc.n == stage:
            stats["mice"] = max(stats["mice"], sc.mice_caught)
            stats["eaten"] = max(stats["eaten"], sc.eaten)
            if sc.boss:
                stats["boss_hp"] = sc.boss.hp
    sc.draw(app.canvas)
    app.screenshot(os.path.join(SHOTS, (name or f"wm-stage{stage}") + ".png"))
    pygame.quit()
    return sc, stats


sc, stats = play(1, 5400)
assert sc.score > 0 and stats["eaten"] > 60, ("the bot should eat on stage 1", stats)
print(f"stage 1: ate {stats['eaten']}, reached stage {sc.n}, score {sc.score}, state {sc.state}")
sc, stats = play(5, 2400, name="wm-bonus-mice")
assert stats["mice"] > 0 and 6 in stats["stages"], stats
print(f"bonus mice: caught {stats['mice']}, then stage {sc.n}")
sc, stats = play(15, 2000, name="wm-bonus-fish")
assert stats["eaten"] > 40 and 16 in stats["stages"], stats
print(f"bonus fish: ate {stats['eaten']}, then stage {sc.n}")
for n in (10, 20, 30, 40, 50, 200):
    sc, stats = play(n, 4200, {"power": 2, "nip": 2}, name=f"wm-boss{n}")
    hp0 = camp[n - 1]["boss"]["hp"]
    print(f"boss stage {n} ({camp[n - 1]['boss']['name']}): hp {stats['boss_hp']}/{hp0} -> stage {sc.n} {sc.state}")
    assert stats["boss_hp"] is None or stats["boss_hp"] < hp0, "the boss should take damage"
for n in (34, 47, 61, 83, 121, 188):
    sc, stats = play(n, 1800, {"speed": 2})
    print(f"stage {n} ({camp[n - 1]['name']}): ate {stats['eaten']}, score {sc.score} -> stage {sc.n} {sc.state}")
    assert stats["eaten"] > 0
print("shots in", SHOTS)
print("WHISKER MAZE OK")
