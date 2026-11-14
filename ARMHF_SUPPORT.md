# Experimental ARMHF support in RetroDECK

**Status: experimental; Nox-Decomp has been confirmed running with functional
rendering using the Mesa GLX runtime path documented below.**

This document consolidates the investigation into running 32-bit ARM hard-float
(ARMHF) PortMaster ports inside RetroDECK's AArch64 Flatpak. It records the
current evidence and separates confirmed facts from remaining hypotheses. It
does not describe a supported general PortMaster feature.

## Summary

- Flatpak multiarch was enabled for the ARM64 RetroDECK prototype. The static
  `arm32-flatpak-probe` runs, confirming the kernel and Flatpak permit at least
  that static ARM32 executable. This does not validate dynamic ARMHF loading.
- RetroDECK's PortMaster data bundle supplies an ARMHF loader and libc. The
  runtime libc is from the Ubuntu 24.04 ARMHF build and provides symbols through
  `GLIBC_2.39`.
- Nox-Decomp's executable and its port-local OpenAL, GL4ES, and FFmpeg libraries
  require no newer than `GLIBC_2.29`. A static dependency inventory found their
  `DT_NEEDED` names in the port-local directories and RetroDECK's ARMHF bundles.
  The observed Nox failures therefore are not explained by a too-new glibc
  requirement or an obvious missing shared-library dependency.
- The ARMHF SDL EGL probe reaches SDL video initialization but has failed to
  create a usable EGL display (`Could not get EGL display`). That EGL test-path
  failure does not prevent the working Mesa GLX configuration below.
- The Chromebook has an AArch64 Panfrost driver, but no host ARMHF DRI driver
  was found. RetroDECK has a separately built ARMHF Mesa/Panfrost sidecar. Its
  presence alone does not prove that it can create a context against the
  Chromebook's DRM device through the Flatpak sandbox.
- A Rocknix H700 image contains a complete ARMHF graphics stack that is useful
  as a reference. Its Gallium library requires `GLIBC_2.43`, so it cannot be
  substituted into the current `GLIBC_2.39` RetroDECK ARMHF runtime.
- Nox-Decomp is confirmed working through the normal PortMaster launch path
  with functional rendering using the Mesa GLX runtime documented below.
  Crop and Claw is separately confirmed working when Westonpack is bypassed
  for RetroDECK + Panfrost + an existing desktop `DISPLAY`. That Westonpack
  fix is separate from Nox's ARMHF graphics configuration.

## Runtime and Nox findings

### Where the ARMHF runtime comes from

The installed RetroDECK PortMaster runtime is in the app's writable data area:

```text
~/.var/app/net.retrodeck.retrodeck/data/PortMaster/retrodeck/libs.armhf/
~/.var/app/net.retrodeck.retrodeck/data/PortMaster/retrodeck/mesa.armhf/lib/
```

Both directories contain ARMHF copies of `libc.so.6` and
`ld-linux-armhf.so.3`. These are shipped in RetroDECK's PortMaster data bundle;
the ARMHF loader and libc used by this experiment are not being obtained from
the host's AArch64 system libraries. The Mesa sidecar has its own copies as
well. The ARM64 Flatpak runtime still provides the normal AArch64 system
runtime; these files are a separate ARMHF compatibility environment.

The port sets `PORT_32BIT=Y` before sourcing `mod_RetroDECK.txt`. That mod
places `libs.armhf` before `libs.aarch64` in `PM_LIBRARY_PATH` for ARMHF ports.
Nox also has port-local library directories, including:

```text
nox-decomp/ffmpeg.armhf/
nox-decomp/openal.armhf/
nox-decomp/gl4es.armhf/
```

The Nox diagnostic launcher explicitly invokes the ARMHF loader. An
absolute ELF interpreter path such as `/lib/ld-linux-armhf.so.3` cannot be
assumed to resolve inside the Flatpak, which is why the explicit loader path
and ARMHF library search path are important.

### Confirmed working Nox graphics configuration

Nox-Decomp is confirmed working both through a direct diagnostic launch and
through its normal PortMaster launch on the tested RetroDECK Chromebook. Both
use the ARMHF dynamic loader and Mesa GLX runtime libraries in RetroDECK's
PortMaster data area. The essential graphics settings are:

```sh
ARMHF_RUNTIME="$HOME/.var/app/net.retrodeck.retrodeck/data/PortMaster/retrodeck/armhf-runtime/lib"
export SDL_VIDEO_GL_DRIVER="$ARMHF_RUNTIME/libGL.so.1"
export LD_LIBRARY_PATH="$ARMHF_RUNTIME:$LD_LIBRARY_PATH"
```

