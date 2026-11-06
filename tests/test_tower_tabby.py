"""TOWER TABBY campaign tests (headless): all 200 stages generate deterministically and validate, the tree's
parts behave (beds, boxes, belts, ropes, tunnels, hammocks), every hazard runs, the bot climbs stage 1, bonus
stages time out into a tally, every boss pattern runs, and the boss -> upgrade -> next stage and final flows work.
usage: python tests/test_tower_tabby.py   (also works under pytest)"""
import json
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_TMP = tempfile.mkdtemp(prefix="tabby-test-")
os.environ["XDG_DATA_HOME"] = _TMP
os.environ["XDG_CACHE_HOME"] = _TMP

from mochi_arcade.arcade import STAGES, is_bonus, is_boss, tier  # noqa: E402
from mochi_arcade.games import tower_tabby_data as D  # noqa: E402


# ----------------------------------------------------------------------------- data
def test_campaign_shape_and_determinism():
    D._cache.clear()
    a = D.generate()
    D._cache.clear()
    b = D.generate()
    assert a == b, "stage generation must be deterministic"
    assert len(a) == STAGES == 200
    for n, st in enumerate(a, 1):
        want = "boss" if is_boss(n) else "bonus" if is_bonus(n) else "normal"
        assert st["k"] == want, (n, st["k"])
        assert st["th"] == tier(n), n
        assert len(st["lv"]) == 6 and all(len(r) == D.NC for r in st["lv"]), n
        assert len(st["sl"]) == 6 and st["sl"][0] == 0, n


def test_every_stage_is_winnable():
    for n, st in enumerate(D.generate(), 1):
        err = D.validate(st)
        assert err is None, f"stage {n} ({st['nm']}): {err}\n{D.ascii(st)}"
        if st["k"] == "normal":
            assert st["mix"] and st["rate"] >= 0.9, n
            assert 10 <= st["par"] <= 90, (n, st["par"])
            assert len(st["kit"]) >= 1 and len(st["fish"]) >= 5, n


def test_templates_are_sound():
    names = set()
    for name, t0, rows, slopes in D.TEMPLATES:
        names.add(name)
        lv = list(reversed(rows))
        st = {"k": "normal", "lv": lv, "sl": [0] + list(reversed(slopes)), "kit": [], "fish": [], "it": [], "en": []}
        assert D.validate(st) is None, name
        mlv, msl = D.mirror(rows, slopes)
        st = {"k": "normal", "lv": list(reversed(mlv)), "sl": [0] + list(reversed(msl)), "kit": [], "fish": [], "it": [],
              "en": []}
        assert D.validate(st) is None, name + " (mirrored)"
        for r in rows:
            for ch in r:
                key = ">" if ch == "<" else ch
                if key in D.STRUCTS:
                    assert D.STRUCTS[key][1] <= t0, f"{name}: {ch} before its tier"
    assert len(names) >= 20


def test_difficulty_curve_and_introductions():
    stages = D.generate()
    rates = []
    for t in range(20):
        normal = [stages[n - 1] for n in range(t * 10 + 1, t * 10 + 11) if stages[n - 1]["k"] == "normal"]
        rates.append(sum(s["rate"] for s in normal if "frenzy" not in s["mods"]) /
                     max(1, sum(1 for s in normal if "frenzy" not in s["mods"])))
        for s in normal:
            for kind, _, _ in s["en"]:
                assert D.HAZARDS[kind][1] <= t, f"{kind} placed before its tier ({t})"
            for kind in s["mix"]:
                assert D.HAZARDS[kind][1] <= t, f"KAW throws {kind} before its tier ({t})"
            for r in s["lv"]:
                for ch in r:
                    key = ">" if ch == "<" else ch
                    if key in D.STRUCTS:
                        assert D.STRUCTS[key][1] <= t, f"{ch} in tier {t}"
    assert all(rates[i + 1] <= rates[i] + 1e-9 for i in range(19)), rates
    assert rates[-1] < rates[0] * 0.6, rates
    news = {s["new"] for s in stages if s["new"]} | {s["nst"] for s in stages if s["nst"]}
    assert {"cone", "mouse", "cushion", "spider", "spritz", "ball", "bot", "moth", "marble"} <= news, news
    assert {"R", "~", "S", "X", ">", "W"} <= news, news
    mods = {m for s in stages for m in s["mods"]}
    assert mods == set(D.MODS), mods
    assert len({s["tpl"] for s in stages if s["k"] == "normal"}) >= 20


