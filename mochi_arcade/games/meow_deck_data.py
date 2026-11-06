"""MEOW DECK data: the cat cards, foes, bosses, collar charms, themes and the 200-floor campaign.

Everything here is plain data (no pygame) so tests can simulate battles headlessly. The campaign is built
deterministically (random.Random(seed)) and exported to the iOS port through meow_deck.EXPORT.
"""
import random

STAGES = 200

# ----------------------------------------------------------------------------- cards
ROLES = ["swipe", "curl", "purr", "curious", "zoomies", "hiss"]
ROLE_INFO = {   # label, frame colour, icon sprite
    "swipe": ("SWIPE", "red", "md_i_claw"),
    "curl": ("CURL UP", "sky", "md_i_shield"),
    "purr": ("PURR", "pink", "md_i_heart"),
    "curious": ("CURIOUS", "lime", "md_i_quest"),
    "zoomies": ("ZOOMIES", "orange", "md_i_up"),
    "hiss": ("HISS", "lavender", "md_i_down"),
    "gold": ("JACKPOT", "yellow", "md_i_coin"),
    "junk": ("PEST", "gray", "md_i_flea"),
}
RARITY = [("COMMON", "gray"), ("RARE", "sky"), ("EPIC", "hotpink"), ("LEGEND", "yellow"), ("GOLDEN", "yellow")]
PRICE = [45, 75, 115, 170, 999]