`SDL_VIDEO_GL_DRIVER` must point to the Mesa/GLVND `libGL.so.1`, rather than
the port-local `gl4es.armhf/libGL.so.1`. Keep the port's FFmpeg and OpenAL
directories on the ARMHF library search path, and invoke the game through the
bundled `ld-linux-armhf.so.3`. The successful run used existing Mesa GLX
runtime files; it did not depend on the proposed source-built Mesa artifacts.

The direct `x11_glx_mesa_runtime` probe created an SDL window, loaded Nox maps
and assets, set a 1920x1200 GL viewport, and remained in the game until the
user closed it. The user confirmed rendering was fully functional. Nox then
received `SDL_QUIT` and exited with status 0.

The original Nox port launcher was restored and left unchanged. Its final
`pm_platform_helper` call provides a hook after the port's normal GL setup and
before it starts the game. RetroDECK's sourced `mod_RetroDECK.txt` wraps that
function, preserving the original helper for other ports and platforms. For
Nox only, it activates when all of these are true: `PORT_32BIT=Y`, AArch64,
`CFW_NAME=RetroDECK`, the RetroDECK Flatpak ID, `PM_PORTNAME=Nox-Decomp`, an
active `DISPLAY`, the host GPU is detected as Panfrost, the ARMHF Panfrost
sidecar and GLX runtime are present, and the bundled ARMHF loader is
executable. Host detection uses the PortMaster `GPU_DRIVER` marker when
available, then checks `/sys/class/drm/card*/device/driver` and
`/sys/class/drm/renderD*/device/driver` symlinks. Merely shipping
`panfrost_dri.so` is not evidence that the machine has a Panfrost GPU: this
sidecar is present in the test ZIP on every host.

When the condition matches, the hook selects SDL X11 and Mesa's GLVND
`libGL.so.1`, sets the Mesa sidecar's EGL/GLES/DRI/GBM paths, sets
`LIBGL_NOES2COMPAT=1`, `LIBGL_GL=21`, and `LIBGL_ES=2`, clears EGL-forcing
variables and `LIBGL_FB`, and orders libraries as port FFmpeg, port OpenAL,
Mesa GLX runtime, Mesa sidecar, then port GL4ES. It launches `noxd.armhf`
through `$controlfolder/retrodeck/libs.armhf/ld-linux-armhf.so.3`, applies the
port's OpenAL preload, then runs `pm_finish` when Nox exits. Conditions that do
not match call the original `pm_platform_helper` unchanged.

This mod-hook approach was tested successfully through the regular PortMaster
flow on the Chromebook; the user confirmed Nox started and rendering worked.
The hook writes the selected driver, loader, graphics variables, library path,
and exit status to the port's existing `log.txt`. Set
`NOX_ARMHF_DIAGNOSTICS=1` to additionally enable `LD_DEBUG=libs`. The result is
confirmed for this RetroDECK Flatpak/Panfrost setup and remains experimental
until tested on other devices and with other ARMHF ports.

## Experimental RetroDECK ZIP packaging

The regular `PortMaster.zip` remains generic. The release workflow builds a
separate experimental ARMHF runtime and ARMHF Mesa sidecar, then adds them only
to `retrodeck.portmaster.zip`. The RetroDECK archive contains:

```text
PortMaster/retrodeck/armhf-runtime/   # Ubuntu 24.04 ARMHF SDL/runtime libraries
PortMaster/retrodeck/mesa.armhf/      # Ubuntu 24.04 ARMHF Mesa + Panfrost userspace
PortMaster/retrodeck/libs.armhf/ld-linux-armhf.so.3
PortMaster/retrodeck/ARMHF-EXPERIMENTAL.txt
```

The workflow's `build-retrodeck-tools` job and local build script both use the
root `Dockerfile.retrodeck-tools`, which holds the existing Ubuntu 24.04 build
for architecture-specific RetroDECK helpers. CI runs that container on native
x86_64 and AArch64 runners and archives its outputs without losing symlinks.
The `build-armhf-experiment` job builds the two ARMHF artifacts from
`experimental/armhf-runtime/Dockerfile` and `Dockerfile.graphics`. These
artifacts are explicitly test-only; do not add them to the generic PortMaster
archive or treat their inclusion as general ARMHF support.

The runtime image checks that all exported ARMHF symlinks resolve. This matters
because Ubuntu's `libelf.so.1`, for example, can point to a versioned file
whose name does not match the usual `*.so.*` collection pattern. The Docker
build now includes symlink targets before packaging and fails if any are still
missing.

On a host with Podman and a working container runtime, run:

```sh
cd /path/to/PortMaster-GUI
./build_retrodeck_test_zip.sh stable
```