def test_bosses():
    stages = D.generate()
    bosses = [stages[n - 1] for n in range(10, 201, 10)]
    assert {b["boss"] for b in bosses} == set(D.BOSSES), "all seven bosses appear"
    assert stages[99]["boss"] == stages[199]["boss"] == "storm"
    last = {}
    for b in bosses:
        assert b["hp"] > last.get(b["boss"], 0), "a boss gets tougher every time it comes back"
        last[b["boss"]] = b["hp"]
        assert b["pat"], b
    assert any(len(set(b["pat"]) - set(D.BOSSES[b["boss"]][2])) for b in bosses), "late bosses borrow patterns"


def test_export():
    from mochi_arcade.games import tower_tabby
    ex = tower_tabby.EXPORT
    text = json.dumps(ex, separators=(",", ":"))
    assert len(text) < 200_000, len(text)
    gen = D.generate()
    for st, g in zip(ex["stages"], gen):
        assert st["lv"] == g["lv"] and st["nm"] == g["nm"]
        assert len(st["nm"]) <= 22, st["nm"]
        assert "tpl" not in st
    assert len(ex["themes"]) == 20


def test_upgrades_and_howto():
    from mochi_arcade.games.tower_tabby import HOWTO, UPGRADES
    assert len(UPGRADES) >= 6
    assert len({u.id for u in UPGRADES}) == len(UPGRADES)
    for u in UPGRADES:
        assert len(u.name) <= 14, u.name
        assert all(len(line) <= 14 for line in u.desc.split("|")), u.desc
    assert all(len(h) <= 46 and h == h.upper() for h in HOWTO), HOWTO
    assert HOWTO[-1] == "ENTER / ESC  PAUSE"
    for q in D.QUIPS:
        assert len(q) <= 30, q


# ----------------------------------------------------------------------------- simulation
_APP = []


def _scene(start=1, stage=None):
    from mochi_arcade import app as A
    from mochi_arcade.games import GAMES, tower_tabby
    if not _APP:
        app = A.App(windowed=True, mute=True, test_frames=1)
        if not app.store.profiles:
            app.store.create("TESTER", "pink")
        app.profile = app.store.last()
        _APP.append(app)
    app = _APP[0]
    info = next(g for g in GAMES if g.id == "tower_tabby")
    sc = tower_tabby.TowerTabby(app, info, {"difficulty": "normal", "start": start})
    if stage:
        sc.stage = stage
        sc.load_stage()
    sc.picks = 0
    sc.state = sc.intro_state
    app.scenes = [sc]
    sc.enter()
    return app, sc


def _run(app, sc, frames, script=None):
    for _ in range(frames):
        app.input.begin()
        keys = script(app.frame) if script else set()
        app.input.script = lambda f, k=keys: k
        app.input.end(app.frame)
        sc.t += 1 / 60
        sc.update(1 / 60)
        app.draw()
        app.frame += 1
        if sc.ending is not None:
            break


def _mash(seed):
    rnd = random.Random(seed)
    state = set()

    def f(frame):
        if frame % 6 == 0:
            state.clear()
            state.update(k for k in ("left", "right", "up", "down", "a", "b") if rnd.random() < 0.3)
        return set(state)
    return f


def _play(sc):
    sc.state, sc.state_t = "play", 0.0


def test_play_stage_one_with_bot():
    from mochi_arcade.games.tower_tabby import gif_bot
    random.seed(3)
    app, sc = _scene(1)
    sc.lives = 50
    _run(app, sc, 60 * 40, gif_bot(sc))
    assert sc.stage > 1, (sc.stage, sc.state, sc.score)
    assert sc.score > 1000


def test_mashing_every_tier():
    random.seed(5)
    for n in (1, 13, 27, 44, 58, 66, 79, 93, 118, 147, 176, 199):
        app, sc = _scene(1, n)
        sc.lives = 99
        _run(app, sc, 60 * 12, _mash(n))
        assert sc.ending is None


