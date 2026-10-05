# SPDX-License-Identifier: MIT
#
# The PortMaster GUI. PortMaster/pugwash bootstraps pylibs and runs it.

from pathlib import Path

## The pylibs directory, default_theme/, resources/ and locales/ live there.
PYLIB_PATH = Path(__file__).resolve().parent.parent
