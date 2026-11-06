"""ROOFTOP RUN courses: 200 fixed stages assembled from curated rooftop chunks with seeded variation.

Everything here is deterministic (random.Random(seed)), so the desktop game and the iOS port (which reads the
exported course strings, see EXPORT in rooftop_run.py) run exactly the same rooftops.

A course is a list of entities in world pixels (y grows downwards, a roof's y is its top surface):
  R x0 x1 y glass        a rooftop (glass=1: a skylight - it cracks under paws and breaks)
  S k x y w h            a solid box standing on a roof: X crate, C fish crate, U AC unit, K chimney,
                         B billboard (floats on legs - slide under it), T water tank
  L x0 x1 y sway         laundry / lantern line: bounce on it (sway = up/down swing in px)
  W x0 x1 y spark        tram wire: jump up to grab it and slide along (spark=1: zaps run along it)
  N x0 x1 k              wind: 0 headwind, 1 tailwind          V x y   updraft vent on a roof
  M x y w amp ph         window-washer lift (moves up and down)
  F x y n dx             a row of fish          A x y n dx h   an arc of fish        G x y  golden fish
  P x y k                capsule: 0 bell magnet 1 umbrella 2 catnip rush 3 fur shield 4 milk (+life) 5 gold bell
  p x y xa xb            walking pigeon         q x y  flying pigeon       s x y ph  sprinkler
  a x y h                antenna spikes         i x y top  icicle         d x y  diving gull (dive height y)
  z x y                  lightning rod (zaps the roof)       J x y  firework spring pad
  E x                    the finish line
Encoded as "T,f1,f2;T,f1,..." strings (ints only) to keep the iOS data small.
"""
import math
import random

GROUND = 150
Y_MIN, Y_MAX = 104, 174
# physics shared with the game (rooftop_run.py imports these)
G_UP = 560.0        # gravity while rising with JUMP held
G_DOWN = 1150.0     # gravity otherwise
JUMP_V = 265.0
AIR_V = 235.0       # double jump
KICK_V = 285.0
BOUNCE_V = 330.0
PAD_V = 440.0
EASY = 0.9          # slowest run-speed factor (easy difficulty) - every gap is checked against it
HANG = 15           # feet below a tram wire while hanging on it
FISH_TOP = 30       # nothing to collect above this line (the HUD lives up there)
SLIDE_H, STAND_H = 7, 14

# districts: name, sky top, sky low, far skyline, near skyline, facade, trim, ledge, windows, landmark, weather,
# the "NEW" line of the district's first stage and Tora's line on its stage cards
THEMES = [
    ("HARBOR LANE", "night", "deep", "ink", "deep", "brown", "choco", "peach", "yellow", "sea", "",
     "JUMP THE GAPS - HOLD JUMP FOR HIGHER!", "THAT FISH WAS MINE, GULLY!"),
    ("LAUNDRY ROW", "night", "ink", "ink", "deep", "darkgray", "ink", "gray", "peach", "moon", "",
     "NEW: BOUNCE ON THE LAUNDRY LINES", "SOCKS? BOING!"),
    ("CHIMNEY HILL", "ink", "deep", "night", "ink", "choco", "black", "brown", "orange", "hills", "",
     "NEW: TAP JUMP ON A WALL TO WALL-KICK", "UP AND OVER, PAWS FIRST."),
    ("PIGEON PLAZA", "night", "deep", "ink", "deep", "gray", "darkgray", "cream", "yellow", "clock", "",
     "NEW: PIGEONS - POUNCE ON THEM OR SLIDE", "COO ALL YOU WANT. MOVE!"),
    ("GLASS GARDENS", "night", "ink", "deep", "ink", "deep", "ink", "mint", "lime", "domes", "",
     "NEW: SKYLIGHTS CRACK - DON'T STOP ON GLASS", "NO BATHS TONIGHT, THANKS."),
    ("NEON ROW", "night", "purple", "ink", "deep", "purple", "ink", "lavender", "pink", "neon", "",
     "NEW: SLIDE UNDER THE BILLBOARDS", "SO BRIGHT... SO FAST!"),
    ("TRAM TOWN", "night", "deep", "ink", "deep", "blue", "ink", "sky", "yellow", "tram", "",
     "NEW: JUMP UP TO GRAB THE TRAM WIRES", "ALL ABOARD THE CLAW EXPRESS."),
    ("WINDY HEIGHTS", "ink", "deep", "night", "ink", "darkgray", "black", "lavender", "sky", "clouds", "wind",
     "NEW: WIND GUSTS AND UPDRAFT VENTS", "MY WHISKERS ARE FLAPPING!"),
    ("ANTENNA ALLEY", "night", "ink", "ink", "deep", "choco", "ink", "peach", "mint", "antennas", "",
     "NEW: SPIKY ANTENNAS AND ZAPPY WIRES", "OUCH-Y ROOFS. NOTED."),
    ("RAINY ROOFTOPS", "black", "ink", "night", "ink", "ink", "black", "gray", "sky", "moon", "rain",
     "RAIN! EVERYTHING MIXES FROM HERE ON", "WET PAWS. GRUMPY CAT."),
    ("CLOCK TOWERS", "night", "deep", "ink", "deep", "brown", "choco", "cream", "yellow", "clock", "",
     "NEW: WINDOW-WASHER LIFTS", "TICK TOCK, GULLY!"),
    ("LANTERN FAIR", "night", "purple", "ink", "deep", "choco", "black", "peach", "orange", "lanterns", "",
     "NEW: SWINGING LANTERN LINES", "OOH, PRETTY. FOCUS, TORA."),
    ("SNOWY EAVES", "ink", "deep", "night", "ink", "gray", "darkgray", "white", "peach", "moon", "snow",
     "NEW: WATCH OUT FOR FALLING ICICLES", "COLD BEANS! COLD PAWS!"),
    ("MOON DOMES", "night", "deep", "ink", "deep", "deep", "ink", "lavender", "yellow", "domes", "",
     "NEW: PIGEON FLOCKS", "THE WHOLE COO CREW?!"),
    ("SKY BRIDGES", "night", "blue", "ink", "deep", "blue", "night", "sky", "white", "towers", "",
     "NEW: WIRE CHAINS OVER THE BIG DROPS", "DON'T LOOK DOWN. OK, I LOOKED."),
    ("FIREWORK FEST", "night", "purple", "ink", "deep", "purple", "night", "pink", "yellow", "fireworks", "",
     "NEW: FIREWORK PADS LAUNCH YOU SKY HIGH", "WHEEE-OW!"),
    ("FOGGY DOCKS", "ink", "darkgray", "deep", "ink", "darkgray", "ink", "gray", "peach", "sea", "fog",
     "NEW: GULLY'S COUSINS DIVE AT YOU", "SMELLS FISHY OUT HERE."),
    ("CRANE YARD", "night", "deep", "ink", "deep", "brown", "black", "orange", "yellow", "cranes", "",
     "EVERY TRICK AT ONCE!", "BIG MACHINES, SMALL CAT."),
    ("STORM FRONT", "black", "ink", "night", "ink", "ink", "black", "darkgray", "lavender", "clouds", "storm",
     "NEW: LIGHTNING RODS ZAP THE ROOF", "THUNDER IS JUST A BIG PURR..."),
    ("LIGHTHOUSE RUN", "night", "deep", "ink", "deep", "deep", "night", "cream", "yellow", "lighthouse", "",
     "THE LAST STRETCH - GET YOUR FISH BACK!", "THIS ENDS TONIGHT, GULLY."),
]

