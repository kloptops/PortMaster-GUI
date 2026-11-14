# Opt-in launcher for ports that need the bundled GL4ES GLES 1.1/EGL pair.
# Example: pm_run_gles1 ./neverputt
pm_run_gles1() {
  if [ "${RETRODECK_ARCH:-}" != "aarch64" ]; then
    echo "pm_run_gles1: GLES1 compatibility libraries are available only on AArch64" >&2
    return 1
  fi

  _pm_gles1_dir="$controlfolder/retrodeck/libs.aarch64/gles1"
  if [ ! -r "$_pm_gles1_dir/libEGL.so.1" ] ||
     [ ! -r "$_pm_gles1_dir/libGLESv1_CM.so.1" ]; then
    echo "pm_run_gles1: compatibility libraries are missing from $_pm_gles1_dir" >&2
    return 1
  fi

  _pm_gles1_native_egl="${LIBGL_EGL:-/usr/lib/aarch64-linux-gnu/libEGL.so.1}"
  _pm_gles1_native_gles="${LIBGL_GLES:-/usr/lib/aarch64-linux-gnu/libGLESv2.so.2}"
  if [ ! -r "$_pm_gles1_native_egl" ] || [ ! -r "$_pm_gles1_native_gles" ]; then
    echo "pm_run_gles1: native EGL/GLES2 drivers were not found" >&2
    return 1
  fi

  (
    LD_LIBRARY_PATH="$_pm_gles1_dir:$LD_LIBRARY_PATH"
    LD_PRELOAD="$_pm_gles1_dir/libEGL.so.1${LD_PRELOAD:+:$LD_PRELOAD}"
    LIBGL_EGL="$_pm_gles1_native_egl"
    LIBGL_GLES="$_pm_gles1_native_gles"
    LIBGL_NOTEST=1
    export LD_LIBRARY_PATH LD_PRELOAD LIBGL_EGL LIBGL_GLES LIBGL_NOTEST
    "$@"
  )
}