def test_tree_parts():
    from mochi_arcade.games.tower_tabby import Player, Seg
    app, sc = _scene(1, 31)            # BOUNCE HOUSE: beds
    _play(sc)
    bed = next(s for s in sc.segs if s.kind == "bed" and s.k == 0)
    x = (bed.x0 + bed.x1) / 2
    sc.p = Player(x, bed.y(x) - 2)
    sc.p.ground = None
    top = sc.p.y
    for _ in range(40):
        _run(app, sc, 1)
        top = min(top, sc.p.y)
    assert top < bed.y(x) - 36, "a spring bed bounces Mikan up a whole level"
    app, sc = _scene(1, 41)            # flimsy boxes
    _play(sc)
    box = next(s for s in sc.segs if s.kind == "box")
    x = (box.x0 + box.x1) / 2
    sc.p = Player(x, box.y(x))
    sc.p.ground = box
    sc.p.inv = 9
    _run(app, sc, 40)
    assert box.gone > 0, "a box collapses when Mikan stands on it"
    _run(app, sc, 60 * 4)
    assert box.gone <= 0, "and comes back"
    belt_st = next(n for n, s in enumerate(D.generate(), 1) if any("<" in r or ">" in r for r in s["lv"][1:]))
    app, sc = _scene(1, belt_st)
    _play(sc)
    belt = next(s for s in sc.segs if s.kind == "belt")
    x = (belt.x0 + belt.x1) / 2
    sc.p = Player(x, belt.y(x))
    sc.p.ground = belt
    sc.p.inv = 9
    _run(app, sc, 20)
    assert (sc.p.x - x) * belt.belt > 5, "conveyors carry Mikan"
    app, sc = _scene(1, 61)            # box tunnels
    _play(sc)
    (x1, k1), (x2, k2) = sc.warps[0]
    sc.p = Player(x1, sc.surface(k1, x1))
    sc.p.ground = sc.support(x1, sc.p.y - 2, sc.p.y + 2)[1]
    sc.p.inv = 9
    _run(app, sc, 3, lambda f: {"down"} if f % 2 == 0 else set())
    _run(app, sc, 40)
    assert abs(sc.p.x - x2) < 4 and abs(sc.p.y - sc.surface(k2, x2)) < 3, "tunnels pair up"
    app, sc = _scene(1, 11)            # ropes: jump + up to grab
    _play(sc)
    rope = next(po for po in sc.posts if po.rope)
    sc.p = Player(rope.x, sc.surface(rope.k, rope.x))
    sc.p.ground = sc.support(rope.x, sc.p.y - 2, sc.p.y + 2)[1]
    sc.p.inv = 9
    _run(app, sc, 2, lambda f: {"a"})
    _run(app, sc, 120, lambda f: {"up", "a"})
    assert abs(sc.p.y - rope.top) < 2, "Mikan climbs the rope to the shelf above"
    app, sc = _scene(1, 21)            # hammocks move and carry Mikan
    _play(sc)
    hm = sc.hams[0]
    x0 = hm.x
    _run(app, sc, 30)
    assert hm.x != x0
    sc.p = Player(hm.x + 16, hm.y)
    sc.p.ground = hm
    sc.p.inv = 9
    px = sc.p.x - hm.x
    _run(app, sc, 30)
    assert sc.p.ground is hm and abs((sc.p.x - hm.x) - px) < 1.5
    assert isinstance(sc.segs[0], Seg)


def test_every_hazard_kind():
    from mochi_arcade.games.tower_tabby import Haz
    random.seed(7)
    app, sc = _scene(1, 99)
    _play(sc)
    sc.lives = 99
    for kind in D.DROPS:
        sc.spawn_drop(kind, 160, 30)
    for h in [Haz("mouse", 100, 150, 5), Haz("bot", 120, 120, 5), Haz("dust", 200, 60, 4)]:
        h.life = 10.0
        sc.hz.append(h)
    sc.moth_t = 1.0
    sc.moth_left = 0.0
    _run(app, sc, 60 * 6, _mash(3))
    kinds = {h.kind for h in sc.hz}
    assert sc.ending is None and "moth" in kinds | {"moth"}
    # pouncing catches things, the wand bats them, milk puts them to sleep
    app, sc = _scene(1, 2)
    _play(sc)
    _run(app, sc, 2)
    p = sc.p
    p.inv = 9.0
    s0 = sc.score
    h = sc.spawn_drop("yarn", p.x + 4, p.y - 6)
    p.pounce = True
    _run(app, sc, 2)
    assert h.dead and sc.score > s0 and sc.bops == 1
    sc.wand_t = 5.0
    h = sc.spawn_drop("cone", p.x + 2, p.y - 8)
    _run(app, sc, 2)
    assert h.batted or h.dead
    sc.milk_t = 3.0
    h = sc.spawn_drop("yarn", p.x + 30, p.y - 6)
    y0 = h.y
    _run(app, sc, 20)
    assert h.y == y0, "warm milk: everything naps"


def test_items_and_kittens():
    from mochi_arcade.games.tower_tabby import Kitten, Pickup
    app, sc = _scene(1)
    _play(sc)
    _run(app, sc, 2)
    p = sc.p
    s0, lives0 = sc.score, sc.lives
    for kind in ("fish", "gfish", "coin", "wand", "bell", "milk", "nip", "heart"):
        sc.items.append(Pickup(kind, p.x, p.y - 6, 100))
        _run(app, sc, 3)
    assert sc.score > s0 + 5000 and sc.lives == lives0 + 1 and sc.shield
    assert sc.wand_t > 0 and sc.nip_t > 0 and sc.milk_t > 0
    sc.kits.append(Kitten(p.x, p.y, 1))
    _run(app, sc, 3)
    assert sc.kits[-1].follow and sc.kittens_saved >= 1


