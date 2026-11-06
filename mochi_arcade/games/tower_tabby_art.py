"""TOWER TABBY pixel art (original): Mikan the chubby orange tabby, kittens, KAW the crow, treats and items.

Sprites are registered in sprites.ART (exported to iOS by gen_data). Chars: k black, o orange, n brown,
c cream, w white, p pink, y yellow, s sky, b blue, i ink, d darkgray, g gray, u purple, r red, l lime, v lavender.
"""
from mochi_arcade import sprites

# ----------------------------------------------------------------------------- Mikan (facing right, 16 x 13)
_HEAD = [
    "..........k...k.",
    ".........kok.kok",
    ".k......kooooook",
    "kok.....kononook",
    "kok.kkkkookookok",
    "kokkononopocpcck",
    ".koooooooocccck.",
    ".konononoccccok.",
    ".koonononcccook.",
    ".kooooooocccook.",
    "..koooooooooook.",
]
_BLINK = _HEAD[:4] + ["kok.kkkkookkookk"[:16]] + _HEAD[5:]


def _legs(a, b):
    return [a, b]


MIKAN_IDLE = [_HEAD + _legs("..kwwk....kwwk..", "...kk......kk..."),
              _BLINK + _legs("..kwwk....kwwk..", "...kk......kk...")]
MIKAN_WALK = [_HEAD + _legs(".kwwk......kwwk.", ".kk.........kk.."),
              _HEAD + _legs("..kwwk....kwwk..", "...kk......kk..."),
              _HEAD + _legs("...kwwk..kwwk...", "....kk....kk...."),
              _HEAD + _legs("..kwwk....kwwk..", "...kk......kk...")]
MIKAN_JUMP = [_HEAD[:1] + _HEAD[1:] + _legs(".kwk........kwk.", "kk..........kk..")]
MIKAN_POUNCE = [[
    "................",
    "...........k..k.",
    "..........kok.kok"[:16],
    "k.........kooook",
    "ok...kkkkkkonook",
    ".okkkononookookk",
    "..konononoopcpck",
    "..kooooooocccck.",
    ".kwkooooooccckwk",
    "kwk.kkkkkkkkk.kk",
    ".k..............",
    "................",
    "................",
]]
_STARTLED = _HEAD[:4] + ["kok.kkkkowkowkok", "kokkononopockpck"] + _HEAD[6:] + [
    "kwwk......kwwk..", ".kk........kk..."]
MIKAN_HURT = [list(reversed(_STARTLED))]
# climbing: Mikan seen from behind, paws on the post (14 x 13)
MIKAN_CLIMB = [[
    "...k......k...",
    "..kok....kok..",
    "..kooooooook..",
    ".kooonnnnoook.",
    ".kooooooooook.",
    "kwkooooooookwk",
    "kwkonononookwk",
    ".kkoononoookk.",
    "..kooooooook..",
    "...kooooook...",
    ".kwwk....kwwk.",
    "..kk..ok..kk..",
    "......ok......",
], [
    "...k......k...",
    "..kok....kok..",
    "..kooooooook..",
    ".kooonnnnoook.",
    ".kooooooooook.",
    ".kooooooooook.",
    "kwkonononookwk",
    "kwkoononoookwk",
    "..kooooooook..",
    "...kooooook...",
    "..kwwk..kwwk..",
    "...kk.ok.kk...",
    "......ok......",
]]
# curled up asleep on the goal cushion (16 x 9)
MIKAN_NAP = [[
    "....k...k.......",
    "...kok.kok......",
    "..kooooooookkk..",
    ".konkkonkooonok.",
    "kooooooooooonook",
    "kopooooooooooonk",
    "kccccoooooooooook"[:16],
    ".kccccooooooookk",
    "..kkkkkkkkkkkk..",
]]

# ----------------------------------------------------------------------------- kittens (8 x 7, gray base)
KITTEN = [[
    "k...k...",
    "kgkkgk..",
    "kgggggk.",
    "kgkggkgk",
    "kgpggpgk",
    ".kggggk.",
    ".kk..kk.",
], [
    "k...k...",
    "kgkkgk..",
    "kgggggk.",
    "kgkggkgk",
    "kgpggpgk",
    ".kggggk.",
    "..kkkk..",
]]
KITTEN_COLORS = [{"g": "g"}, {"g": "w"}, {"g": "d", "p": "p"}, {"g": "c"}, {"g": "e"}]

# ----------------------------------------------------------------------------- KAW the crow (16 x 12, faces left)
KAW_FLY = [[
    "........kkk.....",
    "....kkk.kddk....",
    "...kdddkkdddk...",
    "..kdwkddkdddk...",
    "yyydddddkddk....",
    "..krrrrdddkkkk..",
    "...kddddddddkkkk",
    "....kdddddddddk.",
    ".....kkddddkkk..",
    "......y...y.....",
    ".....yy..yy.....",
    "................",
], [
    "................",
    "....kkk.........",
    "...kdddk........",
    "..kdwkddk.......",
    "yyydddddkkkkk...",
    "..krrrrddddddkk.",
    "...kddddddddkkkk",
    "....kdddddddddk.",
    ".....kkddddkkk..",
    "......y...y.....",
    ".....yy..yy.....",
    "................",
], [
    "................",
    "....kkk.........",
    "...kdddk........",
    "..kdwkddk.......",
    "yyydddddk.......",
    "..krrrrddkkkk...",
    "...kddddddddkkkk",
    "....kdkddddddk..",
    ".....kkddddkk...",
    "......ykdddk....",
    ".....yy.kkk.....",
    "................",
]]
KAW_PERCH = [[
    "................",
    "....kkk.........",
    "...kdddk........",
    "..kdwkddk.......",
    "yyydddddk.......",
    "..krrrrddkkk....",
    "...kddddddddkkkk",
    "....kdddddddddk.",
    ".....kkddddkkk..",
    "......y...y.....",
    ".....yy..yy.....",
    "................",
]]
KAW_DAZED = [[
    "................",
    "....kkk.........",
    "...kdddk........",
    "..kwkwddk.......",
    "yyydddddk.......",
    "..krrrrddkkk....",
    "...kddddddddkkkk",
    "....kdddddddddk.",
    ".....kkddddkkk..",
    "......y...y.....",
    ".....yy..yy.....",
    "................",
]]

