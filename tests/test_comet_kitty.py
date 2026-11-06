"""COMET KITTY: validate all 200 generated stages and bot-play a normal, a bonus and a boss stage headlessly.
usage: python tests/test_comet_kitty.py [shot_dir]"""
import json
import math
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-ck-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = next((a for a in sys.argv[1:] if not a.startswith("--")), None)

from mochi_arcade import app as A  # noqa: E402
from mochi_arcade.arcade import STAGES, is_boss, is_bonus, tier  # noqa: E402
from mochi_arcade.games import GAMES  # noqa: E402
from mochi_arcade.games import comet_kitty as CK  # noqa: E402
from mochi_arcade.games import comet_kitty_data as D  # noqa: E402


# ---------------------------------------------------------------- data
def validate():
    assert len(D.STAGE_TABLE) == STAGES == 200
    json.dumps(CK.EXPORT)                       # exportable to iOS
    for pi, path in enumerate(D.PATHS):
        assert len(path) >= 4, D.PATH_NAMES[pi]
        for x, y in path:
            assert math.isfinite(x) and math.isfinite(y) and -40 <= x <= 360 and -40 <= y <= 240, D.PATH_NAMES[pi]
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            assert math.hypot(x1 - x0, y1 - y0) <= D.STEP + 1.5, D.PATH_NAMES[pi]   # evenly resampled
    for name in D.ENTRY:   # entry paths stay above Tama's flying band and end inside the formation area
        path = D.PATHS[D.path_index(name)]
        assert all(y < D.PLAYER_TOP for x, y in path if -10 < x < 330), name
        assert path[-1][1] < 120 and 0 < path[-1][0] < W, name
    used_bosses = set()
    for n, st in enumerate(D.STAGE_TABLE, 1):
        t = tier(n)
        assert st["n"] == n and st["theme"] == t and 0 <= t < len(D.THEMES)
        if is_boss(n):
            assert st["type"] == "boss"
            assert 0 <= st["boss"] < len(D.BOSSES) and st["hp"] > 0 and st["bv"] > 0
            assert len(st["phases"]) >= st["nphase"] >= 2
            assert all(ph and all(a in D.ATTACKS for a in ph) for ph in st["phases"]), n
            used_bosses.add(st["boss"])
        elif is_bonus(n):
            assert st["type"] == "bonus"
            assert len(st["waves"]) >= 5
            for pi, mirror, delay, count, gold, kd in st["waves"]:
                assert D.PATH_NAMES[pi] in D.PARADE and count >= 1 and -1 <= gold < count and 0 <= delay < 30
                assert D.KINDS[kd][4] <= t
        else:
            assert st["type"] == "normal"
            slots = st["slots"]
            assert 15 <= len(slots) <= 50, (n, len(slots))
            cells = set()
            for c, r, kd, pi, mirror, delay, g, cap in slots:
                assert -7 <= c <= 7 and 0 <= r <= 6, n
                assert (c, r) not in cells, (n, c, r)
                cells.add((c, r))
                assert D.KINDS[kd][4] <= t, (n, D.KINDS[kd][0])      # only unlocked foes
                name = D.PATH_NAMES[pi]
                assert name in D.ENTRY and D.ENTRY_UNLOCK[name] <= t, (n, name)
                assert 0 < delay < 25 and 0 <= g < st["groups"] and -1 <= cap < len(D.CAPSULES)
                # formation slot (with sway and breathing) is on screen, above the player band
                x = W / 2 + c * D.COL_DX * 1.05
                assert 14 <= x - 12 and x + 12 <= W - 14 and D.ROW_Y0 + r * D.ROW_DY + 8 < D.PLAYER_TOP
            assert all(sum(1 for s in slots if s[6] == g) >= 1 for g in range(st["groups"]))
            assert 0.5 <= st["dive_gap"] <= 3 and 1 <= st["dive_max"] <= 6 and 60 <= st["bv"] <= 160
            assert st["speed"] > 60 and st["par"] > 10 and all(m in D.MODS for m in st["mods"])
            if st["new"] >= 0:
                assert any(s[2] == st["new"] for s in slots), n
    assert used_bosses == set(range(len(D.BOSSES)))         # every boss design appears
    # every foe kind is introduced somewhere and shows up in many stages
    seen = {}
    for st in D.STAGE_TABLE:
        for s in st.get("slots", []):
            seen[s[2]] = seen.get(s[2], 0) + 1
    for kd in range(10):
        assert seen.get(kd, 0) >= 10, D.KINDS[kd][0]
    print("data OK:", len(D.STAGE_TABLE), "stages,", len(D.PATHS), "paths,", len(json.dumps(CK.EXPORT)), "bytes")


W = 320


