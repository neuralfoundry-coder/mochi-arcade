"""Shared game scene: pause menu, score, particles, game-over flow, HUD helpers."""
import pygame

from mochi_arcade.app import Scene
from mochi_arcade.gfx import H, W, FloatText, Particles, col, draw_text, panel, sprite
from mochi_arcade.ui import Menu, Result

LIVES = {"easy": 5, "normal": 3, "hard": 2}
SPEED = {"easy": 0.8, "normal": 1.0, "hard": 1.25}


class GameScene(Scene):
    def __init__(self, app, info, opt):
        super().__init__(app)
        self.info, self.opt = info, opt
        self.score = 0
        self.paused = False
        self.ending = None
        self.end_args = None
        self.parts = Particles()
        self.floats = FloatText()
        self.best = app.store.game(app.profile, info.id)["best"]
        self.pause_menu = Menu([
            {"label": "RESUME", "on": self.resume},
            {"label": "RESTART", "on": lambda: app.replace(info.load()(app, info, dict(opt)))},
            {"label": "QUIT TO MENU", "on": self.quit_to_menu},
        ], W // 2, 92, center=True, spacing=14)

    # ---------------------------------------------------------------- flow
    def resume(self):
        self.paused = False
        try:
            pygame.mixer.music.unpause()
        except pygame.error:
            pass

    def quit_to_menu(self):
        from mochi_arcade.games import GAMES
        from mochi_arcade.ui import GameSelect
        self.resume()
        self.app.replace(GameSelect(self.app, GAMES.index(self.info)))

    def add(self, pts, x=None, y=None, color="yellow"):
        self.score += pts
        if x is not None:
            self.floats.add(x, y, str(pts), color)

    def end_game(self, cleared=False, detail="", delay=1.6):
        if self.ending is None:
            self.ending = delay
            self.end_args = (cleared, detail)
            self.app.audio.stop_music()

    def update(self, dt):
        inp = self.app.input
        if self.paused:
            self.pause_menu.update(self.app, dt)
            if inp.hit("back"):
                self.resume()
            return
        if self.ending is not None:
            self.ending -= dt
            self.parts.update(dt)
            self.floats.update(dt)
            self.tick_ending(dt)
            if self.ending <= 0:
                cleared, detail = self.end_args
                self.app.replace(Result(self.app, self.info, self.opt, self.score, cleared, detail))
            return
        if inp.hit("start", "back"):
            self.paused = True
            self.pause_menu.i = 0
            self.app.audio.play("select")
            try:
                pygame.mixer.music.pause()
            except pygame.error:
                pass
            return
        self.tick(dt)
        self.parts.update(dt)
        self.floats.update(dt)

    def tick(self, dt):
        pass

    def tick_ending(self, dt):
        pass

    def draw(self, s):
        self.render(s)
        if self.paused:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((12, 8, 24, 170))
            s.blit(ov, (0, 0))
            panel(s, (90, 64, 140, 76), fill="ink", border="yellow")
            draw_text(s, "PAUSED", W // 2, 72, "yellow", align="center")
            self.pause_menu.draw(s, self.t)

    def render(self, s):
        pass

    # ---------------------------------------------------------------- HUD helpers
    def hearts(self, s, x, y, n, max_show=6):
        for i in range(min(n, max_show)):
            s.blit(sprite("heart"), (x + i * 8, y))
        if n > max_show:
            draw_text(s, f"+{n - max_show}", x + max_show * 8 + 2, y, "pink", shadow=None)

    def banner(self, s, text, sub=None, color="yellow"):
        panel(s, (60, 80, 200, 36 if sub else 24), fill="ink", border=color)
        draw_text(s, text, W // 2, 88, color, align="center")
        if sub:
            draw_text(s, sub, W // 2, 101, "white", align="center")
