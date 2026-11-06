"""Arcade kit shared by every game.

- 200-stage campaign helpers: boss every 10th stage, bonus stage on every x5, checkpoints 1/11/21/...
- Hype: banners, combo counter, FEVER gauge (x2 score), JACKPOT showers, screen flash, hit-stop, slow-mo.
- Boss health bar and the between-stage upgrade picker (3 cards, pick 1).

The iOS port mirrors this file in ios/MochiArcade/Engine/Arcade.swift - keep the two in step.
"""
import math
import random

import pygame

from mochi_arcade.gfx import H, W, col, draw_text, panel, sprite, text_width

STAGES = 200
HYPE_COLORS = ("hotpink", "orange", "yellow", "lime", "mint", "sky", "lavender")


def is_boss(n):
    return n % 10 == 0


def is_bonus(n):
    return n % 10 == 5


def checkpoint_of(n):
    return (n - 1) // 10 * 10 + 1


def tier(n):
    """0 for stages 1-10, 1 for 11-20 ... 19 for 191-200."""
    return (n - 1) // 10


def checkpoints(reach):
    """Start stages a player may pick: every checkpoint up to the furthest stage reached."""
    return list(range(1, max(1, min(reach, STAGES)) + 1, 10))


def rainbow(i, t=0.0):
    return HYPE_COLORS[(i + int(t * 12)) % len(HYPE_COLORS)]


def ease_out(x):
    return 1 - (1 - x) ** 3


