"""ALLEY HOP campaign checks: all 200 stages generate deterministically and validate (traffic gaps fit the speed,
canal / laundry platforms always come round, gates and trains leave time to cross, every kitten and a box can be
reached, fences have a sidewalk below), mechanics show up from their tier on, then headless autopilot runs of
normal stages across the campaign, both bonus stage kinds and every boss design.
usage: python tests/test_alley_hop.py [shot_dir]      (MOCHI_FAST=1 is not needed: runs are unthrottled)"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-ah-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A, music, sprites  # noqa: E402
from mochi_arcade.arcade import STAGES, is_bonus, is_boss  # noqa: E402
from mochi_arcade.games import GAMES, alley_hop as AH  # noqa: E402
from mochi_arcade.games import alley_hop_stages as S  # noqa: E402

# ---------------------------------------------------------------- campaign data
camp = S.build_campaign()
assert len(camp) == STAGES == 200
assert camp == S.CAMPAIGN, "generation must be deterministic"
assert json.loads(json.dumps(AH.EXPORT))["stages"] == camp, "EXPORT must be plain JSON and match the campaign"
kinds = {"normal": 0, "boss": 0, "bonus": 0}
boss_kinds, bonus_kinds, names = set(), set(), set()
for st in camp:
    n = st["n"]
    errs = S.validate(st)
    assert not errs, (n, st["layout"], errs)
    kinds[st["kind"]] += 1
    assert st["tier"] == (n - 1) // 10
    assert (st["kind"] == "boss") == is_boss(n) and (st["kind"] == "bonus") == is_bonus(n), n
    if st["kind"] == "boss":
        boss_kinds.add(st["boss"]["kind"])
    if st["kind"] == "bonus":
        bonus_kinds.add(st["bonus"])
    names.add(st["name"])
assert kinds == {"normal": 160, "boss": 20, "bonus": 20}, kinds
assert len(boss_kinds) >= 6, boss_kinds
assert bonus_kinds == {"feast", "parade"}, bonus_kinds
assert len(names) >= 30, len(names)
# every mechanic shows up from its tier on, on the first stage of that tier (its card announces it)
first = {}
for st in camp:
    if st["kind"] != "normal":
        continue
    for ln in st["lanes"]:
        first.setdefault(ln["t"], st["n"])
        if ln["dv"]:
            first.setdefault("dive", st["n"])
        if ln["t"] == "gap" and not ln["sw"]:
            first.setdefault("pulley", st["n"])
        for k, _, _ in ln["it"]:
            first.setdefault(k, st["n"])
    for key in ("manholes", "dark", "lids"):
        if st[key]:
            first.setdefault(key, st["n"])
assert first["scooter"] == 11 and first["water"] == 21 and first["gap"] == 31, first
assert first["rail"] == 41 and first["fence"] == 41 and first["manholes"] == 51 and first["dive"] == 61, first
assert first["dark"] == 71 and first["van"] == 81 and first["lids"] == 91 and first["pulley"] == 131, first
# difficulty climbs: faster traffic, more kittens, tougher bosses
speed = lambda sts: sum(abs(ln["v"]) for st in sts for ln in st["lanes"] if ln["t"] == "road") / max(  # noqa: E731
    1, sum(1 for st in sts for ln in st["lanes"] if ln["t"] == "road"))
assert speed(camp[180:200]) > speed(camp[0:20]) * 1.4
assert len(camp[190]["kittens"]) > len(camp[0]["kittens"])
assert camp[199]["boss"]["hp"] > camp[9]["boss"]["hp"] and camp[199]["boss"]["sp"] > camp[9]["boss"]["sp"]
assert len(camp[199]["boss"]["atk"]) > len(camp[9]["boss"]["atk"])
# kit hooks: own sprites + songs, howto shape
assert all(k in sprites.ART for k in ("ah_sushi", "ah_kit", "ah_fish", "ah_yarn"))
assert "ah_alley" in music.SONGS and "ah_canal" in music.SONGS
assert AH.HOWTO[-1] == "ENTER / ESC  PAUSE" and all(len(h) <= 46 for h in AH.HOWTO)
assert len(AH.UPGRADES) >= 6
print(f"campaign OK: {kinds}, {len(names)} stage names, bosses {sorted(boss_kinds)}")

# ---------------------------------------------------------------- headless play
info = next(g for g in GAMES if g.id == "alley_hop")


def play(stage, frames, levels=None, name=None, lives=None, chain=False):
    """Run the game unthrottled with the autopilot (drawing every few frames)."""
    ref = [None]
    app = A.App(windowed=True, mute=True, test_frames=frames,
                script=lambda f: AH.autopilot(ref[0]) if ref[0] and f % 2 == 0 else set())
    if not app.store.profiles:
        app.store.create("TESTER", "pink")
    app.profile = app.store.last()
    sc = info.load()(app, info, {"difficulty": "normal", "start": 1, "stage": stage})
    sc.levels.update(levels or {})
    sc.picks_left = 0
    sc.state = "intro"
    if lives:
        sc.lives = lives
    ref[0] = sc
    app.apply_settings()
    app.scenes = [sc]
    sc.enter()
    stats = {"home": 0, "treats": 0, "boss_hp": None, "stages": set(), "cleared": None, "misses": 0}
    prev_lives = sc.lives
    for f in range(frames):
        app.input.begin()
        app.input.end(f)
        if app.scene is not sc:
            break
        sc.t += 1 / 60
        sc.update(1 / 60)
        if f % 4 == 0:
            sc.draw(app.canvas)
        if sc.lives < prev_lives:
            stats["misses"] += 1
        prev_lives = sc.lives
        stats["stages"].add(sc.n)
        if sc.n == stage:
            stats["home"] = max(stats["home"], sc.home_count)
            stats["treats"] = max(stats["treats"], sc.fish_n + sc.gold_n)
            if sc.boss:
                stats["boss_hp"] = sc.boss.hp
            if sc.state in ("tally", "pick") and stats["cleared"] is None:
                stats["cleared"] = f / 60
                if not chain:
                    break
    sc.draw(app.canvas)
    app.screenshot(os.path.join(SHOTS, (name or f"ah-stage{stage}") + ".png"))
    pygame.quit()
    return sc, stats


sc, stats = play(1, 3600, chain=True)
assert sc.score > 0 and 2 in stats["stages"], "the autopilot should clear stage 1"
print(f"stage 1: cleared in {stats['cleared']:.0f}s, reached stage {sc.n}, score {sc.score}")
sc, stats = play(5, 2400, name="ah-bonus-feast")
assert stats["treats"] > 5 and stats["cleared"], stats
print(f"bonus feast: {stats['treats']} treats")
sc, stats = play(15, 2400, name="ah-bonus-parade")
assert stats["home"] >= 8 and stats["cleared"], stats
print(f"bonus parade: {stats['home']} kittens home")
for n in (10, 20, 30, 40, 50, 60, 200):
    sc, stats = play(n, 7200, {"box": 2}, name=f"ah-boss{n}", lives=60)
    spec = camp[n - 1]["boss"]
    print(f"boss stage {n} ({spec['name']}): hp {stats['boss_hp']}/{spec['hp']} misses {stats['misses']}"
          f" cleared {stats['cleared'] is not None}")
    assert stats["boss_hp"] is not None and stats["boss_hp"] < spec["hp"], "the boss should take damage"
# a sample of normal stages over the whole campaign: the autopilot (unlimited lives) should clear nearly all
sample = [n for n in range(2, 201, 9) if camp[n - 1]["kind"] == "normal"]
cleared = 0
for n in sample:
    sc, stats = play(n, 7200, lives=99, name=f"ah-s{n}" if n % 3 == 0 else "ah-last")
    cleared += 1 if stats["cleared"] else 0
    print(f"stage {n:3d} {camp[n - 1]['layout']}: {'%.0fs' % stats['cleared'] if stats['cleared'] else 'not cleared'}"
          f" misses {stats['misses']} home {stats['home']}/{len(camp[n - 1]['kittens'])}")
assert cleared >= len(sample) * 0.85, (cleared, len(sample))
print(f"autopilot cleared {cleared}/{len(sample)} sampled stages")
# the carousel preview at both card sizes
for size in ((112, 74), (92, 58)):
    pv = pygame.Surface(size)
    for t in (0.0, 1.3, 2.9):
        AH.preview(pv, t)
print("shots in", SHOTS)
print("ALLEY HOP OK")
