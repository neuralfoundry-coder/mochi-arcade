"""YARN WEAVER checks: all 200 stages generate and validate (one connected rug, KUMO starts on yarn, hazards
introduced room by room, five boss designs), every hidden picture paints, the claim rules work (smaller pockets
are claimed with whatever is inside, the boss keeps its own piece), then headless bot runs of normal, bonus and
boss stages.
usage: MOCHI_FAST=1 python tests/test_yarn_weaver.py [shot_dir]"""
import json
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-yw-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A  # noqa: E402
from mochi_arcade.arcade import STAGES, is_boss, is_bonus  # noqa: E402
from mochi_arcade.games import GAMES  # noqa: E402
from mochi_arcade.games import yarn_weaver as YW  # noqa: E402
from mochi_arcade.games import yarn_weaver_art as ART  # noqa: E402
from mochi_arcade.games import yarn_weaver_stages as S  # noqa: E402

# ---------------------------------------------------------------- campaign data
camp = S.build_campaign()
assert len(camp) == STAGES == 200
assert json.loads(json.dumps(YW.EXPORT))["stages"] == camp, "EXPORT must be plain JSON and match the campaign"
assert camp == S.CAMPAIGN, "generation must be deterministic"
kinds = {"normal": 0, "boss": 0, "bonus": 0}
bosses, names, first = set(), set(), {}
for st in camp:
    n = st["n"]
    errs = S.validate(st)
    assert not errs, (n, errs)
    kinds[st["kind"]] += 1
    assert st["tier"] == (n - 1) // 10
    assert (st["kind"] == "boss") == is_boss(n) and (st["kind"] == "bonus") == is_bonus(n), n
    names.add(st["pic"]["name"])
    if st["kind"] == "boss":
        bosses.add(st["boss"]["kind"])
        assert st["boss"]["hp"] > 0 and st["boss"]["rate"] > 0
    if st["kind"] == "normal":
        for key in ("moths", "minis", "nose", "hunters", "storm", "knots"):
            if st[key]:
                first.setdefault(key, st["tier"])
        if st["shapes"]:
            first.setdefault("furniture", st["tier"])
        if st["fluffs"] >= 2:
            first.setdefault("twin", st["tier"])
assert kinds == {"normal": 160, "boss": 20, "bonus": 20}, kinds
assert len(bosses) >= 5, bosses
assert len(names) >= 190, len(names)
assert first == {"furniture": 1, "twin": 2, "moths": 3, "minis": 4, "nose": 5, "hunters": 6, "storm": 7,
                 "knots": 8}, first
assert camp[190]["speed"] > camp[0]["speed"] and camp[199]["boss"]["hp"] > camp[9]["boss"]["hp"]
assert camp[188]["target"] > camp[0]["target"]
assert camp[199]["boss"]["name"] == "GRAND FUZZ" and len(camp[199]["boss"]["extra"]) >= 3
# every hidden picture paints (and its golden version)
pygame.init()
surf = pygame.Surface((ART.PW, ART.PH))
for st in camp:
    ART.draw_picture(surf, st["pic"], golden=st["n"] % 17 == 0)
print(f"campaign OK: {kinds}, {len(names)} cats to meet, bosses {sorted(bosses)}")

info = next(g for g in GAMES if g.id == "yarn_weaver")


def make(stage=1, frames=1, script=None, levels=None):
    app = A.App(windowed=True, mute=True, test_frames=frames, script=script or (lambda f: set()))
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    sc = info.load()(app, info, {"difficulty": "normal", "start": 1})
    sc.levels.update(levels or {})
    if stage != 1:
        sc.start_stage(stage)
    app.apply_settings()
    app.scenes = [sc]
    sc.enter()
    return app, sc


# ---------------------------------------------------------------- claim rules
app, sc = make(1)
sc.state = "play"
GW, GH = S.GW, S.GH
sc.balls = []
fl = sc.spawn_ball("fluff", 250.0, 40.0)        # far up-right
pocket = sc.spawn_ball("fluff", 21.0, 161.0)    # will be trapped in a small pocket bottom-left
pocket.vx = pocket.vy = 0.0
pocket.speed = 0.0
sc.kx, sc.ky = 30, GH - 1                       # on the bottom edge
before = sc.percent()


def walk(d, n):
    for _ in range(n):
        assert sc.step(d), (d, sc.kx, sc.ky)


