"""ROOFTOP RUN pixel art and songs (original characters drawn for MOCHI ARCADE).

TORA - a tiger-striped street cat with a notched ear and a red bandana.
GULLY - the smug seagull who stole her fish.   Pigeons, fish coins and friends.
Registered into sprites.ART / music.SONGS at import, so the iOS port gets them through gen_data.
"""
from mochi_arcade import music, sprites


def _grid(w, h):
    return [["."] * w for _ in range(h)]


def _stamp(g, rows, x0, y0):
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != "." and 0 <= y0 + y < len(g) and 0 <= x0 + x < len(g[0]):
                g[y0 + y][x0 + x] = ch
    return g


def _rows(g):
    return ["".join(r) for r in g]


# ----------------------------------------------------------------------------- Tora (20 x 16, facing right)
HEADS = {
    "norm": ["..k.....k.",
             ".kok...kpk",
             "kononnonok",
             "kooooooook",
             "kookoookok",
             "kookoookok",
             "koowwpwwok",
             "kowwkwkwwk",
             ".kkwwwwkk.",
             "...kkkk..."],
    "happy": ["..k.....k.",
              ".kok...kpk",
              "kononnonok",
              "kooooooook",
              "kokokokook",
              "kooooooook",
              "kpowwpwwpk",
              "kowkwwwkwk",
              ".kkwkkkwk.",
              "...kkkk..."],
    "hurt": ["..k.....k.",
             ".kok...kpk",
             "kononnonok",
             "kokokokook",
             "kookoookok",
             "kokokokook",
             "koowwpwwok",
             "kowwwkwwwk",
             ".kkwkwkkk.",
             "...kkkk..."],
    "wow": ["..k.....k.",
            ".kok...kpk",
            "kononnonok",
            "kowwoowwok",
            "kowkoowkok",
            "kowwoowwok",
            "koowwpwwok",
            "kowwwkwwwk",
            ".kkwkkwkk.",
            "...kkkk..."],
}

# body layers: tail + torso + legs (the head is stamped on top at x=9)
_TORSO = ["..knononnok.",
          ".koooooooork",
          ".koonoonoorr",
          ".kooooooooo.",
          "..kkkkkkkkk."]
BODIES = {
    "run0": (["....kk", "...kok", "..kok.", ".kok..", "kok..."], [  # legs stretched out
        "..kwk.....kwk.",
        ".kwk.......kwk",
        "kk..........kk"]),
    "run1": (["...kk.", "..kok.", "..kok.", ".kok..", ".kok.."], [
        "...kwk...kwk..",
        "...kwk....kwk.",
        "....kk.....kk."]),
    "run2": (["....kk", "...kok", "..kok.", ".kok..", "kok..."], [  # legs gathered
        "....kwkkwk....",
        "....kwwwwk....",
        ".....kkkk....."]),
    "run3": (["...kk.", "..kok.", "..kok.", ".kok..", ".kok.."], [
        "..kwk...kwk...",
        ".kwk.....kwk..",
        ".kk.......kk.."]),
}


SCARF = ["krrrrk", ".krrk.", "..kk.."]


def _head(g, kind, x, y, scarf=True):
    _stamp(g, HEADS[kind], x, y)
    if scarf:
        _stamp(g, SCARF, x + 2, y + 9)


def _tora(body, head="norm", head_dy=0, torso_dy=0):
    g = _grid(20, 16)
    tl, lg = BODIES[body]
    _stamp(g, tl, 0, 3 + torso_dy)
    _stamp(g, _TORSO, 2, 8 + torso_dy)
    _stamp(g, lg, 2, 13)
    _head(g, head, 9, 0 + head_dy)
    return _rows(g)


