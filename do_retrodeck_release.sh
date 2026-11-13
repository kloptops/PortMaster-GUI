#!/bin/bash
#
# SPDX-License-Identifier: MIT
#
# retrodeck.portmaster.zip: PortMaster for RetroDECK.
#
#   ./do_retrodeck_release.sh         from dist/PortMaster.zip (./do_release.sh first)
#   ./do_retrodeck_release.sh CHANNEL from the latest alpha/beta/stable PortMaster.zip on GitHub
#
# Writes dist/retrodeck.portmaster.zip.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="${PM_DIST_DIR:-$REPO_DIR/dist}"

BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/pm-retrodeck.XXXXXX")"
trap 'rm -rf "$BUILD_DIR"' EXIT
cd "$BUILD_DIR"

case "${1:-}" in
  alpha|beta|stable)
    curl -fL -o version.json "https://github.com/PortsMaster/PortMaster-GUI/releases/latest/download/version.json"
    curl -fL -o PortMaster.zip "$(jq -r ".$1.url" version.json)"
    PORTMASTER_ZIP="$BUILD_DIR/PortMaster.zip"
    ;;
  *)
    PORTMASTER_ZIP="$DIST_DIR/PortMaster.zip"
    ;;
esac

if [[ ! -f "$PORTMASTER_ZIP" ]]; then
  echo "Missing $PORTMASTER_ZIP, run ./do_release.sh first."
  exit 255
fi

mkdir -p RD_PM/

(
  cd RD_PM/
  unzip -q "$PORTMASTER_ZIP"

  cd PortMaster
  cp retrodeck/control.txt control.txt
  cp retrodeck/PortMaster.txt PortMaster.sh

  # Keep ARM64 input helpers in RetroDECK's private tool directory. PortMaster
  # updates replace the unsuffixed root helpers with their own platform build.
  if readelf -h gptokeyb | grep -q 'Machine:.*AArch64'; then
    mkdir -p retrodeck/aarch64
    cp -p gptokeyb gptokeyb2 retrodeck/aarch64/
  fi

  rm -f tasksetter
  touch tasksetter
)

# Non-stable RetroDECK bundles can be based on the latest stable PortMaster.zip.
# Keep RetroDECK's ARM64-only shared libraries in sync with this checkout as they
# are not part of an older stable base archive.
mkdir -p RD_PM/PortMaster/libs
cp -a "$REPO_DIR/PortMaster/libs.aarch64" RD_PM/PortMaster/libs/

# KDE's Flatpak runtime provides BZip2 as libbz2.so.1, while some AArch64 ports
# (including Frogfall's bundled libzip) request libbz2.so.1.0.
mkdir -p RD_PM/PortMaster/retrodeck/libs.aarch64
ln -sfn /lib/aarch64-linux-gnu/libbz2.so.1 \
  RD_PM/PortMaster/retrodeck/libs.aarch64/libbz2.so.1.0

# Pingus' SDL_mixer needs libmodplug, which PortMaster already bundles with
# the LÖVE runtime. Make it available to all RetroDECK ports as well.
cp -p "$REPO_DIR/PortMaster/runtimes/love_11.5/libs.aarch64/libmodplug.so.1" \
  RD_PM/PortMaster/retrodeck/libs.aarch64/

# Neverball needs the GLVND GLES 1 dispatch library. The Flatpak runtime
# supplies GLdispatch and the Mesa driver; CI stages the ARM64 dispatch library.
GLES1_LIBRARY="$REPO_DIR/PortMaster/retrodeck/aarch64/libGLESv1_CM.so.1.2.0"
if [[ -f "$GLES1_LIBRARY" ]]; then
  cp -p "$GLES1_LIBRARY" RD_PM/PortMaster/retrodeck/libs.aarch64/
  if [[ -f "$REPO_DIR/PortMaster/retrodeck/aarch64/libgles1-copyright" ]]; then
    cp "$REPO_DIR/PortMaster/retrodeck/aarch64/libgles1-copyright" \
      RD_PM/PortMaster/licenses/LICENSE-libgles1.txt
  fi
  ln -sfn libGLESv1_CM.so.1.2.0 \
    RD_PM/PortMaster/retrodeck/libs.aarch64/libGLESv1_CM.so.1
  ln -sfn libGLESv1_CM.so.1 \
    RD_PM/PortMaster/retrodeck/libs.aarch64/libGLESv1_CM.so
fi

mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/retrodeck.portmaster.zip"
(cd RD_PM && zip -9qry "$DIST_DIR/retrodeck.portmaster.zip" PortMaster/)
echo "Built $DIST_DIR/retrodeck.portmaster.zip"
