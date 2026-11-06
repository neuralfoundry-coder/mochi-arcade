"""ROOFTOP RUN bosses (every 10th stage): GULLY, BRUNO the guard dog, SGT. COO's pigeon squad, RUMBLE the
thundercloud and GULLY's fish blimp. Each keeps pace with Tora above the arena, throws telegraphed attacks, then
gets worn out and lands on the roof ahead - that's the moment to jump on it.  lv 0..3 = each lap of the five
bosses mixes in more patterns, fires faster and from lv 2 only a stomp from above counts.
Mirrored in ios/MochiArcade/Games/RooftopRunBoss.swift.
"""
import math
import random

import pygame

from mochi_arcade import cute
from mochi_arcade.gfx import H, W, col, draw_text, sprite

PATTERNS = {
    "gully": [["drop", "dive", "dive"],
              ["drop", "dive", "feathers", "dive"],
              ["feathers", "dive", "drop", "dive"],
              ["feathers", "dive", "dive", "feathers", "dive"]],
    "bruno": [["bark", "bone", "bark"],
              ["bark", "bone", "charge", "bark"],
              ["bark", "charge", "bone", "charge"],
              ["bone", "charge", "bark", "bone", "charge"]],
    "squad": [["crumbs", "dive", "dive"],
              ["crumbs", "dive", "crumbs", "dive"],
              ["dive", "crumbs", "dive", "dive"],
              ["crumbs", "dive", "dive", "crumbs", "dive"]],
    "storm": [["bolt", "rain", "bolt"],
              ["bolt", "gust", "bolt", "rain"],
              ["bolt", "bolt", "gust", "bolt"],
              ["rain", "bolt", "gust", "bolt", "bolt"]],
    "blimp": [["cannon", "anchor", "cannon"],
              ["cannon", "minis", "anchor", "cannon"],
              ["minis", "cannon", "anchor", "minis"],
              ["cannon", "minis", "anchor", "cannon", "minis"]],
}
HOME = {"gully": (232, 52), "bruno": (236, 0), "squad": (214, 62), "storm": (220, 40), "blimp": (214, 42)}


class Shot:
    __slots__ = ("k", "x", "y", "vx", "vy", "t", "life", "state", "gy")

    def __init__(self, k, x, y, vx=0.0, vy=0.0, life=3.0):
        self.k, self.x, self.y, self.vx, self.vy, self.t, self.life = k, x, y, vx, vy, 0.0, life
        self.state = 0
        self.gy = 0.0

    def rect(self):
        k, x, y = self.k, self.x, self.y
        if k == "shell":
            return (x - 4, y - 6, 8, 6) if self.state else (x - 4, y - 4, 8, 8)
        if k in ("feather", "crumb", "hail"):
            return (x - 2, y - 2, 5, 5)
        if k == "wave":
            return (x - 3, y - 11, 7, 11)
        if k == "bone":
            return (x - 5, y - 4, 10, 4) if self.state else (x - 5, y - 3, 10, 6)
        if k == "bolt":
            return (x - 8, self.gy - 16, 17, 16) if self.state == 1 else None
        if k == "debris":
            return (x - 5, y - 9, 10, 9)
        if k == "fishbone":
            return (x - 4, y - 3, 9, 6)
        if k == "anchor":
            return (x - 6, y - 12, 12, 12)
        if k == "mini":
            return (x - 6, y - 4, 12, 8)
        return None


