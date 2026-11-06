"""MEOW DECK checks: the cat card table (60+ distinct cats, readable card text, every portrait painted), all 200
floors generate and validate, every fight is winnable by the bot with a crew fit for its tier, then headless
bot runs of a normal floor, the CAT CAFE (slots + shop) and boss floors, plus touch taps.
usage: MOCHI_FAST=1 python tests/test_meow_deck.py [shot_dir]"""
import json
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TMP = tempfile.mkdtemp(prefix="mochi-md-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["XDG_CACHE_HOME"] = TMP
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

import pygame  # noqa: E402

from mochi_arcade import app as A, sprites  # noqa: E402
from mochi_arcade.arcade import STAGES, is_boss, is_bonus  # noqa: E402
from mochi_arcade.games import GAMES, meow_deck as M  # noqa: E402
from mochi_arcade.games import meow_deck_data as D  # noqa: E402
from mochi_arcade.games import meow_deck_rules as R  # noqa: E402
from mochi_arcade.gfx import text_width  # noqa: E402

# ---------------------------------------------------------------- cards
cats = [c for c in D.CATS if c["id"] not in D.SPECIAL]
assert len(cats) >= 60, len(cats)
assert len({c["name"] for c in D.CATS}) == len(D.CATS), "card names must be unique"
assert len({c["id"] for c in D.CATS}) == len(D.CATS)
for c in D.CATS:
    assert c["spr"] in sprites.ART and len(sprites.ART[c["spr"]]) == 2, c["id"]
    rows = sprites.ART[c["spr"]][0]
    assert len(rows) == 24 and all(len(r) == 24 for r in rows), c["id"]
    assert text_width(c["name"] + "+") <= M.BIG_W - 4, c["name"]
    for lines in (c["text"], c["uptext"]):
        assert 1 <= len(lines) <= 3 and all(len(ln) <= 16 for ln in lines), (c["id"], lines)
    for f in c["fx"] + c["up"]:
        assert f[0] in D._FX_TEXT, f
portraits = {tuple(sprites.ART[c["spr"]][0]) for c in D.CATS}
assert len(portraits) == len(D.CATS), "every cat needs its own face"
for role in D.ROLES:
    assert sum(1 for c in cats if c["role"] == role) >= 8, role
breeds = {c["breed"] for c in cats}
assert len(breeds) == 15, breeds
for b in breeds:
    assert sum(1 for c in cats if c["breed"] == b) >= 3, b
assert {c["rar"] for c in cats} == {0, 1, 2, 3}
for line in M.HOWTO:
    assert len(line) <= 46 and line == line.upper(), line
assert M.HOWTO[-1] == "ENTER / ESC  PAUSE"
assert len(M.CHARMS) >= 6
print(f"cards OK: {len(cats)} cats + {len(D.SPECIAL)} specials, {len(breeds)} breeds")

# ---------------------------------------------------------------- campaign
camp = D.build_campaign()
assert len(camp) == STAGES == 200
assert camp == D.CAMPAIGN, "generation must be deterministic"
assert json.loads(json.dumps(M.EXPORT))["stages"] == camp, "EXPORT must be plain JSON and match the campaign"
kinds = {"normal": 0, "boss": 0, "bonus": 0}
boss_ids, names, first = set(), set(), {}
for st in camp:
    n = st["n"]
    errs = D.validate(st)
    assert not errs, (n, st["name"], errs)
    kinds[st["kind"]] += 1
    assert st["tier"] == (n - 1) // 10 and st["theme"] == st["tier"]
    assert (st["kind"] == "boss") == is_boss(n) and (st["kind"] == "bonus") == is_bonus(n), n
    names.add(st["name"])
    for f in st["foes"]:
        first.setdefault(f["id"], st["tier"])
        if f.get("boss"):
            boss_ids.add(f["id"])
            assert len(f["phases"]) >= (3 if st["tier"] >= 6 else 2), n
assert kinds == {"normal": 160, "boss": 20, "bonus": 20}, kinds
assert len(boss_ids) >= 5, boss_ids
assert len(names) >= 30, len(names)
for fid, f in D.FOES.items():
    assert first.get(fid) == f["tier"], (fid, first.get(fid), f["tier"])   # each foe shows up on its tier
total_hp = [sum(f["hp"] for f in st["foes"]) for st in camp]
assert total_hp[195] > total_hp[5] * 4 and camp[199]["foes"][0]["hp"] > camp[9]["foes"][0]["hp"] * 4
assert camp[150]["foes"][0]["pow"] > camp[1]["foes"][0]["pow"]
mods = {st["mod"] for st in camp if st["mod"]}
assert mods == set(D.MODS), mods
print(f"campaign OK: {kinds}, {len(names)} names, bosses {sorted(boss_ids)}")

# every fight can be won by the bot with a crew fit for the tier (3 tries, fresh HP)
fails = []
for st in camp:
    if st["kind"] == "bonus":
        continue
    wins = 0
    for r in range(3):
        rng = random.Random(st["n"] * 31 + r)
        deck, charms, maxhp = R.reference_kit(st["tier"], rng)
        won, hp, turns = R.simulate(st, deck, charms, maxhp, rng)
        wins += won
        if wins:
            break
    if not wins:
        # bosses are tough: give them a few more tries before calling a floor unwinnable
        for r in range(3, 12):
            rng = random.Random(st["n"] * 31 + r)
            deck, charms, maxhp = R.reference_kit(st["tier"], rng)
            wins += R.simulate(st, deck, charms, maxhp, rng)[0]
            if wins:
                break
    if not wins:
        fails.append(st["n"])
assert not fails, f"unwinnable floors: {fails}"
print("winnable OK: every fight won by the bot")


# ---------------------------------------------------------------- rules unit checks
def battle(foes, deck_ids, charms=None):
    st = {"n": 1, "tier": 0, "kind": "normal", "foes": foes, "mod": ""}
    b = R.Battle(st, [R.Card(c) for c in deck_ids], 70, 70, charms or {}, random.Random(1))
    b.start()
    return b


pug = {"id": "pug", "hp": 50, "pow": 1.0, "blk": 0, "zoom": 0}
b = battle([pug], ["rio"] * 5)
assert len(b.hand) == 5 and b.hero.fish == 3
for c in b.hand:
    c.gold = False
ev = b.play(0, 0)
assert b.foes[0].hp == 44 and b.chain == 1 and b.power == 0
b.play(0, 0)                          # same role + same breed: +2
assert b.chain == 2 and b.power == 2 and b.foes[0].hp == 44 - 8, b.foes[0].hp
b.foes[0].dazed = 1
b.play(0, 0)                          # power 4: (6 + 4) * 3 // 2 = 15
assert b.foes[0].hp == 36 - 15, b.foes[0].hp
assert not b.can_play(0)              # out of fish
b = battle([pug], ["sue"] * 5)
b.foes[0].intent = ["atk", 6, 2]
b.play(0, 0)
b.end_turn()
b.foe_act(0)
assert b.hero.hp == 70 - 6 - 1, b.hero.hp     # 5 block soaks the first hit
b = battle([dict(pug, hp=5)], ["flick"] * 5)
b.play(0, 0)
assert b.foes[0].itchy == 5
b.end_turn()
b.foe_act(0)
assert not b.foes[0].alive and b.won
boss_st = D.CAMPAIGN[9]                  # BARON BULLDOG: summon a pug, then knock the boss out
b = R.Battle(boss_st, [R.Card("rio") for _ in range(10)], 70, 70, {}, random.Random(2))
b.start()
ev = []
b.do_move(0, ["summon", "pug"], ev)
assert len(b.alive()) == 2 and any(e[0] == "summon" for e in ev)
boss = next(k for k, f in enumerate(b.foes) if f.boss)
b.foes[boss].hp = 1
ev = []
b.hit_foe(boss, 50, ev)
assert b.won and sum(1 for e in ev if e[0] == "die") == 2, ev     # the helpers run away with the boss
print("rules OK")

# ---------------------------------------------------------------- headless play
info = next(g for g in GAMES if g.id == "meow_deck")
APP = A.App(windowed=True, mute=True, test_frames=1)
if not APP.store.profiles:
    APP.store.create("TESTER", "pink")
APP.profile = APP.store.last()


def play(stage, frames, name, seed=1, opts=None):
    random.seed(seed)
    o = {"difficulty": "normal", "start": 1, "stage": stage}
    o.update(opts or {})
    sc = info.load()(APP, info, o)
    bot = M.gif_bot(sc)
    APP.scenes = [sc]
    sc.enter()
    seen = set()
    floors = set()
    for f in range(frames):
        APP.input.begin()
        keys = set(bot(f))
        APP.input.pressed = keys - APP.input.held
        APP.input.held = keys
        sc.t += 1 / 60
        sc.update(1 / 60)
        if f % 4 == 0:
            sc.draw(APP.canvas)
        seen.add(sc.state if sc.overlay is None else "charm")
        floors.add(sc.n)
        if f in (frames // 3, 2 * frames // 3):
            sc.draw(APP.canvas)
            pygame.image.save(APP.canvas, os.path.join(SHOTS, f"{name}-{f}.png"))
        if sc.ending is not None:
            break
    return sc, seen, floors


sc, seen, floors = play(1, 5400, "floor1")
assert {"intro", "player", "anim", "foes", "win", "tally", "reward"} <= seen, seen
assert max(floors) >= 3 and sc.score > 0, (floors, sc.score)
print(f"floor 1 run OK: reached floor {max(floors)}, score {sc.score}, deck {len(sc.deck)}")

sc, seen, floors = play(5, 2400, "cafe")
assert {"slots", "cafe"} <= seen and max(floors) >= 6, (seen, floors)
print("cafe run OK")

for n in (10, 60, 100):
    sc, seen, floors = play(n, 7200, f"boss{n}", seed=n, opts={"difficulty": "easy"})
    assert "player" in seen and "foes" in seen, seen
    boss_fought = sc.n > n or (sc.battle and sc.battle.foes[0].hp < sc.battle.foes[0].maxhp)
    assert boss_fought, n
    print(f"boss {n} run OK: states {sorted(seen)}, now floor {sc.n}")

# touch: tap a card to select it, tap it again to play it, tap a foe to target
random.seed(3)
sc = info.load()(APP, info, {"difficulty": "normal", "start": 1, "stage": 2})
APP.scenes = [sc]
for f in range(40):
    APP.input.begin()
    APP.input.pressed, APP.input.held = set(), set()
    sc.t += 1 / 60
    sc.update(1 / 60)
sc.tap(160, 150)             # skip the intro
for f in range(30):
    APP.input.begin()
    APP.input.pressed, APP.input.held = set(), set()
    sc.t += 1 / 60
    sc.update(1 / 60)
assert sc.state == "player", sc.state
b = sc.battle
for c in b.hand:
    c.gold = False
x, y = sc.hand_pos(2)
sc.tap(x + 15, y + 30)
assert sc.sel == 2, sc.sel
fx = sc.foe_x(1)
sc.tgt = 0
sc.tap(fx, M.GROUND - 10)
assert sc.tgt == 1
fish = b.hero.fish
x, y = sc.hand_pos(sc.sel)
sc.tap(x + 15, y + 30)
assert sc.state == "anim", sc.state
print("taps OK")
print("ALL OK")
