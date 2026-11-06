"""JELLY STACK campaign checks (headless).

- builds all 200 stages and validates each one (goals fit the setup, puzzles replay to a full clear ...)
- bot-plays stage 1, a bonus stage and boss stages for a while, fires every boss attack and upgrade,
  and walks the clear -> tally -> upgrade -> next stage flow.

usage: python tests/test_jelly_stack.py [shot_dir]
"""
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-js-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP

import pygame  # noqa: E402

from mochi_arcade import app as A  # noqa: E402
from mochi_arcade.arcade import is_bonus, is_boss  # noqa: E402
from mochi_arcade.games import GAMES  # noqa: E402
from mochi_arcade.games import jelly_stack as J  # noqa: E402
from mochi_arcade.games import jelly_stack_stages as S  # noqa: E402

INFO = next(g for g in GAMES if g.id == "jelly_stack")


# ---------------------------------------------------------------- data
def check_data():
    st = S.STAGE_LIST
    assert len(st) == 200 and [s["n"] for s in st] == list(range(1, 201))
    problems = [(s["n"], p) for s in st for p in S.validate(s)]
    assert not problems, problems[:10]
    assert all(s["k"] == "boss" for s in st if is_boss(s["n"]))
    assert all(s["k"] in ("rain", "well") for s in st if is_bonus(s["n"]))
    assert len({s["boss"]["id"] for s in st if s["boss"]}) >= 6
    assert len(S.UPGRADES) >= 6 and len(S.THEMES) == 20
    # a real difficulty curve: gravity and goals grow tier by tier
    g = [sum(s["g"] for s in st[t * 10:t * 10 + 10]) for t in range(20)]
    assert all(b >= a for a, b in zip(g, g[1:])), g
    hp = [s["boss"]["hp"] for s in st if s["boss"]]
    assert all(b >= a for a, b in zip(hp, hp[1:])), hp
    # every tier has variety
    for t in range(20):
        kinds = {s["k"] for s in st[t * 10:t * 10 + 10]}
        assert len(kinds) >= 6, (t, kinds)
    # EXPORT must be JSON for the iOS port
    import json
    json.dumps(J.EXPORT)
    print(f"data OK: 200 stages, {sum(1 for s in st if s['k'] == 'puzzle')} puzzles replayed")


# ---------------------------------------------------------------- headless harness
def make_app():
    app = A.App(windowed=True, mute=False, test_frames=10 ** 9, script=None)
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    app.audio.build_sfx()
    return app


def new_scene(app, **opt):
    o = {k: d for k, _, _, d in INFO.options}
    o.update(opt)
    scene = J.JellyStack(app, INFO, o)
    app.scenes = [scene]
    scene.enter()
    return scene


def step(app, scene, frames, bot=None):
    for _ in range(frames):
        app.input.begin()
        app.input.script = bot
        app.input.end(app.frame)
        scene.t += 1 / 60
        scene.update(1 / 60)
        app.frame += 1
        if app.scene is not scene:
            break
    scene.draw(app.canvas)


def shot(app, path):
    if path:
        pygame.image.save(pygame.transform.scale(app.canvas, (960, 600)), path)