# a mechanic shows up from its district on (tier index)
INTRO = {"laundry": 1, "chimney": 2, "pigeon": 3, "glass": 4, "sprinkler": 4, "billboard": 5, "ac": 5,
         "wire": 6, "wind": 7, "updraft": 7, "antenna": 8, "spark": 8, "lift": 10, "sway": 11, "icicle": 12,
         "flock": 13, "chain": 14, "pad": 15, "diver": 16, "zap": 18}
SPOTLIGHT = {1: "laundry", 2: "chimney", 3: "pigeon", 4: "glass", 5: "billboard", 6: "wire", 7: "wind",
             8: "antenna", 10: "lift", 11: "laundry", 12: "icicle", 13: "flock", 14: "chain", 15: "pad",
             16: "diver", 18: "zap"}

NAMES = ["SARDINE SPRINT", "TIN ROOF TANGO", "MOONLIT MEOW", "WHISKER DASH", "PAWPRINT PATH", "GUTTER GALLOP",
         "PURR PARKOUR", "TILE TROT", "SOOTY SCAMPER", "TUNA TRAIL", "SKYLINE SKIP", "NIGHT NIBBLE",
         "ALLEY ZOOM", "STRAY STAMPEDE", "CLOTHESPIN CAPER", "SHINGLE SHUFFLE", "BRICK BOUNCE", "CREAM CHASE",
         "MACKEREL MILE", "FEATHER FRENZY", "SQUAWK SQUARE", "TAIL TWISTER", "LANTERN LEAP", "PIGEON PANIC",
         "CHIMNEY CHOMP", "GLASSY GLIDE", "ZIPLINE ZEST", "BREEZY BOLT", "STATIC STROLL", "PUDDLE PAWS",
         "CLOCKWORK CAT", "PAPER MOON", "SNOWBALL SKID", "STARGAZER SPRINT", "BRIDGE BOUNDER", "SPARKLER SPIN",
         "MISTY MARINA", "CRANE CRUISE", "THUNDER TROT", "BEACON BOLT", "ANCHOVY AVENUE", "SALMON SLIDE",
         "MOUSE MARCH", "CATNIP CORNER", "YOWL YARD", "FURBALL FLYER", "HISS HIGHWAY", "MITTEN MILE",
         "NAPTIME NOPE", "TOE BEAN TEMPO", "MEOWNTAIN PASS", "KITTY CORNICE", "BALCONY BEBOP", "EAVES EXPRESS",
         "ROOF RAMBLE", "GABLE GAMBIT", "SPIRE SPRINT", "WEATHERVANE WHIRL", "DORMER DASH", "SNOOT SCOOT",
         "PAW PATROL ROUTE", "SKY SARDINES", "MIDNIGHT MOUSER", "LAST TRAM HOME"]
BOSS_KINDS = ["gully", "bruno", "squad", "storm", "blimp"]
BOSS_NAMES = {"gully": "GULLY", "bruno": "BRUNO", "squad": "SGT. COO", "storm": "RUMBLE", "blimp": "GULLY BLIMP"}
BONUS_KINDS = ["market", "laundry"]
CAP_NAMES = ["BELL MAGNET", "UMBRELLA", "CATNIP RUSH", "FUR SHIELD", "MILK! +1 LIFE", "GOLD BELL"]


