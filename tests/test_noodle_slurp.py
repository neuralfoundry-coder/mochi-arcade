"""NOODLE SLURP campaign checks (headless):
- all 200 stages generate deterministically and pass the validator (spawn safe, everything reachable, no dead ends,
  ice/conveyor/portal exits open, hazards clear of the spawn, enough stars, bosses and bonus stages in place)
- a BFS bot plays stage 1, a bonus stage, every boss design and a few late stages for a while without errors,
  and clears the early stages; the tally -> upgrade pick -> next stage flow works; endless modes run.
usage: python tests/test_noodle_slurp.py [shot_dir]
"""
import collections
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="noodle-test-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else None
if SHOTS:
    os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A  # noqa: E402
from mochi_arcade.arcade import is_boss, is_bonus  # noqa: E402
from mochi_arcade.games import GAMES  # noqa: E402
from mochi_arcade.games import noodle_slurp as G  # noqa: E402
from mochi_arcade.games import noodle_slurp_stages as NS  # noqa: E402

INFO = next(g for g in GAMES if g.id == "noodle_slurp")

# ---------------------------------------------------------------- data checks
stages = G.STAGE_DATA
assert len(stages) == 200
again = NS.build_all()
assert [s["map"] for s in again] == [s["map"] for s in stages], "stage generation must be deterministic"
problems = {s["n"]: NS.validate(s) for s in stages}
bad = {n: p for n, p in problems.items() if p}
assert not bad, bad
for s in stages:
    n = s["n"]
    assert s["kind"] == ("boss" if is_boss(n) else "bonus" if is_bonus(n) else "stage"), n
    assert 0 <= s["theme"] < len(NS.THEMES)
    if s["kind"] == "boss":
        assert s["boss"]["hp"] >= 3 and s["boss"]["pool"], n
    if s["goal"] == "feast":
        assert 20 <= s["map"].count("d") <= 90, (n, s["map"].count("d"))
boss_kinds = collections.Counter(s["boss"]["kind"] for s in stages if s["kind"] == "boss")
assert len(boss_kinds) >= 5, boss_kinds
assert stages[199]["boss"]["kind"] == "bao" and stages[99]["boss"]["kind"] == "bao"
goals = collections.Counter(s["goal"] for s in stages)
assert all(goals[g] >= 8 for g in ("eat", "stars", "length", "survive", "feast", "rush")), goals
for feat, t0 in NS.UNLOCK.items():
    first = 10 * t0 + 1
    for s in stages[:first - 1]:
        m = s["map"]
        if feat == "portals":
            assert "1" not in m, s["n"]
        if feat == "rollers":
            assert not s["rollers"], s["n"]
        if feat == "vents":
            assert not s["vents"], s["n"]
        if feat == "ice":
            assert "~" not in m, s["n"]
        if feat == "arrows":
            assert not any(ch in m for ch in "<>^v"), s["n"]
        if feat == "gates":
            assert "G" not in m, s["n"]
steps = [s["step"] for s in stages if s["kind"] == "stage"]
assert steps[0] > steps[-1], "the campaign should speed up"
print("data OK:", dict(goals), dict(boss_kinds))


# ---------------------------------------------------------------- headless driver + bot
def make_app():
    app = A.App(windowed=True, mute=True, test_frames=1)
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    return app


bot = G.autopilot


def run(scene, app, seconds, stop=None, keys=None, shot=None, shot_at=None):
    """Drive the scene at 60 fps without the real-time clock. Returns frames run."""
    held = set()
    frames = int(seconds * 60)
    for f in range(frames):
        app.input.begin()
        want = keys(f) if keys else bot(scene)
        app.input.pressed = set(want) - held
        app.input.released = held - set(want)
        app.input.held = set(want)
        held = set(want)
        cur = app.scene or scene
        cur.t += 1 / 60
        cur.update(1 / 60)
        if f % 4 == 0 or (shot_at is not None and f == shot_at):
            cur.draw(app.canvas)
        if shot and shot_at is not None and f == shot_at and SHOTS:
            pygame.image.save(pygame.transform.scale(app.canvas, (W3, H3)), os.path.join(SHOTS, shot))
        if stop and stop(cur):
            if shot and SHOTS and (shot_at is None or f < shot_at):
                cur.draw(app.canvas)
                pygame.image.save(pygame.transform.scale(app.canvas, (W3, H3)), os.path.join(SHOTS, shot))
            return f
    return frames


W3, H3 = 960, 600


def campaign(app, start, **kw):
    opts = {"mode": "campaign", "start": start, "speed": "normal"}
    opts.update(kw)
    sc = G.NoodleSlurp(app, INFO, opts)
    app.scenes = [sc]
    return sc


app = make_app()
random.seed(7)

