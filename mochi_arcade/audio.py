"""Tiny chiptune synthesizer: square / triangle / noise voices, sound effects and looping songs.

All music here is composed for MOCHI ARCADE. Songs are rendered once and cached as WAV files.
"""
import array
import hashlib
import math
import os
import random
import wave

import pygame

from mochi_arcade import music

SR = 22050
_NOTE = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}


def freq(note):
    """'A4' -> 440.0 ; 'C#5' -> ..."""
    name, octave = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((_NOTE[name] + (octave - 4) * 12) / 12)


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    d = os.path.join(base, "mochi-arcade")
    os.makedirs(d, exist_ok=True)
    return d


# ----------------------------------------------------------------------------- voices
def voice(wave_kind, f0, n, vol, f1=None, duty=0.25, attack=0.004, release=0.03, decay=0.35, vibrato=0.0):
    """Return n float samples of one note. f1 = end frequency for slides."""
    out = [0.0] * n
    if n <= 0:
        return out
    att = max(1, int(attack * SR))
    rel = max(1, min(n, int(release * SR)))
    ph = 0.0
    rnd = random.random
    nv = 0.0
    hold = 0
    for i in range(n):
        t = i / n
        f = f0 if f1 is None else f0 + (f1 - f0) * t
        if vibrato:
            f *= 1 + vibrato * math.sin(i * 0.0025)
        ph += f / SR
        if ph >= 1.0:
            ph -= int(ph)
        if wave_kind == "square":
            s = 1.0 if ph < duty else -1.0
        elif wave_kind == "triangle":
            s = 4.0 * ph - 1.0 if ph < 0.5 else 3.0 - 4.0 * ph
        elif wave_kind == "sine":
            s = math.sin(ph * 6.283185307)
        else:  # noise, re-sampled at roughly f0 Hz for a pitched hiss
            if hold <= 0:
                nv = rnd() * 2 - 1
                hold = max(1, int(SR / max(f, 1)))
            hold -= 1
            s = nv
        env = 1.0 - decay * t
        if i < att:
            env *= i / att
        if i >= n - rel:
            env *= (n - i) / rel
        out[i] = s * vol * env
    return out


def to_pcm(samples, gain=1.0):
    a = array.array("h", [0] * len(samples))
    for i, v in enumerate(samples):
        v *= gain
        a[i] = 32767 if v > 1 else -32767 if v < -1 else int(v * 32767)
    return a


