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

mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/retrodeck.portmaster.zip"
(cd RD_PM && zip -9qr "$DIST_DIR/retrodeck.portmaster.zip" PortMaster/)
echo "Built $DIST_DIR/retrodeck.portmaster.zip"
