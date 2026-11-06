"""Generate the app icon and README screenshots (headless). usage: python packaging/make_assets.py"""
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
tmp = tempfile.mkdtemp()
os.environ["XDG_DATA_HOME"] = os.environ["XDG_CACHE_HOME"] = tmp

import pygame  # noqa: E402

from mochi_arcade import app as A, ui  # noqa: E402
from mochi_arcade.games import GAMES  # noqa: E402
from mochi_arcade.gfx import col, sprite  # noqa: E402

pygame.init()
# ---------------------------------------------------------------- icon
for size in (256, 128, 64):
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, col("pink"), (0, 0, 32, 32), border_radius=7)
    pygame.draw.rect(s, col("hotpink"), (0, 0, 32, 32), 2, border_radius=7)
    s.blit(sprite("momo_idle", 0), (8, 9))
    pygame.image.save(pygame.transform.scale(s, (size, size)), os.path.join(ROOT, "data", f"mochi-arcade-{size}.png"))


def shot(name, scene_fn, frames, keys=(), seed=1, game_opts=None):
    rnd = random.Random(seed)
    held = set()
    def script(f):
        if f % 8 == 0:
            held.clear()
            held.update(k for k in keys if rnd.random() < 0.45)
        return held
    a = A.App(windowed=True, mute=True, test_frames=frames, script=script)
    a.profile = a.store.last() or a.store.create("MOMO", "white")
    a.shot_path = os.path.join(ROOT, "docs", f"{name}.png")
    a.run(scene_fn(a))
    im = pygame.image.load(a.shot_path)
    pygame.image.save(pygame.transform.scale(im, (640, 400)), a.shot_path)  # 2x for the README
    print("wrote", a.shot_path)


def game(gid, **opts):
    info = next(g for g in GAMES if g.id == gid)
    base = {k: d for k, _, _, d in info.options}
    base.update(opts)
    return lambda a: info.load()(a, info, base)


shot("title", lambda a: ui.Title(a), 100)
# per-game clips: see packaging/record_gifs.py
