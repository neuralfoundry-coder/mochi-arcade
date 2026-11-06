"""Shared game scene: pause menu, score, particles, game-over flow, HUD helpers."""
import pygame

from mochi_arcade.app import Scene
from mochi_arcade.arcade import Hype, UpgradePick
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
        self.hype = Hype(self)          # banners, combo, FEVER, jackpot, flash, hit-stop (arcade.py)
        self.overlay = None             # e.g. UpgradePick between stages
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
        """Score points (doubled during FEVER). Returns the points actually scored."""
        pts *= self.hype.mult
        self.score += pts
        if x is not None:
            self.floats.add(x, y, str(pts), "lime" if self.hype.fever_on else color)
        return pts

    def reached(self, stage):
        """Remember the furthest stage reached (unlocks checkpoints 1, 11, 21 ... in the setup screen)."""
        g = self.app.store.game(self.app.profile, self.info.id)
        if stage > g.get("reach", 1):
            g["reach"] = stage
            self.app.save()

    def pick_upgrade(self, pool, levels, on_done, title="POWER UP!"):
        """Show 3 upgrade cards; on_done(uid or None) runs when the player picks one."""
        self.overlay = UpgradePick(self, pool, levels, on_done, title)

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
            self.hype.update(dt)
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
        gdt = self.hype.update(dt)
        if self.overlay is not None:
            self.overlay.update(dt)
            if self.overlay is not None and self.overlay.done:
                self.overlay = None
            self.parts.update(dt)
            self.floats.update(dt)
            return
        self.tick(gdt)
        self.parts.update(gdt)
        self.floats.update(gdt)

    def tick(self, dt):
        pass

    def tick_ending(self, dt):
        pass

    def draw(self, s):
        self.render(s)
        self.hype.draw(s)
        if self.overlay is not None:
            self.overlay.draw(s)
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