class Boss:
    def __init__(self, scene, spec):
        self.sc = scene
        self.kind, self.name = spec["kind"], spec["name"]
        self.lv = spec["lv"]
        self.final = spec.get("final", False)
        self.rate = spec["rate"]
        self.hp = self.maxhp = spec["hp"]
        self.need_stomp = self.lv >= 2
        self.state = "enter"
        self.t = 0.0            # time in state
        self.at = 0.0           # time in the current attack
        hx, hy = HOME[self.kind]
        self.sx, self.sy = 360.0, float(hy)    # screen position while airborne
        self.wx, self.wy = 0.0, 0.0             # world position while dazed on the roof
        self.flash = 0.0
        self.queue = []
        self.act = None
        self.shots = []
        self.n_fired = 0
        self.tx, self.ty = 0.0, 0.0             # attack target (world)
        self.weather = 0.0                      # storm rain / gust slow-down left
        self.gust = False
        self.squad = []
        if self.kind == "squad":
            n = 3 + self.lv
            for i in range(n):
                self.squad.append({"dx": (i % 3) * 22 - 22 + (i // 3) * 11, "dy": (i // 3) * 16 - 8 + (i % 2) * 6,
                                   "alive": True, "back": 0.0})
            self.hp = self.maxhp = spec["hp"] + n - 3
        self.diver = -1         # squad member index doing the current dive (-1 = sergeant)
        self.by, self.bvy, self.bground = 0.0, 0.0, True   # bruno's feet (world) and hop
        self.dive_y = 0.0
        self.dive_x = 0.0

    # ------------------------------------------------------------------ helpers
    @property
    def cam(self):
        return self.sc.cam

    def world(self):
        """(x, y) of the boss body in world space."""
        if self.state in ("dazed", "hit"):
            return self.wx, self.wy
        return self.cam + self.sx, self.sy

    def speed(self):
        return 1.0 + 0.15 * self.lv

    def sergeant_only(self):
        return self.kind == "squad" and not any(m["alive"] for m in self.squad)

    def new_queue(self):
        pat = PATTERNS[self.kind][min(3, self.lv)][:]
        if self.final:          # the very last fight throws one more volley per round
            pat = pat + ["anchor"]
        self.queue = pat

    # ------------------------------------------------------------------ update
    def update(self, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.weather = max(0.0, self.weather - dt)
        hx, hy = HOME[self.kind]
        if self.kind == "bruno":
            self.bruno_feet(dt)
        if self.state == "enter":
            self.sx += (hx - self.sx) * min(1.0, dt * 2.5)
            if self.t > 2.2 and self.sc.state == "play":
                self.state = "fight"
                self.t = 0.0
                self.new_queue()
        elif self.state == "fight":
            self.bob(dt, hx, hy)
            if self.act is None:
                if self.queue:
                    self.act = self.queue.pop(0)
                    self.at = 0.0
                    self.n_fired = 0
                    self.start_act()
                else:
                    self.land()
            else:
                self.at += dt * self.rate
                self.run_act(dt)
        elif self.state == "dazed":
            self.wy = self.sc.roof_y_at(self.wx) or self.wy
            limit = max(1.6, 3.0 - 0.3 * self.lv)
            if self.t > limit or self.sc.body.x > self.wx + 60:
                self.take_off()
        elif self.state == "hit":
            if self.t > 0.5:
                self.take_off()
        elif self.state == "up":
            self.sx += (hx - self.sx) * min(1.0, dt * 3)
            self.sy += (hy - self.sy) * min(1.0, dt * 3)
            if self.t > 1.0:
                self.state = "fight"
                self.t = 0.0
                self.new_queue()
        elif self.state == "dead":
            self.sy += 60 * dt
            self.sx += 30 * dt
        for m in self.squad:
            m["back"] = max(0.0, m["back"] - dt)
        self.update_shots(dt)

    def bob(self, dt, hx, hy):
        if self.act in ("dive", "charge"):
            return
        k = 0.6 if self.kind == "storm" else 1.0
        self.sx += (hx + math.sin(self.t * 0.9) * 14 * k - self.sx) * min(1.0, dt * 3)
        if self.kind != "bruno":
            self.sy += (hy + math.sin(self.t * 2.1) * 6 - self.sy) * min(1.0, dt * 3)

    def bruno_feet(self, dt):
        x = self.cam + self.sx if self.state not in ("dazed", "hit") else self.wx
        g = self.sc.roof_y_at(x)
        ahead = self.sc.roof_y_at(x + 22)
        if self.bground:
            if g is None:
                self.bground = False
                self.bvy = 0.0
            else:
                self.by = g
                if ahead is None:
                    self.bground = False
                    self.bvy = -230.0
        if not self.bground:
            self.bvy += 900 * dt
            self.by += self.bvy * dt
            if g is not None and self.bvy > 0 and self.by >= g - 1:
                self.by, self.bground = g, True
            if self.by > H + 20:          # missed the roof: pop back up on the next one
                nxt = self.sc.next_roof(x)
                self.by, self.bvy, self.bground = (nxt.y, 0.0, True) if nxt else (150.0, 0.0, True)
        if self.state not in ("dazed", "hit"):
            self.sy = self.by

    def land(self):
        """Worn out: settle on the roof ahead until Tora jumps on it (or runs past)."""
        x = self.cam + 290
        r = self.sc.roof_y_at(x)
        k = 0
        while r is None and k < 30:
            x += 10
            r = self.sc.roof_y_at(x)
            k += 1
        self.wx, self.wy = x, (r if r is not None else 150)
        self.state = "dazed"
        self.t = 0.0
        self.act = None
        if self.kind == "squad":
            self.diver = -1
        self.sc.boss_landed()

    def take_off(self):
        self.sx = self.wx - self.cam
        self.sy = self.wy - 20 if self.kind != "bruno" else self.by
        self.state = "up"
        self.t = 0.0

    # ------------------------------------------------------------------ attacks
    def start_act(self):
        a = self.act
        b = self.sc.body
        if a == "dive":
            low = random.random() < 0.5
            ground = self.sc.roof_y_at(b.x) or b.y
            self.dive_y = ground - (6 if low else 17)
            if self.kind == "squad":
                alive = [i for i, m in enumerate(self.squad) if m["alive"]]
                self.diver = random.choice(alive) if alive else -1
        elif a == "charge":
            self.dive_x = self.sx
        elif a in ("bolt",):
            self.tx = b.x + random.uniform(140, 190) * self.sc.speed / 100
            self.ty = self.sc.roof_y_at(self.tx) or 150
            sh = Shot("bolt", self.tx, self.ty, life=1.6)
            sh.gy = self.ty
            self.shots.append(sh)
        elif a in ("rain", "gust"):
            self.weather = 2.4
            self.gust = a == "gust"

    def run_act(self, dt):
        a, at = self.act, self.at
        bx, by = self.world()
        tora = self.sc.body
        tele = max(0.35, 0.8 - 0.1 * self.lv)
        if a == "drop":                     # GULLY drops clam shells (they roll along the roof)
            if at > tele and self.n_fired < 1 + self.lv and at > tele + self.n_fired * 0.35:
                self.n_fired += 1
                self.shots.append(Shot("shell", bx, by + 6, self.sc.speed * 0.6, 0.0, 4.0))
                self.sc.sfx("pop")
            if at > tele + 1.4:
                self.act = None
        elif a == "feathers":               # aimed feather darts
            if at > tele and self.n_fired == 0:
                self.n_fired = 1
                ax, ay = tora.x + 60, tora.y - 8
                base = math.atan2(ay - by, ax - bx)
                for k in (-1, 0, 1)[: 2 + min(1, self.lv)] if self.lv < 2 else (-1, 0, 1):
                    ang = base + k * 0.22
                    self.shots.append(Shot("feather", bx, by, math.cos(ang) * 140 + self.sc.speed * 0.4,
                                           math.sin(ang) * 140, 3.0))
                self.sc.sfx("shoot")
            if at > tele + 1.0:
                self.act = None
        elif a == "dive":                   # swoop across at head or paw height (slide or jump)
            if at < tele:
                return
            if self.n_fired == 0:
                self.n_fired = 1
                self.dive_x = 330.0
                self.sc.sfx("jump")
            self.dive_x -= 250 * self.speed() * dt
            if not (self.kind == "squad" and self.diver >= 0):
                self.sx, self.sy = self.dive_x, self.dive_y
            if self.dive_x < -40:
                if self.kind == "squad":
                    if self.diver >= 0:
                        self.act = None     # the pigeon rejoins the squad from above
                        self.squad[self.diver]["back"] = 1.0
                        self.diver = -1
                    else:
                        self.act = None
                else:
                    self.sx, self.sy = 340.0, HOME[self.kind][1]
                    self.act = None
        elif a == "bark":                   # BRUNO: a shock-wave that runs along the roof
            if at > tele and self.n_fired == 0:
                self.n_fired = 1
                self.shots.append(Shot("wave", bx - 12, self.by - 1, -150.0 + self.sc.speed, 0.0, 3.0))
                self.sc.sfx("explode")
            if at > tele + 0.9:
                self.act = None
        elif a == "bone":                   # lobbed bone that lands ahead of Tora and lies there
            if at > tele and self.n_fired < 1 + (self.lv >= 2):
                self.n_fired += 1
                land_x = tora.x + random.uniform(120, 170) * self.sc.speed / 100
                tt = 1.0
                self.shots.append(Shot("bone", bx, by - 16, (land_x - bx) / tt, -260.0, 3.2))
                self.sc.sfx("jump")
            if at > tele + 1.2:
                self.act = None
        elif a == "charge":                 # BRUNO charges back across the roof - jump over him
            if at < tele + 0.3:
                return
            if self.n_fired == 0:
                self.n_fired = 1
                self.sc.sfx("explode")
            self.sx -= 230 * self.speed() * dt
            if self.sx < -50:
                self.sx = 360.0
                self.act = None
        elif a == "crumbs":                 # the squad drops bread crumbs
            if at > tele and self.n_fired < 4 + self.lv:
                if at > tele + self.n_fired * 0.18:
                    self.n_fired += 1
                    x = tora.x + random.uniform(60, 220)
                    self.shots.append(Shot("crumb", x, 30.0, self.sc.speed * 0.2, 110.0 + 20 * self.lv, 3.0))
                    self.sc.sfx("pop")
            if at > tele + 1.6:
                self.act = None
        elif a == "bolt":
            if at > 1.9:
                self.act = None
        elif a in ("rain", "gust"):
            if self.n_fired < 3 + self.lv and at > 0.5 + self.n_fired * 0.5:
                self.n_fired += 1
                if a == "rain":
                    for _ in range(3):
                        x = tora.x + random.uniform(40, 260)
                        self.shots.append(Shot("hail", x, 20.0, self.sc.speed * 0.3, 140.0, 3.0))
                else:
                    gx = self.cam + W + 10
                    gy = self.sc.roof_y_at(gx) or 150
                    self.shots.append(Shot("debris", gx, gy, -90.0, 0.0, 4.0))
            if at > 2.6:
                self.act = None
        elif a == "cannon":                 # BLIMP: fish-bone shells lobbed at Tora
            if at > tele and self.n_fired < 2 + (self.lv >= 2):
                if at > tele + self.n_fired * 0.45:
                    self.n_fired += 1
                    land_x = tora.x + random.uniform(70, 160) * self.sc.speed / 100
                    self.shots.append(Shot("fishbone", bx - 20, by + 10, (land_x - bx) / 1.0, -120.0, 2.4))
                    self.sc.sfx("shoot")
            if at > tele + 1.5:
                self.act = None
        elif a == "anchor":
            if at > tele and self.n_fired == 0:
                self.n_fired = 1
                self.shots.append(Shot("anchor", bx, by + 14, self.sc.speed, 60.0, 4.5))
                self.sc.sfx("tin")
            if at > tele + 1.2:
                self.act = None
        elif a == "minis":
            if at > tele and self.n_fired < 2 + (self.lv >= 2):
                if at > tele + self.n_fired * 0.6:
                    self.n_fired += 1
                    ground = self.sc.roof_y_at(tora.x + 200) or tora.y
                    y = ground - (6 if (self.n_fired + self.lv) % 2 else 17)
                    sh = Shot("mini", self.cam + W + 10, y, self.sc.speed - 220.0, 0.0, 3.0)
                    sh.gy = y
                    self.shots.append(sh)
                    self.sc.sfx("jump")
            if at > tele + 2.0:
                self.act = None

    def update_shots(self, dt):
        sc = self.sc
        for s in self.shots:
            s.t += dt
            k = s.k
            if k == "shell":
                if s.state == 0:
                    s.vy += 600 * dt
                    s.x += s.vx * dt
                    s.y += s.vy * dt
                    g = sc.roof_y_at(s.x)
                    if g is not None and s.y >= g and s.y - s.vy * dt <= g + 2:
                        s.y, s.state, s.vx = g, 1, -55.0
                else:
                    s.x += s.vx * dt
                    g = sc.roof_y_at(s.x)
                    if g is None:
                        s.state, s.vy = 0, 0.0
            elif k in ("feather", "crumb", "hail", "mini"):
                s.x += s.vx * dt
                s.y += s.vy * dt
                g = sc.roof_y_at(s.x)
                if k != "mini" and g is not None and s.y >= g:
                    s.life = 0
                    sc.parts.burst(s.x, g - 2, 4, ("white", "cream"), 30, 0.3)
            elif k == "wave":
                s.x += s.vx * dt
            elif k in ("bone", "fishbone"):
                if s.state == 0:
                    s.vy += 520 * dt
                    s.x += s.vx * dt
                    s.y += s.vy * dt
                    g = sc.roof_y_at(s.x)
                    if g is not None and s.vy > 0 and s.y >= g:
                        if k == "fishbone":
                            s.life = 0
                            sc.parts.burst(s.x, g - 2, 8, ("white", "gray", "sky"), 50, 0.4)
                            sc.sfx("brick")
                        else:
                            s.y, s.state, s.vx, s.life = g, 1, 0.0, min(s.life, s.t + 1.6)
            elif k == "bolt":
                if s.state == 0 and s.t > max(0.5, 0.95 - 0.12 * self.lv):
                    s.state = 1
                    sc.sfx("boom")
                    sc.app.shake(3, 0.2)
                    sc.hype.flash("white", 0.12)
                elif s.state == 1 and s.t > max(0.5, 0.95 - 0.12 * self.lv) + 0.45:
                    s.state, s.life = 2, 0
            elif k == "debris":
                s.x += s.vx * dt
                g = sc.roof_y_at(s.x)
                s.y = g if g is not None else s.y + 200 * dt
            elif k == "anchor":
                if s.state == 0:
                    s.vy += 700 * dt
                    s.y += s.vy * dt
                    s.x += s.vx * dt
                    g = sc.roof_y_at(s.x)
                    if g is not None and s.y >= g:
                        s.y, s.state, s.vx = g, 1, -80.0
                        sc.sfx("tin")
                        sc.app.shake(2, 0.15)
                else:
                    s.x += s.vx * dt
                    g = sc.roof_y_at(s.x)
                    if g is None:
                        s.state, s.vy = 0, 0.0
                    else:
                        s.y = g
        self.shots = [s for s in self.shots if s.t < s.life and s.y < H + 30 and s.x > self.cam - 60]

    # ------------------------------------------------------------------ contact with Tora
    def body_rect(self):
        """The boss's own hit box in world space (or None)."""
        x, y = self.world()
        k = self.kind
        if self.state in ("enter", "dead", "up", "hit"):
            return None
        if k == "gully":
            return (x - 12, y - 6, 24, 12) if self.state != "dazed" else (x - 14, y - 20, 28, 20)
        if k == "bruno":
            return (x - 13, y - 20, 26, 20)
        if k == "squad":
            if self.state == "dazed":
                return (x - 7, y - 12, 14, 12)
            if self.act == "dive":
                return (self.cam + self.dive_x - 6, self.dive_y - 4, 12, 8)
            return None
        if k == "storm":
            return (x - 14, y - 12, 28, 12) if self.state == "dazed" else None
        if k == "blimp":
            return (x - 13, y - 12, 26, 12) if self.state == "dazed" else None
        return None

    def dangerous(self):
        """While attacking, touching the boss's body hurts (gully/squad dives, bruno charges or runs)."""
        if self.state != "fight":
            return False
        if self.kind in ("gully",):
            return self.act == "dive" and self.n_fired > 0
        if self.kind == "squad":
            return self.act == "dive" and self.n_fired > 0
        if self.kind == "bruno":
            return True
        return False

    def check(self, b, box):
        """Tora's body against the boss: returns 'stomp', 'bump', 'hurt' or None."""
        r = self.body_rect()
        if r is None or not overlap(box, r):
            return None
        if self.state == "dazed":
            if b.vy > 0 and b.y <= r[1] + 7:
                return "stomp"
            return "bump" if self.need_stomp else "hit"
        if self.dangerous():
            return "hurt"
        return None

    def take_hit(self, dmg):
        self.hp -= dmg
        self.flash = 0.35
        if self.hp <= 0:
            self.hp = 0
            self.state = "dead"
            self.t = 0.0
            self.sx, self.sy = self.wx - self.cam, self.wy - 20
            self.shots = []
            return True
        if self.kind == "squad":
            alive = [m for m in self.squad if m["alive"]]
            if alive:
                alive[0]["alive"] = False
        self.state = "hit"
        self.t = 0.0
        return False

    def hurts(self, box):
        for s in self.shots:
            r = s.rect()
            if r is not None and overlap(box, r):
                return True
        return False

    def slow(self):
        """Run-speed factor while RUMBLE's rain or gusts blow."""
        if self.weather <= 0:
            return 1.0
        return 0.6 if self.gust else 0.8

    # ------------------------------------------------------------------ drawing
    def draw(self, s, t):
        cam = self.cam
        for sh in self.shots:
            if sh.k in ("shell", "crumb", "hail", "bone", "fishbone", "anchor") and sh.state == 0:
                g = self.sc.roof_y_at(sh.x)
                if g is not None and g - sh.y > 6:
                    w = 4 + int(max(0, 60 - (g - sh.y)) / 10)
                    pygame.draw.ellipse(s, col("black"), (int(sh.x - cam) - w, g - 2, w * 2 + 1, 3))
        for sh in self.shots:
            draw_shot(s, sh, cam, t, self.lv)
        if self.kind == "storm" and self.weather > 0:
            draw_storm_weather(s, t, self.gust)
        x, y = self.world()
        sx, sy = int(x - cam), int(y)
        hit = self.flash > 0 and int(t * 20) % 2
        k = self.kind
        if k == "gully":
            if self.act == "dive" and self.n_fired == 0 and self.state == "fight":
                self.draw_dive_warning(s, t)
            remap = {"w": "r", "g": "r"} if hit else None
            if self.state in ("dazed", "hit"):
                sp = sprite("rr_gully_nofish", 0, remap=remap, scale=2)
                s.blit(sp, (sx - 22, sy - 30))
                dizzy(s, sx - 6, sy - 30, t)
            elif self.state == "dead":
                s.blit(sprite("rr_gully_dead", 0, scale=2), (sx - 22, sy - 16))
            else:
                s.blit(sprite("rr_gully", int(t * 8) % 2, remap=remap, scale=2), (sx - 22, sy - 16))
        elif k == "bruno":
            draw_bruno(s, sx, sy, t, self, hit)
        elif k == "squad":
            draw_squad(s, self, t, hit)
        elif k == "storm":
            draw_storm(s, sx, sy, t, self, hit)
        elif k == "blimp":
            draw_blimp(s, sx, sy, t, self, hit)
        if self.state == "dazed" and int(t * 4) % 2:
            r = self.body_rect()
            if r:
                ax = int(r[0] + r[2] / 2 - cam)
                ay = int(r[1]) - 18 - int(abs(math.sin(t * 6)) * 3)
                pygame.draw.polygon(s, col("yellow"), [(ax - 4, ay - 4), (ax + 4, ay - 4), (ax, ay + 1)])
                draw_text(s, "JUMP ON IT!" if self.need_stomp else "GET IT!", ax, ay - 13, "yellow",
                          align="center", outline="ink")

    def draw_dive_warning(self, s, t):
        if int(t * 10) % 2:
            draw_text(s, "!", W - 12, int(self.dive_y) - 6, "red", 2, outline="ink")
        for xx in range(84, W - 22, 10):
            s.fill(col("red"), (xx, int(self.dive_y), 5, 1))


def overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def arc(s, c, cx, cy, r, a0, a1):
    """A 1-px arc from a0 to a1 degrees (0 = right, 90 = down), plotted point by point."""
    cc = col(c)
    for a in range(a0, a1 + 1, 6):
        ra = math.radians(a)
        s.fill(cc, (cx + int(round(math.cos(ra) * r)), cy + int(round(math.sin(ra) * r)), 1, 1))


def dizzy(s, x, y, t):
    for i in range(3):
        a = t * 5 + i * 2.1
        s.fill(col("yellow"), (x + int(math.cos(a) * 8), y + int(math.sin(a) * 2), 2, 2))


def draw_shot(s, sh, cam, t, lv):
    x, y = int(sh.x - cam), int(sh.y)
    k = sh.k
    if k == "shell":
        pygame.draw.ellipse(s, col("black"), (x - 5, y - 6 if sh.state else y - 4, 10, 7))
        pygame.draw.ellipse(s, col("peach"), (x - 4, y - 5 if sh.state else y - 3, 8, 5))
        s.fill(col("pink"), (x - 2, (y - 4 if sh.state else y - 2), 1, 3))
        s.fill(col("pink"), (x + 1, (y - 4 if sh.state else y - 2), 1, 3))
    elif k == "feather":
        ang = math.atan2(sh.vy, sh.vx)
        pygame.draw.line(s, col("white"), (x, y), (x - int(math.cos(ang) * 6), y - int(math.sin(ang) * 6)), 2)
        s.fill(col("gray"), (x, y, 1, 1))
    elif k == "crumb":
        s.fill(col("black"), (x - 2, y - 2, 5, 5))
        s.fill(col("peach"), (x - 1, y - 1, 3, 3))
    elif k == "hail":
        s.fill(col("white"), (x - 1, y - 1, 3, 3))
        s.fill(col("sky"), (x, y + 1, 1, 1))
    elif k == "wave":
        for i in range(3):
            arc(s, "yellow" if (i + int(t * 10)) % 2 else "white", x, y - 6, 4 + i * 3, 110, 250)
    elif k == "bone":
        s.fill(col("white"), (x - 4, y - 3, 9, 2))
        for dx in (-5, 4):
            s.fill(col("white"), (x + dx, y - 4, 2, 4))
        s.fill(col("gray"), (x - 4, y - 1, 9, 1))
    elif k == "bolt":
        if sh.state == 0:
            if int(t * 12) % 2:
                for yy in range(30, int(sh.gy), 8):
                    s.fill(col("yellow"), (x, yy, 1, 4))
            pygame.draw.ellipse(s, col("yellow"), (x - 8, int(sh.gy) - 2, 17, 4), 1)
        elif sh.state == 1:
            px = x
            for yy in range(20, int(sh.gy), 8):
                nx = x + random.randint(-4, 4)
                pygame.draw.line(s, col("white"), (px, yy), (nx, yy + 8), 3)
                pygame.draw.line(s, col("yellow"), (px, yy), (nx, yy + 8), 1)
                px = nx
            for i in range(6):
                s.fill(col("yellow"), (x - 8 + random.randint(0, 16), int(sh.gy) - random.randint(1, 14), 2, 2))
    elif k == "debris":
        pygame.draw.rect(s, col("black"), (x - 5, y - 9, 10, 9))
        s.fill(col("gray"), (x - 4, y - 8, 8, 7))
        s.fill(col("darkgray"), (x - 4, y - 5 + int(t * 8) % 3, 8, 1))
    elif k == "fishbone":
        s.fill(col("white"), (x - 4, y, 9, 1))
        for i in range(3):
            s.fill(col("white"), (x - 2 + i * 2, y - 2, 1, 5))
        pygame.draw.circle(s, col("white"), (x - 5, y), 2)
    elif k == "anchor":
        if sh.state == 0:
            s.fill(col("darkgray"), (x, 40, 1, max(0, y - 52)))
        pygame.draw.rect(s, col("black"), (x - 2, y - 13, 5, 10))
        s.fill(col("gray"), (x - 1, y - 12, 3, 9))
        arc(s, "gray", x, y - 7, 6, 20, 160)
        arc(s, "gray", x, y - 6, 6, 20, 160)
    elif k == "mini":
        sp = sprite("rr_gully_nofish", int(t * 10) % 2, remap={"w": "c", "g": "d"})
        s.blit(sp, (x - 9, y - 9))


def draw_bruno(s, x, y, t, b, hit):
    """BRUNO: a stocky guard dog with a studded collar and a little cap."""
    dazed = b.state == "dazed"
    charging = b.act == "charge" and b.n_fired > 0
    growl = b.act == "charge" and b.n_fired == 0 and b.state == "fight"
    shake = int(math.sin(t * 50) * 1) if growl else 0
    x += shake
    body = col("red" if hit else "brown")
    dark = col("choco")
    run = int(t * 12) % 2 if not dazed else 0
    # body
    pygame.draw.ellipse(s, col("black"), (x - 14, y - 19, 28, 15))
    pygame.draw.ellipse(s, body, (x - 13, y - 18, 26, 13))
    s.fill(col("cream"), (x - 6, y - 9, 10, 3))
    # legs
    for i, lx in enumerate((x - 10, x - 5, x + 3, x + 8)):
        off = (run if i % 2 else 1 - run) * 2
        s.fill(col("black"), (lx - 1, y - 6, 4, 6))
        s.fill(dark, (lx, y - 6 + off // 2, 2, 5 - off // 2))
    # tail
    s.fill(dark, (x + 13, y - 18 + int(math.sin(t * 15) * 2), 3, 4))
    # head (faces left, towards Tora)
    hx, hy = x - 14, y - 22 + (2 if dazed else 0)
    pygame.draw.circle(s, col("black"), (hx, hy), 9)
    pygame.draw.circle(s, body, (hx, hy), 8)
    pygame.draw.ellipse(s, col("cream"), (hx - 9, hy, 10, 7))
    s.fill(col("black"), (hx - 8, hy + 1, 3, 2))           # nose
    pygame.draw.ellipse(s, dark, (hx + 2, hy - 9, 7, 9))    # ear
    pygame.draw.ellipse(s, dark, (hx - 7, hy - 9, 6, 7))
    if dazed:
        s.fill(col("black"), (hx - 4, hy - 3, 3, 1))
        s.fill(col("black"), (hx + 1, hy - 3, 3, 1))
        s.fill(col("pink"), (hx - 5, hy + 6, 3, 4 + int(abs(math.sin(t * 8)) * 2)))    # tongue out
        dizzy(s, hx, hy - 14, t)
    else:
        cute.eyes(s, hx - 1, hy - 2, 3, -1, "angry", size=1)
        if growl or charging:
            s.fill(col("red"), (hx - 4, hy - 3, 1, 1))
            s.fill(col("red"), (hx + 2, hy - 3, 1, 1))
        if b.act == "bark" and b.at > 0.2 and b.at < 1.0:
            s.fill(col("black"), (hx - 8, hy + 4, 6, 3))
            draw_text(s, "WOOF!", hx - 10, hy - 22, "yellow", align="center", outline="ink")
    # studded collar + guard cap
    s.fill(col("red"), (hx - 2, hy + 6, 9, 3))
    for i in range(3):
        s.fill(col("yellow"), (hx - 1 + i * 3, hy + 7, 1, 1))
    s.fill(col("blue"), (hx - 6, hy - 10, 12, 3))
    s.fill(col("blue"), (hx - 9, hy - 8, 5, 2))
    s.fill(col("yellow"), (hx - 1, hy - 10, 2, 2))
    if growl and int(t * 8) % 2:
        draw_text(s, "GRRR", hx, hy - 24, "red", align="center", outline="ink")


def draw_squad(s, b, t, hit):
    cam = b.cam
    hx, hy = b.sx, b.sy
    for i, m in enumerate(b.squad):
        if not m["alive"]:
            continue
        back = m["back"]
        if i == b.diver and b.act == "dive":
            if b.n_fired == 0:      # wind-up: wobble in place, then swoop
                if int(t * 10) % 2:
                    draw_text(s, "!", int(hx + m["dx"]), int(hy + m["dy"]) - 16, "red", outline="ink")
                b.draw_dive_warning(s, t)
                x, y = hx + m["dx"] + math.sin(t * 30) * 2, hy + m["dy"]
            else:
                x, y = b.dive_x, b.dive_y
        else:
            x = hx + m["dx"] + math.sin(t * 3 + i) * 3
            y = hy + m["dy"] + math.cos(t * 4 + i) * 3 - back * 60
        sp = sprite("rr_pigeon_fly", int(t * 10 + i) % 2, remap={"g": "w", "d": "g"})
        s.blit(sp, (int(x) - 6, int(y) - 6))
    # the sergeant: a big pigeon with a cap (leads from the back, dives once the squad is down)
    x, y = (hx + 34, hy - 8)
    if b.state in ("dazed", "hit"):
        x, y = b.wx - cam, b.wy - 6
    elif b.sergeant_only() and b.act == "dive":
        if b.n_fired == 0:
            b.draw_dive_warning(s, t)
        else:
            x, y = b.dive_x, b.dive_y
    sp = sprite("rr_pigeon_fly" if b.state not in ("dazed", "hit") else "rr_pigeon", int(t * 8) % 2,
                remap={"g": "r", "d": "P"} if hit else {"g": "v", "d": "u"}, scale=2 if b.state != "dazed" else 1)
    if b.state in ("dazed", "hit"):
        sp = sprite("rr_pigeon", 0, remap={"g": "r", "d": "P"} if hit else {"g": "v", "d": "u"}, scale=1)
        s.blit(sp, (int(x) - 6, int(y) - 4))
        s.fill(col("blue"), (int(x) - 5, int(y) - 6, 6, 2))
        dizzy(s, int(x), int(y) - 10, t)
    else:
        s.blit(sp, (int(x) - 12, int(y) - 12))
        s.fill(col("blue"), (int(x) - 10, int(y) - 12, 9, 3))     # sergeant's cap
        s.fill(col("yellow"), (int(x) - 6, int(y) - 12, 2, 1))


def draw_storm(s, x, y, t, b, hit):
    """RUMBLE: a grumpy thundercloud. Shrinks into a little puff when worn out."""
    dazed = b.state == "dazed"
    base = "red" if hit else ("gray" if dazed else "darkgray")
    if dazed:
        puffs = ((-8, -6, 6), (0, -9, 7), (8, -6, 6), (0, -4, 8))
    else:
        swell = 1 + (b.weather > 0) * 0.15
        puffs = tuple((int(dx * swell), dy, int(r * swell)) for dx, dy, r in
                      ((-22, 0, 11), (-8, -9, 14), (10, -7, 13), (24, 1, 10), (0, 4, 13)))
    for dx, dy, r in puffs:
        pygame.draw.circle(s, col("black"), (x + dx, y + dy), r + 1)
    for dx, dy, r in puffs:
        pygame.draw.circle(s, col(base), (x + dx, y + dy), r)
    for dx, dy, r in puffs:
        pygame.draw.circle(s, col("gray" if not dazed else "white"), (x + dx - r // 3, y + dy - r // 3), max(1, r // 3))
    ey = y - (4 if dazed else 0)
    if dazed:
        cute.eyes(s, x, ey, 4, 0, "sleepy")
        dizzy(s, x, y - 18, t)
    else:
        cute.eyes(s, x, ey, 6, -1, "angry", size=2)
        cute.mouth(s, x - 1, y + 6, "angry")
        if b.act == "bolt" and int(t * 14) % 2:
            for i in range(3):
                pygame.draw.line(s, col("yellow"), (x - 10 + i * 10, y + 12), (x - 13 + i * 10, y + 20), 2)


def draw_storm_weather(s, t, gust):
    c = col("sky")
    for i in range(50):
        x = (i * 47 + int(t * (300 if gust else 80))) % (W + 30) - 15
        y = (i * 31 + int(t * 300)) % H
        if gust:
            s.fill(col("lavender"), (W - x, y, 10, 1))
        else:
            pygame.draw.line(s, c, (x, y), (x - 2, y + 7))


def draw_blimp(s, x, y, t, b, hit):
    """GULLY's fish blimp: a fish-shaped balloon, a gondola, and Gully at the controls."""
    dazed = b.state in ("dazed", "hit")
    if dazed:
        gx, gy = x, y
        bx, by = x + 4, y - 30
        sag = 4
    else:
        bx, by = x, y
        gx, gy = x, y + 26
        sag = 0
    skin = col("red" if hit else "sky")
    pygame.draw.ellipse(s, col("black"), (bx - 31, by - 15 + sag, 62, 30 - sag))
    pygame.draw.ellipse(s, skin, (bx - 30, by - 14 + sag, 60, 28 - sag))
    pygame.draw.ellipse(s, col("blue"), (bx - 30, by + 2, 60, 12 - sag))
    pygame.draw.polygon(s, col("black"), [(bx + 26, by), (bx + 42, by - 12), (bx + 42, by + 12)])
    pygame.draw.polygon(s, skin, [(bx + 28, by), (bx + 40, by - 9), (bx + 40, by + 9)])
    pygame.draw.circle(s, col("white"), (bx - 18, by - 3 + sag // 2), 5)
    pygame.draw.circle(s, col("black"), (bx - 19, by - 3 + sag // 2), 2)
    for i in range(3):
        s.fill(col("white"), (bx - 6 + i * 9, by - 9 + sag, 4, 1))
    s.fill(col("darkgray"), (gx - 9, by + 12, 1, gy - by - 14))
    s.fill(col("darkgray"), (gx + 9, by + 12, 1, gy - by - 14))
    pygame.draw.rect(s, col("black"), (gx - 13, gy - 12, 26, 12))
    s.fill(col("brown"), (gx - 12, gy - 11, 24, 10))
    s.fill(col("peach"), (gx - 12, gy - 11, 24, 1))
    s.fill(col("gray"), (gx - 16, gy - 9, 4, 3))         # the cannon
    if b.act == "cannon" and b.state == "fight" and int(t * 12) % 2:
        s.fill(col("yellow"), (gx - 18, gy - 9, 2, 3))
    sp = sprite("rr_gully", int(t * 6) % 2 if not dazed else 0, remap={"w": "r"} if hit else None)
    s.blit(sp, (gx - 8, gy - 26))
    s.fill(col("hotpink"), (gx - 2, gy - 28, 6, 2))      # captain's hat
    s.fill(col("hotpink"), (gx, gy - 31, 3, 3))
    if dazed:
        dizzy(s, gx, gy - 32, t)
