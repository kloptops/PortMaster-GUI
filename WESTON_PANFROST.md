# Panfrost and Westonpack on RetroDECK

## Finding

The Crop and Claw failure observed on RetroDECK is associated with the Panfrost graphics path and Westonpack's Crusty/X11 EGL setup. It is not inherently specific to Chromebooks or Flatpak. The successful local workaround launched Godot through RetroDECK's existing desktop X11/EGL session and skipped Westonpack for that game.

That workaround is specific to environments where the Flatpak can access a working host display. It should not be assumed to work on every RetroDECK installation or every Panfrost device.

## Confirmed Crop and Claw test

A writable test overlay copied `westonwrap.sh` out of the mounted squashfs and patched that copy at launch time. The original `weston_pkg_0.2.aarch64.squashfs` remained unchanged. The overlay made the wrapper find RetroDECK's active PortMaster folder under the Flatpak data home, detected Panfrost through `/sys/module/panfrost`, and selected Westonpack's existing direct-app path when `CFW_NAME=RetroDECK`, `GPU_DRIVER=panfrost`, and `DISPLAY` was set.

The user's latest test log confirmed:

```text
Westonpack test detection: CFW_NAME=RetroDECK GPU_DRIVER=panfrost DISPLAY=:0
RetroDECK Panfrost detected, bypassing weston setup entirely!
```

The user confirmed Crop and Claw then worked. This confirms the approach for this game and RetroDECK desktop session; ports that need Weston-specific setup still need compatibility testing.

## Nox-Decomp follow-up

Nox-Decomp does not bundle Weston, and this Nox launch path should not start
Westonpack. Nox is an SDL application; on the RetroDECK desktop it should use
the existing Wayland display directly. Keep Westonpack out of Nox-specific
troubleshooting and fixes. The Westonpack proposal below applies to the
separate Crop and Claw case only.

The original ARMHF SDL2 lacked X11 and Wayland video backends. An experimental
SDL2 2.32.10 runtime has now been cross-built with both backends, OpenGL,
OpenGL ES, and PulseAudio support; its maximum GLIBC symbol requirement is
2.38. It is installed in the isolated `retrodeck/armhf-runtime/lib`
directory, ahead of `libs.armhf` in the Nox test launcher. Logs confirm that
SDL initializes with both X11 and Wayland selected, but window creation fails:
X11 reports `Couldn't find matching GLX visual`, while Wayland reports
`Could not get EGL display`. The Wayland test also showed `LIBGL_FB=0`, which
selects GL4ES's standard X11 path. The current experiment unsets that setting,
directs SDL to the Mesa sidecar's EGL and GLES libraries, sets
`LIBGL_NOES2COMPAT=1`, and explicitly selects `EGL_PLATFORM=wayland`. Nox is
not yet confirmed working.

Earlier logs also contain a GL4ES `eglInitialize: EGL_BAD_DISPLAY`
extension-probe warning. The next launch will show whether explicitly selecting
the Wayland EGL platform lets SDL create a usable window.

To isolate SDL/Mesa from Nox and GL4ES, a standalone `Nox EGL Probe.sh`
PortMaster entry now launches an ARMHF SDL2 probe that creates an OpenGL ES 2
window and context using the same Wayland EGL/GLES libraries. Its output is
written to `ports/nox-decomp/sdl-egl-probe.log`.

This is a per-port launcher experiment. It does not change Westonpack or imply
that every ARMHF port should use the same SDL/display configuration.

## Recommended Westonpack patch

Integrate this as a small upstream `westonwrap.sh` change, rather than modifying the squashfs during every RetroDECK launch. Keep the regular Weston setup for all other cases.

### 1. Resolve RetroDECK's PortMaster directory

The wrapper saves the incoming `XDG_DATA_HOME` as `TMP_DATA_HOME`, then resets `XDG_DATA_HOME` to `$HOME/.local/share`. Its existing fallback to `/roms/ports/PortMaster` fails in the RetroDECK Flatpak. Add this check in the control-folder selection block, before the `/roms` fallback:

```bash
elif [ -d "$TMP_DATA_HOME/PortMaster/" ]; then
    controlfolder="$TMP_DATA_HOME/PortMaster"
```

Then source the selected `control.txt` and firmware mod as usual. This is required before the wrapper can read RetroDECK's `CFW_NAME` or `GPU_DRIVER`.

### 2. Detect the platform and choose direct launch

After the control and mod files are loaded, but before Weston setup begins, add a narrow condition:

```bash
if [[ "$CFW_NAME" = "RetroDECK" \
      && "${GPU_DRIVER:-}" = "panfrost" \
      && -n "${DISPLAY:-}" ]]; then
    echo "RetroDECK Panfrost detected, bypassing weston setup entirely!"
    # Reuse the existing Rocknix direct-app branch's setup and cleanup path.
fi
```

The recommended implementation should factor the already-existing Rocknix direct-app branch into a shared function or route both conditions to the same code. That code preserves the current `DISPLAY`/`WAYLAND_DISPLAY`, runs the wrapped command (arguments from position 5), and exits before starting Weston, seatd, or Crusty. Do not change `CFW_NAME` globally and do not fake `glxinfo`; use explicit platform and driver variables. The test overlay sourced `device_info.txt`, but the installed RetroDECK copy was version 0.1.15 and did not export `GPU_DRIVER`; it therefore used `/sys/module/panfrost` as a fallback. For the upstream patch, prefer PortMaster's supported driver detection and use the sysfs check only as a documented fallback if supported device-info versions do not populate the variable.

The non-empty `DISPLAY` check limits the direct launch to desktop sessions. It does not guarantee the display is reachable, so keep the condition conservative and log which branch was selected. If the direct command fails, the wrapper should report the failure clearly rather than silently implying Weston was started.

### Exact edit location

In the supplied Westonpack 0.2.7.1 wrapper, make the edits in `westonwrap.sh` inside `weston_pkg_0.2.aarch64.squashfs`:

1. Control-folder lookup and `source control.txt` section, around lines 73–92: add the `$TMP_DATA_HOME/PortMaster` candidate.
2. Platform-specific bypass section, around lines 106–130: share or extend the existing Rocknix/Panfrost direct-app branch with the RetroDECK + Panfrost + desktop-display condition.

Line numbers may shift in another Westonpack release; anchor on the control-folder selection and existing `ROCKNIX` bypass condition. The runtime is SquashFS/read-only, so edit the upstream source/build input and regenerate the package for a distributable fix. The successful local test instead used a writable `/tmp` overlay and did not alter the squashfs.

### Validation matrix

- RetroDECK + Panfrost + desktop `DISPLAY`: direct launch; no Weston/seatd/Crusty startup. Crop and Claw is confirmed working in this case.
- RetroDECK + non-Panfrost: existing Westonpack path.
- RetroDECK + Panfrost without `DISPLAY`: existing Westonpack path.
- Other firmware, including Rocknix: existing behavior unchanged.
- Check wrapped-process exit status, controller cleanup, and environment cleanup for both paths.

## Relevant code

- `PortMaster/mod_RetroDECK.txt` — RetroDECK-specific PortMaster settings.
- `PortMaster/device_info.txt` — GPU driver detection, including Panfrost.
- `PortMaster/retrodeck/launch_hooks.txt` — sources the control file and RetroDECK firmware mod for PortMaster's own launcher.
- `PortMaster/mod_nuubOS.txt` — example of special handling when the caller is `westonwrap.sh`; it does not itself establish that the same display assumptions apply to RetroDECK.
