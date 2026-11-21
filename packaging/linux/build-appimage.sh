#!/usr/bin/env bash
# Build the Linux AppImage: PyInstaller, then appimagetool.
#
#   packaging/linux/build-appimage.sh
#
# Needs: Python with RigSwap and PyInstaller installed (pip install -e ".[build]") and
# internet access the first time (to fetch appimagetool). Output:
# dist/RigSwap-<version>-linux-<arch>.AppImage
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
ARCH="${ARCH:-$(uname -m)}"            # x86_64 or aarch64
TOOL_VERSION="1.9.1"
APP_ID="io.github.qpfixxy.RigSwap"
VERSION="$(python -c 'import rigswap; print(rigswap.__version__)')"
echo "Building RigSwap $VERSION ($ARCH)"

python -m PyInstaller --noconfirm --clean --distpath dist --workpath build/pyinstaller \
    packaging/pyinstaller/rigswap.spec

APPDIR=build/AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/metainfo" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a dist/RigSwap "$APPDIR/usr/lib/rigswap"
install -m 755 packaging/linux/AppRun "$APPDIR/AppRun"
install -m 644 "packaging/linux/$APP_ID.desktop" "$APPDIR/$APP_ID.desktop"
install -m 644 "packaging/linux/$APP_ID.desktop" "$APPDIR/usr/share/applications/$APP_ID.desktop"
install -m 644 "packaging/linux/$APP_ID.metainfo.xml" "$APPDIR/usr/share/metainfo/$APP_ID.appdata.xml"
install -m 644 docs/logo/png/rigswap-256.png "$APPDIR/$APP_ID.png"
install -m 644 docs/logo/png/rigswap-256.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP_ID.png"

TOOL="build/appimagetool-$TOOL_VERSION-$ARCH.AppImage"
if [ ! -x "$TOOL" ]; then
    curl -fsSL -o "$TOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/$TOOL_VERSION/appimagetool-$ARCH.AppImage"
    chmod +x "$TOOL"
fi
OUT="dist/RigSwap-$VERSION-linux-$ARCH.AppImage"
# --appimage-extract-and-run: works without FUSE (CI containers, some distros)
ARCH="$ARCH" "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUT"
echo "Built $ROOT/$OUT"
