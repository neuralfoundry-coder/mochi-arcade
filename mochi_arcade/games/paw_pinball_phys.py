"""PAW PINBALL physics: a jingle-bell ball on a sloped table.

Sub-stepped so the ball (and a swinging paw) never moves more than ~1 px per step, which makes every contact a
plain overlap test (swept enough for walls 0 px thick). Flippers are tapered capsules that hand their surface
velocity (angular velocity x lever arm) to the ball, so where the ball sits on the paw and when you flip decide the
shot. Collisions report events to the scene, which does the scoring. Ported line by line in PawPinballPhys.swift.
"""
import math

from mochi_arcade.games.paw_pinball_tables import BALL_R, GATE, LANE_X, METAL, PLUNGE_Y, RUBBER, RW, SLING

GRAV = 330.0          # px/s^2 down the table
VMAX = 640.0          # speed cap
CELL = 16
REST = {METAL: 0.42, RUBBER: 0.62, SLING: 0.62, GATE: 0.3}
SLING_KICK = 175.0
BUMP_KICK = 250.0
POST_REST = 0.6
FLIP_REST = 0.22           # a still paw: soft, so a ball can be caught
FLIP_LIVE = 0.62           # a swinging paw: snappy, the ball leaves early (the shot angle follows the paw)
RAMP_MIN = 175.0
FLIP_R1, FLIP_R2 = 3.6, 2.2
UP_ANG, REST_ANG = -0.42, 0.50
W_UP, W_DOWN = 27.0, 16.0


class Ball:
    def __init__(self, x, y, vx=0.0, vy=0.0, kind="bell"):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.kind = kind            # bell | kitten
        self.coat = 0               # kitten fur colour
        self.state = "play"         # play | ramp | nap | gone
        self.ramp = -1              # ramp index while riding a ramp
        self.rd = 0.0               # distance along the ramp path
        self.rv = 0.0               # ramp speed
        self.nap_t = 0.0
        self.nap_cd = 0.0           # saucer cooldown after a kick-out
        self.lane_in = 0            # bit mask of rollover sensors the ball is inside
        self.auto = -1.0            # >= 0: auto-plunge when this runs out (ball save, multiball)
        self.still_t = 0.0
        self.ax, self.ay = x, y     # anchor for stuck detection
        self.trail = []
        self.boss_cd = 0.0
        self.launched = False       # left the plunger lane

    def speed(self):
        return math.hypot(self.vx, self.vy)

    def in_lane(self):
        return self.x > RW and self.y > 60

    def on_plunger(self):
        return self.in_lane() and self.y >= PLUNGE_Y - BALL_R - 1.5 and abs(self.vy) < 40


class Flipper:
    def __init__(self, x, y, side, length):
        self.px, self.py = x, y
        self.side = side            # +1 left paw (points right), -1 right paw (points left)
        self.len = length
        self.a = REST_ANG           # angle below horizontal
        self.w = 0.0                # angular velocity (negative = swinging up)
        self.pressed = False
        self.stun = 0.0
        self.power = 1.0

    def tip(self):
        return self.px + self.side * self.len * math.cos(self.a), self.py + self.len * math.sin(self.a)

    def update(self, h):
        if self.pressed and self.stun <= 0:
            if self.a > UP_ANG:
                self.w = -W_UP * self.power
                self.a += self.w * h
                if self.a <= UP_ANG:
                    self.a, self.w = UP_ANG, 0.0
            else:
                self.w = 0.0
        else:
            if self.a < REST_ANG:
                self.w = W_DOWN
                self.a += self.w * h
                if self.a >= REST_ANG:
                    self.a, self.w = REST_ANG, 0.0
            else:
                self.w = 0.0

    def is_up(self):
        return self.a < REST_ANG - 0.25


def _seg_contact(b, x1, y1, x2, y2, rad):
    """(nx, ny, depth, t) if the ball overlaps the capsule x1,y1-x2,y2 of radius rad."""
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    t = ((b.x - x1) * dx + (b.y - y1) * dy) / l2 if l2 > 0 else 0.0
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    cx, cy = x1 + dx * t, y1 + dy * t
    ex, ey = b.x - cx, b.y - cy
    d2 = ex * ex + ey * ey
    r = BALL_R + rad
    if d2 >= r * r:
        return None
    d = math.sqrt(d2)
    if d < 1e-6:
        ln = math.sqrt(l2) or 1.0
        return -dy / ln, dx / ln, r, t
    return ex / d, ey / d, r - d, t