# ----------------------------------------------------------------------------- treats and items
FISH = [[
    "...kkkk.kk",
    "..kssssksk",
    ".kswksssk.",
    "..kssssksk",
    "...kkkk.kk",
]]
GOLD_FISH = {"s": "y", "w": "w"}
WAND = [[
    ".......pp",
    "......pPp",
    ".....pPp.",
    "....kpp..",
    "...k.....",
    "..k......",
    ".k.......",
    "k........",
]]
BELL = [[
    "..kkk..",
    ".kyyyk.",
    "kyywyyk",
    "kyyyyyk",
    "kkkkkkk",
    "..kyk..",
]]
MILK = [[
    ".kkkk.",
    ".kwwk.",
    "kwwwwk",
    "kwsswk",
    "kwwwwk",
    "kwwwwk",
    ".kkkk.",
]]
NIP = [[
    "...kk..",
    "..klk..",
    ".kllk..",
    "klllk.k",
    "kllkkll",
    ".kk.kk.",
]]
COIN = [[
    ".kkkk.",
    "kyyyyk",
    "kywyyk",
    "kyyyyk",
    "kyyoyk",
    ".kkkk.",
]]

# ----------------------------------------------------------------------------- upgrade icons (9 x 9)
ICONS = {
    "tt_i_speed": [
        ".........",
        "...ooo...",
        "kk.ooooo.",
        "...ooooo.",
        "kkk.ooo..",
        "....o.o..",
        "kk.ww.ww.",
        ".........",
        "........."],
    "tt_i_climb": [
        "...nen...",
        "...ene...",
        "...nen...",
        "...ene...",
        "..wnenw..",
        "...ene...",
        "...nen...",
        "...ene...",
        "..nnnnn.."],
    "tt_i_pounce": [
        ".........",
        "......yy.",
        "....yy.y.",
        "..yy...yy",
        ".y.....y.",
        "o......y.",
        "oo.......",
        "ooo......",
        "........."],
    "tt_i_heart": [
        ".........",
        ".pp...pp.",
        "pPPp.pPPp",
        "pPPPpPPPp",
        ".pPPPPPp.",
        "..pPPPp..",
        "...pPp...",
        "....p....",
        "........."],
    "tt_i_bell": [
        "...rrr...",
        "..kyyyk..",
        ".kyywyyk.",
        ".kyyyyyk.",
        ".kyyyyyk.",
        "kkkkkkkkk",
        "...kyk...",
        "....k....",
        "........."],
    "tt_i_magnet": [
        ".........",
        ".rr...rr.",
        ".rr...rr.",
        ".rr...rr.",
        ".rr...rr.",
        ".rrr.rrr.",
        "..rrrrr..",
        "...rrr...",
        "........."],
    "tt_i_wand": [
        "......ppp",
        ".....pPPp",
        "....pPPp.",
        "....kpp..",
        "...k.....",
        "..k......",
        ".k.......",
        "k........",
        "........."],
    "tt_i_lucky": [
        "....y....",
        "...yyy...",
        "yyyyyyyyy",
        ".yyyyyyy.",
        "..yyyyy..",
        ".yyy.yyy.",
        ".yy...yy.",
        ".........",
        "........."],
    "tt_i_nap": [
        ".........",
        ".sssss...",
        "....s....",
        "...s.....",
        "..s......",
        ".sssss...",
        "......sss",
        ".......s.",
        "......sss"],
    "tt_i_kitty": [
        ".........",
        ".k...k...",
        ".kekkek..",
        ".keeeeek.",
        ".kekeekek",
        ".kepeepek",
        "..keeeek.",
        "..kk..kk.",
        "........."],
}

ART = {
    "tt_mikan_idle": MIKAN_IDLE,
    "tt_mikan_walk": MIKAN_WALK,
    "tt_mikan_jump": MIKAN_JUMP,
    "tt_mikan_pounce": MIKAN_POUNCE,
    "tt_mikan_hurt": MIKAN_HURT,
    "tt_mikan_climb": MIKAN_CLIMB,
    "tt_mikan_nap": MIKAN_NAP,
    "tt_kitten": KITTEN,
    "tt_kaw_fly": KAW_FLY,
    "tt_kaw_perch": KAW_PERCH,
    "tt_kaw_dazed": KAW_DAZED,
    "tt_fish": FISH,
    "tt_wand": WAND,
    "tt_bell": BELL,
    "tt_milk": MILK,
    "tt_nip": NIP,
    "tt_coin": COIN,
}
ART.update({k: [v] for k, v in ICONS.items()})


def _check():
    for name, frames in ART.items():
        for f in frames:
            w = len(f[0])
            assert all(len(r) == w for r in f), (name, [len(r) for r in f])


_check()
sprites.ART.update(ART)