class Hype:
    """Arcade 'juice' owned by a GameScene: call update(dt) every frame (it returns the game's dt, which is
    0 during hit-stop and scaled during slow-mo) and draw(s) after the game has rendered."""

    FEVER_TIME = 8.0           # per-game tuning: set scene.hype.FEVER_TIME / COMBO_TIME on the instance
    COMBO_TIME = 2.2

    def __init__(self, scene):
        self.scene = scene
        self.audio = scene.app.audio
        self.banners = []          # [text, sub, color, age, dur, rainbow, scale]
        self.flash_t = self.flash_dur = 0.0
        self.flash_c = "white"
        self.stop_t = 0.0
        self.slow_t = 0.0
        self.slow_f = 1.0
        self.combo = 0
        self.combo_t = 0.0
        self.best_combo = 0
        self.fever = 0.0           # gauge 0..1
        self.fever_t = 0.0         # seconds of FEVER left
        self.rain = []             # [x, y, vx, vy, kind, color, spin]
        self.t = 0.0
        self.combo_y = 12          # games can move the combo counter off their HUD

    # ------------------------------------------------------------------ state
    @property
    def fever_on(self):
        return self.fever_t > 0

    @property
    def mult(self):
        return 2 if self.fever_on else 1

    # ------------------------------------------------------------------ events
    def banner(self, text, sub=None, color="yellow", dur=1.5, rainbow=False, scale=2, sound=None):
        self.banners = [b for b in self.banners if b[0] != text]
        self.banners.append([text, sub, color, 0.0, dur, rainbow, scale])
        if sound:
            self.audio.play(sound)

    def flash(self, color="white", dur=0.18):
        self.flash_c, self.flash_t, self.flash_dur = color, dur, dur

    def hitstop(self, dur=0.06):
        self.stop_t = max(self.stop_t, dur)

    def slowmo(self, factor=0.35, dur=0.7):
        self.slow_f, self.slow_t = factor, dur

    def shower(self, n=40, kind="confetti"):
        """kind: confetti | coins | stars | hearts"""
        for _ in range(n):
            c = random.choice(HYPE_COLORS) if kind == "confetti" else ("yellow" if kind == "coins" else "white")
            self.rain.append([random.uniform(0, W), random.uniform(-80, -4), random.uniform(-14, 14),
                              random.uniform(30, 70), kind, c, random.uniform(0, 6)])

    def hit(self, n=1, fever=0.035):
        """A scoring action that keeps the combo alive. Returns the current combo count."""
        self.combo += n
        self.combo_t = self.COMBO_TIME
        self.best_combo = max(self.best_combo, self.combo)
        for m in (10, 25, 50, 100, 200, 300, 500):
            if self.combo - n < m <= self.combo:
                self.banner(f"{m} COMBO!", color="peach" if m < 50 else "hotpink", dur=1.0,
                            rainbow=m >= 100, sound="combo")
                if m >= 50:
                    self.shower(20 + m // 5, "stars")
        self.fever_add(fever * n)
        return self.combo

    def combo_bonus(self, base):
        """Extra points for the current combo (e.g. 10 per combo step, capped)."""
        return base * min(self.combo, 50)

    def keep_combo(self):
        """Keep the combo alive while the game decides (e.g. a chain is still resolving)."""
        if self.combo:
            self.combo_t = self.COMBO_TIME

    def break_combo(self):
        self.combo = 0
        self.combo_t = 0.0

    def fever_add(self, x):
        if self.fever_on:
            return
        self.fever = min(1.0, self.fever + x)
        if self.fever >= 1.0:
            self.start_fever()

    def start_fever(self, dur=None):
        self.fever = 0.0
        self.fever_t = dur or self.FEVER_TIME
        self.banner("FEVER!!", "SCORE X2", rainbow=True, dur=1.6, sound="fever")
        self.flash("yellow", 0.25)
        self.shower(50, "confetti")

    def jackpot(self, pts=0, sub=None):
        """The big moment: coin rain, rainbow banner, flash, slow-mo, fanfare."""
        self.banner("JACKPOT!!", sub or (f"+{pts * self.mult}" if pts else None), rainbow=True, dur=2.0,
                    sound="jackpot")
        self.flash("yellow", 0.3)
        self.slowmo(0.4, 0.8)
        self.shower(80, "coins")
        if pts:
            self.scene.add(pts)
        self.scene.app.shake(4, 0.4)

    def lucky(self, chance):
        return random.random() < chance

    # ------------------------------------------------------------------ frame
    def update(self, dt):
        self.t += dt
        if self.flash_t > 0:
            self.flash_t -= dt
        for b in self.banners:
            b[3] += dt
        self.banners = [b for b in self.banners if b[3] < b[4]]
        for r in self.rain:
            r[0] += r[2] * dt
            r[1] += r[3] * dt
            r[6] += dt * 8
        self.rain = [r for r in self.rain if r[1] < H + 8]
        if self.stop_t > 0:
            self.stop_t -= dt
            return 0.0
        gdt = dt
        if self.slow_t > 0:
            self.slow_t -= dt
            gdt = dt * self.slow_f
        if self.combo_t > 0:
            self.combo_t -= gdt
            if self.combo_t <= 0:
                self.combo = 0
        if self.fever_t > 0:
            self.fever_t -= gdt
            if self.fever_t <= 0:
                self.banner("FEVER END", color="lavender", dur=0.9, scale=1)
        return gdt

    def draw(self, s):
        t = self.t
        if self.fever_on:   # pulsing rainbow frame
            for i in range(2):
                c = col(rainbow(i, t))
                pygame.draw.rect(s, c, (i, i, W - 2 * i, H - 2 * i), 1)
            if self.fever_t < 2 and int(t * 8) % 2:
                pass
            else:
                draw_text(s, "FEVER", W - 3, H - 9, rainbow(0, t), align="right", shadow="ink")
        for x, y, _, _, kind, c, spin in self.rain:
            xi, yi = int(x), int(y)
            if kind == "coins":
                w = max(1, int(abs(math.cos(spin)) * 3))
                pygame.draw.rect(s, col("orange"), (xi - w, yi - 3, w * 2 + 1, 7))
                pygame.draw.rect(s, col("yellow"), (xi - w + 1, yi - 2, max(1, w * 2 - 1), 5))
            elif kind == "stars":
                s.fill(col(c), (xi, yi - 1, 1, 3))
                s.fill(col(c), (xi - 1, yi, 3, 1))
            elif kind == "hearts":
                s.blit(sprite("heart"), (xi - 3, yi - 3))
            else:
                s.fill(col(c), (xi, yi, 2 if int(spin) % 2 else 1, 2))
        if self.combo >= 3:
            txt = f"{self.combo} COMBO"
            draw_text(s, txt, W // 2, self.combo_y, "peach" if self.combo < 25 else rainbow(0, t), align="center")
            # remaining-time bar under the combo text
            w = int(text_width(txt) * max(0.0, self.combo_t) / self.COMBO_TIME)
            s.fill(col("peach"), (W // 2 - text_width(txt) // 2, self.combo_y + 8, w, 1))
        slot_y = None
        for b in self.banners:          # the oldest keeps its place, newer ones stack below it
            slot_y = self._draw_banner(s, *b, below=slot_y)
        if self.flash_t > 0 and self.scene.app.settings().get("shake", True):
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            r, g, bb = col(self.flash_c)
            ov.fill((r, g, bb, int(150 * self.flash_t / max(0.01, self.flash_dur))))
            s.blit(ov, (0, 0))

    def _draw_banner(self, s, text, sub, color, age, dur, rb, scale, below=None):
        # slide in from the right, hold, slide out to the left
        tin, tout = 0.18, 0.2
        w = text_width(text, scale)
        if age < tin:
            x = W + (W // 2 - W) * ease_out(age / tin)
        elif age > dur - tout:
            x = W // 2 - (W // 2 + w) * ease_out((age - (dur - tout)) / tout)
        else:
            x = W // 2
        y = 62 if scale >= 2 else 70
        hh = 8 * scale + (12 if sub else 6)
        if below is not None:
            y = below + 4
        band = pygame.Surface((W, hh), pygame.SRCALPHA)
        band.fill((12, 8, 24, 150))
        s.blit(band, (0, y - 4))
        if rb:
            x0 = int(x) - w // 2
            for i, ch in enumerate(text):
                dy = int(math.sin(self.t * 10 + i * 0.7) * 2)
                draw_text(s, ch, x0 + i * 6 * scale, y + dy, rainbow(i, self.t), scale, outline="ink", shadow=None)
        else:
            draw_text(s, text, int(x), y, color, scale, align="center", outline="ink", shadow=None)
        if sub:
            draw_text(s, sub, int(x), y + 8 * scale + 2, "white", align="center")
        return y - 4 + hh


def boss_bar(s, name, hp, maxhp, t=0.0, y=2, x=60, w=200):
    """Boss health bar (default: across the top of the screen)."""
    frac = max(0.0, min(1.0, hp / max(1, maxhp)))
    panel(s, (x, y, w, 12), fill="black", border="red", radius=3, shadow=False)
    draw_text(s, name, x + 4, y + 3, "white", shadow=None)
    x0 = x + 6 + text_width(name)
    bw = x + w - 4 - x0
    s.fill(col("darkgray"), (x0, y + 4, bw, 4))
    c = "red" if frac > 0.3 or int(t * 8) % 2 else "yellow"
    s.fill(col(c), (x0, y + 4, int(bw * frac), 4))
    s.fill(col("pink"), (x0, y + 4, int(bw * frac), 1))


class Upgrade:
    """One stat/ability a player can level up between stages. icon: sprite name or fn(surface, cx, cy, t)."""

    def __init__(self, uid, name, desc, color="mint", icon=None, max_level=5):
        self.id, self.name, self.desc, self.color, self.icon, self.max = uid, name, desc, color, icon, max_level


class UpgradePick:
    """Overlay: choose 1 of 3 upgrade cards. on_done(uid) is called with the choice."""

    def __init__(self, scene, pool, levels, on_done, title="POWER UP!", n=3):
        self.scene, self.levels, self.on_done, self.title = scene, levels, on_done, title
        avail = [u for u in pool if levels.get(u.id, 0) < u.max]
        random.shuffle(avail)
        self.cards = avail[:n]
        self.i = 0
        self.t = 0.0
        self.done = False
        scene.app.audio.play("levelup")
        if not self.cards:
            self.done = True
            on_done(None)

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        inp = self.scene.app.input
        if inp.hit("left"):
            self.i = (self.i - 1) % len(self.cards)
            self.scene.app.audio.play("move")
        if inp.hit("right"):
            self.i = (self.i + 1) % len(self.cards)
            self.scene.app.audio.play("move")
        if self.t > 0.4 and inp.hit("a", "start"):
            self.done = True
            u = self.cards[self.i]
            self.scene.app.audio.play("card")
            self.on_done(u.id)

    def draw(self, s):
        if self.done:
            return
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((12, 8, 24, 190))
        s.blit(ov, (0, 0))
        for i, ch in enumerate(self.title):
            dy = int(math.sin(self.t * 6 + i * 0.6) * 2)
            draw_text(s, ch, W // 2 - text_width(self.title, 2) // 2 + i * 12, 22 + dy, rainbow(i, self.t), 2,
                      outline="ink", shadow=None)
        n = len(self.cards)
        cw, gap = 88, 8
        x0 = W // 2 - (n * cw + (n - 1) * gap) // 2
        for k, u in enumerate(self.cards):
            sel = k == self.i
            appear = ease_out(min(1.0, max(0.0, self.t * 4 - k * 0.4)))
            x = x0 + k * (cw + gap)
            y = 50 + int((1 - appear) * 120) - (4 if sel else 0)
            panel(s, (x, y, cw, 112), fill="night" if not sel else "ink", border=u.color if sel else "darkgray")
            if sel and int(self.t * 6) % 2:
                pygame.draw.rect(s, col("white"), (x - 1, y - 1, cw + 2, 114), 1, border_radius=5)
            cx, cy = x + cw // 2, y + 24
            pygame.draw.circle(s, col(u.color), (cx, cy), 13)
            pygame.draw.circle(s, col("ink"), (cx, cy), 11)
            if callable(u.icon):
                u.icon(s, cx, cy, self.t)
            elif u.icon:
                sp = sprite(u.icon)
                s.blit(sp, (cx - sp.get_width() // 2, cy - sp.get_height() // 2))
            draw_text(s, u.name, cx, y + 44, u.color, align="center")
            for li, line in enumerate(u.desc.split("|")[:4]):
                draw_text(s, line, cx, y + 58 + li * 9, "white", align="center", shadow=None)
            lv = self.levels.get(u.id, 0)
            for p in range(u.max):
                c = "yellow" if p < lv else ("lime" if p == lv else "darkgray")
                s.fill(col(c), (cx - u.max * 4 + p * 8 + 1, y + 100, 6, 4))
        draw_text(s, "LEFT/RIGHT CHOOSE   A: TAKE IT!", W // 2, H - 12, "lavender", align="center", shadow=None)