def _jump():
    g = _grid(20, 16)
    _stamp(g, ["kk....", "kok...", ".kok..", "..kok.", "...kok"], 0, 2)
    _stamp(g, _TORSO, 2, 7)
    _stamp(g, ["..kwk..kwk....", "..kwk...kwk...", "..kk.....kk..."], 2, 12)
    _head(g, "norm", 9, 0)
    return _rows(g)


def _fall():
    g = _grid(20, 16)
    _stamp(g, ["......", "kk....", "kok...", ".kok..", "..kok."], 0, 2)
    _stamp(g, _TORSO, 2, 6)
    _stamp(g, [".kwk......kwk..", "kwk........kwk.", "kk..........kk."], 1, 11)
    _head(g, "wow", 9, 0)
    return _rows(g)


def _pounce():
    g = _grid(20, 16)
    _stamp(g, ["kk.....", ".kok...", "..kok..", "...kok."], 0, 0)
    _stamp(g, _TORSO, 3, 4)
    _stamp(g, ["...........kwk", "..........kwk.", "..kwk.....kk..", "..kk.........."], 4, 9)
    _head(g, "wow", 10, 3, False)
    return _rows(g)


def _slide():
    # stretched flat along the roof: 20 x 16 canvas, only the bottom 8 rows used
    g = _grid(20, 16)
    _stamp(g, ["kkk.......", "kookkkkkkk"], 0, 9)
    _stamp(g, [".kononnonok.", ".koooooooork", "kwkkwkkkwkrr"], 2, 10)
    _stamp(g, ["..k...k.",
               ".kok.kpk",
               "konnonok",
               "kookookk",
               "koowpwok",
               ".kkkkkk."], 12, 8)
    _stamp(g, ["kwwk......kwwk.", "kkkk......kkkk."], 1, 13)
    _stamp(g, ["krrk", ".kk."], 13, 13)
    return _rows(g)


def _cling():
    # paws on a wall to the right, tail hanging down
    g = _grid(20, 16)
    _stamp(g, ["..knononnok.", ".koooooooork", ".koonoonoorr", ".kooooooooo.", "..kkkkkkkkk."], 2, 6)
    _stamp(g, ["..k...", "..kok.", "...kok", "....kk"], 0, 11)
    _stamp(g, ["kwk", "kwk", "kk."], 10, 11)
    _stamp(g, ["kwwk", "kkk."], 15, 5)
    _stamp(g, ["kwwk", "kkk."], 15, 11)
    _head(g, "wow", 9, 0)
    return _rows(g)


def _idle(blink):
    g = _grid(20, 16)
    _stamp(g, ["...kk.", "..kok.", "..kok.", "..kok.", "...kok"], 0, 3)
    _stamp(g, _TORSO, 2, 8)
    _stamp(g, ["..kwk.....kwk.", "..kwk.....kwk.", "..kkk.....kkk."], 2, 13)
    h = HEADS["norm"][:]
    if blink:
        h = h[:4] + ["kooooooook", "kokkookkok"] + h[6:]
    _stamp(g, h, 9, 1)
    _stamp(g, SCARF, 11, 10)
    return _rows(g)


def _happy(paw):
    g = _grid(20, 16)
    _stamp(g, ["kk....", "kok...", ".kok..", "..kok.", "...kok"], 0, 2)
    _stamp(g, _TORSO, 2, 8)
    _stamp(g, ["..kwk.....kwk.", "..kwk.....kwk.", "..kkk.....kkk."], 2, 13)
    _head(g, "happy", 9, 0 if paw else 1)
    if paw:
        _stamp(g, ["kwk", "kwk", "kok"], 17, 8)
    return _rows(g)


def _hurt():
    g = _grid(20, 16)
    _stamp(g, ["......", "......", "kk....", "kok...", ".kok.."], 0, 5)
    _stamp(g, _TORSO, 2, 8)
    _stamp(g, ["kwk......kwk..", ".kwk....kwk...", "..kk....kk...."], 2, 13)
    _head(g, "hurt", 9, 1)
    return _rows(g)


