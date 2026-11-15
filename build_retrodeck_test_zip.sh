#!/usr/bin/env bash
# Build the experimental RetroDECK ARMHF bundle and local RetroDECK ZIP.
# This is intentionally separate from the generic PortMaster ZIP builder.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
# alpha|beta|stable: on top of that channel's latest PortMaster.zip, so only the tools, libraries and
# mod_RetroDECK.txt come from this checkout. local: everything from this checkout (./do_release.sh test).
CHANNEL="${1:-stable}"
case "$CHANNEL" in alpha|beta|stable|local) ;; *) echo "usage: $0 [alpha|beta|stable|local]" >&2; exit 2 ;; esac

case "$(uname -m)" in
  aarch64|arm64) TOOL_ARCH=aarch64; CONTAINER_ARCH=arm64 ;;
  x86_64|amd64) TOOL_ARCH=x86_64; CONTAINER_ARCH=amd64 ;;
  *) echo "Unsupported host architecture: $(uname -m)" >&2; exit 2 ;;
esac

command -v podman >/dev/null || { echo "podman is required" >&2; exit 1; }

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/retrodeck-test-zip.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -m 700 "$WORK_DIR/runtime" "$WORK_DIR/storage" "$WORK_DIR/runroot"
export XDG_RUNTIME_DIR="$WORK_DIR/runtime"

# Keep Podman's runtime state out of the host's possibly read-only
# /run/user/$UID. The vfs driver is slower but works without overlay setup.
podman_cmd=(podman --root "$WORK_DIR/storage" --runroot "$WORK_DIR/runroot" --storage-driver vfs)

mkdir -p "$WORK_DIR/tools/$TOOL_ARCH"
"${podman_cmd[@]}" build \
  --platform "linux/$CONTAINER_ARCH" \
  --build-arg "RETRODECK_ARCH=$TOOL_ARCH" \
  --file "$REPO_DIR/Dockerfile.retrodeck-tools" \
  --target artifact \
  --output "type=local,dest=$WORK_DIR/tools/$TOOL_ARCH" \
  "$REPO_DIR"

"${podman_cmd[@]}" build \
  --platform "linux/$CONTAINER_ARCH" \
  --file "$REPO_DIR/experimental/armhf-runtime/Dockerfile" \
  --target artifact \
  --output "type=local,dest=$WORK_DIR/armhf-runtime-output" \
  "$REPO_DIR/experimental/armhf-runtime"

"${podman_cmd[@]}" build \
  --platform "linux/$CONTAINER_ARCH" \
  --file "$REPO_DIR/experimental/armhf-runtime/Dockerfile.graphics" \
  --target artifact \
  --output "type=local,dest=$WORK_DIR/mesa-output" \
  "$REPO_DIR/experimental/armhf-runtime"

if [[ "$CHANNEL" == local ]]; then
  PM_DIST_DIR="${PM_DIST_DIR:-$REPO_DIR/dist}" "$REPO_DIR/do_release.sh" test
  release_args=()
else
  release_args=("$CHANNEL")
fi

RD_INCLUDE_ARMHF_EXPERIMENTAL=1 \
RD_RETRODECK_TOOLS_DIR="$WORK_DIR/tools" \
RD_ARMHF_RUNTIME_DIR="$WORK_DIR/armhf-runtime-output/armhf-runtime" \
RD_ARMHF_MESA_DIR="$WORK_DIR/mesa-output/armhf-mesa" \
PM_DIST_DIR="${PM_DIST_DIR:-$REPO_DIR/dist}" \
  "$REPO_DIR/do_retrodeck_release.sh" "${release_args[@]}"

echo "Experimental test ZIP: ${PM_DIST_DIR:-$REPO_DIR/dist}/retrodeck.portmaster.zip"
