# Panfrost and Westonpack on RetroDECK

## Finding

The Crop and Claw failure observed on RetroDECK is associated with the Panfrost graphics path and Westonpack's Crusty/X11 EGL setup. It is not inherently specific to Chromebooks or Flatpak. The successful local workaround launched Godot through RetroDECK's existing desktop X11/EGL session and skipped Westonpack for that game.

That workaround is specific to environments where the Flatpak can access a working host display. It should not be assumed to work on every RetroDECK installation or every Panfrost device.

## Why `mod_RetroDECK.txt` alone cannot fix Westonpack

PortMaster already detects the graphics driver and exports `GPU_DRIVER` from `device_info.txt`. RetroDECK's `mod_RetroDECK.txt` is sourced by ordinary PortMaster launch scripts, so it can make driver-specific settings available to those scripts.

The Westonpack wrapper is a separate process/runtime. In the observed launch log, `westonwrap.sh` tried to read `/roms/ports/PortMaster/control.txt`, which did not exist in the RetroDECK Flatpak environment. It then failed to find `get_controls`. That means the wrapper did not load RetroDECK's control setup or its firmware mod, so a Panfrost branch added only to `mod_RetroDECK.txt` would not affect that wrapper.

## Westonpack's documented Panfrost bypass

The supplied `weston_pkg_0.2.aarch64.squashfs` contains Westonpack 0.2.7.1. Its `westonwrap.sh` includes the documented Rocknix/Panfrost bypass: when `CFW_NAME=ROCKNIX` and `glxinfo` reports an OpenGL version string, it launches the wrapped app directly and skips Westonpack. `NO_PANFROST_BYPASS=1` disables that bypass. Westonpack's changelog also documents Panfrost-specific wrapped library and preload variables. See the [Westonpack changelog](https://github.com/binarycounter/Westonpack/wiki/Changelog) and [platform/mode documentation](https://github.com/binarycounter/Westonpack/wiki/Home).

The wrapper's PortMaster lookup explains the observed failure. It saves the incoming `XDG_DATA_HOME` in `TMP_DATA_HOME`, then immediately replaces `XDG_DATA_HOME` with `$HOME/.local/share` before checking for `PortMaster`. It checks conventional handheld paths and falls back to `/roms/ports/PortMaster`; it never checks the saved Flatpak data path. It then sources `control.txt` and `mod_${CFW_NAME}.txt` from the selected folder. In RetroDECK, that fallback path is absent, so neither its control file nor `mod_RetroDECK.txt` is loaded.

A targeted integration appears possible: teach the wrapper to check `$TMP_DATA_HOME/PortMaster` before the `/roms` fallback, then add a wrapper-only Panfrost branch to `mod_RetroDECK.txt` that presents the Rocknix detection values expected by this bypass. The mod must be sourced by the wrapper for that branch to run. This would adapt the existing bypass without changing `CFW_NAME` for ordinary game scripts. It still needs to be validated against the exact runtime and Flatpak display behavior before treating it as a general fix.

## Options for a general fix

1. Make Westonpack's wrapper load the active PortMaster control folder in RetroDECK, then let it check `GPU_DRIVER=panfrost` and select a direct-display path when one is available.
2. Add a RetroDECK launch integration that selects the direct-display path for Panfrost ports, while retaining Westonpack for other drivers and systems.
3. Keep a per-port launcher workaround where a port cannot use the host display path.

The first two options need a reliable way for the wrapper to find RetroDECK's PortMaster directory and a defined fallback for installations without an accessible desktop display. This note records the investigation; it does not change launch behavior.

## Relevant code

- `PortMaster/mod_RetroDECK.txt` — RetroDECK-specific PortMaster settings.
- `PortMaster/device_info.txt` — GPU driver detection, including Panfrost.
- `PortMaster/retrodeck/launch_hooks.txt` — sources the control file and RetroDECK firmware mod for PortMaster's own launcher.
- `PortMaster/mod_nuubOS.txt` — example of special handling when the caller is `westonwrap.sh`; it does not itself establish that the same display assumptions apply to RetroDECK.