TORA = {
    "rr_tora_run": [_tora("run0"), _tora("run1", head_dy=1, torso_dy=1), _tora("run2"), _tora("run3", head_dy=1, torso_dy=1)],
    "rr_tora_jump": [_jump()],
    "rr_tora_fall": [_fall()],
    "rr_tora_pounce": [_pounce()],
    "rr_tora_slide": [_slide()],
    "rr_tora_cling": [_cling()],
    "rr_tora_idle": [_idle(False), _idle(True)],
    "rr_tora_happy": [_happy(True), _happy(False)],
    "rr_tora_hurt": [_hurt()],
}

# ----------------------------------------------------------------------------- Gully the seagull (22 x 16, facing left)
_GULLY_BODY = [
    "......kkkk............",
    ".....kwwwwk...........",
    "....kwwwwwwk..........",
    "...kwwkkwwwk..........",
    "kkkyykwkwwwk..........",
    "ksyyyywwwwwwk.........",
    "kssskyywwwwwwkk.......",
    ".kssk.kwwwwwwwwkkkk...",
    "..kk...kwwwwwwwwwwwkk.",
    ".......kwwwwwwwwwwggk.",
    "........kwwwwwwwwgk...",
    ".........kkwwwwkkk....",
    "...........kokok......",
    "..........kok.kok.....",
    "..........kk...kk.....",
    "......................",
]
_WING_UP = ["......kk", ".....kgk", "....kggk", "...kgggk", "..kgggk.", ".kgggk..", "kgggk...", ".kkk...."]
_WING_DN = ["kkkkkk..", "kggggkk.", ".kgggggk", "..kkgggk", "....kkk."]


def _gully(wing, fish=True):
    g = _grid(22, 16)
    _stamp(g, _GULLY_BODY, 0, 0)
    if not fish:
        for y in range(4, 9):
            g[y] = [("." if ch == "s" else ch) for ch in g[y]]
        g[5][1] = "y"
        g[6][1] = "."
        g[6][2] = "."
        g[6][3] = "."
        g[6][4] = "k"
        g[7] = list("......kwwwwwwwwkkkk...")
        g[8] = list("..k....kwwwwwwwwwwwkk.")
        g[8][2] = "."
    if wing == 0:
        _stamp(g, _WING_UP, 10, 0)
    else:
        _stamp(g, _WING_DN, 10, 7)
    return _rows(g)


GULLY = {
    "rr_gully": [_gully(0), _gully(1)],
    "rr_gully_nofish": [_gully(0, False), _gully(1, False)],
    "rr_gully_dead": [_gully(1, False)[::-1]],
}

# ----------------------------------------------------------------------------- pigeons (12 x 10, facing left)
_PIGEON = [
    "..kkk.......",
    ".kgggk......",
    "okgkgk......",
    ".kgggtk.....",
    "..ktttgkkkk.",
    "..kgggggggdk",
    "..kggggdddk.",
    "...kggggdk..",
    "....kkkk....",
    "....o..o....",
]
_PIGEON2 = _PIGEON[:7] + ["...kggggdk..", "....kkkk....", "...o....o..."]
_PIGEON_FLY = [
    "......kk....",
    "..kkk.kdk...",
    ".kgggkkddk..",
    "okgkgkkgddk.",
    ".kgggtkggdk.",
    "..ktttgggkkk",
    "..kgggggggdk",
    "...kgggdddk.",
    "....kkkkkk..",
    "............",
]
_PIGEON_FLY2 = [
    "............",
    "..kkk.......",
    ".kgggk......",
    "okgkgkkkkk..",
    ".kgggtkgggkk",
    "..ktttgggddk",
    "..kgggggdddk",
    "...kggkddddk",
    "....kkkkkkk.",
    "............",
]
PIGEON = {"rr_pigeon": [_PIGEON, _PIGEON2], "rr_pigeon_fly": [_PIGEON_FLY, _PIGEON_FLY2]}

