"""WHISKER MAZE bosses: a big house gadget lives in the open hall in the middle of the maze and attacks with
telegraphed patterns (tiles blink before they hurt). Nori grabs the catnip that sprouts in the corners and,
while zoomy, pounces on the boss. Mirrored by ios/MochiArcade/Games/WhiskerMazeBoss.swift.

Patterns (combined per boss, see whisker_maze_maze.BOSSES):
  suck_row / suck_col / suck_cross   vacuum beam along Nori's row / column / both
  snap_row / snap_col / burn_row     the same lines with snapping jaws / hot toaster coils
  bunnies                            dust-bunny minions that chase for a while
  stomp / stomp3 / hop / quake       the slipper leaps onto Nori (x3), hops, or shakes lines around itself
  traps / traps_big                  mousetraps spring up around Nori
  toast / drip / drip8               flying toast / water drops shot out in 4 (8) directions
  pop                                toast lands on a few tiles near Nori
  flood / splash                     the floor around Nori gets slippery / a bucket splash lands on her
"""
import math
import random

LINE_STYLE = {"suck_row": "suck", "suck_col": "suck", "snap_row": "snap", "snap_col": "snap", "burn_row": "burn"}


class Boss:
    def __init__(self, sc, spec):
        self.sc = sc
        self.kind = spec["kind"]
        self.name = spec["name"]
        self.maxhp = self.hp = spec["hp"]
        self.rate = spec["rate"]
        self.speed = spec["speed"]
        self.patterns = list(spec["patterns"])
        self.extra = spec["extra"]
        self.tier = spec["tier"]
        self.x, self.y = 15.0, -4.0          # tile units (centre); flies in from the top
        self.state = "enter"                 # enter | idle | wind | air | land | stun | dead
        self.cd = 2.2
        self.timer = 0.0
        self.flash = 0.0
        self.next = ""
        self.air = (0.0, 0.0, 0.0, 0.0, 1.0)  # from x, y, to x, y, duration
        self.queue = 0                        # stomps still to come (stomp3)
        self.t = 0.0

    @property
    def phase(self):
        f = self.hp / self.maxhp
        return 1 if f > 0.67 else 2 if f > 0.34 else 3

    def wind_frac(self):
        return 1.0 - self.timer / 0.5 if self.state == "wind" else 0.0

    def airborne(self):
        return self.state in ("air", "enter")

    def update(self, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        sc = self.sc
        if self.state == "dead":
            return
        if self.state == "enter":
            self.y = min(8.0, self.y + dt * 7)
            if self.y >= 8.0:
                self.state = "idle"
            return
        if self.state == "stun":
            self.timer -= dt
            self.drift(15.0, 8.0, dt, 2.0)
            if self.timer <= 0:
                self.state = "idle"
                self.cd = max(self.cd, 0.6)
            return
        if self.state == "air":
            self.timer += dt
            fx, fy, tx, ty, dur = self.air
            k = min(1.0, self.timer / dur)
            self.x, self.y = fx + (tx - fx) * k, fy + (ty - fy) * k
            if k >= 1.0:
                self.state = "land"
                self.timer = 0.55
                sc.app.shake(4, 0.25)
                sc.app.audio.play("boom")
            return
        if self.state == "land":
            self.timer -= dt
            if self.timer <= 0:
                if self.queue > 0:
                    self.queue -= 1
                    self.leap()
                else:
                    self.state = "idle"
                    self.cd = self.interval()
            return
        if self.state == "wind":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "idle"
                self.cd = self.interval()
                self.fire(self.next)
            return
        # idle: drift after Nori but stay inside the hall (fly home first when outside it)
        n = sc.nori
        inside = 9.5 <= self.x <= 20.5 and 5.5 <= self.y <= 10.5
        tx = max(10.0, min(20.0, n.x))
        ty = max(6.0, min(10.0, n.y))
        self.drift(tx, ty, dt, self.speed * (1.0 if inside else 2.5))
        self.cd -= dt
        if self.cd <= 0 and sc.state == "play":
            pats = self.patterns + ([self.extra] if self.phase >= 3 else [])
            self.next = random.choice(pats)
            self.state = "wind"
            self.timer = 0.5
            sc.app.audio.play("hold")

    def interval(self):
        return self.rate * (1.0, 0.85, 0.7)[self.phase - 1]

    def drift(self, tx, ty, dt, speed):
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d > 0.01:
            step = min(d, speed * dt)
            self.x += dx / d * step
            self.y += dy / d * step

    def tile(self):
        return int(math.floor(self.x + 0.5)), int(math.floor(self.y + 0.5))

    def leap(self):
        """The slipper jumps onto Nori: a shadow marks the landing zone."""
        sc = self.sc
        tx, ty = sc.nori.tile()
        self.air = (self.x, self.y, float(tx), float(ty), 0.95)
        self.state = "air"
        self.timer = 0.0
        sc.add_hazard(sc.area_tiles(tx, ty, 1), 0.95, 0.3, "stomp")
        sc.app.audio.play("jump")

    def fire(self, p):
        sc = self.sc
        nx, ny = sc.nori.tile()
        ph = self.phase
        bx, by = self.tile()
        if p in LINE_STYLE:
            tiles = sc.row_tiles(ny) if p.endswith("row") else sc.col_tiles(nx)
            sc.add_hazard(tiles, 1.0, 0.5, LINE_STYLE[p])
        elif p == "suck_cross":
            sc.add_hazard(sc.row_tiles(ny) + sc.col_tiles(nx), 1.1, 0.5, "suck")
        elif p == "bunnies":
            for _ in range(1 + ph):
                sc.spawn_bunny()
        elif p == "stomp":
            self.leap()
        elif p == "stomp3":
            self.queue = 2
            self.leap()
        elif p == "hop":
            self.air = (self.x, self.y, random.uniform(10, 20), random.uniform(6, 10), 0.6)
            self.state = "air"
            self.timer = 0.0
            sc.add_hazard(sc.area_tiles(int(self.air[2] + 0.5), int(self.air[3] + 0.5), 1), 0.6, 0.25, "stomp")
        elif p == "quake":
            tiles = [(x, by) for x in range(bx - 5, bx + 6)] + [(bx, y) for y in range(by - 5, by + 6)]
            sc.add_hazard(sc.open_only(tiles), 0.8, 0.4, "quake")
        elif p in ("traps", "traps_big"):
            n = (3 if p == "traps" else 6) + ph
            sc.add_traps(n)
        elif p in ("toast", "drip", "drip8"):
            eight = p == "drip8" or ph >= 2
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            if eight:
                dirs += [(0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)]
            for dx, dy in dirs:
                sc.shots.append([self.x, self.y, dx * 7.0, dy * 7.0, "toast" if p == "toast" else "drip", 4.0])
            sc.app.audio.play("shoot")
        elif p == "pop":
            for _ in range(2 + ph):
                tx = nx + random.randint(-3, 3)
                ty = ny + random.randint(-2, 2)
                sc.add_hazard(sc.open_only([(tx, ty)]) or [(nx, ny)], 1.1, 0.3, "pop")
        elif p == "flood":
            tiles = sc.open_only([(nx + dx, ny + dy) for dx in range(-3, 4) for dy in range(-3, 4)
                                  if abs(dx) + abs(dy) <= 3])
            sc.add_hazard(tiles, 0.6, 7.0, "wet")
        elif p == "splash":
            sc.add_hazard(sc.area_tiles(nx, ny, 1), 0.9, 0.3, "splash")

    def hurt(self, dmg):
        """A zoomy pounce landed. Returns True when the boss is beaten."""
        self.hp = max(0, self.hp - dmg)
        self.flash = 0.3
        self.queue = 0
        if self.hp <= 0:
            self.state = "dead"
            return True
        self.state = "stun"
        self.timer = 1.2
        return False
