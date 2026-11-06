"""Game registry. Every game is an original design for MOCHI ARCADE."""
import importlib


class GameInfo:
    def __init__(self, gid, title, tagline, bg, howto, options, module, cls):
        self.id, self.title, self.tagline, self.bg = gid, title, tagline, bg
        self.howto, self.options, self.module, self.cls = howto, options, module, cls
        self._mod = None

    def _m(self):
        if self._mod is None:
            self._mod = importlib.import_module(f"mochi_arcade.games.{self.module}")
        return self._mod

    def load(self):
        return getattr(self._m(), self.cls)

    def preview(self, surf, t):
        self._m().preview(surf, t)


DIFF = [("easy", "EASY"), ("normal", "NORMAL"), ("hard", "HARD")]

GAMES = [
    GameInfo("soap_hop", "SOAP HOP", "TRAP THE GRUMPS IN BUBBLES!", "deep",
             ["LEFT/RIGHT  MOVE", "Z / SPACE   JUMP (HOLD: BOUNCE ON BUBBLES)", "X / CTRL    BLOW A BUBBLE",
              "", "BLOW BUBBLES AT DUST GRUMPS TO TRAP THEM,", "THEN TOUCH THE BUBBLE TO POP THEM INTO",
              "SNACKS. POP SEVERAL AT ONCE FOR CHAINS!", "SPELL M-O-C-H-I WITH LETTER BUBBLES.",
              "200 STAGES: BOSS EVERY 10TH, BONUS ON X5.", "ENTER / ESC  PAUSE"],
             [("difficulty", "DIFFICULTY", DIFF, "normal"),
              ("start", "START STAGE", "checkpoints", 1)],
             "soap_hop", "SoapHop"),
    GameInfo("jelly_stack", "JELLY STACK", "STACK THE WOBBLY JELLIES!", "ink",
             ["LEFT/RIGHT  MOVE        DOWN   SOFT DROP", "UP / X      ROTATE RIGHT", "Z           ROTATE LEFT",
              "SPACE       HARD DROP", "C / SHIFT   HOLD", "", "FILL A ROW TO MAKE THE JELLIES POP.",
              "CLEAR 4 ROWS AT ONCE FOR A JELLY PARTY!", "", "ENTER / ESC  PAUSE"],
             [("mode", "MODE", [("marathon", "MARATHON"), ("sprint", "SPRINT 40"), ("endless", "ENDLESS")], "marathon"),
              ("level", "START LEVEL", [(1, "1"), (5, "5"), (10, "10"), (15, "15")], 1),
              ("ghost", "GHOST PIECE", [(True, "ON"), (False, "OFF")], True)],
             "jelly_stack", "JellyStack"),
    GameInfo("comet_kitty", "COMET KITTY", "DEFEND THE MILKY WAY!", "night",
             ["LEFT/RIGHT  FLY", "Z / SPACE   SHOOT STARS", "", "SPACE JELLIES GLIDE IN AND SWOOP DOWN.",
              "BOSS PUFFS NEED TWO HITS AND SOMETIMES", "DROP A FRIEND STAR - CATCH IT FOR A", "WINGMAN!",
              "EVERY 4TH WAVE IS A BONUS PARADE.", "", "ENTER / ESC  PAUSE"],
             [("difficulty", "DIFFICULTY", DIFF, "normal"),
              ("wave", "START WAVE", [(1, "1"), (3, "3"), (5, "5")], 1)],
             "comet_kitty", "CometKitty"),
    GameInfo("noodle_slurp", "NOODLE SLURP", "SLURP UP THE DUMPLINGS!", "brown",
             ["ARROWS      STEER THE NOODLE", "", "EAT DUMPLINGS TO GROW LONGER.", "GOLDEN DUMPLINGS ARE WORTH A LOT",
              "BUT DO NOT STAY LONG.", "DON'T BUMP INTO WALLS OR YOURSELF!", "", "ENTER / ESC  PAUSE"],
             [("mode", "MODE", [("classic", "CLASSIC"), ("wrap", "WRAP AROUND"), ("maze", "MAZES")], "classic"),
              ("speed", "SPEED", [("slow", "SLOW"), ("normal", "NORMAL"), ("fast", "FAST")], "normal")],
             "noodle_slurp", "NoodleSlurp"),
    GameInfo("bounce_bun", "BOUNCE BUN", "BREAK ALL THE SNACKS!", "choco",
             ["LEFT/RIGHT  MOVE THE BUN", "Z / SPACE   LAUNCH THE GUMBALL", "", "BOUNCE THE GUMBALL INTO THE SNACKS.",
              "CHOCOLATE NEEDS TWO HITS, TINS NEVER BREAK.", "CATCH CAPSULES: W WIDE  M MULTI  S SLOW",
              "G GLUE  + EXTRA LIFE", "", "ENTER / ESC  PAUSE"],
             [("difficulty", "DIFFICULTY", DIFF, "normal"),
              ("level", "START LEVEL", [(1, "1"), (3, "3"), (5, "5")], 1)],
             "bounce_bun", "BounceBun"),
]
