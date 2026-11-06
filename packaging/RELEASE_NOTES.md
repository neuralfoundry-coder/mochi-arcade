**MOCHI ARCADE 0.1.3**

- Fix: black screen (music only) on a Linux text console. SDL's default desktop-GL renderer presents nothing
  under KMS/DRM on some Intel GPUs (seen on a MacBook Pro 2015, Broadwell + Mesa 25); the game now uses the
  GLES2 renderer there automatically. Desktops (X11/Wayland) are unchanged.

**0.1.2**

- Fix: on a Linux text console (KMS/DRM, no desktop) the game started with music but ignored the keyboard when run as a normal user. The `.deb` now installs a udev rule that lets the user at the active console read keyboards (the same `uaccess` mechanism logind uses for gamepads), and applies it immediately.
- New `sudo mochi-arcade --setup-input` installs the same rule for venv / pip installs.
- If the keyboard still can't be read, the game now says how to fix it instead of running silently.

Five original retro mini games: Soap Hop, Jelly Stack, Comet Kitty, Noodle Slurp, Bounce Bun.

```sh
curl -fsSL https://raw.githubusercontent.com/neuralfoundry-coder/mochi-arcade/main/install.sh | sh
mochi-arcade
```
