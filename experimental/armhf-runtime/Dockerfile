# EXPERIMENTAL: build an isolated ARMHF runtime bundle for RetroDECK testing.
# This image is deliberately not part of the regular PortMaster release build.

FROM ubuntu:24.04 AS build

ARG SDL_VERSION=2.32.10
ENV DEBIAN_FRONTEND=noninteractive
ENV TARGET=arm-linux-gnueabihf

RUN dpkg --add-architecture armhf \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates cmake curl gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf \
      make ninja-build pkg-config \
      libpulse-dev:armhf \
      libx11-dev:armhf libxext-dev:armhf libxfixes-dev:armhf \
      libxcursor-dev:armhf libxi-dev:armhf libxinerama-dev:armhf \
      libxrandr-dev:armhf libxss-dev:armhf \
      libc6:armhf libgcc-s1:armhf libstdc++6:armhf \
      libpulse0:armhf \
      libx11-6:armhf libxext6:armhf libxfixes3:armhf \
      libxcursor1:armhf libxi6:armhf libxinerama1:armhf \
      libxrandr2:armhf libxss1:armhf \
 && rm -rf /var/lib/apt/lists/*

# Resolve target pkg-config metadata only from ARMHF packages.
ENV PKG_CONFIG_LIBDIR=/usr/lib/arm-linux-gnueabihf/pkgconfig:/usr/share/pkgconfig
ENV PKG_CONFIG_PATH=
ENV PKG_CONFIG_SYSROOT_DIR=/

WORKDIR /src
COPY runtime-probe.c /src/runtime-probe.c
RUN curl -fsSL "https://github.com/libsdl-org/SDL/releases/download/release-${SDL_VERSION}/SDL2-${SDL_VERSION}.tar.gz" \
      -o SDL2.tar.gz \
 && tar -xzf SDL2.tar.gz \
 && cmake -S "SDL2-${SDL_VERSION}" -B build-sdl -G Ninja \
      -DCMAKE_SYSTEM_NAME=Linux \
      -DCMAKE_SYSTEM_PROCESSOR=armv7 \
      -DCMAKE_C_COMPILER=${TARGET}-gcc \
      -DCMAKE_CXX_COMPILER=${TARGET}-g++ \
      -DCMAKE_FIND_ROOT_PATH=/usr/${TARGET} \
      -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
      -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY \
      -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
      -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY \
      -DCMAKE_INSTALL_PREFIX=/opt/armhf-runtime \
      -DCMAKE_BUILD_TYPE=Release \
      -DSDL_SHARED=ON -DSDL_STATIC=OFF -DSDL_TEST=OFF \
      -DSDL_X11=ON -DSDL_ALSA=OFF -DSDL_PULSEAUDIO=ON \
      -DSDL_WAYLAND=OFF -DSDL_KMSDRM=OFF -DSDL_OPENGL=OFF \
 && cmake --build build-sdl --parallel 2 \
 && cmake --install build-sdl \
 && install -D /lib/ld-linux-armhf.so.3 /opt/armhf-runtime/lib/ld-linux-armhf.so.3 \
 && install -D "SDL2-${SDL_VERSION}/LICENSE.txt" /opt/armhf-runtime/share/licenses/libsdl2-copyright \
 && arm-linux-gnueabihf-gcc -I/opt/armhf-runtime/include/SDL2 \
      /src/runtime-probe.c -L/opt/armhf-runtime/lib -lSDL2 \
      -o /opt/armhf-runtime/armhf-probe

# Export only runtime libraries, not the cross-compiler or development files.
# These packages provide SDL2's direct and transitive runtime dependencies.
RUN mkdir -p /out/armhf-runtime/lib /out/armhf-runtime/share/licenses \
 && find /opt/armhf-runtime/lib -maxdepth 1 \( -type f -o -type l \) -name '*.so.*' \
      -exec cp -a -t /out/armhf-runtime/lib/ {} + \
 && for d in /lib/arm-linux-gnueabihf /usr/lib/arm-linux-gnueabihf; do \
      if [ -d "$d" ]; then \
        find "$d" -maxdepth 1 \( -type f -o -type l \) -name '*.so.*' \
          -exec cp -a -t /out/armhf-runtime/lib/ {} +; \
      fi; \
    done \
 && pulse_common=$(find /usr/lib/arm-linux-gnueabihf -type f \
      -name 'libpulsecommon-*.so' -print -quit) \
 && test -n "$pulse_common" \
 && cp -a "$pulse_common" /out/armhf-runtime/lib/ \
 && cp -a /opt/armhf-runtime/share/licenses/libsdl2-copyright /out/armhf-runtime/share/licenses/ \
 && cp -a /opt/armhf-runtime/armhf-probe /out/armhf-runtime/armhf-probe \
 && dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
      | awk -F '\t' '$3 == "armhf" { print $1 "\t" $2 }' \
      > /out/armhf-runtime/armhf-packages.tsv \
 && while IFS="$(printf '\t')" read -r package version; do \
      package=${package%:armhf}; \
      copyright="/usr/share/doc/${package}/copyright"; \
      if [ -f "$copyright" ]; then \
        install -D "$copyright" "/out/armhf-runtime/share/licenses/${package}-copyright"; \
      fi; \
    done < /out/armhf-runtime/armhf-packages.tsv \
 && max_glibc=$(for library in /out/armhf-runtime/lib/*.so.* /out/armhf-runtime/armhf-probe; do \
      [ -f "$library" ] || continue; \
      arm-linux-gnueabihf-readelf --version-info "$library" \
        | sed -n '/Version needs section/,/Version definition section/p' \
        | grep -oE 'GLIBC_[0-9]+([.][0-9]+)+' || true; \
    done | sed 's/GLIBC_//' | sort -Vu | tail -n 1) \
 && test -n "$max_glibc" \
 && printf '%s\n' "$max_glibc" > /out/armhf-runtime/GLIBC_MAX_VERSION \
 && { \
      echo 'EXPERIMENTAL ARMHF runtime bundle'; \
      echo "SDL2 source release: ${SDL_VERSION}"; \
      echo 'Build base: Ubuntu 24.04'; \
      echo "Cross compiler: ${TARGET}"; \
      echo 'SDL video backend: X11'; \
      echo 'SDL audio backend: PulseAudio'; \
      echo "Maximum GLIBC symbol requirement: ${max_glibc}"; \
      echo 'Not a supported PortMaster runtime; validate on the target device.'; \
    } > /out/armhf-runtime/EXPERIMENTAL.txt \
 && for library in /out/armhf-runtime/lib/*.so.*; do \
      [ -f "$library" ] || continue; \
      arm-linux-gnueabihf-readelf -h "$library" | grep -q 'Machine:.*ARM' || { \
        echo "Unexpected non-ARM library in ARMHF bundle: $library" >&2; exit 1; \
      }; \
    done \
 && printf '%s\n' \
      '#!/bin/sh' \
      '# EXPERIMENTAL: invoke an ARMHF binary using this bundle loader.' \
      'set -eu' \
      'root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)' \
      'if [ "$#" -lt 1 ]; then echo "usage: $0 ARMHF_BINARY [ARGS...]" >&2; exit 2; fi' \
      'exec "$root/lib/ld-linux-armhf.so.3" --library-path "$root/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$@"' \
      > /out/armhf-runtime/armhf-run \
 && chmod 755 /out/armhf-runtime/armhf-run \
 && cd /out/armhf-runtime \
 && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS

FROM scratch AS artifact
COPY --from=build /out/ /
