"""Player profiles with settings, high scores and per-game progress (JSON in the XDG data dir)."""
import json
import os
import time

DEFAULT_SETTINGS = {"music": 6, "sfx": 8, "fullscreen": True, "scanlines": False, "shake": True}
AVATARS = ["white", "pink", "peach", "mint", "sky", "lavender", "yellow", "lime"]
MAX_PROFILES = 8
MAX_NAME = 8


def data_dir():
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    d = os.path.join(base, "mochi-arcade")
    os.makedirs(d, exist_ok=True)
    return d


class Store:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "profiles.json")
        self.data = {"version": 1, "last": None, "profiles": []}
        self.load()

    # ---------------------------------------------------------------- persistence
    def load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            if isinstance(d, dict) and isinstance(d.get("profiles"), list):
                self.data = d
        except (OSError, ValueError):
            pass
        for p in self.data["profiles"]:
            p.setdefault("settings", {})
            for k, v in DEFAULT_SETTINGS.items():
                p["settings"].setdefault(k, v)
            p.setdefault("games", {})

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=1)
        os.replace(tmp, self.path)

    # ---------------------------------------------------------------- profiles
    @property
    def profiles(self):
        return self.data["profiles"]

    def get(self, name):
        for p in self.profiles:
            if p["name"] == name:
                return p
        return None

    def last(self):
        return self.get(self.data.get("last")) or (self.profiles[0] if self.profiles else None)

    def create(self, name, avatar="white"):
        name = name.strip().upper()[:MAX_NAME]
        if not name or self.get(name) or len(self.profiles) >= MAX_PROFILES:
            return None
        p = {"name": name, "avatar": avatar, "created": int(time.time()),
             "settings": dict(DEFAULT_SETTINGS), "games": {}}
        self.profiles.append(p)
        self.data["last"] = name
        self.save()
        return p

    def delete(self, name):
        self.data["profiles"] = [p for p in self.profiles if p["name"] != name]
        if self.data.get("last") == name:
            self.data["last"] = None
        self.save()

    def select(self, p):
        self.data["last"] = p["name"]
        self.save()

    # ---------------------------------------------------------------- games
    @staticmethod
    def game(p, gid):
        g = p["games"].setdefault(gid, {})
        g.setdefault("best", 0)
        g.setdefault("plays", 0)
        g.setdefault("top", [])
        g.setdefault("options", {})
        g.setdefault("progress", {})
        return g

    def record(self, p, gid, score, detail=""):
        """Store a finished game. Returns (is_new_best, rank or None)."""
        g = self.game(p, gid)
        g["plays"] += 1
        new_best = score > g["best"]
        g["best"] = max(g["best"], score)
        entry = {"score": score, "when": int(time.time()), "detail": detail}
        g["top"].append(entry)
        g["top"].sort(key=lambda e: -e["score"])
        g["top"] = g["top"][:10]
        rank = g["top"].index(entry) + 1 if entry in g["top"] else None
        self.save()
        return new_best, rank
