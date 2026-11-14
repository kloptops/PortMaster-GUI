# Experimental ARMHF runtime bundle

This directory contains a standalone cross-build for investigating dynamic
ARMHF PortMaster ports in RetroDECK's ARM64 Flatpak. Its output is a shared
ARMHF runtime bundle intended to be reusable across ports, rather than a
Nox-specific package. It is deliberately separate from the PortMaster release
workflow and does not populate `PortMaster/libs.armhf/`.

The image cross-compiles SDL2 for ARMHF with X11 video support and exports it
with the ARMHF dynamic loader and runtime-library set. SDL2 is the first
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

The files will be under `out/armhf-runtime/`. The build requires network access
to Ubuntu's package repositories and the pinned SDL2 release archive. To try a
different SDL2 release, override `SDL_VERSION` explicitly and record the
revision used with any test results.

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

The Dockerfile currently copies the ARMHF runtime shared objects installed by
the Ubuntu 24.04 package dependencies into the bundle. This is intentionally
conservative and may include more libraries than SDL2 itself requires. Before
using the bundle beyond the experiment, reduce it to the verified dependency
closure and record package versions, hashes, symbol requirements, and all
upstream license notices. The exported bundle includes `armhf-packages.tsv`,
`GLIBC_MAX_VERSION`, license texts, and `SHA256SUMS` to support that review.

Do not stage this output into the general PortMaster payload or ship it in a
normal RetroDECK release until the experimental promotion criteria in
[`../../EXPERIMENTAL_ARMHF_FLATPAK_PLAN.md`](../../EXPERIMENTAL_ARMHF_FLATPAK_PLAN.md)
are met.