def bot(scene):
    """Greedy placement bot (same idea as the GIF recorder): pick the best rot/x, tap there, hard drop."""
    st = {"piece": None, "target": None, "age": 0}

    def evaluate():
        p = scene.cur
        best = None
        for rot in range(4):
            for x in range(-3, J.BW + 3):
                if not scene.fits(p.cells(x, p.y, rot)):
                    continue
                y = p.y
                while scene.fits(p.cells(x, y + 1, rot)):
                    y += 1
                grid = [row[:] for row in scene.grid]
                ok = True
                for cx, cy in p.cells(x, y, rot):
                    if cy < 0:
                        ok = False
                        break
                    grid[cy][cx] = "x"
                if not ok:
                    continue
                lines = sum(1 for r in grid if all(r))
                heights, holes = [], 0
                for cx in range(J.BW):
                    colm = [grid[cy][cx] for cy in range(J.BH)]
                    top = next((i for i, v in enumerate(colm) if v), J.BH)
                    heights.append(J.BH - top)
                    holes += sum(1 for v in colm[top:] if not v)
                bump = sum(abs(heights[i] - heights[i + 1]) for i in range(J.BW - 1))
                sc = lines * 7.6 - holes * 3.6 - sum(heights) * 0.51 - bump * 0.18
                if best is None or sc > best[0]:
                    best = (sc, rot, x)
        return best

    def f(frame):
        keys = set()
        if scene.overlay is not None:
            return {"a"} if frame % 20 == 0 else set()
        if scene.campaign and scene.state != "play":
            return {"a"} if frame % 10 == 0 else set()
        if scene.clearing or scene.ending is not None:
            return keys
        if scene.cur is not st["piece"]:
            st["piece"] = scene.cur
            b = evaluate()
            st["target"] = b[1:] if b else (0, scene.cur.x)
            st["age"] = 0
        st["age"] += 1
        rot, x = st["target"]
        p = scene.cur
        if frame % 2:
            return keys
        if p.rot != rot and st["age"] < 40:
            keys.add("up")
        elif p.x != x and st["age"] < 60:
            keys.add("right" if x > p.x else "left")
        elif st["age"] > 6:
            keys.add("y")
        return keys
    return f


