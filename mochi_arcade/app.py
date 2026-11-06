"""MOCHI ARCADE application: window, main loop, scenes, input, audio, profiles."""
import argparse
import os
import sys
import time

import warnings

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
warnings.filterwarnings("ignore", message=".*avx2 capable.*")  # harmless pygame build notice
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "nearest")  # crisp pixels when scaling up

import pygame  # noqa: E402

from mochi_arcade import TITLE, __version__  # noqa: E402
from mochi_arcade.audio import SR, Audio  # noqa: E402
from mochi_arcade.gfx import H, W, col, scanlines  # noqa: E402
from mochi_arcade.profiles import DEFAULT_SETTINGS, Store, data_dir  # noqa: E402

ACTIONS = ("left", "right", "up", "down", "a", "b", "x", "y", "start", "back")
KEYMAP = {
    pygame.K_LEFT: "left", pygame.K_a: "left", pygame.K_RIGHT: "right", pygame.K_d: "right",
    pygame.K_UP: "up", pygame.K_w: "up", pygame.K_DOWN: "down", pygame.K_s: "down",
    pygame.K_z: "a", pygame.K_SPACE: "a", pygame.K_x: "b", pygame.K_LCTRL: "b", pygame.K_RCTRL: "b",
    pygame.K_c: "x", pygame.K_LSHIFT: "x", pygame.K_RSHIFT: "x", pygame.K_v: "y",
    pygame.K_RETURN: "start", pygame.K_KP_ENTER: "start", pygame.K_p: "start",
    pygame.K_ESCAPE: "back", pygame.K_BACKSPACE: "back",
}
PADMAP = {0: "a", 1: "b", 2: "x", 3: "y", 6: "back", 7: "start", 8: "back", 9: "start"}


class Input:
    def __init__(self):
        self.held = set()
        self.pressed = set()
        self.released = set()
        self.raw = set()          # raw key codes pressed this frame
        self.text = ""            # typed characters this frame
        self._key_held = set()
        self._pad_held = set()
        self._rep = {}
        self.pads = {}
        self.script = None        # for automated tests: callable(frame) -> set of held actions

    def begin(self):
        self.pressed.clear()
        self.released.clear()
        self.raw.clear()
        self.text = ""

    def event(self, e):
        if e.type == pygame.KEYDOWN:
            self.raw.add(e.key)
            a = KEYMAP.get(e.key)
            if a:
                self._key_held.add(a)
        elif e.type == pygame.KEYUP:
            a = KEYMAP.get(e.key)
            if a:
                self._key_held.discard(a)
        elif e.type == pygame.TEXTINPUT:
            self.text += e.text
        elif e.type == pygame.JOYDEVICEADDED:
            j = pygame.joystick.Joystick(e.device_index)
            self.pads[j.get_instance_id()] = j
        elif e.type == pygame.JOYDEVICEREMOVED:
            self.pads.pop(e.instance_id, None)

    def end(self, frame):
        pad = set()
        for j in self.pads.values():
            try:
                for b, a in PADMAP.items():
                    if b < j.get_numbuttons() and j.get_button(b):
                        pad.add(a)
                if j.get_numhats():
                    hx, hy = j.get_hat(0)
                    pad |= {"left"} if hx < 0 else {"right"} if hx > 0 else set()
                    pad |= {"up"} if hy > 0 else {"down"} if hy < 0 else set()
                if j.get_numaxes() >= 2:
                    ax, ay = j.get_axis(0), j.get_axis(1)
                    pad |= {"left"} if ax < -0.5 else {"right"} if ax > 0.5 else set()
                    pad |= {"up"} if ay < -0.5 else {"down"} if ay > 0.5 else set()
            except pygame.error:
                pass
        now = self._key_held | pad
        if self.script:
            now = set(self.script(frame))
        self.pressed = now - self.held
        self.released = self.held - now
        self.held = now

    def hit(self, *actions):
        return any(a in self.pressed for a in actions)

    def down(self, *actions):
        return any(a in self.held for a in actions)

    def repeat(self, action, delay=0.28, rate=0.075, dt=1 / 60):
        """True on press, then auto-repeats while held (menus, falling blocks)."""
        if action in self.pressed:
            self._rep[action] = -delay
            return True
        if action in self.held:
            self._rep[action] = self._rep.get(action, 0) + dt
            if self._rep[action] >= rate:
                self._rep[action] -= rate
                return True
        return False


class Scene:
    music = None

    def __init__(self, app):
        self.app = app
        self.t = 0.0

    def enter(self):
        if self.music is not False:
            self.app.audio.music(self.music)

    def update(self, dt):
        pass

    def draw(self, s):
        pass


