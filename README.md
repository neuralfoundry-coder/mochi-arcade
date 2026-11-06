# MOCHI ARCADE

**A cute retro arcade starring the mochi gang** — five original mini games with pixel art, chiptune music and save profiles. Runs on Linux desktops, macOS, and even straight on a Linux text console (no X / Wayland needed), so an old laptop turned home server can be a tiny arcade machine.

```sh
curl -fsSL https://raw.githubusercontent.com/neuralfoundry-coder/mochi-arcade/main/install.sh | sh   # install
mochi-arcade                                                                                         # play
```

<p align="center"><img src="docs/arcade.gif" width="640" alt="MOCHI ARCADE front end: title, profiles and the game carousel"></p>

## The games

| | |
|---|---|
| <img src="docs/soap-hop.gif" width="400" alt="Soap Hop gameplay"><br>**Soap Hop** — single-screen platformer. Momo the mochi bunny blows soap bubbles to trap dust grumps, then pops them into snacks. Chain pops for big bonuses, bounce on bubbles, 8 stages. | <img src="docs/jelly-stack.gif" width="400" alt="Jelly Stack gameplay"><br>**Jelly Stack** — falling-block puzzle. Stack wobbly jelly cubes and clear rows. Hold, 3-piece preview, ghost piece, wall kicks, lock delay. Marathon, Sprint 40 and Endless. |
| <img src="docs/comet-kitty.gif" width="400" alt="Comet Kitty gameplay"><br>**Comet Kitty** — fixed-screen shooter. Tama the teacup kitty versus space jellies that glide into formation and swoop down. Boss puffs drop friend stars (wingman!), bonus parade every 4th wave. | <img src="docs/bounce-bun.gif" width="400" alt="Bounce Bun gameplay"><br>**Bounce Bun** — brick breaker. Bounce a gumball off a bun into cookies, candy and chocolate. Wide / multi-ball / slow / glue / extra-life capsules, 8 levels. |
| <img src="docs/noodle-slurp.gif" width="400" alt="Noodle Slurp gameplay"><br>**Noodle Slurp** — snake. A hungry noodle slurps dumplings; golden ones are worth a lot. Classic, wrap-around and maze modes. | <img src="docs/title.png" width="400" alt="Title screen"><br>**…and more to come.** Every game, character, sprite, font glyph, song and sound effect is original. |

<sub>Clips were recorded on **Ubuntu 24.04 on a 2015 MacBook Pro**, straight from the game's frame buffer (`packaging/record_gifs.py`, played by simple autoplay bots).</sub>

**Arcade front end:** title → choose / create a **profile** → main menu → pick a game → game options (difficulty, start stage, mode …) → play. Each profile keeps its own settings, high-score tables and last-used options.

## Install & play

```sh
curl -fsSL https://raw.githubusercontent.com/neuralfoundry-coder/mochi-arcade/main/install.sh | sh
mochi-arcade
```

That's it — the first line installs, the second starts the arcade.

| Command | |
|---|---|
| `mochi-arcade` | start (full screen) |
| `mochi-arcade --windowed` | start in a window (desktop) |
| `mochi-arcade --mute` | no sound |
| `sudo mochi-arcade --setup-input` | one-time fix for a text console where the game plays music but ignores keys (the `.deb` already does this) |
| `mochi-arcade --version` | show the version |

What the installer does:

- **Debian / Ubuntu** — installs the `.deb` from the latest release with `apt`, which pulls in `python3-pygame`.
- **Other Linux and macOS** — installs into `~/.local/share/mochi-arcade` with its own Python venv (needs `python3`) and puts the `mochi-arcade` command in `~/.local/bin`.

