"""Game registry. Every game is an original design for MOCHI ARCADE."""
import importlib


class GameInfo:
    def __init__(self, gid, title, tagline, bg, howto, options, module, cls):
        self.id, self.title, self.tagline, self.bg = gid, title, tagline, bg
        self._howto, self._options, self.module, self.cls = howto, options, module, cls
        self._mod = None

    # howto / options may live in the game module itself (HOWTO, OPTIONS) so a game's files are self-contained
    @property
    def howto(self):
        return self._howto if self._howto is not None else getattr(self._m(), "HOWTO", [])

    @property
    def options(self):
        return self._options if self._options is not None else getattr(self._m(), "OPTIONS", [])

    def _m(self):
        if self._mod is None:
            self._mod = importlib.import_module(f"mochi_arcade.games.{self.module}")
        return self._mod

    @property
    def ready(self):
        return self.id not in HIDDEN

    def load(self):
        return getattr(self._m(), self.cls)

    def preview(self, surf, t):
        self._m().preview(surf, t)


DIFF = [("easy", "EASY"), ("normal", "NORMAL"), ("hard", "HARD")]

# Games still being built: registered (tests run them) but hidden from the carousel until they land.
HIDDEN = {"tower_tabby", "alley_hop", "yarn_weaver", "cloud_pounce", "hairball_havoc", "rooftop_run", "paw_pinball", "meow_deck"}

