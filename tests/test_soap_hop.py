"""SOAP HOP campaign tests (headless): all 200 stages generate deterministically and validate, and the game
runs stage 1, bonus stages, every boss (all patterns), the clear tally, upgrade picks and the final victory.
usage: python tests/test_soap_hop.py   (also works under pytest)"""
import json
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packaging"))
_TMP = tempfile.mkdtemp(prefix="soap-test-")
os.environ["XDG_DATA_HOME"] = _TMP
os.environ["XDG_CACHE_HOME"] = _TMP

from mochi_arcade.arcade import STAGES, is_bonus, is_boss, tier  # noqa: E402
from mochi_arcade.games import soap_hop_data as D  # noqa: E402

ORIGINAL = {lv["name"] for lv in D.LEVELS}


# ----------------------------------------------------------------------------- data
def test_campaign_shape_and_determinism():
    a, b = D.generate(), D.generate()
    assert a == b, "stage generation must be deterministic"
    assert len(a) == STAGES == 200
    for n, st in enumerate(a, 1):
        want = "boss" if is_boss(n) else "bonus" if is_bonus(n) else "normal"
        assert st["k"] == want, (n, st["k"])
        assert st["th"] == tier(n), n
        assert len(st["map"]) == D.ROWS and all(len(r) == D.COLS for r in st["map"]), n
        assert set("".join(st["map"])) <= set("#=."), n


def test_every_stage_is_winnable():
    for n, st in enumerate(D.generate(), 1):
        m, start = st["map"], tuple(st["p"])
        ens = [(k, c, r) for k, c, r, _ in st["en"]]
        strict = st["tpl"] not in ORIGINAL     # the hand-made originals rely on bubble bouncing in places
        err = D.validate(m, start, ens, strict=strict)
        assert err is None, f"stage {n} ({st['nm']}): {err}\n{D.ascii(m, start, st['en'])}"
        if st["k"] == "normal":
            assert 4 <= len(ens) <= 10, (n, len(ens))
        else:
            assert not ens


def test_difficulty_curve_and_roster():
    stages = D.generate()
    seen_new = {}
    avg = []
    for t in range(20):
        normal = [stages[n - 1] for n in range(t * 10 + 1, t * 10 + 11) if stages[n - 1]["k"] == "normal"]
        avg.append(sum(len(s["en"]) for s in normal) / len(normal))
        for s in normal:
            for k, *_ in s["en"]:
                assert D.ENEMIES[k][1] <= t, f"{k} appears before its tier in tier {t}"
            if s["new"]:
                seen_new.setdefault(s["new"], t)
    assert avg[-1] > avg[1] + 2, avg
    assert all(avg[i + 3] >= avg[i] for i in range(1, 17)), avg     # tier 0 = the hand-made originals
    for k, (_, t0, _, _) in D.ENEMIES.items():
        if t0 > 0:
            assert seen_new.get(k) == t0, (k, seen_new)
    mods = {m for s in stages for m in s["mods"]}
    assert mods == set(D.MODS), mods
    assert len({s["tpl"] for s in stages if s["k"] == "normal"}) >= 28


def test_bosses():
    stages = D.generate()
    bosses = [stages[n - 1] for n in range(10, 201, 10)]
    assert {b["boss"] for b in bosses} == set(D.BOSSES), "all six bosses appear"
    assert stages[99]["boss"] == stages[199]["boss"] == "grime"
    last = {}
    for b in bosses:
        assert b["hp"] > last.get(b["boss"], 0), "a boss gets tougher every time it comes back"
        last[b["boss"]] = b["hp"]
        assert b["pat"], b
    assert any(len(set(b["pat"]) - set(D.BOSSES[b["boss"]][2])) for b in bosses), "late bosses borrow patterns"


def test_export():
    from mochi_arcade.games import soap_hop
    ex = soap_hop.EXPORT
    text = json.dumps(ex, separators=(",", ":"))
    assert len(text) < 160_000, len(text)
    gen = D.generate()
    for st, g in zip(ex["stages"], gen):
        assert [D.unrle(r) for r in st["map"]] == g["map"] and st["nm"] == g["nm"]
        assert len(st["nm"]) <= 20, st["nm"]
    assert len(ex["themes"]) == 20


def test_upgrades():
    from mochi_arcade.games.soap_hop import UPGRADES
    assert len(UPGRADES) >= 6
    assert len({u.id for u in UPGRADES}) == len(UPGRADES)
    for u in UPGRADES:
        assert len(u.name) <= 14, u.name
        assert all(len(line) <= 14 for line in u.desc.split("|")), u.desc