def concat(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


# ----------------------------------------------------------------------------- sound effects
def _arp(notes, d, wave_kind="square", vol=0.35, duty=0.25):
    return concat(*[voice(wave_kind, freq(n), int(d * SR), vol, duty=duty, release=0.01, decay=0.2) for n in notes])


SFX = {
    "move": lambda: voice("square", 880, int(0.03 * SR), 0.25, duty=0.125, decay=0.5),
    "select": lambda: _arp(["E5", "B5"], 0.05),
    "back": lambda: _arp(["B5", "E5"], 0.05),
    "type": lambda: voice("square", 1200, int(0.02 * SR), 0.2, duty=0.5),
    "jump": lambda: voice("square", 280, int(0.13 * SR), 0.3, f1=720, duty=0.25),
    "bubble": lambda: voice("sine", 520, int(0.16 * SR), 0.45, f1=980, vibrato=0.05),
    "trap": lambda: voice("sine", 980, int(0.22 * SR), 0.45, f1=380),
    "pop": lambda: concat(voice("noise", 4000, int(0.04 * SR), 0.35), voice("square", 1300, int(0.05 * SR), 0.3, duty=0.5)),
    "fruit": lambda: _arp(["B5", "E6"], 0.07, vol=0.3),
    "hurt": lambda: voice("square", 620, int(0.32 * SR), 0.35, f1=140, duty=0.5),
    "die": lambda: _arp(["G5", "E5", "C5", "G4", "C4"], 0.09, vol=0.32, duty=0.5),
    "shoot": lambda: voice("square", 1500, int(0.08 * SR), 0.22, f1=600, duty=0.125),
    "explode": lambda: voice("noise", 2200, int(0.3 * SR), 0.45, f1=300, decay=0.9),
    "boom": lambda: voice("noise", 900, int(0.6 * SR), 0.55, f1=80, decay=0.95),
    "rotate": lambda: voice("square", 520, int(0.03 * SR), 0.2, duty=0.5),
    "lock": lambda: voice("triangle", 170, int(0.06 * SR), 0.5),
    "line": lambda: _arp(["C6", "E6", "G6"], 0.045, vol=0.3),
    "quad": lambda: _arp(["C5", "E5", "G5", "C6", "E6", "G6", "C7"], 0.05, vol=0.3),
    "levelup": lambda: _arp(["G5", "C6", "E6", "G6"], 0.07, vol=0.3, duty=0.5),
    "eat": lambda: voice("square", 700, int(0.05 * SR), 0.3, f1=1100, duty=0.25),
    "bonus": lambda: _arp(["E6", "G6", "B6", "E7"], 0.04, vol=0.25),
    "paddle": lambda: voice("square", 440, int(0.04 * SR), 0.3, duty=0.5),
    "brick": lambda: voice("square", 880, int(0.04 * SR), 0.28, duty=0.25),
    "tin": lambda: voice("triangle", 1700, int(0.04 * SR), 0.4),
    "powerup": lambda: voice("square", 300, int(0.25 * SR), 0.3, f1=1200, duty=0.5, vibrato=0.08),
    "extra": lambda: _arp(["C6", "E6", "G6", "C7", "G6", "C7"], 0.06, vol=0.3, duty=0.5),
    "hold": lambda: voice("triangle", 660, int(0.05 * SR), 0.4, f1=880),
    "gameover": lambda: _arp(["C5", "B4", "A#4", "A4"], 0.22, vol=0.3, duty=0.5),
    "win": lambda: _arp(["C5", "E5", "G5", "C6", "G5", "C6", "E6"], 0.08, vol=0.3, duty=0.5),
    # arcade kit (mochi_arcade/arcade.py)
    "combo": lambda: _arp(["C6", "G6"], 0.04, vol=0.28),
    "fever": lambda: _arp(["C5", "E5", "G5", "C6", "E6", "G6", "C7", "E7"], 0.035, vol=0.3, duty=0.5),
    "jackpot": lambda: _arp(["G5", "C6", "E6", "G6", "C7", "E7", "G7", "C7", "E7", "G7"], 0.05, vol=0.3, duty=0.5),
    "card": lambda: voice("square", 660, int(0.08 * SR), 0.3, f1=1320, duty=0.5),
    "coin": lambda: concat(voice("square", 988, int(0.05 * SR), 0.25, duty=0.5), voice("square", 1319, int(0.12 * SR), 0.25, duty=0.5)),
    "warning": lambda: concat(*[voice("square", 440, int(0.14 * SR), 0.3, f1=880, duty=0.5) for _ in range(3)]),
    "bossdown": lambda: voice("noise", 1800, int(1.0 * SR), 0.55, f1=60, decay=0.97),
    "stage": lambda: _arp(["C5", "G5", "C6"], 0.07, vol=0.3, duty=0.5),
}


# ----------------------------------------------------------------------------- songs
def _parse(tokens):
    for tok in tokens.split():
        name, den = tok.split(":")
        dotted = den.endswith(".")
        d = 4.0 / float(den.rstrip("."))
        yield name, d * (1.5 if dotted else 1.0)


def _drum(kind, n):
    if kind == "K":
        return voice("sine", 160, n, 0.9, f1=45, decay=0.9, release=0.02)
    if kind == "S":
        return [a + b for a, b in zip(voice("noise", 6000, n, 0.35, decay=0.95), voice("triangle", 210, n, 0.25, decay=1.0))]
    return voice("noise", 9000, min(n, int(0.03 * SR)), 0.18, decay=1.0) + [0.0] * max(0, n - int(0.03 * SR))


def render_song(song):
    beat = 60.0 / song["bpm"]
    tracks = []
    for ch in song["channels"]:
        out = []
        gate = ch.get("gate", 0.85)
        for name, beats in _parse(ch["notes"]):
            n = int(beats * beat * SR)
            if name == "R":
                out.extend([0.0] * n)
            elif ch["wave"] == "drums":
                d = _drum(name, min(n, int(0.18 * SR)))
                out.extend(d + [0.0] * (n - len(d)))
            else:
                on = int(n * gate)
                out.extend(voice(ch["wave"], freq(name), on, ch["vol"], duty=ch.get("duty", 0.25),
                                 decay=ch.get("decay", 0.35), vibrato=ch.get("vibrato", 0.0)))
                out.extend([0.0] * (n - on))
        tracks.append(out)
    n = max(len(t) for t in tracks)
    mix = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            mix[i] += v
    return to_pcm(mix, song.get("gain", 0.8))


def song_path(name):
    s = music.SONGS[name]
    h = hashlib.sha1(repr(s).encode()).hexdigest()[:10]
    return os.path.join(cache_dir(), f"{name}-{h}.wav")


def ensure_song(name):
    path = song_path(name)
    if not os.path.exists(path):
        pcm = render_song(music.SONGS[name])
        tmp = path + ".tmp"
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        os.replace(tmp, path)
    return path


# ----------------------------------------------------------------------------- manager
class Audio:
    def __init__(self, enabled=True):
        self.ok = False
        self.sounds = {}
        self.sfx_vol = 0.8
        self.music_vol = 0.6
        self.current = None
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SR, -16, 1, 512)
            self.fmt = pygame.mixer.get_init()
            pygame.mixer.set_num_channels(16)
            self.ok = self.fmt is not None
        except (pygame.error, NotImplementedError, AttributeError):   # no audio device, or pygame without mixer
            self.ok = False

    def pending_songs(self):
        return [n for n in music.SONGS if not os.path.exists(song_path(n))]

    def build_sfx(self):
        if not self.ok:
            return
        freq_, _, chans = self.fmt
        for name, fn in SFX.items():
            pcm = to_pcm(fn())
            if chans == 2:
                st = array.array("h", [0] * (len(pcm) * 2))
                st[0::2] = pcm
                st[1::2] = pcm
                pcm = st
            try:
                self.sounds[name] = pygame.mixer.Sound(buffer=pcm.tobytes())
            except pygame.error:
                pass

    def set_volumes(self, music_level, sfx_level):
        self.music_vol = max(0, min(10, music_level)) / 10
        self.sfx_vol = max(0, min(10, sfx_level)) / 10
        if self.ok:
            pygame.mixer.music.set_volume(self.music_vol * 0.7)

    def play(self, name):
        if self.ok and self.sfx_vol > 0 and name in self.sounds:
            s = self.sounds[name]
            s.set_volume(self.sfx_vol)
            s.play()

    def music(self, name, loop=True):
        if not self.ok or name == self.current:
            return
        self.current = name
        if name is None:
            pygame.mixer.music.fadeout(300)
            return
        try:
            pygame.mixer.music.load(ensure_song(name))
            pygame.mixer.music.set_volume(self.music_vol * 0.7)
            pygame.mixer.music.play(-1 if loop else 0)
        except pygame.error:
            pass

    def stop_music(self):
        self.music(None)