# stage 1: the bot should clear it
sc = campaign(app, 1)
run(sc, app, 0.5, shot="stage1-intro.png", shot_at=20)
n = run(sc, app, 90, stop=lambda s: s.state in ("clear", "tally"), shot="stage1-play.png", shot_at=900)
assert sc.state in ("clear", "tally"), (sc.state, sc.eaten_stage)
run(sc, app, 4, stop=lambda s: s.state == "tally" and s.tally_i >= 2, shot="stage1-tally.png", shot_at=200)
run(sc, app, 8, stop=lambda s: s.stage_n == 2)
assert sc.stage_n == 2 and sc.state == "intro"
print("stage 1 cleared in", round(n / 60, 1), "s; score", sc.score)

# early campaign: the bot clears several stages in a row (checks winnability end to end)
cleared = 0
sc = campaign(app, 1)
for _ in range(4):
    start = sc.stage_n
    run(sc, app, 120, stop=lambda s, k=start: s.stage_n > k or s.ending is not None)
    if sc.stage_n > start:
        cleared += 1
print("bot cleared", cleared, "of the first 4 stages; lives left", sc.lives)
assert cleared >= 2

# bonus stage
sc = campaign(app, 5)
run(sc, app, 2.5)
run(sc, app, 8, shot="bonus-feast.png", shot_at=300)
assert sc.kind == "bonus"
run(sc, app, 30, stop=lambda s: s.state in ("tally", "pick") or s.overlay is not None)
run(sc, app, 6, stop=lambda s: s.overlay is not None, shot="upgrade-cards.png", shot_at=200)
assert sc.overlay is not None, sc.state
run(sc, app, 1.0, keys=lambda f: {"a"} if f == 40 else set())
assert sc.overlay is None and sc.stage_n == 6 and sum(sc.up.values()) == 1, (sc.stage_n, sc.up)
print("bonus stage + upgrade pick OK:", sc.up)

sc = campaign(app, 15)
run(sc, app, 2.5)
run(sc, app, 8, shot="bonus-rush.png", shot_at=240)

# every boss design, early and late
for n, shot in ((10, "boss-crab.png"), (20, "boss-teapot.png"), (30, "boss-sushi.png"), (40, "boss-golem.png"),
                (50, "boss-ghost.png"), (100, "boss-bao.png"), (170, "boss-crab-late.png"), (200, "boss-final.png")):
    sc = campaign(app, n)
    run(sc, app, 1.0, shot="warning.png" if n == 10 else None, shot_at=50)
    run(sc, app, 3.5)
    assert sc.state == "play" or sc.state in ("dead", "ready"), sc.state
    run(sc, app, 25, stop=lambda s: s.ending is not None, shot=shot, shot_at=500)
    print(f"boss {n} {sc.boss.kind}: hp {sc.boss.hp}/{sc.boss.maxhp} state {sc.state} lives {sc.lives}")

# force a boss defeat to run the BOSS DOWN -> golden feast -> tally -> upgrade chain
sc = campaign(app, 10)
run(sc, app, 4.5)
sc.boss.hp = 1
sc.boss_hit(sc.boss.cells()[0])
assert sc.state == "bossdown"
run(sc, app, 1.2, shot="boss-down.png", shot_at=40)
run(sc, app, 12, stop=lambda s: s.overlay is not None)
assert sc.overlay is not None, sc.state
run(sc, app, 1.0, keys=lambda f: {"a"} if f == 40 else set())
assert sc.stage_n == 11, sc.stage_n
print("boss defeat chain OK")

# later tiers: hazards, themes
for n, shot in ((23, "tier2-portals.png"), (34, "tier3-survive.png"), (57, "tier5-ice.png"), (62, "tier6-vents.png"),
                (78, "tier7-arrows.png"), (114, "tier11.png"), (143, "tier14.png"), (187, "tier18.png"),
                (199, "tier19.png")):
    sc = campaign(app, n)
    run(sc, app, 1.0, shot=shot.replace(".png", "-intro.png") if n in (23, 114) else None, shot_at=40)
    run(sc, app, 30, stop=lambda s: s.ending is not None or s.state in ("clear", "tally"), shot=shot, shot_at=400)
    print(f"stage {n}: state {sc.state} eaten {sc.eaten_stage} stars {len(sc.stars)} lives {sc.lives}")

# squeeze stage runs past its wall closings
sq = [s["n"] for s in stages if s["squeeze"]]
sc = campaign(app, sq[0])
run(sc, app, 26, shot="squeeze.png", shot_at=1300)
print("squeeze stage", sq[0], "rings closed:", sc.squeezed)

# endless modes
for mode in ("classic", "wrap"):
    sc = G.NoodleSlurp(app, INFO, {"mode": mode, "start": 1, "speed": "fast"})
    app.scenes = [sc]
    run(sc, app, 40, stop=lambda s: s.ending is not None, shot=f"endless-{mode}.png", shot_at=1500)
    print(f"{mode}: length {len(sc.body)} eaten {sc.total_eaten} score {sc.score}")

# preview for the game carousel
surf = pygame.Surface((120, 70))
for k in range(10):
    G.preview(surf, k * 0.37)
print("ALL OK" + (f" - shots in {SHOTS}" if SHOTS else ""))