# ----------------------------------------------------------------------------- simulation
_APP = []


def _scene(start=1, stage=None):
    from mochi_arcade import app as A
    from mochi_arcade.games import GAMES, soap_hop
    if not _APP:
        app = A.App(windowed=True, mute=True, test_frames=1)
        if not app.store.profiles:
            app.store.create("TESTER", "pink")
        app.profile = app.store.last()
        _APP.append(app)
    app = _APP[0]
    info = next(g for g in GAMES if g.id == "soap_hop")
    sc = soap_hop.SoapHop(app, info, {"difficulty": "normal", "start": start})
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
            state.update(k for k in ("left", "right", "a", "b", "b") if rnd.random() < 0.3)
        return set(state)
    return f


def test_play_stage_one_with_bot():
    import record_gifs
    app, sc = _scene(1)
    sc.lives = 50
    _run(app, sc, 60 * 40, record_gifs.soap_bot(sc))
    assert sc.score > 0 and (sc.stage > 1 or len(sc.enemies) < 5), (sc.stage, sc.score, len(sc.enemies))


def test_bonus_stages():
    for n in (5, 15):
        app, sc = _scene(1, n)
        assert sc.kind == "bonus"
        mash = _mash(n)
        for _ in range(60 * 30):
            _run(app, sc, 1, mash)
            if sc.state == "timeup":
                break
        assert sc.state == "timeup" and sc.bonus_n > 40, (sc.state, sc.bonus_n)
        _run(app, sc, 60 * 6, lambda f: {"a"} if f % 2 == 0 else set())
        assert sc.stage == n + 1, (n, sc.stage, sc.state)


def test_every_boss_and_pattern():
    for n in (10, 20, 30, 40, 50, 100, 190, 200):
        app, sc = _scene(1, n)
        sc.lives = 99
        sc.boss.hp = sc.boss.maxhp = 10 ** 6      # keep it alive while every pattern is forced in turn
        _run(app, sc, 220)
        assert sc.state == "play" and sc.boss.mode != "enter"
        for pat in ("hop", "slam", "walk", "splash", "spit", "minions", "drift", "inhale", "puff", "rain", "bolt",
                    "slither", "lunge"):
            b = sc.boss
            b.mode, b.mode_t, b.step, b.count = pat, 0.0, 0, 2
            _run(app, sc, 150, _mash(n))
        hp0 = sc.boss.hp
        sc.boss.hurt(sc, 1)
        assert sc.boss.hp == hp0 - 1 or sc.boss.mode == "dying"


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


def test_head_start_and_tally():
    app, sc = _scene(51)
    sc.state, sc.picks = "picks", 5
    for _ in range(6):
        _run(app, sc, 40, lambda f: {"a"} if f % 2 == 0 else set())
    assert sum(sc.ups.values()) == 5, sc.ups
    app, sc = _scene(1)
    _run(app, sc, 130)
    sc.enemies = []
    _run(app, sc, 220)
    assert sc.state == "tally" and sc.tally, sc.state
    _run(app, sc, 300)
    assert sc.stage == 2


def test_final_victory():
    app, sc = _scene(1, 200)
    _run(app, sc, 220)
    sc.boss.hp = 1
    sc.boss.hurt(sc, 1)
    _run(app, sc, 60 * 12)
    _run(app, sc, 40, lambda f: {"a"} if f % 2 == 0 else set())
    assert sc.state == "won" and sc.ending is not None and sc.end_args[0] is True, (sc.state, sc.end_args)


def test_items_and_letters():
    from mochi_arcade.games.soap_hop import Item
    app, sc = _scene(1)
    _run(app, sc, 130)
    s0, lives0 = sc.score, sc.lives
    p = sc.player
    for kind in ("chest", "soda", "clock", "gem", "cake", "heart", "shield"):
        sc.items.append(Item(p.x, p.y, kind))
        _run(app, sc, 3)
    assert sc.score > s0 + 5000 and sc.lives == lives0 + 1 and sc.shield
    sc.letters = [True, True, True, True, False]
    sc.spawn_letter()
    b = sc.bubbles[-1]
    b.x, b.y = p.cx, p.cy
    _run(app, sc, 3)
    assert sc.letters == [False] * 5 and sc.lives == lives0 + 2


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        fn()
        print(f"{name:42} ok", flush=True)
    print("ALL SOAP HOP TESTS OK")
