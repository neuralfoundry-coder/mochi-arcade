# MOCHI ARCADE for iPhone & iPad

A native Swift port of the desktop games (same games, art, music and levels) with touch controls.

- `MochiArcade/Engine` — a 320×200 software renderer that mirrors the pygame drawing calls, the chiptune
  synthesizer, profiles and the scene engine. `GeneratedData.swift` (font, sprites, songs, levels, game list)
  is generated from the Python sources so both versions stay identical:
  `python ios/tools/gen_data.py` (run from the repository root).
- `MochiArcade/Games`, `MochiArcade/UI` — the five games and the arcade front end.
- `MochiArcade/App` — UIKit host: 60 fps display link, pixel-perfect integer scaling, multi-touch D-pad and
  A/B/X/Y buttons (labels change per game), hardware keyboard (same keys as the desktop) and game controllers.
  Landscape puts the controls beside the screen; portrait (and iPad windows) uses a handheld layout with the
  pad under the screen.

Build: `brew install xcodegen fastlane`, then in `ios/`:

```sh
xcodegen generate && open MochiArcade.xcodeproj           # run in the simulator
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer fastlane ios beta   # TestFlight (needs ASC API key env vars)
```

Launch arguments for testing: `-demo N` (start game N with random input), `-touch` (always show touch controls).
