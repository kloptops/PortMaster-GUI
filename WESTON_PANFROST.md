# Panfrost and Westonpack on RetroDECK

## Finding

The Crop and Claw failure observed on RetroDECK is associated with the Panfrost graphics path and Westonpack's Crusty/X11 EGL setup. It is not inherently specific to Chromebooks or Flatpak. The successful local workaround launched Godot through RetroDECK's existing desktop X11/EGL session and skipped Westonpack for that game.

That workaround is specific to environments where the Flatpak can access a working host display. It should not be assumed to work on every RetroDECK installation or every Panfrost device.

## Tested Crop and Claw workaround

The local `Crop and Claw.sh` launcher was changed to skip the Westonpack mount and `westonwrap.sh` call, and invoke Godot directly from the game directory. The tested command shape was:

```bash
/tmp/godot/godot422.aarch64 --resolution 1920x1200 -f \
  --rendering-driver opengl3_es --audio-driver ALSA \
  --main-pack "$GAMEDIR/crop_and_claw.pck" --disable-nes-colors
```

The launcher retained the game's Godot runtime setup and controller handling. This worked in the user's RetroDECK desktop session. The exact executable path, resolution, pack path, and game options are specific to this port; other Westonpack ports need their own launch arguments and may not work when started outside Westonpack. A direct launch also depends on the Flatpak session exposing a usable desktop display to the process.

## Why `mod_RetroDECK.txt` alone cannot fix Westonpack

PortMaster already detects the graphics driver and exports `GPU_DRIVER` from `device_info.txt`. RetroDECK's `mod_RetroDECK.txt` is sourced by ordinary PortMaster launch scripts, so it can make driver-specific settings available to those scripts.

The Westonpack wrapper is a separate process/runtime. In the observed launch log, `westonwrap.sh` tried to read `/roms/ports/PortMaster/control.txt`, which did not exist in the RetroDECK Flatpak environment. It then failed to find `get_controls`. That means the wrapper did not load RetroDECK's control setup or its firmware mod, so a Panfrost branch added only to `mod_RetroDECK.txt` would not affect that wrapper.

## Westonpack's documented Panfrost bypass

The supplied `weston_pkg_0.2.aarch64.squashfs` contains Westonpack 0.2.7.1. Its `westonwrap.sh` includes the documented Rocknix/Panfrost bypass: when `CFW_NAME=ROCKNIX` and `glxinfo` reports an OpenGL version string, it launches the wrapped app directly and skips Westonpack. `NO_PANFROST_BYPASS=1` disables that bypass. Westonpack's changelog also documents Panfrost-specific wrapped library and preload variables. See the [Westonpack changelog](https://github.com/binarycounter/Westonpack/wiki/Changelog) and [platform/mode documentation](https://github.com/binarycounter/Westonpack/wiki/Home).

The wrapper's PortMaster lookup explains the observed failure. It saves the incoming `XDG_DATA_HOME` in `TMP_DATA_HOME`, then immediately replaces `XDG_DATA_HOME` with `$HOME/.local/share` before checking for `PortMaster`. It checks conventional handheld paths and falls back to `/roms/ports/PortMaster`; it never checks the saved Flatpak data path. It then sources `control.txt` and `mod_${CFW_NAME}.txt` from the selected folder. In RetroDECK, that fallback path is absent, so neither its control file nor `mod_RetroDECK.txt` is loaded.

A targeted integration appears possible: teach the wrapper to check `$TMP_DATA_HOME/PortMaster` before the `/roms` fallback, then add a wrapper-only Panfrost branch to `mod_RetroDECK.txt` that presents the Rocknix detection values expected by this bypass. The mod must be sourced by the wrapper for that branch to run. This would adapt the existing bypass without changing `CFW_NAME` for ordinary game scripts. It still needs to be validated against the exact runtime and Flatpak display behavior before treating it as a general fix.

## Proposal: bypass Westonpack for RetroDECK on Panfrost

### Goal

Use Westonpack's existing direct-app path when a PortMaster game runs under RetroDECK on Panfrost. Keep the normal Westonpack path for other RetroDECK graphics drivers and for other firmware.

### Detection

Require both conditions:

1. The PortMaster firmware is RetroDECK (`CFW_NAME=RetroDECK`).
2. The detected graphics driver is Panfrost (`GPU_DRIVER=panfrost`).

Do not select this path from architecture alone: AArch64 does not identify the GPU or the display environment.

### Changes needed

1. In `westonwrap.sh`, around the PortMaster lookup at lines 73–85, add a check for the saved Flatpak data home before checking the reset `$XDG_DATA_HOME` and before falling back to `/roms`:

   ```bash
   elif [ -d "$TMP_DATA_HOME/PortMaster/" ]; then
     controlfolder="$TMP_DATA_HOME/PortMaster"
   ```

   This works with the existing `TMP_DATA_HOME=$XDG_DATA_HOME` at line 74 and allows the wrapper to source RetroDECK's active control and mod files at lines 87–92.
2. The wrapper currently leaves `device_info.txt` commented out at line 88. Ensure `GPU_DRIVER` is available after loading `control.txt`; if RetroDECK's control file does not source device info itself, source `$controlfolder/device_info.txt` there.
3. In `PortMaster/mod_RetroDECK.txt`, add a wrapper-only Panfrost case. For example, after confirming the variables are available:

   ```bash
   if [[ "${0##*/}" == westonwrap*.sh && "$CFW_NAME" == "RetroDECK" \
         && "$GPU_DRIVER" == "panfrost" && -n "${DISPLAY:-}" ]]; then
     CFW_NAME="ROCKNIX"
     glxinfo() { echo "OpenGL version string: RetroDECK Panfrost"; }
   fi
   ```

   This supplies the signals the wrapper checks at lines 106–120. Since the mod is sourced by the wrapper, this changes `CFW_NAME` only in the wrapper process, not in the game launch script. Keep this branch limited to `GPU_DRIVER=panfrost`.
4. Leave the existing Rocknix/Panfrost bypass branch at lines 106–130 intact. It captures the current `WAYLAND_DISPLAY` and `DISPLAY`, runs the command beginning at argument 5, and exits before Weston setup. Do not set `NO_PANFROST_BYPASS=1`, which disables this path.

### Fallback and scope

All other cases should follow the existing Westonpack behavior. A missing control directory, missing/unknown `GPU_DRIVER`, or empty `DISPLAY` must not trigger the bypass. Checking that `DISPLAY` is set does not prove that the X server is reachable; the integration should log the attempted bypass clearly and be tested in the target Flatpak session. The Crop and Claw direct-launch change is a successful local example, but the generic path needs testing with multiple ports because some apps may depend on Westonpack's environment or libraries.

### Validation

- RetroDECK + Panfrost: logs confirm the wrapper sourced the RetroDECK control/mod files, selected the bypass, and launched the app without starting Weston or seatd.
- RetroDECK + non-Panfrost: wrapper starts as it does now.
- Other firmware + Panfrost: wrapper starts as it does now.
- Verify game exit, gptokeyb cleanup, display restoration, and runtime cleanup in all cases.

### Implementation boundary

The control lookup change belongs in the Westonpack wrapper (inside the squashfs or upstream). The conditional RetroDECK behavior belongs in `mod_RetroDECK.txt`. Changing only RetroDECK's `control.txt` cannot fix the wrapper's current hard-coded fallback path.

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
