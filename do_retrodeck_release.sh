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
RETRODECK_TOOLS_DIR="${RD_RETRODECK_TOOLS_DIR:-$REPO_DIR/PortMaster/retrodeck}"

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
  cp "$REPO_DIR/PortMaster/mod_RetroDECK.txt" mod_RetroDECK.txt

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

# Add locally built tools to the RetroDECK-specific bundle. CI provides both
# architectures; the local builder provides the native architecture only.
for arch in x86_64 aarch64; do
  if [[ -d "$RETRODECK_TOOLS_DIR/$arch" ]]; then
    mkdir -p "RD_PM/PortMaster/retrodeck/$arch"
    cp -a "$RETRODECK_TOOLS_DIR/$arch/." "RD_PM/PortMaster/retrodeck/$arch/"
  fi
done

# KDE's Flatpak runtime provides BZip2 as libbz2.so.1, while some AArch64 ports
# (including Frogfall's bundled libzip) request libbz2.so.1.0.
mkdir -p RD_PM/PortMaster/retrodeck/libs.aarch64
ln -sfn /lib/aarch64-linux-gnu/libbz2.so.1 \
  RD_PM/PortMaster/retrodeck/libs.aarch64/libbz2.so.1.0

# Pingus' SDL_mixer needs libmodplug, which PortMaster already bundles with
# the LÖVE runtime. Make it available to all RetroDECK ports as well.
cp -p "$REPO_DIR/PortMaster/runtimes/love_11.5/libs.aarch64/libmodplug.so.1" \
  RD_PM/PortMaster/retrodeck/libs.aarch64/

# Experimental ARMHF support is opt-in so the regular RetroDECK package
# remains unchanged unless the release workflow (or local builder) requests it.
if [[ "${RD_INCLUDE_ARMHF_EXPERIMENTAL:-0}" == "1" ]]; then
  ARMHF_RUNTIME_DIR="${RD_ARMHF_RUNTIME_DIR:-$REPO_DIR/PortMaster/retrodeck/armhf-runtime}"
  ARMHF_MESA_DIR="${RD_ARMHF_MESA_DIR:-$REPO_DIR/PortMaster/retrodeck/mesa.armhf}"
  for required in \
    "$ARMHF_RUNTIME_DIR/lib/ld-linux-armhf.so.3" \
    "$ARMHF_RUNTIME_DIR/lib/libc.so.6" \
    "$ARMHF_RUNTIME_DIR/lib/libGL.so.1" \
    "$ARMHF_RUNTIME_DIR/GLIBC_MAX_VERSION" \
    "$ARMHF_MESA_DIR/lib/dri/panfrost_dri.so" \
    "$ARMHF_MESA_DIR/lib/libEGL.so.1" \
    "$ARMHF_MESA_DIR/lib/libGLESv2.so.2"; do
    if [[ ! -e "$required" ]]; then
      echo "Missing required experimental ARMHF file: $required" >&2
      exit 1
    fi
  done
  mkdir -p RD_PM/PortMaster/retrodeck
  cp -a "$ARMHF_RUNTIME_DIR" RD_PM/PortMaster/retrodeck/armhf-runtime
  cp -a "$ARMHF_MESA_DIR" RD_PM/PortMaster/retrodeck/mesa.armhf
  mkdir -p RD_PM/PortMaster/retrodeck/libs.armhf
  cp -Lp "$ARMHF_RUNTIME_DIR/lib/ld-linux-armhf.so.3" \
    RD_PM/PortMaster/retrodeck/libs.armhf/ld-linux-armhf.so.3
  printf '%s\n' \
    'EXPERIMENTAL: ARMHF SDL runtime and Ubuntu 24.04 Mesa/Panfrost sidecar.' \
    'Nox GLX selection requires RetroDECK Flatpak, ARMHF PortMaster mode, an active X11 DISPLAY, and host Panfrost detection.' \
    'This bundle is for testing and is not a supported general PortMaster ARMHF runtime.' \
    > RD_PM/PortMaster/retrodeck/ARMHF-EXPERIMENTAL.txt
  for glibc_file in "$ARMHF_RUNTIME_DIR/GLIBC_MAX_VERSION" "$ARMHF_MESA_DIR/GLIBC_MAX_VERSION"; do
    glibc_max="$(cat "$glibc_file")"
    if [[ "$(printf '%s\n' "$glibc_max" 2.39 | sort -V | tail -n 1)" != "2.39" ]]; then
      echo "Experimental ARMHF payload requires GLIBC $glibc_max; maximum allowed is 2.39" >&2
      exit 1
    fi
  done
  if find RD_PM/PortMaster/retrodeck/armhf-runtime RD_PM/PortMaster/retrodeck/mesa.armhf \
      -type l ! -exec test -e {} \; -print | grep -q .; then
    echo "Experimental ARMHF bundle contains dangling symlinks" >&2
    exit 1
  fi
