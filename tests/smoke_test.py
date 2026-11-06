"""Headless smoke test: validates level data and runs every scene and game with scripted input.
usage: python tests/smoke_test.py [shot_dir]"""
import os
import random
import sys
import tempfile
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-test-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

from mochi_arcade import app as A, ui  # noqa: E402
from mochi_arcade.games import GAMES, soap_hop, bounce_bun, jelly_stack  # noqa: E402

# ---------------------------------------------------------------- data checks
for lv in soap_hop.LEVELS:
    m = soap_hop.build(lv)
    assert len(m) == 23 and all(len(r) == 40 for r in m), lv["name"]
    assert sum(r.count("P") for r in m) == 1, f"{lv['name']}: needs exactly one P"
    assert all(len(r) <= 36 for r in lv["rows"].values()), lv["name"]
for name, rows in bounce_bun.LEVELS:
    assert all(len(r) == 18 for r in rows), (name, [len(r) for r in rows])
for k, rots in jelly_stack.ROT.items():
    assert len(rots) == 4 and all(len(r) == 4 for r in rots), k
print("data OK")


def make_app(frames, script):
    app = A.App(windowed=True, mute=False, test_frames=frames, script=script)
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    return app


def mash(seed, keys, p=0.3):
    rnd = random.Random(seed)
    state = set()
    def f(frame):
        if frame % 6 == 0:
            state.clear()
            for k in keys:
                if rnd.random() < p:
                    state.add(k)
        return state
    return f


results = []
# ---------------------------------------------------------------- front-end scenes
fronts = [("boot", lambda a: ui.Boot(a)), ("title", lambda a: ui.Title(a)), ("profiles", lambda a: ui.ProfileSelect(a)),
          ("newprofile", lambda a: ui.ProfileCreate(a)), ("mainmenu", lambda a: ui.MainMenu(a)),
          ("gameselect", lambda a: ui.GameSelect(a, 2)), ("setup", lambda a: ui.GameSetup(a, 1)),
          ("options", lambda a: ui.Options(a)), ("scores", lambda a: ui.Scores(a))]
for name, mk in fronts:
    app = make_app(120, lambda f: set())
    app.shot_path = os.path.join(SHOTS, f"ui-{name}.png")
    t = time.time()
    app.run(mk(app))
    results.append((name, app.frame, time.time() - t))

# ---------------------------------------------------------------- games
plans = {
    "soap_hop": ["left", "right", "a", "b", "b"],
    "jelly_stack": ["left", "right", "down", "up", "a", "x"],
    "comet_kitty": ["left", "right", "a", "a"],
    "noodle_slurp": ["left", "right", "up", "down"],
    "bounce_bun": ["left", "right", "a"],
}
for info in GAMES:
    for seed in range(2):
        app = make_app(2400, mash(seed, plans[info.id]))
        app.shot_path = os.path.join(SHOTS, f"game-{info.id}-{seed}.png")
        opts = {k: d for k, _, _, d in info.options}
        scene = info.load()(app, info, opts)
        t = time.time()
        app.run(scene)
        results.append((f"{info.id}#{seed}", app.frame, time.time() - t))

# Result screen + profile persistence
app = make_app(60, lambda f: set())
app.shot_path = os.path.join(SHOTS, "ui-result.png")
app.run(ui.Result(app, GAMES[0], {}, 12345, False, "STAGE 3"))
assert app.store.game(app.profile, GAMES[0].id)["best"] >= 12345
for name, frames, dt in results:
    print(f"{name:16} {frames:5d} frames  {frames / max(dt, 1e-6):7.0f} fps(headless)")
print("shots in", SHOTS)
print("ALL OK")