class App:
    def __init__(self, windowed=False, mute=False, test_frames=0, script=None, profile_dir=None):
        self.test_frames = test_frames
        if profile_dir:
            os.environ["XDG_DATA_HOME"] = profile_dir
        self.store = Store()
        self.profile = self.store.last() if test_frames else None
        st = self.settings()
        if not mute:
            pygame.mixer.pre_init(SR, -16, 1, 512)
        pygame.init()
        pygame.joystick.init()
        self.fullscreen = st["fullscreen"] and not windowed
        self._open_display()
        pygame.display.set_caption(TITLE)
        pygame.mouse.set_visible(False)
        pygame.key.start_text_input()
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.input = Input()
        self.input.script = script
        self.audio = Audio(enabled=not mute)
        self.scenes = []
        self.fade = None
        self.shake_t = 0.0
        self.shake_amt = 0.0
        self.frame = 0
        self.running = True
        self.flash = 0.0
        self.shot_path = None   # tests: save the last frame here before quitting

    def _open_display(self):
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.fullscreen else 0)
        try:
            self.screen = pygame.display.set_mode((W, H), flags, vsync=1)
        except pygame.error:
            self.screen = pygame.display.set_mode((W, H), flags)

    # ---------------------------------------------------------------- settings / profile
    def settings(self):
        return self.profile["settings"] if self.profile else dict(DEFAULT_SETTINGS)

    def apply_settings(self):
        s = self.settings()
        self.audio.set_volumes(s["music"], s["sfx"])
        if bool(s["fullscreen"]) != self.fullscreen and not self.test_frames:
            self.fullscreen = bool(s["fullscreen"])
            try:
                pygame.display.toggle_fullscreen()
            except pygame.error:
                self._open_display()

    def save(self):
        self.store.save()

    # ---------------------------------------------------------------- scenes
    @property
    def scene(self):
        return self.scenes[-1] if self.scenes else None

    def push(self, scene, fade=True):
        def go():
            self.scenes.append(scene)
            scene.enter()
        self._transition(go, fade)

    def replace(self, scene, fade=True):
        def go():
            if self.scenes:
                self.scenes.pop()
            self.scenes.append(scene)
            scene.enter()
        self._transition(go, fade)

    def pop(self, fade=True):
        def go():
            if self.scenes:
                self.scenes.pop()
            if self.scene:
                self.scene.enter()
        self._transition(go, fade)

    def reset_to(self, scene):
        def go():
            self.scenes = [scene]
            scene.enter()
        self._transition(go, True)

    def _transition(self, fn, fade):
        if fade and self.scenes and not self.test_frames:
            self.fade = {"phase": "out", "t": 0.0, "fn": fn}
        else:
            fn()

    def shake(self, amount=3.0, time_=0.25):
        if self.settings().get("shake", True):
            self.shake_amt = max(self.shake_amt, amount)
            self.shake_t = max(self.shake_t, time_)

    # ---------------------------------------------------------------- loop
    def quit(self):
        self.running = False

    def screenshot(self, path=None):
        d = os.path.join(data_dir(), "screenshots")
        os.makedirs(d, exist_ok=True)
        path = path or os.path.join(d, time.strftime("mochi-%Y%m%d-%H%M%S.png"))
        pygame.image.save(pygame.transform.scale(self.canvas, (W * 3, H * 3)), path)
        return path

    def run(self, first_scene):
        self.apply_settings()
        self.audio.build_sfx()
        self.scenes = [first_scene]
        first_scene.enter()
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 1 / 30)
            if self.test_frames:
                dt = 1 / 60
            self.input.begin()
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F12:
                    self.screenshot()
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    if self.profile:
                        self.profile["settings"]["fullscreen"] = not self.fullscreen
                        self.apply_settings()
                        self.save()
                self.input.event(e)
            self.input.end(self.frame)
            if self.fade:
                self.fade["t"] += dt
                if self.fade["phase"] == "out" and self.fade["t"] >= 0.14:
                    self.fade["fn"]()
                    self.fade = {"phase": "in", "t": 0.0, "fn": None}
                elif self.fade["phase"] == "in" and self.fade["t"] >= 0.14:
                    self.fade = None
            scene = self.scene
            if scene is None:
                break
            if not self.fade or self.fade["phase"] == "in":
                scene.t += dt
                scene.update(dt)
            self.draw()
            self.frame += 1
            if self.test_frames and self.frame >= self.test_frames:
                break
        if self.shot_path:
            self.screenshot(self.shot_path)
        pygame.quit()

    def draw(self):
        c = self.canvas
        if self.scene:
            self.scene.draw(c)
        if self.fade:
            a = self.fade["t"] / 0.14
            a = a if self.fade["phase"] == "out" else 1 - a
            ov = pygame.Surface((W, H))
            ov.fill(col("night"))
            ov.set_alpha(int(max(0, min(1, a)) * 255))
            c.blit(ov, (0, 0))
        if self.settings().get("scanlines"):
            scanlines(c)
        ox = oy = 0
        if self.shake_t > 0:
            import random
            self.shake_t -= 1 / 60
            ox = int(random.uniform(-self.shake_amt, self.shake_amt))
            oy = int(random.uniform(-self.shake_amt, self.shake_amt))
            if self.shake_t <= 0:
                self.shake_amt = 0
        self.screen.fill((0, 0, 0))
        self.screen.blit(c, (ox, oy))
        pygame.display.flip()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mochi-arcade", description="MOCHI ARCADE - original retro mini games")
    ap.add_argument("--windowed", action="store_true", help="start in a window")
    ap.add_argument("--mute", action="store_true", help="no audio")
    ap.add_argument("--version", action="version", version=f"{TITLE} {__version__}")
    args = ap.parse_args(argv)
    from mochi_arcade.ui import Boot

    app = App(windowed=args.windowed, mute=args.mute)
    saved = _quiet_tty()
    try:
        app.run(Boot(app))
    finally:
        _restore_tty(saved)
        _flush_tty()
        if os.environ.get("TMUX"):  # repaint a tmux/fbterm console that the game drew over
            os.system("tmux refresh-client >/dev/null 2>&1")


def _quiet_tty():
    """On a text console the keyboard also feeds the terminal: stop it echoing while we play."""
    try:
        import termios
        if sys.stdin.isatty():
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            new = termios.tcgetattr(fd)
            new[3] &= ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(fd, termios.TCSANOW, new)
            return fd, old
    except Exception:
        pass
    return None


def _restore_tty(saved):
    if saved:
        try:
            import termios
            termios.tcsetattr(saved[0], termios.TCSANOW, saved[1])
        except Exception:
            pass


def _flush_tty():
    """When launched from a Linux text console, keys pressed during the game must not reach the shell."""
    try:
        import termios
        if sys.stdin.isatty():
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except Exception:
        pass
