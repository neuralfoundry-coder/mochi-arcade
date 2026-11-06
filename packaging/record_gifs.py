"""Record short gameplay clips (headless) with simple autoplay bots.

usage:
  python packaging/record_gifs.py frames OUT_DIR   # capture PNG frames (needs pygame)
  python packaging/record_gifs.py gifs OUT_DIR     # encode OUT_DIR/<clip>/*.png -> docs/<clip>.gif (needs Pillow)
"""
import math
import os
import sys
import tempfile

CAT_CORNER = ["whisker_maze", "tower_tabby", "alley_hop", "yarn_weaver", "cloud_pounce", "kitten_pile",
              "hairball_havoc", "rooftop_run", "window_watch", "paw_pinball", "meow_deck"]
CLIPS = ["arcade", "soap-hop", "jelly-stack", "comet-kitty", "noodle-slurp", "bounce-bun"] + \
    [g.replace("_", "-") for g in CAT_CORNER]
STEP = 3          # capture every 3rd frame -> 20 fps
SECONDS = 5


# ----------------------------------------------------------------------------- bots
def tap(keys, want, frame):
    """Press on even frames, release on odd ones so every press registers as a new hit."""
    if frame % 2 == 0:
        keys.update(want)


def soap_bot(scene):
    from mochi_arcade.games.soap_hop import FAST_PHASE

    def f(frame):
        keys = set()
        if scene.state not in ("play", "clear", "intro"):
            return keys
        p = scene.player
        cost = lambda x, y: abs(x - p.cx) + 3 * abs(y - p.cy)  # noqa: E731  prefer things on our level
        trapped = [b for b in scene.bubbles if b.enemy and b.age > FAST_PHASE and b.pop_in is None]
        level = [e for e in scene.enemies if abs(e.cy - p.cy) < 16]
        if trapped and min(cost(b.x, b.y) for b in trapped) < 160:
            b = min(trapped, key=lambda b: cost(b.x, b.y))
            if abs(b.x - p.cx) > 3:
                keys.add("right" if b.x > p.cx else "left")
            if b.y < p.cy - 6 and abs(b.x - p.cx) < 20:
                keys.add("a")
        elif level:
            e = min(level, key=lambda e: abs(e.cx - p.cx))
            dx = e.cx - p.cx
            want = "right" if dx > 0 else "left"
            if (scene.face > 0) != (dx > 0):
                keys.add(want)                      # turn to face it
            elif abs(dx) > 70:
                keys.add(want)                      # close in a little
            elif abs(dx) < 22:
                keys.add("left" if dx > 0 else "right")  # back off
            if frame % 10 == 0:
                keys.add("b")
        elif scene.enemies or scene.fruits:
            pool = scene.enemies or scene.fruits
            t = min(pool, key=lambda q: cost(q.cx, q.cy))
            if abs(t.cx - p.cx) > 4:
                keys.add("right" if t.cx > p.cx else "left")
            if t.cy < p.cy - 18 and (frame // 20) % 2 == 0:
                keys.add("a")
        for e in scene.enemies:
            if abs(e.cx - p.cx) < 20 and abs(e.cy - p.cy) < 20 and frame % 10 < 6:
                keys.add("a")
        return keys
    return f


def jelly_bot(scene):
    from mochi_arcade.games.jelly_stack import BW, BH
    st = {"piece": None, "target": None, "wait": 0, "age": 0}

    def evaluate():
        p = scene.cur
        best = None
        for rot in range(4):
            for x in range(-3, BW + 3):
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
                for cx in range(BW):
                    col = [grid[cy][cx] for cy in range(BH)]
                    top = next((i for i, v in enumerate(col) if v), BH)
                    heights.append(BH - top)
                    holes += sum(1 for v in col[top:] if not v)
                bump = sum(abs(heights[i] - heights[i + 1]) for i in range(BW - 1))
                score = lines * 7.6 - holes * 3.6 - sum(heights) * 0.51 - bump * 0.18
                if best is None or score > best[0]:
                    best = (score, rot, x)
        return best

    def f(frame):
        keys = set()
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
        if p.rot != rot and st["age"] < 40:
            tap(keys, {"up"}, frame)
        elif p.x != x and st["age"] < 60:
            tap(keys, {"right" if x > p.x else "left"}, frame)
        elif st["age"] > 14:
            tap(keys, {"y"}, frame)
        return keys
    return f


def comet_bot(scene):
    from mochi_arcade.games.comet_kitty import PY

    def f(frame):
        keys = set()
        if frame % 8 < 4:
            keys.add("a")
        threats = [b for b in scene.bullets if b[1] > PY - 70 and abs(b[0] - scene.px) < 14]
        if threats:
            b = min(threats, key=lambda b: -b[1])
            keys.add("left" if b[0] > scene.px else "right")
            return keys
        live = [e for e in scene.enemies if not (e.state == "enter" and e.t < e.delay)]
        if live:
            e = max(live, key=lambda e: e.y)
            tx = e.x + math.sin(frame * 0.05) * 6
            if abs(tx - scene.px) > 3:
                keys.add("right" if tx > scene.px else "left")
        return keys
    return f


def noodle_bot(scene):
    # the campaign version ships its own path-finding bot
    from mochi_arcade.games.noodle_slurp import gif_bot
    return gif_bot(scene)


def bounce_bot(scene):
    def f(frame):
        keys = set()
        balls = [b for b in scene.balls if b.stuck is None]
        if not balls:
            if frame % 20 in (0, 2):
                keys.add("a")
            return keys
        b = max(balls, key=lambda b: b.y)
        tx = b.x + (6 if b.vx > 0 else -6)
        if abs(tx - scene.px) > 3:
            keys.add("right" if tx > scene.px else "left")
        return keys
    return f


def arcade_script(app):
    """Title -> profiles -> main menu -> game select carousel -> setup."""
    plan = {40: "a", 75: "a", 105: "a", 140: "right", 165: "right", 190: "right", 215: "right", 245: "left",
            270: "left", 300: "a"}

    def f(frame):
        a = plan.get(frame)
        return {a} if a else set()
    return f


# ----------------------------------------------------------------------------- capture
def capture(out, only=None):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    tmp = tempfile.mkdtemp()
    os.environ["XDG_DATA_HOME"] = os.environ["XDG_CACHE_HOME"] = tmp
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import random

    import pygame

    from mochi_arcade import app as A, ui
    from mochi_arcade.games import GAMES

    def record(name, make_scene, bot=None, warmup=60, seed=1, script=None):
        if only and name != only:
            return
        random.seed(seed)
        d = os.path.join(out, name)
        os.makedirs(d, exist_ok=True)
        total = warmup + SECONDS * 60
        # games use a fixed 1/60 s step (deterministic, reproducible clips); the menu clip keeps real fades
        a = A.App(windowed=True, mute=True, test_frames=0 if name == "arcade" else total + 1)
        a.profile = a.store.last() or a.store.create("MOMO", "pink")
        a.profile["settings"]["fullscreen"] = False   # headless: never try to toggle fullscreen
        scene = make_scene(a)
        holder = {"bot": None}
        a.input.script = script or (lambda fr: holder["bot"](fr) if holder["bot"] else set())
        if bot:
            holder["bot"] = bot(scene)
        orig = a.draw
        n = [0]

        def draw():
            orig()
            if a.frame >= warmup and (a.frame - warmup) % STEP == 0:
                pygame.image.save(pygame.transform.scale(a.canvas, (640, 400)), os.path.join(d, f"{n[0]:04d}.png"))
                n[0] += 1
            if a.frame >= total:
                a.running = False
        a.draw = draw
        a.run(scene)
        print(f"{name}: {n[0]} frames", flush=True)

    def game(gid, **opts):
        info = next(g for g in GAMES if g.id == gid)
        o = {k: d for k, _, _, d in info.options}
        o.update(opts)
        return lambda a: info.load()(a, info, o)

    record("arcade", lambda a: ui.Title(a), warmup=10, script=arcade_script(None))
    record("soap-hop", game("soap_hop", stage=8), soap_bot, warmup=380, seed=2)
    record("jelly-stack", game("jelly_stack"), jelly_bot, warmup=20)
    record("comet-kitty", game("comet_kitty"), comet_bot, warmup=200, seed=2)
    record("noodle-slurp", game("noodle_slurp"), noodle_bot, warmup=60, seed=4)
    record("bounce-bun", game("bounce_bun", level=3), bounce_bot, warmup=60, seed=5)
    # CAT CORNER: every game ships its own gif_bot(scene) -> fn(frame) -> keys
    import importlib
    for gid in CAT_CORNER:
        mod = importlib.import_module(f"mochi_arcade.games.{gid}")
        record(gid.replace("_", "-"), game(gid), mod.gif_bot, warmup=240, seed=3)


def encode(out):
    from PIL import Image
    root = os.path.join(os.path.dirname(__file__), "..", "docs")
    for name in CLIPS:
        d = os.path.join(out, name)
        files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        frames = [Image.open(os.path.join(d, f)).convert("RGB").quantize(colors=96, method=Image.Quantize.MEDIANCUT,
                                                                           dither=Image.Dither.NONE) for f in files]
        path = os.path.join(root, f"{name}.gif")
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=1000 // (60 // STEP), loop=0,
                       optimize=True, disposal=1)
        print(f"{path}: {len(frames)} frames, {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    {"frames": capture, "gifs": encode}[sys.argv[1]](*sys.argv[2:])
