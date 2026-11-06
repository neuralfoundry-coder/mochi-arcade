"""HAIRBALL HAVOC pixel art (original): Biscuit the cream cat, the robo-toys, pets, pick-ups and upgrade icons.

Registered into sprites.ART at import (names prefixed "hh_"), so ios/tools/gen_data.py exports them to iOS too.
Characters: k=black i=ink w=white c=cream p=pink P=hotpink e=peach o=orange y=yellow l=lime m=mint t=teal
s=sky b=blue v=lavender u=purple n=brown h=choco g=gray d=darkgray r=red  .=clear
"""
from mochi_arcade import sprites


def _tr(rows, table):
    """Recolour rows with a {char: char} table (used to make animation frames)."""
    return ["".join(table.get(ch, ch) for ch in r) for r in rows]


def _with(rows, i, row):
    r = list(rows)
    r[i] = row
    return r


# ---------------------------------------------------------------- Biscuit (12x12): front / back / side (faces right)
_FRONT = [
    ".kk......kk.",
    ".kok....kpk.",
    "koockkkkcpck",
    "koooccccccck",
    "kookcccckcck",
    "kcokcccckcck",
    "kpcccppcccpk",
    "kccckcckccck",
    ".kcccccccck.",
    ".ktttyytttk.",
    "..kcccccck..",
    "..kwwkkwwk..",
]
_BACK = [
    ".kk......kk.",
    ".kck....kok.",
    "kcckkkkkkook",
    "kcccccccoook",
    "kcccccccoock",
    "kccccccccock",
    "kcccccccccck",
    ".kcccccccck.",
    ".kttttttttk.",
    "..kcccccck..",
    "..kccoocck..",
    "..kwwkkwwk..",
]
_SIDE = [
    "......k...k.",
    ".....kok.kpk",
    ".....kooccck",
    "kk..koocccck",
    "kok.kccckcck",
    "kok.kccckccp",
    ".kokccccpcck",
    "..kcccccccck",
    "..kcccctttk.",
    "..kccccccyk.",
    "..kccccccck.",
    "..kwk..kwk..",
]
_FW = ("..kwwkkwwk..", "..kwwk.kwwk.", ".kwwk.kwwk..")
_SW = ("..kwk..kwk..", "..kwk...kwk.", ".kwk..kwk...")

BISCUIT = {
    "hh_cat_front": [_with(_FRONT, 11, r) for r in _FW],
    "hh_cat_back": [_with(_BACK, 11, r) for r in _FW],
    "hh_cat_side": [_with(_SIDE, 11, r) for r in _SW],
}

# ---------------------------------------------------------------- robo-toys (face right; flip for left)
_MOUSE = [
    "..yyy.kk...",
    "...y.kppk..",
    "..kkkkkpkk.",
    "k.kgggggkgk",
    "k.kgggggggp",
    ".kkgwwwwgk.",
    "..kkkkkkk..",
    "...kk..kk..",
]
_MOUSE_B = _with(_with(_with(_MOUSE, 0, "...y..kk..."), 1, "..yyykppk.."), 7, "..kk..kk...")

_CAR = [
    "....yyy.....",
    ".....y......",
    "...kkkkkk...",
    "..krsssrrk..",
    ".krrrrrrrrrk",
    "krrrrrrrrrry",
    "krwwrrrrrrrk",
    ".kkdkkkkdkk.",
    "..kgk..kgk..",
]
_CAR_B = _with(_with(_CAR, 8, "..kdk..kdk.."), 0, "...y.y......")

_SOCK = [
    "..kkkkkk..",
    ".kwwwwwwk.",
    "kwwkwwkwwk",
    "kwwbwwbwwk",
    "kwwwwwwwwk",
    "kwkkkkkkwk",
    "kwwwwwwwwk",
    "krrrrrrrrk",
    "kwwwwwwwwk",
    "krrrrrrrrk",
    "kssssssssk",
    ".kkkkkkkk.",
]
_SOCK_B = _with(_with(_with(_SOCK, 4, "kwkkkkkkwk"), 5, "kPPPPPPPPk"), 6, "kwkkkkkkwk")

_VAC = [
    "...kkkkkk...",
    ".kkggggggkk.",
    "kggggrrggggk",
    "kggggggggggk",
    "kgddddddddgk",
    "kgdskddskdgk",
    "kgddddddddgk",
    "kggggggggggk",
    ".kkkkkkkkkk.",
    "..dd....dd..",
]
_VAC_B = _with(_with(_VAC, 9, ".d.d....d.d."), 2, "kggggyyggggk")

