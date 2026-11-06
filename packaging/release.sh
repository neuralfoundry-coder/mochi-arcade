#!/bin/sh
# Build release assets into dist/ and (with --publish) create the GitHub release.
set -eu
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' mochi_arcade/__init__.py)
rm -rf dist && mkdir -p dist
packaging/build-deb.sh
git archive --format=tar.gz --prefix="mochi-arcade-$VERSION/" -o "dist/mochi-arcade-$VERSION.tar.gz" HEAD
cp install.sh dist/
(cd dist && shasum -a 256 "mochi-arcade_${VERSION}_all.deb" "mochi-arcade-$VERSION.tar.gz" install.sh > SHA256SUMS && cat SHA256SUMS)
if [ "${1:-}" = --publish ]; then
  gh release create "v$VERSION" dist/* --title "MOCHI ARCADE $VERSION" --notes-file packaging/RELEASE_NOTES.md
fi
