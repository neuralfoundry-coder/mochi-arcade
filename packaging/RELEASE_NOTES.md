**MOCHI ARCADE 0.3.0 — the CAT CORNER**

Eleven new cat-hero arcade games, each a full 200-stage campaign with bosses, bonus stages and upgrade cards:

- **Whisker Maze** (maze raid) · **Tower Tabby** (climbing) · **Alley Hop** (lane crossing) · **Yarn Weaver** (area capture)
- **Cloud Pounce** (vertical jumper) · **Kitten Pile** (falling-pairs puzzle) · **Hairball Havoc** (arena shooter)
- **Rooftop Run** (runner) · **Window Watch** (pointing defense) · **Paw Pinball** (pinball)
- **Meow Deck** — a deck-building card battler with 68 different cats, each card with its own generated portrait

Also:
- macOS / venv installs use **pygame-ce** (Python 3.14's pygame wheels have no sound); without a mixer the game now
  runs muted instead of crashing.
- Fix: shapes sliding in from the left/top edge no longer smear across the screen on pygame 2.5 (Ubuntu 24.04).
- iPhone/iPad: direct taps for pointing games and cards, analog thumb pad, the game carousel shows 16 games.

```sh
curl -fsSL https://raw.githubusercontent.com/neuralfoundry-coder/mochi-arcade/main/install.sh | sh
mochi-arcade
```
