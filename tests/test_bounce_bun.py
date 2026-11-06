"""BOUNCE BUN campaign checks: all 200 stages generate and validate (every snack can be reached, keys before
locks, portal pairs, moving rows stay inside), then headless bot runs of a normal stage, both bonus stage kinds
and every boss design.
usage: python tests/test_bounce_bun.py [shot_dir]"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-bb-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A  # noqa: E402
from mochi_arcade.arcade import STAGES, is_boss, is_bonus  # noqa: E402
from mochi_arcade.games import GAMES, bounce_bun as BB  # noqa: E402
from mochi_arcade.games import bounce_bun_stages as S  # noqa: E402
from mochi_arcade.gfx import W  # noqa: E402

# ---------------------------------------------------------------- campaign data
camp = S.build_campaign()
assert len(camp) == STAGES == 200
assert json.loads(json.dumps(BB.EXPORT))["stages"] == camp, "EXPORT must be plain JSON and match the campaign"
assert camp == S.CAMPAIGN, "generation must be deterministic"
kinds = {"normal": 0, "boss": 0, "bonus": 0}
boss_kinds = set()
names = set()
for st in camp:
    n = st["n"]
    errs = S.validate(st)
    assert not errs, (n, st["name"], errs)
    kinds[st["kind"]] += 1
    assert st["tier"] == (n - 1) // 10
    assert (st["kind"] == "boss") == is_boss(n) and (st["kind"] == "bonus") == is_bonus(n), n
    for row in st["rows"]:
        assert all(ch in BB.KIND or ch == "." for ch in row), (n, row)
    if st["kind"] == "boss":
        b = st["boss"]
        boss_kinds.add(b["kind"])
        assert b["hp"] > 0 and b["rate"] > 0 and b["kind"] in S.BOSSES
    names.add(st["name"])
assert kinds == {"normal": 160, "boss": 20, "bonus": 20}, kinds
assert len(boss_kinds) >= 5, boss_kinds
assert len(names) >= 30, len(names)
# difficulty goes up: later tiers are faster, bosses tougher, bigger layouts, more armour
assert camp[190]["speed"] > camp[0]["speed"]
assert camp[199]["boss"]["hp"] > camp[9]["boss"]["hp"]
armour = lambda sts: sum("".join(s["rows"]).count("h") + "".join(s["rows"]).count("H") for s in sts)  # noqa: E731
assert armour(camp[150:160]) > armour(camp[0:10])
# every mechanic shows up from its introduction tier on
first = {}
for st in camp:
    flat = "".join(st["rows"])
    for ch in "?xrLk*oH":
        if ch in flat:
            first.setdefault(ch, st["tier"])
    if st["moves"]:
        first.setdefault("move", st["tier"])
    if st["creep"]:
        first.setdefault("creep", st["tier"])
assert first["?"] == 1 and first["x"] == 2 and first["move"] == 3 and first["r"] == 4, first
assert first["L"] == 5 and first["*"] == 6 and first["o"] == 7 and first["H"] == 8 and first["creep"] == 9, first
for name, rows in BB.LEVELS:
    assert all(len(r) == 18 for r in rows), name
print(f"campaign OK: {kinds}, {len(names)} stage names, bosses {sorted(boss_kinds)}")


# ---------------------------------------------------------------- headless play
def bot(ref):
    def f(frame):
        sc = ref[0]
        keys = set()
        if sc.overlay is not None:
            if frame % 20 == 0:
                keys.add("right" if frame % 40 else "a")
            return keys
        if sc.state != "play":
            if sc.state == "tally" and frame % 30 == 0:
                keys.add("a")
            return keys
        balls = [b for b in sc.balls if b.stuck is None]
        tx = W / 2
        if not balls:
            if frame % 30 in (0, 1):
                keys.add("a")
            good = [s for s in sc.sweets if s.kind != 9]
            if good:
                tx = max(good, key=lambda s: s.y).x
        else:
            down = [b for b in balls if b.vy > 0] or balls
            b = max(down, key=lambda b: b.y)
            tx = b.x + (5 if b.vx > 0 else -5)
        if abs(tx - sc.px) > 3:
            keys.add("right" if tx > sc.px else "left")
        if frame % 7 == 0:
            keys.add("b")
        return keys
    return f


info = next(g for g in GAMES if g.id == "bounce_bun")


def play(stage, frames, levels=None, name=None):
    """Run the game headless as fast as possible (no frame clock), drawing every few frames."""
    ref = [None]
    stats = {"coins": 0, "sweets": 0, "boss_hp": None, "stages": set()}
    app = A.App(windowed=True, mute=True, test_frames=frames, script=bot(ref))
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
        sc.t += 1 / 60
        sc.update(1 / 60)
        if f % 3 == 0:
            sc.draw(app.canvas)
        stats["coins"] = max(stats["coins"], sc.coins)
        stats["sweets"] = max(stats["sweets"], sc.caught + sc.golds)
        stats["stages"].add(sc.n)
        if sc.boss and sc.n == stage:
            stats["boss_hp"] = sc.boss.hp
    sc.draw(app.canvas)
    app.screenshot(os.path.join(SHOTS, (name or f"bb-stage{stage}") + ".png"))
    pygame.quit()
    return sc, stats


sc, stats = play(1, 3600)
assert sc.score > 0, "the bot should score on stage 1"
print(f"stage 1: reached stage {sc.n}, score {sc.score}, state {sc.state}")
sc, stats = play(5, 2400, name="bb-bonus-coins")
assert stats["coins"] > 0 and 6 in stats["stages"], stats
print(f"bonus coins: {stats['coins']} coins, then stage {sc.n}")
sc, stats = play(15, 2400, name="bb-bonus-rain")
assert stats["sweets"] > 0 and 16 in stats["stages"], stats
print(f"bonus rain: {stats['sweets']} sweets, then stage {sc.n}")
for n in (10, 20, 30, 40, 50, 160, 200):
    sc, stats = play(n, 3600, {"power": 3, "laser": 3, "wide": 4}, name=f"bb-boss{n}")
    print(f"boss stage {n} ({sc.boss.name if sc.n == n else 'beaten'}): hp {stats['boss_hp']}/{camp[n - 1]['boss']['hp']}"
          f" -> stage {sc.n} {sc.state}")
    assert stats["boss_hp"] is None or stats["boss_hp"] < camp[n - 1]["boss"]["hp"], "the boss should take damage"
# later normal stages with every mechanic around
for n in (31, 61, 74, 97, 121, 188):
    sc, stats = play(n, 1800, {"power": 2, "laser": 2})
    print(f"stage {n} ({camp[n - 1]['name']}): score {sc.score} -> stage {sc.n} {sc.state}")
print("shots in", SHOTS)
print("BOUNCE BUN OK")