# ---------------------------------------------------------------- bot play
def bot(scene):
    def f(frame):
        keys = set()
        if scene.overlay is not None or scene.phase == "tally":
            if frame % 20 == 0:
                keys.add("a")
            return keys
        if frame % 2 == 0:
            keys.add("a")
        cx, cy = scene.centre()
        threats = [b for b in scene.bullets if b[1] > cy - 50 and abs(b[0] - cx) < 16 and b[3] > 0]
        boss = scene.boss
        if boss is not None and boss.atk == "laser":
            for x in boss.lx:
                if abs(x - cx) < 18:
                    threats.append([x, cy, 0, 1])
        if threats:
            b = min(threats, key=lambda b: abs(b[0] - cx))
            keys.add("left" if b[0] > cx else "right")
            if cx < 30:
                keys.discard("left")
                keys.add("right")
            elif cx > W - 30:
                keys.discard("right")
                keys.add("left")
            keys.add("down")
            return keys
        live = [e for e in scene.enemies if e.state != "wait" and e.y > 0]
        tx = None
        if boss is not None:
            tx = boss.weak_pos()[0]
        elif live:
            tx = max(live, key=lambda e: e.y).x
        if tx is not None and abs(tx - cx) > 3:
            keys.add("right" if tx > cx else "left")
        if frame % 600 == 300 and scene.bombs > 1:
            keys.add("b")
        return keys
    return f


class FastClock:
    def tick(self, fps=0):
        return 16


def play(stage, frames, shot=None, power=0, lives=3, seed=1, opts=None, until=None):
    random.seed(seed)
    info = next(g for g in GAMES if g.id == "comet_kitty")
    app = A.App(windowed=True, mute=False, test_frames=frames, script=lambda f: set())
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    o = {k: d for k, _, _, d in info.options}
    o.update(opts or {})
    scene = info.load()(app, info, o)
    for u in CK.POOL[:power]:
        scene.levels[u.id] = u.max
    scene.lives = lives
    scene.stage_n = stage
    scene.start_stage()
    app.input.script = bot(scene)
    app.clock = FastClock()       # test frames use a fixed 1/60 s step anyway: don't sleep between them
    if until:
        orig = app.draw

        def draw():
            orig()
            if until(scene):
                app.running = False
        app.draw = draw
    if shot:
        app.shot_path = shot
    app.run(scene)
    return scene, app


def main():
    validate()
    sd = SHOTS
    # stage 1: a fresh kitty must be able to clear it
    s, app = play(1, 60 * 70, sd and os.path.join(sd, "stage1.png"), lives=9)
    print("stage 1 -> now at stage", s.stage_n, "phase", s.phase, "score", s.score, "lives", s.lives)
    assert s.stage_n >= 2, "bot could not clear stage 1"
    # a bonus parade (stage 5) and a later-tier normal stage
    s, _ = play(5, 60 * 30, sd and os.path.join(sd, "bonus.png"), power=3, lives=9)
    print("bonus  -> stage", s.stage_n, "hits", s.hits, "/", s.total)
    assert s.stage_n == 6 or s.overlay is not None or s.phase in ("tally", "between", "intro")
    s, _ = play(137, 60 * 25, sd and os.path.join(sd, "stage137.png"), power=6, lives=30)
    print("st 137 -> stage", s.stage_n, "score", s.score)
    # every boss design, with a maxed-out kitty, must go down and hand out the upgrade pick
    for st in (10, 20, 30, 40, 50, 60, 200):
        s, _ = play(st, 60 * 90, sd and os.path.join(sd, f"boss{st}.png"), power=10, lives=99)
        print(f"boss {st:3d} -> stage", s.stage_n, "phase", s.phase, "boss", s.boss and int(s.boss.hp))
        assert s.stage_n > st or s.phase in ("victory",) or s.ending is not None, f"boss {st} not beaten"
    # a sweep through every tier (pass --all for every single stage): each stage must be clearable
    step = 1 if "--all" in sys.argv else 13
    for st in range(3, STAGES + 1, step):
        s, _ = play(st, 60 * 150, None, power=10 if st > 100 else 4, lives=99, seed=st,
                    until=lambda sc, st=st: sc.stage_n > st or sc.phase == "victory")
        assert s.stage_n > st or s.phase == "victory" or s.ending is not None, f"stage {st} not cleared"
    print("sweep OK")
    # mid-fight screenshots
    if sd:
        for st, fr in ((10, 60 * 8), (40, 60 * 12), (60, 60 * 9), (155, 60 * 9), (85, 60 * 6)):
            play(st, fr, os.path.join(sd, f"mid{st}.png"), power=2, lives=99)
    print("ALL OK")


if __name__ == "__main__":
    main()
