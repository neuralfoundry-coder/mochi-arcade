"""Original chiptune loops for MOCHI ARCADE (composed for this project).

Notation: NOTE:LEN where LEN 1=whole 2=half 4=quarter 8=eighth (add '.' for dotted), R = rest.
Drums: K kick, S snare, H hat.
"""


def _bass(roots, pattern="8"):
    """One bar per root: alternating root / octave."""
    out = []
    for r in roots:
        lo, hi = r + "2", r + "3"
        if pattern == "8":
            out.append(" ".join(f"{n}:8" for n in (lo, hi) * 4))
        else:
            out.append(" ".join(f"{n}:4" for n in (lo, hi) * 2))
    return " ".join(out)


def _drums(bars, pattern):
    return " ".join([pattern] * bars)


ROCK = "K:8 H:8 S:8 H:8 K:8 K:8 S:8 H:8"
BEAT = "K:8 H:8 S:8 H:8 K:8 H:8 S:8 H:8"
SOFT = "K:4 H:4 S:4 H:4"
SPACE = "K:8 H:8 S:8 H:8 K:8 H:8 S:8 S:8"

SONGS = {
    # "Mochi March" - title screen
    "title": {"bpm": 132, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.28, "notes":
            "E5:8 G5:8 C6:8 G5:8 E5:8 G5:8 A5:4  G5:8 E5:8 C5:8 E5:8 A5:4 G5:4 "
            "F5:8 A5:8 C6:8 A5:8 F5:8 A5:8 G5:4  D5:8 G5:8 B5:8 D6:8 C6:4 B5:4 "
            "C6:8 B5:8 A5:8 G5:8 E5:4 G5:4  A5:8 G5:8 E5:8 D5:8 C5:4 E5:4 "
            "F5:8 G5:8 A5:8 C6:8 D6:4 C6:4  B5:8 A5:8 G5:8 D5:8 G5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.7, "notes": _bass(["C", "A", "F", "G"] * 2, "4")},
        {"wave": "drums", "vol": 1, "notes": _drums(8, ROCK)},
    ]},
    # "Suds Hop" - Soap Hop
    "soap": {"bpm": 140, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.26, "notes":
            "C5:8 F5:8 A5:8 F5:8 C6:4 A5:8 F5:8  D5:8 F5:8 A5:8 D6:8 C6:4 A5:4 "
            "A#4:8 D5:8 F5:8 A#5:8 A5:8 F5:8 D5:4  C5:8 E5:8 G5:8 C6:8 A#5:4 G5:4 "
            "A5:8 A5:8 C6:8 A5:8 F5:4 G5:4  F5:8 E5:8 D5:8 E5:8 F5:4 A5:4 "
            "A#5:8 A5:8 G5:8 F5:8 D5:4 F5:4  E5:8 G5:8 C6:8 A#5:8 A5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": _bass(["F", "D", "A#", "C"] * 2)},
        {"wave": "drums", "vol": 1, "notes": _drums(8, BEAT)},
    ]},
    # "Wobble Waltz" - Jelly Stack (calm)
    "jelly": {"bpm": 120, "gain": 0.75, "channels": [
        {"wave": "square", "duty": 0.5, "vol": 0.2, "decay": 0.5, "notes":
            "A4:4 C5:8 E5:8 A5:4 G5:8 E5:8  F5:4 E5:8 C5:8 A4:4 C5:4 "
            "E5:4 G5:8 C6:8 B5:4 G5:4  D5:4 G5:8 B5:8 A5:4 G5:4 "
            "A5:8 G5:8 E5:8 C5:8 D5:4 E5:4  F5:8 A5:8 C6:8 A5:8 G5:4 F5:4 "
            "E5:8 D5:8 C5:8 E5:8 G5:4 C6:4  B5:4 A5:8 G5:8 E5:2"},
        {"wave": "triangle", "vol": 0.4, "gate": 0.8, "notes":
            " ".join(" ".join(f"{a}:4 {b}:4 {a}:4 {b}:4" for a, b in pair) for pair in
                     [[("A2", "E3"), ("F2", "C3"), ("C3", "G3"), ("G2", "D3")]] * 2)},
        {"wave": "drums", "vol": 1, "notes": _drums(8, SOFT)},
    ]},
    # "Saucer Lullaby" - Comet Kitty
    "comet": {"bpm": 150, "channels": [
        {"wave": "square", "duty": 0.125, "vol": 0.24, "notes":
            "E5:8 G5:8 B5:8 E6:8 B5:8 G5:8 E5:8 G5:8  C5:8 E5:8 G5:8 C6:8 G5:8 E5:8 C5:8 E5:8 "
            "D5:8 F#5:8 A5:8 D6:8 A5:8 F#5:8 D5:8 F#5:8  B4:8 D#5:8 F#5:8 B5:8 A5:4 F#5:4 "
            "G5:4 F#5:8 E5:8 B5:4 A5:4  G5:8 E5:8 C5:8 E5:8 G5:4 C6:4 "
            "A5:8 F#5:8 D5:8 F#5:8 A5:4 D6:4  D#6:4 B5:4 F#5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": _bass(["E", "C", "D", "B"] * 2)},
        {"wave": "drums", "vol": 1, "notes": _drums(8, SPACE)},
    ]},
    # "Slurp Shuffle" - Noodle Slurp
    "noodle": {"bpm": 136, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.26, "notes":
            "G5:8 B5:8 D6:8 B5:8 G5:4 R:4  E5:8 G5:8 B5:8 G5:8 E5:4 R:4 "
            "C5:8 E5:8 G5:8 E5:8 C6:8 B5:8 A5:4  D5:8 F#5:8 A5:8 C6:8 B5:4 A5:4 "
            "B5:8 A5:8 G5:8 A5:8 B5:4 D6:4  E6:8 D6:8 B5:8 G5:8 E5:4 G5:4 "
            "A5:8 B5:8 C6:8 E6:8 D6:4 C6:4  A5:8 G5:8 F#5:8 A5:8 G5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": _bass(["G", "E", "C", "D"] * 2)},
        {"wave": "drums", "vol": 1, "notes": _drums(8, BEAT)},
    ]},
    # "Crumb Boogie" - Bounce Bun
    "bounce": {"bpm": 144, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.26, "notes":
            "F#5:8 A5:8 D6:8 A5:8 F#5:8 E5:8 D5:4  D5:8 F#5:8 B5:8 F#5:8 A5:4 F#5:4 "
            "G5:8 B5:8 D6:8 B5:8 A5:8 G5:8 F#5:4  E5:8 A5:8 C#6:8 E6:8 D6:4 C#6:4 "
            "D6:8 C#6:8 B5:8 A5:8 F#5:4 A5:4  B5:8 A5:8 F#5:8 D5:8 B4:4 D5:4 "
            "G5:8 A5:8 B5:8 D6:8 E6:4 D6:4  C#6:8 B5:8 A5:8 E5:8 A5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": _bass(["D", "B", "G", "A"] * 2)},
        {"wave": "drums", "vol": 1, "notes": _drums(8, ROCK)},
    ]},
}

