"""Menus and front-end scenes: boot, title, profiles, main menu, game select, options, scores, results."""
import math

import pygame

from mochi_arcade import TITLE, __version__, cute
from mochi_arcade.app import Scene
from mochi_arcade.gfx import (H, W, Particles, Stars, checker_bg, col, draw_text, draw_wavy, panel, render_text,
                              sprite, text_width)
from mochi_arcade.profiles import AVATARS, MAX_NAME

RAINBOW = ["pink", "peach", "yellow", "lime", "mint", "sky", "lavender"]


def mochi_avatar(s, x, y, color="white", t=0.0, scale=1):
    """The mochi bunny, tinted to the profile colour."""
    remap = None if color == "white" else {"w": {"pink": "p", "peach": "e", "mint": "m", "sky": "s", "lavender": "v",
                                                 "yellow": "y", "lime": "l"}.get(color, "w")}
    if remap and remap["w"] == "p":
        remap["p"] = "P"
    frame = int(t * 2) % 2
    s.blit(sprite("momo_idle", frame, remap=remap, scale=scale), (x, y))


def footer(s, text):
    s.fill(col("ink"), (0, H - 11, W, 11))
    draw_text(s, text, W // 2, H - 9, "lavender", align="center", shadow=None)


class Menu:
    """Vertical menu. items: dicts with label and kind action|choice|slider|toggle."""

    def __init__(self, items, x, y, width=150, spacing=13, center=False):
        self.items, self.x, self.y, self.w, self.sp, self.center = items, x, y, width, spacing, center
        self.i = 0

    def update(self, app, dt):
        inp, au = app.input, app.audio
        n = len(self.items)
        if inp.repeat("up", dt=dt):
            self.i = (self.i - 1) % n
            au.play("move")
        if inp.repeat("down", dt=dt):
            self.i = (self.i + 1) % n
            au.play("move")
        it = self.items[self.i]
        k = it.get("kind", "action")
        if k in ("choice", "slider", "toggle"):
            d = (1 if inp.repeat("right", dt=dt) else 0) - (1 if inp.repeat("left", dt=dt) else 0)
            if k == "toggle" and inp.hit("a", "start"):
                d = 1
            if d:
                cur = it["get"]()
                if k == "slider":
                    nv = max(it.get("min", 0), min(it.get("max", 10), cur + d))
                elif k == "toggle":
                    nv = not cur
                else:
                    vals = [c[0] for c in it["choices"]]
                    idx = vals.index(cur) if cur in vals else 0
                    nv = vals[(idx + d) % len(vals)]
                if nv != cur:
                    it["set"](nv)
                    au.play("move")
        elif inp.hit("a", "start"):
            au.play("select")
            it["on"]()

    def value_text(self, it):
        k = it.get("kind", "action")
        if k == "slider":
            v = it["get"]()
            return "#" * v + "." * (it.get("max", 10) - v)
        if k == "toggle":
            return "ON" if it["get"]() else "OFF"
        if k == "choice":
            cur = it["get"]()
            for v, lab in it["choices"]:
                if v == cur:
                    return lab
        return ""

    def draw(self, s, t):
        for n, it in enumerate(self.items):
            y = self.y + n * self.sp
            sel = n == self.i
            colr = "yellow" if sel else "white"
            label = it["label"]
            if self.center:
                draw_text(s, label, self.x, y, colr, align="center")
                if sel:
                    off = int(math.sin(t * 8) * 2)
                    w = text_width(label)
                    s.blit(sprite("mochi_icon"), (self.x - w // 2 - 13 + off, y))
                continue
            if sel:
                s.blit(sprite("mochi_icon"), (self.x - 12 + int(math.sin(t * 8) * 2), y))
            draw_text(s, label, self.x, y, colr)
            vt = self.value_text(it)
            if vt:
                k = it.get("kind")
                arrows = sel and k in ("choice", "slider")
                txt = ("{ " + vt + " }") if arrows else vt
                draw_text(s, txt, self.x + self.w, y, "mint" if sel else "lavender", align="right")


# ----------------------------------------------------------------------------- boot / title
class Boot(Scene):
    music = False

    def enter(self):
        self.todo = self.app.audio.pending_songs() if self.app.audio.ok else []
        self.total = max(1, len(self.todo))

    def update(self, dt):
        if self.todo:
            from mochi_arcade.audio import ensure_song
            ensure_song(self.todo.pop(0))
            return
        if self.t > 0.2:
            self.app.replace(Title(self.app), fade=True)

    def draw(self, s):
        s.fill(col("night"))
        draw_text(s, TITLE, W // 2, 80, "pink", 2, align="center", outline="ink")
        done = self.total - len(self.todo)
        draw_text(s, "WARMING UP THE MOCHI...", W // 2, 110, "lavender", align="center")
        pygame.draw.rect(s, col("lavender"), (100, 124, 120, 8), 1)
        s.fill(col("pink"), (102, 126, int(116 * done / self.total), 4))


class Title(Scene):
    music = "title"

    def enter(self):
        super().enter()
        self.stars = Stars(60)
        self.parts = Particles()

    def update(self, dt):
        self.stars.update(dt, 6)
        self.parts.update(dt)
        if int(self.t * 10) % 3 == 0:
            self.parts.sparkle(40 + (self.t * 97) % 240, 30 + (self.t * 53) % 40, RAINBOW[int(self.t * 7) % 7])
        inp = self.app.input
        if inp.hit("a", "start"):
            self.app.audio.play("select")
            store = self.app.store
            self.app.replace(ProfileSelect(self.app) if store.profiles else ProfileCreate(self.app, first=True))
        elif inp.hit("back") and self.t > 0.5:
            self.app.quit()

    def draw(self, s):
        s.fill(col("night"))
        self.stars.draw(s, self.t)
        # ground with a parade of the cast
        s.fill(col("deep"), (0, 150, W, 50))
        for x in range(0, W, 16):
            s.fill(col("ink"), (x + int(self.t * 20) % 16, 150, 8, 2))
        draw_wavy(s, "MOCHI", W // 2, 34, self.t, lambda i: ("pink", "peach", "yellow", "mint", "sky")[i % 5], 4,
                  amp=3)
        draw_wavy(s, "ARCADE", W // 2, 70, self.t + 1, "white", 3, amp=2)
        x0 = (self.t * 30) % (W + 120) - 60
        bob = abs(math.sin(self.t * 6)) * 6
        s.blit(sprite("momo_walk", int(self.t * 8), scale=1), (int(x0), 134 - int(bob)))
        cute.grump(s, int(x0) - 40, 134, self.t, flip=False)
        s.blit(sprite("kitty"), (int(x0) + 30, 128 + int(math.sin(self.t * 3) * 3)))
        for i, c in enumerate(("mint", "pink", "sky", "yellow")):
            cute.jelly_cell(s, int(x0) - 90 + i * 10, 140, 9, c, self.t, wobble=math.sin(self.t * 8 + i))
        self.parts.draw(s)
        if int(self.t * 2) % 2 == 0:
            draw_text(s, "PRESS START", W // 2, 108, "yellow", align="center")
        draw_text(s, f"V{__version__}", W - 4, 4, "darkgray", align="right", shadow=None)
        footer(s, "ENTER/Z: START   ESC: QUIT")


# ----------------------------------------------------------------------------- profiles
class ProfileSelect(Scene):
    music = "title"

    def enter(self):
        super().enter()
        store = self.app.store
        self.i = 0
        last = store.last()
        if last in store.profiles:
            self.i = store.profiles.index(last)
        self.confirm_delete = False

    def update(self, dt):
        inp, au, store = self.app.input, self.app.audio, self.app.store
        n = len(store.profiles) + 1
        if self.confirm_delete:
            if inp.hit("a", "start"):
                store.delete(store.profiles[self.i]["name"])
                au.play("back")
                self.confirm_delete = False
                self.i = 0
            elif inp.hit("b", "back"):
                self.confirm_delete = False
            return
        if inp.repeat("up", dt=dt) or inp.repeat("left", dt=dt):
            self.i = (self.i - 1) % n
            au.play("move")
        if inp.repeat("down", dt=dt) or inp.repeat("right", dt=dt):
            self.i = (self.i + 1) % n
            au.play("move")
        if inp.hit("a", "start"):
            au.play("select")
            if self.i == len(store.profiles):
                self.app.replace(ProfileCreate(self.app))
            else:
                p = store.profiles[self.i]
                store.select(p)
                self.app.profile = p
                self.app.apply_settings()
                self.app.replace(MainMenu(self.app))
        elif inp.hit("y") and self.i < len(store.profiles):
            self.confirm_delete = True
        elif inp.hit("back"):
            au.play("back")
            self.app.replace(Title(self.app))

    def draw(self, s):
        checker_bg(s, self.t, "night", "ink")
        draw_text(s, "WHO'S PLAYING?", W // 2, 14, "yellow", 2, align="center", outline="ink")
        store = self.app.store
        items = store.profiles + [None]
        for n, p in enumerate(items):
            col_i, row = n % 3, n // 3
            x, y = 22 + col_i * 96, 44 + row * 52
            sel = n == self.i
            panel(s, (x, y, 84, 44), fill="deep" if sel else "ink", border="yellow" if sel else "lavender")
            if p is None:
                draw_text(s, "+ NEW", x + 42, y + 18, "mint", align="center")
                continue
            mochi_avatar(s, x + 34, y + 4, p.get("avatar", "white"), self.t if sel else 0)
            draw_text(s, p["name"], x + 42, y + 24, "white", align="center")
            best = sum(g.get("best", 0) for g in p.get("games", {}).values())
            draw_text(s, f"{best}", x + 42, y + 33, "lavender", align="center", shadow=None)
        if self.confirm_delete:
            panel(s, (60, 80, 200, 40), fill="night", border="red")
            draw_text(s, f"DELETE {store.profiles[self.i]['name']}?", W // 2, 88, "red", align="center")
            draw_text(s, "Z: YES   X: NO", W // 2, 104, "white", align="center")
        footer(s, "ARROWS: CHOOSE  Z: OK  V: DELETE  ESC: BACK")


class ProfileCreate(Scene):
    music = "title"
    KEYS = ["ABCDEFGHIJ", "KLMNOPQRST", "UVWXYZ0123", "456789-!*<"]  # '<' = delete

    def __init__(self, app, first=False):
        super().__init__(app)
        self.first = first
        self.name = ""
        self.avatar = 0
        self.r, self.c = 0, 0  # r = -1 avatar row, 0..3 keys, 4 = OK button
        self.msg = ""

    def type_char(self, ch):
        if len(self.name) < MAX_NAME:
            self.name += ch
            self.app.audio.play("type")

    def finish(self):
        store = self.app.store
        if not self.name.strip():
            self.msg = "TYPE A NAME FIRST"
            self.app.audio.play("hurt")
            return
        p = store.create(self.name, AVATARS[self.avatar])
        if not p:
            self.msg = "NAME TAKEN OR TOO MANY"
            self.app.audio.play("hurt")
            return
        self.app.profile = p
        self.app.apply_settings()
        self.app.audio.play("win")
        self.app.replace(MainMenu(self.app))

    def update(self, dt):
        inp, au = self.app.input, self.app.audio
        # physical keyboard typing
        for ch in inp.text.upper():
            if ch.isalnum() or ch in "-!*":
                self.type_char(ch)
        if pygame.K_BACKSPACE in inp.raw:
            self.name = self.name[:-1]
            return
        if pygame.K_RETURN in inp.raw or pygame.K_KP_ENTER in inp.raw:
            self.finish()
            return
        if pygame.K_ESCAPE in inp.raw:
            au.play("back")
            self.app.replace(ProfileSelect(self.app) if self.app.store.profiles else Title(self.app))
            return
        # letters typed on a real keyboard (z, x, w, a, s, d...) must not double as menu actions
        if any(ch.isalnum() or ch in "-!*" for ch in inp.text):
            return
        if inp.repeat("up", dt=dt) and self.r > -1:
            self.r -= 1
            au.play("move")
        if inp.repeat("down", dt=dt) and self.r < 4:
            self.r += 1
            au.play("move")
        dx = (1 if inp.repeat("right", dt=dt) else 0) - (1 if inp.repeat("left", dt=dt) else 0)
        if dx:
            au.play("move")
            if self.r == -1:
                self.avatar = (self.avatar + dx) % len(AVATARS)
            elif 0 <= self.r < 4:
                self.c = (self.c + dx) % 10
        if inp.hit("a"):
            if self.r == 4:
                self.finish()
            elif self.r >= 0:
                ch = self.KEYS[self.r][self.c]
                if ch == "<":
                    self.name = self.name[:-1]
                else:
                    self.type_char(ch)
            else:
                self.r = 0
        if inp.hit("b"):
            self.name = self.name[:-1]

    def draw(self, s):
        checker_bg(s, self.t, "night", "ink")
        draw_text(s, "NEW PLAYER", W // 2, 10, "yellow", 2, align="center", outline="ink")
        # avatar picker
        sel = self.r == -1
        panel(s, (110, 30, 100, 30), fill="deep" if sel else "ink", border="yellow" if sel else "lavender")
        mochi_avatar(s, 152, 36, AVATARS[self.avatar], self.t)
        if sel:
            draw_text(s, "{", 118, 42, "yellow")
            draw_text(s, "}", 197, 42, "yellow")
        # name
        panel(s, (90, 66, 140, 16), fill="black", border="pink")
        shown = self.name + ("_" if int(self.t * 3) % 2 else " ")
        draw_text(s, shown, W // 2, 71, "white", align="center")
        # keyboard
        for r, row in enumerate(self.KEYS):
            for c, ch in enumerate(row):
                x, y = 70 + c * 18, 90 + r * 15
                on = self.r == r and self.c == c
                if on:
                    pygame.draw.rect(s, col("yellow"), (x - 3, y - 3, 13, 13), border_radius=2)
                label = "DEL" if ch == "<" else ch
                if ch == "<":
                    draw_text(s, "{", x, y, "black" if on else "red", shadow=None)
                else:
                    draw_text(s, label, x, y, "black" if on else "white", shadow=None)
        ok = self.r == 4
        panel(s, (130, 152, 60, 14), fill="pink" if ok else "ink", border="yellow" if ok else "lavender")
        draw_text(s, "OK!", W // 2, 156, "black" if ok else "white", align="center", shadow=None)
        if self.msg:
            draw_text(s, self.msg, W // 2, 172, "red", align="center")
        footer(s, "TYPE A NAME (OR ARROWS+SPACE)  ENTER: DONE")


# ----------------------------------------------------------------------------- main menu
class MainMenu(Scene):
    music = "title"

    def enter(self):
        super().enter()
        a = self.app
        self.menu = Menu([
            {"label": "PLAY", "on": lambda: a.replace(GameSelect(a))},
            {"label": "OPTIONS", "on": lambda: a.push(Options(a))},
            {"label": "HIGH SCORES", "on": lambda: a.push(Scores(a))},
            {"label": "SWITCH PLAYER", "on": lambda: a.replace(ProfileSelect(a))},
            {"label": "QUIT", "on": a.quit},
        ], W // 2, 96, center=True, spacing=14)
        self.stars = Stars(50, seed=9)

    def update(self, dt):
        self.stars.update(dt, 5)
        self.menu.update(self.app, dt)
        if self.app.input.hit("back"):
            self.app.audio.play("back")
            self.app.replace(ProfileSelect(self.app))

    def draw(self, s):
        s.fill(col("night"))
        self.stars.draw(s, self.t)
        draw_wavy(s, TITLE, W // 2, 22, self.t, lambda i: RAINBOW[i % 7], 2, amp=2)
        p = self.app.profile
        panel(s, (110, 46, 100, 36), fill="ink", border="pink")
        mochi_avatar(s, 120, 56, p.get("avatar", "white"), self.t)
        draw_text(s, "HI,", 142, 56, "lavender", shadow=None)
        draw_text(s, p["name"], 142, 66, "white")
        self.menu.draw(s, self.t)
        footer(s, "ARROWS: MOVE   Z/ENTER: OK   ESC: BACK")


# ----------------------------------------------------------------------------- game select / setup
def progress_card(s, best, plays, reach, t):
    """Campaign progress under the game carousel: stage reached, a 200-stage bar with boss marks, best score."""
    from mochi_arcade.arcade import STAGES
    bx, by, bw = 64, 160, 192
    reach = max(1, min(reach, STAGES))
    draw_text(s, f"STAGE {reach}/{STAGES}", bx, by - 10, "yellow", shadow="ink")
    draw_text(s, f"BEST {best}", bx + bw, by - 10, "mint", align="right", shadow="ink")
    s.fill(col("black"), (bx - 1, by - 1, bw + 2, 7))
    s.fill(col("darkgray"), (bx, by, bw, 5))
    fill = int(bw * reach / STAGES)
    s.fill(col("lime"), (bx, by, fill, 5))
    s.fill(col("white"), (bx, by, fill, 1))
    for k in range(1, STAGES // 10 + 1):   # boss stages: gold once beaten
        x = bx + int(bw * k * 10 / STAGES) - 1
        s.fill(col("yellow" if k * 10 < reach else "gray"), (x, by - 2, 2, 9))
    if plays == 0 and int(t * 3) % 2 == 0:
        draw_text(s, "NEW!", bx + bw // 2, by + 9, "hotpink", align="center", shadow="ink")
    elif plays:
        draw_text(s, f"BOSSES {max(0, (reach - 1) // 10)}  PLAYS {plays}", bx + bw // 2, by + 9, "lavender",
                  align="center", shadow=None)


class GameSelect(Scene):
    music = "title"

    def __init__(self, app, index=0):
        super().__init__(app)
        self.i = index
        self.slide = float(index)

    def update(self, dt):
        from mochi_arcade.games import GAMES
        inp, au = self.app.input, self.app.audio
        if inp.repeat("left", dt=dt):
            self.i = (self.i - 1) % len(GAMES)
            au.play("move")
        if inp.repeat("right", dt=dt):
            self.i = (self.i + 1) % len(GAMES)
            au.play("move")
        self.slide += (self.i - self.slide) * min(1, dt * 12)
        if inp.hit("a", "start"):
            au.play("select")
            self.app.replace(GameSetup(self.app, self.i))
        elif inp.hit("back"):
            au.play("back")
            self.app.replace(MainMenu(self.app))

    def draw(self, s):
        from mochi_arcade.games import GAMES
        info = GAMES[self.i]
        checker_bg(s, self.t, "night", info.bg, size=20, speed=10)
        draw_text(s, "PICK A GAME", W // 2, 8, "white", 2, align="center", outline="ink")
        for n, g in enumerate(GAMES):
            off = n - self.slide
            if abs(off) > 2.2:
                continue
            cx = W // 2 + int(off * 120)
            sel = n == self.i
            w, h = (120, 96) if sel else (100, 80)
            r = pygame.Rect(0, 0, w, h)
            r.center = (cx, 82)
            panel(s, r, fill="black", border="yellow" if sel else "darkgray")
            prev = pygame.Surface((w - 8, h - 22))
            g.preview(prev, self.t if sel else 0)
            s.blit(prev, (r.x + 4, r.y + 4))
            draw_text(s, g.title, cx, r.bottom - 14, "yellow" if sel else "gray", align="center", shadow=None)
        draw_text(s, info.tagline, W // 2, 138, "white", align="center")
        g = self.app.store.game(self.app.profile, info.id)
        progress_card(s, g["best"], g["plays"], g.get("reach", 1), self.t)
        draw_text(s, "{", 8, 78, "yellow")
        draw_text(s, "}", W - 14, 78, "yellow")
        footer(s, "LEFT/RIGHT: CHOOSE   Z: SELECT   ESC: BACK")


class GameSetup(Scene):
    music = "title"

    def __init__(self, app, index):
        super().__init__(app)
        from mochi_arcade.games import GAMES
        self.index = index
        self.info = GAMES[index]
        g = app.store.game(app.profile, self.info.id)
        self.opts = {k: g["options"].get(k, default) for k, _, _, default in self.info.options}
        items = []
        for key, label, choices, _ in self.info.options:
            if choices == "checkpoints":   # start stage: every checkpoint unlocked so far (arcade.py)
                from mochi_arcade.arcade import checkpoints
                choices = [(c, str(c)) for c in checkpoints(g.get("reach", 1))]
                if self.opts[key] not in [c for c, _ in choices]:
                    self.opts[key] = choices[-1][0]
            items.append({"label": label, "kind": "choice", "choices": choices,
                          "get": (lambda k=key: self.opts[k]), "set": (lambda v, k=key: self.opts.__setitem__(k, v))})
        items.append({"label": "HOW TO PLAY", "on": self.toggle_help})
        items.append({"label": "START!", "on": self.start})
        self.menu = Menu(items, 70, 60, width=180, spacing=14)
        self.menu.i = len(items) - 1
        self.help = False

    def toggle_help(self):
        self.help = not self.help

    def start(self):
        a = self.app
        g = a.store.game(a.profile, self.info.id)
        g["options"] = dict(self.opts)
        a.save()
        a.replace(self.info.load()(a, self.info, dict(self.opts)))

    def update(self, dt):
        if self.help:
            if self.app.input.hit("a", "b", "start", "back"):
                self.help = False
            return
        self.menu.update(self.app, dt)
        if self.app.input.hit("back"):
            self.app.audio.play("back")
            self.app.replace(GameSelect(self.app, self.index))

    def draw(self, s):
        checker_bg(s, self.t, "night", self.info.bg, size=20, speed=6)
        draw_text(s, self.info.title, W // 2, 12, "yellow", 2, align="center", outline="ink")
        draw_text(s, self.info.tagline, W // 2, 34, "white", align="center")
        panel(s, (52, 52, 216, 14 + 14 * len(self.menu.items)), fill="ink", border="lavender")
        self.menu.draw(s, self.t)
        if self.help:
            panel(s, (20, 24, 280, 160), fill="night", border="yellow")
            draw_text(s, "HOW TO PLAY", W // 2, 32, "yellow", align="center")
            for n, line in enumerate(self.info.howto):
                draw_text(s, line, 30, 48 + n * 11, "white", shadow=None)
        footer(s, "UP/DOWN: MOVE  LEFT/RIGHT: CHANGE  Z: OK  ESC: BACK")


# ----------------------------------------------------------------------------- options / scores / result
class Options(Scene):
    music = False

    def enter(self):
        a = self.app
        st = a.profile["settings"]

        def setter(k):
            def f(v):
                st[k] = v
                a.apply_settings()
                a.save()
            return f
        self.menu = Menu([
            {"label": "MUSIC", "kind": "slider", "get": lambda: st["music"], "set": setter("music")},
            {"label": "SOUND FX", "kind": "slider", "get": lambda: st["sfx"],
             "set": lambda v: (setter("sfx")(v), a.audio.play("fruit"))},
            {"label": "FULLSCREEN", "kind": "toggle", "get": lambda: st["fullscreen"], "set": setter("fullscreen")},
            {"label": "SCANLINES", "kind": "toggle", "get": lambda: st["scanlines"], "set": setter("scanlines")},
            {"label": "SCREEN SHAKE", "kind": "toggle", "get": lambda: st["shake"], "set": setter("shake")},
            {"label": "BACK", "on": lambda: a.pop()},
        ], 70, 56, width=180, spacing=16)

    def update(self, dt):
        self.menu.update(self.app, dt)
        if self.app.input.hit("back"):
            self.app.audio.play("back")
            self.app.pop()

    def draw(self, s):
        checker_bg(s, self.t, "night", "ink")
        draw_text(s, "OPTIONS", W // 2, 14, "yellow", 2, align="center", outline="ink")
        panel(s, (50, 46, 220, 106), fill="ink", border="lavender")
        self.menu.draw(s, self.t)
        draw_text(s, "F11: FULLSCREEN   F12: SCREENSHOT", W // 2, 164, "lavender", align="center")
        footer(s, "UP/DOWN: MOVE   LEFT/RIGHT: CHANGE   ESC: BACK")


class Scores(Scene):
    music = False

    def __init__(self, app):
        super().__init__(app)
        self.i = 0

    def update(self, dt):
        from mochi_arcade.games import GAMES
        inp = self.app.input
        if inp.repeat("left", dt=dt):
            self.i = (self.i - 1) % len(GAMES)
            self.app.audio.play("move")
        if inp.repeat("right", dt=dt):
            self.i = (self.i + 1) % len(GAMES)
            self.app.audio.play("move")
        if inp.hit("back", "a", "start", "b"):
            self.app.audio.play("back")
            self.app.pop()

    def draw(self, s):
        from mochi_arcade.games import GAMES
        info = GAMES[self.i]
        checker_bg(s, self.t, "night", info.bg)
        draw_text(s, "HIGH SCORES", W // 2, 10, "yellow", 2, align="center", outline="ink")
        draw_text(s, "{ " + info.title + " }", W // 2, 34, "white", align="center")
        panel(s, (60, 48, 200, 124), fill="ink", border="lavender")
        g = self.app.store.game(self.app.profile, info.id)
        if not g["top"]:
            draw_text(s, "NO SCORES YET!", W // 2, 100, "lavender", align="center")
        for n, e in enumerate(g["top"][:9]):
            y = 56 + n * 12
            c = ("yellow", "white", "peach")[n] if n < 3 else "lavender"
            draw_text(s, f"{n + 1}.", 72, y, c)
            draw_text(s, str(e["score"]), 170, y, c, align="right")
            draw_text(s, e.get("detail", "")[:9], 250, y, "gray", align="right", shadow=None)
        footer(s, "LEFT/RIGHT: GAME   ESC: BACK")


class Result(Scene):
    music = False

    def __init__(self, app, info, options, score, cleared=False, detail=""):
        super().__init__(app)
        self.info, self.options, self.score, self.cleared, self.detail = info, options, score, cleared, detail
        self.new_best, self.rank = app.store.record(app.profile, info.id, score, detail)
        self.parts = Particles()
        app.audio.stop_music()
        app.audio.play("win" if (cleared or self.new_best) else "gameover")

    ROLL = 1.2   # seconds for the score to count up

    def update(self, dt):
        self.parts.update(dt)
        if self.t - dt < self.ROLL <= self.t and self.score > 0:
            self.app.audio.play("coin")
            if self.new_best:
                self.app.audio.play("jackpot")
                for k in range(6):
                    self.parts.burst(40 + k * 48, 90, 14, RAINBOW, 90, 1.1)
        if self.new_best and self.t > self.ROLL and int(self.t * 20) % 2 == 0:
            self.parts.burst(W // 2 + (self.t * 131) % 160 - 80, 70, 3, RAINBOW, 50, 0.8)
        inp = self.app.input
        if self.t > 0.6:
            if inp.hit("a", "start"):
                self.app.audio.play("select")
                self.app.replace(self.info.load()(self.app, self.info, dict(self.options)))
            elif inp.hit("b", "back"):
                self.app.audio.play("back")
                from mochi_arcade.games import GAMES
                self.app.replace(GameSelect(self.app, GAMES.index(self.info)))

    def draw(self, s):
        checker_bg(s, self.t, "night", self.info.bg, speed=4)
        title = "STAGE CLEAR!" if self.cleared else "GAME OVER"
        draw_wavy(s, title, W // 2, 30, self.t, "yellow" if self.cleared else "pink", 2, amp=2)
        panel(s, (70, 60, 180, 90), fill="ink", border="lavender")
        draw_text(s, "SCORE", W // 2, 70, "lavender", align="center")
        k = min(1.0, self.t / self.ROLL)
        shown = int(self.score * (1 - (1 - k) ** 3))
        draw_text(s, str(shown), W // 2, 82, "white" if k < 1 else "yellow", 2, align="center", outline="black")
        if self.detail:
            draw_text(s, self.detail, W // 2, 104, "mint", align="center")
        g = self.app.store.game(self.app.profile, self.info.id)
        if self.new_best and self.t > self.ROLL:
            for i, ch in enumerate("NEW BEST!"):
                draw_text(s, ch, W // 2 - 27 + i * 6, 118 + int(math.sin(self.t * 8 + i) * 2), RAINBOW[(i + int(self.t * 10)) % 7])
        elif self.new_best:
            pass
        else:
            draw_text(s, f"BEST {g['best']}", W // 2, 118, "lavender", align="center")
        if self.rank:
            draw_text(s, f"RANK #{self.rank}", W // 2, 132, "peach", align="center")
        self.parts.draw(s)
        footer(s, "Z: PLAY AGAIN   X/ESC: GAMES")