_DRUM = [
    ".kk......kk.",
    "knnk....knnk",
    "knnkkkkkknnk",
    ".knnnnnnnnk.",
    ".knknnnnknk.",
    ".knnneennnk.",
    ".yknnkknnky.",
    ".kkkkkkkkkk.",
    "kwwwwwwwwwwk",
    "krryrryrryrk",
    "krrrrrrrrrrk",
    ".kkkkkkkkkk.",
]
_DRUM_B = _with(_with(_DRUM, 6, "y.knnkknnk.y"), 5, ".knnneennnk.")

_BALL = [
    "...kkkk...",
    ".kkPPyykk.",
    ".kPPyyssk.",
    "kPPPyysssk",
    "kwPyyssswk",
    "kwwPyyswwk",
    "kPPPyysssk",
    ".kPPyyssk.",
    ".kkPPyykk.",
    "...kkkk...",
]
_SPIN3 = {"P": "s", "y": "P", "s": "y"}
_MINIBALL = [
    ".kkkk.",
    "kPPyyk",
    "kPyysk",
    "kyyssk",
    "kwsssk",
    ".kkkk.",
]

_PLANE = [
    "k.........",
    "kwk.......",
    "kwwkk.....",
    "kwwwwkkk..",
    "kwwwwwwwkk",
    "kvvvvkkk..",
    "kvvkk.....",
    "kk........",
]
_PLANE_B = ["." + r[:-1] if i in (0, 7) else r for i, r in enumerate(_PLANE)]

_POPBOX = [
    "kkkkkkkkkk",
    "kvvvvvvvvk",
    "kkkkkkkkkk",
    "kuuuuuuuuk",
    "kuuuyyuuuk",
    "kuuyyyyuuk",
    "kuuuyyuuuk",
    "kuuyuuyuuk",
    "kuuuuuuuuk",
    "kkkkkkkkkk",
]
_POPBOX_B = _with(_with(_POPBOX, 0, ".kkkkkkkkk"), 1, "kkvvvvvvvk")

_GOLEM = [
    "...kkkkkkkk...",
    "...kyyyyyyk...",
    "...kykyykyk...",
    "...kyyyyyyk...",
    "...kykkkkyk...",
    "kkkkkkkkkkkkkk",
    "krrksssssskllk",
    "krrkswwwwskllk",
    "krrkswsswskllk",
    "kkkkswwwwskkkk",
    "...kssssssk...",
    "...kkkkkkkk...",
    "...kookkook...",
    "...kkkkkkkk...",
]
_GOLEM_B = _with(_with(_GOLEM, 12, "..kook..kook.."), 13, "..kkkk..kkkk..")

_BLOCKLET = [
    "kkkkkk",
    "kyyyyk",
    "kkyykk",
    "kyyyyk",
    "kyyyyk",
    "kkkkkk",
]

_HELI = [
    "gggggggggggg",
    "......k.....",
    "....kkkkk...",
    "...kbbwwbk..",
    "kkkbbbbbbbk.",
    "k..kbbbbbk..",
    "....kkkkk...",
    "...k.....k..",
    "..kkkkkkkkk.",
]
_HELI_B = _with(_HELI, 0, "....gggg....")

_TOP = [
    "...kkkk...",
    ".kkoyoykk.",
    ".kyoyoyok.",
    "koyokkoyok",
    "kyokwwkoyk",
    "koykwwkyok",
    "kyoykkyoyk",
    ".koyoyoyk.",
    ".kkyoyokk.",
    "...kkkk...",
]
_SWAP_OY = {"o": "y", "y": "o"}

TOYS = {
    "hh_mouse": [_MOUSE, _MOUSE_B],
    "hh_car": [_CAR, _CAR_B],
    "hh_sock": [_SOCK, _SOCK_B],
    "hh_vac": [_VAC, _VAC_B],
    "hh_drum": [_DRUM, _DRUM_B],
    "hh_ball": [_BALL, _tr(_BALL, _SPIN3)],
    "hh_plane": [_PLANE, _PLANE_B],
    "hh_popbox": [_POPBOX, _POPBOX_B],
    "hh_golem": [_GOLEM, _GOLEM_B],
    "hh_heli": [_HELI, _HELI_B],
    "hh_top": [_TOP, _tr(_TOP, _SWAP_OY)],
    "hh_miniball": [_MINIBALL, _tr(_MINIBALL, _SPIN3)],
    "hh_blocklet": [_BLOCKLET],
}