def _bounce(b, nx, ny, depth, e, svx=0.0, svy=0.0):
    """Push the ball out along n and reflect its velocity relative to a surface moving at (svx, svy).
    Returns the impact speed (0 if the ball was already leaving)."""
    b.x += nx * depth
    b.y += ny * depth
    rvx, rvy = b.vx - svx, b.vy - svy
    vn = rvx * nx + rvy * ny
    if vn < 0:
        b.vx -= (1 + e) * vn * nx
        b.vy -= (1 + e) * vn * ny
        return -vn
    return 0.0


class World:
    """Static table geometry with a uniform grid for the broad phase."""

    def __init__(self, tb):
        self.tb = tb
        self.segs = [list(w) for w in tb["walls"]]
        self.circs = [[p[0], p[1], p[2], 0, i] for i, p in enumerate(tb["posts"])]
        self.circs += [[b[0], b[1], 9.0, 1, i] for i, b in enumerate(tb["bumpers"])]
        self.cols, self.rows = 320 // CELL + 1, 210 // CELL + 1
        self.grid = [[] for _ in range(self.cols * self.rows)]
        pad = BALL_R + 2
        for i, (x1, y1, x2, y2, _) in enumerate(self.segs):
            self._reg(i, min(x1, x2) - pad, min(y1, y2) - pad, max(x1, x2) + pad, max(y1, y2) + pad)
        for i, (x, y, r, _, _) in enumerate(self.circs):
            self._reg(10000 + i, x - r - pad, y - r - pad, x + r + pad, y + r + pad)

    def _reg(self, item, x0, y0, x1, y1):
        for cy in range(max(0, int(y0 // CELL)), min(self.rows - 1, int(y1 // CELL)) + 1):
            for cx in range(max(0, int(x0 // CELL)), min(self.cols - 1, int(x1 // CELL)) + 1):
                self.grid[cy * self.cols + cx].append(item)

    def near(self, x, y):
        cx, cy = int(x // CELL), int(y // CELL)
        if cx < 0 or cy < 0 or cx >= self.cols or cy >= self.rows:
            return ()
        return self.grid[cy * self.cols + cx]


class Physics:
    """Steps every free ball. The scene owns balls, flippers and the dynamic things (fish, kittens, boss ...)
    and receives events: (kind, a, x, y)."""

    def __init__(self, scene, tb):
        self.sc = scene
        self.world = World(tb)
        self.tb = tb
        self.events = []
        self.grav = GRAV

    def emit(self, kind, a, x, y):
        self.events.append((kind, a, x, y))

    def step(self, dt):
        sc = self.sc
        balls = [b for b in sc.balls if b.state == "play"]
        flips = sc.flippers
        vmax = 0.0
        for b in balls:
            vmax = max(vmax, abs(b.vx) + abs(b.vy))
        fl = 0.0
        for f in flips:
            if f.pressed or f.a < REST_ANG:
                fl = max(fl, W_UP * f.power * f.len)
        n = int(math.ceil((vmax + fl) * dt / 1.0))
        n = max(2, min(28, n))
        h = dt / n
        for _ in range(n):
            for f in flips:
                f.update(h)
            for b in balls:
                if b.state != "play":
                    continue
                b.vy += self.grav * h
                px, py = b.x, b.y
                b.x += b.vx * h
                b.y += b.vy * h
                self.statics(b)
                self.dynamics(b)
                for f in flips:
                    self.flipper(b, f)
                self.sensors(b, px, py)
                sp = b.vx * b.vx + b.vy * b.vy
                if sp > VMAX * VMAX:
                    k = VMAX / math.sqrt(sp)
                    b.vx *= k
                    b.vy *= k
                if b.y > 206:
                    b.state = "gone"
                    self.emit("drain", 0, b.x, b.y)
            if len(balls) > 1:
                self.ball_pairs(balls)

    # ---------------------------------------------------------------- contacts
    def statics(self, b):
        wd = self.world
        for item in wd.near(b.x, b.y):
            if item < 10000:
                x1, y1, x2, y2, kind = wd.segs[item]
                c = _seg_contact(b, x1, y1, x2, y2, 0.0)
                if c is None:
                    continue
                nx, ny, depth, _ = c
                if kind == GATE and (x2 - x1) * (b.y - y1) - (y2 - y1) * (b.x - x1) < 0:
                    continue        # one-way: only blocks from the playfield side
                imp = _bounce(b, nx, ny, depth, REST[kind])
                if kind == SLING and imp > 40:
                    b.vx += nx * SLING_KICK
                    b.vy += ny * SLING_KICK
                    self.emit("sling", item, b.x, b.y)
                elif imp > 120:
                    self.emit("wall", int(imp), b.x, b.y)
            else:
                x, y, r, kind, idx = wd.circs[item - 10000]
                ex, ey = b.x - x, b.y - y
                d2 = ex * ex + ey * ey
                rr = r + BALL_R
                if d2 >= rr * rr:
                    continue
                d = math.sqrt(d2) or 0.001
                nx, ny = ex / d, ey / d
                if kind == 1:
                    _bounce(b, nx, ny, rr - d, 0.5)
                    vn = b.vx * nx + b.vy * ny
                    if vn < BUMP_KICK:
                        b.vx += nx * (BUMP_KICK - vn)
                        b.vy += ny * (BUMP_KICK - vn)
                    self.emit("bumper", idx, x, y)
                else:
                    imp = _bounce(b, nx, ny, rr - d, POST_REST)
                    if imp > 120:
                        self.emit("wall", int(imp), b.x, b.y)

    def dynamics(self, b):
        sc = self.sc
        for i, f in enumerate(sc.fish):
            if f[6] > 0:            # down
                continue
            c = _seg_contact(b, f[0], f[1], f[2], f[3], 2.0)
            if c is None:
                continue
            nx, ny, depth, _ = c
            _bounce(b, nx, ny, depth, 0.35)
            f[6] = 1.0
            self.emit("fish", i, (f[0] + f[2]) / 2, (f[1] + f[3]) / 2)
        for r_i, r in enumerate(self.tb["ramps"]):
            x1, y1, x2, y2 = r["gate"]
            c = _seg_contact(b, x1, y1, x2, y2, 0.0)
            if c is None:
                continue
            nx, ny, depth, _ = c
            dx, dy = r["dir"]
            into = b.vx * dx + b.vy * dy
            front = (b.x - x1) * dx + (b.y - y1) * dy < 0.5
            if front and into >= RAMP_MIN * sc.ramp_ease:
                b.state = "ramp"
                b.ramp = r_i
                b.rd = 0.0
                b.rv = max(170.0, min(320.0, into * 0.85))
                self.emit("ramp_in", r_i, b.x, b.y)
                return
            _bounce(b, nx, ny, depth, 0.3)
            if front and into > 60:
                self.emit("ramp_fail", r_i, b.x, b.y)
        for d in sc.dyn:            # [x, y, r, kind, solid, ref]
            x, y, r, kind, solid, ref = d
            ex, ey = b.x - x, b.y - y
            d2 = ex * ex + ey * ey
            rr = r + BALL_R
            if d2 >= rr * rr:
                continue
            if not solid:
                self.emit(kind, ref, x, y)
                continue
            dd = math.sqrt(d2) or 0.001
            nx, ny = ex / dd, ey / dd
            _bounce(b, nx, ny, rr - dd, 0.55)
            if kind in ("boss", "bunny", "pickle"):
                vn = b.vx * nx + b.vy * ny
                if vn < 190:
                    b.vx += nx * (190 - vn)
                    b.vy += ny * (190 - vn)
            self.emit(kind, ref, b.x, b.y)
        if sc.tail_on:
            c = _seg_contact(b, 155.0, 184.0, 155.0, 190.0, 2.5)
            if c is not None:
                nx, ny, depth, _ = c
                _bounce(b, nx, ny, depth, 0.55)

    def flipper(self, b, f):
        tx, ty = f.tip()
        dx, dy = tx - f.px, ty - f.py
        l2 = dx * dx + dy * dy
        t = ((b.x - f.px) * dx + (b.y - f.py) * dy) / l2
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        cx, cy = f.px + dx * t, f.py + dy * t
        rr = BALL_R + FLIP_R1 + (FLIP_R2 - FLIP_R1) * t
        ex, ey = b.x - cx, b.y - cy
        d2 = ex * ex + ey * ey
        if d2 >= rr * rr:
            return
        d = math.sqrt(d2)
        if d < 1e-6:
            ln = math.sqrt(l2)
            nx, ny = dy / ln * f.side, -dx / ln * f.side
        else:
            nx, ny = ex / d, ey / d
        s = t * f.len                  # lever arm: the tip moves fastest
        svx = s * (-f.side * math.sin(f.a)) * f.w
        svy = s * math.cos(f.a) * f.w
        imp = _bounce(b, nx, ny, rr - d, FLIP_LIVE if f.w < 0 else FLIP_REST, svx, svy)
        if imp > 90 and f.w != 0:
            self.emit("flip_hit", f.side, b.x, b.y)

    def sensors(self, b, px, py):
        sc = self.sc
        tb = self.tb
        # rollover lanes
        for i, (lx, ly) in enumerate(tb["lanes"]):
            inside = (b.x - lx) ** 2 + (b.y - ly) ** 2 < 25
            bit = 1 << i
            if inside and not b.lane_in & bit:
                b.lane_in |= bit
                self.emit("lane", i, lx, ly)
            elif not inside and b.lane_in & bit:
                b.lane_in &= ~bit
        # spinner: crossing a horizontal line
        sp = tb["spinner"]
        if sp and (py - sp[1]) * (b.y - sp[1]) <= 0 and py != b.y and sp[0] <= b.x <= sp[2]:
            self.emit("spin", int(abs(b.vy)), b.x, sp[1])
        # nap bed (saucer)
        sa = tb["saucer"]
        if sa and b.nap_cd <= 0:
            if (b.x - sa[0]) ** 2 + (b.y - sa[1]) ** 2 < 20 and b.speed() < 360:
                b.state = "nap"
                b.x, b.y = float(sa[0]), float(sa[1])
                b.vx = b.vy = 0.0
                b.nap_t = 0.0
                self.emit("nap", 0, b.x, b.y)
        # plunger lane exit
        if not b.launched and (b.y < 64 or (b.x < RW - BALL_R and b.y < 120)):
            b.launched = True
            self.emit("launched", 0, b.x, b.y)

    def ball_pairs(self, balls):
        for i in range(len(balls)):
            a = balls[i]
            if a.state != "play":
                continue
            for j in range(i + 1, len(balls)):
                b = balls[j]
                if b.state != "play":
                    continue
                dx, dy = b.x - a.x, b.y - a.y
                d2 = dx * dx + dy * dy
                if d2 >= (2 * BALL_R) ** 2 or d2 < 1e-9:
                    continue
                d = math.sqrt(d2)
                nx, ny = dx / d, dy / d
                push = (2 * BALL_R - d) / 2
                a.x -= nx * push
                a.y -= ny * push
                b.x += nx * push
                b.y += ny * push
                rv = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
                if rv < 0:
                    k = -rv * 0.95
                    a.vx -= nx * k
                    a.vy -= ny * k
                    b.vx += nx * k
                    b.vy += ny * k


def ramp_lengths(path):
    out = [0.0]
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        out.append(out[-1] + math.hypot(x2 - x1, y2 - y1))
    return out


def ramp_pos(path, lens, d):
    """Point and direction at distance d along a ramp path."""
    if d >= lens[-1]:
        (x1, y1), (x2, y2) = path[-2], path[-1]
        L = max(0.001, lens[-1] - lens[-2])
        return x2, y2, (x2 - x1) / L, (y2 - y1) / L
    i = 0
    while i < len(lens) - 2 and lens[i + 1] < d:
        i += 1
    (x1, y1), (x2, y2) = path[i], path[i + 1]
    L = max(0.001, lens[i + 1] - lens[i])
    u = (d - lens[i]) / L
    return x1 + (x2 - x1) * u, y1 + (y2 - y1) * u, (x2 - x1) / L, (y2 - y1) / L


LANE_START = (LANE_X, PLUNGE_Y - BALL_R)