# ---------------------------------------------------------------- play tests
def play_tests(shots=None):
    random.seed(7)
    app = make_app()
    sp = (lambda name: os.path.join(shots, name)) if shots else (lambda name: None)

    # stage 1: intro card, then the bot clears it and the tally runs
    sc = new_scene(app, start=1)
    step(app, sc, 30)
    shot(app, sp("01-intro.png"))
    assert sc.state == "intro" and sc.stage_n == 1
    b = bot(sc)
    step(app, sc, 600, b)
    shot(app, sp("02-stage1-play.png"))
    for _ in range(60):
        if sc.stage_n > 1 or sc.state in ("tally", "clear"):
            break
        step(app, sc, 60, b)
    assert sc.stage_n > 1 or sc.state in ("clear", "tally"), (sc.state, sc.srows)
    print("stage 1 cleared by the bot, score", sc.score)

    # the stage-clear tally rolls its bonus lines into the score
    sc = new_scene(app, start=1)
    sc.begin_stage(3)
    sc.start_play()
    step(app, sc, 120)
    sc.grid = [[None] * J.BW for _ in range(J.BH)]
    score0 = sc.score
    sc.stage_clear()
    step(app, sc, 150)
    shot(app, sp("03-tally.png"))
    assert sc.state == "tally" and sc.score > score0 + 1000 * sc.level

    # a later tier with modifiers, plus every cell type drawn
    sc = new_scene(app, start=121)
    sc.start_play()
    sc.grid[19] = ["g", "i", "*", "b", "c", "$", "s", None, "mint", "pink"]
    sc.ups.update({"peek": 2, "zap": 2, "shield": 1, "bomb": 1, "pocket": 1, "lucky": 1})
    sc.zap = 5
    sc.shield = 2
    step(app, sc, 200, bot(sc))
    shot(app, sp("04-tier13.png"))

    # intro cards that introduce new things, modifiers in play, FEVER rainbow
    for n in (3, 61, 91):
        sc = new_scene(app, start=1)
        sc.begin_stage(n)
        step(app, sc, 40)
        shot(app, sp(f"14-intro-{n}.png"))
    for n in (61, 91, 64):
        sc = new_scene(app, start=1)
        sc.begin_stage(n)
        sc.start_play()
        step(app, sc, 400, bot(sc))
        shot(app, sp(f"15-play-{n}-{sc.st['k']}.png"))
    sc = new_scene(app, start=1)
    sc.begin_stage(34)
    sc.start_play()
    sc.hype.start_fever()
    step(app, sc, 240, bot(sc))
    shot(app, sp("16-fever-stars.png"))

    # bonus stages: candy rain and jackpot well
    for n, name in ((5, "05-bonus-rain.png"), (15, "06-bonus-well.png")):
        sc = new_scene(app, start=1)
        sc.begin_stage(n)
        assert sc.st["k"] in ("rain", "well")
        b = bot(sc)
        step(app, sc, 900, b)
        shot(app, sp(name))
        for _ in range(40):
            if sc.state != "play":
                break
            step(app, sc, 60, b)
        assert sc.state in ("clear", "tally", "upgrade", "intro") or sc.stage_n > n, sc.state
        print(f"bonus stage {n} ({sc.st['k']}) coins {sc.coins}")

    # boss: warning, then the bot fights while every attack fires
    sc = new_scene(app, start=1)
    sc.begin_stage(10)
    step(app, sc, 40)
    shot(app, sp("07-boss-warning.png"))
    b = bot(sc)
    step(app, sc, 200, b)
    for atk in S.ATTACKS:
        if sc.state != "play":
            break
        sc.boss["tele"] = [atk, 5.0]
        step(app, sc, 20, b)
        if atk == "heavy":
            shot(app, sp("08-boss-telegraph.png"))
        sc.boss["tele"] = None
        sc.boss_attack(atk)
        step(app, sc, 20, b)
        if atk == "ink":
            shot(app, sp("09-boss-ink.png"))
    hp0 = sc.boss["hp"] if sc.boss else 0
    step(app, sc, 600, b)
    assert sc.stage_n > 10 or sc.boss["hp"] < hp0 or sc.state != "play"
    print("boss stage 10: reached stage", sc.stage_n, "state", sc.state)

    # final boss art + the knock-out moment, then the upgrade cards
    sc = new_scene(app, start=1)
    sc.lives = 9
    for n in (20, 30, 40, 50, 60, 200):
        sc.begin_stage(n)
        sc.start_play()
        step(app, sc, 30)
        shot(app, sp(f"10-boss-{n}.png"))
    sc.hit_boss(10000)
    assert sc.state == "bossdown"
    step(app, sc, 40)
    shot(app, sp("11-bossdown.png"))
    for _ in range(40):
        step(app, sc, 30, lambda fr: {"a"} if fr % 10 == 0 else set())
        if sc.ending is not None:
            break
    assert sc.ending is not None, "clearing stage 200 must finish the run"

    sc = new_scene(app, start=1)
    sc.begin_stage(30)
    sc.start_play()
    sc.hit_boss(10000)
    for _ in range(60):
        step(app, sc, 10, lambda fr: {"a"} if fr % 10 == 0 else set())
        if sc.overlay is not None:
            break
    assert sc.overlay is not None, sc.state
    step(app, sc, 40)
    shot(app, sp("12-upgrade-cards.png"))
    step(app, sc, 5, lambda fr: {"a"})
    assert sc.overlay is None and sc.stage_n == 31 and sum(sc.ups.values()) == 1, (sc.stage_n, sc.ups)

    # puzzle stage: replay the stored solution through the real controls
    sc = new_scene(app, start=1)
    sc.begin_stage(7)
    sc.start_play()
    for kind, rot, x in sc.st["sol"]:
        assert sc.cur.kind == kind
        while sc.cur.rot != rot:
            sc.rotate(1)
        while sc.cur.x != x:
            sc.try_move(1 if x > sc.cur.x else -1, 0)
        sc.hard_drop()
        step(app, sc, 25)
    assert sc.state in ("clear", "tally"), sc.state
    print("puzzle stage 7 solved through the scene")

    # failing: top out costs a life and retries; last life ends the run
    sc = new_scene(app, start=1)
    sc.start_play()
    sc.lives = 2
    sc.fail_stage("TEST")
    step(app, sc, 130)
    assert sc.lives == 1 and sc.state == "intro" and sc.missed
    sc.start_play()
    sc.fail_stage("TEST")
    step(app, sc, 130)
    assert sc.ending is not None

    # classic modes still play
    for mode in ("marathon", "sprint", "endless"):
        sc = new_scene(app, mode=mode)
        step(app, sc, 900, bot(sc))
        shot(app, sp(f"13-classic-{mode}.png"))
        assert sc.lines > 0, mode
    print("classic modes OK")


if __name__ == "__main__":
    check_data()
    shots = sys.argv[1] if len(sys.argv) > 1 else None
    if shots:
        os.makedirs(shots, exist_ok=True)
    play_tests(shots)
    print("ALL OK")
