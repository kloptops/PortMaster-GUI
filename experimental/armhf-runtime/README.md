# Experimental ARMHF runtime bundle

This directory contains a standalone cross-build for investigating dynamic
ARMHF PortMaster ports in RetroDECK's ARM64 Flatpak. Its output is a shared
ARMHF runtime bundle intended to be reusable across ports, rather than a
Nox-specific package. It is deliberately separate from the PortMaster release
workflow and does not populate `PortMaster/libs.armhf/`.

The image cross-compiles SDL2 for ARMHF with X11 and Wayland video support,
OpenGL and OpenGL ES context support, and PulseAudio. It exports SDL2 with the
ARMHF dynamic loader and runtime-library set. SDL2 is the first
shared library in this experimental bundle; the build can be extended with
other generally useful PortMaster libraries as dependency inventory supports
them. Per-port libraries should remain with their ports unless evidence shows
they are broadly shared. The output is an experiment, not a supported runtime.

## Build and export

From this directory, use Podman or Docker with BuildKit/local output support:

```sh
podman build --target artifact --output type=local,dest=./out .
```

Docker equivalent:

```sh
DOCKER_BUILDKIT=1 docker build --target artifact --output type=local,dest=./out .
```

The files will be under `out/armhf-runtime/`. The SDL2 build enables both
display backends; ports should select one supported by their host session using
`SDL_VIDEODRIVER`. The build requires network access
to Ubuntu's package repositories and the pinned SDL2 release archive. To try a
different SDL2 release, override `SDL_VERSION` explicitly and record the
revision used with any test results.

For the current Nox-Decomp experiment, copy the generated `armhf-runtime/`
directory to `PortMaster/retrodeck/armhf-runtime/`. Its launcher prepends the
bundle's `lib/` directory after the Panfrost Mesa sidecar, so the new SDL2 and
its Wayland dependencies are available without replacing `libs.armhf`. This
is an on-device test arrangement, not a promoted runtime. The Docker build
checks that both X11 and Wayland backend compile definitions are present.

## Experimental ARMHF Mesa graphics sidecar

The ARMHF runtime above intentionally does not bundle graphics drivers. For a
Panfrost ARM64 host, build the separate Mesa sidecar from this directory:

```sh
podman build --file Dockerfile.graphics --target artifact \
  --output type=local,dest=./out/graphics .
```

It exports `out/graphics/armhf-mesa/` with ARMHF EGL, GLES, GBM, DRM, GBM
backend modules and the Panfrost DRI module from Ubuntu 24.04. It is an
experiment for systems where
the ARM64 kernel driver supports the 32-bit DRM ABI. ARM64 Mesa libraries
cannot be reused by ARMHF processes. Do not merge these files into the general
runtime or enable them on non-Panfrost systems.

Keep the sidecar separate from `libs.armhf`, for example in
`PortMaster/retrodeck/mesa.armhf/`, so it cannot replace the existing ARMHF
runtime. For an isolated test, prepend that directory to `LD_LIBRARY_PATH` and
set `LIBGL_EGL` to its `libEGL.so.1`, `LIBGL_GLES` to `libGLESv2.so.2`, and
`LIBGL_DRIVERS_PATH` to its `dri/` directory and `GBM_BACKENDS_PATH` to its
`gbm/` directory. Run an ARMHF EGL/GLES probe
before testing a game. Capture `LD_DEBUG=libs` and a core dump if the probe or
game fails. The sidecar alone does not prove that Panfrost's DRM node, X11 EGL
platform, sandbox device permissions, or the particular Chromebook kernel
work with ARMHF; verify those on the target.

## Device use for the dynamic-loader probe

Copy `armhf-runtime/` to an app-writable location inside the Flatpak. Invoke an
ARMHF executable through the bundled loader, for example:

```sh
./armhf-runtime/armhf-run ./armhf-runtime/armhf-probe
```

The wrapper passes the bundle library directory to the bundled
`ld-linux-armhf.so.3`, avoiding reliance on the absolute host path
`/lib/ld-linux-armhf.so.3`. This is a diagnostic route; it does not change
PortMaster's normal launcher or automatically run existing ports through this
loader. The included probe is dynamically linked to SDL2 and checks that both
the bundled loader and SDL2 can start. Test it first, then use Nox-Decomp as
one compatibility case. Also inspect SDL video, input, controller, and
shutdown behavior across other ARMHF ports before proposing broader
integration.

The bundle includes `armhf-probe`, a loader/SDL startup check, and
`sdl-egl-probe`, which initializes SDL video, creates an OpenGL ES 2.0 window,
and reports whether SDL can create an EGL context. Run `sdl-egl-probe` with the
same `SDL_VIDEODRIVER`, `EGL_PLATFORM`, Mesa sidecar paths, and runtime
libraries used by the Nox launch. This separates SDL/Mesa display setup from
Nox's GL4ES integration.

For comparison on the AArch64 Flatpak SDL stack, build a native 64-bit probe:

```sh
podman build --file Dockerfile.aarch64-probe --target artifact \
  --output type=local,dest=./out/aarch64-probe .
```

Install `sdl64-egl-probe` under
`PortMaster/retrodeck/aarch64-runtime/` and use the temporary `Nox EGL Probe`
entry. It tests SDL's automatic backend selection, Wayland defaults, explicit
system EGL/GLES libraries, forced Wayland EGL, and X11 with default and forced
EGL. Results go to `ports/nox-decomp/sdl64-egl-probe.log`; the ARMHF-specific
probe runs afterward and keeps its separate result in `sdl-egl-probe.log`.
The AArch64 probe uses the Flatpak's SDL2-compatible library at runtime and
does not load that library in the ARMHF process.

For the current device test, a temporary PortMaster entry named
`Nox EGL Probe.sh` runs the new binary with those settings and writes output to
`ports/nox-decomp/sdl-egl-probe.log`. It is separate from the Nox game launcher.

The Dockerfile copies the ARMHF runtime shared objects installed by the Ubuntu
24.04 package dependencies into the bundle, including PulseAudio's nested
`libpulsecommon` helper needed by ports that use the PulseAudio client library.
This is intentionally conservative and may include more libraries than SDL2
itself requires. Before using the bundle beyond the experiment, reduce it to
the verified dependency closure and record package versions, hashes, symbol
requirements, and all upstream license notices. The exported bundle includes
`armhf-packages.tsv`, `GLIBC_MAX_VERSION`, license texts, and `SHA256SUMS` to
support that review.

Do not stage this output into the general PortMaster payload or ship it in a
normal RetroDECK release until the experimental promotion criteria in
[`../../EXPERIMENTAL_ARMHF_FLATPAK_PLAN.md`](../../EXPERIMENTAL_ARMHF_FLATPAK_PLAN.md)
are met.