# arcade kit songs (boss fights, FEVER, bonus stages) - shared by every game
SONGS.update({
    # "Big Grumpy" - boss fight (A minor, driving)
    "boss": {"bpm": 160, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.26, "notes":
            "A4:8 C5:8 E5:8 A5:8 G5:8 E5:8 C5:8 E5:8  A4:8 C5:8 E5:8 A5:8 B5:8 A5:8 G5:8 E5:8 "
            "F4:8 A4:8 C5:8 F5:8 E5:8 C5:8 A4:8 C5:8  G4:8 B4:8 D5:8 G5:8 F5:8 D5:8 B4:8 D5:8 "
            "A5:4 G5:8 A5:8 C6:4 B5:8 A5:8  G5:4 E5:8 G5:8 B5:4 A5:8 G5:8 "
            "F5:8 E5:8 D5:8 C5:8 D5:8 E5:8 F5:8 G#5:8  A5:4 E5:8 A5:8 G#5:4 E5:4"},
        {"wave": "triangle", "vol": 0.45, "gate": 0.6, "notes": _bass(["A", "A", "F", "G", "A", "E", "F", "E"])},
        {"wave": "drums", "vol": 1, "notes": _drums(8, ROCK)},
    ]},
    # "Sugar Rush" - FEVER time (C major, fast)
    "fever": {"bpm": 176, "channels": [
        {"wave": "square", "duty": 0.5, "vol": 0.22, "notes":
            "C6:8 G5:8 E5:8 G5:8 C6:8 G5:8 E6:4  D6:8 B5:8 G5:8 B5:8 D6:8 B5:8 F6:4 "
            "E6:8 C6:8 A5:8 C6:8 E6:8 C6:8 A6:4  G6:8 F6:8 E6:8 D6:8 C6:8 B5:8 G5:4 "
            "C6:8 E6:8 G6:8 E6:8 C6:8 E6:8 G6:4  B5:8 D6:8 F6:8 D6:8 B5:8 D6:8 F6:4 "
            "A5:8 C6:8 E6:8 C6:8 F5:8 A5:8 C6:4  G5:8 B5:8 D6:8 F6:8 E6:4 C6:4"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": _bass(["C", "G", "A", "G", "C", "G", "F", "G"])},
        {"wave": "drums", "vol": 1, "notes": _drums(8, "K:8 H:8 S:8 H:8 K:8 K:8 S:8 S:8")},
    ]},
    # "Candy Parade" - bonus stages (F major, bouncy)
    "bonus": {"bpm": 150, "channels": [
        {"wave": "square", "duty": 0.25, "vol": 0.25, "notes":
            "F5:8 A5:8 C6:8 A5:8 F5:8 A5:8 C6:4  G5:8 A#5:8 D6:8 A#5:8 G5:8 A#5:8 D6:4 "
            "A5:8 C6:8 F6:8 C6:8 A5:8 C6:8 E6:4  D6:8 C6:8 A#5:8 A5:8 G5:4 C6:4 "
            "F5:8 A5:8 C6:8 F6:8 E6:8 C6:8 A5:4  A#5:8 D6:8 F6:8 D6:8 C6:8 A#5:8 G5:4 "
            "A5:8 F5:8 C6:8 A5:8 D6:8 A#5:8 G5:4  C6:8 A#5:8 A5:8 G5:8 F5:2"},
        {"wave": "triangle", "vol": 0.42, "gate": 0.6, "notes": _bass(["F", "G", "F", "C", "F", "A#", "F", "C"])},
        {"wave": "drums", "vol": 1, "notes": _drums(8, BEAT)},
    ]},
})