# ----------------------------------------------------------------------------- pickups
FISH = {
    "rr_fish": [[
        ".kkkk..k",
        "kssssksk",
        "kswsssbk",
        "kssssksk",
        ".kkkk..k",
    ]],
    "rr_goldfish": [[
        "..kkkk...k",
        ".kyyyyk.ky",
        "kyywyyyyok",
        "kyyyyyyyok",
        ".kyyyyk.ko",
        "..kkkk...k",
    ]],
    "rr_feather": [[
        "......kk",
        ".....kwk",
        "....kwgk",
        "...kwwk.",
        "..kwgk..",
        ".kwwk...",
        ".kgk....",
        "kk......",
    ]],
    "rr_head": [[    # HUD life icon
        "k.....k",
        "kok.kok",
        "kooooook",
        "kokoook",
        "kowpwok",
        ".kkkkk.",
    ]],
}
FISH["rr_head"] = [[
    "k.....k.",
    "kok.kpk.",
    "konnnok.",
    "kokookk.",
    "kowpwok.",
    ".kkkkk..",
]]

MY_ART = {}
MY_ART.update(TORA)
MY_ART.update(GULLY)
MY_ART.update(PIGEON)
MY_ART.update(FISH)
sprites.ART.update(MY_ART)


# ----------------------------------------------------------------------------- songs (original)
def _bass(roots):
    return " ".join(" ".join(f"{n}:8" for n in (r + "2", r + "3") * 4) for r in roots)


music.SONGS.update({
    # "Rooftop Rush" - districts 1-10 (D major, bright and bouncy)
    "rr_run": {"bpm": 152, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "D5:8 F#5:8 A5:8 D6:8 C#6:8 A5:8 F#5:4  G5:8 B5:8 D6:8 B5:8 A5:4 F#5:4 "
            "E5:8 G5:8 B5:8 E6:8 D6:8 B5:8 G5:4  A5:8 C#6:8 E6:8 C#6:8 A5:2 "
            "B5:8 A5:8 F#5:8 D5:8 E5:8 F#5:8 A5:4  G5:8 F#5:8 E5:8 D5:8 B4:4 D5:4 "
            "E5:8 F#5:8 G5:8 B5:8 A5:8 G5:8 F#5:8 E5:8  D5:4 A5:8 F#5:8 D5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": _bass(["D", "G", "E", "A", "B", "G", "A", "D"])},
        {"wave": "drums", "vol": 1, "notes": " ".join(["K:8 H:8 S:8 H:8 K:8 K:8 S:8 H:8"] * 8)},
    ]},
    # "Midnight Chase" - districts 11-20 (B minor, driving)
    "rr_chase": {"bpm": 160, "channels": [
        {"wave": "square", "duty": 0.125, "vol": 0.25, "notes":
            "B4:8 D5:8 F#5:8 B5:8 A5:8 F#5:8 D5:4  G4:8 B4:8 D5:8 G5:8 F#5:4 D5:4 "
            "A4:8 C#5:8 E5:8 A5:8 G5:8 E5:8 C#5:4  F#4:8 A#4:8 C#5:8 F#5:8 E5:4 C#5:4 "
            "D5:8 E5:8 F#5:8 A5:8 B5:4 A5:4  G5:8 F#5:8 E5:8 D5:8 E5:4 G5:4 "
            "F#5:8 E5:8 D5:8 C#5:8 D5:8 E5:8 F#5:8 A#5:8  B5:4 F#5:8 D5:8 B4:2"},
        {"wave": "triangle", "vol": 0.44, "gate": 0.6, "notes": _bass(["B", "G", "A", "F#", "D", "G", "F#", "B"])},
        {"wave": "drums", "vol": 1, "notes": " ".join(["K:8 H:8 S:8 H:8 K:8 H:8 S:8 S:8"] * 8)},
    ]},
})