GAMES = [
    GameInfo("soap_hop", "SOAP HOP", "TRAP THE GRUMPS IN BUBBLES!", "deep",
             ["LEFT/RIGHT  MOVE", "Z / SPACE   JUMP (HOLD: BOUNCE ON BUBBLES)", "X / CTRL    BLOW A BUBBLE",
              "", "BLOW BUBBLES AT DUST GRUMPS TO TRAP THEM,", "THEN TOUCH THE BUBBLE TO POP THEM INTO",
              "SNACKS. POP SEVERAL AT ONCE FOR CHAINS!", "SPELL M-O-C-H-I WITH LETTER BUBBLES.",
              "200 STAGES: BOSS EVERY 10TH, BONUS ON X5.", "ENTER / ESC  PAUSE"],
             [("difficulty", "DIFFICULTY", DIFF, "normal"),
              ("start", "START STAGE", "checkpoints", 1)],
             "soap_hop", "SoapHop"),
    GameInfo("jelly_stack", "JELLY STACK", "POP ROWS, BEAT THE JELLY BOSSES!", "ink",
             ["LEFT/RIGHT  MOVE        DOWN   SOFT DROP", "UP / X  ROTATE RIGHT    Z  ROTATE LEFT",
              "SPACE / V  HARD DROP    C / SHIFT  HOLD", "",
              "FILL A ROW TO POP IT - 4 ROWS: JELLY PARTY!", "200 STAGES: DIG, STAR HUNTS, PUZZLES, SPEED",
              "EVERY 10TH STAGE A JELLY BOSS ATTACKS -", "POP ROWS TO HIT IT, BIG POPS HIT HARDER.",
              "BOSSES + BONUS STAGES GIVE UPGRADES.", "POP A GOLDEN JELLY FOR A JACKPOT!", "", "ENTER / ESC  PAUSE"],
             [("mode", "MODE", [("stages", "STAGES"), ("marathon", "MARATHON"), ("sprint", "SPRINT 40"),
                                ("endless", "ENDLESS")], "stages"),
              ("start", "START STAGE", "checkpoints", 1),
              ("level", "CLASSIC LEVEL", [(1, "1"), (5, "5"), (10, "10"), (15, "15")], 1),
              ("ghost", "GHOST PIECE", [(True, "ON"), (False, "OFF")], True)],
             "jelly_stack", "JellyStack"),
    GameInfo("comet_kitty", "COMET KITTY", "DEFEND THE MILKY WAY!", "night",
             ["ARROWS      FLY (8 WAYS)", "Z / SPACE   SHOOT STARS (HOLD)", "X / CTRL    COMET BURST BOMB", "",
              "200 STAGES! A BONUS PARADE EVERY 5TH,", "A BOSS EVERY 10TH - BEAT IT TO POWER UP.",
              "CATCH CAPSULES, CHAIN THE GOLD MEDALS,", "WIPE OUT SQUADS BEFORE THEY LAND!",
              "KILL STREAKS FILL FEVER: HYPER STARS!", "", "ENTER / ESC  PAUSE"],
             [("difficulty", "DIFFICULTY", DIFF, "normal"),
              ("start", "START STAGE", "checkpoints", 1),
              ("autofire", "AUTO FIRE", [("off", "OFF"), ("on", "ON")], "off")],
             "comet_kitty", "CometKitty"),
    GameInfo("noodle_slurp", "NOODLE SLURP", "SLURP THROUGH 200 KITCHENS!", "brown",
             ["ARROWS      STEER THE NOODLE", "Z / SPACE   DASH (WITH THE DASH UPGRADE)", "",
              "SLURP DUMPLINGS TO GROW - DON'T BUMP!", "200 STAGES: EAT, GRAB CHILI STARS, GROW",
              "OR SURVIVE. A FEAST ON EVERY 5TH STAGE,", "A HUNGRY BOSS ON EVERY 10TH - THEN PICK",
              "A POWER UP. GOLDEN DUMPLINGS = BIG POINTS,", "QUICK SLURPS BUILD COMBOS AND FEVER!",
              "", "ENTER / ESC  PAUSE"],
             [("mode", "MODE", [("campaign", "CAMPAIGN"), ("classic", "CLASSIC"), ("wrap", "WRAP AROUND")],
               "campaign"),
              ("start", "START STAGE", "checkpoints", 1),
              ("speed", "SPEED", [("slow", "SLOW"), ("normal", "NORMAL"), ("fast", "FAST")], "normal")],
             "noodle_slurp", "NoodleSlurp"),
    GameInfo("bounce_bun", "BOUNCE BUN", "200 STAGES OF SNACKS!", "choco",
             ["LEFT/RIGHT  MOVE THE BUN (HOLD = FASTER)", "Z / SPACE   LAUNCH (HOLD: STICKY CATCH)",
              "X / CTRL    SPRINKLE LASER (UPGRADE)", "", "BOUNCE THE GUMBALL INTO THE SNACKS!",
              "20 BAKERIES: A BOSS EVERY 10TH STAGE,", "A BONUS ON EVERY X5, THEN PICK AN UPGRADE.",
              "CAPSULES: W WIDE  M MULTI  S SLOW  G GLUE", "F FIREBALL  L LASER  + LIFE  $ JACKPOT",
              "", "ENTER / ESC  PAUSE"],
             [("difficulty", "DIFFICULTY", DIFF, "normal"),
              ("start", "START STAGE", "checkpoints", 1)],
             "bounce_bun", "BounceBun"),

    # ---- the CAT CORNER: cat-hero arcade games (HOWTO / OPTIONS live in each module)
    GameInfo("whisker_maze", "WHISKER MAZE", "A MIDNIGHT SNACK RAID!", "night", None, None, "whisker_maze", "WhiskerMaze"),
    GameInfo("tower_tabby", "TOWER TABBY", "CLIMB THE GIANT CAT TREE!", "deep", None, None, "tower_tabby", "TowerTabby"),
    GameInfo("alley_hop", "ALLEY HOP", "CROSS THE BUSY ALLEYS!", "ink", None, None, "alley_hop", "AlleyHop"),
    GameInfo("yarn_weaver", "YARN WEAVER", "WEAVE YARN, CLAIM THE RUG!", "deep", None, None, "yarn_weaver", "YarnWeaver"),
    GameInfo("cloud_pounce", "CLOUD POUNCE", "BOUNCE UP TO THE MOON!", "night", None, None, "cloud_pounce", "CloudPounce"),
    GameInfo("kitten_pile", "KITTEN PILE", "MATCH 4 SLEEPY KITTENS!", "ink", None, None, "kitten_pile", "KittenPile"),
    GameInfo("hairball_havoc", "HAIRBALL HAVOC", "STOP THE ROBO-MICE!", "ink", None, None, "hairball_havoc", "HairballHavoc"),
    GameInfo("rooftop_run", "ROOFTOP RUN", "CATCH THE FISH THIEF!", "night", None, None, "rooftop_run", "RooftopRun"),
    GameInfo("window_watch", "WINDOW WATCH", "GUARD THE FISHBOWL!", "deep", None, None, "window_watch", "WindowWatch"),
    GameInfo("paw_pinball", "PAW PINBALL", "FLIP, BUMP AND PURR!", "ink", None, None, "paw_pinball", "PawPinball"),
    GameInfo("meow_deck", "MEOW DECK", "COLLECT CATS, WIN DUELS!", "deep", None, None, "meow_deck", "MeowDeck"),
]


def playable():
    """Indices (into GAMES) of the games shown to players."""
    return [i for i, g in enumerate(GAMES) if g.ready]