Use `alpha` or `beta` to choose a different upstream PortMaster base. The
script builds tools for the host's native architecture, builds both ARMHF
bundles, and writes `dist/retrodeck.portmaster.zip`. It needs network access to
Ubuntu package mirrors, the pinned source releases, and the upstream
PortMaster release. An ARM64 machine can test the AArch64 RetroDECK bundle;
CI remains responsible for also building and including the x86_64 helper
artifacts from its native runner.

The mod's Panfrost detection is intentionally separate from packaging. On a
Panfrost RetroDECK Flatpak, a successful launch should log
`RetroDECK ARMHF Nox Mesa GLX launch selected` plus either
`Panfrost detected via: GPU_DRIVER` or the matched DRM sysfs path. On a
non-Panfrost machine, the package may contain the sidecar, but the hook should
log that Panfrost was not detected and preserve the original PortMaster helper
behavior.

The diagnostic launcher is `nox-direct-probe.sh` in the workspace root (run
on-device as `Nox Direct Probe.sh`). Its successful mode is
`x11_glx_mesa_runtime`. The tested GL4ES GLX and EGL alternatives still fail.

### Nox binary and dependency inventory

The port's `noxd.armhf` is a dynamically linked ARM EABI5 hard-float binary.
Its maximum observed glibc requirement is `GLIBC_2.29`. The direct
dependencies include SDL2, OpenAL, GL4ES (`libGL.so.1`), FFmpeg, libc, libm,
libgcc, pthread, and the ARMHF loader. The port-local OpenAL and GL4ES
libraries require at most `GLIBC_2.16` and `GLIBC_2.27`, respectively; its
FFmpeg libraries require at most `GLIBC_2.29`.

An ELF dependency scan across the Nox port-local directories and RetroDECK's
`libs.armhf` and Mesa sidecar found providers for the scanned `DT_NEEDED`
names. This is a static name/architecture inventory, not proof that the
runtime loader resolves the same files in the actual process or that all
runtime `dlopen()` modules are present.

Earlier, Nox reported that `libpulsecommon-16.1.so` was missing. It is now
present in RetroDECK's `libs.armhf` directory. The current dependency scan does
not identify an obvious missing direct or transitive shared-library name.

Observed launch failures over the investigation include:

- `Bad system call` while invoking Nox through the ARMHF loader (SIGSYS).
- Later Nox launches ending with a segmentation fault (SIGSEGV).
- The ARMHF SDL/EGL probe failing window/context creation with
  `Could not get EGL display`.

These observations have not yet been reduced to one root cause. They point
toward sandbox syscall policy, EGL/display backend selection, DRM device access,
or an ARMHF graphics-stack/runtime interaction rather than a simple glibc
version mismatch. A successful static ARM32 probe does not rule out any of
those dynamic-runtime issues.

## Graphics stack comparison

### Chromebook and RetroDECK sidecar

The Chromebook exposes an AArch64 Panfrost/Mali graphics stack and the
AArch64 SDL EGL probes were able to create contexts. No host ARMHF
`panfrost_dri.so` was found under the system library paths. ARM64 Mesa driver
objects cannot be loaded by an ARMHF process because they have a different ELF
class and machine ABI.

RetroDECK's experimental sidecar provides its own ARMHF Mesa 25.2.8 stack,
including EGL, GLES, GBM, DRM, Gallium, LLVM, and Panfrost. Its Panfrost DRI
object is ARM EABI hard-float and has SONAME `libdril_dri.so`. That driver
depends on `libgbm.so.1`, libc, libm, and libgcc. Its Gallium library depends
on LLVM 20.1 and requires up to `GLIBC_2.38`; the sidecar libc provides through
`GLIBC_2.39`.

Despite those files being present, the ARMHF SDL probe has not obtained an EGL
display. The failure does not yet distinguish an inaccessible DRM/render node,
an unsupported EGL platform/backend, a mismatch between the sidecar and the
host kernel/driver, or other sandbox restrictions.

### Rocknix H700 ARMHF reference

The 2026-11-01 Rocknix H700 image was unpacked, and its ARMHF shared objects
were retained locally for comparison under
`../rocknix-h700-20261101-armhf-reference/`. That reference directory is a
workspace artifact outside this repository.

The reference contains the image's `/usr/lib32` ARMHF shared objects and
symlinks, ARMHF loader alias, 32-bit loader search configuration, Mesa EGL
vendor manifest, and an ELF dependency inventory. The full image and
intermediate extraction files were deleted after the selective extraction.

