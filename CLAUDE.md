# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

PortMaster is a port manager for Linux handheld devices (ArkOS, ROCKNIX, muOS, Knulli, TrimUI, etc.). It has two halves:

- **Python app**: an SDL2 GUI (`PortMaster/pugwash`) plus a CLI (`PortMaster/harbourmaster`), both built on the `harbourmaster` library in `PortMaster/pylibs/harbourmaster/`.
- **Device-side shell layer**: `PortMaster/PortMaster.sh`, `control.txt`, `device_info.txt`, `mod_<CFW>.txt`, `libgl_<CFW>.txt` and per-CFW folders (`muos/`, `trimui/`, `batocera/`, `knulli/`, `miyoo/`, `spruce/`, `retrodeck/`). Ports' own launch scripts `source` `control.txt` on the device, so changes here affect every installed port, not just the GUI.

Everything ships as a zip. Bundled binaries (`gptokeyb*`, `xdelta3*`, `7zzs.*`, `innoextract.*`, `sdl2imgshow.*`, ...) are prebuilt; `BUILDING_STUFF.md` documents how to rebuild some of them.

## Commands

There is no build step for the Python code. Code must stay compatible with **Python 3.7** (some CFWs still ship it); all runtime libraries are vendored, and dev tools come from `requirements-dev.txt`.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest                           # all tests except `network`-marked ones
.venv/bin/pytest -m "not sdl"              # skip tests that start SDL headless (dummy video driver)
.venv/bin/pytest tests/test_harbour.py -k install   # single file / test
python3 PortMaster/pugwash                 # run the GUI locally (windowed)
python3 PortMaster/harbourmaster help      # CLI: list/ports/install/uninstall/runtime_list/device_info/...
flake8 --select=E9,F63,F7,F82 PortMaster/pugwash PortMaster/harbourmaster PortMaster/pylibs/harbourmaster PortMaster/pylibs/pug*.py tests   # the lint CI enforces; full flake8 still reports lots of existing style issues
./do_release.sh                            # build PortMaster.zip (+ pylibs.zip inside); `./do_release.sh stable` also builds makeself installers
./do_i18n.sh                               # extract strings with xgettext, sync with Crowdin, compile .mo (needs crowdin CLI)
```

pugwash flags: `--quiet --no-check --debug --no-colour --force-colour --no-log --offline --no-harbour`.

To test on a device: `./do_release.sh`, copy `PortMaster.zip` over, then on the device run `./PortMaster/harbourmaster --no-check install ./PortMaster.zip` (the `./` prefix makes it install a local file).

## Local-dev mode (HM_TESTING)

`pylibs/harbourmaster/config.py` detects a `.git` directory in the cwd (or its parent, and will `chdir` up) and sets `HM_TESTING=True`. In that mode the tools dir is the repo root and ports install into `./ports/`, the window is not fullscreen, and update checks are skipped. Otherwise the tools/ports dirs are chosen by probing CFW-specific paths, overridable with the `HM_TOOLS_DIR` / `HM_PORTS_DIR` / `HM_SCRIPTS_DIR` env vars.

`pugwash` also skips extracting `pylibs.zip` when run from a git checkout. On device, a release ships `pylibs.zip` which pugwash extracts over `pylibs/` and `exlibs/` on first launch.

Device info comes from `hardware.HardwareDetector`, which reads the env file written by the `device_info.txt` shell script, or uses the process environment directly if `DEVICE_NAME` / `DEVICE_CPU` / `CFW_NAME` are set. Set those env vars to emulate another device; the tests rely on this too. The result is memoised in `hardware._CACHED_DICT`.

## Tests

`tests/` (pytest, not shipped). `tests/conftest.py` sets the `HM_*_DIR` and device env vars **before** importing `harbourmaster`, because `config.py` resolves directories at import time. It also sets the builtins (`PORTMASTER_DEBUG`, `PYLIB_PATH`) that library code expects pugwash to inject, and blocks `requests` so no test touches the network. Key fixtures:
- `make_hm` / `hm`: an offline `HarbourMaster` in tmp dirs.
- `online_hm`: the PortMaster source loaded from `tests/data/ports.json`, with downloads served from generated zips.
- `RecordingCallback`: captures messages and message boxes.
- `load_script`: imports the extension-less `pugwash` / `harbourmaster` scripts.

`test_gui_smoke.py` drives pugwash's `fifo_control` mode the same way `PortMasterDialog.txt` does. Known bugs are pinned as `xfail(strict=True)`, so a test fails once the bug is fixed and the marker should then be removed. pugwash's `main()` is wrapped in `logger.catch`, so it exits 0 even after a crash; check its output for tracebacks rather than relying on the exit code.

## Architecture

**Import setup**: `pugwash` and `harbourmaster` (the scripts) prepend `pylibs/` and `exlibs/` to `sys.path`. `exlibs/` holds vendored third-party packages (loguru, requests, urllib3, certifi, ...), and `pylibs/` holds project code plus vendored `sdl2`, `png`, `pyqrcode`. Don't edit vendored code unless that's the point of the change. pugwash injects some globals via `__builtins__` (`PYLIB_PATH`, `PORTMASTER_DEBUG`, `DEFAULT_LANG`, `CURRENT_LANG`), and `pugscene` is star-imported.

**harbourmaster library** (`pylibs/harbourmaster/`):
- `harbour.py`: the `HarbourMaster` class, the core engine for sources, port/runtime install/uninstall, installed-port tracking, and config. Both the GUI and CLI drive it.
- `source.py`: port repository backends registered in `HM_SOURCE_APIS` (`PortMasterV3` is current; V1/V2/`GitHubRepoV1` are legacy or custom sources).
- `platform.py`: per-CFW hooks (`PlatformBase` subclasses registered in `HM_PLATFORMS`, keyed by lowercase device/CFW name). They handle gamelist.xml updates, moving scripts, ES refresh and similar. Add a new CFW here and also as `mod_<CFW>.txt`, plus possibly in `control.txt` / `config.py` path probing.
- `hardware.py`: device capabilities (arch, resolution, RAM, CFW, glibc) used to filter ports via `match_requirements`.
- `info.py`: port.json loading and normalisation (`port_info_load`/`port_info_merge`). `captain.py` validates port zips. `util.py` holds download/hash/signature helpers and the `Callback` progress interface.

**GUI** (`pugwash` + `pylibs/`):
- `PortMasterGUI` (in pugwash) subclasses both `pySDL2gui.GUI` and `harbourmaster.Callback`, so HarbourMaster operations report progress and messages straight into the GUI. It manages a scene stack (`push_scene`/`pop_scene`).
- `pugscene.py`: all screens as `BaseScene` subclasses (main menu, ports list, port info, filters, options, themes, ...).
- `pugtheme.py`: theme loading. Themes are JSON describing per-scene elements; `default_theme/theme.json` is the built-in one. See `THEME.md` for the element/scene spec, inheritance order and text-template tags.
- `pySDL2gui.py`: the low-level SDL2 widget/rendering layer (derived from port_gui).

**FIFO control**: `pugwash fifo_control` and `harbourmaster fifo_control` let shell scripts (e.g. `PortMasterDialog.txt`, used by `PortMaster.sh` for autoinstall) drive dialogs, progress, installs and runtime checks through a named pipe. See `do_fifo_control` / `fifo_*` methods in pugwash. A `pugtask.FifoReader` thread reads the pipe.

## Threading model (GUI)

- **Main thread only:** SDL calls, scenes, `push_scene`/`pop_scene` and `set_data`. Worker threads hand work to the main thread through `gui.dispatcher` (`pugtask.MainThreadDispatcher`): `post()` for fire-and-forget, `call()` when they need the result. `do_update()` drains it every frame.
- **Slow work goes through `gui.run_task(fn, ...)`.** It runs `fn` on a worker while the main loop keeps rendering, then returns the result or re-raises in the caller, so scene code stays synchronous. All HarbourMaster work (install, uninstall, update, runtime checks, startup) goes through it.
  - Only one task runs at a time, because HarbourMaster isn't thread-safe.
  - `run_task` called from the worker just runs inline.
  - Calling it on the main thread while a task is running raises an error.
- **`PortMasterGUI` is `hm.callback`, and its callbacks are thread-aware:**
  - `message`, `progress`, `messages_begin` and `messages_end` are forwarded from the worker. Progress is coalesced to one update per frame.
  - `message_box` blocks the worker until the user answers.
  - Cancel (`do_cancel`) sets a flag on the task. The worker raises `CancelEvent` at its next `progress`/`message`, and only if `gui.cancellable` is true.
- **While a task runs:** only the `messages`/`message_box` layers get input, and lower layers receive their `update_data` after the task. New scene code mustn't read `gui.hm` from the draw path.
- **Other background threads:**
  - `pugtask.DirectoryScanner` works out installed port sizes.
  - `ImageManager.enable_async` decodes port screenshots (absolute paths) and returns a `PendingImage` until the main thread uploads the texture. Theme images load synchronously.
- **`quit()` order:** it destroys textures, the renderer and the window before `sdl2.ext.quit()`. Garbage collection after `SDL_Quit` segfaults on muOS/Mali.
- **Profiling:** `PM_PERF=1` logs fps and every gap between frames over 50 ms to `pugwash.txt` (`pugtask.FrameStats`). Run it on a real device to measure lag.

## Versioning and releases

The version lives in the `## -- BEGIN PORTMASTER INFO --` block at the top of `pugwash` (and `HARBOURMASTER INFO` in `harbourmaster/__init__.py`). `tools/pm_release.py` rewrites that block. `do_release.sh` backs up and restores pugwash around this, so the committed value stays a placeholder. Releases are built by the manually triggered GitHub workflows in `.github/workflows/` (alpha/beta/stable); `do_beta.sh` / `do_stable.sh` stamp the version and commit.

## Translations

Wrap user-facing strings in `_()` (gettext). Strings are extracted from `pugwash`, `pylibs/harbourmaster/*.py` and `pylibs/pug*.py` into `pylibs/locales/messages.pot`; theme strings go into `themes.pot` via `theme_msgfmt.py`. Translations are managed on Crowdin, so don't hand-edit `.po` files for other languages.

## Style

Follow `.flake8`: long lines are fine, `##` comments are the house style, aligned `=` is allowed, and star imports are used.