# id, name, breed, role, rarity, cost, effects, upgraded effects, eyes, accessory, upgraded cost (None = same)
# effects: [op, n] or [op, n, hits]; see meow_deck_rules.Battle.resolve for every op.
_CATS = [
    # ---- SWIPE: attacks
    ("rio", "ROOKIE RIO", "tabby", "swipe", 0, 1, [["dmg", 6]], [["dmg", 9]], "l", None, None),
    ("sam", "SCRAPPY SAM", "ginger", "swipe", 0, 1, [["dmg", 4, 2]], [["dmg", 6, 2]], "y", "bandana", None),
    ("bruno", "BIG BRUNO", "coon", "swipe", 0, 2, [["dmg", 13]], [["dmg", 18]], "o", None, None),
    ("suki", "SWISHY SUKI", "siamese", "swipe", 0, 1, [["dmg", 4], ["draw", 1]], [["dmg", 7], ["draw", 1]], "s", "bow", None),
    ("fury", "FLUFFY FURY", "longhair", "swipe", 0, 1, [["all", 4]], [["all", 6]], "y", None, None),
    ("stomp", "STUBBY STOMP", "munchkin", "swipe", 0, 0, [["dmg", 3]], [["dmg", 5]], "l", "sweat", None),
    ("pepper", "PEPPER PUNCH", "fold", "swipe", 0, 1, [["dmg", 5], ["daze", 1]], [["dmg", 7], ["daze", 2]], "o", "beret", None),
    ("patch", "PIRATE PATCH", "tuxedo", "swipe", 1, 1, [["dmg", 3, 3]], [["dmg", 4, 3]], "y", "eyepatch", None),
    ("cali", "CAPTAIN CALI", "calico", "swipe", 1, 2, [["all", 8]], [["all", 11]], "l", "captain", None),
    ("nyx", "NINJA NYX", "black", "swipe", 1, 1, [["dmg", 7], ["scare", 1]], [["dmg", 9], ["scare", 2]], "y", "mask", None),
    ("tommy", "TIGER TOMMY", "bengal", "swipe", 1, 2, [["dmg", 6, 3]], [["dmg", 8, 3]], "l", None, None),
    ("rumi", "ROCKET RUMI", "sphynx", "swipe", 1, 1, [["dmg", 7], ["wild", 1]], [["dmg", 10], ["wild", 1]], "s", "goggles", None),
    ("bomber", "BELLY BOMBER", "gray", "swipe", 1, 1, [["slam", 1]], [["block", 4], ["slam", 1]], "o", "tie", None),
    ("wasabi", "WILD WASABI", "ginger", "swipe", 2, 1, [["rnd", 4, 4]], [["rnd", 5, 5]], "l", "leaf", None),
    ("soba", "SAMURAI SOBA", "tortie", "swipe", 2, 2, [["dmg", 20]], [["dmg", 28]], "y", "headband", None),
    ("mocha", "MIDNIGHT MOCHA", "black", "swipe", 2, 2, [["dmg", 10], ["itchy", 5]], [["dmg", 13], ["itchy", 7]], "o", "top", None),
    ("theo", "THUNDER THEO", "coon", "swipe", 3, 3, [["all", 14], ["zoom", 1]], [["all", 18], ["zoom", 2]], "y", "scarf", None),
    # ---- CURL UP: block
    ("sue", "SNUGGLY SUE", "gray", "curl", 0, 1, [["block", 5]], [["block", 8]], "y", "scarf2", None),
    ("nori", "NAPPY NORI", "tuxedo", "curl", 0, 1, [["block", 4], ["purr", 2]], [["block", 6], ["purr", 3]], "y", "nightcap", None),
    ("lola", "LOAF LOLA", "white", "curl", 0, 2, [["block", 12]], [["block", 16]], "s", None, None),
    ("dot", "DONUT DOT", "calico", "curl", 0, 1, [["block", 4], ["draw", 1]], [["block", 6], ["draw", 1]], "o", "flower", None),
    ("bea", "BUNDLE BEA", "munchkin", "curl", 0, 0, [["block", 3]], [["block", 5]], "s", "blush", None),
    ("spud", "SPIKY SPUD", "tortie", "curl", 1, 1, [["spiky", 3]], [["spiky", 3], ["block", 4]], "l", None, None),
    ("pip", "PILLOW PIP", "longhair", "curl", 1, 2, [["block", 10], ["fluff", 1]], [["block", 13], ["fluff", 1]], "y", "bell", None),
    ("clover", "CLOUD CLOVER", "fold", "curl", 1, 1, [["block", 6], ["draw", 1]], [["block", 9], ["draw", 1]], "l", "leaf", None),
    ("bento", "BOXY BENTO", "ginger", "curl", 1, 1, [["block", 7], ["wild", 1]], [["block", 10], ["wild", 1]], "y", None, None),
    ("fig", "FORTRESS FIG", "gray", "curl", 2, 2, [["block", 16], ["spiky", 2]], [["block", 20], ["spiky", 3]], "o", "goggles", None),
    ("iggy", "IRON IGGY", "sphynx", "curl", 2, 1, [["fluff", 2], ["once", 1]], [["fluff", 3], ["once", 1]], "l", "shades", None),
    ("goose", "GRANNY GOOSE", "calico", "curl", 3, 2, [["block", 14], ["purr", 4]], [["block", 18], ["purr", 5]], "s", "glasses", None),
    # ---- PURR: healing
    ("pearl", "PURRING PEARL", "white", "purr", 0, 1, [["heal", 4], ["once", 1]], [["heal", 6], ["once", 1]], "s", "bell", None),
    ("hana", "HONEY HANA", "ginger", "purr", 0, 1, [["purr", 4]], [["purr", 6]], "y", "flower", None),
    ("sage", "SLEEPY SAGE", "gray", "purr", 0, 1, [["heal", 3], ["block", 3]], [["heal", 4], ["block", 5]], "y", "nightcap", None),
    ("kiki", "KNEADING KIKI", "tortie", "purr", 0, 1, [["heal", 2], ["draw", 1]], [["heal", 3], ["draw", 1], ["purr", 1]], "y", "beret", None),
    ("coco", "CUDDLE COCO", "black", "purr", 1, 0, [["heal", 3], ["once", 1]], [["heal", 5], ["once", 1]], "y", "blush", None),
    ("maple", "MAMA MAPLE", "tabby", "purr", 1, 2, [["heal", 8], ["purr", 3], ["once", 1]], [["heal", 10], ["purr", 4], ["once", 1]], "l", "chef", None),
    ("bo", "BISCUIT BO", "munchkin", "purr", 1, 1, [["heal", 3], ["block", 5]], [["heal", 4], ["block", 7]], "l", "bandana", None),
    ("dumpling", "DOC DUMPLING", "siamese", "purr", 2, 1, [["heal", 6], ["cleanse", 1]], [["heal", 9], ["cleanse", 1]], "s", "nurse", None),
    ("milo", "MOTOR MILO", "coon", "purr", 2, 2, [["purr", 7]], [["purr", 10]], "o", None, None),
    ("ami", "ANGEL AMI", "sphynx", "purr", 3, 2, [["heal", 15], ["once", 1]], [["heal", 20], ["once", 1]], "s", "halo", None),
    # ---- CURIOUS: draw and fish
    ("niko", "NOSY NIKO", "ginger", "curious", 0, 1, [["draw", 2]], [["draw", 2]], "l", None, 0),
    ("pika", "PEEKY PIKA", "fold", "curious", 0, 0, [["draw", 1]], [["draw", 2]], "y", None, None),
    ("beans", "BUTTON BEANS", "munchkin", "curious", 0, 1, [["draw", 1], ["block", 3]], [["draw", 2], ["block", 3]], "o", "bow", None),
    ("sumi", "SNIFFY SUMI", "siamese", "curious", 1, 0, [["fish", 1], ["draw", 1], ["once", 1]], [["fish", 2], ["draw", 1], ["once", 1]], "s", None, None),
    ("pixel", "PROF PIXEL", "tuxedo", "curious", 1, 1, [["draw", 3]], [["draw", 4]], "y", "glasses", None),
    ("tama", "TREASURE TAMA", "calico", "curious", 1, 0, [["fish", 2], ["once", 1]], [["fish", 3], ["once", 1]], "y", "monocle", None),
    ("shadow", "SPY SHADOW", "black", "curious", 1, 1, [["draw", 2], ["wild", 1]], [["draw", 3], ["wild", 1]], "l", "shades", None),
    ("ella", "EXPLORER ELLA", "bengal", "curious", 2, 1, [["draw", 3], ["fish", 1]], [["draw", 4], ["fish", 1]], "l", "beanie", None),
    ("lulu", "LIBRARY LULU", "longhair", "curious", 2, 2, [["draw", 5]], [["draw", 5]], "s", "glasses", 1),
    ("sora", "STARGAZER SORA", "gray", "curious", 3, 0, [["fish", 2], ["draw", 2], ["once", 1]], [["fish", 3], ["draw", 3], ["once", 1]], "s", "astro", None),
    # ---- ZOOMIES: buffs
    ("zoe", "ZIPPY ZOE", "ginger", "zoomies", 0, 1, [["zoom", 1], ["draw", 1]], [["zoom", 2], ["draw", 1]], "l", "sweat", None),
    ("daisy", "DASH DAISY", "calico", "zoomies", 0, 0, [["wild", 1], ["draw", 1]], [["wild", 1], ["draw", 2]], "l", "flower", None),
    ("tobi", "TURBO TOBI", "bengal", "zoomies", 1, 1, [["zoom", 2]], [["zoom", 3]], "y", "goggles", None),
    ("duke", "DISCO DUKE", "black", "zoomies", 1, 1, [["zoom", 1], ["fluff", 1]], [["zoom", 2], ["fluff", 1]], "P", "shades", None),
    ("meowz", "DJ MEOWZ", "tortie", "zoomies", 1, 1, [["zoom", 1], ["fever", 20]], [["zoom", 2], ["fever", 25]], "y", "headphones", None),
    ("emi", "ECHO EMI", "siamese", "zoomies", 2, 1, [["echo", 1]], [["echo", 1]], "s", "headphones", 0),
    ("zuzu", "ZOOMY ZUZU", "sphynx", "zoomies", 2, 2, [["zoom", 3], ["fish", 1]], [["zoom", 4], ["fish", 1]], "l", "party", None),
    ("fifi", "FEVER FIFI", "longhair", "zoomies", 2, 1, [["fever", 40]], [["fever", 60]], "P", "bow", None),
    ("kumo", "KING KUMO", "coon", "zoomies", 3, 2, [["zoom", 3], ["fluff", 3]], [["zoom", 4], ["fluff", 4]], "y", "crown", None),
    # ---- HISS: debuffs
    ("gus", "GRUMPY GUS", "gray", "hiss", 0, 1, [["dmg", 3], ["scare", 2]], [["dmg", 5], ["scare", 2]], "o", None, None),
    ("hazel", "HISSY HAZEL", "tortie", "hiss", 0, 1, [["dmg", 3], ["daze", 2]], [["dmg", 5], ["daze", 2]], "l", None, None),
    ("flick", "FLEA FLICK", "tabby", "hiss", 0, 1, [["itchy", 5]], [["itchy", 8]], "y", None, None),
    ("greta", "GROWLY GRETA", "coon", "hiss", 0, 2, [["all", 6], ["scareall", 1]], [["all", 8], ["scareall", 1]], "y", None, None),
    ("boo", "BOO BOO", "black", "hiss", 1, 1, [["scareall", 2]], [["scareall", 3]], "l", None, None),
    ("luna", "LULLABY LUNA", "white", "hiss", 1, 1, [["sleep", 1], ["once", 1]], [["sleep", 1], ["once", 1]], "s", "beret", 0),
    ("stella", "STARE STELLA", "siamese", "hiss", 1, 1, [["dazeall", 2]], [["dazeall", 3]], "s", None, None),
    ("willow", "WITCHY WILLOW", "black", "hiss", 2, 1, [["itchyall", 4]], [["itchyall", 6]], "l", "witch", None),
    ("fang", "COUNT FANG", "sphynx", "hiss", 2, 2, [["daze", 2], ["dmg", 8], ["heal", 3]], [["daze", 2], ["dmg", 11], ["heal", 4]], "r", "cape", None),
    ("cleo", "QUEEN CLEO", "white", "hiss", 3, 1, [["scareall", 2], ["dazeall", 2]], [["scareall", 3], ["dazeall", 3]], "y", "crown", None),
    # ---- specials
    ("goldie", "LUCKY GOLDIE", "gold", "gold", 4, 0, [["gold", 1], ["all", 15], ["fish", 2], ["draw", 2], ["once", 1]],
     [["gold", 1], ["all", 20], ["fish", 2], ["draw", 2], ["once", 1]], "o", "gold", None),
    ("fleas", "FLEAS", "bug", "junk", 0, 1, [["scratch", 1], ["once", 1]], [["scratch", 1], ["once", 1]], "k", None, None),
]