Rocknix's graphics stack includes ARMHF Panfrost, EGL, GLES, GBM, DRM, and
SDL2. Its Panfrost DRI object has the same `libdril_dri.so` SONAME and the same
main Panfrost/GBM relationship as RetroDECK's sidecar. The builds are not the
same: Rocknix uses Mesa 26.2.4 and libdrm 2.133, while the sidecar uses Mesa
25.2.8 and libdrm 2.125. Rocknix's Gallium library does not list LLVM as a
dependency, whereas the sidecar's does.

The key compatibility blocker is glibc. Rocknix's Panfrost/Gallium build needs
`GLIBC_2.43`; its bundled ARMHF libc provides through `GLIBC_2.44`. RetroDECK's
bundled ARMHF libc provides only through `GLIBC_2.39`. Do not copy Rocknix's
Gallium library into the existing RetroDECK stack as a drop-in replacement.
The Rocknix files are a reference and a possible source for a separately
matched test runtime only if its libc and dependencies are also handled
consistently. The H700 device's stack also does not by itself establish
compatibility with the Chromebook's different Mali GPU and kernel.

## Westonpack finding (separate issue)

Crop and Claw originally failed in Westonpack's Crusty/X11 EGL path on the
RetroDECK Panfrost desktop. A writable test copy of `westonwrap.sh` detected
RetroDECK + Panfrost + desktop `DISPLAY` and bypassed Weston setup, launching
the game in the existing desktop session. The user confirmed that Crop and
Claw then worked. The SquashFS was not modified during that successful test.

The recommended upstream Westonpack change and exact edit location are
documented in [`WESTON_PANFROST.md`](WESTON_PANFROST.md). This workaround is
separate from Nox's Mesa GLX solution. Nox is an SDL app, and this Westonpack
test does not establish that ARMHF SDL can create an EGL context on the desktop.

## Current test state

| Test | Result |
| --- | --- |
| Static ARM32 executable in multiarch Flatpak | Runs |
| AArch64 SDL EGL probes on Chromebook | Context creation succeeds |
| ARMHF SDL EGL probe using current Mesa sidecar | Fails: `Could not get EGL display` |
| Nox via GL4ES X11 GLX | Fails: `Couldn't find matching GLX visual` |
| Nox direct probe via Mesa GLX runtime | **Confirmed working; user confirms fully functional rendering** |
| Nox normal PortMaster launch via RetroDECK mod hook and Mesa GLX runtime | **Confirmed working; user confirms game start and functional rendering** |
| Earlier Nox configurations | SIGSYS/SIGSEGV observed; not reproduced in the successful Mesa GLX run |
| Nox glibc requirement vs RetroDECK ARMHF libc | Compatible by symbol version (`2.29` required, `2.39` provided) |
| Nox scanned shared-library dependency names | No obvious unresolved names in scanned directories |
| Crop and Claw with Westonpack Panfrost bypass | Confirmed working in tested desktop session |
| Rocknix Gallium used with RetroDECK ARMHF libc | Incompatible as-is (`2.43` required, `2.39` provided) |

## Recommended next diagnostic steps

1. **Keep the mod hook narrowly scoped.** The conditional Mesa GLX selection
   lives in RetroDECK's `mod_RetroDECK.txt`; retain the Nox/Flatpak/Panfrost/
   X11 checks and original-helper fallback. Test this hook after PortMaster
   updates and on other supported ARMHF configurations before broadening it.
2. **Do not mix Rocknix Gallium with the current ARMHF libc.** If testing the
   Rocknix stack, use a coherent isolated runtime with a libc that satisfies
   `GLIBC_2.43`, and treat it as a diagnostic experiment rather than a fix.
3. **Keep the integration experimental.** Do not add the graphics sidecar or
   an ARMHF runtime to the generic PortMaster payload until dynamic loader,
   EGL, controls, audio, and representative-port tests work through the normal
   RetroDECK launcher.

## Related documentation and artifacts

- [`EXPERIMENTAL_ARMHF_FLATPAK_PLAN.md`](EXPERIMENTAL_ARMHF_FLATPAK_PLAN.md) —
  build and packaging plan for the separate ARMHF runtime.
- [`experimental/armhf-runtime/README.md`](experimental/armhf-runtime/README.md)
  — how to build the ARMHF SDL runtime, Mesa sidecar, and diagnostic probes.
- [`WESTON_PANFROST.md`](WESTON_PANFROST.md) — separate Westonpack Panfrost
  bypass proposal and confirmed Crop and Claw test.
- `../ARMHF_MULTIARCH_PLAN.md` — the separate RetroDECK workspace's Flatpak
  multiarch experiment plan.
- `../rocknix-h700-20261101-armhf-reference/ELF-DEPENDENCIES.txt` — the local
  Rocknix ARMHF ELF inventory and dependencies.
