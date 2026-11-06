"""KITTEN PILE campaign checks (headless).

- generates all 200 stages and validates each one (prebuilt chains replay to their length, star / pillow
  counts match, nothing starts popped or floating, colours fit the stage palette)
- checks the core rules (groups, gravity, junk hits, yarn, toy mouse) and that the xorshift generator matches
  the Swift port's reference values
- bot-plays stage 1, bonus stages, a duel and boss stages, fires every rival attack and upgrade, and walks the
  clear -> tally -> upgrade -> next stage flow

usage: python tests/test_kitten_pile.py [shot_dir]
"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-kp-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else None

import pygame  # noqa: E402

from mochi_arcade import app as A  # noqa: E402
from mochi_arcade.arcade import is_bonus, is_boss  # noqa: E402
from mochi_arcade.games import GAMES  # noqa: E402
from mochi_arcade.games import kitten_pile as KP  # noqa: E402
from mochi_arcade.games import kitten_pile_core as K  # noqa: E402
from mochi_arcade.games import kitten_pile_stages as S  # noqa: E402

INFO = next(g for g in GAMES if g.id == "kitten_pile")


# ---------------------------------------------------------------- rules
def check_rules():
    r = K.KRand(12345)
    assert [r.next() for _ in range(3)] == [3336926330, 1697253807, 2816511904], "xorshift32 changed (Swift parity)"
    g = K.parse_rows(["1.....", "1.....", "11...."])
    assert K.find_groups(g) == [[(0, 9), (0, 10), (0, 11), (1, 11)]]
    # gravity drops floating kittens
    g = K.empty_grid()
    g[3][2] = 4
    moves = K.apply_gravity(g)
    assert moves == [(2, 3, 11)] and g[11][2] == 4
    # junk next to a pop: pillows vanish, grandpa yawns first
    g = K.parse_rows(["P.....", "1G....", "1.....", "11...."])
    chain, popped, _ = K.resolve(g)
    assert chain == 1 and popped == 4 and K.count_cells(g, lambda c: c == K.PILLOW) == 0
    assert K.count_cells(g, lambda c: c == K.GRANDPA1) == 1
    # a yarn ball on a kitten puts that whole colour to sleep
    g = K.parse_rows(["2.....", "1...2.", "1.2.3."])
    landed = K.place(g, [(0, 0, K.YARN)])
    chain, popped, _ = K.resolve(g, landed)
    assert chain >= 1 and K.count_cells(g, lambda c: K.kcolor(c) == 2) == 0
    # a toy mouse shoos pillows and grandpas around it
    g = K.parse_rows(["PP....", "GP....", "PPP..."])
    landed = K.place(g, [(1, 0, K.MOUSE)])
    K.resolve(g, landed, mouse_r=2)
    assert K.count_cells(g, K.is_junk) == 3          # lands on row 8: rows 6..10 cleared, the bottom row stays
    # chain construction
    for n in (2, 4, 6):
        rows, c, x = None, 0, 0
        seed = 1
        while rows is None:
            res = K.build_chain(K.KRand(seed), n, 4)
            seed += 1
            if res:
                rows, c, x = res
        assert K.chain_of(rows, c, x) == n
    print("rules OK")


# ---------------------------------------------------------------- data
def check_data():
    st = S.stages()
    assert len(st) == 200 and [s["n"] for s in st] == list(range(1, 201))
    problems = [(s["n"], p) for s in st for p in S.validate(s)]
    assert not problems, problems[:10]
    assert all(s["k"] == "boss" for s in st if is_boss(s["n"]))
    assert all(s["k"] in ("snack", "domino") for s in st if is_bonus(s["n"]))
    assert len({s["boss"]["id"] for s in st if s["boss"]}) >= 6
    assert len(S.UPGRADES) >= 6 and len(S.THEMES) == 20
    g = [sum(s["g"] for s in st[t * 10:t * 10 + 10] if s["k"] not in ("snack", "domino")) for t in range(20)]
    assert all(b <= a * 1.15 for a, b in zip(g, g[1:])), g          # pieces fall faster tier by tier
    hp = [s["boss"]["hp"] for s in st if s["boss"]]
    assert all(b >= a for a, b in zip(hp, hp[1:])), hp
    for t in range(20):
        kinds = {s["k"] for s in st[t * 10:t * 10 + 10]}
        assert len(kinds) >= 6, (t, kinds)
    ch = [s["setups"][0]["len"] for s in st if s["k"] == "trigger"]
    assert ch == sorted(ch), ch
    json.dumps(KP.EXPORT)
    n_setups = sum(len(s["setups"]) for s in st)
    print(f"data OK: 200 stages, {n_setups} prebuilt chains replayed, {len(json.dumps(KP.EXPORT)) // 1024} KB export")


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
    scene = KP.KittenPile(app, INFO, o)
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


def shot(app, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pygame.image.save(pygame.transform.scale(app.canvas, (960, 600)), os.path.join(SHOTS, name + ".png"))


def to_play(app, scene):
    for _ in range(600):
        if scene.state == "play":
            return
        step(app, scene, 1, lambda f: {"a"} if f % 20 == 0 else set())
    raise AssertionError(f"stuck in {scene.state}")


def play(app, scene, frames, name=None):
    bot = KP.gif_bot(scene)
    step(app, scene, frames, bot)
    if name:
        shot(app, name)


def run_flow():
    app = make_app()
    # stage 1 with the bot: it should clear the nap goal
    sc = new_scene(app)
    step(app, sc, 30)
    shot(app, "01-intro")
    to_play(app, sc)
    play(app, sc, 600, "02-stage1")
    for _ in range(40):
        if sc.stage_n > 1 or sc.state in ("clear", "tally"):
            break
        play(app, sc, 300)
    assert sc.stage_n > 1 or sc.state in ("clear", "tally", "upgrade"), (sc.stage_n, sc.state, sc.kits)
    print(f"stage 1 cleared by the bot (score {sc.score})")

    # bonus stages
    for n, name in ((5, "03-snack"), (15, "04-domino")):
        sc = new_scene(app, start=n)
        to_play(app, sc)
        play(app, sc, 420, name)
        for _ in range(30):
            if sc.state != "play":
                break
            play(app, sc, 120)
        assert sc.state in ("clear", "tally", "upgrade") or sc.stage_n > n, (n, sc.state)
        print(f"bonus {n} ({sc.st['k']}): {sc.coins} coins, best chain {sc.best_chain}")
        if n == 15:
            assert sc.best_chain >= 3, sc.best_chain

    # a boss: telegraph, every attack, hits, defeat, upgrade pick, next stage
    sc = new_scene(app, start=10)
    step(app, sc, 40)
    shot(app, "05-warning")
    to_play(app, sc)
    play(app, sc, 500, "06-boss")
    for atk in S.ATTACK_NAMES:
        sc.foe_attack(atk)
        play(app, sc, 120)
    sc.state = "play"
    sc.hit_foe(5)
    assert sc.foe["hp"] < sc.foe["max"]
    sc.hit_foe(10 ** 6)
    assert sc.state == "bossdown"
    step(app, sc, 200)
    for _ in range(400):
        if sc.overlay is not None:
            break
        step(app, sc, 1, lambda f: {"a"} if f % 15 == 0 else set())
    assert sc.overlay is not None, sc.state
    shot(app, "07-upgrades")
    step(app, sc, 40, lambda f: {"a"} if f % 10 == 0 else set())
    assert sc.stage_n == 11 and sum(sc.ups.values()) == 1, (sc.stage_n, sc.ups)
    print(f"boss 10 down, upgrade {sc.ups}, now stage {sc.stage_n}")

    # every upgrade at max, a late duel and the final boss
    for u in S.UPGRADES:
        sc.ups[u[0]] = u[4]
    for n, name in ((58, "08-dark"), (96, "09-duel"), (143, "10-late"), (200, "11-final")):
        ups = dict(sc.ups)
        sc = new_scene(app, start=n)
        sc.ups = ups
        to_play(app, sc)
        play(app, sc, 700, name)
        print(f"stage {n} ({sc.st['k']}): state {sc.state}, score {sc.score}, best chain {sc.best_chain}")

    # top out -> lose a life -> retry; out of lives -> game over
    sc = new_scene(app, start=3)
    to_play(app, sc)
    for y in range(K.ROWS):
        for x in range(K.COLS):
            sc.grid[y][x] = K.PILLOW
    sc.phase, sc.phase_t, sc.guard = "wait", 0.0, 0
    lives = sc.lives
    step(app, sc, 5)
    assert sc.state == "fail" and sc.lives == lives - 1, (sc.state, sc.lives)
    step(app, sc, 130)
    assert sc.state in ("intro", "play") and sc.missed
    shot(app, "12-retry")
    print("fail -> retry OK")

    # the carousel preview
    s = pygame.Surface((112, 74))
    for i in range(30):
        KP.preview(s, i * 0.17)
    if SHOTS:
        pygame.image.save(pygame.transform.scale(s, (448, 296)), os.path.join(SHOTS, "13-preview.png"))


if __name__ == "__main__":
    check_rules()
    check_data()
    run_flow()
    print("kitten pile OK")