STARTER = ["rio"] * 4 + ["sue"] * 4 + ["pearl", "niko"]
SPECIAL = ("goldie", "fleas")
STARTER_IDS = ("rio", "sue", "pearl", "niko")

# effect text (each phrase <= 16 characters so a big card holds it)
_FX_TEXT = {
    "dmg": lambda n, h: f"DEAL {n}" + (f" X{h}" if h > 1 else ""),
    "all": lambda n, h: f"DEAL {n} TO ALL",
    "rnd": lambda n, h: f"{n} DMG X{h} RANDOM",
    "block": lambda n, h: f"BLOCK {n}",
    "heal": lambda n, h: f"HEAL {n}",
    "draw": lambda n, h: f"DRAW {n}",
    "fish": lambda n, h: f"+{n} FISH",
    "zoom": lambda n, h: f"+{n} POWER",
    "fluff": lambda n, h: f"+{n} FLUFF",
    "purr": lambda n, h: f"PURR {n}",
    "spiky": lambda n, h: f"SPIKY {n}",
    "scare": lambda n, h: f"SCARE {n}",
    "scareall": lambda n, h: f"SCARE ALL {n}",
    "daze": lambda n, h: f"DAZE {n}",
    "dazeall": lambda n, h: f"DAZE ALL {n}",
    "itchy": lambda n, h: f"ITCHY {n}",
    "itchyall": lambda n, h: f"ITCHY ALL {n}",
    "sleep": lambda n, h: "FOE NAPS 1 TURN",
    "slam": lambda n, h: "DEAL YOUR BLOCK",
    "fever": lambda n, h: f"FEVER +{n}%",
    "echo": lambda n, h: "NEXT CAT TWICE",
    "wild": lambda n, h: "CHAINS ANY CAT",
    "once": lambda n, h: "ONCE PER FIGHT",
    "cleanse": lambda n, h: "CURE DEBUFFS",
    "gold": lambda n, h: "JACKPOT!",
    "scratch": lambda n, h: "SCRATCH IT OFF",
}
# effects that need a single target foe
TARGETED = ("dmg", "scare", "daze", "itchy", "sleep", "slam")