fi

# Neverball needs the GLVND GLES 1 dispatch library. The Flatpak runtime
# supplies GLdispatch and the Mesa driver; CI stages the ARM64 dispatch library.
GLES1_LIBRARY="$RETRODECK_TOOLS_DIR/aarch64/libGLESv1_CM.so.1.2.0"
if [[ -f "$GLES1_LIBRARY" ]]; then
  cp -p "$GLES1_LIBRARY" RD_PM/PortMaster/retrodeck/libs.aarch64/
  if [[ -f "$RETRODECK_TOOLS_DIR/aarch64/libgles1-copyright" ]]; then
    cp "$RETRODECK_TOOLS_DIR/aarch64/libgles1-copyright" \
      RD_PM/PortMaster/licenses/LICENSE-libgles1.txt
  fi
  ln -sfn libGLESv1_CM.so.1.2.0 \
    RD_PM/PortMaster/retrodeck/libs.aarch64/libGLESv1_CM.so.1
  ln -sfn libGLESv1_CM.so.1 \
    RD_PM/PortMaster/retrodeck/libs.aarch64/libGLESv1_CM.so
fi

# GLES1 ports can opt into this private GL4ES GLES/EGL pair. Keep it nested
# below libs.aarch64 so it is used only by the helper's child process.
GLES1_COMPAT_DIR="$RETRODECK_TOOLS_DIR/aarch64/gles1"
for library in \
  libGLESv1_CM.so.1.0.0 libGLESv1_CM.so.1 libGLESv1_CM.so \
  libEGL.so.1.0.0 libEGL.so.1 libEGL.so; do
  if [[ ! -e "$GLES1_COMPAT_DIR/$library" ]]; then
    echo "Missing GLES1 compatibility library: $GLES1_COMPAT_DIR/$library" >&2
    exit 1
  fi
done
mkdir -p RD_PM/PortMaster/retrodeck/libs.aarch64/gles1
cp -a "$GLES1_COMPAT_DIR/." RD_PM/PortMaster/retrodeck/libs.aarch64/gles1/

# Weston-based AArch64 ports need libjpeg's v8 ABI. The Ubuntu 24.04 ARM64
# release job builds and stages this library with the other RetroDECK tools.
JPEG8_LIBRARY="$RETRODECK_TOOLS_DIR/aarch64/libjpeg.so.8"
if [[ -f "$JPEG8_LIBRARY" ]]; then
  cp -p "$JPEG8_LIBRARY" RD_PM/PortMaster/retrodeck/libs.aarch64/
  cp "$RETRODECK_TOOLS_DIR/aarch64/libjpeg-turbo-LICENSE.md" \
    RD_PM/PortMaster/licenses/LICENSE-libjpeg-turbo.md
else
  echo "Missing AArch64 libjpeg.so.8; build it in the Ubuntu 24.04 ARM64 release job first." >&2
  exit 1
fi

mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/retrodeck.portmaster.zip"
(cd RD_PM && zip -9qry "$DIST_DIR/retrodeck.portmaster.zip" PortMaster/)
unzip -tq "$DIST_DIR/retrodeck.portmaster.zip" >/dev/null
if [[ "${RD_INCLUDE_ARMHF_EXPERIMENTAL:-0}" == "1" ]]; then
  unzip -Z1 "$DIST_DIR/retrodeck.portmaster.zip" | grep -F 'PortMaster/retrodeck/armhf-runtime/lib/ld-linux-armhf.so.3' >/dev/null
  unzip -Z1 "$DIST_DIR/retrodeck.portmaster.zip" | grep -F 'PortMaster/retrodeck/mesa.armhf/lib/dri/panfrost_dri.so' >/dev/null
fi
echo "Built $DIST_DIR/retrodeck.portmaster.zip"
