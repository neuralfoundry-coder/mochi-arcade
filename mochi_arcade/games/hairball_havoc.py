"""HAIRBALL HAVOC - stop the robo-mice!  (placeholder: the full game is being built)."""
from mochi_arcade.games import DIFF
from mochi_arcade.games.base import GameScene
from mochi_arcade.gfx import col, draw_text

HOWTO = ["ARROWS      MOVE", "Z / SPACE   ACTION", "", "COMING SOON!", "", "ENTER / ESC  PAUSE"]
OPTIONS = [("difficulty", "DIFFICULTY", DIFF, "normal"),
           ("start", "START STAGE", "checkpoints", 1)]
SMOKE_KEYS = ["left", "right", "up", "down", "a", "b"]   # keys the smoke test mashes


class HairballHavoc(GameScene):
    music = "title"

    def tick(self, dt):
        if self.t > 2.5:
            self.end_game(False, "COMING SOON")

    def render(self, s):
        preview(s, self.t)


def preview(s, t):
    s.fill(col("ink"))
    w, h = s.get_width(), s.get_height()
    draw_text(s, "HAIRBALL HAVOC", w // 2, h // 2 - 8, "yellow", align="center")
    draw_text(s, "COMING SOON", w // 2, h // 2 + 4, "white", align="center")