def fx_text(fx):
    """Card text lines (<= 16 characters each, at most 3 lines). WILD / ONCE become a last tag line."""
    phrases = [_FX_TEXT[f[0]](f[1], f[2] if len(f) > 2 else 1) for f in fx if f[0] not in ("once", "wild", "gold")]
    tags = [_FX_TEXT[f[0]](f[1], 1) for f in fx if f[0] in ("once", "wild")]
    lines = []
    room = 3 - len(tags)
    for p in phrases:
        if lines and len(phrases) > room and len(lines[-1]) + 1 + len(p) <= 16:
            lines[-1] += " " + p
        else:
            lines.append(p)
    return lines + tags


GLOSSARY = {   # shown under the big card in the deck view (<= 17 characters)
    "zoom": "POWER: +HIT DMG", "fluff": "FLUFF: +BLOCK", "purr": "PURR: HEAL/TURN",
    "spiky": "SPIKY: BITE BACK", "scare": "SCARE: FOE -25%", "scareall": "SCARE: FOE -25%",
    "daze": "DAZE: HIT +50%", "dazeall": "DAZE: HIT +50%", "itchy": "ITCHY: HP DRAIN",
    "itchyall": "ITCHY: HP DRAIN", "once": "ONCE: 1 PER FIGHT", "wild": "WILD: CHAINS ALL",
    "echo": "ECHO: NEXT CAT X2", "fever": "FEVER: COST -1", "sleep": "NAP: FOE SKIPS",
    "slam": "HITS = YOUR BLOCK",
}


def _look(cid, breed, role, eyes, acc):
    from mochi_arcade.games.meow_deck_art import ROLE_FACE
    face = ROLE_FACE.get(role, "open")
    spec = {"breed": breed, "eyes": eyes, "face": face, "acc": acc}
    if cid in ("rio", "niko", "pika", "beans", "daisy"):
        spec["face"] = "wide" if cid != "rio" else "open"
    if cid in ("shadow", "pixel", "lulu"):
        spec["face"] = "open"
    if cid in ("tama",):
        spec["eyes2"] = "s"
    if cid in ("cleo", "willow"):
        spec["face"] = "open"
    return spec


def _build_cats():
    out = []
    for cid, name, breed, role, rar, cost, fx, up, eyes, acc, upcost in _CATS:
        out.append({
            "id": cid, "name": name, "breed": breed, "role": role, "rar": rar, "cost": cost,
            "fx": fx, "up": up, "upcost": cost if upcost is None else upcost,
            "text": fx_text(fx), "uptext": fx_text(up), "spr": "md_c_" + cid,
            "look": _look(cid, breed, role, eyes, acc),
        })
    return out