# ----------------------------------------------------------------------------- jump model
def jump_h(v0=JUMP_V):
    return v0 * v0 / (2 * G_UP)


def air_time(rise, v0=JUMP_V):
    """Seconds a full (held) jump takes to come down to a landing `rise` px above the take-off (negative: lower)."""
    h = jump_h(v0)
    if rise > h - 4:
        return 0.0
    return v0 / G_UP + math.sqrt(2 * (h - rise) / G_DOWN)


def max_gap(v, rise):
    """Widest plain gap allowed at nominal run speed v: measured at easy speed, with a margin for human timing."""
    return int(v * EASY * air_time(rise) * 0.72)


def run_speed(n):
    t, i = (n - 1) // 10, (n - 1) % 10
    return round(88 + 2.6 * t + 0.25 * i, 1)


# ----------------------------------------------------------------------------- builder
class Course:
    def __init__(self, rnd, tier, d, v, feats):
        self.rnd, self.tier, self.d, self.v, self.feats = rnd, tier, d, v, feats
        self.ents = []
        self.x = 0          # end of the open roof
        self.y = GROUND     # its height
        self.rx0 = 0        # its start
        self.glass_at = []  # (x0, x1) of skylights on the open roof

    def has(self, f):
        return f in self.feats

    def add(self, *e):
        self.ents.append(list(e))

    # ---- terrain
    def run(self, n):
        self.x += int(n)

    def close(self):
        """End the open roof at x (skylights split it into pieces)."""
        x0 = self.rx0
        for g0, g1 in self.glass_at:
            if g0 > x0:
                self.add("R", x0, g0, self.y, 0)
            self.add("R", g0, g1, self.y, 1)
            x0 = g1
        if self.x > x0:
            self.add("R", x0, self.x, self.y, 0)
        self.glass_at = []

    def gap(self, w, dy=0):
        self.close()
        self.x += int(w)
        self.y = max(Y_MIN, min(Y_MAX, self.y + int(dy)))
        self.rx0 = self.x

    def jumpable(self, dy):
        """A plain gap width for a height change dy (negative = the far roof is higher)."""
        lo = 18 + int(10 * self.d)
        hi = max(lo + 4, min(max_gap(self.v, -dy), 34 + int(44 * self.d)))
        return self.rnd.randint(lo, hi)

    # ---- pickups
    def fish_row(self, x, y, n, dx=14):
        if n > 0:
            self.add("F", int(x), max(FISH_TOP, int(y)), int(n), int(dx))

    def fish_arc(self, x0, x1, y, h, n=None):
        n = n or max(3, min(9, (x1 - x0) // 14 + 1))
        dx = max(8, (x1 - x0) // max(1, n - 1))
        y = max(FISH_TOP + 8, int(y))
        h = max(0, min(int(h), y - FISH_TOP))
        self.add("A", int(x0), y, int(n), int(dx), h)

    def golden(self, x, y):
        self.add("G", int(x), max(FISH_TOP, int(y)))

    # ---- chunks
    def c_flat(self, n=None):
        n = n or self.rnd.randint(70, 130)
        if self.rnd.random() < 0.7:
            self.fish_row(self.x + 14, self.y - 10, max(2, int(n) // 22), 18)
        self.run(n)

    def c_gap(self):
        dy = self.rnd.choice([0, 0, -16, 16, 24, -24 if self.d > 0.15 else 0, 32])
        dy = max(Y_MIN, min(Y_MAX, self.y + dy)) - self.y
        w = self.jumpable(dy)
        self.run(20)
        x0, y0 = self.x, self.y
        self.gap(w, dy)
        self.fish_arc(x0 - 12, self.x + 14, min(y0, self.y) - 12, 26 + self.rnd.randint(0, 12))
        self.run(40)

    def c_steps(self):
        up = self.rnd.random() < 0.5
        for _ in range(self.rnd.randint(2, 4)):
            dy = -16 if up else 16
            if not (Y_MIN + 20 <= self.y + dy <= Y_MAX):
                dy = -dy
            self.run(self.rnd.randint(36, 60))
            x0, y0 = self.x, self.y
            self.gap(self.rnd.randint(16, 18 + int(18 * self.d)), dy)
            self.fish_row(x0 + 2, min(y0, self.y) - 30, 2, 12)
        self.run(36)

    def c_crates(self):
        n = self.rnd.randint(1, 3 if self.d > 0.1 else 2)
        self.run(30)
        for i in range(n):
            stack = 2 if (self.d > 0.2 and self.rnd.random() < 0.3) else 1
            fishy = self.rnd.random() < 0.25
            for k in range(stack):
                kind = "C" if (fishy and k == stack - 1) else "X"
                self.add("S", kind, self.x, self.y - 14 * (k + 1), 14, 14)
            self.fish_arc(self.x - 24, self.x + 38, self.y - 14 * stack - 8, 18, 5)
            self.run(self.rnd.randint(70, 110))

    def c_drop(self):
        dy = self.rnd.choice([28, 36, 40])
        dy = min(Y_MAX, self.y + dy) - self.y
        self.run(24)
        x0 = self.x
        self.gap(self.jumpable(dy), dy)
        self.fish_row(x0 + 4, self.y - 40, 3, 14)
        self.run(50)

    def c_laundry(self):
        w = int(max_gap(self.v, 0) * self.rnd.uniform(1.3, 1.9)) + 20
        self.run(30)
        x0, y0 = self.x, self.y
        dy = self.rnd.choice([0, 0, 8, -8])
        sway = self.rnd.choice([3, 5, 6]) if self.has("sway") and self.rnd.random() < 0.6 else 0
        self.gap(w, dy)
        ly = max(y0, self.y) + 6 + sway
        self.add("L", x0 - 6, self.x + 6, ly, sway)
        self.fish_arc(x0 + 6, self.x - 6, ly - 50, 36)
        if self.rnd.random() < 0.3:
            self.golden((x0 + self.x) // 2, ly - 100)
        self.run(50)

    def c_chimney(self):
        tall = self.has("chimney") and self.rnd.random() < 0.55
        h = self.rnd.randint(64, 84) if tall else self.rnd.randint(28, 46)
        h = min(h, self.y - 46)
        w = self.rnd.choice([14, 18, 22])
        self.run(40)
        self.add("S", "K", self.x, self.y - h, w, h)
        if tall or self.rnd.random() < 0.3:
            if self.rnd.random() < 0.35:
                self.golden(self.x + w // 2, self.y - h - 12)
            else:
                self.fish_row(self.x + w // 2 - 7, self.y - h - 10, 2, 14)
        self.fish_row(self.x - 4, self.y - h // 2 - 8, 1)
        self.run(w + self.rnd.randint(60, 90))

    def c_pigeons(self):
        L = self.rnd.randint(150, 210)
        x0 = self.x
        n = 1 if self.d < 0.25 else self.rnd.randint(1, 2)
        for i in range(n):
            px = x0 + 90 + i * 60
            self.add("p", px, self.y, px - 40, px + 20)
        if self.rnd.random() < 0.6:
            low = self.rnd.random() < 0.5
            self.add("q", x0 + L + 40, self.y - (11 if low else 46))
            if low:
                self.fish_row(x0 + L - 20, self.y - 4, 3, 12)
        self.fish_row(x0 + 20, self.y - 10, 3, 16)
        self.run(L)

    def c_glass(self):
        self.run(60)
        for _ in range(self.rnd.randint(1, 3 if self.d > 0.3 else 2)):
            w = self.rnd.randint(20, 28)
            self.glass_at.append((self.x, self.x + w))
            self.fish_row(self.x + 2, self.y - 12, w // 12 + 1, 12)
            self.run(w)
            self.run(self.rnd.randint(24, 46))
        self.run(30)

    def c_sprinkler(self):
        self.run(70)
        for i in range(self.rnd.randint(1, 2)):
            self.add("s", self.x, self.y, self.rnd.randint(0, 23) * 10)
            self.fish_arc(self.x - 30, self.x + 30, self.y - 14, 26, 5)
            self.run(self.rnd.randint(90, 130))

    def c_billboard(self):
        w = self.rnd.randint(44, 72)
        self.run(50)
        bottom = self.y - 12
        top = bottom - self.rnd.randint(22, 28)
        self.add("S", "B", self.x, top, w, bottom - top)
        self.fish_row(self.x + 4, self.y - 5, w // 14, 14)
        self.fish_row(self.x + 8, top - 10, w // 18, 18)
        self.run(w + self.rnd.randint(60, 90))

    def c_ac(self):
        self.run(40)
        for i in range(self.rnd.randint(1, 3)):
            w, h = self.rnd.randint(22, 30), self.rnd.randint(14, 22) + 6 * i
            self.add("S", "U", self.x, self.y - h, w, h)
            self.fish_row(self.x + 4, self.y - h - 10, 2, 12)
            self.run(w + self.rnd.randint(14, 40))
        self.run(50)

    def c_wire(self, chain=False):
        hgt = self.rnd.randint(44, 52)
        self.run(110)
        wy = self.y - hgt
        segs = self.rnd.randint(2, 3) if chain else 1
        wx0 = self.x - 90
        spark = 1 if self.has("spark") and self.rnd.random() < 0.5 else 0
        gw = int(max_gap(self.v, 0) * self.rnd.uniform(1.6, 2.3)) + 30 + (120 * (segs - 1))
        x0 = self.x
        self.gap(gw, 0)
        land = max(self.y, wy + HANG + 22)
        self.y = min(Y_MAX, land)
        # the wire (or a chain of wires with small hops between them) spans the drop
        span = self.x + 50 - wx0
        part = span // segs
        for k in range(segs):
            a = wx0 + k * part
            b = a + part - (16 if k < segs - 1 else 0)
            self.add("W", a, b, wy, spark if k == segs - 1 or not chain else 0)
            yy = wy
            self.fish_row(a + 20, yy + 10, max(1, (b - a - 30) // 22), 22)
        if self.rnd.random() < 0.4:
            self.golden(x0 + gw // 2, wy - 22)
        self.run(80)

    def c_wind(self):
        head = self.rnd.random() < 0.55
        L = self.rnd.randint(160, 240)
        self.add("N", self.x, self.x + L, 0 if head else 1)
        x0 = self.x
        self.run(30)
        for _ in range(self.rnd.randint(1, 2)):
            self.add("S", "X", self.x, self.y - 14, 14, 14)
            self.run(self.rnd.randint(60, 90))
        self.fish_row(x0 + 20, self.y - 30, L // 30, 26)
        self.x = max(self.x, x0 + L)
        self.run(30)

    def c_updraft(self):
        self.run(60)
        vx = self.x
        self.add("V", vx, self.y)
        self.fish_row(vx - 6, self.y - 60, 1)
        self.fish_row(vx - 6, self.y - 90, 1)
        self.run(36)
        rise = self.rnd.randint(52, 70)
        rise = min(rise, self.y - Y_MIN)
        self.gap(self.rnd.randint(14, 22), -rise)
        if self.rnd.random() < 0.4:
            self.golden(self.x + 30, self.y - 30)
        self.run(70)

    def c_antenna(self):
        self.run(70)
        for _ in range(self.rnd.randint(1, 3 if self.d > 0.45 else 2)):
            h = self.rnd.randint(10, 18)
            self.add("a", self.x, self.y, h)
            self.fish_arc(self.x - 28, self.x + 28, self.y - h - 10, 18, 5)
            self.run(self.rnd.randint(80, 120))

    def c_lift(self):
        self.run(30)
        x0, y0 = self.x, self.y
        n = 1 if self.d < 0.6 else self.rnd.randint(1, 2)
        lw = 44
        gw = 30 + n * (lw + 34)
        self.gap(gw, 0)
        for k in range(n):
            lx = x0 + 32 + k * (lw + 34)
            amp = self.rnd.randint(10, 18)
            self.add("M", lx, y0 + 10, lw, amp, self.rnd.randint(0, 62) * 10)
            self.fish_row(lx + 8, y0 - 18, 3, 12)
        self.run(60)

    def c_icicle(self):
        self.run(60)
        for _ in range(self.rnd.randint(1, 2)):
            self.add("i", self.x, self.y, self.y - self.rnd.randint(56, 70))
            self.fish_row(self.x - 20, self.y - 10, 3, 12)
            self.run(self.rnd.randint(100, 140))

    def c_flock(self):
        self.run(60)
        x0 = self.x
        n = self.rnd.randint(3, 5)
        low = self.rnd.random() < 0.5
        for k in range(n):
            self.add("q", x0 + 240 + k * 16, self.y - (11 if low else 44) - (abs(k - n // 2) * 6 if not low else 0))
        self.fish_row(x0 + 30, self.y - 10, 5, 18)
        self.run(200)

    def c_pad(self):
        self.run(50)
        self.add("J", self.x, self.y)
        self.fish_row(self.x - 4, self.y - 70, 1)
        self.fish_row(self.x + 6, self.y - 100, 1)
        self.run(26)
        rise = min(self.rnd.randint(70, 88), self.y - Y_MIN)
        self.gap(self.rnd.randint(16, 26), -rise)
        if self.rnd.random() < 0.5:
            self.golden(self.x + 26, self.y - 26)
        self.run(70)

    def c_diver(self):
        self.run(40)
        low = self.rnd.random() < 0.5
        self.add("d", self.x + 160, self.y - (6 if low else 24))
        self.fish_row(self.x + 40, self.y - 10, 4, 18)
        self.run(200)

    def c_zap(self):
        self.run(80)
        for _ in range(self.rnd.randint(1, 2)):
            self.add("z", self.x, self.y)
            self.fish_arc(self.x - 30, self.x + 30, self.y - 20, 22, 5)
            self.run(self.rnd.randint(110, 150))

    def c_capsule(self, k=None):
        if k is None:
            pool = [0, 0, 1, 2, 3, 3]
            if self.tier >= 9:
                pool += [1, 1]
            k = self.rnd.choice(pool)
        self.run(40)
        self.add("P", self.x, self.y - 34, k)
        self.run(60)

    def c_fishcrate(self):
        self.run(40)
        self.add("S", "C", self.x, self.y - 14, 14, 14)
        self.fish_row(self.x + 3, self.y - 30, 1)
        self.run(70)

    def finish(self, length=320):
        """The goal roof: flat, at a friendly height, with Gully's perch and the finish line."""
        target = GROUND if abs(self.y - GROUND) > 20 else self.y
        if self.y != target or self.rnd.random() < 0.5:
            self.run(20)
            dy = target - self.y
            self.gap(min(self.jumpable(dy), max_gap(self.v, -dy)), dy)
        self.run(length)
        self.add("E", self.x)
        self.run(400)           # extra roof past the line so Tora can skid to a stop
        self.close()


# ----------------------------------------------------------------------------- stages
def chunk_pool(tier, feats, spot):
    """(name, weight) pairs for a normal stage."""
    pool = [("flat", 2), ("gap", 6), ("steps", 2), ("crates", 3), ("drop", 2), ("fishcrate", 1)]
    w = {"laundry": 3, "chimney": 3, "pigeon": 3, "glass": 2, "sprinkler": 2, "billboard": 2, "ac": 2, "wire": 2,
         "wind": 2, "updraft": 1, "antenna": 2, "lift": 2, "icicle": 2, "flock": 2, "chain": 1, "pad": 2,
         "diver": 2, "zap": 2}
    for f, wt in w.items():
        if f in feats:
            pool.append((f, wt * (3 if f == spot else 1)))
    return pool


def features(tier):
    return {f for f, t in INTRO.items() if t <= tier}


def build_normal(n, rnd):
    tier, i = (n - 1) // 10, (n - 1) % 10
    d = min(1.0, (tier * 10 + i) / 190)
    v = run_speed(n)
    feats = features(tier)
    spot = SPOTLIGHT.get(tier)
    mods = []
    # stage modifiers for variety
    roll = rnd.random()
    if i in (3, 7) and roll < 0.5:
        mods.append("fishy")
    elif i in (2, 8) and roll < 0.4 and tier >= 2:
        mods.append("gold")
    elif i == 6 and tier >= 1:
        mods.append("fast")
        v = round(v * 1.08, 1)
    c = Course(rnd, tier, d, v, feats)
    c.run(240)
    c.fish_row(120, GROUND - 10, 4, 18)
    length = 2200 + 120 * tier + 40 * i
    pool = chunk_pool(tier, feats, spot)
    names = [p[0] for p in pool]
    weights = [p[1] for p in pool]
    last = None
    since_cap = 0
    first = True
    while c.x < length:
        if first and spot and i in (0, 1):     # the district's first stage opens with its new trick
            pick = spot
        else:
            pick = rnd.choices(names, weights)[0]
            if pick == last and pick not in ("gap", "flat"):
                pick = "gap"
        first = False
        last = pick
        {"flat": c.c_flat, "gap": c.c_gap, "steps": c.c_steps, "crates": c.c_crates, "drop": c.c_drop,
         "fishcrate": c.c_fishcrate, "laundry": c.c_laundry, "chimney": c.c_chimney, "pigeon": c.c_pigeons,
         "glass": c.c_glass, "sprinkler": c.c_sprinkler, "billboard": c.c_billboard, "ac": c.c_ac,
         "wire": c.c_wire, "chain": lambda: c.c_wire(chain=True), "wind": c.c_wind, "updraft": c.c_updraft,
         "antenna": c.c_antenna, "lift": c.c_lift, "icicle": c.c_icicle, "flock": c.c_flock, "pad": c.c_pad,
         "diver": c.c_diver, "zap": c.c_zap}[pick]()
        since_cap += 1
        if since_cap >= rnd.randint(6, 9):
            since_cap = 0
            c.c_capsule()
        # breather between chunks shrinks as the districts go by
        c.c_flat(rnd.randint(40, 70) + int(50 * (1 - d)))
    if "gold" in mods:
        for _ in range(3):
            c.golden(rnd.randint(400, length - 200), rnd.randint(60, 90))
    c.finish()
    if "fishy" in mods:
        extra = []
        for e in c.ents:
            if e[0] == "F" and e[2] - 16 >= FISH_TOP:
                extra.append(["F", e[1], e[2] - 16, e[3], e[4]])
        c.ents.extend(extra)
    # weather / district twists
    th = THEMES[tier]
    if th[10]:
        mods.append(th[10])
    return c, v, mods


def build_bonus(n, rnd):
    tier = (n - 1) // 10
    v = run_speed(n)
    kind = BONUS_KINDS[(n // 10) % 2]
    c = Course(rnd, tier, 0.1, v, {"laundry"})
    c.run(200)
    c.add("P", 140, GROUND - 30, 2)       # catnip rush right away
    length = 2300
    while c.x < length:
        if kind == "laundry":
            c.run(40)
            x0 = c.x
            w = rnd.randint(150, 230)
            y0 = c.y
            c.gap(w, rnd.choice([0, -8, 8]))
            ly = max(y0, c.y) + 8
            c.add("L", x0 - 6, c.x + 6, ly, 4 if tier >= 11 else 0)
            for k in range(3):
                c.fish_arc(x0 + 10 + k * 8, c.x - 10, ly - 40 - 22 * k, 30 + 6 * k)
            c.golden((x0 + c.x) // 2, ly - 118)
            c.run(30)
        else:
            c.fish_row(c.x + 10, c.y - 10, 8, 14)
            c.run(60)
            c.add("S", "C", c.x, c.y - 14, 14, 14)
            c.run(40)
            c.fish_arc(c.x, c.x + 70, c.y - 14, 34, 6)
            c.run(80)
            if rnd.random() < 0.6:
                x0 = c.x
                c.gap(rnd.randint(30, 50), rnd.choice([0, -16, 16]))
                c.fish_arc(x0 - 10, c.x + 10, c.y - 20, 40, 6)
                c.golden((x0 + c.x) // 2, c.y - 64)
            c.run(40)
    c.finish(260)
    return c, v, kind


def build_arena(n, rnd):
    """A boss arena: a 1600 px block of easy rooftops that repeats until the boss is beaten."""
    tier = (n - 1) // 10
    v = run_speed(n)
    c = Course(rnd, tier, 0.2, v, {"laundry"})
    L = 1600
    c.run(470)               # no pickups on the first screen: it is shown again after every wrap-around
    while c.x < L - 420:
        r = rnd.random()
        if r < 0.45:
            c.run(30)
            x0 = c.x
            c.gap(rnd.randint(18, 28), 0)
            c.fish_arc(x0 - 8, c.x + 8, GROUND - 12, 22, 4)
        elif r < 0.65:
            c.run(30)
            x0 = c.x
            c.gap(rnd.randint(90, 130), 0)
            c.add("L", x0 - 6, c.x + 6, GROUND + 6, 0)
            c.fish_arc(x0 + 6, c.x - 6, GROUND - 50, 30)
        else:
            c.run(40)
        c.run(rnd.randint(140, 220))
    c.x = L
    c.close()
    # the first screen of the block again after its end (and the last one before its start), so the
    # wrap-around is seamless
    for e in list(c.ents):
        if e[0] == "R" and e[1] < 440:
            c.add("R", e[1] + L, e[2] + L, e[3], e[4])
        if e[0] == "R" and e[2] > L - 400:
            c.add("R", e[1] - L, e[2] - L, e[3], e[4])
    return c, v, L


def boss_spec(n):
    tier = (n - 1) // 10
    kind = BOSS_KINDS[tier % 5]
    lv = tier // 5               # 0..3: each lap of the five bosses gets meaner
    hp = {"gully": 3, "bruno": 4, "squad": 4, "storm": 4, "blimp": 4}[kind] + lv + (2 if n == 200 else 0)
    return {"kind": kind, "name": BOSS_NAMES[kind], "hp": hp, "lv": lv, "final": n == 200,
            "rate": round(1.0 + 0.12 * lv + 0.01 * tier, 2)}


def encode(ents):
    return ";".join(",".join(str(f) for f in e) for e in ents)


def decode(s):
    out = []
    for part in s.split(";"):
        if not part:
            continue
        f = part.split(",")
        if f[0] == "S":
            out.append([f[0], f[1]] + [int(v) for v in f[2:]])
        else:
            out.append([f[0]] + [int(v) for v in f[1:]])
    return out


def fish_points(e):
    """World positions of the fish in an F (row) or A (arc) entity - integer maths, same on iOS."""
    t, x, y, n, dx = e[0], e[1], e[2], e[3], e[4]
    if t == "F":
        return [(x + k * dx, y) for k in range(n)]
    h = e[5]
    m = max(1, n - 1)
    return [(x + k * dx, y - (4 * h * k * (m - k)) // (m * m)) for k in range(n)]


def build_stage(n):
    rnd = random.Random(7919 * n + 17)
    tier = (n - 1) // 10
    used = set()
    st = {"n": n, "tier": tier, "kind": "normal", "new": "", "mods": [], "bonus": "", "boss": None, "loop": 0}
    if n % 10 == 0:
        c, v, loop = build_arena(n, rnd)
        st.update(kind="boss", boss=boss_spec(n), loop=loop, name=BOSS_NAMES[BOSS_KINDS[tier % 5]])
        st["len"] = 0
    elif n % 10 == 5:
        c, v, kind = build_bonus(n, rnd)
        st.update(kind="bonus", bonus=kind, name="FISH MARKET RUSH" if kind == "market" else "SKY LAUNDRY")
    else:
        c, v, mods = build_normal(n, rnd)
        st["mods"] = mods
        k = n - 1 - (n // 10) - ((n + 5) // 10)          # index among the normal stages (0..159)
        st["name"] = NAMES[(k * 29) % len(NAMES)]
        if n % 10 == 1:
            st["new"] = THEMES[tier][11]
        elif "fast" in mods:
            st["new"] = "NIGHT SPRINT: A LITTLE FASTER!"
        elif "fishy" in mods:
            st["new"] = "FISHY STAGE: DOUBLE THE FISH!"
        elif "gold" in mods:
            st["new"] = "GOLD RUSH: EXTRA GOLDEN FISH UP HIGH"
    del used
    ents = sorted(c.ents, key=lambda e: (e[0] != "R", e[1] if e[0] != "S" else e[2]))
    st["speed"] = v
    fin = [e for e in ents if e[0] == "E"]
    st["len"] = fin[0][1] if fin else 0
    st["fish"] = sum(len(fish_points(e)) for e in ents if e[0] in "FA")
    st["c"] = encode(ents)
    return st


def build_campaign():
    return [build_stage(n) for n in range(1, STAGES_N + 1)]


STAGES_N = 200


# ----------------------------------------------------------------------------- validation
def validate(st):
    """Returns a list of problems (empty = the stage can be cleared with the base moves at easy speed)."""
    errs = []
    ents = decode(st["c"])
    v = st["speed"]
    roofs = sorted([e for e in ents if e[0] == "R"], key=lambda e: e[1])
    lines = [e for e in ents if e[0] == "L"]
    wires = [e for e in ents if e[0] == "W"]
    lifts = [e for e in ents if e[0] == "M"]
    vents = [e for e in ents if e[0] == "V"]
    pads = [e for e in ents if e[0] == "J"]
    boxes = [e for e in ents if e[0] == "S"]
    hz = [e for e in ents if e[0] in "pqsaidz"]
    if not roofs or roofs[0][1] > 0:
        errs.append("course must start on a roof at x=0")
    for r in roofs:
        if not (Y_MIN <= r[3] <= Y_MAX):
            errs.append(f"roof height {r[3]} out of range")
        if r[2] <= r[1]:
            errs.append(f"empty roof at {r[1]}")
        if r[4] and r[2] - r[1] > 28:
            errs.append(f"skylight too long at {r[1]}")
    # walk the roofs left to right: every hole must be crossable
    for a, b in zip(roofs, roofs[1:]):
        if b[1] < a[2]:
            errs.append(f"overlapping roofs at {b[1]}")
            continue
        g0, g1 = a[2], b[1]
        if b[4] and g1 - g0 > 0:
            errs.append(f"skylight right after a gap at {g1}")
        if a[4] and g1 - g0 > 0:
            errs.append(f"gap right after a skylight at {g0}")
        rise = a[3] - b[3]      # positive: the next roof is higher
        if g1 == g0:
            if rise > 0 and rise > 56 and not any(abs(p[1] - a[2]) < 60 for p in pads + vents) and st["tier"] < 2:
                errs.append(f"wall {rise} too tall before wall-kicks at {g0}")
            continue
        w = g1 - g0
        if any(l[1] <= g0 + 4 and l[2] >= g1 - 4 and l[3] >= max(a[3], b[3]) + 2 for l in lines):
            continue
        inside = sorted([m for m in lifts if m[1] >= g0 and m[1] + m[3] <= g1], key=lambda m: m[1])
        if inside:
            edges = [g0] + [p for m in inside for p in (m[1], m[1] + m[3])] + [g1]
            for k in range(0, len(edges), 2):
                if edges[k + 1] - edges[k] > 40:
                    errs.append(f"lift hop {edges[k + 1] - edges[k]} too wide at {edges[k]}")
            for m in inside:
                if m[2] - m[4] < a[3] - 24 or m[2] + m[4] > a[3] + 34:
                    errs.append(f"lift travel out of reach at {m[1]}")
            continue
        wired = [x for x in wires if x[1] < g0 - 40 and x[2] > g0]
        if wired:
            chain = sorted([x for x in wires if x[2] > g0 - 60 and x[1] < g1 + 60], key=lambda x: x[1])
            if chain[-1][2] < g1 + 20:
                errs.append(f"wire ends before the far roof at {g1}")
            hgt = a[3] - wired[0][3]
            if not (36 <= hgt <= jump_h() - 4 + HANG - 6):
                errs.append(f"wire height {hgt} not grabbable at {g0}")
            if b[3] < chain[-1][3] + HANG + 4:
                errs.append(f"roof under wire end too high at {g1}")
            for p, q in zip(chain, chain[1:]):
                if q[1] - p[2] > 24 or abs(q[3] - p[3]) > 8:
                    errs.append(f"wire chain hop too hard at {p[2]}")
            continue
        if rise > 0 and any(g0 - 60 <= vv[1] <= g0 for vv in vents + pads):
            if w > 40:
                errs.append(f"updraft gap too wide at {g0}")
            continue
        lim = max_gap(v, rise) + 6
        if w > lim:
            errs.append(f"gap {w} > {lim} at {g0} (rise {rise})")
        if rise > jump_h() - 10:
            errs.append(f"far roof {rise} too high to jump at {g0}")
    # skylights never sit in a landing zone: 50 px of plain roof after every hole
    run_start = None
    for k, r in enumerate(roofs):
        if k == 0 or roofs[k - 1][2] != r[1] or roofs[k - 1][3] != r[3]:
            run_start = r[1]
        if r[4] and k > 0 and r[1] - run_start < 50:
            errs.append(f"skylight in a landing zone at {r[1]}")
    for e in boxes:
        k, x, y, w, h = e[1:]
        roof = next((r for r in roofs if r[1] <= x and x + w <= r[2]), None)
        if roof is None:
            errs.append(f"box {k} not on one roof at {x}")
            continue
        if k == "B":
            clear = roof[3] - (y + h)
            if clear < SLIDE_H + 3 or clear >= STAND_H:
                errs.append(f"billboard clearance {clear} at {x}")
            if roof[3] - y > jump_h() - 8:
                errs.append(f"billboard too tall at {x}")
        elif y + h != roof[3] and not any(o is not e and o[2] <= x < o[2] + o[4] and o[3] == y + h for o in boxes):
            errs.append(f"box {k} floating at {x}")
        if k == "K" and roof[3] - y > 90:
            errs.append(f"chimney too tall at {x}")
        if k == "K" and roof[3] - y > jump_h() - 8 and st["tier"] < INTRO["chimney"]:
            errs.append(f"tall chimney before wall-kicks at {x}")
    for e in hz:
        x = e[1]
        landing = [r for r in roofs if r[1] <= x <= r[2]]
        if e[0] in "psaz" and not landing:
            errs.append(f"hazard {e[0]} not on a roof at {x}")
        for r in landing:
            prev = [q for q in roofs if q[2] <= r[1]]
            if prev and prev[-1][2] < r[1] and x - r[1] < 40 and e[0] in "asz":
                errs.append(f"hazard {e[0]} in a landing zone at {x}")
    for e in ents:
        if e[0] in "FA":
            for fx, fy in fish_points(e):
                if not (FISH_TOP <= fy <= 190):
                    errs.append(f"fish out of reach at {fx},{fy}")
    if st["kind"] != "boss":
        fin = [e for e in ents if e[0] == "E"]
        if len(fin) != 1:
            errs.append("needs exactly one finish line")
        else:
            fx = fin[0][1]
            goal = next((r for r in roofs if r[1] <= fx - 200 and fx + 60 <= r[2]), None)
            if goal is None:
                errs.append("the finish needs a long flat roof")
    return errs


CAMPAIGN = build_campaign()
