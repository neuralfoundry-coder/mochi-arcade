#!/bin/sh
# MOCHI ARCADE installer
#
#   curl -fsSL https://raw.githubusercontent.com/neuralfoundry-coder/mochi-arcade/main/install.sh | sh
#
# Debian/Ubuntu: installs the .deb from the latest release with apt (pulls in python3-pygame).
# Other Linux / macOS: installs into ~/.local/share/mochi-arcade with a private Python venv.
# env: MOCHI_VERSION=0.1.0 to pin a release.
set -eu
REPO="neuralfoundry-coder/mochi-arcade"
say()  { printf 'mochi-arcade: %s\n' "$*"; }
fail() { say "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1; }
get()  { if need curl; then curl -fsSL "$1"; elif need wget; then wget -qO- "$1"; else fail "need curl or wget"; fi; }
sha256() { if need sha256sum; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

VER="${MOCHI_VERSION:-}"
[ -n "$VER" ] || VER=$(get "https://api.github.com/repos/$REPO/releases/latest" | sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' | head -1)
[ -n "$VER" ] || fail "could not find the latest release"
BASE="https://github.com/$REPO/releases/download/v$VER"
TMP=$(mktemp -d 2>/dev/null || mktemp -d -t mochi)
trap 'rm -rf "$TMP"' EXIT INT TERM
get "$BASE/SHA256SUMS" > "$TMP/SHA256SUMS"
fetch() {
  get "$BASE/$1" > "$TMP/$1"
  want=$(awk -v f="$1" '$2==f {print $1}' "$TMP/SHA256SUMS")
  [ -n "$want" ] && [ "$want" = "$(sha256 "$TMP/$1")" ] || fail "checksum mismatch for $1"
}
SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"

if [ "$(uname -s)" = Linux ] && need apt-get && need dpkg; then
  DEB="mochi-arcade_${VER}_all.deb"
  say "downloading $DEB"
  fetch "$DEB"
  chmod 644 "$TMP/$DEB"; chmod 755 "$TMP"
  say "installing with apt (may ask for your password)"
  $SUDO apt-get install -y "$TMP/$DEB"
  say "installed! start it with:  mochi-arcade"
else
  need python3 || fail "python3 is required (macOS: xcode-select --install, or brew install python)"
  SRC="mochi-arcade-$VER.tar.gz"
  say "downloading $SRC"
  fetch "$SRC"
  HOME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/mochi-arcade"
  mkdir -p "$HOME_DIR"
  rm -rf "$HOME_DIR/app" && mkdir -p "$HOME_DIR/app"
  tar -xzf "$TMP/$SRC" -C "$HOME_DIR/app" --strip-components=1
  [ -x "$HOME_DIR/venv/bin/python" ] || python3 -m venv "$HOME_DIR/venv"
  say "installing pygame into a private venv"
  "$HOME_DIR/venv/bin/python" -m pip install -q --upgrade pip >/dev/null
  "$HOME_DIR/venv/bin/python" -m pip install -q "pygame>=2.1"
  BIN="$HOME/.local/bin"
  mkdir -p "$BIN"
  printf '#!/bin/sh\ncd "%s" && exec "%s" -m mochi_arcade "$@"\n' "$HOME_DIR/app" "$HOME_DIR/venv/bin/python" > "$BIN/mochi-arcade"
  chmod 755 "$BIN/mochi-arcade"
  say "installed! start it with:  $BIN/mochi-arcade"
  case ":$PATH:" in *":$BIN:"*) ;; *) say "(add $BIN to your PATH to just type mochi-arcade)";; esac
fi
