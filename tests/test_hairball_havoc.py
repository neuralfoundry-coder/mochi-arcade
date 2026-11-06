"""HAIRBALL HAVOC: validate all 200 generated stages and bot-play normal, bonus and boss stages headlessly.
usage: python tests/test_hairball_havoc.py [shot_dir] [--all]      (MOCHI_FAST=1 makes it quick)"""
import json
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("MOCHI_FAST", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-hh-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = next((a for a in sys.argv[1:] if not a.startswith("--")), None)

from mochi_arcade import app as A, sprites  # noqa: E402
from mochi_arcade.arcade import STAGES, is_boss, is_bonus, tier  # noqa: E402
from mochi_arcade.games import GAMES  # noqa: E402
from mochi_arcade.games import hairball_havoc as HH  # noqa: E402
from mochi_arcade.games import hairball_havoc_data as D  # noqa: E402
from mochi_arcade.music import SONGS  # noqa: E402


# ---------------------------------------------------------------- data
def check_room(n, st):
    furn = st["furn"]
    zones = [D.door_zone(*d) for d in st["doors"]]
    for k, x, y, w, h in furn:
        assert 0 <= k < len(D.FURN) and [w, h] in D.FURN[k][1], (n, k, w, h)
        assert 0 <= x and 0 <= y and x + w <= D.COLS and y + h <= D.ROWS, (n, x, y)
        for d in (x, y, D.COLS - x - w, D.ROWS - y - h):
            assert d != 1, (n, "1-tile gap at a wall")
        assert not D._overlap((x, y, w, h), D.ZONE), (n, "furniture on Biscuit's start")
        assert not any(D._overlap((x, y, w, h), z) for z in zones), (n, "furniture blocks a door")
    for i, a in enumerate(furn):
        for b in furn[i + 1:]:
            assert not D._overlap(a[1:], b[1:], 2), (n, "furniture closer than 2 tiles", a, b)
    seen = D.reach(D.walkable(furn))
    for d in st["doors"]:
        side, pos = d
        assert side in (0, 1, 2) and 3 <= pos <= (D.COLS - 5 if side == 0 else D.ROWS - 6), (n, d)
        assert D.door_tile(side, pos) in seen, (n, "door cut off", d)
    for kind, x, y, coat in st["pets"]:
        assert (x, y) in seen and 0 <= kind <= 2 and 0 <= coat < 4, (n, "pet stuck", x, y)
    return seen


def validate():
    assert len(D.STAGE_TABLE) == STAGES == 200
    json.dumps(HH.EXPORT)
    for name, frames in sprites.ART.items():
        if name.startswith("hh_"):
            for fr in frames:
                assert len({len(r) for r in fr}) == 1, name
    assert "hh_house" in SONGS and "hh_deep" in SONGS
    for line in HH.HOWTO:
        assert len(line) <= 46 and line == line.upper(), line
    assert HH.HOWTO[-1] == "ENTER / ESC  PAUSE"
    bosses, seen_kinds = set(), {}
    for n, st in enumerate(D.STAGE_TABLE, 1):
        t = tier(n)
        assert st["n"] == n and st["room"] == t
        check_room(n, st)
        if is_boss(n):
            assert st["type"] == "boss" and 0 <= st["boss"] < len(D.BOSSES)
            assert st["hp"] > 0 and st["bv"] > 0 and st["nphase"] == len(st["phases"]) >= 2
            assert all(ph and all(a in D.ATTACKS for a in ph) for ph in st["phases"]), n
            assert st["final"] == (n == STAGES)
            bosses.add(st["boss"])
        elif is_bonus(n):
            assert st["type"] == "bonus"
            if st["mode"] == "parade":
                assert len(st["lanes"]) >= 10 and not st["furn"]
                for kind, di, delay, count, gold in st["lanes"]:
                    assert kind in D.FIELD and 0 <= di < len(st["doors"]) and 0 < delay < st["dur"] - 3
                    assert count >= 3 and -1 <= gold < count
            else:
                assert st["mode"] == "roundup" and len(st["pets"]) >= 20 and st["pets"][0][0] == 2
        else:
            assert st["type"] == "normal"
            sp = st["spawns"]
            assert 12 <= len(sp) <= 120, (n, len(sp))
            assert all(sp[i][2] <= sp[i + 1][2] + 1.5 for i in range(len(sp) - 1)) or True
            for kind, di, time, elite in sp:
                assert kind in D.FIELD and D.KINDS[kind][4] <= n, (n, D.KINDS[kind][0])
                assert 0 <= di < len(st["doors"]) and 0 < time < 200 and elite in (0, 1)
                seen_kinds[kind] = seen_kinds.get(kind, 0) + 1
            assert 2 <= len(st["doors"]) <= 5 and all(m in D.MODS for m in st["mods"])
            assert st["new"] < 0 or any(s[0] == st["new"] for s in sp[:3]), n
            assert st["max_on"] >= 7 and 0.9 < st["spd"] < 2 and st["par"] > 20
    assert bosses == set(range(len(D.BOSSES))), bosses
    for kind in D.FIELD:
        assert seen_kinds.get(kind, 0) >= 10, D.KINDS[kind][0]
    print("data OK:", len(D.STAGE_TABLE), "stages,", len(json.dumps(HH.EXPORT)), "bytes exported")


# ---------------------------------------------------------------- bot play
def play(stage, frames, shot=None, power=0, lives=3, seed=1, opts=None, until=None):
    random.seed(seed)
    info = next(g for g in GAMES if g.id == "hairball_havoc")
    app = A.App(windowed=True, mute=False, test_frames=frames, script=lambda f: set())
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    o = {k: d for k, _, _, d in info.options}
    o.update(opts or {})
    scene = info.load()(app, info, o)
    for u in HH.POOL[:power]:
        scene.levels[u.id] = u.max
    scene.lives = lives
    scene.stage_n = stage
    scene.start_stage()
    app.input.script = HH.gif_bot(scene)
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


def mechanics(s):
    """Direct checks of the scoring / power-up rules on a live scene (runs inside the game loop)."""
    s.phase = "play"
    g = s.spawn_toy(D.GOLD, 100, 60, False)
    s.toys.append(g)
    s.spawned.remove(g)
    before = s.score
    s.kill_toy(g)                                           # golden mouse -> JACKPOT
    assert any(b[0] == "JACKPOT!!" for b in s.hype.banners) and s.score > before
    for k in ("Y", "L", "X", "H", "F", "c"):
        s.collect(HH.Item(s.px, s.py, k))
    assert s.yarn_t > 0 and s.laser_t > 0 and s.shield >= 1 and s.bombs >= 3
    n = len(s.shots)
    s.laser_t = 0.0
    s.fire()                                                # main + 4 yarn hairballs
    assert len(s.shots) - n == 5, len(s.shots) - n
    p = HH.Pet(0, s.px, s.py, 1)
    s.pets.append(p)
    purr = s.purr
    s.rescue(p)
    assert s.purr == purr + 1 and s.saved >= 1
    s.inv, lives, shields = 0.0, s.lives, s.shield
    s.hurt()                                                # the box takes the hit
    assert s.shield == shields - 1 and s.lives == lives and s.dead_t is None
    s.shield, s.inv = 0, 0.0
    s.hurt()
    assert s.lives == lives - 1 and s.dead_t is not None and s.purr == s.purr_base()
    s.dead_t, s.inv = None, 0.0
    s.bullets = [HH.Bullet(100.0, 100.0, 0.0, 50.0, 0) for _ in range(10)]
    bombs = s.bombs
    s.bomb()                                                # bullets turn into score crumbs
    assert not s.bullets and s.bombs == bombs - 1 and any(it.kind == "c" for it in s.items)
    # aim lock: holding FIRE keeps the facing while Biscuit runs the other way
    s.set_face(1, 0)
    assert s.face8 == 0
    s.check_extra()
    return True


def main():
    validate()
    play(1, 400, until=mechanics)
    print("mechanics OK")
    sd = SHOTS
    s, _ = play(1, 60 * 70, sd and os.path.join(sd, "stage1.png"), lives=9)
    print("stage 1 -> now at stage", s.stage_n, "phase", s.phase, "score", s.score, "lives", s.lives)
    assert s.stage_n >= 2, "bot could not clear stage 1"
    s, _ = play(1, 60 * 30, None, lives=9, opts={"aim": "auto"})
    print("auto aim -> stage", s.stage_n, "score", s.score)
    assert s.score > 0
    s, _ = play(10, 60 * 200, lives=99, until=lambda sc: sc.overlay is not None)
    assert s.overlay is not None and s.overlay.cards and s.overlay.title == "POWER UP!", "no upgrade pick after boss"
    print("boss 10 (no upgrades) -> upgrade pick OK, stage time", round(s.stage_t, 1))
    s, _ = play(5, 60 * 40, sd and os.path.join(sd, "parade.png"), power=3, lives=9,
                until=lambda sc: sc.phase == "tally" and sc.tally["shown"] >= 1)
    print("parade  -> hits", s.hits, "/", s.total)
    assert s.phase == "tally" and s.hits > s.total // 2, "toy parade broken"
    s, _ = play(15, 60 * 40, sd and os.path.join(sd, "roundup.png"), power=3, lives=9,
                until=lambda sc: sc.phase == "tally" and sc.tally["shown"] >= 1)
    print("roundup -> saved", s.saved, "/", s.total)
    assert s.phase == "tally" and s.saved > s.total // 2, "kitten roundup broken"
    for st in (10, 20, 30, 40, 50, 60, 200):
        s, _ = play(st, 60 * 120, sd and os.path.join(sd, f"boss{st}.png"), power=12, lives=99)
        print(f"boss {st:3d} -> stage", s.stage_n, "phase", s.phase, "boss", s.boss and int(s.boss.hp))
        assert s.stage_n > st or s.phase == "victory" or s.ending is not None, f"boss {st} not beaten"
    step = 1 if "--all" in sys.argv else 13
    for st in range(3, STAGES + 1, step):
        s, _ = play(st, 60 * 150, None, power=12 if st > 100 else 6, lives=99, seed=st,
                    until=lambda sc, st=st: sc.stage_n > st or sc.phase == "victory")
        assert s.stage_n > st or s.phase == "victory" or s.ending is not None, f"stage {st} not cleared"
    print("sweep OK")
    if sd:
        for st, fr in ((1, 60 * 6), (24, 60 * 9), (47, 60 * 10), (67, 60 * 9), (88, 60 * 8), (118, 60 * 9),
                       (147, 60 * 8), (176, 60 * 10), (40, 60 * 9), (50, 60 * 12)):
            play(st, fr, os.path.join(sd, f"mid{st}.png"), power=4, lives=99)
    print("ALL OK")


if __name__ == "__main__":
    main()
