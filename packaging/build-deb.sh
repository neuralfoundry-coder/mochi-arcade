#!/bin/sh
# Build dist/mochi-arcade_<version>_all.deb in a Debian container (works on any host with Docker).
set -eu
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' mochi_arcade/__init__.py)
mkdir -p dist
docker run --rm -v "$PWD":/src -w /src debian:bookworm sh -euc "
  apt-get update -qq >/dev/null && apt-get install -y -qq --no-install-recommends dpkg-dev >/dev/null
  d=\$(mktemp -d)
  mkdir -p \$d/DEBIAN \$d/usr/bin \$d/usr/lib/python3/dist-packages \$d/usr/share/applications \$d/usr/share/doc/mochi-arcade
  cp -r mochi_arcade \$d/usr/lib/python3/dist-packages/
  find \$d -name __pycache__ -prune -exec rm -rf {} +
  printf '#!/bin/sh\nexec python3 -m mochi_arcade \"\$@\"\n' > \$d/usr/bin/mochi-arcade
  chmod 755 \$d/usr/bin/mochi-arcade
  cp data/mochi-arcade.desktop \$d/usr/share/applications/
  install -D -m 644 data/70-mochi-arcade-input.rules \$d/usr/lib/udev/rules.d/70-mochi-arcade-input.rules
  for s in 64 128 256; do install -D -m 644 data/mochi-arcade-\$s.png \$d/usr/share/icons/hicolor/\${s}x\${s}/apps/mochi-arcade.png; done
  cp README.md LICENSE NOTICE.md \$d/usr/share/doc/mochi-arcade/
  cat > \$d/DEBIAN/control <<CTL
Package: mochi-arcade
Version: $VERSION
Section: games
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-pygame (>= 2.1)
Recommends: libegl1, libgl1-mesa-dri
Maintainer: neuralfoundry-coder <233372748+neuralfoundry-coder@users.noreply.github.com>
Homepage: https://github.com/neuralfoundry-coder/mochi-arcade
Description: original retro mini games starring the mochi gang
 A cute retro arcade with a bubble platformer, a falling-block puzzle, a space
 shooter, a snake game and a brick breaker - all original games, art and music.
 Runs on the desktop or straight on a Linux text console (KMS/DRM).
CTL
  # postinst: byte-compile, then apply the console-keyboard udev rule (uaccess) right away
  printf '%s\\n' '#!/bin/sh' 'set -e' \\
    'python3 -m compileall -q /usr/lib/python3/dist-packages/mochi_arcade >/dev/null 2>&1 || true' \\
    'rm -f /etc/udev/rules.d/70-mochi-arcade-input.rules' \\
    'if command -v udevadm >/dev/null 2>&1; then udevadm control --reload-rules || true; udevadm trigger --subsystem-match=input --action=change || true; fi' \\
    > \$d/DEBIAN/postinst
  printf '%s\\n' '#!/bin/sh' 'set -e' \\
    'find /usr/lib/python3/dist-packages/mochi_arcade -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true' \\
    > \$d/DEBIAN/prerm
  printf '%s\\n' '#!/bin/sh' 'set -e' \\
    'if command -v udevadm >/dev/null 2>&1; then udevadm control --reload-rules || true; fi' \\
    > \$d/DEBIAN/postrm
  chmod 755 \$d/DEBIAN/postinst \$d/DEBIAN/prerm \$d/DEBIAN/postrm
  dpkg-deb --root-owner-group --build \$d dist/mochi-arcade_${VERSION}_all.deb >/dev/null
  chown -R $(id -u):$(id -g) dist
"
ls -l "dist/mochi-arcade_${VERSION}_all.deb"