def test_bonus_stages():
    from mochi_arcade.games.tower_tabby import gif_bot
    for n in (5, 15):
        random.seed(n)
        app, sc = _scene(1, n)
        assert sc.kind == "bonus"
        bot = gif_bot(sc)
        for _ in range(60 * 30):
            _run(app, sc, 1, bot)
            if sc.state == "timeup":
                break
        assert sc.state == "timeup" and sc.bonus_n > 30, (sc.state, sc.bonus_n)
        assert sc.bonus_got > 0, (n, sc.bonus_got)
        _run(app, sc, 60 * 6, lambda f: {"a"} if f % 2 == 0 else set())
        assert sc.stage == n + 1, (n, sc.stage, sc.state)


def test_every_boss_and_pattern():
    random.seed(11)
    pats = ("swoop", "drop", "feathers", "sparks", "beam", "mice", "spit", "dash", "suck", "slam", "hop", "spray",
            "jet", "trace", "roll", "toss")
    for n in (10, 20, 30, 40, 50, 60, 100, 200):
        app, sc = _scene(1, n)
        sc.lives = 99
        sc.boss.hp = sc.boss.maxhp = 10 ** 6
        _run(app, sc, 220)
        assert sc.state == "play" and sc.boss.mode != "enter"
        for pat in pats:
            b = sc.boss
            b.daze, b.air = 0.0, False
            b.mode, b.mode_t, b.step, b.count, b.timer = pat, 0.0, 0, 3, 0.0
            _run(app, sc, 170, _mash(n))
        hp0 = sc.boss.hp
        sc.boss.hurt(sc, 1)
        assert sc.boss.hp == hp0 - 1


def test_pounce_a_dazed_boss():
    app, sc = _scene(1, 20)
    _run(app, sc, 220)
    b = sc.boss
    b.mode, b.daze = "dazed", 2.0
    p = sc.p
    p.x, p.y = b.x - b.hw - 2, b.y + b.hh - 6
    p.ground, p.pounce, p.vy, p.vx = None, True, 0.0, 0.0
    p.inv = 0.0
    hp0 = b.hp
    _run(app, sc, 1)
    assert b.hp == hp0 - 3, (hp0, b.hp)


def test_boss_defeat_flow_and_upgrade_pick():
    app, sc = _scene(1, 10)
    _run(app, sc, 220)
    sc.boss.hp = 1
    sc.boss.hurt(sc, 1)
    assert sc.state == "bossdown"
    _run(app, sc, 60 * 12)
    assert sc.state == "picks" and sc.overlay is not None, sc.state
    _run(app, sc, 40, lambda f: {"a"} if f % 2 == 0 else set())
    assert sc.stage == 11 and sum(sc.ups.values()) == 1, (sc.stage, sc.ups)


def test_head_start_goal_and_tally():
    app, sc = _scene(51)
    sc.state, sc.picks = "picks", 5
    for _ in range(6):
        _run(app, sc, 40, lambda f: {"a"} if f % 2 == 0 else set())
    assert sum(sc.ups.values()) == 5, sc.ups
    app, sc = _scene(1)
    _run(app, sc, 130)
    gx, gy = sc.goal
    sc.p.x, sc.p.y = gx, gy
    sc.p.ground = sc.support(gx, gy - 2, gy + 2)[1]
    _run(app, sc, 3)
    assert sc.state == "clear"
    _run(app, sc, 200)
    assert sc.state == "tally" and sc.tally, sc.state
    _run(app, sc, 400)
    assert sc.stage == 2


def test_lives_and_game_over():
    app, sc = _scene(1)
    _play(sc)
    sc.lives = 1
    sc.p.inv = 0
    sc.hurt()
    assert sc.state == "dead"
    _run(app, sc, 120)
    assert sc.ending is not None and sc.end_args[0] is False


def test_final_victory():
    app, sc = _scene(1, 200)
    _run(app, sc, 220)
    sc.boss.hp = 1
    sc.boss.hurt(sc, 1)
    _run(app, sc, 60 * 12)
    _run(app, sc, 40, lambda f: {"a"} if f % 2 == 0 else set())
    assert sc.state == "won" and sc.ending is not None and sc.end_args[0] is True, (sc.state, sc.end_args)


def test_preview_and_registry():
    import pygame
    from mochi_arcade.games import GAMES, tower_tabby
    info = next(g for g in GAMES if g.id == "tower_tabby")
    assert info.load() is tower_tabby.TowerTabby
    s = pygame.Surface((112, 74))
    for t in (0.0, 0.7, 3.3):
        tower_tabby.preview(s, t)
    assert ("start", "START STAGE", "checkpoints", 1) in tower_tabby.OPTIONS


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        fn()
        print(f"{name:42} ok", flush=True)
    print("ALL TOWER TABBY TESTS OK")
