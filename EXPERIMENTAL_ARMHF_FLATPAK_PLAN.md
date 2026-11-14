# EXPERIMENTAL: shared ARMHF runtime libraries for RetroDECK's ARM64 Flatpak

**Status:** Prototype built; target-device validation is still pending. This is
an experimental RetroDECK integration plan, not a supported PortMaster runtime
or a change to the standard release payload.

## Goal

Investigate whether dynamically linked ARMHF PortMaster ports can run inside
RetroDECK's ARM64 Flatpak, using a reusable shared ARMHF runtime bundle. Nox-
Decomp is an initial compatibility case, not the scope of the runtime. Keep any
libraries private to RetroDECK's PortMaster bundle until representative ports
have been tested on-device and the approach has been reviewed for broader
compatibility.

Flatpak's `--allow=multiarch` has already been verified with a static ARM32
syscall probe. That test proves the host kernel and Flatpak permission allow a
static ARM32 executable to run. It does not test the ARMHF dynamic loader or
shared libraries.

## Current CI and packaging points

The PortMaster-GUI release workflow currently uses GitHub-hosted Ubuntu 24.04
runners, not a Docker container: `ubuntu-24.04` for x86_64 and
`ubuntu-24.04-arm` for AArch64. The `build-retrodeck-tools` job builds selected
RetroDECK libraries and uploads architecture-specific artifacts. The release
job stages those under `PortMaster/retrodeck/<arch>/`.

Relevant existing files:

- `.github/workflows/release.yaml` — Ubuntu 24.04 library/tool builds and
  artifact validation.
- `do_retrodeck_release.sh` — assembles the RetroDECK-specific PortMaster zip
  and stages private compatibility libraries.
- `PortMaster/funcs.txt` — computes `PM_LIBRARY_PATH`; AArch64 runs include
  `libs.armhf` after `libs.aarch64` unless a port requests 32-bit-first order.
- `PortMaster/libs.armhf/` — currently only a placeholder in this checkout;
  no ARMHF compatibility libraries are built here.

The prototype builds a separate ARMHF artifact through
[`experimental/armhf-runtime/Dockerfile`](experimental/armhf-runtime/Dockerfile)
and exports it locally. It is not staged into a release payload. Any future CI
integration should keep the artifact private to RetroDECK; it should not add
the libraries to the general PortMaster runtime bundle or alter existing
x86_64/AArch64 library builds.

## Nox-Decomp dependency inventory

The installed port at `~/retrodeck/PortMaster/ports/nox-decomp` contains a
dynamically linked ARM EABI5 executable, `noxd.armhf`. Its ELF interpreter is
`/lib/ld-linux-armhf.so.3`; its highest observed GLIBC requirement is 2.29.

Direct dependencies from `readelf -d noxd.armhf`:

- `libSDL2-2.0.so.0` — not bundled in Nox's subdirectories; it is expected
  from PortMaster's shared ARMHF libraries.
- `libopenal.so.1`, `libGL.so.1`, and FFmpeg libraries — bundled in the port's
  `openal.armhf/`, `gl4es.armhf/`, and `ffmpeg.armhf/` directories.
- ARMHF base runtime: loader, `libc.so.6`, `libm.so.6`, `libpthread.so.0`, and
  `libgcc_s.so.1`.

The bundled OpenAL and GL4ES libraries depend on the ARMHF base runtime. The
bundled FFmpeg libraries depend on one another and on ARMHF libc, libm,
libpthread, and the loader. These per-port libraries do not replace the
missing dynamic loader, SDL2 library, or base ARMHF runtime.

In the current launch log, Nox exits with “cannot execute: required file not
found.” The executable's ELF interpreter is a likely cause, but confirm this
with a dynamic ARMHF probe before treating it as the only failure.

## Proposed experimental implementation

1. **Gate on dynamic-loader feasibility.** Build a tiny dynamically linked
   ARMHF `hello` executable with the same interpreter path as Nox. Test it in
   the ARM64 Flatpak with `--allow=multiarch`. Determine how the absolute
   `/lib/ld-linux-armhf.so.3` interpreter path can resolve in the Flatpak.
   The static probe did not answer this. If it requires a RetroDECK-specific
   launch shim or a custom runtime layout, document and test that before
   building a large library set.
2. **Build in a separate CI job.** Add an opt-in Ubuntu 24.04 x86_64 job using
   an ARMHF cross toolchain and a pinned ARMHF sysroot. Keep it separate from
   `build-retrodeck-tools`; do not change that job's current AArch64 outputs.
3. **Build a reusable shared-library baseline.** Start with the loader and
   base ARMHF runtime required by the dynamic probe, then build a pinned SDL2
   shared library with the platform backends needed by RetroDECK's existing
   desktop display. Nox does not bundle Weston; PortMaster's
   `pm_platform_helper` may invoke the separately installed Westonpack
   wrapper. The tested Panfrost path bypasses that helper and uses the
   existing X11 display. Inventory more ARMHF ports to identify additional
   libraries that are genuinely shared. Keep libraries bundled by individual
   ports local to those ports unless runtime inspection shows they should be
   shared.
4. **Validate every staged ELF.** Check ELF class/machine, interpreter,
   SONAME, all recursive `DT_NEEDED` entries, symbol versions, and license
   files. Record compiler, sysroot, source versions, hashes, and the maximum
   GLIBC requirement in an artifact manifest. Keep output in a separate
   `armhf` artifact directory.
5. **Keep it opt-in and private to RetroDECK.** Stage the artifact beneath the
   RetroDECK-specific PortMaster payload and expose its library path only in
   that integration. Avoid populating the general `PortMaster/libs.armhf`
   directory or changing generic PortMaster behavior until compatibility with
   other CFWs has been established.
6. **Device test before promotion.** Confirm the dynamic probe, then test
   Nox-Decomp and other representative ARMHF ports through their normal
   PortMaster launch paths. Record loader resolution, SDL video/audio
   initialization, controller behavior, and shutdown. If any stage fails,
   retain the artifact as experimental and do not include it in normal
   release artifacts.

## Promotion criteria

Keep the work marked **EXPERIMENTAL** until all of these are true:

- ARMHF dynamic-loader resolution works inside the Flatpak without relying on
  host ARMHF libraries.
- The dynamic probe and representative ARMHF ports, including Nox-Decomp,
  pass through the normal PortMaster launch path on the target Chromebook.
- All packaged libraries have verified architecture, dependency closure,
  symbol-version requirements, provenance, hashes, and licenses.
- Reset/update behavior preserves user PortMaster data and refreshes only the
  RetroDECK-owned compatibility files.
- The runtime is isolated from the general PortMaster release and can be
  disabled or removed without affecting AArch64 or x86_64 ports.
