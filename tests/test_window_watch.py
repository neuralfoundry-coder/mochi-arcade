"""WINDOW WATCH campaign checks: all 200 stages generate deterministically and validate (well-formed events,
things only after their introduction, enough paw energy to defend every stage), then headless bot runs of a
normal stage, every bonus kind, every boss design and some late stages, plus the touch-tap swat.
usage: python tests/test_window_watch.py [shot_dir]"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-ww-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A, music, sprites  # noqa: E402
from mochi_arcade.arcade import STAGES, is_bonus, is_boss  # noqa: E402
from mochi_arcade.games import GAMES, window_watch as WW  # noqa: E402
from mochi_arcade.games import window_watch_stages as S  # noqa: E402

# ---------------------------------------------------------------- campaign data
camp = S.build_campaign()
assert len(camp) == STAGES == 200
assert camp == S.CAMPAIGN, "generation must be deterministic"
assert json.loads(json.dumps(WW.EXPORT))["stages"] == camp, "EXPORT must be plain JSON and match the campaign"
kinds = {"normal": 0, "boss": 0, "bonus": 0}
boss_kinds, bonus_kinds, names = set(), set(), set()
first = {}
for st in camp:
    n = st["n"]
    errs = S.validate(st)
    assert not errs, (n, st["name"], errs)
    kinds[st["kind"]] += 1
    assert st["tier"] == (n - 1) // 10
    assert (st["kind"] == "boss") == is_boss(n) and (st["kind"] == "bonus") == is_bonus(n), n
    assert 0 <= st["theme"] < len(S.THEMES)
    names.add(st["name"])
    if st["kind"] == "boss":
        b = st["boss"]
        boss_kinds.add(b["kind"])
        assert b["hp"] > 0 and b["rate"] > 0 and b["kind"] in S.BOSS_KINDS and b["attacks"], b
    if st["kind"] == "bonus":
        bonus_kinds.add(st["bonus"])
        assert st["time"] > 0 and len(st["events"]) >= 25, (n, len(st["events"]))
    if st["kind"] == "normal":
        for e in st["events"]:
            first.setdefault(e[1], n)
        if st["wind"]:
            first.setdefault("wind", n)
assert kinds == {"normal": 160, "boss": 20, "bonus": 20}, kinds
assert len(boss_kinds) >= 6, boss_kinds
assert bonus_kinds == {"treats", "bubbles", "fireflies"}, bonus_kinds
assert len(names) >= 150, len(names)
for k, n in S.UNLOCK.items():
    assert first[k] == n, (k, first[k], n)       # every thing shows up exactly from its introduction stage
assert first["wind"] == 61, first["wind"]
assert first["cap"] == 2
# difficulty goes up: faster, busier stages and tougher bosses
harm = lambda st: sum(1 for e in st["events"] if S.KINDS[e[1]][4])  # noqa: E731
assert camp[190]["speed"] > camp[0]["speed"] * 1.7
assert sum(harm(st) for st in camp[180:189]) > 2 * sum(harm(st) for st in camp[0:9])
assert camp[199]["boss"]["hp"] > camp[9]["boss"]["hp"] * 3
assert camp[199]["boss"]["kind"] == "king"
assert all(camp[n - 1]["new"] for n in S.UNLOCK.values() if n > 1)
# art and songs are registered for the exporter
for name in ("ww_drop", "ww_leaf", "ww_crow", "ww_paw", "ww_pawicon", "ww_fish"):
    assert name in sprites.ART, name
for name in ("ww_sill", "ww_moon"):
    assert name in music.SONGS, name
for th in S.THEMES:
    assert th[5] in music.SONGS
print(f"campaign OK: {kinds}, {len(names)} names, bosses {sorted(boss_kinds)}")


# ---------------------------------------------------------------- headless play
info = next(g for g in GAMES if g.id == "window_watch")


def play(stage, frames, levels=None, name=None, taps=None):
    """Run the game headless as fast as possible with the autopilot, drawing every few frames."""
    ref = [None]
    stats = {"caught": 0, "boss_hp": None, "stages": set(), "splash": 0, "chain": 0}
    app = A.App(windowed=True, mute=True, test_frames=frames, script=lambda f: WW.autopilot(ref[0], f))
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
        if taps and f in taps:
            sc.tap(*taps[f])
        sc.t += 1 / 60
        sc.update(1 / 60)
        if f % 3 == 0:
            sc.draw(app.canvas)
        stats["stages"].add(sc.n)
        if sc.n == stage:
            stats["caught"] = max(stats["caught"], sc.caught)
            stats["chain"] = max(stats["chain"], sc.best_chain)
            stats["splash"] += int(sc.splashed)
            if sc.boss:
                stats["boss_hp"] = sc.boss.hp
    sc.draw(app.canvas)
    app.screenshot(os.path.join(SHOTS, (name or f"ww-stage{stage}") + ".png"))
    pygame.quit()
    return sc, stats


sc, stats = play(1, 3000)
assert sc.score > 0 and stats["caught"] > 5, stats
assert 2 in stats["stages"], "the bot should clear stage 1"
print(f"stage 1: reached stage {sc.n}, score {sc.score}, caught {stats['caught']}")
for n in (5, 15, 25):
    sc, stats = play(n, 1700, name=f"ww-bonus{n}")
    assert stats["caught"] > 10 and n + 1 in stats["stages"], (n, stats)
    print(f"bonus {n} ({camp[n - 1]['bonus']}): caught {stats['caught']}, best chain {stats['chain']} -> stage {sc.n}")
ups = {"paw": 2, "quick": 2, "stamina": 2, "chain": 2}
for n in (10, 20, 30, 40, 50, 60, 120, 200):
    sc, stats = play(n, 2400, ups, name=f"ww-boss{n}")
    b = camp[n - 1]["boss"]
    print(f"boss stage {n} ({b['name']}): hp {stats['boss_hp']}/{b['hp']} -> stage {sc.n} {sc.state}")
    assert stats["boss_hp"] is None or stats["boss_hp"] < b["hp"], "the boss should take damage"
for n in (41, 61, 91, 111, 121, 131, 199):
    sc, stats = play(n, 1500, {"paw": 3, "quick": 3, "stamina": 2, "chain": 2, "whisker": 2, "glass": 1})
    print(f"stage {n} ({camp[n - 1]['name']}): caught {stats['caught']}, chain {stats['chain']} -> stage {sc.n} {sc.state}")
    assert stats["caught"] > 0
# touch: a tap swats right where it lands (the iOS port routes onTap here)
sc, stats = play(1, 400, taps={200: (100.0, 80.0), 260: (220.0, 120.0)}, name="ww-taps")
sc, _ = play(1, 2)
sc.state = "play"
e0 = len(sc.rings), sc.energy
sc.tap(100.0, 80.0)
assert len(sc.rings) == e0[0] + 1 and (sc.rings[-1].x, sc.rings[-1].y) == (100.0, 80.0) and sc.energy == e0[1] - 1
# every upgrade can be taken
for u in WW.UPGRADES:
    for _ in range(u.max):
        sc.on_pick(u.id)
assert sc.emax() == 7 and sc.meow_max() == 6 and sc.lives >= 8
print("shots in", SHOTS)
print("WINDOW WATCH OK")
