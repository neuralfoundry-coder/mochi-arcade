"""Pixel art for MOCHI ARCADE (original characters, drawn for this project).

Characters: k=black i=ink w=white c=cream p=pink P=hotpink e=peach o=orange y=yellow l=lime
m=mint t=teal s=sky b=blue v=lavender u=purple n=brown h=choco g=gray d=darkgray r=red  .=clear
Round critters (enemies, blocks, food) are drawn procedurally in cute.py.
"""

# Momo, the mochi bunny (hero of Soap Hop) - facing right
_MOMO = [
    "................",
    "...kk......kk...",
    "..kwpk....kpwk..",
    "..kwpk....kpwk..",
    "..kwwk....kwwk..",
    "...kwwkkkkwwk...",
    "..kwwwwwwwwwwk..",
    ".kwwwwwwwwwwwwk.",
    ".kwwwwwwkwwwkwk.",
    "kwwwwwwwkwwwkwwk",
    "kwwwwwwpwwkwwpwk",
    "kwwwwwwwwwwwwwwk",
    "kwwwwwwwwwwwwwwk",
    ".kwwwwwwwwwwwwk.",
    "..kkkkkkkkkkkk..",
    "................",
]


def _squash(rows):
    """Lower the ears one pixel and widen the bottom - idle bounce / landing."""
    r = rows[:]
    return ["................"] * 2 + r[1:4] + r[5:12] + [r[11], r[12], r[13], r[14]]


def _feet(rows, a):
    r = rows[:]
    r[14] = "..kwwkkkkkkkkk.." if a else "..kkkkkkkkkwwk.."
    r[15] = "..kkk..........." if a else "...........kkk.."
    return r


def _jump(rows):
    r = rows[:]
    return r[0:1] + ["..kk........kk.."] + r[1:5] + r[6:15] + ["................"]


MOMO_IDLE = [_MOMO, _squash(_MOMO)]
MOMO_WALK = [_feet(_MOMO, True), _feet(_MOMO, False)]
MOMO_JUMP = [_jump(_MOMO)]

# Tama, the teacup kitty (hero of Comet Kitty)
KITTY = [
    "................",
    "..k..........k..",
    ".kok........kok.",
    ".kook......kook.",
    ".kooookkkkooook.",
    "kooooooooooooook",
    "koookkooookkoook",
    "koookwooookwoook",
    "kpoooookkooooopk",
    ".kooooooooooook.",
    "kcccccccccccccck",
    ".kwwwwwwwwwwwwk.",
    ".kppppppppppppk.",
    "..kwwwwwwwwwwk..",
    "...kkkkkkkkkk...",
    ".....kkkkkk.....",
]

HEART = [
    ".kk.kk.",
    "kppkppk",
    "kpppppk",
    ".kpppk.",
    "..kpk..",
    "...k...",
]

STAR = [
    "...k...",
    "..kyk..",
    "kkkyykk",
    ".kyyyk.",
    "..kyk..",
    ".kyky..",
    ".kk.kk.",
]

MOCHI_ICON = [
    "..kkkk..",
    ".kwwwwk.",
    "kwwwwwwk",
    "kwkwwkwk",
    "kpwkkwpk",
    "kwwwwwwk",
    ".kkkkkk.",
]

ART = {
    "momo_idle": MOMO_IDLE,
    "momo_walk": MOMO_WALK,
    "momo_jump": MOMO_JUMP,
    "kitty": [KITTY],
    "heart": [HEART],
    "star": [STAR],
    "mochi_icon": [MOCHI_ICON],
}