# ---------------------------------------------------------------- pets
_KITTEN = [
    "kk....kk",
    "kgkkkkgk",
    "kggggggk",
    "kgkggkgk",
    "kggppggk",
    ".kggggk.",
    ".kgwwgk.",
    ".kk..kk.",
]
_HAMSTER = [
    ".kk..kk.",
    "kookkook",
    "kooooook",
    "kokookok",
    "kowppwok",
    "kowwwwok",
    ".kkkkkk.",
]
PETS = {
    "hh_kitten": [_KITTEN, _with(_KITTEN, 7, "..kk.kk.")],
    "hh_hamster": [_HAMSTER, _with(_HAMSTER, 6, ".kk..kk.")],
}

# ---------------------------------------------------------------- pick-ups (8x8) and upgrade icons
ITEMS = {
    "hh_yarn": [[
        "..kkkk..",
        ".kPpPpk.",
        "kPpPpPpk",
        "kpPpPpPk",
        "kPpPpPpk",
        ".kpPpPk.",
        "..kkkkPP",
        ".......P",
    ]],
    "hh_laser": [[
        "......kk",
        ".....krk",
        "....kgk.",
        "...kgk..",
        "..kgk...",
        ".kdk....",
        "kdk.r.r.",
        "kk...r..",
    ]],
    "hh_catnip": [[
        "....kk..",
        "...klk..",
        ".kkklkk.",
        "kllklllk",
        "kllllllk",
        ".kllllk.",
        "..kklk..",
        "....k...",
    ]],
    "hh_box": [[
        "kk....kk",
        "kekkkkek",
        "keeeeeek",
        "knnyynnk",
        "keeyyeek",
        "keeyyeek",
        "keeeeeek",
        "kkkkkkkk",
    ]],
    "hh_bomb": [[
        "......yo",
        ".....k..",
        "..kkkk..",
        ".knnnhk.",
        "knhnnnnk",
        "knnnhnnk",
        ".knhnnk.",
        "..kkkk..",
    ]],
    "hh_fish": [[
        "..kkkk.k",
        ".ksssskk",
        "kskssssk",
        ".ksssskk",
        "..kkkk.k",
    ]],
    "hh_tuna": [[
        ".kkkkkk.",
        "kyyyyyyk",
        "kwwwwwwk",
        "kssbbssk",
        "kwwwwwwk",
        "kyyyyyyk",
        ".kkkkkk.",
    ]],
    "hh_ic_rapid": [[
        "....kkk.",
        "...knnnk",
        "kk.knhnk",
        "...knnnk",
        ".kk.kkk.",
        "........",
        "kk.kk...",
    ]],
    "hh_ic_big": [[
        "..kkkk..",
        ".knnnnk.",
        "knnhnnnk",
        "knnnnhnk",
        "knhnnnnk",
        "knnnhnnk",
        ".knnnnk.",
        "..kkkk..",
    ]],
    "hh_ic_tail": [[
        "...k....",
        "..kyk...",
        ".kyyyk..",
        "kkkykkk.",
        "...yk...",
        "...ykk..",
        "...yyyk.",
        "....kk..",
    ]],
    "hh_ic_zoom": [[
        "....kkk.",
        "...kyyk.",
        "..kyyk..",
        ".kyyyykk",
        "kkkyyyk.",
        "..kyyk..",
        ".kyyk...",
        ".kkk....",
    ]],
    "hh_ic_bounce": [[
        "k......k",
        ".k....k.",
        "..k..k..",
        "...kk...",
        "........",
        "kkkkkkkk",
        "kddddddk",
    ]],
}

ART = {}
ART.update(BISCUIT)
ART.update(TOYS)
ART.update(PETS)
ART.update(ITEMS)
sprites.ART.update(ART)

# recolour tables shared with the iOS port (HairballHavocArt.swift has the same ones)
WHITE = {c: "w" for c in "iwcpPeoylmtsbvunhgdr"}         # hit flash: everything but the outline turns white
GOLDEN = {"g": "y", "w": "y", "d": "o", "y": "o", "p": "o"}  # the rare golden mouse
ELITE = {"g": "v", "w": "v", "r": "u", "s": "v", "b": "u", "n": "u", "y": "P", "o": "P", "l": "v"}
KITTEN_COATS = ({}, {"g": "o"}, {"g": "d"}, {"g": "w", "w": "c"})
BLOCK_COLOURS = ({}, {"y": "s"}, {"y": "l"}, {"y": "r"})