walk("up", 20)
assert sc.weaving and len(sc.trail) == 20
walk("left", 30)                                 # reaches the left edge: the pocket closes
assert not sc.weaving
assert sc.percent() > before
assert pocket not in sc.balls and fl in sc.balls, "the small pocket is claimed together with its fluff"
assert sc.wrapped_n == 1
assert sc.is_edge(sc.ky * GW + sc.kx), "KUMO stands on yarn after a claim"
open_left = sum(1 for v in sc.grid if v == YW.OPEN)
assert open_left == sc.open_n and len(S.open_regions(sc.grid)) == 1, "the rug stays one piece"
# crossing your own loose yarn is not allowed; a snap puts KUMO back where the weave began
sc.kx, sc.ky = 100, GH - 1
walk("up", 5)
walk("right", 3)
walk("down", 2)
walk("left", 2)
assert not sc.step("left"), "blocked by own yarn"
lives = sc.lives
sc.hazard_hit("fluff", 0, 0)
assert sc.lives == lives - 1 and not sc.weaving and (sc.kx, sc.ky) == (100, GH - 1)
assert all(v != YW.TRAIL for v in sc.grid)
pygame.quit()

# the boss keeps the piece it stands on, even when it is the smaller one
app, sc = make(10)
sc.state = "play"
sc.boss.state = "fight"
sc.boss.x, sc.boss.y = 20.0, 150.0
sc.boss.vx = sc.boss.vy = 0.0
hp0 = sc.boss.hp
sc.kx, sc.ky = 40, GH - 1
walk("up", 30)
walk("left", 40)
assert sc.boss.hp < hp0, "claiming rug hurts the boss"
assert not sc.blocked(sc.boss.x, sc.boss.y), "the boss keeps its own piece of rug"
assert sc.percent() > 60, "the big side was claimed"
pygame.quit()
print("claim rules OK")


# ---------------------------------------------------------------- headless play
def play(stage, frames, levels=None, name=None, seed=1):
    random.seed(seed)
    ref = [None]
    stats = {"stages": set(), "claims": 0, "boss_hp": None, "wrapped": 0, "poms": 0, "fish": 0}
    app, sc = make(stage, frames, lambda f: ref[0](f) if ref[0] else set(), levels)
    ref[0] = YW.gif_bot(sc)
    for f in range(frames):
        app.input.begin()
        app.input.end(f)
        if app.scene is not sc:
            break
        sc.t += 1 / 60
        sc.update(1 / 60)
        if f % 3 == 0:
            sc.draw(app.canvas)
        stats["stages"].add(sc.n)
        if sc.n == stage:
            stats["claims"] = max(stats["claims"], sc.claims)
            stats["wrapped"] = max(stats["wrapped"], sc.wrapped_n)
            stats["poms"] = max(stats["poms"], sc.poms_wrapped)
            stats["fish"] = max(stats["fish"], sc.fish_got)
            if sc.boss:
                stats["boss_hp"], stats["boss_max"] = sc.boss.hp, sc.boss.maxhp
    sc.draw(app.canvas)
    app.screenshot(os.path.join(SHOTS, (name or f"yw-stage{stage}") + ".png"))
    pygame.quit()
    return sc, stats


sc, stats = play(1, 3600)
assert sc.score > 0 and stats["claims"] > 0, "the bot should claim rug on stage 1"
print(f"stage 1: claims {stats['claims']}, reached stage {sc.n}, score {sc.score}")
sc, stats = play(5, 2400, name="yw-bonus-poms")
assert 6 in stats["stages"] or sc.state == "pick" or sc.overlay is not None, stats
print(f"bonus poms: {stats['poms']} wrapped, claims {stats['claims']} -> stage {sc.n}")
sc, stats = play(15, 2400, name="yw-bonus-fish")
assert stats["fish"] > 0, stats
print(f"bonus fish: {stats['fish']} treats -> stage {sc.n}")
for n in (10, 20, 30, 40, 50, 200):
    sc, stats = play(n, 3000, {"guard": 3, "quick": 3, "calm": 3}, name=f"yw-boss{n}")
    print(f"boss stage {n} ({camp[n - 1]['boss']['name']}): hp {stats['boss_hp']}/{stats['boss_max']} -> stage {sc.n} "
          f"{sc.state}")
    assert stats["boss_hp"] < stats["boss_max"], "the boss should lose rug"
for n in (24, 47, 63, 78, 88, 99, 123, 166, 199):
    sc, stats = play(n, 1500, {"guard": 2}, seed=n)
    print(f"stage {n} ({camp[n - 1]['room']}): claims {stats['claims']} wraps {stats['wrapped']} -> stage {sc.n} "
          f"{sc.state} {sc.percent()}%")
print("shots in", SHOTS)
print("YARN WEAVER OK")