CATS = _build_cats()
CAT = {c["id"]: c for c in CATS}
POOL = [c["id"] for c in CATS if c["id"] not in SPECIAL and c["id"] not in STARTER_IDS]


def reward_weights(tier):
    """Rarity weights (common, rare, epic, legend) for card rewards on a tier."""
    return [max(30, 70 - 3 * tier), 25 + tier, 5 + tier, tier // 2]


# ----------------------------------------------------------------------------- foes
# move: [kind, n, hits]  kinds: atk blk atkblk buff rally scare soak fleas heal summon steal charge nap shield
FOES = {
    "pug":    {"name": "YAPPY PUG", "spr": "md_f_pug", "hp": 15, "tier": 0,
               "moves": [["atk", 6], ["atk", 3, 2], ["blk", 5]]},
    "thief":  {"name": "CHEESE THIEF", "spr": "md_f_thief", "hp": 11, "tier": 0,
               "moves": [["atk", 4], ["steal", 1], ["atkblk", 3, 4]]},
    "crow":   {"name": "PECKY CROW", "spr": "md_f_crow", "hp": 13, "tier": 1,
               "moves": [["atk", 2, 3], ["atk", 7], ["buff", 1]]},
    "mud":    {"name": "MUD PUPPY", "spr": "md_f_mud", "hp": 18, "tier": 1,
               "moves": [["fleas", 2], ["atk", 7], ["atkblk", 4, 5]]},
    "spray":  {"name": "SPRAY BOTTLE", "spr": "md_f_spray", "hp": 16, "tier": 2,
               "moves": [["soak", 2], ["atk", 8], ["atk", 3, 2]]},
    "squad":  {"name": "SQUEAK SQUAD", "spr": "md_f_squad", "hp": 20, "tier": 2,
               "moves": [["atk", 2, 4], ["blk", 6], ["atk", 3, 3]]},
    "dust":   {"name": "DUSTBOT", "spr": "md_f_dust", "hp": 26, "tier": 3,
               "moves": [["atk", 5], ["charge", 0], ["atk", 16]]},
    "shiny":  {"name": "SHINY CROW", "spr": "md_f_shiny", "hp": 15, "tier": 3,
               "moves": [["steal", 1], ["atk", 4, 2], ["atk", 8]]},
    "cuke":   {"name": "SPOOKY CUKE", "spr": "md_f_cuke", "hp": 22, "tier": 4,
               "moves": [["scare", 2], ["blk", 9], ["atk", 9]]},
    "medic":  {"name": "MOUSE MEDIC", "spr": "md_f_medic", "hp": 14, "tier": 4,
               "moves": [["heal", 8], ["atk", 4], ["shield", 4]]},
    "barker": {"name": "BIG BARKER", "spr": "md_f_barker", "hp": 34, "tier": 5,
               "moves": [["atk", 11], ["blk", 8], ["atk", 6, 2]]},
    "hound":  {"name": "SNIFF HOUND", "spr": "md_f_hound", "hp": 20, "tier": 5,
               "moves": [["rally", 1], ["atk", 6], ["atkblk", 4, 4]]},
    "mop":    {"name": "MOP-O-TRON", "spr": "md_f_mop", "hp": 28, "tier": 6,
               "moves": [["atk", 3, 3], ["soak", 2], ["atk", 10]]},
    "gull":   {"name": "GULL GOON", "spr": "md_f_gull", "hp": 18, "tier": 6,
               "moves": [["atk", 6], ["steal", 1], ["atk", 4, 2]]},
    "turbo":  {"name": "TURBO BOT", "spr": "md_f_turbo", "hp": 30, "tier": 7,
               "moves": [["charge", 0], ["atk", 17], ["blk", 10], ["atk", 6]]},
}
SMALL = ("pug", "thief", "crow", "squad", "shiny", "medic", "gull")

BOSSES = {
    "baron":   {"name": "BARON BULLDOG", "spr": "md_b_baron", "hp": 95,
                "phases": [[["atk", 8], ["atkblk", 5, 8], ["atk", 5, 2]],
                           [["summon", "pug"], ["atk", 14], ["rally", 2], ["atk", 6, 2]]]},
    "cawline": {"name": "QUEEN CAWLINE", "spr": "md_b_cawline", "hp": 85,
                "phases": [[["atk", 4, 3], ["steal", 1], ["blk", 8], ["atk", 9]],
                           [["summon", "crow"], ["atk", 5, 4], ["scare", 2], ["atk", 12]]]},
    "megabot": {"name": "DUSTBOT 9000", "spr": "md_b_megabot", "hp": 105,
                "phases": [[["atk", 7], ["charge", 0], ["atk", 20]],
                           [["atk", 6, 3], ["soak", 2], ["charge", 0], ["atk", 26]]]},
    "cheese":  {"name": "THE BIG CHEESE", "spr": "md_b_cheese", "hp": 72,
                "phases": [[["summon", "thief"], ["atk", 9], ["heal", 6], ["atk", 6]],
                           [["summon", "squad"], ["atk", 6, 2], ["fleas", 2], ["atk", 12]]]},
    "tub":     {"name": "TUB TITAN", "spr": "md_b_tub", "hp": 115,
                "phases": [[["soak", 2], ["atk", 10], ["blk", 12]],
                           [["atk", 4, 4], ["shield", 8], ["atk", 16]]]},
    "cuke":    {"name": "SIR CUCUMBER", "spr": "md_b_cuke", "hp": 125,
                "phases": [[["scare", 2], ["atk", 12], ["blk", 15]],
                           [["atk", 9, 2], ["scare", 3], ["atk", 22]]]},
    "mecha":   {"name": "MECHA MUTT", "spr": "md_b_mecha", "hp": 95,
                "phases": [[["atk", 10], ["summon", "pug"], ["blk", 12], ["atk", 5, 2]],
                           [["charge", 0], ["atk", 21], ["rally", 2], ["atk", 7, 2]],
                           [["atk", 6, 3], ["soak", 2], ["scare", 2], ["fleas", 2], ["atk", 14]]]},
}
BOSS_ORDER = ["baron", "cawline", "megabot", "cheese", "tub", "cuke"]
BOSS_TITLES = ["", " II", " III", " IV"]

# ----------------------------------------------------------------------------- charms (collar passives)
# id, name, desc (| = new line), colour, icon sprite, max level
CHARMS = [
    ("bowl", "BIG BOWL", "+1 FISH|EVERY TURN", "sky", "md_ch_bowl", 2),
    ("nap", "LONG NAP", "+12 MAX HP|AND HEAL 12", "lavender", "md_ch_nap", 5),
    ("claws", "SHARP CLAWS", "START FIGHTS|WITH +1 POWER", "red", "md_ch_claws", 3),
    ("coat", "FLUFFY COAT", "START FIGHTS|WITH +1 FLUFF", "sky", "md_ch_coat", 3),
    ("nose", "CURIOUS NOSE", "DRAW +1 CARD|EVERY TURN", "lime", "md_ch_nose", 2),
    ("bell", "LUCKY BELL", "MORE GOLDEN|KITTENS AND|TREATS", "yellow", "md_ch_bell", 3),
    ("catnip", "CATNIP POUCH", "FEVER FILLS|FASTER", "mint", "md_ch_catnip", 3),
    ("lives", "NINE LIVES", "+1 LIFE|RIGHT NOW", "hotpink", "md_ch_lives", 5),
    ("post", "SCRATCH POST", "BIGGER CHAIN|BONUS CAP", "orange", "md_ch_post", 2),
    ("blanket", "WARM BLANKET", "KEEP 5 BLOCK|PER LEVEL|NEXT TURN", "sky", "md_ch_blanket", 3),
    ("jar", "TREAT JAR", "+50% TREATS", "orange", "md_ch_jar", 2),
    ("motor", "PURR MOTOR", "HEAL 4 AFTER|EVERY FIGHT", "pink", "md_ch_motor", 3),
]

# ----------------------------------------------------------------------------- themes (one per tier)
# name, sky, sky2, ground, ground2, deco kind (0 fence 1 windows 2 trees 3 shelves 4 roofs 5 stars)
THEMES = [
    ("BACK ALLEY", "deep", "ink", "darkgray", "gray", 0),
    ("GARDEN PATCH", "sky", "blue", "teal", "mint", 2),
    ("BIG KITCHEN", "cream", "peach", "brown", "choco", 3),
    ("LIVING ROOM", "lavender", "purple", "choco", "brown", 1),
    ("PUMPKIN PATCH", "ink", "purple", "brown", "orange", 2),
    ("DOG PARK", "sky", "lavender", "lime", "teal", 0),
    ("LAUNDRY DAY", "mint", "teal", "gray", "darkgray", 3),
    ("ROBOT LAB", "night", "ink", "darkgray", "sky", 1),
    ("HARBOR DOCK", "blue", "sky", "brown", "choco", 4),
    ("MOONLIT ROOFS", "night", "deep", "darkgray", "ink", 4),
    ("CHEESE CELLAR", "brown", "choco", "yellow", "orange", 3),
    ("BATH HOUSE", "sky", "white", "teal", "sky", 1),
    ("VEGGIE PATCH", "lime", "teal", "brown", "choco", 2),
    ("PUPPY PALACE", "pink", "hotpink", "purple", "lavender", 1),
    ("STORMY ROOFS", "darkgray", "ink", "gray", "darkgray", 4),
    ("TOY FACTORY", "orange", "peach", "darkgray", "gray", 3),
    ("NEON STREET", "night", "purple", "ink", "hotpink", 0),
    ("SKY GARDEN", "lavender", "sky", "mint", "teal", 2),
    ("STAR BRIDGE", "night", "ink", "blue", "purple", 5),
    ("THE DOG FORT", "red", "hotpink", "darkgray", "black", 4),
]

# curated foe squads: name, foes (minimum tier = latest foe introduction)
SQUADS = [
    ("PUG PATROL", ["pug", "pug"]), ("LONE PUG", ["pug"]), ("CHEESE HEIST", ["thief", "thief"]),
    ("ALLEY TOLL", ["pug", "thief"]), ("MOUSE MOB", ["thief", "thief", "thief"]),
    ("CROW COURT", ["crow", "crow"]), ("MUD SPLASH", ["mud"]), ("MUDDY PALS", ["mud", "thief"]),
    ("PECK PARTY", ["crow", "pug", "crow"]), ("SQUIRT SQUAD", ["spray", "thief"]), ("BATH TIME", ["spray", "spray"]),
    ("SQUEAKY CLEAN", ["squad", "spray"]), ("TINY TERRORS", ["squad", "thief"]), ("CLEANING DAY", ["dust", "spray"]),
    ("ROBO SWEEP", ["dust"]), ("SHINY THINGS", ["shiny", "crow"]), ("CAW CARTEL", ["shiny", "shiny", "crow"]),
    ("CUKE SCARE", ["cuke", "crow"]), ("SALAD BAR", ["cuke", "cuke"]), ("FIELD HOSPITAL", ["medic", "squad"]),
    ("NURSE AND PUG", ["medic", "pug", "pug"]), ("THE BIG DOG", ["barker"]), ("DOG PARK GANG", ["hound", "barker"]),
    ("HUNTING PARTY", ["hound", "pug", "mud"]), ("MOP SQUAD", ["mop", "dust"]), ("SPIN CYCLE", ["mop", "spray"]),
    ("GULL GANG", ["gull", "gull"]), ("HARBOR THIEVES", ["gull", "shiny", "thief"]), ("TURBO RUSH", ["turbo"]),
    ("ROBOT RAVE", ["turbo", "dust"]), ("MAD SCIENCE", ["turbo", "medic", "thief"]), ("PACK ATTACK", ["barker", "hound", "pug"]),
    ("SCARE CROWS", ["cuke", "crow", "shiny"]), ("MOUSE ARMY", ["squad", "medic", "squad"]),
]
MODS = {   # floor modifiers: label, line on the intro card
    "armor": ("ARMORED", "FOES START WITH BLOCK"), "hungry": ("HUNGRY", "FOES HAVE +POWER"),
    "foggy": ("FOGGY", "FOE PLANS ARE HIDDEN"), "lazy": ("LAZY SUNDAY", "FOES NAP ON TURN 1"),
    "treats": ("TREAT RAIN", "DOUBLE TREATS!"), "windy": ("WINDY", "DRAW 1 LESS CARD"),
    "catnip": ("CATNIP AIR", "+1 FISH EVERY TURN"), "swarm": ("SWARM", "AN EXTRA FOE JOINS"),
}
TOFU_LINES = ["LET'S GO, CREW!", "PAWS UP, TEAM!", "NO SNACK LEFT BEHIND!", "STAY FLUFFY!",
              "TAILS HIGH!", "FOR THE FISH!", "WHISKERS READY!", "ONE MORE FLOOR!"]


def squad_tier(foes):
    return max(FOES[f]["tier"] for f in foes)


def hp_mult(n):
    return 1.0 + 0.055 * (n - 1) + 0.00012 * (n - 1) ** 2


def dmg_mult(n):
    return 1.0 + 0.015 * (n - 1)


def build_campaign(seed=7):
    rnd = random.Random(seed)
    camp = []
    seen = set()
    boss_seen = {}
    for n in range(1, STAGES + 1):
        tier = (n - 1) // 10
        pos = (n - 1) % 10 + 1
        st = {"n": n, "tier": tier, "theme": tier, "kind": "normal", "name": "", "foes": [], "mod": "",
              "new": "", "treats": 10 + 2 * tier, "elite": False, "line": TOFU_LINES[(n * 5 + tier) % len(TOFU_LINES)]}
        if pos == 5:
            st["kind"] = "bonus"
            st["name"] = "CAT CAFE"
            st["treats"] = 0
        elif pos == 10:
            st["kind"] = "boss"
            bid = "mecha" if tier in (9, 19) else BOSS_ORDER[(tier - (1 if tier > 9 else 0)) % len(BOSS_ORDER)]
            k = boss_seen.get(bid, 0)
            boss_seen[bid] = k + 1
            b = BOSSES[bid]
            mult = hp_mult(n) * (0.62 if tier == 0 else 0.7 - 0.007 * tier)
            phases = [list(p) for p in b["phases"]]
            if len(phases) < 3 and tier >= 6:
                other = BOSSES[BOSS_ORDER[(BOSS_ORDER.index(bid) + 1) % len(BOSS_ORDER)]]
                phases.append(phases[1] + [m for m in other["phases"][1] if m[0] != "summon"][:2])
            st["name"] = b["name"] + BOSS_TITLES[min(k, 3)]
            st["foes"] = [{"id": bid, "hp": int(b["hp"] * mult), "pow": round(dmg_mult(n), 3), "blk": 0, "zoom": 0,
                           "boss": True, "phases": phases}]
            st["treats"] = 40 + 5 * tier
        else:
            want = {1: 1, 2: 2, 3: 2, 4: 2, 6: 2, 7: 3, 8: 1, 9: 3}[pos]
            if tier == 0 and pos <= 2:
                want = 1 if pos == 1 else 2
            options = [s for s in SQUADS if squad_tier(s[1]) <= tier and len(s[1]) in
                       ((want,) if pos != 8 else (1, 2))]
            fresh = [s for s in options if squad_tier(s[1]) == tier]
            # this tier's new foes debut on its first floors (any squad size)
            debut = [s for s in SQUADS if squad_tier(s[1]) <= tier and len(s[1]) <= 3 and
                     any(FOES[f]["tier"] == tier and f not in seen for f in s[1])]
            if pos <= 3 and debut:
                pick = rnd.choice(debut)
            elif pos == 1 and fresh:
                pick = rnd.choice(fresh)
            elif fresh and rnd.random() < 0.45:
                pick = rnd.choice(fresh)
            else:
                pick = rnd.choice(options)
            name, foes = pick[0], list(pick[1])
            if tier == 0 and pos == 1:
                name, foes = "LONE PUG", ["pug"]
            elite = pos == 8
            mod = ""
            if tier >= 2 and pos != 1 and len(foes) <= 2 and rnd.random() < 0.3 + 0.015 * tier:
                mod = rnd.choice(sorted(MODS))
                if mod == "swarm" and pos == 8:
                    mod = "armor"
            if mod == "swarm":
                foes.append(rnd.choice([f for f in SMALL if FOES[f]["tier"] <= tier]))
            hm = hp_mult(n) * (0.9 + 0.03 * min(3, pos // 2)) * (1.0, 1.0, 0.86, 0.72)[len(foes)]
            out = []
            for f in foes:
                hp = int(FOES[f]["hp"] * hm * (1.7 if elite and len(out) == 0 else 1.0) * rnd.uniform(0.92, 1.08))
                out.append({"id": f, "hp": max(6, hp), "pow": round(dmg_mult(n) * (1.12 if elite else 1.0), 3),
                            "blk": 0, "zoom": 0, "boss": False, "elite": elite and len(out) == 0})
            if mod == "armor":
                for f in out:
                    f["blk"] = 4 + 2 * tier
            if mod == "hungry":
                for f in out:
                    f["zoom"] = 1 + tier // 5
            if elite:
                name = "BOSSY " + FOES[foes[0]]["name"].split(" ")[-1]
            st.update({"name": name, "foes": out, "mod": mod, "elite": elite})
            if elite:
                st["treats"] += 10
            newf = [f for f in foes if f not in seen]
            if newf:
                st["new"] = "NEW FOE: " + FOES[newf[0]]["name"]
        for f in st["foes"]:
            seen.add(f["id"])
        camp.append(st)
    return camp


CAMPAIGN = build_campaign()


def validate(st):
    """Structural checks for one campaign stage; returns a list of problems."""
    errs = []
    n = st["n"]
    if (st["kind"] == "boss") != (n % 10 == 0):
        errs.append("boss position")
    if (st["kind"] == "bonus") != (n % 10 == 5):
        errs.append("bonus position")
    if st["kind"] == "bonus":
        if st["foes"]:
            errs.append("cafe has foes")
        return errs
    if not 1 <= len(st["foes"]) <= 3:
        errs.append(f"{len(st['foes'])} foes")
    for f in st["foes"]:
        if f.get("boss"):
            if f["id"] not in BOSSES:
                errs.append("unknown boss " + f["id"])
            for ph in f["phases"]:
                for m in ph:
                    if m[0] == "summon" and m[1] not in FOES:
                        errs.append("bad summon")
        elif f["id"] not in FOES:
            errs.append("unknown foe " + f["id"])
        if f["hp"] <= 0 or f["pow"] <= 0:
            errs.append("bad stats")
    if st["kind"] == "boss" and (len(st["foes"]) != 1 or not st["foes"][0].get("boss")):
        errs.append("boss stage needs exactly one boss")
    if len(st["name"]) > 22:
        errs.append("name too long")
    return errs