Or grab the packages from the [releases page](https://github.com/neuralfoundry-coder/mochi-arcade/releases):

```sh
sudo apt install ./mochi-arcade_0.1.2_all.deb && mochi-arcade      # Debian / Ubuntu
pip install mochi-arcade-0.1.2.tar.gz && mochi-arcade              # anywhere with Python 3.8+
```

From source: `pip install pygame && python3 -m mochi_arcade`.

### Playing on a Linux text console

On a machine without a desktop, MOCHI ARCADE draws directly to the screen through KMS/DRM. Start it with `mochi-arcade` from the local console (not over SSH). There the keyboard is read straight from `/dev/input`. The Debian package installs a small udev rule (`70-mochi-arcade-input.rules`) that gives the user at the active console access to keyboards, the same way logind already does for gamepads. With other install methods, run `sudo mochi-arcade --setup-input` once. The package also recommends `libegl1` and `libgl1-mesa-dri`, which are needed for this. If there is no sound, unmute the speakers with `alsamixer`.

### iPhone & iPad

A native Swift port lives in [`ios/`](ios/) — the same five games, art and music with on-screen controls
(D-pad + A/B/X/Y, labels change per game), hardware keyboard and game-controller support, landscape and
handheld-style portrait layouts. The game fills the screen with the controls floating on top; **Options → SCREEN**
switches between FULL (as large as possible, original proportions), STRETCH (edge to edge) and PIXEL (integer scaling,
crispest pixels). It is distributed through TestFlight.

## Controls

| | Keyboard | Gamepad |
|---|---|---|
| Move | arrow keys / WASD | d-pad / stick |
| OK · jump · fire | Z / Space | A |
| Back · bubble · rotate | X / Ctrl | B |
| Hold (Jelly Stack) | C / Shift | X |
| Pause | Enter / P / Esc | Start |
| Fullscreen · screenshot | F11 · F12 | |

Jelly Stack: ↑ / X rotate right, Z rotate left, ↓ soft drop, Space hard drop, C hold.

Profiles and screenshots are saved in `~/.local/share/mochi-arcade/`, generated music in `~/.cache/mochi-arcade/`.

## Originality & licenses

Everything here — game designs, names, characters, pixel art, the pixel font, music and sound effects — was made for this project. All art is drawn from code and all sound is synthesized at run time. The games belong to classic genres, whose mechanics are free to use, but they do not copy any existing game's name, characters, graphics, music or levels. See [NOTICE.md](NOTICE.md).

- Code and assets: **MIT** ([LICENSE](LICENSE))
- Dependencies (not bundled): pygame (LGPL-2.1), SDL 2 (zlib), Python (PSF)

## Support

If MOCHI ARCADE made you smile, you can [sponsor the project](https://github.com/sponsors/neuralfoundry-coder) 💖

---

## 한국어 소개

**모찌 친구들이 나오는 귀여운 레트로 아케이드**입니다. 오리지널 미니게임 5종, 도트 그래픽, 칩튠 음악, 프로필 저장을 지원합니다. 리눅스 데스크톱과 macOS는 물론, X 서버가 없는 **리눅스 콘솔에서도 화면에 바로** 실행됩니다.

| 게임 | 장르 | 내용 |
|---|---|---|
| **Soap Hop** | 플랫포머 | 모찌 토끼 모모가 비눗방울로 먼지 그럼프를 가둬 터뜨림 |
| **Jelly Stack** | 낙하 블록 퍼즐 | 말랑한 젤리 블록 쌓기 (홀드, 넥스트, 고스트, 마라톤·스프린트·엔드리스) |
| **Comet Kitty** | 슈팅 | 찻잔 고양이 타마 vs 우주 해파리 편대, 윙맨 별, 보너스 퍼레이드 |
| **Noodle Slurp** | 스네이크 | 만두 먹는 국수, 금만두, 클래식·랩·미로 모드 |
| **Bounce Bun** | 벽돌깨기 | 빵 패들로 과자 벽돌 깨기, 파워업 캡슐 |

```sh
curl -fsSL https://raw.githubusercontent.com/neuralfoundry-coder/mochi-arcade/main/install.sh | sh   # 설치
mochi-arcade                                                                                         # 실행
```

- 창 모드: `mochi-arcade --windowed`, 소리 끄기: `mochi-arcade --mute`
- 리눅스 콘솔(데스크톱 없음)에서 음악만 나오고 키가 안 먹으면 한 번만: `sudo mochi-arcade --setup-input` (`.deb` 설치 시에는 자동 적용)

위의 플레이 영상은 맥북프로 2015의 우분투 24.04에서 게임을 실행해 녹화한 것입니다.

**iPhone·iPad 버전**은 Swift로 다시 만든 네이티브 앱으로 `ios/` 폴더에 있습니다(터치 패드, 키보드·게임패드 지원, 가로·세로 레이아웃). 게임 화면이 전체 화면을 채우고 버튼은 그 위에 반투명하게 떠 있습니다. **OPTIONS → SCREEN**에서 FULL(비율 유지 최대), STRETCH(화면 꽉 채움), PIXEL(정수배 선명한 픽셀)을 고를 수 있습니다. TestFlight로 배포합니다.

모든 게임 디자인·이름·캐릭터·그래픽·음악은 이 프로젝트를 위해 새로 만든 것이며 MIT 라이선스입니다.
